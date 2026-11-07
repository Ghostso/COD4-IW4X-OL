> September25 acceptance: combined Factory and same-build two-client Nuketown
> FFA playtests passed on DLL5C1232D09C67EA580246485BE6D487D769FB637871CD29A515A72DD166855E1F.
> Seven canonical suites, Release,50ms and source audit passed. Earlier pending
> and failed-attempt statements below describe development history, not current acceptance.
> 同构建Factory与双客户端FFA实测通过；下文待测及失败记录保留为历史。

# Factory ammo boxes and Double Tap review / 弹药箱与双发复核

Status: candidate on 818849b; combined Factory and exact-build FFA pending.
当前为候选；需完成同构建 Factory 与双客户端 FFA 验证。

## Double Tap native evidence

Exact out.exe 3.19.26.22 SHA256
`044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9`,
IDA instance eeah, analysis idle (35783 functions).

- `coPerkStatsTable` row25 adds1 to `modRateOfFire`; ability row23 maps to
  float slot12 with default1. The purchased value is2, not a guessed BO1 value.
- `4254E0`, especially `4255F6..42561F`, reads ability23 (EAX=17h before
  `4041C0`) from playerstate+5A8 and multiplies elapsed milliseconds by it in
  weapon states6/7. `4258E0` subtracts that result from weapon timers+2C0/+2C4.
  Thus2 advances the eligible timers at twice the ordinary speed. Animation
  consumer `58CE50` separately uses the same modifier for playback.
- `425635..42572D` has an additional mode/weapon-upgrade branch. `432590`
  requires playerstate+594 bits1000/2000 and weapon definition bytes3908/3909
  equal7; it is not a second unconditional Double Tap multiplier. If that gate
  is satisfied, its multiplier with an active ROF ability is1.2.
- Original Sumpf recording `C-2021-8-30[21-43-53]zm` at278250ms adds perk bit25
  and publishes client2 float+E0=2.0. Re-decoded all8850 snapshots with native
  baseline-relative float semantics, no framing errors. Original Factory's
  reload purchase at555450ms likewise publishes+ B4=2.0 (12305 snapshots).
  Framing-only compact payloads were independently rechecked, not treated as
  final floating-point values. Local evidence: `factory-perks-20260924/`
  `verify-retail-rate.py`, `*-purchases-exact-floats.json`, `ida-rate/`.
- Current BN log shows ROF2 on purchase and after subsequent Armor/Reload
  purchases. Source overlays the class once; it does not accumulate each frame.

Keep the native2 value. This establishes the ordinary modifier, not a measured
rounds-per-minute guarantee for every weapon/upgrade combination. No firing
timer patch or animation-rate override is added in this increment.

原生计时函数将帧时长乘以射速修正值；原始录像精确浮点解码确认2.0。
保留该值，不凭感觉改成其他游戏的倍率。特殊武器升级有独立条件分支，
不宣称所有武器的实际每分钟射速都已实测。

## Original ammo hold / 原版弹药购买

Original Factory recording `C-2021-8-30[20-21-43]zm.demo`, SHA256
`ef3485dc7ebf1883d3ebf93bd282c1ee208b2ceb6821824891607e6411f0205e`,
decodes6190 snapshots exactly, with zero framing errors. Four native HUD size
animations start at583000,714150,791150,878850ms, each lasting2000ms.
The fill uses type5, material `progress_bar_fill`, white RGBA, width120/height9,
from-width3/from-height9, x=-60/y94, screen alignment0x99, origin1, sort-2.
The background uses `progress_bar_bg`, x0/y94, width120/height9, origin5, sort-3.
Names were resolved from the exact live client's native material table; numeric
indices are not portable and are never hardcoded in the implementation.

At585000ms Factory client2 battery5610 becomes4410 while ammo pools22/998
publish216/90. At716200ms6000 becomes4800 with the same reserve capacities;
at880900ms5570 becomes4370. Factory's1.2 multiplier makes1200 raw one battery.
Sumpf `C-2021-8-30[21-43-53]zm` independently records the same2000ms bar;
at339750ms battery1860 becomes860 and reserves refill. Its multiplier is1.
The earlier July Factory recording contains proximity hints, not a completed
purchase. Do not confuse the Factory WW hint or scavenger increments with a
paid purchase. Original special-weapon restrictions remain unresolved.

IDA538510 reads target width+4C, source width+58, start+60 and duration+64;
5385C0 handles height. Native HUD descriptors23..26 already represent these
fields. The writer now serializes them through an icon-only view of unused
text fields, retaining the address-sensitive SvHudElem/WorldClientState layout.
Text, score pulse, other HUD fields and the native descriptor table are unchanged.
The similarly named UI myChannelProgressBar belongs to teleporter UI and is
not the evidence for this ammo interaction.

原Factory录像确认四次2000ms白色进度条及完成时1200原始电池扣款，即一电池。
IDA确认原生HUD宽高插值；按名称解析材质，不硬编码材质编号，不增加网络字段。

## Server owner and reconstruction boundary

