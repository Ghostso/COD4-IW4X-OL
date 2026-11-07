# CoDOL trigger model geometry

The former startup failure occurred because `G_ParseEntityField` recognized
`*N` but sent `?N` through `G_SetModel` and XModel lookup. CoDOL's
MapEnts data has separate trigger models, hulls and slabs. A trigger model is
a union of hulls; a hull has axial bounds and additional slab constraints.
It cannot be replaced with a box or mapped directly onto an unrelated `*N`.

The source layout already decoded by `CODOL_ReadMapEntities` agrees with
[OpenAssetTools' IW4 definitions](https://git.alterware.dev/zone/OpenAssetTools/src/commit/3995596e6c201dbcfa6893d9b6c4c68db56235c3/src/Common/Game/IW4/IW4_Assets.h?display=source):
model contents/count/first hull; hull midpoint/half-size/contents/count/first
slab; slab direction/midpoint/half-size. That is supporting IW4 layout evidence,
not a claim that all CoDOL trigger runtime semantics have been recovered.

`CODOL_ReadTriggerModel` now builds owned convex-hull geometry for one trigger.
Each slab `abs(dot(direction, p)-midpoint) <= halfSize` becomes two outward
planes; plane normalization rescales both normal and distance. Each hull also
retains its six axial bounding planes and contents. Model bounds cover all
its hulls. Validation checks model/hull/slab ranges, finite values, nonnegative
extents, nonzero slab axes, allocation limits and output atomicity.

The focused ASan/UBSan fixture verifies nonzero first indices, a two-hull
union, an oblique cut that excludes a bounding-box corner, boundary inclusion,
normalization, independent ownership, malformed input and atomic failure.
Linux `all test-codol` passes (`/tmp/sh1x-trigger-models-linux.log`).
`codol_checkcollision` now audits every trigger and reports trigger zero's
bounds. Native installation and spawning are now connected as described below.

Remaining verification includes trigger touch callbacks, swept/capsule traces,
rotated shapes, and correct client-facing model-index representation. The
playable-match goal is still incomplete.

Windows build and shipped Bog diagnostic pass: **23 trigger models decoded,
0 failed**. Trigger `?0` has one hull, contents 0x28000001, and bounds
(-75.3301,-81.8196,-8) to (75.7306,82.2197,72). These are the stored trigger
coordinates, not a replacement entity origin. Runtime contact/trace integration
is still absent, so map startup continues to fail at `?0` XModel lookup.
The diagnostic ran afterward, then exited cleanly (PID 58988).
Log: `%TEMP%/sh1x-trigger-geometry-probe/main/qconsole.log`.

## Native installation and spawn path

`CODOL_AppendNativeTriggers` adds native brushes, planes, leaf-brush nodes and
inline collision models before the clipmap is published. Old model indices
remain unchanged. Existing plane/side/index pointers are rebased into the
expanded allocations. The reserved temporary box brush moves to the end and
its original leaf-brush index is updated; its node identity remains stable.
Map limits preserve 16-bit brush indices and the reserved box model handle.
Failed construction leaves the previously installed map untouched.

`CODOL_SetTriggerEntityModel` strictly parses `?N`, resolves the installed
trigger handle and writes the native entity model index. The normal trigger
spawn routines then call `SV_SetBrushModel`, which reads the appended model's
bounds/contents. Native point/contact/trace code can address the geometry via
the regular inline-model handle path; no dummy XModel is created.

The 32-bit ASan/UBSan fixture executes native `CM_PointContents` and verifies
inclusion inside an obliquely cut hull and exclusion of a box corner. It also
checks existing BSP plane references, box-hull index preservation and atomic
failure. This exposed a retained `CM_PointContentsLeafBrushNode_r` loop that
read p[3] before testing u<3; the bound check now precedes coordinate access.

Windows build passes. Shipped Bog now clears `?0` and next fails converting
`com_cellphone_on` with invalid/unsupported native dependencies. Probe PID
68240 exited after normal shutdown. Log:
`%TEMP%/sh1x-trigger-native-vm-probe/main/qconsole.log`.
No vehicle-node VM assertion success marker, live trigger callback, swept
trigger interaction or client match is yet verified. Client/lobby untouched.
Full Linux `make -B -j6 all test-codol` passes for native trigger integration
(`/tmp/sh1x-trigger-native-linux.log`).
