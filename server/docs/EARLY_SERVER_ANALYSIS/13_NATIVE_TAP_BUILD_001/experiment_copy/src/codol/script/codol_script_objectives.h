/* Compass objectives widened to C1's 32 slots (codol_script_objectives.c). */
#ifndef CODOL_SCRIPT_OBJECTIVES_H
#define CODOL_SCRIPT_OBJECTIVES_H
#include "q_shared.h"

/* C1 MSG_ReadDeltaPlayerstate loops 32 slots (0x5a1f9c); CODOL_OBJECTIVE_SLOTS
 * in codol_player_arrays.h states the same number for the wire. */
#define CODOL_OBJECTIVE_TOTAL 32
/* level.objectives / ps->objective in the retained structs. */
#define CODOL_OBJECTIVE_RETAINED 16
#define CODOL_OBJECTIVE_NO_ENTITY 0x7ff

/* Called from G_InitGame right after level is cleared (map load and
 * map_restart alike). */
void CODOL_ResetObjectives(void);
/* Slots 16..31 as client `client` sees them: G_RunFrame's team filter for
 * the slots it does not copy into ps->objective. out holds 16 entries. */
void CODOL_FillHighObjectives(int client, objective_t *out);

void CODOL_Scr_Objective_Add(void);
void CODOL_Scr_Objective_Delete(void);
void CODOL_Scr_Objective_State(void);
void CODOL_Scr_Objective_Icon(void);
void CODOL_Scr_Objective_Position(void);
void CODOL_Scr_Objective_OnEntity(void);
void CODOL_Scr_Objective_Current(void);
void CODOL_Scr_Objective_Team(void);
#endif
