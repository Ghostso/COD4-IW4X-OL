# 413 · **`sv_main_mp.cpp` 全文件收尾** —— "一个累积预算把自己的基准固定了"、`clientInfo` 的 `0x154` vs `0x090`、以及运行帧的完整阶段表

## 一、范围

本报告学习 `sv_main_mp.cpp` 11160–11940 行（`runFrame` 全程），并收尾整个文件（**实际 `11,940` 行**）。

## 二、**`thinkBudget` 的"基准必须随它前进"**（本组最重要的一段）

### 2.1 那段

```php
// AND THE BASE HAS TO ADVANCE WITH IT, OR THE BUDGET IS
// CHARGED THE SAME MILLISECONDS OVER AND OVER.
//
// Ghosts charges max(cmd.serverTime - ps.commandTime, 0)
// and ps.commandTime is advanced BY the pmove inside the
// think, so its next iteration measures from the command
// it just ran. This read ps.commandTime once before the
// loop and never moved it, so commands 8ms apart were
// charged 8, then 16, then 24, then 32 -- the 100ms budget
// gone after five instead of twelve.
//
// AND IT COMPOUNDS. The further behind a client falls, the
// larger the FIRST delta, until one command spends the
// whole budget and the server runs exactly one command per
// frame -- which puts it further behind again. Measured
// with one client tabbed in and both queues saturated:
//
//     pending=7 cmdAge=-513 recvExec=40   (capacity is 8)
//     pending=7 cmdAge=-464 recvExec=73
//     thinkCommands=85 per window, ~17/s executed against
//     ~140/s arriving
//
// cmdAge NEGATIVE is the symptom to remember: the client's
// newest command is half a second AHEAD of what the server
// has executed, which is exactly what a player feels.
playerCommandTime = std::max(playerCommandTime, command->commandTime);
```

### 2.2 二十四层

```text
1. **基准必须随它前进，否则【预算是同样的毫秒被反复扣**】**
2. ⇒ **Ghosts 扣的是 `max(cmd.serverTime - ps.commandTime, 0)`**
3. ⇒ **而 `ps.commandTime` 【由 think 里的 pmove 推进**】**
4. ⇒ **所以它的下一次迭代【从它刚跑过的那个命令】测量**
5. ⇒ **而我方【在循环之前读一次 `ps.commandTime` 而【从不移动它**】】**
6. ⇒ **⇒ 所以相隔 `8ms` 的命令被扣成 `8`、然后 `16`、然后 `24`、然后 `32`**
7. ⇒ **⇒ `100ms` 预算【在第五条而不是第十二条】就用完**
8. ⇒ **而它【会复合**】**
9. ⇒ **一个客户端落后得越远，【第一个 delta 越大**】**
10. ⇒ **直到【一个命令花掉整个预算**】**
11. ⇒ **⇒ 服务器【每帧只跑一个命令**】**
12. ⇒ **⇒ 而那又【让它更落后**】**
13. ⇒ **⚠ 而 `cmdAge` **为负**是【要记住的那个症状**】**
14. ⇒ **客户端最新的命令比服务器已执行的【超前半秒**】
15. ⇒ **⇒ 那正是【一个玩家感觉到的东西**】**
```

### 2.3 ⭐⭐⭐ **"预算是同样的毫秒被反复扣"**

**✅ 这是本报告里**最重要的一个计量错误**。**

**⇒ 三层**：
```text
正确：`charges[i] = t[i] - t[i-1]` ⇒ **总和 = t[n] - t[0]**
错误：`charges[i] = t[i] - t[0]`  ⇒ **总和 = n·(t[n] - t[0])/2**（三角形）
⇒ **⇒ 所以【同样的时间被算了 O(n) 次**】
```

**✅ 与 §409 的"`advanceSdRound` 的位移判据"**不同（这是**一个累积量**）。

**⇒ 三层**：
```text
§412  `BotStuckCheckMilliseconds`：**判据的等价速度被改了**
§413  `playerCommandTime`：**累积的基准被固定了**
⇒ **⇒ 两处都是【改一个量而改变了一个派生量**】
```

**✅ ⭐ **第五次"派生量被忽略"**。

**⚠ 而"会复合"⇒ **一个正反馈回路**。**

**✅ 与 §406 的"服务器每帧只跑一个命令 ⇒ 更落后"**完全闭合 ✓

**⇒ 三层**：
```text
落后 ⇒ `delta` 大 ⇒ **一次花光预算** ⇒ **只跑一个命令** ⇒ **更落后**
⇒ **⇒ 一个【自增强的退化**】
```

**✅ ⭐⭐ **一个"正反馈回路"的完整描述**。

### 2.4 而**"`cmdAge` 为负"**

**⇒ 五层**：
```text
`cmdAge = ps.commandTime - cmd.commandTime`
若 **`cmdAge < 0`** ⇒ **命令【超前**】服务器已执行的位置
⇒ **⇒ 而那不是"滞后"而是【积压**】**
```

**⚠ 这个符号约定需要标注**：通常 `cmdAge` 会是"命令有多旧"，即 `now - cmdTime` 为正。这里**为负**说明**客户端的时间戳领先服务器**。

**✅ 与 §402 的"`pending=7 cmdAge=-513`"**（在同一处出现过）**完全闭合 ✓

**⇒ 三层**：
```text
`capacity is 8` ⇒ **队满**（`pending = 7` 已接近 8）
`recvExec = 40` vs `73` ⇒ **接收 73 而执行 40**
`~17/s executed` vs `~140/s arriving`
⇒ **⇒ 所以【积压**】
```

**✅ ⭐⭐⭐ **"执行 17/s 而到达 140/s"** —— 一个**极清晰的数量级差距**。

**✅ 与 §392 的"`6160` 快照 / `621.4s = 9.9/s` 对 `19.9/s`"**同族（**第六次"数量级差距"）。

### 2.5 而**`SV_ClientThinkBudgetMilliseconds` 的 `0`**

```cpp
const auto thinkBudget = SV_ClientThinkBudgetMilliseconds();
while (!thinkBudget || cumulativeThinkTime < thinkBudget)
```

**⇒ 四层**：
```text
1. **`!thinkBudget` ⇒ `budget == 0` ⇒ 【无上限**】**
2. ⇒ **`cumulativeThinkTime < thinkBudget` ⇒ 有上限**
3. ⇒ **⇒ 所以 `0` 是一个【哨兵值**】**
4. ⇒ **（与 §392 的 `SV_ClientThinkBudgetMilliseconds -> 0（drain the bounded queue）`**一致**）**
```

**✅ 与 §413 二 的"`100ms` 预算在第五条用完"**形成对照**：**`0` 就是为了绕开那个问题**。**

**⇒ 三层**：
```text
`100ms` 预算 ⇒ **五条命令后到底**（基准固定时）
`0`（无上限）⇒ **排空有界队列**（`PendingUserCmdCapacity = 32`）
⇒ **⇒ 所以 `0` 把"时间预算"换成【数量上界**】
```

**✅ ⭐⭐ **"把时间上界换成数量上界"** —— 一个**更稳健的设计**（因为数量上界不会受累积误差影响）。

**⚠ 而 §392 说 `PendingUserCmdCapacity 8 -> 32`** ⇒ **所以队列本身就是上界**。

## 三、`clientInfo` 的 `0x154` vs `0x090`（本组第二重要）

### 3.1 那段

