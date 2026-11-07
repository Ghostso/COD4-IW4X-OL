# 437 · **`sv_client_mp.cpp` 全文件收尾** —— "五个静默的拒绝"的姓名化、`0x1000` 保护的姿态重建、以及"新命令优先但保住那个在飞的前端"

## 一、范围

本报告学习 `sv_client_mp.cpp` 4160–4500 行（`activateBotSlot` 的两个不变式与"会话采纳"、`SV_QueuePendingUserCmd` 的溢出策略、`commitExecutedUserCmd` 的**七个具名拒绝**、`SV_DefaultUserCmdFromPlayerState` 的姿态重建），并收尾整个文件（**共 `4,500` 行**）。

## 二、**"五个静默的拒绝" → 七个具名的拒绝**（本组最重要的一段）

### 2.1 那段

```php
// FIVE SILENT REFUSALS, AND THE PENDING QUEUE JUST GROWS. `cmdAge=-1` in the
// runtime line means lastExecutedUserCmd was never set at all, while thinkCommands
// counts a hundred a second and pending sits at 8 -- so commands arrive, are
// dispatched, and then nothing here commits them. Which of these five stopped it is
// not recoverable from the outside: every one of them returns the same false.
static std::string LastCommitRefusal;
const auto refuse = [clientNum, commandTime](const char *const why) { ... };
if (clientNum >= clients_.size())        return refuse("clientNum_out_of_range");
if (!gameplayAuthorityReady_)            return refuse("gameplay_authority_not_ready");
if (client.gameplayState != Playing)     return refuse("not_playing");
if (!client.lastDispatchedUserCmd)       return refuse("nothing_dispatched");
if (lastDispatchedUserCmd->commandTime != commandTime) return refuse("dispatched_time_mismatch");
if (lastExecutedUserCmd && commandTime <= lastExecutedUserCmd->commandTime)
                                          return refuse("command_time_not_advancing");
if (commands.empty())                    return refuse("pending_queue_empty");
if (commands.front().commandTime != commandTime) return refuse("pending_front_mismatch");
```

### 2.2 二十四层

```text
1. **五个静默的拒绝，而【待处理队列只是【增长**】】**
2. ⇒ **运行时行里的 `cmdAge=-1` 意味着【`lastExecutedUserCmd` 【从未被设过**】】**
3. ⇒ **而 `thinkCommands` 【一秒数到一百**】**
4. ⇒ **而 `pending` 【停在 `8`**】】
5. ⇒ **⇒ 所以【命令到达、被出队、而然后【这里什么也没提交它们**】】**
6. ⇒ **⇒ 而【是这五个里的哪一个停下了它【从外面不可恢复**】】**
7. ⇒ **因为【每一个都返回同一个 `false`**】**
8. ⇒ **⇒ 修法是【每个分支一个【名字**】】**
9. ⇒ **而【七个**名字**：`
      · **`clientNum_out_of_range`**
      · **`gameplay_authority_not_ready`**
      · **`not_playing`**
      · **`nothing_dispatched`**
      · **`dispatched_time_mismatch`**
      · **`command_time_not_advancing`**
      · **`pending_queue_empty`**
      · **`pending_front_mismatch`**（**八个**）`
10. ⇒ **⇒ 而【`LastCommitRefusal` 【去重**】】**
11. ⇒ **⇒ 所以【同一个细节只打印一次**】
```

### 2.3 ⭐⭐⭐ **"是这五个里的哪一个停下了它，从外面不可恢复，因为每一个都返回同一个 `false`"**

**✅ 这是本报告里**最重要的一条"同一个返回值抹掉信息"**。**

**✅ 与 §428 的"四个项能把它关着，而日志一个都没命名"**完全同族（**第九次"多因歧义"）。

**⇒ 三次闭合**：
```text
§426  **两个非 (B) 分支都能楔死而两个都不说**
§428  **四个闸门一个都没命名**
§437  **五个（实为八）拒绝都返回同一个 `false`**
⇒ **⇒ 三次"同一个失败值**】
```

**✅ ⭐⭐⭐ **一个"同一个失败值"的三例表**。

**⚠ 而"`cmdAge=-1`"⇒ **§413 的同一个症状**。**

**⇒ 三层**：
```text
§413  **`cmdAge` 为负 = 客户端最新的命令比服务器已执行的超前半秒**
§437  **`cmdAge=-1` 而 `lastExecutedUserCmd` 从未被设**
⇒ **⇒ 同一个读数，两个解读**
```

