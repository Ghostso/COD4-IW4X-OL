#include "codol_xmodel.h"
#include "codol_asset_stream.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
static uint32_t u32(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static float f32(const uint8_t *p)
{ uint32_t bits=u32(p); float v; memcpy(&v,&bits,4); return v; }
void CODOL_FreeXModelCollision(codol_xmodel_collision_t *m)
{
    uint32_t i;
    if (!m) return;
    for (i=0;i<m->count;++i) free(m->surfaces[i].triangles);
    free(m->surfaces); memset(m,0,sizeof(*m));
}
int CODOL_ReadXModelCollision(const codol_asset_t *asset,codol_xmodel_collision_t *out)
{
    codol_xmodel_skeleton_t skeleton={0};
    codol_xmodel_collision_t result={0};
    const uint8_t *b;
    size_t p,start;
    unsigned i,j;
    if (!out || !CODOL_ReadXModelSkeleton(asset,&skeleton)) return 0;
    p=skeleton.consumed; CODOL_FreeXModelSkeleton(&skeleton); b=asset->data;
    if (u32(b+0x44)) {
        if (b[6]>(asset->size-p)/4) return 0;
        size_t materials=p;
        p+=4*b[6];
        for (i=0;i<b[6];++i)
            if (u32(b+materials+4*i)>=UINT32_MAX-1 && !CODOL_AdvanceMaterialStream(b,asset->size,&p)) return 0;
    }
    for (i=0;i<4;++i) {
        size_t lod=0x48+0x38*i;
        if (u32(b+lod+8)>=UINT32_MAX-1 && !CODOL_AdvanceModelSurfacesStream(b,asset->size,&p)) return 0;
        if (u32(b+lod+12)==UINT32_MAX) {
            const uint8_t *end=memchr(b+p,0,asset->size-p);
            if (!end) return 0;
            p=(size_t)(end-b)+1;
        }
    }
    result.count=u32(b+0x130);
    if ((!u32(b+0x12c) && result.count) || result.count>(asset->size-p)/44) return 0;
    if (result.count && !(result.surfaces=calloc(result.count,sizeof(*result.surfaces)))) return 0;
    start=p; p+=(size_t)result.count*44;
    for (i=0;i<result.count;++i) {
        const uint8_t *raw=b+start+44*i;
        codol_xmodel_collision_surface_t *s=result.surfaces+i;
        uint32_t bone=u32(raw+32),flags;
        if (bone>=b[4]) goto fail;
        s->boneIdx=bone;
        flags=u32(raw+36); memcpy(&s->contents,&flags,4);
        flags=u32(raw+40); memcpy(&s->surfFlags,&flags,4);
        for (j=0;j<3;++j) {
            float mid=f32(raw+8+4*j),half=f32(raw+20+4*j);
            if (!isfinite(mid)||!isfinite(half)||half<0) goto fail;
            s->mins[j]=mid-half; s->maxs[j]=mid+half;
            if (!isfinite(s->mins[j])||!isfinite(s->maxs[j])) goto fail;
        }
        s->triangle_count=u32(raw+4);
        if ((!u32(raw) && s->triangle_count) || s->triangle_count>(asset->size-p)/48) goto fail;
        if (s->triangle_count) {
            uint32_t k;
            s->triangles=calloc(s->triangle_count,sizeof(*s->triangles));
            if (!s->triangles) goto fail;
            for (k=0;k<s->triangle_count;++k) for (j=0;j<12;++j) {
                float value=f32(b+p+48*k+4*j);
                if (!isfinite(value)) goto fail;
                s->triangles[k][j]=value;
            }
            p+=(size_t)s->triangle_count*48;
        }
    }
    result.consumed=p; *out=result; return 1;
fail:
    CODOL_FreeXModelCollision(&result); return 0;
}
