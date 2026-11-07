/* Native combat/killstreak support builtins for the CoDOL server.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Implements, on top of the retained IW3 combat path (G_Damage, CanDamage,
 * G_RunItem, G_EntAttach/G_EntDetach, MissileTrajectory target state):
 *
 *   missile_settargetent / missile_settargetpos   (rocket methods, IW4)
 *   glassradiusdamage                              (function, IW4/T5)
 *   setcanradiusdamage                             (entity method, IW4)
 *   physicslaunchserver                            (script_model method, IW4)
 *   attachshieldmodel / detachshieldmodel / moveshieldmodel (player, IW4)
 *   codol_fire_nearest / codol_radiusdamage        (CoDOL overlay functions)
 *
 * Provenance per builtin is recorded next to its implementation. Nothing in
 * this file is runtime verified; see the worker report and
 * docs/CODOL_IMPLEMENTATION_PASS.json for the review state. */
#ifdef CODOL_SERVER
#include "codol_script_combat_builtins.h"
#include "codol_playerstate_ext.h"
#include "codol_glass_world.h"
#include "scr_vm_functions.h"
#include "g_shared.h"
#include "entity.h"
#include "player.h"
#include "server.h"
#include "cscr_stringlist.h"
#include "codol_weapon_lock.h"
#include "codol_radius_distance.h"
#include "bg_public.h"
#include "q_math.h"
#include "cvar.h"
#include "qcommon_io.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>

/* Retained assembly exports that no shared header declares. Signatures come
 * from the retained listings (src/asmsource/_g_utils_mp.asm,
 * _g_combat_mp.asm, _scr_vm.asm); keep them local to this file. */
extern int G_EntAttach(gentity_t *ent, const char *modelName, unsigned int tagName, int ignoreCollision);
extern int G_EntDetach(gentity_t *ent, const char *modelName, unsigned int tagName);
extern unsigned int Scr_GetConstLowercaseString(unsigned int index);
/* CanDamage(target, inflictor, origin, coneAngleCos, coneDir, contentmask):
 * fraction (0..1) of the retained sample points visible from origin. */
extern float CanDamage(gentity_t *target, gentity_t *inflictor, const float *origin,
    float coneAngleCos, float *coneDir, int contentmask);
extern void G_Damage(gentity_t *targ, gentity_t *inflictor, gentity_t *attacker,
    const float *dir, const float *point, int damage, int dflags, int mod, int weapon,
    int hitLoc, unsigned int modelIndex, unsigned int partName, int timeOffset);

/* Retained means-of-death table indices (src/g_combat_mp.cpp modNames order;
 * the enum in g_shared.h is commented out). GScr_RadiusDamageInternal passes
 * 0xe (MOD_EXPLOSIVE) as its default. */
enum {
    CODOL_MOD_RIFLE_BULLET = 2,
    CODOL_MOD_EXPLOSIVE = 14,
    CODOL_MOD_COUNT = NATIVE_DAMAGE_MOD_COUNT
};

/* T5 player-only poisoning methods; C1 renders the same owned boolean at
 * ps+59c (CG_UpdatePoisonFX4775a4). Never look up a live client's value while
 * serializing an archived/spectator playerState. */
static codol_ps_ext_t *poison_state(scr_entref_t ref)
{
    codol_ps_ext_t *ext;
    if(ref.classnum || ref.entnum>=MAX_GENTITIES ||
       !g_entities[ref.entnum].r.inuse || !g_entities[ref.entnum].client) {
        Scr_ObjectError("Must be called on a client"); return NULL;
    }
    ext=CODOL_PlayerStateExt(&g_entities[ref.entnum].client->ps);
    if(!ext) Scr_Error("player poison state storage is unavailable");
    return ext;
}
void CODOL_Scr_StartPoisoning(scr_entref_t ref)
{
    codol_ps_ext_t *ext=poison_state(ref);
    if(ext) ext->poisoned=1;
}
void CODOL_Scr_StopPoisoning(scr_entref_t ref)
{
    codol_ps_ext_t *ext=poison_state(ref);
    if(ext) ext->poisoned=0;
}
void CODOL_Scr_IsPoisoned(scr_entref_t ref)
{
    codol_ps_ext_t *ext=poison_state(ref);
    if(ext) Scr_AddBool(ext->poisoned!=0);
}
/* GScr_RadiusDamageInternal -> G_RadiusDamage -> G_Damage passes dflags 5 and
 * uses this CanDamage content mask (retained _g_combat_mp.asm). */
#define CODOL_RADIUS_DAMAGE_DFLAGS 5
#define CODOL_CANDAMAGE_CONTENTMASK 0x802011
#define CODOL_RADIUS_DIR_LIFT 24.0f

/* ------------------------------------------------------------------ */
/* Shared helpers                                                      */
/* ------------------------------------------------------------------ */

static int optional_param_defined(unsigned index)
{
    return (unsigned)Scr_GetNumParam()>index && Scr_GetType(index)!=VAR_UNDEFINED;
}

/* Means-of-death string parameter -> retained table index. */
static int mod_from_param(unsigned index, int fallback)
{
    unsigned short name;
    int i;
    if(!optional_param_defined(index)) return fallback;
    name=(unsigned short)Scr_GetConstString(index);
    for(i=0;i<CODOL_MOD_COUNT;++i) if(modNames[i] && *modNames[i]==name) return i;
    Scr_ParamError(index,va("unknown means of death '%s'",SL_ConvertToString(name)));
    return fallback;
}

