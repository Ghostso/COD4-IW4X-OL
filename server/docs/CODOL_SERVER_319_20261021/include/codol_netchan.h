#ifndef CODOL_NETCHAN_H
#define CODOL_NETCHAN_H
/* netchan —— 结构照 IW4 引擎(经 IW4X Game/Structs.hpp:7119 确认),
 * 行为照 CoD4x src/netchan.c(IW3, 同族)。
 * ★ 与 CoD4x 的差别: IW4 用单个 int qport, 没有 CoD4x 自加的 upperqport。 */
#include "codol_types.h"
#include "codol_msg.h"

#ifdef __cplusplus
extern "C" {
#endif

/* 发送回调: 把 bytes 交给传输层(len 已含 netchan 头) */
typedef int (*codol_netchan_send_fn)(void *ctx, const codol_netadr_t *to,
                                     const uint8_t *data, int len);

void codol_netchan_setup(codol_netchan_t *chan, int sock,
                         const codol_netadr_t *adr, unsigned int qport,
                         uint8_t *unsent_buffer, int unsent_buffer_size,
                         uint8_t *fragment_buffer, int fragment_buffer_size);

/* 发送一条消息(超长自动转分片, 每次只发一片) */
int  codol_netchan_transmit(codol_netchan_t *chan, int length, const uint8_t *data,
                            codol_netchan_send_fn send, void *ctx);

/* 继续发送剩余分片; 返回 1=还有, 0=发完 */
int  codol_netchan_transmit_next_fragment(codol_netchan_t *chan,
                                          codol_netchan_send_fn send, void *ctx);

/* 处理收到的包: 成功则 msg 定位在载荷起点, 返回 true。
 * 会丢弃 sequence <= incomingSequence 的包(乱序/重包)。 */
bool codol_netchan_process(codol_netchan_t *chan, codol_msg_t *msg);

/* ---- CODOL 3.19 客户端分片(FAT)接收重组 ---------------------------------
 * 布局见 codol_types.h 的 CODOL_FAT_* 常量块。状态按 peer 独立保存。
 *
 * 返回:
 *   > 0  重组完成 —— 整条消息位于 r->buffer[0..返回值), 形如
 *        u32(序号) ‖ 各片负载(即普通帧那条 13 字节头开头的消息)。
 *        调用方随后按普通帧同一套 13 字节头解析它。
 *     0  本片已收下, 但消息还没收全(重复片也返回 0, 可安全忽略)。
 *   < 0  无效分片(越界/步长不符/序号非法/超过上限/分片确认包)。
 *
 * ctl/ctl_len 非空时: 若该片带 RELIABLE 位, 生成分片确认应答写到 ctl,
 * 长度写入 *ctl_len(否则 0)。实测客户端的分片**不带** RELIABLE 位,
 * 所以这条通常不触发, 但按参照实现保留。 */
int codol_fat_receive(codol_fat_reassembler_t *r, const uint8_t *pkt, int len,
                      uint8_t *ctl, int ctl_cap, int *ctl_len);

/* 清空一条连接的分片重组状态(重连/重新握手时调用) */
void codol_fat_reset(codol_fat_reassembler_t *r);

#ifdef __cplusplus
}
#endif
#endif /* CODOL_NETCHAN_H */
