# 392 · **"50 仍然是默认，而 100 已被证明"** —— 两个耦合常数、`pending=8` 是队列容量、玩家实测"移动快但不平滑"

## 一、范围

本报告学习 `sv_main_mp.cpp` 1000–1350 行。

## 二、**50 vs 100ms 的完整实验记录**（本组最重要的一段）

### 2.1 那段（第一半：测量）

```php
// 50 STILL, AND 100 IS PROVEN -- OLMOD_SV_FRAME_MS=100. See the block below.
//
// Retail's cadence IS 100 ms -- measured 2026-09-05 by decoding both sides with the
// same tool: retail 6160 snapshots / 621.4 s = 9.9/s against ours at 19.9/s, exactly
// double, which is also why a match dies at ~55 minutes on a 16-bit sequence
// (codol-a-match-dies-at-65536-packets). All of that still stands.
//
// IT WAS TRIED LIVE AND THE PLAYER FELT IT IMMEDIATELY: "movement feels somewhat
// faster, but not as smooth, it kind of jerks me because the server needs to keep up
// with my fast directional changes." Confirmed at 8.1 snapshots/s measured on the
// client, so the cadence really was live, and the log said why:
//
//     pending=8   cmdAge=143..155   thinkCommands=257..300
//
// pending 8 IS the queue capacity, and cmdAge ~150 ms is the server executing input
// a seventh of a second old.
```

### 2.2 十八层

```text
1. **50 仍然是默认，而 100 已被证明**（`OLMOD_SV_FRAME_MS=100`）
2. ⇒ **零售的节拍【就是 100ms】**
3. ⇒ **2026-09-05 用【同一个工具】解码双方测得**：
     · **零售 `6160` 个快照 / `621.4` 秒 = `9.9/s`**
     · **我们对 `19.9/s`**
     · **恰好两倍**
4. ⇒ **那也是为什么一场比赛在 `~55` 分钟时【死在一个 16 位序列上】**
5. ⇒ **（`codol-a-match-dies-at-65536-packets`）**
6. ⇒ **所有那些仍然成立**
7. ⇒ **它被试过实机而玩家【立刻】感觉到了**：
      · **"移动感觉快一些，但不那么平滑，它把我【猛推】了"
8. ⇒ **因为服务器需要跟上我的快速方向变化"**
9. ⇒ **在客户端测得 `8.1` 快照/秒【确认】了那个节拍真的生效了**
10. ⇒ **而日志说了为什么**：
      · **`pending=8`**
      · **`cmdAge=143..155`**
      · **`thinkCommands=257..300`**
11. ⇒ **`pending 8` 【就是】队列容量**
12. ⇒ **而 `cmdAge ~150ms` 是服务器在执行【七分之一秒前】的输入**
```

### 2.3 ⭐⭐ **"恰好两倍"与"55 分钟"**

**✅ 与 §372 的"零售 `1909/1909` vs 我们 `95/558`"**同族（**第九次"同工具对拍"）。**

**⇒ 三层**：

```text
零售  9.9/s
我们  19.9/s
⇒ **恰好两倍**
⇒ **所以 16 位序列的耗尽时间也恰好一半**（110 分钟 → 55 分钟）
```

**✅ ⭐ **一个"倍数关系"的双向闭合**。**

**⚠ 而"`65536` 包"⇒ **16 位序列的容量**。**

**✅ 与 §342 的"`uint8` 的模算术"**同族（**第二次"序列回绕"）。**

### 2.4 而**"玩家立刻感觉到了"**

**✅ 与 §355 的"玩家的判决"**第十次。**

**⇒ 三层**：

```text
实机设置 100ms ⇒ **玩家："移动快一些但不那么平滑，它猛推我"**
⇒ 而"猛推"⇒ **`cmdAge=143..155`**（服务器执行 150ms 前的输入）
⇒ **⇒ 玩家的方向变化【积压】而一次性执行**
```

**✅ **一个"体感 → 日志"的完整对应**。**

