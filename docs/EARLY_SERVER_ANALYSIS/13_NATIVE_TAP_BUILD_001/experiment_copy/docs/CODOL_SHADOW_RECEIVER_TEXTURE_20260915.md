# Shadow receiver texture ownership — 2026-09-15

Status: offline C1 producer/consumer verified; passive capture added. No native
server defect established, no renderer mutation or source gameplay change.

## Distinct downstream input

Earlier correct draw-list transfer and frontend lookup matrices do not establish
that the receiver consumes the expected depth texture. The real local source
uses a separately prepared texture pointer and sampling parameter vector:

- A8265F..A8266F copies ten words from scene globals FAA994 into view+180.
- Actual world callback setup ACF219 passes view+180 into AB4750; AB4787 passes
  it as argument2 of AB02F0 along with the local command source and view parameters.
- AB0353 reads argument2+14 (view+194), then AB035D writes source+1388.
- AB0356..AB0363 supplies the following four floats (view+198) to AA7120 as
  code constant54. This happens on the same correctly scoped local source as
  mode1 camera-origin setup, rather than global12A6B30 after it has become2D.

## Concrete texture producer

A83B53 initializes target index10. A83BEA selects11 in the alternate renderer
branch. A83C4A computes index*5; A83C84 reads render-target image at
12D0600+index*20. A83C8F stores it in FAA9A8, which is scene+14 and therefore the
exact source of view+194. A83C7E retains the selected index at view+FAC.

The target-name table begins CBD140 with R_RENDERTARGET_SAVED_SCREEN. Its
indices10/11 are R_RENDERTARGET_SHADOWMAP_LARGE/SMALL (CBD168/CBD16C), established
from the actual C1 strings rather than OpenBLOPS enum ordering. The following
FAA9AC..FAA9B8 floats are computed from renderer dimensions/tiling at A83C95+.
Their full interpretation remains separate from this pointer-ownership proof.

This texture selection is native client renderer configuration. No direct server
entity field or script configstring was identified as its selector in this pass.
Do not force target10/11 or republish a default to claim a shadow fix.

## Passive probe

`tools/codol_shadow_pose_probe.py` now validates additional exact code signatures
and records view0's image, selected target, expected render-target image and
sampling floats, with byte stability and existing frontend/view coherence guards.
It reads the target table only for the verified10/11 indices. Pointer equality
would establish correct preparation, not GPU depth contents or actual draw use.

Initial revalidation found C1 PID90404 command511475 in mp_bloc_sh and correctly
skipped Killhouse scene data. After adding the receiver capture, the next attempt
found command0 and skipped all scene reads. Saved result:
obj/killhouse-shadow-receiver-texture-90404.json. No stale world input, global2D
matrix, or guessed stack address was interpreted.

Next active Killhouse capture can discriminate wrong/stale selected depth image
or malformed view sampling vector before pursuing GPU sampling. No automated
tests, UI input, builds, restarts, hooks, injections or process writes performed.

## Target dimensions and constant54 provenance

The next offline pass resolved the four sampling components. A83C5F retains
tile count T in view+FB0; A83C72 retains full width W in view+FA8, after multiplying
the working height by T. A83C78..A83CE8 computes constant54 exactly as
`(.25/W, .5/(W*T), .5/W, -.25/(W*T))`. The x87 constants at C84420, C84248 and
B60EB8 are .25, .5 and -.25. This vector does not use the scaled viewport extent
CF3EFC, camera coordinates, or a final vision field.

C1 registrations A7C898..A7C9B7 establish these dimension controls:

| Numeric name | Pointer global | Default | Range | Role |
| --- | --- | --- | --- | --- |
| 2642 | CF41F4 | 1024 | 256..2048 | Large width |
| 2643 | CF40E8 | 512 | 128..1024 | Small width |
| 2644 | CF4258 | 2 | 2..2 | Large tile count |
| 2645 | CF41D0 | 4 | 1..4 | Small tile count |

Registration also rounds these integers to powers of two. A83B39/A83B48 select
2642/2644 with target10; A83BD3..A83BEA select2643/2645 with target11. Numeric1619
and the1623 force-unit boolean affect viewport scaling separately. Numeric1617
feeds CF3F04 through A83CEE..A83CFC, also separately from constant54.

The alternate mode CF3F00 is renderer-owned: A861A7 tests numeric1624, then
A861BC calls A803A0 on the current frontend before A861CE enables the mode.
A83B5A..A83B7B may clear it for incompatible view conditions. Additional
shadow subviews use their own target selection at ABDBD0..ABDC9D, and write
their image to subview+44, target index to+1B8, and tile viewport to+50..5C.
Those subviews must not be confused with the receiver's view+194 texture.

Current native `CODOL_RefreshServerDvars` looks up exact inherited names and
only republishes registered SYSTEMINFO variables. Source/config searches found
no explicit numeric2642..2645,1619,1623 or1624 setters in current native startup
or live main scripts. This excludes an identified direct writer, not arbitrary
future GSC calls. Existing evidence already identifies configure_mp.csv as a
legitimate client1623 source and cameraPosTable.csv as a1617 source. The held
friendly-name lighting alias stage remains separate; IW4 `_load` defaults are
not evidence that C1 needs different numeric target dimensions.

The passive probe now reads guarded view dimensions and compares constant54
against the exact formula. Revalidated C1 PID90404 was active in
`maps/mp/mp_bog_sh.d3dbsp`, command196069, so it correctly skipped Killhouse
scene reads. Result: obj/killhouse-shadow-receiver-dimensions-90404.json.

No malformed receiver dimensions or server publication defect is established.
The next useful Killhouse capture can now distinguish pointer/dimension/vector
disagreement without changing render settings. If those agree, actual depth
contents and the consuming material's sampler remain unverified; agreement is
not proof that the visual artifact is absent.

