#ifndef CODOL_PERK_RUNTIME_H
#define CODOL_PERK_RUNTIME_H
#include "codol_abilities.h"
#include "codol_perks.h"
#include "player.h"
#ifdef __cplusplus
extern "C" {
#endif
void CODOL_ResetPerkRuntime(unsigned client);
int CODOL_CommitPerkState(unsigned client,const codol_perk_state_t *selection);
int CODOL_GetScriptAbilities(unsigned client,codol_client_abilities_t *out);
/* Selected-perk contribution only; script ability writes remain independent.
 * Returns zero for absent/non-numeric effects or a non-live player. */
int CODOL_GetSelectedPerkValue(const playerState_t *ps,unsigned id,float *out);
int CODOL_CommitScriptAbilities(unsigned client,const codol_client_abilities_t *state,int written_value_slot);
void CODOL_UpdatePerkMoveSpeed(playerState_t *ps,float base);
#ifdef __cplusplus
}
#endif
#endif
