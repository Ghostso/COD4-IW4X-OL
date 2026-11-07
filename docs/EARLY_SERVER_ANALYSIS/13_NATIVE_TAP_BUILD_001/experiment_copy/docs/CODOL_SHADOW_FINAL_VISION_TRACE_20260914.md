# Final C1 vision inputs

Status: distinct offline consumer trace completed; passive current-client capture is inactive. No source gameplay changes, tests, UI input or process interruption.

C1 blend0x479e80 handles0x70-byte vision records. At fraction0/1 it copies a complete endpoint; otherwise0x479edc iterates21 entries in metadata0xcd67dc with stride12. Scalars call0x479ca0, vectors0x479d90, and boolean endpoints are selected separately. Offset0x6c is blended after the21 named fields. This establishes actual types and native client interpolation rather than assigning T5 offsets to C1.

Final selection0x47a630..0x47a678 chooses a vision channel, checks its20-byte state at cg+0x173eb0, and selects current record cg+0x173c08+channel*0x70. Channel4 can blend against the base channel using cg+0xc8af0. When no channel state exists, it explicitly disables output bytes cg+0xb03ec/cg+0xb0428 and sets character-light scales to1.

The selected named fields reach final scene input through0x47a6e7..0x47a7c9:

| Source name/offset | Final cg offset |
|---|---|
|520 /0x24|0xb03ec (byte)|
|521 /0x28|0xb03f0|
|522 /0x2c|0xb03f4|
|523 /0x30|0xb03f8|
|524 /0x34|0xb03fc|
|525 /0x38|0xb0400 (byte)|
|528 /0x54 vector|0xb0404|
|527 /0x48 vector|0xb0410|
|526 /0x3c vector|0xb041c|
|511 /0|0xb0428 (byte)|
|512 /4|0xb042c|
|513 /8|0xb0430|
|514 /0xc|0xb0434, subsequently multiplied by record+0x6c|
|516 /0x14|0xb0438|

Fields515/517/518/519 are recognized and blended by the parser, but this inspected final transfer does not copy them. That is observed C1 behavior, not a missing native server copy. The engine can still have other consumers outside this routine.

Renderer preparation0xa81eb0 normally copies60 bytes from scene-parameters+0x2c into view+0x218. An explicit local tweak selector0xcf4034 instead chooses individual local dvars. After either route,0xa81f98..0xa81fea applies local modifiers to scalar outputs: the value at view+0x224 undergoes a nonlinear blend/product, view+0x220 is multiplied, and view+0x21c receives an addition. Disable handling installs neutral output values before0xa81bd0 derives rendering constants. These are additional local rendering inputs beyond the server-selected asset; this audit does not assign unverified semantic names to numeric dvars or claim any modifier is wrong.

Renderer0xa82030 separately copies scene-parameters+0x68..0x78 into view+0x254..0x264 unless its local tweak selector0xcf4080 is enabled. When view+0x260 is nonzero, it derives a coefficient group at view+0xcf0..0xd0c. This path has no direct entity index, camera position or server configstring read in the inspected function. Its exact shader use remains unestablished.

The current C1 PID102052 passed the exact final-copy instruction guard at0x47a6e7, but commandTime was0. `obj/killhouse-final-vision-102052.json` records the inactive result; no stale channel or scene values were interpreted. A subsequent active capture can now compare the current channel record and final fields directly against the shipped Killhouse vision using established offsets. No malformed server input or evidence-backed shadow fix was found in this trace.

## Active final-blend evidence recovered

The independent Betty investigation captured the final vision and all five current channel records during active C1 PID102092 gameplay, commandTime96574..96585 (`obj/betty-live-99340-102092.json`). Decoding those bytes with the established transfer map shows every authored output equals the shipped Killhouse asset to float32 precision: fields520..525=1,0.118649,1.10681,0.0857679,0.2,0; vectors528/527/526 match all nine authored components in their correct destination order;511=1,512=513=514scaled=516=0; character scales=1/1. The base current channel likewise contains these authored values. This rules out a malformed server-selected vision or lingering blend for that captured interval, without claiming the exact dark patch was visually isolated then.

The renderer's additional local modifiers are now identified by actual C1 numeric names and registration defaults: pointer0xcf40a8 is1637 (default1 multiplier);0xcf40d8 is2538 (default0 addition);0xcf3fd8 is1639 (default1 in the nonlinear scalar formula). The latter computes `x * ((1-x)*modifier+x)`, which leaves x unchanged when modifier1. The local block override selector0xcf4034 is1635, while the other block's selector0xcf4080 is1634. No logged/native script producer for these exact names was found in the scoped current-log/overlay search. This search is not proof of their current local client values.

At the following deployment the current processes were revalidated as C1 PID102092 and native PID86792; the native log showed startup only. No Betty-model fix was assumed to alter world shading. The remaining distinction is a local renderer override or downstream depth/lighting operation, not a server vision payload mismatch demonstrated by the active capture.

