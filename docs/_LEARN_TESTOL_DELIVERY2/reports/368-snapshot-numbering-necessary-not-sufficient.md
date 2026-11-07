# 368 · **"正确的编号是 bit `0x10` 的【必要】而非【充分】条件"** —— `0xFFFFFF ^ 0 = 0`、`N ^ N = 0`、三次武装三次失败、三层"命名失败项"

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 18800–19200 行。

## 二、**`constBaselines` 与 `useEntityBaselines` 必须一起动**（本组最重要的一段）

### 2.1 那段

```php
// NOT `constBaselineNumbering_`. Correct numbering is NECESSARY for bit 0x10 and it
// is NOT SUFFICIENT -- the flag also requires the server to compute its deltas
// against the SAME baseline the client will resolve against, and this one still
// deltas against zero.
//
// Every field goes on the wire as `value ^ baseline` (writeUnsignedDelta). With the
// flag set and the numbering right, a brush model's solid was sent as
// 0xFFFFFF ^ 0 and the client XORed it against its own baseline for that entity --
// which is 0xFFFFFF -- giving 0. The brush model index cancelled the same way,
// N ^ N. The entity arrived with no solid and no model and was not drawn: the more
// exactly the numbering matched, the more exactly the values cancelled.
//
// So the two move together, always: the table the writers delta against IS the table
// the flag tells the client to resolve against. Null table, no flag.
//
// Armed on 2026-08-31, disarmed the same hour, and armed again only after reading
// the client. The first arming sent the client to a black screen: an entity that
// matched its baseline in every field was written as "changed" with no fields, and
// MSG_ReadDeltaEntity (sub_671170) reads a three-bit skip index UNCONDITIONALLY
// after lastChangedField, so it consumed the next entity's number instead and every
// bit after that was misaligned.
//
// The encoding for "identical to the baseline" is the reader's SECOND bit -- 0
// means "take the baseline verbatim" -- and SV_WritePacketEntities now emits it for
// a const baseline exactly as it always has for a previous-snapshot one. The writer
// additionally refuses to emit a fieldless "changed" entity at all, so the desync
// cannot come back silently.
snapshot_.constBaselines = constBaselineTable_;
snapshot_.useEntityBaselines = constBaselineTable_ != nullptr;
```

### 2.2 二十四层

```text
1. **不是 `constBaselineNumbering_`**
2. ⇒ **正确的编号对 bit `0x10` 是【必要】的而【不充分】**
3. ⇒ **那个标志还要求服务器对着【客户端将解析的那个同一基线】计算它的 delta**
4. ⇒ **而这一个仍对着【零】做 delta**
5. ⇒ **每个字段以 `value ^ baseline` 上线**（`writeUnsignedDelta`）
6. ⇒ **标志设了而编号对了** ⇒ **一个画笔模型的 solid 被发成 `0xFFFFFF ^ 0`**
7. ⇒ **而客户端把它对它自己那个实体的基线 XOR —— 那是 `0xFFFFFF`**
8. ⇒ **得 0**
9. ⇒ **画笔模型索引以同样方式抵消：`N ^ N`**
10. ⇒ **实体到达时没有 solid 也没有模型而【不被画】**
11. ⇒ **编号越精确地匹配，值就越精确地抵消**
12. ⇒ **所以两者永远一起动：写入器 delta 的表【就是】那个标志告诉客户端去解析的表**
13. ⇒ **空表，无标志**
14. ⇒ **2026-08-31 武装，同一小时解除，只在【读了客户端之后】再次武装**
15. ⇒ **第一次武装把客户端送到黑屏**
16. ⇒ **一个在每个字段上都匹配它基线的实体被写成"变了"而【没有字段】**
17. ⇒ **而 `MSG_ReadDeltaEntity`（`sub_671170`）在 `lastChangedField` 之后【无条件】读一个三位跳号索引**
18. ⇒ **所以它反而消费了下一个实体的编号**
19. ⇒ **而之后的每一位都错位**
20. ⇒ **"与基线相同"的编码是读者的【第二位】—— 0 意思是"逐字取基线"**
21. ⇒ **而 `SV_WritePacketEntities` 现在为 const 基线发出它，正如它对前快照基线一直做的**
22. ⇒ **写入器还【拒绝】发出一个无字段的"变了"实体**
23. ⇒ **所以那个失步不能静默地回来**
```

