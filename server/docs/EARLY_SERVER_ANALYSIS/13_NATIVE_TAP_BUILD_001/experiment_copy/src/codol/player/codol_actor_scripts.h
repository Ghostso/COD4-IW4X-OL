#ifndef CODOL_ACTOR_SCRIPTS_H
#define CODOL_ACTOR_SCRIPTS_H
#ifdef CODOL_SERVER
/* server.h leaks a bare #pragma pack(1) into every translation unit that
 * includes it. codol_actor_scripts.cpp defines species_table[] under the
 * default layout; codol_actor_lifecycle.cpp reads the rows under pack(1),
 * so the stateIndex/stateName/stateApply columns were read 3 bytes early
 * (a->species->stateName() jumped to 0xf300330e, the DOGS killstreak
 * crash of 2026-09-22). Wrap the whole header like every other CoDOL
 * header; docs/CODOL_DOG_CRASH_20260922.md. */
#pragma pack(push, 8)
struct gentity_s;
struct DObj_s;
#ifdef __cplusplus
extern "C" {
#endif

/* ---------------------------------------------------------------------------
 * Actor species table.
 *
 * Everything the actor path used to spell "dog" as a literal is a column here:
 * the animtree a spawn needs, the C1 client composition tree that animtree is
 * registered at, the serverinfo-2482 mask bit that registers it, the aitype
 * classname, the animscript module set, and the native animation-state
 * backend (the dog's ported T5 clip machine; NULL for a species that has
 * none yet).
 *
 * Column provenance, all MEASURED 2026-09-20 unless marked:
 *
 *  treeSelector / animlistMask
 *      C1.exe 0x4083f0 builds a five-entry table at bgs+0x90174 (5 records of
 *      0x14 bytes, loop `edi += 0x14` while `edi < 0x64`), registering entry i
 *      only when serverinfo key 2482 has bit (1 << i) set; 0x428ba6 reads
 *      entityState +0x59 as the index into it. The five tree names are stored
 *      at ebp-0x18..-0x8 by 0x40840b..0x408426 and walked upward in step with
 *      the bit, and reading them out of .rdata gives:
 *          0 (bit 0x01) 0xc3f080 "generic_human"   animlists/common_human
 *          1 (bit 0x02) 0xc3f090 "dog"             animlists/common_dog
 *          2 (bit 0x04) 0xc3f080 "generic_human"   animlists/common_civilian
 *          3 (bit 0x08) 0xc3f080 "generic_human"   animlists/common_zombie
 *          4 (bit 0x10) 0xc3f094 "zombie_dog"      (no animlist of its own)
 *      C1 0x408310 loads those four animlists and CLEARS a class bit when
 *      BG_TryLoadAnimList (0x408040) returns false, which it does for an
 *      absent rawfile (both exits of the default-asset arm, 0x408112 and
 *      0x408130, are `xor al,al`). Only common_zombie.animlist ships in a zm
 *      zone, so bit 0x08 is both the only class bit that survives a zm match
 *      and exactly the one that registers generic_human.
 *
 *      codol_animlistMask is registered 0..15 (src/sv_main.c), so bit 0x10 is
 *      currently unreachable; a hellhound species would need that widened.
 *
 *  animtree
 *      A compiled script must declare #using_animtree(<animtree>) or the
 *      server registry has no slot for it and CODOL_ActorPrepareAnimation
 *      refuses the spawn. animtrees/dog.atr and animtrees/generic_human.atr
 *      both ship in common_mp, which is mounted for every asset category.
 *
 *  category
 *      The asset category whose script set ships this species' aitype and
 *      animscripts, i.e. the only category in which the aitype is preloaded.
 *      Loading the multiplayer dog chain under zm/coop is what fatally broke
 *      those categories on 2026-09-20 (see CODOL_DOG_KILLSTREAK_20260920.md).
 * ------------------------------------------------------------------------ */
typedef int (*codol_actor_state_index_t)(const char *name);
typedef const char *(*codol_actor_state_name_t)(unsigned index);
typedef int (*codol_actor_state_apply_t)(struct DObj_s *obj, unsigned entity,
    unsigned generation, unsigned tree, unsigned time, int state, int previous,
    int entering, float rate, float lean, float aimUp, float aimLeft);

typedef struct {
    const char *name;        /* aitype main()'s self.type, and getType() */
    const char *animtree;    /* #using_animtree name; animtrees/<x>.atr */
    unsigned treeSelector;   /* C1 actor composition tree index, 0..4 */
    unsigned animlistMask;   /* serverinfo 2482 bits this species needs */
    unsigned talkBit;        /* setTalkToSpecies() bit for this species */
    const char *category;    /* asset category that preloads the aitype */
    const char *classname;   /* spawner classname, "actor_<aitype file>" */
    const char *animscript;  /* animscript module prefix, "<dir>/<species>" */
    /* Perception model. 0 is the ordinary sighted actor: it acquires an enemy
     * only over a clear line of sight (T5 Actor_UpdateSight ->
     * sentientInfo[].lastKnownPosTime, then Actor_UpdateThreat).
     *
     * 1 is T5's PERFECT INFO actor, MEASURED in OpenBLOPS
     * Game/Server/game/actor_spawner.cpp:199-203: a spawner carrying the
     * ENEMYINFO spawnflag (spawnflags & 8) runs
     *     for (pEnemy = Sentient_FirstSentient(-1); pEnemy; ...)
     *         Actor_GetPerfectInfo(spawn->actor, pEnemy);
     * and Actor_GetPerfectInfo (actor_senses.cpp:513-516) writes
     * lastKnownPosTime = level.time plus the position for EVERY sentient, so
     * the threat pass' only awareness gate (actor_threat.cpp:241,
     * "lastKnownPosTime <= 0" -> unaware) is already satisfied and the actor
     * targets through walls. The zm zombie is that actor twice over: the
     * actor_enemy_zombie_zm QUAKED block declares ENEMYINFO, and T5's own
     * find_flesh (_zombiemode_spawner.gsc:4013) picks its target with
     * get_closest_valid_player -> GetClosest(), pure distance with no sight
     * test at all, then forces it through self.favoriteenemy, which
     * actor_threat.cpp:317-321 gives maxThreat 0x7ffffffe and
     * actor_senses.cpp:303-307 exempts from the FOV cone. */
    unsigned char perfectInfo;
    /* Native animation-state backend. NULL means this species has no state
     * machine yet: it spawns, paths and takes damage, but publishes no
     * animation, so setanimstate() refuses instead of playing a dog clip. */
    codol_actor_state_index_t stateIndex;
    codol_actor_state_name_t stateName;
    codol_actor_state_apply_t stateApply;
} codol_actor_species_t;

unsigned CODOL_ActorSpeciesCount(void);
const codol_actor_species_t *CODOL_ActorSpecies(unsigned index);
/* By self.type ("dog"), by spawner classname ("actor_enemy_dog_mp"). */
const codol_actor_species_t *CODOL_ActorSpeciesByName(const char *name);
const codol_actor_species_t *CODOL_ActorSpeciesByClassname(const char *classname);
/* The animlist mask bits every species of this asset category needs, i.e. the
 * value codol_animlistMask must carry for their animtrees to be registered on
 * the client. Category NULL answers every species' bits. */
unsigned CODOL_ActorSpeciesAnimListMask(const char *category);

/* Call Reset immediately after Scr_BeginLoadScripts. LoadType belongs before
 * Scr_EndLoadScripts, for an actual actor_ classname present in map spawn data
 * or preloaded for this asset category. It does not load scripts during
 * spawnactor or silently substitute a different aitype. Runtime functions
 * require a successfully loaded type. */
void CODOL_ActorScriptsReset(void);
void CODOL_ActorScriptsLoadMapTypes(void);
void CODOL_ActorRegisterFields(void);
void CODOL_ActorRegisterMethods(void);
int CODOL_ActorScriptsLoadType(const char *classname);
int CODOL_ActorScriptsPrecache(void);
int CODOL_ActorScriptsSpawner(struct gentity_s *);
int CODOL_ActorScriptsSpawnerReady(struct gentity_s *);
int CODOL_ActorScriptsInitialize(struct gentity_s *);
#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
#endif
