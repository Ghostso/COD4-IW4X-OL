/* Native dropped-weapon magazines. SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_ITEM_AMMO_H
#define CODOL_ITEM_AMMO_H

/* Translates a native weapon index into the published C1 index for the two
 * retained reliable-command producers (G_SelectWeaponIndex and
 * G_SetEquippedOffHand in src/asmsource/_g_weapon.asm). A weapon with no
 * published index reports itself once and selects none; it is not a reason to
 * end the match, which is what this used to do. */
int CODOL_RequireWeaponWireIndex(unsigned native);
/* Re-arms those per-index warnings. A new zone renumbers weapons, so a stale
 * flag would silence a genuinely new unpublished weapon. */
void CODOL_ResetWeaponWireIndexReports(void);

#endif