## Actual local renderer modifiers verified

The subsequent active capture `obj/killhouse-render-modifiers-102092-active.json` validates C1 PID102092, the exact consumer guard, Killhouse render-world name, and commandTime59499 unchanged across the read. Camera was(4086.8223,360.2336,60.6850). Unlike earlier inactive attempts, this reads actual local dvar values:

|Numeric dvar|Actual value|
|---|---|
|1637 multiplier|1|
|2538 addition|0|
|1639 nonlinear modifier|1|
|1635 block override|0|
|1634 block override|0|
|1502 character-light enable|1|
|529 character-light tweaks|0|
|530/531 character scales|1/1|

The same capture's final vision bytes still match the previously decoded shipped values. Thus the two inspected renderer override selectors were disabled and their extra scalar modifiers were neutral in a real active scene. This excludes those specific override branches as malformed inputs during this capture. It does not prove the user's exact moving dark region was visible in that frame or exclude downstream depth/shadow operations.

The remaining diagnostic must correlate a frame where that precise region is visible with the affected world surface/depth or shadow projection. Repeating server vision/these modifier reads adds no discriminator now that both final scene values and actual local modifiers have been checked. No evidence supports changing them or inserting a server override.




## Distinct downstream world-lightmap input override



Followed the consumer of viewprep's +4190c flag rather than rechecking vision

or entity indices. C1 A82E20 reads numeric enum dvar1475 through CF4194.

Registration A7B909..A7B93C installs default1 with enum strings at CBC6F4:

Black, Unchanged, White, Gray. Asset loader A92D30 loads $white into CF390C,

$black into CF3910 and $gray into CF391C. This is a renderer texture/input

selection path, not a server entity scale field.



The selected pointers become world lightmap/input-bank overrides at

[CECB20]+20/+24. On change, A82E9B..ED1 rebuilds the first bank and

A82ED9..F13 the second; a null override copies each authored entry's pointer,

a nonnull override supplies that selected uniform asset instead.

Default Unchanged uses white for the first bank only when the previously

traced server sun-direction override flag +4190c is set; otherwise both

banks use their authored entries. Black/White/Gray replace both banks.



This establishes another mechanism capable of broad wall lighting changes,

but no incorrect producer or artifact correlation. Passive C1 PID102092

revalidated the exact A82E20 instruction; dvar1475 current/latched/reset all

1. Predicted commandTime was0, so no world-input-bank contents or stale

camera values were interpreted as an active Killhouse frame. The prior

active sun-override capture had no override, but it was a different frame.



No source/gameplay changes, settings writes, tests, builds or restarts.

Exact-artifact active capture is still needed to establish a geometry or

projection cause; uniform-input override is not presently evidenced as it.





### Active world-input-bank capture



After parent reported a rejoin, guarded read-only capture succeeded in C1

PID102092 at command86602 (unchanged at end), camera3810.568,526.615,45.583.

Artifact: obj/killhouse-world-lightmap-102092-active.json. New passive tool

 tools/codol_world_lightmap_probe.py records camera axes, actual lightmap

banks and the already established scene-brush comparisons without process

writes or UI input.



Dvar1475 current/reset1; sun override bytes all0; computed direction-override

flag0; both world override pointers0. The two authored lightmap pairs match

the corresponding published renderer inputs exactly:

2361028832/2361025856 and2361026176/2361037408. Thus this captured world bank

is not replaced by uniform black/white/gray assets. This is actual renderer

input evidence, not an assumption from the menu setting or server dvar value.



Camera axis lengths are1 within float precision. The253 brush entries have

matching model indices/origins and unit quaternions. Scene bytes changed

across reads, so the brush array is not an atomic frame; do not overstate

that comparison. CommandTime remained valid, and no exact dark-region

visual correlation was captured. No source defect or justified shadow fix

has emerged from the world-input-bank branch.





## Direct sun partition/projection trace and guarded capture



C1 ABCEB0 is the world sun-shadow preparation called at A84041, receiving

view, scene-camera data (+100) and frontend output at +41C50. It constructs

two partitions (ABCF25..ABCF48), with partition records at output+70 and

stride160; A8F450 submits each under the explicit sun-shadow marker.

ABCDA0 computes projected world depth from the negated

frontend light direction +419D0 and render-world center/half-size +D8/+E4.

ABC8D0 obtains a light basis through AB96D0, camera/frustum corner rays

through AB99D0 and transformed bounds through AB9AA0/AB9B20 before ABC620.

AB96D0 uses a reference axis chosen by abs(light.z), normalized cross product,

and a second cross product: malformed or zero direction would therefore

matter directly to these projection bases. A8404B..A840A5 copies eight

result coefficients from frontend+41C90 into view+C20..C3C.



Important capture correction: CF4380 is transient and can be NULL outside

frontend submission even with active predicted commandTime. The first

projection artifact at command253508 did not validate that pointer and its

