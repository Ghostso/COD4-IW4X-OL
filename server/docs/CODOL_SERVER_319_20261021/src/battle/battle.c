#include "codol_battle.h"
#include <string.h>
#include <stdio.h>

#ifdef _WIN32
#include <windows.h>
static uint32_t mono_ms(void) { return (uint32_t)GetTickCount64(); }
#else
#include <time.h>
static uint32_t mono_ms(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint32_t)((uint64_t)ts.tv_sec * 1000 + ts.tv_nsec / 1000000);
}
#endif

static uint16_t rd16(const uint8_t *p) { return (uint16_t)(p[0] | (p[1] << 8)); }
static uint32_t rd32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static uint64_t rd64(const uint8_t *p)
{
    return (uint64_t)rd32(p) | ((uint64_t)rd32(p + 4) << 32);
}
static void wr16(uint8_t *p, uint16_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); }
static void wr32(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); p[2] = (uint8_t)(v >> 16); p[3] = (uint8_t)(v >> 24);
}
static void wr64(uint8_t *p, uint64_t v) { wr32(p, (uint32_t)v); wr32(p + 4, (uint32_t)(v >> 32)); }

static uint32_t rnd(codol_battle_t *b)
{
    b->nonce = b->nonce * 1664525u + 1013904223u;
    return (b->nonce >> 8);
}

