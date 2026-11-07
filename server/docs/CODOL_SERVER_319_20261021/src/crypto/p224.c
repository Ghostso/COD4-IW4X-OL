/* P-224 (secp224r1) ECDH —— 战斗服密钥交换用。
 * 坐标 28 字节大端; 公钥导出 100 字节 libtomcrypt 形态。
 * Jacobian 坐标 + 简易 bignum; 单次 ECDH 量级足够。
 */
#include "codol_crypto.h"
#include <string.h>

typedef uint32_t fe[8];

static const fe P = { 0x00000001,0x00000000,0x00000000,0xFFFFFFFF,
                      0xFFFFFFFF,0xFFFFFFFF,0xFFFFFFFF,0x00000000 };
static const fe GX = { 0x115C1D21,0x343280D6,0x56C21122,0x4A03C1D3,
                       0x321390B9,0x6BB4BF7F,0xB70E0CBD,0x00000000 };
static const fe GY = { 0x85007E34,0x44D58199,0x5A074764,0xCD4375A0,
                       0x4C22DFE6,0xB5F723FB,0xBD376388,0x00000000 };

static int bn_cmp(const uint32_t *a, const uint32_t *b, int n)
{
    int i;
    for (i = n - 1; i >= 0; i--) if (a[i] != b[i]) return a[i] > b[i] ? 1 : -1;
    return 0;
}
static uint32_t bn_sub(uint32_t *a, const uint32_t *b, int n)
{
    uint64_t borrow = 0; int i;
    for (i = 0; i < n; i++) { uint64_t t = (uint64_t)a[i] - b[i] - borrow;
        a[i] = (uint32_t)t; borrow = (t >> 32) & 1; }
    return (uint32_t)borrow;
}
static void bn_mul(const uint32_t *a, const uint32_t *b, uint32_t *r)
{
    int i, j;
    memset(r, 0, 16 * sizeof(uint32_t));
    for (i = 0; i < 8; i++) {
        uint64_t carry = 0;
        for (j = 0; j < 8; j++) {
            uint64_t t = (uint64_t)a[i] * b[j] + r[i+j] + carry;
            r[i+j] = (uint32_t)t; carry = t >> 32;
        }
        r[i+8] = (uint32_t)carry;
    }
}
static int bn_bits(const uint32_t *a, int n)
{
    int i;
    for (i = n - 1; i >= 0; i--) if (a[i]) { int b = 0; uint32_t v = a[i];
        while (v) { b++; v >>= 1; } return i*32 + b; }
    return 0;
}
/* r = a mod p —— 长除法式: 每轮减去"不超过 t 的最大 p<<sh" */
static void bn_mod_p(const uint32_t *a, int n, fe r)
{
    uint32_t t[20], pp[20];
    int i;
    if (n > 20) n = 20;
    memset(t, 0, sizeof(t)); memcpy(t, a, (size_t)n * 4);
    memset(pp, 0, sizeof(pp)); for (i = 0; i < 8; i++) pp[i] = P[i];

    while (bn_cmp(t, pp, 20) >= 0) {
        int tb = bn_bits(t, 20), sh = tb - 224;
        uint32_t shifted[20];
        if (sh < 0) sh = 0;
        for (;;) {
            int wi = sh / 32, wb = sh % 32;
            memset(shifted, 0, sizeof(shifted));
            for (i = 0; i + wi < 20; i++) {
                uint32_t v = pp[i];
                shifted[i + wi] |= (wb ? (v << wb) : v);
                if (wb && i + wi + 1 < 20) shifted[i + wi + 1] |= (v >> (32 - wb));
            }
            if (bn_cmp(t, shifted, 20) >= 0) break;
            if (sh == 0) break;
            sh--;
        }
        bn_sub(t, shifted, 20);
    }
    for (i = 0; i < 8; i++) r[i] = t[i];
}
static void fe_copy(fe r, const fe a) { memcpy(r, a, sizeof(fe)); }
static int  fe_zero(const fe a) { int i; for (i=0;i<8;i++) if (a[i]) return 0; return 1; }

