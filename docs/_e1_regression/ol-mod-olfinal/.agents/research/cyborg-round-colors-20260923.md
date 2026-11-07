# Round-selected cyborg body colors

Status: accepted BA candidate on2835f93. Factory and exact-build two-client FFA playtests PASS.

## Native evidence

Exact out.exe SHA256
`044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9`.
IDA MCP instanceeeah: analysis idle,35783functions. Retained decompilation of
CG_CopyAgentModelInfo0x530C90:0x530D37 resolves agent+0x0C through model
configstrings+2568;0x530D48..0x530D86 detects name changes and dirties the DObj.
CG_UpdateAgentDObj0x52FBE0 composes the body and shared-bone attachments. This
supports selecting resident native model aliases, not inventing tint netfields.
It does not reveal the deleted server's round/color selector.

Five original player recordings contain46664 exact decoded snapshots. Resident
body aliases were checked against25 independently saved aliases. Initial intact
bodies with a known round produce this census:

| Rounds | Body suffix | Observations |
|---|---|---:|
|1–4|`_body_blue`|345|
|5–8|`_body_yel`|1048|
|9|`_body_orange`|232|

All1625 classified observations match;49 before the first known round command
are excluded. Three Factory recordings plus Sumpf and Prototype are included.
No same-observed-life intact-body color swap was found. The rule applies to
initial bodies; damaged meshes and eye/material-only effects are separate.
The complete native late-round bands, special-enemy rules and outfit odds remain
unknown. The July31 Factory source hash is
`a8c461be9b8544eb041e95b37a4054a999642b34469cc3b0dda64d55fe2d4a97`.
Local evidence: score-color-census.json, full-corpus source/hash records,
analyze-score-color-evidence.py and score-light-ida decompilations. Native
recordings and IDBs are excluded from the contribution.

## Implementation and reconstruction boundaries

The existing validated `zmsetround` call updates world-owned presentation round
alongside its HUD announcement. Reset starts at1. No second director or timer.
Factory's opt-in presentation loader annotates each resolved matched body/head
pair with explicit color metadata. Spawn selection first filters by round color,
then uses the existing equal clothing cycle within that color. Missing families
do not select another color or another family's head.

R10+ holds orange as a documented fallback beyond the recording coverage.
If an entire requested phase is absent, use resolved blue pairs; unannotated
callers retain their prior cycle, and empty pools retain the caller pair.
These are compatibility policies, not recovered native missing-asset behavior.
Only new spawns change: no live recolor, corpse mutation, new eye FX, damage,
death eligibility, movement or per-frame asset lookup. Runtime remains Factory
presentation-scoped. No MP client/network layout is changed.

## Verification

Seven canonical suites,50ms server regression,Release build and source audit
passed. Regression covers phase boundaries, missing/reordered variants, independent
matched clothing, actual script-to-spawn ownership, invalid-round rejection,
reset and unchanged pre-existing actor models. Existing presentation/death and
multiplayer suites remain required. Factory test: all early-round intact bodies
blue with clothing variety; round5 new bodies yellow; round9 orange if reached.
Headless walking and death/body FX retain their existing paths. Factory and same-build
two-client Nuketown FFA playtests passed on DLL
`79BDD8FAB2216675A13883DD0183C5521C28226174FEA4539408D733B9F59BEC`.
Both FFA clients reached Playing; individual reciprocal kill/score/respawn
assertions were not instrumented. Gameplay source matches the tested package.

## 中文摘要

五份原始录像中的1625个已知回合初始完整身体均符合：1–4回合蓝色、5–8黄色、
9橙色。IDA确认身体配置字符串由原生DObj消费者使用；未恢复原服务端选择器。
服装与颜色分离，沿用Lua回合归属，仅影响新生成个体。10回合以后保留橙色及资源
缺失回退为明确重建策略。不宣称恢复全局眼光切换；Factory及同构建双客户端FFA实测通过；未将人工验收冒充逐项自动战斗断言。
