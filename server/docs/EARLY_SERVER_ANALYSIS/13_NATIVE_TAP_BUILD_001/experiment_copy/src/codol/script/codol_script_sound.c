/* CoDOL script sound methods: authoritative alias registration plus the sound
 * event C1 consumes. SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Transport, from C1's own producers (C1 is both client and server, so its
 * server arm defines the wire contract its client arm reads):
 *   C1 playsoundatpos 0x54d340 -> helper 0x54cf30:
 *       alias lookup 0x4cbda0/0x4cb8e0 (asset type 11), reject looping aliases,
 *       index = G_SoundAliasIndex 0x570920 (a byte, table of 256 slots),
 *       entity = G_TempEntity(origin, 3 = EV_SOUND_ALIAS) 0x572c00,
 *       entity+0xac = index, entity+0x80 = 2046 (no owning entity).
 *   C1's entity-attached playsound 0x54d1c0 writes the same two fields with
 *       entity+0x80 = the source entity number.
 *   C1 StopSounds 0x536120: reject ET_EVENTS receivers, then queue event
 *       5 (EV_STOPSOUND) with parameter 0 on the player state when the entity
 *       has a client, otherwise on the entity event queue.
 * The alias names themselves reach the client through the sound bank the
 * asset publisher mirrors at CS 3395+index, which C1's LocalSound 0x468765
 * reads by index; both paths therefore share one index space of 1..255. */
#ifdef CODOL_SERVER
#include "codol_script_sound.h"
#include "codol_sound_native.h"
#include "scr_vm_functions.h"
#include "g_shared.h"
#include "g_public_mp.h"
#include "g_public.h"
#include "bg.h"
#include "entity.h"
#include "server.h"
#include "qcommon_io.h"
#include "cscr_stringlist.h"
#include "codol_assets.h"
#include "cvar.h"
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

/* Engine producers, declared here like the other native CoDOL script files. */
gentity_t *__cdecl G_TempEntity(const float *origin, int event);
int __cdecl G_SoundAliasIndex(const char *name);
void __cdecl G_AddEvent(gentity_t *ent, int event, int eventParm);
int __cdecl G_DObjGetWorldTagPos(gentity_t *ent, unsigned int tagName, float *out);
int __cdecl SV_DObjGetBoneIndex(gentity_t *ent, unsigned int boneName);
unsigned int __cdecl Scr_GetConstLowercaseString(unsigned int index);

int CODOL_SoundAliasIsLooping(const char *alias)
{
    const snd_alias_list_t *list;
    if(!alias || !*alias) return -1;
    /* Converted archive data, not a name guess: the CoDOL flag word's bit 0 is
     * the measured looping flag (C1 0x738665, 0x738330), and C1's own script
     * arm 0x54cfcc tests exactly that bit on the list's first alias. */
    list=CODOL_FindEngineSoundAlias(alias);
    if(!list || list->count<1 || !list->head) return -1;
    return SND_AliasLooping(&list->head[0]) ? 1 : 0;
}
/* G_SoundAliasIndex registers in CS_SOUNDS and truncates to a byte, so an
 * exhausted bank returns 0 rather than a usable slot. */
static int register_alias(const char *alias)
{
    int sound=G_SoundAliasIndex(alias);
    return sound>0 && sound<=255 ? sound : 0;
}
/* C1 gates every event producer on a counter at gentity+0x1c4. G_AddEvent
 * 0x572d30 compares it with 4 before queueing and increments it at 0x572e0d
 * after, including for a zero event; nine further sites inline the same gate
 * (0x536185, 0x536367, 0x544416, 0x5446f6, 0x544ad6, 0x54cc6d, 0x559778,
 * 0x5751b5, 0x57af5e, plus the sound helper 0x5730cf). Over the limit a
 * non-client entity returns at once, the footstep events 0x74..0x77 return,
 * and the remaining path scans the last four queue slots for an identical
 * (event, parameter) pair - but both outcomes of that scan return, so the scan
 * only selects which path a debug build would report from.
 *
 * Lifecycle, as far as the image proves it: the counter is cleared by the
 * whole-gentity memset in G_FreeEntity (0x572b78), and G_Spawn (0x572590)
 * refuses to reuse a slot freed under 500 ms ago. No further native writer
 * exists - checked for direct displacements, for entity iterators based at
 * any offset of the entity array, and for every memset in the game module,
 * of which only G_FreeEntity's spans the counter. That is not proof of
 * absence: C1 never writes level.time natively either (505 reads, no writes),
 * so its frame advance is virtualized and a reset could live there.
 * The routines below are an UNINTEGRATED draft: there is no caller of
 * CODOL_EntityEventAllowed in the retained producer. Entity-free reset alone
 * does not establish the complete lifecycle and must not be wired as a
 * lifetime limit. The real event rings and sequence epochs remain independent. */
