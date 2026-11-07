#ifndef CODOL_RC_LIFECYCLE_H
#define CODOL_RC_LIFECYCLE_H
#include "scr_vm.h"
#ifdef __cplusplus
extern "C" {
#endif
struct gentity_s;
void CODOL_Scr_VehicleSetOwner(scr_entref_t);
void CODOL_Scr_VehicleGetClientFlag(scr_entref_t);
void CODOL_Scr_VehicleSetClientFlag(scr_entref_t);
void CODOL_Scr_VehicleClearClientFlag(scr_entref_t);
int CODOL_RCVehicleStunned(const struct gentity_s *);
struct gentity_s *CODOL_RCVehicleOwner(const struct gentity_s *);
void CODOL_RCEntityFreed(const struct gentity_s *);
void CODOL_RCResetLifecycle(void);
#ifdef __cplusplus
}
#endif
#endif
