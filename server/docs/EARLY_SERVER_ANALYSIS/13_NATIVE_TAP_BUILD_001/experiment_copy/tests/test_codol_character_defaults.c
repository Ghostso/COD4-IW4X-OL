#include "codol_character_variant.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
int main(void)
{
    const char *m[]={"135","character","cha","heg","100","boots","cha","boo","101","coat","cha","fja","102","BOOTS","cha","boo"};
    const char *c[21]={"character","tf","id"};
    codol_engine_table_t market={"market",4,4,m},characters={"characters",21,1,c};
    uint16_t slots[18]={0},before[18];unsigned i;
    for(i=3;i<21;++i)c[i]="";
    c[3]="boots";c[4]="coat";c[20]="coat";slots[1]=999;
    assert(CODOL_ApplyCharacterDefaults(&market,&characters,135,slots));
    assert(slots[0]==102 && slots[1]==999 && slots[17]==101);
    memset(slots,0,sizeof(slots));memcpy(before,slots,sizeof(slots));
    m[8]="70000";
    assert(!CODOL_ApplyCharacterDefaults(&market,&characters,135,slots) && !memcmp(slots,before,sizeof(slots)));
    m[8]="101";c[4]="missing";
    assert(CODOL_ApplyCharacterDefaults(&market,&characters,135,slots) && !slots[1] && slots[17]==101);
    memcpy(before,slots,sizeof(slots));
    assert(CODOL_ApplyCharacterDefaults(&market,&characters,555,slots) && !memcmp(slots,before,sizeof(slots)));
    characters.columnCount=20;
    assert(!CODOL_ApplyCharacterDefaults(&market,&characters,135,slots));
    puts("PASS: eighteen-slot defaults, preserved overrides, reverse name lookup and atomic invalid IDs");
}