static void fe_add(fe r, const fe a, const fe b)
{
    uint32_t t[9]; uint64_t carry = 0; int i;
    for (i = 0; i < 8; i++) { uint64_t s = (uint64_t)a[i] + b[i] + carry;
        t[i] = (uint32_t)s; carry = s >> 32; }
    t[8] = (uint32_t)carry;
    while (t[8] || bn_cmp(t, P, 8) >= 0) {
        uint64_t borrow = 0;
        for (i = 0; i < 8; i++) { uint64_t s = (uint64_t)t[i] - P[i] - borrow;
            t[i] = (uint32_t)s; borrow = (s >> 32) & 1; }
        t[8] -= (uint32_t)borrow;
    }
    memcpy(r, t, sizeof(fe));
}
static void fe_sub(fe r, const fe a, const fe b)
{
    fe t; memcpy(t, a, sizeof(fe));
    if (bn_sub(t, b, 8)) { fe p2; memcpy(p2, P, sizeof(fe)); (void)bn_cmp(t,t,0); {
        uint64_t carry = 0; int i;
        for (i = 0; i < 8; i++) { uint64_t s = (uint64_t)t[i] + p2[i] + carry;
            t[i] = (uint32_t)s; carry = s >> 32; }
    } }
    memcpy(r, t, sizeof(fe));
}
static void fe_mul(fe r, const fe a, const fe b)
{
    uint32_t prod[16]; bn_mul(a, b, prod); bn_mod_p(prod, 16, r);
}
static void fe_sqr(fe r, const fe a) { fe_mul(r, a, a); }
static void fe_inv(fe r, const fe a)
{
    fe e, base, acc; int i;
    uint64_t borrow = 2;
    memcpy(e, P, sizeof(fe));
    for (i = 0; i < 8 && borrow; i++) {           /* e = p - 2, 带借位传播 */
        uint64_t s = (uint64_t)e[i] - borrow;
        e[i] = (uint32_t)s;
        borrow = (s >> 32) & 1;
    }
    fe_copy(base, a);
    memset(acc, 0, sizeof(fe)); acc[0] = 1;
    for (i = 0; i < 224; i++) {
        if ((e[i/32] >> (i%32)) & 1) fe_mul(acc, acc, base);
        fe_sqr(base, base);
    }
    fe_copy(r, acc);
}
static void fe_from_be(const uint8_t *b, fe r)
{
    int i, j;
    for (i = 0; i < 7; i++) { uint32_t v = 0;
        for (j = 0; j < 4; j++) v = (v << 8) | b[i*4 + j];
        r[6 - i] = v; }
    r[7] = 0;
}
static void fe_to_be(const fe a, uint8_t *o)
{
    int i, j;
    for (i = 0; i < 7; i++) { uint32_t v = a[6 - i];
        for (j = 0; j < 4; j++) o[i*4 + j] = (uint8_t)(v >> (24 - j*8)); }
}

typedef struct { fe x, y, z; } jpt;

static void jpt_inf(jpt *p) { memset(p->x,0,sizeof(fe)); memset(p->y,0,sizeof(fe)); memset(p->z,0,sizeof(fe)); }
static int  jpt_is_inf(const jpt *p) { return fe_zero(p->z); }

static void jpt_double(jpt *r, const jpt *p)
{
    fe delta, gamma, beta, alpha, x3, y3, z3, t1, t2, b4, b8;
    fe three;
    if (jpt_is_inf(p) || fe_zero(p->y)) { jpt_inf(r); return; }
    memset(three,0,sizeof(fe)); three[0] = 3;

    fe_sqr(delta, p->z);
    fe_sqr(gamma, p->y);
    fe_mul(beta, p->x, gamma);
    fe_sub(t1, p->x, delta);
    fe_add(t2, p->x, delta);
    fe_mul(alpha, t1, t2);
    fe_mul(alpha, alpha, three);              /* alpha = 3(x-d)(x+d) */

    fe_add(b8, beta, beta); fe_add(b8, b8, b8); fe_add(b8, b8, b8);   /* 8*beta */
    fe_sqr(x3, alpha);
    fe_sub(x3, x3, b8);

    fe_add(b4, beta, beta); fe_add(b4, b4, b4);                       /* 4*beta */
    fe_sub(t1, b4, x3);
    fe_mul(y3, alpha, t1);
    fe_sqr(t2, gamma); fe_add(t2,t2,t2); fe_add(t2,t2,t2); fe_add(t2,t2,t2);  /* 8*gamma^2 */
    fe_sub(y3, y3, t2);

    fe_add(t1, p->y, p->z);
    fe_sqr(t1, t1); fe_sub(t1, t1, gamma); fe_sub(t1, t1, delta);     /* (y+z)^2 - g - d */
    fe_copy(z3, t1);

    fe_copy(r->x, x3); fe_copy(r->y, y3); fe_copy(r->z, z3);
}

