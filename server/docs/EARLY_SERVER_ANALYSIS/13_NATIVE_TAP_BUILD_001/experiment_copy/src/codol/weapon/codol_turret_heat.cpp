#ifdef CODOL_SERVER
/* Turret overheat, barrel spin and turret mode.
 *
 * Every semantic here is measured in C1 (Call of Duty Online 1.1.1.13,
 * C1.exe, base 0x400000) rather than carried over from IW4: CoDOL's turret
 * model is IW4-lineage but has its own offsets, so only C1 addresses are
 * quoted. IW4 (iw4x.exe) agrees function for function and was used to
 * cross-check.
 *
 * C1 turret struct (0xfc bytes, pool base 0x24ee230, 32 slots, allocated and
 * memset in G_SpawnTurret 0x57e8c0):
 *   +0x04 flags        +0x40 fireState     +0x6c modeChangeTime
 *   +0x70 range^2      +0x7c pitch conv    +0x80 yaw conv (ms)
 *   +0xac heat         +0xb0 overheatEnd   +0xb4 barrelSpin
 *   +0xb8 spinLinger   +0xbc spinRequest
 * Spawn defaults 0x57f28f..0x57f2a7: barrelSpin = 0, overheatEnd = 0,
 * heat = 0, spinRequest = 0, spinLinger = 1000 ms; flags = 0x804 (0x57f139).
 *
 * C1 barrel spin update, 0x57b0f0 (eax = turret entity, edx = user entity):
 *     if (!weapDef->turretBarrelSpinEnabled[+0xbe8]) return;          ; 0x57b105
 *     prev = ent->s.lerp.u.turret.spinning (entityState +0x74);
 *     if (user->client[+0x17c])                                       ; 0x57b12a
 *         spinning = !(client->ps.pm_flags[+0x0c] & 0x800) &&
 *                     (client->buttons[+0x36f0] & 0x801);
 *     else if (turret->fireState[+0x40])       { spinning = 1; stamp; }
 *     else if (turret->flags & 0x100010)       { spinning = 1; stamp; } ; 0x57b160
 *     else if (turret->spinRequest[+0xbc] > 0 &&
 *              turret->spinLinger[+0xb8] + spinRequest >= level.time)
 *                                              { spinning = 1; }
 *     if (spinning != prev) { lerp->lastBarrelRotChangeTime = level.time;
 *                             lerp->lastBarrelRotChangeRate =
 *                                 (uint16)(turret->barrelSpin * 65535); }
 *     turret->barrelSpin = BG_GetTurretBarrelSpin(weapDef, lerp, level.time);
 *
 * C1 overheat update, 0x57b1f0 (ecx = turret entity):
 *     if (!(0 < weapDef->turretOverheatUpRate[+0xab8]))   return;     ; 0x57b207
 *     if (!(0 < weapDef->turretOverheatDownRate[+0xabc])) return;     ; 0x57b218
 *     heating = (ent->s.lerp.eFlags & 0x200, the fired-this-frame bit)  ; 0x57b229
 *               && (!turretBarrelSpinEnabled || barrelSpin >= 1.0f)     ; 0x57b249
 *               && (turret->overheatEnd <= level.time);                 ; 0x57b258
 *     if (heating != prev) { lerp->lastHeatChangeTime = level.time;
 *                            lerp->lastHeatChangeLevel =
 *                                (uint16)(turret->heat * 65535); }
 *     turret->heat = BG_GetTurretHeat(weapDef, lerp, level.time);
 *     if (turret->heat >= 1.0f)                                        ; 0x57b2c5
 *         turret->overheatEnd = level.time -
 *             (int)(weapDef->turretOverheatPenalty[+0xac0] * -1000);
 *     lerp->overheated = (turret->overheatEnd >= level.time);           ; 0x57b2ef
 *
 * C1 BG_GetTurretBarrelSpin 0x41dd80 and BG_GetTurretHeat 0x41de50
 * (ecx = lerp turret block, eax = time, esi = weapDef):
 *     value = lerp->lastChangeLevel * (1/65535)          ; 0xc844f0
 *     if (time <= lerp->lastChangeTime) return value;
 *     dt = (time - lerp->lastChangeTime) * 0.001         ; 0xc84410
 *     heat: value += heating ? upRate*dt : -downRate*dt, clamp [0,1]
 *     spin: spinning ? (upTime   <= 0 ? 1 : min(value + dt/upTime,   1))
 *                    : (downTime <= 0 ? 0 : max(value - dt/downTime, 0))
 *     weapDef +0xad4 = turretBarrelSpinUpTime, +0xad8 = ...DownTime.
 *
 * C1 fire gate, inside the shot producer 0x57b050 (edx = turret entity):
 *     if (turret->flags & 2)                       return;            ; 0x57b056
 *     if (level.time < turret->overheatEnd)        return;            ; 0x57b065
 *     if (weapDef->turretBarrelSpinEnabled &&
 *         !(1.0f < turret->barrelSpin))            return;            ; 0x57b085
 *     turret->fireSndDelay[+0x2c] = 3 * weapDef[+0xb68];
 * Both the manned fire update and the script shot reach the shot only
 * through 0x57b050, so the gate covers both.
 *
 * C1 turret mode, setmode 0x54e0d0 through 0x57e5b0 and getmode 0x54e330:
 *     flags = (flags & ~0x0c0c) | bits;  turret->modeChangeTime = level.time;
 *     "manual" 0, "manual_ai" 0x800, "auto_nonai" 0x4, "auto_ai" 0x804,
 *     "sentry" 0xc, "sentry_offline" 0x408;
 *     getmode returns "sentry" when (flags & 0xc), otherwise "manual".
 *
 * The six curve parameters are weapon-definition values in C1 and are read
 * from this fork's WeaponDef by name. C1's weapon asset carries them at asset
 * offsets 0xab8/0xabc/0xac0 (overheat), 0xad4/0xad8 (spin times) and the byte
 * 0xbe8 (spin enabled), inside the 0xbfc-byte asset the CoDOL weapon loader
 * already validates; mapping them into struct WeaponDef is the parent patch
 * that accompanies this pass. */

