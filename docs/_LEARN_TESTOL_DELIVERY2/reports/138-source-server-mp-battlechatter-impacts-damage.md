# 138 · `server_mp` 首批：战斗语音、碰撞通知、伤害与计时

## 学习范围

本报告逐个读完以下 **10 个文件**：

1. `sv_battlechatter_mp.hpp`
2. `sv_battlechatter_mp.cpp`
3. `sv_client_impacts_mp.hpp`
4. `sv_client_impacts_mp.cpp`
5. `sv_damage_mp.hpp`
6. `sv_damage_mp.cpp`
7. `sv_destructible_mp.hpp`
8. `sv_destructible_mp.cpp`
9. `sv_frame_diagnostics.hpp`
10. 本报告的总装关系对照：`Appmain.cpp` 已在报告137完整学习，本次不重复计入文件数。

这是 `server_mp` 154 文件中的前9个目标文件（按本组功能顺序阅读，而非宣称 Glob 返回顺序就是依赖顺序）。所有结论来自源码；源码注释中的 CODREF/CODDIFF/实测记录均保留其证据边界。

## 一、Battlechatter：声音编号、受众与触发是三条独立规则

### 1.1 11条语音的编号公式

`SvBattleChatterLine` 有11项，顺序为：

```text
0 AttackFlashbang   1 AttackGrenade   2 AttackSmoke
3 AttackStiel       4 AttackStun      5 AttackThwC4
6 KillfirmGeneric   7 KillfirmInfantry
8 PlantClaymore     9 ReloadingGeneric 10 SuppressedGeneric
```

一个阵营的四个声音为 `f1, f2, m1, m2`，每个声音内11条连续；相邻声音参数相差 **52**。公式：

```text
TF: base=1674
SC: base=947
female: base + line
male:   base + 2*52 + line
```

这里实现的是 f1/m1，不是从 f1/f2/m1/m2 中随机；注释依据 IW4 总是选 voice1，明确不发明新随机规则。

静态断言校验：

| 阵营/性别/语音 | 参数 |
|---|---:|
| TF female reload | 1683 |
| TF male reload | 1787 |
| SC female reload | 956 |
| SC male reload | 1060 |
| TF female killfirm_infantry | 1681 |
| TF female attack_flashbang | 1674 |

这些 alias 已位于客户端 CCS announcer 高带，不需服务端另发 configstring/precache。`inform_casualty_generic` 不存在，因此不实现 casualty 语音，而不是用别的台词替代。

### 1.2 距离、抢占和受众

| 常量 | 值 | 语义 |
|---|---:|---|
| `SvBattleChatterAudibleRadius` | 1400 | alias 自身 maxdist；服务端按三维距离平方筛选 |
| `SvBattleChatterSuppressionRadius` | 1000 | 附近已有说话者则丢弃新语音 |
| `SvBattleChatterSpeakerHoldMs` | 2000 | 发言者占用时长，不按音频实际长度排队 |

`SV_BattleChatterSuppressed` 的细节：

- `currentServerTime >= untilServerTime` 视为过期；
- 同一个 clientNum 若仍占用，**无视距离**直接 suppression；
- 其他 speaker 距离平方 **严格小于** 1000² 才 suppression；恰好等于边界不 suppression。

`SV_BattleChatterAudience`：

- 只接收 `alive=true` listener；
- 距离平方 `> 1400²` 排除，恰好等于边界仍接收；
- `Team` 模式下 speaker 为 None/Spectator 则无人接收，否则只给同队；
- `Everyone` 排除 speaker 自己；
- `EveryoneIncludingSpeaker` 包括 speaker，是当前产品默认，而不是零售忠实行为。

`OLMOD_BATTLECHATTER_TEAM=1` 和 `OLMOD_BATTLECHATTER_EXCLUDE_SELF=1` 在上层用于恢复忠实模式。默认“所有人+自己”是源码注释明确记录的用户选择，不应误报成 IW4 原规则。

**表现限制**：per-client `p` 是本地声，无方向和连续衰减；服务端半径只是全有/全无数值门槛。选 `p` 而非 world entity 是为了能做 per-client team/self 筛选，因为当前快照没有恢复完整的 per-client visibility stage。

### 1.3 性别从模型名而不是 customization.female 读取

`SV_BattleChatterFemaleFromModelName` 按下划线拆分，遇到完整 token `m` 写 false、`f` 写 true，**最后一个匹配 token 决定结果**。这支持 `..._m_00_hrt` 等 variant；没有 m/f 返回 `nullopt`，不默认男性。

