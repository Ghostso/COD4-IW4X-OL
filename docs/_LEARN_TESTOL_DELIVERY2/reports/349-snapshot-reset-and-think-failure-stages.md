# 349 · **`reset()` 的六十八个字段**、**`SvClientThinkFailureStage` 的四十个阶段**、**"要塌缩的是爆发而不是一场战斗"**

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 11197–11600 行。

## 二、`SvServerWorld::reset()` 的**六十八项**（本组第二重要）

### 2.1 按主题分组

```text
快照与事件
  snapshot_ = {}
  eventSequence_ = 0
  frameEvents_.clear()
  deferredEvents_.clear()
  lastEvent_.reset()
  pendingAnimationCommands_.clear()

僵尸/工厂（最大一组，约 30 项）
  zombieDamageNumbers_ / zombieInjuries_ / zombieScoreFeedback_
  zombieBattery_.fill(0)
  zombieRevivalEnabled_ = zombieRevivalActive_ = zombieTeamWiped_ = false
  zombieDowned_ / zombieDownedInventories_ / zombieFallbackPistol_=0
  factoryArrivalHolds_ / factoryTravelHolds_ / factoryArrivalMap_=false
  factoryDebugGodmode_ = false
  factoryPerkMachinesEnabled_ / factoryInteractablesEnabled_
  factoryPurchasedPerks_
  factoryPowerMotion/Bound/Failed/Complete/Started/Handles/LeverModel/BodyModel
  zmRetainedCorpses_ / zmActorDeadAt_ / zmDeathFxStates_
  zmFaceGlowStates_ / zmFaceGlowDiagnosticCount_=0
  zmActorNamespaceEnabled_ / zmReconstructedFeedbackEnabled_
  zmRoundTickMilliseconds_=0 / zmPresentationRound_=1

玩家与武器
  playerAbilities_ / paintedPlayers_ / playerEquipment_
  observedWeapons_ / noclipHoldUntil_
  multiplayerOffhandWeapons_
  livingWeaponChildren_.fill({}) / livingWeaponRightTag_=0
  debugBatteryReadyTime_.fill(0)

实体与碰撞
  entityPool_.reset() / entities_
  collisionEntities_ / playerMovementCollisionEntities_ / bulletCollisionEntities_
  entityDamageStates_ / entityDamageHandlers_ / pendingActorPlayerDamage_
  playerTouchHandlers_ / entityTouchHandlers_
  antiLagHistory_
  agentSlotsInUse_.fill(false)

地图与玻璃
  spawnPoints_ / waitingForLoadoutPoint_.reset()
  glassState_.reset() / glassMetadata_ = {} / glassDamageState_.reset()
  factoryDoorMotions_ / missiles_ / factorySpecialWeapons_/Combat_/Statuses_
  factoryViewFxRecipients_ / factoryViewFxNext_
  factoryTrapPresentation_ / factoryTrapFx_={}
  scavengerBags_
  zmPlayerNextActorHitMilliseconds_

击杀回放（带注释）
  killcamReplayWindows_.clear()

客户端
  clientStates_.clear()
```

### 2.2 而 **`killcamReplayWindows_` 的注释**

```php
// 29200: the replay window must not survive a map change, or the first
// death of the next match would be armed against a pose ring that has
// already been reset underneath it.
```

**⇒ 四层**：

```text
1. **回放窗口绝不能活过一次地图切换**
2. ⇒ **否则下一场比赛的第一次死亡会被武装在一个**
3. ⇒ **已经在其下面被重置的姿势环上**
4. ⇒ 所以必须清
```

**✅ 与 §347 的"`killcamReplayPoses` 必须指名同一个接收者"**配合。**

**⚠ 这是 `reset()` 里**唯一被注释解释**的一项。**

**⇒ 说明它曾经是一个真实的 bug。**

### 2.3 而**`zmPresentationRound_ = 1`（不是 0）**

**⇒ 三层**：

