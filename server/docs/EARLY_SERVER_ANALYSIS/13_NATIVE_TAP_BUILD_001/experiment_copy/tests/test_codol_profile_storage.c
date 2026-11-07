#include "codol_profile.h"
#include "codol_stats.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "zlib/zlib.h"
#include <unistd.h>
static void write_bytes(const char *path,const uint8_t *data,size_t n)
{ FILE *f=fopen(path,"wb");assert(f);assert(fwrite(data,1,n,f)==n);assert(!fclose(f)); }
static void selection(const uint8_t *compressed,size_t n)
{
    char root[]="/tmp/sh1x-profile-XXXXXX",seed[256],shared[256],user[256];
    uint8_t out[CODOL_STATS_SIZE],saved[CODOL_STATS_SIZE];
    assert(mkdtemp(root));memset(out,0xa5,sizeof(out));memcpy(saved,out,sizeof(out));
    snprintf(seed,sizeof(seed),"%s/seed",root);snprintf(shared,sizeof(shared),"%s/mpdata_s",root);
    snprintf(user,sizeof(user),"%s/mpdata_s.18446744073709551615",root);
    assert(CODOL_ReadSecureProfile(root,1,1,"seed",out,sizeof(out))==0);
    assert(!memcmp(saved,out,sizeof(out)));
    assert(CODOL_ReadSecureProfile(root,1,1,"../seed",out,sizeof(out))==-1);
    write_bytes(seed,compressed,n);
    assert(CODOL_ReadSecureProfile(root,1,1,"seed",out,sizeof(out))==1);
    memcpy(saved,out,sizeof(out));write_bytes(shared,(const uint8_t *)"bad",3);
    assert(CODOL_ReadSecureProfile(root,1,1,"seed",out,sizeof(out))==-1);
    assert(!memcmp(saved,out,sizeof(out)));
    write_bytes(user,compressed,n);
    assert(CODOL_ReadSecureProfile(root,UINT64_MAX,1,"seed",out,sizeof(out))==1);
    assert(CODOL_ReadSecureProfile(root,UINT64_MAX,0,"seed",out,sizeof(out))==-1);
    assert(CODOL_ReadSecureProfile(root,0,1,"seed",out,sizeof(out))==-1);
    write_bytes(shared,compressed,n);write_bytes(user,(const uint8_t *)"bad",3);
    assert(CODOL_ReadSecureProfile(root,UINT64_MAX,1,"seed",out,sizeof(out))==-1);
    assert(CODOL_ReadSecureProfile(root,2,1,"seed",out,sizeof(out))==1);
    assert(!unlink(user) && !unlink(shared) && !unlink(seed) && !rmdir(root));
}
voidpf zcalloc(voidpf unused,unsigned n,unsigned size)
{ (void)unused;return calloc(n,size); }
void zcfree(voidpf unused,voidpf p)
{ (void)unused;free(p); }
int main(void)
{
    uint8_t compressed[1024],decoded[CODOL_STATS_SIZE],saved[CODOL_STATS_SIZE];size_t n,i;
    FILE *f=fopen("tests/fixtures/profile_storage_synthetic.zlib","rb");assert(f);
    n=fread(compressed,1,sizeof(compressed),f);assert(n && !ferror(f) && !fclose(f));
    memset(decoded,0xa5,sizeof(decoded));memcpy(saved,decoded,sizeof(saved));
    for(i=0;i<n;++i) {
        assert(!CODOL_DecodeStoredProfile(compressed,i,decoded,sizeof(decoded)));
        assert(!memcmp(decoded,saved,sizeof(decoded)));
    }
    assert(!CODOL_DecodeStoredProfile(compressed,n,decoded,sizeof(decoded)-1));
    compressed[n]=0;assert(!CODOL_DecodeStoredProfile(compressed,n+1,decoded,sizeof(decoded)));
    assert(CODOL_DecodeStoredProfile(compressed,n,decoded,sizeof(decoded)));
    selection(compressed,n);
    assert(decoded[4]==11 && decoded[8]==0x57 && decoded[9]==0x8f && decoded[10]==0x6b && decoded[11]==9);
    for(i=12;i<sizeof(decoded);++i)assert(decoded[i]==0);
    f=fopen("tests/fixtures/profile_storage_bad_crc.zlib","rb");assert(f);
    n=fread(compressed,1,sizeof(compressed),f);assert(n && !ferror(f) && !fclose(f));
    memcpy(saved,decoded,sizeof(saved));
    assert(!CODOL_DecodeStoredProfile(compressed,n,decoded,sizeof(decoded)));
    assert(!memcmp(decoded,saved,sizeof(decoded)));
    puts("PASS: stored profile exact inflation, CRC, truncations and atomic failure");
}
