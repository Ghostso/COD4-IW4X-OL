#include "codol_profile.h"
#include "codol_stats.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static void put(uint8_t *p,uint32_t v){for(unsigned i=0;i<4;++i)p[i]=(uint8_t)(v>>(8*i));}
int main(void)
{
    uint8_t profile[CODOL_STATS_SIZE]={0},map[12]={8,0,0,0,12,0,0,0,16,0,0,0};
    codol_structured_property_t props[]={{"rank",{0,0},0,{0,0}},{"experience",{0,0},1,{0,0}},{"rankVersion",{0,0},2,{0,0}}};
    codol_structured_struct_t structure={3,20,0,3,props};
    codol_structured_definition_t def={0};codol_structured_schema_t schema={"secure",1,&def};
    const char *cells[]={"maxrank","1","","2","","","","", "0","","0","","","","","2000", "1","","2000","","","","","4000"};
    codol_engine_table_t table={"rank",8,3,cells};int rank=91,xp=92;
    int totals[]={0,1999,2000,3999,4000,0x7fffffff},ranks[]={0,0,1,1,1,1};
    for(unsigned i=0;i<6;++i)assert(CODOL_RankForExperience(&table,totals[i],&rank) && rank==ranks[i]);
    rank=91;assert(!CODOL_RankForExperience(&table,-1,&rank) && rank==91);
    cells[18]="2001";assert(!CODOL_RankForExperience(&table,0,&rank) && rank==91);cells[18]="2000";
    cells[16]="0";assert(!CODOL_RankForExperience(&table,0,&rank) && rank==91);cells[16]="1";
    def.version=11;def.checksum=0x096b8f57;def.root=(codol_structured_type_t){5,0};
    def.struct_count=1;def.structs=&structure;def.layout=(codol_structured_layout_t){map,sizeof(map),20};
    put(profile+4,11);put(profile+8,def.checksum);put(profile+12,2);put(profile+16,500);put(profile+20,2);
    assert(CODOL_ProfileExperience(profile,sizeof(profile),&schema,&table,&rank,&xp) && rank==1 && xp==2500);
    put(profile+16,2500);
    assert(CODOL_ProfileExperience(profile,sizeof(profile),&schema,&table,&rank,&xp) && xp==4500);
    put(profile+20,1);
    assert(CODOL_ProfileExperience(profile,sizeof(profile),&schema,&table,&rank,&xp) && xp==3999);
    put(profile+16,2000);
    assert(CODOL_ProfileExperience(profile,sizeof(profile),&schema,&table,&rank,&xp) && xp==4000);
    put(profile+12,0);put(profile+16,10);
    assert(CODOL_ProfileExperience(profile,sizeof(profile),&schema,&table,&rank,&xp) && rank==0 && xp==10);
    rank=91;xp=92;put(profile+12,3);
    assert(!CODOL_ProfileExperience(profile,sizeof(profile),&schema,&table,&rank,&xp) && rank==91 && xp==92);
    put(profile+12,2);put(profile+20,2);put(profile+16,0x7fffffff);
    assert(!CODOL_ProfileExperience(profile,sizeof(profile),&schema,&table,&rank,&xp) && rank==91 && xp==92);
    puts("PASS: secure rank/XP conversion, version mismatch strict clamp, zero rank and atomic failures");
}
