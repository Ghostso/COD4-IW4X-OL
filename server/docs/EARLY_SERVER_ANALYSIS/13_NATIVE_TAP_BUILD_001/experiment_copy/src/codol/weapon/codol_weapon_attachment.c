/* CoDOL weaponattach overrides applied to an owned serialized weapon image.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_weapon_attachment.h"
#include <stdlib.h>
#include <string.h>
#include <math.h>
enum { CODOL_ATTACH_TEXT_MAX=1024 };
static uint32_t load32(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static void store32(uint8_t *p,uint32_t v)
{ p[0]=(uint8_t)v; p[1]=(uint8_t)(v>>8); p[2]=(uint8_t)(v>>16); p[3]=(uint8_t)(v>>24); }
static float load_float(const uint8_t *p)
{ uint32_t v=load32(p); float f; memcpy(&f,&v,4); return f; }
static void store_float(uint8_t *p,float f)
{ uint32_t v; memcpy(&v,&f,4); store32(p,v); }
static char *duplicate(const char *text)
{
    char *copy; size_t length;
    if(!text) return NULL;
    length=strlen(text)+1; copy=malloc(length);
    if(copy) memcpy(copy,text,length);
    return copy;
}
/* Serialized value strings exist for the kinds C1's entry loader 0x4c3d00
 * reads as XStrings: every kind below 0x10 and the hide-tag kind. */
