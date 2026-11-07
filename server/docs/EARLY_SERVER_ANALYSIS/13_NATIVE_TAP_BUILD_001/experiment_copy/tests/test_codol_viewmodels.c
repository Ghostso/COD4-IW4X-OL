/* Exercise the actual captured state and archive codec, not a live-client
 * lookup: following an older state must retain its old gloves. */
#include "g_shared.h"
#include "server.h"
#include "codol_playerstate_ext.h"
#include "qcommon.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static gclient_t clients[2];
static client_t snapshots[1];
const void *CODOL_PlayerStateExtLiveBase(unsigned *n){*n=2;return clients;}
const void *CODOL_PlayerStateExtSnapshotBase(unsigned *n){*n=1;return snapshots;}
const void *CODOL_PlayerStateExtArchiveBase(unsigned *n){*n=0;return NULL;}
void Com_PrintWarning(conChannel_t c,const char *f,...){(void)c;(void)f;}
qboolean Assert_MyHandler(const char *e,const char *f,int l,const char *fn,const char *fmt,...)
{(void)fmt;fprintf(stderr,"%s %s:%d %s\n",e,f,l,fn);abort();}
static void roundtrip(const codol_ps_ext_t *state,const codol_ps_ext_t *base,
                      codol_ps_ext_t *out)
{
    byte data[4096];msg_t msg;int size;
    MSG_Init(&msg,data,sizeof(data));
    CODOL_PlayerStateExtWrite(&msg,state,base);
    assert(!msg.overflowed);size=msg.cursize;
    MSG_Init(&msg,data,sizeof(data));msg.cursize=size;
    CODOL_PlayerStateExtRead(&msg,out,base);
    assert(!msg.overflowed);
}
int main(void)
{
    codol_ps_ext_t captured,decoded,reset={0};
    playerState_t *ps=&clients[0].ps,*follow=&clients[1].ps;
    assert(CODOL_PlayerStateSetViewmodels(ps,17,29));
    assert(ps->viewmodelIndex==17);
    captured=*CODOL_PlayerStateExtConst(ps);
    assert(captured.viewhands_model==29);
    {
        playerState_t *snapshot=&snapshots[0].frames[0].ps;
        *snapshot=*ps;
        assert(CODOL_PlayerStateExtCopy(snapshot,ps));
        assert(CODOL_PlayerStateSetViewmodels(snapshot,18,30));
        assert(snapshot->viewmodelIndex==18 &&
               CODOL_PlayerStateExtConst(snapshot)->viewhands_model==30);
        assert(ps->viewmodelIndex==17 && CODOL_PlayerStateExtConst(ps)->viewhands_model==29);
    }
    /* Retained setViewModel may replace the arm after loadout selection. The
     * per-snapshot appearance producer must be able to restore both values. */
    ps->viewmodelIndex=3;
    assert(CODOL_PlayerStateSetViewmodels(ps,17,29));
    assert(ps->viewmodelIndex==17 && CODOL_PlayerStateExtConst(ps)->viewhands_model==29);
    /* CoDOL's extended native model bank accepts 512..2047 as well. */
    assert(CODOL_PlayerStateSetViewmodels(ps,17,CODOL_NATIVE_MODELS-1));
    assert(CODOL_PlayerStateExtConst(ps)->viewhands_model==CODOL_NATIVE_MODELS-1);
    assert(!CODOL_PlayerStateSetViewmodels(ps,17,CODOL_NATIVE_MODELS));
    assert(CODOL_PlayerStateExtConst(ps)->viewhands_model==CODOL_NATIVE_MODELS-1);
    assert(CODOL_PlayerStateSetViewmodels(ps,17,29));
    *follow=*ps;assert(CODOL_PlayerStateExtCopy(follow,ps));
    assert(CODOL_PlayerStateSetViewmodels(ps,18,30));
    assert(CODOL_PlayerStateExtConst(follow)->viewhands_model==29);
    roundtrip(&captured,NULL,&decoded);assert(decoded.viewhands_model==29);
    roundtrip(CODOL_PlayerStateExtConst(ps),&captured,&decoded);
    assert(decoded.viewhands_model==30);
    roundtrip(&reset,&captured,&decoded);assert(!decoded.viewhands_model);
    CODOL_PlayerStateExtClearClientViewhands(0);
    assert(!CODOL_PlayerStateExtConst(ps)->viewhands_model);
    assert(CODOL_PlayerStateExtConst(follow)->viewhands_model==29);
    /* The relocated inventory record: a sparse owned set including a native
     * index past the old 128 ceiling, full and delta, and the unowned model
     * dropped by the encoding. */
    {
        codol_ps_ext_t armed=captured,empty=captured;
        static const unsigned owned[]={3,128,650};
        unsigned k;
        for(k=0;k<3;++k) armed.weapons[owned[k]>>5]|=1u<<(owned[k]&31);
        armed.weaponold[3>>5]|=1u<<3;
        armed.weaponrechamber[650>>5]|=1u<<(650&31);
        armed.weaponmodels[3]=7;armed.weaponmodels[650]=0xab;
        armed.weaponmodels[5]=9; /* not owned: must not survive */
        armed.weapons_known=1;
        roundtrip(&armed,NULL,&decoded);
        for(k=0;k<3;++k) assert(decoded.weapons[owned[k]>>5]&(1u<<(owned[k]&31)));
        assert(decoded.weapons_known==1);
        assert(decoded.weaponold[0]==(1u<<3) && decoded.weaponrechamber[650>>5]==(1u<<(650&31)));
        assert(decoded.weaponmodels[3]==7 && decoded.weaponmodels[650]==0xab && !decoded.weaponmodels[5]);
        assert(!memcmp(decoded.weapons,armed.weapons,sizeof(armed.weapons)));
        /* Unchanged against its own baseline. */
        roundtrip(&armed,&armed,&decoded);
        assert(decoded.weapons_known==1 && decoded.weaponmodels[650]==0xab &&
               !memcmp(decoded.weapons,armed.weapons,sizeof(armed.weapons)));
        /* A state that dropped weapon 650 and its model, delta'd against the
         * armed baseline, and an emptied-but-known inventory. */
        empty=armed;
        empty.weapons[650>>5]&=~(1u<<(650&31));
        roundtrip(&empty,&armed,&decoded);
        assert(!(decoded.weapons[650>>5]&(1u<<(650&31))) && !decoded.weaponmodels[650] &&
               !decoded.weaponrechamber[650>>5] && decoded.weaponmodels[3]==7);
        memset(empty.weapons,0,sizeof(empty.weapons));
        roundtrip(&empty,&armed,&decoded);
        assert(decoded.weapons_known==1 && !decoded.weapons[0] && !decoded.weaponmodels[3]);
        /* Never-recorded against a recorded baseline. */
        roundtrip(&captured,&armed,&decoded);
        assert(!decoded.weapons_known && !decoded.weaponmodels[650]);
        assert(CODOL_PlayerStateExtInventoryTruncations()==0);
    }
    puts("PASS: separate viewhands selection, validation, captured follow state and full/delta archive");
    return 0;
}
