/* battle 外层: NAT / init / 密钥交换 / 数据帧 —— 以"客户端视角"验证 */
#include "codol_battle.h"
#include "codol_crypto.h"
#include "battle_real_packets.inc"   /* 实机报文回放 fixture(_gen_test_fixture.py 生成) */
#include <stdio.h>
#include <string.h>

static int fails;
static void wr16(uint8_t *p, uint16_t v) { p[0]=(uint8_t)v; p[1]=(uint8_t)(v>>8); }
static void wr64(uint8_t *p, uint64_t v) { int i; for (i=0;i<8;i++) p[i]=(uint8_t)(v>>(i*8)); }
static uint16_t rd16(const uint8_t *p) { return (uint16_t)(p[0] | (p[1]<<8)); }
static uint64_t t_rd64(const uint8_t *p) {   /* battle.c 的 rd64 是 static, 测试里自备一个 */
    uint64_t v = 0; int i;
    for (i = 7; i >= 0; i--) v = (v << 8) | p[i];
    return v;
}

static uint8_t ckey[24];   /* 客户端侧传输密钥(由客户端私钥 + 服务端公钥派生) */

int main(void)
{
    codol_battle_t b;
    codol_netadr_t peer;
    uint8_t out[512];
    int n;

    memset(&peer, 0, sizeof(peer));
    peer.type = 1; peer.port = 22011;
    peer.ip[0] = 127; peer.ip[1] = 0; peer.ip[2] = 0; peer.ip[3] = 1;

    codol_battle_init(&b);

    /* ① NAT */
    {
        uint8_t nat[29];
        memset(nat, 0, sizeof(nat));
        nat[0] = 13; nat[1] = 2; nat[2] = 0;
        nat[23]=127; nat[24]=0; nat[25]=0; nat[26]=1; nat[27]=0x20; nat[28]=0x71;
        n = codol_battle_try_nat_reply(&b, &peer, nat, 29, out, sizeof(out));
        if (n == 29 && out[0] == 12) printf("ok   NAT          29B -> type 12\n");
        else { printf("FAIL NAT n=%d out0=%d\n", n, out[0]); fails++; }
    }

    /* ② DTLS init */
    {
        uint8_t init[16];
        memset(init, 0, sizeof(init));
        init[0] = 1; init[1] = 2;
        wr16(init + 6, 0x1234);
        /* ★ 2026-11-05 回归: [8..16] 是**大厅下发的 u64 会话 id**, 不是常量 1。
         *   实测真机 = 0x1122334455667788(我们大厅 createSession 回的那个值)。
         *   样例里写 1 正好把这个 bug 藏了整轮 —— 所以这里特意用非 1 值。 */
        wr64(init + 8, 0x1122334455667788ULL);
        n = codol_battle_try_init_ack(&b, &peer, init, 16, out, sizeof(out));
        if (n != 38) { printf("FAIL init n=%d\n", n); fails++; }
        else if (out[0]!=2 || out[1]!=2 || rd16(out+2)!=0x1234 || rd16(out+14)==0
                 || t_rd64(out+30)!=0x1122334455667788ULL) {
            printf("FAIL init 布局 (cookie[30..38]=%llX, 应回填会话 id)\n",
                   (unsigned long long)t_rd64(out+30)); fails++;
        } else printf("ok   DTLS init    16B -> 38B cookie (client_tag=0x1234 server_tag=0x%04X sid=0x%llX)\n",
                      rd16(out+14), (unsigned long long)t_rd64(out + 30));
    }

    /* ②b 真机报文回放(离线静态测试) —— 字节逐个来自实机 RX 取证
     *    ONCE_20261105_141735\kit\_battle_out.txt:
     *      [battle] RX 16B 01020000000054CC8877665544332211
     *    这条 init 在修 bug 之前被 `rd64(pkt+8) != 1` 判掉, 客户端因此重试了几十次。
     *    以后改战斗服只要跑本测试, 不必再开游戏。 */
    {
        static const uint8_t real_init[16] = {
            0x01,0x02, 0x00,0x00, 0x00,0x00, 0x54,0xCC,
            0x88,0x77,0x66,0x55,0x44,0x33,0x22,0x11 };
        n = codol_battle_try_init_ack(&b, &peer, real_init, 16, out, sizeof(out));
        if (n != 38 || rd16(out+2) != 0xCC54
            || t_rd64(out+30) != 0x1122334455667788ULL) {
            printf("FAIL 真机 init 回放 n=%d tag=%04X sid=%llX\n", n, rd16(out+2),
                   (unsigned long long)t_rd64(out+30)); fails++;
        } else printf("ok   真机 init 回放 01020000000054CC8877665544332211 -> 38B cookie "
                      "(tag=0xCC54 sid 原样回填)\n");
    }

    /* ③ 密钥交换（客户端侧自建密钥对） */
    {
        uint8_t cookie[38], kx[219], ack[114];
        uint8_t cpriv[28], shared[28];
        codol_p224_point_t cpub, spub;

        memcpy(cookie, out, 38);
        codol_p224_gen_keypair(cpriv, &cpub);

        memset(kx, 0, sizeof(kx));
        kx[0] = 3; kx[1] = 2;
        wr16(kx + 2, rd16(cookie + 14));      /* 客户端回显 server_tag */
        memcpy(kx + 6, cookie, 38);
        wr64(kx + 111, 0x1122334455667788ULL);
        codol_p224_export_pubkey(&cpub, kx + 119);

        n = codol_battle_try_key_exchange_ack(&b, &peer, kx, 219, ack, sizeof(ack));
        if (n != 114) { printf("FAIL keyex n=%d\n", n); fails++; }
        /* ★ 2026-11-06 实机纠正: 记录尾 8B([106..114]) = **会话在 引擎+0x170 的键**。
         *   外层 type-4 分支 0xBB429D 以 push 1 打开名字过滤, 并把尾 8B 作为过滤器
         *   传给 0xBB1CB0; 后者用 0xB74090 与 引擎+0x170 条目的 8 字节键比较, 不匹配
         *   就直接跳过 ⇒ ACK 在进入校验前被丢弃。键空间 = 会话 id。 */
        else if (ack[0]!=4 || ack[1]!=2 || t_rd64(ack+106) != 0x1122334455667788ULL) {
            printf("FAIL keyex 布局 (尾 8B=%llX, 应=会话 id 1122334455667788)\n",
                   (unsigned long long)t_rd64(ack + 106)); fails++;
        }
        else {
            codol_battle_assoc_t *a = codol_battle_find(&b, &peer);
            codol_p224_import_pubkey(ack + 6, &spub);
            codol_p224_ecdh(cpriv, &spub, shared);
            codol_derive_transport_key(shared, b.security_key, ckey);
            if (!a || !a->key_ready) { printf("FAIL 会话未就绪\n"); fails++; }
            else if (memcmp(ckey, a->transport_key, 24) != 0) {
                printf("FAIL 双方传输密钥不一致\n"); fails++;
            } else printf("ok   密钥交换    219B -> 114B, 双方传输密钥一致 %02x%02x...\n",
                          ckey[0], ckey[1]);
            /* ★ 离线核对: 把服务端公钥(100B)打出来, 由外部脚本验它是否真在 P-224 曲线上
             *   —— 自测只验"两边一致", 验不出"点根本不在曲线上"(客户端会因此拒收 ACK)。 */
            {
                int j;
                printf("     SERVER_PUBKEY_HEX ");
                for (j = 0; j < 100; j++) printf("%02x", ack[6 + j]);
                printf("\n");
            }
        }
    }

    /* ④ 数据帧: 出站/入站 双向, 都用**客户端侧**密钥独立验证 */
    {
        codol_battle_assoc_t *a = codol_battle_find(&b, &peer);
        const char *msg = "hello-codol";
        uint8_t frame[128], plain[128], auth[64], seed[6], mac[20];
        int flen, plen;

        /* ④a 出站: 服务端 send_data -> 帧内 tag 必须是**接收方(client_tag)** */
        flen = codol_battle_send_data(a, (const uint8_t *)msg, 11, frame, sizeof(frame));
        if (flen != 16 + 11) { printf("FAIL 帧长度 %d\n", flen); fails++; }
        else if (frame[0]!=6 || frame[1]!=2 || frame[2]!=a->cookie[2] || frame[3]!=a->cookie[3]) {
            printf("FAIL 出站帧头: tag 应为接收方 client_tag %02X%02X\n", a->cookie[2], a->cookie[3]); fails++;
        } else if (rd16(frame + 14) != 11) { printf("FAIL 长度域 %u\n", rd16(frame+14)); fails++; }
        else {
            uint16_t seq = rd16(frame + 4);
            memcpy(auth, frame, 6);
            memcpy(auth + 6, frame + 14, 2 + 11);
            codol_hmac_sha1(ckey, 24, auth, 6 + 2 + 11, mac);
            if (memcmp(mac, frame + 6, 8) != 0) { printf("FAIL 出站 HMAC(客户端侧)不符\n"); fails++; }
            else {
                seed[0]=(uint8_t)(seq&0xFF); seed[1]=(uint8_t)(seq>>8); seed[2]=0; seed[3]=0;
                seed[4]=frame[2]; seed[5]=frame[3];
                codol_keystream_xor(ckey, seed, frame + 16, 11, plain);
                if (memcmp(plain, msg, 11) != 0) { printf("FAIL 出站明文字节不符\n"); fails++; }
                else printf("ok   数据帧(出站) 服务端加密 -> 客户端侧 HMAC/解密一致\n");
            }
        }

        /* ④b 入站: 按客户端口径构造帧, 帧内 tag = **接收方(server_tag)** */
        {
            uint16_t seq = 7;
            uint8_t cmsg[11];
            memcpy(cmsg, msg, 11);
            memset(frame, 0, sizeof(frame));
            frame[0]=6; frame[1]=2;
            frame[2]=a->cookie[14]; frame[3]=a->cookie[15];
            wr16(frame + 4, seq);
            wr16(frame + 14, 11);
            seed[0]=(uint8_t)(seq&0xFF); seed[1]=(uint8_t)(seq>>8); seed[2]=0; seed[3]=0;
            seed[4]=frame[2]; seed[5]=frame[3];
            codol_keystream_xor(ckey, seed, cmsg, 11, frame + 16);
            memcpy(auth, frame, 6);
            memcpy(auth + 6, frame + 14, 2 + 11);
            codol_hmac_sha1(ckey, 24, auth, 6 + 2 + 11, mac);
            memcpy(frame + 6, mac, 8);

            plen = codol_battle_read_data(a, frame, 27, plain, sizeof(plain));
            if (plen != 11) { printf("FAIL 入站解密长度 %d\n", plen); fails++; }
            else if (memcmp(plain, msg, 11) != 0) { printf("FAIL 入站明文不符\n"); fails++; }
            else printf("ok   数据帧(入站) 客户端帧 -> 服务端 HMAC/解密一致\n");
            frame[16] ^= 0x01;
            if (codol_battle_read_data(a, frame, 27, plain, sizeof(plain)) != -1) {
                printf("FAIL 入站篡改未被拒绝\n"); fails++;
            } else printf("ok   数据帧(入站) MAC 校验拒绝篡改\n");
        }

        /* ④c 序号越过 65536 回绕: seed 必须带高 16 位
         *   客户端 0xBC2C60 用 0xC74840 从线上 16 位重建 32 位, 再把 4 字节整体写进 seed。
         *   服务端若只写低 16 位, 回绕后两端密钥流错位 —— 这是本轮修的缺陷 #3。 */
        {
            uint8_t f2[128], p2[128];
            uint32_t full = 0x00010000u;      /* 线上低 16 位 = 0, 高 16 位 = 1 */
            int fl;
            a->send_seq = full;
            fl = codol_battle_send_data(a, (const uint8_t *)msg, 11, f2, sizeof(f2));
            if (fl != 27 || rd16(f2 + 4) != 0) {
                printf("FAIL 回绕帧 长度/线上序号 (%d, seq=%u)\n", fl, rd16(f2 + 4)); fails++;
            } else {
                seed[0] = 0; seed[1] = 0;
                seed[2] = (uint8_t)((full >> 16) & 0xFF);
                seed[3] = (uint8_t)((full >> 24) & 0xFF);
                seed[4] = f2[2]; seed[5] = f2[3];
                codol_keystream_xor(ckey, seed, f2 + 16, 11, p2);
                if (memcmp(p2, msg, 11) != 0) {
                    printf("FAIL 回绕帧 seed 高 16 位缺失 (seq=0x%08X)\n", full); fails++;
                } else {
                    printf("ok   数据帧(回绕) seq=0x00010000 -> seed 带高 16 位, 客户端可解\n");
                }
            }
            a->send_seq = 0x00010001u;
        }

        /* ④d 明文上限 1256 —— 客户端 0xBBDC00 的 `cmp [len],0x4E8; jae -> -6` 不发送 */
        {
            static uint8_t big[1300], bigout[1400];
            int fl = codol_battle_send_data(a, big, 1300, bigout, sizeof(bigout));
            if (fl != 0) { printf("FAIL 超长明文未被拒绝 (返回 %d)\n", fl); fails++; }
            else printf("ok   明文上限     1300B 被拒绝(客户端硬上限 0x4E8=1256)\n");
        }

        /* ④e type-7 保活帧: 只推进收帧序号, 不改变连接状态 */
        {
            uint8_t ka[6];
            uint32_t before = a->recv_seq;
            ka[0] = 7; ka[1] = 2; ka[2] = 0; ka[3] = 0;
            wr16(ka + 4, (uint16_t)(before + 3));
            codol_battle_note_keepalive(a, ka, 6);
            if (a->recv_seq != before + 3) {
                printf("FAIL 保活序号未推进 (%u -> %u)\n", before, a->recv_seq); fails++;
            } else printf("ok   保活帧(入站) type-7 只推进收帧序号, 不报错\n");
        }
    }

    /* ⑥ 真机 219B 密钥交换**整条回放**(离线静态测试, 放在最后: 它会把传输密钥覆盖掉)
     *    字节逐字取自实机 RX 取证 ONCE_20261105_151237\kit\_battle_out.txt:
     *      [battle] RX 219B FULL 0302021400000202A507000089DD1C01...  (219 字节)
     *    回放前提: 服务端会话里的 cookie 必须与客户端回带的那一份**逐字节相同**
     *    (server_tag / 时间戳都是我们发的, 客户端只是原样回带), 所以先手工把
     *    取证里的 cookie 灌进 assoc, 再喂整条 219B。 */
    {
        uint8_t kx[219], ck[38];
        codol_battle_assoc_t *a = codol_battle_find(&b, &peer);
        int i, ok = 1;
        for (i = 0; i < 219; i++) { unsigned v = 0; sscanf(KX_REAL_HEX + 2 * i, "%2x", &v); kx[i] = (uint8_t)v; }
        for (i = 0; i < 38; i++) { unsigned v = 0; sscanf(COOKIE_REAL_HEX + 2 * i, "%2x", &v); ck[i] = (uint8_t)v; }
        if (!a) { printf("FAIL 219B 回放: 没有会话\n"); fails++; }
        else {
            uint16_t ctag, stag;
            memcpy(a->cookie, ck, 38);
            ctag = rd16(ck + 2);
            stag = rd16(ck + 14);
            a->client_tag = ctag;
            a->server_tag = stag;
            a->session_id = 0x1122334455667788ULL;
            a->key_ready = 0;
            n = codol_battle_try_key_exchange_ack(&b, &peer, kx, 219, out, sizeof(out));
            if (n != 114) { printf("FAIL 219B 回放 n=%d\n", n); fails++; ok = 0; }
            else if (out[0] != 4 || out[1] != 2
                     || out[2] != (uint8_t)(ctag & 0xFF) || out[3] != (uint8_t)(ctag >> 8)) {
                printf("FAIL 219B 回放 帧头 %02X%02X tag=%02X%02X (应回 client_tag %02X%02X)\n",
                       out[0], out[1], out[2], out[3], (uint8_t)(ctag & 0xFF), (uint8_t)(ctag >> 8));
                fails++; ok = 0;
            }
            /* ★ 2026-11-06 实机纠正: ACK 尾 8B = 会话 id（路由键），不是 "CoDOnlin"。 */
            else if (t_rd64(kx + 111) != 0x1122334455667788ULL) {
                printf("FAIL 回放前提: KX[111..119]=%llX 不是会话 id —— fixture 过期了\n",
                       (unsigned long long)t_rd64(kx + 111)); fails++; ok = 0;
            }
            else if (t_rd64(out + 106) != t_rd64(kx + 111)) {
                printf("FAIL 回放 ACK 尾 8B=%llX, 应等于 KX 里的会话 id %llX\n",
                       (unsigned long long)t_rd64(out + 106),
                       (unsigned long long)t_rd64(kx + 111)); fails++; ok = 0;
            }
            if (ok) printf("ok   真机 219B 回放 -> 114B ACK (client_tag=%04X server_tag=%04X "
                           "尾 8B=会话 id 0x1122334455667788 ✓)\n", ctag, stag);
        }
    }

    printf("\n%s (%d)\n", fails ? "FAILED" : "ALL PASSED", fails);
    return fails ? 1 : 0;
}
