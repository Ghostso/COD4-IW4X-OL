# 409 · **"一个暂停在模式上的游戏"** —— 从 `use` 键到电池：`6/5` 的倍数、三个"静默的洞"、`SvTrace` 的边沿触发纪律

## 一、范围

本报告学习 `sv_main_mp.cpp` 7250–8600 行（`spawnPodiumFigures` 余下 + `holdMatchCompletionState` + SD 的 trace helper 与 `completeSdRound`/`advanceSdRound`）。

## 二、**`podiumFallbackModel` 的"一个角色部件不是身体"**（本组最重要的一段）

### 2.1 那段

```php
// A FIGURE NEEDS A BODY, NOT WHATEVER RESOLVES FIRST. The first
// version took the first of the player's five component models that
// this map's band publishes, and on mp_rust_long that is
// `hea_socomb_sc_m` -- a HEAD. Section 67 names the slots
// (0 cha, 1 fpa, 2 boo, 3 fja, 4 han, 5 hea, 6 ves, 7 heg) and the
// demo's sixteen precaches carry an `fpa_` for every one of its
// three players, so `fpa_` is the body and it is what a base model
// has to be.
//
// Preference order, most specific first:
//   1  this player's OWN fpa_ model, if the band publishes it
//   2  the band's own fpa_ model -- a generic body, right shape,
//      wrong outfit, and section 124 says the outfit is field 49's
//      job anyway
//   3  any of this player's models that resolves, so a wrong figure
//      still beats no figure
```

### 2.2 十八层

```text
1. **一个人偶需要【一个身体**】，不是"什么先解出就用什么"**
2. ⇒ **第一版取了这个玩家的五个部件模型里【这个地图带发布】的第一个**
3. ⇒ **而在 `mp_rust_long` 上那是 `hea_socomb_sc_m`** —— **一个【头**】**
4. ⇒ **第 67 节命名了槽位**：
      · `0` cha / `1` fpa / `2` boo / `3` fja
      · `4` han / `5` hea / `6` ves / `7` heg
5. ⇒ **而 demo 的十六个预缓存【为它的三个玩家每一个都带一个 `fpa_`**】**
6. ⇒ **所以 `fpa_` 是【身体**】**
7. ⇒ **而它是一个基础模型【必须要是】的东西**
8. ⇒ **偏好顺序，最具体优先**：
      · **① 这个玩家【自己的】** `fpa_` 模型（若带发布它）
      · **② 【带自己的】** `fpa_` 模型 —— 一个通用身体，形状对，服装错
      · **③ 这个玩家【任何】能解出的模型** —— **一个错的人偶仍然胜过一个没有人偶**
```

### 2.3 ⭐⭐⭐ **"一个错的人偶仍然胜过一个没有人偶"**

**✅ 与 §407 的"不猜数"**相反** —— 但**不矛盾**。**

**⇒ 三层**：
```text
§407  `\ent\<n>` 的 `n`：**拿不到就跳过**（因为一个错的号会指到【另一个实体】）
§409  人偶模型：**任何能解出的都用**（因为一个错的模型只是【形状/服装错】）
⇒ **⇒ 区别在【错误的后果是否可逆/无害**】
```

**✅ ⭐ **一个极精确的"什么时候可以退而求其次"的判据**。**

**⚠ 而"槽位 `5` 是 `hea_`"⇒ **而头是槽位 5**。**

**✅ 与 §403 的 `"2|9|5|1"`**不同（这是**一个编号表**）。

### 2.4 而**"而 demo 说基础模型是【空的】"**

```php
// AND THE DEMO SAYS THE BASE MODEL IS EMPTY. All three of retail's
// podium figures carry modelIndex 121, and 121 in this build's model
// index space is `tag_origin` -- a model with no mesh at all. The
// character is built ENTIRELY from field 49 and that client's own
// clientInfo ...
//
// So the preference order below is a FALLBACK LADDER now, not the
// policy. It stays because it is what runs when a map's band does
// not publish tag_origin ... Section 125 reasoned `fpa_` was "the body";
// the model table says slot 4 is LEGS and slot 3 is the torso, and retail
// uses neither.
```

