#include "codol_stats.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static void upload(unsigned client,const uint8_t *bytes)
{
    unsigned i;
    CODOL_ResetClientStats(client);
    for(i=0;i<CODOL_STATS_COUNT;++i) {
        size_t offset=i*CODOL_STATS_CHUNK,n=CODOL_STATS_SIZE-offset;
        if(n>CODOL_STATS_CHUNK) n=CODOL_STATS_CHUNK;
        assert(CODOL_AcceptClientStats(client,i,bytes+offset,n));
    }
}
static void class_perks(void)
{
    uint8_t profile[CODOL_STATS_SIZE]={0}; unsigned c,s; int value=77;
    profile[4]=220; profile[8]=0x18; profile[9]=0x52; profile[10]=0xfd; profile[11]=0xe4;
    for(c=0;c<8;++c) for(s=1;s<=5;++s) {
        unsigned offset=0x1511+c*92+(6+s)*2, item=3000+c*5+s;
        profile[offset]=item; profile[offset+1]=item>>8;
    }
    assert(!CODOL_ClientClassPerkItem(0,0,1,&value) && value==77);
    upload(0,profile);
    for(c=0;c<8;++c) for(s=1;s<=5;++s)
        assert(CODOL_ClientClassPerkItem(0,c,s,&value) && value==(int)(3000+c*5+s));
    profile[0x151f]=0xff; profile[0x1520]=0xff;
    upload(1,profile);
    assert(CODOL_ClientClassPerkItem(1,0,1,&value) && value==-1);
    assert(CODOL_ClientClassPerkItem(0,0,1,&value) && value==3001);
    assert(!CODOL_ClientClassPerkItem(0,8,1,&value) && value==3001);
    assert(!CODOL_ClientClassPerkItem(0,0,0,&value) && value==3001);
    assert(!CODOL_ClientClassPerkItem(0,0,6,&value) && value==3001);
    assert(!CODOL_ClientClassPerkItem(32,0,1,&value) && value==3001);
    assert(!CODOL_ClientClassPerkItem(0,0,1,NULL));
    profile[4]=219; upload(1,profile);
    assert(!CODOL_ClientClassPerkItem(1,0,1,&value) && value==3001);
    profile[4]=220; profile[8]^=1; upload(1,profile);
    assert(!CODOL_ClientClassPerkItem(1,0,1,&value) && value==3001);
    CODOL_ResetClientStats(0);
    assert(!CODOL_ClientClassPerkItem(0,0,1,&value) && value==3001);
    CODOL_ResetClientStats(1);
}
int main(void)
{
    uint8_t source[CODOL_STATS_SIZE], altered[CODOL_STATS_CHUNK], response[64], before[64];
    uint32_t remaining = CODOL_STATS_MASK;
    unsigned i;
    for(i = 0; i < sizeof(source); ++i) source[i] = i * 17u + i / 1240u;
    CODOL_ResetClientStats(0);
    assert(!CODOL_ClientStats(0) && CODOL_ClientStatsMissing(0) == remaining);
    /* Descending order includes the shorter final chunk and arbitrary loss. */
    for(i = CODOL_STATS_COUNT; i-- > 0;) {
        size_t n = i == 26 ? 528 : 1240;
        assert(!CODOL_AcceptClientStats(0, i, source + i * 1240, n - 1));
        assert(CODOL_ClientStatsMissing(0) == remaining);
        assert(CODOL_AcceptClientStats(0, i, source + i * 1240, n));
        remaining &= ~(1u << i);
        assert(CODOL_ClientStatsMissing(0) == remaining);
        assert(CODOL_AcceptClientStats(0, i, source + i * 1240, n));
        memcpy(altered, source + i * 1240, n); altered[0] ^= 1;
        assert(!CODOL_AcceptClientStats(0, i, altered, n));
        assert(CODOL_ClientStatsMissing(0) == remaining);
        if(i) assert(!CODOL_ClientStats(0));
    }
    assert(!memcmp(CODOL_ClientStats(0), source, sizeof(source)));
    assert(!CODOL_ClientStats(1) && CODOL_ClientStatsMissing(1) == CODOL_STATS_MASK);
    assert(!CODOL_AcceptClientStats(32, 0, source, 1240));
    assert(!CODOL_AcceptClientStats(0, 27, source, 1240));
    assert(!CODOL_AcceptClientStats(0, 26, source, 1240));
    assert(CODOL_WriteStatsResponse(response, sizeof(response), 0));
    assert(!memcmp(response, "\xff\xff\xff\xffstatResponse 0", 19));
    memcpy(before, response, sizeof(response));
    assert(!CODOL_WriteStatsResponse(response, 4, 0));
    assert(!CODOL_WriteStatsResponse(response, sizeof(response), 0x8000000));
    assert(!memcmp(before, response, sizeof(response)));
    assert(CODOL_WriteStatsResponse(response, sizeof(response), CODOL_STATS_MASK));
    assert(!strcmp((char *)response + 4, "statResponse 134217727"));
    CODOL_ResetClientStats(0);
    assert(!CODOL_ClientStats(0) && CODOL_ClientStatsMissing(0) == CODOL_STATS_MASK);
    puts("CoDOL 27-chunk stats ownership, missing masks and duplicate validation passed");
    class_perks();
    puts("CoDOL per-client packed class perks, schema guards and upload/reset isolation passed");
    return 0;
}
