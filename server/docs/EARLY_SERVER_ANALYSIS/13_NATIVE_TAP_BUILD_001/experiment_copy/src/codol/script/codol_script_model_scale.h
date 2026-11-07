/* CoDOL per-entity model scale: <entity> setModelScale(<scale>).
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_SCRIPT_MODEL_SCALE_H
#define CODOL_SCRIPT_MODEL_SCALE_H
#ifdef CODOL_SERVER
#include "scr_vm.h"
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif
/* The scale C1 draws entity <num> at (entityState +0x54), 1.0 by default. */
float CODOL_EntityModelScale(int num);
/* G_FreeEntity: a recycled entity number starts at normal size. */
void CODOL_EntityModelScaleFreed(int num);
void CODOL_Scr_SetModelScale(scr_entref_t ref);
#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
#endif
