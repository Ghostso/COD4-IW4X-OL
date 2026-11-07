/* netchan: 线头布局 / 往返 / 乱序丢弃 / 分片 */
#include "codol_netchan.h"
#include <stdio.h>
#include <string.h>

static int fails;
static uint8_t last_pkt[2048];
static int     last_len;
static int     send_count;

static int fake_send(void *ctx, const codol_netadr_t *to, const uint8_t *d, int n)
{
    (void)ctx; (void)to;
    memcpy(last_pkt, d, (size_t)n); last_len = n; send_count++;
    return 1;
}

/* ---- CODOL 3.19 分片(FAT)重组 -------------------------------------------
 * 布局: u32(序号|标志) | u8 idx | u8 last | u16 stride | u16 frag_len | 负载
 * 重组结果 = u32(序号) ‖ 各片负载(index*stride 定位), 即普通帧那条消息。 */
static int build_fat(uint8_t *out, uint32_t seq, uint8_t idx, uint8_t last,
                     uint16_t stride, const uint8_t *payload, uint16_t flen,
                     uint32_t flags)
{
    uint32_t v = (seq & CODOL_FAT_SEQ_MASK) | CODOL_FAT_BIT | flags;
    out[0] = (uint8_t)v;         out[1] = (uint8_t)(v >> 8);
    out[2] = (uint8_t)(v >> 16); out[3] = (uint8_t)(v >> 24);
    out[4] = idx; out[5] = last;
    out[6] = (uint8_t)stride;  out[7] = (uint8_t)(stride >> 8);
    out[8] = (uint8_t)flen;    out[9] = (uint8_t)(flen >> 8);
    memcpy(out + CODOL_FAT_HDR, payload, flen);
    return CODOL_FAT_HDR + (int)flen;
}

/* 把 post-seq 负载切成分片帧并逐片交给重组器; 返回收到第一片时的索引 */
static int feed_fat(codol_fat_reassembler_t *r, uint32_t seq, const uint8_t *body,
                    int bodylen, const int *order, int nfrag, int *last_rc)
{
    uint8_t frame[CODOL_FAT_HDR + 2048];
    int total = (bodylen + CODOL_FAT_STRIDE - 1) / CODOL_FAT_STRIDE;
    int i, rc = 0;
    if (total < 1) total = 1;
    for (i = 0; i < nfrag; i++) {
        int idx = order[i], off = idx * CODOL_FAT_STRIDE;
        int len = bodylen - off; if (len > CODOL_FAT_STRIDE) len = CODOL_FAT_STRIDE;
        int n = build_fat(frame, seq, (uint8_t)idx, (uint8_t)(total - 1),
                          CODOL_FAT_STRIDE, body + off, (uint16_t)len, 0);
        rc = codol_fat_receive(r, frame, n, NULL, 0, NULL);
    }
    if (last_rc) *last_rc = rc;
    return total;
}

