/* Production name publication and client-state assembly with controlled engine strings. */
#include "server.h"
#include "g_shared.h"
#include "codol_sv_state.h"
#include "codol_engine_state.h"
#include "qcommon_io.h"
#include "g_hud.h"
#include "codol_hud_fontscale.h"
#include "codol_sv_frame.h"
#include "codol_frame_builder.h"
#include "codol_usercmd.h"
#include "codol_sv_weapons.h"
#include "codol_weapon_native.h"
#include "codol_weapon_lock.h"
#include "codol_entitystate_ext.h"
#include "codol_playerstate_ext.h"
#include "codol_clientstate_ext.h"
#include "codol_actor_delivery.h"
#include "codol_actor_state.h"
#include "codol_sv_entities.h"
#include "codol_glass_snapshot.h"
#include <assert.h>
gentity_t g_entities[MAX_GENTITIES];
level_locals_t level;
struct XModel *cached_models[CODOL_NATIVE_MODELS];
cvar_t *codol_debugTrace, *com_developer;
static struct WeaponDef native_none;
int BG_GetNumWeapons(void) { return 2; }
int CM_NumInlineModels(void) { return 4; }
struct WeaponDef *BG_GetWeaponDef(int index) { assert(index>=0 && index<2); return &native_none; }
int CODOL_BuildServerAmmoBindings(codol_engine_player_bindings_t *out,const playerState_t *ps)
{
    unsigned i; (void)ps;
    out->clip_mask=out->reserve_mask=0x7fff;
    for(i=0;i<16;++i) {
        out->clips[i]=(codol_ammo_binding_t){-1,-1};
        out->reserves[i]=(codol_ammo_binding_t){-1,0};
    }
    return 1;
}
game_hudelem_t g_hudelems[MAX_HUDELEMS];
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
_Static_assert(offsetof(codol_player_array_updates_t,stats)==4,"CoDOL arrays ignore packed engine headers");
_Static_assert(_Alignof(codol_hud_state_t)==_Alignof(uint32_t),"HUD state retains natural alignment");
_Static_assert(sizeof(codol_player_field_t)==6,"netfield descriptors retain natural layout");
server_t sv;
serverStatic_t svs;
svsHeader_t svsHeader;
static cvar_t maximum;
cvar_t *sv_maxclients = &maximum;
static const char *strings[8] = {NULL, "", "body", "attachment", "tag_weapon"};
static int commands;
static char last_command[256];
static cvar_t replicated,private_var;
cvar_t *Cvar_FindVar(const char *name)
{
    if(!strcmp(name,"shared_setting")) return &replicated;
    if(!strcmp(name,"private_setting")) return &private_var;
    return NULL;
}
char *Cvar_DisplayableValue(const cvar_t *var) { return var->string; }
static unsigned field(const codol_client_state_t *wire, unsigned offset)
{
    unsigned i;
    for (i = 0; i < CODOL_CLIENT_FIELDS; ++i)
        if (CODOL_ClientField(i)->offset == offset) return wire->field[i];
    assert(0); return 0;
}
int SV_GetConfigstringIndex(int index) { return sv.configstrings[index]; }
static unsigned entity_field(const codol_entity_state_t *wire, unsigned offset)
{
    unsigned i;
    for(i=0;i<CODOL_ENTITY_FIELDS;++i)
        if(CODOL_EntityField(wire->type,i)->offset==offset) return wire->field[i];
    assert(0); return 0;
}
static void model_entity_test(void)
{
    gentity_t engine={0};
    codol_entity_state_t wire, saved;
    unsigned i;
    memset(&wire,0xa5,sizeof(wire)); wire.type=ET_SCRIPTMOVER;
    engine.s.eType=ET_SCRIPTMOVER; engine.s.index=7;
    assert(CODOL_OverlayServerModelEntity(&wire,&engine));
    assert(entity_field(&wire,0x5c)==1 && entity_field(&wire,0x88)==0xa5a5a5a5);
    /* C1 0x567960: a script mover takes no marks unless told (+58 = none) */
    assert(entity_field(&wire,0x58)==0x7ff);
    engine.s.index=9;
    assert(CODOL_OverlayServerModelEntity(&wire,&engine) && entity_field(&wire,0x5c)==2);
    engine.s.index=0;
    assert(CODOL_OverlayServerModelEntity(&wire,&engine) && entity_field(&wire,0x5c)==0);
    saved=wire;
    for(i=0;i<6;++i) {
        memset(&engine,0,sizeof(engine)); engine.s.eType=ET_SCRIPTMOVER; engine.s.index=7;
        switch(i) {
        case 0: engine.s.index=1; break; /* unpublished */
        case 1: engine.s.index=MAX_MODELS; break;
        case 2: engine.r.bmodel=1; break;
        case 3: engine.s.solid=SOLID_BMODEL; break;
        case 4: engine.s.eType=ET_PLAYER; break;
        case 5: engine.s.eType=ET_GENERAL; break; /* seed type mismatch */
        }
        assert(!CODOL_OverlayServerModelEntity(&wire,&engine));
        assert(!memcmp(&wire,&saved,sizeof(wire)));
    }
    engine.s.eType=ET_GENERAL; wire.type=ET_GENERAL;
    assert(CODOL_OverlayEngineModelEntity(&wire,&engine.s,2047,0));
    assert(entity_field(&wire,0x98)==2047);
    saved=wire;
    assert(!CODOL_OverlayEngineModelEntity(&wire,&engine.s,2048,0));
    assert(!CODOL_OverlayEngineModelEntity(&wire,&engine.s,0,0));
    assert(!CODOL_OverlayEngineModelEntity(&wire,&engine.s,1,1));
    assert(!CODOL_OverlayEngineModelEntity(&wire,&engine.s,1,-1));
    engine.s.index=0;
    assert(!CODOL_OverlayEngineModelEntity(&wire,&engine.s,1,0));
    assert(!CODOL_OverlayEngineModelEntity(&wire,NULL,1,0));
    assert(!CODOL_OverlayEngineModelEntity(NULL,&engine.s,1,0));
    assert(!CODOL_OverlayServerModelEntity(&wire,NULL));
    assert(!CODOL_OverlayServerModelEntity(NULL,&engine));
    assert(!memcmp(&wire,&saved,sizeof(wire)));
}
static void brush_entities(void)
{
    entityState_t source={0}; codol_entity_state_t wire={0}, before;
    source.eType=ET_SCRIPTMOVER; source.index=1; source.solid=SOLID_BMODEL;
    wire.type=ET_SCRIPTMOVER;
    assert(CODOL_OverlayEngineBrushEntity(&wire,&source,2));
    assert(entity_field(&wire,0x98)==1 && entity_field(&wire,0xa8)==0xffffff);
    assert(entity_field(&wire,0x58)==0x7ff);
    before=wire;
    assert(!CODOL_OverlayEngineBrushEntity(&wire,&source,1));
    source.index=0; assert(!CODOL_OverlayEngineBrushEntity(&wire,&source,2));
    source.index=2048; assert(!CODOL_OverlayEngineBrushEntity(&wire,&source,3000));
    source.index=1; source.solid=0; assert(!CODOL_OverlayEngineBrushEntity(&wire,&source,2));
    source.solid=SOLID_BMODEL; source.eType=ET_ITEM;
    assert(!CODOL_OverlayEngineBrushEntity(&wire,&source,2));
    assert(!memcmp(&wire,&before,sizeof(wire)));
}
const char *SL_ConvertToString(unsigned index) { assert(index < 8); return strings[index]; }
void SL_RemoveRefToString(unsigned index) { assert(!index); }
void Com_Printf(conChannel_t channel,const char *fmt,...){(void)channel;(void)fmt;}
void Com_DPrintf(conChannel_t channel,const char *fmt,...){(void)channel;(void)fmt;}
void Q_strncpyz(char *dest,const char *source,int capacity)
{ assert(dest && source && capacity>0); snprintf(dest,(size_t)capacity,"%s",source); }
void CODOL_KillcamTraceFrame(void) { }
/* This fixture has no map shadow state and no native weapon registry. Weapon
 * publication itself is covered elsewhere; an attempt to refresh weapon
 * definitions here is a fixture setup error. */
