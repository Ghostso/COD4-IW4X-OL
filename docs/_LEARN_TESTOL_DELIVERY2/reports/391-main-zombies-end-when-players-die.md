# 391 · **"僵尸在玩家死时结束，不在一个计时器上"** —— `600000ms` 的 `timeLimit` 把每一场干净会话都推到 10:51、`remaining == 30000` 在 50ms 帧上永不触发

## 一、范围

本报告学习 `sv_main_mp.cpp` 650–1000 行。

## 二、**ZM 的 10 分钟"比赛完成"完整事故**（本组最重要的一段）

### 2.1 那段

```php
// SD owns a fresh timer for every round. Treating scr_sd_timelimit as
// this match-level limit prevents all later rounds from completing.
// ZM HAS NO MATCH CLOCK AT ALL, and the booking hands zombies the MP
// limits anyway. MEASURED, every full-length zm session in
// CodolGameServer.log:
//
//   match complete gametype=zm reason=timeLimit elapsed=600000ms
//       limitMinutes=10 scoreLimit=30 best=client0:0
//   ui screen podium ui -> s ui_match_complete "1"
//   match ended gametype=zm t="EXE_MATCHENDED"
//   client timeout client=0
//
// This fired at exactly ten minutes of match clock, pushed the podium,
// and left the player on the end-of-match screen waiting for a round
// that never comes -- join-to-drop 10:51 (600s of clock plus the
// pre-match load) on EVERY clean session going back to the oldest one
// in the log, with the client's packet counter frozen from that
// moment. Zombies ends when the players die, not on a timer.
//
// The limits cannot be zeroed at the booking instead:
// DedicatedSession::valid rejects rules carrying no limits and the
// whole booking is refused. Gating the evaluator also leaves
// ui_timelimit and the gamestate fixture byte-identical, which zeroing
// the rules would not.
if (!status.configured || status.completed || gameType == "sd" ||
    gameType == "zm" || !status.startServerTime ||
    !status.rules.timeLimitMinutes)
{
    return false;
}
```

### 2.2 二十二层

```text
1. **SD 每回合拥有一个【新的计时器】**
2. ⇒ **把 `scr_sd_timelimit` 当作这个比赛级的限制让之后所有回合都不能完成**
3. ⇒ **ZM 【根本没有比赛时钟】**
4. ⇒ **而预约（booking）【还是】给僵尸 MP 的限制**
5. ⇒ **测量：`CodolGameServer.log` 里每一场满长的 zm 会话**：
     · `match complete gametype=zm reason=timeLimit elapsed=600000ms`
     · `limitMinutes=10 scoreLimit=30 best=client0:0`
     · `ui screen podium ui -> s ui_match_complete "1"`
     · `match ended gametype=zm t="EXE_MATCHENDED"`
     · `client timeout client=0`
6. ⇒ **它在【恰好十分钟】的比赛时钟上触发**
7. ⇒ **推了 podium**
8. ⇒ **而把玩家留在结束屏，等一个【永不到来】的回合**
9. ⇒ **⇒ join-to-drop `10:51`**（600 秒时钟 + 赛前加载）
10. ⇒ **在【每一场干净会话】上，一直回溯到日志里最老的那一场**
11. ⇒ **而客户端的包计数器【从那一刻起冻结】**
12. ⇒ **僵尸在【玩家死时】结束，不在一个计时器上**
13. ⇒ **限制【不能】在预约处清零**：
      · **`DedicatedSession::valid` 拒绝没有限制的规则**
      · **而整个预约会被拒**
14. ⇒ **门控评估器还让 `ui_timelimit` 与 gamestate fixture 【逐字节相同】**
15. ⇒ **而清零规则不会**（那会改变它）
16. ⇒ **所以门控在【这里】**
```

### 2.3 ⭐⭐ **"僵尸在玩家死时结束，不在一个计时器上"**

**✅ 这是本文件里**对"游戏设计意图"最清晰的一句**。**

**⇒ 三层**：

```text
ZM 的设计：**在玩家死时结束**
而代码：**10 分钟的 timeLimit**
⇒ **⇒ 每一场都在 10:51 被踢**
```

**✅ 与 §360 的"`21` 被试过并被回退"**不同**（那里是**技术错误**，这里是**设计错误**）。**

**⚠ 而"每一场干净会话"⇒ **100% 的复现率**。**

**✅ 与 §371 的"4,253 次拒绝"**同族（**第四次"100% 复现"）。**

### 2.4 而**"客户端的包计数器从那一刻起冻结"**

