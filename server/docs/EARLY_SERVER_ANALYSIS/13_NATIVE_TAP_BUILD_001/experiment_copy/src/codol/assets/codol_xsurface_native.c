#include "codol_xmodel_native.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
_Static_assert(sizeof(XRigidVertList_t)==12,"native rigid list ABI");
_Static_assert(sizeof(XSurfaceCollisionTree_t)==40,"native tree ABI");
_Static_assert(sizeof(XSurfaceCollisionNode_t)==16,"native tree node ABI");
_Static_assert(sizeof(XSurfaceCollisionLeaf_t)==2,"native tree leaf ABI");
static unsigned u16(const uint8_t *p) { return p[0]|(unsigned)p[1]<<8; }
static uint32_t u32(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
void CODOL_FreeNativeRigidLists(codol_native_rigid_lists_t *out)
{
    unsigned i;
    if (!out) return;
    for (i=0;i<out->count;++i) if (out->lists[i].collisionTree) {
        XSurfaceCollisionTree_t *tree=out->lists[i].collisionTree;
        free(tree->nodes); free(tree->leafs); free(tree);
    }
    free(out->lists); memset(out,0,sizeof(*out));
}
typedef struct { const uint8_t *data; size_t size,p; int retained; } cursor_t;
static const uint8_t *take(cursor_t *c,unsigned count,unsigned stride,unsigned alignment)
{
    const uint8_t *result;
    size_t p=c->p;
    if (c->retained) { if (p>SIZE_MAX-(alignment-1)) return NULL; p=(p+alignment-1)&~(size_t)(alignment-1); }
    if (p>c->size || count>(c->size-p)/stride) return NULL;
    result=c->data+p; c->p=p+(size_t)count*stride; return result;
}
static int pooled(const codol_model_block_t *blocks,uint32_t ref,cursor_t *out)
{
    size_t offset;
    if (!blocks || !ref || ref>=UINT32_MAX-1) return 0;
    --ref; offset=ref&0xfffffff;
    /* This loader allocates all rigid-list/tree records in block 3. */
    if ((ref>>28)!=3 || !blocks[3].data || offset>blocks[3].size || (offset&3)) return 0;
    *out=(cursor_t){blocks[3].data,blocks[3].size,offset,1}; return 1;
}
static int copy_array(cursor_t *c,unsigned count,unsigned stride,unsigned alignment,void **out)
{
    const uint8_t *data=take(c,count,stride,alignment);
    size_t bytes=(size_t)count*stride;
    if (!data) return 0;
    if (bytes) {
        *out=malloc(bytes); if (!*out) return 0;
        memcpy(*out,data,bytes);
    }
    return 1;
}
static int copy_relocated_array(const codol_model_block_t blocks[8],uint32_t ref,
    unsigned count,unsigned stride,void **out)
{
    cursor_t c;
    size_t offset;
    if (!blocks || !ref || ((ref-1)>>28)!=3 || !blocks[3].data) return 0;
    offset=(ref-1)&0xfffffff;
    c=(cursor_t){blocks[3].data,blocks[3].size,offset,0};
    return copy_array(&c,count,stride,1,out);
}
int CODOL_ResolveNativeRigidLists(const codol_surface_t *source,const codol_model_block_t blocks[8],codol_native_rigid_lists_t *out)
{
    codol_native_rigid_lists_t result={0};
    const uint8_t *b;
    cursor_t stream;
    unsigned i,j;
    if (!source || !out) return 0;
    if (!source->rigid_count) { *out=result; return 1; }
    if (source->rigid_reference==UINT32_MAX) {
        if (!source->rigid_stream) return 0;
        stream=(cursor_t){source->rigid_stream,source->rigid_stream_size,0,0};
    } else if (!pooled(blocks,source->rigid_reference,&stream)) return 0;
    b=take(&stream,source->rigid_count,12,4); if (!b) return 0;
    result.lists=calloc(source->rigid_count,sizeof(*result.lists));
    if (!result.lists) return 0;
    result.count=source->rigid_count;
    for (i=0;i<result.count;++i) {
        const uint8_t *h=b+12*i,*raw;
        XRigidVertList_t *list=result.lists+i;
        XSurfaceCollisionTree_t *tree;
        cursor_t external,*tree_stream=&stream;
        uint32_t reference=u32(h+8);
        list->boneOffset=u16(h); list->vertCount=u16(h+2);
        list->triOffset=u16(h+4); list->triCount=u16(h+6);
        if (!reference) continue;
        if (reference!=UINT32_MAX) {
            if (!pooled(blocks,reference,&external)) goto fail;
            tree_stream=&external;
        }
        raw=take(tree_stream,1,40,4); if (!raw) goto fail;
        tree=calloc(1,sizeof(*tree)); if (!tree) goto fail;
        list->collisionTree=tree;
        for (j=0;j<6;++j) {
            uint32_t bits=u32(raw+4*j); float value;
            memcpy(&value,&bits,4);
            /* Native tree construction uses 65535 / axis width. Flat axes
             * therefore legitimately have positive-infinite scales. */
            if (j<3 ? !isfinite(value) : isnan(value) || value<0) goto fail;
            if (j<3) tree->trans[j]=value; else tree->scale[j-3]=value;
        }
        tree->nodeCount=u32(raw+24); tree->leafCount=u32(raw+32);
        if ((!u32(raw+28) && tree->nodeCount) || (!u32(raw+36) && tree->leafCount)) goto fail;
        if (u32(raw+28)) {
            void *nodes=NULL;
            if (source->relocated_tree_arrays ?
                !copy_relocated_array(blocks,u32(raw+28),tree->nodeCount,16,&nodes) :
                !copy_array(tree_stream,tree->nodeCount,16,16,&nodes)) goto fail;
            tree->nodes=nodes;
        }
        if (u32(raw+36)) {
            void *leaves=NULL;
            if (source->relocated_tree_arrays ?
                !copy_relocated_array(blocks,u32(raw+36),tree->leafCount,2,&leaves) :
                !copy_array(tree_stream,tree->leafCount,2,2,&leaves)) goto fail;
            tree->leafs=leaves;
        }
    }
    if (!stream.retained && stream.p!=stream.size) goto fail;
    *out=result; return 1;
fail:
    CODOL_FreeNativeRigidLists(&result); return 0;
}
int CODOL_BuildNativeRigidLists(const codol_surface_t *source,codol_native_rigid_lists_t *out)
{
    return CODOL_ResolveNativeRigidLists(source,NULL,out);
}
void CODOL_FreeNativeSurfaceGeometry(codol_native_surface_geometry_t *out)
{
    if (!out) return;
    CODOL_FreeSurfaceArrays(&out->arrays); CODOL_FreeNativeRigidLists(&out->rigid);
    memset(out,0,sizeof(*out));
}
int CODOL_BuildNativeSurfaceGeometry(const codol_surface_t *source,const codol_model_block_t blocks[8],codol_native_surface_geometry_t *out)
{
    codol_native_surface_geometry_t result={0};
    unsigned i;
    if (!source || !blocks || !out) return 0;
    /* The retained XSurface ABI has four mask words. Never truncate a source
     * surface requiring bones outside that representable range. */
    for (i=4;i<8;++i) if (u32(source->header+52+4*i)) return 0;
    if (!CODOL_ResolveSurfaceArrays(source,blocks,&result.arrays) ||
        !CODOL_ResolveNativeRigidLists(source,blocks,&result.rigid)) {
        CODOL_FreeNativeSurfaceGeometry(&result); return 0;
    }
    memcpy(result.source_header,source->header,sizeof(result.source_header));
    /* C1 0xac6df0 dispatches rigid/skinned paths using byte 1, separately
     * from the graphics-buffer flags in byte 2 (loader 0x4b907b). */
    result.surface.tileMode=(char)source->header[0];
    result.surface.deformed=source->header[1];
    for (i=0;i<4;++i) {
        uint32_t bits=u32(source->header+52+4*i);
        memcpy(result.surface.partBits+i,&bits,4);
    }
    result.surface.vertCount=u16(source->header+4);
    result.surface.triCount=u16(source->header+6);
    for (i=0;i<4;++i) result.surface.vertInfo.vertCount[i]=(short)u16(source->header+20+2*i);
    result.surface.vertInfo.vertsBlend=(unsigned short *)result.arrays.arrays[CODOL_SURFACE_BLEND].data;
    result.surface.verts=(GfxPackedVertex_t *)result.arrays.arrays[CODOL_SURFACE_VERTICES].data;
    result.surface.triIndices=(r_index16_t *)result.arrays.arrays[CODOL_SURFACE_TRIANGLES].data;
    result.surface.vertListCount=result.rigid.count; result.surface.vertList=result.rigid.lists;
    *out=result; return 1;
}
int CODOL_LoadNativeModelSurfaceGeometry(const char *name,unsigned lod,unsigned surface,codol_native_surface_geometry_t *out)
{
    const codol_mounted_model_surfaces_t *mounted;
    int status;
    if (!out) return -1;
    status=CODOL_LoadMountedModelSurfaces(name,lod,&mounted); if (status!=1) return status;
    if (surface>=mounted->source.count) return -1;
    return CODOL_BuildNativeSurfaceGeometry(mounted->source.surfaces+surface,mounted->blocks,out) ? 1 : -1;
}
void CODOL_FreeNativeLodGeometry(codol_native_lod_geometry_t *out)
{
    unsigned i;
    if (!out) return;
    if (out->owners) for (i=0;i<out->count;++i) CODOL_FreeNativeSurfaceGeometry(out->owners+i);
    free(out->owners); free(out->surfaces); memset(out,0,sizeof(*out));
}
int CODOL_BuildNativeLodGeometry(const codol_model_surfaces_t *source,const codol_model_block_t blocks[8],codol_native_lod_geometry_t *out)
{
    codol_native_lod_geometry_t result={0};
    unsigned i,word,triangles=0,vertices=0;
    if (!source || !blocks || !out || source->count>UINT16_MAX || (source->count && !source->surfaces)) return 0;
    result.count=source->count;
    if (result.count) {
        result.surfaces=calloc(result.count,sizeof(*result.surfaces));
        result.owners=calloc(result.count,sizeof(*result.owners));
        if (!result.surfaces || !result.owners) goto fail;
        for (i=0;i<result.count;++i) {
            XSurface *surface=&result.owners[i].surface;
            if (!CODOL_BuildNativeSurfaceGeometry(source->surfaces+i,blocks,result.owners+i)) goto fail;
            /* XModelLoad_670 stores the low 16 bits before adding this surface's
             * counts. These are LOD-local offsets, not serialized C1 pointers. */
            surface->baseTriIndex=(unsigned short)triangles;
            surface->baseVertIndex=(unsigned short)vertices;
            triangles+=surface->triCount; vertices+=surface->vertCount;
            for (word=0;word<4;++word) result.part_bits[word]|=(uint32_t)surface->partBits[word];
            result.surfaces[i]=*surface;
        }
    }
    *out=result; return 1;
fail:
    CODOL_FreeNativeLodGeometry(&result); return 0;
}
int CODOL_LoadNativeModelLodGeometry(const char *name,unsigned lod,codol_native_lod_geometry_t *out)
{
    const codol_mounted_model_surfaces_t *mounted;
    int status;
    if (!out) return -1;
    status=CODOL_LoadMountedModelSurfaces(name,lod,&mounted); if (status!=1) return status;
    return CODOL_BuildNativeLodGeometry(&mounted->source,mounted->blocks,out) ? 1 : -1;
}
void CODOL_FreeNativeModelMesh(codol_native_model_mesh_t *out)
{
    unsigned i;
    if (!out) return;
    for(i=0;i<4;++i) CODOL_FreeNativeLodGeometry(out->owners+i);
    free(out->surfaces); free(out->material_indices); memset(out,0,sizeof(*out));
}
int CODOL_BuildNativeModelMesh(unsigned material_count,const codol_xmodel_lods_t *meta,
    const codol_mounted_model_surfaces_t *const sources[4],codol_native_model_mesh_t *out)
{
    codol_native_model_mesh_t mesh={0}; unsigned i,j,offset=0;
    if (!meta || !sources || !out || material_count>UINT8_MAX ||
        meta->first>meta->count || meta->count>4 || meta->collision_lod < -128 ||
        (meta->collision_lod>=0 && ((unsigned)meta->collision_lod<meta->first ||
          (unsigned)meta->collision_lod>=meta->count))) return 0;
    mesh.lod_count=meta->count-meta->first;
    mesh.collision_lod=meta->collision_lod<0 ? meta->collision_lod : meta->collision_lod-(int)meta->first;
    for(i=meta->first;i<meta->count;++i) {
        const codol_xmodel_lod_t *lod=meta->lods+i;
        if (!isfinite(lod->distance) || lod->distance<0 ||
            (unsigned)lod->surface_index+lod->surface_count>material_count ||
            (lod->surface_count && !sources[i]) ||
            (sources[i] && sources[i]->source.count!=lod->surface_count)) return 0;
        mesh.count+=lod->surface_count;
    }
    if (mesh.count>UINT8_MAX) return 0;
    if (mesh.count) {
        mesh.surfaces=calloc(mesh.count,sizeof(*mesh.surfaces));
        mesh.material_indices=calloc(mesh.count,sizeof(*mesh.material_indices));
        if (!mesh.surfaces || !mesh.material_indices) goto fail;
    }
    for(i=meta->first;i<meta->count;++i) {
        unsigned native=i-meta->first;
        const codol_xmodel_lod_t *from=meta->lods+i;
        XModelLodInfo_t *to=mesh.lods+native;
        codol_native_lod_geometry_t *owner=mesh.owners+native;
        if (sources[i] && !CODOL_BuildNativeLodGeometry(&sources[i]->source,sources[i]->blocks,owner)) goto fail;
        to->dist=from->distance; to->numsurfs=from->surface_count; to->surfIndex=(unsigned short)offset;
        memcpy(to->partBits,owner->part_bits,sizeof(to->partBits));
        for(j=0;j<owner->count;++j) {
            mesh.surfaces[offset+j]=owner->surfaces[j];
            mesh.material_indices[offset+j]=from->surface_index+j;
        }
        offset+=owner->count;
    }
    *out=mesh; return 1;
fail:
    CODOL_FreeNativeModelMesh(&mesh); return 0;
}
int CODOL_LoadNativeModelMesh(const char *name,codol_native_model_mesh_t *out)
{
    const codol_mounted_model_skeleton_t *skeleton;
    const codol_mounted_model_geometry_t *geometry;
    const codol_mounted_model_surfaces_t *sources[4]={0};
    unsigned i; int status;
    if (!out) return -1;
    status=CODOL_LoadMountedXModelSkeleton(name,&skeleton); if(status!=1) return status;
    status=CODOL_LoadMountedXModelGeometry(name,&geometry); if(status!=1) return status;
    for(i=geometry->lods.first;i<geometry->lods.count;++i) {
        if (!geometry->lods.lods[i].surface_count) continue;
        status=CODOL_LoadMountedModelSurfaces(name,i,sources+i); if(status!=1) return -1;
    }
    return CODOL_BuildNativeModelMesh(skeleton->skeleton.surfaces,&geometry->lods,sources,out) ? 1 : -1;
}
