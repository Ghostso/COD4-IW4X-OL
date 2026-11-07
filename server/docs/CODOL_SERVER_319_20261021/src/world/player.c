#include "codol_player.h"
#include "codol_collision.h"
#include "codol_entity.h"
#include <math.h>
#include <string.h>

void codol_player_init(codol_player_t *p, float x, float y, float z)
{
    memset(p, 0, sizeof(*p));
    p->x = x; p->y = y; p->z = z;
    p->gravity = CODOL_GRAVITY;
    p->on_ground = true;
    p->stance = CODOL_STANCE_STAND;
    p->weapon = 1156;
    p->aiming = false;
    p->aim_fraction = 0.0f;
}

/* 照 CoD4x bg_jump.cpp Jump_Start (L133-L156):
 *     velocitySqrd = (height * 2) * ps->gravity;   // 平方量
 *     ...落地减速: velocitySqrd /= factor ...
 *     ps->velocity[2] = sqrtf(velocitySqrd);       // ★ 速度 = **开方后**
 * ★ 之前把未开方的 2*39*800=62400 当成速度 -> 每帧 +1040,
 *   永不落地 -> z 爆炸到百万(实测已复现)。
 *   正确初速 = sqrt(2*39*800) ≈ 249.8 u/s。 */
float codol_player_jump_velocity(const codol_player_t *p)
{
    float val = (CODOL_JUMP_HEIGHT + CODOL_JUMP_HEIGHT) * p->gravity;
    if ((p->pm_flags & CODOL_PMF_JUMPING) &&
        p->pm_time <= CODOL_JUMP_LAND_SLOWDOWN_TIME) {
        float newdiv;
        if (!CODOL_JUMP_SLOWDOWN_ENABLE) {
            newdiv = 1.0f;
        } else if (p->pm_time > 1699) {
            newdiv = 2.5f;
        } else {
            newdiv = (float)p->pm_time * 1.5f * 0.00058823527f + 1.0f;
        }
        if (newdiv > 0.0f) val = val / newdiv;
    }
    if (val <= 0.0f) return 0.0f;
    return sqrtf(val);
}

/* 照 CoD4x Jump_GetLandFactor */
float codol_player_land_factor(const codol_player_t *p)
{
    if (!CODOL_JUMP_SLOWDOWN_ENABLE) return 1.0f;
    if (p->pm_time < 1700)
        return (float)p->pm_time * 1.5f * 0.00058823527f + 1.0f;
    return 2.5f;
}

/* 动态碰撞盒: 只有**真正该挡住玩家**的实体才进这个列表。
 *
 * ★★ 2026-10-24 修正: 原实现把世界里**每一个** in_use 实体都当成 32×32×64 的实心盒,
 *   而 `codol_world_spawn_map_entities()` 会把地图上 333 个 `script_model` **装饰道具**
 *   (轮胎墙、集装箱墙、桌椅、路桩 …) 全部生成为 CODOL_ET_GENERAL。后果:
 *   玩家在 `(-563,-463)` 被旁边的 `cargo_cage_wall_long`(装饰, 原点是它的角点)
 *   用一个人为的 32×32 盒子挡住, 一直按 W 也纹丝不动 —— 而服务端现在**每帧把这个
 *   冻结坐标推给客户端**, 客户端因此也不跑自己的物理 ⇒ 表现为"悬空 + 穿墙"。
 *   装饰道具的真实几何在 clipmap(`codol_static_boxes`, 29 个精确 AABB)里,
 *   不该再被 AABB 近似重复一遍。
 *   ⇒ 只保留**非装饰**实体: actor / vehicle / turret / loot / item / objective 等
 *     玩家真正会撞到的东西。GENERAL(装饰)与 SCRIPT_MOVER(可动装饰)排除。 */
