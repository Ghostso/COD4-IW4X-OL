#include "codol_xsurface.h"
#include "codol_asset_stream.h"
#include <stdlib.h>
#include <string.h>
#include <math.h>
static uint32_t u32(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static unsigned u16(const uint8_t *p) { return p[0]|(unsigned)p[1]<<8; }
void CODOL_FreeSurfaceArrays(codol_surface_arrays_t *out)
{
    if (!out) return;
    free(out->storage); memset(out,0,sizeof(*out));
}
int CODOL_ResolveSurfaceArrays(const codol_surface_t *source,const codol_model_block_t blocks[8],codol_surface_arrays_t *out)
{
    static const unsigned strides[3]={2,32,6};
    const uint8_t *data[3];
    unsigned counts[3]={0},i,j;
    size_t size=45,p=0;
    codol_surface_arrays_t result={0};
    if (!source || !blocks || !out) return 0;
    for (i=0;i<4;++i) {
        unsigned n=u16(source->header+20+2*i);
        if (n>32767) return 0;
        counts[0]+=n*(2*i+1);
    }
    counts[1]=u16(source->header+4); counts[2]=u16(source->header+6);
    for (i=0;i<3;++i) {
        const codol_model_array_t *a=source->arrays+i;
        size_t length=(size_t)counts[i]*strides[i];
        if (a->count!=counts[i] || a->stride!=strides[i]) return 0;
        data[i]=a->data;
        if (length && !data[i]) {
            uint32_t ref=a->reference;
            unsigned block; size_t offset;
            if (!ref || ref>=UINT32_MAX-1) return 0;
            --ref; block=ref>>28; offset=ref&0xfffffff;
            if (block>=8 || !blocks[block].data || offset>blocks[block].size ||
                length>blocks[block].size-offset) return 0;
            data[i]=blocks[block].data+offset;
        }
        size+=length;
    }
    for (i=0;i<counts[1];++i) for (j=0;j<4;++j) {
        uint32_t bits=u32(data[1]+32*i+4*j); float value;
        memcpy(&value,&bits,4); if (!isfinite(value)) return 0;
    }
    for (i=0;i<counts[2]*3;++i) if (u16(data[2]+2*i)>=counts[1]) return 0;
    if (!(result.storage=malloc(size))) return 0;
    for (i=0;i<3;++i) {
        size_t length=(size_t)counts[i]*strides[i];
        result.arrays[i]=source->arrays[i]; result.arrays[i].data=NULL;
        if (!length) continue;
        p+=(16-((uintptr_t)(result.storage+p)&15))&15;
        result.arrays[i].data=result.storage+p;
        memcpy(result.storage+p,data[i],length); p+=length;
    }
    *out=result; return 1;
}
void CODOL_FreeModelSurfaces(codol_model_surfaces_t *out)
{
    if (!out) return;
    free(out->surfaces); free(out->storage); memset(out,0,sizeof(*out));
}
static void array(codol_model_surfaces_t *m,codol_model_array_t *a,
                  uint32_t reference,unsigned count,unsigned stride,size_t *p)
{
    a->reference=reference; a->count=count; a->stride=stride;
    if (reference==UINT32_MAX) {
        a->data=m->storage+*p; *p+=(size_t)count*stride;
    } else if (reference && count) ++m->unresolved;
}
int CODOL_ReadModelSurfaces(const codol_asset_t *asset,codol_model_surfaces_t *out)
{
    codol_model_surfaces_t m={0};
    size_t extent=0,p=48,start;
    unsigned i,j;
    const uint8_t *b;
    if (!asset || !out || asset->type!=3 ||
        !CODOL_AdvanceModelSurfacesStream(asset->data,asset->size,&extent)) return 0;
    m.storage=malloc(extent);
    if (!m.storage) return 0;
    memcpy(m.storage,asset->data,extent); b=m.storage;
    m.name_reference=u32(b); m.surfaces_reference=u32(b+4); m.count=u16(b+8); m.consumed=extent;
    if (m.name_reference==UINT32_MAX) { m.name=(const char *)b+p; p+=strlen(m.name)+1; }
    else if (m.name_reference) ++m.unresolved;
    if (!m.surfaces_reference) {
        if (m.count) goto fail;
        *out=m; return 1;
    }
    if (m.count && !(m.surfaces=calloc(m.count,sizeof(*m.surfaces)))) goto fail;
    start=p; p+=(size_t)m.count*84;
    for (i=0;i<m.count;++i) {
        codol_surface_t *s=m.surfaces+i;
        const uint8_t *h=b+start+84*i;
        unsigned blend=0;
        memcpy(s->header,h,sizeof(s->header));
        for (j=0;j<4;++j) {
            unsigned n=u16(h+20+2*j);
            if (n>32767) goto fail;
            blend+=n*(2*j+1);
        }
        array(&m,&s->arrays[0],u32(h+28),blend,2,&p);
        array(&m,&s->arrays[1],u32(h+32),u16(h+4),32,&p);
        s->rigid_reference=u32(h+44); s->rigid_count=u32(h+40);
        if (s->rigid_reference==UINT32_MAX) {
            size_t rigid=p;
            s->rigid_stream=b+p; p+=(size_t)s->rigid_count*12;
            for (j=0;j<s->rigid_count;++j) {
                uint32_t ref=u32(b+rigid+12*j+8);
                if (ref==UINT32_MAX) {
                    const uint8_t *tree=b+p; p+=40;
                    if (u32(tree+28)) p+=(size_t)u32(tree+24)*16;
                    if (u32(tree+36)) p+=(size_t)u32(tree+32)*2;
                } else if (ref) ++m.unresolved;
            }
            s->rigid_stream_size=p-rigid;
        } else if (s->rigid_reference && s->rigid_count) ++m.unresolved;
        array(&m,&s->arrays[2],u32(h+16),u16(h+6),6,&p);
    }
    if (p!=extent) goto fail;
    *out=m; return 1;
fail:
    CODOL_FreeModelSurfaces(&m); return 0;
}
