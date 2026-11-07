#ifndef CODOL_WIRE_CODEC_H
#define CODOL_WIRE_CODEC_H

#include "codol_types.h"

void           codol_bitstream_init(codol_bitstream_t *bs, const uint8_t *data, size_t len);
uint32_t       codol_bitstream_read_bits(codol_bitstream_t *bs, int count);
uint8_t        codol_bitstream_read_byte(codol_bitstream_t *bs);
uint16_t       codol_bitstream_read_short(codol_bitstream_t *bs);
uint32_t       codol_bitstream_read_long(codol_bitstream_t *bs);
void           codol_bitstream_read_bytes(codol_bitstream_t *bs, uint8_t *out, size_t count);
size_t         codol_bitstream_remaining(const codol_bitstream_t *bs);
bool           codol_bitstream_eof(const codol_bitstream_t *bs);

codol_result_t codol_wire_decode(codol_session_t *session,
                                  const uint8_t *input, size_t input_len,
                                  codol_message_t *message);
codol_result_t codol_wire_encode_header(codol_session_t *session,
                                         uint16_t opcode, uint8_t *out, size_t cap, size_t *out_len);

#endif /* CODOL_WIRE_CODEC_H */
