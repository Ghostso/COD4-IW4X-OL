/* Storage-keyed playerState extension and its archive-stream record. See
 * codol_playerstate_ext.h for the model, the measured reason it cannot live
 * inside playerState_t, the record format and the list of callers. */
#include "codol_playerstate_ext.h"
#ifdef CODOL_SERVER
#include "codol_perk_runtime.h"
#endif
/* Types only: the storage bases arrive through the seam above, so this file
 * references no engine global and links in isolation. */
#include "g_shared.h"
#include "server.h"
#include "qcommon.h"
#include "qcommon_io.h"
#include <math.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

/* The live storage is the retained g_clients reservation: G_InitGame strides it
 * by 0x3184 with the playerState first, so an address inside it names a client
 * slot. Fail the build rather than the game if the declarations drift. */
_Static_assert(offsetof(gclient_t, ps) == 0, "gclient starts with its playerState");
_Static_assert(sizeof(gclient_t) == 0x3184,
    "gclient stride must match G_InitGame's 0x3184 in _g_main_mp.asm");
_Static_assert(sizeof(playerState_t) == 0x2f64,
    "playerState size must match SpectatorClientEndFrame's 0x2f64 memcpy");
_Static_assert(offsetof(clientSnapshot_t, ps) == 0, "snapshot frame starts with its playerState");

#define CODOL_PS_EXT_ARCHIVE \
    (sizeof(((serverStatic_t *)0)->cachedSnapshotClients) / sizeof(cachedClient_t))

/* SpectatorClientEndFrame carries a whole block in its own frame, at
 * [ebp-0x3800] within the 0x3820 reservation; keep the two in step. The
 * reservation is the capacity the weapon worker's hand bundle also has to fit
 * in, so it is stated here, asserted here, and changed in exactly six places in
 * SpectatorClientEndFrame (the reservation, both epilogues, the two argument
 * pointers and the apply pointer). It is not spare headroom to be assumed:
 * whoever adds a field checks this assert. */
#define CODOL_PS_EXT_SPECTATOR_BUNDLE 2048
_Static_assert(sizeof(codol_ps_ext_t) <= CODOL_PS_EXT_SPECTATOR_BUNDLE,
    "SpectatorClientEndFrame reserves 2048 bytes for the extension bundle");

static codol_ps_ext_t live_ext[MAX_CLIENTS];
static codol_ps_ext_t frame_ext[MAX_CLIENTS][PACKET_BACKUP];
static codol_ps_ext_t archive_ext[CODOL_PS_EXT_ARCHIVE];
static const codol_ps_ext_t unknown_ext;
/* What an unlocked player has: IW4's PlayerCmd_WeaponLockFree (0x5dd670) clears
 * the flags and puts the target back to "none". A zeroed block reads as this. */
static const codol_ps_lock_t reset_lock = { 0, CODOL_PS_LOCK_NO_ENTITY, {0, 0, 0}, {0, 0, 0} };
/* An empty second hand: no weapon, idle phase, no magazines. A zeroed block
 * reads as this, and its clip records read as unused rather than as record 0. */
static const codol_ps_hand_t reset_hand = {
    .clip_index = { -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1 }
};
static const codol_ps_offhand_t reset_offhand;
static unsigned misses;
static unsigned event_desyncs;

/* A miss means a playerState that should carry extension state does not, which
 * shows up as unscaled recoil and an unlocked weapon rather than as wrong
 * values. Say so once instead of hiding it behind the counter. */
static void miss(const playerState_t *ps)
{
    if (!misses++)
        Com_PrintWarning(CON_CHANNEL_SERVER,
            "CoDOL playerState extension: untracked playerState storage %p; "
            "state carried by copy (recoil scale, weapon lock) is unknown for it\n",
            (const void *)ps);
}

/* An event epoch that does not match the state's own counter means a producer
 * of ps->eventSequence exists that does not call CODOL_PlayerStateEventAdded.
 * Missing wrap history must not be repaired by guessing during serialization. */
static void desync(const playerState_t *ps, unsigned counter, uint32_t epoch)
{
    if (!event_desyncs++)
        Com_PrintWarning(CON_CHANNEL_SERVER,
            "CoDOL playerState extension: event epoch %u does not match "
            "playerState %p counter %u; event history cannot be serialized\n",
            (unsigned)epoch, (const void *)ps, counter);
}

static codol_ps_ext_t *resolve(const playerState_t *ps)
{
    uintptr_t p = (uintptr_t)ps, base;
    unsigned count = 0;
    size_t i, j;
    const gclient_t *live;
    const client_t *snapshot;
    const cachedClient_t *archive;
    if (!ps) return NULL;
    live = CODOL_PlayerStateExtLiveBase(&count);
    if (live && count) {
        if (count > MAX_CLIENTS) count = MAX_CLIENTS;
        base = (uintptr_t)live;
        if (p >= base && p < base + (uintptr_t)count * sizeof(gclient_t)) {
            i = (size_t)((p - base) / sizeof(gclient_t));
            if (i < count && &live[i].ps == ps) return &live_ext[i];
        }
    }
    snapshot = CODOL_PlayerStateExtSnapshotBase(&count);
    if (snapshot && count) {
        if (count > MAX_CLIENTS) count = MAX_CLIENTS;
        base = (uintptr_t)snapshot;
        if (p >= base && p < base + (uintptr_t)count * sizeof(client_t)) {
            i = (size_t)((p - base) / sizeof(client_t));
            if (i < count) {
                uintptr_t frames = (uintptr_t)snapshot[i].frames;
                if (p >= frames && p < frames + (uintptr_t)PACKET_BACKUP * sizeof(clientSnapshot_t)) {
                    j = (size_t)((p - frames) / sizeof(clientSnapshot_t));
                    if (j < PACKET_BACKUP && &snapshot[i].frames[j].ps == ps) return &frame_ext[i][j];
                }
            }
        }
    }
    archive = CODOL_PlayerStateExtArchiveBase(&count);
    if (archive && count) {
        if (count > CODOL_PS_EXT_ARCHIVE) count = CODOL_PS_EXT_ARCHIVE;
        base = (uintptr_t)archive;
        if (p >= base && p < base + (uintptr_t)count * sizeof(cachedClient_t)) {
            i = (size_t)((p - base) / sizeof(cachedClient_t));
            if (i < count && &archive[i].ps == ps) return &archive_ext[i];
        }
    }
    return NULL;
}

codol_ps_ext_t *CODOL_PlayerStateExt(const playerState_t *ps)
{
    codol_ps_ext_t *ext = resolve(ps);
    if (!ext) miss(ps);
    return ext;
}

const codol_ps_ext_t *CODOL_PlayerStateExtConst(const playerState_t *ps)
{
    return CODOL_PlayerStateExt(ps);
}

int CODOL_PlayerStateExtCopy(const playerState_t *dst, const playerState_t *src)
{
    codol_ps_ext_t *to = resolve(dst);
    const codol_ps_ext_t *from = resolve(src);
    if (!to) return 0;
    if (!from) {
        /* The destination is tracked and the source is not: that is a copy path
         * this file does not know about, not a state without a magnitude. */
        miss(src);
        *to = unknown_ext;
        return 0;
    }
    *to = *from;
    return 1;
}

int CODOL_PlayerStateExtCopyFromClient(const playerState_t *dst, int client)
{
    codol_ps_ext_t *to = resolve(dst);
    if (!to) return 0;
    if (client < 0 || client >= MAX_CLIENTS) { *to = unknown_ext; return 0; }
    *to = live_ext[client];
    return 1;
}

void CODOL_PlayerStateExtFetch(codol_ps_ext_t *out, const playerState_t *src)
{
    const codol_ps_ext_t *from;
    if (!out) return;
    from = resolve(src);
    *out = from ? *from : unknown_ext;
}

void CODOL_PlayerStateExtFetchFromClient(codol_ps_ext_t *out, int client)
{
    if (!out) return;
    *out = (client >= 0 && client < MAX_CLIENTS) ? live_ext[client] : unknown_ext;
}

int CODOL_PlayerStateExtApply(const playerState_t *dst, const codol_ps_ext_t *value)
{
    codol_ps_ext_t *to = resolve(dst);
    if (!to) return 0;
    *to = value ? *value : unknown_ext;
    return 1;
}

const codol_ps_hand_t *CODOL_PlayerStateHandRead(const playerState_t *ps)
{
    const codol_ps_ext_t *ext = resolve(ps);
    if (!ext) { miss(ps); return &reset_hand; }
    return ext->hand_known ? &ext->hand : &reset_hand;
}

codol_ps_hand_t *CODOL_PlayerStateHandMutable(const playerState_t *ps)
{
    codol_ps_ext_t *ext = resolve(ps);
    if (!ext) { miss(ps); return NULL; }
    if (!ext->hand_known) { ext->hand = reset_hand; ext->hand_known = 1; }
    return &ext->hand;
}

