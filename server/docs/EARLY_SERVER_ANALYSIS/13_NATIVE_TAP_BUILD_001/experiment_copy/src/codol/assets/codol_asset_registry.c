/* Native archive ownership for script source resolution.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_assets.h"
#include "codol_script_source.h"
#include "codol_structured_schema.h"
#include "codol_script_profile_vm.h"
#include "codol_collision.h"
#include "codol_dynents.h"
#include "codol_effects.h"
#include "codol_effects_native.h"
#include "codol_sound_native.h"
#include "codol_physics_native.h"
#include "codol_load_blocks.h"
#include "codol_glass_load.h"
#include "codol_glass_map.h"
#include "codol_xsurface.h"
#include "codol_stream_model.h"
#include "codol_material_native.h"
#include "codol_xmodel_native.h"
#include "codol_xanim_native.h"
#include "codol_weapon_native.h"
#include "codol_weapon_compose.h"
#include "world.h"
#include <math.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <stdarg.h>
#include <stdio.h>

typedef struct table_cache_s {
    codol_stringtable_t source;
    codol_engine_table_t engine;
    struct table_cache_s *next;
} table_cache_t;

typedef struct reference_table_s {
    table_cache_t table;
    char *root,*name;
    struct reference_table_s *next;
} reference_table_t;
static reference_table_t *reference_tables;

int CODOL_LoadReferenceStringTable(const char *root,const char *name,const codol_engine_table_t **out)
{
    reference_table_t *entry;char *data=NULL;size_t size,n,i;int status;
    if(!root || !*root)return 0;
    if(!name || !out)return -1;
    n=strlen(name);if(n<4 || strcmp(name+n-4,".csv"))return 0;
    for(entry=reference_tables;entry;entry=entry->next)
        if(!strcmp(root,entry->root) && !strcmp(name,entry->name)){*out=&entry->table.engine;return 1;}
    status=CODOL_ReadScriptSource(root,NULL,name,&data,&size);if(status!=1)return status;
    entry=calloc(1,sizeof(*entry));if(!entry){free(data);return -1;}
    status=CODOL_ReadCSVStringTable(data,size,&entry->table.source);free(data);
    if(!status)goto fail_reference;
    entry->root=strdup(root);entry->name=strdup(name);
    n=(size_t)entry->table.source.rows*entry->table.source.columns;
    entry->table.engine.values=calloc(n,sizeof(*entry->table.engine.values));
    if(!entry->root || !entry->name || !entry->table.engine.values)goto fail_reference;
    for(i=0;i<n;++i)entry->table.engine.values[i]=entry->table.source.cells[i].text;
    entry->table.engine.name=entry->name;
    entry->table.engine.rowCount=entry->table.source.rows;
    entry->table.engine.columnCount=entry->table.source.columns;
    entry->next=reference_tables;reference_tables=entry;*out=&entry->table.engine;return 1;
fail_reference:
    free(entry->root);free(entry->name);free(entry->table.engine.values);
    CODOL_FreeStringTable(&entry->table.source);free(entry);return -1;
}

typedef struct rawfile_cache_s {
    codol_engine_rawfile_t engine;
    struct rawfile_cache_s *next;
} rawfile_cache_t;

/* A string-table name this archive was searched for and does not carry. An
 * archive's contents never change once mounted, so the answer stays true for
 * its whole life; without it every tableLookup walked all ~30k assets of the
 * archives in front of the one that has the table (~140 us each, dozens per
 * kill, 60-70 on a challenge tier). */
typedef struct table_miss_s {
    struct table_miss_s *next;
    char name[1];
} table_miss_t;

typedef struct dependency_index_entry_s {
    const char *name;
    const codol_asset_t *asset;
} dependency_index_entry_t;

typedef struct archive_s {
    codol_zone_t zone;
    codol_load_blocks_t blocks;
    int prepared;
    dependency_index_entry_t *dependency_index;
    size_t dependency_index_capacity;
    int dependency_index_attempted;
    unsigned group;
    codol_script_string_t *script_strings;
    struct model_cache_s *models;
    table_cache_t *tables;
    table_miss_t *table_misses;
    rawfile_cache_t *rawfiles;
    struct material_cache_s *materials;
    struct physics_preset_cache_s *physics_presets;
    struct physics_map_cache_s *physics_maps;
    struct effect_cache_s *effects;
    struct sound_cache_s *sounds;
    struct common_world_cache_s *worlds;
    struct glass_world_cache_s *glass_worlds;
    struct xanim_strings_s *xanim_strings;
    struct weapon_tags_s *weapon_tags;
    codol_native_weapon_core_t *null_weapon;
    struct native_weapon_cache_s *native_weapons;
    struct archive_s *next;
} archive_t;
typedef struct sound_cache_s {
    codol_sound_alias_list_t source; /* first member: native lookups cast back */
    const uint8_t *definition;
    archive_t *archive;
    codol_native_sound_t native;
    int native_ready;
    struct sound_cache_s *next;
} sound_cache_t;
typedef struct native_weapon_cache_s {
    const uint8_t *definition;
    codol_native_weapon_core_t core;
    struct native_weapon_cache_s *next;
} native_weapon_cache_t;
typedef struct xanim_strings_s {
    const uint8_t *definition;
    codol_xanim_handles_t handles;
    codol_native_xanim_t native;
    codol_xanim_string_acquire_t acquire;
    codol_xanim_string_release_t release;
    void *context;
    struct xanim_strings_s *next;
} xanim_strings_t;
typedef struct weapon_tags_s {
    const uint8_t *definition;
    codol_weapon_hide_tag_handles_t handles;
    codol_xanim_string_acquire_t acquire;
    codol_xanim_string_release_t release;
    void *context;
    struct weapon_tags_s *next;
} weapon_tags_t;
typedef struct common_world_cache_s {
    const uint8_t *definition;
    struct ComWorld world;
    struct common_world_cache_s *next;
} common_world_cache_t;
typedef struct glass_world_cache_s {
    const uint8_t *definition;
    codol_glass_groups_t groups;
    struct glass_world_cache_s *next;
} glass_world_cache_t;
_Static_assert(sizeof(struct ComWorld)==16,"IW3 common world ABI");
_Static_assert(sizeof(struct ComPrimaryLight)==68,"IW3 primary light ABI");
_Static_assert(offsetof(struct ComPrimaryLight,defName)==64,"IW3 light name");
typedef struct material_cache_s {
    const uint8_t *definition;
    codol_native_material_t native;
    struct material_cache_s *next;
} material_cache_t;
typedef struct physics_preset_cache_s {
    const uint8_t *definition;
    codol_native_physics_preset_t native;
    struct physics_preset_cache_s *next;
} physics_preset_cache_t;
typedef struct physics_map_cache_s {
    codol_physics_map_t source;
    const uint8_t *definition;
    codol_native_physics_map_t native;
    int native_ready;
    struct physics_map_cache_s *next;
} physics_map_cache_t;
typedef struct effect_cache_s {
    codol_effect_source_t source;
    const uint8_t *definition;
    archive_t *archive;
    struct native_effect_cache_s *native;
    struct effect_cache_s *next;
} effect_cache_t;
typedef struct native_effect_cache_s {
    codol_native_effect_t native;
    effect_cache_t *owner;
    archive_t *generation;
    codol_effect_model_resolver_t resolver;
    void *context;
    struct native_effect_cache_s *next;
    /* Private transaction state; bindings are patched before cache publication. */
    FxEffectDef placeholder;
    codol_effect_bindings_t *bindings;
    struct native_effect_cache_s **children;
    int prepared;
} native_effect_cache_t;
typedef struct {
    native_effect_cache_t *pending;
    archive_t *generation;
    codol_effect_model_resolver_t resolver;
    void *context;
} effect_transaction_t;
typedef struct model_cache_s {
    codol_mounted_model_skeleton_t model;
    codol_asset_t source;
    codol_mounted_model_geometry_t geometry;
    int geometry_ready;
    codol_xmodel_materials_t materials;
    int materials_ready;
    archive_t *archive;
    archive_t *generation; /* Mounted-set head when dependencies were resolved. */
    codol_mounted_model_surfaces_t *surfaces[4];
    codol_stream_model_t streams[4];
    uint16_t *bone_handles;
    codol_bone_string_acquire_t acquire;
    codol_bone_string_release_t release;
    void *string_context;
    struct collision_model_cache_s *collision_model;
    struct model_cache_s *next;
} model_cache_t;
typedef struct collision_model_cache_s {
    codol_native_model_core_t core;
    codol_native_model_mesh_t mesh;
    XModel physics_model; /* Borrows the core's owned arrays and archive dependencies. */
    int physics_ready;
} collision_model_cache_t;
static archive_t *archives;
static archive_t *retired_archives;
static codol_stream_model_loader_t stream_loader;
static void *stream_context;
int CODOL_SetStreamModelLoader(codol_stream_model_loader_t loader,void *context)
{
    if (archives && (loader!=stream_loader || context!=stream_context)) return 0;
    stream_loader=loader; stream_context=context; return 1;
}
typedef struct {
    archive_t *archive;
    codol_collision_named_model_resolver_t model_resolver;
    void *model_context;
} collision_context_t;
static const char *collision_archive_string(void *context,uint32_t reference)
{
    const archive_t *archive=((collision_context_t *)context)->archive;
    return archive->prepared ? CODOL_LoadBlockString(&archive->blocks,reference) : NULL;
}
static void *collision_archive_model(void *context,uint32_t reference)
{
    const collision_context_t *binding=context;
    const archive_t *archive=binding->archive;
    codol_asset_t asset;
    const char *name;
    uint32_t ref;
    if (!archive->prepared || !binding->model_resolver ||
        !CODOL_ResolveModelAlias(&archive->blocks,reference,&asset) || asset.size<360) return NULL;
    ref=(uint32_t)asset.data[0]|(uint32_t)asset.data[1]<<8|
        (uint32_t)asset.data[2]<<16|(uint32_t)asset.data[3]<<24;
    if (ref==UINT32_MAX) {
        name=(const char *)(asset.data+360);
        if (!memchr(name,0,asset.size-360)) return NULL;
    } else name=CODOL_LoadBlockString(&archive->blocks,ref);
    if (!name) return NULL;
    if (*name==',') ++name;
    return *name ? binding->model_resolver(binding->model_context,name) : NULL;
}
int CODOL_LoadMountedCollision(const char *name,codol_collision_map_t *out)
{
    return CODOL_LoadMountedCollisionModels(name,NULL,NULL,out);
}
int CODOL_LoadMountedCollisionModels(const char *name,codol_collision_named_model_resolver_t resolver,
    void *context,codol_collision_map_t *out)
{
    archive_t *entry;
    if (!name || !*name || !out) return -1;
    for (entry=archives;entry;entry=entry->next) {
        collision_context_t binding={entry,resolver,context};
        int status=CODOL_LoadZoneCollisionResolved(&entry->zone,name,collision_archive_string,
            collision_archive_model,&binding,out);
        if (status) return status;
    }
    return 0;
}

/* Locate the one addon_map_ents (IW4 type 42) a coop playlist zone ships.
 *
 * The asset name is maps/mp/<playlist>.mapents for all nine (MEASURED
 * 2026-09-20, docs/CODOL_ADDON_MAP_ENTS_20260920.md), and its name is inline
 * after the 36-byte header for all nine; a de-duplicated block-3 reference is
 * still resolved so a future patch zone that shares the string still matches.
 * Type 42 has no record_asset() entry, so this walks the zone directory the
 * way CODOL_FindRawFileStatus does instead of using the dependency index.
 * 1 = loaded, 0 = no zone carries it, -1 = present but unreadable. */
