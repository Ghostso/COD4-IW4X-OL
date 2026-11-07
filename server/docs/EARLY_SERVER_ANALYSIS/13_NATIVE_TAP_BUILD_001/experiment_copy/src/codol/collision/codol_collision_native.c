#include "codol_collision_native.h"
#include "qcommon.h"
#include <float.h>
#include <limits.h>
#include <math.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

_Static_assert(sizeof(cplane_t)==20,"native collision plane ABI");
_Static_assert(sizeof(cbrushside_t)==12,"native collision side ABI");
_Static_assert(sizeof(cbrush_t)==80,"native collision brush ABI");
_Static_assert(sizeof(cLeafBrushNode_t)==20,"native leaf brush node ABI");
_Static_assert(offsetof(cbrush_t,sides)==32,"native collision brush sides");
_Static_assert(offsetof(cLeafBrushNode_t,data)==8,"native brush node union");
_Static_assert(sizeof(CollisionBorder_t)==28,"native collision border ABI");
_Static_assert(sizeof(CollisionPartition_t)==12,"native collision partition ABI");
_Static_assert(offsetof(CollisionPartition_t,borders)==8,"native partition border pointer");
_Static_assert(sizeof(CollisionAabbTree_t)==32,"native collision AABB ABI");
_Static_assert(offsetof(CollisionAabbTree_t,materialIndex)==24,"native AABB material");
_Static_assert(offsetof(CollisionAabbTree_t,u)==28,"native AABB child/partition index");
_Static_assert(sizeof(cLeaf_t)==44,"native collision leaf ABI");
_Static_assert(sizeof(cmodel_t)==72,"native inline model ABI");
_Static_assert(offsetof(cLeaf_t,leafBrushNode)==36,"native leaf brush node offset");
_Static_assert(offsetof(cLeaf_t,cluster)==40,"native leaf cluster offset");
_Static_assert(offsetof(cmodel_t,leaf)==28,"native inline model leaf offset");
_Static_assert(sizeof(dmaterial_t)==72,"native collision material ABI");
_Static_assert(sizeof(cStaticModel_t)==80,"native static model ABI");
_Static_assert(offsetof(cStaticModel_t,xmodel)==4,"native static model pointer");
_Static_assert(offsetof(cStaticModel_t,origin)==8,"native static model origin");
_Static_assert(offsetof(cStaticModel_t,invScaledAxis)==20,"native static model axis");
_Static_assert(offsetof(cStaticModel_t,absmin)==56,"native static model bounds");

