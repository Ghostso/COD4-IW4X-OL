/* CoDOL 1.1.1.13 native fastfile decryption and inflation. The archive contents
 * remain user-owned; only format code lives here. SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_assets.h"
#include "codol_client_crypto.h"
#include "mbedtls/aes.h"
#include "mbedtls/pk.h"
#include "mbedtls/rsa.h"
#include "mbedtls/sha256.h"
#include "mbedtls/entropy.h"
#include "mbedtls/ctr_drbg.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define FF_HEADER 0x115u
#define FF_BLOCK 0x2000u

static void wipe(void *p, size_t n)
{
    volatile uint8_t *b = p;
    while (n--) *b++ = 0;
}


static int ctr(mbedtls_aes_context *aes, const uint8_t iv[16], const uint8_t *in,
                uint8_t *out, size_t size)
{
    uint8_t counter[16], stream[16]; size_t offset, i, n; int ok = 0;
    memcpy(counter, iv, 16);
    for (offset = 0; offset < size; offset += n) {
        if (mbedtls_aes_crypt_ecb(aes, MBEDTLS_AES_ENCRYPT, counter, stream)) goto done;
        n = size - offset; if (n > 16) n = 16;
        for (i = 0; i < n; ++i) out[offset + i] = in[offset + i] ^ stream[i];
        for (i = 0; i < 16; ++i) if (++counter[i]) break;
    }
    ok = 1;
done:
    wipe(counter, sizeof(counter)); wipe(stream, sizeof(stream)); return ok;
}

static int hash_matches(const uint8_t *data, size_t size, const uint8_t *expected)
{
    uint8_t digest[32];
    return !mbedtls_sha256_ret(data, size, digest, 0) && !memcmp(digest, expected, 32);
}

/* Why the last CODOL_OpenFastFile failed, for the mount error path. */
static const char *open_failure = "";
const char *CODOL_FastFileOpenFailure(void) { return open_failure; }

int CODOL_OpenFastFile(codol_zone_t *out, const char *path, const char *client_exe)
{
    FILE *file; long file_size; uint8_t *raw = NULL, *compressed = NULL, *zone = NULL;
    uint8_t key_iv[40] = {0}, header[FF_BLOCK], table[FF_BLOCK];
    size_t body_size, compressed_size = 0, zone_size = 0, i, section = 0, table_index = 0;
    mbedtls_aes_context aes; int ok = 0, unsigned_file;
    open_failure = "archive format";
    if (!out || !path) { open_failure = "no path"; return 0; }
    if (!(file = fopen(path, "rb"))) { open_failure = "fopen failed"; return 0; }
    if (fseek(file, 0, SEEK_END) || (file_size = ftell(file)) < FF_HEADER ||
        (unsigned long)file_size > CODOL_ASSET_LIMIT || fseek(file, 0, SEEK_SET)) {
        open_failure = "size/seek"; fclose(file); return 0;
    }
    raw = malloc(file_size);
    if (!raw || fread(raw, 1, file_size, file) != (size_t)file_size) {
        open_failure = raw ? "short read" : "malloc(file image) failed"; free(raw); fclose(file); return 0;
    }
    fclose(file); mbedtls_aes_init(&aes);
    unsigned_file = !memcmp(raw, "IWffu100", 8);
    if ((!unsigned_file && memcmp(raw, "IWff0100", 8)) ||
        raw[8] != 0x4e || raw[9] != 1 || raw[10] || raw[11]) goto done;
    body_size = file_size - FF_HEADER;
    if (!body_size || (!unsigned_file && (body_size % FF_BLOCK || body_size < 3 * FF_BLOCK))) goto done;
    if (!CODOL_DecryptClientMaterial(client_exe, raw + 0x15, key_iv, sizeof(key_iv)) || mbedtls_aes_setkey_enc(&aes, key_iv, 192)) goto done;
    compressed = malloc(body_size);
    if (!compressed) { open_failure = "malloc(body) failed"; goto done; }
    if (unsigned_file) {
        if (!ctr(&aes, key_iv + 24, raw + FF_HEADER, compressed, body_size)) goto done;
        compressed_size = body_size;
    } else {
        if (!ctr(&aes, key_iv + 24, raw + FF_HEADER, header, FF_BLOCK) ||
            memcmp(header, "IWffs100", 8) ||
            !hash_matches(header + 0x12c, 0x1fd0 - 0x12c, header + 0xc)) goto done;
        for (i = 1; i < body_size / FF_BLOCK; ++i) {
            const uint8_t *entry;
            if (!table_index) {
                if (section >= (0x1fd0 - 0x150) / 32) goto done;
                entry = header + 0x150 + section * 32;
                if (!ctr(&aes, entry, raw + FF_HEADER + i * FF_BLOCK, table, FF_BLOCK) ||
                    !hash_matches(table, FF_BLOCK, entry)) goto done;
                table_index = 1;
            } else {
                entry = table + (table_index - 1) * 32;
                if (!ctr(&aes, entry, raw + FF_HEADER + i * FF_BLOCK,
                          compressed + compressed_size, FF_BLOCK) ||
                    !hash_matches(compressed + compressed_size, FF_BLOCK, entry)) goto done;
                compressed_size += FF_BLOCK;
                if (++table_index == 257) { ++section; table_index = 0; }
            }
        }
    }
    /* Signed-block files contain zlib padding to the last block boundary. */
    if (!CODOL_Inflate(compressed, compressed_size, &zone, &zone_size, 0, !unsigned_file)) goto done;
    ok = CODOL_OpenZoneImage(out, zone, zone_size);
done:
    mbedtls_aes_free(&aes); wipe(key_iv, sizeof(key_iv));
    free(raw); free(compressed); free(zone); return ok;
}
