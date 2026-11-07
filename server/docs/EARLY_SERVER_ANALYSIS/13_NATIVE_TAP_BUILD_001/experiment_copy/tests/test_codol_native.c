/* Integration tests use the actual netchan entry points and MSG implementation.
 * UDP socket sends and selected engine services use controlled fixtures. */
#include "codol_weapon_state.h"
#include "netchan.h"
#include "codol_wire.h"
#include "codol_crypto.h"
#include "codol_game.h"
#include "codol_sv_state.h"
#include "codol_engine_state.h"
#include "qcommon_io.h"
#include "codol_sv_frame.h"
#include "codol_events.h"
#include "codol_playerstate_ext.h"
#include "codol_entitystate_ext.h"
#include "codol_zone_path.h"
#include "codol_weapon_bits.h"
#include "codol_radar_state.h"
#include "bg.h"
#include <math.h>
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
/* Since dda81bd5 a weapon phase that inherited another animation publishes
 * that animation translated rather than refusing the frame. Only animations
 * outside the native 5-bit+toggle range must still be refused; any refusal
 * must leave the frame untouched. */
#define CODOL_ANIM_REFUSED_OR_TRANSLATED(call) do {     if((unsigned)ps->weapAnim & ~0x21fu) {         assert(!(call) && !memcmp(&state,&before,sizeof(state)));     } else if(!(call)) {         assert(!memcmp(&state,&before,sizeof(state)));     } else state=before; } while(0)

static byte datagrams[4][1500];
static int sizes[4], sends, fail_send;
static gclient_t event_clients[2];
extern const char *codol_player_failure;

/* Entity snapshots use the real model-scale producer. Keep optional trace
 * logging off in this fixture and fail if it is invoked unexpectedly. */
cvar_t *codol_debugTrace;
/* The obituary decoder's producer object also names this engine service;
 * no weapon definition is needed by the no-weapon death code in this test. */
struct WeaponDef *BG_GetWeaponDef(int index)
{
    (void)index;
    return NULL;
}
void QDECL Com_Printf(conChannel_t channel, const char *fmt, ...)
{
    (void)channel; (void)fmt;
    assert(!"unexpected entity trace");
}

/* Link-time socket substitution exists only in this test executable. */
qboolean __wrap_NET_SendPacket(netsrc_t sock, int length, const void *data, netadr_t *to)
{
    (void)sock; (void)to;
    if (fail_send) return qfalse;
    assert(sends < 4 && length <= 1500);
    memcpy(datagrams[sends], data, length);
    sizes[sends++] = length;
    return qtrue;
}

qboolean Assert_MyHandler(const char *exp, const char *file, int line,
                          const char *function, const char *fmt, ...)
{
    (void)fmt;
    fprintf(stderr, "Engine assertion: %s (%s:%d %s)\n", exp, file, line, function);
    abort();
}

static void netchan_test(void)
{
    netchan_t tx, rx;
    netadr_t adr = {0};
    byte unsent[4000], fragments[4000], rx_unsent[4000], rx_fragments[4000];
    byte body[2324], input[4000];
    msg_t msg;
    int i;
    for (i = 0; i < (int)sizeof(body); ++i) body[i] = (byte)i;
    Netchan_Setup(NS_SERVER, &tx, adr, 17, unsent, sizeof(unsent),
                  fragments, sizeof(fragments));
    Netchan_Setup(NS_CLIENT, &rx, adr, 17, rx_unsent, sizeof(rx_unsent),
                  rx_fragments, sizeof(rx_fragments));
    fail_send = 1;
    assert(!Netchan_Transmit(&tx, sizeof(body), body));
    assert(tx.unsentFragments && tx.unsentFragmentStart == 0 && tx.outgoingSequence == 1);
    fail_send = 0;
    assert(Netchan_TransmitNextFragment(&tx));
    assert(tx.unsentFragments && tx.outgoingSequence == 1);
    assert(!Netchan_Transmit(&tx, 10, body)); /* cannot overwrite pending data */
    assert(Netchan_TransmitNextFragment(&tx));
    assert(!tx.unsentFragments && tx.outgoingSequence == 2 && sends == 2);
    assert(!Netchan_TransmitNextFragment(&tx));
    assert(sizes[0] == 1172 && sizes[1] == 1172); /* no empty final fragment */
    memcpy(input, datagrams[1], sizes[1]);
    MSG_Init(&msg, input, sizeof(input)); msg.cursize = sizes[1];
    assert(!Netchan_Process(&rx, &msg) && rx.incomingSequence == 0);
    memcpy(input, datagrams[0], sizes[0]);
    MSG_Init(&msg, input, sizeof(input)); msg.cursize = sizes[0];
    assert(Netchan_Process(&rx, &msg) && rx.incomingSequence == 1);
    assert(msg.readcount == 4 && msg.bit == 32 && msg.cursize == 2328);
    assert(!memcmp(input + 4, body, sizeof(body)));
    assert(!Netchan_Process(&rx, &msg)); /* duplicate delivery */

    /* Client->server qport and unfragmented cursor. */
    Netchan_Setup(NS_SERVER, &rx, adr, 17, rx_unsent, sizeof(rx_unsent),
                  rx_fragments, sizeof(rx_fragments));
    MSG_Init(&msg, input, sizeof(input));
    msg.cursize = CODOL_WritePacket(input, sizeof(input), 5, 17, body, 10, 0);
    assert(Netchan_Process(&rx, &msg));
    assert(msg.readcount == 6 && rx.incomingSequence == 5);
    assert(!memcmp(input + msg.readcount, body, 10));
    /* A failed first fragment is queued for retry, but submission reports the
     * failed send. Successful submission drains every fragment in this frame. */
    Netchan_Setup(NS_SERVER, &tx, adr, 17, unsent, sizeof(unsent), fragments, sizeof(fragments));
    fail_send = 1;
    assert(!CODOL_NetchanSubmit(&tx, 10, body));
    assert(tx.outgoingSequence == 1 && !tx.unsentFragments);
    assert(!CODOL_NetchanSubmit(&tx, sizeof(body), body));
    assert(tx.outgoingSequence == 1 && tx.unsentFragments && !memcmp(unsent, body, sizeof(body)));
    assert(!CODOL_NetchanSubmit(&tx, 10, body));
    assert(tx.unsentLength == sizeof(body) && tx.unsentFragmentStart == 0);
    fail_send = 0; sends = 0;
    assert(Netchan_TransmitNextFragment(&tx));
    assert(Netchan_TransmitNextFragment(&tx));
    assert(tx.outgoingSequence == 2 && !tx.unsentFragments);
    assert(CODOL_NetchanSubmit(&tx, 10, body) && tx.outgoingSequence == 3);
    sends = 0;
    assert(CODOL_NetchanSubmit(&tx, sizeof(body), body));
    assert(tx.outgoingSequence == 4 && !tx.unsentFragments && sends == 2);
    tx.outgoingSequence = CODOL_SEQUENCE_MASK+1;
    assert(!CODOL_NetchanSubmit(&tx, sizeof(body), body) && !tx.unsentFragments);
}

static void unhex(byte *out, const char *hex)
{
    unsigned value;
    while (*hex) {
        assert(sscanf(hex, "%2x", &value) == 1);
        *out++ = value; hex += 2;
    }
}

static void crypto_test(void)
{
    /* Independent alpha0022 fixture: x=bytes(range(28)), security=range(16),
     * payload=range(47), counter=65536, tag=0x1234. Crosses IV counter epoch. */
    byte x[28], security[16], key[24], want_key[24], plain[47];
    byte record[100], expected[63], decoded[47], original[47];
    size_t size, plain_length;
    uint32_t counter;
    unsigned i;
    for (i = 0; i < sizeof(x); ++i) x[i] = i;
    for (i = 0; i < sizeof(security); ++i) security[i] = i;
    for (i = 0; i < sizeof(plain); ++i) plain[i] = i;
    unhex(want_key, "334e4079ec32bcddaf6fe63832ba78741bb83d64ec3255b8");
    unhex(expected, "060234120000fa92fa3f0a49beec2f007071876cf71a244c71a6fc80b813261a"
                    "c9bf111264f2d5f30284eb6db2b93ef5fe4f0ab98b183b8495953c20a0965d");
    assert(CODOL_DeriveKey(key, x, security));
    assert(!memcmp(key, want_key, 24));
    size = CODOL_EncryptRecord(record, sizeof(record), plain, sizeof(plain),
                               65536, 0x1234, key);
    assert(size == sizeof(expected) && !memcmp(record, expected, size));
    assert(CODOL_DecryptRecord(decoded, sizeof(decoded), &plain_length, &counter,
                               record, size, 65535, 0x1234, key));
    assert(counter == 65536 && plain_length == sizeof(plain));
    assert(!memcmp(decoded, plain, sizeof(plain)));
    memset(original, 0xa5, sizeof(original));
    for (i = 0; i < size; ++i) {
        /* Every single-byte modification must fail without producing plaintext. */
        memcpy(decoded, original, sizeof(decoded));
        record[i] ^= 1; plain_length = 999; counter = 999;
        assert(!CODOL_DecryptRecord(decoded, sizeof(decoded), &plain_length, &counter,
                                    record, size, 65535, 0x1234, key));
        assert(!memcmp(decoded, original, sizeof(decoded)));
        assert(plain_length == 999 && counter == 999);
        record[i] ^= 1;
    }
    for (i = 0; i < size; ++i)
        assert(!CODOL_DecryptRecord(decoded, sizeof(decoded), &plain_length, &counter,
                                    record, i, 65535, 0x1234, key));
    assert(!CODOL_DecryptRecord(decoded, 46, &plain_length, &counter,
                                record, size, 65535, 0x1234, key));
    record[size] = 0;
    assert(!CODOL_DecryptRecord(decoded, sizeof(decoded), &plain_length, &counter,
                                record, size + 1, 65535, 0x1234, key));
}

static void usercmd_bridge_test(void)
{
    byte data[32];
    msg_t msg;
    codol_msg_t writer;
    codol_usercmd_t old = {0}, decoded, saved;
    usercmd_t engine;
    int cursor, bit;
    CODOL_MsgWriteInit(&writer, data, sizeof(data));
    /* Start with an opcode in the same partially occupied bit pool. */
    CODOL_WriteBits(&writer, 1, 3);
    CODOL_WriteByte(&writer, 1);
    CODOL_WriteBits(&writer, 1, 1); /* relative time */
    CODOL_WriteByte(&writer, 11);
    CODOL_WriteBits(&writer, 1, 1); /* unchanged path A, XOR key low bit */
    CODOL_WriteBits(&writer, 7, 3);
    assert(!writer.failed);
    MSG_Init(&msg, data, sizeof(data)); msg.cursize = writer.size;
    assert(MSG_ReadBits(&msg, 3) == 1 && MSG_ReadByte(&msg) == 1);
    old.serverTime = 100;
    old.weapon = 769; old.offHandIndex = 1001; old.altModeWeapon = 1023;
    old.buttons = 0x100000 | 4;
    old.direction = 9; old.meleeChargeYaw = 32768;
    assert(CODOL_ReadUsercmdMSG(&msg, 0x579d5, &old, &decoded));
    assert(decoded.serverTime == 111 && decoded.weapon == 769);
    assert(decoded.altModeWeapon == 1023 && msg.readcount == writer.size);
    CODOL_ResetGameInputCore();
    assert(CODOL_MapWeapon(769, 17));
    assert(CODOL_MapWeapon(1001, 18));
    CODOL_ToEngineUsercmd(&decoded, &engine, 3, 4);
    assert(engine.weapon == 17 && engine.offHandIndex == 18);
    assert(engine.forwardmove == 127 && engine.rightmove == -127);
    /* C1's raw right-trigger remains in the native sidecar; only the shared
     * button 4 is translated to the retained engine command. */
    assert(decoded.buttons == (0x100000 | 4) && engine.buttons == 4);
    assert(engine.meleeChargeYaw == 180.0f);
    saved = decoded;
    decoded.buttons = KEY_MASK_PRONE;
    CODOL_ToEngineUsercmd(&decoded, &engine, 3, 4);
    assert(engine.buttons & KEY_MASK_PRONE);
    CODOL_ToEngineUsercmd(&decoded, &engine, 3, 4);
    assert(engine.buttons & KEY_MASK_PRONE); /* held C1 stance remains a level */
    decoded = saved;
    CODOL_RecordUsercmd(0, &decoded);
    assert(CODOL_LastUsercmd(0)->altModeWeapon == 1023);
    CODOL_ResetClientInputCore(0);
    assert(!CODOL_LastUsercmd(0)->serverTime);
    decoded.weapon = 1022;
    CODOL_ToEngineUsercmd(&decoded, &engine, 3, 4);
    assert(engine.weapon == 3); /* unknown wire IDs never alias a byte index */
    saved = decoded;
    cursor = msg.readcount; bit = msg.bit;
    assert(!CODOL_ReadUsercmdMSG(&msg, 0, &old, &decoded));
    assert(msg.overflowed && msg.readcount == cursor && msg.bit == bit);
    assert(!memcmp(&decoded, &saved, sizeof(decoded)));
    CODOL_ResetGameInputCore();
    assert(CODOL_WeaponToEngine(769) == -1);
}

