/* CoDOL vehicle / turret / remote-view script builtins.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_SCRIPT_VEHICLE_BUILTINS_H
#define CODOL_SCRIPT_VEHICLE_BUILTINS_H
#ifdef CODOL_SERVER
#include "scr_vm.h"
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif
struct gentity_s;

/* ---- script vehicle methods (receiver: entity with scr_vehicle) ---- */
/* attachpath(<vehicle node>)      IW4 0x67f120, C1 0x685490 */
void CODOL_Scr_AttachPath(scr_entref_t ref);
/* startpath([<vehicle node>])     IW4 0x67f360, C1 0x6858c0 */
void CODOL_Scr_StartPath(scr_entref_t ref);
/* vehicle_canturrettargetpoint(<point>, [<doSightTrace>], [<ignoreEnt>])
 * IW4 0x67fef0; returns int. */
void CODOL_Scr_VehicleCanTurretTargetPoint(scr_entref_t ref);
/* vehicle_finishdamage(inflictor, attacker, damage, dFlags, meansOfDeath,
 * weapon, point, dir, hitLoc, timeOffset, modelIndex, partName)
 * IW4 0x67f4d0 -> 0x481bd0; no return value. */
void CODOL_Scr_VehicleFinishDamage(scr_entref_t ref);
/* vehicleturretcontrolon(<player>) / vehicleturretcontroloff(<player>)
 * IW4 0x4d1b60 -> 0x421d30 and 0x4634e0 -> 0x49a8a0. */
void CODOL_Scr_VehicleTurretControlOn(scr_entref_t ref);
void CODOL_Scr_VehicleTurretControlOff(scr_entref_t ref);

/* ---- vehicle spawner method (receiver: entity created with spawnflag 2) ---- */
/* vehicle_dospawn([<vehicleType>], [<owner>])  IW4 0x680280 -> 0x420670;
 * returns the spawned vehicle entity, or undefined when the spawner already
 * produced a vehicle this server frame. */
void CODOL_Scr_VehicleDoSpawn(scr_entref_t ref);

/* ---- player methods ---- */
/* startac130() / stopac130()      IW4 0x48f850 / 0x450b40 */
void CODOL_Scr_StartAC130(scr_entref_t ref);
void CODOL_Scr_StopAC130(scr_entref_t ref);
/* remotecamerasoundscapeoff()     IW4 0x5f54d0 */
void CODOL_Scr_RemoteCameraSoundscapeOff(scr_entref_t ref);
/* canplayerplacesentry()          IW4 0x5dca90 -> 0x489fe0; returns an
 * array with keys "result", "origin", "angles". */
void CODOL_Scr_CanPlayerPlaceSentry(scr_entref_t ref);

/* ---- turret methods (receiver: entity with pTurretInfo) ---- */
/* maketurretsolid()               IW4 0x5ed520 -> 0x4038e0 */
void CODOL_Scr_MakeTurretSolid(scr_entref_t ref);
/* setturretminimapvisible(<bool>) IW4 0x5ed0d0 -> 0x4b1310 */
void CODOL_Scr_SetTurretMinimapVisible(scr_entref_t ref);

/* ---- native state and lifecycle consumed by the engine ---- */
/* Path following. Reset at level start (beside CODOL_InitVehicleNodes) and
 * when a vehicle entity is freed. Think returns 1 when the vehicle is on a
 * running path and this call already produced its position, angles and
 * velocity for the frame; the retained physics integration is then skipped
 * for that vehicle. RunFrame walks the vehicle pool for a caller that cannot
 * reach the per-vehicle think. */
void CODOL_VehiclePath_Reset(void);
void CODOL_VehiclePath_EntityFreed(unsigned entnum);
int CODOL_VehiclePath_Think(struct gentity_s *vehicle);
void CODOL_VehiclePath_RunFrame(void);
/* Vehicle damage script callback (IW4 Scr_VehicleDamage lineage).
 * LoadCallback resolves maps/mp/gametypes/_callbacksetup::CodeCallback_VehicleDamage
 * once the gametype scripts are loaded. Callback takes G_Damage's argument
 * list and returns 1 when the script thread was run instead of applying the
 * damage natively; vehicle_finishdamage re-enters G_Damage under a gate. */
void CODOL_VehicleDamage_LoadCallback(void);
int CODOL_VehicleDamageCallback(struct gentity_s *targ, struct gentity_s *inflictor,
    struct gentity_s *attacker, const float *dir, const float *point, int damage,
    int dflags, int mod, int weapon, int hitLoc, unsigned int modelIndex,
    unsigned int partName, int timeOffset);
/* Turret controller bookkeeping (gunner ride slot owner). */
void CODOL_VehicleTurretControl_Reset(void);
void CODOL_VehicleTurretControl_ClientLeft(int clientNum);
struct gentity_s *CODOL_VehicleTurretController(const struct gentity_s *vehicle);
/* Helicopter think: aim a vehicleTurretControlOn turret along its
 * controller's view and notify "turret_fire" while he holds attack. */
void CODOL_VehicleTurretControllerThink(struct gentity_s *vehicle);
/* Per-client remote view flags produced by the player methods above. */
int CODOL_PlayerAC130Active(int clientNum);
int CODOL_PlayerRemoteCameraSoundscape(int clientNum);
void CODOL_PlayerRemoteView_ResetClient(int clientNum);
void CODOL_PlayerRemoteView_ResetAll(void);
/* Turret minimap visibility produced by setturretminimapvisible. */
int CODOL_TurretMinimapVisible(const struct gentity_s *turret);
void CODOL_TurretMinimap_EntityFreed(unsigned entnum);
void CODOL_TurretMinimap_ResetAll(void);

/* Vehicle node record accessors. Implemented by the owner of the class-3
 * vehicle node store (src/codol_script_vehicle_nodes.c); see the parent
 * patch in the worker report. Count is the number of retained records,
 * Value returns the raw map key text of record index or NULL. */
unsigned CODOL_VehicleNodeCount(void);
const char *CODOL_VehicleNodeValue(unsigned index, const char *key);

#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
#endif
