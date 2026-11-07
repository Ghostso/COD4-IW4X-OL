#include "codol_collision.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>

static unsigned u16(const uint8_t *p) { return p[0] | (unsigned)p[1]<<8; }
static uint32_t u32(const uint8_t *p) { return u16(p) | (uint32_t)u16(p+2)<<16; }
static float f32(const uint8_t *p)
{ uint32_t bits=u32(p); float value; memcpy(&value,&bits,4); return value; }
static int reference(uint32_t ref, uint32_t offset, uint32_t *base, int *seen)
{
    if (!ref || ref>=UINT32_MAX-1 || ref<offset) return 0;
    if (!*seen) { *base=ref-offset; *seen=1; }
    return (uint64_t)*base+offset==ref;
}
void CODOL_FreeCollisionBrushes(codol_collision_brushes_t *out)
{
    if (!out) return;
    free(out->planes); free(out->sides); free(out->edges); free(out->brush_storage); free(out->nodes);
    memset(out,0,sizeof(*out));
}
int CODOL_ReadCollisionBrushes(const codol_asset_t *asset, const uint8_t *planes,
                              size_t plane_size, codol_collision_brushes_t *out)
{
    codol_collision_layout_t layout;
    codol_collision_brushes_t t={0};
    const codol_collision_span_t *s=layout.sections;
    const uint8_t *p;
    uint32_t i,j,side=0,edge=0,sidebase=0,edgebase=0;
    int have_side=0,have_edge=0;
    if (!out || !CODOL_ReadCollisionLayout(asset,&layout)) return 0;
    t.plane_count=s[CODOL_COLL_PLANES].count;
    if (plane_size>CODOL_ASSET_LIMIT || plane_size!=(uint64_t)t.plane_count*20 || (plane_size && !planes) ||
        (t.plane_count && (!s[CODOL_COLL_PLANES].reference ||
                          s[CODOL_COLL_PLANES].reference>=UINT32_MAX-1))) return 0;
    t.side_count=s[CODOL_COLL_BRUSH_SIDES].count;
    t.edge_count=s[CODOL_COLL_BRUSH_EDGES].count;
    t.brush_count=s[CODOL_COLL_BRUSHES].count;
    t.node_count=s[CODOL_COLL_NODES].count;
    /* Signed 16-bit child links must represent every node and leaf. */
    if (t.node_count>32768 || s[CODOL_COLL_LEAVES].count>32768) return 0;
#define ALLOC(field,count) do { if (t.count) { \
    t.field=calloc(t.count,sizeof(*t.field)); if (!t.field) goto fail; } } while(0)
    ALLOC(planes,plane_count); ALLOC(sides,side_count);
    ALLOC(edges,edge_count);
    ALLOC(nodes,node_count);
