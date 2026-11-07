# Factory mystery-box restoration / 工厂神秘箱恢复

Status: isolated box-only increment accepted; default off. Fresh Factory and
exact-build two-real-client Nuketown FFA playtests passed. Earlier combined
build results remain historical and were not transferred.

`OLMOD_FACTORY_INTERACTABLES=1` enables only the Factory mystery box in this
increment. Authored sites, generation-owned lid/display/FX entities, atomic
firearm claims, Max Ammo and bounded teddy relocation are included. The pool
uses ordinary published class-derived firearms and Max Ammo for now. This is
explicitly provisional, not a recovered original reward table.

Teleporter/PAP owners, upgrade registry mutation and special weapon/trap combat
are excluded. Their full source remains preserved outside this contribution.
The separate loading note describes the retained attempt-scoped lookup cache.

本次仅含工厂神秘箱及其共享动画、展示和背包事务依赖。普通枪械加最大弹药为临时
奖池；传送器、PAP和特殊武器/陷阱战斗不在本次范围。缩小范围后已重新通过Factory与同构建双客户端FFA验收。

## Historical evidence, corrected scope

The sections below preserve the native investigations and failed hypotheses.
Their dated candidate/pass statements are historical. Current scope is above;
no original server box controller, complete pool or CODOL odds are claimed.

## September26: ammo orientation and original pool census

CA weapon claims and teddy facing passed the focused playtest; ammo was rotated.
CB uses lid yaw+180 for zombie_ammocan. Original Prototype590750/entity537 has
yaw135, authored lid315 and marker45. The bear retains its accepted marker yaw.
The prior notes incorrectly named the22-12-10 recording Sumpf: its gamestate and
corpus catalogue identify zm_prototype_sh. Cross-map evidence is not Factory-
specific eligibility. Authored map entities and recorded orientation establish the axes.

A new complete five-recording hint census decoded46664 snapshots without framing
errors: Factory12305/6190/9060, Sumpf8850, Prototype10259. Actual Factory offers
include all four traps and Tesla; Prototype includes Ray, Max Ammo and the Bowie
knife (generic melee hint at296900, entity503/model249 world_knife_bowie). No
ordinary class firearm or monkey offers observed. This does not prove absence
from the full native pool, nor determine probabilities from camera observations.

Read-only native StringTables plus fresh out.exe IDA49CA70/49C870 resolve the
previous326 unavailable cells:324 empty strings, ray_gun_zm, tesla_gun_zm.
All known serialized cells match. The107-row generic table has blank difficulty
values for its weapon rows; the15-row Factory override is not a loot table.
These do not supply native box weights. Monkey/freezegun/thundergun asset presence
does not establish eligibility. Special-reward gameplay and native pool remain
unfinished; no inert items enabled. Exact CB Factory/FFA still pending.

本次五份原始录像共46664快照精确解析，Factory实际提示证明四种陷阱及Tesla。
Prototype证明Ray、最大弹药和Bowie刀；之前把该录像误标为Sumpf，现已纠正。
弹药模型按箱盖+180度恢复，熊保持已验收方向。原生表中武器概率列确为空，不能
把资源存在或旧枪名当成掉落资格/权重。完整奖池和特殊奖励使用逻辑仍待完成。

## September26: reward ownership, teddy axes and Max Ammo candidate

BZ admitted incoming alternate modes1162/1165 as independent guns: their native
hosts1161/1164 point to them at definition+3720, but the children have no outgoing
link. Exclude both directions and reject alternate exchanges atomically. Fresh
out.exe IDA424470 confirms native held-list/alternate ownership. Repeated-swap
regressions preserve the other firearm's ammo. Exact cause of the unlogged1160
claim remains unknown; refusals now report current/offer/site/reason/refund.
The authored weapon_spawn marker supplies teddy/ammo angles; firearms retain lid
axes. Six Factory marker/lid pairs have the90degree difference observed visually.

