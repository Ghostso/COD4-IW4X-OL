#ifndef CODOL_KNIFE_PICKUP_H
#define CODOL_KNIFE_PICKUP_H
struct gentity_s;
struct WeaponDef;
struct playerState_s;
/* -1: ordinary missile, 0: knife refused, 1: one knife recovered. */
int CODOL_RecoverKnifeAmmo(struct gentity_s *,const struct WeaponDef *,unsigned,unsigned);
int CODOL_IsKnifeDefinition(const struct WeaponDef *);
int CODOL_IsKnifeEntity(const struct gentity_s *);
/* -1: ordinary weapon, otherwise real owned/compatible ammo capacity. */
int CODOL_KnifeCanBeGrabbed(const struct playerState_s *,unsigned);
#endif