#undef ALLOC
    if (t.brush_count) {
        t.brush_storage=calloc(1,(size_t)t.brush_count*sizeof(*t.brushes)+15);
        if (!t.brush_storage) goto fail;
        t.brushes=(codol_collision_brush_t *)(((uintptr_t)t.brush_storage+15)&~(uintptr_t)15);
    }
    for (i=0;i<t.plane_count;++i) {
        codol_collision_plane_t *plane=t.planes+i;
        float length=0;
        plane->type=3;
        for (j=0;j<3;++j) {
            float n=f32(planes+20*i+4*j);
            if (!isfinite(n)) goto fail;
            plane->normal[j]=n; length+=n*n;
            if (n<0) plane->signbits|=1u<<j;
        }
        for (j=0;j<3;++j)
            if (plane->normal[j]==1 && plane->normal[(j+1)%3]==0 && plane->normal[(j+2)%3]==0)
                plane->type=j;
        plane->dist=f32(planes+20*i+12);
        if (!isfinite(plane->dist) || fabsf(length-1)>0.001f) goto fail;
    }
    p=asset->data+s[CODOL_COLL_NODES].offset;
    for (i=0;i<t.node_count;++i) {
        uint32_t ref=u32(p+8*i),base=s[CODOL_COLL_PLANES].reference;
        if (ref<base || (ref-base)%20 || (ref-base)/20>=t.plane_count) goto fail;
        t.nodes[i].plane=t.planes+(ref-base)/20;
        for (j=0;j<2;++j) {
            unsigned raw=u16(p+8*i+4+2*j);
            int child=raw<32768 ? (int)raw : (int)raw-65536;
            if (child>=0) {
                /* Shipped BSPs use forward node edges, excluding cycles. */
                if ((uint32_t)child<=i || (uint32_t)child>=t.node_count) goto fail;
            } else if ((unsigned)(-1-child)>=s[CODOL_COLL_LEAVES].count) goto fail;
            t.nodes[i].children[j]=(int16_t)child;
        }
    }
    p=asset->data+s[CODOL_COLL_BRUSH_SIDES].offset;
    for (i=0;i<t.side_count;++i) {
        uint32_t ref=u32(p+8*i), base=s[CODOL_COLL_PLANES].reference;
        codol_collision_side_t *b=t.sides+i;
        if (ref<base || (ref-base)%20 || (ref-base)/20>=t.plane_count) goto fail;
        b->plane=t.planes+(ref-base)/20;
        b->materialNum=u16(p+8*i+4);
        b->firstAdjacentSideOffset=p[8*i+6]; b->edgeCount=p[8*i+7];
        if (b->materialNum>=s[CODOL_COLL_MATERIALS].count) goto fail;
    }
    if (t.edge_count) memcpy(t.edges,asset->data+s[CODOL_COLL_BRUSH_EDGES].offset,t.edge_count);
    p=asset->data+s[CODOL_COLL_BRUSHES].offset;
    for (i=0;i<t.brush_count;++i) {
        codol_collision_brush_t *b=t.brushes+i;
        const uint8_t *raw=p+36*i, *bounds=asset->data+s[CODOL_COLL_BRUSH_BOUNDS].offset+24*i;
        uint32_t edges=0;
        b->numsides=u16(raw);
#ifdef CODOL_SERVER
        b->glassPieceIndex=u16(raw+2);
        if (b->glassPieceIndex>1024) goto fail;
#endif
        if (b->numsides>t.side_count-side) goto fail;
        if (b->numsides) {
            if (!reference(u32(raw+4),side*8,&sidebase,&have_side)) goto fail;
            b->sides=t.sides+side;
        }
        for (j=0;j<6;++j) {
            unsigned material=u16(raw+12+2*j);
            if (material>=s[CODOL_COLL_MATERIALS].count || material>32767) goto fail;
            b->axialMaterialNum[j/3][j%3]=material;
            b->firstAdjacentSideOffsets[j/3][j%3]=raw[24+j];
            b->edgeCount[j/3][j%3]=raw[30+j]; edges+=raw[30+j];
        }
        for (j=0;j<b->numsides;++j) edges+=b->sides[j].edgeCount;
        if (edges>t.edge_count-edge) goto fail;
        if (edges) {
            if (!reference(u32(raw+8),edge,&edgebase,&have_edge)) goto fail;
            b->baseAdjacentSide=t.edges+edge;
        }
        for (j=0;j<6;++j)
            if ((unsigned)b->firstAdjacentSideOffsets[j/3][j%3]+b->edgeCount[j/3][j%3]>edges) goto fail;
        for (j=0;j<b->numsides;++j)
            if ((unsigned)b->sides[j].firstAdjacentSideOffset+b->sides[j].edgeCount>edges) goto fail;
        for (j=0;j<3;++j) {
            float mid=f32(bounds+4*j),half=f32(bounds+12+4*j);
            if (!isfinite(mid) || !isfinite(half) || half<0) goto fail;
            b->mins[j]=mid-half; b->maxs[j]=mid+half;
            if (!isfinite(b->mins[j]) || !isfinite(b->maxs[j])) goto fail;
        }
        { uint32_t contents=u32(asset->data+s[CODOL_COLL_BRUSH_CONTENTS].offset+4*i);
          memcpy(&b->contents,&contents,4); }
        side+=b->numsides; edge+=edges;
    }
    if (side!=t.side_count || edge!=t.edge_count) goto fail;
    *out=t; return 1;
fail:
    CODOL_FreeCollisionBrushes(&t); return 0;
}
