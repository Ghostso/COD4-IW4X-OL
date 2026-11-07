/* Exercise the production send bookkeeping with controlled transport results. */
#include "server.h"
#include "codol_sv_state.h"
#include "codol_frame_builder.h"
#include "codol_usercmd.h"
#include "codol_playerstate_ext.h"
#include "codol_weapon_bits.h"
#include "codol_actor_delivery.h"
#include "codol_glass_world.h"
#include "bg.h"
#include "qcommon_io.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
server_t sv;
serverStatic_t svs;
svsHeader_t svsHeader;
cvar_t *sv_maxRate;
cvar_t *codol_debugTrace, *com_developer;
static int accepted, attempts;
static int transmitted_size;
static int advance_before_snapshot;
static int ammo_failure;
static byte transmitted[4096];
qboolean Assert_MyHandler(const char *exp, const char *file, int line,
                         const char *function, const char *fmt, ...)
{ (void)exp; (void)file; (void)line; (void)function; (void)fmt; abort(); }
void Com_PrintWarning(conChannel_t channel, const char *fmt, ...)
{ (void)channel; (void)fmt; }
void Com_Printf(conChannel_t channel, const char *fmt, ...)
{ (void)channel; (void)fmt; }
void Com_DPrintf(conChannel_t channel, const char *fmt, ...)
{ (void)channel; (void)fmt; }
void Com_Error(int level, const char *fmt, ...)
{ (void)level; (void)fmt; abort(); }
void Q_strncpyz(char *dest, const char *source, int capacity)
{ assert(capacity > 0); snprintf(dest, (size_t)capacity, "%s", source); }
void NET_OutOfBandPrint(netsrc_t sock, netadr_t *address, const char *fmt, ...)
{ (void)sock; (void)address; (void)fmt; }
void SV_ShowClientUnAckCommands(client_t *client) { (void)client; }
void SV_CodolTraceAckPublication(client_t *client, const char *kind, int packet,
                                 int wireAck, qboolean transmitted, qboolean recovered)
{ (void)client; (void)kind; (void)packet; (void)wireAck; (void)transmitted; (void)recovered; }
void SV_WriteDownloadToClient(client_t *client)
{ if (advance_before_snapshot) ++client->netchan.outgoingSequence; }
unsigned Sys_Milliseconds(void) { return 123456; }
qboolean Sys_IsLANAddress(netadr_t *address) { (void)address; return qtrue; }
void Cvar_SetInt(cvar_t *var, int value) { (void)var; (void)value; }
void SV_WriteDemoMessageForClient(byte *data, int size, client_t *client)
{ (void)data; (void)size; (void)client; }
void SV_DropClient(client_t *client, const char *reason)
{ (void)reason; client->state = CS_ZOMBIE; }
void Com_Memset(void *data, byte value, int size) { memset(data, value, (size_t)size); }
/* This writer fixture has no live game, entities, models, actors or glass map.
 * Keep those boundaries explicit while the actual player-state extension,
 * overlays, snapshot delta and glass section encoder run from production. */
const void *CODOL_PlayerStateExtLiveBase(unsigned *count)
{ *count=0; return NULL; }
const void *CODOL_PlayerStateExtSnapshotBase(unsigned *count)
{ *count=MAX_CLIENTS; return svs.clients; }
const void *CODOL_PlayerStateExtArchiveBase(unsigned *count)
{ *count=0; return NULL; }
int CODOL_ServerModelToWire(unsigned index)
{ assert(index==0); return 0; }
const char *codol_actor_delivery_failure;
void CODOL_ActorDeliveryClear(unsigned client)
{ assert(client<MAX_CLIENTS); }
int CODOL_ActorDeliveryPrepare(unsigned client,unsigned sequence,unsigned acknowledged,
    const codol_entity_state_t *entities,unsigned count,codol_animcmd_t *out,
    unsigned capacity,unsigned *written)
{
    (void)sequence;(void)acknowledged;(void)entities;(void)out;(void)capacity;
    assert(client<MAX_CLIENTS && count==0 && written); *written=0; return 1;
}
int CODOL_ActorAnimPublished(unsigned client,uint32_t sequence)
{ (void)sequence; assert(client<MAX_CLIENTS); return 0; }
int CODOL_GlassWorldEnsureMap(void) { return 1; }
int CODOL_GlassWorldCapture(codol_glass_wire_piece_t *out,size_t capacity,unsigned *count)
{ (void)out; assert(capacity>=CODOL_GLASS_MAX_PIECES && count); *count=0; return 1; }
void CODOL_PacingSnapshot(unsigned client,int psCommandTime,int serverTime,int rateDelayed)
{ (void)psCommandTime;(void)serverTime;(void)rateDelayed; assert(client<MAX_CLIENTS); }
void CODOL_PmoveTraceReport(unsigned client,const float *serverOrigin,
    const float *predictedOrigin,int predictedTime)
{ (void)serverOrigin;(void)predictedOrigin;(void)predictedTime; assert(client<MAX_CLIENTS); }
void CODOL_KillcamTraceFrame(void) { }
int CODOL_WeaponStateSecondBarrelArmed(const playerState_t *ps)
{ assert(ps); return CODOL_PlayerStateHandRead(ps)->second_barrel; }
int CODOL_WeaponIsDualWield(unsigned weapon)
{ assert(weapon==0); return 0; }
struct WeaponDef *BG_GetWeaponDef(int weapon)
{ assert(weapon==0); return NULL; }
qboolean CODOL_NetchanSubmit(netchan_t *chan, int size, const byte *data)
{
    client_t *client = (client_t *)((byte *)chan - offsetof(client_t, netchan));
    ++attempts;
    assert(size <= sizeof(transmitted));
    transmitted_size = size; memcpy(transmitted, data, size);
    SV_Netchan_Encode(client, transmitted, size); /* Inspect decoded bytes. */
    if (accepted) ++client->netchan.outgoingSequence;
    return accepted;
}
/* Empty-world fixture services. Entity/client conversion is covered separately
 * by the production ring-collector fixture; this test owns the live writer. */
