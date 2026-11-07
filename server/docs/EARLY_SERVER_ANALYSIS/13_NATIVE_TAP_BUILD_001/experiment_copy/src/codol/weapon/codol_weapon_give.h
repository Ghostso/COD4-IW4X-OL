/* C ports of five retained IW3 weapon primitives; see codol_weapon_give.c and
 * docs/CODOL_WEAPON_TABLE_20260915.md ("Function ports"). The retained symbols
 * (G_GivePlayerWeapon, G_UseOffHand, PlayerCmd_dropItem, PlayerCmd_giveMaxAmmo,
 * PlayerCmd_giveStartAmmo) keep their assembly bodies until their callers are
 * retargeted to these; the two sets link side by side.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_WEAPON_GIVE_H
#define CODOL_WEAPON_GIVE_H
#include "q_shared.h"
#include "g_shared.h"
#include "scr_vm.h"

/* The layout Weapon_Throw_Grenade (_g_weapon.asm) reads; G_UseOffHand fills
 * forward/right/up/muzzleTrace (0x40 bytes on the retained stack frame). */
typedef struct {
    vec3_t forward, right, up, muzzleTrace, gunForward;   /* +0x00..+0x3b */
    struct WeaponDef *weapDef;                             /* +0x3c: what Weapon_Throw_Grenade reads (_g_weapon.asm:981) */
} codol_weaponParms_t;

/* G_GivePlayerWeapon(playerState_s*, int, unsigned char): 1 when the weapon
 * and its alternate chain were granted, 0 when already owned or the model
 * variant does not exist (weapClass 7/8 are exempt from the model check). */
int __cdecl CODOL_GivePlayerWeapon(playerState_t *ps, int weapon, unsigned char model);
/* G_UseOffHand(gentity_s*): throw the equipped offhand from the gun angles. */
void __cdecl CODOL_UseOffHand(gentity_t *ent);
/* Script methods: <player> dropItem(name[, tag]), giveMaxAmmo(name),
 * giveStartAmmo(name). */
void CODOL_PlayerCmd_dropItem(scr_entref_t ref);
void CODOL_PlayerCmd_giveMaxAmmo(scr_entref_t ref);
void CODOL_PlayerCmd_giveStartAmmo(scr_entref_t ref);
#endif
