#ifdef CODOL_SERVER
/* Turret target family: settargetentity / cleartargetentity / getturrettarget,
 * plus the fire-state family that shares the same state (startfiring,
 * stopfiring, isfiringturret, shootturret, setconvergencetime).
 *
 * IW4 receivers and storage (iw4x.exe, base 0x400000): all of these are entity
 * methods that require entity->pTurretInfo (IW4 entity+0x15c).
 *   0x5ed140 settargetentity   stores Scr_GetEntity(0) in the scripted handle
 *                              (turret+0x50) and Scr_GetVector(1)/zero next to
 *                              it (turret+0x54).
 *   0x5ed1f0 cleartargetentity clears that handle only.
 *   0x5ed260 getturrettarget   reads Scr_GetInt(0); when nonzero the tracked
 *                              target (turret+0x40) is only returned if turret
 *                              flag 0x20 ("can bear on the target") is set.
 *   0x5ecbe0 startfiring       turret->flags |= 0x10.
 *   0x5ecc50 stopfiring        turret->flags &= ~0x10.
 *   0x5eccc0 isfiringturret    returns turret->state(+0x3c) != 0 (0x44a6e0).
 *   0x5ece80 shootturret       fires one shot through 0x44cc30 -> 0x5ff2f0.
 *   0x5ed390 setconvergencetime(<seconds>[,"pitch"|"yaw"]) stores
 *                              seconds*1000 into turret+0x78/+0x7c.
 *
 * The producer chain, all disassembled: turret think 0x45c6e0 runs the
 * script-target update 0x601210 on the unmanned branch. 0x601210 rejects the
 * scripted target when its squared distance from the turret entity origin
 * exceeds the squared range gate turret+0x6c, otherwise tracks it (0x6007f0),
 * runs the "can bear" test (0x600760 -> 0x46b3c0), advances the fire state
 * machine (0x600620) and converges the gun angles (0x6001c0 with the rates
 * from 0x600090). Losing the target runs the clear helper 0x464b20 and the
 * idle convergence through the same gun-angle writer, with weapon rates off.
 *
 * No IW4 offset is carried over: IW4's turret struct is 0xc4 bytes with its
 * own field order, this pool is 0x48 -> CODOL_TURRET_INFO_SIZE bytes. Only the
 * semantics are reproduced, on this fork's own named fields, and every weapon
 * value is read through this fork's named WeaponDef members (whose offsets are
 * confirmed by the retained G_SpawnTurret: leftArc 0x798, rightArc 0x79c,
 * topArc 0x7a0, bottomArc 0x7a4, playerSpread 0x7b0). */

#include "codol_script_turret_target.h"
#include "codol_sentient.h"
#include "g_shared.h"
#include "g_public_mp.h"
#include "dobj.h"
#include "q_math.h"
#include "bg_public.h"
#include "bg.h"
#include "xassets/weapondef.h"
#include "cvar.h"
#include "codol_playerstate_ext.h"
#include "codol_script_startup_missing.h"

#include <math.h>
#include <string.h>
#include <float.h>
#include <limits.h>

/* Pool lives in src/asmsource/_g_misc_mp.asm. */
extern turretInfo_s turretInfo[CODOL_MAX_TURRETS];

/* Hard failure if the struct and the assembly pool stride ever diverge. */
typedef char codol_turretInfo_size_check[
    (sizeof(turretInfo_s) == CODOL_TURRET_INFO_SIZE) ? 1 : -1];

extern "C"
{
/* Retained assembly, declared here because no header exposes them.
 * Argument order is taken from the retained call sites in
 * src/asmsource/_g_misc_mp.asm (turret_think_client) and
 * src/asmsource/_bullet.asm (Bullet_Fire / Bullet_Endpos). */
void Bullet_Fire(gentity_s *attacker, float spread, void *fireParams,
                 gentity_s *weaponEnt, int time);
void Weapon_RocketLauncher_Fire(gentity_s *ent, int weapon, int unused,
                                void *fireParams, const float *velocity, int a, int b);
void G_AddEvent(gentity_s *ent, int event, int eventParm);
int G_SpawnFloat(const char *key, const char *defaultValue, float *out);
/* _g_main_mp.asm: passes vec3_origin for the bounds and ENTITYNUM_NONE as the
 * second ignored entity, so only the turret can be excluded here. */
void G_SightTrace(int *hitNum, const float *start, const float *end,
                  int passEntityNum, int contentmask);
/* codol_actor_lifecycle.cpp: an actor's tag_eye, 0 for a non-actor. */
int CODOL_ActorEyePosition(gentity_s *entity, float *position);
/* sv_world.cpp: two ignored entities. */
void SV_SightTrace(int *hitNum, const float *start, const float *mins, const float *maxs,
                   const float *end, int passEntityNum0, int passEntityNum1, int contentmask);
}

/* turret_think sets nextthink to level.time + 50 before it reaches the target
 * update, so one think is 50 ms of gun movement. */
#define CODOL_TURRET_THINK_MSEC 50
/* IW4 0x70f86c: the turn rate used when no weapon rates are wanted. The
 * retained idle drift in turret_think uses the same 200 deg/s. */
#define CODOL_TURRET_IDLE_TURN_RATE 200.0f
/* IW4 0x739fe0: "close enough to the goal" angle, in degrees. */
#define CODOL_TURRET_ONTARGET_EPSILON 5.0f
/* IW4 0x60065b (0xfa): after this long the turret counts as aimed even if the
 * gun never got within the epsilon. */
#define CODOL_TURRET_AIM_GRACE_MSEC 250
/* IW4 0x6000cb (0x5dc): while firing, the pitch convergence window is never
 * shorter than this. */
#define CODOL_TURRET_FIRING_PITCH_MSEC 1500
/* IW4 0x721b54: squared distance the cached target position must move before
 * the tracked target counts as changed. */
#define CODOL_TURRET_TRACK_EPSILON_SQ 0.001f
/* Retained Bullet_Fire loads this range for every non-spread weapon
 * (_bullet.asm, _float_8192_00000000); C1's can-bear reads the same value the
 * shot will use out of its weapon definition. */
#define CODOL_TURRET_DEFAULT_BULLET_RANGE 8192.0f
/* C1 0x57cda5 (0xfa0): an acquired target is kept for four seconds before the
 * turret looks for another one. */
#define CODOL_TURRET_ACQUIRE_HOLD_MSEC 4000
/* C1 0x57cf06 (0x1f4): after a mode change the turret settles for this long
 * before it acquires. */
#define CODOL_TURRET_MODE_SETTLE_MSEC 500
/* C1 0x57c08f (0xc842e0 = 2.0): the aim point is the target origin plus this
 * height while the turret is not yet in its firing state. */
#define CODOL_TURRET_AIM_HEIGHT 2.0f
/* The mask this fork's own "sighttracepassed" uses without the extra bit;
 * C1's turret trace at 0x57cbd8 passes the same 0x801803. */
#define CODOL_TURRET_SIGHT_MASK 0x801803
/* C1 0x57ae5b / 0x57aea8 compare the steered direction against 0xc84bc0 =
 * 0.95 before they overwrite the shot forward vector. */
#define CODOL_TURRET_STEER_DOT 0.95f

/* Retained turret_think pitch-cap bits, named locally. turret_think applies
 * exactly this sequence to the idle drift; the target path applies it too so a
 * scripted target cannot drive the gun through a script-imposed cap. */
#define CODOL_TURRET_PITCHCAP_PENDING 0x100
#define CODOL_TURRET_PITCHCAP_ACTIVE 0x200
#define CODOL_TURRET_PITCHCAP_MINIMUM 0x400

/* Layout of the fire parameters retained turret_think_client builds on its
 * stack and hands to Bullet_Fire / Weapon_RocketLauncher_Fire: three axis rows
 * (Bullet_Endpos spreads along +0x0c and +0x18 from the start at +0x24), the
 * shot origin, a copy of the direction and the WeaponDef that Bullet_Fire
 * dereferences at +0x3c. */
struct codol_turretFireParams_t
{
    vec3_t forward;
    vec3_t right;
    vec3_t up;
    vec3_t start;
    vec3_t dir;
    struct WeaponDef *weapDef;
};

typedef char codol_turretFireParams_size_check[
    (sizeof(codol_turretFireParams_t) == 0x40) ? 1 : -1];

static float TurretTarget_Normalize180(float angle)
{
    return angle - 360.0f * floorf(angle / 360.0f + 0.5f);
}

/* x86 conversion returns the integer-indefinite value for NaN/overflow.
 * Check the already-rounded value before the C cast to avoid undefined
 * conversion behavior on those inputs. */
static int TurretTarget_ConvertedMilliseconds(double value)
{
    return value >= INT_MIN && value <= INT_MAX ? (int)value : INT_MIN;
}

static struct WeaponDef *TurretTarget_WeaponDef(gentity_s *entity)
{
    if (entity->s.weapon <= 0 || entity->s.weapon >= BG_GetNumWeapons())
    {
        return NULL;
    }
    return BG_GetWeaponDef(entity->s.weapon);
}

/* IW4 0x408d3d and 0x408c9b/0x408cf6: the range gate is stored squared and
 * defaults to the weapon range, or to FLT_MAX when that is not positive; the
 * convergence times default to the weapon's, clamped at zero, in milliseconds.
 * Defaults are applied once per allocated pool slot. The spawn producer below
 * then applies map keys while that entity's SpawnVar is still active.
 * G_SpawnTurret memsets the slot, which clears the flag below. */