static int build_dynamic_boxes(const codol_world_t *world, int skip_entity,
                               codol_collision_box_t *boxes, int capacity)
{
    int i, count = 0;
    if (!world || !boxes || capacity <= 0) return 0;
    for (i = 0; i < CODOL_MAX_ENTITIES && count < capacity; ++i) {
        const codol_entity_state_t *e = &world->entities[i];
        float half_x, half_y, height;
        if (!e->in_use || i == skip_entity) continue;
        if (e->type == CODOL_ET_FREE || e->type == CODOL_ET_CORPSE) continue;
        if (e->type == CODOL_ET_MISSILE) continue;
        /* ★ 装饰道具不参与动态碰撞(它们的几何在 clipmap 里) */
        if (e->type == CODOL_ET_GENERAL || e->type == CODOL_ET_SCRIPT_MOVER) continue;
        half_x = (e->maxs[0] > e->mins[0]) ? (e->maxs[0] - e->mins[0]) * 0.5f : 15.0f;
        half_y = (e->maxs[1] > e->mins[1]) ? (e->maxs[1] - e->mins[1]) * 0.5f : 15.0f;
        height = (e->maxs[2] > e->mins[2]) ? (e->maxs[2] - e->mins[2]) : 70.0f;
        boxes[count].mins[0] = e->pos.origin[0] - half_x;
        boxes[count].mins[1] = e->pos.origin[1] - half_y;
        boxes[count].mins[2] = e->pos.origin[2];
        boxes[count].maxs[0] = e->pos.origin[0] + half_x;
        boxes[count].maxs[1] = e->pos.origin[1] + half_y;
        boxes[count].maxs[2] = e->pos.origin[2] + height;
        boxes[count].contents = CODOL_CONTENTS_SOLID;
        boxes[count].entity_num = e->number;
        count++;
    }
    return count;
}

