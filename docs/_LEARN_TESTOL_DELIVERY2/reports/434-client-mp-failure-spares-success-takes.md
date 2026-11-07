# 434 · **"失败饶过客户端；成功拿走它"** —— 三处清空客户端槽、`ADOPTING` vs `WIPING`、以及"成功那条路径在它下面把座位扔掉了"

## 一、范围

本报告学习 `sv_client_mp.cpp` 3150–3480 行（`commitSessionRoster` 的 adopt/wipe、`rollbackSessionRoster` 的对照、`configureGameState` 的四道门、`clearWorldFrame` 的六清、`clientGenerationIsActive`）。

## 二、**"失败饶过客户端；成功拿走它"**（本组最重要的一段）

### 2.1 那段

```php
// The other half of the enumeration. Exactly three places clear a client slot:
// SV_CheckTimeouts, which records a TimeoutDrop and is therefore never silent;
// commitSessionRoster; and here. A live run loses its client with no timeout logged, so
// it is one of the two roster paths.
//
// IT IS commitSessionRoster, not this one. This path only runs on a FAILED configure,
// and the log separates them cleanly: every ACCEPTED configure is followed within a
// second by clients=0, while the single run that FAILED at stage=server_commit_failed
// kept its client alive for twenty more seconds. Failure spares the client; success
// takes it.
```

### 2.2 二十四层

```text
1. **那个枚举的【另一半**】**
2. ⇒ **恰有三个地方清空一个客户端槽**：
      · **`SV_CheckTimeouts`** ⇒ **记录一个 `TimeoutDrop`** ⇒ **⇒ 所以【从不静默**】**
      · **`commitSessionRoster`**
      · **这里（`rollbackSessionRoster`）**
3. ⇒ **⇒ 而【一次实机运行【在没有 timeout 日志的情况下**】丢掉了它的客户端**
4. ⇒ **⇒ 所以【它是【两条 roster 路径之一**】】**
5. ⇒ **⚠ 它是 `commitSessionRoster`，【不是这一个**】**
6. ⇒ **⇒ 因为【这条路径【只在一个失败的 configure**】上跑**
7. ⇒ **而【日志【干净地把它们分开**】】**
8. ⇒ **每一个【被接纳的**】configure 在**一秒内**跟着 `clients=0`**
9. ⇒ **而【唯一那一次在 `stage=server_commit_failed` 失败的运行**】**
10. ⇒ **⇒ 把它的客户端【多留了二十秒**】**
11. ⇒ **⇒ 【失败饶过客户端；成功拿走它**】**
```

### 2.3 ⭐⭐⭐ **"失败饶过客户端；成功拿走它"**

**✅ 这是本报告里**最重要的一条反直觉**。**

**⇒ 三层**：
```text
失败 ⇒ **客户端【活着**】（20 秒）
成功 ⇒ **客户端【被清**】（1 秒内 `clients=0`）
⇒ **⇒ 所以【"成功"的路径【才是凶手**】】
```

**✅ 与 §433 的"`69420` 每次都拿到那个框"**同族（**第五次"症状与原因反直觉"）。

**⇒ 三层**：
```text
§433  **先连的占错槽** ⇒ **后连的被拒**
§434  **成功的路径杀客户端** ⇒ **失败的路径不杀**
⇒ **⇒ 两次反直觉**
```

**✅ ⭐⭐⭐ **一个"反直觉"的两例**。

### 2.4 而**"三处清空，一处从不静默"**

**⇒ 六层**：
```text
三处清空：
① `SV_CheckTimeouts` ⇒ **记录 `TimeoutDrop`** ⇒ **有证人**
② `commitSessionRoster` ⇒ **记 `ADOPTING`/`WIPING` 日志**（§4.1）
③ `rollbackSessionRoster` ⇒ **记 `WIPING ... rolledBack=` 日志**
⇒ **⇒ 所以【三处现在都有证人**】
```

**✅ 与 §426 的"两个非 (B) 分支都能楔死而两个都不说"**——**互补**（那里**加了证人**，这里**枚举了全部三处**）。

**⇒ 三层**：
```text
§426  **两个分支** ⇒ 加日志
§434  **三处清空** ⇒ 枚举并各有证人
⇒ **⇒ 两次"穷尽枚举 + 证人**】
```

**✅ ⭐⭐⭐ **一个"穷尽枚举"的实例**。