static int kind_has_text(uint32_t type)
{ return type<CODOL_ATTACH_TEXT_LIMIT || type==CODOL_ATTACH_HIDE_TAG; }
static int kind_is_scalar(uint32_t type)
{ return type>=CODOL_ATTACH_INT && type<=CODOL_ATTACH_MILLISECONDS; }
int CODOL_ReadWeaponAttachment(const char *name,codol_weapon_attachment_t *out)
{
    codol_mounted_weapon_attachment_t source;
    codol_weapon_attachment_t result={0};
    uint32_t i; int status;
    if(!name || !*name || !out) return -1;
    status=CODOL_LoadMountedWeaponAttachment(name,&source);
    if(status!=1) return status;
    if(source.count) {
        result.entries=calloc(source.count,sizeof(*result.entries));
        if(!result.entries) { CODOL_FreeMountedWeaponAttachment(&source); return -1; }
    }
    for(i=0;i<source.count;++i) {
        const uint8_t *p=source.entries+12*i;
        codol_weapon_attachment_entry_t *entry=result.entries+i;
        entry->offset=load32(p); entry->type=load32(p+4); entry->value=load32(p+8);
        entry->text=source.texts ? source.texts[i] : NULL;
        /* A null reference is a null value, never an empty string; a resolved
         * string on a kind that carries none means the reader disagrees with
         * the loader about the entry layout. */
        if(entry->text && (!kind_has_text(entry->type) || !entry->value)) break;
        if(!entry->text && entry->value && kind_has_text(entry->type)) break;
    }
    if(i!=source.count) {
        free(result.entries); CODOL_FreeMountedWeaponAttachment(&source); return -1;
    }
    result.asset=source.asset; result.name=source.name; result.count=source.count;
    CODOL_FreeMountedWeaponAttachment(&source);
    *out=result; return 1;
}
void CODOL_FreeWeaponAttachment(codol_weapon_attachment_t *attachment)
{
    if(!attachment) return;
    free(attachment->entries);
    memset(attachment,0,sizeof(*attachment));
}
static void free_image(codol_weapon_source_image_t *image)
{
    size_t i;
    if(!image) return;
    if(image->names) {
        for(i=0;i<image->name_count;++i) free(image->names[i].owned);
        free(image->names);
    }
    for(i=0;i<CODOL_WEAPON_SOURCE_TAGS;++i) free(image->owned_tags[i]);
    free(image->data); free(image->scalar);
    memset(image,0,sizeof(*image));
}
void CODOL_FreeWeaponSourceImage(codol_weapon_source_image_t *image)
{ free_image(image); }
static int copy_image(const codol_weapon_source_image_t *source,codol_weapon_source_image_t *out)
{
    codol_weapon_source_image_t result=*source;
    size_t i;
    result.data=NULL; result.scalar=NULL; result.names=NULL;
    memset(result.owned_tags,0,sizeof(result.owned_tags));
    result.data=malloc(source->size); result.scalar=malloc(source->size);
    if(source->name_count) result.names=calloc(source->name_count,sizeof(*result.names));
    if(!result.data || !result.scalar || (source->name_count && !result.names)) {
        free_image(&result); return 0;
    }
    memcpy(result.data,source->data,source->size);
    memcpy(result.scalar,source->scalar,source->size);
    for(i=0;i<source->name_count;++i) {
        result.names[i]=source->names[i];
        if(!source->names[i].owned) continue;
        result.names[i].owned=duplicate(source->names[i].owned);
        if(!result.names[i].owned) { result.name_count=i+1; free_image(&result); return 0; }
        result.names[i].name=result.names[i].owned;
    }
    for(i=0;i<CODOL_WEAPON_SOURCE_TAGS;++i) {
        if(!source->owned_tags[i]) continue;
        result.owned_tags[i]=duplicate(source->owned_tags[i]);
        if(!result.owned_tags[i]) { free_image(&result); return 0; }
        result.hide_tags[i]=result.owned_tags[i];
    }
    *out=result; return 1;
}
static void push_name(codol_weapon_source_image_t *image,size_t *count,uint32_t offset,const char *name)
{
    image->names[*count].offset=offset;
    image->names[*count].name=name;
    image->names[*count].owned=NULL;
    ++*count;
}
int CODOL_BeginWeaponSourceImage(const char *name,codol_weapon_source_image_t *out)
{
    codol_mounted_weapon_t source; codol_weapon_animations_t animations;
    codol_weapon_effects_t effects; codol_weapon_sounds_t sounds;
    codol_weapon_ammo_names_t ammo; codol_weapon_visuals_t visuals;
    codol_weapon_tail_t tail; codol_weapon_hide_tags_t tags;
    codol_weapon_source_image_t image={0};
    size_t capacity=0,count=0,i,length; int status;
    if(!name || !*name || !out) return -1;
    status=CODOL_LoadMountedWeapon(name,&source);
    if(status!=1) return status;
    if(!source.asset.data || source.asset.size<CODOL_WEAPON_SOURCE_HEADER ||
       !source.strings[0] || !*source.strings[0]) return -1;
    if(CODOL_LoadMountedWeaponAnimations(name,&animations)!=1 ||
       CODOL_LoadMountedWeaponEffects(name,&effects)!=1 ||
       CODOL_LoadMountedWeaponSounds(name,&sounds)!=1 ||
       CODOL_LoadMountedWeaponAmmoNames(name,&ammo)!=1 ||
       CODOL_LoadMountedWeaponVisuals(name,&visuals)!=1 ||
       CODOL_LoadMountedWeaponTail(name,&tail)!=1 ||
       CODOL_LoadMountedWeaponHideTags(name,&tags)!=1) return -1;
    if(tail.count>64) return -1;
    capacity=4+11+144+2+53+3+14+tail.count;
    image.names=calloc(capacity,sizeof(*image.names));
    image.data=malloc(source.asset.size);
    image.scalar=calloc(1,source.asset.size);
    if(!image.names || !image.data || !image.scalar) { free_image(&image); return -1; }
    memcpy(image.data,source.asset.data,source.asset.size);
    image.size=source.asset.size;
    image.base=source.strings[0];
    image.dependency_offset=source.dependency_offset;
    image.tail=tail; image.visuals=visuals; image.effects=effects;
    for(i=0;i<4;++i) push_name(&image,&count,(uint32_t)(4*i),source.strings[i]);
    for(i=0;i<11;++i) {
        codol_weapon_model_t model={0};
        status=CODOL_LoadMountedWeaponModel(name,(unsigned)i,&model);
        if(status<0) { free_image(&image); return -1; }
        model.asset.type=4;
        image.models[i]=model;
        push_name(&image,&count,(uint32_t)(0x10+4*i),status==1 ? model.name : NULL);
    }
    for(i=0;i<144;++i) push_name(&image,&count,(uint32_t)(0x7c+4*i),animations.names[i]);
    for(i=0;i<2;++i) push_name(&image,&count,(uint32_t)(0x35c+4*i),effects.names[i]);
    for(i=0;i<53;++i) push_name(&image,&count,(uint32_t)(0x364+4*i),sounds.names[i]);
    memcpy(image.sound_arrays,sounds.arrays,sizeof(image.sound_arrays));
    push_name(&image,&count,0x564,ammo.ammo);
    push_name(&image,&count,0x56c,ammo.clip);
    push_name(&image,&count,0x57c,ammo.shared_cap);
    for(i=0;i<14;++i) push_name(&image,&count,visuals.entries[i].offset,visuals.entries[i].name);
    for(i=0;i<tail.count;++i)
        if(tail.entries[i].kind!=CODOL_WEAPON_DEP_POINTS)
            push_name(&image,&count,tail.entries[i].offset,tail.entries[i].name);
    image.name_count=count;
    /* Only the fixed header holds scalars, and only outside the slots the
     * mounted readers resolve: those dwords are serialized references, and the
     * 32 halfwords at +0x3c are zone-local script-string indices. */
    memset(image.scalar,1,CODOL_WEAPON_SOURCE_HEADER);
    memset(image.scalar+0x3c,0,0x40);
    /* These are pointers to 31 sound references, not scalar fields or single
     * name slots. Preserve their resolved contents separately above. */
    memset(image.scalar+0x438,0,8);
    /* Graph arrays have no name to override, but their pointers must also
     * remain protected from scalar writes. */
    for(i=0;i<tail.count;++i) if(tail.entries[i].kind==CODOL_WEAPON_DEP_POINTS) {
        unsigned offset=tail.entries[i].offset;
        if(offset>CODOL_WEAPON_SOURCE_HEADER-4) { free_image(&image); return -1; }
        memset(image.scalar+offset,0,4);
    }
    for(i=0;i<count;++i) {
        uint32_t offset=image.names[i].offset;
        if(offset+4>CODOL_WEAPON_SOURCE_HEADER) { free_image(&image); return -1; }
        memset(image.scalar+offset,0,4);
    }
    /* C1 0x421737: the <w> token is the base internal name in a 0x40 buffer,
     * with a trailing "_mp" removed (0x42175d). */
    length=strlen(image.base);
    if(length>=sizeof(image.context)) length=sizeof(image.context)-1;
    memcpy(image.context,image.base,length); image.context[length]=0;
    if(length>=3 && !strcmp(image.context+length-3,"_mp")) image.context[length-3]=0;
    for(i=0;i<CODOL_WEAPON_SOURCE_TAGS;++i) image.hide_tags[i]=tags.names[i];
    free_image(out); *out=image; return 1;
}
int CODOL_WeaponSourceName(const codol_weapon_source_image_t *image,unsigned offset,const char **out)
{
    size_t i;
    if(!image || !out) return 0;
    for(i=0;i<image->name_count;++i) if(image->names[i].offset==offset) {
        *out=image->names[i].name; return 1;
    }
    return 0;
}
int CODOL_WeaponSourceAnimations(const codol_weapon_source_image_t *image,codol_weapon_animations_t *out)
{
    codol_weapon_animations_t result={0}; unsigned i;
    if(!image || !out) return -1;
    for(i=0;i<144;++i)
        if(CODOL_WeaponSourceName(image,0x7c+4*i,result.names+i)!=1) return -1;
    *out=result; return 1;
}
int CODOL_WeaponSourceAmmoNames(const codol_weapon_source_image_t *image,codol_weapon_ammo_names_t *out)
{
    codol_weapon_ammo_names_t result={0};
    if(!image || !out ||
       CODOL_WeaponSourceName(image,0x564,&result.ammo)!=1 ||
       CODOL_WeaponSourceName(image,0x56c,&result.clip)!=1 ||
       CODOL_WeaponSourceName(image,0x57c,&result.shared_cap)!=1) return -1;
    *out=result; return 1;
}
int CODOL_WeaponSourceSounds(const codol_weapon_source_image_t *image,codol_weapon_sounds_t *out)
{
    codol_weapon_sounds_t result={0}; unsigned i;
    if(!image || !out) return -1;
    for(i=0;i<53;++i)
        if(CODOL_WeaponSourceName(image,0x364+4*i,result.names+i)!=1) return -1;
    memcpy(result.arrays,image->sound_arrays,sizeof(result.arrays));
    *out=result; return 1;
}
static void invalidate_renamed_asset(const char *before,const char *after,codol_asset_t *asset)
{
    if((before==NULL)!=(after==NULL) || (before && after && strcmp(before,after))) {
        asset->data=NULL; asset->size=0;
    }
}
int CODOL_WeaponSourceModel(const codol_weapon_source_image_t *image,unsigned index,codol_weapon_model_t *out)
{
    codol_weapon_model_t result; const char *name;
    if(!image || !image->data || !out || index>=11 ||
       CODOL_WeaponSourceName(image,0x10+4*index,&name)!=1) return -1;
    if(!name) return 0;
    if(!*name) return -1;
    result=image->models[index];
    invalidate_renamed_asset(result.name,name,&result.asset);
    result.name=name; *out=result; return 1;
}
int CODOL_WeaponSourceEffects(const codol_weapon_source_image_t *image,codol_weapon_effects_t *out)
{
    codol_weapon_effects_t result; unsigned i;
    if(!image || !image->data || !out) return -1;
    result=image->effects; result.dependency_offset=0;
    for(i=0;i<2;++i) {
        const char *name;
        if(CODOL_WeaponSourceName(image,0x35c+4*i,&name)!=1) return -1;
        invalidate_renamed_asset(result.names[i],name,result.assets+i);
        result.assets[i].type=30; result.names[i]=name;
    }
    *out=result; return 1;
}
static int image_dependency(const codol_weapon_source_image_t *image,codol_weapon_dependency_t *entry)
{
    const char *name=NULL;
    if(entry->kind==CODOL_WEAPON_DEP_POINTS) {
        unsigned count_offset,count;
        switch(entry->offset) {
        case 0x9a8: case 0xbb4: count_offset=0xbb0; break;
        case 0x9ac: case 0xbb8: count_offset=0xbb2; break;
        default: return 0;
        }
        /* Both graph pairs share count fields. A null array stays absent
         * even if the corresponding array in the other pair has knots. */
        if(!entry->points) return entry->point_count==0;
        if(image->size<count_offset+2) return 0;
        count=image->data[count_offset]|(unsigned)image->data[count_offset+1]<<8;
        /* A scalar override may shorten a graph, but cannot create knots
         * beyond the array captured from the defining archive. */
        if(count>entry->point_count) return 0;
        entry->point_count=count; return 1;
    }
    if(CODOL_WeaponSourceName(image,entry->offset,&name)!=1) return 0;
    if(entry->kind==CODOL_WEAPON_DEP_ASSET)
        invalidate_renamed_asset(entry->name,name,&entry->asset);
    entry->name=name; return 1;
}
int CODOL_WeaponSourceTail(const codol_weapon_source_image_t *image,codol_weapon_tail_t *out)
{
    codol_weapon_tail_t result; unsigned i;
    if(!image || !image->data || !out || image->tail.count>64) return -1;
    result=image->tail; result.dependency_offset=0;
    for(i=0;i<result.count;++i)
        if(!image_dependency(image,result.entries+i)) return -1;
    *out=result; return 1;
}
int CODOL_WeaponSourceVisuals(const codol_weapon_source_image_t *image,codol_weapon_visuals_t *out)
{
    codol_weapon_visuals_t result; unsigned i;
    if(!image || !image->data || !out) return -1;
    result=image->visuals; result.dependency_offset=0;
    for(i=0;i<14;++i)
        if(!image_dependency(image,result.entries+i)) return -1;
    *out=result; return 1;
}
int CODOL_WeaponSourceHideTags(const codol_weapon_source_image_t *image,codol_weapon_hide_tags_t *out)
{
    codol_weapon_hide_tags_t result={0}; unsigned i;
    if(!image || !image->data || !out) return 0;
    for(i=0;i<CODOL_WEAPON_SOURCE_TAGS;++i) result.names[i]=image->hide_tags[i];
    *out=result; return 1;
}
int CODOL_WeaponSourceView(const codol_weapon_source_image_t *image,codol_mounted_weapon_t *out)
{
    codol_mounted_weapon_t result={0}; unsigned i;
    if(!image || !image->data || !out) return 0;
    result.asset.type=28; result.asset.data=image->data; result.asset.size=image->size;
    for(i=0;i<4;++i) if(!CODOL_WeaponSourceName(image,4*i,result.strings+i)) return 0;
    if(!result.strings[0] || !*result.strings[0]) return 0;
    result.dependency_offset=image->dependency_offset;
    *out=result; return 1;
}
/* C1 0x41ee30. Returns the operand, or null when the entry carries no value or
 * a prefix this reader will not read past. C1 never checks the closing bracket
 * and would read beyond the terminator for a truncated prefix; a prefix that
 * is not "[<op>]" or "[f<op>]" is rejected here instead. */
