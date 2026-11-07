#ifndef CODOL_PERKS_H
#define CODOL_PERKS_H
#include "codol_assets.h"
#include "codol_playerstate.h"
#include <stdint.h>
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif
enum { CODOL_PERK_SLOTS = 8 };
typedef struct { uint32_t id[CODOL_PERK_SLOTS]; } codol_perk_state_t;
typedef struct { uint32_t id; unsigned slot; } codol_perk_definition_t;
/* coPerkStatsTable: last ASCII-case-insensitive column1 match supplies the
 * numeric ID in column0 and named slot in column5. No pointers escape.
 * Returns 1 found,0 absent,-1 malformed; output unchanged on failure. */
int CODOL_ReadPerkDefinition(const codol_engine_table_t *, const char *, codol_perk_definition_t *);
/* C1 518a10/518b80/518ca0/518db0. These change/query perk IDs only,
 * independently of ability masks/values. Unset clears the resolved slot
 * unconditionally, even if another ID currently occupies that slot. */
int CODOL_SetPerk(codol_perk_state_t *, const codol_perk_definition_t *);
int CODOL_HasPerk(const codol_perk_state_t *, const codol_perk_definition_t *, int *);
int CODOL_UnsetPerk(codol_perk_state_t *, const codol_perk_definition_t *);
void CODOL_ClearPerks(codol_perk_state_t *);
/* Eight measured 8-bit playerState netfields at 4b0..4cc. Reject values
 * outside the wire domain instead of truncating an ID to another perk.
 * Output unchanged on failure; other fields preserved. */
int CODOL_OverlayPlayerPerks(codol_player_fields_t *, const codol_perk_state_t *);
#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
