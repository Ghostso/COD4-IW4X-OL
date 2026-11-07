#include "codol_effects_native.h"
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
_Static_assert(sizeof(FxEffectDef)==32,"native FX header");
#ifdef CODOL_SERVER
_Static_assert(sizeof(struct FxElemDef)==260,"native C1 FX element");
_Static_assert(offsetof(struct FxElemDef,spawnSound)==256,"native C1 FX spawn sound");
#else
_Static_assert(sizeof(struct FxElemDef)==252,"native IW3 FX element");
#endif
_Static_assert(offsetof(struct FxElemDef,elemType)==176,"native FX type");
_Static_assert(offsetof(struct FxElemDef,velSamples)==180,"native FX samples");
_Static_assert(offsetof(struct FxElemDef,visuals)==188,"native FX visuals");
_Static_assert(offsetof(struct FxElemDef,effectRefs)==216,"native FX effect refs");
_Static_assert(offsetof(struct FxElemDef,trailDef)==244,"native FX trail");
#ifdef CODOL_SERVER
/* The owned trail record is C1's own 36-byte layout with 32-bit pointers. */
_Static_assert(sizeof(void *)==4,"native FX trail pointers");
#endif
typedef struct { uint8_t *data; size_t pos; } packing_t;
/* Why the last CODOL_BuildNativeEffect refused its source: which element, of
 * which source type, and at which check. Diagnostic only. */
static char build_failure[160];
const char *CODOL_NativeEffectBuildFailure(void) { return build_failure; }
#define PACK_FAIL(what) do { \
    snprintf(build_failure,sizeof(build_failure),"element %u type %u: %s", \
        i,(unsigned)(r ? r[176] : 255u),what); \
    return 0; } while(0)