static void *array(uint32_t count,size_t stride)
{
    if(count>CODOL_ASSET_LIMIT/stride) return NULL;
    return calloc(count ? count : 1,stride);
}
void CODOL_FreeNativeCollisionAssets(codol_native_collision_assets_t *out)
{
    if (!out) return;
    free(out->materials); free(out->models); memset(out,0,sizeof(*out));
}
int CODOL_BuildNativeCollisionAssets(const codol_collision_materials_t *materials,
    const codol_collision_static_models_t *models,codol_native_collision_assets_t *out)
{
    codol_native_collision_assets_t result={0}; uint32_t i,j;
    if (!materials || !models || !out || materials->unresolved || models->unresolved ||
        (materials->count && !materials->materials) || (models->count && !models->models)) return 0;
    result.material_count=materials->count; result.model_count=models->count;
    result.materials=array(result.material_count,sizeof(*result.materials));
    result.models=array(result.model_count,sizeof(*result.models));
    if (!result.materials || !result.models) goto fail;
    for (i=0;i<result.material_count;++i) {
        const codol_collision_material_t *s=materials->materials+i;
        if (!s->material[0] || !memchr(s->material,0,sizeof(s->material)) ||
            (materials->name_references && materials->name_references[i])) goto fail;
        memcpy(result.materials[i].material,s->material,sizeof(s->material));
        result.materials[i].surfaceFlags=s->surfaceFlags;
        result.materials[i].contentFlags=s->contentFlags;
    }
    for (i=0;i<result.model_count;++i) {
        const codol_collision_static_model_t *s=models->models+i;
        cStaticModel_t *d=result.models+i;
        if (!s->xmodel || (models->model_references && models->model_references[i])) goto fail;
        for (j=0;j<3;++j) {
            if (!isfinite(s->origin[j]) || !isfinite(s->absmin[j]) || !isfinite(s->absmax[j]) ||
                s->absmin[j]>s->absmax[j]) goto fail;
            d->origin[j]=s->origin[j]; d->absmin[j]=s->absmin[j]; d->absmax[j]=s->absmax[j];
        }
        for (j=0;j<9;++j) {
            if (!isfinite(s->invScaledAxis[j/3][j%3])) goto fail;
            d->invScaledAxis[j/3][j%3]=s->invScaledAxis[j/3][j%3];
        }
        d->writable=s->writable; d->xmodel=s->xmodel;
    }
    CODOL_FreeNativeCollisionAssets(out); *out=result; return 1;
fail:
    CODOL_FreeNativeCollisionAssets(&result); return 0;
}
static int span(const void *base,uint32_t count,size_t stride,const void *pointer,
    uint32_t length,uint32_t *index)
{
    uintptr_t delta;
    if(!base || !pointer || (uintptr_t)pointer<(uintptr_t)base) return 0;
    delta=(uintptr_t)pointer-(uintptr_t)base;
    if(delta%stride || delta/stride>=count || length>count-delta/stride) return 0;
    *index=(uint32_t)(delta/stride); return 1;
}
void CODOL_FreeNativeCollisionBrushes(codol_native_brushes_t *out)
{
    if(!out) return;
    free(out->planes); free(out->sides); free(out->edges); free(out->nodes);
    free(out->brush_storage); free(out->brush_nodes); free(out->indices);
    memset(out,0,sizeof(*out));
}
int CODOL_BuildNativeCollisionBrushes(const codol_collision_brushes_t *source,
    const codol_collision_brush_tree_t *tree,codol_native_brushes_t *out)
{
    codol_native_brushes_t result={0}; uint32_t i,j,index;
    cbrush_t *box; cLeafBrushNode_t *box_node;
    if(!source || !tree || !out || source->brush_count>UINT16_MAX ||
        tree->node_count>=INT_MAX || tree->index_count==UINT32_MAX ||
        (source->plane_count && !source->planes) || (source->side_count && !source->sides) ||
        (source->edge_count && !source->edges) || (source->node_count && !source->nodes) ||
        (source->brush_count && !source->brushes) || (tree->node_count && !tree->nodes) ||
        (tree->index_count && !tree->indices)) return 0;
    result.plane_count=source->plane_count; result.side_count=source->side_count;
    result.edge_count=source->edge_count; result.node_count=source->node_count;
    result.brush_count=source->brush_count; result.brush_node_count=tree->node_count+1;
    result.index_count=tree->index_count+1;
    result.planes=array(result.plane_count,sizeof(*result.planes));
    result.sides=array(result.side_count,sizeof(*result.sides));
    result.edges=array(result.edge_count,1);
    result.nodes=array(result.node_count,sizeof(*result.nodes));
    result.brush_nodes=array(result.brush_node_count,sizeof(*result.brush_nodes));
    result.indices=array(result.index_count,sizeof(*result.indices));
    result.brush_storage=calloc(1,(size_t)(result.brush_count+1)*sizeof(*result.brushes)+15);
    if(!result.planes || !result.sides || !result.edges || !result.nodes ||
        !result.brush_nodes || !result.indices || !result.brush_storage) goto fail;
    result.brushes=(cbrush_t *)(((uintptr_t)result.brush_storage+15)&~(uintptr_t)15);
    for(i=0;i<result.plane_count;++i) {
        memcpy(result.planes[i].normal,source->planes[i].normal,sizeof(result.planes[i].normal));
        result.planes[i].dist=source->planes[i].dist; result.planes[i].type=source->planes[i].type;
        result.planes[i].signbits=source->planes[i].signbits;
    }
    for(i=0;i<result.side_count;++i) {
        const codol_collision_side_t *from=source->sides+i; cbrushside_t *to=result.sides+i;
        if(!span(source->planes,source->plane_count,sizeof(*source->planes),from->plane,1,&index)) goto fail;
        to->plane=result.planes+index; to->materialNum=from->materialNum;
        to->firstAdjacentSideOffset=from->firstAdjacentSideOffset; to->edgeCount=from->edgeCount;
    }
    if(result.edge_count) memcpy(result.edges,source->edges,result.edge_count);
    for(i=0;i<result.node_count;++i) {
        if(!span(source->planes,source->plane_count,sizeof(*source->planes),source->nodes[i].plane,1,&index)) goto fail;
        result.nodes[i].plane=result.planes+index;
        memcpy(result.nodes[i].children,source->nodes[i].children,sizeof(result.nodes[i].children));
    }
    for(i=0;i<result.brush_count;++i) {
        const codol_collision_brush_t *from=source->brushes+i; cbrush_t *to=result.brushes+i;
        uint64_t edges=0;
        memcpy(to->mins,from->mins,sizeof(to->mins)); memcpy(to->maxs,from->maxs,sizeof(to->maxs));
        to->contents=from->contents; to->numsides=from->numsides;
#ifdef CODOL_SERVER
        to->glassPieceIndex=from->glassPieceIndex;
#endif
        if(from->numsides) {
            if(!span(source->sides,source->side_count,sizeof(*source->sides),from->sides,from->numsides,&index)) goto fail;
            to->sides=result.sides+index;
            for(j=0;j<from->numsides;++j) edges+=from->sides[j].edgeCount;
        }
        memcpy(to->axialMaterialNum,from->axialMaterialNum,sizeof(to->axialMaterialNum));
        memcpy(to->firstAdjacentSideOffsets,from->firstAdjacentSideOffsets,sizeof(to->firstAdjacentSideOffsets));
        memcpy(to->edgeCount,from->edgeCount,sizeof(to->edgeCount));
        for(j=0;j<6;++j) edges+=from->edgeCount[j/3][j%3];
        if(edges) {
            if(edges>UINT32_MAX || !span(source->edges,source->edge_count,1,from->baseAdjacentSide,(uint32_t)edges,&index)) goto fail;
            to->baseAdjacentSide=result.edges+index;
        }
    }
    for(i=0;i<tree->index_count;++i) {
        if(tree->indices[i]>=source->brush_count) goto fail;
        result.indices[i]=tree->indices[i];
    }
    for(i=0;i<tree->node_count;++i) {
        const codol_collision_brush_node_t *from=tree->nodes+i; cLeafBrushNode_t *to=result.brush_nodes+i;
        to->axis=from->axis; to->leafBrushCount=from->leafBrushCount; to->contents=from->contents;
        if(from->leafBrushCount>0) {
            if(!span(tree->indices,tree->index_count,sizeof(*tree->indices),from->data.leaf.brushes,
                (uint32_t)from->leafBrushCount,&index)) goto fail;
            to->data.leaf.brushes=result.indices+index;
        } else {
            to->data.children.dist=from->data.children.dist; to->data.children.range=from->data.children.range;
            memcpy(to->data.children.childOffset,from->data.children.childOffset,sizeof(to->data.children.childOffset));
        }
    }
    /* Same sentinel layout as retained CM_InitBoxHull/CMod_AllocLeafBrushNode. */
    box=result.brushes+result.brush_count; box->contents=-1;
    result.box_model.leaf.brushContents=-1;
    for(i=0;i<3;++i) {
        result.box_model.leaf.mins[i]=FLT_MAX; result.box_model.leaf.maxs[i]=-FLT_MAX;
        box->axialMaterialNum[0][i]=box->axialMaterialNum[1][i]=-1;
    }
    result.box_model.leaf.leafBrushNode=tree->node_count;
    box_node=result.brush_nodes+tree->node_count; box_node->leafBrushCount=1;
    box_node->data.leaf.brushes=result.indices+tree->index_count;
    result.indices[tree->index_count]=(uint16_t)result.brush_count;
    {
        /* Mantle census: the retained Mantle_Check traces with CONTENTS_MANTLE
         * (0x1000000). alpha0022 mantle_mount.md measured 90 such brushes on
         * mp_killhouse_sh; zero here means the server can never mantle. */
        uint32_t mantle=0,shown=0;
        for(i=0;i<result.brush_count;++i) if(result.brushes[i].contents & 0x1000000) {
            ++mantle;
            if(shown<4) { ++shown; Com_Printf(CON_CHANNEL_SYSTEM,"CoDOL mantle census: brush %u mins (%.0f %.0f %.0f) maxs (%.0f %.0f %.0f) contents 0x%x%s",(unsigned)i,
                result.brushes[i].mins[0],result.brushes[i].mins[1],result.brushes[i].mins[2],result.brushes[i].maxs[0],result.brushes[i].maxs[1],result.brushes[i].maxs[2],(unsigned)result.brushes[i].contents,"\n"); }
        }
        Com_Printf(CON_CHANNEL_SYSTEM,"CoDOL mantle census: %u of %u brushes carry CONTENTS_MANTLE%s",(unsigned)mantle,(unsigned)result.brush_count,"\n");
    }
    CODOL_FreeNativeCollisionBrushes(out); *out=result; return 1;
fail:
    CODOL_FreeNativeCollisionBrushes(&result); return 0;
}
void CODOL_FreeNativeCollisionTerrain(codol_native_terrain_t *out)
{
    if(!out) return;
    free(out->vertices); free(out->triangles); free(out->walkable);
    free(out->borders); free(out->partitions); free(out->aabbs);
    memset(out,0,sizeof(*out));
}
int CODOL_BuildNativeCollisionTerrain(const codol_collision_terrain_t *source,codol_native_terrain_t *out)
{
    codol_native_terrain_t result={0}; uint32_t i,j,index;
    if(!source || !out || source->triangle_count>INT_MAX || source->partition_count>INT_MAX ||
        source->aabb_count>INT_MAX || source->border_count>INT_MAX ||
        source->walkable_words!=((uint64_t)source->triangle_count*3+31)/32) return 0;
#define COPY(field,countfield) do { \
    result.countfield=source->countfield; \
    if(result.countfield && !source->field) goto fail; \
    result.field=array(result.countfield,sizeof(*result.field)); \
    if(!result.field) goto fail; \
    if(result.countfield) memcpy(result.field,source->field,(size_t)result.countfield*sizeof(*result.field)); \
} while(0)
    COPY(vertices,vertex_count); COPY(triangles,triangle_count); COPY(walkable,walkable_words);
