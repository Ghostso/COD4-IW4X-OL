# 328 · **`sub_675E70` 对 `changeHint==3` 字段从不到达值比较**、`compassRadar` 的"默认 1 在第一帧断言"、`rewardIds` 的五个

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 2990–3190 行。

## 二、**`sub_675E70` 的"从不到达值比较"**（本组最重要的一段）

### 2.1 那段

```php
// NO originChanged / velocityChanged / bobCycleChanged /
// movementDirChanged HERE ON PURPOSE. They are changeHint==3
// fields, and sub_675E70 returns the MODE for those without ever
// reaching its value comparison -- in either mode. A change flag
// for them would be a fifth wheel that reads like a decision.
```

### 2.2 五层

```text
1. **刻意没有那四个变化标志**
2. ⇒ 它们是 **`changeHint == 3`** 字段
3. ⇒ **而 `sub_675E70` 对那些【返回模式】而【从不到达它的值比较】—— 在任一模式下**
4. ⇒ **所以一个变化标志对它们会是一个看起来像决策的第五个轮子**
```

### 2.3 **"一个看起来像决策的第五个轮子"**

**✅ 一个**精确的表述** —— 一个**未被使用**的 `bool` 会让人以为它在影响决策。**

**⇒ 与 §323 的"含义未知而刻意不猜"、§319 的"三个未解释字段"同族**（第二十五次）。

### 2.4 而"**在任一模式下**"

**⇒ 三层**：

```text
1. `sub_675E70` 有一个"模式"概念
2. ⇒ 它**在任一模式下**都对 `changeHint==3` 直接返回模式
3. ⇒ **所以值比较从未发生**
```

**✅ 所以那四个字段**无条件发绝对值**。**

## 三、`viewAngleChanged` 与 `deltaAngleChanged` 的**三项**

```cpp
const std::array viewAngleChanged{
    state.viewAngles[0] != baselineViewAngles[0],
    state.viewAngles[1] != baselineViewAngles[1],
    state.viewAngles[2] != baselineViewAngles[2],
};
const std::array deltaAngleChanged{ ... 同样的三项 ... };
const auto anyViewAngleChanged = any_of(viewAngleChanged, identity);
const auto anyDeltaAngleChanged = any_of(deltaAngleChanged, identity);
```

**⇒ 三层：三项 + 一个 `any_of` 汇总。**

**✅ 与 §268 的"三个角度"配合。**

## 四、`weaponAnimChanged` 等的**五个 2 元组**（本组第二重要）

```cpp
const std::array weaponAnimChanged{ ... 2 项 ... };
const std::array weaponStateChanged{ ... 2 项 ... };
const std::array weaponTimeChanged{ ... 2 项 ... };
const std::array weaponDelayChanged{ ... 2 项 ... };
const std::array weaponRestrictKickTimeChanged{ ... 2 项 ... };
```

**⇒ 五个 2 元组。**

**✅ 与 §284 的"六个 2 元组"（`weaponAnim`/`weaponTime`/`weaponDelay`/`weaponState`/`weaponHandFlags`/`weaponShotCount`）**部分重叠**。**

**⇒ 而这里没有 `weaponHandFlags` 与 `weaponShotCount` 的 `Changed`（它们在后面）。**

**✅ 所以总共**七个 2 元组**。**

## 五、`compassRadar` 的**"默认 1 在第一帧断言"**（本组第三重要）

### 5.1 那段

```php
// The demo's baseline for a client's FIRST snapshot is zero, so a
// default of 1 asserts on frame one exactly as retail's does.
const auto baselineCompassRadar =
    baseline ? baseline->compassRadarEnabled : std::uint8_t{};
```

### 5.2 三层

```text
1. **demo 里一个客户端【第一个】快照的基线是零**
2. ⇒ 所以**一个默认值 1 会在第一帧断言，正是零售所做的**
3. ⇒ 所以"无基线 ⇒ 零"这个默认**恰好**给出与零售相同的结果
```

**✅ 一个**巧妙的默认值对齐**。**

**⚠ 而"默认 1"是 `compassRadarEnabled` 的**字段默认**（在 `SvPlayerState` 里）而不是基线的默认。**

**⇒ 所以：**

```text
state.compassRadarEnabled  默认 1
baseline（null）            0
⇒ 变化 ⇒ 第一帧断言
```

**✅ 正确。**

## 六、`rewardIds()` / `rewardTargets()` 的**五个**

```cpp
const auto rewardIds = state.rewardIds();
const auto rewardTargets = state.rewardTargets();
const auto oldRewardIds = baseline ? baseline->rewardIds() : std::array<std::uint8_t, 5>{};
const auto oldRewardTargets = baseline ? baseline->rewardTargets() : std::array<std::uint8_t, 5>{};
const auto rewardsChanged = rewardIds != oldRewardIds || rewardTargets != oldRewardTargets;
```

### 6.1 而 `std::array<uint8_t, 5>`

**⇒ 五个。**

**✅ 与 §317 的 `PlayerStateRewardIdFirstField = 126` 与 `PlayerStateRewardTargetFirstField = 131`**配合：**

