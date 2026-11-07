/* Native C1 mantle state machine. SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_PMOVE_C1_MANTLE_H
#define CODOL_PMOVE_C1_MANTLE_H

#include "codol_pmove_c1.h"

#ifdef __cplusplus
extern "C" {
#endif

int CODOL_PM_CheckMantleC1(codol_pmove_c1_t *move);
void CODOL_PM_MantleMoveC1(codol_pmove_c1_t *move);

#ifdef __cplusplus
}
#endif
#endif
