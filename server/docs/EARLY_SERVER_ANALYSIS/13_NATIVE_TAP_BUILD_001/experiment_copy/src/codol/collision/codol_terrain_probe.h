/* Analytic terrain surface height under a point, from the clipmap's own
 * triangle list. SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Diagnostic only: it answers "does our player trace return the surface our own
 * triangle data describes?", which separates `our trace is approximating' from
 * `our data differs from C1's'. See codol_terrain_probe.c for the measured
 * state that motivates it and for the pre-registered pass/fail thresholds.
 *
 * Returns 0 when no terrain triangle covers the point (a brush floor, or off
 * the terrain entirely) -- that is not a failure, it is "not applicable", and
 * the caller must not fold it into a statistic.
 */
#ifndef CODOL_TERRAIN_PROBE_H
#define CODOL_TERRAIN_PROBE_H
#ifdef __cplusplus
extern "C" {
#endif
int CODOL_TerrainHeightUnder(const float *origin, float *out_height,
                             int *out_tri, float *out_nz, int *out_scanned);
/* Two points, one scan.  `ref_z` is the reference height BOTH samples are
 * culled against, so the two heights are comparable: culling each against its
 * own z would bias the client-side sample by exactly the quantity being
 * measured.  Returns a bitmask: 1 = a valid, 2 = b valid; only 3 is usable. */
int CODOL_TerrainHeightUnder2(const float *a_xy, const float *b_xy, float ref_z,
                              float *out_a_z, float *out_b_z,
                              int *out_a_tri, float *out_a_nz);
#ifdef __cplusplus
}
#endif
#endif