static void TurretTarget_ApplyDefaults(gentity_s *entity, turretInfo_s *turret)
{
    struct WeaponDef *weapDef;
    float range;
    float convergence;

    if (turret->flags & CODOL_TURRET_TARGET_INITED)
    {
        return;
    }
    turret->flags |= CODOL_TURRET_TARGET_INITED;
    CODOL_TurretHeat_Defaults(turret);
    /* C1 G_SpawnTurret 0x57f2cb writes its entity-state owner field as "none".
     * This fork publishes that field through s.otherEntityNum, which the
     * snapshot archives; the acquisition and the CoDOL overlay both read it
     * from the archived state rather than from the live entity. */
    entity->s.otherEntityNum = ENTITYNUM_NONE;
    /* C1's allocator memsets the slot, so a fresh turret prepares its first
     * sweep leg from scratch. */
    turret->sweepSpeed = 0.0f;
    turret->sweepBrake = 0.0f;
    turret->sweepResumeTime = 0;
    turret->sweepFlags = 0;
    turret->onTargetCos = 0.0f;
    turret->flags &= ~(int)CODOL_TURRET_OFF_CONE;
    turret->targetRangeSq = FLT_MAX;
    turret->convergenceTime[0] = 0;
    turret->convergenceTime[1] = 0;

    weapDef = TurretTarget_WeaponDef(entity);
    if (!weapDef)
    {
        return;
    }
    range = weapDef->maxRange;
    if (range > 0.0f)
    {
        turret->targetRangeSq = range * range;
    }
    convergence = weapDef->pitchConvergenceTime;
    if (convergence < 0.0f)
    {
        convergence = 0.0f;
    }
    turret->convergenceTime[0] = (int)(convergence * 1000.0f + 0.5f);
    convergence = weapDef->yawConvergenceTime;
    if (convergence < 0.0f)
    {
        convergence = 0.0f;
    }
    turret->convergenceTime[1] = (int)(convergence * 1000.0f + 0.5f);
}

/* C1 G_SpawnTurret 57ee11..57ee76 prefers "yawconvergencetime", falling
 * back to IW4's "convergencetime" only when absent. The pitch
 * key "pitchconvergencetime", and "maxrange". Missing keys preserve weapon
 * defaults; negative convergence clamps to zero, nonpositive range is unlimited.
 * Read only during spawning: a lazy read in Think would use another entity's
 * spawn variables. Dynamic turrets with no active SpawnVar use weapon defaults. */
/* C1 G_SpawnTurret 0x57ec97..0x57ed3e, once the yaw arcs are clamped: the
 * on-target cone is the yaw span, floored at 90 degrees and ceilinged at 180,
 * stored as a cosine. C1 parks the raw span in the same field first; only the
 * cosine survives. */
static void TurretTarget_UpdateOnTargetCone(turretInfo_s *turret)
{
    float span = turret->arcmax[1] - turret->arcmin[1];
    float value;

    if (!(span > 0.0f))
    {
        span = 0.0f;
    }
    value = (span > 90.0f) ? ((span < 180.0f) ? span : 180.0f) : 90.0f;
    turret->onTargetCos = (float)cos((double)value * 3.14159265358979323846 / 180.0);
}

void CODOL_TurretTarget_Spawn(gentity_s *entity)
{
    turretInfo_s *turret;
    float value;
    if (!entity || !(turret = entity->pTurretInfo))
    {
        return;
    }
    TurretTarget_ApplyDefaults(entity, turret);
    /* The retained G_SpawnTurret has already written all four arcs when it
     * reaches this call, which is where C1 derives the cone too. */
    TurretTarget_UpdateOnTargetCone(turret);
    if (!level.spawnVars.spawnVarsValid)
    {
        return;
    }
    if (G_SpawnFloat("yawconvergencetime", "", &value) ||
        G_SpawnFloat("convergencetime", "", &value))
    {
        if (value < 0.0f) value = 0.0f;
        turret->convergenceTime[1] = (int)(value * 1000.0f + 0.5f);
    }
    if (G_SpawnFloat("pitchconvergencetime", "", &value))
    {
        if (value < 0.0f) value = 0.0f;
        turret->convergenceTime[0] = (int)(value * 1000.0f + 0.5f);
    }
    if (G_SpawnFloat("maxrange", "", &value))
    {
        turret->targetRangeSq = value > 0.0f ? value * value : FLT_MAX;
    }
}

/* IW4 resolves turret geometry through the "tag_aim" tag (the const string
 * behind 0x1aa2eb8, resolved from the SL_GetString sequence at 0x472589), both
 * for the can-bear test 0x46b3c0 and for the shot origin 0x5feef0. Only the
 * translation is taken from the tag: the frame orientation comes from
 * r.currentAngles, so the gun's own rotation is not counted twice. */
static qboolean TurretTarget_MuzzlePosition(gentity_s *entity, vec3_t out)
{
    float tagMat[4][3];

    if (!G_DObjGetWorldTagMatrix(entity, scr_const.tag_aim, tagMat))
    {
        return qfalse;
    }
    VectorCopy(tagMat[3], out);
    return qtrue;
}

/* IW4 0x4d9130: world point into the frame {rows = axis, origin = tag}. */
static void TurretTarget_WorldToLocal(const vec3_t point, const vec3_t origin,
                                      const float axis[3][3], vec3_t out)
{
    vec3_t rel;

    VectorSubtract(point, origin, rel);
    out[0] = rel[0] * axis[0][0] + rel[1] * axis[0][1] + rel[2] * axis[0][2];
    out[1] = rel[0] * axis[1][0] + rel[1] * axis[1][1] + rel[2] * axis[1][2];
    out[2] = rel[0] * axis[2][0] + rel[1] * axis[2][1] + rel[2] * axis[2][2];
}

/* IW4 0x5ff02f composes the gun matrix with the entity matrix before it fires,
 * instead of adding Euler angles. out = gun * base. */
static void TurretTarget_ComposeAxis(const float gun[3][3], const float base[3][3],
                                     float out[3][3])
{
    int i;
    int j;

    for (i = 0; i < 3; ++i)
    {
        for (j = 0; j < 3; ++j)
        {
            out[i][j] = gun[i][0] * base[0][j] +
                        gun[i][1] * base[1][j] +
                        gun[i][2] * base[2][j];
        }
    }
}

/* C1 0x57c0f0 opens its can-bear test with a target filter, before any arc
 * or reach arithmetic (after the tag_aim lookup at 0x57c109, which only fails
 * for a turret without the tag):
 *
 *   client = target->client;                                  ; 0x57c11c
 *   if (client) {
 *       if ((client->ps.abilityMask[0] >> 11) & 1) return 0;  ; 0x57c126
 *       if (client->ps.flags & 0x10) return 0;                ; 0x57c13c
 *   }
 *
 * The mask word is C1 ps+0x4d0, the first of the four MSB-first ability words
 * (bit 31 - 20 = 11), so the first test is ability 20 modNoSentryGuns -
 * Ninja/heartbreaker, whose C1 description PERKS_DESC_NINJA reads "not
 * detected by heartbeat sensors, attack helicopters, hover gunships and sentry
 * guns". The second is the playerhide marker (C1 ps+0xec bit 0x10, stored
 * here as CODOL_PS_EF_HIDDEN in the authoritative playerState, see
 * codol_script_startup_missing.c).
 *
 * Because the filter sits inside can-bear, every C1 turret path that asks
 * can-bear about an entity inherits it: the auto-acquisition validator
 * 0x57ca30 (call 0x57cb05), the scripted-target update 0x57c530 (call
 * 0x57c565, whose failure clears turret flag 0x20 and runs the not-on-aim fire
 * state 0x57c310, the same thing this fork's canBear == false branch does),
 * the think path at 0x57df63 and the actor turret-use check at 0x6ef9cc (this
 * fork has no actor turret use, so that last one has no counterpart). The
 * effective ability mask is the one the playerState extension publishes, the
 * same word C1 reads, so a script setAbilityModifier("modNoSentryGuns") is
 * honoured exactly like the selected perk. */
#define CODOL_TURRET_ABILITY_NO_SENTRY_GUNS 20u

static qboolean TurretTarget_TargetFiltered(gentity_s *target)
{
    const codol_ps_ext_t *ext;

    if (!target || !target->client)
    {
        return qfalse;
    }
    ext = CODOL_PlayerStateExtConst(&target->client->ps);
    if (ext && ext->abilities_known &&
        (ext->abilities.masks[CODOL_TURRET_ABILITY_NO_SENTRY_GUNS >> 5] &
         (0x80000000u >> (CODOL_TURRET_ABILITY_NO_SENTRY_GUNS & 31u))))
    {
        return qtrue;
    }
    if (target->client->ps.eFlags & CODOL_PS_EF_HIDDEN)
    {
        return qtrue;
    }
    return qfalse;
}

/* IW4 0x46b3c0: can the turret bear on this world position? The target is
 * transformed into the turret's own frame, range-checked against the weapon
 * reach and then checked against the turret arc; the aim angles fall out of
 * the same transform. No world trace is involved - the flag this feeds means
 * "can reach", not "has line of sight". */
static qboolean TurretTarget_CanBearOn(gentity_s *entity, turretInfo_s *turret,
                                       gentity_s *target, const vec3_t aimPos, float goal[2])
{
    struct WeaponDef *weapDef;
    float axis[3][3];
    vec3_t muzzle;
    vec3_t local;
    vec3_t angles;
    float range;
    int i;

    if (!TurretTarget_MuzzlePosition(entity, muzzle))
    {
        return qfalse;
    }
    /* C1 0x57c11c..0x57c143, see TurretTarget_TargetFiltered. */
    if (TurretTarget_TargetFiltered(target))
    {
        return qfalse;
    }
    AnglesToAxis(entity->r.currentAngles, (vec3_t *)axis);
    TurretTarget_WorldToLocal(aimPos, muzzle, axis, local);

    /* C1 0x57bf68/0x57bf71 (IW4 0x46b3c0): the reach term is the range the
     * bullet itself will travel, taken from the weapon definition and gated
     * by the integer next to it - not the turret's targeting range, which is
     * a separate gate applied to the target position. In this fork the same
     * pair is what Bullet_Fire uses: a spread weapon traces to
     * fMinDamageRange, every other weapon to the fixed 8192 units the
     * retained _bullet.asm loads at Bullet_Fire+0x14. */
    weapDef = TurretTarget_WeaponDef(entity);
    range = CODOL_TURRET_DEFAULT_BULLET_RANGE;
    if (weapDef && weapDef->weapClass == WEAPCLASS_SPREAD)
    {
        range = weapDef->fMinDamageRange;
    }
    if (range > 0.0f && VectorLengthSquared(local) >= range * range)
    {
        return qfalse;
    }

    /* IW4 0x46b496 calls signed conversion 0x4ab460. Native vectoangles
     * wraps negative pitch/yaw to 0..360, which would reject valid targets
     * against signed turret arcs. Preserve atan2's +/-180 boundary as well. */
    if (local[0] == 0.0f && local[1] == 0.0f)
    {
        angles[0] = local[2] > 0.0f ? -90.0f : 90.0f;
        angles[1] = 0.0f;
    }
    else
    {
        float forward = sqrtf(local[0] * local[0] + local[1] * local[1]);
        angles[0] = (float)atan2(local[2], forward) * -57.2957763671875f;
        angles[1] = (float)atan2(local[1], local[0]) * 57.2957763671875f;
    }
    for (i = 0; i < 2; ++i)
    {
        if (angles[i] > turret->arcmax[i])
        {
            return qfalse;
        }
        if (angles[i] < turret->arcmin[i])
        {
            return qfalse;
        }
    }
    goal[0] = angles[0];
    goal[1] = angles[1];
    return qtrue;
}