```php
//   ① 客户端 clientInfo 的 faction 字段读作 **12 行全 0**（Tf）——
//      只读 RPM 实读 `clientInfo+0x154`，pid 6272，2026-10-16：
//      `[0,0,0,0,0,0,0,0,0,0,0,0]`（脚本 probe_clientinfo_faction_offsets.py）。
//      同一次读数还**纠正了一份已落盘结论**：`-22280 §3.2` 把
//      `clientInfo+0x090` 当作 faction（"0 vs 1"），实读该偏移是
//      **clientNum-1**（序列 `[?,0,1,2,…,10]`），不是 faction。
```

### 3.2 十四层

```text
1. **客户端 `clientInfo` 的 faction 字段读作【12 行全 0**】（Tf）
2. ⇒ **只读 RPM 实读 `clientInfo + 0x154`**
3. ⇒ **pid `6272`，2026-10-16**
4. ⇒ **`[0,0,0,0,0,0,0,0,0,0,0,0]`**
5. ⇒ **（脚本 `probe_clientinfo_faction_offsets.py`）**
6. ⇒ **同一次读数【还纠正了一份已落盘结论**】**
7. ⇒ **`-22280 §3.2` 把 `clientInfo + 0x090` 当作 faction（"0 vs 1"）**
8. ⇒ **实读该偏移是【`clientNum - 1`**】**
9. ⇒ **（序列 `[?,0,1,2,…,10]`）**
10. ⇒ **⇒ 【不是 faction**】**
```

### 3.3 ⭐⭐⭐ **"一次读数纠正了一份已落盘结论"**

**✅ 这是本报告里**最重要的一次偏移自证**。**

**⇒ 三层**：
```text
`+0x090` 读出 `[?,0,1,2,…,10]` ⇒ **一个等差序列**
faction 只可能是 `0/1` ⇒ **而 `0..10` 不是**
⇒ **⇒ 所以 `+0x090` 是【clientNum**】而不是 faction**
```

**✅ ⭐⭐ **"序列的形状否证了它的语义"** —— 一个**极强的自证手法**。

**✅ 与 §397 的"`isAllowed("")` 在两种读法下都返回 `true` ⇒ 零信息"**相反**（这是**一个模式在两种假设下只成立一个**）。

**⇒ 三层**：
```text
假设 A：`+0x090` = faction ⇒ **应该只有 0/1**
观察：`0..10` ⇒ **不可能**
假设 B：`+0x090` = clientNum ⇒ **正好 0..10**
⇒ **⇒ 所以【形状排除了 A**】
```

**✅ ⭐⭐⭐ **一个"用数据的形状排除假设"的范例**。

**⚠ 而"`[?,0,1,2,…,10]`"⇒ `?` 是 client 0 的值**（**可能是 `-1` 或 `0xFF`**）。

**⇒ 三层**：
```text
client 0 ⇒ **`?`**（未打印或异常值）
client 1..11 ⇒ **`0,1,2,…,10`**
⇒ **⇒ 所以是 `clientNum - 1`**（client 0 应为 `-1` ⇒ 无符号下是 `0xFFFFFFFF`）
```

**✅ 一个**可推导的语义**。

### 3.4 而**"服务端写线是对的，缺口在 provider"**

```php
//   ② 服务端写线是对的：`ClientInfoFactionField` ← `state.customization.faction`
//      （sv_snapshot_mp.cpp:5536-5538，1 bit）。
//   ③ 缺口在 provider：bot 的 customization 是**复制已发布真人成员的资产**
//      （Appmain.cpp:4910-4959 "NOTHING IS INVENTED … a COPY of that
//      member's assets"），副本里的 faction 是**真人的 Tf(0)**；
//      这里传入的 `clientSlots[index].characterFaction`（bot 的 Sc=1，
//      由 -22270 对齐）被 provider 忽略 ⇒ 写线发出 0 ⇒ 客户端全 0 ⇒
//      名字色/小地图/UAV 不区分敌我（甲方"我队友不像我队友"）。
```

**⇒ 十六层**：
```text
1. **服务端写线是【对的】**：`ClientInfoFactionField` ← `state.customization.faction`（**1 bit**）
2. ⇒ **缺口在【provider**】**
3. ⇒ **bot 的 customization 是【复制已发布真人成员的资产**】**
4. ⇒ **（`Appmain.cpp:4910-4959` "NOTHING IS INVENTED … **a COPY of that member's assets**"）**
5. ⇒ **⇒ 副本里的 faction 是【真人的 `Tf(0)`**】**
6. ⇒ **而这里传入的 `clientSlots[index].characterFaction`（bot 的 `Sc = 1`）【被 provider 忽略**】**
7. ⇒ **⇒ 写线发出 `0`**
8. ⇒ **⇒ 客户端全 `0`**
9. ⇒ **⇒ 名字色/小地图/UAV **不区分敌我**】
10. ⇒ **甲方原话**：「我队友不像我队友」
```

### 3.5 ⭐⭐ **"一个正确的写线被一个错误的输入毁掉"**

**✅ 与 §410 的"机制从来没有错，缺的是第三个白名单"**完全同族（**第三次"实现正确而接线错误"）。**

**⇒ 三层**：
```text
写线：`ClientInfoFactionField` ← `customization.faction` ⇒ **1 bit，正确**
输入：`customization.faction` 是**真人副本的 `0`**
⇒ **⇒ 所以【写线忠实传递了一个错误的输入**】
```

**✅ ⭐ **一个"GIGO"的精确实例**（garbage in, garbage out）。

**⚠ 而"修法：只在返回值上覆盖 faction 一个字节"⇒ **单变量**。**

**✅ 与 §411 的"单变量"**同族（**第九次）。

**⇒ 三层**：
```text
修 `characterItemId`/`modelIndex` ⇒ **会改变模型**
只修 `faction` ⇒ **只改变敌我显示**
⇒ **⇒ 所以【后者是单变量**】
```

**✅ ⭐ **一个"选择最小改动面"的精确理由**。

**⚠ 而"`Appmain.cpp:4910-4959` 'NOTHING IS INVENTED … a COPY of that member's assets'"⇒ **一个设计声明**。**

**⇒ 三层**：
```text
设计意图："不去发明，只复制一个已发布成员的资产"
副作用：**复制了 `faction`**
⇒ **⇒ 所以那个"不发明"的纪律【产生了这个 bug**】
```

**✅ ⭐⭐ **"一个正确的纪律在它的边界外产生了错误"** —— 一个**极微妙的观察**。

### 3.6 而**"一个已解析过一次的玩家不再停止被发布"**

```php
// AND A PLAYER WHO HAS RESOLVED ONCE NEVER STOPS BEING PUBLISHED.
// Section 166: this provider answers per frame and nothing retained
// its answer, so one frame it could not answer removed that client's
// clientInfo from every observer and left them invisible. Remember
// the last good one and fall back to it; a NEW answer always wins,
// so a mid-match character change still lands.
```

**⇒ 十层**：
```text
1. **一个已经解析过一次的玩家【不再停止被发布**】**
2. ⇒ **这个 provider 【每帧回答**】**
3. ⇒ **而【没有任何东西保留它的答案**】**
4. ⇒ **⇒ 所以【有一帧它答不出】就删掉了那个客户端的 `clientInfo`**
5. ⇒ **⇒ 从【每一个观察者**】那里** ⇒ 让他们**不可见**】**
6. ⇒ **记住最后一个好的并回退到它**
7. ⇒ **而【一个新的答案总是赢**】**
8. ⇒ **⇒ 所以一场比赛中的角色变化【仍然落地**】**
```

**✅ ⭐⭐⭐ **"一帧答不出 ⇒ 从每一个观察者那里消失"** —— 与 §411 的"bot 存在但从不被渲染"**同族（**第三次"存在但不可见"）。**