#undef COPY
    result.border_count=source->border_count; result.partition_count=source->partition_count;
    result.aabb_count=source->aabb_count;
    if((result.border_count && !source->borders) || (result.partition_count && !source->partitions) ||
        (result.aabb_count && !source->aabbs)) goto fail;
    result.borders=array(result.border_count,sizeof(*result.borders));
    result.partitions=array(result.partition_count,sizeof(*result.partitions));
    result.aabbs=array(result.aabb_count,sizeof(*result.aabbs));
    if(!result.borders || !result.partitions || !result.aabbs) goto fail;
    for(i=0;i<result.border_count;++i) {
        const codol_collision_border_t *from=source->borders+i; CollisionBorder_t *to=result.borders+i;
        memcpy(to->distEq,from->distEq,sizeof(to->distEq));
        to->zBase=from->zBase; to->zSlope=from->zSlope;
        to->start=from->start; to->length=from->length;
    }
    for(i=0;i<result.partition_count;++i) {
        const codol_collision_partition_t *from=source->partitions+i; CollisionPartition_t *to=result.partitions+i;
        if(from->firstTri<0 || (uint32_t)from->firstTri>result.triangle_count ||
            from->triCount>result.triangle_count-(uint32_t)from->firstTri) goto fail;
        to->firstTri=from->firstTri; to->triCount=from->triCount; to->borderCount=from->borderCount;
        /* Triangle indices are u16 and relative to the partition's vertex BLOCK
         * (C1 0x00583e30 adds vertBlock*0x3000 to cm.verts), so they can only be
         * range-checked once the owning partition is known. Checking them against
         * the total vertex count before this point was meaningless. */
        to->vertBlock=from->vertBlock; to->vertBlockPad=0;
        for(j=0;j<(uint32_t)from->triCount;++j) {
            uint32_t t=(uint32_t)from->firstTri+j,k;
            for(k=0;k<3;++k)
                if((uint32_t)from->vertBlock*1024u+result.triangles[t][k]>=result.vertex_count)
                    goto fail;
        }
        if(from->borderCount) {
            if(!span(source->borders,source->border_count,sizeof(*source->borders),from->borders,from->borderCount,&index)) goto fail;
            to->borders=result.borders+index;
        }
    }
    for(i=0;i<result.aabb_count;++i) {
        const codol_collision_aabb_t *from=source->aabbs+i; CollisionAabbTree_t *to=result.aabbs+i;
        if(from->index<0) goto fail;
        index=(uint32_t)from->index;
        if(from->childCount) {
            if(index<=i || index>result.aabb_count || from->childCount>result.aabb_count-index) goto fail;
        } else if(index>=result.partition_count) goto fail;
        memcpy(to->origin,from->origin,sizeof(to->origin)); memcpy(to->halfSize,from->halfSize,sizeof(to->halfSize));
        to->materialIndex=from->materialIndex; to->childCount=from->childCount; to->u.firstChildIndex=from->index;
    }
    CODOL_FreeNativeCollisionTerrain(out); *out=result; return 1;
