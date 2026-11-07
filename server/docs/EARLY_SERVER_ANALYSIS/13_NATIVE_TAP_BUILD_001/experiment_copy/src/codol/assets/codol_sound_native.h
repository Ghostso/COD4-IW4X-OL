/* Native CoDOL sound conversion. SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_SOUND_NATIVE_H
#define CODOL_SOUND_NATIVE_H
#include "codol_sound.h"
#include "q_shared.h"
#include "xassets/sounds.h"
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif
struct WeaponDef;
/* Owned native alias list. Storage holds the list, its aliases, sound files,
 * loaded sounds, curves, speaker maps and every copied string; only loaded
 * sample payloads borrow the archive. Converted fields, all measured in C1:
 *   source +0/+8/+12 names (0x738638 secondary lookup, 0x73d0c6 chain check),
 *   +4 subtitle by loader position, +20 sound file (0x73e22c, 0x7384e0),
 *   +24 sequence and +72 probability (weighted picker 0x61ea30),
 *   +28/+32 volume and +36/+40 pitch (randomizer 0x7380a0),
 *   +44/+48 distances (range test 0x738540), +84 start delay (0x7388a8),
 *   +88 falloff curve (0x7375b0), +104 speaker map.
 * Data without a measured IW3 counterpart is converted into the appended
 * CoDOL block instead of being renamed: the +56 flag word (C1 packs its
 * channel index in bits 9..14 and uses bits 0/3/4/6/7/8; SND_AliasLooping and
 * SND_AliasChannel decode the measured parts), the +60 priority byte, the
 * fifth name and the eight unmeasured scalars, each named for its record
 * offset. IW3's own flags word, slavePercentage, lfePercentage,
 * centerPercentage and the envelope trio stay zero because no measurement ties
 * a CoDOL word to them. Curves keep all sixteen CoDOL knots.
 * No playback path is claimed or exercised. out is zero/prior; failure
 * preserves it and success replaces it. */
typedef struct {
    snd_alias_list_t *list;
    void *storage;
    size_t size;
    unsigned aliases,loaded_sounds,streams,curves,speaker_maps;
} codol_native_sound_t;
int CODOL_BuildNativeSoundAliasList(const codol_sound_alias_list_t *,codol_native_sound_t *);
void CODOL_FreeNativeSound(codol_native_sound_t *);
/* Mounted source view of a type 11 asset, newest named definition first.
 * Cached by the defining archive and borrowed until full unmount.
 * 1 decoded, 0 absent, -1 invalid; output unchanged unless decoded. */
int CODOL_LoadMountedSoundAliasList(const char *,const codol_sound_alias_list_t **);
/* Archive-owned native alias list for the winning definition. Same caching and
 * lifetime rules as the native effect cache; failures are not cached and no
 * asset is published in the engine database. 1 ready, 0 absent, -1 invalid. */
int CODOL_LoadEngineNativeSound(const char *,const snd_alias_list_t **);
/* Com_FindSoundAlias adapter: the archive-owned list for name, or NULL when no
 * mounted archive defines it or its definition is malformed. The list is
 * complete or absent, never partially converted, and stays valid until unmount. */
snd_alias_list_t *CODOL_FindEngineSoundAlias(const char *);
/* Every mounted sound alias definition, newest archive first, link references
 * excluded. Returning zero from the callback stops the walk. A name can repeat
 * across archives; CODOL_LoadEngineNativeSound resolves the winning definition.
 * Names borrow archive lifetime. Returns the number of visited definitions,
 * or -1 if a definition cannot be named. */
int CODOL_EnumerateMountedSoundAliases(int (*)(void *,const char *),void *);
/* Every mounted LocalizeEntry (asset 27) as (name, value), newest archive
 * first. A name can repeat across archives; the first visit is the text C1
 * shows (it keeps the first zone that links a name: patch_X loads before X),
 * which codol_dumplocalize was checked against C1's live menu text. Strings
 * are the raw GBK bytes and borrow archive lifetime. Returning zero from the
 * callback stops the walk; returns the number of visited entries or -1. */
