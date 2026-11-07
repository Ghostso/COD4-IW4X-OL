/* T5's scripted-animation GSC surface: the builtins that consume a %anim
 * reference variable.
 *
 * Reference, MEASURED unless marked
 * ---------------------------------
 * D:/CoD/OpenBLOPS Game/Server/game_mp/g_scr_main_mp.cpp holds T5's own
 * GScr_SetAnimInternal / GScr_SetAnimKnobInternal / GScr_SetAnimKnobAllInternal
 * / GScr_SetFlaggedAnim*Internal / GScr_ClearAnim / GScr_GetAnimTime /
 * GScr_SetAnimTime, each annotated with the retail SP address it came from.
 * Parameter order, defaults (weight 1, goal time 0.2, rate 1), the range
 * checks, the error texts and the flag bit meanings below are taken from
 * there, not invented:
 *
 *   flags bit 0 = "complete" (XAnimSetComplete* over the plain entry point)
 *   flags bit 1 = bRestart
 *   so 0 = Limited, 1 = plain, 2 = LimitedRestart, 3 = Restart.
 *
 * The animation command types are T5's too (its own comment: "Command types
 * are 1 = clear, 3 = anim, 4 = knob, 5 = knob-all, 6 = set-time"), and C1
 * 1.1.1.13 agrees. MEASURED in C1.exe, executor 0x443e90, jump table at
 * 0x444140 indexed by type-1:
 *
 *   type 1 -> 0x443f1d  0x63b210(tree, ref, cmd+0x24)          clear
 *   type 2 -> 0x443f35  0x63b250(...)                          clear (strict)
 *   type 3 -> 0x443f4d  arg2&1 ? 0x63c730 : 0x63c520           anim
 *   type 4 -> 0x443fed  arg2&1 ? 0x63b8b0 : 0x63bbe0           knob
 *   type 5 -> 0x44408f  arg2&1 ? 0x63bad0 : 0x63b9c0           knob-all
 *   type 6 -> 0x444126  0x63c310(ref, tree, cmd+0x24)          set time
 *
 * and `arg2 & 1` is read at 0x443f5b/0x443ffb/0x44409d as `test $0x1,%cl` with
 * `je` taking the *plain* arm, while 0x63b9c0 and 0x63bad0 both begin by
 * calling 0x63bbe0 exactly as the retained CoD4 XAnimSetGoalWeightKnobAll
 * (src/asmsource/_xanim.asm:12466) begins by calling XAnimSetGoalWeightKnob.
 * That identifies 0x63bbe0 as the Knob entry point and therefore
 *
 *   wire type = plain / knob / knob-all,   wire arg2 bit 0 = complete,
 *                                          wire arg2 bit 1 = restart.
 *
 * NOTE, and see the doc: src/codol/player/codol_dog_animation.c's apply_batch
 * reads the same two fields as "type = plain/complete, arg2 bit 0 = knob",
 * which agrees with C1 on (3,0) and (4,1) and disagrees on (3,1) and (4,0).
 * This file emits and applies the C1 reading. It therefore does not route
 * through CODOL_DogAnimApplyBatch; it appends to the same journal directly.
 *
 * notifyType: MEASURED, XAnimInfo+0x6 is read only by XAnimProcessClientNotify
 * (_xanim.asm:7570, `movzx ecx, word [eax+0x6]; test cx,cx; jz return`), which
 * a dedicated server never runs. XAnimProcessServerNotify (:4483) gates purely
 * on the DObj entnum and on notifyName (XAnimInfo+0x4). T5's value is
 * reproduced anyway because it costs nothing and C1 recomputes its own from
 * the wire goal weight (0x443f60: weight > 0.001 ? 2 : 0).
 *
 * Notetrack delivery needs nothing from this file. MEASURED: G_RunFrame
 * (_g_main_mp.asm:1284) calls G_DObjUpdateServerTime(ent, 1) for every in-use
 * entity and runs Scr_RunCurrentThreads whenever it returns nonzero;
 * DObjUpdateServerInfo -> XAnimUpdateTimeAndNotetrack -> XAnimProcessServerNotify
 * (_xanim.asm:4483) calls Scr_AddConstString(<notetrack>) + Scr_NotifyNum(
 * dobj->entnum - 1, 0, notifyName, 1) per notetrack, and at state.time == 1.0
 * notifies g_endNotetrackName ("end", interned by XAnimInit at :13181).
 * That is exactly the `self waittill (flagName, note)` that T5's
 * animscripts\shared::DoNoteTracks loops on, so DoNoteTracks stays pure GSC
 * as it is in T5.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifdef CODOL_SERVER
#include "codol_script_anim.h"
#include "scr_vm_functions.h"
#include "xassets/xanims.h"
#include "codol_actor_anim_journal.h"
#include "qcommon_io.h"

#include <math.h>
#include <string.h>

/* codol_actor_lifecycle.h is a C++ header (its extern "C" is unguarded), so
 * the one accessor this file needs is declared here instead of including it.
 * It answers the tree a live actor or an actor corpse owns, and NULL for
 * every other entity. */
extern struct XAnimTree_s *CODOL_ActorOwnedTree(gentity_t *entity);

/* Retained CoD4 XAnim, src/asmsource/_xanim.asm. The signature comments there
 * are the transcription of the original prototypes; note that the Knob form
 * has no notifyType parameter while the plain and Complete forms do. */
extern unsigned int Scr_GetAnim(unsigned int paramIndex, struct XAnimTree_s *tree);
extern int XAnimSetGoalWeight(DObj *obj, unsigned int anim, float goalWeight,
                              float goalTime, float rate, unsigned int notifyName,
                              unsigned int notifyType, int bRestart);
extern int XAnimSetCompleteGoalWeight(DObj *obj, unsigned int anim, float goalWeight,
                                      float goalTime, float rate, unsigned int notifyName,
                                      unsigned int notifyType, int bRestart);
extern int XAnimSetGoalWeightKnob(DObj *obj, unsigned int anim, float goalWeight,
                                  float goalTime, float rate, unsigned int notifyName,
                                  int bRestart);
