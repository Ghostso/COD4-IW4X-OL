/* CoDOL vehicle / turret / remote-view script builtins.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Reference evidence, all measured on iw4x.exe (base 0x400000) and C1.exe
 * 1.1.1.13 unless stated otherwise:
 *   attachpath      IW4 0x67f120 / C1 0x685490: node argument must be a class-3
 *                   vehicle node; the path record is attached (IW4 0x4b8cc0,
 *                   C1 0x6824d0) or the call errors "AttachPath: Unable to
 *                   attach to path node"; the vehicle is then placed at the
 *                   node origin/angles (IW4 0x67ef90, C1 0x685300).
 *   startpath       IW4 0x67f360 / C1 0x6858c0: an optional node argument
 *                   attaches without moving the vehicle (the path origin and
 *                   angles are taken from the live physics state, +0xd8/+0xf0);
 *                   without a node the vehicle must already be attached
 *                   ("StartPath: Can't start vehicle on path.  Vehicle must
 *                   already be attached if no node is specified"). Then the
 *                   end-of-path bit is cleared (IW4 0x42e290 `and word
 *                   [pathPos+2], ~1`), the goal speed is seeded from the
 *                   current one and the move state changes to the path state.
 *   vehicle_canturrettargetpoint IW4 0x67fef0: point, optional int, optional
 *                   ignore entity; requires tag_barrel; aims from the barrel
 *                   position in the tag_turret frame (or the body frame when
 *                   there is no tag_turret); yaw must lie in [-rightArc,
 *                   leftArc] and pitch in [-topArc, bottomArc] of the turret
 *                   weapon (WeaponDef 0x1a0..0x1ac); with the second argument
 *                   set, a locational trace (mask 0x801) from the barrel to the
 *                   point must pass, ignoring the vehicle and the third
 *                   argument.
 *   vehicle_finishdamage IW4 0x67f4d0: twelve arguments, world defaults for
 *                   undefined inflictor/attacker, damage <= 0 does nothing,
 *                   weapon must be precached unless it is "none"; then the
 *                   damage tail 0x481bd0 (health, "damage"/"death" notifies,
 *                   pain/die handlers) runs. The retained G_Damage already
 *                   contains that tail for vehicles, including
 *                   G_VehImmuneToDamage, so this re-enters it under a gate.
 *   vehicleturretcontrolon/off IW4 0x421d30 / 0x49a8a0: the controlling
 *                   player is recorded on the vehicle; "off" for a player who
 *                   is instead riding the vehicle dismounts through
 *                   VEH_UnlinkPlayer. The retained MP think drives the gun
 *                   angles and fire from ride slot 2 (gentity+0x30c), which is
 *                   the slot IW4 0x421d30 also clears (+0x30c) when the
 *                   controller was riding there.
 *   vehicle_dospawn IW4 0x680280 -> 0x420670: receiver must be a vehicle
 *                   spawner (0x67ee80: "Trying to call a vehicle spawner
 *                   command on a ..."), optional type string, optional owner
 *                   that must be a client ("Parameter must be a valid
 *                   client"); one spawn per spawner per frame; the spawner is
 *                   notified "spawned" with the new entity, which is returned.
 *   startac130 / stopac130 IW4 0x48f850 / 0x450b40: set/clear 0x8000 in the
 *                   client's weapon-flags word; remotecamerasoundscapeoff
 *                   IW4 0x5f54d0 clears 0x20 in the same word. C1's weapon
 *                   flag word (playerState 0x344) uses 0x8000 for the offhand
 *                   special restriction and the retained engine uses 0x20
 *                   itself, so neither bit can be published as-is; the state is
 *                   kept natively and exposed through accessors.
 *   maketurretsolid IW4 0x4038e0: contents = (contents & ~1) | 0x2040,
 *                   bounds midpoint (0,0,28) half size (14,14,28), relink.
 *   setturretminimapvisible IW4 0x4b1310: eFlags bit 0x400000 set/cleared.
 *   canplayerplacesentry IW4 0x489fe0 / 0x4a99d0 / 0x681180 with the
 *                   sentry_placement_* dvar defaults registered at 0x453840.
 */
#ifdef CODOL_SERVER
#include "codol_script_vehicle_builtins.h"
#include <stddef.h>
#include "scr_vm_functions.h"
#include "entity.h"
#include "player.h"
#include "g_shared.h"
#include "g_public.h"
#include "server.h"
#include "server_public.h"
#include "cm_public.h"
#include "cscr_stringlist.h"
#include "qcommon_io.h"
#include "q_math.h"
#include "bg_public.h"
#include "xassets/weapondef.h"
#include "codol_vehicle_spawner.h"
#include "codol_vehicle_assets.h"
#include "codol_vehicle_native.h"
#include <math.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

/* g_scr_vehicle.h is written for C++ (bare enum and struct type names). */
#ifndef __cplusplus
typedef struct vehicle_info_t vehicle_info_t;
typedef struct vehicle_node_t vehicle_node_t;
typedef struct vehicle_pathpos_t vehicle_pathpos_t;
typedef struct vehicle_physic_t vehicle_physic_t;
typedef enum VehicleMoveState VehicleMoveState;
typedef enum VehicleTurretState VehicleTurretState;
typedef struct VehicleTurret VehicleTurret;
typedef struct VehicleJitter VehicleJitter;
typedef struct VehicleHover VehicleHover;
typedef struct VehicleRideSlot_t VehicleRideSlot_t;
typedef struct VehicleTags VehicleTags;
typedef struct scr_vehicle_s scr_vehicle_s;
#endif
#include "g_scr_vehicle.h"

/* Retained assembly exports without C prototypes. */
extern int __cdecl G_MeansOfDeathFromScriptParam(int paramIndex);
extern int __cdecl G_GetHitLocationIndexFromString(unsigned int constString);
extern void __cdecl G_Damage(gentity_t *targ, gentity_t *inflictor, gentity_t *attacker,
    const float *dir, const float *point, int damage, int dflags, int mod, int weapon,
    int hitLoc, unsigned int modelIndex, unsigned int partName, int timeOffset);
extern void __cdecl G_DObjGetWorldBoneIndexPos(gentity_t *ent, int boneIndex, float *out);
extern void __cdecl G_DObjGetWorldBoneIndexMatrix(gentity_t *ent, int boneIndex, float (*axis)[3]);
extern void __cdecl G_VehUnlinkPlayer(gentity_t *vehicle, gentity_t *player);

/* _g_vehicles_mp.asm: eight 0x354-byte pool records; entNum at +0x1b8. */
#define VEHICLE_POOL 8
/* Class number of the vehicle node store (codol_script_vehicle_nodes.c). */
#define VEHICLE_NODE_CLASS 3
#define VEHICLE_NODE_LIMIT 16384
#define GUNNER_RIDE_SLOT 2
/* Retained means-of-death table size (src/g_combat_mp.cpp modNames). */
#define MOD_TABLE_ENTRIES NATIVE_DAMAGE_MOD_COUNT
/* Retained scr_vehicle_s.flags: bit 0 occupied, bit 3 first think done. */
#define VEH_FLAG_OCCUPIED 0x1
#define MPH_TO_IPS 17.600000381469727f
/* IW4 vehicle_canturrettargetpoint 0x68014f trace mask. */
#define TURRET_TARGET_TRACE_MASK 0x801
/* IW4 maketurretsolid 0x4038e0. */
#define TURRET_SOLID_CONTENTS 0x2040
#define TURRET_SOLID_HALF_XY 14.0f
#define TURRET_SOLID_HEIGHT 56.0f
/* IW4 setturretminimapvisible 0x4b131b. */
#define TURRET_MINIMAP_EFLAG 0x400000
/* IW4 sentry placement dvar defaults (0x453840..0x4539e2). */
#define SENTRY_FEET_OFFSET_X 17.0f
#define SENTRY_FEET_OFFSET_Y 20.0f
#define SENTRY_FEET_OFFSET_Z 10.0f
#define SENTRY_FEET_TRACE_DIST_Z 20.0f
#define SENTRY_TRACE_RADIUS 30.0f
#define SENTRY_TRACE_RADIUS_CANON_SAFETY 5.0f
#define SENTRY_TRACE_DIST 42.0f
#define SENTRY_TRACE_PITCH 20.0f
#define SENTRY_TRACE_MIN_NORMAL 0.7f
/* IW4 0x4a9b69 / 0x6812f0. */
#define SENTRY_TRACE_MASK 0x2810011