static const char *parse_operator(const char *text,uint32_t type,char *op,char *forced)
{
    size_t next;
    *op=0; *forced=0;
    if(type>=CODOL_ATTACH_TEXT_LIMIT || !text || !*text) return NULL;
    if(text[0]!='[') {
        *op=kind_is_scalar(type) ? '=' : '!';
        return text;
    }
    if(!text[1]) return NULL;
    *forced=text[1]=='f';
    if(*forced && !text[2]) return NULL;
    *op=text[1+(*forced?1:0)];
    next=(size_t)(2+(*forced?1:0));
    if(text[next]!=']') return NULL;
    ++next;
    /* One separator between the prefix and the operand is consumed. */
    if(text[next]) ++next;
    return text+next;
}
static int is_text_operator(char op)
{ return op=='s' || op=='r' || op=='a' || op=='!'; }
/* C1 0x41eaf0: "<w>" becomes the base name, "<uw>" its uppercase. A token is
 * at most three characters; anything else between the brackets is dropped. */
static int expand_text(const char *text,const char *context,char *out,size_t capacity)
{
    size_t used=0;
    if(!text) text="";
    while(*text) {
        char token[4]; unsigned length=0; const char *selector; char mask;
        if(*text!='<') {
            if(used+1>=capacity) return 0;
            out[used++]=*text++; continue;
        }
        ++text;
        while(*text && *text!='>' && length<3) token[length++]=*text++;
        token[length]=0;
        if(*text) ++text;
        selector=token; mask=(char)0xff;
        if(token[0]=='u') { selector=token+1; mask=(char)~0x20; }
        if(*selector!='w') continue;
        for(selector=context;*selector;++selector) {
            if(used+1>=capacity) return 0;
            out[used++]=(char)(*selector&mask);
        }
    }
    out[used]=0; return 1;
}
/* C1 0x41ebc0. 's' and '!' set, 'a' appends, 'r' replaces every occurrence of
 * the first token of the expanded operand with its remainder. */
