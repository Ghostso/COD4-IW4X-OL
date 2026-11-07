/* CoDOL playerState extension: state that C1 keeps inside its playerState and
 * the retained IW3 playerState_t has no room for.
 *
 * Why this exists
 * ---------------
 * C1 stores the fire-recoil scale magnitude at ps+0x3330 (write
 * Scr_PlayerRecoilScaleOn 0x00519839, read BG_WeaponFireRecoil 0x004222c6);
 * IW4 keeps the same value at ps+0x3110. Because it is *in* the playerState,
 * every copy those engines make - archive, spectator follow, snapshot - carries
 * the value, and a spectator watching a delayed playerState sees the magnitude
 * that was armed at that moment, not the one the followed player has now.
 *
 * The retained IW3 playerState_t is exactly 0x2f64 bytes and gclient_s is
 * exactly 0x3184 (G_InitGame strides g_clients by 0x3184 in
 * _g_main_mp.asm:619, over the 0xc6100 reservation at _g_main_mp.asm:1806);
 * every gclient member after the playerState is addressed by hardcoded offset
 * in the retained assembly (for example client+0x3158 = vGunSpeed in
 * G_PlayerEvent). Widening playerState_t would move all of them, so the
 * extension is stored beside each playerState instead of inside it.
 *
 * The model
 * ---------
 * Every playerState that can carry extension state lives in one of three fixed
 * arrays, and its extension block is found from the address of the storage -
 * never from ps->clientNum, which names the player the state describes and is
 * not an identity (a spectator's own playerState carries the followed player's
 * clientNum after SpectatorClientEndFrame copies it in):
 *
 *   live      level.clients[i].ps               the gclient state
 *   snapshot  svs.clients[i].frames[j].ps       what the CoDOL writer serializes
 *   archive   svs.cachedSnapshotClients[k].ps   the delayed history
 *
 * There is no fourth, address-keyed "transient" class. The two paths that copy
 * a playerState through a scratch buffer carry the extension explicitly
 * instead, as a value:
 *
 *   SV_ArchiveSnapshot's local playerState  - the extension written to the
 *       archive stream is taken from the live client being serialized, at the
 *       serialization site, so the scratch buffer never has to hold it.
 *   SpectatorClientEndFrame's stack playerState - the retained frame now also
 *       holds a codol_ps_ext_t, filled by SV_GetArchivedClientInfo through its
 *       out-parameter and applied to the spectator's own storage by
 *       CODOL_PlayerStateExtApply after the retained memcpy.
 *
 * Actual callers (all of them, after the archive patch):
 *   CODOL_PlayerStateExt        codol_recoil_state.c (arm), and through
 *                               CODOL_PlayerStateExtConst the recoil consumer
 *                               and the snapshot overlay
 *   CODOL_PlayerStateExtCopy    SV_BuildClientSnapshot (live -> snapshot frame)
 *   ...CopyFromClient           SV_ArchiveSnapshot's full arm (live -> archive
 *                               slot)
 *   ...Fetch / ...FetchFromClient, ...Apply
 *                               SV_GetArchivedClientInfo (archive or live ->
 *                               caller's bundle) and SpectatorClientEndFrame
 *                               (bundle -> spectator storage)
 *   ...Clear                    the arms that leave a storage without a
 *                               playerState
 *   ...ClearClientRecoil        CODOL_ResetPlayerRecoilScale, i.e. ClientSpawn's
 *                               gclient memset and the connect/disconnect reset
 *   ...ClearClientLock          CODOL_ResetClientWeaponLock, from the same two
 *                               lifecycle sites; neither clear touches the
 *                               other subsystem's field
 *   ...ClearClientHudIcons      ClientSpawn's gclient memset and the
 *                               connect/disconnect reset, for the published
 *                               copy of the weapon HUD icon overrides
 *   ...ClearClientInventory     the same two sites, for the four relocated
 *                               per-weapon arrays the gclient memset used to
 *                               zero in place
 *   ...SetClientHudIcons        the per-frame publisher
 *                               (codol_hud_icon_overrides.c), from the
 *                               retained ClientEndFrame playing path
 *   ...ClearArchive             SV_InitArchivedSnapshot
 *   ...ClearAll                 the map/game reset (CODOL_ResetGameInput),
 *                               which does mean every field of every storage
 *   ...LockRead                 the snapshot writer (codol_sv_gameframe.c), the
 *                               fire gate (codol_weapon_lock_fire.c) and the
 *                               missile launch (codol_weapon_lock_missile.c)
 *   ...LockMutable              the weapon-lock script methods
 *   ...Write* / ...Read*        SV_ArchiveSnapshot / SV_GetCachedSnapshotInternal
 *
 * Archive stream record
 * ---------------------
 * svs.archivedSnapshotBuffer is server-internal memory: SV_ArchiveSnapshot
 * writes it (sv_snapshot.c:1344) and only SV_GetCachedSnapshotInternal reads it
 * back, so extending that format costs nothing on the client wire. One record
 * follows every archived playerState, in both the full and the delta arm:
 *
 *   recoil  1 bit  0 = identical to this playerState's own delta baseline (or
 *                     to "no magnitude" when the playerState had no baseline)
 *                 1 = followed by 1 bit "recorded" and 7 bits percentage
 *   lock    1 bit  0 = identical to the same baseline (or to the reset lock)
 *                 1 = followed by 1 bit "recorded"; when recorded, 7 bits
 *                     flags, 11 bits entity, three 32-bit position words and
 *                     three 32-bit missile-offset words
 *   hand    1 bit  0 = identical to the same baseline (or to the empty hand)
 *                 1 = followed by 1 bit "recorded" and the hand block
 *   loop    1 bit  0 = identical to the same baseline (or to "no loop sound")
 *                 1 = followed by 1 bit "recorded" and 8 bits of sound-bank
 *                     index, the width C1 gives ps+0x1f4 and IW4 gives
 *                     ps+0x190
 *   icons   1 bit  0 = identical to the same baseline (or to "no override in
 *                     any slot")
 *                 1 = followed by eight 8-bit native material configstring
 *                     indices, the width the retained CS_MATERIALS range needs.
 *                     There is no "recorded" bit: an unset slot and a slot
 *                     holding 0 are the same state in both engines - no
 *                     override - so a zeroed block is already the right value
 *   events  1 bit  0 = identical to the same baseline (or to "no epoch")
 *                 1 = followed by 1 bit "recorded"; when recorded, 1 bit for
 *                     the short form - 4 bits of epoch-minus-baseline in
 *                     1..16 - or the 32-bit epoch itself
 *   perks   1 bit  0 = identical to the same baseline (or eight empty slots)
 *                 1 = followed by eight 32-bit numeric perk IDs. Located
 *                     after the ability block and before the scripted queue;
 *                     server-internal representation, not client netfields.
 *   script  1 bit  0 = identical to the same baseline (or to "no queue")
 *                 1 = followed by 1 bit "recorded"; when recorded, the 32-bit
 *                     epoch and the four slots as a 32-bit event and a 32-bit
 *                     parameter each. This record is internal, so it carries
 *                     the native values the producer stored; the eleven bits
 *                     C1's fields 0x120..0x12c and 0x130..0x13c carry are a
 *                     limit of the snapshot translation, applied there and
 *                     never before validation
 *   weapons 1 bit  0 = identical to the same baseline (or to "never recorded")
 *                 1 = followed by 1 bit "recorded"; when recorded, a 7-bit
 *                     count of owned weapons (at most 127; a larger set is
 *                     truncated and counted by
 *                     CODOL_PlayerStateExtInventoryTruncations) and, per owned
 *                     weapon in ascending order, 10 bits of native index, 1 bit
 *                     weaponold, 1 bit weaponrechamber and 8 bits of model.
 *                     The reader rebuilds all four arrays from zero, so an
 *                     unowned weapon carries no old/rechamber/model state.
 *                     Last in the record, after the scripted queue
 *
 * The record is written and read at exactly the points the playerState itself
 * is written and read, with exactly the same baseline, so a rebuilt cached
 * snapshot restores the state that was archived with it.
 */