sun/projection fields are INVALID. This also means the derived frontend

sun flag from the earlier command86602 artifact was not independently

validated; the direct override bytes and separate CECB20 authored/published

lightmap comparisons remain distinct evidence. The probe now waits at most

200ms for a nonnull frontend and records whether its identity remains current.



The guarded recapture succeeded at command303312..303334, frontend CF4400

still current after the dependent reads. Light direction is

(-.19076927,-.82631266,.52991927), length .99999998. World center is

(3926,-925,2070.5742), half-size(19687,17975,3288.4258). Eight copied

coefficients are(.578125,.708374,1,.25,16,32,-8,-24); all finite.

Raw output+41C50..+41F7F is preserved in

obj/killhouse-sun-projection-102092-guarded.json, with its internal matrix

semantics explicitly not yet asserted. This rejects a zero/nonunit sun

basis or nonfinite captured coefficient explanation for that frame.



Next discriminating read is the individual partition clip matrices/bounds

inside this captured block and their projected wall coordinates, after

tracing their writers in ABC8D0/ABCBE0. An exact screen-space artifact frame

would be required for causation. No arbitrary camera-relative bias, extra

zone or server field patch is supported by the current result.







## Partition matrices decoded; dynamic submission sampled



AB98B0 constructs a view matrix at each partition record+0. AB9790 zeros

and writes its orthographic projection at+40, calls61A1D0 with view/projection

and destination+80, then61A630 with destination+C0. Offline decoding the

valid command303312 capture confirms combined=view*projection with maximum

numerical error6.7e-13. Near and far orthographic XY spans are256 and1024

world units. The captured camera maps to clip(.542251,-.109396,.536402,1)

and(.541813,-.110845,.536402,1). These are finite, nonsingular matrices;

this does not establish correct depth sampling at the reported wall.



Decoder tools/codol_decode_sun_partitions.py accepts an independently

established --point world coordinate for that comparison. No actual wall

hit was available; camera coordinates are explicitly labeled NOT wall.

Decoded artifact: obj/killhouse-sun-partitions-decoded.json.



A distinct active capture at command464654 reads dynamic DObj submissions

from FB5624, stride78, counts FB5618/FB561C. A83480's key producer packs

entity into bits7..18 and low renderer flags above19; +6C carries DObj.

Six submitted records were four corpse models (entities19..22), droppedG18

(entity116), and local M9 viewmodel(entity2047). Values at bounds fields

+38..40 range approximately1.2..112.3, not map-sized magnitudes. Those fields

initially receive a common DObj bound scalar, then can be refined by later

processing; the capture labels them by field offset rather than asserting

all are a final radius. Captured low flags are100 for corpses,0 for dropped

weapon,3 for viewmodel; upper input flag bits may be discarded by packing.



This list establishes renderer submission, not actual shadow-pass eligibility.

Neither camera-following caster causation nor absence of static-world shadow

sampling problems follows from it. Raw records are retained in

obj/killhouse-partition-dobj-102092.json. No source/gameplay edits, UI actions,

process writes, builds or tests. Required next evidence remains a known wall

world point tied to the exact artifact frame and shadow-pass caster selection.





## Camera-forward surface inference without user input



Added tools/codol_shadow_surface_inference.py: reads the native clipmap

geometry and evaluates ray/triangle and convex brush-plane intersections

offline. It never calls engine functions or writes either process. Native

PID102952 modulebase2E0000 plus current symbol cm RVA3F0DA0 gives6D0DA0;

clipmap name independently validates maps/mp/mp_killhouse_sh.d3dbsp.

Counts19941 vertices and36436 triangles pass bounds checks. The current

client was inactive, so the tool explicitly uses the earlier guarded camera

capture at command303312 rather than treating current stale memory as play.



The nearest solid candidate is brush11945 at distance29.8301, world point

(3717.3098,-346.1227,52), normal(0,0,1). This captured camera was pointing

down at an elevated horizontal surface, plausibly a step or ledge; it does

not identify the reported dark wall. Other forward hits occur at heights44,

32.35 and4. The first inferred point projects to near clip

(.436686,-.091738,.537052,1) and far(.515421,-.106431,.537052,1), inside

both partitions and away from their XY edges. No partition-clip failure

appears at that inferred surface.



Artifacts: obj/killhouse-shadow-inferred-surface.json and

obj/killhouse-inferred-surface-projection.json. This is explicitly inference

from collision geometry: dynamic submodel transforms, renderer-only surfaces

and material alpha visibility are omitted. It is not an engine raycast, exact

screen pixel hit, or proof about the original wall artifact. An appropriate

active camera capture can now be evaluated without asking the user for world

coordinates or driving the UI.



Dynamic records previously captured demonstrate scene presence only. The

sun-shadow caster eligibility/material depth-pass consumer still needs a

separate C1 trace; copying T5 render flags would not establish it. No source

fix is justified by the current matrix/surface results.





