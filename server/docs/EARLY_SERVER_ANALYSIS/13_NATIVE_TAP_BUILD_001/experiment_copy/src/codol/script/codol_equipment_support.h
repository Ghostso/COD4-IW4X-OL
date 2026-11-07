/* SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_EQUIPMENT_SUPPORT_H
#define CODOL_EQUIPMENT_SUPPORT_H
#include "scr_vm.h"
#include "codol_entities.h"
#ifdef __cplusplus
extern "C" {
#endif
void CODOL_Scr_MakeScrambler(scr_entref_t ref);
int CODOL_OverlayEquipmentScrambler(codol_entity_state_t *wire,const entityState_t *entity);
#ifdef __cplusplus
}
#endif
#endif