Original Prototype C-2021-8-30[22-12-10]zm Max Ammo offer590750/claim591550 changes
equipment clip931 to2 and reserve992 to90 without replacing a gun. Add a separate
Ammo reward, resident zombie_ammocan and original ZOMBIE_CHEST_MAXAMMO prompt.
The source/native atomic refill uses current-life held equipment and preserves
ownership/selection/battery. Full equipment clip capacity and general magazine
fill beyond this sample are reconstruction; paid stations retain their existing
firearm-only scope. Equal-entry pool odds/full-ammo exclusion are reconstruction.

原候选误将替代射击模式当作独立枪械。现同时排除原生关联两端，失败时记录原因及
退款状态；不能据此断言未记录的1160领取失败原因。熊和弹药使用地图奖励锚点角度，
枪械继续沿箱体长轴。原始录像证明最大弹药奖励补充装备弹匣与枪械备弹，不替换枪。
新增独立奖励类型，保持已持武器、选择和电池；未观察装备的容量/概率为明确重建。

Still incomplete: original pool. Remaining ordinary guns are provisional native
published class-derived firearms. Ray/Tesla and fire/freeze/shock/shrink offers
are proven, but type2 fire and offhand deployment/damage continuations are not
implemented. Monkey residency does not prove eligibility. Do not expose inert
rewards or call this full native parity. Exact Factory/FFA acceptance pending.
原始完整奖池仍未恢复；特殊枪械与陷阱的使用逻辑待完成，不能只发放无功能物品。

## September26: bear-pile visibility and BO1-derived relocation candidate

The authored active-site bear pile was never hidden. Preserve script_noteworthy
through source-only map metadata and select each *_rubble by exact link. No native
entity ABI change. Resident bear/couch-effect assets and native sound aliases are
verified; fresh out.exe IDA410BD0/5201B0 supports the model/trajectory transport.
Bear odds, refund and lift choreography use the owned BO1 script as a reference;
CODOL odds/order are unknown. Uniform OTHER-site destination is reconstruction.
Bounded map-owned phases survive buyer departure and clean temporary entities;
failed destination restores the old site without a frame retry loop.

Factory地图每个未启用箱点都有熊堆，原控制器未隐藏当前箱内的熊堆。现按地图
script_noteworthy精确关联，不扩展原生实体ABI。熊模型、烟雾资源及声音别名已核对；
IDA只证明模型和轨迹传输。熊出现概率、退款和升空时序参考BO1，其他位置均匀选择
属于重建，尚未证明CODOL原版规则。阶段有界清理，目的点失败恢复旧箱，无逐帧重试。
原始奖池及特殊奖励使用路径仍未完成；本候选Factory/FFA待验收，未提交。

## September26: per-body horizontal box alignment candidate

BX rise visually accepted; reward M9 still offset to the right. Both owned client
and server expose M9 root midpoint(-7.8863506,.0194250,-1.7567661); authored
base/lid/marker origins agree. Exact-client IDA520263/51FE00/431B00/431A60
confirms modular root ownership, record stride5236 and world fields146/152/4412/4444.
The new map-setup read validates asset identity and geometry, then the box alone
rotates/subtracts horizontal body midpoint. Rise clock/height and FX stay intact.
This is reconstructed body centring, not a native retail script or full attached
weapon bounding box. Unknown bounds retain the old placement. Fresh visual and
same-build FFA remain pending. Native trap/wonder-weapon use continuations and
original reward pool are unfinished; no inert rewards are enabled.

BX上升已获视觉确认，但M9仍偏右。客户端与服务器的模型边界读数一致；地图箱体和
奖励锚点本身重合。新逻辑仅在地图初始化读取并校验根模型，水平旋转补偿中心，
保留原上升高度、时钟和特效。这是重建的主体居中策略，不是已恢复的原版脚本，
也不是所有附件的总包围盒。未知模型保持原位置；本候选视觉和FFA待验收。
原始奖池及特殊武器/陷阱使用路径仍未完成，未启用只能领取却无法使用的奖励。

