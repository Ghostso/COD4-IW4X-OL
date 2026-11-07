/* Does our own player trace return the surface our own terrain data describes?
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Measured state going in (docs/CODOL_IMPLEMENTATION_PASS.md, the ground
 * thread): a walking player's published origin agrees with C1's predicted
 * origin to 0.0000 units vertically on flat ground and differs by 0.066 units
 * on jagged ground, with `gnfrac` pinned at exactly 0.5000 in both cases -- so
 * the server is settled precisely on whatever surface its trace reports, and
 * only where the ground is uneven is that surface somewhere the client is not.
 *
 * Everything that could explain it inside the mover has been excluded:
 * PM_ProjectVelocity cannot rotate the azimuth and its scale is 0.012% at the
 * measured tilt, step_slide contributes exactly zero horizontal displacement
 * (`dxy` 0.0000 on 639 of 639 frames) and selects the same branch byte (0x36)
 * on flat and tilted ground alike, and the collision phase that answers is the
 * same everywhere (`gnhit 1/2046`, `cf 0x1`).
 *
 * So the question left is whether the retained cm_* trace agrees with the
 * triangle list we loaded and handed it. This walks that triangle list
 * directly -- the SAME `cm.verts` / `cm.triIndices` the trace consumes -- finds
 * the terrain surface under the player analytically, and reports the
 * difference. It deliberately reuses the trace's own data rather than the
 * staging copy, so a disagreement is the trace approximating, not two decodes
 * diverging.
 *
 * Pre-registered before the first run, so the result cannot be read after the
 * fact (per-frame, still-view, unblocked, moving, split on |n_xy| at 0.005):
 *   flat    <= 0.001 u   CONTROL. A flat surface is its own best plane, so any
 *                        approximation is invisible there. If flat fails, the
 *                        PROBE is broken and that is what gets reported -- not
 *                        a finding.
 *   tilted  >= 0.02  u   positive, and should account for the 0.066 u seen.
 *   between              inconclusive, and will be called that.
 */
#ifdef CODOL_SERVER
#include "q_shared.h"
#include "qcommon.h"
#include "cm_local.h"
#include "codol_terrain_probe.h"
#include <math.h>

/* Barycentric containment in the XY plane, with the triangle's plane height at
 * that point. Degenerate (zero-area in XY) triangles are vertical walls and
 * carry no height for a point beneath the player, so they are skipped. */
static int tri_height_xy(const float *a, const float *b, const float *c,
                         float x, float y, float *out_z, float *out_nz)
{
    float v0x = b[0]-a[0], v0y = b[1]-a[1];
    float v1x = c[0]-a[0], v1y = c[1]-a[1];
    float det = v0x*v1y - v1x*v0y;
    float px, py, l1, l2, l0, nx, ny, nz, len;
    if(det > -0.0001f && det < 0.0001f) return 0;
    px = x-a[0]; py = y-a[1];
    l1 = (px*v1y - v1x*py)/det;
    l2 = (v0x*py - px*v0y)/det;
    l0 = 1.0f - l1 - l2;
    /* A small negative tolerance keeps a player standing exactly on a shared
     * edge from falling between two triangles and reporting "no surface". */
    if(l0 < -0.0005f || l1 < -0.0005f || l2 < -0.0005f) return 0;
    /* Anchored at a, NOT the symmetric a.z*l0 + b.z*l1 + c.z*l2.
     *
     * Mathematically identical, but on a horizontal triangle both deltas are
     * exactly zero and this returns a[2] BIT-EXACTLY, whereas the symmetric
     * form evaluates z*(l0+l1+l2) and l0 is computed as 1-l1-l2, so the weights
     * sum to 1 only to within rounding. At a world height of ~150 that is a few
     * ULP, about 1.5e-5 per ULP -- which would print as a non-zero `projdz` on
     * FLAT ground and, by the registered rule, void the session as a broken
     * probe. The control has to be exact for the right reason. */
    *out_z = a[2] + l1*(b[2]-a[2]) + l2*(c[2]-a[2]);
    nx = v0y*(c[2]-a[2]) - (b[2]-a[2])*v1y;
    ny = (b[2]-a[2])*v1x - v0x*(c[2]-a[2]);
    nz = det;
    len = (float)sqrt((double)(nx*nx + ny*ny + nz*nz));
    *out_nz = len > 0.0f ? nz/len : 0.0f;
    if(*out_nz < 0.0f) *out_nz = -*out_nz;
    return 1;
}