static unsigned char entity_event_count[MAX_GENTITIES];
static unsigned entity_event_drops;
unsigned CODOL_EntityEventDrops(void) { return entity_event_drops; }
int CODOL_EntityEventPending(const gentity_t *entity)
{
    unsigned number;
    if(!entity) return 0;
    number=(unsigned)entity->s.number;
    if(number>=MAX_GENTITIES) return 0;
    return entity_event_count[number]<CODOL_ENTITY_EVENT_LIMIT;
}
int CODOL_EntityEventAllowed(gentity_t *entity, int event)
{
    unsigned number;
    (void)event;
    if(!entity) return 1;
    number=(unsigned)entity->s.number;
    if(number>=MAX_GENTITIES) return 1;
    if(entity_event_count[number]>=CODOL_ENTITY_EVENT_LIMIT) { ++entity_event_drops; return 0; }
    ++entity_event_count[number]; return 1;
}
/* The tail of C1 0x5730c0, entered with the alias already registered because
 * C1's playsound dispatch registers the index itself at 0x54d2e9 and hands the
 * byte to this helper in cl. Split out so the notification arm can run between
 * the two the way C1 orders them. */
static int queue_sound_event(gentity_t *entity, int sound, int as_master)
{
    /* C1 0x5730c0 begins by clearing the receiver's hidden flag - before the
     * index is even tested (0x5730c7) - because a queued event on an entity
     * the snapshot skips is never transmitted. The same byte its StopSounds
     * clears at 0x53617e; identified as svFlags bit 0 from C1's own
     * hidden-entity producers (info_volume spawn 0x52dd11 sets it, the visible
     * spawn 0x567981 clears it) and from IW4's equivalents at +0x102
     * (spectator transition 0x5d7952 sets it, accessor 0x46932c returns its
     * complement). Retained SVF_NOCLIENT is the same bit, tested by
     * SV_AddCachedEntitiesVisibleFromPoint and its live twin. */
    entity->r.svFlags&=~SVF_NOCLIENT;
    if(sound<=0) return 0;
    /* The native event rings own admission. The separate, unintegrated C1
     * quota draft has no established frame reset and must not gate playback. */
    /* C1 writes the index straight into the event queue parameter, on the
     * player state when the entity has a client and on the entity state
     * otherwise (0x573131 and 0x573161); retained G_AddEvent splits exactly
     * the same way, so the CoDOL player event epoch bookkeeping is preserved. */
    G_AddEvent(entity,as_master ? EV_SOUND_ALIAS_AS_MASTER : EV_SOUND_ALIAS,sound);
    return 1;
}
int CODOL_PlaySoundOnEntity(gentity_t *entity, const char *alias, int as_master, unsigned *index)
{
    int sound;
    if(!entity || !alias || !*alias) return 0;
    if(!(sound=register_alias(alias))) { entity->r.svFlags&=~SVF_NOCLIENT; return 0; }
    if(index) *index=(unsigned)sound;
    return queue_sound_event(entity,sound,as_master);
}
int CODOL_EmitSoundAlias(const float origin[3], const char *alias, int parent,
                         int as_master, unsigned *index)
{
    gentity_t *event;
    int sound;
    if(!origin || !alias || !*alias ||
       (parent!=CODOL_SOUND_NO_PARENT && (parent<0 || parent>=ENTITYNUM_WORLD))) return 0;
    if(!(sound=register_alias(alias))) return 0;
    event=G_TempEntity(origin,as_master ? EV_SOUND_ALIAS_AS_MASTER : EV_SOUND_ALIAS);
    if(!event) return 0;
    event->s.eventParm=sound;
    /* The owning entity travels in otherEntityNum, biased by one so that a
     * zero left there by a retained producer still means "no owner": entity 0
     * is a real player, and the wire sentinel C1 writes for unowned sounds is
     * 2046. The snapshot overlay removes the bias. */
    event->s.otherEntityNum=parent==CODOL_SOUND_NO_PARENT ? 0 : parent+1;
    /* Retained ScrCmd_PlaySound sets the same bit on its temp entity
     * (_g_scr_main_mp.asm ScrCmd_PlaySound, r.svFlags |= 8), which
     * SV_AddCachedEntitiesVisibleFromPoint and its live twin treat as
     * "send regardless of PVS" through their svFlags & 0x18 test. */
    event->r.svFlags|=8;
    if(index) *index=(unsigned)sound;
    return 1;
}
/* C1 0x73d250 resolves a playing length from the "sound/soundlength.csv"
 * string table: asset type 37, looked up in column 0 and read from column 1,
 * parsed by the atoi thunk 0xada2a7 (strtol base ten) whose integer result the
 * caller compares with zero at 0x573073 before substituting 2000 ms. The
 * shipped table, in localized_code_post_gfx_mp.ff, has two columns and 23730
 * rows of integer milliseconds. */