static int apply_text_operator(char op,const char *current,const char *operand,
    const char *context,char *out,size_t capacity)
{
    char expanded[CODOL_ATTACH_TEXT_MAX];
    const char *from,*to; size_t used=0,length;
    if(!expand_text(operand,context,expanded,sizeof(expanded))) return 0;
    if(!current) current="";
    if(op=='s' || op=='!') {
        length=strlen(expanded);
        if(length+1>capacity) return 0;
        memcpy(out,expanded,length+1); return 1;
    }
    if(op=='a') {
        length=strlen(current)+strlen(expanded);
        if(length+1>capacity) return 0;
        strcpy(out,current); strcat(out,expanded); return 1;
    }
    if(op!='r') return 0;
    from=expanded;
    for(length=0;expanded[length] && expanded[length]!=' ';++length);
    to=expanded[length] ? expanded+length+1 : expanded+length;
    expanded[length]=0;
    while(*current) {
        if(*from && !strncmp(current,from,length)) {
            size_t replacement=strlen(to);
            if(used+replacement+1>capacity) return 0;
            memcpy(out+used,to,replacement); used+=replacement; current+=length;
            continue;
        }
        if(used+1>=capacity) return 0;
        out[used++]=*current++;
    }
    out[used]=0; return 1;
}
static int store_name(codol_weapon_source_image_t *image,uint32_t offset,const char *text)
{
    size_t i;
    for(i=0;i<image->name_count;++i) {
        char *owned;
        if(image->names[i].offset!=offset) continue;
        owned=duplicate(text);
        if(!owned) return 0;
        free(image->names[i].owned);
        image->names[i].owned=owned; image->names[i].name=owned; return 1;
    }
    return 0;
}
static int writable(const codol_weapon_source_image_t *image,uint32_t offset,size_t width)
{
    size_t i;
    if(offset>image->size || image->size-offset<width) return 0;
    for(i=0;i<width;++i) if(!image->scalar[offset+i]) return 0;
    return 1;
}
/* C1 0x41eea0 and 0x41eed0, over the base value, the value the previous
 * entries left and the parsed operand. */
