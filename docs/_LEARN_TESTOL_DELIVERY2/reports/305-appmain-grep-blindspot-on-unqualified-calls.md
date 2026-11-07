# 305 · **"`commitSessionRoster` 从未被调用"是假的** —— `grep` 匹配不到类内非限定调用、`FRAMESTALL` 的两路计时

## 一、范围

本报告学习 `Appmain.cpp` 7640–7860 行。

## 二、loadout 刷新的**四个条件**

```cpp
if (role != Dedicated && SV_ShouldRefreshClientLoadouts(
        initialStatus.gameStateConfigured, initialStatus.activeClients, refreshRequested) &&
    (!LastLoadoutPrepareRequestSequence ||
     *LastLoadoutPrepareRequestSequence != requestSequence ||
     !LastLoadoutPrepareAttempt ||
     nowMilliseconds - *LastLoadoutPrepareAttempt >= 1000))
{
    LastLoadoutPrepareAttempt = nowMilliseconds;
    LastLoadoutPrepareRequestSequence = requestSequence;
    static_cast<void>(prepareClientLoadouts());
}
```

### 2.1 四个

```text
role != Dedicated
SV_ShouldRefreshClientLoadouts(...)      ← 【一个策略函数】
（序列变了 或 从未试过 或 已过 1 秒）
```

**⇒ 第三个条件是**四个子条件的三路 OR**。**

**✓ 所以"序列变"⇒ 立即刷新；否则**每秒重试一次**。**

### 2.2 而 `SV_ShouldRefreshClientLoadouts` 的**三个参数**

```text
gameStateConfigured
activeClients
refreshRequested
```

**⇒ 三项。**

### 2.3 而 1 秒节流**第四次出现**（§279 / §281 / §294 / §305）。

## 三、`NET_Frame` 与**连接无关诊断**

```cpp
Network.NET_Frame(Server, nowMilliseconds);
const auto status = Server.status();
if (role == Dedicated)
{
    static uint32 loggedConnectionlessConnected{};
    static uint32 loggedConnectionlessRejected{};
    const auto diagnostics = Server.connectionlessDiagnostics();
    if (diagnostics.connected != loggedConnectionlessConnected)
    {
        loggedConnectionlessConnected = diagnostics.connected;
        logGameServer("connectionless connected peer=" + ipv4 + ":" + port + " slot=" + slot);
    }
    if (diagnostics.rejected != loggedConnectionlessRejected)
    {
        loggedConnectionlessRejected = diagnostics.rejected;
        logGameServer("connectionless rejected peer=" + ipv4 + ":" + port + " reason=" + reason);
    }
}
```

### 3.1 三层

```text
1. **保持连接无关的失败在持久服务器日志里**
2. 因为**专用服进程通常没有可见控制台**
3. ⇒ 所以 `ServerCore` 里的临时 `std::clog` 诊断否则会**丢失**
```

### 3.2 而两个**累积计数器的变化触发**

```text
connected     连接数
rejected      拒绝数
```

**⇒ 与 §276 的"整元组去重"同族（第六次）。**

### 3.3 而 `reason` 是**字符串**

**⇒ 所以拒绝原因可见。**

**✓ 与 §236 的"一个拒绝只说哪个门拒绝了"同族。**

## 四、`configurePendingBooking` 的**两个门槛**

```cpp
const auto mayInitializeDedicatedConfigStrings =
    role == Dedicated && status.netchanPacketsReceived != 0;
markFramePhase(5);
static_cast<void>(configurePendingBooking(
    status.netchanPacketsReceived != 0 &&
    (status.clientsReadyForGameState != 0 || mayInitializeDedicatedConfigStrings)));
```

### 4.1 而 `mayInitializeConfigStrings` 的**两项**

```text
netchanPacketsReceived != 0
(clientsReadyForGameState != 0 || mayInitializeDedicatedConfigStrings)
```

**⇒ 两项，而第二项是**三路 AND/OR 混合**。**

### 4.2 展开

```text
A = netchanPacketsReceived != 0
B = clientsReadyForGameState != 0
C = role == Dedicated && A

mayInit = A && (B || C)
```

**⇒ 若 `A` 真且 `Dedicated`，则 `C` 真 ⇒ `mayInit` 真。**