```text
1. 其它全部清零或清空
2. ⇒ **而 `zmPresentationRound_ = 1`**
3. ⇒ **所以轮次从 1 开始**
```

**✅ 一个**非零的初值**（与 §337 的 `TeamBitCount` 默认 `Sc`(2) 同族）。**

**⚠ 而 §344 的 `reset` 里 `eventSequence_ = 0`。**

**⇒ 两个不同的重置约定。**

### 2.4 而**`reset()` 的顺序**

```text
① 镜像（Collision 阶段的空调用）
② nativeEntityMirrorSynchronized_ = false
③ snapshot_ = {}
④ 其余 60+ 项
```

**✅ 与 §348 六的分析一致。**

**⚠ 而 ③ 在 ① 之后 ⇒ **镜像用的是旧 `snapshot_.serverTime`** ✓**

## 三、`setZmReconstructedFeedbackEnabled` 的**"策略变化时清表现状态"**

```cpp
void SvWorld::setZmReconstructedFeedbackEnabled(const bool enabled)
{
    // OLMOD(reconstructed-zm-feedback): default off, reset across maps.
    // Clear presentation state on policy changes; combat state is untouched.
    if (zmReconstructedFeedbackEnabled_ != enabled) {
        for (auto &[owner, numbers] : zombieDamageNumbers_)
            for (auto &record : numbers.records) record.style = 0;
    }
    zmReconstructedFeedbackEnabled_ = enabled;
}
```

### 3.1 五层

```text
1. **默认关闭，跨地图重置**
2. ⇒ **在策略变化时清表现状态**
3. ⇒ **战斗状态不动**
4. ⇒ 具体是 **把每个伤害数字记录的 `style` 清零**
5. ⇒ **只在开关【变化】时**
```

**✅ "战斗状态不动而表现状态清"是一个**精确的分界**。**

**⇒ 与 §346 的"材质/文本两个不相交抽屉"**同族（**职责分离**）。

## 四、`SvClientThinkFailureStage` 的**四十个阶段**（本组最重要的一段）

### 4.1 完整清单（按主题分）

```text
【核心流程】
None
NotPlaying                       不在比赛中
SpawnedThisFrame                 本帧出生

【命令】
NonIncreasingCommandTime         命令时间不递增
InvalidInputState                输入状态无效

【原生 pmove —— 十四个】
NativePmoveUnavailable           不可用
NativePmoveRejected              被拒
InvalidPmoveOutput               输出无效
NativePmoveInvalidBinding        绑定无效
NativePmoveInvalidCommand        命令无效
NativePmoveWrongThread           线程错
NativePmoveReentrantCall         重入
NativePmoveHandlerSlotBusy       处理槽忙
NativePmoveAnimConditionInstallFailed  动画条件安装失败
NativePmoveNonIncreasingCommandTime    非递增命令时间
NativePmoveSliceLimitExceeded         片数超限
NativePmoveCommandTimeNotAdvanced     命令时间未推进
NativePmoveNativeException            原生异常
NativePmoveHandlerRestoreFailed       处理器恢复失败
NativePmoveTraceFailed                追踪失败
NativePmoveAnimConditionRestoreFailed 动画条件恢复失败
NativePmoveInvalidOutput              输出无效

【状态投影】
NativePlayerStateProjection      原生 playerState 投影
NativeCommandTimeMismatch        原生命令时间不匹配

【武器移动】
WeaponMovementRejected
InvalidWeaponMovementOutput

【实体状态转换 —— 五个】
EntityStateConversion
PostConversionProjection
EntityStateDecode
PredictableEventDecode
ConvertedStateMismatch

【客户端事件】
ClientEventsUnsupported
ClientEventsRejected

【最终投影】
FinalProjection
FinalStateMismatch

【其它】
InvalidClientImpacts
NativeEntityMirrorUnavailable
```

### 4.2 而**原生 pmove 占十七个（42%）**

**⇒ 三层**：

