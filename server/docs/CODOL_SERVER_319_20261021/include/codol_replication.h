#ifndef CODOL_REPLICATION_H
#define CODOL_REPLICATION_H

#include "codol_types.h"

void codol_replication_init(codol_world_t *world);
codol_result_t codol_replication_build(codol_session_t *session, const codol_frame_t *frame,
                                        uint8_t *output, size_t capacity, size_t *output_len);
codol_result_t codol_replication_ack(codol_session_t *session, uint32_t ack_frame);
codol_result_t codol_replication_commit_frame(codol_world_t *world, const codol_frame_t *frame);
codol_snapshot_t *codol_replication_get_baseline(codol_session_t *session);

#endif /* CODOL_REPLICATION_H */