/* ------------------------------------------------------------------ */
/* small vector helpers                                                */
static float angle_normalize180(float angle)
{
    /* IW4 0x67f177..0x67f1c9: (a + 180) * (1/360), floor, back. */
    float turns = (float)floor((double)((angle + 180.0f) * 0.0027777778f));
    return angle - turns * 360.0f;
}
static void axis_transpose_transform(const float *in, float axis[3][3], float *out)
{
    out[0] = DotProduct(in, axis[0]);
    out[1] = DotProduct(in, axis[1]);
    out[2] = DotProduct(in, axis[2]);
}

/* ------------------------------------------------------------------ */
/* receivers                                                           */
static gentity_t *entity_receiver(scr_entref_t ref)
{
    if (ref.classnum || ref.entnum >= MAX_GENTITIES) {
        Scr_ObjectError("not an entity");
        return NULL;
    }
    return &g_entities[ref.entnum];
}
static gentity_t *vehicle_receiver(scr_entref_t ref, const char *method)
{
    gentity_t *ent = entity_receiver(ref);
    if (!ent) return NULL;
    if (!ent->scr_vehicle) {
        Scr_ObjectError(va("%s requires a script vehicle", method));
        return NULL;
    }
    return ent;
}
static gentity_t *player_receiver(scr_entref_t ref, const char *method)
{
    gentity_t *ent = entity_receiver(ref);
    if (!ent) return NULL;
    if (!ent->client) {
        Scr_ObjectError(va("%s requires a player", method));
        return NULL;
    }
    return ent;
}
static gentity_t *turret_receiver(scr_entref_t ref, const char *method)
{
    gentity_t *ent = entity_receiver(ref);
    if (!ent) return NULL;
    if (!ent->pTurretInfo) {
        Scr_ObjectError(va("%s requires a turret; entity classname is '%s'", method,
            ent->classname ? SL_ConvertToString(ent->classname) : ""));
        return NULL;
    }
    return ent;
}
static int vehicle_pool_slot(const gentity_t *ent)
{
    ptrdiff_t slot;
    if (!ent || !ent->scr_vehicle || !level.vehicles) return -1;
    slot = ent->scr_vehicle - level.vehicles;
    if (slot < 0 || slot >= VEHICLE_POOL) return -1;
    return (int)slot;
}

/* ------------------------------------------------------------------ */
/* vehicle node records                                                */
static int node_vector(unsigned index, const char *key, float *out)
{
    const char *text = CODOL_VehicleNodeValue(index, key);
    char extra;
    if (!text) return 0;
    if (sscanf(text, "%f %f %f %c", &out[0], &out[1], &out[2], &extra) != 3 ||
        !isfinite(out[0]) || !isfinite(out[1]) || !isfinite(out[2])) return 0;
    return 1;
}
static int node_float(unsigned index, const char *key, float *out)
{
    const char *text = CODOL_VehicleNodeValue(index, key);
    char *end;
    double value;
    if (!text) return 0;
    value = strtod(text, &end);
    if (end == text || !isfinite(value)) return 0;
    *out = (float)value;
    return 1;
}
/* target -> targetname links, resolved once per level from the map keys the
 * node store retained (the IW4 loader links its 0x44-byte node records the
 * same way; 0x67d160 fills the two switch nodes from those links). */
static short node_next[VEHICLE_NODE_LIMIT];
static short node_prev[VEHICLE_NODE_LIMIT];
static int node_links_built;
static void build_node_links(void)
{
    unsigned count = CODOL_VehicleNodeCount(), i, j;
    if (count > VEHICLE_NODE_LIMIT) count = VEHICLE_NODE_LIMIT;
    for (i = 0; i < count; ++i) { node_next[i] = -1; node_prev[i] = -1; }
    for (i = 0; i < count; ++i) {
        const char *target = CODOL_VehicleNodeValue(i, "target");
        if (!target || !*target) continue;
        for (j = 0; j < count; ++j) {
            const char *name = CODOL_VehicleNodeValue(j, "targetname");
            if (name && !strcmp(name, target)) {
                node_next[i] = (short)j;
                if (node_prev[j] < 0) node_prev[j] = (short)i;
                break;
            }
        }
    }
    node_links_built = 1;
}
static int node_valid(int index)
{
    return index >= 0 && (unsigned)index < CODOL_VehicleNodeCount() &&
           index < VEHICLE_NODE_LIMIT;
}
static int next_node(int index)
{
    if (!node_links_built) build_node_links();
    return node_valid(index) ? node_next[index] : -1;
}
/* Node argument: IW4 0x4523e0 / C1 0x5ce110 accept only a class-3 object
 * ("not a vehicle node" otherwise). */
static int node_argument(unsigned param)
{
    scr_entref_t ref;
    if (Scr_GetType(param) != VAR_POINTER || Scr_GetPointerType(param) != VAR_ENTITY) {
        Scr_ParamError(param, "not a vehicle node");
        return -1;
    }
    ref = Scr_GetEntityRef(param);
    if (ref.classnum != VEHICLE_NODE_CLASS || !node_valid(ref.entnum)) {
        Scr_ParamError(param, "not a vehicle node");
        return -1;
    }
    return ref.entnum;
}

/* ------------------------------------------------------------------ */
/* path following                                                      */
typedef struct {
    int attached;
    int running;
    int entnum;
    int node;             /* node the vehicle last passed / is attached to */
    int next;             /* node it is moving toward, -1 at the path end */
    int approaching;      /* moving from a free position onto the node */
    float frac;           /* 0..1 along segment start -> next */
    vec3_t segStart;      /* origin of node, or the free start position */
} vehicle_path_t;
static vehicle_path_t paths[VEHICLE_POOL];

void CODOL_VehiclePath_Reset(void)
{
    memset(paths, 0, sizeof(paths));
    node_links_built = 0;
}
void CODOL_VehiclePath_EntityFreed(unsigned entnum)
{
    unsigned i;
    for (i = 0; i < VEHICLE_POOL; ++i)
        if (paths[i].attached && (unsigned)paths[i].entnum == entnum)
            memset(&paths[i], 0, sizeof(paths[i]));
}
static vehicle_path_t *path_for(gentity_t *ent)
{
    int slot = vehicle_pool_slot(ent);
    if (slot < 0) return NULL;
    if (paths[slot].attached && paths[slot].entnum != ent->s.number)
        memset(&paths[slot], 0, sizeof(paths[slot]));
    return &paths[slot];
}
/* Retained VEH_SetPosition (_g_vehicles_mp.asm 0x4836..): G_SetOrigin,
 * G_SetAngle, TR_INTERPOLATE on both trajectories, SV_LinkEntity, skipped
 * when nothing changed. */
