/* C1 ability consumers in the retained weapon state machine.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * The retained IW3 PM_Weapon (src/asmsource/_bg_weapons.asm) still owns the
 * offhand, sprint and fire transitions. C1 applies four abilities at exactly
 * those transitions, so the asm calls these at the matching points. Every
 * C1 reader tests the MSB-first ability bit of ps+0x4d0 first, then reads
 * the value slot through 0x402f20 (CODOL_GetActiveAbilityValue).
 *
 *   modBulletSpreadScale (6)       BG_GetSpreadForWeapon 0x422736..0x42276d
 *   modADSSpeedScale (10)          adsFireOnly fire delay 0x41b4ea..0x41b52a
 *   modWeaponRecoveryTimeScale (11) sprint-out, state 25, 0x41d178..0x41d1af
 *   modOffhandSpeedScale (28)      offhand init 0x41c33d, prepare 0x41c4cd,
 *                                  throw 0x41c696/0x41c6cf, end 0x41c8f8
 */
#ifdef CODOL_SERVER
#include "codol_ability_math.h"
#include "codol_abilities.h"
#include "codol_assets.h"
#include "codol_playerstate_ext.h"
#include "q_shared.h"
#include "qcommon_io.h"
#include "player.h"
#include <limits.h>
#include <math.h>

#define C1_ABILITY_SPREAD           6u
#define C1_ABILITY_ADS              10u
#define C1_ABILITY_WEAPON_RECOVERY  11u
#define C1_ABILITY_OFFHAND          28u

/* 1 active with *value, 0 inactive, -1 active without a usable value. */
static int ability_value(const playerState_t *ps, unsigned id, float *value)
{
    const codol_ps_ext_t *ext=CODOL_PlayerStateExtConst(ps);
    const codol_engine_table_t *table;
    int status;
    if(!ext || !ext->abilities_known) return 0;
    if(!(ext->abilities.masks[id>>5]&(UINT32_C(0x80000000)>>(id&31)))) return 0;
    if(CODOL_LoadEngineStringTable("mp/coAbilityModifiersTable.csv",&table)!=1)
        return -1;
    status=CODOL_GetActiveAbilityValue(&ext->abilities,table,id,value);
    return status==1 ? 1 : -1;
}

static void report_once(unsigned id, const char *what)
{
    static unsigned char reported[128];
    if(id>=128 || reported[id]) return;
    reported[id]=1;
    Com_PrintWarning(CON_CHANNEL_SERVER,
        "CoDOL ability %u: %s; using unmodified value\n",id,what);
}

/* A time divided by the ability's value, or left alone when the ability is
 * off. A missing table row or a value C1 could not divide by is reported
 * once and leaves the time unmodified rather than publishing 0x80000000. */
static void divide_time(const playerState_t *ps, unsigned id, int *time)
{
    float value;
    int status=ability_value(ps,id,&value), result;
    if(!status) return;
    if(status<0) { report_once(id,"value unavailable"); return; }
    if(!CODOL_AbilityDivideMsec(*time,value,&result)) {
        report_once(id,"value out of range");
        return;
    }
    *time=result;
}

/* Offhand init, prepare/detonate and end: C1 divides weaponTime only. */
void __cdecl CODOL_WeaponOffhandPhaseTime(playerState_t *ps)
{
    if(ps) divide_time(ps,C1_ABILITY_OFFHAND,&ps->weaponTime);
}

/* Offhand throw (C1 state 19, 0x41c66d..0x41c6ec): weaponTime and
 * weaponDelay, each divided by its own lookup of the same value. */
void __cdecl CODOL_WeaponOffhandThrowTimes(playerState_t *ps)
{
    if(!ps) return;
    divide_time(ps,C1_ABILITY_OFFHAND,&ps->weaponTime);
    divide_time(ps,C1_ABILITY_OFFHAND,&ps->weaponDelay);
}

/* Offhand hold (C1 0x41c564..0x41c590): with ability 39 active the fuse the
 * hold just armed grows by the ability value, truncated to whole seconds
 * (0xae0410 is _ftol) and multiplied by 1000. */
#define C1_ABILITY_FUSE             39u
void __cdecl CODOL_WeaponOffhandFuseBonus(playerState_t *ps)
{
    float value;
    int status;
    double bonus;
    if(!ps) return;
    status=ability_value(ps,C1_ABILITY_FUSE,&value);
    if(!status) return;
    if(status<0 || !isfinite(value)) { report_once(C1_ABILITY_FUSE,"value unavailable"); return; }
    if(!(value>-2000000.0f && value<2000000.0f)) { report_once(C1_ABILITY_FUSE,"value out of range"); return; }
    bonus=(double)(int)value*1000.0;
    if(bonus>(double)INT_MAX-(double)ps->grenadeTimeLeft || bonus<(double)INT_MIN-(double)ps->grenadeTimeLeft) {
        report_once(C1_ABILITY_FUSE,"value out of range");
        return;
    }
    ps->grenadeTimeLeft+=(int)bonus;
}

/* Sprint-out (C1 state 25): weaponTime = sprintOutTime / value11. */
void __cdecl CODOL_WeaponSprintOutTime(playerState_t *ps)
{
    if(ps) divide_time(ps,C1_ABILITY_WEAPON_RECOVERY,&ps->weaponTime);
}

/* C1 0x422736..0x42276d: min and max spread are each rounded to float after
 * the multiply. This replaces the IW3 perk bit 2 / perk_weapSpreadMultiplier
 * branch, which C1 no longer has (the dvar string is absent from C1.exe). */
void __cdecl CODOL_ApplySpreadAbility(const playerState_t *ps, float *min_spread,
                                      float *max_spread)
{
    float value;
    int status;
    if(!ps || !min_spread || !max_spread) return;
    status=ability_value(ps,C1_ABILITY_SPREAD,&value);
    if(!status) return;
    if(status<0 || !isfinite(value)) { report_once(C1_ABILITY_SPREAD,"value unavailable"); return; }
    *min_spread=*min_spread*value;
    *max_spread=*max_spread*value;
}

/* adsFireOnly weapons: the hip-to-ADS fire delay, quickened by ability 10. */
int __cdecl CODOL_WeaponAdsFireOnlyDelay(const playerState_t *ps,
                                         float oo_pos_anim_length, float pos_frac)
{
    float value=1.0f;
    int status=ability_value(ps,C1_ABILITY_ADS,&value), delay;
    if(status<0 || (status && !(isfinite(value) && value>0.0f))) {
        report_once(C1_ABILITY_ADS,"value unavailable");
        status=0;
    }
    if(!CODOL_AdsFireOnlyDelay(oo_pos_anim_length,pos_frac,status,value,&delay))
        return 0;
    return delay;
}
#endif
