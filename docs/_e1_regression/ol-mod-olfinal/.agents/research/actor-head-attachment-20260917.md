# Cyborg head attachment / 生化僵尸头部装配

Status, September 17: accepted isolated increment on merged upstream
`bfbf510ad9646bcb896a1f60dcb22359d45366be`. Exact-candidate Factory head attachment
and two-real-client Nuketown FFA both received human PASS. Historical results
are separate supporting evidence. No movement, eye FX, headshot
or multiplayer protocol changes are included.

## Defect and native evidence

The actor publisher retained the separate head model but forced attachment tag
5 (`j_head`). That tag is a valid bone name, but selecting it changes how the
client combines the head's skeleton with the body. The older Factory comparison
reported floating heads with 5 and correctly attached heads with 0 through
walking, vaulting, death and replacement spawns. This candidate restores 0 and
preserves the selected head model, including the existing no-head case.

IDA 9.3/MCP inspected the exact client `out.exe`, SHA256
`044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9`:

| Consumer | Observed behavior |
|---|---|
| `CG_CopyAgentModelInfo` `0x530C90` | Converts the four model/tag values to strings, stores model strings at record+52+n*64 and tag strings at record+308+n*64, and marks the record dirty on change. Disassembly verifies these accesses. |
| `CG_UpdateAgentDObj` `0x52FBE0` | Resolves each attachment model and the accompanying tag string; writes the string ID into the model descriptor's bone-name field. Passes descriptors to `0x66BE00`, then `0x781960`. |
| `DObjCreateDuplicateParts` `0x781110` | For a noninitial model, zero string ID **or an empty string** enters shared-bone-name matching and builds duplicate-part mappings against preceding models. A nonempty name instead searches for an explicit parent bone. Thus empty tag does not mean an unbound model. |
| `0x7816E0` | Uses the resulting model hierarchy in subsequent DObj setup. No layout or executable patch is introduced by this fix. |

The immediate defect is choosing the named-parent path for the rigged head.
An additional head-parent transform explains the offset seen in the old runtime
comparison; its exact magnitude was not measured in this IDA pass. No original
server head-selection controller or model-family probability is claimed.

## Required reference comparison

BO1 Windows x86 server `DObjCreateDuplicateParts` `0x7E4210` explicitly tests
`boneName && *SL_ConvertToString(...)`: the named case finds a parent bone; the
empty case iterates the model's local bone names and produces duplicate mappings.
Its root-meld assertions and 160-bone limit are reference-specific.

Ghosts PS4 x64 server `DObjCreateDuplicateParts` `0x140247490` has the same
named-versus-empty split, with different structure sizes, bone limits and model
hierarchy handling. Existing IDA types include misleading unrelated names in
some Ghosts pseudocode; those names are not adopted. The relevant branch and
XModelGetBoneIndex calls agree with CODOL/BO1. No foreign ABI, offsets, bone
limits or assembly implementation is copied. No BO2 tie-break was needed for
this narrow semantic agreement.

Canonical input provenance remains in local `ida-research-20260917/input-manifest.json`.
Native evidence is in its `evidence/head-*` directories. Initial full-code
exports failed because py_eval disallows non-IDA imports; corrected IDA-only
exports completed and preserve the full relevant pseudocode. Failed output is
not counted as successful evidence. Confirmed CODOL names/comments are saved
to the canonical IDB and `tools/reverse/annotations/out.exe.json`.

## Scope and verification

Only the zombie agent attachment-tag constant/publication is changed. Player
attachment state and shared netfield serialization remain intact. The existing
actor-slot regression now publishes both separate-head and no-head actors,
checks the chosen model is preserved, and checks both tag slots remain zero.
This checks the production publisher, not a second implementation of DObj.

Before acceptance, verify Factory heads across clothing variants during walk,
barrier tearing, both traversals, attacks, death and replacement spawn; verify
the already accepted traversal timing remains correct. Then repeat the exact
candidate in two-real-client `dm` on `mp_nuked`, recording human results and
which combat/respawn observations were actually completed. Keep the deferred
movement tuning and glowing eyes separate to make any regression attributable.

Exact-candidate human result, September 17: **Factory head attachment PASS**.
The user reported, “Heads are attached to the bodies now. Great!” on candidate
`K-ida-head-attachment`, DLL
`C894A6B9AFE5F07307D0944D09F78A71935D99E6BC5CC972887F3EF9CB22469D`.
This accepts the visible attachment fix; it does not assert that every animation
and clothing combination in the suggested checklist was separately inspected.
Release, all seven canonical suites and the 50ms server suite passed. The function
matrix validates 38 entries; the source audit retains seven inherited findings
and introduces none. Two real clients reached Playing in `dm/mp_nuked` on the
same DLL during setup. After the two-client playtest, the user reported **“Pass!”**.
The latest self-service run `run-177052953` also recorded both slots Playing (2),
health 100 and team 0, with separate accounts/classes. This is a human FFA-mode
PASS; individual reciprocal kill, score and respawn assertions were not reported
separately or automatically asserted. No combat PASS is inferred from startup
alone. The user-operated two-mode gate supplements all repository
automated checks. Local launch adapters/artifacts remain outside this contribution.

## 中文摘要

当前是基于已合并 `bfbf510` 的独立修复。9 月 17 日用户确认本候选 Factory
头部附着正确（PASS），并在双真实客户端 `dm/mp_nuked` 复测后回复 “Pass!”。
不代表检查过全部服装与动画组合；双向击杀、计分和重生未逐项报告或自动断言。
最新自助启动记录确认两个玩家均为 Playing、生命值 100、team 0，使用独立账号
及配置。自动化启动证据与人工模式验收分别记录，旧版 PASS 不转移到此修复。

问题是僵尸头部已有独立骨架模型，但发布端强制使用 `j_head`（tag 5）作为父骨骼。
IDA 核对 CODOL `0x530C90 -> 0x52FBE0 -> 0x66BE00 -> 0x781960 -> 0x781110`
确认：空 tag 通过同名骨骼建立 duplicate-part 映射；非空 tag 则指定额外父骨骼。
BO1 `0x7E4210` 与 Ghosts `0x140247490` 支持这一区别。恢复 tag 0，保留所选
头部模型，不修改玩家 netfield、移动、眼睛 FX 或爆头逻辑；不复制参考库的 ABI/layout。
测试使用实际 actor snapshot 发布路径覆盖有独立头部与无头部附件两种情况。
