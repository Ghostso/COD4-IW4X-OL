#include "codol_collision.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
static unsigned u16(const uint8_t *p) { return p[0]|(unsigned)p[1]<<8; }
static uint32_t u32(const uint8_t *p) { return u16(p)|(uint32_t)u16(p+2)<<16; }
static float f32(const uint8_t *p)
{ uint32_t bits=u32(p); float v; memcpy(&v,&bits,4); return v; }
static int bounds(const uint8_t *p,float *mins,float *maxs)
{
    unsigned i;
    for (i=0;i<3;++i) {
        float mid=f32(p+4*i),half=f32(p+12+4*i);
        if (!isfinite(mid)||!isfinite(half)||half<0) return 0;
        mins[i]=mid-half; maxs[i]=mid+half;
        if (!isfinite(mins[i])||!isfinite(maxs[i])) return 0;
    }
    return 1;
}
static int leaf(const uint8_t *p,const codol_collision_layout_t *layout,codol_collision_leaf_t *out)
{
    uint32_t first=u16(p),count=u16(p+2),node=u32(p+36);
    uint32_t aabbs=layout->sections[CODOL_COLL_AABBS].count;
    uint32_t nodes=layout->sections[CODOL_COLL_LEAF_BRUSH_NODES].count,flags;
    if (first>aabbs || count>aabbs-first || (nodes ? node>=nodes : node!=0)) return 0;
    out->firstCollAabbIndex=first; out->collAabbCount=count; out->leafBrushNode=node;
    flags=u32(p+4); memcpy(&out->brushContents,&flags,4);
    flags=u32(p+8); memcpy(&out->terrainContents,&flags,4);
    out->cluster=-1;
    return bounds(p+12,out->mins,out->maxs);
}
void CODOL_FreeCollisionLeaves(codol_collision_leaves_t *out)
{
    if (!out) return;
    free(out->leaves); free(out->submodels); free(out->surfaces); memset(out,0,sizeof(*out));
}
int CODOL_ReadCollisionLeaves(const codol_asset_t *asset,codol_collision_leaves_t *out)
{
    codol_collision_layout_t layout;
    codol_collision_leaves_t result={0};
    uint32_t i;
    if (!out || !CODOL_ReadCollisionLayout(asset,&layout)) return 0;
    result.leaf_count=layout.sections[CODOL_COLL_LEAVES].count;
    result.submodel_count=layout.sections[CODOL_COLL_SUBMODELS].count;
    result.surface_count=layout.sections[CODOL_COLL_LEAF_SURFACES].count;
    if (result.surface_count) {
        result.surfaces=calloc(result.surface_count,sizeof(*result.surfaces));
        if (!result.surfaces) goto fail;
        for (i=0;i<result.surface_count;++i)
            result.surfaces[i]=u32(asset->data+layout.sections[CODOL_COLL_LEAF_SURFACES].offset+4*i);
    }
    if (result.leaf_count) {
        result.leaves=calloc(result.leaf_count,sizeof(*result.leaves));
        if (!result.leaves) goto fail;
    }
    if (result.submodel_count) {
        result.submodels=calloc(result.submodel_count,sizeof(*result.submodels));
        if (!result.submodels) goto fail;
    }
    for (i=0;i<result.leaf_count;++i)
        if (!leaf(asset->data+layout.sections[CODOL_COLL_LEAVES].offset+40*i,&layout,result.leaves+i)) goto fail;
    for (i=0;i<result.submodel_count;++i) {
        const uint8_t *p=asset->data+layout.sections[CODOL_COLL_SUBMODELS].offset+68*i;
        codol_collision_submodel_t *m=result.submodels+i;
        m->radius=f32(p+24);
        if (!isfinite(m->radius)||m->radius<0 || !bounds(p,m->mins,m->maxs) || !leaf(p+28,&layout,&m->leaf)) goto fail;
    }
    CODOL_FreeCollisionLeaves(out); *out=result; return 1;
fail:
    CODOL_FreeCollisionLeaves(&result); return 0;
}
