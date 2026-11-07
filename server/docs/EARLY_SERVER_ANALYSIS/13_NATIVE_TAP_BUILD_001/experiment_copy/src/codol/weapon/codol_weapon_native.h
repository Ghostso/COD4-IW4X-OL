#ifndef CODOL_WEAPON_NATIVE_H
#define CODOL_WEAPON_NATIVE_H
#include "codol_assets.h"
#include "xassets/weapondef.h"
#include "codol_weapon_registry.h"
#include "codol_weapon_attachment.h"
#include "codol_sound_native.h"
#include "codol_missile_stickiness.h"
#include "codol_bomb.h"
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif
/* C1 +bbe byte gates firing on finalized lock state. */
int CODOL_ApplyNativeWeaponLockRequirement(const codol_mounted_weapon_t *,struct WeaponDef *);
typedef struct {
    int rechamber_variant; /* Source +0x5b0, selected when ps+0x35c == 1. */
    int reload_variant; /* Source +0x5cc, alternate reload branch. */
    int reload_empty_variant; /* Source +0x5d8. */
    int reload_add_variant; /* Source +0x5e0. */
    int reload_empty_add; /* Source +0x5e4; IW3 has only one reload-add field. */
    int reload_empty_add_variant; /* Source +0x5e8. */
    int dive_in; /* Source +0x630; CoDOL dive state 0x1f. */
    int dive_out; /* Source +0x638; CoDOL dive state 0x21. */
    /* Fire type 6 spin-up: C1 0x418414 charges ps+0x5c0 by msec/+0xb3c while
     * the trigger is held and 0x418420 decays it by -msec/+0xb40, clamped to
     * 0..1; the fire gate 0x41b2f6 only opens at 1.0. The retained WeaponDef
     * has neither duration, so they stay in this extension record. */
    int spin_up; /* Source +0xb3c, milliseconds. */
    int spin_down; /* Source +0xb40, milliseconds. */
} codol_weapon_timing_extensions_t;
/* Applies verified fire/detonation, ADS transition, reload/change and sprint
 * timing fields; all other native fields
 * remain unchanged. Retains timing variants without IW3 fields separately.
 * This does not construct or publish a complete WeaponDef. Failure leaves
 * both outputs unchanged. Negative durations are invalid; zero is preserved. */
int CODOL_ApplyNativeWeaponTimings(const codol_mounted_weapon_t *,struct WeaponDef *,
    codol_weapon_timing_extensions_t *);
/* Maps starting ammo, maximum reserve, clip capacity, pellet/shot count and ordinary/start
 * reload transfer caps, shared ammo cap, clip-only, no-partial-reload and
 * segmented-reload flags.
 * Zero caps are preserved for the engine. Native ammo, shared-cap
 * and clip indices are runtime registrations, never copied from serialized
 * CoDOL indices. Preserves all other fields and the whole output on failure. */
int CODOL_ApplyNativeWeaponAmmo(const codol_mounted_weapon_t *,struct WeaponDef *);
/* Base-definition melee damage and normal/charge timing values. Attachment
 * overrides and the CoDOL melee state machine require separate integration.
 * No defaults are fabricated; invalid input leaves the whole output unchanged. */
int CODOL_ApplyNativeWeaponMelee(const codol_mounted_weapon_t *,struct WeaponDef *);
/* Base bullet damage and distance falloff, measured in C1's damage reader.
 * Does not flatten attachment overrides or replace the engine damage path.
 * Finite nonnegative ranges/damage required; failure preserves all of out. */
int CODOL_ApplyNativeWeaponDamage(const codol_mounted_weapon_t *,struct WeaponDef *);
/* Source hit-location order matches IW3 for its first 19 slots; CoDOL's
 * twentieth shield multiplier is retained separately. Does not multiply in
 * global hit-location damage settings. Nonnegative finite values; atomic. */
int CODOL_ApplyNativeWeaponLocationDamage(const codol_mounted_weapon_t *,struct WeaponDef *,float *shield_multiplier);
/* Verified ADS/hip reduced-kick counts/percentages, gun pitch/yaw ranges,
 * acceleration/speed/decay, and view pitch/yaw ranges. Signed/reversed angular
 * ranges are preserved. Other values are finite/nonnegative; counts fit int.
 * Atomic output; view centering/scatter and recoil gameplay remain separate. */
