/* Owned CoDOL archive images. SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_ASSETS_H
#define CODOL_ASSETS_H
#include <stddef.h>
#include <stdint.h>
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif
#define CODOL_ASSET_MAP_ENTS 19
#define CODOL_ASSET_RAWFILE 36
#define CODOL_ASSET_STRINGTABLE 37
/* IW4 asset type 42. The nine coop zones ship exactly one each and no world
 * asset at all, so it is the only place their Spec Ops entities exist. NOTE
 * this is the CoDOL/IW4 zone numbering that codol_load_blocks.c dispatches on,
 * NOT the IW3 XAssetType enum in src/xassets.h that g_assetNames, g_poolSize
 * and DB_XAssetPool are indexed by -- the two disagree from index 1 onwards. */
#define CODOL_ASSET_ADDON_MAP_ENTS 42
#define CODOL_ASSET_LIMIT (512u * 1024u * 1024u)

typedef struct {
    uint8_t *data;
    size_t size, table_offset;
    uint32_t asset_count, string_count, block_size[8];
} codol_zone_t;

typedef struct {
    uint32_t type;
    const uint8_t *data;
    size_t size;
} codol_asset_t;

/* Open copies/owns the zone image. Failed opens leave the output untouched. */
int CODOL_OpenZoneImage(codol_zone_t *out, const void *data, size_t size);
int CODOL_OpenZoneFile(codol_zone_t *out, const char *path);
void CODOL_CloseZone(codol_zone_t *zone);
int CODOL_ZoneAsset(const codol_zone_t *zone, unsigned index, codol_asset_t *asset);
typedef struct {
    uint32_t reference;
    const char *text;
} codol_script_string_t;
/* Read the zone-local script-string index table. The returned array is owned
 * by the caller (free); text points into the owned zone until CloseZone.
 * Preserve null and unresolved references as NULL, with their original value;
 * neither is interchangeable with an explicitly empty inline string.
 * Failed reads leave out untouched. An empty pool succeeds with *out=NULL. */
int CODOL_ReadScriptStrings(const codol_zone_t *zone, codol_script_string_t **out);
typedef struct {
    uint32_t name_reference;
    const char *name;
    float origin[3];
    uint16_t trigger_index;
    uint8_t sun_index;
} codol_map_stage_t;
typedef struct {
    uint8_t *storage;
    const char *name, *text;
    uint32_t name_reference;
    size_t text_size, consumed;
    uint32_t model_count, hull_count, slab_count, stage_count;
    const uint8_t *models, *hulls, *slabs;
    codol_map_stage_t *stages;
} codol_map_entities_t;
/* Read a MapEnts header at an already resolved stream position. The 44-byte
 * header precedes optional inline name and entity text; text_size includes its
 * NUL. Also reads trigger models (8 bytes), hulls (32), slabs (20), and stages.
 * A pooled name stays NULL with its reference preserved. Owns copied strings;
 * failure leaves out untouched. This function does not scan collision blobs. */
int CODOL_ReadMapEntities(const void *data, size_t size, codol_map_entities_t *out);
/* Same record with a 36-byte header and no stages: IW4 asset type 42, the only
 * asset the nine coop zones ship. MEASURED 2026-09-20: name pointer +0 (inline
 * for all nine), entityString +4 (always 0xFFFFFFFF), numEntityChars +8, then
 * trigger model/hull/slab count+pointer pairs to +35, and for every one of the
 * nine the decoded length equals the asset extent exactly. */
int CODOL_ReadAddonMapEntities(const void *data, size_t size, codol_map_entities_t *out);
/* Compose an addon overlay onto a base map's MapEnts: base entity text first,
 * then the addon's minus its leading worldspawn, with every addon "?N" trigger
 * reference biased by the base trigger model count and the addon's trigger
 * models/hulls/slabs appended (and their first/start indices rebased) so one
 * contiguous array serves both halves. The addon must carry no stages. Owns
 * its own storage; out is freed and replaced only on success. */
int CODOL_MergeMapEntities(const codol_map_entities_t *base,
                           const codol_map_entities_t *addon,
                           codol_map_entities_t *out);
