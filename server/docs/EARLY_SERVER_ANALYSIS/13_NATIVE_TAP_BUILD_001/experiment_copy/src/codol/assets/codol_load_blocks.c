/* C1 Push/PopStreamPos 0x4cee10/0x4cee70, InsertPointer 0x4ceec0.
 * Block 0 rewinds on pop; block 2 loader branches zero-fill runtime memory. */
#include "codol_load_blocks.h"
#include <stdlib.h>
#include <string.h>
void CODOL_FreeLoadBlocks(codol_load_blocks_t *s)
{
    unsigned i;
    if (!s) return;
    for (i=0;i<8;++i) free(s->data[i]);
    free(s->asset_aliases);
    free(s->dynamic_records);
    free(s->sound_records);
    free(s->glass_records);
    memset(s,0,sizeof(*s));
}
int CODOL_InitLoadBlocks(codol_load_blocks_t *out,const uint8_t *source,size_t size,
    const uint32_t capacities[8],unsigned active)
{
    codol_load_blocks_t s={0};
    size_t total=0;
    unsigned i;
    if (!out || !capacities || (!source && size) || size>CODOL_ASSET_LIMIT || active>=8) return 0;
    for (i=0;i<8;++i) {
        if (capacities[i]>0x10000000u || capacities[i]>CODOL_ASSET_LIMIT-total) return 0;
        total+=capacities[i];
    }
    for (i=0;i<8;++i) {
        s.capacity[i]=capacities[i];
        if (capacities[i] && !(s.data[i]=calloc(capacities[i],1))) {
            CODOL_FreeLoadBlocks(&s); return 0;
        }
    }
    s.source=source; s.source_size=size; s.active=active; *out=s; return 1;
}
int CODOL_PushLoadBlock(codol_load_blocks_t *s,unsigned block)
{
    if (!s || block>=8 || s->active>=8 || s->depth>=CODOL_LOAD_STACK) return 0;
    s->stack[s->depth].block=s->active;
    s->stack[s->depth].entered=s->position[block];
    ++s->depth; s->active=block; return 1;
}
int CODOL_PopLoadBlock(codol_load_blocks_t *s)
{
    if (!s || !s->depth || s->depth>CODOL_LOAD_STACK || s->active>=8) return 0;
    --s->depth;
    if (!s->active) s->position[0]=s->stack[s->depth].entered;
    s->active=s->stack[s->depth].block; return 1;
}
static int reserve(codol_load_blocks_t *s,unsigned block,size_t length,unsigned alignment,
    int read,int apply,uint32_t *reference)
{
    size_t p;
    if (!s || !reference || block>=8 || !alignment || alignment>128 || (alignment&(alignment-1))) return 0;
    if (s->position[block]>s->capacity[block] || s->capacity[block]>0x10000000u) return 0;
    p=(s->position[block]+alignment-1)&~(size_t)(alignment-1);
    if (p>=0x10000000u || p>s->capacity[block] || length>s->capacity[block]-p ||
        (length && !s->data[block])) return 0;
    if (read && block!=2 && (s->source_position>s->source_size ||
        length>s->source_size-s->source_position || (length && !s->source))) return 0;
    if (length && apply) {
        if (read && block!=2) memcpy(s->data[block]+p,s->source+s->source_position,length);
        else memset(s->data[block]+p,0,length);
    }
    if (read && block!=2) s->source_position+=length;
    s->position[block]=p+length;
    if (s->written[block]<p+length) s->written[block]=p+length;
    *reference=((uint32_t)block<<28)+(uint32_t)p+1; return 1;
}
int CODOL_ReadLoadBlock(codol_load_blocks_t *s,size_t length,unsigned alignment,uint32_t *reference)
{ return s && reserve(s,s->active,length,alignment,1,1,reference); }
int CODOL_InsertLoadPointer(codol_load_blocks_t *s,uint32_t *reference)
{ return reserve(s,3,4,4,0,1,reference); }
void CODOL_LoadBlockViews(const codol_load_blocks_t *s,codol_model_block_t views[8])
{
    unsigned i;
    if (!s || !views) return;
    for (i=0;i<8;++i) views[i]=(codol_model_block_t){s->data[i],s->written[i]};
}
int CODOL_ReplayXModelSkeleton(codol_load_blocks_t *stream,codol_xmodel_skeleton_t *out)
{
    static const unsigned alignments[6]={2,1,2,4,1,4};
    codol_load_blocks_t plan;
    codol_xmodel_skeleton_t model={0};
    codol_asset_t asset;
    unsigned i,pass;
    uint32_t name_reference,array_references[6],ignored;
    size_t name_length;
    if (!stream || !out || stream->active!=0 || !stream->source ||
        stream->source_position>stream->source_size || stream->depth>=CODOL_LOAD_STACK) return 0;
    asset=(codol_asset_t){4,stream->source+stream->source_position,stream->source_size-stream->source_position};
    if (!CODOL_ReadXModelSkeleton(&asset,&model)) return 0;
    name_length=model.name ? strlen(model.name)+1 : 0;
    /* First pass validates all cursor operations without writing block memory.
     * The second pass applies precisely the validated sequence. */
    for (pass=0;pass<2;++pass) {
        plan=*stream;
        name_reference=model.name_reference;
        if (!reserve(&plan,0,360,4,1,pass,&ignored) || !CODOL_PushLoadBlock(&plan,3)) goto fail;
        if (model.name_reference==UINT32_MAX &&
            !reserve(&plan,3,name_length,1,1,pass,&name_reference)) goto fail;
        for (i=0;i<6;++i) {
            codol_model_array_t *a=model.arrays+i;
            array_references[i]=a->reference;
            if (a->reference==UINT32_MAX &&
                !reserve(&plan,3,(size_t)a->count*a->stride,alignments[i],1,pass,array_references+i)) goto fail;
        }
    }
    model.name_reference=name_reference;
    for (i=0;i<6;++i) model.arrays[i].reference=array_references[i];
    *stream=plan; *out=model; return 1;
fail:
    CODOL_FreeXModelSkeleton(&model); return 0;
}
static uint32_t read32(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static const uint8_t *replay_bytes(codol_load_blocks_t *s,uint32_t count,unsigned stride,
    unsigned alignment,int apply)
{
    const uint8_t *start;
    uint32_t ignored;
    if (s->source_position>s->source_size || count>(s->source_size-s->source_position)/stride) return NULL;
    start=s->source+s->source_position;
    if (!reserve(s,s->active,(size_t)count*stride,alignment,1,apply,&ignored)) return NULL;
    return start;
}
static int replay_string(codol_load_blocks_t *s,int apply)
{
    const uint8_t *end;
    uint32_t ignored;
    if (s->source_position>=s->source_size ||
        !(end=memchr(s->source+s->source_position,0,s->source_size-s->source_position))) return 0;
    return reserve(s,s->active,(size_t)(end-(s->source+s->source_position))+1,1,1,apply,&ignored);
}
static int replay_physics(codol_load_blocks_t *s,unsigned type,int apply,uint32_t *reference)
{
    const uint8_t *h,*geoms;
    unsigned i,count;
    h=s->source+s->source_position;
    if (!reserve(s,0,type ? 72 : 68,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    if (read32(h)==UINT32_MAX && !replay_string(s,apply)) return 0;
    if (!type) {
        if (read32(h+28)==UINT32_MAX && !replay_string(s,apply)) return 0;
    } else if (read32(h+8)) {
        count=read32(h+4);
        if (!(geoms=replay_bytes(s,count,68,4,apply))) return 0;
        for (i=0;i<count;++i) if (read32(geoms+68*i)) {
            const uint8_t *brush,*sides;
            unsigned j,n;
            if (!(brush=replay_bytes(s,1,68,4,apply))) return 0;
            n=brush[24]|(unsigned)brush[25]<<8;
            if (read32(brush+28)) {
                if (!(sides=replay_bytes(s,n,8,4,apply))) return 0;
                for (j=0;j<n;++j)
                    if (read32(sides+8*j)==UINT32_MAX && !replay_bytes(s,1,20,4,apply)) return 0;
            }
            if (read32(brush+32) && !replay_bytes(s,read32(brush+60),1,1,apply)) return 0;
            if (read32(brush+64)==UINT32_MAX && !replay_bytes(s,n,20,4,apply)) return 0;
        }
    }
    return CODOL_PopLoadBlock(s);
}
int CODOL_ReplayPhysicsAsset(codol_load_blocks_t *stream,unsigned type,uint32_t *reference)
{
    codol_load_blocks_t plan;
    uint32_t result;
    unsigned pass;
    if (!stream || !reference || type>1 || stream->active!=0 || !stream->source ||
        stream->source_position>stream->source_size || stream->depth>=CODOL_LOAD_STACK) return 0;
    for (pass=0;pass<2;++pass) {
        plan=*stream;
        if (!replay_physics(&plan,type,pass,&result)) return 0;
    }
    *stream=plan; *reference=result; return 1;
}
static unsigned read16(const uint8_t *p) { return p[0]|(unsigned)p[1]<<8; }
static int replay_surfaces(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    const uint8_t *h=s->source+s->source_position,*surfaces;
    unsigned i,count;
    if (!reserve(s,0,48,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    if (read32(h)==UINT32_MAX && !replay_string(s,apply)) return 0;
    if (read32(h+4)) {
        count=read16(h+8);
        if (!(surfaces=replay_bytes(s,count,84,4,apply))) return 0;
        for (i=0;i<count;++i) {
            const uint8_t *surface=surfaces+84*i,*rigid;
            unsigned j,n,blend=0;
            if (read32(surface+28)==UINT32_MAX) {
                for (j=0;j<4;++j) {
                    n=read16(surface+20+2*j); if (n>32767) return 0;
                    blend+=n*(2*j+1);
                }
                if (!replay_bytes(s,blend,2,2,apply)) return 0;
            }
            if (!CODOL_PushLoadBlock(s,6)) return 0;
            if (read32(surface+32)==UINT32_MAX && !replay_bytes(s,read16(surface+4),32,16,apply)) return 0;
            if (!CODOL_PopLoadBlock(s)) return 0;
            if (read32(surface+44)==UINT32_MAX) {
                n=read32(surface+40);
                if (!(rigid=replay_bytes(s,n,12,4,apply))) return 0;
                for (j=0;j<n;++j) if (read32(rigid+12*j+8)==UINT32_MAX) {
                    const uint8_t *tree=replay_bytes(s,1,40,4,apply);
                    if (!tree) return 0;
                    if (read32(tree+28) && !replay_bytes(s,read32(tree+24),16,16,apply)) return 0;
                    if (read32(tree+36) && !replay_bytes(s,read32(tree+32),2,2,apply)) return 0;
                }
            }
            if (!CODOL_PushLoadBlock(s,7)) return 0;
            if (read32(surface+16)==UINT32_MAX && !replay_bytes(s,read16(surface+6),6,16,apply)) return 0;
            if (!CODOL_PopLoadBlock(s)) return 0;
        }
    }
    return CODOL_PopLoadBlock(s);
}
int CODOL_ReplayModelSurfaces(codol_load_blocks_t *stream,uint32_t *reference)
{
    codol_load_blocks_t plan;
    uint32_t result;
    unsigned pass;
    if (!stream || !reference || stream->active!=0 || !stream->source ||
        stream->source_position>stream->source_size || stream->depth>=CODOL_LOAD_STACK) return 0;
    for (pass=0;pass<2;++pass) {
        plan=*stream;
        if (!replay_surfaces(&plan,pass,&result)) return 0;
    }
    *stream=plan; *reference=result; return 1;
}
/* Image 0x4b92d0/load-def 0x4b9250; water 0x4b95a0. */
static int replay_image(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    const uint8_t *h=s->source+s->source_position,*definition;
    if (!reserve(s,0,36,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    if (read32(h+32)==UINT32_MAX && !replay_string(s,apply)) return 0;
    if (read32(h)==UINT32_MAX) {
        if (!(definition=replay_bytes(s,1,16,4,apply)) ||
            !replay_bytes(s,read32(definition+12),1,1,apply)) return 0;
    }
    return CODOL_PopLoadBlock(s);
}
static int replay_water(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    const uint8_t *h=s->source+s->source_position;
    uint32_t m,n,image,ignored;
    uint64_t cells;
    if (!reserve(s,3,68,4,1,apply,reference)) return 0;
    m=read32(h+12); n=read32(h+16); cells=(uint64_t)m*n;
    if (m>INT32_MAX || n>INT32_MAX || cells>UINT32_MAX) return 0;
    if (read32(h+4) && !replay_bytes(s,(uint32_t)cells,8,4,apply)) return 0;
    if (read32(h+8) && !replay_bytes(s,(uint32_t)cells,4,4,apply)) return 0;
    image=read32(h+64);
    if (!CODOL_PushLoadBlock(s,0)) return 0;
    if (image>=UINT32_MAX-1) {
        if (image==UINT32_MAX-1 && !reserve(s,3,4,4,0,apply,&ignored)) return 0;
        if (!replay_image(s,apply,&ignored)) return 0;
    }
    return CODOL_PopLoadBlock(s);
}
static int replay_texture_dependency(codol_load_blocks_t *stream,int water,uint32_t *reference)
{
    codol_load_blocks_t plan;
    uint32_t result;
    unsigned pass;
    if (!stream || !reference || stream->active!=(water ? 3u : 0u) || !stream->source ||
        stream->source_position>stream->source_size || stream->depth>=CODOL_LOAD_STACK) return 0;
    for (pass=0;pass<2;++pass) {
        plan=*stream;
        if (!(water ? replay_water(&plan,pass,&result) : replay_image(&plan,pass,&result))) return 0;
    }
    *stream=plan; *reference=result; return 1;
}
int CODOL_ReplayImage(codol_load_blocks_t *s,uint32_t *reference)
{ return replay_texture_dependency(s,0,reference); }
int CODOL_ReplayWater(codol_load_blocks_t *s,uint32_t *reference)
{ return replay_texture_dependency(s,1,reference); }
static int replay_shader(codol_load_blocks_t *s,int declaration,int apply,uint32_t *reference)
{
    const uint8_t *h=s->source+s->source_position;
    if (!reserve(s,0,declaration ? 100 : 16,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    if (read32(h)==UINT32_MAX && !replay_string(s,apply)) return 0;
    if (!declaration && read32(h+8) && !replay_bytes(s,read16(h+12),4,4,apply)) return 0;
    return CODOL_PopLoadBlock(s);
}
static int replay_shader_asset(codol_load_blocks_t *s,int apply,uint32_t *reference)
{ return replay_shader(s,0,apply,reference); }
static int replay_declaration_asset(codol_load_blocks_t *s,int apply,uint32_t *reference)
{ return replay_shader(s,1,apply,reference); }
static int replay_shader_reference(codol_load_blocks_t *s,uint32_t reference,int declaration,int apply)
{
    uint32_t ignored;
    if (!CODOL_PushLoadBlock(s,0)) return 0;
    if (reference>=UINT32_MAX-1) {
        if (reference==UINT32_MAX-1 && !reserve(s,3,4,4,0,apply,&ignored)) return 0;
        if (!replay_shader(s,declaration,apply,&ignored)) return 0;
    }
    return CODOL_PopLoadBlock(s);
}
/* C1 0x4ba130/0x4ba0c0/0x4b9ef0: technique names follow passes. */
static int replay_technique_set(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    const uint8_t *h=s->source+s->source_position;
    unsigned i,j,k;
    if (!reserve(s,0,204,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    if (read32(h)==UINT32_MAX && !replay_string(s,apply)) return 0;
    for (i=0;i<48;++i) if (read32(h+12+4*i)==UINT32_MAX) {
        const uint8_t *technique,*passes;
        unsigned count;
        if (!(technique=replay_bytes(s,1,8,4,apply))) return 0;
        count=read16(technique+6);
        if (!(passes=replay_bytes(s,count,20,1,apply))) return 0;
        for (j=0;j<count;++j) {
            const uint8_t *pass=passes+20*j,*args;
            unsigned n;
            if (!replay_shader_reference(s,read32(pass),1,apply) ||
                !replay_shader_reference(s,read32(pass+4),0,apply) ||
                !replay_shader_reference(s,read32(pass+8),0,apply)) return 0;
            if (read32(pass+16)) {
                n=pass[12]+pass[13]+pass[14];
                if (!(args=replay_bytes(s,n,8,4,apply))) return 0;
                for (k=0;k<n;++k)
                    if ((read16(args+8*k)==1 || read16(args+8*k)==7) &&
                        read32(args+8*k+4)==UINT32_MAX && !replay_bytes(s,1,16,4,apply)) return 0;
            }
        }
        if (read32(technique)==UINT32_MAX && !replay_string(s,apply)) return 0;
    }
    return CODOL_PopLoadBlock(s);
}
int CODOL_ReplayTechniqueSet(codol_load_blocks_t *stream,uint32_t *reference)
{
    codol_load_blocks_t plan;
    uint32_t result;
    unsigned pass;
    if (!stream || !reference || stream->active!=0 || !stream->source ||
        stream->source_position>stream->source_size || stream->depth>=CODOL_LOAD_STACK) return 0;
    for (pass=0;pass<2;++pass) {
        plan=*stream;
        if (!replay_technique_set(&plan,pass,&result)) return 0;
    }
    *stream=plan; *reference=result; return 1;
}
static int replay_material(codol_load_blocks_t *,int,uint32_t *);
static int replay_model(codol_load_blocks_t *,int,uint32_t *);
static int replay_effect(codol_load_blocks_t *,int,uint32_t *);
static int replay_preset_asset(codol_load_blocks_t *,int,uint32_t *);
static int replay_physics_map_asset(codol_load_blocks_t *,int,uint32_t *);
static int replay_tracer(codol_load_blocks_t *,int,uint32_t *);
static int replay_sound_alias(codol_load_blocks_t *,int,uint32_t *);
static int replay_sound_curve(codol_load_blocks_t *,int,uint32_t *);
static int replay_loaded_sound(codol_load_blocks_t *,int,uint32_t *);
static int record_asset(codol_load_blocks_t *s,unsigned type,uint32_t ref,size_t start,int apply)
{
    if (!s->collect_asset_aliases) return 1;
    if (apply) {
        if (s->asset_alias_count>=s->asset_alias_capacity) return 0;
        s->asset_aliases[s->asset_alias_count]=(codol_asset_alias_t){
            ref,{type,s->source+start,s->source_position-start}};
    }
    ++s->asset_alias_count; return 1;
}
static int replay_weapon(codol_load_blocks_t *,int,uint32_t *);
/* field is the block 3 address of the word holding the reference, or 0 when
 * that word lives in temporary memory. C1 only emits the insert-pointer marker
 * (-2) for temporary holders; a holder already in block 3 is itself the target
 * of later deduplicated pointers (DB_ConvertOffsetToAlias reads the linked
 * asset back out of that word), so an inline (-1) asset must be catalogued at
 * the holder's own address for those pointers to resolve. */
static int replay_field_asset_reference(codol_load_blocks_t *s,uint32_t reference,uint32_t field,int apply,
    int (*loader)(codol_load_blocks_t *,int,uint32_t *))
{
    uint32_t ignored,alias=reference==UINT32_MAX ? field : 0;
    size_t start=s->source_position;
    if (!CODOL_PushLoadBlock(s,0)) return 0;
    if (reference>=UINT32_MAX-1) {
        int type=loader==replay_material ? 5 : loader==replay_model ? 4 : loader==replay_surfaces ? 3 :
            loader==replay_preset_asset ? 0 : loader==replay_physics_map_asset ? 1 : loader==replay_effect ? 30 : loader==replay_tracer ? 40 :
            loader==replay_sound_alias ? 11 : loader==replay_sound_curve ? 12 : loader==replay_loaded_sound ? 13 : loader==replay_weapon ? 28 : -1;
        if (reference==UINT32_MAX-1 && !reserve(s,3,4,4,0,apply,&alias)) return 0;
        if (!loader(s,apply,&ignored)) return 0;
        if (type>=0 && !record_asset(s,(unsigned)type,alias,start,apply)) return 0;
    }
    return CODOL_PopLoadBlock(s);
}
static int replay_asset_reference(codol_load_blocks_t *s,uint32_t reference,int apply,
    int (*loader)(codol_load_blocks_t *,int,uint32_t *))
{ return replay_field_asset_reference(s,reference,0,apply,loader); }
static int replay_material(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    const uint8_t *h=s->source+s->source_position,*textures;
    uint32_t ignored;
    unsigned i;
    if (!reserve(s,0,96,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    if (read32(h)==UINT32_MAX && !replay_string(s,apply)) return 0;
    if (!replay_asset_reference(s,read32(h+80),apply,replay_technique_set)) return 0;
    if (read32(h+84)==UINT32_MAX) {
        if (!(textures=replay_bytes(s,h[72],12,4,apply))) return 0;
        for (i=0;i<h[72];++i) {
            const uint8_t *texture=textures+12*i;
            uint32_t ref=read32(texture+8);
            if (texture[7]==11) {
                if (ref==UINT32_MAX && !replay_water(s,apply,&ignored)) return 0;
            } else if (!replay_asset_reference(s,ref,apply,replay_image)) return 0;
        }
    }
    if (read32(h+88)==UINT32_MAX && !replay_bytes(s,h[73],32,16,apply)) return 0;
    if (read32(h+92)==UINT32_MAX && !replay_bytes(s,h[74],8,4,apply)) return 0;
    return CODOL_PopLoadBlock(s);
}
int CODOL_ReplayMaterial(codol_load_blocks_t *stream,uint32_t *reference)
{
    codol_load_blocks_t plan;
    uint32_t result;
    unsigned pass;
    if (!stream || !reference || stream->active!=0 || !stream->source ||
        stream->source_position>stream->source_size || stream->depth>=CODOL_LOAD_STACK) return 0;
    for (pass=0;pass<2;++pass) {
        plan=*stream;
        if (!replay_material(&plan,pass,&result)) return 0;
    }
    *stream=plan; *reference=result; return 1;
}
static int replay_preset_asset(codol_load_blocks_t *s,int apply,uint32_t *reference)
{ return replay_physics(s,0,apply,reference); }
static int replay_physics_map_asset(codol_load_blocks_t *s,int apply,uint32_t *reference)
{ return replay_physics(s,1,apply,reference); }
static int replay_model(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    static const unsigned strides[6]={2,1,8,12,1,32},alignments[6]={2,1,2,4,1,4};
    const uint8_t *h=s->source+s->source_position,*materials,*surfaces;
    unsigned i,count;
    if (!reserve(s,0,360,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    if (h[5]>h[4]) return 0;
    if (read32(h)==UINT32_MAX && !replay_string(s,apply)) return 0;
    for (i=0;i<6;++i) if (read32(h+44+4*i)==UINT32_MAX) {
        count=i>=1 && i<=3 ? h[4]-h[5] : h[4];
        if (!replay_bytes(s,count,strides[i],alignments[i],apply)) return 0;
    }
    if (read32(h+68)) {
        uint32_t slots=0x30000001u+(uint32_t)((s->position[3]+3)&~(size_t)3);
        if (!(materials=replay_bytes(s,h[6],4,4,apply))) return 0;
        for (i=0;i<h[6];++i) {
            size_t start=s->source_position;
            if (!replay_asset_reference(s,read32(materials+4*i),apply,replay_material)) return 0;
            if (read32(materials+4*i)>=UINT32_MAX-1 &&
                !record_asset(s,5,slots+4*i,start,apply)) return 0;
        }
    }
    for (i=0;i<4;++i) {
        const uint8_t *lod=h+72+56*i;
        if (!replay_asset_reference(s,read32(lod+8),apply,replay_surfaces)) return 0;
        if (read32(lod+12)==UINT32_MAX && !replay_string(s,apply)) return 0;
    }
    if (read32(h+0x12c)) {
        count=read32(h+0x130);
        if (!(surfaces=replay_bytes(s,count,44,4,apply))) return 0;
        for (i=0;i<count;++i)
            if (read32(surfaces+44*i) && !replay_bytes(s,read32(surfaces+44*i+4),48,4,apply)) return 0;
    }
    if (read32(h+0x138) && !replay_bytes(s,h[4],28,4,apply)) return 0;
    if (!replay_asset_reference(s,read32(h+0x160),apply,replay_preset_asset) ||
        !replay_asset_reference(s,read32(h+0x164),apply,replay_physics_map_asset)) return 0;
    return CODOL_PopLoadBlock(s);
}
int CODOL_ReplayXModel(codol_load_blocks_t *stream,uint32_t *reference)
{
    codol_load_blocks_t plan;
    codol_asset_t asset;
    size_t extent;
    uint32_t result;
    unsigned pass;
    if (!stream || !reference || stream->active!=0 || !stream->source ||
        stream->source_position>stream->source_size || stream->depth>=CODOL_LOAD_STACK) return 0;
    asset=(codol_asset_t){4,stream->source+stream->source_position,stream->source_size-stream->source_position};
    if (!CODOL_ReadXModelExtent(&asset,&extent)) return 0;
    for (pass=0;pass<2;++pass) {
        plan=*stream;
        if (!replay_model(&plan,pass,&result) || plan.source_position-stream->source_position!=extent) return 0;
    }
    *stream=plan; *reference=result; return 1;
}
/* C1 XAnimParts 0x4b7a50, delta parts 0x4b7690 and track loaders. */
static int replay_animation(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    static const unsigned pointer_offsets[6]={52,56,60,64,68,72};
    static const unsigned count_offsets[6]={4,6,8,32,10,12};
    static const unsigned widths[6]={1,2,4,2,1,4};
    const uint8_t *h=s->source+s->source_position,*delta;
    unsigned i,index_width;
    if (!reserve(s,0,88,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    if (read32(h)==UINT32_MAX && !replay_string(s,apply)) return 0;
    if (read32(h+48) && !replay_bytes(s,h[26],2,2,apply)) return 0;
    if (read32(h+80) && !replay_bytes(s,h[27],8,4,apply)) return 0;
    index_width=read16(h+14)<256 ? 1 : 2;
    if (read32(h+84)) {
        if (!(delta=replay_bytes(s,1,12,4,apply))) return 0;
        for (i=0;i<3;++i) if (read32(delta+4*i)) {
            const uint8_t *track=replay_bytes(s,1,4,4,apply),*frames;
            unsigned count;
            if (!track) return 0;
            count=read16(track);
            if (!count) {
                if (!replay_bytes(s,1,i==0 ? 12 : i==1 ? 4 : 8,1,apply)) return 0;
            } else {
                if (!(frames=replay_bytes(s,1,i==0 ? 28 : 4,1,apply)) ||
                    !replay_bytes(s,count+1,index_width,1,apply)) return 0;
                if (read32(frames+(i==0 ? 24 : 0))) {
                    unsigned stride=i==0 ? (track[2] ? 3 : 6) : i==1 ? 4 : 8;
                    unsigned alignment=i==0 && track[2] ? 1 : 4;
                    if (!replay_bytes(s,count+1,stride,alignment,apply)) return 0;
                }
            }
        }
    }
    for (i=0;i<6;++i) if (read32(h+pointer_offsets[i])) {
        uint32_t count=i==3 ? read32(h+count_offsets[i]) : read16(h+count_offsets[i]);
        if (!replay_bytes(s,count,widths[i],widths[i],apply)) return 0;
    }
    if (read32(h+76) && !replay_bytes(s,read32(h+36),index_width,index_width,apply)) return 0;
    return CODOL_PopLoadBlock(s);
}
int CODOL_ReplayAnimation(codol_load_blocks_t *stream,uint32_t *reference)
{
    codol_load_blocks_t plan;
    uint32_t result;
    unsigned pass;
    if (!stream || !reference || stream->active!=0 || !stream->source ||
        stream->source_position>stream->source_size || stream->depth>=CODOL_LOAD_STACK) return 0;
    for (pass=0;pass<2;++pass) {
        plan=*stream;
        if (!replay_animation(&plan,pass,&result)) return 0;
    }
    *stream=plan; *reference=result; return 1;
}
/* C1 FxEffectDef 0x4bd5e0; element/visual/extension loaders 0x4bd2b0,
 * 0x4bd050 and 0x4bd230. Effect references serialize names, not nested FX. */
static int replay_effect_visual(codol_load_blocks_t *s,unsigned type,uint32_t ref,uint32_t slot,int apply)
{
    size_t start=s->source_position;
    if (type==12 || type==14) return ref!=UINT32_MAX || replay_string(s,apply);
    if (type==10 || type==11) return 1;
    if(!replay_asset_reference(s,ref,apply,type==9 ? replay_model : replay_material)) return 0;
    return ref<UINT32_MAX-1 || record_asset(s,type==9 ? 4 : 5,slot,start,apply);
}
static int replay_effect(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    const uint8_t *h=s->source+s->source_position,*elements,*visuals,*trail;
    uint64_t count=0;
    unsigned i,j,type,n; uint32_t element_slots,visual_slots;
    if (!reserve(s,0,32,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    if (read32(h)==UINT32_MAX && !replay_string(s,apply)) return 0;
    for (i=16;i<=24;i+=4) {
        uint32_t part=read32(h+i);
        if (part>INT32_MAX) return 0;
        count+=part;
    }
    if (count>INT32_MAX) return 0;
    if (read32(h+28)) {
        element_slots=0x30000001u+(uint32_t)((s->position[3]+3)&~(size_t)3);
        if (!(elements=replay_bytes(s,(uint32_t)count,260,4,apply))) return 0;
        for (i=0;i<count;++i) {
            const uint8_t *e=elements+260*(size_t)i;
            type=e[176]; n=e[177];
            if (read32(e+180) && !replay_bytes(s,e[178]+1,96,4,apply)) return 0;
            if (read32(e+184) && !replay_bytes(s,e[179]+1,48,4,apply)) return 0;
            if (type==13) {
                if (read32(e+188)) {
                    visual_slots=0x30000001u+(uint32_t)((s->position[3]+3)&~(size_t)3);
                    if (!(visuals=replay_bytes(s,n,8,4,apply))) return 0;
                    for (j=0;j<2*n;++j)
                        if (!replay_effect_visual(s,0,read32(visuals+4*j),visual_slots+4*j,apply)) return 0;
                }
            } else if (n<=1) {
                if (!replay_effect_visual(s,type,read32(e+188),element_slots+260*i+188,apply)) return 0;
            } else if (read32(e+188)) {
                visual_slots=0x30000001u+(uint32_t)((s->position[3]+3)&~(size_t)3);
                if (!(visuals=replay_bytes(s,n,4,4,apply))) return 0;
                for (j=0;j<n;++j)
                    if (!replay_effect_visual(s,type,read32(visuals+4*j),visual_slots+4*j,apply)) return 0;
            }
            for (j=216;j<=224;j+=4)
                if (read32(e+j)==UINT32_MAX && !replay_string(s,apply)) return 0;
            if (read32(e+244)) {
                if (type==5) {
                    if (!(trail=replay_bytes(s,1,36,4,apply))) return 0;
                    if (read32(trail+24) && !replay_bytes(s,read32(trail+20),20,4,apply)) return 0;
                    if (read32(trail+32) && !replay_bytes(s,read32(trail+28),2,2,apply)) return 0;
                } else if (!replay_bytes(s,1,type==8 ? 52 : 1,type==8 ? 4 : 1,apply)) return 0;
            }
            if (read32(e+256)==UINT32_MAX && !replay_string(s,apply)) return 0;
        }
    }
    return CODOL_PopLoadBlock(s);
}
int CODOL_ReplayEffect(codol_load_blocks_t *stream,uint32_t *reference)
{
    codol_load_blocks_t plan;
    uint32_t result;
    unsigned pass;
    if (!stream || !reference || stream->active!=0 || !stream->source ||
        stream->source_position>stream->source_size || stream->depth>=CODOL_LOAD_STACK) return 0;
    for (pass=0;pass<2;++pass) {
        plan=*stream;
        if (!replay_effect(&plan,pass,&result)) return 0;
    }
    *stream=plan; *reference=result; return 1;
}
/* C1 LoadedSound 0x4b80b0 and sound data 0x4b7f30. Payload storage
 * temporarily enters block 0, even though the name resides in block 3. */
static int replay_loaded_sound(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    const uint8_t *h=s->source+s->source_position;
    uint32_t ref,ignored;
    if (!reserve(s,0,48,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    if (read32(h)==UINT32_MAX && !replay_string(s,apply)) return 0;
    if (!CODOL_PushLoadBlock(s,0)) return 0;
    ref=read32(h+44);
    if (ref>=UINT32_MAX-1) {
        if (ref==UINT32_MAX-1 && !reserve(s,3,4,4,0,apply,&ignored)) return 0;
        if (!replay_bytes(s,read32(h+12),1,1,apply)) return 0;
    }
    return CODOL_PopLoadBlock(s) && CODOL_PopLoadBlock(s);
}
/* C1 SndCurve 0x4b82b0. */
static int replay_sound_curve(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    const uint8_t *h=s->source+s->source_position;
    if (!reserve(s,0,136,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    if (read32(h)==UINT32_MAX && !replay_string(s,apply)) return 0;
    return CODOL_PopLoadBlock(s);
}
/* C1 snd_alias_list_t 0x4b8750, aliases 0x4b84b0, SoundFile 0x4b8240
 * and SpeakerMap 0x4b8420. Pooled array references consume no input. */
/* Reconstructed loaded sounds live in the rewound scratch block, so a
 * deduplicated pointer into replay memory cannot reach them. Record the
 * serialized span of every alias array and sound file next to the block 3
 * address its reconstruction received; the reader replays those spans from the
 * archive image, which stays owned for the archive's whole lifetime. */
static int record_sound_span(codol_load_blocks_t *s,uint32_t reference,size_t start,uint32_t count,int apply)
{
    if (!s->collect_asset_aliases) return 1;
    if (apply) {
        if (s->sound_record_count>=s->sound_record_capacity) return 0;
        s->sound_records[s->sound_record_count]=(codol_sound_span_t){
            s->source+start,reference,(uint32_t)(s->source_position-start),count};
    }
    ++s->sound_record_count; return 1;
}
static uint32_t block_three_reference(const codol_load_blocks_t *s)
{ return 0x30000001u+(uint32_t)((s->position[3]+3)&~(size_t)3); }
static int replay_sound_alias(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    const uint8_t *h=s->source+s->source_position,*aliases,*file,*speakers;
    uint32_t count,i,j,array,record;
    size_t start,at;
    if (!reserve(s,0,12,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    if (read32(h)==UINT32_MAX && !replay_string(s,apply)) return 0;
    count=read32(h+8);
    if (count>INT32_MAX) return 0;
    if (read32(h+4)==UINT32_MAX) {
        array=block_three_reference(s); start=s->source_position;
        if (!(aliases=replay_bytes(s,count,108,4,apply))) return 0;
        for (i=0;i<count;++i) {
            const uint8_t *a=aliases+(size_t)i*108;
            for (j=0;j<=16;j+=4)
                if (read32(a+j)==UINT32_MAX && !replay_string(s,apply)) return 0;
            if (read32(a+20)==UINT32_MAX) {
                record=block_three_reference(s); at=s->source_position;
                if (!(file=replay_bytes(s,1,12,4,apply))) return 0;
                if (file[0]==1) {
                    if (!replay_field_asset_reference(s,read32(file+4),record+4,apply,replay_loaded_sound)) return 0;
                } else {
                    for (j=4;j<=8;j+=4)
                        if (read32(file+j)==UINT32_MAX && !replay_string(s,apply)) return 0;
                }
                if (!record_sound_span(s,record,at,0,apply)) return 0;
            }
            if (!replay_field_asset_reference(s,read32(a+88),array+(uint32_t)i*108+88,apply,replay_sound_curve)) return 0;
            if (read32(a+104)==UINT32_MAX) {
                if (!(speakers=replay_bytes(s,1,408,4,apply))) return 0;
                if (read32(speakers+4)==UINT32_MAX && !replay_string(s,apply)) return 0;
            }
        }
        if (!record_sound_span(s,array,start,count,apply)) return 0;
    }
    return CODOL_PopLoadBlock(s);
}
int CODOL_ReplaySoundAsset(codol_load_blocks_t *stream,unsigned type,uint32_t *reference)
{
    codol_load_blocks_t plan;
    uint32_t result;
    unsigned pass;
    int (*loader)(codol_load_blocks_t *,int,uint32_t *);
    if (!stream || !reference || stream->active!=0 || !stream->source ||
        stream->source_position>stream->source_size || stream->depth>=CODOL_LOAD_STACK) return 0;
    switch (type) {
    case 11: loader=replay_sound_alias; break;
    case 12: loader=replay_sound_curve; break;
    case 13: loader=replay_loaded_sound; break;
    default: return 0;
    }
    for (pass=0;pass<2;++pass) {
        plan=*stream;
        if (!loader(&plan,pass,&result)) return 0;
    }
    *stream=plan; *reference=result; return 1;
}
/* GfxWorld prefix through cells: C1 0x4c7fe0..0x4c81be. Keep block 3
 * entered for the following draw-data stage; this is not a complete asset. */
static int replay_world_visibility(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    const uint8_t *h=s->source+s->source_position,*skies,*counts=NULL,*trees,*nodes,*cells,*portals;
    uint32_t count,i,j,ignored;
    uint64_t runtime;
    if (!reserve(s,0,628,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    for (i=0;i<8;i+=4) if (read32(h+i)==UINT32_MAX && !replay_string(s,apply)) return 0;
    count=read32(h+20);
    if (count>INT32_MAX) return 0;
    if (read32(h+24)) {
        if (!(skies=replay_bytes(s,count,16,4,apply))) return 0;
        for (i=0;i<count;++i) {
            const uint8_t *sky=skies+(size_t)i*16;
            if (read32(sky+4) && !replay_bytes(s,read32(sky),4,4,apply)) return 0;
            if (!replay_asset_reference(s,read32(sky+8),apply,replay_image)) return 0;
        }
    }
    if (read32(h+56)==UINT32_MAX && !replay_bytes(s,read32(h+8),20,4,apply)) return 0;
    if (read32(h+60) && !replay_bytes(s,read32(h+12),2,2,apply)) return 0;
    count=read32(h+52);
    if (count>INT32_MAX || !CODOL_PushLoadBlock(s,2)) return 0;
    runtime=(uint64_t)count*2048;
    if (read32(h+64) && (runtime>SIZE_MAX || !reserve(s,2,(size_t)runtime,4,1,apply,&ignored))) return 0;
    if (!CODOL_PopLoadBlock(s)) return 0;
    if (read32(h+68) && !(counts=replay_bytes(s,count,4,4,apply))) return 0;
    if (read32(h+72)) {
        if (!(trees=replay_bytes(s,count,4,128,apply))) return 0;
        for (i=0;i<count;++i) if (read32(trees+4*i)) {
            uint32_t n;
            if (!counts || (n=read32(counts+4*i))>INT32_MAX ||
                !(nodes=replay_bytes(s,n,44,4,apply))) return 0;
            for (j=0;j<n;++j) {
                const uint8_t *node=nodes+(size_t)j*44;
                if (read32(node+36)==UINT32_MAX && !replay_bytes(s,read16(node+34),2,2,apply)) return 0;
            }
        }
    }
    if (read32(h+76)) {
        if (!(cells=replay_bytes(s,count,40,4,apply))) return 0;
        for (i=0;i<count;++i) {
            const uint8_t *cell=cells+(size_t)i*40;
            uint32_t n=read32(cell+24);
            if (read32(cell+28)) {
                if (n>INT32_MAX || !(portals=replay_bytes(s,n,60,4,apply))) return 0;
                for (j=0;j<n;++j) {
                    const uint8_t *portal=portals+(size_t)j*60;
                    if (read32(portal+28) && !replay_bytes(s,portal[34],12,4,apply)) return 0;
                }
            }
            if (read32(cell+36) && !replay_bytes(s,cell[32],1,1,apply)) return 0;
        }
    }
    return 1;
}
/* C1 GfxWorldDraw 0x4c7d20: reflection probes, lightmaps, vertices and
 * indices. GPU buffer creation is not part of serialized block replay. */
static int replay_world_draw(codol_load_blocks_t *s,const uint8_t *d,int apply)
{
    const uint8_t *images;
    uint32_t count,i,j,ignored;
    uint64_t size;
    count=read32(d);
    if (count>INT32_MAX) return 0;
    if (read32(d+4)) {
        if (!(images=replay_bytes(s,count,4,4,apply))) return 0;
        for (i=0;i<count;++i)
            if (!replay_asset_reference(s,read32(images+4*i),apply,replay_image)) return 0;
    }
    if (read32(d+8) && !replay_bytes(s,count,12,4,apply)) return 0;
    if (!CODOL_PushLoadBlock(s,2)) return 0;
    size=(uint64_t)count*4;
    if (read32(d+12) && (size>SIZE_MAX || !reserve(s,2,(size_t)size,4,1,apply,&ignored))) return 0;
    if (!CODOL_PopLoadBlock(s)) return 0;
    count=read32(d+16);
    if (count>INT32_MAX) return 0;
    if (read32(d+20)) {
        if (!(images=replay_bytes(s,count,8,4,apply))) return 0;
        for (i=0;i<count;++i) for (j=0;j<2;++j)
            if (!replay_asset_reference(s,read32(images+(size_t)i*8+4*j),apply,replay_image)) return 0;
    }
    for (i=24;i<=28;i+=4) {
        if (!CODOL_PushLoadBlock(s,2)) return 0;
        size=(uint64_t)count*4;
        if (read32(d+i) && (size>SIZE_MAX || !reserve(s,2,(size_t)size,4,1,apply,&ignored))) return 0;
        if (!CODOL_PopLoadBlock(s)) return 0;
    }
    for (i=32;i<=36;i+=4)
        if (!replay_asset_reference(s,read32(d+i),apply,replay_image)) return 0;
    if (read32(d+44) && !replay_bytes(s,read32(d+40),44,4,apply)) return 0;
    if (read32(d+56) && !replay_bytes(s,read32(d+52),1,1,apply)) return 0;
    if (read32(d+68) && !replay_bytes(s,read32(d+64),2,2,apply)) return 0;
    return 1;
}
/* C1 GfxLightGrid 0x4c6e60. Row offsets use the selected bounds axis. */
static int replay_world_light_grid(codol_load_blocks_t *s,const uint8_t *g,int apply)
{
    if (read32(g+28)) {
        uint32_t axis=read32(g+20),minimum,maximum;
        if (axis>2) return 0;
        minimum=read16(g+8+2*axis); maximum=read16(g+14+2*axis);
        if (maximum<minimum || !replay_bytes(s,maximum-minimum+1,2,2,apply)) return 0;
    }
    if (read32(g+36) && !replay_bytes(s,read32(g+32),1,1,apply)) return 0;
    if (read32(g+44) && !replay_bytes(s,read32(g+40),4,4,apply)) return 0;
    if (read32(g+52) && !replay_bytes(s,read32(g+48),168,4,apply)) return 0;
    return 1;
}
/* C1 0x4c81e3..0x4c86c8: world models/materials, scene allocations,
 * shadow geometry and light-region hulls. */
static int replay_world_scene(codol_load_blocks_t *s,const uint8_t *h,int apply)
{
    const uint8_t *records,*hulls;
    uint64_t counts[8],cells=read32(h+52),words=(cells+31)/32,non_sun=0;
    static const unsigned strides[8]={4,4,6,4,32768,4,4,1};
    uint32_t i,j,n,lights=read32(h+32),sun=read32(h+28),ignored;
    if (read32(h+212) && !replay_bytes(s,read32(h+208),60,4,apply)) return 0;
    if (read32(h+248)) {
        n=read32(h+244);
        if (n>INT32_MAX || !(records=replay_bytes(s,n,8,4,apply))) return 0;
        for (i=0;i<n;++i)
            if (!replay_asset_reference(s,read32(records+(size_t)i*8),apply,replay_material)) return 0;
    }
    if (!replay_asset_reference(s,read32(h+256),apply,replay_material) ||
        !replay_asset_reference(s,read32(h+260),apply,replay_material) ||
        !replay_asset_reference(s,read32(h+412),apply,replay_image)) return 0;
    if (read32(h+432) || read32(h+436) || read32(h+440)) {
        if (lights<=sun) return 0;
        non_sun=(uint64_t)lights-sun-1;
    }
    counts[0]=words*cells; counts[1]=words;
    counts[2]=read32(h+572); counts[3]=read32(h+576);
    counts[4]=non_sun; counts[5]=non_sun*counts[2]; counts[6]=non_sun*counts[3]; counts[7]=counts[2];
    for (i=0;i<8;++i) {
        if (!CODOL_PushLoadBlock(s,2)) return 0;
        if (read32(h+416+4*i) && (counts[i]>SIZE_MAX/strides[i] ||
            !reserve(s,2,(size_t)counts[i]*strides[i],i==7 ? 1 : 4,1,apply,&ignored))) return 0;
        if (!CODOL_PopLoadBlock(s)) return 0;
    }
    if (lights>INT32_MAX) return 0;
    if (read32(h+448)) {
        if (!(records=replay_bytes(s,lights,12,4,apply))) return 0;
        for (i=0;i<lights;++i) {
            const uint8_t *r=records+(size_t)i*12;
            if (read32(r+4) && !replay_bytes(s,read16(r),2,2,apply)) return 0;
            if (read32(r+8) && !replay_bytes(s,read16(r+2),2,2,apply)) return 0;
        }
    }
    if (read32(h+452)) {
        if (!(records=replay_bytes(s,lights,8,4,apply))) return 0;
        for (i=0;i<lights;++i) {
            const uint8_t *r=records+(size_t)i*8;
            if (read32(r+4)) {
                n=read32(r);
                if (n>INT32_MAX || !(hulls=replay_bytes(s,n,80,4,apply))) return 0;
                for (j=0;j<n;++j) {
                    const uint8_t *hull=hulls+(size_t)j*80;
                    if (read32(hull+76) && !replay_bytes(s,read32(hull+72),20,4,apply)) return 0;
                }
            }
        }
    }
    return 1;
}
static int replay_world_zero(codol_load_blocks_t *s,uint32_t ref,uint64_t count,unsigned stride,unsigned alignment,int apply)
{
    uint32_t ignored;
    if (!CODOL_PushLoadBlock(s,2)) return 0;
    if (ref && (count>SIZE_MAX/stride || !reserve(s,2,(size_t)count*stride,alignment,1,apply,&ignored))) return 0;
    return CODOL_PopLoadBlock(s);
}
/* Static/dynamic DPVS: C1 0x4c7630 / 0x4c7290. */
static int replay_world_dpvs(codol_load_blocks_t *s,const uint8_t *h,int apply)
{
    const uint8_t *p=h+456,*d=h+564,*records;
    uint32_t models=read32(p),surfaces=read32(h+16),i,j;
    uint64_t sorted=(uint64_t)read32(p+4)+read32(p+8);
    if (models>INT32_MAX || surfaces>INT32_MAX || sorted>UINT32_MAX) return 0;
    for (i=0;i<6;++i)
        if (!replay_world_zero(s,read32(p+52+4*i),read32(p+(i<3 ? 0 : 4)),1,1,apply)) return 0;
    if (read32(p+76) && !replay_bytes(s,(uint32_t)sorted,2,2,apply)) return 0;
    if (read32(p+80) && !replay_bytes(s,models,36,4,apply)) return 0;
    if (read32(p+84)) {
        if (!(records=replay_bytes(s,surfaces,24,4,apply))) return 0;
        for (i=0;i<surfaces;++i)
            if (!replay_asset_reference(s,read32(records+(size_t)i*24+16),apply,replay_material)) return 0;
    }
    if (read32(p+88) && !replay_bytes(s,surfaces,24,4,apply)) return 0;
    if (read32(p+92)) {
        uint32_t slots=0x30000001u+(uint32_t)((s->position[3]+3)&~(size_t)3);
        if (!(records=replay_bytes(s,models,76,4,apply))) return 0;
        for (i=0;i<models;++i) {
            uint32_t ref=read32(records+(size_t)i*76+52);
            size_t start=s->source_position;
            if (!replay_asset_reference(s,ref,apply,replay_model)) return 0;
            if (ref>=UINT32_MAX-1 && !record_asset(s,4,slots+76*i+52,start,apply)) return 0;
        }
    }
    if (!replay_world_zero(s,read32(p+96),surfaces,8,8,apply) ||
        !replay_world_zero(s,read32(p+100),read32(p+48),4,128,apply)) return 0;
    for (i=0;i<2;++i)
        if (!replay_world_zero(s,read32(d+16+4*i),(uint64_t)read32(h+52)*read32(d+4*i),4,4,apply)) return 0;
    /* The client interleaves both dynamic categories for each view. */
    for (i=0;i<3;++i) for (j=0;j<2;++j)
        if (!replay_world_zero(s,read32(d+24+12*j+4*i),read32(d+4*j),32,16,apply)) return 0;
    return 1;
}
static int replay_world(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    const uint8_t *h=s->source+s->source_position;
    if (!replay_world_visibility(s,apply,reference) || !replay_world_draw(s,h+80,apply) ||
        !replay_world_light_grid(s,h+152,apply) || !replay_world_scene(s,h,apply) ||
        !replay_world_dpvs(s,h,apply)) return 0;
    if (read32(h+620) && !replay_bytes(s,read32(h+616),56,4,apply)) return 0;
    return CODOL_PopLoadBlock(s);
}
int CODOL_ReplayWorld(codol_load_blocks_t *stream,uint32_t *reference)
{
    codol_load_blocks_t plan;
    uint32_t result;
    unsigned pass;
    if (!stream || !reference || stream->active!=0 || !stream->source ||
        stream->source_position>stream->source_size || stream->depth>=CODOL_LOAD_STACK) return 0;
    for (pass=0;pass<2;++pass) {
        plan=*stream;
        if (!replay_world(&plan,pass,&result)) return 0;
    }
    *stream=plan; *reference=result; return 1;
}
static int replay_world_prefix(codol_load_blocks_t *stream,int draw,uint32_t *reference)
{
    codol_load_blocks_t plan;
    uint32_t result;
    unsigned pass;
    if (!stream || !reference || stream->active!=0 || !stream->source ||
        stream->source_position>stream->source_size || stream->depth>=CODOL_LOAD_STACK) return 0;
    for (pass=0;pass<2;++pass) {
        plan=*stream;
        if (!replay_world_visibility(&plan,pass,&result)) return 0;
        if (draw && !replay_world_draw(&plan,stream->source+stream->source_position+80,pass)) return 0;
        if (draw && !replay_world_light_grid(&plan,stream->source+stream->source_position+152,pass)) return 0;
        if (draw>1 && !replay_world_scene(&plan,stream->source+stream->source_position,pass)) return 0;
    }
    *stream=plan; *reference=result; return 1;
}
int CODOL_ReplayWorldVisibility(codol_load_blocks_t *s,uint32_t *reference)
{ return replay_world_prefix(s,0,reference); }
int CODOL_ReplayWorldDraw(codol_load_blocks_t *s,uint32_t *reference)
{ return replay_world_prefix(s,1,reference); }
int CODOL_ReplayWorldScene(codol_load_blocks_t *s,uint32_t *reference)
{ return replay_world_prefix(s,2,reference); }
/* C1 FxWorld 0x4be220 and glass system 0x4bdb50. Runtime glass arrays
 * live in zero-filled block 2 and therefore consume no serialized bytes. */
static int record_glass_span(codol_load_blocks_t *,int,codol_glass_span_t);
static int replay_effect_world(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    const uint8_t *h=s->source+s->source_position,*g,*defs,*initial=NULL;
    uint64_t sizes[9],pieces,words;
    uint32_t ignored,count,i;
    if (!reserve(s,0,116,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    if (read32(h)==UINT32_MAX && !replay_string(s,apply)) return 0;
    g=h+4; count=read32(g+8);
    if (count>INT32_MAX) return 0;
    if (read32(g+48)) {
        uint32_t slots=0x30000001u+(uint32_t)((s->position[3]+3)&~(size_t)3);
        if (!(defs=replay_bytes(s,count,36,4,apply))) return 0;
        for (i=0;i<count;++i) {
            const uint8_t *d=defs+(size_t)i*36;
            size_t start=s->source_position;
            if (!replay_asset_reference(s,read32(d+32),apply,replay_preset_asset)) return 0;
            if (read32(d+32)>=UINT32_MAX-1 && !record_asset(s,0,slots+36*i+32,start,apply)) return 0;
            if (!replay_asset_reference(s,read32(d+24),apply,replay_material) ||
                !replay_asset_reference(s,read32(d+28),apply,replay_material)) return 0;
        }
    }
    pieces=read32(g+12); words=read32(g+16);
    sizes[0]=pieces*32; sizes[1]=pieces*32; sizes[2]=pieces*36;
    sizes[3]=(uint64_t)read32(g+36)*4; sizes[4]=words*4;
    sizes[5]=words*read32(g+24);
    if (sizes[5]>UINT64_MAX/4) return 0;
    sizes[5]*=4;
    sizes[6]=(pieces+15)&~UINT64_C(15); sizes[7]=pieces*12;
    sizes[8]=((pieces+3)&~UINT64_C(3))*4;
    for (i=0;i<9;++i) {
        if (!CODOL_PushLoadBlock(s,2)) return 0;
        if (read32(g+52+4*i) && (sizes[i]>SIZE_MAX ||
            !reserve(s,2,(size_t)sizes[i],i==6 || i==8 ? 16 : 4,1,apply,&ignored))) return 0;
        if (!CODOL_PopLoadBlock(s)) return 0;
    }
    if (read32(g+88) && !replay_bytes(s,read32(g+20),2,2,apply)) return 0;
    if (read32(g+92) && !(initial=replay_bytes(s,read32(g+20),52,4,apply))) return 0;
    if (!record_glass_span(s,apply,(codol_glass_span_t){
        .world=h,.group=UINT32_MAX-1,.pieces=initial,.piece_count=read32(g+20)})) return 0;
    if (read32(g+96) && !replay_bytes(s,read32(g+44),4,4,apply)) return 0;
    return CODOL_PopLoadBlock(s);
}
/* C1 ComWorld 0x4bfec0 and primary lights 0x4bfe10. */
static int replay_common_world(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    const uint8_t *h=s->source+s->source_position,*lights;
    uint32_t count,i;
    if (!reserve(s,0,16,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    if (read32(h)==UINT32_MAX && !replay_string(s,apply)) return 0;
    count=read32(h+8);
    if (count>INT32_MAX) return 0;
    if (read32(h+12)) {
        if (!(lights=replay_bytes(s,count,68,4,apply))) return 0;
        for (i=0;i<count;++i)
            if (read32(lights+(size_t)i*68+64)==UINT32_MAX && !replay_string(s,apply)) return 0;
    }
    return CODOL_PopLoadBlock(s);
}
/* C1 GfxLightDef 0x4bab40: attenuation image is an asset reference. */
static int replay_light_definition(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    const uint8_t *h=s->source+s->source_position;
    if (!reserve(s,0,16,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    if (read32(h)==UINT32_MAX && !replay_string(s,apply)) return 0;
    if (!replay_asset_reference(s,read32(h+4),apply,replay_image)) return 0;
    return CODOL_PopLoadBlock(s);
}
/* C1 vehicle-track segments 0x4bc520, sectors 0x4bc410 and branch
 * references 0x4bc480. Branches use -1 inline records, not asset wrappers. */
static int replay_vehicle_segment(codol_load_blocks_t *s,const uint8_t *r,unsigned depth,int apply)
{
    const uint8_t *sectors,*refs,*child;
    uint32_t n,i,j;
    if (depth>=CODOL_LOAD_STACK) return 0;
    if (read32(r)==UINT32_MAX && !replay_string(s,apply)) return 0;
    if (read32(r+4)) {
        n=read32(r+8);
        if (n>INT32_MAX || !(sectors=replay_bytes(s,n,60,4,apply))) return 0;
        for (i=0;i<n;++i) {
            const uint8_t *sector=sectors+(size_t)i*60;
            if (read32(sector+52) && !replay_bytes(s,read32(sector+56),12,4,apply)) return 0;
        }
    }
    for (j=12;j<=20;j+=8) if (read32(r+j)) {
        n=read32(r+j+4);
        if (n>INT32_MAX || !(refs=replay_bytes(s,n,4,4,apply))) return 0;
        for (i=0;i<n;++i) if (read32(refs+4*i)==UINT32_MAX) {
            if (!(child=replay_bytes(s,1,44,4,apply)) ||
                !replay_vehicle_segment(s,child,depth+1,apply)) return 0;
        }
    }
    return 1;
}
static int record_glass_span(codol_load_blocks_t *s,int apply,codol_glass_span_t span)
{
    if(!s->collect_asset_aliases) return 1;
    if(apply) {
        if(s->glass_record_count>=s->glass_record_capacity) return 0;
        s->glass_records[s->glass_record_count]=span;
    }
    ++s->glass_record_count;
    return 1;
}
/* C1 GameWorldMp 0x4bca00 and glass data 0x4bc800. */
static int replay_game_world_mp(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    const uint8_t *h=s->source+s->source_position,*records,*glass;
    uint32_t count,i;
    if (!reserve(s,0,84,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    if (read32(h)==UINT32_MAX && !replay_string(s,apply)) return 0;
    if (apply) memset(s->data[0]+((*reference-1)&0x0fffffffu)+4,0,68);
    if (read32(h+72)==UINT32_MAX) {
        count=read32(h+76);
        if (count>INT32_MAX || !(records=replay_bytes(s,count,44,4,apply))) return 0;
        for (i=0;i<count;++i)
            if (!replay_vehicle_segment(s,records+(size_t)i*44,0,apply)) return 0;
    }
    if (!read32(h+80)) {
        if(!record_glass_span(s,apply,(codol_glass_span_t){h,NULL,NULL,NULL,UINT32_MAX,0,0})) return 0;
    } else {
        if (!(glass=replay_bytes(s,1,128,4,apply))) return 0;
        const uint8_t *pieces=NULL;
        if (read32(glass) && !(pieces=replay_bytes(s,read32(glass+4),12,4,apply))) return 0;
        if(!record_glass_span(s,apply,(codol_glass_span_t){
            .world=h,.glass=glass,.group=UINT32_MAX,
            .pieces=pieces,.piece_count=read32(glass+4)})) return 0;
        if (read32(glass+16)) {
            count=read32(glass+12);
            if (count>INT32_MAX || !(records=replay_bytes(s,count,12,4,apply))) return 0;
            for (i=0;i<count;++i) {
                const uint8_t *r=records+(size_t)i*12;
                const char *name=read32(r)==UINT32_MAX?(const char *)(s->source+s->source_position):NULL;
                const uint8_t *ids=NULL;
                if (read32(r)==UINT32_MAX && !replay_string(s,apply)) return 0;
                if (read32(r+8) && !(ids=replay_bytes(s,read16(r+6),2,2,apply))) return 0;
                if(!record_glass_span(s,apply,(codol_glass_span_t){h,glass,ids,name,i,read32(r),read16(r+6)})) return 0;
            }
        }
    }
    return CODOL_PopLoadBlock(s);
}
/* C1 MapEnts 0x4be8c0, triggers 0x4be6f0 and stages 0x4be820.
 * AddonMapEnts 0x4beae0 shares the prefix but has no stages. */
static int replay_map_entities_body(codol_load_blocks_t *s,int apply,uint32_t *reference,int addon)
{
    const uint8_t *h=s->source+s->source_position,*stages;
    static const unsigned strides[3]={8,32,20};
    unsigned i;
    if (!reserve(s,0,addon ? 36 : 44,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    if (read32(h)==UINT32_MAX && !replay_string(s,apply)) return 0;
    if (read32(h+4) && !replay_bytes(s,read32(h+8),1,1,apply)) return 0;
    for (i=0;i<3;++i)
        if (read32(h+16+8*i) && !replay_bytes(s,read32(h+12+8*i),strides[i],4,apply)) return 0;
    if (!addon && read32(h+36)) {
        if (!(stages=replay_bytes(s,h[40],20,4,apply))) return 0;
        for (i=0;i<h[40];++i)
            if (read32(stages+20*i)==UINT32_MAX && !replay_string(s,apply)) return 0;
    }
    return CODOL_PopLoadBlock(s);
}
static int replay_map_entities(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    return replay_map_entities_body(s,apply,reference,0);
}
static int replay_addon_map_entities(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    return replay_map_entities_body(s,apply,reference,1);
}
int CODOL_ReplayMapEntities(codol_load_blocks_t *stream,uint32_t *reference)
{
    codol_load_blocks_t plan;
    uint32_t result;
    unsigned pass;
    if (!stream || !reference || stream->active!=0 || !stream->source ||
        stream->source_position>stream->source_size || stream->depth>=CODOL_LOAD_STACK) return 0;
    for (pass=0;pass<2;++pass) {
        plan=*stream;
        if (!replay_map_entities(&plan,pass,&result)) return 0;
    }
    *stream=plan; *reference=result; return 1;
}
static int replay_collision_planes(codol_load_blocks_t *s,uint32_t count,int apply)
{
    const uint8_t *records=replay_bytes(s,count,8,4,apply);
    uint32_t i;
    if (!records) return 0;
    for (i=0;i<count;++i)
        if (read32(records+(size_t)i*8)==UINT32_MAX && !replay_bytes(s,1,20,4,apply)) return 0;
    return 1;
}
/* C1 clipMap_t 0x4bf410. Count/pointer offsets preserve loader order,
 * including leaf brushes before leaf-brush nodes and MapEnts after static nodes. */
static int replay_collision(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    static const unsigned fields[][5]={
        {16,20,76,4,1},{24,28,12,4,2},{32,36,8,4,3},{40,44,1,1,0},
        {48,52,8,4,3},{56,60,40,4,0},{72,76,2,2,0},{64,68,20,4,4},
        {80,84,4,4,0},{88,92,12,4,0},{96,100,6,2,0},{96,104,4,1,5},
        {108,112,28,4,0},{116,120,12,4,6},{124,128,32,16,0},{132,136,68,4,0},
        {140,144,36,128,7},{140,148,24,128,0},{140,152,4,4,0},{160,164,28,4,0}
    };
    const uint8_t *h=s->source+s->source_position,*records;
    uint32_t count,i,j,k;
    if (!reserve(s,0,256,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    if (read32(h)==UINT32_MAX && !replay_string(s,apply)) return 0;
    if (read32(h+12)==UINT32_MAX && !replay_bytes(s,read32(h+8),20,4,apply)) return 0;
    for (i=0;i<sizeof(fields)/sizeof(fields[0]);++i) if (read32(h+fields[i][1])) {
        unsigned offset=fields[i][0],kind=fields[i][4];
        count=offset==140 || offset==160 ? read16(h+offset) : read32(h+offset);
        if (kind==5) count=(uint32_t)(((uint64_t)count*3+31)/32);
        if (!(records=replay_bytes(s,count,fields[i][2],fields[i][3],apply))) return 0;
        if (kind==0 || kind==5) continue;
        for (j=0;j<count;++j) {
            const uint8_t *r=records+(size_t)j*fields[i][2];
            if (kind==1 && !replay_asset_reference(s,read32(r),apply,replay_model)) return 0;
            if (kind==2 && read32(r)==UINT32_MAX && !replay_string(s,apply)) return 0;
            if (kind==3 && read32(r)==UINT32_MAX && !replay_bytes(s,1,20,4,apply)) return 0;
            if (kind==4 && read16(r+2)>0 && read16(r+2)<32768 && read32(r+8)==UINT32_MAX &&
                !replay_bytes(s,read16(r+2),2,2,apply)) return 0;
            if (kind==6 && read32(r+8)==UINT32_MAX && !replay_bytes(s,1,28,4,apply)) return 0;
            if (kind==7) {
                unsigned edges=0;
                if (read32(r+4)==UINT32_MAX && !replay_collision_planes(s,read16(r),apply)) return 0;
                for (k=30;k<36;++k) edges+=r[k];
                if (read32(r+8)==UINT32_MAX && !replay_bytes(s,edges,1,1,apply)) return 0;
            }
        }
    }
    if (!replay_asset_reference(s,read32(h+156),apply,replay_map_entities)) return 0;
    for (i=0;i<2;++i) if (read32(h+172+4*i)) {
        uint32_t slots=0x30000001u+(uint32_t)((s->position[3]+3)&~(size_t)3);
        count=read16(h+168+2*i);
        if (!(records=replay_bytes(s,count,92,4,apply))) return 0;
        if(s->collect_asset_aliases) {
            if(apply) {
                if(s->dynamic_record_count>=s->dynamic_record_capacity) return 0;
                s->dynamic_records[s->dynamic_record_count]=(codol_dynamic_records_t){h,records,i,count,slots};
            }
            ++s->dynamic_record_count;
        }
        for (j=0;j<count;++j) {
            const uint8_t *r=records+(size_t)j*92;
            size_t start;
            start=s->source_position;
            if (!replay_asset_reference(s,read32(r+32),apply,replay_model)) return 0;
            if (read32(r+32)>=UINT32_MAX-1 && !record_asset(s,4,slots+92*j+32,start,apply)) return 0;
            start=s->source_position;
            if (!replay_asset_reference(s,read32(r+40),apply,replay_effect)) return 0;
            if (read32(r+40)>=UINT32_MAX-1 && !record_asset(s,30,slots+92*j+40,start,apply)) return 0;
            start=s->source_position;
            if (!replay_asset_reference(s,read32(r+44),apply,replay_preset_asset)) return 0;
            if (read32(r+44)>=UINT32_MAX-1 && !record_asset(s,0,slots+92*j+44,start,apply)) return 0;
        }
    }
    for (i=0;i<3;++i) for (j=0;j<2;++j)
        if (!replay_world_zero(s,read32(h+180+8*i+4*j),read16(h+168+2*j),i==0 ? 32 : i==1 ? 12 : 20,4,apply)) return 0;
    return CODOL_PopLoadBlock(s);
}
int CODOL_ReplayCollision(codol_load_blocks_t *stream,uint32_t *reference)
{
    codol_load_blocks_t plan;
    uint32_t result;
    unsigned pass;
    if (!stream || !reference || stream->active!=0 || !stream->source ||
        stream->source_position>stream->source_size || stream->depth>=CODOL_LOAD_STACK) return 0;
    for (pass=0;pass<2;++pass) {
        plan=*stream;
        if (!replay_collision(&plan,pass,&result)) return 0;
    }
    *stream=plan; *reference=result; return 1;
}
/* C1 TracerDef 0x4c23d0: name followed by a material asset reference. */
static int replay_tracer(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    const uint8_t *h=s->source+s->source_position;
    if (!reserve(s,0,112,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    if (read32(h)==UINT32_MAX && !replay_string(s,apply)) return 0;
    if (!replay_asset_reference(s,read32(h+4),apply,replay_material)) return 0;
    return CODOL_PopLoadBlock(s);
}
/* C1 sound-name indirection 0x4b7160. This is a string pointer record,
 * not an inline snd_alias_list_t. Runtime name lookup is separate. */
static int replay_sound_name(codol_load_blocks_t *s,uint32_t ref,int apply)
{
    const uint8_t *name;
    if (ref!=UINT32_MAX) return 1;
    if (!(name=replay_bytes(s,1,4,4,apply))) return 0;
    return read32(name)!=UINT32_MAX || replay_string(s,apply);
}
/* C1 WeaponDef 0x4c2630. Operations retain loader order, especially the
 * interleaved accuracy graph names and point arrays. Script-string indices
 * remain serialized indices until the zone's runtime string pool is bound. */
static int replay_weapon(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    enum { STRING,MODEL,EFFECT,MATERIAL,SOUND,SOUND_ARRAY,POINTS,PHYSICS,TRACER };
    static const unsigned fields[][3]={
        {0,4,STRING},{0x10,11,MODEL},{0x7c,144,STRING},
        {0x35c,2,EFFECT},{0x364,53,SOUND},{0x438,2,SOUND_ARRAY},
        {0x440,4,EFFECT},{0x450,2,MATERIAL},{0x52c,6,MATERIAL},
        {0x548,1,MATERIAL},{0x550,1,MATERIAL},
        {0x564,1,STRING},{0x56c,1,STRING},{0x57c,1,STRING},
        {0x684,4,MATERIAL},{0x758,1,PHYSICS},{0x7b0,1,MODEL},
        {0x7b8,2,EFFECT},{0x7c0,2,SOUND},{0x8cc,2,EFFECT},
        {0x8ec,1,EFFECT},{0x8f0,1,SOUND},{0x9a0,1,STRING},
        {0x9a8,1,POINTS},{0x9a4,1,STRING},{0x9ac,1,POINTS},
        {0x9fc,2,STRING},{0xa20,2,STRING},{0xaa0,2,STRING},
        {0xaa8,1,TRACER},{0xac4,1,SOUND},{0xac8,1,EFFECT},
        {0xacc,1,STRING},{0xadc,9,SOUND},{0xb00,2,SOUND},
        {0xb48,6,SOUND},{0xb78,1,STRING},{0xb84,2,STRING},
        {0xb90,3,MATERIAL},{0xbb4,2,POINTS}
    };
    const uint8_t *h=s->source+s->source_position,*names;
    unsigned i,j,k,offset,kind;
    uint32_t ref;
    if (!reserve(s,0,0xbfc,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    for (i=0;i<sizeof(fields)/sizeof(fields[0]);++i) for (j=0;j<fields[i][1];++j) {
        offset=fields[i][0]+4*j; kind=fields[i][2]; ref=read32(h+offset);
        switch (kind) {
        case STRING: if (ref==UINT32_MAX && !replay_string(s,apply)) return 0; break;
        case MODEL: if (!replay_asset_reference(s,ref,apply,replay_model)) return 0; break;
        case EFFECT: if (!replay_asset_reference(s,ref,apply,replay_effect)) return 0; break;
        case MATERIAL: if (!replay_asset_reference(s,ref,apply,replay_material)) return 0; break;
        case PHYSICS: if (!replay_asset_reference(s,ref,apply,replay_physics_map_asset)) return 0; break;
        case TRACER: if (!replay_asset_reference(s,ref,apply,replay_tracer)) return 0; break;
        case SOUND: if (!replay_sound_name(s,ref,apply)) return 0; break;
        case SOUND_ARRAY:
            if (ref!=UINT32_MAX) break;
            if (!(names=replay_bytes(s,31,4,4,apply))) return 0;
            for (k=0;k<31;++k) if (!replay_sound_name(s,read32(names+4*k),apply)) return 0;
            break;
        case POINTS:
            if (ref==UINT32_MAX && !replay_bytes(s,read16(h+
                (offset==0x9a8 || offset==0xbb4 ? 0xbb0 : 0xbb2)),8,4,apply)) return 0;
            break;
        }
    }
    return CODOL_PopLoadBlock(s);
}
/* C1 menu Statement 0x4c0260, entries 0x4c00c0 and nested statement
 * pointers 0x4c01c0. Statements stay in block 3, including recursion. */
static int replay_menu_expression(codol_load_blocks_t *s,int apply,uint32_t *reference,unsigned depth)
{
    const uint8_t *h=s->source+s->source_position,*entries;
    uint32_t count,i,child;
    if (depth>=CODOL_LOAD_STACK || !reserve(s,3,20,4,1,apply,reference)) return 0;
    if (read32(h+4)) {
        count=read32(h);
        if (count>INT32_MAX || !(entries=replay_bytes(s,count,12,4,apply))) return 0;
        for (i=0;i<count;++i) {
            const uint8_t *r=entries+12*i;
            if (!read32(r) || read32(r+8)!=UINT32_MAX) continue;
            if (read32(r+4)==2 && !replay_string(s,apply)) return 0;
            if (read32(r+4)==3 && !replay_menu_expression(s,apply,&child,depth+1)) return 0;
        }
    }
    return 1;
}
int CODOL_ReplayMenuExpression(codol_load_blocks_t *stream,uint32_t *reference)
{
    codol_load_blocks_t plan;
    uint32_t result;
    unsigned pass;
    if (!stream || !reference || stream->active!=3 || !stream->source ||
        stream->source_position>stream->source_size) return 0;
    for (pass=0;pass<2;++pass) {
        plan=*stream;
        if (!replay_menu_expression(&plan,pass,&result,0)) return 0;
    }
    *stream=plan; *reference=result; return 1;
}
/* C1 menu event sets 0x4c0630, handler pointers 0x4c0570 and tagged
 * payloads 0x4c04b0. Nonzero handler/set pointers are inline, unlike
 * statement pointers, for which only -1 is inline. */
static int replay_menu_events(codol_load_blocks_t *s,int apply,uint32_t *reference,unsigned depth)
{
    const uint8_t *h=s->source+s->source_position,*refs,*event,*payload;
    uint32_t count,i,child;
    unsigned type;
    if (depth>=CODOL_LOAD_STACK || !reserve(s,3,8,4,1,apply,reference)) return 0;
    if (!read32(h+4)) return 1;
    count=read32(h);
    if (count>INT32_MAX || !(refs=replay_bytes(s,count,4,4,apply))) return 0;
    for (i=0;i<count;++i) if (read32(refs+4*i)) {
        if (!(event=replay_bytes(s,1,8,4,apply))) return 0;
        type=event[4];
        if (type==0) {
            if (read32(event)==UINT32_MAX && !replay_string(s,apply)) return 0;
        } else if (read32(event)) {
            if (type==2) {
                if (!replay_menu_events(s,apply,&child,depth+1)) return 0;
            } else if (type==1 || (type>=3 && type<=6)) {
                if (!(payload=replay_bytes(s,1,8,4,apply))) return 0;
                if (type!=1 && read32(payload)==UINT32_MAX && !replay_string(s,apply)) return 0;
                if (read32(payload+4)==UINT32_MAX &&
                    !replay_menu_expression(s,apply,&child,depth+1)) return 0;
                if (type==1 && read32(payload) &&
                    !replay_menu_events(s,apply,&child,depth+1)) return 0;
            }
        }
    }
    return 1;
}
int CODOL_ReplayMenuEvents(codol_load_blocks_t *stream,uint32_t *reference)
{
    codol_load_blocks_t plan;
    uint32_t result;
    unsigned pass;
    if (!stream || !reference || stream->active!=3 || !stream->source ||
        stream->source_position>stream->source_size) return 0;
    for (pass=0;pass<2;++pass) {
        plan=*stream;
        if (!replay_menu_events(&plan,pass,&result,0)) return 0;
    }
    *stream=plan; *reference=result; return 1;
}
/* C1 key handlers 0x4c0980/0x4c0a30 and window dependencies 0x4c08c0. */
static int replay_menu_keys(codol_load_blocks_t *s,int apply)
{
    const uint8_t *key;
    uint32_t child;
    unsigned depth;
    for (depth=0;depth<CODOL_LOAD_STACK;++depth) {
        if (!(key=replay_bytes(s,1,12,4,apply))) return 0;
        if (read32(key+4) && !replay_menu_events(s,apply,&child,depth+1)) return 0;
        if (!read32(key+8)) return 1;
    }
    return 0;
}
static int replay_menu_window(codol_load_blocks_t *s,const uint8_t *h,int apply)
{
    if (read32(h)==UINT32_MAX && !replay_string(s,apply)) return 0;
    if (read32(h+44)==UINT32_MAX && !replay_string(s,apply)) return 0;
    return replay_asset_reference(s,read32(h+160),apply,replay_material);
}
/* C1 itemDef 0x4c0c90 and type-specific data 0x4c0a80. */
static int replay_menu_item(codol_load_blocks_t *s,int apply)
{
    const uint8_t *h,*payload,*expressions;
    uint32_t child,count,type;
    unsigned i;
    if (!(h=replay_bytes(s,1,380,4,apply)) || !replay_menu_window(s,h,apply)) return 0;
    if (read32(h+0xe4)==UINT32_MAX && !replay_string(s,apply)) return 0;
    for (i=0xf0;i<=0x10c;i+=4)
        if (read32(h+i) && !replay_menu_events(s,apply,&child,0)) return 0;
    for (i=0x110;i<=0x114;i+=4)
        if (read32(h+i)==UINT32_MAX && !replay_string(s,apply)) return 0;
    if (read32(h+0x118) && !replay_menu_keys(s,apply)) return 0;
    for (i=0x11c;i<=0x120;i+=4)
        if (read32(h+i)==UINT32_MAX && !replay_string(s,apply)) return 0;
    if (!replay_asset_reference(s,read32(h+0x128),apply,replay_sound_alias)) return 0;
    type=read32(h+0xb8);
    if (read32(h+0x134)) switch (type) {
    case 6:
        if (!(payload=replay_bytes(s,1,324,4,apply))) return 0;
        if (read32(payload+288) && !replay_menu_events(s,apply,&child,0)) return 0;
        if (!replay_asset_reference(s,read32(payload+320),apply,replay_material)) return 0;
        break;
    case 0: case 4: case 9: case 10: case 11: case 14: case 16: case 17: case 18: case 22: case 23:
        if (!replay_bytes(s,1,32,4,apply)) return 0;
        break;
    case 12:
        if (!(payload=replay_bytes(s,1,392,4,apply))) return 0;
        for (i=0;i<64;++i) if (read32(payload+4*i)==UINT32_MAX && !replay_string(s,apply)) return 0;
        break;
    case 13:
        if (read32(h+0x134)==UINT32_MAX && !replay_string(s,apply)) return 0;
        break;
    case 20: if (!replay_bytes(s,1,28,4,apply)) return 0; break;
    case 21: if (!replay_bytes(s,1,4,4,apply)) return 0; break;
    default: break;
    }
    if (read32(h+0x140)) {
        count=read32(h+0x13c);
        if (count>INT32_MAX || !(expressions=replay_bytes(s,count,8,4,apply))) return 0;
        for (i=0;i<count;++i)
            if (read32(expressions+8*i+4)==UINT32_MAX && !replay_menu_expression(s,apply,&child,0)) return 0;
    }
    for (i=0x144;i<=0x150;i+=4)
        if (read32(h+i)==UINT32_MAX && !replay_menu_expression(s,apply,&child,0)) return 0;
    return 1;
}
/* C1 menuDef 0x4c12b0, item pointers 0x4c1230, MenuList 0x4c18c0. */
static int replay_menu(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    static const unsigned events[]={0xd0,0xd8,0xd4,0xdc};
    const uint8_t *h=s->source+s->source_position,*items;
    uint32_t child,count;
    unsigned i;
    if (!reserve(s,0,400,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    if (!replay_menu_window(s,h,apply)) return 0;
    if (read32(h+0xa4)==UINT32_MAX && !replay_string(s,apply)) return 0;
    for (i=0;i<4;++i) if (read32(h+events[i]) && !replay_menu_events(s,apply,&child,0)) return 0;
    if (read32(h+0xe0) && !replay_menu_keys(s,apply)) return 0;
    if (read32(h+0xe4)==UINT32_MAX && !replay_menu_expression(s,apply,&child,0)) return 0;
    for (i=0xe8;i<=0xec;i+=4) if (read32(h+i)==UINT32_MAX && !replay_string(s,apply)) return 0;
    for (i=0x104;i<=0x118;i+=4)
        if (read32(h+i)==UINT32_MAX && !replay_menu_expression(s,apply,&child,0)) return 0;
    if (read32(h+0x11c)) {
        count=read32(h+0xb0);
        if (count>INT32_MAX || !(items=replay_bytes(s,count,4,4,apply))) return 0;
        for (i=0;i<count;++i) if (read32(items+4*i) && !replay_menu_item(s,apply)) return 0;
    }
    return CODOL_PopLoadBlock(s);
}
static int replay_menu_list(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    const uint8_t *h=s->source+s->source_position,*menus;
    uint32_t count,i;
    if (!reserve(s,0,12,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    if (read32(h)==UINT32_MAX && !replay_string(s,apply)) return 0;
    if (read32(h+8)) {
        count=read32(h+4);
        if (count>INT32_MAX || !(menus=replay_bytes(s,count,4,4,apply))) return 0;
        for (i=0;i<count;++i) if (!replay_asset_reference(s,read32(menus+4*i),apply,replay_menu)) return 0;
    }
    return CODOL_PopLoadBlock(s);
}
/* C1 StructuredDataDefSet 0x4c61c0, definitions 0x4c6150/0x4c5fd0,
 * enums 0x4c5e30 and structs 0x4c5f50. Type references remain serialized. */
static int replay_structured_data(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    const uint8_t *h=s->source+s->source_position,*defs,*records,*members;
    uint32_t count,n,m,i,j,k;
    unsigned kind;
    if (!reserve(s,0,12,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    if (read32(h)==UINT32_MAX && !replay_string(s,apply)) return 0;
    if (read32(h+8)) {
        count=read32(h+4);
        if (count>INT32_MAX || !(defs=replay_bytes(s,count,60,4,apply))) return 0;
        for (i=0;i<count;++i) {
            const uint8_t *d=defs+60*i;
            for (kind=0;kind<2;++kind) if (read32(d+12+8*kind)) {
                n=read32(d+8+8*kind);
                if (n>INT32_MAX || !(records=replay_bytes(s,n,kind ? 20 : 12,4,apply))) return 0;
                for (j=0;j<n;++j) {
                    const uint8_t *r=records+j*(kind ? 20 : 12);
                    if (!read32(r+(kind ? 4 : 8))) continue;
                    m=read32(r);
                    if (m>INT32_MAX || !(members=replay_bytes(s,m,kind ? 24 : 8,4,apply))) return 0;
                    for (k=0;k<m;++k)
                        if (read32(members+k*(kind ? 24 : 8))==UINT32_MAX && !replay_string(s,apply)) return 0;
                }
            }
            for (j=24;j<=32;j+=8)
                if (read32(d+j+4) && !replay_bytes(s,read32(d+j),16,4,apply)) return 0;
            if (read32(d+56) && !replay_bytes(s,read32(d+52),4,4,apply)) return 0;
        }
    }
    return CODOL_PopLoadBlock(s);
}
/* C1 LeaderboardDef 0x4c64d0 and columns 0x4c6460/0x4c63c0. */
static int replay_leaderboard(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    const uint8_t *h=s->source+s->source_position,*columns;
    uint32_t count,i;
    if (!reserve(s,0,24,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    if (read32(h)==UINT32_MAX && !replay_string(s,apply)) return 0;
    if (read32(h+20)) {
        count=read32(h+8);
        if (count>INT32_MAX || !(columns=replay_bytes(s,count,32,4,apply))) return 0;
        for (i=0;i<count;++i) {
            if (read32(columns+32*i)==UINT32_MAX && !replay_string(s,apply)) return 0;
            if (read32(columns+32*i+16)==UINT32_MAX && !replay_string(s,apply)) return 0;
        }
    }
    return CODOL_PopLoadBlock(s);
}
/* C1 Font_s 0x4c8c00 and 24-byte glyph array 0x4c8bc0. */
static int replay_font(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    const uint8_t *h=s->source+s->source_position;
    if (!reserve(s,0,24,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    if (read32(h)==UINT32_MAX && !replay_string(s,apply)) return 0;
    if (!replay_asset_reference(s,read32(h+12),apply,replay_material) ||
        !replay_asset_reference(s,read32(h+16),apply,replay_material)) return 0;
    if (read32(h+20)==UINT32_MAX && !replay_bytes(s,read32(h+8),24,4,apply)) return 0;
    return CODOL_PopLoadBlock(s);
}
/* C1 WeaponAttach 0x4c3dd0, field records 0x4c3d00. Types below 16
 * (signed comparison) and type 39 carry strings; other values are scalar. */
static int replay_weapon_attachment(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    const uint8_t *h=s->source+s->source_position,*fields;
    uint32_t count,i,type;
    if (!reserve(s,0,12,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    if (read32(h)==UINT32_MAX && !replay_string(s,apply)) return 0;
    if (read32(h+8)) {
        count=read32(h+4);
        if (count>INT32_MAX || !(fields=replay_bytes(s,count,12,4,apply))) return 0;
        for (i=0;i<count;++i) {
            type=read32(fields+12*i+4);
            if ((type<16 || type>INT32_MAX || type==39) &&
                read32(fields+12*i+8)==UINT32_MAX && !replay_string(s,apply)) return 0;
        }
    }
    return CODOL_PopLoadBlock(s);
}
/* C1 VehicleDef 0x4c4ec0 and embedded vehicle physics 0x4c4e10.
 * Runtime script-string binding and vehicle simulation are separate. */
static int replay_vehicle(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    static const unsigned names[]={0,8,0xac};
    static const unsigned sounds[]={0x1e0,0x1e4,0x1e8,0x1ec,0x1f4,0x1fc,
        0x200,0x204,0x208,0x210,0x218,0x220,0x228,0x230};
    const uint8_t *h=s->source+s->source_position;
    unsigned i;
    if (!reserve(s,0,0x314,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    for (i=0;i<3;++i) if (read32(h+names[i])==UINT32_MAX && !replay_string(s,apply)) return 0;
    if (!replay_asset_reference(s,read32(h+0xb0),apply,replay_preset_asset)) return 0;
    if (read32(h+0xb4)==UINT32_MAX && !replay_string(s,apply)) return 0;
    if (read32(h+0x190)==UINT32_MAX && !replay_string(s,apply)) return 0;
    if (!replay_asset_reference(s,read32(h+0x194),apply,replay_weapon)) return 0;
    for (i=0;i<2;++i) if (!replay_sound_name(s,read32(h+0x1ac+4*i),apply)) return 0;
    for (i=0;i<2;++i) if (!replay_asset_reference(s,read32(h+0x1d0+4*i),apply,replay_material)) return 0;
    for (i=0;i<sizeof(sounds)/sizeof(sounds[0]);++i)
        if (!replay_sound_name(s,read32(h+sounds[i]),apply)) return 0;
    if (read32(h+0x238)==UINT32_MAX && !replay_string(s,apply)) return 0;
    for (i=0;i<31;++i) if (!replay_sound_name(s,read32(h+0x23c+4*i),apply)) return 0;
    return CODOL_PopLoadBlock(s);
}
/* C1 FxImpactTable 0x4c2180/0x4c20c0: 16 records, each with
 * 31 ordinary and four flesh effect references, in serialized order. */
static int replay_impact_table(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    const uint8_t *h=s->source+s->source_position,*effects;
    unsigned i;
    if (!reserve(s,0,8,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    if (read32(h)==UINT32_MAX && !replay_string(s,apply)) return 0;
    if (read32(h+4)) {
        if (!(effects=replay_bytes(s,16,140,4,apply))) return 0;
        for (i=0;i<560;++i)
            if (!replay_asset_reference(s,read32(effects+4*i),apply,replay_effect)) return 0;
    }
    return CODOL_PopLoadBlock(s);
}
/* C1 LocalizeEntry 0x4c1ea0: value followed by key, both strings. */
static int replay_localize(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    const uint8_t *h=s->source+s->source_position;
    if (!reserve(s,0,8,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    if (read32(h)==UINT32_MAX && !replay_string(s,apply)) return 0;
    if (read32(h+4)==UINT32_MAX && !replay_string(s,apply)) return 0;
    return CODOL_PopLoadBlock(s);
}
/* C1 rawfile 0x4c58a0 and StringTable 0x4c5b90. */
static int replay_rawfile(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    const uint8_t *h=s->source+s->source_position;
    uint32_t compressed,length;
    if (!reserve(s,0,16,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    if (read32(h)==UINT32_MAX && !replay_string(s,apply)) return 0;
    compressed=read32(h+4); length=read32(h+8);
    if (compressed>INT32_MAX || length>INT32_MAX) return 0;
    if (read32(h+12) && !replay_bytes(s,compressed ? compressed : length+1,1,1,apply)) return 0;
    return CODOL_PopLoadBlock(s);
}
static int replay_string_table(codol_load_blocks_t *s,int apply,uint32_t *reference)
{
    const uint8_t *h=s->source+s->source_position,*cells;
    uint32_t rows,columns,i;
    uint64_t count;
    if (!reserve(s,0,16,4,1,apply,reference) || !CODOL_PushLoadBlock(s,3)) return 0;
    if (read32(h)==UINT32_MAX && !replay_string(s,apply)) return 0;
    columns=read32(h+4); rows=read32(h+8); count=(uint64_t)columns*rows;
    if (columns>INT32_MAX || rows>INT32_MAX || count>INT32_MAX) return 0;
    if (read32(h+12)) {
        if (!(cells=replay_bytes(s,(uint32_t)count,8,4,apply))) return 0;
        for (i=0;i<count;++i)
            if (read32(cells+8*i)==UINT32_MAX && !replay_string(s,apply)) return 0;
    }
    return CODOL_PopLoadBlock(s);
}
/* C1 DB_LoadXFile 0x4b5fc3..0x4b616b. The XAssetList itself is read
 * externally and does not advance a block cursor. */
int CODOL_BeginZoneReplay(const codol_zone_t *zone,codol_load_blocks_t *out)
{
    codol_load_blocks_t s={0};
    uint32_t capacities[8];
    const uint8_t *strings;
    unsigned i;
    if (!zone || !out || !zone->data || zone->size<56 || zone->size>CODOL_ASSET_LIMIT ||
        zone->table_offset>zone->size || zone->asset_count>(zone->size-zone->table_offset)/16) return 0;
    for (i=0;i<8;++i) {
        if (zone->block_size[i]>0x10000000u) return 0;
        capacities[i]=(zone->block_size[i]+4095u)&~4095u;
    }
    if (!CODOL_InitLoadBlocks(&s,zone->data,zone->size,capacities,0)) return 0;
    s.source_position=56;
    if (!CODOL_PushLoadBlock(&s,3)) goto fail;
    if (read32(zone->data+44)) {
        if (!(strings=replay_bytes(&s,zone->string_count,4,4,1))) goto fail;
        for (i=0;i<zone->string_count;++i)
            if (read32(strings+4*i)==UINT32_MAX && !replay_string(&s,1)) goto fail;
    } else if (zone->string_count) goto fail;
    if (s.source_position!=zone->table_offset) goto fail;
    if (read32(zone->data+52)) {
        s.directory_reference=0x30000001u+(uint32_t)((s.position[3]+3)&~(size_t)3);
        if (!replay_bytes(&s,zone->asset_count,16,4,1)) goto fail;
    } else if (zone->asset_count) goto fail;
    *out=s; return 1;
fail:
    CODOL_FreeLoadBlocks(&s); return 0;
}
static int compare_asset_alias(const void *a,const void *b)
{
    uint32_t x=((const codol_asset_alias_t *)a)->reference;
    uint32_t y=((const codol_asset_alias_t *)b)->reference;
    return (x>y)-(x<y);
}
int CODOL_ReplayZone(const codol_zone_t *zone,codol_load_blocks_t *out,unsigned *failed_asset)
{
    codol_load_blocks_t pending={0};
    unsigned i;
    if (failed_asset) *failed_asset=UINT32_MAX;
    if (!out || !CODOL_BeginZoneReplay(zone,&pending)) return 0;
    pending.collect_asset_aliases=1;
    for (i=0;i<zone->asset_count;++i) if (CODOL_ReplayZoneAsset(zone,i,&pending)!=1) {
        if (failed_asset) *failed_asset=i;
        CODOL_FreeLoadBlocks(&pending); return 0;
    }
    if (pending.source_position!=zone->size) {
        if (failed_asset) *failed_asset=zone->asset_count;
        CODOL_FreeLoadBlocks(&pending); return 0;
    }
    pending.collect_asset_aliases=0;
    if (pending.asset_alias_count>1) qsort(pending.asset_aliases,pending.asset_alias_count,
        sizeof(*pending.asset_aliases),compare_asset_alias);
    *out=pending; return 1;
}
int CODOL_ReplayZoneAsset(const codol_zone_t *zone,unsigned index,codol_load_blocks_t *stream)
{
    codol_load_blocks_t plan;
    const uint8_t *entry;
    uint32_t type,extent,ref;
    unsigned pass;
    int (*loader)(codol_load_blocks_t *,int,uint32_t *);
    if (!zone || !stream || !zone->data || index>=zone->asset_count ||
        stream->source!=zone->data || stream->source_size!=zone->size || stream->active!=3 ||
        zone->table_offset>zone->size || zone->asset_count>(zone->size-zone->table_offset)/16) return -1;
    entry=zone->data+zone->table_offset+16*index;
    type=read32(entry); extent=read32(entry+12); ref=read32(entry+8);
    if ((size_t)read32(entry+4)+40!=stream->source_position ||
        stream->source_position>zone->size || extent>zone->size-stream->source_position) return -1;
    switch (type) {
    case 0: loader=replay_preset_asset; break;
    case 1: loader=replay_physics_map_asset; break;
    case 2: loader=replay_animation; break;
    case 3: loader=replay_surfaces; break;
    case 4: loader=replay_model; break;
    case 5: loader=replay_material; break;
    case 6: case 7: loader=replay_shader_asset; break;
    case 8: loader=replay_declaration_asset; break;
    case 9: loader=replay_technique_set; break;
    case 10: loader=replay_image; break;
    case 11: loader=replay_sound_alias; break;
    case 12: loader=replay_sound_curve; break;
    case 13: loader=replay_loaded_sound; break;
    case 14: case 15: loader=replay_collision; break;
    case 16: loader=replay_common_world; break;
    case 18: loader=replay_game_world_mp; break;
    case 19: loader=replay_map_entities; break;
    case 20: loader=replay_effect_world; break;
    case 21: loader=replay_world; break;
    case 22: loader=replay_light_definition; break;
    case 24: loader=replay_font; break;
    case 25: loader=replay_menu_list; break;
    case 26: loader=replay_menu; break;
    case 27: loader=replay_localize; break;
    case 28: loader=replay_weapon; break;
    /* C1 0x4c8ed0 dispatch has no load operation for these asset families.
     * They may still occur as zero-payload directory records.  Preserve that
     * no-op behavior, but never use it to skip bytes from an unknown layout. */
    case 23: /* ui_map */
    case 29: /* sound-driver globals */
    case 32: /* aitype */
    case 33: /* mptype */
    case 34: /* character */
    case 35: /* xmodelalias */
        return extent==0 ? 1 : -1;
    case 30: loader=replay_effect; break;
    case 31: loader=replay_impact_table; break;
    case 36: loader=replay_rawfile; break;
    case 37: loader=replay_string_table; break;
    case 38: loader=replay_leaderboard; break;
    case 39: loader=replay_structured_data; break;
    case 40: loader=replay_tracer; break;
    case 41: loader=replay_vehicle; break;
    case 42: loader=replay_addon_map_entities; break;
    case 43: loader=replay_weapon_attachment; break;
    default: return 0;
    }
    if (type==4) {
        codol_asset_t asset={4,zone->data+stream->source_position,extent};
        size_t consumed;
        if (!CODOL_ReadXModelExtent(&asset,&consumed) || consumed!=extent) return -1;
    }
    if (ref<UINT32_MAX-1) return -1;
    for (pass=0;pass<2;++pass) {
        plan=*stream;
        /* Restrict reads to this asset even when later asset bytes exist. */
        plan.source_size=stream->source_position+extent;
        if (!replay_asset_reference(&plan,ref,pass,loader) ||
            plan.source_position!=stream->source_position+extent) return -1;
        if ((type<=2 || type==3 || type==4 || type==5 || type==11 || type==12 || type==13 || type==16 || type==18 || type==20 || type==28 || type==30 || type==39 || type==40 || type==41 || type==43) && !record_asset(&plan,type,stream->directory_reference+16*index+8,
            stream->source_position,pass)) return -1;
        if (!pass && plan.asset_alias_count>stream->asset_alias_capacity) {
            size_t capacity=plan.asset_alias_count;
            codol_asset_alias_t *aliases;
            if (capacity>CODOL_ASSET_LIMIT/sizeof(*aliases)) return -1;
            aliases=realloc(stream->asset_aliases,capacity*sizeof(*aliases));
            if (!aliases) return -1;
            stream->asset_aliases=aliases; stream->asset_alias_capacity=capacity;
        }
        if (!pass && plan.sound_record_count>stream->sound_record_capacity) {
            size_t capacity=plan.sound_record_count;
            codol_sound_span_t *records;
            if(capacity>CODOL_ASSET_LIMIT/sizeof(*records)) return -1;
            records=realloc(stream->sound_records,capacity*sizeof(*records));
            if(!records) return -1;
            stream->sound_records=records; stream->sound_record_capacity=capacity;
        }
        if (!pass && plan.glass_record_count>stream->glass_record_capacity) {
            size_t capacity=plan.glass_record_count;
            codol_glass_span_t *records;
            if(capacity>CODOL_ASSET_LIMIT/sizeof(*records)) return -1;
            records=realloc(stream->glass_records,capacity*sizeof(*records));
            if(!records) return -1;
            stream->glass_records=records; stream->glass_record_capacity=capacity;
        }
        if (!pass && plan.dynamic_record_count>stream->dynamic_record_capacity) {
            size_t capacity=plan.dynamic_record_count;
            codol_dynamic_records_t *records;
            if(capacity>CODOL_ASSET_LIMIT/sizeof(*records)) return -1;
            records=realloc(stream->dynamic_records,capacity*sizeof(*records));
            if(!records) return -1;
            stream->dynamic_records=records; stream->dynamic_record_capacity=capacity;
        }
    }
    plan.source_size=stream->source_size; *stream=plan; return 1;
}
static int resolve_asset_alias(const codol_load_blocks_t *s,unsigned type,uint32_t reference,codol_asset_t *out)
{
    size_t lo=0,hi;
    if (!s || !out || !reference || ((reference-1)>>28)!=3) return 0;
    hi=s->asset_alias_count;
    while (lo<hi) {
        size_t mid=lo+(hi-lo)/2;
        if (s->asset_aliases[mid].reference<reference) lo=mid+1;
        else hi=mid;
    }
    if (lo==s->asset_alias_count || s->asset_aliases[lo].reference!=reference ||
        s->asset_aliases[lo].asset.type!=type) return 0;
    *out=s->asset_aliases[lo].asset; return 1;
}
const char *CODOL_LoadBlockString(const codol_load_blocks_t *s,uint32_t reference)
{
    size_t offset,available;
    const uint8_t *p;
    if (!s || !reference || ((reference-1)>>28)!=3 || !s->data[3] ||
        s->written[3]>s->capacity[3]) return NULL;
    offset=(reference-1)&0xfffffff;
    if (offset>=s->written[3]) return NULL;
    p=s->data[3]+offset; available=s->written[3]-offset;
    return memchr(p,0,available) ? (const char *)p : NULL;
}
int CODOL_ResolveMaterialAlias(const codol_load_blocks_t *s,uint32_t ref,codol_asset_t *out)
{ return resolve_asset_alias(s,5,ref,out); }
int CODOL_ResolveWeaponAlias(const codol_load_blocks_t *s,uint32_t ref,codol_asset_t *out)
{ return resolve_asset_alias(s,28,ref,out); }
int CODOL_ResolveSurfaceAlias(const codol_load_blocks_t *s,uint32_t ref,codol_asset_t *out)
{ return resolve_asset_alias(s,3,ref,out); }
int CODOL_ResolveModelAlias(const codol_load_blocks_t *s,uint32_t ref,codol_asset_t *out)
{ return resolve_asset_alias(s,4,ref,out); }
int CODOL_ResolveEffectAlias(const codol_load_blocks_t *s,uint32_t ref,codol_asset_t *out)
{ return resolve_asset_alias(s,30,ref,out); }
int CODOL_ResolvePhysicsAlias(const codol_load_blocks_t *s,unsigned type,uint32_t ref,codol_asset_t *out)
{ return type<=1 && resolve_asset_alias(s,type,ref,out); }
/* Types 11 alias list, 12 curve and 13 loaded sound use directory entries and
 * the alias/sound-file pointer slots recorded during the complete replay. */
int CODOL_ResolveSoundAlias(const codol_load_blocks_t *s,unsigned type,uint32_t ref,codol_asset_t *out)
{ return type>=11 && type<=13 && resolve_asset_alias(s,type,ref,out); }
int CODOL_ResolveSoundSpan(const codol_load_blocks_t *s,uint32_t ref,codol_asset_t *out,unsigned *count)
{
    size_t i;
    if (!s || !out || !ref) return 0;
    for (i=0;i<s->sound_record_count;++i) if (s->sound_records[i].reference==ref) {
        *out=(codol_asset_t){11,s->sound_records[i].source,s->sound_records[i].size};
        if (count) *count=s->sound_records[i].count;
        return 1;
    }
    return 0;
}
int CODOL_ResolveDynamicRecords(const codol_load_blocks_t *s,const codol_asset_t *collision,
    unsigned category,codol_dynamic_records_t *out)
{
    size_t i;
    if(!s || !collision || !out || category>1 ||
        (collision->type!=14 && collision->type!=15) || !collision->data) return 0;
    for(i=0;i<s->dynamic_record_count;++i) {
        const codol_dynamic_records_t *records=s->dynamic_records+i;
        if(records->collision==collision->data && records->category==category) {
            uintptr_t offset;
            if((uintptr_t)records->records<(uintptr_t)collision->data) return 0;
            offset=(uintptr_t)records->records-(uintptr_t)collision->data;
            if(offset>collision->size || records->count>(collision->size-offset)/92) return 0;
            *out=*records; return 1;
        }
    }
    return 0;
}