#include "codol_script_turret_target.h"
#include "g_shared.h"
#include "g_public_mp.h"
#include "bg_public.h"
#include "xassets/weapondef.h"

#include <string.h>
#include <stddef.h>
static_assert(sizeof(LerpEntityStateTurret)==28, "turret words fit the native union");
static_assert(offsetof(entityState_t,time2)==0x70, "turret bytes preserve native time2 offset");
static_assert(sizeof(entityState_t)==0xf4, "turret state preserves native entity stride");

/* C1 0xc844f0 / 0xc842d8: the heat level and barrel rotation rate are 0..1
 * fractions quantised to 16 bits for the network. */
#define CODOL_TURRET_QUANT 65535.0f
/* C1 0xc84410: milliseconds to seconds. */
#define CODOL_TURRET_MSEC_TO_SEC 0.001f
/* C1 0x57b133 tests buttons & 0x801 - the fire bit plus the ADS bit of the
 * same usercmd button word this fork calls KEY_MASK_ADS_MODE. The retained
 * turret_think_client uses the fire bit alone to decide to shoot. */
#define CODOL_TURRET_SPIN_BUTTONS (KEY_MASK_FIRE | KEY_MASK_ADS_MODE)
/* C1 0x57b12a tests ps.pm_flags & 0x800, the same bit the retained
 * turret_think_client tests (byte [client+0xd] & 8) before it fires. */
#define CODOL_TURRET_PMF_NO_FIRE 0x800

/* Weapon-definition curve parameters. C1 reads all six from the weapon
 * definition; this fork reads the same values by name once the CoDOL weapon
 * loader publishes them. Nothing else configures them: a turret whose weapon
 * carries no overheat rates simply never heats, which is exactly what C1 does
 * for such a weapon. */
struct codol_turretHeatParams_t
{
    float overheatUpRate;
    float overheatDownRate;
    float overheatPenalty;
    float barrelSpinUpTime;
    float barrelSpinDownTime;
    int barrelSpinEnabled;
};