/* IW4 0x600620 stamps turret+0x64 on every state write and notifies
 * "turretstatechange" only when the "is firing" answer flips. */
static void TurretTarget_SetFireState(gentity_s *entity, turretInfo_s *turret, int state)
{
    int wasFiring = (turret->fireState != CODOL_TURRET_FIRESTATE_NONE);
    int isFiring = (state != CODOL_TURRET_FIRESTATE_NONE);

    if (wasFiring != isFiring)
    {
        Scr_Notify(entity, scr_const.turretstatechange, 0);
    }
    turret->fireState = state;
    turret->stateChangeTime = level.time;
    if (!isFiring)
    {
        turret->triggerDown = 0;
    }
}

/* IW4 0x600620: without the fire flag the state drops to "none"; otherwise the
 * turret waits until the gun is within the epsilon (or the 250 ms grace has
 * passed), then until the yaw convergence window has elapsed, and only then
 * counts as firing. */
static void TurretTarget_UpdateFireState(gentity_s *entity, turretInfo_s *turret,
                                         qboolean fireEnabled, const float goal[2],
                                         qboolean goalValid)
{
    const float *gunAngles = entity->s.lerp.u.turret.gunAngles;
    int remaining;

    if (!fireEnabled)
    {
        TurretTarget_SetFireState(entity, turret, CODOL_TURRET_FIRESTATE_NONE);
        return;
    }

    remaining = turret->convergenceTime[1] + turret->targetChangeTime - level.time;

    if (turret->fireState == CODOL_TURRET_FIRESTATE_NONE)
    {
        if (level.time < turret->targetChangeTime + CODOL_TURRET_AIM_GRACE_MSEC)
        {
            /* IW4 0x600760 calls this on both can-bear outcomes with the same
             * script fire flag, but on failure 0x46b3c0 returned without
             * writing the angle buffer, so the epsilon test reads an
             * uninitialised stack local that is essentially never within 5
             * degrees. goalValid reproduces that outcome deterministically:
             * without a valid goal only the 250 ms grace can promote the
             * state, exactly as it does in the reference. */
            if (!goalValid)
            {
                return;
            }
            if (fabsf(TurretTarget_Normalize180(gunAngles[0] - goal[0])) >=
                CODOL_TURRET_ONTARGET_EPSILON)
            {
                return;
            }
            if (fabsf(TurretTarget_Normalize180(gunAngles[1] - goal[1])) >=
                CODOL_TURRET_ONTARGET_EPSILON)
            {
                return;
            }
        }
        TurretTarget_SetFireState(entity, turret, CODOL_TURRET_FIRESTATE_CONVERGING);
    }
    if (turret->fireState == CODOL_TURRET_FIRESTATE_CONVERGING)
    {
        if (remaining > 0)
        {
            return;
        }
        TurretTarget_SetFireState(entity, turret, CODOL_TURRET_FIRESTATE_FIRING);
    }
}

/* IW4 0x600090 picks the rate that covers the remaining angle exactly within
 * the remaining convergence window (or in one think once that window has
 * passed), and 0x6001c0 then clamps it to the weapon's turn speeds - max
 * first, then min, so an inverted weapon definition lets the minimum win. */
static void TurretTarget_TurnRates(gentity_s *entity, turretInfo_s *turret,
                                   const float goal[2], qboolean useWeaponRates,
                                   float rates[2])
{
    const float *gunAngles = entity->s.lerp.u.turret.gunAngles;
    struct WeaponDef *weapDef;
    int remaining[2];
    int frameTime;
    int firingWindow;
    float delta;
    int i;

    remaining[0] = turret->convergenceTime[0] + turret->targetChangeTime - level.time;
    remaining[1] = turret->convergenceTime[1] + turret->targetChangeTime - level.time;
    if (turret->fireState == CODOL_TURRET_FIRESTATE_FIRING)
    {
        firingWindow = turret->stateChangeTime - level.time + CODOL_TURRET_FIRING_PITCH_MSEC;
        if (remaining[0] < firingWindow)
        {
            remaining[0] = firingWindow;
        }
    }

    frameTime = entity->nextthink - level.time;
    if (frameTime <= 0)
    {
        frameTime = CODOL_TURRET_THINK_MSEC;
    }

    for (i = 0; i < 2; ++i)
    {
        delta = fabsf(TurretTarget_Normalize180(gunAngles[i] - goal[i]));
        if (remaining[i] > 0 && frameTime < remaining[i])
        {
            rates[i] = delta * 1000.0f / (float)remaining[i];
        }
        else
        {
            rates[i] = delta * 1000.0f / (float)frameTime;
        }
    }

    weapDef = useWeaponRates ? TurretTarget_WeaponDef(entity) : NULL;
    if (!weapDef)
    {
        rates[0] = CODOL_TURRET_IDLE_TURN_RATE;
        rates[1] = CODOL_TURRET_IDLE_TURN_RATE;
        return;
    }
    for (i = 0; i < 2; ++i)
    {
        if (rates[i] > weapDef->maxTurnSpeed[i])
        {
            rates[i] = weapDef->maxTurnSpeed[i];
        }
        if (rates[i] < weapDef->minTurnSpeed[i])
        {
            rates[i] = weapDef->minTurnSpeed[i];
        }
    }
}

/* IW4 0x6001c0 stepped onto this fork's gun angles. The two-stage shape is the
 * retained one from turret_think: the unspent pitch carried in gunAngles[2] is
 * added back first, both axes step toward the goal, then the pitch is capped
 * and re-limited and the leftover goes back into the carry slot.
 * "turret_on_target" is notified when both axes ended within the epsilon and a
 * target is tracked (IW4 0x6004bc). */
static qboolean TurretTarget_Converge(gentity_s *entity, turretInfo_s *turret,
                                  const float goal[2], qboolean useWeaponRates)
{
    float *gunAngles = entity->s.lerp.u.turret.gunAngles;
    float rates[2];
    float pitchStart;
    float pitch;
    float delta;
    float maxStep;
    qboolean reachedGoal = qtrue;
    int i;

    TurretTarget_TurnRates(entity, turret, goal, useWeaponRates, rates);
    for (i = 0; i < 2; ++i)
    {
        rates[i] *= (float)CODOL_TURRET_THINK_MSEC / 1000.0f;
    }

    pitchStart = gunAngles[0];
    gunAngles[0] += gunAngles[2];

    for (i = 0; i < 2; ++i)
    {
        maxStep = rates[i];
        delta = TurretTarget_Normalize180(goal[i] - gunAngles[i]);
        if (fabsf(delta) >= CODOL_TURRET_ONTARGET_EPSILON)
        {
            reachedGoal = qfalse;
        }
        if (delta > maxStep)
        {
            delta = maxStep;
        }
        else if (delta < -maxStep)
        {
            delta = -maxStep;
        }
        gunAngles[i] += delta;
    }

    pitch = gunAngles[0];
    gunAngles[2] = pitch;
    if (turret->flags & CODOL_TURRET_PITCHCAP_ACTIVE)
    {
        if (turret->flags & CODOL_TURRET_PITCHCAP_MINIMUM)
        {
            if (turret->pitchCap > pitch)
            {
                pitch = turret->pitchCap;
            }
        }
        else if (pitch > turret->pitchCap)
        {
            pitch = turret->pitchCap;
        }
        turret->flags &= ~CODOL_TURRET_PITCHCAP_PENDING;
    }

    delta = TurretTarget_Normalize180(pitch - pitchStart);
    maxStep = rates[0];
    if (delta > maxStep)
    {
        delta = maxStep;
    }
    else if (delta < -maxStep)
    {
        delta = -maxStep;
    }
    gunAngles[0] = pitchStart + delta;
    gunAngles[2] -= gunAngles[0];

    if (reachedGoal && turret->target.isDefined())
    {
        Scr_Notify(entity, scr_const.turret_on_target, 0);
    }
    /* C1 0x57b8e0 and IW4 0x6001c0 hand the caller "the gun is on the goal";
     * C1's mode-settle phase 0x57cf41 branches on it. */
    return reachedGoal;
}

/* IW4 0x6007f0: nothing happens while the handle and the cached position are
 * unchanged; otherwise the handle, the "can bear" flag, the change stamp and
 * the cached position are all rewritten. */
static void TurretTarget_SetTracked(turretInfo_s *turret, gentity_s *target,
                                    const vec3_t aimPos)
{
    vec3_t moved;

    if (turret->target.number == (uint16_t)(target->s.number + 1))
    {
        VectorSubtract(aimPos, turret->targetPos, moved);
        if (VectorLengthSquared(moved) < CODOL_TURRET_TRACK_EPSILON_SQ)
        {
            return;
        }
    }
    turret->target.setEnt(target);
    turret->flags &= ~CODOL_TURRET_TARGET_ONAIM;
    turret->targetChangeTime = level.time;
    VectorCopy(aimPos, turret->targetPos);
}

/* IW4 0x464b20: drop the tracked target, its cached position and the reach
 * flag, and take the fire state back to "none" (which notifies). */
static void TurretTarget_ClearTracked(gentity_s *entity, turretInfo_s *turret)
{
    turret->target.setEnt(NULL);
    turret->flags &= ~CODOL_TURRET_TARGET_ONAIM;
    VectorClear(turret->targetPos);
    TurretTarget_SetFireState(entity, turret, CODOL_TURRET_FIRESTATE_NONE);
}

/* IW4 0x5ff100 fires as the turret's user when it has one and as the turret
 * itself otherwise. On this fork the turret's user handle is r.ownerNum, which
 * is what turret_think and getturretowner read. */
static gentity_s *TurretTarget_Attacker(gentity_s *entity)
{
    unsigned int number = entity->r.ownerNum.number;

    if (number == 0 || number > MAX_GENTITIES)
    {
        return entity;
    }
    return &g_entities[number - 1];
}

/* Defined with the acquisition below; the shot builder needs the same trace
 * for C1's steering step. Both callers already hold the tag_aim muzzle that
 * C1 computes once per validation (0x57ca30's [ebp-0x20]). */