**⇒ 若 `A` 真但非 Dedicated，则 `C` 假 ⇒ 需 `B` 真。**

**✓ 所以客户端需要"有客户端就绪"，而专用服只要"收到包"。**

### 4.3 而"**帧线程在被接受后两秒内停止**"

```php
// The frame thread stops within two seconds of the booking being accepted, somewhere past
// here (sec 36d). Everything from this point is reachable only once configureBooking has
// returned true, which no run before 2026-08-19 ever did -- so bracket it and let the last
// line printed name the region.
logGameServer("pending booking ready: configuring gamestate map=" + ... + " gametype=" + ...);
```

### 4.4 四层

```text
1. 帧线程在 booking 被接受后**两秒内停止**
2. ⇒ **从这里往后的每一行**只有在 `configureBooking` 返回 true 后才可达
3. 而**2026-08-19 之前的任何运行都没做到过**
4. ⇒ **把它括起来并让最后打印的那行命名区域**
```

**✅ 与 §303 的"看门狗"是同一个问题的两种手段**（一个是日志围栏，一个是独立线程）。

## 五、`FRAMESTALL` 的**两路计时**（本组第二重要）

```cpp
const auto serverCpuStart = role == Dedicated ? currentThreadCpuMicroseconds() : std::nullopt;
const auto serverFrameTimingStart = RuntimeClock::now();
try { outbound = Server.onComFrame(nowMilliseconds); }
catch (const std::exception &error)
{
    logGameServer("server frame terminated by C++ exception: " + error.what());
    throw;
}
const auto serverWallUs = elapsedMicroseconds(serverFrameTimingStart);
ServerFrameTiming.record(serverWallUs);
// Wall timers alone mislabel scheduler/I/O waits as expensive native
// movement. Only report slow frames, at most once per second. CPU time
// has OS accounting granularity; it is a discriminator, not a profiler.
static uint64 lastSlowFrameReport{};
if (serverWallUs >= 50000u && serverCpuStart &&
    (!lastSlowFrameReport || nowMilliseconds - lastSlowFrameReport >= 1000u))
{
    const auto cpuEnd = currentThreadCpuMicroseconds();
    if (cpuEnd && *cpuEnd >= *serverCpuStart)
    {
        lastSlowFrameReport = nowMilliseconds;
        logGameServer("FRAMESTALL wallUs=" + serverWallUs + " threadCpuUs=" + (*cpuEnd - *serverCpuStart));
    }
}
```

### 5.1 五层

```text
① 只有专用服取 CPU 起点
② 墙钟无论如何取
③ `onComFrame` 包在 try/catch 里（记录后**重新抛**）
④ **"只有墙钟会把调度/IO 等待误标为昂贵的原生移动"**
⑤ 只在 `wallUs >= 50000`（50 ms）且**每秒最多一次**时报告
```

### 5.2 **"墙钟单独会误标调度/IO 等待为昂贵的原生移动"**

**⇒ 三层**：

```text
1. 墙钟 = CPU 时间 + 等待
2. ⇒ 单独看墙钟**无法区分"算法慢"与"被抢占"**
3. ⇒ 所以需要 CPU 时间作**判别器**
```

### 5.3 而"**CPU 时间有 OS 记账粒度；它是一个判别器，不是分析器**"

**⇒ 三层**：

```text
1. CPU 时间有 OS 记账粒度（约 15 ms）
2. ⇒ 它**不是一个分析器**
3. ⇒ 它只用来**区分**"CPU 忙"与"在等"
```

**✅ 一个精确的工具定位。**

### 5.4 而 `FRAMESTALL` 与 §293 的同一个标签

**§293**："`FRAMESTALL wallUs=977641 threadCpuUs=890625`"

**⇒ 所以那是**这个**日志行的实例。**

**✅ 跨报告闭环。**

### 5.5 而 `try/catch` 里**重新抛**

```cpp
catch (const std::exception &error)
{
    logGameServer("server frame terminated by C++ exception: " + error.what());
    throw;    // ← 【重新抛】
}
```

**⇒ 三层**：

```text
1. 记录原因
2. **重新抛**（不吞掉）
3. ⇒ 让上层（或崩溃）处理
```

