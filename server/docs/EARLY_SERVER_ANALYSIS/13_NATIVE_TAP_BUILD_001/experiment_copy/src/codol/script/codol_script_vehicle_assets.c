/* precachevehicle. SPDX-License-Identifier: AGPL-3.0-or-later */
#ifdef CODOL_SERVER
#include "codol_script_vehicle_assets.h"
#include "codol_vehicle_assets.h"
#include "scr_vm_functions.h"
#include "server.h"
#include "g_shared.h"

void CODOL_Scr_PrecacheVehicle(void)
{
    const char *name;
    int slot;
    /* IW4 4d4840: the gate and its message precede argument handling. IW4
     * falls through to the registrar afterwards because its Scr_Error unwinds
     * the thread; this returns explicitly rather than depend on that. */
    if (!level.initializing) {
        Scr_Error("PrecacheVehicle must be called before any wait statements in script");
        return;
    }
    name = Scr_GetString(0);
    if (!name) return;
    /* IW4 443aa0 passes level.initializing as the create flag and discards the
     * returned slot; an empty name registers nothing and is not an error. */
    slot = CODOL_RegisterVehicleName(name, level.initializing);
    if (slot < 0) {
        Scr_ParamError(0, "precachevehicle: invalid vehicle name or exhausted vehicle definitions");
        return;
    }
    if (slot > 0 && !CODOL_LoadVehicleDefinition(slot)) {
        /* The archive conversion can fail independently of name registration.
         * Do not let the script continue as though a definition was loaded. */
        Scr_ParamError(0, "precachevehicle: vehicle definition could not be loaded");
        return;
    }
    if (slot > 0) {
        /* SpawnVehicle also resolves the fallback definition to select its
         * model path. Cache it while registration is legal, even if this
         * precached vehicle's first spawn happens after the first wait. */
        CODOL_VehicleInfoForSpawn("defaultvehicle");
    }
}
#endif
