#include "codol_netchan.h"
#include <string.h>

void codol_netchan_setup(codol_netchan_t *chan, int sock,
                         const codol_netadr_t *adr, unsigned int qport,
                         uint8_t *unsent_buffer, int unsent_buffer_size,
                         uint8_t *fragment_buffer, int fragment_buffer_size)
{
    memset(chan, 0, sizeof(*chan));
    chan->sock = sock;
    chan->incoming_sequence = -1;   /* 首包 sequence=0 必须被接受 */
    if (adr) memcpy(&chan->remote_address, adr, sizeof(*adr));
    chan->qport = (int)qport;
    chan->unsent_buffer = unsent_buffer;
    chan->unsent_buffer_size = unsent_buffer_size;
    chan->fragment_buffer = fragment_buffer;
    chan->fragment_buffer_size = fragment_buffer_size;
}

int codol_netchan_transmit(codol_netchan_t *chan, int length, const uint8_t *data,
                           codol_netchan_send_fn send, void *ctx)
{
    uint8_t pkt[CODOL_NETCHAN_MAX_PACKETLEN];
    codol_msg_t m;

    if (!chan || !send) return 0;
    if (length < 0 || length > chan->unsent_buffer_size) return 0;

    chan->unsent_fragment_start = 0;

    /* 超长 -> 先拷进 unsent 缓冲, 只发第一片 */
    if (length >= CODOL_NETCHAN_FRAGMENT_SIZE) {
        chan->unsent_fragments = 1;
        chan->unsent_length = length;
        memcpy(chan->unsent_buffer, data, (size_t)length);
        codol_netchan_transmit_next_fragment(chan, send, ctx);
        return 1;
    }

    codol_msg_init(&m, pkt, sizeof(pkt));
    codol_msg_write_long(&m, chan->outgoing_sequence);
    chan->outgoing_sequence++;
    /* 服务端发送不带 qport(客户端才带) */
    if (chan->sock == 0) codol_msg_write_short(&m, chan->qport);
    codol_msg_write_data(&m, data, length);
    if (m.overflowed) return 0;
    return send(ctx, &chan->remote_address, pkt, m.cursize);
}

int codol_netchan_transmit_next_fragment(codol_netchan_t *chan,
                                         codol_netchan_send_fn send, void *ctx)
{
    uint8_t pkt[CODOL_NETCHAN_MAX_PACKETLEN];
    codol_msg_t m;
    int fragment_length;

    if (!chan || !chan->unsent_fragments || !send) return 0;

    fragment_length = chan->unsent_length - chan->unsent_fragment_start;
    if (fragment_length > CODOL_NETCHAN_FRAGMENT_SIZE)
        fragment_length = CODOL_NETCHAN_FRAGMENT_SIZE;

    codol_msg_init(&m, pkt, sizeof(pkt));
    codol_msg_write_long(&m, (int)(chan->outgoing_sequence | (int)CODOL_NETCHAN_FRAGMENT_BIT));
    chan->outgoing_sequence++;
    if (chan->sock == 0) codol_msg_write_short(&m, chan->qport);
    codol_msg_write_long(&m, chan->unsent_fragment_start);
    codol_msg_write_short(&m, fragment_length);
    codol_msg_write_data(&m, chan->unsent_buffer + chan->unsent_fragment_start, fragment_length);
    if (m.overflowed) return 0;

    send(ctx, &chan->remote_address, pkt, m.cursize);

    chan->unsent_fragment_start += fragment_length;
    if (chan->unsent_fragment_start >= chan->unsent_length) {
        chan->unsent_fragments = 0;
        return 0;
    }
    return 1;
}

static uint32_t le32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static void put_le32(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)v;         p[1] = (uint8_t)(v >> 8);
    p[2] = (uint8_t)(v >> 16); p[3] = (uint8_t)(v >> 24);
}

void codol_fat_reset(codol_fat_reassembler_t *r)
{
    if (!r) return;
    r->sequence = 0;
    r->stride = 0;
    r->last_index = 0;
    r->in_use = 0;
    r->received_bytes = 0;
    memset(r->received_bits, 0, sizeof(r->received_bits));
}

/* 收一片 CODOL 客户端分片帧。布局见 codol_types.h 的 CODOL_FAT_* 常量块。
 * 返回值语义见 codol_netchan.h。 */
