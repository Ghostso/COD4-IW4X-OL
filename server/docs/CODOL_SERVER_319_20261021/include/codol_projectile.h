#ifndef CODOL_PROJECTILE_H
#define CODOL_PROJECTILE_H

#include "codol_types.h"
#include "codol_combat.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    CODOL_PROJ_THROWN = 0,
    CODOL_PROJ_FLYING,
    CODOL_PROJ_STUCK,
    CODOL_PROJ_ARMED,
    CODOL_PROJ_EXPLODED,
    CODOL_PROJ_DUD
} codol_projectile_state_t;

typedef enum {
    CODOL_PROJ_EXPLOSION_NONE = 0,
    CODOL_PROJ_EXPLOSION_FRAG,
    CODOL_PROJ_EXPLOSION_FLASH,
    CODOL_PROJ_EXPLOSION_SMOKE,
    CODOL_PROJ_EXPLOSION_EMP,
    CODOL_PROJ_EXPLOSION_INCENDIARY
} codol_projectile_explosion_t;

typedef struct {
    int    entity_num;
    int    owner;
    codol_projectile_state_t state;
    codol_projectile_explosion_t explosion;
    float  fuse_ms;
    float  age_ms;
    float  inner_damage;
    float  outer_damage;
    float  inner_radius;
    float  outer_radius;
    float  gravity;
    float  bounce;
    float  radius;
    bool   stick_to_players;
    bool   sticky_to_world;
    bool   detonate_on_impact;
    bool   timed;
} codol_projectile_t;

typedef struct {
    int   entity_num;
    int   damage;
    float distance;
    bool  killed;
} codol_projectile_hit_t;

typedef struct {
    codol_projectile_hit_t hits[CODOL_MAX_CLIENTS];
    int   hit_count;
    bool  exploded;
} codol_projectile_result_t;

void codol_projectile_default(codol_projectile_t *p);
codol_result_t codol_projectile_spawn(codol_world_t *world, codol_projectile_t *p,
                                      int owner, int explosion_type, float x, float y, float z);
codol_result_t codol_projectile_step(codol_world_t *world, codol_projectile_t *p,
                                     float dt_ms, codol_projectile_result_t *result);
codol_result_t codol_projectile_trigger(codol_world_t *world, codol_projectile_t *p,
                                        codol_projectile_result_t *result);

#ifdef __cplusplus
}
#endif
#endif /* CODOL_PROJECTILE_H */
