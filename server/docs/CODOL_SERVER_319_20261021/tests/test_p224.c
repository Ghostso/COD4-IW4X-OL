/* P-224 ECDH 与参考实现的一致性测试 */
#include "codol_crypto.h"
#include <stdio.h>
#include <string.h>

static int hex2bin(const char *h, uint8_t *out)
{
    int n = 0;
    while (h[0] && h[1]) { unsigned v; char t[3] = { h[0], h[1], 0 };
        sscanf(t, "%x", &v); out[n++] = (uint8_t)v; h += 2; }
    return n;
}
static void hexs(const uint8_t *d, size_t n, char *o)
{
    static const char *H = "0123456789abcdef"; size_t i;
    for (i = 0; i < n; i++) { o[i*2] = H[d[i]>>4]; o[i*2+1] = H[d[i]&15]; }
    o[n*2] = 0;
}
static int fails;
static void chk(const char *n, const uint8_t *g, const char *w)
{
    char b[128]; hexs(g, 28, b);
    if (strcmp(b, w)) { printf("FAIL %-14s\n  got  %s\n  want %s\n", n, b, w); fails++; }
    else printf("ok   %-14s %s\n", n, b);
}
static void pub_of(long k, codol_p224_point_t *p)
{
    uint8_t pv[28]; int i; memset(pv, 0, 28);
    for (i = 27; i >= 0 && k; i--) { pv[i] = (uint8_t)(k & 0xFF); k >>= 8; }
    codol_p224_pubkey_from_priv(pv, p);
}

int main(void)
{
    codol_p224_point_t g, pub, pb, rt;
    uint8_t der[100], priv[28], shared[28];

    pub_of(1, &g);
    chk("Gx", g.x, "b70e0cbd6bb4bf7f321390b94a03c1d356c21122343280d6115c1d21");
    chk("Gy", g.y, "bd376388b5f723fb4c22dfe6cd4375a05a07476444d5819985007e34");

    /* 导出后必须能原样解析回来, 且 100B 形态头部正确 */
    codol_p224_export_pubkey(&g, der);
    if (der[0] != 0x30 || der[1] != 0x45 || der[2] != 3 || der[8] != 28) {
        printf("FAIL export header\n"); fails++;
    } else if (!codol_p224_import_pubkey(der, &rt) ||
               memcmp(rt.x, g.x, 28) || memcmp(rt.y, g.y, 28)) {
        printf("FAIL export/import roundtrip\n"); fails++;
    } else printf("ok   %-14s DER100, roundtrip ok\n", "export/import");

    pub_of(2, &pub);
    chk("2G.x", pub.x, "706a46dc76dcb76798e60e6d89474788d16dc18032d268fd1a704fa6");
    chk("2G.y", pub.y, "1c2b76a7bc25e7702a704fa986892849fca629487acf3709d2e4e8bb");
    pub_of(3, &pub);
    chk("3G.x", pub.x, "df1b1d66a551d0d31eff822558b9d2cc75c2180279fe0d08fd896d04");
    pub_of(4, &pub);
    chk("4G.x", pub.x, "ae99feebb5d26945b54892092a8aee02912930fa41cd114e40447301");

    {   /* 解析对端公钥 + ECDH */
        uint8_t derB[100];
        hex2bin("30430302070002011c021c5e35badfb95668ac93ce8c9652fa3cf7b93c10963c9098f04314af03"
                "021c66d21d531803de75e8d26bf953ad4e73fc61f42eb834a8a2c842748d"
                "00000000000000000000000000000000000000000000000000000000000000", derB);
        if (!codol_p224_import_pubkey(derB, &pb)) { printf("FAIL import\n"); fails++; }
        else {
            chk("pubB.x", pb.x, "5e35badfb95668ac93ce8c9652fa3cf7b93c10963c9098f04314af03");
            hex2bin("1234567890abcdef1234567890abcdef1234567890abcdef12345678", priv);
            if (!codol_p224_ecdh(priv, &pb, shared)) { printf("FAIL ecdh\n"); fails++; }
            else chk("shared(A,B)", shared, "d73cfc8c09ee9c4c1574e0aafad8398c8b35dfe209b1eb65514c5cb0");
        }
    }

    printf("\n%s (%d failure%s)\n", fails ? "FAILED" : "ALL PASSED", fails, fails == 1 ? "" : "s");
    return fails ? 1 : 0;
}
