/* Native C1 command acceptance and execution cursors.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_USERCMD_QUEUE_H
#define CODOL_USERCMD_QUEUE_H

#include "codol_usercmd.h"
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    CODOL_C1_CMD_ACCEPT_INVALID = -3,
    CODOL_C1_CMD_ACCEPT_FULL = -2,
    CODOL_C1_CMD_ACCEPT_ORDER = -1,
    CODOL_C1_CMD_ACCEPT_IGNORED = 0,
    CODOL_C1_CMD_ACCEPTED = 1
} codol_c1_cmd_accept_t;

typedef enum {
    CODOL_C1_CMD_EXEC_INVALID = -1,
    CODOL_C1_CMD_EXEC_EMPTY = 0,
    CODOL_C1_CMD_EXEC_READY = 1,
    CODOL_C1_CMD_EXEC_FUTURE = 2
} codol_c1_cmd_exec_t;

typedef struct {
    size_t accepted;
    size_t ignored;
} codol_c1_cmd_batch_result_t;

/* The owner supplies storage so queue depth is an integration decision based
 * on measured C1 traffic rather than a hard-coded timing assumption here. */
typedef struct {
    codol_usercmd_t *storage;
    size_t capacity;
    size_t head;
    size_t count;
    codol_usercmd_t accepted_cmd;
    codol_usercmd_t executed_cmd;
    codol_usercmd_t previous_executed_cmd;
    unsigned has_accepted;
    unsigned has_executed;
    unsigned has_previous_executed;
} codol_c1_cmd_queue_t;

int CODOL_C1CmdQueueInit(codol_c1_cmd_queue_t *queue,
                         codol_usercmd_t *storage, size_t capacity);
void CODOL_C1CmdQueueReset(codol_c1_cmd_queue_t *queue);

/* Seed both cursors from authoritative C1 state during enter-world/reset.
 * The baseline is a cursor only and is not scheduled for execution. */
int CODOL_C1CmdQueueSeed(codol_c1_cmd_queue_t *queue,
                         const codol_usercmd_t *baseline);

/* Commands must advance serverTime in signed modular order. Stale/repeated
 * commands are ignored. A full queue rejects new work without changing the
 * accepted cursor. Batch acceptance is atomic for the new suffix. */
codol_c1_cmd_accept_t CODOL_C1CmdQueueAccept(
    codol_c1_cmd_queue_t *queue, const codol_usercmd_t *command);
codol_c1_cmd_accept_t CODOL_C1CmdQueueAcceptBatch(
    codol_c1_cmd_queue_t *queue, const codol_usercmd_t *commands, size_t count,
    codol_c1_cmd_batch_result_t *result);

/* max_lead_ms is supplied by the native C1 scheduler after that policy is
 * verified. Begin never mutates cursors. Commit advances the executed cursor
 * only after native ClientThink/Pmove successfully consumes the exact head. */
codol_c1_cmd_exec_t CODOL_C1CmdQueueBeginExecute(
    const codol_c1_cmd_queue_t *queue, uint32_t server_time,
    uint32_t max_lead_ms, codol_usercmd_t *command);
int CODOL_C1CmdQueueCommitExecuted(codol_c1_cmd_queue_t *queue,
                                   uint32_t server_time);

size_t CODOL_C1CmdQueuePending(const codol_c1_cmd_queue_t *queue);
const codol_usercmd_t *CODOL_C1CmdQueueAccepted(
    const codol_c1_cmd_queue_t *queue);
const codol_usercmd_t *CODOL_C1CmdQueueExecuted(
    const codol_c1_cmd_queue_t *queue);
const codol_usercmd_t *CODOL_C1CmdQueuePreviousExecuted(
    const codol_c1_cmd_queue_t *queue);

#ifdef __cplusplus
}
#endif
#endif
