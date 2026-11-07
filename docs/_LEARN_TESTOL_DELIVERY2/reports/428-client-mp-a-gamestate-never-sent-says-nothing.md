# 428 · **"一个从不发送的 gamestate 什么也不说，而它是一个死锁的头"** —— 四项闸门、`s` 的两次处理、以及"`u 10` 是『打开 configstring 4818 里命名的菜单』"

## 一、范围

本报告学习 `sv_client_mp.cpp` 1100–1440 行（可靠命令分派、`n <k>` 通道、`usercmd arrival` 探针、gamestate 闸门、`SV_SendClientMessages` 的开头）。

## 二、**gamestate 死锁的四个闸门**（本组最重要的一段）

### 2.1 那段

```php
// A GAMESTATE THAT IS NEVER SENT SAYS NOTHING, and it is the head of a deadlock:
// no gamestate -> the client never reaches ClientLoading -> it never sends
// gamestateupdate 1..6 -> it never becomes Active -> activeClients stays 0 ->
// configurePendingWorldSpawn returns at its first line -> no world, no spawn
// points, no snapshots. On screen that is a client sitting in the menu or on a
// loading screen forever, with `clients=1 active=0 snapshots=0` in the runtime
// line and not one other complaint anywhere. Four terms can hold it shut and the
// log named none of them. Once per distinct combination per client, so a stuck
// client prints one line rather than one per packet.
if (slot->state == ClientState::Connected)
{
    std::string blocked;
    if (!slot->profileStatsComplete)
        blocked += " PROFILE_STATS_INCOMPLETE(" + received + "/" + required + ")";
    if (!clientGenerationIsActive(*slot))
        blocked += " GENERATION_INACTIVE";
    if (!gameStateConfigured_)
        blocked += " GAMESTATE_NOT_CONFIGURED";
    if (!gameStateBuilder_)
        blocked += " NO_GAMESTATE_BUILDER";
    if (!blocked.empty() && slot->gameStateGateReport != blocked)
    {
        slot->gameStateGateReport = blocked;
        ... "gamestate NOT sent client=" + slotIndex + blocked
    }
}
```

### 2.2 二十四层

```text
1. **一个从不被发送的 gamestate 【什么也不说**】**
2. ⇒ **而它是【一个死锁的头**】**
3. ⇒ **六个环节**：
      · **没有 gamestate**
      · ⇒ **客户端【从不达到 `ClientLoading`**】**
      · ⇒ **它【从不发 `gamestateupdate 1..6`**】**
      · ⇒ **它【从不变成 `Active`**】**
      · ⇒ **`activeClients` 停在 `0`**】
      · ⇒ **`configurePendingWorldSpawn` 【在第一行返回**】**
      · ⇒ **没有世界、没有出生点、没有快照**
4. ⇒ **在屏幕上【那是一个永远坐在菜单或加载屏的客户端**】**
5. ⇒ **而运行时行里 `clients=1 active=0 snapshots=0`**
6. ⇒ **⇒ 而【没有任何其它抱怨在任何地方**】**
7. ⇒ **四个项【能把它关着**】**
8. ⇒ **⇒ 而【日志【一个都没命名**】】**
9. ⇒ **⇒ 所以【每个客户端每个不同的组合各一次**】】
10. ⇒ **⇒ 所以【一个卡住的客户端打印【一行**而不是每包一行**】**
```

### 2.3 ⭐⭐⭐ **"四个项能把它关着，而日志一个都没命名"**

**✅ 这是本报告里**最重要的一条"死锁的静默性"**。**

**⇒ 三层**：
```text
症状：`clients=1 active=0 snapshots=0`（**一行**）
原因：**四个闸门之一**
⇒ **⇒ 而【四个都是布尔**】 ⇒ **那个一行说不出来**
```

**✅ 与 §426 的"两个非 (B) 分支都能楔死而两个都不说"**——**完全同族**（**第七次"多因歧义"**）。

**⇒ 三层**：
```text
§405  "三个所有者一个没留一行"
§426  "两个分支都能楔死而两个都不说"
§428  "四个项能关着而日志一个都没命名"
⇒ **⇒ 三次"多因静默**】
```

