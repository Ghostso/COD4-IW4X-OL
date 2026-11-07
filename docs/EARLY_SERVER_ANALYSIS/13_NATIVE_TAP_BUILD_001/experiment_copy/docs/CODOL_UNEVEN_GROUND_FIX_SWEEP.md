# Uneven-ground jitter: candidate fixes, ranked

Research pass, 2026-09-17. Read-only: nothing under `src/codol/player/`,
`src/codol/collision/`, `src/sv_snapshot.c` or `src/sv_client.c` was edited.
New tool: `tools/codol_c1_disasm.py`. Diffs to hand to the owning worker are in
section 5.

Provenance is marked throughout: **[D]** read from C1.exe / retained asm
disassembly, **[M]** measured from the four existing captures in
`bin/home/main/`, **[I]** inferred.

---

## 0. The headline

Two results change the shape of the problem, and both came from the captures
that already exist - no playtest was spent on either.

1. **[M] The height disagreement does not scale with ground tilt.** Regressing
   `err z` on `(|n_x|+|n_y|)/n_z` over the tilted frames gives R-squared =
   0.000-0.055 in all four captures, and the *steepest* tilt quintile
   (`|n_xy|` 0.07-0.37, i.e. 4-22 degrees) has a median `|err z|` of ~0.000.
   Every candidate whose mechanism is "the two bodies rest at different heights
   *on a plane of slope theta*" predicts a magnitude proportional to theta and
   is therefore falsified. That includes the slope-proportional form of the
   capsule-versus-box lead, the one-frame ground-snap-lag model, and origin
   quantisation.

