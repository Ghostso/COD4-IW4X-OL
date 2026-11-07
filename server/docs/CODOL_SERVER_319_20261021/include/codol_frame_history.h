#ifndef CODOL_FRAME_HISTORY_H
#define CODOL_FRAME_HISTORY_H
/* 快照帧历史与 delta 基线 —— 照手册 §2.5 的**不变量**(不照搬字段/位宽):
 *   · 按客户端保存最近若干帧状态
 *   · 选"客户端已确认的旧帧"作 delta 基线
 *   · 基线过期 -> 回退完整帧
 *   · **发送成功后才提交历史**
 */
#include <stdint.h>
#include <stdbool.h>
#include "codol_player.h"

#ifdef __cplusplus
extern "C" {
#endif

#define CODOL_SNAP_HISTORY 32

typedef struct {
    uint32_t      seq;        /* netchan 序号 */
    uint32_t      server_time;
    codol_player_t player;
    bool          valid;
} codol_snap_frame_t;

typedef struct {
    codol_snap_frame_t frames[CODOL_SNAP_HISTORY];
    int           head;
    int           count;
    uint32_t      last_ack;      /* 客户端最近确认的 seq */
    bool          has_ack;
} codol_frame_history_t;

void codol_frame_history_init(codol_frame_history_t *h);

/* 发送成功后才提交(手册不变量) */
void codol_frame_history_commit(codol_frame_history_t *h, const codol_snap_frame_t *f);

/* 客户端 ACK 提交 */
void codol_frame_history_ack(codol_frame_history_t *h, uint32_t seq);

/* 选 delta 基线: 客户端已确认的那一帧; 过期/不存在返回 NULL(=> 发完整帧) */
const codol_snap_frame_t *codol_frame_history_baseline(const codol_frame_history_t *h);

/* 基线是否过期(手册: 过期回退完整帧) */
bool codol_frame_history_baseline_expired(const codol_frame_history_t *h, uint32_t now_seq);

#ifdef __cplusplus
}
#endif
#endif /* CODOL_FRAME_HISTORY_H */
