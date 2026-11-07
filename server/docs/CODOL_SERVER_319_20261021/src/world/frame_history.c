#include "codol_frame_history.h"
#include <string.h>

void codol_frame_history_init(codol_frame_history_t *h)
{
    memset(h, 0, sizeof(*h));
}

void codol_frame_history_commit(codol_frame_history_t *h, const codol_snap_frame_t *f)
{
    if (!h || !f) return;
    h->frames[h->head] = *f;
    h->frames[h->head].valid = true;
    h->head = (h->head + 1) % CODOL_SNAP_HISTORY;
    if (h->count < CODOL_SNAP_HISTORY) h->count++;
}

void codol_frame_history_ack(codol_frame_history_t *h, uint32_t seq)
{
    if (!h) return;
    /* 只前进不回退(乱序 ACK 不倒退基线) */
    if (!h->has_ack || seq > h->last_ack) { h->last_ack = seq; h->has_ack = true; }
}

const codol_snap_frame_t *codol_frame_history_baseline(const codol_frame_history_t *h)
{
    int i;
    if (!h || !h->has_ack) return NULL;
    for (i = 0; i < CODOL_SNAP_HISTORY; i++) {
        if (h->frames[i].valid && h->frames[i].seq == h->last_ack)
            return &h->frames[i];
    }
    return NULL;
}

bool codol_frame_history_baseline_expired(const codol_frame_history_t *h, uint32_t now_seq)
{
    if (!h || !h->has_ack) return true;
    /* 基线太旧(超出历史窗口) => 过期, 应发完整帧 */
    return (now_seq - h->last_ack) >= CODOL_SNAP_HISTORY;
}
