#ifndef CODOL_WEAPON_RELOAD_H
#define CODOL_WEAPON_RELOAD_H
#include "player.h"
#include "xassets/weapondef.h"
/* C1 inventory byte2 and dual-mag reload producers; direct native callers. */
void CODOL_WeaponReloadSelected(playerState_t *,unsigned weapon);
void CODOL_WeaponReloadRemoved(playerState_t *,unsigned weapon);
void CODOL_WeaponReloadClipFinished(playerState_t *);
int CODOL_WeaponReloadInfo(const playerState_t *,const struct WeaponDef *,int empty,
    int *duration,int *add_time,int *fast);
int CODOL_FastMagSetReloadingState(playerState_t *);
int CODOL_FastMagReloadDelayedAction(playerState_t *);
int CODOL_FastMagReloadClip(playerState_t *);
#endif