static void test_fat(void)
{
    codol_fat_reassembler_t r;
    uint8_t body[3000], msg[3004], frame[CODOL_FAT_HDR + 2048];
    int i, n, rc = 0, total, order[8];
    const uint32_t seq = 100;

    for (i = 0; i < 3000; i++) body[i] = (uint8_t)(i * 7 + 3);
    msg[0] = (uint8_t)seq; msg[1] = 0; msg[2] = 0; msg[3] = 0;
    memcpy(msg + 4, body, 3000);

    total = (3000 + CODOL_FAT_STRIDE - 1) / CODOL_FAT_STRIDE;
    if (total != 3) { printf("FAIL FAT 分片数 %d want 3\n", total); fails++; }

    /* ① 顺序喂入 -> 重组必须逐字节一致 */
    memset(&r, 0, sizeof(r));
    for (i = 0; i < 8; i++) order[i] = i;
    feed_fat(&r, seq, body, 3000, order, total, &rc);
    if (rc != 3004) { printf("FAIL FAT 顺序重组 rc=%d want=3004\n", rc); fails++; }
    else if (memcmp(r.buffer, msg, 3004) != 0) { printf("FAIL FAT 顺序重组内容不符\n"); fails++; }
    else printf("ok   FAT 顺序     3000B -> %d 片 -> 3004B 逐字节一致\n", total);

    /* ② 乱序喂入(2,0,1) */
    memset(&r, 0, sizeof(r));
    order[0] = 2; order[1] = 0; order[2] = 1;
    feed_fat(&r, seq, body, 3000, order, 3, &rc);
    if (rc != 3004 || memcmp(r.buffer, msg, 3004) != 0) {
        printf("FAIL FAT 乱序重组 rc=%d\n", rc); fails++;
    } else printf("ok   FAT 乱序     (2,0,1) 仍逐字节一致\n");

    /* ③ 重复片: 第 0 片发两次, 第二次应被忽略而结果不变 */
    memset(&r, 0, sizeof(r));
    n = build_fat(frame, seq, 0, 2, CODOL_FAT_STRIDE, body, CODOL_FAT_STRIDE, 0);
    if (codol_fat_receive(&r, frame, n, NULL, 0, NULL) != 0) { printf("FAIL FAT 重复 首片应待续\n"); fails++; }
    if (codol_fat_receive(&r, frame, n, NULL, 0, NULL) != 0) { printf("FAIL FAT 重复片未被忽略\n"); fails++; }
    else {
        order[0] = 1; order[1] = 2;
        for (i = 0; i < 2; i++) {
            int idx = order[i], off = idx * CODOL_FAT_STRIDE;
            int len = 3000 - off; if (len > CODOL_FAT_STRIDE) len = CODOL_FAT_STRIDE;
            n = build_fat(frame, seq, (uint8_t)idx, 2, CODOL_FAT_STRIDE, body + off, (uint16_t)len, 0);
            rc = codol_fat_receive(&r, frame, n, NULL, 0, NULL);
        }
        if (rc != 3004 || memcmp(r.buffer, msg, 3004) != 0) {
            printf("FAIL FAT 重复片后重组 rc=%d\n", rc); fails++;
        } else printf("ok   FAT 重复片   重复片被忽略, 重组仍一致\n");
    }

    /* ④ 缺片: 只发 0 和 1, 永远不完成 */
    memset(&r, 0, sizeof(r));
    order[0] = 0; order[1] = 1;
    feed_fat(&r, seq, body, 3000, order, 2, &rc);
    if (rc != 0) { printf("FAIL FAT 缺片 应待续 rc=%d\n", rc); fails++; }
    else printf("ok   FAT 缺片     未收全 -> 返回 0(不误判完成)\n");

    /* ⑤ 边界: 步长不符 / 本片超长 / index>last -> 全部拒绝 */
    memset(&r, 0, sizeof(r));
    n = build_fat(frame, seq, 0, 1, 1000, body, 1000, 0);            /* 步长不是 1154 */
    if (codol_fat_receive(&r, frame, n, NULL, 0, NULL) >= 0) { printf("FAIL FAT 步长 未拒绝\n"); fails++; }
    n = build_fat(frame, seq, 0, 1, CODOL_FAT_STRIDE, body, CODOL_FAT_STRIDE, 0);
    if (codol_fat_receive(&r, frame, n - 1, NULL, 0, NULL) >= 0) { printf("FAIL FAT 截断 未拒绝\n"); fails++; }
    n = build_fat(frame, seq, 3, 1, CODOL_FAT_STRIDE, body, CODOL_FAT_STRIDE, 0);  /* idx>last */
    if (codol_fat_receive(&r, frame, n, NULL, 0, NULL) >= 0) { printf("FAIL FAT idx>last 未拒绝\n"); fails++; }
    n = build_fat(frame, seq, 0, 1, CODOL_FAT_STRIDE, body, 500, 0);  /* 非末片必须满步长 */
    if (codol_fat_receive(&r, frame, n, NULL, 0, NULL) >= 0) { printf("FAIL FAT 非末片短片 未拒绝\n"); fails++; }
    else printf("ok   FAT 边界     步长/截断/idx>last/非末片短片 全部拒绝\n");

    /* ⑥ 两条连续分片消息 */
    memset(&r, 0, sizeof(r));
    for (i = 0; i < 8; i++) order[i] = i;
    feed_fat(&r, seq, body, 3000, order, 3, &rc);
    {
        uint8_t body2[1300], msg2[1304];
        for (i = 0; i < 1300; i++) body2[i] = (uint8_t)(255 - (i & 0xFF));
        msg2[0] = (uint8_t)(seq + 1); msg2[1] = 0; msg2[2] = 0; msg2[3] = 0;
        memcpy(msg2 + 4, body2, 1300);
        feed_fat(&r, seq + 1, body2, 1300, order, 2, &rc);
        if (rc != 1304 || memcmp(r.buffer, msg2, 1304) != 0) {
            printf("FAIL FAT 连续第二条 rc=%d\n", rc); fails++;
        } else printf("ok   FAT 连续     第二条分片消息独立重组正确\n");
    }

    /* ⑦ 经 codol_netchan_process 交替喂: 普通帧 -> 分片帧 -> 普通帧 */
    {
        codol_netchan_t ch;
        codol_msg_t m;
        uint8_t pkt[64];
        codol_netchan_setup(&ch, 1, NULL, 0, NULL, 0, NULL, 0);
        /* 普通帧 (sock=1 => 带 qport): seq(4) | qport(2) | payload */
        pkt[0]=0; pkt[1]=0; pkt[2]=0; pkt[3]=0; pkt[4]=0x11; pkt[5]=0x22;
        memcpy(pkt+6, "ABCD", 4);
        codol_msg_init_readonly(&m, pkt, 10);
        if (!codol_netchan_process(&ch, &m)) { printf("FAIL FAT 普通帧 被拒\n"); fails++; }
        else {
            codol_msg_read_data(&m, (char *)frame, 4);
            if (memcmp(frame, "ABCD", 4) != 0) { printf("FAIL FAT 普通帧 载荷\n"); fails++; }
        }
        /* 分片帧 seq=1: 经 process 收全后应定位在负载 */
        for (i = 0; i < 3; i++) {
            int off = i * CODOL_FAT_STRIDE;
            int len = 3000 - off; if (len > CODOL_FAT_STRIDE) len = CODOL_FAT_STRIDE;
            n = build_fat(frame, 1, (uint8_t)i, 2, CODOL_FAT_STRIDE, body + off, (uint16_t)len, 0);
            codol_msg_init_readonly(&m, frame, n);
            if (!codol_netchan_process(&ch, &m)) {
                if (i < 2) continue;                       /* 前两片应待续 */
                printf("FAIL FAT process 末片未完成\n"); fails++; break;
            }
            if (i < 2) { printf("FAIL FAT process 第%d片过早完成\n", i); fails++; break; }
            {
                uint8_t *p = m.data + m.readcount;         /* readcount 已跳过序号 */
                if (memcmp(p, body, 3000) != 0) { printf("FAIL FAT process 重组载荷\n"); fails++; }
                else printf("ok   FAT process  普通帧/分片帧交替, 重组载荷正确\n");
            }
        }
    }
}

