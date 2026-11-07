# Final status — October 2 / 最终状态

The combined c52b156-based candidate passed Factory travel (solo and two-player)
and exact-build two-client FFA. Earlier named candidate statuses below are
historical investigation records, not the current acceptance state. Debug battery
and initiator-only stopwatch were confirmed in the preceding focused checks;
staged travel and its separate opt-in are documented in
[factory-bo1-travel-20261001.md](factory-bo1-travel-20261001.md).
Keep unobserved native scheduling and final gate clearance labeled reconstruction.
最终整合候选已通过Factory传送及同构建双客户端FFA；下方各版本待验收文字为历史记录。

# October1 CZ recipient correction / CZ秒表接收者修正

CY playtest accepted third-link gate movement/access. That trajectory is unchanged.
CY failed battery aid and expected stopwatch scope. CZ records the initiating
client plus spawn generation on a successful pad link, sends both native clock
elements only to that same player/life, and clears ownership on completion,
expiry or match reset. A rejected competing start cannot steal the clock; a retry
has its own initiator. Other living teammates may still finish the shared link.
Recipient restriction is requested reconstruction policy; original single-POV
recordings alone still do not prove visibility for other clients. Tests cover
recipient/life distinction, competing use, retry, completion and reset. Exact CZ
Factory+FFA remain pending; prior PASS is not inherited.
CY第三段门体验收通过且未改动；CZ按连接发起玩家及生命代次限定秒表，两人仍可共同完成
连接。此接收范围为明确重建，非单视角原录制能独立证实的结论；需同构建重新验收。

# October1 CY correction pending / CY修正待验收

CX playtest FAIL: apostrophe did not grant currency and the lower gate panel
remained in the entrance. Its server logged all three completed motion stages;
the failure was insufficient travel, not a missing third-stage request.

Original Factory demo a8c461be9b8544eb041e95b37a4054a999642b34469cc3b0dda64d55fe2d4a97
was decoded through its full12305 snapshots with captured baseline
7246f541bd15a011df0fc688d58551b678cbcfca4e287849c608e4f3b54f4de0.
Entity90 at344250 has type7/time344250/duration1000/baseZ213.5/deltaZ-35;
345250 type3/500/baseZ195.5;345750 stationaryZ178.5. No later gate step occurs.
Factory demos ef3485dc7ebf1883d3ebf93bd282c1ee208b2ceb6821824891607e6411f0205e
(6190 snapshots) and bc1a998b9e9946dfe12ca7f029a6bb42284144991313d8a8680ebb4a8b12a509
(9060 snapshots) likewise supply no final-link descent. Other-map recordings are
excluded. These are original recordings, not reconstructed test captures.

Settled IDA9.3 MCP analysis of CODOL044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9,
410BD0, confirms native types0/3/7. Continuous17.5+17.5 motion avoids reproducing
the demo coordinate quantization's half-unit snap. Repeating steps per link is
reconstruction. CX's three35-unit steps were insufficient: resident model bounds
centerZ=-26.654041/halfHeight=83.732620 put the top at165.578579 after lowering105
from213.5, while the machine/floor reference is114.5.

CY preserves the recorded first step and a matching second step. The final step
keeps acceleration1s and speed35 but extends the linear stage to2.5s, lowering105
(175 total), ending atZ38.5 with model top95.578579. This clearance endpoint and
final duration are explicitly reconstructed, NOT native demo values. Collision
is released only after the full3.5s final motion; the model remains visible.
Tests cover smooth phases, full-model floor clearance, generation ownership,
native-evaluator refusal/rollback, wire serialization and multiplayer exclusion.

Stopwatch recipient scope remains UNKNOWN: the recorded POV cannot establish
other recipients. CZ supersedes team-wide display with initiating-player scope. CY Factory and exact
two-client FFA acceptance are pending; older PASS results do not transfer.

CX实测失败：电池键无效，下部门板未完全下降。原录制仅证实首次下降35单位；
完整三份Factory录制均未提供最终开启段。CY依据模型包围盒延长第三段以清空入口，
最终距离与时长为明确重建，非原版已证实值。秒表接收范围仍未知；需同构建双模式验收。

# Upstream integration pending fresh acceptance / 上游整合待重新验收

