/* RC-XD wheel spin: the server animation producer C1 relies on.
 *
 * C1 1.1.1.13 does not spin a ground vehicle's wheels from any entity-state
 * word. Its native vehicle code only steers the front wheel tags (wire +68)
 * and bobs all six along the suspension trace (67d5ac..67d7b8); the one
 * speed-driven value it accumulates, instance+34 (67cf30), is the material
 * scroll time handed to R_AddEntity (67d882..67d904). The RC-XD model instead
 * spins its wheel meshes (left/right_wheel_01_jnt front, _02_jnt back) with
 * four xanims that ship in common_mp and that C1's animtrees/vehicles.atr
 * lists: rccar_{front,back}_driving_{forward,backward}. The client learns them
 * through animlists/common.animlist (code_post_gfx_mp), whose "=vehicles"
 * block names exactly these four first, and it plays them only when the
 * server sends animation commands for the car:
 *   - C1 0x443540 gives eType 12 and 14 (like 6) the client realm-0 tree
 *     selected by entity wire +094, so a vehicle DObj has an animtree only
 *     when +094 names one;
 *   - the snapshot animation-command executor 0x443e90 (driven by 0x46aff0)
 *     applies commands to any entity with a DObj, and 0x477100 advances every
 *     snapshot entity's tree to cg.time each frame.
 * This module is that producer: it owns a server "vehicles" XAnimTree for the
 * RC-XD, drives the four clips from the car's actual forward speed, and
 * publishes every change through the existing animation journal, so a viewer
 * that enters PVS late is bootstrapped from the captured server pose.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_VEHICLE_WHEEL_ANIM_H
#define CODOL_VEHICLE_WHEEL_ANIM_H
#ifdef CODOL_SERVER
#include "codol_dog_animation.h"
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif
struct gentity_s;
struct XAnimTree_s;
/* Bind the server "vehicles" tree to a freshly attached RC vehicle and
 * rebuild its server DObj on it. 1 bound, 0 not available (logged). */
int CODOL_VehicleWheelAnimAttach(struct gentity_s *entity, float wheel_radius);
/* Once per physical vehicle frame, before the snapshot of that frame, with the
 * body's signed forward speed in inches per second. */
void CODOL_VehicleWheelAnimFrame(struct gentity_s *entity, float forward_speed, int now);
/* The tree the server DObj of this entity must be built on, or NULL. */
struct XAnimTree_s *CODOL_VehicleWheelAnimTree(const struct gentity_s *entity);
/* Appends the live bound vehicles to an actor capture-source list; never
 * refuses, it simply stops at capacity. */
unsigned CODOL_VehicleWheelAnimCaptureSources(codol_dog_anim_capture_source_t *out,
                                              unsigned capacity);
void CODOL_VehicleWheelAnimEntityFreed(const struct gentity_s *entity);
void CODOL_VehicleWheelAnimReset(void);
#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
#endif
