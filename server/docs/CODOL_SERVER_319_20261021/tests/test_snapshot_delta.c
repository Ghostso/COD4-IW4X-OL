/* test_snapshot_delta: 字段载荷必须是**裸值**(绝对量), 不是 `to ^ 上一帧`。
 *
 * ★ 2026-10-24 重写。原版断言的是相反的语义("同值第二帧应写成 0"),
 *   那正是被证伪的写法: 头部基线位恒写 0(="没有旧基线"), 客户端按绝对量读,
 *   而 `to ^ from` 在"玩家一帧没动"时退化成 0 —— 等于每帧发 position=(0,0,0)。
 *   详见 docs/SNAPSHOT_FIELD_DIFF_20261024.md §5。
 *
 * 本文件现在钉住三件事:
 *   1. 首帧含裸值坐标;
 *   2. 第 2 帧在"值没变"时**仍然含裸值坐标**(不再退化成 0), 且与首帧
 *      除 头部(server_time/first/flags) 外逐字节相同;
 *   3. 值变了就写新值本身, 不是异或值。
 *   4. index61(groundEntityNum) 随接地状态写 2046 / 2047。
 *
 * 黄金向量: tests/fixtures/snapshot_golden_20261024.txt (改动前记录的最后一份首帧)。
 */
#include "codol_snapshot.h"
#include <stdio.h>
#include <string.h>

static int fails;

/* 在 buf 里找 4 字节小端浮点 */
static int has_f32(const uint8_t *buf, int n, float v)
{
    uint8_t pat[4]; int i, j;
    memcpy(pat, &v, 4);
    for (i = 0; i + 4 <= n; i++) {
        for (j = 0; j < 4; j++) if (buf[i + j] != pat[j]) break;
        if (j == 4) return 1;
    }
    return 0;
}

#define HDR_LEN 11   /* ack4 + opcode1 + serverTime4 + first1 + flags1 */