int CODOL_SoundAliasLengthMsec(const char *alias)
{
    const codol_engine_table_t *table=NULL; int row;
    if(!alias || !*alias) return CODOL_SOUND_DEFAULT_MSEC;
    if(CODOL_LoadEngineStringTable("sound/soundlength.csv",&table)!=1 || !table ||
        table->columnCount<2 || table->rowCount<1 || !table->values) return CODOL_SOUND_DEFAULT_MSEC;
    /* C1 StringTable_LookupRowNum61ed00 starts at rowCount-1 and searches
     * backward, so later rows override earlier occurrences of an alias. */
    for(row=table->rowCount-1;row>=0;--row) {
        const char *name=table->values[(size_t)row*table->columnCount];
        const char *length;
        long msec;
        if(!name || Q_stricmp(name,alias)) continue;
        length=table->values[(size_t)row*table->columnCount+1];
        /* C1 73d2ac -> ada2a7 -> ada291 passes (text, NULL, 10)
         * to its 32-bit strtol. Preserve that range on wider host builds. */
        msec=length ? strtol(length,NULL,10) : 0;
        /* C1 573073/573075 substitutes only zero. Negative table values
         * survive and place the deadline before the current engine time. */
        if(msec==0) return CODOL_SOUND_DEFAULT_MSEC;
        if(msec>INT32_MAX) return INT32_MAX;
        if(msec<INT32_MIN) return INT32_MIN;
        return (int)msec;
    }
    return CODOL_SOUND_DEFAULT_MSEC;
}
/* C1 keeps one pending completion notification per entity: the deadline at
 * gentity+0x24c (level.time plus the length above), the script string at
 * +0x254 with a reference held on it (0x572e54 adds, 0x57300a releases), the
 * sound index at +0x256 and the third script parameter at +0x257 (a word at
 * +0x250 is zeroed beside them at 0x57308c; nothing else in the image touches
 * it, so it is not modelled here).
 * The pending string is script-visible: the two builtins 0x55aae0 and 0x55ab20
 * do nothing but GetEntity, test word [ent+0x254] against zero and return the
 * inverted flag through Scr_AddBool 0x5ce690, so a "is a playsound
 * notification outstanding" query exists in C1's own method table. Their names
 * are not recoverable - C1's builtin table entries at 0xcd3734.. are
 * {function, flags, name} triples whose name pointer is the same stripped
 * placeholder 0xc2fead for every entry - so no method is registered for them
 * here.
 * No native reader of the *deadline* was found: of the three .text words
 * holding 0x24c, 0x567236 and 0x58d085 are mid-instruction matches and
 * 0x5730a3 is the writer above. That does not establish that none exists: C1
 * writes level.time nowhere in native code either, so its frame advance is
 * virtualized and a consumer may live there. Neither IW4 nor T5 has a
 * notification form of playsound to copy a firing rule from, so the firing
 * below is this server's, built on the deadline C1 itself computes. */
typedef struct {
    uint32_t deadline;
    unsigned short notify;
    unsigned char sound, suppress, active;
} sound_notification_t;
static sound_notification_t sound_notifications[MAX_GENTITIES];
static const char *sound_index_name(unsigned index)
{
    static char name[MAX_STRING_CHARS];
    if(!index || index>255) return "";
    SV_GetConfigstring(CS_SOUNDS+index,name,sizeof(name));
    return name;
}
/* Never hands a null to %s the way C1's own va call does. */
static const char *sound_string_name(unsigned short string, const char *unset)
{
    const char *text;
    if(!string) return unset;
    text=SL_ConvertToString(string);
    return text ? text : unset;
}
/* C1 0x572e30, entered with ecx = the notification string, esi = the receiving
 * entity, [ebp+8] = the registered sound index and [ebp+0xc] = the third
 * playsound parameter. Returns 0 when it threw, so the caller stops before
 * queueing the event - which is what C1 does too, since its throw at 0x572fde
 * unwinds out of the dispatch before the play call at 0x54d331. */
