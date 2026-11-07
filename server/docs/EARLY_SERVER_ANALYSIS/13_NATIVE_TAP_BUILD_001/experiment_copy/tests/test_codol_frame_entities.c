#include "server.h"
#include "codol_sv_entities.h"
#include "codol_entitystate_ext.h"
#include "qcommon_io.h"
#include "codol_usercmd.h"
#include "bg.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
svsHeader_t svsHeader;
/* This fixture keeps trace logging disabled; the model-scale producer is
 * linked from its real source so entity snapshots use its normal default. */
cvar_t *codol_debugTrace;
void QDECL Com_Printf(conChannel_t channel,const char *fmt,...)
{ (void)channel; (void)fmt; assert(!"unexpected entity trace"); }
static unsigned calls,fail_on,suppressed_slots;
static uint32_t word(const codol_entity_state_t *s,unsigned offset)
{
    unsigned i; for(i=0;i<CODOL_ENTITY_FIELDS;++i)
        if(CODOL_EntityField(s->type,i)->offset==offset) return s->field[i];
    assert(0); return 0;
}
static int resolve(void *ctx,const entityState_t *s,codol_snapshot_entity_bindings_t *b)
{
    unsigned i; assert(ctx==&calls); ++calls;
    if(fail_on==calls) return 0;
    b->state.type=s->eType; b->primary_weapon=s->weapon;
    if(suppressed_slots) {
        /* This fixture owns the already-resolved stance parameter. The
         * unknown event in slot1 deliberately has no semantic binding. */
        memset(b->event_parameters,0,sizeof(b->event_parameters));
        b->event_parameters[2]=3;
        b->event_suppressed_slots=suppressed_slots;
    } else if(!CODOL_ResolveEngineEntityEventParameters(s,b->event_parameters)) return 0;
    /* Distinct seed metadata must survive common-field overlay. */
    for(i=0;i<CODOL_ENTITY_FIELDS;++i)
        if(CODOL_EntityField(b->state.type,i)->offset==0x098) b->state.field[i]=17;
    return 1;
}
/* The entity event counter belongs to the state now: this harness binds its
 * own ring as the snapshot storage the resolver walks and drives the producer
 * hook, so the collected counters are the ring slots' own epochs. */