/* OpenBLOPS MP ScrCmd_DoDamage: dispatch through authoritative G_Damage,
 * including its script damage/death callbacks. This is the MP positional
 * contract, not the different SP destructible-piece argument contract.
 * Native destructible piece damage remains a separate subsystem requirement;
 * current script-model destructibles receive their existing damage callback. */
void CODOL_Scr_DoDamage(scr_entref_t ref)
{
    unsigned argc=Scr_GetNumParam();
    gentity_t *target,*attacker=NULL,*inflictor=NULL;
    vec3_t source,direction;
    const float *origin,*dir;
    float damage;
    int weapon=-1,flags=0,mod=0,hitloc=HITLOC_HEAD,i;
    if(argc<2 || argc>8) {
        Scr_Error("Usage: doDamage(damage, source [, attacker, inflictor, headshot, mod, flags, weapon])");
        return;
    }
    if(argc>=8) weapon=G_GetWeaponIndexForName(Scr_GetString(7));
    if(argc>=7) flags=Scr_GetInt(6);
    if(argc>=6) {
        /* Supplied undefined is a type error, unlike an omitted argument. */
        unsigned name=Scr_GetConstString(5);
        for(mod=0;mod<NATIVE_DAMAGE_MOD_COUNT;++mod)
            if(modNames[mod] && *modNames[mod]==name) break;
        if(mod==NATIVE_DAMAGE_MOD_COUNT) {
            Scr_ParamError(5,va("unknown means of death '%s'",SL_ConvertToString(name)));
            return;
        }
    }
    if(argc>=5 && !Scr_GetInt(4)) hitloc=HITLOC_NONE;
    if(argc>=4) inflictor=Scr_GetEntity(3);
    if(argc>=3) attacker=Scr_GetEntity(2);
    Scr_GetVector(1,source);
    damage=Scr_GetFloat(0);
    if(ref.classnum || ref.entnum>=MAX_GENTITIES) {
        Scr_ObjectError("not an entity"); return;
    }
    target=&g_entities[ref.entnum];
    if(!target->r.inuse) { Scr_ObjectError("entity is not in use"); return; }
    for(i=0;i<3;++i) if(!isfinite(source[i])) {
        Scr_ParamError(1,"source damage vector is not finite"); return;
    }
    /* Avoid undefined float-to-int conversion on malformed script input. */
    if(!isfinite(damage) || (double)damage>INT_MAX || (double)damage<INT_MIN) {
        Scr_ParamError(0,"damage is outside the native integer range"); return;
    }
    origin=target->client ? target->client->ps.origin : target->r.currentOrigin;
    for(i=0;i<3;++i) direction[i]=origin[i]-source[i];
    /* T5 ScrCmd_DoDamage (OpenBLOPS g_scr_main_mp.cpp) substitutes straight up
     * for a zero-length direction. Passing NULL instead crashed the server:
     * the retained G_Damage normalizes dir whenever an attacker is given
     * (G_Damage_60 -> Vec3NormalizeTo), so doDamage from the target's own
     * origin was an access violation reading 0x0 (measured 2026-09-24). */
    if(Vec3Normalize(direction)==0.0f) {
        direction[0]=0.0f; direction[1]=0.0f; direction[2]=1.0f;
    }
    dir=direction;
    G_Damage(target,inflictor,attacker,dir,source,(int)damage,flags,mod,weapon,
        hitloc,0,0,0);
}

/* Weapon name -> index; unknown names fall back to the retained radiusdamage
 * default (-1), which the retained G_Damage path already accepts. */
static int weapon_from_param(unsigned index)
{
    const char *name;
    int weapon;
    if(!optional_param_defined(index)) return -1;
    name=Scr_GetString(index);
    weapon=G_GetWeaponIndexForName(name);
    return weapon ? weapon : -1;
}

static gentity_t *owner_from_param(unsigned index)
{
    gentity_t *owner=NULL;
    if(optional_param_defined(index)) owner=Scr_GetEntity(index);
    return owner ? owner : &g_entities[ENTITYNUM_WORLD];
}

static team_t entity_team(const gentity_t *ent)
{
    if(ent->client) return ent->client->sess.cs.team;
    return (team_t)ent->team;
}

static int player_alive(const gentity_t *ent)
{
    return ent->r.inuse && ent->client &&
        ent->client->sess.sessionState==SESS_STATE_PLAYING && ent->health>0;
}

/* Overlay semantics (_codol.gsc header, gscbuiltins.py _enemy): the owner
 * never hurts itself, and an allies/axis owner never hurts its own team.
 * World-owned strikes hit everyone. */
static int overlay_may_damage(const gentity_t *owner, const gentity_t *victim)
{
    team_t ownerTeam;
    if(victim==owner) return 0;
    if(owner->s.number==ENTITYNUM_WORLD) return 1;
    ownerTeam=entity_team(owner);
    if(ownerTeam!=TEAM_RED && ownerTeam!=TEAM_BLUE) return 1;
    return entity_team(victim)!=ownerTeam;
}

static float linear_falloff(float maxDamage, float minDamage, float distance, float radius)
{
    /* GScr/G_RadiusDamage: min + (1 - d/r) * (max - min). */
    return minDamage+(1.0f-distance/radius)*(maxDamage-minDamage);
}

