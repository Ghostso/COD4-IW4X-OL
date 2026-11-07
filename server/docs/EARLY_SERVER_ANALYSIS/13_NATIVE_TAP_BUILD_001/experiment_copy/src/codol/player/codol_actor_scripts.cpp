/* Original T5 aitype and species script loading/entry lifecycle.
 * Staged native implementation; no runtime script compilation or fake spawn.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifdef CODOL_SERVER
/* The retained headers declare C functions without linkage guards. */
extern "C" {
#include "codol_actor_scripts.h"
#include "codol_actor_lifecycle.h"
#include "codol_sv_state.h"
#include "entity.h"
#include "cscr_stringlist.h"
#include "scr_vm.h"
#include "cm_public.h"
#include "qcommon.h"
#include <string.h>
#include <stdio.h>
}
#include "codol_dog_states.h"

/* --- the species table ---------------------------------------------------
 * See the long column note in codol_actor_scripts.h for where each constant
 * was measured. Adding a species is a row plus its scripts; nothing in the
 * actor path may test a species name again. */
static const codol_actor_species_t species_table[] = {
{
    /* name        */ "dog",
    /* animtree    */ "dog",
    /* treeSelector*/ 1,
    /* animlistMask*/ 0x02u,
    /* talkBit     */ 0x01u,
    /* category    */ "mp",
    /* classname   */ "actor_enemy_dog_mp",
    /* animscript  */ "maps/mp/animscripts/dog",
    /* perfectInfo */ 0,
    CODOL_DogStateIndex, CODOL_DogStateName, CODOL_DogStateApply
},
{
    /* The zm humanoid zombie.
     *
     * MEASURED 2026-09-20, C1.exe 0x40840b..0x40847a: the client's five actor
     * composition trees are, in bit order 0x01,0x02,0x04,0x08,0x10,
     *     generic_human, dog, generic_human, generic_human, zombie_dog
     * so serverinfo-2482 bit 0x08 -- the bit whose animlist is
     * animlists/common_zombie -- registers "generic_human" at tree selector 3.
     * That single bit does both halves of this species' binding:
     *   - it loads common_zombie.animlist (common_gametype_zm, 7,874 bytes),
     *     whose "=generic_human" group holds 220 anims including the whole
     *     ai_zombie_* set, which is what CODOL_RegisterServerAnimListReferences
     *     resolves into the server's generic_human tree;
     *   - it registers the client composition tree this actor is composed
     *     against.
     * animtrees/generic_human.atr ships in common_mp (mounted for every asset
     * category); 389 of its 5,345 lines name ai_zombie_* nodes.
     *
     * Selector 4 / bit 0x10 is "zombie_dog", the hellhound, and needs no
     * animlist of its own (its 60 clips are in common_zombie.animlist too).
     * A future hellhound species row would take selector 4 -- and would also
     * need codol_animlistMask's 0..15 range widened, since 0x10 is outside it.
     *
     * stateApply is NULL: T5 animates humanoid AI from GSC through
     * #using_animtree %anim references, not from a native clip-state table
     * like bg_dog_animations_mp.cpp, and that scripted-animation surface
     * (setanim/setanimknob/animscripted builtins) does not exist here yet. */
    /* name        */ "zombie",
    /* animtree    */ "generic_human",
    /* treeSelector*/ 3,
    /* animlistMask*/ 0x08u,
    /* talkBit     */ 0x02u,
    /* category    */ "zm",
    /* classname   */ "actor_enemy_zombie_zm",
    /* animscript  */ "maps/mp/animscripts/zombie",
    /* perfectInfo */ 1,
    NULL, NULL, NULL
}
};
#define SPECIES_COUNT ((unsigned)(sizeof(species_table)/sizeof(species_table[0])))

