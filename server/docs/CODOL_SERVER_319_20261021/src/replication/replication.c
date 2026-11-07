#include "codol_replication.h"
#include <string.h>
#include <stdio.h>

void codol_replication_init(codol_world_t *world)
{
    if (!world) return;
    memset(&world->snapshot_history, 0, sizeof(world->snapshot_history));
}

codol_result_t codol_replication_build(codol_session_t *session, const codol_frame_t *frame,
                                        uint8_t *output, size_t capacity, size_t *output_len)
{
    if (!session || !frame || !output || capacity == 0 || !output_len)
        return CODOL_ERR_INVALID_ARG;

    *output_len = 0;

    if (capacity < 16) return CODOL_ERR_NO_MEMORY;

    output[0] = (uint8_t)(frame->frame_number >> 24);
    output[1] = (uint8_t)(frame->frame_number >> 16);
    output[2] = (uint8_t)(frame->frame_number >> 8);
    output[3] = (uint8_t)(frame->frame_number);

    output[4] = (uint8_t)(frame->server_time >> 24);
    output[5] = (uint8_t)(frame->server_time >> 16);
    output[6] = (uint8_t)(frame->server_time >> 8);
    output[7] = (uint8_t)(frame->server_time);

    output[8] = (uint8_t)(frame->num_entities >> 8);
    output[9] = (uint8_t)(frame->num_entities);

    *output_len = 10;

    session->netchan.outgoing_sequence++;
    return CODOL_OK;
}

codol_result_t codol_replication_ack(codol_session_t *session, uint32_t ack_frame)
{
    if (!session) return CODOL_ERR_INVALID_ARG;
    (void)ack_frame;
    return CODOL_OK;
}

codol_result_t codol_replication_commit_frame(codol_world_t *world, const codol_frame_t *frame)
{
    if (!world || !frame) return CODOL_ERR_INVALID_ARG;

    codol_snapshot_history_t *hist = &world->snapshot_history;
    int idx = hist->head % CODOL_SNAPSHOT_HISTORY;

    codol_snapshot_t *snap = &hist->snapshots[idx];
    memset(snap, 0, sizeof(*snap));
    snap->frame_number = frame->frame_number;
    snap->server_time = frame->server_time;

    for (int i = 0; i < CODOL_MAX_ENTITIES; i++) {
        if (world->entities[i].in_use) {
            memcpy(&snap->entities[i], &world->entities[i], sizeof(codol_entity_state_t));
        }
    }
    for (int i = 0; i < CODOL_MAX_CLIENTS; i++) {
        memcpy(&snap->players[i], &world->players[i], sizeof(codol_player_state_t));
    }

    hist->head = (hist->head + 1) % CODOL_SNAPSHOT_HISTORY;
    if (hist->count < CODOL_SNAPSHOT_HISTORY) hist->count++;

    return CODOL_OK;
}

codol_snapshot_t *codol_replication_get_baseline(codol_session_t *session)
{
    (void)session;
    return NULL;
}
