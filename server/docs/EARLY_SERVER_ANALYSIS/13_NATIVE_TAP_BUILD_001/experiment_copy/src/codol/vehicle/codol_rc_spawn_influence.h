#ifndef CODOL_RC_SPAWN_INFLUENCE_H
#define CODOL_RC_SPAWN_INFLUENCE_H
#include "scr_vm.h"
#ifdef __cplusplus
extern "C" {
#endif
void CODOL_Scr_SetRCSpawnInfluencer(scr_entref_t);
void CODOL_Scr_RCSpawnWeight(void);
void CODOL_ResetRCSpawnInfluencers(void);
void CODOL_ResetRCSpawnInfluencer(unsigned);
#ifdef __cplusplus
}
#endif
#endif