**✅ 与 §347 的"`cacheAcked=0` 永远"、§377 的"永远 FULL"**同族（**第五次"ack 链断裂"）。**

**⇒ 三层**：

```text
比赛完成 ⇒ **podium 屏**
⇒ **而客户端等一个永不到来的回合**
⇒ **⇒ 包计数器冻结**
⇒ **⇒ 超时**
```

**✅ 与 §368 的"`ack` 冻在 11"**同族（**第六次）。**

### 2.5 而**"限制不能在预约处清零"**

**✅ 与 §349 的"没有空槽 ⇒ 拒绝生成"**同族（**一个"输入验证的必然性"）。**

**⇒ 三层**：

```text
想：把 `timeLimitMinutes` 设为 0 ⇒ **`DedicatedSession::valid` 拒绝整个预约**
⇒ 想：门控评估器 ⇒ **但会改变 `ui_timelimit` 与 gamestate fixture**
⇒ **⇒ 所以只在【这个函数】里门控**
```

**✅ ⭐ **"门控评估器还让 `ui_timelimit` 与 gamestate fixture 逐字节相同，而清零规则不会"** —— 一个**极精细的向后兼容考量**。**

**✅ 与 §337 的"与 `8584acf` 逐字节兼容"**同族（**第三次"逐字节兼容"）。**

### 2.6 而 `gameType == "sd"` 的同一个门

**✅ 与 §352 的"`roundBasedDeathHold_ = (gameType == "sd")`"**完全闭合 ✓

**⇒ **第二次确认 SD 的回合所有权。**

## 三、**`remaining == 30000` 在 50ms 帧上永不触发**（本组第二重要）

### 3.1 那段

```php
if (!state.timesUpSent && status.rules.timeLimitMinutes) {
    const auto limit = (uint64)status.rules.timeLimitMinutes * 60u * 1000u;
    // NOT `remaining == 30000`. A frame is 50 ms and the clock is
    // sampled, so an equality test fires on no frame at all in most
    // matches - the countdown is due once the remaining time has
    // FALLEN THROUGH the mark, which is also what makes a late-starting
    // clock or a paused frame still announce.
    if (elapsed + SvAnnouncerTimesUpRemainingMs >= limit) {
        state.timesUpSent = true;
        cues.timesUp = true;
    }
}
```

### 3.2 十层

```text
1. **不是 `remaining == 30000`**
2. ⇒ **一帧是 `50ms` 而时钟是【采样的】**
3. ⇒ **所以一个相等测试在【大多数比赛里一帧都不触发】**
4. ⇒ **倒计时在剩余时间【跌穿】那个标记时到期**
5. ⇒ **那也正是让一个【晚启动的时钟】或一个【暂停的帧】仍能宣告的东西**
6. ⇒ **所以 `elapsed + remaining >= limit`**（穿越判定）
```

### 3.3 ⭐ **"一个相等测试在大多数比赛里一帧都不触发"**

**✅ 与 §388 的"`from_chars` 必须消耗整个字符串"**不同**（这是**采样与相等的冲突**）。**

**⇒ 三层**：

```text
时钟以 50ms 采样
⇒ **而 `remaining == 30000` 要求恰好命中**
⇒ **⇒ 若 `elapsed` 跳过 30000 ⇒ 永不触发**
```

**✅ 与 §372 的"`player-kinematics` 的 1Hz 采样看不见 20Hz 的翻转"**完全同族（**第二次"采样率 vs 事件率"）。**

**⚠ 而"晚启动的时钟或暂停的帧仍能宣告"⇒ **穿越判定还给出【可恢复性】**。**

**✅ 一个**双重好处**。

## 四、**SD 的七个阶段函数**（本组第三重要）

### 4.1 七个

```text
SV_BeginSdBombRound       ⇒ Inactive → Available
SV_PickUpSdBomb           ⇒ Available/Dropped → Carried
SV_DropSdBomb             ⇒ Carried → Dropped
SV_CommitSdBombPlant      ⇒ Carried → Planted
SV_CommitSdBombDefuse     ⇒ Planted → Defused
SV_AdvanceSdBombTimer     ⇒ Planted → Exploded
```

**⇒ 六个（含两个终点）。**

### 4.2 而**五个阶段的完整状态机**

```text
Inactive
  ↓ SV_BeginSdBombRound
Available
  ↓ SV_PickUpSdBomb
Carried
  ↓ SV_DropSdBomb        ↓ SV_CommitSdBombPlant
Dropped                  Planted
  ↓ SV_PickUpSdBomb        ↓ SV_AdvanceSdBombTimer  ↓ SV_CommitSdBombDefuse
Carried                  Exploded                  Defused
```

