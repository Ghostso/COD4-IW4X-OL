/* 密码学层与 Python/C# 参考实现的逐字节一致性测试 */
#include "codol_crypto.h"
#include <stdio.h>
#include <string.h>
#include <assert.h>

static void hexs(const uint8_t *d, size_t n, char *out)
{
    static const char *H = "0123456789abcdef";
    size_t i;
    for (i = 0; i < n; i++) { out[i*2] = H[d[i] >> 4]; out[i*2+1] = H[d[i] & 15]; }
    out[n*2] = 0;
}

static int check_hex(const char *name, const uint8_t *got, size_t n, const char *want)
{
    char buf[256];
    hexs(got, n, buf);
    if (strcmp(buf, want) != 0) {
        printf("FAIL %-14s got=%s\n                want=%s\n", name, buf, want);
        return 1;
    }
    printf("ok   %-14s %s\n", name, buf);
    return 0;
}

int main(void)
{
    int fails = 0;
    uint8_t out[64];

    /* SHA-1 */
    codol_sha1((const uint8_t *)"abc", 3, out);
    fails += check_hex("sha1(abc)", out, 20, "a9993e364706816aba3e25717850c26c9cd0d89d");

    codol_sha1((const uint8_t *)"", 0, out);
    fails += check_hex("sha1(empty)", out, 20, "da39a3ee5e6b4b0d3255bfef95601890afd80709");

    {
        uint8_t big[1000];
        memset(big, 'a', sizeof(big));
        codol_sha1(big, sizeof(big), out);
        fails += check_hex("sha1(1000a)", out, 20, "291e9a6c66994949b57ba5e650361e98fc36b1ba");
    }

    /* HMAC-SHA1 */
    codol_hmac_sha1((const uint8_t *)"key", 3,
                    (const uint8_t *)"The quick brown fox jumps over the lazy dog", 43, out);
    fails += check_hex("hmac-sha1", out, 20, "de7c9b85b8b78aa6bc8a7a36f70a90701c9db4d9");

    /* AES-128 FIPS-197 */
    {
        uint8_t key[16], pt[16];
        int i;
        codol_aes128_ctx_t c;
        for (i = 0; i < 16; i++) key[i] = (uint8_t)i;
        memset(pt, 0, sizeof(pt));
        {
            const uint8_t p[16] = {0x00,0x11,0x22,0x33,0x44,0x55,0x66,0x77,
                                   0x88,0x99,0xaa,0xbb,0xcc,0xdd,0xee,0xff};
            memcpy(pt, p, 16);
        }
        codol_aes128_init(&c, key);
        codol_aes128_encrypt_block(&c, pt, out);
        fails += check_hex("aes128", out, 16, "69c4e0d86a7b0430d8cdb78070b4c55a");
    }

    /* 密钥流 */
    {
        uint8_t key[16], seed[6], data[40], enc[40];
        int i;
        for (i = 0; i < 16; i++) key[i] = (uint8_t)i;
        seed[0] = 0x34; seed[1] = 0x12; seed[2] = 0; seed[3] = 0; seed[4] = 0xAB; seed[5] = 0xCD;
        for (i = 0; i < 40; i++) data[i] = (uint8_t)i;
        codol_keystream_xor(key, seed, data, 40, enc);
        fails += check_hex("keystream", enc, 40,
            "dffe83c4498c45d70eb2a28077923770e000aeae7ba56e881a9942d7b1547f0bbfb8274c6b55110a");
    }

    printf("\n%s (%d failure%s)\n", fails ? "FAILED" : "ALL PASSED", fails, fails == 1 ? "" : "s");
    return fails ? 1 : 0;
}
