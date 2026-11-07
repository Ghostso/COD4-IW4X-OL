/* Shared by CoDOL usercmds, gamestate and snapshot serialization.
 * A bit-pool byte is reserved at the byte cursor, then filled/read later;
 * whole-byte fields NEVER align or reset that pool.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_msg.h"
#include <string.h>

void CODOL_MsgReadInit(codol_msg_t *m, const void *data, size_t size)
{
    memset(m, 0, sizeof(*m));
    m->data = (uint8_t *)data; m->size = m->capacity = size;
    if (!data && size) m->failed = 1;
}

void CODOL_MsgWriteInit(codol_msg_t *m, void *data, size_t capacity)
{
    memset(m, 0, sizeof(*m)); m->data = data; m->capacity = capacity;
    if (!data && capacity) m->failed = 1;
}

int CODOL_ReadData(codol_msg_t *m, void *out, size_t size)
{
    if (m->failed || m->cursor > m->size || size > m->size - m->cursor ||
        (!out && size)) { m->failed = 1; return 0; }
    if (size) memcpy(out, m->data + m->cursor, size);
    m->cursor += size; return 1;
}

static uint32_t read_integer(codol_msg_t *m, unsigned count)
{
    uint8_t bytes[4]; uint32_t value = 0; unsigned i;
    if (!CODOL_ReadData(m, bytes, count)) return 0;
    for (i = 0; i < count; ++i) value |= (uint32_t)bytes[i] << (8 * i);
    return value;
}

uint32_t CODOL_ReadByte(codol_msg_t *m) { return read_integer(m, 1); }
uint32_t CODOL_ReadShort(codol_msg_t *m) { return read_integer(m, 2); }
uint32_t CODOL_ReadLong(codol_msg_t *m) { return read_integer(m, 4); }

uint32_t CODOL_ReadBits(codol_msg_t *m, unsigned bits)
{
    unsigned i; uint32_t value = 0;
    if (m->failed || bits > 32) { m->failed = 1; return 0; }
    for (i = 0; i < bits; ++i) {
        if (!(m->bit & 7)) {
            if (m->cursor >= m->size || m->cursor > SIZE_MAX / 8) {
                m->failed = 1; return 0;
            }
            m->bit = m->cursor++ * 8;
        }
        if (m->bit / 8 >= m->size) { m->failed = 1; return 0; }
        value |= (uint32_t)((m->data[m->bit / 8] >> (m->bit & 7)) & 1) << i;
        ++m->bit;
    }
    return value;
}

void CODOL_WriteData(codol_msg_t *m, const void *data, size_t size)
{
    if (m->failed || m->size > m->capacity || size > m->capacity - m->size ||
        (!data && size)) { m->failed = 1; return; }
    if (size) memcpy(m->data + m->size, data, size);
    m->size += size;
}

static void write_integer(codol_msg_t *m, uint32_t value, unsigned count)
{
    uint8_t bytes[4]; unsigned i;
    for (i = 0; i < count; ++i) bytes[i] = (uint8_t)(value >> (8 * i));
    CODOL_WriteData(m, bytes, count);
}
void CODOL_WriteByte(codol_msg_t *m, uint32_t v) { write_integer(m, v, 1); }
void CODOL_WriteShort(codol_msg_t *m, uint32_t v) { write_integer(m, v, 2); }
void CODOL_WriteLong(codol_msg_t *m, uint32_t v) { write_integer(m, v, 4); }

void CODOL_WriteBits(codol_msg_t *m, uint32_t value, unsigned bits)
{
    unsigned i;
    if (m->failed || bits > 32) { m->failed = 1; return; }
    for (i = 0; i < bits; ++i) {
        if (!(m->bit & 7)) {
            if (m->size >= m->capacity || m->size > SIZE_MAX / 8) {
                m->failed = 1; return;
            }
            m->bit = m->size * 8; m->data[m->size++] = 0;
        }
        if (m->bit / 8 >= m->size) { m->failed = 1; return; }
        m->data[m->bit / 8] |= ((value >> i) & 1) << (m->bit & 7);
        ++m->bit;
    }
}

void CODOL_WriteString(codol_msg_t *m, const char *text)
{
    if (!text) { m->failed = 1; return; }
    CODOL_WriteData(m, text, strlen(text) + 1);
}