#ifndef CODOL_PLAYERSTATE_EXT_H
#define CODOL_PLAYERSTATE_EXT_H
#include "codol_weapon_slots.h"   /* CODOL_WEAPON_SLOTS, CODOL_WEAPON_BIT_WORDS */
/* Every per-weapon array in this file is the full native table width.
 * C1 registers 700 weapon definitions (bg_weaponDefs 0x0150D720 is 700
 * pointers, BG_ClearWeaponDefs 0x0041F570 memsets 0xAF0, CG_Init 0x00450ADC
 * walks 1..699) and CS_WEAPONS is a 700-slot window, so 700 is the ceiling
 * the client can consume and the width this server publishes. The retained
 * IW3 playerState_t cannot hold them - it has 48 bytes at 0x55c for three
 * bitsets and 128 bytes at 0x81c for the models - so all four arrays live
 * here instead, and the retained assembly reaches them through
 * codol_weapon_bits.inc. Keying them to the *storage* rather than to
 * ps->clientNum is the whole reason they are in this block: a spectator
 * following a delayed player carries the followed player clientNum.
 * SpectatorClientEndFrame now reserves 2048 bytes for the bundle. */
#define CODOL_PS_EXT_WEAPON_BITS CODOL_WEAPON_SLOTS

#include "player.h"
#include "msg.h"
#include "codol_clients.h"
#include "codol_perks.h"
#include "codol_action_slots.h"
#include "codol_killstreak_hud.h"
#include "codol_radar_types.h"
#include "codol_player_links.h"
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif

/* IW4 keeps the weapon lock in the playerState too, next to everything else a
 * spectator has to see: PlayerCmd_WeaponLockFinalize (iw4x 0x5dd500) writes the
 * flags at ps+0x404 (0x40 selects the position target, 1 armed, 2 finalized),
 * the target entity at ps+0x408 and the position at ps+0x40c, and the missile
 * launch reads exactly those back from the owning client at 0x4a4f2b/0x4a4f19.
 * C1 transmits the same three through the measured playerState netfields
 * 0x48c/0x490/0x494..0x49c. The missile offset is the one server-side member:
 * IW4 stores it at client+0x3654 and the only reader is the missile launch
 * (0x4a4f52), never the wire. All four therefore belong to a *state*, not to a
 * client number, and travel with the playerState like the recoil magnitude. */
#define CODOL_PS_LOCK_NO_ENTITY 2047u
/* C1 indexes both event queues with (sequence & 3). */
#define CODOL_PS_SCRIPT_EVENT_SLOTS 4
/* C1's weapon HUD icon override slot table (0x00cd3958) has eight entries, and
 * the measured C1 playerState carries exactly eight consecutive 10-bit fields
 * for them at 0x56c..0x588. The vocabulary is in
 * codol_script_hud_notifications.h, which asserts the counts agree. */
#define CODOL_PS_HUD_ICON_SLOTS 8
/* C1's SetClientMaterial (0x0051ec30) types, in its table order (0x00cd9414):
 * "killcam_you" stores at ps+0x53c and "head_icon_self" at ps+0x540. */
#define CODOL_PS_CLIENT_MATERIAL_SLOTS 2
typedef struct {
    uint32_t flags;   /* 1 armed, 2 finalized, 4 direct / 8 top, 0x10 and 0x20
                       * warnings, 0x40 position target. Seven bits on the wire. */
    uint32_t entity;  /* 0..2046, CODOL_PS_LOCK_NO_ENTITY when none */
    float position[3];
    float missile_offset[3]; /* server-only: consumed at missile creation */
} codol_ps_lock_t;

/* The second weapon hand, its magazines, the fire records that name the hand
 * behind each queued event, and the spin-up charge.
 *
 * These are read by the snapshot writer from the playerState it is serializing,
 * so they have to travel with that playerState exactly like the recoil
 * magnitude: a spectator following a delayed player, and any frame built from
 * an older ring slot or from the archive, must see the hand as it was in that
 * state, not as the live client has it now. Keying them by ps->clientNum was
 * wrong for the same reason this file gives for the recoil magnitude, and a
 * spectator's own playerState carrying the followed player's clientNum makes
 * that failure quiet rather than absent.
 *
 * known 0 means nothing was ever recorded for this state, which is not the same
 * as a recorded idle hand: consumers see the reset hand instead. */
#define CODOL_PS_HAND_CLIPS 15
typedef struct {
    unsigned char known;
    unsigned char dual_wield, second_barrel, fresh_pull;
    unsigned char state, shot_count;
    unsigned char shot_hand;      /* One bit per event ring slot. */
    unsigned char shot_last;      /* One bit per event ring slot. */
    unsigned char shot_known;     /* One bit per event ring slot. */
    uint16_t weapon;              /* Native index, 0..699. */
    uint16_t primary_weapon;      /* The pair's primary for an alternate mode. */
    uint16_t animation;           /* Native weapAnim, restart bit included. */
    int16_t time, delay, restrict_time;
    uint16_t charge;              /* Spin-up charge, 0..1000. */
    uint32_t second_rechamber[CODOL_WEAPON_BIT_WORDS]; /* Inventory byte4, by native weapon. */
    uint32_t fast_mag[CODOL_WEAPON_BIT_WORDS]; /* C1 inventory byte2; alternates at ammo transfer. */
    unsigned char primary_reload_fast; /* Animation choice persists after transfer. */
    signed char clip_index[CODOL_PS_HAND_CLIPS]; /* -1 for an unused record. */
    int16_t magazine[CODOL_PS_HAND_CLIPS];    /* That record's second magazine. */
} codol_ps_hand_t;

/* The three selected offhand weapons.
 *
 * C1's PM_Weapon_CheckForOffHand does not search the inventory for an offhand
 * of a class. It reads one of three *selected* weapons out of the playerState
 * at 0x41cb5a, 0x41cb78 and 0x41cba2 -- ps+0x32c, ps+0x330 and ps+0x334 --
 * choosing between them with CoDOL command buttons 0x4000, 0x8000 and 0x10000.
 * Which offhand class belongs to which slot is measured separately, in the
 * helper at 0x40c7e0 that asks whether a weapon occupies one of the player's
 * slots: definition +0x354 (the retained offhandClass) 1 and 4 answer for the
 * first slot, 2 and 3 for the second and 5 for the third.
 *
 * These are 32-bit playerState wire fields (codol_player_fields.inc carries
 * 0x032c, 0x0330 and 0x0334). Their original server-side producers are not yet
 * established; absence of stores in .text is not proof of absence in C1's
 * virtualized code. They belong to a *state*, exactly like
 * the weapon hand beside them: a spectator following a delayed player and any
 * frame rebuilt from the archive must publish the selection that state carried.
 *
 * known 0 means no selection was ever recorded for this state, which is not
 * three empty slots. */