static qboolean TurretAuto_LineOfSight(gentity_s *entity, gentity_s *target,
                                       const vec3_t muzzle, const vec3_t aimPos);

/* C1 0x57cb80, defined with the team helpers it needs. */
static qboolean TurretAuto_FriendlyBlocked(turretInfo_s *turret, gentity_s *target,
                                           const vec3_t muzzle, const vec3_t aimPos);

/* IW4 0x5feef0: unmanned shots use the composed gun/entity axes and tag_aim.
 * Manned shots use the player's view axes and project the start forward by
 * the view-to-muzzle distance, also used by retained turret_think_client. */
static qboolean TurretTarget_Shoot(gentity_s *entity, turretInfo_s *turret,
                                   struct WeaponDef *weapDef)
{
    codol_turretFireParams_t params;
    float base[3][3];
    float gun[3][3];
    float axis[3][3];
    vec3_t gunAngles;
    vec3_t muzzle;
    gentity_s *attacker;

    /* IW4 0x5ff2f0 is gate first, then the fire-sound window, then the shot;
     * every producer (the manned update 0x5ffd70 and shootturret 0x44cc30)
     * goes through it, so the gate lives here rather than in the callers. */
    if (!CODOL_TurretHeat_CanFire(entity))
    {
        return qfalse;
    }
    if (!TurretTarget_MuzzlePosition(entity, muzzle))
    {
        return qfalse;
    }
    /* IW4 0x5ff303: turret->fireSndDelay = 3 * weapDef fire time. */
    turret->fireSndDelay = 3 * weapDef->iFireTime;

    attacker = TurretTarget_Attacker(entity);
    if (attacker->client)
    {
        vec3_t viewOrigin, toMuzzle;
        float distance;
        G_GetPlayerViewOrigin(&attacker->client->ps, viewOrigin);
        BG_GetPlayerViewDirection(&attacker->client->ps,
                                 params.forward, params.right, params.up);
        VectorSubtract(muzzle, viewOrigin, toMuzzle);
        distance = VectorLength(toMuzzle);
        VectorMA(viewOrigin, distance, params.forward, params.start);
    }
    else
    {
        AnglesToAxis(entity->r.currentAngles, (vec3_t *)base);
        gunAngles[0] = entity->s.lerp.u.turret.gunAngles[0];
        gunAngles[1] = entity->s.lerp.u.turret.gunAngles[1];
        gunAngles[2] = 0.0f;
        AnglesToAxis(gunAngles, (vec3_t *)gun);
        TurretTarget_ComposeAxis(gun, base, axis);
        VectorCopy(axis[0], params.forward);
        VectorCopy(axis[1], params.right);
        VectorCopy(axis[2], params.up);
        VectorCopy(muzzle, params.start);
    }
    VectorCopy(params.forward, params.dir);
    params.weapDef = weapDef;

    /* C1 0x57acf0 takes the turret's "can bear" flag as its third argument
     * (0x57b0d0 passes flags>>5 & 1 for an unmanned shot, 0x57b0a9 passes 0
     * for a manned one). With that flag set and a tracked target, the shot is
     * steered from the gun axis onto the cached aim position, but only while
     * the steered direction stays within 0.95 of the gun forward
     * (0x57ae5b/0x57aea8), and only when the line to it is clear
     * (0x57abc0's sight test, reproduced with the same trace as the
     * acquisition). Only the forward row is replaced, exactly as C1 writes
     * only [ebp-0x60..-0x58]. */
    if (attacker == entity && (turret->flags & CODOL_TURRET_TARGET_ONAIM) &&
        turret->target.isDefined())
    {
        gentity_s *tracked = turret->target.ent();
        vec3_t steer;
        float length;

        VectorSubtract(turret->aimPos, params.start, steer);
        length = VectorNormalize(steer);
        /* C1 0x57ada2 maintains the "outside the on-target cone" flag in the
         * same builder, from the angle between the gun forward and the
         * direction to the aim point, before it decides whether to steer. */
        if (length > 0.0f)
        {
            if (DotProduct(steer, params.forward) > turret->onTargetCos)
            {
                turret->flags &= ~(int)CODOL_TURRET_OFF_CONE;
            }
            else
            {
                turret->flags |= (int)CODOL_TURRET_OFF_CONE;
            }
        }
        if (tracked && length > 0.0f &&
            DotProduct(steer, params.forward) > CODOL_TURRET_STEER_DOT &&
            TurretAuto_LineOfSight(entity, tracked, params.start, turret->aimPos))
        {
            VectorCopy(steer, params.forward);
            VectorCopy(steer, params.dir);
        }
    }
    if (weapDef->weapType == WEAPTYPE_BULLET)
    {
        Bullet_Fire(attacker, turret->playerSpread, &params, entity, level.time);
    }
    else
    {
        /* Retained turret_think_client_230 passes the address of vec3_origin
         * as the launch velocity, not a scalar. */
        Weapon_RocketLauncher_Fire(entity, entity->s.weapon, 0, &params, vec3_origin, 0, 0);
    }
    G_AddEvent(entity, EV_FIRE_WEAPON_MG42, attacker->s.number);
    entity->s.lerp.eFlags |= 0x40;
    /* IW4's heat update reads its own "fired this frame" eFlag; this fork's
     * turret_think clears the equivalent bit before the CoDOL think runs, so
     * the shot is latched on the turret as well. */
    CODOL_TurretHeat_NoteShot(entity);
    return qtrue;
}

static qboolean TurretTarget_ValidTarget(gentity_s *target)
{
    if (!target->r.inuse)
    {
        return qfalse;
    }
    if (target->client && target->client->sess.sessionState != SESS_STATE_PLAYING)
    {
        return qfalse;
    }
    return qtrue;
}

static gentity_s *TurretTarget_Receiver(scr_entref_t ref, const char *usage)
{
    gentity_s *entity;

    if (ref.classnum || ref.entnum >= MAX_GENTITIES)
    {
        Scr_ObjectError("Not an entity");
        return NULL;
    }
    entity = &g_entities[ref.entnum];
    if (!entity->pTurretInfo)
    {
        Scr_Error(usage);
        return NULL;
    }
    return entity;
}

/* IW4 0x5ed140: <turret> settargetentity(<entity>[, <offset>]) */
void CODOL_Scr_SetTargetEntity(scr_entref_t ref)
{
    gentity_s *entity = TurretTarget_Receiver(ref, "settargetentity requires a turret");
    gentity_s *target;
    turretInfo_s *turret;

    if (!entity)
    {
        return;
    }
    turret = entity->pTurretInfo;
    target = Scr_GetEntity(0);
    if (!target)
    {
        return;
    }
    TurretTarget_ApplyDefaults(entity, turret);
    turret->scriptTarget.setEnt(target);

    if (Scr_GetNumParam() > 1)
    {
        Scr_GetVector(1, turret->scriptTargetOffset);
    }
    else
    {
        VectorClear(turret->scriptTargetOffset);
    }
}

/* IW4 0x5ed1f0 drops the scripted handle and keeps the stored offset.
 * The tracked target is released by the next think, not here. */
void CODOL_Scr_ClearTargetEntity(scr_entref_t ref)
{
    gentity_s *entity = TurretTarget_Receiver(ref, "cleartargetentity requires a turret");

    if (entity)
    {
        entity->pTurretInfo->scriptTarget.setEnt(NULL);
    }
}

/* IW4 0x5ed260: <turret> getturrettarget(<requireOnAim>) */
void CODOL_Scr_GetTurretTarget(scr_entref_t ref)
{
    gentity_s *entity = TurretTarget_Receiver(ref, "getturrettarget requires a turret");
    turretInfo_s *turret;
    int requireOnAim;

    if (!entity)
    {
        return;
    }
    turret = entity->pTurretInfo;

    requireOnAim = Scr_GetInt(0);
    if (requireOnAim && !(turret->flags & CODOL_TURRET_TARGET_ONAIM))
    {
        return;
    }
    if (!turret->target.isDefined())
    {
        return;
    }
    Scr_AddEntity(turret->target.ent());
}

/* IW4 0x5ecbe0 / 0x5ecc50: the fire flag the state machine gates on. */
void CODOL_Scr_StartFiring(scr_entref_t ref)
{
    gentity_s *entity = TurretTarget_Receiver(ref, "startfiring requires a turret");

    if (entity)
    {
        entity->pTurretInfo->flags |= CODOL_TURRET_FIRE_ENABLED;
    }
}

void CODOL_Scr_StopFiring(scr_entref_t ref)
{
    gentity_s *entity = TurretTarget_Receiver(ref, "stopfiring requires a turret");

    if (entity)
    {
        /* IW4 clears the flag only; the next think takes the state to "none"
         * through the state machine, which is what notifies. */
        entity->pTurretInfo->flags &= ~CODOL_TURRET_FIRE_ENABLED;
    }
}

/* IW4 0x5eccc0 -> 0x44a6e0: the turret is "firing" while its fire state is not
 * "none", i.e. from the moment it counts as aimed at its target. */
void CODOL_Scr_IsFiringTurret(scr_entref_t ref)
{
    gentity_s *entity = TurretTarget_Receiver(ref, "isfiringturret requires a turret");

    if (entity)
    {
        Scr_AddBool(entity->pTurretInfo->fireState != CODOL_TURRET_FIRESTATE_NONE);
    }
}

/* IW4 0x5ece80 -> 0x44cc30 -> 0x5ff2f0: one shot from the turret, as its user
 * when it has one. The gate is IW4's own 0x5ff2a0 (fire-disable flag, overheat
 * penalty, barrel spin), implemented in src/codol_turret_heat.cpp; the manned
 * fire-rate timer is deliberately not consulted, because 0x44cc30/0x5ff2f0
 * neither reads nor arms it for a script shot. */
void CODOL_Scr_ShootTurret(scr_entref_t ref)
{
    gentity_s *entity = TurretTarget_Receiver(ref, "shootturret requires a turret");
    turretInfo_s *turret;
    struct WeaponDef *weapDef;

    if (!entity)
    {
        return;
    }
    turret = entity->pTurretInfo;
    weapDef = TurretTarget_WeaponDef(entity);
    if (!weapDef)
    {
        return;
    }
    /* The overheat / barrel-spin gate and the fire-sound window are inside
     * TurretTarget_Shoot, exactly as IW4 keeps them inside 0x5ff2f0. */
    TurretTarget_Shoot(entity, turret, weapDef);
}

