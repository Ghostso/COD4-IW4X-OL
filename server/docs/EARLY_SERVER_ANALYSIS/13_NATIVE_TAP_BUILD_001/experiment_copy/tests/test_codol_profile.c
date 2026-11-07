#include "codol_profile.h"
#include "codol_stats.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static void put(uint8_t *p,uint32_t v)
{ unsigned i;for(i=0;i<4;++i)p[i]=(uint8_t)(v>>(i*8)); }
static void upload(unsigned client,const uint8_t *p,unsigned count)
{
    unsigned i;CODOL_ResetClientStats(client);
    for(i=0;i<count;++i) {
        size_t n=CODOL_STATS_SIZE-i*CODOL_STATS_CHUNK;
        if(n>CODOL_STATS_CHUNK)n=CODOL_STATS_CHUNK;
        assert(CODOL_AcceptClientStats(client,i,p+i*CODOL_STATS_CHUNK,n));
    }
}
int main(void)
{
    uint8_t data[CODOL_STATS_SIZE]={0},map[4]={8,0,0,0};uint32_t value=123;
    codol_structured_property_t prop={"experience",{0,0},0,{0,0}};
    codol_structured_struct_t structure={1,12,0,1,&prop};
    codol_structured_definition_t defs[2]={{0}};
    codol_structured_schema_t schema={"mp/playerdata.def",2,defs};
    codol_structured_path_t path={"experience",0};
    const codol_structured_definition_t *selected=NULL;const uint8_t *record=NULL;size_t capacity=99;
    defs[1].version=220;defs[1].checksum=0xe4fd5218;defs[1].root=(codol_structured_type_t){5,0};
    defs[1].struct_count=1;defs[1].structs=&structure;
    defs[1].layout=(codol_structured_layout_t){map,4,12};
    put(data+4,220);put(data+8,0xe4fd5218);put(data+12,457750);
    upload(0,data,26);
    assert(!CODOL_ClientProfileScalar(0,&schema,&path,1,&value) && value==123);
    upload(0,data,27);
    assert(CODOL_ClientProfileRecord(0,&schema,&selected,&record,&capacity));
    assert(selected==defs+1 && record==CODOL_ClientStats(0)+4 && capacity==CODOL_STATS_SIZE-4);
    assert(CODOL_ClientProfileScalar(0,&schema,&path,1,&value) && value==457750);
    put(data+12,999);upload(1,data,27);
    assert(CODOL_ClientProfileScalar(1,&schema,&path,1,&value) && value==999);
    assert(CODOL_ClientProfileScalar(0,&schema,&path,1,&value) && value==457750);
    defs[0]=defs[1];assert(!CODOL_ClientProfileRecord(0,&schema,&selected,&record,&capacity));
    assert(selected==defs+1 && record==CODOL_ClientStats(0)+4 && capacity==CODOL_STATS_SIZE-4);
    memset(defs,0,sizeof(defs[0]));defs[1].checksum++;
    assert(!CODOL_ClientProfileScalar(0,&schema,&path,1,&value) && value==457750);
    defs[1].checksum--;defs[1].layout.record_size=CODOL_STATS_SIZE;
    assert(!CODOL_ClientProfileScalar(0,&schema,&path,1,&value));
    CODOL_ResetClientStats(0);CODOL_ResetClientStats(1);
    puts("PASS: profile schema selection, upload prefix, isolation and atomic failures");
}