Factory's seven shipped `ammobox_trigger` hulls81..87 and localized
`ZOMBIE_CRATE_AMMO_REFILL` prompt are used under the Factory-perk opt-in.
Holding committed use in the same authored hull/life starts the recorded bar.
Release, leaving the hull, changing station/life, or a500ms input gap resets
progress. Completion revalidates funds/stock and atomically charges one battery
with reserve refill; a held key cannot repeat the purchase until released.
These cancellation, stale-input and repeat-suppression rules are reconstructed
server safety policy; the original server code is not recovered.

The world enumerates distinct held primary/secondary/granted firearms, groups
resolved capacities by ammo index with the existing11-bit cap, and validates
the native playerstate overlay before committing ammo and currency. Held firearm magazines and reserve pools refill together. Equipment, selected
weapon, perks and score remain unchanged. Full magazines plus full reserves,
insufficient funds, dead/non-playing/invalid/non-Factory clients are refused.
No-power access remains reconstructed. Grenade refills, second-hand/akimbo clips and WW exclusions remain outside
this increment. Magazine ownership is now established by acknowledged-baseline
reconstruction below; the earlier reserve-only candidate was incomplete.
This supersedes the preceding candidate's instant/free behavior.

取消、输入超时及防重复扣款为重建保护策略。枪械弹匣及备用弹药一起补满；手雷、副手双持及特殊
武器限制不在本次改动内。无电源也可购买为重建策略，不能宣称全部原版逻辑已还原。

## Magazine correction — September25 / 弹匣补充修正

Rebuilt every T2 clip and T4 reserve array against its declared acknowledged
snapshot baseline, including full-snapshot zero initialization. This supersedes
the earlier uncertainty about clip updates possibly being concurrent reloads.
Factory6190 and Sumpf8850 snapshots decode exactly; unchanged clip counts come
from the proper baseline, not simply the preceding chronological frame.

| Recording/time | Magazine before → after | Reserve before → after | Charge |
| --- | --- | --- | --- |
| Factory585000 | clips1210/1209:2/0 →36/15 | pools22/998:0/0 →216/90 |1200raw |
| Factory716200 | clips1210/1209:0/13 →36/15 | pools22/998:0/45 →216/90 |1200raw |
| Factory880900 | clip1210:35 →36 | pool22:8 →216 |1200raw |
| Sumpf339750 | clip1211:30 →100 | pool670:0 →400 |1000raw |

Several completions refill two magazines simultaneously while reserves are
empty beforehand. Thus reserve transfer via ordinary reload cannot explain the
observed result. The third Factory hold (791150) does not complete within the
recorded interval: no charge or refill; it is an attempt, not a fourth purchase.
Factory also publishes equipment clip931 rising on completed purchases; that
is retained as evidence for later equipment work, not silently implemented here.

Fresh exact-client IDA instanceeeah, analysis idle35783 functions, decompiles
671D80 (requested address673349 falls within it). Clip block673269..6732DD
reads4-bit slot,11-bit index and two independently present9-bit counts into
playerstate+494 with12-byte stride. The old decoder comment's673349 address is
not the current clip-block start; the decoded widths match the actual reader.
No game-side reader, netfields or ABI edits are necessary.

The refill transaction now fills resolved held firearm clip count0 to its
capacity, with9-bit bounds; shared clip IDs use maximum capacity, not addition.
It preserves unrelated clips and count1. A partly empty magazine with full
reserve now qualifies, but a full loadout remains a no-charge no-op. Existing
hold, cancellation, currency and native overlay validation remain the owners.
Local evidence: verify-purchase-magazines.py, *-purchase-magazines.json and
ida-magazines/0x673349_0x673349.c. JSON export initially rejected byte fields;
that output-only error was corrected before the saved successful runs.

原始Factory与Sumpf录像证明购买完成时弹匣和备用弹药同时补满，不能由普通换弹
解释。按确认快照基线重建弹药数组，并通过IDA核对字段宽度；不修改原生网络格式。
弹匣未满但备用弹药已满也可购买；全满不扣款。手雷和副手双持另行处理。

## Validation

Source assertions cover depleted/full/invalid cases, both weapon capacities,
magazine-only depletion, unchanged perks, native clip/reserve projection, insufficient funds and one
completion charge. Hold tests cover early release, interrupted contact, station
and life changes, input gaps, completion latch, recorded HUD geometry and size
field validation/serialization. Existing FFA rejection remains covered.
Canonical seven suites, Release,50ms and evidence audit must pass for the frozen
candidate. No source-only assertion is a visual progress-bar acceptance.

Factory retest: spend reserve ammo, add one battery with Numpad+, tap use (no
purchase), hold use for two seconds (white bar, refill and one-battery charge),
cancel by releasing/walking away, then repeat. Full stock must not charge.
Retest perks alongside ammo, followed by exact-build two-client FFA. Both human
acceptances are pending; nothing committed or pushed.
Local reproducible evidence: factory-perks-20260924/mine-ammo-hold.py,
mine-more-ammo-holds.py, *-ammo-hold.json, ammo-materials-live.json and ida-ammo/.
Native recordings, IDBs and live binaries stay local.
