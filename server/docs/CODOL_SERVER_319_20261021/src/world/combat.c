#include "codol_combat.h"
#include "codol_entity.h"
#include <math.h>
#include <string.h>

void codol_damage_policy_default(codol_damage_policy_t *policy)
{
    if (!policy) return;
    memset(policy, 0, sizeof(*policy));
    policy->penetration_depth = 0.0f;
    policy->armor_scale = 1.0f;
    policy->shield_scale = 0.0f;
    policy->allow_shield = true;
}

static int clamp_positive_damage(int damage)
{
    return damage > 0 ? damage : 1;
}

codol_result_t codol_damage_apply(codol_world_t *world,
                                  int target_entity_num,
                                  const codol_weapondef_t *weapon,
                                  float distance,
                                  int hitloc,
                                  const codol_damage_policy_t *policy,
                                  codol_damage_result_t *result)
{
    codol_entity_state_t *target;
    codol_damage_policy_t local;
    int damage;
    if (!world || !weapon || !result) return CODOL_ERR_INVALID_ARG;
    if (!policy) { codol_damage_policy_default(&local); policy = &local; }
    target = codol_entity_get(world, target_entity_num);
    if (!target) return CODOL_ERR_INVALID_ARG;

    memset(result, 0, sizeof(*result));
    result->hitloc = hitloc;
    result->target_health_before = target->health;
    result->damageable = codol_entity_can_damage(target);
    if (!result->damageable) {
        result->target_health_after = target->health;
        return CODOL_OK;
    }

    if (hitloc == CODOL_HITLOC_SHIELD && policy->allow_shield && policy->shield_scale <= 0.0f) {
        result->blocked_by_shield = true;
        result->target_health_after = target->health;
        return CODOL_OK;
    }

    damage = codol_weapondef_damage_for_hit(weapon, distance, true, hitloc);
    damage = clamp_positive_damage(damage);
    if (policy->armor_scale > 0.0f && policy->armor_scale < 1.0f)
        damage = (int)floorf((float)damage * policy->armor_scale + 0.5f);
    if (damage < 1) damage = 1;
    result->damage = damage;
    target->health -= damage;
    if (target->health < 0) target->health = 0;
    result->target_health_after = target->health;
    result->killed = target->health == 0;
    return CODOL_OK;
}
