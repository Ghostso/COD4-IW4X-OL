#ifndef CODOL_OBITUARY_H
#define CODOL_OBITUARY_H
#include "entity.h"
void CODOL_GScr_Obituary(void);
/* Decode only this producer's captured, archived event state. */
int CODOL_DecodeObituary(const entityState_t *,unsigned *victim,
                         unsigned *attacker,unsigned *death_code);
#endif