Current base: c52b15608a46b72b794658e6405916bf24fbdc5c, Eden's
Restore complete dual-wield behavior. The CV teleporter/revive patch applied
cleanly in this separate checkout. Original CV source and frozen build are preserved.
CV's Factory and two-client FFA PASS belong to the older 927cfd3 base only.
The combined candidate requires new Factory and two-real-client FFA acceptance,
including paired-weapon fire/reload and selected-loadout checks where available.
Nothing is committed or pushed. Native evidence and reconstruction limits remain
in the teleporter research review; integration does not add new native evidence.

已基于上游c52b156整合；旧CV验收仅适用于927cfd3基线，不继承为本候选验收。
需重新进行Factory及双客户端FFA测试，保留原候选；尚未提交或推送。

# Factory teleporter linking / Factory传送器连接

Status: frozen CV Factory teleporter and damage-enabled cooperative revival
playtests PASS; same-build two-real-client Nuketown FFA PASS. Seven suites,
Release,50ms and partial source audit214 pass.315 source/asset/test files match
the accepted freeze. No commit/push yet. This is reconstruction with specific
native evidence, not a recovered original server controller. Stopwatch visuals
and intermediate-link FX remain without separate explicit visual confirmation.
状态：同构建传送、伤害开启救援与双客户端FFA实测通过；秒表外观与中途连接特效
尚未单独确认。保留原生证据与重建策略区别，不宣称恢复了完整原服脚本。

`OLMOD_FACTORY_TELEPORTERS=1` plus the existing interactables opt-in enables
this owner only for `zm/zm_factory_sh`. Actual weapon upgrading is excluded.

## Evidence and limits

CU live failure correction: the retained original exception context identifies an
access violation atCODOL7BDD4D, reading address4. The laterC3F48C invalid-CRT sink
belongs to the crash reporter and is not the originating fault. Settled IDAqnti
35783 confirms7BDCE0 tests player eFlags100000, follows the locked entity at+1FC
and dereferences its mapped asset. Although593F40 also hides viewweapons for this
bit, it is not a standalone hide flag. The prior hide-only interpretation is
withdrawn. CV never adds it; ordinary source flags/inventory are retained. Movement
still uses the verified800 gate. Gun hiding is deferred until its full native
contract is established. Treatment progress/caption now go only to the current
living generation-qualified helper; the victim retains downed presentation.
`OLMOD_ZM_DEBUG_GODMODE=1` is a reconstructed diagnostic, latched only for
zm/zm_factory_sh. It suppresses player damage, pain and last stand while preserving
payload validation and reset/map exclusion. It is off by default and cannot prove
revival acceptance by itself: the accepted CV revival run explicitly disabled it.
CU原始异常来自7BDD4D锁定实体资源读取；100000位不是仅隐藏武器的标志，原解释撤回。
CV保留移动锁定而暂缓武器隐藏；进度条仅发送给救援者。调试无敌不代表救援验收通过。

Clock registration correction: the original Factory gamestate message1 contains
CS5169 zombie_stopwatchneedle,5170 zombie_stopwatch,5171 zombie_stopwatch_glass.
These names are absent from the packaged common_zm material NCS list. The initial
CT implementation looked them up without publishing their dynamic registrations,
so missing names caused the optional HUD producer to omit the clock. CU allocates
the three names transactionally above the current native dynamic-material boundary,
preserves occupied slots and publishes them through the ordinary gamestate.
CODOL514880 reads class>=23 from77D8250 through the parsed string table;457350
resolves material names and563043 appends needle to the clock name. Fresh settled
IDA instanceqnti confirms clock descriptors34/41 at DA9138, offsets80/84,
codecs-97/32. Do not reuse old client descriptor addresses from another build.
The original recording's numerical slots are evidence, not hardcoded runtime IDs.
Missing resident artwork, namespace exhaustion or an unknown native boundary
fails closed and emits one map-load diagnostic. Nothing is searched per frame.
The constant-material guard now permits only the explicitly observed dynamic tail.
Regressions verify real gamestate serialization, occupied-slot preservation,
duplicate reuse, constant rejection, conflicts and rollback on partial exhaustion.

CT playtest receipt: final linking visuals matched the reference video; stopwatch
absent. In-progress effects and reviving were not accepted. This is partial human
evidence, not overall Factory/FFA acceptance. CU was superseded by accepted CV after the crash correction.

