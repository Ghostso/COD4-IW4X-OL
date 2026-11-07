#ifndef CODOL_LOAD_BLOCKS_H
#define CODOL_LOAD_BLOCKS_H
#include "codol_xmodel.h"
#pragma pack(push, 8)
enum { CODOL_LOAD_STACK=64 };
typedef struct {
    uint32_t reference;
    codol_asset_t asset;
} codol_asset_alias_t;
/* reference==0 catalogues an unaliased inline dependency for named lookup. */
typedef struct {
    const uint8_t *collision,*records;
    uint32_t category,count,reference;
} codol_dynamic_records_t;
/* Serialized span of an alias array or sound file, keyed by the block 3
 * address its reconstruction received. count is the alias count for arrays. */
typedef struct {
    const uint8_t *source;
    uint32_t reference,size,count;
} codol_sound_span_t;
/* GameWorldMp source ownership and named glass groups. group==UINT32_MAX
 * marks the world itself (also emitted when its glass pointer is null).
 * Other records preserve group order; IDs are serialized little-endian words.
 * name_reference is retained for pooled names, inline_name for inline names. */
typedef struct {
    const uint8_t *world,*glass,*ids;
    const char *inline_name;
    uint32_t group,name_reference;
    uint16_t count;
    /* UINT32_MAX world marker: 12-byte server records.
     * UINT32_MAX-1 FxWorld marker: 52-byte initial glass placements. */
    const uint8_t *pieces;
    uint32_t piece_count;
} codol_glass_span_t;
typedef struct {
    uint8_t *data[8];
    size_t capacity[8],position[8],written[8];
    const uint8_t *source;
    size_t source_size,source_position;
    unsigned active,depth;
    struct { unsigned block; size_t entered; } stack[CODOL_LOAD_STACK];
    codol_asset_alias_t *asset_aliases;
    size_t asset_alias_count,asset_alias_capacity;
    int collect_asset_aliases; /* private to the complete-zone transaction */
    uint32_t directory_reference;
    codol_dynamic_records_t *dynamic_records;
    size_t dynamic_record_count,dynamic_record_capacity;
    codol_sound_span_t *sound_records;
    size_t sound_record_count,sound_record_capacity;
    codol_glass_span_t *glass_records;
    size_t glass_record_count,glass_record_capacity;
} codol_load_blocks_t;
/* Borrowed 92-byte dynamic-entity records from this collision asset's complete
 * replay. Owner identity prevents borrowing records from another zone.
 * Encoded references are not native pointers. Output unchanged on failure. */
int CODOL_ResolveDynamicRecords(const codol_load_blocks_t *,const codol_asset_t *,unsigned,
    codol_dynamic_records_t *);
/* Complete replay retains typed source views for material insertion slots,
 * directory entries and inline model slots. All inline material/surface/model assets
 * are also catalogued by source view for named lookup. Other asset families'
 * pointer-slot aliases are not captured yet. These are never native pointers.
 * 1=found, 0=absent/invalid reference. Output unchanged unless found. */
int CODOL_ResolveMaterialAlias(const codol_load_blocks_t *,uint32_t,codol_asset_t *);
int CODOL_ResolveWeaponAlias(const codol_load_blocks_t *,uint32_t,codol_asset_t *);
/* Type 3 surface assets use insertion slots and directory entries. */
int CODOL_ResolveSurfaceAlias(const codol_load_blocks_t *,uint32_t,codol_asset_t *);
/* Type 4 XModels: directory entries, insertion slots, graphics-world
 * static-model draw-instance, dynamic-definition and effect-visual fields. */
int CODOL_ResolveModelAlias(const codol_load_blocks_t *,uint32_t,codol_asset_t *);
/* Type 30 FX: directory entries, insertion slots and dynamic-definition fields. */
int CODOL_ResolveEffectAlias(const codol_load_blocks_t *,uint32_t,codol_asset_t *);
/* Model/material aliases include inline FX single visuals, visual arrays and
 * both material pointers in decal pairs. Sound/runner strings and light
 * visuals are not treated as material pointers. */
