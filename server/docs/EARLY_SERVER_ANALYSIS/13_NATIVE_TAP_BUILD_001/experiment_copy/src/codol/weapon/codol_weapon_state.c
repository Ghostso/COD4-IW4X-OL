/* CoDOL per-hand weapon state: representation, the second hand's weapon
 * machine, its pmove producers and the queries gameplay/snapshot code reads.
 * See codol_weapon_state.h for the traced C1/IW4/IW3 reference behavior. */
#ifdef CODOL_SERVER
#include "codol_weapon_bits.h"
#include "codol_weapon_state.h"
#include "bg_public.h"
#include "bg.h"
#include "cvar.h"
#include "codol_game.h"
#include "codol_usercmd.h"
#include "codol_weapon_input.h"
#include "codol_playerstate_ext.h"
#include "codol_entitystate_ext.h"
#include "codol_weapon_flags.h"
#include "codol_weapon_native.h"
#include "codol_weapon_reload.h"
#include "codol_variable_zoom.h"
#include "codol_abilities.h"
#include "codol_pmove_c1.h"
#include "codol_engine_state.h"
#include "xassets/weapondef.h"
#include "qcommon_io.h"
#include <string.h>
#include <math.h>
#include <limits.h>

/* Retained gameplay the second hand has to obey, declared here because the tree
 * publishes none of them in a header: the mantle suspension PM_Weapon_420
 * consults (src/asmsource/_bg_mantle.asm:1477 takes the playerState and reads
 * pm_flags bit 2 plus the mantle transition), the two dvars the retained fire
 * and burst paths read through their cvar current value at +0xc
 * (src/g_sv_main.c:234), and the CoDOL lock gate the retained fire path
 * already calls at PM_Weapon_1310 (src/codol_weapon_lock_fire.c:9). */
int Mantle_IsWeaponInactive(playerState_t *ps);
extern cvar_t *player_sustainAmmo;
int CODOL_WeaponLockFireEvent(const playerState_t *ps, const struct WeaponDef *weapon);

/* The retained PM_AddEvent is BG_AddPredictableEventToPlayerstate(event, 0, ps)
 * (src/asmsource/_bg_pmove.asm:3895). bg.h and bg_local.h declare that symbol
 * with different third-parameter spellings; bg.h's gclient_t is the struct whose
 * documented first element is that playerState (src/player.h:409), so this
 * wrapper keeps the enum from bg.h without pulling in the second declaration. */
static void add_player_event(playerState_t *ps, BGEvent event)
{
    BG_AddPredictableEventToPlayerstate(event, 0, (gclient_t *)ps);
}

/* The retained ammoclip decrement and this hand's magazine are both consumed by
 * BG_WeaponFireRecoil through a single ps->weaponRestrictKickTime; C1 keeps one
 * window per hand at ps+0x274 + hand*0x1c. The retained event loop
 * (_g_active_mp.asm:1699) serves ps->events in order, so recording the owning
 * hand of each fire event in the same order lets the recoil read pick the right
 * window without a hand argument the retained signature does not have. */
#define CODOL_SHOT_RECORDS 4

static codol_weapon_state_t codol_weapon_states[MAX_CLIENTS];
/* CoDOL publishes dual wield in its serialized WeaponDef; see the header. */
static codol_weapon_dual_wield_resolver_t codol_dual_wield_resolver;
static codol_weapon_rechamber_resolver_t codol_rechamber_resolver;
static codol_weapon_spinup_resolver_t codol_spinup_resolver;
static codol_weapon_flag_resolver_t codol_detonate_resolver;
static codol_weapon_flag_resolver_t codol_hold_resolver;
static const struct WeaponDef *codol_dual_wield_defs[CODOL_WEAPON_STATE_WEAPONS];
static unsigned char codol_dual_wield_flags[CODOL_WEAPON_STATE_WEAPONS];
static unsigned char codol_dual_wield_known[CODOL_WEAPON_STATE_WEAPONS];

/* Retained weapon animation identifiers, from the same PM_Weapon sites the
 * phases below reproduce. The restart toggle is 0x200 natively (0x400 on the
 * CoDOL wire); CODOL_OverlayEngine*Phase already converts both. */
#define ANIM_IDLE 0
#define ANIM_FIRE 2
#define ANIM_FIRE_EMPTY 3
#define ANIM_RECHAMBER 4
#define ANIM_FIRE_ADS 5
#define ANIM_FIRE_ADS_EMPTY 6
#define ANIM_RECHAMBER_ADS 7
#define ANIM_DROP 10
#define ANIM_RAISE 11
#define ANIM_FIRST_RAISE 12
#define ANIM_RELOAD 13
#define ANIM_RELOAD_EMPTY 14
#define ANIM_RELOAD_START 15
#define ANIM_RELOAD_END 16
#define ANIM_DROP_ALT 17
#define ANIM_RAISE_ALT 18
#define ANIM_DROP_QUICK 19
#define ANIM_RAISE_QUICK 20
#define ANIM_DROP_EMPTY 21
#define ANIM_RAISE_EMPTY 22
#define ANIM_RESTART_BIT 0x200u

/* PM_Weapon_1950 and PM_Weapon_580 both compare fWeaponPosFrac with 0.75 to
 * decide between the hip and ADS animation families; PM_Weapon_1280 uses a
 * full 1.0 to pick the kick-restriction count, as C1 does at 0x41b55e. */
#define ADS_ANIMATION_FRACTION 0.75f
#define ADS_COMPLETE_FRACTION 1.0f

/* PM_Weapon_1230's adsFireOnly branch computes the shot's delay as
 * (1 - fWeaponPosFrac) divided by the float at WeaponDef +0x7f8, and
 * PM_UpdateAimDownSightLerp advances fWeaponPosFrac by msec times that same
 * word (_bg_weapons.asm:5654). That word is fOOPosAnimLength[0]: the header
 * places it at +0x7f8 -- asserted in codol_weapon_native.c and derived in
 * obj/claude-workers/parent-weapon-tail-layout.py, where the two
 * pointer-to-array-of-two members accuracyGraphKnots and
 * originalAccuracyGraphKnots are eight bytes each -- and the CoDOL loader
 * writes the two per-millisecond rates straight into it
 * (CODOL_ApplyNativeWeaponAds, source +0xa28/+0xa2c). An earlier pass of mine
 * claimed this offset conflicted with fMaxDamageRange; that was a bad manual
 * layout count on my side and is withdrawn. BG_LoadWeaponDefInternal fills the
 * same field for retained assets as 1.0f / iAdsTransInTime, defaulting to
 * 0x3b5a740e = 1/300 (_bg_weapons_load_obj.asm:1597..1604), so reading the rate
 * is correct for both asset paths, while recomputing it from iAdsTransInTime
 * would diverge for a CoDOL weapon whose serialized rate is not that exact
 * reciprocal. Read the rate the engine itself divides by. */
#define CODOL_ADS_TRANS_IN_DEFAULT_RATE (1.0f / 300.0f)
static float ads_transition_rate(const struct WeaponDef *def)
{
    float rate = def->fOOPosAnimLength[0];
    return rate > 0.0f ? rate : CODOL_ADS_TRANS_IN_DEFAULT_RATE;
}

static int owns_weapon(const playerState_t *ps,unsigned weapon);
static codol_weapon_state_t *state_of(const playerState_t *ps);
static int clip_of(const struct WeaponDef *def);

static struct WeaponDef *weapon_def(unsigned weapon)
{
    int count;
    if(!weapon || weapon >= CODOL_WEAPON_STATE_WEAPONS) return NULL;
    count = BG_GetNumWeapons();
    if(count <= 0 || weapon >= (unsigned)count) return NULL;
    return BG_GetWeaponDef((int)weapon);
}

/* Optional per-weapon timing metadata that is absent must never be fatal.
 *
 * This whole function only ever computes a timing MULTIPLIER. Its inputs are
 * optional by construction: BG_GetWeaponDef's reload-perk field is optional in
 * IW4 (absent means the perk simply does not apply), and the ability modifier
 * table is a tuning table. Three paths here used to Com_Error(ERR_DROP) on
 * those inputs, so a weapon with no metadata killed the whole match instead of
 * running at its unmodified speed. That is exactly what happened when the
 * AC-130 was first reached: `giveweapon: name ac130_40mm_mp` was immediately
 * followed by `ERROR: CoDOL weapon reload perk metadata unavailable` and a
 * server shutdown. Killstreak-held weapons (the three AC-130 guns, the chopper
 * gunner minigun, the sentry and predator weapons) are exactly the weapons
 * that carry no reload metadata, because they do not reload.
 *
 * Each distinct cause is now reported once per weapon and the unmodified msec
 * is returned. Warning once per weapon, not once globally, keeps a second
 * weapon's missing metadata visible; reporting per call would flood, since
 * this runs every weapon frame. */
static unsigned char codol_weapon_timing_reported[CODOL_WEAPON_STATE_WEAPONS];
#define CODOL_TIMING_REPORT_INHERITS 1u
#define CODOL_TIMING_REPORT_ABILITY  2u
#define CODOL_TIMING_REPORT_RANGE    4u
static void report_weapon_timing_once(unsigned weapon,unsigned cause,
                                      const char *what,unsigned ability)
{
    if(weapon>=CODOL_WEAPON_STATE_WEAPONS) return;
    if(codol_weapon_timing_reported[weapon]&cause) return;
    codol_weapon_timing_reported[weapon]|=(unsigned char)cause;
    Com_PrintWarning(CON_CHANNEL_SERVER,
        "CoDOL weapon %u: %s (ability %u); using unmodified timing\n",
        weapon,what,ability);
}
void CODOL_ResetWeaponTimingReports(void)
{
    memset(codol_weapon_timing_reported,0,sizeof(codol_weapon_timing_reported));
}

/* C1 41ab80 scales the phase/delay clock, not the recoil restriction clock.
 * Ability IDs use the actual per-player values written by GSC. C1's
 * 402f20/403070 both resolve column2 by ID in coAbilityModifiersTable. */
static int weapon_frame_msec(const playerState_t *ps, unsigned phase,
                             const struct WeaponDef *def, int msec)
{
    const codol_ps_ext_t *ext=CODOL_PlayerStateExtConst(ps);
    const codol_engine_table_t *table;
    unsigned ability=0, weapon=ps?(unsigned)ps->weapon:0;
    float modifier, product;
    double rounded_input;
    int inherits;
    if(!ext || !ext->abilities_known) return msec;
    if(phase>=7 && phase<=11 && (ext->abilities.masks[0]&0x40000000u)) {
        if(!CODOL_GetNativeWeaponInheritsPerks(def,&inherits)) {
            /* No reload-perk metadata: the perk does not apply to this weapon.
             * IW4 treats the field as optional and defaults it off; a weapon
             * that never reloads legitimately has none. */
            report_weapon_timing_once(weapon,CODOL_TIMING_REPORT_INHERITS,
                "no reload perk metadata",1);
            inherits=0;
        }
        if(inherits) ability=1;
    }
    if(!ability && phase>=1 && phase<=4 && (ext->abilities.masks[0]&0x200u))
        ability=22;
    if(!ability && (phase==5 || phase==6) && (ext->abilities.masks[0]&0x100u))
        ability=23;
    if(!ability) return msec;
    if(CODOL_LoadEngineStringTable("mp/coAbilityModifiersTable.csv",&table)!=1 ||
       CODOL_GetActiveAbilityValue(&ext->abilities,table,ability,&modifier)!=1) {
        /* An absent tuning row means no modifier, which is the same result as
         * a modifier of 1.0. It is not a reason to end the match. */
        report_weapon_timing_once(weapon,CODOL_TIMING_REPORT_ABILITY,
            "ability modifier unavailable",ability);
        return msec;
    }
    /* 41abe8/41ac49/41acab round the multiplication to float, then add
     * double 2^-30 (c84590) before FISTP under the current rounding mode. */
    product=(float)msec*modifier;
    rounded_input=(double)product+0x1p-30;
    if(!isfinite(rounded_input) || rounded_input>INT_MAX || rounded_input<INT_MIN) {
        /* A nonfinite or out-of-range product means the table value is bad.
         * Fall back to the unmodified duration rather than publishing a
         * garbage timing or dropping the server. */
        report_weapon_timing_once(weapon,CODOL_TIMING_REPORT_RANGE,
            "ability modifier out of range",ability);
        return msec;
    }
    return (int)lrint(rounded_input);
}

int CODOL_WeaponFrameMsec(const playerState_t *ps,int msec)
{
    return weapon_frame_msec(ps,(unsigned)ps->weaponstate,weapon_def(ps->weapon),msec);
}

void CODOL_SetWeaponDualWieldResolver(codol_weapon_dual_wield_resolver_t resolver)
{
    codol_dual_wield_resolver = resolver;
    memset(codol_dual_wield_known, 0, sizeof(codol_dual_wield_known));
}
void CODOL_SetWeaponDualWield(unsigned weapon, int dual_wield)
{
    if(weapon >= CODOL_WEAPON_STATE_WEAPONS) return;
    codol_dual_wield_defs[weapon] = weapon_def(weapon);
    codol_dual_wield_flags[weapon] = dual_wield ? 1 : 0;
    codol_dual_wield_known[weapon] = 1;
}
int CODOL_WeaponIsDualWield(unsigned weapon)
{
    const struct WeaponDef *def = weapon_def(weapon);
    int flag = 0;
    if(!def) return 0;
    if(codol_dual_wield_known[weapon] && codol_dual_wield_defs[weapon] == def)
        return codol_dual_wield_flags[weapon];
    if(codol_dual_wield_resolver && !codol_dual_wield_resolver(def, &flag)) flag = 0;
    codol_dual_wield_defs[weapon] = def;
    codol_dual_wield_flags[weapon] = flag ? 1 : 0;
    codol_dual_wield_known[weapon] = 1;
    return codol_dual_wield_flags[weapon];
}

void CODOL_SetWeaponRechamberDualWieldResolver(codol_weapon_rechamber_resolver_t resolver)
{
    codol_rechamber_resolver = resolver;
}
/* C1 0x4190af/0x4190ba: rechamber uses the serialized +0x5b0 while the akimbo
 * flag is set, otherwise +0x5ac, which is the retained iRechamberTime. */
static int rechamber_time(const struct WeaponDef *def, int dual_wield)
{
    int variant = 0;
    if(dual_wield && codol_rechamber_resolver &&
       codol_rechamber_resolver(def, &variant)) return variant;
    return def->iRechamberTime;
}

int CODOL_WeaponRechamberTime(const playerState_t *ps)
{
    const struct WeaponDef *def;
    if(!ps || !(def=weapon_def(ps->weapon))) return 0;
    /* C1 4190a4..4190c3 uses the selected weapon's akimbo flag for BOTH
     * hands: +5ac normally, +5b0 while dual wield. Selection produces that
     * flag from the same native definition byte resolved here. */
    return rechamber_time(def,CODOL_WeaponIsDualWield(ps->weapon));
}

void CODOL_SetWeaponSpinUpResolver(codol_weapon_spinup_resolver_t resolver)
{
    codol_spinup_resolver = resolver;
}
void CODOL_SetWeaponDetonateTriggerResolver(codol_weapon_flag_resolver_t resolver)
{
    codol_detonate_resolver = resolver;
}
void CODOL_SetWeaponHoldPinResolver(codol_weapon_flag_resolver_t resolver)
{
    codol_hold_resolver = resolver;
}

/* The input this pmove is executing, bound at the single acceptance point
 * rather than matched by time; see codol_weapon_input.h for why a serverTime
 * comparison cannot answer this and what each producer kind means. */
static int executed_input(const playerState_t *ps, codol_weapon_input_t *out)
{
    if(ps->clientNum < 0 || ps->clientNum >= MAX_CLIENTS) return 0;
    return CODOL_ExecutedWeaponInput((unsigned)ps->clientNum, out);
}
/* The two trigger bits of the CoDOL command word. Bit 0 is the one
 * codol_game.c copies into the native fire button; 0x100000 is the one it
 * folds into KEY_MASK_ADS, which is why a native ADS press on its own says
 * nothing about it and is never read as a second trigger here. */
#define CODOL_BUTTON_SECOND_TRIGGER 0x100000u
#define CODOL_BUTTON_PRIMARY_TRIGGER 0x1u

/* C1 0x41b1f0 resolves which button fires a given hand of a given weapon, and
 * the answer is not always bit 0:
 *
 *   weapType grenade with the serialized +0xbe0 byte set -> 0x100000 for any
 *     hand. Those are the remote-detonated pieces of equipment -- c4_mp,
 *     rcbomb_mp, radardirection_mp, airstrike_mp, ac130_mp and the killstreak
 *     variants in the shipped zones -- whose shot is the detonation.
 *   otherwise, while the akimbo flag is set: hand 0 -> 0x100000, hand 1 -> 0x1.
 *   otherwise:                               hand 0 -> 0x1, hand 1 -> 0x100000.
 *
 * def+0x340 is the CoDOL weapon type, which CODOL_ApplyNativeWeaponType already
 * maps onto the native weapType, so grenade is a real field here. The +0xbe0
 * byte has no retained field and is published by the asset side. */
static unsigned hand_request_mask(const struct WeaponDef *def, int dual_wield, unsigned hand)
{
    int detonated = 0;
    if(def->weapType == WEAPTYPE_GRENADE && codol_detonate_resolver &&
       codol_detonate_resolver(def, &detonated) && detonated)
        return CODOL_BUTTON_SECOND_TRIGGER;
    if(dual_wield)
        return hand ? CODOL_BUTTON_PRIMARY_TRIGGER : CODOL_BUTTON_SECOND_TRIGGER;
    return hand ? CODOL_BUTTON_SECOND_TRIGGER : CODOL_BUTTON_PRIMARY_TRIGGER;
}

/* Whether this hand's trigger is asking for a shot, for either hand.
 *
 * A network input answers from the raw CoDOL word with this hand's resolved
 * mask. A bot has no CoDOL word and no separate triggers: its single native
 * fire intent drives every hand it is holding, which is the whole of its input
 * rather than a zero standing in for one. A synthetic input carries no fire
 * intent at all. Native ADS is never read as the other trigger anywhere. */
static unsigned filtered_raw_buttons(unsigned raw);
static int hand_fire_requested(const playerState_t *ps, const struct pmove_t *pm,
                               const struct WeaponDef *def, int dual_wield, unsigned hand)
{
    codol_weapon_input_t input;
    unsigned mask = hand_request_mask(def, dual_wield, hand);
    if(!executed_input(ps, &input)) {
        /* No bound input: fall back to the command this pmove was handed, which
         * is all a caller outside the acceptance path can offer. */
        return mask == CODOL_BUTTON_PRIMARY_TRIGGER && pm &&
               (pm->cmd.buttons & KEY_MASK_FIRE) != 0;
    }
    /* The C1 pmove (CODOL_PmoveC1Try) runs this command and hands PM_Weapon
     * the C1 word after PmoveSingle's filters in pm->cmd.buttons -- frozen,
     * respawned, input-locked and dead commands already stripped -- which is
     * exactly the word C1's hand gate 0x41b240 tests. Read it from there, so a
     * frozen player's second hand cannot fire off the unfiltered raw word. */
    if(pm && CODOL_PmoveC1Active() &&
       (input.kind == CODOL_INPUT_NETWORK || (input.kind == CODOL_INPUT_BOT && input.raw_valid)))
        return ((unsigned)pm->cmd.buttons & mask) != 0;
    switch(input.kind) {
    case CODOL_INPUT_NETWORK: return (filtered_raw_buttons(input.raw_buttons) & mask) != 0;
    case CODOL_INPUT_BOT: return input.raw_valid ? (filtered_raw_buttons(input.raw_buttons) & mask)!=0 :
        (input.native_buttons & KEY_MASK_FIRE)!=0;
    default: return 0;
    }
}