**⇒ 十二层**：
```text
1. **零售三个人偶【全部】携带 `modelIndex 121`**
2. ⇒ **而这个 build 的模型索引空间里 `121` 是 `tag_origin`**
3. ⇒ **⇒ 【一个完全没有网格的模型**】**
4. ⇒ **角色【完全】从字段 49 与那个客户端自己的 `clientInfo` 构建**
5. ⇒ **那就是为什么十六个 `|` 预缓存骑在旁边**
6. ⇒ **而为什么【没有任何东西在实体上命名一个服装**】**
7. ⇒ **所以偏好顺序现在是一个【回退梯子**】，不是策略**
8. ⇒ **它留着因为它是一张地图的带【不发布 `tag_origin` 时】跑的东西**
9. ⇒ **第 125 节推理 `fpa_` 是"身体"**
10. ⇒ **而模型表说【槽位 4 是腿、槽位 3 是躯干**】**
11. ⇒ **而零售【两个都不用**】**
```

### 2.5 ⭐⭐⭐ **"槽位 4 是腿、槽位 3 是躯干，而零售两个都不用"**

**✅ 这是本报告里**最完整的一次自我更正**。**

**⇒ 三层**：
```text
第 67 节（旧）：`3` fja / `4` han ⇒ **没有语义**
第 125 节（旧）：`fpa_` = 身体 ⇒ **错**
模型表（新）：`3` = 躯干、`4` = 腿 ⇒ **而零售用【都不**】
⇒ **⇒ 所以正确答案是【都不用**】：基础模型是 `tag_origin`
```

**✅ 与 §407 的"`number` vs 实体索引"**同族（**第二次"术语表决定结论"）。**

**⚠ 而"索引 `121` 是【这张地图的**】"**

**✅ 与 §408 的"`_tp` 在【地图自己的 fastfile】"**完全同族（**第三次"索引是逐地图的"）。**

**⇒ 三层**：
```text
`121` = `tag_origin` 【在这张地图的模型带上】
⇒ **而它是【按名字解得**】的（`modelResolver_(PodiumBaseModelName)`）
⇒ **⇒ 所以代码【从不硬编码 121**】
```

**✅ ⭐ **"按名字从不按零售的数字"** —— **第五次"按名字不用数字"。**

**⇒ 三层**：
```text
§403  `a 1198` 按武器号（**但先检查是否拥有**）
§407  `\ent\<n>` 用实体索引（**不猜**）
§408  `_tp` 按 `<map>_tp` 名字
§409  `tag_origin` 按名字解索引
```

## 三、**`6/5` 的电池倍数**（本组第二重要）

### 3.1 那段

```php
// Retail's HUD divides the raw battery numerator by 1.2*1000. Door KVP
// costs are display units, so a 1000 door consumes 1200 raw battery.
constexpr std::uint32_t BatteryMultiplierNumerator = 6;
constexpr std::uint32_t BatteryMultiplierDenominator = 5;
const auto rawCost64 =
    static_cast<std::uint64_t>(trigger.cost) * BatteryMultiplierNumerator /
    BatteryMultiplierDenominator;
if (rawCost64 > std::numeric_limits<std::uint32_t>::max())
    return;
```

### 3.2 十四层

```text
1. **零售的 HUD 把原始电池分子【除以 `1.2 * 1000`**】**
2. ⇒ **门的 KVP 成本是【显示单位**】**
3. ⇒ **所以一个 `1000` 的门【消耗 `1200` 原始电池**】**
4. ⇒ **`BatteryMultiplierNumerator = 6`**
5. ⇒ **`BatteryMultiplierDenominator = 5`**
6. ⇒ **`rawCost = cost * 6 / 5`**
7. ⇒ **`int64` 中间量**（**防溢出**）
8. ⇒ **`if (rawCost64 > UINT32_MAX) return;`**（**一个显式的溢出丢弃**）
```

### 3.3 ⭐⭐ **"`6/5` 而不是 `1.2`"**

