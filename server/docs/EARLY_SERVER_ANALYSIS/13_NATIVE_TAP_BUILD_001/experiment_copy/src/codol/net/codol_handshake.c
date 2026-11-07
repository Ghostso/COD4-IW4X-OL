/* SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_handshake.h"
#include <string.h>
static void erase(void *ptr, size_t n)
{ volatile uint8_t *p = ptr; while (n--) *p++ = 0; }
static uint16_t read16(const uint8_t *p)
{ return (uint16_t)(p[0] | (unsigned)p[1] << 8); }
static void write16(uint8_t *p, uint16_t n)
{ p[0] = n; p[1] = n >> 8; }
void CODOL_HandshakeClear(codol_handshake_t *s)
{ if (s) erase(s, sizeof(*s)); }
int CODOL_HandshakeInit(codol_handshake_t *s, uint8_t out[38],
    const uint8_t *packet, size_t n, const uint8_t id[8], const uint8_t ip[4],
    uint16_t port, uint16_t tag, const uint8_t private_key[28],
    codol_ecdh_rng_t rng, void *ctx)
{
    codol_handshake_t next = {0};
    if (!s || !out || !packet || !id || !ip || n != 16 ||
        packet[0] != 1 || packet[1] != 2 || read16(packet + 2) ||
        read16(packet + 4) || !read16(packet + 6) || memcmp(packet + 8, id, 8)) return 0;
    if ((s->pending || s->established) && !memcmp(s->init, packet, 16) &&
        !memcmp(s->init_ack + 24, ip, 4) && read16(s->init_ack + 28) == port) {
        memcpy(out, s->init_ack, 38); return 2;
    }
    if (!tag || !port || !private_key || !rng ||
        !CODOL_ExportPublicKey(next.public_key, private_key, rng, ctx)) {
        erase(&next, sizeof(next)); return 0;
    }
    memcpy(next.private_key, private_key, 28); memcpy(next.init, packet, 16);
    next.init_ack[0] = 2; next.init_ack[1] = 2;
    memcpy(next.init_ack + 2, packet + 6, 2);
    /* Stateful cookie: exact bytes are retained and compared on echo. */
    write16(next.init_ack + 14, tag); write16(next.init_ack + 16, tag);
    memcpy(next.init_ack + 18, packet + 6, 2);
    memcpy(next.init_ack + 24, ip, 4); write16(next.init_ack + 28, port);
    memcpy(next.init_ack + 30, id, 8); next.pending = 1;
    *s = next; memcpy(out, next.init_ack, 38);
    erase(&next, sizeof(next)); return 1;
}
int CODOL_HandshakeCookie(codol_handshake_t *s, uint8_t out[114],
    const uint8_t *packet, size_t n, const uint8_t security[16],
    codol_ecdh_rng_t rng, void *ctx)
{
    codol_association_t data = {0};
    uint8_t x[28] = {0}, ack[114] = {4, 2};
    int ok = 0;
    if (!s || !out || !packet || n != 189) return 0;
    if (s->established) {
        if (memcmp(s->echo, packet, 189)) return 0;
        memcpy(out, s->cookie_ack, 114); return 2;
    }
    if (!s->pending || !security || !rng || packet[0] != 3 || packet[1] != 2 ||
        read16(packet + 2) != read16(s->init_ack + 16) || read16(packet + 4) ||
        memcmp(packet + 6, s->init_ack, 38) || memcmp(packet + 81, s->init + 8, 8)) return 0;
    if (!CODOL_SharedSecret(x, packet + 89, s->private_key, rng, ctx) ||
        !CODOL_AssociationStart(&data, x, security, read16(s->init_ack + 16),
                               read16(s->init + 6))) goto done;
    memcpy(ack + 2, s->init + 6, 2); memcpy(ack + 6, s->public_key, 100);
    memcpy(ack + 106, s->init + 8, 8);
    s->data = data; memcpy(s->echo, packet, 189); memcpy(s->cookie_ack, ack, 114);
    s->pending = 0; s->established = 1; erase(s->private_key, 28);
    memcpy(out, ack, 114); ok = 1;
done:
    erase(x, sizeof(x)); CODOL_AssociationClear(&data);
    return ok;
}
