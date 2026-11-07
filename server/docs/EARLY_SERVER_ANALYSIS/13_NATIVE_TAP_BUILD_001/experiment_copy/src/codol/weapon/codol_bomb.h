#ifndef CODOL_BOMB_H
#define CODOL_BOMB_H
#include "scr_vm.h"
#include "entity.h"
#include "cm_public.h"
struct WeaponDef;
typedef struct {
    unsigned type, guidance;
    float lifetime, acceleration, curvature, destabilization;
    int destabilization_distance;
} codol_bomb_weapon_t;
void CODOL_Scr_LaunchMortarBomb(scr_entref_t ref);
void CODOL_Scr_GetProjectileGravity(void);
/* Partial native LaunchBomb: verified type4/guidance4 constructor only. */
void CODOL_Scr_LaunchBomb(scr_entref_t ref);
gentity_t *CODOL_SpawnMortarBomb(gentity_t *,unsigned,const float [3],const float [3]);
/* Called for actual missile/world collision; returns1 when bomb consumed. */
int CODOL_BombImpact(gentity_t *ent,const trace_t *trace,const float *position);
int CODOL_BombNotifyImpact(gentity_t *ent);
/* Constructor-owned ballistic bombs bypass retained guided-rocket integration. */
int CODOL_BombUsesBallisticTrajectory(gentity_t *ent);
void CODOL_ResetBombState(unsigned entity);
void CODOL_ResetBombStates(void);
int CODOL_GetNativeBombWeapon(const struct WeaponDef *,codol_bomb_weapon_t *);
#endif
