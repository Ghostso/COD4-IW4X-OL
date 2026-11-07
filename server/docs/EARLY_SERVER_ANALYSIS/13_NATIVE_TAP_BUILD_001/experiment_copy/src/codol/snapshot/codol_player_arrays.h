#ifndef CODOL_PLAYER_ARRAYS_H
#define CODOL_PLAYER_ARRAYS_H
#include "codol_delta.h"
#define CODOL_HUD_FIELDS 42
#define CODOL_HUD_SLOTS 31
/* Semantic state must not inherit engine-header packing. */
#pragma pack(push, 8)
typedef struct {
    uint8_t stats_mask;
    int32_t stats[4];
    uint16_t clip_mask, weapons_mask, weapon_index_mask, reserve_mask;
    int16_t clip_index[16];
    uint8_t clip_presence[16];
    uint16_t clip_ammo[16][2];
    uint16_t weapon_index[15];
    uint8_t weapon_flags[15];
    uint16_t reserve_type[16], reserve_ammo[16];
} codol_player_array_updates_t;
typedef struct { uint32_t field[CODOL_HUD_FIELDS]; } codol_hud_element_t;
/* CoDOL hudelem-relative offset for the wire-order field; UINT_MAX if invalid. */
unsigned CODOL_HudFieldOffset(unsigned index);
const char *CODOL_ReachHudFailure(void);
/* Player-state section 5, the objective and waypoint array at ps+0x5D0.
 *
 * Measured in C1: MSG_ReadDeltaPlayerstate gates the section with one bit at
 * 0x5a1f79, then loops a hard-coded 32 slots (0x5a1f9c) of stride 0x24
 * (0x5a1fd6). Each slot reads a raw 3-bit state (0x5a1fa6) that sits outside
 * the field table, then a six-field delta struct through the generic reader
 * 0x5a0a40 against the table at .rdata:0xc39818. The consumers are the compass
 * drawer 0x4321b0 and the on-screen drawer 0x432790.
 *
 * The field table is not sorted by offset; this is its order, and the indices
 * below are what the gap coder counts in:
 *   0 origin.x (0x04, float)    1 origin.y (0x08, float)
 *   2 origin.z (0x0c, float)    3 icon     (0x20, 12 bits)
 *   4 entNum   (0x10, 11 bits)  5 unknown  (0x14, 4 bits, unread by both drawers)
 *
 * state 0 is the free slot and is how a deletion is expressed; only 1 and 4
 * draw (0x4328b5). entNum 0x7ff means use the world origin (0x4328c5); any
 * other value is read as a client number, not a general entity number. icon
 * indexes CS[4275 + icon] (0x453e72), the same material block hudelems use,
 * and icon 0 falls back to the client's built-in "objective" material. */
#define CODOL_OBJECTIVE_SLOTS 32
#define CODOL_OBJECTIVE_FIELDS 6
#define CODOL_OBJECTIVE_NONE 0x7ffu
typedef struct {
    uint32_t state;                          /* raw 3 bits, outside the table */
    uint32_t field[CODOL_OBJECTIVE_FIELDS];  /* table order, see above */
} codol_objective_t;

/* The trailing per-player sections: 5 (objectives) and 6 (HUD elements). They
 * share one carrier because they share the same from/to delta plumbing. */
typedef struct {
    unsigned count[2]; /* archival first, then current */
    codol_hud_element_t elements[2][CODOL_HUD_SLOTS];
    codol_objective_t objectives[CODOL_OBJECTIVE_SLOTS];
} codol_hud_state_t;
int CODOL_ReachHud(codol_hud_state_t *held, const codol_hud_state_t *base,
                   const codol_hud_state_t *requested, const codol_delta_context_t *context);
/* Arrays are updates: omitted slots retain their base values. HUD states are
 * complete packed arrays: reducing count deletes the tail. NULL means empty. */
int CODOL_WritePlayerArrays(codol_msg_t *msg, const codol_player_array_updates_t *updates,
                            const codol_hud_state_t *hud_from, const codol_hud_state_t *hud_to,
                            codol_delta_context_t *context);
#pragma pack(pop)
#endif