Exact CODOL out.exe SHA256:
044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9.
IDA instance0dv5 settled35783 functions before fresh decompilation onSeptember29.
4116F0 projects native playerstate into entity state and derives flags from
movement state. Relocation uses the existing verified converter and rejects
failed native roundtrips before committing position or currency.538B70 case2
renders a Value HUD element from+136; the initial digital countdown has now been replaced by the native clock described below.
6C8500/6C87A0 own myTeleportKeyHint/myTeleportCDTimer and ui_td_teleport_notify.
These do NOT establish Factory's pad/core script and are not reused blindly.

Factory map records identify core trigger38, pad0/1/2 triggers39/41/40, four
origin_teleport_player landing points with yaw270, pack_door and pack_door_clip.
Original July31 Factory recording publishes POWER_UP_TPAD/INACTIVE_TPAD at173250,
LINK_TPAD at317150, TELEPORT_COOLDOWN at351550 and TELEPORT_TO_CORE with literal1.5
at356550. The current Factory battery unit is1200 raw. Charging1800 for that
displayed price is an inference; this sample does not independently prove a debit.
Asset names fx_transporter_pad_start, fx_transporter_beam and mainframe link
single/all exist in Factory's native effect table. Their placement/schedule in
this adapter is reconstructed and awaits visual validation.

Correction to the historical September25 local investigation: differences between
widely spaced retained playerstates do not prove a teleport. A fresh decode also
revealed alternating retained player positions, so that sequence is NOT reliable
evidence for a2.2second transport delay or for preserving specific teleport flags.
The new implementation makes neither claim. Original HUD has a timed link-related
element, but its precise producer timer has not been recovered.

## Reconstructed controller

Power must be on. Starting an unlinked pad opens one shared30second transaction;
any living, standing teammate can complete it at the mainframe. Other pads cannot
replace the pending link. Expiry clears it without charging. Linked travel charges
the activating player1.5batteries and returns that player to an unoccupied authored
core landing, with current life, weapons, ammunition and perks preserved. Unsafe
landings, downed/dead clients and insufficient funds refuse without mutation.
Travel is currently immediate with bounded native emitters and a shared5second
cooldown. Group transport, intermediate-room/camera choreography, sounds and
original cooldown duration are not recovered in this increment.

Each distinct completed link schedules a downward35-unit gate step over1500ms;
only the third completed movement releases its paired collision brush. The
recorded step uses1000ms acceleration (type7,-35u/s), then500ms linear-stop
(type3,-35u/s), then stationary. Repetition per link is reconstruction. The older
+100Z opening claim was wrong: the early21300 move raises50units before linking;
the344250 link-completion movement lowers35units. CX corrects that interpretation.
Wire trajectories retain their original base/time while the native410BD0 evaluator
updates the current pose for collision/native mirroring. Static frame-by-frame
origin writes are no longer used for this gate. No PAP
weapon transformation or upgrade price is added. Source state resets on configure;
no native structs/netfields are expanded. FX carriers are generation-owned,
limited to16 and freed after5seconds. No per-frame asset resolution.

## Validation

Focused machine regressions cover exclusive link ownership, teammate-neutral
completion, timeout boundary, duplicate completion, all-three requirement, cooldown
and match reset. World tests cover stale lives, insufficient funds, invalid/blocked
destinations, native projection and retained inventory/perks. Synthetic fixtures
are not original gameplay evidence. The first clear-destination fixture failed
because it supplied no collision callback; an explicit blocked/clear trace now
tests both cases without weakening the production guard.

Accepted playtests cover Factory teleporters, the focused damage-enabled revival retest, and two-real-client Nuketown FFA. Tests do not establish all native timing details, every blocked-arrival edge case, or long-session stability.

候选默认关闭。地图触发器、原生提示、资源名和客户端消费者有证据；30秒连接、
5秒冷却、队友完成连接、特效调度及三链接开门为明确重建。旧位置样本不足以证明
传送时间，已撤回该推断。此次只恢复连接、单人回传和升级机通路，不包含武器升级。
Factory传送、伤害开启的救援与同构建双客户端FFA实测已通过，不继承旧版本PASS。

## Stopwatch, powered machine presentation and treatment hold