void CODOL_PlayerStateExtClearClientHand(unsigned client)
{
    if (client >= MAX_CLIENTS) return;
    live_ext[client].hand = reset_hand;
    live_ext[client].hand_known = 0;
}

const codol_ps_offhand_t *CODOL_PlayerStateOffhandRead(const playerState_t *ps)
{
    const codol_ps_ext_t *ext = resolve(ps);
    if (!ext) { miss(ps); return &reset_offhand; }
    return ext->offhand_known ? &ext->offhand : &reset_offhand;
}

codol_ps_offhand_t *CODOL_PlayerStateOffhandMutable(const playerState_t *ps)
{
    codol_ps_ext_t *ext = resolve(ps);
    if (!ext) { miss(ps); return NULL; }
    if (!ext->offhand_known) { ext->offhand = reset_offhand; ext->offhand_known = 1; }
    return &ext->offhand;
}

void CODOL_PlayerStateExtClearClientOffhand(unsigned client)
{
    if (client >= MAX_CLIENTS) return;
    live_ext[client].offhand = reset_offhand;
    live_ext[client].offhand_known = 0;
}

void CODOL_PlayerStateExtClearClientInventory(unsigned client)
{
    if (client >= MAX_CLIENTS) return;
    /* The gclient memset at spawn/connect/disconnect used to zero the four
     * in-struct arrays; this is that zeroing for their relocated home, live
     * storage only. An emptied inventory is a recorded state, not an absent
     * one, so known stays set. Captured and archived states keep theirs. */
    memset(live_ext[client].weapons, 0, sizeof(live_ext[client].weapons));
    memset(live_ext[client].weaponold, 0, sizeof(live_ext[client].weaponold));
    memset(live_ext[client].weaponrechamber, 0, sizeof(live_ext[client].weaponrechamber));
    memset(live_ext[client].weaponmodels, 0, sizeof(live_ext[client].weaponmodels));
    live_ext[client].weapons_known = 1;
}

int CODOL_PlayerStateLoopSoundRead(const playerState_t *ps, unsigned *out)
{
    const codol_ps_ext_t *ext = resolve(ps);
    if (out) *out = 0;
    if (!ext) return 0;
    /* An unrecorded state reads as 0, which is silence. The known flag exists
     * so a copy or an archive record can say "nothing was recorded here"
     * rather than "a recorded silence"; both play nothing. */
    if (out) *out = ext->loop_known ? ext->loop_sound : 0u;
    return 1;
}

int CODOL_PlayerStateLoopSoundSet(const playerState_t *ps, unsigned sound)
{
    codol_ps_ext_t *ext;
    /* The sound bank is 256 slots (C1 0x00570920 scans 1..255 of the table at
     * 0x27d5740; the retained G_SoundAliasIndex returns a byte), and the wire
     * field is eight bits, so anything else is a producer that did not use the
     * bank and must not reach the state. */
    if (sound > 255u) return 0;
    ext = resolve(ps);
    if (!ext) { miss(ps); return 0; }
    ext->loop_sound = (unsigned char)sound;
    ext->loop_known = 1;
    return 1;
}

int CODOL_PlayerStateHudIconOverridesRead(const playerState_t *ps,
                                           uint16_t out[CODOL_PS_HUD_ICON_SLOTS])
{
    const codol_ps_ext_t *ext = resolve(ps);
    unsigned slot;
    /* A tracked, zero-initialized record means no overrides. An untracked
     * pointer means the capture is missing; it cannot establish that the
     * player had no overrides. Preserve the caller's output on that failure. */
    if (!out || !ext) return 0;
    for (slot = 0; slot < CODOL_PS_HUD_ICON_SLOTS; ++slot)
        out[slot] = ext->hud_icon[slot];
    return 1;
}

void CODOL_PlayerStateExtSetClientHudIcons(unsigned client,
                                           const uint16_t icons[CODOL_PS_HUD_ICON_SLOTS])
{
    unsigned slot;
    if (client >= MAX_CLIENTS || !icons) return;
    /* The publisher replaces the whole array every frame, like IW4's own
     * publication, so there is no merge and no per-slot bookkeeping here.
     * Values outside the retained material range are dropped rather than
     * published; the script store bounds them, so this only catches a broken
     * producer. */
    for (slot = 0; slot < CODOL_PS_HUD_ICON_SLOTS; ++slot)
        live_ext[client].hud_icon[slot] =
            icons[slot] < (uint16_t)MAX_MATERIALS ? icons[slot] : 0;
}

const codol_ps_lock_t *CODOL_PlayerStateLockRead(const playerState_t *ps)
{
    const codol_ps_ext_t *ext = resolve(ps);
    if (!ext) { miss(ps); return &reset_lock; }
    return ext->lock_known ? &ext->lock : &reset_lock;
}

codol_ps_lock_t *CODOL_PlayerStateLockMutable(const playerState_t *ps)
{
    codol_ps_ext_t *ext = resolve(ps);
    if (!ext) { miss(ps); return NULL; }
    if (!ext->lock_known) { ext->lock = reset_lock; ext->lock_known = 1; }
    return &ext->lock;
}

codol_ps_lock_t *CODOL_PlayerStateExtClientLock(unsigned client)
{
    if (client >= MAX_CLIENTS) return NULL;
    if (!live_ext[client].lock_known) {
        live_ext[client].lock = reset_lock;
        live_ext[client].lock_known = 1;
    }
    return &live_ext[client].lock;
}

/* Every retained producer of ps->eventSequence, and the only ones: they all
 * store the event in ps->events[sequence & 3], the parameter in
 * ps->eventParms[sequence & 3] and then ps->eventSequence = (sequence+1) & 0xff.
 *   BG_AddPredictableEventToPlayerstate  _bg_misc.asm:2861 (the pmove, mantle
 *       and weapon producers, plus the C callers in codol_weapon_state.c,
 *       scr_vm_functions.c and bg_jump.cpp, all route through it)
 *   G_AddEvent client arm                _g_utils_mp.asm:267
 *   G_PlaySoundAlias client arm          _g_utils_mp.asm:1734
 *   G_AnimScriptSound client arm         _g_utils_mp.asm:1819
 * Each of them calls this immediately after that store. */
void CODOL_PlayerStateEventAdded(playerState_t *ps)
{
    codol_ps_ext_t *ext = resolve(ps);
    if (!ext) { miss(ps); return; }
    if (!ext->event_known) { ext->event_epoch = 0; ext->event_known = 1; }
    ++ext->event_epoch;
}

uint32_t CODOL_PlayerStateEventEpoch(const playerState_t *ps)
{
    const codol_ps_ext_t *ext = resolve(ps);
    return (ext && ext->event_known) ? ext->event_epoch : 0;
}

unsigned CODOL_PlayerStateEventDesyncs(void)
{
    return event_desyncs;
}

int CODOL_PlayerStateEventSequence(const playerState_t *ps, unsigned *out)
{
    codol_ps_ext_t *ext;
    unsigned counter;
    if (!ps || !out || ps->eventSequence < 0 || ps->eventSequence > 255) return 0;
    counter = (unsigned)ps->eventSequence;
    ext = resolve(ps);
    if (!ext) {
        /* Untracked storage has no reliable wrap history. Reject serialization. */
        miss(ps);
        desync(ps, counter, counter);
        return 0;
    }
    if (!ext->event_known) {
        /* A state that never had an event is at zero, which is what a fresh
         * spawn looks like; anything else means a producer ran without the
         * hook. Reject that history instead of changing it in a reader. */
        if (counter) { desync(ps, counter, 0); return 0; }
        *out = 0;
        return 1;
    } else if ((ext->event_epoch & 0xffu) != counter) {
        desync(ps, counter, ext->event_epoch);
        return 0;
    }
    *out = ext->event_epoch & 2047u;
    return 1;
}

/* C1's scripted queue producer, 0x00572db3..0x00572dd7: slot (epoch & 3), then
 * the epoch advances. The retained G_AddEvent player branch calls this instead
 * of writing the predicted queue, so a scripted event never lands in the queue
 * pmove predicts and can never be replayed twice by the client. */
void CODOL_PlayerStateScriptEventAdded(playerState_t *ps, unsigned event, unsigned parm)
{
    codol_ps_ext_t *ext = resolve(ps);
    unsigned slot;
    if (!ext) { miss(ps); return; }
    if (!ext->script.known) {
        memset(&ext->script, 0, sizeof(ext->script));
        ext->script.known = 1;
    }
    slot = ext->script.epoch & (CODOL_PS_SCRIPT_EVENT_SLOTS - 1u);
    ext->script.events[slot] = event;
    ext->script.params[slot] = parm;
    ++ext->script.epoch;
}

uint32_t CODOL_PlayerStateScriptEventEpoch(const playerState_t *ps)
{
    const codol_ps_ext_t *ext = resolve(ps);
    return (ext && ext->script.known) ? ext->script.epoch : 0;
}

