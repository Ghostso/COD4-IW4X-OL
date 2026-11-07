/* Death / killcam / follow lifecycle trace.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_KILLCAM_TRACE_H
#define CODOL_KILLCAM_TRACE_H

#ifdef __cplusplus
extern "C" {
#endif

/* One line per human client per *change* of the killcam/follow state tuple,
 * gated on CODOL_TRACE_ON() (dvar codol_debugTrace, default off) and capped
 * for the whole process.  Safe to call more than once per server frame: the
 * sweep self-limits on level.time.
 *
 * What it answers, and why each field is in the line:
 *
 *   ss      sess.sessionState        0 playing 1 dead 2 spectator 3 intermission.
 *                                    ClientEndFrame only runs SpectatorClientEndFrame
 *                                    for 2, so this decides whether a killcam can be
 *                                    published at all.
 *   fsc     sess.forceSpectatorClient  what _killcam.gsc sets (attackerNum / -1).
 *   sc      gclient->spectatorClient   the engine's follow target.  Written from
 *                                    fsc by SpectatorClientEndFrame and by
 *                                    Cmd_FollowCycle_f; ClearKillcamState() in GSC
 *                                    cannot clear it.
 *   kce     sess.killCamEntity       -1 or the projectile entity.
 *   arch    sess.archiveTime (ms)    >0 selects the archived (replay) arm.
 *   psoff   sess.psOffsetTime (ms)
 *   dT      ps.deltaTime             THE killcam state on the wire: C1 0x0046be37
 *                                    enters its killcam when this is nonzero and
 *                                    0x0046bf0c leaves when it returns to zero.
 *   pkce    ps.killCamEntity         wire +0xa54; C1 0x0046c0b8 treats 2047 as none.
 *   psCl    ps.clientNum             != the client's own number means the playerstate
 *                                    currently belongs to somebody else (follow copy);
 *                                    ClientEndFrame respawns the client when it sees
 *                                    that on a non-spectator frame.
 *   pm      ps.pm_type               >= 8 is what makes C1 render third person
 *                                    (CG_CalcThirdPerson 0x004771e0 / 0x00477263).
 *   hp      ps.stats[0]
 *   org     ps.origin                where the camera actually is.
 */
void CODOL_KillcamTraceFrame(void);

#ifdef __cplusplus
}
#endif
#endif