static uint32_t apply_int_operator(char op,uint32_t base,uint32_t current,uint32_t value)
{
    /* C1 ADD/IMUL retain the low 32 bits (41eeb8..41eeca). Unsigned
     * arithmetic preserves that behavior without C signed-overflow UB. */
    if(op=='%') return base*value+current;
    if(op=='*') return current*value;
    if(op=='+') return current+value;
    return value;
}
static float apply_float_operator(char op,float base,float current,float value)
{
    if(op=='%') return base*value+current;
    if(op=='*') return current*value;
    if(op=='+') return current+value;
    return value;
}
static uint32_t parse_integer_operand(const char *text)
{
    /* C1 atoi ada2a7 -> ada291 -> add142 -> adcf17 uses signed base 10
     * and clamps at 32-bit limits (add0b7..add110). A host long can be
     * 64 bits, so narrowing strtol's result would wrap instead of clamp.
     * strtoll also preserves leading whitespace/sign, trailing text and
     * the no-digits result; its own overflow limits lie outside int32. */
    long long value=strtoll(text,NULL,10);
    if(value>INT32_MAX) return UINT32_C(0x7fffffff);
    if(value<INT32_MIN) return UINT32_C(0x80000000);
    return (uint32_t)value;
}
static uint32_t parse_millisecond_operand(const char *text)
{
    /* C1 420c81..420c8f: atof * double 1000, then ae0410. Its SSE2
     * path rounds to double and CVTTSD2SI converts to signed int32.
     * ae49d9 initializes the path selector using IsProcessorFeaturePresent
     * (10); this server already requires SSE2 in COMMON_FLAGS. Do not use
     * an unchecked C cast for NaN, infinity or out-of-range values. */
    double value=trunc(strtod(text,NULL)*1000.0);
    if(!(value>=(double)INT32_MIN && value<=(double)INT32_MAX))
        return UINT32_C(0x80000000);
    return (uint32_t)(int32_t)value;
}
static int apply_scalar(codol_weapon_source_image_t *image,const codol_weapon_source_image_t *base,
    const codol_weapon_attachment_entry_t *entry,char op,const char *operand)
{
    uint32_t offset=entry->offset;
    switch(entry->type) {
    case CODOL_ATTACH_BOOL:
        if(!writable(image,offset,1)) return -1;
        image->data[offset]=operand[0]=='1'; return 0;
    case CODOL_ATTACH_QBOOL:
        if(!writable(image,offset,4)) return -1;
        store32(image->data+offset,operand[0]=='1' ? 0x01010101u : 0); return 0;
    case CODOL_ATTACH_INT: case CODOL_ATTACH_MILLISECONDS: {
        uint32_t value=entry->type==CODOL_ATTACH_INT ? parse_integer_operand(operand)
            : parse_millisecond_operand(operand);
        if(!writable(image,offset,4)) return -1;
        store32(image->data+offset,apply_int_operator(op,
            load32(base->data+offset),load32(image->data+offset),value));
        return 0;
    }
    case CODOL_ATTACH_FLOAT: case CODOL_ATTACH_INCHES: {
        double parsed=strtod(operand,NULL);
        float value=(float)(entry->type==CODOL_ATTACH_INCHES ? parsed*17.6 : parsed);
        if(!writable(image,offset,4)) return -1;
        store_float(image->data+offset,apply_float_operator(op,
            load_float(base->data+offset),load_float(image->data+offset),value));
        return 0;
    }
    default: break;
    }
    return -1;
}
/* C1 0x420930: the tag is appended to the first free of the 32 slots and
 * dropped when they are full. */
