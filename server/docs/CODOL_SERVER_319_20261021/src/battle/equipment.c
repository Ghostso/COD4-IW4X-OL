#include "codol_equipment.h"
#include <string.h>

/* 照 _Slot.__init__: clip = capacity, reserve = capacity*3, 换弹/射速随武器不同
 * base = stock 武器索引(usercmd.weapon 上报的那套); 武器参数一律按 base 判定。 */
static void slot_init(codol_equip_slot_t *s, int weapon, int base, int ammo,
                      int capacity, int fire_ms, int ads)
{
    memset(s, 0, sizeof(*s));
    s->weapon = weapon;
    s->base_index = base;
    s->ammo_key = ammo;
    s->capacity = capacity;
    s->clip = capacity;
    s->reserve = capacity * 3;
    s->fire_ms = fire_ms;
    s->ads_per_sec = ads;
    s->semi = (base == 1158 || base == 309);
    if (base == 309) {
        /* 自由 荣耀 (csg12sscny_mp) */
        s->reload_ms = 2200;
        s->empty_reload_ms = 2799;
    } else if (base == 106) {
        /* 正义 黑金 (ak47ssblack_mp) */
        s->reload_ms = 2304;
        s->empty_reload_ms = 2500;
    } else {
        s->reload_ms = (base == 1157) ? 2000 : ((base == 1158) ? 1799 : 2029);
        s->empty_reload_ms = (base == 1157) ? 2609 : ((base == 1158) ? 2000 : 2799);
    }
    s->reload_add_ms = (base == 1157) ? 1299 : ((base == 1158) ? 1350 : 1399);
    s->empty_reload_add_ms = 1399;
}

static void add_event(codol_equipment_t *e, uint8_t etype, uint16_t parameter)
{
    int i = e->event_sequence & 3;
    e->events[i] = etype;
    e->event_weapons[i] = parameter;
    e->event_sequence = (e->event_sequence + 1) & 0xFF;
}

void codol_equipment_init(codol_equipment_t *e)
{
    memset(e, 0, sizeof(*e));
    e->slot_count = 2;
    e->selected_slot = 0;
    e->backpack = 1;
    e->current_weapon = 309;
    /* ★ 槽位 weapon 必须是 **stock 引擎索引** —— 实测依据:
     *   ONCE_20261026_193429 真实客户端 usercmd 上报 `W=309`(自由荣耀)、
     *   `W=106`(正义黑金), 且那一轮武器显示正确。
     *   ⚠️ 曾误改成动态 ID(1156/1157, 即 configstring 7116/7117-5960),
     *      实测客户端显示成「6 发子弹的 M4A1 Tech / 短剑 Vector」——
     *      1156 落在 stock 表末尾(1135)与动态段起点(1224)之间的空洞,
     *      客户端解析失败后退回自己的默认武器。base_index 保留同值以兼容。 */
    /* 自由 荣耀 (csg12sscny_mp): 容量 6 / 备弹 18 */
    slot_init(&e->slots[0], 309, 309, 309, 6, 192, 4);
    /* 正义 黑金 (ak47ssblack_mp): 容量 30 / 备弹 90 */
    slot_init(&e->slots[1], 106, 106, 106, 30, 96, 4);
}

bool codol_equipment_select_backpack(codol_equipment_t *e, const char *command)
{
    /* 形如 "mr 1 1 customN"; 只有 custom1/custom2 有效 */
    char w[4][32];
    int n = 0, i = 0, j = 0;
    const char *p = command;
    memset(w, 0, sizeof(w));
    if (!p) return false;
    while (*p && n < 4) {
        if (*p == ' ' || *p == '\t') {
            if (j > 0) { n++; j = 0; }
            p++;
            continue;
        }
        if (j < 31) w[n][j++] = *p;
        p++;
    }
    if (j > 0) n++;
    if (n != 4) return false;
    if (strcmp(w[0], "mr") != 0 || strcmp(w[1], "1") != 0 || strcmp(w[2], "1") != 0) return false;
    i = 0;
    if (strcmp(w[3], "custom1") == 0) i = 1;
    else if (strcmp(w[3], "custom2") == 0) i = 2;
    if (i == 0) return false;
    if (i == e->backpack) return true;

    e->backpack = i;
    e->current_weapon = (i == 2) ? 1157 : 309;
    e->selected_slot = 0;
    e->weapon_time = e->weapon_delay = e->weapon_state = 0;
    e->reload_transfer = false;
    if (i == 2) {
        /* ★ custom2 是另一个背包(M4A1 T / Vector 旧配置), 本轮未重新标定,
         *   保持原有编号原样; base 与 weapon 相同以维持旧匹配语义。 */
        e->slot_count = 3;
        slot_init(&e->slots[0], 1157, 1157, 1112, 36, 59, 5);
        slot_init(&e->slots[1], 1158, 1158, 646, 15, 90, 8);
        slot_init(&e->slots[2], 317, 317, 317, 0, 800, 0);
    } else {
        e->slot_count = 2;
        slot_init(&e->slots[0], 309, 309, 309, 6, 192, 4);
        slot_init(&e->slots[1], 106, 106, 106, 30, 96, 4);
    }
    return true;
}

