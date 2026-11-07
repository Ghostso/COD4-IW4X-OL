# 441 · **"`getvelocity` 发货了而 `getorigin` 没有，那读起来像一个疏忽而不是一个决定"** —— `getentarray` 的数组返回、`getorigin` 的两分支、以及 `pmFlags` 的 `uint32` 上界

## 一、范围

本报告学习 `sv_script_builtin_mp.cpp` 1040–1380 行（`setMapGameObjects` 的收尾、`getEntArray` 的 `SvScriptObjectArray`、`validateEntityMethod`、`getOrigin` 的两分支、六个 scripted 系列、`setShellshock`、`setObjective` 的开头）。

## 二、**"`getvelocity` 发货了而 `getorigin` 没有"**（本组最重要的一段）

### 2.1 那段

```php
// WHERE IS IT? The one question the script layer could not ask.
//
// `getvelocity` shipped and `getorigin` did not, which reads like an oversight
// rather than a decision -- they are adjacent fields of the same struct. The
// absence is load-bearing though: without it a script cannot place anything
// relative to anything else, so loot could only ever go at coordinates typed
// into the source by hand, and the play-area circle could not test whether a
// player is inside it. Both of those are BattleCity.
//
//     local where = codol.call("method:getorigin", player)
//     where[1], where[2], where[3]   -- x, y, z
//
// TAKES A PLAYER OR AN ENTITY, dispatched on the receiver's kind rather than
// split into two names. Callers do not care which they are holding -- "put loot
// near this thing" is the same sentence either way -- and the two validators
// already return the right error for the wrong receiver.
//
// The player branch reports playerState.origin, which is the pmove result the
// client is told about, NOT the entity's currentOrigin. They agree while a
// player is alive; playerState is the one that stays correct across a respawn.
```

### 2.2 二十四层

```text
1. **它在哪？脚本层【不能问的唯一问题**】**
2. ⇒ **`getvelocity` 【发货了**】而 `getorigin` 【没有**】**
3. ⇒ **⇒ 那读起来像【一个疏忽**】而不是【一个决定**】**
4. ⇒ **⇒ 因为【它们是【同一个结构的相邻字段**】】**
5. ⇒ **⚠ 而【那个缺席是【承重的**】】**
6. ⇒ **⇒ 没有它，一个脚本【不能【把任何东西相对任何东西放置**】】**
7. ⇒ **⇒ 所以【拾取【只能在源码里【手打坐标**】】**
8. ⇒ **⇒ 而【游戏区域圆【不能测试一个玩家是否在它里面**】】**
9. ⇒ **⇒ 两个都是 BattleCity**
10. ⇒ **用法示例**：`local where = codol.call("method:getorigin", player)` ⇒ `where[1..3] = x,y,z`
11. ⇒ **接受一个【玩家或一个实体**】，在【接收者的 kind 上分派**】而不是【拆成两个名字**】**
12. ⇒ **⇒ 因为【调用者【不在乎它拿着哪个**】】**
13. ⇒ **（"把拾取放在这个东西附近"【两边是同一个句子**】）**
14. ⇒ **⇒ 而【两个验证器【已经为错误的接收者返回正确的错误**】】**
15. ⇒ **玩家分支【报告 `playerState.origin`**】**
16. ⇒ **那【是客户端被告知的 pmove 结果**】，**不是**实体的 `currentOrigin`**
17. ⇒ **⇒ 它们【在玩家活着时一致**】**
18. ⇒ **⇒ 而 `playerState` 是【跨越一次重生仍然正确**】的那个**
```

### 2.3 ⭐⭐⭐ **"那个缺席是承重的"**

**✅ 这是本报告里**最重要的一条"缺席也是设计**。**

**⇒ 三层**：
```text
观察：**`getorigin` 缺失**
朴素解读：**一个疏忽**（因为 `getvelocity` 有而它们是相邻字段）
真正解读：**那个缺席是【承重的**】⇒ **它阻塞了两个 BattleCity 特性**
```

**✅ 与 §416 的"`perks` 三个字段从未写过 ⇒ 从来没有一个 perk 图标出现过"**同族（**第三次"一个缺席的后果**）。

**⇒ 三层**：
```text
§400  **`battery_multiplier` 缺失 ⇒ 除零**
§416  **`perks` 从未写 ⇒ 无图标**
§441  **`getorigin` 缺失 ⇒ 拾取只能手打坐标**
⇒ **⇒ 三次"一个缺失的后果**】
```

