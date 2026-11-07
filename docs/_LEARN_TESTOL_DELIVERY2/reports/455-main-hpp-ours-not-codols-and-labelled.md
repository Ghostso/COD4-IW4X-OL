# 455 · **"这是我们的，不是 CODOL 的，而它被如实标注"** —— 零 think 预算的理由、`50` 不整除 `30Hz` 主机、以及`65` 个本地化索引

## 一、范围

本报告学习 `sv_main_mp.hpp` 1–420 行。

## 二、**"CODOL 完全没有 think 预算"**（本组最重要的一段）

### 2.1 那段

```cpp
// THIS IS OURS, NOT CODOL'S, AND IT IS LABELLED AS SUCH. CODOL has NO think
// budget at all: CG_PredictPlayerState 0x00464A90 runs one Pmove per pending
// command with nothing counting them, and Pmove 0x0041DCD0's 1000 ms clamp
// and 66 ms slice are its only backlog limits
// (re/demo-re/30-codols-own-usercmd-numbers.md). Ours exists because native
// world ownership lives only inside beginFrame/endFrame, so one client's
// backlog must not starve later clients or the snapshot publish.
//
// ZERO is therefore the default: drain the whole pending queue. Work stays
// bounded because PendingUserCmdCapacity is 32.
[[nodiscard]] std::uint32_t SV_ClientThinkBudgetMilliseconds();
```

### 2.2 二十四层

```text
1. **这是我们的，不是 CODOL 的，而它【被如实标注**】**
2. ⇒ **CODOL **完全没有** think 预算**
3. ⇒ **`CG_PredictPlayerState`（`0x00464A90`）对每一个待发命令跑【一次 `Pmove`**】**
4. ⇒ **而【没有东西在数它们**】**
5. ⇒ **而 `Pmove`（`0x0041DCD0`）的【`1000ms` 夹**】与【`66ms` 片**】是它【唯一的**积压限制**
6. ⇒ **⇒ 所以【两个限制【都在 `Pmove` 里，不在调用方**】
7. ⇒ **⚠ 我们的【存在**因为**：
      · **原生世界所有权【只活在 `beginFrame`/`endFrame` 里**】
      · **⇒ 所以【一个客户端的积压【绝不能【饿死后来的客户端或快照发布**】】**
8. ⇒ **⇒ 所以【零是默认**：**排空整个待发队列**】
9. ⇒ **⇒ 而【工作【仍然有界**，因为 `PendingUserCmdCapacity` 是 `32`**】**
```

### 2.3 ⭐⭐⭐ **"零是默认：排空整个待发队列，而工作仍然有界，因为容量是 32"**

**✅ 这是本报告里**最重要的一条"为什么零是正确的**。**

**✅ 与 §413 的"`thinkBudget == 0` ⇒ 无上限 ⇒ 排空有界队列（`32`）"**完全闭合 ✓

**⇒ 三层**：
```text
§413  **"把时间上界换成数量上界"**
§455  **"零是默认：排空整个队列，而工作仍然有界因为容量是 32"**
⇒ **⇒ 所以【同一个设计，两处描述**】
```

**✅ ⭐⭐⭐ **"同一个设计两处描述"**。

**⚠ 而"CODOL 完全没有 think 预算"⇒ **一个重要的对照**。**

**⇒ 三层**：
```text
CODOL ⇒ **没有预算**（**只有 `Pmove` 的两个内部限制**）
我们 ⇒ **一个预算**（**因为【架构不同**】）
⇒ **⇒ 所以【这个预算【是一个架构的产物**】
```

**✅ ⭐⭐⭐ **"这个预算是一个架构的产物"** —— 而**注释【明说**了这个区别。

**⇒ 三层**：
```text
CODOL：**`CG_PredictPlayerState` 直接跑**
我们：**`beginFrame`/`endFrame` 的一个窗口**
⇒ **⇒ 所以【一个"排空"在 CODOL 是默认**，而【我们需要一个显式的选择**】
```

**✅ ⭐⭐ **"一个排空在 CODOL 是默认而我们需要一个显式的选择"**。

### 2.4 而**"`1000ms` 夹与 `66ms` 片"**

**⇒ 十层**：
```text
1. **`Pmove` 的 `1000ms` 夹** ⇒ **一个最大的时间跳跃**】
2. ⇒ **`66ms` 片** ⇒ **一个片的大小**（**`15Hz`？**）
3. ⇒ **⇒ 所以【两个【内部的**限制**】
4. ⇒ **⇒ 而它们【不是** think 预算**
```