int CODOL_PlayerStateScriptEventQueue(const playerState_t *ps, unsigned *sequence,
                                      uint32_t events[CODOL_PS_SCRIPT_EVENT_SLOTS],
                                      uint32_t params[CODOL_PS_SCRIPT_EVENT_SLOTS])
{
    const codol_ps_ext_t *ext;
    unsigned i;
    if (!ps || !sequence || !events || !params) return 0;
    ext = resolve(ps);
    if (!ext) {
        /* No storage means no queue history; publishing four empty slots would
         * be an invention, so the caller is told instead. */
        miss(ps);
        return 0;
    }
    if (!ext->script.known) {
        /* A state that never had a scripted event has an empty queue at
         * sequence zero: that is a recorded fact, not a guess. */
        *sequence = 0;
        for (i = 0; i < CODOL_PS_SCRIPT_EVENT_SLOTS; ++i) { events[i] = 0; params[i] = 0; }
        return 1;
    }
    *sequence = ext->script.epoch & 2047u;
    for (i = 0; i < CODOL_PS_SCRIPT_EVENT_SLOTS; ++i) {
        events[i] = ext->script.events[i];
        params[i] = ext->script.params[i];
    }
    return 1;
}

unsigned CODOL_PlayerStateScriptEventsToTransfer(const playerState_t *ps,
                                                 uint32_t events[CODOL_PS_SCRIPT_EVENT_SLOTS],
                                                 uint32_t params[CODOL_PS_SCRIPT_EVENT_SLOTS])
{
    const codol_ps_ext_t *ext;
    uint32_t pending;
    unsigned handed = 0, slot;
    if (!ps || !events || !params) return 0;
    ext = resolve(ps);
    if (!ext || !ext->script.known) return 0;
    pending = ext->script.epoch - ext->script_transferred;
    /* Only the four slots still exist; anything older was overwritten by the
     * producer, which is the same bound C1's transfer helper walks. */
    if (pending > CODOL_PS_SCRIPT_EVENT_SLOTS) pending = CODOL_PS_SCRIPT_EVENT_SLOTS;
    while (pending--) {
        slot = (ext->script.epoch - 1u - pending) & (CODOL_PS_SCRIPT_EVENT_SLOTS - 1u);
        events[handed] = ext->script.events[slot];
        params[handed] = ext->script.params[slot];
        ++handed;
    }
    return handed;
}

void CODOL_PlayerStateScriptEventsTransferred(playerState_t *ps)
{
    codol_ps_ext_t *ext = resolve(ps);
    if (!ext) { miss(ps); return; }
    ext->script_transferred = ext->script.known ? ext->script.epoch : 0;
}

int CODOL_PlayerStateExtClear(const playerState_t *ps)
{
    codol_ps_ext_t *ext = resolve(ps);
    if (!ext) return 0;
    *ext = unknown_ext;
    return 1;
}

void CODOL_PlayerStateExtClearClientStun(unsigned client)
{
    if (client >= MAX_CLIENTS) return;
    live_ext[client].stun_time = 0;
    live_ext[client].stun_known = 0;
}
void CODOL_PlayerStateExtClearClientRecoil(unsigned client)
{
    if (client >= MAX_CLIENTS) return;
    /* Only the recoil half: a respawn that drops the scale must not drop a
     * weapon lock a script armed in the same frame, and the reverse. */
    live_ext[client].recoil_percent = 0;
    live_ext[client].recoil_known = 0;
}

void CODOL_PlayerStateExtClearClientEvents(unsigned client)
{
    if (client >= MAX_CLIENTS) return;
    /* Both queues are this state's event history and are zeroed together by the
     * same gclient memset; the recoil and lock halves are untouched. */
    memset(&live_ext[client].script, 0, sizeof(live_ext[client].script));
    live_ext[client].script_transferred = 0;
    /* The retained counter is zeroed by the gclient memset that accompanies
     * these sites; the epoch follows it, and nothing else in the block moves. */
    live_ext[client].event_epoch = 0;
    live_ext[client].event_known = 0;
}

void CODOL_PlayerStateExtClearClientLock(unsigned client)
{
    if (client >= MAX_CLIENTS) return;
    /* "No lock recorded" and "the reset lock" read the same to every consumer,
     * so this leaves the block in the state a fresh client has. */
    live_ext[client].lock = reset_lock;
    live_ext[client].lock_known = 0;
}

void CODOL_PlayerStateExtClearClientLoopSound(unsigned client)
{
    if (client >= MAX_CLIENTS) return;
    /* Field-specific like the others: a respawn silences the live player's
     * loop, which is what the gclient memset does to C1's ps+0x1f4, and leaves
     * the recoil, lock, hand and event halves alone. Captured snapshots and
     * archived states keep the loop they were taken with. */
    live_ext[client].loop_sound = 0;
    live_ext[client].loop_known = 0;
}

int CODOL_PlayerStateDiveEndTimeSet(const playerState_t *ps,int value)
{
    codol_ps_ext_t *ext=resolve(ps);
    if(!ext) { miss(ps); return 0; }
    ext->dive_end_time=value;
    return 1;
}

int CODOL_PlayerStateDiveEndTimeRead(const playerState_t *ps,int *value)
{
    const codol_ps_ext_t *ext=resolve(ps);
    if(!ext || !value) return 0;
    *value=ext->dive_end_time;
    return 1;
}

void CODOL_PlayerStateExtClearClientDive(unsigned client)
{
    if(client<MAX_CLIENTS) live_ext[client].dive_end_time=0;
}

int CODOL_PlayerStateSpawnTimeSet(const playerState_t *ps,int value)
{
    codol_ps_ext_t *ext=resolve(ps);
    if(!ext) { miss(ps); return 0; }
    ext->spawn_time=value;
    return 1;
}

int CODOL_PlayerStateSpawnTimeRead(const playerState_t *ps,int *value)
{
    const codol_ps_ext_t *ext=resolve(ps);
    if(!ext || !value) return 0;
    *value=ext->spawn_time;
    return 1;
}

void CODOL_PlayerStateExtClearClientSpawnTime(unsigned client)
{
    if(client<MAX_CLIENTS) live_ext[client].spawn_time=0;
}

int CODOL_PlayerStateSetViewmodels(playerState_t *ps,unsigned arms,unsigned hands)
{
    codol_ps_ext_t *ext;
    if(!ps || arms>=CODOL_NATIVE_MODELS || hands>=CODOL_NATIVE_MODELS) return 0;
    ext=CODOL_PlayerStateExt(ps);
    if(!ext) return 0;
    ps->viewmodelIndex=(int)arms;
    ext->viewhands_model=(uint16_t)hands;
    return 1;
}
void CODOL_PlayerStateExtClearClientViewhands(unsigned client)
{
    if(client<MAX_CLIENTS) live_ext[client].viewhands_model=0;
}
void CODOL_PlayerStateExtClearClientPoison(unsigned client)
{
    if(client<MAX_CLIENTS) live_ext[client].poisoned=0;
}

void CODOL_PlayerStateExtClearClientHudIcons(unsigned client)
{
    if (client >= MAX_CLIENTS) return;
    /* Field-specific like the others, and only the published copy: the script
     * store is cleared by its own owner at the same sites. Both engines zero
     * both halves with the gclient memset that accompanies them, and captured
     * snapshots and archived states keep what they were taken with. */
    memset(live_ext[client].hud_icon, 0, sizeof(live_ext[client].hud_icon));
    /* SetClientMaterial's two playerState words go with the same memset. */
    memset(live_ext[client].client_material, 0, sizeof(live_ext[client].client_material));
}

void CODOL_PlayerStateExtClearArchive(void)
{
    memset(archive_ext, 0, sizeof(archive_ext));
}
void CODOL_PlayerStateExtClearClientAbilities(unsigned client)
{
    if(client>=MAX_CLIENTS) return;
#ifdef CODOL_SERVER
    CODOL_ResetPerkRuntime(client);
#endif
    memset(&live_ext[client].abilities,0,sizeof(live_ext[client].abilities));
    live_ext[client].abilities_known=0;
}
void CODOL_PlayerStateExtClearClientPerks(unsigned client)
{
    if(client<MAX_CLIENTS) CODOL_ClearPerks(&live_ext[client].perks);
}
void CODOL_PlayerStateExtClearClientUseHint(unsigned client)
{
    if(client>=MAX_CLIENTS) return;
    live_ext[client].use_hint_weapon=0;
    live_ext[client].throwback_weapon=0;
}
void CODOL_PlayerStateExtSetCorpseIndex(playerState_t *ps,unsigned index)
{
    codol_ps_ext_t *ext;
    if(!ps || index>=8)return;
    ext=CODOL_PlayerStateExt(ps);
    if(ext)ext->corpse_index=(unsigned char)index;
}
void CODOL_PlayerStateExtClearClientLinks(unsigned client)
{
    if(client>=MAX_CLIENTS) return;
    memset(&live_ext[client].links,0,sizeof(live_ext[client].links));
    live_ext[client].links_known=0;
}