**✅ 与 §398 的"`battery_multiplier` 是 `1.2` 而 `sub_466450` **除以**它"**完全闭合 ✓

**⇒ 三层**：
```text
§398：客户端 `sub_466450` 用 `battery_multiplier`（=1.2）做**除法**
§409：服务端把显示成本 **乘 6/5**（=1.2）得到原始电池
⇒ **⇒ 两端【同一个 1.2，方向相反**】
```

**✅ ⭐ **一个"两端互逆"的完整闭合**。

**⚠ 而"用整数 `6/5` 而不是浮点 `1.2`"⇒ **一个精确的选择**。**

**⇒ 三层**：
```text
浮点 `1.2` ⇒ **`1000 * 1.2 = 1200.f`** 但**浮点误差在某些值上会 `1199.9999`**
整数 `6/5` ⇒ **`1000*6/5 = 1200` 精确**
⇒ **⇒ 所以【整数算术消除浮点误差**】
```

**✅ ⭐ **一个"用整数而不是浮点"的确切理由**。

**⚠ 而"`int64` 中间量 + 显式溢出检查"⇒ **两层防护**。**

**✅ 与 §406 的"`uint8` 截断"**同族（**第二次"整数宽度"）。**

## 四、SD 的"三个静默的 `return false`"（本组第三重要）

### 4.1 那段

```php
// SDTRACE: three silent `return false`s used to make "the round never
// advanced" indistinguishable from "this was not called at all".
```

### 4.2 十二层

```text
1. **三个静默的 `return false`** ⇒ **过去让"回合从未推进"与"这个函数根本没被调用"【无法区分**】**
2. ⇒ **所以现在三种分支各有一条 trace**：
      · **`advance-wait`**（时长不够）
      · **`advance-blocked`**（门控位）
      · **`advance-blocked reason=bomb_runtime` / `begin_next_round_refused`**
3. ⇒ **而它们【各自有不同的去重**】：
      · **`advance-wait`：每秒一次**（`lastWaitedSecond`）
      · **`advance-blocked`：位掩码变化时**（`lastBlockedBits`）
```

### 4.3 ⭐⭐ **"每秒一次，不是每 tick 一次"**

```php
// ONCE PER WHOLE SECOND, NOT ONCE PER TICK. advanceSdRound() runs
// from the frame loop, so the first cut of this trace wrote ~800
// lines a minute and the log itself started to stall
// (`LOGSTALL ... prefix=SDTRACE|advance-blocked`).
```

**⇒ 七层**：
```text
1. **每秒一次，不是每 tick 一次**
2. ⇒ **`advanceSdRound()` 从【帧循环】跑**
3. ⇒ **所以第一版写了【每分钟约 `800` 行**】**
4. ⇒ **而【日志本身开始停滞**】**（`LOGSTALL ... prefix=SDTRACE|advance-blocked`）
5. ⇒ **所以按秒去重**
```

**✅ ⭐ **"日志本身开始停滞"** —— 一个**可观测的二次故障**。**

**✅ 与 §402 的"`INF` 被丢弃 ⇒ 窗口完全没有证人"**相反**（这是**日志太多而非太少**）。

**⇒ 三层**：
```text
§402  太少 ⇒ **没有证人**
§409  太多 ⇒ **日志停滞**（`LOGSTALL`）
⇒ **⇒ 两个方向都会毁掉取证**
```

**✅ ⭐ **一个完整的双向教训**。

### 4.4 而**"位掩码变化时"的去重**

```cpp
static unsigned lastBlockedBits = ~0u;
const unsigned blockedBits =
    (sdRoundStatus_.configured ? 1u : 0u) |
    (sdRoundStatus_.completed ? 2u : 0u) |
    (matchStatus_.completed ? 4u : 0u);
if (blockedBits != lastBlockedBits) { ... }
```

**⇒ 五层**：
```text
1. **六位掩码**（`configured`/`completed`/`matchCompleted`/`bombConfigured`/`pickupTrigger`/`contactRunner`）
2. ⇒ **只在【位组合变化】时打印**
3. ⇒ **所以一条记录说明【哪一位刚刚变了**】
4. ⇒ **`~0u` 初值 ⇒ 第一次一定打印**
5. ⇒ **⇒ 一个"边沿触发在复合状态上"的实例**
```