```text
1. 四十个阶段里 **17 个是原生 pmove**
2. ⇒ **所以 pmove 是最大的失败源**
3. ⇒ **而 17 个里有 4 个是"恢复失败"族**（HandlerRestore / AnimConditionRestore / HandlerSlotBusy / ReentrantCall）
```

**✅ 与 §347 的"我们的 pmove 与客户端的真的分叉了"**配合。**

**⚠ 而四个"恢复失败"说明**调用了原生函数然后需要还原状态**。**

**⇒ 所以本服务器**调用客户端自己的 pmove**（原生），然后**必须还原它改的每个东西**。**

**✅ 与记忆的"战斗服 `world` 从未绑定"**不同** —— 这是**客户端侧 pmove 的借用**。**

### 4.3 而**"恢复"的四项**

```text
HandlerRestoreFailed              处理器
AnimConditionRestoreFailed        动画条件
HandlerSlotBusy                   槽忙（拒绝）
ReentrantCall                     重入（拒绝）
```

**✅ 四个 ⇒ 所以原生 pmove 被**安装了处理器与动画条件**。**

### 4.4 而**`NativePmoveFailure` 到 `SvClientThinkFailureStage` 的映射**

```cpp
static SvClientThinkFailureStage nativePmoveFailureStage(const SvNativePmoveFailure failure)
{
    switch (failure) {
    case None: return NativePmoveRejected;      // ← 【None 映射到 Rejected】
    case InvalidBinding: return ...
    ...
    }
    return NativePmoveRejected;
}
```

**⇒ 三层**：

```text
1. **`SvNativePmoveFailure::None` 映射到 `NativePmoveRejected`**
2. ⇒ 那是一个**逻辑上的不可能**（None 不该是一个失败）
3. ⇒ **所以调用方在"没有具体失败码"时用 `Rejected` 作为兜底**
```

**✅ 与 §346 的"默认分支"同族。**

**⚠ 一处**可能误导的映射**（None ⇒ Rejected 而不是 None）。**

### 4.5 而**"四十个阶段名"是一个完整的诊断面**

**✅ 与 §346 的十九种 frame failure、§348 的十五种 write failure**第三次。**

**⇒ **三个枚举、三种层级的失败名：**

```text
SvSnapshotFrameValidationFailure  19 种   帧准入
SvSnapshotWriteFailure            15 种   写段
SvClientThinkFailureStage         40 种   client think
```

**✅ **七十四种命名失败。**

**⇒ 而这些都是**"沉默读起来像健康"的对策**。**

## 五、`configureSpawnPoints` 的**验证**（本组第三重要）

```cpp
bool SvServerWorld::configureSpawnPoints(
    std::span<const SvWorldSpawnPoint> spawnPoints,
    std::optional<SvWorldSpawnPoint> waitingForLoadoutPoint)
{
    const auto finiteVector = [](const auto &vector) {
        return std::ranges::all_of(vector, [](const float value) { return std::isfinite(value); });
    };
    if (spawnPoints.empty() ||
        std::ranges::any_of(spawnPoints, [&](const auto &spawnPoint) {
            return !finiteVector(spawnPoint.origin) || !finiteVector(spawnPoint.angles) ||
                (spawnPoint.team != SvTeam::None && spawnPoint.team != SvTeam::Tf &&
                 spawnPoint.team != SvTeam::Sc);
        }) ||
        (waitingForLoadoutPoint && (!finiteVector(waitingForLoadoutPoint->origin) ||
                                    !finiteVector(waitingForLoadoutPoint->angles))))
    {
        return false;
    }
    spawnPoints_.assign(spawnPoints.begin(), spawnPoints.end());
    waitingForLoadoutPoint_ = waitingForLoadoutPoint
        ? std::move(waitingForLoadoutPoint)
        : std::optional<SvWorldSpawnPoint>{ spawnPoints.front() };
    return true;
}
```

### 5.1 五层