**⚠ 一处**需要区分的解读**（`cmdAge=-1` 可能是"差一毫秒"或"从未执行"）。

**⇒ 三层**：
```text
若 `lastExecutedUserCmd` 存在 ⇒ `cmdAge = ps.commandTime - cmd.commandTime` ⇒ **`-1` 是【一毫秒超前**】
若不存在 ⇒ **`cmdAge = -1` 是【一个"从未"的哨兵**】
⇒ **⇒ 所以【`-1` 有两种含义**】
```

**✅ ⭐⭐⭐ **一个"-1 的两种含义"** —— 与 §435 的"`None` 两种含义"**同族（**第四次"一值多义"）。

**⇒ 三层**：
```text
§406  `None` ⇒ "平局"
§416  `None` ⇒ 空指针
§435  `None` ⇒ 两种含义
§437  `-1` ⇒ 两种含义
⇒ **⇒ 四次"一值多义**】
```

**✅ ⭐⭐ **一个"一值多义"的四例表**。

### 2.4 而**`refuse` 的去重**

```php
static std::string LastCommitRefusal;
const auto refuse = [clientNum, commandTime](const char *const why) {
    auto details = "client=" + ... + " commandTime=" + ... + " " + why;
    if (details != LastCommitRefusal) { log; LastCommitRefusal = details; }
    return false;
};
```

**⇒ 八层**：
```text
1. **`details` 包含 `client`、`commandTime` 与 `why`**
2. ⇒ **⇒ 所以【任何一项变化 ⇒ 打印**】**
3. ⇒ **而【`static` 一个全局**】 ⇒ **所以【跨客户端共享**】**
4. ⇒ **⇒ 所以【两个客户端交替 ⇒ 每帧都不同 ⇒ 每帧都打印**】
```

### 2.5 ⚠⚠ **一个真实的诊断缺陷**

**✅ 这是本报告里**最重要的一个发现**。**

**⇒ 三层**：
```text
`LastCommitRefusal` 是 **`static`（全局一个）**
而 `details` **包含 `client=` 与 `commandTime=`**
⇒ **⇒ 所以【两个客户端交替 ⇒ 字符串每帧都不同 ⇒ 去重【完全失效**】】
```

**⚠ 而 §417 的 `spawnRefusalReasons_` 的注释【恰恰警告过这个**】**：

```php
// PER CLIENT, NOT ONE FOR ALL OF THEM. A single string means two
// clients alternate `client=0` and `client=1` through it, the
// comparison never matches, and a diagnostic meant to fire on a
// CHANGE fires on every frame instead. It is the same shape as the
// shared edge-trigger that blinded three states in section 118.
std::unordered_map<std::uint32_t, std::string> spawnRefusalReasons_;
```

**✅ ⭐⭐⭐ **"同一条经验在本文件的两处：一处学会了（`spawnRefusalReasons_` 按客户端），一处没有（`LastCommitRefusal` 是全局 `static`）"**。**

**⇒ 三层**：
```text
`spawnRefusalReasons_` ⇒ **按客户端**（**正确**）
`LastCommitRefusal`    ⇒ **全局一个**（**缺陷**）
⇒ **⇒ 所以【同一条经验【一处学会一处没有**】】
```

**✅ 这是本报告里最重要的一条跨段落对比**。

**⚠ 而 `spawnRefusalReasons_` 在 `sv_snapshot_mp.hpp`（§424 附近），而 `LastCommitRefusal` 在 `sv_client_mp.cpp`** ⇒ **两个不同的文件**。

**⇒ 三层**：
```text
`sv_snapshot_mp.hpp` ⇒ **学会了（按客户端）**
`sv_client_mp.cpp`   ⇒ **没有（全局 static）**
⇒ **⇒ 所以【一条经验【需要跨文件传播**】】
```

**✅ ⭐⭐⭐ **一个"经验需要跨文件传播"的实例**。

## 三、**`SV_QueuePendingUserCmd` 的"保住那个在飞的前端"**（本组第二重要）

### 3.1 那段