## Actual dynamic caster eligibility: local viewmodel exclusion



C1 A8B030 builds two sun draw lists: partition visibility starts at FCC4E4

and advances300 to FCC7E4; the loop's draw-list index advances from10 to14

and stops18. Only scene slots with visibility byte1 call A81730.



Producer A8B810 obtains the active frame's partition command records at

FF7DCC + frameIndex*2B8. It extracts scene renderer flags from packed key

(A8B896..A8B8A6) with shift19 and mask41. For the two sun partitions it

tests the command's mask at+E8/+1D0 (A8B8E3/A8B8FF); overlap forces the

corresponding visibility byte to0. The alternate visibility fallback branch

at A8B979/A8B9A7 applies the same exclusion masks. Earlier traced A8F450

constructs these sun commands and explicitly writes mask41 at A8F481.



Consequently the captured local M9 viewmodel (entity2047, packed renderer

flags3) is excluded from both sun partitions: flags3 & mask41 =1. This is

an actual producer/consumer exclusion, not an assumption from model names.

It applies to that captured submission; it does not exclude other geometry,

spotlights, depth effects or future submissions with different flags.

The four corpse flags100 do not overlap41, so they remain candidates subject

to ordinary per-entity visibility and surface material eligibility.



A81730 further rejects a scene DObj with no populated surface record at+44.

For each surface it follows material+50, then+8, and checks the requested

technique slot +C+technique*4 at A81821..A8183A; absent depth/shadow technique

skips emission. This ties caster eligibility to the actual loaded material,

not merely native entity appearance or main-pass visibility.



The passive probe now records both sun visibility bytes and populated surface

record pointer for each dynamic submission. Latest C1 PID102092 commandTime0

means the attempted capture was skipped; no stale visibility bytes were

interpreted. Native had advanced to PID99836, but no native memory was used

for this eligibility trace. No source edits, UI/process changes or tests.





## Brush material shadow-technique gate



Followed remaining brush/static-model paths, excluding the already traced

viewmodel. Sun list A8B1C0 reads brush visibility at FE6504 (near) and

FE6704 (far); only value1 reaches A80FE0. The latter obtains prepared surface

references from frontend+42704 using the submitted brush's first word and

8-byte surface stride. Each surface's material pointer is at+10. At

A81037..A8104B it follows material+50, then+8 (resolved technique set), then

+C+techniqueIndex*4. No technique means no emitted shadow draw surface.

The technique index passed by this list comes from CF3F40. These are actual

caster gating inputs that a future artifact capture can distinguish.



A8B560 prepares the surface reference list. Numeric bool1529 (registered at

A7C115..A7C12D, defaulttrue) chooses either all model surfaces (count+34,

first index+36) or a pre-counted subset (+38). False filters GfxSurface byte17

bit2 at A8B614..A8B623. Its semantic setting name is unestablished here; do

not label it a shadow toggle or change it based on that numeric control.



Probe now captures near/far brush visibility plus the actual material name,

requested shadow technique index and whether the resolved technique exists,

only while the guarded frontend pointer remains current. Latest attempt

obj/killhouse-brush-sun-materials-102092.json was inactive and skipped.

No claims about current materials or shadow eligibility were inferred from

uninitialized scene storage. Native PID99836/client102092 were revalidated;

no process changes, UI input, shared source changes or tests occurred.



## Numeric1529 identity resolved by consumer comparison

C1 A80FE0 has the same complete surface-emitter structure as named retained
IW3 R_AddBModelSurfaces in tools/cod4_dasm/src/_r_scene.asm: bool chooses
all surfaces versus nondecal count, then each prepared material is gated on
the requested technique before draw-key emission. C1 adjacent camera emitter
A80E80 likewise corresponds to named R_AddBModelSurfacesCamera. Both retained
consumers explicitly read r_drawDecals. Combined with C1 A8B560 filtering
surface flag2 when1529 is false, this strongly identifies1529 as decal
rendering control. It is behavioral identification, not a recovered C1 name.
Do not reuse T5 flag2's different primary-light-conflict meaning here.

Passive current/reset capture both1 in client102092. CommandTime0 makes the
new artifact obj/killhouse-decal-filter-102092.json inactive for geometry;
the probe reads only this persistent dvar before skipping scene data. This
setting is at its shipped default, and no incorrect native producer or
camera-dependent darkening cause is established. No client settings changed.


## Shadow sampling settings provenance (2026-09-14, passive/offline)

C1 registration names 1611 and 1612 are the renderer shadow polygon-offset scale and bias. The complete consumer at AB4540 matches the named OpenBLOPS shadow polygon-offset render-state implementation in `Engine/Renderer/gfx_d3d/r_state.cpp`: CF4070 current feeds slope-scale depth bias render state 175 at AB45D9; CF4318 current feeds depth bias render state 195 at AB45F6 after the renderer scale factor. Other consumers at AD8488 and AD9E4E feed these values into shadow shader constants. This establishes rendering relevance, not artifact causation.

