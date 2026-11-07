#include "codol_matchdata.h"
#include <string.h>
static codol_client_matchdata_t match;
static struct {unsigned pending;uint32_t last_sent;} delivery[32];
void CODOL_RequestClientMatchData(unsigned client)
{ if(client<32 && match.name[0]) {delivery[client].pending=1;delivery[client].last_sent=0;} }
void CODOL_AcknowledgeClientMatchData(unsigned client)
{ if(client<32)memset(&delivery[client],0,sizeof(delivery[client])); }
int CODOL_ClientMatchDataDue(unsigned client,uint32_t time)
{ return client<32 && delivery[client].pending && (int32_t)(time-delivery[client].last_sent)>=1000; }
void CODOL_ClientMatchDataSent(unsigned client,uint32_t time)
{ if(client<32 && delivery[client].pending)delivery[client].last_sent=time; }
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
void CODOL_ResetClientMatchData(void)
{
    CODOL_FreeStructuredSchema(&match.schema);
    memset(&match,0,sizeof(match));
    memset(delivery,0,sizeof(delivery));
}
int CODOL_SelectClientMatchData(const char *name)
{
    codol_structured_schema_t schema={0};const codol_structured_definition_t *d;
    size_t n;unsigned i;
    if(!name || !*name)return 0;
    for(n=0;n<sizeof(match.name) && name[n];++n) {}
    if(n==sizeof(match.name))return 0;
    if(match.name[0])return same_name(name,match.name);
    if(CODOL_LoadMountedStructuredSchema(name,&schema)!=1) {
        CODOL_FreeStructuredSchema(&schema);return 0;
    }
    if(!schema.count || !schema.definitions)goto fail;
    d=schema.definitions;
    if(d->layout.record_size<8 || d->layout.record_size>sizeof(match.record))goto fail;
    memcpy(match.name,name,n+1);match.schema=schema;
    for(i=0;i<4;++i) {
        match.record[i]=(uint8_t)(d->version>>(8*i));
        match.record[4+i]=(uint8_t)(d->checksum>>(8*i));
    }
    return 1;
fail:
    CODOL_FreeStructuredSchema(&schema);return 0;
}
codol_client_matchdata_t *CODOL_ClientMatchData(void)
{ return match.name[0] ? &match : NULL; }
