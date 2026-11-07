#include "codol_wire_codec.h"
#include <stdio.h>
#include <string.h>
#include <assert.h>

int main(void)
{
    printf("=== test_wire_codec ===\n");

    uint8_t data[] = {0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0};
    codol_bitstream_t bs;
    codol_bitstream_init(&bs, data, sizeof(data));

    assert(!codol_bitstream_eof(&bs));
    assert(codol_bitstream_remaining(&bs) == 8);

    uint8_t b0 = codol_bitstream_read_byte(&bs);
    assert(b0 == 0x12);

    uint8_t b1 = codol_bitstream_read_byte(&bs);
    assert(b1 == 0x34);

    uint16_t s = codol_bitstream_read_short(&bs);
    assert(s == 0x5678);

    uint32_t l = codol_bitstream_read_long(&bs);
    assert(l == 0x9ABCDEF0);

    assert(codol_bitstream_eof(&bs));

    codol_bitstream_init(&bs, data, 1);
    uint8_t val = codol_bitstream_read_byte(&bs);
    assert(val == 0x12);
    assert(codol_bitstream_eof(&bs));

    uint8_t val2 = codol_bitstream_read_byte(&bs);
    assert(val2 == 0);

    codol_session_t session;
    memset(&session, 0, sizeof(session));
    codol_message_t msg;

    uint8_t packet[] = {0x00, 0x00, 0x00, 0x01, 0x00, 0x02, 0xAA, 0xBB};
    codol_result_t result = codol_wire_decode(&session, packet, sizeof(packet), &msg);
    assert(result == CODOL_OK);
    assert(msg.header.sequence == 1);
    assert(msg.header.opcode == 0x0002);
    assert(msg.header.payload_len == 2);

    result = codol_wire_decode(&session, packet, 2, &msg);
    assert(result == CODOL_ERR_WIRE_REJECT);

    uint8_t out[16];
    size_t out_len;
    session.netchan.outgoing_sequence = 0x12345678;
    result = codol_wire_encode_header(&session, 0x0003, out, sizeof(out), &out_len);
    assert(result == CODOL_OK);
    assert(out_len == 6);
    assert(out[0] == 0x12);
    assert(out[1] == 0x34);
    assert(out[4] == 0x00);
    assert(out[5] == 0x03);

    printf("All wire codec tests PASSED.\n");
    return 0;
}
