#ifndef CODOL_GLASS_GROUPS_H
#define CODOL_GLASS_GROUPS_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    const char *name;
    const uint16_t *pieces;
    uint16_t count;
} codol_glass_group_view_t;
/* Initialize to zero before first use. No installed map differs from a
 * successfully installed map containing zero named groups. */
typedef struct {
    void *groups;
    size_t count;
    uint32_t piece_count;
    int ready;
} codol_glass_groups_t;
int CODOL_InstallGlassGroups(codol_glass_groups_t *,uint32_t piece_count,
    const codol_glass_group_view_t *,size_t count);
void CODOL_FreeGlassGroups(codol_glass_groups_t *);
/* 1=known map (including no match), 0=not installed/invalid arguments.
 * Borrowed output lasts until replacement/free; failure preserves outputs. */
int CODOL_FindGlassGroup(const codol_glass_groups_t *,const char *name,
    const uint16_t **pieces,uint16_t *count);
#ifdef __cplusplus
}
#endif
#endif