int CODOL_RefreshMapSunSampleSize(void) { return 1; }
void CODOL_ResetMapSunSampleSize(void) { }
int CODOL_RefreshServerWeaponMappings(void) { assert(0 && "weapon registry absent"); return 0; }
const char *CODOL_ServerWeaponRegistryError(void) { return "weapon registry absent"; }
int CODOL_RemoteVehicleType(unsigned client)
{ (void)client; assert(0 && "no live player or remote vehicle in fixture"); return -1; }
/* No C1 actor capture is mounted in this asset-name fixture. The frame's
 * explicit actor input is tested below, and the gameplay frame sees the
 * captured empty actor set for this synthetic snapshot. */
const char *codol_actor_delivery_failure;
void CODOL_ActorDeliveryClear(unsigned client) { assert(client<MAX_CLIENTS); }
int CODOL_ActorDeliveryPrepare(unsigned client,unsigned sequence,unsigned acknowledged,
    const codol_entity_state_t *entities,unsigned count,codol_animcmd_t *out,
    unsigned capacity,unsigned *written)
{
    (void)sequence;(void)acknowledged;(void)out;
    assert(client<MAX_CLIENTS && count<=1 && (!count ||
        (entities && entities[0].type!=ET_ACTOR)) &&
        capacity>=CODOL_ACTOR_ANIM_SNAPSHOT_LIMIT && written);
    *written=0; return 1;
}
int CODOL_CopyClientSnapshotActors(unsigned client,uint32_t sequence,
    codol_actor_state_t *out,size_t capacity,unsigned *count)
{
    (void)out; assert(client<2 && sequence==200 && capacity>=32 && count);
    *count=0; return 1;
}
/* The target test has no entity lifecycle clients (vehicles, missiles, glass).
 * Keep their reset boundary narrowed to the real snapshot epoch state. */