**✅ ⭐⭐⭐ **一个"多因静默"的三例表**。

**⚠ 而"每个不同的组合各一次"⇒ **`gameStateGateReport != blocked`**。**

**⇒ 四层**：
```text
1. **按【组合字符串**】去重**
2. ⇒ **⇒ 所以【组合变化时才打印**】**
3. ⇒ **⇒ 而"同一个组合重复" ⇒ 静默**
4. ⇒ **⇒ 一个"边沿触发在复合状态上"的实例**（§409 的位掩码同族）
```

**✅ ⭐⭐ **"按组合字符串去重"** —— 与 §409 的"按位掩码去重"**同族（**第三次）。

**⇒ 三层**：
```text
§409  `blockedBits`（**3 位掩码**）
§426  `cmd-gate-closed`（**6 位掩码**）
§428  `gameStateGateReport`（**一个字符串**）
⇒ **⇒ 三种"复合状态去重"**
```

**✅ ⭐ **一个"复合去重"的三例表**。

### 2.4 而**"四项"的检查顺序**

```text
① PROFILE_STATS_INCOMPLETE(received/required)
② GENERATION_INACTIVE
③ GAMESTATE_NOT_CONFIGURED
④ NO_GAMESTATE_BUILDER
```

**⇒ 五层**：
```text
① ⇒ **客户端侧**（它没发完 stats）
② ⇒ **服务端代次**（`clientGenerationIsActive`）
③ ⇒ **配置**（`gameStateConfigured_`）
④ ⇒ **注入**（`gameStateBuilder_` 是否被设）
⇒ **⇒ 所以【四个不同的层次**】
```

**✅ ⭐⭐ **"四个不同层次的闸门"** —— 与 §418 的"五个隐式消费者"不同（那是**同一层**）。

**⚠ 而"`PROFILE_STATS_INCOMPLETE(0/0)`"⇒ **若两者都是 `0`**。**

**⇒ 三层**：
```text
`received = 0` 且 `required = 0` ⇒ **`required` 还没被设**（**因为第一块还没来**）
⇒ **⇒ 所以 `0/0` 意味着【一个块都没收到**】
```

**✅ 而 §426 说"第一块短 ⇒ `requiredMask = (chunkBit<<1)-1`"** ⇒ **所以 `required` 在第一块之后才非零**。

**⇒ 三层**：
```text
前：`0/0` ⇒ **一个块都没收到**
后：`mask/required` ⇒ **有信息**
⇒ **⇒ 所以【`0/0` 是一个可判读的状态**】
```

**✅ ⭐ **一个"`0/0` 的信息量"**。

## 三、**`s` 被处理两次**（本组第二重要）

### 3.1 两处

```cpp
if (reliableCommand.command == "s")
    queueScoreboardResponse(static_cast<std::uint32_t>(slotIndex), "client_s");
auto menuResponse = SV_ParseMenuResponse(...);
if (menuResponse) { ...; continue; }
...
if (reliableCommand.command == "s")
    continue;
```

**⇒ 十层**：
```text
1. **`s` 先触发 `queueScoreboardResponse`**
2. ⇒ **然后 `SV_ParseMenuResponse` 会失败**（**因为 `s` 不是 `mr`**）
3. ⇒ **⇒ 所以走到 `if (reliableCommand.command == "s") continue;`**
4. ⇒ **⇒ 所以 `s` 是【一个被特殊处理**】的命令**
5. ⇒ **⇒ 而那个 `continue` 是【为了【不落入 `UNHANDLED` 日志**】】**
6. ⇒ **⇒ 所以【一个已处理的命令【必须显式跳过**】那个日志**
```

### 3.2 ⭐⭐ **"一个已处理的命令必须显式跳过 `UNHANDLED` 日志"**

**✅ 这是本报告里**最重要的一条"日志的分类"**。**

**⇒ 三层**：
```text
设计：**`UNHANDLED` 日志捕获"未知命令"**
风险：**一个已处理的命令落入它** ⇒ **假的"未知"**
⇒ **⇒ 所以【每个已处理的命令必须 `continue`**】
```

**✅ 与 §411 的"`m 0` 是第六套命令"**不同（这是**一个日志分类问题**）。

