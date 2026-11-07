#ifndef CODOL_COLLISION_NATIVE_H
#define CODOL_COLLISION_NATIVE_H
#include "codol_collision.h"
#include "cm_local.h"
#include "codol_dynents_native.h"
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif
/* Owned native brush/BSP data, including the extra brush, index and leaf-brush
 * node required by CM_InitBoxHull. brush_count excludes the extra box brush;
 * brush_node_count/index_count include their extra entries. No pointer borrows
 * decoded staging. This is not a complete clipMap or visibility installation. */
typedef struct {
    uint32_t plane_count,side_count,edge_count,node_count,brush_count;
    uint32_t brush_node_count,index_count;
    cplane_t *planes;
    cbrushside_t *sides;
    char *edges;
    cNode_t *nodes;
    cbrush_t *brushes;
    void *brush_storage;
    cLeafBrushNode_t *brush_nodes;
    uint16_t *indices;
    cmodel_t box_model;
} codol_native_brushes_t;
/* Source must be decoded/validated collision staging. Validates/remaps all
 * borrowed pointer spans and preserves out on failure. out is zero or a prior
 * result; success frees/replaces it. Source may be freed after success. */
int CODOL_BuildNativeCollisionBrushes(const codol_collision_brushes_t *,
    const codol_collision_brush_tree_t *,codol_native_brushes_t *);
void CODOL_FreeNativeCollisionBrushes(codol_native_brushes_t *);
typedef struct {
    uint32_t vertex_count,triangle_count,walkable_words,border_count,partition_count,aabb_count;
    float (*vertices)[3];
    uint16_t (*triangles)[3];
    uint32_t *walkable;
    CollisionBorder_t *borders;
    CollisionPartition_t *partitions;
    CollisionAabbTree_t *aabbs;
} codol_native_terrain_t;
/* Owned native terrain, with partition border pointers relocated. Source is
 * validated decoded staging; failure preserves out, success replaces it.
 * No visibility or engine-global collision state is installed. */
int CODOL_BuildNativeCollisionTerrain(const codol_collision_terrain_t *,codol_native_terrain_t *);
void CODOL_FreeNativeCollisionTerrain(codol_native_terrain_t *);
typedef struct {
    uint32_t leaf_count,model_count;
    cLeaf_t *leaves;
    cmodel_t *models;
    uint32_t surface_count;
    uint32_t *surfaces;
} codol_native_leaves_t;
/* Owned leaf/inline-model records. Validates references against the source
 * terrain/tree counts and keeps cluster values unchanged; no PVS is invented.
 * The temporary box handle is reserved and cannot become an inline model.
 * Failure preserves out; success frees/replaces a zero/prior result. */
int CODOL_BuildNativeCollisionLeaves(const codol_collision_leaves_t *,uint32_t,uint32_t,
    codol_native_leaves_t *);
void CODOL_FreeNativeCollisionLeaves(codol_native_leaves_t *);
typedef struct {
    uint32_t material_count,model_count;
    dmaterial_t *materials;
    cStaticModel_t *models;
} codol_native_collision_assets_t;
/* Owns native material and static-model records. XModels remain borrowed from
 * the resolver/archive and must outlive this result. Rejects unresolved data.
 * Atomic replacement; no global clipmap or spatial sectors are installed. */
int CODOL_BuildNativeCollisionAssets(const codol_collision_materials_t *,
    const codol_collision_static_models_t *,codol_native_collision_assets_t *);
void CODOL_FreeNativeCollisionAssets(codol_native_collision_assets_t *);
typedef struct {
    const char *name;
    uint32_t cluster_count,cluster_bytes;
    int vised;
    const uint8_t *visibility;
    size_t visibility_size;
    const int16_t *leaf_clusters;
    uint32_t leaf_count;
} codol_clip_map_metadata_t;
typedef struct {
    clipMap_t map;
    codol_native_brushes_t brushes;
    codol_native_terrain_t terrain;
    codol_native_leaves_t leaves;
    codol_native_collision_assets_t assets;
    codol_native_dynamic_entities_t dynamics;
    unsigned trigger_model_base,trigger_model_count;
} codol_native_clip_map_t;
/* Append trigger hull brushes and inline collision models before publishing cm. */
int CODOL_AppendNativeTriggers(const codol_map_entities_t *,codol_native_clip_map_t *);
int CODOL_TriggerClipHandle(unsigned);
/* Assembles owned native clipmap storage from validated staging and explicit
 * visibility metadata and the staged collision checksum. XModel/FX/preset bindings remain borrowed.
 * No checksum, leaf clusters or PVS are fabricated. Success replaces out;
 * the native fields do not borrow source buffers. Does not publish cm,
 * initialize thread data or activate physics. Callers must separately retain
 * source MapEnts extensions for CoDOL trigger/stage startup; those extensions
 * are not represented by IW3 MapEnts or consumed by this constructor. */
int CODOL_BuildNativeClipMap(const codol_collision_map_t *,const codol_dynamic_entities_t *,
    const codol_dynamic_binding_t *const [2],const codol_clip_map_metadata_t *,codol_native_clip_map_t *);
void CODOL_FreeNativeClipMap(codol_native_clip_map_t *);
/* Explicit conservative server policy for maps without translated PVS:
 * all leaves share cluster 0, with an all-visible row and vised=false.
 * This disables spatial visibility culling; it is not recovered CoDOL PVS.
 * Other construction/ownership requirements are identical to BuildNativeClipMap. */
int CODOL_BuildUnculledNativeClipMap(const codol_collision_map_t *,const codol_dynamic_entities_t *,
    const codol_dynamic_binding_t *const [2],const char *,codol_native_clip_map_t *);
/* Engine dependency adapter: resolves this mounted map's dynamic models, FX
 * graphs and presets, then builds the explicit unculled native map above.
 * source must be the same mounted map's collision staging. Caller retains its
 * MapEnts extensions for startup. SL must be initialized. 1=ready, 0=absent,
 * -1=invalid/unresolved; failure preserves out. Does not install or activate cm. */
int CODOL_BuildEngineClipMap(const char *,const codol_collision_map_t *,codol_native_clip_map_t *);
/* Installs a fully constructed maps/mp/<name>.d3dbsp in cm. Retains source
 * MapEnts extensions, but does not initialize threads or activate physics. */
int CODOL_InstallEngineClipMap(const char *);
void CODOL_ShutdownEngineClipMap(void);
#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
