#ifndef CODOL_SCRIPT_TURRET_TARGET_H
#define CODOL_SCRIPT_TURRET_TARGET_H
#ifdef CODOL_SERVER

#include "scr_vm.h"

/* Slot count of the retained turretInfo pool. Must stay equal to the
 * "cmp eax, 0x20" slot limit and the "turretInfo: resb" reservation in
 * src/asmsource/_g_misc_mp.asm. */
#define CODOL_MAX_TURRETS 32

/* sizeof(turretInfo_s) with the CoDOL target/fire block appended. Must equal
 * TURRET_INFO_SIZE in src/asmsource/_g_misc_mp.asm, which drives the pool
 * reservation, the free-slot stride and the allocation memset; the .cpp
 * static-asserts it against the real struct size. */
#define CODOL_TURRET_INFO_SIZE 0xd8

#ifdef __cplusplus
extern "C" {
#endif

struct gentity_s;
struct turretInfo_s;

/* GSC methods on a turret entity. IW4 handlers:
 *   settargetentity 0x5ed140, cleartargetentity 0x5ed1f0,
 *   getturrettarget 0x5ed260, startfiring 0x5ecbe0, stopfiring 0x5ecc50,
 *   isfiringturret 0x5eccc0, shootturret 0x5ece80,
 *   setconvergencetime 0x5ed390. */
void CODOL_Scr_SetTargetEntity(scr_entref_t ref);
void CODOL_Scr_ClearTargetEntity(scr_entref_t ref);
void CODOL_Scr_GetTurretTarget(scr_entref_t ref);
void CODOL_Scr_StartFiring(scr_entref_t ref);
void CODOL_Scr_StopFiring(scr_entref_t ref);
void CODOL_Scr_IsFiringTurret(scr_entref_t ref);
void CODOL_Scr_ShootTurret(scr_entref_t ref);
void CODOL_Scr_SetConvergenceTime(scr_entref_t ref);
void CODOL_Scr_SetAutoRotationDelay(scr_entref_t ref);
void CODOL_Scr_StartBarrelSpin(scr_entref_t ref);
void CODOL_Scr_StopBarrelSpin(scr_entref_t ref);
void CODOL_Scr_SetMode(scr_entref_t ref);
void CODOL_Scr_GetMode(scr_entref_t ref);
void CODOL_Scr_SetTurretTeam(scr_entref_t ref);
void CODOL_Scr_SetTurretModeChangeWait(scr_entref_t ref);
void CODOL_Scr_SetSentryCarried(scr_entref_t ref);
void CODOL_Scr_SetSentryOwner(scr_entref_t ref);
void CODOL_Scr_SetScanningPitch(scr_entref_t ref);

/* Producer/consumer called from retained assembly in _g_misc_mp.asm.
 * Tracks the scripted target, drives the gun angles, runs the fire state
 * machine. Script shootturret produces shots. Returns qtrue when it owned the gun
 * angles this think, in which case the retained idle-drift path is skipped
 * for that frame. */
qboolean CODOL_TurretTarget_Think(struct gentity_s *entity);

/* Apply weapon defaults and map keys while this entity's SpawnVar is active. */
void CODOL_TurretTarget_Spawn(struct gentity_s *entity);

/* Releases both entity handles before G_FreeTurret releases the slot. */
void CODOL_TurretTarget_Free(struct gentity_s *entity);

/* Level init: raw-clears target state without touching the EntHandle
 * registry (which G_InitTurrets may run either side of EntHandle::Init). */
void CODOL_TurretTarget_ResetAll(void);

/* Turret overheat / barrel spin / mode, src/codol_turret_heat.cpp. C1 runs the
 * spin update and then the heat update from its turret think (0x57dc87 /
 * 0x57dc8e); CanFire is the fire gate inside C1's shot producer 0x57b050,
 * which every shot goes through. SetMode/GetMode are C1's setmode 0x54e0d0
 * and getmode 0x54e330. */
void CODOL_TurretHeat_Update(struct gentity_s *entity, struct gentity_s *user);
void CODOL_TurretHeat_ThinkClient(struct gentity_s *entity, struct gentity_s *user);
qboolean CODOL_TurretHeat_CanFire(struct gentity_s *entity);
void CODOL_TurretHeat_NoteShot(struct gentity_s *entity);
void CODOL_TurretHeat_Defaults(struct turretInfo_s *turret);
qboolean CODOL_TurretHeat_SetMode(struct gentity_s *entity, const char *mode);
const char *CODOL_TurretHeat_GetMode(struct gentity_s *entity);
void CODOL_TurretHeat_Reset(struct turretInfo_s *turret);

#ifdef __cplusplus
}
#endif

#endif
#endif