extern int XAnimSetGoalWeightKnobAll(DObj *obj, unsigned int anim, unsigned int rootAnim,
                                     float goalWeight, float goalTime, float rate,
                                     unsigned int notifyName, int bRestart);
extern void XAnimClearTreeGoalWeights(struct XAnimTree_s *tree, unsigned int anim, float blend);
extern void XAnimSetTime(struct XAnimTree_s *tree, unsigned int anim, float fraction);
extern float XAnimGetTime(const struct XAnimTree_s *tree, unsigned int anim);
/* src/asmsource/_codol_xanim_complete_knob.asm: Knob plus the ancestor
 * completion loop that the retained tree has no XAnimSetCompleteGoalWeightKnob
 * for. cdecl(obj, ref, weight, blend, rate, restart, notifyName). */
extern int CODOL_XAnimSetCompleteGoalWeightKnobNotified(DObj *obj, unsigned int anim,
                                                        float goalWeight, float goalTime,
                                                        float rate, int bRestart,
                                                        unsigned int notifyName);
/* Same file: KnobAll plus T5's XAnimSetCompleteGoalWeightKnobAll completion
 * walk (OpenBLOPS xanim.cpp:3989 -> XAnimSetCompleteGoalWeightNode :3906),
 * which raises the root anim's own record and every record above it to goal
 * 1. The retained KnobAll stops one level below the root anim, and the root
 * anim's record is born with a zeroed state (XAnimEnsureGoalWeightParent), so
 * without the walk the whole knobbed branch hangs under a weight-0 record and
 * never receives time (docs/CODOL_ZOMBIE_ANIM_SYNC_20260921.md).
 * cdecl(obj, anim, rootAnim, weight, blend, rate, notifyName, restart). */
extern int CODOL_XAnimSetCompleteGoalWeightKnobAll(DObj *obj, unsigned int anim,
                                                   unsigned int rootAnim, float goalWeight,
                                                   float goalTime, float rate,
                                                   unsigned int notifyName, int bRestart);

/* T5 command types, its own naming. 2 (clear-strict) has no script command. */
#define ANIMCMD_CLEAR    1u
#define ANIMCMD_ANIM     3u
#define ANIMCMD_KNOB     4u
#define ANIMCMD_KNOBALL  5u
#define ANIMCMD_SETTIME  6u

/* T5 GScr_SetAnimInternal's flags byte. */
#define ANIMFLAG_COMPLETE 1
#define ANIMFLAG_RESTART  2

typedef struct {
    gentity_t *ent;
    struct XAnimTree_s *tree;
    DObj *obj;
} anim_ent_t;

/* The retained XAnim info pool (src/asmsource/_xanim.asm:13269): 4096 records
 * of 56 bytes, index 0 the null record. XAnimSetGoalWeight* allocate one
 * record per (tree, anim) they touch and thread them by parent/children/next,
 * starting at XAnimTree_s::children (the root info). The diagnostics below
 * read it directly because the retained query exports cannot answer "did the
 * clip land": XAnimGetWeight() returns 0.0 both for "no record" and for
 * "record present, weight not yet blended", and XAnimGetAnimName() reads the
 * developer-only debugAnimNames table (NULL at developer 0). */
extern XAnimInfo g_xAnimInfo[4096];
#define ANIM_INFO_COUNT 4096u

/* Info record of `anim` in `tree`, or 0 when the tree holds none. */
static unsigned find_info(const struct XAnimTree_s *tree, unsigned anim)
{
    unsigned stack[64], sp = 0, guard = 0;
    if (!tree->children || tree->children >= ANIM_INFO_COUNT) return 0;
    stack[sp++] = tree->children;
    while (sp && guard++ < ANIM_INFO_COUNT) {
        unsigned i = stack[--sp], c, g2;
        if (!i || i >= ANIM_INFO_COUNT) continue;
        if (g_xAnimInfo[i].animIndex == anim) return i;
        for (c = g_xAnimInfo[i].children, g2 = 0; c && c < ANIM_INFO_COUNT && g2 < 256;
             c = g_xAnimInfo[c].next, ++g2)
            if (sp < 64) stack[sp++] = c;
    }
    return 0;
}

static unsigned count_infos(const struct XAnimTree_s *tree)
{
    unsigned stack[64], sp = 0, guard = 0, n = 0;
    if (!tree->children || tree->children >= ANIM_INFO_COUNT) return 0;
    stack[sp++] = tree->children;
    while (sp && guard++ < ANIM_INFO_COUNT) {
        unsigned i = stack[--sp], c, g2;
        if (!i || i >= ANIM_INFO_COUNT) continue;
        ++n;
        for (c = g_xAnimInfo[i].children, g2 = 0; c && c < ANIM_INFO_COUNT && g2 < 256;
             c = g_xAnimInfo[c].next, ++g2)
            if (sp < 64) stack[sp++] = c;
    }
    return n;
}

/* A developer-independent name for an animtree entry: the clip's own
 * XAnimParts::name for a leaf, "#index(blend)" for a blend node. */
static const char *anim_entry_name(const XAnim_s *anims, unsigned ref, char *buf, size_t size)
{
    if (anims && ref < anims->size) {
        const XAnimEntry *e = &anims->entries[ref];
        if (!e->numAnims && e->u.parts && e->u.parts->name) return e->u.parts->name;
        Com_sprintf(buf, (int)size, "#%u(%s)", ref, e->numAnims ? "blend" : "leaf?");
        return buf;
    }
    Com_sprintf(buf, (int)size, "#%u(out of range)", ref);
    return buf;
}

/* Bounded, always-on report of every animation transaction that XAnim
 * accepted, and a LOUD warning for the one failure XAnim never reports:
 * returning 0 without leaving a record for the clip in the tree. MEASURED
 * need, docs/CODOL_ZOMBIE_ANIM_KNOB_20260921.md: a zm zombie went a whole
 * session with "no clip playing" and not one line explained it, because the
 * retained entry points only signal the two T5 script errors and the actor
 * diagnostic could not name what it saw.
 *
 * Bound: the first ANIM_REPORT_FULL transactions of each actor incarnation
 * are printed in full (the spawn pose, the first move cycles), then one line
 * per ANIM_REPORT_PERIOD_MS per actor. The zombie move loop re-issues its
 * knob-all every 0.4 s for the whole match; unbounded that is 15 lines a
 * second for six zombies. The warning keeps its own once-a-second bound. */
