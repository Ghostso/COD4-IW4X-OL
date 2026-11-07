#include "codol_character_composition.h"
#include "codol_character_variant.h"
#include "codol_player_appearance.h"
#include "codol_stats.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static const char *market_cells[]={
    "10","head","cha","hea", "20","coat","cha","fja",
    "30","vest","cha","ves", "40","rig","cha","ves",
    "50","pads","cha","elp", "60","hands","cha","han"};
static const char *default_cells[21];
static const char *rig_cells[]={"vest","rig","1"};
static const char *part_cells[]={
    "head","model","s ss sss","head_model","",
    "coat","model","m sc urb","coat_sc_m_00","coat_sc_vmchar",
    "vest","model","m sc urb","vest_sc_m_00","",
    "rig","model","m sc urb","rig_sc_m_00","",
    "pads","model","s ss sss","pads_model","",
    "hands","model","m sc urb","hands_wht","hands_vmchar"};
static codol_engine_table_t market={"market",4,6,market_cells};
static codol_engine_table_t defaults={"defaults",21,1,default_cells};
static codol_engine_table_t rigs={"rigs",3,1,rig_cells};
static codol_engine_table_t parts={"parts",5,6,part_cells};
static int missing_parts;
int CODOL_LoadEngineStringTable(const char *name,const codol_engine_table_t **out)
{
    if(!strcmp(name,"mp/coMarketplaceItems.csv"))*out=&market;
    else if(!strcmp(name,"mp/coCharacterDefTable.csv"))*out=&defaults;
    else if(!strcmp(name,"mp/coChestRigs.csv"))*out=&rigs;
    else if(!strncmp(name,"mp/coCharItems/",15)) {
        if(missing_parts)return -1;
        *out=&parts;
    } else return 0;
    return 1;
}
static void put(uint8_t *p,uint32_t n){for(unsigned i=0;i<4;++i)p[i]=(uint8_t)(n>>(8*i));}
int main(void)
{
    uint8_t profile[CODOL_STATS_SIZE]={0},original[CODOL_STATS_SIZE],map[963*4];
    codol_structured_property_t root[]={
        {"tfCharacterIndex",{9,0},0,{0,0}}, {"scCharacterIndex",{9,0},1,{0,0}},
        {"zmCharacterIndex",{9,0},2,{0,0}}, {"characterClasses",{6,0},3,{0,0}}};
    codol_structured_property_t slots={"slots",{6,1},0,{0,0}};
    codol_structured_struct_t structures[]={{4,1934,0,963,root},{1,40,0,20,&slots}};
    codol_structured_array_t arrays[]={{48,{5,1},40},{20,{9,0},2}};
    codol_structured_definition_t def={0};codol_structured_schema_t schema={"public",1,&def};
    codol_character_composition_t result,before;
    def.version=220;def.checksum=0xe4fd5218;def.root=(codol_structured_type_t){5,0};
    def.struct_count=2;def.structs=structures;def.indexed_count=2;def.indexed_arrays=arrays;
    def.layout=(codol_structured_layout_t){map,sizeof(map),1934};
    for(unsigned i=0;i<963;++i)put(map+4*i,8+2*i);
    put(profile+4,220);put(profile+8,def.checksum);
    /* SC selects record 1, while TF remains at empty record 0. */
    assert(CODOL_StructuredWriteScalar(&def.layout,9,1,profile+4,sizeof(profile)-4,1));
    assert(CODOL_StructuredWriteScalar(&def.layout,9,3+20+4,profile+4,sizeof(profile)-4,10));
    assert(CODOL_StructuredWriteScalar(&def.layout,9,3+20+3,profile+4,sizeof(profile)-4,65535));
    for(unsigned i=0;i<21;++i)default_cells[i]="";
    default_cells[0]="head";default_cells[3+2]="coat";default_cells[3+3]="hands";
    default_cells[3+5]="vest";default_cells[3+7]="pads";
    memcpy(original,profile,sizeof(profile));
    assert(CODOL_ComposeProfileCharacter(profile,sizeof(profile),&schema,"sc",0,"urb","wht",0,&result));
    assert(result.character_index==1 && result.items[2]==20 && result.items[5]==30 && result.items[15]==40);
    assert(!strcmp(result.models[2],"coat_sc_m_00") && !strcmp(result.models[15],"rig_sc_m_00"));
    assert(!strcmp(result.viewmodels[2],"coat_sc_vmchar"));
    /* -1 is "nothing chosen", not "stays empty": C1 composes into a zeroed
     * array (0060b074) and skips -1 while copying (0060d2c0/0060d3a0), so the
     * slot reaches the default merge as a zero and gets the character default.
     * This is the TF hea_sean case whose viewmodel hands went missing. */
    assert(result.items[3]==60 && !strcmp(result.models[3],"hands_wht"));
    assert(!strcmp(result.viewmodels[3],"hands_vmchar"));
    assert(!result.items[7] && !result.models[7]); /* Torso rejects elbow pads. */
    assert(!memcmp(original,profile,sizeof(profile)));
    before=result;missing_parts=1;
    assert(!CODOL_ComposeProfileCharacter(profile,sizeof(profile),&schema,"sc",0,"urb","wht",0,&result));
    assert(!memcmp(&before,&result,sizeof(result))); /* No partial defaults/rig output on loader error. */
    missing_parts=0;
    assert(CODOL_ComposeProfileCharacter(profile,sizeof(profile),&schema,"tf",0,"urb","wht",0,&result));
    assert(!result.character_index && !result.items[4] && !result.models[4]);
    {
        codol_character_parts_t ordered;
        memset(&result,0,sizeof(result));
        result.models[0]="pants";result.models[4]="head";
        result.models[5]="vest";result.models[9]="material";
        result.viewmodels[2]="arms";result.viewmodels[3]="gloves";
        assert(CODOL_OrderCharacterParts(&result,&ordered));
        assert(ordered.count==3 && !strcmp(ordered.model[0],"pants"));
        assert(!strcmp(ordered.model[1],"vest") && !strcmp(ordered.model[2],"head"));
        assert(!strcmp(ordered.arms,"arms") && !strcmp(ordered.hands,"gloves"));
    }
    puts("PASS: selected profile -> defaults -> rig -> visibility -> model names; immutable input and atomic failure");
}
