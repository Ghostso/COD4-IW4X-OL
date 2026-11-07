/* CoDOL perk slots. SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_perks.h"
#include <errno.h>
#include <stdlib.h>
#include <string.h>

/* C1 40eef0 indexes these eight names at cd915c. */
static const char *const slots[CODOL_PERK_SLOTS] = {
    "perk1", "perk2", "perk3", "perk4",
    "upgrade1", "upgrade2", "upgrade3", "equipment"
};
static int same_name(const char *a, const char *b)
{
    unsigned x, y;
    if (!a || !b) return 0;
    do {
        x=(unsigned char)*a++; y=(unsigned char)*b++;
        if (x>='A' && x<='Z') x+='a'-'A';
        if (y>='A' && y<='Z') y+='a'-'A';
        if (x!=y) return 0;
    } while (x);
    return 1;
}
int CODOL_ReadPerkDefinition(const codol_engine_table_t *table, const char *name,
                            codol_perk_definition_t *out)
{
    int row;
    if (!table || !name || !*name || !out || table->rowCount<0 || table->columnCount<6 ||
        (table->rowCount && !table->values) ||
        (size_t)table->rowCount>SIZE_MAX/sizeof(*table->values)/(size_t)table->columnCount) return -1;
    for (row=table->rowCount-1; row>=0; --row) {
        const char *const *cells=table->values+(size_t)row*table->columnCount;
        codol_perk_definition_t result;
        char *end; long long id;
        if (!same_name(cells[1], name)) continue;
        if (!cells[0] || !*cells[0] || !cells[5] || !*cells[5]) return -1;
        errno=0; id=strtoll(cells[0], &end, 10);
        /* C1 uses atoi; reject malformed/overflow data instead of allowing
         * a wrapped index. Zero is the empty slot sentinel. */
        if (errno==ERANGE || end==cells[0] || *end || id<=0 || id>INT32_MAX) return -1;
        result.id=(uint32_t)id;
        for (result.slot=0; result.slot<CODOL_PERK_SLOTS; ++result.slot)
            if (same_name(cells[5], slots[result.slot])) break;
        if (result.slot==CODOL_PERK_SLOTS) return -1;
        *out=result; return 1;
    }
    return 0;
}
static int valid(const codol_perk_definition_t *definition)
{
    return definition && definition->slot<CODOL_PERK_SLOTS &&
        definition->id>0 && definition->id<=INT32_MAX;
}
int CODOL_SetPerk(codol_perk_state_t *state, const codol_perk_definition_t *definition)
{
    if (!state || !valid(definition)) return 0;
    state->id[definition->slot]=definition->id; return 1;
}
int CODOL_HasPerk(const codol_perk_state_t *state, const codol_perk_definition_t *definition, int *out)
{
    if (!state || !out || !valid(definition)) return 0;
    *out=state->id[definition->slot]==definition->id; return 1;
}
int CODOL_UnsetPerk(codol_perk_state_t *state, const codol_perk_definition_t *definition)
{
    if (!state || !valid(definition)) return 0;
    state->id[definition->slot]=0; return 1;
}
void CODOL_ClearPerks(codol_perk_state_t *state)
{
    if (state) memset(state, 0, sizeof(*state));
}
int CODOL_OverlayPlayerPerks(codol_player_fields_t *out, const codol_perk_state_t *state)
{
    codol_player_fields_t next;
    unsigned slot, field;
    if (!out || !state) return 0;
    next=*out;
    for (slot=0; slot<CODOL_PERK_SLOTS; ++slot) {
        if (state->id[slot]>255) return 0;
        for (field=0; field<CODOL_PLAYER_FIELDS; ++field) {
            const codol_player_field_t *definition=CODOL_PlayerField(field);
            if (definition->offset!=0x4b0+4*slot) continue;
            if (definition->bits!=8 || definition->hint!=0) return 0;
            next.field[field]=state->id[slot];
            break;
        }
        if (field==CODOL_PLAYER_FIELDS) return 0;
    }
    *out=next; return 1;
}