static qboolean TurretHeat_Params(gentity_s *entity, codol_turretHeatParams_t *out)
{
    struct WeaponDef *weapDef;

    out->overheatUpRate = 0.0f;
    out->overheatDownRate = 0.0f;
    out->overheatPenalty = 0.0f;
    out->barrelSpinUpTime = 0.0f;
    out->barrelSpinDownTime = 0.0f;
    out->barrelSpinEnabled = 0;

    if (entity->s.weapon <= 0 || entity->s.weapon >= BG_GetNumWeapons())
    {
        return qfalse;
    }
    weapDef = BG_GetWeaponDef(entity->s.weapon);
    if (!weapDef)
    {
        return qfalse;
    }
#ifdef CODOL_WEAPONDEF_TURRET_HEAT
    out->overheatUpRate = weapDef->turretOverheatUpRate;
    out->overheatDownRate = weapDef->turretOverheatDownRate;
    out->overheatPenalty = weapDef->turretOverheatPenalty;
    out->barrelSpinUpTime = weapDef->turretBarrelSpinUpTime;
    out->barrelSpinDownTime = weapDef->turretBarrelSpinDownTime;
    out->barrelSpinEnabled = weapDef->turretBarrelSpinEnabled ? 1 : 0;
#endif
    return qtrue;
}

static int TurretHeat_Quantise(float fraction)
{
    int value;

    if (fraction <= 0.0f)
    {
        return 0;
    }
    if (fraction >= 1.0f)
    {
        return (int)CODOL_TURRET_QUANT;
    }
    value = (int)(fraction * CODOL_TURRET_QUANT + 0.5f);
    if (value > (int)CODOL_TURRET_QUANT)
    {
        value = (int)CODOL_TURRET_QUANT;
    }
    return value;
}

/* C1 captures its interpolation base by writing the 16-bit network word and
 * reading it back, so the base is rounded the same way here; otherwise the
 * two sides would drift apart once the transport exists. */
static float TurretHeat_Requantise(float fraction)
{
    return (float)TurretHeat_Quantise(fraction) / CODOL_TURRET_QUANT;
}

/* C1 BG_GetTurretHeat 0x41de50. */
static float TurretHeat_Advance(const codol_turretHeatParams_t *params, float heat,
                                int elapsedMsec, qboolean heating)
{
    float seconds;

    if (elapsedMsec <= 0)
    {
        return heat;
    }
    seconds = (float)elapsedMsec * CODOL_TURRET_MSEC_TO_SEC;
    if (heating)
    {
        heat += params->overheatUpRate * seconds;
        return (heat >= 1.0f) ? 1.0f : heat;
    }
    heat -= params->overheatDownRate * seconds;
    return (heat < 0.0f) ? 0.0f : heat;
}

/* C1 BG_GetTurretBarrelSpin 0x41dd80. A non-positive time means the barrel
 * reaches the end state immediately, which is the reference's early return. */
static float TurretHeat_AdvanceSpin(const codol_turretHeatParams_t *params, float spin,
                                    int elapsedMsec, qboolean spinning)
{
    float seconds;

    if (elapsedMsec <= 0)
    {
        return spin;
    }
    seconds = (float)elapsedMsec * CODOL_TURRET_MSEC_TO_SEC;
    if (spinning)
    {
        if (!(params->barrelSpinUpTime > 0.0f))
        {
            return 1.0f;
        }
        spin += seconds / params->barrelSpinUpTime;
        return (spin >= 1.0f) ? 1.0f : spin;
    }
    if (!(params->barrelSpinDownTime > 0.0f))
    {
        return 0.0f;
    }
    spin -= seconds / params->barrelSpinDownTime;
    return (spin < 0.0f) ? 0.0f : spin;
}

