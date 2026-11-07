#include "codol_character_variant.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
int main(void)
{
    const char *cells[]={
        "coat","model","m tf urb","exact_cau",
        "coat","model","s ss sss","shared_wht",
        "coat","model","f tf urb","wrong_gender_wht",
        "coat","model","m sc urb","wrong_faction_wht",
        "coat","model","m tf des","wrong_camo_wht",
        "coat","model","m tf urb","last_exact_cau"};
    codol_engine_table_t table={"parts",4,6,cells}; unsigned row=99;const char *value="unchanged";
    assert(CODOL_CharacterVariant(&table,"coat","model",0,0,"urb","wht",&row,&value)==1);
    assert(row==1 && !strcmp(value,"shared_wht"));
    assert(CODOL_CharacterVariant(&table,"coat","model",0,0,"urb","cau",&row,&value)==1 && row==5);
    assert(CODOL_CharacterVariant(&table,"coat","model",1,0,"urb","wht",&row,&value)==1 && row==2);
    assert(CODOL_CharacterVariant(&table,"coat","model",0,1,"urb","wht",&row,&value)==1 && row==3);
    assert(CODOL_CharacterVariant(&table,"coat","model",0,0,"des","wht",&row,&value)==1 && row==4);
    row=99;value="unchanged";
    assert(!CODOL_CharacterVariant(&table,"missing","model",0,0,"urb","wht",&row,&value));
    assert(row==99 && !strcmp(value,"unchanged"));
    cells[6]="s zm sss";
    assert(!CODOL_CharacterVariant(&table,"coat","model",1,1,"woo","wht",&row,&value));
    assert(row==99);
    cells[20]="other"; /* A different item terminates backward group traversal. */
    cells[16]="coat";cells[12]="other";
    assert(!CODOL_CharacterVariant(&table,"coat","model",0,0,"urb","cau",&row,&value));
    cells[18]="short";
    assert(CODOL_CharacterVariant(&table,"coat","model",0,0,"urb","cau",&row,&value)==-1 && row==99);
    assert(CODOL_CharacterVariant(&table,"coat","model",0,3,"urb","wht",&row,&value)==-1);
    puts("PASS: C1 character variants, skin priority, shared fallback, reverse ties and contiguous groups");
}