**⇒ 三层**：
```text
`leave` ⇒ **`dropClientSlot` + `break`**（**不 continue 因为槽没了**）
`s`    ⇒ **`queueScoreboardResponse` + `continue`**
`mr`   ⇒ **`SV_ParseMenuResponse` 成功 + `continue`**
其余   ⇒ **`UNHANDLED` 或 `EVERY`**
⇒ **⇒ 四条路径，两种 `continue`**
```

**✅ ⭐⭐ **一个"命令分派表"的完整结构**。

**⚠ 而"`leave` 用 `break`"⇒ **因为槽已经被释放，不能继续遍历。**

**✅ 而"`clientLeft` ⇒ 提前返回"**（`if (clientLeft) return {...}`）。

**⇒ 三层**：
```text
`leave` ⇒ **`dropClientSlot` + `break` + `clientLeft = true`**
⇒ **然后** `if (clientLeft) return {...}` **⇒ 所以【不碰槽**】
⇒ **⇒ 一个"释放后不触碰"的三段式**
```

**✅ ⭐⭐ **"释放后不触碰"** —— 与 §405 的"一个离开了的客户端什么都不保留"**同族（**第八次"槽释放"）。

## 四、**`u 10` 的完整语义**（本组第三重要）

### 4.1 那段

```php
// The answer worth watching for is `mr <n> bad`. out.exe's `u`
// handler (sub_610DB0) resolves its argument through
// sub_514880(_, n + 4808) -- the CONFIGSTRING getter, whose class
// table byte_77D8250 is the same one WeaponCountConfigStringIndex
// is derived from -- so `u 10` means "open the menu NAMED IN
// CONFIGSTRING 4818", not "screen ten". An empty configstring makes
// the client reply `mr 10 bad` and do nothing. This server fills
// three of those sixty-four slots.
```

### 4.2 二十层

```text
1. **值得观察的答案是 `mr <n> bad`**
2. ⇒ **`out.exe` 的 `u` 处理器（`sub_610DB0`）**：
3. ⇒ **通过 `sub_514880(_, n + 4808)` 解析它的参数**
4. ⇒ **⇒ 那是【那个 **CONFIGSTRING getter**】**
5. ⇒ **而它的类表 `byte_77D8250` 是【同一个**】`WeaponCountConfigStringIndex` 从它推导出来的**
6. ⇒ **⇒ 所以 `u 10` 意味着"打开【在 CONFIGSTRING `4818` 里命名的那个菜单**】"**
7. ⇒ **⇒ 【不是"屏幕十"**】**
8. ⇒ **一个空的 configstring 让客户端回 `mr 10 bad` 而【什么也不做**】**
9. ⇒ **而这个服务器【填了那六十四个槽里的三个**】**
```

### 4.3 ⭐⭐⭐ **"`u 10` 是『打开 configstring 4818 里命名的菜单』，不是『屏幕十』"**

**✅ 这是本报告里**最重要的一次命令语义纠正**。**

**⇒ 三层**：
```text
朴素理解：`u 10` ⇒ **"打开第 10 个屏幕"**（一个枚举）
真相：`u 10` ⇒ **"打开 cs 4818 里那个名字**"**（一个间接）
⇒ **⇒ 所以【`u` 的参数是一个【cs 偏移**】不是屏幕号**】
```

**✅ 与 §408 的"`_tp` 在【地图自己的 fastfile】"**同族（**第四次"一个数字的含义取决于已加载的资产"）。

**⇒ 三层**：
```text
§403  `u 10` **在死亡时画死亡相机**（**当时说是"屏幕请求"**）
§428  **`u 10` 是"打开 cs 4818 命名的菜单"**
⇒ **⇒ 而 §408 说"`u 10` 是一个它从未做过的 REQUEST"**
```

**⚠ 一处**需要标注的语义演进**（§408 说 `u 10` "不是这个服务器缺乏的内容，而是它从未做过的请求"，这里给出了机制）。

**✅ 而 `q 19` 与 `u 10` 的**同一家族**（§408 的"`r` 与 `q` 共享 109c 的请求家族"）。

**⇒ 三层**：
```text
`u <n>` ⇒ **cs 4808 + n**
`q <n>` ⇒ **可能同族**（§408 说 "19 是同一个索引")
⇒ **⇒ 所以【两个命令共用一个 cs 带**】
```

