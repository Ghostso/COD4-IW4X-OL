/* Native C1 replicated-dvar allocation; no retained IW3 configstring indices. */
#ifdef CODOL_SERVER
#include "server.h"
#include "codol_sv_state.h"
#include "codol_replicated_dvars.h"
#include <stdlib.h>
#include <string.h>

static const char *effective(const codol_configstrings_t *bank,
                             const codol_configstrings_t *inherited, unsigned index)
{
    const char *value = CODOL_GetConfigstring(bank, index);
    return value ? value : CODOL_GetConfigstring(inherited, index);
}

static void publish(unsigned index, const char *value)
{
    int i;
    if ((sv.state != SS_GAME && !sv.restarting) || !svs.clients || !sv_maxclients)
        return;
    for (i = 0; i < sv_maxclients->integer; ++i) {
        client_t *client = &svs.clients[i];
        if (client->state >= CS_PRIMED && client->gamestateSent)
            SV_SendServerCommandNoLoss(client, "d %u %s", index, value);
    }
}

int CODOL_PublishReplicatedDvar(const char *name, const char *value)
{
    codol_configstrings_t *bank = CODOL_ServerConfigstrings(), *staged;
    const codol_configstrings_t *inherited = CODOL_ServerInheritedConfigstrings();
    const char *old_name, *old_value;
    char *name_copy = NULL, *value_copy = NULL;
    unsigned slot, name_index, value_index;
    size_t name_bytes, value_bytes, old_bytes;
    int new_name;

    if (!name || !*name || !value ||
        (name_bytes = strlen(name) + 1) > CODOL_CONFIGSTRING_VALUE_CHARS + 1 ||
        (value_bytes = strlen(value) + 1) > CODOL_CONFIGSTRING_VALUE_CHARS + 1 ||
        strpbrk(name, " \t\r\n\"") || strpbrk(value, "\r\n")) return 0;
    /* Pre-map changes are republished by SV_SaveSystemInfo after constants load.
     * Allocating before then would hide the shipped names behind our first slot. */
    if (!inherited) return 1;

    /* C1 466020 walks names24..223 and values224..423, stopping at the
     * first empty name. Preserve inherited order and append only at its end. */
    for (slot = 0; slot < CODOL_MAX_REPLICATED_DVARS; ++slot) {
        old_name = effective(bank, inherited, CODOL_CS_DVAR_NAMES + slot);
        if (!old_name || !*old_name || !Q_stricmp(old_name, name)) break;
    }
    if (slot == CODOL_MAX_REPLICATED_DVARS) return 0;
    name_index = CODOL_CS_DVAR_NAMES + slot;
    value_index = CODOL_CS_DVAR_VALUES + slot;
    new_name = !old_name || !*old_name;
    old_value = effective(bank, inherited, value_index);
    if (!new_name && old_value && !strcmp(old_value, value)) return 1;

    staged = malloc(sizeof(*staged));
    value_copy = malloc(value_bytes);
    if (new_name) name_copy = malloc(name_bytes);
    if (!staged || !value_copy || (new_name && !name_copy)) goto fail;
    memcpy(value_copy, value, value_bytes);
    if (new_name) memcpy(name_copy, name, name_bytes);
    memcpy(staged, bank, sizeof(*staged));
    staged->values[value_index] = value_copy;
    if (new_name) staged->values[name_index] = name_copy;
    if (!CODOL_ConfigstringPoolSize(staged, inherited, NULL)) goto fail;
    free(staged);

    old_bytes = bank->values[value_index] ? strlen(bank->values[value_index]) + 1 : 0;
    bank->bytes = bank->bytes - old_bytes + value_bytes;
    if (!old_bytes) ++bank->count;
    free(bank->values[value_index]);
    bank->values[value_index] = value_copy;
    /* Send the value before revealing a newly allocated name: C1 reapplies
     * the complete bank on each update, so no dvar sees a stale slot value. */
    publish(value_index, value_copy);
    if (new_name) {
        old_bytes = bank->values[name_index] ? strlen(bank->values[name_index]) + 1 : 0;
        bank->bytes = bank->bytes - old_bytes + name_bytes;
        if (!old_bytes) ++bank->count;
        free(bank->values[name_index]);
        bank->values[name_index] = name_copy;
        publish(name_index, name_copy);
    }
    return 1;
fail:
    free(staged);
    free(value_copy);
    free(name_copy);
    return 0;
}
#endif
