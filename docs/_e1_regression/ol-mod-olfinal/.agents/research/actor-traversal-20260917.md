# Actor traversal and supported movement: IDA review

Status: September 17, 2026 accepted contribution candidate on upstream `18928325`.
Human retest confirmed that the perch animation returned and frozen sliding was
gone. The preceding blend-only candidate failed; its native blend findings remain
valid. This snapshot distinguishes native evidence from reconstructed policy.

## Reproduced failure

Run `156634250` logged 19 window starts, all alias 691/v6. Every completed crossing
took 1500 ms. The exact CODOL asset has 34 frames at 30 Hz: 1133.33 ms. The old
movement curve was derived from a different v7 demo crossing. Thus the server
continued moving the actor after its nonlooping animation had ended. Blending
cannot repair this clock/curve mismatch.

IDA confirms `out.exe` leaf updater `0x786E70` multiplies elapsed time by the
leaf's rate and asset frequency, then clamps nonlooping time near 1 and finally
at 1. It does not stretch a clip to the reconstructed server's 1500 ms timer.
This explains the reported frozen-pose slide without assuming a renderer fault.

## Native references inspected with IDA 9.3

| Responsibility | CODOL evidence | Reference evidence |
|---|---|---|
| Animation duration | Exact asset frequency/frame data; leaf updater `0x786E70` | BO1 `XAnimGetLength` `0x7ED5C0`; Ghosts `0x14024F070`; BO2 `0x7B18D0`: frames divided by framerate |
| Root movement | Hashed v6/v7 CODOL translation tracks; original Factory demos | BO1 `XAnimGetAbsDelta` `0x7F25B0`, `Actor_GetAnimDeltas` `0x900290`; Ghosts `XAnimGetAbsDelta` `0x14024EBE0` |
| Traversal lifetime | Original type2/flags3 commands and subsequent walking; original server owner missing | BO1 `Actor_Negotiation_Think` `0x910780`; BO2 `0x895A80`: retain negotiation while animation script lives, then clear motion/recalculate path/pop state |
| Grounded movement | Current `EngineBindings` trace wrapper `0x46EA60`, world trace `0x668220`, checked in decompilation and disassembly | BO1 `Actor_Physics_1` `0x912E40` and ground trace `0x9151C0`; Ghosts `G_StepSlideMove` `0x140164B70`; BO2 `AIPhys_StepSlideMove` `0x899FA0` |
| Turning | Current server owns body yaw; original CODOL controller absent | BO1 `CalcYaw` `0x910FF0` integrates angular velocity. Our bounded-turn helper is simpler and remains authored |

The reference algorithms differ. BO1 separates ground, air, no-gravity and
no-clip motion; Ghosts exposes a generic traced step/slide path in the supplied
server; no identically named Actor_Physics was found in its symbol search. BO2
was inspected to investigate that difference. Its step-function pseudocode has
a local-allocation warning, so it is not a trustworthy layout/prototype source;
disassembly is retained separately. No BO2/Ghosts structures or ABI are imported.
No matching original CODOL server controller is claimed.

Exact input hashes and canonical database paths are recorded in the adjacent
blend review and the local `ida-research-20260917/input-manifest.json`. BO2's
additional `CoDMPServer_PC.exe` SHA-256 is
`ecede1035e091aaf45f358f5d7f73aa90f2a747027a13bf9906699d1121736cc`.
Raw IDA results remain outside Git under that folder's `evidence` directory.

## Restored implementation and explicit boundaries

- Keep each clip's own translation track and duration: v6 1133.33 ms, v7 1400 ms.
  The source tracks come from `common_gametype_zm.ff` SHA-256
  `7f49272825482e466f2782910aa2ee97e4b777ad36a528d7d7be5ae30c06b7c0`;
  decoded corpus SHA-256
  `c6f361930ccb1e71e411524841f204555c9756e8368af5c31c3205c3d7ca57ea`.
- Resolve both variants by name. Actor/generation alternation is a reproducible
  test policy, **not** the recovered original selection probability. Original
  player demos contain both variants; this is not evidence from our own tests.
- Align and face the window before tearing, retain crossing ownership until
  measured landing, then re-anchor pursuit at the landed actor. The 300 deg/s
  yaw bound and 90 units/s settlement are authored compatibility policies.