/* ------------------------------------------------------------------ */
/* setcanradiusdamage                                                   */
/* ------------------------------------------------------------------ */

int CODOL_EntityCanRadiusDamage(const gentity_t *ent)
{
    return ent && !(ent->flags&CODOL_FL_NO_RADIUS_DAMAGE);
}

/* IW4 method (common_scripts/_pipes.gsc: SetCanRadiusDamage(false) as an
 * optimization next to SetCanDamage(true)). Stored as an entity flag so
 * radius producers can skip the entity; G_FreeEntity's memset resets it. */
void CODOL_Scr_SetCanRadiusDamage(scr_entref_t ref)
{
    gentity_t *ent=VM_GetGEntityForEntRef(ref);
    if(!ent) return;
    if(Scr_GetNumParam()!=1) {
        Scr_Error("Usage: <entity> SetCanRadiusDamage( <boolean> )");
        return;
    }
    if(Scr_GetInt(0)) ent->flags&=~CODOL_FL_NO_RADIUS_DAMAGE;
    else ent->flags|=CODOL_FL_NO_RADIUS_DAMAGE;
}

/* ------------------------------------------------------------------ */
/* missile_settargetent / missile_settargetpos                          */
/* ------------------------------------------------------------------ */

/* Retained GScr_MissileSetTarget and IW4 "Entity %i is not a rocket" check
 * the classname only. */
static gentity_t *rocket_receiver(scr_entref_t ref)
{
    gentity_t *ent=VM_GetGEntityForEntRef(ref);
    if(!ent) return NULL;
    if(ent->classname!=scr_const.rocket) {
        Scr_Error(va("Entity %i is not a rocket",ent->s.number));
        return NULL;
    }
    return ent;
}

/* IW4 Missile_SetTargetEnt(<entity> [, <offset>]). Same state the retained
 * missile_settarget writes: the outer missileTargetEnt handle, the native
 * offset at missile.targetOffset, and the CoDOL persistent lock flag (an
 * explicit entity target replaces any point target so MissileTrajectory
 * stops following a stale absolute point). Velocity, flight mode and stage
 * are preserved, as with missile_cleartarget. */
void CODOL_Scr_MissileSetTargetEnt(scr_entref_t ref)
{
    gentity_t *ent=rocket_receiver(ref);
    gentity_t *target=NULL;
    if(!ent) return;
    if(Scr_GetNumParam()<1 || Scr_GetNumParam()>2) {
        Scr_Error("Usage: <missile> Missile_SetTargetEnt( <target entity> [, <offset>] )");
        return;
    }
    if(Scr_GetType(0)!=VAR_UNDEFINED) target=Scr_GetEntity(0);
    if(target && !target->r.inuse) target=NULL;
    CODOL_EntHandleSetEnt(&ent->missileTargetEnt,target);
    CODOL_SetMissileEntityTarget((unsigned)ent->s.number,target!=NULL);
    if(Scr_GetNumParam()==2) Scr_GetVector(1,ent->missile.targetOffset);
    else VectorClear(ent->missile.targetOffset);
}

/* IW4 Missile_SetTargetPos(<position>) (_ac130.gsc: retarget to a point far
 * above the plane when the gunner leaves). Uses the CoDOL absolute point
 * target that MissileTrajectory already consumes for point weapon locks
 * (codol_weapon_lock_missile.c), clearing any entity target. */
void CODOL_Scr_MissileSetTargetPos(scr_entref_t ref)
{
    gentity_t *ent=rocket_receiver(ref);
    unsigned number;
    vec3_t pos;
    if(!ent) return;
    if(Scr_GetNumParam()!=1) {
        Scr_Error("Usage: <missile> Missile_SetTargetPos( <position> )");
        return;
    }
    Scr_GetVector(0,pos);
    number=(unsigned)ent->s.number;
    if(number>=ENTITYNUM_WORLD) {
        Scr_ObjectError("missile entity index out of range");
        return;
    }
    CODOL_EntHandleSetEnt(&ent->missileTargetEnt,NULL);
    CODOL_ResetMissilePosition(number);
    VectorCopy(pos,codol_missile_positions[number]);
    codol_missile_position_active[number]=1;
    codol_missile_lock_active[number]=1;
    VectorClear(ent->missile.targetOffset);
}

/* ------------------------------------------------------------------ */
/* Glass piece store and glassradiusdamage                              */
/* ------------------------------------------------------------------ */

/* Real map-backed glass store is shared with native bullet/explosion producers. */
void CODOL_Scr_GlassRadiusDamage(void)
{
    vec3_t origin;
    float radius,maximum,minimum;
    if (Scr_GetNumParam()!=4) { Scr_Error("glassradiusdamage requires origin, radius, maximum and minimum"); return; }
    Scr_GetVector(0,origin);radius=Scr_GetFloat(1);maximum=Scr_GetFloat(2);minimum=Scr_GetFloat(3);
    if (!isfinite(radius) || radius<=0) { Scr_ParamError(1,"glass radius must be finite and positive"); return; }
    if (!isfinite(maximum) || maximum<0) { Scr_ParamError(2,"maximum glass damage must be finite and nonnegative"); return; }
    if (!isfinite(minimum) || minimum<0 || minimum>maximum) { Scr_ParamError(3,"minimum glass damage must be between zero and maximum"); return; }
    CODOL_GlassExplosionDamage(origin,maximum,minimum,radius,-1.0f,NULL);
}

