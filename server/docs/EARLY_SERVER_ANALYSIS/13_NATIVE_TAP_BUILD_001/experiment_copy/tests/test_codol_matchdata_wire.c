#include "codol_matchdata.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
int main(void)
{
    uint8_t data[1200],saved[1200],record[1024];codol_msg_t m;size_t i,bit,n;
    const char name[]="mp/clientmatchdata.def";char longname[65];
    for(i=0;i<sizeof(record);++i)record[i]=(uint8_t)(i*17);
    memset(data,0xa5,sizeof(data));CODOL_MsgWriteInit(&m,data,sizeof(data));
    CODOL_WriteBits(&m,1,1);bit=m.bit;
    assert(CODOL_WriteClientMatchDataSection(&m,name,record,sizeof(record)));
    assert(m.bit==bit && data[0]==1 && data[1]==4);
    assert(!memcmp(data+2,name,sizeof(name)));
    assert(!memcmp(data+2+sizeof(name),record,sizeof(record)));
    assert(m.size==2+sizeof(name)+sizeof(record));
    CODOL_WriteBits(&m,1,1);assert(data[0]==3);
    CODOL_WriteByte(&m,5);assert(data[m.size-1]==5);
    n=1+sizeof(name)+sizeof(record);
    for(i=0;i<n;++i) {
        memset(data,0xa5,sizeof(data));memcpy(saved,data,sizeof(data));
        CODOL_MsgWriteInit(&m,data,i);
        assert(!CODOL_WriteClientMatchDataSection(&m,name,record,sizeof(record)));
        assert(m.failed && !m.size && !m.bit && !memcmp(data,saved,sizeof(data)));
    }
    CODOL_MsgWriteInit(&m,data,n);
    assert(CODOL_WriteClientMatchDataSection(&m,name,record,sizeof(record)) && m.size==n);
    memset(longname,'x',64);longname[64]=0;
    CODOL_MsgWriteInit(&m,data,sizeof(data));
    assert(!CODOL_WriteClientMatchDataSection(&m,longname,record,1024));
    longname[63]=0;CODOL_MsgWriteInit(&m,data,sizeof(data));
    assert(CODOL_WriteClientMatchDataSection(&m,longname,record,1024));
    CODOL_MsgWriteInit(&m,data,sizeof(data));
    assert(!CODOL_WriteClientMatchDataSection(&m,name,record,1023));
    CODOL_MsgWriteInit(&m,data,sizeof(data));
    assert(!CODOL_WriteClientMatchDataSection(&m,"",record,1024));
    puts("PASS: match-data wire section, full record, interleaved bits and atomic capacity failures");
}