void CODOL_FreeMapEntities(codol_map_entities_t *entities);
typedef struct { float normal[3],distance; } codol_trigger_plane_t;
typedef struct {
    float mins[3],maxs[3];
    int32_t contents;
    unsigned plane_count;
    codol_trigger_plane_t *planes;
} codol_trigger_hull_t;
typedef struct {
    float mins[3],maxs[3];
    int32_t contents;
    unsigned hull_count;
    codol_trigger_hull_t *hulls;
} codol_trigger_model_t;
/* Decode one ?N trigger model into owned convex hulls. Each slab becomes two
 * outward planes; six axial planes retain each hull's box bounds. Coordinates
 * remain in the source trigger frame. Failure preserves out. No engine handle
 * is installed; this is geometry for native trigger collision integration. */
int CODOL_ReadTriggerModel(const codol_map_entities_t *,unsigned,codol_trigger_model_t *);
void CODOL_FreeTriggerModel(codol_trigger_model_t *);
/* Walk the measured collision stream to its inline MapEnts record. Does not
 * search for text or use map-specific offsets; output is untouched on failure.
 * Inline static XModels still require their own loader and are rejected. */
int CODOL_LocateCollisionMapEntities(const codol_asset_t *asset, size_t *offset);
int CODOL_ReadCollisionMapEntities(const codol_asset_t *asset, codol_map_entities_t *out);
enum codol_collision_section {
    CODOL_COLL_PLANES, CODOL_COLL_STATIC_MODELS, CODOL_COLL_MATERIALS,
    CODOL_COLL_BRUSH_SIDES, CODOL_COLL_BRUSH_EDGES, CODOL_COLL_NODES,
    CODOL_COLL_LEAVES, CODOL_COLL_LEAF_BRUSHES, CODOL_COLL_LEAF_BRUSH_NODES,
    CODOL_COLL_LEAF_SURFACES, CODOL_COLL_VERTICES, CODOL_COLL_TRIANGLES,
    CODOL_COLL_WALKABLE, CODOL_COLL_BORDERS, CODOL_COLL_PARTITIONS,
    CODOL_COLL_AABBS, CODOL_COLL_SUBMODELS, CODOL_COLL_BRUSHES,
    CODOL_COLL_BRUSH_BOUNDS, CODOL_COLL_BRUSH_CONTENTS, CODOL_COLL_STATIC_NODES,
    CODOL_COLL_SECTIONS
};
typedef struct {
    size_t offset; /* asset-relative; SIZE_MAX for externally pooled planes */
    uint32_t count, stride, reference;
} codol_collision_span_t;
typedef struct {
    codol_collision_span_t sections[CODOL_COLL_SECTIONS];
    size_t map_entities;
    uint32_t name_reference;
} codol_collision_layout_t;
/* Validated stream spans, not native pointers or relocated engine geometry.
 * Requires the source asset to remain alive. Failure leaves out untouched. */
int CODOL_ReadCollisionLayout(const codol_asset_t *asset, codol_collision_layout_t *out);
/* Returns inline name, or NULL for a deduplicated name requiring block fixups. */
const char *CODOL_RawFileName(const codol_asset_t *asset);
/* Caller frees the returned payload with free(). Always appends a sentinel NUL;
 * size excludes that sentinel, and compressed length must match exactly. */
int CODOL_ReadRawFile(const codol_asset_t *asset, uint8_t **out, size_t *size);
int CODOL_FindRawFile(const codol_zone_t *zone, const char *name,
                      uint8_t **out, size_t *size);
/* 1=loaded, 0=no matching inline name, -1=matching asset invalid/unreadable.
 * Outputs remain untouched unless loaded. Pooled names need relocation. */
int CODOL_FindRawFileStatus(const codol_zone_t *zone, const char *name,
                           uint8_t **out, size_t *size);
typedef struct {
    uint32_t reference, hash;
    /* NULL with reference 0 is an absent cell; NULL with a nonzero reference
     * needs relocation. Neither is an inline empty string. */
    const char *text;
} codol_table_cell_t;
typedef struct {
    uint8_t *storage;
    const char *name;
    uint32_t name_reference, values_reference, columns, rows, unresolved;
    codol_table_cell_t *cells;
} codol_stringtable_t;
/* Owned structural reader; inline strings are hash-checked. Pooled references
 * stay explicit until block relocation resolves them. No hash-based guessing. */
int CODOL_ReadStringTable(const codol_asset_t *asset, codol_stringtable_t *out);
uint32_t CODOL_StringTableHash(const char *text);
const char *CODOL_StringTableName(const codol_asset_t *asset);
void CODOL_FreeStringTable(codol_stringtable_t *table);
const codol_table_cell_t *CODOL_StringTableCell(const codol_stringtable_t *table,
                                               unsigned row, unsigned column);