**⚠ 而"`TimeoutDrop` 的 `Cause`"⇒ **§432 说它已有而公告没读**。**

## 三、**`ADOPTING` vs `WIPING`**（本组第二重要）

### 3.1 那段

```php
// A client that is IN the new roster is not a leftover from some
// previous session -- it is this session's player, which connected
// during setup and is now being told which session it belongs to.
// Wiping it on generation alone is what made every live run end in
// "netchan packet has no connected client slot": the client
// completed DTLS and connected, SessionStart committed a roster
// carrying a new generation twenty seconds later, and the slot it
// was already using was thrown away underneath it. Adopt it
// instead, and keep wiping only the clients the new roster does
// not name.
```

### 3.2 二十层

```text
1. **一个【在新名册里**】的客户端【不是一个前一会话的遗留**】**
2. ⇒ **⇒ 它是【【这个】会话的玩家**】**
3. ⇒ **它在【设置期间连接**】**
4. ⇒ **而【现在被告知它属于哪个会话**】**
5. ⇒ **⚠ 只按【代次**】清它是【让每一次实机运行都以"`netchan packet has no connected client slot`"结束**】的东西**
6. ⇒ **客户端【完成了 DTLS 并连接**】**
7. ⇒ **而 `SessionStart` 【在二十秒之后**】提交了一个带【新代次**】的名册**
8. ⇒ **⇒ 而【它已经在用的那个槽【在它下面被扔掉了**】】**
9. ⇒ **⇒ 所以【接纳它**】**
10. ⇒ **而【只继续清【新名册【不命名**】的客户端**】**
```

### 3.3 ⭐⭐⭐ **"它已经在用的那个槽【在它下面**】被扔掉了"**

**✅ 这是本报告里**最重要的一条"时序竞态**。**

**⇒ 三层**：
```text
时刻 A：**客户端连接（`gen = 0`）**
时刻 B：**二十秒后，`SessionStart` 提交 `gen = 1`**
⇒ **⇒ 而【一条"清掉所有 `gen != 1`"的规则【在 B 时刻杀死了 A 时刻的客户端**】**
```

**✅ 与 §433 的"客户端在会话被 stage 之前连接没有名册"**——**同一根** ✓

**⇒ 三层**：
```text
§433  **先连的占第一个空闲槽** ⇒ 序号冲突
§434  **先连的代次是 `0`** ⇒ 被"按代次清"杀掉
⇒ **⇒ 两次"先连者受害**】
```

**✅ ⭐⭐⭐ **一个"先连者受害"的两例**。

**⚠ 而"两条修法"**：
```text
§433  **stageSessionRoster 里重定位座位**（因为客户端【还不知道自己的号**】）
§434  **commitSessionRoster 里 ADOPT**（因为客户端【已经在名册里**】）
⇒ **⇒ 所以【两个不同的守卫，同一个根**】
```

**✅ ⭐⭐ **"两个守卫，同一个根"**。

### 3.4 而**`clientGenerationIsActive` 的四个分支**

```cpp
bool SvClientSystem::clientGenerationIsActive(const ClientSlot &client) const
{
    if (!client.sessionGeneration)
        return !pendingRoster_ && !activeRoster_;
    return activeRoster_ &&
        client.sessionGeneration == activeRoster_->generation;
}
```

**⇒ 十层**：
```text
1. **`sessionGeneration == 0`**（**一个从未分代的客户端**）
2. ⇒ **⇒ 活跃【当且仅当【两个名册都为空**】】**
3. ⇒ **（即：没有任何名册 ⇒ 一个无会话的单机模式）**
4. ⇒ **`sessionGeneration != 0`**（**已分代**）
5. ⇒ **⇒ 活跃【当且仅当【它等于 `activeRoster_` 的代次**】】**
6. ⇒ **⇒ 所以【`pendingRoster_` 的代次【不算活跃**】】**
```

### 3.5 ⭐⭐⭐ **"`pendingRoster_` 的代次不算活跃"**

**✅ 这是 §428 的 gamestate 死锁四项之一**（`GENERATION_INACTIVE`）的来源。

**⇒ 三层**：
```text
一个客户端带了 `pendingRoster_` 的代次 ⇒ **`clientGenerationIsActive` 返回 `false`**
⇒ **⇒ 而 §428 的 gamestate 闸门【会拒绝发送**】
⇒ **⇒ 所以【"还没 commit" 是一个【合法的"不活跃"**】
```

