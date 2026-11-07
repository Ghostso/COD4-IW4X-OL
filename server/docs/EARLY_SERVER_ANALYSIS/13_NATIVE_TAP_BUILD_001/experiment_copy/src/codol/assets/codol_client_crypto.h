#ifndef CODOL_CLIENT_CRYPTO_H
#define CODOL_CLIENT_CRYPTO_H
#include <stdint.h>
#include <stddef.h>
/* Read the verified C1 RSA material and decrypt an OAEP-SHA256 blob.
 * Failure leaves output unchanged. No key material is embedded in this source. */
int CODOL_DecryptClientMaterial(const char *,const uint8_t [256],uint8_t *,size_t);
/* The two C1.exe regions the server needs, as file offsets into C1.exe. */
#define CODOL_C1_IWD_BLOB_OFFSET 0x838b20u
#define CODOL_C1_IWD_BLOB_SIZE   256u
#define CODOL_C1_RSA_DER_OFFSET  0x83c248u
#define CODOL_C1_RSA_DER_SIZE    1191u
/* c1_keys.bin (tools/codol_export_c1_keys.py) holds exactly those two regions,
 * IWD blob then RSA DER, so a server can run without shipping C1.exe. Reads one
 * region at its C1.exe offset from either file; the callers' SHA-256 checks are
 * what make a wrong or truncated file fail. */
int CODOL_ReadClientRegion(const char *path,unsigned long exe_offset,uint8_t *out,size_t size);
/* <basepath>/C1.exe when it exists, otherwise <basepath>/c1_keys.bin. */
int CODOL_DefaultClientKeyPath(const char *basepath,char *out,size_t size);
#endif