/* The trigger word C1's hand gate 0x41b240 actually tests is pm->cmd.buttons
 * after PmoveSingle's input filters, which CODOL_FilterUsercmd transcribes: a
 * remote-controlling (0x200000) or input-locked (0x10000000) command keeps
 * neither trigger. The retained engine command is built from the filtered
 * word (CODOL_ToEngineUsercmd), so reading the raw word unfiltered here let a
 * hand fire through an input lock that the native fire bit already obeyed. */
static unsigned filtered_raw_buttons(unsigned raw)
{
    codol_usercmd_t wire, game;
    memset(&wire, 0, sizeof(wire));
    wire.buttons = raw;
    CODOL_FilterUsercmd(&wire, &game);
    return game.buttons;
}

/* C1 0x41b240, the hand fire gate: `call 0x41b1f0 / and eax, [pm+8]` at
 * 0x41b270..0x41b275. The trigger that opens hand 0 is the one 0x41b1f0
 * resolves for it, which for an akimbo weapon is the second trigger 0x100000,
 * not bit 0. The retained gate PM_Weapon_840, the fresh-pull edge
 * PM_Weapon_170 (C1 0x41ab10, old command at 0x41ab45/0x41ab59) and the
 * segmented-reload interrupt edge all tested bit 0 of the command the C1
 * pmove hands PM_Weapon, so on an akimbo weapon the attack button opened
 * hand 0 AND hand 1 (the native machine) while the second trigger opened
 * nothing, and hand 0's pin (CODOL_WeaponStatePinRequest, which asks for
 * 0x100000) never engaged: a semi-automatic gun emptied hand 0 at its fire
 * rate. They now test pm->cmd / pm->oldcmd with this mask.
 *
 * Only the dual-wield answer differs from bit 0 on those arms: for any other
 * weapon 0x41b1f0 gives hand 0 bit 0, and the remote-detonated grenade case
 * (0x100000 for any hand) belongs to the retained detonate arm, which does
 * not reach here. */
unsigned CODOL_WeaponStateHandZeroMask(const playerState_t *ps)
{
    const struct WeaponDef *def;
    if(!ps || !CODOL_WeaponStateIsDualWielding(ps) || !(def = weapon_def(ps->weapon)))
        return CODOL_BUTTON_PRIMARY_TRIGGER;
    return hand_request_mask(def, 1, 0);
}

/* C1 BG_PlayerCanAds 0x418140..0x418154: the first test of the whole predicate
 *
 *   00418140  cmp dword [edx+0x35c], 1      the akimbo flag
 *   00418147  mov ecx, 0xc00
 *   0041814c  jne 0x418156                  not akimbo: the ordinary tests
 *   0041814e  test [edx+0xec], ecx          eFlags turret/vehicle pair
 *   00418154  je  0x41816f                  -> return 0, no ADS
 *
 * An akimbo player cannot aim down the sights; the right mouse button is the
 * second hand's trigger (0x41b1f0). C1's CL_CmdButtons still sends the ADS bit
 * 0x800 for that button (0x48fc12 has no akimbo test), so the server must
 * refuse it here exactly as PM_UpdateAimDownSightFlag 0x418270 does, or it
 * raises PMF 0x10, lerps fWeaponPosFrac to 1 and publishes an aim the client's
 * own prediction never makes. */
int CODOL_WeaponStateBlocksAds(const playerState_t *ps)
{
    return ps && CODOL_WeaponStateIsDualWielding(ps) &&
           !(ps->eFlags & (int)PLAYER_EFLAG_TURRET_MASK);
}

/* The same question for the retained machine's own hand, which has no pmove in
 * hand at the point the request chain asks. */
int CODOL_WeaponStateFireRequest(const playerState_t *ps, unsigned hand)
{
    const struct WeaponDef *def;
    if(!ps || hand >= CODOL_WEAPON_HANDS || !(def = weapon_def(ps->weapon))) return 0;
    return hand_fire_requested(ps, NULL, def,
        (int)CODOL_PlayerStateHandRead(ps)->dual_wield, hand);
}

/* C1's double-barrel arm of the same pin decision, 0x41ae37..0x41ae6c.
 *
 *   0041ae37  cmp dword [esi+0x35c], 1      the akimbo flag; akimbo skips it
 *   0041ae40  je  0x41ae7b
 *   0041ae45  cmp dword [edx+0x350], 5      fireType double barrel
 *   0041ae4c  jne 0x41ae7b
 *   0041ae4e  mov edx, [esi+0x344]          the weapon-flags word
 *   0041ae54  and edx, 0x100                the armed barrel
 *   0041ae5a  je  0x41ae60
 *   0041ae5c  test eax, eax                 buttons & mask(0x41b1f0)
 *   0041ae5e  jne 0x41ae6c
 *   0041ae60  test edx, edx
 *   0041ae62  jne 0x41ae73
 *   0041ae64  test ecx, 0x100000            the raw second trigger
 *   0041ae6a  je  0x41ae73
 *   0041ae6c  mov dword [ebp-8], 0          the quota flag, cleared
 *
 * So a double barrel whose *other* trigger is asking does not pin: the barrel
 * that did not take the last shot is still owed and comes out on the same
 * magazine. Which trigger took the last shot is C1's ps+0x344 bit 0x100,
 * written at 0x41babc..0x41bae5 from the executing command's second trigger;
 * the retained playerState uses that bit for its own fresh-pull latch, so the
 * armed barrel is kept in the hand bundle and mirrored from there.
 *
 * Returns 1 when the quota flag must be cleared. The retained pin chain owns
 * every other term; this answers only the arm it does not have. */
int CODOL_WeaponStateDoubleBarrelReleasesPin(const playerState_t *ps, unsigned hand)
{
    const struct WeaponDef *def;
    const codol_weapon_state_t *state;
    codol_weapon_input_t input;
    unsigned armed, buttons;
    if(!ps || hand >= CODOL_WEAPON_HANDS || !(def = weapon_def(ps->weapon))) return 0;
    /* 0x41ae45: the arm is the double-barrel fire type, written as the CoDOL
     * number for the same reason hand_quota_done is. */
    if(def->fireType != 5) return 0;
    /* 0x41ae37: an akimbo weapon leaves before the arm; its two triggers are
     * two hands, not two barrels. */
    if(CODOL_PlayerStateHandRead(ps)->dual_wield) return 0;
    /* The command being executed, which is where C1 reads pm->cmd.buttons.
     * Without one there is no trigger to compare and nothing is released. */
    if(!executed_input(ps, &input)) return 0;
    if(input.kind != CODOL_INPUT_NETWORK && !input.raw_valid) return 0;
    buttons = input.raw_buttons;
    /* The live armed barrel: the producer records it at this frame's shot, as
     * C1 does at 0x41bae5, and publishes it afterwards. */
    state = state_of(ps);
    armed = state && state->second_barrel ? 1u : 0u;
    if(armed) return (buttons & hand_request_mask(def, 0, hand)) != 0;
    return (buttons & CODOL_BUTTON_SECOND_TRIGGER) != 0;
}

/* The command this pmove frame is executing, for the two double-barrel sites
 * below, with C1's two standing exclusions already applied: 0x41bb2a leaves on
 * the akimbo flag and 0x41bb41 leaves on any fire type but 5. */
static int double_barrel_command(const playerState_t *ps, const struct WeaponDef *def,
                                 unsigned *buttons)
{
    codol_weapon_input_t input;
    if(!ps || !def || def->fireType != WEAPON_FIRETYPE_DOUBLEBARREL) return 0;
    if(CODOL_PlayerStateHandRead(ps)->dual_wield) return 0;
    if(!executed_input(ps, &input)) return 0;
    if(input.kind != CODOL_INPUT_NETWORK && !input.raw_valid) return 0;
    *buttons = input.raw_buttons;
    return 1;
}

/* C1 0x41bb20: the half of the fire dispatch the retained machine has no
 * counterpart for.
 *
 *   0041bb2a  cmp dword [esi+0x35c], 1      akimbo leaves
 *   0041bb32  je  0x41bb9e
 *   0041bb41  cmp dword [ecx+0x350], 5      fireType double barrel
 *   0041bb48  jne 0x41bb9e
 *   0041bb4a  and dword [esi+0x344], ~0x200 the both-barrel flag, per frame
 *   0041bb54  mov ecx, [ebx+0x8]            the command's buttons
 *   0041bb5d  test ecx, 0x100000            the second trigger
 *   0041bb63  je  0x41bba8                  ... or nothing happens
 *   0041bb8f  xor eax, eax
 *   0041bb91  call 0x41b930                 fire HAND 0
 *
 * It runs at 0x41daf7, before the hand gate 0x41b240 at 0x41db03, and is
 * subject to the same weaponTime/weaponDelay test at 0x41da54..0x41da6a -- the
 * semi-automatic pin governs both triggers -- but to nothing else: the mask
 * 0x41b1f0 builds for hand 0 is bit 0 and never sees 0x100000.
 *
 * So in C1 the right trigger fires a barrel on its own. The previous pass here
 * concluded that it could not, reading the hand gate alone; that conclusion
 * missed this call and is withdrawn. */
int CODOL_WeaponStateSecondTriggerFires(const playerState_t *ps)
{
    const struct WeaponDef *def;
    unsigned buttons = 0;
    if(!ps || !(def = weapon_def(ps->weapon))) return 0;
    if(!double_barrel_command(ps, def, &buttons)) return 0;
    return (buttons & CODOL_BUTTON_SECOND_TRIGGER) != 0;
}

/* The request term C1 gates the semi-automatic pin on, which is not the plain
 * hand request. 0x41ae32 keeps `buttons & mask(0x41b1f0)` in EDI; 0x41ae73
 * then does `and ecx, 0x100000 / or eax, ecx` for a non-akimbo double barrel,
 * and 0x41ae9f gates the pin on that EAX while 0x41af3d clears the hand's shot
 * counter from the plain EDI. So the second trigger pins the weapon it just
 * fired, exactly as the first one does, but it does not keep the counter
 * alive on its own. */
int CODOL_WeaponStatePinRequest(const playerState_t *ps, unsigned hand)
{
    if(CODOL_WeaponStateFireRequest(ps, hand)) return 1;
    return CODOL_WeaponStateSecondTriggerFires(ps);
}

/* The same dispatch with BOTH triggers down: 0x41bb20 fires hand 0 and then
 * the gate at 0x41db03 fires hand 0 again, so 0x41b930 runs twice off one
 * command and both barrels leave in the same pmove frame. 0x41bb6a..0x41bb80
 * also raises ps+0x344 bit 0x200 when the magazine held more than one round,
 * which BG_WeaponFireRecoil squares the horizontal kick by at 0x00422407.
 *
 * The retained machine fires at most once per hand per frame, so the second
 * round is taken here, immediately after PM_Weapon_1370/1380 queued the first
 * one's event. Everything a retained shot does to the playerState is repeated:
 * PM_Weapon_2210's magazine decrement with its turret and player_sustainAmmo
 * exclusions, PM_Weapon_1320's saturating three-bit counter, the shot record
 * the recoil and snapshot producers index, and the fire event itself.
 *
 * One deliberate divergence: C1 still calls 0x41b930 for the second trigger
 * when the magazine is already empty and lets the fire routine dry-fire it.
 * The retained empty/reload handling owns that case, so an empty magazine
 * simply takes no extra round here. */
void CODOL_WeaponStateDoubleBarrelSecondShot(playerState_t *ps)
{
    const struct WeaponDef *def;
    unsigned buttons = 0;
    int clip, remaining;
    if(!ps || !(def = weapon_def(ps->weapon))) return;
    if(!double_barrel_command(ps, def, &buttons)) return;
    /* 0x41bb5d needs the second trigger, and the barrel the retained machine
     * just fired is the one the hand gate opened, so the extra round is owed
     * only when both triggers are down on the same command. */
    if((buttons & (CODOL_BUTTON_PRIMARY_TRIGGER | CODOL_BUTTON_SECOND_TRIGGER)) !=
       (CODOL_BUTTON_PRIMARY_TRIGGER | CODOL_BUTTON_SECOND_TRIGGER)) return;
    if(def->iClipIndex < 0 || def->iClipIndex >= 128) return;
    /* PM_Weapon_1310's lock gate refuses this round the way it refuses the
     * retained one, and without consuming anything. */
    if(CODOL_WeaponLockFireEvent(ps, def) != 0) return;
    clip = ps->ammoclip[def->iClipIndex];
    if(clip <= 0) return;
    if(!(ps->eFlags & PLAYER_EFLAG_TURRET_MASK) &&
       !(player_sustainAmmo && player_sustainAmmo->boolean) &&
       !CODOL_WeaponUnlimitedAmmo(def))
        ps->ammoclip[def->iClipIndex] = clip - 1;
    remaining = ps->ammoclip[def->iClipIndex];
    if(ps->weaponShotCount < 4u) ps->weaponShotCount += 1u;
    CODOL_WeaponStateRecordShot(ps, 0, remaining ? 0u : 1u);
    add_player_event(ps, remaining ? EV_FIRE_WEAPON : EV_FIRE_WEAPON_LASTSHOT);
}

/* One term of C1's hand decision, not the decision: see the header. The full
 * disassembly of 0x41adc6..0x41aed5 reads
 *
 *   [ebp-0x10] = hand[0x27c] & 1                       fresh trigger pull
 *   [ebp-8]    = !fresh_pull && quota_helper(0x41a9d0) quota spent
 *   [ebp-0xc]  = def[0x340] == grenade && def[0xbe4]   this term
 *   eax        = cmd.buttons & mask(0x41b1f0), plus 0x100000 for a
 *                double-barrel weapon after the arm at 0x41ae73
 *   0x41ae7b   weaponstate 16..21 leaves without pinning
 *   0x41ae8f   leaves unless [ebp-8] or [ebp-0xc]
 *   0x41ae9f   leaves unless eax                        a live request
 *   0x41aeae   leaves unless ps->weapon == pm->weapon
 *   0x41aec3   leaves unless BG_GetAmmoInClip(ps, def, hand)
 *   0x41aed5   hand[0x26c] = 1                          the hold
 *
 * The retained chain already carries every one of those but this term: the
 * quota is [ebp-0x4a] (PM_Weapon_1830 and its fireType arms), the request and
 * the ps/pm weapon match are PM_Weapon_1600, and the magazine test and the
 * weapon-time store are PM_Weapon_1620. My previous pass reported this term as
 * an unconditional hold and acted on it before any of those, which was wrong;
 * it now feeds the retained term at PM_Weapon_1580 instead. */
static int hand_weapon_always_pins(const struct WeaponDef *def);
int CODOL_WeaponStateWeaponHoldsFire(const playerState_t *ps, unsigned hand)
{
    const struct WeaponDef *def;
    if(!ps || hand >= CODOL_WEAPON_HANDS || !(def = weapon_def(ps->weapon))) return 0;
    return hand_weapon_always_pins(def);
}

/* ---- the offhand detonation phase ----------------------------------------
 *
 * C1 splits one thing the retained engine does not have at all: an offhand
 * weapon whose shot is a detonation rather than a throw. Two measured gates
 * feed it, and they are deliberately different gates:
 *
 *   PM_Weapon_CheckForOffHand 0x41cbaf..0x41cbc7 lets the sequence start at
 *     all. It calls BG_GetAmmoInClip(ps, def, 0) (0x40f220) and, when that is
 *     zero, refuses unless the definition carries the serialized byte +0xbe0.
 *     So a remote-detonated piece of equipment is the one offhand you may
 *     raise with an empty magazine. This is the *clip*, nothing else.
 *   PM_Weapon_OffHandPrepare 0x41c41b..0x41c431 then decides which phase to
 *     enter. It calls the total-ammo helper 0x41def0 -- reserve record at
 *     ps+0x360 keyed by def+0x568, plus the clip record at ps+0x3d8 keyed by
 *     def+0x570, plus that clip's second magazine while the weapon is akimbo
 *     -- and takes the detonation only when the definition carries +0xbe0 and
 *     that total is zero. Otherwise it queues EV_PREP_OFFHAND and throws.
 *
 * The retained engine reaches neither: BG_GetFirstAvailableOffhand returns 0
 * for an empty offhand and PM_Weapon_CheckForOffHand_110 emits
 * EV_EMPTY_OFFHAND instead of starting anything. Both helpers below are what
 * the retained sites ask so that it can. */
/* Both ammo indices have to be usable before a total means anything; a
 * definition that fails this is reported as uncountable rather than as zero,
 * because zero is the value that detonates. */