Original C-2021-7-31[15-32-16]zm.demo SHA256
a8c461be9b8544eb041e95b37a4054a999642b34469cc3b0dda64d55fe2d4a97:
12,305 exact decoded snapshots. At317150 current HUD slot4 is type12,
material298 zombie_stopwatch, 96x96 at(10,20), alignment11, deadline348100
at native+80 and dial period60000 at+84. Slot6 is the matching type5 glass
material299, sort3 versus face sort2. Needle297 is zombie_stopwatchneedle.
Alpha clears at344250. A second clock at1150350 has deadline1181300.
CODOL IDA563043 clock cases12/13 load the face and append needle;538300
computes nonnegative deadline minus server time. Existing HUD descriptors34
and41 carry the deadline and dial period; no native structure/netfield expansion.
The adapter reuses source-side scale fields with clock-specific serialization;
ordinary icon/text serialization remains unchanged. Missing artwork fails closed.
The transaction remains reconstructed30seconds; native sample has approximately
31seconds remaining at its first captured clock. No tick sound is claimed.

In the same recording, Factory machine entity568 receives sound event3/alias59
at177150 (CS3684 zmb_perks_packa_loop), then four event113 records at180150,
parameters3788/2764/3276/2252: effect204, bones7/5/6/4. The common-zombies
FX prefix is calibrated at122 from preserved runtime name evidence, placing204
at misc/fx_zombie_cola_on_blue_glow. The packed ON model has eight bones;
its 360-byte header is followed by script-string bone IDs. Named attachments
4..7 are tag_on_glow_left, tag_on_glow_left1, tag_on_glow_right,
tag_on_glow_right1. Resolve current runtime names instead of hardcoding indices.
These events follow power at173250, well before the link clock. The candidate
uses the ON model and hum after approximately4seconds, then four tagged glows
3seconds later. Initial delay and model-swap trigger are reconstructed; the
four event parameters and relative sound/glow timing are recorded evidence.
No new per-frame asset search, no extra persistent entity, one sequence per map.
The Factory-level FX index base was not proven by this sample; do not infer
absence or exact timing of final-link effects from guessed level indices.

Reviving helper movement presentation is a reconstructed producer built on the
verified CODOL41CB40 pm_flags0x800 consumer. The initial593F40-only hide flag
interpretation was unsafe and is withdrawn by the live crash/7BDCE0 evidence
above. The adapter qualifies the helper by life generation, fresh Use,
reach/LOS, match state and the downed target. It neutralizes only the local
Pmove command copy, preserving the accepted raw Use command for treatment.
Native Pmove sees a temporary freeze; the source flag is removed afterward
only if this operation added it. Snapshot presentation retains source entity
flags and inventory/ammo; it does not yet hide the gun. Release, obstruction,
completion or invalidation drops the owner. The referenced videos do not independently prove this flag producer;
the original revive samples inspected so far are not verified helper POV.

Fresh decompilation used settled CODOL instance0dv5 and the binary hash above.
Local evidence artifacts, binaries and IDBs remain outside this contribution.
Earlier tentative packed-model parsing (inline LOD name) and FX prefix127
were rejected; corrected model-header and calibrated common-FX evidence are used.
The supplied video final-link segment remains unverified here, so exact electrical
effect timing remains reconstructed. Final-link visuals were accepted against the reference video; intermediate-link effects remain unproven.

Validation: clock layout/serialization and clock-to-icon clearing, revive hold
ownership/cancellation/inventory retention, stale sound/FX entity rejection and
registered sound emission are covered by source regressions. Factory teleporter, damage-enabled revival and exact-build FFA
acceptance for this combined candidate are PASS; visual uncertainties remain as noted above.

原生录像确认秒表材质/指针、升级机通电后的循环音与四处蓝光。倒计时通过现有
HUD字段传输，不扩展原生协议。救援者冻结使用已验证客户端消费者；武器隐藏暂缓，
触发逻辑、初始延迟和连接特效调度仍明确标记为重建；本次同构建实测结果见上。

Regression correction: the first machine-sound wire test failed because ET6 validation admitted tagged FX only. Original Factory entity568 proves sound event3 here. Admission now includes only valid nonzero native sound indices; the actual packet serializer test, seven suites,50ms and Release pass. No human result inferred.
