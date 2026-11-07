#ifndef CODOL_SKILL_RATING_H
#define CODOL_SKILL_RATING_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
/* IW4 5f9580 integer skill-pair reducer. Both pointers must be valid.
 * This only changes the supplied ratings; profile ownership, field lookup,
 * eligibility and persistence belong to the script/profile caller. */
void CODOL_UpdateSkillRatings(int32_t *winner,int32_t *loser,float weight);
#ifdef __cplusplus
}
#endif
#endif
