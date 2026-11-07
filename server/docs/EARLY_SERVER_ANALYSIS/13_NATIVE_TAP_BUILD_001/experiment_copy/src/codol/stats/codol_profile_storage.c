#include "codol_profile.h"
#include "codol_stats.h"
#include "zlib/zlib.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <errno.h>
#include <inttypes.h>
int CODOL_DecodeStoredProfile(const uint8_t *compressed,size_t size,uint8_t *out,size_t capacity)
{
    uint8_t *decoded=NULL;size_t length=0;uint32_t expected;int ok=0;
    if(!out || capacity<CODOL_STATS_SIZE || !compressed || !size || size>CODOL_STATS_SIZE+1024)return 0;
    if(!CODOL_Inflate(compressed,size,&decoded,&length,CODOL_STATS_SIZE,0))return 0;
    if(length==CODOL_STATS_SIZE) {
        expected=(uint32_t)decoded[0]|(uint32_t)decoded[1]<<8|
            (uint32_t)decoded[2]<<16|(uint32_t)decoded[3]<<24;
        if((uint32_t)crc32(0,decoded+4,CODOL_STATS_SIZE-4)==expected) {
            memcpy(out,decoded,CODOL_STATS_SIZE);ok=1;
        }
    }
    free(decoded);return ok;
}
static int read_file(const char *directory,const char *name,uint8_t *out,size_t capacity)
{
    char path[4096];FILE *f;long size;uint8_t *compressed;int written,ok;
    written=snprintf(path,sizeof(path),"%s/%s",directory,name);
    if(written<0 || (size_t)written>=sizeof(path))return -1;
    f=fopen(path,"rb");if(!f)return errno==ENOENT ? 0 : -1;
    if(fseek(f,0,SEEK_END) || (size=ftell(f))<=0 || (unsigned long)size>CODOL_STATS_SIZE+1024 || fseek(f,0,SEEK_SET)) {
        fclose(f);return -1;
    }
    compressed=malloc((size_t)size);if(!compressed) {fclose(f);return -1;}
    ok=fread(compressed,1,(size_t)size,f)==(size_t)size && !ferror(f);
    if(fclose(f))ok=0;
    if(ok)ok=CODOL_DecodeStoredProfile(compressed,(size_t)size,out,capacity);
    free(compressed);return ok ? 1 : -1;
}
int CODOL_ReadSecureProfile(const char *directory,uint64_t uid,int per_uid,
    const char *seed,uint8_t *out,size_t capacity)
{
    char name[64];int status;const char *p;
    if(!directory || !*directory || !out || capacity<CODOL_STATS_SIZE)return -1;
    if(seed && *seed) {
        if(!strcmp(seed,".") || !strcmp(seed,".."))return -1;
        for(p=seed;*p;++p)if(*p=='/' || *p=='\\' || *p==':' || (unsigned char)*p<32)return -1;
    }
    if(per_uid && uid) {
        snprintf(name,sizeof(name),"mpdata_s.%" PRIu64,uid);
        status=read_file(directory,name,out,capacity);if(status)return status;
    }
    status=read_file(directory,"mpdata_s",out,capacity);if(status)return status;
    return seed && *seed ? read_file(directory,seed,out,capacity) : 0;
}
