#ifndef CODOL_EQUIPMENT_H
#define CODOL_EQUIPMENT_H
/* 武器/弹药/开火/换弹状态机 —— 逐行移植参照实现 battle_server.py 的
 * `_Slot` / `_Equipment`(L925-L1025)。参照当年在真实客户端字节上打出 120 次
 * WEAPON_FIRE, 说明这套语义与客户端一致。
 *
 * ★ 之前 C 版整块缺失: 装备是**静态模板**(clip=30/reserve=90/weapon_state=0/
 *   events=0), 于是每帧把弹药回拨到 30、开火与换弹事件从不回显 ->
 *   弹药数量不准/自动回升、换弹动作反复、自己开火。
 */
#include <stdint.h>
#include <stdbool.h>
#include "codol_usercmd.h"
#include "codol_snapshot.h"

#ifdef __cplusplus
extern "C" {
#endif

#define CODOL_EQUIP_MAX_SLOTS 4
#define CODOL_BTN_FIRE   0x1u    /* usercmd.buttons: 开火 */
#define CODOL_BTN_RELOAD 0x10u   /* usercmd.buttons: 换弹 */

typedef struct {
    int  weapon;      /* ★ 客户端认的武器编号(线上值)。
                       *   gamestate 里 `** 309 0 0` -> configstring 7116
                       *   -> **动态 ID 1156**; 客户端 usercmd.weapon 发的是
                       *   **stock base(309)**, 快照武器槽发的是**动态 ID(1156)**。
                       *   两套编号并存, 槽位登记必须用动态 ID, 否则客户端切枪
                       *   信号(309) 永远匹配不上槽位 -> 副武器切不出来。 */
    int  base_index;  /* stock 武器索引(309/106) —— usercmd.weapon 上报的那套 */
    int  ammo_key;
    int  capacity;
    int  clip;
    int  reserve;
    int  fire_ms;
    int  ads_per_sec;
    bool semi;
    int  reload_ms;
    int  empty_reload_ms;
    int  reload_add_ms;
    int  empty_reload_add_ms;
} codol_equip_slot_t;

typedef struct {
    codol_equip_slot_t slots[CODOL_EQUIP_MAX_SLOTS];
    int      slot_count;
    int      selected_slot;
    int      weapon_time;
    int      weapon_delay;
    int      weapon_state;
    int      backpack;
    int      event_sequence;
    uint8_t  events[4];
    uint16_t event_weapons[4];
    uint32_t previous_buttons;
    bool     reload_transfer;
    /* 客户端 usercmd.weapon 告诉我们的当前武器(CoD4x/IW4 语义: 服务端采信) */
    int      current_weapon;
} codol_equipment_t;

void codol_equipment_init(codol_equipment_t *e);

/* 用一条 usercmd 推进(elapsed_ms = 距上一条命令的毫秒); 返回是否**本次开火** */
bool codol_equipment_step(codol_equipment_t *e, const codol_usercmd_t *c, int elapsed_ms);

/* `mr 1 1 custom1/custom2` 选择背包 */
bool codol_equipment_select_backpack(codol_equipment_t *e, const char *command);

/* 映射到快照结构 */
void codol_equipment_to_snapshot(const codol_equipment_t *e, codol_snap_equip_t *out);

#ifdef __cplusplus
}
#endif
#endif /* CODOL_EQUIPMENT_H */
