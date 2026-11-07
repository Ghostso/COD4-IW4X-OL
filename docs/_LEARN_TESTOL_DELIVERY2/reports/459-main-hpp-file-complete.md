# 459 · **`sv_main_mp.hpp` 全文件收尾** —— "一个按键是一个电平不是一个边沿"、"一个槽每个不同的串"、`1500ms` 的三次修订

## 一、范围

本报告学习 `sv_main_mp.hpp` 1440–1793 行（`PerkLife`/`EquipmentLife` 的 `selectedLoadout` 键、`SvUiClientLife` 的完整状态、`SvDeathViewMilliseconds` 的三次修订、`lootActivateHeld_` 的"电平不是边沿"、`hintStringSlots_` 的"一个槽每串"），并收尾整个文件（**共 `1,793` 行**）。

## 二、**"`ACTIVATE` 是一个电平，不是一个边沿"**（本组最重要的一段）

### 2.1 那段

```cpp
// ACTIVATE IS A LEVEL, NOT AN EDGE. The bit stays set for as long as the key
// is down and usercmds arrive faster than anyone can let go, so without this
// one press would empty the whole ring.
std::map<std::uint32_t, bool> lootActivateHeld_;
```

### 2.2 二十层

```text
1. **`ACTIVATE` 是【一个电平**，不是一个【边沿**】**
2. ⇒ **那个位【在键按下的时候【一直设着**】**
3. ⇒ **而【usercmd 到达得比任何人能松手【更快**】**
4. ⇒ **⇒ 所以【没有这个，**一次按键【会排空整个环**】】**
5. ⇒ **⇒ 所以 `lootActivateHeld_` 记录【上一帧的**电平**】
```

### 2.3 ⭐⭐⭐ **"一次按键会排空整个环"**

**✅ 这是本报告里**最重要的一条"一个电平被当成边沿的后果**。**

**✅ 与 §413 的"`A` 的 `A_RESEND|` 只在主武器索引真的变了才补发"**不同（那是**去重**，这是**电平→边沿的转换**）。

**⇒ 三层**：
```text
`buttons & Activate` ⇒ **一个电平**（**按键期间恒真**）
而【一个拾取【应该【触发一次**】
⇒ **⇒ 所以【必须**自己**做一个上升沿**】
```

**✅ ⭐⭐⭐ **"必须自己做一个上升沿"**。

**⚠ 而"排空整个环"⇒ **一个具体的后果**。**

**⇒ 三层**：
```text
若【无电平跟踪**】⇒ **每一帧都触发一次拾取** ⇒ **一个箱子集群【被一次按键全拿走**】
⇒ **⇒ 所以【一个"环"被排空**】
```

**✅ 与 §450 的"`playsound` 只接受 `0..255`"**不同（这是**一个时序状态**）。

**⇒ 三层**：
```text
§409  **"候选-提交模式"的 `candidate`**（**一个事务状态**）
§459  **`lootActivateHeld_`**（**一个上一帧的电平**）
⇒ **⇒ 两种"跨帧状态**】
```

**✅ ⭐⭐ **一个"跨帧状态"的两例**。

### 2.4 而**同一个模式在 `zmUseActivateHeld_`**

**⇒ 六层**：
```text
`lootActivateHeld_`      ⇒ **拾取的边沿**
`zmUseActivateHeld_`     ⇒ **zm 使用键的边沿**
`barrierRepairHintTarget_`⇒ **一个当前的屏障**
⇒ **⇒ 三个独立的状态**
```

**✅ 与 §410 的"`loot BUTTONS` 的日志"**配合。

**⇒ 三层**：
```text
§410  **`loot BUTTONS client=… buttons=0x%08X activate=N`**（**一个首次变化的日志**）
§459  **`lootActivateHeld_`**
⇒ **⇒ 同一个"边沿"的两个用法**（**一个日志、一个逻辑**）
```

**✅ ⭐ **一个"边沿"的两个用法**。

## 三、**"一个槽每个不同的串，不是一个槽每个触发器"**（本组第二重要）

### 3.1 那段