static int arm_notification(gentity_t *entity, unsigned short notify, unsigned sound,
                            unsigned suppress, const char *alias)
{
    unsigned number=(unsigned)entity->s.number;
    sound_notification_t *pending;
    if(number>=MAX_GENTITIES) return 1;
    pending=sound_notifications+number;
    /* C1's exact branches: 0x572e6d goes straight to the store when nothing is
     * pending; 0x572e7a takes the report when the *stored* parameter is zero;
     * only when it is non-zero does 0x572e82 let a non-zero new parameter skip
     * it. So both registrations must pass a non-zero third parameter to
     * silence it.
     *
     * This is a script error, not a warning: 0x572fab builds the text with va
     * 0x6286d0, stores it into the error buffer at 0x27d1488 exactly like the
     * unknown-alias site, and throws through 0x5cd3a0 - but unlike the alias
     * sites it leaves the parameter-index word 0x278a014 untouched, which is
     * the plain Scr_Error form. C1 releases the reference it took on the new
     * string (0x572f0e) before throwing, so nothing is stored and no sound is
     * played. The message text and its argument order are C1's, with two
     * deliberate divergences: C1 passes a null pointer for "new string"
     * (ebx is zero at 0x572f7d, cleared with the saved string at 0x572f23)
     * and a null for a classname it cannot resolve, and this build prints the
     * names instead of relying on a printf that tolerates null. */
    if(pending->active && (!pending->suppress || !suppress)) {
        Scr_Error(va("issued a second playsound with notification string before the first "
            "finished on entity %i classname %s targetname %s location %g %g %g "
            "old string %s alias %s new string %s alias %s at time %i\n",
            entity->s.number,
            sound_string_name(entity->classname,"<undefined>"),
            sound_string_name(entity->targetname,"<undefined>"),
            entity->r.currentOrigin[0],entity->r.currentOrigin[1],entity->r.currentOrigin[2],
            sound_string_name(pending->notify,"<undefined>"),sound_index_name(pending->sound),
            sound_string_name(notify,"<undefined>"),alias,level.time));
        return 0;
    }
    /* C1 retains the replacement before releasing the old string (572e54,
     * 572ff8,57300b,573022), including replacement with the same string.
     * Zero is an absent string and never receives a reference. */
    if(notify) SL_AddRefToString(notify);
    if(pending->active && pending->notify) SL_RemoveRefToString(pending->notify);
    pending->notify=notify; pending->sound=(unsigned char)sound;
    pending->suppress=(unsigned char)suppress;
    /* 0x57306e reads the length of the *registered alias name* and 0x573073
     * substitutes 2000 ms for a zero, then 0x573098 adds level.time. This is
     * the alias's own playing length, not a fixed duration. */
    pending->deadline=(uint32_t)level.time+
        (uint32_t)CODOL_SoundAliasLengthMsec(sound_index_name(sound));
    pending->active=notify!=0;
    return 1;
}
void CODOL_RunSoundFrame(int time)
{
    unsigned i;
    for(i=0;i<MAX_GENTITIES;++i) {
        sound_notification_t *pending=sound_notifications+i;
        unsigned short notify;
        /* Engine time wraps at 32 bits. Table lengths are signed milliseconds;
         * ordinary negative lengths therefore produce an already-due time.
         * Exact C1 frame ordering and the half-range boundary remain unverified. */
        if(!pending->active || (uint32_t)((uint32_t)time-pending->deadline)>=0x80000000u) continue;
        notify=pending->notify;
        pending->active=0; pending->notify=0;
        /* The receiver may have been freed or reused while the sound played;
         * only an entity still in use is notified, and the reference is
         * released either way. */
        if(g_entities[i].r.inuse && notify) Scr_Notify(&g_entities[i],notify,0);
        if(notify) SL_RemoveRefToString(notify);
    }
}
void CODOL_ResetEntitySoundState(unsigned entity)
{
    sound_notification_t *pending;
    if(entity>=MAX_GENTITIES) return;
    pending=sound_notifications+entity;
    if(pending->active && pending->notify) SL_RemoveRefToString(pending->notify);
    memset(pending,0,sizeof(*pending));
    /* C1 clears the event counter with the same whole-entity memset. */
    entity_event_count[entity]=0;
}
void CODOL_ResetSoundState(void)
{
    unsigned i;
    for(i=0;i<MAX_GENTITIES;++i) {
        CODOL_ResetEntitySoundState(i);
    }
    entity_event_drops=0;
}
/* C1 0x54cf30 and IW4 0x5f6890 validate the loaded alias before touching the
 * sound bank, and both report through the *parameter zero* error form no
 * matter which parameter the caller read the alias from, because one shared
 * helper serves every entry point:
 *   C1 0x54cf83 and 0x54cfd1 build the message with va 0x6286d0 and throw
 *   through 0x5cd3a0, having first stored 1 into the error-parameter word at
 *   0x278a014; retained Scr_ParamError stores paramNum+1 into gScrVarPub+0x10
 *   (_scr_vm.asm Scr_ParamError_+0x8..+0x10), so that 1 is parameter zero.
 *   The neighbouring count error at 0x54d353 leaves the word untouched, which
 *   is the plain Scr_Error form - so the two forms really are distinct here.
 *   IW4 0x5f68a0 and 0x5f68c3 likewise pass a literal 0 as the first argument
 *   of 0x4fbc70 beside the same two message texts.
 * An empty alias is not a separate diagnostic in either engine: C1 0x54cf45
 * sends the empty string straight to the unknown-alias throw with a null asset
 * (0x54cf4a), and IW4's lookup 0x4b6490 returns null for it. The previous
 * "%s requires a sound alias name" text existed in neither image.
 * C1 additionally prints the asset-side report before throwing: 0x54cf67 calls
 * Com_PrintError 0x594540 - identified from its own "^1Error: " prefix at
 * 0x594572 - with "Missing soundalias \"%s\".\n". C1's channel number 12 is
 * its own console-channel enum and is NOT equated with this build's; the
 * severity is what carries over. C1 reaches that print when the asset lookup
 * resolves to the default asset, which is the state this loader represents by
 * finding no alias at all. */
