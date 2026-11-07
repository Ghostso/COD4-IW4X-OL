#ifndef CODOL_ACTOR_ANIM_JOURNAL_H
#define CODOL_ACTOR_ANIM_JOURNAL_H
#include "codol_animcmd.h"
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
#pragma pack(push, 8)

/* Actor animation delivery, not actor behavior. No callback performs gameplay
 * or substitutes for XAnim. All inputs are already captured native state. */
#define CODOL_ACTOR_ANIM_SNAPSHOT_LIMIT 1024
#define CODOL_ACTOR_ANIM_ARCHIVES 1200
/* An actor's incarnation, as published on the animation channel.
 *
 * gentity_s::useCount counts how many times an entity slot has been FREED:
 * src/g_main_mp.cpp:381 (`gEnt->useCount = useCount + 1` in G_FreeEntity) is
 * its only writer, so an entity sitting in a slot that has never been
 * recycled carries useCount 0. Zero is also the "no incarnation" sentinel
 * that the journal (event->generation), the live pose capture
 * (CODOL_DogAnimCapture) and the pose archive (CODOL_DogAnimArchiveFind) all
 * test, so such an actor can never be addressed on the animation channel.
 *
 * MEASURED 2026-09-20, zm_prototype_sh: zm spawns its zombies into virgin
 * slots (575, 576, 577 ... allocated in ascending order because nothing had
 * been freed yet), every one of them useCount 0. Every setanimknoball() on
 * them was refused with "no incarnation", and because one bad source fails
 * the WHOLE recipient capture, no actor in the match animated at all --
 * "pose capture: bad source (ent 576 gen 0 ...)". The multiplayer dog never
 * hit this only because mp entity churn hands it a recycled slot.
 *
 * The incarnation is therefore 1-based: incarnation = useCount + 1. Every
 * producer of a published generation, and every comparison of a published
 * generation against a live entity, goes through this macro, so 0 keeps
 * meaning "absent" while a first-use entity stays addressable. Reuse
 * counters that never reach the animation channel (a->enemyGeneration, the
 * spawn-path and script-path reuse guards, the world-weapon/vehicle/bot
 * records) keep comparing raw useCount: they only ever test equality between
 * two raw reads, which 0 does not break. */
#define CODOL_ACTOR_INCARNATION(useCount) ((uint32_t)(useCount) + 1u)
typedef struct {
    codol_animcmd_t command;
    uint32_t generation; /* nonzero incarnation of the actor entity */
} codol_actor_anim_event_t;
typedef struct {
    uint64_t end;         /* exclusive journal serial */
    uint32_t epoch;       /* map lifetime, invalid after Reset */
    uint32_t time;        /* source world time, before killcam delta */
} codol_actor_anim_cut_t;
/* Return 1 only when this captured snapshot contains this entity incarnation,
 * 0 when absent/different, -1 for missing capture metadata. Never inspect live
 * g_entities while preparing a historical snapshot. */
typedef int (*codol_actor_anim_visible_t)(unsigned entity,uint32_t generation,
                                        void *capturedContext);
void CODOL_ActorAnimJournalReset(void);
/* Why the last delivery step refused. Every zero return on the delivery path
 * (capture, archive, bootstrap, journal, prepare) sets it through
 * CODOL_ActorDeliveryFail, which formats the reason and returns 0 so a
 * `return CODOL_ActorDeliveryFail(...)` replaces a silent `return 0`. The
 * frame builder prints it once per distinct reason and drops only the
 * animation commands of that frame, never the whole snapshot. */
extern const char *codol_actor_delivery_failure;
int CODOL_ActorDeliveryFail(const char *format,...);
/* Publish one immutable, atomic, same-time animation transaction. Tree indices
 * and goal weights must already have been resolved by the animation producer. */
int CODOL_ActorAnimJournalAppend(const codol_actor_anim_event_t *,unsigned count);
/* Seal the producer phase through time. No subsequently appended transaction
 * may have time <= this cut: C1 has already advanced those time watermarks. */
int CODOL_ActorAnimJournalCut(uint32_t time,codol_actor_anim_cut_t *);
int CODOL_ActorAnimArchive(int archivedFrame,uint32_t time);
int CODOL_ActorAnimArchiveCut(int archivedFrame,uint32_t time,codol_actor_anim_cut_t *);
void CODOL_ActorAnimClientClear(unsigned client);
/* timeline changes on a live/replay transition or rewind, not every archive
 * frame. First capture in a timeline requires a full current-tree bootstrap
 * transaction (possibly genuinely empty). Its source state must match cut.
 * The journal freezes that bootstrap across unacknowledged retransmissions.
 *
 * ackSequence is the last actually acknowledged outgoing snapshot, not a
 * guessed delta baseline. Capture never advances acknowledged delivery.
 * bootstrapKnown=0 refuses initialization rather than inventing animation.
 * Newly visible actors in an established timeline require an owner-generated
 * current-time goal-state transaction. Filtering a historical event is not
 * permission to replay it later against C1's newer global time watermark. */
int CODOL_ActorAnimCapture(unsigned client,uint32_t sequence,uint32_t ackSequence,
    uint32_t timeline,const codol_actor_anim_cut_t *cut,
    const codol_actor_anim_event_t *bootstrap,unsigned bootstrapCount,int bootstrapKnown,
    codol_actor_anim_visible_t visible,void *capturedContext);
/* Copy pending commands into frame bindings. Call Published only after the
 * corresponding complete snapshot was serialized successfully. */
int CODOL_ActorAnimCopy(unsigned client,uint32_t sequence,codol_animcmd_t *out,
                       unsigned capacity,unsigned *count);
int CODOL_ActorAnimPublished(unsigned client,uint32_t sequence);
#pragma pack(pop)
#ifdef __cplusplus
}
#endif
#endif