## Depth comparison path: distinct from texture dimensions

Registration A7C70D/A7C745 proves numeric1611 default1.5, range0..8,
flags0, and numeric1612 default4, range0..32, flags100. Their globals are
CF4070/CF4318. Numeric1617 registers default.25, minimum.015625, maximum32
at A7C759..A7C79A with flags44. The maximum comes from BEECE8=32; it must
not be described as FLT_MAX.

AB4540's packed-state branch30 uses1611 as slope scale and1612 multiplied by
1/65536 as fixed depth bias. AB45D9 submits render state175 when capability
CF3F45 permits it; otherwise AB45E3 doubles the fixed bias. AB45F6 submits
render state195. Other packed-state modes select different globals CF40BC /
CF4084, so their behavior cannot be attributed to1611/1612 indiscriminately.

There is also a separately prepared shader bias, code constant22:

- AD8488..AD84C3 supplies `(1612*.25, 1611, 0, 0)` to AA7090 for its shadow
  subview path.
- AD9E4E..AD9E91 supplies `(1612*.03*partition[+78], 1611*.65, 0, 0)` for
  the sun partition path. Partition address is
  `view[F94]+41CB0+partitionIndex*160`; AD9EB6 subsequently selects the
  associated view+5FC draw descriptor. Constants C03AE0/C84930 contain the
  floating-point .03/.65 factors.

Consequently matching dvars alone does not prove correct final depth comparison:
the sun path additionally depends on a per-partition value at+78. A candidate
producer AB9878 stores+78 while building a projection and duplicates it into
+14C; this pass has not completed caller/alias ownership to prove that this is
the exact AD9E path's producer. Do not label the field a simple depth range or
reciprocal before completing that link.

Existing recorded server-bank evidence contains no numeric1611/1612/1617;
the native publisher uses exact registered names. CameraPosTable is the proven
client producer for those names, and the prior parent-controlled default bias
comparison was accepted but did not remove the broad pattern. Vision fields
are not read directly by either shader-constant setup above. This does not
exclude upstream camera/projection dependence or establish an intended official
MP reset policy.

Next discriminator is the actual sun partition+78 alongside its prepared
constant22, with current view/frontend ownership, rather than another arbitrary
bias toggle. No native/gameplay changes or renderer mutations made.

## Resolved partition ownership: correction to the candidate producer

The next bounded trace disproved the apparent +78 alias and resolved the actual
input. A84033 pushes frontend+41C50 as argument3 of ABCEB0. ABCEC6 retains that
argument, then ABCEF7 passes it in ECX into ABC8D0. ABC90A saves it at stack+1C.
After the call-stack adjustments ABCB99 reloads that same pointer; ABCBA2 adds
70. ABCBAB passes the resulting projection address in EAX to AB98B0, which
calls AB9790 at AB99C2 without changing EAX. ABCBB8 increments each projection
by160. Therefore projection0 is frontend+41CC0, not41CB0.

AD9E47's containing-record pointer is frontend+41CB0. Its depth multiplier at
+78 is consequently frontend+41D28: exactly projection+68, produced by AB985B.
AB9878's projection+78 is frontend+41D38 and is a different element. It must
not be used for the shader multiplier. AB9843..AB985B forms a reciprocal from
the depth bounds plus its existing adjustment, then writes projection matrix
element10 (+68). AB9878 instead writes element14 (translation); the subsequent
AB9880 copy to+14C does not feed AD9E's bias multiplier.

The probe now verifies these instruction signatures and requires view+F94 to
equal the current guarded frontend before reading either projection. It records
the full projection matrix, finite/stability checks, and the derived constant22
using element10. This is a CPU-input computation, not a claim to have read the
GPU constant upload. A new passive attempt revalidated C1 PID90404 but found
commandTime0, so all scene reads were skipped. Saved result:
obj/killhouse-shadow-depth-bias-90404.json.

Ownership is now established; no runtime malformed depth scale is observed yet.
The next naturally active Killhouse capture can discriminate nonfinite/stale
projection depth scale and inconsistent view ownership without a setting change.

## Actual active Killhouse capture

Revalidated C1 PID90404 was naturally active in Killhouse at command62389..62401.
`obj/killhouse-shadow-depth-bias-90404-resume.json` records the corrected probe:

- Current frontend CF4400, view F4F840, and view+F94 ownership all agree and
  remain stable across reads.
- Receiver target10 is SHADOWMAP_LARGE; image1243E48 exactly matches the target
  table. Stored target dimensions are1024x2048, matching width1024 and two tiles.
- Constant54 is (.000244140625,.000244140625,.00048828125,-.0001220703125),
  exactly the derived formula, with zero error. Image/vector/dimensions stable.
- Projection addresses D360C0/D36220 have finite matrices and identical depth
  scale2.4567314540036023e-5. Their XY scales are respectively .0078125 and
  .001953125. Derived constant22 for both is approximately
  (9.2127429525e-8,1.3,0,0); both matrix reads remained stable.
- Prepared destination draw lists contained50/109 entries. Separate global
  construction counters were already0 and must not be interpreted as missing
  draw submissions. The unrelated global command source was2D and owned the
  other frontend, exactly why the corrected probe uses actual view ownership.

This sample excludes a wrong prepared receiver image, dimension/vector mismatch,
nonfinite projection depth scale, or wrong view/frontend ownership. No GPU depth
texels or exact artifact pixels were captured, so it does not eliminate shader
sampling/material/depth-content causes or certify visual correctness. No native
change is justified by these matching CPU inputs. No game input or setting
mutation was performed.
