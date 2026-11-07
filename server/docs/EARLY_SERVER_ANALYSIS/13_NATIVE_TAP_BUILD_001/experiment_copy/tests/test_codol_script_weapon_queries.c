#include "scr_vm_functions.h"
#include "codol_weapon_native.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static struct WeaponDef definition;
static int index_value, flag_value, available, result, errors, reads;
char *Scr_GetString(unsigned int index) { assert(index==0); return "test_weapon"; }
int G_GetWeaponIndexForName(const char *name) { assert(!strcmp(name,"test_weapon")); return index_value; }
struct WeaponDef *BG_GetWeaponDef(int index) { assert(index==index_value && index); return &definition; }
int CODOL_GetNativeWeaponInheritsPerks(const struct WeaponDef *d,int *out)
{ assert(d==&definition); ++reads; if(!available) return 0; *out=flag_value; return 1; }
void Scr_AddInt(int value) { result=value; }
void Scr_Error(const char *message) { assert(strstr(message,"metadata")); ++errors; }
int main(void)
{
    result=-1; CODOL_Scr_WeaponInheritsPerks(); assert(result==1 && !reads && !errors);
    index_value=7; available=1;
    for(flag_value=0;flag_value<2;++flag_value) {
        result=-1; CODOL_Scr_WeaponInheritsPerks(); assert(result==flag_value && !errors);
    }
    available=0; result=-1; CODOL_Scr_WeaponInheritsPerks(); assert(errors==1 && result==-1);
    puts("PASS: native weapon query resolution, zero-index behavior, both flag values and missing metadata error");
}
