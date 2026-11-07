#ifndef CODOL_BATTLE_H
#define CODOL_BATTLE_H
/* CODOL 战斗服"外层"—— NAT / DTLS-like 握手 / 数据帧。
 * 字节布局逐条对齐客户端实测(经参照实现与客户端交互验证):
 *   NAT:      收 29B(type 0x0D) -> 回 29B(type 0x0C)
 *   DTLS init:收 16B              -> 回 38B cookie
 *   密钥交换: 收 219B             -> 回 114B ack(内含 100B 公钥)
 *   数据帧:   06 02 <tag:2> <seq:2> <hmac:8> <len:2> <cipher>
 *             AES 流 seed = seq[0..4](完整 32 位小端), tag_lo, tag_hi   ; HMAC-SHA1 前 8B
 *             HMAC 输入 = 帧头 6B || 长度 2B || 密文
 *             (客户端 0xBC2C60: HMAC_Update(帧基址,6) 由 0xBC2540 序列化出 6 字节头证明;
 *              再 HMAC_Update(载荷起点-2, ...) 覆盖长度字段到帧尾)
 */
#include "codol_types.h"
#include "codol_crypto.h"

#ifdef __cplusplus
extern "C" {
#endif

#define CODOL_BATTLE_MAX_PEERS   16
#define CODOL_BATTLE_COOKIE_LEN  38
#define CODOL_BATTLE_ACK_LEN     114
#define CODOL_BATTLE_FRAME_HDR   16

/* ★★★ 单帧明文上限 1256 字节 —— 客户端硬编码, 超出直接拒发。
 *
 * 证据: 客户端真正的出站函数 0xBBDC00(vtable +04 = 0xBBE1C0 尾调用进来):
 *     0xBBDC2E  cmp dword [ebp+0x10], 0x4E8    ; 第 3 参(长度) vs 1256
 *     0xBBDC43  jae 0xBBDD12                  ; 超长 -> eax = 0xFFFFFFFA (-6), 不发送
 * 注意 0xBBE1C0 只是状态闸(要求 [DTLS+0x4d4]==3), 真正组帧发送在 0xBBDC00。
 *
 * 架构上 netchan 分片步长 CODOL_FAT_STRIDE = 1154, 加 10B 分片头 = 1164,
 * 再套 netchan 头仍在 1256 以内 —— 所以正常路径不会触发; 这道闸是防止上层
 * 误传大包时"服务端以为发成功、客户端静默丢弃"。 */
#define CODOL_BATTLE_MAX_PLAIN   1256

/* ★★★ 2026-11-06 实机纠正（推翻前一版的两条判断）
 *
 * ① ACK 尾 8 字节 = **会话在 引擎+0x170 里的键**（路由用），必须回填会话 id。
 *    证据：外层 type-4 分支 0xBB429D 以 `push 1` 打开名字过滤，并把 ACK 尾 8 字节
 *    作为过滤器传给 0xBB1CB0；后者用 0xB74090 把它与 引擎+0x170 条目的 8 字节键比较，
 *    不匹配就跳过该会话 —— ACK 在进入任何校验之前被丢弃。
 *    键空间 = 会话 id（0x7F5AB0 按键删除时用同一 key 比对连接对象 +0xC）。
 *    实机 run ONCE_20261106_001100 用 "CoDOnlin" 复现了"KX 重发 6 次后换 tag 重来"。
 *
 * ② securityKey 必须用**大厅下发的** battle_security_key.txt（由 lobby_server.py 的
 *    SEC_KEY 写出）。客户端 0x621DB0 注册的 "CoDOnlin" 条目只是启动时的独立默认项，
 *    与本会话无关；0xBBDE10 用会话 id 查到的才是大厅注入的那 16 字节。 */

typedef struct {
    bool     in_use;
    codol_netadr_t peer;
    uint8_t  cookie[CODOL_BATTLE_COOKIE_LEN];
    uint16_t client_tag;
    uint16_t server_tag;
    /* ★ 会话 id: 客户端把大厅 createSession 下发的 **u64 会话 id** 原样填进
     *   DTLS init 的 [8..16](实测 = 0x1122334455667788, 正是我们大厅回的 sessionId)。
     *   本地抓包把这一字段当成常量 1 是**错的** —— 服务端必须原样回填到 cookie
     *   末尾 8 字节, 客户端才认可 cookie 并发 219B 密钥交换。 */
    uint64_t session_id;
    uint8_t  transport_key[24];
    /* ★ 32 位序号: 线上只传低 16 位, 但 AES 流的 seed 用的是**完整 32 位**。
     *   客户端 0xBC2C60 用 0xC74840 从 16 位重建 32 位, 再把 4 字节整体塞进 seed[0..4]。
     *   若这里只维护 16 位, 序号过 65536 回绕后 seed 高 16 位会与服务端不一致 ⇒ 解密错位。 */
    uint32_t send_seq;
    uint32_t recv_seq;          /* 上一个已接受的 32 位收帧序号, 用于从 16 位重建 */
    bool     key_ready;
    /* 客户端分片(FAT)重组状态 —— 必须**按 peer** 保存, 不能全局共享 */
    codol_fat_reassembler_t fat;
    uint32_t fat_frames;        /* 收到的分片帧数 */
    uint32_t fat_reassembled;   /* 成功重组条数 */
    uint32_t fat_invalid;       /* 被拒分片数 */
} codol_battle_assoc_t;

typedef struct {
    codol_battle_assoc_t peers[CODOL_BATTLE_MAX_PEERS];
    uint8_t  security_key[16];
    uint8_t  priv[28];
    codol_p224_point_t pub;
    uint32_t nonce;
} codol_battle_t;

void codol_battle_init(codol_battle_t *b);
codol_battle_assoc_t *codol_battle_find(codol_battle_t *b, const codol_netadr_t *peer);
codol_battle_assoc_t *codol_battle_find_or_alloc(codol_battle_t *b, const codol_netadr_t *peer);

/* 三个握手入口: 命中则返回应答长度(>0)并写入 out; 未命中返回 0 */
int codol_battle_try_nat_reply(codol_battle_t *b, const codol_netadr_t *peer,
                               const uint8_t *pkt, int len,
                               uint8_t *out, int out_cap);
int codol_battle_try_init_ack(codol_battle_t *b, const codol_netadr_t *peer,
                              const uint8_t *pkt, int len, uint8_t *out, int out_cap);
int codol_battle_try_key_exchange_ack(codol_battle_t *b, const codol_netadr_t *peer,
                                      const uint8_t *pkt, int len,
                                      uint8_t *out, int out_cap);

/* 数据帧 */
int  codol_battle_send_data(codol_battle_assoc_t *a, const uint8_t *plain, int len,
                            uint8_t *out, int out_cap);
/* 成功返回明文长度(>=0), 失败返回 -1 */
int  codol_battle_read_data(codol_battle_assoc_t *a, const uint8_t *pkt, int len,
                            uint8_t *plain_out, int out_cap);

/* 记录一条**非数据帧**(客户端 type-7 保活)的序号, 只推进 32 位收帧序号, 不改连接状态。
 * 客户端状态泵 0xBBEA80 在 [DTLS+0x4d4]==3 之后按 [+0x5d8] 周期调 0xBBDD40 发 type-7;
 * 其接收处理器 0xBB4593 直接返回(什么都不做) ⇒ 服务端静默忽略即可。
 * 但这些帧与数据帧**共用同一个序号计数器**, 不推进会让后续数据帧的 16 位差值变大。 */
void codol_battle_note_keepalive(codol_battle_assoc_t *a, const uint8_t *pkt, int len);

#ifdef __cplusplus
}
#endif
#endif /* CODOL_BATTLE_H */
