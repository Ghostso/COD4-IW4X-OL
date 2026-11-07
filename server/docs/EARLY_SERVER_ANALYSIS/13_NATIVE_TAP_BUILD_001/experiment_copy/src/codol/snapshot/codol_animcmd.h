#ifndef CODOL_ANIMCMD_H
#define CODOL_ANIMCMD_H
#include "codol_msg.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Semantic state must not inherit engine-header packing. */
#pragma pack(push, 8)
typedef struct {
    uint32_t time;
    uint16_t entity, ref, sub;
    uint8_t type, arg2;
    /* C1 command+1c is goal weight (decoder5a10e0); +20 is playback
     * rate (decoder5a1060). Their wire codecs are intentionally different. */
    float goal_weight, playback_rate, blend, fraction;
} codol_animcmd_t;
int CODOL_WriteAnimCommands(codol_msg_t *msg, const codol_animcmd_t *commands,
                            size_t count, uint32_t server_time);
#pragma pack(pop)
#ifdef __cplusplus
}
#endif
#endif
