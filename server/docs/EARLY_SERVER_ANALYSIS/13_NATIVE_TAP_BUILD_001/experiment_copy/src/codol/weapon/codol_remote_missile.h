/*
 * Native consumer of the CoDOL controls link: a player whose controls are
 * linked to a missile steers it with the two remote-angle bytes its client
 * puts in every accepted command.
 *
 * See src/codol_remote_missile.c for the measured C1 evidence, and
 * the native trajectory consumer for the IW4 speed/boost implementation.
 * C1's speed consumer has not been located; runtime parity remains unverified.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
#ifndef __CODOL_REMOTE_MISSILE_H__
#define __CODOL_REMOTE_MISSILE_H__

#ifdef CODOL_SERVER

#include "q_shared.h"
#pragma pack(push, 8)

#ifdef __cplusplus
extern "C" {
#endif

struct gentity_s;
struct usercmd_s;

typedef struct {
    unsigned char armed, boosted;
} codol_remote_speed_state_t;
/* Controls mode is distinct from owner-handle lifetime. C1 explicitly sets
 * and clears it for missile targets in controlslinkto/controlsunlink. */
void CODOL_SetMissileRemoteMode(unsigned entity, int enabled);
int CODOL_MissileRemoteMode(unsigned entity);
void CODOL_ResetMissileRemoteState(unsigned entity);
void CODOL_ResetMissileRemoteStates(void);
/* Called by native MissileTrajectory after its launch/type/handler gates.
 * Returns1 after producing a remote trajectory, zero for normal movement. */
int CODOL_RemoteMissileTrajectory(struct gentity_s *missile, vec3_t out);
/* Bounded native dispatch evidence; does not alter the missile or its input. */
void CODOL_RemoteMissileTraceDispatch(struct gentity_s *missile);
/* IW4 reference speed step, using missile-owned state in the trajectory path.
 * Caller supplies resolved dvars and accepted CoDOL buttons (zero without a
 * controls owner) and the length of the server frame being advanced (IW4's
 * fixed 0.05 at 20fps). Returns1 when a boost event must be emitted. */
int CODOL_RemoteMissileSpeedStep(codol_remote_speed_state_t *state,
    unsigned buttons, const vec3_t angles, vec3_t velocity, vec3_t position,
    float normal_speed, float boost_speed, float acceleration, float deceleration,
    float frame_seconds);

/* The missile this client is remote-controlling, or NULL. Reproduces the
 * resolution C1 0x50c870 performs: the camera-linked entity, which must also
 * carry a controls handle and be a missile. */
struct gentity_s *CODOL_RemoteMissileControlledEntity(int clientNum);

/* Per-accepted-command steering, the equivalent of the call C1's
 * ClientThink_real makes at 0x50cfea, after activation. Pass the time delta
 * that ClientThink_real computed before pmove advanced ps->commandTime,
 * with the same command's accepted-input binding still active. Do not
 * recompute from the updated playerState or steer before scripts run.
 * Doing nothing is the normal outcome: it returns immediately for a client
 * that is not steering a missile. */
void CODOL_RemoteMissileClientThink(struct gentity_s *ent,
                                    int msec);

#ifdef __cplusplus
}
#endif

#endif /* CODOL_SERVER */
#pragma pack(pop)
#endif /* __CODOL_REMOTE_MISSILE_H__ */