/* IWff0100 signed-block and IWffu100 unsigned-stream containers. Key material
 * is read from the user's local C1.exe; no key is embedded or written to disk. */
int CODOL_OpenFastFile(codol_zone_t *out, const char *path, const char *client_exe);
/* Reason the last CODOL_OpenFastFile returned 0 (static text). */
const char *CODOL_FastFileOpenFailure(void);

/* Archive registry used by the native script loader. Mounts persist until
 * shutdown so returned data is never tied to a transient database buffer. */
int CODOL_MountArchive(const char *path, const char *client_exe);
/* Atomic set: input order is ascending override priority (last wins).
 * All archives are validated before publication. Failure leaves existing
 * mounts/caches untouched; failed_index identifies the rejected input. */
int CODOL_MountArchives(const char *const *paths, size_t count,
                        const char *client_exe, size_t *failed_index);
int CODOL_LoadScriptAsset(const char *name, uint8_t **out, size_t *size);
int CODOL_LoadScriptAssetStatus(const char *name, uint8_t **out, size_t *size);
/* Layout consumed by retained IW3 StringTable routines; strings/pointers live
 * until UnmountArchives. 1=ready, 0=not found, -1=present but not resolvable. */
typedef struct {
    const char *name;
    int columnCount, rowCount;
    const char **values;
} codol_engine_table_t;
int CODOL_LoadEngineStringTable(const char *name, const codol_engine_table_t **out);
int CODOL_ReadCSVStringTable(const char *data,size_t size,codol_stringtable_t *out);
int CODOL_LoadReferenceStringTable(const char *root,const char *name,const codol_engine_table_t **out);
/* Retained IW3 RawFile layout. Decoded bytes may contain NULs; len is exact,
 * with an additional sentinel. Cache ownership/lifetime matches tables. */
typedef struct {
    const char *name;
    int len;
    const char *buffer;
} codol_engine_rawfile_t;
int CODOL_LoadEngineRawFile(const char *name, const codol_engine_rawfile_t **out);
/* Attaches the lobby-served secure profile for a connecting client (codol_profilePath, userinfo xuid). */
int CODOL_AutoBindClientSecureProfile(unsigned client,const char *userinfo);
struct ComWorld;
/* Owned cached world/lights/strings, retained until full unmount. 1/0/-1 for
 * ready/absent/invalid; output unchanged on failure. No global publication. */
int CODOL_LoadEngineCommonWorld(const char *,const struct ComWorld **);
/* Replayed serialized weapon view, not an IW3 WeaponDef. The four leading
 * string references are resolved; all other pointer fields remain serialized.
 * Borrowed until full unmount, including retired groups. 1/0/-1 status; output
 * unchanged on failure. Never publish asset.data as a native weapon. */
typedef struct {
    codol_asset_t asset;
    const char *strings[4];
    size_t dependency_offset; /* First inline model after leading strings. */
} codol_mounted_weapon_t;
int CODOL_LoadMountedWeapon(const char *,codol_mounted_weapon_t *);
struct WeaponDef;
/* Complete native 'none' definition, archive-owned through full unmount.
 * Other names/absent root return 0; malformed none returns -1. Atomic output. */
int CODOL_LoadMountedNullWeapon(const char *,const struct WeaponDef **);
typedef struct { const char *names[32]; } codol_weapon_hide_tags_t;
/* Resolve source +0x3c's 32 script-string indices using the defining archive.
 * Zero is absent. Preserve all slots, including after gaps, for composition.
 * Names borrow archive/retired-group lifetime; no native handles are acquired.
 * 1=ready, 0=absent weapon, -1=invalid; output is unchanged on failure. */
int CODOL_LoadMountedWeaponHideTags(const char *,codol_weapon_hide_tags_t *);
typedef struct { const char *name; codol_asset_t asset; } codol_weapon_model_t;
/* Resolves one of the eleven leading model slots (source +0x10..+0x38),
 * including inline definitions, pooled aliases and newest named overrides.
 * 1=ready, 0=null slot/absent weapon, -1=invalid; output unchanged unless ready.
 * These are source slots; their native gun/hand/world roles need separate mapping. */
int CODOL_LoadMountedWeaponModel(const char *,unsigned,codol_weapon_model_t *);
typedef struct {
    const char *names[144];
    size_t dependency_offset; /* After names, before inline flash effects. */
} codol_weapon_animations_t;
/* Resolves the complete serialized animation-name block after inline models.
 * Borrowed until full unmount. Preserves source slot order and null/empty names;
 * it does not map 144 source slots onto IW3's 33 animation slots or load XAnims.
 * 1=ready, 0=absent weapon, -1=invalid; failure leaves out unchanged. */
