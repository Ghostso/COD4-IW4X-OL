/* Native actor allocation and script/type lifetime, staged for integration.
 * No GSC spawnactor registration until AI initialization is connected. */
#ifndef CODOL_ACTOR_LIFECYCLE_H
#define CODOL_ACTOR_LIFECYCLE_H
#ifdef CODOL_SERVER
#include "codol_sentient.h"
#include "codol_dog_animation.h"
struct codol_actor_lifetime_s;
typedef struct codol_actor_lifetime_s codol_actor_lifetime_t;
extern "C" {
/* Entity must be a freshly allocated live non-client, not a spawner. Claims
 * an actor slot and sentient together, without evicting unrelated sentients.
 * Capacity refusal does not modify the entity or another live actor. */
codol_actor_lifetime_t *CODOL_ActorAllocate(gentity_s *entity, int team);
codol_actor_lifetime_t *CODOL_ActorForEntity(gentity_s *entity);
/* Requires a preloaded original aitype main function handle. Calls the actual
 * entity script; revalidates after it runs because script may delete self.
 * No thread id is retained: Scr_FreeThread releases only the caller reference,
 * and ordinary entity script lifetime owns a yielding thread. */
/* Native perception selects enemy; GSC enemy is read-only. */
gentity_s *CODOL_ActorEnemy(gentity_s *entity);
unsigned CODOL_ActorEnemyModel(gentity_s *entity);
void CODOL_ActorInheritSight(gentity_s *entity);
int CODOL_ActorSetEnemy(gentity_s *entity, gentity_s *enemy);
int CODOL_ActorSetGoal(gentity_s *entity, const float *goal);
/* 0 unavailable/blocked, 1 route direction, 2 inside authored goal volume. */
int CODOL_ActorGoalDirection(gentity_s *entity, float *direction);
int CODOL_ActorMoveDelta(gentity_s *entity, const float *delta);
/* AI_ANIM_MOVE_CODE root-motion consumer, once after animation advancement.
 * Native capsule gravity/slide/step are applied; traversal remains separate. */
int CODOL_ActorAdvanceGoalAnimation(gentity_s *entity, int time, int useGoalWeight);
int CODOL_ActorRunCorpseFrame(gentity_s *entity);
int CODOL_ActorRunFrame(gentity_s *entity);
int CODOL_ActorRunTypeMain(gentity_s *entity, int mainHandle);
/* Original T5 animscript entrypoints, resolved during map script loading.
 * No numeric T5 function/animation indices are copied to C1. The native AI
 * selects a descriptor; these are retained VM code handles for this map only. */
typedef struct {
    int init, stop, move, combat, death, pain, flashed, turn, jump;
} codol_actor_script_table_t;
int CODOL_ActorInitScripts(gentity_s *, const codol_actor_script_table_t *);
/* Call only in the native AI phase with an empty VM operand stack, never from
 * a GSC builtin: T5 transitions run the pending script queue before entry.
 * The caller supplies actual native move/animation modes, not C1 offsets. */
int CODOL_ActorSwitchScript(gentity_s *, int function, int moveMode, int animMode);
void CODOL_ActorStopScript(gentity_s *);
int CODOL_ActorScriptModes(gentity_s *, int *moveMode, int *animMode);
/* Called only after native AI initialization and selected DObj tree creation.
 * Enables capture from that real tree, never an invented idle pose. */
/* Bind real dog tree after aitype model creation, before animscript init. */
struct XAnimTree_s *CODOL_ActorOwnedTree(gentity_s *entity);
int CODOL_ActorPrepareAnimation(gentity_s *entity);
int CODOL_ActorFinishInitialization(gentity_s *entity, unsigned treeSelector);
int CODOL_ActorCaptureSources(codol_dog_anim_capture_source_t *out,
                             unsigned capacity, unsigned *count);
/* Called after the existing engine DObj tick, once per archive frame. */
int CODOL_ActorArchivePose(int frame, unsigned time);
/* Sentient_Free must call Forget before returning the slot to its allocator.
 * Forget owns neither the entity nor its DObj: G_FreeEntity releases those. */
void CODOL_ActorForget(gentity_s *entity);
void CODOL_ActorRelease(gentity_s *entity);
/* Same reset epoch as Sentient_ResetAll; do not release old EntHandles after
 * the shared handle registry has already been reset. */
void CODOL_ActorLifetimeReset(void);
}
#endif
#endif