static int hexval(int c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

/* ★★★ 2026-11-06 (实机纠正): securityKey 必须用**大厅下发的值**, 不是客户端内置常量。
 *
 * 服务端 0xBBDE10 用 ACK 尾 8 字节(= 会话 id)去 引擎+0x40 表里查 16 字节密钥,
 * 命中的那条是**大厅注入的会话项**(0x7F5A50(key, value) → 0xBB9D40 插入),
 * 其 value 就是 lobby_server.py 的 SEC_KEY, 同时被写成 battle_security_key.txt。
 * 客户端 0x621DB0 注册的 "CoDOnlin" 条目只是启动时的**独立默认项**, 与本会话无关。
 *
 * 因此这里恢复为读取大厅写出的文件(读不到才回退 0x01)。
 * 此前误改为硬编码 03 09 02 0F… —— 那会让传输密钥与客户端不一致。 */
static bool load_security_key(uint8_t out16[16])
{
    FILE *fp = fopen("battle_security_key.txt", "rb");
    char buf[128];
    size_t n, i;
    if (!fp) return false;
    n = fread(buf, 1, sizeof(buf) - 1, fp);
    fclose(fp);
    buf[n] = '\0';
    while (n > 0 && (buf[n - 1] == '\n' || buf[n - 1] == '\r' ||
                     buf[n - 1] == ' '  || buf[n - 1] == '\t')) {
        buf[--n] = '\0';
    }
    if (n < 32) return false;
    for (i = 0; i < 16; i++) {
        int hi = hexval((unsigned char)buf[i * 2]);
        int lo = hexval((unsigned char)buf[i * 2 + 1]);
        if (hi < 0 || lo < 0) return false;
        out16[i] = (uint8_t)((hi << 4) | lo);
    }
    return true;
}

void codol_battle_init(codol_battle_t *b)
{
    memset(b, 0, sizeof(*b));
    if (load_security_key(b->security_key)) {
        fprintf(stderr, "[battle] securityKey <- battle_security_key.txt "
                        "(%02X%02X%02X%02X...) 大厅下发值\n",
                b->security_key[0], b->security_key[1],
                b->security_key[2], b->security_key[3]);
    } else {
        memset(b->security_key, 0x01, sizeof(b->security_key));
        fprintf(stderr, "[battle] securityKey = 0x01*16 "
                        "(未找到 battle_security_key.txt, 回退默认)\n");
    }
    b->nonce = mono_ms() | 1u;
    codol_p224_gen_keypair(b->priv, &b->pub);
}

codol_battle_assoc_t *codol_battle_find(codol_battle_t *b, const codol_netadr_t *peer)
{
    int i;
    for (i = 0; i < CODOL_BATTLE_MAX_PEERS; i++) {
        codol_battle_assoc_t *a = &b->peers[i];
        if (!a->in_use) continue;
        if (a->peer.type == peer->type && a->peer.port == peer->port &&
            /* ★ 2026-11-07 (run ONCE_20261107_164303 实机判定):
             *   ip[] 是 16 字节, 但只有前 4 字节是 IPv4 地址(battle.c:187 的
             *   `cookie[24+i] = peer->ip[i]` 也只取 4 字节)。原实现 memcmp 16 字节,
             *   把 4..15 这段**未定义的填充**也纳入比较 —— 一旦某条填充字节变化,
             *   同一个对端就 find 不到, 表现为「assoc=无 而 peer[0] type/port 全同」。
             *   实机日志: incoming{type=1 port=22011} / peer[0] type=1 port=22011
             *   key_ready=1 / live_peers=1, 仍然返回 NULL ⇒ 只能是 ip 的填充位在比。
             *   这里只比 4 字节, 与全库其余地址比较口径一致。 */
            memcmp(a->peer.ip, peer->ip, 4) == 0)
            return a;
    }
    return NULL;
}

codol_battle_assoc_t *codol_battle_find_or_alloc(codol_battle_t *b, const codol_netadr_t *peer)
{
    codol_battle_assoc_t *a = codol_battle_find(b, peer);
    int i;
    if (a) return a;
    for (i = 0; i < CODOL_BATTLE_MAX_PEERS; i++) {
        if (!b->peers[i].in_use) {
            memset(&b->peers[i], 0, sizeof(b->peers[i]));
            b->peers[i].in_use = true;
            memcpy(&b->peers[i].peer, peer, sizeof(*peer));
            /* ★ 2026-11-07: ip[] 只有前 4 字节是 IPv4, 4..15 是未定义填充。
             *   来源处的填充每次可能不同, 这里统一清零, 避免污染任何比较。 */
            memset(b->peers[i].peer.ip + 4, 0, 12);
            return &b->peers[i];
        }
    }
    return NULL;
}

/* ① NAT 遍历: 29B, pkt[0] 13(0x0D Probe)->12(0x0C Ack), 末 6B 必须回指本机 127.0.0.1:28960
 *    依据: 实机抓包常量（BATTLE_SERVER_PROTOCOL.md），首字节 0x0D -> 应答 0x0C，其余 28B 原样回显 */
int codol_battle_try_nat_reply(codol_battle_t *b, const codol_netadr_t *peer,
                               const uint8_t *pkt, int len,
                               uint8_t *out, int out_cap)
{
    (void)b; (void)peer;
    if (len != 29 || pkt[0] != 13 || pkt[1] != 2 || pkt[2] != 0) return 0;
    if (!(pkt[23] == 127 && pkt[24] == 0 && pkt[25] == 0 && pkt[26] == 1 &&
          pkt[27] == 0x20 && pkt[28] == 0x71)) return 0;
    if (out_cap < 29) return 0;
    memcpy(out, pkt, 29);
    out[0] = 12;
    return 29;
}

/* ② DTLS init: 收 16B -> 回 38B cookie */
int codol_battle_try_init_ack(codol_battle_t *b, const codol_netadr_t *peer,
                              const uint8_t *pkt, int len, uint8_t *out, int out_cap)
{
    codol_battle_assoc_t *a;
    uint16_t client_tag;
    uint16_t server_tag;
    uint64_t session_id;
    int i;

    if (len != 16 || pkt[0] != 1 || pkt[1] != 2) return 0;
    if (rd16(pkt + 2) != 0) return 0;
    client_tag = rd16(pkt + 6);
    if (client_tag == 0) return 0;
    /* ★ 2026-11-05 修正: 这里原先是 `if (rd64(pkt + 8) != 1) return 0;`
     *   —— 那是从"会话 id 恰好是 1"的样例里抄来的常量, 真机客户端填的是**大厅
     *   createSession 下发的会话 id**(实测 `88 77 66 55 44 33 22 11`)。
     *   结果: 客户端每 ~4s 发一次 16B init, 服务端**每次都丢掉**, 永远不回 38B cookie,
     *   客户端就一直停在"等待连接"(clientState 到不了 3), 直到 15s 判超时回大厅。
     *   现在: 原样取用客户端给的会话 id, 存进 assoc 并回填 cookie 末尾。 */
    session_id = rd64(pkt + 8);
    if (out_cap < CODOL_BATTLE_COOKIE_LEN) return 0;

    a = codol_battle_find_or_alloc(b, peer);
    if (!a) return 0;

    /* 同一 client_tag 复用既有 cookie(客户端重发时保持稳定) */
    if (a->cookie[0] == 0 || a->client_tag != client_tag
        || a->session_id != session_id) {
        server_tag = (uint16_t)(rnd(b) & 0xFFFF);
        if (server_tag == 0) server_tag = 1;
        a->client_tag = client_tag;
        a->server_tag = server_tag;
        a->session_id = session_id;

        memset(a->cookie, 0, sizeof(a->cookie));
        a->cookie[0] = 2; a->cookie[1] = 2;
        wr16(a->cookie + 2, client_tag);
        wr16(a->cookie + 4, 0);
        wr32(a->cookie + 6, mono_ms());
        /* [10..13] 留 0 */
        wr16(a->cookie + 14, server_tag);
        wr16(a->cookie + 16, server_tag);
        wr16(a->cookie + 18, client_tag);
        /* [20..23] 留 0 */
        for (i = 0; i < 4; i++) a->cookie[24 + i] = peer->ip[i];
        wr16(a->cookie + 28, peer->port);
        wr64(a->cookie + 30, session_id);
    }

    memcpy(out, a->cookie, CODOL_BATTLE_COOKIE_LEN);
    return CODOL_BATTLE_COOKIE_LEN;
}

/* ③ 密钥交换: 收 219B -> 回 114B(内含 100B 公钥) 并派生传输密钥 */
int codol_battle_try_key_exchange_ack(codol_battle_t *b, const codol_netadr_t *peer,
                                      const uint8_t *pkt, int len,
                                      uint8_t *out, int out_cap)
{
    codol_battle_assoc_t *a;
    uint8_t shared[28];
    codol_p224_point_t peer_pub;

    if (len != 219 || pkt[0] != 3 || pkt[1] != 2) return 0;
    a = codol_battle_find(b, peer);
    if (!a || a->cookie[0] == 0) return 0;
    if (rd16(pkt + 2) != rd16(a->cookie + 14)) return 0;          /* 客户端回显 server_tag */
    if (memcmp(pkt + 6, a->cookie, CODOL_BATTLE_COOKIE_LEN) != 0) return 0;
    /* ★ 2026-11-05: 原为常量判据 `if (rd64(pkt + 111) != 1) return 0;`。
     *   实测 init 侧该字段 = 大厅下发的 u64 会话 id, 所以这里本该比对会话 id;
     *   但样例抓包把它记成 1, 无法排除"它其实是独立常量"的可能 —— 两种都放行。
     *   真实取值由 battle_service.c 的 KX 诊断日志记录(那边有 log 依赖)。 */
    {
        uint64_t ksid = rd64(pkt + 111);
        if (ksid != a->session_id && ksid != 1) return 0;
    }
    if (out_cap < CODOL_BATTLE_ACK_LEN) return 0;

    /* ★★★ 2026-11-07 (实机): 每次 createSession(21/1) 客户端都会在 A-phase
     *   0x7F4630 重新生成一份 16 字节 securityKey 并经大厅写出。
     *   本进程启动时只读过一次, 于是"客户端重连(新 key)"之后所有数据帧都会
     *   HMAC 失败 -> RX_DROP 风暴 -> 永远卡在"等待连接"。
     *   实测 run ONCE_20261107_103242: 首会话 key=8f2f… 握手/数据全通;
     *   10:34:46 客户端重新 21/1 key=9d1d… 换 tag 重连, 服务端仍用旧 key,
     *   20 帧全 DROP。
     *   ⇒ 在每次 KX(派生传输密钥之前)重新读一次文件, key 变了就换用。 */
    {
        uint8_t fresh[16];
        if (load_security_key(fresh) && memcmp(fresh, b->security_key, 16) != 0) {
            memcpy(b->security_key, fresh, 16);
            fprintf(stderr, "[battle] securityKey 已按新 21/1 会话更新 (%02X%02X%02X%02X...)\n",
                    fresh[0], fresh[1], fresh[2], fresh[3]);
        }
    }

    if (!codol_p224_import_pubkey(pkt + 119, &peer_pub)) return 0;
    if (!codol_p224_ecdh(b->priv, &peer_pub, shared)) return 0;
    codol_derive_transport_key(shared, b->security_key, a->transport_key);
    a->key_ready = true;
    a->send_seq = 0;
    a->recv_seq = 0;

    memset(out, 0, CODOL_BATTLE_ACK_LEN);
    out[0] = 4;
    out[1] = 2;
    out[2] = a->cookie[2];      /* 参照实现: 这里放 client_tag */
    out[3] = a->cookie[3];
    codol_p224_export_pubkey(&b->pub, out + 6);
    /* ★★★ 2026-11-06 (实机纠正): [106..114] 这 8 字节 = **会话在 引擎+0x170 里的键**。
     *
     * 外层 type-4 分支 0xBB429D 的实参把"过滤开关"置 1：
     *     BB42E8  call 0xBBFF90(&tail8)      ; 取 ACK 尾 8 字节
     *     BB42F3  push 1                     ; ★ 第 7 参 = 1 ⇒ 启用名字过滤
     *     BB42FE  push &tail8                ; 过滤器 = 这 8 字节
     *     BB4309  call 0xBB1CB0
     * 而 0xBB1CB0 的过滤是：
     *     BB1D63  lea eax,[esi+8]            ; 引擎+0x170 条目的 8 字节键
     *     BB1E63  call 0xB74090              ; 与 ACK 尾 8 字节比较
     *     BB1E6A  je 0xBB1EBA                ; 不匹配 ⇒ 该会话被跳过
     * ⇒ 尾 8 字节对不上 ⇒ ACK 在任何校验之前就被丢弃 ⇒ 客户端状态停在 2、
     *   反复重发 KX、6 次后换 tag 重来(实机 run ONCE_20261106_001100 已复现)。
     *
     * 键空间 = 会话 id：0x7F5AB0 按键删除时，用同一个 key 去比连接对象的
     * [obj+8]→+0xC(即会话 id)，再调 0xBB9E70(引擎+0x40, key) 删除。
     * 因此这里必须回填 init[8..16] 那个会话 id。
     *
     * (此前误改为 "CoDOnlin" —— 那是 0x621DB0 在启动时注册的**独立默认项**，
     *  与战斗会话无关；实机证明它会被路由层直接丢掉。) */
    wr64(out + 106, a->session_id);
    return CODOL_BATTLE_ACK_LEN;
}

int codol_battle_send_data(codol_battle_assoc_t *a, const uint8_t *plain, int len,
                           uint8_t *out, int out_cap)
{
    uint8_t seed[6], mac[20];
    uint8_t auth[6 + 2 + 2048];
    uint32_t seq;
    int auth_len;

    if (!a || !a->key_ready || len < 0 || out_cap < CODOL_BATTLE_FRAME_HDR + len) return 0;
    /* ★ 客户端 0xBBDC00 对 >1256 的明文直接返回 -6 不发送 ⇒ 这里必须先挡住,
     *   否则服务端会"发送成功"(进而 tx_frames++), 客户端却静默丢弃。 */
    if (len > CODOL_BATTLE_MAX_PLAIN) return 0;

    memset(out, 0, CODOL_BATTLE_FRAME_HDR + (size_t)len);
    out[0] = 6;
    out[1] = 2;
    /* ★ 帧内 tag = **接收方**的 tag: 发给客户端 => client_tag(cookie[2..3]);
     *   客户端发来的帧我们则按 server_tag(cookie[14..15]) 校验。 */
    out[2] = a->cookie[2];
    out[3] = a->cookie[3];
    seq = a->send_seq++;
    wr16(out + 4, (uint16_t)seq);
    wr16(out + 14, (uint16_t)len);

    /* ★ seed[0..4] = **完整 32 位**序号(小端), seed[4..6] = tag。
     *   客户端 0xBC2C60 用 0xC74840 从线上 16 位重建 32 位, 再整体 4 字节写入 seed。
     *   只写低 16 位会让序号过 65536 回绕后密钥流与服务端错位。 */
    seed[0] = (uint8_t)(seq & 0xFF);
    seed[1] = (uint8_t)((seq >> 8) & 0xFF);
    seed[2] = (uint8_t)((seq >> 16) & 0xFF);
    seed[3] = (uint8_t)((seq >> 24) & 0xFF);
    seed[4] = out[2]; seed[5] = out[3];
    codol_keystream_xor(a->transport_key, seed, plain, (size_t)len, out + 16);

    /* auth = pkt[0:6] + pkt[14:]
     * ★ 不是缺陷: 客户端 0xBC2C60 的 MAC 也覆盖这 6 字节头 ——
     *   它先 HMAC_Update(帧基址, N), N 由 0xBC26B0 -> 0xBC2540 序列化器写出,
     *   0xBC2540 恰好写 1+1+2+2 = 6 字节(type/const/tag/seq), 即同一份记录头。 */
    memcpy(auth, out, 6);
    auth_len = 6;
    memcpy(auth + auth_len, out + 14, (size_t)(2 + len));
    auth_len += 2 + len;
    codol_hmac_sha1(a->transport_key, 24, auth, (size_t)auth_len, mac);
    memcpy(out + 6, mac, 8);
    return CODOL_BATTLE_FRAME_HDR + len;
}

/* 由线上 16 位序号重建 32 位: 以上次值为基准, 取最近的一次回绕。
 * 客户端对**收**帧用的是同一套语义(0xC74840)。 */
static uint32_t codol_seq_extend(uint32_t last, uint16_t lo)
{
    uint32_t base  = last & 0xFFFF0000u;
    int32_t  delta = (int32_t)lo - (int32_t)(last & 0xFFFFu);
    if (delta < -32768) {
        base += 0x10000u;
    } else if (delta > 32767) {
        if (base >= 0x10000u) base -= 0x10000u;
    }
    return base | (uint32_t)lo;
}

int codol_battle_read_data(codol_battle_assoc_t *a, const uint8_t *pkt, int len,
                           uint8_t *plain_out, int out_cap)
{
    uint8_t mac[20], seed[6];
    uint8_t auth[6 + 2 + 2048];
    uint16_t enc_len;
    uint32_t seq;
    int auth_len;

    if (!a || !a->key_ready || len < CODOL_BATTLE_FRAME_HDR) return -1;
    if (pkt[0] != 6 || pkt[1] != 2) return -1;
    if (pkt[2] != a->cookie[14] || pkt[3] != a->cookie[15]) return -1;

    enc_len = rd16(pkt + 14);
    if ((int)enc_len > len - CODOL_BATTLE_FRAME_HDR) return -1;
    if ((int)enc_len > out_cap) return -1;

    /* auth = pkt[0:6] + pkt[14:] —— 与客户端 0xBC2C60 一致(见 send_data 的说明) */
    memcpy(auth, pkt, 6);
    auth_len = 6;
    memcpy(auth + auth_len, pkt + 14, (size_t)(2 + enc_len));
    auth_len += 2 + enc_len;
    codol_hmac_sha1(a->transport_key, 24, auth, (size_t)auth_len, mac);
    if (memcmp(mac, pkt + 6, 8) != 0) return -1;

    /* 线上只有 16 位, 但 seed 要完整 32 位 */
    a->recv_seq = codol_seq_extend(a->recv_seq, rd16(pkt + 4));
    seq = a->recv_seq;
    seed[0] = (uint8_t)(seq & 0xFF);
    seed[1] = (uint8_t)((seq >> 8) & 0xFF);
    seed[2] = (uint8_t)((seq >> 16) & 0xFF);
    seed[3] = (uint8_t)((seq >> 24) & 0xFF);
    seed[4] = pkt[2]; seed[5] = pkt[3];
    codol_keystream_xor(a->transport_key, seed, pkt + 16, enc_len, plain_out);
    return (int)enc_len;
}

void codol_battle_note_keepalive(codol_battle_assoc_t *a, const uint8_t *pkt, int len)
{
    if (!a || !pkt || len < 6) return;
    /* type-7 与数据帧共用序号计数器(客户端 [DTLS+0x508]), 只推进不判重放。 */
    a->recv_seq = codol_seq_extend(a->recv_seq, rd16(pkt + 4));
}