static int append_hide_tag(codol_weapon_source_image_t *image,const codol_weapon_attachment_entry_t *entry)
{
    unsigned i;
    if(!entry->text || !*entry->text) return -1;
    for(i=0;i<CODOL_WEAPON_SOURCE_TAGS;++i) {
        char *owned;
        if(image->hide_tags[i]) continue;
        owned=duplicate(entry->text);
        if(!owned) return -1;
        image->owned_tags[i]=owned; image->hide_tags[i]=owned; return 0;
    }
    return 0;
}
/* C1 0x4208e0. 1 deferred to the group applier, 0 applied or ignored,
 * -1 malformed. */
static int apply_entry(codol_weapon_source_image_t *image,const codol_weapon_source_image_t *base,
    const codol_weapon_attachment_entry_t *entry,int defer,char *op_out,char *forced_out)
{
    char op,forced,buffer[CODOL_ATTACH_TEXT_MAX];
    const char *operand,*current=NULL;
    if(entry->type>=CODOL_ATTACH_TEXT_LIMIT) {
        if(entry->type==CODOL_ATTACH_HIDE_TAG) return append_hide_tag(image,entry);
        if(!writable(image,entry->offset,4)) return -1;
        store32(image->data+entry->offset,entry->value); return 0;
    }
    if(!entry->text || !*entry->text) return 0;
    operand=parse_operator(entry->text,entry->type,&op,&forced);
    if(!operand) return -1;
    if(!*operand) return 0;
    if(is_text_operator(op)) {
        if(defer) {
            if(op_out) *op_out=op;
            if(forced_out) *forced_out=forced;
            return 1;
        }
        if(!kind_is_scalar(entry->type)) {
            if(!CODOL_WeaponSourceName(image,entry->offset,&current)) return -1;
            if(!apply_text_operator(op,current,operand,image->context,buffer,sizeof(buffer))) return -1;
            /* C1 0x420e60 trims ".map" from the result and stores no field. */
            if(entry->type==CODOL_ATTACH_MAP) return 0;
            return store_name(image,entry->offset,buffer) ? 0 : -1;
        }
        /* A text operator on a scalar kind reaches the scalar handler with the
         * operand, not with the operator's result (C1 0x420aea). */
    } else if(!kind_is_scalar(entry->type)) {
        /* C1 would consume a buffer it never filled; reject instead. */
        return -1;
    }
    return apply_scalar(image,base,entry,op,operand);
}
typedef struct {
    uint32_t offset;
    char op,forced;
    const codol_weapon_attachment_entry_t *entry;
    const codol_weapon_attachment_t *attachment;
} deferred_t;
/* C1 0x420f10. Offset, then forced entries, then the set/replace precedence,
 * then the serialized value. C1 does not order a second set operator against a
 * differing operator; that fallthrough is preserved. */