/* Client presentation. C1 publishes the turret heat and barrel spin through
 * its entityState, and both of its own consumers (BG_GetTurretBarrelSpin
 * 0x41dd80 and BG_GetTurretHeat 0x41de50) recompute the current value from
 * exactly these words, which is why the interpolation base and the change
 * stamp are captured here the same way C1 captures them:
 *
 *   entityState +0x64  lastBarrelRotChangeTime   netfield bits -97  (C1 0xc368b8)
 *   entityState +0x68  lastBarrelRotChangeRate   netfield bits  16  (C1 0xc368c4)
 *   entityState +0x6c  lastHeatChangeLevel       netfield bits  16  (C1 0xc368dc)
 *   entityState +0x70  lastHeatChangeTime        netfield bits -97  (C1 0xc368d0)
 *   entityState +0x74  the three direction bytes netfield bits  32  (C1 0xc368ac)
 *                      +0x74 spinning, +0x75 overheated, +0x76 heating
 *
 * The fields are written into the entity state itself, so the snapshot
 * archive carries them and no historical value is ever read back out of the
 * live gentity. LerpEntityStateTurret has to declare them first, which is the
 * shared change in turret-behavior-parent.patch; until it lands the macro is
 * undefined and nothing is written. */
static void TurretHeat_PublishSpin(gentity_s *entity, turretInfo_s *turret, qboolean spinning)
{
#ifdef CODOL_ENTITYSTATE_TURRET_STATE
    struct LerpEntityStateTurret *lerp = &entity->s.lerp.u.turret;

    lerp->lastBarrelRotChangeTime = turret->spinChangeTime;
    lerp->lastBarrelRotChangeRate = TurretHeat_Quantise(turret->spinBase);
    entity->s.turretState.barrelSpinning = spinning ? 1 : 0;
#else
    (void)entity;
    (void)turret;
    (void)spinning;
#endif
}

static void TurretHeat_PublishHeat(gentity_s *entity, turretInfo_s *turret, qboolean heating)
{
#ifdef CODOL_ENTITYSTATE_TURRET_STATE
    struct LerpEntityStateTurret *lerp = &entity->s.lerp.u.turret;

    lerp->lastHeatChangeTime = turret->heatChangeTime;
    lerp->lastHeatChangeLevel = TurretHeat_Quantise(turret->heatBase);
    entity->s.turretState.heating = heating ? 1 : 0;
    entity->s.turretState.overheated = (turret->flags & CODOL_TURRET_OVERHEATED) ? 1 : 0;
#else
    (void)entity;
    (void)turret;
    (void)heating;
#endif
}

/* C1 0x57b0f0. user is the entity on the turret, or NULL when unmanned. */
static void TurretHeat_UpdateSpin(gentity_s *entity, turretInfo_s *turret,
                                  const codol_turretHeatParams_t *params, gentity_s *user)
{
    qboolean spinning = qfalse;
    qboolean wasSpinning = (turret->flags & CODOL_TURRET_BARREL_SPINNING) ? qtrue : qfalse;

    if (!params->barrelSpinEnabled)
    {
        return;
    }

    if (user && user != entity && user->client)
    {
        if (!(user->client->ps.pm_flags & CODOL_TURRET_PMF_NO_FIRE) &&
            (user->client->buttons & CODOL_TURRET_SPIN_BUTTONS))
        {
            spinning = qtrue;
        }
    }
    else if (turret->fireState != CODOL_TURRET_FIRESTATE_NONE ||
             (turret->flags & (CODOL_TURRET_FIRE_ENABLED | CODOL_TURRET_SPIN_REQUESTED)))
    {
        spinning = qtrue;
        turret->spinRequestTime = level.time;
    }
    else if (turret->spinRequestTime > 0 &&
             turret->spinLingerTime + turret->spinRequestTime >= level.time)
    {
        spinning = qtrue;
    }

    if (spinning != wasSpinning)
    {
        turret->spinBase = TurretHeat_Requantise(turret->barrelSpinFrac);
        turret->spinChangeTime = level.time;
        if (spinning)
        {
            turret->flags |= CODOL_TURRET_BARREL_SPINNING;
        }
        else
        {
            turret->flags &= ~CODOL_TURRET_BARREL_SPINNING;
        }
    }
    turret->barrelSpinFrac = TurretHeat_AdvanceSpin(params, turret->spinBase,
                                                    level.time - turret->spinChangeTime,
                                                    spinning);
    TurretHeat_PublishSpin(entity, turret, spinning);
}