```cpp
// ONE BAND SLOT PER DISTINCT STRING, not per trigger. Retail's own capture
// gives all four of zm_factory_sh's 1000-point doors the same relative index,
// and the band is only 96 wide against 54 triggers on this map alone.
std::map<std::string, std::uint16_t, std::less<>> hintStringSlots_;
```

### 3.2 二十层

```text
1. **【一个带槽每【不同的串**，不是【每触发器**】**
2. ⇒ **零售自己的捕获【给 `zm_factory_sh` 的【全部四扇 1000 点的门【同一个相对索引**】】**
3. ⇒ **而【那个带【只有 `96` 宽**】**
4. ⇒ **⇒ 对着【这张地图上【单独的 `54` 个触发器**】**
5. ⇒ **⇒ 所以【必须【按串去重**】
```

### 3.3 ⭐⭐⭐ **"零售自己的捕获给全部四扇 1000 点的门同一个相对索引"**

**✅ 这是本报告里**最重要的一条"一个测出的等价**。**

**⇒ 三层**：
```text
若不按串去重 ⇒ **`54` 个触发器【要 `54` 个槽**】
而【带【只有 `96` 宽**】 ⇒ **`54/96 = 56%`** ⇒ **接近满**
⇒ **⇒ 所以【按串去重【把一个必然的溢出**变成一个【有余量**的设计**】
```

**✅ ⭐⭐⭐ **"把一个必然的溢出变成一个有余量的设计"**。**

**⚠ 而"全部四扇 1000 点的门同一个相对索引"⇒ **一个可测的等价**。**

**⇒ 三层**：
```text
四扇门 ⇒ **同一个**相对索引**
⇒ **⇒ 所以【按串去重【与零售一致**】
```

**✅ 与 §458 的"刻意与客户端自己的分配器同一个形状"**同族（**第四次"对齐既有实现**）。

**⇒ 三层**：
```text
§412  **bot 对齐真实弹道**
§447  **`actorfire` 对齐同样的参数**
§458  **提示串分配器对齐 `sub_4EC5D0`**
§459  **按串去重【与零售一致**】
⇒ **⇒ 四次"对齐**】
```

**✅ ⭐⭐ **一个"对齐"的四例表**。

### 3.4 而**`cursorHintTrigger_` 被"加宽到 32 位以持有 loot 键"**

```cpp
// What each client is currently being told, so the wire only carries a change.
// WIDENED TO 32 BITS to hold a loot key as well as a trigger index -- one
// function owns cursorHint and it now has two kinds of answer to remember.
// SvLootHintKeyBase separates them; a trigger index can never collide with it.
std::map<std::uint32_t, std::uint32_t> cursorHintTrigger_;
```

**⇒ 十二层**：
```text
1. **每个客户端【当前被告知的**东西**】
2. ⇒ **⇒ 所以【线上只携一个变化**】
3. ⇒ **⚠ 【加宽到 `32` 位**以持有【一个 loot 键**与一个【触发器索引**】】
4. ⇒ **因为【一个函数拥有 `cursorHint` 而现在它【有两种答案要记**】】
5. ⇒ **⇒ `SvLootHintKeyBase` **分开它们**】**
6. ⇒ **⇒ 一个触发器索引【永不**与它碰撞**
```

**✅ 与 §416 的"`SvLootHintKeyBase = 0x10000u`"**完全闭合 ✓

**⇒ 三层**：
```text
§416  **"`SvLootHintKeyBase = 0x10000u`；`SEPARATES A LOOT ANSWER FROM A TRIGGER ANSWER`；触发器索引小；**没有东西能通过数触发器到达这一位**"
§459  **"加宽到 `32` 位... `SvLootHintKeyBase` 分开它们；一个触发器索引永不与它碰撞"**
⇒ **⇒ 同一个设计的两次**
```

**✅ ⭐⭐⭐ **"同一个设计的两次"**。

**⚠ 而"只有线上携一个变化"⇒ **一个"只发变化"的原则**。**

**✅ 与 §430 的"`SV_SetConfigString` 的 `existing->second == value ⇒ return 0`"**同族（**第三次"只发变化**）。

**⇒ 三层**：
```text
§341  **"一个未变的客户端完全不提"**
§430  **"值未变 ⇒ 返回 `0`"**
§459  **"线上只携一个变化"**
⇒ **⇒ 三次"只发变化**】
```