/* ------------------------------------------------------------------ */
/* physicslaunchserver                                                  */
/* ------------------------------------------------------------------ */

#define CODOL_PHYSICS_MAX_CHILDREN 8

#pragma pack(push, 8)
typedef struct {
    int active;
    int useCount;      /* gentity_t.useCount at launch: reuse detection */
    int launchTime;
    int restStartTime;
    float lastOrigin[3];
    int passOverridden;   /* ownerNum was replaced by the release carrier */
    int savedOwner;       /* entity ownerNum named before (-1 none) ... */
    int savedOwnerUseCount; /* ... and its useCount, to detect reuse */
    int contentsCleared;  /* r.contents was cleared for the flight */
    int savedContents;    /* r.contents to restore when the launch ends */
    int childCount;       /* linked children whose contents were cleared */
    unsigned short childNumber[CODOL_PHYSICS_MAX_CHILDREN];
    int childUseCount[CODOL_PHYSICS_MAX_CHILDREN];
    int childContents[CODOL_PHYSICS_MAX_CHILDREN];
} codol_physics_launch_t;
#pragma pack(pop)

static codol_physics_launch_t physics_launches[MAX_GENTITIES];

/* Rest detection: no measurable motion for this long. The retained
 * G_RunItem parks a landed item through a 50 ms TR_LINEAR_STOP, so this is
 * several frames past that. The hard timeout bounds an item that keeps
 * sliding on geometry it cannot settle on. */
#define CODOL_PHYSICS_REST_MS 250
#define CODOL_PHYSICS_MIN_FLIGHT_MS 100
#define CODOL_PHYSICS_TIMEOUT_MS 30000
#define CODOL_PHYSICS_MAX_SPIN 720.0f

void CODOL_ResetPhysicsLaunches(void)
{
    memset(physics_launches,0,sizeof(physics_launches));
}

static void physics_launch_notify(gentity_t *ent)
{
    unsigned notify=SL_GetString("physics_finished",0);
    if(!notify) return;
    Scr_Notify(ent,(unsigned short)notify,0);
    SL_RemoveRefToString(notify);
}

/* Put back the owner handle and contents PhysicsLaunchServer borrowed for
 * the flight. Every end of a launch goes through here, notified or not. */
static void physics_launch_restore_owner(codol_physics_launch_t *launch, gentity_t *ent)
{
    int same=ent->r.inuse && ent->useCount==launch->useCount,i;
    /* EntHandles are registered with the entity they name (enthandle.cpp
     * AddEntHandleInfo), so the owner goes back through setEnt, never by
     * copying the handle. */
    if(launch->passOverridden && same) {
        gentity_t *owner=NULL;
        if(launch->savedOwner>=0 && g_entities[launch->savedOwner].r.inuse &&
           g_entities[launch->savedOwner].useCount==launch->savedOwnerUseCount)
            owner=&g_entities[launch->savedOwner];
        CODOL_EntHandleSetEnt(&ent->r.ownerNum,owner);
    }
    if(launch->contentsCleared && same) {
        ent->r.contents=launch->savedContents;
        SV_LinkEntity(ent);
    }
    for(i=0;i<launch->childCount;++i) {
        gentity_t *child=&g_entities[launch->childNumber[i]];
        if(child->r.inuse && child->useCount==launch->childUseCount[i] && !child->r.contents) {
            child->r.contents=launch->childContents[i];
            SV_LinkEntity(child);
        }
    }
    launch->childCount=0;
    launch->passOverridden=0;
    launch->contentsCleared=0;
}

/* What rides on the object: the crate's team-coloured
 * com_plasticcase_friendly/_enemy models are linkTo'd to it
 * (_airdrop.gsc deleteOnOwnerDeath, 0.25 s after the crate spawns, so for
 * the C-130 drop only AFTER the launch) and share its bounds exactly. A
 * trace does not skip an entity's own children, and G_RunItem frees an item
 * whose move starts solid - MEASURED: every emergency-airdrop crate freed
 * 234 ms into its fall, the frame its first child linked. Clear the
 * contents of each rider while the object flies and give them back when it
 * lands. Riders attached mid-flight are caught at the next frame; one
 * linked by a script thread that runs before this frame's entity pass is
 * not, which is why _airdrop.gsc also makes its purely visual riders
 * non-solid. */
static void physics_launch_clear_children(codol_physics_launch_t *launch, gentity_t *ent)
{
    gentity_t *child;
    int i,known;
    for(child=ent->tagChildren;child && child->tagInfo;child=child->tagInfo->next) {
        if(!child->r.contents) continue;
        for(known=0,i=0;i<launch->childCount;++i)
            if(launch->childNumber[i]==child->s.number && launch->childUseCount[i]==child->useCount) known=1;
        if(known) continue;
        if(launch->childCount>=CODOL_PHYSICS_MAX_CHILDREN) break;
        launch->childNumber[launch->childCount]=(unsigned short)child->s.number;
        launch->childUseCount[launch->childCount]=child->useCount;
        launch->childContents[launch->childCount]=child->r.contents;
        ++launch->childCount;
        child->r.contents=0;
        SV_LinkEntity(child);
    }
}