**✅ ⭐ **"边沿触发在复合状态上"** —— 与 §402 的"`PMFLAGS|` 在变化时打一行"**同族（**第二次）。**

**⇒ 三层**：
```text
§402  `PMFLAGS|`：**单值**变化
§409  `cmd-gate-closed`/`advance-blocked`：**位掩码**变化
⇒ **⇒ 同一纪律，复杂度递增**
```

**⚠ 而"`static` 局部变量"⇒ **一个隐藏的全局**（跨客户端共享）。**

**✅ 与 §407 的"`checkDeathAnimationRisk` 里 `static` 的 map"**同族（**第二次"`static` 局部 ⇒ 全局"）。

**⇒ 三层**：
```text
§407  `animatedThisLife` / `reports` ⇒ **按 clientNum 索引 [所以正确】**
§409  `lastBlockedBits` ⇒ **全局一个** [因为门控是**全局的** ⇒ 正确】
```
**✅ 而 §409 的 `lastWaitedSecond` 也是全局 —— **正确的原因同上**。

**⇒ 而 `lastNoTargetPhase` 是 **`std::map<clientNum, unsigned>`** ⇒ **按客户端**。

**✅ ⭐ **一个"去重粒度必须匹配状态粒度"的完整模式**。

### 4.5 而**"USE 键的黑洞"**

```php
// SDTRACE: THE USE KEY'S BLACK HOLE. Every committed command lands here
// first, so this used to return in silence -- "I pressed use and nothing
// happened" and "the command never arrived" produced identical evidence.
```

**⇒ 五层**：
```text
1. **`use` 键的黑洞**
2. ⇒ **每一个 committed 命令【先落在这里**】**
3. ⇒ **所以它过去【静默地返回**】**
4. ⇒ **⇒ "我按了 use 什么也没发生" 与 "命令从未到达"【产生相同的证据**】**
5. ⇒ **所以加 `cmd-gate-closed` 的六位掩码 trace**
```

**✅ 与 §402 的"等待 vs 拒绝"**同族（**第九次"沉默的诊断"）。**

**⇒ 三层**：
```text
拒绝 ⇒ **有内容**（可以读它拒绝了什么）
等待/静默 ⇒ **没有内容**
⇒ **⇒ 而第三条路：**命令从未到达** —— 也是静默**
```
**✅ ⭐ **一个比 §402 更细的三分**（**到达但被拒 / 到达但等待 / 从未到达**）。

## 五、**`sdTrace` 的"名字不是数字"**

```php
// Names, not numbers: a flow log that prints "phase=3" costs the reader a
// cross-reference on every line. Everything here is a pure formatter and
// changes no state.
```

**⇒ 四层**：
```text
1. **名字不是数字**
2. ⇒ **一个打印 `phase=3` 的流日志【在每一行上花掉读者一次交叉引用**】**
3. ⇒ **这里的每一样都是【纯格式化器**】**
4. ⇒ **且【不改变任何状态**】**
```

**✅ ⭐ **"在每一行上花掉读者一次交叉引用"** —— 一个**精确的可读性成本**。**

**⚠ 而"纯格式化器且不改变状态"⇒ **一个"取证不能改变被取证对象"的纪律**。**

**✅ 与 §402 的"`PMFLAGS|` 纯只读观测"**完全同族（**第二次"取证必须只读"）。**

**⇒ 三层**：
```text
八个名字函数：`sdTeamName` / `sdBombPhaseName` / `sdRoundEndReasonName`
`sdOriginText`：**模板**（因为 `origin` 成员在三种结构里别名不同）
`sdTrace`：**统一前缀 `SDTRACE|`**
```

**✅ 而"模板 on purpose"⇒ **一个明确的技术选择**。**

```cpp
// Template on purpose: the origin members are indexed float triples, but the
// exact alias differs between the trigger, player-state and home-origin
// structs, and a fixed parameter type would tie this trace to one of them.
```