**✅ ⭐⭐ **一个"只发变化"的三例表**。

## 四、**`SvDeathViewMilliseconds` 的三次修订**（本组第三重要）

### 4.1 那段

```cpp
// 28400: how long the dead player looks at their own body before the
// killcam replay starts. 2697 never names a number for it ...
// so this is the operator's 2 s, matching the shortest
// 2697 camtime (2.5 s) without making the death hold feel long.
// 1200 ms, not 2000: cha.lua requests respawn at 3000 ms and the killcam is
// armed at death + 1500 ms (SvKillCamDelayMilliseconds). A longer body view
// would swallow the killcam entirely -- measured in this very file: the
// branch that fires the killcam continues while the view is still up.
// 28800: 1500 ms, not 1200. 2697's "let the player watch themselves die"
// block is `wait(0.25) + wait(0.25) + wait(1.0)` before
// `death_delay_finished` (`_damage.gsc:857-869`); the killcam only starts
// after that.
static constexpr std::uint32_t SvDeathViewMilliseconds = 1'500;
```

### 4.2 二十四层

```text
1. **三次修订**：`2000` → `1200` → **`1500`**
2. ⇒ **而【每一次都有一个理由**】**
3. ⇒ **第一次 ⇒ "操作员的 `2` 秒，匹配 `2697` 最短的 `camtime`（`2.5` 秒）"**
4. ⇒ **第二次 ⇒ "`1200` 不是 `2000`：`cha.lua` 在 `3000ms` 请求重生而 killcam 在【死亡 `+1500ms`】被武装 ⇒ 一个更长的身体视角【会完全吞掉 killcam**】"**
5. ⇒ **第三次 ⇒ "`1500` 不是 `1200`：`2697` 的『让玩家看自己死』块是 `wait(0.25) + wait(0.25) + wait(1.0)` 在 `death_delay_finished` 之前 ⇒ killcam 只在【那之后**】开始"**
6. ⇒ **⇒ 所以【`0.25 + 0.25 + 1.0 = 1.5` 秒**】
```

### 4.3 ⭐⭐⭐ **"`0.25 + 0.25 + 1.0 = 1.5`"**

**✅ 这是本报告里**最漂亮的一条"一个源码的相加**。**

**⇒ 三层**：
```text
`wait(0.25)` + `wait(0.25)` + `wait(1.0)` ⇒ **`1.5` 秒**
⇒ **⇒ 所以【`1500` 是【一个源码的加法**，不是一个估计**】
```

**✅ ⭐⭐⭐ **"`1500` 是一个源码的加法，不是一个估计"**。**

**⚠ 而"`cha.lua` 在 `3000ms` 请求重生"**⇒ **`3000 = 1500 (body) + 1500 (killcam delay)`** ✓

**⇒ 三层**：
```text
`SvDeathViewMilliseconds = 1500`
`SvKillCamDelayMilliseconds = 1500`
⇒ **`1500 + 1500 = 3000`** ⇒ **正好 `cha.lua` 的重生请求**
```

**✅ ⭐⭐⭐ **"两个 `1500` 相加正好是那个重生请求"** —— 一个**极精确的闭合**。

**✅ 与 §404 的"两个串联的 `1500ms`"**完全闭合 ✓

**⇒ 三层**：
```text
§404  **"两个 `1500ms`：身体相机 + 回放延迟"**
§459  **"`1500 + 1500 = 3000` = `cha.lua` 的重生请求"**
⇒ **⇒ 一个完整的算术闭合**
```

**✅ ⭐⭐⭐ **"一个完整的算术闭合"**。

### 4.4 而**"一个更长的身体视角会完全吞掉 killcam"**

**⇒ 六层**：
```text
若 `deathView > 1500` ⇒ **killcam 在 `1500` 武装而【身体视角还在**】
⇒ **⇒ 而【那个触发的分支【在视角还在的时候继续**】（**实测**）
⇒ **⇒ 所以【会吞掉**】
```

**✅ 与 §404 的"最终击杀得不到私有回放"**同族（**第二次"一个窗口的竞争**）。

