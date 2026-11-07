/* Native weapon-definition budget: what the retained bg_weaponDefs table can
 * still take, and whether a name can be handed to a script without costing a
 * slot.
 *
 * Two producers compose weapons at spawn time - the bot CSV bridge
 * (codol_bot_loadout.c) and the human profile bridge
 * (codol_script_profile_loadout.c) - and both used to assume that "fall back to
 * the stock base weapon" is free. It is not. A stock name the native table does
 * not already hold still costs a definition slot, because giveWeapon resolves
 * it through BG_GetWeaponIndexForName, which calls G_RegisterWeapon and
 * appends. On a full table that appends past the engine->wire map, after which
 * the retained SaveRegisteredWeapons update (native configstring 0x8d2 = 2258)
 * can no longer rebuild the map - which used to ERR_DROP the whole match.
 *
 * The ceiling itself is CODOL_WEAPON_SLOTS and lives in codol_weapon_slots.h
 * (via codol_sv_weapons.h) so it has exactly one definition; nothing here
 * restates it. */
#ifndef CODOL_WEAPON_BUDGET_H
#define CODOL_WEAPON_BUDGET_H
#ifdef CODOL_SERVER
/* Room for one more composed definition and the retained alternate it may drag
 * in with it. 1 when composing is safe, 0 when the table is effectively full.
 * Call this *before* composing: append_weapon_set only refuses a publish after
 * BG_GetWeaponIndexForName has already appended the definition. */
int CODOL_NativeWeaponRoom(void);
/* 1 when this exact name already occupies a native definition slot *and* has a
 * wire index, so giving it registers nothing and the client can resolve it.
 * Uses the find-only BG_FindWeaponIndexForName; it never registers. */
int CODOL_WeaponAlreadyLive(const char *name);
/* The name a producer may safely answer with when its real choice failed:
 * `name` itself when there is room for it or it is already live, otherwise the
 * scripts' "none". Never returns NULL. An unarmed player is degraded; a
 * dropped server is a dead match. */
const char *CODOL_SafeStockWeapon(const char *name);
#endif
#endif