**✅ ⭐ 一个**带回路的状态机**（`Dropped → Carried`）。**

**⚠ 而"`Exploded` / `Defused`"是两个终点。**

**✅ 与 §349 的"四十个 think 阶段"**不同（这是**一个游戏状态机**）。

### 4.3 而**每个函数的"时间单调"检查**

```php
serverTime < status.phaseStartServerTime
```

**⇒ 五个函数里【都有】。**

**✅ 与 §345 的"`serverTime` 倒退 ⇒ 新代际"**不同**（这里**拒绝倒退**）。**

**⇒ 三层**：

```text
§345  倒退 ⇒ **新代际**（清空/重建）
§391  倒退 ⇒ **拒绝操作**
```

**✅ 一个**精确的区分**（一个是时间源重置，一个是非法输入）。

### 4.4 而**`SV_AdvanceSdBombTimer` 的四个前置**

```php
if (!status.configured || status.phase != Planted ||
    !rules.bombMilliseconds || serverTime < status.plantedServerTime ||
    serverTime - status.plantedServerTime < rules.bombMilliseconds)
    return false;
```

**⇒ 四层 + 一个穿越判定。**

**✅ 与 §391 三 的"穿越判定"**完全同族（**第二次）。**

## 五、**`SV_EvaluateSdElimination` 的四种结果**（本组第四重要）

### 5.1 那段

```php
if (!state.attackers || !state.defenders) return std::nullopt;
if (!state.attackersAlive && !state.defendersAlive) {
    return std::pair{ state.bombPlanted ? SvTeam::Tf : SvTeam::Sc, SvSdRoundEndReason::SimultaneousElimination };
}
if (!state.attackersAlive && !state.bombPlanted) {
    return std::pair{ SvTeam::Sc, SvSdRoundEndReason::AttackersEliminated };
}
if (!state.defendersAlive) {
    return std::pair{ SvTeam::Tf, SvSdRoundEndReason::DefendersEliminated };
}
return std::nullopt;
```

### 5.2 七层

```text
1. **双方都灭 ⇒ 【同时消灭】**
2. ⇒ **而赢家是 `bombPlanted ? Tf : Sc`** ⇒ **因为炸弹已下时攻方仍可赢**
3. ⇒ **攻方灭而【未下包】⇒ 守方赢**
4. ⇒ **守方灭 ⇒ 攻方赢**
5. ⇒ **而【攻方灭但已下包】⇒ 没有结果**（等炸弹）
```

**✅ ⭐ **"攻方全灭但炸弹已下"⇒ 只返回 `nullopt`** —— 一个**正确的游戏规则**。**

**⇒ 三层**：

```text
若攻方全灭而【已下包】
⇒ **炸弹仍在计时 ⇒ 攻方仍可能赢**
⇒ **⇒ 所以不能判守方赢**
```

**✅ 与 §391 四.2 的状态机**完全闭合 ✓

**⚠ 而"同时消灭"⇒ 所以**`bombPlanted` 决定赢家**。**

**✅ 一个**精确的规则**。

## 六、**`SV_EvaluateSdTimeLimit` 的"下包暂停计时"**

```php
// CODREF(sd_round_timer): IW4 sd.gsc and Ghosts sd.gsc both route the
// mode timer through onTimeLimit. Planting pauses that timer and uses
// the bomb end time instead, so this is round policy, not match policy.
if (!startedServerTime || !timeLimitMinutes || state.bombPlanted ||
    currentServerTime < startedServerTime) return std::nullopt;
```

**⇒ 六层**：

```text
1. **IW4 `sd.gsc` 与 Ghosts `sd.gsc` 都把模式计时器路由到 `onTimeLimit`**
2. ⇒ **下包【暂停】那个计时器**
3. ⇒ **并改用炸弹结束时间**
4. ⇒ **所以这是【回合策略】不是比赛策略**
5. ⇒ 所以 `state.bombPlanted ⇒ return nullopt`
```

**✅ 与 §391 二 的"SD 每回合拥有一个新的计时器"**完全闭合 ✓

**⇒ **第三次确认那个回合所有权。**

## 七、**九种 `SvSdRoundEndReason`**

```text
BombDefused             ⇒ Sc 赢
BombExploded            ⇒ Tf 赢
SimultaneousElimination ⇒ bombPlanted ? Tf : Sc
AttackersEliminated     ⇒ Sc 赢
DefendersEliminated     ⇒ Tf 赢
TimeLimit               ⇒ Sc 赢
```

