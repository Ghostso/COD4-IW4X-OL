/* CoDOL vehicle definition registration, loading and configstring lifecycle.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_VEHICLE_ASSETS_H
#define CODOL_VEHICLE_ASSETS_H
#ifdef __cplusplus
extern "C" {
#endif
/* Measured C1 1.1.1.13: CG_ConfigstringModified467350 routes configstrings
 * 0xd23..0xd42 through4674bb..4674cb into the asset lookup4cb8e0 with asset
 * type0x29 (41, VehicleDef) and caches the header in the 32-entry table at
 * 0x2bc3018 (0x2bbfb8c biased by0xd23*4). Client vehicle instances
 * (0x2bc2798, stride0x88) select their definition through the slot number kept
 * at instance+4, so a slot number is the wire identity of a vehicle
 * definition; its consumers read the cached header (0x2c8,0x2cc,0x2d0,0x2f8 at
 * 44e772/4564d4/4717f2/471dae). The bank ends where CODOL_CS_SOUNDS begins.
 *
 * Measured IW4 (iw4x precachevehicle4d4840): gate on level.initializing
 * (0x1a831c4) with Scr_Error "PrecacheVehicle must be called before any wait
 * statements in script" (0x6fb848), then Scr_GetString(0) and registrar
 * 0x443aa0, which is G_FindConfigstringIndex(name, base0x665, capacity0x20,
 * create=level.initializing, label "VehicleDef") at4af0c0: index0 is
 * reserved, the search runs over slots1..31, an equal name is reused, a free
 * slot is published with SV_SetConfigstring, an empty/NULL name yields0, and
 * exhaustion dumps the bank and Com_Errors. The registrar then loads the
 * definition once per slot (0x674bc0, ecx=slot/eax=name), which resolves the
 * definition by name, registers its turret weapon through
 * G_GetWeaponIndexForName (0x49e540) and instantiates the definition's physics
 * parameters. The builtin discards the index: precachevehicle returns nothing.
 *
 * Mounted CoDOL VehicleDefs are converted by codol_vehicle_native.cpp into
 * retained simulation records plus an extended definition store. A text
 * record cannot bypass conversion, and a missing or invalid archive asset
 * does not fall back to defaultvehicle. Physics and additional movement
 * consumers are still under implementation. */
#define CODOL_CS_VEHICLES 3363
#define CODOL_VEHICLE_SLOTS 32

/* Drop every slot binding. The configstring bank is reset separately; stale
 * bindings are also detected lazily, so a missed reset cannot alias a slot. */
void CODOL_ResetVehicleAssets(void);
/* Register a definition name in the vehicle bank. Returns the slot (1..31),
 * 0 for an empty name, and -1 for an invalid name, an exhausted bank, or a
 * missing slot with create=0. Registration publishes the name to clients that
 * already hold a gamestate; it does not load the definition. */
int CODOL_RegisterVehicleName(const char *name, int create);
/* Bind a registered slot to a loaded definition, registering its turret
 * weapon. Idempotent per slot. Returns1 when the slot names a definition that
 * exists, 0 when the load failed or fell back to another definition. */
int CODOL_LoadVehicleDefinition(int slot);
/* Native spawn lookup. Requires registration during script initialization;
 * later spawns reuse the published slot. A failure drops the level instead
 * of handing retained spawn/model fallback code an invalid record index. */
int CODOL_VehicleInfoForSpawn(const char *name);
/* Registered slot for a name without publishing anything, or -1/0 as above. */
int CODOL_VehicleSlotForName(const char *name);
/* Published name of a slot, or NULL. Never a fallback definition's name. */
const char *CODOL_VehicleName(int slot);
/* Retained s_vehicleInfos index bound to a slot, or -1 while unloaded. */
int CODOL_VehicleInfoIndex(int slot);
/* Weapon index registered with the definition's turret weapon, or 0. */
int CODOL_VehicleTurretWeapon(int slot);
/* Wire slot for a simulated vehicle: the slot bound to a retained record,
 * registering and publishing the record's name when a script never precached
 * it. Returns -1 when the record is invalid or the bank is exhausted. */
int CODOL_BindVehicleInfoIndex(int info_index);
#ifdef __cplusplus
}
#endif
#endif
