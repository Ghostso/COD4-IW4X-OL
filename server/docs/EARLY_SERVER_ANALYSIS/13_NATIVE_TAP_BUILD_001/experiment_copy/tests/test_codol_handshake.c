#include "codol_handshake.h"
#include "codol_connect.h"
#include "codol_crypto.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static int rng(void *ctx, unsigned char *p, size_t n)
{ unsigned *s = ctx; while(n--) { *s = *s * 1664525u + 1013904223u; *p++ = *s >> 24; } return 0; }
int main(void)
{
    codol_handshake_t s = {0}, before;
    codol_association_t peer;
    uint8_t init[16] = {1,2,0,0,0,0,0x78,0x56,1,2,3,4,5,6,7,8};
    uint8_t ip[4] = {127,0,0,1}, private_key[28] = {0}, peer_private[28] = {0};
    uint8_t ack[38], expected[38] = {2,2,0x78,0x56}, echo[189] = {3,2,0x34,0x12};
    uint8_t reply[114], bad[189], saved[114], security[16] = {7}, x[28];
    uint8_t plain[80], encrypted[100], decoded[80];
    unsigned seed = 1; size_t i, n, length;
    private_key[27] = 1; peer_private[27] = 2;
    expected[14] = expected[16] = 0x34; expected[15] = expected[17] = 0x12;
    expected[18] = 0x78; expected[19] = 0x56;
    memcpy(expected + 24, ip, 4); expected[28] = 0x31; expected[29] = 0x75;
    memcpy(expected + 30, init + 8, 8);
    assert(CODOL_HandshakeInit(&s, ack, init, 16, init + 8, ip, 30001, 0x1234, private_key, rng, &seed) == 1);
    assert(!memcmp(ack, expected, 38) && s.pending && !s.established);
    before = s;
    assert(CODOL_HandshakeInit(&s, ack, init, 16, init + 8, ip, 30001, 1, NULL, NULL, NULL) == 2);
    assert(!memcmp(&s, &before, sizeof(s)));
    memcpy(echo + 6, ack, 38); memcpy(echo + 81, init + 8, 8);
    assert(CODOL_ExportPublicKey(echo + 89, peer_private, rng, &seed));
    memset(reply, 0xa5, sizeof(reply)); memcpy(saved, reply, sizeof(reply));
    /* Every byte of the issued cookie is checked, including its address/ID. */
    for (i = 0; i < 38; ++i) {
        memcpy(bad, echo, 189); bad[6 + i] ^= 1;
        assert(!CODOL_HandshakeCookie(&s, reply, bad, 189, security, rng, &seed));
        assert(!memcmp(&s, &before, sizeof(s)) && !memcmp(reply, saved, 114));
    }
    { const size_t corrupt[] = {0,1,2,4,81,89};
      for (i = 0; i < sizeof(corrupt)/sizeof(corrupt[0]); ++i) {
        memcpy(bad, echo, 189); bad[corrupt[i]] ^= 1;
        assert(!CODOL_HandshakeCookie(&s, reply, bad, 189, security, rng, &seed));
        assert(!memcmp(&s, &before, sizeof(s)) && !memcmp(reply, saved, 114));
      }
    }
    assert(!CODOL_HandshakeCookie(&s, reply, echo, 188, security, rng, &seed));
    assert(CODOL_HandshakeCookie(&s, reply, echo, 189, security, rng, &seed) == 1);
    assert(s.established && !s.pending && !memcmp(reply, "\x04\x02\x78\x56\0\0", 6));
    assert(!memcmp(reply + 106, init + 8, 8));
    for (i = 0; i < 28; ++i) assert(!s.private_key[i]);
    /* Peer consumes the actual COOKIE_ACK key and exchanges encrypted OOB. */
    assert(CODOL_SharedSecret(x, reply + 6, peer_private, rng, &seed));
    assert(CODOL_AssociationStart(&peer, x, security, 0x5678, 0x1234));
    n = CODOL_WriteChallengeResponse(plain, sizeof(plain), 12345);
    length = CODOL_AssociationSeal(&s.data, encrypted, sizeof(encrypted), plain, n);
    assert(CODOL_AssociationOpen(&peer, decoded, sizeof(decoded), &length, encrypted, length, NULL));
    assert(length == n && !memcmp(decoded, plain, n));
    length = CODOL_AssociationSeal(&peer, encrypted, sizeof(encrypted), plain, n);
    assert(CODOL_AssociationOpen(&s.data, decoded, sizeof(decoded), &length, encrypted, length, NULL));
    before = s; memcpy(saved, reply, 114);
    assert(CODOL_HandshakeCookie(&s, reply, echo, 189, NULL, NULL, NULL) == 2);
    assert(!memcmp(&s, &before, sizeof(s)) && !memcmp(reply, saved, 114));
    memcpy(bad, echo, 189); bad[44] ^= 1;
    assert(!CODOL_HandshakeCookie(&s, reply, bad, 189, security, rng, &seed));
    assert(!memcmp(&s, &before, sizeof(s)));
    init[6] ^= 1;
    memset(peer_private, 0, 28);
    assert(!CODOL_HandshakeInit(&s, ack, init, 16, init + 8, ip, 30001, 0x1235, peer_private, rng, &seed));
    assert(!memcmp(&s, &before, sizeof(s)));
    memcpy(bad, init, 16); bad[8] ^= 1;
    assert(!CODOL_HandshakeInit(&s, ack, bad, 16, init + 8, ip, 30001, 0x1235, private_key, rng, &seed));
    assert(!memcmp(&s, &before, sizeof(s)));
    assert(CODOL_HandshakeInit(&s, ack, init, 16, init + 8, ip, 30001, 0x1235, private_key, rng, &seed) == 1);
    assert(s.pending && !s.established && !s.data.active);
    CODOL_HandshakeClear(&s); memset(&before, 0, sizeof(before));
    assert(!memcmp(&s, &before, sizeof(s)));
    puts("CoDOL cookie handshake, peer ECDH DATA exchange and retransmissions passed");
    return 0;
}
