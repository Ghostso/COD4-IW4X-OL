/* Script-model animation state: the engine half of precachempanim,
 * scriptmodelplayanim and scriptmodelclearanim.
 *
 * Measured reference (IW4, D:/CoD/shx/iw4x.exe)
 * --------------------------------------------
 * precachempanim (0x5f8380) registers one name into an indexed bank with
 * start 4042, max 63, create 1 and the error label "mp anim", and returns
 * nothing. G_FindConfigstringIndex scans slots 1..max-1, so the usable slots
 * are 1..62 and slot 0 means "no animation". scriptmodelplayanim (0x4d9a00)
 * looks the name up in the same bank with create 0, refuses an unregistered
 * name, and stores the pair (slot, level.time); scriptmodelclearanim
 * (0x4512e0) stores (0, 0). There is no rate, blend, notify, queue or second
 * slot: a second play replaces the pair and slot 0 is the stop.
 *
 * C1 does not use IW4's configstring representation, so IW4's base 4042 is not
 * reused here. Only the bank shape (63 slots, precache-before-play, one
 * animation per entity, replace-on-play) is taken from IW4.
 *
 * Measured C1 consumer (D:/CoD/CODOL Builds/.../C1.exe), aligned
 * ------------------------------------------------------------
 * 43fcf9  if (nextState.eType (cent+0xe8) == 6) {          ; ET_SCRIPTMOVER
 * 43fd06     v = nextState wire 0x060 (cent+0x144)
 * 43fd0e     if (v <= 0) goto no-play                      ; whole field, not index
 * 43fd14     if (nextState wire 0x06c (cent+0x150) != 0) goto no-play
 * 43fd25     index = v & 0x7ff
 * 43fd2d     if (0x63a5f0(dobj->tree, index)) goto already-playing
 * 43fd45     if (v & 0x800) 0x63bbe0(dobj, index, ...) else 0x63c520(...)
 * 43fd73     parts    = [[dobj] + index*8 + 8]
 * 43fd7b     duration = parts numframes / framerate
 * 43fd9c     0x63c310(index, dobj, clock(0x61bea0) / duration)
 *
 * The tree the index is relative to is chosen by a different field. The DObj
 * constructor 0x59a800 stores the tree its caller passes (0x634660 writes it
 * to DObj+0); the caller 0x44372b takes that tree from the eType dispatch
 * 0x443540, whose ET_SCRIPTMOVER arm 0x4435bb reads nextState wire 0x094
 * (cent+0x178), returns no tree when it is zero, and otherwise loads
 * [0x262799c + wire094*4]. So the pair the client consumes is
 * (wire 0x094 = tree, wire 0x060 = entry index inside that tree).
 *
 * Wire widths, from the measured 1.1.1.13 eType 6 table
 * (src/codol_entity_fields.inc): 0x060 is 12 bits (11-bit index plus the
 * 0x800 variant bit), 0x094 is 4 bits, so a publishable client tree is 1..15,
 * and 0x06c is the codec-97 timestamp this arm requires to be 0.
 *
 * C1 tree registry, and why a server tree id is not a client tree id
 * -----------------------------------------------------------------
 * 0x5c9700(name, realm, &id) is C1's Scr_UsingTreeInternal: it interns the
 * canonicalised name (0x5cb860 skips leading '\\' and '/' and lowercases each
 * character), and for a new name does id = ++count[realm]
 * (0x5c97ff/0x5c9806, so ids are 1-based) and stores the name id at
 * 0x2627788 + (realm*128 + id)*2 (0x5c9823). 0x5c9f10(alloc, realm) then
 * walks 1..count and publishes each built tree at 0x26279a0 + realm*512 + ...
 * (0x5ca0bd). Realm 0's pointers therefore occupy 0x26279a0.., which is what
 * the renderer arm indexes as 0x262799c + id*4: the script-model tree
 * selector is an id in the CLIENT realm 0.
 *
 * The retained server has the same two-realm registry - Scr_UsingTreeInternal
 * (src/asmsource/_scr_animtree.asm:444) does id = ++gScrAnimPub.xanim_num[realm]
 * and stores the name at gScrAnimGlob+8 + (realm*128 + id)*2 - but Scr_UsingTree
 * (asm:614) passes realm 1 and Scr_GetAnims (asm:593) reads
 * gScrAnimPub+0x20c + id*4, which is xanim_lookup[1]: the SERVER realm. Ids in
 * the two realms are independent, each assigned in its own realm's
 * registration order, so a server tree id must never be published as the
 * client selector. Only C1's own producers write realm 0 - the four
 * 0x403770 blocks that register "multiplayer" (0xc306ac) and resolve the
 * nodes torso/legs/turning/code before 0x450bd2 loads the realm, and the
 * compiler's #using_animtree arm at 0x408263 - none of which the server sees.
 * The correspondence is therefore a name-to-id map this module requires to be
 * declared (CODOL_BindClientAnimTree); nothing here guesses one, and an
 * animation in a tree with no declared client id is refused rather than
 * published under a server id.
 *
 * Entry indices within one named tree do correspond: 0x5ca030 sizes a C1 tree
 * from a per-name entry count (0x5c92f0) and builds it from that named asset,
 * as the retained loader does, so two trees built from the same animtree name
 * enumerate the same entries in the same order. That is an inference from the
 * loader, not a measured client dump. Note the layouts differ and must not be
 * cast across: C1 allocates count*8+4 with its parts pointer at 8+index*8,
 * while the retained XAnim_s (src/xassets/xanims.h) has debugName/size/
 * debugAnimNames before entries[], so its parts sit at 16+index*8. This module
 * only reads retained trees, through Scr_GetAnims and XAnimGetAnimDebugName.
 *
 * What this module does not do
 * ----------------------------
 * It does not write a configstring, an entity state field or a snapshot. It
 * keeps the live per-entity intent that the GSC handlers produce, and hands
 * out a captured value object (codol_model_anim_t) plus a pure encoder, so the
 * publication path never has to look a live entity up by number while it is
 * serialising an archived state. The archived capture/copy plumbing belongs to
 * codol_entitystate_ext. GSC producers capture the resolved fields there;
 * snapshot copies and the internal archive stream retain them, and the model
 * entity overlay publishes them. GSC registration remains pending.
 */