### 2.5 那段（第二半：根因）

```php
// THE CAUSE IS A COUPLED CONSTANT I MOVED ALONE. SV_ChargeClientThinkTime spends a
// fixed 100 ms budget of simulated command time per snapshot cycle -- Ghosts' default,
// paired with Ghosts' tick rate. At a 50 ms frame that is 100 ms of budget every
// 50 ms, TWICE real time, and the headroom is what absorbs a burst of commands. At a
// 100 ms frame it is 100 ms every 100 ms: exactly real time, no headroom at all. A
// fast direction change produces a burst, and the burst has nowhere to go.
//
// So the frame interval and the think budget are one decision, not two, and BOTH
// coupled constants have since moved:
//
//   PendingUserCmdCapacity          8 -> 32   CODOL's own MAX_PACKET_USERCMDS, read
//                                             off CL_WritePacket 0x005B2C10
//   SV_ClientThinkBudgetMilliseconds  -> 0 (drain the bounded queue)
//
// The larger queue was byte-for-byte inert at 50 because it peaked at 7 of 8
// across every runtime-perf sample. Removing the artificial budget now matches
// CODOL's command loop and prevents a remote burst from carrying into later frames.
```

### 2.6 十六层

```text
1. **原因是【一个我单独移动的耦合常数】**
2. ⇒ **`SV_ChargeClientThinkTime` 每个快照周期花【固定的 100ms 预算】的模拟命令时间**
3. ⇒ **那是 Ghosts 的默认，配 Ghosts 的 tick 率**
4. ⇒ **在 `50ms` 帧上那是【每 50ms 有 100ms 的预算】** ⇒ **两倍实时**
5. ⇒ **而那个余量【正是】吸收一串命令的东西**
6. ⇒ **在 `100ms` 帧上那是每 100ms 有 100ms：恰好实时，【没有余量】**
7. ⇒ **一次快速方向变化产生一个爆发，而那个爆发【无处可去】**
8. ⇒ **所以帧间隔与 think 预算是【一个决定，不是两个】**
9. ⇒ **而两个耦合常数此后都移动了**：
      · **`PendingUserCmdCapacity` `8 → 32`**（**CODOL 自己的 `MAX_PACKET_USERCMDS`，从 `CL_WritePacket 0x005B2C10` 读出**）
      · **`SV_ClientThinkBudgetMilliseconds` `→ 0`**（**排空那个有界队列**）
10. ⇒ **更大的队列在 50 时【逐字节惰性】**
11. ⇒ **因为它在每一个运行时性能样本里峰值都是 `8` 个里的 `7`**
12. ⇒ **移除那个人工预算现在匹配 CODOL 的命令循环**
13. ⇒ **并防止一个远端爆发带进之后的帧**
```

### 2.7 ⭐⭐⭐ **"一个我单独移动的耦合常数"**

**✅ 这是本文件里**最重要的一个"耦合常数"教训**。**

**⇒ 三层**：

```text
`SV_ChargeClientThinkTime` 的 100ms 预算是【配 Ghosts 的 tick 率】的
⇒ 而 50ms 帧 ⇒ **每 50ms 有 100ms 预算 ⇒ 2 倍余量**
⇒ 而 100ms 帧 ⇒ **恰好 1:1 ⇒ 零余量**
⇒ **⇒ 所以"改成 100"不是改一个数，是改成零余量**
```

**✅ 与 §384 的"一个编解码器不是一个类型"**同族（**第三次"一个数背后有语义"）。**

**⚠ 而"爆发无处可去"⇒ **一个极具体的机制**。**

**✅ **一个"余量"模型**。**

### 2.8 而**"更大的队列在 50 时逐字节惰性"**

**✅ 与 §349 的"32 个 actor 廉价"**同族（**第四次"成本/收益量化"）。**

**⇒ 三层**：

```text
`PendingUserCmdCapacity = 8 → 32`
⇒ **而在 50ms 帧上它峰值只有 7/8**
⇒ **⇒ 所以那个改动【完全无效】**
```

