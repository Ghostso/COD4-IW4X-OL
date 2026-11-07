# Factory teleporter links and staged return accepted — October 2

Based on upstream c52b156 (complete dual-wield behavior), with no newer upstream
commit at final review. Factory solo and simultaneous two-player staged travel
playtests passed; the same gameplay binary passed two-real-client Nuketown FFA.
Release, seven suites,50ms server regression,223-review partial source audit,
four audit-validator tests and frozen gameplay/source identity checks passed.
Simultaneous travel used explicit debug godmode; that run does not validate damage
or revival. No new long-session performance claim or recovered paid-travel claim.

`OLMOD_FACTORY_TELEPORTERS=1` (with INTERACTABLES) adds shared pad/core linking,
initiator-only native stopwatch, machine power presentation and phased PAP access
gate. `OLMOD_FACTORY_BO1_TELEPORT_TRAVEL=1` separately opts into BO1-derived staged
return travel: charge, per-player effect rooms and safe mainframe arrivals.
The combined change also retains helper-only treatment progress/movement lock and
corrects the loopback-only opt-in battery key to the focused player (default F6).
Read [link evidence](.agents/research/factory-teleporter-links-20260929.md) and
[staged travel evidence](.agents/research/factory-bo1-travel-20261001.md).
Native assets/consumers are distinguished from reconstructed timing/selection.
PAP weapon upgrading and peripheral travel steam/heat-sink choreography remain
outside this contribution. Launchers, binaries, media and IDBs remain excluded.

Factory传送连接与分阶段回传已通过单人、双人以及同构建Nuketown FFA验收。
独立开关启用BO1衍生重建，不声称恢复CODOL原版付费传送脚本；原生消费者与重建
策略分别记录。双人传送使用测试无敌，不冒充伤害/救援验证。升级武器及周边蒸汽效果
尚未包含；自动检查与冻结源码一致性通过，不提交本地启动工具或原生资源。

# Factory cooperative revival and arrival hold accepted — September29

Two-client Factory and exact-build Nuketown FFA playtests passed. Seven suites,
Release,50ms regression, independent T16 wire decode and202-entry partial source
audit passed. Gameplay source matches the tested freeze; final edits are evidence
and documentation. See [revive review](.agents/research/factory-cooperative-revive-20260928.md)
and [arrival evidence](.agents/research/factory-entry-20260923.md).

OLMOD_ZM_COOP_REVIVE=1 enables Factory last stand, held revival, temporary pistol
ammo, native feedback, teammate spectating and team elimination. The existing
OLMOD_FACTORY_ENTRY=1 adds a per-player3100ms initial movement hold. Native wire
and original demo facts are separated from reconstructed timers/selection/loss
choreography. No native player ABI growth or long-session performance fix claimed.
Keep launcher infrastructure, recordings, native binaries and IDBs out of Git.

合作救援与入场锁定通过同构建Factory/双客户端FFA实测及自动检查。原生证据和
重建边界见对应研究文档；不提交本地启动工具与原生资源，不宣称修复长期性能问题。

# Local Factory co-op and held weapons accepted — September27

Two-real-client Factory and same-build Nuketown FFA playtests PASS. Seven suites,
Release,50ms and196-entry partial source audit pass. The accepted gameplay source
is unchanged after testing; final edits record documentation/evidence boundaries.

Shared world/snapshot code now publishes generation-owned ordinary firearm ET6
children through existing native client-info field0. Factory may opt into
`OLMOD_ZM_COOP_SPAWN_ZONES=1` for living-player occupied/open-neighbor zone union.
Install matching zm.lua. Native weapon evidence and reconstructed spawn-policy
limits live in the two September26/27 research documents linked by game_server.md.
Remote admission, special/dual-hand weapon presentation, reconnect/revive and
empty-server lifecycle remain open. Known long-session slowdown is not fixed.
Launchers, recordings, native binaries and IDBs are excluded. No new PR required.