int CODOL_ApplyNativeWeaponRecoil(const codol_mounted_weapon_t *,struct WeaponDef *);
/* Shared trigger modes and the per-shot rechamber gate. CoDOL double-barrel
 * and spin-up modes require native gameplay extensions and are rejected;
 * never substitute full-auto/single-shot for them. Atomic on failure. */
int CODOL_ApplyNativeWeaponFireMode(const codol_mounted_weapon_t *,struct WeaponDef *);
/* Exact per-millisecond ADS rates and the verified enable/rechamber flags.
 * Does not reconstruct integer durations or map CoDOL reload-while-ADS.
 * Finite nonnegative rates and serialized boolean bytes required; atomic. */
int CODOL_ApplyNativeWeaponAds(const codol_mounted_weapon_t *,struct WeaponDef *);
/* Weapon hip/ADS movement multipliers and sprint-duration multiplier.
 * Preserve zero and values above one; reject negative/nonfinite values.
 * Does not flatten player perks or composed-weapon overrides; atomic. */
int CODOL_ApplyNativeWeaponMovement(const codol_mounted_weapon_t *,struct WeaponDef *);
/* Shared bullet/grenade/projectile types and primary/offhand/item/altmode
 * inventory roles; CODOL_SERVER additionally preserves exclusive/scavenger.
 * Reject CoDOL riotshield/bomb weapon types rather than reinterpreting them
 * as IW3 binoculars. Weapon class
 * is separate (CoDOL adds sniper/throwingknife) and remains untouched. Atomic. */
int CODOL_ApplyNativeWeaponType(const codol_mounted_weapon_t *,struct WeaponDef *);
/* Translates the ten shared class names from source +344 to native enum IDs.
 * Source sniper (1) and throwingknife (9) need gameplay extensions and reject;
 * they are not substituted with rifle, MG or item. Atomic, other fields intact. */
int CODOL_ApplyNativeWeaponClass(const codol_mounted_weapon_t *,struct WeaponDef *);
/* Penetration none/small/medium/large and all six CoDOL offhand classes,
 * including alternate frag and equipment used by the three-slot selector. Does not
 * implement penetration traces, grenade behavior or stance. Atomic output. */
int CODOL_ApplyNativeWeaponCombatClasses(const codol_mounted_weapon_t *,struct WeaponDef *);
typedef struct {
    float (*points[4])[2]; /* Active graphs 0/1, then original graphs 0/1. */
} codol_native_weapon_graphs_t;
/* Copies serialized graph pairs into owned, aligned native arrays. Graph names
 * borrow archive lifetime. owner must be zero/prior, and out must stop using
 * its arrays before owner is freed. Failure preserves both outputs. */
int CODOL_BindNativeWeaponGraphs(const codol_weapon_tail_t *,struct WeaponDef *,codol_native_weapon_graphs_t *);
void CODOL_FreeNativeWeaponGraphs(codol_native_weapon_graphs_t *);
/* Assigns registration keys, defaulting empty ammo/clip names to internalName.
 * Empty shared-cap names disable sharing. Borrowed names; indices untouched. */
int CODOL_ApplyNativeWeaponAmmoNames(const codol_weapon_ammo_names_t *,const char *internalName,struct WeaponDef *);
/* Maps verified hip/ADS spread parameters only. Requires finite nonnegative
 * source values; failure preserves out. Does not implement firing behavior. */
int CODOL_ApplyNativeWeaponSpread(const codol_mounted_weapon_t *,struct WeaponDef *);
/* Copies fuse duration (+654), timed-detonation ownership (+be2), and held
 * cook-off gating (+bcc). Zero duration is preserved independently of the
 * two flags; the missile scheduler decides its lifetime. Atomic on failure. */
int CODOL_ApplyNativeWeaponFuse(const codol_mounted_weapon_t *,struct WeaponDef *);
/* Verified launch velocity components and radius/inner/outer blast damage.
 * Preserve signed serialized integers and zero; atomic on invalid input. */