/* C1 0x57b1f0. */
static void TurretHeat_UpdateHeat(gentity_s *entity, turretInfo_s *turret,
                                  const codol_turretHeatParams_t *params)
{
    qboolean heating = qfalse;
    qboolean wasHeating = (turret->flags & CODOL_TURRET_HEATING) ? qtrue : qfalse;
    qboolean fired;

    fired = ((entity->s.lerp.eFlags & 0x40) ||
             (turret->flags & CODOL_TURRET_FIRED)) ? qtrue : qfalse;
    turret->flags &= ~CODOL_TURRET_FIRED;

    if (!(params->overheatUpRate > 0.0f) || !(params->overheatDownRate > 0.0f))
    {
        return;
    }

    if (fired &&
        (!params->barrelSpinEnabled || turret->barrelSpinFrac >= 1.0f) &&
        turret->overheatEndTime <= level.time)
    {
        heating = qtrue;
    }

    if (heating != wasHeating)
    {
        turret->heatBase = TurretHeat_Requantise(turret->heat);
        turret->heatChangeTime = level.time;
        if (heating)
        {
            turret->flags |= CODOL_TURRET_HEATING;
        }
        else
        {
            turret->flags &= ~CODOL_TURRET_HEATING;
        }
    }

    turret->heat = TurretHeat_Advance(params, turret->heatBase,
                                      level.time - turret->heatChangeTime, heating);

    if (turret->heat >= 1.0f)
    {
        turret->overheatEndTime = level.time + (int)(params->overheatPenalty * 1000.0f);
    }
    if (turret->overheatEndTime >= level.time)
    {
        turret->flags |= CODOL_TURRET_OVERHEATED;
    }
    else
    {
        turret->flags &= ~CODOL_TURRET_OVERHEATED;
    }
    TurretHeat_PublishHeat(entity, turret, heating);
}