- Ordinary walking requires support. Unsupported drops need a distinct movement
  owner; a waypoint tolerance cannot authorize walking in midair. The retry
  qualifies up/across/down against native collision instead of ignoring
  startSolid. Its skin, probe depth and controller hull remain explicit project
  policy; this is not a port of complete Actor_Physics.
- Preserve the existing snapshot, barrier and entity ownership. The warehouse
  connector, head attachments, perks, and independent round-gap fix are excluded.

## Validation boundary

The seven restored source/test files match the accepted movement implementation
apart from new evidence comments and the existing IDA-reviewed blend comment.
Existing regressions cover the two root curves, durations, short-turn behavior,
ground/ceiling admission and unsupported negotiation edges. Live checks must also
confirm both variants exit, return to walking, and repeat for replacement actors.
Automated root/route checks are not proof of human animation feel.

Release build, all seven canonical suites, and the server suite with 50 ms ticks
passed. The function matrix validates 37 entries. Source audit has seven inherited
errors and zero new errors; this is not a clean full-source audit.

An offline Factory run entered through the normal menus completed 15 of 15 natural
crossings at all four starting windows, including replacement actors: nine v6
crossings at 1200 ms and six v7 crossings at 1400 ms with 100 ms server ticks.
No forced animation, actor warp or demo replay was used. A saved close-up records
v6 crossing into walking; the separate human retest confirmed the perch and the
absence of frozen sliding. Later crowded rounds and full-map navigation were not
qualified by this run. Floating heads remain an inherited, separate issue.

### Two-client multiplayer regression — September 17

The unchanged gameplay commit `8c10d82da07c1dfebd9bd7b02049088a9d221174`
also ran two real, separately authenticated clients in the same offline
`dm` session on `mp_nuked`. Both slots reached `gameplay_state=2` (Playing),
health 100 and team 0. Each client's snapshot projection contained both players:
`player_entity_mask=3`, `client_info_mask=3`. The user inspected the run and
reported: "Everything looks launched correctly now, and the functionality looks
fine here." **Human result: PASS for this mode's launch and observed functionality.**

The local test launcher retained the existing restricted, windowed host route.
Each client used Charge -> bottom Nuketown -> Start Matching -> Start, followed
by independent native loadout capture and one existing local `SessionStart`
submission containing both authenticated players, explicit `dm`/`mp_nuked`,
score limit 30 and time limit 10 minutes. This authored session adapter is not
evidence of a completely native shared-lobby roster flow. The local launcher and
account-table changes are outside this contribution; gameplay files were unchanged.

Automated reciprocal damage, kill attribution and respawn cycles were **not
completed** and are not claimed as individually verified. This is a scoped
multiplayer smoke test, not exhaustive compatibility or long-soak coverage.
Repeat two-client multiplayer validation on each future zombie candidate and
record omitted observations explicitly. Local run `run-163364671` evidence is
archived in `ida-research-20260917/ffa-regression/accepted-run-163364671/`;
the repeat procedure is `ffa-regression/REPEAT-TWO-CLIENT-TEST.md`. Runtime logs,
account data, launcher binaries and screenshots remain outside Git.

同一未修改的 gameplay 提交 `8c10d82` 已在离线 `mp_nuked` / `dm` 中运行两个
真实、独立认证的客户端。两端均进入 Playing（2），生命值 100、team 0，
snapshot 的 player/client-info mask 均为 3。用户检查后确认启动与所见功能正常，
本模式人工冒烟测试 **PASS**。两端分别通过原生菜单进入，再以各自原生 loadout
通过现有本地 SessionStart 接口提交双人会话；该适配流程不代表完全恢复原生共享
lobby。诊断 launcher 与账号表不属于本提交，gameplay 源码未改变。自动化双向
伤害、击杀归属和重生循环尚未完成，不能将其列为逐项通过，也不宣称穷尽 MP 兼容性。

Tested plugin SHA-256:
`B1F8B9179420B1444C4880A63BF632642C60C1A3D581539DADEBA19A8DDC70D7`.
The audit records these helpers as partial symbol coverage, not a complete review
of `stepActorEntities` or the original AI. The previous PR remains withdrawn;
this candidate is submitted as PR #2, with the scoped multiplayer result above.