**✅ ⭐⭐ **"cs 4808 + n"** —— 与 §408 的"`d 2557`"等**不同（这是**一个带**）。

**⚠ 而"六十四个槽里的三个"⇒ **`4808..4871` 是 `64` 个菜单槽**。**

**⇒ 三层**：
```text
`4808..4871` ⇒ **`64` 个菜单槽**
而【填了 `3` 个**
⇒ **⇒ 所以【`61` 个是空的 ⇒ `mr <n> bad`**】
```

**✅ ⭐ **一个"带的容量与填充"的实例**。

**✅ 而 §388 的"materials 4872"**——**所以 `4872` 紧接在 `4808..4871` 之后**。

**⇒ 三层**：
```text
`4808..4871` ⇒ **菜单槽（`64`）**
`4872..`     ⇒ **materials**（§388）
⇒ **⇒ 两个带【相邻**】
```

**✅ ⭐ **一个"配置串带相邻"的确认**。

## 五、**`n <k>` 的"首次去重是错的"**

### 5.1 那段

```php
// FIRST-TIME-ONLY CANNOT BE COUNTED, AND COUNTING IS THE TEST.
//
// `n <k>` is the one channel left that could carry alt-fire: key 3
// emits NO usercmd button at all -- measured 2026-09-04 with a
// control in the same window, two left-clicks giving exactly two
// 0x00000001 edges and five presses of 3 giving none. Dedupe was
// right while these were noise; it is wrong now, because the whole
// question is whether some `n <k>` arrives once per press.
// OLMOD_LOG_CLIENT_COMMANDS=1 logs EVERY one, capped.
```

### 5.2 十八层

```text
1. **"首次"不能计数，而【计数就是那个测试**】**
2. ⇒ **`n <k>` 是【剩下唯一可能携带 alt-fire 的通道**】**
3. ⇒ **因为【键 `3` 【完全不发**】一个 usercmd 按钮**】
4. ⇒ **测量 `2026-09-04`，同一个窗口里有一个对照**：
      · **两次左键 ⇒ 恰好两个 `0x00000001` 边**
      · **五次按 `3` ⇒ 一个也没有**
5. ⇒ **⇒ 所以【键 `3` 不在 usercmd 里**】
6. ⇒ **去重【在这些是噪声时是对的**】**
7. ⇒ **⇒ 而它【现在是错的**】**
8. ⇒ **因为【整个问题就是【某个 `n <k>` 是否每次按下到达一次**】】**
9. ⇒ **⇒ 所以【需要一个"记录每一个"的开关**】**
```

### 5.3 ⭐⭐⭐ **"去重在噪声时是对的，现在是错的，因为整个问题就是『是否每次按下到达一次』"**

**✅ 这是本报告里**最重要的一条"去重的适用条件**。**

**⇒ 三层**：
```text
去重的目的：**减少噪声**
去重的代价：**消灭【计数信息**】**
⇒ **⇒ 所以【当"计数"本身是问题时，去重必须关**】
```

**✅ 与 §420 的"`n 89` 的 `10:10` 计数"**完全闭合 ✓

**⇒ 三层**：
```text
§420  `n 89` **十次按键十条命令**
§428  **"计数就是那个测试"** ⇒ 所以需要 `EVERY`
⇒ **⇒ 而 `n 89` 正是那个结论的来源**
```

**✅ ⭐⭐⭐ **一个"去重 vs 计数"的完整辩证**。

**⚠ 而"两次左键 ⇒ 两个 `0x00000001` 边"⇒ **一个阳性对照**。**

**✅ 与 §427 的"一个沉默的仪器与从未运行过的不可区分"**完全同族 ✓

**⇒ 三层**：
```text
对照：**两次左键 ⇒ 两个边**
实验：**五次按 3 ⇒ 零个边**
⇒ **⇒ 所以【按键确实到达 usercmd 而键 3 不**】
```

**✅ ⭐⭐ **一个"同一窗口内的对照"** —— 与 §412 的"`check_perframe_cost.py` 复核"不同（这是**实验内对照**）。

