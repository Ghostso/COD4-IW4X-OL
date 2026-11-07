/* CoDOL configstring namespace, separate from assembly-visible IW3 storage. */
#ifndef CODOL_CONFIGSTRINGS_H
#define CODOL_CONFIGSTRINGS_H
#include "codol_msg.h"
#pragma pack(push, 8)
#define CODOL_MAX_CONFIGSTRINGS 6519
/* C1 SV_SetConfigstring5d30e0 rejects strlen(value)+1 > 0x3f8.
 * Dynamic updates are one d command; C1 has no IW3 x/y/z reassembly. */
#define CODOL_CONFIGSTRING_VALUE_CHARS 1015
/* C1's rebuilt pool includes its reserved empty byte, then each nonempty
 * effective value and its NUL (4875c8..487660). */
#define CODOL_CONFIGSTRING_POOL_BYTES 131072
#define CODOL_MAX_GAME_CLIENTS 18 /* C1 dvar 2485 domain, not table capacity. */
#define CODOL_CS_SERVER_ID 3
/* C1 team scores. The reliable commands C (4699d5) and D (469a12) write
 * cg+0xBEB20 and cg+0xBEB24 live; these two configstrings hold the same
 * values for the win/lose banner (550960) and for a late joiner's gamestate.
 * CS 5 is teamScores[TEAM_RED] (axis), CS 6 is teamScores[TEAM_BLUE]
 * (allies), matching the C/D pairing in PlayerCmd_UpdateScores. */
#define CODOL_CS_TEAM_SCORE1 5
#define CODOL_CS_TEAM_SCORE2 6
#define CODOL_CS_FOG 13
#define CODOL_CS_AMBIENT 1300
#define CODOL_CS_AC130_AMBIENT 1301
#define CODOL_CS_NORTHYAW 1302
#define CODOL_CS_MATCH_END_TIME 15
#define CODOL_CS_SLOWMOTION 6132 /* C1 54a5d2; four-field parser466eb0. */
#define CODOL_CS_MAP_CENTER 16
#define CODOL_CS_MINIMAP 1303
#define CODOL_CS_THERMAL_BODY_MATERIAL 1304 /* C1 4675bf ->43de20. */
#define CODOL_CS_WEAPONS 5362
#define CODOL_WEAPON_SLOTS 700 /* C1 CG_Init validates slots 1..699. */
#define CODOL_CS_MODELS 1315
#define CODOL_MODEL_SLOTS 2048
#define CODOL_CS_TAGS 5299
#define CODOL_CS_SOUNDS 3395
#define CODOL_CS_EFFECTS 3651
#define CODOL_EFFECT_SLOTS 320 /* Sentinel zero, effect IDs 1..319. */
#define CODOL_BYTE_EFFECT_SLOTS 256 /* ET_FX/ET_LOOP_FX carry an 8-bit selector. */
#define CODOL_CS_TAGGED_EFFECTS 3971
#define CODOL_TAGGED_EFFECT_SLOTS 256
#define CODOL_CS_TEAM_THERMAL 6100
#define CODOL_CS_MINIMAP_ICONS 6085 /* C1 precacheminimapicon54ff80:17c5..17d3. */
#define CODOL_CS_STATUS_ICONS 6062 /* C1 dispatcher467534:17ae..17b5. */
#define CODOL_CS_HEAD_ICONS 6070 /* C1 precache head54fdb0:17b6..17c4. */
#define CODOL_MINIMAP_ICON_SLOTS 15
#define CODOL_TEAM_THERMAL_SLOTS 32 /* All slots, including zero, are usable. */
#define CODOL_CS_MATERIALS 4275
#define CODOL_CS_MENUS 4243
#define CODOL_CS_SHELLSHOCKS 4227
#define CODOL_SHELLSHOCK_SLOTS 16
#define CODOL_MENU_SLOTS 32
#define CODOL_HUD_MATERIAL_SLOTS 256
#define CODOL_CS_LOCALIZEDSTRINGS 680
#define CODOL_CS_HINTSTRINGS 584 /* C1 45629c: offsets base6d0d130 + 584*4. */
/* C1 CS 584..679 (its G_GetHintStringIndex 0x53c4d0 compares against 0x60,
 * G_RegisterWeapon 0x529add passes 0x60). Slots 0..31 are the retained
 * 0x115 block (it ends at CS_LOCALIZEDSTRINGS); 32..95 are CoDOL-owned. */
#define CODOL_HINTSTRING_SLOTS 96
#define CODOL_HINTSTRING_RETAINED 32
#define CODOL_LOCALIZED_SLOTS 600
#define CODOL_SOUND_SLOTS 257 /* Sentinel zero, playable indices 1..256. */
#define CODOL_TAG_SLOTS 64
#define CODOL_CS_PLAYERNAMES 1280
#define CODOL_PLAYERNAME_SLOTS 20 /* Followed by ambience at1300/1301. */
/* C1 467560 routes 1305..1310 into the vision applier 466b80 with the type
 * index; its global builtins publish there (5504fd naked, 5505cd thermal,
 * 55067d pain). IW4 uses 45c..460 and IW3 used 824/825 for naked/night. */
