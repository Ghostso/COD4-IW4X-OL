/* Convert prepared CoDOL skeletal/collision data into the retained IW3 ABI. */
#include "codol_xmodel_native.h"
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <math.h>

_Static_assert(sizeof(XModel)==220,"native XModel ABI");
_Static_assert(offsetof(XModel,lodRampType)==7,"native LOD ramp type");
_Static_assert(sizeof(XSurface)==56,"native surface stride");
_Static_assert(offsetof(XSurface,baseTriIndex)==8,"native triangle base");
_Static_assert(offsetof(XSurface,baseVertIndex)==10,"native vertex base");
_Static_assert(offsetof(XSurface,triIndices)==12,"native triangle pointer");
_Static_assert(offsetof(XSurface,vertInfo)==16,"native blend information");
_Static_assert(offsetof(XSurface,verts)==28,"native vertex pointer");
_Static_assert(offsetof(XSurface,vertListCount)==32,"native rigid list count");
_Static_assert(offsetof(XSurface,vertList)==36,"native rigid list pointer");
_Static_assert(offsetof(XSurface,partBits)==40,"native surface part bits");
_Static_assert(sizeof(GfxPackedVertex_t)==32,"native packed vertex stride");
_Static_assert(offsetof(GfxPackedVertex_t,texCoord)==20,"native vertex texture coordinates");
_Static_assert(offsetof(GfxPackedVertex_t,normal)==24,"native vertex normal");
_Static_assert(sizeof(XModelLodInfo_t)==28,"native LOD stride");
_Static_assert(offsetof(XModel,lodInfo)==40,"native LOD array offset");
_Static_assert(offsetof(XModelLodInfo_t,smodelCacheIndexPlusOne)==25,"native LOD cache index");
_Static_assert(offsetof(XModelLodInfo_t,smodelCacheVertCountExponent)==26,"native LOD cache vertex exponent");
_Static_assert(offsetof(XModel,boneNames)==8,"native bone handles offset");
_Static_assert(offsetof(XModel,baseMat)==28,"native base matrix offset");
_Static_assert(offsetof(XModel,collSurfs)==152,"native collision offset");
_Static_assert(offsetof(XModel,boneInfo)==164,"native bone bounds offset");
_Static_assert(offsetof(XModel,mins)==172,"native bounds offset");
_Static_assert(offsetof(XModel,flags)==208,"native model flags");
_Static_assert(sizeof(DObjAnimMat)==32,"native bone matrix size");
_Static_assert(sizeof(XModelCollSurf_t)==44,"native collision surface size");
_Static_assert(offsetof(XModelCollSurf_t,collTris)==0,"native collision triangles");
_Static_assert(offsetof(XModelCollSurf_t,numCollTris)==4,"native collision triangle count");
_Static_assert(offsetof(XModelCollSurf_t,mins)==8,"native collision bounds");
_Static_assert(offsetof(XModelCollSurf_t,boneIdx)==32,"native collision bone");
_Static_assert(offsetof(XModelCollSurf_t,contents)==36,"native collision contents");
_Static_assert(offsetof(XModelCollSurf_t,surfFlags)==40,"native collision flags");
_Static_assert(sizeof(XBoneInfo_t)==sizeof(codol_xmodel_bone_info_t),"native bone info size");