static int offhand_ammo_countable(const struct WeaponDef *def)
{
    return def->iAmmoIndex >= 0 && def->iAmmoIndex < 128 &&
           def->iClipIndex >= 0 && def->iClipIndex < 128;
}
static int offhand_total_ammo(const playerState_t *ps, const struct WeaponDef *def)
{
    int total, second = 0;
    /* The retained playerState carries the reserve and the first magazine in
     * the two flat arrays the CoDOL records index by key; the second magazine
     * is only in the hand bundle. PM_Weapon's own ammo test at the throw
     * (PM_Weapon_940) adds exactly the first two. */
    if(def->iAmmoIndex < 0 || def->iAmmoIndex >= 128 ||
       def->iClipIndex < 0 || def->iClipIndex >= 128) return 0;
    total = ps->ammo[def->iAmmoIndex] + ps->ammoclip[def->iClipIndex];
    if(CODOL_WeaponIsDualWield((unsigned)ps->offHandIndex) &&
       CODOL_WeaponStateClipAmmoByIndex(ps, def->iClipIndex, 1, &second)) total += second;
    return total;
}
static int weapon_detonates(const struct WeaponDef *def)
{
    int value = 0;
    return codol_detonate_resolver && codol_detonate_resolver(def, &value) && value != 0;
}
int CODOL_WeaponStateOffhandDetonates(const playerState_t *ps)
{
    const struct WeaponDef *def;
    int total;
    /* An unresolvable definition takes no CoDOL branch at all: 0 leaves the
     * retained prepare exactly as it was, which is the only behaviour this
     * engine can still carry out. C1 does not validate here -- it indexes
     * bg_weaponDefs directly -- so the check is ours, not a divergence in the
     * decision it guards. */
    if(!ps || !(def = weapon_def((unsigned)ps->offHandIndex))) return 0;
    if(!weapon_detonates(def)) return 0;
    if(!offhand_ammo_countable(def)) return 0;
    total = offhand_total_ammo(ps, def);
    /* C1 0x41c42f is `test eax, eax / jne`: the detonation is taken on exactly
     * zero, and any non-zero total -- including a negative one -- throws. The
     * previous <= 0 here turned a negative total into a detonation, which is
     * the opposite of the branch. */
    return total == 0;
}
/* ---- offhand selection ---------------------------------------------------
 *
 * C1 does not search the inventory for an offhand of a class. It reads one of
 * three *selected* weapons out of the playerState and raises that one.
 * PM_Weapon_CheckForOffHand 0x41cb41..0x41cba2 is three identical arms:
 *
 *   0x41cb41  ecx = 0x4000   slot ps+0x32c
 *   0x41cb62  ecx = 0x8000   slot ps+0x330
 *   0x41cb80  ecx = 0x10000  slot ps+0x334
 *
 * and each arm takes its slot only when the button is set in cmd.buttons, is
 * *not* set in oldcmd.buttons (`test dword [esi+0x30], ecx`) and is not set in
 * the playerState's own weapon-flags word (`test dword [edi+0x344], ecx`).
 * C1 40c7e0 first accepts an exact weapon match in ANY selected slot. Its
 * fallback permits a class when the corresponding conventional slot is empty:
 * classes1/4 for0x32c,2/3 for0x330,5 for0x334. That fallback is not a
 * restriction on which classes the server may explicitly assign to a button.
 *
 * Nothing in C1's .text writes those three words, and nothing writes the
 * per-button bits of +0x344 except one clear of 0x10000 at 0x41a0c0. Both are
 * authored by the server -- they are 32-bit playerState wire fields
 * (codol_player_fields.inc carries 0x032c, 0x0330 and 0x0334) that the client
 * only reads. So the selection itself is implementation work on this side; what
 * is measured is the consumer, and that is what this reproduces.
 *
 * Two gates follow the slot, and neither is the class scan's ammo test:
 *   0x41cbaf  BG_GetAmmoInClip(ps, def, hand 0) may be zero only when the
 *             definition carries +0xbe0 -- the remote-detonated equipment.
 *   0x41cbcd  when the definition carries +0xbe5, ps+0xa8 must not be 0x7ff.
 *             ps+0xa8 is groundEntityNum: it is written with that sentinel by
 *             a dozen sites in the movement code (0x408aaf .. 0x416849),
 *             assigned from a trace result at 0x411baa, compared against the
 *             sentinel throughout PM_ movement, and published to entityState
 *             +0x88 by BG_PlayerStateToEntityState at 0x40d15b -- which is the
 *             field CODOL_OverlayEngineMovement already publishes as
 *             groundEntityNum. The same pair gates the fire request at
 *             0x41b2aa..0x41b2bf. So a +0xbe5 weapon may only be raised or
 *             fired while the player is standing on something. */
#define CODOL_OFFHAND_BUTTON_FRAG      0x4000u
#define CODOL_OFFHAND_BUTTON_SPECIAL   0x8000u
#define CODOL_OFFHAND_BUTTON_EQUIPMENT 0x10000u

static codol_weapon_flag_resolver_t codol_ground_resolver;
void CODOL_SetWeaponRequiresGroundResolver(codol_weapon_flag_resolver_t resolver)
{
    codol_ground_resolver = resolver;
}
static int weapon_requires_ground(const struct WeaponDef *def)
{
    int value = 0;
    return codol_ground_resolver && codol_ground_resolver(def, &value) && value != 0;
}

/* The three button words this frame and the frame before, in CoDOL spelling.
 *
 * Only a network input has a CoDOL word. A bot's native command carries the
 * two retained offhand bits at the same positions -- CODOL_ToEngineUsercmd
 * keeps 0x4000 and 0x8000 through its 0xff3f mask -- but never 0x10000, which
 * it drops entirely, so a bot can express two of the three buttons and not the
 * third. That is the whole of a bot's input rather than a zero standing in for
 * a word it never sent. A synthetic pmove expresses none. */
/* C1 PmoveSingle 0x416022..0x4160ab filters the command it hands PM_Weapon,
 * after Pmove 0x416c40 already reduced a remote-controlling command to
 * 0x80300: frozen (pm_flags 0x800) keeps 0x1300, a respawned player (0x400)
 * keeps 0x1301, an input-locked command (0x10000000) keeps 0x10001b02 and
 * otherFlags 0x10000000 drops the trigger. The C1 pmove port already runs
 * these on pm->cmd; this is the same filter for a caller without it. */
static unsigned c1_pmove_buttons(const playerState_t *ps, unsigned raw)
{
    unsigned buttons = filtered_raw_buttons(raw);
    if((unsigned)ps->pm_flags & 0x80000u) buttons &= 0x80300u;
    if((unsigned)ps->pm_flags & 0x800u) buttons &= 0x1300u;
    else if((unsigned)ps->pm_flags & 0x400u) buttons &= 0x1301u;
    if(buttons & 0x10000000u) buttons &= 0x10001b02u;
    if((unsigned)ps->otherFlags & 0x10000000u) buttons &= ~1u;
    return buttons;
}

/* Which pmove substep of the executed command is running. C1 Pmove copies the
 * filtered command over oldcmd after every PmoveSingle (0x416cb0), so only
 * the first substep compares against the previous command; later ones compare
 * against this command's own filtered copy, which the C1 pmove port leaves in
 * pm->oldcmd. Keyed by the executed command's time and the first substep's. */
static int edge_command_time[MAX_CLIENTS];
static int edge_first_substep[MAX_CLIENTS];
static unsigned char edge_known[MAX_CLIENTS];
static int first_substep(const playerState_t *ps, const codol_weapon_input_t *input,
                         const struct pmove_t *pm)
{
    unsigned client = (unsigned)ps->clientNum;
    int command_time = (int)input->raw.serverTime;
    if(!pm || client >= MAX_CLIENTS) return 1;
    if(!edge_known[client] || edge_command_time[client] != command_time) {
        edge_known[client] = 1;
        edge_command_time[client] = command_time;
        edge_first_substep[client] = pm->cmd.serverTime;
        return 1;
    }
    return pm->cmd.serverTime == edge_first_substep[client];
}

static int offhand_buttons(const playerState_t *ps, const struct pmove_t *pm,
                           unsigned *now, unsigned *before)
{
    const unsigned native = CODOL_OFFHAND_BUTTON_FRAG | CODOL_OFFHAND_BUTTON_SPECIAL;
    codol_weapon_input_t input;
    if(!ps) return 0;
    if(executed_input(ps, &input) && (input.kind == CODOL_INPUT_NETWORK || input.raw_valid)) {
        /* C1 tests cmd.buttons (pm+0x08) after PmoveSingle's filters and
         * oldcmd.buttons (pm+0x30), the previous command exactly as the client
         * sent it: CG_PredictPlayerState reads oldcmd as command number - 1,
         * including one it skipped for an equal millisecond. The input binder
         * keeps that word, duplicates included (sv_client.c). */
        if(pm && CODOL_PmoveC1Active() && input.raw_valid)
            *now = (unsigned)pm->cmd.buttons;
        else *now = c1_pmove_buttons(ps, input.raw_buttons);
        if(input.raw_valid && pm && CODOL_PmoveC1Active() && !first_substep(ps, &input, pm))
            *before = (unsigned)pm->oldcmd.buttons;
        /* No previous CoDOL word means no previous state to compare against,
         * so every raised bit reads as the rising edge C1 requires. */
        else *before = input.previous_raw_valid ? input.previous_raw_buttons : 0u;
        return 1;
    }
    if(!pm) return 0;
    if(executed_input(ps, &input) && input.kind == CODOL_INPUT_SYNTHETIC) return 0;
    *now = (unsigned)pm->cmd.buttons & native;
    *before = (unsigned)pm->oldcmd.buttons & native;
    return 1;
}

unsigned CODOL_WeaponStateSelectOffhand(const playerState_t *ps, const struct pmove_t *pm)
{
    static const unsigned buttons[CODOL_OFFHAND_SLOTS] = {
        CODOL_OFFHAND_BUTTON_FRAG,
        CODOL_OFFHAND_BUTTON_SPECIAL,
        CODOL_OFFHAND_BUTTON_EQUIPMENT
    };
    const codol_ps_offhand_t *slots;
    const struct WeaponDef *def;
    unsigned now = 0, before = 0, i, weapon = 0;
    if(!ps || !offhand_buttons(ps, pm, &now, &before)) return 0;
    /* C1 41ca10 precedes ordinary slot selection: held use/frag button,
     * positive remaining fuse, a cursor target, and ps+40 captured weapon.
     * No ownership or rising-edge requirement applies to a thrown grenade. */
    if((now&CODOL_OFFHAND_BUTTON_FRAG) && ps->throwBackGrenadeTimeLeft>0 &&
       (unsigned)ps->cursorHintEntIndex<ENTITYNUM_WORLD) {
        const codol_ps_ext_t *extension=CODOL_PlayerStateExtConst(ps);
        if(extension && extension->throwback_weapon &&
           extension->throwback_weapon<(unsigned)BG_GetNumWeapons())
            return extension->throwback_weapon;
    }
    slots = CODOL_PlayerStateOffhandRead(ps);
    /* A state that never had a selection recorded selects nothing. It is not
     * the same as three empty slots and must not be filled in from anywhere. */
    if(!slots->known) return 0;
    for(i = 0; i < CODOL_OFFHAND_SLOTS; ++i) {
        if(!(now & buttons[i]) || (before & buttons[i])) continue;
        if((unsigned)ps->weapFlags & buttons[i]) continue;
        weapon = slots->weapon[i];
        break;
    }
    if(i == CODOL_OFFHAND_SLOTS || !weapon) return 0;
    /* C1 indexes bg_weaponDefs with the slot unchecked; an unusable index here
     * selects nothing rather than reading past the table. */
    if(!(def = weapon_def(weapon))) return 0;
    if(def->iClipIndex < 0 || def->iClipIndex >= 128) return 0;
    /* The retained ammoclip is the first magazine C1's BG_GetAmmoInClip
     * returns for hand 0; the bundle carries only the second. */
    if(ps->ammoclip[def->iClipIndex] == 0 && !weapon_detonates(def)) return 0;
    if(weapon_requires_ground(def) && ps->groundEntityNum >= ENTITYNUM_NONE) return 0;
    return weapon;
}

/* ---- offhand init, hold and cancel ----------------------------------------
 *
 * The retained machine carries the init -> prepare -> hold -> throw sequence;
 * these are the C1 decisions inside it that it does not make. */
#define CODOL_BUTTON_OFFHAND_ANY    0x1c000u
#define CODOL_BUTTON_OFFHAND_CANCEL 0x400000u
#define C1_WEAPON_CLASS_THROWINGKNIFE 9u
void __cdecl CODOL_WeaponOffhandPhaseTime(playerState_t *ps);

/* C1 0x41e3c0, the magazine decrement every shot goes through, returns
 * before touching the clip record when def+0x560 is set (0x41e3cf), so such a
 * weapon fires for as long as its owner holds it. minigun_zm is the only
 * shipped definition with the byte: the zombies power-up limits it by time
 * (_zombiemode_powerups.gsc), not by its 500-round magazine. */
int __cdecl CODOL_WeaponUnlimitedAmmo(const struct WeaponDef *def)
{
    int value = 0;
    return def && CODOL_GetNativeWeaponUnlimitedAmmo(def, &value) && value != 0;
}

static int offhand_cancels(const struct WeaponDef *def)
{
    int value = 0;
    return def && CODOL_GetNativeWeaponOffhandCancel(def, &value) && value != 0;
}
static int offhand_holds_pin(const struct WeaponDef *def)
{
    int value = 0;
    return def && codol_hold_resolver && codol_hold_resolver(def, &value) && value != 0;
}
/* C1 0x41c5a0: one of the three offhand buttons is down and its restriction
 * (C1 weapFlags 0x20000/0x40000/0x80000) is clear. This engine keeps the three
 * restrictions as the single CODOL_WEAP_OFFHAND_DISABLED bit and publishes it
 * as all three (CODOL_OverlayEngineOffhandControl). */
static int offhand_button_allowed(const playerState_t *ps, unsigned buttons)
{
    if((unsigned)ps->weapFlags & CODOL_WEAP_OFFHAND_DISABLED) return 0;
    return (buttons & CODOL_BUTTON_OFFHAND_ANY) != 0;
}

/* C1 0x41c387..0x41c39d: PM_Weapon_OffHandInit calls PM_Weapon_OffHandPrepare
 * itself when the offhand's serialized weapon class (+0x344) is 9. The
 * retained class is remapped, so the serialized one is asked for. */
int CODOL_WeaponStateOffhandPreparesAtInit(const playerState_t *ps)
{
    const struct WeaponDef *def;
    unsigned weapon_class = 0;
    if(!ps || !(def = weapon_def((unsigned)ps->offHandIndex))) return 0;
    return CODOL_GetNativeWeaponClass(def, &weapon_class) &&
           weapon_class == C1_WEAPON_CLASS_THROWINGKNIFE;
}

/* C1 PM_Weapon_OffHandEnd 0x41c860, reached early by a cancel. The retained
 * end is the same writes spread over PM_Weapon_2390/980/2010: back to the
 * weapon with the quick raise, or a one-millisecond delay with no weapon. */
static void offhand_end(playerState_t *ps)
{
    const struct WeaponDef *def = weapon_def((unsigned)ps->weapon);
    if(!ps->weapon || !def) {
        ps->weaponTime = 0;
        ps->weaponDelay = 1;
    } else {
        ps->weaponTime = def->quickRaiseTime;
        CODOL_WeaponOffhandPhaseTime(ps); /* C1 0x41c8f8 */
        ps->weaponDelay = 0;
        if(ps->pm_type < 8)
            ps->weapAnim = (int)(ANIM_RAISE_QUICK | ((~(unsigned)ps->weapAnim) & ANIM_RESTART_BIT));
    }
    ps->weaponstate = 20;
    ps->weapFlags &= ~2;
    ps->pm_flags &= ~0x200;
    ps->throwBackGrenadeTimeLeft = 0;
    ps->throwBackGrenadeOwner = ENTITYNUM_NONE;
    CODOL_WeaponStateOffhandEndNotify(ps);
}
void __cdecl CODOL_WeaponStateOffhandEndNotify(playerState_t *ps)
{
    if(ps) add_player_event(ps, (BGEvent)CODOL_EV_OFFHAND_END_NOTIFY);
}

/* C1 0x41c5f0, the hold (C1 18, native 18). Taken in C1's order: a held-pin
 * weapon and a disabled weapon throw at once; otherwise the throw waits while
 * an offhand button is down in both this command and the one before it -- the
 * raw CoDOL word, so the equipment button 0x10000 counts as well as the two
 * the native command carries -- and the cancel button ends a +0xbec weapon
 * without throwing it (0x41c638..0x41c650, fuse cleared). */
int CODOL_WeaponStateOffhandHold(playerState_t *ps, const struct pmove_t *pm)
{
    const struct WeaponDef *def;
    unsigned now = 0, before = 0;
    if(!ps || !(def = weapon_def((unsigned)ps->offHandIndex))) return 0;
    if(offhand_holds_pin(def)) return 0;
    if((unsigned)ps->weapFlags & 0x80u) return 0;
    if(!offhand_buttons(ps, pm, &now, &before)) return 0;
    if(!offhand_button_allowed(ps, now)) return 0;
    if(!(before & CODOL_BUTTON_OFFHAND_ANY) || !(now & CODOL_BUTTON_OFFHAND_ANY)) return 0;
    if(offhand_cancels(def) && (now & CODOL_BUTTON_OFFHAND_CANCEL)) {
        offhand_end(ps);
        ps->grenadeTimeLeft = 0;
        return 2;
    }
    return 1;
}

/* C1 0x41ce70, run every frame after the detonation check: in prepare (C1 17)
 * a held-pin offhand ends as soon as no offhand button is down; otherwise, in
 * init or prepare (C1 16/17), a +0xbec offhand ends on the cancel button. */
void CODOL_WeaponStateOffhandCancelCheck(struct pmove_t *pm)
{
    playerState_t *ps;
    const struct WeaponDef *def;
    unsigned now = 0, before = 0;
    if(!pm || !(ps = pm->ps)) return;
    if(ps->weaponstate != 15 && ps->weaponstate != 16) return;
    if(!(def = weapon_def((unsigned)ps->offHandIndex))) return;
    if(!offhand_buttons(ps, pm, &now, &before)) return;
    if(ps->weaponstate == 16 && offhand_holds_pin(def)) {
        if(!(now & CODOL_BUTTON_OFFHAND_ANY)) offhand_end(ps);
        return;
    }
    if(offhand_cancels(def) && (now & CODOL_BUTTON_OFFHAND_CANCEL)) offhand_end(ps);
}

/* ---- dolphin-dive weapon phases -------------------------------------------
 *
 * C1 0x4089d0 ends the loop once the dive slides: dvar "2332" (a bool
 * registered at 0x408720 with default 1, nothing in this server changes it),
 * PMF_DIVETOPRONE, and jumpTime below zero -- codol_dive.c writes -now at the
 * touchdown, exactly as C1 0x409022 does. */
#define C1_PMF_DIVETOPRONE 0x40000000u
#define C1_DIVE_SLIDE_ENDS_LOOP 1
static int dive_phase(int state)
{
    return state >= CODOL_WEAPONSTATE_DIVE_IN && state <= CODOL_WEAPONSTATE_DIVE_OUT;
}
static int dive_sliding(const playerState_t *ps)
{
    return C1_DIVE_SLIDE_ENDS_LOOP && ((unsigned)ps->pm_flags & C1_PMF_DIVETOPRONE) &&
           ps->jumpTime < 0;
}
/* Source +0x630 / +0x638, already loaded into the core's timing record. */
static int dive_time(const struct WeaponDef *def, int leaving)
{
    codol_weapon_timing_extensions_t timings;
    int dual_mag = 0;
    if(!def || !CODOL_GetNativeWeaponReloadData(def, &dual_mag, &timings)) return 0;
    return leaving ? timings.dive_out : timings.dive_in;
}
/* C1 0x41d1f0/0x41d350/0x41d2a0 for hand 0: the phase, its time, a zero
 * delay, and animation 35/36/37 (38/39/40 with an empty magazine, 0x41e3f0),
 * restarted only when it changes -- which every dive transition does. */
static void set_dive_phase(playerState_t *ps, int phase, int time)
{
    const struct WeaponDef *def = weapon_def((unsigned)ps->weapon);
    int clip = clip_of(def);
    unsigned animation = clip >= 0 && ps->ammoclip[clip] == 0 ?
        CODOL_ANIM_DIVE_EMPTY : CODOL_ANIM_DIVE;
    ps->weaponstate = phase;
    ps->weaponTime = time;
    ps->weaponDelay = 0;
    if(ps->pm_type < 8)
        ps->weapAnim = (int)(animation | ((~(unsigned)ps->weapAnim) & ANIM_RESTART_BIT));
}
/* C1 0x41d4b0: a weapon selected in the command, a hand state outside
 * raise/drop (1..5), fire/rechamber (6, 7), melee (13..15), the offhand
 * sequence (16..21) and the dive itself, the dive flag up and not yet
 * sliding. Reload, sprint and night vision are left for the dive. */
