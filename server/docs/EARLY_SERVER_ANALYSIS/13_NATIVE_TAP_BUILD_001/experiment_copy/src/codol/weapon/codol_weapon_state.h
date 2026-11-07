/* CoDOL per-hand weapon state and the second hand's weapon machine.
 *
 * The retained IW3 playerState carries a single weapon, a single weaponstate
 * machine and one flat ammoclip[128] array. Both IW4 and CoDOL C1 carry two
 * hand blocks, a per-clip record holding one magazine per hand, and run their
 * whole weapon machine once per hand. This module owns the missing
 * representation, the second hand's machine, its producers inside the retained
 * pmove and the queries gameplay/snapshot code consumes. Hand 0 remains the
 * retained engine machine; hand 1 is a real independent machine implemented
 * here, with its own timers, magazine, rechamber and predictable events.
 *
 * Reference behavior (each engine traced separately, no offsets equated):
 *
 *   CoDOL C1.exe
 *     PM_Weapon @0x41db80 runs `for(hand = 0; hand <= BG_GetLastWeaponHand(ps);
 *     ++hand) result[hand] = PM_Weapon_Hand(pm, hand)` at 0x41dc2d..0x41dc51 and
 *     then combines the two results with max() at 0x41dcb4..0x41dcc1.
 *     BG_GetLastWeaponHand @0x422930 returns 1 only when the equipped weapon's
 *     definition byte +0xbd5 (dual wield) is set, using ps+0x328 instead of
 *     ps+0x33c while the offhand viewmodel flag ps+0x344 bit 2 is up.
 *     PM_Weapon_Hand @0x41ace0 addresses its state as `ps + hand*0x1c`:
 *     +0x26c weaponTime, +0x274 a second timer, +0x278 weaponstate,
 *     +0x27c a flag; it decrements both timers by pml->msec (+0x28) scaled by
 *     0x41ab80 and only advances the phase once weaponTime reaches zero.
 *     BG_GetAmmoInClip @0x417fc0 / the setter @0x418000 scan fifteen records of
 *     {clipKey, ammo[2]} at ps+0x3d8 keyed by definition +0x570 and index the
 *     magazine by hand. PM_ReloadClip @0x41e4f0 takes the hand as its first
 *     stack argument and its callers at 0x41a36b/0x41a389/0x41a39d pass it
 *     through, so the reload transfer is per hand as well.
 *     PM_StartWeaponAnim @0x4180b0 writes the animation with a toggled 0x400
 *     restart bit, mirrors it into +0x284 with that hand's own toggle when
 *     ps+0x35c == 1, and clears +0x284 outright otherwise (0x4180ec).
 *     A weapon change writes ps+0x33c and ps+0x340 together (0x419cdf/0x419ce5),
 *     sets the dual-wield flag from the definition byte (0x419d51/0x419d68) and
 *     resets *both* hand states to zero when the weapon does not change
 *     (0x419d77/0x419d7d), so weapon-change events are emitted once, not twice.
 *
 *   IW4 iw4x.exe
 *     Hand weaponstates client+0x1f8 and client+0x214, stride 0x1c, both tested
 *     by isswitchingweapon 0x5d9f20. Clip records client+0x350, fifteen entries
 *     of {clipKey, ammo[2]} scanned by 0x48d170 and indexed by hand. Current
 *     weapon client+0x2b4 and the cached primary for an alternate-mode weapon
 *     client+0x2b8, written together by PM_BeginWeaponChange 0x576437..0x57644e.
 *
 *   IW3 (retained src/asmsource/_bg_weapons.asm), used for this machine's
 *   phase timings, animations and events because it is the code the second hand
 *   has to behave like:
 *     PM_Weapon_1230 fire gate, PM_Weapon_1900 state 5 with iFireTime/iFireDelay,
 *     PM_Weapon_2210 magazine decrement, PM_Weapon_1950/1360 fire animation
 *     (hip 2, hip-empty 3, ADS 5, ADS-empty 6, chosen on the post-shot count),
 *     PM_Weapon_1370/1380 EV_FIRE_WEAPON_LASTSHOT when that count is zero and
 *     EV_FIRE_WEAPON otherwise, PM_Weapon_1270 setting the bolt-action
 *     rechamber bit, PM_Weapon_580..610 the rechamber phase (state 6,
 *     iRechamberTime, iRechamberBoltTime, animation 4 or ADS 7,
 *     EV_RECHAMBER_WEAPON), PM_SetReloadingState (animation 13 with iReloadTime
 *     and EV_RELOAD, or 14 with iReloadEmptyTime and EV_RELOAD_FROM_EMPTY,
 *     state 7 or 8, weaponDelay from iReloadAddTime bounded by
 *     iRechamberBoltTime) and PM_ReloadClip (top-off bounded by the shared
 *     reserve and by iReloadAmmoAdd for the segmented states).
 *     Retained playerState: weapon +0xe8, weaponstate +0xec, weaponTime +0x3c,
 *     weaponDelay +0x40, weapAnim +0x624, ammo +0x15c, ammoclip +0x35c,
 *     weapons +0x55c. WeaponDef: iAmmoIndex +0x328, iClipIndex +0x330,
 *     iClipSize +0x338, weapType +0x12c, fireType +0x140, bBoltAction +0x4e8,
 *     iReloadAmmoAdd +0x534, altWeaponIndex +0x540. All confirmed against the
 *     field order in src/xassets/weapondef.h.
 */