```php
client.pendingUserCmds.push_back(command);
while (client.pendingUserCmds.size() > PendingUserCmdCapacity)
{
    // OLMOD(pending-usercmd-queue): unlike Ghosts, game-side execution
    // can fail transactionally after dispatch. Never let later packet
    // ingress evict that exact queue front before commit or an explicit
    // recovery discard resolves its ownership.
    const auto dispatchedFrontPending =
        client.lastDispatchedUserCmd &&
        client.pendingUserCmds.front().commandTime == client.lastDispatchedUserCmd->commandTime &&
        (!client.lastExecutedUserCmd ||
            client.lastDispatchedUserCmd->commandTime > client.lastExecutedUserCmd->commandTime);
    if (dispatchedFrontPending)
    {
        // OLMOD(pending-usercmd-latest-tail): preserve the exact
        // in-flight front, but keep Ghosts' low-latency newest-command
        // policy for every uncommitted slot behind it.
        const auto oldestUndispatched = std::next(client.pendingUserCmds.begin());
        client.lastDroppedOverflowUserCmd = *oldestUndispatched;
        ++client.droppedOverflowUserCmds;
        client.pendingUserCmds.erase(oldestUndispatched);
        continue;
    }
    // CODREF(sv_process_client_thinks): without an in-flight project
    // transaction, retain the newest full-capacity deferred window.
    client.lastDroppedOverflowUserCmd = client.pendingUserCmds.front();
    ++client.droppedOverflowUserCmds;
    client.pendingUserCmds.pop_front();
}
```

### 3.2 二十四层

```text
1. **与 `Ghosts` 不同，游戏侧执行【可以在 dispatch 之后事务性地失败**】**
2. ⇒ **⇒ 所以【永不让后来的包入口【驱逐那个精确的队列前端**】】**
3. ⇒ **在【提交**或【一次显式的恢复性丢弃】解决它的所有权之前**
4. ⇒ **`dispatchedFrontPending` 的三个条件**：
      · **`lastDispatchedUserCmd` 存在**
      · **`front().commandTime == lastDispatchedUserCmd->commandTime`**
      · **且【`!lastExecutedUserCmd` 或 `lastDispatched->commandTime > lastExecuted->commandTime`**】
5. ⇒ **⇒ 第三个条件排除"已经执行过"** ⇒ **所以只对【真的在飞**】的那个**
6. ⇒ **⇒ 若在飞 ⇒ 【丢弃【第二个**】而不是前端**】
7. ⇒ **否则 ⇒ 丢前端**（**保留最新的 `capacity` 个**）
```

### 3.3 ⭐⭐⭐ **"保住那个精确的在飞前端，但对它之后的每一个未提交槽保持 Ghosts 的『最新命令』策略"**

**✅ 这是本报告里**最重要的一个双目标权衡**。**

**⇒ 三层**：
```text
目标 A：**不驱逐那个在飞的**（**否则它的所有权丢失 ⇒ 事务失败**）
目标 B：**保持最新**（**否则持续入口 ⇒ 数秒输入延迟**）
⇒ **⇒ 所以【丢【第二个**】同时满足两者**】
```

**✅ 与 §413 的"`thinkBudget` 会复合"**同族（**第四次"两个约束必须同时满足**）。

**⇒ 三层**：
```text
§413  **时间预算 + 数量上界**
§426  **六样状态一起清**
§437  **保住前端 + 保持最新**
⇒ **⇒ 三次"双约束**】
```

**✅ ⭐⭐ **一个"双约束"的三例表**。

**⚠ 而"`erase(std::next(begin()))`"⇒ **`deque` 的中间删除**。**

**⇒ 三层**：
```text
`std::deque` ⇒ **中间 `erase` 是 `O(n)`**
而 `n <= 32` ⇒ **可接受**
⇒ **⇒ 所以【一个小的 `deque` 是合适的**】
```

**✅ ⭐ **一个数据结构选择的理由**。

### 3.4 而**"`command.commandTime <= client.lastQueuedUserCmdTime ⇒ 拒绝"**

**⇒ 六层**：
```text
1. **一个【不前进**】的命令 ⇒ 直接拒绝**
2. ⇒ **⇒ 所以【队列里的 `commandTime` 单调递增**】**
3. ⇒ **⇒ 而那【正是 `commitExecutedUserCmd` 的 `command_time_not_advancing` 检查的前提**】
```

**✅ 与 §413 的"`NonIncreasingCommandTime` 是一个失败阶段"**配合。

**⇒ 三层**：
```text
入口：`commandTime <= lastQueued ⇒ 拒绝`
执行：`commandTime <= lastExecuted ⇒ 拒绝`
⇒ **⇒ 两个层次的同一检查**
```

**✅ ⭐⭐ **一个"同一检查两层"的实例**。

## 四、**`SV_DefaultUserCmdFromPlayerState` 的 `0x1000` 保护**（本组第三重要）

### 4.1 那段

