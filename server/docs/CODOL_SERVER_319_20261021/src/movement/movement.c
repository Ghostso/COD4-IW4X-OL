#include "codol_movement.h"
#include "codol_world.h"
#include "codol_entity.h"
#include "codol_collision.h"
#include "codol_player.h"
#include <string.h>
#include <math.h>

void codol_pmove_constants_init(codol_pmove_constants_t *c)
{
    if (!c) return;
    memset(c, 0, sizeof(*c));

    c->mins[0] = -15.0f; c->mins[1] = -15.0f; c->mins[2] = 0.0f;
    c->maxs[0] =  15.0f; c->maxs[1] =  15.0f; c->maxs[2] = 70.0f;

    c->eye_offset[0] = 0.0f; c->eye_offset[1] = 0.0f; c->eye_offset[2] = 60.0f;

    c->gravity        = 800.0f;
    c->step_size      = 18.0f;
    c->friction       = 6.0f;
    c->accelerate     = 10.0f;
    c->air_accelerate = 1.0f;
    c->max_speed      = 320.0f;
    c->jump_velocity  = 270.0f;
}

static void apply_friction(codol_pmove_t *pm, float dt)
{
    if (!pm || !pm->ps) return;
    float *vel = pm->ps->velocity;
    float speed = sqrtf(vel[0] * vel[0] + vel[1] * vel[1] + vel[2] * vel[2]);
    if (speed < 0.1f) {
        vel[0] = vel[1] = vel[2] = 0.0f;
        return;
    }
    float drop = speed * pm->constants.friction * dt;
    float new_speed = speed - drop;
    if (new_speed < 0.0f) new_speed = 0.0f;
    float scale = new_speed / speed;
    vel[0] *= scale;
    vel[1] *= scale;
    vel[2] *= scale;
}

static void apply_acceleration(codol_pmove_t *pm, float dt)
{
    if (!pm || !pm->ps) return;
    float forward[3] = {0, 0, 0}, right[3] = {0, 0, 0};
    float yaw = (float)pm->cmd.yaw * (3.14159265f / 32768.0f);
    forward[0] = cosf(yaw); forward[1] = sinf(yaw);
    right[0] = -sinf(yaw);  right[1] = cosf(yaw);

    float accel = pm->walking ? pm->constants.accelerate : pm->constants.air_accelerate;
    float wish_speed = pm->constants.max_speed;

    float fwd = (float)pm->cmd.forwardmove / 127.0f;
    float rgt = (float)pm->cmd.rightmove / 127.0f;

    pm->ps->velocity[0] += (forward[0] * fwd + right[0] * rgt) * accel * wish_speed * dt;
    pm->ps->velocity[1] += (forward[1] * fwd + right[1] * rgt) * accel * wish_speed * dt;
}

static void apply_gravity(codol_pmove_t *pm, float dt)
{
    if (!pm || !pm->ps) return;
    pm->ps->velocity[2] -= pm->constants.gravity * dt;
}


codol_result_t codol_pmove_single(codol_pmove_t *pm)
{
    if (!pm || !pm->ps) return CODOL_ERR_INVALID_ARG;

    float dt = 1.0f / (float)CODOL_SERVER_TICK_HZ;

    apply_friction(pm, dt);
    apply_acceleration(pm, dt);
    if (pm->cmd.buttons & 0x01) {
        if (pm->walking) {
            pm->ps->velocity[2] = pm->constants.jump_velocity;
            pm->walking = false;
        }
    }
    if (!pm->walking) apply_gravity(pm, dt);
    return CODOL_OK;
}

codol_result_t codol_movement_process_usercmd(codol_world_t *world, int client_num,
                                               const codol_usercmd_t *cmd)
{
    return codol_movement_process_usercmd_dt(world, client_num, cmd,
                                             1.0f / (float)CODOL_SERVER_TICK_HZ);
}

/* ★★ dt 必须来自**真实命令间隔**, 不是固定 tick 周期。
 *   实测(ONCE_20261026_215228): 相邻 usercmd 的 time 差是 112ms 甚至 12000ms,
 *   而这里原先写死 1/128=7.8ms ⇒ 玩家按 W 走 12 秒, 服务端只积分了 7.8ms,
 *   速度只有真实的 1/1500 ⇒ 服务端算出的位置完全不可信, 每帧发出去只会把
 *   客户端越推越远(实测飘到 1260,-1087, 出生点是 48,-572, 即"穿墙飘走")。
 */
