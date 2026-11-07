/* C1 XModel loader 0x4bbb80: header 0x168, skeleton fields 0x2c..0x40.
 * Its quaternion loader consumes four shorts per non-root bone. */
#include "codol_xmodel.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
static uint32_t u32(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static void put32(uint8_t *p,uint32_t value)
{ unsigned i; for (i=0;i<4;++i) p[i]=(uint8_t)(value>>(8*i)); }
static const uint8_t *block_pointer(const codol_model_block_t blocks[8],uint32_t reference,size_t length,size_t *available)
{
    unsigned block;
    size_t offset;
    if (!reference || reference>=UINT32_MAX-1) return NULL;
    --reference; block=reference>>28; offset=reference&0xfffffff;
    if (block>=8 || !blocks[block].data || blocks[block].size>CODOL_ASSET_LIMIT ||
        offset>blocks[block].size || length>blocks[block].size-offset) return NULL;
    if (available) *available=blocks[block].size-offset;
    return blocks[block].data+offset;
}
void CODOL_FreeXModelSkeleton(codol_xmodel_skeleton_t *m)
{
    if (!m) return;
    free(m->storage); memset(m,0,sizeof(*m));
}
int CODOL_ReadXModelSkeleton(const codol_asset_t *asset,codol_xmodel_skeleton_t *out)
{
    static const unsigned strides[6]={2,1,8,12,1,32};
    codol_xmodel_skeleton_t m={0};
    size_t p=0x168,offsets[6]={0},name_offset=0,name_length=0,owned_size=15;
    unsigned i,j;
    const uint8_t *b;
    if (!asset || !out || asset->type!=4 || !asset->data || asset->size<p || asset->size>CODOL_ASSET_LIMIT) return 0;
    b=asset->data; m.name_reference=u32(b); m.bones=b[4]; m.roots=b[5]; m.surfaces=b[6];
    if (m.roots>m.bones) return 0;
    if (m.name_reference==UINT32_MAX) {
        const uint8_t *end=memchr(b+p,0,asset->size-p);
        if (!end) return 0;
        name_offset=p; p=(size_t)(end-b)+1; name_length=p-name_offset;
    } else if (m.name_reference) ++m.unresolved;
    for (i=0;i<6;++i) {
        codol_model_array_t *a=m.arrays+i;
        a->reference=u32(b+0x2c+4*i); a->stride=strides[i];
        a->count=i>=1 && i<=3 ? m.bones-m.roots : m.bones;
        if (a->reference==UINT32_MAX) {
            if (a->count>(asset->size-p)/a->stride) return 0;
            offsets[i]=p; p+=(size_t)a->count*a->stride;
            if (i==CODOL_MODEL_PARENTS) {
                for (j=0;j<a->count;++j)
                    if (!b[offsets[i]+j] || b[offsets[i]+j]>m.roots+j) return 0;
            }
            if (i==CODOL_MODEL_TRANSLATIONS || i==CODOL_MODEL_BASE_MATS) {
                for (j=0;j<a->count*a->stride;j+=4) {
                    uint32_t bits=u32(b+offsets[i]+j); float value;
                    memcpy(&value,&bits,4); if (!isfinite(value)) return 0;
                }
            }
        } else if (a->reference && a->count) ++m.unresolved;
    }
    m.consumed=p;
    /* File data is packed. Keep the allocation base for free(), but give each
     * array a 16-byte-aligned address for native skeletal consumers. Counts
     * are byte-sized, so the six bounded arrays cannot overflow this sum. */
    owned_size+=name_length;
    for (i=0;i<6;++i) if (offsets[i])
        owned_size+=15+(size_t)m.arrays[i].count*m.arrays[i].stride;
    m.storage=malloc(owned_size);
    if (!m.storage) return 0;
    p=0;
    if (name_offset) { memcpy(m.storage,b+name_offset,name_length); m.name=(const char *)m.storage; p=name_length; }
    for (i=0;i<6;++i) if (offsets[i]) {
        size_t length=(size_t)m.arrays[i].count*m.arrays[i].stride;
        p+=(16-((uintptr_t)(m.storage+p)&15))&15;
        m.arrays[i].data=m.storage+p;
        memcpy(m.storage+p,b+offsets[i],length); p+=length;
    }
    *out=m; return 1;
}
int CODOL_RelocateXModelSkeleton(const codol_xmodel_skeleton_t *source,
    const codol_model_block_t blocks[8], codol_xmodel_skeleton_t *out)
{
    static const unsigned strides[6]={2,1,8,12,1,32};
    const uint8_t *arrays[6];
    const char *name;
    size_t lengths[6],name_length=0,size=360,p;
    unsigned i;
    uint8_t *data;
    codol_asset_t asset;
    codol_xmodel_skeleton_t result={0};
    if (!source || !blocks || !out || source==out || source->bones>255 ||
        source->roots>source->bones || source->surfaces>255) return 0;
    name=source->name;
    if (!name && source->name_reference) {
        size_t available;
        const uint8_t *end,*start=block_pointer(blocks,source->name_reference,1,&available);
        if (!start || !(end=memchr(start,0,available))) return 0;
        name=(const char *)start; name_length=(size_t)(end-start)+1;
    } else if (name) name_length=strlen(name)+1;
    if (name_length>CODOL_ASSET_LIMIT-size) return 0;
    size+=name_length;
    for (i=0;i<6;++i) {
        const codol_model_array_t *a=source->arrays+i;
        unsigned count=i>=1 && i<=3 ? source->bones-source->roots : source->bones;
        if (a->count!=count || a->stride!=strides[i]) return 0;
        lengths[i]=(size_t)count*strides[i]; arrays[i]=a->data;
        if (lengths[i] && !arrays[i]) arrays[i]=block_pointer(blocks,a->reference,lengths[i],NULL);
        if (lengths[i] && !arrays[i]) return 0;
        if (lengths[i]>CODOL_ASSET_LIMIT-size) return 0;
        size+=lengths[i];
    }
    data=calloc(size,1); if (!data) return 0;
    data[4]=source->bones; data[5]=source->roots; data[6]=source->surfaces;
    p=360;
    if (name) { put32(data,UINT32_MAX); memcpy(data+p,name,name_length); p+=name_length; }
    for (i=0;i<6;++i) {
        put32(data+44+4*i,UINT32_MAX);
        if (lengths[i]) memcpy(data+p,arrays[i],lengths[i]);
        p+=lengths[i];
    }
    asset=(codol_asset_t){4,data,size};
    i=CODOL_ReadXModelSkeleton(&asset,&result); free(data);
    if (!i) return 0;
    result.name_reference=source->name_reference;
    result.consumed=source->consumed;
    for (i=0;i<6;++i) result.arrays[i].reference=source->arrays[i].reference;
    *out=result; return 1;
}
void CODOL_FreeXModelBoneNames(codol_xmodel_bone_names_t *names)
{
    if (!names) return;
    free(names->names); free(names->storage); memset(names,0,sizeof(*names));
}
int CODOL_ResolveXModelBoneNames(const codol_xmodel_skeleton_t *model,
    const codol_script_string_t *pool, unsigned pool_count, codol_xmodel_bone_names_t *out)
{
    codol_xmodel_bone_names_t result={0};
    const codol_model_array_t *array;
    size_t size=0,pos=0;
    unsigned i;
    if (!model || !out || (pool_count && !pool) || model->bones>255) return 0;
    array=model->arrays+CODOL_MODEL_BONE_NAMES;
    if (array->count!=model->bones || array->stride!=2 || (model->bones && !array->data)) return 0;
    for (i=0;i<model->bones;++i) {
        unsigned index=array->data[2*i]|(unsigned)array->data[2*i+1]<<8;
        size_t length;
        if (index>=pool_count) return 0;
        if (!pool[index].text) continue;
        length=strlen(pool[index].text)+1;
        if (length>CODOL_ASSET_LIMIT-size) return 0;
        size+=length;
    }
    result.count=model->bones;
    if (result.count && !(result.names=calloc(result.count,sizeof(*result.names)))) return 0;
    if (size && !(result.storage=malloc(size))) { free(result.names); return 0; }
    for (i=0;i<result.count;++i) {
        codol_xmodel_bone_name_t *name=result.names+i;
        const char *text;
        name->index=array->data[2*i]|(unsigned)array->data[2*i+1]<<8;
        name->reference=pool[name->index].reference;
        text=pool[name->index].text;
        if (text) {
            size_t length=strlen(text)+1;
            memcpy(result.storage+pos,text,length);
            name->text=result.storage+pos; pos+=length;
        } else ++result.unresolved;
    }
    *out=result; return 1;
}
