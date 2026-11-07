#ifndef CODOL_LOCATION_SELECTION_H
#define CODOL_LOCATION_SELECTION_H
#include "scr_vm.h"
void CODOL_BeginLocationSelection(scr_entref_t ref);
void CODOL_BeginLocationMortarSelection(scr_entref_t ref);
void CODOL_EndLocationSelection(scr_entref_t ref);
struct gentity_s;
void CODOL_ConfirmLocation(struct gentity_s *ent, const float *position);
int CODOL_LocationSelectionAction(struct gentity_s *ent);
#endif
