#ifndef CODOL_EFFECTS_H
#define CODOL_EFFECTS_H
#include "codol_xmodel.h"
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    const char *name;
    uint32_t flags,total_size;
    int32_t looping_life;
    uint32_t counts[3],count;
    const uint8_t *elements; /* contiguous 260-byte source records */
    size_t dependency_offset;
} codol_effect_prefix_t;
/* Borrowed source header/elements from a replayed effect, not native FxElemDef.
 * Resolves inline/pooled names, checks counts and source spans, and preserves
 * out on failure. Nested samples/visuals/extensions follow dependency_offset
 * and still require decoding/relocation. Asset and block views must outlive out. */
int CODOL_ReadEffectPrefix(const codol_asset_t *,const codol_model_block_t [8],codol_effect_prefix_t *);
typedef struct {
    uint32_t reference;
    codol_asset_t inline_asset; /* model/material; zero for pooled references */
    const char *string; /* sound/runner visual */
} codol_effect_visual_t;
typedef struct {
    const uint8_t *record,*velocity_samples,*visual_samples;
    unsigned velocity_count,visual_sample_count,visual_count;
    codol_effect_visual_t *visuals;
    const char *effect_names[3],*extra_name; /* +256: C1 spawn-sound XString */
    const uint8_t *extension,*trail_vertices,*trail_indices;
    uint32_t extension_size,trail_vertex_count,trail_index_count;
} codol_effect_element_t;
typedef struct {
    codol_effect_prefix_t prefix;
    codol_effect_element_t *elements;
} codol_effect_source_t;
/* Complete serialized traversal, including sample arrays, visual dependencies,
 * effect-name references and extension records. Owns descriptor arrays only;
 * payloads/strings borrow asset and blocks. No native pointers are fabricated.
 * out is zero/prior; success replaces it, failure preserves it. */
int CODOL_ReadEffectSource(const codol_asset_t *,const codol_model_block_t [8],codol_effect_source_t *);
void CODOL_FreeEffectSource(codol_effect_source_t *);
/* Canonical named definition, newest first. Cached source survives replacement
 * until full unmount. 1=decoded, 0=absent, -1=invalid; out unchanged unless ready. */
int CODOL_LoadMountedEffectSource(const char *,const codol_effect_source_t **);
typedef codol_mounted_model_material_t codol_effect_visual_source_t;
/* Resolve a material/model visual through the effect's owning archive, then
 * current named overrides. Decal visual indices address both materials.
 * Returns 0 for null/non-asset visuals or absent effect, -1 for invalid/missing
 * dependencies, 1 for a borrowed source (block 0 excluded). Not a native handle. */
int CODOL_LoadMountedEffectVisual(const char *,unsigned element,unsigned visual,codol_effect_visual_source_t *);
#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