#ifndef CODOL_MODEL_ANIMATION_H
#define CODOL_MODEL_ANIMATION_H

#include <stdint.h>
#pragma pack(push, 8)

#ifdef __cplusplus
extern "C" {
#endif

/* IW4 capacity, kept exactly: slot 0 is "no animation", 1..62 are usable. */
#define CODOL_MP_ANIM_SLOTS 63
/* One entry per entity number: MAX_GENTITIES (2048, entity.h GENTITYNUM_BITS
 * 11) in this tree; it was left at 1024 when entities were widened, which
 * silently dropped scriptmodel/destructible animation on entity 1024+. Checked, not
 * assumed, by every entry point that takes an entity number. */
#define CODOL_MODEL_ANIMATION_ENTITIES 2048
/* C1 43fd25: the index the client uses is `wire060 & 0x7ff`. */
#define CODOL_MODEL_ANIM_INDEX_MASK 0x7ffu
/* C1 43fd45: bit 0x800 of the same 12-bit field selects 0x63bbe0. */
#define CODOL_MODEL_ANIM_VARIANT_BIT 0x800u
/* Wire 0x094 is 4 bits and 0 means "no tree" (C1 4435dd), so a client tree
 * selector this arm can carry is 1..15. */
#define CODOL_MODEL_ANIM_CLIENT_TREES 15
/* Realm-local tree ids are 1-based and bounded by the 128-slot realm table,
 * on both sides (asm:478 shifts the realm by 7; C1 0x5c9f10 by 8 for words). */
#define CODOL_MODEL_ANIM_TREES 128
/* The realm Scr_GetAnims and Scr_UsingTree use (asm:593, asm:614). */
#define CODOL_MODEL_ANIM_SERVER_REALM 1

/* A captured animation. Every field is a value: nothing in it has to be
 * resolved again later, which is what lets an archived state be published
 * without reading live game state. */
typedef struct {
    unsigned slot;        /* precache bank slot, 0 when none. */
    unsigned server_tree; /* 1-based id in the retained realm-1 registry. */
    unsigned client_tree; /* declared realm-0 id for wire 0x094, 1..15. */
    unsigned index;       /* entry index inside that tree, <= 0x7ff. */
    unsigned variant;     /* 0 or 1; C1's 0x800 bit. */
    int start_time;       /* server time of the play that produced this. */
    unsigned sequence;    /* server-side play counter, see below. */
    unsigned char active; /* 0 = this entity carries no animation. */
} codol_model_anim_t;

/* Map lifetime. Clears the bank, the client-tree bindings and every
 * per-entity animation. */
void CODOL_ResetModelAnimations(void);
/* Native entity initialization/reuse: discard animation, play history and
 * tree binding. Does not alter the map's bank or client-tree registry. */
void CODOL_ResetEntityModelAnimation(unsigned entity);

/* --- precache bank (IW4 shape) --------------------------------------- */

/* Returns the slot for name, registering it when it is new. Returns -1 for an
 * invalid name and for bank overflow, which is the arm IW4 reports as
 * "G_FindConfigstringIndex: overflow mp anim". Never returns 0. Registration
 * is idempotent for a repeated name and does not resolve or load an asset,
 * because the reference precache does not either. */
int CODOL_RegisterMpAnimName(const char *name);
/* The slot of an already registered name, or 0 when it was never precached.
 * Does not register. */
int CODOL_FindMpAnimName(const char *name);
/* The registered name of a slot, or NULL for slot 0, an out of range slot and
 * an unused slot. Borrowed, valid until the next reset. */
const char *CODOL_MpAnimName(unsigned slot);

/* --- retained (realm 1) animtree registry ---------------------------- */

/* The number of trees Scr_UsingTree has registered in the server realm; ids
 * run 1..count. */
unsigned CODOL_ServerAnimTreeCount(void);
/* Copy every server tree's canonical registered name out of the compiler's
 * using_xanim_lookup table. MUST be called at the end of script loading,
 * while those variable objects are still alive -- Scr_EndLoadAnimTrees
 * ClearObject()s the container and recycles the ids. Without it
 * CODOL_ServerAnimTreeName falls back to XAnim_s->debugName, which is only
 * populated when com_developer is set, so on a production launch every tree
 * would be nameless. */
void CODOL_SnapshotServerAnimTreeNames(void);
/* The canonical name tree id was registered under, or NULL for an id outside
 * 1..count and for a slot whose name string is empty. Borrowed.
 * Answers from the snapshot above when one has been taken; do not assume a
 * developer build. */
const char *CODOL_ServerAnimTreeName(unsigned server_tree);
/* The entry index of name inside one specific tree. Returns 1 and writes
 * *index on a match; returns 0 for an id outside 1..count, a tree that was
 * registered but never built (Scr_GetAnims null), a tree with no debug name
 * table, a name no entry carries, and a matching entry whose index the 11-bit
 * wire field cannot carry. Never scans another tree. */
int CODOL_FindAnimInServerTree(unsigned server_tree, const char *name, unsigned *index);

/* --- client (realm 0) correspondence --------------------------------- */

/* The producer of the client's realm-0 ids, measured this pass
 * ----------------------------------------------------------
 * The client does not learn its animtrees from the server and does not learn
 * them from script: BG_LoadAnimList (C1 0x408310) reads the rawfiles
 * "animlists/<name>.animlist" out of the loaded zones and BG_TryLoadAnimList
 * (0x408040, path format "animlists/%s.animlist" at 0xc3efc4) tokenises each
 * one. A token starting with '=' (0x4081f6) sets the current animtree name;
 * every other token appends one anim entry at bgs+0x901d8[count] with
 * count = bgs+0x921d8 bounded by 0x800 (0x408220), and registers the current
 * animtree with Scr_UsingTreeInternal(name, realm) (0x408263), which hands out
 * ids 1,2,3.. in first-registration order. The load order is fixed
 * (0x40831E..0x4083E3):
 *
 *   count = 0
 *   "common"                                     always
 *   "common_actor_shared"   if (flags & 0x0d)
 *   "common_human"          if (flags & 0x01)    each of these four clears its
 *   "common_dog"            if (flags & 0x02)    own bit when the list is
 *   "common_civilian"       if (flags & 0x04)    absent
 *   "common_zombie"         if (flags & 0x08)
 *   <mapname>                                    always, "mapname" dvar
 *
 * with flags = bgs+0x921f8, loaded from cgs+0x164 at 0x450af8. Only after that
 * does the client register its own "multiplayer" tree (0x450ba1 calls the
 * 0x403770 block, which registers 0xc306ac four times), and only then does the
 * loader 0x5c9f10 (0x450bd2) walk ids 1..count[realm] and publish the built
 * trees at 0x26279a0 + realm*512 + (id-1)*4 - the array the ET_SCRIPTMOVER arm
 * indexes as [0x262799c + wire094*4] (0x4435df).
 *
 * So the correspondence is reproducible from data the server also has: parse
 * the same animlists in the same order and the realm-0 ids fall out. That is
 * what CODOL_LoadClientAnimTrees does. It is a producer, not a declaration.
 *
 * Two things this does NOT establish, and which this module still refuses to
 * guess (see obj/claude-workers/animation-binding-report.md):
 *   - the entry index inside a tree (wire 0x060) is still resolved against the
 *     retained server tree; C1's own per-tree entry order was not measured;
 *   - the realm passed to every one of these calls is [bgs+0x921f4], which no
 *     instruction in .text writes, so realm 0 is inference from the absence of
 *     a writer (C1's virtualised .tvm0 section was not decoded).
 */

/* The bits of the animlist flag word (C1 0x408354..0x4083c4). */
#define CODOL_ANIMLIST_HUMAN     0x01u
#define CODOL_ANIMLIST_DOG       0x02u
#define CODOL_ANIMLIST_CIVILIAN  0x04u
#define CODOL_ANIMLIST_ZOMBIE    0x08u
/* C1 0x40834a gates "common_actor_shared" on this mask of the same word. */
#define CODOL_ANIMLIST_ACTOR_SHARED_MASK 0x0du
/* C1 0x408220: the anim entry array is [0x800]; registration stops with it. */
#define CODOL_ANIMLIST_MAX_ENTRIES 0x800u

/* Rebuild the client realm-0 registry by replaying BG_LoadAnimList's order for
 * map_name and anim_flags, reading each list with CODOL_LoadEngineRawFile
 * ("animlists/<name>.animlist"). Clears the previous registry first, exactly as
 * 0x40831E zeroes the entry count. Returns the number of lists that were
 * present and parsed (0 when none were; multiplayer is still registered).
 * Invalid mounted rawfiles or registry overflow return -1 and clear the partial registry, leaving
 * tree_count unchanged. *tree_count, when given, receives the resulting number
 * of registered client trees, including any beyond the 15 the wire can carry.
 * A map_name of NULL or "" skips only the trailing per-map list. */
int CODOL_LoadClientAnimTrees(const char *map_name, unsigned anim_flags,
                              unsigned *tree_count);
/* Replay collected animation tokens into the server trees already declared by
 * scripts, immediately before those trees are built. Client-only trees are
 * skipped. This prevents map animations named only by animlists from pruning. */
unsigned CODOL_RegisterServerAnimListReferences(void);
/* Replay one animlist body, in the order its tokens appear, against the
 * registry as it currently stands. Exposed for the same reason C1 exposes
 * BG_TryLoadAnimList: the per-map list is one more body in the same sequence.
 * Returns the number of animtree registrations it performed, or -1 if the
 * registry is full. On failure earlier registrations remain; the map loader
 * clears the entire partial registry before returning its error. */
int CODOL_ParseAnimListClientTrees(const char *text, int length);
/* Number of client trees the registry holds; ids are 1..count. */
unsigned CODOL_ClientAnimTreeCount(void);
/* The name id client_tree was registered under, or NULL. Borrowed. */
const char *CODOL_ClientAnimTreeName(unsigned client_tree);

/* Declare that the tree registered on this server under tree_name is the
 * client realm-0 id client_tree. This is the manual override for a registry
 * the animlists could not produce; it writes the same ordered table, so it
 * must agree with it. Names are compared canonically (leading separators
 * skipped, case folded), which is the form both sides intern. Returns 0 for an
 * invalid name, for a client_tree outside 1..15, when that id already holds a
 * different name, and when that name already holds a different id. Re-stating
 * the same pair succeeds. */
int CODOL_BindClientAnimTree(const char *tree_name, unsigned client_tree);
/* The client id for a server tree id, matched by name. Returns 0 when the
 * server tree does not exist, has no name, is in no client registry, or landed
 * on an id the 4-bit wire field cannot carry. */
int CODOL_ClientAnimTreeForServerTree(unsigned server_tree, unsigned *client_tree);
/* Number of registered client trees, for the diagnostic that has to say
 * whether a refusal came from an empty registry. */
unsigned CODOL_ClientAnimTreeBindingCount(void);

/* --- resolution ------------------------------------------------------ */

/* Resolve an animation name to a publishable (tree, index) pair.
 * server_tree != 0 restricts the search to that one tree. server_tree == 0
 * searches only the trees that have a declared client binding and requires
 * exactly one of them to carry the name: an ambiguous name is refused, not
 * resolved to whichever tree happens to be registered first. Returns 1 and
 * fills *out (slot and start_time are left at 0; the caller sets those);
 * returns 0 otherwise. */
int CODOL_ResolveMpAnim(const char *name, unsigned server_tree, codol_model_anim_t *out);

/* --- per-entity live intent ------------------------------------------ */

/* Bind an entity to one server tree, so its plays resolve inside that tree
 * only. 0 removes the binding. Returns 0 for an out of range entity and for a
 * tree id outside 1..count. */
int CODOL_BindEntityAnimTree(unsigned entity, unsigned server_tree);
unsigned CODOL_EntityAnimTree(unsigned entity);

/* scriptmodelplayanim's store. slot must be a registered bank slot; the pair
 * is resolved through CODOL_ResolveMpAnim with the entity's tree binding.
 * Returns 0 without mutating when the entity is out of range, the slot is not
 * registered, the name resolves in no bound tree, or the resolution is
 * ambiguous, so an entity is never left carrying an animation that cannot be
 * published. A second play replaces the first and advances the sequence. */
int CODOL_SetModelAnimation(unsigned entity, unsigned slot, int start_time, int variant);
/* GSC publication transaction: resolve without mutation, capture the encoded
 * fields, then commit immediately on the same server thread. Commit accepts
 * only the value just prepared for that entity; it performs no fallible work. */
int CODOL_PrepareModelAnimation(unsigned entity,unsigned slot,int start_time,
                                int variant,codol_model_anim_t *out);
void CODOL_CommitModelAnimation(unsigned entity,const codol_model_anim_t *prepared);
/* scriptmodelclearanim's store. Clearing an entity that carries no animation
 * succeeds. Keeps its tree binding and play history; entity reuse must call
 * CODOL_ResetEntityModelAnimation instead. */
int CODOL_ClearModelAnimation(unsigned entity);
/* Capture what this entity currently carries. Returns 1 and fills *out for an
 * entity with an animation; returns 0 and zeroes *out otherwise, so an entity
 * without an animation is never captured as slot 0 at time 0 by accident. */
int CODOL_ModelAnimationCaptureLive(unsigned entity, codol_model_anim_t *out);
/* The bank slot and issue time this entity carries, for script-facing
 * queries. Returns 0 for an out of range entity and for an entity with no
 * animation, leaving the outputs untouched. */
int CODOL_ModelAnimationState(unsigned entity, unsigned *slot, int *start_time);
/* The animation name this entity carries, or NULL. Borrowed. */
const char *CODOL_ModelAnimationName(unsigned entity);
/* How many plays this entity has been given. It increases on every play,
 * including a replay of the animation it is already carrying. It is server
 * state only: the measured arm starts an animation the DObj is not already
 * running (C1 43fd2d) and no same-animation restart input is established, so
 * this counter has no wire encoding and must not be invented into one. */
unsigned CODOL_ModelAnimationSequence(unsigned entity);

/* --- wire encoding --------------------------------------------------- */

/* Encode a captured animation into the two eType 6 fields the measured arm
 * consumes: *wire060 = (index & 0x7ff) | (variant ? 0x800 : 0) and
 * *wire094 = the declared client tree. Returns 1 only for a capture the
 * client would actually start; returns 0 - leaving both outputs untouched -
 * for an inactive capture, a capture with no client tree, an index the field
 * cannot carry, and a value of 0, which C1 43fd0e reads as "no animation".
 * Pure: it reads nothing but its argument, so it is safe on an archived
 * capture. The caller must also leave wire 0x06c at 0 (C1 43fd14). */
int CODOL_ModelAnimationEncode(const codol_model_anim_t *state, uint32_t *wire060, uint32_t *wire094);
/* The two fields a cleared entity publishes. Both are 0: wire 0x060 zero is
 * the no-play input, and wire 0x094 zero selects no tree. The ordinary script
 * model DObj path passes wire094 at43e974/43e986 to443610. Its cache check
 * at43e58e compares this selector with the cached one; a change calls42be50,
 * which removes the old DObj map entry and calls634740 before rebuilding.
 * A delivered nonzero-to-zero tree transition therefore invalidates the old
 * DObj too. Same-animation replay without that transition remains unresolved. */
void CODOL_ModelAnimationEncodeCleared(uint32_t *wire060, uint32_t *wire094);

#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
