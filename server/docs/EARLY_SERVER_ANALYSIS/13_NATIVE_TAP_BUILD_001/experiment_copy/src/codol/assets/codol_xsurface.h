#ifndef CODOL_XSURFACE_H
#define CODOL_XSURFACE_H
#include "codol_xmodel.h"
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif
enum { CODOL_SURFACE_BLEND, CODOL_SURFACE_VERTICES, CODOL_SURFACE_TRIANGLES };
typedef struct {
    uint8_t header[84];
    codol_model_array_t arrays[3];
    uint32_t rigid_reference,rigid_count;
    const uint8_t *rigid_stream;
    size_t rigid_stream_size;
    unsigned relocated_tree_arrays; /* streamed models have explicit node/leaf references */
} codol_surface_t;
typedef struct {
    uint8_t *storage;
    const char *name;
    uint32_t name_reference,surfaces_reference;
    unsigned count,unresolved;
    codol_surface_t *surfaces;
    size_t consumed;
} codol_model_surfaces_t;
/* Owned serialized surface data, not native pointers. Inline arrays remain
 * packed; pooled references remain explicit. Rigid stream includes its inline
 * tree dependencies. Output is unchanged on failure. */
int CODOL_ReadModelSurfaces(const codol_asset_t *,codol_model_surfaces_t *);
void CODOL_FreeModelSurfaces(codol_model_surfaces_t *);
typedef struct {
    uint8_t *storage;
    codol_model_array_t arrays[3];
} codol_surface_arrays_t;
/* Copy inline or retained-block arrays to 16-byte-aligned owned memory.
 * References are preserved. Rigid trees are resolved separately. */
int CODOL_ResolveSurfaceArrays(const codol_surface_t *,const codol_model_block_t[8],codol_surface_arrays_t *);
void CODOL_FreeSurfaceArrays(codol_surface_arrays_t *);
typedef struct {
    codol_model_surfaces_t source;
    codol_model_block_t blocks[8];
} codol_mounted_model_surfaces_t;
/* Cached inline/pooled LOD asset from the winning model mount. Named stubs
 * resolve to the newest real surface definition across mounts. Pooled names
 * and block views borrow that definition's archive. Valid until unmount.
 * Checks the active LOD's declared material range and surface count.
 * 1=ready, 0=absent/inactive, -1=invalid or required geometry unresolved
 * (including empty stream placeholders). Output and cache publication are atomic. */
int CODOL_LoadMountedModelSurfaces(const char *,unsigned,const codol_mounted_model_surfaces_t **);
#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
