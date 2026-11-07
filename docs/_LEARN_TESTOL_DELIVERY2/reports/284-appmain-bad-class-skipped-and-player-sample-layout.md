# 284 · **"一个坏职业不丢整场"**、`custom1..5` 的键、`CodolWorldPlayerSampleV1` 的 192 字节

## 一、范围

本报告学习 `Appmain.cpp` 3020–3240 行。

## 二、**"一个坏职业跳过而不致命"**（本组最重要的一段）

```php
std::uint32_t memberClassMask{};
for (uint32_t classIndex = 0; classIndex < sessionMember.loadout.classes.size(); ++classIndex)
{
    if (!(sessionMember.loadout.classMask & (1u << classIndex))) continue;
    const auto loadout = Bindings.resolveSessionWeaponLoadout(sessionMember.loadout, classIndex);
    const auto perks   = Bindings.resolveSessionPerks(sessionMember.loadout, classIndex);
    const auto offhands= Bindings.resolveSessionEquipment(sessionMember.loadout, classIndex);
    if (!offhands)
        logGameServer("equipment resolution failed xuid=" + N + " class=" + N);
    if (!loadout || !perks || !offhands)
    {
        if (failedClassIndex < 0) failedClassIndex = (int32)classIndex;
        const auto &loadoutClass = sessionMember.loadout.classes[classIndex];
        logGameServer("loadout class skipped xuid=" + N + " class=" + N +
            " primaryItem=" + N + " secondaryItem=" + N +
            " failure=" + loadoutResolveFailureName(Bindings.loadoutResolveFailure()));
        continue;                    // ← 【跳过，不 break】
    }
    preparedMember.loadouts.emplace("custom" + (classIndex + 1), *loadout);
    preparedMember.perks.emplace(...);
    preparedMember.equipment.emplace(...);
    preparedMember.offhands.emplace(...);
    memberClassMask |= 1u << classIndex;
}
if (!memberClassMask)
{
    logGameServer("loadout resolution failed xuid=" + N + " class=" + N);
    failSession(WeaponLoadoutFailed, failedClassIndex, resolvedClassMask);
    memberResolutionFailed = true;
    break;
}
```

### 2.1 **三层**

```text
一个职业失败   ⇒ continue（跳过）
所有职业都失败 ⇒ failSession + break（整场失败）
否则           ⇒ 用成功的那些职业
```

### 2.2 而 `failedClassIndex` 只记**第一个**

```php
if (failedClassIndex < 0) failedClassIndex = (int32)classIndex;
```

**⇒ 与 §245 的 `failedIndex` 只记第一个同族。**

### 2.3 而失败日志的**四个量**

```text
xuid
class
primaryItem / secondaryItem   ← 【原始 itemId，不是解析后的】
failure                        ← loadoutResolveFailureName
```

**⇒ 而 `primaryItem` 是 `loadoutClass.weapons[0].itemId`（原始）。**

**⇒ 所以日志同时给出**输入**与**失败原因**。**

### 2.4 而 `equipment resolution failed` 是**单独的日志**

```php
if (!offhands) logGameServer("equipment resolution failed ...");
```

**⇒ 在统一失败日志**之前**打。**

**⇒ 所以一个装备失败会产生**两行**日志。**

**⚠ 可能是有意的（区分来源），但有点冗余。**

### 2.5 而**四个 `map` 的键**

```cpp
preparedMember.loadouts.emplace("custom" + std::to_string(classIndex + 1), *loadout);
preparedMember.perks.emplace(...同上...);
preparedMember.equipment.emplace(...同上...);
preparedMember.offhands.emplace(...同上...);
```

**⇒ 键是 `"custom1"`..`"custom5"`（`classIndex + 1`）。**

**⇒ 与 §257 的 `selectedLoadout[6] - '1'` **完全一致** ✓**

**⇒ 所以四个 map 用同一个键空间。**

### 2.6 而 `equipment` 存的是**原始的结构**

```cpp
preparedMember.equipment.emplace("custom" + N, sessionMember.loadout.classes[classIndex].equipment);
```

**⇒ 而 `offhands` 存的是**解析后**的 `*offhands`。**

**⇒ 所以同一份数据存了两次（原始 + 解析后）。**

**⚠ 一处冗余** —— 但可能因为下游需要两者。

## 三、`configureBooking` 的**四项 + 一个代际要求**