void CODOL_ResetEntityEventGeneration(unsigned number)
{ CODOL_ResetEntityEventEpoch(number); }
void CODOL_ResetEntityEventGenerations(void)
{ CODOL_ResetEntityEventEpochs(); CODOL_EntityStateExtClearAll(); }
void SV_SendServerCommandNoLoss(client_t *client, const char *format, ...)
{
    va_list args;
    assert(client == &svs.clients[0]);
    va_start(args, format); vsnprintf(last_command, sizeof(last_command), format, args); va_end(args);
    ++commands;
}
static int frame_entity_seed(void *context,const entityState_t *source,codol_snapshot_entity_bindings_t *out)
{
    unsigned i; (void)context;
    out->state.type=source->eType;
    for(i=0;i<CODOL_ENTITY_FIELDS;++i)
        if(CODOL_EntityField(out->state.type,i)->offset==0x98) out->state.field[i]=17;
    return CODOL_ResolveEngineEntityEventParameters(source,out->event_parameters);
}
static int frame_client_seed(void *context,const clientState_t *source,codol_client_state_t *out)
{
    unsigned i; (void)source;
    if(context) return 0;
    for(i=0;i<CODOL_CLIENT_FIELDS;++i)
        if(CODOL_ClientField(i)->offset==0xc0) out->field[i]=0x11223344;
    return 1;
}
static void frame_assembly_test(void)
{
    clientSnapshot_t *source=&svs.clients[0].frames[0];
    entityState_t entities[4]={{0}}; clientState_t clients[4]={{0}};
    codol_player_fields_t seed={0}; codol_player_array_updates_t arrays={0};
    codol_engine_player_bindings_t player={0}; codol_native_frame_bindings_t bindings={0},invalid;
    uint32_t followed_sequence=0;
    codol_native_frame_t *frame=NULL,*before; const codol_snapshot_state_t *state;
    codol_actor_state_t actor={0}; codol_animcmd_t command={0}; size_t count;
    unsigned event;
    codol_ps_ext_t *extension;
    codol_ps_ext_t abilities={0};
    memset(sv.configstrings,0,sizeof(sv.configstrings));
    CODOL_ResetWeaponMap();
    memset(source,0,sizeof(*source));
    source->ps.clientNum=0;
    source->ps.moveSpeedScaleMultiplier=1; source->ps.groundEntityNum=ENTITYNUM_WORLD;
    source->ps.throwBackGrenadeOwner=ENTITYNUM_NONE;
    extension=CODOL_PlayerStateExt(&source->ps);
    assert(extension); CODOL_PlayerStateExtClear(&source->ps);
    extension->links_known=1;
    extension->links.linkWeaponEntNum=ENTITYNUM_NONE;
    extension->links.cameraEntNum=ENTITYNUM_NONE;
    extension->links.controlsEntNum=ENTITYNUM_NONE;
    for(event=0;event<3;++event) {
        ++source->ps.eventSequence; CODOL_PlayerStateEventAdded(&source->ps);
    }
    source->first_entity=source->first_client=3; source->num_entities=source->num_clients=1;
    entities[3].number=2;
    clients[3].attachedVehEntNum=ENTITYNUM_NONE;
    svsHeader.snapshotEntities=entities; svsHeader.numSnapshotEntities=4; svsHeader.nextSnapshotEntities=4;
    svsHeader.snapshotClients=clients; svsHeader.numSnapshotClients=4; svsHeader.nextSnapshotClients=4;
    svsHeader.clients=svs.clients;
    svs.numSnapshotClients=4; svs.snapshotClients[3]=clients[3];
    abilities.abilities_known=1; abilities.abilities.masks[0]=0x11223344;
    assert(CODOL_CaptureClientAbilities(3,&abilities));
    CODOL_ResetEntityEventGenerations();
    CODOL_EntityStateExtClear(&entities[3]);
    for(event=0;event<254;++event) {
        entities[3].eventSequence=(entities[3].eventSequence+1)&255;
        CODOL_EntityStateEventAdded(&entities[3]);
    }
    actor.data[4]=55; command.arg2=7;
    bindings.player_seed=&seed; bindings.array_seed=&arrays; bindings.player=&player;
    bindings.entity_resolve=frame_entity_seed; bindings.client_resolve=frame_client_seed;
    bindings.actors=&actor; bindings.actor_count=1; bindings.commands=&command; bindings.command_count=1;
    assert(CODOL_CaptureClientSnapshotHud(0,200,&source->ps.hud));
    assert(CODOL_BuildNativeFrame(&frame,0,200,source,&bindings));
    /* The entity counter published is that entity state's own epoch. */
    assert(CODOL_EntityStateEventEpoch(&entities[2])==0);
    state=CODOL_NativeFrameState(frame);
    assert(state && state->sequence==200 && state->entity_count==1 && state->client_count==1 && state->actor_count==1);
    assert(state->entities[0].number==2 && entity_field(&state->entities[0],0x98)==17);
    assert(field(&state->clients[0],0xc0)==0x11223344 && field(&state->clients[0],0xbc)==2047);
    assert(CODOL_NativeFrameUpdates(frame));
    actor.data[4]=77; command.arg2=9;
    assert(state->actors[0].data[4]==55 && CODOL_NativeFrameCommands(frame,&count)[0].arg2==7 && count==1);
    before=frame;
    ++source->ps.eventSequence; CODOL_PlayerStateEventAdded(&source->ps);
    entities[3].eventSequence=255; CODOL_EntityStateEventAdded(&entities[3]);
    clients[3].modelindex=MAX_MODELS; /* Fail after entity generation advanced in staging. */
    assert(!CODOL_BuildNativeFrame(&frame,0,200,source,&bindings));
    assert(frame==before);
    clients[3].modelindex=0;
    invalid=bindings; invalid.client_context=&invalid;
    assert(!CODOL_BuildNativeFrame(&frame,0,200,source,&invalid));
    invalid=bindings; invalid.client_resolve=NULL;
    assert(!CODOL_BuildNativeFrame(&frame,0,200,source,&invalid));
    assert(!CODOL_BuildNativeFrame(&frame,0,201,source,&bindings));
    assert(frame==before);
    assert(state->actors[0].data[4]==55 && entity_field(&state->entities[0],0xb0)==254);
    assert(CODOL_BuildNativeFrame(&frame,0,200,source,&bindings));

    state=CODOL_NativeFrameState(frame); assert(state->actors[0].data[4]==77);
    assert(CODOL_SetWeaponLock(CODOL_PlayerStateWeaponLock(&source->ps),17,NULL,1,NULL,0));
    assert(CODOL_SetWeaponLock(CODOL_ClientWeaponLock(0),18,NULL,1,NULL,1));
    assert(CODOL_SetWeaponLock(CODOL_ClientWeaponLock(1),19,NULL,1,NULL,1));
    assert(CODOL_BuildGameplayFrame(0,200,source));
    {
        const codol_native_frame_t *live=CODOL_ClientNativeFrame(0,200);
        const codol_snapshot_state_t *built=CODOL_NativeFrameState(live);
        assert(built && built->entity_count==1 && built->client_count==1 && !built->actor_count);
        for(unsigned i=0;i<CODOL_PLAYER_FIELDS;++i) {
            if(CODOL_PlayerField(i)->offset==0x48c)assert(built->player->field[i]==11);
            if(CODOL_PlayerField(i)->offset==0x490)assert(built->player->field[i]==17);
        }
        /* Recipient 1 follows source player 0: their own lock must not leak. */
        assert(CODOL_CaptureClientSnapshotHud(1,200,&source->ps.hud));
        assert(CODOL_BuildGameplayFrame(1,200,source));
        { const codol_snapshot_state_t *followed=CODOL_NativeFrameState(CODOL_ClientNativeFrame(1,200));
          assert(followed);
          for(unsigned i=0;i<CODOL_PLAYER_FIELDS;++i) {
              if(CODOL_PlayerField(i)->offset==0x490)assert(followed->player->field[i]==17);
              if(CODOL_PlayerField(i)->offset==0x0f0)followed_sequence=followed->player->field[i];
          }
        }
        assert(field(&built->clients[0],0xc0)==0x11223344 && field(&built->clients[0],0xbc)==2047);
        /* The published counter is the source state's own, so both recipients
         * of that state publish the same one instead of each accumulating. */
        for(unsigned i=0;i<CODOL_PLAYER_FIELDS;++i)
            if(CODOL_PlayerField(i)->offset==0x0f0) {
                assert(built->player->field[i]==(uint32_t)source->ps.eventSequence);
                assert(followed_sequence==built->player->field[i]);
            }

        {
            unsigned char bytes[8192]; codol_msg_t message;
            codol_delta_context_t context={0};
            CODOL_MsgWriteInit(&message,bytes,sizeof(bytes));
            assert(CODOL_WriteSnapshot(&message,built,NULL,CODOL_NativeFrameUpdates(live),NULL,0,0,1,&context));
            assert(!message.failed && message.size>0);
        }
        {
            entityState_t original=entities[3];
            unsigned char bytes[8192]; codol_msg_t message; codol_delta_context_t context={0};
            entities[3].eType=ET_SCRIPTMOVER; entities[3].index=1; entities[3].solid=SOLID_BMODEL;
            g_entities[2].r.bmodel=1;
            assert(CODOL_BuildGameplayFrame(0,200,source));
            live=CODOL_ClientNativeFrame(0,200); built=CODOL_NativeFrameState(live);
            assert(entity_field(&built->entities[0],0x98)==1 && entity_field(&built->entities[0],0xa8)==0xffffff);
            CODOL_MsgWriteInit(&message,bytes,sizeof(bytes));
            assert(CODOL_WriteSnapshot(&message,built,NULL,CODOL_NativeFrameUpdates(live),NULL,0,0,1,&context));
            entities[3].index=4;
            assert(CODOL_BuildGameplayFrame(0,200,source));
            assert(CODOL_NativeFrameState(CODOL_ClientNativeFrame(0,200))->entity_count==0);
            entities[3]=original; g_entities[2].r.bmodel=0;
        }
        assert(CODOL_MapWeapon(25,1));
        entities[3].eType=ET_ITEM; entities[3].index=1;
        assert(CODOL_BuildGameplayFrame(0,200,source));
        built=CODOL_NativeFrameState(CODOL_ClientNativeFrame(0,200));
        assert(built->entities[0].type==ET_ITEM && entity_field(&built->entities[0],0x98)==25);
        {
            unsigned char bytes[8192]; codol_msg_t message; codol_delta_context_t context={0};
            codol_entity_state_t item=built->entities[0],saved=item;
            entityState_t invalid_item=entities[3];
            CODOL_MsgWriteInit(&message,bytes,sizeof(bytes));
            assert(CODOL_WriteSnapshot(&message,built,NULL,
                CODOL_NativeFrameUpdates(CODOL_ClientNativeFrame(0,200)),NULL,0,0,1,&context));
            invalid_item.index=0;
            assert(!CODOL_OverlayEngineItem(&item,&invalid_item) && !memcmp(&item,&saved,sizeof(item)));
            invalid_item.index=-1;
            assert(!CODOL_OverlayEngineItem(&item,&invalid_item) && !memcmp(&item,&saved,sizeof(item)));
            invalid_item.index=2;
            assert(!CODOL_OverlayEngineItem(&item,&invalid_item) && !memcmp(&item,&saved,sizeof(item)));
            assert(CODOL_MapWeapon(700,2));
            assert(!CODOL_OverlayEngineItem(&item,&invalid_item) && !memcmp(&item,&saved,sizeof(item)));
        }
        entities[3].index=129; /* Native variant one is not yet translated. */
        assert(CODOL_BuildGameplayFrame(0,200,source));
        assert(CODOL_NativeFrameState(CODOL_ClientNativeFrame(0,200))->entity_count==0);
        entities[3].eType=ET_VEHICLE; entities[3].index=0;
        assert(CODOL_BuildGameplayFrame(0,200,source));
        assert(CODOL_NativeFrameState(CODOL_ClientNativeFrame(0,200))->entity_count==0);

        entities[3].eType=ET_GENERAL;
        source->ps.weapon=2; /* no native definition or wire slot */
        assert(!CODOL_BuildGameplayFrame(0,200,source));
        source->ps.weapon=0;
        assert(CODOL_BuildGameplayFrame(0,200,source));
        CODOL_ResetEntityEventGeneration(0); CODOL_ResetEntityEventGeneration(2);
        assert(!CODOL_EntityStateEventEpoch(&entities[2]));
        CODOL_ClearClientNativeFrame(0);
    }
    CODOL_FreeNativeFrame(frame); CODOL_ClearClientSnapshotHud(0);
    svsHeader.snapshotEntities=NULL; svsHeader.snapshotClients=NULL;
    puts("PASS: owned native frame assembly, captured HUD, explicit client seeds and cross-section clock rollback");
}
/* Bind the synthetic snapshot rings to the real extension implementation so
 * the producer hooks above and the frame builder read the same owned state. */
