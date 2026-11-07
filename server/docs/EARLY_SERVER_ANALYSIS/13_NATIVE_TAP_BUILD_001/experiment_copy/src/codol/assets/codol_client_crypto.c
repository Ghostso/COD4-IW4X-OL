#include "codol_client_crypto.h"
#include "mbedtls/pk.h"
#include "mbedtls/rsa.h"
#include "mbedtls/sha256.h"
#include "mbedtls/entropy.h"
#include "mbedtls/ctr_drbg.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void wipe(void *p, size_t n)
{
    volatile uint8_t *b = p;
    while (n--) *b++ = 0;
}

#define CODOL_C1_KEYS_SIZE (CODOL_C1_IWD_BLOB_SIZE + CODOL_C1_RSA_DER_SIZE)
int CODOL_ReadClientRegion(const char *path, unsigned long exe_offset, uint8_t *out, size_t size)
{
    FILE *file; long length; unsigned long offset = exe_offset; int ok;
    if (!path || !out || !size || !(file = fopen(path, "rb"))) return 0;
    if (fseek(file, 0, SEEK_END) || (length = ftell(file)) < 0) { fclose(file); return 0; }
    if (length == (long)CODOL_C1_KEYS_SIZE) {
        /* c1_keys.bin: the IWD blob, then the RSA DER, nothing else. */
        if (exe_offset == CODOL_C1_IWD_BLOB_OFFSET && size <= CODOL_C1_IWD_BLOB_SIZE) offset = 0;
        else if (exe_offset == CODOL_C1_RSA_DER_OFFSET && size <= CODOL_C1_RSA_DER_SIZE) offset = CODOL_C1_IWD_BLOB_SIZE;
        else { fclose(file); return 0; }
    }
    ok = !fseek(file, (long)offset, SEEK_SET) && fread(out, 1, size, file) == size;
    fclose(file);
    return ok;
}
int CODOL_DefaultClientKeyPath(const char *basepath, char *out, size_t size)
{
    FILE *file; int n;
    if (!basepath || !out || !size) return 0;
    n = snprintf(out, size, "%s/C1.exe", basepath);
    if (n < 0 || (size_t)n >= size) return 0;
    if ((file = fopen(out, "rb"))) { fclose(file); return 1; }
    n = snprintf(out, size, "%s/c1_keys.bin", basepath);
    return n >= 0 && (size_t)n < size;
}

int CODOL_DecryptClientMaterial(const char *exe, const uint8_t encrypted[256], uint8_t *out, size_t expected_size)
{
    static const uint8_t expected[32] = {
        0x3a,0x2f,0x78,0x91,0xac,0x98,0xf1,0xfd,0xf6,0xa9,0xa2,0x21,0xc5,0x58,0x67,0x25,
        0x15,0x7d,0xf2,0x70,0xd6,0x83,0x1e,0x0f,0xf8,0x2c,0x38,0x3c,0xd2,0x62,0xcb,0xb5 };
    uint8_t der[CODOL_C1_RSA_DER_SIZE], digest[32], plain[40]={0}; size_t size = 0;
    mbedtls_pk_context pk; mbedtls_entropy_context entropy;
    mbedtls_ctr_drbg_context rng; int ok = 0;
    if (!out || !encrypted || !expected_size || expected_size>sizeof(plain) || !exe) return 0;
    if (!CODOL_ReadClientRegion(exe, CODOL_C1_RSA_DER_OFFSET, der, sizeof(der))) {
        wipe(der, sizeof(der)); return 0;
    }
    mbedtls_pk_init(&pk); mbedtls_entropy_init(&entropy); mbedtls_ctr_drbg_init(&rng);
    if (mbedtls_sha256_ret(der, sizeof(der), digest, 0) || memcmp(digest, expected, 32)) goto done;
    if (mbedtls_pk_parse_key(&pk, der, sizeof(der), NULL, 0) ||
        !mbedtls_pk_can_do(&pk, MBEDTLS_PK_RSA)) goto done;
    if (mbedtls_ctr_drbg_seed(&rng, mbedtls_entropy_func, &entropy,
                             (const uint8_t *)"codol-archive", 13)) goto done;
    mbedtls_rsa_set_padding(mbedtls_pk_rsa(pk), MBEDTLS_RSA_PKCS_V21, MBEDTLS_MD_SHA256);
    ok = !mbedtls_rsa_rsaes_oaep_decrypt(mbedtls_pk_rsa(pk), mbedtls_ctr_drbg_random,
             &rng, MBEDTLS_RSA_PRIVATE, NULL, 0, &size, encrypted, plain, sizeof(plain)) && size == expected_size;
    if (ok) memcpy(out,plain,expected_size);
done:
    mbedtls_pk_free(&pk); mbedtls_ctr_drbg_free(&rng); mbedtls_entropy_free(&entropy);
    wipe(der, sizeof(der)); wipe(plain,sizeof(plain)); return ok;
}

