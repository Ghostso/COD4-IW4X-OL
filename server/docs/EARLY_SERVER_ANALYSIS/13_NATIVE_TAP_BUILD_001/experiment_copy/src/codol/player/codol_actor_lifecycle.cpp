/* C1 actor pool 6C4F80: 32 stable identities; SP_actor6C4B50 allocates a
 * sentient after the actor and rolls back if either pool is exhausted.
 * T5 Actor_FinishSpawning runs the original aitype main on that entity.
 * This is native ownership, not AI or a replacement dog script.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifdef CODOL_SERVER
/* The retained headers declare C functions without linkage guards. */
extern "C" {
#include "codol_actor_lifecycle.h"
#include "codol_actor_scripts.h"
#include "codol_actor_delivery.h"
#include "g_shared.h"
#include "game/surfaceflags.h"
#include "entity.h"
#include "dobj.h"
#include "cscr_stringlist.h"
#include "cscr_variable.h"
#include "scr_vm_functions.h"
#include <string.h>
#include <math.h>
#include "server.h"
#include "codol_actor_physics.h"
#include "codol_dog_states.h"
#include "scr_vm.h"
#include "codol_model_animation.h"
#include "xassets/xanims.h"
#include "xassets/weapondef.h"
#include <stddef.h>
#include "codol_vehicle_wheel_anim.h"
}
extern "C" XAnim_s *Scr_GetAnims(unsigned);

extern "C" {
#include "codol_bot_nav.h"
/* codol_script_path_nodes.c: the map node record behind a graph node. */
const char *CODOL_PathNodeValue(unsigned index, const char *key);
}
extern "C" {
void Scr_DecTime(void);
void Scr_IncTime(void);
void Scr_RunCurrentThreads(void);
#include "codol_dog_combat.h"
#include "codol_player_appearance.h"
}

struct codol_actor_lifetime_s {
    gentity_s *entity;
    codol_sentient_t *sentient;
    unsigned generation;
    unsigned char allocated, typeStarted, initialized, scriptsStarted, switching;
    codol_actor_script_table_t scripts;
    short animThread;
    int animFunction, moveMode, animMode, scriptAnimMode;
    /* The species row this actor was initialized as; NULL until aitype
     * main() sets self.type. Every former "dog" literal in this file is
     * now a column of it (codol_actor_scripts.h). */
    const codol_actor_species_t *species;
    int enemyNum;
    unsigned enemyGeneration;
    float goal[3], goalRadius, goalHeight, stopAnimDistSq, lookAheadDir[3];
    unsigned char pathEndAnimNotified;
    unsigned char hasGoal, goalNotified;
    unsigned short route[CODOL_BOT_NODES];
    int routeCount, routeCursor, goalNode;
    /* Waypoint links this actor wedged on (see the stuck detector): the bot
     * graph marks links for players, and a "crouch" link can be a knee-high
     * wall a player vaults but a dog cannot step (mp_killhouse_sh nodes
     * 99/100 -> 103/104: a 32-unit cinderblock wall).  The planner skips
     * them for this actor from then on. */
    unsigned short bannedLinkFrom[8], bannedLinkTo[8];
    unsigned bannedLinkCount;
    /* Start nodes this actor wedged walking straight at from off the graph
     * (the route's first leg, where there is no link to ban): Prototype's
     * west yard node 255 (-865 102) sits behind a steep dirt face beside the
     * car that a +18 sweep clears but the actor's step cannot, and every
     * re-plan picked it again as the nearest node. */
    unsigned short bannedStart[4];
    unsigned bannedStartCount;
    int shortcutBanTime;
    /* Dog wall hop (T5 Actor_Dog_Exposed_Think -> the species "jump"
     * animscript over an obstacle in the path): the traversal rides the
     * negotiation hold with no begin/end node; start and landing are kept
     * so a hop that ends in solid can be finished honestly. */
    unsigned char wallHop;
    float hopStart[3], hopLanding[3];
    int hopTime, hopDiagTime;
    int lastRootMotionTime;
    codol_actor_physics_t physics;
    unsigned serverTree;
    XAnimTree_s tree;
    int animationState, lastAnimationTime;
    float animationRate, aimUp, aimLeft, lean, meleeAttackDistance;
    int scriptOrient; // 0 default, 1 fixed yaw, 2 enemy, 3 enemy/motion, 4 goal, 5 motion
    float scriptYaw;
    unsigned char safeToChangeScript, painPending;
    float damageYaw;
    int deathTime, enemySeenTime, talkMask;
    unsigned enemyModel;
    unsigned short weaponName;
    int lastMeleeTime;
    unsigned char ignoreAll;
    float engageMin, engageMinFalloff, engageMax, engageMaxFalloff;
    /* Flashbang state (T5 actor_s flashBanged / flashBangedStrength).
     * maps\mp\_dogs::flash_dogs sets it, the think then runs the species'
     * flashed animscript, and dog_flashed::main clears it with
     * setFlashBanged( false ) when its animation completes. */
    int flashBanged;
    float flashStrength;
    /* Diagnostics ("CoDOL actor:", every species): one summary line per second per actor and
     * one line per goal/route/animscript/animstate transition. */
    int diagTime, diagState, movesAccepted, movesRejected;
    /* Hostile sentients the last perception pass considered. "enemy -1
     * cand 0" is a targeting/registration failure; "enemy -1 cand 1" on a
     * sighted species is an occluded target. */
    int diagCandidates;
    float diagOrigin[3], lastTranslation[3], diagGoal[3];
    int savedContents;
    unsigned char routeFailNotified, routeDiagPrinted;
    /* Log rate limits: the route-FAILED and goal-set lines fire per goal
     * change, and a chased player changes the goal every frame (5,804 +
     * 2,476 lines in one zm session).  At most one line per 5 s per actor,
     * carrying the count since the last one. */
    int routeFailLogTime, routeFailCount, goalLogTime, goalLogCount;
    /* T5 codeGoal: the enemy attack spot carries its own (small) radius so
     * the chase never ends inside the script's 128-unit goalradius. */
    float chaseRadius;
    /* T5 Path_UpdateLeanAmount inputs and the stuck detector. */
    float prevMoveDir[2], stuckOrigin[3];
    int stuckTime, stuckCount;
    /* Root motion the animation asked for since the stuck window opened: a
     * wedge is motion asked for and refused; a clip that asks for none is a
     * stall of the animation and gets no repath. */
    float stuckAttempt;
    unsigned char stallDiagPrinted, windowDiagPrinted;
    /* T5 Actor_Negotiation_Start/Think: a node_negotiation_begin -> _end
     * traversal.  pending is raised by the route follower when the actor
     * reaches the begin node of such a leg; RunFrame then aligns the actor to
     * the node, hands the species' traversal animscript the pair, and holds
     * the mover (no chase goal, no stuck detector, no script re-selection)
     * until that thread ends or times out. */
    unsigned char negotiating, negotiationPending;
    int negotiationBegin, negotiationEnd, negotiationStartTime;
    float negotiationStartOrigin[3];
    /* T5 AIS_SCRIPTEDANIM (GScr_AnimScripted -> Actor_PushState + Actor_KillAnimScript
     * + animscripts/zombie_scripted): the animscript is dead, the clip the
     * builtin published owns the tree, the mover only faces the given angles,
     * consumes the origin offset and applies the clip's root motion.  Popped by
     * stopanimscripted(), the clip's length, or death. */
    unsigned char scripted, scriptedAlign;
    int scriptedStartTime, scriptedEndTime;
    float scriptedOrigin[3];
    /* Physics verdicts inside the stuck window: moves the physics refused
     * (start in solid) and moves it throttled to under half the asked
     * displacement.  A wedge needs one of them; a slow cycle has neither. */
    int stuckRejected, stuckBlocked;
    unsigned char slowDiagPrinted;
    int wedgeDiagCount; float wedgeDiagSpot[3];
};
#define DOG_DIAG(...) Com_Printf(CON_CHANNEL_SERVER, "CoDOL actor: " __VA_ARGS__)
static codol_actor_lifetime_t actors[CODOL_MAX_ACTOR_SLOTS];
struct actor_corpse_owner {
    gentity_s *entity;unsigned generation;int time;
    XAnimTree_s tree;codol_actor_physics_t physics;
};
static actor_corpse_owner corpses[8]; // original T5 actorCorpseInfo capacity
static int ActorBecomeCorpse(gentity_s *entity);
/* T5 SentientInfo_Copy gates teammate information by the RECEIVER species:
 * a sender only shares sight with a species it was told to talk to. The
 * dog row owns bit 1, so setTalkToSpecies("dog") behaves exactly as the
 * former hardcoded `talkMask & 1` did. */
static unsigned ActorTalkBit(const codol_actor_lifetime_t *a)
{
    return a && a->species ? a->species->talkBit : 0u;
}
static int ActorMayTarget(const codol_actor_lifetime_t *a, const codol_sentient_t *s);


codol_actor_lifetime_t *CODOL_ActorForEntity(gentity_s *entity)
{
    if (!entity || !entity->r.inuse) return NULL;
    codol_sentient_t *s = CODOL_Sentient_ForEntity(entity);
    if (!s || !s->isActor || (unsigned)s->actorSlot >= CODOL_MAX_ACTOR_SLOTS)
        return NULL;
    codol_actor_lifetime_t *a = &actors[s->actorSlot];
    if (!a->allocated || a->entity != entity || a->sentient != s ||
        a->generation != CODOL_ACTOR_INCARNATION(entity->useCount) ||
        s->handle.number != entity->s.number + 1) return NULL;
    return a;
}

codol_actor_lifetime_t *CODOL_ActorAllocate(gentity_s *entity, int team)
{
    if (!entity || !entity->r.inuse || entity->client ||
        entity->s.number < 0 || entity->s.number >= ENTITYNUM_WORLD ||
        entity->s.eType == ET_ACTOR_SPAWNER ||
        (unsigned)team >= CODOL_SENTIENT_TEAM_COUNT ||
        CODOL_Sentient_ForEntity(entity)) return NULL;
    unsigned slot;
    for (slot=0; slot<CODOL_MAX_ACTOR_SLOTS; ++slot)
        if (!actors[slot].allocated && !CODOL_Sentient_ActorBySlot(slot)) break;
    if (slot == CODOL_MAX_ACTOR_SLOTS) return NULL;
    /* C1 SP_actor scans all75 records directly. Class0 bypasses the
     * non-actor24-record recycling policy of makeEntitySentient. */
    codol_sentient_t *s = CODOL_Sentient_Alloc(0);
    if (!s) return NULL;
    CODOL_Sentient_Setup(s, entity, team);
    s->isActor = 1;
    s->actorSlot = (int)slot;
    codol_actor_lifetime_t *a = &actors[slot];
    memset(a, 0, sizeof(*a));
    a->entity = entity;
    a->sentient = s;
    a->generation = CODOL_ACTOR_INCARNATION(entity->useCount);
    a->allocated = 1;
    a->enemyNum = -1;
    a->lastRootMotionTime = -1;
    a->lastAnimationTime = -1;
    a->animationRate = 1.0f;
    a->safeToChangeScript = 1;
    a->goalRadius = 4.0f;
    a->goalHeight = 80.0f;
    a->goalNode = -1;
    a->deathTime = -1;
    a->lastMeleeTime = -1;
    a->talkMask = -1;
    entity->s.lerp.u.actor.actorSlot = (int)slot;
    return a;
}

int CODOL_ActorRunTypeMain(gentity_s *entity, int mainHandle)
{
    codol_actor_lifetime_t *a = CODOL_ActorForEntity(entity);
    if (!a || !mainHandle || a->typeStarted) return 0;
    unsigned generation = a->generation;
    /* Mark before entering GSC: a recursive initialization cannot run main
     * twice, and a script error must not cause a second partially run main. */
    a->typeStarted = 1;
    short thread = Scr_ExecEntThread(entity, mainHandle, 0);
    Scr_FreeThread(thread);
    a = CODOL_ActorForEntity(entity);
    return a && a->generation == generation;
}

/* Separate native actor namespace. Non-actor writes return zero so the VM
 * retains its ordinary dynamic-field fallback rather than stealing script
 * fields from players, vehicles or generic script entities. */
extern "C" void Scr_AddClassField(unsigned int, const char *, unsigned int);
extern "C" void CODOL_ActorRegisterFields(void)
{
    Scr_AddClassField(0, "team", 0x8000);
    Scr_AddClassField(0, "aiteam", 0x8000);
    Scr_AddClassField(0, "type", 0x8001);
    Scr_AddClassField(0, "enemy", 0x8002);
    Scr_AddClassField(0, "goalradius", 0x8003);
    Scr_AddClassField(0, "goalheight", 0x8004);
    Scr_AddClassField(0, "safetochangescript", 0x8005);
    Scr_AddClassField(0, "animplaybackrate", 0x8006);
    Scr_AddClassField(0, "meleeattackdist", 0x8007);
    Scr_AddClassField(0, "damageyaw", 0x8008);
    Scr_AddClassField(0, "ignoreall", 0x8009);
    Scr_AddClassField(0, "script_owner", 0x800a);
    Scr_AddClassField(0, "aiweapon", 0x800b);
    Scr_AddClassField(0, "stopanimdistsq", 0x800c);
    Scr_AddClassField(0, "lookaheaddir", 0x800d);
}
static const char *ActorTeamNames[CODOL_SENTIENT_TEAM_COUNT] = {
    "none", "axis", "allies", "team3", "team4", "team5", "team6"
};
extern "C" int CODOL_ActorSetField(unsigned classnum, int entnum, int offset)
{
    if (classnum || (unsigned)entnum >= ENTITYNUM_WORLD) return 0;
    codol_actor_lifetime_t *a = CODOL_ActorForEntity(&g_entities[entnum]);
    if (!a) return 0;
    if(offset==0x800d){Scr_Error("lookaheaddir is owned by native path following");return 1;}
    if(offset==0x800c){float value=Scr_GetFloat(0);if(!isfinite(value)||value<0)Scr_ParamError(0,"stopanimdistsq must be finite and nonnegative");else a->stopAnimDistSq=value;return 1;}
    if(offset==0x800b){Scr_SetString(&a->weaponName,Scr_GetConstString(0));return 1;}
    if(offset==0x8009){a->ignoreAll=Scr_GetInt(0)!=0;if(a->ignoreAll)CODOL_ActorSetEnemy(a->entity,NULL);return 1;}
    if(offset==0x800a){Scr_Error("script_owner is managed through setentityowner");return 1;}
    if (offset == 0x8008) {
        Scr_Error("actor damageyaw is owned by native damage processing");return 1;
    }
    if (offset == 0x8007) {
        float distance = Scr_GetFloat(0);
        if (!isfinite(distance) || distance < 0) Scr_ParamError(0, "meleeattackdist must be finite and nonnegative");
        else a->meleeAttackDistance = distance;
        return 1;
    }
    if (offset == 0x8005) {
        a->safeToChangeScript = Scr_GetInt(0) != 0;
        return 1;
    }
    if (offset == 0x8006) {
        float rate = Scr_GetFloat(0);
        if (!isfinite(rate) || rate <= 0 || rate > 5) {
            Scr_ParamError(0, "actor animation rate exceeds native animation command range (0,5]");
            return 1;
        }
        a->animationRate = rate;
        return 1;
    }
    if (offset == 0x8002) {
        Scr_Error("actor enemy is read-only; native perception owns enemy selection");
        return 1;
    }
    if (offset == 0x8003 || offset == 0x8004) {
        float number = Scr_GetFloat(0);
        if (!isfinite(number) || number < 0) {
            Scr_ParamError(0, "actor goal dimension must be finite and >= 0");
            return 1;
        }
        if (offset == 0x8003) a->goalRadius = fmaxf(4.0f, number);
        else a->goalHeight = fmaxf(80.0f, number);
        a->goalNotified = 0;
        return 1;
    }
    const char *value = Scr_GetString(0);
    if (offset == 0x8000) {
        for (unsigned i = 0; i < CODOL_SENTIENT_TEAM_COUNT; ++i)
            /* T5 _dogs::dog_manager_get_team returns "free" in a non-team
             * game; T5 sentients carry TEAM_FREE. Here FFA players are team
             * NONE too, so a free dog is team NONE and targets by owner. */
            if (!strcmp(value, ActorTeamNames[i]) || (!i && (!strcmp(value, "neutral") || !strcmp(value, "free")))) {
                /* Real targeting/class-mask consumers read this same record. */
                a->sentient->team = (int)i;
                a->entity->team = (int)i;
                return 1;
            }
        Scr_Error("actor team: unknown native sentient team");
        return 1;
    }
    if (offset == 0x8001) {
        const codol_actor_species_t *row = CODOL_ActorSpeciesByName(value);
        if (!row) {
            Scr_Error("actor type: no such native actor species");
            return 1;
        }
        a->species = row;
        /* C1 composition tree selector is independently resolved when its
         * actual DObj is initialized. T5 species zero is NOT a C1 tree index. */
        return 1;
    }
    Scr_Error("actor field: invalid registered field offset");
    return 1;
}
extern "C" void CODOL_ActorGetField(unsigned classnum, int entnum, int offset)
{
    if (classnum || (unsigned)entnum >= ENTITYNUM_WORLD) return;
    codol_actor_lifetime_t *a = CODOL_ActorForEntity(&g_entities[entnum]);
    if (!a) return;
    if(offset==0x800d){Scr_AddVector(a->lookAheadDir);return;}
    if(offset==0x800c){Scr_AddFloat(a->stopAnimDistSq);return;}
    if(offset==0x800b){Scr_AddString(a->weaponName?SL_ConvertToString(a->weaponName):"");return;}
    if(offset==0x8009){Scr_AddBool(a->ignoreAll);return;}
    if(offset==0x800a){if(a->entity->r.ownerNum.isDefined())Scr_AddEntity(a->entity->r.ownerNum.ent());return;}
    if (offset == 0x8000 && (unsigned)a->sentient->team < CODOL_SENTIENT_TEAM_COUNT)
        Scr_AddString(ActorTeamNames[a->sentient->team]);
    else if (offset == 0x8001 && a->species)
        Scr_AddString(a->species->name);
    else if (offset == 0x8002) {
        gentity_s *enemy = CODOL_ActorEnemy(&g_entities[entnum]);
        if (enemy) Scr_AddEntity(enemy);
    } else if (offset == 0x8003) Scr_AddFloat(a->goalRadius);
    else if (offset == 0x8004) Scr_AddFloat(a->goalHeight);
    else if (offset == 0x8005) Scr_AddBool(a->safeToChangeScript);
    else if (offset == 0x8006) Scr_AddFloat(a->animationRate);
    else if (offset == 0x8007) Scr_AddFloat(a->meleeAttackDistance);
    else if (offset == 0x8008) Scr_AddFloat(a->damageYaw);
}

gentity_s *CODOL_ActorEnemy(gentity_s *entity)
{
    codol_actor_lifetime_t *a = CODOL_ActorForEntity(entity);
    if (!a || (unsigned)a->enemyNum >= ENTITYNUM_WORLD) return NULL;
    gentity_s *enemy = &g_entities[a->enemyNum];
    if (!enemy->r.inuse || (unsigned)enemy->useCount != a->enemyGeneration ||
        enemy->health <= 0 || !CODOL_Sentient_ForEntity(enemy)) {
        a->enemyNum = -1;
        CODOL_DogCombatRelease(entity);
        return NULL;
    }
    return enemy;
}

int CODOL_ActorSetEnemy(gentity_s *entity, gentity_s *enemy)
{
    codol_actor_lifetime_t *a = CODOL_ActorForEntity(entity);
    if (!a) return 0;
    /* The entrance walk sets ignoreall until its barrier has been torn.
     * Damage can arrive during that walk; it must not let the attacker
     * replace the scripted entrance goal with a chase goal. */
    if (enemy && a->ignoreAll) return 0;
    codol_sentient_t *target = enemy ? CODOL_Sentient_ForEntity(enemy) : NULL;
    if (enemy && (!enemy->r.inuse || enemy == entity || enemy->health <= 0 ||
        !target || target->dontTarget || !ActorMayTarget(a, target))) return 0;
    int changed = a->enemyNum != (enemy ? enemy->s.number : -1) ||
        (enemy && a->enemyGeneration != (unsigned)enemy->useCount);
    if (!changed) return 1;
    CODOL_DogCombatRelease(entity);
    a->enemyNum = enemy ? enemy->s.number : -1;
    a->enemyGeneration = enemy ? (unsigned)enemy->useCount : 0;
    if (changed && enemy) {
        unsigned name = SL_GetString("enemy", 0);
        Scr_Notify(entity, (unsigned short)name, 0);
        SL_RemoveRefToString(name);
    }
    return 1;
}

/* Straight-line reachability for the direct-to-goal shortcut. The sweep is
 * lifted by the actor's step height: waypoints and goals sit on the floor,
 * and a floor-touching capsule reports every ramp, kerb and slope seam as a
 * hit, which is what kept every route "blocked". Physics still steps/slides. */
/* Other live actors do not block an actor's own movement or reachability
 * sweeps (T5 dogs negotiate around each other; here they pass through).
 * Contents are read live by the clip world, so no relink is needed. */
extern "C" void CODOL_ActorsPassable(gentity_s *self, int passable)
{
    for (unsigned i = 0; i < CODOL_MAX_ACTOR_SLOTS; ++i) {
        codol_actor_lifetime_t *o = &actors[i];
        if (!o->allocated || !o->entity || o->entity == self || !o->entity->r.inuse) continue;
        if (passable) { o->savedContents = o->entity->r.contents; o->entity->r.contents = 0; }
        else o->entity->r.contents = o->savedContents;
    }
}
static int ActorClearSegment(gentity_s *entity, const float *from, const float *to)
{
    trace_t trace;
    float mins[3], maxs[3], start[3], end[3];
    memcpy(mins, entity->r.mins, 12); memcpy(maxs, entity->r.maxs, 12);
    memcpy(start, from, 12); memcpy(end, to, 12);
    mins[2] += 18.0f; if (mins[2] > maxs[2] - 8.0f) mins[2] = maxs[2] - 8.0f;
    CODOL_ActorsPassable(entity, 1);
    G_TraceCapsule(&trace, start, mins, maxs, end, entity->s.number, entity->clipmask);
    CODOL_ActorsPassable(entity, 0);
    return !trace.startsolid && !trace.allsolid && trace.fraction == 1.0f;
}
/* Check the first movement step toward the node after a proposed waypoint
 * advance with the actor's real hull.  The lifted straight-line shortcut
 * intentionally ignores floor seams; it also misses the steep dirt face at
 * Prototype node 435, where a +18 sweep is clear but the actual actor's
 * forward trace hits a non-walkable (normal z .08/.22) slope at fraction 0.
 * A floor contact (normal z >= .7) is not an obstacle.  When the face is
 * steep, mirror physicsMove's up/forward/down step trial before refusing to
 * advance: a climbable kerb must remain traversable. */
