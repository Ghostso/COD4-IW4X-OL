/* SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_profile_updates.h"
#include <stdlib.h>
#include <string.h>

#define CLIENTS 32

/* The stored blob is [crc32(record)][record]. Every offset here is
 * record-relative, exactly like C1's dirty map, which starts at the record and
 * never describes the four CRC bytes the seal rewrites. */
#define RECORD_BASE 4u

typedef struct {
    uint8_t *image;                            /* record before the write */
    uint8_t dirty[CODOL_PROFILE_DIRTY_BYTES];  /* C1 +0x6a009 */
    uint8_t flag;                              /* C1 +0x6b009 */
} update_state_t;

static update_state_t updates[CLIENTS];

static update_state_t *state_for(unsigned client)
{
    return client < CLIENTS ? &updates[client] : NULL;
}

static size_t record_size(void)
{
    size_t size = CODOL_STATS_SIZE - RECORD_BASE;
    return size < CODOL_PROFILE_RECORD_SIZE ? size : CODOL_PROFILE_RECORD_SIZE;
}

/* The shared public view only: the session copy when a script has edited it,
 * otherwise the completed upload. The attached secure profile is never read. */
static const uint8_t *public_record(unsigned client)
{
    const uint8_t *blob = CODOL_ClientStats(client);
    return blob ? blob + RECORD_BASE : NULL;
}

static void drop_image(update_state_t *s)
{
    free(s->image);
    s->image = NULL;
}

static uint32_t map_word(const uint8_t *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 |
           (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

void CODOL_ResetProfileUpdates(unsigned client)
{
    update_state_t *s = state_for(client);
    if(!s) return;
    drop_image(s);
    memset(s->dirty, 0, sizeof(s->dirty));
    s->flag = 0;
}

void CODOL_ProfileUploadReplaced(unsigned client)
{
    update_state_t *s = state_for(client);
    if(!s) return;
    /* 0x5cf933 clears the 0x1000-byte map when the received mask completes and
     * stops there; the flag byte sits immediately past that memset. */
    memset(s->dirty, 0, sizeof(s->dirty));
    drop_image(s);
}

int CODOL_BeginProfileUpdate(unsigned client)
{
    update_state_t *s = state_for(client);
    const uint8_t *record = s ? public_record(client) : NULL;
    size_t size = record_size();
    if(!record) return 0;
    if(!s->image) {
        s->image = (uint8_t *)malloc(size);
        if(!s->image) return 0;
    }
    memcpy(s->image, record, size);
    return 1;
}

size_t CODOL_MarkProfileWrite(unsigned client, size_t offset, size_t length)
{
    update_state_t *s = state_for(client);
    const uint8_t *record = s ? public_record(client) : NULL;
    size_t i, size = record_size(), marked = 0;
    if(!record) return 0;
    if(offset >= size || length > size - offset) return 0;
    /* C1 raises the flag after the setter returns, whether or not any byte
     * changed (0x553788 follows the call at 0x553772 unconditionally). */
    s->flag = 1;
    if(!s->image) return 0;
    for(i = offset; i < offset + length; ++i) {
        /* 0x61f640: a byte equal to what is already stored is not written and
         * not marked. */
        if(record[i] == s->image[i]) continue;
        s->dirty[i >> 3] |= (uint8_t)(1u << (i & 7u));
        s->image[i] = record[i];
        ++marked;
    }
    return marked;
}

size_t CODOL_MarkProfileField(unsigned client, const codol_structured_layout_t *layout,
                              const codol_structured_field_t *field, size_t text_length)
{
    uint32_t address;
    size_t offset, width;
    unsigned kind;
    if(!layout || !field || !layout->offset_map || layout->offset_map_size % 4)
        return 0;
    if(field->logical_index >= layout->offset_map_size / 4) return 0;
    kind = (unsigned)field->type.kind;
    address = map_word(layout->offset_map + (size_t)field->logical_index * 4);
    switch(kind) {
    case 0: case 8: offset = address; width = 4; break;   /* int32, float32 */
    case 9:         offset = address; width = 2; break;   /* short */
    case 1:         offset = address; width = 1; break;   /* byte */
    case 2:         offset = address >> 3; width = 1; break; /* bool: bit slot */
    case 4:         offset = field->mapped_address; width = 2; break; /* enum */
    case 3:         /* string, written with its terminator */
        if(text_length >= field->type.index) return 0;
        offset = field->mapped_address;
        width = text_length + 1;
        break;
    default: return 0;
    }
    return CODOL_MarkProfileWrite(client, offset, width);
}

int CODOL_ProfileUpdatePending(unsigned client)
{
    const update_state_t *s = state_for(client);
    return s ? s->flag != 0 : 0;
}

const uint8_t *CODOL_ProfileUpdateDirtyMap(unsigned client, size_t *size)
{
    const update_state_t *s = state_for(client);
    if(!s) return NULL;
    if(size) *size = CODOL_PROFILE_DIRTY_BYTES;
    return s->dirty;
}

int CODOL_ProfileUpdateNextRange(unsigned client, size_t from,
                                 size_t *offset, size_t *length)
{
    const update_state_t *s = state_for(client);
    size_t i, start, size = record_size();
    if(!s || !offset || !length) return 0;
    for(i = from; i < size; ++i)
        if((s->dirty[i >> 3] >> (i & 7u)) & 1u) break;
    if(i >= size) return 0;
    start = i;
    while(i < size && ((s->dirty[i >> 3] >> (i & 7u)) & 1u)) ++i;
    *offset = start;
    *length = i - start;
    return 1;
}