int CODOL_BuildServerAmmoBindings(codol_engine_player_bindings_t *out,const playerState_t *ps)
{
    unsigned i;
    assert(ps->commandTime==svsHeader.time && ps->weapon==0 &&
           ps->offHandIndex==0 && !CODOL_WeaponBitsOwned(ps,1));
    if(ammo_failure) return 0;
    out->clip_mask=out->reserve_mask=0x7fff;
    for(i=0;i<16;++i) {
        out->clips[i]=(codol_ammo_binding_t){-1,-1};
        out->reserves[i]=(codol_ammo_binding_t){-1,0};
    }
    return 1;
}
int CODOL_CollectServerHud(codol_hud_state_t *out,const hudElemState_t *source)
{
    assert(source && source->current[0].type==HE_TYPE_FREE && source->archival[0].type==HE_TYPE_FREE);
    memset(out,0,sizeof(*out)); return 1;
}
int CODOL_CollectServerEntitiesForClient(int first,int count,codol_entity_state_t *out,size_t capacity,
    codol_snapshot_entity_resolver_t resolve,void *context,size_t *emitted,int local_client)
{ (void)first;(void)out;(void)capacity;(void)resolve;(void)context;(void)local_client;
  assert(!count); assert(emitted); *emitted=0; return 1; }