static int compare_records(const deferred_t *a,const deferred_t *b)
{
    if(a->offset!=b->offset) return a->offset<b->offset ? -1 : 1;
    if(!a->forced!=!b->forced) return a->forced ? -1 : 1;
    /* C1 420f47 jumps directly to its zero return for equal operators. */
    if(a->op==b->op) return 0;
    if(a->op!=b->op) {
        if(a->op=='!' || a->op=='s') return -1;
        if(b->op=='!') return 1;
        if(a->op=='r') return -1;
        if(b->op=='r') return 1;
    }
    return strcmp(a->entry->text,b->entry->text);
}
static void swap_records(deferred_t **order,ptrdiff_t a,ptrdiff_t b)
{
    deferred_t *value=order[a]; order[a]=order[b]; order[b]=value;
}
/* C1 421979 calls its CRT sorter ada970, not a stable sort. Preserve its
 * comparison and swap order: equal operators compare equal, and their order
 * determines which set/forced entry apply_group keeps. Indices avoid forming
 * pointers outside the array during the partition's sentinel scans. */
static void sort_record_range(deferred_t **order,ptrdiff_t low,ptrdiff_t high)
{
    while(low<high) {
        ptrdiff_t middle,left,right;
        if(high-low+1<=8) {
            /* ada8e0: first maximum wins ties, then swaps to the last slot. */
            while(high>low) {
                ptrdiff_t i,maximum=low;
                for(i=low+1;i<=high;++i)
                    if(compare_records(order[i],order[maximum])>0) maximum=i;
                swap_records(order,maximum,high--);
            }
            return;
        }
        middle=low+(high-low+1)/2;
        if(compare_records(order[low],order[middle])>0) swap_records(order,low,middle);
        if(compare_records(order[low],order[high])>0) swap_records(order,low,high);
        if(compare_records(order[middle],order[high])>0) swap_records(order,middle,high);
        left=low; right=high;
        for(;;) {
            /* adaab0..adaaf5: do not compare the pivot against itself. */
            if(middle>left) {
                do { ++left; }
                while(left<middle && compare_records(order[left],order[middle])<=0);
            }
            if(middle<=left) {
                do { ++left; }
                while(left<=high && compare_records(order[left],order[middle])<=0);
            }
            do { --right; }
            while(right>middle && compare_records(order[right],order[middle])>0);
            if(left>right) break;
            swap_records(order,left,right);
            if(middle==right) middle=left;
        }
        /* adab2d..adab66 skips the equal run before the left partition. */
        ++right;
        if(middle<right) {
            do { --right; }
            while(right>middle && compare_records(order[right],order[middle])==0);
        }
        if(middle>=right) {
            do { --right; }
            while(right>low && compare_records(order[right],order[middle])==0);
        }
        /* Process the smaller range first, as the CRT's explicit stack does.
         * Tail iteration over the larger range bounds recursion depth. */
        if(right-low>=high-left) {
            if(left<high) sort_record_range(order,left,high);
            high=right;
        } else {
            if(low<right) sort_record_range(order,low,right);
            low=left;
        }
    }
}
static void sort_records(deferred_t **order,size_t count)
{
    if(count>1) sort_record_range(order,0,(ptrdiff_t)count-1);
}
/* Both halves of one replace operand, expanded. */
static int split_replacement(const deferred_t *record,const char *context,char *buffer,
    size_t capacity,const char **from,const char **to)
{
    char op,forced; const char *operand; size_t length;
    operand=parse_operator(record->entry->text,record->entry->type,&op,&forced);
    if(!operand || !expand_text(operand,context,buffer,capacity)) return 0;
    for(length=0;buffer[length] && buffer[length]!=' ';++length);
    *to=buffer[length] ? buffer+length+1 : buffer+length;
    buffer[length]=0; *from=buffer;
    return 1;
}
/* C1 0x420fb0: case-insensitive containment. An empty needle is contained. */
static int contains_text(const char *haystack,const char *needle)
{
    size_t i,j;
    if(!haystack || !needle) return 0;
    if(!*needle) return 1;
    for(i=0;haystack[i];++i) {
        for(j=0;needle[j];++j) {
            char a=haystack[i+j],b=needle[j];
            if(a>='A' && a<='Z') a=(char)(a+0x20);
            if(b>='A' && b<='Z') b=(char)(b+0x20);
            if(a!=b) break;
        }
        if(!needle[j]) return 1;
    }
    return 0;
}
static int apply_deferred(codol_weapon_source_image_t *image,const codol_weapon_source_image_t *base,
    const deferred_t *record)
{ return apply_entry(image,base,record->entry,0,NULL,NULL)>=0; }
/* C1 0x4210c0, over one offset's records in comparator order. */
static int apply_group(codol_weapon_source_image_t *image,const codol_weapon_source_image_t *base,
    deferred_t *const *group,size_t count)
{
    size_t index=0,limit,candidate,outer,inner;
    if(group[0]->forced) {
        if(!apply_deferred(image,base,group[0])) return 0;
        /* Every further forced entry for this field is ignored. */
        for(index=1;index<count && group[index]->forced;++index);
        return 1;
    }
    if(index<count && (group[index]->op=='!' || group[index]->op=='s')) {
        if(!apply_deferred(image,base,group[index])) return 0;
        ++index;
        /* Only one set command survives. */
        while(index<count && (group[index]->op=='!' || group[index]->op=='s')) ++index;
    }
    for(limit=index;limit<count && group[limit]->op=='r';++limit);
    for(candidate=index;candidate<limit;++candidate) {
        int clash=0;
        for(outer=candidate;outer+1<limit && !clash;++outer) {
            char first[CODOL_ATTACH_TEXT_MAX],second[CODOL_ATTACH_TEXT_MAX];
            const char *outer_from,*outer_to,*inner_from,*inner_to;
            if(!split_replacement(group[outer],image->context,first,sizeof(first),
                &outer_from,&outer_to)) return 0;
            for(inner=outer+1;inner<limit && !clash;++inner) {
                if(!split_replacement(group[inner],image->context,second,sizeof(second),
                    &inner_from,&inner_to)) return 0;
                /* A replace whose result feeds a later replace, or whose search
                 * text a later replace produces, is order dependent: C1 drops
                 * the earlier one. */
                if(contains_text(inner_from,outer_to) || contains_text(outer_from,inner_to)) clash=1;
            }
        }
        if(!clash && !apply_deferred(image,base,group[candidate])) return 0;
    }
    for(index=limit;index<count;++index)
        if(!apply_deferred(image,base,group[index])) return 0;
    return 1;
}
int CODOL_ApplyWeaponAttachments(codol_weapon_source_image_t *image,
    const codol_weapon_attachment_t *const *attachments,unsigned count)
{
    codol_weapon_source_image_t scratch={0};
    deferred_t *records=NULL,**order=NULL;
    size_t total=0,used=0,start,end;
    unsigned i,j; int status=-1;
    if(!image || !image->data || !image->scalar || (count && !attachments)) return -1;
    for(i=0;i<count;++i) {
        if(!attachments[i] || (attachments[i]->count && !attachments[i]->entries)) return -1;
        if(attachments[i]->count>(size_t)PTRDIFF_MAX-total) return -1;
        total+=attachments[i]->count;
    }
    if(!copy_image(image,&scratch)) return -1;
    if(total) {
        records=calloc(total,sizeof(*records));
        order=calloc(total,sizeof(*order));
        if(!records || !order) goto done;
    }
    /* First pass, in definition order: scalar, raw and hide-tag entries are
     * applied as they are read; text operators are collected. */
    for(i=0;i<count;++i) for(j=0;j<attachments[i]->count;++j) {
        const codol_weapon_attachment_entry_t *entry=attachments[i]->entries+j;
        char op=0,forced=0;
        int result=apply_entry(&scratch,image,entry,1,&op,&forced);
        if(result<0) goto done;
        if(result!=1) continue;
        records[used].offset=entry->offset; records[used].op=op;
        records[used].forced=forced; records[used].entry=entry;
        records[used].attachment=attachments[i];
        order[used]=records+used; ++used;
    }
    sort_records(order,used);
    for(start=0;start<used;start=end) {
        for(end=start+1;end<used && order[end]->offset==order[start]->offset;++end);
        if(!apply_group(&scratch,image,order+start,end-start)) goto done;
    }
    free_image(image); *image=scratch;
    memset(&scratch,0,sizeof(scratch));
    status=1;
done:
    free(records); free(order); free_image(&scratch);
    return status;
}