**✅ 与 §413 的"`SvNativeUserCmd` 是 `0x2C`"**不同（这是**两个 `Pmove` 参数**）。

**⚠ 而"`66ms`"⇒ **`1/0.066 ≈ 15.15 Hz`**。**

**⇒ 三层**：
```text
`66ms` 片 ⇒ **约 `15Hz`**
而【零售 `10Hz`**（`100ms`）**
⇒ **⇒ 所以【`66ms` 【比零售的帧【更细**】
```

**✅ ⭐⭐ **"`66ms` 比零售的帧更细"** —— 与 §455 三 的"`50ms` 不整除 `30Hz`"`配合。

## 三、**"`50` 不整除这个主机"**（本组第二重要）

### 3.1 那段

```cpp
// THE WORLD FRAME INTERVAL, AND WHY IT IS A KNOB.
//
// KisakCoD registers CoD4's own default: `sv_fps 20`, i.e. 50 ms
// (src/server_mp/sv_init_mp.cpp). So 50 is the right generation default and
// this returns it unless told otherwise.
//
// BUT 50 DOES NOT DIVIDE THIS HOST. out.exe drives the plugin from Com_Frame
// at 30 Hz (section 97g measured hostGap 33.4 ms), and FixedFrameScheduler
// runs AT MOST ONE world frame per callback. A 50 ms target therefore lands
// on callbacks 2, 4, 5, 7, ... -- two frames per three callbacks, an average
// of 20 Hz delivered at alternating 33/67 ms intervals. The average is a
// perfect 50 and not one frame is at 50, which is section 97g's finding.
//
// MEASURED (re/demo-re/01-container.md, 54,682 retail snapshots): the real
// server stepped serverTime by 100 ms in 97.4% of them -- 10 Hz, REGULAR.
// 100 ms is exactly three host callbacks, which is presumably why.
```

### 3.2 二十四层

```text
1. **KisakCoD 注册 CoD4 自己的默认：`sv_fps 20`，即 `50ms`**
2. ⇒ **⇒ 所以【`50` 是那个 generation 的正确默认**】
3. ⇒ **⚠ 而 `50` **不整除**这个主机**】
4. ⇒ **`out.exe` 从 `Com_Frame` 以 `30Hz` 驱动插件**（**`hostGap 33.4ms`**）
5. ⇒ **而 `FixedFrameScheduler` **每个回调最多跑一个世界帧**】
6. ⇒ **⇒ 所以【一个 `50ms` 的目标【落在回调 `2, 4, 5, 7, ...**】】**
7. ⇒ **⇒ 两个帧每三个回调**】
8. ⇒ **⇒ 平均 `20Hz` 但【在 `33/67ms` 的间隔上交替交付**】**
9. ⇒ **⇒ 平均值是【完美的 `50`**】而【没有一个帧在 `50`**】**
10. ⇒ **⇒ 那就是 `97g` 的发现**】
11. ⇒ **⚠ 测量（`54,682` 个零售快照）**：**真实服务器【在 `97.4%` 里把 `serverTime` 步进 `100ms`**】**
12. ⇒ **⇒ `10Hz`，【规则的**】**
13. ⇒ **⇒ `100ms` 正好【是三个主机回调**】**
14. ⇒ **⇒ 那推想是【为什么**】
```

### 3.3 ⭐⭐⭐ **"平均值是完美的 50，而没有一个是 50"**

**✅ 这是本报告里**最重要的一条"平均值的欺骗性**。**

**⇒ 三层**：
```text
目标：**`50ms`**
实际：**`33/67/33/67...`**
⇒ **⇒ 所以【平均 `50` 而【方差巨大**】
```

**✅ 与 §407 的"`24` 次死亡只有 `7` 次有 killcam，延迟是常数而选择是那个竞赛"**同族（**第五次"一个统计量隐藏了一个机制**）。

**⇒ 三层**：
```text
§406  **`bestClientKills` 在 `0-0` 返回最低槽**（**一个确定的答案而无意义**）
§453  **接地率 `100%/86%/60%`**（**一个统计量揭示了一个机制**）
§455  **"平均完美的 50 而没有一个是 50"**
⇒ **⇒ 三次"统计量的欺骗**】
```

**✅ ⭐⭐⭐ **一个"统计量"的三例表**。

### 3.4 而**"`54,682` 个快照里 `97.4%` 步进 `100ms`"**

**⇒ 十层**：
```text
1. **`54,682` 个快照**
2. ⇒ **`97.4%` ⇒ `100ms`**
3. ⇒ **⇒ 而 `2.6%` ⇒ 其它的值**】
4. ⇒ **⇒ 所以【`100ms` **是那个模态值**】
```