## September26: recorded reward rise / 原始奖品上升轨迹

The class-derived display previously appeared45units above the marker. Original
Factory entity781 (165550) and Sumpf774 (870800) instead use native trajectory
7 for2000ms,3 for100ms,8 for899ms, then hold40units above the marker. DeltaZ is
25.80645179748535. Fresh exact-client IDA410BD0 confirms these trajectory
semantics. The source sends native trajectories and retains their start while
cycling models; phase updates are independent of150ms selector changes. PAP's
stationary display API is preserved. No new per-frame asset scan or engine call.
Local hashes/raw records: factory-interactables-20260925/BOX-RISE-AND-POOL-FINDINGS.md.

Original offer strings confirm four traps (fire/freeze/shock/shrink), plus Tesla
and Ray Gun offers. Factory's Tesla offer is tied to a complete box rise/cycle and
original model460 weapon_usa_tesla. These selected observations do NOT establish
weights/full pool. Current class-derived firearms remain a compatibility pool;
native lethal-equipment replacement and trap deployment are pending. No invented
trap odds or claims of complete native rewards. Fresh Factory/FFA required.

原始两段录像显示奖品由箱内升高40单位，使用7/3/8/0轨迹及2000/100/899毫秒
阶段；IDA410BD0确认原生求值。轮换保留起始时间，PAP静止展示接口不变。
录像证实四种陷阱及奇迹武器报价，但尚不能确定完整奖池或概率。当前仍为职业
派生枪械兼容奖池，致命装备替换和陷阱部署待恢复；本候选Factory/FFA待验收。

## September26: original box FX pair restored in candidate

Fresh offline decoding finds event113/127 and113/253 on two model121 root carriers
at box-open in July31 Factory(165550) and August30 Sumpf(870850); both disappear
with close at170550/876250. Current owned native registry maps these to
env/light/fx_ray_sun_sm_short and zombie/treasure_box2, agreeing with the previously
calibrated common-ZM list beginning122. Do not concatenate incomplete name lists.
Both recordings agree on marker origin/+5height and angles(90,lidYaw+90,0),
(-90,lidYaw-90,-90). Exact out.exe IDA452970/452D10/5319B0/4DB5E0 confirms
effect/bone encoding and attached ownership. Existing assets supply appearance.

The candidate resolves names once at map load, emits each effect once on two
noncolliding owned carriers and removes both on close; partial allocation rolls
back. The local report factory-interactables-20260925/BOX-FX-FINDINGS.md contains
capture hashes, native evidence and limits. Source tests verify transforms,
publication and cleanup, not visual fidelity. Original server scripts, complete
drop tables and exact brightness are not claimed recovered. Factory/FFA pending.

原始Factory与Sumpf录像均在开箱时创建两个根骨骼特效载体，关闭时移除。
当前原生注册表和已校准资源顺序确认短光束及treasure_box2；两段录像的位置、
高度差和朝向一致。IDA确认事件113编码及附着路径。候选只复用原生资源，
每次购买创建一次，关闭清理；分配失败回滚。人工视觉及同构建FFA仍待验收。

## September26: missing lid tree and replay / 箱盖动画树与重播

BU visibly cycles usable weapons but failed lid playback. Read-only client samples
show ES+98=0 and DObj.tree=0 while its ordinary clock advances. Exact out.exe
IDA5204B4/527290/527370 identifies ES+98 as the animation-tree selector, resolved
against789C534/count789C634 definition byte+10. Both owned client and server
registries uniquely map aliases727/728 to tree12; the two named clips each contain
120frames at60fps. The candidate resolves this membership at map load, binds the
active lid before purchase and refuses missing/ambiguous trees. It does not
hardcode12 or scan/call native assets per frame. 527B40->789E90->789B60 establishes
flags3 as complete weighting plus requested restart for repeated transitions.
The close phase now waits2000ms. Weapon-selector display keeps marker position
but uses lid yaw (long edge); that orientation and45unit lift remain reconstructed.
Fresh visual and exact-build FFA acceptance are pending. No new native hook.