static int ActorRouteContinuationBlocked(gentity_s *entity, const float *target)
{
    const float *start = entity->r.currentOrigin;
    float dx = target[0]-start[0], dy = target[1]-start[1];
    float length = sqrtf(dx*dx + dy*dy);
    if (length < 0.001f) return 0;
    float travel = fminf(length, 16.0f) / length;
    float ahead[3] = {start[0]+dx*travel, start[1]+dy*travel, start[2]};
    trace_t tr, upTrace, raisedTrace, landing;
    CODOL_ActorsPassable(entity, 1);
    G_TraceCapsule(&tr, start, entity->r.mins, entity->r.maxs,
        ahead, entity->s.number, entity->clipmask);
    if (!tr.startsolid && !tr.allsolid &&
        (tr.fraction >= 1.0f || tr.normal[2] >= 0.7f)) {
        CODOL_ActorsPassable(entity, 0);
        return 0;
    }
    float up[3] = {start[0], start[1], start[2]+18.0f};
    G_TraceCapsule(&upTrace, start, entity->r.mins, entity->r.maxs,
        up, entity->s.number, entity->clipmask);
    if (upTrace.startsolid || upTrace.allsolid || upTrace.fraction <= 0.0f) {
        CODOL_ActorsPassable(entity, 0);
        return 1;
    }
    float lift = 18.0f*upTrace.fraction;
    float raised[3] = {start[0], start[1], start[2]+lift};
    float raisedAhead[3] = {ahead[0], ahead[1], ahead[2]+lift};
    G_TraceCapsule(&raisedTrace, raised, entity->r.mins, entity->r.maxs,
        raisedAhead, entity->s.number, entity->clipmask);
    if (raisedTrace.startsolid || raisedTrace.allsolid || raisedTrace.fraction < 1.0f) {
        CODOL_ActorsPassable(entity, 0);
        return 1;
    }
    float down[3] = {raisedAhead[0], raisedAhead[1], raisedAhead[2]-lift-0.25f};
    G_TraceCapsule(&landing, raisedAhead, entity->r.mins, entity->r.maxs,
        down, entity->s.number, entity->clipmask);
    CODOL_ActorsPassable(entity, 0);
    return landing.startsolid || landing.allsolid ||
        landing.fraction >= 1.0f || landing.normal[2] < 0.7f;
}
/* Waypoint links are authored for player traversal and the combat-training
 * bots walk them without a per-edge trace; a per-edge capsule sweep rejected
 * every sloped link. Dogs skip prone/climb links (no traversal animations). */
static int ActorRouteWalkable(int stance)
{
    /* CODOL_BOT_NEGOTIATE is the map's node_negotiation_begin -> _end pair,
     * the link T5 Path_IsNegotiationLink hands EVERY actor (a window sill on
     * the zm maps: 12 of them ring zm_prototype_sh, and they are the only
     * links between the spawner yard and the interior).  Rejecting it as a
     * CLIMB, as this filter did until 2026-09-21, made every zombie route
     * fail on a connected graph -- see docs/CODOL_ZOMBIE_ROUTE_20260921.md. */
    return stance == CODOL_BOT_STAND || stance == CODOL_BOT_CROUCH || stance == CODOL_BOT_NEGOTIATE;
}
static int ActorStartBanned(const codol_actor_lifetime_t *a, int node)
{
    unsigned n = a->bannedStartCount < 4 ? a->bannedStartCount : 4;
    for (unsigned i = 0; i < n; ++i)
        if (a->bannedStart[i] == node) return 1;
    return 0;
}
static int ActorRouteContinuationBlocked(gentity_s *entity, const float *target);
/* The route endpoints for an actor: the nearest waypoint it may stand on and,
 * for the start, can walk to.  A bare nearest-node pick can land on a CLIMB
 * node (a player mantle, e.g. mp_killhouse_sh node 59 on the ladder at
 * (3691 169)), which the stance filter then refuses as an endpoint, so every
 * route to a goal beside it failed with "no path between nearest nodes"; and
 * the nearest node to a dog can be across a knee-high wall (killhouse node
 * 102 from (3199 -489)), which it then ran into for good.  The start is the
 * nearest of the eight closest walkable nodes the dog's hull can reach in a
 * straight line, else the nearest walkable one. */
static int ActorNearestWalkableNode(gentity_s *entity, const codol_actor_lifetime_t *a,
    const float *point, int reachable)
{
    /* Every species since 2026-10-01: zombies wedged on the same node-behind-
     * an-obstacle starts the dogs did (Prototype yard, VPS 17733 log). */
    int nearest = CODOL_BotNavNearest(point);
    if (nearest < 0 || !a) return nearest;
    enum { CANDIDATES = 8 };
    int best[CANDIDATES]; float bestDistance[CANDIDATES]; int count = 0;
    for (int i = 0, n = CODOL_BotNavCount(); i < n; ++i) {
        const float *p = CODOL_BotNavPoint(i);
        if (!p || !ActorRouteWalkable(CODOL_BotNavStance(i))) continue;
        if (reachable && ActorStartBanned(a, i)) continue;
        float d = (float)Vec3DistanceSq(p, point);
        int slot;
        if (count < CANDIDATES) slot = count++;
        else if (d >= bestDistance[CANDIDATES-1]) continue;
        else slot = CANDIDATES - 1;
        while (slot > 0 && bestDistance[slot-1] > d) {
            best[slot] = best[slot-1]; bestDistance[slot] = bestDistance[slot-1]; --slot;
        }
        best[slot] = i; bestDistance[slot] = d;
    }
    if (!count) return nearest;
    /* Reachable: the lifted straight sweep is clear AND the actor's own first
     * step toward the node is (the lifted sweep passes over a knee-high
     * steep face the step cannot climb). */
    if (reachable)
        for (int c = 0; c < count; ++c)
            if (ActorClearSegment(entity, point, CODOL_BotNavPoint(best[c])) &&
                !ActorRouteContinuationBlocked(entity, CODOL_BotNavPoint(best[c]))) return best[c];
    return best[0];
}
/* A dog embedded in solid with no clear waypoint within 64 units cannot
 * move at all (every sweep starts solid).  T5 has no such state -- its
 * actors never leave the navmesh -- so the dog is placed on the nearest
 * clear walkable waypoint that no living player can see (a pop in view is
 * worse than a longer hop), else the nearest clear one. */
static int ActorWaypointHidden(const float *point)
{
    for (int i = 0; i < level.maxclients; ++i) {
        gentity_s *player = &g_entities[i];
        if (!player->r.inuse || !player->client || player->health <= 0) continue;
        float eye[3] = {player->r.currentOrigin[0], player->r.currentOrigin[1],
            player->r.currentOrigin[2] + player->client->ps.viewHeightCurrent};
        float target[3] = {point[0], point[1], point[2] + 32.0f}, zero[3] = {0,0,0};
        trace_t tr;
        G_TraceCapsule(&tr, eye, zero, zero, target, i, 0x1);
        if (!tr.startsolid && tr.fraction >= 1.0f) return 0;
    }
    return 1;
}
static int ActorRecoverFromSolid(gentity_s *entity, codol_actor_lifetime_t *a)
{
    int bestHidden = -1, bestAny = -1;
    float hiddenDistance = INFINITY, anyDistance = INFINITY, bestOrigin[2][3];
    for (int i = 0, n = CODOL_BotNavCount(); i < n; ++i) {
        const float *p = CODOL_BotNavPoint(i);
        if (!p || !ActorRouteWalkable(CODOL_BotNavStance(i))) continue;
        float d = (float)Vec3DistanceSq(p, entity->r.currentOrigin);
        if (d >= anyDistance && d >= hiddenDistance) continue;
        float origin[3] = {p[0], p[1], p[2]+1.0f};
        trace_t probe;
        CODOL_ActorsPassable(entity, 1);
        G_TraceCapsule(&probe, origin, entity->r.mins, entity->r.maxs, origin, entity->s.number, entity->clipmask);
        CODOL_ActorsPassable(entity, 0);
        if (probe.startsolid || probe.allsolid) continue;
        if (d < anyDistance) { anyDistance = d; bestAny = i; memcpy(bestOrigin[1], origin, 12); }
        if (d < hiddenDistance && ActorWaypointHidden(origin)) {
            hiddenDistance = d; bestHidden = i; memcpy(bestOrigin[0], origin, 12);
        }
    }
    int pick = bestHidden >= 0 ? 0 : 1, node = bestHidden >= 0 ? bestHidden : bestAny;
    if (node < 0) return 0;
    DOG_DIAG("ent %d embedded in solid at (%.0f %.0f %.0f): placed on %s waypoint %d (%.0f %.0f %.0f), %.0f away\n",
        entity->s.number, entity->r.currentOrigin[0], entity->r.currentOrigin[1], entity->r.currentOrigin[2],
        pick == 0 ? "the nearest hidden" : "the nearest (none hidden)", node,
        bestOrigin[pick][0], bestOrigin[pick][1], bestOrigin[pick][2], sqrtf(pick == 0 ? hiddenDistance : anyDistance));
    G_SetOrigin(entity, bestOrigin[pick]);
    memcpy(a->sentient->origin, bestOrigin[pick], 12);
    memset(a->physics.velocity, 0, 12);
    a->routeCount = a->routeCursor = 0;
    SV_LinkEntity(entity);
    return 1;
}
static int ActorLinkBanned(const codol_actor_lifetime_t *a, int from, int to)
{
    unsigned n = a->bannedLinkCount < 8 ? a->bannedLinkCount : 8;
    for (unsigned i = 0; i < n; ++i)
        if ((a->bannedLinkFrom[i] == from && a->bannedLinkTo[i] == to) ||
            (a->bannedLinkFrom[i] == to && a->bannedLinkTo[i] == from)) return 1;
    return 0;
}
static int ActorRouteEdge(int from, int to, void *context)
{
    if (!ActorRouteWalkable(CODOL_BotNavStance(from)) || !ActorRouteWalkable(CODOL_BotNavStance(to))) return 0;
    const codol_actor_lifetime_t *a = context ? CODOL_ActorForEntity((gentity_s *)context) : NULL;
    return !a || !ActorLinkBanned(a, from, to);
}
/* Once per actor: which nodes the failed route ran between and why the
 * search gave up, so a failure on a connected graph names its cause. */
static void ActorRouteFailedDetail(gentity_s *entity, codol_actor_lifetime_t *a, int from, int to)
{
    const codol_bot_route_stats_t *st = CODOL_BotNavLastRouteStats();
    const float *sp = CODOL_BotNavPoint(from), *gp = CODOL_BotNavPoint(to);
    static const char *const stops[4] = {"found", "frontier exhausted", "bad node index", "path over capacity"};
    if (a->routeDiagPrinted || !sp || !gp) return;
    a->routeDiagPrinted = 1;
    DOG_DIAG("ent %d route detail: start node %d (%.0f %.0f %.0f) %.0f away stance %d component %d -> goal node %d (%.0f %.0f %.0f) %.0f from goal stance %d component %d; %s after %d expansions, %d links rejected by the stance filter%s\n",
        entity->s.number, from, sp[0], sp[1], sp[2], sqrtf((float)Vec3DistanceSq(sp, entity->r.currentOrigin)), CODOL_BotNavStance(from), CODOL_BotNavComponent(from),
        to, gp[0], gp[1], gp[2], sqrtf((float)Vec3DistanceSq(gp, a->goal)), CODOL_BotNavStance(to), CODOL_BotNavComponent(to),
        stops[st->stop & 3], st->expanded, st->filtered, from == to ? " (start == goal)" : "");
}
/* T5 Actor_PathEndActions notifies "bad_path" when no route exists; the
 * ported _dogs.gsc patrol waits on it to pick another node. Once per goal. */
static void ActorRouteFailed(gentity_s *entity, codol_actor_lifetime_t *a, const char *why)
{
    if (a->routeFailNotified) return;
    a->routeFailNotified = 1;
    ++a->routeFailCount;
    if (level.time - a->routeFailLogTime >= 5000) {
        DOG_DIAG("ent %d route FAILED (%s) x%d in %d ms: from (%.0f %.0f %.0f) to goal (%.0f %.0f %.0f), %d graph nodes\n",
            entity->s.number, why, a->routeFailCount, a->routeFailLogTime ? level.time - a->routeFailLogTime : 0,
            entity->r.currentOrigin[0], entity->r.currentOrigin[1],
            entity->r.currentOrigin[2], a->goal[0], a->goal[1], a->goal[2], CODOL_BotNavCount());
        a->routeFailLogTime = level.time; a->routeFailCount = 0;
    }
    unsigned name = SL_GetString("bad_path", 0);
    Scr_Notify(entity, (unsigned short)name, 0);
    SL_RemoveRefToString(name);
}
int CODOL_ActorSetGoal(gentity_s *entity, const float *goal)
{
    codol_actor_lifetime_t *a = CODOL_ActorForEntity(entity);
    if (!a || !goal || !isfinite(goal[0]) || !isfinite(goal[1]) ||
        !isfinite(goal[2])) return 0;
    int changed = !a->hasGoal || fabsf(goal[0]-a->goal[0])>1 ||
        fabsf(goal[1]-a->goal[1])>1 || fabsf(goal[2]-a->goal[2])>1;
    /* T5 Actor_SetGoalPos re-paths only when the destination leaves the
     * current path's last node: a chased enemy moves the attack spot every
     * frame, and re-planning from the nearest node (usually just behind the
     * dog) each frame made the dog ping-pong around that node. */
    int keepRoute = a->hasGoal && a->routeCount > 0 && a->routeCursor < a->routeCount &&
        CODOL_BotNavNearest(goal) == (int)a->route[a->routeCount-1];
    memcpy(a->goal, goal, sizeof(a->goal));
    a->hasGoal = 1;
    a->chaseRadius = 0;
    a->goalNode = -1;
    a->goalNotified = 0;
    a->routeFailNotified = 0;
    if (!keepRoute) a->routeCount = a->routeCursor = 0;
    float gx=goal[0]-a->diagGoal[0], gy=goal[1]-a->diagGoal[1], gz=goal[2]-a->diagGoal[2];
    if (changed && gx*gx+gy*gy+gz*gz > 64*64) {
        memcpy(a->diagGoal, goal, 12);
        ++a->goalLogCount;
        if (level.time - a->goalLogTime >= 5000) {
            DOG_DIAG("ent %d goal set x%d (%.0f %.0f %.0f) from (%.0f %.0f %.0f) radius %.0f%s\n",
                entity->s.number, a->goalLogCount, goal[0], goal[1], goal[2], entity->r.currentOrigin[0],
                entity->r.currentOrigin[1], entity->r.currentOrigin[2], a->goalRadius,
                keepRoute?" (route kept)":"");
            a->goalLogTime = level.time; a->goalLogCount = 0;
        }
    }
    return 1;
}
int CODOL_ActorGoalDirection(gentity_s *entity, float *direction)
{
    codol_actor_lifetime_t *a = CODOL_ActorForEntity(entity);
    if (!a || !a->hasGoal || !direction || !entity->clipmask) return 0;
    memset(direction, 0, 3 * sizeof(float));
    float dx = a->goal[0] - entity->r.currentOrigin[0];
    float dy = a->goal[1] - entity->r.currentOrigin[1];
    float dz = a->goal[2] - entity->r.currentOrigin[2];
    float radius = a->chaseRadius > 0 ? a->chaseRadius : a->goalRadius;
    if (dx*dx + dy*dy <= radius*radius && fabsf(dz) <= a->goalHeight) {
        if (!a->goalNotified) {
            a->goalNotified = 1;
            unsigned name = SL_GetString("goal", 0);
            Scr_Notify(entity, (unsigned short)name, 0);
            SL_RemoveRefToString(name);
        }
        return 2;
    }
    const float *next = a->goal;
    /* A wedge on the straight shortcut suspends it for a few seconds: the
     * +18 sweep passes over a knee-high wall the actor's step cannot climb
     * under a low overhang (zm_zombie_training's final-room yard at
     * (-478 3876 433): every frame took the shortcut into the wall, the
     * route over node 74 was never followed, and with no route leg there
     * was no link to ban). */
    if (level.time < a->shortcutBanTime || !ActorClearSegment(entity, entity->r.currentOrigin, next)) {
        if (a->routeCursor >= a->routeCount) {
            int from = ActorNearestWalkableNode(entity, a, entity->r.currentOrigin, 1);
            int to = ActorNearestWalkableNode(entity, a, a->goal, 0);
            const float *start = CODOL_BotNavPoint(from), *end = CODOL_BotNavPoint(to);
            /* MEASURED 2026-09-20: CoDOL ships pathnodes for NO map -- no
             * pathdata asset class exists in the zone inventory, the zm maps
             * are plain game_map_mp and ALL_rawfile.txt has no node entries.
             * The only graphs on this server are the 15 hand-authored
             * bin/home/main/waypoints/mp_*_wp.csv, all multiplayer, so on a
             * zm map CODOL_BotNavCount() is 0 and there is nothing to plan
             * over. Refusing to move is then not caution, it is the actor
             * standing still forever; the straight line is the only path
             * there is, and physics still slides it along geometry. With a
             * graph loaded the chaseRadius gate stands: a scripted patrol
             * goal should use the nodes rather than walk into a wall. */
            if (!start || !end) { ActorRouteFailed(entity, a, "no waypoint graph"); if (!a->chaseRadius && CODOL_BotNavCount() > 0) return 0; goto straight; }
            /* A script goal (not a chase) whose nearest waypoint is more than
             * 512 units away lies off the graph: the waypoints cover the
             * playable area, and the map's own path nodes, which
             * _dogs::init_node_arrays patrols between, also cover level
             * geometry outside it (mp_killhouse_sh (-143 -1478), ~3000
             * units from any waypoint).  Walking the straight line from
             * the last waypoint wedged the dog on the boundary wall until it
             * left; T5 Path_FindPath fails such a goal, so this reports
             * bad_path and the patrol picks another node.  Dogs only: the zm
             * entrance walk owns its own goals and bad_path handling. */
            if (!a->chaseRadius && a->species && !strcmp(a->species->name, "dog") &&
                Vec3DistanceSq(end, a->goal) > 512.0f*512.0f) {
                ActorRouteFailed(entity, a, "goal is off the waypoint graph");
                return 0;
            }
            a->routeCount = CODOL_BotNavRouteFiltered(from, to, a->route,
                CODOL_BOT_NODES, ActorRouteEdge, entity);
            a->routeCursor = 0;
            if (!a->routeCount) { ActorRouteFailed(entity, a, "no path between nearest nodes"); ActorRouteFailedDetail(entity, a, from, to); if (!a->chaseRadius) return 0; goto straight; }
            DOG_DIAG("ent %d route node %d -> %d: %d nodes\n", entity->s.number, from, to, a->routeCount);
        }
        /* Advance past nodes reached (24 units: a run frame moves ~17) or
         * passed within the following link's 24-unit corridor.  A bare dot
         * test marked a node passed even when the actor was far to the side:
         * on Prototype it skipped node 268 from 181 units away and aimed
         * through a brush at node 270; another actor skipped node 154 from
         * 103 away and walked into world clip toward node 515. */
        while (a->routeCursor < a->routeCount) {
            const float *node = CODOL_BotNavPoint(a->route[a->routeCursor]);
            if (!node) { a->routeCount = 0; return 0; }
            dx = node[0] - entity->r.currentOrigin[0];
            dy = node[1] - entity->r.currentOrigin[1];
            int passed = dx*dx + dy*dy <= 24.0f*24.0f;
            /* A negotiation begin node whose end node is the next leg is
             * REACHED, never walked past: T5 starts the traversal at the
             * node (Actor_Negotiation_Start) and the traversal animation is
             * authored from it.  The "behind me" shortcut below would skip
             * it from 30 units to the side and send the mover into the wall. */
            int beginOfLeg = a->routeCursor + 1 < a->routeCount &&
                CODOL_BotNavNegotiationEnd(a->route[a->routeCursor]) == (int)a->route[a->routeCursor+1];
            if (!passed && !beginOfLeg && a->routeCursor + 1 < a->routeCount) {
                const float *after = CODOL_BotNavPoint(a->route[a->routeCursor+1]);
                if (after) {
                    float legX = after[0]-node[0], legY = after[1]-node[1];
                    float legSq = legX*legX + legY*legY;
                    float cross = dx*legY - dy*legX;
                    passed = legSq > 0 && dx*legX + dy*legY < 0 &&
                        cross*cross <= 24.0f*24.0f*legSq;
                }
            }
            if (passed && !beginOfLeg && a->routeCursor + 1 < a->routeCount) {
                const float *after = CODOL_BotNavPoint(a->route[a->routeCursor+1]);
                if (after) {
                    float legX = after[0]-node[0], legY = after[1]-node[1];
                    float legSq = legX*legX + legY*legY;
                    float cross = dx*legY - dy*legX;
                    /* The static walk used a centered 31-unit hull.  Only an
                     * actor off that centerline needs this extra live probe;
                     * centered actors can use the graph's normal step path. */
                    if (legSq > 0 && cross*cross > 8.0f*8.0f*legSq &&
                        ActorRouteContinuationBlocked(entity, after)) passed = 0;
                }
            }
            if (!passed) break;
            if (beginOfLeg && !a->negotiating) {
                a->negotiationPending = 1;
                a->negotiationBegin = a->route[a->routeCursor];
                a->negotiationEnd = a->route[a->routeCursor+1];
                break;   /* RunFrame starts the traversal; the cursor stays on the begin node */
            }
            ++a->routeCursor;
        }
        if (a->routeCursor >= a->routeCount) {
            /* Route exhausted: final leg straight at the goal; physics
             * slides along whatever the reachability sweep disliked. */
            a->routeCount = a->routeCursor = 0;
            next = a->goal;
        } else {
            next = CODOL_BotNavPoint(a->route[a->routeCursor]);
            if (!next) { a->routeCount = 0; return 0; }
        }
    }
straight:
    if (next == a->goal) a->routeCount = a->routeCursor = 0;
    float length = 0;
    for (unsigned i = 0; i < 3; ++i) {
        direction[i] = next[i] - entity->r.currentOrigin[i];
        length += direction[i]*direction[i];
    }
    if (length <= 0) return 0;
    length = sqrtf(length);
    for (unsigned i = 0; i < 3; ++i) direction[i] /= length;
    /* Separation steering (minimal T5 actor avoidance): other live actors are
     * passable to the clip sweeps above, so steer around any inside two
     * capsule radii instead of walking into/through them and piling up. */
    float steer[2] = {0, 0};
    for (unsigned i = 0; i < CODOL_MAX_ACTOR_SLOTS; ++i) {
        codol_actor_lifetime_t *o = &actors[i];
        if (!o->allocated || !o->initialized || o->entity == entity || !o->entity || !o->entity->r.inuse ||
            o->entity->health <= 0) continue;
        float ox = entity->r.currentOrigin[0] - o->entity->r.currentOrigin[0];
        float oy = entity->r.currentOrigin[1] - o->entity->r.currentOrigin[1];
        float oz = entity->r.currentOrigin[2] - o->entity->r.currentOrigin[2];
        float d = sqrtf(ox*ox + oy*oy);
        if (fabsf(oz) > 48.0f || d >= 40.0f) continue;
        if (d < 1.0f) { ox = -direction[1]; oy = direction[0]; d = 1.0f; }
        float w = (40.0f - d) / 40.0f;
        steer[0] += ox / d * w; steer[1] += oy / d * w;
    }
    if (steer[0] != 0 || steer[1] != 0) {
        direction[0] += steer[0]; direction[1] += steer[1];
        float h = sqrtf(direction[0]*direction[0] + direction[1]*direction[1]);
        if (h > 0) { direction[0] /= h; direction[1] /= h; direction[2] = 0; }
    }
    return 1;
}

/* Apply the real native animation/physics displacement supplied for this
 * frame. No fixed dog speed, teleport-to-target or timed bite is substituted.
 * Route direction is consumed by the AI/orientation producer before this call.
 * Full step/gravity physics remains the movement owner's responsibility. */
