#include "codol_dynents_native.h"
#include <math.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
_Static_assert(sizeof(DynEntityDef)==96,"retained dynamic definition stride");
_Static_assert(offsetof(DynEntityDef,xModel)==32,"dynamic model pointer");
_Static_assert(offsetof(DynEntityDef,destroyPieces)==44,"IW3 pieces insertion");
_Static_assert(offsetof(DynEntityDef,physPreset)==48,"native preset pointer");
_Static_assert(offsetof(DynEntityDef,health)==52,"native health");
_Static_assert(offsetof(DynEntityDef,mass)==56,"native mass");
_Static_assert(offsetof(DynEntityDef,contents)==92,"native contents");
void CODOL_FreeNativeDynamicEntities(codol_native_dynamic_entities_t *out)
{
    unsigned category;
    if(!out) return;
    for(category=0;category<2;++category) {
        free(out->definitions[category]); free(out->poses[category]);
        free(out->clients[category]); free(out->collisions[category]);
    }
    memset(out,0,sizeof(*out));
}
int CODOL_BuildNativeDynamicEntities(const codol_dynamic_entities_t *source,
    const codol_dynamic_binding_t *const bindings[2],codol_native_dynamic_entities_t *out)
{
    codol_native_dynamic_entities_t result={0}; unsigned category,i,j;
    if(!source || !bindings || !out) return 0;
    for(category=0;category<2;++category) {
        uint32_t count=source->count[category];
        if(count>UINT16_MAX || (count && (!source->entities[category] || !bindings[category]))) goto fail;
        result.count[category]=count;
        if(!count) continue;
        result.definitions[category]=calloc(count,sizeof(DynEntityDef));
        /* DynEnt_LoadEntities allocates and clears count*32, count*12 and
         * count*20 bytes. The retained accessors use exactly these strides;
         * CoDOL's runtime block replay uses the same sizes. These are loader
         * defaults, not an activated pose copied from the entity definition. */
        result.poses[category]=calloc(count,32);
        result.clients[category]=calloc(count,12);
        result.collisions[category]=calloc(count,20);
        if(!result.definitions[category] || !result.poses[category] ||
            !result.clients[category] || !result.collisions[category]) goto fail;
        for(i=0;i<count;++i) {
            const codol_dynamic_entity_t *s=source->entities[category]+i;
            const codol_dynamic_binding_t *b=bindings[category]+i;
            DynEntityDef *d=result.definitions[category]+i;
            /* C1 table 0xc3cb84: invalid, clutter, destruct, eight bytes each;
             * flags 0, 0x00010001, 0x01010001 match retained dynEntProps. */
            /* A destroy effect may be missing even when referenced: it is
             * cosmetic server-side and the clipmap builder degrades an effect
             * the native decoder cannot build (codol_sv_xmodel.c). An effect
             * without a reference is still malformed. */
            if((s->type!=1 && s->type!=2) || !!s->model_reference!=!!b->model ||
                (!s->effect_reference && b->effect) || !!s->preset_reference!=!!b->preset) goto fail;
            for(j=0;j<4;++j) if(!isfinite(s->quat[j])) goto fail;
            for(j=0;j<3;++j) if(!isfinite(s->origin[j])) goto fail;
            for(j=0;j<9;++j) if(!isfinite(s->mass[j])) goto fail;
            d->type=s->type; memcpy(d->quat,s->quat,sizeof(d->quat));
            memcpy(d->origin,s->origin,sizeof(d->origin)); d->xModel=b->model;
            d->brushModel=s->brush_model; d->physicsBrushModel=s->physics_brush_model;
            d->destroyFx=b->effect; d->physPreset=b->preset; d->health=s->health;
            memcpy(d->mass,s->mass,sizeof(d->mass)); memcpy(&d->contents,&s->contents,4);
            /* CoDOL has no destroyed-pieces field; calloc leaves it NULL. */
        }
    }
    CODOL_FreeNativeDynamicEntities(out); *out=result; return 1;
fail:
    CODOL_FreeNativeDynamicEntities(&result); return 0;
}