**✅ ⭐⭐⭐ **一个"缺失的后果"的三例表**。

**⚠ 而"一次疏忽 vs 一个决定"⇒ **一个极精确的自我诊断**。**

**✅ 与 §404 的"这是一个窄回退，不是一个诊断"**同族（**第三次"对自身行为的定性**）。

**⇒ 三层**：
```text
§404  **"窄回退，不是诊断"**
§435  **"缩短窗口，不关闭它"**
§441  **"读起来像一个疏忽而不是一个决定"**
⇒ **⇒ 三次"对自己代码的诚实定性**】
```

**✅ ⭐⭐ **一个"诚实定性"的三例表**。

### 2.4 而**"在接收者的 kind 上分派而不是拆成两个名字"**

```cpp
if (call.self && call.self->kind == SvScriptObjectKind::Entity)
{
    SvEntityHandle handle;
    if (auto error = validateEntityMethod(world, call, 0, handle)) return std::move(*error);
    const auto entity = world.entity(handle);
    if (!entity) return failure(ObjectNotFound, "getorigin entity does not exist");
    return success(entity->currentOrigin);
}
std::optional<SvPlayerState> playerState;
if (auto error = validatePlayerMethod(world, call, 0, playerState)) return std::move(*error);
return success(playerState->origin);
```

**⇒ 十二层**：
```text
1. **`kind == Entity` ⇒ 实体分支**
2. ⇒ **`kind != Entity` ⇒ 玩家分支**（**或失败**）
3. ⇒ **⇒ 所以【一个名字两个分支**】**
4. ⇒ **而【两个验证器【各自返回正确的错误**】】**
5. ⇒ **⇒ 所以【一个非实体非玩家的 self ⇒ `validatePlayerMethod` 的 `InvalidSelf`**】**
```

### 2.5 ⭐⭐⭐ **"两个验证器已经为错误的接收者返回正确的错误"**

**✅ 与 §438 的"五道检查五个错误码"**同族（**第二次"错误码正确分配"）。

**⇒ 三层**：
```text
若【只有一个验证器**】⇒ **必须自己检查 kind**
若【有两个验证器**】⇒ **`kind` 分派后各自验证**
⇒ **⇒ 所以【后者【少一个检查**】】
```

**✅ ⭐⭐ **"两个验证器消除了一个检查"** —— 与 §406 的"四条路径一个出口"**不同（这是**一个复用的好处**）。

**⚠ 而"`playerState.origin` vs `entity->currentOrigin`"⇒ **一个关键的区分**。**

**⇒ 八层**：
```text
`playerState.origin` ⇒ **pmove 的结果** ⇒ **客户端被告知的**
`entity->currentOrigin` ⇒ **实体自己的**
⇒ **⇒ 活着时一致**，**重生后只有前者正确**
```

**✅ ⭐⭐⭐ **"跨一次重生仍然正确的那个"** —— 与 §422 的"`setPlayerScriptedPosition` 在 pmove 之后重新应用"**不同（这是**一个读的选择**）。

**✅ 与 §440 的"`snapshot()` vs `playerState()`"**同族（**第三次"两个数据源，两个时机"）。

**⇒ 三层**：
```text
§413  **`snapshot()` 在 `endFrame` 前空**
§440  **`playerState()` 是活的**
§441  **`playerState.origin` 跨重生正确而 `entity->currentOrigin` 不是**
⇒ **⇒ 三次"选择一个数据源**】
```

**✅ ⭐⭐ **一个"数据源选择"的三例表**。

## 三、**`getEntArray` 的 `SvScriptObjectArray`**（本组第二重要）

### 3.1 那段

```cpp
SvScriptObjectArray objects;
for (const auto handle : world.findMapEntities(*value, *key))
{
    objects.push_back({
        .kind = SvScriptObjectKind::Entity,
        .id = handle.entityNum,
        .entityGeneration = handle.generation,
    });
}
return success(std::move(objects));
```

**⇒ 十二层**：
```text
1. **`SvScriptObjectArray` 是一个【独立的类型**】**
2. ⇒ **⇒ 所以【`SvScriptValue` 【不是**】完全无列表**】
3. ⇒ **⇒ 它有【至少一个**"对象数组"类型**
4. ⇒ **而【§438 说的"没有表类型或字符串列表类型**】】**
5. ⇒ **⇒ 所以【两者【不矛盾**】：无【表/字符串列表】，而有【对象数组**】】
```