本地双客户端Factory及同构建Nuketown FFA通过；共享手持武器子实体有IDA/demo依据，
合作区域并集刷怪为默认关闭的重建策略。远程、特殊双持、重连/复活及空服生命周期未完成。

# Factory special rewards: accepted combined contribution — September27

Restores opt-in Ray Gun/Wunderwaffe combat, grenade/tactical throws, placed
trap effects, shrinking/contact kills and monkey attraction/animation/song.
Box offers descend before expiry, dynamic box/monkey sounds register safely,
and owner-only Wunderwaffe tube effects follow clip count. Pool weights and
several combat values remain explicit reconstruction policy, not recovered
CODOL odds. See .agents/research/factory-special-rewards-20260926.md.

Factory feature acceptance PASS on frozen CL; same-build two-real-client
Nuketown FFA PASS on the exact candidate. Seven suites, Release,50ms,194-entry partial audit
and independent wire decode pass. A severe Factory slowdown remains open:
late average frame138ms, primarily begin/end phases, already slow before
Tesla equip. No root cause or performance fix established.
Gameplay source matches the tested freeze. Launchers, media and IDBs stay local;
deferred teleporter/Pack-a-Punch and remote-multiplayer work is excluded.

Factory特殊奖品及箱体表现合并：僵尸功能与同构建双客户端FFA验收通过。
原版概率未恢复，权重与部分战斗参数为显式重建策略。Factory帧耗时问题仍未定位，
不得描述为性能修复；传送器、Pack-a-Punch和远程联机工作不包含在本次提交中。

# Factory mystery box accepted — September26

Factory and exact-build two-real-client Nuketown FFA playtests PASS on the
isolated box-only candidate. Release, seven canonical suites, 50ms regression
and the 187-entry partial source-audit validator pass. Gameplay source is
unchanged since acceptance; final changes only record evidence and scope.

`OLMOD_FACTORY_INTERACTABLES=1` enables Factory's mystery-box lifecycle,
native presentation and atomic claims. Read
[.agents/research/factory-interactables-20260925.md](.agents/research/factory-interactables-20260925.md)
for evidence and reconstruction limits. The temporary pool remains ordinary
published class-derived firearms plus Max Ammo. Teleporters, Pack-a-Punch,
upgrade registration and experimental special-reward combat are excluded and
preserved separately. Keep launchers, recordings, binaries and IDBs local.

缩小范围后的神秘箱构建已通过Factory与同构建双客户端FFA人工验收，以及Release、
七项套件、50ms回归和187项局部证据索引检查。临时奖池仍为普通枪械与最大弹药；
传送器、PAP及特殊奖品战斗独立保留，不进入本次贡献。原生证据与重建边界见链接。

# Factory perks, ammo and battery HUD accepted — September25

Factory and same-build two-client Nuketown FFA playtests PASS. Seven suites,
Release,50ms regression and source audit171 PASS. Exact candidate gameplay
sources unchanged after acceptance; local launcher/account/display overlay restored.
Read .agents/research/factory-perk-machines-20260924.md,
factory-ammo-rate-20260924.md, factory-battery-hud-20260925.md and
factory-debug-battery-20260924.md for evidence and limitations.

OLMOD_FACTORY_PERK_MACHINES=1 enables the Factory purchases and native modifiers;
ammo uses two-second hold and refills firearm magazines/reserves. Guarded client
HUD conversion restores1200raw=1Factory battery without changing raw prices.
Optional local Numpad+ aid requires OLMOD_ZM_DEBUG_BATTERY=1. Ownership prices
2/3/4 are recorded; fourth5 extrapolated. Cooperative revival/drink sequence,
equipment/akimbo refill and wonder-weapon ammo exclusion remain incomplete.
Next: combined mystery box, teleporters and Pack-a-Punch. User owns menus.

