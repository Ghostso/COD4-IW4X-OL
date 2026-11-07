#ifndef CODOL_ENTITIES_H
#define CODOL_ENTITIES_H
#include "codol_delta.h"
#define CODOL_ENTITY_FIELDS 66
#define CODOL_ENTITY_SENTINEL 2047
/* Semantic state must not inherit engine-header packing. */
#pragma pack(push, 8)
typedef struct { uint16_t offset; int16_t bits; uint8_t hint; } codol_entity_field_t;
typedef struct {
    uint16_t number, type;
    uint32_t field[CODOL_ENTITY_FIELDS]; /* field[0] comes from type */
} codol_entity_state_t;
const codol_entity_field_t *CODOL_EntityField(unsigned type, unsigned index);
const char *CODOL_ReachEntityFailure(void);
int CODOL_ReachEntity(codol_entity_state_t *held, const codol_entity_state_t *base,
                      const codol_entity_state_t *requested, const codol_delta_context_t *context);
/* Sorted complete states. Missing old entities are removed, unchanged ones
 * inherited, absent fields explicitly zeroed. Baseline: pass no from entities. */
int CODOL_WriteEntities(codol_msg_t *msg, const codol_entity_state_t *from, size_t from_count,
                        const codol_entity_state_t *to, size_t to_count,
                        codol_delta_context_t *context);
#pragma pack(pop)
#endif