### 2.3 ⭐⭐ **"编号越精确地匹配，值就越精确地抵消"**

**✅ 这是本文件里**最反直觉的一条**。**

**⇒ 三层**：

```text
前提：标志说"客户端用 const 表解析"
     ⇒ 客户端用 `const[n]` 做基线
     ⇒ **而我们发 `value ^ 0`（对零 delta）**
     ⇒ 客户端算 `const[n] ^ (value ^ 0) = const[n] ^ value`
     ⇒ **当 `value == const[n]` 时 ⇒ 得 0**
```

**✅ 所以**越对越错**。**

**⚠ 一个**极端反直觉的失败模式**。**

**⇒ 与 §351 的"槽 0 不是失败而是规则"**同族（**"正确"反而是错的**）。**

### 2.4 而**两个具体的抵消**

```text
solid              0xFFFFFF ^ 0 = 0xFFFFFF     ⇒ 客户端 XOR 自己的 0xFFFFFF ⇒ 0
brushModelIndex    N ^ 0 = N                   ⇒ 客户端 XOR 自己的 N        ⇒ 0
```

**⇒ 三层**：

```text
1. **两个字段都精确抵消**
2. ⇒ **所以实体到达时"没有 solid 也没有模型"**
3. ⇒ **所以不被画**
```

**✅ 与 §350 的"门不可见"**同族（**第五次"不画"**）。

**⚠ 而这里的原因**完全不同**（XOR 抵消 vs 缺画笔分支）。**

**✅ 与 §367 的"两次 eType 迁移两次事故"**同族（**第三次"同一个症状不同原因"**）。

**⇒ **"不画"的五个原因**：**

```text
§322  allowlist 丢 eType
§343  126/132 个 scriptmodel 不写坐标（位置错而非不画）
§350  ET_GENERAL 没有画笔分支
§361  空资源 ⇒ 无骨骼
§368  const 基线 XOR 抵消
§367  eType 别名 ⇒ 零快照
```

**⇒ **六个**。

### 2.5 而**"三次武装三次失败"**

```text
第一次  2026-08-31 武装 ⇒ 黑屏（无字段"变了"实体）
        同一小时解除
第二次  （隐含，§350 的 +3 问题）⇒ 控制台成了僵尸身体
第三次  读客户端之后 ⇒ 成功
```

**✅ 与 §362 的"两个极端都试过"**同族（**第三次"多次尝试"**）。

**⚠ 而"只在读了客户端之后再次武装"⇒ **一个明确的教训**：**

```text
不要靠推理 ⇒ 要读客户端
```

**✅ 与 §360 的"崩溃说 `demoq` 是对的"、§363 的"the traffic wins"**第六次"实测优先"。

### 2.6 而**"无字段的『变了』实体"的三位**

**✅ 与 §345 的"(0,0) 是未变而"变化但无字段"不可编码"**完全一致 ✓

**⇒ **第二次确认那个核心事实。**

**⚠ 而 §345 的注释说"2026-08-31 黑屏"。**

**⇒ 所以**§345 与 §368 记录的是**同一次事故**。**

**✅ **第三次交叉引用同一事故**（§345、§347、§368）。

### 2.7 而**"写入器拒绝发出一个无字段的『变了』实体"**

**✅ 与 §343 的"一个没什么可说的实体绝不能走这条路"**完全一致 ✓

**⇒ **第二次确认那个守卫。**

**✅ 一个**双保险**（写入器拒绝 + 编码 `(0,0)`）。

## 三、**`beginFrame` 的帧序列（十二步）**（本组第二重要）