void CODOL_WeaponStateDiveCheck(struct pmove_t *pm)
{
    playerState_t *ps;
    int state;
    if(!pm || !(ps = pm->ps)) return;
    if(!CODOL_UsercmdWeapon(&pm->cmd)) return;
    state = ps->weaponstate;
    if((state >= 1 && state <= 6) || (state >= 12 && state <= 20) ||
       state == CODOL_WEAPONSTATE_OFFHAND_DETONATE || dive_phase(state)) return;
    if(!((unsigned)ps->pm_flags & C1_PMF_DIVETOPRONE) || dive_sliding(ps)) return;
    set_dive_phase(ps, CODOL_WEAPONSTATE_DIVE_IN,
                   dive_time(weapon_def((unsigned)ps->weapon), 0));
}
void CODOL_WeaponStateDiveInDone(playerState_t *ps)
{
    if(ps) set_dive_phase(ps, CODOL_WEAPONSTATE_DIVE_LOOP, 0);
}
void CODOL_WeaponStateDiveLoop(playerState_t *ps)
{
    if(!ps) return;
    if(!dive_sliding(ps) && ((unsigned)ps->pm_flags & C1_PMF_DIVETOPRONE)) return;
    set_dive_phase(ps, CODOL_WEAPONSTATE_DIVE_OUT,
                   dive_time(weapon_def((unsigned)ps->weapon), 1));
}

/* Conventional lethal/tactical/equipment grouping for setoffhandequipment.
 * This is loadout policy, not a C1 restriction on explicitly assigned slots.
 * The primary-class setter below deliberately assigns any requested class to
 * primary slot0; the client honors that explicit assignment. */
static int offhand_slot_of_class(int offhand_class)
{
    switch(offhand_class) {
    case 1: case 4: return 0;
    case 2: case 3: return 1;
    case 5: return 2;
    default: return -1;
    }
}
static int offhand_slot_of_weapon(unsigned weapon)
{
    const struct WeaponDef *def = weapon_def(weapon);
    return def ? offhand_slot_of_class((int)def->offhandClass) : -1;
}
int CODOL_WeaponStateOffhandSlotForWeapon(unsigned weapon)
{
    return offhand_slot_of_weapon(weapon);
}
unsigned CODOL_WeaponStateWeaponForName(const char *name)
{
    unsigned weapon;
    int count;
    /* The retained BG_GetWeaponIndexForName is an assembly global that takes an
     * error callback and has no C declaration; this is the same lookup over the
     * same table, bounded by the same weapon_def() range check the rest of this
     * file uses, and it reports "not found" instead of raising. */
    if(!name || !*name || (count = BG_GetNumWeapons()) <= 0) return 0;
    if(count > CODOL_WEAPON_STATE_WEAPONS) count = CODOL_WEAPON_STATE_WEAPONS;
    for(weapon = 1; weapon < (unsigned)count; ++weapon) {
        const struct WeaponDef *def = weapon_def(weapon);
        if(def && def->szInternalName && !strcmp(def->szInternalName, name)) return weapon;
    }
    return 0;
}
int CODOL_WeaponStateSetOffhandSlots(playerState_t *ps, const unsigned weapon[3])
{
    codol_ps_offhand_t *slots;
    codol_weapon_state_t *state;
    unsigned i;
    if(!ps || !weapon) return 0;
    /* Check the whole set first: alpha0022's set_class replaces all three
     * together, and a set that is rejected must leave the previous selection
     * exactly as it was rather than applying the entries that happened to
     * come before the bad one. */
    for(i = 0; i < CODOL_OFFHAND_SLOTS; ++i) {
        if(!weapon[i]) continue;
        if(weapon[i] >= CODOL_WEAPON_STATE_WEAPONS) return 0;
        /* C1 40c82a/40c83c/40c84f accepts an exact selection in any
         * slot. Only automatic fallback uses conventional class grouping. */
        if(offhand_slot_of_weapon(weapon[i]) < 0) return 0;
    }
    if(!(slots = CODOL_PlayerStateOffhandMutable(ps))) return 0;
    /* Whole-loadout assignment replaces both automatic class selections.
     * Getters still describe the explicitly assigned classes. */
    state=state_of(ps);
    if(state) {
        state->offhand_primary_known=state->offhand_secondary_known=0;
        state->offhand_primary_class=weapon[0]?(unsigned char)weapon_def(weapon[0])->offhandClass:0;
        state->offhand_secondary_class=weapon[1]?(unsigned char)weapon_def(weapon[1])->offhandClass:0;
    }
    slots->known = 1;
    for(i = 0; i < CODOL_OFFHAND_SLOTS; ++i) slots->weapon[i] = (uint16_t)weapon[i];
    return 1;
}
void CODOL_WeaponStateOffhandReleased(playerState_t *ps,unsigned weapon)
{
    codol_ps_offhand_t *slots;
    unsigned slot;
    if(!ps || !weapon || !(slots=CODOL_PlayerStateOffhandMutable(ps))) return;
    slots->known=1;
    for(slot=0;slot<CODOL_OFFHAND_SLOTS;++slot)
        if(slots->weapon[slot]==weapon) slots->weapon[slot]=0;
}
int CODOL_WeaponStateOffhandSlot(const playerState_t *ps, unsigned slot, unsigned *weapon)
{
    const codol_ps_offhand_t *slots;
    if(!ps || !weapon || slot >= CODOL_OFFHAND_SLOTS) return 0;
    slots = CODOL_PlayerStateOffhandRead(ps);
    if(!slots->known) return 0;
    *weapon = slots->weapon[slot];
    return 1;
}

/* ---- Persistent offhand classes ----------------------------------
 * IW4 5d94d0 records the class; CoDOL needs a concrete slot selection as
 * well. C1 40c82a/40c83c/40c84f accept a weapon already in ANY slot before
 * their class-based empty-slot fallback. C1 41cb41..41cba8 raises the weapon
 * in the pressed slot directly, without a class-to-button check. Therefore
 * all five nonzero classes can be published in primary slot0 or secondary
 * slot1; class0 disables the requested slot. Each preference is independent.
 */
/* Prefer the first owned weapon the C1 selector can use. Keep an owned
 * fallback when all magazines are empty so later ammo grants need no new
 * script call. These slots are server-authored; C1 does no inventory scan.
 * Ground restrictions are checked when the input is executed, not used to
 * change equipment every time the player leaves the ground. */
static unsigned owned_weapon_of_class(const playerState_t *ps,unsigned class_index)
{
    unsigned weapon,fallback=0;
    int count=BG_GetNumWeapons();
    if(!class_index || count<=0) return 0;
    if(count>CODOL_WEAPON_STATE_WEAPONS) count=CODOL_WEAPON_STATE_WEAPONS;
    for(weapon=1;weapon<(unsigned)count;++weapon) {
        const struct WeaponDef *def;
        if(!owns_weapon(ps,weapon) || !(def=weapon_def(weapon)) ||
           (unsigned)def->offhandClass!=class_index) continue;
        if(!fallback) fallback=weapon;
        if(def->iClipIndex>=0 && def->iClipIndex<128 &&
           (ps->ammoclip[def->iClipIndex]!=0 || weapon_detonates(def))) return weapon;
    }
    return fallback;
}
void CODOL_WeaponStateRefreshOffhands(playerState_t *ps)
{
    const codol_weapon_state_t *state=state_of(ps);
    codol_ps_offhand_t *slots;
    unsigned slot;
    if(!state || !state->initialized) return;
    if(!(slots=CODOL_PlayerStateOffhandMutable(ps))) return;
    /* A take may also remove an alternate chain. Clear actual assignments
     * whose ownership vanished, not just the original API argument. */
    if(slots->known)
        for(slot=0;slot<CODOL_OFFHAND_SLOTS;++slot)
            if(slots->weapon[slot] && !owns_weapon(ps,slots->weapon[slot])) slots->weapon[slot]=0;
    if(state->offhand_primary_known) {
        slots->known=1;
        slots->weapon[0]=(uint16_t)owned_weapon_of_class(ps,state->offhand_primary_class);
    }
    if(state->offhand_secondary_known) {
        slots->known=1;
        slots->weapon[1]=(uint16_t)owned_weapon_of_class(ps,state->offhand_secondary_class);
    }
}
int CODOL_WeaponStateSetOffhandPrimaryClass(playerState_t *ps,unsigned class_index)
{
    codol_weapon_state_t *state=state_of(ps);
    if(!state || class_index>=CODOL_OFFHAND_PRIMARY_CLASS_COUNT) return 0;
    if(!state->initialized) CODOL_ResetClientWeaponState((unsigned)ps->clientNum);
    if(!CODOL_PlayerStateOffhandMutable(ps)) return 0;
    state->offhand_primary_class=(unsigned char)class_index;
    state->offhand_primary_known=1;
    CODOL_WeaponStateRefreshOffhands(ps);
    return 1;
}
int CODOL_WeaponStateOffhandPrimaryClass(const playerState_t *ps,unsigned *class_index)
{
    const codol_weapon_state_t *state=state_of(ps);
    if(!state || !state->initialized || !class_index) return 0;
    *class_index=state->offhand_primary_class; return 1;
}
int CODOL_WeaponStateSetOffhandSecondaryClass(playerState_t *ps,unsigned class_index)
{
    codol_weapon_state_t *state=state_of(ps);
    if(!state || class_index>=CODOL_OFFHAND_PRIMARY_CLASS_COUNT) return 0;
    if(!state->initialized) CODOL_ResetClientWeaponState((unsigned)ps->clientNum);
    if(!CODOL_PlayerStateOffhandMutable(ps)) return 0;
    state->offhand_secondary_class=(unsigned char)class_index;
    state->offhand_secondary_known=1;
    CODOL_WeaponStateRefreshOffhands(ps);
    return 1;
}
int CODOL_WeaponStateOffhandSecondaryClass(const playerState_t *ps,unsigned *class_index)
{
    const codol_weapon_state_t *state=state_of(ps);
    if(!state || !state->initialized || !class_index) return 0;
    *class_index=state->offhand_secondary_class; return 1;
}
void CODOL_WeaponStateOffhandGranted(playerState_t *ps,unsigned weapon)
{
    if(ps && weapon && owns_weapon(ps,weapon)) CODOL_WeaponStateRefreshOffhands(ps);
}

/* Retained BG_LoadPlayerAnimTypes (_bg_weapons_load_obj.asm) fills these from
 * mp/playeranimtypes.txt; WeaponDef.playerAnimType indexes them. */
extern const char *g_playerAnimTypeNames[];
extern int g_playerAnimTypeNamesCount;

/* C1 BG_PlayerStateToEntityState 0x40d104..0x40d13d, entityState +0x60:
 *   weaponstate ps+0x278 in 16..20 (offhand init, prepare, hold, fire and
 *   offhand detonation - not 21, the end) and the offhand ps+0x328's
 *   definition +0x33c (player animation type) equal to the index of "hold"
 *   (0x41ea5b looks the name up and keeps it at 0x150c694)
 *   -> the offhand, else 0.
 * "hold" is the placed equipment: claymore, C4, bouncing betty, scrambler. */
static unsigned held_offhand_weapon(const playerState_t *ps)
{
    const struct WeaponDef *def;
    unsigned state;
    int i, hold = -1;
    if(ps->offHandIndex <= 0 || (unsigned)ps->offHandIndex >= CODOL_WEAPON_SLOTS ||
       !CODOL_TranslateEngineWeaponState((unsigned)ps->weaponstate, &state) ||
       state < 16 || state > 20) return 0;
    for(i = 0; i < g_playerAnimTypeNamesCount && i < 64; ++i)
        if(g_playerAnimTypeNames[i] && !Q_stricmp(g_playerAnimTypeNames[i], "hold")) { hold = i; break; }
    def = weapon_def((unsigned)ps->offHandIndex);
    return hold >= 0 && def && def->playerAnimType == hold ? (unsigned)ps->offHandIndex : 0;
}

void CODOL_WeaponStateCaptureEntityWeapon(const playerState_t *ps, struct entityState_s *es)
{
    unsigned primary = 0;
    int resolved;
    if(!ps || !es) return;
    /* An unresolvable pair is recorded as unresolved rather than left alone:
     * the consumer then reports the entity as uncaptured instead of publishing
     * either a guess or the pair some earlier frame captured for it. */
    resolved = CODOL_WeaponStatePrimaryWeapon(ps, &primary);
    CODOL_EntityStatePrimaryWeaponCaptured(es, primary, resolved);
    CODOL_EntityStateHeldOffhandCaptured(es, held_offhand_weapon(ps));
}

/* C1 0x4183e0, called from PM_Weapon at 0x41dbf1 once per frame with the pmove:
 * a fire type 6 weapon charges by msec/spinUpTime while the trigger is held and
 * decays by -msec/spinDownTime otherwise, clamped to 0..1 (0x418456); anything
 * else parks the charge at zero (0x418469). The weapon is the offhand while the
 * offhand viewmodel flag is up, exactly as the hand count is chosen. */
static void update_spinup_charge(codol_weapon_state_t *state, const playerState_t *ps,
                                 const struct pmove_t *pm, int msec)
{
    const struct WeaponDef *def;
    int up = 0, down = 0;
    float rate, charge;
    def = weapon_def((ps->weapFlags & 0x2) ? (unsigned)ps->offHandIndex : ps->weapon);
    if(!def || def->fireType != 6) { state->spinup_charge = 0.0f; return; }
    if(!codol_spinup_resolver || !codol_spinup_resolver(def, &up, &down) || up <= 0 || down <= 0) {
        /* No published durations: the charge cannot advance, so the weapon
         * cannot fire. Reported, never silently turned into full auto. */
        state->spinup_charge = 0.0f;
        return;
    }
    rate = (pm->cmd.buttons & KEY_MASK_FIRE) ? 1.0f / (float)up : -1.0f / (float)down;
    charge = state->spinup_charge + (float)msec * rate;
    if(charge < 0.0f) charge = 0.0f;
    if(charge > 1.0f) charge = 1.0f;
    state->spinup_charge = charge;
}

/* C1 PM_Weapon runs 0x4183e0 at 0x41dbf1, before the hand gates at 0x41dd3c,
 * and only once the pm_type (< 8), PMF 0x400 and turret (eFlags 0xc00) exits
 * at 0x41db8e..0x41dbbe have passed. The retained PM_Weapon calls this at the
 * matching point (after PM_Weapon_10's same three exits), so the fire gate
 * below sees this frame's charge, as C1's does. */
void CODOL_WeaponStateSpinUpFrame(struct pmove_t *pm, struct pml_t *pml)
{
    playerState_t *ps;
    codol_weapon_state_t *state;
    int msec;
    if(!pm || !pml || !(ps = pm->ps) || !(state = state_of(ps))) return;
    if(!state->initialized) CODOL_ResetClientWeaponState((unsigned)ps->clientNum);
    msec = pml->msec;
    if(msec < 0) msec = 0;
    update_spinup_charge(state, ps, pm, msec);
}

/* C1's hand fire gate 0x41b240, for fire type 6 (0x41b2e0..0x41b301): the
 * trigger only opens the hand once the charge has reached 1.0. Returns 1 when
 * hand 0's trigger must be withheld. A delayed shot already owed is not
 * affected; C1 0x41b2c1 passes that one through ECX regardless of the charge. */
int CODOL_WeaponStateSpinUpWithholds(const playerState_t *ps)
{
    const struct WeaponDef *def;
    const codol_weapon_state_t *state;
    if(!ps || !(def = weapon_def(ps->weapon)) || def->fireType != 6 ||
       !(state = state_of(ps))) return 0;
    return !(state->spinup_charge >= 1.0f);
}

/* Retained melee 12..14 (PM_Weapon_2330/2340 and the charge start) and sprint
 * 22..24 (PM_Weapon entry/loop/exit). Both describe the whole player here. */
static int player_wide_phase(int state)
{
    return (state >= 12 && state <= 14) || (state >= 22 && state <= 24);
}
/* Retained melee alone: MELEE_INIT, MELEE_FIRE and MELEE_END (C1 13..15). */
static int melee_phase(int state)
{
    return state >= 12 && state <= 14;
}

static int owns_weapon(const playerState_t *ps, unsigned weapon)
{
    return weapon < CODOL_WEAPON_STATE_WEAPONS && CODOL_WeaponBitsOwned(ps, weapon);
}
/* Has the ownership bitset moved since the clip records were last keyed? */
static int owned_changed(const codol_weapon_state_t *state, const playerState_t *ps)
{
    unsigned i;
    for(i = 0; i < CODOL_WEAPON_BIT_WORDS; ++i)
        if(state->owned[i] != CODOL_WeaponBitsOwnedWord(ps, i)) return 1;
    return 0;
}
static int clip_of(const struct WeaponDef *def)
{
    if(!def || def->iClipIndex < 0 || def->iClipIndex >= 128) return -1;
    return def->iClipIndex;
}
static int reserve_of(const struct WeaponDef *def)
{
    if(!def || def->iAmmoIndex < 0 || def->iAmmoIndex >= 128) return -1;
    return def->iAmmoIndex;
}
static codol_weapon_state_t *state_of(const playerState_t *ps)
{
    if(!ps || ps->clientNum < 0 || ps->clientNum >= MAX_CLIENTS) return NULL;
    return codol_weapon_states + ps->clientNum;
}
static unsigned second_rechamber(const codol_weapon_state_t *state,unsigned weapon)
{
    return weapon<CODOL_WEAPON_STATE_WEAPONS &&
        !!(state->second_rechamber[weapon>>5]&(1u<<(weapon&31)));
}
static void set_second_rechamber(codol_weapon_state_t *state,unsigned value)
{
    codol_weapon_hand_t *hand=state->hand+1;
    hand->rechamber=value?1u:0u;
    if(hand->weapon>=CODOL_WEAPON_STATE_WEAPONS) return;
    if(value) state->second_rechamber[hand->weapon>>5]|=1u<<(hand->weapon&31);
    else state->second_rechamber[hand->weapon>>5]&=~(1u<<(hand->weapon&31));
}
static void clear_records(codol_weapon_state_t *state)
{
    unsigned i;
    for(i = 0; i < CODOL_WEAPON_CLIP_SLOTS; ++i) {
        state->clips[i].clip_index = -1;
        state->clips[i].ammo[0] = state->clips[i].ammo[1] = 0;
    }
}
static codol_weapon_clip_t *record_for(codol_weapon_state_t *state, int clip_index)
{
    unsigned i;
    if(clip_index < 0) return NULL;
    for(i = 0; i < CODOL_WEAPON_CLIP_SLOTS; ++i)
        if(state->clips[i].clip_index == clip_index) return state->clips + i;
    return NULL;
}