int CODOL_ActorMoveDelta(gentity_s *entity, const float *delta)
{
    codol_actor_lifetime_t *a = CODOL_ActorForEntity(entity);
    if (!a || !a->initialized || !delta || !entity->clipmask) return 0;
    float end[3], origin[3];
    for (unsigned i = 0; i < 3; ++i) {
        if (!isfinite(delta[i])) return 0;
        end[i] = entity->r.currentOrigin[i] + delta[i];
        if (!isfinite(end[i])) return 0;
    }
    trace_t trace;
    G_TraceCapsule(&trace, entity->r.currentOrigin, entity->r.mins, entity->r.maxs,
                  end, entity->s.number, entity->clipmask);
    if (trace.startsolid || trace.allsolid) return 0;
    for (unsigned i = 0; i < 3; ++i)
        origin[i] = entity->r.currentOrigin[i] + delta[i] * trace.fraction;
    G_SetOrigin(entity, origin);
    memcpy(a->sentient->origin, origin, sizeof(origin));
    SV_LinkEntity(entity);
    if (trace.fraction < 1.0f) a->routeCount = 0;
    return 1;
}

extern "C" void XAnimCalcDelta(DObj *, unsigned, float *, float *, unsigned char);
/* The retained XAnim info pool (src/asmsource/_xanim.asm:13269, 4096 records
 * of 56 bytes). The per-second diagnostic walks it directly, for two MEASURED
 * reasons (docs/CODOL_ZOMBIE_ANIM_KNOB_20260921.md section 2):
 *   - XAnimGetDescendantWithGreatestWeight(tree, x) takes an INFO index, not
 *     an anim index: its first instructions are `lea eax,[edx*8]; shl edx,6;
 *     sub edx,eax; lea eax,[edx+g_xAnimInfo]` (_xanim.asm:2045-2049), and
 *     both retained callers (:2410, :2589) hand it the info index they were
 *     iterating. Passing anim 0 read info slot 0 -- the pool's null record --
 *     and always answered 0, so the field never named anything.
 *   - XAnimGetAnimName reads XAnim_s::debugAnimNames, which is NULL at
 *     developer 0 (codol_model_animation.c:CODOL_FindAnimInServerTree notes
 *     the same), so the name was "" on every production boot regardless.
 * A leaf's XAnimParts::name is real asset data and is used instead. */
extern "C" XAnimInfo g_xAnimInfo[4096];
#define XANIM_INFO_COUNT 4096u

/* Describe what an actor's server animtree is playing: follow the heaviest
 * child from the root info down to a leaf and report that clip's state.
 * "w" is the blended weight XAnimCalcDelta uses, "g" the goal the script
 * asked for, "t"/"ot" the clip's normalised time and the previous frame's
 * (root motion is their difference), "infos" the record count of the whole
 * tree. */
static void ActorDescribeTree(const XAnimTree_s *tree, char *out, size_t size)
{
    if (!tree->anims) { Q_strncpyz(out, "anim none (no tree)", (int)size); return; }
    unsigned root = tree->children;
    if (!root || root >= XANIM_INFO_COUNT) {
        Com_sprintf(out, (int)size, "anim none (tree %p has no infos)", (const void *)tree);
        return;
    }
    /* Count every record reachable from the root (bounded by the pool). */
    unsigned infos = 0, stack[64], sp = 0, guard = 0;
    stack[sp++] = root;
    while (sp && guard++ < XANIM_INFO_COUNT) {
        unsigned i = stack[--sp];
        if (!i || i >= XANIM_INFO_COUNT) continue;
        ++infos;
        for (unsigned c = g_xAnimInfo[i].children, g2 = 0; c && c < XANIM_INFO_COUNT && g2 < 256; c = g_xAnimInfo[c].next, ++g2)
            if (sp < 64) stack[sp++] = c;
    }
    /* Heaviest path to a leaf, remembered so the chain can be dumped. */
    unsigned leaf = root, depth = 0, chain[24], chainLen = 0;
    chain[chainLen++] = root;
    for (guard = 0; guard < 64; ++guard) {
        const XAnimInfo *n = &g_xAnimInfo[leaf];
        unsigned best = 0; float bestW = -1.0f;
        for (unsigned c = n->children, g2 = 0; c && c < XANIM_INFO_COUNT && g2 < 256; c = g_xAnimInfo[c].next, ++g2) {
            const XAnimInfo *ch = &g_xAnimInfo[c];
            float w = ch->state.weight > 0.0f ? ch->state.weight : ch->state.goalWeight * 0.5f;
            if (w > bestW) { bestW = w; best = c; }
        }
        if (!best) break;
        leaf = best; ++depth;
        if (chainLen < 24) chain[chainLen++] = leaf;
    }
    const XAnimInfo *n = &g_xAnimInfo[leaf];
    unsigned anim = n->animIndex;
    const XAnimEntry *e = anim < tree->anims->size ? &tree->anims->entries[anim] : NULL;
    int isLeaf = e && !e->numAnims;
    const char *name = isLeaf && e->u.parts && e->u.parts->name ? e->u.parts->name : NULL;
    int delta = isLeaf && e->u.parts ? e->u.parts->bDelta : -1;
    char blend[24];
    if (!name) { Com_sprintf(blend, sizeof(blend), "#%u%s", anim, isLeaf ? "" : "(blend)"); name = blend; }
    Com_sprintf(out, (int)size, "anim %s w %.2f g %.2f t %.3f ot %.3f rate %.2f delta %d depth %u infos %u",
        name, n->state.weight, n->state.goalWeight, n->state.time, n->state.oldTime,
        n->state.rate, delta, depth, infos);
    /* Record-chain dump, root -> leaf, for the first lines of a boot and for
     * every line that shows the frozen-clip signature (weight in, time never
     * moving). One entry per record: `info:anim` then `f<parent flags>` for a
     * blend node (1 loopsync, 2 nonloopsync, 4 sync root -- XAnimSetupSyncNodes
     * marks the group, XAnimFillInSyncNodes_r copies the loop bit into nested
     * blend nodes) or `L` for a leaf, then goal, weight, time, oldTime, rate,
     * cycle counts. The first record whose goal/weight is 0 on this path is
     * the one XAnimUpdateTimeAndNotetrack stops at (weight 0 -> free-check
     * only), and nothing below it can ever receive time. Bounded: 24 lines of
     * each kind per boot. */
    static unsigned s_chainDumps, s_stallDumps;
    int stalled = n->state.weight > 0.0f && n->state.time == 0.0f && n->state.oldTime == 0.0f && isLeaf;
    if (s_chainDumps < 24 || (stalled && s_stallDumps < 24)) {
        if (stalled) ++s_stallDumps;
        ++s_chainDumps;
        size_t used = strlen(out);
        if (used + 8 < size) {
            Com_sprintf(out + used, (int)(size - used), " chain");
            for (unsigned i = 0; i < chainLen; ++i) {
                const XAnimInfo *r = &g_xAnimInfo[chain[i]];
                const XAnimEntry *re = r->animIndex < tree->anims->size ? &tree->anims->entries[r->animIndex] : NULL;
                char kind[8];
                if (re && !re->numAnims) Q_strncpyz(kind, "L", sizeof(kind));
                else Com_sprintf(kind, sizeof(kind), "f%x", (unsigned)r->u.animParent.flags);
                used = strlen(out);
                if (used + 64 >= size) break;
                Com_sprintf(out + used, (int)(size - used), " %u:%u %s g%.2f w%.2f t%.3f ot%.3f r%.2f c%d/%d",
                    chain[i], (unsigned)r->animIndex, kind, r->state.goalWeight, r->state.weight,
                    r->state.time, r->state.oldTime, r->state.rate, (int)r->state.cycleCount,
                    (int)r->state.oldCycleCount);
            }
        }
    }
}
int CODOL_ActorAdvanceGoalAnimation(gentity_s *entity, int time, int useGoalWeight)
{
    codol_actor_lifetime_t *a = CODOL_ActorForEntity(entity);
    if (!a || !a->initialized || time <= a->lastRootMotionTime) return 0;
    DObj *obj = Com_GetServerDObj(entity->s.number);
    if (!obj || !DObjGetTree(obj)) return 0;
    unsigned generation = a->generation;
    float direction[3]={0,0,0}, rotation[4]={0,0,0,0}, translation[3]={0,0,0};
    int mode=a->scriptAnimMode ? a->scriptAnimMode : a->animMode;
    /* T5 runs the dog turn animscript as AI_ANIM_MOVE_CODE: the path moves
     * and orients the dog (orient to motion) while the turn clip plays; the
     * script's animMode( "zonly_physics" ) leaves code in charge of xy.  Here
     * the path's pace is the clip's forward root motion (the C1 turn clips
     * are run starts), and the native facing turns the dog. */
    if(a->scripts.turn && a->animFunction==a->scripts.turn && a->species && !strcmp(a->species->name,"dog"))
        mode=a->animMode;
    int route = mode==1 && a->moveMode ? CODOL_ActorGoalDirection(entity, direction) : 0;
    a = CODOL_ActorForEntity(entity);
    if (!a || a->generation != generation) return 0;
    float seconds=(level.time-level.previousTime)*.001f;
    if (!g_gravity || seconds<=0 || seconds>.25f) return 0;
    a->lastRootMotionTime=time;
    if(mode==8) {memset(a->physics.velocity,0,12);return 1;}
    XAnimCalcDelta(obj,0,rotation,translation,useGoalWeight!=0);
    for(int i=0;i<3;++i)if(!isfinite(translation[i]))return 0;
    if(!isfinite(rotation[0]) || !isfinite(rotation[1]))return 0;
    float delta[3]={0,0,0};
    if(mode==1 && route==1) {
        float distance=sqrtf(translation[0]*translation[0]+translation[1]*translation[1]);
        a->stuckAttempt+=distance;
        for(int i=0;i<3;++i)delta[i]=direction[i]*distance;
    } else if(mode==2 || mode==4 || mode==5 || mode==6 || mode==7) {
        float yaw=entity->r.currentAngles[1]*.01745329252f;
        delta[0]=cosf(yaw)*translation[0]-sinf(yaw)*translation[1];
        delta[1]=sinf(yaw)*translation[0]+cosf(yaw)*translation[1];
        delta[2]=(mode==5 || mode==6)?translation[2]:0;
    }
    if(mode>=3 && mode<=7 && (rotation[0]!=0 || rotation[1]!=0)) {
        float norm=rotation[0]*rotation[0]+rotation[1]*rotation[1];
        float turn=atan2f(2*rotation[0]*rotation[1]/norm,1-2*rotation[0]*rotation[0]/norm)*57.295779513f;
        entity->r.currentAngles[1]=fmodf(entity->r.currentAngles[1]+turn+360,360);
        memcpy(entity->s.lerp.apos.trBase,entity->r.currentAngles,12);
    }
    int moved=CODOL_ActorPhysicsMoveMode(entity,&a->physics,delta,seconds,
        g_gravity->value,18.0f,mode==5?1:mode==6?2:mode==7?3:0);
    memcpy(a->lastTranslation,translation,12);
    if (moved) ++a->movesAccepted; else ++a->movesRejected;
    if (!moved) ++a->stuckRejected;
    if (a->physics.blocked) ++a->stuckBlocked;
    if (moved) memcpy(a->sentient->origin, entity->r.currentOrigin, 12);
    return moved;
}

/* Team NONE is free-for-all: everything except the owner and fellow actors is
 * hostile (T5 TEAM_FREE dogs). Any other team is hostile to other teams. */
static int ActorMayTarget(const codol_actor_lifetime_t *a, const codol_sentient_t *s)
{
    if (!s || !s->entity) return 0;
    if (a->sentient->team) return s->team && s->team != a->sentient->team;
    if (s->isActor) return 0;
    return s->entity->s.number != a->sentient->ownerNum;
}
/* MP sight acquisition over the real sentient registry. A retained enemy
 * remains available when temporarily occluded; visible challengers are ranked
 * by distance. Full T5 threat/suppression weighting is not implemented here.
 *
 * A species whose perception column says perfectInfo (the zm zombie) skips
 * the sight trace entirely and takes the nearest hostile sentient. That is
 * not a shortcut around the trace: it is what T5 does for this actor at both
 * levels. MEASURED, OpenBLOPS Game/Server/game/actor_spawner.cpp:199-203 --
 * the ENEMYINFO spawnflag the actor_enemy_zombie_zm QUAKED block declares
 * runs Actor_GetPerfectInfo over EVERY sentient at spawn, which is the write
 * (actor_senses.cpp:514, lastKnownPosTime = level.time) that satisfies the
 * one awareness gate in the threat pass (actor_threat.cpp:241). MEASURED,
 * T5 _zombiemode_spawner.gsc:4013 find_flesh picks its target with
 * get_closest_valid_player, which is _zombiemode_utility.gsc GetClosest() --
 * distance only -- and pins it with self.favoriteenemy, which the threat
 * pass scores at 0x7ffffffe (actor_threat.cpp:317-321) and the sight pass
 * exempts from the FOV cone (actor_senses.cpp:303-307).
 *
 * Why it matters here, MEASURED 2026-09-20 in bin/home/main/qconsole.log:
 * every live zm zombie logged "enemy -1" for the whole match (360/360 diag
 * samples). The zm spawn structs put them 1000-2500 units from the player
 * behind map geometry, so the capsule trace below could never return a clear
 * line, no enemy was ever acquired, chaseRadius stayed 0, the straight-line
 * fallback in CODOL_ActorGoalDirection was skipped and they logged
 * "moved 0/s" forever -- which is also why the player never saw one. */
static void ActorUpdateVisibleEnemy(gentity_s *entity)
{
    codol_actor_lifetime_t *a=CODOL_ActorForEntity(entity);
    if(!a)return;
    gentity_s *best=NULL;
    float bestDistance=INFINITY;
    int perfect=a->species && a->species->perfectInfo;
    int candidates=0;
    float eye[3];
    for(int i=0;i<3;++i)eye[i]=entity->r.currentOrigin[i]+(entity->r.mins[i]+entity->r.maxs[i])*.5f;
    for(codol_sentient_t *s=CODOL_Sentient_First(CODOL_SENTIENT_MASK_ALL);s;
        s=CODOL_Sentient_Next(s,CODOL_SENTIENT_MASK_ALL)) {
        gentity_s *candidate=s->entity;
        if(!candidate || candidate==entity || !candidate->r.inuse || candidate->health<=0 ||
            s->dontTarget || !ActorMayTarget(a, s))continue;
        ++candidates;
        float target[3],distance=0;
        for(int i=0;i<3;++i){target[i]=candidate->r.currentOrigin[i]+(candidate->r.mins[i]+candidate->r.maxs[i])*.5f;
            float d=target[i]-eye[i];distance+=d*d;}
        if(distance>=bestDistance)continue;
        if(!perfect) {
            trace_t trace;float zero[3]={0,0,0};
            G_TraceCapsule(&trace,eye,zero,zero,target,entity->s.number,entity->clipmask);
            // Endpoint is inside the target; accept its own entity hit as sight.
            if(trace.startsolid || trace.allsolid ||
                (trace.fraction<1 && (trace.hitType!=TRACE_HITTYPE_ENTITY || trace.hitId!=candidate->s.number)))continue;
        }
        best=candidate;bestDistance=distance;
    }
    a->diagCandidates=candidates;
    if(best) {
        a->enemySeenTime=level.time;
        CODOL_ActorSetEnemy(entity,best);
    } else {
        // T5 SentientInfo_Copy gates teammate information by sender species
        // mask and timestamp. Here the represented sight record is the target.
        for(unsigned i=0;i<CODOL_MAX_ACTOR_SLOTS;++i) {
            codol_actor_lifetime_t *sender=&actors[i];
            if(!sender->initialized || sender==a || !(sender->talkMask & ActorTalkBit(a)) ||
                sender->enemySeenTime<=a->enemySeenTime ||
                sender->sentient->team!=a->sentient->team)continue;
            gentity_s *known=CODOL_ActorEnemy(sender->entity);
            if(known && CODOL_ActorSetEnemy(entity,known))a->enemySeenTime=sender->enemySeenTime;
        }
    }
}
void CODOL_ActorInheritSight(gentity_s *entity)
{
    codol_actor_lifetime_t *a=CODOL_ActorForEntity(entity);if(!a)return;
    for(unsigned i=0;i<CODOL_MAX_ACTOR_SLOTS;++i) {
        codol_actor_lifetime_t *sender=&actors[i];
        if(!sender->initialized || sender==a || !(sender->talkMask & ActorTalkBit(a)) ||
           sender->sentient->team!=a->sentient->team || sender->enemySeenTime<=a->enemySeenTime)continue;
        gentity_s *enemy=CODOL_ActorEnemy(sender->entity);
        if(enemy && CODOL_ActorSetEnemy(entity,enemy))a->enemySeenTime=sender->enemySeenTime;
    }
}
static void ActorOrientToDirection(gentity_s *entity,const float *direction,float seconds)
{
    if(!direction || seconds<=0 || seconds>.25f)return;
    if(direction[0]==0 && direction[1]==0)return;
    float desired=atan2f(direction[1],direction[0])*57.295779513f;
    float delta=fmodf(desired-entity->r.currentAngles[1],360.0f);
    if(delta>180)delta-=360;if(delta< -180)delta+=360;
    // T5 Actor_UpdateBodyAngle's exposed/prone dog rate is360 deg/s.
    delta=fmaxf(-360.0f*seconds,fminf(360.0f*seconds,delta));
    float yaw=fmodf(entity->r.currentAngles[1]+delta+360.0f,360.0f);
    entity->r.currentAngles[0]=entity->r.currentAngles[2]=0;
    entity->r.currentAngles[1]=yaw;
    memcpy(entity->s.lerp.apos.trBase,entity->r.currentAngles,12);
}

/* ---------------------------------------------------------------------------
 * Negotiation (T5 actor_negotiation.cpp, OpenBLOPS Game/Server/game).
 *
 * The map's node_negotiation_begin -> node_negotiation_end pairs are the zm
 * window sills: MEASURED 2026-09-21 on zm_prototype_sh, the pf4 sill is a
 * 42-unit world brush (floor z 1 -> 42 at y 1018 -> 2 inside) under a lintel
 * that leaves ~108 units of headroom at the begin node -- an 18-unit step
 * never clears it, and the pairs carry animscript "zombie_mantle_over_40"
 * for exactly that reason.  T5's sequence:
 *   Actor_Negotiation_Start  - orient mode DONT_CHANGE, traverse mode
 *                              NOGRAVITY, momentum cleared;
 *   Actor_Negotiation_Think  - run the node's animscript
 *                              (animscripts/traverse/<animscript>::main) as
 *                              the actor's anim-specific script in
 *                              AI_ANIM_USE_BOTH_DELTAS_NOCLIP (the script
 *                              asks traverseMode "nogravity"+"noclip"); the
 *                              actor moves by the clip's root motion only;
 *   cleanup                  - when the script thread dies: nearest node :=
 *                              the end node, wish/velocity zeroed, path
 *                              recalculated, state popped.
 * The GSC half here is maps/mp/animscripts/<species>_jump::main(begin,
 * begin_angles, end, animscript), the species' traversal module (this
 * port's "jump" slot IS T5's traversal slot; zombie_jump.gsc is
 * T5 animscripts/traverse/zombie_mantle_over_40 + shared::DoTraverse).
 * MEASURED (obj/claude-workers/xanim_probe.py on common_gametype_zm): the
 * clips carry the link -- ai_zombie_traverse_v1 +64.6 units forward over 58
 * frames, v5 +62.7, v2 +70.1, v6 +108.6, crawl_v1 +76.8 -- and a "gravity
 * on" notetrack at t 0.85-0.98; only v1/v2 carry any z.  The sill is
 * crossed in noclip, as T5 crosses it, and the actor lands on the end node.
 * Alignment: T5 AnimScripted lerps the actor onto the given origin/angles;
 * the route follower only hands over within 24 units of the begin node, and
 * that remainder is snapped here so the authored clip starts where it was
 * authored to start.
 * ------------------------------------------------------------------------ */
struct actor_switch_params { float begin[3], angles[3], end[3]; const char *script; };
static const actor_switch_params *s_switchParams;
static const char *ActorNodeAnimscript(int node)
{
    int record = CODOL_BotNavRecord(node);
    const char *v = record >= 0 ? CODOL_PathNodeValue((unsigned)record, "animscript") : NULL;
    return v && *v ? v : "";
}
static int ActorStartNegotiation(gentity_s *entity)
{
    codol_actor_lifetime_t *a = CODOL_ActorForEntity(entity);
    if (!a) return 0;
    int begin = a->negotiationBegin, end = a->negotiationEnd;
    const float *bp = CODOL_BotNavPoint(begin), *ep = CODOL_BotNavPoint(end);
    if (!bp || !ep || !a->scripts.jump || !a->scriptsStarted) return 0;
    if (CODOL_BotNavLinkBlocked(begin, end)) {
        /* The barrier went back up (repair) after this route was planned. */
        a->routeCount = a->routeCursor = 0;
        return 0;
    }
    int record = CODOL_BotNavRecord(begin);
    const char *anglesText = record >= 0 ? CODOL_PathNodeValue((unsigned)record, "angles") : NULL;
    actor_switch_params params;
    params.script = ActorNodeAnimscript(begin);
    memcpy(params.begin, bp, 12); memcpy(params.end, ep, 12);
    params.angles[0] = params.angles[2] = 0;
    if (!anglesText || sscanf(anglesText, "%f %f %f", &params.angles[0], &params.angles[1], &params.angles[2]) != 3 ||
        !isfinite(params.angles[1])) {
        params.angles[0] = params.angles[2] = 0;
        params.angles[1] = atan2f(ep[1]-bp[1], ep[0]-bp[0]) * 57.295779513f;
    }
    float from[3]; memcpy(from, entity->r.currentOrigin, 12);
    float origin[3] = {bp[0], bp[1], entity->r.currentOrigin[2]};
    float angles[3] = {0, params.angles[1], 0};
    a->safeToChangeScript = 1;
    G_SetOrigin(entity, origin);
    memcpy(entity->r.currentAngles, angles, 12);
    memcpy(entity->s.lerp.apos.trBase, angles, 12);
    memcpy(a->sentient->origin, origin, 12);
    memset(a->physics.velocity, 0, sizeof(a->physics.velocity));
    a->prevMoveDir[0] = a->prevMoveDir[1] = 0;
    SV_LinkEntity(entity);
    a->negotiating = 1;
    a->negotiationPending = 0;
    a->negotiationStartTime = level.time;
    memcpy(a->negotiationStartOrigin, origin, 12);
    a->stuckTime = 0; a->stuckCount = 0; a->stuckAttempt = 0;
    DOG_DIAG("ent %d negotiation start: node %d (%.0f %.0f %.0f) -> node %d (%.0f %.0f %.0f) animscript '%s' yaw %.0f; aligned from (%.0f %.0f %.0f)\n",
        entity->s.number, begin, bp[0], bp[1], bp[2], end, ep[0], ep[1], ep[2], params.script, params.angles[1],
        from[0], from[1], from[2]);
    s_switchParams = &params;
    int ok = CODOL_ActorSwitchScript(entity, a->scripts.jump, 0, 1);
    s_switchParams = NULL;
    a = CODOL_ActorForEntity(entity);
    if (!a) return 0;
    if (!ok || a->animFunction != a->scripts.jump) {
        DOG_DIAG("ent %d negotiation start: the traversal animscript could not be entered (%s); route dropped\n",
            entity->s.number, ok ? "another script held the actor" : "switch refused");
        a->negotiating = 0;
        a->routeCount = a->routeCursor = 0;
        return 0;
    }
    a->safeToChangeScript = 0;   /* nothing replaces the traversal but its own end (or death) */
    return 1;
}
/* ---------------------------------------------------------------------------
 * Dog wall hop.
 *
 * T5 Actor_Dog_Exposed_Think (OpenBLOPS game/actor_dog_exposed.cpp) runs the
 * species jump animscript (dog_jump::main -> "traverse_wallhop") with
 * AI_ANIM_USE_BOTH_DELTAS_NOCLIP when Actor_Dog_ObstacleInPath finds a solid
 * 32 units ahead at +20, and its map traversals (animscripts/traverse/
 * mantle_over_40, mantle_on_40, jump_down_40) cross 40-unit walls and ledges
 * over node_negotiation links.  CoDOL MP maps are navigated on the bot
 * waypoint graph, whose vault/mantle links (mp_killhouse_sh 99/100 -> 103/104:
 * a 32-unit cinderblock wall) carry no traversal of their own, so the dog
 * wedged on them.  Here a dog whose path is blocked by a low obstacle it can
 * clear takes the T5 traversal the geometry calls for:
 *   level landing       -> "traverse_wallhop"      (C1 german_shepherd_run_jump_40,  140 units)
 *   landing 18..48 up   -> "traverse_jump_up_40"   (C1 german_shepherd_traverse_up_40, 116 fwd, +40)
 *   landing 18..48 down -> "traverse_jump_down_40" (C1 german_shepherd_traverse_down_40, 106 fwd, -40)
 *   low opening         -> "traverse_window"       (C1 german_shepherd_run_jump_window_40, 192 units;
 *                          T5 mantle_window_36 / mantle_over_40), else the wall hop clip through it
 * The distances are the clips' own root motion (xanim delta tracks,
 * common_gametype_mp).  The hop needs a clear sweep 48 units up, over the
 * obstacle to the landing, and a floor there.
 * ------------------------------------------------------------------------ */
