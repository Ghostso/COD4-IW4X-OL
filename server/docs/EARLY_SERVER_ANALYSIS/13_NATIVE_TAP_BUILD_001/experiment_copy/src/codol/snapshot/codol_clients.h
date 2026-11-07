#ifndef CODOL_CLIENTS_H
#define CODOL_CLIENTS_H
#include "codol_entities.h"
#define CODOL_CLIENT_FIELDS 77
#define CODOL_CLIENT_ATTACHMENTS 16
/* Semantic state must not inherit engine-header packing. */
#pragma pack(push, 8)
typedef struct {
    unsigned number;
    uint32_t field[CODOL_CLIENT_FIELDS];
} codol_client_state_t;
/* CoDOL composition uses its own model IDs and storage, never the six-entry
 * attachment arrays embedded in the retained IW3 ABI. */
typedef struct {
    unsigned model;
    unsigned attach_model[CODOL_CLIENT_ATTACHMENTS];
    unsigned attach_tag[CODOL_CLIENT_ATTACHMENTS];
} codol_client_appearance_t;
enum { CODOL_ABILITY_MASK_WORDS=4, CODOL_ABILITY_VALUES=23 };
/* C1 ability-modifier state, distinct from retained IW3 perk bits. Mask IDs
 * use 0x80000000 >> (id & 31); values use the modifier table's slot mapping.
 * Values must already include the table defaults and modifier operations. */
typedef struct {
    uint32_t masks[CODOL_ABILITY_MASK_WORDS];
    float values[CODOL_ABILITY_VALUES];
} codol_client_abilities_t;
/* Snapshot-owned copy at clientState +c0..128. No pointers to live state
 * escape, so a captured frame retains the values that existed at capture.
 * Does not translate perk names, infer defaults or populate gameplay state. */
int CODOL_OverlayClientAbilities(codol_client_state_t *,const codol_client_abilities_t *);
/* Replace the entire appearance, clearing removed parts. Models must be
 * contiguous; an empty base is legal in C1. Other client fields are preserved.
 * Inputs are already resolved/published configstring IDs. Atomic on failure. */
int CODOL_OverlayClientAppearance(codol_client_state_t *,const codol_client_appearance_t *);
const codol_entity_field_t *CODOL_ClientField(unsigned index);
int CODOL_ReachClient(codol_client_state_t *held, const codol_client_state_t *base,
                      const codol_client_state_t *requested, const codol_delta_context_t *context);
int CODOL_WriteClients(codol_msg_t *msg, const codol_client_state_t *from, size_t from_count,
                       const codol_client_state_t *to, size_t to_count,
                       codol_delta_context_t *context);
#pragma pack(pop)
#endif
