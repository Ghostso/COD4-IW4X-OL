/* C1 1.1.1.13: thermal builtin 0x550130, range helper 0x54f9d0,
 * effect index 0x570730. Keep retained IW3 IDs private to the engine. */
#include "codol_configstrings.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *effective(const codol_configstrings_t *bank,
    const codol_configstrings_t *base,unsigned index)
{ return bank->values[index] ? bank->values[index] : base->values[index]; }
static unsigned lower(unsigned c) { return c>='A' && c<='Z' ? c+32 : c; }
static int equal_fold(const char *a,const char *b)
{
    while(*a && lower((unsigned char)*a)==lower((unsigned char)*b)) { ++a; ++b; }
    return lower((unsigned char)*a)==lower((unsigned char)*b);
}
static void install(codol_configstrings_t *bank,unsigned index,char *copy)
{
    if(bank->values[index]) bank->bytes-=strlen(bank->values[index])+1;
    else ++bank->count;
    free(bank->values[index]); bank->values[index]=copy; bank->bytes+=strlen(copy)+1;
}
int CODOL_RegisterTeamThermal(codol_configstrings_t *bank,
    const codol_configstrings_t *base,const char *effect,const char *tag)
{
    unsigned i,fx=0,empty_fx=0,thermal=CODOL_TEAM_THERMAL_SLOTS;
    size_t n; char value[1024],*effect_copy=NULL,*thermal_copy=NULL;
    int new_fx=0,existing_thermal=0;
    if(!bank || !base || bank==base || !effect || !*effect || !tag) return -1;
    for(n=0;effect[n];++n)
        if(n>=63 || (unsigned char)effect[n]<=32 || effect[n]=='"' ||
           effect[n]==127 || effect[n]==';' || effect[n]=='\\') return -1;
    for(n=0;tag[n];++n) {
        unsigned char c=(unsigned char)tag[n];
        if(n>=sizeof(value)-4 || c<32 || c==127 || c=='"') return -1;
        value[3+n]=(char)lower(c);
    }
    value[3+n]=0;
    for(i=1;i<CODOL_EFFECT_SLOTS;++i) {
        const char *name=effective(bank,base,CODOL_CS_EFFECTS+i);
        if(name && !strcmp(name,effect)) { fx=i; break; }
        if(!empty_fx && (!name || !*name)) empty_fx=i;
    }
    if(!fx) { fx=empty_fx; new_fx=1; }
    if(!fx) return -1;
    value[0]=(char)('0'+fx/100); value[1]=(char)('0'+(fx/10)%10); value[2]=(char)('0'+fx%10);
    for(i=0;i<CODOL_TEAM_THERMAL_SLOTS;++i) {
        const char *name=effective(bank,base,CODOL_CS_TEAM_THERMAL+i);
        if(name && equal_fold(name,value)) { thermal=i; existing_thermal=1; break; }
        if(thermal==CODOL_TEAM_THERMAL_SLOTS && (!name || !*name)) thermal=i;
    }
    if(thermal==CODOL_TEAM_THERMAL_SLOTS) return -1;
    /* Allocate both writes before publishing either, including a newly resolved
     * effect. Full banks and allocation failure cannot leave partial entries. */
    if(bank->bytes>SIZE_MAX-strlen(effect)-strlen(value)-2) return -1;
    if(new_fx) {
        effect_copy=malloc(strlen(effect)+1);
        if(!effect_copy) return -1;
        strcpy(effect_copy,effect);
    }
    if(!existing_thermal) {
        thermal_copy=malloc(strlen(value)+1);
        if(!thermal_copy) { free(effect_copy); return -1; }
        strcpy(thermal_copy,value);
    }
    if(effect_copy) install(bank,CODOL_CS_EFFECTS+fx,effect_copy);
    if(thermal_copy) install(bank,CODOL_CS_TEAM_THERMAL+thermal,thermal_copy);
    return (int)thermal;
}
