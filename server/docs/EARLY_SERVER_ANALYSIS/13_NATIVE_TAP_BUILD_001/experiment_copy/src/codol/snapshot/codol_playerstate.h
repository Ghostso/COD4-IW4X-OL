#ifndef CODOL_PLAYERSTATE_H
#define CODOL_PLAYERSTATE_H
#include "codol_delta.h"
#include "codol_player_arrays.h"
#define CODOL_PLAYER_FIELDS 244
/* Semantic state must not inherit engine-header packing. */
#pragma pack(push, 8)
typedef struct {
    uint16_t offset;
    int16_t bits;
    uint8_t hint;
} codol_player_field_t;
typedef struct { uint32_t field[CODOL_PLAYER_FIELDS]; } codol_player_fields_t;
const codol_player_field_t *CODOL_PlayerField(unsigned index);
int CODOL_ReachPlayerFields(codol_player_fields_t *held, const codol_player_fields_t *base,
                            const codol_player_fields_t *requested, int read_origin_velocity,
                            const codol_delta_context_t *context);
/* Writes rov, lc, gaps and the mandatory hint-2 second pass. Snapshot assembly
 * must follow this with the seven player-state array/HUD sections. */
int CODOL_WritePlayerFields(codol_msg_t *msg, const codol_player_fields_t *from,
                            const codol_player_fields_t *to, int read_origin_velocity,
                            codol_delta_context_t *context);
int CODOL_WritePlayerState(codol_msg_t *msg, const codol_player_fields_t *from,
                           const codol_player_fields_t *to,
                           const codol_player_array_updates_t *updates,
                           const codol_hud_state_t *hud_from, const codol_hud_state_t *hud_to,
                           int read_origin_velocity, codol_delta_context_t *context);
#pragma pack(pop)
#endif
