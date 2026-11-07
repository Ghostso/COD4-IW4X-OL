# Factory sliding-door motion / Factory 滑动门运动

Status: candidate on f81f0b3. Factory door-opening playtest passed; same-build two-client FFA passed. Accepted for a scoped commit; not published. Staircase debris remains a separate unresolved model-animation path.

The existing openMapTargetGroup deactivated every brush/model in a purchased target group. Original Factory player recordings instead retain the visible sliding brushes and publish timed positional trajectories. Thirteen brush identities have observed acceleration (type7,250ms), linear-stop (type3,500ms), deceleration (type8,250ms), then stationary (type0) states. The candidate retains those measured phase bases/deltas and rebases the epochs to purchase time. It does not replay actors, player inputs or demo sessions.

Exact CODOL out.exe SHA256 044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9 was opened using IDA Professional 9.3 through ida-multi-mcp; analysis settled at 35,783 functions. Decompilation of 0x410BD0 confirms type7 quadratic acceleration at 0x410D38, type3 duration-clamped linear motion at 0x410C88, and type8 quadratic deceleration at 0x410DBA. Production uses the existing EngineBindings evaluator; no native calling convention or wire layout changes.

Motion records come from the original C-2021-7-31[15-32-16]zm recording, decoded before this increment. The selected records retain observed brush identity and original map fields. Raw records, decoder provenance, phase extraction and fresh IDA output remain in the local evidence archive. Snapshot quantization is retained in phase bases. The apparent displacement differs from script_vector alone, so copying the BO1 script vector formula would not reproduce these recordings.

BO1 common_zombie_patch/maps/_zombiemode_blockers.gsc door_activate is a reference: move/slide_apart use MoveTo with quarter-time acceleration/deceleration; clip blockers and physics/animated debris are separate branches. It is not authority for CODOL displacement or collision timing. Ghosts controller equivalence has not been established and is not claimed.

The candidate is limited by exact Factory map/brush/target/origin identity. Native brush and player layouts are unchanged; generation-qualified motion ownership is stored separately from WorldClientState. Purchase stages the entire group and starts motion only after native publication succeeds. An unavailable evaluator refuses the transaction without charge. Repeated activation is refused. Motion updates stop after settlement, avoiding permanent per-door native relinking.

Remaining boundaries: simultaneous group start preserves the existing transaction but does not reproduce the recording's small stagger between paired leaves. Nonmoving clip/model handling remains the previous behavior, so original clip release timing is not claimed recovered. Audio cues, physics debris, repair rewards/timing, corpse collision, actor overlap and hit effects are not included. Factory door-opening acceptance is recorded; this is not a separate exhaustive collision certification. Same-build two-client FFA playtest passed. Both clients reached Playing; individual combat assertions were not separately instrumented.

当前候选恢复十三个已测滑动门刷体的四阶段轨迹，保持门可见并更新其碰撞位置。原生轨迹求值依据当前 CODOL 的 IDA 证据；成对门的启动间隔及独立 clip 的释放时序尚未恢复。楼梯杂物、音效、修板、尸体碰撞及命中特效不在本次候选中，Factory 开门实测通过；同构建双客户端 FFA 实测通过。

## Validation / 验证

Gameplay DLL SHA256: F6821D7A2E1FF9667B75D20BB79F67472973EFD59A186A3E4075D5982B437E6B.

- Release build, seven canonical suites and 50-ms server suite passed.
- Focused synthetic tests verify exact map/brush/target/origin qualification, elapsed phase selection including a skipped frame, atomic refusal without an evaluator, retained brush visibility/identity, duplicate activation rejection and final settlement. The synthetic evaluator is not evidence of native physics fidelity.
- Factory door-opening playtest passed on this DLL. Stair debris and paired-leaf staggering are not covered by that acceptance.
- Same-build two-real-client Nuketown FFA: passed. Both clients reached Playing; individual combat assertions were not separately instrumented. No earlier build's result is reused.
- The native-adjacent WorldClientState size guard remains unchanged; motion ownership is outside its layout.

构建、七个仓库测试套件及 50ms 测试通过。结构测试与原生求值证据分开记录；Factory 开门实测通过，双客户端 FFA 实测通过。