**✅ ⭐ **"逐字节惰性"** —— 一个**极强的负面**。**

**⚠ 而"7 of 8"⇒ **一个精确的峰值**。**

**✅ 与 §371 的"4,253 次全 `weapon=1137`"**同族（**第五次"100% 一致"）。**

### 2.9 而**`CL_WritePacket 0x005B2C10` 的 `MAX_PACKET_USERCMDS`**

**✅ ⭐ **一个从客户端代码读出的常数**。**

**⇒ 三层**：

```text
`MAX_PACKET_USERCMDS` = **32**
⇒ **从 `CL_WritePacket 0x005B2C10` 读出**
⇒ **所以 32 是【CODOL 自己的】而不是猜的**
```

**✅ 与 §370 的"去问键盘不要问镜像"**同族（**第五次"从真正的源读"）。**

## 三、**100ms 的完整实测（2026-09-06）**（本组第二重要）

### 3.1 那段

```php
// MEASURED AT 100 WITH BOTH MOVED, 2026-09-06, before the player was asked anything:
//
//   cadence       50 frames per 5 s window = 10.0/s   (retail's own 9.9/s)
//   pending       mean 6.7, MAX 19        -- against max EXACTLY 8 in the run that
//                                            felt bad, because 8 was the ceiling and
//                                            everything above it was being deleted
//   dropped       12, ALL of them inside the world-spawn stall, and ZERO since;
//                 earlier runs reached 1009
//   cmdAge        mean 168 ms, max 550 -- inside the 50 ms runs' own band of
//                 120..316 mean, whose max spikes were 9-12 SECONDS
//
// and only then: "this feels good compared to what i experienced last time. repeated
// movements left to right actually feel good and not like the same complaint."
//
// That is the same player and the same test that produced the complaint at the top of
// this comment. Retail's cadence also halves our snapshot rate, which is the whole of
// codol-a-match-dies-at-65536-packets: 110 minutes to the 16-bit wrap instead of 55.
```

### 3.2 十六层

```text
1. **在两个都移动后在 100 上测量，2026-09-06，在问玩家任何东西【之前】**
2. ⇒ **节拍：5 秒窗口里 50 帧 = `10.0/s`**（零售自己的 `9.9/s`）
3. ⇒ **`pending`：均值 `6.7`、最大 `19`**
4. ⇒ **对照那个"感觉坏"的运行里的最大【恰好 8】**
5. ⇒ **因为 `8` 是天花板而【8 以上的一切都在被删】**
6. ⇒ **`dropped`：`12`，【全部】在世界生成停摆之内，此后【零】**
7. ⇒ **更早的运行达到 `1009`**
8. ⇒ **`cmdAge`：均值 `168ms`、最大 `550`**
9. ⇒ **在 50ms 运行的【自己的带】`120..316` 均值之内**
10. ⇒ **而那些运行的【最大尖峰是 9–12 秒】**
11. ⇒ **而【只有那时】才问**："这比我上次体验的好。左右反复移动真的感觉好，不是同一个抱怨了。"
12. ⇒ **同一个玩家、同一个测试**
13. ⇒ **⇒ 而顶部那个抱怨就是它产生的**
14. ⇒ **零售的节拍还把我们快照率【减半】**
15. ⇒ **那正是 `codol-a-match-dies-at-65536-packets` 的全部**
16. ⇒ **`110` 分钟到 16 位回绕，而不是 `55`**
```

### 3.3 ⭐⭐ **"8 是天花板而 8 以上的一切都在被删"**

**✅ 与 §377 的"一个会消失的身体"**不同**（这是**静默删除输入**）。**

**⇒ 三层**：

```text
`pending = 8` 是【队列容量】
⇒ **而一次爆发需要 > 8**
⇒ **⇒ 多出来的【被丢弃】**
⇒ **⇒ 而玩家感觉是"猛推"**
```