**⇒ 三层**：
```text
§410  obituary 到达不了 ⇒ **没有 feed**
§411  bot 没有 apply 的出生 ⇒ **从不渲染**
§413  provider 一帧答不出 ⇒ **从所有观察者消失**
⇒ **⇒ 三条都是"实体存在而客户端看不到**】
```

**✅ ⭐ **一个"可见性"的三例表**。

**⚠ 而"记住最后一个好的并回退，而新答案总是赢"⇒ **一个"缓存但让新值优先"的模式**。**

**✅ 与 §400 的"缓存键必须含那个状态"**同族（**第三次"缓存"）。

**⇒ 三层**：
```text
缓存：`lastCharacterCustomizations_[clientNum]`
失效条件：**`xuid` 不同**（换了人）
⇒ **⇒ 所以【槽复用被挡住**】
```

**✅ ⭐ **一个"缓存必须绑定身份"的实例**。

## 四、`weaponSelectSequences_` 的 `a <weapon>` 去重（本组第三重要）

### 4.1 那段

```php
// ★★ 28100 刀BN（第 ⑥ 项 A1「传奇武器双模式切换卡顿/丢瞄准镜」）——
//   零售画武器**极轻**（`0C-2020-4-11[11-11-11]cha.demo` 全片仅 18 条 `a`，
//   重生段就一条 `a 1378`），而我方**只要 `loadoutSequence` 变就补发
//   `a <primary>`** ⇒ 玩家按 3 切到 alt 模式时，服务端会把客户端**拽回主武器**
//   ⇒ 表现就是"卡一下 / 闪回 / 丢镜"。
//   ⇒ 本刀加**去重**：只有当**主武器索引真的变了**才补发。
```

### 4.2 十四层

```text
1. **零售画武器【极轻**】**
2. ⇒ **`cha.demo` 全片【仅 `18` 条 `a`**】**
3. ⇒ **重生段就【一条 `a 1378`**】**
4. ⇒ **而我方【只要 `loadoutSequence` 变就补发 `a <primary>`**】**
5. ⇒ **⇒ 玩家按 `3` 切到 alt 模式时**
6. ⇒ **服务端会把客户端【拽回主武器**】**
7. ⇒ **⇒ 表现就是"卡一下 / 闪回 / 丢镜"**
8. ⇒ **本刀加去重：只有【主武器索引真的变了**】才补发**
```

### 4.3 ⭐⭐⭐ **"按 3 切到 alt 模式 ⇒ 服务端把客户端拽回主武器"**

**✅ 与 §404 的"撤掉 `a <weapon>`"**完全闭合 ✓

**⇒ 三层**：
```text
§404  `a <weapon>` 从**重生簇**撤掉（因为崩）
§413  `a <weapon>` 从**背包切换**去掉重（因为拽回）
⇒ **⇒ 两处都在收缩 `a` 的发送**
```

**✅ 而 §403 的"`a` 要求 cgame 画一把它必须已经拥有的武器"**是语义**。**

**⇒ 三层语义汇总**：
```text
`a <n>` 的语义：**让 cgame 画一把它已经拥有的武器**（§403）
副作用：**会把当前显示拽到 `n`**（§413）
⇒ **⇒ 所以【在 alt 模式切换时它是破坏性的**】
```

**✅ ⭐⭐ **"一个命令的语义正确而它在某个语境下有害"** —— 一个**极重要的区分**。

**⚠ 而"`A_RESEND|` 日志"⇒ **一个 A/B 判据**。**

**✅ 与 §410 的"`loot BUTTONS` 为未确认常量专设"**同族（**第二次"为一次核对专设日志"）。

**⇒ 三层**：
```text
问题：**按 3 切模式时服务器有没有插一脚？**
工具：**`A_RESEND|client=… weapon=… seq=…`** 与 **`skipped weapon-unchanged=…`**
⇒ **⇒ 所以一次按键就从日志判定**
```

**✅ ⭐ **一个精确的 A/B 仪器**。

### 4.4 而**"`backpackSwap = tracked != 0`"**

```cpp
auto &tracked = weaponSelectSequences_[clientNum];
const auto sequence = clientSlots[index].loadoutSequence;
if (tracked != sequence) {
    const bool backpackSwap = tracked != 0;
    tracked = sequence;
    ...
}
```

**⇒ 五层**：
```text
1. **`tracked != sequence` ⇒ 序列变化**
2. ⇒ **`backpackSwap = tracked != 0`**
3. ⇒ **⇒ 所以【首次（`tracked == 0`）不算背包切换**】**
4. ⇒ **而【首次也不需要发 `a`**】（**因为"already displays right"**）
5. ⇒ **⇒ 与 §411 的 `BotLoadoutSequence = 1` 是【同一个边沿编码**】
```

**✅ ⭐ **第三次"用 `0` 表示『还没发生过』"**。

**⇒ 三层**：
```text
§411  bot 的 `loadoutSequence` **从 `1` 开始** ⇒ `0` 保留给"未初始化"
§413  人类路径 `tracked` **从 `0` 开始** ⇒ `0` 表示"首次"
⇒ **⇒ 两条路径用同一个哨兵**
```

**✅ 而 §411 的注释说"`weaponSelectSequences_ keys on the same value and starts at 0`"**—— **完全闭合** ✓

**⇒ 三层**：
```text
bot：`BotLoadoutSequence = 1` ⇒ **第一次提交时 `tracked` 是 `0` 而 `sequence` 是 `1`**
人类：`loadoutSequence` 由客户端给 ⇒ **第一次时 `tracked` 是 `0`**
⇒ **⇒ 两者都走 `backpackSwap = false`**
```

## 五、**`BATTLE ROYALE` 的三次尝试与两个"不是空的"**

### 5.1 那段

```php
// BATTLE ROYALE SPAWN LOADOUT: TRIED, REVERTED, FINDING KEPT.
// ...
// The obvious small step -- copy `secondary` over `primary` so the player
// keeps only a sidearm -- was tried 2026-09-05 03:23 AND IS WRONG ON THIS
// BUILD. Measured: the player spawned holding `weap=1148`, which is the
// FIRST LOOT-BAND INDEX, with no weapon name and 0 ammo on the HUD. The
// secondary slot does not resolve to a usable sidearm here, so the swap
// trades a working CheyTac for an unusable weapon.
//
// AND "SPAWN WITH NOTHING" IS NOT AVAILABLE EITHER. Section 152y: an
// Active client with no loadout gets `viewmodelIndex = 0`, a zero
// viewmodel makes the client's sub_53F5F0 return null, and sub_59CC70
// writes through it unchecked -- an access violation, not an empty
// inventory.
```

### 5.2 二十层

```text
1. **尝试过、回退了、但保留发现**
2. ⇒ **玩家进 `mp_battlecity` 的第一句话是"我用我的 TDM 职业出生了"**
3. ⇒ **而他们是对的**：**`dmz.lua` 是 `dm.lua` 的副本** ⇒ **BattleCity 跑死斗规则并发存档职业**
4. ⇒ **零售在首生发【一把】武器**（`a 1213`，`C-2021-7-25[22-0-7]dmz` 的 seq 34），**其余靠捡**】
5. ⇒ **明显的小步（把 `secondary` 拷到 `primary`）在 2026-09-05 03:23 试过【而这个 build 上是错的**】**
6. ⇒ **测量：玩家出生持有 `weap = 1148`**
7. ⇒ **⇒ 那是【loot 带的第一个索引**】**
8. ⇒ **而 HUD 上【没有武器名、`0` 弹药**】**
9. ⇒ **⇒ `secondary` 槽在这里【不解析到一把可用的副武器**】**
10. ⇒ **所以那个交换把一把【能用的 CheyTac】换成一把【不能用的武器**】**
11. ⇒ **而"空手出生"【也不可用**】**
12. ⇒ **第 152y 节：一个没有 loadout 的 `Active` 客户端得到 `viewmodelIndex = 0`**
13. ⇒ **而零 viewmodel 让客户端的 `sub_53F5F0` **返回 null**】
14. ⇒ **而 `sub_59CC70` **不检查地**通过它写入 ⇒ **一个访问违例**】
15. ⇒ **⇒ 【不是一个空库存**】**
16. ⇒ **所以真正的 BR 出生需要【loot 系统能够交还一把武器**】**
17. ⇒ **在职业能被拿走之前**
18. ⇒ **⇒ 在那之前职业留着：它对那个模式是错的但它【可玩**】**
19. ⇒ **⇒ 【那是两者中更好的那个**】**
```

