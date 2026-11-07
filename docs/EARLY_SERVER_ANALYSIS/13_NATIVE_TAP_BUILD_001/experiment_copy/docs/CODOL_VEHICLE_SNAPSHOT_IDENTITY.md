# C1 vehicle snapshot identity — parent evidence

Aligned VehicleCl_ResetEntity starts67cc10; diagnosticc72e60 names it and prints instance/definition/entity/localclient. cent.nextState startsate4. Readscent13c =>wire58. Low4bits select instance0..15 in2bc2798,stride88. At67cc53..67cc5f, (cent13c>>4)&31 becomes instance+4, which indexes VehicleDef table2bc3018. Therefore wire58 carries instance|(definitionSlot<<4), matching9-bit eType12/14field tables. No high bits can be inferred from this function.

Caller46b9ce..46b9dc invokes reset with cent inedi and localclient onstack; enclosing type-dispatch still needs aligned table decoding to confirm all supported types. Previously reported488943 is in serialization488900, reading/writing the whole0x880-byte instancearray through a functionpointer. It is not the per-snapshot slot writer.

Remaining native integration: stable16-instance allocation and lifecycle, actual native vehicle-info to31usable definition slots, captured state surviving archive/entity reuse, body/steering/turret/flags/model fields, exact eType dispatch. Do not publish only a selector and claim a complete vehicle snapshot. Current codol_sv_gameframe.c turret branch is the nearby integration surface. No builds/tests/runtime or client match verification.

## Native vehicle instance allocation and conversion assignment

Retained G_VehiclesInit iterates8 slots ofstride0x354, entNum+1b8=1023empty; SpawnVehicle scans same8 and storesentNum/infoIdx+1bc. This fits C1low4instance packing without another allocator. Native lifecycle can own slot identity; definition slot must be captured with entityState so archived snapshots do not read live reused records. Existing codol_entitystate_ext copies at sv_snapshot.c1105/1194/2004 provide capture propagation surface. No vehicle snapshot branch integrated yet; current entity_seed rejects vehicle types bydefault.

Started ONE fresh Claude Opus/high bounded40turn worker vehicle-native, supervisor66088/verifiedCLI71192. Owns NEW codol_vehicle_native.cpp/.h and scratchvehicle-native-* only. Native VehicleDef-to-simulation conversion uses complete mountedreader; shared changes patchonly. Parent owns existing vehicle assets and snapshot capture. Prompt explicitly repeats unrestricted native rewrite permission and nohooks/builds/tests/syntax/assembly/emulation/runtime/nestedagents, checkpoint3calls/reserve10handoff. All earlier workers terminal. No output counted; no match entry verified.

## Vehicle identity captured-state representation

Added vehicle_identity/vehicle_known to codol_es_ext_t and capture/get API. Valid instance0..15/definition1..31 packs into9bits; invalid/unresolved capture clears previous identity, getter preserves output on failure. Existing whole-extension copies and entity/map/archive clears carry/reset it. Extended BOTH internal archive writers and reader with changed/known/9bitidentity record after primaryweapon; reader rejects slot0 identity, truncation and nonvehicle state. This changes the native internal archive format; it is not a new C1 network field.

Spawn/correct definition-loader producer and frame serializer not yet wired; no claim that actual vehicle snapshots work. In particular, do not read live scr_vehicle during delayed serialization. Native eight-slot lifecycle will supply instance; successful converteddefinition supplies slot. Workervehicle-native71192 verified live, ownershipnewnativecpp/h only. No builds/tests/runtime or GSC count change.

## C1 vehicle pose and frame consumer trace

Aligned VehicleCl frame routine67cfc0: instance fromwire58 low4; wire5c&7f ->instance18flags; wire74 ->instance38; derives speed from next trajectory delta and invokes67ccf0(local velocity from two position trajectories and interpolatedbodyaxis),67ce50(angular velocity from two angular trajectories),67cf30(accumulates scroll using def14),67c760(other effects/flags). Do not invent separate network velocity fields for these derived values.