static void usermove_packet_test(void)
{
    byte buffer[4096]; codol_msg_t wire; msg_t msg={0};
    codol_usercmd_t commands[CODOL_MAX_USERCMDS],saved[CODOL_MAX_USERCMDS];
    float origin[3],prior[3]={99,98,97}; uint32_t time; unsigned count,i,length;
    for(count=1;count<=CODOL_MAX_USERCMDS;count=count==1 ? 2 : CODOL_MAX_USERCMDS) {
        CODOL_MsgWriteInit(&wire,buffer,sizeof(buffer));
        CODOL_WriteByte(&wire,0xab); /* Already consumed count/prefix. */
        for(i=0;i<count;++i) {
            CODOL_WriteBits(&wire,1,1); CODOL_WriteByte(&wire,10); /* time delta */
            CODOL_WriteBits(&wire,0,1); CODOL_WriteBits(&wire,7,3); /* unchanged */
        }
        CODOL_WriteLong(&wire,0x42c80000); CODOL_WriteLong(&wire,0xc2480000);
        CODOL_WriteLong(&wire,0x41480000); CODOL_WriteLong(&wire,1234);
        assert(!wire.failed); length=wire.size;
        memset(commands,0xa5,sizeof(commands));
        msg=(msg_t){0}; msg.data=buffer; msg.cursize=length; msg.readcount=1;
        assert(CODOL_ReadUsermoveMSG(&msg,0,count,commands,CODOL_MAX_USERCMDS,origin,&time));
        for(i=0;i<count;++i) assert(commands[i].serverTime==(i+1)*10 && !commands[i].buttons);
        assert(origin[0]==100 && origin[1]==-50 && origin[2]==12.5f && time==1234);
        assert(msg.readcount==(int)length && msg.bit==(int)wire.bit);
        if(count==2) {
            memcpy(saved,commands,sizeof(saved));
            for(i=1;i<length;++i) {
                msg=(msg_t){0}; msg.data=buffer; msg.cursize=i; msg.readcount=1;
                memcpy(origin,prior,sizeof(origin)); time=5678;
                assert(!CODOL_ReadUsermoveMSG(&msg,0,count,commands,CODOL_MAX_USERCMDS,origin,&time));
                assert(msg.overflowed && msg.readcount==1 && !msg.bit);
                assert(!memcmp(commands,saved,sizeof(saved)) && !memcmp(origin,prior,sizeof(origin)) && time==5678);
            }
            for(i=0;i<3;++i) {
                byte old[4]; memcpy(old,buffer+length-16+4*i,4);
                memset(buffer+length-16+4*i,255,4);
                msg=(msg_t){0}; msg.data=buffer; msg.cursize=length; msg.readcount=1;
                assert(!CODOL_ReadUsermoveMSG(&msg,0,count,commands,CODOL_MAX_USERCMDS,origin,&time));
                assert(!memcmp(commands,saved,sizeof(saved)) && !memcmp(origin,prior,sizeof(origin)) && time==5678);
                memcpy(buffer+length-16+4*i,old,4);
            }
            msg=(msg_t){0}; msg.data=buffer; msg.cursize=length; msg.readcount=1;
            assert(!CODOL_ReadUsermoveMSG(&msg,0,count,commands,1,origin,&time));
        }
        if(count==CODOL_MAX_USERCMDS) break;
    }
}
static void gamestate_bridge_test(void)
{
    byte buffer[4096], reference[4096];
    msg_t msg;
    codol_msg_t wire;
    int length;
    CODOL_ResetServerConfigstrings();
    /* The gamestate writer requires the inherited fastfile table for the zone
     * it is asked to write, so the client's string namespace is validated
     * against exactly what it will apply the overrides to. */
    assert(CODOL_SetServerMapIdentity("mp_killhouse_sh","mp"));
    assert(!CODOL_SetServerMapIdentity("mp_cargoship_sh","mp"));
    assert(CODOL_SetServerInheritedConfigstrings("mp",0,NULL));
    assert(CODOL_ServerMapIdentityMatches("mp_killhouse_sh","mp"));
    assert(!CODOL_ServerMapIdentityMatches("mp_cargoship_sh","mp"));
    assert(CODOL_SetConfigstring(CODOL_ServerConfigstrings(), 6517, "55"));
    assert(CODOL_SetServerId(INT32_MIN));
    assert(!strcmp(CODOL_GetConfigstring(CODOL_ServerConfigstrings(),3),"-2147483648"));
    assert(CODOL_SetServerId(INT32_MAX));
    assert(!strcmp(CODOL_GetConfigstring(CODOL_ServerConfigstrings(),3),"2147483647"));
    assert(CODOL_SetServerId(257));
    MSG_Init(&msg, buffer, sizeof(buffer));
    MSG_WriteLong(&msg, 123); /* cleartext reliable ACK is outside gamestate */
    MSG_WriteByte(&msg, 1); MSG_WriteLong(&msg, 17); MSG_WriteData(&msg, "test", 5);
    length = msg.cursize;
    assert(CODOL_WriteServerGamestate(&msg, "mp_killhouse_sh", "mp", "tdm", 16, 17, 3, 456,"Test Server"));
    CODOL_MsgWriteInit(&wire, reference, sizeof(reference));
    assert(CODOL_WriteGamestate(&wire, CODOL_ServerConfigstrings(), "mp_killhouse_sh",
        "mp", 0xad1e1713, 17, 3, 456));
    assert(buffer[0] == 123 && buffer[4] == 1 && buffer[length] == 2);
    assert(msg.cursize == length + wire.size);
    assert(!memcmp(buffer + length, reference, wire.size));
    assert(msg.bit == msg.cursize * 8 && buffer[msg.cursize-1] == 5);
    assert(!strcmp(CODOL_GetConfigstring(CODOL_ServerConfigstrings(), 0),
        "\\g_gametype\\tdm\\mapname\\mp_killhouse_sh\\2485\\16\\2492\\Test Server\\2482\\0"));
    MSG_Init(&msg, buffer, 12); MSG_WriteLong(&msg, 123);
    assert(!CODOL_WriteServerGamestate(&msg, "mp_killhouse_sh", "mp", "tdm", 16, 17, 3, 456,"Test Server"));
    assert(msg.overflowed && msg.cursize == 4); /* partial bytes cannot become a sendable message */
    MSG_Init(&msg, buffer, sizeof(buffer));
    assert(!CODOL_WriteServerGamestate(&msg, "map", "tdm", "tdm", 16, 17, 3, 456,"Test Server"));
    assert(msg.overflowed && !msg.cursize);
    MSG_Init(&msg, buffer, sizeof(buffer));
    assert(!CODOL_WriteServerGamestate(&msg, "mp_cargoship_sh", "mp", "tdm", 16, 17, 3, 456,"Test Server"));
    assert(msg.overflowed && !msg.cursize);
    {
        unsigned bad_limits[2]={0,19},i;
        for(i=0;i<2;++i) {
            MSG_Init(&msg,buffer,sizeof(buffer));
            assert(!CODOL_WriteServerGamestate(&msg,"mp_killhouse_sh","mp","tdm",bad_limits[i],17,0,456,"Test Server"));
            assert(msg.overflowed && !msg.cursize);
        }
        MSG_Init(&msg,buffer,sizeof(buffer));
        assert(!CODOL_WriteServerGamestate(&msg,"mp_killhouse_sh","mp","tdm",18,17,18,456,"Test Server"));
        assert(msg.overflowed && !msg.cursize);
        MSG_Init(&msg,buffer,sizeof(buffer));
        assert(CODOL_WriteServerGamestate(&msg,"mp_killhouse_sh","mp","tdm",18,17,17,456,"Test Server"));
        assert(!strcmp(CODOL_GetConfigstring(CODOL_ServerConfigstrings(),0),"\\g_gametype\\tdm\\mapname\\mp_killhouse_sh\\2485\\18\\2492\\Test Server\\2482\\0"));
    }
    {
        char hostname[257],before[1024]; unsigned i;
        const char *invalid[]={"bad\\key","bad\nname","bad\rname","bad\"name","bad;name",NULL};
        strcpy(before,CODOL_GetConfigstring(CODOL_ServerConfigstrings(),0));
        for(i=0;i<sizeof(invalid)/sizeof(invalid[0]);++i) {
            MSG_Init(&msg,buffer,sizeof(buffer));
            assert(!CODOL_WriteServerGamestate(&msg,"mp_killhouse_sh","mp","tdm",18,17,0,456,invalid[i]));
            assert(msg.overflowed && !msg.cursize && !strcmp(before,CODOL_GetConfigstring(CODOL_ServerConfigstrings(),0)));
        }
        memset(hostname,'a',256); hostname[256]=0;
        assert(!CODOL_SetServerInfo("mp_killhouse_sh","tdm",18,hostname));
        hostname[255]=0;
        assert(CODOL_SetServerInfo("mp_killhouse_sh","tdm",18,hostname));
        assert(strstr(CODOL_GetConfigstring(CODOL_ServerConfigstrings(),0),hostname));
        assert(CODOL_SetServerInfo("mp_killhouse_sh","tdm",18,""));
        assert(!strcmp(CODOL_GetConfigstring(CODOL_ServerConfigstrings(),0),"\\g_gametype\\tdm\\mapname\\mp_killhouse_sh\\2485\\18\\2492\\\\2482\\0"));
    }
    CODOL_ResetServerConfigstrings();
    assert(!CODOL_ServerConfigstrings()->count);
}

static uint32_t player_word(const codol_player_fields_t *state, unsigned offset)
{
    unsigned i;
    for (i = 0; i < CODOL_PLAYER_FIELDS; ++i)
        if (CODOL_PlayerField(i)->offset == offset) return state->field[i];
    assert(0); return 0;
}
static float player_float(const codol_player_fields_t *state, unsigned offset)
{
    uint32_t word = player_word(state, offset);
    float value; memcpy(&value, &word, sizeof(value)); return value;
}
static void engine_movement_test(void)
{
    playerState_t *ps = &event_clients[0].ps;
    codol_player_fields_t state, before;
    memset(ps, 0, sizeof(*ps));
    CODOL_PlayerStateExtClear(ps);
    memset(&state, 0xa5, sizeof(state));
    {
        static const unsigned native_states[]={0,1,2,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24};
        static const unsigned target_states[]={0,1,2,6,7,8,9,10,11,12,13,14,15,16,17,19,18,19,21,22,23,24,25};
        unsigned phase,i;
        ps->weaponTime=649; ps->weaponDelay=150;
        for(i=0;i<sizeof(native_states)/sizeof(native_states[0]);++i) {
            phase=999;
            assert(CODOL_TranslateEngineWeaponState(native_states[i],&phase) && phase==target_states[i]);
            ps->weaponstate=native_states[i]; before=state;
            assert(CODOL_OverlayEnginePrimaryWeaponPhase(&state,ps,0x408));
            assert(CODOL_OverlayEngineWeaponPhase(&before,ps,target_states[i],0x408));
            assert(!memcmp(&state,&before,sizeof(state)));
        }
        for(i=0;i<64;++i) {
            /* 27 is the CoDOL-only offhand detonation state, which the
             * retained engine had no number for. It translates like the
             * rest and so is not a rejection case. Neither are the CoDOL
             * dive phases 28..30, which C1 0x41d1f0/0x41d350/0x41d2a0
             * publish as 31/32/33. */
            if(i>=CODOL_WEAPONSTATE_DIVE_IN && i<=CODOL_WEAPONSTATE_DIVE_OUT) {
                phase=999;
                assert(CODOL_TranslateEngineWeaponState(i,&phase) &&
                       phase==31+(i-CODOL_WEAPONSTATE_DIVE_IN));
                continue;
            }
            if(i<=2 || (i>=5 && i<=24) || i==CODOL_WEAPONSTATE_OFFHAND_DETONATE) continue;
            phase=999; ps->weaponstate=i; before=state;
            assert(!CODOL_TranslateEngineWeaponState(i,&phase) && phase==999);
            assert(!CODOL_OverlayEnginePrimaryWeaponPhase(&state,ps,0x408));
            assert(!memcmp(&state,&before,sizeof(state)));
        }
        ps->weaponstate=-1; before=state;
        assert(!CODOL_OverlayEnginePrimaryWeaponPhase(&state,ps,0x408) && !memcmp(&state,&before,sizeof(state)));
        assert(!CODOL_TranslateEngineWeaponState(0,NULL));
        assert(!CODOL_OverlayEnginePrimaryWeaponPhase(&state,NULL,0));
        {
            const unsigned anims[]={13,15,17,18}; unsigned j,toggle;
            for(i=7;i<=11;++i) for(j=0;j<4;++j) for(toggle=0;toggle<2;++toggle) {
                ps->weaponstate=i; ps->weapAnim=(13+j)|(toggle ? 0x200 : 0);
                assert(CODOL_OverlayEngineReloadPhase(&state,ps));
                assert(player_word(&state,0x278)==i+1);
                assert(player_word(&state,0x268)==(anims[j]|(toggle ? 0x400 : 0)));
                assert(player_word(&state,0x26c)==649 && player_word(&state,0x270)==150);
            }
            before=state; ps->weaponstate=6;
            assert(!CODOL_OverlayEngineReloadPhase(&state,ps) && !memcmp(&state,&before,sizeof(state)));
            ps->weaponstate=7;
            for(i=0;i<2048;++i) {
                if((i>=13 && i<=16) || (i>=0x20d && i<=0x210)) continue;
                ps->weapAnim=i;
                /* Since dda81bd5 a reload phase that inherited another
                 * animation publishes it translated (C1 keeps the hand's
                 * animation across phases); only animations outside the
                 * native 5-bit+toggle range are refused, and a refusal still
                 * leaves the frame untouched. */
                if(i & ~0x21fu) {
                    assert(!CODOL_OverlayEngineReloadPhase(&state,ps) && !memcmp(&state,&before,sizeof(state)));
                } else if(!CODOL_OverlayEngineReloadPhase(&state,ps)) {
                    assert(!memcmp(&state,&before,sizeof(state)));
                } else {
                    assert(player_word(&state,0x278)==8);
                    state=before;
                }
            }
            ps->weapAnim=-1;
            assert(!CODOL_OverlayEngineReloadPhase(&state,ps) && !memcmp(&state,&before,sizeof(state)));
            assert(!CODOL_OverlayEngineReloadPhase(&state,NULL));
        }
        {
            unsigned j,toggle;
            for(i=22;i<=24;++i) for(j=23;j<=25;++j) for(toggle=0;toggle<2;++toggle) {
                ps->weaponstate=i; ps->weapAnim=j|(toggle ? 0x200 : 0); before=state;
                assert(CODOL_OverlayEngineSprintPhase(&state,ps));
                assert(CODOL_OverlayEngineWeaponPhase(&before,ps,i+1,(j+2)|(toggle ? 0x400 : 0)));
                assert(!memcmp(&state,&before,sizeof(state)));
                assert(player_word(&state,0x26c)==649 && player_word(&state,0x270)==150);
            }
            before=state;
            for(i=0;i<64;++i) if(i<22 || i>24) {
                ps->weaponstate=i;
                assert(!CODOL_OverlayEngineSprintPhase(&state,ps) && !memcmp(&state,&before,sizeof(state)));
            }
            ps->weaponstate=22;
            for(i=0;i<2048;++i) {
                if((i>=23 && i<=25) || (i>=0x217 && i<=0x219)) continue;
                ps->weapAnim=i;
                CODOL_ANIM_REFUSED_OR_TRANSLATED(CODOL_OverlayEngineSprintPhase(&state,ps));
            }
            ps->weapAnim=23; ps->weaponTime=32768;
            assert(!CODOL_OverlayEngineSprintPhase(&state,ps) && !memcmp(&state,&before,sizeof(state)));
            ps->weaponTime=0; ps->weaponDelay=0; ps->weaponstate=23; ps->weapAnim=24;
            assert(CODOL_OverlayEngineSprintPhase(&state,ps));
            assert(player_word(&state,0x278)==24 && player_word(&state,0x268)==26);
            assert(!player_word(&state,0x26c) && !player_word(&state,0x270));
            assert(!CODOL_OverlayEngineSprintPhase(&state,NULL) && !CODOL_OverlayEngineSprintPhase(NULL,ps));
        }
        {
            const unsigned source_anims[]={10,17,19,21},target_anims[]={10,19,21,23};
            unsigned j,toggle;
            ps->weaponTime=500; ps->weaponDelay=0;
            for(i=3;i<=4;++i) for(j=0;j<4;++j) for(toggle=0;toggle<2;++toggle) {
                ps->weaponstate=i; ps->weapAnim=source_anims[j]|(toggle ? 0x200 : 0); before=state;
                assert(CODOL_OverlayEngineWeaponDropPhase(&state,ps));
                assert(CODOL_OverlayEngineWeaponPhase(&before,ps,j==1 ? 5 : i,target_anims[j]|(toggle ? 0x400 : 0)));
                assert(!memcmp(&state,&before,sizeof(state)));
                assert(player_word(&state,0x26c)==500 && !player_word(&state,0x270));
            }
            before=state;
            for(i=0;i<64;++i) if(i!=3 && i!=4) {
                ps->weaponstate=i;
                assert(!CODOL_OverlayEngineWeaponDropPhase(&state,ps) && !memcmp(&state,&before,sizeof(state)));
            }
            ps->weaponstate=3;
            for(i=0;i<2048;++i) {
                if(i==10 || i==17 || i==19 || i==21 || i==0x20a || i==0x211 || i==0x213 || i==0x215) continue;
                ps->weapAnim=i;
                CODOL_ANIM_REFUSED_OR_TRANSLATED(CODOL_OverlayEngineWeaponDropPhase(&state,ps));
            }
            ps->weapAnim=17; ps->weaponDelay=32768;
            assert(!CODOL_OverlayEngineWeaponDropPhase(&state,ps) && !memcmp(&state,&before,sizeof(state)));
            ps->weaponTime=0; ps->weaponDelay=0;
            assert(CODOL_OverlayEngineWeaponDropPhase(&state,ps) && player_word(&state,0x278)==5);
            assert(!player_word(&state,0x26c));
            assert(!CODOL_OverlayEngineWeaponDropPhase(NULL,ps) && !CODOL_OverlayEngineWeaponDropPhase(&state,NULL));
        }
        {
            const unsigned source_anims[]={11,12,18,20,22},target_anims[]={11,12,20,22,24};
            unsigned j,toggle;
            ps->weaponTime=3000; ps->weaponDelay=0;
            for(i=1;i<=2;++i) for(j=0;j<5;++j) for(toggle=0;toggle<2;++toggle) {
                ps->weaponstate=i; ps->weapAnim=source_anims[j]|(toggle ? 0x200 : 0); before=state;
                assert(CODOL_OverlayEngineWeaponRaisePhase(&state,ps));
                assert(CODOL_OverlayEngineWeaponPhase(&before,ps,i,target_anims[j]|(toggle ? 0x400 : 0)));
                assert(!memcmp(&state,&before,sizeof(state)) && player_word(&state,0x26c)==3000);
            }
            before=state;
            for(i=0;i<64;++i) if(i!=1 && i!=2) {
                ps->weaponstate=i;
                assert(!CODOL_OverlayEngineWeaponRaisePhase(&state,ps) && !memcmp(&state,&before,sizeof(state)));
            }
            ps->weaponstate=1;
            for(i=0;i<2048;++i) {
                if(i==11 || i==12 || i==18 || i==20 || i==22 || i==0x20b || i==0x20c || i==0x212 || i==0x214 || i==0x216) continue;
                ps->weapAnim=i;
                CODOL_ANIM_REFUSED_OR_TRANSLATED(CODOL_OverlayEngineWeaponRaisePhase(&state,ps));
            }
            ps->weapAnim=12; ps->weaponTime=32768;
            assert(!CODOL_OverlayEngineWeaponRaisePhase(&state,ps) && !memcmp(&state,&before,sizeof(state)));
            ps->weaponTime=0;
            assert(CODOL_OverlayEngineWeaponRaisePhase(&state,ps) && !player_word(&state,0x26c));
            assert(!CODOL_OverlayEngineWeaponRaisePhase(NULL,ps) && !CODOL_OverlayEngineWeaponRaisePhase(&state,NULL));
        }
        {
            const unsigned phases[][4]={{0,0,0,0},{5,2,6,2},{5,3,6,3},{5,5,6,5},{5,6,6,6},
                {6,4,7,4},{6,7,7,7},{1,12,1,12},{2,18,2,20},{3,17,5,19},{4,19,4,21},
                {7,13,8,13},{11,16,12,18},{22,23,23,25},{23,24,24,26},{24,25,25,27},
                {12,8,13,8},{12,9,13,9},{13,8,14,8},{13,9,14,9},{14,8,15,8},{14,9,15,9},
                {15,19,16,21},{16,18,17,20},{16,26,17,31},{17,2,19,2},
                {18,18,18,20},{18,26,18,31},{19,2,19,2},{20,20,21,22},
                {20,27,21,32},{21,27,22,32}};
            unsigned j,toggle;
            ps->weaponTime=330; ps->weaponDelay=17;
            for(j=0;j<sizeof(phases)/sizeof(*phases);++j) for(toggle=0;toggle<2;++toggle) {
                ps->weaponstate=phases[j][0]; ps->weapAnim=phases[j][1]|(toggle ? 0x200 : 0); before=state;
                assert(CODOL_OverlayEnginePrimaryWeapon(&state,ps));
                assert(CODOL_OverlayEngineWeaponPhase(&before,ps,phases[j][2],phases[j][3]|(toggle ? 0x400 : 0)));
                assert(!memcmp(&state,&before,sizeof(state)));
            }
            before=state;
            for(i=0;i<2048;++i) {
                unsigned a=i&~0x200u;
                if(a==2 || a==3 || a==5 || a==6) continue;
                ps->weaponstate=5; ps->weapAnim=i;
                CODOL_ANIM_REFUSED_OR_TRANSLATED(CODOL_OverlayEnginePrimaryWeapon(&state,ps));
            }
            /* Melee no longer refuses an unexpected animation: a state that
             * carries a raise or drop animation is translated the way the
             * drop and raise phases translate it. Only bits outside the
             * animation and ADS mask are still refused. */
            for(j=12;j<=14;++j) for(i=0;i<2048;++i) {
                if(!(i & ~0x21fu)) continue;
                ps->weaponstate=j; ps->weapAnim=i;
                assert(!CODOL_OverlayEnginePrimaryWeapon(&state,ps) && !memcmp(&state,&before,sizeof(state)));
            }
            ps->weaponstate=15; ps->weapAnim=8;
            CODOL_ANIM_REFUSED_OR_TRANSLATED(CODOL_OverlayEnginePrimaryWeapon(&state,ps));
            for(j=15;j<=21;++j) for(i=0;i<2048;++i) {
                unsigned a=i&~0x200u;
                if((j==15 && a==19) || ((j==16 || j==18) && (a==18 || a==26)) ||
                   ((j==17 || j==19) && a==2) || (j==20 && (a==20 || a==27)) ||
                   (j==21 && a==27)) continue;
                ps->weaponstate=j; ps->weapAnim=i;
                CODOL_ANIM_REFUSED_OR_TRANSLATED(CODOL_OverlayEngineOffhandPhase(&state,ps));
            }
            ps->weaponstate=5; ps->weapAnim=2; ps->weaponTime=32768;
            assert(!CODOL_OverlayEnginePrimaryWeapon(&state,ps) && !memcmp(&state,&before,sizeof(state)));
            assert(!CODOL_OverlayEnginePrimaryWeapon(NULL,ps) && !CODOL_OverlayEnginePrimaryWeapon(&state,NULL));
        }
        ps->weaponTime=649; ps->weaponDelay=150; ps->weaponstate=999; ps->weapAnim=999;
        assert(CODOL_OverlayEngineWeaponPhase(&state,ps,13,0x408));
        assert(player_word(&state,0x26c)==649 && player_word(&state,0x270)==150);
        assert(player_word(&state,0x278)==13 && player_word(&state,0x268)==0x408);
        before=state; ps->weaponDelay=32768;
        assert(!CODOL_OverlayEngineWeaponPhase(&state,ps,13,0x408) && !memcmp(&state,&before,sizeof(state)));
        ps->weaponDelay=-32768; ps->weaponTime=32767;
        assert(CODOL_OverlayEngineWeaponPhase(&state,ps,63,2047));
        assert(player_word(&state,0x270)==(uint32_t)-32768 && player_word(&state,0x26c)==32767);
        before=state;
        assert(!CODOL_OverlayEngineWeaponPhase(&state,ps,64,0) && !memcmp(&state,&before,sizeof(state)));
        assert(!CODOL_OverlayEngineWeaponPhase(&state,ps,0,2048) && !memcmp(&state,&before,sizeof(state)));
        memset(&state,0xa5,sizeof(state));
    }
    ps->commandTime = 20000; ps->clientNum = 3;
    ps->speed = 190; ps->gravity = 800; ps->moveSpeedScaleMultiplier = 1.0f;
    ps->origin[0] = 21.25f; ps->origin[1] = -200.5f; ps->origin[2] = 64.0f;
    ps->velocity[1] = 123.0f; ps->viewangles[1] = 270.0f; ps->delta_angles[0] = -30.0f;
    ps->groundEntityNum = ENTITYNUM_WORLD; ps->viewHeightTarget = 60; ps->viewHeightCurrent = 59.5f;
    ps->bobCycle = 255; ps->movementDir = -1;
    assert(CODOL_OverlayEngineMovement(&state, ps));
    assert(player_word(&state, 0) == 20000 && player_word(&state, 0x140) == 3);
    assert(player_word(&state, 0x90) == 800 && player_word(&state, 0x98) == 190);
    assert(player_float(&state, 0x254) == 1.0f);
    assert(player_float(&state, 0x1c) == 21.25f && player_float(&state, 0x20) == -200.5f);
    assert(player_float(&state, 0x24) == 64.0f && player_float(&state, 0x2c) == 123.0f);
    assert(player_float(&state, 0x150) == 270.0f && player_float(&state, 0x9c) == -30.0f);
    assert(player_word(&state, 0xa8) == 2046 && player_word(&state, 0x158) == 60);
    /* Zero means linked to entity 0 in C1 and suppresses the eye-height add. */
    assert(player_word(&state, 0x1ec) == ENTITYNUM_NONE);
    assert(player_float(&state, 0x15c) == 59.5f && player_word(&state, 0xe8) == UINT32_MAX);
    assert(player_word(&state, 0x10) == 0xa5a5a5a5); /* flags require separate translation */
    {
        /* Crouching and reversing back to standing keep the live interpolation
         * epoch and direction, rather than inheriting a previous snapshot. */
        ps->viewHeightLerpTime=19950; ps->viewHeightLerpTarget=40; ps->viewHeightLerpDown=1;
        assert(CODOL_OverlayEngineMovement(&state,ps));
        assert(player_word(&state,0x160)==19950 && player_word(&state,0x164)==40 && player_word(&state,0x168)==1);
        ps->viewHeightLerpTime=20000; ps->viewHeightLerpTarget=60; ps->viewHeightLerpDown=0;
        assert(CODOL_OverlayEngineMovement(&state,ps));
        assert(player_word(&state,0x160)==20000 && player_word(&state,0x164)==60 && !player_word(&state,0x168));
        before=state; ps->viewHeightLerpTarget=128;
        assert(!CODOL_OverlayEngineMovement(&state,ps) && !memcmp(&state,&before,sizeof(state)));
        ps->viewHeightLerpTarget=-129;
        assert(!CODOL_OverlayEngineMovement(&state,ps) && !memcmp(&state,&before,sizeof(state)));
        ps->viewHeightLerpTarget=-128; ps->viewHeightLerpDown=2;
        assert(!CODOL_OverlayEngineMovement(&state,ps) && !memcmp(&state,&before,sizeof(state)));
        ps->viewHeightLerpDown=-1;
        assert(!CODOL_OverlayEngineMovement(&state,ps) && !memcmp(&state,&before,sizeof(state)));
        ps->viewHeightLerpDown=1; ps->viewHeightLerpTime=INT32_MIN;
        assert(CODOL_OverlayEngineMovement(&state,ps));
        assert(player_word(&state,0x160)==UINT32_C(0x80000000) && player_word(&state,0x164)==(uint32_t)-128);
        ps->viewHeightLerpTarget=127;
        assert(CODOL_OverlayEngineMovement(&state,ps) && player_word(&state,0x164)==127);
        ps->viewHeightLerpTime=ps->viewHeightLerpTarget=ps->viewHeightLerpDown=0;
        assert(CODOL_OverlayEngineMovement(&state,ps));
        assert(!player_word(&state,0x160) && !player_word(&state,0x164) && !player_word(&state,0x168));
    }
    {
        unsigned bit,slot,initial;
        for(slot=0;slot<CODOL_PLAYER_FIELDS;++slot) if(CODOL_PlayerField(slot)->offset==0xc) break;
        assert(slot<CODOL_PLAYER_FIELDS);
        for(initial=0;initial<2;++initial) for(bit=0;bit<32;++bit) {
            state.field[slot]=initial ? UINT32_MAX : UINT32_C(0x12345678);
            before=state;
            ps->pm_flags=(int)(UINT32_C(1)<<bit);
            assert(CODOL_OverlayEngineMovement(&state,ps));
            /* The native movement producer now stores C1 pm_flags directly. */
            before.field[slot]=(uint32_t)ps->pm_flags;
            assert(!memcmp(&state,&before,sizeof(state)));
        }
        ps->pm_flags=0x8000;
        assert(CODOL_OverlayEngineMovement(&state,ps) && (player_word(&state,0xc)&0x8000));
        ps->pm_flags=0;
        assert(CODOL_OverlayEngineMovement(&state,ps) && !(player_word(&state,0xc)&0x8000));
    }
    ps->groundEntityNum = ENTITYNUM_NONE;
    assert(CODOL_OverlayEngineMovement(&state, ps) && player_word(&state, 0xa8) == 2047);
    ps->groundEntityNum = 17;
    assert(CODOL_OverlayEngineMovement(&state, ps) && player_word(&state, 0xa8) == 17);
    {
        const int timers[]={-32768,-1,0,1,3000,32767},owners[]={0,ENTITYNUM_WORLD-1,ENTITYNUM_WORLD,ENTITYNUM_NONE};
        unsigned a,b,c,k;
        for(a=0;a<6;++a) for(b=0;b<6;++b) for(c=0;c<4;++c) {
            ps->grenadeTimeLeft=timers[a]; ps->throwBackGrenadeTimeLeft=timers[b]; ps->throwBackGrenadeOwner=owners[c];
            ps->weapFlags=2; before=state;
            assert(CODOL_OverlayEngineGrenadeState(&state,ps));
            assert(player_word(&state,0x34)==(uint32_t)timers[a] && player_word(&state,0x3c)==(uint32_t)timers[b]);
            assert(player_word(&state,0x38)==(unsigned)owners[c]); /* identity: 2046/2047 are shared sentinels */
            assert(player_word(&state,0x40)==0); /* no captured throwback weapon */
            assert(player_word(&state,0x344)==(player_word(&before,0x344)|2u));
            for(k=0;k<CODOL_PLAYER_FIELDS;++k) {
                unsigned off=CODOL_PlayerField(k)->offset;
                if(off!=0x34 && off!=0x38 && off!=0x3c && off!=0x40 && off!=0x344)
                    assert(state.field[k]==before.field[k]);
            }
        }
        for(k=0;k<32;++k) {
            before=state; ps->weapFlags=(int)(UINT32_C(1)<<k);
            assert(CODOL_OverlayEngineGrenadeState(&state,ps));
            assert(player_word(&state,0x344)==((player_word(&before,0x344)&~2u)|(k==1 ? 2u : 0u)));
        }
        before=state;
        ps->grenadeTimeLeft=32768;
        assert(!CODOL_OverlayEngineGrenadeState(&state,ps) && !memcmp(&state,&before,sizeof(state)));
        ps->grenadeTimeLeft=-32769;
        assert(!CODOL_OverlayEngineGrenadeState(&state,ps) && !memcmp(&state,&before,sizeof(state)));
        ps->grenadeTimeLeft=0; ps->throwBackGrenadeTimeLeft=32768;
        assert(!CODOL_OverlayEngineGrenadeState(&state,ps) && !memcmp(&state,&before,sizeof(state)));
        ps->throwBackGrenadeTimeLeft=-32769;
        assert(!CODOL_OverlayEngineGrenadeState(&state,ps) && !memcmp(&state,&before,sizeof(state)));
        ps->throwBackGrenadeTimeLeft=0; ps->throwBackGrenadeOwner=ENTITYNUM_NONE+1;
        assert(!CODOL_OverlayEngineGrenadeState(&state,ps) && !memcmp(&state,&before,sizeof(state)));
        ps->throwBackGrenadeOwner=-1;
        assert(!CODOL_OverlayEngineGrenadeState(&state,ps) && !memcmp(&state,&before,sizeof(state)));
        assert(!CODOL_OverlayEngineGrenadeState(NULL,ps) && !CODOL_OverlayEngineGrenadeState(&state,NULL));
    }
    before = state; ps->origin[2] = NAN; ps->pm_flags=0x8000;
    assert(!CODOL_OverlayEngineMovement(&state, ps) && !memcmp(&before, &state, sizeof(state)));
    ps->origin[2] = 0; ps->clientNum = 32; ps->pm_flags=0;
    assert(!CODOL_OverlayEngineMovement(&state, ps) && !memcmp(&before, &state, sizeof(state)));
}