**✅ ⭐ **"最大的 `pending` 恰好 8"⇒ **一个饱和的队列**。**

**⚠ 而"更早的运行达到 1009"⇒ **一个 126 倍的差异**。**

**✅ 与 §362 的 `145`、§384 的 `73/163`**同族（**第三次"极端对照"）。**

### 3.4 而**"`cmdAge` 均值 168 而最大 550，那些 50ms 运行的最大尖峰是 9–12 秒"**

**✅ 与 §355 的"前 40 帧"**同族（**第六次"最大尖峰 vs 均值"）。**

**⇒ 三层**：

```text
100ms 运行：`cmdAge` 均值 168 / 最大 550
 50ms 运行：`cmdAge` 均值 120..316 / **最大 9–12 秒**
⇒ **所以 100ms 的【最大】反而更好（550 vs 12000）**
```

**✅ ⭐ **一个反直觉的结论**（更慢的节拍有更好的最大延迟）。**

**⚠ 而"9–12 秒"⇒ **一个极端的卡顿**。**

**✅ 与 §374 的"`3000ms` 的帧"**同族（**第四次"秒级卡顿"）。**

### 3.5 而**"在两个都移动后…在问玩家任何东西之前"**

**✅ 与 §372 的"从一个不可能包含一个的样本得出结论"**相反**（这里**先测量后询问**）。**

**⇒ 三层**：

```text
顺序：**测量 → 然后问玩家**
⇒ **所以玩家的评价【不是】唯一证据**
⇒ **而是一个【确认】**
```

**✅ ⭐ **一个极严谨的实验顺序**。**

**⚠ 而"同一个玩家、同一个测试"⇒ **所以对照有效**。**

**✅ 与 §355 的"`OLMOD_SWAY_PHASE` 的算子调优"**同族（**第二次"同一玩家对照"）。**

## 四、**"为什么默认仍是 50"**（本组第三重要）

### 4.1 那段

```php
// SO WHY IS THE DEFAULT STILL 50? Because the suite encodes a 50 ms TIMELINE, not
// just the constant. Flipping the default was tried here and immediately failed three
// tests in a row -- the scheduler recursion guard, its residual drain, and the SD
// round-arming integration test -- because they advance a fixed number of
// onComFrame calls and assert a specific serverTime. Two of those are now scaled off
// SV_FrameMilliseconds() and are honest at any frame; the integration timelines are
// not, and patching them one failure at a time is how a test stops measuring the
// thing it names. That sweep is its own piece of work, deliberately not done in the
// middle of a live match.
//
// Until then 100 is a one-variable decision and it is fully measured:
//     OLMOD_SV_FRAME_MS=100   set INSIDE the elevated process that runs
//                             host-nuked.ps1, never in a caller of it.
```

### 4.2 十四层

```text
1. **那么为什么默认仍是 50？**
2. ⇒ **因为测试套件编码了一条【50ms 的时间线】，不只是那个常数**
3. ⇒ **翻转默认在这里被试过而【立刻连着失败三个测试】**：
      · **调度器的递归守卫**
      · **它的残余排空**
      · **SD 回合武装的集成测试**
4. ⇒ **因为它们推进【固定数量的 `onComFrame` 调用】并断言一个【具体的 `serverTime`】**
5. ⇒ **那两个现在已按 `SV_FrameMilliseconds()` 缩放而在任何帧上都诚实**
6. ⇒ **而【集成时间线不是】**
7. ⇒ **而【一次修一个失败】正是让测试【停止测量它所命名之物】的方式**
8. ⇒ **那个清扫是它自己的一块工作**
9. ⇒ **【故意】不在一个实机比赛的中途做**
10. ⇒ **在那之前 100 是一个【单变量决定】而它被【完整测量】了**
11. ⇒ **`OLMOD_SV_FRAME_MS=100` 设在【运行 `host-nuked.ps1` 的那个提权进程【之内】】
12. ⇒ **绝不在它的一个调用方里**
```

