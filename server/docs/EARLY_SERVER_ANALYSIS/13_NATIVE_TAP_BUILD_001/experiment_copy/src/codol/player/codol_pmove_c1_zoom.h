/* C1 variable-zoom scope step, PM_UpdateVariableZoom 0x00418480.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_PMOVE_C1_ZOOM_H
#define CODOL_PMOVE_C1_ZOOM_H

#include "codol_pmove_c1.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Runs C1's step for this command and queues EV_SCOPE_ZOOM when the level
 * changes. Call after the ADS lerp and before PM_Weapon, as C1 does. */
void CODOL_PM_UpdateVariableZoomC1(codol_pmove_c1_t *move);
/* PM_BeginWeaponChange 0x4197c2..0x4197ce: level, time and latch go to 0. */
void __cdecl CODOL_VariableZoomBeginWeaponChange(struct playerState_s *ps);

#ifdef __cplusplus
}
#endif
#endif
