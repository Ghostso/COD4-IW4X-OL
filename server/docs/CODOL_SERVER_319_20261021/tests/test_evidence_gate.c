#include "codol_evidence_gate.h"
#include <stdio.h>
#include <string.h>
#include <assert.h>

static int dummy_handler(codol_session_t *s, const uint8_t *d, size_t l)
{
    (void)s; (void)d; (void)l;
    return 0;
}

int main(void)
{
    printf("=== test_evidence_gate ===\n");

    codol_evidence_registry_t reg;
    codol_evidence_registry_init(&reg, false);

    codol_evidence_registry_add_id(&reg, "CODOL-BATTLE-SERVER-REVERSE-COVERAGE-001");
    codol_evidence_registry_add_id(&reg, "CODOL_2697_SERVER_STATIC_ANALYSIS_20261011");
    codol_evidence_registry_add_id(&reg, "R3_EVIDENCE_20261021_122246");

    assert(codol_evidence_registry_has_id(&reg, "CODOL-BATTLE-SERVER-REVERSE-COVERAGE-001"));
    assert(!codol_evidence_registry_has_id(&reg, "NONEXISTENT"));

    codol_wire_entry_t table[] = {
        {
            .opcode = 0x0001,
            .name = "gamestate",
            .version = "3.19",
            .evidence_level = CODOL_EV_LEVEL_1_TARGET_STATIC,
            .evidence_id = "CODOL-BATTLE-SERVER-REVERSE-COVERAGE-001",
            .status = CODOL_HANDLER_ACTIVE,
            .handler = dummy_handler,
        },
        {
            .opcode = 0x0002,
            .name = "snapshot",
            .version = "3.19",
            .evidence_level = CODOL_EV_LEVEL_1_TARGET_STATIC,
            .evidence_id = "CODOL-BATTLE-SERVER-REVERSE-COVERAGE-001",
            .status = CODOL_HANDLER_ACTIVE,
            .handler = dummy_handler,
        },
        {
            .opcode = 0x0003,
            .name = "reference_2697_writer",
            .version = "2.6.9.7",
            .evidence_level = CODOL_EV_LEVEL_2_FAMILY_REFERENCE,
            .evidence_id = "CODOL_2697_SERVER_STATIC_ANALYSIS_20261011",
            .status = CODOL_HANDLER_REFERENCE,
            .handler = dummy_handler,
        },
        {
            .opcode = 0x0004,
            .name = "disabled_entry",
            .version = NULL,
            .evidence_level = CODOL_EV_LEVEL_5_UNVERIFIED,
            .evidence_id = NULL,
            .status = CODOL_HANDLER_DISABLED,
            .handler = NULL,
        },
    };
    size_t count = sizeof(table) / sizeof(table[0]);

    codol_result_t result = codol_wire_table_validate(table, count, &reg);
    printf("debug mode validation: %s\n", result == CODOL_OK ? "PASS" : "FAIL");
    assert(result == CODOL_OK);

    codol_evidence_registry_t reg_release;
    codol_evidence_registry_init(&reg_release, true);
    codol_evidence_registry_add_id(&reg_release, "CODOL-BATTLE-SERVER-REVERSE-COVERAGE-001");

    result = codol_wire_table_validate(table, count, &reg_release);
    printf("release mode validation: %s\n", result != CODOL_OK ? "PASS (correctly rejected reference)" : "FAIL (should have rejected reference)");
    assert(result != CODOL_OK);

    const codol_wire_entry_t *found = codol_wire_table_lookup(table, count, 0x0001, false);
    assert(found != NULL);
    assert(found->opcode == 0x0001);

    found = codol_wire_table_lookup(table, count, 0x0001, true);
    assert(found != NULL);

    found = codol_wire_table_lookup(table, count, 0x0003, true);
    assert(found == NULL);

    found = codol_wire_table_lookup(table, count, 0x0004, false);
    assert(found == NULL);

    found = codol_wire_table_lookup(table, count, 0xFFFF, false);
    assert(found == NULL);

    printf("All evidence gate tests PASSED.\n");
    return 0;
}