/* IW4 0x5ed390: <turret> setconvergencetime(<seconds>[, "pitch"|"yaw"]),
 * default axis "yaw", stored as milliseconds. */
void CODOL_Scr_SetConvergenceTime(scr_entref_t ref)
{
    gentity_s *entity = TurretTarget_Receiver(ref, "setconvergencetime requires a turret");
    turretInfo_s *turret;
    int axis = 1;
    const char *name;

    if (!entity)
    {
        return;
    }
    turret = entity->pTurretInfo;
    /* Take the weapon defaults first so the explicit value is not overwritten
     * by the lazy initialisation on the first think. */
    TurretTarget_ApplyDefaults(entity, turret);

    if (Scr_GetNumParam() > 1)
    {
        name = Scr_GetString(1);
        if (!strcmp(name, "yaw"))
        {
            axis = 1;
        }
        else if (!strcmp(name, "pitch"))
        {
            axis = 0;
        }
        else
        {
            Scr_Error("setconvergencetime: axis must be \"pitch\" or \"yaw\"");
            return;
        }
    }
    /* IW4 5ed43e uses double 1000, then 6b5240 truncates toward zero. */
    turret->convergenceTime[axis] = TurretTarget_ConvertedMilliseconds(
        trunc((double)Scr_GetFloat(0) * 1000.0));
}

/* IW4 0x5ed840: <turret> setautorotationdelay(<seconds>). The value must be
 * nonnegative (despite "need a positive duration"), stored as milliseconds through
 * 0x6014a0, and its only reader in IW4 is the barrel spin update 0x60154a,
 * where it is how long the barrel keeps spinning after the last spin request.
 * IW4 rounds a float millisecond value plus 2^-30 under the current rounding
 * mode. Its zero comparison accepts zero; only negative durations error. */
void CODOL_Scr_SetAutoRotationDelay(scr_entref_t ref)
{
    gentity_s *entity = TurretTarget_Receiver(ref, "setautorotationdelay requires a turret");
    float seconds;

    if (!entity)
    {
        return;
    }
    seconds = Scr_GetFloat(0);
    if (seconds < 0.0f)
    {
        Scr_Error("need a positive duration");
        return;
    }
    entity->pTurretInfo->spinLingerTime = TurretTarget_ConvertedMilliseconds(
        nearbyint((double)(float)((double)seconds * 1000.0) +
                  9.313225746154785e-10));
}

/* C1 startbarrelspin 0x536620 / stopbarrelspin 0x5366b0: the script request
 * bit the barrel spin update tests together with the fire flag (C1 0x57b160,
 * "flags & 0x100010"). Stopping also clears the spin request time, which ends
 * the linger immediately (C1 0x53673d). */
void CODOL_Scr_StartBarrelSpin(scr_entref_t ref)
{
    gentity_s *entity = TurretTarget_Receiver(ref, "startbarrelspin requires a turret");

    if (entity)
    {
        entity->pTurretInfo->flags |= CODOL_TURRET_SPIN_REQUESTED;
    }
}

void CODOL_Scr_StopBarrelSpin(scr_entref_t ref)
{
    gentity_s *entity = TurretTarget_Receiver(ref, "stopbarrelspin requires a turret");

    if (entity)
    {
        entity->pTurretInfo->flags &= ~CODOL_TURRET_SPIN_REQUESTED;
        entity->pTurretInfo->spinRequestTime = 0;
    }
}

/* C1 setmode 0x54e0d0: <turret> setmode(<"manual"|"manual_ai"|"auto_nonai"|
 * "auto_ai"|"sentry"|"sentry_offline">). Any other name is a script error, as
 * it is at C1 0x54e318. */
void CODOL_Scr_SetMode(scr_entref_t ref)
{
    gentity_s *entity = TurretTarget_Receiver(ref, "setmode requires a turret");

    if (!entity)
    {
        return;
    }
    if (!CODOL_TurretHeat_SetMode(entity, Scr_GetString(0)))
    {
        Scr_Error("setmode: unknown turret mode");
    }
}

/* C1 getmode 0x54e330. */
void CODOL_Scr_GetMode(scr_entref_t ref)
{
    gentity_s *entity = TurretTarget_Receiver(ref, "getmode requires a turret");
    const char *mode;

    if (!entity)
    {
        return;
    }
    mode = CODOL_TurretHeat_GetMode(entity);
    if (mode)
    {
        Scr_AddString(mode);
    }
}

/* C1 setsentryowner 0x536970: <turret> setsentryowner(<entity|undefined>). The receiver
 * must be in an auto or sentry mode (C1 0x5369ee tests its flags & 0xc and
 * otherwise raises "turret number '%i' is not auto or sentry"), and the owner
 * entity number is stored in the entity state (C1 0x536a92 writes ent+0x80).
 * This fork publishes it through s.otherEntityNum so the snapshot archives it;
 * team-3 acquisition then skips the owner. C1 additionally prints a warning
 * when a different owner was already set, which has no equivalent here. */
void CODOL_Scr_SetSentryOwner(scr_entref_t ref)
{
    gentity_s *entity = TurretTarget_Receiver(ref, "setsentryowner requires a turret");
    gentity_s *owner;

    if (!entity)
    {
        return;
    }
    if (!(entity->pTurretInfo->flags &
          (CODOL_TURRET_MODE_AUTO | CODOL_TURRET_MODE_SENTRY)))
    {
        Scr_Error("setsentryowner: turret is not auto or sentry");
        return;
    }
    /* C1 distinguishes a missing argument (536a32) from an explicit
     * undefined value (536a3f ->536af4), which clears the archived owner. */
    if (Scr_GetNumParam() == 0)
    {
        Scr_Error("setsentryowner requires an entity or undefined argument");
        return;
    }
    if (Scr_GetType(0) == VAR_UNDEFINED)
    {
        entity->s.otherEntityNum = ENTITYNUM_NONE;
        return;
    }
    owner = Scr_GetEntity(0);
    if (!owner)
    {
        return;
    }
    entity->s.otherEntityNum = owner->s.number;
}

/* C1 setturretteam 0x537370: <turret> setturretteam(<"axis"|"allies"|"team3">).
 * The team selects which candidate class the acquisition iterator walks; any
 * other name is a script error, as it is at C1 0x5374c4. The codes are the
 * ones C1 stores in its turret +0x78 and are the same 1/2/3 encoding this
 * fork's CoDOL client state conversion uses for TEAM_RED/TEAM_BLUE. */
void CODOL_Scr_SetTurretTeam(scr_entref_t ref)
{
    gentity_s *entity = TurretTarget_Receiver(ref, "setturretteam requires a turret");
    const char *team;

    if (!entity)
    {
        return;
    }
    team = Scr_GetString(0);
    if (!strcmp(team, "axis"))
    {
        entity->pTurretInfo->turretTeam = CODOL_TURRET_TEAM_AXIS;
    }
    else if (!strcmp(team, "allies"))
    {
        entity->pTurretInfo->turretTeam = CODOL_TURRET_TEAM_ALLIES;
    }
    else if (!strcmp(team, "team3"))
    {
        entity->pTurretInfo->turretTeam = CODOL_TURRET_TEAM_THREE;
    }
    else
    {
        Scr_Error("setturretteam: unknown team");
        return;
    }
    /* C1 537461/53747d/537499 writes only the team; it preserves the
     * acquisition cursor and the currently tracked target. */
}

/* C1 0x537c70 (IW4 record 0x73d504 "setturretmodechangewait" -> 0x5edab0):
 * <turret> setturretmodechangewait(<bool>) sets the flag the auto path checks
 * before it acquires after a mode change. */
void CODOL_Scr_SetTurretModeChangeWait(scr_entref_t ref)
{
    gentity_s *entity = TurretTarget_Receiver(ref, "setturretmodechangewait requires a turret");

    if (!entity)
    {
        return;
    }
    if (Scr_GetInt(0))
    {
        entity->pTurretInfo->flags |= CODOL_TURRET_MODE_CHANGE_WAIT;
    }
    else
    {
        entity->pTurretInfo->flags &= ~CODOL_TURRET_MODE_CHANGE_WAIT;
    }
}

/* C1 0x55a6d0: <turret> setscanningpitch(<pitch>). Exactly one argument
 * ("illegal call to SetScanningPitch()" otherwise), a turret receiver
 * ("entity is not a turret"), and the float is stored unclamped as the pitch
 * the auto-rotation sweep holds (C1 turret +0x20). */
void CODOL_Scr_SetScanningPitch(scr_entref_t ref)
{
    gentity_s *entity;

    if (Scr_GetNumParam() != 1)
    {
        Scr_Error("illegal call to SetScanningPitch()");
        return;
    }
    entity = TurretTarget_Receiver(ref, "entity is not a turret");
    if (!entity)
    {
        return;
    }
    entity->pTurretInfo->scanningPitch = Scr_GetFloat(0);
}

/* C1 0x536bf0 (IW4 record 0x73d3f0 "setsentrycarried" -> 0x5ed040):
 * <turret> setsentrycarried(<bool>), only on a sentry-mode turret. A carried
 * sentry does not acquire (C1 0x57cf52). */
void CODOL_Scr_SetSentryCarried(scr_entref_t ref)
{
    gentity_s *entity = TurretTarget_Receiver(ref, "setsentrycarried requires a turret");

    if (!entity)
    {
        return;
    }
    if (!(entity->pTurretInfo->flags & CODOL_TURRET_MODE_SENTRY))
    {
        Scr_Error("setsentrycarried: turret is not a sentry");
        return;
    }
    entity->pTurretInfo->sentryCarried = Scr_GetInt(0) ? 1 : 0;
}