void CODOL_ResetClientWeaponState(unsigned client)
{
    codol_weapon_state_t *state;
    if(client >= MAX_CLIENTS) return;
    state = codol_weapon_states + client;
    memset(state, 0, sizeof(*state));
    clear_records(state);
    state->initialized = 1;
    edge_known[client] = 0;
    /* Reset only the live extension; captured snapshot/history hands belong
     * to their original frame and must survive a later respawn. The offhand
     * selection is the same kind of live state and the same kind of history:
     * a spawn clears what this client has selected, and every captured or
     * archived copy keeps the selection it was taken with. */
    CODOL_PlayerStateExtClearClientHand(client);
    CODOL_PlayerStateExtClearClientOffhand(client);
    /* C1 keeps the variable-zoom level in the playerState the spawn zeroes. */
    CODOL_VariableZoomResetClient(client);
}
void CODOL_WeaponStateRecordShot(playerState_t *ps, unsigned hand, unsigned last_shot)
{
    codol_weapon_state_t *state = state_of(ps);
    const struct WeaponDef *def;
    unsigned slot;
    if(!state || hand >= CODOL_WEAPON_HANDS) return;
    def = weapon_def(ps->weapon);
    /* C1 0x41b8d2 refuses the last-shot variant for a double-barrel weapon,
     * whatever the magazine did. */
    if(last_shot && def && def->fireType == 5) last_shot = 0;
    /* C1 0x41bad0, in the same shot path, arms the next barrel from the second
     * trigger of the command being executed; a dual-wielded weapon skips it. */
    /* C1 0x41bad0 arms the next barrel from the second trigger of the command
     * being EXECUTED, inside the shot itself. Read that command here rather
     * than state->command_buttons: the frame capture is taken by
     * CODOL_WeaponStateUpdate at PM_Weapon's exit, so mid-PM_Weapon it still
     * holds the PREVIOUS command and the barrel was armed one frame late --
     * exactly wrong on the rising edge that starts a shot. A shot taken with
     * no bound command -- a bot, or a command the acceptance gate rejected --
     * leaves the barrel where it was instead of reading a stale word. */
    if(def && def->fireType == 5 && !state->dual_wield) {
        codol_weapon_input_t shot_input;
        if(executed_input(ps, &shot_input) &&
           (shot_input.kind == CODOL_INPUT_NETWORK || shot_input.raw_valid))
            state->second_barrel =
                (shot_input.raw_buttons & CODOL_BUTTON_SECOND_TRIGGER) ? 1u : 0u;
    }
    /* The slot this event is about to occupy: BG_AddPredictableEventToPlayerstate
     * stores at events[eventSequence & 3] and then advances the sequence
     * (_bg_misc.asm:2852..2861). */
    slot = (unsigned)ps->eventSequence & 3u;
    state->ring_hand[slot] = (unsigned char)hand;
    state->ring_lastshot[slot] = last_shot ? 1 : 0;
    state->ring_known[slot] = 1;
    if(state->shot_count >= CODOL_SHOT_RECORDS) {
        /* The retained queue only keeps four events; drop the oldest with it. */
        state->shot_head = (state->shot_head + 1) % CODOL_SHOT_RECORDS;
        state->shot_count -= 1;
    }
    state->shot_hands[(state->shot_head + state->shot_count) % CODOL_SHOT_RECORDS] =
        (unsigned char)hand;
    state->shot_count += 1;
}

int CODOL_WeaponStateRecoilRestrictTime(const playerState_t *ps)
{
    codol_weapon_state_t *state;
    unsigned hand;
    if(!ps) return 0;
    if(!(state = state_of(ps))) return ps->weaponRestrictKickTime;
    if(!state->shot_count) return ps->weaponRestrictKickTime;
    hand = state->shot_hands[state->shot_head];
    state->shot_head = (state->shot_head + 1) % CODOL_SHOT_RECORDS;
    state->shot_count -= 1;
    if(hand >= CODOL_WEAPON_HANDS || !hand) return ps->weaponRestrictKickTime;
    return state->hand[hand].restrict_time;
}

/* What 0x41ada0..0x41aed5 actually decides is whether to PIN this hand's
 * weaponTime to 1 so its fire gate cannot reopen -- not whether to refuse a
 * shot. Reading it as a refusal was my error, and the gate at PM_Weapon_1230
 * that acted on it is withdrawn along with it.
 *
 * Two local flags feed the decision and it takes either of them:
 *
 *   [ebp-8]  = quota spent and no fresh trigger pull. 0x41adc9 reads this
 *              hand's fresh-pull bit (ps+0x27c), and 0x41addf asks the quota
 *              helper 0x41a9d0, whose jump table at 0x41aa4c is indexed by
 *              fireType-1 and answers "spent" from this hand's own three-bit
 *              counter at ps+0x280 + hand*0x1c.
 *   [ebp-0xc] = the weapon pins regardless: def+0x340 is grenade and the
 *              serialized byte +0xbe4 is set (0x41adf9..0x41ae15). In the
 *              shipped zones that is briefcase_bomb_mp and
 *              briefcase_bomb_defuse_mp, the two plant weapons -- no gun and
 *              no dual-wield weapon carries it.
 *
 * 0x41ae8f..0x41ae99 leaves the block only when BOTH are zero, so the second
 * flag is a bypass of the first, which is what the double-barrel arms at
 * 0x41ae5a..0x41ae6c modify: a trigger that does not match the armed barrel
 * clears the quota flag only, and the weapon flag still pins if set.
 *
 * The armed barrel lives in the CoDOL hand bundle rather than the retained
 * ps->weapFlags bit 0x100, which this engine already uses as its own trigger
 * latch (PM_Weapon_1830 reads weapFlags >> 8 & 1, PM_Weapon_1310 clears it). */
static int hand_quota_done(const struct WeaponDef *def, unsigned count);
static int hand_weapon_always_pins(const struct WeaponDef *def)
{
    int value = 0;
    return def->weapType == WEAPTYPE_GRENADE && codol_hold_resolver &&
           codol_hold_resolver(def, &value) && value != 0;
}
static int hand_should_pin(const codol_weapon_hand_t *hand, const struct WeaponDef *def,
                           int dual_wield, int second_barrel, unsigned raw_buttons,
                           int raw_valid)
{
    int quota = !hand->fresh_pull && hand_quota_done(def, hand->shot_count);
    if(quota && def->fireType == 5 && !dual_wield && raw_valid) {
        unsigned primary = (raw_buttons & CODOL_BUTTON_PRIMARY_TRIGGER) != 0;
        unsigned second = (raw_buttons & CODOL_BUTTON_SECOND_TRIGGER) != 0;
        /* 0x41ae5a..0x41ae6c: the armed barrel against the trigger asking. */
        if(second_barrel ? primary : second) quota = 0;
    }
    return quota || hand_weapon_always_pins(def);
}
int CODOL_WeaponStateSecondBarrelArmed(const playerState_t *ps)
{
    return ps ? (int)CODOL_PlayerStateHandRead(ps)->second_barrel : 0;
}

int CODOL_WeaponStateShotRecord(const playerState_t *ps, unsigned slot,
                                unsigned *hand, unsigned *last_shot)
{
    const codol_ps_hand_t *carried;
    if(!ps || !hand || !last_shot || slot >= 4) return 0;
    carried = CODOL_PlayerStateHandRead(ps);
    if(!(carried->shot_known & (1u << slot))) return 0;
    *hand = (carried->shot_hand >> slot) & 1u;
    *last_shot = (carried->shot_last >> slot) & 1u;
    return 1;
}

int CODOL_WeaponStateSpinUpCharge(const playerState_t *ps, float *charge)
{
    if(!ps || !charge) return 0;
    *charge = (float)CODOL_PlayerStateHandRead(ps)->charge / 1000.0f;
    return 1;
}

void CODOL_WeaponStateReloadRequest(playerState_t *ps)
{
    codol_weapon_state_t *state = state_of(ps);
    if(!state) return;
    if(!state->initialized) CODOL_ResetClientWeaponState((unsigned)ps->clientNum);
    state->hand[1].reload_request = 1;
}

void CODOL_ResetWeaponStates(void)
{
    unsigned client;
    for(client = 0; client < MAX_CLIENTS; ++client) CODOL_ResetClientWeaponState(client);
    /* A new zone re-registers definitions; drop the resolved dual-wield cache
     * rather than trusting pointers from the archive generation being left. */
    memset(codol_dual_wield_known, 0, sizeof(codol_dual_wield_known));
    /* The timing warnings are keyed by weapon index and a new zone renumbers
     * weapons, so a stale flag would silence a genuinely new gap. */
    CODOL_ResetWeaponTimingReports();
}
const codol_weapon_state_t *CODOL_ClientWeaponState(unsigned client)
{
    return client < MAX_CLIENTS ? codol_weapon_states + client : NULL;
}

/* ------------------------------------------------------------------ */
/* Inventory-keyed clip records                                        */
/* ------------------------------------------------------------------ */

/* Rebuild the fifteen clip records from the current inventory, in ascending
 * native weapon order so the slots agree with CODOL_BuildEngineAmmoBindings.
 * Existing magazines are carried over by key; a clip that has just entered the
 * inventory starts with both hands holding the engine's single magazine, which
 * is how a dual-wield weapon arrives from a spawn loadout or a pickup. Only
 * runs when ownership actually changed, so ordinary frames stay cheap. */
static void rekey_records(codol_weapon_state_t *state, const playerState_t *ps)
{
    codol_weapon_clip_t records[CODOL_WEAPON_CLIP_SLOTS];
    unsigned weapon, count = 0, i, j;
    for(i = 0; i < CODOL_WEAPON_CLIP_SLOTS; ++i) {
        records[i].clip_index = -1;
        records[i].ammo[0] = records[i].ammo[1] = 0;
    }
    for(weapon = 1; weapon < CODOL_WEAPON_STATE_WEAPONS && count < CODOL_WEAPON_CLIP_SLOTS; ++weapon) {
        const struct WeaponDef *def;
        int clip;
        if(!owns_weapon(ps, weapon) || !(def = weapon_def(weapon))) continue;
        if((clip = clip_of(def)) < 0) continue;
        for(i = 0; i < count; ++i) if(records[i].clip_index == clip) break;
        if(i < count) continue;
        records[count].clip_index = clip;
        records[count].ammo[0] = ps->ammoclip[clip];
        records[count].ammo[1] = CODOL_WeaponIsDualWield(weapon) ? ps->ammoclip[clip] : 0;
        for(j = 0; j < CODOL_WEAPON_CLIP_SLOTS; ++j) {
            if(state->clips[j].clip_index != clip) continue;
            records[count].ammo[1] = state->clips[j].ammo[1];
            break;
        }
        ++count;
    }
    memcpy(state->clips, records, sizeof(state->clips));
    for(i=0;i<CODOL_WEAPON_BIT_WORDS;++i) {
        state->owned[i]=CODOL_WeaponBitsOwnedWord(ps,i);
        state->second_rechamber[i]&=state->owned[i];
    }
}

/* ------------------------------------------------------------------ */
/* Weapon selection and the cached primary                             */
/* ------------------------------------------------------------------ */

/* Resolve the primary owning an alternate-mode weapon from the player's own
 * inventory. IW4 and C1 never do this: their PM_BeginWeaponChange is handed the
 * primary by the caller and refuses the switch without one (IW4 0x576468 and C1
 * 0x419cfb both error and clear the weapon). This search runs only at the
 * transition, when a directly scripted switch supplied no context, and its
 * result is then cached, so a later inventory change cannot alter the answer.
 * WeaponDef.altWeaponIndex is a forward link only; alternate definitions
 * registered for composed CoDOL weapons carry no back link (alpha0022
 * alt_weapons.py: partner defs ship with both alternate name fields empty). */
static unsigned owned_primary_for_alternate(const playerState_t *ps, unsigned alternate)
{
    unsigned weapon;
    for(weapon = 1; weapon < CODOL_WEAPON_STATE_WEAPONS; ++weapon) {
        const struct WeaponDef *def;
        if(!owns_weapon(ps, weapon) || !(def = weapon_def(weapon))) continue;
        if(def->inventoryType == WEAPINVENTORY_ALTMODE) continue;
        if(def->altWeaponIndex == alternate) return weapon;
    }
    return 0;
}

static void start_second_raise(codol_weapon_state_t *state, const playerState_t *ps,
                               const struct WeaponDef *def)
{
    codol_weapon_hand_t *hand = state->hand + 1;
    const codol_weapon_clip_t *record;
    unsigned animation;
    int time;
    int state_id = CODOL_WEAPONSTATE_RAISING;
    (void)ps;
    if(!def) return;
    record = record_for(state, clip_of(def));
    /* PM_Weapon's raise selection (PM_Weapon_2180/1150/1140/2090/1130): first,
     * alternate, quick, empty or ordinary raise, each with its own duration and
     * animation, and state 2 rather than 1 for the alternate one
     * (PM_Weapon_2270). This hand makes the choice from its own magazine and
     * from the put-away it just finished. */
    if(((unsigned)hand->animation & 0x1fu) == ANIM_DROP_ALT) {
        animation = ANIM_RAISE_ALT; time = def->iAltRaiseTime;
        state_id = CODOL_WEAPONSTATE_RAISING_ALT;
    } else if(!hand->state && !hand->time) {
        animation = ANIM_FIRST_RAISE; time = def->iFirstRaiseTime;
    } else if(hand->state == CODOL_WEAPONSTATE_DROPPING_QUICK) {
        animation = ANIM_RAISE_QUICK; time = def->quickRaiseTime;
    } else if(record && !record->ammo[1]) {
        animation = ANIM_RAISE_EMPTY; time = def->iEmptyRaiseTime;
    } else {
        animation = ANIM_RAISE; time = def->iRaiseTime;
    }
    if(time <= 0) time = def->iRaiseTime > 0 ? def->iRaiseTime : 1;
    hand->state = state_id;
    hand->time = time;
    hand->delay = 0;
    hand->shot_pending = 0;
    hand->rechamber = second_rechamber(state,hand->weapon);
    hand->shot_count = 0;
    hand->animation = (int)(animation | ((~(unsigned)hand->animation) & ANIM_RESTART_BIT));
}

static void select_weapon(codol_weapon_state_t *state, playerState_t *ps,
                          unsigned previous, unsigned next)
{
    struct WeaponDef *def = weapon_def(next), *owner;
    unsigned primary = 0;
    int riot_shield = 0;
    state->hand[0].weapon = next;
    CODOL_WeaponReloadSelected(ps,next);
    /* C1 PM_BeginWeaponChange 0x41979a/0x4197a6: weapFlags bit 0x1000 follows
     * whether the incoming weapon's def+0x340 is 3 (riot shield). It reaches
     * the wire as C1 bit 0x1000 and clientState 0x01c riotShieldNext. */
    if(def && CODOL_GetNativeWeaponRiotShield(def,&riot_shield) && riot_shield)
        ps->weapFlags |= CODOL_WEAP_RIOTSHIELD_NEXT;
    else
        ps->weapFlags &= ~CODOL_WEAP_RIOTSHIELD_NEXT;
    if(!def) {
        /* Weapon 0 is the empty hand; both hands and the cache go with it. */
        state->primary_weapon = 0;
        state->dual_wield = 0;
        memset(state->hand + 1, 0, sizeof(state->hand[1]));
        return;
    }
    if(def->inventoryType != WEAPINVENTORY_ALTMODE) {
        /* alpha0022 weapon_spawn.py asserts ps+0x33c == ps+0x340 for an
         * ordinary weapon; C1's own pmove leaves the partner word at zero
         * because the reader only consults it for inventory type 3. Publish
         * the current weapon so both conventions read back identically. */
        primary = next;
    } else if((owner = weapon_def(previous)) != NULL && owner->altWeaponIndex == next) {
        primary = previous; /* The weapon we are switching away from owns it. */
    } else if((owner = weapon_def(state->primary_weapon)) != NULL &&
              owner->altWeaponIndex == next) {
        primary = state->primary_weapon; /* Already in the alternate pair. */
    } else {
        primary = owned_primary_for_alternate(ps, next);
        if(!primary)
            Com_PrintWarning(CON_CHANNEL_SERVER,
                "weapon state: alternate weapon '%s' selected with no primary in inventory\n",
                def->szInternalName ? def->szInternalName : "");
    }
    state->primary_weapon = primary;
    state->second_barrel = 0;
    state->dual_wield = CODOL_WeaponIsDualWield(next) ? 1u : 0u;
    /* C1 sets ps+0x35c from the weapon being selected and PM_StartWeaponAnim
     * clears the second hand outright when it is not dual wield (0x4180ec). */
    if(!state->dual_wield) { memset(state->hand + 1, 0, sizeof(state->hand[1])); return; }
    if(state->hand[1].state == CODOL_WEAPONSTATE_DROPPING ||
       state->hand[1].state == CODOL_WEAPONSTATE_DROPPING_QUICK)
        return; /* Still putting the previous weapon away on its own clock. */
    state->hand[1].weapon = next;
    start_second_raise(state, ps, def);
}

void CODOL_WeaponStateSelectWeapon(playerState_t *ps, unsigned previous, unsigned next)
{
    codol_weapon_state_t *state = state_of(ps);
    if(!state) return;
    if(!state->initialized) CODOL_ResetClientWeaponState((unsigned)ps->clientNum);
    select_weapon(state, ps, previous, next);
}

/* A scripted assignment replaces the weapon outside pmove. Resolve the pair
 * against the weapon this state still holds, which is the one being left, and
 * do it now rather than letting the next pmove frame infer it from a value two
 * assignments old. */
void CODOL_WeaponStateScriptedWeapon(playerState_t *ps, unsigned next)
{
    codol_weapon_state_t *state = state_of(ps);
    if(!state) return;
    if(!state->initialized) CODOL_ResetClientWeaponState((unsigned)ps->clientNum);
    if(next == state->hand[0].weapon) return;
    select_weapon(state, ps, state->hand[0].weapon, next);
}

void CODOL_WeaponStateTakeWeapon(playerState_t *ps, unsigned weapon)
{
    codol_weapon_state_t *state = state_of(ps);
    CODOL_WeaponReloadRemoved(ps,weapon);
    if(!state || !weapon) return;
    if(!state->initialized) { CODOL_ResetClientWeaponState((unsigned)ps->clientNum); return; }
    if(weapon<CODOL_WEAPON_STATE_WEAPONS) {
        codol_ps_hand_t *carried=CODOL_PlayerStateHandMutable(ps);
        state->second_rechamber[weapon>>5]&=~(1u<<(weapon&31));
        if(carried) carried->second_rechamber[weapon>>5]&=~(1u<<(weapon&31));
    }
    /* IW4 and C1 both refuse an alternate mode with no primary; once the
     * primary is gone the cache cannot answer for it either. */
    if(state->primary_weapon == weapon && state->hand[0].weapon != weapon)
        state->primary_weapon = 0;
    if(state->hand[1].weapon == weapon) {
        memset(state->hand + 1, 0, sizeof(state->hand[1]));
        state->dual_wield = 0;
    }
    /* Clear actual assignments, including a primary slot holding a class
     * normally used by the tactical/equipment loadout slot. The shared take
     * epilogue reconciles the remaining inventory after ownership changes. */
    CODOL_WeaponStateOffhandReleased(ps, weapon);
}

/* C1 starts the change once for both hands (0x419d77/0x419d7d reset both hand
 * states together and PM_BeginWeaponChange is not per-hand), so the second hand
 * only runs the drop timer here; the retained code owns the change's events. */