**⇒ 三层**：
```text
§404  **"延迟是常数，选择是那个竞赛"**
§459  **"`deathView` 与 killcam 的 `1500` 竞争"**
⇒ **⇒ 两次"窗口的竞争**】
```

**✅ ⭐⭐ **"窗口的竞争"两例**。

## 五、**`PerkLife` 的 `selectedLoadout` 键**（本组第四重要）

### 5.1 那段

```cpp
// WHICH CLASS THIS LIFE'S PERKS WERE RESOLVED FOR. An in-game
// backpack switch changes SvClient::selectedLoadout without bumping
// spawnGeneration, so without this key the perks were resolved once
// on spawn and never again -- the client switched class and kept the
// old three perks. A change here re-resolves exactly like a spawn
// generation bump does.
std::string selectedLoadout{};
```

**⇒ 十二层**：
```text
1. **这条命的 perk 是【为哪个职业**解析的**
2. ⇒ **一个比赛中背包切换【改变 `selectedLoadout` 而【不提 `spawnGeneration`**】】
3. ⇒ **⇒ 所以【没有这个键，perk 在出生时解析一次而【永不再**】】**
4. ⇒ **⇒ 客户端【换了职业而【保留旧的三个 perk**】】**
5. ⇒ **⇒ 这里的变化【重解析**，与一个 `spawnGeneration` 提升【完全一样**】】
```

### 5.2 ⭐⭐⭐ **"两个键：`spawnGeneration` 与 `selectedLoadout`"**

**✅ 与 §434 的"`clientGenerationIsActive` 的四个分支"**不同（这是**一个复合键**）。

**⇒ 三层**：
```text
`spawnGeneration` ⇒ **一次出生**
`selectedLoadout` ⇒ **一次职业切换**
⇒ **⇒ 所以【两个"生命事件**】**
```

**✅ 与 §407 的"`lifeState` 的两个边沿"**同族（**第三次"一个对象两个生命周期**）。

**⇒ 三层**：
```text
§407  **bot 的 `lifeState`（death / respawn 两个边沿）**
§422  **`setPlayerCanTakeDamage` 的"代次作用域"**
§459  **`PerkLife` 的 `spawnGeneration` + `selectedLoadout`**
⇒ **⇒ 三次"两个生命周期**】
```

**✅ ⭐⭐ **"两个生命周期"三例表**。

**⚠ 而"`EquipmentLife` 有同样的键"**⇒ **一个一致的模式**。

**⇒ 三层**：
```text
`PerkLife` ⇒ `spawnGeneration` + `selectedLoadout`
`EquipmentLife` ⇒ **同样**
⇒ **⇒ 所以【两个结构【同一个键**】
```

**✅ ⭐⭐ **"两个结构同一个键"**。

## 六、`SvUiClientLife` 的二十三个字段

**⇒ 分组**：

```text
连接三态     connected / seen / alive / everAlive
prematch     prematchUntil / prematchTickSecond / prematchStageTwoAt
             prematchStage / prematchVisionStage
spy 四阶段   spyPhase / spyPhaseUntil / spyRoundEndsAt / spyRoundNumber
pmFlags 探针 pmFlagsLogged / pmFlagsLoggedValid
工厂         classMenuResponseSequence
Wetwork      firstSpawnAt / wetworkActivationAt / wetworkSpawnTime
死亡         killCamAt / killCamActive / deathViewUntil
```

**⇒ 六个组，二十三字段。**

### 6.1 ⭐⭐⭐ **"`pmFlagsLogged` 只用于打到日志的去重，不参与任何游戏逻辑"**

**⇒ 六层**：
```text
1. **`pmFlagsLogged`/`pmFlagsLoggedValid`**
2. ⇒ **只用于【打到日志**的去重**
3. ⇒ **⇒ 【不参与任何游戏逻辑**】**
4. ⇒ **⇒ 而【目的**是"先拿到『开局/复活之后 `pm_flags` 到底取什么值、什么时候变』，【再决定**出生保护怎么实现**】"
```

**✅ 与 §402 的"`PMFLAGS|` 纯只读观测，不改任何状态"**完全闭合 ✓

**⇒ 三层**：
```text
§402  **`PMFLAGS|` 一个只读观测**
§459  **`pmFlagsLogged` 一个只用于日志去重的字段**
⇒ **⇒ 一个完整的"取证字段"**
```

