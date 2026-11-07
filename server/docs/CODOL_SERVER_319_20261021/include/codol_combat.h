#ifndef CODOL_COMBAT_H
#define CODOL_COMBAT_H

#include "codol_types.h"
#include "codol_weapondefs.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    float penetration_depth;
    float armor_scale;
    float shield_scale;
    bool  allow_shield;
} codol_damage_policy_t;

typedef struct {
    int   damage;
    int   target_health_before;
    int   target_health_after;
    int   hitloc;
    bool  blocked_by_shield;
    bool  killed;
    bool  damageable;
} codol_damage_result_t;

void codol_damage_policy_default(codol_damage_policy_t *policy);
codol_result_t codol_damage_apply(codol_world_t *world,
                                  int target_entity_num,
                                  const codol_weapondef_t *weapon,
                                  float distance,
                                  int hitloc,
                                  const codol_damage_policy_t *policy,
                                  codol_damage_result_t *result);

#ifdef __cplusplus
}
#endif
#endif /* CODOL_COMBAT_H */