static int ActorIsDog(const codol_actor_lifetime_t *a)
{
    return a && a->species && !strcmp(a->species->name, "dog");
}
/* Sweep hull (mins, maxs) from raised to the landing xy at the same height,
 * drop it to a floor, and require the dog's own hull to stand there. */
static int ActorHopLanding(gentity_s *entity, const float *raised, const float *mins,
    const float *maxs, const float *dir, float distance, float *landing)
{
    trace_t tr;
    float over[3] = {raised[0]+dir[0]*distance, raised[1]+dir[1]*distance, raised[2]};
    G_TraceCapsule(&tr, raised, mins, maxs, over, entity->s.number, entity->clipmask);
    if (tr.startsolid || tr.allsolid || tr.fraction < 1.0f) return 0;
    float down[3] = {over[0], over[1], over[2]-96.0f};
    G_TraceCapsule(&tr, over, mins, maxs, down, entity->s.number, entity->clipmask);
    if (tr.startsolid || tr.allsolid || tr.fraction >= 1.0f || tr.normal[2] < 0.7f) return 0;
    landing[0] = over[0]; landing[1] = over[1]; landing[2] = over[2] - 96.0f*tr.fraction + 0.25f;
    G_TraceCapsule(&tr, landing, entity->r.mins, entity->r.maxs, landing, entity->s.number, entity->clipmask);
    return !tr.startsolid && !tr.allsolid;
}
static int ActorStartWallHop(gentity_s *entity, const float *direction)
{
    codol_actor_lifetime_t *a = CODOL_ActorForEntity(entity);
    if (!ActorIsDog(a) || !a->scripts.jump || !a->scriptsStarted || a->negotiating) return 0;
    if (a->hopTime && level.time - a->hopTime < 1000) return 0;
    float len = sqrtf(direction[0]*direction[0] + direction[1]*direction[1]);
    if (len < 0.001f) return 0;
    float dir[3] = {direction[0]/len, direction[1]/len, 0};
    const float *o = entity->r.currentOrigin;
    trace_t tr;
    float mins[3], ahead[3] = {o[0]+dir[0]*24.0f, o[1]+dir[1]*24.0f, o[2]};
    memcpy(mins, entity->r.mins, 12); mins[2] += 18.0f;
    CODOL_ActorsPassable(entity, 1);
    /* T5 Actor_Dog_ObstacleInPath looks 32 ahead; the hull's own radius (15)
     * plus this 24-unit sweep reaches the same point.  A step (<18) is not an
     * obstacle; a slope (normal z >= .7) is walked, not hopped. */
    G_TraceCapsule(&tr, o, mins, entity->r.maxs, ahead, entity->s.number, entity->clipmask);
    int blocked = !tr.startsolid && !tr.allsolid && tr.fraction < 1.0f && tr.normal[2] < 0.7f;
    float raised[3] = {o[0], o[1], o[2]+48.0f}, landing[3];
    const char *state = NULL, *hopWhy = "no clear landing over it";
    if (blocked) {
        /* Open above (a wall): the whole dog clears it 48 up.  T5 dog_jump /
         * traverse\shared dog_jump_up / dog_jump_down. */
        G_TraceCapsule(&tr, o, entity->r.mins, entity->r.maxs, raised, entity->s.number, entity->clipmask);
        if (!tr.startsolid && !tr.allsolid && tr.fraction >= 1.0f) {
            static const struct { const char *state; float distance, minDz, maxDz; } hops[3] = {
                {"traverse_wallhop", 140.0f, -18.0f, 18.0f},
                {"traverse_jump_up_40", 116.0f, 18.0f, 48.0f},
                {"traverse_jump_down_40", 106.0f, -48.0f, -18.0f},
            };
            for (int h = 0; h < 3 && !state; ++h) {
                if (!ActorHopLanding(entity, raised, entity->r.mins, entity->r.maxs, dir, hops[h].distance, landing)) continue;
                float dz = landing[2] - o[2];
                if (dz >= hops[h].minDz && dz <= hops[h].maxDz) state = hops[h].state;
            }
        } else {
            /* A low opening (a wall with a beam or sill above it: the
             * killhouse crouch passages, nodes 99/100 -> 103/104): the dog
             * dives through it.  T5 traverse\mantle_window_36 and
             * mantle_over_40 -> dog_wall_and_window_hop( "traverse_window" ),
             * C1 german_shepherd_run_jump_window_40, 192 units.  The opening
             * is probed with a 16-unit-tall slice of the dog's hull 36 up
             * (the gap over a <=36-unit wall) and the landing must be level. */
            float sliceMins[3] = {entity->r.mins[0], entity->r.mins[1], 0};
            float sliceMaxs[3] = {entity->r.maxs[0], entity->r.maxs[1], 16.0f};
            float window[3] = {o[0], o[1], o[2]+36.0f};
            G_TraceCapsule(&tr, o, sliceMins, sliceMaxs, window, entity->s.number, entity->clipmask);
            if (tr.startsolid || tr.allsolid || tr.fraction < 1.0f) hopWhy = "no headroom over it";
            else if (ActorHopLanding(entity, window, sliceMins, sliceMaxs, dir, 192.0f, landing) &&
                     fabsf(landing[2] - o[2]) <= 18.0f)
                state = "traverse_window";
            /* No room for the 192-unit dive: the 140-unit wall hop clip
             * through the same opening. */
            else if (ActorHopLanding(entity, window, sliceMins, sliceMaxs, dir, 140.0f, landing) &&
                     fabsf(landing[2] - o[2]) <= 18.0f)
                state = "traverse_wallhop";
        }
    }
    CODOL_ActorsPassable(entity, 0);
    if (!state) {
        if (blocked && (!a->hopDiagTime || level.time - a->hopDiagTime >= 5000)) {
            a->hopDiagTime = level.time;
            DOG_DIAG("ent %d path blocked ahead at (%.0f %.0f %.0f) heading (%.2f %.2f) but no hop: %s\n",
                entity->s.number, o[0], o[1], o[2], dir[0], dir[1], hopWhy);
        }
        return 0;
    }
    actor_switch_params params;
    params.script = state;
    memcpy(params.begin, o, 12); memcpy(params.end, landing, 12);
    params.angles[0] = params.angles[2] = 0;
    params.angles[1] = atan2f(dir[1], dir[0]) * 57.295779513f;
    float angles[3] = {0, params.angles[1], 0};
    memcpy(entity->r.currentAngles, angles, 12);
    memcpy(entity->s.lerp.apos.trBase, angles, 12);
    memset(a->physics.velocity, 0, sizeof(a->physics.velocity));
    a->safeToChangeScript = 1;
    a->negotiating = 1;
    a->negotiationPending = 0;
    a->negotiationBegin = a->negotiationEnd = -1;
    a->negotiationStartTime = level.time;
    memcpy(a->negotiationStartOrigin, o, 12);
    a->wallHop = 1;
    memcpy(a->hopStart, o, 12); memcpy(a->hopLanding, landing, 12);
    a->stuckTime = 0; a->stuckCount = 0; a->stuckAttempt = 0;
    DOG_DIAG("ent %d wall hop '%s' from (%.0f %.0f %.0f) to (%.0f %.0f %.0f) yaw %.0f\n",
        entity->s.number, state, o[0], o[1], o[2], landing[0], landing[1], landing[2], params.angles[1]);
    unsigned generation = a->generation;
    s_switchParams = &params;
    int ok = CODOL_ActorSwitchScript(entity, a->scripts.jump, 0, 1);
    s_switchParams = NULL;
    a = CODOL_ActorForEntity(entity);
    if (!a || a->generation != generation) return 1;
    if (!ok || a->animFunction != a->scripts.jump) {
        DOG_DIAG("ent %d wall hop: the jump animscript could not be entered; route kept\n", entity->s.number);
        a->negotiating = 0; a->wallHop = 0;
        return 0;
    }
    /* Actor_SetAnimScript(..., AI_ANIM_USE_BOTH_DELTAS_NOCLIP): the clip's
     * root motion carries the dog over, through the obstacle's clip. */
    a->scriptAnimMode = 5;
    a->scriptOrient = 1;
    a->scriptYaw = params.angles[1];
    a->safeToChangeScript = 0;
    return 1;
}
static void ActorFinishWallHop(gentity_s *entity, const char *why)
{
    codol_actor_lifetime_t *a = CODOL_ActorForEntity(entity);
    if (!a) return;
    trace_t probe;
    const float *o = entity->r.currentOrigin;
    CODOL_ActorsPassable(entity, 1);
    G_TraceCapsule(&probe, o, entity->r.mins, entity->r.maxs, o, entity->s.number, entity->clipmask);
    CODOL_ActorsPassable(entity, 0);
    int solid = probe.startsolid || probe.allsolid;
    if (solid) {
        /* Ended inside the wall (a clip shorter than the gap, or a timeout):
         * finish at the landing the hop was planned for, else back where it
         * started.  Both were clear when the hop began. */
        const float *targets[2] = {a->hopLanding, a->hopStart};
        for (int t = 0; t < 2; ++t) {
            CODOL_ActorsPassable(entity, 1);
            G_TraceCapsule(&probe, targets[t], entity->r.mins, entity->r.maxs, targets[t], entity->s.number, entity->clipmask);
            CODOL_ActorsPassable(entity, 0);
            if (probe.startsolid || probe.allsolid) continue;
            float origin[3]; memcpy(origin, targets[t], 12);
            G_SetOrigin(entity, origin);
            memcpy(a->sentient->origin, origin, 12);
            SV_LinkEntity(entity);
            break;
        }
    }
    DOG_DIAG("ent %d wall hop %s after %d ms at (%.0f %.0f %.0f)%s, landing (%.0f %.0f %.0f)\n",
        entity->s.number, why, level.time - a->negotiationStartTime, o[0], o[1], o[2],
        solid ? " IN SOLID (placed)" : "", a->hopLanding[0], a->hopLanding[1], a->hopLanding[2]);
    a->negotiating = 0;
    a->negotiationPending = 0;
    a->wallHop = 0;
    a->hopTime = level.time;
    a->routeCount = a->routeCursor = 0;
    memset(a->physics.velocity, 0, sizeof(a->physics.velocity));
    a->prevMoveDir[0] = a->prevMoveDir[1] = 0;
    a->scriptAnimMode = 0;
    a->scriptOrient = 0;
    a->safeToChangeScript = 1;
    a->stuckTime = 0; a->stuckCount = 0; a->stuckAttempt = 0;
}
static void ActorFinishNegotiation(gentity_s *entity, const char *why)
{
    codol_actor_lifetime_t *hop = CODOL_ActorForEntity(entity);
    if (hop && hop->wallHop) { ActorFinishWallHop(entity, why); return; }
    codol_actor_lifetime_t *a = CODOL_ActorForEntity(entity);
    if (!a) return;
    const float *bp = CODOL_BotNavPoint(a->negotiationBegin), *ep = CODOL_BotNavPoint(a->negotiationEnd);
    const float *o = entity->r.currentOrigin;
    float db = bp ? sqrtf((o[0]-bp[0])*(o[0]-bp[0]) + (o[1]-bp[1])*(o[1]-bp[1])) : 0;
    float de = ep ? sqrtf((o[0]-ep[0])*(o[0]-ep[0]) + (o[1]-ep[1])*(o[1]-ep[1])) : 0;
    trace_t probe;
    CODOL_ActorsPassable(entity, 1);
    G_TraceCapsule(&probe, o, entity->r.mins, entity->r.maxs, o, entity->s.number, entity->clipmask);
    CODOL_ActorsPassable(entity, 0);
    int solid = probe.startsolid || probe.allsolid;
    int crossed = ep && bp && de < db;
    if (ep && (!crossed || solid)) {
        /* The clip's root motion did not carry the actor over (a short or
         * delta-less clip, or a timeout): finish the link the honest way and
         * say so.  The end node is on the walkable graph by construction. */
        static const float lifts[3] = {1.0f, 20.0f, 44.0f};
        int snapped = 0;
        for (int l = 0; l < 3 && !snapped; ++l) {
            float origin[3] = {ep[0], ep[1], ep[2]+lifts[l]};
            CODOL_ActorsPassable(entity, 1);
            G_TraceCapsule(&probe, origin, entity->r.mins, entity->r.maxs, origin, entity->s.number, entity->clipmask);
            CODOL_ActorsPassable(entity, 0);
            if (probe.startsolid || probe.allsolid) continue;
            DOG_DIAG("ent %d negotiation %s after %d ms SHORT: at (%.0f %.0f %.0f) %.0f from begin, %.0f from end%s; snapped to end node %d (%.0f %.0f %.0f)\n",
                entity->s.number, why, level.time - a->negotiationStartTime, o[0], o[1], o[2], db, de,
                solid ? " (in solid)" : "", a->negotiationEnd, origin[0], origin[1], origin[2]);
            G_SetOrigin(entity, origin);
            memcpy(a->sentient->origin, origin, 12);
            SV_LinkEntity(entity);
            snapped = 1;
        }
        if (!snapped)
            DOG_DIAG("ent %d negotiation %s after %d ms SHORT at (%.0f %.0f %.0f) and the end node is solid for it; left in place\n",
                entity->s.number, why, level.time - a->negotiationStartTime, o[0], o[1], o[2]);
    } else {
        DOG_DIAG("ent %d negotiation %s after %d ms: (%.0f %.0f %.0f) -> (%.0f %.0f %.0f), end node %.0f away, dz %.0f\n",
            entity->s.number, why, level.time - a->negotiationStartTime,
            a->negotiationStartOrigin[0], a->negotiationStartOrigin[1], a->negotiationStartOrigin[2],
            o[0], o[1], o[2], de, ep ? o[2]-ep[2] : 0.0f);
    }
    /* T5 cleanup: momentum zero, path recalculated from the end node, state
     * popped; the ordinary selection resumes next frame. */
    a->negotiating = 0;
    a->negotiationPending = 0;
    a->routeCount = a->routeCursor = 0;
    memset(a->physics.velocity, 0, sizeof(a->physics.velocity));
    a->prevMoveDir[0] = a->prevMoveDir[1] = 0;
    a->scriptAnimMode = 0;
    a->scriptOrient = 0;
    a->safeToChangeScript = 1;
    a->stuckTime = 0; a->stuckCount = 0; a->stuckAttempt = 0;
}
static void ActorNegotiationFrame(gentity_s *entity)
{
    codol_actor_lifetime_t *a = CODOL_ActorForEntity(entity);
    if (!a) return;
    unsigned generation = a->generation;
    int alive = a->animFunction == a->scripts.jump && a->animThread &&
        Scr_GetObjectType((unsigned short)a->animThread) != VAR_DEAD_THREAD;
    if (!alive) { ActorFinishNegotiation(entity, "complete"); return; }
    if (level.time - a->negotiationStartTime > (a->wallHop ? 3000 : 8000)) { ActorFinishNegotiation(entity, "TIMED OUT"); return; }
    /* The traversal script owns facing ("face angle" = scriptOrient 1). */
    if (a->scriptOrient == 1) {
        float facing[3] = {cosf(a->scriptYaw*.01745329252f), sinf(a->scriptYaw*.01745329252f), 0};
        ActorOrientToDirection(entity, facing, (level.time-level.previousTime)*.001f);
    }
    a = CODOL_ActorForEntity(entity);
    if (!a || a->generation != generation) return;
    CODOL_ActorAdvanceGoalAnimation(entity, level.time, 0);
}
/* Once per actor: the stuck detector fired next to a negotiation node.  Name
 * what the capsule hits on the way to the end node, the heights, the link's
 * cut state and the animscript, so a window stall is measured, not guessed. */
static void ActorWindowStuckDiag(gentity_s *entity, codol_actor_lifetime_t *a)
{
    if (a->windowDiagPrinted) return;
    int begin = -1, end = -1;
    if (a->routeCursor < a->routeCount) {
        int n = a->route[a->routeCursor];
        if (CODOL_BotNavNegotiationEnd(n) >= 0) { begin = n; end = CODOL_BotNavNegotiationEnd(n); }
        else if (a->routeCursor > 0 && CODOL_BotNavNegotiationEnd(a->route[a->routeCursor-1]) == n) { begin = a->route[a->routeCursor-1]; end = n; }
    }
    if (begin < 0) {
        int n = CODOL_BotNavNearest(entity->r.currentOrigin);
        const float *p = CODOL_BotNavPoint(n);
        if (p && CODOL_BotNavNegotiationEnd(n) >= 0 &&
            (p[0]-entity->r.currentOrigin[0])*(p[0]-entity->r.currentOrigin[0]) + (p[1]-entity->r.currentOrigin[1])*(p[1]-entity->r.currentOrigin[1]) <= 64.0f*64.0f) {
            begin = n; end = CODOL_BotNavNegotiationEnd(n);
        }
    }
    const float *ep = CODOL_BotNavPoint(end), *bp = CODOL_BotNavPoint(begin);
    if (!ep || !bp) return;
    a->windowDiagPrinted = 1;
    float target[3] = {ep[0], ep[1], entity->r.currentOrigin[2]};
    trace_t tr;
    CODOL_ActorsPassable(entity, 1);
    G_TraceCapsule(&tr, entity->r.currentOrigin, entity->r.mins, entity->r.maxs, target, entity->s.number, entity->clipmask);
    CODOL_ActorsPassable(entity, 0);
    const char *hitWhat = tr.hitType == TRACE_HITTYPE_ENTITY ? "entity" : tr.hitType == TRACE_HITTYPE_DYNENT_MODEL ? "dynent model" :
        tr.hitType == TRACE_HITTYPE_DYNENT_BRUSH ? "dynent brush" : tr.hitType == TRACE_HITTYPE_GLASS ? "glass" : "world";
    const char *cls = "";
    if (tr.hitType == TRACE_HITTYPE_ENTITY && tr.hitId < MAX_GENTITIES && g_entities[tr.hitId].classname)
        cls = SL_ConvertToString(g_entities[tr.hitId].classname);
    const char *fn = a->scripted?"scripted":a->animFunction==a->scripts.move?"move":a->animFunction==a->scripts.stop?"stop":
        a->animFunction==a->scripts.combat?"combat":a->animFunction==a->scripts.jump?"traverse":a->animFunction?"other":"none";
    int blocked = CODOL_BotNavLinkBlocked(begin, end);
    DOG_DIAG("ent %d window stuck detail: at (%.0f %.0f %.0f); begin node %d (%.0f %.0f %.0f) end node %d z %.0f; sweep to end: fraction %.2f startsolid %d hit %s%s%s id %d contents 0x%x surf 0x%x material %s; link %s%d; animscript %s negotiating %d rm (%.2f %.2f %.2f) attempted %.1f\n",
        entity->s.number, entity->r.currentOrigin[0], entity->r.currentOrigin[1], entity->r.currentOrigin[2],
        begin, bp[0], bp[1], bp[2], end, ep[2], tr.fraction, tr.startsolid, hitWhat, *cls ? " " : "", cls, tr.hitId, tr.cflags, tr.sflags,
        tr.material ? tr.material : "-", blocked ? "CUT by ent " : "open ", blocked ? blocked-1 : 0,
        fn, a->negotiating, a->lastTranslation[0], a->lastTranslation[1], a->lastTranslation[2], a->stuckAttempt);
}

/* Every real wedge, once per actor per 48-unit spot: what the capsule sees
 * where it stands, below it, and 16 units along its wish direction at floor
 * level and one step up, plus the graph leg it was walking.  The window
 * detail above is added when a negotiation node is at hand. */
