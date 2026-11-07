#include "scr_vm_functions.h"
#include "cscr_variable.h"
#include "codol_stats.h"
#include "codol_assets.h"
#include "codol_structured_schema.h"
#include "codol_profile.h"
#include "codol_script_profile_vm.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
struct function_stack_t gFs;
gentity_t g_entities[MAX_GENTITIES];
static gclient_t client;
static unsigned object=42,type=VAR_ENTITY;
static scr_entref_t ref;
static int args[2]={0,1},errors,table_status=1;
static const char *result;
static const char *class_name;
static int class_result;
char *Scr_GetString(unsigned index) { assert(index==0); return (char *)class_name; }
void Scr_AddInt(int value) { class_result=value; }
static const char *cells[]={"3002","specialty_fastreload","per","",
                            "3003","specialty_marathon","per",""};
static codol_engine_table_t table={"mp/coMarketplaceItems.csv",4,2,cells};
static uint8_t offset_map[8*5*4];
static int schema_status=1;
static unsigned schema_loads;
static void put32(uint8_t *p,uint32_t v)
{ unsigned i;for(i=0;i<4;++i)p[i]=(uint8_t)(v>>(i*8)); }
/* A deliberately reversed physical map makes the fixture prove that the
 * builtin follows the mounted definition instead of the old byte constant. */
int CODOL_LoadMountedStructuredSchema(const char *name,codol_structured_schema_t *out)
{
    codol_structured_definition_t *d;unsigned i;
    assert(!strcmp(name,"mp/playerdata.def"));++schema_loads;
    if(schema_status!=1)return schema_status;
    out->name=name;out->count=1;
    out->definitions=calloc(1,sizeof(*out->definitions));assert(out->definitions);
    d=out->definitions;d->version=220;d->checksum=0xe4fd5218;
    d->root=(codol_structured_type_t){5,0};
    d->struct_count=2;d->structs=calloc(2,sizeof(*d->structs));assert(d->structs);
    d->structs[0].count=1;d->structs[0].logical_count=40;
    d->structs[0].properties=calloc(1,sizeof(*d->structs[0].properties));
    assert(d->structs[0].properties);
    d->structs[0].properties[0]=(codol_structured_property_t){"weaponClasses",{6,0},0,{0,0}};
    d->structs[1].count=1;d->structs[1].logical_count=5;
    d->structs[1].properties=calloc(1,sizeof(*d->structs[1].properties));
    assert(d->structs[1].properties);
    d->structs[1].properties[0]=(codol_structured_property_t){"perks",{6,1},0,{0,0}};
    d->indexed_count=2;d->indexed_arrays=calloc(2,sizeof(*d->indexed_arrays));
    assert(d->indexed_arrays);
    d->indexed_arrays[0]=(codol_structured_array_t){8,{5,1},0};
    d->indexed_arrays[1]=(codol_structured_array_t){5,{9,0},0};
    for(i=0;i<40;++i)put32(offset_map+4*i,8+(39-i)*2);
    d->layout=(codol_structured_layout_t){offset_map,sizeof(offset_map),88};
    return 1;
}
/* The class builtin reads only the public profile. The shared VM also has a
 * secure-profile branch, which is intentionally unavailable in this fixture. */
