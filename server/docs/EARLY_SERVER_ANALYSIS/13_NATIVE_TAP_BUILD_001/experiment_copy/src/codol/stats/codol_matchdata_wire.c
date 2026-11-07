#include "codol_matchdata.h"
int CODOL_WriteClientMatchDataSection(codol_msg_t *m,const char *name,
    const uint8_t *record,size_t record_size)
{
    size_t n,needed;
    if(!m)return 0;
    if(m->failed || !m->data || !name || !*name || !record ||
       record_size!=CODOL_CLIENT_MATCHDATA_CAPACITY)goto fail;
    for(n=0;n<64 && name[n];++n) {}
    if(n==64)goto fail;
    needed=1+n+1+CODOL_CLIENT_MATCHDATA_CAPACITY;
    if(m->size>m->capacity || needed>m->capacity-m->size)goto fail;
    CODOL_WriteByte(m,4);CODOL_WriteData(m,name,n+1);
    CODOL_WriteData(m,record,record_size);return 1;
fail:m->failed=1;return 0;
}