```text
1.  auto previousSnapshot = std::move(snapshot_);  snapshot_ = {};
2.  snapshot_.serverTime = previousSnapshot.serverTime + frameMilliseconds;
3.  snapshot_.emitPlayersInActorsSection = !zmActorNamespaceEnabled_;
4.  stepZmBarrierMotions();
5.  stepFactoryDoorMotions();
6.  stepFactoryPowerMotions();
7.  stepActorEntities(frameMilliseconds);      // "Actors advance BEFORE the snapshot is assembled"
8.  frameEvents_ = previousDeferredEvents;  deferredEvents_.clear();
9.  ZM 回合心跳（"AND IT HAS TO BE HERE"）
10. 保存 previousEventSequence / lastEvent / previousClientStates / previousArrivalHolds
11. snapshot_.flags = 0; constBaselines; 六个容器 clear + reserve
12. 提交上一 think 的摔落伤害（"COMMIT LAST THINK'S FALL DAMAGE FIRST"）
```

### 3.1 而第 7 步的理由

```php
// Actors advance BEFORE the snapshot is assembled, so the origin this frame
// publishes is the one they just moved to.
```

**✅ 三层**：

```text
1. actor 在快照组装【之前】推进
2. ⇒ **所以这一帧发布的 origin 是它们【刚移动到】的那个**
3. ⇒ **而不是上一帧的**
```

**✅ 一个**顺序的必然性**。

## 四、**ZM 回合心跳的"必须在这里"**（本组第三重要）

### 4.1 那段

```php
// THE ZM ROUND HEARTBEAT, AND IT HAS TO BE HERE.
//
// The first cut raised it from stepActorEntities, which runs four lines
// above -- and the two lines above THIS one rotate the event lists, so an
// event queued before them is moved into `previousFrameEvents` and is only
// ever put back on the REJECTED-frame path. The script never saw a single
// tick: the world spawned, `zm adjacent spawn zones` printed, and then
// nothing, forever. `codol.on` carries seventeen reactive events and no
// periodic one, so this is the only heartbeat a Lua round director can have.
//
// A rejected frame advances this stamp without the script seeing the tick,
// which costs one heartbeat out of the sixty in a minute. Not worth a
// rollback path of its own.
if (zmActorNamespaceEnabled_ && !zombieTeamWiped_ &&
    (snapshot_.serverTime - zmRoundTickMilliseconds_ >= 100u || zmRoundTickMilliseconds_ == 0u))
{
    zmRoundTickMilliseconds_ = snapshot_.serverTime;
    queueZmRoundTickEvent(snapshot_.serverTime);
}
```

### 4.2 十四层

```text
1. **ZM 回合心跳，而它【必须在这里】**
2. ⇒ **第一版从 `stepActorEntities` 抬起它，那个跑在上面四行**
3. ⇒ **而【这一行上面两行】轮换事件列表**
4. ⇒ **所以在它们【之前】排队的一个事件被移进 `previousFrameEvents`**
5. ⇒ **而只在【被拒帧】路径上被放回**
6. ⇒ **脚本从未见过一次 tick**
7. ⇒ **世界生成了、`zm adjacent spawn zones` 打印了、然后永远什么都没有**
8. ⇒ **`codol.on` 携带【十七个反应式事件】而没有周期事件**
9. ⇒ **所以这是【一个 Lua 回合导演唯一能有的心跳】**
10. ⇒ **一个被拒帧推进这个时间戳而脚本看不到 tick**
11. ⇒ **那在一分钟的六十个里花掉【一个心跳】**
12. ⇒ **不值得为它一条自己的回滚路径**
13. ⇒ **`>= 100ms` 或 `== 0`（首次）**
14. ⇒ **所以 10Hz 的心跳**
```

### 4.3 ⭐ **"世界生成了、打印了、然后永远什么都没有"**

**✅ 与 §355 的"前 40 帧的日志结论都作废"**同族（**第四次"部分工作而静默停止"**）。

**⇒ 三层**：

```text
1. 世界生成 ✓
2. ⇒ **一行日志 ✓**
3. ⇒ **然后零 tick**
```

**✅ 与 §362 的"帧验证通过而什么也没画"**同族（**第五次"部分成功"**）。

### 4.4 而**"十七个反应式事件而没有周期事件"**

**✅ 与 §367 的"`codol.on` 的反应式"**配合。**

**⇒ 三层**：

