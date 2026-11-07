#include "codol_iwd_crypto.h"
#include "codol_client_crypto.h"
#include "mbedtls/aes.h"
#include "mbedtls/sha256.h"
#include <stdio.h>
#include <string.h>
int CODOL_ReadIwdKey(const char *exe,uint8_t out[24])
{
    static const uint8_t expected[32]={0xe0,0xad,0x40,0xd9,0xae,0xf6,0x69,0xc1,
        0xa4,0x9a,0x5b,0x7d,0xa0,0xe3,0x16,0xff,0x70,0x42,0xe2,0x71,0xff,0xd6,0x1c,0xf1,
        0x34,0x01,0x2b,0x4b,0xfb,0x39,0x3c,0xb3};
    uint8_t blob[CODOL_C1_IWD_BLOB_SIZE],digest[32]; int ok;
    if (!out || !exe) return 0;
    /* C1 0x59dc60 references encrypted data at VA 0xc39b20 (file 0x838b20). */
    ok=CODOL_ReadClientRegion(exe,CODOL_C1_IWD_BLOB_OFFSET,blob,sizeof(blob));
    return ok && !mbedtls_sha256_ret(blob,sizeof(blob),digest,0) &&
        !memcmp(digest,expected,32) && CODOL_DecryptClientMaterial(exe,blob,out,24);
}
static void put32(uint8_t *p,uint32_t v)
{ unsigned i; for(i=0;i<4;++i) p[i]=(uint8_t)(v>>(8*i)); }
static int crypt(const uint8_t key[24],uint32_t a,uint32_t b,uint32_t c,
    const uint8_t *in,uint8_t *out,size_t length)
{
    mbedtls_aes_context aes; uint8_t counter[16],stream[16]={0}; size_t off=0; int ok;
    if (!key || (length && (!in || !out))) return 0;
    put32(counter,a); put32(counter+4,b); put32(counter+8,c); put32(counter+12,0x01010101);
    mbedtls_aes_init(&aes);
    /* mbedTLS CTR increments the big-endian 128-bit counter, unlike fastfiles. */
    ok=!mbedtls_aes_setkey_enc(&aes,key,192) &&
        !mbedtls_aes_crypt_ctr(&aes,length,&off,counter,stream,in,out);
    mbedtls_aes_free(&aes); memset(stream,0,sizeof(stream)); return ok;
}
int CODOL_IwdCryptFilename(const uint8_t key[24],uint32_t archive,uint32_t index,
    const uint8_t *in,uint8_t *out,size_t length)
{ return length<=65535 && crypt(key,0x01010101,archive,index,in,out,length); }
int CODOL_IwdCryptDataChunk(const uint8_t key[24],uint32_t archive,uint32_t offset,
    const uint8_t *in,uint8_t *out,size_t length)
{ return length<=0x4000 && crypt(key,offset,archive,0x01010101,in,out,length); }
