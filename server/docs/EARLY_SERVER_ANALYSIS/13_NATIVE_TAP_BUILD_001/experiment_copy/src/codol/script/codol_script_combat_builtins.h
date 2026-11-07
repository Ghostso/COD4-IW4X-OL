/* SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_SCRIPT_COMBAT_BUILTINS_H
#define CODOL_SCRIPT_COMBAT_BUILTINS_H
#include "scr_vm.h"
#include "g_public_mp.h"
#include <stdint.h>
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif

/* ---- Script builtins (registered from Scr_InitFunctions' CODOL block) ---- */

/* Methods on a rocket entity (classname "rocket"). */
void CODOL_Scr_MissileSetTargetEnt(scr_entref_t ref);
void CODOL_Scr_MissileSetTargetPos(scr_entref_t ref);
/* Function: glassradiusdamage(pos, radius, maxDamage, minDamage). */
void CODOL_Scr_GlassRadiusDamage(void);
/* Method on any entity: setcanradiusdamage(bool). */
void CODOL_Scr_SetCanRadiusDamage(scr_entref_t ref);
/* T5 MP entity method: damage, source, attacker, inflictor, headshot,
 * means of death, flags, weapon. Trailing arguments are optional. */
void CODOL_Scr_DoDamage(scr_entref_t ref);
void CODOL_Scr_StartPoisoning(scr_entref_t ref);
void CODOL_Scr_StopPoisoning(scr_entref_t ref);
void CODOL_Scr_IsPoisoned(scr_entref_t ref);
/* Method on a script_model: physicslaunchserver(contactPoint, force). */
void CODOL_Scr_PhysicsLaunchServer(scr_entref_t ref);
/* Player methods (IW4 riot shield model attachment). */
void CODOL_PlayerCmd_AttachShieldModel(scr_entref_t ref);
void CODOL_PlayerCmd_DetachShieldModel(scr_entref_t ref);
void CODOL_PlayerCmd_MoveShieldModel(scr_entref_t ref);
/* CoDOL overlay functions:
 *   codol_fire_nearest(src, range, damage, owner, weapon [, mod]) -> 1 hit / 0
 *   codol_radiusdamage(pos, radius, max, min, owner, weapon [, mod]) -> hit count */
void CODOL_Scr_FireNearest(void);
void CODOL_Scr_RadiusDamage(void);

/* ---- Radius-damage opt-out (setcanradiusdamage) ----
 * Stored in gentity_t.flags. The retained IW3 flag set does not use this
 * bit; G_FreeEntity's memset clears it with the entity. */
#define CODOL_FL_NO_RADIUS_DAMAGE 0x40000000
int CODOL_EntityCanRadiusDamage(const gentity_t *ent);

/* ---- Server physics launch lifecycle ----
 * Launched script_models are moved by the retained G_RunItem path
 * (G_RunFrameForEntity dispatches every physicsObject entity to it). This
 * frame function detects rest, restores the stationary trajectories, clears
 * physicsObject and notifies "physics_finished". Call once per simulation
 * frame from G_RunFrame (next to CODOL_RunSoundFrame). Reset at map change. */
void CODOL_RunPhysicsLaunchFrame(int time);
void CODOL_ResetPhysicsLaunches(void);

/* ---- Riot shield attachment state ----
 * Tag string index (SL) the shield model is attached to, 0 when none.
 * "Raised" means attached to tag_weapon_left. */
unsigned CODOL_PlayerShieldTag(unsigned clientNum);
int CODOL_PlayerShieldRaised(unsigned clientNum);
void CODOL_ResetPlayerShieldState(unsigned clientNum);

/* ---- C-callable EntHandle setter ----
 * Implemented by the parent in src/enthandle.cpp:
 *   extern "C" void CODOL_EntHandleSetEnt(EntHandle *h, gentity_t *ent){ h->setEnt(ent); } */
void CODOL_EntHandleSetEnt(EntHandle *handle, gentity_t *ent);

#ifdef __cplusplus
}
#endif
#pragma pack(pop)
struct gentity_s;
void CODOL_NotifyWeaponFired(struct gentity_s *ent,int weapon);
#endif