Passive capture `obj/killhouse-shadow-sampling-dvars-102092.json` had no predicted gameplay state. Its current/reset values were 1611=1.15/1.5, 1612=1/4, 1617=.185/.25, 1623=1/0; target dimensions/counts matched resets. Later capture `obj/killhouse-shadow-sampling-active-102092.json` was requested immediately after a connection log, but its guard still returned commandTime zero. Its persistent values were 1611=2, 1612=.125, 1617=.25, 1623=1. Filename does not establish an active scene; geometry was correctly skipped.

These differences are not evidence of leftover diagnostic edits. C1 function 60F2D0 loads the shipped StringTable `mp/cameraPosTable.csv` at 60F303, selects a row by its column-zero camera name, and applies columns 10/11/12 to 1617/1611/1612 through calls 6100D9/6101A8/610278. Extracted original and patch table rows are saved in `obj/code_post_gfx_mp-camera-shadow-rows.json` and `obj/patch_code_post_gfx_mp-camera-shadow-rows.json`. Both have `character_loadout_center` = .185,1.15,1, exactly the earlier observed triple. The weapon_loadout family, including patched `weapon_loadout_m4a1techevent_mp`, uses .16,2,.125. `weapon_loadout_spas12_mp` deliberately uses bias44. Do not replace these authored viewer settings with registration defaults indiscriminately.

Shipped `ui_viewer_hide.cfg` sets 1617=.25,1641=0,1498=0,1477=2.5,1478=1.5. It does not restore1611/1612. This explains a possible mixed persistent state after leaving the viewer. Whether these viewer bias values survive into actual Killhouse rendering still requires a guarded active capture plus transition-path review; there is no confirmed native publisher defect yet.

1623 appears in the shipped `configure_mp.csv` graphics/GPU configuration columns, so its nondefault boolean has a separate legitimate graphics initialization path. Decrypted main-IWD cfg/csv/gsc scan found no explicit relevant setters. Cached-zone text scan found the viewer hide command above; numeric-name string searches alone had missed the direct C1 table-driven setters. Encrypted player config was not decoded and is not claimed excluded.

No source/config/runtime setting was changed. Next discriminator: capture bias/scale with a valid gameplay state immediately after viewer hide/join and determine whether original C1 map initialization restores these fields elsewhere. A native restoration would only be justified after establishing the intended transition behavior, not merely a mismatch with reset values.


### Matched viewer-hide transition capture

Parent-controlled Ready transition on the same C1 PID102092:
- `obj/killhouse-shadow-lobby-before-join-102092.json`: commandTime0, scale1611=2, bias1612=.125, filter1617=.2. Exact authored `team_urban` row.
- `obj/killhouse-shadow-after-ready-102092.json`: commandTime0, scale2, bias.125, filter.25. Hide command's filter restoration occurred; gameplay had not initialized, so this does not yet prove gameplay contamination.

C1 teardown queues `exec ui_viewer_hide` at60A7E7..60A7F3, after renderer world teardown A887D0. A887D0 clears world/scene pointers and calls A88620; it does not directly reference either bias dvar. All direct pointer references to CF4070/CF4318 in the executable are registration, camera table setters, and three renderer consumers. This excludes a separate direct-pointer map-init reset, but not generic dvar-name/flag resets in broader lifecycle code. Scale registration A7C70D uses flags0 (EBX initialized0 atA7B3A3); bias registration A7C745 uses0x100. Do not borrow IW3 flag meanings: CoDOL dvars.py identifies0x100 as EXTERNAL, not CHEAT.

The verified replicated bank in `obj/killhouse-replicated-dvars-102052-postfix.json` contains no1611/1612/1617. Its only shadow-named pair is `sm_sunShadowScale=1`. Native CODOL_RefreshServerDvars in codol_sv_assets.c publishes same-name registered SYSTEMINFO vars, and source search finds no numeric bias setters. Therefore current evidence identifies a client viewer lifecycle candidate, not an incorrectly published native bias field. No correction is justified yet; active scene capture is pending the unrelated connection blocker.


### Gameplay persistence confirmed, causation still unproven

Second matched parent-controlled Ready sequence reached actual gameplay:
- Lobby `obj/killhouse-shadow-team-jungle-baseline-102092.json`, command0:1617=.175,1611=2,1612=.125, matching shipped team_forest.
- Gameplay `obj/killhouse-shadow-jungle-after-ready-102092.json`, command32807..32819:1617=.25,1611=2,1612=.125. Frontend pointer remained current and brush scene unchanged across reads.

This proves authored lobby bias values survive into the current MP session. It does not prove the original official MP transition intended different values or that the dark region is caused by the retained bias. Spectator camera was3492,-238,232. No world or view DObjs were submitted.253 brush submissions had matching indices/origins; authored/published lightmaps matched. Three brush entries were sun-visible in both partitions, but the sampled prepared-material lists were empty; do not infer material eligibility from that incomplete stage.

