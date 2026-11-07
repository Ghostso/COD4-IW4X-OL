/* 快照编码器离线探针 —— 复现服务端首帧参数, 再逐项扫描哪个量能造成字节差。
 * 目的: 定位 "上轮成功 105B / 本轮 103B" 到底由哪个输入或哪段代码决定。 */
#include "codol_snapshot.h"
#include "codol_equipment.h"
#include <stdio.h>
#include <string.h>

/* 与 battle_service.c send_snapshot() 的首帧调用逐参对应 */
static int build(const codol_snap_equip_t *eq, int omit, int first, int aiming,
                 float aim_fraction, int16_t pitch, int16_t yaw, int16_t roll,
                 uint32_t cmd_time, float afx, float afy, float afz,
                 float avx, float avy, codol_snap_state_t *from, codol_snap_state_t *cur)
{
    uint8_t buf[512];
    return codol_snapshot_build(buf, (int)sizeof buf, 0, 1000, cmd_time,
                                first ? true : false,
                                afx, afy, afz,
                                pitch, yaw, roll,
                                avx, avy, aim_fraction, aiming ? true : false,
                                omit ? true : false,
                                false, (uint16_t)0,
                                from, cur, eq, NULL, 0);
}

int main(void)
{
    codol_snap_equip_t eq;
    codol_snap_state_t from, cur;
    codol_equipment_t e;
    int n;

    codol_equipment_init(&e);
    codol_equipment_to_snapshot(&e, &eq);
    codol_snap_state_zero(&from);
    codol_snap_state_zero(&cur);

    printf("== equipment from codol_equipment_init() ==\n");
    printf("   slot_count=%d weapon=%d ammo=%d clip=%d reserve=%d cap=%d\n",
           eq.slot_count, eq.slots[0].weapon, eq.slots[0].ammo_key,
           eq.slots[0].clip, eq.slots[0].reserve, eq.slots[0].capacity);

    printf("\n== 服务端首帧参数(omit=1, first=1) ==\n");
    n = build(&eq, 1, 1, 0, 0.0f, 0, 0, 0, 0, 48.0f, -572.0f, -116.0f, 0.0f, 0.0f, &from, &cur);
    printf("   bytes = %d   (期望: 与日志 TX_SNAPSHOT seq=2 相同)\n", n);

    printf("\n== 单项扫描(改动一个量, 看字节数变化) ==\n");
    codol_snap_state_zero(&from); codol_snap_state_zero(&cur);
    printf("   omit=0               -> %d\n",
           build(&eq, 0, 1, 0, 0.0f, 0, 0, 0, 0, 48.0f, -572.0f, -116.0f, 0.0f, 0.0f, &from, &cur));
    codol_snap_state_zero(&from); codol_snap_state_zero(&cur);
    printf("   first=0              -> %d\n",
           build(&eq, 1, 0, 0, 0.0f, 0, 0, 0, 0, 48.0f, -572.0f, -116.0f, 0.0f, 0.0f, &from, &cur));
    codol_snap_state_zero(&from); codol_snap_state_zero(&cur);
    printf("   aiming=1             -> %d\n",
           build(&eq, 1, 1, 1, 0.0f, 0, 0, 0, 0, 48.0f, -572.0f, -116.0f, 0.0f, 0.0f, &from, &cur));
    codol_snap_state_zero(&from); codol_snap_state_zero(&cur);
    printf("   yaw=1000             -> %d\n",
           build(&eq, 1, 1, 0, 0.0f, 0, 1000, 0, 0, 48.0f, -572.0f, -116.0f, 0.0f, 0.0f, &from, &cur));
    codol_snap_state_zero(&from); codol_snap_state_zero(&cur);
    printf("   command_time=1000    -> %d\n",
           build(&eq, 1, 1, 0, 0.0f, 0, 0, 0, 1000, 48.0f, -572.0f, -116.0f, 0.0f, 0.0f, &from, &cur));

    /* 装备为空(用户观察到的"主武器是空的")会怎样 */
    {
        codol_snap_equip_t z;
        memset(&z, 0, sizeof z);
        codol_snap_state_zero(&from); codol_snap_state_zero(&cur);
        printf("   空装备(slot_count=0) -> %d\n",
               build(&z, 1, 1, 0, 0.0f, 0, 0, 0, 0, 48.0f, -572.0f, -116.0f, 0.0f, 0.0f, &from, &cur));
        codol_snap_state_zero(&from); codol_snap_state_zero(&cur);
        {
            codol_snap_equip_t t = eq;
            t.slots[0].weapon = 0;
            printf("   装备不空但 weapon=0   -> %d\n",
                   build(&t, 1, 1, 0, 0.0f, 0, 0, 0, 0, 48.0f, -572.0f, -116.0f, 0.0f, 0.0f, &from, &cur));
        }
    }

    /* 事件 0x19/0x1A 会跳过 11 位武器号 */
    {
        codol_snap_equip_t t = eq;
        codol_snap_state_zero(&from); codol_snap_state_zero(&cur);
        t.event_sequence = 4;
        t.events[0] = 0x19; t.events[1] = 0x24; t.events[2] = 0x24; t.events[3] = 0x24;
        printf("   events[0]=0x19       -> %d\n",
               build(&t, 1, 1, 0, 0.0f, 0, 0, 0, 0, 48.0f, -572.0f, -116.0f, 0.0f, 0.0f, &from, &cur));
    }

    printf("\n== 第 2 帧: 字段载荷是裸值吗(基线不应影响输出) ==\n");
    {
        uint8_t b1[512], b2[512], b3[512];
        codol_snap_state_t c1, c2, c3;
        int n1, n2, n3, j, base_diff = 0, f1f2_diff = 0;

        /* 帧1: 基线全零 */
        codol_snap_state_zero(&from); codol_snap_state_zero(&cur);
        n1 = codol_snapshot_build(b1, (int)sizeof b1, 0, 1000, 1000, true,
                                  48.0f, -572.0f, -116.0f, 0, 0, 0,
                                  0.0f, 0.0f, 0.0f, false,
                                  false, false, 0, &from, &cur, &eq, NULL, 0);
        c1 = cur;

        /* 帧2(a): from = 帧1 的值 —— 非零基线 */
        codol_snap_state_zero(&c2);
        n2 = codol_snapshot_build(b2, (int)sizeof b2, 0, 2000, 1000, false,
                                  48.0f, -572.0f, -116.0f, 0, 0, 0,
                                  0.0f, 0.0f, 0.0f, false,
                                  false, false, 0, &c1, &c2, &eq, NULL, 0);

        /* 帧2(b): from = 全零 —— 零基线。载荷若是裸值, 两者必须完全相同。 */
        codol_snap_state_zero(&from); codol_snap_state_zero(&c3);
        n3 = codol_snapshot_build(b3, (int)sizeof b3, 0, 2000, 1000, false,
                                  48.0f, -572.0f, -116.0f, 0, 0, 0,
                                  0.0f, 0.0f, 0.0f, false,
                                  false, false, 0, &from, &c3, &eq, NULL, 0);

        if (n2 == n3)
            for (j = 0; j < n2; j++) if (b2[j] != b3[j]) base_diff++;
        if (n1 == n3)
            for (j = 0; j < n1; j++) if (b1[j] != b3[j]) f1f2_diff++;

        printf("   帧1 基线全零           len=%d\n", n1);
        printf("   帧2 from=帧1(非零基线) len=%d\n", n2);
        printf("   帧2 from=零(零基线)    len=%d\n", n3);
        printf("   帧2 两种基线之间不同的字节数 = %d   (0 = 载荷是裸值, 基线不参与编码)\n", base_diff);
        printf("   帧1 与 帧2 不同的字节数       = %d   (只应是头部 serverTime/first/flags)\n", f1f2_diff);

        printf("XCHK frame1=");
        for (j = 0; j < n1; j++) printf("%02X", b1[j]);
        printf("\nXCHK frame2_prev=");
        for (j = 0; j < n2; j++) printf("%02X", b2[j]);
        printf("\nXCHK frame2_zero=");
        for (j = 0; j < n3; j++) printf("%02X", b3[j]);
        printf("\nXCHK frame2_baseline_diff_bytes=%d\n", base_diff);
        printf("XCHK frame1_vs_frame2_zero_diff_bytes=%d\n", f1f2_diff);
        printf("XCHK frame1_vs_frame2_zero_diff_offsets=");
        if (n1 == n3) { int first = 1; for (j = 0; j < n1; j++) if (b1[j] != b3[j]) { printf("%s%d", first ? "" : ",", j); first = 0; } }
        printf("\n");
    }

    printf("\n== 与 Python 参照逐字节对拍 ==\n");
    printf("   (ack=0 server_time=1000 command_time=1000 first=1 xyz=48,-572,-116)\n");
    {
        uint8_t buf[512];
        int n, j;
        codol_snap_state_zero(&from); codol_snap_state_zero(&cur);
        n = codol_snapshot_build(buf, (int)sizeof buf, 0, 1000, 1000, true,
                                 48.0f, -572.0f, -116.0f, 0, 0, 0,
                                 0.0f, 0.0f, 0.0f, false,
                                 false, false, 0, &from, &cur, &eq, NULL, 0);
        printf("C   omit=0 len=%d\n", n);
        for (j = 0; j < n; j++) printf("%02X", buf[j]);
        printf("\nXCHK omit0_first=");
        for (j = 0; j < n; j++) printf("%02X", buf[j]);
        printf("\n");
        codol_snap_state_zero(&from); codol_snap_state_zero(&cur);
        n = codol_snapshot_build(buf, (int)sizeof buf, 0, 1000, 1000, true,
                                 48.0f, -572.0f, -116.0f, 0, 0, 0,
                                 0.0f, 0.0f, 0.0f, false,
                                 true, false, 0, &from, &cur, &eq, NULL, 0);
        printf("C   omit=1 len=%d\n", n);
        for (j = 0; j < n; j++) printf("%02X", buf[j]);
        printf("\nXCHK omit1_first=");
        for (j = 0; j < n; j++) printf("%02X", buf[j]);
        printf("\n");

        /* ★ 实机首帧用的是 command_time = svc->processed_input_time(=0, 还没收过 usercmd),
         *   上面那份用 1000 是为了与 Python 参照的黄金向量对齐。这里再出一份 ct=0 的,
         *   用来跟 ENTITY_SECTION 那轮的**线上字节**逐字节对账。 */
        codol_snap_state_zero(&from); codol_snap_state_zero(&cur);
        n = codol_snapshot_build(buf, (int)sizeof buf, 0, 1000, 0, true,
                                 48.0f, -572.0f, -116.0f, 0, 0, 0,
                                 0.0f, 0.0f, 0.0f, false,
                                 true, false, 0, &from, &cur, &eq, NULL, 0);
        printf("C   omit=1 command_time=0 len=%d\n", n);
        for (j = 0; j < n; j++) printf("%02X", buf[j]);
        printf("\nXCHK omit1_first_ct0=");
        for (j = 0; j < n; j++) printf("%02X", buf[j]);
        printf("\n");
    }
    printf("\n== 实体段(开着) ==");
    {
        codol_snap_entity_t ents[8];
        uint8_t buf[512];
        int n, j, k;
        for (k = 0; k < 8; k++) {
            ents[k].number = k;
            ents[k].type   = 7;                 /* ACTOR */
            ents[k].x = 100.0f + k * 10.0f;
            ents[k].y = -200.0f;
            ents[k].z = -124.0f;
        }
        codol_snap_state_zero(&from); codol_snap_state_zero(&cur);
        n = codol_snapshot_build(buf, (int)sizeof buf, 0, 1000, 1000, true,
                                 48.0f, -572.0f, -116.0f, 0, 0, 0,
                                 0.0f, 0.0f, 0.0f, false,
                                 true, false, 0, &from, &cur, &eq, ents, 8);
        printf("   8 实体  n=%d  末字节=0x%02X (应为 0x05)\n", n, n > 0 ? buf[n-1] : 0);
        printf("   尾部 24 字节: ");
        for (j = (n > 24 ? n - 24 : 0); j < n; j++) printf("%02X", buf[j]);
        printf("\n");
        if (n <= 0) { printf("   失败: 构建返回 %d\n", n); }
        else if (buf[n-1] != 0x05) { printf("   失败: 终止符没了\n"); }
        else if (n >= (int)sizeof buf) { printf("   失败: 撑爆缓冲\n"); }
        else printf("   通过: 终止符在, %d < %d 缓冲\n", n, (int)sizeof buf);
    }
    return 0;
}
