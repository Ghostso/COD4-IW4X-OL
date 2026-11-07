#ifndef CODOL_REMOTE_VEHICLE_SCRIPT_H
#define CODOL_REMOTE_VEHICLE_SCRIPT_H
#include "scr_vm.h"
#ifdef __cplusplus
extern "C" {
#endif
void CODOL_Scr_UseVehicle(scr_entref_t);
void CODOL_Scr_GetSeatOccupant(scr_entref_t);
void CODOL_PlayerCmd_IsRemoteControlling(scr_entref_t);
/* Registered as "unlink": remote-control/player-link release, then the
 * retained tag unlink. */
void CODOL_Scr_Unlink(scr_entref_t);
#ifdef __cplusplus
}
#endif
#endif