/* Type 0 preset or type 1 collision map. Presets additionally catalogue
 * inline pointer fields in glass definitions and dynamic-entity definitions. */
int CODOL_ResolvePhysicsAlias(const codol_load_blocks_t *,unsigned type,uint32_t,codol_asset_t *);
/* Type 11 alias lists, 12 curves and 13 loaded sounds, from directory entries,
 * weapon/effect pointer slots and inline nested sound-file references. */
int CODOL_ResolveSoundAlias(const codol_load_blocks_t *,unsigned type,uint32_t,codol_asset_t *);
/* Serialized span behind a deduplicated alias array or sound file pointer.
 * Lets the reader replay loaded sounds and inline curves the loader wrote into
 * the rewound scratch block. 1=found, 0=absent; output unchanged if absent. */
int CODOL_ResolveSoundSpan(const codol_load_blocks_t *,uint32_t,codol_asset_t *,unsigned *count);
/* Caller keeps source alive. Capacities describe loader memory, not file
 * extents. Individual failed operations leave state/output unchanged. */
int CODOL_InitLoadBlocks(codol_load_blocks_t *,const uint8_t *,size_t,const uint32_t [8],unsigned);
void CODOL_FreeLoadBlocks(codol_load_blocks_t *);
int CODOL_PushLoadBlock(codol_load_blocks_t *,unsigned);
int CODOL_PopLoadBlock(codol_load_blocks_t *);
/* Alignment affects memory only. Block 2 is zero-filled without reading input.
 * Returns the encoded block reference, never a serialized-file offset. */
int CODOL_ReadLoadBlock(codol_load_blocks_t *,size_t,unsigned,uint32_t *);
/* DB_InsertPointer reserves four aligned bytes in block 3, with no file read. */
int CODOL_InsertLoadPointer(codol_load_blocks_t *,uint32_t *);
void CODOL_LoadBlockViews(const codol_load_blocks_t *,codol_model_block_t [8]);
/* Borrowed NUL-terminated XString in persistent block 3. Rejects sentinels,
 * scratch/runtime blocks and references beyond replayed bytes (including
 * zero-filled allocator capacity). NULL means unresolved/invalid. */
const char *CODOL_LoadBlockString(const codol_load_blocks_t *,uint32_t);
/* Caller has entered temporary block 0 for the asset reference. Replays the
 * header and skeletal prefix, then leaves block 3 pushed for remaining model
 * dependencies. Inline references become their reconstructed locations.
 * Failure preserves memory, cursors and output. Does not finish an XModel. */
int CODOL_ReplayXModelSkeleton(codol_load_blocks_t *,codol_xmodel_skeleton_t *);
/* Type 0 PhysPreset or type 1 PhysCollmap. Caller has entered block 0.
 * Returns to block 0 with dependencies in block 3. Atomic on failure.
 * Copies serialized records; engine pointer patching is a later step. */
int CODOL_ReplayPhysicsAsset(codol_load_blocks_t *,unsigned,uint32_t *);
/* XModelSurfs: records/trees in block 3, vertices in 6, indices in 7.
 * Same caller/atomicity contract as physics replay; creates no GPU objects. */
int CODOL_ReplayModelSurfaces(codol_load_blocks_t *,uint32_t *);
/* Image starts in block 0; water starts in block 3. Nested image references
 * use temporary block 0 and preserve insertion slots for -2 references. */
int CODOL_ReplayImage(codol_load_blocks_t *,uint32_t *);
int CODOL_ReplayWater(codol_load_blocks_t *,uint32_t *);
int CODOL_ReplayTechniqueSet(codol_load_blocks_t *,uint32_t *);
int CODOL_ReplayMaterial(codol_load_blocks_t *,uint32_t *);
/* Complete XModel and inline dependencies. Starts/ends in block 0, with
 * validated serialized extent and an atomic block-memory preflight. */