```text
1. `codol.on` 有 17 个反应式
2. ⇒ **而【零】个周期式**
3. ⇒ **所以 Lua 回合导演没有心跳**
```

**✅ **一个架构缺口**，而这里**补上了**。

### 4.5 而**"一个被拒帧花掉一个心跳，不值得回滚"**

**✅ 与 §349 的"代价不对称的正确选择"**同族（**第十二次**）。

**⇒ 三层**：

```text
代价：一分钟花 1 个 tick（1/60）
修复代价：一条回滚路径
⇒ **1/60 不值得**
```

**✅ 一个**量化的取舍**。

## 五、**摔落伤害的"三层命名"**（本组第四重要）

### 5.1 六种结果

```cpp
enum class FinishPlayerDamageResult {
    Applied, ClientNotFound, NotPlaying, InvalidPayload,
    DeathTransitionUnavailable, NativeMirrorUnavailable,
};
```

**⇒ 六种，且每种一个名字。**

### 5.2 而"AND SAY WHAT IT RETURNED"

```php
// AND SAY WHAT IT RETURNED. This used to be a bare
// static_cast<void>, which proves only that the server DECIDED
// to hurt the player -- not that health moved. The refusals are
// real and reachable: a lethal fall needs the death transition
// to be available, and a fall that lands on the frame the
// player is already dead is refused too. Those read identically
// to "it worked" from outside, and the log is the only place
// the difference can show.
const auto before = state.client.playerState.health;
const auto result = finishPlayerDamage(*payload);
const auto after = clientStates_.count(clientNum) ? clientStates_.at(clientNum).client.playerState.health : 0;
OlMod::RuntimeLog::write(..., "fall damage client=... damage=... health " +
    std::to_string(before) + " -> " + std::to_string(after) + " result=" + damageResultName(result));
```

**⇒ 十一层**：

```text
1. **并且说它返回了什么**
2. ⇒ **这过去是一个裸的 `static_cast<void>`**
3. ⇒ **它只证明了服务器【决定】伤害玩家**
4. ⇒ **而不是血量【动了】**
5. ⇒ **那些拒绝是真实且可达的**：
     · **一次致命的摔落需要死亡转换可用**
     · **而在玩家【已经死了】的那一帧落地的摔落也被拒**
6. ⇒ **它们从外面读起来与"它工作了"完全相同**
7. ⇒ **而日志是区别能显示的唯一地方**
8. ⇒ **所以记录 `before -> after` 与 `result`**
```

**✅ 与 §346 的"七十五项一个笼统的拒绝"**相反**（这是**六种具名结果**）。**

**⇒ **第四次"命名而不是计数"。**

### 5.3 而**"自我归因"的三处**

```cpp
// Self-inflicted: MOD_FALLING has no other agent, and the
// player's own entity is the only honest attribution.
.inflictorEntityNum = clientNum,
.attackerEntityNum = clientNum,
```

**⇒ 三层**：

```text
1. `MOD_FALLING` 没有其它代理
2. ⇒ **玩家自己的实体是唯一诚实的归因**
3. ⇒ **所以 inflictor 与 attacker 都是自己**
```

**✅ 一个**诚实的建模**。**

### 5.4 而 **`weaponAssetIndex = 0` 的理由**

```php
// Genuinely absent, and the builder admits 0 for FALLING
// alone. The held weapon is 0 during the unarmed window, so
// naming it here would drop exactly the falls that happen
// right after a spawn.
```

**⇒ 五层**：

```text
1. **真正缺席，而 builder 【只为 FALLING】接纳 0**
2. ⇒ **持有的武器在无武装窗口里是 0**
3. ⇒ **所以在这里命名它会【恰好丢掉】那些出生后立刻发生的摔落**
4. ⇒ **所以用 0**
```

**✅ 与 §352 的"无武装出生"**配合。**

**⚠ 而"丢掉"⇒ **所以 `finishPlayerDamage` 会拒绝一个 `weapon == 0` 的伤害**（除 FALLING）。**

**✅ 一个**精确的例外**。

### 5.5 而**"直下"的方向**

