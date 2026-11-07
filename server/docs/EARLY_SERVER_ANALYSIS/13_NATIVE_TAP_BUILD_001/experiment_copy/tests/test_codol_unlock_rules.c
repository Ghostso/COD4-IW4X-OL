#include "codol_unlock_rules.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static int rank=4,stage=2,override,available=1,override_available=1,calls;
static char last_key[64];
static int read_value(void *context,const char *group,const char *key,int *out)
{
    assert(context==&rank);++calls;
    if(!available)return 0;
    if(!strcmp(group,"experienceRank"))*out=rank;
    else if(!strcmp(group,"titleUnlocked") || !strcmp(group,"iconUnlocked")) {
        if(!override_available)return 0;*out=override;
    }
    else {assert(!strcmp(group,"challengeState"));strcpy(last_key,key);*out=stage;}
    return 1;
}
static int evaluate(const char *category,const char *required,const char *challenges)
{
    int result=-7;
    assert(CODOL_EvaluateUnlockRule("fixture",category,required,challenges,read_value,&rank,&result));
    return result;
}
int main(void)
{
    assert(evaluate("feature","0","")==1);
    assert(evaluate("feature","4","ch_ghillie")==1 && !strcmp(last_key,"ch_ghillie"));
    assert(evaluate("feature","4","ch_ghillie_2")==0);
    stage=3;assert(evaluate("feature","4","ch_ghillie_2")==1);
    assert(evaluate("feature","4","ch_ghillie_3")==0);
    rank=3;calls=0;assert(evaluate("feature","4","ch_ghillie")==0 && calls==1);
    override=1;calls=0;assert(evaluate("title","99","ch_ghillie_9")==1 && calls==1);
    assert(evaluate("icon","99","ch_ghillie_9")==1);
    override=0;assert(evaluate("title","99","")==0);
    rank=4;stage=4;assert(evaluate("feature","4"," ; ch_ghillie_2\t; ch_other_3 ; ")==1);
    assert(!strcmp(last_key,"ch_other"));
    assert(evaluate("feature","","x_12")==1 && !strcmp(last_key,"x_12"));
    assert(evaluate("feature","","_2")==1 && !strcmp(last_key,"_2"));
    override_available=0;int result=77;
    assert(evaluate("title","4","ch_ghillie_2")==1);
    assert(evaluate("icon","4","ch_ghillie_2")==1);
    assert(!CODOL_EvaluateUnlockRule("x","title","5","",read_value,&rank,&result) && result==77);
    assert(!CODOL_EvaluateUnlockRule("x","icon","4","ch_ghillie_4",read_value,&rank,&result) && result==77);
    available=0;
    assert(!CODOL_EvaluateUnlockRule("x","feature","999999999999999999999999","",read_value,&rank,&result) && result==77);
    assert(!CODOL_EvaluateUnlockRule("x","feature","0","",read_value,&rank,&result) && result==77);
    assert(!CODOL_EvaluateUnlockRule("x","feature","","ch",read_value,&rank,&result) && result==77);
    assert(evaluate("feature","","")==1);
    puts("PASS: native IW4 unlock rules, ghillie stages, rank gating, overrides and unavailable data");
}