static const char *ActorHitKind(const trace_t *tr)
{
    return tr->fraction >= 1.0f && !tr->startsolid ? "nothing" :
        tr->hitType == TRACE_HITTYPE_ENTITY ? "entity" : tr->hitType == TRACE_HITTYPE_DYNENT_MODEL ? "dynent model" :
        tr->hitType == TRACE_HITTYPE_DYNENT_BRUSH ? "dynent brush" : tr->hitType == TRACE_HITTYPE_GLASS ? "glass" : "world";
}
static const char *ActorHitClass(const trace_t *tr)
{
    if (tr->hitType == TRACE_HITTYPE_ENTITY && tr->hitId < MAX_GENTITIES && g_entities[tr->hitId].classname)
        return SL_ConvertToString(g_entities[tr->hitId].classname);
    return "";
}
static void ActorWedgeDiag(gentity_s *entity, codol_actor_lifetime_t *a, const float *direction)
{
    const float *o = entity->r.currentOrigin;
    float sx = o[0]-a->wedgeDiagSpot[0], sy = o[1]-a->wedgeDiagSpot[1];
    if (a->wedgeDiagCount && sx*sx+sy*sy < 48.0f*48.0f) return;
    memcpy(a->wedgeDiagSpot, o, 12); ++a->wedgeDiagCount;
    trace_t stand, ground, flat, stepped, vertical, raisedForward, landing;
    float down[3] = {o[0], o[1], o[2]-18.0f};
    float ahead[3] = {o[0]+direction[0]*16.0f, o[1]+direction[1]*16.0f, o[2]};
    float up[3] = {o[0], o[1], o[2]+18.0f}, aheadUp[3] = {ahead[0], ahead[1], o[2]+18.0f};
    CODOL_ActorsPassable(entity, 1);
    G_TraceCapsule(&stand, o, entity->r.mins, entity->r.maxs, o, entity->s.number, entity->clipmask);
    G_TraceCapsule(&ground, o, entity->r.mins, entity->r.maxs, down, entity->s.number, entity->clipmask);
    G_TraceCapsule(&flat, o, entity->r.mins, entity->r.maxs, ahead, entity->s.number, entity->clipmask);
    G_TraceCapsule(&stepped, up, entity->r.mins, entity->r.maxs, aheadUp, entity->s.number, entity->clipmask);
    G_TraceCapsule(&vertical, o, entity->r.mins, entity->r.maxs, up, entity->s.number, entity->clipmask);
    float lift = 18.0f*vertical.fraction;
    float raised[3] = {o[0], o[1], o[2]+lift};
    float raisedAhead[3] = {ahead[0], ahead[1], ahead[2]+lift};
    G_TraceCapsule(&raisedForward, raised, entity->r.mins, entity->r.maxs,
        raisedAhead, entity->s.number, entity->clipmask);
    float landingEnd[3] = {raisedAhead[0], raisedAhead[1], raisedAhead[2]-lift-0.25f};
    G_TraceCapsule(&landing, raisedAhead, entity->r.mins, entity->r.maxs,
        landingEnd, entity->s.number, entity->clipmask);
    CODOL_ActorsPassable(entity, 0);
    int nearest = CODOL_BotNavNearest(o);
    const float *np = CODOL_BotNavPoint(nearest);
    int legFrom = -1, legTo = -1;
    if (a->routeCursor < a->routeCount) {
        legTo = a->route[a->routeCursor];
        legFrom = a->routeCursor > 0 ? a->route[a->routeCursor-1] : nearest;
    }
    char animState[160] = "";
    ActorDescribeTree(&a->tree, animState, sizeof(animState));
    DOG_DIAG("ent %d wedge detail at (%.1f %.1f %.1f) heading (%.2f %.2f): standing %s; floor 18 down: fraction %.2f normal z %.2f startsolid %d hit %s%s%s; ahead 16: fraction %.2f startsolid %d hit %s%s%s id %d contents 0x%x surf 0x%x material %s normal (%.2f %.2f %.2f); ahead 16 at +18: fraction %.2f startsolid %d hit %s; nearest node %d (%.0f %.0f %.0f) %.0f away, route leg %d -> %d; physics rejected %d throttled %d unstuck %d grounded %d vel (%.0f %.0f %.0f); %s\n",
        entity->s.number, o[0], o[1], o[2], direction[0], direction[1],
        stand.startsolid || stand.allsolid ? "IN SOLID" : "clear",
        ground.fraction, ground.normal[2], ground.startsolid, ActorHitKind(&ground), *ActorHitClass(&ground) ? " " : "", ActorHitClass(&ground),
        flat.fraction, flat.startsolid, ActorHitKind(&flat), *ActorHitClass(&flat) ? " " : "", ActorHitClass(&flat), flat.hitId, flat.cflags, flat.sflags,
        flat.material ? flat.material : "-", flat.normal[0], flat.normal[1], flat.normal[2],
        stepped.fraction, stepped.startsolid, ActorHitKind(&stepped),
        nearest, np ? np[0] : 0.0f, np ? np[1] : 0.0f, np ? np[2] : 0.0f,
        np ? sqrtf((np[0]-o[0])*(np[0]-o[0])+(np[1]-o[1])*(np[1]-o[1])) : 0.0f, legFrom, legTo,
        a->stuckRejected, a->stuckBlocked, a->physics.unstuck, a->physics.grounded,
        a->physics.velocity[0], a->physics.velocity[1], a->physics.velocity[2], animState);
    DOG_DIAG("ent %d step trial: up fraction %.3f startsolid %d normal z %.2f; raised forward fraction %.3f startsolid %d normal z %.2f; landing fraction %.3f startsolid %d normal z %.2f (lift %.2f)\n",
        entity->s.number, vertical.fraction, vertical.startsolid, vertical.normal[2],
        raisedForward.fraction, raisedForward.startsolid, raisedForward.normal[2],
        landing.fraction, landing.startsolid, landing.normal[2], lift);
    ActorWindowStuckDiag(entity, a);
}

/* ------------------------------------------------------------------------
 * T5 AIS_SCRIPTEDANIM.  GScr_AnimScripted_SP (OpenBLOPS g_scr_main_mp.cpp
 * :20578) pushes the state, kills the animscript and hands animscripts/
 * zombie_scripted.gsc the parameters; that script publishes the clip with
 * the flagged knob-all and waits for "killanimscript".  Here the builtin
 * (codol_script_anim.c) publishes the clip itself and this owns the actor
 * state: no goal, no route, no selection, no stuck detector while it holds.
 * MEASURED 2026-09-21 part 2: with the tear played by setFlaggedAnimKnobAll-
 * Restart from the entity thread, the move animscript's own knob-all loop
 * (zombie_move::MoveStandRun, every zombie_run_anim_update_time) drove the
 * walk cycle back to weight 1 over the tear clip, so no "board" note was
 * ever delivered and no board came down all session.
 * ------------------------------------------------------------------------ */
static void ActorFinishScripted(gentity_s *entity, const char *why)
{
    codol_actor_lifetime_t *a = CODOL_ActorForEntity(entity);
    if (!a) return;
    DOG_DIAG("ent %d animscripted %s after %d ms at (%.0f %.0f %.0f)\n", entity->s.number, why,
        level.time - a->scriptedStartTime, entity->r.currentOrigin[0], entity->r.currentOrigin[1], entity->r.currentOrigin[2]);
    a->scripted = 0; a->scriptedAlign = 0;
    a->safeToChangeScript = 1;
    a->scriptOrient = 0; a->scriptAnimMode = 0;
    a->routeCount = a->routeCursor = 0;
    memset(a->physics.velocity, 0, sizeof(a->physics.velocity));
    a->prevMoveDir[0] = a->prevMoveDir[1] = 0;
    a->stuckTime = 0; a->stuckCount = 0; a->stuckAttempt = 0; a->stuckRejected = a->stuckBlocked = 0;
}
static void ActorScriptedFrame(gentity_s *entity)
{
    codol_actor_lifetime_t *a = CODOL_ActorForEntity(entity);
    if (!a) return;
    unsigned generation = a->generation;
    if (level.time >= a->scriptedEndTime) { ActorFinishScripted(entity, "ran its length"); return; }
    float seconds = (level.time-level.previousTime)*.001f;
    if (a->scriptOrient == 1) {
        float facing[3] = {cosf(a->scriptYaw*.01745329252f), sinf(a->scriptYaw*.01745329252f), 0};
        ActorOrientToDirection(entity, facing, seconds);
    }
    if (a->scriptedAlign) {
        /* GScr_UpdateScriptedAnim consumes the origin offset a little per
         * update rather than snapping (T5 SP: 0.25 units per 50 ms tick, for
         * its cutscene-scale offsets).  The tear spot is 2-32 units off after
         * a goalradius-2 walk: 120 u/s closes that inside the 0.3 s blend. */
        float d[3] = {a->scriptedOrigin[0]-entity->r.currentOrigin[0], a->scriptedOrigin[1]-entity->r.currentOrigin[1], 0};
        float len = sqrtf(d[0]*d[0]+d[1]*d[1]);
        float most = fmaxf(2.0f, 120.0f*seconds);
        if (len <= most) a->scriptedAlign = 0;
        else { d[0] *= most/len; d[1] *= most/len; }
        if (len > 0.1f) CODOL_ActorMoveDelta(entity, d);
        a = CODOL_ActorForEntity(entity);
        if (!a || a->generation != generation) return;
    }
    CODOL_ActorAdvanceGoalAnimation(entity, level.time, 0);
}
extern "C" int CODOL_ActorScriptedAnimBegin(gentity_s *entity, const float *origin, const float *angles,
                                            const char *mode, int durationMsec)
{
    codol_actor_lifetime_t *a = CODOL_ActorForEntity(entity);
    if (!a || !a->initialized || !a->scriptsStarted || entity->health <= 0) return 0;
    unsigned generation = a->generation;
    if (!a->scripted) CODOL_ActorStopScript(entity);   /* T5 Actor_KillAnimScript */
    a = CODOL_ActorForEntity(entity);
    if (!a || a->generation != generation) return 0;
    static const char *names[]={"none","normal","pos deltas","angle deltas",
        "gravity","noclip","nogravity","zonly_physics","nophysics"};
    int m;
    for (m = 0; m < 9; ++m) if (mode && !strcmp(mode, names[m])) break;
    const float *o = entity->r.currentOrigin;
    float dx = origin[0]-o[0], dy = origin[1]-o[1], dz = origin[2]-o[2];
    int align = isfinite(dx) && isfinite(dy) && isfinite(dz) && dx*dx+dy*dy <= 64.0f*64.0f && fabsf(dz) <= 64.0f;
    a->scripted = 1;
    a->scriptedAlign = (unsigned char)align;
    a->safeToChangeScript = 0;
    a->scriptedStartTime = level.time;
    a->scriptedEndTime = level.time + (durationMsec > 0 ? durationMsec : 0) + 500;
    a->scriptAnimMode = m < 9 ? m : 1;
    a->scriptOrient = 1;
    a->scriptYaw = isfinite(angles[1]) ? angles[1] : entity->r.currentAngles[1];
    memcpy(a->scriptedOrigin, origin, 12);
    a->routeCount = a->routeCursor = 0;
    a->negotiationPending = 0;
    a->moveMode = 0;   /* no route direction: the clip's own delta (if any) is the only motion */
    memset(a->physics.velocity, 0, sizeof(a->physics.velocity));
    a->prevMoveDir[0] = a->prevMoveDir[1] = 0;
    a->stuckTime = 0; a->stuckCount = 0; a->stuckAttempt = 0; a->stuckRejected = a->stuckBlocked = 0;
    DOG_DIAG("ent %d animscripted: %d ms at (%.0f %.0f %.0f) yaw %.0f mode %s, from (%.0f %.0f %.0f) %.0f away%s\n",
        entity->s.number, durationMsec, origin[0], origin[1], origin[2], a->scriptYaw, m < 9 ? names[m] : "normal",
        o[0], o[1], o[2], sqrtf(dx*dx+dy*dy), align ? "" : " (too far to align; played in place)");
    return 1;
}
extern "C" int CODOL_ActorScriptedAnimStop(gentity_s *entity, const char *why)
{
    codol_actor_lifetime_t *a = CODOL_ActorForEntity(entity);
    if (!a || !a->scripted) return 0;
    ActorFinishScripted(entity, why ? why : "stopped");
    return 1;
}

int CODOL_ActorRunFrame(gentity_s *entity)
{
    codol_actor_lifetime_t *a = CODOL_ActorForEntity(entity);
    if (!a || !a->initialized) return 0;
    unsigned generation = a->generation;
    if (entity->health <= 0) {
        if(a->animFunction==a->scripts.death && a->animThread &&
           Scr_GetObjectType((unsigned short)a->animThread)==VAR_DEAD_THREAD) {
            ActorBecomeCorpse(entity);return 1;
        }
        a->scripted = 0; a->scriptedAlign = 0;
        a->safeToChangeScript=1;
        CODOL_ActorSwitchScript(entity, a->scripts.death, 0, 1);
        a=CODOL_ActorForEntity(entity);
        if(a && a->generation==generation)CODOL_ActorAdvanceGoalAnimation(entity,level.time,0);
        return 1;
    }
    if(!a->ignoreAll)ActorUpdateVisibleEnemy(entity);
    a=CODOL_ActorForEntity(entity);
    if(!a || a->generation!=generation)return 1;
    gentity_s *enemy = CODOL_ActorEnemy(entity);
    if (level.time - a->diagTime >= 1000) {
        const float *o = entity->r.currentOrigin;
        float dx=o[0]-a->diagOrigin[0], dy=o[1]-a->diagOrigin[1], dz=o[2]-a->diagOrigin[2];
        const char *fn = a->scripted?"scripted":a->animFunction==a->scripts.move?"move":a->animFunction==a->scripts.stop?"stop":
            a->animFunction==a->scripts.combat?"combat":a->animFunction==a->scripts.pain?"pain":
            a->animFunction==a->scripts.death?"death":a->animFunction?"other":"none";
        const char *st = a->species && a->species->stateName ?
            a->species->stateName((unsigned)a->animationState) : NULL;
        /* What the server animtree is actually playing: the heaviest leaf,
         * its weights, its normalised time and whether that clip carries a
         * delta (root-motion) track. "anim none (tree ... has no infos)"
         * means no set*anim* call ever landed on this tree; a named clip
         * with w 1.00 and t frozen means the tree holds it but never ticks;
         * a delta 1 clip with t advancing and rm (0 0 0) is the delta
         * evaluation itself. The tree pointer is the one the builtins print
         * in their "CoDOL anim:" lines, so the two can be matched. */
        char animState[1200] = "anim none";
        ActorDescribeTree(&a->tree, animState, sizeof(animState));
        DOG_DIAG("ent %d hp %d org (%.0f %.0f %.0f) moved %.0f/s goal %s(%.0f %.0f %.0f) route %d/%d enemy %d cand %d script %s state %s mode %d/%d/%d orient %d rm (%.2f %.2f %.2f) phys ok %d rej %d vel (%.0f %.0f %.0f) grounded %d tree %p %s\n",
            entity->s.number, entity->health, o[0], o[1], o[2], a->diagTime?sqrtf(dx*dx+dy*dy+dz*dz):0.0f,
            a->hasGoal?"":"NONE ", a->goal[0], a->goal[1], a->goal[2], a->routeCursor, a->routeCount,
            a->enemyNum, a->diagCandidates, fn, st?st:"?", a->scriptAnimMode, a->animMode, a->moveMode, a->scriptOrient,
            a->lastTranslation[0], a->lastTranslation[1], a->lastTranslation[2],
            a->movesAccepted, a->movesRejected, a->physics.velocity[0], a->physics.velocity[1],
            a->physics.velocity[2], a->physics.grounded, (const void *)&a->tree, animState);
        a->diagTime = level.time; memcpy(a->diagOrigin, o, 12);
        a->movesAccepted = a->movesRejected = 0;
    }
    /* T5 Actor_Negotiation_Think: while the traversal animscript runs, the
     * actor is its root motion and nothing else -- no chase goal, no route,
     * no stuck detector, no script re-selection.  The thread ending (or the
     * safety timeout) pops the state. */
    if (a->negotiating) { ActorNegotiationFrame(entity); return 1; }
    /* T5 AIS_SCRIPTEDANIM: the same hold while a scripted clip plays. */
    if (a->scripted) { ActorScriptedFrame(entity); return 1; }
    int attacking = enemy && a->animFunction == a->scripts.combat && !a->safeToChangeScript;
    if (enemy && !attacking) {
        codol_dog_attack_goal_t attack;
        // Original aitype/GSC owns attack distance; zero is not replaced by a
        // guessed reach. Synced player melee requires a separate native owner.
        CODOL_DogCombatGoal(entity, enemy, a->meleeAttackDistance, 0, &attack);
        attacking = attack.inAttackRange;
        const float *goal = attack.goalSet ? attack.goal : enemy->r.currentOrigin;
        float dx = goal[0]-a->goal[0], dy = goal[1]-a->goal[1];
        // T5 invalidates a chase path only once the destination moved >15 units.
        if (!a->hasGoal || dx*dx+dy*dy>225.0f || fabsf(goal[2]-a->goal[2])>15.0f)
            CODOL_ActorSetGoal(entity, goal);
        /* T5 Actor_UpdateMeleeGoalPos gives the attack spot its own code-goal
         * radius; with the script's 128-unit goalradius the dog reached "goal"
         * ~100 units short of bite range and thrashed move_start/stop_attackidle
         * every frame the enemy moved. Reach the spot itself (bite range). */
        a->chaseRadius = attack.goalSet ? 24.0f : fmaxf(24.0f, a->meleeAttackDistance);
    }
    float direction[3] = {0,0,0};
    int route = CODOL_ActorGoalDirection(entity, direction);
    a = CODOL_ActorForEntity(entity);
    if (!a || a->generation != generation) return 1;
    if (a->negotiationPending) {
        a->negotiationPending = 0;
        if (ActorStartNegotiation(entity)) return 1;
        a = CODOL_ActorForEntity(entity);
        if (!a || a->generation != generation) return 1;
    }
    /* A moving dog whose path runs into a low wall hops it (see
     * ActorStartWallHop).  Not while biting, flashed, in pain or turning. */
    if (route == 1 && ActorIsDog(a) && !attacking && !a->flashBanged && !a->painPending &&
        (a->animFunction == a->scripts.move || a->animFunction == a->scripts.turn || !a->animFunction) &&
        ActorStartWallHop(entity, direction))
        return 1;
    a = CODOL_ActorForEntity(entity);
    if (!a || a->generation != generation) return 1;
    /* T5 Path_UpdateLeanAmount/Path_UpdateMomentum: lean is the dot of the
     * wish direction with last frame's, negated when turning right; the run
     * knob's lean_L/lean_R weights come from it (BG_Dog_GetRunAnimWeights). */
    if (route == 1 && (a->prevMoveDir[0] != 0 || a->prevMoveDir[1] != 0)) {
        float lean = direction[0]*a->prevMoveDir[0] + direction[1]*a->prevMoveDir[1];
        if (lean > 0 && direction[0]*a->prevMoveDir[1] - direction[1]*a->prevMoveDir[0] < 0) lean = -lean;
        a->lean = fmaxf(-1.0f, fminf(1.0f, lean));
    } else a->lean = 0;
    if (route == 1) { a->prevMoveDir[0] = direction[0]; a->prevMoveDir[1] = direction[1]; }
    else a->prevMoveDir[0] = a->prevMoveDir[1] = 0;
    /* Stuck detector: a dog with somewhere to go that has not moved 8 units in
     * a second is wedged (corner, other dogs, unreachable spot). Drop the route
     * so it re-plans from the nearest node, release its attack-spot claim so
     * the next pick is a different spot, and on a repeat tell the script
     * (bad_path) so a patrol picks another node. */
    if (route == 1) {
        float sx = entity->r.currentOrigin[0]-a->stuckOrigin[0], sy = entity->r.currentOrigin[1]-a->stuckOrigin[1];
        if (sx*sx+sy*sy > 64.0f || !a->stuckTime) {
            memcpy(a->stuckOrigin, entity->r.currentOrigin, 12); a->stuckTime = level.time; a->stuckCount = 0;
            a->stuckAttempt = 0; a->stuckRejected = a->stuckBlocked = 0;
        } else if (level.time - a->stuckTime >= 1000 && a->stuckAttempt < 8.0f) {
            /* MEASURED 2026-09-21 (docs/CODOL_ZOMBIE_WINDOW_20260921.md): every
             * yard "stuck" of ent 576 on zm_prototype_sh sat on clear, flat
             * floor with rm (0 0 0) and ai_zombie_walk_v7 at t 0.37-0.49, and
             * the clip's own delta track is exactly zero from t 0.353 to
             * 0.579 -- an authored one-second pause.  That is not a wedge;
             * repathing and snapping it to a node only teleported it
             * backwards every second.  Wait the stall out.  Part 2: walk_v3
             * (t 0.58-0.75) and walk_v9 (t 0.33-0.48, 0.69-0.84) pause the
             * same way; the delta tracks were read correctly. */
            if (!a->stallDiagPrinted) {
                a->stallDiagPrinted = 1;
                char animState[160] = "";
                ActorDescribeTree(&a->tree, animState, sizeof(animState));
                DOG_DIAG("ent %d not moving for %d ms but the animation asked for only %.1f units of root motion (clip stall, not wedged; route kept): %s\n",
                    entity->s.number, level.time - a->stuckTime, a->stuckAttempt, animState);
            }
            a->stuckTime = level.time; a->stuckAttempt = 0; a->stuckRejected = a->stuckBlocked = 0;
        } else if (level.time - a->stuckTime >= 1000) {
            /* MEASURED 2026-09-21 part 2: ent 576 at (-1327 -844) was walking
             * walk_v3's slow section (6-8 u/s at rate 0.55) with phys ok 60
             * rej 0 -- the old "asked >= 8, moved < 8" verdict called that a
             * wedge, repathed, snapped it to node 379 (the rubberband) and
             * sent bad_path, which burned an entrance.  A wedge is motion
             * the PHYSICS refused or throttled; a slow cycle is neither. */
            int wedged = a->stuckRejected > 0 || a->stuckBlocked >= 15;
            if (!wedged) {
                if (!a->slowDiagPrinted) {
                    a->slowDiagPrinted = 1;
                    char animState[160] = "";
                    ActorDescribeTree(&a->tree, animState, sizeof(animState));
                    DOG_DIAG("ent %d moved under 8 units in %d ms with %.1f asked for, but physics accepted every move (rejected 0, throttled %d frames): a slow cycle, not a wedge; route kept: %s\n",
                        entity->s.number, level.time - a->stuckTime, a->stuckAttempt, a->stuckBlocked, animState);
                }
                a->stuckTime = level.time; a->stuckAttempt = 0; a->stuckRejected = a->stuckBlocked = 0;
            } else {
                ++a->stuckCount;
                ActorWedgeDiag(entity, a, direction);
                DOG_DIAG("ent %d stuck at (%.0f %.0f %.0f) for %d ms (asked %.1f, physics rejected %d, throttled %d, unstuck %d) -> %s\n", entity->s.number,
                    entity->r.currentOrigin[0], entity->r.currentOrigin[1], entity->r.currentOrigin[2],
                    level.time - a->stuckTime, a->stuckAttempt, a->stuckRejected, a->stuckBlocked, a->physics.unstuck,
                    a->stuckCount >= 2 ? "unwedge" : "repath");
                /* The link the actor was following when the physics refused
                 * it cannot be walked by this actor (a player-only vault or
                 * duck, a ledge): replanning over it again only wedges it on
                 * the same wall every second.  Ban it for this actor. */
                if (a->routeCursor >= a->routeCount) {
                    a->shortcutBanTime = level.time + 5000;
                    DOG_DIAG("ent %d wedged on the straight leg to its goal; following the waypoint route for 5 s\n", entity->s.number);
                }
                if (a->routeCursor < a->routeCount) {
                    int next = a->route[a->routeCursor];
                    int prev = a->routeCursor > 0 ? a->route[a->routeCursor-1] : CODOL_BotNavNearest(entity->r.currentOrigin);
                    /* Wedged walking from off the graph to the route's own
                     * start node: no link to ban, so the start pick avoids
                     * that node for this actor; the next plan starts from a
                     * node it can step to. */
                    if (a->routeCursor == 0 && !ActorStartBanned(a, next)) {
                        a->bannedStart[a->bannedStartCount++ % 4] = (unsigned short)next;
                        DOG_DIAG("ent %d wedged walking onto start node %d; the planner starts elsewhere for this actor\n",
                            entity->s.number, next);
                    }
                    if (prev >= 0 && prev != next && !ActorLinkBanned(a, prev, next)) {
                        unsigned slot = a->bannedLinkCount++ % 8;
                        a->bannedLinkFrom[slot] = (unsigned short)prev;
                        a->bannedLinkTo[slot] = (unsigned short)next;
                        DOG_DIAG("ent %d wedged on waypoint link %d -> %d; the planner avoids it for this actor\n",
                            entity->s.number, prev, next);
                    }
                }
                a->routeCount = a->routeCursor = 0;
                CODOL_DogCombatRelease(entity);
                a->stuckTime = level.time; a->stuckAttempt = 0; a->stuckRejected = a->stuckBlocked = 0;
                if (a->stuckCount >= 2) {
                    a->stuckCount = 0;
                    /* Second second in the same spot.  T5 has no teleport here
                     * and neither does this: the physics lifts a capsule that
                     * settled into the floor (codol_actor_physics.cpp), so what
                     * is left is a wall or a pile -- step sideways out of it.
                     * Only an actor that is startsolid where it stands, which
                     * cannot move at all, is placed on the nearest clear node,
                     * and only within 64 units (the old 256 was the "slide
                     * across the yard" the user saw).  No bad_path from here:
                     * that notify is the route planner's (T5 Path_FindPath),
                     * and firing it from a wedge cost one entrance per second. */
                    trace_t probe;
                    CODOL_ActorsPassable(entity, 1);
                    G_TraceCapsule(&probe, entity->r.currentOrigin, entity->r.mins, entity->r.maxs, entity->r.currentOrigin, entity->s.number, entity->clipmask);
                    CODOL_ActorsPassable(entity, 0);
                    if (probe.startsolid || probe.allsolid) {
                        int candidates[2] = {-1, CODOL_BotNavNearest(entity->r.currentOrigin)};
                        if (a->routeCursor < a->routeCount) candidates[0] = a->route[a->routeCursor];
                        int snapped = 0;
                        for (int c = 0; c < 2 && !snapped; ++c) {
                            const float *point = candidates[c] >= 0 ? CODOL_BotNavPoint(candidates[c]) : NULL;
                            if (!point) continue;
                            float dx = point[0]-entity->r.currentOrigin[0], dy = point[1]-entity->r.currentOrigin[1];
                            if (dx*dx+dy*dy >= 64.0f*64.0f) continue;
                            static const float lifts[3] = {1.0f, 20.0f, 44.0f};
                            for (int l = 0; l < 3 && !snapped; ++l) {
                                float origin[3] = {point[0], point[1], point[2]+lifts[l]};
                                CODOL_ActorsPassable(entity, 1);
                                G_TraceCapsule(&probe, origin, entity->r.mins, entity->r.maxs, origin, entity->s.number, entity->clipmask);
                                CODOL_ActorsPassable(entity, 0);
                                if (probe.startsolid || probe.allsolid) continue;
                                DOG_DIAG("ent %d embedded in solid: placed on nav node %d (%.0f %.0f %.0f) lift %.0f, %.0f away\n", entity->s.number, candidates[c], origin[0], origin[1], origin[2], lifts[l], sqrtf(dx*dx+dy*dy));
                                G_SetOrigin(entity, origin);
                                memcpy(a->sentient->origin, origin, 12);
                                memset(a->physics.velocity, 0, 12);
                                SV_LinkEntity(entity);
                                snapped = 1;
                            }
                        }
                        if (!snapped && ActorIsDog(a) && ActorRecoverFromSolid(entity, a)) snapped = 1;
                        if (!snapped) DOG_DIAG("ent %d embedded in solid and no clear nav node within 64; left in place\n", entity->s.number);
                    } else {
                        float nudge[3] = {-direction[1]*12.0f, direction[0]*12.0f, 0};
                        if ((level.time/1000)&1) { nudge[0] = -nudge[0]; nudge[1] = -nudge[1]; }
                        CODOL_ActorMoveDelta(entity, nudge);
                    }
                }
            }
        }
    } else { a->stuckTime = 0; a->stuckCount = 0; }
    /* Radial push-out between overlapping actors (capsule radius 15): the
     * separation steering above avoids most piles, this resolves the rest. */
    for (unsigned i = 0; i < CODOL_MAX_ACTOR_SLOTS; ++i) {
        codol_actor_lifetime_t *o = &actors[i];
        if (!o->allocated || !o->initialized || o->entity == entity || !o->entity || !o->entity->r.inuse ||
            o->entity->health <= 0) continue;
        float ox = entity->r.currentOrigin[0] - o->entity->r.currentOrigin[0];
        float oy = entity->r.currentOrigin[1] - o->entity->r.currentOrigin[1];
        float oz = entity->r.currentOrigin[2] - o->entity->r.currentOrigin[2];
        float d = sqrtf(ox*ox + oy*oy);
        if (fabsf(oz) > 48.0f || d >= 30.0f) continue;
        if (d < 1.0f) { ox = (float)((entity->s.number & 1) ? 1 : -1); oy = 0; d = 1.0f; }
        float push = fminf(4.0f, (30.0f - d) * 0.5f);
        float delta[3] = {ox / d * push, oy / d * push, 0};
        int rc = a->routeCount, rcur = a->routeCursor; /* a blocked push is not a route failure */
        CODOL_ActorMoveDelta(entity, delta);
        a = CODOL_ActorForEntity(entity);
        if (!a || a->generation != generation) return 1;
        a->routeCount = rc; a->routeCursor = rcur;
    }
    a = CODOL_ActorForEntity(entity);
    if (!a || a->generation != generation) return 1;
    memcpy(a->lookAheadDir,direction,sizeof(a->lookAheadDir));
    // T5 Actor_PathEndActions: the original move script owns stop blending.
    // Only a complete remaining route may emit stop_soon; melee approach does not.
    if (route == 1 && a->stopAnimDistSq > 0) {
        float dx=entity->r.currentOrigin[0]-a->goal[0];
        float dy=entity->r.currentOrigin[1]-a->goal[1];
        float distanceSq=dx*dx+dy*dy;
        const char *event=NULL;
        if(a->pathEndAnimNotified && distanceSq>a->stopAnimDistSq) {
            a->pathEndAnimNotified=0;event="run";
        } else if(!a->pathEndAnimNotified && distanceSq<a->stopAnimDistSq &&
                  a->routeCursor>=a->routeCount && !enemy) {
            a->pathEndAnimNotified=1;event="stop_soon";Scr_AddFloat(sqrtf(distanceSq));
        }
        if(event) {
            unsigned name=SL_GetString(event,0);
            Scr_Notify(entity,(unsigned short)name,event[0]=='s'?1:0);
            SL_RemoveRefToString(name);
            a=CODOL_ActorForEntity(entity);
            if(!a || a->generation!=generation)return 1;
        }
    }
    /* Pain is a script-owned state, not a one-frame pulse. Let the original
     * DoNoteTracksForTime finish; death above can still interrupt immediately.
     * T5 Actor_Dog_Think: a flashbanged dog that is not in a synced melee (MP
     * dogs never start one: dog_cant_kill_in_one_hit is always true) runs
     * the flashed animscript (Actor_Exposed_FlashBanged: move stop, orient
     * don't change) instead of attacking or moving, until the script that
     * clears the flag ends. */
    int painRunning = a->animFunction==a->scripts.pain && a->animThread &&
        Scr_GetObjectType((unsigned short)a->animThread)!=VAR_DEAD_THREAD;
    int flashRunning = a->animFunction==a->scripts.flashed && a->animThread &&
        Scr_GetObjectType((unsigned short)a->animThread)!=VAR_DEAD_THREAD;
    int flashed = (a->flashBanged || flashRunning) && !a->painPending && !painRunning;
    /* T5 Actor_Dog_ShouldTurn (actor_dog_exposed.cpp): a moving dog whose
     * path direction is more than dog_turn90_angle off its facing, with at
     * least dog_turn_min_goal_dist of path left, runs the species turn
     * animscript (dog_turn: 90/180 turn states, which C1 maps to its
     * run_start_L/R and run_start_180_L/R clips); a running turn is not
     * interrupted until the script says it is safe. */
    int turnRunning = a->scripts.turn && a->animFunction==a->scripts.turn && a->animThread &&
        Scr_GetObjectType((unsigned short)a->animThread)!=VAR_DEAD_THREAD && !a->safeToChangeScript;
    int turning = 0;
    if (ActorIsDog(a) && a->scripts.turn && route == 1 && !attacking && !flashed &&
        !a->painPending && !painRunning) {
        if (turnRunning) turning = 1;
        else if (a->animFunction == a->scripts.move && (direction[0] != 0 || direction[1] != 0)) {
            /* _dogs.gsc registers these from script (setdvar: string
             * dvars), so read them parsed; T5 defaults when unset. */
            float threshold = Cvar_FindVar("dog_turn90_angle") ? Cvar_VariableValue("dog_turn90_angle") : 70.0f;
            float minGoal = Cvar_FindVar("dog_turn_min_goal_dist") ? Cvar_VariableValue("dog_turn_min_goal_dist") : 40.0f;
            float gx = a->goal[0]-entity->r.currentOrigin[0], gy = a->goal[1]-entity->r.currentOrigin[1];
            float yaw = atan2f(direction[1], direction[0]) * 57.295779513f;
            float delta = fmodf(yaw - entity->r.currentAngles[1], 360.0f);
            if (delta > 180) delta -= 360; if (delta < -180) delta += 360;
            if ((a->routeCursor < a->routeCount || gx*gx+gy*gy >= minGoal*minGoal) && fabsf(delta) > threshold)
                turning = 1;
        }
    }
    float facing[3] = {direction[0],direction[1],0};
    if (flashed) {
        facing[0]=facing[1]=0;
    } else if (a->scriptOrient == 1) {
        facing[0]=cosf(a->scriptYaw*.01745329252f);
        facing[1]=sinf(a->scriptYaw*.01745329252f);
    } else if ((a->scriptOrient == 2 || a->scriptOrient == 3 ||
                (!a->scriptOrient && attacking)) && enemy) {
        facing[0]=enemy->r.currentOrigin[0]-entity->r.currentOrigin[0];
        facing[1]=enemy->r.currentOrigin[1]-entity->r.currentOrigin[1];
    } else if (a->scriptOrient == 2) {
        facing[0]=facing[1]=0;
    } else if (a->scriptOrient == 4 && a->hasGoal) {
        facing[0]=a->goal[0]-entity->r.currentOrigin[0];
        facing[1]=a->goal[1]-entity->r.currentOrigin[1];
    }
    ActorOrientToDirection(entity,facing,(level.time-level.previousTime)*.001f);
    // Original species GSC remains the animation-state producer. Native path
    // progress chooses movement versus stop; no timer-driven dog imitation.
    int function = (a->painPending || painRunning) ? a->scripts.pain : flashed ? a->scripts.flashed :
        attacking ? a->scripts.combat : turning ? a->scripts.turn : (route == 1 ? a->scripts.move : a->scripts.stop);
    if (!CODOL_ActorSwitchScript(entity, function, !flashed && !attacking && route == 1 ? 3 : 0, 1)) return 1;
    a = CODOL_ActorForEntity(entity);
    if (!a || a->generation != generation) return 1;
    if(a->animFunction==a->scripts.pain)a->painPending=0;
    if(a->lastAnimationTime<level.time && a->species && a->species->stateApply) {
        DObj *obj=Com_GetServerDObj(entity->s.number);
        if(!a->species->stateApply(obj,entity->s.number,a->generation,a->serverTree,level.time,
            a->animationState,a->animationState,0,a->animationRate,a->lean,a->aimUp,a->aimLeft)) return 1;
        a->lastAnimationTime=level.time;
    }
    CODOL_ActorAdvanceGoalAnimation(entity, level.time, 0);
    return 1;
}

