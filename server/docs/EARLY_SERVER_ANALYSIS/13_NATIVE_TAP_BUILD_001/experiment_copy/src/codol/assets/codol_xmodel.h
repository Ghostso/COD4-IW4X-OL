#ifndef CODOL_XMODEL_H
#define CODOL_XMODEL_H
#include "codol_assets.h"
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif
enum { CODOL_MODEL_BONE_NAMES, CODOL_MODEL_PARENTS, CODOL_MODEL_QUATS,
       CODOL_MODEL_TRANSLATIONS, CODOL_MODEL_CLASSIFICATION, CODOL_MODEL_BASE_MATS,
       CODOL_MODEL_SKELETON_ARRAYS };
typedef struct {
    uint32_t reference, count, stride;
    const uint8_t *data; /* NULL for absent or unresolved; reference distinguishes */
} codol_model_array_t;
typedef struct {
    uint8_t *storage;
    const char *name;
    uint32_t name_reference;
    unsigned bones, roots, surfaces, unresolved;
    size_t consumed;
    codol_model_array_t arrays[CODOL_MODEL_SKELETON_ARRAYS];
} codol_xmodel_skeleton_t;
/* Owned XModel prefix through skeletal arrays. Quaternion stride is 8,
 * matching retained DObjCalcBaseSkel. Pooled arrays remain explicit. Materials, LODs, collision surfaces
 * and conversion to a runtime XModel are subsequent work. Owned arrays are
 * 16-byte aligned; consumed describes packed input bytes. Failure is atomic. */
int CODOL_ReadXModelSkeleton(const codol_asset_t *,codol_xmodel_skeleton_t *);
void CODOL_FreeXModelSkeleton(codol_xmodel_skeleton_t *);
typedef struct {
    const uint8_t *data;
    size_t size;
} codol_model_block_t;
/* Blocks are reconstructed loader memory, NOT consecutive zone-file slices.
 * CoDOL encodes (block << 28 | offset) + 1. Copies resolved data and validates
 * it using the same rules as inline data. The original references are kept.
 * Missing blocks/arrays fail atomically; source and output must be distinct. */
int CODOL_RelocateXModelSkeleton(const codol_xmodel_skeleton_t *,
    const codol_model_block_t blocks[8], codol_xmodel_skeleton_t *);
typedef struct {
    uint16_t index; /* Zone-local index, never an engine SL handle. */
    uint32_t reference;
    const char *text;
} codol_xmodel_bone_name_t;
typedef struct {
    unsigned count, unresolved;
    codol_xmodel_bone_name_t *names;
    char *storage;
} codol_xmodel_bone_names_t;
/* Bind an inline bone-name array to its OWN zone's decoded script-string pool.
 * Text is copied and survives zone/skeleton release. Unresolved strings keep
 * their references; invalid indices and absent/pooled bone arrays fail. */
int CODOL_ResolveXModelBoneNames(const codol_xmodel_skeleton_t *,
    const codol_script_string_t *, unsigned, codol_xmodel_bone_names_t *);
void CODOL_FreeXModelBoneNames(codol_xmodel_bone_names_t *);
typedef struct {
    codol_xmodel_skeleton_t skeleton;
    codol_xmodel_bone_names_t bone_names;
} codol_mounted_model_skeleton_t;
/* Owned cached conversion from a prepared mount, including inline definitions
 * in other assets. Newest archive/last definition
 * wins. 1=ready, 0=absent, -1=matching asset cannot be resolved. Output stays
 * valid until UnmountArchives; bone indices are not engine SL handles yet. */
int CODOL_LoadMountedXModelSkeleton(const char *,const codol_mounted_model_skeleton_t **);
typedef unsigned (*codol_bone_string_acquire_t)(void *,const char *);
typedef void (*codol_bone_string_release_t)(void *,unsigned);
/* One owned string reference per bone, including duplicates. Provider returns
 * zero on failure. Bound handles stay valid until unmount; provider/context
 * must also survive until unmount. Matching patches never reuse older handles. */
int CODOL_BindMountedModelBoneHandles(const char *,codol_bone_string_acquire_t,
    codol_bone_string_release_t,void *,const uint16_t **,unsigned *);
/* Native SL adapter; call only after the engine string system is initialized. */
int CODOL_LoadEngineModelBoneHandles(const char *,const uint16_t **,unsigned *);
typedef struct {
    float mins[3],maxs[3];
    int boneIdx,contents,surfFlags;
    uint32_t triangle_count;
    float (*triangles)[12]; /* CoDOL's 48-byte collision triangle records */
} codol_xmodel_collision_surface_t;
typedef struct {
    uint32_t count;
    codol_xmodel_collision_surface_t *surfaces;
    size_t consumed;
} codol_xmodel_collision_t;
/* Structural traversal through material, technique/shader and LOD dependencies.
 * Converts owned collision bounds; never scans for plausible geometry. */