```php
if (!configureBooking(
        session.bookingCommand.c_str(),
        session.booking,
        session.matchRules,
        CodolGameServer::SvConfigStringGenerationRequirement::CurrentGeneration))
{
    logGameServer("booking configuration failed request=" + requestId);
    failSession(ConfigureBookingFailed, -1, resolvedClassMask);
    continue;
}
```

### 3.1 四项

```text
bookingCommand   命令串
booking          预定
matchRules       规则
generationRequirement  【CurrentGeneration】
```

### 3.2 而 `CurrentGeneration` 与 §279 的默认 `NewGeneration`

**⇒ 两个不同的要求**：

```text
NewGeneration        需要新代际（默认）
CurrentGeneration    用当前代际
```

**⇒ 而这里用 `CurrentGeneration`** —— 因为已经在会话链里建立了代际（`DedicatedMapGeneration`）。

**✓ 与 §282 的"同地图代际复用"一致。**

### 3.3 而 `failSession(ConfigureBookingFailed, -1, resolvedClassMask)`

**⇒ 传了 `resolvedClassMask`。**

**⇒ 因为到这里 classMask 已经解析完。**

## 四、`PreparedLoadouts` 的**六个字段**

```php
{
    const std::lock_guard lock(LoadoutMutex);
    prepared.requestSequence = LoadoutPrepareRequestSequence;
    prepared.sessionGeneration = queued.requestId;
    PreparedLoadouts = std::move(prepared);
    LoadoutPreparation.currentCharacter = (int32)session.members.front().loadout.characterIndex;
    LoadoutPreparation.resolvedClassMask = resolvedClassMask;
    LoadoutPreparation.registeredClassMask = resolvedClassMask;
    ++LoadoutPreparation.attemptCount;
}
ActiveDedicatedSession = session;
```

### 4.1 七项

```text
prepared.requestSequence      = LoadoutPrepareRequestSequence
prepared.sessionGeneration    = queued.requestId
PreparedLoadouts              = move(prepared)
LoadoutPreparation.currentCharacter  = members.front().characterIndex
LoadoutPreparation.resolvedClassMask = resolvedClassMask
LoadoutPreparation.registeredClassMask = resolvedClassMask
++LoadoutPreparation.attemptCount
```

### 4.2 而**两个 classMask 被设成同一个值**

```cpp
resolvedClassMask    = resolvedClassMask;
registeredClassMask  = resolvedClassMask;
```

**⇒ 所以这里它们**总是相等**。**

**⚠ 而 §271 的定义里它们是**两个不同的阶段**（解析 vs 注册）。**

**⇒ 所以"注册"可能发生在**后面**（游戏线程），而这里只是**乐观地**设成相同。**

**⇒ 待读 `registeredClassMask` 的更新点。**

### 4.3 而 `ActiveDedicatedSession = session` 在锁外

**⚠ 而它不在 `LoadoutMutex` 或 `DedicatedControlMutex` 的保护下。**

**⇒ 可能是一个竞态**（如果其他线程读它）。

**⇒ 但从设计看，`processDedicatedControlMessages` 只在游戏线程跑。**

## 五、**`deferredSessions` 的回填**

```php
if (!deferredSessions.empty())
{
    const std::lock_guard lock(DedicatedControlMutex);
    while (!deferredSessions.empty())
    {
        DedicatedSessionStarts.push_front(std::move(deferredSessions.back()));
        deferredSessions.pop_back();
    }
}
```

### 5.1 三层

```text
持 DedicatedControlMutex
从 deferredSessions 的【尾部】取
push_front 到 DedicatedSessionStarts
```

**⇒ 所以**保持顺序**：`

```text
deferred = [A, B, C]
取 C → push_front ⇒ stays = [C]
取 B → push_front ⇒ stays = [B, C]
取 A → push_front ⇒ stays = [A, B, C]
```

**✓ 顺序保持。**

### 5.2 而"下一轮会重新处理"

**⇒ 所以延后的会话排在**队列最前**（因为 `push_front`）⇒ 优先。**

**✓ 一个正确的"重试优先"设计。**

## 六、`commands` 的**最后处理**

```php
for (const auto &command : commands)
    static_cast<void>(CODOL_GameServerConfigureBooking(command.c_str()));
