/* CoDOL 1.1.1.13 bdDTLS DATA records (not RFC DTLS).
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_CRYPTO_H
#define CODOL_CRYPTO_H
#include <stddef.h>
#include <stdint.h>

/* x is the 28-byte big-endian P-224 shared X coordinate. */
int CODOL_DeriveKey(uint8_t key[24], const uint8_t x[28], const uint8_t security[16]);
size_t CODOL_EncryptRecord(uint8_t *out, size_t capacity, const uint8_t *plain,
                           size_t length, uint32_t counter, uint16_t tag,
                           const uint8_t key[24]);
/* Verify MAC and exact length before decrypting. Outputs remain unchanged on
 * malformed/tag/MAC errors. Caller handles replay window and counter high-water.
 * Returns 1 on success, 0 on failure (including crypto backend failure). */
int CODOL_DecryptRecord(uint8_t *out, size_t capacity, size_t *plain_length,
                        uint32_t *counter, const uint8_t *record, size_t length,
                        uint32_t last_counter, uint16_t expected_tag,
                        const uint8_t key[24]);
#endif
