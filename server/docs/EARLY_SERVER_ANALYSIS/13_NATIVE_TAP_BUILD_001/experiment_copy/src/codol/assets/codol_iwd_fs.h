#ifndef CODOL_IWD_FS_H
#define CODOL_IWD_FS_H
#include "zlib/unzip.h"
#include <stdint.h>
/* C1 archive checksum input: CRC plus full filename hash bucket. */
uint32_t CODOL_IwdChecksumWord(const char *name, uint32_t crc, uint32_t hash_size);
/* Initialize before indexing archives. Failure clears previous key state;
 * existing ZIP handles own their keys and remain independently usable. */
int CODOL_InitIwdFilesystem(const char *client_exe);
void CODOL_ClearIwdFilesystem(void);
int CODOL_IsEncryptedIwd(const char *path);
unzFile CODOL_OpenIwdArchive(const char *path);
#endif