int CODOL_EnumerateMountedLocalize(int (*)(void *,const char *,const char *),void *);
enum { CODOL_WEAPON_SOUND_SLOTS=53, CODOL_WEAPON_SOUND_SURFACES=31, CODOL_WEAPON_SOUND_TAIL=24 };
typedef struct {
    /* Source name slots +0x364.., the two 31-entry surface arrays at +0x438
     * and +0x43c, and the tail sound records in loader order. */
    snd_alias_list_t *names[CODOL_WEAPON_SOUND_SLOTS];
    snd_alias_list_t *arrays[2][CODOL_WEAPON_SOUND_SURFACES];
    snd_alias_list_t *tail[CODOL_WEAPON_SOUND_TAIL];
    unsigned tail_offsets[CODOL_WEAPON_SOUND_TAIL],tail_count;
    unsigned requested,resolved,absent;
} codol_weapon_sound_bindings_t;
/* Resolve the supplied dependency views without the weapon-name cache. This
 * lets each composed weapon retain its own adjusted bindings. Aliases borrow
 * archive lifetime; the output itself contains no allocations to release.
 * Keep the bindings at a stable address after ApplyNativeWeaponSounds because
 * WeaponDef.bounceSound points into arrays[0]. 1 ready, -1 invalid; failure
 * preserves out. Missing aliases have the same policy as the cached loader. */
int CODOL_BuildNativeWeaponSoundBindings(const codol_weapon_sounds_t *,
    const codol_weapon_tail_t *,codol_weapon_sound_bindings_t *);
/* Resolve every sound name a mounted weapon carries to a native alias list.
 * Both resolved views must belong to the named weapon; the caller keeps them.
 * Names that no mounted archive defines stay null and are counted in absent,
 * because CoDOL ships alias assets in sound zones a dedicated server need not
 * mount; a malformed or unconvertible definition fails the whole call.
 * Cached per weapon name until CODOL_ResetNativeWeaponSounds; the returned
 * arrays keep stable addresses so bounceSound can point at them.
 * 1 ready, -1 invalid. Output unchanged unless ready. */
int CODOL_LoadEngineWeaponSounds(const char *,const codol_weapon_sounds_t *,
    const codol_weapon_tail_t *,const codol_weapon_sound_bindings_t **);
/* Source line in codol_sound_native.c of the last failure; 0 if none. */
int CODOL_NativeSoundFailureLine(void);
const char *CODOL_NativeSoundFailureName(void);
/* Writes all 45 retained sound fields. CoDOL's 53 name slots are IW3's 45 in
 * the same order plus three interleaved extras (9 akimbo fire, 12/13 fire-loop
 * end) and five appended ones (48..52); slot n therefore maps to IW3 field n
 * for n<9, n-1 for 10..11, n-3 for 14..47. The +0x438 surface array becomes
 * bounceSound and tail records +0x7c0/+0x7c4/+0x8f0 become the projectile
 * explosion, dud and ignition sounds. Roles rest on C1 consumers (script
 * pickup readers 0x558d90/0x558df0, CG_FireWeapon 0x481d60, the fire-loop
 * driver 0x484f20, G_SpawnTurret 0x57eb1a..0x57eb85 against the retained
 * +0x178..+0x184 reads, the note-track dispatcher 0x445070 and the surface
 * lookup 0x482a38) and on which shipped weapons populate each slot.
 * The eight CoDOL-only slots and the +0x43c surface array stay in the bindings
 * and are not written. Fields whose bindings are null are cleared.
 * Failure preserves the output. */
int CODOL_ApplyNativeWeaponSounds(const codol_weapon_sound_bindings_t *,struct WeaponDef *);
/* Releases the weapon binding cache. The archive registry calls this from
 * CODOL_UnmountArchives, before the native alias lists themselves are freed. */
void CODOL_ResetNativeWeaponSounds(void);
#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