A controlled comparison of1611/1612 against known registration defaults (1.5/4) at an unchanged gameplay camera would discriminate the retained-bias candidate. This is a diagnostic comparison only: permanent native publication requires deciding intended gameplay values and accounting for map tuning. Worker performed no writes or input; parent controls any visual comparison.


### Parent-controlled bias comparison accepted

Parent sent normal server reliable dvar commands setting1611=1.5 and1612=4. Passive `obj/killhouse-shadow-default-comparison-102092.json` confirms actual C1 acceptance at command177557: scale1.5,bias4,filter.25. Frontend and brush table remained stable across this read. Spectator origin remained3492,-238,232; forward-axis dot with the prior gameplay capture was.884668 (about28 degrees), so the images are not a fixed-view A/B pair. Parent reports the broad region still appears visible. This observation cannot be dismissed as rejected dvar commands, but is not yet a controlled visual exclusion. Worker made no runtime writes.


### Restored comparison and1623 discriminator

Passive `obj/killhouse-shadow-restored-comparison-102092.json` confirms parent restoration accepted during gameplay at command92850:1611=2,1612=.125. Frontend pointer was unavailable, so this capture contains persistent dvars only; no scene interpretation.

C1 numeric1623 has exactly one executable consumer outside registration: A83B8D loads its pointer, A83B99 checks currentboolean, A83BA1 overwrites computed scalarCF3EF8 with1 whenenabled. Immediately beforehand A83B85..A83B93 copies numeric1619 currentvalue intoCF3EF8. Current1619=1, so either1623 branch produces exactly1. Subsequent alternate shadow mode atA83BA7..A83BF3 transforms that same scalar and selects target dimensions/counts; its input is still identical for either1623 value. Therefore toggling1623 alone cannot change this captured configuration's shadow computation. This is an exact consumer exclusion, not a general claim that1623 never matters. Registration A7C84C uses archiveflag1 and defaultfalse; configure_mp.csv legitimately selects it by graphics configuration.

No permanent bias restore was added: parent observed the broad pattern still under accepted registration-default bias values, with camera-direction drift preventing a perfect visualA/B. No demonstrated server-authored scene-light publication mismatch emerged from this1623 branch. Remaining useful captures must identify actual artifact-facing surface/material and per-partition sampling output; repeating forced-unit toggles at1619=1 would provide no new evidence.

### Derived sampling consumer, guarded capture pending

Offline trace now follows the renderer-owned scalar beyond its dvar input. A83CEE..A83CFC multiplies target dimension2642 by current1617, then divides by the selected target extent before storingCF3F04. ABC789..ABC7AB readsCF3F04/CF3EF8 into its output+4c and a constant multiple into+50. This is a physical sampling/target-footprint path;1617 should not be described as an independently adjustable screen-space blur radius. The producer is local renderer setup and selected target dimensions, not an additional server snapshot field. This does not establish correct GPU sampling or eliminate a shadow artifact.

The passive world probe now records guarded derivedCF3EF8/CF3EFC/CF3F04, their consumer ratio, and rawFAA9A8 target constants. These fields are read only after both gameplay and frontend-pointer guards. They permit distinguishing valid dvars but invalid/zero derived sampling from normal derived sampling; they do not read GPU depth/shadow texels. Existing final frontend-stability checks still apply.

Current C1 PID102092 was revalidated. Captureobj/killhouse-shadow-derived-sampling-102092.json returnedcommandTime0, so the new fields and scene were intentionally skipped. No active evidence was inferred from retained frontend storage. No native/client settings changed and no tests/builds ran. A later guarded active capture can check the actual derived ratio; absent that capture, there is no evidence-backed producer correction. If derived values remain finite/nonzero and consistent with selected target geometry, the remaining visual discriminator requires identifying the exact artifact-facing surface and its GPU depth/shadow sampling, rather than resetting more unrelated dvars.

## Map-loader render defaults: exact-name publication gap

Effective source ordering in CODOL_ReadScriptSourceWithNativeOverlay is native scripts, alpha overlay, vendor/mp, vendor root. There is no native or alpha _load.gsc override. Alpha's mp_killhouse_sh.gsc calls FX, vendor _load, minimap, team setup; its provenance explicitly says it is a reconstructed minimal template, not extracted original CoDOL gameplay GSC. Vendor _load sets level._loadStarted once, installs the five vision channels (naked map name, night, missilecam, thermal, pain map name), then executes six IW4 renderer-default setDvar calls. _art::main is inside a developer block and does not supply a missing ordinary map-lighting configuration here.

Native GScr_SetCvar calls Cvar_SetAllowCheatOnly; its optional third argument adds0x400 only when supplied. The six calls have no third argument. Unknown dvars are created as external/user-created strings, without SYSTEMINFO. CODOL_RefreshServerDvars only refreshes names whose native variables are SYSTEMINFO. Therefore these source statements are not proof that the intended client renderer values were published. The earlier received configstring bank indeed retained specular2,gridTweaks1,intensity1.1,contrast1 instead of vendor defaults2.5/0/1/0.

