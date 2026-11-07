#include "server.h"
#include "codol_clientstate_ext.h"
#include "qcommon.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
serverStatic_t svs;
svsHeader_t svsHeader;
qboolean Assert_MyHandler(const char *e,const char *f,int l,const char *fn,const char *fmt,...)
{(void)fmt;fprintf(stderr,"%s %s:%d %s\n",e,f,l,fn);abort();}
static unsigned field(const codol_client_state_t *s,unsigned offset)
{
    unsigned i;for(i=0;i<CODOL_CLIENT_FIELDS;++i)
        if(CODOL_ClientField(i)->offset==offset)return s->field[i];
    abort();
}
int main(void)
{
    codol_client_appearance_t a={0},b={0},bad;
    codol_client_state_t out={0};
    byte data[4096];msg_t msg;int size;unsigned i;
    svs.numSnapshotClients=2;
    svsHeader.numSnapshotClients=2;
    svsHeader.snapshotClients=svs.snapshotClients;
    svs.snapshotClients[0].clientIndex=0;
    svs.snapshotClients[1].clientIndex=0;
    svsHeader.nextSnapshotClients=1;
    a.model=99;
    for(i=0;i<CODOL_CLIENT_ATTACHMENTS;++i)a.attach_model[i]=100+i;
    assert(CODOL_PublishClientAppearance(0,&a));
    assert(CODOL_CapturePublishedClientAbilities(0,0));
    b.model=222;b.attach_model[0]=223;
    assert(CODOL_PublishClientAppearance(0,&b));
    assert(CODOL_OverlayCapturedClientAbilities(0,&out));
    assert(field(&out,0x14)==99 && field(&out,0x5c)==115);
    bad=b;bad.attach_model[2]=224; /* Hole before a present part. */
    assert(!CODOL_PublishClientAppearance(0,&bad));
    assert(CODOL_CapturePublishedClientAbilities(1,0));
    svsHeader.nextSnapshotClients=2;
    assert(CODOL_OverlayCapturedClientAbilities(1,&out));
    assert(field(&out,0x14)==222 && field(&out,0x20)==223 && !field(&out,0x5c));
    /* Archive old A, change live to B, decode A and recapture its own set. */
    assert(CODOL_PublishClientAppearance(0,&a));
    svs.cachedSnapshotClients[0].cs.clientIndex=0;
    MSG_Init(&msg,data,sizeof(data));
    CODOL_WriteArchivedClientAbilities(&msg,0,&svs.cachedSnapshotClients[0].cs);
    assert(!msg.overflowed);size=msg.cursize;
    assert(CODOL_PublishClientAppearance(0,&b));
    MSG_Init(&msg,data,sizeof(data));msg.cursize=size;
    CODOL_ReadArchivedClientAbilities(&msg,&svs.cachedSnapshotClients[0].cs);
    assert(!msg.overflowed);
    assert(CODOL_CaptureArchivedClientAbilities(2,&svs.cachedSnapshotClients[0].cs));
    svsHeader.nextSnapshotClients=3;
    assert(CODOL_OverlayCapturedClientAbilities(2,&out));
    assert(field(&out,0x14)==99 && field(&out,0x5c)==115);
    CODOL_ClearPublishedClientAbilities(0);
    assert(CODOL_OverlayCapturedClientAbilities(2,&out));
    assert(field(&out,0x5c)==115);
    /* An explicitly empty appearance clears all old parts. */
    memset(&b,0,sizeof(b));assert(CODOL_PublishClientAppearance(0,&b));
    assert(CODOL_CapturePublishedClientAbilities(3,0));
    svsHeader.nextSnapshotClients=4;
    assert(CODOL_OverlayCapturedClientAbilities(3,&out));
    assert(!field(&out,0x14) && !field(&out,0x5c));
    puts("PASS: sixteen-part appearance capture, replacement, archive ownership and clear");
    return 0;
}
