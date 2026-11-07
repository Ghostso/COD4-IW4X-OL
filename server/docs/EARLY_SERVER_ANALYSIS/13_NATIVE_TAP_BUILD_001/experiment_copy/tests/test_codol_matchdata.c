#include "codol_matchdata.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
static unsigned size=858,loads;
int CODOL_LoadMountedStructuredSchema(const char *name,codol_structured_schema_t *s)
{
    ++loads;
    if(!strcmp(name,"missing"))return 0;
    s->count=1;s->definitions=calloc(1,sizeof(*s->definitions));assert(s->definitions);
    s->definitions[0].version=16;s->definitions[0].checksum=0x3fd7bbad;
    s->definitions[0].layout.record_size=size;
    return 1;
}
int main(void)
{
    codol_client_matchdata_t *m;unsigned i;
    char longname[65];memset(longname,'a',64);longname[64]=0;
    CODOL_ResetClientMatchData();assert(!CODOL_ClientMatchData());
    assert(!CODOL_SelectClientMatchData(NULL));assert(!CODOL_SelectClientMatchData(""));
    assert(!CODOL_SelectClientMatchData(longname));assert(loads==0);
    assert(!CODOL_SelectClientMatchData("missing"));assert(!CODOL_ClientMatchData());
    size=1025;assert(!CODOL_SelectClientMatchData("oversize"));assert(!CODOL_ClientMatchData());
    size=7;assert(!CODOL_SelectClientMatchData("tiny"));assert(!CODOL_ClientMatchData());
    size=858;assert(CODOL_SelectClientMatchData("mp/clientmatchdata.def"));
    m=CODOL_ClientMatchData();assert(m);
    assert(!memcmp(m->record,"\x10\0\0\0\xad\xbb\xd7\x3f",8));
    for(i=8;i<sizeof(m->record);++i)assert(m->record[i]==0);
    m->record[654]=17;i=loads;
    CODOL_RequestClientMatchData(0);CODOL_RequestClientMatchData(1);
    assert(!CODOL_ClientMatchDataDue(0,999) && CODOL_ClientMatchDataDue(0,1000));
    CODOL_ClientMatchDataSent(0,1000);
    assert(!CODOL_ClientMatchDataDue(0,1999) && CODOL_ClientMatchDataDue(0,2000));
    CODOL_AcknowledgeClientMatchData(0);
    assert(!CODOL_ClientMatchDataDue(0,3000) && CODOL_ClientMatchDataDue(1,3000));
    CODOL_RequestClientMatchData(0);assert(CODOL_ClientMatchDataDue(0,3000));
    assert(CODOL_SelectClientMatchData("MP/CLIENTMATCHDATA.DEF"));
    assert(loads==i && m->record[654]==17);
    assert(!CODOL_SelectClientMatchData("other"));assert(loads==i && m->record[654]==17);
    CODOL_ResetClientMatchData();assert(!CODOL_ClientMatchData());
    assert(!CODOL_ClientMatchDataDue(0,5000) && !CODOL_ClientMatchDataDue(1,5000));
    size=1024;assert(CODOL_SelectClientMatchData("other"));
    assert(CODOL_ClientMatchData()->record[654]==0);
    CODOL_ResetClientMatchData();CODOL_ResetClientMatchData();
    puts("PASS: match-data schema ownership, selection, headers and reset");
}