```text
1. **空列表 ⇒ 拒绝**
2. ⇒ **任一出生点非有限或 team 不在 {None, Tf, Sc} ⇒ 拒绝**
3. ⇒ **等待装备点若非有限 ⇒ 拒绝**
4. ⇒ **替换整个列表**（assign）
5. ⇒ **若未给等待点 ⇒ 用【第一个出生点】**
```

**✅ 与 §347 四的"只有 1 与 2 在客户端解析"**配合 —— 所以 team 只允许 3 个值。**

**⚠ 而 `None` 允许 ⇒ 所以**自由混战的出生点无队**。**

**✅ 与 §347 四的 `SV_PresentableTeam` 把 `None` 映射到 1 或 2**完全一致 ✓**

### 5.2 而 **`waitingForLoadoutPoint` 的默认**

**⇒ 三层**：

```text
1. 若调用方给了 ⇒ 用它
2. ⇒ 否则用 `spawnPoints.front()`
3. ⇒ **所以装备点总是不为空**
```

**✅ 一个**总有一个合法值**的保证。**

## 六、`requestAltWeaponToggle` 的**按客户端标志**

```cpp
void SvServerWorld::requestAltWeaponToggle(const std::uint32_t clientNum)
{
    if (clientNum < pendingAltToggle_.size())
        pendingAltToggle_[clientNum] = true;
}
```

**⇒ 三层**：

```text
1. 一个按客户端的 bool 数组
2. ⇒ **越界 ⇒ 静默丢弃**
3. ⇒ **否则置 true**（而不是切换）
```

**✅ 与 §344 的 `requestAltWeaponToggle` 配合 —— 而 §344 提到"`n 89` 是可靠命令"。**

**⚠ 而这里 `= true` 而不是 `^= true` ⇒ **重复请求不撤销**。**

**⇒ 合理（要的是一个"有请求"的事实）。**

## 七、**"要塌缩的是爆发而不是一场战斗"**（本组第四重要）

### 7.1 那段

```php
// OFF WITH OLMOD_PLAYER_VOCALS=0. A pain grunt is the loudest thing in
// this pass and the cheapest to silence if it is wrong.
static const bool vocalsEnabled = [] {
    const char *const value = std::getenv("OLMOD_PLAYER_VOCALS");
    return !(value && value[0] == '0' && !value[1]);
}();
if (!vocalsEnabled) return;
// COLLAPSE A BURST, NOT A FIGHT.
//
// The first cut raised a pain vocal per DAMAGE PAYLOAD, and a burst of
// bullets inside one command is a dozen payloads -- a dozen vocals into
// a four-slot ring, which is not something the client can dispatch.
//
// The second cut used FOUR SECONDS, taken from retail's match-wide rate
// (137 pain vocals across ~8 players over 621 s). That rate is real and
// it is the wrong model: it describes eight players spread over a map,
// not two of them in a close fight. The player's verdict was "I've only
// heard it once" -- correct, because at one grunt per four seconds most
// hits in a 1v1 are silent and the one that lands reads as random.
//
// What actually needs collapsing is the BURST: the several payloads a
// single shot or a single command produces. Half a second does that and
// leaves every distinct exchange audible. The ring carries it easily --
// measured at two to four events a second against forty snapshots.
constexpr std::uint32_t PlayerVocalCooldownMilliseconds = 500;
```

### 7.2 十三层

```text
1. **用 `OLMOD_PLAYER_VOCALS=0` 关闭**
2. ⇒ **一声痛呼是这一遍里最响的东西，而错了的话也是最便宜静音的**
3. ⇒ **塌缩一个爆发，不是一场战斗**
4. ⇒ **第一版对【每个伤害载荷】起一声痛呼**
5. ⇒ **而一条命令里的一串子弹是【十几个载荷】**
6. ⇒ **十几个痛呼进一个四槽环，那不是客户端能派发的**
7. ⇒ **第二版用了【四秒】**，取自零售的整场速率
8. ⇒ **（137 声痛呼跨约 8 个玩家在 621 秒里）**
9. ⇒ **那个速率是真的而它是【错误的模型】**
10. ⇒ **它描述的是八个玩家散布在一张地图上，不是他们两个在一场近距离战斗里**
11. ⇒ **玩家的判决是"我只听到过一次" —— 正确的**，因为在每四秒一声时**一场 1v1 里大多数命中是静默的**
12. ⇒ **而真正需要塌缩的是【爆发】**：一次射击或一条命令产生的几个载荷
13. ⇒ **半秒做那个而让每一次不同的交锋都可听见。环轻松承载它 —— 实测每秒二到四个事件对四十个快照**
```

