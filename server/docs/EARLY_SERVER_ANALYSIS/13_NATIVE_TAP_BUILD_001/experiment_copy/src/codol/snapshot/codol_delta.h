/* Value codecs shared by CoDOL entity/player/client/actor snapshot fields. */
#ifndef CODOL_DELTA_H
#define CODOL_DELTA_H
#include "codol_msg.h"
/* Semantic state must not inherit engine-header packing. */
#pragma pack(push, 8)
typedef struct {
    uint32_t server_time;
    int32_t position_base[3];
    int clamp_positions;
    unsigned clamped;
} codol_delta_context_t;
/* C1 wide position codec uses FISTP(center + 2^-30), nearest/even.
 * Only position_base changes; nonfinite/out-of-int32 centers reject atomically. */
int CODOL_SetDeltaPositionBase(codol_delta_context_t *,const float center[3]);
/* Values are raw native 32-bit words: float bits for float fields, integer bits
 * for integers. Special codecs determine their type; default negative widths
 * carry signed integers. No engine structure is reinterpreted as a CoDOL struct. */
int CODOL_WriteDeltaValue(codol_msg_t *msg, int bits, uint32_t from, uint32_t to,
                          codol_delta_context_t *context);
/* Value the client holds after this encoder's quantization. Output is untouched
 * on failure. Context counters are not changed by this read-only calculation. */
int CODOL_ReachDeltaValue(int bits, uint32_t from, uint32_t to,
                          const codol_delta_context_t *context, uint32_t *held);
#pragma pack(pop)
#endif
