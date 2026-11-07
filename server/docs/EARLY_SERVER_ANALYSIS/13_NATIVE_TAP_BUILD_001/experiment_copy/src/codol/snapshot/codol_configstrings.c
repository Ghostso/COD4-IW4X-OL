/* Derived from alpha0022's active build_configstring_block/build_gamestate,
 * with 1.1.1.13 settings from 2-START-GAMESERVER.cmd (no IW4 section counts).
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_configstrings.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

int CODOL_ConstConfigChecksum(const char *zone_type, uint32_t *checksum)
{
    uint32_t value;
    if (!zone_type || !checksum) return 0;
    /* Active FS_CRC_BY_ZONE_TYPE in alpha0022/zone_crc.py. The zm measurement
     * was added after that file's introductory "unknown" paragraph. */
    if (!strcmp(zone_type, "mp")) value = UINT32_C(0xad1e1713);
    else if (!strcmp(zone_type, "coop")) value = UINT32_C(0xe8139f9b);
    else if (!strcmp(zone_type, "zm")) value = UINT32_C(0x801cef02);
    else return 0;
    *checksum = value; return 1;
}

void CODOL_ClearConfigstrings(codol_configstrings_t *state)
{
    unsigned i;
    if (!state) return;
    for (i = 0; i < CODOL_MAX_CONFIGSTRINGS; ++i) free(state->values[i]);
    memset(state, 0, sizeof(*state));
}

int CODOL_SetConfigstring(codol_configstrings_t *state, unsigned index, const char *value)
{
    char *copy = NULL;
    size_t size = value ? strlen(value) + 1 : 0;
    size_t old;
    if (!state || index >= CODOL_MAX_CONFIGSTRINGS) return 0;
    old = state->values[index] ? strlen(state->values[index]) + 1 : 0;
    if (size > SIZE_MAX - (state->bytes - old)) return 0;
    if (value) {
        copy = malloc(size);
        if (!copy) return 0;
        memcpy(copy, value, size);
    }
    free(state->values[index]); state->values[index] = copy;
    state->count = state->count - !!old + !!size;
    state->bytes = state->bytes - old + size;
    return 1;
}

const char *CODOL_GetConfigstring(const codol_configstrings_t *state, unsigned index)
{
    return state && index < CODOL_MAX_CONFIGSTRINGS ? state->values[index] : NULL;
}

const char *CODOL_GetEffectiveConfigstring(const codol_configstrings_t *overrides,
    const codol_configstrings_t *inherited, unsigned index)
{
    const char *value = CODOL_GetConfigstring(overrides, index);
    return value ? value : CODOL_GetConfigstring(inherited, index);
}

int CODOL_ConfigstringPoolSize(const codol_configstrings_t *overrides,
    const codol_configstrings_t *inherited, size_t *bytes)
{
    size_t total = 1;
    unsigned i;
    if (!overrides) return 0;
    for (i = 0; i < CODOL_MAX_CONFIGSTRINGS; ++i) {
        const char *value = overrides->values[i];
        size_t length, remaining;
        if (!value && inherited) value = inherited->values[i];
        if (!value || !*value) continue;
        remaining = CODOL_CONFIGSTRING_POOL_BYTES - total;
        /* Reserve one byte for this value's NUL without overflowing a size
         * calculation, and stop scanning once the client capacity is exceeded. */
        for (length = 0; length < remaining && value[length]; ++length) {}
        if (length == remaining) return 0;
        total += length + 1;
    }
    if (bytes) *bytes = total;
    return 1;
}