#define ANIM_REPORT_FULL 6
#define ANIM_REPORT_PERIOD_MS 10000
static struct { unsigned generation; unsigned shown; int lastTime, lastWarn; } s_animReport[MAX_GENTITIES];

static void anim_report(const anim_ent_t *e, const char *method, unsigned int type,
                        unsigned int ref, unsigned int rootRef, float goalWeight,
                        float goalTime, float rate, int flags, int xanimResult)
{
    const unsigned entnum = (unsigned)e->ent->s.number;
    const unsigned generation = CODOL_ACTOR_INCARNATION(e->ent->useCount);
    char nameBuf[32], rootBuf[32];
    const char *name, *rootName;
    unsigned info, rootInfo;
    int wantsRecord;
    if (entnum >= MAX_GENTITIES) return;
    if (s_animReport[entnum].generation != generation) {
        s_animReport[entnum].generation = generation;
        s_animReport[entnum].shown = 0;
        s_animReport[entnum].lastTime = s_animReport[entnum].lastWarn = 0;
    }
    name = anim_entry_name(e->tree->anims, ref, nameBuf, sizeof(nameBuf));
    rootName = type == ANIMCMD_KNOBALL
        ? anim_entry_name(e->tree->anims, rootRef, rootBuf, sizeof(rootBuf)) : "-";
    info = find_info(e->tree, ref);
    rootInfo = e->tree->children;
    /* The setters that must leave a record behind. clear/settime may not. */
    wantsRecord = (type == ANIMCMD_ANIM || type == ANIMCMD_KNOB || type == ANIMCMD_KNOBALL)
                  && goalWeight > 0.0f && xanimResult == 0;

    if (wantsRecord && !info) {
        if (!s_animReport[entnum].lastWarn || level.time - s_animReport[entnum].lastWarn >= 1000 ||
            level.time < s_animReport[entnum].lastWarn) {
            s_animReport[entnum].lastWarn = level.time;
            Com_PrintWarning(CON_CHANNEL_SERVER,
                "CoDOL anim: %s() ent %d: XAnim returned 0 for anim %u '%s' (root %u '%s') "
                "but tree %p holds NO record for it afterwards (root info %u, %u records) "
                "-- the clip did not land on the actor's tree\n",
                method, entnum, ref, name, rootRef, rootName, (const void *)e->tree,
                rootInfo, count_infos(e->tree));
        }
    } else if (wantsRecord && rate == 0.0f) {
        /* Legal in T5 ("must set nonnegative rate" admits 0) but it freezes
         * the clip at its current time: a locomotion cycle at rate 0 is a
         * standing actor with a walk pose. Once a second, so a script that
         * does it every frame cannot bury the log. */
        if (!s_animReport[entnum].lastWarn || level.time - s_animReport[entnum].lastWarn >= 1000 ||
            level.time < s_animReport[entnum].lastWarn) {
            s_animReport[entnum].lastWarn = level.time;
            Com_PrintWarning(CON_CHANNEL_SERVER,
                "CoDOL anim: %s() ent %d: anim %u '%s' set with playback rate 0; "
                "it will hold its current frame\n", method, entnum, ref, name);
        }
    }

    if (s_animReport[entnum].shown >= ANIM_REPORT_FULL &&
        s_animReport[entnum].lastTime &&
        level.time - s_animReport[entnum].lastTime < ANIM_REPORT_PERIOD_MS &&
        level.time >= s_animReport[entnum].lastTime)
        return;
    ++s_animReport[entnum].shown;
    s_animReport[entnum].lastTime = level.time;
    if (info) {
        const XAnimInfo *n = &g_xAnimInfo[info];
        Com_Printf(CON_CHANNEL_SERVER,
            "CoDOL anim: %s() ent %d tree %p (DObj tree %p, anims %p size %u, root info %u) "
            "type %u anim %u '%s' root %u '%s' weight %.2f blend %.2f rate %.2f%s%s -> xanim %d; "
            "record %u: g %.2f w %.2f t %.3f rate %.2f, %u records in tree\n",
            method, entnum, (const void *)e->tree, (const void *)DObjGetTree(e->obj),
            (const void *)e->tree->anims, e->tree->anims->size, rootInfo,
            type, ref, name, rootRef, rootName, goalWeight, goalTime, rate,
            (flags & ANIMFLAG_COMPLETE) ? " complete" : "",
            (flags & ANIMFLAG_RESTART) ? " restart" : "", xanimResult,
            info, n->state.goalWeight, n->state.weight, n->state.time, n->state.rate,
            count_infos(e->tree));
    } else {
        Com_Printf(CON_CHANNEL_SERVER,
            "CoDOL anim: %s() ent %d tree %p (DObj tree %p, anims %p size %u, root info %u) "
            "type %u anim %u '%s' root %u '%s' weight %.2f blend %.2f rate %.2f%s%s -> xanim %d; "
            "no record for it, %u records in tree\n",
            method, entnum, (const void *)e->tree, (const void *)DObjGetTree(e->obj),
            (const void *)e->tree->anims, e->tree->anims->size, rootInfo,
            type, ref, name, rootRef, rootName, goalWeight, goalTime, rate,
            (flags & ANIMFLAG_COMPLETE) ? " complete" : "",
            (flags & ANIMFLAG_RESTART) ? " restart" : "", xanimResult,
            count_infos(e->tree));
    }
}

/* T5 GScr_GetEntAnimTree + the "No model exists." check every one of these
 * methods performs before touching XAnim. The tree requirement is narrower
 * here than in T5 on purpose: only an actor (or an actor corpse) owns a server
 * animtree on this server, and only an actor's commands are carried by the
 * snapshot's animation-command section. Anything else is refused by name
 * rather than animated server-side and lost on the wire. */
