#ifndef CODOL_CRYPTO_H
#define CODOL_CRYPTO_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ---------------- SHA-1 ---------------- */
typedef struct {
    uint32_t h[5];
    uint64_t total_len;
    uint8_t  buf[64];
    size_t   buf_len;
} codol_sha1_ctx_t;

void codol_sha1_init(codol_sha1_ctx_t *c);
void codol_sha1_update(codol_sha1_ctx_t *c, const uint8_t *data, size_t len);
void codol_sha1_final(codol_sha1_ctx_t *c, uint8_t out[20]);
void codol_sha1(const uint8_t *data, size_t len, uint8_t out[20]);

/* ---------------- HMAC-SHA1 ---------------- */
void codol_hmac_sha1(const uint8_t *key, size_t key_len,
                     const uint8_t *data, size_t data_len,
                     uint8_t out[20]);

/* ---------------- AES-128 ---------------- */
typedef struct { uint32_t rk[44]; } codol_aes128_ctx_t;

void codol_aes128_init(codol_aes128_ctx_t *c, const uint8_t key[16]);
void codol_aes128_encrypt_block(const codol_aes128_ctx_t *c,
                                const uint8_t in[16], uint8_t out[16]);

/* ---------------- 密钥流 (AES-128 + SHA1(seed) 计数器) ----------------
 * 计数器初值 = SHA1(seed) 的 20 字节; 每生成一个 16B 块后, 把 20 字节计数器
 * 当作 **小端 160 位整数** 加 1 (与 Python `_keystream_xor` 一致)。
 */
void codol_keystream_xor(const uint8_t key16[16], const uint8_t seed[6],
                         const uint8_t *in, size_t len, uint8_t *out);

/* ---------------- P-224 ECDH ----------------
 * 坐标 = 28 字节大端。公钥导出为 100 字节 libtomcrypt 形态。
 */
typedef struct { uint8_t x[28]; uint8_t y[28]; } codol_p224_point_t;

void codol_p224_gen_keypair(uint8_t priv_out[28], codol_p224_point_t *pub_out);
void codol_p224_export_pubkey(const codol_p224_point_t *pub, uint8_t out100[100]);
bool codol_p224_import_pubkey(const uint8_t in100[100], codol_p224_point_t *out);
bool codol_p224_ecdh(const uint8_t priv[28], const codol_p224_point_t *peer,
                     uint8_t shared_x28[28]);

/* 传输密钥 = SHA1(shared_x_28BE || security_key16) 的前 20 字节 + 4 个 0 = 24B */
void codol_derive_transport_key(const uint8_t shared_x28[28],
                                const uint8_t security_key16[16],
                                uint8_t out24[24]);

/* 便于测试: 用给定私钥算公钥 */
void codol_p224_pubkey_from_priv(const uint8_t priv[28], codol_p224_point_t *out);

#ifdef __cplusplus
}
#endif
#endif /* CODOL_CRYPTO_H */
