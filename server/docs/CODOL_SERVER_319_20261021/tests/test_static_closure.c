#include "codol_types.h"
#include "codol_weapondefs.h"
#include "codol_entity.h"
#include "codol_combat.h"
#include "codol_projectile.h"
#include "codol_gamemode.h"
#include "codol_world.h"
#include "codol_collision.h"
#include "codol_movement.h"
#include "codol_player.h"
#include "codol_battle_service.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
    static codol_world_t world;
    codol_entity_state_t *target;
    
    codol_weapondef_t weapon;
    codol_damage_policy_t policy;
    codol_damage_result_t damage_result;
    codol_projectile_t projectile;
    codol_projectile_result_t projectile_result;
    codol_mode_config_t mode_config;
    codol_mode_t mode;
    

    memset(&world, 0, sizeof(world));
    world.state = CODOL_WORLD_STATE_READY;
    assert(codol_entity_table_init(&world) == CODOL_OK);
    target = codol_entity_alloc(&world, CODOL_ET_PLAYER);
    assert(target != NULL);
    target->health = 100;
    target->in_use = true;
    target->pos.origin[0] = 10.0f;
    target->pos.origin[1] = 0.0f;
    target->pos.origin[2] = 0.0f;

    memset(&weapon, 0, sizeof(weapon));
    weapon.damage = 10;
    weapon.player_damage = 10;
    weapon.min_damage = 10;
    weapon.min_player_damage = 10;
    weapon.damage_tiers[0] = 10;
    weapon.damage_ranges[0] = 1000.0f;
    weapon.location_damage_multipliers[CODOL_HITLOC_HEAD] = 1.5f;
    codol_damage_policy_default(&policy);
    assert(codol_damage_apply(&world, target->number, &weapon, 100.0f,
                              CODOL_HITLOC_HEAD, &policy, &damage_result) == CODOL_OK);
    assert(damage_result.damage == 15);
    assert(damage_result.target_health_after == 85);

    policy.armor_scale = 0.5f;
    assert(codol_damage_apply(&world, target->number, &weapon, 100.0f,
                              CODOL_HITLOC_HEAD, &policy, &damage_result) == CODOL_OK);
    assert(damage_result.damage == 8);
    assert(damage_result.target_health_after == 77);

    target->health = 100;
    policy.armor_scale = 1.0f;
    assert(codol_damage_apply(&world, target->number, &weapon, 100.0f,
                              CODOL_HITLOC_SHIELD, &policy, &damage_result) == CODOL_OK);
    assert(damage_result.blocked_by_shield && target->health == 100);

    codol_projectile_default(&projectile);
    
    assert(codol_projectile_spawn(&world, &projectile, 0, CODOL_PROJ_EXPLOSION_FRAG,
                                  0.0f, 0.0f, 0.0f) == CODOL_OK);
    projectile.inner_radius = 50.0f;
    projectile.outer_radius = 100.0f;
    projectile.inner_damage = 40.0f;
    projectile.outer_damage = 10.0f;
    projectile.fuse_ms = 100.0f;
    target->health = 100;
    assert(codol_projectile_step(&world, &projectile, 101.0f, &projectile_result) == CODOL_OK);
    assert(projectile_result.exploded);
    assert(projectile_result.hit_count == 1);
    assert(target->health < 100);

    memset(&mode_config, 0, sizeof(mode_config));
    mode_config.score_limit = 1;
    mode_config.respawn_delay_ms = 10;
    codol_mode_init(&mode, &mode_config);
    assert(codol_mode_join(&mode, 0) == CODOL_OK);
    assert(codol_mode_player_killed(&mode, 0, 1, 0) == CODOL_OK);
    assert(codol_mode_is_match_over(&mode));

    /* Static world/mode lifecycle: init allocates the mode, load enables step,
     * spawn joins the mode, and shutdown releases the allocation. */
    {
        static codol_world_t mode_world;
        codol_frame_t frame;
        assert(codol_world_init(&mode_world, "coop_train") == CODOL_OK);
        assert(mode_world.gamemode != NULL);
        assert(codol_world_load_assets(&mode_world) == CODOL_OK);
        assert(codol_world_spawn_player(&mode_world, 0) == CODOL_OK);
        assert(codol_entity_count_in_use(&mode_world) == 1);
        assert(mode_world.players[0].origin[0] == 48.0f);
        assert(mode_world.entities[0].pos.origin[2] == -116.0f);
        assert(((codol_mode_t *)mode_world.gamemode)->state == CODOL_MODE_ACTIVE);
        assert(codol_world_spawn_player(&mode_world, 0) == CODOL_OK);
        assert(codol_entity_count_in_use(&mode_world) == 1);
        memset(&frame, 0, sizeof(frame));
        assert(codol_world_step(&mode_world, NULL, 0, &frame) == CODOL_OK);
        assert(frame.num_entities == 1);
        codol_world_shutdown(&mode_world);
        assert(mode_world.gamemode == NULL);
    }

    /* All declared static entity factories allocate distinct live entities
     * and free back to zero. */
    {
        int before = codol_entity_count_in_use(&world);
        codol_entity_state_t *actor, *vehicle, *turret, *loot, *objective;
        assert(codol_entity_spawn_actor(&world, 0, 1, 2, 3, 100, 7) == CODOL_OK);
        assert(codol_entity_spawn_vehicle(&world, 0, 4, 5, 6, 200, 8) == CODOL_OK);
        assert(codol_entity_spawn_turret(&world, 0, 7, 8, 9, 150, 9) == CODOL_OK);
        assert(codol_entity_spawn_loot(&world, 0, 10, 11, 12, 13) == CODOL_OK);
        assert(codol_entity_spawn_objective(&world, 13, 14, 15, 16) == CODOL_OK);
        assert(codol_entity_count_in_use(&world) == before + 5);
        actor = &world.entities[before];
        vehicle = &world.entities[before + 1];
        turret = &world.entities[before + 2];
        loot = &world.entities[before + 3];
        objective = &world.entities[before + 4];
        assert(actor->type == CODOL_ET_ACTOR && vehicle->type == CODOL_ET_VEHICLE);
        assert(turret->type == CODOL_ET_TURRET && loot->type == CODOL_ET_LOOT);
        assert(objective->type == CODOL_ET_OBJECTIVE);
        codol_entity_free(&world, actor->number);
        codol_entity_free(&world, vehicle->number);
        codol_entity_free(&world, turret->number);
        codol_entity_free(&world, loot->number);
        codol_entity_free(&world, objective->number);
        assert(codol_entity_count_in_use(&world) == before);
    }

    /* Dynamic hull trace must block and report the nearest surface. */
    {
        codol_collision_trace_t ct;
        codol_collision_box_t hull;
        float start[3] = {-10.0f, 0.0f, 0.0f};
        float end[3] = {10.0f, 0.0f, 0.0f};
        float mins[3] = {-1.0f, -1.0f, -1.0f};
        float maxs[3] = {1.0f, 1.0f, 1.0f};
        hull.mins[0] = -0.5f; hull.mins[1] = -2.0f; hull.mins[2] = -2.0f;
        hull.maxs[0] = 0.5f; hull.maxs[1] = 2.0f; hull.maxs[2] = 2.0f;
        hull.contents = CODOL_CONTENTS_SOLID;
        hull.entity_num = 77;
        codol_collision_box_trace_ex(&ct, start, end, mins, maxs,
                                     CODOL_CONTENTS_SOLID, -1, &hull, 1);
        assert(ct.fraction > 0.0f && ct.fraction < 1.0f);
        assert(ct.normal[0] < -0.9f);
        assert(ct.entity_num == 77);
    }

    /* World-aware player movement uses the static clip set and collides with
     * an entity hull instead of passing through it. */
    {
        static codol_world_t move_world;
        codol_player_t player;
        codol_usercmd_t cmd;
        codol_trace_t mt;
        float start[3] = {-10.0f, 0.0f, 0.0f};
        float end[3] = {10.0f, 0.0f, 0.0f};
        float mins[3] = {-1.0f, -1.0f, -1.0f};
        float maxs[3] = {1.0f, 1.0f, 1.0f};
        assert(codol_world_init(&move_world, "coop_train") == CODOL_OK);
        assert(codol_world_spawn_player(&move_world, 1) == CODOL_OK);
        {
            int i;
            codol_entity_state_t *spawned = NULL;
            for (i = 0; i < CODOL_MAX_ENTITIES; ++i) {
                if (move_world.entities[i].in_use &&
                    move_world.entities[i].type == CODOL_ET_PLAYER &&
                    move_world.entities[i].owner == 1) {
                    spawned = &move_world.entities[i];
                    break;
                }
            }
            assert(spawned != NULL);
            spawned->pos.origin[0] = 0.0f;
            spawned->pos.origin[1] = 0.0f;
            spawned->pos.origin[2] = 0.0f;
            spawned->mins[0] = -15.0f;
            spawned->mins[1] = -15.0f;
            spawned->mins[2] = 0.0f;
            spawned->maxs[0] = 15.0f;
            spawned->maxs[1] = 15.0f;
            spawned->maxs[2] = 70.0f;
        }
        codol_player_init(&player, -20.0f, 0.0f, -116.0f);
        memset(&cmd, 0, sizeof(cmd));
        cmd.forwardmove = 127;
        codol_player_move_in_world(&player, &cmd, 0.1f, &move_world, -1);
        assert(player.x < 0.0f && player.x > -20.0f);
        mt = codol_movement_trace(&move_world, start, end, mins, maxs, -1,
                                  CODOL_CONTENTS_SOLID);
        assert(mt.fraction < 1.0f);
        assert(mt.entity_num >= 0);
        codol_world_shutdown(&move_world);
    }

    /* Respawn timer and objective/vehicle lifetime state remain explicit. */
    {
        codol_mode_t respawn_mode;
        memset(&mode_config, 0, sizeof(mode_config));
        mode_config.respawn_delay_ms = 50;
        codol_mode_init(&respawn_mode, &mode_config);
        assert(codol_mode_join(&respawn_mode, 2) == CODOL_OK);
        assert(codol_mode_player_killed(&respawn_mode, 2, 1, 0) == CODOL_OK);
        assert(codol_mode_respawn_due(&respawn_mode, 2) != CODOL_OK);
        assert(codol_mode_tick(&respawn_mode, 51) == CODOL_OK);
        assert(codol_mode_respawn_due(&respawn_mode, 2) == CODOL_OK);
    }

    
    /* Projectile uses the same static clipmap and stops at a wall. */
    {
        static codol_world_t projectile_world;
        codol_projectile_t wall_projectile;
        codol_projectile_result_t wall_result;
        codol_entity_state_t *shell;
        assert(codol_world_init(&projectile_world, "coop_train") == CODOL_OK);
        codol_projectile_default(&wall_projectile);
        assert(codol_projectile_spawn(&projectile_world, &wall_projectile,
                                      -1, CODOL_PROJ_EXPLOSION_NONE,
                                      -585.0f, -433.0f, -80.0f) == CODOL_OK);
        shell = codol_entity_get(&projectile_world, wall_projectile.entity_num);
        assert(shell != NULL);
        shell->pos.velocity[0] = 1000.0f;
        assert(codol_projectile_step(&projectile_world, &wall_projectile, 100.0f,
                                     &wall_result) == CODOL_OK);
        assert(shell->pos.origin[0] < -547.0f);
        codol_world_shutdown(&projectile_world);
    }

    /* Impact-detonation and sticky state are observable independently. */
    {
        codol_projectile_t impact_projectile;
        codol_projectile_result_t impact_result;
        codol_entity_state_t *impact_entity;
        codol_projectile_default(&impact_projectile);
        impact_projectile.detonate_on_impact = true;
        impact_projectile.timed = false;
        assert(codol_projectile_spawn(&world, &impact_projectile, 0,
                                      CODOL_PROJ_EXPLOSION_FRAG,
                                      -10.0f, 0.0f, -115.5f) == CODOL_OK);
        impact_entity = codol_entity_get(&world, impact_projectile.entity_num);
        assert(impact_entity != NULL);
        impact_entity->pos.velocity[2] = -100.0f;
        assert(codol_projectile_step(&world, &impact_projectile, 16.0f,
                                     &impact_result) == CODOL_OK);
        assert(impact_result.exploded);
        assert(impact_projectile.state == CODOL_PROJ_EXPLODED);
    }

    
    /* Battle-service world binding must route usercmd into the authoritative
     * world entity, not only the legacy standalone player. */
    {
        static codol_world_t service_world;
        /* ★ 必须 static: codol_battle_service_t 内含 peers[16] × 32.8KB 的分片重组
         *   缓冲 ≈ 525KB, 放栈上在 Release 下会撑爆默认 1MB 栈(0xC0000005)。 */
        static codol_battle_service_t service;
        codol_usercmd_t service_cmd;
        codol_entity_state_t *service_entity;
        float before_x;
        assert(codol_world_init(&service_world, "coop_train") == CODOL_OK);
        assert(codol_world_load_assets(&service_world) == CODOL_OK);
        codol_battle_service_init(&service, NULL, NULL);
        codol_battle_service_bind_world(&service, &service_world, 0);
        service_entity = NULL;
        for (int i = 0; i < CODOL_MAX_ENTITIES; ++i) {
            if (service_world.entities[i].in_use &&
                service_world.entities[i].type == CODOL_ET_PLAYER &&
                service_world.entities[i].owner == 0) {
                service_entity = &service_world.entities[i];
                break;
            }
        }
        assert(service_entity != NULL);
        before_x = service_entity->pos.origin[0];
        memset(&service_cmd, 0, sizeof(service_cmd));
        service_cmd.forwardmove = 127;
        assert(codol_battle_service_apply_usercmd(&service, &service_cmd, 16) == CODOL_OK);
        assert(service_entity->pos.origin[0] != before_x);
        assert(service.player.x == service_entity->pos.origin[0]);
        assert(codol_entity_spawn_actor(&service_world, 0, 0.0f, 0.0f, -116.0f, 100, 0) == CODOL_OK);
        codol_world_shutdown(&service_world);
    }

    puts("test_static_closure: all checks passed");
    return 0;
}