**✅ 与 §428 的"四个项能把它关着"**完全闭合 ✓

**⇒ 三层**：
```text
§428  `GENERATION_INACTIVE`
§434  **`clientGenerationIsActive` 的实现**
⇒ **⇒ 一项的具体来源**
```

**✅ ⭐ **一个"闸门来源"的定位**。

**⚠ 而"`!pendingRoster_ && !activeRoster_`"⇒ **一个无会话模式**。**

**⇒ 三层**：
```text
两个名册都空 ⇒ **一个无会话的单机/测试模式**
⇒ **⇒ 所以【`gen = 0` 的客户端在那种模式下是活跃的**】
```

**✅ ⭐ **一个"无会话模式"的实例**。

## 四、**`configureGameState` 的四道门**（本组第三重要）

### 4.1 四道

```text
① sessionGeneration 必须匹配 pendingRoster_ 的代次
② gameState.playerNames 必须与名册的用户名【逐项相同】
③ SV_ValidateGameState 必须通过
④ （隐含）之后才 move 与 commit
```

**⇒ 十四层**：
```text
1. **① 代次匹配** ⇒ **否则拒绝并记 `requested=` 与 `pending=`**
2. ⇒ **② 玩家名【必须与名册【逐项相同**】】**
3. ⇒ **⇒ 否则记 `gameState=` 与 `roster=` 的【大小**】**
4. ⇒ **③ `SV_ValidateGameState`** ⇒ **否则记【四个**】：
      · `configStrings` 的数量
      · `simpleWeapons` 的数量
      · `modularWeapons` 的数量与【范围**】
      · **`weaponCount` 的值或 `<missing>`**
5. ⇒ **⇒ 而【全部通过之后**】才 move**
```

### 4.2 ⭐⭐⭐ **"Generation was validated before any state mutation, so commit cannot fail and gamestate/identity become visible together"**

```php
// Generation was validated before any state mutation, so commit
// cannot fail and gamestate/identity become visible together.
static_cast<void>(commitSessionRoster(sessionGeneration));
```

**⇒ 八层**：
```text
1. **代次【在任何状态变异之前**】被验证**
2. ⇒ **⇒ 所以 `commit` 【不能失败**】**
3. ⇒ **⇒ 而【gamestate 与身份【一起变得可见**】】**
4. ⇒ **⇒ 一个"预验证消除失败**"的模式**
```

**✅ 与 §409 的"候选-提交模式"**完全同族（**第五次"预验证**）。

**⇒ 三层**：
```text
§409  `candidate` → 转移 → 检查 → **全部成功才 `move`**
§433  `queueScoreboardResponse` 的 `pendingCount + size > capacity` **先检查**
§434  **`sessionGeneration` 先验证 ⇒ `commit` 不能失败**
⇒ **⇒ 三次"先验证后提交**】
```

**✅ ⭐⭐ **一个"预验证"的三例表**。

**⚠ 而"`static_cast<void>(...)`"⇒ **一个显式的忽略返回值**，**因为"它不能失败"**。**

**✅ 与 §422 的"`static_cast<void>(clients_.queueReliableCommand(...))`"**同族（**第九次"忽略返回值"）。

**⇒ 三层**：
```text
若【不检查】⇒ **一个静默的失败**
而【注释说明了为什么不能失败**】 ⇒ **一个已证明的忽略**
⇒ **⇒ 所以【注释是那个忽略的许可证**】
```

**✅ ⭐⭐⭐ **"注释是那个忽略的许可证"** —— 本报告里最重要的一条关于 `static_cast<void>` 的说明。

### 4.3 而**"②玩家名逐项相同"** 的理由

**⇒ 三层**：
```text
名册 ⇒ **`xuid` 排序 ⇒ 序号 = 槽**
gamestate ⇒ **`playerNames` 按【同序**】
⇒ **⇒ 所以【两者必须逐项相同**】**
```

**✅ 与 §433 的"名册按 `xuid` 排序固定序号，而 gamestate 按同样顺序提交"**完全闭合 ✓