### 3.2 ⭐⭐⭐ **"没有表类型或字符串列表类型"与"有对象数组"不矛盾**

**✅ 这是本报告里**对 §438 的一个精确化**。**

**⇒ 三层**：
```text
§438  **`SvScriptValue` 没有表或字符串列表类型**
§441  **而它有 `SvScriptObjectArray`**
⇒ **⇒ 所以【两种列表：字符串的有**（用逗号串）**，对象的有**（用数组类型）**
```

**✅ ⭐⭐⭐ **"两种列表，两种绕法"** —— 与 §440 的"逗号串编码整数列表"**互补**。

**⇒ 三层**：
```text
字符串列表 ⇒ **逗号串**（§440 的 `"1,3,5"`）
对象列表 ⇒ **`SvScriptObjectArray`**（§441）
⇒ **⇒ 所以【字符串的用编码，对象的用类型**】
```

**✅ ⭐⭐ **"字符串的用编码，对象的用类型"** —— 本报告的一个技术要点。

**⚠ 而"`.entityGeneration = handle.generation`"⇒ **一个代次安全**。**

**⇒ 三层**：
```text
`id = handle.entityNum`
`entityGeneration = handle.generation`
⇒ **⇒ 所以【一个对象【携带它被取出的那个代次**】】
⇒ **⇒ 而 `validateEntityMethod` 【要求 `entityGeneration` 非零**】（§441 三.3）
```

**✅ 与 §424 的"代次 `0` 的有效性"**——**这里 `entityGeneration` 必须非零**。

**⇒ 三层**：
```text
§424  **`SvEntityHandle{ num, 0 }` ⇒ 代次 `0` ⇒ 静默不匹配**
§441  **`!call.self->entityGeneration ⇒ InvalidSelf`**
⇒ **⇒ 所以【§424 的缺陷在这里【被一个检查挡住了**】】
```

**✅ ⭐⭐⭐ **"§424 的缺陷在这里被一个检查挡住了"** —— 一个跨报告的防御闭合。

### 3.3 而**`validateEntityMethod` 的五道**

```cpp
if (call.arguments.size() != expectedArgumentCount) ⇒ InvalidArgumentCount
if (!call.self)                                      ⇒ MissingSelf
if (call.self->kind != Entity || !call.self->entityGeneration) ⇒ InvalidSelf
handle = { .entityNum = call.self->id, .generation = *call.self->entityGeneration };
if (!world.entity(handle))                           ⇒ ObjectNotFound
```

**⇒ 六层**：
```text
1. **参数个数**
2. ⇒ **`self` 存在**
3. ⇒ **`kind == Entity` 【且 `entityGeneration` 非零**】**
4. ⇒ **组装 `handle`**
5. ⇒ **`world.entity(handle)` 存在**
⇒ **⇒ 同 `validatePlayerMethod` 的【五道**】，但第 3 道多一个代次检查**
```

**✅ ⭐⭐ **"与 `validatePlayerMethod` 五道同形，但第 3 道多一个代次"** ⇒ **一个对称的验证器对**。

**⇒ 三层**：
```text
`validatePlayerMethod` ⇒ `kind == Player` + `playerState` 存在 + `Playing`
`validateEntityMethod` ⇒ `kind == Entity` + **`entityGeneration` 非零** + `world.entity` 存在
⇒ **⇒ 两个对称的验证器**
```

**✅ ⭐⭐ **"一个对称的验证器对"** —— 而**两者都是五道五码**。

## 四、**`setScriptedPosition` 的五个参数与两个上界**（本组第三重要）

```cpp
validatePlayerMethod(world, call, 5, playerState)
for (axis 0..2) { double, isfinite ⇒ origin[axis] }
pmType  = get_if<int64_t>(arguments[3])
pmFlags = get_if<int64_t>(arguments[4])
if (!pmType || !pmFlags || *pmType < 0 || *pmType > UINT8_MAX || *pmFlags < 0 ||
    static_cast<std::uint64_t>(*pmFlags) > UINT32_MAX) ⇒ InvalidArgumentValue
```