BU枪械轮换可见，但箱盖播放失败。只读采样显示ES+98和DObj.tree均为0，而时钟
正常推进。IDA确认ES+98选择原生动画树；客户端及服务端均找到含开/关别名的唯一树，
两段动画都是120帧/60fps。候选按别名成员关系解析并提前绑定，不硬编码树号；flags3
请求完整权重及重复播放，关闭等待2000ms。枪械按箱体长轴摆放仍属重建策略。
人工Factory及同构建FFA待验收，无新客户端hook。

## September 26 standalone-display correction / 9 月 26 日独立展示实体修正

The BS build's box display exposed a producer/admission mismatch: the producer
sets a nonzero ET6 weapon selector with parent/tag zero, while the snapshot
validator accepted weapons only on linked children. This rejects the whole new
world frame, not just the display. The 4.4 s roll plus 10 s offer explains the
reported 14.4 s interruption until the display is freed; no render-FPS cause is
inferred. PAP shares this display API.

Fresh IDA instance `0dv5` completed analysis (35,783 functions) for `out.exe`
SHA256 `044C396C90A7CFA63EAC32BEA194BF4DFA4D1EAB547D9082AE8A575EB49257F9`.
At `0x520263`, centity `+0x15C` is `ES+0x68`, the actual weapon selector.
The parent test at `0x520273` only controls optional tag selection: parent zero
still reaches weapon DObj builder `0x51FE00`. Null-parent rendering continues
from `0x5222B5` to draw submission `0x5231EE`. The earlier interpretation of
centity `+0xD8` and its minus-one lookup as this network weapon field was wrong;
that separate override must not change the raw 11-bit weapon selector.

Correction scope: admit the producer's standalone subset with bounded nonzero
weapon and zero parent/tag/model/brush/podium; retain common validity checks and
the existing linked-child branch. Validate a candidate display before publication
and before reporting transaction success. Retain it through snapshot validation
and serialization in regression tests, including weapon change, PAP, removal and
invalid half-links. Model zero is a candidate restriction, not a universal native
requirement. This documentation does not claim the corrected build passed tests
or fresh Factory/two-client FFA acceptance.

The original box demo cycles field-19 model indices without a field-29 weapon
assertion. The candidate's weapon-selector box visual is reconstruction. The PAP
demo transmits both model and weapon; native code permits that combination but
clears the local model argument when selecting the weapon path. It does not prove
both fields draw separate meshes. This candidate uses the model-zero subset for
both displays; model mappings and retail animation remain unrecovered.

BS 构建的神秘箱展示暴露了生成端与快照准入规则不一致：生成端写入非零 ET6 武器
索引，父实体和标签均为零；校验器却只允许有链接的武器子实体。这会拒绝整张新世界
快照，而非仅拒绝展示实体。4.4 秒滚动加 10 秒报价与报告的 14.4 秒停顿相符；实体
释放后快照恢复。这里不推断渲染帧率原因。PAP 使用相同展示接口。

新 IDA 实例 `0dv5` 已完成 35,783 个函数的分析，输入 SHA256 如上。
`0x520263` 读取 centity `+0x15C`，即真正的 `ES+0x68` 武器索引；`0x520273`
的父实体检查仅用于可选标签选择，父实体为零仍进入 `0x51FE00` 武器 DObj 构建。
无父实体的绘制路径从 `0x5222B5` 继续到 `0x5231EE`。此前把 centity `+0xD8`
及其减一查询等同于该网络武器字段的解释错误；它是独立覆盖路径，不能据此修改原始
11 位武器索引。

修正范围为新增窄独立形状：武器索引非零且有界，父实体、标签、模型、刷模型及 podium
字段为零；保留共有校验和既有链接子实体规则。生成端须在发布及报告交易成功前校验
候选。回归必须让展示实体保留到快照校验和序列化，覆盖换枪、PAP、移除及不完整链接。
模型为零是候选子集限制，不是原生通用要求。本文不声称修正构建已通过测试或新的
Factory／双客户端 FFA 验收。