### 5.3 ⭐⭐⭐ **"零 viewmodel ⇒ 访问违例，不是一个空库存"**

**✅ 与 §407 的"`battery_multiplier` 缺失 ⇒ `0xC0000094` 除零"**完全同族（**第二次"零不是一个中性值"）。**

**⇒ 三层**：
```text
意图：**空手**（视觉上不显示武器）
实现：`viewmodelIndex = 0`
后果：**客户端 `sub_53F5F0` 返回 null，`sub_59CC70` 不检查地写入 ⇒ AV**
⇒ **⇒ 所以"没有武器"在【这个引擎里不是一个可表达的状态**】
```

**✅ ⭐⭐ **"一个缺失的值不是一个中性的默认，而是一个崩溃"** —— 第三次确认那条见证概念。

### 5.4 而**"`1148` 是 loot 带的第一个索引"**

**✅ 与 §388 的"`1147..1154` 八个模块化武器"**完全闭合 ✓

**⇒ 三层**：
```text
§388  `firstDynamicWeapon = 1147`，注册了 `1147..1154`
§413  `secondary` 解析到 `1148` ⇒ **loot 带的第二个索引**
⇒ **⇒ 所以 `secondary` 【解析到了一个 loot 武器而不是副武器**】
```

**⚠ 一处**数值差异**：注释说 `1148` 是"FIRST LOOT-BAND INDEX"，而 §388 说 `1147` 是 `firstDynamicWeapon`。**

**⇒ 三层**：
```text
`1147` ⇒ `firstDynamicWeapon`（§388/§402）
`1148` ⇒ 注释说的 "FIRST LOOT-BAND INDEX"（§413）
⇒ **⇒ 相差 1** ⇒ **可能是【两个不同的带的起点**】
```

**⚠ 一个**需要标注的差**。

## 六、**`UAV` 与 `weapon changes` 的观测**

```cpp
observeUavWeaponChanges(pending);
```

**⇒ 四层**：
```text
1. **每次世界事件批次都调 `observeUavWeaponChanges`**
2. ⇒ **所以 UAV 的持有者【按武器变化追踪**】**
3. ⇒ **（`_codol.gsc` 的 `setTeamRadar(team,1)` + `codol_radar_off(team,30)`）**
4. ⇒ **与 §410 的"UAV 雷达依据 `_codol.gsc` 原文"**一致**
```

**✅ 与 §410 的"只发命令 / 只写雷达到期时间，不碰伤害、死亡、武器路径"**配合。

## 七、**`runFrame` 的完整阶段表**（本组第四重要）

```text
0.  `++status_.frameNumber`
1.  `clients_.publishZmRoundHud(frameNumber)`   ← **NOT at enter-world**（§12.132）
2.  构造 `activeClients`：
      · 解析 pending loadout
      · 解析/复用 `resolvedLoadouts_`
      · `a <weapon>` 去重（`A_RESEND|`）
      · 填 `characterCustomization` + `characterOptionMask`（**顺序有依赖**）
      · **faction 对齐**（刀G）
      · **记住最后一个好的 customization**
      · `precacheCharacterModels`
3.  `erase_if` ×3（清理已离开的客户端）
4.  `world_.beginFrame(frameMilliseconds, activeClients)`   ← **失败 ⇒ 报 + return**
5.  `trackMatchParticipation`
6.  `world_.stepZombieRevives()` + 团灭检测
7.  `scriptRuntime_.advance(serverTime)`
8.  `dispatchPendingWorldEvents()`          ← **spawn/killed 的延迟通知**
9.  `driveBotClients()`                     ← **bot 的命令在这里入队**
10. killcam 档案（`OLMOD_KILLCAM_ARCHIVE`）
11. **client-think 循环**（`thinkBudget`）：
      · `SV_KillcamArchiveRecord`
      · `dispatchNextPendingUserCmd`
      · `SV_ChargeClientThinkTime`
      · `world_.clientThink`
      · 拒绝 ⇒ `discardRejectedUserCmd` / `discardUnsupportedUserCmd`
      · 提交 ⇒ `commitExecutedUserCmd`
      · `processSdCommittedCommand` / `processLootCommittedCommand` / `processZmUseCommittedCommand`
      · `dispatchPendingWorldEvents()`
12. `advanceSdRound()` 或 `evaluateSdRound()`
13. `projectSdObjectives` / `projectClientHudElems` / `driveClientUav`
14. `announceConnectionChanges` / `announceMatchRules` / `driveMatchAnnouncer`
    / `driveBattleChatter` / `announceSoundAliases` / `announceFactorySoundAliases`
    / `announceLoadoutDvars` / `announceVisionSet` / `projectDeathVision`
    / `announceMatchCompletion` / `driveMatchEndSequence` / `holdMatchCompletionState`
15. `pumpSdSoundQueues`
16. `dispatchPendingWorldEvents()` / `publishDirtyScoreboard("inmatch_update")`
17. **`tag_weapon_right` 的 12248 带解析**（一次性）
18. `world_.endFrame(activeClients)`        ← **失败 ⇒ 报 + return**
19. `dispatchPendingWorldEvents()`  ← **endFrame 之后的第三次**
20. `logPlayerPresentation()`                ← **必须在 endFrame 之后**
21. **obituary 归档核对**（读【已发布】的快照）
22. `status_.serverTime = snapshot.serverTime`
23. **比赛时限判定**（`SV_UpdateMatchTimeLimit`）
24. `clients_.setWorldFrame(snapshot, &validationFailure)`
25. 六段计时记录
```

**⇒ 二十五个阶段。**

### 7.1 ⭐ **"三次 `dispatchPendingWorldEvents`"**

**⇒ 三层**：
```text
第 8 步 ⇒  **beginFrame 之后、client-think 之前**（spawn/killed 的延迟通知）
第 11 步（循环内）⇒ **每条命令之后**（同步语义）
第 16 步 ⇒ **HUD 投影之后、endFrame 之前**（未被命令产生的模式事件）
第 19 步 ⇒ **endFrame 之后**（endFrame 发现的"断开连接"）
⇒ **⇒ 四次**
```

**⚠ 注释说"Mode-owned events that were not produced by one exact command still drain before ClientEndFrame. Notifications discovered by endFrame drain at the second call below."**

**⇒ 三层**：
```text
"the second call below" ⇒ **指的是第 19 步**
⇒ **⇒ 所以注释数的是【第 16 与第 19 = 第 1 与第 2 次**（在 endFrame 前后这个尺度上）
```

**✅ ⭐ **一个"注释与代码的计数口径不同"的实例**（**不影响正确性**）。

### 7.2 而**"`logPlayerPresentation` 必须在 `endFrame` 之后"**

```php
// After endFrame, not before: world_.snapshot() is only the frame the
// clients will actually be sent once endFrame has published it, and
// reading it earlier found no ET_PLAYER entities at all.
```

