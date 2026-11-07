#ifndef CODOL_MISSILE_ROLLING_H
#define CODOL_MISSILE_ROLLING_H
#include "entity.h"
#include "xassets/weapondef.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Native collision response. -1: caller retains ordinary bounce; 0: handled
 * rolling-enabled bounce; 1: handled rolling contact. A return of 1 NEVER
 * means stop: the caller still evaluates its authoritative stop/stick policy.
 * Only velocity/angular trajectory are changed. Caller retains origin,
 * linear trajectory time/type/base, impact notification and fuse ownership. */
int CODOL_MissileApplyRollingResponse(gentity_t *ent,const struct WeaponDef *definition,
    const float normal[3],const float incoming[3],unsigned surface);
/* C1 dvar1193 controls the ordinary floor-rest speed (default20). */
int CODOL_MissileBelowRestSpeed(const float velocity[3]);
#ifdef __cplusplus
}
#endif
#endif
