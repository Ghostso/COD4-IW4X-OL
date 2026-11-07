#include "codol_association.h"
#include "codol_crypto.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static void rejected(codol_association_t *s, const uint8_t *packet, size_t n,
                     const uint8_t *candidate)
{
    codol_association_t before = *s;
    uint8_t out[64], original[64];
    size_t size = 123;
    memset(out, 0xa5, sizeof(out)); memcpy(original, out, sizeof(out));
    assert(!CODOL_AssociationOpen(s, out, sizeof(out), &size, packet, n, candidate));
    assert(size == 123 && !memcmp(out, original, sizeof(out)));
    assert(!memcmp(s, &before, sizeof(before)));
}
int main(void)
{
    codol_association_t a = {0}, b = {0}, before;
    uint8_t x[28] = {1}, security[16] = {2}, next[16] = {3}, key[24];
    uint8_t packet[80], earlier[80], tampered[80], out[64], plain[17];
    size_t n, oldn, length;
    unsigned i;
    memset(plain, 0x42, sizeof(plain));
    assert(CODOL_AssociationStart(&a, x, security, 0x1234, 0x5678));
    assert(CODOL_AssociationStart(&b, x, security, 0x5678, 0x1234));
    n = CODOL_AssociationSeal(&a, packet, sizeof(packet), plain, sizeof(plain));
    assert(n == 33 && a.send_next == 2 && packet[4] == 1);
    assert(CODOL_AssociationOpen(&b, out, sizeof(out), &length, packet, n, NULL));
    assert(length == sizeof(plain) && !memcmp(out, plain, length));
    rejected(&b, packet, n, NULL);
    oldn = CODOL_AssociationSeal(&a, earlier, sizeof(earlier), plain, 1);
    n = CODOL_AssociationSeal(&a, packet, sizeof(packet), plain, 17);
    assert(a.send_next == 4); /* One counter per record, not per AES block. */
    assert(CODOL_AssociationOpen(&b, out, sizeof(out), &length, packet, n, NULL));
    assert(CODOL_AssociationOpen(&b, out, sizeof(out), &length, earlier, oldn, NULL));
    assert(b.receive_high == 3 && b.receive_window == 7);
    rejected(&b, earlier, oldn, NULL);

    n = CODOL_AssociationSeal(&a, packet, sizeof(packet), plain, 17);
    memcpy(tampered, packet, n); tampered[6] ^= 1;
    rejected(&b, tampered, n, next);
    memcpy(tampered, packet, n); tampered[2] ^= 1;
    rejected(&b, tampered, n, NULL);
    rejected(&b, packet, n - 1, NULL);
    assert(CODOL_AssociationOpen(&b, out, sizeof(out), &length, packet, n, NULL));

    /* Delay counter 5 to the last permitted position, then outside the window. */
    oldn = CODOL_AssociationSeal(&a, earlier, sizeof(earlier), plain, 1);
    for (i = 0; i < 31; ++i) {
        n = CODOL_AssociationSeal(&a, packet, sizeof(packet), plain, 1);
        assert(CODOL_AssociationOpen(&b, out, sizeof(out), &length, packet, n, NULL));
    }
    before = b;
    assert(b.receive_high == 36);
    assert(CODOL_AssociationOpen(&b, out, sizeof(out), &length, earlier, oldn, NULL));
    b = before;
    n = CODOL_AssociationSeal(&a, packet, sizeof(packet), plain, 1);
    assert(CODOL_AssociationOpen(&b, out, sizeof(out), &length, packet, n, NULL));
    rejected(&b, earlier, oldn, NULL);

    /* Reaching the 16-bit boundary uses the full counter for IV derivation. */
    a.send_next = 65534; b.receive_high = 65533; b.receive_window = 1;
    oldn = CODOL_AssociationSeal(&a, earlier, sizeof(earlier), plain, 17);
    for (i = 0; i < 3; ++i) {
        n = CODOL_AssociationSeal(&a, packet, sizeof(packet), plain, 17);
        assert(CODOL_AssociationOpen(&b, out, sizeof(out), &length, packet, n, NULL));
        assert(!memcmp(out, plain, 17));
    }
    assert(b.receive_high == 65537 && a.send_next == 65538);
    assert(CODOL_AssociationOpen(&b, out, sizeof(out), &length, earlier, oldn, NULL));

    /* Reused association: adopt a lobby candidate only on a valid MAC. */
    assert(CODOL_DeriveKey(key, x, next));
    n = CODOL_EncryptRecord(packet, sizeof(packet), plain, 17, 65538, b.local_tag, key);
    rejected(&b, packet, n, NULL);
    rejected(&b, packet, n, security);
    assert(CODOL_AssociationOpen(&b, out, sizeof(out), &length, packet, n, next));
    assert(!memcmp(b.key, key, 24) && b.receive_high == 65538);
    rejected(&b, packet, n, next);
    n = CODOL_AssociationSeal(&b, packet, sizeof(packet), plain, 17);
    assert(n && packet[4] == 1); /* Rotation does not reset either direction. */
    assert(CODOL_AssociationOpen(&a, out, sizeof(out), &length, packet, n, next));

    before = a;
    assert(!CODOL_AssociationSeal(&a, packet, 1, plain, 17));
    assert(!memcmp(&a, &before, sizeof(a)));
    a.send_next = UINT32_MAX;
    assert(CODOL_AssociationSeal(&a, packet, sizeof(packet), plain, 1));
    assert(a.send_exhausted);
    assert(!CODOL_AssociationSeal(&a, packet, sizeof(packet), plain, 1));
    assert(CODOL_AssociationStart(&a, x, security, 1, 2));
    assert(a.send_next == 1 && !a.received && !a.send_exhausted);
    /* With no receive history, the first wire counter is a raw uint16. */
    assert(CODOL_DeriveKey(key, x, security));
    n = CODOL_EncryptRecord(packet, sizeof(packet), plain, 17, 60000, 1, key);
    before = a; length = 123;
    assert(!CODOL_AssociationOpen(&a, out, 1, &length, packet, n, NULL));
    assert(length == 123 && !memcmp(&a, &before, sizeof(a)));
    assert(CODOL_AssociationOpen(&a, out, sizeof(out), &length, packet, n, NULL));
    assert(a.receive_high == 60000 && !memcmp(out, plain, 17));
    CODOL_AssociationClear(&a);
    memset(&before, 0, sizeof(before));
    assert(!memcmp(&a, &before, sizeof(a)));
    assert(!CODOL_AssociationSeal(&a, packet, sizeof(packet), plain, 1));
    puts("CoDOL association replay, rollover, key rotation and lifecycle passed");
    return 0;
}