原始箱子演示循环写入 field 19 模型索引，未断言 field 29 武器字段，因此候选的武器
索引箱子展示仍是重建。PAP 演示同时传输模型与武器，原生允许这种组合，但进入武器
路径时会清零局部模型参数，不能据此断言两个字段分别绘制模型。本候选对两种展示均
采用模型零的窄子集；原始模型映射与动画编排尚未恢复。

## Mixed actor and lid animation publication / 演员与箱盖动画的共同发布

The BT visual failure is separate from the repaired entity-domain rejection.
The current run resolves open/close aliases 728/727, and the client lid458 was
observed with animation727 and start81700. The source helper queues ClearTree
then SetGoalWeight, but the agents-present snapshot branch previously generated
only ET_ACTOR records and omitted `frame.animationCommands`. Native `5221A0`
also skips its ET6 fallback when animation start `ES+6C` is nonzero. This is a
concrete missing-publication path, not evidence of unresolved clip names.

Fresh saved IDA `5400B0.c`, input SHA256
`044C396C90A7CFA63EAC32BEA194BF4DFA4D1EAB547D9082AE8A575EB49257F9`,
checks command time against client/global/entity floors at `54013D`/`54014D`,
updates accepted timestamps at `540212`/`540222`, then increments the global
floor once at `540285`. Export SHA256:
`23BAAAFC32B52F1BD0B105E9B7C7B772B7A9CB2392A7A19BDEC8B1AEE1907B18`.
The local evidence is `factory-interactables-20260925/box-visual-failure-20260926/5400B0.c`
in the parent research workspace. This is native consumer evidence, not the
recovered original server's lid controller.

The narrow writer correction keeps one command section and union alias table,
including actor null-ancestor slot0. It stable-sorts shared commands by their
original timestamps, emits those at/before the frame time before the unchanged
actor records, then emits future commands afterward. Same-time clear/goal order
is preserved. Retained commands are not retimed, avoiding repeated tree resets.
Combined records are capped at512; alias capacity includes the reserved null.
Actor type8/flags0, transition/maintenance selection and commit-after-complete-
snapshot delivery tracking stay unchanged. `writeExplicitAnimationCommand`
and `writeAnimationCommandSelector` share the previous generic payload bits;
this does not substitute generic type1 for the actor's ancestor-weighting type8.

Fresh same-input exports also resolve the script-model flags concern:
`527B40` case1 with flags bit0 set calls `789E90` at `527BFD`; `789E90` calls
`788BF0` at `789F5D`. The latter sets the node goal, then walks parent links
through `word_81AE7C6`, raising zero parent goals/rates to one. Thus existing
type1/flags1 already activates ancestry; no change to type8 is justified for
the lid. Export SHAs in the same local evidence directory are
`BE045DB7E6A194ACF4D1127DB95865E4D9527BCB86B2EF1AAAAD306F8EBE382E`
(`527B40.c`),
`57364D12801968E7CC0B2792BE2E06402B5D8B304FB47BC393E28CB915C58A03`
(`789E90.c`) and
`E3EF049BE81FA85A8A01D9885FD4E6866791B4FE75682779E8C86E28D6E9771E`
(`788BF0.c`). This confirms the preserved command mechanism, not retail box
clip assignment or current live animation success.

Mixed records are explicit because their actual wire positions also contain
generated actors and do not match `frame.animationCommands` indexes. The normal
writer also refuses generic baseline-index reuse when the previous frame had
agents. Ordinary-to-ordinary encoding is retained. Review covers this section
and the helper extraction only, not the full snapshot function/file. Focused
mixed-frame decode, alias/count limits, timestamp ordering and baseline-transition
tests are required; exact-candidate lid motion and Factory/FFA acceptance are
still pending. This update records no new PASS.