void CODOL_WeaponStateBeginChange(playerState_t *ps, int alternate, int quick)
{
    codol_weapon_state_t *state = state_of(ps);
    codol_weapon_hand_t *hand;
    const struct WeaponDef *def;
    const codol_weapon_clip_t *record;
    unsigned animation;
    int time;
    if(!state) return;
    if(!state->initialized) CODOL_ResetClientWeaponState((unsigned)ps->clientNum);
    if(!state->dual_wield || !state->hand[1].weapon) return;
    hand = state->hand + 1;
    if(!(def = weapon_def(hand->weapon))) return;
    record = record_for(state, clip_of(def));
    /* PM_BeginWeaponChange's own selection: an alternate-mode partner uses the
     * alternate drop; otherwise C1 picks the animation empty-first
     * (0x419930..0x41994f) but the time quick-first (0x419a41 before
     * 0x419a54), and skips the animation altogether while sprinting
     * (0x41991c, PMF 0x4000). */
    if(alternate) {
        animation = ANIM_DROP_ALT; time = def->iAltDropTime;
    } else {
        int empty = record && !record->ammo[1];
        animation = empty ? ANIM_DROP_EMPTY : quick ? ANIM_DROP_QUICK : ANIM_DROP;
        time = quick ? def->quickDropTime : empty ? def->iEmptyDropTime : def->iDropTime;
    }
    if(time <= 0) time = def->iDropTime > 0 ? def->iDropTime : 1;
    hand->state = quick ? CODOL_WEAPONSTATE_DROPPING_QUICK : CODOL_WEAPONSTATE_DROPPING;
    hand->time = time;
    hand->delay = 0;
    hand->shot_pending = 0;
    if(alternate || !((unsigned)ps->pm_flags & 0x4000u))
        hand->animation = (int)(animation | ((~(unsigned)hand->animation) & ANIM_RESTART_BIT));
}

/* A drop cancelled back to the weapon already held (C1 0x41b171..0x41b1b8):
 * every hand is readied by 0x41c1c0 and then given animation 1 by 0x418080,
 * two restarts that leave the toggle where it was. The retained machine does
 * the same for its own hand at PM_Weapon_1720/2000 and asks for this one. */
void CODOL_WeaponStateCancelChange(playerState_t *ps)
{
    codol_weapon_state_t *state = state_of(ps);
    codol_weapon_hand_t *hand;
    if(!state || !state->initialized || !state->dual_wield) return;
    hand = state->hand + 1;
    if(!hand->weapon) return;
    hand->state = CODOL_WEAPONSTATE_READY;
    hand->time = 0;
    hand->delay = 0;
    hand->shot_pending = 0;
    if(ps->pm_type < 8)
        hand->animation = (int)(1u | ((unsigned)hand->animation & ANIM_RESTART_BIT));
}

/* PM_ResetWeaponState clears the engine machine and restarts the viewmodel
 * animation. C1 does the same for both hands at 0x419d77/0x419d7d and then lets
 * PM_StartWeaponAnim clear the second hand outright when the weapon is not dual
 * wield (0x4180ec). Loadout, cache and magazines are untouched. */
void CODOL_WeaponStateResetHands(playerState_t *ps)
{
    codol_weapon_state_t *state = state_of(ps);
    unsigned hand;
    if(!state) return;
    for(hand = 0; hand < CODOL_WEAPON_HANDS; ++hand) {
        state->hand[hand].state = CODOL_WEAPONSTATE_READY;
        state->hand[hand].time = 0;
        state->hand[hand].delay = 0;
        state->hand[hand].shot_pending = 0;
        state->hand[hand].shot_count = 0;
        state->hand[hand].trigger_held = 0;
    }
    if(!state->dual_wield) memset(state->hand + 1, 0, sizeof(state->hand[1]));
    /* C1's own weapon-state reset at 0x41a0c0 clears exactly one of the three
     * per-button offhand restrictions -- bit 0x10000, the equipment button --
     * in the same instruction stream that zeroes both hand weaponstates
     * (ps+0x278 and ps+0x294). The other two are not touched there and are not
     * touched here. */
    ps->weapFlags &= ~(int)CODOL_WEAP_OFFHAND_EQUIPMENT_DISABLED;
}

/* ------------------------------------------------------------------ */
/* The second hand's weapon machine                                    */
/* ------------------------------------------------------------------ */

static void set_animation(codol_weapon_hand_t *hand, unsigned animation)
{
    hand->animation = (int)(animation | ((~(unsigned)hand->animation) & ANIM_RESTART_BIT));
}

/* PM_ReloadClip for this hand: top the magazine off out of the shared reserve,
 * bounded by iReloadAmmoAdd in the segmented states, and announce the transfer
 * exactly as the retained code does with EV_RELOAD_ADDAMMO. */
static void hand_reload_clip(codol_weapon_clip_t *record, playerState_t *ps,
                             const struct WeaponDef *def, const codol_weapon_hand_t *hand)
{
    int reserve = reserve_of(def), capacity = def->iClipSize, add, cap;
    int start=hand->state==CODOL_WEAPONSTATE_RELOAD_SEGMENT ||
        hand->state==CODOL_WEAPONSTATE_RELOAD_INTERRUPT;
    if(reserve < 0 || capacity <= 0) return;
    if(start && !def->iReloadStartAdd)return;
    add = capacity - record->ammo[1];
    if(add > ps->ammo[reserve]) add = ps->ammo[reserve];
    cap=start ? def->iReloadStartAdd : def->iReloadAmmoAdd;
    if(cap > 0 && cap < capacity && add > cap) add = cap;
    if(add > 0) {
        record->ammo[1] += add;
        ps->ammo[reserve] -= add;
        add_player_event(ps, EV_RELOAD_ADDAMMO);
    }
    CODOL_WeaponReloadClipFinished(ps);
}

/* C1 419150: add time is selected from this hand's clip and current reload
 * phase. Segmented start uses min(nonzero start-add-time,start-time). */
static int hand_reload_add_time(const playerState_t *ps,const struct WeaponDef *def,
                               const codol_weapon_clip_t *record,const codol_weapon_hand_t *hand)
{
    int time,add,fast;
    if(hand->state==CODOL_WEAPONSTATE_RELOAD_SEGMENT ||
       hand->state==CODOL_WEAPONSTATE_RELOAD_INTERRUPT) {
        add=def->iReloadStartAddTime;
        return add && add>def->iReloadStartTime ? def->iReloadStartTime : add;
    }
    if(CODOL_WeaponReloadInfo(ps,def,!record->ammo[1] && !def->weapType,&time,&add,&fast))
        return add;
    time=record->ammo[1] || def->weapType ? def->iReloadTime : def->iReloadEmptyTime;
    add=def->iReloadAddTime;
    return !add || add>=time ? time : add;
}
static void hand_set_reload_delay(const playerState_t *ps,const struct WeaponDef *def,
                                  const codol_weapon_clip_t *record,codol_weapon_hand_t *hand)
{
    int add=hand_reload_add_time(ps,def,record,hand);
    if(def->bBoltAction && hand->rechamber) {
        if(!add)add=hand->time;
        if(def->iRechamberBoltTime<add)add=def->iRechamberBoltTime;
        if(!add)add=1;
    }
    if(add)hand->delay=add;
}

/* C1 41a1b0: brass is a conditional first action. If add-time is later,
 * schedule its remainder instead of transferring ammunition at bolt-time. */
static void hand_reload_delayed(codol_weapon_state_t *state,playerState_t *ps,
                                const struct WeaponDef *def,codol_weapon_clip_t *record)
{
    codol_weapon_hand_t *hand=state->hand+1;
    int add,bolt;
    if(def->bBoltAction && hand->rechamber) {
        set_second_rechamber(state,0);
        add_player_event(ps,(BGEvent)CODOL_EV_EJECT_BRASS_SECONDARY);
        if((hand->state==CODOL_WEAPONSTATE_RELOAD_SEGMENT ||
            hand->state==CODOL_WEAPONSTATE_RELOAD_INTERRUPT) && !def->iReloadStartAddTime)
            return;
        if(hand->time) {
            add=hand_reload_add_time(ps,def,record,hand);
            bolt=def->iRechamberBoltTime<add ? def->iRechamberBoltTime : 1;
            add-=bolt;
            if(add>=1) { hand->delay=add; return; }
        }
    }
    hand_reload_clip(record,ps,def,hand);
}

/* PM_SetReloadingState for this hand: one reload step, which for a segmented
 * weapon is one increment of the loop that PM_Weapon_2310 keeps re-entering. */
static void hand_begin_reload(codol_weapon_state_t *state, playerState_t *ps,
                              const struct WeaponDef *def, codol_weapon_clip_t *record)
{
    codol_weapon_hand_t *hand = state->hand + 1;
    int previous = hand->state, time, add, fast=0, empty;
    empty=!record->ammo[1] && !def->weapType;
    if(CODOL_WeaponReloadInfo(ps,def,empty,&time,&add,&fast)) {
        set_animation(hand,empty ? (fast ? CODOL_HAND_ANIM_RELOAD_EMPTY_FAST : ANIM_RELOAD_EMPTY) :
            (fast ? CODOL_HAND_ANIM_RELOAD_FAST : ANIM_RELOAD));
        add_player_event(ps,empty ? EV_RELOAD_FROM_EMPTY : EV_RELOAD);
    } else {
        if(record->ammo[1] || def->weapType) {
            set_animation(hand, ANIM_RELOAD);
            time = def->iReloadTime;
            add_player_event(ps, EV_RELOAD);
        } else {
            set_animation(hand, ANIM_RELOAD_EMPTY);
            time = def->iReloadEmptyTime;
            add_player_event(ps, EV_RELOAD_FROM_EMPTY);
        }
        add=def->iReloadAddTime;
        if(!add || add>=time)add=time;
    }
    hand->state = previous == 10 ? CODOL_WEAPONSTATE_RELOADING_AGAIN : CODOL_WEAPONSTATE_RELOADING;
    hand->time = time;
    hand_set_reload_delay(ps,def,record,hand);
    hand->shot_pending = 0;
    hand->shot_count = 0;
}

/* PM_Weapon_890 / PM_Weapon_1020: leaving the reload machine. A weapon with no
 * end animation drops straight to idle; otherwise state 11 plays it out and
 * announces EV_RELOAD_END. The rechamber this hand owed is cleared either way,
 * matching the retained code clearing its weaponrechamber bit first. */
static void hand_reload_end(codol_weapon_state_t *state, playerState_t *ps,
                            const struct WeaponDef *def)
{
    codol_weapon_hand_t *hand = state->hand + 1;
    set_second_rechamber(state,0);
    hand->delay = 0;
    hand->shot_pending = 0;
    if(def->iReloadEndTime <= 0) {
        hand->state = CODOL_WEAPONSTATE_READY;
        hand->time = 0;
        set_animation(hand, ANIM_IDLE);
        return;
    }
    hand->state = CODOL_WEAPONSTATE_RELOAD_END;
    hand->time = def->iReloadEndTime;
    set_animation(hand, ANIM_RELOAD_END);
    add_player_event(ps, EV_RELOAD_END);
}

/* PM_Weapon_2190 and the identical tail of PM_Weapon_2310: whether a segmented
 * reload takes another increment. Reserve exhausted or a full magazine ends it;
 * bNoPartialReload additionally refuses to start an increment that would not
 * fit, and otherwise only tops up from empty. */
static int hand_reload_continues(const playerState_t *ps, const struct WeaponDef *def,
                                 const codol_weapon_clip_t *record)
{
    int reserve = reserve_of(def), clip = record->ammo[1], capacity = def->iClipSize;
    if(reserve < 0 || !ps->ammo[reserve]) return 0;
    if(capacity <= 0 || clip >= capacity) return 0;
    if(!def->bNoPartialReload) return 1;
    if(def->iReloadAmmoAdd && capacity > def->iReloadAmmoAdd)
        return def->iReloadAmmoAdd <= capacity - clip;
    return clip == 0;
}

/* PM_BeginWeaponReload: a segmented weapon with a start time opens the sequence
 * in state 9 with its own animation and the start/notify events; everything
 * else goes straight to a single reload step. The shot counter is cleared and
 * the ADS reset is announced exactly as the retained code does. */
static void hand_begin_reload_sequence(codol_weapon_state_t *state, playerState_t *ps,
                                       const struct WeaponDef *def, codol_weapon_clip_t *record)
{
    codol_weapon_hand_t *hand = state->hand + 1;
    hand->shot_count = 0;
    add_player_event(ps, EV_RESET_ADS);
    add_player_event(ps, EV_RELOAD_START_NOTIFY);
    if(!def->bSegmentedReload || def->iReloadStartTime <= 0) {
        hand_begin_reload(state, ps, def, record);
        return;
    }
    set_animation(hand, ANIM_RELOAD_START);
    hand->time = def->iReloadStartTime;
    hand->delay = 0;
    hand->shot_pending = 0;
    hand->state = CODOL_WEAPONSTATE_RELOAD_SEGMENT;
    hand_set_reload_delay(ps,def,record,hand);
    add_player_event(ps, EV_RELOAD_START);
}

/* PM_Weapon_CheckForReload (src/asmsource/_bg_weapons.asm:1310..1470), applied
 * to this hand instead of the engine's, statement for statement:
 *
 *   :1323 states 12..20 do nothing at all.
 *   :1326 the request is the level of the reload button, ORed at :1331 with the
 *         queued weapFlags bit 0 that the retained code consumes for its own
 *         hand and now forwards here.
 *   :1348 a segmented weapon in state 9 or 7 takes a fire *rising edge* as an
 *         interrupt: state 7 becomes 8 immediately (:1362), state 9 becomes 10
 *         only once more than MY_RELOADSTART_INTERUPT_IGNORE_FRAC of
 *         iReloadStartTime has elapsed (:1453..1466, the 0.4f constant in the
 *         file's own .data at :8590).
 *   :1337 states 1..4 do nothing; :1364 states 7..11 only raise an animation
 *         script event, never a new reload.
 *   :1390 the ammunition decision: an empty magazine with reserve left reloads
 *         by itself unless the weapon is firing (state 5) or sprinting (22..24),
 *         and a requested reload additionally has to be useful -- reserve left,
 *         magazine not full, and for bNoPartialReload either a whole
 *         iReloadAmmoAdd increment fits or the magazine is empty. */
#define CODOL_RELOADSTART_INTERRUPT_IGNORE_FRAC 0.4f
static void hand_check_for_reload(codol_weapon_state_t *state, playerState_t *ps,
                                  const struct pmove_t *pm, const struct WeaponDef *def,
                                  codol_weapon_clip_t *record)
{
    codol_weapon_hand_t *hand = state->hand + 1;
    int requested, useful = 0, clip, reserve = reserve_of(def), st = hand->state;
    if(st >= 12 && st <= 20) return;
    requested = (pm->cmd.buttons & KEY_MASK_RELOAD) != 0;
    if(hand->reload_request) { hand->reload_request = 0; requested = 1; }
    if(def->bSegmentedReload &&
       (st == CODOL_WEAPONSTATE_RELOAD_SEGMENT || st == CODOL_WEAPONSTATE_RELOADING) &&
       hand_fire_requested(ps, pm, def, (int)state->dual_wield, 1) && !hand->trigger_held) {
        if(st == CODOL_WEAPONSTATE_RELOADING) {
            hand->state = CODOL_WEAPONSTATE_RELOADING_AGAIN;
        } else if(def->iReloadStartTime > 0 &&
                  (float)(def->iReloadStartTime - hand->time) / (float)def->iReloadStartTime >
                      CODOL_RELOADSTART_INTERRUPT_IGNORE_FRAC) {
            hand->state = CODOL_WEAPONSTATE_RELOAD_INTERRUPT;
        }
        return;
    }
    if(st >= CODOL_WEAPONSTATE_RAISING && st <= CODOL_WEAPONSTATE_DROPPING_QUICK) return;
    if(st >= CODOL_WEAPONSTATE_RELOADING && st <= CODOL_WEAPONSTATE_RELOAD_END) return;
    if(!record || reserve < 0 || def->iClipSize <= 0) return;
    clip = record->ammo[1];
    if(requested && ps->ammo[reserve] && clip < def->iClipSize) {
        if(!def->bNoPartialReload) useful = 1;
        else if(def->iReloadAmmoAdd && def->iClipSize > def->iReloadAmmoAdd)
            useful = def->iReloadAmmoAdd <= def->iClipSize - clip;
        else useful = clip == 0;
    }
    if(!clip && ps->ammo[reserve] && st != CODOL_WEAPONSTATE_FIRING &&
       !(st >= 22 && st <= 24)) {
        hand_begin_reload_sequence(state, ps, def, record);
        return;
    }
    if(useful) hand_begin_reload_sequence(state, ps, def, record);
}

/* The shot itself: PM_Weapon_2210's magazine decrement, PM_Weapon_1950/1360's
 * animation selection on the post-shot count, PM_Weapon_1370/1380's last-shot
 * distinction and PM_Weapon_1270's bolt-action rechamber bit. */
static void hand_take_shot(codol_weapon_state_t *state, playerState_t *ps,
                           const struct WeaponDef *def, codol_weapon_clip_t *record)
{
    codol_weapon_hand_t *hand = state->hand + 1;
    int remaining, event;
    unsigned animation;
    /* PM_Weapon_1310 consults the CoDOL lock gate before consuming a round; a
     * nonzero result replaces the shot with the returned warning event. */
    if((event = CODOL_WeaponLockFireEvent(ps, def)) != 0) {
        add_player_event(ps, (BGEvent)event);
        return;
    }
    /* PM_Weapon_2210 skips the decrement while player_sustainAmmo is set or
     * the player is riding a turret/vehicle, and for an unlimited-ammo
     * definition (C1 0x41e3cf). */
    if(record->ammo[1] > 0 && !(ps->eFlags & PLAYER_EFLAG_TURRET_MASK) &&
       !(player_sustainAmmo && player_sustainAmmo->boolean) &&
       !CODOL_WeaponUnlimitedAmmo(def)) record->ammo[1] -= 1;
    remaining = record->ammo[1];
    if(ps->fWeaponPosFrac > ADS_ANIMATION_FRACTION)
        animation = remaining ? ANIM_FIRE_ADS : ANIM_FIRE_ADS_EMPTY;
    else
        animation = remaining ? ANIM_FIRE : ANIM_FIRE_EMPTY;
    set_animation(hand, animation);
    if(def->bBoltAction) set_second_rechamber(state,1);
    /* Record the owning hand and whether this emptied the magazine, both in the
     * queue order the recoil read consumes and in the ring slot the snapshot
     * producer indexes: C1 picks EV_SV_FIRE_WEAPON 43/45 or the last-shot
     * variants 44/46 from exactly those two facts (0x41b8db..0x41b8f3), except
     * that a double-barrel weapon never takes the last-shot variant
     * (0x41b8d2). */
    CODOL_WeaponStateRecordShot(ps, 1, !remaining);
    add_player_event(ps, remaining ? EV_FIRE_WEAPON : EV_FIRE_WEAPON_LASTSHOT);
}