int CODOL_TerrainHeightUnder2(const float *a_xy, const float *b_xy, float ref_z,
                              float *out_a_z, float *out_b_z,
                              int *out_a_tri, float *out_a_nz)
{
    int i, p, besta = -1, bestb = -1;
    float az = 0.0f, bz = 0.0f, anz = 0.0f;
    if(!a_xy || !b_xy || cm.triCount <= 0 || !cm.triIndices || !cm.verts) return 0;
    if(cm.partitionCount <= 0 || !cm.partitions) return 0;
    /* Walk the PARTITIONS, not the flat triangle array: a triangle index is a
     * u16 inside its partition's 1024-vertex block, exactly as the trace reads
     * it (C1 0x00583e30 / _cm_mesh.asm). Resolving against cm.verts[0] would
     * relocate every triangle of every partition whose block is nonzero. */
    for(p = 0; p < cm.partitionCount; ++p) {
        const CollisionPartition_t *pa = &cm.partitions[p];
        const float (*verts)[3] = (const float (*)[3])
            (cm.verts + (unsigned)pa->vertBlock * 1024u);
        unsigned t;
        for(t = 0; t < pa->triCount; ++t) {
            const uint16_t *idx;
            const float *v0, *v1, *v2;
            float z, nz;
            i = pa->firstTri + (int)t;
            if(i < 0 || i >= cm.triCount) continue;
            idx = cm.triIndices + 3*i;
            if((unsigned)pa->vertBlock * 1024u + idx[0] >= cm.vertCount ||
               (unsigned)pa->vertBlock * 1024u + idx[1] >= cm.vertCount ||
               (unsigned)pa->vertBlock * 1024u + idx[2] >= cm.vertCount)
                continue;
            v0 = verts[idx[0]]; v1 = verts[idx[1]]; v2 = verts[idx[2]];
            if(tri_height_xy(v0, v1, v2, a_xy[0], a_xy[1], &z, &nz) &&
               z <= ref_z + 0.25f && (besta < 0 || z > az)) {
                az = z; anz = nz; besta = i;
            }
            if(tri_height_xy(v0, v1, v2, b_xy[0], b_xy[1], &z, &nz) &&
               z <= ref_z + 0.25f && (bestb < 0 || z > bz)) {
                bz = z; bestb = i;
            }
        }
    }
    if(besta >= 0) {
        if(out_a_z) *out_a_z = az;
        if(out_a_tri) *out_a_tri = besta;
        if(out_a_nz) *out_a_nz = anz;
    }
    if(bestb >= 0 && out_b_z) *out_b_z = bz;
    return (besta >= 0 ? 1 : 0) | (bestb >= 0 ? 2 : 0);
}

int CODOL_TerrainHeightUnder(const float *origin, float *out_height,
                             int *out_tri, float *out_nz, int *out_scanned)
{
    int i, p, best = -1;
    float best_z = 0.0f, best_nz = 0.0f;
    if(!origin || cm.triCount <= 0 || !cm.triIndices || !cm.verts) return 0;
    if(cm.partitionCount <= 0 || !cm.partitions) return 0;
    /* Partition order, for the block-relative index reason above. */
    for(p = 0; p < cm.partitionCount; ++p) {
        const CollisionPartition_t *pa = &cm.partitions[p];
        const float (*verts)[3] = (const float (*)[3])
            (cm.verts + (unsigned)pa->vertBlock * 1024u);
        unsigned t;
        for(t = 0; t < pa->triCount; ++t) {
            const uint16_t *idx;
            float z, nz;
            i = pa->firstTri + (int)t;
            if(i < 0 || i >= cm.triCount) continue;
            idx = cm.triIndices + 3*i;
            if((unsigned)pa->vertBlock * 1024u + idx[0] >= cm.vertCount ||
               (unsigned)pa->vertBlock * 1024u + idx[1] >= cm.vertCount ||
               (unsigned)pa->vertBlock * 1024u + idx[2] >= cm.vertCount)
                continue;
            if(!tri_height_xy(verts[idx[0]], verts[idx[1]], verts[idx[2]],
                              origin[0], origin[1], &z, &nz)) continue;
            /* The surface the player is standing on is the highest one that is
             * not above their feet by more than the ground trace's own reach.
             * Anything higher is a bridge or an overhang the trace would not
             * have hit. */
            if(z > origin[2] + 0.25f) continue;
            if(best < 0 || z > best_z) { best_z = z; best_nz = nz; best = i; }
        }
    }
    if(best < 0) return 0;
    if(out_height) *out_height = best_z;
    if(out_tri) *out_tri = best;
    if(out_nz) *out_nz = best_nz;
    if(out_scanned) *out_scanned = cm.triCount;
    return 1;
}
#endif
