#include "codol_stream_model.h"
#include <stdlib.h>
#include <string.h>
static uint32_t u32(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static void put32(uint8_t *p,uint32_t v)
{ unsigned i; for(i=0;i<4;++i) p[i]=(uint8_t)(v>>(8*i)); }
void CODOL_FreeStreamModel(codol_stream_model_t *m)
{
    unsigned i;
    if (!m) return;
    for(i=0;i<3;++i) free(m->storage[i]);
    memset(m,0,sizeof(*m));
}
int CODOL_ReadStreamModel(const uint8_t *b,size_t length,codol_stream_model_t *out)
{
    static const unsigned map[3]={3,6,7};
    uint32_t size[4],offset[4],start[4],count[4];
    codol_stream_model_t result={0};
    unsigned i,j;
    /* Header/version checks and relocation-table limit: C1 0x4c9f98..0x4ca036.
     * Schema ID measured across all installed 1.1.1.13 model archives. */
    if (!b || !out || length<88 || u32(b)!=1 || u32(b+4)!=0xe9c9c447) return 0;
    for(i=0;i<4;++i) {
        const uint8_t *d=b+8+20*i;
        size[i]=u32(d); offset[i]=u32(d+4); start[i]=u32(d+8); count[i]=u32(d+12);
        if(size[i]>0xfffffff || offset[i]>length || size[i]>length-offset[i] ||
           (size[i] && offset[i]<88)) return 0;
        for(j=0;j<i;++j) if(size[i] && size[j] && offset[i]<(size_t)offset[j]+size[j] &&
            offset[j]<(size_t)offset[i]+size[i]) return 0;
    }
    if(size[0]<48 || size[3]>=0x4000 || size[3]%4) return 0;
    for(i=0;i<3;++i) {
        if(start[i]>size[3]/4 || count[i]>size[3]/4-start[i]) return 0;
        for(j=0;j<count[i];++j) {
            uint32_t fix=u32(b+offset[3]+4*(start[i]+j)),location=fix>>3,target=fix&7;
            if(target>2 || size[i]<4 || location>size[i]-4 || location%4 ||
                u32(b+offset[i]+location)>=size[target]) return 0;
        }
    }
    for(i=0;i<3;++i) {
        if(size[i]) {
            result.storage[i]=malloc(size[i]); if(!result.storage[i]) goto fail;
            memcpy(result.storage[i],b+offset[i],size[i]);
        }
        result.blocks[map[i]]=(codol_model_block_t){result.storage[i],size[i]};
    }
    /* C1 0x5817d0: low three bits select target, high bits locate the word
     * in the current block. Read original words so repeated relocations cannot
     * turn an already encoded reference into a second offset. */
    for(i=0;i<3;++i) for(j=0;j<count[i];++j) {
        uint32_t fix=u32(b+offset[3]+4*(start[i]+j)),location=fix>>3,target=fix&7;
        put32(result.storage[i]+location,((uint32_t)map[target]<<28)+u32(b+offset[i]+location)+1);
    }
    *out=result; return 1;
fail:
    CODOL_FreeStreamModel(&result); return 0;
}
static unsigned u16(const uint8_t *p) { return p[0]|(unsigned)p[1]<<8; }
static const uint8_t *root_ref(const codol_stream_model_t *m,uint32_t ref,size_t bytes)
{
    size_t offset;
    if (!ref || ((ref-1)>>28)!=3) return NULL;
    offset=(ref-1)&0xfffffff;
    if (offset>m->blocks[3].size || bytes>m->blocks[3].size-offset) return NULL;
    return m->blocks[3].data+offset;
}
int CODOL_ReadStreamModelSurfaces(const codol_stream_model_t *m,codol_model_surfaces_t *out)
{
    codol_model_surfaces_t result={0};
    const uint8_t *root,*name,*end,*headers;
    size_t name_size;
    unsigned i,j;
    if (!m || !out || !m->blocks[3].data || m->blocks[3].size<48) return 0;
    root=m->blocks[3].data;
    result.name_reference=u32(root); result.surfaces_reference=u32(root+4); result.count=u16(root+8);
    name=root_ref(m,result.name_reference,1);
    if (!name) return 0;
    end=memchr(name,0,m->blocks[3].size-(size_t)(name-root)); if (!end) return 0;
    name_size=(size_t)(end-name)+1;
    headers=root_ref(m,result.surfaces_reference,(size_t)result.count*84);
    if (result.count && !headers) return 0;
    result.storage=malloc(name_size);
    if (!result.storage) return 0;
    memcpy(result.storage,name,name_size); result.name=(const char *)result.storage;
    if (result.count && !(result.surfaces=calloc(result.count,sizeof(*result.surfaces)))) goto fail;
    for(i=0;i<result.count;++i) {
        codol_surface_t *s=result.surfaces+i;
        const uint8_t *h=headers+84*i;
        unsigned blend=0;
        memcpy(s->header,h,84);
        for(j=0;j<4;++j) blend+=u16(h+20+2*j)*(2*j+1);
        s->arrays[0]=(codol_model_array_t){u32(h+28),blend,2,NULL};
        s->arrays[1]=(codol_model_array_t){u32(h+32),u16(h+4),32,NULL};
        s->arrays[2]=(codol_model_array_t){u32(h+16),u16(h+6),6,NULL};
        s->rigid_count=u32(h+40); s->rigid_reference=u32(h+44);
        s->relocated_tree_arrays=1;
    }
    *out=result; return 1;
fail:
    free(result.surfaces); free(result.storage); return 0;
}
