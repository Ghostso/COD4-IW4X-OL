> September25 acceptance: combined Factory and same-build two-client Nuketown
> FFA playtests passed on DLL5C1232D09C67EA580246485BE6D487D769FB637871CD29A515A72DD166855E1F.
> Seven canonical suites, Release,50ms and source audit passed. Earlier pending
> and failed-attempt statements below describe development history, not current acceptance.
> 同构建Factory与双客户端FFA实测通过；下文待测及失败记录保留为历史。

# Factory perk machines — September 24, 2026

Status: candidate on818849b; first Factory test failed (no perk prompts).
Cabinet-edge reach correction awaits Factory and exact-build two-client FFA.
Enable `OLMOD_FACTORY_PERK_MACHINES=1` for `zm/zm_factory_sh` only.

## Original purchase evidence

Original player-recorded demos, not local test recordings, were decoded through
complete snapshot frames. Factory:12305 accepted frames; Sumpf:8850; zero framing
errors. These are offline observations, not a current candidate gameplay PASS.

| Recording / server time | Observed purchase | Price |
|---|---|---|
| Factory 501650 / grant506150 | Quick Revive, none owned | 2 batteries |
| Factory 551350 / grant555450 | Speed Cola, one owned | 3 batteries |
| Factory 1084050 / grant1088550 | Juggernog, two owned | 4 batteries |
| Sumpf 273850 / grant278250 | Double Tap, none owned | 2 batteries |
| Sumpf 710650 / grant715250 | Quick Revive, one owned | 3 batteries |

Factory `C-2021-7-31[15-32-16]zm.demo` SHA256
`a8c461be9b8544eb041e95b37a4054a999642b34469cc3b0dda64d55fe2d4a97`.
Sumpf `C-2021-8-30[21-43-53]zm.demo` SHA256
`6bf3d7cbdf90eb2243e2644f456fcd076d7147385f753cb54c7c1dc248602277`.
Reliable Factory hints878/879/880 carry Quick2, Reload3, Armor4. The Factory raw
deductions are2400,3601,4800; the one-unit middle residual is unresolved. Factory
battery multiplier is1.2, Sumpf1.0. Shared hint strings can describe another
player's offer: Sumpf's later Quick2 is not evidence that the local buyer's price
fell after purchasing Quick Revive.

Reconstruction: price is2+currently owned machine perks, ignoring class perks.
First three prices and differing first-machine identities support ownership over
fixed machine prices. Fourth price5 is extrapolated. No recovered server script
or evidence establishes a round-based increase. Loss/rebuy pricing is unverified.
The same calculation owns prompt and charge; insufficient funds and duplicates
retain the existing refusal path. No changes to other map economies.

## Native effect evidence

Exact IDA9.3 database out.exe, SHA256
`044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9`, instanceeeah,
auto-analysis idle.404100 maps modifier ID to client float slot;54C230..54C284
projects client modifier bits/floats into playerstate590/5A8.58CE50 reads reload
modifier1 in reload animation states and modifier23 for firing. No new netfields,
native offsets, calling convention or ABI are introduced.

Recovered `mp/coPerkStatsTable.csv` rows22..25 and
`mp/coAbilityModifiersTable.csv` define:

| Perk | Modifier | Default + delta | Client float |
|---|---|---|---|
| Juggernog |104 max health|100+150|server-owned|
| Quick Revive |105 revive rate|1+2|server-owned|
| Speed Cola |1 reload speed|1+1|1|
| Double Tap |23 fire rate|1+1|12|

Original Factory purchase sets reload float to2 and maximum health to250;
Sumpf Double Tap sets float12 to2. Purchases overlay the class base once, with
generation ownership. Class refresh, native prediction, snapshots and temporary
paint cleanup preserve the overlay. Reset clears it and other modes exclude it.
Juggernog increases current health by the maximum-health difference, retaining
injury (reconstruction); the death-hold development option remains unchanged.

## Limits and test scope

### Cabinet-edge interaction correction

The first candidate never registered a perk hint despite power activation. Its
strict physical-overlap selector missed logged approaches at Speed Cola
(-328,-830,61), Juggernog(715,-1419,133) and Double Tap(-323,-1077,191).
Comparing the standing player box to the authored hulls leaves6,11,11 units of
separation respectively. The cabinet collision prevents reaching the tiny use
volumes. Quick Revive was not approached in this sampled route; no live diagnosis
for that machine is claimed. Source-purchase tests alone did not cover reaching
the machines; the initial seven-suite PASS therefore did not establish usability.

The optional correction adds12 units in XY for only these four machine identities
when no ordinary prompt already owns the position. Original Z bounds, hull/slab
checks, power/ownership gates and collision remain intact. Machine-only selection
prevents unrelated volumes from shadowing this fallback. Regression cases cover
the three observed positions, a synthetic Quick Revive edge, distant positions,
other floors, door exclusion and other-map exclusion. This is a bounded use-reach
reconstruction, not a recovered original radius or proven native wall-occlusion
rule. Opposite-side wall behavior remains a playtest concern; no broad trigger
radius or collision bypass is introduced. IDA string searches for use-radius/FOV
and cursor-hint server controls found no original selection owner in this client.

Quick Revive's bit/modifier is stored, but cooperative downed-player interaction
is not implemented; this does not establish functional revival or solo self-revive.
Original spend-to-grant delays of4.1–4.6 seconds suggest purchase/drink choreography;
this candidate grants immediately and does not claim that choreography restored.
Native rendering, reload speed, firing cadence and price presentation need playtest.
Focused source checks cover price progression, unrelated class perks, actual
purchase/duplicate refusal, insufficient funds, modifier persistence, health,
reset and mode/option isolation. The lifecycle fixture uses a discounted synthetic
purchase after a real damage award; it does not claim an in-game economy test.

## 中文摘要

原版Factory与Sumpf录像支持按已持有机器技能数量递增的2、3、4电池价格，
第四次5电池是明确标注的推断，未发现按回合涨价的证据。提示与扣费共享计算。
IDA及原版表格/快照支持装填、射速、最大生命值和复活速率字段；效果叠加于职业
基础值且不重复累加。合作倒地复活与购买饮用动画仍未实现，不宣称已恢复。
Factory与同构建双客户端FFA待实测；原生文件与启动工具不纳入贡献。
