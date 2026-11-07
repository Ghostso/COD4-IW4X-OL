#ifndef CODOL_SCRIPT_WEAPON_VISUAL_QUERIES_H
#define CODOL_SCRIPT_WEAPON_VISUAL_QUERIES_H
#ifdef __cplusplus
extern "C" {
#endif
/* Weapon-definition queries that answer with visual identity rather than
 * gameplay numbers. Measured against IW4 first, then C1 1.1.1.13, which is
 * authoritative for the CoDOL data layout.
 *
 * Both queries take one weapon name and follow the reference resolver
 * behaviour exactly, including the two engines' different failure modes:
 * an unresolved weapon returns undefined from getweaponhidetags and raises
 * a script error from getweaponflashtagname. See the worker report for the
 * disassembly the contracts were taken from.
 *
 * weaponhasthermalscope (IW4 0x5f2aa0, WeaponDef+0x67b) is C1 0x542010,
 * definition +0xbe6. The evidence is the function table's order, which keeps
 * IW4's (isweaponcliponly, isweapondetonationtimed, weaponhasthermalscope,
 * then the vehicle-node functions) with C1's own four inserted after it, and
 * the weaponattach assets: only thermal_* assets override +0xbe6 (all to 1
 * but thermal_scope, which writes 0). The two bytes earlier notes could not attribute are
 * attachment flags as well: +0xbf4 is written only by gps_base (marketplace
 * items gps_default and sra_tracker) and +0xbf5 only by lock_base
 * (sra_idlock); C1 reads each from one script query (0x542140, 0x5421d0). */
void CODOL_Scr_GetWeaponHideTags(void);
void CODOL_Scr_GetWeaponFlashTagName(void);
/* getWeaponScriptMods( <weapon> ): C1 0x535c10. */
void CODOL_Scr_GetWeaponScriptMods(void);
/* weaponHasThermalScope( <weapon> ): C1 0x542010, definition +0xbe6.
 * codol_weaponHasGPS / codol_weaponHasIDLock / codol_weaponHasHPBT: C1
 * 0x542140 (+0xbf4), 0x5421d0 (+0xbf5), 0x5583d0 (+0xbf3), whose names C1
 * strips. See the .c file for the attachment evidence. */
void CODOL_Scr_WeaponHasThermalScope(void);
void CODOL_Scr_WeaponHasGPS(void);
void CODOL_Scr_WeaponHasIDLock(void);
void CODOL_Scr_WeaponHasHPBT(void);
#ifdef __cplusplus
}
#endif
#endif
