#include "codol_profile.h"
#include "codol_stats.h"
#include <assert.h>
#include <string.h>
#include <stdio.h>
#include <math.h>
static void put(uint8_t *p,uint32_t v){for(unsigned i=0;i<4;++i)p[i]=(uint8_t)(v>>(8*i));}
int main(void)
{
    uint8_t profile[CODOL_STATS_SIZE]={0},map[4000]={0};
    codol_structured_property_t prop={"challenges",{6,0},0,{0,0}};
    codol_structured_struct_t structure={1,4008,0,1000,&prop};
    codol_structured_array_t array={1000,{8,0},4};
    codol_structured_definition_t def={0};
    codol_structured_schema_t schema={"mp/playersecuredata.def",1,&def};
    const char *cells[23];for(unsigned i=0;i<23;++i)cells[i]="";
    cells[0]="ch_ghillie";cells[4]="60";cells[6]="50";cells[8]="100";cells[10]="200";
    codol_engine_table_t table={"mp/allChallengesTable.csv",23,1,cells};
    def.version=11;def.checksum=0x096b8f57;def.root=(codol_structured_type_t){5,0};
    def.struct_count=1;def.structs=&structure;def.indexed_count=1;def.indexed_arrays=&array;
    def.layout=(codol_structured_layout_t){map,sizeof(map),4008};
    for(unsigned i=0;i<1000;++i)put(map+4*i,8+4*i);
    put(profile+4,11);put(profile+8,0x096b8f57);
    float samples[]={0,49.5f,50,99.5f,100,199.5f,200,10000};
    int expected[]={1,1,2,2,3,3,4,4},value=0;
    for(unsigned i=0;i<8;++i) {
        memcpy(profile+12+60*4,&samples[i],4);
        assert(CODOL_ProfileChallengeState(profile,sizeof(profile),&schema,&table,"ch_ghillie",&value));
        assert(value==expected[i]);
    }
    value=91;float bad=NAN;memcpy(profile+12+60*4,&bad,4);
    assert(!CODOL_ProfileChallengeState(profile,sizeof(profile),&schema,&table,"ch_ghillie",&value) && value==91);
    bad=50;memcpy(profile+12+60*4,&bad,4);cells[8]="49";
    assert(!CODOL_ProfileChallengeState(profile,sizeof(profile),&schema,&table,"ch_ghillie",&value) && value==91);
    cells[8]="100";cells[4]="1000";
    assert(!CODOL_ProfileChallengeState(profile,sizeof(profile),&schema,&table,"ch_ghillie",&value) && value==91);
    cells[4]="60";profile[4]=12;
    assert(!CODOL_ProfileChallengeState(profile,sizeof(profile),&schema,&table,"ch_ghillie",&value) && value==91);
    puts("PASS: CoDOL numeric challenge progress to IW4 tier, mapped profile access and atomic failures");
}