```php
// CODREF(MSG_SetDefaultUserCmd): OLFinal out.exe 0x0066F170 builds
// the first usercmd delta baseline from the acknowledged playerstate.
// When protected playerstate flag 0x1000 is present it reconstructs
// the level-driven stance buttons from eFlags, plus ADS from the
// weapon-position fraction. Leaving these buttons zero made every
// packet boundary look like a stance release and caused the client to
// fight the authoritative view-height transition.
if (playerState.otherFlags & 0x1000u)
{
    if (playerState.eFlags & 0x8u)       result.buttons |= 0x100u;
    else if (playerState.eFlags & 0x4u)  result.buttons |= 0x200u;
    if (playerState.weaponPositionFraction != 0.0f) result.buttons |= 0x800u;
    result.conditionalElevenBits = 0x7FFu;
}
```

### 4.2 二十层

```text
1. **`OLFinal out.exe 0x0066F170` 从【被确认的 `playerState`** 构建第一个 usercmd delta 基准**】**
2. ⇒ **当【受保护的 `playerState` 旗标 `0x1000`**】存在时**
3. ⇒ **它【从 `eFlags` 重建【关卡驱动的姿态按钮**】】**
4. ⇒ **加【`ADS` 从武器位置分数**】**
5. ⇒ **⚠ 让这些按钮【保持零**】让【每一个包边界【看起来像一次姿态释放**】】**
6. ⇒ **⇒ 而让客户端【对抗权威的视高过渡**】**
7. ⇒ **`eFlags & 0x8` ⇒ `0x100`（**`PRONE`？**）**
8. ⇒ **`eFlags & 0x4` ⇒ `0x200`（**`CROUCH`？**）**
9. ⇒ **`weaponPositionFraction != 0` ⇒ `0x800`（**`ADS`？**）**
10. ⇒ **`conditionalElevenBits = 0x7FF`**（**`11` 位全一**）**
```

### 4.3 ⭐⭐⭐ **"让这些按钮保持零让每一个包边界看起来像一次姿态释放"**

**✅ 与 §428 的"那要紧的帧（没有姿态位的）不会被正在被测量的那个条件过滤掉"**不同（这是**一个基线问题**）。

**⇒ 三层**：
```text
机制：**usercmd 的 delta 基准**
若基准里姿态按钮是 `0` ⇒ **每一条后续命令都"释放"**
⇒ **⇒ 所以【客户端【看到一次持续的释放**】】
```

**✅ 与 §427 的"`OLMOD(section-86)` 的『改变不是非零』"**同族（**第五次"基线的正确性**）。

**⇒ 三层**：
```text
§415  **agent 的 `fields` 默认值 = 客户端的 base**
§427  **usercmd 的 `11` 位路径 vs `10` 位**
§437  **usercmd 基准里的姿态按钮**
⇒ **⇒ 三次"基准必须正确**】
```

**✅ ⭐⭐⭐ **一个"基准正确性"的三例表**。

**⚠ 而"`eFlags 0x8 → buttons 0x100`" 与 §428 的 `StanceButtons = 0x100 | 0x200`**完全吻合 ✓

**⇒ 三层**：
```text
§428  **`StanceButtons = 0x100 | 0x200`**（**`PRONE`/`CROUCH`**）
§437  **`eFlags 0x8 → 0x100`、`eFlags 0x4 → 0x200`**
⇒ **⇒ 两处同一个映射**
```

**✅ ⭐⭐ **一个"映射"的重复确认**。

**⚠ 而"`weaponPositionFraction != 0.0f ⇒ 0x800`"⇒ **`0x800` 是 `ADS`**。**

**✅ 与 §411 的"`ADS = 0x800`"**完全一致 ✓

**⇒ 三层**：
```text
§411  **`ADS = 0x800`**（**2697 的表**）
§437  **`weaponPositionFraction != 0 ⇒ 0x800`**
⇒ **⇒ 同一个位**
```

**✅ ⭐ **一个"按键位表"的确认**。

**⚠ 而"`conditionalElevenBits = 0x7FF`"⇒ **`11` 位全一**。**

**⇒ 三层**：
```text
`0x7FF` ⇒ **`11` 位全一** ⇒ **"全部设置**"
⇒ **⇒ 所以【这是一个"全部未知位设为 `1`**"的选择**】
```

**✅ 与 §427 的"`OLMOD(section-86)` 说 `11` 位 vs `10` 位"**配合。

**⇒ 三层**：
```text
§427  **`10` 位 vs `11` 位**
§437  **`conditionalElevenBits = 0x7FF`（`11` 位全一）**
⇒ **⇒ 所以【那个字段是 `11` 位**】**
```

