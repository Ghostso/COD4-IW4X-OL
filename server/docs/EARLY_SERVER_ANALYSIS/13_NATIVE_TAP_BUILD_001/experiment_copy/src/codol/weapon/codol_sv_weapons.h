#ifndef CODOL_SV_WEAPONS_H
#define CODOL_SV_WEAPONS_H
#include "codol_weapon_registry.h"
#include "codol_engine_state.h"
/* Native weapon-definition capacity, and the one place it is written down.
 *
 * The ceiling is the retained playerState_t's per-weapon bitsets, not the
 * definition table used to be BG_IsWeaponValid's four-dword ps+0x55c bitset;
 * the bitsets now live in the playerState extension at C1's own width, where
 * bg_weaponDefs (0x0150D720) holds 700 and the CG_Init walk (0x00450ADC)
 * validates 1..699 - see docs/CODOL_WEAPON_TABLE_20260915.md.
 *
 * Every 128 in the weapon path must read CODOL_WEAPON_SLOTS, including
 * codol_bot_loadout.c's admission check: two copies of the number is how a
 * widening half-lands. */
#include "codol_weapon_slots.h"   /* CODOL_WEAPON_SLOTS */
/* Refresh from the exact override/inherited weapon names before gamestate.
 * A failed refresh invalidates the previously exposed registry. */
int CODOL_RefreshServerWeaponRegistry(void);
int CODOL_InitializeServerWeaponConfigstrings(const char *zone_type);
const codol_weapon_registry_t *CODOL_ServerWeaponRegistry(void);
void CODOL_ResetServerWeaponRegistry(void);
const char *CODOL_ServerWeaponRegistryError(void);
int CODOL_RefreshServerWeaponMappings(void);
/* Register a canonical composed definition in the retained native weapon table,
 * then publish its adjusted name/partners and rebuild engine/wire mappings.
 * Configstring and registry changes commit together; native registration is
 * monotonic like BG_GetWeaponIndexForName. The supplied base must match its
 * published index. 1 published/already present, 0 invalid, -1 failed. */
int CODOL_PublishComposedWeapon(const char *,const char *,unsigned *slot);
/* Resolve snapshot ammo slots from this frame's inventory and the actual
 * registered native definitions. Preserve unrelated bindings and all output
 * on failure. Publication/mapping refresh precedes the read-only resolution. */
int CODOL_BuildServerAmmoBindings(codol_engine_player_bindings_t *,const playerState_t *);
/* Called by BG_GetWeaponIndexForName before a loaded definition is appended.
 * 0 refuses it (warning printed) when the 700-slot table or a 128-entry
 * retained ammo/clip/shared-cap pool would overflow. */
struct WeaponDef;
int CODOL_AdmitWeaponPools(const struct WeaponDef *def);
/* Send newly committed weapon names to primed recipients, in registry order. */
void CODOL_BroadcastWeaponConfigstrings(unsigned first,unsigned count);
#endif
