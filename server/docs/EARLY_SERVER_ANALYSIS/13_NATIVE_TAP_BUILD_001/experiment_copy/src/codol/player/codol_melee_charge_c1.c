/* C1 PM_MeleeChargeUpdate (0x415c40).
 *
 * The retained IW3 body computed the lunge from player_meleeChargeFriction
 * (speed = sqrt(2*dist*friction), meleeChargeTime = speed/friction*1000) and
 * then decremented meleeChargeTime by pml->msec itself. C1 does neither: the
 * lunge duration is the weapon definition melee delay, the launch speed is the
 * constant-deceleration speed that covers meleeChargeDist in exactly that
 * delay, and the countdown belongs to PM_MeleeChargeMove (0x415ec4) alone.
 *
 * Keeping the IW3 body meant the server lunged at a different speed than the
 * C1 client predicted and, because PM_MeleeChargeMove also decrements,
 * for half as long.  The player the server traces from at EV_FIRE_MELEE was
 * therefore short of the position the client had already moved to, and the
 * melee trace fell behind the target.
 */
#include "q_shared.h"
#include "cvar.h"
#include "player.h"
#include "bg_public.h"
#include "xassets/weapondef.h"
#include "qcommon.h"
#include <math.h>

/* C1 0x415c4e / 0x415edb: PMF_MELEE_CHARGE. */
#define C1_PMF_MELEE_CHARGE 0x00010000u
/* C1 0xc323a8: the default lunge distance above which the charge pair of
 * melee timings is used instead of the ordinary pair. */
#define C1_MELEE_CHARGE_DIST_THRESHOLD 64.0f
/* C1 0xc842f8. */
#define C1_DEG2RAD 0.01745329238474369f

static void melee_charge_clear(playerState_t *ps)
{
    ps->pm_flags &= ~C1_PMF_MELEE_CHARGE;
    ps->meleeChargeYaw = 0.0f;
    ps->meleeChargeDist = 0;
    ps->meleeChargeTime = 0;
}

void REGPARM(2) CODOL_PM_MeleeChargeUpdateC1(struct pmove_t *pm, struct pml_t *pml)
{
    playerState_t *ps;
    const struct WeaponDef *def;
    float seconds, speed, yaw;
    (void)pml;
    if(!pm || !(ps = pm->ps)) return;
    if(!(ps->pm_flags & C1_PMF_MELEE_CHARGE))
    {
        melee_charge_clear(ps);
        return;
    }
    /* C1 0x415c7c: once the trajectory is running only PM_MeleeChargeMove
     * touches it. */
    if(ps->meleeChargeTime) return;

    def = BG_GetWeaponDef((int)ps->weapon);
    if(!def)
    {
        melee_charge_clear(ps);
        return;
    }
    /* C1 0x415d10: the charge pair is selected by the lunge distance. */
    seconds = (float)((float)ps->meleeChargeDist > C1_MELEE_CHARGE_DIST_THRESHOLD
                          ? def->meleeChargeDelay
                          : def->iMeleeDelay) * 0.001f;
    if(seconds <= 0.0f)
    {
        melee_charge_clear(ps);
        return;
    }
    /* C1 0x415d64..0x415da9: constant deceleration covering meleeChargeDist
     * in `seconds`, launched along meleeChargeYaw. */
    speed = 2.0f * (float)ps->meleeChargeDist / seconds;
    yaw = ps->meleeChargeYaw * C1_DEG2RAD;
    ps->velocity[0] = speed * cosf(yaw);
    ps->velocity[1] = speed * sinf(yaw);
    /* C1 0x415daf..0x415dba. */
    ps->meleeChargeTime = (int)(seconds * 1000.0f);
    if(codol_meleeDebug && codol_meleeDebug->boolean)
        Com_Printf(CON_CHANNEL_SERVER,
            "CoDOL melee: lunge client %d dist %d yaw %.1f delay %d ms speed %.0f u/s chargeTime %d origin (%.1f %.1f %.1f)\n",
            ps->clientNum, ps->meleeChargeDist, ps->meleeChargeYaw,
            (int)(seconds * 1000.0f), speed, ps->meleeChargeTime,
            ps->origin[0], ps->origin[1], ps->origin[2]);
}
