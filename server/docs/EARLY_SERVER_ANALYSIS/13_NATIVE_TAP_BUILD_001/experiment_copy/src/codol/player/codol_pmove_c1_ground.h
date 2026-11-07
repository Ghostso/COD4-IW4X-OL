/* Native C1 ground/air/step movement. SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_PMOVE_C1_GROUND_H
#define CODOL_PMOVE_C1_GROUND_H
#include "codol_pmove_c1.h"
void CODOL_PM_GroundTraceC1(codol_pmove_c1_t *move);
int CODOL_PM_CheckJumpC1(codol_pmove_c1_t *move);
void CODOL_PM_NormalMoveC1(codol_pmove_c1_t *move);
void CODOL_PM_AirMoveC1(codol_pmove_c1_t *move);
void CODOL_PM_LadderMoveC1(codol_pmove_c1_t *move);
void CODOL_PM_MeleeChargeMoveC1(codol_pmove_c1_t *move);
void CODOL_PM_FreeMoveC1(codol_pmove_c1_t *move);
void CODOL_PM_FootstepsC1(codol_pmove_c1_t *move,int msec);
#endif