Aligned pose routine67d080 reads prev/next state pairs and shortest-angle interpolates fields: wire60 at67d0a8->pose40; wire70 at67d16b (continue to recorddestination); wire64 at67d217; wire6c at67d2c5; wire68 at67d372->pose4c. At67d412, wire7c(cent160) is integer converted usingsecondsfactor into pose50. It resolves bone tags from24ee0c0/c2/c6 at67d46b onward. Exact semantic mapping of these five posefields to nativebody/roll/steering/gunangles still needs bone-controller evidence; do not infer just from layout proximity. Following posecode67d590 is next bounded trace. C1table12/14 uses measuredfloat/angle/time codecs for these fields.

Native snapshot identity storage alreadywritten, but no complete vehicle framebranch integrated. Nativeconversionworker71192 remains lastverifiedlive. No builds/tests/runtime or clientmatchentry.

Additional aligned pose destinations: wire70 -> pose42 (67d207); wire64 -> pose44 (67d2b4); wire6c -> pose46 (67d361). Branch67d590 fills six bone indices60..65 withFE and returns; alternate67d5ac derives wheel/bone data after a distance check. Server helper67a1a0 resolves shared string slots24ee0c0/0c2/0c6 into bone fields384/388/390. Exact part semantics remain open; these observations do not authorize guessed snapshot mappings.

### Vehicle pose mapping implemented from both server and client evidence

C1's aligned spawn function67a500 sets vehicle+4 to entity+58 at67a6ab..67a6ae and writes packed identity there. Controller67ac10 then reads this block:

| Wire offset | Meaning | Controller evidence |
| --- | --- | --- |
| 60 | body pitch | block+8 -> tag_body angle[0] |
| 64 | body roll | block+c -> tag_body angle[2] |
| 68 | steering yaw | steering update678680 -> block+10 |
| 6c | gun pitch | block+14 -> tag_barrel angle[0] |
| 70 | gun yaw | block+18 -> tag_turret angle[1] |

String initialization57787c..5778ec confirms slots24ee0c0=tag_body,24ee0c2=tag_turret,24ee0c6=tag_barrel. C1's controller resolves these through vehicle384/388/390, respectively. Retained G_VehEntHandler_Controller independently consumes native body54/58 and gun64/68 in the same pitch/roll/yaw roles.

Added CODOL_OverlayEngineVehiclePose in codol_engine_state.c/.h: translates the five named fields atomically from captured entityState. It is deliberately only the pose portion of the pending full vehicle adapter, and has no frame call site yet. No build/test/runtime validation.

Correction to avoid an attractive but unsupported mapping: wire7c is read with millisecond-to-second scaling by the client, but C1's producer67b3a4..67b3b8 loads VehicleDef+160, scales it and stores entity+7c. It is not demonstrated to be a level-clock timestamp or the retained native materialTime. Preserve this distinction before integrating the full vehicle serializer.

Suspension resolved: native G_VehEntHandler_Think_200 multiplies named vehicle_info_t.suspensionTravel (8c) by1000 and writes entity.time2(70). C1's67b3a4..67b3b8 similarly writes VehicleDef160*1000 into entity7c. Client67d703..67d73f uses the decoded value as negative body-up travel for the wheel trace endpoint. Added captured time2->wire7c to the pose overlay; materialTime is not used. The table's time codec does not imply timestamp semantics.

C1 entity74 is a controlling-client number, not native vehicle.team: spawn67a6df..67a6ff reads optional player's ps140 and writes block+1c, otherwise zero. Native player-state translation codol_engine_state.c independently maps ps.clientNum to C1 ps140. Frame67cfc0 copies this field to client vehicle-instance38. Full vehicle adapter needs a captured controlling-client value; do not translate native union.team into this field by proximity.

### Vehicle flag2 producer narrowed to physics state
- Aligned C1think67b016 clears wire5c bit2 before testing vehicle+210 (physics instance). When present,65c7e0 updates position/angles/velocities from it;67b19a..67b1ac then setsbit2 iff physics-instance1ec iszero. No claim yet that1ec is wheel contact count; that is a lead requiring its producer.
- This excludes translating native occupied flag1 directly into C1bit2. Native vehicle flags1=occupied (use/unlink),8=first-think initialized (G_VehEntHandler_Think/InitFirstThink), so copying nativeflags into C1flags would conflate unrelated state.
- Next physics trace: writes to instance1ec in65c7e0 and related native physics routines. Remaining wireflag20 GSC setter identity and40 ownership binding still unresolved.
- No source flag mapping guessed; no builds/tests/runtime.