static void vehicle_set_position(gentity_t *ent, const float *origin, const float *angles)
{
    if (VectorCompare(origin, ent->r.currentOrigin) && VectorCompare(origin, ent->s.lerp.pos.trBase) &&
        VectorCompare(angles, ent->r.currentAngles) && VectorCompare(angles, ent->s.lerp.apos.trBase))
        return;
    G_SetOrigin(ent, origin);
    G_SetAngle(ent, angles);
    ent->s.lerp.pos.trType = TR_INTERPOLATE;
    ent->s.lerp.apos.trType = TR_INTERPOLATE;
    SV_LinkEntity(ent);
}
/* IW4 0x4b8cc0: fill the path record from the node. */
static int attach_node(gentity_t *ent, vehicle_path_t *path, int node, int teleport)
{
    scr_vehicle_s *vehicle = ent->scr_vehicle;
    vec3_t origin, angles;
    float speed = 0.0f, lookahead = 0.0f;
    if (!node_valid(node) || !node_vector(node, "origin", origin)) return 0;
    if (!node_vector(node, "angles", angles)) VectorClear(angles);
    node_float(node, "speed", &speed);
    node_float(node, "lookahead", &lookahead);
    path->attached = 1;
    path->entnum = ent->s.number;
    path->node = node;
    path->next = next_node(node);
    path->frac = 0.0f;
    path->approaching = !teleport;
    if (teleport) VectorCopy(origin, path->segStart);
    else VectorCopy(vehicle->phys.origin, path->segStart);
    vehicle->pathPos.nodeIdx = (int16_t)node;
    vehicle->pathPos.endOfPath = (int16_t)(vehicle->pathPos.endOfPath | 1);
    vehicle->pathPos.frac = 0.0f;
    vehicle->pathPos.speed = speed * MPH_TO_IPS;
    vehicle->pathPos.lookAhead = lookahead;
    if (teleport) {
        VectorCopy(origin, vehicle->pathPos.origin);
        VectorCopy(angles, vehicle->pathPos.angles);
    } else {
        VectorCopy(vehicle->phys.origin, vehicle->pathPos.origin);
        VectorCopy(vehicle->phys.angles, vehicle->pathPos.angles);
    }
    VectorCopy(origin, vehicle->pathPos.lookPos);
    return 1;
}
void CODOL_Scr_AttachPath(scr_entref_t ref)
{
    gentity_t *ent = vehicle_receiver(ref, "attachpath");
    vehicle_path_t *path;
    scr_vehicle_s *vehicle;
    vec3_t angles;
    int node;
    if (!ent) return;
    vehicle = ent->scr_vehicle;
    path = path_for(ent);
    if (!path) { Scr_Error("attachpath: vehicle is not in the native vehicle pool"); return; }
    node = node_argument(0);
    if (node < 0) return;
    if (!attach_node(ent, path, node, 1)) {
        Scr_Error("AttachPath: Unable to attach to path node");
        return;
    }
    path->running = 0;
    /* IW4 0x67f15c..0x67f1d6 / C1 0x685548..0x6855b8: place the vehicle on
     * the node; the yaw normalization applies to definition type 1 only. */
    VectorCopy(vehicle->pathPos.angles, angles);
    if (vehicle->infoIdx >= 0 && vehicle->infoIdx < 32 && s_vehicleInfos[vehicle->infoIdx].type == 1)
        angles[1] = angle_normalize180(angles[1]);
    VectorCopy(vehicle->pathPos.origin, vehicle->phys.origin);
    VectorCopy(vehicle->pathPos.origin, vehicle->phys.prevOrigin);
    VectorCopy(angles, vehicle->phys.angles);
    VectorCopy(angles, vehicle->phys.prevAngles);
    VectorClear(vehicle->phys.vel);
    vehicle_set_position(ent, vehicle->pathPos.origin, angles);
}
void CODOL_Scr_StartPath(scr_entref_t ref)
{
    gentity_t *ent = vehicle_receiver(ref, "startpath");
    vehicle_path_t *path;
    scr_vehicle_s *vehicle;
    if (!ent) return;
    vehicle = ent->scr_vehicle;
    path = path_for(ent);
    if (!path) { Scr_Error("startpath: vehicle is not in the native vehicle pool"); return; }
    if (Scr_GetNumParam() > 0) {
        int node = node_argument(0);
        if (node < 0) return;
        if (!attach_node(ent, path, node, 0)) {
            Scr_Error("StartPath: Unable to attach to path node");
            return;
        }
    } else if (!path->attached || vehicle->pathPos.nodeIdx < 0) {
        Scr_Error("StartPath: Can't start vehicle on path.  Vehicle must already be attached if no node is specified");
        return;
    }
    /* IW4 0x42e290 / C1 0x6859fa: clear the end-of-path bit; the goal speed
     * is seeded from the current speed and the move state becomes the path
     * state. */
    vehicle->pathPos.endOfPath = (int16_t)(vehicle->pathPos.endOfPath & ~1);
    path->running = 1;
    vehicle->moveState = VEH_MOVESTATE_MOVE;
    vehicle->stopping = 0;
}
/* Speed the path wants at this node: script vehicle_setspeed (manual mode)
 * wins, then the node's own speed, then the definition's maximum. */
static float path_goal_speed(const scr_vehicle_s *vehicle, int node)
{
    float speed = 0.0f;
    if (vehicle->manualMode) return vehicle->manualSpeed;
    if (node_valid(node) && node_float(node, "speed", &speed) && speed > 0.0f)
        return speed * MPH_TO_IPS;
    if (vehicle->infoIdx >= 0 && vehicle->infoIdx < 32)
        return s_vehicleInfos[vehicle->infoIdx].maxSpeed;
    return 0.0f;
}
static float path_accel(const scr_vehicle_s *vehicle, int braking)
{
    float value = 0.0f;
    if (vehicle->manualMode) value = braking ? vehicle->manualDecel : vehicle->manualAccel;
    if (!(value > 0.0f) && vehicle->infoIdx >= 0 && vehicle->infoIdx < 32)
        value = s_vehicleInfos[vehicle->infoIdx].accel;
    if (!(value > 0.0f)) value = 1.0e6f;
    return value;
}
static void notify_node_trigger(int node, gentity_t *vehicle)
{
    Scr_AddEntity(vehicle);
    Scr_NotifyNum(node, VEHICLE_NODE_CLASS, scr_const.trigger, 1);
}
/* Point `distance` units ahead of the vehicle along the path, following into
 * later segments; used for the facing direction. */