Factory及同构建双客户端FFA、七项套件、Release、50ms与证据索引通过。价格与
显示单位已对齐；重建边界及未完成项见研究文档。下一步为神秘箱、传送器及武器升级。

# Factory power and bridge accepted — September24

`OLMOD_FACTORY_POWER_MOTION=1` restores Factory's raised bridges, recorded
power-switch and bridge motion, powered cabinet and native four-jet steam group.
Read .agents/research/factory-power-bridge-20260924.md for IDA/demo evidence,
transaction ownership and reconstruction limits. Factory and exact-build
two-client Nuketown FFA playtests PASS; seven suites, Release, 50ms regression
and source audit PASS. No new netfields or native ABI changes.
The failed static-model configstring experiment is corrected without bypassing
native validation. Next: Factory perk machines, then teleporters, then mystery
box and Pack-a-Punch together. User owns menus; local launchers stay excluded.

Factory电源、升桥初态、下降轨迹、电源柜及四处原生蒸汽通过同构建Factory与
双客户端FFA实测。静态模型重复更新断线已修正，保留原生验证与重建边界。

# Factory class-confirmed arrival accepted — September 24

`OLMOD_FACTORY_ENTRY=1` restores Factory class confirmation, authored platform
spawns, stationary native arrival particles and recorded introductory text/vision.
Factory and exact-build two-client Nuketown FFA playtests PASS; seven canonical
suites, Release, 50ms regression and source audit PASS. Evidence, activation and
reconstruction limits: [.agents/research/factory-entry-20260923.md](.agents/research/factory-entry-20260923.md).
Gameplay was tested on e1faa84; sound/camera choreography and two-player Factory
entry still need dedicated validation. Local graphics/FFA launch tooling is excluded.

Factory入场选装功能通过同构建Factory与双客户端FFA实测；原生证据、重建边界及
启用方式见研究文档。双人Factory入场、音效与镜头编排仍需单独验证。

# Native face-glow acceptance — September23

Collision a9c1ac6 accepted and published to both authorized repos. BC restores
optional ordinary native eye lens flares plus mouth glow; read
.agents/research/cyborg-face-glow-20260923.md. Special red/global switching
trigger remains unknown. Factory and exact-build two-client FFA PASS; seven
suites, Release, 50ms and source audit PASS. User owns menus.

眼部光斑与嘴部辉光：生命周期适配为重建，Factory与同构建双客户端FFA实测通过。

# Player/cyborg collision candidate — September23

Round-color commit96208b3 is published to both authorized OLfinal-live repos.
BB restores a separate player Pmove view of native packed-solid cyborg capsules.
Read .agents/research/cyborg-player-collision-20260923.md. Bullet/actor navigation
views and ordinary multiplayer are preserved; no rigid crowd separation claim.
Factory101 kills/round4 and exact-build two-client FFA PASS. Seven suites,
50ms,Release and evidence audit PASS. User owns menus.

玩家与活僵尸碰撞：独立Pmove视图；第4回合101击杀及同构建FFA通过。

# Round-color acceptance — September23

Accepted scoring base2835f93 published to both authorized OLfinal-live repos.
Read .agents/research/cyborg-round-colors-20260923.md. BA separates Factory
clothing from round-selected body colors:1–4blue,5–8yellow,9orange. Later rounds
hold orange as explicit fallback; no claim of global live-eye recoloring.
No death/movement/score policy changes. Factory and exact-build two-client FFA
playtests PASS; seven suites,50ms,Release and source audit PASS. Ready for
scoped publication to both authorized repositories. User owns menus.

回合配色候选：服装与颜色分离，仅影响新生成的身体。10回合后策略为明确回退；
Factory与同构建FFA实测通过，不宣称恢复原版眼光全局变化。

# Cyborg scoring and scoreboard accepted — September23