static void jpt_add(jpt *r, const jpt *p, const jpt *q)
{
    fe z1z1, z2z2, u1, u2, s1, s2, h, i2, j, rr, v, t, x3, y3, z3;
    if (jpt_is_inf(p)) { *r = *q; return; }
    if (jpt_is_inf(q)) { *r = *p; return; }

    fe_sqr(z1z1, p->z);
    fe_sqr(z2z2, q->z);
    fe_mul(u1, p->x, z2z2);
    fe_mul(u2, q->x, z1z1);
    fe_mul(t, q->z, z2z2); fe_mul(s1, p->y, t);
    fe_mul(t, p->z, z1z1); fe_mul(s2, q->y, t);
    fe_sub(h, u2, u1);
    fe_sub(rr, s2, s1);
    if (fe_zero(h)) {
        if (fe_zero(rr)) { jpt_double(r, p); return; }
        jpt_inf(r); return;
    }
    fe_add(i2, h, h); fe_sqr(i2, i2);          /* (2h)^2 */
    fe_mul(j, h, i2);
    fe_add(rr, rr, rr);                        /* 2(s2-s1) */
    fe_mul(v, u1, i2);
    fe_sqr(x3, rr); fe_sub(x3, x3, j); fe_add(t, v, v); fe_sub(x3, x3, t);
    fe_sub(t, v, x3); fe_mul(y3, rr, t);
    fe_mul(t, s1, j); fe_add(t, t, t); fe_sub(y3, y3, t);
    fe_add(t, p->z, q->z); fe_sqr(t, t); fe_sub(t, t, z1z1); fe_sub(t, t, z2z2);
    fe_mul(z3, t, h);
    fe_copy(r->x, x3); fe_copy(r->y, y3); fe_copy(r->z, z3);
}

static void jpt_mul(jpt *r, const jpt *p, const uint8_t k28[28])
{
    jpt acc, base; int i;
    jpt_inf(&acc); base = *p;
    for (i = 0; i < 224; i++) {
        if ((k28[27 - i/8] >> (i % 8)) & 1) jpt_add(&acc, &acc, &base);
        jpt_double(&base, &base);
    }
    *r = acc;
}

static void jpt_to_affine(const jpt *p, fe xo, fe yo)
{
    fe zi, zi2, zi3;
    if (jpt_is_inf(p)) { memset(xo,0,sizeof(fe)); memset(yo,0,sizeof(fe)); return; }
    fe_inv(zi, p->z); fe_sqr(zi2, zi); fe_mul(zi3, zi2, zi);
    fe_mul(xo, p->x, zi2); fe_mul(yo, p->y, zi3);
}

void codol_p224_pubkey_from_priv(const uint8_t priv[28], codol_p224_point_t *out)
{
    jpt g, r; fe x, y;
    fe_copy(g.x, GX); fe_copy(g.y, GY); memset(g.z,0,sizeof(fe)); g.z[0] = 1;
    jpt_mul(&r, &g, priv);
    jpt_to_affine(&r, x, y);
    fe_to_be(x, out->x); fe_to_be(y, out->y);
}

void codol_p224_gen_keypair(uint8_t priv_out[28], codol_p224_point_t *pub_out)
{
    static uint32_t st = 0x2545F491u; int i;
    for (i = 0; i < 28; i++) { st = st * 1103515245u + 12345u; priv_out[i] = (uint8_t)(st >> 16); }
    priv_out[0] &= 0x7F;
    if (!priv_out[0] && !priv_out[1]) priv_out[27] = 1;
    codol_p224_pubkey_from_priv(priv_out, pub_out);
}