**✅ ⭐ **"一个固定的参数类型会把这条 trace 绑死到其中一个"** —— **一个精确的泛型理由**。

## 六、**`completeSdRound` 的"抛异常而不是静默"**

```cpp
if (!sdRoundStatus_.configured || sdRoundStatus_.completed ||
    matchStatus_.completed ||
    (winner != SvTeam::Tf && winner != SvTeam::Sc) ||
    reason == SvSdRoundEndReason::None)
{
    throw std::logic_error("invalid authoritative SD round completion");
}
```

**⇒ 六层**：
```text
1. **五个前置条件全部不满足 ⇒ 【抛 `logic_error`**】**
2. ⇒ **而【不是静默返回**】**
3. ⇒ **理由：`completeSdRound` 是【权威的**】回合完成入口**
4. ⇒ **一个不合法调用说明【调用方有 bug**】**
5. ⇒ **⇒ 所以崩溃比静默好**
```

**✅ 与 §408 的"故意的无闸写入器"**相反**（那里**为了避免静默丢数据**，这里**为了避免静默错数据**）。

**⇒ 三层**：
```text
§408  `addClientGp` ⇒ **无闸**（因为闸会丢合法数据）
§409  `completeSdRound` ⇒ **抛异常**（因为不合法调用是 bug）
⇒ **⇒ 两个方向，同一个原则【不能静默**】
```

**✅ ⭐ **一个完整的"何时该抛、何时该绕"的对照**。

**⚠ 而 `setTeamScore` 失败也抛**：

```cpp
if (!clients_.setTeamScore(winner, score + 1))
    throw std::logic_error("SD round winner has no authoritative team score");
```

**✅ 与 §408 的"`podium figure SKIPPED` 记日志而不是抛"**不同（那是**可恢复的缺失**）。

**⇒ 三层**：
```text
缺数据（模型解不出）⇒ **记日志 + 跳过**（可恢复）
不合法调用 ⇒ **抛异常**（bug）
⇒ **⇒ 判据是【调用方的错还是环境的错**】
```

**✅ ⭐ **一个精确的"错误分类"**。

### 6.1 而**"`setTeamScore` 上面是唯一的写者"**

```php
// SDTRACE: the round ends exactly once per round, so this line is not rate
// limited -- and the pair of scores is what makes a wrong winner visible
// without a second run (`setTeamScore` above is the only writer).
```

**⇒ 四层**：
```text
1. **一个回合【恰好结束一次**】⇒ **所以这一行【不做速率限制**】**
2. ⇒ **而【那对比分**】是什么让一个错的赢家【不需要第二次运行就可看见**】**
3. ⇒ **（`setTeamScore` 是唯一的写者）**
4. ⇒ **⇒ 所以 `scoreBefore`/`scoreAfter` 的差【必须恰好是 `1`**】
```

**✅ ⭐ **"不需要第二次运行就可看见"** —— 一个**自校验的日志设计**。

**✅ 与 §402 的"`match complete ... tf=150 sc=31 winner=Tf` 说明判定全对"**同族（**第二次"日志自带判定依据"）。

**⇒ 三层**：
```text
`scoreBefore` / `scoreAfter` ⇒ **差必须是 1**
`winner` / `reason` ⇒ **可与比分对照**
⇒ **⇒ 两两互校**
```

## 七、**SD 的三个结算出口**（本组第四重要）

```text
出口 1：`winnerScore >= rules.winLimit`
        ⇒ matchStatus_.completed
        ⇒ winner = 本回合赢家
        ⇒ endReason = WinLimit
        ⇒ 播 matchWon / matchLost
        ⇒ **return**

出口 2：`roundsPlayed < rules.roundLimit`
        ⇒ **不结束比赛**
        ⇒ `sdSideSwitchPending_ = rules.roundSwitch && roundsPlayed % rules.roundSwitch == 0`
        ⇒ **return**

出口 3：`roundsPlayed >= rules.roundLimit`
        ⇒ matchStatus_.completed
        ⇒ winner = tf != sc ? (tf > sc ? Tf : Sc) : **None**
        ⇒ endReason = RoundLimit
        ⇒ **若 None ⇒ 双方播 draw**
        ⇒ **否则 ⇒ 赢家 matchWon / 输家 matchLost**
```