### 4.3 ⭐⭐ **"一次修一个失败正是让测试停止测量它所命名之物的方式"**

**✅ 这是本文件里**最深刻的测试哲学**。**

**⇒ 三层**：

```text
一个测试说"SD 回合武装"
⇒ **而它实际断言一个具体的 `serverTime`**
⇒ **所以修它到"通过"就是【让它不再测那件事】**
```

**✅ 与 §346 的"七十五项合取"**同族（**第六次"测试的名义 vs 实际"）。**

**⚠ 而"故意不在实机比赛的中途做"⇒ **一个精确的风险管理**。**

**✅ 与 §350 的"不要一般化这个例外"**同族（**第三次"故意不做"）。**

### 4.4 而**"设在运行 `host-nuked.ps1` 的那个提权进程【之内】，绝不在它的一个调用方里"**

**✅ 与 §371 的"`OLMOD_PLAYER_VOCALS`"**同族（**第八次环境变量旋钮）。**

**⚠ 而"之内 vs 调用方"⇒ **一个进程环境的精确性**。**

**⇒ 三层**：

```text
在调用方设置 ⇒ **可能不传播到提权进程**
⇒ **所以必须在【那个进程之内】设置**
```

**✅ 与 §354 的"`OLMOD_FACTORY_POWER_MOTION`"**配合。

## 五、**`SV_ClientThinkBudgetMilliseconds` 的默认 0**（本组第四重要）

```cpp
// CODOL has no separate think budget. The queue is hard-bounded at
// 32 commands, so drain the received burst this frame instead of
// carrying a high-ping player's input into another 100 ms frame.
return 0u;
```

### 5.1 五层

```text
1. **CODOL 没有独立的 think 预算**
2. ⇒ **队列硬界在 32 条命令**
3. ⇒ **所以【在这一帧里排空收到的爆发】**
4. ⇒ **而不是把高延迟玩家的输入带进另一个 100ms 帧**
5. ⇒ **所以默认 0**
```

**✅ ⭐ **"队列硬界在 32"⇒ **所以不需要时间预算**。**

**⇒ 三层**：

```text
有时间预算 ⇒ **速率限制**
有队列界 ⇒ **数量限制**
⇒ **CODOL 用【后者】**
```

**✅ 与 §391 的"`clients_(18, 30'000, ...)`"**同族（**一个显式界**）。

### 5.2 而**"0 是有意义的：没有预算，排空那个有界队列"**

```cpp
// 0 is meaningful: no budget, drain the bounded queue.
if (error == std::errc{} && pointer == last && parsed <= 10000) return parsed;
```

**✅ 与 §388 的"`from_chars` 必须消耗整个字符串"**同族（**第五次"严格解析"）。**

**⚠ 而"0 有意义"⇒ **所以不能把它当成"未设置"**。**

**✅ 与 §381 的"零速度是合法的"**同族（**第三次"零有语义"）。**

## 六、**`FixedFrameScheduler::advance` 的"每回调最多一个世界帧"**（本组第五重要）

```cpp
auto elapsed = nowMilliseconds - previousMilliseconds_;
previousMilliseconds_ = nowMilliseconds;
elapsed = std::min(elapsed, 500u);
residualMilliseconds_ += elapsed;
if (residualMilliseconds_ < frameMilliseconds_) return 0;
// CODREF(sv_frame): BO2 SV_FrameInternal 0x006F91C0 and Ghosts
// 0x1401FA4B0 fold all complete 50 ms residual slices into the target
// level time, then wake the server exactly once. BO1 0x007159E0 is the
// older branch that waits/runs once per residual slice in one call.
// CODDIFF(sv_frame): ol-mod currently has no independent server thread,
// so retain the residual but execute at most one complete world frame
// per host callback. This prevents a slow frame from recursively
// multiplying gameplay, native mirror and snapshot work while keeping
// every authoritative 50 ms step available to later callbacks.
residualMilliseconds_ -= frameMilliseconds_;
runFrame(frameMilliseconds_);
return 1;
```