**⚠ 而"`OLMOD_LOG_CLIENT_COMMANDS=1` 记录每一个，有上限（`400`）"⇒ **一个有界开关**。**

**✅ 与 §427 的"首次目击每比特"**不同（那里**去重是对的**，这里**必须不去重**）。

**⇒ 三层**：
```text
§427  `button bits` ⇒ **首次目击每比特是对的**（**因为问的是"哪些位存在"**）
§428  `n <k>`       ⇒ **必须不去重**（**因为问的是"每次按下是否到达"**）
⇒ **⇒ 所以【去重与否取决于问题**】
```

**✅ ⭐⭐⭐ **一个"同一个手法在不同问题下相反"的实例** —— 本报告的核心洞察。

## 六、**`usercmd arrival` 探针的"按一个姿态位武装然后无条件一个窗口"**

### 6.1 那段

```php
// Section 185: the pmove sees cmdIn=0 for five consecutive frames while a
// player is prone, and the engine re-derives the stance from cmd.buttons
// EVERY frame (sub_417D10 LABEL_131), so no button means standing. Two
// explanations remain and they need opposite fixes: the client sends the
// toggle and stops, or the client sustains it and this server loses it
// between arrival and the pmove. cmdIn is the DECODED usercmd, so the only
// step it does not cover is this one -- ingress, the eight-slot queue and
// its overflow drops.
//
// Armed by a stance bit ARRIVING and then unconditional for a window, so
// the frames that matter (the ones with NO stance bit) are not filtered out
// by the very condition being measured. Section 184h paid for that lesson.
constexpr std::uint32_t StanceButtons = 0x100u | 0x200u;
static std::uint32_t arrivalWindow{};
for (const auto &command : processed.userCommands)
{
    if ((command.buttons & StanceButtons) != 0)
        arrivalWindow = 120;
    ...
}
```

### 6.2 二十层

```text
1. **第 `185` 节：`pmove` 在一个玩家趴着时【连续五帧看到 `cmdIn = 0`**】**
2. ⇒ **而引擎【每一帧**】从 `cmd.buttons` 重新推姿态（`sub_417D10`）
3. ⇒ **⇒ 所以【没有按钮意味着站立**】**
4. ⇒ **⇒ 两个解释【仍然存在**】而它们需要【相反的修复**】**
5. ⇒ **① 客户端发【一次切换就停**】** ⇒ **客户端的问题**
6. ⇒ **② 客户端【持续发**】而这个服务器【在到达与 `pmove` 之间【丢了它**】** ⇒ **服务端的问题**
7. ⇒ **`cmdIn` 是【解码后的 usercmd**】**
8. ⇒ **⇒ 所以【它不覆盖的唯一一步就是【这一步**】】**
9. ⇒ **（入口、八槽队列与它的溢出丢弃）**
10. ⇒ **⇒ 所以【探针在【入口处**】**
11. ⇒ **按【一个姿态位到达】武装，然后【无条件一个窗口**】】
12. ⇒ **⇒ 所以【那些要紧的帧（【没有**姿态位的）不会被【正在被测量的那个条件】过滤掉**
13. ⇒ **（第 `184h` 节为那个教训付过代价）**
```

### 6.3 ⭐⭐⭐ **"那些要紧的帧（没有姿态位的）不会被正在被测量的那个条件过滤掉"**

**✅ 这是本报告里**最重要的一条"观测者效应**。**

**⇒ 三层**：
```text
错误：**只记录带姿态位的帧** ⇒ **看不到"没有姿态位"的帧** ⇒ **而那正是问题**
正确：**按一个姿态位【武装**】然后【无条件记录一个窗口**】
⇒ **⇒ 所以【触发条件不能同时是过滤条件**】
```

**✅ 与 §410 的"`writeHudElems` 把 `Text` 当脉冲字幕"**不同（这是**一个观测设计**）。

**⇒ 三层**：
```text
§402  "`PMFLAGS|` 在变化时打一行" ⇒ **只看变化**（**而问题是"值是什么"**）
§428  **按位武装然后无条件记录** ⇒ **看到全部**
⇒ **⇒ 所以【"只看变化"与"看全部"取决于问题**】
```