**⇒ 三个出口.**

**⚠ 而"出口 3 的平局是 `SvTeam::None`"⇒ **与 §406 的"平局不算领先"**同族（**第二次"平局是一个显式的第三值"）。

**✅ 与 §406 的"`tf == 0 && sc == 0 ⇒ return`"**不同（那是**不宣告**，这是**显式的平局结果**）。

**⇒ 三层**：
```text
announcer：平局 ⇒ **不宣告领先**（因为"领先"不存在）
SD 比赛末：平局 ⇒ **`winner = None`** 并**播 `draw`**
⇒ **⇒ 两种处理，都正确**
```

**✅ ⭐ **一个"同一个概念两种语境"的精确区分**。

### 7.1 而**"侧换在回合间，且 `roundSwitch` 是模数"**

```cpp
sdSideSwitchPending_ = matchStatus_.rules.roundSwitch &&
    sdRoundStatus_.roundsPlayed % matchStatus_.rules.roundSwitch == 0;
```

**⇒ 四层**：
```text
1. **`roundSwitch` 是【一个模数**】，不是布尔**
2. ⇒ **`roundsPlayed % roundSwitch == 0`**
3. ⇒ **⇒ 所以每 `roundSwitch` 回合换一次边**
4. ⇒ **而 `roundSwitch == 0` ⇒ 【永不换边**】（`&&` 短路）
```

**✅ 一个**极简洁的"半场"表达**。

## 八、**`evaluateSdRound` 的候选-提交模式**

```cpp
auto candidate = sdBombStatus_;
if (!SV_BeginSdBombRound(candidate, ...) || !setSdBombVisual(...))
    throw std::logic_error("armed SD round could not expose its bomb");
sdBombStatus_ = std::move(candidate);
```

**⇒ 六层**：
```text
1. **拷贝到一个 `candidate`**
2. ⇒ **在候选上做转移**（`SV_BeginSdBombRound`）
3. ⇒ **并检查视觉**（`setSdBombVisual`）
4. ⇒ **两者都成功 ⇒ 【才提交**】（`sdBombStatus_ = std::move(candidate)`）
5. ⇒ **否则【抛异常**】且 `sdBombStatus_` **不变**
6. ⇒ **⇒ 所以一个失败的转移【不留下半状态**】
```

**✅ 与 §409 四的"抛异常而不是静默"**同族（**第二次"失败必须可见"）。**

**⇒ 三层**：
```text
`advanceSdRound`：**四个 candidate**（clients/useObjects/roundStatus/bombStatus）+ **全部成功才 move**
`evaluateSdRound`：**一个 candidate**
⇒ **⇒ 同一模式，规模不同**
```

**✅ ⭐ **一个"事务式提交"的完整实现**。

**⚠ 而"`advanceSdRound` 的四个 candidate"⇒ **一个跨四个子系统的原子提交**。**

**✅ 与 §404 的"槽复用要清状态"**同族（**第四次"多子系统一致性"）。**

## 九、关键结论