int CODOL_LoadMountedWeaponAnimations(const char *,codol_weapon_animations_t *);
typedef struct {
    const char *names[2];
    codol_asset_t assets[2];
    size_t dependency_offset; /* After leading effects, before sound names. */
} codol_weapon_effects_t;
/* Resolves source +0x35c/+0x360, including inline/pooled FX and named overrides.
 * Null slots stay null. Borrowed until full unmount. Source views, not native FX.
 * 1=ready, 0=absent weapon, -1=invalid; output unchanged unless ready. */
int CODOL_LoadMountedWeaponEffects(const char *,codol_weapon_effects_t *);
typedef struct {
    const char *names[53];
    const char *arrays[2][31];
    size_t dependency_offset; /* After both sound arrays, before further FX. */
} codol_weapon_sounds_t;
/* Resolves indirect sound-name slots +0x364..+0x434 and arrays +0x438/+0x43c.
 * Borrowed source names,
 * not native sound aliases. 1/0/-1; failed calls preserve the whole output. */
int CODOL_LoadMountedWeaponSounds(const char *,codol_weapon_sounds_t *);
typedef struct {
    const char *ammo,*clip,*shared_cap;
    size_t dependency_offset;
} codol_weapon_ammo_names_t;
/* Traverses intervening FX/materials and resolves +0x564/+0x56c/+0x57c.
 * Borrowed until full unmount; 1/0/-1, failure preserves out. No registration. */
int CODOL_LoadMountedWeaponAmmoNames(const char *,codol_weapon_ammo_names_t *);
enum { CODOL_WEAPON_DEP_STRING, CODOL_WEAPON_DEP_SOUND, CODOL_WEAPON_DEP_ASSET, CODOL_WEAPON_DEP_POINTS };
typedef struct {
    unsigned offset,kind;
    const char *name;
    codol_asset_t asset;
    const uint8_t *points; /* Serialized little-endian float pairs. */
    unsigned point_count;
} codol_weapon_dependency_t;
typedef struct {
    codol_weapon_dependency_t entries[14]; /* Four FX, then ten materials. */
    size_t dependency_offset;
} codol_weapon_visuals_t;
/* Resolves +0x440..+0x450 and the intervening material groups through +0x550.
 * Original offsets and null slots are retained. Named overrides apply after
 * advancing over inline source data. Borrowed lifetime; atomic 1/0/-1. */
int CODOL_LoadMountedWeaponVisuals(const char *,codol_weapon_visuals_t *);
typedef struct {
    codol_weapon_dependency_t entries[64];
    unsigned count;
    size_t dependency_offset;
} codol_weapon_tail_t;
/* Resolves the remaining dependencies after ammo names in loader order.
 * Includes null slots; offset identifies the original header field. Named
 * assets use the winning mounted definition. Borrowed through retired archive
 * lifetime; 1/0/-1, atomic output, exact final source extent required. */
int CODOL_LoadMountedWeaponTail(const char *,codol_weapon_tail_t *);
typedef struct {
    codol_asset_t asset;
    const char *name;       /* Borrowed archive string. */
    const uint8_t *entries; /* count serialized {u32 offset,u32 type,u32 value}. */
    uint32_t count;
    const char **texts;     /* Owned array; borrowed strings, null where absent. */
} codol_mounted_weapon_attachment_t;
/* Type 43 weaponattach definition in C1 loader order (0x4c3dd0, 0x4c3d00):
 * the twelve-byte header, its name, count twelve-byte entries, then one string
 * per entry whose kind carries one. Entry values stay serialized and are never
 * native pointers; strings borrow archive lifetime through retired groups and
 * the texts array is owned by the caller. Requires the exact source extent.
 * 1/0/-1, atomic output; the overrides themselves are applied elsewhere. */
