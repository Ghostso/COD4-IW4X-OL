# Parent animation review — not registered

Animation finish is confirmed terminalmax15 (16reportedturns), cost1.811803; CLI73256 is gone. Ownership released. No shared registration patch accepted. VehicleCLI77704 remains lastverifiedlive.

Rejected worker conclusions: eType6 field0x6c is codec-97, which encodes a full timestamp with short delta optimization (codol_delta.c), so a32-bit start time DOES have a possible wire home. This does not prove its semantic purpose. Native gentity_t DOES have classname (entity.h), and scr_const.script_model exists (scr_vm.h). Parent corrected draft receiver to use it and removed invented exact-argument-count checks absent from cited IW4 handlers. Other draft parity gaps (name bounds, classname error staging, empty-name handling, complete C1 consumer) remain; no bindings counted.

New aligned C1 evidence:440e20 explicitly tests nextState.eType6 atcent+e8, reads selector cent+144 (wire60, masked7ff), timecent+150(wire6c), flagcent+154(wire70). If timezero clearsselector; outputselector/time/flag passed to440f-class consumer. Caller441035..441088 compares returnedtime againstCGtime;44109d allocates128-byte state,441105storesselectorword atstate78;44119a freesstate whenselectorzero. These findings refute the report's no-timestamp rationale and provide a concrete next trace. It may be a different animation/physics subsystem; do not label this proven MP animation or write fields yet. Next inspect4405c0,4402f0 and callers/asset lookup to identify selector semantics.

No builds/tests/runtime. No real C1 match entry verified.

## Script-mover follow-up and vehicle handoff

Parent followed aligned C1 routines4405c0,4402f0,440330,440c30,441290. The selector/time state participates in DObj root transforms and linked-parent transforms:4405c0 resolves an entity DObj through25d9ed8/2575ed8 and calls63aa40, which reads its tree and extracts quaternion/translation;441290 writes resulting position/angles. These calls do not yet identify the selector-to-animation producer. A bounded offline instruction scan of440000..448000 yielded selector/time accesses440e32/440e38 and cache78reads/writes4410ef/441107; other hits442a38/443173 are leads only. A rawrelativecall scan found441050 as caller440e20, not proof against indirect calls. No state fields published; missing animation bindings remain unregistered.

Vehicle original worker confirmed terminalmax55,56reportedturns,cost4.6019735,session3da84d54-d463-45cc-bbab-f1ae4d6f2884. Source files exist but final report/patch absent. Resumed SAME session for bounded15turn handoff with first-action report, no broad research. Supervisor75340, verifiedCLI78100. Ownership unchanged until terminal. Initial draft precachevehicle adds exactargc1 absent from measured IW4handler; parent must remove/review after worker finishes, not count as support now. All no-hooks/no-builds/tests/runtime/native-rewrite rules repeated. Animation ownership parent, no live animationworker. No match entry verified.

## Parent review: C1 animation entry layout differs from retained header

Aligned43fcf9..43fdb7 confirms the reported scriptmover consumer: wire60 positive,wire6c zero, low11 index,bit800 variant, two XAnim calls and parts-based duration. However, the report's claim that its parts read matches src/xassets/xanims.h is false. At43fd73..43fd77, ebx->tree->anims is followed by [anims+index*8+8]. The retained 32-bit XAnim_s declares debugName0,size4,debugAnimNames8,entries12; u.parts is entry+4, so native parts are at16+index*8. C1 uses a different header shape. Do not cast across them or cite the native layout as proof of client tree compatibility.

The worker's global name scan also selects the first matching entry in any script tree and caches that answer per name. That is not the entity DObj's tree identity, and the same name may occupy different indices in different trees. A successful scan is not proof of a publishable animation. The suggested shared writer additionally reads live per-entity state by entity number and would violate archived snapshot ownership. No proposed animation publication/registration accepted.

Next work must establish the client's DObj tree construction and corresponding server tree/entry mapping, then implement per-state capture and real stop/replay behavior. The absence of a configstring bank does not remove these requirements. No builds/tests/runtime.

## Client DObj construction and tree selector identified

Aligned C1allocator59a800 writes the entity's handle at25d9ed8, allocates a0xc8 DObj and passes its stack argument+10 as the tree to634660. The latter stores that argument to DObj+0 at634703. Six direct-call leads:428d1d,43e730,44372b,443aa4,4504a6,47ca94.

Caller44372b constructs a tree at2627e00 using the result of443540 (stored in local-110). The443540 dispatch table was read as data: eType6,12,14 select4435bb; eType11 selects44355a; eTypes18/20 select443585. For scriptmover6,4435bb reads cent178 (wire94), returns0 when it iszero, otherwise indexes pointer table262799c by that selector. Thus the client's scriptmodel tree is explicitly selected by wire94; animation entry wire60 is relative to that selected tree. Model slotwire98 is a separate field.

450b0f..450b54 initializes table entry0 and surrounding animation registry state, setting2627d9c=0 and2627da8=1; fuller table registration still needs tracing. These are aligned branch/instruction observations; guessed unaligned leading output450ae0 was not used. No animation source publication yet; tree namespace/order and stop/replay semantics remain open. No builds/tests/runtime.

## Client/server tree registries and compact C1 allocation

Aligned5c9f10 loads a selected realm (stack+c), iterates1..count at2627d9c+realm*4 and writes pointers starting26279a0+realm*512. Thus262799c is client-realm table slot0, with the second128-pointer table at2627b9c. Renderer4435bb selects the first table. Native Scr_GetAnims instead reads gScrAnimPub+20c+i*4, the second/server table. Tree IDs cannot be assumed identical merely because a server name resolves.

Loader5ca030..5ca05e obtains an entry count, allocates count*8+4 bytes and stores the count at offset0.5ca0b6..5ca0bd publishes that allocation into its selected realm/index slot. This independently confirms C1 entries begin at4 and their parts union sits at8+index*8, unlike native debug header entries at12. C1 tree IDs are assigned in registration order:5c97ff increments the realm count and5c9817 returns the new index. A server-global first-match name scan neither selects the client's realm nor establishes registration order.

Next: establish client script tree-registration input/order and a name-based correspondence before publishing wire94, then resolve leaf index within that exact tree and capture the pair with entity state. No animation integration accepted; no builds/tests/runtime.
