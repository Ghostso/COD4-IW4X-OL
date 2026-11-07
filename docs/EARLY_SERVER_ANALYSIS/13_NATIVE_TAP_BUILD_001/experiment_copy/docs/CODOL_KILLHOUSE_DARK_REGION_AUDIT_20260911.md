# Killhouse camera-linked dark-region audit (2026-09-11)

Status: unresolved. Read-only audit; no renderer/native gameplay change justified.

## Observation limits

User reports a region that follows the camera and enlarges near a wall. Parent's UI comparison found broad darkening before class selection; AO High -> Off retained the broad region, while Shadows On -> Off removed sharp roof-beam shadows but retained the broad region. The precise user-reported artifact was not reliably isolated in those comparisons. These observations must not be used to claim a cause ruled out. Greater distance in the loading image also changes apparent shadow detail.

## Established native evidence

- A passive PID85712 capture contained 315 linked, client-visible brush entities. Each model index and origin matched the shipped mp_killhouse_sh MapEnts; no index/origin mismatch was found.
- Synthetic trigger brushes exist separately and have no-client visibility. Four hidden scriptmodels also have client masks from hide(); their native flag0x20 alone does not prove an unwanted caster.
- No dynamic primary-light entities or live player/corpse entities existed in that capture. The static common world reported30 lights. This describes the capture, not every screenshot.
- Native player eFlags/otherFlags are copied directly into their C1 fields. No missing shadow-specific bit has been established.
- T5 r_enablePlayerShadow / renderflag0x400003 were not established in C1 and must not be copied as assumed constants.

## C1-specific passive discriminator

C1's local viewmodel builder at47c550 assembles custom jacket/glove roots and weapon pieces. At47ca79..47caa3 it builds DObjs with handles0x800/0x801.

The two-hand DObj table is decoded as:

    index = u32(0x6c3d2bc)
    table = u32(0x16d3b58 + index*4) ^ 0x90834eee
    dobj[hand] = u32(table + hand*20)

The renderer-side model traversal at4830d5..48310b reads modelCount from DObj+9 and the XModel pointer array from DObj+0xc0. XModel+0 is its name pointer. These observations allow a passive capture to identify which local models actually exist at the exact artifact frame. Presence alone does not prove drawing: menu/transition DObjs can be stale. Correlate with gameplay commandTime, camera pose, selected weapon and screenshot; do not infer a viewmodel cause from stale records.

No tests, input simulation, settings changes, debugger attachment, or process restarts were performed by this worker. Parent handled the earlier reversible visual comparisons.

## Active class4 capture

`obj/killhouse-shadow-live-class4.json` records a passive C1 PID74192 capture after the parent's rejoin. commandTime692368 and pm_type0 identify predicted gameplay state. Player origin was (4172,926,4.125), camera origin (4172,926,64.125): a60-unit eye offset. eFlags was0, otherFlags0x1000, weapon114, arms145 and hands300.

Hand0's DObj contained12 models: custom jacket/gloves, the M4A1tech weapon body and nine attachment pieces. This includes `hbs_normal_ss_13_vmgun` and `mag_dualar15_m4ncm_blk_vmgun`; their geometry is present in the composed local object. Hand1's DObj was null. This does not establish that the heartbeat display is drawn or that any model casts the reported dark region. Renderer submission flags remain undecoded, and the exact user artifact was not isolated at this capture.

`tools/codol_shadow_probe.py` performs only ReadProcessMemory reads and validates a C1 code signature before resolving its encoded tables. It reports predicted gameplay activity, not a verified received-snapshot pointer. No native shadow change is justified by this capture.

## 2026-09-14 spectator evidence and proposed isolation

User confirms the camera-dependent patch occurs in spectator mode before spawning. A spawned local character is not required. Keep the malformed Shadow Company lobby avatar investigation separate. An earlier screenshot is suggestive of a regression but is not a same-camera/build comparison.

Research: Microsoft, Common Techniques to Improve Shadow Depth Maps and Cascaded Shadow Maps:
https://learn.microsoft.com/en-us/windows/win32/dxtecharts/common-techniques-to-improve-shadow-depth-maps
https://learn.microsoft.com/en-us/windows/win32/dxtecharts/cascaded-shadow-maps
Camera-relative shadow coverage and depth bias can create camera-dependent artifacts. This is a mechanism hypothesis, not evidence that C1 uses a particular implementation or that its renderer is defective.

Source review this turn: native map configstring refresh covers fog and ambient; vision producers are separate. No explicit shadow/sun renderer override was found in the searched native CoDOL code and script overlay. This does not exclude shipped scripts, saved client settings, or other code. The previous brush audit checked model indices and positions, not complete C1 rendering flags or received scene submissions. C1 441532 interpolates entity scale, and 441573..441587 treats brush solids specially; neither establishes a bad caster.

Proposed fix path, not an implemented fix:
1. Capture the same spectator camera in earlier and current server builds with identical client settings/map assets. Record received entity states and fog/vision configstrings, rather than comparing photographs at different distances.
2. If server versions differ, isolate world brush/script-model submissions in an offline diagnostic branch. Compare full C1 flags, angles, scale, solid/model selection and visibility, including duplicate world geometry. Restore the erroneous producer/serializer to the verified C1 contract; do not suppress all shadows as the fix.
3. If the server comparison is identical, isolate shadow projection from depth-based postprocessing using the exact camera/patch. Previous UI toggles were not conclusive. Do not change bias values speculatively or add zones.

