#ifndef CODOL_SCRIPT_ENTITY_FX_H
#define CODOL_SCRIPT_ENTITY_FX_H
#include "scr_vm.h"
/* Player-only method; registered native source, not runtime-verified. */
void CODOL_PlayerCmd_PlayFX(scr_entref_t ref);
void CODOL_Scr_PlayFXOnTagForClients(void);
#endif
