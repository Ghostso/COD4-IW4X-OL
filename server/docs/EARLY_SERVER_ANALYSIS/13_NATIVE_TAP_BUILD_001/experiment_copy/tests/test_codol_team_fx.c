#include "scr_vm_functions.h"
#include "codol_sv_state.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
level_locals_t level;
static codol_configstrings_t bank,base;
static int errors,parameters=2,effect_id=7;
static const char *argument="J_Spine4";
codol_configstrings_t *CODOL_ServerConfigstrings(void) { return &bank; }
const codol_configstrings_t *CODOL_ServerInheritedConfigstrings(void) { return &base; }
int Scr_GetNumParam(void) { return parameters; }
int Scr_GetInt(unsigned i) { assert(!i); return effect_id; }
char *Scr_GetString(unsigned i) { assert(i==1); return (char *)argument; }
void Scr_Error(const char *error) { assert(error); ++errors; }
void SV_GetConfigstring(int index,char *out,int size)
{ assert(index==CS_FX+7 && size>32); strcpy(out,"misc/thermal_beacon_inverted"); }
/* Engine string helper needed by the native effect-name adapter for its
 * extra-effect branch; this fixture exercises the retained configstring ID. */
void Q_strncpyz(char *dest,const char *src,int size)
{
    size_t n;
    assert(dest && src && size>0);
    n=strlen(src); if(n>=(size_t)size)n=(size_t)size-1;
    memcpy(dest,src,n);dest[n]=0;
}
int main(void)
{
    unsigned i; char text[64]; size_t bytes; unsigned count;
    const char *fx="misc/thermal_beacon_inverted";
    assert(CODOL_SetConfigstring(&base,CODOL_CS_EFFECTS+19,fx));
    CODOL_Scr_PrecacheFxTeamThermal(); assert(errors==1 && !bank.count);
    level.initializing=1; parameters=1;
    CODOL_Scr_PrecacheFxTeamThermal(); assert(errors==2 && !bank.count);
    parameters=2; effect_id=0;
    CODOL_Scr_PrecacheFxTeamThermal(); assert(errors==3 && !bank.count);
    effect_id=7; CODOL_Scr_PrecacheFxTeamThermal();
    assert(errors==3 && bank.count==1);
    assert(!strcmp(bank.values[6100],"019j_spine4"));
    assert(!bank.values[3651+19]); /* inherited effect, native ID 7 never serialized */
    argument="j_SPINE4"; CODOL_Scr_PrecacheFxTeamThermal(); assert(bank.count==1);
    argument="bad\"tag"; CODOL_Scr_PrecacheFxTeamThermal(); assert(errors==4 && bank.count==1);
    assert(CODOL_RegisterTeamThermal(&bank,&base,"new_fx","tag")==1);
    assert(!strcmp(bank.values[3652],"new_fx") && !strcmp(bank.values[6101],"001tag"));
    for(i=2;i<CODOL_TEAM_THERMAL_SLOTS;++i) {
        snprintf(text,sizeof(text),"019tag%u",i);
        assert(CODOL_SetConfigstring(&base,6100+i,text));
    }
    count=bank.count; bytes=bank.bytes;
    assert(CODOL_RegisterTeamThermal(&bank,&base,"would_leak","absent")==-1);
    assert(bank.count==count && bank.bytes==bytes && !bank.values[3653]);
    assert(CODOL_RegisterTeamThermal(&bank,&base,fx,"TAG31")==31);
    assert(bank.count==count && bank.bytes==bytes);
    CODOL_ClearConfigstrings(&bank); CODOL_ClearConfigstrings(&base);
    for(i=1;i<CODOL_EFFECT_SLOTS;++i) {
        snprintf(text,sizeof(text),"effect_%u",i);
        assert(CODOL_SetConfigstring(&base,3651+i,text));
    }
    assert(CODOL_RegisterTeamThermal(&bank,&base,"absent","tag")==-1 && !bank.count);
    assert(CODOL_RegisterTeamThermal(&bank,&base,"effect_319","tag")==0);
    assert(!strcmp(bank.values[6100],"319tag"));
    CODOL_ClearConfigstrings(&bank); CODOL_ClearConfigstrings(&base);
    assert(CODOL_RegisterTeamThermal(&bank,&base,fx,"bad\ntag")==-1 && !bank.count);
    assert(CODOL_RegisterTeamThermal(&bank,&bank,fx,"tag")==-1);
    puts("PASS: thermal namespace translation, inherited reuse, all slots, atomic exhaustion and VM gates");
}