static void path_lookahead_point(const vehicle_path_t *path, float distance, float *out)
{
    vec3_t from, to, dir;
    int node = path->next;
    float length;
    unsigned guard = 0;
    VectorCopy(path->segStart, from);
    if (node < 0 || !node_vector(node, "origin", to)) { VectorCopy(from, out); return; }
    VectorSubtract(to, from, dir);
    length = VectorLength(dir);
    distance += path->frac * length;
    while (distance > length && guard++ < 64) {
        int following = next_node(node);
        vec3_t nextOrigin;
        if (following < 0 || following == node || !node_vector(following, "origin", nextOrigin)) break;
        distance -= length;
        VectorCopy(to, from);
        VectorCopy(nextOrigin, to);
        VectorSubtract(to, from, dir);
        length = VectorLength(dir);
        node = following;
    }
    if (length > 0.0f) {
        if (distance > length) distance = length;
        VectorMA(from, distance / length, dir, out);
    } else VectorCopy(to, out);
}
int CODOL_VehiclePath_Think(gentity_t *ent)
{
    vehicle_path_t *path;
    scr_vehicle_s *vehicle;
    vec3_t segEnd, dir, origin, look = {0.0f, 0.0f, 0.0f}, angles, velocity;
    float dt, goal, speed, length, remaining, travel;
    int passed = 0;
    if (!ent || !ent->scr_vehicle) return 0;
    path = path_for(ent);
    if (!path || !path->attached || !path->running) return 0;
    vehicle = ent->scr_vehicle;
    dt = (float)(level.time - level.previousTime) * 0.001f;
    if (!(dt > 0.0f)) dt = 0.05f;
    if (path->next < 0 || !node_vector(path->next, "origin", segEnd)) {
        /* Attached to a terminal node: nothing to move toward. */
        VectorClear(vehicle->phys.vel);
        vehicle->speed = 0.0f;
        vehicle->moveState = VEH_MOVESTATE_STOP;
        vehicle->pathPos.endOfPath = (int16_t)(vehicle->pathPos.endOfPath | 1);
        path->running = 0;
        Scr_Notify(ent, scr_const.reached_end_node, 0);
        return 1;
    }
    goal = path_goal_speed(vehicle, path->node);
    speed = vehicle->speed;
    if (speed < goal) { speed += path_accel(vehicle, 0) * dt; if (speed > goal) speed = goal; }
    else if (speed > goal) { speed -= path_accel(vehicle, 1) * dt; if (speed < goal) speed = goal; }
    travel = speed * dt;
    /* Advance along segments, firing each node's "trigger" as it is passed
     * (the IW4 tank script waits on exactly that: _tank.gsc handleBranchNode). */
    while (travel > 0.0f) {
        VectorSubtract(segEnd, path->segStart, dir);
        length = VectorLength(dir);
        remaining = length * (1.0f - path->frac);
        if (travel < remaining) { path->frac += travel / length; travel = 0.0f; break; }
        travel -= remaining;
        path->node = path->next;
        path->next = next_node(path->node);
        path->frac = 0.0f;
        path->approaching = 0;
        VectorCopy(segEnd, path->segStart);
        vehicle->pathPos.nodeIdx = (int16_t)path->node;
        vehicle->pathPos.speed = path_goal_speed(vehicle, path->node);
        node_float(path->node, "lookahead", &vehicle->pathPos.lookAhead);
        ++passed;
        notify_node_trigger(path->node, ent);
        if (path->next < 0 || path->next == path->node || !node_vector(path->next, "origin", segEnd)) {
            path->next = -1;
            break;
        }
        if (passed > 64) break;
    }
    VectorSubtract(segEnd, path->segStart, dir);
    length = VectorLength(dir);
    if (path->next < 0 || length <= 0.0f) {
        VectorCopy(path->segStart, origin);
        VectorCopy(origin, look);
        VectorCopy(vehicle->phys.angles, angles);
        VectorClear(velocity);
        speed = 0.0f;
    } else {
        VectorMA(path->segStart, path->frac, dir, origin);
        path_lookahead_point(path, vehicle->pathPos.lookAhead > 0.0f ? vehicle->pathPos.lookAhead : 1.0f, look);
        VectorSubtract(look, origin, dir);
        if (VectorLength(dir) <= 0.001f) VectorSubtract(segEnd, path->segStart, dir);
        Vec3Normalize(dir);
        vectoangles(dir, angles);
        angles[2] = 0.0f;
        VectorScale(dir, speed, velocity);
    }
    VectorCopy(vehicle->phys.origin, vehicle->phys.prevOrigin);
    VectorCopy(vehicle->phys.angles, vehicle->phys.prevAngles);
    VectorCopy(origin, vehicle->phys.origin);
    VectorCopy(angles, vehicle->phys.angles);
    VectorCopy(velocity, vehicle->phys.vel);
    VectorCopy(origin, vehicle->pathPos.origin);
    VectorCopy(angles, vehicle->pathPos.angles);
    VectorCopy(look, vehicle->pathPos.lookPos);
    vehicle->pathPos.frac = path->frac;
    vehicle->speed = speed;
    vehicle_set_position(ent, origin, angles);
    if (path->next < 0) {
        vehicle->moveState = VEH_MOVESTATE_STOP;
        vehicle->pathPos.endOfPath = (int16_t)(vehicle->pathPos.endOfPath | 1);
        path->running = 0;
        Scr_Notify(ent, scr_const.reached_end_node, 0);
    } else vehicle->moveState = VEH_MOVESTATE_MOVE;
    return 1;
}
void CODOL_VehiclePath_RunFrame(void)
{
    unsigned i;
    if (!level.vehicles) return;
    for (i = 0; i < VEHICLE_POOL; ++i) {
        unsigned number = level.vehicles[i].entNum;
        if (number >= ENTITYNUM_WORLD || !paths[i].attached || !paths[i].running) continue;
        if (g_entities[number].scr_vehicle != &level.vehicles[i]) continue;
        CODOL_VehiclePath_Think(&g_entities[number]);
    }
}

/* ------------------------------------------------------------------ */
/* vehicle_canturrettargetpoint                                        */
/* IW4 0x67fef0..0x68019b. The envelope is the VEHICLE definition's turret
 * spans, not the turret weapon's arcs: 0x48a250 returns the vehicle slot
 * array 0x666abf0 (the same table IW4 443ac3 fills with VehicleDefs), and
 * 0x6800e4..0x68012e compares pitch against -def+0x1a8 / def+0x1ac and yaw
 * against -def+0x1a4 / def+0x1a0, i.e. turretVertSpanUp/Down and
 * turretHorizSpanRight/Left. The retained IW3 aim clamp in Scr_Vehicle_Think
 * (_g_scr_vehicle.asm, info+0xd0..0xdc) uses the same four spans. Vehicle
 * turret weapons such as cobra_20mm_mp carry zero weapon arcs, so testing
 * those rejected every point and the attack helicopter never took a target. */
void CODOL_Scr_VehicleCanTurretTargetPoint(scr_entref_t ref)
{
    gentity_t *ent = vehicle_receiver(ref, "vehicle_canturrettargetpoint");
    scr_vehicle_s *vehicle;
    const vehicle_info_t *info;
    vec3_t point, barrel, baseAngles, delta, local, aim;
    float axis[3][3];
    int doTrace = 0, ignore = ENTITYNUM_NONE, count;
    if (!ent) return;
    vehicle = ent->scr_vehicle;
    if (vehicle->infoIdx < 0 || vehicle->infoIdx >= 32) { Scr_Error("vehicle has no definition"); return; }
    info = &s_vehicleInfos[vehicle->infoIdx];
    Scr_GetVector(0, point);
    count = Scr_GetNumParam();
    if (count > 1) doTrace = Scr_GetInt(1);
    if (count > 2) {
        gentity_t *ignoreEnt = Scr_GetEntity(2);
        if (ignoreEnt) ignore = ignoreEnt->s.number;
    }
    if (vehicle->boneIndex.barrel < 0) { Scr_Error("Vehicle has no tag [tag_barrel]\n"); return; }
    G_DObjGetWorldBoneIndexPos(ent, vehicle->boneIndex.barrel, barrel);
    if (vehicle->boneIndex.turret >= 0) {
        G_DObjGetWorldBoneIndexMatrix(ent, vehicle->boneIndex.turret, axis);
        AxisToAngles(axis, baseAngles);
    } else VectorCopy(vehicle->phys.angles, baseAngles);
    VectorSubtract(point, barrel, delta);
    Vec3Normalize(delta);
    /* IW4 0x67ffed..0x68009b: world aim direction expressed in the base frame
     * and converted back to angles. */
    AnglesToAxis(baseAngles, axis);
    axis_transpose_transform(delta, axis, local);
    vectoangles(local, aim);
    aim[0] = angle_normalize180(aim[0]);
    aim[1] = angle_normalize180(aim[1]);
    if (aim[0] < -info->turretVertSpanUp || aim[0] > info->turretVertSpanDown ||
        aim[1] < -info->turretHorizSpanRight || aim[1] > info->turretHorizSpanLeft) {
        Scr_AddInt(0);
        return;
    }
    if (!doTrace) { Scr_AddInt(1); return; }
    {
        trace_t trace;
        G_LocationalTrace(&trace, barrel, point, ent->s.number, TURRET_TARGET_TRACE_MASK, NULL);
        if (trace.fraction >= 1.0f) { Scr_AddInt(1); return; }
        if (trace.hitType == TRACE_HITTYPE_ENTITY && ignore != ENTITYNUM_NONE && trace.hitId == ignore) {
            Scr_AddInt(1);
            return;
        }
        Scr_AddInt(0);
    }
}