#define CODOL_OFFHAND_SLOTS 3
typedef struct {
    unsigned char known;
    unsigned char reserved;
    uint16_t weapon[CODOL_OFFHAND_SLOTS]; /* Native index; 0 = nothing selected. */
} codol_ps_offhand_t;

/* C1's second, server-side player event queue. G_AddEvent @0x00572d30 takes the
 * player branch at 0x00572da5 through ent->client (+0x17c) and writes
 * client+0x120[seq & 3] = event, client+0x130[seq & 3] = parm, then
 * client+0x118 = (seq + 1) & 0x7ff - a queue of four, a counter modulo 2048,
 * and no relation to the predicted queue at 0x0f0/0x0f4/0x104 that pmove fills.
 * Its non-player branch at 0x00572ddf writes the entity queue (ent+0xb0/+0xb4/
 * +0xc4) instead. The C1 client consumes both: CG_CheckPlayerstateEvents
 * @0x0045d680 replays the predicted queue at 0x45d6d0 and this one at
 * 0x45d744, each from the sequence it last received.
 *
 * The retained IW3 playerState has one queue, so the scripted one lives here
 * and travels with the state exactly like the rest of the block. */
typedef struct {
    /* Scripted events counted into this state; the wire field 0x118 carries
     * epoch modulo 2048, the same modulus C1's producer applies. */
    uint32_t epoch;
    /* Engine event ids and parameters as G_AddEvent received them, at their
     * native width: the wire translation maps and range-checks them, and the
     * internal archive record carries them unmodified. Slot is epoch & 3, as
     * in C1. */
    uint32_t events[CODOL_PS_SCRIPT_EVENT_SLOTS];
    uint32_t params[CODOL_PS_SCRIPT_EVENT_SLOTS];
    /* 0 when this state never had a scripted event. */
    unsigned char known;
    unsigned char reserved[3];
} codol_ps_script_events_t;

