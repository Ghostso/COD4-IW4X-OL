#include "codol_profile.h"
#include "codol_stats.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static void put(uint8_t *p,uint32_t n){for(unsigned i=0;i<4;++i)p[i]=(uint8_t)(n>>(8*i));}
int main(void)
{
    uint8_t profile[CODOL_STATS_SIZE]={0},map[963*4];
    codol_structured_property_t root[]={
        {"tfCharacterIndex",{9,0},0,{0,0}}, {"scCharacterIndex",{9,0},1,{0,0}},
        {"zmCharacterIndex",{9,0},2,{0,0}}, {"characterClasses",{6,0},3,{0,0}}};
    codol_structured_property_t slots={"slots",{6,1},0,{0,0}};
    codol_structured_struct_t structures[]={{4,1934,0,963,root},{1,40,0,20,&slots}};
    codol_structured_array_t arrays[]={{48,{5,1},40},{20,{9,0},2}};
    codol_structured_definition_t def={0};codol_structured_schema_t schema={"public",1,&def};
    codol_profile_character_t result,before;
    def.version=220;def.checksum=0xe4fd5218;def.root=(codol_structured_type_t){5,0};
    def.struct_count=2;def.structs=structures;def.indexed_count=2;def.indexed_arrays=arrays;
    def.layout=(codol_structured_layout_t){map,sizeof(map),1934};
    for(unsigned i=0;i<963;++i) put(map+4*i,8+2*i);
    put(profile+4,220);put(profile+8,def.checksum);
    assert(CODOL_StructuredWriteScalar(&def.layout,9,0,profile+4,sizeof(profile)-4,47));
    assert(CODOL_StructuredWriteScalar(&def.layout,9,1,profile+4,sizeof(profile)-4,1));
    for(unsigned i=0;i<20;++i) {
        assert(CODOL_StructuredWriteScalar(&def.layout,9,3+47*20+i,profile+4,sizeof(profile)-4,300+i));
        assert(CODOL_StructuredWriteScalar(&def.layout,9,3+20+i,profile+4,sizeof(profile)-4,100+i));
    }
    assert(CODOL_ProfileCharacter(profile,sizeof(profile),&schema,"tf",&result) && result.character_index==47);
    for(unsigned i=0;i<20;++i)assert(result.items[i]==300+i);
    assert(CODOL_ProfileCharacter(profile,sizeof(profile),&schema,"sc",&result) && result.character_index==1);
    for(unsigned i=0;i<20;++i)assert(result.items[i]==100+i);
    assert(CODOL_ProfileCharacter(profile,sizeof(profile),&schema,"zm",&result) && !result.character_index);
    for(unsigned i=0;i<20;++i)assert(!result.items[i]);
    before=result;
    assert(!CODOL_ProfileCharacter(profile,sizeof(profile),&schema,"bad",&result) && !memcmp(&before,&result,sizeof(result)));
    profile[12]=48;
    assert(!CODOL_ProfileCharacter(profile,sizeof(profile),&schema,"tf",&result) && !memcmp(&before,&result,sizeof(result)));
    profile[12]=47;arrays[1].count_or_enum=19;
    assert(!CODOL_ProfileCharacter(profile,sizeof(profile),&schema,"tf",&result) && !memcmp(&before,&result,sizeof(result)));
    arrays[1].count_or_enum=20;put(map+4*(3+47*20+19),1934);
    assert(!CODOL_ProfileCharacter(profile,sizeof(profile),&schema,"tf",&result) && !memcmp(&before,&result,sizeof(result)));
    assert(!CODOL_ProfileCharacter(profile,sizeof(profile)-1,&schema,"sc",&result));
    profile[4]=0;assert(!CODOL_ProfileCharacter(profile,sizeof(profile),&schema,"sc",&result));
    puts("PASS: faction-specific profile records, twenty slots, last class and atomic schema failures");
}
