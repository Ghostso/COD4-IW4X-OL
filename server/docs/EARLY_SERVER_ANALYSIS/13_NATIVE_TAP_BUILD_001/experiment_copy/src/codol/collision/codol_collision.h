#ifndef CODOL_COLLISION_H
#define CODOL_COLLISION_H
#include "codol_assets.h"
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif

/* Owned terrain data in IW3 field order. No serialized pointer is exposed. */
typedef struct {
    float distEq[3], zBase, zSlope, start, length;
} codol_collision_border_t;
#pragma pack(push, 4)
typedef struct {
    uint8_t triCount, borderCount;
    /* C1 0x00583e30 reads this byte as a VERTEX BLOCK selector:
     *   movzx esi, byte [partition+2] ; imul esi,esi,0x3000 ; add esi, cm.verts
     * 0x3000 = 1024 verts * 12 bytes. Triangle indices are u16 and therefore
     * BLOCK-RELATIVE, not absolute. This loader previously discarded the byte
     * as padding, which silently relocates every triangle of every partition
     * whose block is nonzero. Only maps with more than 65536 terrain vertices
     * ever set it -- which is why killhouse is unaffected and storm_spring is
     * not. Carried into CollisionPartition_t and added to the vertex base by
     * every triangle-fetch site in _cm_mesh.asm and _phys_world_collision.asm. */
    uint8_t vertBlock, vertBlockPad;
    int firstTri;
    codol_collision_border_t *borders;
} codol_collision_partition_t;
#pragma pack(pop)
typedef struct {
    float origin[3], halfSize[3];
    uint16_t materialIndex, childCount;
    int index;
} codol_collision_aabb_t;
typedef struct {
    uint32_t vertex_count, triangle_count, walkable_words;
    uint32_t border_count, partition_count, aabb_count;
    float (*vertices)[3];
    uint16_t (*triangles)[3];
    uint32_t *walkable;
    codol_collision_border_t *borders;
    codol_collision_partition_t *partitions;
    codol_collision_aabb_t *aabbs;
} codol_collision_terrain_t;
/* Accepts the forward-ordered trees and contiguous partition border slices
 * measured in shipped maps. Unsupported relationships fail atomically.
 * This does not install a clipMap or resolve its other asset dependencies. */
int CODOL_ReadCollisionTerrain(const codol_asset_t *, codol_collision_terrain_t *);
void CODOL_FreeCollisionTerrain(codol_collision_terrain_t *);
typedef struct {
    float normal[3], dist;
    uint8_t type, signbits, pad[2];
} codol_collision_plane_t;
#pragma pack(push, 2)
typedef struct {
    codol_collision_plane_t *plane;
    unsigned materialNum;
    int16_t firstAdjacentSideOffset;
    uint8_t edgeCount, pad;
} codol_collision_side_t;
#pragma pack(pop)
typedef struct __attribute__((aligned(16))) {
    float mins[3];
    int contents;
    float maxs[3];
    unsigned numsides;
    codol_collision_side_t *sides;
    int16_t axialMaterialNum[2][3];
    uint8_t *baseAdjacentSide;
    int16_t firstAdjacentSideOffsets[2][3];
    uint8_t edgeCount[2][3];
#ifdef CODOL_SERVER
    uint16_t glassPieceIndex; /* C1 one-based ID; retained tail padding, stride80 unchanged. */
#endif
} codol_collision_brush_t;
typedef struct {
    codol_collision_plane_t *plane;
    int16_t children[2]; /* negative values encode leaf index as -1-child */
} codol_collision_node_t;
typedef struct {
    uint32_t plane_count, side_count, edge_count, brush_count;
    codol_collision_plane_t *planes;
    codol_collision_side_t *sides;
    uint8_t *edges;
    codol_collision_brush_t *brushes;
    void *brush_storage; /* original allocation for 16-byte alignment */
    uint32_t node_count;
    codol_collision_node_t *nodes; /* plane pointers borrow this object's planes */
} codol_collision_brushes_t;
/* resolved_planes is the explicit shared plane array, exactly planeCount*20
 * bytes. No heuristic search or fabricated plane is used. All data is copied;
 * failure preserves out. Shared-array resolution remains the caller's job. */