static void engine_player_mode_test(void)
{
    static const unsigned modes[] = {0, 1, 2, 3, 5, 6, 7, 8, 9};
    playerState_t ps = {0};
    codol_player_fields_t state, before;
    unsigned mode, bits;
    for (mode = 0; mode < sizeof(modes)/sizeof(modes[0]); ++mode) {
        for (bits = 0; bits < 8; ++bits) {
            memset(&state, 0, sizeof(state));
            ps.pm_type = modes[mode]; ps.otherFlags = bits;
            assert(CODOL_OverlayEnginePlayerMode(&state, &ps));
            assert(player_word(&state, 4) == modes[mode]);
            assert(player_word(&state, 0x10) == bits);
        }
    }
    /* Mode and otherFlags are carried in the native C1 representation. */
    memset(&state, 0xa5, sizeof(state));
    ps.pm_type = 4; ps.otherFlags = 0xfffffff9;
    assert(CODOL_OverlayEnginePlayerMode(&state, &ps));
    assert(player_word(&state, 0x10) == UINT32_C(0xfffffff9));
    before = state; ps.pm_type = 10;
    assert(!CODOL_OverlayEnginePlayerMode(&state, &ps) && !memcmp(&state, &before, sizeof(state)));
    ps.pm_type = -1;
    assert(!CODOL_OverlayEnginePlayerMode(&state, &ps) && !memcmp(&state, &before, sizeof(state)));
}

static void engine_weapon_health_test(void)
{
    playerState_t ps = {0};
    codol_player_fields_t state, before;
    codol_player_array_updates_t updates = {0}, old_updates;
    memset(&state, 0xa5, sizeof(state));
    CODOL_ResetWeaponMap();
    assert(CODOL_MapWeapon(777, 7) && CODOL_MapWeapon(900, 8) && CODOL_MapWeapon(1023, 127));
    ps.weapon = 7; ps.offHandIndex = 127;
    assert(CODOL_OverlayEngineWeaponSelection(&state, &ps, 8));
    assert(player_word(&state, 0x33c) == 777 && player_word(&state, 0x340) == 900);
    assert(player_word(&state, 0x328) == 1023 && player_word(&state, 0x344) == 0xa5a5a5a5);
    before = state;
    assert(!CODOL_OverlayEngineWeaponSelection(&state, &ps, 9));
    assert(!memcmp(&state, &before, sizeof(state)));
    ps.offHandIndex = -1;
    assert(!CODOL_OverlayEngineWeaponSelection(&state, &ps, 8));
    assert(!memcmp(&state, &before, sizeof(state)));
    ps.weapon = 0; ps.offHandIndex = 0;
    assert(CODOL_OverlayEngineWeaponSelection(&state, &ps, 0));
    assert(!player_word(&state, 0x33c) && !player_word(&state, 0x340) && !player_word(&state, 0x328));
    /* Slot 1 is the dead yaw (C1 ps+0x194); it is published with health. */
    ps.stats[0] = 75; ps.stats[1] = 270; ps.stats[2] = 100;
    updates.stats_mask = 10; updates.stats[1] = 5; updates.stats[3] = 7;
    updates.clip_mask = 4; updates.clip_ammo[2][0] = 30;
    assert(CODOL_OverlayEngineHealth(&updates, &ps));
    assert(updates.stats_mask == 15 && updates.stats[0] == 75 && updates.stats[2] == 100);
    assert(updates.stats[1] == 270 && updates.stats[3] == 7 && updates.clip_ammo[2][0] == 30);
    /* Script health beyond the sixteen-bit slot saturates instead of
     * rejecting the frame (the killstreak test hook sets 100000). */
    old_updates = updates; ps.stats[0] = 100000; ps.stats[2] = -40000;
    assert(CODOL_OverlayEngineHealth(&updates, &ps));
    assert(updates.stats[0] == 32767 && updates.stats[2] == -32768);
    assert(updates.stats[1] == old_updates.stats[1] && updates.stats[3] == old_updates.stats[3]);
    ps.stats[2] = 100;
    ps.stats[0] = 0;
    assert(CODOL_OverlayEngineHealth(&updates, &ps) && updates.stats[0] == 0);
    CODOL_ResetWeaponMap();
}

static void engine_inventory_test(void)
{
    playerState_t *ps = &event_clients[0].ps;
    codol_player_array_updates_t out = {0}, before;
    uint32_t raised[CODOL_WEAPON_BIT_WORDS] = {0};
    unsigned i;
    memset(ps, 0, sizeof(*ps));
    CODOL_PlayerStateExtClear(ps);
    CODOL_ResetWeaponMap();
    for (i = 1; i <= 16; ++i) assert(CODOL_MapWeapon(700+i, i));
    CODOL_WeaponBitsOwnedSet(ps, 3, 1);
    CODOL_WeaponBitsOwnedSet(ps, 9, 1);
    raised[0] = 1u << 9;
    out.stats_mask = 5; out.stats[0] = 100; out.clip_mask = 4;
    assert(CODOL_OverlayEngineInventory(&out, ps, raised));
    assert(out.weapons_mask == 0x7fff && out.weapon_index_mask == 0x7fff);
    assert(out.weapon_index[0] == 703 && out.weapon_index[1] == 709);
    assert(!out.weapon_flags[0] && out.weapon_flags[1] == 1);
    assert(out.stats[0] == 100 && out.clip_mask == 4);
    CODOL_WeaponBitsOwnedSet(ps, 3, 0);
    assert(CODOL_OverlayEngineInventory(&out, ps, raised));
    assert(out.weapon_index[0] == 709 && !out.weapon_index[1] && !out.weapon_flags[1]);
    CODOL_WeaponBitsOwnedSet(ps, 9, 0);
    assert(CODOL_OverlayEngineInventory(&out, ps, NULL));
    for (i = 0; i < 15; ++i) assert(!out.weapon_index[i] && !out.weapon_flags[i]);
    for (i = 1; i <= 15; ++i) CODOL_WeaponBitsOwnedSet(ps, i, 1);
    assert(CODOL_OverlayEngineInventory(&out, ps, NULL));
    assert(out.weapon_index[14] == 715);
    before = out;
    CODOL_WeaponBitsOwnedSet(ps, 16, 1);
    assert(!CODOL_OverlayEngineInventory(&out, ps, NULL) && !memcmp(&out, &before, sizeof(out)));
    CODOL_PlayerStateExtClear(ps);
    CODOL_WeaponBitsOwnedSet(ps, 20, 1);
    assert(!CODOL_OverlayEngineInventory(&out, ps, NULL) && !memcmp(&out, &before, sizeof(out)));
    CODOL_PlayerStateExtClear(ps);
    CODOL_WeaponBitsOwnedSet(ps, 0, 1);
    assert(!CODOL_OverlayEngineInventory(&out, ps, NULL) && !memcmp(&out, &before, sizeof(out)));
    CODOL_PlayerStateExtClear(ps);
    CODOL_ResetWeaponMap();
}