unsigned CODOL_ActorSpeciesCount(void) { return SPECIES_COUNT; }
const codol_actor_species_t *CODOL_ActorSpecies(unsigned index)
{
    return index < SPECIES_COUNT ? &species_table[index] : NULL;
}
const codol_actor_species_t *CODOL_ActorSpeciesByName(const char *name)
{
    if (!name) return NULL;
    for (unsigned i = 0; i < SPECIES_COUNT; ++i)
        if (!strcmp(name, species_table[i].name)) return &species_table[i];
    return NULL;
}
const codol_actor_species_t *CODOL_ActorSpeciesByClassname(const char *classname)
{
    if (!classname) return NULL;
    for (unsigned i = 0; i < SPECIES_COUNT; ++i)
        if (!strcmp(classname, species_table[i].classname)) return &species_table[i];
    return NULL;
}
unsigned CODOL_ActorSpeciesAnimListMask(const char *category)
{
    unsigned mask = 0;
    for (unsigned i = 0; i < SPECIES_COUNT; ++i)
        if (!category || !strcmp(category, species_table[i].category))
            mask |= species_table[i].animlistMask;
    return mask;
}

struct actor_script_type {
    char classname[64];
    int main, precache, spawner;
    unsigned species;
    bool loaded, precached;
};
static actor_script_type types[32];
/* One animscript set per species, loaded at most once per map. */
static codol_actor_script_table_t speciesScripts[SPECIES_COUNT];
static bool speciesLoaded[SPECIES_COUNT];

static int LoadMain(const char *file)
{
    if (!Scr_LoadScript(file)) return 0;
    return Scr_GetFunctionHandle(file, "main");
}

void CODOL_ActorScriptsReset(void)
{
    memset(types, 0, sizeof(types));
    memset(speciesScripts, 0, sizeof(speciesScripts));
    memset(speciesLoaded, 0, sizeof(speciesLoaded));
}

/* Loads <animscript>_init .. <animscript>_jump for one species. All nine or
 * none: a half-bound set would leave CODOL_ActorSwitchScript with a zero
 * handle for exactly the transition that needs it. */
static int LoadSpeciesScripts(unsigned index)
{
    if (index >= SPECIES_COUNT) return 0;
    if (speciesLoaded[index]) return 1;
    static const char *const suffix[] = {
        "_init", "_stop", "_move", "_combat", "_death",
        "_pain", "_flashed", "_turn", "_jump"
    };
    const char *prefix = species_table[index].animscript;
    size_t prefixLength = strlen(prefix);
    codol_actor_script_table_t pending = {};
    int *slot[] = {
        &pending.init, &pending.stop, &pending.move, &pending.combat,
        &pending.death, &pending.pain, &pending.flashed, &pending.turn,
        &pending.jump
    };
    for (unsigned i = 0; i < 9; ++i) {
        char file[96];
        if (prefixLength + strlen(suffix[i]) >= sizeof(file)) return 0;
        memcpy(file, prefix, prefixLength);
        strcpy(file + prefixLength, suffix[i]);
        *slot[i] = LoadMain(file);
        if (!*slot[i]) return 0;
    }
    speciesScripts[index] = pending;
    speciesLoaded[index] = true;
    return 1;
}

int CODOL_ActorScriptsLoadType(const char *classname)
{
    if (!classname || strncmp(classname, "actor_", 6) || !classname[6] ||
        strlen(classname) >= sizeof(types[0].classname)) return 0;
    /* aitype is a file identifier, not a free-form script path. */
    for (const char *c = classname + 6; *c; ++c)
        if (!((*c >= 'a' && *c <= 'z') || (*c >= 'A' && *c <= 'Z') ||
              (*c >= '0' && *c <= '9') || *c == '_')) return 0;
    /* Only a classname this build has a species row for: an unknown actor_*
     * must not be given some other species' animscripts. */
    const codol_actor_species_t *row = CODOL_ActorSpeciesByClassname(classname);
    if (!row) return 0;
    unsigned index = (unsigned)(row - species_table);
    actor_script_type *slot = NULL;
    for (unsigned i = 0; i < 32; ++i) {
        if (types[i].loaded && !strcmp(types[i].classname, classname)) return 1;
        if (!slot && !types[i].loaded) slot = &types[i];
    }
    if (!slot) return 0;
    if (!LoadSpeciesScripts(index)) return 0;
    char file[80];
    snprintf(file, sizeof(file), "aitype/%s", classname + 6);
    actor_script_type pending = {};
    pending.main = LoadMain(file);
    if (!pending.main) return 0;
    pending.precache = Scr_GetFunctionHandle(file, "precache");
    pending.spawner = Scr_GetFunctionHandle(file, "spawner");
    if (!pending.precache || !pending.spawner) return 0;
    strcpy(pending.classname, classname);
    pending.species = index;
    pending.loaded = true;
    *slot = pending;
    return 1;
}

