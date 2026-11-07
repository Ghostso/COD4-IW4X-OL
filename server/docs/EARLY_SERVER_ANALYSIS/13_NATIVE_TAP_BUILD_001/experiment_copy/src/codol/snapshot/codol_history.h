#ifndef CODOL_HISTORY_H
#define CODOL_HISTORY_H
#include "codol_snapshot.h"
typedef struct codol_history_s codol_history_t;
codol_history_t *CODOL_CreateHistory(void);
void CODOL_ClearHistory(codol_history_t *history);
void CODOL_DestroyHistory(codol_history_t *history);
/* Commit only after successful transport acceptance. State must describe the
 * quantized client-held values, not unquantized engine input. Makes deep copies;
 * failure leaves history unchanged. Sequences must strictly increase. */
int CODOL_CommitHistory(codol_history_t *history, const codol_snapshot_state_t *held);
/* Prepare client-decoded values against an exact retained base (zero for a
 * full snapshot), then commit atomically. Call after successful serialization
 * and transport acceptance, using the same context and rov as the writer. */
int CODOL_CommitReachedHistory(codol_history_t *history, const codol_snapshot_state_t *requested,
                               uint32_t base_sequence, int read_origin_velocity,
                               const codol_delta_context_t *context);
/* Allocate/quantize before sending. One pending snapshot per history; it is
 * invisible to ACK lookup. Finish performs no allocation and requires the exact
 * attempted sequence. accepted=0 discards it. Clear/Destroy also discard it. */
const char *CODOL_HistoryFailure(void);
int CODOL_PrepareHistory(codol_history_t *history, const codol_snapshot_state_t *requested,
                         uint32_t base_sequence, int read_origin_velocity,
                         const codol_delta_context_t *context);
/* Prepare a SNAPFLAG_BASELINE frame. Its reached state is copied into the
 * separately pinned no-delta baseline only if transport accepts the frame. */
int CODOL_PrepareBaselineHistory(codol_history_t *history, const codol_snapshot_state_t *requested,
                                 int read_origin_velocity,
                                 const codol_delta_context_t *context);
int CODOL_FinishHistory(codol_history_t *history, uint32_t sequence, int accepted);
/* Exact acknowledged sequence only. No guessing a base for an ACK that names
 * another kind of packet. Returned pointer lasts until overwrite/reset/destroy. */
const codol_snapshot_state_t *CODOL_FindHistoryBase(const codol_history_t *history,
                                                  uint32_t acknowledged, uint32_t next_sequence);
/* Zero until the first successfully transmitted frame is committed. */
uint32_t CODOL_HistoryLatestSequence(const codol_history_t *history);
/* The frame CODOL_Prepare*History just staged: the requested state reached as
 * the client will hold it (quantized). NULL when nothing is pending. */
const codol_snapshot_state_t *CODOL_HistoryPendingState(const codol_history_t *history);
/* C1's persistent noDeltaSnapshot, used when deltaNum is zero without flag 8.
 * This state remains available after its ordinary 32-frame ring slot expires. */
const codol_snapshot_state_t *CODOL_HistoryBaseline(const codol_history_t *history);
/* The newest committed frame with floor < sequence <= acknowledged: what the
 * client holds as cl.snap after acknowledging that message. NULL when no
 * such frame is still in the 32-frame ring. */
const codol_snapshot_state_t *CODOL_HistoryReceivedState(const codol_history_t *history,
                                                        uint32_t acknowledged, uint32_t floor);
#endif
