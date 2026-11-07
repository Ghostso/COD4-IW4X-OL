#include "codol_effects.h"
#include "codol_asset_stream.h"
#include <stdlib.h>
#include <string.h>
static uint32_t u32(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
int CODOL_ReadEffectPrefix(const codol_asset_t *asset,const codol_model_block_t blocks[8],codol_effect_prefix_t *out)
{
    codol_effect_prefix_t result={0}; const uint8_t *end,*name; size_t pos=32,available;
    uint32_t ref,life; uint64_t count=0; unsigned i;
    if(!asset || !out || asset->type!=30 || !asset->data || asset->size<32 || asset->size>CODOL_ASSET_LIMIT) return 0;
    ref=u32(asset->data);
    if(ref==UINT32_MAX) { name=asset->data+32; available=asset->size-32; }
    else {
        size_t offset;
        if(!blocks || !ref || ((ref-1)>>28)!=3) return 0;
        offset=(ref-1)&0xfffffff;
        if(!blocks[3].data || blocks[3].size>CODOL_ASSET_LIMIT || offset>=blocks[3].size) return 0;
        name=blocks[3].data+offset; available=blocks[3].size-offset;
    }
    if(!(end=memchr(name,0,available)) || end==name || *name==',') return 0;
    if(ref==UINT32_MAX) pos+=(size_t)(end-name)+1;
    result.name=(const char *)name; result.flags=u32(asset->data+4); result.total_size=u32(asset->data+8);
    life=u32(asset->data+12); memcpy(&result.looping_life,&life,4);
    for(i=0;i<3;++i) {
        result.counts[i]=u32(asset->data+16+4*i);
        if(result.counts[i]>INT32_MAX) return 0;
        count+=result.counts[i];
    }
    if(count>INT32_MAX || count>(asset->size-pos)/260 || (count && !u32(asset->data+28))) return 0;
    result.count=(uint32_t)count; result.elements=count ? asset->data+pos : NULL;
    result.dependency_offset=pos+(size_t)count*260; *out=result; return 1;
}
static int take(const codol_asset_t *asset,size_t *pos,uint32_t count,unsigned stride,const uint8_t **out)
{
    if(*pos>asset->size || count>(asset->size-*pos)/stride) return 0;
    *out=count ? asset->data+*pos : NULL; *pos+=(size_t)count*stride; return 1;
}
static int string_ref(const codol_asset_t *asset,const codol_model_block_t blocks[8],size_t *pos,uint32_t ref,const char **out)
{
    const uint8_t *p,*end; size_t size;
    if(!ref) { *out=NULL; return 1; }
    if(ref==UINT32_MAX) { p=asset->data+*pos; size=asset->size-*pos; }
    else {
        size_t offset;
        if(!blocks || ((ref-1)>>28)!=3) return 0;
        offset=(ref-1)&0xfffffff;
        if(!blocks[3].data || offset>=blocks[3].size || blocks[3].size>CODOL_ASSET_LIMIT) return 0;
        p=blocks[3].data+offset; size=blocks[3].size-offset;
    }
    if(!(end=memchr(p,0,size))) return 0;
    *out=(const char *)p; if(ref==UINT32_MAX) *pos+=(size_t)(end-p)+1; return 1;
}
static int visual(const codol_asset_t *asset,const codol_model_block_t blocks[8],size_t *pos,
    unsigned type,uint32_t ref,codol_effect_visual_t *out)
{
    size_t start=*pos,extent=0; out->reference=ref;
    if(type==12 || type==14) return string_ref(asset,blocks,pos,ref,&out->string);
    if(type==10 || type==11 || ref<UINT32_MAX-1) return 1;
    if(type==9) {
        codol_asset_t model={4,asset->data+start,asset->size-start};
        if(!CODOL_ReadXModelExtent(&model,&extent)) return 0;
        *pos+=extent;
    } else if(!CODOL_AdvanceMaterialStream(asset->data,asset->size,pos)) return 0;
    out->inline_asset=(codol_asset_t){type==9 ? 4 : 5,asset->data+start,*pos-start}; return 1;
}
void CODOL_FreeEffectSource(codol_effect_source_t *out)
{
    unsigned i;
    if(!out) return;
    if(out->elements) for(i=0;i<out->prefix.count;++i) free(out->elements[i].visuals);
    free(out->elements); memset(out,0,sizeof(*out));
}
int CODOL_ReadEffectSource(const codol_asset_t *asset,const codol_model_block_t blocks[8],codol_effect_source_t *out)
{
    codol_effect_source_t result={0}; size_t pos; unsigned i,j;
    if(!out || !CODOL_ReadEffectPrefix(asset,blocks,&result.prefix)) return 0;
    pos=result.prefix.dependency_offset;
    if(result.prefix.count && !(result.elements=calloc(result.prefix.count,sizeof(*result.elements)))) return 0;
    for(i=0;i<result.prefix.count;++i) {
        codol_effect_element_t *e=result.elements+i;
        const uint8_t *r=result.prefix.elements+260*i,*refs=NULL; unsigned type=r[176],n=r[177];
        e->record=r;
        if(u32(r+180)) {
            e->velocity_count=(unsigned)r[178]+1;
            if(!take(asset,&pos,e->velocity_count,96,&e->velocity_samples)) goto fail;
        }
        if(u32(r+184)) {
            e->visual_sample_count=(unsigned)r[179]+1;
            if(!take(asset,&pos,e->visual_sample_count,48,&e->visual_samples)) goto fail;
        }
        if(type==13) {
            if(u32(r+188)) {
                e->visual_count=2*n;
                if(!take(asset,&pos,e->visual_count,4,&refs)) goto fail;
            }
        } else if(n<=1) { e->visual_count=1; refs=r+188; }
        else if(u32(r+188)) {
            e->visual_count=n;
            if(!take(asset,&pos,n,4,&refs)) goto fail;
        }
        if(e->visual_count && !(e->visuals=calloc(e->visual_count,sizeof(*e->visuals)))) goto fail;
        for(j=0;j<e->visual_count;++j)
            if(!visual(asset,blocks,&pos,type,u32(refs+4*j),e->visuals+j)) goto fail;
        for(j=0;j<3;++j) if(!string_ref(asset,blocks,&pos,u32(r+216+4*j),e->effect_names+j)) goto fail;
        if(u32(r+244)) {
            e->extension_size=type==5 ? 36 : type==8 ? 52 : 1;
            if(!take(asset,&pos,1,e->extension_size,&e->extension)) goto fail;
            if(type==5) {
                e->trail_vertex_count=u32(e->extension+20); e->trail_index_count=u32(e->extension+28);
                if(u32(e->extension+24) && !take(asset,&pos,e->trail_vertex_count,20,&e->trail_vertices)) goto fail;
                if(u32(e->extension+32) && !take(asset,&pos,e->trail_index_count,2,&e->trail_indices)) goto fail;
            }
        }
        if(!string_ref(asset,blocks,&pos,u32(r+256),&e->extra_name)) goto fail;
    }
    if(pos!=asset->size) goto fail;
    CODOL_FreeEffectSource(out); *out=result; return 1;
fail:
    CODOL_FreeEffectSource(&result); return 0;
}