**⇒ 三层**：
```text
§433  **"名册固定每个成员的槽，而 gamestate 按同样的顺序提交玩家名"**
§434  **`gameState.playerNames != expectedNames ⇒ 拒绝**
⇒ **⇒ 那个"必须"被【强制执行**】
```

**✅ ⭐⭐ **一个"约束被强制执行"的实例**。

**⚠ 而"只记【大小**】"⇒ **一个不完整的诊断**。**

**⇒ 三层**：
```text
日志：`gameState=2 roster=3`
⇒ **⇒ 知道【数量不同**】但【不知道【是哪一个**】】
```

**⚠ 一个**诊断的局限**（**标注**）。

**✅ 与 §432 的"逐要素一致漏了一个字节"**同族（**第三次"一个不完整的验证**）。

## 五、**`clearWorldFrame` 的六清**（本组第四重要）

```cpp
for (auto &client : clients_) {
    client.snapshotHistory = {};
    client.lastSnapshotServerTime = 0;
    client.snapshotSent = false;
    client.baselineCacheAcknowledged = false;
    client.baselineCacheInitializationMessage.reset();
    client.newestFlaggedSnapshotMessage.reset();
    client.baselineFrame.reset();
}
```

**⇒ 十二层**：
```text
1. **七样**（不是六）
2. ⇒ **`snapshotHistory = {}`** ⇒ **历史帧全部作废**
3. ⇒ **`lastSnapshotServerTime = 0`** ⇒ **去重键重置**
4. ⇒ **`snapshotSent = false`** ⇒ **允许重发同一 `serverTime`**
5. ⇒ **`baselineCacheAcknowledged = false`**
6. ⇒ **`baselineCacheInitializationMessage.reset()`**
7. ⇒ **`newestFlaggedSnapshotMessage.reset()`**
8. ⇒ **`baselineFrame.reset()`**
9. ⇒ **⇒ 与 §426 的 `stage 6` 的清【完全同一组**】**
```

### 5.1 ⭐⭐⭐ **"与 `stage 6` 的清完全同一组"**

**⇒ 三层**：
```text
§426  `stage 6`（**进入世界**）⇒ 清六个
§434  `clearWorldFrame`（**世界重建**）⇒ 清七个
⇒ **⇒ 所以【两个"快照状态失效**"的时刻**】
```

**✅ 与 §429 的"客户端进入世界时扔掉了快照状态"**完全同源 ✓

**⇒ 三层**：
```text
§426  **`stage 6` ⇒ 客户端重新初始化 cgame**
§434  **`clearWorldFrame` ⇒ 服务器重建世界**
⇒ **⇒ 两端的"代次变更**"必须【同时清**】
```

**✅ ⭐⭐ **一个"两端同时清"的实例**。

**⚠ 而"`lastSnapshotServerTime = 0`"⇒ **§429 的 `DuplicateServerTime` 检查**。**

**⇒ 三层**：
```text
`buildSnapshotMessage`：`client.snapshotSent && client.lastSnapshotServerTime == worldFrame_->serverTime` ⇒ **拒绝 `DuplicateServerTime`**
⇒ **⇒ 所以【`clearWorldFrame` 必须重置两者**】
```

**✅ ⭐ **一个"检查与重置的配对"**。

## 六、**`gameplayAuthorityReady_` 的 `setGameplayAuthorityReady`**

```cpp
void SvClientSystem::setGameplayAuthorityReady(const bool ready)
{
    gameplayAuthorityReady_ = ready;
    if (ready) return;
    for (auto &client : clients_) {
        client.pendingUserCmds.clear();
        client.lastQueuedUserCmdTime = client.lastReceivedUserCmd ? client.lastReceivedUserCmd->commandTime : 0;
    }
}
```

**⇒ 八层**：
```text
1. **`ready = true` ⇒ 【什么都不做**】**
2. ⇒ **`ready = false` ⇒ 【清空所有 `pendingUserCmds`**】**
3. ⇒ **并把 `lastQueuedUserCmdTime` 设成【最后收到的命令时间**】**
4. ⇒ **⇒ 所以【权威不可用时【丢弃队列并重置基准**】**
```

**✅ 与 §428 的"`!gameplayAuthorityReady_` ⇒ `pendingUserCmds.clear()` + 设 `lastQueuedUserCmdTime`"**完全一致 ✓

**⇒ 三层**：
```text
§428  `SV_PacketEvent` 的 `!gameplayAuthorityReady_` 分支
§434  `setGameplayAuthorityReady(false)` 的同一动作
⇒ **⇒ 两处同一行为**
```

**✅ ⭐ **一个"同一行为两处"的确认**。

## 七、**`autoSelectMissingLoadouts` 的"唯一的人步骤"**

### 7.1 那段

```php
// WHY THIS EXISTS. Every gate from SessionStart to a spawned player is automatic
// except one: the class pick, which arrives as a changeclass menu response from the
// client's own UI. That single human step made every test cycle need somebody
// watching the screen, and the things still being debugged -- movement, the
// viewmodel, the DObj -- are all AFTER it. So synthesize the same response the
// client would send, through the same dispatcher, and let the rest of the flow run
// untouched.
//
// Deliberately NOT a gameplay behaviour: it is off unless OLMOD_AUTO_LOADOUT=1, it
// only ever fires for a client that has been Active for a while without choosing,
// and it picks custom1 -- the first class the session roster registered. A real pick
// arriving first wins, because pendingSelectedLoadout is then already set.
```

### 7.2 十八层

```text
1. **从 `SessionStart` 到一个已出生的玩家，【每一个门都是自动的【除了一个**】】**
2. ⇒ **职业选择，它作为【一个 changeclass 菜单响应**】来自客户端的 UI**
3. ⇒ **⇒ 那一个【人的步骤**】让【每一个测试周期都需要有人【看着屏幕**】】**
4. ⇒ **而【仍在调试的东西**】：
      · **移动**
      · **viewmodel**
      · **DObj**