extern "C" int CODOL_PathNodeOrigin(unsigned index, float *origin);
static void CODOL_ActorSetGoalNode(scr_entref_t ref)
{
    if (ref.classnum || ref.entnum >= ENTITYNUM_WORLD ||
        !CODOL_ActorForEntity(&g_entities[ref.entnum])) {
        Scr_ObjectError("setgoalnode requires a live native actor");
        return;
    }
    scr_entref_t node = Scr_GetEntityRef(0);
    float point[3];
    if (node.classnum != 2 || !CODOL_PathNodeOrigin(node.entnum, point)) {
        Scr_ParamError(0, "setgoalnode requires a current path node with an origin");
        return;
    }
    CODOL_ActorSetGoal(&g_entities[ref.entnum], point);
    CODOL_ActorForEntity(&g_entities[ref.entnum])->goalNode = node.entnum;
}
static codol_actor_lifetime_t *ActorMethodReceiver(scr_entref_t ref)
{
    if (ref.classnum || ref.entnum>=ENTITYNUM_WORLD) {
        Scr_ObjectError("method requires a native actor"); return NULL;
    }
    codol_actor_lifetime_t *a=CODOL_ActorForEntity(&g_entities[ref.entnum]);
    if (!a) Scr_ObjectError("method requires a live native actor");
    return a;
}
static void ActorSetAnimationState(scr_entref_t ref)
{
    codol_actor_lifetime_t *a=ActorMethodReceiver(ref);
    if (!a) return;
    /* The animation-state machine is a species column. A species whose
     * backend is NULL has no native clip table (T5 animates it from GSC
     * %anim references instead) and must say so, rather than be handed some
     * other species' state names. */
    if (!a->species || !a->species->stateApply || !a->species->stateIndex) {
        /* Not a gap to be filled with an invented clip table: T5 has no
         * native animation state machine for any species but the dog, and
         * animates the rest from GSC. That scripted surface is registered
         * (src/codol/script/codol_script_anim.c: setanim, setanimknob,
         * setanimknoball, the setflaggedanim* family, clearanim,
         * setanimtime, getanimtime) and publishes onto the same wire this
         * method does, so a species with no native backend animates by
         * calling those from its animscripts instead of this. */
        Scr_Error("setanimstate: this actor species has no native animation "
                  "state machine; animate it from its animscripts with "
                  "setanim/setflaggedanimknoball and a %anim reference");
        return;
    }
    int state=a->species->stateIndex(Scr_GetString(0));
    if (state<0) {Scr_ParamError(0,"unknown original MP actor animation state");return;}
    DObj *obj=Com_GetServerDObj(a->entity->s.number);
    if (!a->tree.anims || !a->species->stateApply(obj,a->entity->s.number,a->generation,
        a->serverTree,level.time,state,a->animationState,1,a->animationRate,a->lean,a->aimUp,a->aimLeft)) {
        DOG_DIAG("ent %d setanimstate '%s' FAILED (tree %s, dobj %s)\n", a->entity->s.number,
            Scr_GetString(0), a->tree.anims?"owned":"none", obj?"yes":"no");
        Scr_Error("actor animation state could not publish its native C1 tree transaction");return;
    }
    if (state != a->diagState) {
        DOG_DIAG("ent %d setanimstate '%s' (from '%s')\n", a->entity->s.number, Scr_GetString(0),
            a->species->stateName?a->species->stateName((unsigned)a->animationState):"?");
        a->diagState = state;
    }
    a->animationState=state;
    a->lastAnimationTime=level.time;
}
static void ActorSetAimAnimationWeights(scr_entref_t ref)
{
    codol_actor_lifetime_t *a=ActorMethodReceiver(ref);
    if (!a)return;
    float up=Scr_GetFloat(0),left=Scr_GetFloat(1);
    if (!isfinite(up)||!isfinite(left)){Scr_Error("actor aim weights must be finite");return;}
    a->aimUp=up;a->aimLeft=left;
}
static void ActorDeltaTurnYaw(scr_entref_t ref)
{
    codol_actor_lifetime_t *a=ActorMethodReceiver(ref);
    if(!a)return;
    if(!a->hasGoal){Scr_AddFloat(0);return;}
    const float *point=a->goal;
    if(a->routeCursor<a->routeCount) {
        const float *route=CODOL_BotNavPoint(a->route[a->routeCursor]);
        if(route)point=route;
    }
    float yaw=atan2f(point[1]-a->entity->r.currentOrigin[1],point[0]-a->entity->r.currentOrigin[0])*57.295779513f;
    float delta=fmodf(yaw-a->entity->r.currentAngles[1],360.0f);
    if(delta>180)delta-=360;if(delta< -180)delta+=360;
    Scr_AddFloat(delta);
}
unsigned CODOL_ActorEnemyModel(gentity_s *entity)
{
    codol_actor_lifetime_t *a=CODOL_ActorForEntity(entity);
    return a?a->enemyModel:0;
}
static void ActorSetEnemyModel(scr_entref_t ref)
{
    codol_actor_lifetime_t *a=ActorMethodReceiver(ref);if(!a)return;
    const char *name=Scr_GetString(0);
    /* CoDOL replaces G_ModelIndex with the runtime bank registrar (the same
     * substitution _g_items.asm makes under CODOL_SERVER): a killstreak model
     * name is only known when the reward fires, so it cannot be a level-load
     * precache. Returns 0 when the bank is full, never an unpublished slot. */
    a->enemyModel=*name?CODOL_RegisterRuntimeModel(name):0;
    DOG_DIAG("ent %d setenemymodel '%s' -> model %u (friendly model %u%s)\n", a->entity->s.number,
        name, a->enemyModel, a->entity->model, a->enemyModel==a->entity->model?", identical: C1 ships one dog model":"");
}
static void ActorOwner(scr_entref_t ref)
{
    codol_actor_lifetime_t *a=ActorMethodReceiver(ref);if(!a)return;
    gentity_s *owner=Scr_GetEntity(0);
    a->entity->r.ownerNum.setEnt(owner);
    a->sentient->ownerNum=owner?owner->s.number:-1;
}
static void ActorClearOwner(scr_entref_t ref)
{
    codol_actor_lifetime_t *a=ActorMethodReceiver(ref);if(!a)return;
    a->entity->r.ownerNum.setEnt(NULL);a->sentient->ownerNum=-1;
}
static void ActorClearTarget(scr_entref_t ref)
{
    codol_actor_lifetime_t *a=ActorMethodReceiver(ref);if(!a)return;
    CODOL_ActorSetEnemy(a->entity,NULL);
}
/* A destination whose capsule starts solid freezes the actor for good: the
 * first sweep in codol_actor_physics.cpp slide() returns 0 on startsolid, so
 * EVERY move is rejected and the origin never changes again -- MEASURED
 * 2026-09-20, 116 of 360 zm diag samples logged "phys ok 0 rej 60 grounded 0"
 * with zero velocity, i.e. a third of the zombies were wedged in geometry
 * from the moment they were placed.
 *
 * T5 does not place an actor into solid either: SpawnActor's CHECK_SPAWN arm
 * refuses the spawn outright when SpotWouldTelefrag(ent) (OpenBLOPS
 * Game/Server/game/actor_spawner.cpp:141-157). Refusing is wrong for this
 * caller -- the zm spawn structs are all this map offers, and dropping them
 * would just mean fewer zombies -- so the same test is used to LIFT the
 * capsule out instead, one step height at a time up to its own height, then
 * settle it back down onto whatever floor the lift cleared. Actors are made
 * passable for the test exactly as the physics move does, so overlapping
 * another zombie is not mistaken for solid. A destination that cannot be
 * resolved is left where script asked and named in the log. */
