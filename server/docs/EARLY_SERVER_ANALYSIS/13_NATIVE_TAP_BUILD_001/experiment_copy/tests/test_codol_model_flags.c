#include "xassets/xmodel.h"
#include <assert.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
extern unsigned XModelGetFlags(const XModel *);
int main(void)
{
    XModel model={0}; unsigned i;
    _Static_assert(offsetof(XModel,flags)==0xd0,"retained flags offset");
    for(i=0;i<256;++i) {
        unsigned char flags=(unsigned char)i; memcpy(&model.flags,&flags,1);
        model.field_D1=0x55; model.field_D2=0x66; model.field_D3=0x77;
        assert(XModelGetFlags(&model)==i);
    }
    puts("PASS: all model flag bytes through retained assembly getter"); return 0;
}