void CODOL_PlayerStateExtClearAll(void)
{
#ifdef CODOL_SERVER
    unsigned client;
    for(client=0;client<MAX_CLIENTS;++client) CODOL_ResetPerkRuntime(client);
#endif
    memset(live_ext, 0, sizeof(live_ext));
    memset(frame_ext, 0, sizeof(frame_ext));
    memset(archive_ext, 0, sizeof(archive_ext));
    misses = 0;
    event_desyncs = 0;
}

/* ---- archive stream record ------------------------------------------------
 * Written after every archived playerState and read at the matching read, with
 * the same baseline. Format documented in codol_playerstate_ext.h. Each field
 * has its own changed bit, so an unchanged half costs one bit and neither half
 * can disturb the other's inherited value. */
static uint32_t float_bits(float value)
{
    uint32_t word;
    memcpy(&word, &value, sizeof(word));
    return word;
}

static float bits_float(uint32_t word)
{
    float value;
    memcpy(&value, &word, sizeof(value));
    return value;
}

static int lock_same(const codol_ps_lock_t *a, const codol_ps_lock_t *b)
{
    return a->flags == b->flags && a->entity == b->entity &&
        !memcmp(a->position, b->position, sizeof(a->position)) &&
        !memcmp(a->missile_offset, b->missile_offset, sizeof(a->missile_offset));
}

static int script_same(const codol_ps_script_events_t *a, const codol_ps_script_events_t *b)
{
    return a->epoch == b->epoch &&
        !memcmp(a->events, b->events, sizeof(a->events)) &&
        !memcmp(a->params, b->params, sizeof(a->params));
}

static const codol_ps_lock_t *effective_lock(const codol_ps_ext_t *ext)
{
    return ext->lock_known ? &ext->lock : &reset_lock;
}

/* The hand bundle changes as a unit -- a phase, its clock, its magazines and
 * the records naming the hand behind each queued event all move together -- so
 * one changed bit and a plain body is both correct and small on a stream that
 * only carries archived frames. */
static void hand_write(msg_t *msg, const codol_ps_hand_t *hand)
{
    unsigned i;
    MSG_WriteBits(msg, hand->dual_wield ? 1 : 0, 1);
    MSG_WriteBits(msg, hand->second_barrel ? 1 : 0, 1);
    MSG_WriteBits(msg, hand->fresh_pull ? 1 : 0, 1);
    MSG_WriteBits(msg, hand->state & 0x3f, 6);
    MSG_WriteBits(msg, hand->shot_count & 7, 3);
    MSG_WriteBits(msg, hand->shot_hand & 0xf, 4);
    MSG_WriteBits(msg, hand->shot_last & 0xf, 4);
    MSG_WriteBits(msg, hand->shot_known & 0xf, 4);
    /* Full native indices: a composed weapon above 127 must not come back
     * from an archived frame as a different definition. */
    MSG_WriteBits(msg, hand->weapon, CODOL_WEAPON_INDEX_BITS);
    MSG_WriteBits(msg, hand->primary_weapon, CODOL_WEAPON_INDEX_BITS);
    MSG_WriteBits(msg, hand->animation & 0x7ff, 11);
    MSG_WriteBits(msg, (int)(uint16_t)hand->time, 16);
    MSG_WriteBits(msg, (int)(uint16_t)hand->delay, 16);
    MSG_WriteBits(msg, (int)(uint16_t)hand->restrict_time, 16);
    MSG_WriteBits(msg, hand->charge > 1000 ? 1000 : hand->charge, 10);
    /* Full native width: the two bitsets are CODOL_WEAPON_BIT_WORDS words, and
     * a writer and reader that disagree here shift every record after them. */
    for(i=0;i<CODOL_WEAPON_BIT_WORDS;++i) {
        MSG_WriteBits(msg,(int)hand->second_rechamber[i],32);
        MSG_WriteBits(msg,(int)hand->fast_mag[i],32);
    }
    MSG_WriteBits(msg,hand->primary_reload_fast ? 1 : 0,1);
    for (i = 0; i < CODOL_PS_HAND_CLIPS; ++i) {
        if (hand->clip_index[i] < 0) { MSG_WriteBit0(msg); continue; }
        MSG_WriteBit1(msg);
        MSG_WriteBits(msg, hand->clip_index[i] & 0x7f, 7);
        MSG_WriteBits(msg, hand->magazine[i] & 0x1ff, 9);
    }
}
static int hand_read(msg_t *msg, codol_ps_hand_t *hand)
{
    unsigned i;
    int value;
    *hand = reset_hand;
    hand->dual_wield = (unsigned char)MSG_ReadBits(msg, 1);
    hand->second_barrel = (unsigned char)MSG_ReadBits(msg, 1);
    hand->fresh_pull = (unsigned char)MSG_ReadBits(msg, 1);
    hand->state = (unsigned char)MSG_ReadBits(msg, 6);
    hand->shot_count = (unsigned char)MSG_ReadBits(msg, 3);
    hand->shot_hand = (unsigned char)MSG_ReadBits(msg, 4);
    hand->shot_last = (unsigned char)MSG_ReadBits(msg, 4);
    hand->shot_known = (unsigned char)MSG_ReadBits(msg, 4);
    hand->weapon = (uint16_t)MSG_ReadBits(msg, CODOL_WEAPON_INDEX_BITS);
    hand->primary_weapon = (uint16_t)MSG_ReadBits(msg, CODOL_WEAPON_INDEX_BITS);
    hand->animation = (uint16_t)MSG_ReadBits(msg, 11);
    hand->time = (int16_t)(uint16_t)MSG_ReadBits(msg, 16);
    hand->delay = (int16_t)(uint16_t)MSG_ReadBits(msg, 16);
    hand->restrict_time = (int16_t)(uint16_t)MSG_ReadBits(msg, 16);
    value = MSG_ReadBits(msg, 10);
    if (value < 0 || value > 1000) return 0;
    hand->charge = (uint16_t)value;
    for(i=0;i<CODOL_WEAPON_BIT_WORDS;++i) {
        hand->second_rechamber[i]=(uint32_t)MSG_ReadBits(msg,32);
        hand->fast_mag[i]=(uint32_t)MSG_ReadBits(msg,32);
    }
    hand->primary_reload_fast=(unsigned char)MSG_ReadBits(msg,1);
    for (i = 0; i < CODOL_PS_HAND_CLIPS; ++i) {
        int present = MSG_ReadBit(msg);
        if (present < 0) return 0;
        if (!present) continue;
        hand->clip_index[i] = (signed char)MSG_ReadBits(msg, 7);
        hand->magazine[i] = (int16_t)MSG_ReadBits(msg, 9);
    }
    return !msg->overflowed;
}
/* The relocated inventory: four 700-wide arrays whose owned set is sparse
 * (the wire inventory is fifteen slots), so the record lists owned weapons
 * rather than the bitsets. An unowned weapon carries no old/rechamber/model
 * state, and the reader rebuilds all four arrays from zero. */
#define CODOL_PS_INVENTORY_RECORD_MAX 127u
static unsigned inventory_truncations;
static int inventory_owned(const codol_ps_ext_t *value, unsigned w)
{
    return (value->weapons[w >> 5] >> (w & 31u)) & 1u;
}
static int inventory_same(const codol_ps_ext_t *a, const codol_ps_ext_t *b)
{
    if (a->weapons_known != b->weapons_known) return 0;
    if (!a->weapons_known) return 1;
    return !memcmp(a->weapons, b->weapons, sizeof(a->weapons)) &&
           !memcmp(a->weaponold, b->weaponold, sizeof(a->weaponold)) &&
           !memcmp(a->weaponrechamber, b->weaponrechamber, sizeof(a->weaponrechamber)) &&
           !memcmp(a->weaponmodels, b->weaponmodels, sizeof(a->weaponmodels));
}
static void inventory_write(msg_t *msg, const codol_ps_ext_t *value)
{
    unsigned w, count = 0;
    for (w = 0; w < CODOL_WEAPON_SLOTS; ++w)
        if (inventory_owned(value, w)) ++count;
    if (count > CODOL_PS_INVENTORY_RECORD_MAX) {
        ++inventory_truncations;
        count = CODOL_PS_INVENTORY_RECORD_MAX;
    }
    MSG_WriteBits(msg, (int)count, 7);
    for (w = 0; w < CODOL_WEAPON_SLOTS && count; ++w) {
        if (!inventory_owned(value, w)) continue;
        --count;
        MSG_WriteBits(msg, (int)w, 10);
        MSG_WriteBits(msg, (int)((value->weaponold[w >> 5] >> (w & 31u)) & 1u), 1);
        MSG_WriteBits(msg, (int)((value->weaponrechamber[w >> 5] >> (w & 31u)) & 1u), 1);
        MSG_WriteBits(msg, (int)value->weaponmodels[w], 8);
    }
}
static void inventory_clear(codol_ps_ext_t *value)
{
    memset(value->weapons, 0, sizeof(value->weapons));
    memset(value->weaponold, 0, sizeof(value->weaponold));
    memset(value->weaponrechamber, 0, sizeof(value->weaponrechamber));
    memset(value->weaponmodels, 0, sizeof(value->weaponmodels));
}
static int inventory_read(msg_t *msg, codol_ps_ext_t *value)
{
    int count, prev = -1;
    unsigned n;
    inventory_clear(value);
    count = MSG_ReadBits(msg, 7);
    if (count < 0 || msg->overflowed) return 0;
    for (n = 0; n < (unsigned)count; ++n) {
        int w = MSG_ReadBits(msg, 10);
        int old = MSG_ReadBits(msg, 1);
        int rechamber = MSG_ReadBits(msg, 1);
        int model = MSG_ReadBits(msg, 8);
        /* Ascending and inside the native table, as the writer emits them. */
        if (msg->overflowed || w <= prev || w >= (int)CODOL_WEAPON_SLOTS ||
            old < 0 || rechamber < 0 || model < 0) return 0;
        prev = w;
        value->weapons[w >> 5] |= 1u << (w & 31);
        if (old) value->weaponold[w >> 5] |= 1u << (w & 31);
        if (rechamber) value->weaponrechamber[w >> 5] |= 1u << (w & 31);
        value->weaponmodels[w] = (unsigned char)model;
    }
    return !msg->overflowed;
}
unsigned CODOL_PlayerStateExtInventoryTruncations(void)
{
    return inventory_truncations;
}
/* Check the reader's semantic domains before emitting any part of a record.
 * Masking a bad target/index here would turn it into a different, valid value
 * in delayed snapshots, bypassing the validation at wire publication. */