#ifndef CODOL_WEAPON_STATE_H
#define CODOL_WEAPON_STATE_H
#include "codol_playerstate_ext.h"  /* CODOL_PS_EXT_WEAPON_BITS */
#include "q_shared.h"
#include "player.h"
#pragma pack(push, 8)
struct pmove_t;
struct pml_t;
struct entityState_s;

/* CoDOL/IW4 both carry exactly two hands and fifteen clip records. */
#define CODOL_WEAPON_HANDS 2
#define CODOL_WEAPON_CLIP_SLOTS 15
/* Ownership is the CODOL_WEAPON_SLOTS-bit playerState-extension bitset; no
 * weapon above it can be held. */
#define CODOL_WEAPON_STATE_WEAPONS CODOL_WEAPON_SLOTS

/* Retained IW3 weaponstate values, read out of _bg_weapons.asm itself:
 * PM_Weapon_2270 writes 2 for an alternate-mode raise and 1 otherwise,
 * PM_BeginWeaponChange writes 4 for a quick drop and 3 otherwise,
 * PM_Weapon_1900 writes 5 for firing, PM_Weapon_610 writes 6 for rechambering
 * and PM_SetReloadingState writes 7 or 8. IW4's isswitchingweapon accepts 1..5
 * because IW4 splits the alternate drop into its own state 5; IW3 keeps
 * alternate drops in 3/4 and distinguishes them by weapon animation 17, so the
 * native switching set is 1..4. The second hand uses the same numbering, which
 * is what CODOL_TranslateEngineWeaponState already converts for the wire. */
/* CoDOL-only internal event: the second hand's brass ejection. C1 selects wire
 * event 38 for hand 1 where hand 0 gets 35 -- `mov edx,hand / neg / sbb /
 * and edx,3 / add edx,0x23` at 0x418fd3..0x418fdc in PM_Weapon_CheckForRechamber
 * and at 0x41a219..0x41a222 in the delayed reload, both then calling the shared
 * zero-parameter emitter 0x40f360. That is a distinct event ID, not a parameter
 * and not the primary event, so it needs a distinct native ID here. The retained
 * BGEvent enum ends at EV_LANDING_PAIN_PAINTEDMETAL = 134 and the retained
 * HandleClientEvent only dispatches 0x13..0x3f and 0x6a..0x86, so 135 is inert
 * in the retained game and needs only the CoDOL wire mapping. Keep this one
 * reserved when the BGEvent enum grows; stop-fx occupies137. */
#define CODOL_EV_EJECT_BRASS_SECONDARY 135
/* CoDOL-only internal event: the weapon change C1 announces and IW3 does not.
 * C1 queues its event 0x1c with the weapon as the parameter in two places --
 * PM_Weapon_OffHandInit at 0x41c239 and PM_BeginWeaponChange at 0x419888,
 * the function whose 0x41981c writes weaponstate `3 + (arg != 0)`. alpha0022
 * equipment.py names it EV_WEAPON_SWITCH_STARTED at its line 133. No retained
 * event carries that meaning: EV_SWITCH_OFFHAND (34) is C1's separate event 51
 * and is already emitted at the selection, and native 28 is
 * EV_RECHAMBER_WEAPON. So it needs its own native ID past the enum, beside the
 * secondary brass, and only a CoDOL wire mapping. */
#define CODOL_EV_WEAPON_SWITCH_STARTED 136
/* CoDOL-only: dive-to-prone touchdown, C1 event 186 (EV_DTP_LAND, pushed
 * at 0x408f92). Native producer is codol_dive.c. */
#define CODOL_EV_DTP_LAND 140
/* CoDOL-only mantle-start event. C1 PM_StartMantle queues event 183. */
#define CODOL_EV_MANTLE_START 141
/* CoDOL-only dive launch. C1 PM_CheckDive queues event 185 immediately after
 * PM_DiveStart at 0x4090a8. */
#define CODOL_EV_DTP_LAUNCH 142
/* CoDOL-only: C1 PM_Weapon_OffHandEnd 0x41c860 queues event 16,
 * EV_OFFHAND_END_NOTIFY, with a zero parameter at 0x41c961..0x41c98a, on every
 * path that ends an offhand: the throw's end, a cancel, the held-pin release and
 * the offhand detonation's end. The retained enum has no such event; 143 is the
 * stance agent's EV_STANCE_INVALID (codol_events.h). */
