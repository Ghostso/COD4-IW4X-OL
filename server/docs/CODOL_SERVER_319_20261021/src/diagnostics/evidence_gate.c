#include "codol_evidence_gate.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void codol_evidence_registry_init(codol_evidence_registry_t *reg, bool release_mode)
{
    memset(reg, 0, sizeof(*reg));
    reg->release_mode = release_mode;
}

codol_result_t codol_evidence_registry_add_id(codol_evidence_registry_t *reg, const char *id)
{
    if (!reg || !id) return CODOL_ERR_INVALID_ARG;
    if (reg->known_count >= 4096) return CODOL_ERR_NO_MEMORY;

    const char **new_ids = (const char **)realloc((void *)reg->known_ids,
                                                   (reg->known_count + 1) * sizeof(const char *));
    if (!new_ids) return CODOL_ERR_NO_MEMORY;

    reg->known_ids = new_ids;
    reg->known_ids[reg->known_count] = _strdup(id);
    if (!reg->known_ids[reg->known_count]) return CODOL_ERR_NO_MEMORY;
    reg->known_count++;
    return CODOL_OK;
}

bool codol_evidence_registry_has_id(const codol_evidence_registry_t *reg, const char *id)
{
    if (!reg || !id) return false;
    for (size_t i = 0; i < reg->known_count; i++) {
        if (strcmp(reg->known_ids[i], id) == 0) return true;
    }
    return false;
}

static codol_result_t validate_single_entry(const codol_wire_entry_t *entry,
                                             const codol_evidence_registry_t *reg,
                                             size_t index)
{
    if (!entry) return CODOL_ERR_INVALID_ARG;

    if (entry->status == CODOL_HANDLER_DISABLED) return CODOL_OK;

    if (entry->status == CODOL_HANDLER_ACTIVE) {
        if (!entry->version || strcmp(entry->version, CODOL_TARGET_VERSION) != 0) {
            fprintf(stderr, "[EVIDENCE-GATE] entry %zu (opcode 0x%04X) version \"%s\" != target \"%s\"\n",
                    index, entry->opcode,
                    entry->version ? entry->version : "(null)", CODOL_TARGET_VERSION);
            return CODOL_ERR_NO_EVIDENCE;
        }
        if (!entry->evidence_id || !codol_evidence_registry_has_id(reg, entry->evidence_id)) {
            fprintf(stderr, "[EVIDENCE-GATE] entry %zu (opcode 0x%04X) evidence_id \"%s\" not in registry\n",
                    index, entry->opcode,
                    entry->evidence_id ? entry->evidence_id : "(null)");
            return CODOL_ERR_NO_EVIDENCE;
        }
        if (entry->evidence_level != CODOL_EV_LEVEL_0_TARGET_RUNTIME &&
            entry->evidence_level != CODOL_EV_LEVEL_1_TARGET_STATIC) {
            fprintf(stderr, "[EVIDENCE-GATE] entry %zu (opcode 0x%04X) evidence_level %d is not target-grade\n",
                    index, entry->opcode, (int)entry->evidence_level);
            return CODOL_ERR_NO_EVIDENCE;
        }
    }

    if (reg && reg->release_mode && entry->status == CODOL_HANDLER_REFERENCE) {
        fprintf(stderr, "[EVIDENCE-GATE] entry %zu (opcode 0x%04X) is REFERENCE but release_mode=true\n",
                index, entry->opcode);
        return CODOL_ERR_NO_EVIDENCE;
    }

    if (entry->status != CODOL_HANDLER_DISABLED && !entry->handler) {
        fprintf(stderr, "[EVIDENCE-GATE] entry %zu (opcode 0x%04X) has NULL handler\n",
                index, entry->opcode);
        return CODOL_ERR_INVALID_ARG;
    }

    return CODOL_OK;
}

codol_result_t codol_wire_table_validate(const codol_wire_entry_t *table, size_t count,
                                          const codol_evidence_registry_t *reg)
{
    if (!table || count == 0) return CODOL_ERR_INVALID_ARG;
    if (!reg) return CODOL_ERR_INVALID_ARG;

    int errors = 0;
    for (size_t i = 0; i < count; i++) {
        if (validate_single_entry(&table[i], reg, i) != CODOL_OK) {
            errors++;
        }
    }
    return errors > 0 ? CODOL_ERR_NO_EVIDENCE : CODOL_OK;
}

const codol_wire_entry_t *codol_wire_table_lookup(const codol_wire_entry_t *table, size_t count,
                                                    uint16_t opcode, bool release_mode)
{
    if (!table) return NULL;
    for (size_t i = 0; i < count; i++) {
        if (table[i].opcode != opcode) continue;
        if (release_mode && table[i].status != CODOL_HANDLER_ACTIVE) return NULL;
        if (table[i].status == CODOL_HANDLER_DISABLED) return NULL;
        return &table[i];
    }
    return NULL;
}