static void physics_launch_settle(gentity_t *ent, int time)
{
    vec3_t angles;
    ent->s.lerp.pos.trType=TR_STATIONARY;
    ent->s.lerp.pos.trTime=time;
    ent->s.lerp.pos.trDuration=0;
    VectorCopy(ent->r.currentOrigin,ent->s.lerp.pos.trBase);
    VectorClear(ent->s.lerp.pos.trDelta);
    if(ent->s.lerp.apos.trType!=TR_STATIONARY) {
        BG_EvaluateTrajectory(&ent->s.lerp.apos,time,angles);
        ent->s.lerp.apos.trType=TR_STATIONARY;
        ent->s.lerp.apos.trTime=time;
        ent->s.lerp.apos.trDuration=0;
        VectorClear(ent->s.lerp.apos.trDelta);
        G_SetAngle(ent,angles);
    }
    ent->physicsObject=0;
    SV_LinkEntity(ent);
    physics_launch_notify(ent);
}

void CODOL_RunPhysicsLaunchFrame(int time)
{
    unsigned i;
    for(i=0;i<MAX_GENTITIES;++i) {
        codol_physics_launch_t *launch=&physics_launches[i];
        gentity_t *ent=&g_entities[i];
        if(!launch->active) continue;
        /* Freed/reused, re-linked by script, or physics cleared elsewhere:
         * the launch is over without a notification, as the entity is no
         * longer the object that was launched. */
        if(!ent->r.inuse || ent->useCount!=launch->useCount || !ent->physicsObject || ent->tagInfo) {
            if(CODOL_TRACE_VERBOSE())
                Com_Printf(CON_CHANNEL_SERVER,"CoDOL physics launch: entity %u ended without settling after %d ms (inuse %d physics %d linked %d)\n",
                    i,time-launch->launchTime,ent->r.inuse,ent->physicsObject,ent->tagInfo!=NULL);
            physics_launch_restore_owner(launch,ent);
            launch->active=0;
            continue;
        }
        physics_launch_clear_children(launch,ent);
        if(Vec3DistanceSq(ent->r.currentOrigin,launch->lastOrigin)>0.01) {
            VectorCopy(ent->r.currentOrigin,launch->lastOrigin);
            launch->restStartTime=time;
            if(time-launch->launchTime<CODOL_PHYSICS_TIMEOUT_MS) continue;
        } else if(time-launch->restStartTime<CODOL_PHYSICS_REST_MS ||
                  time-launch->launchTime<CODOL_PHYSICS_MIN_FLIGHT_MS) {
            continue;
        }
        launch->active=0;
        physics_launch_restore_owner(launch,ent);
        physics_launch_settle(ent,time);
    }
}

/* IW4 <script_model> PhysicsLaunchServer(<contact point>, <force>)
 * (_airdrop.gsc: crate released from the plane; af_chase_code.gsc:
 * boat debris). IW4 hands the object to its server rigid-body simulation
 * and raises "physics_finished" when it comes to rest. This server has no
 * rigid-body solver; the launch uses the retained physicsObject path
 * (G_RunFrameForEntity -> G_RunItem: gravity trajectory, capsule trace
 * against the entity's clipmask, bounce/slide, rest parking), and the frame
 * function above raises the notification once the object stops moving.
 * The force is applied as an initial velocity for a unit-mass body; the
 * contact-point lever arm only adds a bounded angular velocity. */