int CODOL_LoadMountedWeaponAttachment(const char *,codol_mounted_weapon_attachment_t *);
void CODOL_FreeMountedWeaponAttachment(codol_mounted_weapon_attachment_t *);
typedef struct {
    const uint8_t *header,*metadata,*indices,*frames;
    unsigned count,frame_stride;
} codol_xanim_track_t;
typedef struct {
    codol_asset_t asset;
    const char *name;
    const uint8_t *bone_indices,*notifies,*streams[6],*indices;
    unsigned bone_count,notify_count,index_width;
    uint32_t stream_counts[6],index_count;
    codol_xanim_track_t tracks[3]; /* translation, two-component quat, four-component quat */
    const codol_script_string_t *script_strings;
    unsigned script_string_count;
} codol_mounted_xanim_t;
/* Complete source traversal, not native XAnimParts. All views borrow archive
 * lifetime, including retired groups. Preserves all three source delta tracks.
 * 1=ready, 0=absent, -1=invalid; failed calls preserve out. */
int CODOL_LoadMountedXAnim(const char *,codol_mounted_xanim_t *);

typedef struct {
    codol_asset_t asset;
    const char *name,*prefix_strings[2]; /* Header8 andac; semantics not assumed. */
    codol_asset_t physics_preset; /* Zeroed for a null headerb0 dependency. */
    const char *physics_preset_name,*physics_profile;
    const char *string190,*string238;
    codol_asset_t weapon,materials[2];
    const char *weapon_name,*material_names[2];
    const char *sounds[47]; /* 1ac/1b0, fourteen sparse fields, then23c[31]. */
    size_t dependency_offset;
} codol_mounted_vehicle_t;
/* VehicleDef41 has a serialized0x314-byte header. Prefix strings occur at
 * header offsets0,8,ac, in that order (C1 replay4c4ec0). Header references
 * remain serialized, never native pointers. This is an archive-owned view;
 * Resolves the physics preset atb0 and profile string atb4; dependency_offset
 * follows the complete dependency stream. Resolves weapon/material definitions
 * and all47 sound-name slots in loader order. Native simulation is separate.
 * 1=found,0=absent,-1=invalid; failure preserves out. */
int CODOL_LoadMountedVehicle(const char *,codol_mounted_vehicle_t *);
typedef struct {
    uint16_t bones[255],notifies[255];
    unsigned bone_count,notify_count;
} codol_xanim_handles_t;
typedef unsigned (*codol_xanim_string_acquire_t)(void *,const char *);
typedef void (*codol_xanim_string_release_t)(void *,unsigned);
typedef struct { uint16_t tags[32]; } codol_weapon_hide_tag_handles_t;
/* Acquires one reference per populated slot, including duplicate names. Cached
 * by defining archive and callbacks/context until full unmount; callers must
 * keep the callback context alive that long. Zero slots stay zero. Does not
 * truncate to IW3 WeaponDef.hideTags[8]. Output is unchanged on failure.
 * Returns 1 ready, 0 absent, -1 invalid or acquisition failure. */
int CODOL_BindMountedWeaponHideTags(const char *,codol_xanim_string_acquire_t,
    codol_xanim_string_release_t,void *,const codol_weapon_hide_tag_handles_t **);
/* Native engine SL provider; returned references remain archive-owned. */
int CODOL_LoadEngineWeaponHideTags(const char *,const codol_weapon_hide_tag_handles_t **);
/* Owned SL references for an already-resolved (possibly composed) tag view.
 * out must be zeroed or a previous owned result. Acquires one reference per
 * populated slot, including duplicates. Failure rolls back new references
 * and preserves out; success releases its old references and replaces it.
 * Returns 1 ready, -1 invalid/acquisition failure. Release before SL shutdown.
 * Do not pass archive-borrowed handles to the release function. */
int CODOL_AcquireEngineWeaponHideTags(const codol_weapon_hide_tags_t *,codol_weapon_hide_tag_handles_t *);
void CODOL_ReleaseEngineWeaponHideTags(codol_weapon_hide_tag_handles_t *);
/* Resolves all zone-local names before acquiring native script-string refs.
 * Cached per asset/provider; survives replacement until full unmount, which
 * releases every acquisition. Callbacks must not change mounted archives.
 * 1/0/-1; failure preserves out and rolls back acquired references. */
int CODOL_BindMountedXAnimHandles(const char *,codol_xanim_string_acquire_t,
    codol_xanim_string_release_t,void *,const codol_xanim_handles_t **);
int CODOL_LoadEngineXAnimHandles(const char *,const codol_xanim_handles_t **);
void CODOL_UnmountArchives(void);
/* Free the archives a previous group replacement moved aside. Nothing else
 * frees them: mount_archives only unlinks the outgoing group because live
 * native code still holds WeaponDef pointers into it. Every borrower listed on
 * CODOL_UnloadCategoryAssets must be reset first. Returns how many were freed. */