int CODOL_ApplyNativeWeaponProjectile(const codol_mounted_weapon_t *,struct WeaponDef *);
/* C1 surface IDs are retained by the collision material loader. These arrays
 * have 31 entries, unlike the retained WeaponDef's 29-entry arrays. */
#define CODOL_WEAPON_BOUNCE_SURFACES 31
typedef struct {
    float parallel[CODOL_WEAPON_BOUNCE_SURFACES];
    float perpendicular[CODOL_WEAPON_BOUNCE_SURFACES];
    unsigned char rolling; /* C1 +bdb, checked with dvar1194. */
} codol_weapon_bounce_t;
int CODOL_ReadNativeWeaponBounce(const codol_mounted_weapon_t *,codol_weapon_bounce_t *);
/* Returns parallel/perpendicular in out[0]/out[1], without changing out on
 * missing definition or invalid surface. Never indexes the IW3 arrays. */
int CODOL_GetNativeWeaponBounce(const struct WeaponDef *,unsigned surface,float out[2]);
int CODOL_GetNativeWeaponRolling(const struct WeaponDef *,int *enabled);
typedef struct {
    const char *pickup;         /* Sound slot 0, source +0x364. */
    const char *pickup_player;  /* Sound slot 1, source +0x368. */
    const char *proj_explosion; /* Tail sound record at source +0x7c0. */
} codol_native_weapon_sounds_t;
/* Selects the verified pickup and projectile-explosion sound names from
 * resolved source views. CoDOL stores names, not native alias assets, so no
 * snd_alias_list_t is fabricated here. Empty and null slots become null and
 * names borrow archive lifetime. The tail must carry exactly one +0x7c0 sound
 * record. Failure preserves the whole output. */
int CODOL_ApplyNativeWeaponSoundNames(const codol_weapon_sounds_t *,
    const codol_weapon_tail_t *,codol_native_weapon_sounds_t *);
/* Applies 28 verified shared animation-name roles from a resolved source view.
 * Unverified native slots remain unchanged. The caller must retain the complete
 * source view (all 144 slots) for CoDOL variants; names borrow archive lifetime.
 * This does not load XAnimParts or translate network animation IDs. */
int CODOL_ApplyNativeWeaponAnimationNames(const codol_weapon_animations_t *,struct WeaponDef *);
/* Source slots: hands, two view models, two world models, magazine and
 * view/world knife models. Slots 6/9/10 remain unbound native roles. All populated
 * references require genuine native XModels retained for the weapon lifetime.
 * Clears unused tails of the larger IW3 arrays. Failure preserves out; other
 * weapon fields are untouched. Does not register a complete weapon. */