void CODOL_FreeNativeModelCore(codol_native_model_core_t *core)
{
    if (!core) return;
    free(core->model.collSurfs); free(core->model.materialHandles); memset(core,0,sizeof(*core));
}
int CODOL_BuildNativeModelCore(const codol_mounted_model_skeleton_t *source,
    const codol_mounted_model_geometry_t *geometry,const uint16_t *handles,unsigned count,
    codol_native_model_core_t *out)
{
    static const unsigned strides[6]={2,1,8,12,1,32};
    codol_native_model_core_t core={0};
    const codol_xmodel_skeleton_t *s;
    unsigned i;
    if (!source || !geometry || !out) return 0;
    s=&source->skeleton;
    if (!s->name || s->unresolved || s->bones>=DOBJ_MAX_PARTS || s->roots>s->bones ||
        count!=s->bones || (count && !handles) || geometry->bounds.bone_count!=count || geometry->bounds.flags>UINT8_MAX ||
        geometry->collision.count>INT_MAX || (geometry->collision.count && !geometry->collision.surfaces)) return 0;
    for (i=0;i<count;++i) if (!handles[i]) return 0;
    for (i=0;i<6;++i) {
        const codol_model_array_t *a=s->arrays+i;
        unsigned expected=i>=1 && i<=3 ? s->bones-s->roots : s->bones;
        if (a->count!=expected || a->stride!=strides[i] ||
            (expected && (!a->data || ((uintptr_t)a->data&15)))) return 0;
    }
    core.model.name=s->name;
    core.model.numBones=(char)s->bones; core.model.numRootBones=(char)s->roots;
    core.model.boneNames=(xScriptString_t *)handles;
    core.model.parentList=(char *)s->arrays[CODOL_MODEL_PARENTS].data;
    core.model.quats=(short *)s->arrays[CODOL_MODEL_QUATS].data;
    core.model.trans=(float *)s->arrays[CODOL_MODEL_TRANSLATIONS].data;
    core.model.partClassification=(char *)s->arrays[CODOL_MODEL_CLASSIFICATION].data;
    core.model.baseMat=(DObjAnimMat *)s->arrays[CODOL_MODEL_BASE_MATS].data;
    core.model.boneInfo=(XBoneInfo_t *)geometry->bounds.bones;
    core.model.radius=geometry->bounds.radius;
    core.model.collLod=(short)geometry->lods.collision_lod;
    memcpy(&core.model.contents,&geometry->bounds.contents,sizeof(core.model.contents));
    { uint8_t flags=(uint8_t)geometry->bounds.flags; memcpy(&core.model.flags,&flags,1); }
    memcpy(core.model.mins,geometry->bounds.mins,sizeof(core.model.mins));
    memcpy(core.model.maxs,geometry->bounds.maxs,sizeof(core.model.maxs));
    core.physics_preset_reference=geometry->bounds.physics_preset_reference;
    core.physics_map_reference=geometry->bounds.physics_map_reference;
    if (geometry->collision.count) {
        if (!(core.model.collSurfs=calloc(geometry->collision.count,sizeof(*core.model.collSurfs)))) return 0;
        for (i=0;i<geometry->collision.count;++i) {
            const codol_xmodel_collision_surface_t *from=geometry->collision.surfaces+i;
            XModelCollSurf_t *to=core.model.collSurfs+i;
            if (from->boneIdx<0 || (unsigned)from->boneIdx>=count || from->triangle_count>INT_MAX ||
                (from->triangle_count && !from->triangles)) { CODOL_FreeNativeModelCore(&core); return 0; }
            to->collTris=from->triangles; to->numCollTris=(int)from->triangle_count;
            memcpy(to->mins,from->mins,sizeof(to->mins)); memcpy(to->maxs,from->maxs,sizeof(to->maxs));
            to->boneIdx=from->boneIdx; to->contents=from->contents; to->surfFlags=from->surfFlags;
        }
    }
    core.model.numCollSurfs=geometry->collision.count;
    *out=core; return 1;
}
int CODOL_BindNativeModelMesh(codol_native_model_core_t *core,const codol_native_model_mesh_t *mesh,
    xMaterial_t *const *materials,unsigned material_count)
{
    xMaterial_t **bound=NULL; unsigned i,end=0;
    int ramp=XMODEL_LOD_RAMP_RIGID;
    if (!core || !core->model.name || !mesh || mesh->count>UINT8_MAX || mesh->lod_count>4 ||
        mesh->collision_lod<SHRT_MIN || (mesh->collision_lod>=0 &&
          (unsigned)mesh->collision_lod>=mesh->lod_count) ||
        (mesh->count && (!mesh->surfaces || !mesh->material_indices || !materials))) return 0;
    for(i=0;i<mesh->lod_count;++i) {
        const XModelLodInfo_t *lod=mesh->lods+i;
        if (!isfinite(lod->dist) || lod->dist<0 || lod->surfIndex!=end ||
            lod->numsurfs>mesh->count-end) return 0;
        end+=lod->numsurfs;
    }
    if(end!=mesh->count) return 0;
    for(i=0;i<mesh->count;++i) {
        if(mesh->material_indices[i]>=material_count || !materials[mesh->material_indices[i]]) return 0;
        /* Retained XModelLoad_230 sets byte 7 when any surface byte 1 is nonzero. */
        if(mesh->surfaces[i].deformed) ramp=XMODEL_LOD_RAMP_SKINNED;
    }
    if(mesh->count) {
        bound=malloc(mesh->count*sizeof(*bound)); if(!bound) return 0;
        for(i=0;i<mesh->count;++i) bound[i]=materials[mesh->material_indices[i]];
    }
    free(core->model.materialHandles);
    core->model.materialHandles=bound; core->model.surfs=mesh->surfaces;
    core->model.numsurfs=(char)mesh->count; core->model.numLods=(short)mesh->lod_count;
    core->model.collLod=(short)mesh->collision_lod;
    core->model.lodRampType=(char)ramp;
    memcpy(core->model.lodInfo,mesh->lods,sizeof(core->model.lodInfo));
    return 1;
}