BT 的视觉失败与此前已修正的实体准入拒绝是两个问题。本轮已解析开/关动画别名
728/727，客户端箱盖458可见动画字段727、开始时间81700。生成端虽然排队 ClearTree
和 SetGoalWeight，但含演员的快照分支此前只生成 ET_ACTOR 命令，遗漏
`frame.animationCommands`。原生 `5221A0` 在 `ES+6C` 非零时也跳过 ET6 自动初始化。
这是明确的发布缺口，不能归因于缺少动画名。

上述精确输入的 `5400B0` 证明命令同时受客户端时间、全局时间下界和实体时间下界
约束，并在接收后推进下界。因此修正保留一个命令段和包含 null0 的联合别名表，按
原始时间稳定排序：不晚于当前帧的共享命令先发，随后保持原样的演员命令，未来命令
最后发。同时间清树/设权重顺序不变，不给保留命令重写时间，避免重复重启动画。
总记录上限512，别名上限包含空槽；演员 type8/flags0、发送节奏及完整快照成功后才
提交的记录保持不变。提取的小型共享写入函数复用既有通用编码，没有用 type1 替换
演员的祖先权重 type8。

同一输入的新导出进一步证明箱盖无需改成 type8：`527B40` 的 case1/flags1 经
`789E90` 进入 `788BF0`，设置节点目标后沿 `word_81AE7C6` 父链将零目标权重和速率
提升为一。现有 type1/flags1 本身已激活祖先。上述导出哈希固定了该调用链证据，
但不证明这些片段就是零售箱子的动画分配，也不代表本次实机动画已成功。

混合命令全部显式编码；其真实线序包含生成的演员记录，不能用仅含通用命令的 DTO
索引引用基线。上一帧含演员时，普通分支也禁用这类基线索引复用；普通帧之间的编码
不变。审查仅覆盖此段与小型编码辅助函数，不作整函数或整文件声明。混合解码、容量、
时间顺序、基线转换及精确候选箱盖/Factory/FFA 验证仍须完成；本文不新增 PASS。

## Current validation

Release, seven canonical suites, the 50ms server regression and the 187-entry
source-audit validator pass. Audit coverage remains partial; a valid index is
not a full native-implementation audit. Machine regressions cover mixed actor/lid
ordering, display admission/lifecycle, claim rollback, inventory preservation,
ammo refill, rise and relocation policy.

Focused Factory and exact-build two-real-client Nuketown FFA playtests passed
on the isolated CE build. Factory covered repeat opening/closing, native FX and
reward rise, ordinary weapon claims, teddy relocation and use at the new site.
FFA acceptance followed movement/reload, reciprocal kills, score, respawn and
audio checks. These are human playtest results, separate from machine assertions.
The accepted DLL SHA-256 is
`1CA7A8A0B60D812932AF0DB5849942208D4B92FC54C6CFB76E6E4DAEB47424C3`;
frozen source archive SHA-256 is
`E8B32B7BBFC05B24BF8D4B89D06B98AE567898E6FAB7EAB668C345CBF4053490`.
Gameplay/test sources remained byte-identical; only final documentation and
evidence-index acceptance changed after the playtests.

The shared snapshot boundary retains the existing function-matrix comparison
for BO1 Windows x86 SV_WriteSnapshotToClient (0x00717E80) and Ghosts PS4 x64
(0x1402078F0). CODOL's own command consumer and recorded wire remain the
authority; no Ghosts ABI/layout is imported. These scoped references do not
establish a recovered retail box controller, original odds, packet-loss visual
parity or complete special-reward functionality. Raw captures, binaries and
IDA databases remain local.

Factory与同构建双客户端FFA人工实测通过；机器回归与人工结果分别记录。
源码证据索引通过仅代表引用有效，不能等同全文件审计或原生行为完全恢复。
原始奖池、概率和特殊奖品功能仍有明确缺口，原始录像、二进制及IDA数据库不提交。