**⇒ 十四层**：
```text
1. **五个参数**：三个 `double` 位置 + 一个 `pmType` + 一个 `pmFlags`
2. ⇒ **三个位置【必须有限**】**
3. ⇒ **`pmType` 是 `0..UINT8_MAX`**（`0..255`）
4. ⇒ **`pmFlags` 是 `0..UINT32_MAX`**
5. ⇒ **⇒ 而 `*pmFlags < 0` 先检查，然后 `uint64_t(*pmFlags) > UINT32_MAX`**
6. ⇒ **⇒ 所以【负数不通过**】**
```

### 4.1 ⭐⭐⭐ **"先检查 `< 0` 再转 `uint64_t`"**

**✅ 与 §438 的 `static_cast<uint64_t>(*integer) > limit`**——**互补** ✓

**⇒ 三层**：
```text
§438  **`static_cast<uint64_t>(*integer) > limit`** ⇒ **负数变成一个巨大的正数 ⇒ 被拒**
§441  **`*pmFlags < 0 || uint64_t(*pmFlags) > UINT32_MAX`** ⇒ **两段检查**
⇒ **⇒ 两种写法，同一效果**】
```

**✅ ⭐⭐⭐ **"两种写法同一效果"** —— 一个**同一意图的两个实现**。

**⇒ 三层**：
```text
写法 A：**先 `< 0` 再转**
写法 B：**直接转成 `uint64_t` 比较**
⇒ **⇒ 两者【都对**】
```

**✅ ⭐ **一个"两种写法"的实例**。</br>

**✅ 与 §438 的"那个 cast 正是这个检查能工作的原因"**配合。

### 4.2 而**`pmType` 的 `0..UINT8_MAX`**

**⇒ 五层**：
```text
`pmType` ⇒ **`0..255`**
而【实际有效值只有 `0`（`Normal`）/`2`（`Noclip`）/`5`（`Intermission`）/`8`（`Dead`）**】（§416）
⇒ **⇒ 所以【脚本【可以传 `0..255` 的任何值**】】**
```

### 4.3 ⚠ **一个真实的开放点**

**✅ 与 §416 的 `SvPmTypeNormal = 0` / `Noclip = 2` / `Intermission = 5` / `Dead = 8`**配合。

**⇒ 三层**：
```text
脚本可以传 `pmType = 3`（`UFO`）或 `4`（`limbo`）或 `6` 或 `7`
⇒ **⇒ 而这些【从未被验证**】**
```

**⚠ 一个**未验证的输入空间**（**标注**）。

**✅ 与 §439 的"脚本是一个外部输入 ⇒ 必须检查"**同族（**第二次"外部输入"）。

**⇒ 三层**：
```text
§439  **`isfinite` 检查 `yaw`**
§441  **`pmType 0..255` 与 `pmFlags 0..UINT32_MAX`**
⇒ **⇒ 两次"一个宽泛的范围**】
```

**✅ ⭐ **一个"宽泛范围"的两例**。

## 五、**四个 scripted 系列共享同一个后置条件**

```text
setScriptedViewAngles  ⇒ WorldMutationFailed : "requires an active scripted position"
setScriptedViewClamp   ⇒ WorldMutationFailed : "requires an active scripted position"
setScriptedLinkState   ⇒ WorldMutationFailed : "requires an active scripted position"
```

**⇒ 八层**：
```text
1. **三个函数【共享同一条失败消息**】**
2. ⇒ **⇒ 所以【它们都【要求一个活跃的 scripted position**】】**
3. ⇒ **⇒ 而 `clearScriptedPosition` 【清除它**】**
4. ⇒ **⇒ 所以【"清除之后调用任何一个 ⇒ 失败"**】
```

### 5.1 ⭐⭐⭐ **"三个函数共享同一条失败消息，所以它们都要求一个活跃的 scripted position"**

**✅ 与 §440 的"`NotPlaying` 与 `NotDead` 共用一个 `InvalidObjectState`"**同族（**第二次"同一个前提的两半**）。

**⇒ 三层**：
```text
§440  **`NotPlaying`/`NotDead` ⇒ 同一个前提**
§441  **三个函数 ⇒ 同一个"需要活跃的 scripted position"**
⇒ **⇒ 两次"同一个前提**】
```

**✅ ⭐⭐ **一个"同一个前提"的两例**。

**⚠ 而"`clearScriptedPosition` ⇒ 之后三个都失败"⇒ **一个状态机**。**