### 6.1 十二层

```text
1. **`elapsed` 被 `min` 到 `500ms`**（**防一个巨大的暂停**）
2. ⇒ **加到 `residualMilliseconds_`**
3. ⇒ **不足一帧 ⇒ 返回 0**
4. ⇒ **`BO2 SV_FrameInternal 0x006F91C0` 与 `Ghosts 0x1401FA4B0` 把所有完整的 50ms 残余片折进目标 level time**
5. ⇒ **然后【精确地唤醒服务器一次】**
6. ⇒ **`BO1 0x007159E0` 是【更老的分支】**：在一次调用里等/跑每个残余片
7. ⇒ **ol-mod 当前【没有独立的服务器线程】**
8. ⇒ **所以保留残余但【每个宿主回调最多执行一个完整世界帧】**
9. ⇒ **这防止一个慢帧【递归地乘】gameplay、原生镜像与快照工作**
10. ⇒ **同时保持每一个权威的 50ms 步对之后的回调【可用】**
11. ⇒ **所以 `residualMilliseconds_ -= frameMilliseconds_`**（**只减一帧**）
12. ⇒ **而 `return 1`**（**只跑一个**）
```

### 6.2 ⭐ **"防止一个慢帧递归地乘"**

**✅ 与 §374 的"`3000ms` 的帧"**同族（**第五次"慢帧"）。**

**⇒ 三层**：

```text
若跑所有残余片 ⇒ **一个 500ms 的暂停 ⇒ 10 个世界帧**
⇒ **每个都要原生镜像 + 快照 ⇒ 更慢**
⇒ **⇒ 递归放大**
```

**✅ ⭐ **"保留残余但最多跑一个"** —— 一个**精确的折中**。**

**⚠ 而"残余保留"⇒ **所以之后会追上**。**

**✅ 与 §391 的"穿越判定让晚启动的时钟仍能宣告"**同族（**第二次"可追赶"）。**

### 6.3 而 **`elapsed = std::min(elapsed, 500u)`**

**⇒ 三层**：

```text
1. **一个巨大的 `elapsed`（如暂停）被夹到 500**
2. ⇒ **所以最多积累 500ms 的残余**
3. ⇒ **⇒ 最多 10 个 50ms 帧**
```

**✅ 与 §375 的"`clip.duration()` 的 `min`"**同族（**第三次"夹到上界"）。**

## 七、**`setEnabled` 的"这次转换擦掉每一个已连接客户端"**（本组第六重要）

```php
// THIS TRANSITION WIPES EVERY CONNECTED CLIENT -- clients_.reset() is thirteen lines
// below. A client that connected before it lands keeps sending on a slot that no longer
// exists, and the only symptom is "netchan packet has no connected client slot" with
// nothing to say the server threw the slot away. Say it.
OlMod::RuntimeLog::write(..., std::string("server enabled ") + (status_.enabled ? "true" : "false") +
    " -> " + (enabled ? "true" : "false") +
    "; RESETTING every connected client, connectedClients was " + std::to_string(status_.connectedClients));
```

### 7.1 八层

```text
1. **这次转换【擦掉每一个已连接客户端】**
2. ⇒ **`clients_.reset()` 在下面【十三行】**
3. ⇒ **一个在它落地【之前】连接的客户端继续在一个【不再存在的槽】上发送**
4. ⇒ **而唯一的症状是 `netchan packet has no connected client slot`**
5. ⇒ **而【没有任何东西说】服务器把那个槽扔掉了**
6. ⇒ **所以说它**
7. ⇒ **日志包含 `server enabled <old> -> <new>` 与 `connectedClients was N`**
```

**✅ 与 §368 的"命名失败项"**同族（**第七次）。**

**⚠ 而"十三行"⇒ **一个精确的距离**。**

**✅ 与 §377 的"两层之外"**同族。

### 7.2 而**`setEnabled` 的清空清单（约 90 项）**