```php
// Straight down. Feeds the damage direction indicator, and
// an upward or zero vector would point the flinch wrongly.
.direction = { 0.0f, 0.0f, -1.0f },
```

**⇒ 三层**：

```text
1. **直下**
2. ⇒ **喂伤害方向指示器**
3. ⇒ **一个向上或零向量会把畏缩指错**
```

**✅ 一个**极具体的 UI 关切**。**

## 六、**三层"命名失败项"的日志模式**（本组第五重要）

### 6.1 第一处：`spawn not requested`

```php
if (playing && client.spawnSequence && !spawnRequested) {
    auto why = "client=" + ... + " spawnSeq=" + ... + " applied=" + ... +
        (sharedPmoveAvailable() ? "" : " NO_SHARED_PMOVE") +
        (client.spawnSequence == gameClient.appliedSpawnSequence ? " ALREADY_APPLIED" : "");
    if (why != spawnRefusalReasons_[clientNum]) { write; spawnRefusalReasons_[clientNum] = why; }
}
```

### 6.2 第二处：`spawn refused`

```php
if (spawnRequested && !(spawnPoint && validInputLoadout && validInputCustomization && spawnSolid)) {
    auto why = ... +
        (spawnPoint ? "" : " NO_SPAWN_POINT") +
        (validInputLoadout ? "" : (client.resolvedLoadout ? " LOADOUT_INVALID" : " LOADOUT_UNRESOLVED")) +
        (validInputCustomization ? "" : (client.characterCustomization ? " CUSTOMIZATION_INVALID" : " CUSTOMIZATION_ABSENT")) +
        (spawnSolid ? "" : " NO_SPAWN_SOLID");
    ...
}
```

### 6.3 第三处：`SV_ClientSpawn` 内部失败

```php
if (!spawned) {
    // The call had no else branch, so a spawn that was requested, passed
    // every precondition and then refused inside looked exactly like no spawn
    // at all -- and appliedSpawnSequence is only advanced on success, so it
    // retried in silence twenty times a second.
    auto why = "client=" + ... + " reason=" + spawnFailure;
    ...
}
```

### 6.4 三层 ⇒ 一个完整的覆盖

```text
第一处  **从未请求**（五合取的前置之一失败）
第二处  **请求了但前置失败**（四个具名项）
第三处  **前置全通过而【内部】拒绝**（`spawnFailure` 字符串）
```

**✅ 与 §346 的"七十五项合取"**完全相反（这是**三层穷尽的命名**）。**

**⇒ 三层**：

```text
① 没请求      ⇒ 命名【为什么没请求】
② 请求了但拒  ⇒ 命名【哪一项】
③ 通过了但内部拒 ⇒ 命名【内部理由】
```

**✅ **一个完整的可观测性设计**。**

**⚠ 而"一个五合取"与"四个具名项"⇒ **第二处覆盖了四加一个**。**

**✅ **完整。**

### 6.5 而**"去重"的三处一致**

```cpp
if (why != spawnRefusalReasons_[clientNum]) { write; spawnRefusalReasons_[clientNum] = std::move(why); }
```

**⇒ 三层**：

```text
1. **每客户端一个理由字符串**
2. ⇒ **只在【变化】时写**
3. ⇒ **所以一个卡住的客户端打一行而不是每秒二十行**
```

**✅ 与 §346 的 `psDomainBad` 与 §347 的 `std::hash`**第三种去重实现。**

**⇒ **第四次去重，而这里是**最好的**（按客户端 + 内容变化）。

### 6.6 而**"它静默地每秒重试二十次"**

**✅ 与 §362 的"每秒重置 20 次"**同族（**第五次 20Hz**）。

## 七、**"比赛决定之后没有人回来"**

