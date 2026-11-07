/* Native playerstate sections, from alpha0022/weapon_spawn.py and spawn_player.py. */
#include "codol_player_arrays.h"
#include <string.h>
#include <stdio.h>
#include <limits.h>
unsigned CODOL_HudFieldOffset(unsigned index)
{
    /* C1's table at 0xc39860, in wire order. */
    static const unsigned offsets[CODOL_HUD_FIELDS]={
        0x30,0x08,0x04,0x00,0x4c,0x48,0x44,0x10,0x0c,0x80,0x38,0x2c,
        0x34,0x3c,0xa4,0x28,0x14,0x1c,0x20,0x18,0x24,0x88,0x84,0x58,
        0x5c,0x50,0x54,0x8c,0x90,0xa0,0x94,0x98,0x9c,0x40,0x78,0x70,
        0x74,0x60,0x64,0x6c,0x68,0x7c
    };
    return index<CODOL_HUD_FIELDS ? offsets[index] : UINT_MAX;
}

static const int hud_bits[CODOL_HUD_FIELDS] = {
    -85,-91,-92,4,8,10,10,11,-90,0,-97,8,-85,16,10,4,-86,-97,16,-86,4,
    0,10,-97,16,10,10,-85,-97,5,12,-65,-65,10,-97,-97,16,-99,-99,8,4,32
};
static const codol_hud_state_t empty_hud;
static const codol_player_array_updates_t empty_updates;
/* Which HUD field the last CODOL_ReachHud refused, for the server trace. */
static char hud_reach_failure[160];
const char *CODOL_ReachHudFailure(void) { return hud_reach_failure; }
int CODOL_ReachHud(codol_hud_state_t *held, const codol_hud_state_t *base,
                   const codol_hud_state_t *requested, const codol_delta_context_t *ctx)
{
    codol_hud_state_t out = {0};
    unsigned a, slot, i;
    if (!held || !ctx) return 0;
    if (!base) base = &empty_hud;
    if (!requested) requested = &empty_hud;
    for (a = 0; a < 2; ++a) {
        if (base->count[a] > 31 || requested->count[a] > 31) return 0;
        out.count[a] = requested->count[a];
        for (slot = 0; slot < out.count[a]; ++slot) {
            if (!requested->elements[a][slot].field[3]) {
                snprintf(hud_reach_failure,sizeof(hud_reach_failure),"%s element %u has wire type 0",a ? "current" : "archival",slot);
                return 0;
            }
            for (i = 0; i < CODOL_HUD_FIELDS; ++i) {
                uint32_t from = slot < base->count[a] ? base->elements[a][slot].field[i] : 0;
                uint32_t to = requested->elements[a][slot].field[i];
                out.elements[a][slot].field[i] = to;
                if (from == to) continue;
                if (!CODOL_ReachDeltaValue(hud_bits[i], from, to, ctx, &out.elements[a][slot].field[i])) {
                    float ff, tf; memcpy(&ff,&from,4); memcpy(&tf,&to,4);
                    snprintf(hud_reach_failure,sizeof(hud_reach_failure),
                        "%s element %u (type %u) field %u offset 0x%02x bits %d: from 0x%08x (%g) to 0x%08x (%g)",
                        a ? "current" : "archival",slot,requested->elements[a][slot].field[3],i,
                        CODOL_HudFieldOffset(i),hud_bits[i],from,ff,to,tf);
                    return 0;
                }
            }
        }
    }
    /* Section 5 is delta coded against this held state too (every field is
     * XORed with its base value). Dropping the objectives here left the held
     * frame empty while the client kept the real values, so every second
     * snapshot decoded as V ^ V = 0: icon 0, the client's built-in objective
     * ring, pinned to entNum 0, the local player. Every objective field
     * reaches its target exactly (full floats or plain bit fields). */
    memcpy(out.objectives, requested->objectives, sizeof(out.objectives));
    *held = out; return 1;
}

