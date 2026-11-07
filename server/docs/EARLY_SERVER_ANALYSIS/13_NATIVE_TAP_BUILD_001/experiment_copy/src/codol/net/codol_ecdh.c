/* SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_ecdh.h"
#include "mbedtls/ecdh.h"
#include <string.h>

static int coordinate(mbedtls_mpi *out, const uint8_t *key, size_t end, size_t *pos)
{
    size_t n, p = *pos;
    if (p + 2 > end || key[p++] != 2) return 0;
    n = key[p++];
    if (!n || n > 29 || n > end - p || (key[p] & 128)) return 0;
    /* Accept fixed-width coordinates used by alpha0022 as well as minimal
     * positive INTEGERs. A 29th byte may only be a necessary sign byte. */
    if (n == 29 && (key[p] || !(key[p + 1] & 128))) return 0;
    if (mbedtls_mpi_read_binary(out, key + p, n)) return 0;
    *pos = p + n;
    return 1;
}

static int import_public(mbedtls_ecp_group *group, mbedtls_ecp_point *q,
                         const uint8_t key[100])
{
    static const uint8_t prefix[] = {3, 2, 7, 0, 2, 1, 28};
    size_t end, p = 9, i;
    if (key[0] != 0x30 || key[1] < 13 || key[1] > 69 ||
        memcmp(key + 2, prefix, sizeof(prefix))) return 0;
    end = key[1] + 2;
    if (!coordinate(&q->X, key, end, &p) ||
        !coordinate(&q->Y, key, end, &p) || p != end) return 0;
    for (i = end; i < 100; ++i) if (key[i]) return 0;
    return !mbedtls_mpi_lset(&q->Z, 1) && !mbedtls_ecp_check_pubkey(group, q);
}

static int write_coordinate(uint8_t *out, size_t *pos, const mbedtls_mpi *value)
{
    uint8_t bytes[28];
    size_t p = *pos;
    if (mbedtls_mpi_write_binary(value, bytes, sizeof(bytes))) return 0;
    out[p++] = 2;
    out[p++] = 28 + ((bytes[0] & 128) != 0);
    if (bytes[0] & 128) out[p++] = 0;
    memcpy(out + p, bytes, sizeof(bytes));
    *pos = p + sizeof(bytes);
    return 1;
}

int CODOL_ExportPublicKey(uint8_t out[100], const uint8_t private_key[28],
                          codol_ecdh_rng_t rng, void *rng_context)
{
    uint8_t staged[100] = {0x30, 0, 3, 2, 7, 0, 2, 1, 28};
    mbedtls_ecp_group group;
    mbedtls_ecp_point q;
    mbedtls_mpi d;
    size_t pos = 9;
    int ok = 0;
    if (!out || !private_key || !rng) return 0;
    mbedtls_ecp_group_init(&group); mbedtls_ecp_point_init(&q); mbedtls_mpi_init(&d);
    if (mbedtls_ecp_group_load(&group, MBEDTLS_ECP_DP_SECP224R1) ||
        mbedtls_mpi_read_binary(&d, private_key, 28) ||
        mbedtls_ecp_check_privkey(&group, &d) ||
        mbedtls_ecp_mul(&group, &q, &d, &group.G, rng, rng_context) ||
        !write_coordinate(staged, &pos, &q.X) ||
        !write_coordinate(staged, &pos, &q.Y)) goto done;
    staged[1] = pos - 2;
    memcpy(out, staged, sizeof(staged)); ok = 1;
done:
    mbedtls_mpi_free(&d); mbedtls_ecp_point_free(&q); mbedtls_ecp_group_free(&group);
    return ok;
}

int CODOL_SharedSecret(uint8_t out[28], const uint8_t peer[100],
                       const uint8_t private_key[28],
                       codol_ecdh_rng_t rng, void *rng_context)
{
    uint8_t staged[28];
    volatile uint8_t *wipe = staged;
    mbedtls_ecp_group group;
    mbedtls_ecp_point q;
    mbedtls_mpi d, x;
    size_t i;
    int ok = 0;
    if (!out || !peer || !private_key || !rng) return 0;
    mbedtls_ecp_group_init(&group); mbedtls_ecp_point_init(&q);
    mbedtls_mpi_init(&d); mbedtls_mpi_init(&x);
    if (mbedtls_ecp_group_load(&group, MBEDTLS_ECP_DP_SECP224R1) ||
        mbedtls_mpi_read_binary(&d, private_key, 28) ||
        mbedtls_ecp_check_privkey(&group, &d) || !import_public(&group, &q, peer) ||
        mbedtls_ecdh_compute_shared(&group, &x, &q, &d, rng, rng_context) ||
        mbedtls_mpi_write_binary(&x, staged, sizeof(staged))) goto done;
    memcpy(out, staged, sizeof(staged)); ok = 1;
done:
    for (i = 0; i < sizeof(staged); ++i) wipe[i] = 0;
    mbedtls_mpi_free(&x); mbedtls_mpi_free(&d);
    mbedtls_ecp_point_free(&q); mbedtls_ecp_group_free(&group);
    return ok;
}