**⇒ 五层**：
```text
1. **必须在 `endFrame` 之后**
2. ⇒ **因为 `world_.snapshot()` 只有【在 `endFrame` 发布了它之后**】才是客户端真正会收到的那个帧**
3. ⇒ **而【更早读它找到【完全没有 `ET_PLAYER` 实体**】】**
4. ⇒ **⇒ 所以【顺序不是风格问题而是正确性问题**】**
```

**✅ ⭐⭐ **"更早读它找到一个空集合"** —— 一个**极清晰的顺序依赖证据**。

**✅ 与 §409 的"`sdOriginText` 是模板 on purpose"**不同（这是**一个读的时机**）。

**⇒ 三层**：
```text
§413  `snapshot()` 在 `endFrame` 前 ⇒ **空**（约等于"变量未初始化"）
⇒ **⇒ 而这不是【一个慢的问题而是【一个空数据的问题**】
```

**✅ ⭐ **第二次"读一个还没发布的量"**。

### 7.3 而**"obituary 创建与发出是两个声明"**

```php
// AN OBITUARY THAT IS CREATED AND AN OBITUARY THAT IS SENT ARE
// DIFFERENT CLAIMS, and spawnObituaryEvent only proves the first.
// shouldArchiveWorldEntity is a fail-closed allow-list, so a missing
// eType there drops the entity with no log anywhere. This reads the
// PUBLISHED snapshot -- the one the clients are about to be sent.
```

**⇒ 八层**：
```text
1. **"被创建"与"被发出"是【两个不同的声明**】**
2. ⇒ **`spawnObituaryEvent` 只证明【第一个**】**
3. ⇒ **`shouldArchiveWorldEntity` 是一个【fail-closed 白名单**】**
4. ⇒ **所以那里一个缺失的 eType 【静默地丢掉那个实体**】**
5. ⇒ **（【没有日志在任何地方**）】
6. ⇒ **⇒ 所以这个核对读【已发布】的快照**
7. ⇒ **⇒ 那个客户端即将被发送的**
8. ⇒ **并用 `archivedObituaries_` 去重**
```

**✅ ⭐⭐⭐ **"创建与发出是两个不同的声明"** —— 与 §410 的"三条白名单"**完全闭合 ✓

**⇒ 三层**：
```text
§410  `spawnObituaryEvent` 返回真 ⇒ **对象建了**
§410  第三个白名单缺 eType ⇒ **整帧拒收**
§413  **核对已发布快照里有没有那个 `EntityTypeObituary`**
⇒ **⇒ 所以这是【端到端**的确认**
```

**✅ ⭐⭐ **"一个端到端的核对"** —— 第四次"用发布后的状态验证"。

**⚠ 而"fail-closed 白名单"⇒ **与 §410 的三条白名单是同一批**。**

**⇒ 三层**：
```text
`spawnObituaryEvent` ⇒ **创建**
`shouldArchiveWorldEntity` ⇒ **归档**（第 2 条白名单？）
帧级白名单 ⇒ **发送**（第 3 条）
⇒ **⇒ 三个环节各有一个白名单**
```

**✅ ⭐ **与 §410 的"三条独立的 eType 白名单"**完全闭合 ✓

## 八、**`reportWorldFrameRejection` 的"说它出来"**

```php
// SAY SO. A world phase that rejects publishes no playerStates, and the
// only thing the log then showed was `missing_playerstate` from the
// SNAPSHOT WRITER -- which is a symptom two layers downstream and names
// the wrong suspect. That cost a session: the real fault was an access
// violation inside BG_UpdatePlayerDObj poisoning the native entity
// mirror. Edge-triggered, so a healthy server stays silent.
```

**⇒ 十层**：
```text
1. **说它出来**
2. ⇒ **一个拒绝的世界阶段【不发布任何 playerState**】**
3. ⇒ **而那时日志只显示【快照写者的 `missing_playerstate`**】**
4. ⇒ **那是【往下两层的症状】而【命名了错误的嫌疑**】**
5. ⇒ **那花了【一整个会话**】**
6. ⇒ **真正的故障是 `BG_UpdatePlayerDObj` 内部的【一个访问违例**】**
7. ⇒ **它【污染了原生实体镜像**】**
8. ⇒ **边沿触发 ⇒ 所以健康的服务器【保持沉默**】**
```

### 8.1 ⭐⭐⭐ **"一个往下两层的症状命名了错误的嫌疑"**

**✅ 与 §405 的"『领先/失去是静默的』有三个可能的所有者"**同族（**第八次"多因歧义"）。**

**⇒ 三层**：
```text
症状：`missing_playerstate`（快照写者）
真因：`BG_UpdatePlayerDObj` 的 AV（世界层）
距离：**两层**
⇒ **⇒ 所以【症状的位置不等于根因的位置**】
```

**✅ ⭐⭐ **"症状的位置与根因的位置无关"** —— 一个**极重要的诊断纪律**。

**⚠ 而"那花了一整个会话"⇒ **一个可量化的代价**。**

**✅ 与 §404 的"值得一个周期"**同族（**第五次"每个错误的代价"）。**

**⇒ 三层**：
```text
§402  "四个周期与四个负面" ⇒ **方法错**
§413  "一整个会话" ⇒ **症状在上游而根因在下游**
```

**✅ ⭐ **两种不同的浪费**。

## 九、**`SV_UpdateMatchTimeLimit` 的两条分支**

```cpp
if (SV_UpdateMatchTimeLimit(matchStatus_, matchGameType_, status_.serverTime,
        tf, sc))
{
    if (matchGameType_ == "dm")
    {
        // The team scores it just compared are both 0 in a teamless
        // mode, so it will have called the match a draw.
        // Free-for-all's winner on time is whoever is ahead on their
        // own score.
        matchStatus_.winner = SvTeam::None;
        if (const auto best = clients_.bestClientKills())
            matchStatus_.winnerClientNum = best->first;
    }
    ...
}
```

**⇒ 七层**：
```text
1. **`dm` 是【无队伍模式**】 ⇒ **两队比分都是 `0`**
2. ⇒ **所以 `SV_UpdateMatchTimeLimit` 【会判成平局**】**
3. ⇒ **⇒ 所以【覆盖它**】：`winner = None`（**平局在队伍域**）
4. ⇒ **而 `winnerClientNum = bestClientKills()->first`**（**个人域的赢家**）
5. ⇒ **⇒ 所以【同一个"平局"在两个域里有不同的答案**】
```

**✅ 与 §406 的"`teamMode = cha || sd`"**完全闭合 ✓

**⇒ 三层**：
```text
§406  **`1000 + 队伍序号`** 在一个 `uint32` 里编码两个域
§413  `winner = None` 但 `winnerClientNum = best->first` ⇒ **两个域并存**
⇒ **⇒ 同一设计的两处**
```

**✅ ⭐ **一个"两个域并存而不是覆盖"的设计**。

**⚠ 而"THE SCORE-LIMIT PATH LOGS AND THIS ONE DID NOT"⇒ **两个路径的日志不对称**。**

**✅ 与 §408 的"判定全对而只缺一个屏幕"**同族（**第三次"两个路径不同"）。

**⇒ 三层**：
```text
`scoreLimit` 路径 ⇒ **记日志**
`timeLimit` 路径 ⇒ **不记** ⇒ **⇒ 一场打完时钟的比赛在日志里与"被判定"的不可区分**
```