A further necessary distinction is now proven by passive C1 memory, not merely naming assumptions. C1 replicated applier466020 calls625330 with the received literal name;625330 resolves6232C0, whose hash6217E0 and case-insensitive comparison do not remap friendly names to numeric registrations. Unknown names become string variables via624740. tools/codol_map_lighting_dvar_probe.py passively implements that exact hash/chain lookup (next+48), verifies numeric globals and code guard, and compares the two identities.

Captureobj/codol-map-lighting-dvars-102092.json (commandTime0, persistent dvars only):

| Intended meaning | Renderer numeric/current | Separate friendly EXTERNAL string |
| --- | --- | --- |
| specular scale |1477 /2.5|r_specularColorScale /2|
| diffuse scale |1478 /1.5|r_diffuseColorScale /1|
| grid tweak enable |1498 /true|r_lightGridEnableTweaks /1|
| grid intensity |1500 /1|r_lightGridIntensity /1.1|
| grid contrast |1501 /0|r_lightGridContrast /1|
| sun scale |1619 /1|sm_sunShadowScale /1|

Each pair has different pointers/types. Friendly received values are not evidence for actual renderer state. Semantic labels originate in the C1/IW4 alignment and existing renderer consumer work; pointer separation and exact numeric names are directly verified. Current1477/1478 also match shipped ui_viewer_hide assignments2.5/1.5. The inactive capture cannot establish their previous gameplay values or claim1498 caused the moving shadow.

This establishes missing integration of the loader's friendly renderer intent with C1 numeric variables, rather than proving the reconstructed Killhouse script has correct original lighting defaults. A native correction must use verified C1 target identities and explicit publication/lifecycle, preserve authored map/vision behavior, and be reviewed before touching shared source. Blindly changing all constants or resetting every renderer dvar remains unjustified. Global map VisionSetNaked already has a nativeC1 configstring producer and previously verified final blended values; it is a separate successful path.

### Staged publication capability; no default override integrated

Review-only source is in obj/lighting-publication-stage/codol_script_lighting.c/.h (outside makefile sources). It maps only the six exact friendly/numeric identities and sends an explicitly supplied numeric value through the existing C1 200-pair bank. C1 keeps its real registered types, bounds and reset values. It rejects invalid values and calls before inherited constants are installed. No startup defaults, live writes or shared setter edits were added. Not built/tested, not a completed shadow fix.

Do not attach this helper unconditionally to every inherited _load default yet: that would deliberately change actual diffuse1478 from shipped viewer-hide1.5 to IW4 template1, and could overwrite legitimate authored grid tweaks. The map script is reconstructed and does not prove original C1 desired values. Any integration must establish authored values first, then call after map constants load, republish after each reset, and publish global updates to existing plus later-joining clients. The existing replicated-bank helper covers those recipient groups once supplied a map-lifetime value. Per-client setClientDvar must use the name resolver and its existing per-client reliable path, not broadcast through this global helper. Native script getters should retain their chosen semantic state or be canonicalized consistently; this stage does not implement a general alias registry.

Scoped producer audit found these six friendly names used by other inherited IW4 map scripts as well, including distinct favela/subbase/estate grid settings and estate sun optimizations. A blanket setter rewrite would enable all those unverified values, not just Killhouse. Therefore the staged API is explicit capability, with call-site integration held for parent review and evidence. Existing global VisionSetNaked(mapname) publication remains intact.

### Authored world sun-blind path, distinct from depth shadows

New offline asset captureobj/killhouse-authored-gfxworld-sun.json decodes originalmp_killhouse_sh gfx_map asset200. Patch_mp_killhouse_sh contains no type21 replacement. The serialized sun block atworld+FC is valid; blindMaxDarken at+130 is0, glareMaxLighten at+144 is.08, sunFxDirection at+150 is(-.989257,-.022069,.144512). The header has30 primary lights and sun primary index3. Flare direction is separate from the previously captured shadow-light direction and should not be conflated with it.

C1 consumerAB5890 readsworld[CF39A0]+150..158, dotted against the current view forwardaxis. AB58D1 testsworld+130; if notpositive, AB58E4 writeszero blindoutput. Whenpositive, AB5970 multiplies the interpolated visibility by that exactworld+130 value. This matches the named sun-blind structure/algorithm in OpenBLOPSrb_sky.cpp, but all stated C1 offsets are verified by C1 instructions. SetterA7D965..A7D96E copies numeric1716 at[CF434C]+C into sunstructure+34, matchingworld+130 after itsFC base.