int CODOL_BindNativeWeaponModels(const codol_mounted_weapon_t *,const XModel *const [11],struct WeaponDef *);
typedef struct {
    struct WeaponDef definition;
    unsigned source_weapon_class; /* C1 +0x344, before retained class mapping. */
    codol_bomb_weapon_t bomb; /* C1 source types and explicit-velocity launch data. */
    codol_weapon_timing_extensions_t timings;
    codol_missile_stickiness_t missile_stickiness;
    codol_weapon_bounce_t bounce;
    float shield_damage_multiplier;
    unsigned char inherits_perks; /* C1 +0xbc2; script query 0x541a80. */
    unsigned char lock_warning_gate; /* C1 +0xbbd; firing checks at 0x41b9f3. */
    unsigned char dual_wield; /* C1 +0xbd5; read at 0x419d51 to set ps+0x35c. */
    unsigned char riot_shield; /* C1 +0x340 == 3; PM 0x41979a sets weapFlags 0x1000 while raising it. */
    unsigned char ads_reload; /* C1 +0xbca; permits ADS through reload states. */
    unsigned char dual_mag; /* C1 +0xbc7; alternating quick reload magazine. */
    /* Two grenade-type behaviours the retained WeaponDef cannot express:
     * +0xbe0 makes the weapon fire on the second trigger alone (C1 0x41b207,
     * the remote-detonated equipment), and +0xbe4 makes it pin its weapon
     * time whatever the trigger quota says (0x41ae09, the plant weapons). */
    unsigned char detonate_trigger, hold_pin;
    /* +0xbe5 requires the player to be standing on something before the weapon
     * may be raised or fired: C1 tests it against ps+0xa8 -- groundEntityNum,
     * which the movement code writes with the 0x7ff sentinel throughout and
     * BG_PlayerStateToEntityState publishes at 0x40d15b -- in
     * PM_Weapon_CheckForOffHand at 0x41cbcd and again in the fire request at
     * 0x41b2aa. */
    unsigned char requires_ground;
    /* +0xbec lets the cancel button 0x400000 end an offhand before it is
     * thrown: C1 0x41c638 in the hold and 0x41ceb2 in init/prepare. */
    unsigned char offhand_cancel;
    /* +0x560: the weapon never spends a round. C1 0x41e3cf skips the magazine
     * decrement and 0x41b94d the ammo test for it, and its clip registration
     * 0x41f3f0 gives it no clip pool entry (def+0x570 = -1). Of the shipped
     * definitions only minigun_zm (the zombies Death Machine) sets it. */
    unsigned char unlimited_ammo;
    unsigned char silenced; /* C1 muzzle tag selector 548f1d: source +bda. */
    /* Definition bytes C1 exposes to script: a builtin loads the registered
     * definition and pushes the byte. +0xbf3/+0xbf4/+0xbf5 have no other
     * reader in C1's .text; +0xbe6 is also read by cgame (0x477433,
     * 0x483a4f), which the server does not run. The weaponattach assets
     * that set them (all write 1, except thermal_scope's 0) name their
     * marketplace items:
     *   +0xbe6 thermal_*   (C1 0x542010, IW4's weaponhasthermalscope slot)
     *   +0xbf3 hpbt_base/heiap_barrett/slap_base, item mag_hpbt (0x5583d0)
     *   +0xbf4 gps_base, items gps_default and sra_tracker (0x542140)
     *   +0xbf5 lock_base, item sra_idlock (0x5421d0)
     * Composed definitions carry their attachments' overrides, so these
     * answer for the exact composed weapon, as C1's do. */
    unsigned char thermal_scope, hpbt, gps, id_lock;
    /* +0x944..+0x94c: the scope's zoom FOV per variable-zoom level. C1
     * PM_UpdateVariableZoom 0x418480 steps ps+0x5c4 through the levels whose
     * FOV is non-zero (0x4184e2) and the view reads the chosen one at 0x4716ea;
     * a weapon with only +0x944 set has one level and no variable zoom. */
    float zoom_fov[3];
    const char *partner_weapon_name; /* Source +b88; separate from the +b78 alternate. */
    const char *script_mods; /* Source +a24, returned by C1 GetWeaponScriptMods. Not IW3 szScript. */
    const XModel *source_models[11]; /* All leading references, including unbound roles. */
    const char *source_strings[4]; /* Retain leading names with original source order. */
    codol_native_weapon_graphs_t graphs;
    codol_weapon_animations_t animations;
    const struct XAnimParts *animation_parts[144]; /* Borrowed archive-owned native payloads. */
    codol_weapon_hide_tag_handles_t hide_tags;
} codol_native_weapon_core_t;
/* A composed definition already identifies one CoDOL camo/model recipe row.
 * Bind that row's real models into every retained variant slot so legacy
 * giveWeapon variant selection cannot reject or substitute the base weapon's
 * serialized art. Both models are required; failure preserves the core. */
int CODOL_BindNativeComposedWeaponModels(const XModel *world,const XModel *view,
    codol_native_weapon_core_t *);
/* Exact definition identity, including archive generations retained by live
 * native users. Returned tags borrow that definition's lifetime. */
int CODOL_GetNativeWeaponHideTags(const struct WeaponDef *,const codol_weapon_hide_tag_handles_t **);
int CODOL_GetNativeWeaponSilenced(const struct WeaponDef *,int *);
/* Source +a24 of this exact definition: C1's script-mod string, after any
 * composed attachment overrides (silencer_kcam sets "nokillcam"). Never
 * null on success; empty when the weapon carries none. 0 not a CoDOL core. */