```php
// NOBODY COMES BACK AFTER THE MATCH IS DECIDED. A player reported
// the exact shape of this: "after the kill and then freeze, the
// player respawned in front of me where he died". The kill that
// ends a match still arms a respawn three seconds out, and the
// freeze at +1000 does not touch it, so the loser stood back up in
// the middle of the end-of-match hold.
//
// Both spawn paths are gated, not just the timed one: an external
// spawn request that arrives after the final kill is the same
// mistake with a different trigger.
const auto matchOver = matchCompleted_;
const auto externalSpawnRequested = !matchOver && deathAnimationComplete && sharedPmoveAvailable() && playing &&
    client.spawnSequence && client.spawnSequence != gameClient.appliedSpawnSequence;
const auto timedRespawnRequested = !matchOver && deathAnimationComplete && sharedPmoveAvailable() && playing &&
    gameClient.deathState && gameClient.respawnTime &&
    (int32)(snapshot_.serverTime - *gameClient.respawnTime) >= 0;
```

### 7.1 十层

```text
1. **比赛决定之后没有人回来**
2. ⇒ **一个玩家报告了它的精确形状**：
     · **"在击杀与冻结之后，玩家在我杀死他的地方又复活了"**
3. ⇒ **结束一场比赛的那次击杀仍武装一个三秒后的重生**
4. ⇒ **而 `+1000` 的冻结【不碰它】**
5. ⇒ **所以输家在比赛末保持的中间站了起来**
6. ⇒ **两个生成路径都被门控，不只是计时的那个**
7. ⇒ **因为在最终击杀之后到达的一个外部生成请求是【同一个错误的不同触发器】**
8. ⇒ **所以 `matchOver` 与【两个】条件与**
```

**✅ 与 §349 的"玩家的判决"**同族（**第四次以玩家观感为终审**）。

**⚠ 而**两个生成路径**（外部 / 计时）⇒ **必须同时修**。**

**✅ 与 §367 的"两条路径必须一致"**同族（**第六次"多路径一致"**）。

## 八、**玩家的初次状态（19 个字段）**

```cpp
gameClient.playerState = {
    .clientNum = clientNum, .commandTime = snapshot_.serverTime,
    .pmType = 4, .gravity = 800, .speed = 190,
    .moveSpeedScaleMultiplier = 1.0f, .health = 100, .maxHealth = 100,
    .viewHeightCurrent = 60.0f, .viewHeightTarget = 60, .viewHeightLerpTarget = 60,
    .playerSizeScale = PlayerSizeScaleBootstrap,
    .groundEntityNum = EntityNumNone, .viewEntityNum = EntityNumNone,
    .movingPlatformEntityNum = EntityNumNone, .remoteEyesEntityNum = EntityNumNone,
    .remoteControlEntityNum = EntityNumNone, .remoteTurretEntityNum = EntityNumNone,
    .linkEntityNum = EntityNumNone,
};
```

**⇒ 三层**：

```text
1. **`pmType = 4`**（未出生）
2. ⇒ **`gravity = 800` / `speed = 190`**（Cod 的经典值）
3. ⇒ **`health = maxHealth = 100`**
4. ⇒ **三个视角高度 60**
5. ⇒ **`playerSizeScale = PlayerSizeScaleBootstrap`**
6. ⇒ **七个 `EntityNumNone`**
```

**✅ 与 §344 的"`pmType != SvPmTypeNormal` 拒绝"配合。**

**⚠ 而 `pmType = 4` ⇒ **所以初次状态不是 Normal**（不能传送/拾取）。**

**✅ 与 §364 的"`pmType == 0` 才能传送"**完全一致 ✓

**⇒ **第二次确认 `pmType` 的取值。**

### 8.1 而 **`PlayerSizeScaleBootstrap` 的注释**

```php
// CODDIFF(client_spawn): this is the only source default.
// Entity and DObj state are downstream projections; they
// must not repeat or independently choose the value.
```

**⇒ 五层**：

```text
1. **这是唯一的源默认值**
2. ⇒ **实体与 DObj 状态是【下游投影】**
3. ⇒ **它们不能重复或独立选择这个值**
4. ⇒ **所以 `entity.networkState.playerSizeScale = gameClient.playerState.playerSizeScale`**
```

**✅ 与 §368 三的"actor 在快照组装之前推进"**同族（**一个"单一源"原则**）。

**⇒ **一个关键的架构约束**：**

```text
playerState   是【源】
entity       是【投影】
DObj         是【投影的投影】
⇒ **只有源可以选值**
```

