/* SHA-1 + HMAC-SHA1 —— 与客户端/参考实现的字节序一致 */
#include "codol_crypto.h"
#include <string.h>

#define ROL32(x, n) (((x) << (n)) | ((x) >> (32 - (n))))

static void sha1_block(uint32_t st[5], const uint8_t b[64])
{
    uint32_t w[80], a, bb, c, d, e;
    int i;
    for (i = 0; i < 16; i++)
        w[i] = ((uint32_t)b[i*4] << 24) | ((uint32_t)b[i*4+1] << 16)
             | ((uint32_t)b[i*4+2] << 8) | (uint32_t)b[i*4+3];
    for (i = 16; i < 80; i++)
        w[i] = ROL32(w[i-3] ^ w[i-8] ^ w[i-14] ^ w[i-16], 1);

    a = st[0]; bb = st[1]; c = st[2]; d = st[3]; e = st[4];
    for (i = 0; i < 80; i++) {
        uint32_t f, k, t;
        if (i < 20)      { f = (bb & c) | ((~bb) & d);        k = 0x5A827999; }
        else if (i < 40) { f = bb ^ c ^ d;                    k = 0x6ED9EBA1; }
        else if (i < 60) { f = (bb & c) | (bb & d) | (c & d); k = 0x8F1BBCDC; }
        else             { f = bb ^ c ^ d;                    k = 0xCA62C1D6; }
        t = ROL32(a, 5) + f + e + k + w[i];
        e = d; d = c; c = ROL32(bb, 30); bb = a; a = t;
    }
    st[0] += a; st[1] += bb; st[2] += c; st[3] += d; st[4] += e;
}

void codol_sha1_init(codol_sha1_ctx_t *c)
{
    c->h[0] = 0x67452301; c->h[1] = 0xEFCDAB89; c->h[2] = 0x98BADCFE;
    c->h[3] = 0x10325476; c->h[4] = 0xC3D2E1F0;
    c->total_len = 0; c->buf_len = 0;
}

void codol_sha1_update(codol_sha1_ctx_t *c, const uint8_t *data, size_t len)
{
    c->total_len += len;
    while (len) {
        size_t n = 64 - c->buf_len;
        if (n > len) n = len;
        memcpy(c->buf + c->buf_len, data, n);
        c->buf_len += n; data += n; len -= n;
        if (c->buf_len == 64) { sha1_block(c->h, c->buf); c->buf_len = 0; }
    }
}

void codol_sha1_final(codol_sha1_ctx_t *c, uint8_t out[20])
{
    uint64_t bits = c->total_len * 8;
    uint8_t pad[72]; size_t padlen; int i;
    memset(pad, 0, sizeof(pad));   /* ★ 必须清零: 除 0x80 外的填充字节都要是 0 */
    pad[0] = 0x80;
    padlen = (c->buf_len < 56) ? (56 - c->buf_len) : (120 - c->buf_len);
    codol_sha1_update(c, pad, padlen);
    for (i = 0; i < 8; i++) pad[i] = (uint8_t)(bits >> (56 - i*8));
    codol_sha1_update(c, pad, 8);
    for (i = 0; i < 5; i++) {
        out[i*4]   = (uint8_t)(c->h[i] >> 24);
        out[i*4+1] = (uint8_t)(c->h[i] >> 16);
        out[i*4+2] = (uint8_t)(c->h[i] >> 8);
        out[i*4+3] = (uint8_t)(c->h[i]);
    }
}

void codol_sha1(const uint8_t *data, size_t len, uint8_t out[20])
{
    codol_sha1_ctx_t c;
    codol_sha1_init(&c);
    codol_sha1_update(&c, data, len);
    codol_sha1_final(&c, out);
}

void codol_hmac_sha1(const uint8_t *key, size_t key_len,
                     const uint8_t *data, size_t data_len,
                     uint8_t out[20])
{
    uint8_t k[64], ipad[64], opad[64], inner[20];
    codol_sha1_ctx_t c;
    size_t i;

    memset(k, 0, sizeof(k));
    if (key_len > 64) codol_sha1(key, key_len, k);
    else memcpy(k, key, key_len);

    for (i = 0; i < 64; i++) { ipad[i] = k[i] ^ 0x36; opad[i] = k[i] ^ 0x5C; }

    codol_sha1_init(&c);
    codol_sha1_update(&c, ipad, 64);
    codol_sha1_update(&c, data, data_len);
    codol_sha1_final(&c, inner);

    codol_sha1_init(&c);
    codol_sha1_update(&c, opad, 64);
    codol_sha1_update(&c, inner, 20);
    codol_sha1_final(&c, out);
}
