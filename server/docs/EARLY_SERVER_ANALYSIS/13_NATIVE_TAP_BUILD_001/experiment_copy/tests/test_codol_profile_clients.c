#include "codol_profile.h"
#include "codol_stats.h"
#include <assert.h>
#include <stdio.h>
int main(void)
{
    uint8_t data[CODOL_STATS_SIZE]={0};data[4]=11;data[8]=1;
    codol_structured_definition_t def={0};def.version=11;def.checksum=1;def.layout.record_size=8;
    codol_structured_schema_t schema={"secure",1,&def};uint64_t uid=0;
    assert(!CODOL_ClientSecureProfile(0,&uid) && uid==0);
    assert(CODOL_AttachClientSecureProfile(0,UINT64_MAX,data,sizeof(data),&schema));
    const uint8_t *owned=CODOL_ClientSecureProfile(0,&uid);assert(owned!=data && uid==UINT64_MAX);
    data[12]=55;assert(owned[12]==0);
    assert(CODOL_AttachClientSecureProfile(1,2,data,sizeof(data),&schema));
    assert(CODOL_ClientSecureProfile(1,&uid)[12]==55 && uid==2);
    data[4]=12;assert(!CODOL_AttachClientSecureProfile(0,3,data,sizeof(data),&schema));
    assert(CODOL_ClientSecureProfile(0,&uid)==owned && uid==UINT64_MAX);
    data[4]=11;assert(!CODOL_AttachClientSecureProfile(32,3,data,sizeof(data),&schema));
    assert(!CODOL_AttachClientSecureProfile(0,0,data,sizeof(data),&schema));
    assert(CODOL_AttachClientSecureProfile(0,3,data,sizeof(data),&schema));
    assert(CODOL_ClientSecureProfile(0,&uid)[12]==55 && uid==3);
    CODOL_DetachClientSecureProfile(0);assert(!CODOL_ClientSecureProfile(0,NULL));
    assert(CODOL_ClientSecureProfile(1,NULL));CODOL_ResetClientSecureProfiles();
    assert(!CODOL_ClientSecureProfile(1,NULL));CODOL_ResetClientSecureProfiles();
    puts("PASS: secure profile ownership, isolation, atomic replacement and connection reset");
}
