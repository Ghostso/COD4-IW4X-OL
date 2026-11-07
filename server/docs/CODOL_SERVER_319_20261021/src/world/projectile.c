#include "codol_projectile.h"
#include "codol_entity.h"
#include "codol_collision.h"
#include <math.h>
#include <string.h>

void codol_projectile_default(codol_projectile_t *p)
{
    if (!p) return;
    memset(p, 0, sizeof(*p));
    p->entity_num = -1;
    p->owner = -1;
    p->state = CODOL_PROJ_THROWN;
    p->explosion = CODOL_PROJ_EXPLOSION_NONE;
    p->fuse_ms = 2500.0f;
    p->gravity = 800.0f;
    p->bounce = 0.3f;
    p->radius = 4.0f;
    p->timed = true;
}

codol_result_t codol_projectile_spawn(codol_world_t *world, codol_projectile_t *p,
                                      int owner, int explosion_type, float x, float y, float z)
{
    codol_entity_state_t *e;
    if (!world || !p) return CODOL_ERR_INVALID_ARG;
    if (p->entity_num >= 0) return CODOL_ERR_STATE;
    e = codol_entity_alloc(world, CODOL_ET_MISSILE);
    if (!e) return CODOL_ERR_NO_MEMORY;
    p->entity_num = e->number;
    p->owner = owner;
    p->state = CODOL_PROJ_FLYING;
    p->explosion = (codol_projectile_explosion_t)explosion_type;
    p->age_ms = 0.0f;
    e->owner = owner;
    e->health = 1;
    e->pos.origin[0] = x;
    e->pos.origin[1] = y;
    e->pos.origin[2] = z;
    return CODOL_OK;
}

static void projectile_explode(codol_world_t *world, codol_projectile_t *p,
                               codol_projectile_result_t *result)
{
    codol_entity_state_t *center;
    int i;
    if (!world || !p || !result) return;
    center = codol_entity_get(world, p->entity_num);
    if (!center) return;
    result->exploded = true;
    p->state = CODOL_PROJ_EXPLODED;
    if (p->explosion == CODOL_PROJ_EXPLOSION_NONE) return;
    for (i = 0; i < CODOL_MAX_ENTITIES && result->hit_count < CODOL_MAX_CLIENTS; ++i) {
        codol_entity_state_t *e = &world->entities[i];
        float dx, dy, dz, distance, damage;
        if (!e->in_use || e == center || e->number == p->entity_num) continue;
        if (e->type != CODOL_ET_PLAYER && e->type != CODOL_ET_ACTOR &&
            e->type != CODOL_ET_VEHICLE && e->type != CODOL_ET_TURRET) continue;
        dx = e->pos.origin[0] - center->pos.origin[0];
        dy = e->pos.origin[1] - center->pos.origin[1];
        dz = e->pos.origin[2] - center->pos.origin[2];
        distance = sqrtf(dx * dx + dy * dy + dz * dz);
        if (distance > p->outer_radius) continue;
        damage = p->outer_damage;
        if (distance <= p->inner_radius) damage = p->inner_damage;
        else if (p->outer_radius > p->inner_radius) {
            float t = (distance - p->inner_radius) / (p->outer_radius - p->inner_radius);
            damage = p->inner_damage + (p->outer_damage - p->inner_damage) * (1.0f - t);
        }
        if (damage < 1.0f) damage = 1.0f;
        result->hits[result->hit_count].entity_num = e->number;
        result->hits[result->hit_count].damage = (int)floorf(damage + 0.5f);
        result->hits[result->hit_count].distance = distance;
        e->health -= result->hits[result->hit_count].damage;
        if (e->health < 0) e->health = 0;
        result->hits[result->hit_count].killed = e->health == 0;
        result->hit_count++;
    }
}

