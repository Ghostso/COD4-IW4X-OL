/* Wire contract: C1 CL_ParseGlass 4484a0; application 448170.
 * This section is independent from entity events. */
#include "codol_glass_snapshot.h"

static int valid(const codol_glass_wire_piece_t *p, size_t count)
{
    size_t i;
    if (count > CODOL_GLASS_MAX_PIECES || (count && !p)) return 0;
    for (i = 0; i < count; ++i) {
        if (p[i].state > 3) return 0;
        if (p[i].state == 2 && p[i].direction != 255 &&
            (p[i].impact_x > 63 || p[i].impact_y > 63)) return 0;
    }
    return 1;
}
static int changed(const codol_glass_wire_piece_t *a,
                   const codol_glass_wire_piece_t *b)
{
    if (a->state != b->state) return 1;
    if (a->state != 2) return 0;
    if (a->direction != b->direction) return 1;
    return a->direction != 255 &&
        (a->impact_x != b->impact_x || a->impact_y != b->impact_y);
}
static void piece(codol_msg_t *m, const codol_glass_wire_piece_t *p)
{
    CODOL_WriteBits(m, p->state, 2);
    if (p->state != 2) return;
    CODOL_WriteBits(m, p->direction != 255, 1);
    if (p->direction == 255) return;
    CODOL_WriteByte(m, p->direction);
    CODOL_WriteBits(m, p->impact_x, 6);
    CODOL_WriteBits(m, p->impact_y, 6);
}
static size_t piece_bits(const codol_glass_wire_piece_t *p)
{ return 2 + (p->state==2 ? (p->direction==255 ? 1 : 21) : 0); }
int CODOL_WriteGlass(codol_msg_t *m, const codol_glass_wire_piece_t *to,
    size_t count, const codol_glass_wire_piece_t *base, size_t base_count)
{
    size_t i, changes = 0,dense_bits=11,sparse_bits=11;
    if (!m) return 0;
    if (!valid(to, count) || !valid(base, base_count)) goto fail;
    if (!count) { CODOL_WriteBits(m, 0, 1); return !m->failed; }
    if (base && base_count == count) {
        for (i = 0; i < count; ++i) changes += changed(to + i, base + i);
        if (!changes) { CODOL_WriteBits(m, 0, 1); return !m->failed; }
    } else {
        base = NULL;
        for (i=0;i<count;++i) changes += to[i].state!=0;
        /* A new map's C1 glass store starts intact. Subsequent application is
         * monotonic, so no zero-state record can restore a broken piece. */
        if (!changes) { CODOL_WriteBits(m,0,1); return !m->failed; }
    }
    for (i=0;i<count;++i) {
        dense_bits+=piece_bits(to+i);
        if (base ? changed(to+i,base+i) : to[i].state!=0)
            sparse_bits+=11+piece_bits(to+i);
    }
    CODOL_WriteBits(m, 1, 1);
    if (sparse_bits<dense_bits) {
        CODOL_WriteBits(m, 1, 1);
        for (i = 0; i < count; ++i) if (base ? changed(to+i,base+i) : to[i].state!=0) {
            CODOL_WriteBits(m, (unsigned)i, 11);
            piece(m, to + i);
        }
        CODOL_WriteBits(m, CODOL_GLASS_MAX_PIECES, 11);
    } else {
        CODOL_WriteBits(m, 0, 1);
        CODOL_WriteBits(m, (unsigned)count, 11);
        for (i = 0; i < count; ++i) piece(m, to + i);
    }
    return !m->failed;
fail:
    m->failed = 1;
    return 0;
}
