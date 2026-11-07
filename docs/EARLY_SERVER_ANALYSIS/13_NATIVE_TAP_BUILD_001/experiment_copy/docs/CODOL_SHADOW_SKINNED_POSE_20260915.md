# Killhouse skinned shadow pose audit

**Evidence correction:** the first version checked frontend identity stability
without requiring a nonnull pointer. That was insufficient: null can remain
stable outside rendering. The earlier pose samples below did not retain the
pointer value and therefore cannot establish a current rendered frame. Their
normal selected bone values are archived observations, not proof excluding a
malformed live caster. The corrected probe requires one of the two verified C1
frontend allocations and readable allocation endpoints before scene capture.

Status: offline consumer traced, passive capture tool written. No gameplay fix,
build, automated test, settings change, or process mutation. Current capture is
inactive and provides no evidence about the reported visible artifact.

## Why this is a separate path

Prior captures in CODOL_SHADOW_FINAL_VISION_TRACE_20260914.md established authored
sun-blind zero, disabled actual lightgrid tweaks, finite derived shadow sampling,
ordinary brush transforms, and no oversized single-XModel caster in that frame.
Those findings do not validate skinned vertices. A DObj can retain ordinary model
radius and entity scale while its bone transforms deform submitted geometry.

## Exact C1 consumers

- A81730 submits scene DObj surfaces from scene+44, with DObj at scene+6C and
  per-model LOD bytes beginning scene+48. It rejects absent prepared surfaces;
  material technique availability additionally gates actual submission.
- AA6980 prepares/caches scene entity bounds. AA69E8 calls 637940, whose verified
  implementation returns DObj+98: the current rotation/translation array.
- 637C40 returns byte DObj+A, the bone count. This is separate from model count
  byte+9 returned by 637950; model pointers are reached through DObj+C0.
- AA6AC9 loads the matrix pointer; AA6ACD advances four bytes. AA6AD5 tests the
  relevant part bit before consuming each bone. AA6F3C advances 32 bytes per bone.
- AA6AE2 reads matrix+1C (the quaternion transform weight). Quaternion components
  occupy +0..+C. AA6C2D/34/3B read translations +10/+14/+18, accounting for the
  earlier four-byte pointer advance. AA6C4C/5A/68 add render-origin globals
  FAA99C/FAA9A0/FAA9A4. Therefore raw skeleton translation is not automatically a
  world coordinate and should not be compared directly with entity origin.
- AA6900 requests pose production through 45E5B0 under DObj lock/unlock
  6382B0/6382E0. No external calls to these functions were made.

The named IW3 reference `_r_dobj_skin.asm` helps identify the facility; every C1
offset above comes from C1 instructions, not equivalence with IW3/T5 layouts.

## Guarded passive capture

`tools/codol_shadow_pose_probe.py` validates the full executable path and exact
C1 code signatures before decoding client pointers. It requires nonzero predicted
command time and exact renderer world `maps/mp/mp_killhouse_sh.d3dbsp`. It reads
scene DObjs only then, and captures skeletons only for records whose sun partition
visibility is 1. It records matrices, model names, finite components, translation
bounds, per-record/matrix/pointer stability, and frontend/count stability.

Limitations: reads are not an atomic frame. The selected part-bit mask is not yet
decoded by the probe, so uninitialized unused bones cannot be labeled corrupted.
Finite transforms do not establish correct GPU shadow samples. Positive command
time does not identify whether the reported artifact is visible at capture time.

`obj/killhouse-shadow-pose-100756.json`: executable path verified; predicted
commandTime=0. Scene capture intentionally skipped. No malformed pose, rendering
producer mismatch, or evidence-backed native correction established yet.

Next concrete check: capture active Killhouse sun-eligible DObj poses with stable
records, then correlate any abnormal bone spread with the actual selected part
bits and prepared surface submission. Do not repeat sunblind/lightgrid resets or
introduce arbitrary shadow dvars based on this inactive sample.

## Follow-up: reconstruct actual bounds bone selection

Revalidated the same C1 process and path again. Follow-up artifact
`obj/killhouse-shadow-pose-followup-100756.json` remains commandTime=0; no scene
claim. Offline tracing now resolves the selection mask rather than treating all
bones as consumed.

AA6A24 calls 637960 with the DObj, a 32-byte output bitset and scene+48 LOD bytes.
637973/977 enumerate model count +9 and model pointer array +C0. Each model's bone
count is byte+4. Its selected signed LOD indexes a 0x38-byte record at model+48;
negative LOD contributes nothing. Record+4 is surface count, record+10..+2C is the
eight-word part mask. 637A81..637BAC shifts that mask by cumulative prior model
bone counts and ORs into the DObj mask; 637BB1 advances the cumulative count even
when that model's LOD is negative. The mask uses MSB-first indexing, consistent
with AA6ABC/AA6AD5. This is selection by actual render LOD, hence camera-dependent.

The probe now captures selected LODs, immutable asset mask bytes with stability
checks, reconstructed selected bone indices, and separately reports nonfinite
selected bones. It also captures the render-origin vector added by AA6C4C/5A/68.
This eliminates the previous unused-bone ambiguity for the bounds consumer.
Per-surface skin/hide filtering may exclude additional bones; mask membership
does not prove that every vertex reaches a GPU depth pass.

Concrete remaining candidate: camera-dependent LOD change selecting malformed
composed-model bone data. This is an investigation target, not an observed defect.
No current frame establishes it and no native field fix is justified yet. The
tool rejects out-of-range embedded LOD records instead of following arbitrary
memory. No C1 function is invoked and no renderer state is changed.

## Active Killhouse: selected poses are ordinary

Parent reconnected the client; worker supplied no input. Revalidated PID100756,
image guards and exact Killhouse world. Two passive captures now provide actual
scene evidence:

| Capture | Command time | Sun-eligible skinned entity | Selected bones | Selected translation span |
| --- | ---: | ---: | ---: | --- |
| obj/killhouse-shadow-pose-active-100756.json | 815743 | 3, far partition | 77 / 157 | 26.45 x 22.27 x 63.72 |
| obj/killhouse-shadow-pose-active-second-100756.json | 843652 | 1, both partitions | 113 | 33.68 x 20.42 x 41.56 |

Both captures have three world DObjs. Frontend, count, scene records, captured
matrix bytes and matrix pointers remained stable within each read. Selected
bones contain no nonfinite values. First capture entity3 has nonzero prepared
surface pointer D36B00, packed key08200180, renderer flags104; exclusion mask41
does not reject it. Its eight models are pants, boots, jacket, hands, vest, head,
beret and vest accessory, with model bone counts summing to157. First model LOD0,
remaining models LOD2; captured LOD bytes are stable. Selected quaternion squared
norms range .999563.. .999975 and transform weights 2.00005..2.00087, consistent
with ordinary normalized transforms.

The first DObj's *unselected* bones span roughly1500 units in one axis, while its
selected bounds remain human-sized. Reporting the unselected span as a giant
caster would be wrong: the exact C1 bounds mask excludes those bones. Captured
render-origin addition is (3492,-238,284); selected translations are relative to
that renderer origin, not malformed world coordinates.

These archived values contain no giant or malformed selected skinned pose, but
the missing nonnull-frontend guard prevents excluding a current malformed caster
from them. They do not prove GPU correctness, identify the visible artifact's
frame, or identify a native server field to change.
No gameplay code or settings changed; no automated tests/builds performed.