static void engine_ammo_test(void)
{
    playerState_t ps = {0};
    codol_player_array_updates_t out = {0}, before;
    codol_ammo_binding_t clips[16] = {{0}}, reserves[16] = {{0}};
    clips[15].engine_index = 127; clips[15].wire_key = 900;
    reserves[3].engine_index = 17; reserves[3].wire_key = 850;
    ps.ammoclip[127] = 30; ps.ammo[17] = 180;
    out.stats_mask = 5; out.stats[0] = 100; out.weapons_mask = 0x7fff;
    assert(CODOL_OverlayEngineAmmo(&out, &ps, 0x8000, clips, 8, reserves));
    assert(out.clip_mask == 0x8000 && out.clip_index[15] == 900 && out.clip_presence[15] == 3);
    assert(out.clip_ammo[15][0] == 30 && out.clip_ammo[15][1] == 0);
    assert(out.reserve_mask == 8 && out.reserve_type[3] == 850 && out.reserve_ammo[3] == 180);
    assert(out.stats[0] == 100 && out.weapons_mask == 0x7fff);
    before = out; ps.ammo[17] = 2048;
    assert(!CODOL_OverlayEngineAmmo(&out, &ps, 0x8000, clips, 8, reserves));
    assert(!memcmp(&out, &before, sizeof(out)));
    ps.ammo[17] = 2047; ps.ammoclip[127] = 512;
    assert(!CODOL_OverlayEngineAmmo(&out, &ps, 0x8000, clips, 8, reserves));
    assert(!memcmp(&out, &before, sizeof(out)));
    ps.ammoclip[127] = 511;
    assert(CODOL_OverlayEngineAmmo(&out, &ps, 0x8000, clips, 8, reserves));
    assert(out.clip_ammo[15][0] == 511 && out.reserve_ammo[3] == 2047);
    clips[15].engine_index = clips[15].wire_key = -1;
    reserves[3].engine_index = -1;
    assert(CODOL_OverlayEngineAmmo(&out, &ps, 0x8000, clips, 8, reserves));
    assert(out.clip_index[15] == -1 && !out.clip_ammo[15][0] && !out.reserve_ammo[3]);
    before = out;
    assert(!CODOL_OverlayEngineAmmo(&out, &ps, 1, NULL, 0, NULL));
    clips[15].engine_index = 128;
    assert(!CODOL_OverlayEngineAmmo(&out, &ps, 0x8000, clips, 0, NULL));
    assert(!memcmp(&out, &before, sizeof(out)));
    assert(CODOL_OverlayEngineAmmo(&out, &ps, 0, NULL, 0, NULL));
    assert(!memcmp(&out, &before, sizeof(out)));
}

static uint32_t client_word(const codol_client_state_t *state, unsigned offset)
{
    unsigned i;
    for (i = 0; i < CODOL_CLIENT_FIELDS; ++i)
        if (CODOL_ClientField(i)->offset == offset) return state->field[i];
    assert(0); return 0;
}
static int hud_test_resolve(void *,const hudelem_t *,codol_hud_bindings_t *);
int CODOL_CollectServerHud(codol_hud_state_t *out,const hudElemState_t *source)
{
    int calls=0;
    return CODOL_CollectEngineHud(out,source,hud_test_resolve,&calls);
}
static void engine_player_composition_test(void)
{
    playerState_t *ps=&event_clients[0].ps,*bad=&event_clients[1].ps;
    codol_player_fields_t fields,saved;
    codol_player_array_updates_t arrays={0},old_arrays;
    codol_hud_state_t hud,old_hud; int hud_calls=0;
    codol_engine_player_bindings_t bindings={0},invalid;
    uint32_t used[CODOL_WEAPON_BIT_WORDS]={1u<<7}; unsigned i;
    memset(ps,0,sizeof(*ps)); memset(bad,0,sizeof(*bad));
    CODOL_PlayerStateExtClear(ps); CODOL_PlayerStateExtClear(bad);
    {
        codol_ps_ext_t *ext=CODOL_PlayerStateExt(ps);
        assert(ext);
        ext->links_known=1;
        ext->links.linkWeaponEntNum=ENTITYNUM_NONE;
        ext->links.cameraEntNum=ENTITYNUM_NONE;
        ext->links.controlsEntNum=ENTITYNUM_NONE;
    }
    CODOL_ResetWeaponMap(); assert(CODOL_MapWeapon(777,7));
    ps->commandTime=1234; ps->weapon=7; CODOL_WeaponBitsOwnedSet(ps,7,1);
    ps->moveSpeedScaleMultiplier=1; ps->groundEntityNum=ENTITYNUM_WORLD; ps->throwBackGrenadeOwner=ENTITYNUM_NONE;
    ps->stats[0]=100; ps->stats[1]=270; ps->stats[2]=125; ps->ammo[4]=90; ps->ammoclip[3]=23;
    for(i=0;i<7;++i) {
        ps->eventSequence=(ps->eventSequence+1)&255;
        CODOL_PlayerStateEventAdded(ps);
    }
    ps->grenadeTimeLeft=-1; ps->weapFlags=2;
    ps->eFlags=0x40006;
    ps->legsAnim=512|0x400; ps->torsoAnim=1023;
    ps->fWeaponPosFrac=0.75f; ps->aimSpreadScale=127.5f;
    bindings.alt_weapon=7; bindings.used_before=used;
    bindings.hud_resolve=hud_test_resolve; bindings.hud_context=&hud_calls;
    ps->hud.archival[0].type=HE_TYPE_TEXT; ps->hud.archival[0].text=1;
    ps->hud.current[0].type=HE_TYPE_MATERIAL; ps->hud.current[0].materialIndex=2;
    bindings.clip_mask=bindings.reserve_mask=0xffff;
    for(i=0;i<16;++i) { bindings.clips[i]=(codol_ammo_binding_t){-1,-1}; bindings.reserves[i]=(codol_ammo_binding_t){-1,0}; }
    bindings.clips[0]=(codol_ammo_binding_t){3,42}; bindings.reserves[0]=(codol_ammo_binding_t){4,43};
    memset(&fields,0xa5,sizeof(fields)); arrays.stats[1]=77;
    memset(&hud,0xa5,sizeof(hud));
    if(!CODOL_OverlayEnginePlayer(&fields,&arrays,&hud,ps,&bindings)) {
        fprintf(stderr,"player composition: %s\n",codol_player_failure);
        assert(0);
    }
    assert(player_word(&fields,0xc4)==1536 && player_word(&fields,0xcc)==1023);
    assert(hud_calls==2 && hud.count[0]==1 && hud.count[1]==1);
    assert(hud.elements[0][0].field[22]==21 && hud.elements[1][0].field[4]==32);
    assert(player_word(&fields,0)==1234 && player_word(&fields,0xa8)==2046);
    assert(player_word(&fields,0x0ec)==0x40006u);
    assert(player_word(&fields,0x33c)==777 && player_word(&fields,0x340)==777);
    assert(!player_word(&fields,0x278) && !player_word(&fields,0x268));
    assert(player_float(&fields,0x348)==0.75f && player_float(&fields,0x34c)==127.5f);
    assert(player_word(&fields,0x34)==UINT32_MAX && player_word(&fields,0x38)==2047 && (player_word(&fields,0x344)&2));
    assert(arrays.stats[0]==100 && arrays.stats[1]==270 && arrays.stats[2]==125 && arrays.stats_mask==7);
    assert(arrays.weapon_index[0]==777 && arrays.weapon_flags[0]==1 && arrays.weapons_mask==0x7fff);
    assert(arrays.clip_index[0]==42 && arrays.clip_ammo[0][0]==23 && arrays.clip_presence[0]==3);
    assert(arrays.reserve_type[0]==43 && arrays.reserve_ammo[0]==90);
    assert(arrays.clip_index[15]==-1 && !arrays.clip_ammo[15][0] && !arrays.reserve_ammo[15]);
    assert(player_word(&fields,0xf0)==CODOL_PlayerStateEventEpoch(ps));
    saved=fields; old_arrays=arrays; old_hud=hud;
    {
        codol_hud_state_t malformed=old_hud;
        assert(CODOL_CaptureClientSnapshotHud(3,81,&ps->hud));
        *bad=*ps; assert(CODOL_PlayerStateExtCopy(bad,ps)); memset(&bad->hud,0xa5,sizeof(bad->hud));
        invalid=bindings; invalid.hud_resolve=NULL; invalid.hud_context=NULL;
        assert(CODOL_OverlayClientSnapshotPlayer(3,81,&fields,&arrays,&hud,bad,&invalid));
        assert(!memcmp(&fields,&saved,sizeof(fields)) && !memcmp(&arrays,&old_arrays,sizeof(arrays)) &&
            !memcmp(&hud,&old_hud,sizeof(hud)));
        assert(!CODOL_OverlayClientSnapshotPlayer(3,80,&fields,&arrays,&hud,bad,&invalid));
        bad->ammoclip[3]=512; bad->commandTime=9999;
        assert(!CODOL_OverlayClientSnapshotPlayer(3,81,&fields,&arrays,&hud,bad,&invalid));
        malformed.count[1]=CODOL_HUD_SLOTS+1;
        assert(!CODOL_OverlayEnginePlayerWithHud(&fields,&arrays,&hud,ps,&bindings,&malformed));
        assert(!CODOL_OverlayEnginePlayerWithHud(&fields,&arrays,&hud,ps,&bindings,NULL));
        assert(!memcmp(&fields,&saved,sizeof(fields)) && !memcmp(&arrays,&old_arrays,sizeof(arrays)) &&
            !memcmp(&hud,&old_hud,sizeof(hud)));
        CODOL_ClearClientSnapshotHud(3);
        assert(!CODOL_OverlayClientSnapshotPlayer(3,81,&fields,&arrays,&hud,ps,&bindings));
    }
    for(i=0;i<14;++i) {
        *bad=*ps; assert(CODOL_PlayerStateExtCopy(bad,ps)); invalid=bindings;
        switch(i) {
        case 0: bad->speed=-1; break;
        case 1: bad->pm_type=10; break;
        case 2: bad->weapon=126; break;
        case 3: bad->weaponstate=99; break;
        case 4: bad->grenadeTimeLeft=32768; break;
        /* Health above the 16-bit wire slot saturates instead of refusing
         * the frame (CODOL_OverlayEngineHealth), so it is no longer invalid. */
        case 5: continue;
        case 6: CODOL_WeaponBitsOwnedSet(bad,0,1); break;
        case 7: bad->ammoclip[3]=512; break;
        case 8: invalid.event_parameters[3]=2048; break;
        case 9: bad->aimSpreadScale=NAN; break;
        case 10: bad->hud.current[0].text=999; break; /* Fail after archival element resolution. */
        case 11: invalid.hud_resolve=NULL; break;
        case 12: bad->legsAnim=2048; break;
        case 13: bad->torsoAnim=-1; break;
        }
        bad->commandTime=9999;
        assert(!CODOL_OverlayEnginePlayer(&fields,&arrays,&hud,bad,&invalid));
        assert(!memcmp(&fields,&saved,sizeof(fields)) && !memcmp(&arrays,&old_arrays,sizeof(arrays)) &&
            !memcmp(&hud,&old_hud,sizeof(hud)));
    }
    assert(!CODOL_OverlayEnginePlayer(NULL,&arrays,&hud,ps,&bindings));
    assert(!CODOL_OverlayEnginePlayer(&fields,NULL,&hud,ps,&bindings));
    assert(!CODOL_OverlayEnginePlayer(&fields,&arrays,NULL,ps,&bindings));
    assert(!CODOL_OverlayEnginePlayer(&fields,&arrays,&hud,NULL,&bindings));
    assert(!CODOL_OverlayEnginePlayer(&fields,&arrays,&hud,ps,NULL));
    {
        /* Controlled wire fixture seed, not a production default for fields
         * whose engine producers are still unfinished. */
        codol_player_fields_t produced={0}; codol_player_array_updates_t sent={0};
        codol_hud_state_t sent_hud;
        codol_snapshot_state_t snapshot={0}; const codol_snapshot_state_t *base;
        codol_delta_context_t context={0}; codol_history_t *history;
        uint8_t buffer[16384],prefix[4]; msg_t message;
        CODOL_ResetClientSnapshotHistory(3); history=CODOL_ClientSnapshotHistory(3); assert(history);
        assert(CODOL_CaptureClientSnapshotHud(3,100,&ps->hud));
        *bad=*ps; assert(CODOL_PlayerStateExtCopy(bad,ps)); memset(&bad->hud,0xa5,sizeof(bad->hud));
        invalid=bindings; invalid.hud_resolve=NULL; invalid.hud_context=NULL;
        assert(CODOL_OverlayClientSnapshotPlayer(3,100,&produced,&sent,&sent_hud,bad,&invalid));
        snapshot.sequence=100; snapshot.player=&produced; snapshot.hud=&sent_hud;
        context.server_time=1234;
        MSG_Init(&message,buffer,sizeof(buffer)); MSG_WriteLong(&message,123); memcpy(prefix,buffer,4);
        {
            codol_delta_context_t before=context;
            assert(CODOL_SetConfigstring(CODOL_ServerConfigstrings(),16,"1024 2048"));
            assert(!CODOL_PrepareClientSnapshot(3,&message,&snapshot,0,&sent,NULL,0,8,1,&context));
            assert(message.overflowed && message.cursize==4 && !memcmp(prefix,buffer,4));
            assert(!CODOL_ClientSnapshotPending(3) && !memcmp(&before,&context,sizeof(context)));
            MSG_Init(&message,buffer,sizeof(buffer)); MSG_WriteLong(&message,123);
            assert(CODOL_SetConfigstring(CODOL_ServerConfigstrings(),16,"-1024.5 2048.5 128"));
        }
        assert(CODOL_PrepareClientSnapshot(3,&message,&snapshot,0,&sent,NULL,0,8,1,&context));
        assert(context.position_base[0]==-1024 && context.position_base[1]==2049 && context.position_base[2]==128);
        assert(CODOL_SetConfigstring(CODOL_ServerConfigstrings(),16,""));
        assert(message.cursize>4 && !message.overflowed && !memcmp(prefix,buffer,4));
        assert(CODOL_ClientSnapshotPrepared(3,&message,100) && !CODOL_FindHistoryBase(history,100,101));
        assert(CODOL_FinishClientSnapshot(3,&message,100,1));
        base=CODOL_FindHistoryBase(history,100,101); assert(base && base->player!=&produced && base->hud!=&sent_hud);
        assert(player_float(base->player,0x348)==0.75f && player_float(base->player,0x34c)==127.5f);
        assert(player_word(base->player,0x34)==UINT32_MAX && player_word(base->player,0x38)==2047);
        assert(base->hud->count[0]==1 && base->hud->count[1]==1 && base->hud->elements[0][0].field[22]==21);
        *bad=*ps; assert(CODOL_PlayerStateExtCopy(bad,ps)); bad->commandTime=1284; bad->fWeaponPosFrac=1; memset(&bad->hud,0,sizeof(bad->hud));
        assert(CODOL_CaptureClientSnapshotHud(3,101,&bad->hud));
        memset(&bad->hud,0xa5,sizeof(bad->hud));
        assert(CODOL_OverlayClientSnapshotPlayer(3,101,&produced,&sent,&sent_hud,bad,&invalid));
        assert(player_float(base->player,0x348)==0.75f && base->hud->count[0]==1); /* Owned ACK base. */
        snapshot.sequence=101; context.server_time=1284;
        MSG_Init(&message,buffer,sizeof(buffer)); MSG_WriteLong(&message,124);
        assert(CODOL_PrepareClientSnapshot(3,&message,&snapshot,100,&sent,NULL,0,0,1,&context));
        assert(!CODOL_FinishClientSnapshot(3,&message,101,0));
        assert(!CODOL_FindHistoryBase(history,101,102) && CODOL_FindHistoryBase(history,100,102));
        MSG_Init(&message,buffer,sizeof(buffer)); MSG_WriteLong(&message,124);
        assert(CODOL_PrepareClientSnapshot(3,&message,&snapshot,100,&sent,NULL,0,0,1,&context));
        assert(CODOL_FinishClientSnapshot(3,&message,101,1));
        base=CODOL_FindHistoryBase(history,101,102); assert(base);
        assert(player_float(base->player,0x348)==1 && player_word(base->player,0)==1284);
        assert(!base->hud->count[0] && !base->hud->count[1]);
        CODOL_ResetClientSnapshotHistory(3);
    }
    memset(&ps->hud,0,sizeof(ps->hud)); bindings.hud_resolve=NULL;
    assert(CODOL_OverlayEnginePlayer(&fields,&arrays,&hud,ps,&bindings));
    memset(&old_hud,0,sizeof(old_hud)); assert(!memcmp(&hud,&old_hud,sizeof(hud)));
}
static void engine_aim_test(void)
{
    playerState_t ps={0}; codol_player_fields_t state,before;
    const float ads[]={0,0.125f,0.75f,0.999f,1},spread[]={0,0.125f,127.5f,254.75f,255};
    const float invalid[]={NAN,INFINITY,-INFINITY,-0.125f,256}; unsigned a,b,i;
    memset(&state,0xa5,sizeof(state));
    for(a=0;a<5;++a) for(b=0;b<5;++b) {
        before=state; ps.fWeaponPosFrac=ads[a]; ps.aimSpreadScale=spread[b];
        assert(CODOL_OverlayEngineAim(&state,&ps));
        assert(player_float(&state,0x348)==ads[a] && player_float(&state,0x34c)==spread[b]);
        assert(!player_word(&state,0x354) && !player_word(&state,0x358));
        for(i=0;i<CODOL_PLAYER_FIELDS;++i) if(CODOL_PlayerField(i)->offset!=0x348 &&
            CODOL_PlayerField(i)->offset!=0x34c && CODOL_PlayerField(i)->offset!=0x354 &&
            CODOL_PlayerField(i)->offset!=0x358)
            assert(state.field[i]==before.field[i]);
    }
    before=state;
    for(i=0;i<5;++i) {
        ps.fWeaponPosFrac=invalid[i]; ps.aimSpreadScale=0;
        assert(!CODOL_OverlayEngineAim(&state,&ps) && !memcmp(&state,&before,sizeof(state)));
        ps.fWeaponPosFrac=0; ps.aimSpreadScale=invalid[i];
        assert(!CODOL_OverlayEngineAim(&state,&ps) && !memcmp(&state,&before,sizeof(state)));
    }
    ps.fWeaponPosFrac=1.001f; ps.aimSpreadScale=0;
    assert(!CODOL_OverlayEngineAim(&state,&ps) && !memcmp(&state,&before,sizeof(state)));
    assert(!CODOL_OverlayEngineAim(NULL,&ps) && !CODOL_OverlayEngineAim(&state,NULL));
}
static void engine_client_test(void)
{
    clientState_t cs = {0};
    codol_client_assets_t assets = {0};
    codol_client_state_t out, before;
    unsigned i;
    memset(&out, 0xa5, sizeof(out));
    cs.clientIndex = 19; cs.team = TEAM_BLUE; cs.modelindex = 7;
    cs.attachedVehEntNum=ENTITYNUM_NONE;
    cs.attachModelIndex[5] = 9; cs.attachTagIndex[5] = 3;
    strcpy(cs.netname, "Not perk bits");
    assets.model = 1800; assets.attach_model[5] = 2047; assets.attach_tag[5] = 63;
    assert(CODOL_OverlayEngineClient(&out, &cs, &assets));
    assert(out.number == 19 && client_word(&out, 4) == 2 && client_word(&out, 0x14) == 1800);
    assert(client_word(&out, 0x34) == 2047 && client_word(&out, 0x74) == 63);
    for (i = 6; i < 16; ++i) assert(!client_word(&out, 0x20+4*i) && !client_word(&out, 0x60+4*i));
    assert(client_word(&out, 0xc0) == 0xa5a5a5a5 && client_word(&out, 0xcc) == 0xa5a5a5a5);
    assert(client_word(&out,0xbc)==2047);
    {
        const int valid[]={0,17,ENTITYNUM_WORLD-1,ENTITYNUM_NONE},invalid[]={-1,ENTITYNUM_WORLD,MAX_GENTITIES,4095};
        codol_client_state_t reached; codol_delta_context_t context={0};
        for(i=0;i<4;++i) {
            cs.attachedVehEntNum=valid[i];
            assert(CODOL_OverlayEngineClient(&out,&cs,&assets));
            assert(client_word(&out,0xbc)==(unsigned)valid[i]);
            /* Wire reachability is checked using a clean complete test state. */
            reached=(codol_client_state_t){0}; reached.number=cs.clientIndex;
            { unsigned j; for(j=0;j<CODOL_CLIENT_FIELDS;++j)
                if(CODOL_ClientField(j)->offset==0xbc) reached.field[j]=client_word(&out,0xbc); }
            assert(CODOL_ReachClient(&reached,NULL,&reached,&context));
            assert(client_word(&reached,0xbc)==client_word(&out,0xbc));
        }
        before=out;
        for(i=0;i<4;++i) {
            cs.attachedVehEntNum=invalid[i];
            assert(!CODOL_OverlayEngineClient(&out,&cs,&assets) && !memcmp(&out,&before,sizeof(out)));
        }
        cs.attachedVehEntNum=ENTITYNUM_NONE;
    }
    before = out; assets.attach_tag[5] = 64;
    assert(!CODOL_OverlayEngineClient(&out, &cs, &assets) && !memcmp(&out, &before, sizeof(out)));
    assets.attach_tag[5] = 63; assets.model = 0;
    assert(!CODOL_OverlayEngineClient(&out, &cs, &assets) && !memcmp(&out, &before, sizeof(out)));
    memset(&assets, 0, sizeof(assets)); memset(&cs, 0, sizeof(cs));
    cs.team = TEAM_SPECTATOR;
    assert(CODOL_OverlayEngineClient(&out, &cs, &assets));
    /* C1 team getter 0x50e080 returns spectator from jump-table entry 6. */
    assert(client_word(&out, 4) == 6 && !client_word(&out, 0x14));
    assert(!client_word(&out, 0x34) && !client_word(&out, 0x74));
    before = out; cs.clientIndex = 32;
    assert(!CODOL_OverlayEngineClient(&out, &cs, &assets) && !memcmp(&out, &before, sizeof(out)));
}

