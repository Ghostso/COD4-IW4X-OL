/* Ability metadata owned by the retained clientState snapshot ring. */
#ifdef CODOL_SERVER
#include "codol_clientstate_ext.h"
#include "server.h"
#include <string.h>
#include <math.h>

#define CODOL_CS_EXT_SLOTS \
    (sizeof(((serverStatic_t *)0)->snapshotClients) / sizeof(clientState_t))
#pragma pack(push, 8)
typedef struct {
    codol_client_abilities_t abilities;
    codol_client_appearance_t appearance;
    unsigned char appearance_known;
    int sequence;
    int client;
    unsigned char captured;
} codol_cs_abilities_t;
#pragma pack(pop)
static codol_cs_abilities_t snapshots[CODOL_CS_EXT_SLOTS];
/* Session clientState data: preserve across ClientSpawn's savedSess restore,
 * replace at client-info publication, clear on connection reuse/map reset.
 * It is deliberately separate from the spectator-copyable playerState. */
static codol_client_abilities_t published[MAX_CLIENTS];
static codol_client_appearance_t published_appearance[MAX_CLIENTS];
static unsigned char published_appearance_known[MAX_CLIENTS];
#define CODOL_CS_EXT_ARCHIVE \
    (sizeof(((serverStatic_t *)0)->cachedSnapshotClients) / sizeof(cachedClient_t))
static codol_cs_abilities_t archives[CODOL_CS_EXT_ARCHIVE];

static codol_cs_abilities_t *archive_slot(const clientState_t *cs)
{
    uintptr_t address = (uintptr_t)cs;
    uintptr_t base = (uintptr_t)&svs.cachedSnapshotClients[0].cs;
    size_t slot;
    if (!cs || address < base || (address-base) % sizeof(cachedClient_t)) return NULL;
    slot = (address-base) / sizeof(cachedClient_t);
    return slot < CODOL_CS_EXT_ARCHIVE ? &archives[slot] : NULL;
}

void CODOL_ClearCapturedClientAbilities(void)
{
    memset(snapshots, 0, sizeof(snapshots));
    memset(published, 0, sizeof(published));
    memset(published_appearance,0,sizeof(published_appearance));
    memset(published_appearance_known,0,sizeof(published_appearance_known));
    CODOL_ClearArchivedClientAbilities();
}

void CODOL_ClearPublishedClientAbilities(unsigned client)
{
    if (client < MAX_CLIENTS) memset(&published[client], 0, sizeof(published[client]));
    if (client < MAX_CLIENTS) {
        memset(&published_appearance[client],0,sizeof(published_appearance[client]));
        published_appearance_known[client]=0;
    }
}

int CODOL_PublishClientAppearance(unsigned client,const codol_client_appearance_t *appearance)
{
    codol_client_state_t validation={0};
    if(client>=MAX_CLIENTS || !CODOL_OverlayClientAppearance(&validation,appearance)) return 0;
    published_appearance[client]=*appearance;
    published_appearance_known[client]=1;
    return 1;
}

void CODOL_PublishClientAbilities(unsigned client, const playerState_t *ps)
{
    codol_ps_ext_t state;
    if (client >= MAX_CLIENTS || !ps) return;
    CODOL_PlayerStateExtFetch(&state, ps);
    if (state.abilities_known) published[client] = state.abilities;
    else memset(&published[client],0,sizeof(published[client]));
}

int CODOL_CapturePublishedClientAbilities(int sequence, unsigned client)
{
    codol_ps_ext_t state = {0};
    if (client >= MAX_CLIENTS) return 0;
    state.abilities = published[client];
    state.abilities_known = 1;
    if(!CODOL_CaptureClientAbilities(sequence, &state)) return 0;
    snapshots[sequence % svs.numSnapshotClients].appearance=published_appearance[client];
    snapshots[sequence % svs.numSnapshotClients].appearance_known=published_appearance_known[client];
    return 1;
}

void CODOL_ClearArchivedClientAbilities(void)
{
    memset(archives, 0, sizeof(archives));
}