/* ------------------------------------------------------------------------
 * Auto / sentry turret behaviour, measured in C1.
 *
 * C1's turret think 0x57dc20 routes an unmanned turret whose mode is "auto,
 * not AI driven" (its flags 0x4 set and 0x800 clear) into 0x57cee0, which is:
 *
 *   if ((flags & 0x200000) && modeChangeTime > 0 &&
 *       level.time > modeChangeTime + 500) {          ; 0x57cef3..0x57cf11
 *       clear the tracked target; fireState = 0; targetChangeTime = level.time
 *       if (!converge(ent, {0,0}, weaponRates)) return;   ; still settling
 *       modeChangeTime = 0;
 *   }
 *   if (!(flags & 0x400000)) acquired = acquire(ent);  ; carried sentries skip
 *   if (acquired && aim(ent, acquired)) { converge; return; }
 *   ... scripted target ...                            ; 0x57cfcc
 *   clear the tracked target                           ; 0x57d01b
 *
 * Acquisition 0x57ccf0 keeps the current target while it stays valid and
 * level.time <= targetChangeTime + 4000 (0x57cda5), otherwise takes the next
 * candidate from the round-robin iterator 0x57cc30, which walks a global
 * per-class list with the cursor in turret+0x74 and selects the class from
 * turret+0x78 - the team that setturretteam 0x537370 writes ("axis" 1,
 * "allies" 2, "team3" 3; the spawn default 4 acquires nothing, 0x57cd16).
 * C1's list is its sentient registry, which this fork does not have; the
 * equivalent candidate set here is the connected playing clients, walked with
 * the same one-candidate-per-think cursor.
 *
 * Validation 0x57ca30 rejects a target that is flagged untargetable, then
 * requires the squared distance from the turret entity to be strictly inside
 * the turret range gate, computes the aim point through 0x57c030 and finishes
 * with the sight trace at 0x57cbd8. 0x57c030 is the whole of C1's "lead": in
 * the firing state the aim point is the target's own aim position (for a
 * player, its view origin), otherwise the target origin raised by 2.0 units.
 * There is no velocity extrapolation anywhere in the chain. */

/* C1 0x57c030. In the firing state it asks the target's sentient for its eye
 * (0x578a10): an actor answers with its own eye (actor +0xffc), a client with
 * its view origin. Aiming an actor at its feet instead sent nearly every
 * sentry round into the floor between a zombie's legs (measured 2026-09-24:
 * 271 rounds, one hit). */
static void TurretAuto_AimPoint(turretInfo_s *turret, gentity_s *target, vec3_t out)
{
    if (turret->fireState == CODOL_TURRET_FIRESTATE_FIRING && target->client)
    {
        G_GetPlayerViewOrigin(&target->client->ps, out);
    }
    else if (turret->fireState == CODOL_TURRET_FIRESTATE_FIRING &&
             CODOL_ActorEyePosition(target, out))
    {
    }
    else
    {
        VectorCopy(target->r.currentOrigin, out);
        out[2] += CODOL_TURRET_AIM_HEIGHT;
    }
    VectorAdd(out, turret->scriptTargetOffset, out);
}

/* C1 0x57cbd8: the shot has to reach the aim point, ignoring both the turret
 * and the target.
 *
 * SV_SightTrace's hitNum is not an entity number. On entry it seeds
 * CM_BoxSightTrace's cached-brush test and must be 0; on return it is 0 for a
 * clear line and nonzero when anything blocked it. This test used to seed it
 * with ENTITYNUM_NONE and read a 0 result as "blocked by entity 0", so every
 * clear line was refused unless the target was entity 0: an auto turret
 * never acquired a zombie in zombies (measured
 * 2026-09-24, developer trace in TurretAuto_Acquire). */
static qboolean TurretAuto_LineOfSight(gentity_s *entity, gentity_s *target,
                                       const vec3_t muzzle, const vec3_t aimPos)
{
    int hitNum = 0;

    SV_SightTrace(&hitNum, muzzle, vec3_origin, vec3_origin, aimPos,
                  entity->s.number, target->s.number, CODOL_TURRET_SIGHT_MASK);
    return hitNum == 0 ? qtrue : qfalse;
}

/* C1 0x57ca30. distSqOut receives the squared distance from the turret to the
 * aim point, which C1 writes through its fourth argument (0x57cc14) and its
 * caller uses to arbitrate between the old and the new target. */
static qboolean TurretAuto_ValidateTarget(gentity_s *entity, turretInfo_s *turret,
                                          gentity_s *target, vec3_t aimOut, float goal[2],
                                          float *distSqOut)
{
    vec3_t delta;
    vec3_t muzzle;
    float distSq;

    if (!target || !TurretTarget_ValidTarget(target) || target->health <= 0)
    {
        return qfalse;
    }
    TurretAuto_AimPoint(turret, target, aimOut);
    VectorSubtract(aimOut, entity->r.currentOrigin, delta);
    distSq = VectorLengthSquared(delta);
    if (distSqOut)
    {
        *distSqOut = distSq;
    }
    if (!(distSq < turret->targetRangeSq))
    {
        return qfalse;
    }
    if (!TurretTarget_CanBearOn(entity, turret, target, aimOut, goal))
    {
        return qfalse;
    }
    /* C1 runs the friendly sweep at 0x57cb80 between the bear test that
     * produced the muzzle and the sight trace at 0x57cbd8, on the same
     * muzzle. */
    if (!TurretTarget_MuzzlePosition(entity, muzzle))
    {
        return qfalse;
    }
    if (TurretAuto_FriendlyBlocked(turret, target, muzzle, aimOut))
    {
        return qfalse;
    }
    return TurretAuto_LineOfSight(entity, target, muzzle, aimOut);
}

/* C1 keeps the turret's own team in turret+0x78 and every candidate's team in
 * the sentient record (+0x08). Both are the same small class number, so no
 * translation happens anywhere in the turret family: setturretteam writes
 * 1/2/3 and the registry stores 1/2/3/4. */
static qboolean TurretAuto_TeamIsSet(const turretInfo_s *turret)
{
    return (turret->turretTeam >= CODOL_TURRET_TEAM_AXIS &&
            turret->turretTeam <= CODOL_TURRET_TEAM_THREE) ? qtrue : qfalse;
}

/* ------------------------------------------------------------------------
 * Friendly blocker, C1 predicate 0x57c8e0 and its caller loop 0x57cb80.
 *
 * The loop runs over C1's client entity slots (fixed stride 0x2cc, bound
 * 0x3524 = 19 slots) and skips a slot whose per-client in-use byte
 * (0x24375b8 + i, the same table every other C1 client loop gates on, e.g.
 * 0x5726a7 which bounds itself with level.maxclients at 0x24b5010) is zero.
 * A slot is a friendly when its sentient (entity+0x184) carries the same team
 * at +0x8 as the turret's own team in turretInfo+0x78, i.e. the team
 * setturretteam writes. Here the candidate set is this fork's connected
 * clients, walked to level.maxclients, and the team comes from the client
 * session; the class-3 turret has no counterpart in this fork's team set, so
 * such a turret has no friendlies to be blocked by - the same gap the
 * acquisition iterator already documents.
 *
 * The predicate takes the friendly in eax, the tag_aim muzzle in esi, the
 * target in edi and the aim offset on the stack:
 *
 *   friendlyPoint = friendly->r.currentOrigin + friendly->r.mins;  ; 0x57c905
 *   d1 = friendlyPoint - muzzle; len1 = Vec3Normalize(d1);         ; 0x57c947
 *   if (len1 < 0.001) return blocked;                              ; 0x57c952
 *   targetPoint = target->r.currentOrigin + target->r.mins + offset; 0x57c988
 *   d2 = targetPoint - muzzle; len2 = Vec3Normalize(d2);           ; 0x57c9e0
 *   if (len1 > len2) return clear;                                 ; 0x57c9ef
 *   return DotProduct(d1, d2) > dvar->current.value;               ; 0x57ca16
 *
 * 0x57c905/0x57c988 read entity+0x118 and entity+0x14c, which are r.mins and
 * r.currentOrigin: C1's entityState is 0x10 bytes longer than this fork's, so
 * the whole entityShared block sits at this fork's offsets plus 0x10 (mins
 * 0x108 -> 0x118, maxs 0x114 -> 0x124, contents 0x120 -> 0x130, absmin 0x124
 * -> 0x134, absmax 0x130 -> 0x140, currentOrigin 0x13c -> 0x14c,
 * currentAngles 0x148 -> 0x158). Both body points are therefore the entity
 * origin plus its own bounding-box minimum, and the target additionally
 * carries the aim offset that 0x57ca30 was called with. That offset is what
 * this fork's aim point already folds in: 0x57ca30 forms its aim point as
 * target->r.currentOrigin + offset (0x57ca70 and again at 0x57cb53), so
 * offset == aimPos - target->r.currentOrigin and the predicate's target point
 * is exactly aimPos + target->r.mins.
 *
 * There is no corridor width and no radius anywhere in the pair: the only
 * distance term is the 0.001 degeneracy epsilon at 0xc84274, and the shape of
 * the test is a cone around the line of fire whose cosine is the dvar read at
 * 0x57c9f7 through the pointer at 0x220cf88. */

/* 0xc84274: a friendly standing on the muzzle always blocks, because its
 * direction cannot be normalized. */
#define CODOL_TURRET_BLOCK_EPSILON 0.001f

/* C1 registers the cone dvar at 0x52bea2 (value 0.95, minimum 0, maximum
 * FLT_MAX) and keeps the pointer in 0x220cf88. The shipped C1 has its dvar
 * names stripped to ordinals - this one registers as "1332" - so the name
 * below is this fork's; the value, the limits and the read site are C1's.
 * C1's flag word is 0xc4: serverinfo, read-only and cheat-protected. The
 * serverinfo bit is dropped here because this fork's serverinfo string is
 * what CoD4 clients parse; read-only keeps the value where C1 pins it. */
static float TurretAuto_FriendlyBlockDot(void)
{
    static cvar_t *blockDot = NULL;

    if (!blockDot)
    {
        blockDot = Cvar_RegisterFloat("codol_turretFriendlyBlockDot", 0.95f, 0.0f, FLT_MAX,
                                      CVAR_ROM | CVAR_CHEAT,
                                      "Cosine of the cone in which a friendly player blocks an auto turret's shot");
    }
    return blockDot->floatval;
}

/* C1 0x57c8e0. */
static qboolean TurretAuto_FriendlyBlocks(gentity_s *friendly, const vec3_t muzzle,
                                          const vec3_t targetPoint, float blockDot)
{
    vec3_t toFriendly;
    vec3_t toTarget;
    float friendlyDist;
    float targetDist;

    VectorAdd(friendly->r.currentOrigin, friendly->r.mins, toFriendly);
    VectorSubtract(toFriendly, muzzle, toFriendly);
    friendlyDist = VectorNormalize(toFriendly);
    if (friendlyDist < CODOL_TURRET_BLOCK_EPSILON)
    {
        return qtrue;
    }

    VectorSubtract(targetPoint, muzzle, toTarget);
    targetDist = VectorNormalize(toTarget);
    if (friendlyDist > targetDist)
    {
        return qfalse;
    }
    return (DotProduct(toFriendly, toTarget) > blockDot) ? qtrue : qfalse;
}

