#ifndef CODOL_GLASS_LOAD_H
#define CODOL_GLASS_LOAD_H
#include "codol_load_blocks.h"
#include "codol_glass_groups.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Materialize a replayed GameWorldMp's named groups. Destination must be
 * zero-initialized or owned by the glass-group API. Failure preserves it;
 * successful output owns its names and IDs independently of the archive. */
int CODOL_LoadGlassGroups(const codol_load_blocks_t *,const codol_asset_t *,
                         codol_glass_groups_t *);
/* Named GameWorldMp lookup, with normal mounted-definition precedence.
 * 1=ready, 0=absent, -1=invalid; borrowed output lasts until archive unmount. */
int CODOL_LoadMountedGlassGroups(const char *,const codol_glass_groups_t **);
#ifdef __cplusplus
}
#endif
#endif