### 7.3 **"那个速率是真的而它是错误的模型"**

**✅ 这是本文件里**最深刻的一条统计教训**。**

**⇒ 与 §345 的"从一个不可能包含一个的样本得出结论"**同族但不同**：**

```text
§345  样本偏差：样本不可能包含目标 ⇒ 零命中无意义
§349  模型偏差：**整场速率是真的** ⇒ 但它描述的场景与目标场景不同
```

**✅ **两种不同的"统计上正确而应用上错误"。**

### 7.4 而**"玩家的判决"**

**✅ 一个**用户验收测试**被引用为证据。**

**⇒ 与 §331 的"`OLMOD_SWAY_PHASE` 的算子调优 1.0→3.0→2.0→2.5"**同族（**第二次"以玩家观感为终审"**）。**

### 7.5 而 **500ms 的 12.5 倍缩减**

```text
第一版   每载荷 ⇒ 十几声/秒
第二版   4000ms ⇒ 0.25 声/秒
终版     500ms  ⇒ 2 声/秒
```

**✅ 而 `2 声/秒` 与"实测每秒二到四个事件"**一致 ✓**

**⇒ **设计目标 = 实测上界的一半**。**

### 7.6 而**四槽环**

```cpp
auto &ring = playerEventRings_[clientNum];
ring.ring[ring.sequence & 3u] = { EventSoundAlias, (int32)parameter };
ring.sequence = static_cast<uint8_t>(ring.sequence + 1);
```

**⇒ 四层**：

```text
1. **四槽环**（`& 3`）
2. ⇒ **写当前 sequence 命名的槽**
3. ⇒ **然后推进**
4. ⇒ **`uint8` 的 sequence（回绕）**
```

**✅ 与 §342 的"四槽环"**第五次确认。**

**⇒ 而注释解释顺序：**

```php
// THE SAME CONVENTION THE MERGE USES, and it has to be: write the slot
// the CURRENT sequence names, then advance. clientThink copies whatever
// the native ring gained on top of this and republishes both fields
// from here, so an event staged now survives to the wire; one written
// to entity.networkState directly does not.
```

**⇒ 六层**：

```text
1. **与合并用的同一个约定，而它必须是**
2. ⇒ **写【当前】 sequence 命名的槽，然后推进**
3. ⇒ **`clientThink` 复制原生环在其上获得的任何东西**
4. ⇒ **并从【这里】重新发布两个字段**
5. ⇒ **所以现在暂存的一个事件活到线上**
6. ⇒ **而一个直接写到 `entity.networkState` 的不会**
```

**✅ 一个**"唯一正确的写入路径"**。**

**⇒ 与 §343 的"正确的编码器已经在文件里"**同族（**第二次"只有一条路对"**）。**

## 八、`setXxx` 的**九个注入点**

```text
setSharedPmoveRunner
setWeaponMovementRunner
setPlayerStateToEntityStateConverter
setDeathAnimationRunner
setSpawnAnimationRunner
setClientEventsHandler
setMissileFrameRunner
setAltFireResolver
setClientImpactsDispatcher(+ order)
setClientImpactsScriptDispatcher
```

**⇒ 十个（含 `+ order`）。**

**✅ 与 §312 的"`ServerCore` 注入五个可调用物"**同族 —— **一个注入式架构。**

**⇒ 而这里是**十个注入点**。**

**⚠ 而 §312 说的是 `Appmain.cpp` 的 `ServerCore`（五个）。**