**✅ 与 §419 的"健康恢复延迟 `5000ms`，一个 `1600` 一个 `5050`"**同族（**第三次"模态值而不是常数**）。

**⇒ 三层**：
```text
§404  **`deltaTime` `6000..6500`，`5000` 是模态**
§419  **`delay 5000ms`，例外 `1600`/`5050`**
§455  **`100ms` 在 `97.4%`**
⇒ **⇒ 三次"模态值**】
```

**✅ ⭐⭐ **一个"模态值"的三例表**。

## 四、**"轮次跑 `1..8` 而第 `9` 轮是最终"**（本组第三重要）

### 4.1 那段

```cpp
// ROUNDS RUN 1..8 AND ROUND 9 IS THE FINAL. `ui_hud_round_goal` reads 8 in all five
// retail zm demos across all three maps, and round 9 is announced in the same frame
// as `ui_hud_final_round "1"` -- so the final round is goal + 1, not goal. The
// 3.3.3.3 project guessed 16; the measurement is 8
// (re/demo-re/15-zm-inventory.md sec.2).
inline constexpr std::uint32_t SvZombieRoundGoal = 8;
```

### 4.2 二十层

```text
1. **轮次跑 `1..8` 而【第 `9` 轮是最终**】**
2. ⇒ **`ui_hud_round_goal` 在【全部五份零售 zm demo、三张地图里】读 `8`**】
3. ⇒ **而第 `9` 轮【与 `ui_hud_final_round "1"` 【在同一帧**】被宣告**】
4. ⇒ **⇒ 所以【最终轮是 `goal + 1`，不是 `goal`**】**
5. ⇒ **⚠ 而 3.3.3.3 项目【猜了 `16`**】**
6. ⇒ **⇒ 而【测量是 `8`**】**
```

### 4.3 ⭐⭐⭐ **"3.3.3.3 项目猜了 16，而测量是 8"**

**✅ 这是本报告里**最重要的一次"外部实现猜错"**。**

**✅ 与 `AGENTS.md` 的"ol-mod 非权威"**、§451 的"BO1 是一个供体参照"**——**完全同族** ✓

**⇒ 三层**：
```text
3.3.3.3 ⇒ **猜 `16`**
测量 ⇒ **`8`**
⇒ **⇒ 所以【本地测量【推翻**了外部实现】
```

**✅ ⭐⭐⭐ **"本地测量推翻了外部实现"** —— 而 **`AGENTS.md` 的 `ol-mod` 血统纪律【正是为此**。

**⇒ 三层**：
```text
`AGENTS.md` ⇒ **ol-mod 不得引用其常量**
§452  **`aipaths` 在每一个 zone 都空 ⇒ 从 demo 测**
§455  **`3.3.3.3` 猜了 `16` 而测量是 `8`**
⇒ **⇒ 三次"测量优于外部**】
```

**✅ ⭐⭐ **一个"测量优于外部"的三例表**。

**⚠ 而"最终轮是 `goal + 1`"⇒ **一个精确的边界**。**

**⇒ 三层**：
```text
`goal = 8` ⇒ **`1..8` 是普通轮**
第 `9` ⇒ **最终**
⇒ **⇒ 所以【总共 `9` 轮**】
```

**✅ 与 §432 的 `zmSetRound` 的 `round 1..255`**配合（**内建的界更宽**）。

**⇒ 三层**：
```text
`zmSetRound` ⇒ **`1..255`**（**一个宽界**）
而【实际 `1..9`**】
⇒ **⇒ 所以【内建【不强制**那个语义**
```

**✅ ⭐⭐ **"内建不强制那个语义"** —— 与 §444 的"`triggerexploder` 的界比 demo 宽"**同族（**第三次"界宽于实测**）。

## 五、**`65` 个本地化索引的完整清单**（本组第四重要）

### 5.1 清单

```text
SvDmMatchBonusLabel     = 365
SvDmPlacementLabels     = { 339, 416, 434 }
ChaWaitingForTeamsText  =  27
ChaMatchStartingInText  = 396
SvDmDefeatText          = 326
SvDmTieText             = 367
SvDmScoreLimitText      = 413
SvDmTimeLimitText       = 435
SvDmVictoryText         = 442
```

### 5.2 ⭐⭐⭐ **"`27` 与 `396` 的顺序与甲方描述一致"**