typedef struct {
    /* player_recoilScaleOn magnitude, 0..100. Meaningful only while the
     * playerState carries CODOL_WEAP_RECOIL_SCALE, exactly like C1's
     * ps+0x3330 next to weapFlags bit 0x400. */
    unsigned char recoil_percent;
    /* 0 when no magnitude was ever recorded for this state, which is not the
     * same as a recorded 0: a recorded 0 removes the recoil, an unrecorded one
     * must not, so consumers treat it as unscaled. Copies carry both. */
    unsigned char recoil_known;
    /* 0 when no lock was ever recorded for this state. A zeroed block must not
     * read as "locked onto entity 0": consumers see the reset lock instead. */
    unsigned char lock_known;
    /* 0 when this state never had an event counted into its epoch. */
    unsigned char event_known;
    codol_ps_lock_t lock;
    /* C1's scripted queue, filled by the retained G_AddEvent player branch. */
    codol_ps_script_events_t script;
    /* Predictable-event epoch: how many events the producers have added to this
     * playerState, without the 8-bit wrap the retained counter carries. The
     * retained producers keep ps->eventSequence = epoch & 0xff (see the
     * producer list in the .c), so the epoch is the same number the engine
     * counted, only wide enough to survive the wrap - and it belongs to the
     * state, so a copy, an archived frame and a spectator all carry the epoch
     * that state was produced with instead of a recipient-side accumulator. */
    uint32_t event_epoch;
    /* How much of the scripted queue has already been transferred to the entity
     * state, the equivalent of C1's cursor at ps+0x11c and of the retained
     * oldEventSequence for the predicted queue. Live bookkeeping only: it is
     * not part of the queue a snapshot or an archived state carries, and the
     * archive record does not encode it. */
    uint32_t script_transferred;
    /* The three selected offhands, and 0 when none was ever recorded. */
    codol_ps_offhand_t offhand;
    unsigned char offhand_known;
    /* 0 when no hand state was ever recorded for this playerState. */
    unsigned char hand_known;
    codol_ps_hand_t hand;
    /* The looping sound this state carries: C1 ps+0x1f4, IW4 ps+0x190, named
     * loopSound by IW4's own playerState netfield table (0x00742020 entry 149,
     * 8 bits). Both engines copy it into the entity state in every
     * BG_PlayerStateToEntityState (C1 0x0040d09d, IW4 0x0056e88a), so it is the
     * only place a player's loop sound survives a frame, and the local player
     * hears its own loop through this field rather than through an entity the
     * client synthesises from the playerState. 0 is silence, 1..255 is the same
     * sound bank index the entity field carries. */
    unsigned char loop_sound;
    /* 0 when no loop sound was ever recorded for this state. A recorded 0 and
     * an unrecorded state both play nothing, so this exists to keep copies and
     * archive records honest rather than to change what is heard. */
    unsigned char loop_known;
    /* The weapon HUD icon overrides this state carries: one native material
     * configstring index (relative to CS_MATERIALS) per slot, 0 for "no
     * override", in C1's slot order.
     *
     * This is the *published copy*, not the script's store. Both references
     * keep the script-owned array in the gclient - IW4 client+0x3264 (setter
     * 0x005f56d0, getter 0x005f57c0), C1 client+0x35ac - and copy it into that
     * client's own playerState once per frame: IW4 0x005d80bc moves
     * client+0x3264..0x3278 to ps+0x470..0x484 beside the radar flags. Only the
     * publisher in codol_hud_icon_overrides.c writes this half; the script
     * methods never touch it.
     *
     * That split is what makes following work, and it is not academic here:
     * SpectatorClientEndFrame copies the followed player's archived playerState
     * over the follower's and applies its extension with it, so a follower
     * carries - and serializes - the followed player's icons, while its own
     * script-owned array stays untouched. Keeping the script's values here
     * instead would lose them and make the getter answer for the followed
     * player.
     *
     * There is no "known" flag, unlike the loop sound: both engines start a
     * client with the array zeroed and treat 0 as the absence of an override
     * (the setter stores 0 for scr_const.none, the getter answers "none" for 0,
     * and C1's client consumer draws nothing), so an unrecorded state and a
     * recorded all-zero state are the same state. */
    uint16_t hud_icon[CODOL_PS_HUD_ICON_SLOTS];
    /* SetClientMaterial: one native material configstring index (relative
     * to CS_MATERIALS) per C1 type, 0 for none. C1 writes them straight into
     * the playerState (0x0051edbe: ent->client + 0x53c + type*4, G_MaterialIndex
     * 0x00570290), so unlike the HUD icon overrides there is no script-owned
     * half: a follower draws the followed player's materials, as in C1. The
     * client reads ps+0x540 as the local player's zombies HUD portrait
     * (0x00460652; 0 draws hud_character_soldier). Cleared with hud_icon. */
    uint16_t client_material[CODOL_PS_CLIENT_MATERIAL_SLOTS];
    /* C1 ps+544..554 types and +558..568 weapon IDs. Internal IDs stay
     * captured here; the snapshot publisher resolves their wire identities.
     * Archive block follows icons: changed bit, five (type2, weapon7) pairs. */
    codol_action_slots_t action_slots;
    codol_killstreak_hud_t killstreak_hud;
    codol_radar_types_t radar_types;
    /* Ability values follow the playerState through archive/spectator copies.
     * Unknown means no producer initialized defaults, not all defaults zero. */
    codol_client_abilities_t abilities;
    unsigned char abilities_known;
    /* C1 ps+4b0..4cc: eight numeric perk IDs; zero is an empty slot.
     * These travel with ps independently of ability masks and values. */
    codol_perk_state_t perks;
    /* Captured with this state, never fetched from a live client by a reader.
     * Includes the three weapon-view reference angle words. The internal
     * archive writes those as 32-bit words after cameraFlags; C1 receives
     * them through its existing angle netfields at 0x1e0..0x1e8.
     * Archive record after perks and before scripted events: changed bit,
     * known bit when changed, then mode2/offset1/linkWeapon11/camera11/tag6/controls11/flags8
     * and three 32-bit weapon-view angle words.
     * Native entity numbers are converted to C1 numbers only at publication.
     * Unknown must not be interpreted as a valid link to entity zero. */
    codol_ps_links_t links;
    unsigned char links_known;
    /* Binding for native ps.cursorHint-4, captured with that state. Zero is
     * unknown/non-weapon; otherwise wire weapon + 1 (2..701). Internal archive
     * stores changed bit and 10 bits after links, before scripted events. */
    uint16_t use_hint_weapon;
    /* Captured native weapon for C1 ps+40 throwback selection; zero is none.
     * Its wire identity is the same state's use_hint_weapon binding above. */
    uint16_t throwback_weapon;
    /* C1 ps+e4: corpse-info slot returned by the death clone producer. */
    unsigned char corpse_index;
    /* StunPlayer: C1 ps+0x3338 / IW4 ps+0x3118 stun end time (level.time + ms),
     * consumed by the weapon stun gate and published as wire field 0x3338. */
    int32_t stun_time;
    unsigned char stun_known;
    /* C1 ps+0x59c, consumed by CG_UpdatePoisonFX4775a0. */
    unsigned char poisoned;
    /* C1 ps+0x148: native model index for the separately composed gloves.
     * Arms remain in ps.viewmodelIndex (C1 +0x144). Captured/archive copies
     * own this value; a spectator must never read the live player's outfit. */
    uint16_t viewhands_model;
    /* C1 ps+0x234: completion time used by PM_UpdateStance's 100 ms
     * dive-to-prone lockout. Zero means no completed dive. */
    int32_t dive_end_time;
    /* C1 ps+0x333c (netfield 98, TIME): level.time of the last ClientSpawn,
     * stamped at the C1 ClientSpawn tail 0x50f9ad. PM_Weapon_CheckForChange
     * 0x41b109..0x41b14b ignores a usercmd weapon 0 for 200 ms after it. Zero
     * until the client first spawns. */
    int32_t spawn_time;
    /* The four per-weapon arrays the retained IW3 playerState_t holds at
     * 0x55c (weapons), 0x56c (weaponold), 0x57c (weaponrechamber) and 0x81c
     * (weaponmodels), relocated here at the full 700-slot native width. The
     * in-struct originals are dead: every retained assembly site that read
     * them now calls through codol_weapon_bits.inc, and a completeness check
     * greps the tree for any that do not. They are part of a *state*, like
     * everything else in this block, so a captured snapshot and an archived
     * history carry the inventory they were taken with.
     *
     * weapons_known 0 means nothing was ever recorded for this storage, which
     * is not the same as a recorded empty inventory; the archive codec uses it
     * to tell an absent record from an emptied one. */
    uint32_t weapons[CODOL_WEAPON_BIT_WORDS];
    uint32_t weaponold[CODOL_WEAPON_BIT_WORDS];
    uint32_t weaponrechamber[CODOL_WEAPON_BIT_WORDS];
    unsigned char weaponmodels[CODOL_WEAPON_SLOTS];
    unsigned char weapons_known;
} codol_ps_ext_t;