int CODOL_GetNativeWeaponScriptMods(const struct WeaponDef *,const char **);
/* One of the script-only definition bytes of this exact definition (composed
 * attachment overrides applied). 0 when the definition is not a CoDOL core. */
typedef enum {
    CODOL_WEAPON_SCRIPT_FLAG_THERMAL_SCOPE, /* +0xbe6 */
    CODOL_WEAPON_SCRIPT_FLAG_HPBT,          /* +0xbf3 */
    CODOL_WEAPON_SCRIPT_FLAG_GPS,           /* +0xbf4 */
    CODOL_WEAPON_SCRIPT_FLAG_ID_LOCK        /* +0xbf5 */
} codol_weapon_script_flag_t;
int CODOL_GetNativeWeaponScriptFlag(const struct WeaponDef *,codol_weapon_script_flag_t,int *);
/* Assemble the verified weapon core in one transaction. All supplied views
 * must belong to source; models, names and acquired tag references are borrowed
 * and must outlive the core. Graph arrays are owned. Retains all 144 animation
 * slots and 32 tags separately without truncating them into IW3 arrays.
 * animation_parts stays unbound here; the engine loader resolves those assets.
 * out must be zero/prior. Failure preserves it; success replaces it.
 * Unconverted fields remain zero. The default-weapon startup provider uses
 * this record; it does not yet represent complete gameplay weapon support. */
int CODOL_BuildNativeWeaponCore(const codol_mounted_weapon_t *,const XModel *const [11],
    const codol_weapon_animations_t *,const codol_weapon_ammo_names_t *,
    const codol_weapon_tail_t *,const codol_weapon_hide_tag_handles_t *,codol_native_weapon_core_t *);
void CODOL_FreeNativeWeaponCore(codol_native_weapon_core_t *);
/* Image variant: validates model/tag presence against resolved overridden
 * slots rather than the untouched serialized references. Same borrowed
 * dependency/owned graph and atomic replacement rules as the stock builder. */
int CODOL_BuildNativeWeaponCoreFromImage(const codol_weapon_source_image_t *,
    const XModel *const [11],const codol_weapon_hide_tag_handles_t *,codol_native_weapon_core_t *);
/* Complete, strictly validated empty 'none' asset, matching retained
 * BG_LoadDefaultWeaponDef_LoadObj semantics. Rejects nonempty dependencies or
 * unconverted nonzero fields. Same ownership/atomicity rules as core builder. */
int CODOL_BuildNativeNullWeapon(const codol_mounted_weapon_t *,const codol_weapon_animations_t *,
    const codol_weapon_ammo_names_t *,const codol_weapon_tail_t *,codol_native_weapon_core_t *);
/* Resolve mounted views and engine model/tag/animation providers, then build the core.
 * The tail's +7b0 projectile model also resolves to an archive-owned native
 * XModel; null clears it, malformed or unresolved references reject the load.
 * Every nonempty source animation name must resolve to native XAnimParts;
 * null/empty slots remain null and source slot order is preserved.
 * Leading view/world muzzle flashes resolve to archive-owned native FX;
 * null slots clear the pointers and unresolved/malformed references reject.
 * The four +440..+44c brass effects also bind native view/world ordinary
 * and last-shot FX, with matching source metadata required for every slot.
 * 1 ready, 0 absent weapon, -1 invalid/unresolved dependency. Atomic output;
 * zero/prior ownership and incomplete-record restrictions above still apply. */
int CODOL_LoadEngineWeaponCore(const char *,codol_native_weapon_core_t *);
/* Source line in codol_weapon_loader.c where the last core build failed; 0 if none. */
int CODOL_EngineWeaponCoreFailureLine(void);
/* codol_weapon_native.c: first failing line of the last core build, 0 if none. */
int CODOL_NativeWeaponCoreFailureLine(void);
void CODOL_ResetNativeWeaponCoreFailure(void);
/* Load adjusted dependencies and acquire owned tag refs before publication.
 * All three outputs must be zero/prior results of this API. They are replaced
 * together on success and preserved on failure. Keep image and sound bindings
 * alive at stable addresses until the core is freed, then release owned tags.
 * Models/effects/animations/aliases borrow mounted archive lifetime. */