**✅ ⭐⭐⭐ **"一个取证字段"** —— 而 **§402 说"我方一帧都没观测过"**，**§459 给出了那个观测的实现**。

### 6.2 而**"spy 的 7 回合"**

```cpp
// 零售 spy 每局 **7 回合**（`s scr_spy_roundlimit "7"`，`scr_round` 1..7，终局后回 "0"）
std::uint8_t spyRoundNumber{};
```

**⇒ 三层**：
```text
`scr_spy_roundlimit = 7`
`scr_round` ⇒ `1..7`
终局后回 `"0"`
⇒ **⇒ 所以【`7` 是一个【测出的值**】
```

**⚠ 而 §403 的"spy 的五阶段状态机"**⇒ **现在有第六个维度：回合。**

**⇒ 三层**：
```text
§403  **spy 的五个阶段**（0 prematch / 1 pickup / 2 assign_role / 3 结算 / 4 回合间 / 5 终局）
§459  **`spyRoundNumber`（`1..7`）**
⇒ **⇒ 所以【阶段是【一个回合内**的**，而回合是【跨阶段**的**】
```

**✅ ⭐⭐⭐ **"阶段是一个回合内的，而回合是跨阶段的"** —— 一个**二维的状态机**。

## 七、`SvMatchEndKill` 的"最后一个击杀必须在重生抹掉它之前存活"

```cpp
// THE MATCH-END KILLCAM REPLAYS THE LAST KILL OF THE MATCH, so the last
// one has to survive the respawn that erases it from killCamSubjects_.
// Retail's match-end frame names a killer (killCamClientNum 2, and the
// same client on `L 2 7`) and a victim (killCamLookAtEntity 8) that are
// not the winner and not the recording client, which is what a final
// kill looks like.
struct SvMatchEndKill
{
    std::uint32_t killerClientNum{};
    std::uint32_t victimClientNum{};
    std::uint32_t serverTime{};
};
std::optional<SvMatchEndKill> lastMatchKill_;
```

**⇒ 十层**：
```text
1. **比赛末的回放【回放那场比赛的最后一个击杀**】**
2. ⇒ **⇒ 所以【最后一个【必须在【那个把它从 `killCamSubjects_` 抹掉的【重生**】之前存活**】**
3. ⇒ **零售的比赛末帧【命名一个凶手**】`killCamClientNum 2` + `L 2 7`**
4. ⇒ **与一个受害者**】`killCamLookAtEntity 8`**
5. ⇒ **⇒ 而它们【既不是赢家也不是录制客户端**】**
6. ⇒ **⇒ 那正是一个【最终击杀**看起来的样子**】
```

### 7.1 ⭐⭐⭐ **"它们既不是赢家也不是录制客户端，那正是一个最终击杀看起来的样子"**

**✅ 与 §408 的"`L 2 7` 在 +11100 与 `u 10` 并列"**——**完全闭合** ✓

**⇒ 三层**：
```text
§408  **"`L 2 7` 是这个序列唯一的候选（`sub_7C3280` 的 slot-7 分支是一个展示模式选择器）"**
§459  **"`killCamClientNum 2` 与 `L 2 7` 是同一个客户端，而它是凶手"**
⇒ **⇒ 所以【`L 2 7` 的 `2` 是【凶手**，不是"shoutcast 选中的那个"**】
```

**✅ ⭐⭐⭐ **"`L 2 7` 的 `2` 是凶手，不是 shoutcast 选中的那个"** —— **一个对 §408 的 INFERRED 的修正**。</br>

**✅ 而 §408 说那是 **INFERRED, NOT MEASURED**（"retail sends client 2 there, which is the client its `cl_shoutcastSelectedClient "2"` at connect also names -- so retail's choice is 'whoever the shoutcast is watching', not 'the winner'"）**。**

**⇒ 三层**：
```text
§408  **"`L 2 7` 的 `2` 是 shoutcast 选中的那个"**（**INFERRED**）
§459  **"`killCamClientNum 2` 与 `L 2 7` 是同一个客户端，而它是【凶手**"**
⇒ **⇒ 所以【§459 给出了一个【更强的证据**】
```

