#ifndef CODOL_ANIMATION_TABLES_H
#define CODOL_ANIMATION_TABLES_H
#include <stdint.h>
/* server.h leaks a bare #pragma pack(1) into every translation unit that
 * includes it, so a CoDOL header whose structs are not wrapped gets a
 * different layout in those units than in the ones that define them. Wrap
 * the whole header, as codol_actors.h does. Verified with
 * obj/claude-workers/packcheck.py. */
#pragma pack(push, 8)
#define CODOL_ANIM_MOVE_COUNT 55
#define CODOL_ANIM_LEGACY_MOVE_COUNT 43
#define CODOL_ANIM_EVENT_COUNT 24
#define CODOL_ANIM_LEGACY_EVENT_COUNT 21
#define CODOL_ANIM_RECORD_COUNT 1024
#define CODOL_ANIM_CONDITION_COUNT 19
#define CODOL_ANIM_LEGACY_CONDITION_COUNT 10
typedef struct { int index; uint32_t low,high; } codol_anim_condition_t;
typedef struct {
    uint32_t count;
    void *items[128];
} codol_anim_script_slot_t;
#ifdef __cplusplus
extern "C" {
#endif
/* The native parser has one active globalScriptData owner. Extended slots
 * borrow its script-item pointers and are reset for each parsing pass. */
void CODOL_ResetAnimMoveScripts(void *owner);
codol_anim_script_slot_t *CODOL_AnimMoveScript(void *owner,int state,int movement,int canned);
codol_anim_script_slot_t *CODOL_RequireAnimMoveScript(void *owner,int state,int movement,int canned);
codol_anim_script_slot_t *CODOL_AnimEventScript(void *owner,int event);
codol_anim_script_slot_t *CODOL_RequireAnimEventScript(void *owner,int event);
void CODOL_SetAnimConditionValue(int client,int condition,uint64_t value);
void CODOL_SetAnimConditionBit(int client,int condition,int bit);
struct playerState_s;
void CODOL_UpdateAnimConditionsFromPlayerState(int client,const struct playerState_s *ps);
int CODOL_AnimConditionMatches(const void *client_info,const codol_anim_condition_t *condition);
/* Native command ABI: two body parts, two animation indices, two durations,
 * and a sound-alias pointer. Storage may move only on append. */
void *CODOL_AppendAnimCommand(void *item);
void *CODOL_AnimCommands(void *item);
extern unsigned char CODOL_AnimationRecords[CODOL_ANIM_RECORD_COUNT*0x60];
extern unsigned CODOL_AnimationCount;
void CODOL_BeginAnimationRecords(unsigned count);
#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
