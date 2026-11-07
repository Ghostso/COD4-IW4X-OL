#ifndef CODOL_SCRIPT_PLAYERUSE_H
#define CODOL_SCRIPT_PLAYERUSE_H
#ifdef CODOL_SERVER
#include "scr_vm.h"
#ifdef __cplusplus
extern "C" {
#endif
struct gentity_s;
void CODOL_Scr_DisablePlayerUse(scr_entref_t);
void CODOL_Scr_EnablePlayerUse(scr_entref_t);
int CODOL_PlayerUseAllowed(const struct gentity_s *player,const struct gentity_s *target);
void CODOL_PlayerUseResetClient(int slot);
void CODOL_PlayerUseResetAll(void);
void CODOL_PlayerUseClearTarget(int number);
#ifdef __cplusplus
}
#endif
#endif
#endif