**⇒ 三层**：
```text
`setScriptedPosition` ⇒ **建立状态**
`setScriptedViewAngles`/`Clamp`/`LinkState` ⇒ **需要它**
`clearScriptedPosition` ⇒ **销毁它**
⇒ **⇒ 一个【四态机**】
```

**✅ ⭐⭐ **一个"四态机"的实例** —— 与 §422 的"`setPlayerCanTakeDamage` 的代次作用域"**不同（这是**一个显式状态**）。

## 六、**`setShellshock` 的 `1..15` / `1..65535`**

```php
if (*profileIndex <= 0 || *profileIndex > 0xF ||
    *durationMilliseconds <= 0 || *durationMilliseconds > UINT16_MAX)
    ⇒ "setshellshock expects profile 1..15 and duration 1..65535"
```

**⇒ 六层**：
```text
1. **`profileIndex` 是 `1..15`**（`0xF`）
2. ⇒ **`durationMilliseconds` 是 `1..65535`**（`UINT16_MAX`）
3. ⇒ **⇒ 所以【两个都【排除 `0`**】】**
4. ⇒ **⇒ 而 `profile` 是 `4` 位 ⇒ `0..15`，但【排除 `0`** ⇒ `1..15`**
```

### 6.1 ⭐⭐⭐ **"排除 `0` 的两个字段"**

**✅ 与 §439 的"`round 1..255` / `goal 0..255`"**——**对照** ✓

**⇒ 三层**：
```text
§439  **`round = 0` ⇒ 拒绝**；`goal = 0` ⇒ **接受**
§441  **`profileIndex = 0` ⇒ 拒绝**；`duration = 0` ⇒ **拒绝**
⇒ **⇒ 所以【"零是否合法"【逐个字段决定**】】
```

**✅ ⭐⭐⭐ **"零是否合法逐个字段决定"** —— 与 §439 的"界由语义决定"**同族（**第四个**）。

**⇒ 三层**：
```text
§431  **`clamp(0, 1000000)`**
§439  **`round 1..255` / `goal 0..255`**
§440  **`respawn 0..60000`**
§441  **`shellshock 1..15` / `1..65535`**
⇒ **⇒ 四组"逐字段决定**】
```

**✅ ⭐⭐ **一个"逐字段决定"的四例表**。

**⚠ 而"`duration = 0` ⇒ 拒绝"**⇒ **一个"0 毫秒的 shellshock 无意义**。**

**⇒ 三层**：
```text
`duration = 0` ⇒ **一个零长的效果** ⇒ **无意义** ⇒ 拒绝
`goal = 0` ⇒ **可能意味着"无目标"** ⇒ 有意义 ⇒ 接受
⇒ **⇒ 所以【"零"的意义【由它所在的字段**决定**】
```

**✅ ⭐⭐⭐ **"'零'的意义由它所在的字段决定"** —— 本报告的核心洞察。

## 七、`setObjective` 的八个参数

```php
validatePlayerMethod(world, call, 8, playerState)
slot    = get_if<int64_t>(arguments[0])
state   = get_if<int64_t>(arguments[1])
icon    = get_if<int64_t>(arguments[5])
entityNum = get_if<int64_t>(arguments[6])
teamNum = get_if<int64_t>(arguments[7])
（arguments[2..4] ⇒ 三个 float 位置）
```

**⇒ 八层**：
```text
1. **八个参数**
2. ⇒ **`slot`/`state`/`icon`/`entityNum`/`teamNum` 五个整数**
3. ⇒ **三个 `float` 位置**（`[2..4]`）
4. ⇒ **⇒ 与 §416 的 `SvObjective` 的五个字段**（`state`/`origin[3]`/`icon`/`entityNum`/`teamNum`）**完全对应**
5. ⇒ **⇒ 所以【`slot` 是【数组下标**】不是 `SvObjective` 的字段**
```

**✅ 与 §416 的 `SvObjective` 结构**完全闭合 ✓

**⇒ 三层**：
```text
`SvObjective` ⇒ `state` / `origin[3]` / `icon` / `entityNum` / `teamNum`（**五个字段**）
`setObjective` ⇒ **`slot` + 那五个字段**（**八个参数**）
⇒ **⇒ 所以【`slot` 是【外部的**】**
```

**✅ ⭐⭐ **一个"结构字段 vs 外部索引"的区分**。

