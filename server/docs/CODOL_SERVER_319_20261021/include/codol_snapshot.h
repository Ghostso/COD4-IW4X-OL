#ifndef CODOL_SNAPSHOT_H
#define CODOL_SNAPSHOT_H
/* 运动快照 —— 逐行照抄 CodolMotionSnapshot.Build(参照实现)。
 * 首帧应为 124 字节(参照日志: TX_SPAWN_EXPERIMENT bytes=124)。 */
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    int   weapon;      /* 1156 */
    int   ammo_key;    /* 585  */
    int   clip;        /* 30   */
    int   reserve;     /* 71   */
    int   capacity;    /* 4    */
} codol_snap_slot_t;

typedef struct {
    int                weapon_time;
    int                weapon_delay;
    int                weapon_state;
    int                event_sequence;
    uint8_t            events[4];
    uint16_t           event_weapons[4];
    codol_snap_slot_t  slots[4];
    int                slot_count;
    /* ★ 当前手持槽位 —— index 39 必须发 sel.weapon(参照 battle_server.py:1183),
     *   不是 slots[0]。默认 0。 */
    int                selected_slot;
} codol_snap_equip_t;

void codol_snap_equip_default(codol_snap_equip_t *eq);

/* ===================== 帧基线(◁ 参考实现笃定)
 * ★ 本协议每个字段写的是 **新值 XOR 基线值**。
 *   依据: CoD4x MSG_WriteDeltaField (msg.c:1983-2216):
 *     case -88:  MSG_WriteLong(msg, to ^ from);        // float -> 32 位异或
 *     default:   if (to) { bit1; write (to ^ from) 的 abs(bits) 位 } else bit0;
 *   首帧 deltaNum=0 -> 客户端用全零基线, 所以裸值恰好等于异或值;
 *   从第二帧起必须真异或, 否则客户端解出垃圾。 */
typedef struct {
    uint32_t command_time;
    int      pm_flags;
    float    x, y, z;
    float    vx, vy;
    uint16_t yaw, pitch, roll;
    float    aim_fraction;
    int      weapon_state, weapon_time, weapon_delay;
    int      current_weapon;
    int      viewmodel;
    int      weapon_choice;
    int      view_entity;
    int      ground_entity;
    int      pm_type;
    int      objective_entity;
    int      speed, gravity;
    int      size_scale;
    uint8_t  events[4];
    uint16_t event_weapons[4];
} codol_snap_state_t;

void codol_snap_state_zero(codol_snap_state_t *st);

/* ===================== 实体段(entityState)入参 =====================
 * 描述一个要发给客户端的实体。字段与参照实现 sv_snapshot_mp.cpp 对应:
 *   number = 实体槽号(writeEntityNumber 用, 必须**升序**传入)
 *   type   = eType(字段 0, 原样写 8 位字节)
 *   x/y/z  = pos.origin(字段 2/3/4, 经 writeEntityOrigin 压缩)
 * 传入实体数组与条数; ents==NULL 或 ent_count<=0 = **不发实体段**
 * (与开关关闭的产出完全一致)。 */
typedef struct {
    int   number;
    int   type;
    float x, y, z;
} codol_snap_entity_t;

/* 生成一帧; 返回字节数(首帧应为 124) */
int codol_snapshot_build(uint8_t *out, int out_cap,
                         uint32_t ack, uint32_t server_time, uint32_t command_time,
                         bool first,
                         float x, float y, float z,
                         int16_t pitch, int16_t yaw, int16_t roll,
                         float vx, float vy, float aim_fraction, bool aiming,
                         bool omit_motion,
                         bool on_ground,
                         uint16_t living_weapon_entity,
                         const codol_snap_state_t *from,
                         codol_snap_state_t *cur,
                         const codol_snap_equip_t *eq,
                         const codol_snap_entity_t *ents, int ent_count);

#ifdef __cplusplus
}
#endif
#endif /* CODOL_SNAPSHOT_H */
