/* 域运算逐项对齐测试 */
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
static void hexs(const uint8_t *d, size_t n, char *out)
{
    static const char *H = "0123456789abcdef"; size_t i;
    for (i = 0; i < n; i++) { out[i*2] = H[d[i]>>4]; out[i*2+1] = H[d[i]&15]; }
    out[n*2] = 0;
}
static int fails;
static void chk(const char *name, const uint8_t *got, const char *want)
{
    char b[128]; hexs(got, 28, b);
    if (strcmp(b, want)) { printf("FAIL %-10s\n  got  %s\n  want %s\n", name, b, want); fails++; }
    else printf("ok   %-10s %s\n", name, b);
}

int main(void)
{
    uint8_t gx[28], gy[28], out[28];
    hex2bin("b70e0cbd6bb4bf7f321390b94a03c1d356c21122343280d6115c1d21", gx);
    hex2bin("bd376388b5f723fb4c22dfe6cd4375a05a07476444d5819985007e34", gy);

    codol_p224_test_fe(gx, gy, out, 0);
    chk("add", out, "7445704621abe37a7e3670a017473774b0c958867908026f965c9b54");
    codol_p224_test_fe(gx, gy, out, 1);
    chk("sub", out, "f9d6a934b5bd9b83e5f0b0d27cc04c31fcbac9bdef5cff3c8c5b9eee");
    codol_p224_test_fe(gx, gy, out, 2);
    chk("mul", out, "7a8c7bbe69f5f9a5371987f4887c5dae71360fab68b91e160bb4c1c9");
    codol_p224_test_fe(gx, gy, out, 3);
    chk("inv", out, "7b533e53fc631668587f2986f7d33b43dec9e5b81912c6d22bbcc003");

    printf("\n%s (%d)\n", fails ? "FAILED" : "ALL PASSED", fails);
    return fails ? 1 : 0;
}