int CODOL_ReplayXModel(codol_load_blocks_t *,uint32_t *);
int CODOL_ReplayAnimation(codol_load_blocks_t *,uint32_t *);
/* FX records and inline model/material dependencies; no runtime FX lookup. */
int CODOL_ReplayEffect(codol_load_blocks_t *,uint32_t *);
/* Types 11 alias list, 12 curve, 13 loaded sound; includes serialized audio
 * payloads without audio-device initialization or runtime pointer patching. */
int CODOL_ReplaySoundAsset(codol_load_blocks_t *,unsigned,uint32_t *);
/* GfxWorld header, skies, BSP, cell trees and portals only. Starts in block 0
 * and leaves block 3 entered for draw data. Atomic on failure; does not finish
 * the world or install runtime visibility. */
int CODOL_ReplayWorldVisibility(codol_load_blocks_t *,uint32_t *);
/* Extends the same prefix through draw data and the light grid, leaving block
 * 3 entered for world models. Includes visibility; starts in block 0. No GPU calls. */
int CODOL_ReplayWorldDraw(codol_load_blocks_t *,uint32_t *);
/* Extends the draw prefix through scene allocations, shadow geometry and
 * light regions. Leaves block 3 entered for static/dynamic DPVS data. */
int CODOL_ReplayWorldScene(codol_load_blocks_t *,uint32_t *);
/* Complete serialized GfxWorld with dependencies and runtime allocations.
 * Starts/ends in block 0; does not install engine world pointers. */
int CODOL_ReplayWorld(codol_load_blocks_t *,uint32_t *);
/* Entity text, trigger geometry and map stages. Serialized replay only;
 * CODOL_ReadMapEntities separately validates and owns runtime-facing data. */
int CODOL_ReplayMapEntities(codol_load_blocks_t *,uint32_t *);
/* Complete clipMap serialized replay, including MapEnts and dynamic assets.
 * Starts/ends in block 0; owned collision conversion/installation is separate. */
int CODOL_ReplayCollision(codol_load_blocks_t *,uint32_t *);
/* Menu statement trees in block 3; bounded recursion, strings and nested
 * inline statements. Atomic on failure; does not evaluate or finish a menu. */
int CODOL_ReplayMenuExpression(codol_load_blocks_t *,uint32_t *);
/* Menu event sets and tagged conditional/local-variable payloads in block 3.
 * Reconstructs data with bounded recursion; never executes event scripts. */
int CODOL_ReplayMenuEvents(codol_load_blocks_t *,uint32_t *);
/* Initialize directory/string-pool replay from an opened zone. Zone must
 * outlive the stream. Declared capacities are rounded to allocator pages. */
int CODOL_BeginZoneReplay(const codol_zone_t *,codol_load_blocks_t *);
/* Ordered dispatch: 1 replayed (including measured zero-payload no-load
 * families), 0 unsupported type, -1 invalid/cursor mismatch. Never skips an
 * unknown or nonempty unimplemented asset. Failure leaves memory/cursors
 * untouched. */
int CODOL_ReplayZoneAsset(const codol_zone_t *,unsigned,codol_load_blocks_t *);
/* Complete transaction. Source zone outlives the result; failure leaves out
 * untouched. failed_asset is UINT32_MAX for initialization failure. */
int CODOL_ReplayZone(const codol_zone_t *,codol_load_blocks_t *,unsigned *failed_asset);
/* Production mounts retain reconstructed blocks until unmount. Archive input
 * order and atomicity match MountArchives; no runtime pointer publication yet. */
int CODOL_MountRuntimeArchives(const char *const *,size_t,const char *,size_t *,unsigned *);
/* Atomically replace a nonzero logical group after complete validation. Old
 * group assets stop participating in lookup. Previously borrowed objects remain
 * owned until UnmountArchives, including across subsequent group replacements. */
int CODOL_ReplaceRuntimeArchives(const char *const *,size_t,const char *,unsigned,size_t *,unsigned *);
/* Borrowed reconstructed views, newest archive first. Returns 0 for missing or
 * source-only mounts. Block 0 is scratch, never a persistent asset object. */
unsigned CODOL_MountedArchiveCount(unsigned group);
int CODOL_MountedBlockViews(unsigned,codol_model_block_t [8]);
#pragma pack(pop)
#endif
