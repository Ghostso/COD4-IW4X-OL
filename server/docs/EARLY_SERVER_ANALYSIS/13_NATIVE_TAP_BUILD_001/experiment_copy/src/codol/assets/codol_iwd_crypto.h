#ifndef CODOL_IWD_CRYPTO_H
#define CODOL_IWD_CRYPTO_H
#include <stdint.h>
#include <stddef.h>
int CODOL_ReadIwdKey(const char *client_exe,uint8_t out[24]);
/* Archive key is CRC32 of the archive basename, including .iwd. Filenames use
 * the central-directory ordinal. Data is processed in 0x4000-byte chunks using
 * each chunk's absolute file offset; never reseed at a caller's read boundary. */
int CODOL_IwdCryptFilename(const uint8_t key[24],uint32_t archive_key,uint32_t index,
    const uint8_t *,uint8_t *,size_t);
int CODOL_IwdCryptDataChunk(const uint8_t key[24],uint32_t archive_key,uint32_t offset,
    const uint8_t *,uint8_t *,size_t);
#endif
