/* Native C1 command acceptance and execution cursors.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_usercmd_queue.h"
#include <limits.h>
#include <string.h>

static int cmd_valid(const codol_usercmd_t *command)
{
    return command && command->weapon < CODOL_WEAPON_IDS &&
           command->offHandIndex < CODOL_WEAPON_IDS &&
           command->altModeWeapon < CODOL_WEAPON_IDS;
}

/* C1 command time is a 32-bit wire value. Signed subtraction gives the usual
 * wrap-safe order while the endpoints remain less than 2^31 ms apart. */
static int time_after(uint32_t left, uint32_t right)
{
    return (int32_t)(left - right) > 0;
}

static codol_usercmd_t *queue_tail(codol_c1_cmd_queue_t *queue)
{
    return queue->storage + (queue->head + queue->count) % queue->capacity;
}

int CODOL_C1CmdQueueInit(codol_c1_cmd_queue_t *queue,
                         codol_usercmd_t *storage, size_t capacity)
{
    if (!queue || !storage || !capacity) return 0;
    memset(queue, 0, sizeof(*queue));
    queue->storage = storage;
    queue->capacity = capacity;
    return 1;
}

void CODOL_C1CmdQueueReset(codol_c1_cmd_queue_t *queue)
{
    codol_usercmd_t *storage;
    size_t capacity;
    if (!queue) return;
    storage = queue->storage;
    capacity = queue->capacity;
    memset(queue, 0, sizeof(*queue));
    queue->storage = storage;
    queue->capacity = capacity;
}

int CODOL_C1CmdQueueSeed(codol_c1_cmd_queue_t *queue,
                         const codol_usercmd_t *baseline)
{
    if (!queue || !queue->storage || !queue->capacity || !cmd_valid(baseline))
        return 0;
    CODOL_C1CmdQueueReset(queue);
    queue->accepted_cmd = *baseline;
    queue->executed_cmd = *baseline;
    queue->previous_executed_cmd = *baseline;
    queue->has_accepted = 1;
    queue->has_executed = 1;
    queue->has_previous_executed = 1;
    return 1;
}

codol_c1_cmd_accept_t CODOL_C1CmdQueueAccept(
    codol_c1_cmd_queue_t *queue, const codol_usercmd_t *command)
{
    if (!queue || !queue->storage || !queue->capacity || !cmd_valid(command))
        return CODOL_C1_CMD_ACCEPT_INVALID;
    if (queue->has_accepted &&
        !time_after(command->serverTime, queue->accepted_cmd.serverTime))
        return CODOL_C1_CMD_ACCEPT_IGNORED;
    if (queue->count == queue->capacity) return CODOL_C1_CMD_ACCEPT_FULL;
    *queue_tail(queue) = *command;
    ++queue->count;
    queue->accepted_cmd = *command;
    queue->has_accepted = 1;
    return CODOL_C1_CMD_ACCEPTED;
}

codol_c1_cmd_accept_t CODOL_C1CmdQueueAcceptBatch(
    codol_c1_cmd_queue_t *queue, const codol_usercmd_t *commands, size_t count,
    codol_c1_cmd_batch_result_t *result)
{
    size_t first_new = 0, i, new_count;
    codol_c1_cmd_batch_result_t local = {0, 0};
    if (result) *result = local;
    if (!queue || !queue->storage || !queue->capacity ||
        (count && !commands)) return CODOL_C1_CMD_ACCEPT_INVALID;
    if (!count) return CODOL_C1_CMD_ACCEPT_IGNORED;

    for (i = 0; i < count; ++i) {
        if (!cmd_valid(commands + i)) return CODOL_C1_CMD_ACCEPT_INVALID;
        if (i && !time_after(commands[i].serverTime,
                             commands[i - 1].serverTime))
            return CODOL_C1_CMD_ACCEPT_ORDER;
    }
    if (queue->has_accepted) {
        while (first_new < count &&
               !time_after(commands[first_new].serverTime,
                           queue->accepted_cmd.serverTime))
            ++first_new;
    }
    new_count = count - first_new;
    if (new_count > queue->capacity - queue->count)
        return CODOL_C1_CMD_ACCEPT_FULL;

    for (i = first_new; i < count; ++i) {
        *queue_tail(queue) = commands[i];
        ++queue->count;
    }
    local.ignored = first_new;
    local.accepted = new_count;
    if (new_count) {
        queue->accepted_cmd = commands[count - 1];
        queue->has_accepted = 1;
    }
    if (result) *result = local;
    return new_count ? CODOL_C1_CMD_ACCEPTED : CODOL_C1_CMD_ACCEPT_IGNORED;
}

codol_c1_cmd_exec_t CODOL_C1CmdQueueBeginExecute(
    const codol_c1_cmd_queue_t *queue, uint32_t server_time,
    uint32_t max_lead_ms, codol_usercmd_t *command)
{
    const codol_usercmd_t *head;
    int32_t lead;
    if (!queue || !queue->storage || !queue->capacity || !command ||
        max_lead_ms > INT32_MAX) return CODOL_C1_CMD_EXEC_INVALID;
    if (!queue->count) return CODOL_C1_CMD_EXEC_EMPTY;
    head = queue->storage + queue->head;
    lead = (int32_t)(head->serverTime - server_time);
    if (lead > (int32_t)max_lead_ms) return CODOL_C1_CMD_EXEC_FUTURE;
    *command = *head;
    return CODOL_C1_CMD_EXEC_READY;
}

int CODOL_C1CmdQueueCommitExecuted(codol_c1_cmd_queue_t *queue,
                                   uint32_t server_time)
{
    codol_usercmd_t *head;
    if (!queue || !queue->storage || !queue->capacity || !queue->count)
        return 0;
    head = queue->storage + queue->head;
    if (head->serverTime != server_time) return 0;
    if (queue->has_executed) {
        queue->previous_executed_cmd = queue->executed_cmd;
        queue->has_previous_executed = 1;
    } else {
        queue->previous_executed_cmd = *head;
        queue->has_previous_executed = 1;
    }
    queue->executed_cmd = *head;
    queue->has_executed = 1;
    queue->head = (queue->head + 1) % queue->capacity;
    --queue->count;
    return 1;
}

size_t CODOL_C1CmdQueuePending(const codol_c1_cmd_queue_t *queue)
{
    return queue ? queue->count : 0;
}

const codol_usercmd_t *CODOL_C1CmdQueueAccepted(
    const codol_c1_cmd_queue_t *queue)
{
    return queue && queue->has_accepted ? &queue->accepted_cmd : NULL;
}

const codol_usercmd_t *CODOL_C1CmdQueueExecuted(
    const codol_c1_cmd_queue_t *queue)
{
    return queue && queue->has_executed ? &queue->executed_cmd : NULL;
}

const codol_usercmd_t *CODOL_C1CmdQueuePreviousExecuted(
    const codol_c1_cmd_queue_t *queue)
{
    return queue && queue->has_previous_executed ?
           &queue->previous_executed_cmd : NULL;
}