/* C1 0x57cb80. */
static qboolean TurretAuto_FriendlyBlocked(turretInfo_s *turret, gentity_s *target,
                                           const vec3_t muzzle, const vec3_t aimPos)
{
    vec3_t targetPoint;
    float blockDot;
    unsigned int ownMask;
    codol_sentient_t *sentient;

    if (!TurretAuto_TeamIsSet(turret))
    {
        return qfalse;
    }
    ownMask = 1u << turret->turretTeam;
    blockDot = TurretAuto_FriendlyBlockDot();
    VectorAdd(aimPos, target->r.mins, targetPoint);

    for (sentient = CODOL_Sentient_First(ownMask); sentient;
         sentient = CODOL_Sentient_Next(sentient, ownMask))
    {
        if (!sentient->entity || sentient->entity == target)
        {
            continue;
        }
        if (TurretAuto_FriendlyBlocks(sentient->entity, muzzle, targetPoint, blockDot))
        {
            return qtrue;
        }
    }
    return qfalse;
}

/* C1 0x57cc30: one candidate per think out of the sentient registry. The class
 * mask comes from the table C1 builds at 0x57cc51 and indexes with the
 * turret's own team, the cursor is the pool index in turret+0x74 (0x57ccbc),
 * a cursor of -1 restarts at the first record (0x57cc94 -> 0x578e70) and
 * running out of records resets the cursor to -1 (0x57ccd7). */
static gentity_s *TurretAuto_NextCandidate(turretInfo_s *turret)
{
    unsigned int classMask = CODOL_Sentient_ClassMask(turret->turretTeam);
    codol_sentient_t *sentient;

    if (!classMask)
    {
        turret->acquireCursor = -1;
        return NULL;
    }
    if (turret->acquireCursor > -1)
    {
        sentient = CODOL_Sentient_Next(CODOL_Sentient_ByIndex(turret->acquireCursor), classMask);
    }
    else
    {
        sentient = CODOL_Sentient_First(classMask);
    }
    if (!sentient)
    {
        turret->acquireCursor = -1;
        return NULL;
    }
    turret->acquireCursor = CODOL_Sentient_Index(sentient);
    return sentient->entity;
}

/* C1 0x57ccf0, in its measured order.
 *
 *   if (team is not 1..3) { warn 0xc5ea88; clear the aim; return NULL; }
 *   tracked = NULL;
 *   if (flags & 0x20 and the tracked entity is set) {              ; 0x57cd3d
 *       if (the tracked entity has a sentient                      ; 0x57cd52
 *           && tracked->health > 0                                 ; 0x57cd5a
 *           && !sentient->dontTarget                               ; 0x57cd81
 *           && validate(tracked)) {                                ; 0x57cd92
 *           if (level.time <= targetChangeTime + 4000) return tracked;
 *           tracked stays as a fallback;                           ; 0x57cda5
 *       }
 *   }
 *   candidate = nextCandidate();                                   ; 0x57cdbd
 *   if (!candidate) return tracked;
 *   if (candidate's sentient says dontTarget) return tracked;      ; 0x57cdd6
 *   if (team == 3 && candidate is the sentry owner) return tracked;; 0x57cde9
 *   if (mode is sentry && candidate is neither a client nor an actor)
 *       return tracked;                                            ; 0x57cdf7
 *   if (the candidate's sentient is owned by the sentry owner) return tracked;
 *                                                                  ; 0x57ce17
 *   if (candidate->health <= 0) return tracked;                    ; 0x57ce30
 *   if (!validate(candidate)) return tracked;                      ; 0x57ce4a
 *   if (tracked && trackedDistSq <= candidateDistSq) return tracked;; 0x57ce97
 *   return candidate;
 *
 * The one structural difference from C1: C1's validation takes an aim offset
 * and returns the offset to keep, while this fork's aim producer returns the
 * aim position itself, so the arbitration below carries positions. */
static gentity_s *TurretAuto_Acquire(gentity_s *entity, turretInfo_s *turret,
                                     vec3_t aimOut, float goal[2])
{
    gentity_s *tracked = NULL;
    gentity_s *candidate;
    codol_sentient_t *sentient;
    vec3_t trackedAim;
    float trackedGoal[2];
    float trackedDistSq = 0.0f;
    float candidateDistSq = 0.0f;
    int sentryOwner;

    if (!TurretAuto_TeamIsSet(turret))
    {
        /* C1 0x57cd16 warns and acquires nothing until setturretteam runs. */
        return NULL;
    }
    sentryOwner = entity->s.otherEntityNum;

    if ((turret->flags & CODOL_TURRET_TARGET_ONAIM) && turret->target.isDefined())
    {
        gentity_s *previous = turret->target.ent();

        sentient = CODOL_Sentient_ForEntity(previous);
        if (previous && sentient && !sentient->dontTarget && previous->health > 0 &&
            TurretAuto_ValidateTarget(entity, turret, previous, trackedAim, trackedGoal,
                                      &trackedDistSq))
        {
            if (level.time <= turret->targetChangeTime + CODOL_TURRET_ACQUIRE_HOLD_MSEC)
            {
                VectorCopy(trackedAim, aimOut);
                goal[0] = trackedGoal[0];
                goal[1] = trackedGoal[1];
                return previous;
            }
            tracked = previous;
        }
    }

    candidate = TurretAuto_NextCandidate(turret);
    sentient = candidate ? CODOL_Sentient_ForEntity(candidate) : NULL;
    /* Developer trace, once a second per turret: the candidate this think
     * offered and why it was refused. An acquisition that never fires is
     * otherwise silent. */
    if (candidate && sentient && !sentient->dontTarget &&
        !(turret->turretTeam == CODOL_TURRET_TEAM_THREE &&
          sentryOwner == candidate->s.number) &&
        !((turret->flags & CODOL_TURRET_MODE_SENTRY) && !candidate->client &&
          !sentient->isActor) &&
        !(sentient->ownerNum >= 0 && sentient->ownerNum == sentryOwner) &&
        candidate->health > 0 &&
        TurretAuto_ValidateTarget(entity, turret, candidate, aimOut, goal, &candidateDistSq) &&
        !(tracked && trackedDistSq <= candidateDistSq))
    {
        return candidate;
    }

    if (tracked)
    {
        VectorCopy(trackedAim, aimOut);
        goal[0] = trackedGoal[0];
        goal[1] = trackedGoal[1];
    }
    return tracked;
}

/* ------------------------------------------------------------------------
 * Auto-rotation sweep, C1 0x57b610, reached at 0x57d030 for a sentry-mode
 * turret that is not offline and has no target:
 *
 *   gunAngles[0] = AngleApproach(turret->scanningPitch, gunAngles[0],
 *                                weapDef->turretSweepRate, 0.05);   ; 0x57b650
 *   if (gunAngles[0] != turret->scanningPitch) return;              ; 0x57b661
 *   if (flags & 0x100) { remaining = gunAngles[1] - arcmin[1]; dir = -1; }
 *   else               { remaining = arcmax[1] - gunAngles[1]; dir = +1; }
 *   if (!(flags & 0x80)) {                                          ; 0x57b570
 *       flags |= 0x80; speed = 0;
 *       resumeTime = level.time + weapDef->turretSweepDelay;
 *       brake = rate*rate / (2*accel);
 *       if (remaining * 0.5 < brake) brake = remaining * 0.5;
 *   }
 *   if (level.time < resumeTime) return;                            ; 0x57b6b1
 *   if (brake <= remaining) { speed += accel*0.05;
 *                             if (speed >= rate) speed = rate; }     ; 0x57b724
 *   else { speed -= accel*0.05;
 *          if (speed <= 0) { flags &= ~0x80; flags ^= 0x100;         ; 0x57b5e0
 *                            speed = brake = 0; resumeTime = 0; return; } }
 *   gunAngles[1] += dir * 0.05 * speed;                             ; 0x57b755
 *
 * The pitch is C1 turret +0x20 (0x57b64a / 0x57b661), the scanning pitch, not
 * the drop pitch at +0x1c. Sweeping at the drop pitch held a placed sentry at
 * the -89 its script sets for carrying, so it scanned the sky.
 *
 * The three weapon values are asset-backed exactly like the heat and spin
 * curves: C1 reads them from its weapon definition at +0xa14, +0xa18 and
 * +0xa1c, and the CoDOL weapon loader publishes them under the same names. */

struct codol_turretSweepParams_t
{
    float rate;
    float accel;
    int delay;
};

static qboolean TurretSweep_Params(gentity_s *entity, codol_turretSweepParams_t *out)
{
    struct WeaponDef *weapDef;

    out->rate = 0.0f;
    out->accel = 0.0f;
    out->delay = 0;
    weapDef = TurretTarget_WeaponDef(entity);
    if (!weapDef)
    {
        return qfalse;
    }
#ifdef CODOL_WEAPONDEF_TURRET_SWEEP
    out->rate = weapDef->turretSweepRate;
    out->accel = weapDef->turretSweepAccel;
    out->delay = weapDef->turretSweepDelay;
#endif
    /* C1 divides by twice the acceleration when it sizes the braking distance
     * and clamps the ramp at the rate; a weapon carrying neither cannot
     * sweep, which is C1's behaviour for such a weapon too. */
    return (out->rate > 0.0f && out->accel > 0.0f) ? qtrue : qfalse;
}

/* C1 0x618b20: step current toward target by at most rate*dt on the shortest
 * way round, landing exactly on the target once it is within one step, which
 * is what C1's equality test at 0x57b661 depends on. */
static float TurretSweep_Approach(float target, float current, float rate, float seconds)
{
    float maxStep = rate * seconds;
    float delta = TurretTarget_Normalize180(target - current);

    if (delta > maxStep)
    {
        return current + maxStep;
    }
    if (delta < -maxStep)
    {
        return current - maxStep;
    }
    return target;
}

/* C1 0x57b5e0. */
static void TurretSweep_Reverse(turretInfo_s *turret)
{
    turret->sweepFlags &= ~CODOL_TURRET_SWEEP_LEG;
    turret->sweepFlags ^= CODOL_TURRET_SWEEP_REVERSE;
    turret->sweepSpeed = 0.0f;
    turret->sweepBrake = 0.0f;
    turret->sweepResumeTime = 0;
}