static int hud_array(codol_msg_t *m, const codol_hud_state_t *from,
                      const codol_hud_state_t *to, unsigned array, codol_delta_context_t *ctx)
{
    unsigned slot, i, lc;
    CODOL_WriteBits(m, to->count[array], 5);
    for (slot = 0; slot < to->count[array]; ++slot) {
        const uint32_t *f = slot < from->count[array] ? from->elements[array][slot].field : empty_hud.elements[0][0].field;
        const uint32_t *t = to->elements[array][slot].field;
        int previous = -1;
        if (!t[3]) return 0; /* client's gather scan stops at the first free element */
        for (lc = 0, i = 0; i < CODOL_HUD_FIELDS; ++i) if (f[i] != t[i]) lc = i + 1;
        CODOL_WriteBits(m, lc, 6);
        for (i = 0; i < lc; ++i) {
            unsigned gap;
            if (f[i] == t[i]) continue;
            gap = (int)i - previous; previous = i;
            CODOL_WriteBits(m, gap == 1, 1);
            if (gap != 1) {
                --gap;
                while (gap >= 7) { CODOL_WriteBits(m, 7, 3); gap -= 7; }
                CODOL_WriteBits(m, gap, 3);
            }
            if (!CODOL_WriteDeltaValue(m, hud_bits[i], f[i], t[i], ctx)) return 0;
        }
    }
    return !m->failed;
}

/* Section 5 field widths, in the table's own order (.rdata:0xc39818). */
static const int objective_bits[CODOL_OBJECTIVE_FIELDS] = { 0, 0, 0, 12, 11, 4 };

/* The section-5 gap coder is plain unary: delta-1 zero bits then a 1
 * (0x5a09e2, gapMode 1). It is deliberately neither the player-field coder
 * (4-bit, escape 15, 0x5a1ad2) nor the HUD coder (3-bit, escape 7, 0x5a18a0).
 * Three sections, three codings; getting this one wrong desynchronises
 * everything after it, which is the whole HUD. */
static void objective_gap(codol_msg_t *m, unsigned delta)
{
    while (delta > 1) { CODOL_WriteBits(m, 0, 1); --delta; }
    CODOL_WriteBits(m, 1, 1);
}

/* Whether any slot carries anything. The reader costs a flat 32 * 4 bits once
 * the gate is on, because state is read unconditionally for every slot, so the
 * gate stays off while nothing is live and the wire is then byte for byte what
 * it was before this section existed. */
static int objectives_live(const codol_hud_state_t *s)
{
    unsigned i, f;
    if (!s) return 0;
    for (i = 0; i < CODOL_OBJECTIVE_SLOTS; ++i) {
        if (s->objectives[i].state) return 1;
        for (f = 0; f < CODOL_OBJECTIVE_FIELDS; ++f)
            if (s->objectives[i].field[f]) return 1;
    }
    return 0;
}