**✅ ⭐⭐ **一个"位宽"的确认**。

## 五、**`activateBotSlot` 的两个不变式**（本组第四重要）

### 5.1 那段

```php
// loop rather than assumed:
//  * loadoutSequence must be non-zero AND selectedLoadout non-empty, or
//    the admission block at sv_main_mp.cpp:8422 never runs and
//    resolvedLoadout stays nullopt -- a zero viewmodel and a client
//    access violation (section 152y, sv_main_mp.cpp:8491-8495);
//  * the caller must have written resolvedLoadouts_[clientNum] with
//    THIS sequence BEFORE calling here, so that block's lookup at
//    :8445 hits and :8427 -- the loadoutProvider_ profile getter a bot
//    has no profile for -- is never reached, not even for one frame.
if (!loadoutSequence || selectedLoadout.empty() || xuid == 0)
    return false;
```

**⇒ 十六层**：
```text
1. **两个不变式**【从一个循环读出**】而不是【假设**】**
2. ⇒ **① `loadoutSequence` 必须【非零**】且 `selectedLoadout` 【非空**】**
3. ⇒ **⇒ 否则 `sv_main_mp.cpp:8422` 的准入块【永不运行**】**
4. ⇒ **⇒ 而 `resolvedLoadout` 【停在 `nullopt`**】**
5. ⇒ **⇒ ⇒ 【一个零 `viewmodel` 与一个客户端访问违例**】**
6. ⇒ **（第 `152y` 节，`sv_main_mp.cpp:8491-8495`）**
7. ⇒ **② 调用者必须【在调这里之前**】用【这个**序列写了 `resolvedLoadouts_[clientNum]`**
8. ⇒ **⇒ 所以那个块的查找在 `:8445` 【命中**】**
9. ⇒ **⇒ 而 `:8427` —— **`loadoutProvider_` 的 profile getter，而一个 bot 【没有 profile**】**
10. ⇒ **⇒ 【永不被到达**】** ⇒ **甚至【一帧都不**
11. ⇒ **⇒ 所以【两个不变式【防止一个 AV**】】**
```

### 5.2 ⭐⭐⭐ **"永不被到达，甚至一帧都不"**

**✅ 与 §435 的"这段宽限里的每一毫秒都是一个客户端可能死掉的帧"**同族（**第三次"一帧也是致命的"）。

**⇒ 三层**：
```text
§412  **贴脸 `dist ≈ 41` ⇒ `pitch ≈ 65°`**
§435  **每一毫秒都是一个可能死掉的帧**
§437  **甚至一帧都不**
⇒ **⇒ 三次"一帧的代价**】
```

**✅ ⭐⭐ **一个"一帧的代价"的三例表**。

**⚠ 而"`xuid == 0` ⇒ 拒绝"⇒ **一个显式的身份检查**。**

**✅ 与 §436 的"`duplicateIdentity`"**配合。

## 六、**`activateBotSlot` 的"会话采纳"与它的已知限制**

### 6.1 那段

```php
// OLMOD(bot-client-p7b session-adoption): MAKE THE BOT A SESSION MEMBER, not merely a
// server-made slot. Measured before this change, in a live room (2026-10-12 12:39):
// every bot slot read `session_generation=0 generation_active=0` while the one real
// player read `=1`, and commitSessionRoster logged `rosterMembers=[<real player only>]`.
// The adoption loop in commitSessionRoster (:3012-3028) runs at COMMIT time, and the
// commit happens BEFORE the bots exist (12:39:01 commit vs 12:39:06..12:39:42 creation),
// so a bot can only be admitted here.
//
// KNOWN LIMIT, not fixed here: a LATER commitSessionRoster for a NEW generation carries
// only the members that beginSessionRoster() was given, so these bot entries are wiped
// and the bot slots are released. One generation per match is the observed case; if a
// re-commit is ever seen, extend beginSessionRoster() to preserve bot members.
if (activeRoster_) {
    if (!sessionMemberForXuid(*activeRoster_, xuid))
        activeRoster_->members.push_back(SessionRosterMember{ .xuid = xuid, .username = client.name });
    client.sessionGeneration = activeRoster_->generation;
}
```

### 6.2 二十层