void CODOL_Scr_PhysicsLaunchServer(scr_entref_t ref)
{
    gentity_t *ent=VM_GetGEntityForEntRef(ref);
    codol_physics_launch_t *launch;
    vec3_t point, force, lever, torque, extent;
    float inertia;
    unsigned number;
    if(!ent) return;
    number=(unsigned)ent->s.number;
    if(ent->classname!=scr_const.script_model) {
        Scr_ObjectError(va("Entity %i is not a script_model",number));
        return;
    }
    if(Scr_GetNumParam()!=2) {
        Scr_Error("Usage: <script_model> PhysicsLaunchServer( <contact point>, <force> )");
        return;
    }
    if(ent->tagInfo) {
        Scr_ObjectError(va("Entity %i is linked; unlink it before PhysicsLaunchServer",number));
        return;
    }
    Scr_GetVector(0,point);
    Scr_GetVector(1,force);

    ent->s.lerp.pos.trType=TR_GRAVITY;
    ent->s.lerp.pos.trTime=level.time;
    ent->s.lerp.pos.trDuration=0;
    VectorCopy(ent->r.currentOrigin,ent->s.lerp.pos.trBase);
    VectorCopy(force,ent->s.lerp.pos.trDelta);

    /* Angular velocity from the lever arm, if the contact point is not the
     * origin sentinel the airdrop passes. Inertia ~ (half extent)^2 for a
     * unit mass; spin is clamped so a small crate impulse cannot tumble. */
    VectorSubtract(point,ent->r.currentOrigin,lever);
    VectorCopy(ent->r.currentAngles,ent->s.lerp.apos.trBase);
    ent->s.lerp.apos.trTime=level.time;
    ent->s.lerp.apos.trDuration=0;
    if(point[0]==0.0f && point[1]==0.0f && point[2]==0.0f) {
        ent->s.lerp.apos.trType=TR_STATIONARY;
        VectorClear(ent->s.lerp.apos.trDelta);
    } else {
        int i;
        CrossProduct(lever,force,torque);
        VectorSubtract(ent->r.maxs,ent->r.mins,extent);
        inertia=0.25f*DotProduct(extent,extent);
        if(inertia<1.0f) inertia=1.0f;
        for(i=0;i<3;++i) {
            float spin=torque[i]/inertia;
            if(spin>CODOL_PHYSICS_MAX_SPIN) spin=CODOL_PHYSICS_MAX_SPIN;
            else if(spin<-CODOL_PHYSICS_MAX_SPIN) spin=-CODOL_PHYSICS_MAX_SPIN;
            ent->s.lerp.apos.trDelta[i]=spin;
        }
        ent->s.lerp.apos.trType=DotProduct(ent->s.lerp.apos.trDelta,ent->s.lerp.apos.trDelta)>0.0f ?
            TR_LINEAR : TR_STATIONARY;
    }

    /* G_RunItem substitutes its default mask (0x491) for a zero clipmask and
     * clears the ground entity so the first trace does not skip the floor. */
    ent->s.groundEntityNum=ENTITYNUM_NONE;
    ent->physicsObject=1;
    SV_LinkEntity(ent);

    launch=&physics_launches[number];
    if(launch->active) physics_launch_restore_owner(launch,ent);
    launch->active=1;
    launch->useCount=ent->useCount;
    launch->launchTime=level.time;
    launch->restStartTime=level.time;
    launch->passOverridden=0;
    launch->contentsCleared=0;
    VectorCopy(ent->r.currentOrigin,launch->lastOrigin);

    /* A released object starts inside the thing that carried it: the
     * airdrop crate is unlinked from the little bird's tag_ground (and the
     * C-130's) and launched in place, still inside the vehicle's bounds.
     * The retained G_RunItem traces with pass entity r.ownerNum and FREES
     * an item whose first move is startsolid with no upward normal
     * (_g_items.asm G_RunItem_90 -> G_FreeEntity), so every care package
     * vanished one frame after release and "physics_finished" never came.
     * IW4's rigid body does not collide with its carrier; reproduce that by
     * passing the entity the object starts inside for the launch, and
     * restore the real owner when the launch ends. World/terrain overlap is
     * left alone: that is a genuinely bad release point.
     *
     * G_RunItem was written for trigger-contents items; it never excludes
     * the moving entity from its own trace. A script_model that carries
     * brush collision (the crate's CloneBrushmodelToScriptmodel) therefore
     * starts solid against ITSELF on every frame and is freed the same way.
     * Fly it without contents and restore them when it comes to rest, when
     * it becomes solid for players again (IW4 crates are solid once landed). */
    if(ent->r.contents) {
        launch->savedContents=ent->r.contents;
        launch->contentsCleared=1;
        ent->r.contents=0;
        SV_LinkEntity(ent);
    }
    launch->childCount=0;
    physics_launch_clear_children(launch,ent);
    {
        trace_t tr;
        int mask=ent->clipmask ? ent->clipmask : 0x491;
        int pass=ent->r.ownerNum.number ? ent->r.ownerNum.number-1 : ENTITYNUM_NONE;
        G_TraceCapsule(&tr,ent->r.currentOrigin,ent->r.mins,ent->r.maxs,ent->r.currentOrigin,pass,mask);
        if(tr.startsolid || tr.allsolid) {
            int hit=Trace_GetEntityHitId(&tr);
            if(hit>=0 && hit<ENTITYNUM_WORLD && hit!=(int)number && g_entities[hit].r.inuse) {
                launch->savedOwner=pass!=ENTITYNUM_NONE ? pass : -1;
                launch->savedOwnerUseCount=pass!=ENTITYNUM_NONE ? g_entities[pass].useCount : 0;
                launch->passOverridden=1;
                CODOL_EntHandleSetEnt(&ent->r.ownerNum,&g_entities[hit]);
                if(CODOL_TRACE_VERBOSE())
                    Com_Printf(CON_CHANNEL_SERVER,"CoDOL physics launch: entity %u starts inside entity %d; passing it\n",number,hit);
            }
        }
    }
}

/* ------------------------------------------------------------------ */
/* Riot shield model attachment                                         */
/* ------------------------------------------------------------------ */

#pragma pack(push, 8)
typedef struct {
    unsigned short tag;   /* SL index the shield is attached at, 0 = none */
    unsigned short raised;
} codol_shield_state_t;
#pragma pack(pop)

static codol_shield_state_t shield_state[MAX_CLIENTS];

unsigned CODOL_PlayerShieldTag(unsigned clientNum)
{
    return clientNum<MAX_CLIENTS ? shield_state[clientNum].tag : 0;
}

int CODOL_PlayerShieldRaised(unsigned clientNum)
{
    return clientNum<MAX_CLIENTS && shield_state[clientNum].tag && shield_state[clientNum].raised;
}

void CODOL_ResetPlayerShieldState(unsigned clientNum)
{
    if(clientNum<MAX_CLIENTS) memset(&shield_state[clientNum],0,sizeof(shield_state[clientNum]));
}

static gentity_t *shield_player(scr_entref_t ref)
{
    gentity_t *ent=VM_GetGEntityForEntRef(ref);
    if(!ent) return NULL;
    if(!ent->client || (unsigned)ent->s.number>=MAX_CLIENTS) {
        Scr_ObjectError("shield model methods require a player entity");
        return NULL;
    }
    return ent;
}

