/* C1 GameWorldMp 4bca00 / FxWorld 4be220; initial placement consumed at
 * 523ba4..523bbf and 523e60..523e77. Never infer piece positions from names. */
#include "codol_glass_map.h"
#include "codol_glass_snapshot.h"
#include <stddef.h>
static const char *glass_failure;
const char *CODOL_GlassMapFailure(void) { return glass_failure ? glass_failure : "unknown"; }
#define GLASS_FAIL(reason) (glass_failure=(reason),0)

static uint32_t word(const uint8_t *p)
{ return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24; }
static int extent(const uint8_t *base, size_t size, const void *p, size_t bytes)
{
    uintptr_t offset;
    if (!base || !p || (uintptr_t)p < (uintptr_t)base) return 0;
    offset = (uintptr_t)p - (uintptr_t)base;
    return offset <= size && bytes <= size - offset;
}
static const codol_glass_span_t *marker(const codol_load_blocks_t *b,
    const codol_asset_t *a, uint32_t kind)
{
    size_t i;
    const codol_glass_span_t *found = NULL;
    if (!b || !a || !a->data || b->glass_record_count > b->glass_record_capacity ||
        (b->glass_record_count && !b->glass_records) ||
        !extent(b->source,b->source_size,a->data,a->size)) return NULL;
    for (i=0;i<b->glass_record_count;++i) {
        const codol_glass_span_t *s=b->glass_records+i;
        if (s->world!=a->data || s->group!=kind) continue;
        if (found) return NULL;
        found=s;
    }
    return found;
}
int CODOL_ReadGlassMap(const codol_load_blocks_t *gb,const codol_asset_t *g,
    const codol_load_blocks_t *fb,const codol_asset_t *f,codol_glass_map_source_t *out)
{
    const codol_glass_span_t *gs,*fs;
    unsigned count;
    glass_failure=NULL;
    if (!out || !g || g->type!=18 || g->size<84) return GLASS_FAIL("GameWorld header");
    gs=marker(gb,g,UINT32_MAX);
    if (!gs || (!!gs->glass != !!word(g->data+80))) return GLASS_FAIL("GameWorld owned marker");
    if (!gs->glass) {
        if (gs->pieces || gs->piece_count) return GLASS_FAIL("null glass has pieces");
        *out=(codol_glass_map_source_t){0}; return 1;
    }
    if (!extent(g->data,g->size,gs->glass,128)) return GLASS_FAIL("GameWorld glass extent");
    count=word(gs->glass+4);
    if (count>CODOL_GLASS_MAX_PIECES || gs->piece_count!=count ||
        (count && (!word(gs->glass) ||
        !extent(g->data,g->size,gs->pieces,(size_t)count*12)))) return GLASS_FAIL("GameWorld piece count/extent");
    if (!count) { *out=(codol_glass_map_source_t){0}; return 1; }
    if (!f || f->type!=20 || f->size<116) return GLASS_FAIL("FxWorld header absent");
    fs=marker(fb,f,UINT32_MAX-1);
    if (!fs || fs->piece_count!=count || word(f->data+24)!=count ||
        !extent(f->data,f->size,fs->pieces,(size_t)count*52)) return GLASS_FAIL("FxWorld piece marker/count/extent");
    *out=(codol_glass_map_source_t){count,gs->pieces,fs->pieces};
    return 1;
}
