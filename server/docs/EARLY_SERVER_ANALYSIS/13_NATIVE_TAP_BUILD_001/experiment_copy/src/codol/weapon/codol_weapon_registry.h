#ifndef CODOL_WEAPON_REGISTRY_H
#define CODOL_WEAPON_REGISTRY_H
/* Replay client registration order; this registry owns names, never engine
 * pointers or serialized runtime indices. Include implicit none/default first. */
typedef struct codol_weapon_registry_s codol_weapon_registry_t;
codol_weapon_registry_t *CODOL_CreateWeaponRegistry(void);
void CODOL_DestroyWeaponRegistry(codol_weapon_registry_t *);
/* wire must be the next sequential slot. base=-1 for stock, an earlier slot
 * for a '*' custom definition. Flags are serialized booleans. Failure leaves
 * the entire registry unchanged. Ammo/clip names are compared verbatim (an
 * empty zone string stays empty, as on the client). */
int CODOL_RegisterWeaponKeys(codol_weapon_registry_t *,unsigned wire,const char *name,
    const char *ammo,const char *clip,unsigned deduplicate,unsigned no_clip,int base);
int CODOL_GetWeaponKeys(const codol_weapon_registry_t *,unsigned wire,int *ammo,int *clip);
int CODOL_FindRegisteredWeapon(const codol_weapon_registry_t *,const char *name);
/* Borrowed until registry destruction; output unchanged for an absent slot. */
int CODOL_RegisteredWeaponName(const codol_weapon_registry_t *,unsigned,const char **);
/* The strings and flags the keys were derived from, for the server trace. */
int CODOL_RegisteredWeaponKeyNames(const codol_weapon_registry_t *,unsigned,const char **ammo,const char **clip,
    unsigned *deduplicate,unsigned *no_clip);
#endif