static int check_alias(const char *alias)
{
    int looping=CODOL_SoundAliasIsLooping(alias);
    if(looping<0) {
        Com_PrintError(CON_CHANNEL_ERROR,"Missing soundalias \"%s\".\n",alias ? alias : "");
        Scr_ParamError(0,va("unknown sound alias '%s'",alias ? alias : ""));
        return 0;
    }
    if(looping) {
        Scr_ParamError(0,va("'%s' is a looping alias, use 'playloopsound' instead",alias));
        return 0;
    }
    return 1;
}
/* The failure message is this server's own: neither C1 nor T5 can fail here.
 * C1's G_SoundAliasIndex 0x570920 registers into the sound bank behind the
 * configstrings, and T5 0x694400 accepts a zero alias id and simply plays
 * nothing (0x69440f returns null). This build cannot take T5's silent path:
 * CODOL_OverlayEngineSoundEvent rejects a zero index, and the snapshot seed
 * in codol_sv_gameframe.c turns that rejection into a failed frame for every
 * client, so an unregisterable alias is reported to the script instead. */
static int emit_checked(const float *origin, const char *alias, int parent, const char *builtin)
{
    if(!CODOL_EmitSoundAlias(origin,alias,parent,0,NULL)) {
        Scr_Error(va("%s: unable to register sound alias '%s'",builtin,alias));
        return 0;
    }
    return 1;
}
/* Retained ScrCmd_PlaySound and ScrCmd_PlaySoundAsMaster spawn an unowned
 * temp entity at the receiver's origin and leave otherEntityNum zero, so their
 * sounds neither belong to the entity nor follow it. C1 plays an entity's own
 * sound through its event queue instead, which is what these replace them
 * with.
 *
 * C1's playsound dispatch is 0x54d1f0 and its whole body is reproduced here:
 *   0x54d1ff  entity  = GetEntity(entref)            (0x534a10)
 *   0x54d20e  alias   = Scr_GetString(0)             (0x5cded0)
 *   0x54d21e..0x54d2e4  the shared alias check below, both throws included
 *   0x54d2e9  index   = G_SoundAliasIndex(alias)     (0x570920, byte in al)
 *   0x54d2f0  count   = numParams
 *   0x54d2f7  count == 2 -> notify = Scr_GetConstString(1), third param 0
 *   0x54d301  count == 3 -> third param = Scr_GetInt(2) first, then the string
 *             any other count -> jne 0x54d32b, no notification at all
 *   0x54d323  arm_notification(notify, entity, index, third param)  (0x572e30)
 *   0x54d331  queue the event on the entity                         (0x5730c0)
 * So C1 has no parameter-count error for playsound: one parameter, or four and
 * more, simply play the sound without registering a notification. */
