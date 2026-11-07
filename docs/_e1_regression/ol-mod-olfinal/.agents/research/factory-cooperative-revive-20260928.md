# Factory cooperative revival / Factory合作救援

Status: accepted September29 on base bdfebbd; two-client Factory and exact-build Nuketown FFA playtests passed.
状态：基于上游bdfebbd；同构建Factory与双客户端FFA实测通过。

## Evidence and limits

IDA Professional 9.3, exact CODOL1649370 out.exe SHA256
044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9.
Analysis settled before decompilation. Raw binaries/IDBs/decompilation stay local.

* CODOL PM_CheckDuck417D10 at417FFB..418003 forces prone when ps+4 is7.
  PMoveSingle41CB40 treats types>=8 as dead movement, while7 continues through
  collision/movement. This establishes the native prone transport, not the full
  original server's last-stand script or exact transition animation selection.
* BO1 PlayerCmd_Revive605E90 clears lastStand/revive, restores max health and
  damage feedback, then selects a laststand-to-stance animation. Its pm_type8 is
  NOT CODOL's value: CODOL8 is dead. No BO1 offsets/types are transplanted.
* CODOL6DDF40 initializes myReviveHint;6DE020 reads a separate countdown and
  ui_zhunt_wait_revive. That is insufficient evidence to repurpose zombie HUD
  netfields. This candidate uses the existing hint/progress material transport.
* Quick Revive consumes the already recovered ability105 resolved rate3. Hold4s,
  bleedout45s, reach72units, damage interruption, bleedout pause while held,
  max-health restoration and next-wave respawn are explicit reconstruction
  policy. The original CODOL timers, perks lost on down, generalized pistol selection,
  revive-specific voices/animation events are not yet recovered. Spectator
  playerstate transport is now measured below; target selection is reconstructed.

原生证据仅确认CODOL俯卧状态传输与现有能力倍率；4秒救援、45秒流血、72单位范围
及服务器状态机为明确标注的重建规则，并非原版完整脚本。不得套用BO1的pm_type数值。

## Ownership

OLMOD_ZM_COOP_REVIVE=1 is admitted only for zm/zm_factory_sh and arms once two
Playing lives have spawned. It remains armed for that session if a player leaves.
Solo sessions and FFA keep their existing damage/death behavior.

Lethal damage creates a generation-owned downed side record, health1 and native
pm_type7 without a PlayerKilled event or a new spawn. Native player owner sizes,
netfields, collision ABI and the shared FFA death path are unchanged. Health
regeneration, zombie targeting and cooperative spawn-zone occupancy exclude downed
players. Use requires a living helper, uninterrupted fresh committed commands,
bounded 3D distance and a native world trace. Releasing Use, losing reach, taking
damage, disconnecting or replacing a life cancels progress. Completion restores
the same life/loadout and awards one scoreboard revive.

Bleedout uses the existing death transaction and holds respawn until the next
wave. An all-down team stops the director and selects the isolated zombie results path.
The outcome is a localized game-over caption, current scoreboard/profile data,
ui_match_complete at+1500ms, then EXE_MATCHENDED at+7600ms. It does not select
FFA podium assets, victory music or grant invented reward items. A bled-out
player follows a living teammate until next-wave respawn. The exact original
defeat-specific choreography remains unresolved.

## Validation

Machine: seven canonical suites and50ms regression pass. Coverage includes
solo/two-player arming, native movement type preservation, target exclusion,
missing/blocked trace refusal, release cancellation, continuous hold completion,
same-life health restoration, no duplicate completion, ability-rate3, bleedout,
legacy three-second respawn suppression, next-wave respawn and all-down handling.
Release and202-entry partial source audit pass. Two-client Factory and exact-build
Nuketown FFA playtests passed on the frozen candidate. Human acceptance is separate
from the listed machine assertions; no additional automated combat result is claimed.

Focused test: both clients manually enter Factory and confirm classes; let one
survivor be downed, revive with Use, interrupt/repeat and swap roles. Then verify
bleedout/next-round recovery and all-down results on both clients. Check both bodies, weapons,
HUD and ordinary doors/round progression. Same-build two-client FFA remains a
separate acceptance requirement before publication.

## Native revive UI and results evidence / 原生救援界面与结算证据

Original Factory C-2021-7-31[15-32-16]zm.demo, SHA256
 a8c461be9b8544eb041e95b37a4054a999642b34469cc3b0dda64d55fe2d4a97:
60150 archived HUD slot0 carries type14, targetEntNum1, material199,16x16,
RGBA255/255/51/200, value1, flags0x408. At70850 it switches to material200;
72750 removes it after revival. The sequence repeats at514050/519150.
Original Sumpf C-2021-8-30[20-21-43]zm.demo independently records the same
material transition at547000/551300, removing it at553400.

Read-only retained NCS resolution in the exact CODOL client maps199 to
waypoint_last_stand_localized and200 to waypoint_revive_new. Runtime code resolves
these names rather than hardcoding their material indices. Localized NCS band
952 has52 MPUI_BEING_REVIVED,59 MPUI_REVIVING,462 ZOMBIE_GAME_OVER. The native
PLATFORM_REVIVE prompt is present in both original recordings and is registered
by name through the existing hint owner. CODOL IDA538B70 reads Text labels
through538250; the wire serializer is unchanged.

The white treatment bar uses the measured native interaction materials/layout
(fill186,background184,120x9,y94) and a localized caption at y80. The available
revive recordings show the downed viewpoint, not the helper's full treatment
bar; applying that interaction geometry to treatment is an explicit visual
reconstruction guided by the supplied reference. No replacement bitmap is used.

All five retained original zombie endings are victories. Factory outcome1235750
closes menus (r,H,m0), sets configstring479, asserts ui_match_complete at+1500ms,
and sends t EXE_MATCHENDED at+7500ms. Four Sumpf endings agree within200ms.
CODOL IDA5C0FD0 and5BF940 distinguish EXE_MATCHENDED from generic disconnection;
613A40/6119F0 handle the reliable dvar path. Applying the measured successful
zombie transition schedule to team elimination is reconstructed; a retail defeat
capture is still needed. The native after-action presentation was included in the two-client Factory playtest. This evidence does not claim exact loss rewards,
voice, menu payload or pose parity. No fake loot/XP grant is introduced.

原始录像确认黄色救援标记与救治十字图标的材质切换、颜色、尺寸及目标绑定。
治疗进度条采用实测交互条布局；完整失败结算尚缺原版失败录像，当前复用已确认的
僵尸模式结算传输时序，不使用FFA领奖台或胜利奖励。同构建双客户端Factory与FFA实测通过。

## Death and teammate spectating / 死亡与队友观战

Status: accepted with exact-build Factory and two-client FFA playtests. The prior UI
candidate's revival worked in a two-client playtest, but after bleedout its
camera stayed at the death position. It lacked a spectator view owner.

Exact-build IDA45CE10 (CGAME_FOLLOWING string xref at45CEAF) reads secured
playerstate+0x10 and tests bit0x800 before drawing the followed-player label.
The five original zombie recordings decode to46,664 complete snapshot endpoints.
Three contain359 follow snapshots:20-21-43(168),20-34-14(32),21-43-53(159),
all C-2021-8-30. Field54 is0x2800 plus transient subject bits; field59 is the
watched client instead of recorder2. Normal play is0x1000 with subject2.
At1078250..1080000 in21-43-53 the subject changes from1 to4 after subject1's
death state. Follow snapshots retain subject pm_type0/1. The Factory recording
does not contain observer follow; applying the shared zombie protocol to Factory
is a reconstruction supported by the client consumer, not a Factory-specific demo.

The immutable snapshot keeps recipient identity separate from subject identity.
Only the wire view copies the survivor's playerstate and sets ownership0x2800;
the authoritative dead player remains health0, with its own slot, life, corpse,
inventory and next-wave respawn owner. Both current and acknowledged old frames
resolve their own subject before delta encoding. Follow disables recipient
prediction substitution and uses subject hold-breath/damage-number state.
No client-side per-frame hook, new wire field, or native player-node enlargement.

Deterministic lowest-live-slot selection and automatic reselection on disconnect
or death are policy. Manual target cycling/free-camera and exact retail death
camera delay are not implemented. All-down results take precedence over following;
next-wave spawn removes the projection. Downed players are not eligible subjects.
The option remains restricted to cooperative Factory; FFA gets no projection.

原版三份僵尸录像共359帧确认观战标志0x2800及被观察玩家编号；IDA确认0x800的
“跟随”界面判断。仅在发送快照时投影队友视角，不改变死亡玩家的生命、装备或输入
归属。最低存活编号选择、自动切换及Factory应用为明确重建；手动切换与自由镜头未实现。

## Downed inventory and damage feedback / 倒地装备与受伤反馈

