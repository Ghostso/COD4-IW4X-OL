/* C1 1.1.1.13 loaders: GfxWorld 0x4c7fe0, skies 0x4c7cb0,
 * DPVS planes 0x4c7b00, image 0x4b92d0, image loaddef 0x4b9250.
 * Allocation alignment applies to memory blocks, not serialized file bytes. */
#include "codol_collision.h"
#include <string.h>
static uint32_t u32(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static int take(size_t *p,size_t size,uint32_t count,unsigned stride)
{
    if (*p>size || count>(size-*p)/stride) return 0;
    *p+=(size_t)count*stride; return 1;
}
static int string(const uint8_t *b,size_t size,size_t *p)
{
    const uint8_t *end;
    if (*p>=size || !(end=memchr(b+*p,0,size-*p))) return 0;
    *p=(size_t)(end-b)+1; return 1;
}
static int image(const uint8_t *b,size_t size,size_t *p)
{
    size_t header=*p,def;
    if (!take(p,size,1,36)) return 0;
    if (u32(b+header+32)==UINT32_MAX && !string(b,size,p)) return 0;
    if (u32(b+header)==UINT32_MAX) {
        def=*p;
        if (!take(p,size,1,16) || !take(p,size,u32(b+def+12),1)) return 0;
    }
    return 1;
}
const char *CODOL_WorldBaseName(const codol_asset_t *asset)
{
    size_t p=0x274,start;
    if (!asset || asset->type!=21 || !asset->data || asset->size<p || asset->size>CODOL_ASSET_LIMIT) return NULL;
    if (u32(asset->data)==UINT32_MAX && !string(asset->data,asset->size,&p)) return NULL;
    if (u32(asset->data+4)!=UINT32_MAX) return NULL;
    start=p;
    if (!string(asset->data,asset->size,&p)) return NULL;
    return (const char *)(asset->data+start);
}
int CODOL_ReadWorldPlanes(const codol_asset_t *asset,codol_world_planes_t *out)
{
    codol_world_planes_t result={0};
    const uint8_t *b;
    size_t p=0x274,size,skies,i;
    uint32_t count;
    if (!asset || !out || asset->type!=21 || !asset->data ||
        asset->size<p || asset->size>CODOL_ASSET_LIMIT) return 0;
    b=asset->data; size=asset->size;
    result.name_reference=u32(b);
    if (result.name_reference==UINT32_MAX) {
        result.name=(const char *)(b+p);
        if (!string(b,size,&p)) return 0;
    }
    if (u32(b+4)==UINT32_MAX && !string(b,size,&p)) return 0;
    count=u32(b+0x14); skies=p;
    if (u32(b+0x18)) {
        if (!take(&p,size,count,16)) return 0;
        for (i=0;i<count;++i) {
            const uint8_t *sky=b+skies+16*i;
            uint32_t ref=u32(sky+8);
            if (u32(sky+4) && !take(&p,size,u32(sky),4)) return 0;
            if ((ref==UINT32_MAX || ref==UINT32_MAX-1) && !image(b,size,&p)) return 0;
        }
    } else if (count) return 0;
    /* This entry owns inline planes; pooled planes need a different owner. */
    if (u32(b+0x38)!=UINT32_MAX) return 0;
    result.offset=p; result.count=u32(b+8);
    if (!take(&p,size,result.count,20)) return 0;
    *out=result; return 1;
}
int CODOL_ReadWorldBrushes(const codol_asset_t *collision,const codol_asset_t *world,
                           codol_collision_brushes_t *out)
{
    codol_world_planes_t planes;
    codol_collision_layout_t layout;
    if (!out || !CODOL_ReadCollisionLayout(collision,&layout) ||
        !CODOL_ReadWorldPlanes(world,&planes) || !planes.name_reference ||
        planes.name_reference!=layout.name_reference ||
        planes.count!=layout.sections[CODOL_COLL_PLANES].count) return 0;
    if (planes.name_reference==UINT32_MAX &&
        strcmp(planes.name,(const char *)(collision->data+256))) return 0;
    return CODOL_ReadCollisionBrushes(collision,world->data+planes.offset,
                                     (size_t)planes.count*20,out);
}