5. ⇒ **⇒ 全部【在那个步骤【之后**】】**
6. ⇒ **⇒ 所以【合成【客户端会发的同一个响应**】**】
7. ⇒ **通过【同一个 `dispatcher`**】**
8. ⇒ **而【流程的其余部分【原样跑**】】**
9. ⇒ **⇒ 刻意地【不是一个玩法行为**】**
10. ⇒ **`OLMOD_AUTO_LOADOUT=1` 才开**
11. ⇒ **只对一个【已经 `Active` 一段时间而没有选**】的客户端触发**
12. ⇒ **而它选 `custom1` —— 名册注册的第一个职业**
13. ⇒ **⇒ 而【一个先到的真实选择【赢**】，因为 `pendingSelectedLoadout` 那时【已经设了**】**
```

### 7.3 ⭐⭐⭐ **"通过同一个 dispatcher，让流程的其余部分原样跑"**

**✅ 这是本报告里**最重要的一条"测试注入的正确做法"**。**

**⇒ 三层**：
```text
错误：**直接设置 `selectedLoadout`** ⇒ **绕过 dispatcher ⇒ 少测一段**
正确：**合成一个【客户端会发的响应**】并【喂给同一个 `dispatcher`**】
⇒ **⇒ 所以【整条链路都被测到**】
```

**✅ 与 §427 的"对称往返即使两边都错也会通过"**相反**（那里**测了不该测的**，这里**测了该测的**）。

**⇒ 三层**：
```text
§427  **写者+读者都来自我们** ⇒ 零信息
§434  **合成的输入 + 真实的 dispatcher** ⇒ 有信息
⇒ **⇒ 区别在【输入是不是合成的**】
```

**✅ ⭐⭐⭐ **"合成的输入 + 真实的处理链是有信息的；合成的输入 + 合成的处理链是零信息的"** —— 一个**极精确的测试判据**。

**⚠ 而"一个先到的真实选择赢"⇒ **一个人工优先的判据**。**

**⇒ 三层**：
```text
`pendingSelectedLoadout` 非空 ⇒ **自动选择【不触发**】
⇒ **⇒ 所以【真实选择优先**】
```

**✅ ⭐⭐ **"真实优先于合成"** —— 与 §408 的"`OK` 与 `Cancel` 的优先级"**同族。

**⚠ 而"_dupenv_s"`⇒ **一个 Windows 特有的环境变量读取**。**

**✅ 与 §432 的 `getenv`**不同（这是**`_dupenv_s`**，更安全但更罗嗦）。

**⇒ 三层**：
```text
`getenv` ⇒ **简单但有缓冲区风险**
`_dupenv_s` ⇒ **分配一个缓冲区，调用者释放**
⇒ **⇒ 所以【这里选了后者**】
```

**✅ ⭐ **一个"安全 API"的选择**。

## 八、关键结论

