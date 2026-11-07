# Factory navigation and window-entry review / Factory 导航与窗口入口复核

Status: manual Factory and same-build two-client Nuketown FFA playtests passed on September 20, 2026. Prepared for review; not committed or published. Base: `4e2787aab1951ba314d454fa86804e08448be50a`.

## Behavior and scope

Distant spawn goals could route across a real window without assigning its barrier owner. The movement guard then rejected the window leg and actors circled outside. Assign the first forward map-owned window in the route to the existing barrier controller, and align spawn eligibility with explicit/nearby entrance ownership. Reverse crossings are not adopted. An initial attachment may search up to 256 units only when the existing 128-unit component/capsule-qualified search fails; this does not teleport the actor.

Replace fixed-distance post-window steering with bounded bend-area lookahead and saved-plane progress. [The component review](actor-lookahead-20260917.md) records BO1/Ghosts IDA comparisons, BO2 differences and the exact CODOL collision-consumer identity. This is a reconstructed adapter; the original CODOL server AI controller remains unresolved.

For Factory only, `OLMOD_ZM_NAV_SOURCE=bo1_hybrid` adds BO1 ordinary-walk candidates after CODOL map identity, grounding and body-clearance checks. The default remains `codol_recovered`. Other maps ignore the opt-in. The table supplies 106 shadow nodes and 5,553 candidate walks; these are candidate counts, not a guarantee that every edge is admitted. Seventeen shadow heights are raised using captured walkable-floor evidence. Exact CODOL node coordinates and CODOL-owned barrier/negotiation semantics remain authoritative.

Ordinary stair admission samples support every eight planar units, retains the existing 18-unit step bound and checks body clearance. It is limited to reference-edge admission at map load, not a general runtime shortcut across floors. Missing reference data/validators reject hybrid construction; there is no silent clearance bypass.

## Evidence boundaries

- Native reference facts: BO1 `Path_CalcLookahead` 0x90A120 and Ghosts 0x1400FF410 area selection; BO1 0x90A670 feedback and 0x908820 progress. CODOL `out.exe` SHA256 `044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9` retains trace wrapper 0x46EA60/world trace 0x668220.
- Runtime diagnosis: forward window legs 768->767 and 798->797 were rejected as unowned negotiations. Source correction transfers ownership before that guard. Spawn eligibility previously omitted a mapped entrance because an unconstrained shortest path bypassed it.
- Project policy: bounded lookahead, donor graph admission, first-attachment expansion and window handoff are explicit reconstructed boundaries. They are not newly recovered CODOL server functions. Source audit records are symbol-scoped, not whole-file/native-completeness claims.
- Donor provenance: graph SHA256 `278ca269460db021b79473d4e216bdc56c8e7057447327245e44f7867ef4fc37`; crosswalk `eea5ee3cde1d5208c9a26c0902969f63a7bd0178a505d97c33d3a0fef03a93a4`. Height capture digest and adjustment rules are in `tools/reverse/catalogs/zm_factory_bo1_hybrid_walkable_heights.json`. Raw captures, game binaries and IDBs remain local.
- The checked-in C++ table is sufficient to build. Regeneration with `GenerateBo1HybridNavgraph.py --graph <graph.json> --crosswalk <crosswalk.json> --height-overrides <catalog.json> --output <table.cpp>` additionally requires the matching local extraction inputs; those raw extraction inputs are not distributed by this change.

## Validation

Tested gameplay DLL SHA256: `EA49B947F738749088B92FA882921ED6BD8D834FF549CF428D2DC2CF50C18A9F`.

- Release build, seven canonical repository suites and 50-ms server suite passed.
- Manual Factory playtest passed window behavior and navigation, with the hybrid option enabled.
- Manual two-real-client Nuketown `dm/mp_nuked` playtest passed on the same gameplay DLL. Both real clients reached Playing; individual reciprocal kill/score/respawn assertions were not separately recorded.
- Local sessions used the established offline launch/session adapter. This verifies gameplay under that adapter, not parity with a complete upstream backend deployment.
- Review preparation changes only comments, trailing whitespace and documentation/catalogs after the gameplay tests. Executable C++ tokens are compared against the frozen tested source snapshot.

The portable editor was separately accepted as a workflow check and is excluded from this gameplay change. No earlier build's acceptance is reused. The test infrastructure and raw evidence archives stay outside the contribution.

## Deliberately excluded

Round-gap snapshot namespace correction; native entity synchronization optimization; custom room graph/editor/capture tooling; launcher/account/display changes; new headshot/eye/weapon/perk behavior. Previously merged head attachment and traversal timing remain upstream behavior. Passing these tests is not a claim that the excluded snapshot/performance issues are fixed.

## 中文摘要

本次变更修复窗口入口归属与生成资格不一致造成的窗口外绕圈，并以有界面积前视改善翻越后的路径跟随。Factory 可通过 `OLMOD_ZM_NAV_SOURCE=bo1_hybrid` 启用 BO1 普通行走参考边；默认图不变，每条新增边须通过 CODOL 地图身份、地面支撑及身体碰撞检查，楼梯保留 18 单位步高限制。BO1 数据与重建策略不代表恢复了 CODOL 原版服务端 AI。

同一候选已通过 Factory 窗口/导航人工测试及双真实客户端 Nuketown FFA 人工测试；七个仓库测试套件与 50ms 服务端测试通过。双客户端均进入 Playing；未单独记录双向击杀、分数及重生断言。编辑器及启动工具不包含在本提交中，快照空波次修复、内存检查优化和自定义房间图另行处理。
