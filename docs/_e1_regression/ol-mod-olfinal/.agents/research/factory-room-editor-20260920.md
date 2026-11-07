# Editable Factory room navigation / Factory 房间导航编辑

Status: reviewed and accepted for integration after same-build Factory and FFA verification. Base: 1599bf4bd1966354f1c8ad30f4b89ccaa1b99859.

## Scope

Add a portable offline graph editor, a deterministic export compiler and the first authored Factory teleporter-room graph. The room corrects ordinary walk topology where the BO1 reference geometry differs from CODOL. This is authored replacement topology, not recovered original CODOL server AI.

Activation requires Factory, OLMOD_ZM_NAV_SOURCE=bo1_hybrid and OLMOD_FACTORY_ROOM_DRAFT=1. The default graph is unchanged. Remove the room variable to disable it. The compiled room requires the expected 1,206-node hybrid base; it is not a general importer for other maps or future base layouts.

Admission copies the graph, projects authored probe positions onto nearby floor, and validates ordinary links in both directions through existing CODOL trace-backed support/body checks. Required ports must pass. Only completely isolated non-port proposals may be omitted; disconnected linked sections reject the complete edit. Rejection preserves the previous graph. Existing crossing edges can reconnect only to nearby, same-floor, collision-qualified points; unrelated rooms do not acquire proximity links.

Native node IDs and existing barrier/negotiation metadata remain unchanged. Two short window landing connectors use the existing compact supported-landing policy, bounded to 32 planar units and the two explicit window ports; this is narrower than the ordinary body hull and is a project policy, not proof of native controller equivalence. No new jump owner is assigned to local:372/396. Local:409 retains an ordinary route and is not declared a recovered window.

## Evidence

The exact CODOL out.exe SHA256 is 044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9. Existing IDA evidence for trace wrapper 0x46EA60/world trace 0x668220 and BO1/Ghosts path references is recorded in [navigation review](navigation-increment-20260920.md) and [lookahead review](actor-lookahead-20260917.md). Those native consumers are reused, not modified or newly decompiled for this room. Graph placement, bindings, clearance thresholds and atomic admission are explicitly reconstructed project boundaries.

The included editable source compiles to 84 connected proposals and 202 links; standalone local:330 is excluded. During the accepted live run, FACTORYROOM applied reported 83 admitted points, 192 accepted authored links, 10 rejected authored links, 48 reconnected boundary edges and isolated local:404 omitted. Required ports remained connected. Earlier rejected imports retained the old graph and do not count as validation of this custom topology.

## Validation

Gameplay DLL SHA256: 4F57440E2E889865EB0573ADAAF68412D311BB371E20BB826A5382B2A2C7FCA0.

- Release build, seven canonical suites and the 50-ms server suite passed.
- Synthetic import checks cover atomic rejection, floor mismatch, retained native IDs/ownership, isolated-point omission and rejection of disconnected linked sections.
- Editor interaction/undo/export checks, deterministic header regeneration and malformed required-window rejection passed. These are structural checks, not substitutes for runtime collision.
- Factory room navigation/window playtest passed after confirmed custom graph admission.
- Same-build two-real-client Nuketown dm/mp_nuked FFA playtest passed. Both slots independently reached Playing with health 100. Individual reciprocal kill/score/respawn assertions were not separately instrumented.
- The local offline session adapter was used. This does not certify an arbitrary backend deployment. Raw logs, launchers, accounts, game binaries and IDBs are excluded.

The offline editor was previously accepted; the integrated compiler has automated structural coverage. A new manual editor export-to-rebuild round trip was not repeated for this candidate. Optional live position reads a selected local log; it cannot prove grounded movement or detect noclip. Import/export alone never installs a graph.

## Limits and rollback

This is one reviewed room with explicit ports and replacement footprint. Other rooms require new bindings and live validation. Cleared ordinary points remain in the native ID space with their ordinary links replaced. No performance, weapons, perks, effects, network serialization or launcher changes are included. Existing multiplayer behavior has a focused regression pass, not an exhaustive guarantee against all regressions.

## 中文摘要

新增可离线使用的导航编辑器、确定性导出编译器及 Factory 传送房间的人工编辑图。仅在 Factory 同时启用 bo1_hybrid 与 OLMOD_FACTORY_ROOM_DRAFT=1 时生效，默认图不变。新增普通路径须通过现有 CODOL 碰撞与地面支撑验证；必要接口失败或已连接区域断开时整体回退，仅允许省略完全孤立的非接口点。保留原节点编号、窗口破板及翻越归属，不宣称恢复原版服务端 AI。

同一 DLL 的 Factory 与双客户端 Nuketown FFA 实测通过，两客户端状态均为 Playing；七个仓库测试套件及 50ms 服务端测试通过。未单独自动断言双向击杀、分数及重生，也未在此候选重复人工编辑器导出到重建流程。现有 IDA 碰撞证据被复用，本次人工拓扑与导入策略明确属于项目边界。移除房间环境变量即可回退。