**✅ **一个贯穿全文件的层次模型。**

## 九、关键结论

1. **⭐⭐ "正确的编号是 bit `0x10` 的【必要】而非【充分】条件"`** —— 还必须**对着客户端将解析的同一基线做 delta**。
2. **⭐ "越精确地匹配就越精确地抵消"`** —— `0xFFFFFF ^ 0 = 0xFFFFFF` 而客户端 XOR 自己的 `0xFFFFFF` ⇒ **0**。
3. **两个字段（`solid` 与 `brushModelIndex`）同时抵消 ⇒ 实体到达时没有 solid 也没有模型 ⇒ 不被画`**。
4. **"所以两者永远一起动：写入器 delta 的表就是那个标志告诉客户端去解析的表。空表，无标志"`** —— **一条强制不变式**。
5. **⭐⭐ "2026-08-31 武装，同一小时解除，只在【读了客户端之后】再次武装"`** —— **三次尝试**。
6. **第一次武装 ⇒ 黑屏**（无字段"变了"实体 ⇒ 三位跳号消耗下一个实体号）。
7. **"与基线相同"的编码是**读者的第二位**`** —— 第二次确认 §345 的 `(0,0)`。
8. **"写入器还拒绝发出一个无字段的『变了』实体 ⇒ 那个失步不能静默地回来"`** —— 第二次确认 §343 的守卫。
9. **`beginFrame` 的十二步序列**，而 **"actor 在快照组装之前推进，所以这一帧发布的 origin 是它们刚移动到的那个"`**。
10. **⭐ ZM 回合心跳的"必须在这里"`** —— 从 `stepActorEntities` 抬起它让事件**被移进 `previousFrameEvents` 而只在被拒帧路径放回** ⇒ **脚本零 tick**。
11. **"世界生成了、`zm adjacent spawn zones` 打印了、然后永远什么都没有"`** —— 第四次"部分工作而静默停止"。
12. **"`codol.on` 携带十七个反应式事件而没有周期事件 ⇒ 这是 Lua 回合导演唯一能有的心跳"`** —— 一个**架构缺口**。
13. **"一个被拒帧花掉一个心跳（1/60），不值得一条回滚路径"`** —— 第十二次代价不对称。
14. **摔落伤害的六种具名结果**，而 **"一个裸的 `static_cast<void>` 只证明服务器【决定】伤害玩家，而不是血量【动了】"`**。
15. **"自我归因"**（`MOD_FALLING` 没有其它代理）+ **`weaponAssetIndex = 0` 的理由**（"命名它会恰好丢掉那些出生后立刻发生的摔落"）。
16. **"直下"的方向喂伤害指示器**（"向上或零向量会把畏缩指错"）。
17. **⭐⭐ 三层"命名失败项"的完整覆盖**（从未请求 / 请求了但前置失败 / 通过了但内部拒绝）—— **与 §346 的"七十五项合取"完全相反**。
18. **第四次去重实现，而这里是【最好的】**（按客户端 + 内容变化）。
19. **"它静默地每秒重试二十次"`** —— 第五次 20Hz。
20. **"比赛决定之后没有人回来"`** —— 玩家报告"输家在比赛末保持的中间站了起来"，而**两个生成路径都必须门控**（第六次多路径一致）。
21. **玩家的初次状态 19 个字段**（`pmType = 4` / `gravity = 800` / `speed = 190` / `health = 100` / 三视角高度 60 / 七 `EntityNumNone`）。
22. **⭐ "`PlayerSizeScaleBootstrap` 是唯一的源默认值；实体与 DObj 是下游投影，它们不能重复或独立选择这个值"`** —— **一个贯穿全文件的层次模型**（源 / 投影 / 投影的投影）。

## 十、未闭合点

- `PlayerSizeScaleBootstrap` 的值。
- `matchCompleted_` 的设置点。
- `finishPlayerDamage` 的完整拒绝条件。
- `queueZmRoundTickEvent` 发出的事件名。
- `codol.on` 的十七个反应式事件清单。
- `sv_snapshot_mp.cpp` 19200 行之后未读取（27,016 行，进度 71%）。