#define CODOL_EV_OFFHAND_END_NOTIFY 144
/* CoDOL-only: C1 PM_UpdateVariableZoom 0x418480 queues event 184,
 * EV_SCOPE_ZOOM, with a zero parameter when a variable-zoom scope changes
 * level (0x41853e..0x418545). Producer: codol_pmove_c1_zoom.c. */
#define CODOL_EV_SCOPE_ZOOM 145

#define CODOL_WEAPONSTATE_READY 0
#define CODOL_WEAPONSTATE_RAISING 1
#define CODOL_WEAPONSTATE_RAISING_ALT 2
#define CODOL_WEAPONSTATE_DROPPING 3
#define CODOL_WEAPONSTATE_DROPPING_QUICK 4
#define CODOL_WEAPONSTATE_FIRING 5
#define CODOL_WEAPONSTATE_RECHAMBERING 6
#define CODOL_WEAPONSTATE_RELOADING 7
#define CODOL_WEAPONSTATE_RELOADING_AGAIN 8
/* Segmented reload, from PM_BeginWeaponReload and the PM_Weapon jump table
 * (entries 9/10 -> PM_Weapon_2320, entry 11 -> PM_Weapon_850): 9 opens the
 * sequence, 10 records that the trigger asked to break out of it, and 11 plays
 * the end animation before returning to idle. */
#define CODOL_WEAPONSTATE_RELOAD_SEGMENT 9
#define CODOL_WEAPONSTATE_RELOAD_INTERRUPT 10
#define CODOL_WEAPONSTATE_RELOAD_END 11
/* Extension animation IDs, used only by the native second-hand machine. */
#define CODOL_HAND_ANIM_RELOAD_FAST 28
#define CODOL_HAND_ANIM_RELOAD_EMPTY_FAST 29

typedef struct {
    unsigned weapon;   /* Native weapon index carried in this hand; 0 = empty. */
    int state;         /* Native weaponstate machine value. */
    int animation;     /* Native weapAnim including the 0x200 restart toggle. */
    int time, delay;   /* Native weaponTime/weaponDelay, milliseconds. */
    int restrict_time; /* C1's second per-hand timer, ps+0x274 + hand*0x1c. */
    unsigned rechamber;     /* Bolt-action rechamber owed by this hand. */
    unsigned shot_count;    /* Burst counter, the ps->weaponShotCount analogue. */
    unsigned trigger_held;  /* Edge tracking for non-automatic fire. */
    unsigned shot_pending;  /* A shot waiting out this weapon's fire delay. */
    unsigned delay_expired; /* This hand's delayed action landed this frame. */
    unsigned fresh_pull;    /* C1's per-hand 1-bit ps+0x27c, set by 0x41ab10. */
    unsigned reload_request;/* Queued weapFlags bit 0, forwarded to this hand. */
    unsigned brass_pending; /* A rechamber owes this hand's brass ejection. */
} codol_weapon_hand_t;

typedef struct {
    int clip_index;                    /* Native WeaponDef.iClipIndex; -1 free. */
    int ammo[CODOL_WEAPON_HANDS];      /* Right hand mirrors ps->ammoclip. */
} codol_weapon_clip_t;

/* IW4 5d94d0 / registry73c670 searches the six strings at799bd0 and writes
 * the class index to client+2ac. Init472388..47292a gives the order below.
 * CoDOL uses the same five nonzero definition class values. Explicit primary
 * selection can contain any of them: C1 40c82a/40c83c/40c84f accepts a weapon
 * found in ANY selected slot before its class-based empty-slot fallback. */
#define CODOL_OFFHAND_PRIMARY_CLASS_NONE 0
#define CODOL_OFFHAND_PRIMARY_CLASS_FRAG 1
#define CODOL_OFFHAND_PRIMARY_CLASS_SMOKE 2
#define CODOL_OFFHAND_PRIMARY_CLASS_FLASH 3
#define CODOL_OFFHAND_PRIMARY_CLASS_THROWINGKNIFE 4
#define CODOL_OFFHAND_PRIMARY_CLASS_OTHER 5
#define CODOL_OFFHAND_PRIMARY_CLASS_COUNT 6

