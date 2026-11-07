#ifndef CODOL_DOG_ANIMATION_H
#define CODOL_DOG_ANIMATION_H
#include "codol_actor_anim_journal.h"
#include <stdint.h>
struct DObj_s;
struct XAnimTree_s;
#ifdef __cplusplus
extern "C" {
#endif
#pragma pack(push, 8)
#define CODOL_DOG_ANIM_NODES 255
typedef struct {
    uint16_t ref;
    uint16_t parent; /* pose index + 1, zero denotes the tree root link */
    uint8_t leaf;
    uint8_t sync_root,looping;
    float current_weight,goal_weight,remaining_blend,playback_rate,fraction;
} codol_dog_anim_node_t;
typedef struct {
    uint32_t generation,time;
    uint16_t entity,count;
    codol_dog_anim_node_t nodes[CODOL_DOG_ANIM_NODES];
} codol_dog_anim_pose_t;
typedef struct {
    unsigned entity;
    uint32_t generation;
    const struct XAnimTree_s *tree;
} codol_dog_anim_capture_source_t;
/* Capture on the game thread after its XAnim update. Store this value with the
 * actor archive; it owns no live pointers and remains valid after entity free. */
int CODOL_DogAnimCapture(const struct XAnimTree_s *,unsigned entity,
    uint32_t generation,uint32_t time,codol_dog_anim_pose_t *);
/* Emit clear + current weights + pending goals + leaf phases from a captured
 * pose. No live XAnim access, invented clip or fixed idle bootstrap. */
int CODOL_DogAnimBootstrap(const codol_dog_anim_pose_t *,
    codol_actor_anim_event_t *,unsigned capacity,unsigned *count);
/* Supported native owner operation: resolve ref against the selected dog tree
 * first. It publishes before mutating XAnim; refusal leaves native state intact.
 * Batch operations additionally support the C1 knob bit for goal/complete-goal.
 * Notifications require their own verified producers. */
int CODOL_DogAnimGoal(struct DObj_s *,unsigned entity,uint32_t generation,
    uint32_t time,unsigned ref,float goal_weight,float blend,float playback_rate,
    int complete,int restart);
int CODOL_DogAnimApplyBatch(struct DObj_s *,const codol_actor_anim_event_t *,unsigned count);
/* Same atomic wire/native transaction, plus a real server notetrack channel
 * on the final command, a leaf goal. During the ordinary DObj tick, GSC receives
 * entity notify(channel, authored_notetrack), including the engine end marker.
 * No channel or script string handle is written into the C1 wire record.
 * The caller owns the listener/state transition and must install it first. */
/* Also supports a synchronized group when prior commands establish a
 * positive complete leaf goal in that group. Notification remains native. */
int CODOL_DogAnimApplyNotifiedBatch(struct DObj_s *,
    const codol_actor_anim_event_t *,unsigned count,unsigned notifyEvent,
    const char *channel);
int CODOL_DogAnimApplyNotifiedLeafBatch(struct DObj_s *,
    const codol_actor_anim_event_t *,unsigned count,unsigned notifyEvent,
    const char *channel);
/* Immutable pose ownership after the engine's existing DObj tick. Captures
 * all sources atomically; old archive is invalidated on failed replacement. */
void CODOL_DogAnimArchiveReset(void);
int CODOL_DogAnimArchiveStore(int frame,uint32_t time,
    const codol_dog_anim_capture_source_t *,unsigned count);
const codol_dog_anim_pose_t *CODOL_DogAnimArchiveFind(int frame,uint32_t time,
    unsigned entity,uint32_t generation);
#pragma pack(pop)
#ifdef __cplusplus
}
#endif
#endif
