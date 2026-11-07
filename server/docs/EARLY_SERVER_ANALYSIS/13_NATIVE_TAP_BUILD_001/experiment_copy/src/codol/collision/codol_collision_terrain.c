#include "codol_collision.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>

static uint16_t u16(const uint8_t *p) { return p[0] | (uint16_t)p[1]<<8; }
static uint32_t u32(const uint8_t *p)
{ return (uint32_t)u16(p) | (uint32_t)u16(p+2)<<16; }
static int floats(float *out, const uint8_t *p, unsigned count)
{
    unsigned i;
    for (i=0; i<count; ++i) {
        uint32_t bits=u32(p+4*i);
        memcpy(out+i, &bits, 4);
        if (!isfinite(out[i])) return 0;
    }
    return 1;
}
void CODOL_FreeCollisionTerrain(codol_collision_terrain_t *t)
{
    if (!t) return;
    free(t->vertices); free(t->triangles); free(t->walkable);
    free(t->borders); free(t->partitions); free(t->aabbs);
    memset(t, 0, sizeof(*t));
}
int CODOL_ReadCollisionTerrain(const codol_asset_t *asset, codol_collision_terrain_t *out)
{
    codol_collision_layout_t layout;
    codol_collision_terrain_t t={0};
    const codol_collision_span_t *s=layout.sections;
    const uint8_t *p;
    uint32_t i,j,k,border=0,base=0;
    int have_base=0;
    if (!out || !CODOL_ReadCollisionLayout(asset, &layout)) return 0;
#define ALLOC(field, countfield, section) do { \
    t.countfield=s[section].count; \
    if (t.countfield) { \
        t.field=calloc(t.countfield, sizeof(*t.field)); \
        if (!t.field) goto fail; \
    } \
} while (0)
    ALLOC(vertices, vertex_count, CODOL_COLL_VERTICES);
    ALLOC(triangles, triangle_count, CODOL_COLL_TRIANGLES);
    ALLOC(walkable, walkable_words, CODOL_COLL_WALKABLE);
    ALLOC(borders, border_count, CODOL_COLL_BORDERS);
    ALLOC(partitions, partition_count, CODOL_COLL_PARTITIONS);
    ALLOC(aabbs, aabb_count, CODOL_COLL_AABBS);
#undef ALLOC
    p=asset->data+s[CODOL_COLL_VERTICES].offset;
    for (i=0; i<t.vertex_count; ++i)
        if (!floats(t.vertices[i], p+12*i, 3)) goto fail;
    p=asset->data+s[CODOL_COLL_TRIANGLES].offset;
    /* Terrain triangle indices are u16 and relative to the owning partition's
     * vertex BLOCK, so nothing here can range-check them; that happens in the
     * partition loop below, once the block is known. */
    for (i=0; i<t.triangle_count; ++i) for (j=0; j<3; ++j)
        t.triangles[i][j]=u16(p+6*i+2*j);
    p=asset->data+s[CODOL_COLL_WALKABLE].offset;
    for (i=0; i<t.walkable_words; ++i) t.walkable[i]=u32(p+4*i);
    p=asset->data+s[CODOL_COLL_BORDERS].offset;
    for (i=0; i<t.border_count; ++i) {
        float values[7];
        if (!floats(values, p+28*i, 7)) goto fail;
        memcpy(&t.borders[i], values, sizeof(values));
    }
    p=asset->data+s[CODOL_COLL_PARTITIONS].offset;
    for (i=0; i<t.partition_count; ++i) {
        codol_collision_partition_t *part=t.partitions+i;
        uint32_t first=u32(p+12*i+4), ref=u32(p+12*i+8);
        part->triCount=p[12*i]; part->borderCount=p[12*i+1];
        part->vertBlock=p[12*i+2];
        if (first>t.triangle_count || part->triCount>t.triangle_count-first ||
            part->borderCount>t.border_count-border) goto fail;
        part->firstTri=(int)first;
        /* C1 0x00583e30 resolves this partition's triangles against
         * cm.verts + vertBlock*0x3000 (0x3000 = 1024 verts * 12 bytes), so the
         * only meaningful bound on a u16 index is block*1024 + index. */
        for (j=0; j<part->triCount; ++j)
            for (k=0; k<3; ++k)
                if ((uint32_t)part->vertBlock*1024u+t.triangles[first+j][k]
                    >= t.vertex_count) goto fail;
        if (part->borderCount) {
            if (!ref || ref>=UINT32_MAX-1 || ref<(uint64_t)border*28) goto fail;
            if (!have_base) { base=ref-border*28; have_base=1; }
            if ((uint64_t)base+(uint64_t)border*28!=ref) goto fail;
            part->borders=t.borders+border;
            border+=part->borderCount;
        }
    }
    if (border!=t.border_count) goto fail;
    p=asset->data+s[CODOL_COLL_AABBS].offset;
    for (i=0; i<t.aabb_count; ++i) {
        codol_collision_aabb_t *a=t.aabbs+i;
        uint32_t index=u32(p+32*i+28);
        if (!floats(a->origin, p+32*i, 3) || !floats(a->halfSize, p+32*i+16, 3)) goto fail;
        for (j=0; j<3; ++j) if (a->halfSize[j]<0) goto fail;
        a->materialIndex=u16(p+32*i+12); a->childCount=u16(p+32*i+14);
        if (a->materialIndex>=s[CODOL_COLL_MATERIALS].count) goto fail;
        if (a->childCount) {
            /* Forward edges also rule out cycles before engine traversal. */
            if (index<=i || index>t.aabb_count || a->childCount>t.aabb_count-index) goto fail;
        } else if (index>=t.partition_count) goto fail;
        a->index=(int)index;
    }
    *out=t; return 1;
fail:
    CODOL_FreeCollisionTerrain(&t); return 0;
}