/* C1 0x57b610. Returns qtrue when it owned the gun angles this think. */
static qboolean TurretAuto_Sweep(gentity_s *entity, turretInfo_s *turret)
{
    codol_turretSweepParams_t params;
    float *gunAngles = entity->s.lerp.u.turret.gunAngles;
    float seconds = (float)CODOL_TURRET_THINK_MSEC / 1000.0f;
    float remaining;
    float direction;
    float step;

    if (!TurretSweep_Params(entity, &params))
    {
        return qfalse;
    }

    gunAngles[0] = TurretSweep_Approach(turret->scanningPitch, gunAngles[0], params.rate, seconds);
    if (gunAngles[0] != turret->scanningPitch)
    {
        return qtrue;
    }

    if (turret->sweepFlags & CODOL_TURRET_SWEEP_REVERSE)
    {
        remaining = gunAngles[1] - turret->arcmin[1];
        direction = -1.0f;
    }
    else
    {
        remaining = turret->arcmax[1] - gunAngles[1];
        direction = 1.0f;
    }

    if (!(turret->sweepFlags & CODOL_TURRET_SWEEP_LEG))
    {
        float brake = params.rate * params.rate / (2.0f * params.accel);
        float half = remaining * 0.5f;

        turret->sweepFlags |= CODOL_TURRET_SWEEP_LEG;
        turret->sweepSpeed = 0.0f;
        turret->sweepResumeTime = (int)((uint32_t)level.time + (uint32_t)params.delay);
        turret->sweepBrake = (half < brake) ? half : brake;
    }

    if (level.time < turret->sweepResumeTime)
    {
        return qtrue;
    }

    step = params.accel * seconds;
    if (turret->sweepBrake <= remaining)
    {
        turret->sweepSpeed += step;
        if (turret->sweepSpeed >= params.rate)
        {
            turret->sweepSpeed = params.rate;
        }
    }
    else
    {
        turret->sweepSpeed -= step;
        if (turret->sweepSpeed <= 0.0f)
        {
            TurretSweep_Reverse(turret);
            return qtrue;
        }
    }
    gunAngles[1] += direction * seconds * turret->sweepSpeed;
    return qtrue;
}

/* C1 0x57cee0. Returns qtrue when it owned the gun angles this think. */
static qboolean TurretAuto_Think(gentity_s *entity, turretInfo_s *turret)
{
    vec3_t aimPos;
    float goal[2] = { 0.0f, 0.0f };
    gentity_s *target;
    qboolean fireEnabled;

    VectorClear(aimPos);
    if ((turret->flags & CODOL_TURRET_MODE_CHANGE_WAIT) && turret->modeChangeTime > 0 &&
        level.time > turret->modeChangeTime + CODOL_TURRET_MODE_SETTLE_MSEC)
    {
        TurretTarget_ClearTracked(entity, turret);
        turret->targetChangeTime = level.time;
        goal[0] = 0.0f;
        goal[1] = 0.0f;
        if (!TurretTarget_Converge(entity, turret, goal, qtrue))
        {
            /* Still settling; C1 0x57cf43 keeps the frame until the gun is
             * back on the neutral angles. */
            return qtrue;
        }
        turret->modeChangeTime = 0;
    }

    target = turret->sentryCarried ? NULL : TurretAuto_Acquire(entity, turret, aimPos, goal);
    if (!target)
    {
        /* C1 0x57d01b drops the tracked target and then sweeps, but only for a
         * sentry that is not offline (0x57d023 / 0x57d028); every other mode
         * falls through to the scripted target and the shared idle writer. */
        if ((turret->flags & CODOL_TURRET_MODE_SENTRY) &&
            !(turret->flags & CODOL_TURRET_MODE_OFFLINE))
        {
            TurretTarget_ClearTracked(entity, turret);
            if (TurretAuto_Sweep(entity, turret))
            {
                return qtrue;
            }
        }
        return qfalse;
    }

    TurretTarget_SetTracked(turret, target, aimPos);
    turret->flags |= CODOL_TURRET_TARGET_ONAIM;
    VectorCopy(aimPos, turret->aimPos);
    /* C1 0x57cf9d hands the target aim 0x57c530 a constant 1 as its fire flag
     * (the argument 0x57c571 passes on to the fire state 0x57c310): an auto or
     * sentry turret always engages what it acquired. The startfiring flag
     * only gates scripted targets. Reading it here left a placed sentry in
     * the "none" fire state, so it never raised "turretstatechange" and
     * sentry_attackTargets never shot. */
    fireEnabled = qtrue;
    TurretTarget_UpdateFireState(entity, turret, fireEnabled, goal, qtrue);
    TurretTarget_Converge(entity, turret, goal, qtrue);
    return qtrue;
}

qboolean CODOL_TurretTarget_Think(gentity_s *entity)
{
    turretInfo_s *turret = entity->pTurretInfo;
    gentity_s *target;
    vec3_t aimPos;
    vec3_t delta;
    float goal[2] = { 0.0f, 0.0f };
    qboolean canBear;
    qboolean fireEnabled;

    if (!turret)
    {
        return qfalse;
    }
    TurretTarget_ApplyDefaults(entity, turret);
    /* IW4 0x45c73f/0x45c747 run the barrel spin update and then the overheat
     * update on the unmanned branch, before anything aims. The user entity of
     * an unmanned turret has no client, which is the branch the spin update
     * takes for NULL here. */
    CODOL_TurretHeat_Update(entity, NULL);

    /* C1 0x57dca1: an auto-mode turret that is not AI driven runs its own
     * acquisition before the scripted target is considered. */
    if ((turret->flags & CODOL_TURRET_MODE_AUTO) && !(turret->flags & CODOL_TURRET_MODE_AI) &&
        TurretAuto_Think(entity, turret))
    {
        return qtrue;
    }

    if (turret->scriptTarget.isDefined())
    {
        target = turret->scriptTarget.ent();
        if (target && TurretTarget_ValidTarget(target))
        {
            VectorAdd(target->r.currentOrigin, turret->scriptTargetOffset, aimPos);
            /* IW4 0x601274 measures the range gate from the turret entity
             * origin, not from the muzzle. */
            VectorSubtract(aimPos, entity->r.currentOrigin, delta);
            if (VectorLengthSquared(delta) < turret->targetRangeSq)
            {
                TurretTarget_SetTracked(turret, target, aimPos);
                canBear = TurretTarget_CanBearOn(entity, turret, target, aimPos, goal);
                if (canBear)
                {
                    turret->flags |= CODOL_TURRET_TARGET_ONAIM;
                    VectorCopy(aimPos, turret->aimPos);
                }
                else
                {
                    turret->flags &= ~CODOL_TURRET_TARGET_ONAIM;
                }

                /* IW4 0x600760 runs the fire state machine on both can-bear
                 * outcomes, with the script fire flag alone (0x600784 and
                 * 0x6007a5 both push arg1, the flag 0x601216 extracted from
                 * turret->flags & 0x10). */
                fireEnabled = (turret->flags & CODOL_TURRET_FIRE_ENABLED) ? qtrue : qfalse;
                TurretTarget_UpdateFireState(entity, turret, fireEnabled, goal, canBear);
                /* IW4 script-target think produces aiming/state notifies;
                 * scripts decide when to call shootturret. No extra native shot. */
                if (canBear)
                {
                    TurretTarget_Converge(entity, turret, goal, qtrue);
                }
                /* IW4 keeps the frame even when it cannot bear: the gun holds
                 * its angles instead of drifting back to idle. */
                return qtrue;
            }
        }
    }

    TurretTarget_ClearTracked(entity, turret);
    /* IW4 6012fe..60135b handles the no-target branch itself and returns true.
     * The same convergence routine applies the idle pitch/yaw and pitch caps. */
    goal[0] = turret->dropPitch;
    goal[1] = 0.0f;
    TurretTarget_Converge(entity, turret, goal, qfalse);
    return qtrue;
}

void CODOL_TurretTarget_Free(gentity_s *entity)
{
    turretInfo_s *turret = entity->pTurretInfo;

    if (!turret)
    {
        return;
    }
    /* Deregister before G_FreeTurret hands the slot back, otherwise the
     * EntHandle registry keeps pointers into a reused slot. Notifying here
     * would run script on a turret that is being destroyed, so the fire state
     * is dropped silently. */
    turret->target.setEnt(NULL);
    turret->scriptTarget.setEnt(NULL);
    turret->flags &= ~(CODOL_TURRET_TARGET_ONAIM | CODOL_TURRET_FIRE_ENABLED |
                       CODOL_TURRET_TARGET_INITED);
    turret->fireState = CODOL_TURRET_FIRESTATE_NONE;
    turret->stateChangeTime = 0;
    turret->triggerDown = 0;
    turret->sweepSpeed = 0.0f;
    turret->sweepBrake = 0.0f;
    turret->sweepResumeTime = 0;
    turret->sweepFlags = 0;
    turret->onTargetCos = 0.0f;
    turret->flags &= ~(int)CODOL_TURRET_OFF_CONE;
    CODOL_TurretHeat_Reset(turret);
}

void CODOL_TurretTarget_ResetAll(void)
{
    int i;

    /* Raw clear: at level init the handle registry is reinitialised too, so
     * setEnt() would walk stale info indices. */
    for (i = 0; i < CODOL_MAX_TURRETS; ++i)
    {
        memset(&turretInfo[i].target, 0, sizeof(turretInfo[i].target));
        memset(&turretInfo[i].scriptTarget, 0, sizeof(turretInfo[i].scriptTarget));
        VectorClear(turretInfo[i].scriptTargetOffset);
        VectorClear(turretInfo[i].targetPos);
        VectorClear(turretInfo[i].aimPos);
        turretInfo[i].targetChangeTime = 0;
        turretInfo[i].targetRangeSq = 0.0f;
        turretInfo[i].convergenceTime[0] = 0;
        turretInfo[i].convergenceTime[1] = 0;
        turretInfo[i].fireState = CODOL_TURRET_FIRESTATE_NONE;
        turretInfo[i].stateChangeTime = 0;
        turretInfo[i].sweepSpeed = 0.0f;
        turretInfo[i].sweepBrake = 0.0f;
        turretInfo[i].sweepResumeTime = 0;
        turretInfo[i].sweepFlags = 0;
        turretInfo[i].onTargetCos = 0.0f;
        turretInfo[i].flags &= ~(CODOL_TURRET_TARGET_ONAIM | CODOL_TURRET_FIRE_ENABLED |
                                 CODOL_TURRET_TARGET_INITED);
        CODOL_TurretHeat_Reset(&turretInfo[i]);
    }
}
#endif