static void play_sound_method(scr_entref_t ref, int as_master, const char *builtin, int notify_form)
{
    gentity_t *entity=VM_GetGEntityForEntRef(ref);
    const char *alias;
    int sound, count;
    if(!entity) return;
    alias=Scr_GetString(0);
    if(!check_alias(alias)) return;
    /* C1 registers the index before it looks at the parameter count, and hands
     * the same index to both the notification arm and the event queue. */
    if(!(sound=register_alias(alias))) {
        Scr_Error(va("%s: unable to register sound alias '%s'",builtin,alias));
        return;
    }
    count=Scr_GetNumParam();
    if(notify_form && (count==2 || count==3)) {
        /* 0x54d303 reads the integer parameter before 0x54d312 reads the
         * string, and the arm throws on an unfinished previous notification -
         * in which case no event is queued. */
        unsigned suppress=count==3 ? (unsigned)Scr_GetInt(2) : 0;
        unsigned short notify=(unsigned short)Scr_GetConstString(1);
        if(!arm_notification(entity,notify,(unsigned)sound,suppress,alias)) return;
    }
    queue_sound_event(entity,sound,as_master);
    if(!notify_form && count!=1)
        /* IW4 0x5f6933 and 0x5f6be3 check the count only after the sound has
         * been played, and report through Scr_Error. */
        Scr_Error(va("%s has %d parameters.  There should be exactly one.",builtin,count));
}
void CODOL_Scr_PlaySound(scr_entref_t ref) { play_sound_method(ref,0,"playsound",1); }
void CODOL_Scr_PlaySoundAsMaster(scr_entref_t ref)
{
    gentity_t *entity;
    const char *alias;
    int count;
    cvar_t *probe=Cvar_FindVar("r_reflectionProbeGenerate");
    if(!probe) probe=Cvar_RegisterBool("r_reflectionProbeGenerate",qfalse,0,
        "Generate cube maps for reflection probes.");
    /* IW4 registration518970 names dvar66e60fc r_reflectionProbeGenerate,
     * default false, flags0. Probe generation skips even receiver validation.
     * The enabled producer is exactly the same helper as playsound5f6900:
     * 5f6890 emits an unowned positional temp entity with event3 at5f68e6.
     * There is no event4 or receiver event-queue write in this path. */
    if(probe && probe->boolean) goto check_count;
    entity=VM_GetGEntityForEntRef(ref);
    if(!entity) return;
    alias=Scr_GetString(0);
    if(!check_alias(alias)) return;
    if(!CODOL_EmitSoundAlias(entity->r.currentOrigin,alias,
            CODOL_SOUND_NO_PARENT,0,NULL)) {
        Scr_Error(va("playsoundasmaster: unable to register sound alias '%s'",alias));
        return;
    }
check_count:
    count=Scr_GetNumParam();
    if(count!=1)
        Scr_Error(va("playsoundasmaster has %d parameters.  There should be exactly one.",count));
}
/* playsoundatpos(<origin>, <alias>), a global function in every image checked:
 * IW4's table entry at .data 0x79aa8c is {"playsoundatpos", 0x5f6960, 0} in the
 * function table, and the CoDOL alpha registers the name the same way.
 *
 * Parameter order is IW4's and C1's alike. IW4 0x5f6986 calls Scr_GetVector
 * 0x411560 with index 0 and Scr_GetString 0x425900 with index 1; C1 0x54d393
 * calls its Scr_GetVector 0x5cdfe0 with index 0 in eax and its Scr_GetString
 * 0x5cded0 with index 1, then hands both to the positional helper 0x54cf30.
 *
 * The count rule is where the two diverge, and C1 wins because C1 is the
 * client this server serves: IW4 0x5f6968 demands exactly two ("cmp eax, 2 /
 * je") and reports "playsoundatpos needs 2 parameters - you had %i
 * parameters" at 0x6f25e0, while C1 0x54d34e accepts two or more ("cmp eax, 2
 * / jae") and reports "playsoundatpos needs at least 2 parameters - you had %i
 * parameters" at 0xc58e48. Extra parameters are ignored: the helper only reads
 * a third one when its notification-entity argument is non-null (0x54d048),
 * and this call site passes null there (0x54d3ac). Neither engine returns a
 * value - C1 discards the temp entity the helper returns in eax. */