源码记录：456个 `fpa_` body 中279 male、173 female、4 unresolved；4个是误放在 body 槽的 `fpa_tightjeans_*`。选择这条路径是因为实测 female 角色的 `customization.female` 也为 false；不直接修那个字段，是为了避免同时改变客户端角色呈现。

### 1.4 reload 事件号

`SvEventReloadStartNotify = 0x1D`（29），不是名称表直观推测的27。注释引用本 build 实机 usercmd/event ring 的换弹记录，并区分 `EV_RELOAD_START_NOTIFY` 与状态变化：GSC `reload_start` 应对应 notify。

本组文件只提供事件号常量，实际事件扫描和 speaker 状态维护在后续 `sv_main_mp.cpp` 等文件核对。

## 二、Client impacts：32个 touch 的事务后处理计划

### 2.1 不是恢复出的原生 `ClientImpacts`

头文件反复强调这些是 ol-mod 的 typed candidate/callback/script schema，不是 CODOL `pmove_t`、`gentity_s`、`entityHandler_t` 或 script VM 布局。参考 BO1/Ghosts/BO2 的共同结构，CODOL 原生 server callback owner 尚未恢复。

三层输出：

1. `SvClientImpactBatch`：原始 touch 过滤成 generation-safe 候选；
2. `SvClientImpactCallbackBatch`：每目标两个 handler callback，最多64；
3. `SvClientImpactScriptNotificationBatch`：每目标 source/target 双向通知，最多64。

### 2.2 `SV_BuildClientImpactBatch` 的完整校验

- source 必须 `<= MaximumServerCollisionEntityNum`；
- 输入 touch 最多32，否则整个 `nullopt`；
- linkedEntities 每个都必须通过 `SV_IsCollisionEntityValid`，且 entityNum 不重复，否则整个失败；
- 用实体号布尔数组记录 linked，便于 O(1) 查目标；
- 输入 target `> EntityNumNone` 整批失败；
- target==source 或超过 server collision 上限：跳过，不失败；
- 重复 touch 按 first-seen 去重；
- 未 linked 的目标增加 `unresolvedEntityCount`，不进入 impact；
- 保留的 target 以原首次顺序写入32项数组，`impactCount` 是有效长度。

注意两种上限语义不同：source/linked 用 `MaximumServerCollisionEntityNum`；原始 target 先允许到 `EntityNumNone`，再在具体候选阶段过滤。`inputTouchCount` 保留原始数量，`impactCount` 不是它，`unresolvedEntityCount` 也不含自碰/越界/重复。

### 2.3 callback 顺序仍是显式策略

`TargetThenSource`（BO1/Ghosts）与 `SourceThenTarget`（BO2）都可由调用方选。每次 contact 固定1。

防御性重建时：

- source 越界、impactCount>32 整批失败；
- target 越界、等于 source、重复，整批失败；
- 未识别 enum default 失败。

Script notification 固定 source→target，每 touch 两条，同样严格验证。glass touch、原生 handler 绑定、生产 script lifetime/notify 语义仍是 TODO，不能把“生成64条计划”理解成玻璃和原生触碰已完整接通。

## 三、伤害公共领域与 obituary 参数

### 3.1 核心数量

- `MaximumGameClients = 18`
- `MaximumGameEntities = 2048`
- `MethodOfDeathCount = 20`
- `HitLocationCount = 21`

20个 MOD 的完整顺序：

```text
0 UNKNOWN          1 PISTOL_BULLET    2 RIFLE_BULLET
3 EXPLOSIVE_BULLET 4 GRENADE          5 GRENADE_SPLASH
6 PROJECTILE       7 PROJECTILE_SPL   8 MELEE
9 HEAD_SHOT       10 GAS             11 DOGBITE
12 SPECIAL_ATTACK 13 CRUSH           14 FALLING
15 SUICIDE        16 TRIGGER_HURT    17 EXPLOSIVE
18 IMPACT         19 PUNISH
```

源码同时修正旧注释：命中位置名称表实际有20项（0 none、1 helmet、2 head、3 neck、4/5 torso、6..11 arm/hand、12..17 leg/foot、18 gun、19 shield）。`HitLocationCount=21` 仍是原生 WeaponDef multiplier 数组读取长度，未证明可缩到19或20；不要把“名称表20项”和“数组21项”混为一谈。

