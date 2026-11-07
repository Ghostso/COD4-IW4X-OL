/* CoDOL collision stream traversal, with IW3 loader ordering retained. */
#include "codol_assets.h"
#include <string.h>
static uint32_t u32(const uint8_t *p)
{ return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24; }
static unsigned u16(const uint8_t *p) { return p[0] | (unsigned)p[1]<<8; }
static int take(size_t *position, size_t size, uint64_t count, unsigned stride)
{
    if (*position > size || count > (size-*position)/stride) return 0;
    *position += (size_t)count*stride; return 1;
}
static int string(const uint8_t *b, size_t size, size_t *p)
{
    const uint8_t *end = memchr(b+*p, 0, size-*p);
    if (!end) return 0;
    *p = (size_t)(end-b)+1; return 1;
}
static int plane_array(const uint8_t *b, size_t size, size_t *p, uint32_t count)
{
    size_t start = *p, i;
    if (!take(p, size, count, 8)) return 0;
    for (i = 0; i < count; ++i)
        if (u32(b+start+8*i) == UINT32_MAX && !take(p, size, 1, 20)) return 0;
    return 1;
}
static void span(codol_collision_layout_t *layout, unsigned section, size_t offset,
                 uint32_t count, uint32_t stride, uint32_t reference)
{
    codol_collision_span_t *s = &layout->sections[section];
    s->offset = offset; s->count = count; s->stride = stride; s->reference = reference;
}
int CODOL_ReadCollisionLayout(const codol_asset_t *asset, codol_collision_layout_t *out)
{
    uint32_t h[64];
    codol_collision_layout_t layout = {0};
    const uint8_t *b;
    size_t size, p = 256, start, i, j;
    unsigned brush_count;
    if (!asset || !out || !asset->data || (asset->type != 14 && asset->type != 15) ||
        asset->size < p || asset->size > CODOL_ASSET_LIMIT) return 0;
    b = asset->data; size = asset->size;
    for (i = 0; i < 64; ++i) h[i] = u32(b+4*i);
    if (h[0] == UINT32_MAX && !string(b, size, &p)) return 0;
    layout.name_reference = h[0];
    span(&layout, CODOL_COLL_PLANES, h[3] == UINT32_MAX ? p : SIZE_MAX, h[2], 20, h[3]);
    if (h[3] == UINT32_MAX && !take(&p, size, h[2], 20)) return 0;
    start = p;
    span(&layout, CODOL_COLL_STATIC_MODELS, p, h[4], 76, h[5]);
    if (!take(&p, size, h[4], 76)) return 0;
    for (i = 0; i < h[4]; ++i) {
        uint32_t model = u32(b+start+76*i);
        if (model == UINT32_MAX || model == UINT32_MAX-1) return 0;
    }
    start = p;
    span(&layout, CODOL_COLL_MATERIALS, p, h[6], 12, h[7]);
    if (!take(&p, size, h[6], 12)) return 0;
    for (i = 0; i < h[6]; ++i)
        if (u32(b+start+12*i) == UINT32_MAX && !string(b, size, &p)) return 0;
    span(&layout, CODOL_COLL_BRUSH_SIDES, p, h[8], 8, h[9]);
    if (!plane_array(b, size, &p, h[8])) return 0;
    span(&layout, CODOL_COLL_BRUSH_EDGES, p, h[10], 1, h[11]);
    if (!take(&p, size, h[10], 1)) return 0;
    span(&layout, CODOL_COLL_NODES, p, h[12], 8, h[13]);
    if (!plane_array(b, size, &p, h[12])) return 0;
    span(&layout, CODOL_COLL_LEAVES, p, h[14], 40, h[15]);
    if (!take(&p, size, h[14], 40)) return 0;
    span(&layout, CODOL_COLL_LEAF_BRUSHES, p, h[18], 2, h[19]);
    if (!take(&p, size, h[18], 2)) return 0;
    /* Load_clipMap_t loads leafbrushes before leafbrushNodes despite their
     * opposite order in the header. Each leaf node may own inline indices. */
    start = p;
    span(&layout, CODOL_COLL_LEAF_BRUSH_NODES, p, h[16], 20, h[17]);
    if (!take(&p, size, h[16], 20)) return 0;
    for (i = 0; i < h[16]; ++i) {
        unsigned count = u16(b+start+20*i+2);
        if (count && count < 0x8000 && u32(b+start+20*i+8) == UINT32_MAX &&
            !take(&p, size, count, 2)) return 0;
    }
    span(&layout, CODOL_COLL_LEAF_SURFACES, p, h[20], 4, h[21]);
    if (!take(&p, size, h[20], 4)) return 0;
    span(&layout, CODOL_COLL_VERTICES, p, h[22], 12, h[23]);
    if (!take(&p, size, h[22], 12)) return 0;
    span(&layout, CODOL_COLL_TRIANGLES, p, h[24], 6, h[25]);
    if (!take(&p, size, h[24], 6)) return 0;
    span(&layout, CODOL_COLL_WALKABLE, p, (uint32_t)(((uint64_t)h[24]*3+31)/32), 4, h[26]);
    if (!take(&p, size, ((uint64_t)h[24]*3+31)/32, 4)) return 0;
    span(&layout, CODOL_COLL_BORDERS, p, h[27], 28, h[28]);
    if (!take(&p, size, h[27], 28)) return 0;
    start = p;
    span(&layout, CODOL_COLL_PARTITIONS, p, h[29], 12, h[30]);
    if (!take(&p, size, h[29], 12)) return 0;
    for (i = 0; i < h[29]; ++i)
        /* Inline partition border is ONE object, not borderCount objects. */
        if (u32(b+start+12*i+8) == UINT32_MAX && !take(&p, size, 1, 28)) return 0;
    span(&layout, CODOL_COLL_AABBS, p, h[31], 32, h[32]);
    if (!take(&p, size, h[31], 32)) return 0;
    span(&layout, CODOL_COLL_SUBMODELS, p, h[33], 68, h[34]);
    if (!take(&p, size, h[33], 68)) return 0;
    brush_count = h[35] & 0xffff; start = p;
    span(&layout, CODOL_COLL_BRUSHES, p, brush_count, 36, h[36]);
    if (!take(&p, size, brush_count, 36)) return 0;
    for (i = 0; i < brush_count; ++i) {
        const uint8_t *brush = b+start+36*i;
        if (u32(brush+4) == UINT32_MAX && !plane_array(b, size, &p, u16(brush))) return 0;
        if (u32(brush+8) == UINT32_MAX) {
            unsigned edges = 0;
            for (j = 0; j < 6; ++j) edges += brush[30+j];
            if (!take(&p, size, edges, 1)) return 0;
        }
    }
    span(&layout, CODOL_COLL_BRUSH_BOUNDS, p, brush_count, 24, h[37]);
    if (!take(&p, size, brush_count, 24)) return 0;
    span(&layout, CODOL_COLL_BRUSH_CONTENTS, p, brush_count, 4, h[38]);
    if (!take(&p, size, brush_count, 4)) return 0;
    span(&layout, CODOL_COLL_STATIC_NODES, p, h[40], 28, h[41]);
    if (!take(&p, size, h[40], 28) || size-p < 44 ||
        (h[39] != UINT32_MAX && h[39] != UINT32_MAX-1) || u32(b+p) != h[0]) return 0;
    layout.map_entities = p; *out = layout; return 1;
}
int CODOL_LocateCollisionMapEntities(const codol_asset_t *asset, size_t *offset)
{
    codol_collision_layout_t layout;
    if (!offset || !CODOL_ReadCollisionLayout(asset, &layout)) return 0;
    *offset = layout.map_entities; return 1;
}
int CODOL_ReadCollisionMapEntities(const codol_asset_t *asset, codol_map_entities_t *out)
{
    size_t offset;
    return out && CODOL_LocateCollisionMapEntities(asset, &offset) &&
        CODOL_ReadMapEntities(asset->data+offset, asset->size-offset, out);
}