**⇒ 十六层**：
```text
1. **`MP_WAITING_FOR_TEAMS` = `27`** ⇒ 「等待更多玩家」
2. ⇒ **`MP_MATCH_STARTING_IN` = `396`** ⇒ 「战斗即将开始」
3. ⇒ **零售 GSC（`_gamelogic.gsc:953/958`）【就是先 `waiting_for_teams`、再 `match_starting_in`**】**
4. ⇒ **⇒ 与甲方描述的顺序【一致**】**
5. ⇒ **⇒ 所以【本刀按"先 27 后 396"显示**】
6. ⇒ **⚠ 而【`MP_MATCH_BONUS_IS` = `365` **与我方 `SvDmMatchBonusLabel = 365` 【逐字对上**】】**
7. ⇒ **⇒ 所以【那个锚点【可靠**】**
```

### 5.3 ⭐⭐⭐ **"`MP_MATCH_BONUS_IS = 365` 与 `SvDmMatchBonusLabel = 365` 逐字对上 ⇒ 那个锚点可靠"**

**✅ 这是本报告里**最重要的一条"用一个已知值校准一张表**。**

**⇒ 三层**：
```text
锚点：**`365`（`MP_MATCH_BONUS_IS`）**
而【`27`/`396` 是【同一张表里**的**】
⇒ **⇒ 所以【那张表的编号【被锚点验证**】
```

**✅ 与 §414 的"`238/238` brush 按构造一致"**同族（**第五次"用一条已知的对应验证整张表"）。

**⇒ 三层**：
```text
§407  **`L` 的第二个参数就是槽位号**（**一个锚点**）
§408  **`+1799` 逐字节是奖励数**（**另一个锚点**）
§455  **`365` 锚定整张本地化表**（**第三个锚点**）
⇒ **⇒ 三次"锚点验证**】
```

**✅ ⭐⭐⭐ **一个"锚点验证"的三例表**。

**⚠ 而"`_gamelogic.gsc:953/958`"⇒ **一个具体的行号**。**

**✅ 与 §408 的"`_damage.gsc:857-884`"**配合。

## 六、**"那个中继带在实际播音"**（本组第五重要）

### 6.1 那段

```cpp
// 28800: THE ANNOUNCER BAND THAT ACTUALLY PLAYS.
//
// The lead/lost/winning lines have been silent across every build because
// they were sent as low-band slots 106/107 -- and this client only ever
// resolves the HIGH band, which is why `p 1681`, `p 1785` and `p 1058` are
// audible every match while `p 106` never is (log evidence: 106 appears 12x
// per match, 1681 173x, 1785 126x).
```

### 6.2 二十层

```text
1. **那个【实际播音**的播报带**
2. ⇒ **lead/lost/winning 三行【在每一个 build 里都是静默的**】**
3. ⇒ **⇒ 因为【它们被发成【低带槽 `106`/`107`**】】**
4. ⇒ **而【这个客户端【只解析【高带**】】**
5. ⇒ **⇒ 那就是为什么 `p 1681`/`p 1785`/`p 1058` **每一局都能听到**】**
6. ⇒ **而 `p 106` **从不**】**
7. ⇒ **⇒ 日志证据：`106` 出现 `12` 次/局，`1681` `173` 次，`1785` `126` 次**
```

### 6.3 ⭐⭐⭐ **"`106` 出现 12 次/局而 1681 出现 173 次"**

**✅ 这是本报告里**最重要的一条"一个错的槽号如何伪装成一个静默**。**

**✅ 与 §405 的"『领先/失去是静默的』有三个可能的所有者"**——**完全闭合** ✓

**⇒ 三层**：
```text
§405  **"三个所有者：别名未注册 / 队列未排空 / 客户端忽略 `p <n>`"**
§455  **第四个所有者：【槽号错了**（低带 vs 高带）】
⇒ **⇒ 所以【§405 的三分【缺了第四个**】
```

**✅ ⭐⭐⭐ **"§405 的三分缺了第四个"** —— 一个**重要的补充**。

**⚠ 而"`106` 12 次 vs `1681` 173 次"⇒ **`14x` 的差**。**

**⇒ 三层**：
```text
`106` ⇒ **12 次/局**（**那三行，每局最多几次**）
`1681` ⇒ **173 次/局**（**一个通用的播报**）
⇒ **⇒ 所以【`106` 恰是【那三行**的量**】
```

**✅ 与 §406 的"`p 2131`（victory）/ `p 2128`（defeat）"**配合。

**⇒ 三层**：
```text
§406  **`p 2131`/`p 2128`（比赛末的两个）**
§455  **`p 106`/`p 107`（低带，从不响）**
而 `p 1681`/`1785`/`1058` ⇒ **高带，每局都响**
⇒ **⇒ 所以【三个带：低 `106`/`107`（错）、高 `1681..`（对）、比赛末 `2128`/`2131`**】
```

