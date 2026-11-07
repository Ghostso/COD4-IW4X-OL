#include "codol_ecdh.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

/* Test-only deterministic blinding source. Production must supply a CSPRNG. */
static int rng(void *ctx, unsigned char *out, size_t size)
{
    unsigned *state = ctx;
    while (size--) { *state = *state * 1664525u + 1013904223u; *out++ = *state >> 24; }
    return 0;
}
static int fail_rng(void *ctx, unsigned char *out, size_t size)
{ (void)ctx; (void)out; (void)size; return -1; }
static void unhex(uint8_t *out, const char *s)
{
    unsigned x;
    while (*s) { assert(sscanf(s, "%2x", &x) == 1); *out++ = x; s += 2; }
}
int main(void)
{
    uint8_t a[28], b[28] = {0}, pa[100], pb[100], expected[100] = {0};
    uint8_t shared[28], other[28], expected_x[28], bad[100], before[100];
    unsigned state = 1;
    size_t i;
    for (i = 0; i < 28; ++i) a[i] = i + 1;
    b[27] = 2;
    /* Independent PyCryptodome P-224 vectors; exported with alpha0022's
     * documented DER format, including the sign byte on A's Y coordinate. */
    unhex(expected, "30440302070002011c021c627b7c0b3a2fb7a478ac5670e9973194a5fda0bc0791b07506a73ddd021d0099113b3fdea71bbff9921330d9ce980155eebd620c46be927c214543");
    assert(CODOL_ExportPublicKey(pa, a, rng, &state));
    assert(!memcmp(pa, expected, 100));
    memset(expected, 0, 100);
    unhex(expected, "30430302070002011c021c706a46dc76dcb76798e60e6d89474788d16dc18032d268fd1a704fa6021c1c2b76a7bc25e7702a704fa986892849fca629487acf3709d2e4e8bb");
    assert(CODOL_ExportPublicKey(pb, b, rng, &state));
    assert(!memcmp(pb, expected, 100));
    unhex(expected_x, "b4f2a5ed637f9ff7563471a2ca438897a04679bd4a6f8790f1bf16f1");
    assert(CODOL_SharedSecret(shared, pb, a, rng, &state));
    assert(CODOL_SharedSecret(other, pa, b, rng, &state));
    assert(!memcmp(shared, expected_x, 28) && !memcmp(shared, other, 28));
    /* Targeted corruptions cover structure, padding and point membership;
     * rejected inputs must leave the previous shared secret unchanged. */
    { const size_t offsets[] = {0, 1, 2, 4, 8, 9, 10, 11, 40, 68, 99};
      for (i = 0; i < sizeof(offsets)/sizeof(offsets[0]); ++i) {
        memcpy(bad, pb, 100); bad[offsets[i]] ^= 0x80;
        memcpy(other, shared, 28);
        assert(!CODOL_SharedSecret(other, bad, a, rng, &state));
        assert(!memcmp(other, shared, 28));
      }
    }
    memcpy(before, pa, 100);
    memset(b, 0, 28);
    assert(!CODOL_ExportPublicKey(pa, b, rng, &state));
    assert(!memcmp(pa, before, 100));
    memset(b, 255, 28);
    assert(!CODOL_SharedSecret(other, pb, b, rng, &state));
    assert(!memcmp(other, shared, 28));
    assert(!CODOL_ExportPublicKey(pa, a, fail_rng, NULL));
    assert(!memcmp(pa, before, 100));
    assert(!CODOL_SharedSecret(other, pb, a, fail_rng, NULL));
    assert(!memcmp(other, shared, 28));
    assert(!CODOL_ExportPublicKey(pa, a, NULL, NULL));
    puts("CoDOL P-224 exchange vectors and malformed-key rejection passed");
    return 0;
}
