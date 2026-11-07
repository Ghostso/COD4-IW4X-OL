#ifndef CODOL_SNAPSHOT_H
#define CODOL_SNAPSHOT_H
#include "codol_playerstate.h"
#include "codol_entities.h"
#include "codol_clients.h"
#include "codol_actors.h"
#include "codol_animcmd.h"
#include "codol_glass_snapshot.h"
/* Semantic state must not inherit engine-header packing. */
#pragma pack(push, 8)
typedef struct {
    uint32_t sequence;
    const codol_player_fields_t *player;
    const codol_hud_state_t *hud;
    const codol_entity_state_t *entities;
    size_t entity_count;
    const codol_client_state_t *clients;
    size_t client_count;
    const codol_actor_state_t *actors;
    size_t actor_count;
    const codol_glass_wire_piece_t *glass;
    size_t glass_count;
} codol_snapshot_state_t;
/* Serializes one svc_snapshot + EOF. The transport's reliable ACK and commands
 * precede this body. Caller owns states, selects an acknowledged base, and must
 * record the quantized client-held state only after a successful send. */
const char *CODOL_WriteSnapshotFailure(void);
int CODOL_WriteSnapshot(codol_msg_t *msg, const codol_snapshot_state_t *to,
                        const codol_snapshot_state_t *base,
                        const codol_player_array_updates_t *updates,
                        const codol_animcmd_t *commands, size_t command_count,
                        unsigned flags, int read_origin_velocity,
                        codol_delta_context_t *context);
/* As above, with the wire deltaNum selected independently from the effective
 * serialization base. C1 deltaNum 0/flags 0 uses its pinned baseline. */
int CODOL_WriteSnapshotDeltaNumber(codol_msg_t *msg, const codol_snapshot_state_t *to,
                        const codol_snapshot_state_t *base, uint32_t delta_number,
                        const codol_player_array_updates_t *updates,
                        const codol_animcmd_t *commands, size_t command_count,
                        unsigned flags, int read_origin_velocity,
                        codol_delta_context_t *context);
#pragma pack(pop)
#endif
