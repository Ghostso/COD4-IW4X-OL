#include "codol_profile.h"
#include "codol_stats.h"
#include <assert.h>
#include <stdio.h>
int main(void)
{
    uint8_t profile[CODOL_STATS_SIZE]={0};profile[4]=11;profile[8]=1;
    codol_structured_definition_t def={0};def.version=11;def.checksum=1;def.layout.record_size=8;
    codol_structured_schema_t schema={"synthetic",1,&def};
    const char *cells[]={"free","feature","","", "ranked","feature","4","", "title","title","",""};
    codol_engine_table_t table={"unlock",4,3,cells};int value=91;
    assert(CODOL_ProfileItemUnlocked(profile,sizeof(profile),&schema,&table,NULL,NULL,"FREE",&value) && value==1);
    assert(CODOL_ProfileItemUnlocked(profile,sizeof(profile),&schema,&table,NULL,NULL,"absent",&value) && value==1);
    value=91;
    assert(!CODOL_ProfileItemUnlocked(profile,sizeof(profile),&schema,&table,NULL,NULL,"ranked",&value) && value==91);
    assert(CODOL_ProfileItemUnlocked(profile,sizeof(profile),&schema,&table,NULL,NULL,"title",&value) && value==1);
    value=91;cells[10]="4";
    assert(!CODOL_ProfileItemUnlocked(profile,sizeof(profile),&schema,&table,NULL,NULL,"title",&value) && value==91);
    cells[4]="FREE";
    assert(!CODOL_ProfileItemUnlocked(profile,sizeof(profile),&schema,&table,NULL,NULL,"free",&value) && value==91);
    profile[4]=12;
    assert(!CODOL_ProfileItemUnlocked(profile,sizeof(profile),&schema,&table,NULL,NULL,"absent",&value) && value==91);
    puts("PASS: composed unlock lookup case-folding, missing-row behavior and unavailable-data preservation");
}