static int archive_values_valid(const codol_ps_ext_t *value)
{
    if(value->viewhands_model>=CODOL_NATIVE_MODELS || value->poisoned>1) return 0;
    unsigned i;
    if(value->use_hint_weapon == 1 || value->use_hint_weapon > 701) return 0;
    if(value->throwback_weapon>127 ||
       (value->throwback_weapon && !value->use_hint_weapon))return 0;
    if(value->corpse_index>=8)return 0;
    if (value->recoil_known && value->recoil_percent > 100) return 0;
    if (value->lock_known) {
        if (value->lock.flags > 0x7f ||
            value->lock.entity > CODOL_PS_LOCK_NO_ENTITY) return 0;
        for (i = 0; i < 3; ++i)
            if (!isfinite(value->lock.position[i]) ||
                !isfinite(value->lock.missile_offset[i])) return 0;
    }
    for (i = 0; i < CODOL_PS_HUD_ICON_SLOTS; ++i)
        if (value->hud_icon[i] >= MAX_MATERIALS) return 0;
    for (i = 0; i < CODOL_PS_CLIENT_MATERIAL_SLOTS; ++i)
        if (value->client_material[i] >= MAX_MATERIALS) return 0;
    for (i = 0; i < CODOL_ACTION_SLOT_COUNT; ++i)
        if(value->action_slots.type[i]>3 || value->action_slots.weapon[i]>=128)return 0;
    if(value->radar_types.spyplane>3 || value->radar_types.satellite>3 ||
       value->radar_types.motion_tracker>1)return 0;
    if(value->killstreak_hud.count>256)return 0;
    for(i=0;i<5;++i)
        if(value->killstreak_hud.id[i]>128 || value->killstreak_hud.target[i]>25)return 0;
    if (value->abilities_known)
        for (i = 0; i < CODOL_ABILITY_VALUES; ++i)
            if (!isfinite(value->abilities.values[i])) return 0;
    for (i = 0; i < CODOL_PERK_SLOTS; ++i)
        if (value->perks.id[i] > INT32_MAX) return 0;
    return !value->links_known || CODOL_PlayerLinksValid(&value->links);
}

