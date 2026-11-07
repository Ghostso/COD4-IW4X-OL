#include "codol_stream_model.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
static codol_stream_model_loader_t loader;
static unsigned reads,frees;
static int mode;
int CODOL_SetStreamModelLoader(codol_stream_model_loader_t f,void *context)
{ assert(!context); loader=f; return 1; }
static void put32(unsigned char *p,unsigned v)
{ unsigned i; for(i=0;i<4;++i) p[i]=(unsigned char)(v>>(8*i)); }
int FS_ReadFile(const char *path,void **out)
{
    unsigned char *b; unsigned i;
    assert(!strcmp(path,"models/lod")); ++reads;
    if(mode==1) { *out=NULL; return -1; }
    b=calloc(1,136); assert(b);
    put32(b,mode==2 ? 2 : 1); put32(b+4,0xe9c9c447);
    put32(b+8,48); put32(b+12,88);
    for(i=1;i<4;++i) put32(b+12+20*i,136);
    b[88]=42; *out=b; return 136;
}
void FS_FreeFile(void *p) { assert(p); ++frees; memset(p,0,136); free(p); }
int main(void)
{
    codol_stream_model_t model={0},saved;
    unsigned i; char long_name[300];
    const char *invalid[]={"", ".", "..", "../lod", "a/lod", "a\\lod", "C:lod"};
    CODOL_InitEngineStreamModels(); assert(loader);
    assert(loader(NULL,"lod",&model)==1 && reads==1 && frees==1);
    assert(model.blocks[3].data[0]==42); saved=model;
    for(i=0;i<sizeof(invalid)/sizeof(*invalid);++i) assert(loader(NULL,invalid[i],&model)==-1);
    memset(long_name,'a',sizeof(long_name)-1); long_name[sizeof(long_name)-1]=0;
    assert(loader(NULL,long_name,&model)==-1 && reads==1);
    mode=1; assert(loader(NULL,"lod",&model)==0 && frees==1);
    assert(!memcmp(&model,&saved,sizeof(model)));
    mode=2; assert(loader(NULL,"lod",&model)==-1 && frees==2);
    assert(!memcmp(&model,&saved,sizeof(model)) && model.blocks[3].data[0]==42);
    CODOL_FreeStreamModel(&model);
    puts("PASS: engine streamed-model filesystem adapter and ownership"); return 0;
}
