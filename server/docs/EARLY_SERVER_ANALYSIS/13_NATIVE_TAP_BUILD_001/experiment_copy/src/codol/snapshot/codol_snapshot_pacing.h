/* Per-snapshot usercmd consumption pacing.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Snapshots leave on the server's own fixed cadence, but `ps.commandTime` only
 * advances when usercmds are executed, and usercmds are executed on receipt
 * (C1's contract -- docs: "Q3 reference timing contract").  If the client
 * batches several commands into one packet, a snapshot window contains a whole
 * number of packets, so the published `ps.commandTime` advances in packet-sized
 * lumps rather than by the snapshot interval.
 *
 * C1's client turns that jitter straight into the drawn weapon-sway phase
 * (measured: phase = 3.0 x (cg.time - snapshot ps.commandTime), i.e. 3 units of
 * phase per millisecond of jitter), so +-17 ms of lumpiness becomes a visible
 * alternating sawtooth.  It is also bad for prediction agreement generally.
 *
 * This module measures the thing that has to change, BEFORE anything changes:
 *   - the distribution of per-snapshot `ps.commandTime` advance
 *   - how many usercmds and how many usermove PACKETS each window consumed
 *   - the short/long transition probabilities the defect was reported with
 *   - the snapshot wall-clock cadence, independently of the command clock
 *
 * Acceptance: the advance distribution collapses from bimodal to unimodal at
 * the snapshot interval, `near` approaches `n`, and P(short|long) falls to
 * chance.  `cmds` and `pkts` say WHERE the lumps come from: ~3 commands per
 * packet with 1 or 2 packets per window means the batching is the client's,
 * and no server-side drain rule can smooth it without deferring input.
 */
#ifndef CODOL_SNAPSHOT_PACING_H
#define CODOL_SNAPSHOT_PACING_H

#ifdef __cplusplus
extern "C" {
#endif

/* One usermove packet was parsed for this client, carrying `cmdCount` cmds. */
void CODOL_PacingPacket(unsigned client, int cmdCount);
/* One usercmd was handed to ClientThink (i.e. actually simulated). */
void CODOL_PacingExecuted(unsigned client, int commandTime);
/* A snapshot is being written; `psCommandTime` is what it publishes. */
/* `rateDelayed` is the client's rate-choke flag from its PREVIOUS snapshot:
 * a delayed snapshot is skipped by SV_SendClientMessages, which stretches the
 * wall cadence and is a completely different mechanism from the client
 * batching several usercmds into one packet.  The two predict different
 * columns, so both are reported and the capture decides. */
void CODOL_PacingSnapshot(unsigned client, int psCommandTime, int serverTime,
                          int rateDelayed);
void CODOL_PacingResetClient(unsigned client);

#ifdef __cplusplus
}
#endif
#endif
