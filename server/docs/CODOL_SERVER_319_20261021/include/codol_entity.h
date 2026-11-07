#ifndef CODOL_ENTITY_H
#define CODOL_ENTITY_H

#include "codol_types.h"

#define CODOL_ET_FREE         0
#define CODOL_ET_PLAYER       1
#define CODOL_ET_CORPSE       2
#define CODOL_ET_ITEM         3
#define CODOL_ET_MISSILE      4
#define CODOL_ET_SCRIPT_MOVER 5
#define CODOL_ET_GENERAL      6

#define CODOL_ET_ACTOR        7
#define CODOL_ET_VEHICLE      8
#define CODOL_ET_TURRET       9
#define CODOL_ET_LOOT         10
#define CODOL_ET_OBJECTIVE    11

codol_result_t codol_entity_table_init(codol_world_t *world);
codol_entity_state_t *codol_entity_alloc(codol_world_t *world, int type);
void           codol_entity_free(codol_world_t *world, int entity_num);
codol_entity_state_t *codol_entity_get(codol_world_t *world, int entity_num);
codol_player_state_t *codol_player_get(codol_world_t *world, int client_num);

bool codol_entity_is_alive(const codol_entity_state_t *e);
bool codol_entity_can_damage(const codol_entity_state_t *e);
void codol_entity_set_health(codol_world_t *world, int entity_num, int health);
void codol_entity_set_cannot_die(codol_world_t *world, int entity_num, bool value);
void codol_entity_set_owner(codol_world_t *world, int entity_num, int owner);
int  codol_entity_count_in_use(const codol_world_t *world);
codol_result_t codol_entity_spawn_actor(codol_world_t *world, int owner, float x, float y, float z, int health, int model_index);
codol_result_t codol_entity_spawn_vehicle(codol_world_t *world, int owner, float x, float y, float z, int health, int model_index);
codol_result_t codol_entity_spawn_turret(codol_world_t *world, int owner, float x, float y, float z, int health, int weapon);
codol_result_t codol_entity_spawn_loot(codol_world_t *world, int owner, float x, float y, float z, int item);
codol_result_t codol_entity_spawn_objective(codol_world_t *world, float x, float y, float z, int health);

#endif /* CODOL_ENTITY_H */