int CODOL_ReadXModelCollision(const codol_asset_t *,codol_xmodel_collision_t *);
void CODOL_FreeXModelCollision(codol_xmodel_collision_t *);
typedef struct {
    float bounds[2][3], offset[3], radiusSquared;
} codol_xmodel_bone_info_t;
typedef struct {
    float mins[3], maxs[3], radius;
    uint32_t bone_count, bone_info_reference;
    codol_xmodel_bone_info_t *bones;
    uint32_t physics_preset_reference, physics_map_reference;
    size_t consumed;
    uint32_t contents;
    uint32_t flags; /* source byte 0x12b; kept wide for checked native binding */
} codol_xmodel_bounds_t;
/* Owned bounds through the 28-byte bone-info array, before physics assets.
 * A nonzero bone-info pointer denotes an inline array in this stream format.
 * Physics references are retained, not resolved or installed in the engine. */
int CODOL_ReadXModelBounds(const codol_asset_t *, codol_xmodel_bounds_t *);
void CODOL_FreeXModelBounds(codol_xmodel_bounds_t *);
typedef struct {
    float distance;
    uint16_t surface_count, surface_index;
    uint32_t surfaces_reference, name_reference;
    uint8_t remaining[40]; /* fields not yet converted, retained verbatim */
} codol_xmodel_lod_t;
typedef struct {
    unsigned first, count;
    int collision_lod;
    codol_xmodel_lod_t lods[4];
} codol_xmodel_lods_t;
int CODOL_ReadXModelLods(const codol_asset_t *,codol_xmodel_lods_t *);
typedef struct {
    codol_xmodel_collision_t collision;
    codol_xmodel_bounds_t bounds;
    codol_xmodel_lods_t lods;
} codol_mounted_model_geometry_t;
/* Owned geometry for the same winning prepared asset as the skeleton cache.
 * 1=ready, 0=absent, -1=invalid; failure leaves output unchanged. Valid until
 * unmount. Physics references still need binding before native publication. */
int CODOL_LoadMountedXModelGeometry(const char *,const codol_mounted_model_geometry_t **);
/* Validate the complete serialized XModel including inline physics assets.
 * Pooled dependencies remain references; this does not construct a runtime model. */
int CODOL_ReadXModelExtent(const codol_asset_t *, size_t *);
/* Borrowed views of the four inline LOD surface assets. Null/pooled slots have
 * NULL data; their references remain available through ReadXModelLods.
 * Validates the complete model first. Failure leaves all outputs unchanged. */
int CODOL_XModelInlineSurfaceAssets(const codol_asset_t *,codol_asset_t [4]);
typedef struct {
    uint32_t reference;
    codol_asset_t inline_asset;
} codol_xmodel_material_t;
typedef struct {
    unsigned count;
    uint32_t array_reference;
    codol_xmodel_material_t *materials;
    size_t consumed;
} codol_xmodel_materials_t;
/* Owns the slot descriptors; inline asset views borrow the input model bytes.
 * Null and pooled references remain explicit, never fabricated native handles. */
int CODOL_ReadXModelMaterials(const codol_asset_t *,codol_xmodel_materials_t *);
void CODOL_FreeXModelMaterials(codol_xmodel_materials_t *);
/* Winning mounted model; cached descriptors and views survive until unmount.
 * 1=decoded, 0=model absent, -1=invalid. Referenced materials still need binding. */
int CODOL_LoadMountedModelMaterials(const char *,const codol_xmodel_materials_t **);
/* Resolve one slot to a borrowed serialized material, including pooled aliases
 * in the model's own archive, then selecting the current named definition
 * across mounts (including stub resolution and material overrides).
 * 0=model absent; -1=missing/invalid slot or asset.
 * Does not create a native material handle. Output unchanged on failure. */
int CODOL_LoadMountedModelMaterial(const char *,unsigned,codol_asset_t *);
typedef struct {
    codol_asset_t asset;
    const char *name;
    codol_model_block_t blocks[8];
} codol_mounted_model_material_t;
/* Also returns the real definition's name and retained blocks. All views are
 * borrowed until unmount; scratch block 0 is excluded. Same status/atomicity. */
int CODOL_LoadMountedModelMaterialSource(const char *,unsigned,codol_mounted_model_material_t *);
typedef codol_mounted_model_material_t codol_mounted_model_physics_t;
/* Preset (0), collision map (1). Inline views borrow the model; null and pooled
 * references produce empty views. Failure preserves both outputs. */
int CODOL_XModelInlinePhysicsAssets(const codol_asset_t *,codol_asset_t [2]);
/* Resolve a model physics dependency and its defining archive's blocks.
 * 1=ready, 0=model/dependency absent, -1=invalid/unresolved. Borrowed until
 * unmount; no native physics object or simulation is installed here. */
int CODOL_LoadMountedModelPhysics(const char *,unsigned,codol_mounted_model_physics_t *);
#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