static int write_objectives(codol_msg_t *m, const codol_hud_state_t *from,
                            const codol_hud_state_t *to, codol_delta_context_t *ctx)
{
    unsigned i, f;
    if (!objectives_live(to) && !objectives_live(from)) { CODOL_WriteBits(m, 0, 1); return 1; }
    CODOL_WriteBits(m, 1, 1);
    for (i = 0; i < CODOL_OBJECTIVE_SLOTS; ++i) {
        const codol_objective_t *a = &from->objectives[i], *b = &to->objectives[i];
        int last = -1, previous = -1;
        if (b->state > 7) return 0;
        CODOL_WriteBits(m, b->state, 3);
        for (f = 0; f < CODOL_OBJECTIVE_FIELDS; ++f)
            if (a->field[f] != b->field[f]) last = (int)f;
        if (last < 0) { CODOL_WriteBits(m, 0, 1); continue; }
        CODOL_WriteBits(m, 1, 1);
        /* The reader takes the last changed index, not a count, and stops when
         * its running index reaches it (0x5a0a9b). */
        CODOL_WriteBits(m, (uint32_t)last, 3);
        for (f = 0; (int)f <= last; ++f) {
            if (a->field[f] == b->field[f]) continue;
            objective_gap(m, (unsigned)((int)f - previous));
            previous = (int)f;
            if (!CODOL_WriteDeltaValue(m, objective_bits[f], a->field[f], b->field[f], ctx)) return 0;
        }
    }
    return !m->failed;
}
int CODOL_WritePlayerArrays(codol_msg_t *m, const codol_player_array_updates_t *u,
                            const codol_hud_state_t *from, const codol_hud_state_t *to,
                            codol_delta_context_t *ctx)
{
    unsigned i, hand;
    int hud_changed = 0;
    if (!m || !ctx) return 0;
    if (!u) u = &empty_updates;
    if (!from) from = &empty_hud;
    if (!to) to = &empty_hud;
    if (u->stats_mask > 15 || u->weapons_mask > 0x7fff || u->weapon_index_mask > 0x7fff) goto fail;
    /* 1. stats */
    CODOL_WriteBits(m, !!u->stats_mask, 1);
    if (u->stats_mask) {
        CODOL_WriteBits(m, u->stats_mask, 4);
        for (i = 0; i < 4; ++i) if (u->stats_mask & (1u << i)) {
            if (i < 3) {
                if (u->stats[i] < -32768 || u->stats[i] > 65535) goto fail;
                CODOL_WriteShort(m, u->stats[i]);
            } else {
                if (u->stats[i] < 0 || u->stats[i] > 255) goto fail;
                CODOL_WriteByte(m, u->stats[i]);
            }
        }
    }
    /* 2. clip updates are terminated by a zero bit, not a separate count. */
    for (i = 0; i < 16; ++i) if (u->clip_mask & (1u << i)) {
        if (u->clip_index[i] < -1 || u->clip_index[i] > 1022 || u->clip_presence[i] > 3) goto fail;
        CODOL_WriteBits(m, 1, 1); CODOL_WriteBits(m, i, 4);
        CODOL_WriteBits(m, u->clip_index[i] < 0 ? 1023 : u->clip_index[i], 10);
        for (hand = 0; hand < 2; ++hand) {
            int present = !!(u->clip_presence[i] & (1u << hand));
            CODOL_WriteBits(m, present, 1);
            if (present) {
                if (u->clip_ammo[i][hand] > 511) goto fail;
                CODOL_WriteBits(m, u->clip_ammo[i][hand], 9);
            }
        }
    }
    CODOL_WriteBits(m, 0, 1);
    /* 3. equipped weapons have exactly 15 optional slots. */
    CODOL_WriteBits(m, !!u->weapons_mask, 1);
    if (u->weapons_mask) for (i = 0; i < 15; ++i) {
        int present = !!(u->weapons_mask & (1u << i));
        CODOL_WriteBits(m, present, 1);
        if (!present) continue;
        present = !!(u->weapon_index_mask & (1u << i));
        CODOL_WriteBits(m, present, 1);
        if (present) {
            if (u->weapon_index[i] > 1023) goto fail;
            CODOL_WriteBits(m, u->weapon_index[i], 10);
        }
        if (u->weapon_flags[i] > 31) goto fail;
        CODOL_WriteBits(m, u->weapon_flags[i], 5);
    }
    /* 4. reserve ammunition uses its own zero-terminated list. */
    for (i = 0; i < 16; ++i) if (u->reserve_mask & (1u << i)) {
        if (u->reserve_type[i] > 1023 || u->reserve_ammo[i] > 2047) goto fail;
        CODOL_WriteBits(m, 1, 1); CODOL_WriteBits(m, i, 4);
        CODOL_WriteBits(m, u->reserve_type[i], 10); CODOL_WriteBits(m, u->reserve_ammo[i], 11);
    }
    CODOL_WriteBits(m, 0, 1);
    /* 5. ps+0x5D0, the objective and waypoint array. */
    if (!write_objectives(m, from, to, ctx)) goto fail;
    /* 6. A single gate covers both HUD arrays, including count-zero deletion. */
    for (i = 0; i < 2; ++i) {
        if (from->count[i] > CODOL_HUD_SLOTS || to->count[i] > CODOL_HUD_SLOTS) goto fail;
        if (from->count[i] != to->count[i] ||
            memcmp(from->elements[i], to->elements[i], to->count[i] * sizeof(codol_hud_element_t))) hud_changed = 1;
    }
    CODOL_WriteBits(m, hud_changed, 1);
    if (hud_changed && (!hud_array(m, from, to, 0, ctx) || !hud_array(m, from, to, 1, ctx))) goto fail;
    CODOL_WriteBits(m, 0, 1); /* 7. ps+0x3340: not implemented in reference */
    return !m->failed;
fail:
    m->failed = 1; return 0;
}
