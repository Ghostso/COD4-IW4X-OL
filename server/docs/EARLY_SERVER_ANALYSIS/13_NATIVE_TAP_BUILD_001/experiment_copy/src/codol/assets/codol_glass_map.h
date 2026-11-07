/* Borrowed C1 map data. SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_GLASS_MAP_H
#define CODOL_GLASS_MAP_H
#include "codol_load_blocks.h"
#include <stdint.h>
#pragma pack(push, 8)
typedef struct {
    unsigned count;
    const uint8_t *server_pieces; /* GameWorldMp: count * 12 */
    const uint8_t *initial_pieces; /* FxWorld: count * 52 */
} codol_glass_map_source_t;
/* 1 valid, 0 absent, -1 invalid. Borrowed spans last until archive unmount. */
int CODOL_LoadMountedGlassMap(const char *, codol_glass_map_source_t *);
int CODOL_ReadGlassMap(const codol_load_blocks_t *, const codol_asset_t *,
    const codol_load_blocks_t *, const codol_asset_t *, codol_glass_map_source_t *);
const char *CODOL_GlassMapFailure(void);
#pragma pack(pop)
#endif