```

### 6.1 **在会话之后**

**⇒ 所以 `Booking` 命令串在**所有**会话处理之后。**

**⇒ 与 §280 的"Booking 是最后兜底"一致** ✓

### 6.2 而返回值被忽略

```cpp
static_cast<void>(...)
```

**⇒ 所以 `CODOL_GameServerConfigureBooking` 的失败**不记录**。**

**⚠ 一处缺失的错误记录** —— 而 §281 里 `commands` 的队列本身也没有失败日志。

**⇒ 所以"命令串失败的路径是静默的"。**

## 七、`CodolWorldPlayerSampleV1` 的**四十四个字段 / 192 字节**

```php
struct CodolWorldPlayerSampleV1
{
    uint32 structSize, schemaVersion, frameNumber, serverTime;
    uint32 userCmdValid, userCmdCommandTime, userCmdButtons;
    array<uint32,3> userCmdAngles;
    uint32 userCmdWeapon, userCmdOffHandIndex, userCmdLastWeaponAltModeSwitch;
    int32 userCmdForwardMove, userCmdRightMove;
    uint32 playerCommandTime;
    array<float,3> playerOrigin, playerVelocity;
    uint32 groundEntityNum, gravity, speed;
    float moveSpeedScaleMultiplier;
    uint32 pmTime, pmFlags, jumpTime;
    float jumpOriginZ;
    uint32 eFlags, otherFlags;
    float viewHeightCurrent;
    int32 viewHeightTarget, viewHeightLerpTarget, viewHeightLerpTime;
    uint32 viewHeightLerpDown;
    uint32 weaponValid, currentWeaponAssetIndex;
    int32 weaponTime, weaponDelay;
    uint32 weaponState, weaponAnim, clipAmmo, weaponType, fireType;
    uint32 definitionFireDelay, definitionFireTime;
};
static_assert(sizeof(CodolWorldPlayerSampleV1) == 192);
static_assert(alignof(CodolWorldPlayerSampleV1) == alignof(uint32));
```

### 7.1 六组

```text
头部（4）      structSize, schemaVersion, frameNumber, serverTime
usercmd（10）  userCmdValid, CommandTime, Buttons, Angles[3], Weapon,
               OffHandIndex, LastWeaponAltModeSwitch, ForwardMove, RightMove
玩家（5）      playerCommandTime, Origin[3], Velocity[3]（算 3 个字段）
移动（5）      groundEntityNum, gravity, speed, moveSpeedScaleMultiplier, pmTime
跳跃（2）      pmFlags, jumpTime, jumpOriginZ（3 个）
标志（2）      eFlags, otherFlags
视线（5）      viewHeightCurrent, Target, LerpTarget, LerpTime, LerpDown
武器（10）     weaponValid, currentWeaponAssetIndex, weaponTime, weaponDelay,
               weaponState, weaponAnim, clipAmmo, weaponType, fireType,
               definitionFireDelay, definitionFireTime