/* ------------------------------------------------------------------ */
/* vehicle damage callback and vehicle_finishdamage                    */
static int vehicle_damage_handle;
static int vehicle_damage_finishing;
void CODOL_VehicleDamage_LoadCallback(void)
{
    vehicle_damage_handle = Scr_GetFunctionHandle("maps/mp/gametypes/_callbacksetup", "CodeCallback_VehicleDamage");
}
int CODOL_VehicleDamageCallback(gentity_t *targ, gentity_t *inflictor, gentity_t *attacker,
    const float *dir, const float *point, int damage, int dflags, int mod, int weapon,
    int hitLoc, unsigned int modelIndex, unsigned int partName, int timeOffset)
{
    short thread;
    if (!targ || !targ->scr_vehicle || !vehicle_damage_handle || vehicle_damage_finishing) return 0;
    /* Script parameters are pushed last-first (Scr_PlayerKilled in
     * g_scr_main_mp.cpp): (inflictor, attacker, damage, dFlags, meansOfDeath,
     * weapon, point, dir, hitLoc, timeOffset, modelIndex, partName). */
    if (partName) Scr_AddConstString(partName); else Scr_AddString("");
    Scr_AddInt((int)modelIndex);
    Scr_AddInt(timeOffset);
    Scr_AddConstString(G_GetHitLocationString((enum hitLocation_t)(hitLoc >= 0 && hitLoc < HITLOC_NUM ? hitLoc : HITLOC_NONE)));
    Scr_AddVector(dir ? dir : vec3_origin);
    Scr_AddVector(point ? point : vec3_origin);
    Scr_AddString(weapon > 0 && BG_GetWeaponDef(weapon) ? BG_GetWeaponDef(weapon)->szInternalName : "none");
    if (mod >= 0 && mod < MOD_TABLE_ENTRIES) Scr_AddConstString(*modNames[mod]);
    else Scr_AddString("badMOD");
    Scr_AddInt(dflags);
    Scr_AddInt(damage);
    if (attacker) Scr_AddEntity(attacker); else Scr_AddUndefined();
    if (inflictor) Scr_AddEntity(inflictor); else Scr_AddUndefined();
    thread = Scr_ExecEntThread(targ, vehicle_damage_handle, 12);
    Scr_FreeThread(thread);
    return 1;
}
void CODOL_Scr_VehicleFinishDamage(scr_entref_t ref)
{
    gentity_t *ent = vehicle_receiver(ref, "vehicle_finishdamage");
    gentity_t *inflictor, *attacker;
    vec3_t point, dir;
    int damage, dflags, mod, weapon, hitLoc, timeOffset, modelIndex;
    unsigned int partName;
    if (!ent) return;
    if (Scr_GetNumParam() != 12) { Scr_Error("vehicle_finishdamage requires 12 arguments"); return; }
    /* IW4 0x67f4e1..0x67f540: undefined or non-entity inflictor/attacker
     * default to the world entity. */
    inflictor = &g_entities[ENTITYNUM_WORLD];
    attacker = &g_entities[ENTITYNUM_WORLD];
    if (Scr_GetType(0) == VAR_POINTER && Scr_GetPointerType(0) == VAR_ENTITY) inflictor = Scr_GetEntity(0);
    if (Scr_GetType(1) == VAR_POINTER && Scr_GetPointerType(1) == VAR_ENTITY) attacker = Scr_GetEntity(1);
    damage = Scr_GetInt(2);
    if (damage <= 0) return;
    dflags = Scr_GetInt(3);
    mod = G_MeansOfDeathFromScriptParam(4);
    weapon = G_GetWeaponIndexForName(Scr_GetString(5));
    Scr_GetVector(6, point);
    Scr_GetVector(7, dir);
    hitLoc = G_GetHitLocationIndexFromString((unsigned short)Scr_GetConstString(8));
    timeOffset = Scr_GetInt(9);
    modelIndex = Scr_GetInt(10);
    partName = (unsigned short)Scr_GetConstString(11);
    if (partName == scr_const.empty) partName = 0;
    if (!weapon && (unsigned short)Scr_GetConstString(5) != scr_const.none) {
        Scr_Error(va("weapon [%s] has not been precached", Scr_GetString(5)));
        return;
    }
    /* Retained G_Damage runs the vehicle immunity gate, the health change,
     * the "damage"/"death" notifies and the vehicle pain/die handlers. The
     * gate stops the callback dispatcher from re-entering script. */
    vehicle_damage_finishing = 1;
    G_Damage(ent, inflictor, attacker, dir, point, damage, dflags, mod, weapon, hitLoc,
             (unsigned int)modelIndex, partName, timeOffset);
    vehicle_damage_finishing = 0;
}

/* ------------------------------------------------------------------ */
/* vehicle turret control                                              */
static int turret_control_owner[VEHICLE_POOL]; /* player entity number + 1 */
void CODOL_VehicleTurretControl_Reset(void) { memset(turret_control_owner, 0, sizeof(turret_control_owner)); }
void CODOL_VehicleTurretControl_ClientLeft(int clientNum)
{
    unsigned i;
    for (i = 0; i < VEHICLE_POOL; ++i) if (turret_control_owner[i] == clientNum + 1) {
        unsigned number = level.vehicles ? level.vehicles[i].entNum : ENTITYNUM_NONE;
        if (number < ENTITYNUM_WORLD && g_entities[number].scr_vehicle == &level.vehicles[i] &&
            g_entities[number].scr_vehicle->boneIndex.riderSlots[GUNNER_RIDE_SLOT].entNum == clientNum)
            g_entities[number].scr_vehicle->boneIndex.riderSlots[GUNNER_RIDE_SLOT].entNum = ENTITYNUM_NONE;
        turret_control_owner[i] = 0;
    }
}
gentity_t *CODOL_VehicleTurretController(const gentity_t *vehicle)
{
    int slot = vehicle_pool_slot(vehicle);
    if (slot < 0 || !turret_control_owner[slot]) return NULL;
    return &g_entities[turret_control_owner[slot] - 1];
}
/* IW4's vehicle think drives a vehicleTurretControlOn turret from its
 * controller: the turret follows the controller's view and, while the attack
 * button is held and the refire delay (turret.fireTime, reloaded by
 * fireWeapon at _g_scr_vehicle.asm CMD_VEH_FireWeapon) has run out, the
 * vehicle is notified "turret_fire". IW4 _helicopter.gsc heliRide (and this
 * tree's copy) answers that notify with `chopper fireWeapon()`. The retained
 * helicopter think (Scr_Vehicle_Think) has neither step, so the chopper
 * gunner's gun never turned with his view and never fired. The retained
 * turret aim consumes the same target fields SetTurretTargetVec writes. */