int CODOL_ReadCollisionBrushes(const codol_asset_t *, const uint8_t *resolved_planes,
                              size_t plane_size, codol_collision_brushes_t *out);
void CODOL_FreeCollisionBrushes(codol_collision_brushes_t *);
typedef struct {
    size_t offset;
    uint32_t count, name_reference;
    const char *name; /* inline name, otherwise NULL; borrows the asset */
} codol_world_planes_t;
/* Structural traversal of the graphics-world prefix, including inline sky
 * images. Returns a borrowed span; does not load renderer resources. */
int CODOL_ReadWorldPlanes(const codol_asset_t *, codol_world_planes_t *);
const char *CODOL_WorldBaseName(const codol_asset_t *); /* borrowed inline name */
/* The two assets must come from the same zone (pooled references are local).
 * Matches map identity/count, resolves the plane span, then owns conversion. */
int CODOL_ReadWorldBrushes(const codol_asset_t *collision, const codol_asset_t *world,
                           codol_collision_brushes_t *out);
typedef struct {
    char material[64];
    int surfaceFlags, contentFlags;
} codol_collision_material_t;
typedef struct {
    uint32_t count, unresolved;
    codol_collision_material_t *materials;
    uint32_t *name_references; /* nonzero only for unresolved names */
} codol_collision_materials_t;
typedef const char *(*codol_collision_name_resolver_t)(void *, uint32_t);
/* Names must fit the retained 64-byte engine field. NULL resolver/results
 * preserve unresolved references; never install while unresolved is nonzero.
 * Resolver strings are copied immediately. Failure leaves out unchanged. */
int CODOL_ReadCollisionMaterials(const codol_asset_t *, codol_collision_name_resolver_t,
                                 void *context, codol_collision_materials_t *out);
void CODOL_FreeCollisionMaterials(codol_collision_materials_t *);
typedef struct {
    uint16_t firstCollAabbIndex, collAabbCount;
    int brushContents, terrainContents;
    float mins[3], maxs[3];
    int leafBrushNode;
    int16_t cluster, pad;
} codol_collision_leaf_t;
typedef struct {
    float mins[3], maxs[3], radius;
    codol_collision_leaf_t leaf;
} codol_collision_submodel_t;
typedef struct {
    uint32_t leaf_count, submodel_count;
    codol_collision_leaf_t *leaves;
    codol_collision_submodel_t *submodels;
    uint32_t surface_count;
    uint32_t *surfaces;
} codol_collision_leaves_t;
/* CoDOL leaf records have no IW3 visibility-cluster field. Converted cluster
 * stays -1 until visibility integration supplies it. Geometry is owned;
 * leaf-surface values are preserved as serialized, without guessing a renderer
 * index limit. Initialize out to zero; success frees/replaces it, failure
 * preserves it. This does not publish a complete clipMap. */
int CODOL_ReadCollisionLeaves(const codol_asset_t *, codol_collision_leaves_t *out);
void CODOL_FreeCollisionLeaves(codol_collision_leaves_t *);
typedef union {
    struct { uint16_t *brushes; } leaf;
    struct { float dist, range; uint16_t childOffset[2]; } children;
} codol_collision_brush_node_data_t;
#pragma pack(push, 2)
typedef struct {
    uint8_t axis;
    int16_t leafBrushCount;
    int contents;
    codol_collision_brush_node_data_t data;
} codol_collision_brush_node_t;
#pragma pack(pop)
typedef struct {
    uint32_t node_count, index_count, pooled_count;
    codol_collision_brush_node_t *nodes;
    uint16_t *indices;
} codol_collision_brush_tree_t;
int CODOL_ReadCollisionBrushTree(const codol_asset_t *, codol_collision_brush_tree_t *out);
void CODOL_FreeCollisionBrushTree(codol_collision_brush_tree_t *);
#pragma pack(push, 4)
typedef struct {
    uint16_t writable;
    void *xmodel;
    float origin[3], invScaledAxis[3][3], absmin[3], absmax[3];
} codol_collision_static_model_t;
#pragma pack(pop)
typedef struct {
    uint32_t count, unresolved;
    codol_collision_static_model_t *models;
    uint32_t *model_references;
} codol_collision_static_models_t;
typedef void *(*codol_collision_model_resolver_t)(void *,uint32_t);
/* Transforms/bounds are owned; resolved native XModels remain resolver-owned
 * and must outlive this result. NULL resolutions retain explicit references.
 * Do not publish while unresolved is nonzero. Failure preserves out. */