static int tag_is_raised(unsigned tag)
{
    const char *name=SL_ConvertToString(tag);
    return name && !strcmp(name,"tag_weapon_left");
}

static void shield_record(gentity_t *ent, unsigned tag)
{
    codol_shield_state_t *state=&shield_state[ent->s.number];
    state->tag=(unsigned short)tag;
    state->raised=(unsigned short)(tag && tag_is_raised(tag));
}

/* IW4 player AttachShieldModel(<model>, <tag>) (_class.gsc:
 * "weapon_riot_shield_mp" on tag_weapon_left when raised, tag_shield_back
 * when stowed). The attachment goes through the retained G_EntAttach with
 * collision enabled, so server DObj traces can meet the shield model; the
 * IW4 shield hit encoding (Bullet_ProcessShieldHit, G_GetShieldTagMatrix)
 * is not reproduced here. Failure to attach is a script error, as with the
 * retained attach method. */
void CODOL_PlayerCmd_AttachShieldModel(scr_entref_t ref)
{
    gentity_t *ent=shield_player(ref);
    const char *model;
    unsigned tag;
    if(!ent) return;
    if(Scr_GetNumParam()!=2) {
        Scr_Error("Usage: <player> AttachShieldModel( <model name>, <tag name> )");
        return;
    }
    model=Scr_GetString(0);
    tag=Scr_GetConstLowercaseString(1);
    if(!G_EntAttach(ent,model,tag,0)) {
        Scr_Error(va("failed to attach shield model %s to tag %s",model,SL_ConvertToString(tag)));
        return;
    }
    shield_record(ent,tag);
}

/* IW4 player DetachShieldModel(<model>, <tag>) (_class.gsc _detachAll,
 * _damage.gsc LaunchShield). Detaches through the retained G_EntDetach and
 * clears the recorded shield placement. */
void CODOL_PlayerCmd_DetachShieldModel(scr_entref_t ref)
{
    gentity_t *ent=shield_player(ref);
    const char *model;
    unsigned tag;
    if(!ent) return;
    if(Scr_GetNumParam()!=2) {
        Scr_Error("Usage: <player> DetachShieldModel( <model name>, <tag name> )");
        return;
    }
    model=Scr_GetString(0);
    tag=Scr_GetConstLowercaseString(1);
    if(!G_EntDetach(ent,model,tag)) {
        Scr_Error(va("failed to detach shield model %s from tag %s",model,SL_ConvertToString(tag)));
        return;
    }
    if(shield_state[ent->s.number].tag==tag) shield_record(ent,0);
}

/* IW4 player MoveShieldModel(<model>, <from tag>, <to tag>) (_class.gsc
 * weapon_change: back <-> hand). Detach from the source tag, then attach at
 * the destination; a failed re-attach leaves the shield detached and errors. */
void CODOL_PlayerCmd_MoveShieldModel(scr_entref_t ref)
{
    gentity_t *ent=shield_player(ref);
    const char *model;
    unsigned from, to;
    if(!ent) return;
    if(Scr_GetNumParam()!=3) {
        Scr_Error("Usage: <player> MoveShieldModel( <model name>, <from tag>, <to tag> )");
        return;
    }
    model=Scr_GetString(0);
    from=Scr_GetConstLowercaseString(1);
    to=Scr_GetConstLowercaseString(2);
    if(!G_EntDetach(ent,model,from)) {
        Scr_Error(va("failed to detach shield model %s from tag %s",model,SL_ConvertToString(from)));
        return;
    }
    shield_record(ent,0);
    if(!G_EntAttach(ent,model,to,0)) {
        Scr_Error(va("failed to attach shield model %s to tag %s",model,SL_ConvertToString(to)));
        return;
    }
    shield_record(ent,to);
}

/* ------------------------------------------------------------------ */
/* codol_radiusdamage / codol_fire_nearest                              */
/* ------------------------------------------------------------------ */

/* codol_radiusdamage(pos, radius, max, min, owner, weapon [, mod])
 * Overlay-authored builtin (gsc_overlay/maps/mp/killstreaks/_codol.gsc,
 * _weapons.gsc equipExplode; reference gscbuiltins.py _codol_radiusdamage).
 * Linear falloff over every damageable entity in range, excluding the owner
 * and the owner's team, applied through the retained G_Damage with the
 * dflags, direction lift and CanDamage line-of-sight scale that the retained
 * G_RadiusDamage uses. Returns the number of entities damaged (the reference
 * returns its hit count; nonzero means hit). */