```text
1. **让 bot 成为一个【会话成员**】，而不只是一个服务器造的槽**
2. ⇒ **测量（`2026-10-12 12:39`）**：
      · **每一个 bot 槽读 `session_generation=0 generation_active=0`**
      · **而那一个真实玩家读 `=1`**
      · **而 `commitSessionRoster` 记录 `rosterMembers=[<只有那个真实玩家>]`**
3. ⇒ **`commitSessionRoster` 的采纳循环【在【提交**时间**】跑**
4. ⇒ **而【提交【发生在 bot 存在【之前**】】**
5. ⇒ **（`12:39:01` 提交 vs `12:39:06..12:39:42` 创建）**
6. ⇒ **⇒ 所以【一个 bot 【只能在这里**】被准入**
7. ⇒ **⇒ 而 `clientGenerationIsActive()` 然后【对这个槽报告 `true`**】**
8. ⇒ **因为【它比较 `ClientSlot::sessionGeneration` 与【那个活跃代次**】】**
9. ⇒ **⇒ （`ClientSlot` 也是【客户端槽遥测**所打印的东西**）**
10. ⇒ **⚠ 已知限制，不在这里修**：
      · **一个【更晚**的 `commitSessionRoster` 为新代次**】**
      · **只携带【`beginSessionRoster()` 被给的那些成员**】**
      · **⇒ 所以【这些 bot 条目【被抹掉**而 bot 槽被释放**】**
11. ⇒ **（每场一个代次是【被观察到的情况**】）**
12. ⇒ **⇒ 若【重提交**】被看到，扩展 `beginSessionRoster()` 以保留 bot 成员**
```

### 6.3 ⭐⭐⭐ **"KNOWN LIMIT，不在这里修"**

**✅ 与 §435 的"这缩短窗口，它不关闭它"**同族（**第三次"明确标注的限制**）。

**⇒ 三层**：
```text
§404  **"窄回退不是诊断"**
§435  **"缩短窗口不关闭"**
§437  **"KNOWN LIMIT，不在这里修"**
⇒ **⇒ 三次"已知限制的声明**】
```

**✅ ⭐⭐⭐ **一个"已知限制"的三例表**。

**⚠ 而"如果重提交被看到，扩展 `beginSessionRoster()`"⇒ **一个可执行的前进路径**。**

**✅ 与 §415 的"如果僵尸仍然保持一个姿势而别名在线上，那个 resolve 因另一个原因失败"**同族（**第三次"可证伪条件"）。

## 七、**两个 `discard*` 的六个状态闭合**

```text
commitExecutedUserCmd        ⇒ 成功 ⇒ lastExecutedUserCmd
discardUnsupportedUserCmd    ⇒ lastDiscardedUnsupportedUserCmd + 计数
discardRejectedUserCmd       ⇒ lastDiscardedRejectedUserCmd   + 计数
SV_QueuePendingUserCmd       ⇒ 溢出 ⇒ lastDroppedOverflowUserCmd + 计数
SV_PacketEvent（入口）       ⇒ lastReceivedUserCmd
dispatchNextPendingUserCmd   ⇒ lastDispatchedUserCmd
```

**⇒ 六个状态，与 §436 的 `ClientIngressStatus` 的六项完全闭合** ✓

**✅ 而 `discard*` 的三段共享同一个前提**：

```cpp
if (clientNum >= clients_.size()) return false;
if (!gameplayAuthorityReady_ || client.gameplayState != Playing ||
    !client.lastDispatchedUserCmd ||
    client.lastDispatchedUserCmd->commandTime != commandTime) return false;
if (commands.empty() || commands.front().commandTime != commandTime) return false;
```

**⇒ 五层**：
```text
1. **三段（`commit` / `discardUnsupported` / `discardRejected`）共享同一套前提**
2. ⇒ **⇒ 所以【只有那个【真的在飞**】的命令能被三者之一处理**】
3. ⇒ **⇒ 而【`commit` 独有【两条**检查**（`not_playing` 与 `command_time_not_advancing`）**】
4. ⇒ **⇒ 因为【它要【推进**，而两个 discard 只是【排空**】】
```

**✅ ⭐⭐ **"commit 要推进而 discard 只是排空"** —— 一个**精确的职责区分**。

## 八、关键结论