### 3.2 死亡动画条件是整数值，不是位旗

`SvDeathAnimationConditions`：

- hitLocation：0 torso、1 head、2 neck、3 legs；
- damageType：0 bullet、1 explosion light、2 explosion；
- hitDirection：0 front、1 left、2 right、3 back。

partGroup 映射常量：helmet1/head2/neck3 属头部语义，腿为12..17；其他默认 torso。所有 condition 是 `ANIM_CONDTYPE_VALUE`，不能按 bitmask 处理。

### 3.3 obituary 是12-bit参数双命名空间

`CG_Obituary` 对 `parm & 0xFFF` 判断：

- `< 1700`：weapon asset index，读取 WeaponDef killIcon；
- `>= 1700`：`1700 + methodOfDeath`，只有8种 MOD 有专门图标：
  - 8 melee、9 headshot、11 dogbite、13 crush、14 falling、15 suicide、16 trigger_hurt、18 impact。
- 其他 MOD 即使>=1700也走 generic `killicondied`。
- `SV_ObituaryEventParameter` 对有专属图标者发 `1700+MOD`；其他发 weapon index；weapon=0 或>=1700则发1700+UNKNOWN。

静态断言：melee=1708、headshot=1709、impact=1718；rifle bullet + weapon1260仍发1260；rifle bullet + weapon0发1700。

源码注释用145条 dm obituary 佐证：124条直接 weapon，12条1708，8条1709，1条1718。这是“零售何时选择方法图标”的样本证据，不是所有模式都必然同分布。

paint helper：

- bullet paint：pistol/rifle/headshot；
- explosive paint：explosive bullet、grenade、grenade splash、projectile、projectile splash、explosive。

## 四、伤害 payload 的不可变事务边界

### 4.1 能力视图与状态

- `SvDamageablePlayerView`：entityNum + clientNum；
- `SvDamageableEntityView`：entityNum + generation + kind + 是否使用 weapon hit-location multipliers；
- generation 用于防止排队的命中在槽位复用后伤到新实体；
- `SvEntityDamageState`：kind、health、canTakeDamage、cannotDie、stageIndex；
- `SV_IsEntityDamageStateValid` 只要求 `health > 0`，用于注册活体 owner；终态可留作 status，但不再导出为可伤害能力。

### 4.2 player payload 校验

`SV_IsPlayerDamagePayloadValid` 检查：

- 四个 limits 都非零；
- targetClientNum < maximumClients；
- optional inflictor/attacker 若存在，< maximumEntities；
- damage > 0；
- weaponAssetIndex <= MaximumWeaponAssetIndex（**这里允许0**，具体构造器另有限制）；
- MOD、hitLocation 在各自 limits 内；
- optional point/direction 所有分量 finite。

它不检查 damageFlags/timeOffset/boneIndex 的额外语义，也不改 health/knockback；这些要么由生产者/脚本负责，要么尚未恢复。

### 4.3 `SV_BuildPlayerDamagePayload`

构造器比通用 validator 更严格：

- target<18，inflictor/attacker<2048；
- baseDamage>0；
- multiplier finite 且 `[0,20]`；
- MOD<20，hitLocation<21；
- weapon>0，唯一例外是 FALLING，因为摔伤没有 firing weapon；
- 所有输入向量 finite；
- scaled=baseDamage*multiplier 必须 finite 且 `< 2147483648.0f`；
- 转 int32 后 `max(1, damage)`。

因此 multiplier=0 仍产生1伤害，而不是0；这是当前明确策略。负 scaled 不可能由合法输入产生。浮点边界检查放在转换前，避免 overflow UB。

Entity payload 当前还要求 weapon>0，注释明确普通子弹是当前生产者；radius/missile/melee/script 需要另外的政策，不应套用此函数假装通用。

## 五、Destructible：支持目录、状态溢出与提交后表现

### 5.1 仅7种 IW4-derived 定义

| type | 各阶段 health | destroyed model |
|---|---|---|
| `toy_tv_flatscreen_wallmount_01` | 1, 200 | 无；第2阶段 replacement=`ma_flatscreen_tv_wallmount_broken_01` |
| `toy_transformer_small01` | 75,75,150,250,400 | `utility_transformer_small01_dest` |
| `toy_light_ceiling_fluorescent_single` | 150 | `me_lightfluohang_single_destroyed` |
| `vehicle_80s_sedan1_red` | 250,200,100,300,400 | red_destroyed |
| `vehicle_80s_sedan1_green` | 同上 | green_destroyed |
| `vehicle_80s_sedan1_brn` | 同上 | brn_destroyed |
| `vehicle_pickup` | 300,200,100,300,400 | `vehicle_pickup_destroyed` |