void CODOL_PlayerStateExtWrite(msg_t *msg, const codol_ps_ext_t *value,
                               const codol_ps_ext_t *baseline)
{
    codol_ps_ext_t from = baseline ? *baseline : unknown_ext;
    codol_ps_ext_t to = value ? *value : unknown_ext;
    const codol_ps_lock_t *lock;
    uint32_t delta;
    unsigned i;
    if (!msg) return;
    if (!archive_values_valid(&to) || !archive_values_valid(&from)) {
        msg->overflowed = 1;
        return;
    }
    if (to.recoil_known == from.recoil_known && to.recoil_percent == from.recoil_percent) {
        MSG_WriteBit0(msg);
    } else {
        MSG_WriteBit1(msg);
        MSG_WriteBits(msg, to.recoil_known ? 1 : 0, 1);
        MSG_WriteBits(msg, to.recoil_known ? to.recoil_percent : 0, 7);
    }
    if (to.stun_known == from.stun_known && to.stun_time == from.stun_time) {
        MSG_WriteBit0(msg);
    } else {
        MSG_WriteBit1(msg);
        MSG_WriteBits(msg, to.stun_known ? 1 : 0, 1);
        MSG_WriteLong(msg, to.stun_known ? to.stun_time : 0);
    }
    if (to.lock_known == from.lock_known && lock_same(effective_lock(&to), effective_lock(&from))) {
        MSG_WriteBit0(msg);
    }
    else {
        MSG_WriteBit1(msg);
        MSG_WriteBits(msg, to.lock_known ? 1 : 0, 1);
        if (to.lock_known) {
            lock = &to.lock;
            /* The setters keep flags inside the seven wire bits (0x7f) and the
             * target inside the eleven the C1 field carries; a value outside
             * them would be rejected by CODOL_OverlayWeaponLock before it could
             * be published. */
            MSG_WriteBits(msg, (int)lock->flags, 7);
            MSG_WriteBits(msg, (int)lock->entity, 11);
            for (i = 0; i < 3; ++i) MSG_WriteBits(msg, (int)float_bits(lock->position[i]), 32);
            for (i = 0; i < 3; ++i) MSG_WriteBits(msg, (int)float_bits(lock->missile_offset[i]), 32);
        }
    }
    if (to.hand_known == from.hand_known && !memcmp(&to.hand, &from.hand, sizeof(to.hand))) {
        MSG_WriteBit0(msg);
    } else {
        MSG_WriteBit1(msg);
        MSG_WriteBits(msg, to.hand_known ? 1 : 0, 1);
        if (to.hand_known) hand_write(msg, &to.hand);
    }
    /* The loop sound: one byte, the width of both engines' fields. Written
     * here, before the event block, so writer and reader always reach it. */
    if (to.loop_known == from.loop_known && to.loop_sound == from.loop_sound) {
        MSG_WriteBit0(msg);
    } else {
        MSG_WriteBit1(msg);
        MSG_WriteBits(msg, to.loop_known ? 1 : 0, 1);
        MSG_WriteBits(msg, to.loop_known ? (int)to.loop_sound : 0, 8);
    }
    /* The published weapon HUD icon overrides: eight native material indices,
     * eight bits each, the width the retained CS_MATERIALS range
     * (MAX_MATERIALS = 256, indices 0..255) needs. No "recorded" bit, because
     * an unset slot and a slot holding 0 are the same state - no override - in
     * both engines and in every consumer here. Written before the event block,
     * in the reader's order. Preflight also checks the publisher's bounds
     * before any part of this record is emitted. */
    if (!memcmp(to.hud_icon, from.hud_icon, sizeof(to.hud_icon))) {
        MSG_WriteBit0(msg);
    } else {
        MSG_WriteBit1(msg);
        for (i = 0; i < CODOL_PS_HUD_ICON_SLOTS; ++i)
            MSG_WriteBits(msg, (int)to.hud_icon[i], 8);
    }
    if (!memcmp(&to.action_slots,&from.action_slots,sizeof(to.action_slots))) {
        MSG_WriteBit0(msg);
    } else {
        MSG_WriteBit1(msg);
        for(i=0;i<CODOL_ACTION_SLOT_COUNT;++i) {
            MSG_WriteBits(msg,to.action_slots.type[i],2);
            MSG_WriteBits(msg,to.action_slots.weapon[i],CODOL_WEAPON_INDEX_BITS);
        }
    }
    if (!memcmp(&to.killstreak_hud,&from.killstreak_hud,sizeof(to.killstreak_hud))) {
        MSG_WriteBit0(msg);
    } else {
        MSG_WriteBit1(msg);
        MSG_WriteBits(msg,to.killstreak_hud.count,9);
        for(i=0;i<5;++i) {
            MSG_WriteBits(msg,to.killstreak_hud.id[i],8);
            MSG_WriteBits(msg,to.killstreak_hud.target[i],5);
        }
    }
    if (!memcmp(&to.radar_types,&from.radar_types,sizeof(to.radar_types))) {
        MSG_WriteBit0(msg);
    } else {
        MSG_WriteBit1(msg);
        MSG_WriteBits(msg,to.radar_types.spyplane,2);
        MSG_WriteBits(msg,to.radar_types.satellite,2);
        MSG_WriteBits(msg,to.radar_types.motion_tracker,1);
    }
    /* The event epoch usually advances by a handful per archived frame, so the
     * short form carries the difference from the same baseline the playerState
     * was delta'd against; anything else carries the epoch itself. Every block
     * is written unconditionally, in the reader's order: an early return here
     * used to end the record before the scripted-queue block while the reader
     * still consumed a bit for it, which desynchronised the stream for every
     * archived state whose event epoch had not moved. */
    if (to.event_known == from.event_known && to.event_epoch == from.event_epoch) {
        MSG_WriteBit0(msg);
    } else {
        MSG_WriteBit1(msg);
        MSG_WriteBits(msg, to.event_known ? 1 : 0, 1);
        if (to.event_known) {
            delta = to.event_epoch - from.event_epoch;
            if (from.event_known && delta >= 1 && delta <= 16) {
                MSG_WriteBit1(msg);
                MSG_WriteBits(msg, (int)(delta - 1), 4);
            } else {
                MSG_WriteBit0(msg);
                MSG_WriteBits(msg, (int)to.event_epoch, 32);
            }
        }
    }
    /* The three selected offhands. A weapon index is ten bits on the CoDOL
     * wire, and the producers only ever store an index the player holds, so
     * sixteen bits carry any value this can hold. */
    if (to.offhand_known == from.offhand_known &&
        !memcmp(&to.offhand, &from.offhand, sizeof(to.offhand))) {
        MSG_WriteBit0(msg);
    } else {
        MSG_WriteBit1(msg);
        MSG_WriteBits(msg, to.offhand_known ? 1 : 0, 1);
        if (to.offhand_known)
            for (i = 0; i < CODOL_OFFHAND_SLOTS; ++i)
                MSG_WriteBits(msg, (int)to.offhand.weapon[i], 16);
    }
    /* Internal archive ability block, before the scripted queue's terminal
     * fast paths. Stored values survive clear/unset, even with zero masks. */
    if(to.abilities_known==from.abilities_known &&
       (!to.abilities_known || !memcmp(&to.abilities,&from.abilities,sizeof(to.abilities)))) {
        MSG_WriteBit0(msg);
    } else {
        MSG_WriteBit1(msg);
        MSG_WriteBits(msg,to.abilities_known ? 1 : 0,1);
        if(to.abilities_known) {
            for(i=0;i<CODOL_ABILITY_MASK_WORDS;++i)
                MSG_WriteBits(msg,(int)to.abilities.masks[i],32);
            for(i=0;i<CODOL_ABILITY_VALUES;++i)
                MSG_WriteBits(msg,(int)float_bits(to.abilities.values[i]),32);
        }
    }
    /* Perk IDs belong to ps even though client ability masks use a separate
     * channel. Internal delta baseline includes empty slots and replacements. */
    if(!memcmp(&to.perks,&from.perks,sizeof(to.perks))) MSG_WriteBit0(msg);
    else {
        MSG_WriteBit1(msg);
        for(i=0;i<CODOL_PERK_SLOTS;++i) MSG_WriteBits(msg,(int)to.perks.id[i],32);
    }
    /* Link state precedes the scripted queue, whose writer has early returns.
     * The same record participates in full and delta archived snapshots. */
    if(to.links_known == from.links_known &&
       (!to.links_known || !memcmp(&to.links, &from.links, sizeof(to.links)))) {
        MSG_WriteBit0(msg);
    } else {
        MSG_WriteBit1(msg);
        MSG_WriteBits(msg, to.links_known ? 1 : 0, 1);
        if(to.links_known) {
            MSG_WriteBits(msg, (int)to.links.mode, 2);
            MSG_WriteBits(msg, (int)to.links.offsetEnabled, 1);
            MSG_WriteBits(msg, (int)to.links.anglesLocked, 1);
            MSG_WriteBits(msg, (int)to.links.linkWeaponEntNum, 11);
            MSG_WriteBits(msg, (int)to.links.cameraEntNum, 11);
            MSG_WriteBits(msg, (int)to.links.cameraTagIndex, 6);
            MSG_WriteBits(msg, (int)to.links.controlsEntNum, 11);
            MSG_WriteBits(msg, (int)to.links.cameraFlags, 8);
            for(i=0;i<3;++i)
                MSG_WriteBits(msg, (int)to.links.weaponViewAngleBits[i], 32);
            for(i=0;i<3;++i)
                MSG_WriteBits(msg, (int)to.links.linkAngleBits[i], 32);
        }
    }
    if(to.use_hint_weapon == from.use_hint_weapon) MSG_WriteBit0(msg);
    else {
        MSG_WriteBit1(msg);
        MSG_WriteBits(msg, (int)to.use_hint_weapon, 10);
    }
    if(to.throwback_weapon == from.throwback_weapon) MSG_WriteBit0(msg);
    else {
        MSG_WriteBit1(msg);
        MSG_WriteBits(msg,(int)to.throwback_weapon,CODOL_WEAPON_INDEX_BITS);
    }
    if(to.corpse_index == from.corpse_index) MSG_WriteBit0(msg);
    else {
        MSG_WriteBit1(msg);
        MSG_WriteBits(msg,(int)to.corpse_index,3);
    }
    /* Native model namespace, independent of the C1 model bank. */
    if(to.viewhands_model == from.viewhands_model) MSG_WriteBit0(msg);
    else {
        MSG_WriteBit1(msg);
        MSG_WriteBits(msg, (int)to.viewhands_model, 16);
    }
    /* C1 ps+0x234 is a signed command time. Keep it with the captured state;
     * delayed snapshots must not consult the live client's latest dive. */
    if(to.dive_end_time == from.dive_end_time) MSG_WriteBit0(msg);
    else {
        MSG_WriteBit1(msg);
        MSG_WriteLong(msg,to.dive_end_time);
    }
    /* C1 ps+0x333c spawn time travels with the captured state too. */
    if(to.spawn_time == from.spawn_time) MSG_WriteBit0(msg);
    else {
        MSG_WriteBit1(msg);
        MSG_WriteLong(msg,to.spawn_time);
    }
    /* Poison belongs to this captured state, including delayed spectators. */
    MSG_WriteBits(msg,to.poisoned,1);
    /* SetClientMaterial's native material indices, eight bits each like the
     * HUD icon overrides; changed bit first. */
    if(!memcmp(to.client_material,from.client_material,sizeof(to.client_material))) MSG_WriteBit0(msg);
    else {
        MSG_WriteBit1(msg);
        for(i=0;i<CODOL_PS_CLIENT_MATERIAL_SLOTS;++i)
            MSG_WriteBits(msg,(int)to.client_material[i],8);
    }
    /* The scripted queue: its epoch and all four slots, at the widths C1's
     * fields carry. The live consumption cursor is not encoded - it is not part
     * of the state a snapshot or an archived frame describes. */
    if (to.script.known == from.script.known && script_same(&to.script, &from.script)) {
        MSG_WriteBit0(msg);
    } else {
        MSG_WriteBit1(msg);
        MSG_WriteBits(msg, to.script.known ? 1 : 0, 1);
        if (to.script.known) {
            MSG_WriteBits(msg, (int)to.script.epoch, 32);
            for (i = 0; i < CODOL_PS_SCRIPT_EVENT_SLOTS; ++i) {
                /* Internal archive stores native values, before wire translation. */
                MSG_WriteBits(msg, (int)to.script.events[i], 32);
                MSG_WriteBits(msg, (int)to.script.params[i], 32);
            }
        }
    }
    /* The relocated inventory, last in the record: changed bit, known bit,
     * then the owned weapons as a 7-bit count and (10-bit index, old bit,
     * rechamber bit, 8-bit model) per weapon in ascending order. The scripted
     * queue above no longer returns early, so this block is always reached. */
    if (inventory_same(&to, &from)) {
        MSG_WriteBit0(msg);
    } else {
        MSG_WriteBit1(msg);
        MSG_WriteBits(msg, to.weapons_known ? 1 : 0, 1);
        if (to.weapons_known) inventory_write(msg, &to);
    }
}