**⇒ 六种（含两个炸弹结果）。**

**✅ 与 §348 的"十五种写失败"、§349 的"四十个 think 阶段"**同族（**第五个枚举 + 名字**）。**

## 八、**`ServerCore` 的构造与十个注入**（本组第五重要）

### 8.1 十个注入

```cpp
scriptBuiltins_(world_, {
    .addClientScore,
    .addClientXp,
    .addTeamScoreForClient,
    .addKillForClient,
    .addDeathForClient,      // ★★ 28100 刀AB
    .addAssistForClient,     // ★★ 28100 刀AB
    .playSoundForClient,     // ★ 刀BP
    .isBotClient,            // 28800
})
```

**⇒ 八个（`scriptBuiltins_` 的）。**

### 8.2 而 `clients_(18, 30'000, ...)`

```cpp
clients_(18, 30'000, std::move(gameStateBuilder), std::move(snapshotBuilder))
```

**⇒ 三层**：

```text
1. **`18` 个客户端槽**
2. ⇒ **`30'000ms` 的超时**（30 秒）
3. ⇒ 与 §346 的"`MaximumGameClients`"**配合**
```

**✅ 与 §370 的"`killerClientNum > 255`"**不同（那是**8 位域**）。**

**⚠ 而"`18`"⇒ 与 §345 的"`MaximumGameClients`"**同值**。**

**✅ **第二次确认 18。**

### 8.3 而**"不是在这里包装发布模型 configstring"**

```php
// NOT WRAPPED TO PUBLISH THE MODEL CONFIGSTRING HERE. That was tried
// and it BROKE JOINING: publishing cs 2876 at first-zombie-spawn time
// (plus its `|` precache) left the client unable to enter --
// 无法加入游戏会话, "unable to join game session", reproduced twice.
// publishActorModelConfigString still exists and works (the log shows
// `actor model PUBLISHED index=308 cs=2876 name=c_zom_ger_body1`), so
// the mechanism is fine and the TIMING is what is wrong: retail carries
// its model band IN THE GAMESTATE -- Appmain's brushmodel census notes
// retail zm_factory_sh sending 34 of them at cs 2979/2980 and
// 2995..3026 -- i.e. before any client connects, not mid-session.
// See re/demo-re/20-zm-actor-lifecycle.md 12.21.
```

### 8.4 十六层

```text
1. **不是在这里包装以发布模型 configstring**
2. ⇒ **那被试过而它【破坏了加入】**
3. ⇒ **在第一个僵尸生成时发布 `cs 2876`**（加上它的 `|` precache）
4. ⇒ **让客户端【无法进入】**
5. ⇒ **`无法加入游戏会话` / `unable to join game session`，复现【两次】**
6. ⇒ **`publishActorModelConfigString` 【仍然】存在并工作**
7. ⇒ **（日志显示 `actor model PUBLISHED index=308 cs=2876 name=c_zom_ger_body1`）**
8. ⇒ **所以那个机制是好的而【时机】是错的**
9. ⇒ **零售把它的模型带【放在 gamestate 里】**
10. ⇒ **Appmain 的 brushmodel 普查记录零售 `zm_factory_sh` 发了 `34` 个**
11. ⇒ **在 `cs 2979/2980` 与 `2995..3026`**
12. ⇒ **即在【任何客户端连接之前】，不是会话中途**
13. ⇒ **（`re/demo-re/20-zm-actor-lifecycle.md` 12.21）**
```

### 8.5 ⭐⭐ **"机制是好的而时机是错的"**

**✅ 与 §350 的"`ET_SCRIPTMOVER` 而不是 `ET_GENERAL`"**不同**（那是**机制错**，这是**时机错**）。**

**⇒ 三层**：

```text
机制：`publishActorModelConfigString` ✓（日志证明）
时机：**会话中途** ✗
⇒ **⇒ 客户端在【已经建立了 configstring 基线之后】收到一个新的 ⇒ 拒绝**
```

**✅ 与 §368 的"`constBaselines` 的 XOR 抵消"**同族（**第八次"协议时序依赖"）。**

**⚠ 而"`34` 个在 `cs 2979/2980` 与 `2995..3026`"⇒ **一个具体的分布**。**

**✅ 与 §350 的"373 个 `ET_SCRIPTMOVER`"**不同（这是 **34 个模型带条目**）。

**⇒ 而"`2979/2980`（2 个）+ `2995..3026`（32 个）= 34** ✓**

**✅ **一个精确的算术闭合。**

## 九、`isBotClient` 的"从网络槽直接读"

```php
// 28800: method:isbot -- the kill-effect tables are keyed on the
// killing weapon, so without this a bot kill played a player's
// cosmetic death effect. Read straight off the network slot.
.isBotClient = [this](const std::uint32_t clientNum) {
    const auto &slots = clients_.clients();
    return clientNum < slots.size() && slots[clientNum].isBot;
},
```

**⇒ 五层**：

```text
1. **`method:isbot`**
2. ⇒ **击杀效果表按击杀武器键**
3. ⇒ **没有这个，一次 bot 击杀播放了一个【玩家的】外观死亡效果**
4. ⇒ **直接从网络槽读**
5. ⇒ **所以是一个纯读取**
```

**✅ 与 §312 的"`>=` 误把人类当 bot"**完全同族（**第二次"bot 识别"）。**

**⇒ 而这里用 `slots[clientNum].isBot` ⇒ **一个显式的标志**。**

**✅ 与 §312 的"real xuid ≈1.67e19 vs bot base 7.95e17，21× 更大"**不同（那是**范围推断**）。**

**⇒ **两个不同的 bot 判定**。**

## 十、关键结论

1. **⭐⭐ "僵尸在【玩家死时】结束，不在一个计时器上"`** —— 而 `timeLimit` 在**恰好十分钟**触发，把每一场干净会话推到 **`10:51`**，**客户端的包计数器从那一刻起冻结**。
2. **五条完整日志**（`match complete gametype=zm reason=timeLimit elapsed=600000ms` / `podium` / `match ended` / `client timeout`）。
3. **"限制不能在预约处清零：`DedicatedSession::valid` 拒绝没有限制的规则而整个预约会被拒"`** —— 一个输入验证的必然性。
4. **⭐ "门控评估器还让 `ui_timelimit` 与 gamestate fixture 逐字节相同，而清零规则不会"`** —— 第三次"逐字节兼容"。
5. **⭐⭐ "不是 `remaining == 30000`：一帧是 50ms 而时钟是采样的，所以一个相等测试在大多数比赛里一帧都不触发"`** —— 第二次"采样率 vs 事件率"，而**穿越判定还给出可恢复性**。
6. **⭐ SD 的六个阶段函数构成一个带回路的状态机**（`Dropped → Carried`），而**每个都有"时间单调"检查**（与 §345 的"倒退 ⇒ 新代际"**相反**，这里**拒绝倒退**）。
7. **⭐⭐ "攻方全灭而【已下包】⇒ 没有结果（等炸弹）"`** —— 一个正确的游戏规则，与状态机**完全闭合**。
8. **"同时消灭"的赢家是 `bombPlanted ? Tf : Sc`**。
9. **"下包【暂停】那个计时器并改用炸弹结束时间，所以这是【回合策略】不是比赛策略"`** —— 第三次确认 SD 的回合所有权。
10. **六种 `SvSdRoundEndReason`** 与**六种结果映射** —— 第五个"枚举 + 名字"。
11. **`clients_(18, 30'000, ...)`** —— **18 个客户端槽**（第二次确认 `MaximumGameClients`）+ **30 秒超时**。
12. **⭐ `scriptBuiltins_` 的八个注入**（含两个 `★ 28100 刀AB` 的 `addDeathForClient`/`addAssistForClient` 与 `★ 刀BP` 的 `playSoundForClient`）。
13. **⭐⭐ "机制是好的而【时机】是错的"`** —— `publishActorModelConfigString` 在**会话中途**发布 `cs 2876` ⇒ **`unable to join game session`，复现两次**。
14. **"零售把它的模型带【放在 gamestate 里】：`zm_factory_sh` 发 `34` 个在 `cs 2979/2980` 与 `2995..3026`，即在任何客户端连接之前"`** —— 而 **`2 + 32 = 34`** 一个精确的算术闭合。
15. **`isBotClient` 直接读 `slots[clientNum].isBot`** —— 与 §312 的"xuid 范围推断"**两个不同的 bot 判定**。

## 十一、未闭合点

- `DedicatedSession::valid` 的完整条件。
- `ui_timelimit` 与 gamestate fixture 的字节布局。
- `SvSdRoundEndReason` 的完整枚举。
- `SvAnnouncerTimesUpRemainingMs` 的值（30000？）。
- `publishActorModelConfigString` 的实现。
- `sv_main_mp.cpp` 1000 行之后未读取。
