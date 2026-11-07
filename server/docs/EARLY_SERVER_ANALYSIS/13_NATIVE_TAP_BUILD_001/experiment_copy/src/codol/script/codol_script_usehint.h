#ifndef CODOL_SCRIPT_USEHINT_H
#define CODOL_SCRIPT_USEHINT_H
#ifdef CODOL_SERVER
#include "scr_vm.h"
#ifdef __cplusplus
extern "C" {
#endif
struct gentity_s;
void CODOL_Scr_ForceUseHintOn(scr_entref_t ref);
void CODOL_Scr_ForceUseHintOff(scr_entref_t ref);
void CODOL_Scr_SetHintString(scr_entref_t ref);
qboolean CODOL_ForceUseHint_Apply(struct gentity_s *entity);
void CODOL_ForceUseHint_ResetClient(int slot);
void CODOL_ForceUseHint_ResetAll(void);
#ifdef __cplusplus
}
#endif
#endif
#endif
