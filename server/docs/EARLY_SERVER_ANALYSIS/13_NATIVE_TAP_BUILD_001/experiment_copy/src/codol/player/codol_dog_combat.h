#ifndef CODOL_DOG_COMBAT_H
#define CODOL_DOG_COMBAT_H
struct gentity_s;
/* Native dog combat geometry. This is an implementation component, not a
 * callable dog actor: animation, movement and damage producers must call it. */
typedef struct {
    float enemyPosition[3], goal[3];
    int goalSet, inAttackRange;
} codol_dog_attack_goal_t;
void CODOL_DogCombatReset(void);
void CODOL_DogCombatRelease(struct gentity_s *dog);
void CODOL_DogCombatGoal(struct gentity_s *dog, struct gentity_s *enemy,
                        float attackDistance, int enemyInSyncedMelee,
                        codol_dog_attack_goal_t *result);
#endif
