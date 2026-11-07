#ifndef CODOL_KILLSTREAK_HUD_H
#define CODOL_KILLSTREAK_HUD_H
#include "player.h"
#include "scr_vm.h"
#include "codol_playerstate.h"
#include <stdint.h>
#pragma pack(push, 8)
typedef struct {
    uint16_t count;
    uint8_t id[5];
    uint8_t target[5];
} codol_killstreak_hud_t;
#pragma pack(pop)
#ifdef __cplusplus
extern "C" {
#endif
void CODOL_Scr_SetKillstreak(scr_entref_t ref);
void CODOL_Scr_GetKillstreak(scr_entref_t ref);
void CODOL_Scr_SetKillstreakID(scr_entref_t ref);
void CODOL_Scr_GetKillstreakID(scr_entref_t ref);
void CODOL_Scr_SetKillstreakTarget(scr_entref_t ref);
void CODOL_Scr_GetKillstreakTarget(scr_entref_t ref);
void CODOL_ResetClientKillstreakHud(unsigned client);
int CODOL_OverlayKillstreakHud(codol_player_fields_t *wire,const playerState_t *ps);
#ifdef __cplusplus
}
#endif
#endif
