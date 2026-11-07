#include "codol_structured_data.h"
#include <assert.h>
#include <string.h>
#include <stdio.h>
int main(void)
{
    /* Nonidentity map, including unaligned int and two bits in one byte. */
    uint8_t map[]={5,0,0,0, 2,0,0,0, 9,0,0,0, 15,0,0,0};
    uint8_t record[12],saved[12]; uint32_t value=0xdeadbeef;
    codol_structured_layout_t layout={map,sizeof(map),9};
    memset(record,0xa5,sizeof(record));
    assert(CODOL_StructuredWriteScalar(&layout,0,0,record,sizeof(record),0x89abcdef));
    assert(!memcmp(record+5,"\xef\xcd\xab\x89",4) && record[9]==0xa5);
    assert(CODOL_StructuredReadScalar(&layout,0,0,record,sizeof(record),&value) && value==0x89abcdef);
    assert(CODOL_StructuredWriteScalar(&layout,1,1,record,sizeof(record),0x34) && record[2]==0x34);
    assert(CODOL_StructuredReadScalar(&layout,1,1,record,sizeof(record),&value) && value==0x34);
    assert(CODOL_StructuredWriteScalar(&layout,2,2,record,sizeof(record),1));
    assert(record[1]==0xa7);
    assert(CODOL_StructuredWriteScalar(&layout,2,3,record,sizeof(record),0) && record[1]==0x27);
    assert(CODOL_StructuredReadScalar(&layout,2,2,record,sizeof(record),&value) && value==1);
    memcpy(saved,record,sizeof(record));
    assert(!CODOL_StructuredWriteScalar(&layout,1,1,record,sizeof(record),0x1234));
    assert(!CODOL_StructuredWriteScalar(&layout,2,2,record,sizeof(record),2));
    assert(!CODOL_StructuredWriteScalar(&layout,0,4,record,sizeof(record),0));
    assert(!CODOL_StructuredWriteScalar(&layout,3,0,record,sizeof(record),0));
    assert(!CODOL_StructuredWriteScalar(&layout,0,0,record,8,0));
    map[0]=6; assert(!CODOL_StructuredWriteScalar(&layout,0,0,record,sizeof(record),0));
    assert(!CODOL_StructuredReadScalar(&layout,0,0,record,sizeof(record),&value) && value==1);
    assert(!memcmp(record,saved,sizeof(record)));
    layout.offset_map_size=15;
    assert(!CODOL_StructuredReadScalar(&layout,1,0,record,sizeof(record),&value));
    layout.offset_map_size=sizeof(map);map[0]=7;
    assert(CODOL_StructuredWriteScalar(&layout,9,0,record,sizeof(record),0x1234ffff));
    assert(record[7]==255 && record[8]==255 && record[9]==0xa5);
    assert(CODOL_StructuredReadScalar(&layout,9,0,record,sizeof(record),&value) && value==65535);
    map[0]=8;memcpy(saved,record,sizeof(record));
    assert(!CODOL_StructuredWriteScalar(&layout,9,0,record,sizeof(record),0));
    assert(!memcmp(saved,record,sizeof(record)));
    map[0]=5;
    {
        const uint32_t bits[]={0,0x80000000,0x3f800000,0x7f800000,0x7fc12345,0xffffffff};
        unsigned i;
        for(i=0;i<sizeof(bits)/sizeof(bits[0]);++i) {
            assert(CODOL_StructuredWriteScalar(&layout,8,0,record,sizeof(record),bits[i]));
            assert(CODOL_StructuredReadScalar(&layout,8,0,record,sizeof(record),&value));
            assert(value==bits[i] && record[9]==0xa5);
        }
    }
    map[0]=6;memcpy(saved,record,sizeof(record));
    assert(!CODOL_StructuredWriteScalar(&layout,8,0,record,sizeof(record),0));
    assert(!CODOL_StructuredReadScalar(&layout,8,0,record,sizeof(record),&value) && value==0xffffffff);
    assert(!memcmp(saved,record,sizeof(record)));
    puts("PASS: structured scalar map addressing, LE unaligned storage, bit preservation and atomic bounds failures");
}