fail:
    CODOL_FreeNativeCollisionTerrain(&result); return 0;
}
void CODOL_FreeNativeCollisionLeaves(codol_native_leaves_t *out)
{
    if(!out) return;
    free(out->leaves); free(out->models); free(out->surfaces); memset(out,0,sizeof(*out));
}
static int native_leaf(const codol_collision_leaf_t *from,uint32_t aabbs,uint32_t nodes,cLeaf_t *to)
{
    if(from->firstCollAabbIndex>aabbs || from->collAabbCount>aabbs-from->firstCollAabbIndex ||
        from->leafBrushNode<0 || (nodes ? (uint32_t)from->leafBrushNode>=nodes : from->leafBrushNode!=0) ||
        from->cluster < -1) return 0;
    to->firstCollAabbIndex=from->firstCollAabbIndex; to->collAabbCount=from->collAabbCount;
    to->brushContents=from->brushContents; to->terrainContents=from->terrainContents;
    memcpy(to->mins,from->mins,sizeof(to->mins)); memcpy(to->maxs,from->maxs,sizeof(to->maxs));
    to->leafBrushNode=from->leafBrushNode; to->cluster=from->cluster;
    return 1;
}
int CODOL_BuildNativeCollisionLeaves(const codol_collision_leaves_t *source,uint32_t aabbs,
    uint32_t nodes,codol_native_leaves_t *out)
{
    codol_native_leaves_t result={0}; uint32_t i;
    if(!source || !out || source->submodel_count>CAPSULE_MODEL_HANDLE ||
        (source->leaf_count && !source->leaves) || (source->submodel_count && !source->submodels) ||
        (source->surface_count && !source->surfaces)) return 0;
    result.leaf_count=source->leaf_count; result.model_count=source->submodel_count;
    result.leaves=array(result.leaf_count,sizeof(*result.leaves));
    result.models=array(result.model_count,sizeof(*result.models));
    result.surface_count=source->surface_count;
    result.surfaces=array(result.surface_count,sizeof(*result.surfaces));
    if(!result.leaves || !result.models || !result.surfaces) goto fail;
    if(result.surface_count) memcpy(result.surfaces,source->surfaces,result.surface_count*sizeof(*result.surfaces));
    for(i=0;i<result.leaf_count;++i)
        if(!native_leaf(source->leaves+i,aabbs,nodes,result.leaves+i)) goto fail;
    for(i=0;i<result.model_count;++i) {
        const codol_collision_submodel_t *from=source->submodels+i; cmodel_t *to=result.models+i;
        if(!native_leaf(&from->leaf,aabbs,nodes,&to->leaf)) goto fail;
        memcpy(to->mins,from->mins,sizeof(to->mins)); memcpy(to->maxs,from->maxs,sizeof(to->maxs));
        to->radius=from->radius;
    }
    CODOL_FreeNativeCollisionLeaves(out); *out=result; return 1;
fail:
    CODOL_FreeNativeCollisionLeaves(&result); return 0;
}