int CODOL_ImportConstantConfigstrings(codol_configstrings_t *out,size_t rows,const char *const *cells)
{
    codol_configstrings_t result={0}; size_t i;
    if(!out || rows>CODOL_MAX_CONFIGSTRINGS || (rows && !cells)) return 0;
    for(i=0;i<rows;++i) {
        const unsigned char *p=(const unsigned char *)cells[2*i]; unsigned index=0;
        if(!p || !*p || !cells[2*i+1]) goto fail;
        for(;*p;++p) {
            /* The overflow guard compares an unsigned running index against a
             * signed expression; make the bound unsigned so the comparison has
             * one signedness. The value is always in range: the digit is 0..9
             * and CODOL_MAX_CONFIGSTRINGS is far larger. */
            if(*p<'0' || *p>'9' ||
               index>(unsigned)(CODOL_MAX_CONFIGSTRINGS-1-(*p-'0'))/10u) goto fail;
            index=index*10+(*p-'0');
        }
        if(result.values[index] || !CODOL_SetConfigstring(&result,index,cells[2*i+1])) goto fail;
    }
    CODOL_ClearConfigstrings(out); *out=result; return 1;
fail:
    CODOL_ClearConfigstrings(&result); return 0;
}
static int register_inherited_name(codol_configstrings_t *overrides,const codol_configstrings_t *inherited,
    const char *name,unsigned first,unsigned count,size_t limit,int token)
{
    unsigned slot,available=0; size_t length=0;
    if(!overrides || !inherited || overrides==inherited || !name) return -1;
    if(!*name) return 0;
    while(name[length] && length<limit) {
        unsigned char c=(unsigned char)name[length++];
        if(token && (c<=32 || c==127 || c=='"' || c==';' || c=='\\')) return -1;
    }
    if(length==limit) return -1;
    for(slot=1;slot<count;++slot) {
        const char *base=inherited->values[first+slot],*changed=overrides->values[first+slot];
        const char *effective=changed ? changed : base;
        if(effective && !strcmp(effective,name)) return (int)slot;
        if(!available && (!base || !*base) && (!changed || !*changed)) available=slot;
    }
    if(!available || !CODOL_SetConfigstring(overrides,first+available,name)) return -1;
    return (int)available;
}
int CODOL_RegisterHudMaterial(codol_configstrings_t *overrides,const codol_configstrings_t *inherited,const char *name)
{ return register_inherited_name(overrides,inherited,name,CODOL_CS_MATERIALS,CODOL_HUD_MATERIAL_SLOTS,64,1); }
int CODOL_RegisterLocalizedString(codol_configstrings_t *overrides,const codol_configstrings_t *inherited,const char *text)
{ return register_inherited_name(overrides,inherited,text,CODOL_CS_LOCALIZEDSTRINGS,CODOL_LOCALIZED_SLOTS,1024,0); }
int CODOL_RegisterEffectName(codol_configstrings_t *overrides,const codol_configstrings_t *inherited,const char *name)
{ return register_inherited_name(overrides,inherited,name,CODOL_CS_EFFECTS,CODOL_EFFECT_SLOTS,64,1); }
int CODOL_RegisterByteEffectName(codol_configstrings_t *overrides,const codol_configstrings_t *inherited,const char *name)
{ return register_inherited_name(overrides,inherited,name,CODOL_CS_EFFECTS,CODOL_BYTE_EFFECT_SLOTS,64,1); }
int CODOL_RegisterTaggedEffect(codol_configstrings_t *overrides,const codol_configstrings_t *inherited,unsigned effect,const char *tag)
{
    char value[1024]; int length;
    if(!effect || effect>=CODOL_EFFECT_SLOTS || !tag || !*tag) return -1;
    /* C1 543e42..543e4c formats c576e0 "%03d%s", then searches
     * slots1..255 and publishes CS3971+slot at543f21..543f2a. */
    length=snprintf(value,sizeof(value),"%03u%s",effect,tag);
    if(length<0 || (size_t)length>=sizeof(value)) return -1;
    return register_inherited_name(overrides,inherited,value,CODOL_CS_TAGGED_EFFECTS,
        CODOL_TAGGED_EFFECT_SLOTS,sizeof(value),1);
}
static int register_asset_name(codol_configstrings_t *state, const char *name,
                               unsigned first, unsigned count)
{
    unsigned slot, available = 0;
    size_t length = 0;
    if (!state || !name) return -1;
    if (!*name) return 0;
    while (name[length] && length < 64) {
        if ((unsigned char)name[length] < 32 || name[length] == 127) return -1;
        ++length;
    }
    if (length == 64) return -1;
    for (slot = 1; slot < count; ++slot) {
        const char *old = state->values[first + slot];
        if (old && !strcmp(old, name)) return slot;
        if (!available && (!old || !*old)) available = slot;
    }
    if (!available || !CODOL_SetConfigstring(state, first + available, name)) return -1;
    return available;
}

int CODOL_RegisterModelName(codol_configstrings_t *state, const char *name)
{
    return register_asset_name(state, name, CODOL_CS_MODELS, CODOL_MODEL_SLOTS);
}
int CODOL_RegisterTagName(codol_configstrings_t *state, const char *name)
{
    return register_asset_name(state, name, CODOL_CS_TAGS, CODOL_TAG_SLOTS);
}
/* Model and tag banks are inherited with the fastfile just like effects.
 * Allocate only truly unused slots; never overwrite an inherited entry while
 * an entity or archived snapshot can still refer to its numeric index. */
static const codol_configstrings_t empty_asset_inheritance;
int CODOL_RegisterInheritedModelName(codol_configstrings_t *state,
    const codol_configstrings_t *inherited, const char *name)
{
    return register_inherited_name(state, inherited ? inherited : &empty_asset_inheritance,
        name, CODOL_CS_MODELS, CODOL_MODEL_SLOTS, 64, 1);
}
int CODOL_RegisterInheritedTagName(codol_configstrings_t *state,
    const codol_configstrings_t *inherited, const char *name)
{
    return register_inherited_name(state, inherited ? inherited : &empty_asset_inheritance,
        name, CODOL_CS_TAGS, CODOL_TAG_SLOTS, 64, 1);
}

void CODOL_PlayerNameToken(char output[64], const char *name)
{
    unsigned n = 0;
    int separator = 0;
    if (!name) { output[0] = 0; return; }
    while (*name && n < 63) {
        unsigned char c = (unsigned char)*name++;
        if (c <= 32 || c == 127 || c == '"' || c == '\\' || c == '/' || c == ';') {
            separator = n != 0;
            continue;
        }
        if (separator && n < 63) output[n++] = '_';
        separator = 0;
        if (n < 63) output[n++] = c;
    }
    if (!n) { memcpy(output, "Player", 7); return; }
    output[n] = 0;
}