static int anim_receiver(scr_entref_t ref, const char *method, anim_ent_t *out)
{
    gentity_t *ent;
    if (ref.classnum || ref.entnum >= MAX_GENTITIES) {
        Scr_ObjectError("not an entity");
        return 0;
    }
    ent = &g_entities[ref.entnum];
    if (!ent->r.inuse) {
        Scr_ObjectError("not an entity");
        return 0;
    }
    out->ent = ent;
    out->tree = CODOL_ActorOwnedTree(ent);
    if (!out->tree || !out->tree->anims || !out->tree->anims->size) {
        Scr_ObjectError(va("%s() requires an entity with a server animtree; "
                           "only actors own one on this server", method));
        return 0;
    }
    out->obj = Com_GetServerDObj(ent->s.number);
    if (!out->obj) {
        Scr_ObjectError("No model exists.");
        return 0;
    }
    if (DObjGetTree(out->obj) != out->tree) {
        Scr_ObjectError(va("%s(): this entity's DObj does not carry its owned "
                           "animtree", method));
        return 0;
    }
    return 1;
}

/* T5 GScr_GetOptionalFloat (SP 0x008016B0 region): an undefined parameter
 * keeps the default rather than reading zero. */
static float optional_float(unsigned int index, float fallback)
{
    return Scr_GetType(index) ? Scr_GetFloat(index) : fallback;
}

static float clampf(float v, float lo, float hi)
{
    if (!isfinite(v)) return lo;
    return v < lo ? lo : (v > hi ? hi : v);
}

/* Resolve one %anim parameter against this entity's tree. Scr_GetAnim
 * (_scr_vm.asm:5706) raises "type %s is not an anim" for a non-VAR_ANIMATION
 * parameter and "anim '%s' in animtree '%s' does not belong to the entity's
 * animtree '%s'" when the reference was compiled against a different tree,
 * both through Scr_ErrorJumpOut, so a failure never returns here. */
static unsigned int anim_param(unsigned int index, struct XAnimTree_s *tree)
{
    unsigned int ref = Scr_GetAnim(index, tree) & 0xffffu;
    /* Scr_GetAnim proves the reference belongs to this tree but never bounds
     * its index, and everything downstream - XAnim, entries[].parent, the
     * 11-bit wire ref - indexes with it. */
    if (ref >= tree->anims->size) {
        Scr_ParamError((int)index, "animation index is outside this animtree");
        return 0;
    }
    return ref;
}

/* T5 uses XAnimHasTime, which the retained CoD4 XAnim does not export. Its
 * predicate is reproduced from the data: a primitive always has a time, and a
 * blended parent only has one when it is a sync group. The sync bits are
 * loopsync (1) and nonloopsync (2), assigned by GetAnimTreeParseProperties
 * (src/cscr_animtree.cpp); codol_dog_animation.c's notified_target_proven
 * requires the same `flags & 3` before it will hang a notify on a non-leaf. */
static int anim_has_time(const XAnim_s *anims, unsigned int ref)
{
    if (!anims || ref >= anims->size) return 0;
    if (!anims->entries[ref].numAnims) return 1;
    return (anims->entries[ref].u.animParent.flags & 3) != 0;
}

/* Publish one animation transaction: apply it to the server's own XAnim tree
 * first, then append it to the delivery journal, so a refused operation
 * publishes nothing. T5 turns a nonzero XAnim return into a script error
 * (GScr_HandleAnimError), not a fatal, and so does this.
 *
 * The journal validator (codol_actor_anim_journal.c:valid_event) bounds the
 * floats at weight <= 5, rate <= 5, blend <= 1.7. T5's own snapshot clamp
 * (G_StoreAnimCommand, SP 0x004E7D80) is tighter -- weight 0..1, goal time
 * 0..1.5, rate 0..3 -- and is applied to the published copy only, while XAnim
 * still receives the script's values, exactly as retail does. */