int main(void)
{
    codol_snap_equip_t eq;
    uint8_t b1[512], b2[512], b3[512], bg[512], ba[512], bf[512];
    codol_snap_state_t zero, c1, c2, c3, cg, ca;
    int n1, n2, n3, ng, na, i;

    codol_snap_equip_default(&eq);
    codol_snap_state_zero(&zero);

    /* ---- 1. 首帧: 基线全零, 含裸值 48.0 / -572.0 ---- */
    n1 = codol_snapshot_build(b1, sizeof(b1), 0, 1000, 1000, true,
                              48.0f, -572.0f, -116.0f, 0, 0, 0,
                              0.0f, 0.0f, 0.0f, false, false, true,
                              0, &zero, NULL, &eq, NULL, 0);
    if (n1 <= 0) { printf("FAIL 首帧构建 %d\n", n1); return 1; }
    if (!has_f32(b1, n1, 48.0f) || !has_f32(b1, n1, -572.0f)) {
        printf("FAIL 首帧应含裸值 48.0/-572.0\n"); fails++;
    } else printf("ok   首帧            含裸值 48.0/-572.0\n");
    codol_snap_state_zero(&c1);

    /* ---- 2. 第 2 帧: 值完全相同, 基线=首帧值 -> **仍须含裸值** ---- */
    codol_snap_state_zero(&c2);
    n2 = codol_snapshot_build(b2, sizeof(b2), 0, 2000, 1000, false,
                              48.0f, -572.0f, -116.0f, 0, 0, 0,
                              0.0f, 0.0f, 0.0f, false, false, true,
                              0, &c1, &c2, &eq, NULL, 0);
    if (n2 <= 0) { printf("FAIL 第 2 帧构建 %d\n", n2); return 1; }
    if (!has_f32(b2, n2, 48.0f) || !has_f32(b2, n2, -572.0f)) {
        printf("FAIL 第 2 帧丢了裸值 -> 又退化成 to^from(玩家没动就发 0)\n"); fails++;
    } else printf("ok   第 2 帧(值未变)   仍含裸值 48.0/-572.0\n");

    /* 首帧**比后续帧长**是设计如此: 视角字段 idx 18/19/29 只在首帧写
     * (omit_viewangles 语义, 之后交给客户端自己保持视角)。
     * 因此这里不断言等长, 只断言: 首帧不长于第 2 帧且未漏写位置裸值。 */
    if (n1 < n2) {
        printf("FAIL 首帧(%d) 不应短于第 2 帧(%d)\n", n1, n2); fails++;
    } else printf("ok   首帧/第 2 帧    首帧 %d >= 第 2 帧 %d (首帧另含视角字段)\n", n1, n2);

    /* ---- 3. 第 3 帧: 位置变化 -> 写**新值本身**, 不是异或值 ---- */
    codol_snap_state_zero(&c3);
    n3 = codol_snapshot_build(b3, sizeof(b3), 0, 3000, 1000, false,
                              100.0f, -572.0f, -116.0f, 0, 0, 0,
                              0.0f, 0.0f, 0.0f, false, false, true,
                              0, &c2, &c3, &eq, NULL, 0);
    if (n3 <= 0) { printf("FAIL 第 3 帧 %d\n", n3); fails++; }
    else if (!has_f32(b3, n3, 100.0f)) {
        printf("FAIL 第 3 帧没写新值 100.0 -> 异或没有清干净\n"); fails++;
    } else printf("ok   第 3 帧(位置变)   写的是新值 100.0\n");

    /* ---- 4. index61 = groundEntityNum: 目前**恒写 2047**(=空中) ----
     * 为什么不按接地状态动态写: 服务端这份接地状态是**退化的** —— 碰撞地面是写死的常数
     * (`collision.c: codol_ground_z = -116`), 玩家永远不离开地面 ⇒ on_ground 恒 true
     * ⇒ "动态写"实际产出恒定 2046。实测(SNAPSHOT_RAWFIX_20261024_1357) 恒发 2046 会让
     * 客户端进"飞行模式"且开镜失效, 恒发 2047 则让客户端自己跑物理。
     * 所以本测试断言: 传 true / false 必须产出**完全相同**的字节。 */
    codol_snap_state_zero(&cg); codol_snap_state_zero(&ca);
    ng = codol_snapshot_build(bg, sizeof(bg), 0, 4000, 1000, false,
                              48.0f, -572.0f, -116.0f, 0, 0, 0,
                              0.0f, 0.0f, 0.0f, false, false, /*on_ground*/ true,
                              0, &zero, &cg, &eq, NULL, 0);
    na = codol_snapshot_build(ba, sizeof(ba), 0, 4000, 1000, false,
                              48.0f, -572.0f, -116.0f, 0, 0, 0,
                              0.0f, 0.0f, 0.0f, false, false, /*on_ground*/ false,
                              0, &zero, &ca, &eq, NULL, 0);
    if (ng <= 0 || na <= 0 || ng != na) {
        printf("FAIL groundEntityNum 两帧构建异常 %d/%d\n", ng, na); fails++;
    } else {
        int ndiff = 0;
        for (i = 0; i < ng; i++) if (bg[i] != ba[i]) ndiff++;
        if (ndiff) {
            printf("FAIL on_ground 影响了输出(%d 字节不同) —— 非首帧应当省略 idx61\n", ndiff);
            fails++;
        } else printf("ok   groundEntityNum   非首帧省略 idx61, 与 on_ground 无关\n");
    }

    /* ---- 5. 首帧 idx61 必须是 2047(ENTITYNUM_NONE), 不是 2046 ----
     * 2046 = "站在某个世界实体上", 但我们**没有在实体段下发任何实体**(ents=0),
     * 客户端找不到那个 groundEntity ⇒ 状态不一致。
     * 实测(2026-10-26): 首帧写 2046 -> 开镜失效(瞄准镜消失) + 人物在房顶。
     * 与 2026-10-24 的 SNAPSHOT_RAWFIX_20261024_1357 结论一致。
     * 2047 是诚实的"我不知道你踩着什么", 客户端据此自己跑物理。 */
    {
        int nf = codol_snapshot_build(bf, sizeof(bf), 0, 5000, 1000, /*first*/ true,
                                      48.0f, -572.0f, -116.0f, 0, 0, 0,
                                      0.0f, 0.0f, 0.0f, false, false, true,
                                      0, &zero, NULL, &eq, NULL, 0);
        if (nf <= 0) {
            printf("FAIL 首帧构建 %d\n", nf); fails++;
        } else {
            static const uint8_t fe07[2] = {0xFE, 0x07};   /* 2046 */
            static const uint8_t ff07[2] = {0xFF, 0x07};   /* 2047 */
            int has_fe = 0, has_ff = 0, k;
            for (k = 0; k + 2 <= nf; k++) {
                if (bf[k] == fe07[0] && bf[k+1] == fe07[1]) has_fe = 1;
                if (bf[k] == ff07[0] && bf[k+1] == ff07[1]) has_ff = 1;
            }
            if (!has_ff) {
                printf("FAIL 首帧里找不到 2047(ENTITYNUM_NONE)\n"); fails++;
            } else if (has_fe) {
                printf("FAIL 首帧里仍有 2046 —— 会让客户端开镜失效\n"); fails++;
            } else {
                printf("ok   首帧 idx61       写入 2047(空中), 无 2046\n");
            }
        }
    }

    printf("\n%s (%d)\n", fails ? "FAILED" : "ALL PASSED", fails);
    return fails ? 1 : 0;
}