int codol_fat_receive(codol_fat_reassembler_t *r, const uint8_t *pkt, int len,
                      uint8_t *ctl, int ctl_cap, int *ctl_len)
{
    uint32_t raw, seq, start, i;
    bool reliable, ackflag;
    uint8_t idx, last;
    uint16_t stride, flen;

    if (ctl_len) *ctl_len = 0;
    if (!r || !pkt || len < CODOL_FAT_HDR) return -1;

    raw = le32(pkt);
    if (!(raw & CODOL_FAT_BIT)) return -1;              /* 不是分片帧 */
    seq      = raw & CODOL_FAT_SEQ_MASK;
    reliable = (raw & CODOL_FAT_RELIABLE_BIT) != 0;
    ackflag  = (raw & CODOL_FAT_ACK_BIT) != 0;

    /* 客户端发来的"分片确认包": 我们从不请求分片确认, 记下即可 */
    if (ackflag) return -1;

    idx    = pkt[4];
    last   = pkt[5];
    stride = (uint16_t)(pkt[6] | (pkt[7] << 8));
    flen   = (uint16_t)(pkt[8] | (pkt[9] << 8));

    /* 边界校验(照参照实现): 序号非 0; index <= last; last 在上限内;
     * 步长必须是固定值; 本片长度不得超过步长; 帧里必须有这么多字节;
     * 非末片必须是满步长。 */
    if (seq == 0 || idx > last || last >= CODOL_FAT_MAX_FRAGMENTS ||
        stride != CODOL_FAT_STRIDE || flen > stride ||
        len < CODOL_FAT_HDR + (int)flen ||
        (idx != last && flen != stride))
        return -1;

    if (r->sequence != seq) {
        /* 更旧的消息: 丢弃(重连造成的序号回退由 codol_fat_reset() 处理) */
        if (r->sequence != 0 && seq < r->sequence) return -1;
        r->sequence = seq;
        r->stride = stride;
        r->last_index = last;
        r->in_use = 1;
        r->received_bytes = 0;
        memset(r->received_bits, 0, sizeof(r->received_bits));
        put_le32(r->buffer, seq);
    } else if (r->last_index != last || r->stride != stride) {
        return -1;                       /* 同一序号却换了分片参数 */
    }

    /* 重复片: 已收过 —— 安全忽略 */
    if (r->received_bits[idx >> 5] & (1u << (idx & 31))) return 0;

    start = (uint32_t)idx * (uint32_t)stride;
    if (start + flen > CODOL_FAT_MAX_MESSAGE) return -1;
    memcpy(r->buffer + 4 + start, pkt + CODOL_FAT_HDR, (size_t)flen);
    r->received_bits[idx >> 5] |= (1u << (idx & 31));
    r->received_bytes += flen;

    /* 带 RELIABLE 位 -> 回一条分片确认(实测不触发, 保留以对齐引擎行为) */
    if (reliable && ctl && ctl_cap >= CODOL_FAT_HDR + 16) {
        put_le32(ctl, seq | CODOL_FAT_BIT | CODOL_FAT_ACK_BIT);
        ctl[4] = idx;
        ctl[5] = last;
        ctl[6] = (uint8_t)stride; ctl[7] = (uint8_t)(stride >> 8);
        ctl[8] = (uint8_t)flen;   ctl[9] = (uint8_t)(flen >> 8);
        for (i = 0; i < 4; i++)
            put_le32(ctl + CODOL_FAT_HDR + i * 4, r->received_bits[i]);
        if (ctl_len) *ctl_len = CODOL_FAT_HDR + 16;
    }

    /* 全部片都到齐了吗 */
    for (i = 0; i <= (uint32_t)last; i++)
        if (!(r->received_bits[i >> 5] & (1u << (i & 31)))) return 0;

    /* 收全: buffer[0 .. 4+received_bytes) 即整条消息 */
    {
        int total = (int)(4 + r->received_bytes);
        codol_fat_reset(r);
        return total;
    }
}

bool codol_netchan_process(codol_netchan_t *chan, codol_msg_t *msg)
{
    int sequence;

    if (!chan || !msg || !msg->data) return false;
    if (msg->cursize < 4) return false;

    /* ---- CODOL 3.19 分片帧: 10 字节头, **不含 qport** ----
     * 收全后 msg 指向重组好的整条消息(u32 序号 ‖ 载荷), 与普通帧
     * 同样从"序号"开始, 所以这里统一消费掉序号再交给上层。 */
    if (le32(msg->data) & CODOL_FAT_BIT) {
        int n = codol_fat_receive(&chan->fat, msg->data, msg->cursize, NULL, 0, NULL);
        if (n <= 0) return false;                 /* 还需等待 / 无效 */
        codol_msg_init_readonly(msg, chan->fat.buffer, n);
        codol_msg_begin_reading(msg);
        (void)codol_msg_read_long(msg);           /* 跳过序号, 定位到载荷 */
        return true;
    }

    codol_msg_begin_reading(msg);
    sequence = codol_msg_read_long(msg);

    /* 服务端要弹掉客户端带的 qport */
    if (chan->sock == 1) codol_msg_read_short(msg);

    /* 乱序/重包: 直接丢弃 */
    if (sequence <= chan->incoming_sequence) return false;

    if (msg->overflowed) return false;

    chan->dropped = sequence - (chan->incoming_sequence + 1);
    chan->incoming_sequence = sequence;
    return true;
}