/* Set both native model indices together after profile model publication.
 * Zero clears a component. Snapshot translation resolves both model banks. */
int CODOL_PlayerStateSetViewmodels(playerState_t *,unsigned arms,unsigned hands);
void CODOL_PlayerStateExtClearClientViewhands(unsigned client);
void CODOL_PlayerStateExtClearClientPoison(unsigned client);
int CODOL_PlayerStateDiveEndTimeSet(const playerState_t *ps,int value);
int CODOL_PlayerStateDiveEndTimeRead(const playerState_t *ps,int *value);
void CODOL_PlayerStateExtClearClientDive(unsigned client);
int CODOL_PlayerStateSpawnTimeSet(const playerState_t *ps,int value);
int CODOL_PlayerStateSpawnTimeRead(const playerState_t *ps,int *value);
void CODOL_PlayerStateExtClearClientSpawnTime(unsigned client);

/* The three storage bases, bound once in codol_playerstate_ext_storage.c to
 * level.clients, svs.clients and svs.cachedSnapshotClients. They are a seam,
 * not indirection for its own sake: this file needs the array *types* to walk
 * them but must not reach into engine globals, so the resolver works the same
 * whether the arrays are the server's or a test's. A NULL base (count 0)
 * disables that class of storage. */
const void *CODOL_PlayerStateExtLiveBase(unsigned *count);
const void *CODOL_PlayerStateExtSnapshotBase(unsigned *count);
const void *CODOL_PlayerStateExtArchiveBase(unsigned *count);

/* Resolve the extension block owning this playerState storage. NULL means the
 * playerState is a scratch buffer that carries no extension; a read through
 * CODOL_PlayerStateExt also reports it, because the two consumers only ever
 * see live and snapshot storages. */
codol_ps_ext_t *CODOL_PlayerStateExt(const playerState_t *ps);
const codol_ps_ext_t *CODOL_PlayerStateExtConst(const playerState_t *ps);

/* Propagate along a playerState copy between tracked storages. Returns 0 when
 * the destination carries no extension. */
int CODOL_PlayerStateExtCopy(const playerState_t *dst, const playerState_t *src);
/* Same, when the source is a live client identified by index (the archive
 * writer copies through svsHeader pointers, not through level.clients). */
int CODOL_PlayerStateExtCopyFromClient(const playerState_t *dst, int client);

/* Explicit value transfer for the scratch-buffer paths: fetch reads a tracked
 * storage into the caller's own block, apply writes the caller's block into a
 * tracked storage. A NULL or unknown side yields/records "no magnitude". */
void CODOL_PlayerStateExtFetch(codol_ps_ext_t *out, const playerState_t *src);
void CODOL_PlayerStateExtFetchFromClient(codol_ps_ext_t *out, int client);
int CODOL_PlayerStateExtApply(const playerState_t *dst, const codol_ps_ext_t *value);