static uint32_t entity_word(const codol_entity_state_t *state, unsigned offset)
{
    unsigned i;
    for (i = 0; i < CODOL_ENTITY_FIELDS; ++i)
        if (CODOL_EntityField(state->type, i)->offset == offset) return state->field[i];
    assert(0); return 0;
}
static void engine_player_flags_test(void)
{
    playerState_t ps={0}; entityState_t es={0};
    codol_player_fields_t player={0},saved_player;
    codol_entity_state_t entity={0},saved_entity;
    const uint32_t patterns[]={0x55555555,0xaaaaaaaa};
    unsigned pattern,bit,i;
    entity.type=1; es.eType=ET_PLAYER;
    for(pattern=0;pattern<2;++pattern) for(bit=0;bit<=33;++bit) {
        uint32_t input=bit<32 ? UINT32_C(1)<<bit : bit==32 ? UINT32_C(0x0e200000) : 0;
        uint32_t player_expected=input&~(uint32_t)CODOL_PS_EF_RADAR_CARRIERS;
        uint32_t entity_expected=(input&~((uint32_t)CODOL_PS_EF_RADAR_CARRIERS|UINT32_C(0x200000)))|
            ((input&CODOL_PS_EF_RADAR_JAMMER) ? UINT32_C(0x200000) : 0u);
        for(i=0;i<CODOL_PLAYER_FIELDS;++i)
            if(CODOL_PlayerField(i)->offset==0x0ec) player.field[i]=patterns[pattern];
        for(i=0;i<CODOL_ENTITY_FIELDS;++i)
            if(CODOL_EntityField(1,i)->offset==0x008) entity.field[i]=patterns[pattern];
        memcpy(&ps.eFlags,&input,4); memcpy(&es.lerp.eFlags,&input,4);
        assert(CODOL_OverlayEnginePlayerFlags(&player,&ps));
        assert(CODOL_OverlayEnginePlayerEntityFlags(&entity,&es));
        assert(player_word(&player,0x0ec)==player_expected &&
               entity_word(&entity,0x008)==entity_expected);
    }
    saved_player=player; saved_entity=entity;
    assert(!CODOL_OverlayEnginePlayerFlags(NULL,&ps));
    assert(!CODOL_OverlayEnginePlayerFlags(&player,NULL));
    assert(!CODOL_OverlayEnginePlayerEntityFlags(NULL,&es));
    assert(!CODOL_OverlayEnginePlayerEntityFlags(&entity,NULL));
    es.eType=ET_MISSILE;
    assert(!CODOL_OverlayEnginePlayerEntityFlags(&entity,&es));
    assert(!memcmp(&player,&saved_player,sizeof(player)) && !memcmp(&entity,&saved_entity,sizeof(entity)));
}
static void engine_viewhands_wire_test(void)
{
    codol_player_fields_t from={0},to={0},invalid;
    codol_delta_context_t context={20000,{0,0,0},0,0};
    codol_msg_t message;
    byte bytes[128];
    const codol_player_field_t *arms=CODOL_PlayerField(60);
    const codol_player_field_t *hands=CODOL_PlayerField(61);
    /* C1's transition reader consumes these exact consecutive fields as
     * CS_MODELS indices before installing the pair in every equipped weapon. */
    assert(arms && arms->offset==0x144 && arms->bits==11 && arms->hint==0);
    assert(hands && hands->offset==0x148 && hands->bits==11 && hands->hint==0);
    to.field[60]=17; to.field[61]=29;
    CODOL_MsgWriteInit(&message,bytes,sizeof(bytes));
    assert(CODOL_WritePlayerFields(&message,&from,&to,0,&context));
    assert(!message.failed && message.size);
    /* The writer, not only the overlay, enforces the 11-bit model namespace. */
    invalid=to; invalid.field[61]=2048;
    CODOL_MsgWriteInit(&message,bytes,sizeof(bytes));
    assert(!CODOL_WritePlayerFields(&message,&from,&invalid,0,&context));
    assert(message.failed);
}
/* The player event counter belongs to the playerState now, so this harness
 * binds the live storage the extension resolver walks and reports through the
 * same warning hook the server uses. */
const void *CODOL_PlayerStateExtLiveBase(unsigned *count){if(count)*count=2;return event_clients;}
const void *CODOL_PlayerStateExtSnapshotBase(unsigned *count){if(count)*count=0;return NULL;}
const void *CODOL_PlayerStateExtArchiveBase(unsigned *count){if(count)*count=0;return NULL;}
void Com_PrintWarning(conChannel_t channel,const char *fmt,...){(void)channel;(void)fmt;}
static void engine_player_events_test(void)
{
    {
        playerState_t *reloading=&event_clients[1].ps; codol_player_fields_t fields={0};
        uint32_t parameters[4]={99,99,99,99};
        unsigned event;
        memset(reloading,0,sizeof(*reloading)); CODOL_PlayerStateExtClear(reloading);
        reloading->events[0]=EV_RELOAD; reloading->events[1]=EV_RELOAD_FROM_EMPTY;
        reloading->events[2]=EV_RELOAD_START; reloading->events[3]=EV_RECHAMBER_WEAPON;
        for(event=0;event<4;++event) {
            reloading->eventSequence=(reloading->eventSequence+1)&255;
            CODOL_PlayerStateEventAdded(reloading);
        }
        assert(CODOL_ResolveEnginePlayerEventParameters(reloading,parameters));
        assert(CODOL_OverlayEnginePlayerEvents(&fields,reloading,parameters));
        assert(player_word(&fields,0xf0)==4 && player_word(&fields,0xf4)==18);
        assert(player_word(&fields,0xf8)==19 && player_word(&fields,0xfc)==20 && player_word(&fields,0x100)==34);
        assert(!player_word(&fields,0x104) && !player_word(&fields,0x110));
        reloading->eventParms[3]=1;
        assert(!CODOL_ResolveEnginePlayerEventParameters(reloading,parameters));
        assert(!parameters[0] && !parameters[3]);
    }
    playerState_t *ps=&event_clients[0].ps,*other=&event_clients[1].ps;
    codol_player_fields_t wire={0},saved;
    uint32_t parms[4]={2047,0,37,511}; unsigned i;
    memset(ps,0,sizeof(*ps)); memset(other,0,sizeof(*other));
    CODOL_PlayerStateExtClear(ps); CODOL_PlayerStateExtClear(other);
    for(i=0;i<CODOL_PLAYER_FIELDS;++i) wire.field[i]=123;
    /* The extension epoch must be advanced by the same producer hook that
     * advances the retained eight-bit counter. Readers reject an orphaned
     * nonzero counter instead of inventing wrap history. */
    for(i=0;i<255;++i) {
        ps->eventSequence=(ps->eventSequence+1)&255;
        CODOL_PlayerStateEventAdded(ps);
    }
    ps->events[0]=EV_JUMP; ps->events[3]=EV_FIRE_WEAPON;
    assert(CODOL_OverlayEnginePlayerEvents(&wire,ps,parms));
    assert(player_word(&wire,0xf0)==255 && player_word(&wire,0xf4)==120);
    assert(player_word(&wire,0x100)==30 && player_word(&wire,0x104)==2047);
    assert(player_word(&wire,0x110)==511 && player_word(&wire,0x114)==123 && player_word(&wire,0x118)==123);
    /* Three more events through the producer hook: the retained counter wraps,
     * the epoch this state carries does not. */
    for(i=0;i<3;++i) { ps->eventSequence=(ps->eventSequence+1)&255; CODOL_PlayerStateEventAdded(ps); }
    assert(ps->eventSequence==2 && CODOL_PlayerStateEventEpoch(ps)==258);
    assert(CODOL_OverlayEnginePlayerEvents(&wire,ps,parms));
    assert(player_word(&wire,0xf0)==258);
    /* A different state publishes its own history, not a continuation of the
     * one published before it: this is the archived-spectator case. */
    other->events[0]=EV_JUMP; other->events[3]=EV_FIRE_WEAPON;
    for(i=0;i<5;++i) { other->eventSequence=(other->eventSequence+1)&255; CODOL_PlayerStateEventAdded(other); }
    assert(CODOL_OverlayEnginePlayerEvents(&wire,other,parms));
    assert(player_word(&wire,0xf0)==5 && CODOL_PlayerStateEventEpoch(ps)==258);
    saved=wire; parms[3]=2048;
    assert(!CODOL_OverlayEnginePlayerEvents(&wire,ps,parms));
    assert(!memcmp(&wire,&saved,sizeof(wire)));
    parms[3]=511; ps->events[3]=-1;
    assert(!CODOL_OverlayEnginePlayerEvents(&wire,ps,parms));
    assert(!memcmp(&wire,&saved,sizeof(wire)));
    {
        unsigned visible=0;
        /* A native event with no C1 mapping is omitted from its physical slot
         * without rejecting the other three events or changing the epoch. */
        assert(CODOL_ResolveEnginePlayerEventParametersVisible(ps,parms,&visible));
        assert(visible==7 && parms[3]==0);
        assert(CODOL_OverlayEnginePlayerEventsWithShotsVisible(&wire,ps,parms,NULL,visible));
        assert(player_word(&wire,0xf0)==258 && player_word(&wire,0x100)==0 &&
               player_word(&wire,0x110)==0);
    }
    saved=wire;
    ps->events[3]=EV_FIRE_WEAPON; ps->eventSequence=256;
    assert(!CODOL_OverlayEnginePlayerEvents(&wire,ps,parms));
    assert(!memcmp(&wire,&saved,sizeof(wire)));
    ps->eventSequence=2;
}

/* Entity event history is a property of the entity state now, so the harness
 * binds the live entity storage the resolver walks and drives the producer.
 * codol_entitystate_ext.c takes the bases through the same seam. */
/* Three player overlays and the legacy profile reader are owned by the script
 * area and read state only the script VM populates. Linking their translation
 * units would pull the whole VM into this harness for state it never sets, so
 * they are stubbed with the same answer they give for an unpopulated client:
 * nothing to publish, and the overlay step succeeds. */
int CODOL_OverlayEngineThermal(codol_player_fields_t *wire,const playerState_t *ps)
{ return wire && ps; }
int CODOL_OverlayEngineStun(codol_player_fields_t *wire,const playerState_t *ps)
{ return wire && ps; }
int CODOL_ScriptProfileLegacyGetInt(unsigned client,const char *key,int *value)
{ (void)client; (void)key; (void)value; return 0; }

/* Whole-game and per-client reset hooks, plus the glass snapshot pair, reached
 * from codol_game.c / codol_sv_state.c / codol_sv_snapshot.c. This harness
 * never populates the state they clear, and linking their translation units
 * pulls in the player, script and collision areas together with `level`, `cm`,
 * `sv_mapname` and the Cvar registry - state this test does not build. They are
 * stubbed with the answer they give for an unpopulated server: nothing to
 * reset, nothing to publish, and the step succeeds. Without them the whole
 * test-codol target stopped at this link and never reached the later tests.
 */
void CODOL_ResetClientActionSlotState(unsigned client){(void)client;}
void CODOL_ResetLookAtClientState(unsigned client){(void)client;}
void CODOL_KillcamTraceFrame(void){}
/* This fixture has no weapon definitions, so its inventory records have no
 * dual-hand or second-barrel state. Native inventory ownership uses the real
 * extended weapon-bit implementation linked by the test target. */
