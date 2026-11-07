/* SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_SCRIPT_LIGHT_H
#define CODOL_SCRIPT_LIGHT_H
#include "scr_vm.h"
#ifdef __cplusplus
extern "C" {
#endif
void CODOL_Scr_SetLightIntensity(scr_entref_t ref);
void CODOL_Scr_GetLightIntensity(scr_entref_t ref);
void CODOL_Scr_SetLightRadius(scr_entref_t ref);
void CODOL_Scr_GetLightRadius(scr_entref_t ref);
void CODOL_Scr_SetLightExponent(scr_entref_t ref);
void CODOL_Scr_GetLightExponent(scr_entref_t ref);
void CODOL_Scr_SetLightColor(scr_entref_t ref);
void CODOL_Scr_GetLightColor(scr_entref_t ref);
void CODOL_Scr_GetLightFovInner(scr_entref_t ref);
void CODOL_Scr_GetLightFovOuter(scr_entref_t ref);
void CODOL_Scr_SetLightFov(scr_entref_t ref);
#ifdef __cplusplus
}
#endif
#endif
