/* 探针: 验证"世界活着 -> 有实体 -> 能算伤害"这条链。
 *
 * 动机(2026-10-25): 战斗服的 svc->world 一直是 NULL(bind_world 从未调用),
 * 导致 ensure_damage_target()/apply_test_hit() 第一句就 return, HIT/DAMAGE 永远为 0。
 * 本探针把 apply_test_hit() 依赖的**每一步原样**跑一遍, 离线证明这条路是通的。
 */
#include "codol_world.h"
#include "codol_entity.h"
#include "codol_combat.h"
#include "codol_weapondefs.h"
#include "codol_collision.h"
#include "codol_movement.h"
#include <stdio.h>
#include <string.h>

static int fails;

int main(void)
{
    static codol_world_t w;          /* 与 main.c 一样放静态区, 结构很大 */
    codol_weapondef_t *weapon;
    codol_damage_policy_t policy;
    codol_damage_result_t res;
    int i, target = -1, spawned = 0;

    /* ① 世界初始化 + 加载资产(等价于 main.c 的两步) */
    if (codol_world_init(&w, "mp_firingrange") != CODOL_OK) {
        printf("FAIL world_init\n"); return 1;
    }
    if (codol_world_load_assets(&w) != CODOL_OK) {
        printf("FAIL world_load_assets\n"); return 1;
    }
    printf("ok   世界          init + load_assets 通过\n");

    /* ② 生成玩家 —— 这正是 bind_world 内部做的事 */
    if (codol_world_spawn_player(&w, 0) != CODOL_OK) {
        printf("FAIL spawn_player\n"); fails++;
    } else {
        const codol_player_state_t *ps = codol_player_get(&w, 0);
        if (ps) printf("ok   玩家实体      origin=(%.1f,%.1f,%.1f)\n",
                       ps->origin[0], ps->origin[1], ps->origin[2]);
        else { printf("FAIL player_get 为空\n"); fails++; }
    }

    /* ③ 生成 actor —— 与 ensure_damage_target() 的第一个 codol_entity_spawn_actor 同参 */
    if (codol_entity_spawn_actor(&w, 0, 0.0f, 0.0f, -116.0f, 100, 0) != CODOL_OK) {
        printf("FAIL spawn_actor\n"); fails++;
    } else {
        for (i = 0; i < CODOL_MAX_ENTITIES; ++i) {
            codol_entity_state_t *e = &w.entities[i];
            if (e->in_use && e->type == CODOL_ET_ACTOR) {
                e->owner = 1001;                     /* ensure_damage_target 的标记法 */
                e->mins[0] = -15.0f; e->mins[1] = -15.0f; e->mins[2] = 0.0f;
                e->maxs[0] = 15.0f;  e->maxs[1] = 15.0f;  e->maxs[2] = 70.0f;
                target = e->number;
                spawned++;
            }
        }
        if (target < 0) { printf("FAIL actor 未出现在实体表\n"); fails++; }
        else printf("ok   靶子实体      actor number=%d (世界中 in_use 的 actor 数=%d)\n",
                    target, spawned);
    }

    /* ④ 武器定义查找 —— apply_test_hit 里用的就是这个名字 */
    weapon = (codol_weapondef_t *)codol_weapondef_find("m4a1tech_mp");
    if (!weapon) { printf("FAIL weapondef_find(m4a1tech_mp)\n"); fails++; }
    else printf("ok   武器定义      m4a1tech_mp damage=%d 射程=%.0f..%.0f\n",
                weapon->damage, weapon->max_damage_range, weapon->min_damage_range);

    /* ⑤ 伤害结算 —— apply_test_hit 的核心调用 */
    if (target >= 0 && weapon) {
        codol_damage_policy_default(&policy);
        if (codol_damage_apply(&w, target, weapon, 20.0f,
                               CODOL_HITLOC_TORSO_UPPER, &policy, &res) != CODOL_OK) {
            printf("FAIL damage_apply\n"); fails++;
        } else {
            printf("ok   伤害结算      target=%d damage=%d health %d->%d killed=%d\n",
                   target, res.damage, res.target_health_before,
                   res.target_health_after, (int)res.killed);
            if (res.damage <= 0) { printf("FAIL 伤害为 0, 打不出 HIT\n"); fails++; }
        }
    }

    /* ⑥ 世界推进一帧(带 0 条 usercmd, 与 main.c 当前调用一致) */
    {
        codol_frame_t frame;
        memset(&frame, 0, sizeof frame);
        if (codol_world_step(&w, NULL, 0, &frame) != CODOL_OK) {
            printf("FAIL world_step\n"); fails++;
        } else {
            printf("ok   世界推进      num_entities=%d\n", frame.num_entities);
        }
    }

    /* ⑦ 真碰撞移动: 喂 usercmd 进世界, 看服务端玩家是否真的移动。
     *   这正是 codol_battle_service_apply_usercmd() 在 svc->world 非空时走的路径
     *   (codol_movement_process_usercmd), bind_world 之前它永远走 else 的假积分。 */
    {
        const codol_player_state_t *ps0 = codol_player_get(&w, 0);
        float x0 = ps0 ? ps0->origin[0] : 0.0f, y0 = ps0 ? ps0->origin[1] : 0.0f;
        uint32_t t = 2000;
        int k, moved = 0;
        for (k = 0; k < 60; k++) {
            codol_usercmd_t cmd;
            memset(&cmd, 0, sizeof cmd);
            cmd.time = t; t += 16;
            cmd.forwardmove = 1;                      /* 一直朝前走 */
            cmd.yaw = 0;
            if (codol_movement_process_usercmd(&w, 0, &cmd) == CODOL_OK) moved++;
        }
        {
            const codol_player_state_t *ps = codol_player_get(&w, 0);
            if (!ps) { printf("FAIL 移动后取不到玩家状态\n"); fails++; }
            else {
                float dx = ps->origin[0] - x0, dy = ps->origin[1] - y0;
                float d = (dx < 0 ? -dx : dx) + (dy < 0 ? -dy : dy);
                printf("ok   真碰撞移动  %d 次 usercmd 成功; 起(%.1f,%.1f) -> 终(%.1f,%.1f,%.1f) 位移=%.1f\n",
                       moved, x0, y0, ps->origin[0], ps->origin[1], ps->origin[2], d);
                if (d < 1.0f) { printf("FAIL 喂了 60 条 usercmd 位置却没动 -> 仍走假积分?\n"); fails++; }
                if (ps->origin[2] < -400.0f || ps->origin[2] > 200.0f) {
                    printf("FAIL z=%.1f 异常(穿地/飞天)\n", ps->origin[2]); fails++;
                }
            }
        }
    }

    /* ⑧ 碰撞数据本身生效: 朝 clipmap 里第一块 brush 打一条 trace。
     *   盒 = {{-832,-176,-105},{-816,-16,-9}}(见 codol_clipmap_coop_train.inc 第 1 条)。 */
    {
        codol_collision_trace_t tr;
        float start[3] = { -780.0f, -96.0f, -50.0f };
        float end[3]   = { -900.0f, -96.0f, -50.0f };   /* 沿 -x 穿过 x∈[-832,-816] 那块 */
        float mins[3]  = { -1.0f, -1.0f, -1.0f };
        float maxs[3]  = {  1.0f,  1.0f,  1.0f };
        memset(&tr, 0, sizeof tr);
        codol_collision_box_trace(&tr, start, end, mins, maxs, CODOL_CONTENTS_MASK_ALL);
        printf("ok   碰撞 trace   fraction=%.3f normal=(%.2f,%.2f,%.2f) end=(%.1f,%.1f,%.1f)\n",
               tr.fraction, tr.normal[0], tr.normal[1], tr.normal[2],
               tr.end_pos[0], tr.end_pos[1], tr.end_pos[2]);
        if (tr.fraction >= 1.0f) {
            printf("FAIL 该方向应撞到 brush 却 fraction=1 -> clipmap 没生效\n"); fails++;
        }
    }

    /* ⑨ 地图实体表落地: 333 个静态道具 + 1 个 actor(世界原有的合成 actor 另算) */
    {
        int n = codol_world_spawn_map_entities(&w);
        int generals = 0, actors = 0, k, map_actor = -1;
        float ax = 0, ay = 0, az = 0;
        for (k = 0; k < CODOL_MAX_ENTITIES; ++k) {
            const codol_entity_state_t *e = &w.entities[k];
            if (!e->in_use) continue;
            if (e->type == CODOL_ET_GENERAL) generals++;
            else if (e->type == CODOL_ET_ACTOR) {
                actors++;
                if (e->owner == -1) { map_actor = e->number; ax = e->pos.origin[0]; ay = e->pos.origin[1]; az = e->pos.origin[2]; }
            }
        }
        printf("ok   地图实体    spawn 返回 %d; 世界内 GENERAL=%d ACTOR=%d\n", n, generals, actors);
        if (generals != 333) { printf("FAIL 静态道具数 %d != 333\n", generals); fails++; }
        if (map_actor < 0) { printf("FAIL 地图自带 actor 没生成\n"); fails++; }
        else printf("ok   地图 actor  number=%d origin=(%.1f,%.1f,%.1f) 血量=%d\n",
                    map_actor, ax, ay, az, w.entities[map_actor].health);

        /* 表里第一条道具是 (-780,-48,-126) 的轮胎墙, 核对真的落在这个坐标上 */
        {
            int found = 0;
            for (k = 0; k < CODOL_MAX_ENTITIES; ++k) {
                const codol_entity_state_t *e = &w.entities[k];
                if (e->in_use && e->type == CODOL_ET_GENERAL &&
                    e->pos.origin[0] > -780.5f && e->pos.origin[0] < -779.5f &&
                    e->pos.origin[1] > -48.5f  && e->pos.origin[1] < -47.5f) { found = 1; break; }
            }
            if (!found) { printf("FAIL 表里第一条道具(-780,-48,-126)没落地\n"); fails++; }
            else printf("ok   坐标核对    表首道具 (-780,-48) 已落地\n");
        }
    }

    codol_world_shutdown(&w);
    printf("\n%s (%d)\n", fails ? "FAILED" : "ALL PASSED", fails);
    return fails ? 1 : 0;
}