static void anim_publish(const anim_ent_t *e, const char *method, unsigned int type,
                         unsigned int ref, unsigned int rootRef, float goalWeight,
                         float goalTime, float rate, float fraction, int flags,
                         unsigned int notifyName)
{
    codol_actor_anim_event_t event;
    const int restart = (flags & ANIMFLAG_RESTART) != 0;
    const int complete = (flags & ANIMFLAG_COMPLETE) != 0;
    const unsigned int notifyType = goalWeight > 0.001f ? 2u : 0u;
    int error = 0;

    switch (type) {
    case ANIMCMD_CLEAR:
        XAnimClearTreeGoalWeights(e->tree, ref, goalTime);
        break;
    case ANIMCMD_SETTIME:
        XAnimSetTime(e->tree, ref, fraction);
        break;
    case ANIMCMD_ANIM:
        error = complete
            ? XAnimSetCompleteGoalWeight(e->obj, ref, goalWeight, goalTime, rate,
                                         notifyName, notifyType, restart)
            : XAnimSetGoalWeight(e->obj, ref, goalWeight, goalTime, rate,
                                 notifyName, notifyType, restart);
        break;
    case ANIMCMD_KNOB:
        error = complete
            ? CODOL_XAnimSetCompleteGoalWeightKnobNotified(e->obj, ref, goalWeight,
                                                           goalTime, rate, restart,
                                                           notifyName)
            : XAnimSetGoalWeightKnob(e->obj, ref, goalWeight, goalTime, rate,
                                     notifyName, restart);
        break;
    default: /* ANIMCMD_KNOBALL */
        error = complete
            ? CODOL_XAnimSetCompleteGoalWeightKnobAll(e->obj, ref, rootRef, goalWeight,
                                                      goalTime, rate, notifyName, restart)
            : XAnimSetGoalWeightKnobAll(e->obj, ref, rootRef, goalWeight, goalTime,
                                        rate, notifyName, restart);
        break;
    }

    if (error) {
        /* T5 GScr_HandleAnimError, verbatim. */
        if (error == 1) Scr_Error("root anim is not an ancestor of the anim");
        else Scr_Error("cannot flag anim since it has 0 effective goal weight");
        return;
    }
    anim_report(e, method, type, ref, rootRef, goalWeight, goalTime, rate, flags, error);

    memset(&event, 0, sizeof(event));
    event.generation = CODOL_ACTOR_INCARNATION(e->ent->useCount);
    event.command.entity = (uint16_t)e->ent->s.number;
    /* T5 G_StoreAnimCommand: `level.time ? level.time : 50`. The journal
     * refuses time 0. */
    event.command.time = (uint32_t)(level.time ? level.time : 50);
    event.command.type = (uint8_t)type;
    event.command.ref = (uint16_t)ref;
    event.command.sub = (uint16_t)rootRef;
    event.command.arg2 = (uint8_t)((complete ? 1 : 0) | (restart ? 2 : 0));
    event.command.goal_weight = clampf(goalWeight, 0.0f, 1.0f);
    event.command.blend = clampf(goalTime, 0.0f, 1.5f);
    event.command.playback_rate = clampf(rate, 0.0f, 3.0f);
    event.command.fraction = clampf(fraction, 0.0f, 1.0f);
    if (!event.generation) {
        /* An entity that has never been allocated cannot be addressed by the
         * journal, whose events are keyed on (entity, incarnation).
         *
         * Throttled to one line a second, exactly like the journal refusal
         * below and for the same reason. An actor whose incarnation never
         * arrives hits this for EVERY animation on EVERY frame: MEASURED
         * 2026-09-20, one zombie produced 96 of these in a single zm match
         * and helped bury the log. The condition is systematic rather than
         * per-call, so a line a second loses nothing. */
        static int lastIncarnationComplaint;
        if (!lastIncarnationComplaint ||
            level.time - lastIncarnationComplaint >= 1000 ||
            level.time < lastIncarnationComplaint) {
            lastIncarnationComplaint = level.time;
            Com_PrintWarning(CON_CHANNEL_SERVER,
                "CoDOL anim: %s() on entity %d with no incarnation; not published "
                "(throttled to one line a second)\n",
                method, e->ent->s.number);
        }
        return;
    }
    if (!CODOL_ActorAnimJournalAppend(&event, 1)) {
        /* A systematic refusal (a journal cut already past this server time,
         * for instance) would otherwise print once per animation per actor per
         * frame. One line a second still surfaces it. */
        static int lastComplaint;
        if (!lastComplaint || level.time - lastComplaint >= 1000 ||
            level.time < lastComplaint) {
            lastComplaint = level.time;
            Com_PrintWarning(CON_CHANNEL_SERVER,
                "CoDOL anim: %s() on entity %d applied but could not be published (%s)\n",
                method, e->ent->s.number,
                codol_actor_delivery_failure ? codol_actor_delivery_failure
                                             : "journal refused the transaction");
        }
    }
}

/* ------------------------------------------------------------------------
 * clearanim(%anim, blendTime)
 * T5 SP 0x00800660. Two parameters, no defaults, no XAnim return value.
 * ---------------------------------------------------------------------- */
void CODOL_Scr_ClearAnim(scr_entref_t ref)
{
    anim_ent_t e;
    unsigned int anim;
    float blend;
    if (!anim_receiver(ref, "clearanim", &e)) return;
    if (Scr_GetNumParam() != 2) { Scr_Error("incorrect number of parameters"); return; }
    anim = anim_param(0, e.tree);
    blend = Scr_GetFloat(1);
    if (!(blend >= 0.0f)) { Scr_ParamError(1, "must set nonnegative blend time"); return; }
    anim_publish(&e, "clearanim", ANIMCMD_CLEAR, anim, 0, 0.0f, blend, 1.0f, 0.0f, 0, 0);
}

/* ------------------------------------------------------------------------
 * The un-flagged weight setters.
 *   <ent> setanim(%anim [, weight [, goalTime [, rate]]])
 * T5 GScr_SetAnimInternal / GScr_SetAnimKnobInternal: one to four parameters,
 * defaults weight 1 / goalTime 0.2 / rate 1. setanim bounds the weight at 1,
 * the knob forms do not (read straight off SP 0x00800880).
 * ---------------------------------------------------------------------- */
static void set_anim_common(scr_entref_t ref, const char *method, unsigned int type,
                            int flags, int boundWeight)
{
    anim_ent_t e;
    unsigned int anim;
    float weight = 1.0f, goalTime = 0.2f, rate = 1.0f;
    int params;
    if (!anim_receiver(ref, method, &e)) return;
    params = Scr_GetNumParam();
    if (params < 1 || params > 4) { Scr_Error("incorrect number of parameters"); return; }
    if (params >= 4) {
        rate = optional_float(3, rate);
        if (!(rate >= 0.0f)) { Scr_ParamError(3, "must set nonnegative rate"); return; }
    }
    if (params >= 3) {
        goalTime = optional_float(2, goalTime);
        if (!(goalTime >= 0.0f)) { Scr_ParamError(2, "must set nonnegative goal time"); return; }
    }
    if (params >= 2) {
        weight = optional_float(1, weight);
        if (!(weight >= 0.0f) || (boundWeight && weight > 1.0f)) {
            Scr_ParamError(1, "must set nonnegative weight"); return;
        }
    }
    anim = anim_param(0, e.tree);
    anim_publish(&e, method, type, anim, 0, weight, goalTime, rate, 0.0f, flags, 0);
}

void CODOL_Scr_SetAnim(scr_entref_t ref)
{ set_anim_common(ref, "setanim", ANIMCMD_ANIM, ANIMFLAG_COMPLETE, 1); }
void CODOL_Scr_SetAnimLimited(scr_entref_t ref)
{ set_anim_common(ref, "setanimlimited", ANIMCMD_ANIM, 0, 1); }
void CODOL_Scr_SetAnimRestart(scr_entref_t ref)
{ set_anim_common(ref, "setanimrestart", ANIMCMD_ANIM, ANIMFLAG_COMPLETE | ANIMFLAG_RESTART, 1); }
void CODOL_Scr_SetAnimKnob(scr_entref_t ref)
{ set_anim_common(ref, "setanimknob", ANIMCMD_KNOB, ANIMFLAG_COMPLETE, 0); }
void CODOL_Scr_SetAnimKnobLimited(scr_entref_t ref)
{ set_anim_common(ref, "setanimknoblimited", ANIMCMD_KNOB, 0, 0); }
void CODOL_Scr_SetAnimKnobRestart(scr_entref_t ref)
{ set_anim_common(ref, "setanimknobrestart", ANIMCMD_KNOB, ANIMFLAG_COMPLETE | ANIMFLAG_RESTART, 0); }