static int ActorResolveSolidOrigin(gentity_s *entity,float *origin)
{
    trace_t trace;
    CODOL_ActorsPassable(entity,1);
    G_TraceCapsule(&trace,origin,entity->r.mins,entity->r.maxs,origin,
                   entity->s.number,entity->clipmask);
    int solid=trace.startsolid || trace.allsolid;
    if(solid) {
        float height=entity->r.maxs[2]-entity->r.mins[2];
        for(float lift=18.0f;lift<=height+18.0f;lift+=18.0f) {
            float probe[3]={origin[0],origin[1],origin[2]+lift};
            G_TraceCapsule(&trace,probe,entity->r.mins,entity->r.maxs,probe,
                           entity->s.number,entity->clipmask);
            if(trace.startsolid || trace.allsolid)continue;
            float floorPos[3]={probe[0],probe[1],probe[2]-lift-18.0f};
            G_TraceCapsule(&trace,probe,entity->r.mins,entity->r.maxs,floorPos,
                           entity->s.number,entity->clipmask);
            if(!trace.startsolid && !trace.allsolid && trace.fraction<1)
                probe[2]+=(floorPos[2]-probe[2])*trace.fraction;
            DOG_DIAG("ent %d teleport destination (%.0f %.0f %.0f) is solid; lifted to (%.0f %.0f %.0f)\n",
                entity->s.number,origin[0],origin[1],origin[2],probe[0],probe[1],probe[2]);
            memcpy(origin,probe,12);
            CODOL_ActorsPassable(entity,0);
            return 1;
        }
        DOG_DIAG("ent %d teleport destination (%.0f %.0f %.0f) is solid and no lift up to %.0f units clears it; the actor will not be able to move\n",
            entity->s.number,origin[0],origin[1],origin[2],height+18.0f);
    }
    CODOL_ActorsPassable(entity,0);
    return !solid;
}
static void ActorForceTeleport(scr_entref_t ref)
{
    codol_actor_lifetime_t *a=ActorMethodReceiver(ref);if(!a)return;
    float origin[3],angles[3];Scr_GetVector(0,origin);
    if(Scr_GetNumParam()>1)Scr_GetVector(1,angles);else memcpy(angles,a->entity->r.currentAngles,12);
    for(int i=0;i<3;++i)if(!isfinite(origin[i])||!isfinite(angles[i])){Scr_Error("actor teleport requires finite vectors");return;}
    ActorResolveSolidOrigin(a->entity,origin);
    G_SetOrigin(a->entity,origin);
    memcpy(a->entity->r.currentAngles,angles,12);memcpy(a->entity->s.lerp.apos.trBase,angles,12);
    memcpy(a->sentient->origin,origin,12);memset(&a->physics,0,sizeof(a->physics));
    a->routeCount=a->routeCursor=0;
    SV_LinkEntity(a->entity);
}
struct codol_actor_melee_params {
    float forward[3],right[3],up[3],muzzleTrace[3],gunForward[3];
    WeaponDef *weapon;
};
static_assert(offsetof(codol_actor_melee_params,weapon)==0x3c,"retained weaponParms ABI");
extern "C" gentity_s *CODOL_ActorMeleeTrace(gentity_s *,codol_actor_melee_params *,float,float,float);
static cvar_t *actorMeleeRange,*actorMeleeWidth,*actorMeleeHeight;
static void ActorEye(gentity_s *entity,float *position)
{
    float matrix[4][3];unsigned tag=SL_GetString("tag_eye",0);
    int found=G_DObjGetWorldTagMatrix(entity,tag,matrix);
    SL_RemoveRefToString(tag);
    if(found)memcpy(position,matrix[3],12);
    else {memcpy(position,entity->r.currentOrigin,12);position[2]+=64;}
}
static void ActorGetEye(scr_entref_t ref)
{
    if(!ref.classnum && ref.entnum<ENTITYNUM_WORLD && CODOL_ActorForEntity(&g_entities[ref.entnum])) {
        float eye[3];ActorEye(&g_entities[ref.entnum],eye);Scr_AddVector(eye);return;
    }
    ScrCmd_GetEye(ref);
}
static void ActorMelee(scr_entref_t ref)
{
    codol_actor_lifetime_t *a=ActorMethodReceiver(ref);if(!a)return;
    if(a->lastMeleeTime==level.time)return;
    const char *name=a->weaponName?SL_ConvertToString(a->weaponName):"";
    int weapon=G_GetWeaponIndexForName(name);
    if(!weapon){Scr_Error("actor melee requires its real aiweapon definition");return;}
    codol_actor_melee_params params={};params.weapon=BG_GetWeaponDef(weapon);
    if(!params.weapon){Scr_Error("actor melee definition unavailable");return;}
    ActorEye(a->entity,params.muzzleTrace);
    AngleVectors(a->entity->r.currentAngles,params.forward,params.right,params.up);
    float direction[3];int hasDirection=Scr_GetNumParam()!=0;
    if(hasDirection){Scr_GetVector(0,direction);for(int i=0;i<3;++i)if(!isfinite(direction[i])){Scr_ParamError(0,"melee direction must be finite");return;}}
    gentity_s *enemy=CODOL_ActorEnemy(a->entity);
    if(enemy) {
        float target[3];
        if(enemy->client){memcpy(target,enemy->r.currentOrigin,12);target[2]+=enemy->client->ps.viewHeightCurrent;}
        else ActorEye(enemy,target);
        for(int i=0;i<3;++i)params.forward[i]=target[i]-params.muzzleTrace[i];
        if(hasDirection) {
            float length=sqrtf(direction[0]*direction[0]+direction[1]*direction[1]);
            if(length==0){Scr_ParamError(0,"melee direction needs horizontal component");return;}
            float scale=sqrtf(params.forward[0]*params.forward[0]+params.forward[1]*params.forward[1])/length;
            params.forward[0]=direction[0]*scale;params.forward[1]=direction[1]*scale;
        }
    } else if(hasDirection)memcpy(params.forward,direction,12);
    float length=sqrtf(params.forward[0]*params.forward[0]+params.forward[1]*params.forward[1]+params.forward[2]*params.forward[2]);
    if(length==0)return;
    for(int i=0;i<3;++i)params.forward[i]/=length;
    memcpy(params.gunForward,params.forward,12);
    a->lastMeleeTime=level.time;
    a->entity->s.weapon=weapon;
    gentity_s *hit=CODOL_ActorMeleeTrace(a->entity,&params,actorMeleeRange->value,
        actorMeleeWidth->value,actorMeleeHeight->value);
    if(hit && hit->r.inuse)Scr_AddEntity(hit);
}
static void ActorVelocity(scr_entref_t ref)
{
    if(!ref.classnum && ref.entnum<ENTITYNUM_WORLD) {
        codol_actor_lifetime_t *a=CODOL_ActorForEntity(&g_entities[ref.entnum]);
        if(a){Scr_AddVector(a->physics.velocity);return;}
    }
    PlayerCmd_GetVelocity(ref);
}
static void ActorTalkSpecies(scr_entref_t ref)
{
    codol_actor_lifetime_t *a=ActorMethodReceiver(ref);if(!a)return;
    int mask=0;
    for(unsigned i=0;i<Scr_GetNumParam();++i) {
        const char *species=Scr_GetString(i);
        if(!strcmp(species,"all")){mask=-1;break;}
        const codol_actor_species_t *row=CODOL_ActorSpeciesByName(species);
        if(row)mask|=row->talkBit;
        // Original T5 ignores unrecognized species rather than errors.
    }
    a->talkMask=mask;
}
static void ActorEngagementMin(scr_entref_t ref)
{
    codol_actor_lifetime_t *a=ActorMethodReceiver(ref);if(!a)return;
    float distance=Scr_GetFloat(0),falloff=Scr_GetFloat(1);
    if(!isfinite(distance)||!isfinite(falloff)||falloff>distance){Scr_Error("minimum distance falloff must be <= minimum distance");return;}
    a->engageMin=distance;a->engageMinFalloff=falloff;
}
static void ActorEngagementMax(scr_entref_t ref)
{
    codol_actor_lifetime_t *a=ActorMethodReceiver(ref);if(!a)return;
    float distance=Scr_GetFloat(0),falloff=Scr_GetFloat(1);
    if(!isfinite(distance)||!isfinite(falloff)||falloff<distance){Scr_Error("maximum distance falloff must be >= maximum distance");return;}
    a->engageMax=distance;a->engageMaxFalloff=falloff;
}
static void ActorAnimationMode(scr_entref_t ref)
{
    codol_actor_lifetime_t *a=ActorMethodReceiver(ref);
    if(!a)return;
    const char *name=Scr_GetString(0);
    static const char *names[]={"none","normal","pos deltas","angle deltas",
        "gravity","noclip","nogravity","zonly_physics","nophysics"};
    int mode;
    for(mode=0;mode<9;++mode)if(!strcmp(name,names[mode]))break;
    if(mode==9){Scr_ParamError(0,"unsupported actor animmode (point-relative anchor is not implemented)");return;}
    if(mode && (Scr_GetNumParam()<2 || Scr_GetInt(1))) {
        // Clear current route, not the authored script goal.
        a->routeCount=a->routeCursor=0;
    }
    a->scriptAnimMode=mode;
}
static void ActorSetGoalPosition(scr_entref_t ref)
{
    codol_actor_lifetime_t *a=ActorMethodReceiver(ref);
    if (!a) return;
    float goal[3]; Scr_GetVector(0,goal);
    if (!CODOL_ActorSetGoal(a->entity,goal))
        Scr_ParamError(0,"setgoalpos requires a finite position");
}
static void ActorOrientMode(scr_entref_t ref)
{
    codol_actor_lifetime_t *a=ActorMethodReceiver(ref);
    if (!a) return;
    const char *mode=Scr_GetString(0);
    int orientation=0;
    float yaw=a->entity->r.currentAngles[1], vector[3];
    if (!strcmp(mode,"face angle")) {orientation=1;yaw=Scr_GetFloat(1);}
    else if (!strcmp(mode,"face current")) orientation=1;
    else if (!strcmp(mode,"face direction") || !strcmp(mode,"face point")) {
        Scr_GetVector(1,vector);
        if (!isfinite(vector[0]) || !isfinite(vector[1]) || !isfinite(vector[2])) {
            Scr_ParamError(1,"orientation vector must be finite");return;
        }
        int point=!strcmp(mode,"face point");
        if (point) for(int i=0;i<3;++i) vector[i]-=a->entity->r.currentOrigin[i];
        if (!point && vector[0]==0 && vector[1]==0) {
            Scr_ParamError(1,"cannot face (0,0,*)");return;
        }
        orientation=1;
        if (!point || vector[0]*vector[0]+vector[1]*vector[1]>=1)
            yaw=atan2f(vector[1],vector[0])*57.295779513f;
    } else if (!strcmp(mode,"face enemy")) orientation=2;
    else if (!strcmp(mode,"face enemy or motion")) orientation=3;
    else if (!strcmp(mode,"face goal")) orientation=4;
    else if (!strcmp(mode,"face motion")) orientation=5;
    else if (strcmp(mode,"face default")) {Scr_ParamError(0,"unknown actor orientation mode");return;}
    if (!isfinite(yaw)) {Scr_ParamError(1,"orientation yaw must be finite");return;}
    a->scriptOrient=orientation;
    a->scriptYaw=yaw;
    if (Scr_GetNumParam()>2 && Scr_GetInt(2)>0) {
        a->entity->r.currentAngles[1]=yaw;
        memcpy(a->entity->s.lerp.apos.trBase,a->entity->r.currentAngles,12);
    }
}
/* ---------------------------------------------------------------------------
 * The remaining engine surface the ported dog scripts call.
 *
 * These are AI/actor facilities IW4OL never had: the dog animscripts are the
 * first script in this tree that asks the engine whether an entity is an AI,
 * whether it can see another entity, where to aim at it, or to flashbang it.
 * Each is implemented against the native actor record, with an honest arm for
 * a non-actor receiver rather than a constant stand-in.
 * ------------------------------------------------------------------------ */

/* isai( <entity> )
 * IW4/T5 return true only for an actual AI actor. A player, a script model and
 * a bot client are all false here: a bot is a client, not a sentient actor. */
static void ScrActorIsAI(void)
{
    gentity_s *entity = Scr_GetEntity(0);
    Scr_AddBool(entity && !entity->client && CODOL_ActorForEntity(entity) != NULL);
}

/* <actor> setFlashBanged( <on>, [<strength>] )
 * T5 ActorCmd_SetFlashBanged / Actor_SetFlashed (OpenBLOPS
 * game/actor_script_cmd.cpp, game_mp/actor_mp.cpp): one or two arguments,
 * strength defaults to 1; "off" clears flag and strength, "on" raises the
 * strength to the larger of the two and sets the flag.  The flag has no
 * expiry: the dog think (Actor_Dog_Think -> Actor_Exposed_FlashBanged) runs
 * the flashed animscript while it is set, and that script clears it. */
static void ActorSetFlashBanged(scr_entref_t ref)
{
    codol_actor_lifetime_t *a = ActorMethodReceiver(ref); if (!a) return;
    unsigned params = Scr_GetNumParam();
    if (params != 1 && params != 2) { Scr_Error("Invalid call to setFlashBanged()."); return; }
    float strength = params == 2 ? Scr_GetFloat(1) : 1.0f;
    if (!isfinite(strength)) { Scr_ParamError(1, "flashbang strength must be finite"); return; }
    if (!Scr_GetInt(0)) { a->flashBanged = 0; a->flashStrength = 0; return; }
    if (strength > a->flashStrength) a->flashStrength = strength;
    a->flashBanged = 1;
}

/* <actor> getFlashBangedStrength()
 * T5 ActorCmd_GetFlashBangedStrength: the stored strength. dog_flashed
 * multiplies it by 1000 for its flashendtime. */
static void ActorGetFlashBangedStrength(scr_entref_t ref)
{
    codol_actor_lifetime_t *a = ActorMethodReceiver(ref); if (!a) return;
    Scr_AddFloat(a->flashStrength);
}

/* C1 0x578a10's actor arm (actor +0xffc): the eye of an actor, 0 for an
 * entity that is not one. Used by the turret aim point. */
extern "C" int CODOL_ActorEyePosition(gentity_s *entity, float *position)
{
    if (!entity || !entity->r.inuse || !CODOL_ActorForEntity(entity)) return 0;
    ActorEye(entity, position);
    return 1;
}

/* Aim point: the eye of a client, the tag_eye of an actor. */
static int ScrShootAtPosition(gentity_s *entity, float *position)
{
    if (!entity || !entity->r.inuse) return 0;
    if (entity->client) {
        memcpy(position, entity->r.currentOrigin, 12);
        position[2] += entity->client->ps.viewHeightCurrent;
        return 1;
    }
    if (CODOL_ActorForEntity(entity)) { ActorEye(entity, position); return 1; }
    memcpy(position, entity->r.currentOrigin, 12);
    position[2] += (entity->r.mins[2] + entity->r.maxs[2]) * .5f;
    return 1;
}

/* <entity> getShootAtPos()
 * Called on the dog's ENEMY, which in MP is always a player, so the client arm
 * is the reachable one. Nothing is returned for a freed entity, which is the
 * undefined result dog_shared::trackLoop already tests for. */
static void ScrGetShootAtPos(scr_entref_t ref)
{
    float position[3];
    if (ref.classnum || ref.entnum >= ENTITYNUM_WORLD) {
        Scr_ObjectError("getshootatpos requires an entity"); return;
    }
    if (ScrShootAtPosition(&g_entities[ref.entnum], position)) Scr_AddVector(position);
}

/* <entity> canSee( <other> )
 * The same eye-to-centre visibility the native actor perception uses, so a
 * script asking "can I see him" and the native enemy selection cannot
 * disagree. A trace that ends on the target's own entity counts as sight,
 * because the endpoint is inside its bounds. */
static void ScrCanSee(scr_entref_t ref)
{
    if (ref.classnum || ref.entnum >= ENTITYNUM_WORLD) {
        Scr_ObjectError("cansee requires an entity"); return;
    }
    gentity_s *self = &g_entities[ref.entnum];
    gentity_s *other = Scr_GetEntity(0);
    if (!self->r.inuse || !other || !other->r.inuse) { Scr_AddBool(qfalse); return; }
    float eye[3], target[3];
    if (!ScrShootAtPosition(self, eye) || !ScrShootAtPosition(other, target)) {
        Scr_AddBool(qfalse); return;
    }
    trace_t trace; float zero[3] = {0,0,0};
    G_TraceCapsule(&trace, eye, zero, zero, target, self->s.number, self->clipmask);
    Scr_AddBool(!trace.startsolid && !trace.allsolid &&
        (trace.fraction >= 1.0f ||
         (trace.hitType == TRACE_HITTYPE_ENTITY && trace.hitId == other->s.number)));
}

/* <actor> teleport( <origin>, [<angles>] )
 * dog_combat nudges an attacking dog out of a player it would otherwise
 * overlap. Unlike forceteleport this keeps the actor's route and goal: it is
 * a position correction inside one attack, not a respawn. */
static void ActorTeleport(scr_entref_t ref)
{
    codol_actor_lifetime_t *a = ActorMethodReceiver(ref); if (!a) return;
    float origin[3], angles[3];
    Scr_GetVector(0, origin);
    for (int i = 0; i < 3; ++i)
        if (!isfinite(origin[i])) { Scr_ParamError(0, "teleport origin must be finite"); return; }
    if (Scr_GetNumParam() > 1) {
        Scr_GetVector(1, angles);
        for (int i = 0; i < 3; ++i)
            if (!isfinite(angles[i])) { Scr_ParamError(1, "teleport angles must be finite"); return; }
        memcpy(a->entity->r.currentAngles, angles, 12);
        memcpy(a->entity->s.lerp.apos.trBase, angles, 12);
    }
    G_SetOrigin(a->entity, origin);
    memcpy(a->sentient->origin, origin, 12);
    memset(a->physics.velocity, 0, sizeof(a->physics.velocity));
    SV_LinkEntity(a->entity);
}

/* <entity> disconnectpaths() / <entity> connectpaths()
 * T5 Path_DisconnectPaths / Path_ConnectPaths on the map graph: the zm
 * barrier clip cuts its window's negotiation link while the boards stand
 * (_zombiemode_blockers::blocker_init, T5's DISCONNECT_PATHS spawnflag on the
 * clip), zombie_goto_entrance restores it after the tear, the repair loop
 * cuts it again.  Any linked entity may call them (doors, debris). */
static void ScrEntDisconnectPaths(scr_entref_t ref)
{
    if (ref.classnum || ref.entnum >= ENTITYNUM_WORLD) { Scr_ObjectError("disconnectpaths requires an entity"); return; }
    gentity_s *e = &g_entities[ref.entnum];
    if (!e->r.inuse || e->r.absmin[0] > e->r.absmax[0]) { Scr_ObjectError("disconnectpaths requires a linked entity with bounds"); return; }
    int n = CODOL_BotNavDisconnectPaths(ref.entnum, e->r.absmin, e->r.absmax);
    DOG_DIAG("ent %d disconnectpaths: %d links cut inside (%.0f %.0f %.0f)-(%.0f %.0f %.0f) contents 0x%x\n", ref.entnum, n,
        e->r.absmin[0], e->r.absmin[1], e->r.absmin[2], e->r.absmax[0], e->r.absmax[1], e->r.absmax[2], e->r.contents);
}
static void ScrEntConnectPaths(scr_entref_t ref)
{
    if (ref.classnum || ref.entnum >= ENTITYNUM_WORLD) { Scr_ObjectError("connectpaths requires an entity"); return; }
    int n = CODOL_BotNavConnectPaths(ref.entnum);
    DOG_DIAG("ent %d connectpaths: %d links restored\n", ref.entnum, n);
}
static void ActorFinishDamage(scr_entref_t ref);
/* codol_getWalkableWaypoints()
 * The origins of the loaded bot waypoint graph's standable nodes (stand,
 * crouch and negotiation stances, the ones ActorRouteWalkable accepts), for
 * maps\mp\_dogs when the map has no path nodes of its own. */
static void ScrWalkableWaypoints(void)
{
    Scr_MakeArray();
    for (int i = 0, n = CODOL_BotNavCount(); i < n; ++i) {
        const float *p = CODOL_BotNavPoint(i);
        if (!p || !ActorRouteWalkable(CODOL_BotNavStance(i))) continue;
        Scr_AddVector(p);
        Scr_AddArray();
    }
}
extern "C" void CODOL_ActorRegisterSpawnMethods(void);
extern "C" void CODOL_ActorRegisterMethods(void)
{
    Scr_AddMethod("disconnectpaths", ScrEntDisconnectPaths, qfalse);
    Scr_AddMethod("connectpaths", ScrEntConnectPaths, qfalse);
    actorMeleeRange=Cvar_RegisterFloat("ai_meleeRange",64,0,1000,0,"AI melee range");
    actorMeleeWidth=Cvar_RegisterFloat("ai_meleeWidth",20,0,1000,0,"AI melee width");
    actorMeleeHeight=Cvar_RegisterFloat("ai_meleeHeight",10,0,1000,0,"AI melee height");
    Scr_AddMethod("melee",ActorMelee,qfalse);
    CODOL_ActorRegisterSpawnMethods();
    Scr_AddMethod("setenemymodel", ActorSetEnemyModel, qfalse);
    Scr_AddMethod("setentityowner", ActorOwner, qfalse);
    Scr_AddMethod("clearentityowner", ActorClearOwner, qfalse);
    Scr_AddMethod("clearentitytarget", ActorClearTarget, qfalse);
    Scr_AddMethod("forceteleport", ActorForceTeleport, qfalse);
    /* scr_vm_main.c registers the retained player-only geteye/getvelocity
     * first and Scr_AddMethod refuses a duplicate name, so these actor-aware
     * wrappers (which fall through to the retained implementation for a
     * non-actor receiver) silently lost: "entity N is not a player" from
     * dog_pain.gsc. Replace the registration. */
    Scr_RemoveMethod("geteye");
    Scr_RemoveMethod("getvelocity");
    Scr_AddMethod("geteye", ActorGetEye, qfalse);
    Scr_AddMethod("getvelocity", ActorVelocity, qfalse);
    Scr_AddMethod("settalktospecies", ActorTalkSpecies, qfalse);
    Scr_AddMethod("setengagementmindist", ActorEngagementMin, qfalse);
    Scr_AddMethod("setengagementmaxdist", ActorEngagementMax, qfalse);
    Scr_AddMethod("animmode", ActorAnimationMode, qfalse);
    Scr_AddMethod("setgoalpos", ActorSetGoalPosition, qfalse);
    Scr_AddMethod("orientmode", ActorOrientMode, qfalse);
    Scr_AddMethod("setgoalnode", CODOL_ActorSetGoalNode, qfalse);
    Scr_AddMethod("setanimstate", ActorSetAnimationState, qfalse);
    Scr_AddMethod("setaimanimweights", ActorSetAimAnimationWeights, qfalse);
    Scr_AddMethod("getdeltaturnyaw", ActorDeltaTurnYaw, qfalse);
    /* Engine surface the ported dog scripts need; see the block above. */
    Scr_AddFunction("isai",ScrActorIsAI,qfalse);
    Scr_AddMethod("setflashbanged",ActorSetFlashBanged,qfalse);
    Scr_AddMethod("getflashbangedstrength",ActorGetFlashBangedStrength,qfalse);
    Scr_AddMethod("getshootatpos",ScrGetShootAtPos,qfalse);
    Scr_AddMethod("cansee",ScrCanSee,qfalse);
    Scr_AddMethod("teleport",ActorTeleport,qfalse);
    Scr_AddMethod("finishactordamage",ActorFinishDamage,qfalse);
    Scr_AddFunction("codol_getwalkablewaypoints",ScrWalkableWaypoints,qfalse);
}

static int ActorScriptIsBound(const codol_actor_lifetime_t *a, int function)
{
    const codol_actor_script_table_t *s = &a->scripts;
    return function && (function == s->stop || function == s->move ||
        function == s->combat || function == s->death || function == s->pain ||
        function == s->flashed || function == s->turn || function == s->jump);
}

int CODOL_ActorInitScripts(gentity_s *entity, const codol_actor_script_table_t *table)
{
    codol_actor_lifetime_t *a = CODOL_ActorForEntity(entity);
    if (!a || !a->typeStarted || !a->species || a->scriptsStarted || !table ||
        !table->init || !table->stop || !table->move || !table->combat ||
        !table->death || !table->pain || !table->flashed || !table->turn ||
        !table->jump) return 0;
    unsigned generation = a->generation;
    a->scripts = *table;
    a->scriptsStarted = 1;
    /* T5 Actor_InitAnimScript executes species init separately from the
     * replaceable movement/combat script. Its background child threads belong
     * to the entity and must not be killed on every movement transition. */
    short thread = Scr_ExecEntThread(entity, table->init, 0);
    Scr_FreeThread(thread);
    a = CODOL_ActorForEntity(entity);
    return a && a->generation == generation && a->scriptsStarted;
}

void CODOL_ActorStopScript(gentity_s *entity)
{
    codol_actor_lifetime_t *a = CODOL_ActorForEntity(entity);
    if (!a) return;
    short thread = a->animThread;
    a->animThread = 0;
    a->animFunction = 0;
    /* Clear ownership before notifying: an endon or callback may free self. */
    if (thread) {
        Scr_Notify(entity, scr_const.killanimscript, 0);
        Scr_FreeThread(thread);
    }
}

int CODOL_ActorSwitchScript(gentity_s *entity, int function, int moveMode, int animMode)
{
    codol_actor_lifetime_t *a = CODOL_ActorForEntity(entity);
    if (!a || !a->scriptsStarted || a->switching ||
        !ActorScriptIsBound(a, function) || gScrVmPub.function_count ||
        gScrVmPub.inparamcount || gScrVmPub.outparamcount ||
        gScrVmPub.top != gScrVmPub.stack) return 0;
    unsigned generation = a->generation;
    if (a->animFunction == function && a->animThread &&
        Scr_GetObjectType((unsigned short)a->animThread)==VAR_DEAD_THREAD) {
        Scr_FreeThread(a->animThread);
        a->animThread=0;a->animFunction=0;
    }
    if (a->animFunction == function) {
        a->animMode = animMode;
        if (a->moveMode != moveMode) {
            a->moveMode = moveMode;
            /* Original dog_move listens to this event; do not restart it
             * merely because the native movement intent changed. */
            unsigned name = SL_GetString("movemode", 0);
            Scr_Notify(entity, (unsigned short)name, 0);
            SL_RemoveRefToString(name);
        }
        a = CODOL_ActorForEntity(entity);
        return a && a->generation == generation;
    }
    if (a->animFunction && !a->safeToChangeScript) return 1;
    a->switching = 1;
    /* T5 Actor_SetAnimScript processes the canceled script at the previous
     * script time, before executing the replacement. This is an AI-frame
     * operation, not a nested call from a script builtin. */
    Scr_DecTime();
    CODOL_ActorStopScript(entity);
    Scr_RunCurrentThreads();
    a = CODOL_ActorForEntity(entity);
    if (!a || a->generation != generation) {
        Scr_IncTime();
        return 0;
    }
    DOG_DIAG("ent %d animscript -> %s (moveMode %d animMode %d)\n", entity->s.number,
        function==a->scripts.move?"dog_move":function==a->scripts.stop?"dog_stop":
        function==a->scripts.combat?"dog_combat":function==a->scripts.pain?"dog_pain":
        function==a->scripts.death?"dog_death":function==a->scripts.jump?"traverse (jump)":
        function==a->scripts.flashed?"dog_flashed":function==a->scripts.turn?"dog_turn":"other", moveMode, animMode);
    a->animFunction = function;
    a->scriptOrient = 0; // T5 clears prior script orientation on replacement.
    a->scriptAnimMode = 0;
    a->moveMode = moveMode;
    a->animMode = animMode;
    /* Parameters are pushed last-first (Scr_PlayerKilled).  Only the
     * negotiation entry carries any: main(begin_origin, begin_angles,
     * end_origin, animscript). */
    unsigned numParams = 0;
    if (s_switchParams) {
        Scr_AddString(s_switchParams->script);
        Scr_AddVector(s_switchParams->end);
        Scr_AddVector(s_switchParams->angles);
        Scr_AddVector(s_switchParams->begin);
        numParams = 4;
        s_switchParams = NULL;
    }
    short thread = Scr_ExecEntThread(entity, function, numParams);
    a = CODOL_ActorForEntity(entity);
    if (a && a->generation == generation) {
        a->animThread = thread; // keep reference until replacement or free
        a->switching = 0;
    } else if (thread) {
        Scr_FreeThread(thread);
    }
    /* Shared entity frame still owns DObj ticking; do not tick it twice. */
    Scr_IncTime();
    a = CODOL_ActorForEntity(entity);
    return a && a->generation == generation && a->animFunction == function;
}