/* The retained tree declares COM_Parse but never defines it; the live parser
 * is Com_Parse, which returns a parseInfo_t whose token is what we want. */
static const char *actor_parse(char **cursor)
{
    const char *c = *cursor;
    parseInfo_t *info = Com_Parse(&c);
    *cursor = (char *)c;
    return info ? info->token : "";
}

/* Copies the server animtree registry's names out of the compiler objects
 * before Scr_EndLoadAnimTrees recycles them; see the long note above
 * CODOL_ServerAnimTreeName in codol_model_animation.c.  This is the last
 * script-loading step of GScr_LoadScripts, so every #using_animtree in the
 * compiled set has already registered its slot by the time the wrapper below
 * takes the snapshot. */
extern "C" void CODOL_SnapshotServerAnimTreeNames(void);

static void ActorScriptsLoadMapTypes(void)
{
    // Read a private cursor; never advance the spawn parser's global cursor.
    char *cursor = CM_EntityString();
    if (!cursor) return;
    while (cursor) {
        const char *token = actor_parse(&cursor);
        if (!token[0]) break;
        if (strcmp(token, "{")) {
            Com_Error(ERR_DROP, "actor preload: malformed map entity block");
            return;
        }
        char classname[64] = "";
        while (cursor) {
            token = actor_parse(&cursor);
            if (!strcmp(token, "}")) break;
            if (!token[0]) { Com_Error(ERR_DROP, "actor preload: truncated entity"); return; }
            bool isClassname = !strcmp(token, "classname");
            token = actor_parse(&cursor);
            if (!cursor) { Com_Error(ERR_DROP, "actor preload: missing entity value"); return; }
            if (isClassname) Q_strncpyz(classname, token, sizeof(classname));
        }
        // A map that authors a spawner for a species this build knows must get
        // that species' own aitype and animscripts. Any other actor_ classname
        // is left alone rather than given a species implementation guessed
        // from a substring in its name.
        if (CODOL_ActorSpeciesByClassname(classname) &&
            !CODOL_ActorScriptsLoadType(classname)) {
            Com_Error(ERR_DROP, "actor preload: incomplete aitype or animscripts for '%s'",
                      classname);
            return;
        }
    }
    /* Species preload. A species' aitype is loaded on every map of its asset
     * category, because the feature that spawns it (the dogs killstreak, the
     * zm zombie spawner) builds its own spawner through spawnactorspawner and
     * no CoDOL map authors one in its entity string (T5's maps did). A map
     * that does author one is still the fatal case above, because there the
     * missing scripts would leave a dead entity.
     *
     * THE CATEGORY COLUMN IS LOAD-BEARING. Before it existed, the multiplayer
     * dog aitype was preloaded in every category: aitype/enemy_dog_mp and the
     * nine maps/mp/animscripts/dog_* modules resolve out of the SHARED root
     * (the zm and coop category roots ship no dog scripts), and their
     * transitive file::function references reach maps/mp/gametypes/_spawnlogic,
     * whose maps\mp\gametypes\_callbacksetup::AbortLevel() does not exist in a
     * category _callbacksetup -- a fatal compile error at Game Initialization.
     * MEASURED 2026-09-20 on zm_prototype_sh: archives and configstrings
     * mounted correctly as zm, then "unknown function ... _spawnlogic.gsc line
     * 49" and "Server fatal crashed"
     * (bin/home/main/qconsole.zm-crash-20260920.log).
     *
     * The gate is the asset category, not the map name, because that is what
     * decides the script set (a coop match runs an mp_* level zone). */
    const char *zone = CODOL_ServerZoneType();
    if (!zone) return;
    for (unsigned i = 0; i < SPECIES_COUNT; ++i) {
        const codol_actor_species_t *row = &species_table[i];
        if (strcmp(zone, row->category)) {
            Com_DPrintf(CON_CHANNEL_SERVER,
                "CoDOL actor: '%s' category, skipping the '%s' species preload (category '%s')\n",
                zone, row->name, row->category);
            continue;
        }
        if (!speciesLoaded[i] && !CODOL_ActorScriptsLoadType(row->classname))
            Com_PrintWarning(CON_CHANNEL_SERVER,
                "CoDOL actor: aitype/%s or the %s_* animscripts did not load; "
                "the '%s' species is unavailable on this map\n",
                row->classname + 6, row->animscript, row->name);
    }
}