void CODOL_Scr_RadiusDamage(void)
{
    vec3_t pos, dir;
    float radius, maxDamage, minDamage;
    gentity_t *owner;
    int weapon, mod, hits=0, i;
    if(Scr_GetNumParam()<6 || Scr_GetNumParam()>7) {
        Scr_Error("Usage: codol_radiusdamage( <position>, <radius>, <max damage>, <min damage>, <owner>, <weapon> [, <means of death>] )");
        return;
    }
    Scr_GetVector(0,pos);
    radius=Scr_GetFloat(1);
    maxDamage=Scr_GetFloat(2);
    minDamage=Scr_GetFloat(3);
    if(!(radius>0.0f)) {
        Scr_ParamError(1,"Invalid <range> value specified for radius damage ( parameter 2 ).");
        return;
    }
    if(!(maxDamage>=0.0f)) {
        Scr_ParamError(2,"Invalid <max_damage> value specified for radius damage ( parameter 3 ).");
        return;
    }
    if(!(minDamage>=0.0f)) {
        Scr_ParamError(3,"Invalid <min_damage> value specified for radius damage ( parameter 4 ).");
        return;
    }
    owner=owner_from_param(4);
    weapon=weapon_from_param(5);
    mod=mod_from_param(6,CODOL_MOD_EXPLOSIVE);

    for(i=0;i<level.num_entities;++i) {
        gentity_t *ent=&g_entities[i];
        float distance, scale;
        int damage;
        if(!ent->r.inuse || !ent->takedamage || ent==owner) continue;
        if(!CODOL_EntityCanRadiusDamage(ent)) continue;
        if(ent->client) {
            if(!player_alive(ent)) continue;
            if(level.bPlayerIgnoreRadiusDamage) continue;
        }
        if(!overlay_may_damage(owner,ent)) continue;
        distance=CODOL_RadiusBoxDistance(pos,ent->r.absmin,ent->r.absmax);
        if(distance>radius) continue;
        scale=CanDamage(ent,NULL,pos,1.0f,NULL,CODOL_CANDAMAGE_CONTENTMASK);
        if(!(scale>0.0f)) continue;
        damage=(int)(linear_falloff(maxDamage,minDamage,distance,radius)*scale);
        if(damage<=0) continue;
        VectorSubtract(ent->r.currentOrigin,pos,dir);
        dir[2]+=CODOL_RADIUS_DIR_LIFT;
        G_Damage(ent,NULL,owner,dir,pos,damage,CODOL_RADIUS_DAMAGE_DFLAGS,mod,weapon,
            HITLOC_NONE,0,0,0);
        ++hits;
    }
    Scr_AddInt(hits);
}

/* codol_fire_nearest(src, range, damage, owner, weapon [, mod])
 * Overlay-authored builtin (_codol.gsc gunship/sentry/dog bursts;
 * reference gscbuiltins.py _codol_fire_nearest). One shot at the nearest
 * live enemy player within range of src that the retained CanDamage can
 * see from src; the damage is delivered by G_Damage as a torso-upper hit
 * from the owner. Returns 1 when a target was hit, otherwise 0. The
 * reference picks the nearest enemy without a visibility test; a target
 * behind cover is skipped here in favour of the next nearest visible one. */
void CODOL_Scr_FireNearest(void)
{
    vec3_t src, delta, dir, point;
    float range, rangeSq;
    gentity_t *owner, *best=NULL;
    float bestDistSq=0.0f;
    int damage, weapon, mod, i;
    if(Scr_GetNumParam()<5 || Scr_GetNumParam()>6) {
        Scr_Error("Usage: codol_fire_nearest( <source position>, <range>, <damage>, <owner>, <weapon> [, <means of death>] )");
        return;
    }
    Scr_GetVector(0,src);
    range=Scr_GetFloat(1);
    damage=Scr_GetInt(2);
    if(!(range>0.0f)) {
        Scr_ParamError(1,"range must be greater than 0");
        return;
    }
    owner=owner_from_param(3);
    weapon=weapon_from_param(4);
    mod=mod_from_param(5,CODOL_MOD_RIFLE_BULLET);
    if(damage<=0) {
        Scr_AddInt(0);
        return;
    }
    rangeSq=range*range;
    for(i=0;i<level.maxclients;++i) {
        gentity_t *ent=&g_entities[i];
        float distSq;
        if(!player_alive(ent) || !ent->takedamage || ent==owner) continue;
        if(!overlay_may_damage(owner,ent)) continue;
        VectorSubtract(ent->r.currentOrigin,src,delta);
        distSq=DotProduct(delta,delta);
        if(distSq>rangeSq) continue;
        if(best && distSq>=bestDistSq) continue;
        if(!(CanDamage(ent,NULL,src,1.0f,NULL,CODOL_CANDAMAGE_CONTENTMASK)>0.0f)) continue;
        best=ent;
        bestDistSq=distSq;
    }
    if(!best) {
        Scr_AddInt(0);
        return;
    }
    /* Aim at the player's view origin so the hit direction matches a shot
     * from src; the impact point is that origin. */
    G_GetPlayerViewOrigin(&best->client->ps,point);
    VectorSubtract(point,src,dir);
    Vec3NormalizeTo(dir,dir);
    G_Damage(best,owner,owner,dir,point,damage,0,mod,weapon,HITLOC_TORSO_UPR,0,0,0);
    Scr_AddInt(1);
}

/* IW4's FireWeapon (and CoDOL's) raise "weapon_fired" with the weapon's
 * internal name as the notify parameter; the retained IW3 FireWeapon raised
 * it with none, which the IW4 gametype's weapon_fired watcher rejects with an
 * undefined/string comparison. The retained assembly now calls this. */
void CODOL_NotifyWeaponFired(gentity_t *ent,int weapon)
{
    const char *name=NULL;
    if(!ent) return;
    if(weapon>0) {
        struct WeaponDef *def=BG_GetWeaponDef(weapon);
        if(def) name=*(const char *const *)def;
    }
    Scr_AddString(name && *name ? name : "none");
    Scr_Notify(ent,scr_const.weapon_fired,1);
}

#endif