typedef struct {
    codol_weapon_hand_t hand[CODOL_WEAPON_HANDS];
    unsigned primary_weapon; /* IW4 client+0x2b8 / C1 ps+0x340 equivalent. */
    unsigned dual_wield;     /* C1 ps+0x35c equivalent. */
    unsigned initialized;
    /* Live script preference. Concrete selected weapons are captured in the
     * playerState extension; serializers never consult this mutable record.
     * Cleared with native weapon state on spawn/connect/disconnect/reset. */
    unsigned char offhand_primary_class;
    unsigned char offhand_primary_known;
    unsigned char offhand_secondary_class;
    unsigned char offhand_secondary_known;
    int engine_state;        /* Retained weaponstate seen by the last update. */
    int engine_animation;    /* Retained weapAnim seen by the last update. */
    unsigned int owned[CODOL_WEAPON_BIT_WORDS]; /* Ownership the records were last keyed from. */
    unsigned int second_rechamber[CODOL_WEAPON_BIT_WORDS]; /* Per-owned-weapon hand1 bolt latch. */
    /* C1's spin-up charge, ps+0x5c0: a single 0..1 float, not per hand,
     * produced at 0x4183e0 and gating fire type 6 at 0x41b2f6. */
    float spinup_charge;
    /* C1's double-barrel armed barrel, its weapFlags bit 0x100 at ps+0x344.
     * Kept here because the retained ps->weapFlags bit 0x100 is the trigger
     * latch (PM_Weapon_1830/PM_Weapon_1310) and must not be overwritten. */
    unsigned second_barrel;
    /* The raw CoDOL command this pmove frame is running, captured by the
     * producer; command_valid is 0 for a bot or a rejected command. */
    unsigned command_valid, command_buttons;
    /* Which hand produced each fire event still queued in ps->events, and
     * whether it emptied that hand's magazine. Two views of the same records:
     * the ring, indexed exactly as BG_AddPredictableEventToPlayerstate indexes
     * ps->events (eventSequence & 3, _bg_misc.asm:2852), for the snapshot
     * producer; and a FIFO for BG_WeaponFireRecoil, which is handed an event
     * with no sequence and must consume them in the order they are served. */
    unsigned char ring_hand[4], ring_lastshot[4], ring_known[4];
    unsigned char shot_hands[4];
    unsigned shot_head, shot_count;
    codol_weapon_clip_t clips[CODOL_WEAPON_CLIP_SLOTS];
} codol_weapon_state_t;

