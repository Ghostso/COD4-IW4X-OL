#include "codol_collision.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
static unsigned u16(const uint8_t *p) { return p[0]|(unsigned)p[1]<<8; }
static uint32_t u32(const uint8_t *p) { return u16(p)|(uint32_t)u16(p+2)<<16; }
static int i16(const uint8_t *p) { unsigned v=u16(p); return v<32768?(int)v:(int)v-65536; }
static float f32(const uint8_t *p)
{ uint32_t bits=u32(p); float v; memcpy(&v,&bits,4); return v; }
void CODOL_FreeCollisionBrushTree(codol_collision_brush_tree_t *t)
{
    if (!t) return;
    free(t->nodes); free(t->indices); memset(t,0,sizeof(*t));
}
int CODOL_ReadCollisionBrushTree(const codol_asset_t *asset,codol_collision_brush_tree_t *out)
{
    codol_collision_layout_t l;
    codol_collision_brush_tree_t t={0};
    const uint8_t *rows,*pool;
    uint32_t i,j,used=0,extra=0,base=0;
    int have_base=0;
    size_t inline_pos;
    if (!out || !CODOL_ReadCollisionLayout(asset,&l)) return 0;
    t.node_count=l.sections[CODOL_COLL_LEAF_BRUSH_NODES].count;
    t.pooled_count=l.sections[CODOL_COLL_LEAF_BRUSHES].count;
    rows=asset->data+l.sections[CODOL_COLL_LEAF_BRUSH_NODES].offset;
    pool=asset->data+l.sections[CODOL_COLL_LEAF_BRUSHES].offset;
    inline_pos=l.sections[CODOL_COLL_LEAF_BRUSH_NODES].offset+(size_t)t.node_count*20;
    for (i=0;i<t.node_count;++i) {
        int count=i16(rows+20*i+2);
        if (count>0 && u32(rows+20*i+8)==UINT32_MAX) {
            if ((uint32_t)count>UINT32_MAX-extra) return 0;
            extra+=count;
        }
    }
    if (extra>UINT32_MAX-t.pooled_count || (uint64_t)extra+t.pooled_count>CODOL_ASSET_LIMIT/2) return 0;
    t.index_count=t.pooled_count+extra;
    if (t.node_count && !(t.nodes=calloc(t.node_count,sizeof(*t.nodes)))) goto fail;
    if (t.index_count && !(t.indices=calloc(t.index_count,sizeof(*t.indices)))) goto fail;
    for (i=0;i<t.pooled_count;++i) {
        t.indices[i]=u16(pool+2*i);
        if (t.indices[i]>=l.sections[CODOL_COLL_BRUSHES].count) goto fail;
    }
    extra=t.pooled_count;
    for (i=0;i<t.node_count;++i) {
        const uint8_t *p=rows+20*i;
        codol_collision_brush_node_t *node=t.nodes+i;
        uint32_t flags=u32(p+4);
        int count=i16(p+2);
        node->axis=p[0]; node->leafBrushCount=count; memcpy(&node->contents,&flags,4);
        if (count>0) {
            uint32_t ref=u32(p+8);
            if (ref==UINT32_MAX) {
                node->data.leaf.brushes=t.indices+extra;
                for (j=0;j<(uint32_t)count;++j) {
                    unsigned index=u16(asset->data+inline_pos+2*j);
                    if (index>=l.sections[CODOL_COLL_BRUSHES].count) goto fail;
                    t.indices[extra+j]=index;
                }
                inline_pos+=2*(unsigned)count; extra+=count;
            } else {
                if ((uint32_t)count>t.pooled_count-used || !ref || ref==UINT32_MAX-1 || ref<(uint64_t)used*2) goto fail;
                if (!have_base) { base=ref-used*2; have_base=1; }
                if ((uint64_t)base+(uint64_t)used*2!=ref) goto fail;
                node->data.leaf.brushes=t.indices+used; used+=count;
            }
        } else {
            static const uint8_t zero[20]={0};
            if (i==0 && !memcmp(p,zero,20)) continue; /* reserved empty node */
            if (count < -1 || node->axis>2 || (count<0 && i+1>=t.node_count)) goto fail;
            node->data.children.dist=f32(p+8); node->data.children.range=f32(p+12);
            if (!isfinite(node->data.children.dist)||!isfinite(node->data.children.range)||node->data.children.range<0) goto fail;
            for (j=0;j<2;++j) {
                unsigned offset=u16(p+16+2*j);
                if (!offset || offset>=t.node_count-i) goto fail;
                node->data.children.childOffset[j]=offset;
            }
        }
    }
    if (used!=t.pooled_count || extra!=t.index_count) goto fail;
    *out=t; return 1;
fail:
    CODOL_FreeCollisionBrushTree(&t); return 0;
}
