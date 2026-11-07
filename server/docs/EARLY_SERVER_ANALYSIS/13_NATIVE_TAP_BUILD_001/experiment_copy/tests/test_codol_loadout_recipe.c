#include "codol_script_profile_loadout.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static const char *market_values[18*4],*attachment_values[17*4];
static char ids[17][8],names[17][20];
static const char *default_values[]={"m4_mp","sto","part_16","y","mag","part_1","y"};
static const char *camo_values[]={"part_0","m4_mp","13","","",""};
static const char *art_values[]={"m4_mp","0","base_black","base_black_vm","m4_mp","13","base_tiger","base_tiger_vm"};
static codol_engine_table_t market={"market",4,18,market_values};
static codol_engine_table_t attachments={"attachments",4,17,attachment_values};
static codol_engine_table_t defaults={"defaults",7,1,default_values};
static codol_engine_table_t camo={"cam",6,1,camo_values};
static codol_engine_table_t art={"art",4,2,art_values};
static codol_engine_table_t empty={"empty",6,0,NULL};
int CODOL_LoadEngineStringTable(const char *name,const codol_engine_table_t **out)
{
    if(!strcmp(name,"mp/coMarketplaceItems.csv"))*out=&market;
    else if(!strcmp(name,"mp/coWeaponAttachmentTable.csv"))*out=&attachments;
    else if(!strcmp(name,"mp/coweapitemswea.csv"))*out=&defaults;
    else if(!strcmp(name,"mp/coweapitems/cam.csv"))*out=&camo;
    else if(!strcmp(name,"mp/coweapmodels/m4_mp.csv"))*out=&art;
    else if(!strncmp(name,"mp/coweapitems/",15))*out=&empty;
    else return 0;
    return 1;
}
int main(void)
{
    int selected[15];codol_loadout_recipe_t recipe,saved;unsigned i;
    market_values[0]="1001";market_values[1]="m4_mp";market_values[2]="wea";market_values[3]="assault";
    for(i=0;i<17;++i) {
        snprintf(ids[i],sizeof(ids[i]),"%u",2000+i);
        snprintf(names[i],sizeof(names[i]),"part_%u",i);
        market_values[4*(i+1)]=ids[i];market_values[4*(i+1)+1]=names[i];
        market_values[4*(i+1)+2]="wat";
        market_values[4*(i+1)+3]=i==0 ? "cam":i==1 ? "mag":(i==14 || i==16) ? "sto":"gri";
        attachment_values[4*i]="m4_mp";attachment_values[4*i+1]=names[i];
        attachment_values[4*i+2]="nop";attachment_values[4*i+3]=i==1 ? "3":"0";
        if(i<15)selected[i]=2000+i;
    }
    assert(CODOL_ComposeLoadoutWeaponRecipe(1001,selected,15,&recipe)==1);
    assert(recipe.flag==13 && recipe.base_index==2);
    assert(recipe.count==15); /* All fifteen choices; no default replaces one. */
    for(i=0;i<15;++i)assert(recipe.parts[i].origin==CODOL_LOADOUT_PART_EQUIPPED && recipe.parts[i].item==i+1);
    assert(recipe.parts[1].variant==3);
    assert(strstr(recipe.name,"*a 2 13") == recipe.name);
    selected[14]=-1;
    assert(CODOL_ComposeLoadoutWeaponRecipe(1001,selected,15,&recipe)==1);
    assert(recipe.count==15 && recipe.parts[14].item==17 && recipe.parts[14].origin==CODOL_LOADOUT_PART_DECLARED);
    saved=recipe;selected[14]=2999;
    assert(CODOL_ComposeLoadoutWeaponRecipe(1001,selected,15,&recipe)==-1);
    assert(!memcmp(&recipe,&saved,sizeof(recipe)));
    selected[14]=2014;attachments.rowCount=14;
    assert(CODOL_ComposeLoadoutWeaponRecipe(1001,selected,15,&recipe)==-1);
    assert(!memcmp(&recipe,&saved,sizeof(recipe)));
    puts("PASS: full profile attachment set, camo/variant distinction, declared defaults, invalid selection atomicity");
    return 0;
}