/* The weapon lock of a playerState storage. The read accessor never returns
 * NULL: an untracked storage, or one that never recorded a lock, reads as the
 * reset lock (no flags, CODOL_PS_LOCK_NO_ENTITY), which is what an unlocked
 * player has. The mutable accessor records that reset lock on first use and
 * returns NULL for an untracked storage. */
const codol_ps_lock_t *CODOL_PlayerStateLockRead(const playerState_t *ps);
codol_ps_lock_t *CODOL_PlayerStateLockMutable(const playerState_t *ps);
/* The live slot by index: the same block the resolver returns for
 * level.clients[client].ps, for callers that hold a client number instead of a
 * playerState. */
codol_ps_lock_t *CODOL_PlayerStateExtClientLock(unsigned client);
/* The hand bundle of this playerState, and a writable one for its producer.
 * Read returns the reset hand for an untracked or unrecorded state, never a
 * different player's; Mutable returns NULL for an untracked one. */
const codol_ps_hand_t *CODOL_PlayerStateHandRead(const playerState_t *ps);
codol_ps_hand_t *CODOL_PlayerStateHandMutable(const playerState_t *ps);
void CODOL_PlayerStateExtClearClientHand(unsigned client);
/* The selected offhands of this playerState, and a writable set for their
 * producer. Read returns the reset selection for an untracked or unrecorded
 * state, never a different player's; Mutable returns NULL for an untracked
 * one. */
const codol_ps_offhand_t *CODOL_PlayerStateOffhandRead(const playerState_t *ps);
codol_ps_offhand_t *CODOL_PlayerStateOffhandMutable(const playerState_t *ps);
void CODOL_PlayerStateExtClearClientOffhand(unsigned client);
/* The relocated inventory of the live slot: the four per-weapon arrays are
 * zeroed and weapons_known set, the state the gclient memset used to leave the
 * in-struct originals in. Live only, like every other ClearClient*. */
void CODOL_PlayerStateExtClearClientInventory(unsigned client);
/* Archived inventory records that had to drop owned weapons past the 127 the
 * record's count field carries; 0 unless something is badly wrong. */
unsigned CODOL_PlayerStateExtInventoryTruncations(void);

/* The looping sound of a playerState storage.
 *
 * Read reports the value the state carries and returns 0 for an untracked
 * storage, with *out set to 0: the transfer below runs for every state the
 * engine builds an entityState from, so its caller counts those instead of
 * warning per frame. A tracked state that never recorded one reads as 0, which
 * is silence rather than a guess.
 *
 * Set records it; 0 stops the loop. It fails for an untracked storage and for
 * a value outside the sound bank's 0..255, so an out-of-range index can never
 * reach the eight-bit wire field.
 *
 * The original C1 producer remains unresolved. Script playloopsound writes
 * the entity field directly; it must not be substituted for that producer.
 * The measured player-to-entity transfer reads this captured storage. */
int CODOL_PlayerStateLoopSoundRead(const playerState_t *ps, unsigned *out);
int CODOL_PlayerStateLoopSoundSet(const playerState_t *ps, unsigned sound);

/* The published weapon HUD icon overrides of a playerState storage.
 *
 * Read fills all eight slots and returns 1 for tracked storage. Missing storage
 * returns 0 without changing the output; it is not evidence of empty icons.
 * It reads the
 * state being serialized - captured, archived or spectator-followed - and is
 * the only read the snapshot path makes; no live client is consulted.
 *
 * SetClient is the producer half and takes a client number, because the
 * publisher runs from the retained ClientEndFrame with one. It replaces the
 * whole array of that client's live playerState storage, exactly as IW4's
 * publication does. Nothing else writes this field: script values reach a
 * playerState only by being published. */
int CODOL_PlayerStateHudIconOverridesRead(const playerState_t *ps,
                                           uint16_t out[CODOL_PS_HUD_ICON_SLOTS]);
void CODOL_PlayerStateExtSetClientHudIcons(unsigned client,
                                           const uint16_t icons[CODOL_PS_HUD_ICON_SLOTS]);

/* Predictable-event epoch.
 *
 * CODOL_PlayerStateEventAdded is the producer hook: the retained event
 * producers call it immediately after they store ps->eventSequence, so the
 * epoch is advanced by the same code that advanced the engine counter rather
 * than inferred from byte deltas later.
 *
 * CODOL_PlayerStateEventSequence yields what the C1 field 0x0f0 carries for
 * this state: epoch modulo 2048. It fails only on a malformed playerState; an
 * untracked storage, an unrecorded epoch with a non-zero counter, or an epoch
 * whose low byte disagrees with ps->eventSequence is repaired from the state's
 * own counter and reported through CODOL_PlayerStateEventDesyncs, never passed
 * off as tracked history. */