void CODOL_ActorScriptsLoadMapTypes(void)
{
    ActorScriptsLoadMapTypes();
    /* Unconditional, and after every return path above: the snapshot is not
     * species-specific, and the window in which the compiler's tree-name
     * objects are readable closes for good at BG_LoadAnim's
     * Scr_EndLoadAnimTrees. */
    CODOL_SnapshotServerAnimTreeNames();
}

static actor_script_type *FindType(gentity_s *entity)
{
    if (!entity || !entity->r.inuse || !entity->classname) return NULL;
    const char *name = SL_ConvertToString(entity->classname);
    for (unsigned i = 0; i < 32; ++i)
        if (types[i].loaded && !strcmp(types[i].classname, name)) return &types[i];
    return NULL;
}

int CODOL_ActorScriptsPrecache(void)
{
    for (unsigned i = 0; i < 32; ++i) {
        actor_script_type *type = &types[i];
        if (!type->loaded || type->precached) continue;
        /* Called in level initialization while assets can be precached, before
         * any aitype main/spawner executes, as T5 FinishSpawningAll requires. */
        type->precached = true;
        short thread = Scr_ExecThread(type->precache, 0);
        Scr_FreeThread(thread);
    }
    return 1;
}

/* True when this spawner's aitype scripts are loaded and precached, i.e. when
 * spawnactor on it can actually produce an initialized actor. */
int CODOL_ActorScriptsSpawnerReady(gentity_s *entity)
{
    actor_script_type *type = FindType(entity);
    return type && type->precached && speciesLoaded[type->species] &&
        entity->s.eType == ET_ACTOR_SPAWNER;
}

int CODOL_ActorScriptsSpawner(gentity_s *entity)
{
    actor_script_type *type = FindType(entity);
    if (!type || !type->precached || entity->s.eType != ET_ACTOR_SPAWNER) return 0;
    unsigned generation = (unsigned)entity->useCount;
    short thread = Scr_ExecEntThread(entity, type->spawner, 0);
    Scr_FreeThread(thread);
    return entity->r.inuse && (unsigned)entity->useCount == generation &&
        entity->s.eType == ET_ACTOR_SPAWNER;
}

/* Each stage names itself: a spawnactor that yields `undefined` must say why
 * in the log instead of leaving the calling script to dereference it. */
#define STAGE_WARN(...) Com_PrintWarning(CON_CHANNEL_SERVER, "CoDOL actor: actor init: " __VA_ARGS__)
int CODOL_ActorScriptsInitialize(gentity_s *entity)
{
    actor_script_type *type = FindType(entity);
    const char *cls = entity && entity->classname ? SL_ConvertToString(entity->classname) : "?";
    if (!type) { STAGE_WARN("no loaded aitype for classname '%s'\n", cls); return 0; }
    if (!type->precached) { STAGE_WARN("aitype '%s' was never precached (level init order)\n", cls); return 0; }
    const codol_actor_species_t *row = &species_table[type->species];
    if (!speciesLoaded[type->species]) { STAGE_WARN("%s_* animscripts are not loaded\n", row->animscript); return 0; }
    if (!CODOL_ActorForEntity(entity)) { STAGE_WARN("ent %d has no actor record\n", entity->s.number); return 0; }
    if (!CODOL_ActorRunTypeMain(entity, type->main)) {
        STAGE_WARN("aitype/%s::main() failed or deleted the actor\n", cls + 6); return 0;
    }
    if (!CODOL_ActorPrepareAnimation(entity)) return 0; /* names its own cause */
    if (!CODOL_ActorInitScripts(entity, &speciesScripts[type->species])) {
        STAGE_WARN("%s_init::main() failed, or the actor's type/species was not set to \"%s\" by aitype main\n",
                   row->animscript, row->name); return 0;
    }
    if (!CODOL_ActorFinishInitialization(entity, row->treeSelector)) {
        STAGE_WARN("server DObj for ent %d does not own the '%s' animtree\n",
                   entity->s.number, row->animtree); return 0;
    }
    return 1;
}
#endif