int CODOL_ReadCollisionStaticModels(const codol_asset_t *,codol_collision_model_resolver_t,
                                    void *context,codol_collision_static_models_t *out);
void CODOL_FreeCollisionStaticModels(codol_collision_static_models_t *);
typedef struct {
    codol_collision_materials_t materials;
    codol_collision_brushes_t brushes;
    codol_collision_terrain_t terrain;
    codol_collision_leaves_t leaves;
    codol_collision_brush_tree_t brush_tree;
    codol_map_entities_t entities;
    uint32_t static_model_count; /* native XModel dependencies still need resolution */
    codol_collision_static_models_t static_models;
    uint32_t checksum; /* Serialized collision checksum, header +0xcc. */
} codol_collision_map_t;
/* Atomic owned staging of a same-zone collision/world pair. Frees all staged
 * components on failure and leaves out unchanged. out must be zero-initialized
 * or a previous result; success frees/replaces it. This is not engine publication: unresolved
 * materials, static-model dependencies and visibility still need integration. */
int CODOL_ReadCollisionMap(const codol_asset_t *collision,const codol_asset_t *world,
                           codol_collision_name_resolver_t resolver,void *context,
                           codol_collision_map_t *out);
void CODOL_FreeCollisionMap(codol_collision_map_t *);
/* Same staging/atomicity contract, with optional native static-model binding.
 * The resolver owns returned models and must keep them alive with this map. */
int CODOL_ReadCollisionMapResolved(const codol_asset_t *,const codol_asset_t *,
    codol_collision_name_resolver_t,codol_collision_model_resolver_t,void *,codol_collision_map_t *);
/* 1=loaded, 0=no matching inline world basename, -1=invalid/ambiguous pair.
 * Uses only assets from this zone; atomic replacement follows ReadCollisionMap.
 * Pooled basenames need shared-string resolution and are not guessed. */
int CODOL_LoadZoneCollision(const codol_zone_t *,const char *map_name,
                            codol_collision_name_resolver_t,void *context,
                            codol_collision_map_t *out);
int CODOL_LoadZoneCollisionResolved(const codol_zone_t *,const char *,
    codol_collision_name_resolver_t,codol_collision_model_resolver_t,void *,codol_collision_map_t *);
/* Same matching/status rules; borrowed outputs are unchanged on failure. */
int CODOL_FindZoneCollisionPair(const codol_zone_t *,const char *,codol_asset_t *,codol_asset_t *);
/* Mounted archives, newest first. Matching invalid maps block older fallback.
 * Returned data is owned independently of mounts. Prepared mounts resolve
 * material names against their own replayed block 3; unavailable names retain
 * explicit references. Static models/visibility still require integration. */
int CODOL_LoadMountedCollision(const char *map_name,codol_collision_map_t *out);
typedef void *(*codol_collision_named_model_resolver_t)(void *,const char *);
/* Resolves zone-local model aliases to names before asking the caller for a
 * native XModel. Comma-prefixed references request the canonical name. The
 * caller applies mounted override rules and owns returned models. NULL leaves
 * the encoded dependency explicit; never publish a map with unresolved models.
 * Callback names are borrowed only during the call. No engine object is made
 * by this adapter, and native models may not outlive their owning mounts. */
int CODOL_LoadMountedCollisionModels(const char *,codol_collision_named_model_resolver_t,
    void *,codol_collision_map_t *);
/* Production native-model/SL binding. Returned static model pointers borrow
 * archive caches until unmount. Map publication/visibility remain separate;
 * check unresolved counts before installation. Same 1/0/-1 staging contract. */
int CODOL_LoadEngineCollisionMap(const char *,codol_collision_map_t *);
/* The one addon_map_ents (IW4 type 42) named maps/mp/<playlist>.mapents, from
 * the mounted archives, newest first. A coop match mounts both its playlist
 * zone -- which carries nothing but this asset -- and the base mp_* level zone
 * that carries the world. 1 = loaded (caller owns and frees it), 0 = no
 * mounted zone carries it, -1 = present but unreadable. */
int CODOL_LoadMountedAddonMapEntities(const char *playlist_map,codol_map_entities_t *out);
#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