void CODOL_FreeNativeClipMap(codol_native_clip_map_t *out)
{
    if (!out) return;
    free((void *)out->map.name); free(out->map.visibility);
    if (out->map.mapEnts) { free(out->map.mapEnts->entityString); free(out->map.mapEnts); }
    CODOL_FreeNativeDynamicEntities(&out->dynamics);
    CODOL_FreeNativeCollisionAssets(&out->assets);
    CODOL_FreeNativeCollisionLeaves(&out->leaves);
    CODOL_FreeNativeCollisionTerrain(&out->terrain);
    CODOL_FreeNativeCollisionBrushes(&out->brushes);
    memset(out,0,sizeof(*out));
}
int CODOL_BuildUnculledNativeClipMap(const codol_collision_map_t *source,const codol_dynamic_entities_t *dynamic,
    const codol_dynamic_binding_t *const bindings[2],const char *name,codol_native_clip_map_t *out)
{
    static const uint8_t visible[8]={255,255,255,255,255,255,255,255};
    codol_clip_map_metadata_t metadata={0}; int16_t *clusters; int ready;
    if (!source || !out || !source->leaves.leaf_count ||
        source->leaves.leaf_count>CODOL_ASSET_LIMIT/sizeof(*clusters)) return 0;
    clusters=calloc(source->leaves.leaf_count,sizeof(*clusters)); if (!clusters) return 0;
    /* CMod_LoadVisibility uses an all-FF row when its BSP visibility lump is
     * absent. CoDOL has no leaf cluster field, so this explicit adapter also
     * assigns every leaf to the same native cluster. The eight-byte row uses
     * the retained loader's 64-cluster rounding convention. */
    metadata.name=name; metadata.cluster_count=1; metadata.cluster_bytes=sizeof(visible);
    metadata.visibility=visible; metadata.visibility_size=sizeof(visible);
    metadata.leaf_clusters=clusters; metadata.leaf_count=source->leaves.leaf_count;
    ready=CODOL_BuildNativeClipMap(source,dynamic,bindings,&metadata,out);
    free(clusters); return ready;
}
int CODOL_BuildNativeClipMap(const codol_collision_map_t *source,const codol_dynamic_entities_t *dynamic,
    const codol_dynamic_binding_t *const bindings[2],const codol_clip_map_metadata_t *metadata,
    codol_native_clip_map_t *out)
{
    codol_native_clip_map_t result={0}; clipMap_t *m=&result.map;
    size_t name_size,vis_size; uint64_t expected; uint32_t i,j;
    if (!source || !dynamic || !bindings || !metadata || !out || !metadata->name ||
        !*metadata->name || !source->brushes.node_count || !source->leaves.leaf_count || !source->leaves.submodel_count ||
        metadata->leaf_count!=source->leaves.leaf_count || !metadata->leaf_clusters ||
        !metadata->cluster_count || metadata->cluster_count>32768 ||
        metadata->cluster_bytes<(metadata->cluster_count+7)/8 ||
        (metadata->vised!=0 && metadata->vised!=1) || !metadata->visibility ||
        !source->entities.text || !source->entities.text_size || source->entities.text_size>CODOL_ASSET_LIMIT ||
        memchr(source->entities.text,0,source->entities.text_size)!=source->entities.text+source->entities.text_size-1 ||
        source->static_model_count!=source->static_models.count) return 0;
    name_size=strlen(metadata->name)+1; if (name_size>4096) return 0;
    expected=(uint64_t)metadata->cluster_bytes*(metadata->vised ? metadata->cluster_count : 1);
    if (expected>CODOL_ASSET_LIMIT || expected!=metadata->visibility_size) return 0;
    vis_size=(size_t)expected;
    if (!CODOL_BuildNativeCollisionBrushes(&source->brushes,&source->brush_tree,&result.brushes) ||
        !CODOL_BuildNativeCollisionTerrain(&source->terrain,&result.terrain) ||
        !CODOL_BuildNativeCollisionLeaves(&source->leaves,source->terrain.aabb_count,source->brush_tree.node_count,&result.leaves) ||
        !CODOL_BuildNativeCollisionAssets(&source->materials,&source->static_models,&result.assets) ||
        !CODOL_BuildNativeDynamicEntities(dynamic,bindings,&result.dynamics)) goto fail;
    for (i=0;i<result.leaves.leaf_count;++i) {
        int cluster=metadata->leaf_clusters[i];
        if (cluster < -1 || cluster >= (int)metadata->cluster_count) goto fail;
        result.leaves.leaves[i].cluster=cluster;
    }
    for (i=0;i<result.brushes.side_count;++i)
        if (result.brushes.sides[i].materialNum>=result.assets.material_count) goto fail;
    for (i=0;i<result.brushes.brush_count;++i) for (j=0;j<6;++j)
        if ((uint16_t)result.brushes.brushes[i].axialMaterialNum[j/3][j%3]>=result.assets.material_count) goto fail;
    for (i=0;i<result.terrain.aabb_count;++i)
        if (result.terrain.aabbs[i].materialIndex>=result.assets.material_count) goto fail;
    for (i=0;i<result.brushes.node_count;++i) for (j=0;j<2;++j) {
        int child=result.brushes.nodes[i].children[j];
        if (child>=0 ? ((uint32_t)child<=i || (uint32_t)child>=result.brushes.node_count) :
            (uint32_t)(-1-child)>=result.leaves.leaf_count) goto fail;
    }
    if(!CODOL_AppendNativeTriggers(&source->entities,&result)) goto fail;
    m->name=malloc(name_size); m->visibility=malloc(vis_size); m->mapEnts=calloc(1,sizeof(*m->mapEnts));
    if (!m->name || !m->visibility || !m->mapEnts) goto fail;
    m->mapEnts->entityString=malloc(source->entities.text_size);
    if (!m->mapEnts->entityString) goto fail;
    memcpy((void *)m->name,metadata->name,name_size); memcpy(m->visibility,metadata->visibility,vis_size);
    memcpy(m->mapEnts->entityString,source->entities.text,source->entities.text_size);
    m->mapEnts->name=m->name; m->mapEnts->numEntityChars=(int)source->entities.text_size;
    m->checksum=source->checksum; m->numClusters=metadata->cluster_count;
    m->clusterBytes=metadata->cluster_bytes; m->vised=metadata->vised;
    m->planeCount=result.brushes.plane_count; m->planes=result.brushes.planes;
    m->numStaticModels=result.assets.model_count; m->staticModelList=result.assets.models;
    m->numMaterials=result.assets.material_count; m->materials=result.assets.materials;
    m->numBrushSides=result.brushes.side_count; m->brushsides=result.brushes.sides;
    m->numBrushEdges=result.brushes.edge_count; m->brushEdges=result.brushes.edges;
    m->numNodes=result.brushes.node_count; m->nodes=result.brushes.nodes;
    m->numLeafs=result.leaves.leaf_count; m->leafs=result.leaves.leaves;
    m->leafbrushNodesCount=result.brushes.brush_node_count; m->leafbrushNodes=result.brushes.brush_nodes;
    m->numLeafBrushes=result.brushes.index_count; m->leafbrushes=result.brushes.indices;
    m->numLeafSurfaces=result.leaves.surface_count; m->leafsurfaces=result.leaves.surfaces;
    m->vertCount=result.terrain.vertex_count; m->verts=result.terrain.vertices;
    m->triCount=result.terrain.triangle_count; m->triIndices=(uint16_t *)result.terrain.triangles;
    m->triEdgeIsWalkable=(byte *)result.terrain.walkable;
    m->borderCount=result.terrain.border_count; m->borders=result.terrain.borders;
    m->partitionCount=result.terrain.partition_count; m->partitions=result.terrain.partitions;
    m->aabbTreeCount=result.terrain.aabb_count; m->aabbTrees=result.terrain.aabbs;
    m->numSubModels=result.leaves.model_count; m->cmodels=result.leaves.models;
    m->numBrushes=result.brushes.brush_count; m->brushes=result.brushes.brushes;
    m->box_brush=result.brushes.brushes+result.brushes.brush_count; m->box_model=result.brushes.box_model;
    for (i=0;i<2;++i) {
        m->dynEntCount[i]=result.dynamics.count[i]; m->dynEntDefList[i]=result.dynamics.definitions[i];
        m->dynEntPoseList[i]=result.dynamics.poses[i]; m->dynEntClientList[i]=result.dynamics.clients[i];
        m->dynEntCollList[i]=result.dynamics.collisions[i];
    }
    CODOL_FreeNativeClipMap(out); *out=result; return 1;
fail:
    CODOL_FreeNativeClipMap(&result); return 0;
}