int CODOL_ActorScriptModes(gentity_s *entity, int *moveMode, int *animMode)
{
    codol_actor_lifetime_t *a = CODOL_ActorForEntity(entity);
    if (!a || !a->scriptsStarted || !moveMode || !animMode) return 0;
    *moveMode = a->moveMode;
    *animMode = a->animMode;
    return 1;
}

extern "C" void G_DObjUpdate(gentity_s *entity);
XAnimTree_s *CODOL_ActorOwnedTree(gentity_s *entity)
{
    codol_actor_lifetime_t *a=CODOL_ActorForEntity(entity);
    if(a && a->tree.anims)return &a->tree;
    for(unsigned i=0;i<8;++i)if(corpses[i].entity==entity &&
        entity->r.inuse && corpses[i].generation==CODOL_ACTOR_INCARNATION(entity->useCount))return &corpses[i].tree;
    /* The one other server-animated entity: an RC-XD whose wheel clips are
     * driven natively (codol_vehicle_wheel_anim.h). G_DObjUpdate asks here. */
    return CODOL_VehicleWheelAnimTree(entity);
}
#define ANIM_WARN(...) Com_PrintWarning(CON_CHANNEL_SERVER, "CoDOL actor: animation: " __VA_ARGS__)
int CODOL_ActorPrepareAnimation(gentity_s *entity)
{
    codol_actor_lifetime_t *a=CODOL_ActorForEntity(entity);
    if (!a || !a->typeStarted) { ANIM_WARN("ent %d is not a started actor\n", entity->s.number); return 0; }
    if (!a->species) { ANIM_WARN("actor ent %d: aitype main never set self.type to a known species\n", entity->s.number); return 0; }
    const codol_actor_species_t *row=a->species;
    if (!entity->model) { ANIM_WARN("actor ent %d has no model (character script setModel failed?)\n", entity->s.number); return 0; }
    if (entity->s.eType!=ET_ACTOR || a->tree.anims) { ANIM_WARN("actor ent %d: eType %d / tree already owned\n", entity->s.number, entity->s.eType); return 0; }
    unsigned serverTree, treeCount=CODOL_ServerAnimTreeCount();
    for(serverTree=1;serverTree<=treeCount;++serverTree) {
        const char *name=CODOL_ServerAnimTreeName(serverTree);
        if(name && !strcmp(name,row->animtree))break;
    }
    if(serverTree>treeCount) {
        /* The registry only holds trees a compiled script declared with
         * #using_animtree; maps/mp/_dogs.gsc declares "dog" and the zm script
         * set must declare this species' own tree for the same reason.
         * Name every slot: a registered-but-unnamed slot means the snapshot
         * did not run, which is a different defect from no declaration. */
        char dump[512]; unsigned i, used=0;
        dump[0]=0;
        for(i=1;i<=treeCount && used+72<sizeof(dump);++i) {
            const char *name=CODOL_ServerAnimTreeName(i);
            used+=(unsigned)snprintf(dump+used,sizeof(dump)-used,"%s%u='%s'%s",
                used?" ":"",i,name?name:"<unnamed>",
                Scr_GetAnims(i)?"":"(no xanim)");
        }
        ANIM_WARN("no server animtree named \"%s\" is registered for species '%s' (%u registered: %s; a loaded script must declare #using_animtree(\"%s\") so animtrees/%s.atr mounts)\n",
                  row->animtree, row->name, treeCount, treeCount?dump:"none",
                  row->animtree, row->animtree);
        return 0;
    }
    XAnim_s *anims=Scr_GetAnims(serverTree);
    if(!anims) { ANIM_WARN("server animtree \"%s\" (%u) has no XAnim set\n", row->animtree, serverTree); return 0; }
    // Retained XAnimCreateTree initializes exactly this 8-byte representation.
    // Actor owns stable storage; native XAnimClearTree releases node records.
    a->tree.anims=anims;
    a->tree.children=0;
    a->tree.pad=0;
    a->serverTree=serverTree;
    /* C1 0x4083f0 registers the client's five actor composition trees at
     * bgs+0x90174, one per serverinfo-2482 bit; 0x428ba6 reads entityState
     * +0x59 as the index into it. The species row carries the index its
     * animtree is registered at (dog = 1, the verified C1 common_dog slot). */
    entity->s.lerp.u.actor.treeSelector=(int)row->treeSelector;
    G_DObjUpdate(entity); // native callsite supplies this owned tree to create
    DObj *obj=Com_GetServerDObj(entity->s.number);
    if(!obj || DObjGetTree(obj)!=&a->tree) {
        ANIM_WARN("actor ent %d: server DObj %s the owned '%s' tree (model %u)\n",
                  entity->s.number, obj?"does not use":"was not created for",
                  row->animtree, entity->model);
        return 0;
    }
    return 1;
}
int CODOL_ActorFinishInitialization(gentity_s *entity, unsigned treeSelector)
{
    codol_actor_lifetime_t *a=CODOL_ActorForEntity(entity);
    if(!a || !a->typeStarted || !a->scriptsStarted || a->initialized ||
       !a->species || treeSelector!=a->species->treeSelector ||
       entity->s.eType!=ET_ACTOR || !entity->model || !a->tree.anims)return 0;
    DObj *obj=Com_GetServerDObj(entity->s.number);
    if(!obj || obj->entnum!=entity->s.number+1 || DObjGetTree(obj)!=&a->tree)return 0;
    a->initialized=1;
    return 1;
}

int CODOL_ActorCaptureSources(codol_dog_anim_capture_source_t *out,
                            unsigned capacity, unsigned *count)
{
    codol_dog_anim_capture_source_t sources[CODOL_MAX_ACTOR_SLOTS];
    unsigned n=0;
    if (!count || (!out && capacity)) return 0;
    *count=0;
    for (unsigned i=0; i<CODOL_MAX_ACTOR_SLOTS; ++i) {
        codol_actor_lifetime_t *a=&actors[i];
        if (!a->allocated || !a->initialized) continue;
        if (CODOL_ActorForEntity(a->entity) != a) return 0;
        DObj *obj=Com_GetServerDObj(a->entity->s.number);
        if (!obj || obj->entnum != a->entity->s.number+1 || !DObjGetTree(obj)) return 0;
        sources[n].entity=(unsigned)a->entity->s.number;
        sources[n].generation=a->generation;
        sources[n].tree=DObjGetTree(obj);
        ++n;
    }
    if (n>capacity) return 0;
    if (n) memcpy(out,sources,n*sizeof(*out));
    /* Wheel-animated vehicles ride the same pose capture and journal delivery
     * (C1 plays their commands through the same executor 0x443e90). They take
     * only the capacity actors leave; one that does not fit is simply not
     * visible to the animation channel this frame. */
    n+=CODOL_VehicleWheelAnimCaptureSources(out+n,capacity-n);
    *count=n;
    return 1;
}

int CODOL_ActorArchivePose(int frame, unsigned time)
{
    codol_dog_anim_capture_source_t sources[CODOL_MAX_ACTOR_SLOTS];
    unsigned count;
    if (!CODOL_ActorCaptureSources(sources, CODOL_MAX_ACTOR_SLOTS, &count))
        return 0;
    return CODOL_DogAnimArchiveStore(frame, time, sources, count);
}

static void ActorRecordDamage(gentity_s *entity,gentity_s *attacker,const float *direction)
{
    codol_actor_lifetime_t *a=CODOL_ActorForEntity(entity);if(!a)return;
    float x=direction?-direction[0]:0,y=direction?-direction[1]:0;
    if(!direction && attacker){x=attacker->r.currentOrigin[0]-entity->r.currentOrigin[0];y=attacker->r.currentOrigin[1]-entity->r.currentOrigin[1];}
    float yaw=(x!=0 || y!=0)?atan2f(y,x)*57.295779513f:entity->r.currentAngles[1];
    a->damageYaw=fmodf(yaw-entity->r.currentAngles[1]+360,360);
    if(attacker && attacker!=entity)CODOL_ActorSetEnemy(entity,attacker);
}
extern "C" void CODOL_ActorPain(gentity_s *entity,gentity_s *attacker,int damage,
    const float *point,int meansOfDeath,const float *direction,hitLocation_t location,int weapon)
{
    (void)damage;(void)point;(void)meansOfDeath;(void)location;(void)weapon;
    ActorRecordDamage(entity,attacker,direction);
    codol_actor_lifetime_t *a=CODOL_ActorForEntity(entity);
    if(a && entity->health>0)a->painPending=1;
}
/* ---------------------------------------------------------------------------
 * Script damage and death callbacks for actors (T5 MP, OpenBLOPS
 * Game/Server/game_mp/g_combat_mp.cpp G_Damage actor arm,
 * g_scr_main_mp.cpp Scr_ActorDamage / Scr_ActorKilled and
 * game/actor_script_cmd.cpp ActorCmd_finishActorDamage).
 *
 * T5 hands every damage an actor takes to
 * maps/mp/gametypes/_callbacksetup::CodeCallback_ActorDamage, and the actor
 * only loses health when script answers with finishActorDamage; that is where
 * _globallogic_actor::Callback_ActorDamage refuses friendly fire, damage from
 * the dogs' own owner and between dogs of one owner, and draws the attacker's
 * hit marker.  The retained G_Damage applied actor damage natively with no
 * such gate, so a teammate - or the owner himself - could shoot the dogs dead.
 * The dispatcher mirrors CODOL_VehicleDamageCallback: finishActorDamage
 * re-enters G_Damage under a gate, so health, the "damage"/"death" notifies
 * and the pain/die handlers stay the retained ones.  A script tree without the
 * callback (handle 0) keeps the native path unchanged.
 *
 * Before the callback T5 scales the damage by the weapon's hit-location
 * multiplier unless it is a melee hit, and never passes less than 1.  The
 * multiplier here is C1's (G_GetWeaponHitLocationMultiplier 0x521010, the
 * same arithmetic _g_combat_mp.asm G_DamageClient_50 uses for players).
 * ------------------------------------------------------------------------ */
extern "C" int __cdecl G_MeansOfDeathFromScriptParam(int paramIndex);
extern "C" int __cdecl G_GetHitLocationIndexFromString(unsigned int constString);
extern "C" void __cdecl G_Damage(gentity_s *targ, gentity_s *inflictor, gentity_s *attacker,
    const float *dir, const float *point, int damage, int dflags, int mod, int weapon,
    int hitLoc, unsigned int modelIndex, unsigned int partName, int timeOffset);
extern "C" float g_fHitLocDamageMult[];
static int actorDamageHandle, actorKilledHandle, actorDamageFinishing;
/* src/g_combat_mp.cpp modNames[7] is MOD_MELEE (the C enum is not built). */
static const int ACTOR_MOD_MELEE=7;
extern "C" void CODOL_ActorDamage_LoadCallbacks(void)
{
    actorDamageHandle=Scr_GetFunctionHandle("maps/mp/gametypes/_callbacksetup","CodeCallback_ActorDamage");
    actorKilledHandle=Scr_GetFunctionHandle("maps/mp/gametypes/_callbacksetup","CodeCallback_ActorKilled");
    actorDamageFinishing=0;
}
static void ActorPushWeapon(int weapon)
{
    WeaponDef *def=weapon>0?BG_GetWeaponDef(weapon):NULL;
    Scr_AddString(def?def->szInternalName:"none");
}
static void ActorPushMeansOfDeath(int mod)
{
    if(mod>=0 && mod<NATIVE_DAMAGE_MOD_COUNT && modNames[mod])Scr_AddConstString(*modNames[mod]);
    else Scr_AddString("badMOD");
}
static void ActorPushHitLocation(int hitLoc)
{
    Scr_AddConstString(G_GetHitLocationString((hitLocation_t)(hitLoc>=0 && hitLoc<HITLOC_NUM?hitLoc:HITLOC_NONE)));
}
static float ActorHitLocationMultiplier(int hitLoc,int weapon)
{
    if(hitLoc<0 || hitLoc>=HITLOC_NUM)return 1.0f;
    WeaponDef *def=weapon>0?BG_GetWeaponDef(weapon):NULL;
    if(def && def->weapType==WEAPTYPE_BULLET && (int)def->weapClass!=7)
        return def->locationDamageMultipliers[hitLoc]*g_fHitLocDamageMult[hitLoc];
    return g_fHitLocDamageMult[hitLoc];
}
extern "C" int CODOL_ActorDamageCallback(gentity_s *targ,gentity_s *inflictor,gentity_s *attacker,
    const float *dir,const float *point,int damage,int dflags,int mod,int weapon,
    int hitLoc,unsigned int modelIndex,unsigned int partName,int timeOffset)
{
    (void)modelIndex;(void)partName;
    if(!targ || targ->client || !actorDamageHandle || actorDamageFinishing)return 0;
    codol_actor_lifetime_t *a=CODOL_ActorForEntity(targ);
    if(!a || a->deathTime>=0 || targ->health<=0)return 0;
    if(mod!=ACTOR_MOD_MELEE)damage=(int)(ActorHitLocationMultiplier(hitLoc,weapon)*(float)damage);
    if(damage<=0)damage=1;
    /* Scr_ActorDamage pushes last-first: (eInflictor, eAttacker, iDamage,
     * iDFlags, sMeansOfDeath, sWeapon, vPoint, vDir, sHitLoc, timeOffset). */
    Scr_AddInt(timeOffset);
    ActorPushHitLocation(hitLoc);
    Scr_AddVector(dir?dir:vec3_origin);
    Scr_AddVector(point?point:vec3_origin);
    ActorPushWeapon(weapon);
    ActorPushMeansOfDeath(mod);
    Scr_AddInt(dflags);
    Scr_AddInt(damage);
    if(attacker)Scr_AddEntity(attacker);else Scr_AddUndefined();
    if(inflictor)Scr_AddEntity(inflictor);else Scr_AddUndefined();
    short thread=Scr_ExecEntThread(targ,actorDamageHandle,10);
    Scr_FreeThread(thread);
    return 1;
}
/* <actor> finishActorDamage( eInflictor, eAttacker, iDamage, iDFlags,
 *     sMeansOfDeath, sWeapon, vPoint, vDir, sHitLoc, psOffsetTime )
 * T5 ActorCmd_finishActorDamage: world defaults for an undefined inflictor or
 * attacker, damage <= 0 does nothing, damage to a dead actor is an error. */
static void ActorFinishDamage(scr_entref_t ref)
{
    codol_actor_lifetime_t *a=ActorMethodReceiver(ref);if(!a)return;
    if(Scr_GetNumParam()!=10){Scr_Error("finishactordamage requires 10 arguments");return;}
    int damage=Scr_GetInt(2);
    if(damage<=0)return;
    if(a->deathTime>=0 || a->entity->health<=0){Scr_Error("Trying to do damage to a actor that is already dead");return;}
    gentity_s *inflictor=&g_entities[ENTITYNUM_WORLD],*attacker=&g_entities[ENTITYNUM_WORLD];
    if(Scr_GetType(0)==VAR_POINTER && Scr_GetPointerType(0)==VAR_ENTITY)inflictor=Scr_GetEntity(0);
    if(Scr_GetType(1)==VAR_POINTER && Scr_GetPointerType(1)==VAR_ENTITY)attacker=Scr_GetEntity(1);
    int dflags=Scr_GetInt(3);
    int mod=G_MeansOfDeathFromScriptParam(4);
    int weapon=G_GetWeaponIndexForName(Scr_GetString(5));
    if(!weapon && (unsigned short)Scr_GetConstString(5)!=scr_const.none) {
        Scr_Error(va("weapon [%s] has not been precached",Scr_GetString(5)));return;
    }
    float point[3]={0,0,0},dir[3]={0,0,0};
    const float *pointArg=NULL;
    if(Scr_GetType(6)!=VAR_UNDEFINED){Scr_GetVector(6,point);pointArg=point;}
    if(Scr_GetType(7)!=VAR_UNDEFINED)Scr_GetVector(7,dir);
    int hitLoc=G_GetHitLocationIndexFromString((unsigned short)Scr_GetConstString(8));
    int timeOffset=Scr_GetInt(9);
    /* The retained G_Damage normalizes dir whenever it runs its tail; a zero
     * direction reads as straight up there, as T5 doDamage substitutes (see
     * CODOL_Scr_DoDamage for the null-direction crash this avoids). */
    if(dir[0]==0 && dir[1]==0 && dir[2]==0)dir[2]=1;
    actorDamageFinishing=1;
    G_Damage(a->entity,inflictor,attacker,dir,pointArg,damage,dflags,mod,weapon,hitLoc,0,0,timeOffset);
    actorDamageFinishing=0;
}
/* T5 MP Actor_Die -> Scr_ActorKilled: (eInflictor, eAttacker, iDamage,
 * sMeansOfDeath, sWeapon, vDir, sHitLoc, psOffsetTime). */
static void ActorKilledCallback(gentity_s *entity,gentity_s *inflictor,gentity_s *attacker,
    int damage,int mod,int weapon,const float *dir,int hitLoc,int timeOffset)
{
    if(!actorKilledHandle)return;
    Scr_AddInt(timeOffset);
    ActorPushHitLocation(hitLoc);
    Scr_AddVector(dir?dir:vec3_origin);
    ActorPushWeapon(weapon);
    ActorPushMeansOfDeath(mod);
    Scr_AddInt(damage);
    if(attacker)Scr_AddEntity(attacker);else Scr_AddUndefined();
    if(inflictor)Scr_AddEntity(inflictor);else Scr_AddUndefined();
    short thread=Scr_ExecEntThread(entity,actorKilledHandle,8);
    Scr_FreeThread(thread);
}
extern "C" void CODOL_ActorDie(gentity_s *entity,gentity_s *inflictor,gentity_s *attacker,
    int damage,int meansOfDeath,int weapon,const float *direction,hitLocation_t location,int timeOffset)
{
    ActorRecordDamage(entity,attacker,direction);
    codol_actor_lifetime_t *a=CODOL_ActorForEntity(entity);if(!a || a->deathTime>=0)return;
    a->deathTime=level.time;a->painPending=0;a->safeToChangeScript=1;
    entity->takedamage=0;
    CODOL_DogCombatRelease(entity);
    // Generic G_Damage already sent death. Do not send a duplicate reward event.
    ActorKilledCallback(entity,inflictor,attacker,damage,meansOfDeath,weapon,direction,(int)location,timeOffset);
}

static int ActorBecomeCorpse(gentity_s *entity)
{
    codol_actor_lifetime_t *a=CODOL_ActorForEntity(entity);
    if(!a || !a->tree.anims)return 0;
    /* Captured before CODOL_ActorRelease below invalidates the record: the
     * corpse keeps composing out of the same client actor tree the live
     * actor used, which is a species column, not always the dog's. */
    unsigned treeSelector=a->species?a->species->treeSelector:1u;
    unsigned index=0;
    for(unsigned i=0;i<8;++i) {
        if(!corpses[i].entity){index=i;break;}
        if(corpses[i].time<corpses[index].time)index=i;
    }
    if(corpses[index].entity)G_FreeEntity(corpses[index].entity);
    actor_corpse_owner pending={};
    actor_corpse_owner *body=&pending;
    body->entity=entity;body->generation=CODOL_ACTOR_INCARNATION(entity->useCount);body->time=level.time;
    body->tree=a->tree;body->physics=a->physics;
    memset(&a->tree,0,sizeof(a->tree)); // transfer nodes, do not clear them
    DObj *obj=Com_GetServerDObj(entity->s.number);
    if(obj)obj->tree=NULL;
    CODOL_ActorRelease(entity);
    corpses[index]=pending;
    body=&corpses[index];
    if(obj)obj->tree=&body->tree;
    entity->s.eType=ET_ACTOR_CORPSE;
    entity->s.lerp.u.actor.actorSlot=(int)index;
    entity->s.lerp.u.actor.treeSelector=(int)treeSelector;
    entity->r.contents=CONTENTS_CORPSE;
    entity->clipmask=0x820011;
    entity->takedamage=0;
    // C1 46C4DF -> 42A5C0 copies the previous actor composition into the
    // corpse slot and swaps animation trees when this same entity changes type.
    Scr_FreeEntityNum(entity->s.number,0);
    G_DObjUpdate(entity);
    SV_LinkEntity(entity);
    return 1;
}
int CODOL_ActorRunCorpseFrame(gentity_s *entity)
{
    for(unsigned i=0;i<8;++i)if(corpses[i].entity==entity &&
       corpses[i].generation==CODOL_ACTOR_INCARNATION(entity->useCount)) {
        float dt=(level.time-level.previousTime)*.001f,zero[3]={0,0,0};
        if(g_gravity && dt>0 && dt<=.25f)
            CODOL_ActorPhysicsMove(entity,&corpses[i].physics,zero,dt,g_gravity->value,0);
        return 1;
    }
    return 0;
}

void CODOL_ActorForget(gentity_s *entity)
{
    for(unsigned i=0;i<8;++i)if(corpses[i].entity==entity) {
        DObj *obj=Com_GetServerDObj(entity->s.number);
        if(obj && obj->tree==&corpses[i].tree)obj->tree=NULL;
        if(corpses[i].tree.anims)XAnimClearTree(&corpses[i].tree);
        memset(&corpses[i],0,sizeof(corpses[i]));
    }
    /* Free hooks run while the entity is still allocated, but scan identity
     * directly so teardown also works if sentient's index was already cleared. */
    for (unsigned i=0; i<CODOL_MAX_ACTOR_SLOTS; ++i)
        if (actors[i].allocated && actors[i].entity==entity) {
            short thread = actors[i].animThread;
            /* Child threads of the current animscript (dog_stop::lookAtTarget
             * -> dog_shared::trackLoop) end on "killanimscript". This runs
             * before Scr_FreeEntity / the corpse's Scr_FreeEntityNum, so a
             * deleted or corpse-converted dog cannot leave a thread that
             * wakes on an entity whose script fields are gone ("undefined is
             * not a field object" at self.a in trackLoop). */
            if (actors[i].scriptsStarted && entity->r.inuse)
                Scr_Notify(entity, scr_const.killanimscript, 0);
            CODOL_DogCombatRelease(entity);
            DObj *obj=Com_GetServerDObj(entity->s.number);
            if(obj && obj->tree==&actors[i].tree)obj->tree=NULL;
            if(actors[i].tree.anims)XAnimClearTree(&actors[i].tree);
            Scr_SetString(&actors[i].weaponName,0);
            memset(&actors[i],0,sizeof(actors[i]));
            // G_FreeEntity owns termination of entity scripts. Drop only the
            // extra actor-held reference here; no callbacks during teardown.
            if (thread) Scr_FreeThread(thread);
        }
}
void CODOL_ActorRelease(gentity_s *entity)
{
    codol_actor_lifetime_t *a=CODOL_ActorForEntity(entity);
    if (!a) return;
    codol_sentient_t *s=a->sentient;
    CODOL_ActorForget(entity);
    CODOL_Sentient_Free(s);
}
void CODOL_ActorLifetimeReset(void) { memset(actors,0,sizeof(actors));memset(corpses,0,sizeof(corpses));CODOL_ActorDeliveryReset(); }
#endif