const uint8_t *CODOL_ClientSecureProfile(unsigned client,uint64_t *uid)
{ (void)client;(void)uid;assert(0 && "class fixture unexpectedly accessed secure profile");return NULL; }
int Scr_GetInt(unsigned index) { assert(index<2); return args[index]; }
unsigned Scr_GetSelf(unsigned id) { assert(id==77); return object; }
unsigned Scr_GetObjectType(unsigned id) { assert(id==42); return type; }
scr_entref_t Scr_GetEntityIdRef(unsigned id) { assert(id==42); return ref; }
void Scr_Error(const char *s) { assert(s && *s); ++errors; }
void Scr_AddString(const char *s) { assert(!result); result=s; }
int CODOL_LoadEngineStringTable(const char *name,const codol_engine_table_t **out)
{ assert(!strcmp(name,table.name)); *out=&table; return table_status; }
static void upload_at(unsigned number,int item,unsigned ci,unsigned slot)
{
    unsigned i; uint8_t data[CODOL_STATS_SIZE]={0};
    assert(ci<8 && slot<5);
    put32(data+4,220);put32(data+8,0xe4fd5218);
    /* Independent of the resolver under test: reversed physical position for
     * logical class*5+slot, within the synthetic mounted record. */
    data[4+8+(39-ci*5-slot)*2]=(uint8_t)item;
    data[4+8+(39-ci*5-slot)*2+1]=(uint8_t)(item>>8);
    CODOL_ResetClientStats(number);
    for(i=0;i<CODOL_STATS_COUNT;++i) {
        size_t off=i*CODOL_STATS_CHUNK,n=CODOL_STATS_SIZE-off;
        if(n>CODOL_STATS_CHUNK)n=CODOL_STATS_CHUNK;
        assert(CODOL_AcceptClientStats(number,i,data+off,n));
    }
}
static void upload(unsigned number,int item){upload_at(number,item,0,0);}
static void reject(void)
{ int before=errors; result=NULL; CODOL_Scr_GetClassPerk(); assert(errors==before+1 && !result); }
int main(void)
{
    static const struct {const char *name; int index;} cases[]={
        {"custom1",0},{"CUSTOM3",2},{" \tClass008\r\n",7},{"class9",8},
        {"",-1},{"custom",-1},{"custom0",-1},{"class-1",-1},{"custom+1",-1},
        {"custom 1",-1},{"custom1x",-1},{"autoassign",-1},{"class1.5",-1},
        {"class2147483648",2147483647},{"class2147483649",-1},
        {"custom99999999999999999999",-1},{"class00000000000000001",0}};
    unsigned i;
    for(i=0;i<sizeof(cases)/sizeof(*cases);++i) {
        class_name=cases[i].name; class_result=-99;
        CODOL_Scr_GetClassIndex(); assert(class_result==cases[i].index);
    }
    gFs.localId=77; g_entities[0].client=g_entities[1].client=&client;
    g_entities[0].r.inuse=g_entities[1].r.inuse=1;
    upload(0,3002); upload(1,3003);
    CODOL_Scr_GetClassPerk(); assert(!strcmp(result,"specialty_fastreload") && !errors);
    ref.entnum=1; result=NULL; CODOL_Scr_GetClassPerk(); assert(!strcmp(result,"specialty_marathon"));
    upload_at(1,3003,7,4);args[0]=7;args[1]=5;result=NULL;
    CODOL_Scr_GetClassPerk();assert(result && !strcmp(result,"specialty_marathon"));
    args[0]=0;args[1]=1;
    CODOL_ResetClientStats(1); reject(); ref.entnum=0;
    args[0]=-1; reject(); args[0]=8; reject(); args[0]=0;
    args[1]=0; reject(); args[1]=6; reject(); args[1]=1;
    gFs.localId=0; reject(); gFs.localId=77;
    object=0; reject(); object=42; type=VAR_ARRAY; reject(); type=VAR_ENTITY;
    ref.classnum=2; reject(); ref.classnum=0;
    ref.entnum=MAX_CLIENTS; reject(); ref.entnum=0;
    table_status=-1; reject(); table_status=1;
    cells[2]="weap"; reject(); cells[2]="per";
    cells[4]="3002";result=NULL;CODOL_Scr_GetClassPerk();
    assert(result && !strcmp(result,"specialty_marathon"));cells[4]="3003";
    upload(0,3100); reject();
    upload(0,-1); result=NULL; CODOL_Scr_GetClassPerk(); assert(result && !*result);
    assert(schema_loads==1);
    CODOL_ResetScriptProfiles();schema_status=0;
    upload(0,3002);reject();assert(schema_loads==2);
    CODOL_ResetScriptProfiles();schema_status=1;
    result=NULL;CODOL_Scr_GetClassPerk();assert(result && !strcmp(result,"specialty_fastreload"));
    CODOL_ResetScriptProfiles();CODOL_ResetClientStats(0);CODOL_ResetClientStats(1);
    puts("PASS: GSC self selects per-client uploaded perks; catalogue resolution and errors");
}