Status: accepted September29 with exact-build Factory and two-client FFA playtests. Exact CODOL
executable SHA256 044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9.
The five original recordings were decoded against their referenced baselines:
46,664 complete snapshot endpoints. Two Factory down/revive episodes provide the
inventory evidence; they do not prove every weapon or map variant.

At Factory60050 the recorder holds MG4(45/200) and TMP(15/45). At60150 pm_type7
removes the ordinary gun and gives TMP15/90; firing consumes this temporary ammo.
At72750 revival restores MG4(45/200) and TMP(15/45). At514050 a two-ordinary-gun
loadout instead receives M9(15/90); at521150 the original weapons/ammo return.
Recorded forged identities1159/1178 resolve to base M9/TMP, but are not copied
into runtime. The fallback resolves m9_mp by name and validates its definition.
Preference for an owned secondary pistol, then primary pistol, then M9 is a
reconstruction of those examples. Full definition clip plus90 reserve generalizes
their observed15/90; other pistol capacities are not independently verified.

The temporary inventory is generation-owned and published only after the native
damage transaction commits. Restore includes held weapons, clip/reserve counts,
offhand slots, resolved loadout and an existing supplemental weapon grant. Downed
input cannot select the hidden standing loadout or throw its equipment. Disconnect and a new spawn discard the old backup; bleedout never restores it into a dead life. No pinned native ABI grows.

Points remain enabled while downed. In the second original episode pm_type7 lasts
514050..521050; scoreboard12320 rises to12400 at516350 and12480 at517450, alongside
two kills/headshots and native blue80 reward updates. Suppressing downed rewards
would contradict this capture. Separate battery conversion is unchanged.

Original down commands are `i 1000 2.000000 0 1`, `3 "grayscale" 1000`, then the
pistol selection; revival sends `i 100 0.000000 0 1` and restores the gun. IDA613A40
dispatches `i` to611920/43C250 (timed blur) and `3` to46CEF0 with vision channel5.
The candidate reproduces these and restores the Factory vision on revive/bleedout.
That cleanup is explicit policy; a full-screen red-blood overlay is not established
by the mere existence of myBloodOverlay registration at6D3410. Recorded UI countdown
starts at40; existing45-second bleedout remains labeled reconstruction, not native timing.

The missing claw overlay uses existing snapshot tail T16. IDA671D80 at674114..674183
reads eight records, index3 bits, sequence4, style4, entity12; destination ps+0x3812,
stride4. Renderer562070..562493 selects zombie_claw%d for style1 and controls its
artwork/placement and450ms fade. Original Factory and four Sumpf recordings carry
these actor-associated style1 records. Style0 also occurs but is not reinterpreted.
Successful zombie melee damage now produces a bounded eight-record side owner;
ring ordering and sequence policy are reconstructed. Immutable acknowledged frames
carry deltas, including injury-only changes and explicit clears on life/view changes.
FFA receives no producer. There is no added netfield or replacement image asset.

Regression coverage includes independent temporary ammo/restoration, native fallback
selection, recorded vision commands, bounded T16 encoding/wrap/acknowledgement/clear,
injury-only snapshot deltas, follow ownership and the prior revive lifecycle tests.
Release, source audit and playtest receipts are recorded with the frozen candidate;
machine checks do not establish visual acceptance or long-session stability.

原版Factory两次倒地确认独立手枪弹药15/90，救起后恢复原装备与弹药；倒地期间
两次击杀各获得80分，因此保留计分。手枪优先级及其他弹匣容量属于明确重建。
IDA确认灰度/模糊指令，以及T16八槽爪痕反馈通道；客户端负责原生图案和淡出。
仅提交成功的僵尸近战伤害生成反馈，不改变FFA、原生结构大小或计分规则。
同构建双客户端Factory与FFA实测通过；上述自动检查与实测结果分别记录。

## Accepted build / 验收构建

Frozen gameplay DLL SHA256:
0D9A159FFC9E44398661427B1DAD1E836C3AA2DA42F4DDF3C2569918041BD934.
Two-real-client Factory and same-build Nuketown FFA playtests passed. All313
packaged source/asset/test files match the final gameplay tree. Final documentation
does not alter that candidate. Machine checks: seven suites, Release,50ms,
202-entry partial source audit and independent native T16 payload decode pass.
Source audit remains partial; this is not a claim of whole-server native parity.

同一冻结构建通过双模式实测；313个源码/资源/测试文件保持一致。原生脚本未完全
恢复，计时与选择策略仍保留前述重建标记；不包含本地测试基础设施或原生资源。