2. **[D] The trace shapes are identical.** C1's client ground trace and ours
   sweep the same volume. C1's standing player `Bounds` is `mid (0,0,35)`,
   `half (15,15,35)` (constant at `0xc3ea0c`, written by `PM_SetBounds`
   `0x00412560`), i.e. mins `(-15,-15,0)` / maxs `(15,15,70)` - byte-for-byte
   what `CODOL_PM_UpdateStanceC1` sets (`codol_pmove_c1.c:1565-1566`,
   `stance_top` 70/50/30 = C1's 70/50/30). Both trace cores derive a capsule of
   radius 15 and vertical offset 20 from that box (details in section 2).
   **The capsule-versus-box lead is dead for the standing ground trace.**

What is left, and what section 1 argues is the most probable answer, is that
there is **no independent height bug at all**: the universal horizontal error -
the "parked" perpendicular/along residual - projects onto a non-planar height
field. Flat ground projects it to exactly zero, which is why flat is bit-exact;
jagged ground projects it to something, which is why jagged is never exact.
That hypothesis is cheap to test decisively and should be tested before
anything else on this list is built.

---

## 1. What the existing captures actually say

Filter used everywhere below: de-duplicated `CoDOL pmerr` lines, `RING-MISS`
dropped, `spd > 10`, `walk 1`, `gn.z > 0.5`; tilt split on `|n_xy|` at 0.005.

### M1 - flat is bit-exact, tilted never is

| capture | n_flat | n_tilt | flat p25/p50/p75 | tilt p10 | tilt p50 |
|---|---|---|---|---|---|
| stepinstr | 53 | 423 | 0.0000 / 0.0000 / 0.0008 | 0.0062 | 0.0660 |
| puddle | 76 | 435 | 0.0000 / 0.0000 / 0.0000 | 0.0055 | 0.0627 |
| terrprobe | 70 | 213 | 0.0000 / 0.0000 / 0.0000 | - | 0.0688 |
| reverify | 97 | 160 | 0.0000 / 0.0000 / 0.0000 | - | 0.2086 |

On flat ground the client's predicted z equals ours to every printed digit.
On tilted ground **even the best decile is non-zero**. Whatever the mechanism
is, it is not "sometimes"; it engages on every non-axial frame.

### M2 - no dependence on tilt magnitude (the key negative)

`err z` regressed on `(|n_x|+|n_y|)/n_z`, no intercept:

| capture | slope | R-squared | median `err z` in the steepest quintile |
|---|---|---|---|
| stepinstr | -0.582 | 0.048 | -0.0110 (`|n_xy|` 0.020-0.244) |
| puddle | -0.204 | 0.055 | -0.0026 (0.057-0.365) |
| terrprobe | -0.014 | 0.000 | -0.0002 (0.070-0.321) |
| reverify | -0.110 | 0.012 | -0.0057 (0.082-0.365) |

A box/capsule rest-height difference at r = 15 would give a slope of about
-15 and a clean monotone trend. There is neither.

### M3 - it is not a seam-crossing transient

Splitting on whether the ground normal changed since the previous frame:

| capture | tilt + normal changed | tilt + normal unchanged |
|---|---|---|
| stepinstr | med 0.1099, n=62 | med 0.0602, n=807 |
| puddle | med 0.0487, n=109 | med 0.0627, n=759 |
| terrprobe | med 0.0341, n=54 | med 0.0837, n=370 |
| reverify | med 0.0574, n=48 | med 0.2542, n=263 |

The error is at least as large on frames that stayed on one triangle. It is a
standing state, not an event at a seam.

### M4 - the local plane explains about 7% of it

Reconstructing `err_x`, `err_y` from `along`/`lat` and the travel direction
(view yaw composed with `f`/`r`), the height a shared plane would demand is
`-(err . n_xy)/n_z`. Median of that term is **0.0042-0.0055**; median
`|err z|` is **0.063-0.097**. The residual - a genuine surface-height
disagreement - is:

| capture | flat residual (med / medAbs) | tilt residual (med / medAbs) | tilt p75 | tilt p90 |
|---|---|---|---|---|
| stepinstr | +0.0000 / 0.0000 | -0.0614 / 0.0671 | -0.0066 | +0.0038 |
| puddle | +0.0000 / 0.0000 | -0.0422 / 0.0528 | -0.0002 | +0.0078 |
| terrprobe | +0.0000 / 0.0000 | -0.0600 / 0.0628 | -0.0002 | +0.0051 |
| reverify | +0.0000 / 0.0000 | -0.0563 / 0.0817 | -0.0000 | +0.0033 |

Two facts to hold onto: the residual is **identically zero on flat** (median,
p25 and p75 all exactly 0.0000), and it is **one-sided** - p90 is barely above
zero, so the server's foot is essentially never *above* the client's. `err =
serverOrigin - predictedOrigin` (`codol_pmove_trace.c:348`), so **the server
sits lower.**

### M5 - the structure is plateaus, not noise

A contiguous tilted walk (`stepinstr`, t 33224 to 33435, one normal,
`|n_xy| = 0.01078`):

```
t33224  errz -0.0719  along -0.4639
t33257  errz -0.0709  along -0.4494
t33292  errz -0.0710  along -0.4644
t33327  errz -0.0732  along -0.4875
t33363  errz -0.0743  along -0.4968
t33399  errz -0.0377  along -0.1618
t33435  errz -0.0378  along -0.1661
```

`err z` holds a stable value for as long as `along` holds its value, and steps
when `along` steps. The same normal produced -0.071, -0.038 and (later) -0.069
at different places. So the offset is a function of *where* and of *how far
behind*, not of the surface's slope.

### M6 - `err z` tracks the horizontal error

Quiet regime only (`|err z| < 0.2`, `|along| < 1`, `|err_xy| > 0.02`), fitting
`|err z| = k * |err_xy|`:

| capture | k | R-squared | median ratio |
|---|---|---|---|
| stepinstr | 0.0698 | 0.402 | 0.058 |
| puddle | 0.0422 | 0.192 | 0.067 |
| terrprobe | 0.0416 | 0.420 | 0.071 |
| reverify | 0.0149 | 0.113 | 0.045 |
| **pooled (n=718)** | **0.0449** | - | **0.060** |

The implied effective gradient is about 0.06 (3.4 degrees) against a resting
triangle slope of 0.011-0.019 (0.6-1.1 degrees) - i.e. the height field
*around* the contact is an order of magnitude rougher than the triangle the
feet are on. That is exactly what "jagged" means.

### M7 - the force gate is already saturated on tilted ground

The 3D gate fires on 851 of 854 tilted moving frames (`|err| > 0.1`), driven by
the parked perpendicular residual, not by z. So every tilted frame is measured
*one frame after* a forced correction; `err z` is a fresh single-frame
quantity, not an accumulation.

### M8 - refined acceptance baseline

With the filter above (de-dup plus `RING-MISS` dropped), per session:

| capture | n_flat | n_tilt | P_flat | P_tilt | dP |
|---|---|---|---|---|---|
| stepinstr | 53 | 423 | 0.170 | 0.794 | 0.625 |
| puddle | 76 | 435 | 0.118 | 0.795 | 0.677 |
| terrprobe | 70 | 213 | 0.100 | 0.822 | 0.722 |
| reverify | 97 | 160 | 0.124 | 0.750 | 0.626 |

**dP = 0.662 +/- 0.046** (sd over four sessions) - materially tighter than the
0.706 +/- 0.093 on record, because de-duplicating the ring lines and dropping
`RING-MISS` removes most of the between-session variance. Two consequences: the
dP < 0.15 target is unchanged and still far outside the noise, and the
`n_flat >= 30` gate is met by all four captures under this filter (it was not
under the looser one).

---

## 2. What the client actually does (disassembly)

All addresses are C1.exe 1.1.1.13, ImageBase 0x400000, read with
`tools/codol_c1_disasm.py`.

| what | where | finding |
|---|---|---|
| pmove trace handler table | `0x00cd8168` | 3 entries, 8 bytes each: `{0x00486620, 0}`, `{0x0052d4e0, 0x0050d570}`, `{0x0052d4e0, 0x0050d570}`. `pm->handler` is `byte [pm+0x120]`. |
| `CG_TraceCapsule` | `0x00486620` | thin shim to `0x00486370` |
| trace signature | `0x00412388`, `0x004123e8`, `0x0041247a`, `0x00408d31` | `(trace_t*, const float *start, const float *end, Bounds*, int passEntityNum, int contentmask)` - **one `Bounds`, not mins/maxs**. `Bounds` = `midPoint[3]` at +0, `halfSize[3]` at +0xc. `isPoint` is `halfSize[0]+halfSize[1]+halfSize[2] == 0` (`0x0048640a`). |
| `pm->bounds` | `pm + 0xdc` | |
| standing player Bounds | const at `0x00c3ea0c` = `0,0,35, 15,15,35` | gives mins `(-15,-15,0)`, maxs `(15,15,70)` |
| `PM_SetBounds` | `0x00412560` | copies that constant; `pm_type == 5` uses 4/8/12 from `0x00c3e060`/`0x00c3ee0c`/`0x00c3ee00` |
| world trace entry | `0x00586f20` | to setup `0x00586a10`, trace `0x00586c90` |
| **`tw->radius`** | `0x00586b7e..0x00586ba6` | `radius = min(size[0], size[1])` |
| `tw->radiusOffset` | `0x00586d3e..0x00586d90` | `radiusOffset[i] = fabs(offset[i]) + radius` - a **rounded box** (anisotropic offset plus sphere), not IW3's `(r, r, r+offsetZ)` vertical capsule |
| `axialCullOnly` | `0x00586990` | same volume test as IW3 |
| FP model | throughout pmove | C1 is an **x87** build (`fld`/`fucomp`); our server is SSE |

Against the retained engine (`src/asmsource/_cm_trace.asm`, `CM_Trace` at line
2201): ours computes `size[i] = (maxs[i]-mins[i])*0.5`,
`radius = min(size[0], size[2])`, `offsetZ = size[2] - radius`,
`radiusOffset = (r, r, r+offsetZ)`.

**The two radius formulas differ** - `min(size0, size2)` versus
`min(size0, size1)` - but **every player hull in either tree has
`size[0] == size[1]`** (stand 15/15/35, crouch 15/15/25, prone 15/15/15,
MPVIEWER 8/8/12, the mantle probes 0.1/0.1/...), so the two always return the
same number today. And because `offsetZ = size[2] - radius` on both sides, the
bottom cap sits at `origin + mins[2]` regardless of hull height: a height
mismatch cannot move the resting foot. **The capsule geometry is identical.**

Two traps worth recording: `0x00c84420` and `0x00c84258` are **doubles** 0.25
and 1.0 (`fmul`/`fsub qword ptr`), which read as `0, 1.625` and `0, 1.875` if
dumped as floats; and `PM_WalkMove` is `0x004108f0`, called only from
`PmoveSingle` `0x00415ff0` at `0x00416937`.

---

## 3. Ranked candidates

Ranked by how well each explains **both** the categorical flat/jagged split and
the ~0.066 u magnitude, and by cost.

---

### #1 - NULL HYPOTHESIS: there is no height bug; `err z` is the horizontal error projected onto rough ground

**Confidence: high. Test this before building anything else.**

**Mechanism.** The client and the server disagree horizontally by 0.15-0.5 u on
every frame, flat or tilted (the parked perpendicular/along residual). Both
bodies are pinned to the surface under their own feet - our `gnfrac` is
0.50000 on 68-78% of logged frames and within 0.0001 of 0.5 on 96-99% of them
(worst observed 0.47370, i.e. 0.013 u), which means our feet are on the traced
surface every frame. On a flat plane, any horizontal offset projects to **zero** height
difference; on a height field it projects to
`h(x_srv,y_srv) - h(x_cli,y_cli)`.

**Why it fits everything.** Exactly zero on flat [M1, M4]. Never zero on tilted
[M1]. Independent of the resting triangle's slope, because the relevant
gradient is the neighbourhood's, not the contact triangle's [M2]. Stable
plateaus that step when `along` steps [M5]. Correlated with `|err_xy|` at
k = 0.045-0.07 [M6]. One-sided if the local terrain is systematically higher
behind the lag direction [M4]. Not a seam event [M3].

**Predicted magnitude.** `|err z| = g_local * |err_xy|`. At the measured
`|err_xy|` of about 0.5 and `|err z|` of about 0.066, `g_local` is about 0.13;
the pooled fit gives 0.045-0.07 over a mixed sample. The stated arithmetic that
"0.45 u along an 0.881 degree slope is 0.0069 u, not 0.066" assumes the
*plane*; jagged terrain is not a plane and only needs a neighbourhood gradient
of about 7 degrees to close the gap.

**Falsification.** Sample our own terrain height field at **both** origins in
one pass and log the difference. If `err z - (h_srv - h_cli)` is about 0 on
tilted, the height symptom is a projection of the horizontal one and this whole
thread folds into the parked problem. If the residual stays at about 0.05, a
real height bug exists and #2-#4 are back on.

**Cheapest test (zero extra playtests - fold into the next capture).** Diff A
in section 5: one extra output from the existing terrain scan, evaluated at the
client's reported `(x,y)` with our `z` as the reference plane. Costs one extra
barycentric test per triangle in a scan that already runs, rate-limited to
25 ms and behind `CODOL_TRACE_ON()`.

**Pre-registered thresholds.**

- *Control (must pass or the session is void):* on flat frames, `projdz` must
  be identically `0.0000` and `tmask` must be 3 on at least 30 frames. A
  non-zero flat `projdz` means the probe's triangle selection is wrong - that
  is the exact failure that voided the last probe run, and it must be reported
  as a broken probe, not as a finding.
- *Primary:* `dP_resid = P(|err z - projdz| > 0.01 | tilted) -
  P(same | flat)`. Baseline for `dP` is **0.662 +/- 0.046** [M8].
  **`dP_resid < 0.15` accepts the null**: close the height thread, hand the
  whole symptom to the horizontal/perp problem.
  **`dP_resid > 0.45` rejects it**: a genuine height bug of the original size
  survives; proceed to #2. 0.15-0.45 is partial; report it as such and proceed
  to #2 with the residual as the new baseline.
- *Evaluability:* `n_flat >= 30`, `n_tilt >= 30`, both with `tmask == 3`.

**Note this is not a "fix".** If it passes, the deliverable is a retraction and
a redirect, which is worth more than any of the fixes below.

---

### #2 - Our decoded terrain does not match what the trace returns (the `tdz` control)

**Confidence: unknown - genuinely unmeasured. Free to run alongside #1.**

**Mechanism.** `cm.verts`/`cm.triIndices` are built by
`codol_collision_terrain.c` from the CoDOL BSP and handed to the retained IW3
clipmap (`codol_collision_native.c:400-407`). If the decode is subtly wrong - a
stride, a border/partition misassignment, the `triEdgeIsWalkable` sizing (see
#3) - the trace answers a surface that is not the one the data describes, and
only non-coplanar terrain can show it.

**Predicted magnitude.** The already-built probe measures
`tdz = ps->origin[2] - h_tri(x,y)`. If our data and the retained mesh trace
agree, `tdz` must be **`0.125 / n_z`, i.e. about +0.1250** everywhere - that is
`SURFACE_CLIP_EPSILON`, applied along the triangle normal by
`CM_TraceCapsuleThroughTriangle` (`hitDist - 0.125`,
`src/futureusecode/cm_mesh.cpp:469`, and the same constant in
`src/asmsource/_cm_mesh.asm`). A *uniform* `+0.1250` on both arms is a pass.
Anything else - 0, scattered, a different constant, or flat differing from
tilted - is a real finding and names the layer.

**Falsification.** Flat arm `tdz` must be `+0.1250 +/- 0.001`. If the flat arm
is not a tight constant, the probe is broken (its triangle-selection path has
*never* been exercised) and the session is void for both #1 and #2.

**Cheapest test.** Already committed and gated; it just has to run once. No
code change beyond Diff A. Same capture as #1.

---

### #3 - `triEdgeIsWalkable` sizing / bit order

**Confidence: medium-low. Static check, zero playtests.**

**Mechanism.** `codol_collision_stream.c:85` derives the walkable lump's size
as `ceil(triCount*3 / 32)` 32-bit words *from the triangle count*, not from a
header field. If CoDOL packs those bits differently (per-triangle byte, a
different edge order, or a separate count), the array is garbage past some
point. `CM_TraceCapsuleThroughTriangle` uses those bits to set
`trace->walkable` on edge and vertex hits, and our ground gate reads it
(`codol_pmove_c1_ground.c:280`). Wrong bits change which contacts are accepted
at triangle seams.

**Why it half-fits.** A sphere resting on a convex ridge sits **below** the
ridge line by `r - sqrt(r*r - d*d)` - one-sided downward, zero on coplanar
ground, and independent of the slope. At r = 15 a lateral contact offset of
1.4 u gives exactly 0.066. That is a very good shape match. **But** it only
engages on edge and vertex contacts, and M5's long stable plateaus are not what
intermittent edge hits look like. Rank it below #1 and #2 for that reason.

**Falsification / cheapest test.** Static, offline, no server: load
mp_storm_spring's collision asset, compute `triCount`, and dump the walkable
bit array. A correct terrain array is heavily biased to ones (most terrain
edges are walkable) with visible structure; a mis-sized or mis-packed one looks
like about 50% ones with no structure, and/or the last partial word has set
bits beyond bit `triCount*3`. Pre-register: **ones-fraction >= 0.8 and no set
bits beyond `triCount*3` is a pass.** A fail is a data bug to fix regardless of
this thread.

---

### #4 - The client is not on the surface we think (read `cg_t` live)

**Confidence: medium. Costs a playtest - spend only if #1 and #2 both come back
clean.**

**Mechanism.** Nobody has ever measured C1's own ground trace result. If the
client resolves a different surface - a static model, a patch, a dynent, or a
terrain partition we do not load - the height difference is arbitrary and
position-dependent, which matches M5 exactly.

**Cheapest test.** A new `tools/` probe modelled on `codol_sway_probe.py` and
`codol_crosshair_probe.py` (`CG_INDEX 0x06C3D2AC`, `CG_TABLE 0x016D3B58`,
`CG_KEY 0x490B400C`; the client must be in a match, `cg_t` is memset between
matches). Read the client's predicted origin and its `pml.groundTrace` normal,
sample at about 10 Hz for 30 s of walking, and compare the normal against the
`gn` column of the same-timestamp server line.

**Pre-registered:** if the client's ground normal matches ours on at least 95%
of paired samples to 1e-3, the surfaces are the same and this candidate is
dead. Below 80%, it is the answer. The *control* is the flat stretch: the
normals must match there, or the probe is reading the wrong field and the
session is void.

**Instruction if it is ever needed:** one 60-second walk across the same jagged
stretch of mp_storm_spring used for the existing captures, with
`codol_debugTrace 1`. It produces the paired-normal match fraction above.

---

### #5 - `radius = min(size[0], size[2])` vs C1's `min(size[0], size[1])`

**Confidence: this is a parity defect, not this bug. Predicted dP contribution:
0.**

**[D]** Established in section 2. Every hull in the tree has
`size[0] == size[1]`, so the two formulas agree today. Fix it for parity - a
future non-square hull (a vehicle, a mover, a scripted trace) would silently
diverge - but do not spend a capture on it and do not expect it to move dP.

**Falsification:** trivially, by inspection. Already done.

---

### Explicitly killed - do not spend on these

| candidate | killed by |
|---|---|
| capsule vs box for the standing ground trace | [D] section 2: identical bounds give identical radius 15, offset (0,0,20), foot at `origin + mins[2]` |
| any rest-height model proportional to ground slope | [M2] R-squared <= 0.055; steepest quintile has about zero error |
| one-frame ground-snap lag | [M2] and the per-line arithmetic: at t33327 `stepdz` = -0.011 (the surface really does drop 0.011 per frame) while `err z` = -0.0732 on the same line - 6.6x short |
| quantisation of the reported origin | the `err z` distribution is continuous; no clustering at any of 1/4, 1/8, 1/16, 1/32 |
| seam-crossing transients | [M3] frames on an unchanged normal are the *worse* arm |
| the +/-0.25 ground-trace reach | `gnfrac` is within 0.0001 of 0.5 on 96-99% of logged frames and never outside [0.474, 0.501] - the trace never approaches either end of its 0.5 u span, so changing the span cannot change the result |
| x87 vs SSE | flat is bit-exact [M1], so the shared path already agrees to the last bit; a rounding-model difference cannot produce 0.066 while producing 0.0000 |

---

## 4. Recommendation

**Do not implement a fix yet.** One capture, with Diff A applied, decides
between "there is no height bug" (#1) and "our terrain data is wrong" (#2), and
those two answers point at completely different work. Both ride on the same
already-gated probe and the same walk; #3 is a static check that can be done in
parallel with no server at all.

If forced to name the most likely outcome: **#1 passes.** The evidence for it
(M1 plus M2 plus M5 plus M6, four independent properties, all from data that
already exists) is stronger than anything I could assemble for a mechanism
inside the mover, and section 2 closes the only trace-shape difference anyone
had identified.

Predicted dP if #1 is right: `dP` on raw `err z` stays at 0.662 (nothing was
fixed), and `dP_resid` falls below 0.10. That is a *diagnosis*, not a fix - the
fix then belongs to the horizontal/perp thread, where a 0.15-0.5 u standing
horizontal error is the whole disease.

---

## 5. Diffs for the owning worker

### Diff A - sample the terrain height at the client's origin too

`src/codol/collision/codol_terrain_probe.h` - add a two-point entry point. The
existing single-point function stays; the new one takes an explicit reference z
so both samples are culled against the *same* plane (the current
`z > origin[2] + 0.25f` cull would otherwise bias the client-side sample).

```c
/* Two points, one scan.  `ref_z` is the reference height both samples are
 * culled against (use the server's origin z for both), so the two heights are
 * comparable.  Returns a bitmask: 1 = a valid, 2 = b valid. */
int CODOL_TerrainHeightUnder2(const float *a_xy, const float *b_xy, float ref_z,
                              float *out_a_z, float *out_b_z,
                              int *out_a_tri, float *out_a_nz);
```

`src/codol/collision/codol_terrain_probe.c` - one extra `tri_height_xy` call
inside the existing loop:

```c
int CODOL_TerrainHeightUnder2(const float *a_xy, const float *b_xy, float ref_z,
                              float *out_a_z, float *out_b_z,
                              int *out_a_tri, float *out_a_nz)
{
    int i, besta = -1, bestb = -1;
    float az = 0.0f, bz = 0.0f, anz = 0.0f;
    if(!a_xy || !b_xy || cm.triCount <= 0 || !cm.triIndices || !cm.verts) return 0;
    for(i = 0; i < cm.triCount; ++i) {
        const uint16_t *idx = cm.triIndices + 3*i;
        float z, nz;
        if(idx[0] >= cm.vertCount || idx[1] >= cm.vertCount || idx[2] >= cm.vertCount)
            continue;
        if(tri_height_xy(cm.verts[idx[0]], cm.verts[idx[1]], cm.verts[idx[2]],
                         a_xy[0], a_xy[1], &z, &nz) && z <= ref_z + 0.25f &&
           (besta < 0 || z > az)) { az = z; anz = nz; besta = i; }
        if(tri_height_xy(cm.verts[idx[0]], cm.verts[idx[1]], cm.verts[idx[2]],
                         b_xy[0], b_xy[1], &z, &nz) && z <= ref_z + 0.25f &&
           (bestb < 0 || z > bz)) { bz = z; bestb = i; }
    }
    if(besta >= 0) { if(out_a_z) *out_a_z = az; if(out_a_tri) *out_a_tri = besta;
                     if(out_a_nz) *out_a_nz = anz; }
    if(bestb >= 0 && out_b_z) *out_b_z = bz;
    return (besta >= 0 ? 1 : 0) | (bestb >= 0 ? 2 : 0);
}
```

`src/codol/player/codol_pmove_trace.c` - the two-point sample belongs in the
**report** function, not in `CODOL_PM_GroundTraceC1`, because that is the only
place both origins are in hand (`serverOrigin` and `predictedOrigin`, around
line 348). Drop the existing in-pmove call site
(`codol_pmove_c1_ground.c:309-317`) and add, just after the `err[]`
computation:

```c
    /* Both feet sampled against the same reference plane, one triangle scan.
     * `projdz` is the height difference the two horizontal positions alone
     * demand.  If err[2] - projdz is ~0 on tilted ground there is no height
     * bug: the vertical symptom is the horizontal error projected onto a
     * non-planar surface (docs/CODOL_UNEVEN_GROUND_FIX_SWEEP.md, #1). */
    projdz = 0.0f; terr_mask = 0;
    if(CODOL_TRACE_ON()) {
        float az = 0.0f, bz = 0.0f;
        terr_mask = CODOL_TerrainHeightUnder2(serverOrigin, predictedOrigin,
                                              serverOrigin[2], &az, &bz,
                                              &terr_tri, &terr_nz);
        terr_trace_z = serverOrigin[2];
        terr_tri_z   = az;
        if(terr_mask == 3) projdz = az - bz;
    }
```

and extend the format string (it already carries the `terr ...` group) with:

```
        "projdz %+.5f resid %+.5f tmask %d "
```

```c
        (double)projdz,
        (double)((terr_mask == 3) ? err[2] - projdz : 0.0f),
        terr_mask,
```

Rate limiting: keep the existing 25 ms gate and the humans-only owner check -
the scan is `cm.triCount` barycentric tests and must not run per client per
frame. `tmask != 3` rows are **not applicable** and must be excluded from the
statistic, never read as zero.

### Diff B - parity only, no expected effect (#5)

`src/asmsource/_cm_trace.asm`, `CM_Trace` (the block just after
`CM_CalcTraceExtents`, around line 2270): the radius currently comes from
`min(size[0], size[2])` (`[ebp-0x118]` vs `[ebp-0x110]`). C1 uses
`min(size[0], size[1])` (`[ebp-0x118]` vs `[ebp-0x114]`) - `0x00586b7e`. The
change is one operand:

```
	movss xmm4, dword [ebp-0x118]
-	movss xmm2, dword [ebp-0x110]
+	movss xmm2, dword [ebp-0x114]
```

but `offsetZ` at `[ebp-0xe8]` is computed as `size[2] - radius` from `xmm2`
further down, so `xmm2` must be reloaded from `[ebp-0x110]` before that
subtraction. Land this only with a deliberate regression pass over brush, mesh
and static-model traces; it is latent today and carries no dP claim.

---

## 6. Tooling added

`tools/codol_c1_disasm.py` - read-only C1.exe disassembly helper (capstone).
`--func ADDR`, `--range A B`, `--xref ADDR`, `--float ADDR N`,
`--find-bytes HEX`. Section-mapped, so `.rdata` and `.data` constants resolve.
