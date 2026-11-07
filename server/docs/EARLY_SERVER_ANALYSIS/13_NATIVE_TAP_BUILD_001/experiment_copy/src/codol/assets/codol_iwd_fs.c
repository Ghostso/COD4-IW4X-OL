#ifdef CODOL_SERVER
#include "codol_iwd_fs.h"
#include "codol_iwd_crypto.h"
#include <string.h>
static unsigned char iwd_key[24];
static int key_ready;
uint32_t CODOL_IwdChecksumWord(const char *name, uint32_t crc, uint32_t hash_size)
{
    uint32_t hash = 0, i;
    /* C1 0x6159f0 hashes the extension too; FS_HashFileName stops at '.'.
     * Archive names have already been lowercased by the native loader. */
    for (i = 0; name[i]; ++i) {
        int32_t letter = (int8_t)name[i];
        if (letter >= 'A' && letter <= 'Z') letter += 'a' - 'A';
        if (letter == '\\') letter = '/';
        hash += (uint32_t)letter * (i + 119u);
    }
    /* Explicit arithmetic shifts reproduce the signed x86 hash folding. */
    {
        uint32_t shift10 = (hash >> 10) | ((hash & 0x80000000u) ? 0xffc00000u : 0);
        uint32_t shift20 = (hash >> 20) | ((hash & 0x80000000u) ? 0xfffff000u : 0);
        hash ^= shift10 ^ shift20;
    }
    return crc + (hash & (hash_size - 1u));
}
void CODOL_ClearIwdFilesystem(void)
{
    volatile unsigned char *p=iwd_key; unsigned i;
    for(i=0;i<sizeof(iwd_key);++i) p[i]=0;
    key_ready=0;
}
int CODOL_InitIwdFilesystem(const char *exe)
{
    CODOL_ClearIwdFilesystem();
    key_ready=CODOL_ReadIwdKey(exe,iwd_key); return key_ready;
}
int CODOL_IsEncryptedIwd(const char *path)
{
    static const char *const patterns[]={"iw_image","iw_model","iw_config","iw_sound","iw_ui_image","iw_adlc"};
    const char *base,*p; unsigned i;
    if (!path) return 0;
    base=path;
    for(p=path;*p;++p) if(*p=='/' || *p=='\\') base=p+1;
    for(i=0;i<sizeof(patterns)/sizeof(*patterns);++i) if(strstr(base,patterns[i])) return 1;
    return 0;
}
unzFile CODOL_OpenIwdArchive(const char *path)
{
    if (!path) return NULL;
    if (CODOL_IsEncryptedIwd(path)) return key_ready ? unzOpenIwd(path,iwd_key) : NULL;
    return unzOpen(path);
}
#endif
