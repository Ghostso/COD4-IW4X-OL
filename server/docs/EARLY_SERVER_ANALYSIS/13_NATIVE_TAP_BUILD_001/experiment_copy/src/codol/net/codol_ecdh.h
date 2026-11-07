/* CoDOL bdDTLS P-224 key exchange. SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_ECDH_H
#define CODOL_ECDH_H
#include <stddef.h>
#include <stdint.h>

/* Caller supplies a cryptographically random scalar (big endian) and RNG for
 * multiplication blinding. No fixed server key or process-global RNG is used.
 * Public keys use the client's 100-byte padded libtomcrypt export format.
 * All output buffers remain unchanged on failure. */
typedef int (*codol_ecdh_rng_t)(void *, unsigned char *, size_t);
int CODOL_ExportPublicKey(uint8_t out[100], const uint8_t private_key[28],
                          codol_ecdh_rng_t rng, void *rng_context);
int CODOL_SharedSecret(uint8_t out[28], const uint8_t peer[100],
                       const uint8_t private_key[28],
                       codol_ecdh_rng_t rng, void *rng_context);
#endif
