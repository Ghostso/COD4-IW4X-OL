#include "codol_character_variant.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
int main(void)
{
    const char *m[]={"10","source","cha","fja","20","rig_a","cha","bar","21","rig_b","cha","bar"};
    const char *r[]={"source","rig_a","1","0","source","rig_b","0","1","source","rig_b","1","0"};
    codol_engine_table_t market={"market",4,3,m},rigs={"rigs",4,3,r};
    uint16_t slots[18]={0},before[18];unsigned selector=99,expected[]={0,4,2,1,3};
    for(unsigned i=0;i<5;++i)assert(CODOL_ChestRigSelector(i,&selector) && selector==expected[i]);
    assert(!CODOL_ChestRigSelector(5,&selector) && selector==3);
    slots[5]=10;slots[15]=99;
    assert(CODOL_ApplyCharacterChestRig(&market,&rigs,0,slots) && slots[15]==21);
    assert(CODOL_ApplyCharacterChestRig(&market,&rigs,1,slots) && slots[15]==21);
    r[10]="01";
    assert(CODOL_ApplyCharacterChestRig(&market,&rigs,0,slots) && slots[15]==20);
    r[0]="SOURCE";slots[15]=99;
    assert(CODOL_ApplyCharacterChestRig(&market,&rigs,0,slots) && slots[15]==99);
    r[0]="source";r[10]="1";r[9]="missing";
    assert(CODOL_ApplyCharacterChestRig(&market,&rigs,0,slots) && slots[15]==0);
    r[9]="rig_b";m[8]="70000";slots[15]=99;memcpy(before,slots,sizeof(slots));
    assert(!CODOL_ApplyCharacterChestRig(&market,&rigs,0,slots) && !memcmp(before,slots,sizeof(slots)));
    assert(!CODOL_ApplyCharacterChestRig(&market,&rigs,2,slots));
    slots[5]=0;assert(CODOL_ApplyCharacterChestRig(&market,&rigs,0,slots) && slots[15]==99);
    /* A negative signed profile short cannot select a marketplace vest,
     * even if its unsigned spelling happens to exist in the table. */
    m[0]="65535";slots[5]=65535;
    assert(CODOL_ApplyCharacterChestRig(&market,&rigs,0,slots) && slots[15]==99);
    puts("PASS: chest-rig active column, exact flags, last-row replacement, missing-ID clear and atomic errors");
}