Read .agents/research/zm-scoreboard-accounting-20260923.md. AZ Factory and
exact-build two-client Nuketown FFA playtests PASS; seven suites,50ms,Release
and source audit PASS. Native damage-number transport, zombie weapon-location
scaling, independent score/battery, blue rewards and Tab row are included.
Orange head-hit/decay criteria remain default-off reconstruction. AY's90-point
rule is superseded by recorded80-point headshot-counted kills. No round-color,
death-FX or probability change. Next increment: round-selected body colors.
User owns all menus. Publish the same accepted commit to both authorized repos.

Factory、同构建双客户端 FFA 及源码验证通过；分数与电池分别记账，恢复原生伤害数字
和记分牌。橙色条件仍为可选重建；本次不修改死亡概率或回合配色。

# Head-intact death weighting candidate — September22 (published0d64246)

On accepted b0e0bf2, reduce ordinary head-intact Tesla base-animation weight from
50% to20% of the complete pool. Preserve headless/electrical behavior. This is
reconstructed presentation tuning; no native probability claim or damage-number
changes. Read [.agents/research/head-intact-death-weighting-20260922.md](.agents/research/head-intact-death-weighting-20260922.md).
Factory and exact-build two-client FFA accepted on AV. Ready for scoped publication.

# Headless wave-counter hotfix — September 22

Isolated from published e384059. Read
[headless-wave-notifications](.agents/research/headless-wave-notifications-20260922.md).
The published timer death path loses its Lua notification at frame rotation.
The focused regression reproduces it. Fixed suites, Release,50ms and source audit
pass. Factory and exact-build two-client Nuketown FFA playtests pass;
no damage-number changes, new PR, force push, or inherited PASS.

# Refined Factory damage/FX candidate — September 22

Presentation correction: Tesla-named BASE animations also occur without nearby
body-shock events in original CODOL recordings, including on headless models.
Ordinary deaths retain the existing base mix. Electrical loop/down sequences,
body lightning and delayed electrical head removal require the separate lethal
weapon classification. AQ coupled these incorrectly; AR overrestricted base
animations. Exact headless-selection triggers/odds are not recovered. Natural
Wunderwaffe acquisition/chain combat remains unverified.

Read .agents/research/factory-refined-damage-fx-20260922.md. Parent baseline cc2db75; refined native hit/FX contribution. Factory and exact-build two-client FFA accepted on AS (DLL C6F431C1DBF9D8AB28187B12C07A3D95B90D3329025DC749F83D31CD622D2F0B). Metadata audit references reconciled without changing the accepted gameplay source. Publish the SAME accepted commit to CODOL-EMU/ol-mod-olfinal and zeroxak/codol only after review; no PRs or force pushes. Current user policy supersedes older single-remote instructions below. All menu input belongs to the user. Power/perk work is excluded.

# Factory presentation and corpses (2026-09-21)

Factory and exact-build two-client Nuketown FFA passed. See [.agents/research/factory-presentation-preview-20260921.md](.agents/research/factory-presentation-preview-20260921.md).
Opt-in matched outfits/seven death clips and bounded nonblocking corpses are
accepted. Selection weights and100second/oldest-first cleanup are reconstructed
policy. Native head/torso death FX remain deferred. No publication yet.

Factory服装/死亡表现与无碰撞尸体保留已通过同构建双模式验证；选择与清理策略为重建。

# Factory sliding-door candidate (2026-09-20)

Factory door-opening playtest passed; exact-build FFA passed. See [.agents/research/factory-door-motion-20260920.md](.agents/research/factory-door-motion-20260920.md). Thirteen measured sliding brushes only; no debris/repair/corpse changes. Accepted for a scoped commit; not published.

Factory 滑动门实测通过，同构建 FFA 实测通过；杂物与修板等另行处理。

# Factory room/editor contribution review (2026-09-20)

Factory and exact-build two-client FFA passed. The opt-in room and portable tool are accepted for integration; see [.agents/research/factory-room-editor-20260920.md](.agents/research/factory-room-editor-20260920.md). Accepted for normal integration to OLfinal-live.

