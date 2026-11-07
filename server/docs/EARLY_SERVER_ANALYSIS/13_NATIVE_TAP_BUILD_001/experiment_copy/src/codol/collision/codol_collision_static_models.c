#include "codol_collision.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
static uint32_t u32(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static float f32(const uint8_t *p)
{ uint32_t bits=u32(p); float v; memcpy(&v,&bits,4); return v; }
void CODOL_FreeCollisionStaticModels(codol_collision_static_models_t *out)
{
    if (!out) return;
    free(out->models); free(out->model_references); memset(out,0,sizeof(*out));
}
int CODOL_ReadCollisionStaticModels(const codol_asset_t *asset,codol_collision_model_resolver_t resolver,
                                    void *context,codol_collision_static_models_t *out)
{
    codol_collision_layout_t layout;
    codol_collision_static_models_t result={0};
    uint32_t i,j;
    if (!out || !CODOL_ReadCollisionLayout(asset,&layout)) return 0;
    result.count=layout.sections[CODOL_COLL_STATIC_MODELS].count;
    if (result.count) {
        result.models=calloc(result.count,sizeof(*result.models));
        result.model_references=calloc(result.count,sizeof(*result.model_references));
        if (!result.models || !result.model_references) goto fail;
    }
    for (i=0;i<result.count;++i) {
        const uint8_t *p=asset->data+layout.sections[CODOL_COLL_STATIC_MODELS].offset+76*i;
        codol_collision_static_model_t *m=result.models+i;
        uint32_t ref=u32(p);
        if (!ref || ref>=UINT32_MAX-1) goto fail;
        for (j=0;j<3;++j) {
            float mid=f32(p+52+4*j),half=f32(p+64+4*j);
            m->origin[j]=f32(p+4+4*j);
            if (!isfinite(m->origin[j]) || !isfinite(mid) || !isfinite(half) || half<0) goto fail;
            m->absmin[j]=mid-half; m->absmax[j]=mid+half;
            if (!isfinite(m->absmin[j]) || !isfinite(m->absmax[j])) goto fail;
        }
        for (j=0;j<9;++j) {
            float value=f32(p+16+4*j);
            if (!isfinite(value)) goto fail;
            m->invScaledAxis[j/3][j%3]=value;
        }
        if (resolver) m->xmodel=resolver(context,ref);
        if (!m->xmodel) { result.model_references[i]=ref; ++result.unresolved; }
    }
    *out=result; return 1;
fail:
    CODOL_FreeCollisionStaticModels(&result); return 0;
}