static uint8_t der_uint(const uint8_t raw[28], uint8_t *out)
{
    int i = 0, n, need; uint8_t body[30];
    while (i < 27 && raw[i] == 0) i++;
    n = 28 - i;
    need = (raw[i] & 0x80) ? 1 : 0;
    body[0] = 0;
    memcpy(body + need, raw + i, (size_t)n);
    out[0] = 0x02; out[1] = (uint8_t)(n + need);
    memcpy(out + 2, body, (size_t)(n + need));
    return (uint8_t)(2 + n + need);
}

void codol_p224_export_pubkey(const codol_p224_point_t *pub, uint8_t out100[100])
{
    uint8_t dx[32], dy[32], lx, ly;
    lx = der_uint(pub->x, dx);
    ly = der_uint(pub->y, dy);
    memset(out100, 0, 100);
    out100[0] = 0x30; out100[1] = (uint8_t)(7 + lx + ly);
    out100[2]=3; out100[3]=2; out100[4]=7; out100[5]=0; out100[6]=2; out100[7]=1; out100[8]=28;
    memcpy(out100 + 9, dx, lx);
    memcpy(out100 + 9 + lx, dy, ly);
}

bool codol_p224_import_pubkey(const uint8_t in100[100], codol_p224_point_t *out)
{
    uint8_t end, pos, ln, skip, x[28], y[28];
    if (in100[0] != 0x30) return false;
    end = (uint8_t)(in100[1] + 2);
    if (end > 100 || end < 9) return false;
    if (in100[2]!=3||in100[3]!=2||in100[4]!=7||in100[5]!=0||in100[6]!=2||in100[7]!=1||in100[8]!=28) return false;
    pos = 9;
    if (in100[pos] != 2) return false;
    ln = in100[pos+1]; pos = (uint8_t)(pos + 2);
    if (ln < 1 || ln > 29 || pos + ln > end || (in100[pos] & 0x80)) return false;
    skip = (ln == 29) ? 1 : 0;
    if (skip && in100[pos] != 0) return false;
    memset(x, 0, 28);
    memcpy(x + 28 - (ln - skip), in100 + pos + skip, (size_t)(ln - skip));
    pos = (uint8_t)(pos + ln);
    if (in100[pos] != 2) return false;
    ln = in100[pos+1]; pos = (uint8_t)(pos + 2);
    if (ln < 1 || ln > 29 || pos + ln > end || (in100[pos] & 0x80)) return false;
    skip = (ln == 29) ? 1 : 0;
    if (skip && in100[pos] != 0) return false;
    memset(y, 0, 28);
    memcpy(y + 28 - (ln - skip), in100 + pos + skip, (size_t)(ln - skip));
    memcpy(out->x, x, 28); memcpy(out->y, y, 28);
    return true;
}

bool codol_p224_ecdh(const uint8_t priv[28], const codol_p224_point_t *peer,
                     uint8_t shared_x28[28])
{
    jpt p, r; fe x, y;
    fe_from_be(peer->x, p.x); fe_from_be(peer->y, p.y);
    memset(p.z, 0, sizeof(fe)); p.z[0] = 1;
    jpt_mul(&r, &p, priv);
    if (jpt_is_inf(&r)) return false;
    jpt_to_affine(&r, x, y);
    fe_to_be(x, shared_x28);
    return true;
}

void codol_derive_transport_key(const uint8_t shared_x28[28],
                                const uint8_t security_key16[16],
                                uint8_t out24[24])
{
    uint8_t buf[44], d[20];
    memcpy(buf, shared_x28, 28);
    memcpy(buf + 28, security_key16, 16);
    codol_sha1(buf, 44, d);
    memcpy(out24, d, 20);
    memset(out24 + 20, 0, 4);
}

/* ---- 仅供测试: 暴露域运算, 便于与参考实现逐项对齐 ---- */
void codol_p224_test_fe(const uint8_t a28[28], const uint8_t b28[28],
                        uint8_t out28[28], int op)
{
    fe a, b, r;
    fe_from_be(a, a);   /* 占位, 下面重算 */
    fe_from_be(a28, a);
    fe_from_be(b28, b);
    switch (op) {
        case 0: fe_add(r, a, b); break;
        case 1: fe_sub(r, a, b); break;
        case 2: fe_mul(r, a, b); break;
        case 3: fe_inv(r, a);    break;
        default: memset(r, 0, sizeof(fe)); break;
    }
    fe_to_be(r, out28);
}