1. **⭐⭐⭐ `commitExecutedUserCmd` 的"五个静默的拒绝"→ 实为八个具名的拒绝**：`clientNum_out_of_range` / `gameplay_authority_not_ready` / `not_playing` / `nothing_dispatched` / `dispatched_time_mismatch` / `command_time_not_advancing` / `pending_queue_empty` / `pending_front_mismatch` —— **第九次"多因歧义"**（与 §426、§428 同族）。
2. **⭐⭐ "`cmdAge=-1` 而 `lastExecutedUserCmd` 从未被设过，而 `thinkCommands` 一秒数到一百，而 `pending` 停在 `8` ⇒ 命令到达、被出队、而然后这里什么也没提交它们"`** —— 一个**精确的症状三元组**。
3. **⭐⭐⭐ "`-1` 的两种含义"**：**有 `lastExecutedUserCmd` 时 `-1` 是"一毫秒超前"，没有时是"从未"哨兵** —— 第四次"一值多义"（与 §406/§416/§435 同族）。
4. **⚠⚠ 一个真实的诊断缺陷**：**`LastCommitRefusal` 是【全局 `static`】而 `details` 含 `client=` 与 `commandTime=` ⇒ 两个客户端交替 ⇒ 字符串每帧都不同 ⇒ 去重【完全失效**】—— **而 §417 的 `spawnRefusalReasons_` 的注释恰恰警告过这个**（"一个共用的字符串意味着两个客户端交替，比较永不匹配，而一个本该在变化时触发的诊断会每帧触发"）⇒ **同一条经验，一处学会（`sv_snapshot_mp.hpp`），一处没有（`sv_client_mp.cpp`）**。
5. **⭐⭐⭐ `SV_QueuePendingUserCmd` 的双目标**：**与 Ghosts 不同，游戏侧执行可以在 dispatch 之后事务性地失败 ⇒ 永不让后来的包入口驱逐那个精确的队列前端；但保留那个前端而拖到秒级延迟也不行 ⇒ 所以丢【第二个】同时满足两者**（保住前端 + 保持最新）—— 第三次"双约束"。
6. **⭐ 三个条件确认"真的在飞"**（`lastDispatchedUserCmd` 存在 + `front().commandTime` 匹配 + **且未执行或已执行更早**）。
7. **⭐ `std::deque` 的中间 `erase` 是 `O(n)` 但 `n <= 32` ⇒ 可接受**。
8. **⭐⭐ "入口拒绝不前进的命令 ⇒ 队列里的 `commandTime` 单调递增 ⇒ 那正是 `commitExecutedUserCmd` 的 `command_time_not_advancing` 检查的前提"`** —— **同一检查在两层**。
9. **⭐⭐⭐ `SV_DefaultUserCmdFromPlayerState` 的 `0x1000` 保护**：**`OLFinal out.exe 0x0066F170` 从被确认的 `playerState` 构建第一个 usercmd delta 基准，当 `otherFlags & 0x1000` 时它从 `eFlags` 重建关卡驱动的姿态按钮 + 从武器位置分数重建 ADS；让这些按钮保持零让【每一个包边界看起来像一次姿态释放】并让客户端【对抗权威的视高过渡】`**。
10. **⭐⭐ 三个映射闭合**：**`eFlags 0x8 → buttons 0x100`**（`PRONE`，与 §428 的 `StanceButtons = 0x100|0x200` 吻合）、**`eFlags 0x4 → 0x200`**（`CROUCH`）、**`weaponPositionFraction != 0 → 0x800`**（`ADS`，与 §411 的 2697 表吻合）。
11. **⭐ `conditionalElevenBits = 0x7FF` = `11` 位全一** ⇒ 与 §427 的"`11` 位 vs `10` 位"闭合。
12. **⭐⭐⭐ `activateBotSlot` 的两个不变式**：① **`loadoutSequence` 非零且 `selectedLoadout` 非空，否则 `sv_main_mp.cpp:8422` 的准入块永不运行 ⇒ `resolvedLoadout` 停在 `nullopt` ⇒ 零 `viewmodel` ⇒ AV**；② **调用者必须在此前用【这个序列】写了 `resolvedLoadouts_[clientNum]`，所以 `:8445` 的查找命中而 `:8427`（`loadoutProvider_` 的 profile getter，**一个 bot 没有 profile**）【永不被到达，甚至一帧都不**】。
13. **⭐⭐ `activateBotSlot` 的"会话采纳"**：**bot 槽读 `session_generation=0`，而 `commitSessionRoster` 的采纳循环在**提交**时跑，而**提交发生在 bot 存在之前**（`12:39:01` vs `12:39:06..12:39:42`）⇒ **一个 bot 只能在这里被准入**。
14. **⭐⭐⭐ "KNOWN LIMIT，不在这里修：一个更晚的 `commitSessionRoster` 为新代次只携带 `beginSessionRoster()` 被给的那些成员 ⇒ 这些 bot 条目被抹掉而 bot 槽被释放；每场一个代次是观察到的情况，若重提交被看到，扩展 `beginSessionRoster()` 以保留 bot 成员"`** —— 第三次"已知限制的声明"（与 §404/§435 同族）。
15. **⭐ 六个命令生命周期状态**（`Received` / `Dispatched` / `Executed` / `DiscardedUnsupported` / `DiscardedRejected` / `DroppedOverflow`）**与 §436 的 `ClientIngressStatus` 六项完全闭合**；而 **`commit` 独有两条额外检查（`not_playing` 与 `command_time_not_advancing`）因为"它要推进而两个 discard 只是排空"`**。

## 九、`sv_client_mp.cpp` 全文件总览

**行数：`4,500`**。**`SvClientSystem` 约 `120` 个公开方法。**

**十四个功能域**：

| 域 | 内容 |
|---|---|
| **OOB 协议** | `getchallenge` / `connect` / `gamestateupdate` / `heartbeat` / `stats` |
| **握手** | `SV_GetChallenge`（31 位非零）/ `findChallenge`（IP/XUID/会话三元组）/ `SV_DirectConnect`（七道校验） |
| **会话名册** | `stageSessionRoster` / `commitSessionRoster`（ADOPT vs WIPE）/ `rollbackSessionRoster` / `sessionAllowsXuid` |
| **gamestate 闸门** | 四道（`PROFILE_STATS_INCOMPLETE` / `GENERATION_INACTIVE` / `GAMESTATE_NOT_CONFIGURED` / `NO_GAMESTATE_BUILDER`） |
| **快照基准** | `selectBaseline` / `newestFlaggedSnapshotMessage` / `baselineFrame` / 三重不变式 |
| **usercmd 队列** | 六状态 / `SV_QueuePendingUserCmd` 双目标 / `dispatchNextPendingUserCmd` |
| **计分** | 十个统一的四步累加器 / `bestClientKills` / `topClientsByKills` |
| **比分板** | `queueScoreboardResponse`（`K`...`K` `J`）/ 两个 FNV 指纹 |
| **连接公告** | `f`（`15 FE base64 FE ^7`）/ `e`（`FE base64 FE ^7 EXE_LEFTGAME`） |
| **ZM** | `publishZmRoundHud`（200 帧门 + 空队列门） |
| **菜单** | `SV_ParseMenuResponse` / `SV_DispatchMenuResponse` |
| **Loadout** | `commitPendingLoadout`（`None` 二义）/ `resolveAndCommitPendingLoadout` |
| **Bot** | `freeClientSlot`（槽 0 保留）/ `activateBotSlot`（两个不变式 + 会话采纳） |
| **诊断** | `clientIngressStatus`（~40 字段）/ `serverReliableCommandStatus` |

**十二个具名失败枚举**：
```text
SvSnapshotAssemblyFailure（6）
SvTeamPolicy
ClientState（Free/Connected/ClientLoading/Active）
ClientGameplayState（Inactive/WaitingForLoadout/Playing）
SvClientThinkFailureStage（37）
SvSnapshotFrameValidationFailure（20）
SvSnapshotWriteFailure（15）
SvServerWorld::FinishPlayerDamageResult（6）
WeaponAmmoMutationResult（5）
RespawnRequestResult（5）
TimeoutDrop::Cause
NetchanProcessKind（Accepted/Rejected/Duplicate/FragmentPending/FragmentAcknowledgement）
```

**十一个环境变量**：
```text
OLMOD_USERCMD_SAMPLE / OLMOD_SCOREBOARD_TRACE / OLMOD_LOG_CLIENT_COMMANDS
OLMOD_LOG_NAME_BYTES / OLMOD_AUTO_LOADOUT / OLMOD_AUTO_LOADOUT_GRACE_MS
OLMOD_CLIENT_TIMEOUT_MS / OLMOD_CONNECT_TIMEOUT_MS / OLMOD_VERBOSE_LOG
OLMOD_SNAPSHOT_ENTITY_BASELINES / OLMOD_SNAPSHOT_ENTRY_FLAG
```

## 十、未闭合点

- `PeerAddress::operator==` 是否含端口。
- `SvProfilePatchLoadOnly` / `SvProfilePatchLoadAndRebuild` 的字节值。
- `0x0066F170` 的完整 `MSG_SetDefaultUserCmd`。
- `otherFlags 0x1000` 的语义（"受保护的 playerstate 旗标"）。
- `LastCommitRefusal` 的全局 `static` 是否应改成按客户端。
- **下一步**：`sv_script_builtin_mp.cpp`（`199,423` 字节）。