static void hand_begin_fire(codol_weapon_state_t *state, playerState_t *ps,
                            const struct WeaponDef *def, codol_weapon_clip_t *record)
{
    codol_weapon_hand_t *hand = state->hand + 1;
    int already_firing = hand->state == CODOL_WEAPONSTATE_FIRING;
    hand->state = CODOL_WEAPONSTATE_FIRING;
    hand->time = def->iFireTime > 0 ? def->iFireTime : 1;
    hand->delay = def->iFireDelay > 0 ? def->iFireDelay : 0;
    /* PM_Weapon_1230's adsFireOnly branch replaces the fire delay with the
     * aim-down-sight transition still owed, so the shot waits for full ADS. */
    if(def->adsFireOnly) {
        float owed = (ADS_COMPLETE_FRACTION - ps->fWeaponPosFrac) / ads_transition_rate(def);
        hand->delay = owed > 0.0f ? (int)owed : 0;
    }
    /* PM_Weapon_1280/1300: the kick-restriction window is a whole number of
     * fire cycles plus the fire delay, counted from the ADS or hip reduced-kick
     * bullet count, and it is only armed when the hand was not already firing.
     * C1 computes the same product per hand at 0x41b56d/0x41b588 into
     * ps+0x274 + hand*0x1c, which is this hand's own field. */
    if(!already_firing) {
        int bullets = ps->fWeaponPosFrac >= ADS_COMPLETE_FRACTION ?
            def->adsGunKickReducedKickBullets : def->hipGunKickReducedKickBullets;
        hand->restrict_time = bullets * def->iFireTime + def->iFireDelay;
        if(hand->restrict_time < 0) hand->restrict_time = 0;
    }
    /* PM_Weapon_1320: the shot counter advances for every non-automatic fire
     * type and saturates at 4. C1 keeps it per hand in the three-bit field at
     * ps+0x280 + hand*0x1c (cleared at 0x41af35/0x41af59, tested by the
     * burst-continuation helper 0x41aa70 at 0x41aab5). */
    if(def->fireType != WEAPON_FIRETYPE_FULLAUTO) {
        /* C1 41b63c..41b646 consumes a fresh burst pull only when the
         * sequence starts. A pull queued during an existing burst survives
         * until the next sequence; releasing alone does not discard it. */
        if(!hand->shot_count) hand->fresh_pull = 0;
        if(hand->shot_count < 4) hand->shot_count += 1;
    }
    if(hand->delay) { hand->shot_pending = 1; return; }
    hand->shot_pending = 0;
    hand_take_shot(state, ps, def, record);
}

/* A burst weapon that has fired its whole burst returns to idle and parks.
 * BURSTFIRE2/3/4 complete at shot counts above 1, 2 and 3 respectively
 * (retained PM_Weapon_1850/2280/1860, C1 quota table 0x41aa4c). The wait is
 * CoDOL's, not the retained engine's: C1 loads the hard-coded float at
 * 0xc30cb4 -- verified to be exactly 200.0 -- into that hand's weaponTime at
 * 0x41ad89..0x41adaa, where the retained engine would consult
 * player_burstFireCooldown. The client predicts the constant, so the server
 * uses the constant; the dvar is deliberately not read here. Returns 0 while
 * the burst is still running and the hand may fire on its ordinary cycle. */
#define CODOL_BURST_FIRE_COOLDOWN_MS 200
static int hand_clip_spent(const struct WeaponDef *def, const codol_weapon_clip_t *record);
static int hand_burst_cooldown(const codol_weapon_hand_t *hand, const struct WeaponDef *def,
                               const codol_weapon_clip_t *record)
{
    unsigned burst;
    /* PM_Weapon_1530 filters to fireType 2..4 before any of this; automatic and
     * single-shot weapons never take a burst cooldown. */
    switch(def->fireType) {
    case WEAPON_FIRETYPE_BURSTFIRE2: burst = 2; break;
    case WEAPON_FIRETYPE_BURSTFIRE3: burst = 3; break;
    case WEAPON_FIRETYPE_BURSTFIRE4: burst = 4; break;
    default: return 0;
    }
    /* C1 0x41ad7d takes the wait whenever 0x41aa70 reports nothing owed,
     * which a magazine emptied short of the quota also does. */
    if(!hand->shot_count || (hand->shot_count < burst && !hand_clip_spent(def, record))) return 0;
    return CODOL_BURST_FIRE_COOLDOWN_MS;
}

/* C1's quota dispatcher 0x41a9d0 and its six-entry table at 0x41aa4c, indexed
 * by fireType-1: full auto never blocks, single shot and double barrel are done
 * at one round, bursts at two, three and four, and spin-up is never done
 * (0x41aa00). alpha0022 docs/weapon_firemodes.md 1.1 records the same table.
 * The shipped zones use only 0, 1, 3 and 5 (see the harvest in
 * obj/claude-workers/weapon-hands-dualwield.json). */
static int hand_quota_done(const struct WeaponDef *def, unsigned count)
{
    switch(def->fireType) {
    case WEAPON_FIRETYPE_FULLAUTO: return 0;
    case WEAPON_FIRETYPE_SINGLESHOT: return count >= 1;
    case WEAPON_FIRETYPE_BURSTFIRE2: return count >= 2;
    case WEAPON_FIRETYPE_BURSTFIRE3: return count >= 3;
    case WEAPON_FIRETYPE_BURSTFIRE4: return count >= 4;
    /* Written as the CoDOL fire-type numbers rather than enumerators so this
     * hand behaves correctly whether or not the shared weapFireType_t has been
     * extended yet: 5 is double barrel, whose arm 0x41a9e9 is shared with the
     * single shot, and 6 is spin-up, whose arm 0x41aa00 never reports done. */
    case 5: return count >= 1;
    case 6: return 0;
    default: return count >= 1;
    }
}
/* C1 0x418ec0, the first test 0x41aa70 makes: a bullet weapon (definition
 * +0x340, weapType) whose magazine for this hand is empty, or which has no
 * magazine record at all, owes no more rounds of its burst. */
static int hand_clip_spent(const struct WeaponDef *def, const codol_weapon_clip_t *record)
{
    return def->weapType == WEAPTYPE_BULLET && (!record || record->ammo[1] == 0);
}
/* C1 0x41aa70: this hand still owes rounds of a burst it started, which the
 * fire gate ORs with the trigger at 0x41b2cb, so a released trigger does not
 * cut a burst short. An emptied magazine ends it (0x418ec0). */
static int hand_burst_owed(const codol_weapon_hand_t *hand, const struct WeaponDef *def,
                           const codol_weapon_clip_t *record)
{
    /* C1 0x41aa70 owes nothing to full auto or spin-up (0x41aaa3..0x41aaaa). */
    return def->fireType != WEAPON_FIRETYPE_FULLAUTO && def->fireType != 6 && hand->shot_count &&
           !hand_clip_spent(def, record) && !hand_quota_done(def, hand->shot_count);
}

static void advance_second_hand(codol_weapon_state_t *state, playerState_t *ps,
                                const struct pmove_t *pm, int msec)
{
    codol_weapon_hand_t *hand = state->hand + 1;
    const struct WeaponDef *def = weapon_def(hand->weapon);
    codol_weapon_clip_t *record;
    int pressed, edge, cooldown, wants, requested;
    if(!def) return;
    record = record_for(state, clip_of(def));

    /* The dive phases are written to every hand at once (C1 0x41d1f0,
     * 0x41d350 and 0x41d2a0 each loop over the hands, 0x422980), so this hand
     * follows the engine's phase and time and restarts its own animation --
     * the dive animation of its own magazine -- at each transition. Leaving
     * the dive (0x41c1c0 through 0x41d7f6) readies every hand as well. */
    if(dive_phase(ps->weaponstate)) {
        if(hand->state != ps->weaponstate) {
            hand->state = ps->weaponstate;
            hand->delay = 0;
            hand->shot_pending = 0;
            set_animation(hand, record && record->ammo[1] == 0 ?
                CODOL_ANIM_DIVE_EMPTY : CODOL_ANIM_DIVE);
        }
        hand->time = ps->weaponTime;
        return;
    }
    if(dive_phase(hand->state)) {
        hand->state = CODOL_WEAPONSTATE_READY;
        hand->time = 0;
        hand->delay = 0;
        set_animation(hand, ANIM_IDLE);
    }

    /* C1 0x41ab10, called from PM_Weapon at 0x41dc1d before the per-hand
     * machines run: a 0->1 edge of the fire button (pm+0x08 against pm+0x30)
     * arms this hand's own fresh-pull bit, ps+0x27c bit 0. */
    pressed = hand_fire_requested(ps, pm, def, (int)state->dual_wield, 1);
    edge = pressed && !hand->trigger_held;
    hand->trigger_held = pressed ? 1u : 0u;
    /* C1 41ab23..41ab31 limits this latch to fire types 2..4. In
     * particular, a semi-auto pull must not bypass its spent-shot gate. */
    if(edge && def->fireType >= WEAPON_FIRETYPE_BURSTFIRE2 &&
       def->fireType <= WEAPON_FIRETYPE_BURSTFIRE4) hand->fresh_pull = 1;

    /* C1 PM_Weapon_Hand decrements the second per-hand timer unconditionally
     * before anything else, clamped at zero (0x41ad0d..0x41ad25). */
    if(hand->restrict_time > 0) {
        hand->restrict_time -= msec;
        if(hand->restrict_time < 0) hand->restrict_time = 0;
    }
    /* A melee takes this hand over whatever it was doing, a reload included.
     * C1's melee begin 0x41bd30 restarts the melee animation on every hand
     * (0x41bf09 -> 0x4180b0: +0x268, and +0x284 when the akimbo flag +0x35c is
     * 1), and then, on an akimbo weapon, writes melee state 13 into this hand
     * and copies the first hand's weaponTime and weaponDelay into it
     * (0x41bfe6..0x41c012: +0x294, +0x288, +0x28c). Its reload is dropped
     * unfinished: the delay that would have added the rounds is overwritten.
     * From there both hands run the same melee states on the same clocks --
     * 13 -> 14 (0x41bcd0, the hit only for hand 0), 14 -> 15 with the end time
     * and animation (0x41bc00), 15 -> ready and idle (0x41c1c0) -- so this hand
     * follows the engine's melee phase, time and delay and restarts its own
     * animation exactly when the engine restarts its own. Melee start already
     * refused a raising or dropping hand (0x41c171), so only a hand that
     * started the melee with the engine is in it. */
    if(melee_phase(ps->weaponstate) &&
       (!melee_phase(state->engine_state) || melee_phase(hand->state))) {
        if(!melee_phase(state->engine_state) || ps->weapAnim != state->engine_animation)
            set_animation(hand, (unsigned)ps->weapAnim & 0x1fu);
        hand->state = ps->weaponstate;
        hand->time = ps->weaponTime;
        hand->delay = ps->weaponDelay;
        hand->shot_pending = 0;
        return;
    }
    /* Both hands leave the melee together at 0x41c1c0: ready, clocks cleared,
     * idle restarted. This hand may then reload an empty magazine afresh. */
    if(melee_phase(hand->state)) {
        hand->state = CODOL_WEAPONSTATE_READY;
        hand->time = 0;
        hand->delay = 0;
        set_animation(hand, ANIM_IDLE);
    }
    msec=weapon_frame_msec(ps,(unsigned)hand->state,def,msec);
    /* C1 41ace0 updates both clocks before the phase handler consumes the
     * delay-expired result. The handler must see the remaining phase time. */
    if(hand->time) {
        hand->time-=msec;
        if(hand->time<0)hand->time=0;
    }
    hand->delay_expired = 0;
    if(hand->delay > 0) {
        hand->delay -= msec;
        if(hand->delay <= 0) {
            hand->delay = 0;
            /* C1's per-hand function returns 1 exactly on the frame its delay
             * reaches zero (0x41af6d..0x41af97) and returns 0 otherwise; the
             * melee check refuses while any hand reports it. */
            hand->delay_expired = 1;
            if(hand->state==CODOL_WEAPONSTATE_RECHAMBERING && hand->rechamber) {
                /* C1 418fce clears the inventory latch and 418fdc emits
                 * brass only when the bolt delay expires. */
                set_second_rechamber(state,0);
                add_player_event(ps,(BGEvent)CODOL_EV_EJECT_BRASS_SECONDARY);
            }
            if(hand->shot_pending && record) {
                hand->shot_pending = 0;
                hand_take_shot(state, ps, def, record);
            } else if(hand->state == CODOL_WEAPONSTATE_RELOADING ||
                      hand->state == CODOL_WEAPONSTATE_RELOADING_AGAIN ||
                      hand->state == CODOL_WEAPONSTATE_RELOAD_SEGMENT ||
                      hand->state == CODOL_WEAPONSTATE_RELOAD_INTERRUPT) {
                if(record) hand_reload_delayed(state,ps,def,record);
            }
        }
    }
    {
        if(hand->time > 0) {
            /* Still running a phase, but PM_Weapon calls CheckForReload every
             * frame regardless of state (PM_Weapon_410): that is exactly where
             * a segmented reload gets interrupted part-way through its own
             * animation, so a busy hand has to run it too. */
            hand_check_for_reload(state, ps, pm, def, record);
            return;
        }
        if(hand->delay && !hand->delay_expired)return;
        hand->time = 0;
        /* Dispatch zero-duration phases too, as C1 41da44..41da79 does;
         * requiring a previously positive timer strands them permanently. */
        switch(hand->state) {
        case CODOL_WEAPONSTATE_DROPPING:
        case CODOL_WEAPONSTATE_DROPPING_QUICK:
            /* The retained machine owns which weapon comes next; this hand
             * follows it and raises with its own timing. */
            hand->weapon = ps->weapon;
            if(!(def = weapon_def(hand->weapon))) {
                memset(hand, 0, sizeof(*hand));
                return;
            }
            start_second_raise(state, ps, def);
            return;
        case CODOL_WEAPONSTATE_RAISING:
        case CODOL_WEAPONSTATE_RAISING_ALT:
        case CODOL_WEAPONSTATE_RELOAD_END:
            hand->state = CODOL_WEAPONSTATE_READY;
            set_animation(hand, ANIM_IDLE);
            break;
        case CODOL_WEAPONSTATE_RELOADING:
        case CODOL_WEAPONSTATE_RELOADING_AGAIN:
            /* C1 41a550 transfers only on its delay-expired argument,
             * handled above; completion separately clears the bolt latch. */
            if(def->bSegmentedReload && pressed) hand->state = CODOL_WEAPONSTATE_RELOADING_AGAIN;
            set_second_rechamber(state,0);
            if(!def->bSegmentedReload) {
                hand->state = CODOL_WEAPONSTATE_READY;
                set_animation(hand, ANIM_IDLE);
                break;
            }
            if(hand->state == CODOL_WEAPONSTATE_RELOADING_AGAIN || !record ||
               !hand_reload_continues(ps, def, record)) hand_reload_end(state, ps, def);
            else hand_begin_reload(state, ps, def, record);
            return;
        case CODOL_WEAPONSTATE_RELOAD_SEGMENT:
        case CODOL_WEAPONSTATE_RELOAD_INTERRUPT:
            /* PM_Weapon_2320. Holding the trigger asks to break out, which is
             * only honoured once the magazine is no longer empty. */
            if(def->bSegmentedReload && pressed) hand->state = CODOL_WEAPONSTATE_RELOAD_INTERRUPT;
            if(!record) { hand_reload_end(state, ps, def); return; }
            if(hand->state == CODOL_WEAPONSTATE_RELOAD_INTERRUPT && record->ammo[1])
                hand_reload_end(state, ps, def);
            else if(!hand_reload_continues(ps, def, record)) hand_reload_end(state, ps, def);
            else hand_begin_reload(state, ps, def, record);
            return;
        case CODOL_WEAPONSTATE_FIRING:
            if(hand->rechamber) {
                /* PM_Weapon_610: state 6 with iRechamberTime, the bolt time in
                 * weaponDelay when it is shorter, and EV_RECHAMBER_WEAPON. */
                int duration = rechamber_time(def, (int)state->dual_wield);
                hand->state = CODOL_WEAPONSTATE_RECHAMBERING;
                /* C1 4190c3 stores the selected duration verbatim; only
                 * the missing/overlong bolt delay is replaced with one. */
                hand->time = duration;
                if(def->iRechamberBoltTime > 0 && def->iRechamberBoltTime < hand->time)
                    hand->delay = def->iRechamberBoltTime;
                else hand->delay = 1;
                set_animation(hand, ps->fWeaponPosFrac > ADS_ANIMATION_FRACTION ?
                    ANIM_RECHAMBER_ADS : ANIM_RECHAMBER);
                add_player_event(ps, EV_RECHAMBER_WEAPON);
                return;
            }
            /* PM_Weapon_1840: a completed burst returns to idle and waits out
             * CoDOL's 200 ms burst wait before the trigger can act again. */
            cooldown = hand_burst_cooldown(hand, def, record);
            hand->state = CODOL_WEAPONSTATE_READY;
            set_animation(hand, ANIM_IDLE);
            if(cooldown) { hand->time = cooldown; hand->shot_count = 0; return; }
            break;
        case CODOL_WEAPONSTATE_RECHAMBERING:
            if(hand->delay) return;
            hand->state = CODOL_WEAPONSTATE_READY;
            set_animation(hand, ANIM_IDLE);
            break;
        case CODOL_WEAPONSTATE_READY:
            break; /* A burst cooldown expiring must not restart the idle. */
        default:
            hand->state = CODOL_WEAPONSTATE_READY;
            set_animation(hand, ANIM_IDLE);
            break;
        }
    }
    hand_check_for_reload(state, ps, pm, def, record);
    if(hand->state != CODOL_WEAPONSTATE_READY || hand->time > 0 || hand->delay > 0) return;
    if(!record) return;
    /* Melee and sprint are the two phases the retained engine runs for the
     * whole player rather than for one hand: they drive
     * PM_SetProneMovementOverride and the player-wide movement override, and
     * the body performs one melee no matter how many weapons it holds. C1
     * keeps them in a hand block like every other phase (all its state writes
     * address one block; the indexed one is 0x418f31), so the second hand gets
     * the same phase rather than standing still through it. It is entered once,
     * at the transition, with its own animation toggle and its own clock -- not
     * re-read every frame -- and it ends when its own timer runs out or the
     * engine leaves the phase, whichever comes first. */
    if(player_wide_phase(ps->weaponstate)) {
        if(!player_wide_phase(state->engine_state) || !player_wide_phase(hand->state)) {
            hand->state = ps->weaponstate;
            hand->time = ps->weaponTime > 0 ? ps->weaponTime : 1;
            hand->delay = 0;
            hand->shot_pending = 0;
            set_animation(hand, (unsigned)ps->weapAnim & 0x1fu);
        }
        return;
    }
    if(player_wide_phase(hand->state)) {
        hand->state = CODOL_WEAPONSTATE_READY;
        hand->time = 0;
        set_animation(hand, ANIM_IDLE);
    }

    /* Re-checked against the actual C1 gates. Every weaponstate write in C1
     * targets one hand's block (they all address it through a hand-block
     * pointer, or by index at 0x418f31), and the per-hand machine gates firing
     * on THIS hand's state alone: 0x41ae81 refuses while it is in the offhand
     * range, CoDOL 16..21, which is native 15..20 through the existing state
     * map. The genuinely cross-hand rules live elsewhere and are already
     * implemented -- the melee start refuses while any hand is raising or
     * dropping (0x41c070) and the whole weapon-change/offhand/melee block is
     * skipped while any hand is mid-burst (0x41dc56/0x41dc66). So the previous
     * blanket "engine hand is past 12" hold was wrong and is gone.
     *
     * Two retained states are still held, and this is a stated divergence
     * rather than a C1 gate: 12..14 (melee) and 22..24 (sprint) are not
     * per-hand in the retained engine at all. They drive
     * PM_SetProneMovementOverride and the player-wide movement override, so a
     * second hand firing through them would contradict the machine that owns
     * them here. The retained offhand throw needs no state test: it raises
     * weapFlags bit 2, which is gated below. */
    if(hand->state >= 15 && hand->state <= 20) return;
    /* PM_Weapon_420's two suspensions, which reach the retained machine before
     * any weapon decision: a mantle that makes the weapon inactive, and
     * pm_flags bit 3, which forces the weapon down. */
    if(Mantle_IsWeaponInactive(ps)) return;
    if(ps->pm_flags & 0x8) return;
    /* weapFlags bit 2 is the offhand viewmodel: the retained fire path then
     * works from ps->offHandIndex (PM_Weapon_1810) and this hand's weapon is
     * not the one being used. */
    if(ps->weapFlags & 0x2) return;

    /* C1's fire gate (0x41b240, fed at 0x41b2cb): the trigger ORed with the
     * burst this hand still owes. While the quota is spent and the trigger is
     * still held the weapon time is pinned to 1 (0x41aed5) so the gate cannot
     * reopen; releasing clears the counter and the pin (0x41af59/0x41af63).
     * That, not an edge test, is what makes a semi-automatic weapon fire once
     * per pull -- and it is why a released trigger cannot cut a burst short. */
    requested = hand_fire_requested(ps, pm, def, (int)state->dual_wield, 1);
    wants = requested || hand_burst_owed(hand, def, record);
    if(!wants) {
        if(!hand_burst_owed(hand, def, record)) hand->shot_count = 0;
        hand->time = 0;
        return;
    }
    /* 0x41aed5: a hand whose trigger is spent, or whose weapon holds fire,
     * keeps weaponTime at 1 so its gate cannot reopen. Two further terms of
     * that decision were missing here and are measured, not assumed: 0x41ae9f
     * takes the button word alone, so a burst still owed with the trigger
     * released falls through instead of pinning, and 0x41aec3 requires ammo in
     * *this hand's* magazine, so an empty one falls through as well. C1's
     * remaining term, ps->weapon == pm->weapon (0x41aeae), is already implied:
     * this hand's weapon and its definition were resolved from the state this
     * pmove is running. */
    if(requested && record->ammo[1] > 0 &&
       hand_should_pin(hand, def, (int)state->dual_wield, (int)state->second_barrel,
                       state->command_valid ? state->command_buttons : 0u,
                       state->command_valid)) { hand->time = 1; return; }
    /* Fire type 6 additionally waits for a full spin-up: C1 0x41b2f6 compares
     * the charge against 1.0 and only then reports the weapon ready. */
    if(def->fireType == 6 && !(state->spinup_charge >= 1.0f)) return;
    if(record->ammo[1] <= 0) return;
    hand_begin_fire(state, ps, def, record);
}