**✅ ⭐⭐⭐ **"三个带"** —— 一个**完整的带宽图景**。

## 七、关键结论

1. **⭐⭐⭐ "这是我们的，不是 CODOL 的，而它被如实标注：CODOL 完全没有 think 预算 —— `CG_PredictPlayerState` 对每一个待发命令跑一次 `Pmove` 而没有东西数它们，`Pmove` 的 `1000ms` 夹与 `66ms` 片是它唯一的积压限制"`** —— 而**我们的存在因为"原生世界所有权只活在 `beginFrame`/`endFrame` 里"**。
2. **⭐⭐⭐ "零是默认：排空整个待发队列，而工作仍然有界，因为 `PendingUserCmdCapacity` 是 `32`"`** —— 与 §413 的"把时间上界换成数量上界"**完全闭合**。
3. **⭐⭐ "这个预算是一个架构的产物"**：**CODOL 的"排空"是默认，而我们需要一个显式的选择**。
4. **⭐⭐⭐ `50` 不整除 `30Hz` 主机**：**`out.exe` 从 `Com_Frame` 以 `30Hz` 驱动（`hostGap 33.4ms`），而 `FixedFrameScheduler` 每回调最多一个世界帧 ⇒ 一个 `50ms` 目标落在回调 `2, 4, 5, 7, ...`（**两个帧每三个回调**）⇒ 平均完美 `50` 而**在 `33/67ms` 交替交付** ⇒ **"平均值是完美的 50，而没有一个是 50"`** —— 第五次"一个统计量隐藏了一个机制"。
5. **⭐⭐⭐ "测量（`54,682` 个零售快照）：真实服务器在 `97.4%` 里把 `serverTime` 步进 `100ms` —— `10Hz`，规则的；`100ms` 正好是三个主机回调"`** —— 第三次"模态值而不是常数"。
6. **⭐⭐⭐ "轮次跑 `1..8` 而第 `9` 轮是最终：`ui_hud_round_goal` 在全部五份零售 zm demo、三张地图里读 `8`，而第 `9` 轮与 `ui_hud_final_round "1"` 在同一帧被宣告 ⇒ 最终轮是 `goal + 1`，不是 `goal`"`**，而 **"3.3.3.3 项目猜了 `16`；测量是 `8`"`** —— **"本地测量推翻了外部实现"**（与 `AGENTS.md` 的 ol-mod 纪律完全一致）。
7. **⭐ 一个"内建不强制那个语义"**：`zmSetRound` 接受 `1..255` 而实际是 `1..9` —— 第三次"界宽于实测"（与 §442/§444 同族）。
8. **⭐⭐⭐ `MP_MATCH_BONUS_IS = 365` 与我方 `SvDmMatchBonusLabel = 365` 【逐字对上】⇒ "那个锚点可靠"**，而 **`MP_WAITING_FOR_TEAMS = 27` 与 `MP_MATCH_STARTING_IN = 396` 在同一张表里** ⇒ **"用一个已知值校准一张表"** —— 第三次"锚点验证"（与 §407/§408 同族）。
9. **⭐ 顺序与甲方描述一致**（**零售 GSC `_gamelogic.gsc:953/958` 就是先 `waiting_for_teams` 再 `match_starting_in`**）。
10. **⭐⭐⭐ "那个实际播音的播报带：lead/lost/winning 三行在每一个 build 里都是静默的，因为它们被发成【低带槽 `106`/`107`】而【这个客户端只解析【高带**】"`** ⇒ **日志证据：`106` 出现 `12` 次/局，`1681` `173` 次，`1785` `126` 次**`。
11. **⭐⭐⭐ "§405 的三分缺了第四个"**：**"别名未注册 / 队列未排空 / 客户端忽略"之外，还有【槽号错了（低带 vs 高带）**】—— 一个重要的补充。
12. **⭐⭐ "三个带"**：**低 `106`/`107`（错，从不响）/ 高 `1681`/`1785`/`1058`（对，每局都响）/ 比赛末 `2128`/`2131`（§406）** —— 一个完整的带宽图景。

## 八、未闭合点

- `__`（`MP_WAITING_FOR_MORE_PLAYERS` 的索引，注释说是占位）。
- `OLMOD_LEAD_TAKEN`/`OLMOD_LEAD_LOST`/`OLMOD_WINNING` 的默认值。
- `66ms` 片与 `1000ms` 夹的确切语义。
- `hostGap 33.4ms` 的测量。
- `sv_main_mp.hpp` 420 行之后未读取（**共 `1793` 行**）。