**✅ ⭐⭐⭐ **一个"观测窗口的武装"** —— 与 §428 五 的"去重与否取决于问题"**同族**。</br>

**✅ 而"窗口 = `120`"⇒ **`120` 条命令**。**

**⇒ 三层**：
```text
`arrivalWindow = 120` ⇒ **一个计数窗口**（不是时间）
⇒ **⇒ 所以【在 `20Hz` 下约 `6` 秒**】（若是每帧一条）
```

**✅ ⭐ **一个"计数窗口"**。

**⚠ 而"`!OlMod::RuntimeLog::verbose()` ⇒ 默认关"**⇒ **热日志修复**。

**✅ 与 §402 的"`INF` 在 `warn` 下不可见"**相反**（这是**默认关，需要显式开**）。

**⇒ 三层**：
```text
§402  **太少（`INF` 被丢弃）** ⇒ 提级
§428  **太多（逐命令诊断）** ⇒ **默认关 + `verbose()` 门**
⇒ **⇒ 两个方向**
```

**✅ ⭐ **一个"日志量"的双向处理**。

## 七、**`SV_SendClientMessages` 的"一个被接纳的消息可以越过预算"**

### 7.1 那段

```php
// CODDIFF(sv_send_client_messages): CODOL has no retained server
// scheduler. The source budget is supplied by the caller rather
// than guessed from absent CODOL Live_GetNecessaryBandwidth dvars.
// As in BO1/BO2, one admitted message may cross the budget; the
// next due client resumes the ring on the following call.
if (bytesSent >= maximumBytesPerFrame)
{
    client.rateDelayed = true;
    ...
}
```

**⇒ 十层**：
```text
1. **CODOL 【没有保留的服务器调度器**】**
2. ⇒ **源预算【由调用方供给**】**
3. ⇒ **而不是【从缺席的 `Live_GetNecessaryBandwidth` dvar 猜**】**
4. ⇒ **与 `BO1`/`BO2` 一样，一个被接纳的消息【可以越过预算**】**
5. ⇒ **⇒ 而【下一个到期的客户端在下一次调用里【继续那个环**】】**
6. ⇒ **`client.rateDelayed = true`** ⇒ **一个标记**
```

### 7.2 ⭐⭐⭐ **"一个被接纳的消息可以越过预算"**

**✅ 这是本报告里**最重要的一条"预算的软性"**。**

**⇒ 三层**：
```text
硬预算：**`bytesSent + msg > budget` ⇒ 不发** ⇒ **可能【永远不发**】（若 `msg > budget`）
软预算：**发完检查** ⇒ **一个可以越过**
⇒ **⇒ 所以【软预算保证【进度**】**
```

**✅ 与 §413 的"`thinkBudget == 0` ⇒ 无上限"**不同（这是**一个软上限**）。

**⇒ 三层**：
```text
§413  `thinkBudget` ⇒ **`0` 表示无上限**（**哨兵**）
§428  `maximumBytesPerFrame` ⇒ **软上限**（**可以越过一次**）
⇒ **⇒ 两个不同的"上限"语义**
```

**✅ ⭐⭐ **一个"硬 vs 软上限"的区分**。

**⚠ 而"环（ring）"⇒ **`nextSnapshotSendClient_` 是一个轮转游标**。**

**⇒ 三层**：
```text
`startClient = nextSnapshotSendClient_ % clients_.size()`
`for (offset = 0; offset < size; ++offset)`
`clientNum = (startClient + offset) % size`
⇒ **⇒ 所以【每次都从上次停的地方开始**】 ⇒ **公平**
```

**✅ ⭐⭐ **一个"公平轮转"的实例**。

## 八、关键结论