/* ------------------------------------------------------------------------
 * The knob-all forms.
 *   <ent> setanimknoball(%anim, %rootAnim [, weight [, goalTime [, rate]]])
 * T5 GScr_SetAnimKnobAllInternal, SP 0x00800D40: "Parameters shift by one
 * against the non-All form", two to five parameters, and two explicit refusals
 * -- a root anim in a different tree, and a root anim equal to the anim.
 *
 * The retained CoD4 XAnim exports XAnimSetGoalWeightKnobAll but no
 * XAnimSetCompleteGoalWeightKnobAll. The "complete" half is NOT optional and
 * NOT limited to ancestors above the root anim: the KnobAll walk drives the
 * chain from the anim up to -- but excluding -- the root anim (C1 0x63bb7a
 * `fld1` feeding the per-ancestor setter; retained _xanim.asm:12467 returns
 * the moment the parent's animIndex equals rootAnim), and the root anim's own
 * record is created by XAnimEnsureGoalWeightParent with a zeroed state. Under
 * a compact script animtree the tree root is entry 0 and `%body` is a child
 * of it (entry 2 on zm_prototype_sh, parent 0), so `body`'s record stayed at
 * goal 0 / weight 0 / rate 0 and XAnimUpdateTimeAndNotetrack returned at it
 * before any zombie clip ever received time (MEASURED, build de015044:
 * `anim ai_zombie_walk_v4 w 1.00 g 1.00 t 0.00 ot 0.00` for a whole session).
 * CODOL_XAnimSetCompleteGoalWeightKnobAll (_codol_xanim_complete_knob.asm)
 * now reproduces T5's completion walk, so the former "root anim must be a
 * top-level node" refusal is gone; T5 has no such refusal either.
 * ---------------------------------------------------------------------- */
static void set_anim_knoball_common(scr_entref_t ref, const char *method, int flags)
{
    anim_ent_t e;
    unsigned int anim, root, walk, guard;
    float weight = 1.0f, goalTime = 0.2f, rate = 1.0f;
    int params;
    if (!anim_receiver(ref, method, &e)) return;
    params = Scr_GetNumParam();
    if (params < 2 || params > 5) { Scr_Error("incorrect number of parameters"); return; }
    if (params >= 5) {
        rate = optional_float(4, rate);
        if (!(rate >= 0.0f)) { Scr_ParamError(4, "must set nonnegative rate"); return; }
    }
    if (params >= 4) {
        goalTime = optional_float(3, goalTime);
        if (!(goalTime >= 0.0f)) { Scr_ParamError(3, "must set nonnegative goal time"); return; }
    }
    if (params >= 3) {
        weight = optional_float(2, weight);
        if (!(weight >= 0.0f)) { Scr_ParamError(2, "must set nonnegative weight"); return; }
    }
    root = anim_param(1, e.tree);
    anim = anim_param(0, e.tree);
    /* Scr_GetAnim already refuses a reference from another tree, which covers
     * T5's "root anim is not in the same anim tree". */
    if (root == anim) { Scr_Error("root anim is not an ancestor of the anim"); return; }
    for (walk = anim, guard = 0; walk && guard <= e.tree->anims->size; ++guard) {
        if (walk == root) break;
        walk = e.tree->anims->entries[walk].parent;
    }
    if (walk != root) { Scr_Error("root anim is not an ancestor of the anim"); return; }
    anim_publish(&e, method, ANIMCMD_KNOBALL, anim, root, weight, goalTime, rate,
                 0.0f, flags, 0);
}

void CODOL_Scr_SetAnimKnobAll(scr_entref_t ref)
{ set_anim_knoball_common(ref, "setanimknoball", ANIMFLAG_COMPLETE); }
void CODOL_Scr_SetAnimKnobAllRestart(scr_entref_t ref)
{ set_anim_knoball_common(ref, "setanimknoballrestart", ANIMFLAG_COMPLETE | ANIMFLAG_RESTART); }

/* ------------------------------------------------------------------------
 * The flagged forms.
 *   <ent> setflaggedanim(flag, %anim [, weight [, goalTime [, rate]]])
 * T5 GScr_SetFlaggedAnimInternal / GScr_SetFlaggedAnimKnobInternal, SP
 * 0x00801870 / 0x00802220: "the notify string as parameter 0 and shift every
 * other parameter up by one; they also require a strictly positive weight
 * ('must set positive weight', not 'must set nonnegative weight') and reject
 * animations with no concept of time."
 *
 * `flag` is the notify name the engine will raise on this entity for every
 * notetrack of this animation and once more, as "end", when it completes --
 * which is what animscripts\shared::DoNoteTracks waits on.
 * ---------------------------------------------------------------------- */
static void set_flagged_anim_common(scr_entref_t ref, const char *method,
                                    unsigned int type, int flags)
{
    anim_ent_t e;
    unsigned int anim, notifyName;
    float weight = 1.0f, goalTime = 0.2f, rate = 1.0f;
    int params;
    if (!anim_receiver(ref, method, &e)) return;
    params = Scr_GetNumParam();
    if (params < 2 || params > 5) { Scr_Error("incorrect number of parameters"); return; }
    if (params >= 5) {
        rate = optional_float(4, rate);
        if (!(rate >= 0.0f)) { Scr_ParamError(4, "must set nonnegative rate"); return; }
    }
    if (params >= 4) {
        goalTime = optional_float(3, goalTime);
        if (!(goalTime >= 0.0f)) { Scr_ParamError(3, "must set nonnegative goal time"); return; }
    }
    if (params >= 3) {
        weight = optional_float(2, weight);
        if (!(weight > 0.0f)) { Scr_ParamError(2, "must set positive weight"); return; }
    }
    anim = anim_param(1, e.tree);
    notifyName = (unsigned int)(unsigned short)Scr_GetConstString(0);
    if (!anim_has_time(e.tree->anims, anim)) {
        Scr_ParamError(1, "blended nonsynchronized animation has no concept of time");
        return;
    }
    anim_publish(&e, method, type, anim, 0, weight, goalTime, rate, 0.0f, flags, notifyName);
}