**✅ 而"那正是让『十二杀而没有比赛结束』读成一个计分 bug 的那个缺口，而实际的限制是 30 而结束它的是时钟"`** —— 一个**极具体的误判**。

**⇒ 五层**：
```text
玩家看到：**12 杀而比赛结束了**
推断：**计分 bug**（因为限制应该是 30）
真因：**时钟到了**
⇒ **⇒ 而日志【不能区分**】
```

**✅ ⭐⭐ **"一次缺失的日志制造了一个不存在的 bug"** —— 第九次"沉默的诊断"。

### 9.1 而**刀AJ 的"只加字段不改下发"**

```php
// ★★ 28100 刀AJ（goal 第④步的**数据侧**验证）——
//   甲方要的结算四组里，「败北/获胜」与「比分」都依赖"服务端判断对哪队赢"。
//   这条日志原来**只打 best client、不打队伍 winner 和两边比分** ⇒
//   结算段一旦出问题，无法判断是"判断错"还是"显示没画"。
//   本刀只加字段，**不改任何下发**。
```

**⇒ 十层**：
```text
1. **结算四组里「败北/获胜」与「比分」都依赖【服务端判断对哪队赢**】**
2. ⇒ **这条日志原来【只打 `best client`**】**
3. ⇒ **【不打队伍 winner 和两边比分**】**
4. ⇒ **⇒ 所以结算段出问题，**无法判断是"判断错"还是"显示没画"**】**
5. ⇒ **本刀【只加字段，不改任何下发**】**
6. ⇒ **⇒ 一个"零风险"的取证**
```

**✅ 与 §402 的"`PMFLAGS|` 纯只读观测，不改任何状态"**完全同族（**第三次"取证必须只读"）。**

**⇒ 三层**：
```text
§402  `PMFLAGS|`：**不改任何状态**
§410  `olmod-kill-feed`：**默认关**
§413  `match complete ...`：**只加字段**
⇒ **⇒ 三条零风险取证**
```

**✅ ⭐ **一个"取证的零风险"三例表**。

**⚠ 而"判断错 vs 显示没画"⇒ **一个必须能区分的二选一**。**

**✅ 与 §413 八 的"症状在下游而根因在上游"**同族（**第四次"定位层的区分"）。**

**⇒ 三层**：
```text
层 1：**判断**（`winner`/`tf`/`sc`）
层 2：**显示**（屏幕四组）
⇒ **⇒ 所以日志必须同时打出【层 1**】
```

**✅ ⭐ **一个"分层日志"的设计**。

## 十、**`tag_weapon_right` 的 12248 带**

```cpp
if (!livingWeaponRightTagInitialized_)
{
    constexpr std::uint16_t linkTagBase = 12248;
    ...
    for (std::uint16_t tag = 1; tag < 256; ++tag)
    {
        const auto name = clients_.configString(linkTagBase + tag);
        if (name && *name == "tag_weapon_right") { livingWeaponRightTag = tag; break; }
        if ((!name || name->empty()) && !emptyTag) emptyTag = tag;
    }
    ...
    if (!stored || *stored != "tag_weapon_right")
    {
        // The configstring owner refused the insertion. Keep the
        // world tag at zero and retry on a later frame; no child is
        // publishable without a real map-band name.
        world_.setLivingWeaponRightTag(0);
        livingWeaponRightTagInitialized_ = false;
        livingWeaponRightTag = 0;
    }
}
```

**⇒ 十二层**：
```text
1. **`linkTagBase = 12248`**（**与 §407 的 `podium 的 linkTagBase = 12248`** 同值）
2. ⇒ **扫 `tag = 1..255`**
3. ⇒ **若名字是 `tag_weapon_right` ⇒ 用它**
4. ⇒ **否则记第一个空槽**
5. ⇒ **没有现成的 ⇒ 写进空槽**
6. ⇒ **而【写完后【读回来核对**】**
7. ⇒ **不匹配 ⇒ 【`setLivingWeaponRightTag(0)` + 重置初始化标志 + 下帧重试**】**
8. ⇒ **⇒ 所以【没有真实的地图带名字 ⇒【没有子实体可发布**】】**
9. ⇒ **（`fail-safe`：宁可不画武器，也不挂到任意骨上）**
```

### 10.1 ⭐⭐⭐ **"读回来核对"**

**✅ 这是本报告里**最重要的一个写后验证**。**

**⇒ 三层**：
```text
写：`SV_SetConfigString(12248+tag, "tag_weapon_right")`
读回：`configString(12248+tag)`
比对：**必须相等**
不相等 ⇒ **回滚 + 下帧重试**
⇒ **⇒ 所以【写入成功不等于写入生效**】
```

**✅ 与 §408 的"`_tp` 只在 `DB_FindXAssetHeader` 成功时写"**同族（**第三次"验证写入"）。

**⇒ 三层**：
```text
§408  **资产不存在 ⇒ 不写**（在写之前验证）
§413  **写完读回核对**（在写之后验证）
⇒ **⇒ 两个方向的防御**
```

**✅ ⭐ **一个"写前 vs 写后"的双防御**。

**⚠ 而"`livingWeaponRightTagInitialized_ = livingWeaponRightTag != 0 || !emptyTag;`"⇒ **三态逻辑**。**

**⇒ 五层**：
```text
`tag != 0`      ⇒ **成功** ⇒ `initialized = true`
`tag == 0` 但 `!emptyTag` ⇒ **没有空槽** ⇒ `initialized = true`（**不再重试**，因为不可能成功）
`tag == 0` 且 `emptyTag` ⇒ **写失败** ⇒ `initialized = false`（**下帧重试**）
⇒ **⇒ 所以【"没地方写"与"写失败"被区分**】
```

**✅ ⭐⭐ **"一个不可恢复的失败被标记为『已初始化』以免无限重试"** —— 一个**精确的重试判据**。

**✅ 与 §411 的"队满 ⇒ 丢弃并记一行"**同族（**第四次"有界重试"）。

### 10.2 而**"从不把零售的数字带进另一张地图"**

```php
// Entity links use the map-owned 12248 tag band.  Never carry a retail
// numeric tag into another map; withholding the child until this name is
// present is safer than attaching it to an arbitrary bone.
```

**⇒ 六层**：
```text
1. **实体链接用【地图拥有的 `12248` 标签带**】**
2. ⇒ **【从不】把零售的数字带进另一张地图**
3. ⇒ **【扣住子实体】直到这个名字出现**
4. ⇒ **⇒ 比【把它挂到任意一根骨上】更安全**
5. ⇒ **⇒ 一个"省略优于错误"的实例**
```

**✅ 与 §407 的"不猜数"**同族（**第二十六次"不要发明"）。**

**⇒ 三层**：
```text
§407  实体号拿不到 ⇒ **跳过**
§411  按钮位未取证 ⇒ **不清**
§413  标签名不可得 ⇒ **扣住子实体**
⇒ **⇒ 三条都是"未知 ⇒ 不做"**
```

**✅ ⭐ **一个"未知 ⇒ 不做"的三例表**。

## 十一、**六段计时**

```cpp
framePrepareTiming_.record(...);         // 步骤 3 之前
frameBeginWorldTiming_.record(...);      // beginFrame
frameClientThinkTiming_.record(...);     // client-think 循环
frameModeTiming_.record(...);            // 中间的模式/HUD/announce 段
frameEndAndPublishTiming_.record(...);   // endFrame + setWorldFrame
frameTotalTiming_.record(...);           // 全程
```

**⇒ 六段。**

**✅ 与 §404 的"`0.35–0.87 s` 的入场分段计时"**同族（**第二次"分段计时"）。

**⇒ 三层**：
```text
`BOTTRACE|create-stages`：`slotUs`/`activateUs`/`otherUs`/`totalUs` ⇒ **4 段**
`runFrame`：`prepare`/`beginWorld`/`clientThink`/`mode`/`endPublish`/`total` ⇒ **6 段**
⇒ **⇒ 同一个手法在一个函数与一个 BOT 上讲**
```

**✅ ⭐ **一个"分段计时"的两例**。

**⚠ 而"`frameClientThinkTiming_` 把 Lua 回调也算进去"⇒ **§413 二 的"`SCRIPTSLOW`"是为它准备的**。**

```cpp
// TIMED, BECAUSE THIS IS COUNTED AS `thinkUs` AND IS NOT THINK.
// ...
// 12.163 chased a 1.6 s "client think" spike through collision linking
// and actor counts on that reading before noticing the script was inside it.
```

**⇒ 九层**：
```text
1. **计时因为【它被算作 `thinkUs` 而【它不是 think**】】**
2. ⇒ **`dispatchPendingWorldEvents` 跑在【每命令循环内部**】**
3. ⇒ **而 `frameClientThinkTiming_` 包住那个循环**
4. ⇒ **⇒ 所以每一个 Lua 回调花的微秒【落进 client-think 窗口**】**
5. ⇒ **`12.163` 追了一个 `1.6 s` 的"client think"尖峰**
6. ⇒ **穿过【碰撞链接与演员计数**】**
7. ⇒ **在那个读数上**
8. ⇒ **而【在注意到脚本就在里面之前**】**
9. ⇒ **⇒ 所以加了 `SCRIPTSLOW us=… events=… types:…`**
```

### 11.1 ⭐⭐ **"那不是 think"**

**✅ 与 §405 的"`sendRawCommand` 的首字节通道"**同族（**第二次"一个没有区分力的仪器"）。**

**⇒ 三层**：
```text
现象：`thinkUs` 有 1.6s 尖峰
归因：**碰撞链接 / 演员计数**
真因：**Lua 回调**（因为它在同一个计时窗口里）
⇒ **⇒ 所以【一个合并的计时窗口制造了一个错误的嫌疑**】
```

**✅ ⭐⭐ **"一个合并的度量把两件事混成一件"** —— 与 §413 八 的"症状在两层的下游"**同族（**第五次"定位错误"）。

**⇒ 三层**：
```text
§413 八  `missing_playerstate` ⇒ **命名了错误的嫌疑**
§413 十一  `thinkUs` 尖峰 ⇒ ** chased 错了两个子系统**
⇒ **⇒ 两条都是【一个观测的名字是错的**】
```

**✅ 而 `SCRIPTSLOW` 的门是 `20000us`（`20ms`）。**

**✅ 一个**具体阈值**。

## 十二、关键结论

1. **⭐⭐⭐ `thinkBudget` 的基准必须随它前进**：**"同一段毫秒被反复扣" ⇒ 相隔 `8ms` 的命令被扣成 `8`/`16`/`24`/`32` ⇒ `100ms` 预算在第五条而不是第十二条用完**。
2. **⭐⭐⭐ "而它会复合：落后越远，第一个 delta 越大 ⇒ 一个命令花光预算 ⇒ 每帧只跑一个命令 ⇒ 更落后"** —— 一个完整描述的正反馈回路。
3. **⚠ "`cmdAge` 为负是要记住的症状：客户端最新的命令比服务器已执行的超前半秒"** —— 实测 **`~17/s executed` 对 `~140/s arriving`**。
4. **⭐ `thinkBudget == 0` ⇒ 无上限 ⇒ 排空有界队列（`32`）** ⇒ **把时间上界换成数量上界**（更稳健，不受累积误差影响）。
5. **⭐⭐⭐ `clientInfo+0x090` 实读是 `clientNum - 1`（序列 `[?,0,1,2,…,10]`）而不是 faction** —— **"序列的形状否证了它的语义"**：faction 只能是 `0/1`，而 `0..10` 不可能。
6. **⭐⭐⭐ "服务端写线是对的（`ClientInfoFactionField` ← `customization.faction`，1 bit），缺口在 provider：bot 的 customization 是复制真人成员的资产，副本里的 faction 是 `Tf(0)`，传入的 `Sc(1)` 被忽略"** ⇒ **名字色/小地图/UAV 不区分敌我** ⇒ 甲方「我队友不像我队友」。
7. **⭐ "一个正确的纪律在它的边界外产生了错误"**：`Appmain.cpp` 的 "NOTHING IS INVENTED … a COPY of that member's assets" **产生了这个 bug**。
8. **⭐ 修法是"只覆盖 `faction` 一个字节"（`characterItemId`/`modelIndex` 不动）⇒ 单变量**。
9. **⭐⭐⭐ "一帧答不出 ⇒ 从每一个观察者那里消失"**（`clientInfo` provider 每帧回答而没人保留）—— 与 §410/§411 构成**"存在但不可见"的三例**。
10. **⭐ `weaponSelectSequences_` 的 `a <weapon>` 去重**：**零售 cha 全片仅 `18` 条 `a`，而我方只要 `loadoutSequence` 变就补发 ⇒ 玩家按 `3` 切 alt 模式时服务端把客户端拽回主武器 ⇒ "卡一下/闪回/丢镜"**。而 **`A_RESEND|` 日志是判据**。
11. **⭐⭐ "一个命令的语义正确而它在某个语境下有害"**（`a <n>` 的语义是"画一把已拥有的武器"，副作用是"把显示拽到 n"）。
12. **⭐⭐⭐ "零 viewmodel ⇒ 客户端 `sub_53F5F0` 返回 null，`sub_59CC70` 不检查地写入 ⇒ 一个访问违例，【不是一个空库存】"** —— 第二次"零不是一个中性值"。
13. **Battle Royale 的三次尝试**：`secondary` 拷到 `primary` ⇒ **`weap=1148`（loot 带）+ 无武器名 + `0` 弹药** ⇒ 把能用的 CheyTac 换成不能用的武器；**空手出生 ⇒ AV**；**结论：真正的 BR 出生需要 loot 系统先能交还武器**。
14. **`runFrame` 的二十五个阶段**，而 **`dispatchPendingWorldEvents` 出现四次**（`beginFrame` 后、每条命令后、`endFrame` 前、`endFrame` 后）。
15. **⭐⭐ "`logPlayerPresentation` 必须在 `endFrame` 之后：`world_.snapshot()` 只有 `endFrame` 发布它之后才是客户端会收到的帧，而更早读它找到完全没有 `ET_PLAYER` 实体"`** —— **顺序不是风格问题而是正确性问题**。
16. **⭐⭐⭐ "一个 obituary 被创建与一个 obituary 被发出是两个不同的声明，而 `spawnObituaryEvent` 只证明第一个；`shouldArchiveWorldEntity` 是 fail-closed 白名单，那里缺一个 eType 静默丢掉那个实体（没有日志在任何地方）"`** ⇒ **端到端核对读已发布的快照** —— 第三次"用发布后的状态验证"。
17. **⭐⭐⭐ "一个往下两层的症状命名了错误的嫌疑"**：`missing_playerstate`（快照写者）而真因是 `BG_UpdatePlayerDObj` 的 AV（世界层），**那花了一整个会话**。
18. **⭐ `dm` 的时限判定**：`SV_UpdateMatchTimeLimit` 在两队都是 `0` 时会判成平局 ⇒ **覆盖为 `winner = None` 但 `winnerClientNum = bestClientKills()->first`** ⇒ **"平局"在两个域里有不同答案**。
19. **⭐⭐ "score-limit 路径记日志而 time-limit 路径不记 ⇒ 一场打完时钟的比赛与一场被判定不可区分"** ⇒ **那正是让"十二杀而没有比赛结束"读成一个计分 bug 的缺口**（实际限制是 `30` 而结束它的是时钟）。
20. **⭐ 刀AJ"只加字段不改任何下发"** ⇒ 一个**零风险的取证**，而**判据是"判断错 vs 显示没画"必须能区分**。
21. **⭐⭐ `tag_weapon_right` 的 12248 带**：**扫 `1..255` 找现成的，找到第一个空槽写下，而【写完后读回来核对】；不匹配 ⇒ `setLivingWeaponRightTag(0)` + 重置 + 下帧重试**。
22. **⭐⭐⭐ "`initialized = (tag != 0) || !emptyTag`" 的三态**：**"没地方写"（不可恢复）被标记为已初始化以免无限重试，而"写失败"（可恢复）保留下帧重试** —— 一个精确的重试判据。
23. **⭐ "从不把零售的数字带进另一张地图；扣住子实体直到这个名字出现，比把它挂到任意一根骨上更安全"`** —— 第二十六次"不要发明"。
24. **六段计时**（`prepare`/`beginWorld`/`clientThink`/`mode`/`endPublish`/`total`），而 **`frameClientThinkTiming_` 把 Lua 回调也算进去** ⇒ **`12.163` 追了一个 `1.6 s` 的"client think"尖峰穿过碰撞链接与演员计数，在注意到脚本就在里面之前** ⇒ 加 `SCRIPTSLOW us=… events=… types:…`（门 `20000us`）。

