/* C1 ADS sway phase: the server-side producer of playerState +0x4a0.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_SWAY_PHASE_H
#define CODOL_SWAY_PHASE_H
#ifdef CODOL_SERVER
#include "q_shared.h"

struct playerState_s;

/* Returns the authoritative weapon-sway phase for this playerstate, advancing
 * the per-client accumulator when ps->commandTime has moved since the previous
 * call. Idempotent for repeated calls at the same commandTime, which is the
 * normal case: roughly half of all snapshots republish an unchanged
 * commandTime (docs/CODOL_SWAY_CAUSE_SWEEP_20260916.md R1d). */
int CODOL_SwayPhase(const struct playerState_s *ps);

/* Drops the accumulator for one client, so the next call re-seeds. Call on
 * spawn/respawn and on a client slot being reused. Safe with an out-of-range
 * clientNum. */
void CODOL_SwayPhaseReset(int clientNum);

/* Drops the whole resolved-definition cache, which is keyed by a raw WeaponDef
 * pointer. Call whenever those definitions can be freed -- today that is the
 * asset-category teardown, which releases the retired archives and the
 * composed weapon cores built from them. */
void CODOL_SwayPhaseResetDefs(void);

#endif /* CODOL_SERVER */
#endif
