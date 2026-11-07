#include "codol_structured_schema.h"
#include <stdlib.h>
#include <string.h>
typedef struct {const uint8_t *data; size_t size,pos; const char *(*resolve)(void *,uint32_t); void *context;} stream_t;
static uint32_t u32(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
const char *CODOL_StructuredStatusText(int status)
{
    switch(status) {
    case CODOL_STRUCTURED_TYPE: return "Incorrect data type";
    case CODOL_STRUCTURED_BOUNDS: return "Index is outside array bounds";
    case CODOL_STRUCTURED_NAME: return "Name is not a property of the current struct";
    case CODOL_STRUCTURED_ENUM: return "String is not an entry of the required enum";
    case CODOL_STRUCTURED_CHANGED: return "Value changed";
    case CODOL_STRUCTURED_UNCHANGED: return "Value set, no change";
    case CODOL_STRUCTURED_BYTE_RANGE: return "Given int value is too large to fit in a byte";
    case CODOL_STRUCTURED_STRING_LENGTH: return "String is too long";
    }
    return "Incorrect data type";
}
int CODOL_ResolveStructuredFieldStatus(const codol_structured_definition_t *d,
    const codol_structured_path_t *path,size_t count,codol_structured_field_t *out,int *status)
{
    codol_structured_type_t type; uint64_t logical=0; size_t n,width,offset;
    uint32_t address; int state=CODOL_STRUCTURED_TYPE;
    if(!d || !out || (count && !path) || !d->layout.offset_map ||
       d->layout.offset_map_size%4)goto fail;
    type=d->root;
    for(n=0;n<count;++n) {
        uint32_t i; uint64_t step=1; const codol_structured_array_t *a;
        if(type.kind==5) {
            const codol_structured_struct_t *s;
            if(!path[n].name || !d->structs || type.index>=d->struct_count)goto fail;
            s=d->structs+type.index;
            if(s->count && !s->properties)goto fail;
            for(i=0;i<s->count;++i)
                if(s->properties[i].name && !strcmp(path[n].name,s->properties[i].name))break;
            if(i==s->count){state=CODOL_STRUCTURED_NAME;goto fail;}
            logical+=s->properties[i].logical_index; type=s->properties[i].type;
        } else if(type.kind==6) {
            if(path[n].name || path[n].index<0 || !d->indexed_arrays ||
               type.index>=d->indexed_count)goto fail;
            a=d->indexed_arrays+type.index;
            if((uint32_t)path[n].index>=a->count_or_enum){state=CODOL_STRUCTURED_BOUNDS;goto fail;}
            if(a->element.kind==5) {
                if(!d->structs || a->element.index>=d->struct_count)goto fail;
                step=d->structs[a->element.index].logical_count;
                if(!step)goto fail;
            }
            logical+=step*(uint32_t)path[n].index; type=a->element;
        } else if(type.kind==7) {
            const codol_structured_enum_t *e;
            if(!path[n].name || !d->enum_arrays || type.index>=d->enum_array_count)goto fail;
            a=d->enum_arrays+type.index;
            if(!d->enums || a->count_or_enum>=d->enum_count)goto fail;
            e=d->enums+a->count_or_enum;
            if(e->count && !e->members)goto fail;
            for(i=0;i<e->count;++i)
                if(e->members[i].name && !strcmp(path[n].name,e->members[i].name))break;
            if(i==e->count){state=CODOL_STRUCTURED_ENUM;goto fail;}
            /* C1 loads a word at enum entry+4, not the serialized byte stride. */
            logical+=e->members[i].value&0xffffu; type=a->element;
        } else goto fail;
        if(logical>UINT32_MAX || logical>=d->layout.offset_map_size/4){state=CODOL_STRUCTURED_BOUNDS;goto fail;}
    }
    switch(type.kind) {
    case 0: case 8: width=4;break;
    case 1: case 2: width=1;break;
    case 3: width=type.index;if(!width)goto fail;break;
    case 4: if(!d->enums || type.index>=d->enum_count)goto fail; width=2;break;
    case 9: width=2;break;
    default:goto fail;
    }
    if(logical>=d->layout.offset_map_size/4){state=CODOL_STRUCTURED_BOUNDS;goto fail;}
    address=u32(d->layout.offset_map+(size_t)logical*4);
    offset=type.kind==2 ? address>>3 : address;
    if(offset>d->layout.record_size || width>d->layout.record_size-offset){state=CODOL_STRUCTURED_BOUNDS;goto fail;}
    *out=(codol_structured_field_t){type,(uint32_t)logical,address};
    if(status)*status=CODOL_STRUCTURED_OK;
    return 1;
fail:
    if(status)*status=state;
    return 0;
}
int CODOL_ResolveStructuredField(const codol_structured_definition_t *d,
    const codol_structured_path_t *path,size_t count,codol_structured_field_t *out)
{ return CODOL_ResolveStructuredFieldStatus(d,path,count,out,NULL); }
int CODOL_StructuredReadText(const codol_structured_definition_t *d,
    const codol_structured_path_t *path,size_t count,const uint8_t *record,
    size_t capacity,const char **out)
{
    codol_structured_field_t f;const uint8_t *p;uint32_t i,value;
    if(!record || !out || !d || capacity<d->layout.record_size ||
       !CODOL_ResolveStructuredField(d,path,count,&f))return 0;
    if(f.type.kind!=3 && f.type.kind!=4)return 0;
    p=record+f.mapped_address;
    if(f.type.kind==3) {
        if(!memchr(p,0,f.type.index))return 0;
        *out=(const char *)p;return 1;
    }
    if(f.type.kind==4) {
        const codol_structured_enum_t *e=d->enums+f.type.index;
        if(e->count && !e->members)return 0;
        value=(uint32_t)p[0]|(uint32_t)p[1]<<8;
        for(i=0;i<e->count;++i)if((e->members[i].value&0xffffu)==value && e->members[i].name) {
            *out=e->members[i].name;return 1;
        }
    }
    return 0;
}
int CODOL_StructuredWriteText(const codol_structured_definition_t *d,
    const codol_structured_path_t *path,size_t count,uint8_t *record,
    size_t capacity,const char *value)
{
    codol_structured_field_t f;size_t n;uint32_t i,v;
    if(!record || !value || !d || capacity<d->layout.record_size ||
       !CODOL_ResolveStructuredField(d,path,count,&f))return 0;
    if(f.type.kind==3) {
        for(n=0;n<f.type.index && value[n];++n) {}
        if(n==f.type.index)return 0;
        memmove(record+f.mapped_address,value,n+1);return 1;
    }
    if(f.type.kind==4) {
        const codol_structured_enum_t *e=d->enums+f.type.index;
        if(e->count && !e->members)return 0;
        for(i=0;i<e->count;++i)if(e->members[i].name && !strcmp(value,e->members[i].name)) {
            v=e->members[i].value;
            record[f.mapped_address]=(uint8_t)v;
            record[f.mapped_address+1]=(uint8_t)(v>>8);return 1;
        }
    }
    return 0;
}
static const uint8_t *take(stream_t *s,uint32_t count,size_t stride)
{
    const uint8_t *p;
    if(count>(s->size-s->pos)/stride) return NULL;
    p=s->data+s->pos; s->pos+=(size_t)count*stride; return p;
}
static const char *name(stream_t *s,uint32_t reference)
{
    const uint8_t *end; const char *p;
    if(reference!=UINT32_MAX) return reference && s->resolve ? s->resolve(s->context,reference) : NULL;
    end=memchr(s->data+s->pos,0,s->size-s->pos); if(!end)return NULL;
    p=(const char *)(s->data+s->pos); s->pos=(size_t)(end-s->data)+1; return p;
}
static int array_ref(uint32_t count,uint32_t reference)
{ return count ? reference==UINT32_MAX : reference==0 || reference==UINT32_MAX; }
void CODOL_FreeStructuredSchema(codol_structured_schema_t *schema)
{
    uint32_t i,j;
    if(!schema)return;
    for(i=0;i<schema->count && schema->definitions;++i) {
        codol_structured_definition_t *d=schema->definitions+i;
        for(j=0;j<d->enum_count && d->enums;++j)free(d->enums[j].members);
        for(j=0;j<d->struct_count && d->structs;++j)free(d->structs[j].properties);
        free(d->enums);free(d->structs);free(d->indexed_arrays);free(d->enum_arrays);
    }
    free(schema->definitions);memset(schema,0,sizeof(*schema));
}
int CODOL_ReadStructuredSchema(const codol_asset_t *asset,const char *(*resolver)(void *,uint32_t),
    void *context,codol_structured_schema_t *out)
{
    stream_t s; codol_structured_schema_t result={0}; const uint8_t *header,*defs; uint32_t i,j,k;
    if(!asset || !out || asset->type!=39 || !asset->data || asset->size<12 || asset->size>CODOL_ASSET_LIMIT)return 0;
    s=(stream_t){asset->data,asset->size,0,resolver,context}; header=take(&s,1,12);
    result.name=name(&s,u32(header));result.count=u32(header+4);
    if(!result.name || !*result.name || !array_ref(result.count,u32(header+8)) ||
       !(defs=take(&s,result.count,60)))goto fail;
    if(result.count && !(result.definitions=calloc(result.count,sizeof(*result.definitions))))goto fail;
    for(i=0;i<result.count;++i) {
        const uint8_t *raw=defs+i*60,*records,*members;
        codol_structured_definition_t *d=result.definitions+i;
        d->version=u32(raw);d->checksum=u32(raw+4);
        d->root=(codol_structured_type_t){u32(raw+40),u32(raw+44)};
        d->layout.record_size=u32(raw+48);
        d->enum_count=u32(raw+8);d->struct_count=u32(raw+16);
        if(!array_ref(d->enum_count,u32(raw+12)) || !(records=take(&s,d->enum_count,12)))goto fail;
        if(d->enum_count && !(d->enums=calloc(d->enum_count,sizeof(*d->enums))))goto fail;
        for(j=0;j<d->enum_count;++j) {
            const uint8_t *r=records+j*12; codol_structured_enum_t *e=d->enums+j;
            e->count=u32(r);
            if(!array_ref(e->count,u32(r+8)) || !(members=take(&s,e->count,8)))goto fail;
            if(e->count && !(e->members=calloc(e->count,sizeof(*e->members))))goto fail;
            for(k=0;k<e->count;++k) {
                e->members[k].name=name(&s,u32(members+k*8));e->members[k].value=u32(members+k*8+4);
                if(!e->members[k].name)goto fail;
            }
        }
        if(!array_ref(d->struct_count,u32(raw+20)) || !(records=take(&s,d->struct_count,20)))goto fail;
        if(d->struct_count && !(d->structs=calloc(d->struct_count,sizeof(*d->structs))))goto fail;
        for(j=0;j<d->struct_count;++j) {
            const uint8_t *r=records+j*20;codol_structured_struct_t *t=d->structs+j;
            t->count=u32(r);t->size=u32(r+8);t->bit_offset=u32(r+12);t->logical_count=u32(r+16);
            if(!array_ref(t->count,u32(r+4)) || !(members=take(&s,t->count,24)))goto fail;
            if(t->count && !(t->properties=calloc(t->count,sizeof(*t->properties))))goto fail;
            for(k=0;k<t->count;++k) {
                const uint8_t *m=members+k*24;codol_structured_property_t *p=t->properties+k;
                p->name=name(&s,u32(m));p->type=(codol_structured_type_t){u32(m+4),u32(m+8)};
                p->logical_index=u32(m+12);p->extra[0]=u32(m+16);p->extra[1]=u32(m+20);
                if(!p->name || !*p->name)goto fail;
            }
        }
        for(j=0;j<2;++j) {
            uint32_t count=u32(raw+24+j*8);codol_structured_array_t *arrays;
            if(!array_ref(count,u32(raw+28+j*8)) || !(records=take(&s,count,16)))goto fail;
            arrays=count ? calloc(count,sizeof(*arrays)) : NULL;if(count && !arrays)goto fail;
            if(j) {d->enum_array_count=count;d->enum_arrays=arrays;}
            else {d->indexed_count=count;d->indexed_arrays=arrays;}
            for(k=0;k<count;++k) arrays[k]=(codol_structured_array_t){u32(records+k*16),
                {u32(records+k*16+4),u32(records+k*16+8)},u32(records+k*16+12)};
        }
        k=u32(raw+52);
        if(!array_ref(k,u32(raw+56)) || !(d->layout.offset_map=take(&s,k,4)))goto fail;
        d->layout.offset_map_size=(size_t)k*4;
    }
    if(s.pos!=s.size)goto fail;
    CODOL_FreeStructuredSchema(out);*out=result;return 1;
fail: CODOL_FreeStructuredSchema(&result);return 0;
}