This identifies a concrete camera-dependent darkening input with a known authored zero, not a speculative dvar reset. A runtime positiveworld+130 during Killhouse would establish departure from the authored asset and justify tracing the sun setter/lifecycle. A matchingzero excludes this particular blind darkening branch in that activecapture, while still allowing other shadow/depth/material causes. The probe now records the entire96-byte sun block plus these decoded fields only after active-game/frontend guards. RevalidatedPID102092 returnedcommandTime0 inobj/killhouse-world-sun-after-audit-102092.json, so no runtime world claim was made. No user input, settings changes, native edits, tests or builds.

### Active request captured Rust, not Killhouse

The next passive request revalidatedPID102092 and found nonzero commandTime105241..105263. Its lightmap count1 and world bounds differed from Killhouse, so the world identity was checked before interpreting the apparent sun-blind difference. Actual renderer world is maps/mp/mp_rust.d3dbsp. The probe now explicitly reads renderer-world name and skips Killhouse scene interpretation for any other map, in addition to the existing code/gameplay/frontend guards.

obj/killhouse-world-sun-live-request-102092.json captured Rust: blindMaxDarken.18502, glare0 anddirection(.919158,-.195373,.342020). Offline extraction from originalmp_rust.zone matches all these fields exactly. This is legitimate authored Rust lighting, not evidence of Killhouse contamination. Derived scalar1, footprint.25 and ratio.25 were finite, but only establish Rust values. Followupobj/killhouse-world-sun-live-request-identity-102092.json records the explicit mismatch and skips scene capture. Numeric dvars were separately saved inobj/codol-map-lighting-dvars-live-request-102092.json; they likewise must not be labeled Killhouse gameplay values.

This capture establishes no Killhouse shadow cause. It prevents a false positive that nonzero predicted commandTime alone would have allowed. No client input or runtime setting changed.

### Verified active Killhouse capture, PID100756

Revalidated C1PID100756 and nativePID40176 paths. obj/killhouse-shadow-active-100756.json confirms renderer maps/mp/mp_killhouse_sh.d3dbsp, command89857..89868, frontend pointer current and brush submissions unchanged across reads. Camera(4044.484,984.812,63.621),253brushes,18world DObjs/0view DObjs.

Runtime sun blindMaxDarken=0,glareMaxLighten=.08 and sunFXdirection exactly match original Killhouse. Therefore the verified camera-dependent sun-blind branch cannot produce darkening in this capture. Derived samplingCF3EF8=1,CF3EFC=1024,CF3F04=.25 and consumer ratio=.25 are finite/nonzero. No malformed derived footprint observed. This does not inspect GPU texture samples or prove the user artifact was visible in this exact frame.

Companionobj/killhouse-lighting-active-100756.json atcommand90455 confirms actual numeric1477=2.5,1478=1.5,1498=false,1500=1,1501=0,1619=1. Consequently grid tweaks are disabled in actual Killhouse, despite separate inherited friendly string r_lightGridEnableTweaks=1. Do not infer renderer state from those EXTERNAL strings. The numeric values match the shipped viewer-hide/default path; diffuse1.5 differs from the inherited IW4 _load template1 without proving it wrong forC1. Depthbias1611/12 remains2/.125, as previously observed. Neither a sun-blind fix nor a grid-tweak reset is justified by this capture. No runtime mutation occurred.

### Separate single-XModel caster path captured

Prior probes covered sceneDObj plus brushes but omitted C1's optimized single-XModel scene branch. This is a distinct server-entity rendering consumer, not another viewmodel flag recheck. C1 A835A5 allocates the single-model scene slot; A835C3 selects baseFCD6FC with stride48h, countFCD6F0 (capacity1024). It stores model+4,obj+8,quaternion+C,origin+1C,scale+28,packedentity/renderflags+2C,radius+30,lightingorigin+38. A83642..A8364B explicitly writes unit scale. A8B0CA..A8B124 submits its shadow surfaces only for partition visibility1; it also checks model availability and packedflag0x20000000. The separate camera/partition visibility arrays areFDF6FC/FDFAFC/FDFEFC, verified by A8BB39..A8BC1A.

Extended the passive world probe with these records and per-record/count stability checks. Active exact-Killhouse captureobj/killhouse-single-model-casters-100756.json atcommand346855 has112singlemodels, stablefrontend/count/records. Camera(3066,-545,64.125). All scales1, all quaternion squared lengths within.001 of1. Visibility triples(camera,near,far):105records(2,2,2),6(0,2,2),1(2,2,1).

The only captured partition-visible model is entity891 me_ac_big, radius43.597,origin(3286,-748,613),about625units from camera. The largest submitted model is entity448 com_drop_rope_obj,radius414,origin(3776,-2818,164),but neither sun partition marks itvisible. Other large examples are ordinary fence poles withradius99.33. No oversized-scale, malformedrotation, or camera-attached single-model caster was found in this frame. This does not exclude a transient caster on another frame, GPU material defects, or prove the exact visual artifact occurred during the sample. No native producer mismatch justified a patch. Runtime untouched.
