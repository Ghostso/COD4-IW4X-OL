#include "codol_world.h"
#include "codol_platform.h"
#include "codol_entity.h"
#include "codol_movement.h"
#include "codol_collision.h"
#include "codol_gamemode.h"
#include "codol_player.h"
#include "codol_mapents_coop_train.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

/* ★ 地图实体表(由 tools/gen_mapents_inc.py 从 _map_extract/coop_train_entities.txt 生成)。
 *   334 条: 333 个静态道具(script_model/script_struct/script_origin —— 靶场的轮胎墙之类)
 *   + 1 个 actor_ally_hero_quartermaster_so(这张图上唯一的 actor)。
 *   script_brushmodel 不在这里: 它们已经是 clipmap 碰撞(见 collision.c)。 */
const codol_mapent_t codol_mapents_coop_train[] = {
#include "codol_mapents_coop_train.inc"
};

/* 把地图实体生成进世界。返回生成条数。
 * ★ 2026-10-25: 在此之前世界里**只有玩家**(bind_world 只生成玩家), 地图上有什么
 *   服务端完全不知道 —— 这个函数就是补上"地图的实体名册"。 */
int codol_world_spawn_map_entities(codol_world_t *world)
{
    int i, props = 0, actors = 0, skipped = 0;
    if (!world) return 0;
    for (i = 0; i < CODOL_MAPENTS_COOP_TRAIN_COUNT; i++) {
        const codol_mapent_t *me = &codol_mapents_coop_train[i];
        if (me->kind == 1) {                       /* 静态道具 */
            codol_entity_state_t *e = codol_entity_alloc(world, CODOL_ET_GENERAL);
            if (!e) { skipped++; continue; }
            e->pos.origin[0] = me->x;
            e->pos.origin[1] = me->y;
            e->pos.origin[2] = me->z;
            e->apos.angles[1] = me->yaw;
            e->health = 0;                         /* 静态道具不参与伤害 */
            /* 实体表只给 origin, 没有 mins/maxs; 用保守的"人形大小"占位,
             * 真正的几何在 clipmap(这些道具本身多是可穿过的装饰)。 */
            e->mins[0] = -16.0f; e->mins[1] = -16.0f; e->mins[2] = 0.0f;
            e->maxs[0] =  16.0f; e->maxs[1] =  16.0f; e->maxs[2] = 64.0f;
            props++;
        } else if (me->kind == 2) {                /* actor */
            if (codol_entity_spawn_actor(world, -1, me->x, me->y, me->z, 100, 0) == CODOL_OK)
                actors++;
            else
                skipped++;
        }
    }
    CODOL_LOG_INFO("world \"%s\" map entities spawned: %d props + %d actors (skip %d)",
                   world->map_name, props, actors, skipped);
    return props + actors;
}
static codol_mode_t *world_mode(codol_world_t *world) { return (codol_mode_t *)world->gamemode; }
codol_result_t codol_world_init(codol_world_t *world, const char *map_name)
{
    if (!world || !map_name) return CODOL_ERR_INVALID_ARG;
    memset(world, 0, sizeof(*world));
    world->state = CODOL_WORLD_STATE_LOADING;
    snprintf(world->map_name, sizeof(world->map_name), "%s", map_name);
    world->gravity = 800.0f;
    world->frame_number = 0;
    world->start_time_us = codol_platform_time_us();
    codol_entity_table_init(world);
    codol_replication_init(world);
    world->clipmap = (void *)codol_static_boxes;
    world->map_ents = (void *)codol_static_boxes;
    world->gamemode = calloc(1, sizeof(codol_mode_t));
    if (!world->gamemode) return CODOL_ERR_NO_MEMORY;
    {
        codol_mode_config_t mode_config;
        memset(&mode_config, 0, sizeof(mode_config));
        snprintf(mode_config.map_name, sizeof(mode_config.map_name), "%s", map_name);
        snprintf(mode_config.gametype, sizeof(mode_config.gametype), "dm");
        mode_config.score_limit = 30;
        mode_config.time_limit_ms = 600000;
        mode_config.respawn_delay_ms = 3000;
        codol_mode_init(world_mode(world), &mode_config);
    }
    return CODOL_OK;
}
codol_result_t codol_world_load_assets(codol_world_t *world)
{
    if (!world) return CODOL_ERR_INVALID_ARG;
    if (world->state != CODOL_WORLD_STATE_LOADING) return CODOL_ERR_STATE;
    if (!world->clipmap) world->clipmap = (void *)codol_static_boxes;
    if (!world->map_ents) world->map_ents = (void *)codol_static_boxes;
    world->state = CODOL_WORLD_STATE_READY;
#ifdef CODOL_PLACEHOLDER_WORLD
    /* 对照实验: 退回 Phase 7 之前的 placeholder 世界 */
    CODOL_LOG_INFO("world \"%s\" assets loaded (placeholder)", world->map_name);
#else
    CODOL_LOG_INFO("world \"%s\" assets loaded (%d clip volumes)", world->map_name, codol_static_box_count);
#endif
    return CODOL_OK;
}
codol_result_t codol_world_step(codol_world_t *world, const codol_usercmd_t *commands, size_t command_count, codol_frame_t *frame)
{
    if (!world || !frame) return CODOL_ERR_INVALID_ARG;
    if (world->state != CODOL_WORLD_STATE_READY && world->state != CODOL_WORLD_STATE_RUNNING) return CODOL_ERR_STATE;
    world->state = CODOL_WORLD_STATE_RUNNING;
    world->frame_number++;
    frame->frame_number = world->frame_number;
    frame->server_time = codol_platform_time_us() - world->start_time_us;
    if (commands) for (size_t i=0;i<command_count;i++) if (commands[i].time>0 && (int)i<CODOL_MAX_CLIENTS) codol_movement_process_usercmd(world,(int)i,&commands[i]);
    if (world_mode(world)) codol_mode_tick(world_mode(world),16);
    frame->num_entities = codol_entity_count_in_use(world);
    frame->first_entity = 0;
    codol_replication_commit_frame(world,frame);
    return CODOL_OK;
}
codol_result_t codol_world_spawn_player(codol_world_t *world, int client_num)
{
    codol_player_state_t *ps; codol_entity_state_t *ent; codol_mode_t *mode;
    codol_player_t player;
    if (!world || client_num < 0 || client_num >= CODOL_MAX_CLIENTS) return CODOL_ERR_INVALID_ARG;
    ps = codol_player_get(world,client_num); if (!ps) return CODOL_ERR_NO_MEMORY;
    for (int i = 0; i < CODOL_MAX_ENTITIES; ++i) {
        if (world->entities[i].in_use &&
            world->entities[i].type == CODOL_ET_PLAYER &&
            world->entities[i].owner == client_num)
            codol_entity_free(world, i);
    }
    memset(ps,0,sizeof(*ps)); ps->client_num=client_num; ps->health=100; ps->max_health=100; ps->team=client_num&1;
    ent = codol_entity_alloc(world,CODOL_ET_PLAYER); if (!ent) return CODOL_ERR_NO_MEMORY;
    ent->mins[0] = -15.0f; ent->mins[1] = -15.0f; ent->mins[2] = 0.0f;
    ent->maxs[0] =  15.0f; ent->maxs[1] =  15.0f; ent->maxs[2] = 70.0f;
    ent->owner=client_num; ent->health=100; ent->pos.origin[0]=48.0f; ent->pos.origin[1]=-572.0f; ent->pos.origin[2]=-116.0f;
    codol_player_init(&player, ent->pos.origin[0], ent->pos.origin[1], ent->pos.origin[2]);
    ps->origin[0] = player.x;
    ps->origin[1] = player.y;
    ps->origin[2] = player.z;
    ps->velocity[0] = player.vx;
    ps->velocity[1] = player.vy;
    ps->velocity[2] = player.vz;
    mode=world_mode(world); if (mode) codol_mode_join(mode,client_num);
    return CODOL_OK;
}
void codol_world_shutdown(codol_world_t *world)
{
    if (!world) return;
    world->state=CODOL_WORLD_STATE_SHUTDOWN;
    free(world->gamemode);
    world->gamemode=NULL;
    CODOL_LOG_INFO("world \"%s\" shut down",world->map_name);
}