static uint32_t u32(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static int part(packing_t *p,const void *data,size_t size,unsigned alignment,void **out)
{
    size_t at=(p->pos+alignment-1)&~(size_t)(alignment-1);
    if(at>CODOL_ASSET_LIMIT || size>CODOL_ASSET_LIMIT-at) return 0;
    *out=p->data ? p->data+at : NULL;
    if(p->data && data && size) memcpy(*out,data,size);
    p->pos=at+size; return 1;
}
static int pack(const codol_effect_source_t *source,const codol_effect_bindings_t *bindings,packing_t *p)
{
    struct FxElemDef *elements; void *memory,*name; unsigned i,j; FxEffectDef *fx=(FxEffectDef *)p->data;
    p->pos=sizeof(FxEffectDef);
    if(!part(p,source->prefix.name,strlen(source->prefix.name)+1,1,&name) ||
        !part(p,NULL,(size_t)source->prefix.count*sizeof(*elements),4,&memory)) return 0;
    elements=memory;
    for(i=0;i<source->prefix.count;++i) {
        const codol_effect_element_t *s=source->elements+i; const codol_effect_bindings_t *b=bindings+i;
        const uint8_t *r=s->record; struct FxElemDef *d=fx ? elements+i : NULL;
        unsigned type,n; void *velocity,*visual_samples,*visual_array=NULL,*spawn_sound=NULL,*extension=NULL;
        if(!r) PACK_FAIL("no record");
        type=r[176];
        /* Decals always use an array of material pairs, including one mark.
         * Retained Load_FxElemDefVisuals: native type 9, stride 8, two handles. */
        n=type==13 ? (u32(r+188) ? 2*(unsigned)r[177] : 0) : (r[177]>1 ? r[177] : 1);
#ifdef CODOL_SERVER
        /* Every C1 element type the zone loader knows (0..14). The server
         * keeps each element's C1 identity and never draws it, so the only
         * type-specific work is ownership of what the loader reads: the
         * visuals (below) and the +244 extension. C1 Load_FxElemDef extension
         * switch 0x4bd230: type 5 is a 36-byte trail with 20-byte vertices
         * and u16 indices (0x4bd0e0), type 8 a 52-byte spark fountain
         * (0x4bd1f0), any other type one byte (0x4b6c20). */
        if(type>14) PACK_FAIL("unsupported element type");
        if(!!u32(r+244)!=!!s->extension || (s->extension && !s->extension_size))
            PACK_FAIL("extension mismatch");
        if(s->extension && s->extension_size!=(type==5 ? 36u : type==8 ? 52u : 1u))
            PACK_FAIL("extension size mismatch");
#else
        if(type!=0 && type!=1 && type!=3 && type!=4 && type!=6 && type!=9 && type!=10 && type!=12 && type!=13 && type!=14)
            PACK_FAIL("unsupported element type");
        if(u32(r+244) || s->extension_size || s->extension) PACK_FAIL("trail/extension present");
#endif
        if(s->visual_count!=n || (n && !s->visuals)) PACK_FAIL("visual count mismatch");
#ifdef CODOL_SERVER
        if(!!u32(r+256)!=!!s->extra_name) PACK_FAIL("spawn sound mismatch");
        if(s->extra_name && !part(p,s->extra_name,strlen(s->extra_name)+1,1,&spawn_sound)) return 0;
#else
        if(type==4 || u32(r+252) || u32(r+256) || s->extra_name) return 0;
#endif
        if(type!=13 && (n>1 ? !u32(r+188) : s->visuals[0].reference!=u32(r+188))) PACK_FAIL("visual reference mismatch");
        if(s->velocity_count!=(u32(r+180) ? (unsigned)r[178]+1 : 0) ||
            s->visual_sample_count!=(u32(r+184) ? (unsigned)r[179]+1 : 0) ||
            (s->velocity_count && !s->velocity_samples) || (s->visual_sample_count && !s->visual_samples)) PACK_FAIL("sample count mismatch");
        if(type==12 ? (b->visual_count || b->visuals) : (b->visual_count!=n || (n && !b->visuals))) PACK_FAIL("binding count mismatch");
        if(!part(p,s->velocity_samples,(size_t)s->velocity_count*96,4,&velocity) ||
            !part(p,s->visual_samples,(size_t)s->visual_sample_count*48,4,&visual_samples)) return 0;
        if(n>1 && !part(p,NULL,(size_t)n*4,4,&visual_array)) return 0;
#ifdef CODOL_SERVER
        if(s->extension) {
            if(!part(p,s->extension,s->extension_size,4,&extension)) return 0;
            if(type==5) {
                /* The trail record keeps C1's layout: +0x14 vertex count,
                 * +0x18 vertices, +0x1c index count, +0x20 indices. Its two
                 * pointers are rebound to owned copies of the arrays. */
                void *vertices=NULL,*indices=NULL;
                if((s->trail_vertex_count && !s->trail_vertices) || (s->trail_index_count && !s->trail_indices))
                    PACK_FAIL("trail arrays missing");
                if(s->trail_vertices && !part(p,s->trail_vertices,(size_t)s->trail_vertex_count*20,4,&vertices)) return 0;
                if(s->trail_indices && !part(p,s->trail_indices,(size_t)s->trail_index_count*2,2,&indices)) return 0;
                if(d) {
                    memcpy((uint8_t *)extension+0x18,&vertices,4);
                    memcpy((uint8_t *)extension+0x20,&indices,4);
                }
            }
        }
#endif
        for(j=0;j<n;++j) {
            const codol_effect_visual_t *v=s->visuals+j; void *value=NULL;
            if(type==12) {
                if(!!v->reference!=!!v->string) return 0;
                if(v->string && !part(p,v->string,strlen(v->string)+1,1,&value)) return 0;
            } else {
                /* Light visuals carry no asset; runner names bind native FX,
                 * not strings. C1 0x4bcf60 / IW3 Load_FxElemVisuals. */
                if((type==10 || type==11) && (v->reference || b->visuals[j])) PACK_FAIL("light visual carries an asset");
                if(type==14 && !!v->reference!=!!v->string) PACK_FAIL("runner name mismatch");
                if(!!v->reference!=!!b->visuals[j]) PACK_FAIL("visual not bound");
                value=(void *)b->visuals[j];
            }
            if(d) { if(n>1) ((void **)visual_array)[j]=value; else d->visuals=value; }
        }
        for(j=0;j<3;++j) if(!!u32(r+216+4*j)!=!!s->effect_names[j] || !!s->effect_names[j]!=!!b->effects[j]) PACK_FAIL("effect reference not bound");
        if(d) {
            memcpy(d->parameters,r,176);
#ifdef CODOL_SERVER
            /* Preserve C1 identity, including type4 line. C1 c3cb54[4]
             * dispatches4e4d80 (velocity-directed line drawing). +256 is a
             * spawn sound consumed at4ff3b7/502602 through4ff850, not an FX
             * asset reference. Client-owned FX playback uses this same
             * original definition identity published by the server. */
            d->elemType=(uint8_t)type;
            d->trailDef=extension;
            memcpy(d->codolParameters,r+252,4);
            d->spawnSound=spawn_sound;
#else
            /* C1 draw table c3cb54[3] -> 4e6020 matches retained
             * FX_DrawElem_Tail: velocity normalization, backward center
             * shift, camera/velocity cross products, sprite generation.
             * IW3 s_drawElemHandler assigns this routine type 2. */
            /* C1 table slot 1 -> 4e5db0 supplies the element's own axes to
             * sprite generation, matching IW3 FX_DrawElem_OrientedSprite. */
            /* C1 slot 6 -> 4e4500 -> 4e44a0 allocates a particle cloud;
             * 4e4210 evaluates/normalizes velocity, sets cloud dimensions,
             * position and flags. Retained FX_DrawElem_Cloud is type 4. */
            d->elemType=type==1 ? 1 : type==3 ? 2 : type==6 ? 4 : type==9 ? 5 : type==10 ? 6 : type==12 ? 8 : type==13 ? 9 : type==14 ? 10 : 0;
#endif
            d->visualCount=r[177]; d->velIntervalCount=r[178]; d->visIntervalCount=r[179];
            d->velSamples=s->velocity_count ? velocity : NULL; d->visSamples=s->visual_sample_count ? visual_samples : NULL;
            if(n>1) d->visuals=visual_array;
            memcpy(d->collisionBounds,r+192,24); memcpy(d->effectRefs,b->effects,sizeof(d->effectRefs));
            memcpy(d->emissionParameters,r+228,16); memcpy(d->lighting,r+248,4);
        }
    }
    if(p->pos>INT32_MAX) return 0;
    if(fx) {
        fx->name=name; memcpy(&fx->flags,&source->prefix.flags,4); fx->totalSize=(int)p->pos;
        fx->msecLoopingLife=source->prefix.looping_life; fx->elemDefCountLooping=source->prefix.counts[0];
        fx->elemDefCountOneShot=source->prefix.counts[1]; fx->elemDefCountEmission=source->prefix.counts[2];
        fx->elemDefs=source->prefix.count ? elements : NULL;
    }
    return 1;
}
void CODOL_FreeNativeEffect(codol_native_effect_t *out)
{ if(out) { free(out->storage); memset(out,0,sizeof(*out)); } }
int CODOL_BuildNativeEffect(const codol_effect_source_t *source,const codol_effect_bindings_t *bindings,codol_native_effect_t *out)
{
    packing_t p={0}; codol_native_effect_t result={0}; uint64_t count;
    if(!source || !out || !source->prefix.name || !*source->prefix.name || *source->prefix.name==',' ||
        (source->prefix.count && (!source->elements || !bindings))) return 0;
    count=(uint64_t)source->prefix.counts[0]+source->prefix.counts[1]+source->prefix.counts[2];
    if(count!=source->prefix.count || count>CODOL_ASSET_LIMIT/sizeof(struct FxElemDef) || !pack(source,bindings,&p)) return 0;
    result.size=p.pos; result.storage=calloc(1,result.size); if(!result.storage) return 0;
    p.data=result.storage;
    if(!pack(source,bindings,&p) || p.pos!=result.size) { free(result.storage); return 0; }
    result.effect=result.storage; result.source_total_size=source->prefix.total_size;
    CODOL_FreeNativeEffect(out); *out=result; return 1;
}