int CODOL_SetPlayerNames(codol_configstrings_t *state, unsigned count, const char *const *names)
{
    char *pending[CODOL_PLAYERNAME_SLOTS] = {0};
    unsigned i;
    if (!state || count > CODOL_PLAYERNAME_SLOTS || (count && !names)) return 0;
    for (i = 0; i < CODOL_PLAYERNAME_SLOTS; ++i) {
        const char *name = i < count && names[i] ? names[i] : "";
        size_t length = 0;
        while (length < 63 && name[length]) ++length;
        pending[i] = malloc(length + 1);
        if (!pending[i]) goto fail;
        memcpy(pending[i], name, length); pending[i][length] = 0;
    }
    for (i = 0; i < CODOL_PLAYERNAME_SLOTS; ++i) {
        unsigned index = CODOL_CS_PLAYERNAMES + i;
        if (state->values[index]) state->bytes -= strlen(state->values[index]) + 1;
        else ++state->count;
        free(state->values[index]); state->values[index] = pending[i];
        state->bytes += strlen(pending[i]) + 1;
    }
    return 1;
fail:
    for (i = 0; i < CODOL_PLAYERNAME_SLOTS; ++i) free(pending[i]);
    return 0;
}

int CODOL_SetReplicatedDvars(codol_configstrings_t *state, unsigned count,
                            const char *const *names, const char *const *values)
{
    char *pending[400] = {0};
    unsigned i, j;
    if (!state || count > CODOL_MAX_REPLICATED_DVARS || (count && (!names || !values))) return 0;
    /* Allocate/validate before changing the bank, so a failed replacement is atomic. */
    for (i = 0; i < count; ++i) {
        if (!names[i] || !*names[i] || !values[i]) goto fail;
        for (j = 0; j < i; ++j) if (!strcmp(names[i], names[j])) goto fail;
        pending[i] = malloc(strlen(names[i]) + 1);
        pending[i+200] = malloc(strlen(values[i]) + 1);
        if (!pending[i] || !pending[i+200]) goto fail;
        strcpy(pending[i], names[i]); strcpy(pending[i+200], values[i]);
    }
    /* Publish explicit empties in the tail: clients may inherit const names there.
     * The client stops at the first empty name and pairs values with name + 200. */
    for (i = count; i < 200; ++i) {
        pending[i] = calloc(1, 1); pending[i+200] = calloc(1, 1);
        if (!pending[i] || !pending[i+200]) goto fail;
    }
    for (i = 0; i < 400; ++i) {
        unsigned index = CODOL_CS_DVAR_NAMES + i;
        if (state->values[index]) state->bytes -= strlen(state->values[index]) + 1;
        else ++state->count;
        free(state->values[index]); state->values[index] = pending[i];
        state->bytes += strlen(pending[i]) + 1;
    }
    return 1;
fail:
    for (i = 0; i < 400; ++i) free(pending[i]);
    return 0;
}

int CODOL_WriteConfigstrings(codol_msg_t *msg, const codol_configstrings_t *state)
{
    unsigned i;
    if (!msg || !state) return 0;
    /* The reference emits this as a fresh substream, independently of any
     * preceding message's partially filled bit pool. */
    msg->bit = 0;
    CODOL_WriteByte(msg, 3);
    CODOL_WriteShort(msg, state->count);
    for (i = 0; i < CODOL_MAX_CONFIGSTRINGS; ++i) {
        if (!state->values[i]) continue;
        CODOL_WriteBits(msg, 0, 1); /* absolute index */
        CODOL_WriteBits(msg, i, 13);
        CODOL_WriteString(msg, state->values[i]);
    }
    CODOL_WriteByte(msg, 5); /* gamestate command block terminator */
    return !msg->failed;
}

int CODOL_WriteGamestate(codol_msg_t *msg, const codol_configstrings_t *state,
                         const char *map, const char *zone_type, uint32_t const_crc,
                         uint32_t command_sequence, uint32_t client_number,
                         uint32_t checksum_feed)
{
    if (!msg || !state || !map || !*map || !zone_type ||
        (strcmp(zone_type, "mp") && strcmp(zone_type, "coop") && strcmp(zone_type, "zm"))) {
        if (msg) msg->failed = 1;
        return 0;
    }
    CODOL_WriteByte(msg, 2);
    CODOL_WriteLong(msg, command_sequence);
    CODOL_WriteString(msg, map);
    CODOL_WriteString(msg, zone_type);
    CODOL_WriteLong(msg, const_crc);
    if (!CODOL_WriteConfigstrings(msg, state)) return 0;
    CODOL_WriteLong(msg, client_number);
    CODOL_WriteLong(msg, checksum_feed);
    CODOL_WriteByte(msg, 5);
    return !msg->failed;
}