void CODOL_PlayerStateExtRead(msg_t *msg, codol_ps_ext_t *out,
                              const codol_ps_ext_t *baseline)
{
    codol_ps_ext_t value = baseline ? *baseline : unknown_ext;
    codol_ps_lock_t lock;
    const uint32_t base_event_epoch = baseline ? baseline->event_epoch : 0;
    const int base_event_known = baseline ? baseline->event_known != 0 : 0;
    int changed, known, percent, flags, entity, failed = 0;
    unsigned i;
    if (!msg) {
        if (out) *out = unknown_ext;
        return;
    }
    if (!archive_values_valid(&value)) {
        msg->overflowed = 1;
        if (out) *out = unknown_ext;
        return;
    }
    changed = MSG_ReadBit(msg);
    if (changed < 0 || msg->overflowed) {
        failed = 1;
    } else if (changed) {
        known = MSG_ReadBits(msg, 1);
        percent = MSG_ReadBits(msg, 7);
        if (msg->overflowed || known < 0 || percent < 0 ||
            percent > 100 || (!known && percent != 0)) {
            failed = 1;
        } else {
            /* Only this field: the other half keeps the baseline it inherited. */
            value.recoil_known = known ? 1 : 0;
            value.recoil_percent = (unsigned char)(known ? percent : 0);
        }
    }
    if (!failed) {
        changed = MSG_ReadBit(msg);
        if (changed < 0 || msg->overflowed) {
            failed = 1;
        } else if (changed) {
            int stun_time;
            known = MSG_ReadBits(msg, 1);
            stun_time = MSG_ReadLong(msg);
            if (msg->overflowed || known < 0 || (!known && stun_time != 0)) {
                failed = 1;
            } else {
                value.stun_known = known ? 1 : 0;
                value.stun_time = known ? stun_time : 0;
            }
        }
    }
    if (!failed) {
        changed = MSG_ReadBit(msg);
        if (changed < 0 || msg->overflowed) {
            failed = 1;
        } else if (changed) {
            known = MSG_ReadBits(msg, 1);
            if (msg->overflowed || known < 0) {
                failed = 1;
            } else if (!known) {
                value.lock_known = 0;
                value.lock = reset_lock;
            } else {
                lock = reset_lock;
                flags = MSG_ReadBits(msg, 7);
                entity = MSG_ReadBits(msg, 11);
                for (i = 0; i < 3; ++i)
                    lock.position[i] = bits_float((uint32_t)MSG_ReadBits(msg, 32));
                for (i = 0; i < 3; ++i)
                    lock.missile_offset[i] = bits_float((uint32_t)MSG_ReadBits(msg, 32));
                if (msg->overflowed || flags < 0 || entity < 0 ||
                    flags > 0x7f || entity > (int)CODOL_PS_LOCK_NO_ENTITY) {
                    failed = 1;
                } else {
                    for (i = 0; i < 3; ++i)
                        if (!isfinite(lock.position[i]) || !isfinite(lock.missile_offset[i]))
                            failed = 1;
                    if (!failed) {
                        lock.flags = (uint32_t)flags;
                        lock.entity = (uint32_t)entity;
                        value.lock = lock;
                        value.lock_known = 1;
                    }
                }
            }
        }
    }
    if (!failed) {
        changed = MSG_ReadBit(msg);
        if (changed < 0 || msg->overflowed) {
            failed = 1;
        } else if (changed) {
            known = MSG_ReadBits(msg, 1);
            if (msg->overflowed || known < 0) {
                failed = 1;
            } else if (!known) {
                value.hand = reset_hand;
                value.hand_known = 0;
            } else if (!hand_read(msg, &value.hand)) {
                failed = 1;
            } else {
                value.hand_known = 1;
            }
        }
    }
    if (!failed) {
        changed = MSG_ReadBit(msg);
        if (changed < 0 || msg->overflowed) {
            failed = 1;
        } else if (changed) {
            int sound;
            known = MSG_ReadBits(msg, 1);
            sound = MSG_ReadBits(msg, 8);
            /* The bank is 256 slots and the wire field eight bits, so the only
             * unreadable combination is an unrecorded state carrying a value. */
            if (msg->overflowed || known < 0 || sound < 0 || sound > 255 ||
                (!known && sound != 0)) {
                failed = 1;
            } else {
                value.loop_known = known ? 1 : 0;
                value.loop_sound = (unsigned char)(known ? sound : 0);
            }
        }
    }
    if (!failed) {
        changed = MSG_ReadBit(msg);
        if (changed < 0 || msg->overflowed) {
            failed = 1;
        } else if (changed) {
            uint16_t icons[CODOL_PS_HUD_ICON_SLOTS];
            for (i = 0; i < CODOL_PS_HUD_ICON_SLOTS && !failed; ++i) {
                int material = MSG_ReadBits(msg, 8);
                /* The whole eight-bit domain is a valid index into the retained
                 * material range, so only an overflowed stream can fail here;
                 * it is checked per slot so a truncated record cannot leave
                 * half an array behind. */
                if (msg->overflowed || material < 0 || material >= MAX_MATERIALS) failed = 1;
                else icons[i] = (uint16_t)material;
            }
            if (!failed) memcpy(value.hud_icon, icons, sizeof(value.hud_icon));
        }
    }
    if (!failed) {
        changed=MSG_ReadBit(msg);
        if(changed<0 || msg->overflowed)failed=1;
        else if(changed) {
            codol_action_slots_t slots={0};
            for(i=0;i<CODOL_ACTION_SLOT_COUNT && !failed;++i) {
                int type=MSG_ReadBits(msg,2),weapon=MSG_ReadBits(msg,CODOL_WEAPON_INDEX_BITS);
                if(type<0 || weapon<0 || msg->overflowed)failed=1;
                else {slots.type[i]=(uint8_t)type;slots.weapon[i]=(uint16_t)weapon;}
            }
            if(!failed)value.action_slots=slots;
        }
    }
    if (!failed) {
        changed=MSG_ReadBit(msg);
        if(changed<0 || msg->overflowed)failed=1;
        else if(changed) {
            codol_killstreak_hud_t hud={0};
            int count=MSG_ReadBits(msg,9);
            if(count<0 || count>256 || msg->overflowed)failed=1;
            else hud.count=(uint16_t)count;
            for(i=0;i<5 && !failed;++i) {
                int id=MSG_ReadBits(msg,8),target=MSG_ReadBits(msg,5);
                if(id<0 || id>128 || target<0 || target>25 || msg->overflowed)failed=1;
                else {hud.id[i]=(uint8_t)id;hud.target[i]=(uint8_t)target;}
            }
            if(!failed)value.killstreak_hud=hud;
        }
    }
    if (!failed) {
        changed=MSG_ReadBit(msg);
        if(changed<0 || msg->overflowed)failed=1;
        else if(changed) {
            int spy=MSG_ReadBits(msg,2),sat=MSG_ReadBits(msg,2),motion=MSG_ReadBit(msg);
            if(spy<0 || sat<0 || motion<0 || msg->overflowed)failed=1;
            else {value.radar_types.spyplane=(uint8_t)spy;
                  value.radar_types.satellite=(uint8_t)sat;
                  value.radar_types.motion_tracker=(uint8_t)motion;}
        }
    }
    if (!failed) {
        changed = MSG_ReadBit(msg);
        if (changed < 0 || msg->overflowed) {
            failed = 1;
        } else if (changed) {
            known = MSG_ReadBits(msg, 1);
            if (msg->overflowed || known < 0) {
                failed = 1;
            } else if (!known) {
                value.event_known = 0;
                value.event_epoch = 0;
            } else {
                int shortform = MSG_ReadBit(msg);
                if (shortform < 0 || msg->overflowed) {
                    failed = 1;
                } else if (shortform) {
                    int step = MSG_ReadBits(msg, 4);
                    /* The short form is a difference from the baseline, so a
                     * baseline that carried no epoch cannot produce one. */
                    if (msg->overflowed || step < 0 || !base_event_known) failed = 1;
                    else { value.event_epoch = base_event_epoch + (uint32_t)step + 1u; value.event_known = 1; }
                } else {
                    uint32_t epoch = (uint32_t)MSG_ReadBits(msg, 32);
                    if (msg->overflowed) failed = 1;
                    else { value.event_epoch = epoch; value.event_known = 1; }
                }
            }
        }
    }
    if (!failed) {
        /* The selected offhands, in the order the writer emitted them. */
        changed = MSG_ReadBit(msg);
        if (changed < 0 || msg->overflowed) {
            failed = 1;
        } else if (changed) {
            known = MSG_ReadBits(msg, 1);
            if (msg->overflowed || known < 0) {
                failed = 1;
            } else if (!known) {
                value.offhand = reset_offhand;
                value.offhand_known = 0;
            } else {
                codol_ps_offhand_t slots = reset_offhand;
                for (i = 0; i < CODOL_OFFHAND_SLOTS && !failed; ++i) {
                    int weapon = MSG_ReadBits(msg, 16);
                    if (msg->overflowed || weapon < 0) failed = 1;
                    else slots.weapon[i] = (uint16_t)weapon;
                }
                if (!failed) { slots.known = 1; value.offhand = slots; value.offhand_known = 1; }
            }
        }
    }
    if(!failed) {
        changed=MSG_ReadBit(msg);
        if(changed<0 || msg->overflowed) failed=1;
        else if(changed) {
            known=MSG_ReadBits(msg,1);
            if(known<0 || msg->overflowed) failed=1;
            else if(!known) {
                memset(&value.abilities,0,sizeof(value.abilities));
                value.abilities_known=0;
            } else {
                codol_client_abilities_t abilities;
                for(i=0;i<CODOL_ABILITY_MASK_WORDS;++i)
                    abilities.masks[i]=(uint32_t)MSG_ReadBits(msg,32);
                for(i=0;i<CODOL_ABILITY_VALUES;++i) {
                    abilities.values[i]=bits_float((uint32_t)MSG_ReadBits(msg,32));
                    if(!isfinite(abilities.values[i])) failed=1;
                }
                if(msg->overflowed) failed=1;
                if(!failed) { value.abilities=abilities; value.abilities_known=1; }
            }
        }
    }
    if(!failed) {
        changed=MSG_ReadBit(msg);
        if(changed<0 || msg->overflowed) failed=1;
        else if(changed) {
            codol_perk_state_t perks;
            for(i=0;i<CODOL_PERK_SLOTS;++i) {
                perks.id[i]=(uint32_t)MSG_ReadBits(msg,32);
                if(perks.id[i]>INT32_MAX) failed=1;
            }
            if(msg->overflowed) failed=1;
            if(!failed) value.perks=perks;
        }
    }
    if(!failed) {
        changed = MSG_ReadBit(msg);
        if(changed < 0 || msg->overflowed) failed = 1;
        else if(changed) {
            known = MSG_ReadBits(msg, 1);
            if(known < 0 || msg->overflowed) failed = 1;
            else if(!known) {
                memset(&value.links, 0, sizeof(value.links));
                value.links_known = 0;
            } else {
                codol_ps_links_t links;
                links.mode = (uint32_t)MSG_ReadBits(msg, 2);
                links.offsetEnabled = (uint32_t)MSG_ReadBits(msg, 1);
                links.anglesLocked = (uint32_t)MSG_ReadBits(msg, 1);
                links.linkWeaponEntNum = (uint32_t)MSG_ReadBits(msg, 11);
                links.cameraEntNum = (uint32_t)MSG_ReadBits(msg, 11);
                links.cameraTagIndex = (uint32_t)MSG_ReadBits(msg, 6);
                links.controlsEntNum = (uint32_t)MSG_ReadBits(msg, 11);
                links.cameraFlags = (uint32_t)MSG_ReadBits(msg, 8);
                for(i=0;i<3;++i)
                    links.weaponViewAngleBits[i] = (uint32_t)MSG_ReadBits(msg, 32);
                for(i=0;i<3;++i)
                    links.linkAngleBits[i] = (uint32_t)MSG_ReadBits(msg, 32);
                if(msg->overflowed || !CODOL_PlayerLinksValid(&links)) failed = 1;
                else { value.links = links; value.links_known = 1; }
            }
        }
    }
    if(!failed) {
        changed = MSG_ReadBit(msg);
        if(changed < 0 || msg->overflowed) failed = 1;
        else if(changed) {
            int binding = MSG_ReadBits(msg, 10);
            if(binding < 0 || binding == 1 || binding > 701 || msg->overflowed) failed = 1;
            else value.use_hint_weapon = (uint16_t)binding;
        }
    }
    if(!failed) {
        changed=MSG_ReadBit(msg);
        if(changed<0 || msg->overflowed)failed=1;
        else if(changed) {
            int weapon=MSG_ReadBits(msg,CODOL_WEAPON_INDEX_BITS);
            if(weapon<0 || msg->overflowed)failed=1;
            else value.throwback_weapon=(uint16_t)weapon;
        }
        if(value.throwback_weapon && !value.use_hint_weapon)failed=1;
    }
    if(!failed) {
        changed=MSG_ReadBit(msg);
        if(changed<0 || msg->overflowed)failed=1;
        else if(changed) {
            int index=MSG_ReadBits(msg,3);
            if(index<0 || msg->overflowed)failed=1;
            else value.corpse_index=(unsigned char)index;
        }
    }
    if(!failed) {
        changed=MSG_ReadBit(msg);
        if(changed<0 || msg->overflowed) failed=1;
        else if(changed) {
            int model=MSG_ReadBits(msg,16);
            if(model<0 || model>=CODOL_NATIVE_MODELS || msg->overflowed) failed=1;
            else value.viewhands_model=(uint16_t)model;
        }
    }
    if(!failed) {
        changed=MSG_ReadBit(msg);
        if(changed<0 || msg->overflowed) failed=1;
        else if(changed) value.dive_end_time=MSG_ReadLong(msg);
        if(msg->overflowed) failed=1;
    }
    if(!failed) {
        changed=MSG_ReadBit(msg);
        if(changed<0 || msg->overflowed) failed=1;
        else if(changed) value.spawn_time=MSG_ReadLong(msg);
        if(msg->overflowed) failed=1;
    }
    if(!failed) {
        int poisoned=MSG_ReadBits(msg,1);
        if(poisoned<0 || msg->overflowed) failed=1;
        else value.poisoned=(unsigned char)poisoned;
    }
    if(!failed) {
        changed=MSG_ReadBit(msg);
        if(changed<0 || msg->overflowed) failed=1;
        else if(changed) {
            uint16_t materials[CODOL_PS_CLIENT_MATERIAL_SLOTS];
            for(i=0;i<CODOL_PS_CLIENT_MATERIAL_SLOTS && !failed;++i) {
                int material=MSG_ReadBits(msg,8);
                if(msg->overflowed || material<0 || material>=MAX_MATERIALS) failed=1;
                else materials[i]=(uint16_t)material;
            }
            if(!failed) memcpy(value.client_material,materials,sizeof(value.client_material));
        }
    }
    if (!failed) {
        changed = MSG_ReadBit(msg);
        if (changed < 0 || msg->overflowed) {
            failed = 1;
        } else if (changed) {
            known = MSG_ReadBits(msg, 1);
            if (msg->overflowed || known < 0) {
                failed = 1;
            } else if (!known) {
                memset(&value.script, 0, sizeof(value.script));
            } else {
                codol_ps_script_events_t queue;
                memset(&queue, 0, sizeof(queue));
                queue.epoch = (uint32_t)MSG_ReadBits(msg, 32);
                for (i = 0; i < CODOL_PS_SCRIPT_EVENT_SLOTS && !failed; ++i) {
                    uint32_t slot_event = (uint32_t)MSG_ReadBits(msg, 32);
                    uint32_t slot_param = (uint32_t)MSG_ReadBits(msg, 32);
                    if (msg->overflowed) failed = 1;
                    else {
                        queue.events[i] = slot_event;
                        queue.params[i] = slot_param;
                    }
                }
                if (!failed) { queue.known = 1; value.script = queue; }
            }
        }
    }
    if (!failed) {
        /* The relocated inventory, in the writer's order: last. */
        changed = MSG_ReadBit(msg);
        if (changed < 0 || msg->overflowed) {
            failed = 1;
        } else if (changed) {
            known = MSG_ReadBits(msg, 1);
            if (msg->overflowed || known < 0) {
                failed = 1;
            } else if (!known) {
                inventory_clear(&value);
                value.weapons_known = 0;
            } else if (!inventory_read(msg, &value)) {
                failed = 1;
            } else {
                value.weapons_known = 1;
            }
        }
    }
    if (failed) {
        /* A record this reader cannot trust means the stream is out of step:
         * fail the frame rather than hand a rebuilt state made-up values. */
        msg->overflowed = 1;
        value = unknown_ext;
    }
    /* The cursor belongs to the live transfer, never to a rebuilt state. */
    value.script_transferred = 0;
    if (out) *out = value;
}