int CODOL_WeaponIsDualWield(unsigned weapon){(void)weapon;return 0;}
int CODOL_WeaponStateSecondBarrelArmed(const playerState_t *ps){(void)ps;return 0;}
void CODOL_ResetClientKillstreakHud(unsigned client){(void)client;}
void CODOL_PmoveC1ResetClient(unsigned client){(void)client;}
void CODOL_PmoveC1ResetAll(void){}
int  CODOL_RefreshMapSunSampleSize(void){return 1;}
void CODOL_ResetMapSunSampleSize(void){}
int  CODOL_GlassWorldEnsureMap(void){return 1;}
int  CODOL_GlassWorldCapture(codol_glass_wire_piece_t *pieces,size_t capacity,unsigned *count)
{ (void)pieces; (void)capacity; if(count)*count=0; return 1; }
int  CODOL_WriteGlass(codol_msg_t *msg,const codol_glass_wire_piece_t *to,size_t count,
                      const codol_glass_wire_piece_t *base,size_t base_count)
{ (void)msg; (void)to; (void)count; (void)base; (void)base_count; return 1; }
void CODOL_ResetPerkRuntime(unsigned client){(void)client;}
void CODOL_ResetClientRadarTypes(unsigned client){(void)client;}
void CODOL_ResetAllRadarTypes(void){}
int  CODOL_ActorAnimPublished(unsigned client,uint32_t sequence)
{ (void)client; (void)sequence; return 0; }
void CODOL_ActorDeliveryClear(unsigned client){(void)client;}

static gentity_t event_entities[4];
const void *CODOL_EntityStateExtLiveBase(unsigned *count){if(count)*count=4;return event_entities;}
const void *CODOL_EntityStateExtSnapshotBase(unsigned *count){if(count)*count=0;return NULL;}
const void *CODOL_EntityStateExtArchiveBase(unsigned *count){if(count)*count=0;return NULL;}
static void entity_event_produced(entityState_t *es)
{ es->eventSequence=(es->eventSequence+1)&255; CODOL_EntityStateEventAdded(es); }
/* Put an entity's event counter at a chosen value the way the server does:
   through the producer hook, so the extension's epoch agrees with it. Writing
   the counter directly leaves the epoch behind and the overlay rejects the
   entity as desynchronized. */
static void entity_event_seq(entityState_t *es,unsigned count)
{
    CODOL_EntityStateExtClear(es); es->eventSequence=0;
    while(count--) entity_event_produced(es);
}
static void engine_entity_events_test(void)
{
    entityState_t *es=&event_entities[0].s,*other=&event_entities[1].s;
    codol_entity_state_t wire={0},saved;
    uint32_t event=EV_JUMP; unsigned i;
    es->eType=ET_GENERAL;
    memcpy(&es->events[3],&event,4);
    /* An entity state that never had an event publishes a recorded zero. */
    assert(CODOL_OverlayEngineEntityEvents(&wire,es));
    assert(entity_word(&wire,0xb0)==0 && entity_word(&wire,0xc0)==120);
    for(i=1;i<=254;++i) entity_event_produced(es);
    assert(CODOL_OverlayEngineEntityEvents(&wire,es));
    assert(entity_word(&wire,0xb0)==254);
    /* Past the retained counter's wrap the epoch keeps counting, so the
     * published sequence stays continuous modulo 2048. */
    for(i=255;i<=2050;++i) {
        entity_event_produced(es);
        assert(CODOL_OverlayEngineEntityEvents(&wire,es));
        assert(entity_word(&wire,0xb0)==(i&2047));
    }
    saved=wire;
    assert(CODOL_OverlayEngineEntityEvents(&wire,es));
    assert(!memcmp(&saved,&wire,sizeof(wire)));
    /* A second entity publishes its own history, not a continuation. */
    other->eType=ET_GENERAL; memcpy(&other->events[3],&event,4);
    for(i=0;i<3;++i) entity_event_produced(other);
    assert(CODOL_OverlayEngineEntityEvents(&wire,other));
    assert(entity_word(&wire,0xb0)==3);
    saved=wire;
    /* A failure after earlier slots have translated preserves the output. */
    event=UINT32_MAX; memcpy(&other->events[3],&event,4);
    assert(!CODOL_OverlayEngineEntityEvents(&wire,other));
    assert(!memcmp(&saved,&wire,sizeof(wire)));
    event=EV_FIRE_WEAPON; memcpy(&other->events[3],&event,4);
    assert(CODOL_OverlayEngineEntityEvents(&wire,other));
    assert(entity_word(&wire,0xb0)==3 && entity_word(&wire,0xc0)==30);
    saved=wire;
    /* A counter the producers cannot have written, and a state whose counter
     * no longer matches its epoch, are both refused instead of guessed. */
    other->eventSequence=256;
    assert(!CODOL_OverlayEngineEntityEvents(&wire,other));
    other->eventSequence=7;
    assert(!CODOL_OverlayEngineEntityEvents(&wire,other));
    assert(!memcmp(&saved,&wire,sizeof(wire)));
    other->eventSequence=3; other->eType=ET_MISSILE;
    assert(!CODOL_OverlayEngineEntityEvents(&wire,other));
    assert(!memcmp(&saved,&wire,sizeof(wire)));
    other->eType=ET_GENERAL;
    {
        uint32_t parameters[4]={0,255,1024,2047};
        assert(CODOL_OverlayEngineEntityEventQueue(&wire,other,parameters));
        assert(entity_word(&wire,0xb0)==3 && entity_word(&wire,0xc0)==30);
        for(i=0;i<4;++i) assert(entity_word(&wire,0xc4+4*i)==parameters[i]);
        saved=wire;
        for(i=0;i<4;++i) {
            uint32_t prior=parameters[i]; parameters[i]=2048;
            assert(!CODOL_OverlayEngineEntityEventQueue(&wire,other,parameters));
            assert(!memcmp(&saved,&wire,sizeof(wire)));
            parameters[i]=prior;
        }
        event=UINT32_MAX; memcpy(&other->events[3],&event,4);
        assert(!CODOL_OverlayEngineEntityEventQueue(&wire,other,parameters));
        assert(!memcmp(&saved,&wire,sizeof(wire)));
        event=EV_FIRE_WEAPON; memcpy(&other->events[3],&event,4);
        memset(parameters,0,sizeof(parameters));
        assert(CODOL_OverlayEngineEntityEventQueue(&wire,other,parameters));
        for(i=0;i<4;++i) assert(!entity_word(&wire,0xc4+4*i));
        assert(!CODOL_OverlayEngineEntityEventQueue(&wire,other,NULL));
    }
}
static void engine_entity_composition_test(void)
{
    /* The event epoch is keyed off the entityState's address, so the subject
     * has to live in the base this harness publishes rather than on the
     * stack. */
    entityState_t *es=&event_entities[0].s,valid;
    memset(es,0,sizeof(*es));
    codol_entity_state_t wire={0},saved;
    uint32_t parameters[4]={0,255,1024,2047},event=EV_JUMP;
    unsigned type,i;
    CODOL_ResetWeaponMap(); assert(CODOL_MapWeapon(769,7));
    assert(CODOL_MapWeapon(1023,8));
    {
        codol_entity_state_t weapons,before;
        entityState_t source={0};
        memset(&weapons,0xa5,sizeof(weapons)); weapons.type=ET_PLAYER;
        source.eType=ET_PLAYER; source.weapon=7;
        assert(CODOL_OverlayEnginePlayerEntityWeapons(&weapons,&source,8));
        assert(entity_word(&weapons,0xd4)==(769u|(1023u<<16)));
        assert(entity_word(&weapons,0x80)==0xa5a5a5a5);
        assert(CODOL_OverlayEnginePlayerEntityWeapons(&weapons,&source,7));
        assert(entity_word(&weapons,0xd4)==(769u|(769u<<16)));
        source.weapon=0;
        assert(CODOL_OverlayEnginePlayerEntityWeapons(&weapons,&source,0));
        assert(!entity_word(&weapons,0xd4));
        before=weapons;
        source.weapon=1;
        assert(!CODOL_OverlayEnginePlayerEntityWeapons(&weapons,&source,7));
        source.weapon=7;
        assert(!CODOL_OverlayEnginePlayerEntityWeapons(&weapons,&source,1));
        assert(!CODOL_OverlayEnginePlayerEntityWeapons(&weapons,&source,128));
        source.eType=ET_MISSILE;
        assert(!CODOL_OverlayEnginePlayerEntityWeapons(&weapons,&source,7));
        source.eType=ET_PLAYER;
        assert(!CODOL_OverlayEnginePlayerEntityWeapons(&weapons,NULL,7));
        assert(!CODOL_OverlayEnginePlayerEntityWeapons(NULL,&source,7));
        assert(!memcmp(&weapons,&before,sizeof(weapons)));
        weapons.type=ET_GENERAL; before=weapons;
        assert(!CODOL_OverlayEnginePlayerEntityWeapons(&weapons,&source,7));
        assert(!memcmp(&weapons,&before,sizeof(weapons)));
    }
    es->number=23; es->clientNum=5; es->weapon=7; entity_event_seq(es,1);
    es->lerp.eFlags=0x2000a;
    es->lerp.pos.trType=TR_GRAVITY; es->lerp.pos.trTime=19000;
    es->lerp.pos.trBase[2]=100; es->lerp.pos.trDelta[0]=300;
    memcpy(&es->events[3],&event,4);
    assert(CODOL_MapWeapon(25,9));
    for(type=ET_GENERAL;type<=ET_VEHICLE_CORPSE;++type) {
        memset(&wire,0,sizeof(wire)); wire.type=type; es->eType=type;
        es->index=type==ET_ITEM ? 9 : 0;
        for(i=0;i<CODOL_ENTITY_FIELDS;++i)
            if(CODOL_EntityField(type,i)->offset==0x008) wire.field[i]=137;
        if(!CODOL_OverlayEngineEntity(&wire,es,parameters)) { fprintf(stderr,"TYPE %u REJECTED\n",type); assert(0); }
        assert(wire.number==23 && wire.type==type && wire.field[0]==type);
        assert(entity_word(&wire,0x008)==
            ((type==ET_PLAYER || type==ET_PLAYER_CORPSE) ? 0x2000au : 137u));
        assert(entity_word(&wire,0x054)==0x3f800000);
        assert(entity_word(&wire,0x00c)==5 && entity_word(&wire,0x020)==0x42c80000);
        assert(entity_word(&wire,0x0b0)==CODOL_EntityStateEventEpoch(es));
        assert(entity_word(&wire,0x0c0)==120);
        for(i=0;i<4;++i) assert(entity_word(&wire,0x0c4+4*i)==parameters[i]);
        if(type==ET_PLAYER) assert(entity_word(&wire,0x09c)==5);
        if(type==ET_ITEM) assert(entity_word(&wire,0x098)==25);
        if(type==ET_MISSILE) assert(entity_word(&wire,0x0d4)==769 && !entity_word(&wire,0x080));
    }
    {
        /* Native obituary 87 becomes C1 event type 128. The shared entity
         * overlay must accept that translated type after the obituary seed;
         * rejecting it drops the entire killfeed event from the snapshot. */
        /* The composition path reads captured extension fields, so use the
         * harness's registered entity-state storage instead of a stack copy. */
        entityState_t *obituary=&event_entities[1].s;
        codol_entity_state_t feed={0};
        memset(obituary,0,sizeof(*obituary));
        entity_event_seq(obituary,0);
        obituary->number=23;
        obituary->eType=ET_EVENTS+EV_OBITUARY;
        obituary->otherEntityNum=0;
        obituary->attackerEntityNum=1;
        obituary->eventParm=2;
        obituary->index=0;
        feed.type=(unsigned)CODOL_EntityTypeToWire(obituary->eType);
        assert(feed.type==128);
        assert(CODOL_OverlayObituary(&feed,obituary));
        assert(CODOL_OverlayEngineEntity(&feed,obituary,parameters));
        assert(entity_word(&feed,0x080)==0);
        assert(entity_word(&feed,0x084)==1);
        assert(entity_word(&feed,0x0ac)==(700u+2u)%256u);
        assert(entity_word(&feed,0x0e0)==(700u+2u)/256u);
    }
    {
        /* Melee hit/miss: C1's event-52 handler plays the hit on the entity
         * at +80 (the struck one); an unset +80 put every knife hit on
         * player 0 for every client. */
        entityState_t melee; codol_entity_state_t hit={0},before;
        memset(&melee,0,sizeof(melee));
        melee.number=40; melee.eType=ET_EVENTS+EV_MELEE_HIT;
        melee.otherEntityNum=3; melee.eventParm=1; melee.weaponModel=2;
        hit.type=(unsigned)CODOL_EntityTypeToWire(melee.eType);
        assert(hit.type==(unsigned)CODOL_EntityTypeToWire(ET_EVENTS)+52u);
        assert(CODOL_OverlayEngineEventParameter(&hit,1));
        assert(CODOL_OverlayEngineMeleeEvent(&hit,&melee));
        assert(entity_word(&hit,0x080)==3 && entity_word(&hit,0x0ac)==1);
        assert((entity_word(&hit,0x0d4)&0xffffu)==0 && ((entity_word(&hit,0x0e4)>>16)&0xffu)==2);
        memset(&hit,0,sizeof(hit));
        melee.eType=ET_EVENTS+EV_MELEE_MISS; melee.otherEntityNum=ENTITYNUM_WORLD;
        hit.type=(unsigned)CODOL_EntityTypeToWire(melee.eType);
        assert(CODOL_OverlayEngineMeleeEvent(&hit,&melee) && entity_word(&hit,0x080)==ENTITYNUM_WORLD);
        before=hit; melee.otherEntityNum=-1;
        assert(!CODOL_OverlayEngineMeleeEvent(&hit,&melee) && !memcmp(&hit,&before,sizeof(hit)));
        melee.otherEntityNum=3; melee.eType=ET_EVENTS+EV_OBITUARY;
        assert(!CODOL_OverlayEngineMeleeEvent(&hit,&melee) && !memcmp(&hit,&before,sizeof(hit)));
        /* +d6: the attacker's knife row, captured in un2 (C1 0x573cd4). */
        melee.eType=ET_EVENTS+EV_MELEE_HIT; melee.un2=13;
        memset(&hit,0,sizeof(hit)); hit.type=(unsigned)CODOL_EntityTypeToWire(melee.eType);
        assert(CODOL_OverlayEngineMeleeEvent(&hit,&melee) && entity_word(&hit,0x0d4)==(13u<<16));
        before=hit; melee.un2=65536;
        assert(!CODOL_OverlayEngineMeleeEvent(&hit,&melee) && !memcmp(&hit,&before,sizeof(hit)));
    }
    {
        /* Bullet hits: C1's finishPlayerDamage (0x51bf79..0x51c074) writes
         * the shooter +80, surface +90, flag +e0 and victim +88 on event 60,
         * and shooter, surface and the victim's client +9c on 63/64. */
        entityState_t bullet; codol_entity_state_t hit={0},before;
        memset(&bullet,0,sizeof(bullet));
        bullet.number=41; bullet.eType=ET_EVENTS+EV_BULLET_HIT;
        bullet.otherEntityNum=4; bullet.surfType=7; bullet.un1.helicopterStage=1; bullet.un2=9+1;
        hit.type=(unsigned)CODOL_EntityTypeToWire(bullet.eType);
        assert(hit.type==(unsigned)CODOL_EntityTypeToWire(ET_EVENTS)+60u);
        assert(CODOL_OverlayEngineBulletHit(&hit,&bullet));
        assert(entity_word(&hit,0x080)==4 && entity_word(&hit,0x090)==7 &&
               entity_word(&hit,0x0e0)==1 && entity_word(&hit,0x088)==9 &&
               (entity_word(&hit,0x0d4)&0xffffu)==0);
        /* A world impact captures no victim and leaves +88 alone. */
        memset(&hit,0,sizeof(hit)); hit.type=(unsigned)CODOL_EntityTypeToWire(bullet.eType);
        bullet.un2=0; bullet.surfType=3; bullet.un1.helicopterStage=0;
        assert(CODOL_OverlayEngineBulletHit(&hit,&bullet) && entity_word(&hit,0x088)==0 &&
               entity_word(&hit,0x090)==3);
        memset(&hit,0,sizeof(hit));
        bullet.eType=ET_EVENTS+EV_BULLET_HIT_CLIENT_LARGE; bullet.clientNum=6; bullet.surfType=7;
        hit.type=(unsigned)CODOL_EntityTypeToWire(bullet.eType);
        assert(hit.type==(unsigned)CODOL_EntityTypeToWire(ET_EVENTS)+64u);
        assert(CODOL_OverlayEngineBulletHit(&hit,&bullet) && entity_word(&hit,0x09c)==6 &&
               entity_word(&hit,0x080)==4);
        before=hit; bullet.surfType=32;
        assert(!CODOL_OverlayEngineBulletHit(&hit,&bullet) && !memcmp(&hit,&before,sizeof(hit)));
        bullet.surfType=7; bullet.otherEntityNum=-1;
        assert(!CODOL_OverlayEngineBulletHit(&hit,&bullet) && !memcmp(&hit,&before,sizeof(hit)));
        bullet.otherEntityNum=4; bullet.eType=ET_EVENTS+EV_MELEE_HIT;
        assert(!CODOL_OverlayEngineBulletHit(&hit,&bullet) && !memcmp(&hit,&before,sizeof(hit)));
    }
    es->eType=ET_PLAYER; memset(&wire,0,sizeof(wire)); wire.type=ET_PLAYER;
    assert(CODOL_OverlayEngineEntity(&wire,es,parameters));
    saved=wire; valid=*es;
    {
        codol_entity_state_t remote=wire,before;
        entityState_t *player=&event_entities[1].s;
        *player=*es;
        entity_event_seq(player,2);
        player->legsAnim=512; player->torsoAnim=1023|0x400;
        assert(CODOL_OverlayEnginePlayerEntity(&remote,player,8,parameters));
        assert(entity_word(&remote,0xd8)==512 && entity_word(&remote,0xdc)==2047);
        assert(entity_word(&remote,0xd4)==(769u|(1023u<<16)));
        assert(entity_word(&remote,0x09c)==5 && entity_word(&remote,0x054)==0x3f800000);
        assert(entity_word(&remote,0xb0)==CODOL_EntityStateEventEpoch(player));
        {
            uint8_t bytes[2048]; codol_msg_t message;
            codol_delta_context_t context={20000,{0,0,0},0,0};
            codol_entity_state_t held;
            assert(CODOL_ReachEntity(&held,NULL,&remote,&context));
            assert(entity_word(&held,0xd8)==512 && entity_word(&held,0xdc)==2047);
            assert(entity_word(&held,0xd4)==(769u|(1023u<<16)));
            CODOL_MsgWriteInit(&message,bytes,sizeof(bytes));
            assert(CODOL_WriteEntities(&message,NULL,0,&remote,1,&context));
            assert(!message.failed && message.size>0);
        }
        before=remote; entity_event_seq(player,3);
        player->legsAnim=2048;
        assert(!CODOL_OverlayEnginePlayerEntity(&remote,player,8,parameters));
        assert(!memcmp(&remote,&before,sizeof(remote)));
        player->legsAnim=512; player->torsoAnim=-1;
        assert(!CODOL_OverlayEnginePlayerEntity(&remote,player,8,parameters));
        assert(!memcmp(&remote,&before,sizeof(remote)));
        player->torsoAnim=1023|0x400;
        /* Shared composition succeeds locally, then primary mapping fails. */
        assert(!CODOL_OverlayEnginePlayerEntity(&remote,player,1,parameters));
        assert(!memcmp(&remote,&before,sizeof(remote)));
        player->weapon=1;
        assert(!CODOL_OverlayEnginePlayerEntity(&remote,player,8,parameters));
        player->weapon=7; player->clientNum=64;
        assert(!CODOL_OverlayEnginePlayerEntity(&remote,player,8,parameters));
        player->clientNum=5; player->eType=ET_MISSILE;
        assert(!CODOL_OverlayEnginePlayerEntity(&remote,player,8,parameters));
        player->eType=ET_PLAYER;
        assert(!CODOL_OverlayEnginePlayerEntity(&remote,player,8,NULL));
        assert(!CODOL_OverlayEnginePlayerEntity(&remote,player,8,NULL));
        assert(!CODOL_OverlayEnginePlayerEntity(NULL,player,8,parameters));
        assert(!CODOL_OverlayEnginePlayerEntity(&remote,NULL,8,parameters));
        assert(!memcmp(&remote,&before,sizeof(remote)));
        assert(CODOL_OverlayEnginePlayerEntity(&remote,player,7,parameters));
        assert(entity_word(&remote,0xd4)==(769u|(769u<<16)));
        player->weapon=0;
        player->legsAnim=512|0x400; player->torsoAnim=0;
        assert(CODOL_OverlayEnginePlayerEntity(&remote,player,0,parameters));
        assert(!entity_word(&remote,0xd4));
        assert(entity_word(&remote,0xd8)==1536 && !entity_word(&remote,0xdc));
    }
    for(i=0;i<8;++i) {
        *es=valid; entity_event_seq(es,2);
        if(i==0) es->number=ENTITYNUM_WORLD;
        if(i==1) es->lerp.pos.trBase[0]=NAN;
        if(i==2) es->lerp.apos.trType=TR_SINE;
        if(i==3) es->clientNum=-1;
        if(i==4) es->clientNum=64;
        if(i==5) es->eventSequence=256;
        if(i==6) { event=UINT32_MAX; memcpy(&es->events[3],&event,4); }
        if(i==7) parameters[3]=2048;
        assert(!CODOL_OverlayEngineEntity(&wire,es,parameters));
        assert(!memcmp(&wire,&saved,sizeof(wire)));
        parameters[3]=2047;
    }
    *es=valid; es->eType=ET_MISSILE;
    assert(!CODOL_OverlayEngineEntity(&wire,es,parameters));
    es->eType=ET_MOVER;
    assert(!CODOL_OverlayEngineEntity(&wire,es,parameters));
    *es=valid;
    assert(!CODOL_OverlayEngineEntity(NULL,es,parameters));
    assert(!CODOL_OverlayEngineEntity(&wire,NULL,parameters));
    assert(!CODOL_OverlayEngineEntity(&wire,es,NULL));
    
    assert(!memcmp(&wire,&saved,sizeof(wire)));
    CODOL_ResetWeaponMap();
}
static void engine_trajectory_test(void)
{
    entityState_t es = {0};
    codol_entity_state_t state = {0}, before;
    float value; uint32_t word;
    es.number = 23; es.lerp.pos.trType = TR_LINEAR; es.lerp.pos.trTime = 12345;
    es.lerp.pos.trBase[0] = 150.25f; es.lerp.pos.trDelta[0] = -17.5f;
    es.lerp.apos.trType = TR_INTERPOLATE; es.lerp.apos.trBase[1] = 270.0f;
    state.type = 1;
    assert(CODOL_OverlayEngineTrajectories(&state, &es));
    assert(state.number == 23 && state.type == 1 && state.field[0] == 1);
    assert(entity_word(&state, 0xc) == 2 && entity_word(&state, 0x10) == 12345);
    word = entity_word(&state, 0x18); memcpy(&value, &word, 4); assert(value == 150.25f);
    word = entity_word(&state, 0x24); memcpy(&value, &word, 4); assert(value == -17.5f);
    word = entity_word(&state, 0x40); memcpy(&value, &word, 4); assert(value == 270.0f);
    before = state; es.lerp.apos.trBase[2] = NAN;
    assert(!CODOL_OverlayEngineTrajectories(&state, &es) && !memcmp(&state, &before, sizeof(state)));
    es.lerp.apos.trBase[2] = 0; es.lerp.pos.trType = (trType_t)6;
    assert(CODOL_OverlayEngineTrajectories(&state, &es) && entity_word(&state, 0xc)==6);
    {
        unsigned type, mode;
        for (type = 0; type < 22; ++type) for (mode = 0; mode < 13; ++mode) {
            state.type = type;
            es.lerp.pos.trType = es.lerp.apos.trType = (trType_t)mode;
            es.lerp.pos.trDuration = es.lerp.apos.trDuration = 250;
            assert(CODOL_OverlayEngineTrajectories(&state, &es));
            assert(entity_word(&state, 0xc) == mode && entity_word(&state, 0x30) == mode);
            assert(entity_word(&state, 0x14) == 250 && entity_word(&state, 0x38) == 250);
        }
        before = state;
        es.lerp.pos.trType = TR_SINE; es.lerp.pos.trDuration = 0;
        assert(!CODOL_OverlayEngineTrajectories(&state, &es) && !memcmp(&state, &before, sizeof(state)));
        es.lerp.pos.trDuration = 250; es.lerp.apos.trType = TR_SINE; es.lerp.apos.trDuration = 0;
        assert(!CODOL_OverlayEngineTrajectories(&state, &es) && !memcmp(&state, &before, sizeof(state)));
        es.lerp.apos.trType = TR_GRAVITY; es.lerp.apos.trDuration = -1;
        assert(!CODOL_OverlayEngineTrajectories(&state, &es) && !memcmp(&state, &before, sizeof(state)));
    }
    es.lerp.pos.trType = TR_STATIONARY; es.number = ENTITYNUM_WORLD;
    assert(!CODOL_OverlayEngineTrajectories(&state, &es) && !memcmp(&state, &before, sizeof(state)));
}

