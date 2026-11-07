/* precachevehicle: the script producer of the CoDOL vehicle definition bank.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_SCRIPT_VEHICLE_ASSETS_H
#define CODOL_SCRIPT_VEHICLE_ASSETS_H
#ifdef __cplusplus
extern "C" {
#endif
/* precachevehicle(<vehicleInfo>): one string argument, no return value.
 * Measured IW4 precachevehicle4d4840 gates on level.initializing, resolves
 * Scr_GetString(0), registers the name in the vehicle configstring bank and
 * loads the definition once per slot; see codol_vehicle_assets.h for the
 * measured registrar, bank and loader. Register as
 * Scr_AddFunction("precachevehicle", CODOL_Scr_PrecacheVehicle, 0). */
void CODOL_Scr_PrecacheVehicle(void);
#ifdef __cplusplus
}
#endif
#endif