void CODOL_PlayerStateEventAdded(playerState_t *ps);
int CODOL_PlayerStateEventSequence(const playerState_t *ps, unsigned *out);
/* The raw epoch, for diagnostics: 0 when the state has none recorded. */
uint32_t CODOL_PlayerStateEventEpoch(const playerState_t *ps);
unsigned CODOL_PlayerStateEventDesyncs(void);

/* C1's scripted queue.
 *
 * CODOL_PlayerStateScriptEventAdded is the producer, called by the retained
 * G_AddEvent player branch in place of the predicted-queue stores it used to
 * make: it records the event and parameter in slot (epoch & 3) and advances the
 * epoch, exactly as C1 0x00572db3..0x00572dd7 does.
 *
 * CODOL_PlayerStateScriptEventQueue reports the queue for serialization: the
 * sequence is epoch modulo 2048 and the four slots are returned in C1's slot
 * order. It fails on an untracked storage and on a state that never recorded
 * one, so an unknown queue is never published as an empty one. */
void CODOL_PlayerStateScriptEventAdded(playerState_t *ps, unsigned event, unsigned parm);
int CODOL_PlayerStateScriptEventQueue(const playerState_t *ps, unsigned *sequence,
                                      uint32_t events[CODOL_PS_SCRIPT_EVENT_SLOTS],
                                      uint32_t params[CODOL_PS_SCRIPT_EVENT_SLOTS]);
/* The scripted events this state has not transferred to its entity state yet,
 * oldest first, without moving the cursor - the queue itself must stay intact
 * for the snapshot. Only the four slots that still exist can be reported, which
 * is the same bound C1's helper walks. CODOL_PlayerStateScriptEventsTransferred
 * moves the cursor once the transfer has run. */
unsigned CODOL_PlayerStateScriptEventsToTransfer(const playerState_t *ps,
                                                 uint32_t events[CODOL_PS_SCRIPT_EVENT_SLOTS],
                                                 uint32_t params[CODOL_PS_SCRIPT_EVENT_SLOTS]);
void CODOL_PlayerStateScriptEventsTransferred(playerState_t *ps);
uint32_t CODOL_PlayerStateScriptEventEpoch(const playerState_t *ps);

/* Zero the extension of a storage that was zeroed or left without a state. */
int CODOL_PlayerStateExtClear(const playerState_t *ps);
/* Live client slot by index, for the gclient memset in ClientSpawn and for
 * connect/disconnect. Independent of whatever clientNum that state carries,
 * and field-specific by construction: resetting one subsystem must not erase
 * the other's state, so there is no whole-block per-client clear. Respawn and
 * disconnect change the live state only - captured snapshots and archived
 * history keep the values they were taken with, as they do in IW4 and C1. */
void CODOL_PlayerStateExtClearClientRecoil(unsigned client);
void CODOL_PlayerStateExtClearClientStun(unsigned client);
void CODOL_PlayerStateExtClearClientLock(unsigned client);
void CODOL_PlayerStateExtClearClientEvents(unsigned client);
void CODOL_PlayerStateExtClearClientLoopSound(unsigned client);
void CODOL_PlayerStateExtClearClientHudIcons(unsigned client);
void CODOL_PlayerStateExtClearClientAbilities(unsigned client);
void CODOL_PlayerStateExtClearClientPerks(unsigned client);
void CODOL_PlayerStateExtClearClientLinks(unsigned client);
/* Only live hint binding; captured and archived states retain their value. */
void CODOL_PlayerStateExtClearClientUseHint(unsigned client);
void CODOL_PlayerStateExtSetCorpseIndex(playerState_t *ps,unsigned index);
/* The cached-snapshot ring, for SV_InitArchivedSnapshot. */
void CODOL_PlayerStateExtClearArchive(void);
void CODOL_PlayerStateExtClearAll(void);

/* Archive stream codec. The baseline is the playerState the archived state was
 * delta'd against, or NULL for an absolute record. */
void CODOL_PlayerStateExtWrite(msg_t *msg, const codol_ps_ext_t *value,
                               const codol_ps_ext_t *baseline);
void CODOL_PlayerStateExtRead(msg_t *msg, codol_ps_ext_t *out,
                              const codol_ps_ext_t *baseline);
void CODOL_PlayerStateExtWriteState(msg_t *msg, const playerState_t *ps,
                                    const playerState_t *baseline);
void CODOL_PlayerStateExtWriteClient(msg_t *msg, int client,
                                     const playerState_t *baseline);
void CODOL_PlayerStateExtReadState(msg_t *msg, const playerState_t *ps,
                                   const playerState_t *baseline);

/* Number of reads that found no storage since startup: bookkeeping failures
 * are visible rather than silently defaulted. */
unsigned CODOL_PlayerStateExtMisses(void);

#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
