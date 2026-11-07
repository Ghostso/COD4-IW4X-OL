#include "scr_vm.h"
#include "cvar.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
void CODOL_Scr_GetDvarVector(void);
static int argc=1,exists=1,errors,outputs;
static char *raw="1 2 3";
static char *fallback="4 5 6";
static float result[3];
int Scr_GetNumParam(void){return argc;}
char *Scr_GetString(unsigned i){assert(i<2);return i ? fallback : "fixture";}
cvar_t *Cvar_FindVar(const char *name){static cvar_t var;assert(!strcmp(name,"fixture"));return exists ? &var : NULL;}
char *Cvar_GetVariantString(const char *name){assert(exists && !strcmp(name,"fixture"));return raw;}
void Scr_AddVector(const float *v){memcpy(result,v,sizeof(result));++outputs;}
void Scr_Error(const char *s){assert(s && *s);++errors;}
void GScr_SetCvar(void){assert(0);}
int main(void)
{
    CODOL_Scr_GetDvarVector();assert(outputs==1 && result[0]==1 && result[2]==3);
    raw="(-1.5, 2e1, 3) trailing";CODOL_Scr_GetDvarVector();
    assert(outputs==2 && result[0]==-1.5f && result[1]==20 && result[2]==3);
    argc=2;exists=0;CODOL_Scr_GetDvarVector();assert(outputs==3 && result[0]==4 && result[2]==6);
    exists=1;raw="";CODOL_Scr_GetDvarVector();assert(errors==1 && outputs==3);
    raw="1 2";CODOL_Scr_GetDvarVector();assert(errors==2 && outputs==3);
    raw="1,2,3";CODOL_Scr_GetDvarVector();assert(errors==3 && outputs==3);
    exists=0;argc=1;CODOL_Scr_GetDvarVector();assert(errors==4 && outputs==3);
    argc=0;CODOL_Scr_GetDvarVector();argc=3;CODOL_Scr_GetDvarVector();
    assert(errors==6 && outputs==3);
    puts("PASS: dvar vector parsing, missing versus empty, explicit defaults and argument errors");
}