No source fix, builds, tests, process writes, or restarts this turn. Cause remains unconfirmed.

### 2026-09-14 correction
User rechecked the earlier screenshot and sees the same artifact. Withdraw its use as evidence of a server-version regression. Spectator reproduction remains valid. Earlier/current build comparison is no longer the leading discriminator without a demonstrably good baseline.

## C1 scene submission audit (2026-09-14)

Offline C1 findings, without runtime modification:

- Entity dispatch at `0x443c70` routes types6 and13 to `0x43fc80`. Its `0x43fcb4` gate skips the entire submission when entityState.eFlags bit0x10 is set (centity+0xec). General model submission at `0x43ea44` uses the same gate. These are C1 bits, not imported T5 constants.
- A mover with no DObj and solid0xffffff follows `0x43feb9..0x43ff0b`. It resolves the inline model from centity+0x17c (entityState+0x98), decodes its absolute origin, takes centity+0x24 angles and entity number, then calls `0xa80510`. That submission function stores the model pointer, origin, angle quaternion and entity number in scene-brush records at `0xfe1304`, stride0x28, with count at `0xfe12fc`. Capacity is512. No camera-position, entity-scale or separate per-brush shadow-flag argument is passed on this branch.
- Current `CODOL_OverlayEngineBrushEntity` publishes inline model+0x98 and solid+0xa8. The earlier315-brush capture verified these selectors and origins, but did not verify received angle quaternions, complete visibility, or the resulting scene-brush records. Those remain a concrete passive comparison surface; the absence of a camera argument at submission does not exclude camera-dependent behavior later in the renderer.
- General model submission `0x43ea93` passes render flags0 to `0xa83480`. Ordinary mover DObjs do likewise; a particular attached-weapon branch can set flags4 at `0x43fe64`. There is no demonstrated missing server-provided shadow flag in these calls.
- Model lighting-position helper `0x43e480` checks entityState.eFlags0x1000. When unset, it clears a cached vector and recomputes it using `0x43e370`; when set it retains a nonzero cached vector. The computation uses the first XModel's+0x140 vector, entity angles and decoded absolute origin. It does not read the camera. Native generic/mover eFlags preservation remains an independent compatibility audit item, but no wrongly published lighting-cache or visibility bit has been established for the reported patch. The earlier four hidden models were already excluded through client masks.

No source correction is justified from this evidence. The server-input hypothesis is narrower now: compare actual received mover visibility, angles and model selection against the resulting scene records before assigning a renderer cause or changing flags.

### Passive scene-brush tool

Added `tools/codol_scene_brush_probe.py`. It opens only PROCESS_VM_READ, validates three exact C1 code signatures and bounds the brush count to512. It captures scene brush entity/model/origin/quaternion, resolves the inline model index from render-world+0xd4 (C1 `0xa804f0`, model stride60), and correlates centity nextState identity, flags, solid/model selector and interpolated transform. It compares origins/model indices and reports whether the scene bytes remained unchanged across the read interval. Quaternions are captured but not independently recomputed; asynchronous reads cannot establish a single atomic frame.

Process discovery found C1 PID90944 at image base0x400000. The passive invocation passed its build guards but found commandTime0, so it deliberately skipped scene capture. `obj/killhouse-scene-brush-90944.json` records this inactive result. The active capture branch has been source-reviewed against the above C1 consumers, but has not yet captured an in-match scene. No received-state mismatch was observed because no active scene was available.

### Subsequent active capture

PID discovery again found C1 PID90944. `obj/killhouse-scene-brush-90944-active.json` captured commandTime17200 and camera (3492,-238,232), with253 submitted scene brushes. Every record matched its centity's model selector and interpolated origin exactly; maximum origin difference was0. Entity IDs matched nextState and none were duplicated. All records were type6, flags0, solid0xffffff, angles(0,0,0), with the corresponding identity quaternion(0,0,0,1). The scene bytes and commandTime remained unchanged across the read interval.

This active sample found no received-state-to-brush-submission mismatch. It does not establish that the reported patch was visible at this camera/time, compare visibility against an official server, or exclude later camera-dependent renderer processing. The previous inactive result remains a separate earlier capture.

## Distinct depth-postprocess input path

C1 contains SSAO materials (`ssao_calc_fast`, `ssao_calc_slow`, downsample/full-resolution apply variants). Its `r_ssao` registration at `0xab5cee` stores the dvar pointer at `0x14fd454`. During per-view preparation, call `0xa8273e` invokes `0xa81a40`, which copies local dvar values into the view structure:

- view+0xfbc: enabled when `r_ssao` is nonzero and the float dvar at pointer0x14fd448 is greater than zero;
- view+0xfbd: whether `r_ssao` equals1;
- view+0xfc4/+0xfc8/+0xfcc: current floats from pointers0x14fd448/0x14fd458/0x14fd444;
- view+0xfbe and+0xfc0: additional local dvar values from0x14fd45c/0x14fd44c.

The adjacent float registrations use numeric names2454/2455/2456; their semantic meanings were not established and should not be guessed from order. This specific preparation path reads local dvars, not serialized entity-state fields. Searches of `src/codol` and `scripts/codol` found no explicit producers for `r_ssao`, those numeric names, shadowmap or sun-shadow bias. This search does not exclude generic client-dvar commands, shipped scripts or saved client settings.

No camera-dependent sun projection defect or incorrect server-driven postprocess input has been established. The SSAO path is a distinct renderer lead, not a diagnosis; earlier UI comparisons did not reliably isolate the exact patch. No settings or runtime state were changed.