static entityState_t ring[4]={{0}};
const void *CODOL_EntityStateExtLiveBase(unsigned *count){if(count)*count=0;return NULL;}
const void *CODOL_EntityStateExtSnapshotBase(unsigned *count){if(count)*count=4;return ring;}
const void *CODOL_EntityStateExtArchiveBase(unsigned *count){if(count)*count=0;return NULL;}
void Com_PrintWarning(conChannel_t channel,const char *fmt,...){(void)channel;(void)fmt;}
static void produced(entityState_t *es,unsigned times)
{ while(times--) { es->eventSequence=(es->eventSequence+1)&255; CODOL_EntityStateEventAdded(es); } }
int main(void)
{
    codol_entity_state_t out[2],saved[2];
    unsigned i;
    svsHeader.snapshotEntities=ring; svsHeader.numSnapshotEntities=4; svsHeader.nextSnapshotEntities=5;
    ring[3].number=2; ring[3].eType=ET_GENERAL; produced(&ring[3],255);
    ring[3].lerp.pos.trBase[0]=123;
    { uint32_t event=EV_STANCE_FORCE_STAND,reason=3;
      memcpy(&ring[3].events[2],&event,4); memcpy(&ring[3].eventParms[2],&reason,4); }
    ring[0].number=9; ring[0].eType=ET_PLAYER; ring[0].clientNum=3;
    ring[0].weapon=7; ring[0].legsAnim=1536; ring[0].torsoAnim=1023;
    produced(&ring[0],1);
    CODOL_ResetWeaponMap(); assert(CODOL_MapWeapon(777,7));
    memset(out,0xa5,sizeof(out));
    assert(CODOL_CollectServerEntities(3,2,out,2,resolve,&calls));
    assert(calls==2 && out[0].number==2 && out[1].number==9);
    assert(word(&out[0],0x98)==17 && word(&out[0],0x18)==0x42f60000);
    assert(word(&out[0],0xbc)==6 && word(&out[0],0xcc)==3);
    assert(word(&out[1],0xd8)==1536 && word(&out[1],0xdc)==1023);
    assert(word(&out[1],0xd4)==(777u|(777u<<16)));
    assert(word(&out[0],0xb0)==255 && word(&out[1],0xb0)==1);
    memcpy(saved,out,sizeof(out));
    produced(&ring[3],1); produced(&ring[0],1);
    for(i=0;i<8;++i) {
        int first=3,count=2; size_t cap=2;
        calls=0; fail_on=0;
        if(i==0) fail_on=2;
        if(i==1) first=0; /* Expired span. */
        if(i==2) count=3; /* Past next snapshot index. */
        if(i==3) cap=1;
        if(i==4) count=0; /* An empty span converts nothing. */
        if(i==5) ring[0].number=2; /* Duplicate IDs cannot enter delta merge. */
        if(i==6) ring[0].legsAnim=2048; /* Failure after earlier entity converted. */
        assert(i==4 ? CODOL_CollectServerEntities(first,count,out,cap,i==7?NULL:resolve,&calls)
                    : !CODOL_CollectServerEntities(first,count,out,cap,i==7?NULL:resolve,&calls));
        assert(!memcmp(out,saved,sizeof(out)));
        ring[0].number=9; ring[0].legsAnim=1536;
    }
    fail_on=0; calls=0;
    assert(CODOL_CollectServerEntities(3,2,out,2,resolve,&calls));
    assert(word(&out[0],0xb0)==256 && word(&out[1],0xb0)==2);
    assert(CODOL_CollectServerEntities(5,0,NULL,0,NULL,NULL));
    assert(!CODOL_CollectServerEntities(6,0,NULL,0,NULL,NULL));
    CODOL_ResetEntityEventEpochs();
    assert(CODOL_CollectCurrentServerEntities(3,2,out,2,resolve,&calls));
    assert(CODOL_CollectCurrentServerEntities(3,2,out,2,resolve,&calls));
    assert(word(out,0xb0)==256 && word(out+1,0xb0)==2);
    /* Recipient re-sampling of the same frame must not advance either clock. */
    assert(CODOL_CollectCurrentServerEntities(3,2,out,2,resolve,&calls));
    assert(word(out,0xb0)==256 && word(out+1,0xb0)==2);
    /* The live clears do not touch a snapshot ring slot's own history. */
    CODOL_ResetEntityEventEpoch(ENTITYNUM_NONE);
    CODOL_ResetEntityEventEpochs();
    assert(CODOL_CollectCurrentServerEntities(3,2,out,2,resolve,&calls));
    assert(word(out,0xb0)==256 && word(out+1,0xb0)==2);
    {
        size_t emitted=99;
        memcpy(saved,out,sizeof(out));
        calls=0; fail_on=1;
        assert(CODOL_CollectServerEntitiesEmitted(3,2,out,2,resolve,&calls,&emitted));
        assert(emitted==1 && out[0].number==9);
        assert(word(out,0xb0)==2); /* Filtering does not advance the epoch. */
        assert(!memcmp(out+1,saved+1,sizeof(out[1])));

        memcpy(out,saved,sizeof(out));
        ring[0].number=2; calls=0; fail_on=1; emitted=99;
        assert(!CODOL_CollectServerEntitiesEmitted(3,2,out,2,resolve,&calls,&emitted));
        assert(!emitted && !memcmp(out,saved,sizeof(out)));
        ring[0].number=1; calls=0; emitted=99;
        assert(!CODOL_CollectServerEntitiesEmitted(3,2,out,2,resolve,&calls,&emitted));
        assert(!emitted && !memcmp(out,saved,sizeof(out)));
        ring[0].number=9; fail_on=0;
        emitted=99;
        assert(!CODOL_CollectServerEntitiesEmitted(6,0,out,2,resolve,&calls,&emitted));
        assert(!emitted && !memcmp(out,saved,sizeof(out)));
    }
    {
        entityState_t original=ring[0];
        /* The archived clone carries its own identity and animations. It must
         * survive collection without a player weapon binding or model seed. */
        ring[0].number=19; ring[0].eType=ET_PLAYER_CORPSE;
        ring[0].lerp.eFlags=0xa0000; ring[0].groundEntityNum=ENTITYNUM_NONE;
        calls=0; fail_on=0;
        assert(CODOL_CollectServerEntities(4,1,out,2,resolve,&calls));
        assert(out[0].number==19 && out[0].type==ET_PLAYER_CORPSE);
        assert(word(out,0x09c)==3 && word(out,0x008)==0xa0000);
        assert(word(out,0x0d8)==1536 && word(out,0x0dc)==1023);
        assert(word(out,0x088)==ENTITYNUM_NONE && word(out,0x0b0)==2);
        ring[0]=original;
    }
    {
        entityState_t original=ring[3],captured;
        uint32_t unknown=UINT32_MAX;
        memcpy(&ring[3].events[1],&unknown,sizeof(unknown));
        captured=ring[3]; calls=0; fail_on=0; suppressed_slots=2;
        assert(CODOL_CollectServerEntities(3,1,out,2,resolve,&calls));
        assert(word(out,0xb8)==0 && word(out,0xc8)==0);
        assert(word(out,0xbc)==6 && word(out,0xcc)==3);
        assert(word(out,0xb0)==256);
        assert(!memcmp(&ring[3],&captured,sizeof(captured)));
        memcpy(saved,out,sizeof(out));
        suppressed_slots=32;
        assert(!CODOL_CollectServerEntities(3,1,out,2,resolve,&calls));
        assert(!memcmp(out,saved,sizeof(out)));
        suppressed_slots=0;
        assert(!CODOL_CollectServerEntities(3,1,out,2,resolve,&calls));
        assert(!memcmp(out,saved,sizeof(out)));
        ring[3]=original;
    }
    {
        playerState_t ps={0}; uint32_t parameters[4],before[4];
        ps.events[1]=EV_STANCE_FORCE_PRONE; ps.eventParms[1]=2;
        assert(CODOL_ResolveEnginePlayerEventParameters(&ps,parameters));
        assert(!parameters[0] && parameters[1]==2 && !parameters[2] && !parameters[3]);
        memcpy(before,parameters,sizeof(before)); ps.events[3]=EV_SOUND_ALIAS;
        assert(!CODOL_ResolveEnginePlayerEventParameters(&ps,parameters));
        assert(!memcmp(parameters,before,sizeof(before)));
        assert(!CODOL_ResolveEnginePlayerEventParameters(NULL,parameters));
        assert(!CODOL_ResolveEngineEntityEventParameters(NULL,parameters));
    }
    puts("PASS: native visible entity collection, ring wrap/expiry, semantic bindings and atomic generation commit");
    {
        playerState_t ps={0};
        codol_player_fields_t fields={{0}},saved_fields;
        unsigned slot;
        for(slot=0;slot<CODOL_PLAYER_FIELDS;++slot)
            if(CODOL_PlayerField(slot)->offset==0x144) break;
        assert(slot<CODOL_PLAYER_FIELDS);
        ps.viewmodelIndex=7;
        assert(CODOL_OverlayEngineViewmodel(&fields,&ps,55));
        assert(fields.field[slot]==55); /* Native slot7 is not client slot7. */
        saved_fields=fields;
        assert(!CODOL_OverlayEngineViewmodel(&fields,&ps,0));
        assert(!CODOL_OverlayEngineViewmodel(&fields,&ps,2048));
        assert(!memcmp(&fields,&saved_fields,sizeof(fields)));
        ps.viewmodelIndex=0;
        assert(!CODOL_OverlayEngineViewmodel(&fields,&ps,55));
        assert(CODOL_OverlayEngineViewmodel(&fields,&ps,0));
        assert(!fields.field[slot]);
        for(slot=0;slot<CODOL_PLAYER_FIELDS;++slot)
            if(CODOL_PlayerField(slot)->offset==0x148) break;
        assert(slot<CODOL_PLAYER_FIELDS);
        assert(CODOL_OverlayEngineViewhands(&fields,73));
        assert(fields.field[slot]==73);
        saved_fields=fields;
        assert(!CODOL_OverlayEngineViewhands(&fields,2048));
        assert(!memcmp(&fields,&saved_fields,sizeof(fields)));
        assert(CODOL_OverlayEngineViewhands(&fields,0));
        assert(!fields.field[slot]);
    }
    puts("PASS: viewmodel bank remapping, invalid bindings and clear");
}