#ifdef __cplusplus
extern "C" {
#endif

/* Per-weapon dual wield. CoDOL stores the flag in its serialized WeaponDef at
 * +0xbd5 (C1 reads it at 0x419d51 and 0x422967); the retained IW3 WeaponDef has
 * no such field and its layout is indexed by the retained assembly, so the asset
 * side publishes the flag instead of growing the engine struct. The resolver is
 * asked once per definition pointer and re-asked whenever an archive reload
 * replaces it. With no resolver installed every weapon is single-hand, which is
 * what the retained stock definitions describe. */
struct WeaponDef;
typedef int (*codol_weapon_dual_wield_resolver_t)(const struct WeaponDef *, int *);
void CODOL_SetWeaponDualWieldResolver(codol_weapon_dual_wield_resolver_t resolver);
void CODOL_SetWeaponDualWield(unsigned weapon, int dual_wield);
int CODOL_WeaponIsDualWield(unsigned weapon);
/* C1 picks the rechamber duration from the serialized +0x5b0 instead of +0x5ac
 * while ps+0x35c is set (0x4190ba); the asset side already captures that value
 * as codol_weapon_timing_extensions_t.rechamber_variant. Same resolver
 * contract: unavailable means the ordinary iRechamberTime is used. */
typedef int (*codol_weapon_rechamber_resolver_t)(const struct WeaponDef *, int *);
void CODOL_SetWeaponRechamberDualWieldResolver(codol_weapon_rechamber_resolver_t resolver);
/* C1 4190a4: selected primary uses the alternate duration while akimbo. */
int CODOL_WeaponRechamberTime(const playerState_t *ps);
/* Spin-up fire type 6 charges over def+0xb3c milliseconds while the trigger is
 * held and decays over def+0xb40 (C1 0x418414/0x418420); the retained WeaponDef
 * has neither field, so the asset side supplies them. Without a resolver a
 * spin-up weapon cannot charge and therefore cannot fire, which is reported
 * rather than silently degraded to full auto. */
typedef int (*codol_weapon_spinup_resolver_t)(const struct WeaponDef *, int *up_ms, int *down_ms);
void CODOL_SetWeaponSpinUpResolver(codol_weapon_spinup_resolver_t resolver);
/* Two serialized booleans of a grenade-type weapon that the retained WeaponDef
 * has no field for, both read beside def+0x340 in C1: +0xbe0 makes the weapon
 * fire on the second trigger alone (0x41b207, the remote-detonated equipment),
 * and +0xbe4 makes it pin its weapon time regardless of the trigger quota
 * (0x41ae09, the briefcase-bomb plant weapons). Unresolved means neither. */
typedef int (*codol_weapon_flag_resolver_t)(const struct WeaponDef *, int *);
void CODOL_SetWeaponDetonateTriggerResolver(codol_weapon_flag_resolver_t resolver);
void CODOL_SetWeaponHoldPinResolver(codol_weapon_flag_resolver_t resolver);

/* C1 ps+0x5c0, wire field 171 at offset 0x5c0. Zero unless a spin-up weapon is
 * held. Fails only on unusable input. */
int CODOL_WeaponStateSpinUpCharge(const playerState_t *ps, float *charge);
/* C1 0x4183e0 at 0x41dbf1: advance the charge at PM_Weapon's entry. */
void CODOL_WeaponStateSpinUpFrame(struct pmove_t *pm, struct pml_t *pml);
/* C1 0x41b2e0..0x41b301: hand 0's trigger is withheld until the charge is 1. */
int CODOL_WeaponStateSpinUpWithholds(const playerState_t *ps);
/* The armed barrel of a double-barrel weapon, published to the CoDOL weapon
 * flags. It selects which barrel the next shot uses and, through the arms at
 * C1 0x41ae5a..0x41ae6c, whether that hand's weapon time is pinned. */
int CODOL_WeaponStateSecondBarrelArmed(const playerState_t *ps);
/* The retained request chain asks this instead of testing cmd.buttons bit 0,
 * because C1 0x41b1f0 resolves which button fires a hand from the weapon and
 * the akimbo flag: an akimbo first hand fires on 0x100000, remote-detonated
 * equipment fires on 0x100000 for any hand, and everything else keeps bit 0. */
int CODOL_WeaponStateFireRequest(const playerState_t *ps, unsigned hand);
/* C1 0x41b1f0's trigger mask for hand 0, for the retained gate
 * PM_Weapon_840 and the two old-command edges: bit 0 for a single weapon,
 * 0x100000 while dual wielding. */
unsigned CODOL_WeaponStateHandZeroMask(const playerState_t *ps);
/* C1 BG_PlayerCanAds 0x418140: akimbo off a turret never aims down sights. */
int CODOL_WeaponStateBlocksAds(const playerState_t *ps);
/* C1 0x41ae37..0x41ae6c: the double-barrel arm of the pin decision. 1 when
 * the trigger asking is not the one that took the last shot, which is what
 * clears the quota flag so the other barrel can leave on the same magazine.
 * Every other term of the pin belongs to the retained chain. */
int CODOL_WeaponStateDoubleBarrelReleasesPin(const playerState_t *ps, unsigned hand);
/* C1 0x41bb20, called from the fire dispatch at 0x41daf7 before the hand gate
 * 0x41b240 at 0x41db03: a non-akimbo double barrel (fireType 5) whose second
 * trigger 0x100000 is down fires hand 0 outright. The retained fire gate at
 * PM_Weapon_840 only sees the native fire bit -- CODOL_ToEngineUsercmd masks
 * the CoDOL word with 0xff3f -- so it asks this for the other trigger. */
int CODOL_WeaponStateSecondTriggerFires(const playerState_t *ps);
/* The request term the semi-automatic pin is gated on: the hand request plus
 * the second trigger of a non-akimbo double barrel, C1 0x41ae73 feeding
 * 0x41ae9f. The plain CODOL_WeaponStateFireRequest stays the term that keeps
 * the shot counter alive (C1 0x41af3d). */
int CODOL_WeaponStatePinRequest(const playerState_t *ps, unsigned hand);
/* The rest of 0x41bb20: with BOTH triggers down the dispatch calls the fire
 * routine 0x41b930 twice off one command, so both barrels leave in the same
 * pmove frame. The retained machine fires once per hand per frame, so this
 * takes the second round -- magazine, shot counter, shot record and fire
 * event -- right after PM_Weapon_1370/1380 queued the first one's event. */
void CODOL_WeaponStateDoubleBarrelSecondShot(playerState_t *ps);
/* Whether this weapon carries C1's serialized hold byte, WeaponDef +0xbe4.
 *
 * This is one of the two terms C1's hand decision takes at 0x41ae8f..0x41ae99:
 * a grenade-type weapon with that byte reaches the hold even when the fire
 * quota is not spent. It is *not* the hold itself. C1 still requires a live
 * trigger request (0x41ae9f), the pmove's weapon to match the playerState's
 * (0x41aeae) and ammo in that hand's magazine (0x41aec3) before it writes the
 * weapon time at 0x41aed5, and the retained chain already tests all three in
 * PM_Weapon_1600/1620. The retained engine builds the same term from its own
 * WeaponDef field +0x5b4 (PM_Weapon_1580), which is a different field from
 * C1's; this reports the CoDOL one so a weapon only the CoDOL asset marks is
 * not silently dropped from the term. */
int CODOL_WeaponStateWeaponHoldsFire(const playerState_t *ps, unsigned hand);
/* C1 def+0x560: shots never spend a round (0x41e3cf). Called by the retained
 * PM_Weapon_2210 decrement as well as the second hand's. */
int __cdecl CODOL_WeaponUnlimitedAmmo(const struct WeaponDef *def);
/* CoDOL-only native weaponstate: the offhand detonation phase.
 *
 * C1's per-hand machine has six offhand phases where the retained engine has
 * five. Its state 20 is a detonation the retained engine cannot reach at all,
 * and the two sequences line up exactly once that is accounted for:
 *
 *   native 15 init      -> C1 16      native 19 attack -> C1 19
 *   native 16 prepare   -> C1 17      native 20 end    -> C1 21
 *   native 17 release   -> C1 19      native 21 weapon detonation -> C1 22
 *   native 18 hold      -> C1 18      (C1 20 offhand detonation: no native)
 *
 * That is also why the retained hold excludes 15..20 where C1 excludes 16..21,
 * and why PM_Weapon_CheckForOffHand refuses 15..19 where C1 refuses 16..20:
 * the native ranges are the preimage of the C1 ranges minus the missing state,
 * not an off-by-one. This number gives that state a native home. It is above
 * every value the retained engine writes (0..24) and above every value it
 * compares (its jump table and bound stop at 26), so no existing branch can
 * see it; the branches that must are extended explicitly beside it. */
#define CODOL_WEAPONSTATE_OFFHAND_DETONATE 27
/* Whether the offhand this playerState has raised should detonate instead of
 * throw, asked by PM_Weapon_OffHandPrepare. C1 0x41c41b..0x41c431: the
 * definition carries the serialized byte +0xbe0 and the total ammo helper
 * 0x41def0 answers zero. */
int CODOL_WeaponStateOffhandDetonates(const playerState_t *ps);
/* Offhand selection, replacing the retained class scan.
 *
 * C1 does not search the inventory: PM_Weapon_CheckForOffHand 0x41cb41..
 * 0x41cba2 reads one of three selected weapons out of the playerState,
 * choosing between them with CoDOL buttons 0x4000, 0x8000 and 0x10000, each
 * required to be a rising edge against the previous command and each gated by
 * the same bit of the playerState weapon-flags word. The class-to-slot
 * grouping is measured at 0x40c7e0. The two gates that follow are the empty
 * magazine allowed only for a +0xbe0 weapon (0x41cbaf) and the ground
 * requirement of a +0xbe5 weapon (0x41cbcd). Returns the weapon to raise, or 0
 * to select nothing at all. */
unsigned CODOL_WeaponStateSelectOffhand(const playerState_t *ps, const struct pmove_t *pm);
/* The producer for those three words.
 *
 * They are 32-bit playerState wire fields the server authors and the client
 * consumes; a scan of C1's .text finds only reads, but C1 also carries a
 * virtualized section, so that scan cannot say a producer does not exist --
 * only that the server is the one that has to fill them.
 *
 * The reference server fills them from the player's *loadout*, not from
 * anything about acquisition: alpha0022 equipment.py takes one weapon_loadout
 * record, maps its lethal/tactical/special item ids to weapon names
 * (class_equipment, line 251), stores all three at once (EquipmentState
 * set_class, line 419) and publishes ps+0x32C/0x330/0x334 every frame with 0
 * for an empty slot (ps_slot_fields, line 453). So the assignment here is
 * explicit and whole-set for the same reason: a partial or order-dependent
 * rule would be a different producer, not a smaller one.
 *
 * This whole-loadout API uses conventional class grouping1/4,2/3,5;
 * it is its own policy, not a C1 restriction on explicit slot assignments.
 * Zero empties a slot. Replaces both class preferences. Fails without writing
 * anything when any entry is unusable, so a rejected set never half-applies. */
int CODOL_WeaponStateSetOffhandSlots(playerState_t *ps, const unsigned weapon[3]);
/* Which slot that weapon's own offhand class names, or -1 for a weapon with
 * no offhand class. The grouping above, exposed for the script setter's
 * argument checking. */
int CODOL_WeaponStateOffhandSlotForWeapon(unsigned weapon);
/* Persistent primary-button class. All classes0..5 are accepted; none clears
 * primary slot0, other classes select an owned weapon of that exact class in
 * slot0. Missing inventory leaves slot0 empty but retains the preference for
 * future grants. Other two slots stay unchanged. */
int CODOL_WeaponStateSetOffhandPrimaryClass(playerState_t *ps,unsigned class_index);
int CODOL_WeaponStateOffhandPrimaryClass(const playerState_t *ps,unsigned *class_index);
/* IW4 5d95f0 uses the same six classes for secondary button/slot1. */
int CODOL_WeaponStateSetOffhandSecondaryClass(playerState_t *ps,unsigned class_index);
int CODOL_WeaponStateOffhandSecondaryClass(const playerState_t *ps,unsigned *class_index);
/* Live producer after successful grants/removals and ammo changes. Publishes
 * concrete primary/secondary selections for future snapshots; prunes removed
 * weapons from all slots. Never resolves archives through live preferences. */
void CODOL_WeaponStateRefreshOffhands(playerState_t *ps);
void CODOL_WeaponStateOffhandGranted(playerState_t *ps,unsigned weapon);
/* The weapon of that internal name, or 0 when there is none. */
unsigned CODOL_WeaponStateWeaponForName(const char *name);
/* Lifecycle, not selection: a weapon the player no longer holds cannot stay
 * selected. Only clears the slot that actually held it. */
void CODOL_WeaponStateOffhandReleased(playerState_t *ps, unsigned weapon);
/* The selected weapon of a slot, for the snapshot producer. Fails for a state
 * that never had a selection recorded, which is not three empty slots. */
int CODOL_WeaponStateOffhandSlot(const playerState_t *ps, unsigned slot, unsigned *weapon);
/* WeaponDef +0xbe5: the weapon may only be raised or fired while the player is
 * standing on something (C1 0x41cbcd and 0x41b2aa both test it against
 * groundEntityNum). Published by the asset side like the other bytes. */
void CODOL_SetWeaponRequiresGroundResolver(codol_weapon_flag_resolver_t resolver);
/* Captured entity publication.
 *
 * The retained BG_PlayerStateToEntityState stores one weapon into the entity
 * state (entityState +0xc4). C1 stores two: 0x40d14d writes the current weapon
 * to +0xd4, and 0x40d0d7..0x40d0fd writes to +0xd6 the primary that owns it --
 * the cached primary at ps+0x340 when the current weapon's definition has
 * inventory type 3 (alternate mode), and the current weapon itself otherwise.
 * The retained entityState has no second word, so the pair is captured beside
 * the entity state it was produced for, from the playerState the producer was
 * handed, and travels with that entity state into snapshots and the archive. */
void CODOL_WeaponStateCaptureEntityWeapon(const playerState_t *ps, struct entityState_s *es);
/* Per-queued-event view for the snapshot producer: which hand fired the event
 * in ps->events[slot] and whether that shot emptied its magazine. C1 selects
 * EV_SV_FIRE_WEAPON 43 / 45 and their last-shot variants 44 / 46 from exactly
 * these two facts at 0x41b8db..0x41b8f3. Returns 0 when that slot holds no
 * recorded shot. */
int CODOL_WeaponStateShotRecord(const playerState_t *ps, unsigned slot,
                                unsigned *hand, unsigned *last_shot);

const codol_weapon_state_t *CODOL_ClientWeaponState(unsigned client);
/* Full lifecycle reset: connect, spawn, disconnect and level restart. */
void CODOL_ResetClientWeaponState(unsigned client);
void CODOL_ResetWeaponStates(void);
/* Clears the per-weapon "already reported" flags for the optional timing
 * metadata warnings. Absent metadata is a warning and an unmodified duration,
 * never a dropped server: a killstreak-held weapon such as ac130_40mm_mp
 * legitimately carries no reload-perk metadata because it does not reload. */
void CODOL_ResetWeaponTimingReports(void);

/* Producers, called from the retained pmove (src/asmsource/_bg_weapons.asm).
 *
 * SelectWeapon runs where PM_Weapon assigns ps->weapon: it resolves the cached
 * primary from the weapon actually being left, exactly as IW4's and C1's
 * PM_BeginWeaponChange receive it from their caller, and starts the second
 * hand's own raise.
 * BeginChange runs at the end of PM_BeginWeaponChange and starts the second
 * hand's drop with the same quick/alternate selection the retained code made,
 * matching C1 initiating the change once for both hands.
 * Update runs at PM_Weapon's single exit: it mirrors the retained machine into
 * hand 0 and runs the second hand's own machine for this frame.
 * ResetHands is the PM_ResetWeaponState counterpart. */
/* PM_Weapon_CheckForReload consumes the queued reload request in weapFlags bit
 * 0 for the engine hand; the retained code forwards it here so the second hand
 * sees the same request instead of inferring one. */
void CODOL_WeaponStateReloadRequest(playerState_t *ps);
/* The retained fire path records its own shot so the recoil consumer below can
 * tell whose kick-restriction window applies to each queued fire event. */
void CODOL_WeaponStateRecordShot(playerState_t *ps, unsigned hand, unsigned last_shot);
/* BG_WeaponFireRecoil's kick-restriction read. Returns the restriction of the
 * hand that produced the fire event now being served, consuming that record;
 * with nothing recorded it is the engine's own ps->weaponRestrictKickTime. */
int CODOL_WeaponStateRecoilRestrictTime(const playerState_t *ps);
void CODOL_WeaponStateSelectWeapon(playerState_t *ps, unsigned previous, unsigned next);
void CODOL_WeaponStateBeginChange(playerState_t *ps, int alternate, int quick);
void CODOL_WeaponStateUpdate(struct pmove_t *pm, struct pml_t *pml);
/* C1 41ab80: ability-scaled phase/delay step for the primary hand. */
int CODOL_WeaponFrameMsec(const playerState_t *ps, int msec);
void CODOL_WeaponStateResetHands(playerState_t *ps);
/* BG_TakePlayerWeapon: drop the state that referred to a weapon being removed,
 * before its ownership bit and ps->weapon are cleared. */
void CODOL_WeaponStateTakeWeapon(playerState_t *ps, unsigned weapon);
/* Scripted assignment. Gameplay outside pmove that writes ps->weapon directly
 * must report the pair so the cached primary is resolved with the weapon that
 * was actually being left, rather than with whatever pmove last observed. */
void CODOL_WeaponStateScriptedWeapon(playerState_t *ps, unsigned next);

/* Queries. All return 0 on unusable input and leave outputs unchanged. */
int CODOL_WeaponStateHand(const playerState_t *ps, unsigned hand, codol_weapon_hand_t *out);
/* IW4 getcurrentprimaryweapon 0x5d92d0 / C1 BG_PlayerStateToEntityState
 * 0x40d0d7: the current weapon, or the cached primary when the current weapon
 * is an alternate-mode entry. Fails when an alternate mode has no primary. */
int CODOL_WeaponStatePrimaryWeapon(const playerState_t *ps, unsigned *primary);
/* IW4 0x48d170 / C1 BG_GetAmmoInClip 0x417fc0: locate the record whose key is
 * the weapon's clip index and return that record's per-hand magazine; an absent
 * record yields 0. */
int CODOL_WeaponStateClipAmmo(const playerState_t *ps, unsigned weapon, unsigned hand, int *ammo);
int CODOL_WeaponStateSetLeftClip(playerState_t *ps,unsigned weapon,int ammo);
/* Same lookup keyed by the native clip index, for the snapshot ammo producer. */
int CODOL_WeaponStateClipAmmoByIndex(const playerState_t *ps, int clip_index, unsigned hand, int *ammo);
/* IW4 isswitchingweapon 0x5d9f20: either hand mid raise or drop. */
int CODOL_WeaponStateIsSwitching(const playerState_t *ps);
int CODOL_WeaponStateIsReloading(const playerState_t *ps);
int CODOL_WeaponStateIsDualWielding(const playerState_t *ps);
/* Consumers of the per-hand result C1's PM_Weapon combines with max() at
 * 0x41dcb4 and feeds to the melee check 0x41c070, and of the burst-continuation
 * helper 0x41aa70 it asks for every hand at 0x41dc56/0x41dc66. Both are the
 * second hand's half of gates the retained PM_Weapon already applies to its own
 * hand; they are called from it, not from a parallel machine. */
int CODOL_WeaponStateSecondHandBlocksMelee(const playerState_t *ps);
int CODOL_WeaponStateSecondHandBursting(const playerState_t *ps);
/* C1 0x418ec0: this hand's magazine of the held bullet weapon is empty, so
 * the burst-continuation helper 0x41aa70 reports nothing owed. */
int CODOL_WeaponStateHandClipSpent(const playerState_t *ps, unsigned hand);

/* CoDOL-only native weaponstates: the dolphin-dive weapon phases, C1 31..33.
 * C1 0x41d4b0 enters dive-in (0x41d1f0: time +0x630) while PMF_DIVETOPRONE is
 * up and the dive is not yet sliding; its expiry enters the zero-time loop
 * (0x41d350), which leaves through dive-out (0x41d2a0: time +0x638) once the
 * dive slides or ends (0x41d967), and dive-out ends in the ready state
 * (0x41c1c0). Fire, switch, reload, melee, offhand, detonation and sprint all
 * refuse these states in C1, and the retained branches are extended beside
 * CODOL_WEAPONSTATE_OFFHAND_DETONATE. The native animation carries one of two
 * dive IDs (normal / empty magazine); the phase selects C1's 35..40. */
#define CODOL_WEAPONSTATE_DIVE_IN 28
#define CODOL_WEAPONSTATE_DIVE_LOOP 29
#define CODOL_WEAPONSTATE_DIVE_OUT 30
#define CODOL_ANIM_DIVE 30
#define CODOL_ANIM_DIVE_EMPTY 31
/* PM_Weapon's dive check, run between its sprint and offhand checks. */
void CODOL_WeaponStateDiveCheck(struct pmove_t *pm);
/* Jump-table arms for the dive-in expiry and the loop. */
void CODOL_WeaponStateDiveInDone(playerState_t *ps);
void CODOL_WeaponStateDiveLoop(playerState_t *ps);
/* C1 0x41c394: a throwing knife (serialized class 9) prepares at init. */
int CODOL_WeaponStateOffhandPreparesAtInit(const playerState_t *ps);
/* C1 0x41c5f0, the offhand hold: 0 throw now, 1 keep holding, 2 the hold was
 * cancelled (the offhand already ended back to the weapon). */
int CODOL_WeaponStateOffhandHold(playerState_t *ps, const struct pmove_t *pm);
/* C1 0x41ce70: releasing a held-pin offhand or pressing the cancel button
 * (0x400000, def +0xbec) during init/prepare ends the offhand. */
void CODOL_WeaponStateOffhandCancelCheck(struct pmove_t *pm);
/* Queues CODOL_EV_OFFHAND_END_NOTIFY; called where the retained machine ends
 * an offhand (PM_Weapon_2010, PM_Weapon_1780, the detonation end). */
void __cdecl CODOL_WeaponStateOffhandEndNotify(playerState_t *ps);
/* C1 0x41b18a: a drop cancelled back to the held weapon readies every hand
 * with animation 1; this is the second hand's half. */
void __cdecl CODOL_WeaponStateCancelChange(playerState_t *ps);

#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
