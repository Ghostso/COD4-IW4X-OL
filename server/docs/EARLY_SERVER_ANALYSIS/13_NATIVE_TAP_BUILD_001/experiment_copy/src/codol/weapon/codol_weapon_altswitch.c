/* CoDOL alternate-mode weapon switch selection for the retained pmove.
 *
 * Reference behavior (C1.exe 1.1.1.13):
 *
 *   BG_IsAltSwitch @0x419670 (eax = weapon being left, ecx = weapon selected,
 *   stack = playerState):
 *     if(!left || !selected) return 0;
 *     if(def(left)+0xb7c == selected) return 1;              altWeaponIndex
 *     if(def(left)+0x34c == 3 && ps+0x340 == selected) return 1;
 *   +0x34c is the inventory type (3 = alternate mode) and ps+0x340 the primary
 *   that owns the alternate-mode weapon in hand. The second arm is the way back
 *   from an underbarrel launcher: composed CoDOL alternate definitions carry no
 *   +0xb78 back link (gl_acr_mp etc. ship with an empty alternate name), so the
 *   forward link alone never recognises gl_* -> rifle.
 *
 *   PM_BeginWeaponChange @0x4196b0 calls it at 0x41986f (skipped under pm_flags
 *   0x4000). An alternate switch queues event 0x1b, starts animation 0x13 and
 *   weaponstate 5 (0x4198b5..0x4198e4) with the left weapon's +0x600 alternate
 *   drop time (0x419a39); otherwise event 0x1a, animation 0x0a/0x15/0x17 and
 *   state 3/4 (0x4198f8..0x4199ec) with the ordinary drop, which also runs the
 *   third-person drop anim-script event (0x419971).
 *
 *   PM_Weapon passes the finishing weaponstate to PM_FinishWeaponChange
 *   (0x41d80c -> 0x419bf0). The alternate raise (animation 0x14, weaponstate 2,
 *   the new weapon's +0xb80 time, no raise events) is chosen purely because
 *   that state is 5 (0x419df1..0x419e31), not by re-testing the weapons.
 *
 * The retained IW3 machine instead compared altWeaponIndex of the weapon left
 * at both sites (_bg_weapons.asm PM_BeginWeaponChange_60, PM_Weapon before
 * PM_Weapon_1130). Leaving gl_acr_mp for its rifle therefore took the ordinary
 * drop/raise: the player saw the weapon-switch animation, the third-person
 * drop/raise anim-script events fired, and the launcher's put-away never ran.
 * The retained machine keeps states 3/4 and marks the alternate drop with
 * animation 17, which the snapshot publishes as C1 state 5 / animation 0x13
 * (codol_engine_state.c CODOL_ResolveEngineWeaponState); testing that animation
 * at the raise is the retained equivalent of C1's state-5 test. */
#ifdef CODOL_SERVER
#include "codol_weapon_altswitch.h"
#include "codol_weapon_state.h"
#include "bg_public.h"
#include "bg.h"
#include "xassets/weapondef.h"

/* Retained alternate drop animation (PM_BeginWeaponChange: or eax, 0x11). */
#define CODOL_ALTSWITCH_ANIM_DROP_ALT 17u

static const struct WeaponDef *alt_weapon_def(unsigned weapon)
{
    int count;
    if(!weapon || weapon >= CODOL_WEAPON_STATE_WEAPONS) return NULL;
    count = BG_GetNumWeapons();
    if(count <= 0 || weapon >= (unsigned)count) return NULL;
    return BG_GetWeaponDef((int)weapon);
}

int CODOL_WeaponIsAltSwitch(const playerState_t *ps, unsigned previous, unsigned next)
{
    const struct WeaponDef *def;
    unsigned primary = 0;
    if(!ps || !previous || !next || !(def = alt_weapon_def(previous))) return 0;
    if(def->altWeaponIndex == next) return 1;                       /* 0x419682 */
    /* 0x419691..0x41969d: an alternate-mode weapon switches back to its owning
     * primary. ps+0x340 is the cached primary of the weapon in hand; the
     * change is always started from the weapon in hand, so only answer for it. */
    if(def->inventoryType != WEAPINVENTORY_ALTMODE || (unsigned)ps->weapon != previous)
        return 0;
    return CODOL_WeaponStatePrimaryWeapon(ps, &primary) && primary && primary == next;
}

int CODOL_WeaponChangeWasAlternate(const playerState_t *ps)
{
    if(!ps || (ps->weaponstate != 3 && ps->weaponstate != 4)) return 0;
    return (((unsigned)ps->weapAnim) & 0x1fu) == CODOL_ALTSWITCH_ANIM_DROP_ALT;
}
#endif