**⚠ 一个**重要的推理升级**（**而 §459 的措辞"那正是一个最终击杀看起来的样子"是【一个论证**而**不是一个测量**）。

**✅ ⭐⭐ **"一个论证而不是一个测量"** —— 与 §435 的"INFERRED, NOT MEASURED"**同族。

## 八、关键结论

1. **⭐⭐⭐ `lootActivateHeld_` 的"`ACTIVATE` 是一个电平，不是一个边沿：那个位在键按下的时候一直设着，而 usercmd 到达得比任何人能松手更快 ⇒ 没有这个，**一次按键会排空整个环**"`** —— **"必须自己做一个上升沿"**，而**同一个模式在 `zmUseActivateHeld_` 也有**。
2. **⭐⭐⭐ `hintStringSlots_` 的"一个带槽每【不同的串】，不是每触发器：零售自己的捕获给 `zm_factory_sh` 的全部四扇 1000 点的门【同一个相对索引】，而那个带只有 `96` 宽对着这张地图上单独的 `54` 个触发器"`** ⇒ **"把一个必然的溢出变成一个有余量的设计"** —— 第四次"对齐既有实现"。
3. **⭐⭐ `cursorHintTrigger_` 被"加宽到 `32` 位以持有 loot 键"** 与 §416 的 `SvLootHintKeyBase = 0x10000u` **完全闭合**；而 **"线上只携一个变化"是第三次"只发变化"**。
4. **⭐⭐⭐ `SvDeathViewMilliseconds` 的三次修订**：`2000` → `1200` → **`1500`**，而**每一次都有理由**；第三次的根据是**"`2697` 的『让玩家看自己死』块是 `wait(0.25) + wait(0.25) + wait(1.0)` 在 `death_delay_finished` 之前"** ⇒ **`0.25 + 0.25 + 1.0 = 1.5` 秒**。
5. **⭐⭐⭐ "`1500` 是一个源码的加法，不是一个估计"**，而 **`SvDeathViewMilliseconds (1500) + SvKillCamDelayMilliseconds (1500) = 3000` ⇒ 正好是 `cha.lua` 的重生请求** —— 一个完整的算术闭合（与 §404 的"两个串联的 `1500ms`"同族）。
6. **⭐⭐ "一个更长的身体视角会完全吞掉 killcam"**（因为那个触发的分支在视角还在的时候继续）—— 第二次"窗口的竞争"（与 §404 的"延迟是常数，选择是那个竞赛"同族）。
7. **⭐⭐⭐ `PerkLife` 的 `selectedLoadout` 键**：**"一个比赛中背包切换改变 `selectedLoadout` 而【不提 `spawnGeneration`】，所以没有这个键 perk 在出生时解析一次而永不再 ⇒ 客户端换了职业而保留旧的三个 perk"`** ⇒ **"两个键：`spawnGeneration`（一次出生）与 `selectedLoadout`（一次职业切换）"`** —— 第三次"两个生命周期"（与 §407/§422 同族），而 **`EquipmentLife` 有同样的键**。
8. **⭐ `pmFlagsLogged`/`pmFlagsLoggedValid` 是"只用于打到日志的去重，不参与任何游戏逻辑"`** —— **一个取证字段**（与 §402 的"纯只读观测"同族），而 **§402 说"我方一帧都没观测过"，§459 给出了那个观测的实现**。
9. **⭐⭐ "spy 每局 7 回合（`s scr_spy_roundlimit "7"`，`scr_round` 1..7，终局后回 "0"）"`** ⇒ **"阶段是一个回合内的，而回合是跨阶段的"`** —— 一个**二维的状态机**（对 §403 的五阶段的补充）。
10. **⭐⭐⭐ `SvMatchEndKill` 的"最后一个击杀必须在那个把它从 `killCamSubjects_` 抹掉的重生之前存活"`**，而 **零售的比赛末帧命名一个凶手（`killCamClientNum 2` + `L 2 7`）与一个受害者（`killCamLookAtEntity 8`）—— 它们既不是赢家也不是录制客户端** ⇒ **"那正是一个最终击杀看起来的样子"`** —— 一个**对 §408 的 INFERRED 的推理升级**（**而 §459 的措辞是一个论证而不是一个测量**）。

## 九、`sv_main_mp.hpp` 全文件总览

**行数：`1,793`**。

**十四个自由函数 / 类**：

| 项 | 内容 |
|---|---|
| `SV_ShouldDiscardRejectedUserCmd` / `SV_ClientThinkBudgetMilliseconds` / `SV_ChargeClientThinkTime` | think 预算 |
| `SV_FrameMilliseconds` / `FixedFrameScheduler` | 帧调度 |
| `ServerStatus` / `SvServerFrameTimingStatus` / `SvConnectionlessDiagnostics` | 状态 |
| `SvWorldWeaponSample` / `SvWorldPlayerSample` / `SvOutboundPacket` | 采样 |
| `SvMatchEndReason`（6）/ `SvSdRoundEndReason`（7）/ `SvSdBombPhase`（7） | 三个枚举 |
| `SvSdRoundStatus` / `SvSdBombStatus` / `SvSdBombRules` / `SvSdEliminationState` / `SvSdRuntimeStatus` | SD |
| `SvGameplayPresentationClientStatus` / `SvGameplayPresentationStatus` | 呈现 |
| `SvSdTeamSoundPresentation`（14）/ `SvSdSoundPresentation` | 音效 |
| `SV_BuildSdObjectives` / `SV_BuildSdPlantedObjectives` / `SV_AddSdBombObjective` / `SV_BuildObjectiveHudElems` | SD 目标 |
| `SV_CalculateDmMatchBonus` / `SV_IsDmOutcomeTie` / `SV_BuildDmOutcomeHudElems` / `SV_BuildFeedbackHudElems` / `SV_BuildFactoryEntryHud` / `SV_BuildZmScoreHudElem` | HUD |
| `SV_BeginSdBombRound` … `SV_EvaluateSdRoundOutcome`（7 个） | SD 状态转移 |
| `SvAnnouncerState` / `SvAnnouncerCues` / `SvAnnouncerClientDialog` / `SV_UpdateMatchAnnouncer` | 播报 |
| `SV_UpdateMatchTimeLimit` | 时限 |
| `ServerCore`（约 `150` 个公开方法 + `100` 个私有） | 核心 |

**`ServerCore` 的三把锁 / 两个互斥**：
```text
mutex_           ⇒ 控制线程 + 帧入口（非递归）
zmZonesMutex_    ⇒ zm 区域（因为 loadGameplayScript 持 mutex_ 时脚本读它们）
                  单向顺序：mutex_ → zmZonesMutex_，反之永不发生