extern "C"
{

/* Both turret paths run the spin update and then the heat update, as C1's
 * turret think does at 0x57dc87 / 0x57dc8e. */
void CODOL_TurretHeat_Update(gentity_s *entity, gentity_s *user)
{
    turretInfo_s *turret;
    codol_turretHeatParams_t params;

    if (!entity || !entity->pTurretInfo)
    {
        return;
    }
    turret = entity->pTurretInfo;
    if (!TurretHeat_Params(entity, &params))
    {
        return;
    }
    TurretHeat_UpdateSpin(entity, turret, &params, user);
    TurretHeat_UpdateHeat(entity, turret, &params);
}

/* Retained turret_think_client entry. That function derives the user pointer
 * from the turret's user handle without checking it, so the handle is
 * re-checked here before the client is read. */
void CODOL_TurretHeat_ThinkClient(gentity_s *entity, gentity_s *user)
{
    unsigned int number;

    if (!entity)
    {
        return;
    }
    number = entity->r.ownerNum.number;
    if (number == 0 || number > MAX_GENTITIES)
    {
        user = NULL;
    }
    CODOL_TurretHeat_Update(entity, user);
}

/* C1 0x57b050's gate. C1's turret flag 0x2 is a retained stance bit in this
 * fork's turretInfo_s, so the CoDOL fire-disable flag stands in for it; the
 * overheat and barrel-spin terms are C1's own. */
qboolean CODOL_TurretHeat_CanFire(gentity_s *entity)
{
    turretInfo_s *turret;
    codol_turretHeatParams_t params;

    if (!entity || !entity->pTurretInfo)
    {
        return qfalse;
    }
    turret = entity->pTurretInfo;
    if (turret->flags & CODOL_TURRET_FIRE_DISABLED)
    {
        return qfalse;
    }
    if (level.time < turret->overheatEndTime)
    {
        return qfalse;
    }
    if (TurretHeat_Params(entity, &params) && params.barrelSpinEnabled &&
        turret->barrelSpinFrac < 1.0f)
    {
        return qfalse;
    }
    return qtrue;
}

/* Called by the shot producer. C1's heat update reads its own eFlags 0x200;
 * this fork's turret_think clears the equivalent eFlags 0x40 before the CoDOL
 * think runs, so a script shot is latched on the turret as well. */
void CODOL_TurretHeat_NoteShot(gentity_s *entity)
{
    if (entity && entity->pTurretInfo)
    {
        entity->pTurretInfo->flags |= CODOL_TURRET_FIRED;
    }
}

/* C1 G_SpawnTurret 0x57f28f..0x57f2a7 and 0x57f139: the heat and spin state
 * start at zero, the spin linger default is 1000 ms, and the turret spawns in
 * "auto_ai" mode (C1 turret flags 0x804). Applied once per pool slot; the
 * allocation memset already produces the zeros. */
void CODOL_TurretHeat_Defaults(turretInfo_s *turret)
{
    if (!turret)
    {
        return;
    }
    turret->spinLingerTime = 1000;
    turret->flags = (turret->flags & ~CODOL_TURRET_MODE_MASK) |
                    CODOL_TURRET_MODE_AUTO | CODOL_TURRET_MODE_AI;
    turret->modeChangeTime = level.time;
}

/* C1 setmode 0x54e0d0 -> 0x57e5b0: replace the four mode bits and stamp the
 * change time. Returns qfalse for an unknown mode name, which is C1's
 * Scr_Error path at 0x54e318. */
qboolean CODOL_TurretHeat_SetMode(gentity_s *entity, const char *mode)
{
    turretInfo_s *turret;
    int bits;

    if (!entity || !entity->pTurretInfo || !mode)
    {
        return qfalse;
    }
    if (!strcmp(mode, "manual"))
    {
        bits = 0;
    }
    else if (!strcmp(mode, "manual_ai"))
    {
        bits = CODOL_TURRET_MODE_AI;
    }
    else if (!strcmp(mode, "auto_nonai"))
    {
        bits = CODOL_TURRET_MODE_AUTO;
    }
    else if (!strcmp(mode, "auto_ai"))
    {
        bits = CODOL_TURRET_MODE_AUTO | CODOL_TURRET_MODE_AI;
    }
    else if (!strcmp(mode, "sentry"))
    {
        bits = CODOL_TURRET_MODE_AUTO | CODOL_TURRET_MODE_SENTRY;
    }
    else if (!strcmp(mode, "sentry_offline"))
    {
        bits = CODOL_TURRET_MODE_SENTRY | CODOL_TURRET_MODE_OFFLINE;
    }
    else
    {
        return qfalse;
    }
    turret = entity->pTurretInfo;
    turret->flags = (turret->flags & ~CODOL_TURRET_MODE_MASK) | bits;
    turret->modeChangeTime = level.time;
    return qtrue;
}

/* C1 getmode 0x54e330: "sentry" while either mode bit is set, otherwise
 * "manual". C1 keeps a third branch returning "auto_nonai" that its own bit
 * test can never reach; it is left out rather than reproduced as dead code. */
const char *CODOL_TurretHeat_GetMode(gentity_s *entity)
{
    if (!entity || !entity->pTurretInfo)
    {
        return NULL;
    }
    if (entity->pTurretInfo->flags & (CODOL_TURRET_MODE_AUTO | CODOL_TURRET_MODE_SENTRY))
    {
        return "sentry";
    }
    return "manual";
}

/* Slot reset for G_FreeTurret and G_InitTurrets; the allocation memset
 * already clears a freshly taken slot. */
void CODOL_TurretHeat_Reset(turretInfo_s *turret)
{
    if (!turret)
    {
        return;
    }
    turret->heat = 0.0f;
    turret->heatBase = 0.0f;
    turret->heatChangeTime = 0;
    turret->overheatEndTime = 0;
    turret->barrelSpinFrac = 0.0f;
    turret->spinBase = 0.0f;
    turret->spinChangeTime = 0;
    turret->spinRequestTime = 0;
    turret->spinLingerTime = 1000;
    turret->modeChangeTime = 0;
    turret->flags &= ~(CODOL_TURRET_HEATING | CODOL_TURRET_OVERHEATED |
                       CODOL_TURRET_BARREL_SPINNING | CODOL_TURRET_FIRED |
                       CODOL_TURRET_SPIN_REQUESTED | CODOL_TURRET_MODE_MASK);
}

}
#endif
