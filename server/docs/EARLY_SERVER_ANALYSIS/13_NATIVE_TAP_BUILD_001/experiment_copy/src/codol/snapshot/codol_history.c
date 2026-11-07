/* Owned CoDOL snapshot ring. Never stores pointers into engine frame buffers. */
#include "codol_history.h"
#include "codol_player_arrays.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef struct {
    codol_snapshot_state_t state;
    codol_player_fields_t player;
    codol_hud_state_t hud;
} frame_t;
struct codol_history_s {
    frame_t *frames[32];
    frame_t *pending;
    frame_t *baseline;
    frame_t *pending_baseline;
    uint32_t latest;
};
static void release(frame_t *f)
{
    if (!f) return;
    free((void *)f->state.entities); free((void *)f->state.clients); free((void *)f->state.actors); free((void *)f->state.glass); free(f);
}
static void *copy_array(const void *data, size_t count, size_t size)
{
    void *out;
    if (!count) return NULL;
    out = malloc(count*size);
    if (out) memcpy(out, data, count*size);
    return out;
}
static frame_t *clone_frame(const frame_t *source)
{
    frame_t *out;
    if (!source) return NULL;
    out = calloc(1, sizeof(*out));
    if (!out) return NULL;
    out->state = source->state;
    out->player = source->player; out->state.player = &out->player;
    out->hud = source->hud; out->state.hud = &out->hud;
    out->state.entities = NULL; out->state.clients = NULL; out->state.actors = NULL; out->state.glass = NULL;
    out->state.entities = copy_array(source->state.entities, source->state.entity_count,
                                     sizeof(*source->state.entities));
    out->state.clients = copy_array(source->state.clients, source->state.client_count,
                                    sizeof(*source->state.clients));
    out->state.actors = copy_array(source->state.actors, source->state.actor_count,
                                   sizeof(*source->state.actors));
    out->state.glass = copy_array(source->state.glass, source->state.glass_count,
                                  sizeof(*source->state.glass));
    if ((source->state.glass_count && !out->state.glass) ||
        (source->state.entity_count && !out->state.entities) ||
        (source->state.client_count && !out->state.clients) ||
        (source->state.actor_count && !out->state.actors)) {
        release(out); return NULL;
    }
    return out;
}
codol_history_t *CODOL_CreateHistory(void) { return calloc(1, sizeof(codol_history_t)); }
void CODOL_ClearHistory(codol_history_t *h)
{
    unsigned i;
    if (!h) return;
    for (i = 0; i < 32; ++i) release(h->frames[i]);
    release(h->pending);
    release(h->baseline);
    release(h->pending_baseline);
    memset(h, 0, sizeof(*h));
}
void CODOL_DestroyHistory(codol_history_t *h) { CODOL_ClearHistory(h); free(h); }
/* Why the last commit/prepare refused, for the server's overflow trace. */
static char history_failure[200];
const char *CODOL_HistoryFailure(void) { return history_failure; }
#define HFAIL(...) (snprintf(history_failure,sizeof(history_failure),__VA_ARGS__), 0)
static int commit(codol_history_t *h, const codol_snapshot_state_t *s,
                  const codol_snapshot_state_t *base, int rov, const codol_delta_context_t *ctx, int prepare)
{
    frame_t *f;
    size_t i;
    if (!h || !s || !s->player) return HFAIL("null history/state/player");
    if (s->sequence <= h->latest || s->sequence > 0x1fffffff)
        return HFAIL("sequence %u not after latest %u", s->sequence, h->latest);
    if (s->glass_count > CODOL_GLASS_MAX_PIECES || (s->glass_count && !s->glass) ||
        s->entity_count > 2047 || s->client_count > 32 || s->actor_count > 32 ||
        (s->entity_count && !s->entities) || (s->client_count && !s->clients) ||
        (s->actor_count && !s->actors) || (s->hud && (s->hud->count[0] > 31 || s->hud->count[1] > 31)))
        return HFAIL("counts: entities %u clients %u actors %u hud %u/%u", (unsigned)s->entity_count,
            (unsigned)s->client_count, (unsigned)s->actor_count,
            s->hud ? s->hud->count[0] : 0u, s->hud ? s->hud->count[1] : 0u);
    for (i = 0; i < s->entity_count; ++i)
        if (s->entities[i].number >= 2047 || s->entities[i].type > 255 ||
            (i && s->entities[i].number <= s->entities[i-1].number))
            return HFAIL("entity list order/range at index %u: number %u type %u", (unsigned)i,
                s->entities[i].number, s->entities[i].type);
    for (i = 0; i < s->client_count; ++i)
        if (s->clients[i].number >= 32 || (i && s->clients[i].number <= s->clients[i-1].number))
            return HFAIL("client list order/range at index %u", (unsigned)i);
    for (i = 0; i < s->actor_count; ++i)
        if (s->actors[i].number >= 32 || (i && s->actors[i].number <= s->actors[i-1].number))
            return HFAIL("actor list order/range at index %u", (unsigned)i);
    f = calloc(1, sizeof(*f));
    if (!f) return HFAIL("frame allocation");
    f->state = *s; f->player = *s->player; f->state.player = &f->player;
    if (s->hud) f->hud = *s->hud;
    f->state.hud = &f->hud;
    f->state.entities = copy_array(s->entities, s->entity_count, sizeof(*s->entities));
    f->state.clients = copy_array(s->clients, s->client_count, sizeof(*s->clients));
    f->state.actors = copy_array(s->actors, s->actor_count, sizeof(*s->actors));
    f->state.glass = copy_array(s->glass, s->glass_count, sizeof(*s->glass));
    if ((s->glass_count && !f->state.glass) ||
        (s->entity_count && !f->state.entities) || (s->client_count && !f->state.clients) ||
        (s->actor_count && !f->state.actors)) { release(f); return 0; }
    if (ctx) {
        static const codol_player_fields_t empty_player;
        size_t bi = 0;
        if (!CODOL_ReachPlayerFields(&f->player, base ? base->player : &empty_player, s->player, rov, ctx)) {
            release(f); return HFAIL("player fields not reachable (%s base)", base ? "delta" : "empty");
        }
        if (!CODOL_ReachHud(&f->hud, base ? base->hud : NULL, s->hud, ctx)) {
            release(f); return HFAIL("HUD not reachable: %s (%u/%u elements, %s base)", CODOL_ReachHudFailure(),
                s->hud ? s->hud->count[0] : 0u, s->hud ? s->hud->count[1] : 0u, base ? "delta" : "no");
        }
        for (i = 0; i < s->entity_count; ++i) {
            const codol_entity_state_t *old = NULL;
            while (base && bi < base->entity_count && base->entities[bi].number < s->entities[i].number) ++bi;
            if (base && bi < base->entity_count && base->entities[bi].number == s->entities[i].number)
                old = &base->entities[bi];
            if (!CODOL_ReachEntity((codol_entity_state_t *)f->state.entities+i, old, &s->entities[i], ctx)) {
                release(f); return HFAIL("entity %u (type %u) not reachable (%s base): %s", s->entities[i].number,
                    s->entities[i].type, old ? "delta" : "no", CODOL_ReachEntityFailure());
            }
        }
        bi = 0;
        for (i = 0; i < s->client_count; ++i) {
            const codol_client_state_t *old = NULL;
            while (base && bi < base->client_count && base->clients[bi].number < s->clients[i].number) ++bi;
            if (base && bi < base->client_count && base->clients[bi].number == s->clients[i].number)
                old = &base->clients[bi];
            if (!CODOL_ReachClient((codol_client_state_t *)f->state.clients+i, old, &s->clients[i], ctx)) {
                release(f); return HFAIL("client %u not reachable (%s base)", s->clients[i].number, old ? "delta" : "no");
            }
        }
    }
    if (prepare) { h->pending = f; return 1; }
    release(h->pending); h->pending = NULL;
    release(h->frames[s->sequence & 31]);
    h->frames[s->sequence & 31] = f; h->latest = s->sequence;
    return 1;
}
int CODOL_CommitHistory(codol_history_t *h, const codol_snapshot_state_t *s)
{
    return commit(h, s, NULL, 0, NULL, 0);
}
int CODOL_CommitReachedHistory(codol_history_t *h, const codol_snapshot_state_t *s,
                               uint32_t base_sequence, int rov, const codol_delta_context_t *ctx)
{
    const codol_snapshot_state_t *base = NULL;
    if (!ctx || !s) return 0;
    if (base_sequence) {
        base = CODOL_FindHistoryBase(h, base_sequence, s->sequence);
        if (!base) return 0;
    }
    return commit(h, s, base, rov, ctx, 0);
}
int CODOL_PrepareHistory(codol_history_t *h, const codol_snapshot_state_t *s,
                         uint32_t base_sequence, int rov, const codol_delta_context_t *ctx)
{
    const codol_snapshot_state_t *base = NULL;
    if (!h || h->pending || !s || !ctx)
        return HFAIL("prepare: %s", !h ? "no history" : h->pending ? "a frame is already pending" : "no state/context");
    if (base_sequence) {
        base = CODOL_FindHistoryBase(h, base_sequence, s->sequence);
        if (!base && h->baseline && h->baseline->state.sequence == base_sequence &&
            base_sequence < s->sequence) base = &h->baseline->state;
        if (!base) return HFAIL("prepare: base %u not held for %u (latest %u)", base_sequence, s->sequence, h->latest);
    }
    return commit(h, s, base, rov, ctx, 1);
}
int CODOL_PrepareBaselineHistory(codol_history_t *h, const codol_snapshot_state_t *s,
                                 int rov, const codol_delta_context_t *ctx)
{
    if (!CODOL_PrepareHistory(h, s, 0, rov, ctx)) return 0;
    h->pending_baseline = clone_frame(h->pending);
    if (!h->pending_baseline) {
        release(h->pending); h->pending = NULL;
        return HFAIL("prepare: baseline copy allocation");
    }
    return 1;
}
int CODOL_FinishHistory(codol_history_t *h, uint32_t sequence, int accepted)
{
    frame_t *f;
    if (!h || !h->pending || h->pending->state.sequence != sequence || (accepted != 0 && accepted != 1)) return 0;
    f = h->pending; h->pending = NULL;
    if (!accepted) {
        release(f); release(h->pending_baseline); h->pending_baseline = NULL;
        return 1;
    }
    if (h->pending_baseline) {
        release(h->baseline); h->baseline = h->pending_baseline;
        h->pending_baseline = NULL;
    }
    release(h->frames[sequence & 31]);
    h->frames[sequence & 31] = f; h->latest = sequence;
    return 1;
}
const codol_snapshot_state_t *CODOL_FindHistoryBase(const codol_history_t *h,
                                                  uint32_t ack, uint32_t next)
{
    const frame_t *f;
    if (!h || !ack || ack > h->latest || next <= h->latest || next > 0x1fffffff ||
        next <= ack || next-ack > 31) return NULL;
    f = h->frames[ack & 31];
    return f && f->state.sequence == ack ? &f->state : NULL;
}
const codol_snapshot_state_t *CODOL_HistoryPendingState(const codol_history_t *h)
{
    return h && h->pending ? &h->pending->state : NULL;
}
uint32_t CODOL_HistoryLatestSequence(const codol_history_t *h)
{
    return h ? h->latest : 0;
}
const codol_snapshot_state_t *CODOL_HistoryReceivedState(const codol_history_t *h,
                                                        uint32_t ack, uint32_t floor)
{
    uint32_t i;
    if (!h || !ack || !h->latest) return NULL;
    if (ack > h->latest) ack = h->latest;
    for (i = 0; i < 32 && ack - i > floor && ack - i > 0; ++i) {
        const frame_t *f = h->frames[(ack - i) & 31];
        if (f && f->state.sequence == ack - i) return &f->state;
    }
    return NULL;
}
const codol_snapshot_state_t *CODOL_HistoryBaseline(const codol_history_t *h)
{
    return h && h->baseline ? &h->baseline->state : NULL;
}