按精确 type 字符串匹配。tropical/ratnest02/tubetvsound/ceiling-fan 等没有 title-local 证据的变体明确不支持。

### 5.2 伤害溢出算法

合法定义要求 type 非空、stages 非空且每个 health>0。当前状态必须未 destroyed、stageIndex 合法、`0 < health <= 当前阶段满血`，damage>0。

用 int64 `remainingDamage` 循环：

1. 若 remaining >= 当前 health，扣除当前 health，进入下一阶段；
2. 到末尾则 health=0、destroyed=true，立即返回；
3. 否则下一阶段 health 重置为该阶段定义满血，记录 `enteredStages`；
4. 最终不足击穿时，从当前 health 减去 remaining。

这意味着一颗高伤害弹可跨多个阶段并执行每个 entered stage 的表现；不是简单 clamp 到当前阶段1点血。

### 5.3 表现资源先验证，mutation 后提交

- `stageModelIndexes` 必须和 stages 等长；
- 有 replacementModel 必须解析到非零 index，无名必须 `nullopt`；
- destroyedModel 同样严格；
- `stageEvents` 要么为空，要么与 stages 等长。

`SV_ApplyDestructibleEntityDamage` 要求 Destructible kind、canTakeDamage、!cannotDie、currentModelIndex!=0、stage 合法、damage>0。输出：

- 更新 health/stageIndex；
- destroyed 后 canTakeDamage=false；
- 进入 destroyed 时使用 destroyedModelIndex（若定义为空，则 mutation modelIndex 可为空）；
- 非 destroyed 时遍历 enteredStages，最后一个有 replacement 的模型生效；
- 将所有 entered stage events 顺序拼接，再拼 destroyedEvents。

注释明确**尚未表示**阶段碰撞、part/tag mutation、动画、爆炸半径伤害和车辆特殊行为；它当前是 model/event-only 计划，不等同完整 IW4 destructible。

## 六、`SvTimingAccumulator` 的精确桶边界

字段：count、totalMicroseconds、last、maximum、buckets[7]。

`record(us)` 使用 `us <= threshold` 找第一个桶：

| bucket | 范围 |
|---:|---|
| 0 | 0..1000 µs |
| 1 | 1001..2000 |
| 2 | 2001..5000 |
| 3 | 5001..10000 |
| 4 | 10001..20000 |
| 5 | 20001..50000 |
| 6 | >50000 |

平均值为整数除法 `total/count`，count=0返回0。`take()` 返回快照后把整个 window 清零，所以 Appmain 的周期日志展示的是“自上次 take 以来”的窗口，不是进程累计；total/max/count 都可能随日志间隔重置。

## 七、跨文件理解

- 子弹 trace 产生 hitLocation/MOD/weapon 后，`SV_BuildPlayerDamagePayload` 只构造不可变输入；真正的伤害、死亡、obituary 与 battlechatter 由 world/script/post-commit 阶段继续处理。
- Entity damage 比 player damage 多 generation，是因为一般 entity slot 会复用；玩家 clientNum 另有 session/spawn generation 管理，不能简单类推。
- Client impact 与 damage 都坚持“候选先验证、效果后提交”，避免同一 usercmd 后半段失败却已发出声音/换模型/改血量。
- Battlechatter 和 obituary 都利用客户端已有高带/素材，但语义不同：battlechatter 是 per-client `p` 本地声；obituary 是12-bit事件参数选择 kill icon。

## 八、本组未闭合点

1. CODOL 原生 client impact callback 顺序和 handler owner 尚未恢复。
2. glass touch 不在 client impact plan 内。
3. `HitLocationCount=21` 的真实数组长度仍应保持现状，不能凭20项名称表擅改。
4. damage builder 不包含 knockback、protection、pain、last-stand 等完整 G_Damage 行为。
5. destructible 只有7种定义且表现子集有限。
6. battlechatter 默认受众是产品分支，非零售忠实；本地声没有真实空间衰减。

**本组9个目标源码文件已读完。继续 `server_mp` 的 entity/native characterinfo/native pmove 等文件。**