#define CODOL_CS_VISIONSET 1305
#define CODOL_VISIONSET_SLOTS 6 /* Scripts drive the first five. */
#define CODOL_CS_WEAPON_COUNT 6517
#define CODOL_CS_DVAR_NAMES 24
#define CODOL_CS_DVAR_VALUES 224
#define CODOL_MAX_REPLICATED_DVARS 200

typedef struct {
    char *values[CODOL_MAX_CONFIGSTRINGS];
    size_t bytes;
    unsigned count;
} codol_configstrings_t;

/* Zero initialize before use. NULL/unset differs from explicitly published empty:
 * an empty value clears a client constant; unset leaves it inherited. */
void CODOL_ClearConfigstrings(codol_configstrings_t *state);
int CODOL_SetConfigstring(codol_configstrings_t *state, unsigned index, const char *value);
/* Validate the client-visible merged pool. Empty overrides clear inherited
 * values; NULL overrides inherit. bytes is optional and unchanged on failure. */
int CODOL_ConfigstringPoolSize(const codol_configstrings_t *overrides,
    const codol_configstrings_t *inherited, size_t *bytes);
/* Replace the whole name block atomically. NULL entries and unused slots clear
 * inherited names; names are bounded to the client's 63-byte storage. */
int CODOL_SetPlayerNames(codol_configstrings_t *state, unsigned count, const char *const *names);
/* Produce a single reliable-command token; NULL means a disconnected slot. */
void CODOL_PlayerNameToken(char output[64], const char *name);
const char *CODOL_GetConfigstring(const codol_configstrings_t *state, unsigned index);
/* An explicit override, including "", takes precedence over the inherited
 * fastfile value. This is the value C1 has after a gamestate. */
const char *CODOL_GetEffectiveConfigstring(const codol_configstrings_t *overrides,
    const codol_configstrings_t *inherited, unsigned index);
/* Build a separate inherited bank from (decimal index,value) rows. Atomic
 * replacement; duplicate/out-of-range indices are invalid. Do not serialize
 * this bank as overrides: the client already owns these constant values. */
int CODOL_ImportConstantConfigstrings(codol_configstrings_t *,size_t rows,const char *const *cells);
/* Reuse effective values, then allocate only slots not occupied by constants.
 * An inherited match creates no override. Empty values return sentinel zero.
 * Keep the inherited bank immutable for the map lifetime. */
int CODOL_RegisterHudMaterial(codol_configstrings_t *overrides,const codol_configstrings_t *inherited,const char *);
int CODOL_RegisterLocalizedString(codol_configstrings_t *overrides,const codol_configstrings_t *inherited,const char *);
int CODOL_RegisterEffectName(codol_configstrings_t *overrides,const codol_configstrings_t *inherited,const char *);
/* A high inherited match may be duplicated into a free low slot; never truncate. */
int CODOL_RegisterByteEffectName(codol_configstrings_t *overrides,const codol_configstrings_t *inherited,const char *);
int CODOL_RegisterTaggedEffect(codol_configstrings_t *overrides,const codol_configstrings_t *inherited,unsigned effect,const char *tag);
/* Publish an already resolved asset name, reusing its existing slot. Empty
 * names return the reserved zero slot; invalid names/full ranges return -1.
 * These do not load or validate the existence of an asset. Slots remain stable
 * until the bank is reset; callers must not overwrite registered entries. */
int CODOL_RegisterModelName(codol_configstrings_t *state, const char *name);
int CODOL_RegisterTagName(codol_configstrings_t *state, const char *name);
int CODOL_RegisterInheritedModelName(codol_configstrings_t *state,
    const codol_configstrings_t *inherited, const char *name);
int CODOL_RegisterInheritedTagName(codol_configstrings_t *state,
    const codol_configstrings_t *inherited, const char *name);
/* Resolve a retained effect by name into the CoDOL effect bank and register
 * its thermal attachment. Returns thermal slot 0..31, or -1 without mutation.
 * The caller must enforce precache timing and validate the loaded effect. */
int CODOL_RegisterTeamThermal(codol_configstrings_t *overrides,
    const codol_configstrings_t *inherited,const char *effect,const char *tag);
/* Measured checksums of the unmodified 1.1.1.13 constant tables, not fastfile
 * checksums. Custom tables require an explicit checksum in WriteGamestate. */
int CODOL_ConstConfigChecksum(const char *zone_type, uint32_t *checksum);
/* Caller supplies names contiguously. Replaces the complete replicated block. */
int CODOL_SetReplicatedDvars(codol_configstrings_t *state, unsigned count,
                            const char *const *names, const char *const *values);
/* Both writers return zero on overflow; failed bytes must never be sent. */
int CODOL_WriteConfigstrings(codol_msg_t *msg, const codol_configstrings_t *state);
int CODOL_WriteGamestate(codol_msg_t *msg, const codol_configstrings_t *state,
                         const char *map, const char *zone_type, uint32_t const_crc,
                         uint32_t command_sequence, uint32_t client_number,
                         uint32_t checksum_feed);
#pragma pack(pop)
#endif