## 十三、`sv_main_mp.cpp` 全文件总览

**行数：`11,940`**（此前记录的 `9,393` 是错的）。

**二十六个 `ServerCore` 方法大类**：

| 类别 | 方法 |
|---|---|
| 帧驱动 | `runFrame` |
| 世界阶段 | `holdMatchCompletionState`、`driveMatchEndSequence`、`announceMatchCompletion` |
| HUD | `projectClientHudElems`、`logPlayerPresentation`、`checkDeathAnimationRisk` |
| SD | `completeSdRound`、`advanceSdRound`、`evaluateSdRound`、`announceSdRoundStart`、`announceSdLastAlive`、`pumpSdSoundQueues`、`queueSdSoundForClient/Team`、`sendSdSoundToTeam`、`processSdCommittedCommand`、`projectSdObjectives`、`setSdBombVisual` |
| 通报 | `announceMatchRules`、`announceVisionSet`、`projectDeathVision`、`announceLoadoutDvars`、`announceSoundAliases`、`announceFactorySoundAliases` |
| 播报 | `driveMatchAnnouncer`、`driveBattleChatter`、`queueAnnouncerLine`、`queueLocalSound`、`playAnnouncerLine`、`sendRawCommand` |
| 击杀/反馈 | `creditAssists`、`trackMatchParticipation`、`matchParticipationMilliseconds` |
| Bot | `nonBotTeamCounts`、`createBotClient`、`driveBotClients` |
| 资产 | `precacheCharacterModels`、`registerOutfitModelConfigString`、`publishActorModelConfigString`、`setOutfitModelSlots`、`setPodiumFallbackModel`、`setTopPlayersCamera/Places`、`spawnPodiumFigures` |
| 命令 | `processLootCommittedCommand`、`processZmUseCommittedCommand` |
| 杂 | `reportWorldFrameRejection`、`observeUavWeaponChanges`、`driveClientUav`、`driveClientPerks`、`driveClientEquipment`、`driveFactoryBox`、`driveFactoryTeleporters`、`driveCursorHints`、`driveClientUiScreens` |