**⇒ 三层**：

```text
`clients_.reset()` / `world_.reset()` / `scriptRuntime_.reset()`
+ **七个 hint 表**
+ **五个 battleChatter 表**
+ **九个 podium 标志**
+ **九个 SD 标志**
+ **...**
```

**⚠ 而 §349 的 `SvServerWorld::reset()` 有**六十八项**。**

**⇒ 所以**两层重置**（`ServerCore::setEnabled` + `SvServerWorld::reset`）。**

**✅ 一个**清晰的层次**。

### 7.3 而**"一场新比赛是一个新的宣告者"**

```php
// A NEW MATCH IS A NEW ANNOUNCER. Leaving matchStartSent set
// would make the second match of a session open in silence, and
// leaving `leader` set would suppress the first lead change.
announcer_ = {};
```

**⇒ 四层**：

```text
1. **一场新比赛是一个新的宣告者**
2. ⇒ **留着 `matchStartSent` ⇒ 一个会话的第二场比赛【静默开场】**
3. ⇒ **留着 `leader` ⇒ 压制第一次领先变化**
4. ⇒ **所以 `announcer_ = {}`**
```

**✅ 与 §391 的"`SV_UpdateMatchAnnouncer` 的 `matchStartSent`"**完全闭合 ✓

**⇒ **第二次确认那个状态。**

## 八、`onComFrame` 的七步

```text
1. `clients_.SV_CheckTimeouts(now)`
2. 若非 factoryEntryEnabled_ ⇒ `clients_.autoSelectMissingLoadouts(now)`
3. `scheduler_.advance(now, [this](ms) { runFrame(ms); })`
4. `clients_.SV_SendClientMessages(now)` ⇒ 每个用 `dtlsPeers_.NET_DtlsBuildData`
5. 更新十个 `status_` 字段
6. 返回 `outbound`
```

**⇒ 五步。**

### 8.1 而**"headless bring-up 的自动选职业"**

```php
// Headless bring-up: pick a class for anyone who has not, so a test cycle can
// reach a spawned player with nobody at the keyboard. No-op unless
// OLMOD_AUTO_LOADOUT=1; see SvClientSystem::autoSelectMissingLoadouts.
// OLMOD(factory-class-confirmation): the retail Factory join requests
// changeclass_marines before Playing. Never let the diagnostic automatic
// class pick bypass that confirmation, even if the host sets AUTO_LOADOUT.
if (!factoryEntryEnabled_)
    static_cast<void>(clients_.autoSelectMissingLoadouts(nowMilliseconds));
```

**⇒ 六层**：

```text
1. **无人值守的 bring-up：给任何还没选的人挑一个职业**
2. ⇒ **所以一个测试周期能在【没人在键盘旁】的情况下到达一个已出生的玩家**
3. ⇒ **除非 `OLMOD_AUTO_LOADOUT=1` 否则 no-op**
4. ⇒ **零售的 Factory 加入在 Playing 之前请求 `changeclass_marines`**
5. ⇒ **绝不让那个诊断性的自动职业选择【绕过那个确认】**
6. ⇒ **即使宿主设了 `AUTO_LOADOUT`**
```

**✅ 与 §391 的"机制好而时机错"**同族（**第二次"机制 vs 时机"）。**

**⚠ 而"`changeclass_marines`"⇒ **一个具体的脚本请求名**。**

**✅ 与 §391 的"`无法加入游戏会话`"**配合。

## 九、关键结论