static void engine_physics_trajectory_test(void)
{
    /* The event epoch is keyed off the entityState's address, so the subject
     * lives in the base this harness publishes. */
    entityState_t *ep=&event_entities[2].s;
#define engine (*ep)
    memset(ep,0,sizeof(*ep));
    codol_entity_state_t wire={0},held,saved;
    codol_delta_context_t context={20000,{0,0,0},0,0};
    codol_msg_t message;
    uint32_t parameters[4]={0};
    uint8_t bytes[4096];
    unsigned axis;
    engine.number=27; engine.eType=ET_SCRIPTMOVER;
    engine.lerp.pos.trType=engine.lerp.apos.trType=TR_PHYSICS;
    engine.lerp.pos.trTime=engine.lerp.apos.trTime=19000;
    engine.lerp.pos.trDuration=0x7fffffff; /* Native launch lifetime. */
    for(axis=0;axis<3;++axis) {
        engine.lerp.pos.trBase[axis]=100.0f+axis;
        engine.lerp.pos.trDelta[axis]=-30.0f+axis;
        engine.lerp.apos.trBase[axis]=45.0f*axis;
        engine.lerp.apos.trDelta[axis]=15.0f+axis;
    }
    wire.type=CODOL_EntityTypeToWire(engine.eType);
    assert(CODOL_OverlayEngineEntity(&wire,&engine,parameters));
    assert(entity_word(&wire,0xc)==9 && entity_word(&wire,0x30)==9);
    assert(entity_word(&wire,0x14)==0x7fffffff);
    for(axis=0;axis<3;++axis) {
        uint32_t word;
        memcpy(&word,&engine.lerp.pos.trDelta[axis],4);
        assert(entity_word(&wire,0x24+4*axis)==word);
        memcpy(&word,&engine.lerp.apos.trDelta[axis],4);
        assert(entity_word(&wire,0x48+4*axis)==word);
    }
    assert(CODOL_ReachEntity(&held,NULL,&wire,&context));
    assert(entity_word(&held,0xc)==9 && entity_word(&held,0x30)==9);
    assert(entity_word(&held,0x14)==0x7fffffff);
    CODOL_MsgWriteInit(&message,bytes,sizeof(bytes));
    assert(CODOL_WriteEntities(&message,NULL,0,&wire,1,&context));
    saved=wire;
    engine.lerp.apos.trDelta[2]=NAN;
    assert(!CODOL_OverlayEngineEntity(&wire,&engine,parameters));
    assert(!memcmp(&wire,&saved,sizeof(wire)));
    engine.lerp.apos.trDelta[2]=17;
    engine.lerp.apos.trType=(trType_t)7;
    assert(!CODOL_OverlayEngineEntity(&wire,&engine,parameters));
    assert(!memcmp(&wire,&saved,sizeof(wire)));
    puts("PASS: native physics launch trajectories translate to CoDOL rigid-body mode and encode");
}
#undef engine

static void engine_missile_test(void)
{
    entityState_t engine = {0};
    codol_entity_state_t wire = {0}, saved;
    codol_delta_context_t context = {20000, {0, 0, 0}, 0, 0};
    codol_msg_t message;
    uint8_t bytes[4096];
    unsigned i;
    CODOL_ResetWeaponMap(); assert(CODOL_MapWeapon(769, 7));
    engine.number = 23; engine.eType = ET_MISSILE; engine.weapon = 7;
    engine.lerp.pos.trType = TR_GRAVITY; engine.lerp.pos.trTime = 19000;
    engine.lerp.pos.trBase[2] = 100; engine.lerp.pos.trDelta[0] = 300;
    engine.lerp.pos.trDelta[2] = 120;
    wire.type = 4;
    for (i = 0; i < CODOL_ENTITY_FIELDS; ++i)
        if (CODOL_EntityField(4, i)->offset == 0x80) wire.field[i] = 33;
    /* es+0x80 is the missile's owner entity (C1 rocket spawn 0x5310ce, read
     * by the compass update; measured live 2026-09-28). An out-of-range
     * otherEntityNum leaves the seeded word alone. */
    engine.otherEntityNum = ENTITYNUM_NONE;
    assert(CODOL_OverlayEngineMissile(&wire, &engine));
    assert(entity_word(&wire, 0x80) == 33);
    engine.otherEntityNum = 5;
    assert(CODOL_OverlayEngineMissile(&wire, &engine));
    assert(wire.number == 23 && entity_word(&wire, 0xd4) == 769);
    assert(entity_word(&wire, 0x80) == 5);
    assert(entity_word(&wire, 0x54) == 0x3f800000 && entity_word(&wire, 0xc) == 5);
    CODOL_MsgWriteInit(&message, bytes, sizeof(bytes));
    assert(CODOL_WriteEntities(&message, NULL, 0, &wire, 1, &context));
    saved = wire;
    engine.weapon = 8;
    assert(!CODOL_OverlayEngineMissile(&wire, &engine) && !memcmp(&wire, &saved, sizeof(wire)));
    engine.weapon = 7; engine.lerp.pos.trDelta[2] = NAN;
    assert(!CODOL_OverlayEngineMissile(&wire, &engine) && !memcmp(&wire, &saved, sizeof(wire)));
    engine.lerp.pos.trDelta[2] = 120; engine.eType = ET_PLAYER;
    assert(!CODOL_OverlayEngineMissile(&wire, &engine) && !memcmp(&wire, &saved, sizeof(wire)));
    CODOL_ResetWeaponMap();
}