void CODOL_Scr_SetFlaggedAnim(scr_entref_t ref)
{ set_flagged_anim_common(ref, "setflaggedanim", ANIMCMD_ANIM, ANIMFLAG_COMPLETE); }
void CODOL_Scr_SetFlaggedAnimLimited(scr_entref_t ref)
{ set_flagged_anim_common(ref, "setflaggedanimlimited", ANIMCMD_ANIM, 0); }
void CODOL_Scr_SetFlaggedAnimRestart(scr_entref_t ref)
{ set_flagged_anim_common(ref, "setflaggedanimrestart", ANIMCMD_ANIM, ANIMFLAG_COMPLETE | ANIMFLAG_RESTART); }
void CODOL_Scr_SetFlaggedAnimKnob(scr_entref_t ref)
{ set_flagged_anim_common(ref, "setflaggedanimknob", ANIMCMD_KNOB, ANIMFLAG_COMPLETE); }
void CODOL_Scr_SetFlaggedAnimKnobRestart(scr_entref_t ref)
{ set_flagged_anim_common(ref, "setflaggedanimknobrestart", ANIMCMD_KNOB, ANIMFLAG_COMPLETE | ANIMFLAG_RESTART); }
/* T5's MP table does not carry setflaggedanimknoblimited and its SP index
 * 122 was left unidentified, but the shipped IW4 animscripts tree in
 * bin/home/codol_rawfiles/animscripts calls it, and the flags rule the rest
 * of the family is built from fixes it exactly: Limited is flags 0. */
void CODOL_Scr_SetFlaggedAnimKnobLimited(scr_entref_t ref)
{ set_flagged_anim_common(ref, "setflaggedanimknoblimited", ANIMCMD_KNOB, 0); }
void CODOL_Scr_SetFlaggedAnimKnobLimitedRestart(scr_entref_t ref)
{ set_flagged_anim_common(ref, "setflaggedanimknoblimitedrestart", ANIMCMD_KNOB, ANIMFLAG_RESTART); }

/* setflaggedanimknoball(flag, %anim, %rootAnim [, weight [, goalTime [, rate]]])
 * T5 GScr_SetFlaggedAnimKnobAllInternal, SP 0x00801D70. This is the shape the
 * zombie animscripts use for locomotion, pain, melee and death. */
static void set_flagged_anim_knoball_common(scr_entref_t ref, const char *method, int flags)
{
    anim_ent_t e;
    unsigned int anim, root, notifyName, walk, guard;
    float weight = 1.0f, goalTime = 0.2f, rate = 1.0f;
    int params;
    if (!anim_receiver(ref, method, &e)) return;
    params = Scr_GetNumParam();
    if (params < 3 || params > 6) { Scr_Error("incorrect number of parameters"); return; }
    if (params >= 6) {
        rate = optional_float(5, rate);
        if (!(rate >= 0.0f)) { Scr_ParamError(5, "must set nonnegative rate"); return; }
    }
    if (params >= 5) {
        goalTime = optional_float(4, goalTime);
        if (!(goalTime >= 0.0f)) { Scr_ParamError(4, "must set nonnegative goal time"); return; }
    }
    if (params >= 4) {
        weight = optional_float(3, weight);
        if (!(weight > 0.0f)) { Scr_ParamError(3, "must set positive weight"); return; }
    }
    root = anim_param(2, e.tree);
    anim = anim_param(1, e.tree);
    notifyName = (unsigned int)(unsigned short)Scr_GetConstString(0);
    if (root == anim) { Scr_Error("root anim is not an ancestor of the anim"); return; }
    for (walk = anim, guard = 0; walk && guard <= e.tree->anims->size; ++guard) {
        if (walk == root) break;
        walk = e.tree->anims->entries[walk].parent;
    }
    if (walk != root) { Scr_Error("root anim is not an ancestor of the anim"); return; }
    if (!anim_has_time(e.tree->anims, anim)) {
        Scr_ParamError(1, "blended nonsynchronized animation has no concept of time");
        return;
    }
    anim_publish(&e, method, ANIMCMD_KNOBALL, anim, root, weight, goalTime, rate,
                 0.0f, flags, notifyName);
}

void CODOL_Scr_SetFlaggedAnimKnobAll(scr_entref_t ref)
{ set_flagged_anim_knoball_common(ref, "setflaggedanimknoball", ANIMFLAG_COMPLETE); }
void CODOL_Scr_SetFlaggedAnimKnobAllRestart(scr_entref_t ref)
{ set_flagged_anim_knoball_common(ref, "setflaggedanimknoballrestart",
                                  ANIMFLAG_COMPLETE | ANIMFLAG_RESTART); }

/* ------------------------------------------------------------------------
 * animscripted( notifyName, origin, angles, %anim [, mode [, %root [, rate
 *               [, goalTime]]]] ) / stopanimscripted()
 * T5 GScr_AnimScripted_SP (OpenBLOPS g_scr_main_mp.cpp:20638 ->
 * GScr_StartScriptedAnim_SP :20578): 4..8 parameters, refuses a dead AI,
 * pushes AIS_SCRIPTEDANIM, kills the animscript and runs animscripts/
 * zombie_scripted.gsc, whose init() defaults mode to "normal", root to
 * %body and goalTime to 0.2 and whose main() publishes the clip with the
 * flagged knob-all under the notify name.  The actor half of that state
 * (kill the animscript, hold selection/goal/route, face the angles, consume
 * the origin offset, pop on stopanimscripted or the clip's length) is
 * codol_actor_lifecycle.cpp CODOL_ActorScriptedAnimBegin/Stop; the clip half
 * is the same publish the knob-all builtins use, restart + complete, so the
 * notetracks reach the script exactly as setflaggedanimknoballrestart's do.
 * The default root is T5's %body: the top of the clip's ancestry below the
 * tree root (root anim 0).
 * MEASURED 2026-09-21 (docs/CODOL_ZOMBIE_WINDOW_20260921.md part 2): the
 * zm tear was published with setflaggedanimknoballrestart from the entity
 * thread while the move animscript kept knobbing the walk cycle every 0.2 s;
 * the tear clip never held weight and no "board" note fired all session.
 * ---------------------------------------------------------------------- */