void codol_player_move_in_world(codol_player_t *p, const codol_usercmd_t *c, float dt,
                                const codol_world_t *world, int skip_entity)
{
    float yaw_rad, wish_f, wish_r, norm;

    if (!p || !c) return;

    /* 时间: 用于 pm_time(跳跃/落地窗口) 与去重 */
    if (p->last_cmd_time && c->time > (uint32_t)p->last_cmd_time)
        p->pm_time += (int)(c->time - (uint32_t)p->last_cmd_time);
    p->last_cmd_time = (int)c->time;

    p->pitch = c->pitch;
    p->yaw   = c->yaw;
    p->roll  = c->roll;
    p->buttons = c->buttons;
    if (p->on_ground) p->jump_origin_z = p->z;   /* IW4 playerState: jumpOriginZ */
    if (c->weapon) p->weapon = c->weapon;

    /* 方向换算 —— 逐行照拄 CODOL-Combat-Server-v0.1 \
     * GameWorld.ComputeMoveVelocity (L621-L638) 与实测标定配置
     * firingrange_live.cfg:
     *   dir_bias = 0 -2        # 客户端 yaw 单位=32768/圈(非65536)且符号相反
     *   flip_move_y = 1        # 东西方向与 +Y 相反
     *   flip_strafe_x = 1      # A/D 互换
     *   vx = (cos*fwd + sin*right)*Speed*norm ; vy = (sin*fwd - cos*right)*Speed*norm
     */
    {
        int fwd   = (c->forwardmove > 0 ? 1 : 0) - (c->forwardmove < 0 ? 1 : 0);
        int right = (c->rightmove   > 0 ? 1 : 0) - (c->rightmove   < 0 ? 1 : 0);
        double yd, yaw_rad, cf, sf;

        right = -right;                                    /* flip_strafe_x = 1 */

        yd = (c->yaw >= 32768) ? ((double)c->yaw - 65536.0) : (double)c->yaw;
        yd = yd * 360.0 / 65536.0;
        yaw_rad = (yd * CODOL_DIR_BIAS_SCALE + CODOL_DIR_BIAS_DEG) * 3.14159265358979 / 180.0;

        norm = (fwd != 0 && right != 0) ? CODOL_HALF_DIAG : 1.0f;
        cf = cos(yaw_rad); sf = sin(yaw_rad);
        /* ★ 冲刺: IW4X CMD_BUTTON_SPRINT = 1<<1 = 0x2。
         *   实测(2026-10-22): 之前没有 SPRINT 概念，Shift 的按键位被当成切枪信号。
         *   这里只管速度; 切枪已在 equipment.c 加了合法性校验。 */
        {
            float speed = CODOL_MOVE_SPEED;
            if ((c->buttons & CODOL_BTN_SPRINT) && fwd > 0)
                speed = CODOL_SPRINT_SPEED;
            p->vx = (float)((cf * fwd + sf * right) * speed * norm);
            p->vy = (float)((sf * fwd - cf * right) * speed * norm);
        }
        p->vy = -p->vy;                                    /* flip_move_y = 1 */
    }
    /* 开镜(照参照实现): aiming = buttons & 0x800;
     *   aim_fraction += (+−1) * ads_per_sec * dt, 钳住 [0,1]
     * → 快照 index 41 = WeaponPositionFraction, index 20 = PmFlags(aiming ? 0x10 : 0) */
    p->aiming = ((c->buttons & CODOL_BTN_ADS) != 0);
    {
        float step = (p->aiming ? 1.0f : -1.0f) * CODOL_ADS_PER_SEC * dt;
        p->aim_fraction += step;
        if (p->aim_fraction > 1.0f) p->aim_fraction = 1.0f;
        if (p->aim_fraction < 0.0f) p->aim_fraction = 0.0f;
    }

    /* 垂直: 真实重力 + 地面/障碍 trace(照 CoD4x PM_SlideMove 的落地判定顺序)。
     * 先水平位移(逐轴 trace), 再垂直 trace; 落地时把 z 钳到接触点并清空 vz。 */
    {
        codol_collision_trace_t tr;
        codol_collision_box_t dynamic_boxes[CODOL_MAX_ENTITIES];
        int dynamic_count = build_dynamic_boxes(world, skip_entity, dynamic_boxes, CODOL_MAX_ENTITIES);
        float start[3], end[3], mins[3] = {-15.0f, -15.0f, 0.0f}, maxs[3] = {15.0f, 15.0f, 70.0f};

        /* 水平 X */
        start[0] = p->x; start[1] = p->y; start[2] = p->z;
        end[0] = p->x + p->vx * dt; end[1] = p->y; end[2] = p->z;
        codol_collision_box_trace_ex(&tr, start, end, mins, maxs,
                                     CODOL_CONTENTS_PLAYERCLIP | CODOL_CONTENTS_SOLID,
                                     skip_entity, dynamic_boxes, dynamic_count);
        p->x = tr.end_pos[0];

        /* 水平 Y */
        start[0] = p->x; start[1] = p->y; start[2] = p->z;
        end[0] = p->x; end[1] = p->y + p->vy * dt; end[2] = p->z;
        codol_collision_box_trace_ex(&tr, start, end, mins, maxs,
                                     CODOL_CONTENTS_PLAYERCLIP | CODOL_CONTENTS_SOLID,
                                     skip_entity, dynamic_boxes, dynamic_count);
        p->y = tr.end_pos[1];

        /* 垂直: 重力积分后向下 trace */
        p->vz -= p->gravity * dt;
        start[0] = p->x; start[1] = p->y; start[2] = p->z;
        end[0] = p->x; end[1] = p->y; end[2] = p->z + p->vz * dt;
        codol_collision_box_trace_ex(&tr, start, end, mins, maxs,
                                     CODOL_CONTENTS_SOLID,
                                     skip_entity, dynamic_boxes, dynamic_count);
        if (tr.fraction < 1.0f && tr.normal[2] > 0.5f) {
            p->z = tr.end_pos[2];
            p->vz = 0.0f;
            p->on_ground = true;
        } else {
            p->z = tr.end_pos[2];
            p->on_ground = false;
        }
    }
}

void codol_player_apply_list(codol_player_t *p, const codol_usercmd_list_t *l, float dt)
{
    int i;
    if (!p || !l) return;
    for (i = 0; i < l->count; i++)
        codol_player_apply_usercmd(p, &l->cmds[i], dt);
}

void codol_player_apply_usercmd(codol_player_t *p, const codol_usercmd_t *c, float dt)
{
    codol_player_move_in_world(p, c, dt, NULL, -1);
}