codol_result_t codol_movement_process_usercmd_dt(codol_world_t *world, int client_num,
                                                 const codol_usercmd_t *cmd,
                                                 float dt)
{
    codol_player_t player;
    codol_player_state_t *ps;
    codol_entity_state_t *entity;
    codol_pmove_constants_t constants;
    if (!world || !cmd || client_num < 0 || client_num >= CODOL_MAX_CLIENTS)
        return CODOL_ERR_INVALID_ARG;
    if (!(dt > 0.0f) || dt > 0.5f) dt = 1.0f / (float)CODOL_SERVER_TICK_HZ;
    ps = codol_player_get(world, client_num);
    entity = codol_entity_get(world, client_num);
    if (!ps) return CODOL_ERR_INVALID_ARG;
    memset(&player, 0, sizeof(player));
    player.x = ps->origin[0];
    player.y = ps->origin[1];
    player.z = ps->origin[2];
    player.vx = ps->velocity[0];
    player.vy = ps->velocity[1];
    player.vz = ps->velocity[2];
    player.yaw = (uint16_t)cmd->yaw;
    player.buttons = cmd->buttons;
    player.on_ground = true;
    codol_pmove_constants_init(&constants);
    player.gravity = constants.gravity;
    codol_player_move_in_world(&player, cmd, dt,
                               world, entity ? entity->number : -1);
    ps->origin[0] = player.x;
    ps->origin[1] = player.y;
    ps->origin[2] = player.z;
    ps->velocity[0] = player.vx;
    ps->velocity[1] = player.vy;
    ps->velocity[2] = player.vz;
    if (entity) {
        memcpy(entity->pos.origin, ps->origin, sizeof(entity->pos.origin));
        memcpy(entity->pos.velocity, ps->velocity, sizeof(entity->pos.velocity));
    }
    return CODOL_OK;
}

codol_trace_t codol_movement_trace(const codol_world_t *world,
                                    const float start[3], const float end[3],
                                    const float mins[3], const float maxs[3],
                                    int skip_entity, int content_mask)
{
    codol_collision_trace_t ct;
    codol_trace_t tr;
    memset(&tr, 0, sizeof(tr));
    tr.fraction = 1.0f;
    tr.end_pos[0] = end[0];
    tr.end_pos[1] = end[1];
    tr.end_pos[2] = end[2];
    tr.entity_num = -1;
    if (!start || !end || !mins || !maxs) return tr;
    {
        codol_collision_box_t trace_boxes[CODOL_MAX_ENTITIES];
        int trace_count = 0, i;
        if (world) {
            for (i = 0; i < CODOL_MAX_ENTITIES && trace_count < CODOL_MAX_ENTITIES; ++i) {
                const codol_entity_state_t *e = &world->entities[i];
                float half_x, half_y, height;
                if (!e->in_use || i == skip_entity || e->type == CODOL_ET_MISSILE || e->type == CODOL_ET_CORPSE) continue;
                half_x = (e->maxs[0] > e->mins[0]) ? (e->maxs[0] - e->mins[0]) * 0.5f : 15.0f;
                half_y = (e->maxs[1] > e->mins[1]) ? (e->maxs[1] - e->mins[1]) * 0.5f : 15.0f;
                height = (e->maxs[2] > e->mins[2]) ? e->maxs[2] - e->mins[2] : 70.0f;
                trace_boxes[trace_count].mins[0] = e->pos.origin[0] - half_x;
                trace_boxes[trace_count].mins[1] = e->pos.origin[1] - half_y;
                trace_boxes[trace_count].mins[2] = e->pos.origin[2];
                trace_boxes[trace_count].maxs[0] = e->pos.origin[0] + half_x;
                trace_boxes[trace_count].maxs[1] = e->pos.origin[1] + half_y;
                trace_boxes[trace_count].maxs[2] = e->pos.origin[2] + height;
                trace_boxes[trace_count].contents = CODOL_CONTENTS_SOLID;
                trace_boxes[trace_count].entity_num = e->number;
                ++trace_count;
            }
        }
        codol_collision_box_trace_ex(&ct, start, end, mins, maxs, content_mask,
                                     skip_entity, trace_boxes, trace_count);
    }
    tr.fraction = ct.fraction;
    memcpy(tr.end_pos, ct.end_pos, sizeof(tr.end_pos));
    memcpy(tr.normal, ct.normal, sizeof(tr.normal));
    tr.startsolid = ct.startsolid;
    tr.allsolid = ct.allsolid;
    tr.entity_num = ct.entity_num;
    return tr;
}
