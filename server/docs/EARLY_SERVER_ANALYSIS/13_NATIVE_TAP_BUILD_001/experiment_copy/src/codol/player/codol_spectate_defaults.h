/* SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_SPECTATE_DEFAULTS_H
#define CODOL_SPECTATE_DEFAULTS_H
#include "scr_vm.h"
#ifdef __cplusplus
extern "C" {
#endif
void CODOL_Scr_SetSpectateDefaults(scr_entref_t ref);
void CODOL_GetSpectateDefaults(unsigned client, float *origin, float *angles);
void CODOL_ResetSpectateDefaults(unsigned client);
void CODOL_ResetAllSpectateDefaults(void);
#ifdef __cplusplus
}
#endif
#endif