void CODOL_Scr_PlaySoundAtPos(void)
{
    vec3_t origin; const char *alias;
    if(Scr_GetNumParam()<2) {
        Scr_Error(va("playsoundatpos needs at least 2 parameters - you had %i parameters",
            Scr_GetNumParam()));
        return;
    }
    Scr_GetVector(0,origin);
    alias=Scr_GetString(1);
    if(!check_alias(alias)) return;
    emit_checked(origin,alias,CODOL_SOUND_NO_PARENT,"playsoundatpos");
}
/* playsoundatposition(<alias>, <origin>) - the T5 spelling, also a global
 * function: T5's table entry at .data 0xe08b4c is {"playsoundatposition",
 * 0x647d70, 0} and the map names 0x647d70 Scr_PlaySoundAtPosition in
 * g_scr_main_mp.obj. Its script-facing contract is followed exactly:
 * Scr_GetNumParam 0x8de4e0 must be 2 (0x647d80 "cmp eax, 2 / je"), otherwise
 * Scr_Error 0x8def20 with "playsoundatposition has %d parameters.  There
 * should be two." at 0xcc3378; Scr_GetString 0x8ddd40 reads parameter 0 and
 * Scr_GetVector 0x8ddf50 parameter 1; nothing is returned.
 *
 * The producer contract is NOT T5's, because the receiving client is C1.
 * T5 resolves the name with SND_FindAliasId 0x93c3a0 and hands the resulting
 * 32-bit id to G_PlaySoundAliasAtPoint 0x694400, which stores that id whole in
 * entityState +0x7c, sets the broadcast flag byte at +0xe2 and writes its own
 * no-owner sentinel 1022 to +0xc4. Native transport translates the alias name
 * into C1's configstring bank and positional event instead of these offsets.
 * Parent traced93c3a0 through955ca0: the ID is a string hash, not proof of a
 * loaded asset. Every nonempty name hashes to a nonzero ID; an empty name
 * yields zero and694400 emits nothing. No unknown/looping-alias script error
 * is introduced. G_SoundAliasIndex registers names without asset validation. */
void CODOL_Scr_PlaySoundAtPosition(void)
{
    vec3_t origin; const char *alias;
    if(Scr_GetNumParam()!=2) {
        Scr_Error(va("playsoundatposition has %d parameters.  There should be two.",
            Scr_GetNumParam()));
        return;
    }
    /* T5 reads vector1 before string0, including their error order. */
    Scr_GetVector(1,origin);
    alias=Scr_GetString(0);
    if(!*alias) return;
    emit_checked(origin,alias,CODOL_SOUND_NO_PARENT,"playsoundatposition");
}
/* <entity> playsoundontag(<alias>[, <tag>]) - T5 Scr_PlaySoundOnTag 0x6476d0,
 * read instruction by instruction:
 *   0x6476e8  entity  = GetEntity(entref)                    (0x643f30)
 *   0x647703  aliasId = 0 and tagName = 0 unless the count allows them
 *   0x64770b  count >= 1 -> aliasId = SND_FindAliasId(Scr_GetString(0))
 *   0x647732  count >= 2 -> tag = Scr_GetConstString(1) (0x8ddb70)
 *   0x64774a  the tag is compared against one script constant; only a tag that
 *             differs from it is validated, so the constant is the tag-less
 *             spelling and it is passed through with tagName resolved anyway
 *   0x64775e  SV_DObjGetBoneIndex(entity, tag) < 0 ->
 *             SV_DObjDumpInfo(entity) then Scr_ParamError(1,
 *             "tag '%s' does not exist on entity with model '%s'") - a throw,
 *             so nothing is played
 *   0x6477c4  tagName = G_TagIndex(Scr_GetString(1))         (0x690980)
 *   0x6477d8  entity and aliasId both non-zero -> play (0x694460)
 * A missing alias parameter, an empty alias name and a count below one all
 * leave aliasId zero and play nothing, without an error. Following the ruling
 * already applied to playsoundatposition, no unknown-alias or looping-alias
 * error is introduced for a T5-spelled builtin: SND_FindAliasId 0x93c3a0 is a
 * name hash and validates no asset, so T5 cannot produce one. */