**⇒ 所以**两个注入层**（`ServerCore` 五个 + `SvServerWorld` 十个）。**

### 8.1 而 `setClientImpactsDispatcher` **带一个 order**

```cpp
void setClientImpactsDispatcher(const SvClientImpactCallbackOrder callbackOrder,
                                SvClientImpactsDispatcher dispatcher)
{
    clientImpactCallbackOrder_ = callbackOrder;
    clientImpactsDispatcher_ = std::move(dispatcher);
}
```

**⇒ 三层**：

```text
1. **一个回调顺序枚举**
2. ⇒ **与派发器一起注入**
3. ⇒ **所以顺序是可配置的**
```

**⚠ 一个**可疑的设计**（为什么顺序要可配？）。**

**⇒ 可能因为**两个 build 的回调顺序不同**。**

**✅ 与 AGENTS.md 的"确认参照服务同一个 build"配合。**

## 九、关键结论

1. **`reset()` 的六十八项**，按八个主题分组，而**工厂/僵尸占约 30 项**。
2. **`killcamReplayWindows_` 是唯一被注释解释的项** —— "回放窗口绝不能活过一次地图切换"。
3. **`zmPresentationRound_ = 1` 而非 0** —— 一个非零初值。
4. **`reset()` 的四步顺序**：镜像（旧时间）→ 清标志 → 清 `snapshot_` → 其余。
5. **`setZmReconstructedFeedbackEnabled` 的"战斗状态不动而表现状态清"** —— 一个精确的职责分界。
6. **⭐ `SvClientThinkFailureStage` 的四十个阶段**，而**原生 pmove 占十七个（42%）**。
7. **四个"恢复失败"族** ⇒ 本服务器**借用客户端的原生 pmove** 并**必须还原它改的每个东西**。
8. **`SvNativePmoveFailure::None` 映射到 `NativePmoveRejected`** —— 一个可能误导的兜底。
9. **⭐ 全区共有七十四种命名失败**（帧 19 + 写 15 + think 40），全部是"沉默读起来像健康"的对策。
10. **`configureSpawnPoints` 的五层验证**，而 team 只允许 `{None, Tf, Sc}`（与 `SV_PresentableTeam` 一致）。
11. **等待装备点总有一个合法值**（默认取第一个出生点）。
12. **`requestAltWeaponToggle` 用 `= true` 而非 `^=`** ⇒ 重复请求不撤销。
13. **⭐ "要塌缩的是爆发，不是一场战斗"** —— 三版参数（每载荷 → 4 秒 → 500ms）。
14. **⭐ "那个速率是真的而它是错误的模型"** —— 整场速率描述八个玩家散布在图上，不是两个人在近战。
15. **"玩家的判决是『我只听到过一次』"** —— 第二次以玩家观感为终审。
16. **500ms = 实测上界（2–4 事件/秒）的一半** —— 设计目标。
17. **四槽环第五次确认**，而"写当前 sequence 命名的槽然后推进"是**唯一正确的写入路径**。
18. **"一个直接写到 `entity.networkState` 的不会活到线上"** —— 第二次"只有一条路对"。
19. **`SvServerWorld` 的十个注入点** —— 与 `ServerCore` 的五个构成**两个注入层**。
20. **`setClientImpactsDispatcher` 带一个可配置的回调顺序** —— 可能因为两个 build 的顺序不同。

## 十、未闭合点

- `reset()` 里那六十八项是否有遗漏的容器。
- `zmPresentationRound_` 从 1 开始的理由。
- 原生 pmove 的"安装/恢复"具体安装了什么（处理器 + 动画条件）。
- `SvClientImpactCallbackOrder` 的取值。
- `OLMOD_PLAYER_VOCALS` 的默认（代码是 `!(value && value[0]=='0' && !value[1])` ⇒ **默认为开**）。
- `sv_snapshot_mp.cpp` 11600 行之后未读取（27,016 行，进度 43%）。