int main(void)
{
    codol_netchan_t tx, rx;
    codol_netadr_t adr;
    uint8_t unsent[8192], frag[8192];
    uint8_t payload[8] = { 0xDE,0xAD,0xBE,0xEF,0x01,0x02,0x03,0x04 };
    codol_msg_t m;
    char got[64];
    int i;

    memset(&adr, 0, sizeof(adr));
    adr.type = 1; adr.port = 28960; adr.ip[0] = 127; adr.ip[3] = 1;

    codol_netchan_setup(&tx, 0, &adr, 0x1234, unsent, sizeof(unsent), frag, sizeof(frag));
    codol_netchan_setup(&rx, 1, &adr, 0, unsent, sizeof(unsent), frag, sizeof(frag));

    send_count = 0;
    codol_netchan_transmit(&tx, (int)sizeof(payload), payload, fake_send, NULL);
    if (send_count != 1) { printf("FAIL transmit 未发送\n"); fails++; }

    /* 头: uint32 sequence(MSB-first) 紧接载荷；服务端发送不含 qport */
    if (last_len != 6 + (int)sizeof(payload)) {
        printf("FAIL 头长度 got=%d want=%d\n", last_len, 6 + (int)sizeof(payload)); fails++;
    } else if (!(last_pkt[0]==0 && last_pkt[1]==0 && last_pkt[2]==0 && last_pkt[3]==0)) {
        printf("FAIL sequence 应为 0: %02x %02x %02x %02x\n", last_pkt[0],last_pkt[1],last_pkt[2],last_pkt[3]); fails++;
    } else if (memcmp(last_pkt + 6, payload, sizeof(payload)) != 0) {
        printf("FAIL 载荷不符\n"); fails++;
    } else printf("ok   线头+载荷  seq=0, %d B\n", last_len);

    /* 往返: 收到的 msg 应定位在载荷 */
    codol_msg_init_readonly(&m, last_pkt, last_len);
    if (!codol_netchan_process(&rx, &m)) { printf("FAIL process 拒绝\n"); fails++; }
    else {
        codol_msg_read_data(&m, got, (int)sizeof(payload));
        if (memcmp(got, payload, sizeof(payload)) != 0) { printf("FAIL 往返载荷\n"); fails++; }
        else printf("ok   往返      载荷一致\n");
    }

    /* 乱序/重包: 同一个包再来一次应被丢弃 */
    codol_msg_init_readonly(&m, last_pkt, last_len);
    if (codol_netchan_process(&rx, &m)) { printf("FAIL 重包未被丢弃\n"); fails++; }
    else printf("ok   重包丢弃  sequence<=incoming 已丢\n");

    /* 第二个包 seq=1 应被接受 */
    codol_netchan_transmit(&tx, (int)sizeof(payload), payload, fake_send, NULL);
    codol_msg_init_readonly(&m, last_pkt, last_len);
    if (!codol_netchan_process(&rx, &m)) { printf("FAIL seq=1 被拒\n"); fails++; }
    else printf("ok   递增接受  seq=1 通过\n");

    /* 分片: 发 3000B */
    {
        uint8_t big[3000];
        for (i = 0; i < 3000; i++) big[i] = (uint8_t)(i * 7);
        codol_netchan_setup(&tx, 0, &adr, 0x1234, unsent, sizeof(unsent), frag, sizeof(frag));
        codol_netchan_setup(&rx, 1, &adr, 0, unsent, sizeof(unsent), frag, sizeof(frag));
        tx.outgoing_sequence = 0; tx.incoming_sequence = -1; rx.incoming_sequence = -1;
        send_count = 0;
        codol_netchan_transmit(&tx, 3000, big, fake_send, NULL);
        printf("ok   分片       首片 %d B, 已发 %d 片\n", last_len, send_count);
        while (tx.unsent_fragments) codol_netchan_transmit_next_fragment(&tx, fake_send, NULL);
        printf("ok   分片       共发出 %d 片\n", send_count);
    }

    printf("\n--- CODOL 3.19 分片(FAT)重组 ---\n");
    test_fat();

    printf("\n%s (%d)\n", fails ? "FAILED" : "ALL PASSED", fails);
    return fails ? 1 : 0;
}
