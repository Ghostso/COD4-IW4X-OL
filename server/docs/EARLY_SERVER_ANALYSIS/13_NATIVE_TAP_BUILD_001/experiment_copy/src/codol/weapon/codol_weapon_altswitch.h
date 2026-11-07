/* CoDOL alternate-mode (underbarrel attachment) weapon switch selection.
 *
 * C1 decides an alternate switch with its own predicate (0x419670) that also
 * recognises the way back from an alternate-mode weapon to the primary that
 * owns it, and raises with the alternate animation exactly when the change
 * started as an alternate drop (0x41d80c passes the weaponstate, 0x419df6 tests
 * it for 5). The retained IW3 machine only follows WeaponDef.altWeaponIndex
 * forward; see codol_weapon_altswitch.c. */
#ifndef CODOL_WEAPON_ALTSWITCH_H
#define CODOL_WEAPON_ALTSWITCH_H

#include "q_shared.h"
#include "player.h"

/* 1 when changing from `previous` to `next` is an alternate-mode switch. */
int CODOL_WeaponIsAltSwitch(const playerState_t *ps, unsigned previous, unsigned next);
/* 1 when the drop that just completed was the alternate drop. */
int CODOL_WeaponChangeWasAlternate(const playerState_t *ps);

#endif
