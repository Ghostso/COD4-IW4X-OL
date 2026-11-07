#ifndef CODOL_SCRIPT_RANK_EXPERIENCE_H
#define CODOL_SCRIPT_RANK_EXPERIENCE_H
#ifdef CODOL_SERVER
#include "scr_vm.h"
/* Explicit total-XP adapters; generic structured data access stays raw. */
void CODOL_Scr_GetRankExperience(scr_entref_t);
void CODOL_Scr_SetRankExperience(scr_entref_t);
#endif
#endif