1. **⭐⭐ "50 仍然是默认，而 100 已被证明"`** —— 零售 **`6160/621.4 = 9.9/s`** vs 我们 **`19.9/s`**，**恰好两倍**，**也是 55 分钟死在 16 位序列上的全部原因**。
2. **⭐ "它被试过实机而玩家立刻感觉到了：移动感觉快一些，但不那么平滑，它把我猛推了"`** —— 而日志给了 `pending=8 cmdAge=143..155`。
3. **⭐⭐ "原因是【一个我单独移动的耦合常数】"`** —— `SV_ChargeClientThinkTime` 的 **100ms 预算**在 50ms 帧上是 **2 倍余量**、在 100ms 帧上是**恰好实时零余量** ⇒ **爆发无处可去**。
4. **"所以帧间隔与 think 预算是【一个决定，不是两个】"`**。
5. **两个耦合常数**：`PendingUserCmdCapacity 8→32`（**从 `CL_WritePacket 0x005B2C10` 读出的 `MAX_PACKET_USERCMDS`**）+ `SV_ClientThinkBudgetMilliseconds → 0`。
6. **⭐ "更大的队列在 50 时【逐字节惰性】，因为它在每一个运行时性能样本里峰值都是 8 个里的 7"`** —— 一个极强的负面。
7. **⭐⭐ 100ms 的完整实测**：`cadence 10.0/s` / `pending 均值 6.7 最大 19`（**对照"感觉坏"的运行里最大恰好 8，因为 8 是天花板而 8 以上的一切都在被删**）/ `dropped 12 全在生成停摆内`（**早前 1009**）/ `cmdAge 均值 168 最大 550`（**而 50ms 运行的最大尖峰是 9–12 秒**）。
8. **"在两个都移动后…【在问玩家任何东西之前】"`** —— 一个极严谨的实验顺序。
9. **⭐ "而只有那时才问：这比我上次体验的好"`** —— **同一个玩家、同一个测试**。
10. **⭐⭐ "为什么默认仍是 50？因为测试套件编码了一条 50ms 的【时间线】，不只是那个常数"`** —— 而 **"一次修一个失败正是让测试【停止测量它所命名之物】的方式"`**。
11. **"那个清扫是它自己的一块工作，故意不在一个实机比赛的中途做"`** —— 第三次"故意不做"。
12. **"`OLMOD_SV_FRAME_MS=100` 设在运行 `host-nuked.ps1` 的那个提权进程【之内】，绝不在它的一个调用方里"`** —— 第八次环境变量旋钮，而**进程环境传播的精确性**。
13. **⭐ `SV_ClientThinkBudgetMilliseconds` 的默认 0** —— **"CODOL 没有独立的 think 预算；队列硬界在 32 条命令，所以在这一帧里排空收到的爆发"`**。
14. **"0 是有意义的"`** —— 第三次"零有语义"。
15. **⭐ `FixedFrameScheduler::advance` 的"最多一个世界帧"`** —— 而 **"保留残余但最多跑一个"**：**"防止一个慢帧递归地乘 gameplay、原生镜像与快照工作，同时保持每一个权威的 50ms 步对之后的回调可用"`**。
16. **`elapsed = min(elapsed, 500u)`** —— 第三次"夹到上界"。
17. **⭐ `setEnabled` 的"这次转换擦掉每一个已连接客户端"`** —— `clients_.reset()` **在十三行之后**，而**唯一症状是 `netchan packet has no connected client slot`**（**没有任何东西说服务器把槽扔掉了**）。
18. **两层重置**（`ServerCore::setEnabled` 约 90 项 + `SvServerWorld::reset` 六十八项）。
19. **"一场新比赛是一个新的宣告者：留着 `matchStartSent` 会让一个会话的第二场比赛静默开场"`** —— 第二次确认那个状态。
20. **"headless bring-up 的自动选职业：绝不让那个诊断性选择绕过 `factoryEntryEnabled_` 的确认，因为零售的 Factory 加入在 Playing 之前请求 `changeclass_marines`"`** —— 第二次"机制 vs 时机"。

## 十、未闭合点

- `codol-a-match-dies-at-65536-packets` 的完整分析。
- `host-nuked.ps1` 的位置。
- `PendingUserCmdCapacity` 的当前值（32）。
- `SvClientSystem::autoSelectMissingLoadouts` 的实现。
- 那三个失败的测试名。
- `sv_main_mp.cpp` 1350 行之后未读取。