extern int CODOL_ActorScriptedAnimBegin(gentity_t *ent, const float *origin, const float *angles,
                                        const char *mode, int durationMsec);
extern int CODOL_ActorScriptedAnimStop(gentity_t *ent, const char *why);
extern int __cdecl XAnimGetLengthMsec(const void *anims, unsigned animIndex);
void CODOL_Scr_AnimScripted(scr_entref_t ref)
{
    anim_ent_t e;
    unsigned int anim, root = 0, notifyName, walk, guard;
    float rate = 1.0f, goalTime = 0.2f, origin[3], angles[3];
    const char *mode = "normal";
    int params, lengthMsec;
    if (!anim_receiver(ref, "animscripted", &e)) return;
    params = Scr_GetNumParam();
    if (params < 4 || params > 8) { Scr_Error("Incorrect number of parameters for animscripted command"); return; }
    if (e.ent->health <= 0) { Scr_Error("tried to play a scripted animation on a dead AI"); return; }
    notifyName = (unsigned int)(unsigned short)Scr_GetConstString(0);
    Scr_GetVector(1, origin);
    Scr_GetVector(2, angles);
    anim = anim_param(3, e.tree);
    if (params >= 5 && Scr_GetType(4)) mode = Scr_GetString(4);
    if (params >= 6 && Scr_GetType(5)) root = anim_param(5, e.tree);
    if (params >= 7) {
        rate = optional_float(6, rate);
        if (!(rate >= 0.0f)) { Scr_ParamError(6, "must set nonnegative rate"); return; }
    }
    if (params >= 8) {
        goalTime = optional_float(7, goalTime);
        if (!(goalTime >= 0.0f)) { Scr_ParamError(7, "must set nonnegative goal time"); return; }
    }
    if (!root) {
        for (walk = anim, guard = 0; guard <= e.tree->anims->size; ++guard) {
            unsigned int parent = e.tree->anims->entries[walk].parent;
            if (!parent || parent >= e.tree->anims->size || parent == walk) break;
            walk = parent;
        }
        root = walk;
    }
    if (root == anim) { Scr_Error("root anim is not an ancestor of the anim"); return; }
    for (walk = anim, guard = 0; walk && guard <= e.tree->anims->size; ++guard) {
        if (walk == root) break;
        walk = e.tree->anims->entries[walk].parent;
    }
    if (walk != root) { Scr_Error("root anim is not an ancestor of the anim"); return; }
    if (!anim_has_time(e.tree->anims, anim)) {
        Scr_ParamError(3, "blended nonsynchronized animation has no concept of time");
        return;
    }
    lengthMsec = XAnimGetLengthMsec(e.tree->anims, anim);
    if (rate > 0.0f) lengthMsec = (int)((float)lengthMsec / rate);
    lengthMsec += (int)(goalTime * 1000.0f);
    if (!CODOL_ActorScriptedAnimBegin(e.ent, origin, angles, mode, lengthMsec)) {
        Scr_ObjectError("animscripted requires a live actor with its animscripts started");
        return;
    }
    anim_publish(&e, "animscripted", ANIMCMD_KNOBALL, anim, root, 1.0f, goalTime, rate,
                 0.0f, ANIMFLAG_COMPLETE | ANIMFLAG_RESTART, notifyName);
}
void CODOL_Scr_StopAnimScripted(scr_entref_t ref)
{
    gentity_t *ent;
    if (ref.classnum || ref.entnum >= MAX_GENTITIES) { Scr_ObjectError("not an entity"); return; }
    ent = &g_entities[ref.entnum];
    if (!ent->r.inuse) { Scr_ObjectError("not an entity"); return; }
    if (Scr_GetNumParam() != 0) { Scr_Error("incorrect number of parameters"); return; }
    /* T5 tolerates a stop with no scripted animation in flight (the tear
     * loop calls it after every exit); so does this. */
    CODOL_ActorScriptedAnimStop(ent, "stopanimscripted");
}

/* ------------------------------------------------------------------------
 * setanimtime(%anim, fraction) / getanimtime(%anim)
 * T5 SP 0x008027D0 / 0x008016C0. The time is the animation's normalized
 * position, 0..1.
 * ---------------------------------------------------------------------- */
void CODOL_Scr_SetAnimTime(scr_entref_t ref)
{
    anim_ent_t e;
    unsigned int anim;
    float fraction;
    if (!anim_receiver(ref, "setanimtime", &e)) return;
    if (Scr_GetNumParam() != 2) { Scr_Error("incorrect number of parameters"); return; }
    anim = anim_param(0, e.tree);
    fraction = Scr_GetFloat(1);
    if (!(fraction >= 0.0f) || fraction > 1.0f) {
        Scr_ParamError(1, "animation time must be between 0 and 1"); return;
    }
    if (!anim_has_time(e.tree->anims, anim)) {
        Scr_ParamError(0, "blended nonsynchronized animation has no concept of time");
        return;
    }
    anim_publish(&e, "setanimtime", ANIMCMD_SETTIME, anim, 0, 0.0f, 0.0f, 1.0f,
                 fraction, 0, 0);
}

void CODOL_Scr_GetAnimTime(scr_entref_t ref)
{
    anim_ent_t e;
    unsigned int anim;
    if (!anim_receiver(ref, "getanimtime", &e)) return;
    if (Scr_GetNumParam() != 1) { Scr_Error("incorrect number of parameters"); return; }
    anim = anim_param(0, e.tree);
    if (!anim_has_time(e.tree->anims, anim)) {
        Scr_ParamError(0, "blended nonsynchronized animation has no concept of time");
        return;
    }
    Scr_AddFloat(XAnimGetTime(e.tree, anim));
}

#endif