void CODOL_Scr_PlaySoundOnTag(scr_entref_t ref)
{
    gentity_t *entity=VM_GetGEntityForEntRef(ref);
    const char *alias; unsigned int tag; vec3_t origin;
    if(!entity) return;
    if(Scr_GetNumParam()<1) return;
    alias=Scr_GetString(0);
    if(!*alias) return;
    VectorCopy(entity->r.currentOrigin,origin);
    if(Scr_GetNumParam()>=2 && (tag=Scr_GetConstLowercaseString(1))!=0) {
        /* T5 validates with the bone index and reports with the model name,
         * dumping the DObj first so the offending model's tag list reaches the
         * log; the retained twins carry the same contract. */
        if(SV_DObjGetBoneIndex(entity,tag)<0) {
            SV_DObjDumpInfo(entity);
            Scr_ParamError(1,va("tag '%s' does not exist on entity with model '%s'",
                SL_ConvertToString(tag),SL_ConvertToString(G_ModelName(entity->model))));
            return;
        }
        /* The bone exists, so this only fails when the entity carries no DObj
         * at all this frame; T5 would still play, at the entity's position. */
        G_DObjGetWorldTagPos(entity,tag,origin);
    }
    /* T5's consumer settles the semantics: its sound event carries the owner
     * at entityState+0xc4 and the tag at +0x98, and the handler (0x4b1cc0,
     * tag arm at 0x4b5ca1) resolves that pair through the owner's DObj once,
     * when the sound starts, using the resulting world position - reporting
     * "playsoundontag could not find dobj for ent %d" or "... could not find
     * tag %s on ent %d" when it cannot. It is a one-shot resolution, not a
     * continuous attachment. C1's event has no tag word for any producer to
     * write, so this resolves the same pair server side at emission.
     *
     * The event is emitted unowned. C1's only two writers of the owner field
     * are its positional helper 0x54d03e and its stop-sound producer, and the
     * helper stores the no-owner sentinel 0x7fe unconditionally - no C1
     * producer ever puts a real entity number into a sound event, so what its
     * client does with one is unestablished. Naming the receiver there would
     * risk the client re-anchoring the sound on the entity origin and
     * discarding the tag position resolved just above, which is the one thing
     * T5's one-shot resolution guarantees it plays at. */
    emit_checked(origin,alias,CODOL_SOUND_NO_PARENT,"playsoundontag");
}
void CODOL_Scr_StopSounds(scr_entref_t ref)
{
    gentity_t *entity=VM_GetGEntityForEntRef(ref);
    if(!entity) return;
    /* IW4 0x5ecbac and C1 0x536136 both refuse event entities, whose state has
     * no sound to stop; both then queue the stop event with parameter zero and
     * consume no script parameters. */
    if(entity->s.eType>=ET_EVENTS) {
        Scr_Error(va("StopSounds() does not support entities of type 'ET_EVENTS' [Ent #%i].",
            entity->s.number));
        return;
    }
    /* Both engines clear the receiver's hidden bit before queueing, so a
     * hidden entity's stop event still reaches the clients that are playing
     * its sounds: C1 0x53617e on svFlags at +0x116, IW4 0x5ecbc8 at +0x102. */
    entity->r.svFlags&=~SVF_NOCLIENT;
    G_AddEvent(entity,EV_STOPSOUNDS,0);
}
/* soundAliasSubtitle(<alias>): see codol_script_sound.h. Reservoir sampling
 * keeps the choice uniform over subtitled variants in one pass. A subtitle
 * with a quote or line break is never offered, so the result can always be
 * handed to setClientSubtitle's quoted ']' argument. */
void CODOL_Scr_SoundAliasSubtitle(void)
{
    const snd_alias_list_t *list;
    const char *alias,*pick=NULL;
    unsigned i,seen=0;
    alias=Scr_GetString(0);
    list=CODOL_FindEngineSoundAlias(alias);
    if(!list || !list->head) return;
    for(i=0;i<(unsigned)list->count;++i) {
        const char *subtitle=list->head[i].subtitle;
        if(!subtitle || !*subtitle || strpbrk(subtitle,"\"\r\n")) continue;
        ++seen;
        if(!(rand()%seen)) pick=subtitle;
    }
    if(pick) Scr_AddString(pick);
}
#endif