1. **⭐⭐⭐ "一个人偶需要一个身体，不是『什么先解出就用什么』"** —— 第一版在 `mp_rust_long` 上取到了 `hea_socomb_sc_m`，**一个头**。
2. **槽位表**（`0` cha / `1` fpa / `2` boo / `3` fja / `4` han / `5` hea / `6` ves / `7` heg），而**模型表说槽位 3 是躯干、4 是腿**，**零售两个都不用** —— **第 125 节的"`fpa_` 是身体"是被推翻的推理**。
3. **⭐⭐⭐ "一个错的人偶仍然胜过一个没有人偶"（而 §407 的 `\ent\<n>` 是"拿不到就跳过"）** —— 区别在**错误的后果是否可逆**：错模型只是形状/服装错，错实体号会指到另一个实体。
4. **⭐⭐ "零售三个人偶全部携带 `modelIndex 121`，而 121 是 `tag_origin` —— 一个完全没有网格的模型；角色完全从字段 49 与该客户端自己的 `clientInfo` 构建"`** ⇒ **偏好顺序现在是一个【回退梯子】，不是策略**。
5. **⭐ "按名字从不按零售的数字"（`modelResolver_(PodiumBaseModelName)`）** —— 第五次"按名字不用数字"。
6. **⭐⭐ `6/5` 的电池倍数与 §398 的 `1.2` 完全互逆闭合并**：**客户端 `sub_466450` 除以 `1.2`，服务端乘 `6/5`** —— 而**用整数 `6/5` 而不是浮点 `1.2` 消除了浮点误差**（`1000*1.2` 可能出 `1199.9999`）。
7. **"`int64` 中间量 + 显式 `> UINT32_MAX ⇒ return`"** —— **两层防护**。
8. **⭐⭐⭐ SD 的"三个静默的 `return false`"让"回合从未推进"与"函数根本没被调用"无法区分** —— 第九次"沉默的诊断"，而这里是**三分**（到达但被拒 / 到达但等待 / **从未到达**）。
9. **⭐⭐ "每秒一次，不是每 tick 一次：第一版写了每分钟约 `800` 行而【日志本身开始停滞】（`LOGSTALL ... prefix=SDTRACE|advance-blocked`）"`** —— 与 §402 的"日志太少 ⇒ 没有证人"构成**一个完整的双向教训**。
10. **⭐ 去重粒度必须匹配状态粒度**：`advance-wait` 按秒、`advance-blocked`/`cmd-gate-closed` 按**六位掩码变化**（全局状态 ⇒ 全局 `static`）、`use-no-target`/`lastButtons` 按 **`clientNum`**（客户端状态 ⇒ `map<clientNum, ...>`）。
11. **"名字不是数字：一个打印 `phase=3` 的流日志在每一行上花掉读者一次交叉引用"`** —— 一个精确的可读性成本，而 **"纯格式化器且不改变状态"** 是取证纪律（第二次"取证必须只读"）。
12. **`sdOriginText` 是模板（on purpose）**：**"一个固定的参数类型会把这条 trace 绑死到其中一个结构上"`** —— 一个精确的泛型理由。
13. **⭐⭐⭐ `completeSdRound` 抛 `logic_error` 而不是静默**（五个前置条件），**与 §408 的"故意的无闸写入器"方向相反但同一原则：不能静默**。判据是**调用方的错还是环境的错**：缺模型 ⇒ 记日志跳过；不合法调用 ⇒ 抛。
14. **⭐ "`scoreBefore`/`scoreAfter` 的差必须恰好是 `1`，因为 `setTeamScore` 是唯一的写者"`** —— 一个**自校验的日志设计**（第二次"日志自带判定依据"）。
15. **SD 的三个结算出口**（`WinLimit` / 回合间 `roundSwitch` 模数换边 / `RoundLimit` 含**显式 `None` 平局**）。
16. **⭐ `roundSwitch` 是【一个模数】不是布尔**（`roundsPlayed % roundSwitch == 0`，而 `0` 短路 ⇒ 永不换边）。
17. **事务式提交**：`candidate` 拷贝 → 转移 → 检查 → **全部成功才 `move`**，否则抛且原状态不变；`advanceSdRound` 是**跨四个子系统的原子提交**。

## 十、未闭合点

- `SvDmOutcomeDelayMilliseconds` / `SvDmOutcomeDurationMilliseconds` / `SvDmPlacementLabels` 的值。
- `SvObjectiveCompletionAward` 的分值。
- `SvAssistAwardees` 的时间窗。
- `zmRawBatteryCost` 的实现。
- `SV_FactoryPerkPriceUnits` 的六个档位。
- `FactorySteamConfigString` 的索引（11990）。
- `sv_main_mp.cpp` 8600 行之前（`processLootCommittedCommand` 起始段）已读。
- `sv_main_mp.cpp` 9264 行之后未读取。