_Static_assert(offsetof(scr_vehicle_s, turret) == 0x1d4, "native vehicle turret block moved");
_Static_assert(offsetof(scr_vehicle_s, hasTarget) == 0x268, "native vehicle turret has-target moved");
_Static_assert(offsetof(scr_vehicle_s, targetEnt) == 0x27c, "native vehicle turret target entity moved");
_Static_assert(offsetof(scr_vehicle_s, targetOrigin) == 0x284, "native vehicle turret target moved");
static int turret_control_last_think[VEHICLE_POOL];
void CODOL_VehicleTurretControllerThink(gentity_t *ent)
{
    gentity_t *player;
    scr_vehicle_s *vehicle;
    float tagMat[4][3], forward[3];
    int slot, elapsed;

    if (!ent || !ent->scr_vehicle) return;
    slot = vehicle_pool_slot(ent);
    if (slot < 0) return;
    vehicle = ent->scr_vehicle;
    elapsed = turret_control_last_think[slot] ? level.time - turret_control_last_think[slot] : 0;
    turret_control_last_think[slot] = level.time;
    player = CODOL_VehicleTurretController(ent);
    if (!player || !player->r.inuse || !player->client) return;
    if (vehicle->turret.fireTime > 0 && elapsed > 0) {
        vehicle->turret.fireTime -= elapsed;
        if (vehicle->turret.fireTime < 0) vehicle->turret.fireTime = 0;
    }
    /* Aim: a point far along the controller's view, from the tag the
     * weapon-view link renders it from (C1 CG 0x476280), else the vehicle. */
    if (!G_DObjGetWorldTagMatrix(ent, scr_const.tag_player, tagMat))
        VectorCopy(ent->r.currentOrigin, tagMat[3]);
    AngleVectors(player->client->ps.viewangles, forward, NULL, NULL);
    vehicle->hasTarget = 1;
    vehicle->targetEnt = ENTITYNUM_NONE;
    VectorMA(tagMat[3], 16384.0f, forward, vehicle->targetOrigin);
    VectorClear(vehicle->targetOffset);
    if ((player->client->buttons & 1) && vehicle->turret.fireTime <= 0)
        Scr_Notify(ent, scr_const.turret_fire, 0);
}
static gentity_t *client_argument(unsigned param)
{
    gentity_t *player;
    if (Scr_GetType(param) != VAR_POINTER || Scr_GetPointerType(param) != VAR_ENTITY) {
        Scr_ParamError(param, "Parameter must be a valid client");
        return NULL;
    }
    player = Scr_GetEntity(param);
    if (!player || !player->client) {
        Scr_ParamError(param, "Parameter must be a valid client");
        return NULL;
    }
    return player;
}
void CODOL_Scr_VehicleTurretControlOn(scr_entref_t ref)
{
    gentity_t *ent = vehicle_receiver(ref, "vehicleturretcontrolon");
    gentity_t *player;
    scr_vehicle_s *vehicle;
    int slot;
    if (!ent) return;
    player = client_argument(0);
    if (!player) return;
    vehicle = ent->scr_vehicle;
    slot = vehicle_pool_slot(ent);
    if (slot < 0) { Scr_Error("vehicleturretcontrolon: vehicle is not in the native vehicle pool"); return; }
    /* IW4 0x421d30: VEH_LinkCommonChecks rejects a player already using a
     * vehicle, then the vehicle's gunner ride slot is cleared when this
     * player was riding in it, and the vehicle records the controller. */
    if (player->r.ownerNum.number && player->r.ownerNum.number - 1 != ent->s.number) {
        Scr_Error("VEH_LinkCommonChecks: Player is already using a vehicle");
        return;
    }
    if (vehicle->boneIndex.riderSlots[GUNNER_RIDE_SLOT].entNum != ENTITYNUM_NONE &&
        vehicle->boneIndex.riderSlots[GUNNER_RIDE_SLOT].entNum != player->s.number &&
        turret_control_owner[slot] == 0) {
        Scr_Error("vehicleturretcontrolon: the vehicle's gunner seat is occupied");
        return;
    }
    /* The retained think reads ride slot 2's playerState for the gun angles
     * and its attack button for the turret fire; the controller takes that
     * slot without a bone link (its own link is scripted). */
    vehicle->boneIndex.riderSlots[GUNNER_RIDE_SLOT].entNum = player->s.number;
    turret_control_owner[slot] = player->s.number + 1;
}
void CODOL_Scr_VehicleTurretControlOff(scr_entref_t ref)
{
    gentity_t *ent = vehicle_receiver(ref, "vehicleturretcontroloff");
    gentity_t *player;
    scr_vehicle_s *vehicle;
    int slot;
    if (!ent) return;
    player = client_argument(0);
    if (!player) return;
    vehicle = ent->scr_vehicle;
    slot = vehicle_pool_slot(ent);
    if (slot < 0) { Scr_Error("vehicleturretcontroloff: vehicle is not in the native vehicle pool"); return; }
    if (turret_control_owner[slot] == player->s.number + 1) {
        if (vehicle->boneIndex.riderSlots[GUNNER_RIDE_SLOT].entNum == player->s.number)
            vehicle->boneIndex.riderSlots[GUNNER_RIDE_SLOT].entNum = ENTITYNUM_NONE;
        turret_control_owner[slot] = 0;
        return;
    }
    /* IW4 0x49a8f0..0x49a94c: a player who is not the controller must be
     * riding this vehicle, and is dismounted. */
    if (!player->r.ownerNum.number || player->r.ownerNum.number - 1 != ent->s.number) {
        Scr_Error("VEH_UnlinkPlayer: Vehicle is not player's owner");
        return;
    }
    G_VehUnlinkPlayer(ent, player);
}

/* ------------------------------------------------------------------ */
/* vehicle_dospawn                                                     */
static int spawner_last_spawn_time[MAX_GENTITIES];
static void install_vehicle_collision(gentity_t *entity)
{
    /* Per-spawn collmap lookup, the same rule as the retained
     * G_VehiclesSetupSpawnedEnts / CODOL_Scr_SpawnVehicle apply. */
    const char *model;
    int i;
    if (!entity->model) return;
    model = SL_ConvertToString(G_ModelName(entity->model));
    for (i = 0; i < level.num_entities; ++i) {
        gentity_t *candidate = &g_entities[i];
        if (!candidate->r.inuse || !candidate->classname ||
            Q_stricmp(SL_ConvertToString(candidate->classname), "script_vehicle_collmap") ||
            Q_stricmp(SL_ConvertToString(candidate->targetname), model)) continue;
        if (!candidate->s.index) {
            Com_PrintWarning(CON_CHANNEL_SERVER, "WARNING: Cannot use empty vehicle collmap for [%s]\n", model);
            return;
        }
        if (!CM_ClipHandleIsValid(candidate->s.index)) return;
        SV_UnlinkEntity(entity);
        entity->s.index = candidate->s.index;
        if (!SV_SetBrushModel(entity)) return;
        entity->r.contents = (entity->spawnflags & 1) ? 0xa00000 : 0x800000;
        SV_LinkEntity(entity);
        return;
    }
}
void CODOL_Scr_VehicleDoSpawn(scr_entref_t ref)
{
    gentity_t *spawner = entity_receiver(ref);
    const codol_vehicle_spawner_t *record;
    const codol_vehicle_native_t *definition;
    gentity_t *owner = NULL, *entity;
    const char *type = NULL, *model;
    int count, info;
    if (!spawner) return;
    record = CODOL_VehicleSpawner(spawner);
    if (!record) {
        const char *name = spawner->classname ? SL_ConvertToString(spawner->classname) : "<unnamed>";
        if (spawner->scr_vehicle)
            Scr_Error(va("Trying to call a vehicle spawner command on a vehicle.\nEntity '%s' at (%.0f %.0f %.0f)\n",
                name, spawner->r.currentOrigin[0], spawner->r.currentOrigin[1], spawner->r.currentOrigin[2]));
        else
            Scr_Error(va("Trying to call a vehicle spawner command on a non-script_vehicle entity.\nEntity '%s' at (%.0f %.0f %.0f)\n",
                name, spawner->r.currentOrigin[0], spawner->r.currentOrigin[1], spawner->r.currentOrigin[2]));
        return;
    }
    count = Scr_GetNumParam();
    if (count > 0 && Scr_GetType(0) != VAR_UNDEFINED) type = Scr_GetString(0);
    if (count > 1 && Scr_GetType(1) != VAR_UNDEFINED) {
        owner = client_argument(1);
        if (!owner) return;
    }
    /* IW4 0x420670: one vehicle per spawner per server frame. */
    if (spawner_last_spawn_time[spawner->s.number] == level.time && level.time) { Scr_AddUndefined(); return; }
    if (!type || !*type) type = CODOL_VehicleName(record->vehicle_slot);
    if (!type || !*type) { Scr_Error("vehicle spawner has no vehicle definition"); return; }
    info = CODOL_VehicleInfoForSpawn(type);
    definition = CODOL_NativeVehicleDefinition(info);
    if (!definition) { Scr_Error(va("vehicle_dospawn could not load vehicle definition '%s'", type)); return; }
    spawner_last_spawn_time[spawner->s.number] = level.time;
    entity = G_Spawn();
    /* IW4 0x4f34e0 / 0x4c8b10: the new entity takes the spawner's
     * template (classname, targetname, model, spawnflags without the
     * spawner bit) and position. */
    Scr_SetString(&entity->classname, spawner->classname);
    Scr_SetString(&entity->targetname, spawner->targetname);
    Scr_SetString(&entity->target, spawner->target);
    entity->spawnflags = spawner->spawnflags & ~2;
    model = spawner->model ? SL_ConvertToString(G_ModelName(spawner->model)) : "";
    if (*model) G_SetModel(entity, model);
    VectorCopy(spawner->r.currentOrigin, entity->r.currentOrigin);
    VectorCopy(spawner->r.currentAngles, entity->r.currentAngles);
    G_SetOrigin(entity, spawner->r.currentOrigin);
    G_SetAngle(entity, spawner->r.currentAngles);
    if (definition->type == 5) {
        G_SpawnHelicopter(entity, owner, type, model);
        entity->health = definition->health;
    } else SpawnVehicle(entity, type);
    CODOL_CaptureVehicleSpawnClient(entity, owner);
    install_vehicle_collision(entity);
    /* IW4 0x4206d9..0x4206ea: return the vehicle and notify the spawner. */
    Scr_AddEntity(entity);
    {
        unsigned spawned = SL_GetString("spawned", 0);
        if (spawned) {
            Scr_AddEntity(entity);
            Scr_Notify(spawner, (unsigned short)spawned, 1);
            SL_RemoveRefToString(spawned);
        }
    }
}

