#include "codol_matchdata_server.h"
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
static codol_server_matchdata_t match;
static struct {codol_server_matchdata_submission_t view; char name[CODOL_SERVER_MATCHDATA_NAME];} last;
static uint32_t submissions;
static uint32_t u32(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
/* C1 compares definition names with 0x6283d0, which folds ASCII case. */
static int same_name(const char *a,const char *b)
{
    for(;;++a,++b) {
        unsigned char x=*a,y=*b;
        if(x>='A' && x<='Z')x+='a'-'A';
        if(y>='A' && y<='Z')y+='a'-'A';
        if(x!=y)return 0;
        if(!x)return 1;
    }
}
static int usable(const codol_structured_schema_t *s)
{
    const codol_structured_definition_t *d;
    if(!s->count || !s->definitions)return 0;
    d=s->definitions;
    return d->layout.record_size>=8 && d->layout.record_size<=sizeof(match.record);
}
static void store_header(const codol_structured_definition_t *d)
{
    unsigned i;
    for(i=0;i<4;++i) {
        match.record[i]=(uint8_t)(d->version>>(8*i));
        match.record[4+i]=(uint8_t)(d->checksum>>(8*i));
    }
}
static int header_matches(const codol_structured_definition_t *d)
{
    unsigned i;
    for(i=0;i<4;++i)
        if(match.record[i]!=(uint8_t)(d->version>>(8*i)) ||
           match.record[4+i]!=(uint8_t)(d->checksum>>(8*i)))return 0;
    return 1;
}
/* C1 re-resolves the definition asset on every access. The native store caches
 * the decoded schema and reloads it after the archives were released. */
static codol_server_matchdata_t *ensure(void)
{
    codol_structured_schema_t schema={0};
    if(!match.name[0])return NULL;
    if(match.schema.count && match.schema.definitions)return &match;
    if(CODOL_LoadMountedStructuredSchema(match.name,&schema)!=1 || !usable(&schema) ||
       !header_matches(schema.definitions)) {
        CODOL_FreeStructuredSchema(&schema);return NULL;
    }
    match.schema=schema;return &match;
}
codol_matchdata_def_status_t CODOL_SelectServerMatchData(const char *name)
{
    codol_structured_schema_t schema={0};size_t n;
    if(!name)return CODOL_MATCHDATA_DEF_UNAVAILABLE;
    /* C1 0x553c40 compares names before testing whether one was selected.
     * Selecting "" while already empty is consequently a no-op. */
    if(same_name(name,match.name))return CODOL_MATCHDATA_DEF_UNCHANGED;
    if(match.name[0])return CODOL_MATCHDATA_DEF_ALREADY_SET;
    for(n=0;n<sizeof(match.name) && name[n];++n) {}
    if(n==sizeof(match.name))return CODOL_MATCHDATA_DEF_NAME_TOO_LONG;
    if(CODOL_LoadMountedStructuredSchema(name,&schema)!=1 || !schema.count || !schema.definitions) {
        CODOL_FreeStructuredSchema(&schema);return CODOL_MATCHDATA_DEF_UNAVAILABLE;
    }
    if(schema.definitions->layout.record_size>sizeof(match.record)) {
        CODOL_FreeStructuredSchema(&schema);return CODOL_MATCHDATA_DEF_TOO_LARGE;
    }
    if(schema.definitions->layout.record_size<8) {
        CODOL_FreeStructuredSchema(&schema);return CODOL_MATCHDATA_DEF_UNAVAILABLE;
    }
    memcpy(match.name,name,n+1);match.schema=schema;
    store_header(schema.definitions);
    return CODOL_MATCHDATA_DEF_LOADED;
}
codol_server_matchdata_t *CODOL_ServerMatchData(void)
{ return ensure(); }
const char *CODOL_ServerMatchDataDef(void)
{ return match.name[0] ? match.name : NULL; }
void CODOL_ClearServerMatchData(void)
{
    CODOL_FreeStructuredSchema(&match.schema);
    memset(match.record,0,sizeof(match.record));
    match.name[0]=0;
    last.view.record=NULL;last.view.size=0;
}
void CODOL_ReleaseServerMatchDataSchema(void)
{ CODOL_FreeStructuredSchema(&match.schema); }
void CODOL_ResetServerMatchData(void)
{
    CODOL_FreeStructuredSchema(&match.schema);
    memset(&match,0,sizeof(match));
    memset(&last,0,sizeof(last));
    submissions=0;
}
int CODOL_PrepareServerMatchDataSubmission(codol_server_matchdata_submission_t *out)
{
    codol_server_matchdata_t *m=ensure();const codol_structured_definition_t *d;size_t n;
    if(!out || !m)return 0;
    d=m->schema.definitions;
    for(n=0;n<sizeof(last.name)-1 && m->name[n];++n)last.name[n]=m->name[n];
    last.name[n]=0;
    last.view.name=last.name;last.view.version=d->version;last.view.checksum=d->checksum;
    last.view.record=m->record;last.view.id=++submissions;
    /* C1 0x5cf203 accepts only definitions longer than four bytes. */
    last.view.size=d->layout.record_size>4 ? d->layout.record_size : 0;
    *out=last.view;
    return last.view.size ? 1 : -1;
}
const codol_server_matchdata_submission_t *CODOL_LastServerMatchDataSubmission(void)
{ return last.view.record ? &last.view : NULL; }
static codol_server_matchdata_sink_t sink;
static void *sink_context;
void CODOL_SetServerMatchDataSink(codol_server_matchdata_sink_t handler,void *context)
{ sink=handler;sink_context=context; }
int CODOL_DeliverServerMatchData(const codol_server_matchdata_submission_t *submission)
{
    if(!submission || !submission->record || !submission->size)return -1;
    if(!sink)return 0;
    return sink(sink_context,submission) ? 1 : -1;
}
typedef struct {
    codol_matchdata_text_sink_t sink; void *context;
    const codol_structured_definition_t *def; const uint8_t *record;
} report_t;
static void emit(report_t *r,const char *format,...)
{
    char line[1024];int n;va_list args;
    va_start(args,format);n=vsnprintf(line,sizeof(line),format,args);va_end(args);
    if(n<0)return;
    if((size_t)n>=sizeof(line))n=(int)sizeof(line)-1;
    r->sink(r->context,line,(size_t)n);
}
static void dump(report_t *r,codol_structured_type_t type,const char *name,
    unsigned depth,uint32_t logical)
{
    const codol_structured_definition_t *d=r->def;
    char indent[16],child[32];size_t pad=(size_t)depth*2,width,offset;
    uint32_t address,i,step,value;const uint8_t *p;
    if(depth>32 || !name)return;
    if(pad>15)pad=15;
    memset(indent,' ',pad);indent[pad]=0;
    if(type.kind==5) {
        const codol_structured_struct_t *s;
        if(!d->structs || type.index>=d->struct_count)return;
        s=d->structs+type.index;
        if(s->count && !s->properties)return;
        emit(r,"%s%s\n",indent,name);
        for(i=0;i<s->count;++i)
            dump(r,s->properties[i].type,s->properties[i].name,depth+1,
                logical+s->properties[i].logical_index);
        return;
    }
    if(type.kind==6) {
        const codol_structured_array_t *a;
        if(!d->indexed_arrays || type.index>=d->indexed_count)return;
        a=d->indexed_arrays+type.index;step=1;
        if(a->element.kind==5) {
            if(!d->structs || a->element.index>=d->struct_count)return;
            step=d->structs[a->element.index].logical_count;
            if(!step)return;
        }
        emit(r,"%s%s\n",indent,name);
        for(i=0;i<a->count_or_enum;++i) {
            snprintf(child,sizeof(child),"[%u]",i);
            dump(r,a->element,child,depth+1,logical+i*step);
        }
        return;
    }
    if(type.kind==7) {
        const codol_structured_array_t *a;const codol_structured_enum_t *e;
        if(!d->enum_arrays || type.index>=d->enum_array_count)return;
        a=d->enum_arrays+type.index;
        if(!d->enums || a->count_or_enum>=d->enum_count)return;
        e=d->enums+a->count_or_enum;
        if(e->count && !e->members)return;
        step=1;
        if(a->element.kind==5) {
            if(!d->structs || a->element.index>=d->struct_count)return;
            step=d->structs[a->element.index].logical_count;
            if(!step)return;
        }
        emit(r,"%s%s\n",indent,name);
        /* C1's dump (0x62097c) scales the enum value by the element's logical
         * count; its path traversal (0x61f270) adds the value unscaled. */
        for(i=0;i<e->count;++i) {
            if(!e->members[i].name)continue;
            snprintf(child,sizeof(child),"[%s]",e->members[i].name);
            dump(r,a->element,child,depth+1,logical+(e->members[i].value&0xffffu)*step);
        }
        return;
    }
    switch(type.kind) {
    case 0: case 8: width=4;break;
    case 1: case 2: width=1;break;
    case 3: width=type.index;if(!width)return;break;
    case 4: if(!d->enums || type.index>=d->enum_count)return;width=2;break;
    case 9: width=2;break;
    default:return;
    }
    if(!d->layout.offset_map || d->layout.offset_map_size%4 ||
       logical>=d->layout.offset_map_size/4)return;
    address=u32(d->layout.offset_map+(size_t)logical*4);
    offset=type.kind==2 ? address>>3 : address;
    if(offset>d->layout.record_size || width>d->layout.record_size-offset)return;
    p=r->record+offset;
    switch(type.kind) {
    case 0: {
        int32_t integer;value=u32(p);memcpy(&integer,&value,4);
        emit(r,"%s%s\t= %d\n",indent,name,integer);break;
    }
    case 1: emit(r,"%s%s\t= %d\n",indent,name,(int)*p);break;
    case 2: emit(r,"%s%s\t= %s\n",indent,name,
        (*p&(uint8_t)(1u<<(address&7))) ? "true" : "false");break;
    case 3:
        if(!memchr(p,0,width))return;
        emit(r,"%s%s\t= \"%s\"\n",indent,name,(const char *)p);break;
    case 4: {
        const codol_structured_enum_t *e=d->enums+type.index;
        if(e->count && !e->members)return;
        value=(uint32_t)p[0]|(uint32_t)p[1]<<8;
        for(i=0;i<e->count;++i)
            if(e->members[i].name && (e->members[i].value&0xffffu)==value) {
                emit(r,"%s%s\t= %s\n",indent,name,e->members[i].name);return;
            }
        break;
    }
    case 8: {
        float number;value=u32(p);memcpy(&number,&value,4);
        emit(r,"%s%s\t= %f\n",indent,name,(double)number);break;
    }
    case 9: {
        int16_t shortint=(int16_t)((uint16_t)p[0]|(uint16_t)p[1]<<8);
        emit(r,"%s%s\t= %i\n",indent,name,(int)shortint);break;
    }
    default:break;
    }
}
int CODOL_WriteServerMatchDataReport(codol_matchdata_text_sink_t text,void *context)
{
    codol_server_matchdata_t *m=ensure();report_t r;
    if(!text || !m)return 0;
    r.sink=text;r.context=context;r.def=m->schema.definitions;r.record=m->record;
    dump(&r,r.def->root,"Root",1,0);
    return 1;
}
