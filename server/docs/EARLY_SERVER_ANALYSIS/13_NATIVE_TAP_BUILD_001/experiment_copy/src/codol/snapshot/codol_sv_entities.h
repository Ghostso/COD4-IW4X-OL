#ifndef CODOL_SV_ENTITIES_H
#define CODOL_SV_ENTITIES_H
extern int codol_entity_failure_number, codol_entity_failure_type;
extern const char *codol_entity_failure_stage;
/* Resolver-supplied reason for the entity currently being seeded. Cleared
 * before each resolve and printed with the one-per-type drop warning, so a
 * dropped entity states why instead of only naming its type. */
extern char codol_entity_seed_reason[160];
#include "codol_engine_state.h"

/* Complete type-specific seed and semantically resolved event arguments for
 * the exact retained snapshot entity. Resolver must not mutate engine state.
 * Asset publication precedes collection; native indices are not wire indices. */
/* Semantic state must not inherit engine-header packing. */
#pragma pack(push, 8)
typedef struct {
    codol_entity_state_t state;
    uint32_t event_parameters[4];
    /* Physical queue slots suppressed for this recipient or explicitly
     * omitted by the semantic resolver because their mapping is unavailable.
     * Zero preserves the ordinary queue; do not change its event epoch. */
    unsigned event_suppressed_slots;
    unsigned primary_weapon;
} codol_snapshot_entity_bindings_t;
typedef int (*codol_snapshot_entity_resolver_t)(void *,const entityState_t *,
                                               codol_snapshot_entity_bindings_t *);
/* Read first_entity/num_entities from svsHeader's retained snapshot ring.
 * Preserve visibility/order from that snapshot. Output and generation clocks
 * commit together only after the entire span converts. Clocks are indexed by
 * native entity number, not visible-list position or recipient ACK. Their owner
 * must clear them on entity reuse/map reset. No codec, send, or ACK commit here.
 * Requires a real resolver for every nonempty span; no default zero-state path. */
int CODOL_CollectServerEntities(int first,int count,codol_entity_state_t *out,size_t capacity,
    codol_snapshot_entity_resolver_t resolve,void *context);
/* As above, but an entity the resolver cannot seed is dropped rather than
 * failing the whole array; *emitted receives the number written. */
int CODOL_CollectServerEntitiesEmitted(int first,int count,codol_entity_state_t *out,size_t capacity,
    codol_snapshot_entity_resolver_t resolve,void *context,size_t *emitted);
/* As Emitted, for one recipient: a child whose link parent is not among the
 * emitted entities is published with its parent link cleared (or dropped if
 * that conversion fails). local_client is the recipient's viewed client
 * (ps.clientNum), which C1 resolves from the predicted player and which is
 * therefore never missing; -1 when there is none. */
int CODOL_CollectServerEntitiesForClient(int first,int count,codol_entity_state_t *out,size_t capacity,
    codol_snapshot_entity_resolver_t resolve,void *context,size_t *emitted,int local_client);
/* Event history is owned by the states themselves (codol_entitystate_ext.h,
 * codol_playerstate_ext.h), not by recipient-side clocks. These clear the live
 * histories: G_InitGentity resets a reused slot, server clear/quit the map. */
/* The snapshot-area epoch reset. The Generation forms below add the vehicle,
 * model, missile and glass resets that live outside this area. */
void CODOL_ResetEntityEventEpoch(unsigned entity_number);
void CODOL_ResetEntityEventEpochs(void);
void CODOL_ResetEntityEventGeneration(unsigned entity_number);
void CODOL_ResetEntityEventGenerations(void);
/* There is no player event clock: the player event counter lives with the
 * playerState (codol_playerstate_ext.h), so it survives copies and archiving
 * instead of being accumulated per recipient. */
int CODOL_CollectCurrentServerEntities(int first,int count,codol_entity_state_t *out,size_t capacity,
    codol_snapshot_entity_resolver_t resolve,void *context);
#pragma pack(pop)
#endif
