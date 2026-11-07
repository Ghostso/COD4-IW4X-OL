/* Per-command pmove result ring + client-prediction error decomposition.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * The client tells this server its own predicted origin and the commandTime it
 * belongs to (usermove tail, src/sv_client.c).  When that disagrees with our
 * authoritative result by more than 0.1 units, SV_WriteSnapshotToClient forces
 * the hint-3 netfield group (origin, velocity, bobCycle, movementDir) with a
 * zero delta base, overriding the client's prediction: that correction is the
 * sniper-scope jitter (docs/CODOL_IMPLEMENTATION_PASS.md, 2026-09-16 20:45).
 *
 * The live 20:42 capture says the disagreement is BIMODAL -- bit-exact on the
 * median frame, with a tail worth one to four whole commands (1.8 ms median,
 * 45 ms max of travel) and a perpendicular component as large as the along
 * component.  That is not arithmetic drift; it is discrete events.  So this
 * ring keeps, per pmove SUBSTEP, everything needed to name the event:
 *   - along / perpendicular split of the error vs the travelled direction
 *     (`lat` is that split, signed; its SIGN is only meaningful on moving,
 *     divergent rows -- on stationary or in-tolerance rows it is noise)
 *   - the error as milliseconds of travel and as a travelled-distance ratio
 *   - the 66 ms subdivision index and whether the substep ended the command
 *   - the viewangles the forward/right basis was built from
 *   - the pm_flags edge inside the substep (stance / ADS / sprint / jump)
 *   - what the slide/step solver actually hit, with the plane normal
 *   - whether the native C1 pmove ran at all for that command
 */
#ifndef CODOL_PMOVE_TRACE_H
#define CODOL_PMOVE_TRACE_H

#include "codol_pmove_c1.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Called from wish() with the command scale and the resulting wish vector. */
void CODOL_PmoveTraceWish(int client, const float *wishdir, float wishspeed,
                          float cmdScale, float fwd, float right);
/* Called from PM_CmdScale with the weapon move-scale selector it actually
 * used.  `adsWeapon` is the boolean C1 0x00410234/0x00410238 tests
 * (PMF_ADS || prone-with-ADS-fraction); it, not fWeaponPosFrac, decides
 * whether moveSpeedScale (+0x670) or adsMoveSpeedScale (+0x674) applies, so a
 * one-command disagreement about it is directly visible here. */
void CODOL_PmoveTraceScale(int client, float mss, float adsmss, int adsWeapon);
/* Called from the slide/step solver with what collision actually did.  A NULL
 * normal updates only `blocked` and `stepDelta`, keeping the plane the slide
 * solver recorded for this substep. */
void CODOL_PmoveTraceCollision(int client, int blocked, float stepDelta,
                               const float *normal, float fraction, int hitType);
/* Called from the walk mover with the ground plane that actually acted on this
 * substep, at full precision, plus the azimuth change (degrees) that
 * PM_ProjectVelocity applied to the wish direction and to the velocity.
 *
 * PM_ProjectVelocity (C1 0x0040f460) scales in[0] and in[1] by the SAME factor
 * and only recomputes Z, so by construction it cannot rotate the horizontal
 * azimuth at all -- these two columns should read 0.000.  They are printed
 * precisely so that "the ground normal rotated the move" is measured instead of
 * assumed: a non-zero value refutes the reading of the code, and a zero value
 * rules the ground plane out as the source of a horizontal rotation. */
void CODOL_PmoveTraceGround(int client, const float *normal, float fraction,
                            int hitType, int hitId, unsigned sflags,
                            unsigned cflags, float projWishDeg,
                            float projVelDeg);
/* Called from PM_StepSlideMove with WHICH BRANCHES RAN and what each produced.
 *
 * The along-track error is ground-CORRELATED but not ground-dose-dependent: on
 * storm_spring, still-view unblocked frames read 0.0061 u on flat ground and
 * 0.2465 u on tilted ground, yet the error is NOT monotonic in tilt -- the
 * worst bucket is the smallest non-zero tilt and the steepest slopes are nearly
 * clean.  Whatever it is, it is triggered by LEAVING FLAT, not by how far from
 * flat, which is the shape of a branch that either runs or does not.  These are
 * the branches: the step-up probe, the down trace and its rejection, the
 * slide_dot/step_dot rollback, and the ground snap.
 *
 * `slide_xy` is the horizontal distance the plain slide produced, `final_xy`
 * what the function actually returned; their difference is the horizontal
 * displacement the step machinery added or removed on that substep. */
void CODOL_PmoveTraceStep(int client, unsigned flags, float slide_xy,
                          float final_xy, float step_up);
/* Called once per completed pmove substep, after ps->commandTime advanced. */
void CODOL_PmoveTraceCommit(const codol_pmove_c1_t *move,
                            const float *origin_before, int msec,
                            unsigned pm_flags_before, int substep, int final);
/* Called when CODOL_PmoveC1Try declines a command and the RETAINED IW3 Pmove
 * simulates it instead -- a different simulation for that whole command. */
void CODOL_PmoveTraceFallback(unsigned client, int commandTime, int reason);
/* Called from CODOL_ReadOriginVelocityFlag (src/sv_snapshot.c), at snapshot
 * build time, with the SAME two vectors the rov gate itself compares.  It must
 * not be called from SV_UserMove: the usercmds carried by that packet have not
 * been simulated yet at parse time (SV_ClientThink runs after the parse loop),
 * so the ring cannot yet hold the commandTime the client is reporting -- that
 * is why an earlier revision of this trace saw 2 divergences where the rov gate
 * saw 182.  Acceptance test: the number of divergence lines printed here must
 * equal the `toofar` count in `CoDOL rov:` over the same period. */
void CODOL_PmoveTraceReport(unsigned client, const float *serverOrigin,
                            const float *predictedOrigin, int predictedTime);
void CODOL_PmoveTraceResetClient(unsigned client);

#ifdef __cplusplus
}
#endif
#endif