```

**⇒ 我数到约 45 个字段。**

### 7.2 **`sizeof == 192` 与 `alignof == 4`**

**⇒ 两个 `static_assert`。**

**⇒ 所以 `192 = 48 个 uint32`。**

**⇒ 而字段数约 45 ⇒ 数组字段贡献额外。**

**⇒ 算一下**：`userCmdAngles[3]` 贡献 2 额外、`playerOrigin[3]` 贡献 2、`playerVelocity[3]` 贡献 2 ⇒ 45 + 6 = 51？**

**⚠ 51 × 4 = 204 ≠ 192。**

**⇒ 所以我数多了。**

**⇒ 实际应该是 48 个 4 字节槽。**

### 7.3 而 `alignof == 4` 意味着**没有 8 字节字段**

**✓ 全是 4 字节或数组。**

### 7.4 `userCmdLastWeaponAltModeSwitch`

**⇒ 与 §243 的"`lastWeaponAltModeSwitch` NEVER MOVES"**相关**！**

**⇒ 那个探针的结论是这个字段**从不移动**。**

**⇒ 而这里它被暴露在采样结构里。**

**⇒ 所以控制 socket 能验证"它是否移动"。**

## 八、`CodolWorldPlayerSampleV2` 的**额外二十四个字段 / 352 字节**

```php
struct CodolWorldPlayerSampleV2
{
    CodolWorldPlayerSampleV1 base{};         // 192
    uint32 pmType;
    array<float,3> viewAngles, deltaAngles, ladderVector;
    uint32 sprintButtonUpRequired, sprintDelay, lastSprintStart, lastSprintEnd, sprintStartMaxLength;
    float mantleYaw;
    uint32 mantleTimer, mantleTransitionIndex, mantleFlags;
    float weaponPositionFraction;
    array<uint32,2> weaponAnim;
    array<int32,2> weaponTime, weaponDelay;
    array<uint32,2> weaponState, weaponHandFlags, weaponShotCount;
    uint32 legsTimer, legsAnim, torsoTimer, torsoAnim;
    float proneDirection, proneDirectionPitch, proneTorsoPitch;
    uint32 bobCycle;
};
static_assert(sizeof(CodolWorldPlayerSampleV2) == 352);
static_assert(offsetof(CodolWorldPlayerSampleV2, pmType) == 192);
```

### 8.1 **`352 - 192 = 160` 额外字节 = 40 个 uint32**

### 8.2 六组额外

```text
pmType                    1
三个角度向量              9
冲刺（5）                 5
攀爬（4）                 mantleYaw, Timer, TransitionIndex, Flags
武器（2 × 5 + 1）         weaponPositionFraction + 5 个 2 元组
腿/躯干（4）              legsTimer, legsAnim, torsoTimer, torsoAnim
趴（3）                   proneDirection, Pitch, TorsoPitch
bobCycle                  1
```

**⇒ 1 + 9 + 5 + 4 + 1 + 10 + 4 + 3 + 1 = 38。**

**⇒ 而需要 40。**

**⚠ 差 2。**

**⇒ 可能 `weaponAnim` 等五个 2 元组是 10 个而 `weaponPositionFraction` 是 1 ⇒ 11。**

**⇒ 1 + 9 + 5 + 4 + 11 + 4 + 3 + 1 = 38。**

**⇒ 仍差 2。**

**⇒ 可能有对齐填充或者我数错。**

### 8.3 而 `offsetof(pmType) == 192` 确认了 `base` 是精确的 192

**✓ 所以 V2 是 V1 的**严格扩展**。**

### 8.4 而 V2 里的**九个 `float[3]`**

```text
viewAngles
deltaAngles
ladderVector
```

**⇒ 三个向量 = 9 个 float。**

**⇒ 而 §278 的 `.viewAngles` 只有**一个**（来自 `worldPlayerState->viewAngles`）。**

**⇒ 所以 V2 暴露更多。**

### 8.5 而**五个 2 元组**

```text
weaponAnim[2]
weaponTime[2]
weaponDelay[2]
weaponState[2]
weaponHandFlags[2]
weaponShotCount[2]
```

**⇒ **六个**（我数六）。**

**⇒ 六 × 2 = 12。**

**⇒ 重新算**：1 + 9 + 5 + 4 + 1 + 12 + 4 + 3 + 1 = 40** ✓**

**✅ 正好 40！**

### 8.6 所以 V2 的额外 40 个槽完全对上了

**⇒ 这验证了结构定义的完整性。**

### 8.7 而"两个武器"的 2 元组

**⇒ 因为 `weaponAnim`/`weaponTime`/`weaponDelay`/`weaponState`/`weaponHandFlags`/`weaponShotCount` 各有两个元素 ⇒ **双持或主/副武器**。**

**⇒ 与 §243 的 `weaponClasses[0]` 的"主/副"概念相关。**

## 九、关键结论

1. **一个坏职业 `continue`，全部坏才 `failSession`** —— "不扔整场"。
2. **`failedClassIndex` 只记第一个**。
3. **失败日志同时给出输入（itemId）与原因（failure name）**。
4. **四个 map 的键是 `"custom1".."custom5"`（`classIndex + 1`）** —— 与 §257 一致。
5. **`equipment` 存原始而 `offhands` 存解析后** —— 一份数据两份。
6. **`configureBooking` 用 `CurrentGeneration`** 而不是默认的 `NewGeneration`。
7. **`resolvedClassMask == registeredClassMask` 在这里总是相等** —— 与 §271 的"两阶段"定义**不一致**。
8. **`deferredSessions` 的 `push_front` 保持顺序且优先重试**。
9. **`commands` 在最后处理且返回值被忽略** —— 命令串失败是**静默的**。
10. **`CodolWorldPlayerSampleV1` = 192 字节 / 48 槽**，`alignof == 4`。
11. **`CodolWorldPlayerSampleV2` = 352 字节** = V1 + 40 槽，`offsetof(pmType) == 192` ✓
12. **V2 的额外字段正好 40 槽**（1+9+5+4+1+12+4+3+1）算术闭合。
13. **`userCmdLastWeaponAltModeSwitch` 被暴露** —— 可验证 §243 的"从不移动"结论。

## 十、未闭合点

- `registeredClassMask` 的实际更新点。
- `codolWorldPlayerSampleV1` 的字段数与 48 槽的精确对应。
- `commands` 命令串失败是否真的静默。
- `Appmain.cpp` 3240 行之后未读取。
