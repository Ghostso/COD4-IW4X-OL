/* SPDX-License-Identifier: AGPL-3.0-or-later */
#ifdef CODOL_SERVER
#include "codol_scoreboard_stats.h"
#include "sys_cod4defs.h"
#include "codol_script_profile_vm.h"
#include <string.h>

/* Session data, deliberately separate from the playerState cleared on spawn.
 * C1 client fields 0xc3c0d8..0xc3c108 and 0xc3c198 name these integer values.
 * Connection/map reset owns their lifetime; snapshot history does not. */
static int score_stats[MAX_CLIENTS][CODOL_SCORE_STAT_COUNT];
int CODOL_GetScoreStat(unsigned client, unsigned stat)
{
    return client < MAX_CLIENTS && stat < CODOL_SCORE_STAT_COUNT
        ? score_stats[client][stat] : 0;
}
void CODOL_SetScoreStat(unsigned client, unsigned stat, int value)
{
    if (client < MAX_CLIENTS && stat < CODOL_SCORE_STAT_COUNT)
        score_stats[client][stat] = value;
}
void CODOL_ResetScoreStats(unsigned client)
{
    if (client < MAX_CLIENTS) memset(score_stats[client], 0, sizeof(score_stats[client]));
}
void CODOL_ResetAllScoreStats(void)
{
    memset(score_stats, 0, sizeof(score_stats));
}

int CODOL_ReadScoreboardSkill(unsigned client, int *out)
{
    const codol_structured_path_t path[2] = {{"skills", 0}, {"tdm", 0}};
    const codol_structured_definition_t *definition;
    const uint8_t *record;
    codol_structured_field_t field;
    size_t capacity;
    uint32_t raw;
    int32_t value;
    float number;
    /* C1 5d2480 ->590670 with al=0 selects public mp/playerdata.def through
     * 590590. Its final signed divide by100 and +25 is independent of the
     * active gametype: the lookup names are literally skills and tdm. */
    if (!out || client >= MAX_CLIENTS ||
        !CODOL_ScriptProfileView(client, CODOL_PROFILE_PUBLIC,
            &definition, &record, &capacity) ||
        !CODOL_ResolveStructuredField(definition, path, 2, &field) ||
        !CODOL_StructuredReadScalar(&definition->layout, field.type.kind,
            field.logical_index, record, capacity, &raw)) return 0;
    switch (field.type.kind) {
    case 0: memcpy(&value, &raw, sizeof(value)); break;
    case 1: case 2: value = (int32_t)raw; break;
    case 9: value = (raw & 0x8000u) ? (int32_t)(raw & 0xffffu) - 65536
                                  : (int32_t)(raw & 0xffffu); break;
    case 8:
        memcpy(&number, &raw, sizeof(number));
        value = CODOL_ScoreInteger(number);
        break;
    default: return 0;
    }
    *out = value / 100 + 25;
    return 1;
}
#endif

