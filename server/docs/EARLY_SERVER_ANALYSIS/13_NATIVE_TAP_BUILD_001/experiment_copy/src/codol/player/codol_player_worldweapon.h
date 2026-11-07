#ifndef CODOL_PLAYER_WORLDWEAPON_H
#define CODOL_PLAYER_WORLDWEAPON_H
#ifdef __cplusplus
extern "C" {
#endif
/* C1 native linked script_model world guns. Call after player appearance and
 * playerState->entityState producers, before snapshot capture. */
void CODOL_UpdatePlayerWorldWeapons(void);
/* Live lifecycle only. Archived entity states retain their captured selector. */
void CODOL_ResetPlayerWorldWeaponEntity(unsigned entity);
void CODOL_ResetPlayerWorldWeapons(void);
/* Re-arms the per-(cause,tag) entity-link warnings. A link that cannot be
 * published is otherwise invisible, and the previous global eight-message cap
 * was exhausted during boot by one repeating tag. */
void CODOL_ResetEntityLinkReports(void);
#ifdef __cplusplus
}
#endif
#endif