```text
126..130   rewardIds（5 个）
131..135   rewardTargets（5 个）
```

**✅ 所以 5 + 5 = 10 个字段。**

### 6.2 而 **`rewardActionType` / `rewardActionWeapon`** 是**另一对**

```cpp
const auto oldRewardActionType = baseline ? baseline->rewardActionType : 0;
const auto oldRewardActionWeapon = baseline ? baseline->rewardActionWeapon : 0;
const auto rewardActionChanged = state.rewardActionType != oldRewardActionType ||
    state.rewardActionWeapon != oldRewardActionWeapon;
```

**⇒ 而 §317 的 `PlayerStateRewardActionTypeField = 187` 与 `PlayerStateRewardActionWeaponField = 204`。**

**✅ 所以"10 个槽 + 2 个动作"两套。**

## 七、`perks` 的**三个**

```cpp
const std::array perksChanged{
    state.perks[0] != baselinePerks[0],
    state.perks[1] != baselinePerks[1],
    state.perks[2] != baselinePerks[2],
};
```

**⇒ 三个。**

**✅ 与 §317 的 `PlayerStatePerkField0/1/2 = 123/124/125`**完全一致** ✓**

## 八、`numbersChanged` 的**四项**

```cpp
bool numbersChanged = false;
if (numbers)
    for (unsigned slot = 0; slot < numbers->size(); ++slot)
        numbersChanged |= (*numbers)[slot].sequence !=
            (baselineNumbers ? (*baselineNumbers)[slot].sequence : 0);
```

**⇒ 三层**：

```text
1. 只在 `numbers` 非空时比较
2. ⇒ **只比较 `sequence`**（不是整个结构）
3. ⇒ 而基线缺失时用 0
```

**✅ 所以"伤害数字"的判据是**序号变化**。**

## 九、`injuriesChanged` 的**整体比较**

```cpp
const SvZombieInjuryRing emptyInjuries{};
const auto injuriesChanged = (injuries ? *injuries : emptyInjuries) !=
    (baselineInjuries ? *baselineInjuries : emptyInjuries);
```

**⇒ 三层**：

```text
1. 两个都为空 ⇒ 空 == 空 ⇒ false
2. 一个为一个空 ⇒ 比较
3. ⇒ **整体比较**（不是逐项）
```

**⚠ 而 `numbersChanged` 是**逐项**。**

**⇒ 两个环用**两种判据**。**

**✅ 一处不一致（但可能因为 `SvZombieInjuryRing` 有 `operator!=`）。**

## 十、`hudElemsChanged` 的**两个数组**

```cpp
const auto hudElemsChanged = state.hudCurrent != baselineHudCurrent ||
    state.hudArchival != baselineHudArchival;
```

**⇒ 三层**：

```text
hudCurrent  31 项
hudArchival 31 项
⇒ 任一变化 ⇒ 变化
```

**✅ 所以**两组 HUD 数组**（当前与归档）。**

**⚠ 而 §325 的 `writeHudElems` 只处理 `elems` 一个数组。**

**⇒ 所以 `hudArchival` 可能**在别处写**。**

## 十一、约 60 个 `*Changed` 布尔

**⇒ 而从 §327 的约 90 个 `baseline*` 推导，这里约**60 个 `*Changed`**。**

**⚠ 而有些字段**没有** `Changed`（那四个 `changeHint==3` 的）。**

## 十二、`oldRewardIds` 的**命名不一致**

```cpp
const auto oldRewardIds = ...        // ← 【old】
const auto oldRewardTargets = ...    // ← 【old】
const auto oldRewardActionType = ... // ← 【old】
```

**⚠ 而其它都是 `baseline*`。**

**⇒ 四处用 `old*` 而其余用 `baseline*`。**

**✅ 一处命名不一致。**

## 十三、关键结论

1. **⭐ `sub_675E70` 对 `changeHint==3` 字段**返回模式而从不到达值比较**（在任一模式下）。
2. **"一个变化标志对它们会是一个看起来像决策的第五个轮子"** —— 一个精确的表述。
3. **五个 + 两个 = 七个武器 2 元组 `*Changed`。**
4. **`compassRadar` 的"默认 1 在第一帧断言"** —— 因为 demo 的第一快照基线是零。
5. **`rewardIds`/`rewardTargets` 各五个**（字段 126..130 与 131..135）。
6. **`rewardActionType`/`Weapon` 是另一对**（187/204）。
7. **`perks` 三个**（123/124/125）。
8. **`numbersChanged` 逐项比 `sequence`；`injuriesChanged` 整体比较** —— 两环两种判据。
9. **`hudElemsChanged` 两个数组**（`hudCurrent` / `hudArchival` 各 31）。
10. **约 60 个 `*Changed` 布尔** 而四个字段刻意没有。
11. **四处用 `old*` 而其余用 `baseline*`** —— 命名不一致。

## 十四、未闭合点

- `hudArchival` 在哪写。
- `SvZombieInjuryRing` 的 `operator!=` 语义。
- `sub_675E70` 的"模式"概念。
- `sv_snapshot_mp.cpp` 3190 行之后未读取（1.47 MB，进度 21%）。