/* ------------------------------------------------------------------ */
/* Frame producer                                                      */
/* ------------------------------------------------------------------ */

/* The second hand may only run when the player is alive, holding a real weapon
 * and not driving a turret or vehicle: the same gates PM_Weapon itself applies
 * at its entry (pm_type above 6, native turret eFlags) and around the fire path
 * (weapFlags 0x80, the global weapon disable this tree already documents in
 * codol_weapon_flags.h). */
static int second_hand_runnable(const playerState_t *ps)
{
    if(ps->pm_type > 7) return 0;
    if(ps->eFlags & PLAYER_EFLAG_TURRET_MASK) return 0;
    if(ps->weapFlags & 0x80) return 0;
    return 1;
}


/* Publish this frame's hand into the extension that travels with the
 * playerState. Everything a consumer reads -- the phase, its clock, the second
 * magazines, the records naming the hand behind each queued event and the
 * spin-up charge -- is read back from there, so a spectator following a delayed
 * player and any frame built from an older ring slot or the archive see the
 * hand of that state rather than the live client's. The live machine below
 * stays keyed by client because it is a producer, not a source of truth. */
static void publish_hand(codol_weapon_state_t *state, playerState_t *ps)
{
    codol_ps_hand_t *out = CODOL_PlayerStateHandMutable(ps);
    const codol_weapon_hand_t *hand = state->hand + 1;
    unsigned i, charge;
    if(!out) return;
    out->dual_wield = state->dual_wield ? 1 : 0;
    memcpy(out->second_rechamber,state->second_rechamber,sizeof(out->second_rechamber));
    for(i=0;i<CODOL_WEAPON_BIT_WORDS;++i)out->fast_mag[i]&=CODOL_WeaponBitsOwnedWord(ps,i);
    out->second_barrel = state->second_barrel ? 1 : 0;
    out->fresh_pull = hand->fresh_pull ? 1 : 0;
    out->state = (unsigned char)(hand->state & 0x3f);
    out->shot_count = (unsigned char)(hand->shot_count & 7u);
    out->weapon = (uint16_t)(hand->weapon < CODOL_WEAPON_SLOTS ? hand->weapon : 0);
    out->primary_weapon = (uint16_t)(state->primary_weapon < CODOL_WEAPON_SLOTS ? state->primary_weapon : 0);
    out->animation = (uint16_t)((unsigned)hand->animation & 0x7ffu);
    out->time = (int16_t)(hand->time < -32768 ? -32768 : hand->time > 32767 ? 32767 : hand->time);
    out->delay = (int16_t)(hand->delay < -32768 ? -32768 : hand->delay > 32767 ? 32767 : hand->delay);
    out->restrict_time = (int16_t)(hand->restrict_time < 0 ? 0 :
        hand->restrict_time > 32767 ? 32767 : hand->restrict_time);
    charge = (unsigned)(state->spinup_charge * 1000.0f + 0.5f);
    out->charge = (uint16_t)(charge > 1000 ? 1000 : charge);
    out->shot_hand = out->shot_last = out->shot_known = 0;
    for(i = 0; i < 4; ++i) {
        if(!state->ring_known[i]) continue;
        out->shot_known |= (unsigned char)(1u << i);
        if(state->ring_hand[i]) out->shot_hand |= (unsigned char)(1u << i);
        if(state->ring_lastshot[i]) out->shot_last |= (unsigned char)(1u << i);
    }
    for(i = 0; i < CODOL_WEAPON_CLIP_SLOTS && i < CODOL_PS_HAND_CLIPS; ++i) {
        out->clip_index[i] = (int16_t)state->clips[i].clip_index;
        out->magazine[i] = (int16_t)(state->clips[i].ammo[1] < 0 ? 0 :
            state->clips[i].ammo[1] > 511 ? 511 : state->clips[i].ammo[1]);
    }
}

void CODOL_WeaponStateUpdate(struct pmove_t *pm, struct pml_t *pml)
{
    playerState_t *ps;
    codol_weapon_state_t *state;
    int msec;
    unsigned i;
    if(!pm || !pml || !(ps = pm->ps) || !(state = state_of(ps))) return;
    if(!state->initialized) CODOL_ResetClientWeaponState((unsigned)ps->clientNum);
    if(ps->weapon != state->hand[0].weapon)
        select_weapon(state, ps, state->hand[0].weapon, ps->weapon);
    if(owned_changed(state, ps)) rekey_records(state, ps);
    for(i = 0; i < CODOL_WEAPON_CLIP_SLOTS; ++i) {
        codol_weapon_clip_t *record = state->clips + i;
        if(record->clip_index < 0) continue;
        /* Magazine records belong to inventory, including holstered weapons.
         * Ownership removal clears them in rekey_records. */
        record->ammo[0] = ps->ammoclip[record->clip_index];
    }

    /* Capture the raw command this pmove is running, once, for the producers
     * that need CoDOL-only bits and have no pmove of their own. */
    {
        codol_weapon_input_t input;
        int bound = executed_input(ps, &input) && (input.kind == CODOL_INPUT_NETWORK || input.raw_valid);
        state->command_valid = bound ? 1u : 0u;
        state->command_buttons = bound ? input.raw_buttons : 0u;
        /* Every PM_Weapon pass ends here, so the first substep of a command
         * is recorded even when nothing asked for an offhand edge in it. */
        if(bound && input.raw_valid) (void)first_substep(ps, &input, pm);
    }
    msec = pml->msec;
    if(msec < 0) msec = 0;
    /* The spin-up charge belongs to the weapon, not to a hand; C1 advances it
     * once per pmove frame before the per-hand machines run, which is now
     * CODOL_WeaponStateSpinUpFrame at PM_Weapon's entry. */
    if(state->dual_wield && state->hand[1].weapon && second_hand_runnable(ps))
        advance_second_hand(state, ps, pm, msec);
    else if(!state->dual_wield)
        memset(state->hand + 1, 0, sizeof(state->hand[1]));

    state->hand[0].weapon = ps->weapon;
    state->hand[0].state = ps->weaponstate;
    state->hand[0].animation = ps->weapAnim;
    state->hand[0].time = ps->weaponTime;
    state->hand[0].delay = ps->weaponDelay;
    state->hand[0].restrict_time = ps->weaponRestrictKickTime;
    state->hand[0].shot_count = ps->weaponShotCount;
    /* C1 arms the fresh trigger-pull latch for burst weapons only, and that
     * bracket now lives where C1 puts it: at the arm itself, _bg_weapons.asm
     * PM_Weapon_360, against 0x41ab29..0x41ab31. Clearing it here instead was
     * this pass's predecessor and is withdrawn -- PM_Weapon_170 sets the latch
     * and PM_Weapon_1830 consumes it inside a single PM_Weapon call, while
     * this runs at PM_Weapon_20 on the way out, so the clear could never reach
     * the pin decision that read it. */
    state->hand[0].fresh_pull = ((unsigned)ps->weapFlags >> 8) & 1u;
    state->hand[0].rechamber = ps->weapon < CODOL_WEAPON_STATE_WEAPONS &&
        CODOL_WeaponBitsRechamberTest(ps, ps->weapon);
    state->engine_state = ps->weaponstate;
    state->engine_animation = ps->weapAnim;
    CODOL_WeaponStateRefreshOffhands(ps);
    publish_hand(state, ps);
}

/* ------------------------------------------------------------------ */
/* Queries                                                             */
/* ------------------------------------------------------------------ */

int CODOL_WeaponStateHand(const playerState_t *ps, unsigned hand, codol_weapon_hand_t *out)
{
    const codol_ps_hand_t *carried;
    if(!ps || !out || hand >= CODOL_WEAPON_HANDS) return 0;
    carried = CODOL_PlayerStateHandRead(ps);
    memset(out, 0, sizeof(*out));
    if(hand) {
        out->weapon = carried->weapon;
        out->state = carried->state;
        out->animation = carried->animation;
        out->time = carried->time;
        out->delay = carried->delay;
        out->restrict_time = carried->restrict_time;
        out->shot_count = carried->shot_count;
        out->fresh_pull = carried->fresh_pull;
        if(carried->weapon<CODOL_WEAPON_STATE_WEAPONS)
            out->rechamber=!!(carried->second_rechamber[carried->weapon>>5]&
                (1u<<(carried->weapon&31)));
        return 1;
    }
    /* Hand 0 is the engine's own machine; read it live so a query made before
     * this frame's producer runs still reports the retained truth. */
    if(hand == 0) {
        out->weapon = ps->weapon;
        out->state = ps->weaponstate;
        out->animation = ps->weapAnim;
        out->time = ps->weaponTime;
        out->delay = ps->weaponDelay;
        out->restrict_time = ps->weaponRestrictKickTime;
        out->shot_count = ps->weaponShotCount;
        out->fresh_pull = ((unsigned)ps->weapFlags >> 8) & 1u;
        if(ps->weapon < CODOL_WEAPON_STATE_WEAPONS)
            out->rechamber = CODOL_WeaponBitsRechamberTest(ps, ps->weapon);
    }
    return 1;
}

int CODOL_WeaponStatePrimaryWeapon(const playerState_t *ps, unsigned *primary)
{
    const struct WeaponDef *def;
    unsigned carried;
    if(!ps || !primary) return 0;
    if(!ps->weapon) { *primary = 0; return 1; }
    if(!(def = weapon_def(ps->weapon))) return 0;
    if(def->inventoryType != WEAPINVENTORY_ALTMODE) { *primary = ps->weapon; return 1; }
    carried = CODOL_PlayerStateHandRead(ps)->primary_weapon;
    if(!carried || !weapon_def(carried)) return 0;
    *primary = carried;
    return 1;
}

int CODOL_WeaponStateClipAmmoByIndex(const playerState_t *ps, int clip_index, unsigned hand, int *ammo)
{
    const codol_ps_hand_t *carried;
    unsigned i;
    if(!ps || !ammo || hand >= CODOL_WEAPON_HANDS) return 0;
    *ammo = 0;
    if(clip_index < 0 || clip_index >= 128) return 1;
    /* The retained first-hand magazine is directly indexed by the definition's
     * clip key. It is already valid after giveweapon/setweaponammoclip, before
     * the next movement frame rebuilds the secondary-hand record list. */
    if(hand == 0) { *ammo = ps->ammoclip[clip_index]; return 1; }
    carried = CODOL_PlayerStateHandRead(ps);
    for(i = 0; i < CODOL_PS_HAND_CLIPS; ++i) {
        if(carried->clip_index[i] != clip_index) continue;
          /* Only the second hand uses the record bundle carried with ps. */
          *ammo = carried->magazine[i];
        return 1;
    }
    return 1;
}

int CODOL_WeaponStateClipAmmo(const playerState_t *ps, unsigned weapon, unsigned hand, int *ammo)
{
    const struct WeaponDef *def;
    if(!ps || !ammo || hand >= CODOL_WEAPON_HANDS) return 0;
    if(!(def = weapon_def(weapon))) { *ammo = 0; return 1; }
    return CODOL_WeaponStateClipAmmoByIndex(ps, clip_of(def), hand, ammo);
}

int CODOL_WeaponStateSetLeftClip(playerState_t *ps,unsigned weapon,int ammo)
{
    codol_weapon_state_t *state=state_of(ps);
    const struct WeaponDef *def=weapon_def(weapon);
    codol_weapon_clip_t *record;
    if(!state || !def || ammo<0 || !CODOL_WeaponIsDualWield(weapon))return 0;
    if(!state->initialized)CODOL_ResetClientWeaponState((unsigned)ps->clientNum);
    if(owned_changed(state,ps))rekey_records(state,ps);
    record=record_for(state,clip_of(def));
    if(!record)return 0;
    record->ammo[1]=ammo>def->iClipSize?def->iClipSize:ammo;
    publish_hand(state,ps);
    return 1;
}

static int switching_state(int state)
{
    return state >= CODOL_WEAPONSTATE_RAISING && state <= CODOL_WEAPONSTATE_DROPPING_QUICK;
}
static int reload_state(int state)
{
    return state >= CODOL_WEAPONSTATE_RELOADING && state <= CODOL_WEAPONSTATE_RELOAD_END;
}

/* C1 combines the two per-hand results with max() at PM_Weapon 0x41dcb4 and
 * hands the result to the melee check at 0x41c070, which refuses when that
 * value is nonzero (0x41c104), when any hand carries a pending weaponDelay
 * outside the reload family (0x41c14e) or when any hand is raising or dropping
 * (0x41c171). The retained PM_Weapon applies exactly those three rules to its
 * own hand just before PM_MeleeChargeStart; this reports them for the second. */
int CODOL_WeaponStateSecondHandBlocksMelee(const playerState_t *ps)
{
    const codol_ps_hand_t *carried;
    const codol_weapon_state_t *state;
    if(!ps) return 0;
    carried = CODOL_PlayerStateHandRead(ps);
    if(!carried->weapon) return 0;
    /* The one-frame "this hand's delayed action landed" flag is not part of the
     * state a snapshot carries: this gate runs inside the same server frame its
     * producer ran in, so it reads the live machine for that bit alone. */
    state = state_of(ps);
    if(state && state->hand[1].delay_expired) return 1;
    if(carried->delay > 0 && !reload_state(carried->state)) return 1;
    return switching_state(carried->state);
}

/* C1 PM_Weapon asks 0x41aa70 for each hand at 0x41dc56/0x41dc66 and skips the
 * whole weapon-change, offhand and melee block while either answers yes. That
 * helper reports a hand whose own three-bit shot counter (ps+0x280 + hand*0x1c,
 * tested at 0x41aab5) is still inside its burst. */
int CODOL_WeaponStateSecondHandBursting(const playerState_t *ps)
{
    const codol_ps_hand_t *carried;
    const struct WeaponDef *def;
    if(!ps) return 0;
    carried = CODOL_PlayerStateHandRead(ps);
    if(!carried->weapon || !carried->shot_count) return 0;
    if(!(def = weapon_def(carried->weapon))) return 0;
    if(CODOL_WeaponStateHandClipSpent(ps, 1)) return 0;
    return def->fireType >= WEAPON_FIRETYPE_BURSTFIRE2 &&
           def->fireType <= WEAPON_FIRETYPE_BURSTFIRE4;
}

/* C1 0x418ec0 for one hand of the held weapon, the test the burst-continuation
 * helper 0x41aa70 makes before anything else: a bullet weapon (definition
 * +0x340, weapType; 0x41b79c's grenade test reads the same field) whose
 * magazine for this hand holds nothing -- the fifteen {clipKey, ammo[2]}
 * records at ps+0x3d8, or no record at all -- owes no more rounds of a burst.
 * 0x41aa70 then answers no, so the firing phase ends in the 200 ms wait
 * (0x41ad7d), the shot counter clears (0x41af4d) and the weapon-change block
 * runs again (0x41dc56/0x41dc66). The retained hand-0 machine asks this from
 * _bg_weapons.asm (CODOL_BURST_CLIP_SPENT); both hands share ps->weapon, as
 * 0x41aa70 reads ps+0x33c for either. */
int CODOL_WeaponStateHandClipSpent(const playerState_t *ps, unsigned hand)
{
    const struct WeaponDef *def;
    int ammo;
    if(!ps || hand >= CODOL_WEAPON_HANDS || !(def = weapon_def(ps->weapon))) return 0;
    if(def->weapType != WEAPTYPE_BULLET) return 0;
    if(!CODOL_WeaponStateClipAmmo(ps, ps->weapon, hand, &ammo)) return 0;
    return ammo == 0;
}
int CODOL_WeaponStateIsSwitching(const playerState_t *ps)
{
    const codol_ps_hand_t *carried;
    if(!ps) return 0;
    if(switching_state(ps->weaponstate)) return 1;
    carried = CODOL_PlayerStateHandRead(ps);
    return carried->weapon && switching_state(carried->state);
}

int CODOL_WeaponStateIsReloading(const playerState_t *ps)
{
    if(!ps) return 0;
    /* IW4 5d9ec1..5d9efd tests both hand states, without a session or
     * current-weapon gate. Its reload family8..12 maps to native7..11:
     * reload, reload-again, segmented start/interruption, and reload-end. */
    return reload_state(ps->weaponstate) ||
           reload_state(CODOL_PlayerStateHandRead(ps)->state);
}

int CODOL_WeaponStateIsDualWielding(const playerState_t *ps)
{
    /* IW4 5d9e41 compares the stored playerState dual-wield field to exactly1.
     * Selection publishes our equivalent into the hand extension; use that
     * captured value rather than querying today's weapon asset or live slot. */
    return ps && CODOL_PlayerStateHandRead(ps)->dual_wield == 1;
}
#endif