1. **⭐⭐⭐ gamestate 死锁的六个环节**：**没有 gamestate → 客户端从不达到 `ClientLoading` → 从不发 `gamestateupdate 1..6` → 从不变 `Active` → `activeClients = 0` → `configurePendingWorldSpawn` 在第一行返回 → 没有世界、没有出生点、没有快照** ⇒ **屏幕上是一个永远坐在菜单/加载屏的客户端，运行时行 `clients=1 active=0 snapshots=0`，而【没有任何其它抱怨在任何地方】**。
2. **⭐⭐⭐ "四个项能把它关着，而日志一个都没命名"`** —— 第七次"多因歧义"（与 §405、§426 同族）；四个闸门（`PROFILE_STATS_INCOMPLETE(recv/req)` / `GENERATION_INACTIVE` / `GAMESTATE_NOT_CONFIGURED` / `NO_GAMESTATE_BUILDER`）**属于四个不同的层次**。
3. **⭐ "每个客户端每个不同的组合各一次"** ⇒ **按组合字符串去重** —— 第三种"复合状态去重"（与 §409 的 3 位、§426 的 6 位掩码同族）。
4. **⭐ `PROFILE_STATS_INCOMPLETE(0/0)` 是一个可判读的状态**（`required` 在第一块短块之后才非零）。
5. **⭐⭐ "`s` 被处理两次"**：**先 `queueScoreboardResponse`，然后 `SV_ParseMenuResponse` 失败，再走 `if (command == "s") continue;`** ⇒ **那个 `continue` 是为了不落入 `UNHANDLED` 日志** ⇒ **"一个已处理的命令必须显式跳过那个日志"`**。
6. **⭐⭐ `leave` 的三段式**（`dropClientSlot` + `break` + `clientLeft = true` ⇒ **然后提前返回**）—— **"释放后不触碰"**（第八次"槽释放"）。
7. **⭐⭐⭐ "`u 10` 意味着『打开在 CONFIGSTRING `4818` 里命名的那个菜单』，不是『屏幕十』"`** —— 而 **`sub_514880(_, n + 4808)` 是那个 CONFIGSTRING getter，它的类表 `byte_77D8250` 也是 `WeaponCountConfigStringIndex` 的来源**。
8. **⭐ "一个空的 configstring 让客户端回 `mr 10 bad` 而什么也不做；这个服务器填了那六十四个槽里的三个"`** ⇒ **`4808..4871` 是 `64` 个菜单槽**，而 **`4872` 是 §388 的 materials 带**（相邻）。
9. **⭐⭐⭐ "去重在这些是噪声时是对的，而现在它是错的，因为整个问题就是『某个 `n <k>` 是否每次按下到达一次』"`** —— 一个"去重的适用条件"的精确判据。
10. **⭐⭐ "键 `3` 完全不发一个 usercmd 按钮：两次左键给出恰好两个 `0x00000001` 边，五按下 `3` 给出零个"`** —— 一个**同窗口内的阳性对照**（与 §427 的"沉默仪器不可区分"同族）。
11. **⭐⭐⭐ "`button bits` 的首次目击每比特是对的（问的是『哪些位存在』）；`n <k>` 必须不去重（问的是『每次按下是否到达』）⇒ 去重与否取决于问题"`** —— 同一个手法在不同问题下相反，本报告的核心洞察。
12. **⭐⭐⭐ `usercmd arrival` 探针的"按一个姿态位到达武装，然后无条件一个窗口"** ⇒ **"那些要紧的帧（没有姿态位的）不会被【正在被测量的那个条件】过滤掉"`** —— 一个"触发条件不能同时是过滤条件"的观测设计。
13. **⭐ 窗口是 `120` 条命令**（不是一个时间），而 `arrivalLines < 400`、`verbose()` 门 ⇒ **热日志默认关**。
14. **⭐⭐ `SV_SendClientMessages` 的软预算**：**"与 `BO1`/`BO2` 一样，一个被接纳的消息可以越过预算；下一个到期的客户端在下一次调用里继续那个环"`** —— **软预算保证进度**（硬预算可能永远不发）。
15. **⭐ 公平轮转**：`startClient = nextSnapshotSendClient_ % size`，然后 `(startClient + offset) % size` ⇒ **每次都从上次停的地方开始**。

## 九、未闭合点

- `cs 4808` 的菜单带与 `WeaponCountConfigStringIndex` 的共同类表。
- 本服务器填的三个菜单槽是哪三个。
- `configurePendingWorldSpawn` 的"第一行返回"。
- `gameStateGateReport` 是否在成功后清空。
- `StanceButtons = 0x100 | 0x200`（`PRONE`/`CROUCH`）。
- `sv_client_mp.cpp` 1440 行之后未读取（**共 `4500` 行**）。