void CODOL_PlayerStateExtWriteState(msg_t *msg, const playerState_t *ps,
                                    const playerState_t *baseline)
{
    CODOL_PlayerStateExtWrite(msg, resolve(ps), resolve(baseline));
}

void CODOL_PlayerStateExtWriteClient(msg_t *msg, int client,
                                     const playerState_t *baseline)
{
    codol_ps_ext_t value;
    CODOL_PlayerStateExtFetchFromClient(&value, client);
    CODOL_PlayerStateExtWrite(msg, &value, resolve(baseline));
}

void CODOL_PlayerStateExtReadState(msg_t *msg, const playerState_t *ps,
                                   const playerState_t *baseline)
{
    codol_ps_ext_t value;
    CODOL_PlayerStateExtRead(msg, &value, resolve(baseline));
    /* The producers keep ps->eventSequence = epoch & 0xff, and the record was
     * written beside this very playerState, so a mismatch here is a rebuilt
     * state whose two halves disagree: repair from the counter the state
     * carries and report it rather than publish an invented epoch. */
    if (ps && value.event_known && ps->eventSequence >= 0 && ps->eventSequence <= 255 &&
        (value.event_epoch & 0xffu) != (unsigned)ps->eventSequence) {
        desync(ps, (unsigned)ps->eventSequence, value.event_epoch);
        value.event_epoch += ((unsigned)ps->eventSequence - value.event_epoch) & 0xffu;
    }
    /* An untracked destination means the caller is rebuilding into something
     * this file does not follow; the record was still consumed, so the stream
     * stays in step. */
    CODOL_PlayerStateExtApply(ps, &value);
}

unsigned CODOL_PlayerStateExtMisses(void)
{
    return misses;
}