**✓ 与 §244 的"两个方向代价不对称"配合 —— 吞掉会更糟。**

## 六、`markFramePhase(6)` 的**位置**

```cpp
markFramePhase(5);
configurePendingBooking(...);
configurePendingWorldSpawn(nowMilliseconds);
configureBotClients();
markFramePhase(6);
outbound = Server.onComFrame(nowMilliseconds);      // ← 【第 6 阶段的实际工作】
markFramePhase(7);
```

### 6.1 **`markFramePhase(6)` 在 `onComFrame` **之前**

**⇒ 与 §303 的"每个名字是**已进入**的区域"一致** ✓

**⇒ 所以"停顿在阶段 6" = "停在 `onComFrame` 里"。**

### 6.2 而看门狗**只报阶段 6**

**⇒ 所以它专抓 `onComFrame` 的停顿。**

**✓ 与 §303 的"专用服帧线程在 gamestate 配置后几秒停止"配合 —— 那是 `onComFrame`。**

## 七、**"`commitSessionRoster` 从未被调用"是假的**（本组最重要的一段）

### 7.1 那段完整的自我更正

```php
// AIM THE INSTRUMENT AT THE TRANSITION ITSELF: whenever connectedClients changes, print
// every slot the server will still talk about, so whatever empties them shows up in the
// census on one side or the other.
//
// CORRECTION. An earlier version of this comment claimed "commitSessionRoster is never
// called from anywhere". THAT IS FALSE, and it is the whole bug. It is called from
// SvClientSystem::configureGameState under `if (sessionGeneration)`, and has been since
// 99d66d1 -- an UNQUALIFIED intra-class call, which a grep for the member-qualified form
// (`.commitSessionRoster`, `Server.commitSessionRoster`) does not match. The log proves
// the reachability without reading any code: the client dies within a second of every
// `gamestate configuration ACCEPTED`, and on the one run that FAILED at
// stage=server_commit_failed -- the failure that returns before this very call -- the
// client SURVIVED for twenty more seconds. Accept kills it; failure spares it.
```

### 7.2 八层

```text
1. **修正**：早先版本声称"`commitSessionRoster` 从未从任何地方被调用"
2. **那是假的，而它就是整个 bug**
3. 它从 `SvClientSystem::configureGameState` 在 `if (sessionGeneration)` 下被调用
4. 而这从 **99d66d1** 起就是这样
5. ⇒ **一个【非限定的类内调用】**，而对成员限定形式（`.commitSessionRoster`、`Server.commitSessionRoster`）的 `grep` **匹配不到**
6. ⇒ **日志证明可达性而不读任何代码**：
7. **客户端在每一次 `gamestate configuration ACCEPTED` 之后一秒内死掉**
8. 而**在那一次于 `stage=server_commit_failed` 失败的运行**（那个失败**在这个调用之前就返回了**）⇒ **客户端多活了二十秒**
9. ⇒ **接受杀死它；失败饶它**
```

### 7.3 **这是一个极重要的方法论发现**

**⇒ "`grep` 一个成员限定形式匹配不到非限定的类内调用"**

**⇒ 与记忆里 `codol-grep-sweep-skips-binaries`（"目录级 grep 只回文本文件"）**同族。**

**⇒ 第三次"`grep` 的盲区"：**

```text
记忆    目录级 grep 跳过二进制
§305    `grep` 一个成员限定形式漏掉非限定的类内调用
§259    （若用 `grep` 而非全扫会漏）
```

### 7.4 而**"接受杀死它；失败饶它"**是一个**干净的对照实验**

```text
ACCEPTED         ⇒ 客户端一秒内死
server_commit_failed（在调用之前返回）⇒ 客户端多活 20 秒
```

**⇒ 所以**因果已定** —— `commitSessionRoster` 是杀死客户端的那一步。**

**✅ 这是一个**完美的差分证据**（第五次"用两个分支的差定因果"）。**

### 7.5 而"**日志证明可达性而不读任何代码**"

**⇒ 三层**：

```text
1. 不需要读代码
2. 只需要**两个分支的不同后果**
3. ⇒ 就证明了"那个调用**确实被执行**"
```

