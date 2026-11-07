/* test_equipment: 开火/换弹状态机 (移植参照 _Equipment) —— 锁死
 * "弹药每帧被静态模板回拨 / 事件不回显 / 换弹反复 / 自己开火" 这类回归 */
#include "codol_equipment.h"
#include <stdio.h>
#include <string.h>

static int fails;
#define CK(cond, fmt, ...) do { if (!(cond)) { printf("FAIL " fmt "\n", ##__VA_ARGS__); fails++; } } while (0)

static codol_usercmd_t cmd(uint32_t t, uint32_t btn, uint16_t w)
{
    codol_usercmd_t c; memset(&c, 0, sizeof(c));
    c.time = t; c.buttons = btn; c.weapon = w; return c;
}

int main(void)
{
    codol_equipment_t e;
    codol_usercmd_t c;

    /* ① 默认背包 1: 自由荣耀(csg12sscny_mp) stock 索引 309
     *   clip=6, reserve=18 —— 它是**半自动/泵动**(semi)。 */
    codol_equipment_init(&e);
    CK(e.slot_count == 2, "slot_count=%d (应 2)", e.slot_count);
    CK(e.slots[0].weapon == 309 && e.slots[0].base_index == 309,
       "槽0 weapon=%d base=%d", e.slots[0].weapon, e.slots[0].base_index);
    CK(e.slots[0].clip == 6 && e.slots[0].reserve == 18,
       "槽0 clip=%d reserve=%d", e.slots[0].clip, e.slots[0].reserve);
    CK(e.slots[1].weapon == 106 && e.slots[1].base_index == 106,
       "槽1 weapon=%d base=%d", e.slots[1].weapon, e.slots[1].base_index);
    CK(e.slots[1].clip == 30 && e.slots[1].reserve == 90,
       "槽1 clip=%d reserve=%d", e.slots[1].clip, e.slots[1].reserve);
    CK(e.slots[0].semi, "309(自由荣耀)应为半自动/泵动");
    printf("ok   默认        槽0=%d(%d) clip=%d / 槽1=%d(%d) clip=%d\n",
           e.slots[0].weapon, e.slots[0].base_index, e.slots[0].clip,
           e.slots[1].weapon, e.slots[1].base_index, e.slots[1].clip);

    /* ② 开火 1 发: clip-1, state=6, 事件 0x24
     *   usercmd.weapon 上报的是 **stock base(309)**, 不是动态 ID。 */
    c = cmd(1000, CODOL_BTN_FIRE, 309);
    CK(codol_equipment_step(&e, &c, 0) == true, "第一发应开火");
    CK(e.slots[0].clip == 5, "开火后 clip=%d (应 5)", e.slots[0].clip);
    CK(e.weapon_state == 6, "weapon_state=%d (应 6)", e.weapon_state);
    CK(e.weapon_time == e.slots[0].fire_ms, "weapon_time=%d (应 %d)", e.weapon_time, e.slots[0].fire_ms);
    CK(e.events[(e.event_sequence + 3) & 3] == 0x24, "应发出 0x24 开火事件");
    printf("ok   开火         clip=%d state=6 event=0x24 冷却=%dms\n", e.slots[0].clip, e.weapon_time);

    /* ③ 冷却内连按: 不扣弹 */
    c.time = 1010;
    CK(codol_equipment_step(&e, &c, 0) == false, "冷却内不应再开火");
    CK(e.slots[0].clip == 5, "冷却内 clip 应变 %d", e.slots[0].clip);
    printf("ok   射速冷却     冷却内连按 clip 仍为 %d\n", e.slots[0].clip);

    /* ④ 过冷却后可再开火 —— 半自动需先松开扳机再按 */
    c.time = 1080; c.buttons = 0;
    codol_equipment_step(&e, &c, e.slots[0].fire_ms);
    c.buttons = CODOL_BTN_FIRE;
    CK(codol_equipment_step(&e, &c, 0) == true, "过冷却后应能开火");
    CK(e.slots[0].clip == 4, "第二发后 clip=%d (应 4)", e.slots[0].clip);
    printf("ok   连续开火     clip=%d\n", e.slots[0].clip);

    /* ⑤ 换弹: state=8, 事件 0x19, 转运置位 */
    c = cmd(1100, CODOL_BTN_RELOAD, 309);
    c.buttons = 0; codol_equipment_step(&e, &c, e.slots[0].fire_ms);   /* 清掉射击冷却 */
    c.buttons = CODOL_BTN_RELOAD;
    CK(codol_equipment_step(&e, &c, 0) == false, "换弹不应被判为开火");
    CK(e.weapon_state == 8, "换弹 weapon_state=%d (应 8)", e.weapon_state);
    CK(e.reload_transfer == true, "换弹应置 reload_transfer");
    CK(e.weapon_time == e.slots[0].reload_ms, "换弹 weapon_time=%d (应 %d)", e.weapon_time, e.slots[0].reload_ms);
    printf("ok   换弹         state=8 event=0x19 时长=%dms 转运=%dms\n",
           e.weapon_time, e.slots[0].reload_add_ms);

    /* ⑥ 转运结束 -> 备弹补满弹匣 (4 -> 6, reserve 18 -> 16) */
    c.buttons = 0;
    codol_equipment_step(&e, &c, e.slots[0].reload_add_ms);
    CK(e.slots[0].clip == 6, "换弹后 clip=%d (应 6)", e.slots[0].clip);
    CK(e.slots[0].reserve == 16, "换弹后 reserve=%d (应 16)", e.slots[0].reserve);
    printf("ok   换弹完成     clip=%d reserve=%d\n", e.slots[0].clip, e.slots[0].reserve);

    /* ⑦ 背包切换: custom2 -> 3 槽, 1157/1158/317, 1158 为半自动 */
    CK(codol_equipment_select_backpack(&e, "mr 1 1 custom2") == true, "custom2 应生效");
    CK(e.slot_count == 3, "custom2 slot_count=%d (应 3)", e.slot_count);
    CK(e.slots[0].weapon == 1157 && e.slots[1].weapon == 1158 && e.slots[2].weapon == 317,
       "custom2 武器 = %d/%d/%d", e.slots[0].weapon, e.slots[1].weapon, e.slots[2].weapon);
    CK(e.slots[1].semi == true && e.slots[0].semi == false, "1158 应为半自动");
    CK(!codol_equipment_select_backpack(&e, "mr 1 1 custom9"), "custom9 不应生效");
    printf("ok   背包切换     custom2 -> 1157/%d/317 (semi=%d)\n", e.slots[1].weapon, (int)e.slots[1].semi);

    /* ⑧ 半自动: 按住不放只出 1 发, 松开再按才出第 2 发 */
    {
        int clip0;
        /* 切到 1158 时不按开火(否则切槽那一步本身就会打出一发) */
        c = cmd(2000, 0, 1158);
        codol_equipment_step(&e, &c, 0);
        CK(e.selected_slot == 1, "应切到 1158 槽, 实际 %d", e.selected_slot);
        clip0 = e.slots[1].clip;
        c.time = 2100; c.buttons = CODOL_BTN_FIRE;
        CK(codol_equipment_step(&e, &c, e.slots[1].fire_ms) == true, "半自动首发应开火");
        CK(e.slots[1].clip == clip0 - 1, "半自动首发 clip=%d (应 %d)", e.slots[1].clip, clip0 - 1);
        c.time = 2200;
        CK(codol_equipment_step(&e, &c, e.slots[1].fire_ms) == false, "半自动按住不应连发");
        CK(e.slots[1].clip == clip0 - 1, "半自动按住 clip 不应变 (%d)", e.slots[1].clip);
        c.time = 2300; c.buttons = 0;
        codol_equipment_step(&e, &c, e.slots[1].fire_ms);
        c.time = 2400; c.buttons = CODOL_BTN_FIRE;
        CK(codol_equipment_step(&e, &c, e.slots[1].fire_ms) == true, "松开再按应能开火");
        printf("ok   半自动       按住 1 发, 松开再按 1 发 (clip %d -> %d)\n", clip0, e.slots[1].clip);
    }

    /* ⑨ 空仓自动换弹: 事件应为 0x1A, 时长 = empty_reload_ms */
    {
        codol_equipment_init(&e);
        e.slots[0].clip = 0;
        c = cmd(3000, 0, 309);
        codol_equipment_step(&e, &c, 0);
        CK(e.weapon_state == 8, "空仓应自动换弹 state=%d", e.weapon_state);
        CK(e.weapon_time == e.slots[0].empty_reload_ms,
           "空仓换弹时长=%d (应 %d)", e.weapon_time, e.slots[0].empty_reload_ms);
        CK(e.events[(e.event_sequence + 3) & 3] == 0x1A, "空仓应发 0x1A 事件");
        printf("ok   空仓换弹     state=8 event=0x1A 时长=%dms\n", e.weapon_time);
    }

    printf("\n%s (%d)\n", fails ? "FAILED" : "ALL PASSED", fails);
    return fails ? 1 : 0;
}