void CODOL_WriteArchivedClientAbilities(msg_t *msg, int client, const clientState_t *cache)
{
    codol_cs_abilities_t value = {0}, *slot = cache ? archive_slot(cache) : NULL;
    unsigned i;
    if (!msg) return;
    if (client < 0 || client >= MAX_CLIENTS || (cache && !slot)) {
        msg->overflowed = 1; return;
    }
    value.abilities = published[client];
    value.appearance=published_appearance[client];
    value.appearance_known=published_appearance_known[client];
    for (i=0; i<CODOL_ABILITY_VALUES; ++i)
        if (!isfinite(value.abilities.values[i])) { msg->overflowed = 1; return; }
    for (i=0; i<CODOL_ABILITY_MASK_WORDS; ++i)
        MSG_WriteBits(msg, value.abilities.masks[i], 32);
    for (i=0; i<CODOL_ABILITY_VALUES; ++i) {
        uint32_t word;
        memcpy(&word, &value.abilities.values[i], sizeof(word));
        MSG_WriteBits(msg, word, 32);
    }
    value.client = client;
    MSG_WriteBits(msg,value.appearance_known,1);
    if(value.appearance_known) {
        MSG_WriteBits(msg,value.appearance.model,11);
        for(i=0;i<CODOL_CLIENT_ATTACHMENTS;++i) {
            MSG_WriteBits(msg,value.appearance.attach_model[i],11);
            MSG_WriteBits(msg,value.appearance.attach_tag[i],6);
        }
    }
    value.captured = !msg->overflowed;
    if (slot) *slot = value;
}

void CODOL_ReadArchivedClientAbilities(msg_t *msg, const clientState_t *cache)
{
    codol_cs_abilities_t value = {0}, *slot = archive_slot(cache);
    unsigned i;
    if (!msg) return;
    if (!slot) { msg->overflowed = 1; return; }
    slot->captured=0;
    for (i=0; i<CODOL_ABILITY_MASK_WORDS; ++i)
        value.abilities.masks[i] = (uint32_t)MSG_ReadBits(msg, 32);
    for (i=0; i<CODOL_ABILITY_VALUES; ++i) {
        uint32_t word = (uint32_t)MSG_ReadBits(msg, 32);
        memcpy(&value.abilities.values[i], &word, sizeof(word));
        if (!isfinite(value.abilities.values[i])) msg->overflowed = 1;
    }
    {
        int known=MSG_ReadBit(msg);
        codol_client_state_t validation={0};
        if(known<0) { msg->overflowed=1; return; }
        value.appearance_known=(unsigned char)known;
        if(known) {
            value.appearance.model=(unsigned)MSG_ReadBits(msg,11);
            for(i=0;i<CODOL_CLIENT_ATTACHMENTS;++i) {
                value.appearance.attach_model[i]=(unsigned)MSG_ReadBits(msg,11);
                value.appearance.attach_tag[i]=(unsigned)MSG_ReadBits(msg,6);
            }
            if(!CODOL_OverlayClientAppearance(&validation,&value.appearance)) msg->overflowed=1;
        }
    }
    value.client = cache->clientIndex;
    value.captured = !msg->overflowed;
    *slot = value;
}

int CODOL_CaptureArchivedClientAbilities(int sequence, const clientState_t *cache)
{
    const codol_cs_abilities_t *slot = archive_slot(cache);
    codol_ps_ext_t state = {0};
    if (!slot || !slot->captured || slot->client != cache->clientIndex) return 0;
    state.abilities = slot->abilities;
    state.abilities_known = 1;
    if(!CODOL_CaptureClientAbilities(sequence, &state)) return 0;
    snapshots[sequence % svs.numSnapshotClients].appearance=slot->appearance;
    snapshots[sequence % svs.numSnapshotClients].appearance_known=slot->appearance_known;
    return 1;
}

int CODOL_CaptureClientAbilities(int sequence, const codol_ps_ext_t *state)
{
    codol_cs_abilities_t next = {0};
    int slot;
    if (sequence < 0 || svs.numSnapshotClients <= 0 ||
        (size_t)svs.numSnapshotClients > CODOL_CS_EXT_SLOTS) return 0;
    slot = sequence % svs.numSnapshotClients;
    next.sequence = sequence;
    next.client = svs.snapshotClients[slot].clientIndex;
    if (state && state->abilities_known) next.abilities = state->abilities;
    next.captured = 1;
    snapshots[slot] = next;
    return 1;
}

int CODOL_OverlayCapturedClientAbilities(int sequence, codol_client_state_t *out)
{
    const codol_cs_abilities_t *held;
    int slot, count = svsHeader.numSnapshotClients;
    if (!out || sequence < 0 || count <= 0 ||
        (size_t)count > CODOL_CS_EXT_SLOTS || !svsHeader.snapshotClients ||
        sequence >= svsHeader.nextSnapshotClients ||
        (int64_t)sequence < (int64_t)svsHeader.nextSnapshotClients - count) return 0;
    slot = sequence % count;
    held = &snapshots[slot];
    if (!held->captured || held->sequence != sequence ||
        held->client != svsHeader.snapshotClients[slot].clientIndex) return 0;
    {
        codol_client_state_t next=*out;
        if(!CODOL_OverlayClientAbilities(&next, &held->abilities) ||
           (held->appearance_known && !CODOL_OverlayClientAppearance(&next,&held->appearance))) return 0;
        *out=next;return 1;
    }
}
#endif