1. **⭐⭐⭐ "失败饶过客户端；成功拿走它"**：**每一个被接纳的 `configure` 在一秒内跟着 `clients=0`，而唯一那一次在 `stage=server_commit_failed` 失败的运行把它的客户端多留了二十秒** ⇒ **第五次"症状与原因反直觉"**（与 §433 同族）。
2. **⭐⭐ "恰有三处清空一个客户端槽：`SV_CheckTimeouts`（记 `TimeoutDrop`，从不静默）、`commitSessionRoster`、`rollbackSessionRoster`"`** —— **一个穷尽枚举**（与 §426 的"加证人"互补）。
3. **⭐⭐⭐ `commitSessionRoster` 的 `ADOPTING` vs `WIPING`**：**"只按代次清它是让每一次实机运行都以 `netchan packet has no connected client slot` 结束的东西：客户端完成了 DTLS 并连接，`SessionStart` 在二十秒之后提交了一个带【新代次】的名册，而它已经在用的那个槽【在它下面】被扔掉了"`** —— **第六次"先连者受害"**（与 §433 同根：**两个不同的守卫，同一个根**）。
4. **⭐⭐ "一个在新名册里的客户端不是前一会话的遗留，它【是这个会话的玩家】，它在设置期间连接，而现在被告知它属于哪个会话"`** —— **"接纳它，而只继续清新名册不命名的客户端"**。
5. **⭐⭐⭐ `clientGenerationIsActive` 的四个分支**：`sessionGeneration == 0` ⇒ **活跃当且仅当两个名册都为空**（**无会话模式**）；`!= 0` ⇒ **活跃当且仅当等于 `activeRoster_` 的代次** ⇒ **`pendingRoster_` 的代次不算活跃** —— 这正是 §428 的 `GENERATION_INACTIVE` 闸门的来源。
6. **⭐⭐⭐ `configureGameState` 的四道门**：① **代次匹配 `pendingRoster_`**；② **`playerNames` 与名册逐项相同**（§433 的约束被强制执行）；③ **`SV_ValidateGameState`**（否则记四个数：`configStrings`/`simpleWeapons`/`modularWeapons`+范围/`weaponCount` 或 `<missing>`）④ **全部通过之后才 `move`**。
7. **⭐⭐⭐ "代次在任何状态变异之前被验证，所以 `commit` 不能失败，而 gamestate 与身份一起变得可见"`** ⇒ **`static_cast<void>(commitSessionRoster(...))` 是一个【已证明的忽略】，而【注释是那个忽略的许可证】`** —— 第三次"预验证后提交"（与 §409/§433 同族），也是本文档里最清晰的一条关于 `static_cast<void>` 的说明。
8. **⚠ 一个诊断的局限**：`gameState=` 与 `roster=` 只记**大小** ⇒ 知道数量不同但不知道是哪一个 —— 第三次"一个不完整的验证"（与 §432 同族）。
9. **⭐⭐ `clearWorldFrame` 的七清**（`snapshotHistory` / `lastSnapshotServerTime` / `snapshotSent` / `baselineCacheAcknowledged` / `baselineCacheInitializationMessage` / `newestFlaggedSnapshotMessage` / `baselineFrame`）**与 §426 的 `stage 6` 完全同一组** —— 一个"两端同时清"的实例（**`stage 6` 是客户端重新初始化 cgame，`clearWorldFrame` 是服务器重建世界**）。
10. **⭐ `lastSnapshotServerTime = 0` 与 `snapshotSent = false` 是 §429 的 `DuplicateServerTime` 检查的配对重置**。
11. **⭐ `setGameplayAuthorityReady(false)` 与 §428 的 `!gameplayAuthorityReady_` 分支做同一动作**（清队列 + 重置基准）。
12. **⭐⭐⭐ `autoSelectMissingLoadouts` 的"通过同一个 dispatcher，让流程的其余部分原样跑"**：**"合成的输入 + 真实的处理链是有信息的；合成的输入 + 合成的处理链是零信息的"`** —— 与 §427 的"对称往返"形成**极精确的对照**。
13. **⭐ "一个先到的真实选择赢，因为 `pendingSelectedLoadout` 那时已经设了"`** —— 真实优先于合成。
14. **⭐ `_dupenv_s` 而不是 `getenv`**（分配一个缓冲区，调用者释放）。

## 九、未闭合点

- `stage=server_commit_failed` 的完整阶段枚举。
- `SV_ValidateGameState` 的具体条件。
- `custom1` 的命名（名册注册的第一个职业）。
- `OLMOD_AUTO_LOADOUT` 的"Active 一段时间"阈值。
- `dupenv_s` 的返回值处理（未读完）。
- `sv_client_mp.cpp` 3480 行之后未读取（**共 `4500` 行**）。