/* ------------------------------------------------------------------ */
/* player remote-view flags                                            */
static unsigned char ac130_active[MAX_CLIENTS];
static unsigned char remote_soundscape[MAX_CLIENTS];
int CODOL_PlayerAC130Active(int clientNum)
{
    return clientNum >= 0 && clientNum < MAX_CLIENTS && ac130_active[clientNum];
}
int CODOL_PlayerRemoteCameraSoundscape(int clientNum)
{
    return clientNum >= 0 && clientNum < MAX_CLIENTS && remote_soundscape[clientNum];
}
void CODOL_PlayerRemoteView_ResetClient(int clientNum)
{
    if (clientNum < 0 || clientNum >= MAX_CLIENTS) return;
    ac130_active[clientNum] = 0;
    remote_soundscape[clientNum] = 0;
}
void CODOL_PlayerRemoteView_ResetAll(void)
{
    memset(ac130_active, 0, sizeof(ac130_active));
    memset(remote_soundscape, 0, sizeof(remote_soundscape));
}
void CODOL_Scr_StartAC130(scr_entref_t ref)
{
    gentity_t *ent = player_receiver(ref, "startac130");
    if (ent && Scr_GetNumParam() == 0) ac130_active[ent->s.number] = 1;
    else if (ent) Scr_Error("startac130 takes no arguments");
}
void CODOL_Scr_StopAC130(scr_entref_t ref)
{
    gentity_t *ent = player_receiver(ref, "stopac130");
    if (ent && Scr_GetNumParam() == 0) ac130_active[ent->s.number] = 0;
    else if (ent) Scr_Error("stopac130 takes no arguments");
}
void CODOL_Scr_RemoteCameraSoundscapeOff(scr_entref_t ref)
{
    gentity_t *ent = player_receiver(ref, "remotecamerasoundscapeoff");
    if (ent && Scr_GetNumParam() == 0) remote_soundscape[ent->s.number] = 0;
    else if (ent) Scr_Error("remotecamerasoundscapeoff takes no arguments");
}

/* ------------------------------------------------------------------ */
/* turret solidity and minimap visibility                              */
void CODOL_Scr_MakeTurretSolid(scr_entref_t ref)
{
    gentity_t *ent = turret_receiver(ref, "maketurretsolid");
    if (!ent) return;
    /* IW4 0x4038e0. Its svFlags bit 4 has no measured retained meaning
     * (IW3's 4 is SVF_VISDUMMY) and is not copied. */
    ent->r.contents = (ent->r.contents & ~1) | TURRET_SOLID_CONTENTS;
    VectorSet(ent->r.mins, -TURRET_SOLID_HALF_XY, -TURRET_SOLID_HALF_XY, 0.0f);
    VectorSet(ent->r.maxs, TURRET_SOLID_HALF_XY, TURRET_SOLID_HALF_XY, TURRET_SOLID_HEIGHT);
    SV_LinkEntity(ent);
}
static unsigned char turret_minimap[MAX_GENTITIES];
int CODOL_TurretMinimapVisible(const gentity_t *turret)
{
    if (!turret || !turret->pTurretInfo) return 0;
    return turret_minimap[turret->s.number];
}
void CODOL_TurretMinimap_EntityFreed(unsigned entnum)
{
    if (entnum < MAX_GENTITIES) turret_minimap[entnum] = 0;
}
void CODOL_TurretMinimap_ResetAll(void) { memset(turret_minimap, 0, sizeof(turret_minimap)); }
void CODOL_Scr_SetTurretMinimapVisible(scr_entref_t ref)
{
    gentity_t *ent = turret_receiver(ref, "setturretminimapvisible");
    int visible;
    if (!ent) return;
    if (Scr_GetNumParam() != 1) { Scr_Error("setturretminimapvisible requires one argument"); return; }
    visible = Scr_GetInt(0) != 0;
    turret_minimap[ent->s.number] = (unsigned char)visible;
    /* IW4 keeps the flag in the entity state (0x4b1310). The CoDOL entity
     * overlay only translates the turret-fired bit today, so this stays a
     * native marker until C1's consumer is measured. */
    if (visible) ent->s.lerp.eFlags |= TURRET_MINIMAP_EFLAG;
    else ent->s.lerp.eFlags &= ~TURRET_MINIMAP_EFLAG;
}

/* ------------------------------------------------------------------ */
/* canplayerplacesentry                                                */
static void add_array_vector(const float *value, const char *key)
{
    unsigned index = SL_GetString(key, 0);
    Scr_AddVector(value);
    Scr_AddArrayStringIndexed(index);
    SL_RemoveRefToString(index);
}
/* IW4 0x4a99d0: from the eye-level point in front of the player, trace a
 * 2r box down to the player's foot height. The sentry origin is the hit
 * point lowered by the box radius; the hit must be world geometry with a
 * normal steeper than the minimum. */
