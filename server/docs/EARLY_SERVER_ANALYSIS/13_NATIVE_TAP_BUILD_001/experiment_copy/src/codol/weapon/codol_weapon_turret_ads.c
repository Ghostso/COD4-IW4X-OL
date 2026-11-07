/* CoDOL mounted-turret aim-down-sight (zoom) transition.  Native C1; no
 * retained IW3 behaviour survives here, because IW3/IW4 have none.
 *
 * Retained CoD4 PM_UpdateAimDownSightLerp (_bg_weapons.asm:5752) answers a
 * linked player with `test [ebx+0xb0], PLAYER_EFLAG_TURRET_MASK / jnz` into
 * the "fWeaponPosFrac = 0, adsDelayTime = 0" exit: a mounted MG simply has no
 * ADS in IW3 or IW4.  CoDOL added one, and C1 reaches it *before* every gate
 * that reads the weapon definition, which is what makes it work at all --
 * turret_minigun_mp ships with WeaponDef +0xbc8 (aimDownSight) == 0, measured
 * straight out of mp_overgrown's fastfile.
 *
 * C1 PM_UpdateAimDownSightLerp 0x004185a0 (MEASURED, C1.exe 1.1.1.13):
 *
 *   4185c2  test DWORD PTR [esi+0xec],0xc00   ; eFlags & PLAYER_EFLAG_TURRET_MASK
 *   4185cc  fild DWORD PTR [ecx+0x28]         ; (float)pml->msec, raw
 *   4185d9  je   418655                       ; not linked -> ordinary ADS
 *   4185dd  mov  ecx,ds:0x1509e94             ; dvar "210"
 *   4185e3  fcom DWORD PTR [ecx+0xc]          ; 0.0 vs value
 *   4185eb  jp   418642                       ; value <= 0 (or NaN) -> snap
 *   4185f1  fld  DWORD PTR [ecx+0xc]
 *   4185f4  fld1
 *   4185f6  fdivrp st(1),st                   ; rate = 1.0 / value
 *   4185fd  ... frac +/- rate * msec ...
 *   41861f  call 0x4010e0                     ; clamp(frac, 0.0, 1.0)
 *   4187f5  mov  DWORD PTR [esi+0x350],0      ; adsDelayTime = 0
 *
 * Note what the turret arm does NOT do: it never reads the weapon definition,
 * never touches the +0xa28/+0xa2c per-millisecond ADS rates the ordinary path
 * uses, and never applies the ability-10 elapsed-time modifier (C1 applies
 * that only at 0x0041875b, downstream of the `je 418655`).  So the transition
 * is uniform for every mountable turret and is tuning data, not weapon data.
 *
 * The two dvars, read out of C1's registration block at 0x0040c1f3..0x0040c258
 * (each `mov ds:X,eax` stores the *preceding* call's return value, so the name
 * pushed immediately before a `call` pairs with the store after the next
 * argument block):
 *
 *   "209"  Dvar_RegisterBool (0x624370), default 1,               flags 4,
 *          pointer 0x150c5ac, read only by BG_PlayerCanAds 0x00418183.
 *   "210"  Dvar_RegisterFloat(0x6244d0), default 250.0, [0,5000], flags 4,
 *          pointer 0x1509e94, read only by the arm above.
 *
 * C1 flags 4 is IW4's DVAR_CHEAT, so an unmodified client always runs the
 * defaults: a 250 ms zoom-in and a 250 ms zoom-out.  These are registered as
 * real server dvars with the same type, default and range rather than baked in
 * as constants, matching the precedent in codol_script_weapon_visual_queries.c.
 */
#ifdef CODOL_SERVER
#include "codol_weapon_turret_ads.h"
#include "q_shared.h"
#include "player.h"
#include "cvar.h"

/* C1 pm_flags PMF_ADS_BUTTON, tested at 0x004185ed and 0x00418642. */
#define CODOL_TURRET_PMF_ADS_BUTTON 0x10

int CODOL_TurretAdsAllowed(void)
{
    static cvar_t *gate;
    if(!gate) gate=Cvar_RegisterBool("bg_turretAdsEnabled",qtrue,CVAR_CHEAT,
        "Allow a player linked to a turret to aim down sight (C1 dvar 209).");
    return gate && gate->boolean;
}

float CODOL_TurretAdsTransitionMsec(void)
{
    static cvar_t *time;
    if(!time) time=Cvar_RegisterFloat("bg_turretAdsTime",250.0f,0.0f,5000.0f,
        CVAR_CHEAT,
        "Milliseconds a linked player takes to zoom a turret fully in or out; "
        "zero snaps (C1 dvar 210).");
    return time ? time->value : 250.0f;
}

int CODOL_TurretAdsLerp(playerState_t *ps,int msec)
{
    float duration,rate,frac;

    if(!ps || !(ps->eFlags&PLAYER_EFLAG_TURRET_MASK)) return 0;

    duration=CODOL_TurretAdsTransitionMsec();
    /* C1 0x004185e3 compares 0.0 against the dvar with `fcom`/`fnstsw`/
     * `test ah,5`/`jp`, which takes the snap arm for value <= 0 *and* for an
     * unordered compare.  `!(duration > 0)` reproduces both, NaN included. */
    if(!(duration>0.0f)) {
        ps->fWeaponPosFrac=(ps->pm_flags&CODOL_TURRET_PMF_ADS_BUTTON) ?
            1.0f : 0.0f;
        ps->adsDelayTime=0;
        return 1;
    }

    /* Same operation order as C1: one reciprocal, one multiply by the raw
     * millisecond count, one add or subtract against the stored fraction.
     * Recomputing this as msec/duration would diverge in the last bits from
     * the fraction the client predicts. */
    rate=1.0f/duration;
    frac=ps->fWeaponPosFrac;
    if(ps->pm_flags&CODOL_TURRET_PMF_ADS_BUTTON) frac=frac+rate*(float)msec;
    else frac=frac-rate*(float)msec;

    if(frac<0.0f) frac=0.0f;
    else if(frac>1.0f) frac=1.0f;
    ps->fWeaponPosFrac=frac;
    ps->adsDelayTime=0;
    return 1;
}
#endif
