/* C1 material 0x4ba280, texture 0x4b9f80, image 0x4b92d0. */
#include "codol_asset_stream.h"
#include "codol_assets.h"
#include <string.h>
static uint32_t u32(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static unsigned u16(const uint8_t *p) { return p[0]|(unsigned)p[1]<<8; }
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
/* C1 0x4bb3f0: PhysPreset, 68 bytes, name then sound prefix. */
int CODOL_AdvancePhysicsPresetStream(const uint8_t *b,size_t size,size_t *position)
{
    size_t p,h;
    if (!b || !position || size>CODOL_ASSET_LIMIT) return 0;
    p=h=*position;
    if (!take(&p,size,1,68)) return 0;
    if (u32(b+h)==UINT32_MAX && !string(b,size,&p)) return 0;
    if (u32(b+h+28)==UINT32_MAX && !string(b,size,&p)) return 0;
    *position=p; return 1;
}
/* C1 0x4bb650/0x4bb5c0/0x4bb360/0x4bb2c0. */
int CODOL_AdvancePhysicsMapStream(const uint8_t *b,size_t size,size_t *position)
{
    size_t p,h,geoms;
    uint32_t i,count;
    if (!b || !position || size>CODOL_ASSET_LIMIT) return 0;
    p=h=*position;
    if (!take(&p,size,1,72)) return 0;
    if (u32(b+h)==UINT32_MAX && !string(b,size,&p)) return 0;
    if (u32(b+h+8)) {
        geoms=p; count=u32(b+h+4);
        if (!take(&p,size,count,68)) return 0;
        for (i=0;i<count;++i) if (u32(b+geoms+68*i)) {
            size_t brush=p,sides;
            unsigned j,n;
            if (!take(&p,size,1,68)) return 0;
            n=u16(b+brush+24);
            if (u32(b+brush+28)) {
                sides=p;
                if (!take(&p,size,n,8)) return 0;
                for (j=0;j<n;++j)
                    if (u32(b+sides+8*j)==UINT32_MAX && !take(&p,size,1,20)) return 0;
            }
            if (u32(b+brush+32) && !take(&p,size,u32(b+brush+60),1)) return 0;
            if (u32(b+brush+64)==UINT32_MAX && !take(&p,size,n,20)) return 0;
        }
    }
    *position=p; return 1;
}
int CODOL_AdvanceImageStream(const uint8_t *b,size_t size,size_t *position)
{
    size_t p,header,def;
    if (!b || !position || size>CODOL_ASSET_LIMIT) return 0;
    p=header=*position;
    if (!take(&p,size,1,36)) return 0;
    if (u32(b+header+32)==UINT32_MAX && !string(b,size,&p)) return 0;
    if (u32(b+header)==UINT32_MAX) {
        def=p;
        if (!take(&p,size,1,16) || !take(&p,size,u32(b+def+12),1)) return 0;
    }
    *position=p; return 1;
}
/* C1 water loader 0x4b95a0: 68-byte header, two M*N arrays, image. */
int CODOL_AdvanceWaterStream(const uint8_t *b,size_t size,size_t *position)
{
    size_t p,h;
    uint32_t m,n,ref;
    uint64_t cells;
    if (!b || !position || size>CODOL_ASSET_LIMIT) return 0;
    p=h=*position;
    if (!take(&p,size,1,68)) return 0;
    m=u32(b+h+12); n=u32(b+h+16); cells=(uint64_t)m*n;
    if (m>INT32_MAX || n>INT32_MAX || cells>UINT32_MAX) return 0;
    if (u32(b+h+4) && !take(&p,size,(uint32_t)cells,8)) return 0;
    if (u32(b+h+8) && !take(&p,size,(uint32_t)cells,4)) return 0;
    ref=u32(b+h+64);
    if (ref>=UINT32_MAX-1 && !CODOL_AdvanceImageStream(b,size,&p)) return 0;
    *position=p; return 1;
}
static int shader(const uint8_t *b,size_t size,size_t *p)
{
    size_t h=*p;
    if (!take(p,size,1,16)) return 0;
    if (u32(b+h)==UINT32_MAX && !string(b,size,p)) return 0;
    return !u32(b+h+8) || take(p,size,u16(b+h+12),4);
}
/* C1 0x4ba130 / 0x4b9ef0. The technique name follows its passes. */
int CODOL_AdvanceTechniqueSetStream(const uint8_t *b,size_t size,size_t *position)
{
    size_t p,h;
    unsigned i,j,k;
    if (!b || !position || size>CODOL_ASSET_LIMIT) return 0;
    p=h=*position;
    if (!take(&p,size,1,204)) return 0;
    if (u32(b+h)==UINT32_MAX && !string(b,size,&p)) return 0;
    for (i=0;i<48;++i) if (u32(b+h+12+4*i)==UINT32_MAX) {
        size_t technique=p,passes;
        unsigned count;
        if (!take(&p,size,1,8)) return 0;
        count=u16(b+technique+6); passes=p;
        if (!take(&p,size,count,20)) return 0;
        for (j=0;j<count;++j) {
            const uint8_t *pass=b+passes+20*j;
            if (u32(pass)>=UINT32_MAX-1) {
                size_t decl=p;
                if (!take(&p,size,1,100)) return 0;
                if (u32(b+decl)==UINT32_MAX && !string(b,size,&p)) return 0;
            }
            if (u32(pass+4)>=UINT32_MAX-1 && !shader(b,size,&p)) return 0;
            if (u32(pass+8)>=UINT32_MAX-1 && !shader(b,size,&p)) return 0;
            if (u32(pass+16)) {
                unsigned args=pass[12]+pass[13]+pass[14];
                size_t arg=p;
                if (!take(&p,size,args,8)) return 0;
                for (k=0;k<args;++k) {
                    unsigned type=u16(b+arg+8*k);
                    if ((type==1 || type==7) && u32(b+arg+8*k+4)==UINT32_MAX && !take(&p,size,1,16)) return 0;
                }
            }
        }
        if (u32(b+technique)==UINT32_MAX && !string(b,size,&p)) return 0;
    }
    *position=p; return 1;
}
int CODOL_AdvanceMaterialStream(const uint8_t *b,size_t size,size_t *position)
{
    size_t p,h,textures;
    unsigned i;
    if (!b || !position || size>CODOL_ASSET_LIMIT) return 0;
    p=h=*position;
    if (!take(&p,size,1,96)) return 0;
    if (u32(b+h)==UINT32_MAX && !string(b,size,&p)) return 0;
    if (u32(b+h+0x50)>=UINT32_MAX-1 && !CODOL_AdvanceTechniqueSetStream(b,size,&p)) return 0;
    if (u32(b+h+0x54)==UINT32_MAX) {
        textures=p;
        if (!take(&p,size,b[h+0x48],12)) return 0;
        for (i=0;i<b[h+0x48];++i) {
            const uint8_t *texture=b+textures+12*i;
            uint32_t ref=u32(texture+8);
            if (texture[7]==11) {
                if (ref==UINT32_MAX && !CODOL_AdvanceWaterStream(b,size,&p)) return 0;
            } else if (ref>=UINT32_MAX-1 && !CODOL_AdvanceImageStream(b,size,&p)) return 0;
        }
    }
    if (u32(b+h+0x58)==UINT32_MAX && !take(&p,size,b[h+0x49],32)) return 0;
    if (u32(b+h+0x5c)==UINT32_MAX && !take(&p,size,b[h+0x4a],8)) return 0;
    *position=p; return 1;
}
/* XModelSurfs 0x4bb890, XSurface 0x4b8ff0, collision tree 0x4b8d50. */
int CODOL_AdvanceModelSurfacesStream(const uint8_t *b,size_t size,size_t *position)
{
    size_t p,h,surfaces;
    unsigned count,i,j;
    if (!b || !position || size>CODOL_ASSET_LIMIT) return 0;
    p=h=*position;
    if (!take(&p,size,1,48)) return 0;
    if (u32(b+h)==UINT32_MAX && !string(b,size,&p)) return 0;
    count=u16(b+h+8); surfaces=p;
    if (u32(b+h+4)) {
        if (!take(&p,size,count,84)) return 0;
        for (i=0;i<count;++i) {
            const uint8_t *s=b+surfaces+84*i;
            if (u32(s+0x1c)==UINT32_MAX) {
                unsigned shorts=0;
                for (j=0;j<4;++j) {
                    unsigned n=u16(s+0x14+2*j);
                    if (n>=32768) return 0;
                    shorts+=n*(2*j+1);
                }
                if (!take(&p,size,shorts,2)) return 0;
            }
            if (u32(s+0x20)==UINT32_MAX && !take(&p,size,u16(s+4),32)) return 0;
            if (u32(s+0x2c)==UINT32_MAX) {
                uint32_t rigid_count=u32(s+0x28),k;
                size_t rigid=p;
                if (!take(&p,size,rigid_count,12)) return 0;
                for (k=0;k<rigid_count;++k) if (u32(b+rigid+12*k+8)==UINT32_MAX) {
                    size_t tree=p;
                    if (!take(&p,size,1,40)) return 0;
                    if (u32(b+tree+28) && !take(&p,size,u32(b+tree+24),16)) return 0;
                    if (u32(b+tree+36) && !take(&p,size,u32(b+tree+32),2)) return 0;
                }
            }
            if (u32(s+0x10)==UINT32_MAX && !take(&p,size,(uint32_t)u16(s+6)*3,2)) return 0;
        }
    }
    *position=p; return 1;
}