static int sentry_ground_trace(const playerState_t *ps, const float *viewPos, vec3_t origin, vec3_t angles, vec3_t normal)
{
    vec3_t traceAngles, forward, start, end, mins, maxs;
    trace_t trace;
    float eyeHeight = viewPos[2] - ps->origin[2];
    VectorSet(traceAngles, SENTRY_TRACE_PITCH, ps->viewangles[1], 0.0f);
    AngleVectors(traceAngles, forward, NULL, NULL);
    VectorMA(viewPos, SENTRY_TRACE_RADIUS_CANON_SAFETY + SENTRY_TRACE_DIST, forward, start);
    VectorSet(end, start[0], start[1], start[2] - eyeHeight);
    VectorSet(mins, -SENTRY_TRACE_RADIUS, -SENTRY_TRACE_RADIUS, -SENTRY_TRACE_RADIUS);
    VectorSet(maxs, SENTRY_TRACE_RADIUS, SENTRY_TRACE_RADIUS, SENTRY_TRACE_RADIUS);
    G_TraceCapsule(&trace, start, mins, maxs, end, ps->clientNum, SENTRY_TRACE_MASK);
    VectorSubtract(end, start, end);
    VectorMA(start, trace.fraction, end, origin);
    VectorSet(angles, 0.0f, ps->viewangles[1], 0.0f);
    if (trace.startsolid || trace.allsolid) {
        if (com_developer && com_developer->integer) {
            static int lastSolidReport;
            if (level.time - lastSolidReport >= 1000 || level.time < lastSolidReport) {
                lastSolidReport = level.time;
                Com_DPrintf(CON_CHANNEL_SCRIPT, "CoDOL canplayerplacesentry ground trace starts solid: start (%.1f %.1f %.1f) drop %.1f startsolid %d allsolid %d hitType %d hitId %d cflags 0x%x sflags 0x%x\n",
                    start[0], start[1], start[2], end[2], (int)trace.startsolid, (int)trace.allsolid, (int)trace.hitType, (int)trace.hitId, (unsigned)trace.cflags, (unsigned)trace.sflags);
            }
        }
        origin[2] = ps->origin[2]; return 0;
    }
    /* IW4 accepts only world geometry here. This engine's G_TraceCapsule
     * reports a world hit as hitType ENTITY with hitId ENTITYNUM_WORLD, not
     * as NONE (measured 2026-09-24: floor hits read 1/2046). Testing for NONE
     * alone refused every spot, so no sentry or SAM could ever be placed. */
    if (trace.fraction >= 1.0f ||
        !(trace.hitType == TRACE_HITTYPE_NONE ||
          (trace.hitType == TRACE_HITTYPE_ENTITY && trace.hitId == ENTITYNUM_WORLD)) ||
        trace.normal[2] < SENTRY_TRACE_MIN_NORMAL) {
        if (com_developer && com_developer->integer) {
            static int lastReport;
            if (level.time - lastReport >= 1000 || level.time < lastReport) {
                lastReport = level.time;
                Com_DPrintf(CON_CHANNEL_SCRIPT, "CoDOL canplayerplacesentry ground trace: fraction %.3f hitType %d hitId %d normal (%.2f %.2f %.2f)\n",
                    trace.fraction, (int)trace.hitType, (int)trace.hitId, trace.normal[0], trace.normal[1], trace.normal[2]);
            }
        }
        return 0;
    }
    origin[2] -= SENTRY_TRACE_RADIUS;
    VectorCopy(trace.normal, normal);
    /* IW4 0x4a9c46..0x4a9cad: the facing is the yaw direction projected onto
     * the ground plane, (n x f) x n. */
    {
        vec3_t left, projected;
        CrossProduct(normal, forward, left);
        CrossProduct(left, normal, projected);
        if (Vec3Normalize(projected) > 0.0f) vectoangles(projected, angles);
    }
    return 1;
}
/* IW4 0x681180: four feet at (+-x, +-y, +z) in the sentry frame are traced
 * feet_trace_dist_z along -up; every foot must find ground, the origin
 * follows the feet and the pitch/roll come from the foot height pairs. The
 * exact IW4 accept condition beyond "all feet touch" was not decoded. */
static int sentry_feet(int passEntityNum, vec3_t origin, vec3_t angles)
{
    float axis[3][3];
    float height[4];
    vec3_t foot, end;
    unsigned i;
    float front, back, right, left, drop;
    AnglesToAxis(angles, axis);
    for (i = 0; i < 4; ++i) {
        float sx = (i & 1) ? -SENTRY_FEET_OFFSET_X : SENTRY_FEET_OFFSET_X;
        float sy = (i & 2) ? -SENTRY_FEET_OFFSET_Y : SENTRY_FEET_OFFSET_Y;
        trace_t trace;
        VectorMA(origin, sx, axis[0], foot);
        VectorMA(foot, sy, axis[1], foot);
        VectorMA(foot, SENTRY_FEET_OFFSET_Z, axis[2], foot);
        VectorMA(foot, -SENTRY_FEET_TRACE_DIST_Z, axis[2], end);
        G_LocationalTrace(&trace, foot, end, passEntityNum, SENTRY_TRACE_MASK, NULL);
        if (trace.fraction >= 1.0f) return 0;
        /* Height of the ground under this foot relative to the sentry base. */
        height[i] = SENTRY_FEET_OFFSET_Z - SENTRY_FEET_TRACE_DIST_Z * trace.fraction;
    }
    drop = 0.25f * (height[0] + height[1] + height[2] + height[3]);
    VectorMA(origin, drop, axis[2], origin);
    front = 0.5f * (height[0] + height[2]);
    back = 0.5f * (height[1] + height[3]);
    right = 0.5f * (height[2] + height[3]);
    left = 0.5f * (height[0] + height[1]);
    angles[0] = angles[0] - (float)(atan2((double)(front - back), (double)(2.0f * SENTRY_FEET_OFFSET_X)) * (180.0 / M_PI));
    angles[2] = angles[2] + (float)(atan2((double)(right - left), (double)(2.0f * SENTRY_FEET_OFFSET_Y)) * (180.0 / M_PI));
    return 1;
}
void CODOL_Scr_CanPlayerPlaceSentry(scr_entref_t ref)
{
    gentity_t *ent = player_receiver(ref, "canplayerplacesentry");
    playerState_t *ps;
    vec3_t viewPos, origin, angles, normal;
    int result;
    if (!ent) return;
    if (Scr_GetNumParam() != 0) { Scr_Error("canplayerplacesentry takes no arguments"); return; }
    ps = &ent->client->ps;
    /* IW4 0x47ec30 builds the reach point from the view origin with lean
     * and bob; the retained G_GetPlayerViewOrigin is that producer here. */
    G_GetPlayerViewOrigin(ps, viewPos);
    if (viewPos[2] > ps->origin[2] + 60.0f) viewPos[2] = ps->origin[2] + 60.0f;
    result = sentry_ground_trace(ps, viewPos, origin, angles, normal);
    {
        int ground = result;
        if (result) result = sentry_feet(ent->s.number, origin, angles);
        /* Developer trace, at most once a second: which stage refused. */
        if (!result && com_developer && com_developer->integer) {
            static int lastReport;
            if (level.time - lastReport >= 1000 || level.time < lastReport) {
                lastReport = level.time;
                Com_DPrintf(CON_CHANNEL_SCRIPT, "CoDOL canplayerplacesentry: client %d refused at %s stage, origin (%.1f %.1f %.1f) view z %.1f foot z %.1f\n",
                    ps->clientNum, ground ? "feet" : "ground-trace", origin[0], origin[1], origin[2], viewPos[2], ps->origin[2]);
            }
        }
    }
    /* IW4 0x5dcaf6..0x5dcb3c: array with "result", "origin", "angles". */
    Scr_MakeArray();
    {
        unsigned key = SL_GetString("result", 0);
        Scr_AddBool(result != 0);
        Scr_AddArrayStringIndexed(key);
        SL_RemoveRefToString(key);
    }
    add_array_vector(origin, "origin");
    add_array_vector(angles, "angles");
}
#endif
