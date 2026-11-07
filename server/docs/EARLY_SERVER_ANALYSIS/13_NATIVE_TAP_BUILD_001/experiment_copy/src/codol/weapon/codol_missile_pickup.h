#ifndef CODOL_MISSILE_PICKUP_H
#define CODOL_MISSILE_PICKUP_H
struct gentity_s;
struct playerState_s;
struct WeaponDef;
int CODOL_IsInventoryMissile(const struct gentity_s *);
int CODOL_InventoryMissileUseAllowed(const struct gentity_s *,const struct gentity_s *);
int CODOL_InventoryMissileCanBeGrabbed(const struct playerState_s *,unsigned);
/* -1 ordinary missile, 0 refused, 2 inventory recovery/cleanup completed. */
int CODOL_RecoverMissileAmmo(struct gentity_s *,const struct WeaponDef *,unsigned,unsigned,struct gentity_s *);
/* -2 unavailable hint, -1 knife/ordinary missile; otherwise interned hint. */
int CODOL_InventoryMissileHint(const struct gentity_s *);
#endif
