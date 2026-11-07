/* Ported from alpha0022/netchan_fragment.py and dtls_crypto.extend_ctr16.
 * Evidence and limitations: docs/CODOL_PORT.md.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_wire.h"
#include <string.h>

static unsigned read16(const uint8_t *p)
{
    return (unsigned)p[0] | (unsigned)p[1] << 8;
}

static void write16(uint8_t *p, unsigned v)
{
    p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8);
}

static void write32(uint8_t *p, uint32_t v)
{
    write16(p, v); write16(p + 2, v >> 16);
}

size_t CODOL_WritePacket(uint8_t *out, size_t capacity, uint32_t sequence,
                        int qport, const uint8_t *message, size_t length,
                        unsigned index)
{
    size_t header = qport < 0 ? 4u : 6u;
    size_t offset, count, chunk;
    if (!out || (!message && length) || length > CODOL_MAX_MESSAGE ||
        sequence > CODOL_SEQUENCE_MASK || qport < -1 || qport > 65535)
        return 0;
    if (length < CODOL_FRAGMENT_SIZE) {
        if (index || capacity < header + length) return 0;
        write32(out, sequence);
        if (qport >= 0) write16(out + 4, (unsigned)qport);
        if (length) memcpy(out + header, message, length);
        return header + length;
    }
    count = (length + CODOL_FRAGMENT_SIZE - 1) / CODOL_FRAGMENT_SIZE;
    if (index >= count) return 0;
    offset = index * CODOL_FRAGMENT_SIZE;
    chunk = length - offset;
    if (chunk > CODOL_FRAGMENT_SIZE) chunk = CODOL_FRAGMENT_SIZE;
    if (capacity < header + 6 + chunk) return 0;
    write32(out, sequence | CODOL_FRAGMENT_BIT);
    if (qport >= 0) write16(out + 4, (unsigned)qport);
    out[header] = (uint8_t)index;
    out[header + 1] = (uint8_t)(count - 1);
    write16(out + header + 2, CODOL_FRAGMENT_SIZE);
    write16(out + header + 4, (unsigned)chunk);
    memcpy(out + header + 6, message + offset, chunk);
    return header + 6 + chunk;
}

int CODOL_ReadFragment(codol_fragments_t *s, uint8_t *buffer,
                       size_t capacity, uint32_t sequence, const uint8_t *data,
                       size_t length)
{
    unsigned index, last, stride, chunk, i;
    size_t offset;
    uint32_t bit;
    if (!s || !buffer || !data || !(sequence & CODOL_FRAGMENT_BIT))
        return CODOL_WIRE_INVALID;
    if (sequence & CODOL_ACK_BIT) return CODOL_WIRE_ACK;
    sequence &= CODOL_SEQUENCE_MASK;
    if (length < 6) return CODOL_WIRE_INVALID;
    index = data[0]; last = data[1];
    stride = read16(data + 2); chunk = read16(data + 4);
    offset = (size_t)index * stride;
    if (last >= CODOL_MAX_FRAGMENTS || index > last ||
        stride != CODOL_FRAGMENT_SIZE || !chunk || chunk > stride ||
        (index != last && chunk != stride) || length != 6u + chunk ||
        offset + chunk > capacity || (size_t)last * stride >= capacity)
        return CODOL_WIRE_INVALID;
    if (s->active && sequence < s->sequence) return CODOL_WIRE_WAIT;
    if (s->active && sequence == s->sequence &&
        (s->last != last || s->stride != stride)) return CODOL_WIRE_INVALID;
    if (!s->active || sequence != s->sequence) {
        memset(s, 0, sizeof(*s));
        s->active = 1; s->sequence = sequence;
        s->last = (uint8_t)last; s->stride = (uint16_t)stride;
    }
    bit = UINT32_C(1) << (index & 31);
    if (s->received[index >> 5] & bit) {
        if ((index == last && s->length != offset + chunk) ||
            memcmp(buffer + offset, data + 6, chunk)) return CODOL_WIRE_INVALID;
    } else {
        memcpy(buffer + offset, data + 6, chunk);
        s->received[index >> 5] |= bit;
        if (index == last) s->length = (uint32_t)(offset + chunk);
    }
    for (i = 0; i <= last; ++i)
        if (!(s->received[i >> 5] & (UINT32_C(1) << (i & 31))))
            return CODOL_WIRE_WAIT;
    return CODOL_WIRE_COMPLETE;
}

void CODOL_Xor(uint8_t *data, size_t length, uint8_t key,
               const uint8_t *command, size_t command_length)
{
    size_t i, j = 0;
    for (i = 0; i < length; ++i) {
        if (command && command_length) {
            if (j == command_length || !command[j]) j = 0;
            key ^= (uint8_t)(command[j++] << (i & 1));
        }
        data[i] ^= key;
    }
}

uint32_t CODOL_ExtendCounter(uint16_t wire, uint32_t last)
{
    uint32_t epoch = last >> 16;
    unsigned previous = last & 65535u;
    if (wire < previous && previous - wire > 32768u) ++epoch;
    else if (wire > previous && wire - previous > 32768u && epoch) --epoch;
    return (epoch << 16) | wire;
}