static const char *addon_map_ents_name(const archive_t *archive, const codol_asset_t *asset)
{
    const uint8_t *p; size_t available; uint32_t reference;
    if (!asset || asset->type != CODOL_ASSET_ADDON_MAP_ENTS || asset->size < 36) return NULL;
    p = asset->data;
    reference = (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
    if (reference == UINT32_MAX) { p += 36; available = asset->size-36; }
    else {
        if (!archive->prepared) return NULL;
        return CODOL_LoadBlockString(&archive->blocks, reference);
    }
    return memchr(p, 0, available) ? (const char *)p : NULL;
}
static int asset_name_equal(const char *, const char *);
int CODOL_LoadMountedAddonMapEntities(const char *name, codol_map_entities_t *out)
{
    static const char prefix[] = "maps/mp/", suffix[] = ".mapents";
    char wanted[256];
    size_t length;
    archive_t *archive;
    if (!name || !*name || !out) return -1;
    length = strlen(name);
    if (length + sizeof(prefix) + sizeof(suffix) - 1 > sizeof(wanted)) return -1;
    memcpy(wanted, prefix, sizeof(prefix)-1);
    memcpy(wanted + sizeof(prefix)-1, name, length);
    memcpy(wanted + sizeof(prefix)-1 + length, suffix, sizeof(suffix));
    for (archive = archives; archive; archive = archive->next) {
        unsigned i;
        /* Later assets override earlier names, just as a patch zone does. */
        for (i = archive->zone.asset_count; i > 0; --i) {
            codol_asset_t asset;
            const char *candidate;
            if (!CODOL_ZoneAsset(&archive->zone, i-1, &asset)) return -1;
            if (asset.type != CODOL_ASSET_ADDON_MAP_ENTS) continue;
            candidate = addon_map_ents_name(archive, &asset);
            if (!candidate || candidate[0] == ',' || !asset_name_equal(candidate, wanted)) continue;
            return CODOL_ReadAddonMapEntities(asset.data, asset.size, out) ? 1 : -1;
        }
    }
    return 0;
}

int CODOL_LoadMountedDynamicEntities(const char *name,codol_dynamic_entities_t *out)
{
    archive_t *entry;
    if(!name || !*name || !out) return -1;
    for(entry=archives;entry;entry=entry->next) {
        codol_asset_t collision,world;
        int status=CODOL_FindZoneCollisionPair(&entry->zone,name,&collision,&world);
        if(status<0) return -1;
        if(status==1) return CODOL_ReadDynamicEntities(&collision,&entry->blocks,out)?1:-1;
    }
    return 0;
}

int CODOL_MountArchive(const char *path, const char *client_exe)
{
    return CODOL_MountArchives(&path, 1, client_exe, NULL);
}

static int mount_archives(const char *const *paths,size_t count,
                         const char *client_exe,size_t *failed_index,unsigned *failed_asset,int prepare,unsigned group)
{
    archive_t *pending = NULL, *tail = NULL;
    size_t i;
    if (failed_asset) *failed_asset=UINT32_MAX;
    if (!paths || !count) { if (failed_index) *failed_index = 0; return 0; }
    for (i = 0; i < count; ++i) {
        archive_t *entry = calloc(1, sizeof(*entry));
        if (!entry) goto fail;
        if (!paths[i] || !(client_exe && *client_exe ?
            CODOL_OpenFastFile(&entry->zone, paths[i], client_exe) :
            CODOL_OpenZoneFile(&entry->zone, paths[i]))) {
            free(entry); goto fail;
        }
        if (prepare && !CODOL_ReplayZone(&entry->zone,&entry->blocks,failed_asset)) {
            CODOL_CloseZone(&entry->zone); free(entry); goto fail;
        }
        entry->prepared=prepare;
        entry->group=group;
        if (!tail) tail = entry;
        entry->next = pending; pending = entry;
    }
    if(group) {
        archive_t **link=&archives;
        while(*link) {
            archive_t *entry=*link;
            if(entry->group==group) {
                *link=entry->next; entry->next=retired_archives; retired_archives=entry;
            } else link=&entry->next;
        }
    }
    /* A new archive can replace any named dependency used by a composed
     * weapon, even without replacing an existing group. Preserve old cores
     * for live users, but force subsequent names to resolve the new mount. */
    CODOL_RetireComposedWeapons();
    tail->next = archives; archives = pending; return 1;
fail:
    if (failed_index) *failed_index = i;
    while (pending) {
        archive_t *entry = pending; pending = entry->next;
        free(entry->dependency_index);
        CODOL_FreeLoadBlocks(&entry->blocks); CODOL_CloseZone(&entry->zone); free(entry);
    }
    return 0;
}
int CODOL_MountArchives(const char *const *paths,size_t count,const char *client_exe,size_t *failed_index)
{
    return mount_archives(paths,count,client_exe,failed_index,NULL,0,0);
}
int CODOL_MountRuntimeArchives(const char *const *paths,size_t count,const char *client_exe,
                              size_t *failed_index,unsigned *failed_asset)
{
    return mount_archives(paths,count,client_exe,failed_index,failed_asset,1,0);
}
int CODOL_ReplaceRuntimeArchives(const char *const *paths,size_t count,const char *client_exe,
                                unsigned group,size_t *failed_index,unsigned *failed_asset)
{
    if(!group) return 0;
    return mount_archives(paths,count,client_exe,failed_index,failed_asset,1,group);
}
/* How many archives of a mount group are currently live. A restart of the
 * same map can reuse them instead of re-opening, decrypting and replaying
 * every zone: mount_archives retires the old group rather than freeing it
 * (retired cores are still reachable from composed weapons), so remounting
 * unchanged content keeps a second full copy of the map resident. */
unsigned CODOL_MountedArchiveCount(unsigned group)
{
    const archive_t *entry; unsigned count=0;
    for(entry=archives;entry;entry=entry->next)
        if(entry->group==group && entry->prepared) ++count;
    return count;
}
/* Move a mount group aside WITHOUT mounting a replacement, so a caller that
 * knows the outgoing asset category is finished can unload it before the next
 * one is opened instead of holding both resident. Same retirement the mount
 * path performs (archives whose data is still reachable from a composed weapon
 * must not be freed here), so CODOL_ReleaseRetiredArchives, and every borrower
 * reset it lists, still have to follow. group 0 is the startup set and is
 * refused: nothing in it is category-specific. Returns how many were retired. */
unsigned CODOL_RetireRuntimeArchiveGroup(unsigned group)
{
    archive_t **link=&archives; unsigned count=0;
    if(!group) return 0;
    while(*link) {
        archive_t *entry=*link;
        if(entry->group==group) {
            *link=entry->next; entry->next=retired_archives; retired_archives=entry; ++count;
        } else link=&entry->next;
    }
    if(count) CODOL_RetireComposedWeapons();
    return count;
}
int CODOL_MountedBlockViews(unsigned index,codol_model_block_t views[8])
{
    archive_t *entry=archives;
    if (!views) return 0;
    while (entry && index) { entry=entry->next; --index; }
    if (!entry || !entry->prepared) return 0;
    CODOL_LoadBlockViews(&entry->blocks,views); return 1;
}

int CODOL_LoadScriptAssetStatus(const char *name, uint8_t **out, size_t *size)
{
    const codol_engine_rawfile_t *rawfile;
    uint8_t *data;
    size_t length;
    int status;
    if (!name || !out || !size) return -1;
    /* Share archive precedence and reconstructed XString resolution with the
     * engine rawfile path. The standalone zone reader knows inline names only. */
    status = CODOL_LoadEngineRawFile(name, &rawfile);
    if (status != 1) return status;
    if (!rawfile->buffer || rawfile->len < 0) return -1;
    length = (size_t)rawfile->len;
    /* This VM compiles source. Binary bytecode must be translated through
     * a separate loader, never silently truncated at an embedded NUL. */
    if (length > 16*1024*1024 || memchr(rawfile->buffer, 0, length)) return -1;
    data = malloc(length + 1);
    if (!data) return -1;
    memcpy(data, rawfile->buffer, length + 1);
    *out = data; *size = length; return 1;
}

int CODOL_LoadScriptAsset(const char *name, uint8_t **out, size_t *size)
{
    return CODOL_LoadScriptAssetStatus(name, out, size) == 1;
}

static int asset_name_equal(const char *a, const char *b)
{
    for (;;) {
        unsigned x = (unsigned char)*a++, y = (unsigned char)*b++;
        if (x == '\\') x = '/';
        if (y == '\\') y = '/';
        if (x >= 'A' && x <= 'Z') x += 32;
        if (y >= 'A' && y <= 'Z') y += 32;
        if (x != y) return 0;
        if (!x) return 1;
    }
}
static const char *dependency_asset_name(const archive_t *,const codol_asset_t *);
int CODOL_LoadMountedXModelSkeleton(const char *name,const codol_mounted_model_skeleton_t **out)
{
    archive_t *archive;
    if (!name || !*name || !out) return -1;
    for (archive=archives;archive;archive=archive->next) {
        model_cache_t *cached;
        unsigned index,limit=archive->zone.asset_count;
        const codol_asset_t *selected=NULL;
        for (cached=archive->models;cached;cached=cached->next)
            if (cached->generation==archives && asset_name_equal(cached->model.skeleton.name,name)) { *out=&cached->model; return 1; }
        if (archive->prepared) {
            size_t i;
            /* Models can be defined inside the graphics world or another
             * asset, without their own directory entry. Source order retains
             * last-definition wins even though aliases are sorted by address. */
            for (i=0;i<archive->blocks.asset_alias_count;++i) {
                const codol_asset_t *asset=&archive->blocks.asset_aliases[i].asset;
                const char *candidate;
                if (asset->type!=4) continue;
                candidate=dependency_asset_name(archive,asset);
                if (!candidate || *candidate==',' || !asset_name_equal(candidate,name)) continue;
                if (!selected || asset->data>selected->data) selected=asset;
            }
            if (!selected) continue;
            limit=1;
        }
        for (index=limit;index;--index) {
            codol_asset_t asset;
            codol_xmodel_skeleton_t source={0},owned={0};
            codol_model_block_t views[8];
            if (selected) asset=*selected;
            else if (!CODOL_ZoneAsset(&archive->zone,index-1,&asset)) return -1;
            if (asset.type!=4) continue;
            if (!CODOL_ReadXModelSkeleton(&asset,&source)) return -1;
            if (source.name && !asset_name_equal(source.name,name)) { CODOL_FreeXModelSkeleton(&source); continue; }
            if (!archive->prepared) { CODOL_FreeXModelSkeleton(&source); return -1; }
            CODOL_LoadBlockViews(&archive->blocks,views);
            views[0]=(codol_model_block_t){0}; /* discarded temporary headers */
            if (!CODOL_RelocateXModelSkeleton(&source,views,&owned)) { CODOL_FreeXModelSkeleton(&source); return -1; }
            CODOL_FreeXModelSkeleton(&source);
            if (!owned.name || !asset_name_equal(owned.name,name)) { CODOL_FreeXModelSkeleton(&owned); continue; }
            if (!archive->script_strings && !CODOL_ReadScriptStrings(&archive->zone,&archive->script_strings)) {
                CODOL_FreeXModelSkeleton(&owned); return -1;
            }
            cached=calloc(1,sizeof(*cached));
            if (!cached) { CODOL_FreeXModelSkeleton(&owned); return -1; }
            cached->model.skeleton=owned;
            cached->source=asset;
            cached->archive=archive;
            cached->generation=archives;
            if (!CODOL_ResolveXModelBoneNames(&owned,archive->script_strings,archive->zone.string_count,&cached->model.bone_names) ||
                cached->model.bone_names.unresolved) {
                CODOL_FreeXModelBoneNames(&cached->model.bone_names);
                CODOL_FreeXModelSkeleton(&cached->model.skeleton); free(cached); return -1;
            }
            cached->next=archive->models; archive->models=cached;
            *out=&cached->model; return 1;
        }
    }
    return 0;
}
int CODOL_LoadMountedXModelGeometry(const char *name,const codol_mounted_model_geometry_t **out)
{
    const codol_mounted_model_skeleton_t *model;
    codol_mounted_model_geometry_t pending={0};
    model_cache_t *cached;
    int status;
    if (!out) return -1;
    status=CODOL_LoadMountedXModelSkeleton(name,&model);
    if (status!=1) return status;
    cached=(model_cache_t *)model;
    if (!cached->geometry_ready) {
        if (!CODOL_ReadXModelCollision(&cached->source,&pending.collision) ||
            !CODOL_ReadXModelBounds(&cached->source,&pending.bounds) ||
            !CODOL_ReadXModelLods(&cached->source,&pending.lods)) {
            CODOL_FreeXModelCollision(&pending.collision);
            CODOL_FreeXModelBounds(&pending.bounds); return -1;
        }
        cached->geometry=pending; cached->geometry_ready=1;
    }
    *out=&cached->geometry; return 1;
}
int CODOL_LoadMountedModelMaterials(const char *name,const codol_xmodel_materials_t **out)
{
    const codol_mounted_model_skeleton_t *model; model_cache_t *cached; int status;
    if (!out) return -1;
    status=CODOL_LoadMountedXModelSkeleton(name,&model); if(status!=1) return status;
    cached=(model_cache_t *)model;
    if(!cached->materials_ready) {
        if(!CODOL_ReadXModelMaterials(&cached->source,&cached->materials)) return -1;
        cached->materials_ready=1;
    }
    *out=&cached->materials; return 1;
}
static archive_t *find_dependency_definition(unsigned,const char *,codol_asset_t *);
int CODOL_LoadMountedModelMaterialSource(const char *name,unsigned index,codol_mounted_model_material_t *out)
{
    const codol_xmodel_materials_t *materials;
    const codol_mounted_model_skeleton_t *model;
    const codol_xmodel_material_t *slot;
    codol_mounted_model_material_t result={0};
    archive_t *archive;
    int status;
    if (!out) return -1;
    status=CODOL_LoadMountedModelMaterials(name,&materials); if (status!=1) return status;
    if (index>=materials->count) return -1;
    slot=materials->materials+index;
    if (CODOL_LoadMountedXModelSkeleton(name,&model)!=1) return -1;
    archive=((const model_cache_t *)model)->archive;
    if (slot->inline_asset.data) result.asset=slot->inline_asset;
    else if (!CODOL_ResolveMaterialAlias(&archive->blocks,slot->reference,&result.asset)) return -1;
    result.name=dependency_asset_name(archive,&result.asset);
    if (!result.name || !*result.name) return -1;
    /* Asset linking also redirects real definitions to the current override. */
    archive=find_dependency_definition(5,result.name[0]==',' ? result.name+1 : result.name,&result.asset);
    if (!archive) return -1;
    result.name=dependency_asset_name(archive,&result.asset);
    CODOL_LoadBlockViews(&archive->blocks,result.blocks);
    result.blocks[0]=(codol_model_block_t){0};
    *out=result; return 1;
}
int CODOL_LoadMountedModelMaterial(const char *name,unsigned index,codol_asset_t *out)
{
    codol_mounted_model_material_t source; int status;
    if (!out) return -1;
    status=CODOL_LoadMountedModelMaterialSource(name,index,&source);
    if (status==1) *out=source.asset;
    return status;
}
static const char *dependency_asset_name(const archive_t *archive,const codol_asset_t *asset)
{
    uint32_t ref; const uint8_t *p; size_t available,offset,header;
    if (!asset || (asset->type>2 && asset->type!=3 && asset->type!=4 && asset->type!=5 && asset->type!=11 && asset->type!=12 && asset->type!=13 && asset->type!=16 && asset->type!=18 && asset->type!=20 && asset->type!=28 && asset->type!=30 && asset->type!=39 && asset->type!=40 && asset->type!=41 && asset->type!=43)) return NULL;
    /* Sound headers: 12-byte alias list, 136-byte curve, 48-byte loaded sound;
     * all three carry their name reference in the leading word. */
    header=asset->type==0 ? 68 : asset->type==1 ? 72 : asset->type==2 ? 88 : asset->type==3 ? 48 : asset->type==4 ? 360 : asset->type==11 ? 12 : asset->type==12 ? 136 : asset->type==13 ? 48 : asset->type==16 ? 16 : asset->type==18 ? 84 : asset->type==20 ? 116 : asset->type==28 ? 0xbfc : asset->type==30 ? 32 : asset->type==39 ? 12 : asset->type==40 ? 112 : asset->type==41 ? 0x314 : asset->type==43 ? 12 : 96;
    if (asset->size<header) return NULL;
    p=asset->data; ref=(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
    if (ref==UINT32_MAX) { p+=header; available=asset->size-header; }
    else {
        if (!ref || ((ref-1)>>28)!=3) return NULL;
        offset=(ref-1)&0xfffffff;
        if (offset>=archive->blocks.written[3]) return NULL;
        p=archive->blocks.data[3]+offset; available=archive->blocks.written[3]-offset;
    }
    return memchr(p,0,available) ? (const char *)p : NULL;
}
/* Hash normalization must match asset_name_equal byte for byte: ASCII case
 * folding and slash equivalence only. Preserve punctuation and non-ASCII. */
static uint32_t dependency_name_hash(unsigned type,const char *name)
{
    uint32_t hash=2166136261u^type;
    unsigned c;
    while((c=(unsigned char)*name++)!=0) {
        if(c=='\\')c='/';
        if(c>='A' && c<='Z')c+=32;
        hash=(hash^c)*16777619u;
    }
    return hash;
}
/* Replayed blocks and aliases are immutable once the archive is published.
 * Index only complete archives; failure leaves the original scan available.
 * Nothing is shared between archive generations or built during zone replay. */
static int prepare_dependency_index(archive_t *archive)
{
    dependency_index_entry_t *index;
    size_t capacity=16,i,count=archive->blocks.asset_alias_count;
    if(archive->dependency_index)return 1;
    if(!archive->prepared || archive->dependency_index_attempted)return 0;
    archive->dependency_index_attempted=1;
    if(!count)return 0;
    if(count>(size_t)-1/2)return 0;
    while(capacity<count*2) {
        if(capacity>(size_t)-1/2)return 0;
        capacity*=2;
    }
    if(capacity>(size_t)-1/sizeof(*index))return 0;
    index=calloc(capacity,sizeof(*index));
    if(!index)return 0;
    for(i=0;i<count;++i) {
        const codol_asset_t *asset=&archive->blocks.asset_aliases[i].asset;
        const char *name=dependency_asset_name(archive,asset);
        size_t slot;
        if(!name || !*name || name[0]==',')continue;
        slot=dependency_name_hash(asset->type,name)&(capacity-1);
        while(index[slot].asset) {
            if(index[slot].asset->type==asset->type &&
               asset_name_equal(index[slot].name,name))break;
            slot=(slot+1)&(capacity-1);
        }
        /* The old scan selects the greatest serialized source address, not
         * the last alias-array position (that array is sorted by reference). */
        if(!index[slot].asset || asset->data>index[slot].asset->data) {
            index[slot].name=name;index[slot].asset=asset;
        }
    }
    archive->dependency_index=index;
    archive->dependency_index_capacity=capacity;
    return 1;
}
/* DB_LinkXAssetEntry's leading comma denotes a reference, not an overriding
 * definition. Search real definitions newest first, including inline assets. */
static archive_t *find_dependency_definition(unsigned type,const char *name,codol_asset_t *out)
{
    archive_t *archive;
    if (!name || !*name) return NULL;
    for (archive=archives;archive;archive=archive->next) {
        const codol_asset_t *winner=NULL; size_t i;
        if(prepare_dependency_index(archive)) {
            size_t mask=archive->dependency_index_capacity-1;
            size_t slot=dependency_name_hash(type,name)&mask;
            const dependency_index_entry_t *entry;
            while((entry=&archive->dependency_index[slot])->asset) {
                if(entry->asset->type==type && asset_name_equal(entry->name,name)) {
                    *out=*entry->asset;return archive;
                }
                slot=(slot+1)&mask;
            }
            continue;
        }
        for (i=0;i<archive->blocks.asset_alias_count;++i) {
            const codol_asset_t *asset=&archive->blocks.asset_aliases[i].asset;
            const char *candidate;
            if (asset->type!=type) continue;
            candidate=dependency_asset_name(archive,asset);
            if (!candidate || candidate[0]==',' || !asset_name_equal(candidate,name)) continue;
            if (!winner || asset->data>winner->data) winner=asset;
        }
        if (winner) { *out=*winner; return archive; }
    }
    return NULL;
}
static uint32_t world_u32(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static int weapon_string(const archive_t *archive,const codol_asset_t *asset,size_t *pos,uint32_t ref,const char **out)
{
    const uint8_t *p,*end; size_t available,offset;
    if (!ref) { *out=NULL; return 1; }
    if (ref==UINT32_MAX) {
        if (*pos>asset->size) return 0;
        p=asset->data+*pos; available=asset->size-*pos;
    } else {
        if (((ref-1)>>28)!=3) return 0;
        offset=(ref-1)&0xfffffff;
        if (offset>=archive->blocks.written[3]) return 0;
        p=archive->blocks.data[3]+offset; available=archive->blocks.written[3]-offset;
    }
    end=memchr(p,0,available); if (!end) return 0;
    *out=(const char *)p;
    if (ref==UINT32_MAX) *pos+=(size_t)(end-p)+1;
    return 1;
}
static unsigned xanim_u16(const uint8_t *p) { return p[0]|(unsigned)p[1]<<8; }
static int xanim_take(const codol_asset_t *asset,size_t *pos,size_t count,size_t stride,const uint8_t **out)
{
    if(*pos>asset->size || count>(asset->size-*pos)/stride) return 0;
    *out=asset->data+*pos; *pos+=count*stride; return 1;
}
int CODOL_LoadMountedXAnim(const char *name,codol_mounted_xanim_t *out)
{
    static const unsigned offsets[]={4,6,8,32,10,12},widths[]={1,2,4,2,1,4};
    codol_mounted_xanim_t result={0}; archive_t *archive; const uint8_t *h,*delta;
    size_t pos=88; unsigned i;
    if(!name || !*name || !out) return -1;
    archive=find_dependency_definition(2,name,&result.asset); if(!archive) return 0;
    if(result.asset.size<pos) return -1;
    h=result.asset.data;
    if(!weapon_string(archive,&result.asset,&pos,world_u32(h),&result.name)) return -1;
    result.bone_count=h[26]; result.notify_count=h[27]; result.index_width=xanim_u16(h+14)<256 ? 1 : 2;
    if(world_u32(h+48) && !xanim_take(&result.asset,&pos,result.bone_count,2,&result.bone_indices)) return -1;
    if(world_u32(h+80) && !xanim_take(&result.asset,&pos,result.notify_count,8,&result.notifies)) return -1;
    if(world_u32(h+84)) {
        if(!xanim_take(&result.asset,&pos,1,12,&delta)) return -1;
        for(i=0;i<3;++i) if(world_u32(delta+4*i)) {
            codol_xanim_track_t *track=result.tracks+i;
            if(!xanim_take(&result.asset,&pos,1,4,&track->header)) return -1;
            track->count=xanim_u16(track->header);
            track->frame_stride=i==0 ? (track->header[2] ? 3 : 6) : i==1 ? 4 : 8;
            if(!track->count) {
                if(!xanim_take(&result.asset,&pos,1,i==0 ? 12 : i==1 ? 4 : 8,&track->frames)) return -1;
            } else {
                if(!xanim_take(&result.asset,&pos,1,i==0 ? 28 : 4,&track->metadata) ||
                   !xanim_take(&result.asset,&pos,track->count+1,result.index_width,&track->indices)) return -1;
                if(world_u32(track->metadata+(i==0 ? 24 : 0)) &&
                   !xanim_take(&result.asset,&pos,track->count+1,track->frame_stride,&track->frames)) return -1;
            }
        }
    }
    for(i=0;i<6;++i) {
        result.stream_counts[i]=i==3 ? world_u32(h+offsets[i]) : xanim_u16(h+offsets[i]);
        if(world_u32(h+52+4*i) && !xanim_take(&result.asset,&pos,result.stream_counts[i],widths[i],result.streams+i)) return -1;
    }
    result.index_count=world_u32(h+36);
    if(world_u32(h+76) && !xanim_take(&result.asset,&pos,result.index_count,result.index_width,&result.indices)) return -1;
    if(pos!=result.asset.size) return -1;
    if(!archive->script_strings && !CODOL_ReadScriptStrings(&archive->zone,&archive->script_strings)) return -1;
    result.script_strings=archive->script_strings; result.script_string_count=archive->zone.string_count;
    *out=result; return 1;
}
int CODOL_BindMountedXAnimHandles(const char *name,codol_xanim_string_acquire_t acquire,
    codol_xanim_string_release_t release,void *context,const codol_xanim_handles_t **out)
{
    codol_mounted_xanim_t source; codol_asset_t definition; archive_t *archive;
    xanim_strings_t *cached; const char *names[510]; unsigned total,i,handle; int status;
    if(!out || !acquire || !release) return -1;
    status=CODOL_LoadMountedXAnim(name,&source); if(status!=1) return status;
    archive=find_dependency_definition(2,name,&definition); if(!archive) return -1;
    for(cached=archive->xanim_strings;cached;cached=cached->next)
        if(cached->definition==source.asset.data && cached->acquire==acquire && cached->release==release && cached->context==context) {
            *out=&cached->handles; return 1;
        }
    if(source.bone_count>255 || source.notify_count>255 ||
        (source.bone_count && !source.bone_indices) || (source.notify_count && !source.notifies)) return -1;
    total=source.bone_count+source.notify_count;
    for(i=0;i<total;++i) {
        unsigned index=xanim_u16(i<source.bone_count ? source.bone_indices+2*i : source.notifies+8*(i-source.bone_count));
        if(!source.script_strings || index>=source.script_string_count || !source.script_strings[index].text) return -1;
        names[i]=source.script_strings[index].text;
    }
    cached=calloc(1,sizeof(*cached)); if(!cached) return -1;
    for(i=0;i<total;++i) {
        handle=acquire(context,names[i]);
        if(!handle || handle>UINT16_MAX) {
            if(handle) release(context,handle);
            while(i) { --i; release(context,i<source.bone_count ? cached->handles.bones[i] : cached->handles.notifies[i-source.bone_count]); }
            free(cached); return -1;
        }
        if(i<source.bone_count) cached->handles.bones[i]=(uint16_t)handle;
        else cached->handles.notifies[i-source.bone_count]=(uint16_t)handle;
    }
    cached->handles.bone_count=source.bone_count; cached->handles.notify_count=source.notify_count;
    cached->definition=source.asset.data; cached->acquire=acquire; cached->release=release; cached->context=context;
    cached->next=archive->xanim_strings; archive->xanim_strings=cached;
    *out=&cached->handles; return 1;
}
int CODOL_LoadMountedNativeXAnim(const char *name,codol_xanim_string_acquire_t acquire,
    codol_xanim_string_release_t release,void *context,const struct XAnimParts **out)
{
    codol_mounted_xanim_t source; codol_asset_t definition; archive_t *archive;
    const codol_xanim_handles_t *handles; xanim_strings_t *cached; int status;
    if(!out || !acquire || !release) return -1;
    status=CODOL_LoadMountedXAnim(name,&source); if(status!=1) return status;
    status=CODOL_BindMountedXAnimHandles(name,acquire,release,context,&handles);
    if(status!=1) return status;
    archive=find_dependency_definition(2,name,&definition); if(!archive) return -1;
    for(cached=archive->xanim_strings;cached;cached=cached->next) {
        if(&cached->handles!=handles) continue;
        if(!cached->native.parts && !CODOL_BuildNativeXAnim(&source,handles,&cached->native)) return -1;
        *out=cached->native.parts; return 1;
    }
    return -1;
}
static int weapon_sound(const archive_t *,const codol_asset_t *,size_t *,int,uint32_t,const char **);
static int vehicle_dependency(const archive_t *archive,const codol_asset_t *vehicle,
    size_t *pos,unsigned type,uint32_t reference,codol_asset_t *out,const char **name)
{
    codol_asset_t source={0};
    archive_t *owner;
    const char *source_name;
    if(!reference) return 1;
    if(reference>=UINT32_MAX-1) {
        size_t i;
        if(*pos>=vehicle->size) return 0;
        for(i=0;i<archive->blocks.asset_alias_count;++i) {
            const codol_asset_t *candidate=&archive->blocks.asset_aliases[i].asset;
            if(candidate->type==type && candidate->data==vehicle->data+*pos) {
                source=*candidate; break;
            }
        }
        if(!source.size || source.size>vehicle->size-*pos) return 0;
        *pos+=source.size;
    } else if(type==28) {
        if(!CODOL_ResolveWeaponAlias(&archive->blocks,reference,&source)) return 0;
    } else if(type==5) {
        if(!CODOL_ResolveMaterialAlias(&archive->blocks,reference,&source)) return 0;
    } else return 0;
    source_name=dependency_asset_name(archive,&source);
    if(!source_name || !*source_name) return 0;
    owner=find_dependency_definition(type,source_name[0]==',' ? source_name+1 : source_name,out);
    if(!owner) return 0;
    *name=dependency_asset_name(owner,out);
    return *name && **name;
}
int CODOL_LoadMountedVehicle(const char *name,codol_mounted_vehicle_t *out)
{
    codol_mounted_vehicle_t result={0};
    archive_t *archive;
    uint32_t reference;
    unsigned i;
    static const unsigned sound_offsets[]={0x1e0,0x1e4,0x1e8,0x1ec,0x1f4,0x1fc,
        0x200,0x204,0x208,0x210,0x218,0x220,0x228,0x230};
    size_t pos=0x314;
    if(!name || !*name || !out) return -1;
    archive=find_dependency_definition(41,name,&result.asset);
    if(!archive) return 0;
    if(result.asset.size<pos) return -1;
    if(!weapon_string(archive,&result.asset,&pos,world_u32(result.asset.data),&result.name) ||
       !weapon_string(archive,&result.asset,&pos,world_u32(result.asset.data+8),&result.prefix_strings[0]) ||
       !weapon_string(archive,&result.asset,&pos,world_u32(result.asset.data+0xac),&result.prefix_strings[1]) ||
       !result.name || !*result.name) return -1;
    reference=world_u32(result.asset.data+0xb0);
    if(reference) {
        codol_asset_t preset={0};
        const char *preset_name;
        archive_t *owner;
        if(reference>=UINT32_MAX-1) {
            size_t i;
            /* Replay retained the exact nested extent. Advance over the
             * original bytes before resolving a newer named definition. */
            if(pos>=result.asset.size) return -1;
            for(i=0;i<archive->blocks.asset_alias_count;++i) {
                const codol_asset_t *candidate=&archive->blocks.asset_aliases[i].asset;
                if(candidate->type==0 && candidate->data==result.asset.data+pos) {
                    preset=*candidate; break;
                }
            }
            if(!preset.size || preset.size>result.asset.size-pos) return -1;
            pos+=preset.size;
        } else if(!CODOL_ResolvePhysicsAlias(&archive->blocks,0,reference,&preset)) return -1;
        preset_name=dependency_asset_name(archive,&preset);
        if(!preset_name || !*preset_name) return -1;
        owner=find_dependency_definition(0,preset_name[0]==',' ? preset_name+1 : preset_name,
            &result.physics_preset);
        if(!owner) return -1;
        result.physics_preset_name=dependency_asset_name(owner,&result.physics_preset);
        if(!result.physics_preset_name || !*result.physics_preset_name) return -1;
    }
    if(!weapon_string(archive,&result.asset,&pos,world_u32(result.asset.data+0xb4),
        &result.physics_profile)) return -1;
    if(!weapon_string(archive,&result.asset,&pos,world_u32(result.asset.data+0x190),
        &result.string190) || !vehicle_dependency(archive,&result.asset,&pos,28,
        world_u32(result.asset.data+0x194),&result.weapon,&result.weapon_name)) return -1;
    for(i=0;i<2;++i)
        if(!weapon_sound(archive,&result.asset,&pos,0,world_u32(result.asset.data+0x1ac+4*i),
            &result.sounds[i])) return -1;
    for(i=0;i<2;++i)
        if(!vehicle_dependency(archive,&result.asset,&pos,5,world_u32(result.asset.data+0x1d0+4*i),
            &result.materials[i],&result.material_names[i])) return -1;
    for(i=0;i<14;++i)
        if(!weapon_sound(archive,&result.asset,&pos,0,world_u32(result.asset.data+sound_offsets[i]),
            &result.sounds[2+i])) return -1;
    if(!weapon_string(archive,&result.asset,&pos,world_u32(result.asset.data+0x238),
        &result.string238)) return -1;
    for(i=0;i<31;++i)
        if(!weapon_sound(archive,&result.asset,&pos,0,world_u32(result.asset.data+0x23c+4*i),
            &result.sounds[16+i])) return -1;
    if(pos!=result.asset.size) return -1;
    result.dependency_offset=pos;
    *out=result;
    return 1;
}
int CODOL_LoadMountedWeapon(const char *name,codol_mounted_weapon_t *out)
{
    codol_mounted_weapon_t result={0}; archive_t *archive; unsigned i;
    size_t pos=0xbfc;
    if (!name || !*name || !out) return -1;
    archive=find_dependency_definition(28,name,&result.asset); if (!archive) return 0;
    if (result.asset.size<pos) return -1;
    for (i=0;i<4;++i)
        if (!weapon_string(archive,&result.asset,&pos,world_u32(result.asset.data+4*i),result.strings+i)) return -1;
    if (!result.strings[0] || !*result.strings[0]) return -1;
    result.dependency_offset=pos;
    *out=result; return 1;
}
int CODOL_LoadMountedWeaponHideTags(const char *name,codol_weapon_hide_tags_t *out)
{
    codol_mounted_weapon_t weapon; codol_weapon_hide_tags_t result={0};
    archive_t *archive; codol_asset_t definition; unsigned i; int status;
    if(!out) return -1;
    status=CODOL_LoadMountedWeapon(name,&weapon); if(status!=1) return status;
    archive=find_dependency_definition(28,name,&definition); if(!archive) return -1;
    /* C1 hide-tag consumer 0x422847/0x422852 selects def+3c. Serialized
     * script-string IDs belong to this zone, not the engine's SL table. */
    for(i=0;i<32;++i) {
        const uint8_t *p=weapon.asset.data+0x3c+2*i;
        unsigned index=(unsigned)p[0]|(unsigned)p[1]<<8;
        if(!index) continue;
        if(!archive->script_strings && !CODOL_ReadScriptStrings(&archive->zone,&archive->script_strings)) return -1;
        if(index>=archive->zone.string_count || !archive->script_strings[index].text ||
           !*archive->script_strings[index].text) return -1;
        result.names[i]=archive->script_strings[index].text;
    }
    *out=result; return 1;
}
static const codol_native_weapon_core_t *CODOL_FindNativeWeaponQueryCore(const struct WeaponDef *definition)
{
    archive_t *archive; native_weapon_cache_t *cached; unsigned generation;
    if(!definition) return NULL;
    for(generation=0;generation<2;++generation)
        for(archive=generation ? retired_archives : archives;archive;archive=archive->next) {
            if(archive->null_weapon && definition==&archive->null_weapon->definition)
                return archive->null_weapon;
            for(cached=archive->native_weapons;cached;cached=cached->next)
                if(definition==&cached->core.definition) return &cached->core;
        }
    return CODOL_ComposedWeaponCore(definition);
}
int CODOL_GetNativeWeaponClass(const struct WeaponDef *definition,unsigned *out)
{
    const codol_native_weapon_core_t *core=CODOL_FindNativeWeaponQueryCore(definition);
    if(!core || !out || core->source_weapon_class>=12)return 0;
    *out=core->source_weapon_class;
    return 1;
}
int CODOL_GetNativeBombWeapon(const struct WeaponDef *definition,codol_bomb_weapon_t *out)
{
    const codol_native_weapon_core_t *core=CODOL_FindNativeWeaponQueryCore(definition);
    if(!core || !out)return 0;
    *out=core->bomb;
    return 1;
}
int CODOL_GetNativeWeaponMissileStickiness(const struct WeaponDef *definition,
    codol_missile_stickiness_t *out)
{
    const codol_native_weapon_core_t *core=CODOL_FindNativeWeaponQueryCore(definition);
    if(!core || !out) return 0;
    *out=core->missile_stickiness;
    return 1;
}
int CODOL_GetNativeWeaponBounce(const struct WeaponDef *definition,unsigned surface,float out[2])
{
    const codol_native_weapon_core_t *core;
    if(!out || surface>=CODOL_WEAPON_BOUNCE_SURFACES) return 0;
    core=CODOL_FindNativeWeaponQueryCore(definition);
    if(!core) return 0;
    out[0]=core->bounce.parallel[surface];
    out[1]=core->bounce.perpendicular[surface];
    return 1;
}
int CODOL_GetNativeWeaponRolling(const struct WeaponDef *definition,int *enabled)
{
    const codol_native_weapon_core_t *core=CODOL_FindNativeWeaponQueryCore(definition);
    if(!core || !enabled) return 0;
    *enabled=core->bounce.rolling;
    return 1;
}
int CODOL_LoadMountedWeaponAttachment(const char *name,codol_mounted_weapon_attachment_t *out)
{
    codol_mounted_weapon_attachment_t result={0}; archive_t *archive;
    const uint8_t *h; size_t pos=12; uint32_t i;
    if(!name || !*name || !out) return -1;
    archive=find_dependency_definition(43,name,&result.asset); if(!archive) return 0;
    if(result.asset.size<pos) return -1;
    h=result.asset.data;
    if(!weapon_string(archive,&result.asset,&pos,world_u32(h),&result.name)) return -1;
    if(!result.name || !*result.name) return -1;
    result.count=world_u32(h+4);
    /* C1 0x4c3e59 reads the entry array only when the pointer field is set;
     * 0x4c3d00 then walks exactly count twelve-byte entries and resolves the
     * value of every kind below 16, plus kind 39, as an XString. */
    if(!world_u32(h+8)) {
        if(result.count || pos!=result.asset.size) return -1;
        *out=result; return 1;
    }
    if(result.count>INT32_MAX || pos>result.asset.size ||
       (result.asset.size-pos)/12<result.count) return -1;
    result.entries=result.asset.data+pos; pos+=12*(size_t)result.count;
    if(result.count && !(result.texts=calloc(result.count,sizeof(*result.texts)))) return -1;
    for(i=0;i<result.count;++i) {
        uint32_t type=world_u32(result.entries+12*i+4);
        if(!(type<16 || type>INT32_MAX || type==39)) continue;
        if(!weapon_string(archive,&result.asset,&pos,world_u32(result.entries+12*i+8),result.texts+i)) {
            free((void *)result.texts); return -1;
        }
    }
    if(pos!=result.asset.size) { free((void *)result.texts); return -1; }
    *out=result; return 1;
}
void CODOL_FreeMountedWeaponAttachment(codol_mounted_weapon_attachment_t *attachment)
{
    if(!attachment) return;
    free((void *)attachment->texts);
    memset(attachment,0,sizeof(*attachment));
}
int CODOL_GetNativeWeaponDetonateTrigger(const struct WeaponDef *definition,int *out)
{
    const codol_native_weapon_core_t *core=CODOL_FindNativeWeaponQueryCore(definition);
    if(!core || !out) return 0;
    *out=core->detonate_trigger; return 1;
}
int CODOL_GetNativeWeaponRequiresGround(const struct WeaponDef *definition,int *out)
{
    const codol_native_weapon_core_t *core=CODOL_FindNativeWeaponQueryCore(definition);
    if(!core || !out) return 0;
    *out=core->requires_ground; return 1;
}
int CODOL_GetNativeWeaponHideTags(const struct WeaponDef *definition,const codol_weapon_hide_tag_handles_t **out)
{
    const codol_native_weapon_core_t *core=CODOL_FindNativeWeaponQueryCore(definition);
    if(!core || !out) return 0;
    *out=&core->hide_tags; return 1;
}
int CODOL_GetNativeWeaponSilenced(const struct WeaponDef *definition,int *out)
{
    const codol_native_weapon_core_t *core=CODOL_FindNativeWeaponQueryCore(definition);
    if(!core || !out) return 0;
    *out=core->silenced!=0; return 1;
}
int CODOL_GetNativeWeaponScriptMods(const struct WeaponDef *definition,const char **out)
{
    const codol_native_weapon_core_t *core=CODOL_FindNativeWeaponQueryCore(definition);
    if(!core || !out) return 0;
    *out=core->script_mods ? core->script_mods : ""; return 1;
}
int CODOL_GetNativeWeaponScriptFlag(const struct WeaponDef *definition,codol_weapon_script_flag_t flag,int *out)
{
    const codol_native_weapon_core_t *core=CODOL_FindNativeWeaponQueryCore(definition);
    if(!core || !out) return 0;
    switch(flag) {
    case CODOL_WEAPON_SCRIPT_FLAG_THERMAL_SCOPE: *out=core->thermal_scope; return 1;
    case CODOL_WEAPON_SCRIPT_FLAG_HPBT: *out=core->hpbt; return 1;
    case CODOL_WEAPON_SCRIPT_FLAG_GPS: *out=core->gps; return 1;
    case CODOL_WEAPON_SCRIPT_FLAG_ID_LOCK: *out=core->id_lock; return 1;
    }
    return 0;
}
int CODOL_GetNativeWeaponHoldPin(const struct WeaponDef *definition,int *out)
{
    const codol_native_weapon_core_t *core=CODOL_FindNativeWeaponQueryCore(definition);
    if(!core || !out) return 0;
    *out=core->hold_pin; return 1;
}
int CODOL_GetNativeWeaponZoomFov(const struct WeaponDef *definition,float out[3])
{
    const codol_native_weapon_core_t *core=CODOL_FindNativeWeaponQueryCore(definition);
    if(!core || !out) return 0;
    memcpy(out,core->zoom_fov,sizeof core->zoom_fov); return 1;
}
int CODOL_GetNativeWeaponOffhandCancel(const struct WeaponDef *definition,int *out)
{
    const codol_native_weapon_core_t *core=CODOL_FindNativeWeaponQueryCore(definition);
    if(!core || !out) return 0;
    *out=core->offhand_cancel; return 1;
}
int CODOL_GetNativeWeaponUnlimitedAmmo(const struct WeaponDef *definition,int *out)
{
    const codol_native_weapon_core_t *core=CODOL_FindNativeWeaponQueryCore(definition);
    if(!core || !out) return 0;
    *out=core->unlimited_ammo; return 1;
}
int CODOL_GetNativeWeaponSpinUp(const struct WeaponDef *definition,int *up_ms,int *down_ms)
{
    const codol_native_weapon_core_t *core=CODOL_FindNativeWeaponQueryCore(definition);
    if(!core || !up_ms || !down_ms) return 0;
    *up_ms=core->timings.spin_up;
    *down_ms=core->timings.spin_down; return 1;
}
int CODOL_GetNativeWeaponRechamberDualWield(const struct WeaponDef *definition,int *out)
{
    const codol_native_weapon_core_t *core=CODOL_FindNativeWeaponQueryCore(definition);
    if(!core || !out) return 0;
    *out=core->timings.rechamber_variant; return 1;
}
int CODOL_GetNativeWeaponDualWield(const struct WeaponDef *definition,int *out)
{
    const codol_native_weapon_core_t *core=CODOL_FindNativeWeaponQueryCore(definition);
    if(!core || !out) return 0;
    *out=core->dual_wield; return 1;
}
int CODOL_GetNativeWeaponRiotShield(const struct WeaponDef *definition,int *out)
{
    const codol_native_weapon_core_t *core=CODOL_FindNativeWeaponQueryCore(definition);
    if(!core || !out) return 0;
    *out=core->riot_shield; return 1;
}
int CODOL_GetNativeWeaponAdsReload(const struct WeaponDef *definition,int *out)
{
    const codol_native_weapon_core_t *core=CODOL_FindNativeWeaponQueryCore(definition);
    if(!core || !out) return 0;
    *out=core->ads_reload; return 1;
}
int CODOL_GetNativeWeaponReloadData(const struct WeaponDef *definition,int *dual_mag,
    codol_weapon_timing_extensions_t *timings)
{
    const codol_native_weapon_core_t *core=CODOL_FindNativeWeaponQueryCore(definition);
    if(!core || !dual_mag || !timings) return 0;
    *dual_mag=core->dual_mag;
    *timings=core->timings;
    return 1;
}
int CODOL_GetNativeWeaponAnimationName(const struct WeaponDef *definition,unsigned slot,
    const char **out)
{
    const codol_native_weapon_core_t *core=CODOL_FindNativeWeaponQueryCore(definition);
    if(!core || !out || slot>=144) return 0;
    *out=core->animations.names[slot];
    return 1;
}
int CODOL_GetNativeWeaponInheritsPerks(const struct WeaponDef *definition,int *out)
{
    const codol_native_weapon_core_t *core=CODOL_FindNativeWeaponQueryCore(definition);
    if(!core || !out) return 0;
    *out=core->inherits_perks; return 1;
}
int CODOL_GetNativeWeaponLockWarningGate(const struct WeaponDef *definition,int *out)
{
    const codol_native_weapon_core_t *core=CODOL_FindNativeWeaponQueryCore(definition);
    if(!core || !out) return 0;
    *out=core->lock_warning_gate; return 1;
}
static const char *structured_string(void *context,uint32_t reference)
{ return CODOL_LoadBlockString(&((archive_t *)context)->blocks,reference); }
int CODOL_LoadMountedStructuredSchema(const char *name,codol_structured_schema_t *out)
{
    codol_asset_t asset; archive_t *archive;
    if(!name || !*name || !out)return -1;
    archive=find_dependency_definition(39,name,&asset);if(!archive)return 0;
    return CODOL_ReadStructuredSchema(&asset,structured_string,archive,out) ? 1 : -1;
}
int CODOL_LoadMountedNativeWeapon(const char *name,
    int (*build)(const char *,codol_native_weapon_core_t *),const struct WeaponDef **out)
{
    codol_asset_t definition; archive_t *archive;
    native_weapon_cache_t *cached;
    if(!name || !*name || !build || !out) return -1;
    archive=find_dependency_definition(28,name,&definition); if(!archive) return 0;
    for(cached=archive->native_weapons;cached;cached=cached->next)
        if(cached->definition==definition.data) { *out=&cached->core.definition; return 1; }
    cached=calloc(1,sizeof(*cached)); if(!cached) return -1;
    if(build(name,&cached->core)!=1) { CODOL_FreeNativeWeaponCore(&cached->core); free(cached); return -1; }
    cached->definition=definition.data; cached->next=archive->native_weapons;
    archive->native_weapons=cached; *out=&cached->core.definition; return 1;
}
int CODOL_LoadMountedDefaultWeapon(const char *name,
    int (*build)(const char *,codol_native_weapon_core_t *),const struct WeaponDef **out)
{
    if(!name || !*name || !build || !out) return -1;
    if(!asset_name_equal(name,"defaultweapon_mp")) return 0;
    return CODOL_LoadMountedNativeWeapon(name,build,out);
}
int CODOL_LoadMountedNullWeapon(const char *name,const struct WeaponDef **out)
{
    codol_mounted_weapon_t source; codol_asset_t definition; archive_t *archive;
    codol_weapon_animations_t animations; codol_weapon_ammo_names_t ammo; codol_weapon_tail_t tail;
    codol_native_weapon_core_t *native; int status;
    if(!name || !*name || !out) return -1;
    if(!asset_name_equal(name,"none")) return 0;
    status=CODOL_LoadMountedWeapon(name,&source); if(status!=1) return status;
    archive=find_dependency_definition(28,name,&definition); if(!archive) return -1;
    if(archive->null_weapon) { *out=&archive->null_weapon->definition; return 1; }
    if(CODOL_LoadMountedWeaponAnimations(name,&animations)!=1 || CODOL_LoadMountedWeaponAmmoNames(name,&ammo)!=1 ||
       CODOL_LoadMountedWeaponTail(name,&tail)!=1) return -1;
    native=calloc(1,sizeof(*native)); if(!native) return -1;
    if(!CODOL_BuildNativeNullWeapon(&source,&animations,&ammo,&tail,native)) { free(native); return -1; }
    archive->null_weapon=native; *out=&native->definition; return 1;
}
int CODOL_BindMountedWeaponHideTags(const char *name,codol_xanim_string_acquire_t acquire,
    codol_xanim_string_release_t release,void *context,const codol_weapon_hide_tag_handles_t **out)
{
    codol_weapon_hide_tags_t source; codol_asset_t definition; archive_t *archive;
    weapon_tags_t *cached; unsigned i,handle; int status;
    if(!out || !acquire || !release) return -1;
    /* Validate every archive string before acquiring any engine references. */
    status=CODOL_LoadMountedWeaponHideTags(name,&source); if(status!=1) return status;
    archive=find_dependency_definition(28,name,&definition); if(!archive) return -1;
    for(cached=archive->weapon_tags;cached;cached=cached->next)
        if(cached->definition==definition.data && cached->acquire==acquire &&
           cached->release==release && cached->context==context) {
            *out=&cached->handles; return 1;
        }
    cached=calloc(1,sizeof(*cached)); if(!cached) return -1;
    for(i=0;i<32;++i) {
        if(!source.names[i]) continue;
        handle=acquire(context,source.names[i]);
        if(!handle || handle>UINT16_MAX) {
            if(handle) release(context,handle);
            while(i) { --i; if(cached->handles.tags[i]) release(context,cached->handles.tags[i]); }
            free(cached); return -1;
        }
        cached->handles.tags[i]=(uint16_t)handle;
    }
    cached->definition=definition.data; cached->acquire=acquire;
    cached->release=release; cached->context=context;
    cached->next=archive->weapon_tags; archive->weapon_tags=cached;
    *out=&cached->handles; return 1;
}
int CODOL_LoadMountedWeaponModel(const char *name,unsigned index,codol_weapon_model_t *out)
{
    codol_mounted_weapon_t weapon; codol_weapon_model_t result={0};
    archive_t *archive; codol_asset_t definition; size_t pos; unsigned i; int status;
    if (!out || index>=11) return -1;
    status=CODOL_LoadMountedWeapon(name,&weapon); if (status!=1) return status;
    archive=find_dependency_definition(28,name,&definition); if (!archive) return -1;
    pos=weapon.dependency_offset;
    for (i=0;i<=index;++i) {
        uint32_t ref=world_u32(weapon.asset.data+0x10+4*i);
        codol_asset_t model={0};
        if (ref>=UINT32_MAX-1) {
            size_t extent;
            if (pos>weapon.asset.size) return -1;
            model=(codol_asset_t){4,weapon.asset.data+pos,weapon.asset.size-pos};
            if (!CODOL_ReadXModelExtent(&model,&extent)) return -1;
            model.size=extent; pos+=extent;
        } else if (i==index) {
            if (!ref) return 0;
            if (!CODOL_ResolveModelAlias(&archive->blocks,ref,&model)) return -1;
        }
        if (i!=index) continue;
        result.name=dependency_asset_name(archive,&model);
        if (!result.name || !*result.name) return -1;
        archive=find_dependency_definition(4,result.name[0]==',' ? result.name+1 : result.name,&result.asset);
        if (!archive) return -1;
        result.name=dependency_asset_name(archive,&result.asset);
        if (!result.name || !*result.name) return -1;
        *out=result; return 1;
    }
    return -1;
}
int CODOL_LoadMountedWeaponAnimations(const char *name,codol_weapon_animations_t *out)
{
    codol_mounted_weapon_t weapon; codol_weapon_animations_t result={0};
    archive_t *archive; codol_asset_t definition; size_t pos; unsigned i; int status;
    if (!out) return -1;
    status=CODOL_LoadMountedWeapon(name,&weapon); if (status!=1) return status;
    archive=find_dependency_definition(28,name,&definition); if (!archive) return -1;
    pos=weapon.dependency_offset;
    for (i=0;i<11;++i) if (world_u32(weapon.asset.data+0x10+4*i)>=UINT32_MAX-1) {
        codol_asset_t model; size_t extent;
        if (pos>weapon.asset.size) return -1;
        model=(codol_asset_t){4,weapon.asset.data+pos,weapon.asset.size-pos};
        if (!CODOL_ReadXModelExtent(&model,&extent)) return -1;
        pos+=extent;
    }
    for (i=0;i<144;++i)
        if (!weapon_string(archive,&weapon.asset,&pos,world_u32(weapon.asset.data+0x7c+4*i),result.names+i)) return -1;
    result.dependency_offset=pos; *out=result; return 1;
}
int CODOL_LoadMountedWeaponEffects(const char *name,codol_weapon_effects_t *out)
{
    codol_mounted_weapon_t weapon; codol_weapon_animations_t animations;
    codol_weapon_effects_t result={0}; archive_t *archive,*owner;
    codol_asset_t definition; size_t pos; unsigned i; int status;
    if (!out) return -1;
    status=CODOL_LoadMountedWeapon(name,&weapon); if (status!=1) return status;
    status=CODOL_LoadMountedWeaponAnimations(name,&animations); if (status!=1) return status;
    archive=find_dependency_definition(28,name,&definition); if (!archive) return -1;
    pos=animations.dependency_offset;
    for (i=0;i<2;++i) {
        uint32_t ref=world_u32(weapon.asset.data+0x35c+4*i);
        codol_asset_t effect={0}; const char *effect_name;
        if (!ref) continue;
        if (ref>=UINT32_MAX-1) {
            size_t j;
            if (pos>=weapon.asset.size) return -1;
            /* Complete replay records exact source extents, including nested
             * dependencies. Advance over the original before named override. */
            for (j=0;j<archive->blocks.asset_alias_count;++j) {
                const codol_asset_t *candidate=&archive->blocks.asset_aliases[j].asset;
                if (candidate->type==30 && candidate->data==weapon.asset.data+pos) { effect=*candidate; break; }
            }
            if (!effect.size || effect.size>weapon.asset.size-pos) return -1;
            pos+=effect.size;
        } else if (!CODOL_ResolveEffectAlias(&archive->blocks,ref,&effect)) return -1;
        effect_name=dependency_asset_name(archive,&effect);
        if (!effect_name || !*effect_name) return -1;
        owner=find_dependency_definition(30,effect_name[0]==',' ? effect_name+1 : effect_name,result.assets+i);
        if (!owner) return -1;
        result.names[i]=dependency_asset_name(owner,result.assets+i);
        if (!result.names[i] || !*result.names[i]) return -1;
    }
    result.dependency_offset=pos; *out=result; return 1;
}
static int weapon_sound(const archive_t *archive,const codol_asset_t *asset,size_t *pos,
    int pooled,uint32_t ref,const char **out)
{
    uint32_t string;
    if(!ref) { *out=NULL; return 1; }
    if(ref==UINT32_MAX) {
        /* Serialized bytes have no padding; replayed block-3 wrappers align
         * to four bytes, including those following an odd-length name. */
        if(pooled) *pos=(*pos+3)&~(size_t)3;
        if(*pos>asset->size || asset->size-*pos<4) return 0;
        string=world_u32(asset->data+*pos); *pos+=4;
        return weapon_string(archive,asset,pos,string,out);
    } else {
        size_t offset=(ref-1)&0xfffffff,pooled_pos;
        codol_asset_t pool={0,archive->blocks.data[3],archive->blocks.written[3]};
        if(((ref-1)>>28)!=3 || offset>pool.size || pool.size-offset<4) return 0;
        string=world_u32(pool.data+offset); pooled_pos=offset+4;
        return weapon_string(archive,&pool,&pooled_pos,string,out);
    }
}
int CODOL_LoadMountedWeaponSounds(const char *name,codol_weapon_sounds_t *out)
{
    codol_mounted_weapon_t weapon; codol_weapon_effects_t effects;
    codol_weapon_sounds_t result={0}; archive_t *archive; codol_asset_t definition;
    size_t pos; unsigned i; int status;
    if (!out) return -1;
    status=CODOL_LoadMountedWeapon(name,&weapon); if(status!=1) return status;
    status=CODOL_LoadMountedWeaponEffects(name,&effects); if(status!=1) return status;
    archive=find_dependency_definition(28,name,&definition); if(!archive) return -1;
    pos=effects.dependency_offset;
    for(i=0;i<53;++i)
        if(!weapon_sound(archive,&weapon.asset,&pos,0,world_u32(weapon.asset.data+0x364+4*i),result.names+i)) return -1;
    for(i=0;i<2;++i) {
        uint32_t ref=world_u32(weapon.asset.data+0x438+4*i);
        codol_asset_t array=weapon.asset; size_t cursor=pos,start; unsigned j; int pooled=ref!=UINT32_MAX;
        if(!ref) continue;
        if(pooled) {
            if(((ref-1)>>28)!=3) return -1;
            array=(codol_asset_t){0,archive->blocks.data[3],archive->blocks.written[3]}; cursor=(ref-1)&0xfffffff;
        }
        if(cursor>array.size || array.size-cursor<31*4) return -1;
        start=cursor; cursor+=31*4;
        for(j=0;j<31;++j)
            if(!weapon_sound(archive,&array,&cursor,pooled,world_u32(array.data+start+4*j),result.arrays[i]+j)) return -1;
        if(!pooled) pos=cursor;
    }
    result.dependency_offset=pos; *out=result; return 1;
}
int CODOL_LoadMountedWeaponVisuals(const char *name,codol_weapon_visuals_t *out)
{
    static const unsigned dependencies[][3]={{0x440,4,30},{0x450,2,5},{0x52c,6,5},{0x548,1,5},{0x550,1,5}};
    codol_mounted_weapon_t weapon; codol_weapon_sounds_t sounds;
    codol_weapon_visuals_t result={0}; archive_t *archive; codol_asset_t definition;
    size_t pos; unsigned i,j,index=0; int status;
    if(!out) return -1;
    status=CODOL_LoadMountedWeapon(name,&weapon); if(status!=1) return status;
    status=CODOL_LoadMountedWeaponSounds(name,&sounds); if(status!=1) return status;
    archive=find_dependency_definition(28,name,&definition); if(!archive) return -1;
    pos=sounds.dependency_offset;
    for(i=0;i<sizeof(dependencies)/sizeof(dependencies[0]);++i)
        for(j=0;j<dependencies[i][1];++j) {
            codol_weapon_dependency_t *entry=result.entries+index++;
            archive_t *owner; const char *asset_name;
            uint32_t ref=world_u32(weapon.asset.data+dependencies[i][0]+4*j);
            codol_asset_t asset={0}; size_t k;
            entry->offset=dependencies[i][0]+4*j; entry->kind=CODOL_WEAPON_DEP_ASSET;
            /* Keep the slot's type even when an attachment is the first
             * definition to supply its asset name. */
            entry->asset.type=dependencies[i][2];
            if(!ref) continue;
            if(ref>=UINT32_MAX-1) {
                if(pos>=weapon.asset.size) return -1;
                for(k=0;k<archive->blocks.asset_alias_count;++k) {
                    const codol_asset_t *candidate=&archive->blocks.asset_aliases[k].asset;
                    if(candidate->type==dependencies[i][2] && candidate->data==weapon.asset.data+pos) { asset=*candidate; break; }
                }
                if(!asset.size || asset.size>weapon.asset.size-pos) return -1;
                pos+=asset.size;
            } else if(!(dependencies[i][2]==30 ? CODOL_ResolveEffectAlias(&archive->blocks,ref,&asset) :
                CODOL_ResolveMaterialAlias(&archive->blocks,ref,&asset))) return -1;
            asset_name=dependency_asset_name(archive,&asset); if(!asset_name || !*asset_name) return -1;
            owner=find_dependency_definition(dependencies[i][2],asset_name[0]==',' ? asset_name+1 : asset_name,&entry->asset);
            if(!owner) return -1;
            entry->name=dependency_asset_name(owner,&entry->asset); if(!entry->name || !*entry->name) return -1;
        }
    result.dependency_offset=pos; *out=result; return 1;
}
int CODOL_LoadMountedWeaponAmmoNames(const char *name,codol_weapon_ammo_names_t *out)
{
    codol_mounted_weapon_t weapon; codol_weapon_visuals_t visuals;
    codol_weapon_ammo_names_t result={0}; archive_t *archive; codol_asset_t definition;
    size_t pos; int status;
    if(!out) return -1;
    status=CODOL_LoadMountedWeapon(name,&weapon); if(status!=1) return status;
    status=CODOL_LoadMountedWeaponVisuals(name,&visuals); if(status!=1) return status;
    archive=find_dependency_definition(28,name,&definition); if(!archive) return -1;
    pos=visuals.dependency_offset;
    if(!weapon_string(archive,&weapon.asset,&pos,world_u32(weapon.asset.data+0x564),&result.ammo) ||
       !weapon_string(archive,&weapon.asset,&pos,world_u32(weapon.asset.data+0x56c),&result.clip) ||
       !weapon_string(archive,&weapon.asset,&pos,world_u32(weapon.asset.data+0x57c),&result.shared_cap)) return -1;
    result.dependency_offset=pos; *out=result; return 1;
}
int CODOL_LoadMountedWeaponTail(const char *name,codol_weapon_tail_t *out)
{
    enum { S=CODOL_WEAPON_DEP_STRING,N=CODOL_WEAPON_DEP_SOUND,A=CODOL_WEAPON_DEP_ASSET,P=CODOL_WEAPON_DEP_POINTS };
    static const unsigned fields[][4]={
        {0x684,4,A,5},{0x758,1,A,1},{0x7b0,1,A,4},
        {0x7b8,2,A,30},{0x7c0,2,N,0},{0x8cc,2,A,30},
        {0x8ec,1,A,30},{0x8f0,1,N,0},{0x9a0,1,S,0},
        {0x9a8,1,P,0xbb0},{0x9a4,1,S,0},{0x9ac,1,P,0xbb2},
        {0x9fc,2,S,0},{0xa20,2,S,0},{0xaa0,2,S,0},
        {0xaa8,1,A,40},{0xac4,1,N,0},{0xac8,1,A,30},
        {0xacc,1,S,0},{0xadc,9,N,0},{0xb00,2,N,0},
        {0xb48,6,N,0},{0xb78,1,S,0},{0xb84,2,S,0},
        {0xb90,3,A,5},{0xbb4,2,P,0xbb0}
    };
    codol_mounted_weapon_t weapon; codol_weapon_ammo_names_t ammo;
    codol_weapon_tail_t result={0}; codol_asset_t definition; archive_t *archive;
    size_t pos; unsigned i,j; int status;
    if(!out) return -1;
    status=CODOL_LoadMountedWeapon(name,&weapon); if(status!=1) return status;
    status=CODOL_LoadMountedWeaponAmmoNames(name,&ammo); if(status!=1) return status;
    archive=find_dependency_definition(28,name,&definition); if(!archive) return -1;
    pos=ammo.dependency_offset;
    for(i=0;i<sizeof(fields)/sizeof(fields[0]);++i) for(j=0;j<fields[i][1];++j) {
        codol_weapon_dependency_t *entry; uint32_t ref;
        if(result.count>=64) return -1;
        entry=result.entries+result.count++; entry->offset=fields[i][0]+4*j; entry->kind=fields[i][2];
        if(entry->kind==A) entry->asset.type=fields[i][3];
        ref=world_u32(weapon.asset.data+entry->offset);
        if(!ref) continue;
        if(entry->kind==S) {
            if(!weapon_string(archive,&weapon.asset,&pos,ref,&entry->name)) return -1;
        } else if(entry->kind==N) {
            if(!weapon_sound(archive,&weapon.asset,&pos,0,ref,&entry->name)) return -1;
        } else if(entry->kind==P) {
            const uint8_t *base=weapon.asset.data; size_t size=weapon.asset.size,at=pos,k;
            entry->point_count=xanim_u16(weapon.asset.data+fields[i][3]+2*j);
            if(ref!=UINT32_MAX) {
                if(((ref-1)>>28)!=3) return -1;
                base=archive->blocks.data[3]; size=archive->blocks.written[3]; at=(ref-1)&0xfffffff;
            }
            if(at>size || entry->point_count>(size-at)/8) return -1;
            entry->points=base+at;
            for(k=0;k<(size_t)entry->point_count*2;++k) {
                uint32_t bits=world_u32(entry->points+4*k); float value; memcpy(&value,&bits,4);
                if(!isfinite(value)) return -1;
            }
            if(ref==UINT32_MAX) pos+=8*entry->point_count;
        } else {
            codol_asset_t original={0}; archive_t *owner; const char *asset_name; size_t k;
            for(k=0;k<archive->blocks.asset_alias_count;++k) {
                const codol_asset_alias_t *candidate=archive->blocks.asset_aliases+k;
                if(candidate->asset.type!=fields[i][3]) continue;
                if(ref>=UINT32_MAX-1 ? (pos<weapon.asset.size && candidate->asset.data==weapon.asset.data+pos) : candidate->reference==ref) {
                    original=candidate->asset; break;
                }
            }
            if(!original.data || !original.size) return -1;
            if(ref>=UINT32_MAX-1) { if(pos>weapon.asset.size || original.size>weapon.asset.size-pos) return -1; pos+=original.size; }
            asset_name=dependency_asset_name(archive,&original); if(!asset_name || !*asset_name) return -1;
            owner=find_dependency_definition(fields[i][3],asset_name[0]==',' ? asset_name+1 : asset_name,&entry->asset);
            if(!owner) return -1;
            entry->name=dependency_asset_name(owner,&entry->asset); if(!entry->name || !*entry->name) return -1;
        }
    }
    if(pos!=weapon.asset.size) return -1;
    result.dependency_offset=pos; *out=result; return 1;
}
static int world_string(const archive_t *archive,const codol_asset_t *asset,size_t *pos,uint32_t ref,const char **out)
{
    const uint8_t *p,*end; size_t available,offset,length; char *copy;
    if (!ref) { *out=NULL; return 1; }
    if (ref==UINT32_MAX) {
        if (*pos>asset->size) return 0;
        p=asset->data+*pos; available=asset->size-*pos;
    } else {
        if (((ref-1)>>28)!=3) return 0;
        offset=(ref-1)&0xfffffff;
        if (offset>=archive->blocks.written[3]) return 0;
        p=archive->blocks.data[3]+offset; available=archive->blocks.written[3]-offset;
    }
    end=memchr(p,0,available); if (!end) return 0;
    length=(size_t)(end-p)+1; copy=malloc(length); if (!copy) return 0;
    memcpy(copy,p,length); if (ref==UINT32_MAX) *pos+=length;
    *out=copy; return 1;
}
static void free_common_world(common_world_cache_t *cached)
{
    unsigned i;
    if (cached->world.primaryLights) for (i=0;i<cached->world.primaryLightCount;++i)
        free((void *)cached->world.primaryLights[i].defName);
    free(cached->world.primaryLights); free((void *)cached->world.name); free(cached);
}
int CODOL_LoadMountedGlassMap(const char *name,codol_glass_map_source_t *out)
{
    archive_t *ga,*fa;
    codol_asset_t game,fx;
    if (!name || !*name || !out) return -1;
    ga=find_dependency_definition(18,name,&game);
    if (!ga) return 0;
    fa=find_dependency_definition(20,name,&fx);
    if (!CODOL_ReadGlassMap(&ga->blocks,&game,fa?&fa->blocks:NULL,
        fa?&fx:NULL,out)) {
        Com_PrintWarning(CON_CHANNEL_SERVER,"CoDOL glass map %s: %s (game size %u, fx size %u)\n",
            name,CODOL_GlassMapFailure(),(unsigned)game.size,fa?(unsigned)fx.size:0u);
        return -1;
    }
    return 1;
}
int CODOL_LoadMountedGlassGroups(const char *name,const codol_glass_groups_t **out)
{
    archive_t *archive;
    codol_asset_t asset;
    glass_world_cache_t *cached;
    if(!name || !*name || !out) return -1;
    archive=find_dependency_definition(18,name,&asset);
    if(!archive) return 0;
    for(cached=archive->glass_worlds;cached;cached=cached->next)
        if(cached->definition==asset.data) { *out=&cached->groups; return 1; }
    cached=calloc(1,sizeof(*cached));
    if(!cached) return -1;
    if(!CODOL_LoadGlassGroups(&archive->blocks,&asset,&cached->groups)) {
        free(cached); return -1;
    }
    cached->definition=asset.data;
    cached->next=archive->glass_worlds;
    archive->glass_worlds=cached;
    *out=&cached->groups;
    return 1;
}
int CODOL_LoadEngineCommonWorld(const char *name,const struct ComWorld **out)
{
    archive_t *archive; codol_asset_t asset; common_world_cache_t *cached;
    const uint8_t *lights; size_t pos=16; unsigned i,j; uint32_t count;
    if (!name || !*name || !out) return -1;
    archive=find_dependency_definition(16,name,&asset); if (!archive) return 0;
    for (cached=archive->worlds;cached;cached=cached->next)
        if (cached->definition==asset.data) { *out=&cached->world; return 1; }
    if (asset.size<16 || world_u32(asset.data+4)>1) return -1;
    count=world_u32(asset.data+8);
    if (count>CODOL_ASSET_LIMIT/68 || (count && !world_u32(asset.data+12))) return -1;
    cached=calloc(1,sizeof(*cached)); if (!cached) return -1;
    if (!world_string(archive,&asset,&pos,world_u32(asset.data),&cached->world.name) ||
        !cached->world.name || !*cached->world.name) goto fail;
    if (count>(asset.size-pos)/68) goto fail;
    /* C1 4bff4c..4bff6e treats the light-array word as a presence flag:
     * every nonzero value loads a fresh aligned inline array. Unlike the
     * world/name strings, this word is not a packed block reference. The
     * replay layer consumes stream alignment; this asset view is contiguous. */
    lights=asset.data+pos; pos+=(size_t)count*68;
    cached->world.primaryLightCount=count;
    cached->world.isInUse=(int)world_u32(asset.data+4);
    if (count) {
        cached->world.primaryLights=calloc(count,sizeof(*cached->world.primaryLights));
        if (!cached->world.primaryLights) goto fail;
    }
    for (i=0;i<count;++i) {
        struct ComPrimaryLight *light=cached->world.primaryLights+i;
        const uint8_t *r=lights+68*i;
        for (j=4;j<64;j+=4) { float value; uint32_t bits=world_u32(r+j); memcpy(&value,&bits,4); if (!isfinite(value)) goto fail; }
        memcpy(light,r,64);
        if (!world_string(archive,&asset,&pos,world_u32(r+64),&light->defName)) goto fail;
    }
    if (pos!=asset.size) goto fail;
    cached->definition=asset.data; cached->next=archive->worlds; archive->worlds=cached;
    *out=&cached->world; return 1;
fail:
    free_common_world(cached); return -1;
}
int CODOL_LoadMountedEffectSource(const char *name,const codol_effect_source_t **out)
{
    archive_t *archive; codol_asset_t asset; effect_cache_t *cached; codol_model_block_t blocks[8];
    if(!name || !*name || *name==',' || !out) return -1;
    archive=find_dependency_definition(30,name,&asset); if(!archive) return 0;
    for(cached=archive->effects;cached;cached=cached->next)
        if(cached->definition==asset.data) { *out=&cached->source; return 1; }
    cached=calloc(1,sizeof(*cached)); if(!cached) return -1;
    CODOL_LoadBlockViews(&archive->blocks,blocks); blocks[0]=(codol_model_block_t){0};
    if(!CODOL_ReadEffectSource(&asset,blocks,&cached->source)) { free(cached); return -1; }
    cached->definition=asset.data; cached->archive=archive; cached->next=archive->effects; archive->effects=cached;
    *out=&cached->source; return 1;
}
int CODOL_LoadMountedEffectVisual(const char *name,unsigned element,unsigned index,codol_effect_visual_source_t *out)
{
    const codol_effect_source_t *source; const codol_effect_visual_t *visual;
    effect_cache_t *cached; archive_t *archive; codol_effect_visual_source_t result={0};
    unsigned type; int status;
    if(!out) return -1;
    status=CODOL_LoadMountedEffectSource(name,&source); if(status!=1) return status;
    if(element>=source->prefix.count || index>=source->elements[element].visual_count) return -1;
    type=source->elements[element].record[176]; visual=source->elements[element].visuals+index;
    if(type==10 || type==11 || type==12 || type==14 || !visual->reference) return 0;
    type=type==9 ? 4 : 5; cached=(effect_cache_t *)source; archive=cached->archive;
    if(visual->reference>=UINT32_MAX-1) result.asset=visual->inline_asset;
    else {
        status=type==4 ? CODOL_ResolveModelAlias(&archive->blocks,visual->reference,&result.asset) :
            CODOL_ResolveMaterialAlias(&archive->blocks,visual->reference,&result.asset);
        if(!status) return -1;
    }
    if(!result.asset.data || result.asset.type!=type) return -1;
    result.name=dependency_asset_name(archive,&result.asset);
    if(!result.name || !*result.name) return -1;
    archive=find_dependency_definition(type,result.name[0]==',' ? result.name+1 : result.name,&result.asset);
    if(!archive) return -1;
    result.name=dependency_asset_name(archive,&result.asset);
    CODOL_LoadBlockViews(&archive->blocks,result.blocks); result.blocks[0]=(codol_model_block_t){0};
    *out=result; return 1;
}
static native_effect_cache_t *effect_node(effect_transaction_t *transaction,const char *name,int *status)
{
    const codol_effect_source_t *source; effect_cache_t *owner; native_effect_cache_t *node;
    *status=CODOL_LoadMountedEffectSource(name,&source); if(*status!=1) return NULL;
    owner=(effect_cache_t *)source;
    for(node=owner->native;node;node=node->next)
        if(node->generation==transaction->generation && node->resolver==transaction->resolver && node->context==transaction->context) return node;
    for(node=transaction->pending;node;node=node->next) if(node->owner==owner) return node;
    node=calloc(1,sizeof(*node)); if(!node) { *status=-1; return NULL; }
    node->owner=owner; node->generation=transaction->generation; node->resolver=transaction->resolver; node->context=transaction->context;
    node->next=transaction->pending; transaction->pending=node; return node;
}
static void free_effect_work(native_effect_cache_t *node)
{
    unsigned i;
    if(node->bindings) for(i=0;i<node->owner->source.prefix.count;++i) free((void *)node->bindings[i].visuals);
    free(node->bindings); free(node->children); node->bindings=NULL; node->children=NULL;
}
/* Why the last CODOL_LoadMountedNativeEffect returned -1: the graph member
 * that failed and the check it failed. Diagnostic only; empty after success. */
static char effect_failure[256];
const char *CODOL_NativeEffectFailureDetail(void) { return effect_failure; }
static const char *va_effect(const char *format,...)
{
    static char text[160]; va_list args;
    va_start(args,format); vsnprintf(text,sizeof(text),format,args); va_end(args);
    return text;
}
#define EFFECT_FAIL_DETAIL(effect,what) snprintf(effect_failure,sizeof(effect_failure),"%s: %s",(effect) ? (effect) : "?",(what))
int CODOL_LoadMountedNativeEffect(const char *name,codol_effect_model_resolver_t resolver,void *context,const FxEffectDef **out)
{
    effect_transaction_t transaction={NULL,archives,resolver,context}; native_effect_cache_t *root,*node;
    unsigned i,j; int status;
    if(!out) return -1;
    effect_failure[0]=0;
    root=effect_node(&transaction,name,&status);
    if(!root) {
        if(status<0) EFFECT_FAIL_DETAIL(name,"source did not decode");
        return status;
    }
    for(;;) {
        const codol_effect_source_t *source;
        for(node=transaction.pending;node && node->prepared;node=node->next) {}
        if(!node) break;
        source=&node->owner->source;
        if(source->prefix.count) {
            node->bindings=calloc(source->prefix.count,sizeof(*node->bindings));
            node->children=calloc(source->prefix.count,3*sizeof(*node->children));
            if(!node->bindings || !node->children) goto fail;
        }
        for(i=0;i<source->prefix.count;++i) {
            const codol_effect_element_t *element=source->elements+i;
            unsigned type=element->record[176]; codol_effect_bindings_t *binding=node->bindings+i;
            /* C1 knows element types 0..14; CODOL_BuildNativeEffect decides
             * which of them this build retains natively. */
            if(type>14) {
                EFFECT_FAIL_DETAIL(source->prefix.name,va_effect("element %u has unsupported type %u",i,type)); goto fail;
            }
            if(type!=12) {
                const void **visuals=calloc(element->visual_count,sizeof(*visuals));
                if(element->visual_count && !visuals) goto fail;
                binding->visuals=visuals; binding->visual_count=element->visual_count;
                for(j=0;j<element->visual_count;++j) {
                    codol_effect_visual_source_t visual;
                    if(type==14) {
                        const char *runner=element->visuals[j].string;
                        native_effect_cache_t *child;
                        if(!runner) continue;
                        child=effect_node(&transaction,runner,&status);
                        if(!child) { EFFECT_FAIL_DETAIL(runner,status ? "runner source did not decode" : "runner is in no mounted zone"); goto fail; }
                        visuals[j]=child->native.effect ? child->native.effect : &child->placeholder;
                        continue;
                    }
                    status=CODOL_LoadMountedEffectVisual(source->prefix.name,i,j,&visual);
                    if(status<0) { EFFECT_FAIL_DETAIL(source->prefix.name,va_effect("element %u visual %u did not resolve",i,j)); goto fail; }
                    if(!status) continue;
                    if(visual.asset.type==5) {
                        const Material_t *material;
                        if(CODOL_LoadEngineMaterial(visual.name,&material)!=1) { EFFECT_FAIL_DETAIL(source->prefix.name,va_effect("material %s did not load",visual.name)); goto fail; }
                        visuals[j]=material;
                    } else {
                        if(!resolver || !(visuals[j]=resolver(context,visual.name))) { EFFECT_FAIL_DETAIL(source->prefix.name,va_effect("model %s did not load",visual.name)); goto fail; }
                        if(archives!=transaction.generation) goto fail;
                    }
                }
            }
            for(j=0;j<3;++j) if(element->effect_names[j]) {
                native_effect_cache_t *child=effect_node(&transaction,element->effect_names[j],&status);
                if(!child) { EFFECT_FAIL_DETAIL(element->effect_names[j],status ? "referenced effect did not decode" : "referenced effect is in no mounted zone"); goto fail; }
                node->children[3*i+j]=child;
                binding->effects[j]=child->native.effect ? child->native.effect : &child->placeholder;
            }
        }
        if(!CODOL_BuildNativeEffect(source,node->bindings,&node->native)) {
            EFFECT_FAIL_DETAIL(source->prefix.name,CODOL_NativeEffectBuildFailure()); goto fail;
        }
        node->prepared=1;
    }
    if(archives!=transaction.generation) goto fail;
    /* Every graph member now owns its final storage. Remove all temporary
     * references before exposing any node, including self/mutual references. */
    for(node=transaction.pending;node;node=node->next)
        for(i=0;i<node->owner->source.prefix.count;++i) for(j=0;j<3;++j)
            if(node->children[3*i+j]) node->native.effect->elemDefs[i].effectRefs[j]=node->children[3*i+j]->native.effect;
    /* Runner visuals participate in the same graph transaction, including
     * cycles. Replace temporary handles only after every node is prepared. */
    for(node=transaction.pending;node;node=node->next)
        for(i=0;i<node->owner->source.prefix.count;++i) {
            struct FxElemDef *element=node->native.effect->elemDefs+i;
            unsigned count=node->owner->source.elements[i].visual_count;
            /* Source identity is authoritative across both native layouts. */
            if(node->owner->source.elements[i].record[176]!=14) continue;
            for(j=0;j<count;++j) {
                void **slot=count>1 ? (void **)element->visuals+j : &element->visuals;
                native_effect_cache_t *child;
                for(child=transaction.pending;child;child=child->next)
                    if(*slot==&child->placeholder) { *slot=child->native.effect; break; }
            }
        }
    while(transaction.pending) {
        node=transaction.pending; transaction.pending=node->next; free_effect_work(node);
        node->next=node->owner->native; node->owner->native=node;
    }
    *out=root->native.effect; return 1;
fail:
    while(transaction.pending) {
        node=transaction.pending; transaction.pending=node->next; free_effect_work(node);
        CODOL_FreeNativeEffect(&node->native); free(node);
    }
    return -1;
}
/* Nested sound references keep the archive's own catalogue, then follow the
 * winning named definition exactly like model, material and effect links. */
static char sound_dep_detail[1024];
const char *CODOL_SoundDependencyFailureDetail(void) { return sound_dep_detail; }
static int sound_dependency(void *context,unsigned type,uint32_t reference,codol_sound_view_t *out)
{
    archive_t *archive=context; codol_sound_view_t result={0}; const char *name;
    if(!archive || !out || (type!=CODOL_SOUND_SPAN && (type<11 || type>13))) return -1;
    if(type==CODOL_SOUND_SPAN) {
        /* Deduplicated data pointer: hand back the serialized span the loader
         * replayed there. Its own archive owns those bytes until unmount. */
        if(!CODOL_ResolveSoundSpan(&archive->blocks,reference,&result.asset,NULL)) return -1;
        CODOL_LoadBlockViews(&archive->blocks,result.blocks);
        result.blocks[0]=(codol_model_block_t){0};
        *out=result; return 1;
    }
    if(!CODOL_ResolveSoundAlias(&archive->blocks,type,reference,&result.asset)) {
        /* Diagnostic for the engine error path: where the request fell among
         * this archive's recorded aliases, and every curve alias it holds. */
        size_t i,n=archive->blocks.asset_alias_count,used=0,index=0;
        const archive_t *walk;
        uint32_t below=0,above=0; unsigned below_type=0,above_type=0,curves=0;
        for(walk=archives;walk && walk!=archive;walk=walk->next) ++index;
        for(i=0;i<n;++i) {
            const codol_asset_alias_t *a=archive->blocks.asset_aliases+i;
            if(a->reference<=reference && a->reference>=below) { below=a->reference; below_type=a->asset.type; }
            if(a->reference>reference && (!above || a->reference<above)) { above=a->reference; above_type=a->asset.type; }
        }
        used=(size_t)snprintf(sound_dep_detail,sizeof(sound_dep_detail),
            "archive #%u aliases %u: below 0x%08x/%u above 0x%08x/%u; curve aliases:",
            (unsigned)index,(unsigned)n,below,below_type,above,above_type);
        for(i=0;i<n && used<sizeof(sound_dep_detail)-16;++i) {
            const codol_asset_alias_t *a=archive->blocks.asset_aliases+i;
            if(a->asset.type!=12) continue;
            ++curves;
            used+=(size_t)snprintf(sound_dep_detail+used,sizeof(sound_dep_detail)-used," 0x%08x",a->reference);
        }
        if(used<sizeof(sound_dep_detail)-16) used+=(size_t)snprintf(sound_dep_detail+used,sizeof(sound_dep_detail)-used," (%u)",curves);
        if(((reference-1)>>28)==3) {
            size_t offset=(reference-1)&0xfffffff;
            const codol_load_blocks_t *b=&archive->blocks;
            if(offset+40<=b->written[3] && used<sizeof(sound_dep_detail)-120) {
                const uint8_t *p=b->data[3]+offset;
                used+=(size_t)snprintf(sound_dep_detail+used,sizeof(sound_dep_detail)-used,"; block3 written 0x%x words:",(unsigned)b->written[3]);
                for(i=0;i<10 && used<sizeof(sound_dep_detail)-12;++i)
                    used+=(size_t)snprintf(sound_dep_detail+used,sizeof(sound_dep_detail)-used," %08x",
                        (unsigned)(p[4*i]|p[4*i+1]<<8|p[4*i+2]<<16|(unsigned)p[4*i+3]<<24));
            }
            for(i=0;i<b->sound_record_count && used<sizeof(sound_dep_detail)-60;++i) {
                const codol_sound_span_t *r=b->sound_records+i;
                if(((r->reference-1)>>28)!=3) continue;
                if(offset>=((r->reference-1)&0xfffffff) && offset<((r->reference-1)&0xfffffff)+r->size)
                    used+=(size_t)snprintf(sound_dep_detail+used,sizeof(sound_dep_detail)-used,"; inside span 0x%08x size %u count %u at +%u",
                        r->reference,r->size,r->count,(unsigned)(offset-((r->reference-1)&0xfffffff)));
            }
        }
        return -1;
    }
    name=dependency_asset_name(archive,&result.asset);
    if(!name || !*name) { snprintf(sound_dep_detail,sizeof(sound_dep_detail),"alias resolved but its name is empty"); return -1; }
    archive=find_dependency_definition(type,name[0]==',' ? name+1 : name,&result.asset);
    if(!archive) { snprintf(sound_dep_detail,sizeof(sound_dep_detail),"definition '%s' not mounted",name); return 0; }
    CODOL_LoadBlockViews(&archive->blocks,result.blocks);
    result.blocks[0]=(codol_model_block_t){0};
    *out=result; return 1;
}
int CODOL_LoadMountedSoundAliasList(const char *name,const codol_sound_alias_list_t **out)
{
    archive_t *archive; codol_asset_t asset; sound_cache_t *cached; codol_sound_view_t view={0};
    if(!name || !*name || *name==',' || !out) return -1;
    archive=find_dependency_definition(11,name,&asset); if(!archive) return 0;
    for(cached=archive->sounds;cached;cached=cached->next)
        if(cached->definition==asset.data) { *out=&cached->source; return 1; }
    cached=calloc(1,sizeof(*cached)); if(!cached) return -1;
    view.asset=asset; CODOL_LoadBlockViews(&archive->blocks,view.blocks);
    view.blocks[0]=(codol_model_block_t){0};
    if(!CODOL_ReadSoundAliasList(&view,sound_dependency,archive,&cached->source)) { free(cached); return -1; }
    cached->definition=asset.data; cached->archive=archive;
    cached->next=archive->sounds; archive->sounds=cached;
    *out=&cached->source; return 1;
}
/* Publication helper: every sound definition a mounted archive owns. Real
 * definitions only, so DB_LinkXAssetEntry style link references are skipped. */
int CODOL_EnumerateMountedSoundAliases(int (*visit)(void *,const char *),void *context)
{
    archive_t *archive; int visited=0;
    if(!visit) return -1;
    for(archive=archives;archive;archive=archive->next) {
        size_t i;
        for(i=0;i<archive->blocks.asset_alias_count;++i) {
            const codol_asset_t *asset=&archive->blocks.asset_aliases[i].asset;
            const char *name;
            if(asset->type!=11) continue;
            name=dependency_asset_name(archive,asset);
            if(!name) return -1;
            if(!*name || name[0]==',') continue;
            ++visited;
            if(!visit(context,name)) return visited;
        }
    }
    return visited;
}
int CODOL_LoadEngineNativeSound(const char *name,const snd_alias_list_t **out)
{
    const codol_sound_alias_list_t *source; sound_cache_t *cached; int status;
    if(!out) return -1;
    status=CODOL_LoadMountedSoundAliasList(name,&source); if(status!=1) return status;
    cached=(sound_cache_t *)source;
    if(!cached->native_ready) {
        if(!CODOL_BuildNativeSoundAliasList(&cached->source,&cached->native)) return -1;
        cached->native_ready=1;
    }
    *out=cached->native.list; return 1;
}
int CODOL_LoadMountedDynamicDependency(const char *name,unsigned category,unsigned index,
    unsigned type,codol_dynamic_dependency_t *out)
{
    archive_t *archive; unsigned offset;
    if(!name || !*name || category>1 || !out || (type!=0 && type!=4 && type!=30)) return -1;
    offset=type==4 ? 32 : type==30 ? 40 : 44;
    for(archive=archives;archive;archive=archive->next) {
        codol_asset_t collision,world; codol_dynamic_records_t records;
        codol_dynamic_dependency_t result={0}; const uint8_t *p; uint32_t ref;
        int status=CODOL_FindZoneCollisionPair(&archive->zone,name,&collision,&world);
        if(status<0) return -1;
        if(!status) continue;
        if(!archive->prepared || !CODOL_ResolveDynamicRecords(&archive->blocks,&collision,category,&records) ||
            index>=records.count) return -1;
        p=records.records+92*index+offset;
        ref=(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
        if(!ref) return 0;
        if(ref>=UINT32_MAX-1) ref=records.reference+92*index+offset;
        status=type==4 ? CODOL_ResolveModelAlias(&archive->blocks,ref,&result.asset) :
            type==30 ? CODOL_ResolveEffectAlias(&archive->blocks,ref,&result.asset) :
            CODOL_ResolvePhysicsAlias(&archive->blocks,0,ref,&result.asset);
        if(!status) return -1;
        result.name=dependency_asset_name(archive,&result.asset);
        if(!result.name || !*result.name) return -1;
        archive=find_dependency_definition(type,result.name[0]==',' ? result.name+1 : result.name,&result.asset);
        if(!archive) return -1;
        result.name=dependency_asset_name(archive,&result.asset);
        CODOL_LoadBlockViews(&archive->blocks,result.blocks); result.blocks[0]=(codol_model_block_t){0};
        *out=result; return 1;
    }
    return 0;
}
int CODOL_LoadMountedModelPhysics(const char *name,unsigned type,codol_mounted_model_physics_t *out)
{
    const codol_mounted_model_skeleton_t *model;
    const codol_mounted_model_geometry_t *geometry;
    model_cache_t *cached; archive_t *archive;
    codol_mounted_model_physics_t result={0}; codol_asset_t inline_assets[2];
    uint32_t ref; int status;
    if (!out || type>1) return -1;
    status=CODOL_LoadMountedXModelSkeleton(name,&model); if (status!=1) return status;
    status=CODOL_LoadMountedXModelGeometry(name,&geometry); if (status!=1) return status;
    ref=type ? geometry->bounds.physics_map_reference : geometry->bounds.physics_preset_reference;
    if (!ref) return 0;
    cached=(model_cache_t *)model; archive=cached->archive;
    if (ref>=UINT32_MAX-1) {
        if (!CODOL_XModelInlinePhysicsAssets(&cached->source,inline_assets)) return -1;
        result.asset=inline_assets[type];
    } else if (!CODOL_ResolvePhysicsAlias(&archive->blocks,type,ref,&result.asset)) return -1;
    result.name=dependency_asset_name(archive,&result.asset);
    if (!result.name || !*result.name) return -1;
    archive=find_dependency_definition(type,result.name[0]==',' ? result.name+1 : result.name,&result.asset);
    if (!archive) return -1;
    result.name=dependency_asset_name(archive,&result.asset);
    CODOL_LoadBlockViews(&archive->blocks,result.blocks); result.blocks[0]=(codol_model_block_t){0};
    *out=result; return 1;
}
int CODOL_LoadEngineMaterial(const char *name,const Material_t **out)
{
    codol_mounted_model_material_t source={0}; archive_t *archive;
    material_cache_t *cached;
    if (!name || !*name || !out) return -1;
    if (*name==',') { ++name; if (!*name) return -1; }
    archive=find_dependency_definition(5,name,&source.asset);
    if (!archive) {
        /* A known CoDOL dependency must not silently become an IW3 default. */
        size_t i;
        for (archive=archives;archive;archive=archive->next)
            for (i=0;i<archive->blocks.asset_alias_count;++i) {
                const codol_asset_t *asset=&archive->blocks.asset_aliases[i].asset;
                const char *candidate;
                if (asset->type!=5) continue;
                candidate=dependency_asset_name(archive,asset);
                if (candidate && candidate[0]==',' && asset_name_equal(candidate+1,name)) return -1;
            }
        return 0;
    }
    for (cached=archive->materials;cached;cached=cached->next)
        if (cached->definition==source.asset.data) { *out=&cached->native.material; return 1; }
    source.name=dependency_asset_name(archive,&source.asset);
    CODOL_LoadBlockViews(&archive->blocks,source.blocks); source.blocks[0]=(codol_model_block_t){0};
    cached=calloc(1,sizeof(*cached)); if (!cached) return -1;
    if (!CODOL_BuildNativeMaterial(&source,&cached->native)) { free(cached); return -1; }
    cached->definition=source.asset.data; cached->next=archive->materials; archive->materials=cached;
    *out=&cached->native.material; return 1;
}
int CODOL_LoadMountedPhysicsMap(const char *name,const codol_physics_map_t **out)
{
    archive_t *archive; physics_map_cache_t *cached;
    codol_mounted_model_physics_t source={0};
    if (!name || !*name || *name==',' || !out) return -1;
    archive=find_dependency_definition(1,name,&source.asset);
    if (!archive) return 0;
    for (cached=archive->physics_maps;cached;cached=cached->next)
        if (cached->definition==source.asset.data) { *out=&cached->source; return 1; }
    CODOL_LoadBlockViews(&archive->blocks,source.blocks); source.blocks[0]=(codol_model_block_t){0};
    cached=calloc(1,sizeof(*cached)); if (!cached) return -1;
    if (!CODOL_ReadPhysicsMap(&source,&cached->source)) { free(cached); return -1; }
    cached->definition=source.asset.data; cached->next=archive->physics_maps; archive->physics_maps=cached;
    *out=&cached->source; return 1;
}
int CODOL_LoadEnginePhysicsMap(const char *name,const PhysGeomList_t **out)
{
    const codol_physics_map_t *source; physics_map_cache_t *cached; int status;
    if (!out) return -1;
    status=CODOL_LoadMountedPhysicsMap(name,&source); if (status!=1) return status;
    /* source is the first member of this loader's private cache object. */
    cached=(physics_map_cache_t *)source;
    if (!cached->native_ready) {
        if (!CODOL_BuildNativePhysicsMap(source,&cached->native)) return -1;
        cached->native_ready=1;
    }
    *out=&cached->native.map; return 1;
}
int CODOL_LoadEnginePhysicsPreset(const char *name,const struct PhysPreset **out)
{
    archive_t *archive; physics_preset_cache_t *cached;
    codol_mounted_model_physics_t source={0};
    if(!name || !*name || *name==',' || !out) return -1;
    archive=find_dependency_definition(0,name,&source.asset);
    if(!archive) return 0;
    for(cached=archive->physics_presets;cached;cached=cached->next)
        if(cached->definition==source.asset.data) { *out=&cached->native.preset; return 1; }
    source.name=dependency_asset_name(archive,&source.asset);
    CODOL_LoadBlockViews(&archive->blocks,source.blocks); source.blocks[0]=(codol_model_block_t){0};
    cached=calloc(1,sizeof(*cached)); if(!cached) return -1;
    if(!CODOL_BuildNativePhysicsPreset(&source,&cached->native)) { free(cached); return -1; }
    cached->definition=source.asset.data; cached->next=archive->physics_presets; archive->physics_presets=cached;
    *out=&cached->native.preset; return 1;
}
int CODOL_LoadMountedModelSurfaces(const char *name,unsigned lod,const codol_mounted_model_surfaces_t **out)
{
    const codol_mounted_model_skeleton_t *model;
    codol_xmodel_lods_t lods;
    const codol_xmodel_lod_t *expected;
    model_cache_t *cached;
    archive_t *surface_archive;
    const char *surface_name;
    codol_asset_t assets[4];
    codol_mounted_model_surfaces_t *pending;
    codol_stream_model_t stream={0};
    int status;
    if (!out || lod>=4) return -1;
    status=CODOL_LoadMountedXModelSkeleton(name,&model); if (status!=1) return status;
    cached=(model_cache_t *)model;
    if (cached->surfaces[lod]) { *out=cached->surfaces[lod]; return 1; }
    if (!CODOL_ReadXModelLods(&cached->source,&lods)) return -1;
    if (lod<lods.first || lod>=lods.count) return 0;
    expected=lods.lods+lod;
    if ((unsigned)expected->surface_index+expected->surface_count>model->skeleton.surfaces) return -1;
    if (!CODOL_XModelInlineSurfaceAssets(&cached->source,assets)) return -1;
    if (!assets[lod].data) {
        if (!expected->surfaces_reference) return expected->surface_count ? -1 : 0;
        if (!CODOL_ResolveSurfaceAlias(&cached->archive->blocks,
            expected->surfaces_reference,assets+lod)) return -1;
    }
    surface_archive=cached->archive;
    surface_name=dependency_asset_name(surface_archive,assets+lod);
    if (surface_name && *surface_name) {
        archive_t *definition=find_dependency_definition(3,surface_name+(surface_name[0]==','),assets+lod);
        if (definition) {
            surface_archive=definition;
            surface_name=dependency_asset_name(surface_archive,assets+lod);
        } else if(surface_name[0]==',') return -1;
    }
    pending=calloc(1,sizeof(*pending)); if (!pending) return -1;
    if (!CODOL_ReadModelSurfaces(assets+lod,&pending->source)) { free(pending); return -1; }
    /* A pooled name borrows its retained archive, as do the array block views. */
    if (!pending->source.name && surface_name) {
        pending->source.name=surface_name;
        if (pending->source.unresolved) --pending->source.unresolved;
    }
    /* Only empty named dependencies may be replaced by streamed geometry.
     * A nonempty count mismatch is malformed, not a request for another asset. */
    if (!pending->source.count && expected->surface_count && pending->source.name && stream_loader) {
        codol_model_surfaces_t replacement={0};
        if (stream_loader(stream_context,pending->source.name,&stream)!=1 ||
            !CODOL_ReadStreamModelSurfaces(&stream,&replacement) ||
            !asset_name_equal(replacement.name,pending->source.name) ||
            replacement.count!=expected->surface_count) {
            CODOL_FreeModelSurfaces(&replacement); CODOL_FreeStreamModel(&stream);
            CODOL_FreeModelSurfaces(&pending->source); free(pending); return -1;
        }
        CODOL_FreeModelSurfaces(&pending->source); pending->source=replacement;
    }
    if (pending->source.count!=expected->surface_count) {
        CODOL_FreeModelSurfaces(&pending->source); free(pending); return -1;
    }
    if (stream.storage[0]) {
        memcpy(pending->blocks,stream.blocks,sizeof(pending->blocks)); cached->streams[lod]=stream;
    } else CODOL_LoadBlockViews(&surface_archive->blocks,pending->blocks);
    pending->blocks[0]=(codol_model_block_t){0};
    cached->surfaces[lod]=pending; *out=pending; return 1;
}
int CODOL_BindMountedModelBoneHandles(const char *name,codol_bone_string_acquire_t acquire,
    codol_bone_string_release_t release,void *context,const uint16_t **out,unsigned *count)
{
    const codol_mounted_model_skeleton_t *model;
    model_cache_t *cached;
    uint16_t *handles;
    unsigned i,handle;
    int status;
    if (!acquire || !release || !out || !count) return -1;
    status=CODOL_LoadMountedXModelSkeleton(name,&model);
    if (status!=1) return status;
    /* model is the first member of the private cache allocation. */
    cached=(model_cache_t *)model;
    if (cached->acquire) {
        if (cached->acquire!=acquire || cached->release!=release || cached->string_context!=context) return -1;
        *out=cached->bone_handles; *count=model->bone_names.count; return 1;
    }
    handles=calloc(model->bone_names.count ? model->bone_names.count : 1,sizeof(*handles));
    if (!handles) return -1;
    for (i=0;i<model->bone_names.count;++i) {
        handle=acquire(context,model->bone_names.names[i].text);
        if (!handle || handle>UINT16_MAX) {
            if (handle) release(context,handle);
            while (i) release(context,handles[--i]);
            free(handles); return -1;
        }
        handles[i]=(uint16_t)handle;
    }
    cached->bone_handles=handles; cached->acquire=acquire; cached->release=release; cached->string_context=context;
    *out=handles; *count=model->bone_names.count; return 1;
}
int CODOL_LoadMountedCollisionXModel(const char *name,codol_bone_string_acquire_t acquire,
    codol_bone_string_release_t release,void *context,const XModel **out)
{
    const codol_mounted_model_skeleton_t *skeleton;
    const codol_mounted_model_geometry_t *geometry;
    const codol_xmodel_materials_t *slots;
    const uint16_t *handles; unsigned count,i;
    xMaterial_t *materials[256]={0};
    model_cache_t *cached; collision_model_cache_t *pending;
    int status;
    if (!out || !acquire || !release) return -1;
    status=CODOL_LoadMountedXModelSkeleton(name,&skeleton); if(status!=1) return status;
    cached=(model_cache_t *)skeleton;
    if (cached->collision_model) {
        if (CODOL_BindMountedModelBoneHandles(name,acquire,release,context,&handles,&count)!=1) return -1;
        *out=&cached->collision_model->core.model; return 1;
    }
    if (CODOL_LoadMountedXModelGeometry(name,&geometry)!=1 ||
        CODOL_LoadMountedModelMaterials(name,&slots)!=1 || slots->count>256) return -1;
    pending=calloc(1,sizeof(*pending)); if(!pending) return -1;
    if (CODOL_LoadNativeModelMesh(name,&pending->mesh)!=1) goto fail;
    for(i=0;i<pending->mesh.count;++i) {
        unsigned slot=pending->mesh.material_indices[i];
        codol_mounted_model_material_t source; const Material_t *material;
        if(slot>=slots->count) goto fail;
        if(materials[slot]) continue;
        if(CODOL_LoadMountedModelMaterialSource(name,slot,&source)!=1 ||
            CODOL_LoadEngineMaterial(source.name,&material)!=1) goto fail;
        materials[slot]=(xMaterial_t *)material;
    }
    if (CODOL_BindMountedModelBoneHandles(name,acquire,release,context,&handles,&count)!=1 ||
        !CODOL_BuildNativeModelCore(skeleton,geometry,handles,count,&pending->core) ||
        !CODOL_BindNativeModelMesh(&pending->core,&pending->mesh,materials,slots->count)) goto fail;
    cached->collision_model=pending; *out=&pending->core.model; return 1;
fail:
    CODOL_FreeNativeModelCore(&pending->core); CODOL_FreeNativeModelMesh(&pending->mesh);
    free(pending); return -1;
}
int CODOL_LoadMountedPhysicsXModel(const char *name,codol_bone_string_acquire_t acquire,
    codol_bone_string_release_t release,void *context,const XModel **out)
{
    const XModel *base; const codol_mounted_model_skeleton_t *skeleton;
    const struct PhysPreset *preset=NULL; const PhysGeomList_t *map=NULL;
    codol_mounted_model_physics_t dependency;
    collision_model_cache_t *cached; int status;
    if (!out) return -1;
    status=CODOL_LoadMountedCollisionXModel(name,acquire,release,context,&base);
    if (status!=1) return status;
    if (CODOL_LoadMountedXModelSkeleton(name,&skeleton)!=1) return -1;
    cached=((model_cache_t *)skeleton)->collision_model;
    if (!cached->physics_ready) {
        if (cached->core.physics_preset_reference &&
            (CODOL_LoadMountedModelPhysics(name,0,&dependency)!=1 ||
             CODOL_LoadEnginePhysicsPreset(dependency.name,&preset)!=1)) return -1;
        if (cached->core.physics_map_reference &&
            (CODOL_LoadMountedModelPhysics(name,1,&dependency)!=1 ||
             CODOL_LoadEnginePhysicsMap(dependency.name,&map)!=1)) return -1;
        /* Publish both dependencies together; static-only users keep their view. */
        cached->physics_model=*base;
        cached->physics_model.physPreset=(struct PhysPreset *)preset;
        cached->physics_model.physGeoms=(PhysGeomList_t *)map;
        cached->physics_ready=1;
    }
    *out=&cached->physics_model; return 1;
}
int CODOL_LoadEngineRawFile(const char *name, const codol_engine_rawfile_t **out)
{
    archive_t *archive;
    if (!name || !out) return -1;
    for (archive = archives; archive; archive = archive->next) {
        rawfile_cache_t *cached;
        unsigned index;
        for (cached = archive->rawfiles; cached; cached = cached->next)
            if (asset_name_equal(cached->engine.name, name)) { *out = &cached->engine; return 1; }
        for (index = archive->zone.asset_count; index; --index) {
            codol_asset_t asset;
            const char *candidate;
            uint8_t *bytes;
            size_t length;
            if (!CODOL_ZoneAsset(&archive->zone, index-1, &asset)) return -1;
            if (asset.type != CODOL_ASSET_RAWFILE) continue;
            if (!asset.size) continue; /* directory reference, no definition */
            if (asset.size < 16) return -1;
            if (!world_u32(asset.data)) continue; /* unnamed rawfile */
            /* C1 4c58e7..4c592c: the leading word is an XString, either
             * inline (-1) or a packed block reference. Its payload remains
             * inline regardless of the nonzero buffer word (4c592e..4c5958). */
            candidate = world_u32(asset.data) == UINT32_MAX ?
                CODOL_RawFileName(&asset) :
                CODOL_LoadBlockString(&archive->blocks, world_u32(asset.data));
            if (!candidate) return -1;
            if (*candidate == ',' || !asset_name_equal(candidate, name)) continue;
            if (!CODOL_ReadRawFile(&asset, &bytes, &length)) return -1;
            if (length > INT_MAX) { free(bytes); return -1; }
            cached = calloc(1, sizeof(*cached));
            if (!cached) { free(bytes); return -1; }
            cached->engine.name = candidate;
            cached->engine.len = (int)length;
            cached->engine.buffer = (const char *)bytes;
            cached->next = archive->rawfiles; archive->rawfiles = cached;
            *out = &cached->engine; return 1;
        }
    }
    return 0;
}

int CODOL_LoadEngineStringTable(const char *name, const codol_engine_table_t **out)
{
    archive_t *archive;
    if (!name || !out) return -1;
    for (archive = archives; archive; archive = archive->next) {
        table_cache_t *cached;
        unsigned index;
        table_miss_t *miss;
        for (cached = archive->tables; cached; cached = cached->next)
            if (asset_name_equal(cached->engine.name, name)) { *out = &cached->engine; return 1; }
        for (miss = archive->table_misses; miss; miss = miss->next)
            if (asset_name_equal(miss->name, name)) break;
        if (miss) continue;
        for (index = archive->zone.asset_count; index; --index) {
            codol_asset_t asset;
            const char *candidate;
            size_t count, i;
            if (!CODOL_ZoneAsset(&archive->zone, index-1, &asset)) return -1;
            if (asset.type != CODOL_ASSET_STRINGTABLE) continue;
            if (!asset.size) continue;
            if (asset.size < 16) return -1;
            if (!world_u32(asset.data)) continue;
            /* C1 4c5bd5..4c5c1a uses the same inline/packed XString
             * representation as rawfiles. Do not miss a table override just
             * because its name was deduplicated into persistent block 3. */
            candidate = world_u32(asset.data) == UINT32_MAX ?
                CODOL_StringTableName(&asset) :
                CODOL_LoadBlockString(&archive->blocks, world_u32(asset.data));
            if (!candidate) return -1;
            if (*candidate == ',' || !asset_name_equal(candidate, name)) continue;
            cached = calloc(1, sizeof(*cached));
            if (!cached) return -1;
            if (!CODOL_ReadStringTable(&asset, &cached->source) ||
                cached->source.columns > INT_MAX || cached->source.rows > INT_MAX) goto fail;
            /* Inline names belong to source.storage; packed names borrow the
             * archive's replayed block, which outlives this cache entry. */
            if (!cached->source.name) cached->source.name = candidate;
            count = (size_t)cached->source.rows*cached->source.columns;
            if (count && !(cached->engine.values = calloc(count, sizeof(*cached->engine.values)))) goto fail;
            for (i = 0; i < count; ++i) {
                codol_table_cell_t *cell=cached->source.cells+i;
                /* C1 4c5b41..4c5b43 leaves a zero cell pointer untouched.
                 * Retained table queries skip NULL search cells and return
                 * an empty string when selecting one; do not turn it into
                 * a searchable empty-string key or an invalid relocation. */
                if(!cell->text && cell->reference) {
                    cell->text=CODOL_LoadBlockString(&archive->blocks,cell->reference);
                    if(!cell->text || CODOL_StringTableHash(cell->text)!=cell->hash) goto fail;
                }
                cached->engine.values[i]=cell->text;
            }
            cached->source.unresolved=0;
            cached->engine.name = cached->source.name;
            cached->engine.rowCount = cached->source.rows;
            cached->engine.columnCount = cached->source.columns;
            if (com_developer && com_developer->integer > 1 && cached->source.columns) {
                size_t row;
                Com_DPrintf(CON_CHANNEL_FILES, "CoDOL mounted stringtable %s: %ux%u, column 0:", cached->engine.name, (unsigned)cached->source.rows, (unsigned)cached->source.columns);
                for (row = 0; row < cached->source.rows && row < 64; ++row) {
                    const char *text = cached->engine.values[row*cached->source.columns];
                    Com_DPrintf(CON_CHANNEL_FILES, " %s", text ? text : "<null>");
                }
                Com_DPrintf(CON_CHANNEL_FILES, "\n");
                /* Small tables in full: every cell with its inline/pooled origin. */
                if (cached->source.rows <= 8) {
                    for (row = 0; row < cached->source.rows; ++row) {
                        size_t col;
                        Com_DPrintf(CON_CHANNEL_FILES, "  row %u:", (unsigned)row);
                        for (col = 0; col < cached->source.columns; ++col) {
                            const codol_table_cell_t *cell = cached->source.cells + row*cached->source.columns + col;
                            const char *text = cached->engine.values[row*cached->source.columns+col];
                            Com_DPrintf(CON_CHANNEL_FILES, " [%s%s]", text ? text : "<null>",
                                        cell->reference == UINT32_MAX ? "" : cell->reference ? "*" : "0");
                        }
                        Com_DPrintf(CON_CHANNEL_FILES, "\n");
                    }
                }
            }
            cached->next = archive->tables; archive->tables = cached;
            *out = &cached->engine; return 1;
fail:
            CODOL_FreeStringTable(&cached->source); free(cached->engine.values); free(cached);
            return -1; /* a broken patch must not silently expose an older table */
        }
        /* Not in this archive: remember that, so the next lookup skips it. */
        {
            size_t length = strlen(name);
            miss = malloc(sizeof(*miss) + length);
            if (miss) {
                memcpy(miss->name, name, length + 1);
                miss->next = archive->table_misses; archive->table_misses = miss;
            }
        }
    }
    return 0;
}

/* Loose-file CSV overlays, keyed by (script root, name) and never by mounted
 * generation, so nothing about a group replacement drops them. The asset
 * category selects the script root (cscr_parser.cpp:584 passes
 * CODOL_ServerZoneType() into the overlay lookup), so a category switch that
 * left these resident would answer the new category from the old category's
 * loose files for the rest of the process. */
void CODOL_ResetReferenceStringTables(void)
{
    while(reference_tables) {
        reference_table_t *entry=reference_tables;reference_tables=entry->next;
        free(entry->root);free(entry->name);free(entry->table.engine.values);
        CODOL_FreeStringTable(&entry->table.source);free(entry);
    }
}
/* Every cache an archive owns. Split out of CODOL_UnmountArchives so a single
 * retired generation can be released without tearing down the startup group.
 * Callers must first drop everything that borrows from this archive: composed
 * weapon cores, weapon sound bindings, script profiles and model animations. */
static void free_archive(archive_t *entry)
{
    {
        while(entry->sounds) {
            sound_cache_t *sound=entry->sounds; entry->sounds=sound->next;
            CODOL_FreeNativeSound(&sound->native);
            CODOL_FreeSoundAliasList(&sound->source); free(sound);
        }
        while(entry->effects) {
            effect_cache_t *effect=entry->effects; entry->effects=effect->next;
            while(effect->native) {
                native_effect_cache_t *native=effect->native; effect->native=native->next;
                CODOL_FreeNativeEffect(&native->native); free(native);
            }
            CODOL_FreeEffectSource(&effect->source); free(effect);
        }
        while (entry->models) {
            model_cache_t *model=entry->models; entry->models=model->next;
            unsigned i;
            if(model->collision_model) {
                CODOL_FreeNativeModelCore(&model->collision_model->core);
                CODOL_FreeNativeModelMesh(&model->collision_model->mesh);
                free(model->collision_model);
            }
            /* Release a bone-name handle only while it still names this bone.
             * A retired archive can outlive the script string generation that
             * interned the name; releasing a recycled handle decrements a
             * stranger's refcount and, once that string is freed for real,
             * SL_FreeString walks its hash chain forever (2026-09-22 verrukt
             * hang: main thread parked in SL_RemoveRefToStringOfSize called
             * from free_archive). Leaking a dead handle costs nothing. */
            if (model->release) for (i=0;i<model->model.bone_names.count;++i)
                if (CODOL_EngineStringHandleIs(model->bone_handles[i],model->model.bone_names.names[i].text))
                    model->release(model->string_context,model->bone_handles[i]);
            free(model->bone_handles);
            for (i=0;i<4;++i) if (model->surfaces[i]) {
                CODOL_FreeModelSurfaces(&model->surfaces[i]->source); free(model->surfaces[i]);
                CODOL_FreeStreamModel(&model->streams[i]);
            }
            CODOL_FreeXModelCollision(&model->geometry.collision);
            CODOL_FreeXModelMaterials(&model->materials);
            CODOL_FreeXModelBounds(&model->geometry.bounds);
            CODOL_FreeXModelBoneNames(&model->model.bone_names);
            CODOL_FreeXModelSkeleton(&model->model.skeleton); free(model);
        }
        while(entry->weapon_tags) {
            weapon_tags_t *tags=entry->weapon_tags; unsigned i;
            entry->weapon_tags=tags->next;
            /* No names are cached here to validate against; an interned tag
             * name is a few bytes, a stale release is a hang. Keep the refs. */
            (void)i;
            free(tags);
        }
        if(entry->null_weapon) { CODOL_FreeNativeWeaponCore(entry->null_weapon); free(entry->null_weapon); }
        while(entry->native_weapons) {
            native_weapon_cache_t *weapon=entry->native_weapons;
            entry->native_weapons=weapon->next;
            CODOL_FreeNativeWeaponCore(&weapon->core); free(weapon);
        }
        free(entry->script_strings);
        while(entry->glass_worlds) {
            glass_world_cache_t *world=entry->glass_worlds;
            entry->glass_worlds=world->next;
            CODOL_FreeGlassGroups(&world->groups); free(world);
        }
        while (entry->worlds) {
            common_world_cache_t *world=entry->worlds; entry->worlds=world->next;
            free_common_world(world);
        }
        while (entry->physics_maps) {
            physics_map_cache_t *map=entry->physics_maps; entry->physics_maps=map->next;
            CODOL_FreeNativePhysicsMap(&map->native); CODOL_FreePhysicsMap(&map->source); free(map);
        }
        while(entry->physics_presets) {
            physics_preset_cache_t *preset=entry->physics_presets; entry->physics_presets=preset->next;
            CODOL_FreeNativePhysicsPreset(&preset->native); free(preset);
        }
        while (entry->materials) {
            material_cache_t *material=entry->materials; entry->materials=material->next;
            CODOL_FreeNativeMaterial(&material->native); free(material);
        }
        while (entry->rawfiles) {
            rawfile_cache_t *raw = entry->rawfiles; entry->rawfiles = raw->next;
            free((void *)raw->engine.buffer); free(raw);
        }
        while (entry->tables) {
            table_cache_t *table = entry->tables; entry->tables = table->next;
            free(table->engine.values); CODOL_FreeStringTable(&table->source); free(table);
        }
        while (entry->table_misses) {
            table_miss_t *miss = entry->table_misses; entry->table_misses = miss->next;
            free(miss);
        }
        while(entry->xanim_strings) {
            xanim_strings_t *strings=entry->xanim_strings; unsigned i;
            entry->xanim_strings=strings->next;
            CODOL_FreeNativeXAnim(&strings->native);
            /* Same as weapon tags: no cached names to validate, keep the refs. */
            (void)i;
            free(strings);
        }
        free(entry->dependency_index);
        CODOL_FreeLoadBlocks(&entry->blocks); CODOL_CloseZone(&entry->zone); free(entry);
    }
}
/* Release the archives a previous CODOL_ReplaceRuntimeArchives moved aside.
 * mount_archives only unlinks the outgoing group (it cannot free it: live
 * native code still holds WeaponDef pointers into it, which is what
 * CODOL_FindNativeWeaponQueryCore walks the retired list for), so without this
 * every map or category change leaves a full extra copy of the gametype and
 * map zones resident for the rest of the process. Returns how many were freed.
 *
 * PRECONDITION: no borrower of a retired archive may still be live. The
 * borrowers are CODOL_ResetComposedWeapons (retired cores and their base
 * definitions), CODOL_ResetNativeWeaponSounds (alias lists), the engine sound
 * channel bindings, CODOL_ResetScriptProfiles and CODOL_ResetModelAnimations.
 * CODOL_UnloadCategoryAssets is the entry point that sequences all of them. */
unsigned CODOL_ReleaseRetiredArchives(void)
{
    unsigned count=0;
    while(retired_archives) {
        archive_t *entry=retired_archives; retired_archives=entry->next;
        free_archive(entry); ++count;
    }
    return count;
}
void CODOL_UnmountArchives(void)
{
    /* Composed cores borrow image/archive strings and native assets, and own
     * SL references. Release them before any of those providers disappear. */
    CODOL_ResetComposedWeapons();
    /* Cached profile definitions borrow names and offset maps from these
     * archives. Invalidate them before releasing the backing storage. */
    CODOL_ResetScriptProfiles();
    /* Weapon sound bindings borrow archive-owned alias lists. */
    CODOL_ResetNativeWeaponSounds();
    CODOL_ResetReferenceStringTables();
    CODOL_ReleaseRetiredArchives();
    while (archives) {
        archive_t *entry=archives; archives=entry->next;
        free_archive(entry);
    }
}
/* A LocalizeEntry string: inline (0xffffffff, the next NUL-terminated string in
 * the entry's own stream bytes) or a de-duplicated reference into runtime
 * block 3 that the replay laid out. Only a prepared archive has that block. */
static const char *localize_string(const archive_t *archive,const uint8_t **cursor,const uint8_t *end,uint32_t ref)
{
    const char *s; size_t offset;
    if(ref==UINT32_MAX) {
        s=(const char *)*cursor;
        if(*cursor>=end || !memchr(*cursor,0,(size_t)(end-*cursor))) return NULL;
        *cursor+=strlen(s)+1; return s;
    }
    if(!archive->prepared || !ref || ((ref-1)>>28)!=3) return NULL;
    offset=(ref-1)&0xfffffff;
    if(offset>=archive->blocks.written[3]) return NULL;
    s=(const char *)archive->blocks.data[3]+offset;
    return memchr(s,0,archive->blocks.written[3]-offset) ? s : NULL;
}
static uint32_t localize_u32(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
int CODOL_EnumerateMountedLocalize(int (*visit)(void *,const char *,const char *),void *context)
{
    archive_t *archive; int visited=0;
    if(!visit) return -1;
    for(archive=archives;archive;archive=archive->next) {
        const codol_zone_t *zone=&archive->zone; uint32_t k;
        if(zone->table_offset>zone->size || zone->asset_count>(zone->size-zone->table_offset)/16) continue;
        for(k=0;k<zone->asset_count;++k) {
            const uint8_t *entry=zone->data+zone->table_offset+16*k,*p,*cursor,*end;
            uint32_t type=localize_u32(entry),position=localize_u32(entry+4)+40,extent=localize_u32(entry+12);
            const char *value,*name;
            if(type!=27 || position>zone->size || extent<8 || extent>zone->size-position) continue;
            /* C1 LocalizeEntry 0x4c1ea0 (replay_localize): value, then name. */
            p=zone->data+position; end=p+extent; cursor=p+8;
            value=localize_string(archive,&cursor,end,localize_u32(p));
            name=localize_string(archive,&cursor,end,localize_u32(p+4));
            if(!value || !name || !*name) continue;
            ++visited;
            if(!visit(context,name,value)) return visited;
        }
    }
    return visited;
}
