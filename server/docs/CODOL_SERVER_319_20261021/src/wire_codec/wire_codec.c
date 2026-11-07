#include "codol_wire_codec.h"
#include <string.h>
#include <stdio.h>

void codol_bitstream_init(codol_bitstream_t *bs, const uint8_t *data, size_t len)
{
    memset(bs, 0, sizeof(*bs));
    bs->data = data;
    bs->len = len;
    bs->pos = 0;
    bs->bit_pos = 0;
}

uint32_t codol_bitstream_read_bits(codol_bitstream_t *bs, int count)
{
    if (!bs || count <= 0 || count > 32) return 0;
    if (codol_bitstream_remaining(bs) < (size_t)((count + 7) / 8)) return 0;

    uint32_t value = 0;
    for (int i = 0; i < count; i++) {
        size_t byte_idx = bs->pos + (bs->bit_pos + i) / 8;
        int bit_idx = 7 - ((bs->bit_pos + i) % 8);
        if (byte_idx < bs->len) {
            value |= ((bs->data[byte_idx] >> bit_idx) & 1) << (count - 1 - i);
        }
    }
    bs->bit_pos += count;
    while (bs->bit_pos >= 8) {
        bs->pos++;
        bs->bit_pos -= 8;
    }
    return value;
}

uint8_t codol_bitstream_read_byte(codol_bitstream_t *bs)
{
    return (uint8_t)codol_bitstream_read_bits(bs, 8);
}

uint16_t codol_bitstream_read_short(codol_bitstream_t *bs)
{
    return (uint16_t)codol_bitstream_read_bits(bs, 16);
}

uint32_t codol_bitstream_read_long(codol_bitstream_t *bs)
{
    return codol_bitstream_read_bits(bs, 32);
}

void codol_bitstream_read_bytes(codol_bitstream_t *bs, uint8_t *out, size_t count)
{
    if (!bs || !out) return;
    for (size_t i = 0; i < count; i++) {
        out[i] = codol_bitstream_read_byte(bs);
    }
}

size_t codol_bitstream_remaining(const codol_bitstream_t *bs)
{
    if (!bs || bs->pos >= bs->len) return 0;
    return bs->len - bs->pos;
}

bool codol_bitstream_eof(const codol_bitstream_t *bs)
{
    return !bs || bs->pos >= bs->len;
}

codol_result_t codol_wire_decode(codol_session_t *session,
                                  const uint8_t *input, size_t input_len,
                                  codol_message_t *message)
{
    if (!session || !input || input_len == 0 || !message) return CODOL_ERR_INVALID_ARG;

    codol_bitstream_t bs;
    codol_bitstream_init(&bs, input, input_len);

    memset(message, 0, sizeof(*message));

    if (input_len < 4) {
        return CODOL_ERR_WIRE_REJECT;
    }

    message->header.sequence = codol_bitstream_read_long(&bs);
    message->header.opcode = codol_bitstream_read_short(&bs);
    message->header.payload = input + bs.pos;
    message->header.payload_len = input_len - bs.pos;

    (void)session;
    return CODOL_OK;
}

codol_result_t codol_wire_encode_header(codol_session_t *session,
                                         uint16_t opcode, uint8_t *out, size_t cap, size_t *out_len)
{
    if (!session || !out || cap < 6 || !out_len) return CODOL_ERR_INVALID_ARG;

    out[0] = (uint8_t)(session->netchan.outgoing_sequence >> 24);
    out[1] = (uint8_t)(session->netchan.outgoing_sequence >> 16);
    out[2] = (uint8_t)(session->netchan.outgoing_sequence >> 8);
    out[3] = (uint8_t)(session->netchan.outgoing_sequence);
    out[4] = (uint8_t)(opcode >> 8);
    out[5] = (uint8_t)(opcode);
    *out_len = 6;
    return CODOL_OK;
}