Factory 房间与同构建双客户端 FFA 验证通过；本次为人工拓扑与工具贡献，非原版 AI 恢复。

# Round-gap candidate (2026-09-20)

Empty-agent snapshot correction on b55174a; Factory through round3 and exact-build two-client FFA passed. See [.agents/research/actor-round-gap-20260920.md](.agents/research/actor-round-gap-20260920.md). Accepted for integration.

空快照 agent 删除修正：Factory 第3轮验证通过，同构建双客户端 FFA 通过。

# ol-mod task entry

## Navigation contribution review — 2026-09-20

Factory navigation/window entry and same-build two-client FFA passed on base4e2787a. See [.agents/research/navigation-increment-20260920.md](.agents/research/navigation-increment-20260920.md) for exact scope, IDA/runtime boundaries and opt-in activation. This supersedes earlier movement-deferred handoff text below. Editor and launcher tooling are excluded. Prepared for review, not published.

Factory 导航与窗口入口候选已完成同一构建的 Factory/双客户端 FFA 验证；范围及限制见上述复核文档。编辑器与启动工具不在本次贡献范围内。

## Contribution handoff (2026-09-17)

The accepted head-attachment increment starts at merged `OLfinal-live` commit `bfbf510` and
fixes only cyborg head attachment. Read
[the head-attachment IDA review](.agents/research/actor-head-attachment-20260917.md).
The user accepted visible Factory head attachment and the two-real-client
Nuketown FFA retest on this exact candidate. See the review for the human result
and machine evidence scope. Movement tuning remains deferred. The user's repeatable
two-mode shortcut supplements rather than replaces the repository test gates.
Future accepted increments use a normal integration to `OLfinal-live` after
verification and user acceptance, without new PRs, force pushes or bypassing
branch protections, per the user's latest instruction.

The previously accepted traversal contribution below is now merged upstream.

The cyborg traversal/movement candidate on `18928325` passed a Factory retest:
perching returned and frozen sliding stopped. See
[the IDA review](.agents/research/actor-traversal-20260917.md) for evidence,
validation and remaining limitations. This is a reconstructed adapter, not a
recovered original server controller. Keep head attachments, the warehouse
connector and the independent round-gap fix separate from this contribution.

The same gameplay commit also passed the user's two-client Nuketown `dm` mode
smoke test; both real slots were verified Playing. See the validation section of
the IDA review for the session adapter and uncompleted automated combat checks.
Repeat this multiplayer check alongside zombie validation for future zombie
improvements before committing, per the contributor's standing instruction.

When this checkout is used inside the CODOL workspace, read `../ACTIVE_STATE.md` first. It is the current cross-repository handoff and should be verified against Git and live processes before acting.

Do not read `.agents/AGENTS.md` in full at startup. It is a 115 KB legacy research and handoff document for an older branch. Keep it as historical evidence and query only the relevant section with `rg -n -m 30` when a specific subsystem needs it.

## Working rules

- Preserve unrelated working-tree changes and inspect path-scoped diffs before editing or committing.
- The live branch is `OLfinal-live`. Push only to the `olfinal` remote when the user asks for a push.
- Keep runtime logs, traces, crash dumps, generated assets, IDA databases, and game binaries out of Git.
- Prefer CODOL-native evidence from the exact build: source, xrefs, decompilation, wire bytes, and repeatable runtime traces. Use other Call of Duty sources as references, then validate differences against CODOL.
- Treat synthetic calls and forced state as probes. Do not describe them as proof of a natural client/server path.
- Use bounded reads and filtered tool output. Save full evidence on disk and record only the conclusion, artifact path, and next action in `../ACTIVE_STATE.md`.
- Reuse the canonical Wetwork launch and capture scripts listed in the active state. Do not rediscover historical one-off scripts unless the canonical path fails.
- The user controls the game UI. Inspect processes, logs, files, and traces without clicking or driving the client.