codol_result_t codol_projectile_step(codol_world_t *world, codol_projectile_t *p,
                                     float dt_ms, codol_projectile_result_t *result)
{
    codol_entity_state_t *e;
    if (!world || !p || !result) return CODOL_ERR_INVALID_ARG;
    memset(result, 0, sizeof(*result));
    e = codol_entity_get(world, p->entity_num);
    if (!e) return CODOL_ERR_STATE;
    if (p->state == CODOL_PROJ_EXPLODED || p->state == CODOL_PROJ_DUD) return CODOL_OK;

    p->age_ms += dt_ms;
    if (p->state == CODOL_PROJ_FLYING && dt_ms > 0.0f) {
        codol_collision_trace_t trace;
        codol_collision_box_t boxes[CODOL_MAX_ENTITIES];
        int box_count = 0, i;
        float start[3], finish[3], mins[3], maxs[3], seconds = dt_ms / 1000.0f;
        e->pos.velocity[2] -= p->gravity * seconds;
        start[0] = e->pos.origin[0];
        start[1] = e->pos.origin[1];
        start[2] = e->pos.origin[2];
        finish[0] = start[0] + e->pos.velocity[0] * seconds;
        finish[1] = start[1] + e->pos.velocity[1] * seconds;
        finish[2] = start[2] + e->pos.velocity[2] * seconds;
        mins[0] = mins[1] = mins[2] = -p->radius;
        maxs[0] = maxs[1] = maxs[2] = p->radius;
        for (i = 0; i < CODOL_MAX_ENTITIES && box_count < CODOL_MAX_ENTITIES; ++i) {
            const codol_entity_state_t *other = &world->entities[i];
            float half_x, half_y, height;
            if (!other->in_use || i == p->entity_num || other->type == CODOL_ET_FREE ||
                other->type == CODOL_ET_CORPSE || other->type == CODOL_ET_MISSILE) continue;
            half_x = (other->maxs[0] > other->mins[0]) ? (other->maxs[0] - other->mins[0]) * 0.5f : 15.0f;
            half_y = (other->maxs[1] > other->mins[1]) ? (other->maxs[1] - other->mins[1]) * 0.5f : 15.0f;
            height = (other->maxs[2] > other->mins[2]) ? other->maxs[2] - other->mins[2] : 70.0f;
            boxes[box_count].mins[0] = other->pos.origin[0] - half_x;
            boxes[box_count].mins[1] = other->pos.origin[1] - half_y;
            boxes[box_count].mins[2] = other->pos.origin[2];
            boxes[box_count].maxs[0] = other->pos.origin[0] + half_x;
            boxes[box_count].maxs[1] = other->pos.origin[1] + half_y;
            boxes[box_count].maxs[2] = other->pos.origin[2] + height;
            boxes[box_count].contents = CODOL_CONTENTS_SOLID;
            boxes[box_count].entity_num = other->number;
            ++box_count;
        }
        codol_collision_box_trace_ex(&trace, start, finish, mins, maxs,
                                     CODOL_CONTENTS_PLAYERCLIP | CODOL_CONTENTS_SOLID,
                                     p->entity_num, boxes, box_count);
        e->pos.origin[0] = trace.end_pos[0];
        e->pos.origin[1] = trace.end_pos[1];
        e->pos.origin[2] = trace.end_pos[2];
        if (trace.fraction < 1.0f) {
            if (p->sticky_to_world || (p->stick_to_players && trace.entity_num >= 0)) {
                p->state = CODOL_PROJ_STUCK;
            } else {
                float dot = e->pos.velocity[0] * trace.normal[0] +
                            e->pos.velocity[1] * trace.normal[1] +
                            e->pos.velocity[2] * trace.normal[2];
                e->pos.velocity[0] = (e->pos.velocity[0] - 2.0f * dot * trace.normal[0]) * p->bounce;
                e->pos.velocity[1] = (e->pos.velocity[1] - 2.0f * dot * trace.normal[1]) * p->bounce;
                e->pos.velocity[2] = (e->pos.velocity[2] - 2.0f * dot * trace.normal[2]) * p->bounce;
                if (fabsf(e->pos.velocity[2]) < 1.0f) e->pos.velocity[2] = 0.0f;
            }
            if (p->detonate_on_impact) {
                projectile_explode(world, p, result);
                return CODOL_OK;
            }
        }
    }
    if (p->timed && p->age_ms >= p->fuse_ms) {
        projectile_explode(world, p, result);
        return CODOL_OK;
    }
    return CODOL_OK;
}

codol_result_t codol_projectile_trigger(codol_world_t *world, codol_projectile_t *p,
                                        codol_projectile_result_t *result)
{
    if (!world || !p || !result) return CODOL_ERR_INVALID_ARG;
    memset(result, 0, sizeof(*result));
    if (!codol_entity_get(world, p->entity_num)) return CODOL_ERR_STATE;
    projectile_explode(world, p, result);
    return CODOL_OK;
}