**✅ 与 §243 的"686 对照"、§277 的"我瞄的正是那堵墙"同族。**

### 7.6 而**census 的九个字段**

```cpp
census += (census.empty() ? "" : " | ") + clientNum + ":state=" + state +
    " xuid=" + xuid + " peer=" + ipv4 + ":" + port +
    " gen=" + sessionGeneration + " genActive=" + (0|1) +
    " lastPacket=" + lastPacketTime;
```

**⇒ 七个字段。**

### 7.7 而 census **只在 `connectedClients` 变化时打印**

```cpp
if (finalStatus.connectedClients != LastCensusConnectedClients) { ... }
```

**⇒ 三个量**：

```text
旧值 -> 新值
now=
[每个槽的明细]
```

**⇒ 所以"什么把它们清空了"会在 census 的一侧或另一侧出现。**

**✓ 一个精确的诊断设计。**

## 八、`client-think rejected` 的**六个 + 十一个**

```cpp
"client-think rejected client=" + clientNum + " commandTime=" + lastAttempted +
" committed=" + lastCommitted + " psCmdTime=" + playerStateCommandTime +
" serverTime=" + serverTime + " stage=" + stageName + " failures=" + failureCount +
(nativeActionDiagnostics ? " nativeAction={pmType= ... clientNum= ... viewmodel= ...
    weapon= ... anim=a,b state=a,b shots=a,b}" : "")
```

### 8.1 七个基本 + 七个 nativeAction

```text
基本    clientNum / commandTime / committed / psCmdTime / serverTime / stage / failures
native  pmType / clientNum / viewmodel / weapon / anim[2] / state[2] / shots[2]
```

**⇒ 七个 + 七个（其中三个是 2 元组 ⇒ 十个值）。**

### 8.2 而触发的**三条件**

```cpp
if (thinkStatus->failureStage != None &&
    (!lastStatus ||
     lastStatus->lastAttemptedCommandTime != thinkStatus->lastAttemptedCommandTime ||
     lastStatus->failureStage != thinkStatus->failureStage))
```

**⇒ 三层**：

```text
失败阶段非 None
且（无上次 或 commandTime 变了 或 失败阶段变了）
```

**⇒ 所以"同一个失败反复在同一 commandTime"不重复打印。**

**✓ 与 §273 的 `(reason, weapon)` 去重同族（第七次）。**

## 九、关键结论

1. **loadout 刷新的四个条件**含"序列变 或 从未试过 或 已过 1 秒"。
2. **1 秒节流第四次出现**。
3. **"专用服没有可见控制台 ⇒ `std::clog` 会丢失"** —— 所以要转存到持久日志。
4. **`configurePendingBooking` 的两项：客户端需"有客户端就绪"，专用服只要"收到包"**。
5. **"帧线程在被接受后两秒内停止"**，而"2026-08-19 之前的任何运行都没做到过"。
6. **`FRAMESTALL` 的两路计时**：墙钟 + CPU 时间。
7. **"墙钟单独会误标调度/IO 等待为昂贵的原生移动"**。
8. **"CPU 时间是判别器不是分析器"** —— OS 记账粒度约 15 ms。
9. **`markFramePhase(6)` 在 `onComFrame` **之前** ⇒ 所以"停顿在阶段 6" = "停在 `onComFrame` 里"。
10. **⭐ "`commitSessionRoster` 从未被调用"是假的** —— 它是**非限定的类内调用**而 `grep` 匹配不到。
11. **`grep` 盲区第三次**（前两次：目录级跳过二进制、成员限定形式）。
12. **"接受杀死它；失败饶它"** —— `ACCEPTED` 一秒内死 vs `server_commit_failed` 多活 20 秒。
13. **"日志证明可达性而不读任何代码"** —— 一个完美的差分证据（第五次）。
14. **census 只在 `connectedClients` 变化时打印**，含七个字段。
15. **`client-think rejected` 的七 + 十个值**，且"同一 commandTime 同一阶段"不重复。

## 十、未闭合点

- `commitSessionRoster` 具体如何杀死客户端。
- `SV_ShouldRefreshClientLoadouts` 的策略。
- `99d66d1` 是哪次提交。
- `Appmain.cpp` 7860 行之后未读取。
