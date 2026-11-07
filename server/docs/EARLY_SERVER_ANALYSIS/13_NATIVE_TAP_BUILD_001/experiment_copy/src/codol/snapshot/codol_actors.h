#ifndef CODOL_ACTORS_H
#define CODOL_ACTORS_H
#include "codol_entities.h"
/* Semantic state must not inherit engine-header packing. */
#pragma pack(push, 8)
typedef struct {
    unsigned number;
    /* Canonical CoDOL bytes, not an IW3 actor. Fields at 0x44/45/46 overlap;
     * one shared byte image ensures their transmitted words agree. */
    uint8_t data[0x5c];
    /* Native archive metadata; never part of the canonical wire byte image.
     * Preserve alternate model/team/owner with the same historic actor, so a
     * per-recipient model choice uses the archived actor and not a live one. */
    unsigned enemyModel, actorTeam;
    int ownerClient;
} codol_actor_state_t;
const codol_entity_field_t *CODOL_ActorField(unsigned index);
int CODOL_WriteActors(codol_msg_t *msg, const codol_actor_state_t *from, size_t from_count,
                      const codol_actor_state_t *to, size_t to_count,
                      codol_delta_context_t *context);
#pragma pack(pop)
#endif
