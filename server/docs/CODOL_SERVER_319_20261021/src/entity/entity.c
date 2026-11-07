#include "codol_entity.h"
#include <string.h>

codol_result_t codol_entity_table_init(codol_world_t *world)
{
    if (!world) return CODOL_ERR_INVALID_ARG;
    memset(world->entities, 0, sizeof(world->entities));
    memset(world->players, 0, sizeof(world->players));
    for (int i = 0; i < CODOL_MAX_ENTITIES; i++) {
        world->entities[i].number = i;
        world->entities[i].type = CODOL_ET_FREE;
        world->entities[i].in_use = false;
        world->entities[i].owner = -1;
    }
    return CODOL_OK;
}

codol_entity_state_t *codol_entity_alloc(codol_world_t *world, int type)
{
    if (!world) return NULL;
    for (int i = 0; i < CODOL_MAX_ENTITIES; i++) {
        codol_entity_state_t *e = &world->entities[i];
        if (!e->in_use) {
            memset(e, 0, sizeof(*e));
            e->number = i;
            e->type = type;
            e->in_use = true;
            e->owner = -1;
            return e;
        }
    }
    return NULL;
}

void codol_entity_free(codol_world_t *world, int entity_num)
{
    if (!world || entity_num < 0 || entity_num >= CODOL_MAX_ENTITIES) return;
    codol_entity_state_t *e = &world->entities[entity_num];
    e->in_use = false;
    e->type = CODOL_ET_FREE;
}

codol_entity_state_t *codol_entity_get(codol_world_t *world, int entity_num)
{
    if (!world || entity_num < 0 || entity_num >= CODOL_MAX_ENTITIES) return NULL;
    if (!world->entities[entity_num].in_use) return NULL;
    return &world->entities[entity_num];
}

codol_player_state_t *codol_player_get(codol_world_t *world, int client_num)
{
    if (!world || client_num < 0 || client_num >= CODOL_MAX_CLIENTS) return NULL;
    return &world->players[client_num];
}

bool codol_entity_is_alive(const codol_entity_state_t *e)
{
    return e && e->in_use && e->health > 0;
}

bool codol_entity_can_damage(const codol_entity_state_t *e)
{
    return codol_entity_is_alive(e) && (e->flags & 0x1u) == 0;
}

void codol_entity_set_health(codol_world_t *world, int entity_num, int health)
{
    codol_entity_state_t *e = codol_entity_get(world, entity_num);
    if (!e) return;
    e->health = health < 0 ? 0 : health;
}

void codol_entity_set_cannot_die(codol_world_t *world, int entity_num, bool value)
{
    codol_entity_state_t *e = codol_entity_get(world, entity_num);
    if (!e) return;
    if (value) e->flags |= 0x1u;
    else e->flags &= ~0x1u;
}

void codol_entity_set_owner(codol_world_t *world, int entity_num, int owner)
{
    codol_entity_state_t *e = codol_entity_get(world, entity_num);
    if (!e) return;
    e->owner = owner;
}

int codol_entity_count_in_use(const codol_world_t *world)
{
    int n = 0;
    if (!world) return 0;
    for (int i = 0; i < CODOL_MAX_ENTITIES; i++)
        if (world->entities[i].in_use) ++n;
    return n;
}

static void entity_set_origin(codol_entity_state_t *e, float x, float y, float z)
{
    if (!e) return;
    e->pos.origin[0] = x; e->pos.origin[1] = y; e->pos.origin[2] = z;
}

codol_result_t codol_entity_spawn_actor(codol_world_t *world, int owner, float x, float y, float z, int health, int model_index)
{
    codol_entity_state_t *e = codol_entity_alloc(world, CODOL_ET_ACTOR);
    if (!e) return CODOL_ERR_NO_MEMORY;
    e->owner = owner; e->health = health; e->model_index = model_index;
    entity_set_origin(e, x, y, z);
    return CODOL_OK;
}

codol_result_t codol_entity_spawn_vehicle(codol_world_t *world, int owner, float x, float y, float z, int health, int model_index)
{
    codol_entity_state_t *e = codol_entity_alloc(world, CODOL_ET_VEHICLE);
    if (!e) return CODOL_ERR_NO_MEMORY;
    e->owner = owner; e->health = health; e->model_index = model_index;
    entity_set_origin(e, x, y, z);
    return CODOL_OK;
}

codol_result_t codol_entity_spawn_turret(codol_world_t *world, int owner, float x, float y, float z, int health, int weapon)
{
    codol_entity_state_t *e = codol_entity_alloc(world, CODOL_ET_TURRET);
    if (!e) return CODOL_ERR_NO_MEMORY;
    e->owner = owner; e->health = health; e->weapon = weapon;
    entity_set_origin(e, x, y, z);
    return CODOL_OK;
}

codol_result_t codol_entity_spawn_loot(codol_world_t *world, int owner, float x, float y, float z, int item)
{
    codol_entity_state_t *e = codol_entity_alloc(world, CODOL_ET_LOOT);
    if (!e) return CODOL_ERR_NO_MEMORY;
    e->owner = owner; e->health = 1; e->weapon = item;
    entity_set_origin(e, x, y, z);
    return CODOL_OK;
}

codol_result_t codol_entity_spawn_objective(codol_world_t *world, float x, float y, float z, int health)
{
    codol_entity_state_t *e = codol_entity_alloc(world, CODOL_ET_OBJECTIVE);
    if (!e) return CODOL_ERR_NO_MEMORY;
    e->health = health;
    entity_set_origin(e, x, y, z);
    return CODOL_OK;
}