static int hud_test_resolve(void *context,const hudelem_t *source,codol_hud_bindings_t *out)
{
    int *calls=context;
    ++*calls;
    if(source->text==999) return 0;
    *out=(codol_hud_bindings_t){(unsigned)source->label+10,(unsigned)source->text+20,
        (unsigned)source->materialIndex+30,7,0x80};
    return 1;
}
int main(void)
{
    {
        codol_delta_context_t context={123,{7,8,9},1,42},saved;
        float center[3]={0.5f,-0.5f,-1.5f};
        const char *invalid[]={"1 2","1 2 3 4","1,2 3","nan 2 3","1 inf 3","1 2 1e99","2147483648 0 0"};
        unsigned i;
        assert(CODOL_SetDeltaPositionBase(&context,center));
        assert(context.position_base[0]==1 && context.position_base[1]==0 && context.position_base[2]==-1);
        assert(context.server_time==123 && context.clamp_positions==1 && context.clamped==42);
        saved=context; center[2]=INFINITY;
        assert(!CODOL_SetDeltaPositionBase(&context,center) && !memcmp(&context,&saved,sizeof(context)));
        assert(!CODOL_SetDeltaPositionBase(NULL,center) && !CODOL_SetDeltaPositionBase(&context,NULL));
        for(i=0;i<sizeof(invalid)/sizeof(invalid[0]);++i) {
            assert(CODOL_SetConfigstring(CODOL_ServerConfigstrings(),16,invalid[i]));
            assert(!CODOL_ApplyServerPositionBase(&context) && !memcmp(&context,&saved,sizeof(context)));
        }
        assert(CODOL_SetConfigstring(CODOL_ServerConfigstrings(),16,"  1.5 -2.5 100000.25  "));
        assert(CODOL_ApplyServerPositionBase(&context));
        assert(context.position_base[0]==2 && context.position_base[1]==-2 && context.position_base[2]==100000);
        assert(CODOL_SetConfigstring(CODOL_ServerConfigstrings(),16,""));
        assert(CODOL_ApplyServerPositionBase(&context));
        assert(!context.position_base[0] && !context.position_base[1] && !context.position_base[2]);
        CODOL_ResetServerConfigstrings();
        {
            const char *constants[]={"16","100 200 300"};
            assert(CODOL_SetServerInheritedConfigstrings("mp",1,constants));
            assert(CODOL_ApplyServerPositionBase(&context));
            assert(context.position_base[0]==100 && context.position_base[1]==200 && context.position_base[2]==300);
            assert(CODOL_SetConfigstring(CODOL_ServerConfigstrings(),16,""));
            assert(CODOL_ApplyServerPositionBase(&context));
            assert(!context.position_base[0] && !context.position_base[1] && !context.position_base[2]);
            CODOL_ResetServerConfigstrings();
        }
    }
    {
        hudelem_t engine={0}; codol_hud_element_t hud,saved; unsigned i,j;
        {
            unsigned translated=99;
            /* The wire keeps the seven engine HUD flag bits verbatim:
             * the three alignment/anchor bits plus the distance,
             * rotating-edge and offscreen-only bits. */
            for(i=0;i<0x80;++i) assert(CODOL_TranslateEngineHudFlags(i,&translated) && translated==i);
            for(i=7;i<32;++i) {
                translated=99;
                assert(!CODOL_TranslateEngineHudFlags(1u<<i,&translated) && translated==99);
            }
            assert(!CODOL_TranslateEngineHudFlags(0,NULL));
        }
        memset(&hud,0x5a,sizeof(hud));
        engine.x=1.5f; engine.y=-2; engine.z=4.5f; engine.fontScale=1.25f;
        engine.width=120; engine.height=30; engine.fromWidth=10; engine.fromHeight=20;
        engine.fadeStartTime=700; engine.fadeTime=300; engine.moveStartTime=800; engine.moveTime=200;
        engine.fromX=0.5f; engine.fromY=-2; engine.alignOrg=3; engine.alignScreen=0x55;
        engine.duration=900; engine.fxDecayStartTime=1000; engine.fxDecayDuration=400;
        { uint32_t color=0x12345678; memcpy(&engine.color,&color,4); }
        assert(CODOL_OverlayEngineHudPresentation(&hud,&engine));
        /* Independent wire indices from the C1 HUD field table. */
        assert(hud.field[0]==0x12345678 && hud.field[1]==0xc0000000 && hud.field[2]==0x3fc00000 && hud.field[8]==0x40900000);
        assert(hud.field[5]==30 && hud.field[6]==120 && hud.field[10]==700 && hud.field[13]==300);
        assert(hud.field[16]==0x3fa00000 && hud.field[19]==0x3fa00000 && !hud.field[17] && !hud.field[18]);
        assert(hud.field[35]==800 && hud.field[36]==200 && hud.field[37]==0x3f000000 && hud.field[41]==900);
        assert(hud.field[31]==1000 && hud.field[32]==400);
        assert(hud.field[3]==0x5a5a5a5a && hud.field[4]==0x5a5a5a5a && hud.field[7]==0x5a5a5a5a);
        assert(hud.field[14]==0x5a5a5a5a && hud.field[20]==0x5a5a5a5a && hud.field[22]==0x5a5a5a5a && hud.field[29]==0x5a5a5a5a && hud.field[33]==0x5a5a5a5a);
        saved=hud; engine.sort=NAN;
        assert(!CODOL_OverlayEngineHudPresentation(&hud,&engine) && !memcmp(&hud,&saved,sizeof(hud)));
        for(i=0;i<CODOL_HUD_FIELDS;++i) {
            assert(CODOL_HudFieldOffset(i)<0xa8 && !(CODOL_HudFieldOffset(i)&3));
            for(j=0;j<i;++j) assert(CODOL_HudFieldOffset(i)!=CODOL_HudFieldOffset(j));
        }
        {
            static const int expected[]={0,1,2,3,-1,-1,4,5,6,8,9,11,12,13,7,10};
            codol_hud_bindings_t bindings={11,22,33,4,0x80};
            engine.sort=0; engine.targetEntNum=ENTITYNUM_NONE; engine.font=3;
            engine.text=444; engine.label=555; engine.materialIndex=66; engine.flags=0x20;
            for(i=1;i<HE_TYPE_COUNT;++i) {
                engine.type=(he_type_t)i; saved=hud;
                if(expected[i]<0) assert(!CODOL_BuildEngineHudElement(&hud,&engine,&bindings) && !memcmp(&hud,&saved,sizeof(hud)));
                else {
                    assert(CODOL_BuildEngineHudElement(&hud,&engine,&bindings));
                    assert(hud.field[3]==(unsigned)expected[i] && hud.field[7]==2047 && hud.field[20]==3);
                    assert(hud.field[4]==33 && hud.field[22]==22 && hud.field[33]==11 && hud.field[29]==4 && hud.field[14]==0x80);
                }
            }
            saved=hud; bindings.material=256;
            assert(!CODOL_BuildEngineHudElement(&hud,&engine,&bindings) && !memcmp(&hud,&saved,sizeof(hud)));
            bindings.material=33; engine.offscreenMaterialIdx=1;
            assert(!CODOL_BuildEngineHudElement(&hud,&engine,&bindings) && !memcmp(&hud,&saved,sizeof(hud)));
        }
        {
            hudElemState_t source={0}; codol_hud_state_t collected,before; int calls=0;
            memset(&collected,0x5a,sizeof(collected));
            source.archival[0].type=HE_TYPE_TEXT; source.archival[0].text=1;
            source.current[0].type=HE_TYPE_MATERIAL; source.current[0].materialIndex=2;
            source.current[2].type=HE_TYPE_VALUE; /* Entries after FREE are outside the packed span. */
            assert(CODOL_CollectEngineHud(&collected,&source,hud_test_resolve,&calls) && calls==2);
            assert(collected.count[0]==1 && collected.count[1]==1);
            assert(collected.elements[0][0].field[3]==1 && collected.elements[0][0].field[22]==21);
            assert(collected.elements[1][0].field[3]==4 && collected.elements[1][0].field[4]==32);
            assert(!collected.elements[1][1].field[3]); before=collected;
            source.current[0].text=999;
            assert(!CODOL_CollectEngineHud(&collected,&source,hud_test_resolve,&calls) && !memcmp(&collected,&before,sizeof(before)));
            source.current[0].text=0; source.current[0].type=HE_TYPE_MAPNAME;
            assert(!CODOL_CollectEngineHud(&collected,&source,hud_test_resolve,&calls) && !memcmp(&collected,&before,sizeof(before)));
            memset(&source,0,sizeof(source));
            for(i=0;i<MAX_HUDELEMENTS;++i) source.current[i].type=HE_TYPE_VALUE;
            assert(CODOL_CollectEngineHud(&collected,&source,hud_test_resolve,&calls) && collected.count[1]==31);
            memset(&source,0,sizeof(source));
            assert(CODOL_CollectEngineHud(&collected,&source,NULL,NULL) && !collected.count[0] && !collected.count[1]);
        }
    }
    {
        char path[256],saved[256]; unsigned i;
        const char *invalid[]={"","../common_mp","dir/map","dir\\map","map.ff","map;quit"};
        assert(CODOL_ZoneFilePath("D:/CoD","chinese",NULL,"mp_killhouse_sh",path,sizeof(path)));
        assert(!strcmp(path,"D:/CoD/client_shipRetail/chinese/mp_killhouse_sh.ff"));
        assert(CODOL_ZoneFilePath(NULL,NULL,"/custom zones","mp_killhouse_sh_load",path,sizeof(path)));
        assert(!strcmp(path,"/custom zones/mp_killhouse_sh_load.ff"));
        memcpy(saved,path,sizeof(path));
        for(i=0;i<sizeof(invalid)/sizeof(*invalid);++i) {
            assert(!CODOL_ZoneFilePath("/base","chinese",NULL,invalid[i],path,sizeof(path)));
            assert(!memcmp(path,saved,sizeof(path)));
        }
        assert(!CODOL_ZoneFilePath("/base","../chinese",NULL,"map",path,sizeof(path)));
        assert(!CODOL_ZoneFilePath("/base","chinese",NULL,"map",path,4));
        assert(!memcmp(path,saved,sizeof(path)));
    }
    engine_missile_test();
    {
        byte buffer[4096], expected[4096];
        msg_t msg;
        codol_msg_t wire;
        codol_player_fields_t player = {{0}};
        codol_snapshot_state_t state = {0};
        codol_delta_context_t context = {20000, {0, 0, 0}, 0, 0}, copy;
        int prefix;
        state.sequence = 10; state.player = &player; player.field[0] = 20000;
        MSG_Init(&msg, buffer, sizeof(buffer));
        MSG_WriteLong(&msg, 123); MSG_WriteByte(&msg, 1); MSG_WriteLong(&msg, 7);
        MSG_WriteData(&msg, "d 1280 Player", sizeof("d 1280 Player")); prefix = msg.cursize;
        memcpy(expected, buffer, prefix);
        CODOL_MsgWriteInit(&wire, expected+prefix, sizeof(expected)-prefix);
        copy = context;
        assert(CODOL_WriteSnapshot(&wire, &state, NULL, NULL, NULL, 0, 8, 1, &copy));
        assert(CODOL_WriteServerSnapshot(&msg, &state, NULL, NULL, NULL, 0, 8, 1, &context));
        assert(msg.cursize == prefix+(int)wire.size && msg.bit == msg.cursize*8);
        assert(!memcmp(buffer, expected, msg.cursize) && buffer[msg.cursize-1] == 5);
        MSG_Init(&msg, buffer, 6); MSG_WriteLong(&msg, 123); prefix = msg.cursize;
        copy = context;
        assert(!CODOL_WriteServerSnapshot(&msg, &state, NULL, NULL, NULL, 0, 8, 1, &context));
        assert(msg.overflowed && msg.cursize == prefix && !memcmp(&context, &copy, sizeof(copy)));
        MSG_Init(&msg, buffer, sizeof(buffer)); state.sequence = 0;
        assert(!CODOL_WriteServerSnapshot(&msg, &state, NULL, NULL, NULL, 0, 8, 1, &context));
        assert(msg.overflowed && !msg.cursize);
        {
            codol_history_t *history = CODOL_CreateHistory();
            assert(history); state.sequence = 10;
            MSG_Init(&msg, buffer, sizeof(buffer)); MSG_WriteLong(&msg, 123);
            assert(CODOL_PrepareServerSnapshot(&msg, history, &state, 9, NULL, NULL, 0, 0, 1, &context));
            assert(buffer[9] == 0 && buffer[10] == 8); /* missing ACK produces full baseline */
            assert(!CODOL_FindHistoryBase(history, 10, 11));
            assert(CODOL_FinishHistory(history, 10, 1));
            state.sequence = 11;
            MSG_Init(&msg, buffer, sizeof(buffer)); MSG_WriteLong(&msg, 123);
            assert(CODOL_PrepareServerSnapshot(&msg, history, &state, 10, NULL, NULL, 0, 0, 1, &context));
            assert(buffer[9] == 1 && buffer[10] == 0);
            assert(CODOL_FinishHistory(history, 11, 0));
            assert(!CODOL_FindHistoryBase(history, 11, 12));
            MSG_Init(&msg, buffer, 6); MSG_WriteLong(&msg, 123);
            assert(!CODOL_PrepareServerSnapshot(&msg, history, &state, 10, NULL, NULL, 0, 0, 1, &context));
            assert(!CODOL_FinishHistory(history, 11, 1));
            assert(CODOL_FindHistoryBase(history, 10, 11));
            CODOL_DestroyHistory(history);
        }
        {
            codol_history_t *a = CODOL_ClientSnapshotHistory(0);
            codol_history_t *b = CODOL_ClientSnapshotHistory(1);
            assert(a && b && a != b && CODOL_ClientSnapshotHistory(0) == a);
            assert(!CODOL_ClientSnapshotHistory(MAX_CLIENTS));
            state.sequence = 1;
            assert(CODOL_CommitHistory(a, &state));
            assert(CODOL_FindHistoryBase(a, 1, 2) && !CODOL_FindHistoryBase(b, 1, 2));
            assert(CODOL_PrepareHistory(b, &state, 0, 1, &context));
            CODOL_ResetClientSnapshotHistory(0);
            a = CODOL_ClientSnapshotHistory(0);
            assert(a && !CODOL_FindHistoryBase(a, 1, 2));
            assert(CODOL_FinishHistory(b, 1, 1));
            CODOL_ResetSnapshotHistories();
            a = CODOL_ClientSnapshotHistory(0); b = CODOL_ClientSnapshotHistory(1);
            assert(a && b && !CODOL_FindHistoryBase(a, 1, 2) && !CODOL_FindHistoryBase(b, 1, 2));
            assert(CODOL_PrepareHistory(a, &state, 0, 1, &context));
            CODOL_ResetSnapshotHistories();
            CODOL_ResetSnapshotHistories();
        }
        {
            unsigned scenario;
            for (scenario = 0; scenario < 9; ++scenario) {
                codol_history_t *history;
                msg_t other;
                int committed;
                state.sequence = 1;
                MSG_Init(&msg, buffer, sizeof(buffer)); MSG_WriteLong(&msg, 123);
                assert(CODOL_PrepareClientSnapshot(0, &msg, &state, 0, NULL, NULL, 0, 8, 1, &context));
                history = CODOL_ClientSnapshotHistory(0);
                assert(CODOL_ClientSnapshotPrepared(0, &msg, 1));
                assert(!CODOL_FindHistoryBase(history, 1, 2));
                other = msg;
                if (scenario == 2) ++msg.cursize;
                if (scenario == 3) msg.overflowed = qtrue;
                if (scenario == 5) CODOL_DiscardClientSnapshot(0);
                if (scenario == 6) msg.data[0] ^= 1;
                if (scenario == 7) msg.data[msg.cursize - 1] ^= 1;
                if (scenario == 8) msg.splitData = msg.data;
                committed = CODOL_FinishClientSnapshot(0, scenario == 4 ? &other : &msg, 1, scenario != 1);
                assert(committed == (scenario == 0));
                assert(!!CODOL_FindHistoryBase(history, 1, 2) == (scenario == 0));
                assert(!CODOL_ClientSnapshotPrepared(0, &msg, 1));
                CODOL_ResetSnapshotHistories();
            }
        }
    }
    {
        unsigned i;
        assert(CODOL_EventToWire(EV_NONE) == 0);
        assert(CODOL_EventToWire(EV_FIRE_WEAPON) == 30);
        assert(CODOL_EventToWire(EV_OBITUARY) == 107);
        assert(CODOL_EventToWire(EV_JUMP) == 120);
        assert(CODOL_EventToWire(EV_STOPSOUNDS) == 5);
        assert(CODOL_EventToWire(256) == -1);
        for (i = 0; i <= ET_VEHICLE_CORPSE; ++i) assert(CODOL_EntityTypeToWire(i) == (int)i);
        assert(CODOL_EntityTypeToWire(ET_EVENTS + EV_FIRE_WEAPON) == 51);
        assert(CODOL_EntityTypeToWire(ET_EVENTS + EV_OBITUARY) == 128);
        assert(CODOL_EntityTypeToWire(ET_EVENTS + EV_STOPSOUNDS) == 26);
        assert(CODOL_EntityTypeToWire(ET_MOVER) == -1);
        assert(CODOL_EntityTypeToWire(256) == -1);
    }
    {
        codol_configstrings_t bank = {0};
        unsigned i; char name[64];
        assert(CODOL_RegisterModelName(&bank, "") == 0 && !bank.count);
        assert(CODOL_RegisterModelName(&bank, "body_model") == 1);
        assert(CODOL_RegisterModelName(&bank, "body_model") == 1 && bank.count == 1);
        assert(CODOL_RegisterTagName(&bank, "tag_head") == 1);
        assert(!strcmp(CODOL_GetConfigstring(&bank, 1316), "body_model"));
        assert(!strcmp(CODOL_GetConfigstring(&bank, 5300), "tag_head"));
        assert(!CODOL_GetConfigstring(&bank, 1315) && !CODOL_GetConfigstring(&bank, 5299));
        assert(CODOL_RegisterModelName(&bank, "bad\nname") == -1);
        for (i = 2; i < 2048; ++i) {
            snprintf(name, sizeof(name), "model_%u", i);
            assert(CODOL_RegisterModelName(&bank, name) == (int)i);
        }
        assert(CODOL_RegisterModelName(&bank, "overflow") == -1);
        assert(CODOL_RegisterModelName(&bank, "body_model") == 1);
        assert(CODOL_SetConfigstring(&bank, 5363, "weapon_one"));
        for (i = 2; i < 64; ++i) {
            snprintf(name, sizeof(name), "tag_%u", i);
            assert(CODOL_RegisterTagName(&bank, name) == (int)i);
        }
        assert(CODOL_RegisterTagName(&bank, "overflow") == -1);
        assert(!strcmp(CODOL_GetConfigstring(&bank, 5363), "weapon_one"));
        CODOL_ClearConfigstrings(&bank);
        assert(CODOL_RegisterModelName(&bank, "new_map_body") == 1);
        CODOL_ClearConfigstrings(&bank);
    }
    {
        char token[64];
        CODOL_PlayerNameToken(token, "  ^2Alpha  Player\";\\//Two ");
        assert(!strcmp(token, "^2Alpha_Player_Two"));
        CODOL_PlayerNameToken(token, NULL); assert(!*token);
        CODOL_PlayerNameToken(token, "   "); assert(!strcmp(token, "Player"));
        CODOL_PlayerNameToken(token, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789XYZ");
        assert(strlen(token) == 63 && token[62] == 'X');
    }
    {
        codol_configstrings_t names = {0};
        const char *list[3] = {"Alpha Player", NULL, "^2Bravo"};
        assert(CODOL_SetConfigstring(&names, 1300, "local-info"));
        assert(CODOL_SetPlayerNames(&names, 3, list));
        assert(!strcmp(CODOL_GetConfigstring(&names, 1280), "Alpha Player"));
        assert(!strcmp(CODOL_GetConfigstring(&names, 1281), ""));
        assert(!strcmp(CODOL_GetConfigstring(&names, 1282), "^2Bravo"));
        assert(!strcmp(CODOL_GetConfigstring(&names, 1299), ""));
        assert(!strcmp(CODOL_GetConfigstring(&names, 1300), "local-info"));
        assert(names.count == 21);
        assert(!CODOL_SetPlayerNames(&names, 21, list));
        assert(!strcmp(CODOL_GetConfigstring(&names, 1280), "Alpha Player"));
        assert(CODOL_SetPlayerNames(&names, 0, NULL));
        assert(!strcmp(CODOL_GetConfigstring(&names, 1280), ""));
        assert(!strcmp(CODOL_GetConfigstring(&names, 1300), "local-info"));
        CODOL_ClearConfigstrings(&names);
    }
    netchan_test(); crypto_test(); usercmd_bridge_test(); usermove_packet_test(); gamestate_bridge_test();
    engine_movement_test();
    engine_player_mode_test();
    engine_weapon_health_test();
    engine_inventory_test();
    engine_ammo_test();
    engine_client_test();
    engine_trajectory_test();
    engine_physics_trajectory_test();
    engine_entity_events_test();
    engine_entity_composition_test();
    engine_player_events_test();
    engine_player_flags_test();
    engine_viewhands_wire_test();
    engine_player_composition_test();
    engine_aim_test();
    puts("PASS: native netchan, loss handling, reassembly, bdDTLS DATA, usercmd, gamestate and movement bridges");
    return 0;
}