**⚠ 而 `SvObjective` 的 `std::array<SvObjective, 32>`**（§416）⇒ **`slot` 是 `0..31`**。**

**✅ 与 §411 的"`archivalHud` 的 `31` 槽"**不同（**那是 HUD，这是 objective**）。

## 八、关键结论

1. **⭐⭐⭐ "`getvelocity` 发货了而 `getorigin` 没有，那读起来像一个疏忽而不是一个决定 —— 它们是一个结构的相邻字段"`** —— 第三次"对自己代码的诚实定性"（与 §404、§435 同族）。
2. **⭐⭐⭐ "那个缺席是承重的：没有它一个脚本不能把任何东西相对任何东西放置，所以拾取【只能在源码里手打坐标】，而游戏区域圆不能测试一个玩家是否在里面 —— 两个都是 BattleCity"`** —— 第三次"一个缺失的后果"（与 §400、§416 同族）。
3. **⭐⭐ "接受一个玩家或一个实体，在接收者的 `kind` 上分派而不是拆成两个名字，因为调用者不在乎它拿着哪个 —— 而两个验证器已经为错误的接收者返回正确的错误"`** ⇒ **"两个验证器消除一个检查"**。
4. **⭐⭐⭐ "玩家分支报告 `playerState.origin`，那是客户端被告知的 pmove 结果，不是实体的 `currentOrigin`：它们在玩家活着时一致，而 `playerState` 是【跨越一次重生仍然正确】的那个"`** —— 第三次"数据源选择"（与 §413、§440 同族）。
5. **⭐⭐⭐ 对 §438 的精确化**：**`SvScriptValue` 确实【没有表或字符串列表类型】，但【有 `SvScriptObjectArray`】** ⇒ **"两种列表，两种绕法"**：**字符串列表用逗号串（§440），对象列表用数组类型（§441）**。
6. **⭐⭐⭐ "`getentarray` 的每个对象携带 `entityGeneration`，而 `validateEntityMethod` 要求它非零 ⇒ §424 的『代次 0 静默不匹配』缺陷在这里【被一个检查挡住了】"`** —— 一个跨报告的防御闭合。
7. **⭐⭐ `validateEntityMethod` 与 `validatePlayerMethod` 是【一个对称的验证器对】**（各五道五码），而**实体版的第 3 道多一个 `entityGeneration` 非零检查**。
8. **⭐⭐ "先检查 `< 0` 再转 `uint64_t`"（§441）与 "直接转成 `uint64_t` 比较"（§438）是【同一意图的两个实现】** —— 两者都对。
9. **⚠ 一个真实的开放点**：**`pmType` 被接受为 `0..255` 而实际有效值只有 `0`/`2`/`5`/`8`** ⇒ **脚本可以传 `3`（`UFO`）/`4`（`limbo`）/`6`/`7`**【而这些从未被验证**】。
10. **⭐⭐ `setScriptedViewAngles`/`Clamp`/`LinkState` 三个函数共享同一条失败消息（`"requires an active scripted position"`）** ⇒ **"同一个前提"** —— 与 §440 的 `NotPlaying`/`NotDead` 同族；而 **`setScriptedPosition` 建立状态、`clearScriptedPosition` 销毁它 ⇒ 一个四态机**。
11. **⭐⭐⭐ "『零』的意义由它所在的字段决定"**：**`round = 0` 拒绝而 `goal = 0` 接受（§439）；`profileIndex = 0` 与 `duration = 0` 都拒绝（§441）** —— 第四组"逐字段决定"（与 §431/§439/§440 同族）。
12. **⭐ `setObjective` 的八个参数 = `slot` + `SvObjective` 的五个字段**（`state`/`origin[3]`/`icon`/`entityNum`/`teamNum`）⇒ **`slot` 是【外部的数组下标】**（`0..31`，与 §416 的 `std::array<SvObjective, 32>` 闭合）。

## 九、未闭合点

- `SvScriptObjectArray` 的确切定义（是否 `variant` 的一个成员）。
- `BattleCity`（`mp_battlecity`）的两个特性（拾取 / 游戏区域圆）。
- `pmType = 3`/`4`/`6`/`7` 的行为。
- `findMapEntities` 的 `value`/`key` 语义。
- `SvScriptObjectKind` 的完整枚举（`Player` / `Entity` / 其它）。
- `sv_script_builtin_mp.cpp` 1380 行之后未读取（**共 `4424` 行**）。
