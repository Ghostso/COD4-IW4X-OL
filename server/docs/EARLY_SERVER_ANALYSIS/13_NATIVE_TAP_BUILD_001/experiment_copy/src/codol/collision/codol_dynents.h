#ifndef CODOL_DYNENTS_H
#define CODOL_DYNENTS_H
#include "codol_load_blocks.h"
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    uint32_t type;
    float quat[4],origin[3];
    uint32_t model_reference;
    uint16_t brush_model,physics_brush_model;
    uint32_t effect_reference,preset_reference;
    int health;
    float mass[9];
    uint32_t contents;
    uint32_t model_slot,effect_slot,preset_slot;
} codol_dynamic_entity_t;
typedef struct {
    uint32_t count[2];
    codol_dynamic_entity_t *entities[2];
} codol_dynamic_entities_t;
/* Owned decoding from complete replay. CoDOL's 92-byte record omits the
 * retained IW3 destroyed-pieces pointer (native records are 96 bytes).
 * References and typed pointer-slot addresses remain explicit: no native
 * model/effect/physics object is fabricated or installed. Finite pose/mass
 * data is required; unsupported type semantics remain for later translation.
 * Failure preserves out; success frees/replaces a zero/prior result. */
int CODOL_ReadDynamicEntities(const codol_asset_t *,const codol_load_blocks_t *,codol_dynamic_entities_t *);
void CODOL_FreeDynamicEntities(codol_dynamic_entities_t *);
/* Newest matching map, same archive's replay. 1=decoded, 0=absent, -1=invalid.
 * Source-only mounts cannot provide nonempty definitions. Output is owned. */
int CODOL_LoadMountedDynamicEntities(const char *,codol_dynamic_entities_t *);
typedef struct {
    codol_asset_t asset;
    const char *name;
    codol_model_block_t blocks[8];
} codol_dynamic_dependency_t;
/* type: 4=model, 30=effect, 0=preset. Resolves the selected definition's
 * pointer in its owning archive, then applies mounted named overrides.
 * 1=resolved, 0=null dependency or absent map, -1=invalid/unresolved.
 * Borrowed until unmount; block 0 excluded. Failure preserves out. */
int CODOL_LoadMountedDynamicDependency(const char *,unsigned category,unsigned index,
    unsigned type,codol_dynamic_dependency_t *);
#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