const void *CODOL_EntityStateExtLiveBase(unsigned *count){if(count)*count=0;return NULL;}
const void *CODOL_EntityStateExtSnapshotBase(unsigned *count)
{ if(count)*count=(unsigned)svsHeader.numSnapshotEntities;return svsHeader.snapshotEntities; }
const void *CODOL_EntityStateExtArchiveBase(unsigned *count){if(count)*count=0;return NULL;}
const void *CODOL_PlayerStateExtLiveBase(unsigned *count){if(count)*count=0;return NULL;}
const void *CODOL_PlayerStateExtSnapshotBase(unsigned *count)
{ if(count)*count=MAX_CLIENTS;return svs.clients; }
const void *CODOL_PlayerStateExtArchiveBase(unsigned *count){if(count)*count=0;return NULL;}
void Com_PrintWarning(conChannel_t channel,const char *fmt,...){(void)channel;(void)fmt;}
int main(void)
{
    brush_entities();
    client_t *clients = svs.clients;
    codol_client_state_t wire = {0}, saved;
    clientState_t engine = {0};
    maximum.integer = 2; sv.emptyConfigString = 1;
    clients[0].state = CS_PRIMED; clients[0].gamestateSent = 1;
    clients[1].state = CS_CONNECTED;
    sv.configstrings[CS_MODELS+7] = 2; sv.configstrings[CS_MODELS+9] = 3;
    sv.configstrings[CS_TAGS+5] = 4;
    assert(CODOL_PublishAssetConfigstring(CS_MODELS+7)==1);
    assert(commands==2 && !strcmp(last_command,"d 1317 attachment"));
    assert(CODOL_PublishAssetConfigstring(CS_TAGS+5)==1);
    assert(commands == 3 && !strcmp(last_command, "d 5300 tag_weapon"));
    assert(CODOL_ServerModelToWire(7) == 1 && CODOL_ServerModelToWire(9) == 2);
    assert(CODOL_ServerTagToWire(5) == 1 && CODOL_ServerTagToWire(0) == 0);
    assert(CODOL_ServerModelToWire(1) == -1 && CODOL_ServerModelToWire(MAX_MODELS) == -1);
    assert(CODOL_RefreshServerAssetNames() && commands == 3);
    assert(CODOL_PublishAssetConfigstring(CS_MODELS)==1);
    assert(CODOL_PublishAssetConfigstring(CS_TAGS)==1);
    assert(CODOL_PublishAssetConfigstring(CS_MODELS-1)==1); /* selector 829 */
    assert(CODOL_PublishAssetConfigstring(CS_MODELS+MAX_MODELS)==1); /* sound sentinel */
    assert(CODOL_PublishAssetConfigstring(CS_TAGS-1)==1); /* head icon */
    assert(CODOL_PublishAssetConfigstring(CS_TAGS+MAX_TAGS)==1); /* native item mask 0x90a */
    assert(commands==3);
    engine.modelindex = 7; engine.attachModelIndex[0] = 9; engine.attachTagIndex[0] = 5;
    engine.attachedVehEntNum=ENTITYNUM_NONE;
    assert(CODOL_OverlayServerClient(&wire, &engine));
    assert(field(&wire, 0x14) == 1 && field(&wire, 0x20) == 2 && field(&wire, 0x60) == 1);
    model_entity_test();
    {
        clientState_t ring[4] = {{0}};
        codol_client_state_t result[2], unchanged[2];
        memset(result, 0xa5, sizeof(result)); memcpy(unchanged, result, sizeof(result));
        ring[3] = engine; ring[0] = engine; ring[0].clientIndex = 1;
        ring[0].attachedVehEntNum=17;
        svsHeader.snapshotClients = ring; svsHeader.numSnapshotClients = 4;
        svsHeader.nextSnapshotClients = 5;
        svs.numSnapshotClients=4;
        svs.snapshotClients[3]=ring[3]; svs.snapshotClients[0]=ring[0];
        assert(CODOL_CaptureClientAbilities(3,NULL));
        assert(CODOL_CaptureClientAbilities(4,NULL));
        assert(!CODOL_CollectServerClients(3, 2, result, 1) && !memcmp(result, unchanged, sizeof(result)));
        assert(CODOL_CollectServerClients(3, 2, result, 2));
        assert(result[0].number == 0 && result[1].number == 1);
        assert(field(&result[0],0xbc)==2047 && field(&result[1],0xbc)==17);
        assert(field(&result[1], 0x14) == 1 && field(&result[1], 0x20) == 2);
        memcpy(unchanged, result, sizeof(result));
        ring[0].attachedVehEntNum=ENTITYNUM_WORLD;
        assert(!CODOL_CollectServerClients(3,2,result,2) && !memcmp(result,unchanged,sizeof(result)));
        ring[0].attachedVehEntNum=17;
        ring[0].clientIndex = 0;
        assert(!CODOL_CollectServerClients(3, 2, result, 2));
        ring[0].clientIndex = 32;
        assert(!CODOL_CollectServerClients(3, 2, result, 2));
        ring[0].clientIndex = 1; ring[0].modelindex = MAX_MODELS;
        assert(!CODOL_CollectServerClients(3, 2, result, 2));
        assert(!memcmp(result, unchanged, sizeof(result)));
        svsHeader.nextSnapshotClients = 8;
        assert(!CODOL_CollectServerClients(3, 2, result, 2)); /* overwritten */
        assert(!CODOL_CollectServerClients(8, 1, result, 2)); /* future */
        assert(CODOL_CollectServerClients(8, 0, NULL, 0));
        svsHeader.snapshotClients = NULL;
        assert(!CODOL_CollectServerClients(7, 1, result, 2));
    }
    saved = wire; engine.attachModelIndex[1] = MAX_MODELS;
    assert(!CODOL_OverlayServerClient(&wire, &engine) && !memcmp(&wire, &saved, sizeof(wire)));
    strings[2] = "replacement"; /* recycled handle with new text */
    assert(CODOL_RefreshServerAssetNames() && commands == 4);
    assert(CODOL_ServerModelToWire(7) == 3);
    {
        gentity_t model={0}; codol_entity_state_t entity={0};
        model.s.eType=ET_SCRIPTMOVER; model.s.index=7; entity.type=ET_SCRIPTMOVER;
        assert(CODOL_OverlayServerModelEntity(&entity,&model) && entity_field(&entity,0x5c)==3);
    }
    engine.attachModelIndex[1] = 0;
    assert(CODOL_OverlayServerClient(&wire, &engine) && field(&wire, 0x14) == 3);
    assert(!strcmp(CODOL_GetConfigstring(CODOL_ServerConfigstrings(), CODOL_CS_MODELS+1), "body"));
    strings[2] = "invalid;command";
    assert(CODOL_PublishAssetConfigstring(CS_MODELS+7)==-1 && commands == 4);
    sv.configstrings[CS_MODELS+7] = 1;
    assert(CODOL_PublishAssetConfigstring(CS_MODELS+7)==1 && CODOL_ServerModelToWire(7) == -1);
    assert(commands==4); /* Removal unbinds the native ID; retained wire names stay stable. */
    strings[5]="sound_alias"; sv.configstrings[CS_SOUNDS+255]=5;
    assert(CODOL_PublishAssetConfigstring(CS_SOUNDS+255)==1);
    assert(commands==5 && !strcmp(last_command,"d 3650 sound_alias"));
    assert(!strcmp(CODOL_GetConfigstring(CODOL_ServerConfigstrings(),3650),"sound_alias"));
    assert(!CODOL_GetConfigstring(CODOL_ServerConfigstrings(),CS_SOUNDS+255));
    assert(CODOL_RefreshServerAssetNames() && commands==5);
    strings[5]="replacement_sound";
    assert(CODOL_PublishAssetConfigstring(CS_SOUNDS+255)==1 && commands==6);
    assert(!strcmp(last_command,"d 3650 replacement_sound"));
    strings[5]="invalid;alias";
    assert(CODOL_PublishAssetConfigstring(CS_SOUNDS+255)==-1 && commands==6);
    assert(!strcmp(CODOL_GetConfigstring(CODOL_ServerConfigstrings(),3650),"replacement_sound"));
    sv.configstrings[CS_SOUNDS+255]=1;
    assert(CODOL_PublishAssetConfigstring(CS_SOUNDS+255)==1 && commands==7);
    assert(!strcmp(last_command,"d 3650 ") && !*CODOL_GetConfigstring(CODOL_ServerConfigstrings(),3650));
    assert(CODOL_PublishAssetConfigstring(CS_SOUNDS+MAX_SOUNDS)==1 && commands==7); /* FX bank */
    strings[6]="90"; strings[7]="\"compass_map_native\" -100 200 300 -400";
    sv.configstrings[822]=6; sv.configstrings[823]=7;
    assert(CODOL_PublishAssetConfigstring(822)==1 && commands==9);
    assert(!strcmp(last_command,"d 1303 \"compass_map_native\" -100 200 300 -400"));
    assert(!strcmp(CODOL_GetConfigstring(CODOL_ServerConfigstrings(),1302),"90"));
    assert(!CODOL_GetConfigstring(CODOL_ServerConfigstrings(),822));
    assert(CODOL_RefreshServerMapConfigstrings() && commands==9);
    assert(CODOL_PublishAssetConfigstring(824)==0); /* Native vision, not CoDOL second minimap. */
    strings[7]="invalid\ncommand";
    assert(CODOL_PublishAssetConfigstring(823)==-1 && commands==9);
    sv.configstrings[823]=1;
    assert(CODOL_PublishAssetConfigstring(823)==1 && commands==10);
    assert(!strcmp(last_command,"d 1303 ") && !*CODOL_GetConfigstring(CODOL_ServerConfigstrings(),1303));
    {
        int prior=commands; codol_configstrings_t *bank=CODOL_ServerConfigstrings();
        strings[5]="600000"; sv.configstrings[11]=5;
        assert(CODOL_PublishAssetConfigstring(11)==1 && commands==++prior);
        assert(!strcmp(last_command,"d 15 600000") && !strcmp(CODOL_GetConfigstring(bank,15),"600000"));
        assert(!CODOL_GetConfigstring(bank,11));
        strings[7]="-1024 2048 128"; sv.configstrings[12]=7;
        assert(CODOL_PublishAssetConfigstring(12)==1 && commands==++prior);
        assert(!strcmp(last_command,"d 16 -1024 2048 128") && !strcmp(CODOL_GetConfigstring(bank,16),strings[7]));
        assert(!CODOL_GetConfigstring(bank,12));
        assert(CODOL_RefreshServerMapConfigstrings() && commands==prior);
        strings[5]="700000\ncommand";
        assert(CODOL_PublishAssetConfigstring(11)==-1 && commands==prior);
        assert(!strcmp(CODOL_GetConfigstring(bank,15),"600000"));
        strings[5]="700000"; clients[0].gamestateSent=0;
        assert(CODOL_RefreshServerMapConfigstrings() && commands==prior);
        assert(!strcmp(CODOL_GetConfigstring(bank,15),"700000"));
        clients[0].gamestateSent=1;
        sv.configstrings[11]=sv.configstrings[12]=1;
        assert(CODOL_PublishAssetConfigstring(11)==1 && commands==prior+2);
        assert(!*CODOL_GetConfigstring(bank,15) && !*CODOL_GetConfigstring(bank,16));
        assert(!strcmp(last_command,"d 16 "));
    }
    {
        const char *constants[]={"4276","white","681","MP_VICTORY",
            "24","shared_setting","224","10","25","private_setting","225","unchanged"};
        static gclient_t hudClient; hudElemState_t *hud=&hudClient.ps.hud; codol_hud_state_t result={0},before;
        int prior=commands;
        strings[5]="white"; strings[6]="MP_VICTORY";
        sv.configstrings[CS_MATERIALS+7]=5; sv.configstrings[CS_LOCALIZEDSTRINGS+9]=6;
        assert(CODOL_PublishAssetConfigstring(CS_MATERIALS+7)==-1 && commands==prior);
        replicated.flags=CVAR_SYSTEMINFO; replicated.string="10"; private_var.string="secret";
        assert(CODOL_SetServerInheritedConfigstrings("mp",6,constants));
        assert(CODOL_RefreshServerAssetNames() && commands==prior);
        assert(CODOL_ServerMaterialToWire(7)==1 && CODOL_ServerLocalizedToWire(9)==1);
        assert(!CODOL_GetConfigstring(CODOL_ServerConfigstrings(),4276));
        hud->current[0].type=HE_TYPE_TEXT; hud->current[0].text=9; hud->current[0].label=9;
        hud->current[0].materialIndex=7; hud->current[0].flags=5;
        CODOL_CopyClientHudFontScale(&hudClient,0,&hud->current[0],&g_hudelems[0]);
        assert(CODOL_CollectServerHud(&result,hud) && result.count[1]==1 && commands==prior);
        assert(CODOL_CaptureClientSnapshotHud(0,200,hud));
        assert(result.elements[1][0].field[22]==1 && result.elements[1][0].field[33]==1 && result.elements[1][0].field[4]==1 && result.elements[1][0].field[14]==5);
        strings[5]="custom_material";
        assert(CODOL_PublishAssetConfigstring(CS_MATERIALS+7)==1 && commands==++prior);
        assert(!strcmp(last_command,"d 4277 custom_material") && CODOL_ServerMaterialToWire(7)==2);
        strings[6]="Hello player";
        assert(CODOL_PublishAssetConfigstring(CS_LOCALIZEDSTRINGS+9)==1 && commands==++prior);
        assert(!strcmp(last_command,"d 682 Hello player") && CODOL_ServerLocalizedToWire(9)==2);
        strings[7]="preallocated"; sv.configstrings[CS_MATERIALS+8]=7;
        assert(CODOL_SetConfigstring(CODOL_ServerConfigstrings(),4278,"preallocated"));
        assert(CODOL_PublishAssetConfigstring(CS_MATERIALS+8)==1 && commands==++prior);
        assert(!strcmp(last_command,"d 4278 preallocated") && CODOL_ServerMaterialToWire(8)==3);
        assert(CODOL_CollectServerHud(&result,hud) && result.elements[1][0].field[22]==2 && result.elements[1][0].field[4]==2 && commands==prior);
        {
            codol_hud_state_t captured;
            assert(CODOL_CopyClientSnapshotHud(0,200,&captured));
            assert(captured.elements[1][0].field[22]==1 && captured.elements[1][0].field[4]==1);
            CODOL_ClearClientSnapshotHud(0);
        }
        before=result; hud->current[0].soundID=1;
        assert(!CODOL_CollectServerHud(&result,hud) && !memcmp(&result,&before,sizeof(result)));
        hud->current[0].soundID=0; hud->current[0].flags=0x80; /* outside seven-bit C1 mask */
        assert(!CODOL_CollectServerHud(&result,hud) && !memcmp(&result,&before,sizeof(result)));
        hud->current[0].flags=5; strings[6]="invalid\ncommand";
        assert(CODOL_PublishAssetConfigstring(CS_LOCALIZEDSTRINGS+9)==-1 && commands==prior);
        sv.configstrings[CS_LOCALIZEDSTRINGS+9]=1;
        assert(CODOL_PublishAssetConfigstring(CS_LOCALIZEDSTRINGS+9)==1 && CODOL_ServerLocalizedToWire(9)==-1 && commands==prior);
        assert(!CODOL_CollectServerHud(&result,hud) && !memcmp(&result,&before,sizeof(result)));
        assert(!strcmp(CODOL_GetConfigstring(CODOL_ServerConfigstrings(),682),"Hello player"));
    }
    {
        int prior=commands; codol_configstrings_t *bank=CODOL_ServerConfigstrings();
        assert(CODOL_RefreshServerDvars() && commands==prior && !CODOL_GetConfigstring(bank,224));
        assert(!CODOL_GetConfigstring(bank,24) && !CODOL_GetConfigstring(bank,225));
        replicated.string="20";
        assert(CODOL_RefreshServerDvars() && commands==++prior && !strcmp(last_command,"d 224 20"));
        assert(!strcmp(CODOL_GetConfigstring(bank,224),"20") && !CODOL_GetConfigstring(bank,225));
        assert(CODOL_RefreshServerDvars() && commands==prior);
        replicated.string="invalid\ncommand";
        assert(!CODOL_RefreshServerDvars() && commands==prior && !strcmp(CODOL_GetConfigstring(bank,224),"20"));
        replicated.string="";
        assert(CODOL_RefreshServerDvars() && commands==++prior && !strcmp(last_command,"d 224 "));
        replicated.string="30";
        assert(CODOL_SetConfigstring(bank,24,""));
        assert(CODOL_RefreshServerDvars() && commands==prior); /* Explicit name terminator wins over constants. */
        assert(CODOL_SetConfigstring(bank,24,"unknown_setting"));
        assert(CODOL_RefreshServerDvars() && commands==prior); /* Unknown and private variables stay untouched. */
        assert(CODOL_SetConfigstring(bank,24,"shared_setting"));
        clients[0].gamestateSent=0;
        assert(CODOL_RefreshServerDvars() && commands==prior && !strcmp(CODOL_GetConfigstring(bank,224),"30"));
        clients[0].gamestateSent=1;
    }
    {
        int prior=commands;
        codol_configstrings_t *bank=CODOL_ServerConfigstrings();
        assert(CODOL_SetConfigstring(bank,CODOL_CS_WEAPONS+4,"m4_mp"));
        assert(CODOL_SetConfigstring(bank,CODOL_CS_WEAPONS+5,"gl_m4_mp"));
        clients[0].gamestateSent=0;
        CODOL_BroadcastWeaponConfigstrings(4,2); assert(commands==prior);
        clients[0].gamestateSent=1;
        CODOL_BroadcastWeaponConfigstrings(4,1);
        assert(commands==++prior && !strcmp(last_command,"d 5366 m4_mp"));
        CODOL_BroadcastWeaponConfigstrings(5,1);
        assert(commands==++prior && !strcmp(last_command,"d 5367 gl_m4_mp"));
        CODOL_BroadcastWeaponConfigstrings(CODOL_WEAPON_SLOTS-1,2);
        assert(commands==prior);
    }
    {
        int prior = commands;
        clients[0].gamestateSent = 0;
        assert(CODOL_PublishServerId(257) && commands == prior);
        assert(!strcmp(CODOL_GetConfigstring(CODOL_ServerConfigstrings(), 3), "257"));
        clients[0].gamestateSent = 1;
        assert(CODOL_PublishServerId(258));
        assert(commands == ++prior && !strcmp(last_command, "d 3 258"));
        assert(CODOL_PublishServerId(258) && commands == prior);
        assert(CODOL_PublishServerId(INT32_MIN));
        assert(commands == ++prior && !strcmp(last_command, "d 3 -2147483648"));
    }
    CODOL_ResetServerAssetNames(); CODOL_ResetServerConfigstrings();
    assert(CODOL_ServerMaterialToWire(7)==-1 && CODOL_ServerLocalizedToWire(9)==-1);
    assert(CODOL_ServerModelToWire(9) == -1 && CODOL_ServerTagToWire(5) == -1);
    puts("PASS: production model/tag publication, handle recycling and client-state mapping");
    frame_assembly_test();
    return 0;
}