int CODOL_LoadEngineWeaponCoreFromImage(const codol_weapon_source_image_t *,
    codol_weapon_hide_tag_handles_t *,codol_weapon_sound_bindings_t *,codol_native_weapon_core_t *);
/* Stock registry replay from resolved mounted names and +bbc/+560 flags.
 * Custom definitions must use RegisterWeaponKeys with their resolved base. */
int CODOL_RegisterMountedWeaponKeys(codol_weapon_registry_t *,unsigned,const char *);
/* Archive-owned startup definition. The callback composes engine dependencies;
 * only defaultweapon_mp is accepted. Failed construction is not cached. */
int CODOL_LoadMountedDefaultWeapon(const char *,
    int (*build)(const char *,codol_native_weapon_core_t *),const struct WeaponDef **);
/* Archive-owned stock definitions through the native core builder. Cache by
 * winning asset identity, preserve old pointers across mounted overrides, and
 * do not cache failures. Core completeness restrictions still apply. */
int CODOL_LoadMountedNativeWeapon(const char *,
    int (*build)(const char *,codol_native_weapon_core_t *),const struct WeaponDef **);
/* Query metadata by the exact registered definition, including retained archive
 * generations. Unknown pointers fail without changing the output. */
int CODOL_GetNativeWeaponInheritsPerks(const struct WeaponDef *,int *);
int CODOL_GetNativeWeaponLockWarningGate(const struct WeaponDef *,int *);
/* Resolver for CODOL_SetWeaponDualWieldResolver in codol_weapon_state.h. */
int CODOL_GetNativeWeaponDualWield(const struct WeaponDef *,int *);
/* C1 weapType word +0x340 == 3 (riot shield); feeds CODOL_WEAP_RIOTSHIELD_NEXT. */
int CODOL_GetNativeWeaponRiotShield(const struct WeaponDef *,int *);
/* C1 +0xbca, consumed by the native ADS-fraction producer. */
int CODOL_GetNativeWeaponAdsReload(const struct WeaponDef *,int *);
int CODOL_GetNativeWeaponReloadData(const struct WeaponDef *,int *dual_mag,
    codol_weapon_timing_extensions_t *);
/* One of the 144 retained source animation-name slots (3 banks of 48, source
 * +0x7c + 4*slot), after attachment overrides for a composed definition.
 * NULL or "" means the client registers that slot as idle (C1 0x47c0df). */
int CODOL_GetNativeWeaponAnimationName(const struct WeaponDef *,unsigned slot,const char **);
/* codol_weapon_timing_extensions_t.rechamber_variant, which C1 selects
 * instead of iRechamberTime while the akimbo flag is set (0x4190ba).
 * Resolver for CODOL_SetWeaponRechamberDualWieldResolver. */
int CODOL_GetNativeWeaponRechamberDualWield(const struct WeaponDef *,int *);
/* Spin-up charge and decay durations, for CODOL_SetWeaponSpinUpResolver. */
int CODOL_GetNativeWeaponSpinUp(const struct WeaponDef *,int *up_ms,int *down_ms);
/* The two grenade-type booleans, for the resolvers in codol_weapon_state.h. */
int CODOL_GetNativeWeaponDetonateTrigger(const struct WeaponDef *,int *);
int CODOL_GetNativeWeaponClass(const struct WeaponDef *,unsigned *);
int CODOL_GetNativeWeaponHoldPin(const struct WeaponDef *,int *);
int CODOL_GetNativeWeaponOffhandCancel(const struct WeaponDef *,int *);
int CODOL_GetNativeWeaponUnlimitedAmmo(const struct WeaponDef *,int *);
/* The three variable-zoom FOVs (source +0x944..+0x94c) of a registered or
 * composed definition, attachment overrides included. */
int CODOL_GetNativeWeaponZoomFov(const struct WeaponDef *,float out[3]);
/* WeaponDef +0xbe5, for CODOL_SetWeaponRequiresGroundResolver. */
int CODOL_GetNativeWeaponRequiresGround(const struct WeaponDef *,int *);
#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
