#include "codol_map_custom.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
int main(void)
{
    const char data[]="// map metadata\n{map other environment arctic}\n{environment \"urban\" /* keep */ map \"mp_bog_sh\" allieschar \"team // literal\" empty \"\"}";
    char out[128]="unchanged";
    assert(CODOL_MapCustom(data,sizeof(data)-1,"MP_BOG_SH","ENVIRONMENT",out,sizeof(out))==1 && !strcmp(out,"urban"));
    assert(CODOL_MapCustom(data,sizeof(data)-1,"mp_bog_sh","allieschar",out,sizeof(out))==1 && !strcmp(out,"team // literal"));
    assert(CODOL_MapCustom(data,sizeof(data)-1,"mp_bog_sh","empty",out,sizeof(out))==1 && !*out);
    strcpy(out,"unchanged");
    assert(!CODOL_MapCustom(data,sizeof(data)-1,"missing","environment",out,sizeof(out)) && !strcmp(out,"unchanged"));
    assert(!CODOL_MapCustom(data,sizeof(data)-1,"mp_bog_sh","absent",out,sizeof(out)));
    assert(CODOL_MapCustom(data,sizeof(data)-1,"mp_bog_sh","environment",out,3)==-1 && !strcmp(out,"unchanged"));
    const char *bad[]={"{map x", "{map}","{map \"x}","/* unfinished","{map x}{broken}"};
    for(unsigned i=0;i<5;++i)assert(CODOL_MapCustom(bad[i],strlen(bad[i]),"x","map",out,sizeof(out))==-1 && !strcmp(out,"unchanged"));
    puts("PASS: arena lookup, key ordering, case, quotes/comments, missing values and malformed records");
}