**十二个关键常量域**：
```text
帧率        SvFrameMilliseconds / OLmodSvFrameMs
think       SV_ClientThinkBudgetMilliseconds / PendingUserCmdCapacity
匹配末      OutroScreen 11100 / OutroSlowMotion 14000,15500 / OutroKillCamEnd 16900
            OutroVision 17000 / PodiumScreen 17400 / OutroFinalScores 31500
            MatchEnded 32700 / PodiumFigures 16600 / PodiumIntermission 17000
            PodiumView 17400 / MatchEndFreeze 1000
击杀回放    SvKillCamPreKillMilliseconds / SvDeathViewMilliseconds
            SvKillcamReplayLengthMs 2500 / SvKillcamPostDelayMs 2000
            SvKillcamArchiveClients 24 / SvKillcamArchiveFrames 160
            SvKillcamArchiveWindowMs
播报        SvAnnouncerLeadChangeCooldownMs / SvAnnouncerDialogSpacingMs 3000
            SvLeadBlowoutMargin 20 / SvAnnouncerSpawnMusic 2130
            SvAnnouncerVictoryMusic 2131 / SvAnnouncerDefeatMusic 2128
            SvAnnouncerWinningMusic / SvAnnouncerLosingMusic
奖章        SvSplashReleaseIntervalMilliseconds / SvSplashQueueLimit
            SvSplashFirstBlood / Headshot / Revenge / FirstPlaceKill（+Points）
反馈        SvDamageFeedbackDurationMilliseconds / SvScoreFeedbackDurationMilliseconds
            SvDmScoreFeedbackKillPoints / SvScoreFeedbackKillPoints
BOT         BotWalkDestinationHoldMs 8000 / BotWalkEnemyDestinationHoldMs 2000
            BotWalkReplanIntervalMs 250 / BotWalkProbeIntervalMs 1000
            BotWalkYawStepDegrees 4.0
            BotStuckCheckMilliseconds 300 / BotStuckDistanceUnits 12
            BotStuckNudgeMilliseconds 700 / BotBlockedEdgeCapacity 16
            BotSprintMinDistanceUnits 512 / BotUserCmdButtonSprint 0x2
            BotCombatMaxRangeUnits 1500 / BotChaseMaxRangeUnits 4000
            BotEngageMinDistUnits 256 / BotEngageMaxDistUnits 768
            BotAimDamping 0.9 / BotAimBandwidth 18 / BotAimBandwidthSquared 324
            BotFireMissConeDegrees 6 / BotAimReactionMilliseconds 180
            BotCombatBurstFrames 8 / BotCombatReleaseFrames 4
            BotMeleeRangeUnits 64 / BotMeleeMaxErrorDegrees 30
            BotMeleeCooldownMilliseconds 1500 / BotUserCmdButtonMelee 0x4
            BotCombatUserCmdButtonFire 0x1 / BotServerFrameSeconds 0.05
            BotAimSubSteps 4
工厂        FactoryEntry FX 100/100/600 / carriers 3600/6100
            4100 zm_begin 100 / +400 zm_factory_sh 2000
            SvZombieResultsMilliseconds / SvZombieMatchEndedMilliseconds
            BatteryMultiplier 6/5
配置串      15 HUD 时钟 / 464 ui_timelimit / 510 cha prematch / 13 fog
            479 ui_eog_show / 23 winner / 3 sd round / 475 / 460
            2557 vision naked / 11861 timescale / 792 objective marker
            12248 tag band / 12249/12250 / 2060 mpIntro / 2972
            4355 HUD icon / 4872 materials / 5896 tags / 5960 weapons / 2568 models
```

## 十四、未闭合点

- `SV_ClientThinkBudgetMilliseconds()` 的当前值（是否为 `0`）。
- `1147`（`firstDynamicWeapon`）vs `1148`（注释说的 "FIRST LOOT-BAND INDEX"）的差。
- `SvKillcamArchiveWindowMs` 的窗口。
- `bestClientKills()` 在 `dm` 时限判定里未加 `<= 0` 守卫（与 §406 的 announcer 不同）。
- `SvSnapshotFrameValidationFailure` 的全部枚举。
- **下一步**：`sv_const_baselines_mp.cpp`（`902,974` 字节）。
