#ifndef CODOL_ACTION_SLOTS_H
#define CODOL_ACTION_SLOTS_H
#include "player.h"
#include "scr_vm.h"
#include "codol_playerstate.h"
#include <stdint.h>
#define CODOL_ACTION_SLOT_COUNT 5
#pragma pack(push, 8)
typedef struct {
    uint16_t weapon[CODOL_ACTION_SLOT_COUNT];
    uint8_t type[CODOL_ACTION_SLOT_COUNT];
} codol_action_slots_t;
#pragma pack(pop)
#ifdef __cplusplus
extern "C" {
#endif
void CODOL_Scr_SetActionSlot(scr_entref_t ref);
void CODOL_ResetClientActionSlotState(unsigned client);
int CODOL_OverlayActionSlots(codol_player_fields_t *wire,const playerState_t *ps);
#ifdef __cplusplus
}
#endif
#endif