bool codol_equipment_step(codol_equipment_t *e, const codol_usercmd_t *c, int elapsed_ms)
{
    int i;
    codol_equip_slot_t *sel;
    bool fired = false, reload_pressed;

    if (!e || !c) return false;

    /* ★ 客户端每帧告诉我们它手上的武器(usercmd.weapon)。
     *   CoD4x/IW4 语义: 服务端采信它。
     *
     *   ★★ 修正(2026-10-22 实机): 之前直接采信任何非零值，而 usercmd
     *   位流在真实客户端上会解出垃圾值(实测恒为 58566)。
     *   58566 不在任何真实武器 ID 范围内，但它反复命中切枪循环的
     *   比较，于是每帧都在"切枪"。实测表现: W+Shift 变切枪。
     *   约束: 只接受 1..2047 且必须命中已知槽位。 */
    /* ★ 客户端 usercmd.weapon = **stock base 索引**(实测 309 / 106), 不是动态 ID。
     *   槽位登记的 weapon 是动态 ID(1156/1157), 所以必须按 base_index 比对,
     *   否则切枪信号永远匹配不上 -> 副武器切不出来(实测症状)。 */
    if (c->weapon >= 1 && c->weapon <= 2047) {
        bool known = false;
        for (i = 0; i < e->slot_count; i++)
            if (e->slots[i].base_index == (int)c->weapon ||
                e->slots[i].weapon == (int)c->weapon) { known = true; break; }
        if (known) e->current_weapon = (int)c->weapon;

        /* 切枪: 仅当上报值真的命中其它槽位时才切 */
        for (i = 0; i < e->slot_count; i++) {
            if ((e->slots[i].base_index == (int)c->weapon ||
                 e->slots[i].weapon == (int)c->weapon) && i != e->selected_slot) {
                e->selected_slot = i;
                e->weapon_time = e->weapon_delay = e->weapon_state = 0;
                e->reload_transfer = false;
                break;
            }
        }
    }

    e->weapon_time -= elapsed_ms;
    if (e->weapon_time < 0) e->weapon_time = 0;
    e->weapon_delay -= elapsed_ms;
    if (e->weapon_delay < 0) e->weapon_delay = 0;

    /* 换弹"转运"阶段结束 -> 把备弹填进弹匣 */
    if (e->reload_transfer && e->weapon_delay == 0) {
        sel = &e->slots[e->selected_slot];
        {
            int amount = sel->capacity - sel->clip;
            if (amount > sel->reserve) amount = sel->reserve;
            sel->clip += amount;
            sel->reserve -= amount;
        }
        e->reload_transfer = false;
    }
    if (e->weapon_time == 0) e->weapon_state = 0;

    sel = &e->slots[e->selected_slot];
    reload_pressed = (c->buttons & CODOL_BTN_RELOAD) != 0;
    if (e->weapon_time == 0 && sel->capacity > 0 && sel->clip < sel->capacity &&
        sel->reserve > 0 && (reload_pressed || sel->clip == 0)) {
        bool empty = (sel->clip == 0);
        e->weapon_time = empty ? sel->empty_reload_ms : sel->reload_ms;
        e->weapon_delay = empty ? sel->empty_reload_add_ms : sel->reload_add_ms;
        e->weapon_state = 8;
        e->reload_transfer = true;
        add_event(e, empty ? 0x1A : 0x19, 0);
    }

    if ((c->buttons & CODOL_BTN_FIRE) && e->weapon_time == 0 && sel->clip > 0 &&
        (!sel->semi || (e->previous_buttons & CODOL_BTN_FIRE) == 0)) {
        sel->clip -= 1;
        e->weapon_time = sel->fire_ms;
        e->weapon_state = 6;
        add_event(e, 0x24, (uint16_t)sel->weapon);
        fired = true;
    }

    e->previous_buttons = c->buttons;
    return fired;
}

void codol_equipment_to_snapshot(const codol_equipment_t *e, codol_snap_equip_t *out)
{
    int i;
    memset(out, 0, sizeof(*out));
    out->weapon_time = e->weapon_time;
    out->weapon_delay = e->weapon_delay;
    out->weapon_state = e->weapon_state;
    out->event_sequence = e->event_sequence;
    for (i = 0; i < 4; i++) {
        out->events[i] = e->events[i];
        out->event_weapons[i] = e->event_weapons[i];
    }
    out->slot_count = e->slot_count;
    /* ★ index 39 用得到: 当前手持槽。参照写 sel.weapon。 */
    out->selected_slot = (e->selected_slot >= 0 && e->selected_slot < e->slot_count)
                             ? e->selected_slot : 0;
    for (i = 0; i < e->slot_count && i < 4; i++) {
        /* ★ 每个槽位恒定写自己的武器 ID。
         *   之前把选中槽写成 current_weapon -> 切枪时 slots[0] 的 ID 也跟着变,
         *   客户端看到的是"同一槽位武器变了" -> 装备丢失/没枪。 */
        out->slots[i].weapon = e->slots[i].weapon;
        out->slots[i].ammo_key = e->slots[i].ammo_key;
        out->slots[i].clip = e->slots[i].clip;
        out->slots[i].reserve = e->slots[i].reserve;
        out->slots[i].capacity = e->slots[i].capacity;
    }
}
