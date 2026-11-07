/* SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_HANDSHAKE_H
#define CODOL_HANDSHAKE_H
#include "codol_association.h"
#include "codol_ecdh.h"
#pragma pack(push, 8)
typedef struct {
    codol_association_t data;
    uint8_t init[16], init_ack[38], private_key[28], public_key[100];
    uint8_t echo[189], cookie_ack[114];
    unsigned pending, established;
} codol_handshake_t;
#pragma pack(pop)
void CODOL_HandshakeClear(codol_handshake_t *);
/* Owner binds this state to a UDP endpoint and supplies its trusted session ID,
 * fresh private scalar/local tag and RNG. Return 1 new, 2 retransmission, 0
 * rejected; failure preserves state/output. Caller clears the old game client
 * only on a successful new INIT. Duplicate INIT reuses the original cookie. */
int CODOL_HandshakeInit(codol_handshake_t *, uint8_t out[38],
    const uint8_t *, size_t, const uint8_t security_id[8], const uint8_t ip[4],
    uint16_t port, uint16_t local_tag, const uint8_t private_key[28],
    codol_ecdh_rng_t, void *);
/* Caller supplies the security key belonging to that trusted session ID.
 * Successful COOKIE_ECHO enables DATA MAC verification, not player identity.
 * An exact retransmission returns the cached ACK without resetting DATA. */
int CODOL_HandshakeCookie(codol_handshake_t *, uint8_t out[114],
    const uint8_t *, size_t, const uint8_t security_key[16], codol_ecdh_rng_t, void *);
#endif