unsigned CODOL_ReleaseRetiredArchives(void);
/* 1 when the engine script-string handle still reads exactly `name` (so a
 * cached reference to it is live), 0 for a dead or recycled handle. */
int CODOL_EngineStringHandleIs(unsigned handle,const char *name);
/* Move a mount group aside without mounting a replacement, so the outgoing
 * asset category can be unloaded before the next one is opened. group 0 (the
 * startup set) is refused. Returns how many archives were retired. */
unsigned CODOL_RetireRuntimeArchiveGroup(unsigned group);
/* SV_SetCoDOLCategoryTeardown entry point, called BEFORE the new category
 * mounts: retires the live group-1 archives and then unloads everything that
 * belonged to `previous_category`. */
void CODOL_UnloadGametypeAssets(const char *previous_category,const char *next_category);
/* SV_SetCoDOLSessionMapInstaller entry point: the playlist/session spelling of
 * this match's map ("" or NULL when there is none, which is every mp and zm
 * entry). Consulted by the two-argument CODOL_LoadMapArchives. */
void CODOL_SetSessionMapName(const char *session_map);
const char *CODOL_SessionMapName(void);
/* Drop the loose-file CSV overlay cache. Keyed by (script root, name) and not
 * by mounted generation, so a category switch must drop it explicitly. */
void CODOL_ResetReferenceStringTables(void);
/* Forget the map/session/category the group-1 reuse fast path remembers, so
 * the next CODOL_LoadMapArchives remounts even for the same name. Call it
 * whenever the mounted set is torn down behind that cache's back. */
void CODOL_ForgetMountedMapArchives(void);
/* Retire every piece of native state that belongs to the asset category
 * `from_type` ("mp", "coop" or "zm"), then free the retired archives, so a
 * handoff into another category leaves nothing of the old one resident or
 * reachable. Safe to call with a NULL/unknown from_type (it then only reports
 * differently). Not a no-op: callers gate it on an actual category change. */
void CODOL_UnloadCategoryAssets(const char *from_type);
void CODOL_InitAssetCommands(void);
int CODOL_LoadStartupArchives(void);
/* The asset category a map name PROVES, or NULL when the name proves nothing.
 * C1 0x612850 derives its own category from a case-insensitive prefix test on
 * the map/gametype it was handed -- "zm" (two characters), then "coop" (four),
 * everything else "mp" -- but only the first two are load-bearing: a coop
 * match's LEVEL zone is spelled mp_* (MEASURED: the coop playlist entry
 * coop_training_mp_killhouse_sh loads the level zone mp_killhouse_sh), so an
 * mp_* name is genuinely ambiguous between "mp" and "coop" and this returns
 * NULL for it. Callers that need a default may use "mp"; callers that need to
 * detect a contradiction must treat NULL as "no evidence", not as "mp". */
const char *CODOL_ZoneTypeForMap(const char *map);
/* Mount the group-1 archives for one match.
 *   map          the LEVEL zone spelling, what the client DB_LoadXFile's last
 *                (mp_killhouse_sh, zm_zombie_training, mp_crash_tropical).
 *   session_map  the playlist/session spelling when it differs from `map`
 *                (coop_training_mp_killhouse_sh); NULL or equal to `map` when
 *                there is no separate spelling, which is every mp and zm entry.
 *   zone_type    the asset category carrier ("mp", "coop" or "zm"). This is
 *                the authority; the map name is only used to refuse a
 *                contradiction it can actually prove.
 * MEASURED (dw-capture.log:2232, the client's own ClientLoadTime telemetry):
 * a coop match loads BOTH spellings -- "2005 common_mp | 1324
 * common_gametype_coop | 1720 coop_training_mp_killhouse_sh | 4956
 * mp_killhouse_sh" -- and coop_training_mp_killhouse_sh.ff is 41,861,397 bytes
 * carrying 44 of its own weapon assets, so the session zone is real content,
 * not a loadscreen stub. */
int CODOL_LoadMapArchivesEx(const char *map,const char *session_map,const char *zone_type);
/* Retained two-argument form: no separate session spelling. */
int CODOL_LoadMapArchives(const char *map,const char *zone_type);
int CODOL_BuildZonePath(const char *name,char *out,size_t capacity);

/* Bounded zlib stream helper shared with the fastfile reader. */
int CODOL_Inflate(const uint8_t *in, size_t input_size, uint8_t **out,
                  size_t *output_size, size_t exact_size, int padded);
#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