int CODOL_CollectServerClientsResolved(int first,int count,codol_client_state_t *out,size_t capacity,
    codol_snapshot_client_resolver_t resolve,void *context)
{ (void)first;(void)out;(void)capacity;(void)resolve;(void)context; assert(!count); return 1; }
static void live_writer_test(client_t *client)
{
    codol_player_fields_t seed={{0}};
    codol_player_array_updates_t arrays={0};
    codol_engine_player_bindings_t player={0};
    codol_native_frame_bindings_t bindings={0};
    clientSnapshot_t *source;
    byte bytes[4096]; msg_t msg;
    unsigned sequence;
    bindings.player_seed=&seed; bindings.array_seed=&arrays; bindings.player=&player;
    player.event_parameters[0]=2047; /* Recipient producer must replace this stale binding. */
    memset(client,0,sizeof(*client)); client->state=CS_ACTIVE; client->snapshotMsec=50;
    /* Use the server's actual snapshot storage so its extension resolver reads
     * the same owned state as the production frame builder. */
    assert(client==&svs.clients[0]);
    source=&client->frames[1];
    source->ps.moveSpeedScaleMultiplier=1; source->ps.groundEntityNum=ENTITYNUM_WORLD;
    source->ps.throwBackGrenadeOwner=ENTITYNUM_NONE;
    source->ps.events[0]=EV_FIRE_WEAPON; source->ps.eventSequence=1;
    {
        codol_ps_ext_t *ext=CODOL_PlayerStateExt(&source->ps);
        assert(ext);
        ext->links_known=1;
        ext->links.linkWeaponEntNum=ENTITYNUM_NONE;
        ext->links.cameraEntNum=ENTITYNUM_NONE;
        ext->links.controlsEntNum=ENTITYNUM_NONE;
    }
    CODOL_PlayerStateEventAdded(&source->ps);
    svsHeader.clients=client; svsHeader.time=20000;
    CODOL_ResetWeaponMap(); CODOL_ResetSnapshotHistories();
    accepted=1; advance_before_snapshot=0;
    for(sequence=1;sequence<=2;++sequence) {
        client->netchan.outgoingSequence=sequence; client->deltaMessage=sequence-1;
        source->ps.commandTime=svsHeader.time;
        if(sequence==2) {
            source->ps.events[1]=EV_FIRE_WEAPON_LASTSHOT; source->ps.eventSequence=2;
            CODOL_PlayerStateEventAdded(&source->ps);
        }
        assert(CODOL_CaptureClientSnapshotHud(0,sequence,&source->ps.hud));
        if(!CODOL_BuildClientNativeFrame(0,sequence,source,&bindings)) {
            fprintf(stderr,"native frame %u failed: %s: %s\n",sequence,
                codol_frame_failure ? codol_frame_failure : "unknown",
                codol_player_failure ? codol_player_failure : "unknown");
            abort();
        }
        assert(CODOL_NativeFrameUpdates(CODOL_ClientNativeFrame(0,sequence))->clip_mask==0x7fff);
        assert(!player.clip_mask && !player.reserve_mask); /* Borrowed caller bindings stay intact. */
        assert(player.event_parameters[0]==2047);
        {
            unsigned i; const codol_player_fields_t *fields=CODOL_NativeFrameState(CODOL_ClientNativeFrame(0,sequence))->player;
            for(i=0;i<CODOL_PLAYER_FIELDS;++i) {
                if(CODOL_PlayerField(i)->offset==0xf0) assert(fields->field[i]==sequence);
                if(CODOL_PlayerField(i)->offset==0x1ec) assert(fields->field[i]==ENTITYNUM_NONE);
                if(CODOL_PlayerField(i)->offset==0xf4) assert(fields->field[i]==30);
                if(CODOL_PlayerField(i)->offset==0xf8) assert(fields->field[i]==(sequence==2 ? 31u : 0u));
                if(CODOL_PlayerField(i)->offset==0x104) assert(!fields->field[i]);
            }
        }
        MSG_Init(&msg,bytes,sizeof(bytes)); MSG_WriteLong(&msg,0);
        SV_WriteSnapshotToClient(client,&msg);
        assert(!msg.overflowed && CODOL_ClientSnapshotPrepared(0,&msg,sequence));
        assert(bytes[4]==0 && bytes[9]==sequence-1); /* CoDOL opcode and exact ACK delta. */
        assert(!!(bytes[10]&8)==(sequence==1));
        SV_EndClientSnapshot(client,&msg);
        assert(CODOL_FindHistoryBase(CODOL_ClientSnapshotHistory(0),sequence,sequence+1));
        svsHeader.time+=50;
    }
    /* A disconnected client has no native frame; preserve the already queued
     * reliable payload, regardless of which sender invokes the writer. */
    client->state=CS_ZOMBIE;
    MSG_Init(&msg,bytes,sizeof(bytes)); MSG_WriteLong(&msg,123);
    SV_WriteSnapshotToClient(client,&msg);
    assert(!msg.overflowed && msg.cursize==4 && bytes[0]==123);
    client->state=CS_ACTIVE;
    /* Stored sequence 2 cannot be emitted as 3; recovery sends only ACK/EOF. */
    MSG_Init(&msg,bytes,sizeof(bytes)); MSG_WriteLong(&msg,0);
    SV_WriteSnapshotToClient(client,&msg); assert(msg.overflowed && msg.cursize==4);
    SV_EndClientSnapshot(client,&msg); assert(transmitted_size==5);
    /* The extension's event epoch is authoritative. A producer that advances
     * only the retained low byte must invalidate this same-sequence rebuild. */
    source->ps.commandTime=svsHeader.time; source->ps.eventSequence=3;
    assert(!CODOL_BuildClientNativeFrame(0,2,source,&bindings));
    assert(!CODOL_ClientNativeFrame(0,2)); source->ps.eventSequence=2;
    ammo_failure=1;
    assert(!CODOL_BuildClientNativeFrame(0,2,source,&bindings));
    assert(!CODOL_ClientNativeFrame(0,2)); ammo_failure=0;
    assert(!CODOL_BuildClientNativeFrame(0,2,NULL,&bindings));
    assert(!CODOL_ClientNativeFrame(0,2)); /* Failed same-sequence rebuild invalidates old data. */
    CODOL_ResetSnapshotHistories(); assert(!CODOL_ClientNativeFrame(0,2));
    puts("PASS: live snapshot entry point emits CoDOL full/delta frames and rejects stale native captures");
}
#include "codol_matchdata.h"
int CODOL_LoadMountedStructuredSchema(const char *name,codol_structured_schema_t *out)
{
    (void)name;out->count=1;out->definitions=calloc(1,sizeof(*out->definitions));
    assert(out->definitions);out->definitions->layout.record_size=858;return 1;
}
int main(void)
{
    static client_t client;
    byte data[8] = {0};
    msg_t msg = {0};
    clientSnapshot_t *frame = &client.frames[1];
    msg.data = data; msg.cursize = sizeof(data); msg.maxsize = sizeof(data);
    client.state = CS_PRIMED; client.netchan.outgoingSequence = 1;
    client.snapshotMsec = 50; svs.time = 1000;
    frame->messageSize = 19; frame->messageSent = 20; frame->messageAcked = 21;
    assert(!SV_SendMessageToClient(&msg, &client));
    assert(!memcmp(data, (byte[8]){0}, sizeof(data))); /* Rejected send preserves plaintext. */
    assert(attempts == 1 && client.netchan.outgoingSequence == 1);
    assert(frame->messageSize == 19 && frame->messageSent == 20 && frame->messageAcked == 21);
    assert(client.nextSnapshotTime == 1050);
    accepted = 1;
    assert(SV_SendMessageToClient(&msg, &client));
    assert(!memcmp(data, (byte[8]){0}, sizeof(data)));
    assert(attempts == 2 && client.netchan.outgoingSequence == 2);
    assert(frame->messageSize == 8 && frame->messageSent == 123456 && frame->messageAcked == ~0u);
    client.delayDropMsg = "test drop";
    assert(!SV_SendMessageToClient(&msg, &client));
    assert(client.state == CS_ZOMBIE && attempts == 2);
    client.delayDropMsg = NULL; msg.overflowed = qtrue;
    assert(!SV_SendMessageToClient(&msg, &client) && attempts == 2);
    {
        byte buffer[4096];
        codol_player_fields_t player = {{0}};
        codol_snapshot_state_t state = {0};
        codol_delta_context_t context = {20000, {0, 0, 0}, 0, 0};
        int scenario, snapshot_bytes = 0;
        svsHeader.clients = &client;
        state.player = &player; state.sequence = 1;
        for (scenario = 0; scenario < 6 + snapshot_bytes; ++scenario) {
            int prepared_size;
            codol_history_t *history;
            memset(&client, 0, sizeof(client));
            client.state = CS_ACTIVE; client.netchan.outgoingSequence = 1;
            client.snapshotMsec = 50;
            accepted = scenario != 1; attempts = 0;
            advance_before_snapshot = scenario == 3;
            MSG_Init(&msg, buffer, sizeof(buffer)); MSG_WriteLong(&msg, 0);
            assert(CODOL_SelectClientMatchData("mp/clientmatchdata.def"));
            CODOL_RequestClientMatchData(0);
            assert(CODOL_PrepareClientSnapshot(0, &msg, &state, 0, NULL, NULL, 0, 8, 1, &context));
            assert(CODOL_ClientSnapshotPending(0));
            history = CODOL_ClientSnapshotHistory(0); prepared_size = msg.cursize;
            assert(buffer[prepared_size-(1026+sizeof("mp/clientmatchdata.def"))]==4);
            assert(!strcmp((char *)buffer+prepared_size-(1025+sizeof("mp/clientmatchdata.def")),"mp/clientmatchdata.def"));
            if (!scenario) snapshot_bytes = prepared_size;
            assert(!CODOL_FindHistoryBase(history, 1, 2));
            if (scenario == 2) msg.overflowed = qtrue;
            if (scenario == 4) ++client.netchan.outgoingSequence; /* Changed before finalization. */
            if (scenario == 5) MSG_WriteByte(&msg, 0); /* Prepared message changed size. */
            /* Mutate every byte, including ACK prefix and EOF, without changing
             * pointer or size. Each must take the recovery path, not enter history. */
            if (scenario >= 6) buffer[scenario - 6] ^= 1;
            SV_EndClientSnapshot(&client, &msg);
            assert(attempts == 1);
            if (scenario >= 2) {
                assert(transmitted_size == 5); /* ACK + EOF recovery, no snapshot */
            } else {
                assert(transmitted_size == prepared_size); /* no duplicate EOF */
            }
            assert(transmitted[transmitted_size-1] == 5);
            assert(!!CODOL_FindHistoryBase(history, 1, 2) == (scenario == 0));
            assert(!CODOL_ClientSnapshotPrepared(0, &msg, 1));
            assert(!CODOL_ClientSnapshotPending(0));
            assert(CODOL_ClientMatchDataDue(0,20000)==(scenario!=0));
            CODOL_ResetSnapshotHistories();
        }
    }
    puts("PASS: production send rejection, frame rollback, retry and delayed drop");
    live_writer_test(&svs.clients[0]);
    CODOL_ResetClientMatchData();
    return 0;
}