```

**二十二个侧表（"搬到外面"）**：
```text
resolvedLoadouts_ / weaponSelectSequences_ / matchParticipation_ / dmMatchBonuses_
lastCharacterCustomizations_ / perkLives_ / perkSlotsSent_ / equipmentLives_ / uiClientLife_
killCamSubjects_ / archivedObituaries_ / lastMatchKill_ / matchRulesAnnounced_
announcer_ / battleChatterSequence_ / battleChatterVoiceFemale_ / announcerDialog_
visionAnnounced_ / factoryEntries_ / clientFeedback_ / assistLedger_ / lootHintTarget_
```

**十一个"只发变化"的比较点**：
```text
weaponSelectSequences_ / perkSlotsSent_ / dmMatchBonuses_
lastCharacterCustomizations_ / cursorHintTrigger_ / hintStringSlots_
battleChatterSequence_ / visionAnnounced_ / matchRulesAnnounced_
lastSplashRelease_ / factoryInteractionHintCache_
```

## 十、未闭合点

- `SvAnnouncerLeadTakenHigh = 1681` / `LeadLostHigh = 1683` / `WinningHigh = 1058` 与 `SvAnnouncerLeadTaken` 等的映射。
- `SvPrematchWaitingText = 396` 与 `SvPrematchStartingText = 396` **同值**（我标注的可疑点）。
- `spyRoundEndsAt` 的 `60s` 回合时长（**一个占位**）。
- `SvDeathViewMilliseconds` 是否还会被第四次修订。
- **下一步**：`sv_native_playerstate_mp.cpp`（`89,189` 字节）。
