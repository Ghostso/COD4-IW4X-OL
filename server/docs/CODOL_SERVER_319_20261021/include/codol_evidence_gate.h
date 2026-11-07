#ifndef CODOL_EVIDENCE_GATE_H
#define CODOL_EVIDENCE_GATE_H

#include "codol_types.h"

typedef enum {
    CODOL_EV_LEVEL_0_TARGET_RUNTIME = 0,
    CODOL_EV_LEVEL_1_TARGET_STATIC,
    CODOL_EV_LEVEL_2_FAMILY_REFERENCE,
    CODOL_EV_LEVEL_3_SELF_IMPL,
    CODOL_EV_LEVEL_4_CLAIM,
    CODOL_EV_LEVEL_5_UNVERIFIED
} codol_evidence_level_t;

typedef enum {
    CODOL_HANDLER_ACTIVE = 0,
    CODOL_HANDLER_REFERENCE,
    CODOL_HANDLER_DISABLED
} codol_handler_status_t;

typedef struct codol_wire_entry {
    uint16_t                opcode;
    const char             *name;
    const char             *version;
    codol_evidence_level_t  evidence_level;
    const char             *evidence_id;
    codol_handler_status_t  status;
    int (*handler)(codol_session_t *, const uint8_t *, size_t);
} codol_wire_entry_t;

void codol_evidence_registry_init(codol_evidence_registry_t *reg, bool release_mode);
codol_result_t codol_evidence_registry_add_id(codol_evidence_registry_t *reg, const char *id);
bool codol_evidence_registry_has_id(const codol_evidence_registry_t *reg, const char *id);

codol_result_t codol_wire_table_validate(const codol_wire_entry_t *table, size_t count,
                                          const codol_evidence_registry_t *reg);

const codol_wire_entry_t *codol_wire_table_lookup(const codol_wire_entry_t *table, size_t count,
                                                    uint16_t opcode, bool release_mode);

#endif /* CODOL_EVIDENCE_GATE_H */
