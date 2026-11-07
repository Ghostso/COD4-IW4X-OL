# 444 · **"时间在服务器时钟之外"** —— `setGroundTiltTrajectory` 的 `serverTime + timeOffset`、`playSetGroundReferenceEnt` 的"零或一"、以及五个 FX 内置的"是一个函数"重复

## 一、范围

本报告学习 `sv_script_builtin_mp.cpp` 2060–2400 行（`setGroundTiltTrajectory` 的 `9` 参数与时间域、`playerSetGroundReferenceEnt` 的"零或一"、`playAnimation` 的 `flags 0..3`、`playSoundAt` 的 `as_master`、`triggerExploder`/`fireMagicAt` 的 `1..255`、`playFxAt` 的开头）。

## 二、**"时间在服务器时钟之外"**（本组最重要的一段）

### 2.1 那段

```php
const auto trajectoryTime =
    static_cast<std::int64_t>(world.snapshot().serverTime) + *timeOffset;
if (trajectoryTime < 0 ||
    trajectoryTime > std::numeric_limits<std::uint32_t>::max())
{
    return failure(
        SvScriptBuiltinErrorCode::InvalidArgumentValue,
        "setgroundtilttrajectory time is outside the server clock");
}
```

### 2.2 二十层

```text
1. **`timeOffset` 是一个【有符号的**偏移**
2. ⇒ **`trajectoryTime = int64(serverTime) + *timeOffset`**
3. ⇒ **⚠ 而它在【`int64` 里**算】 ⇒ **所以【溢出【不可能**】】**
4. ⇒ **然后检查 `0 <= trajectoryTime <= UINT32_MAX`**
5. ⇒ **⇒ 否则 `"time is outside the server clock"`**
6. ⇒ **⇒ 所以【`serverTime + timeOffset` 【必须落在一个 `uint32` 里**】】**
```

### 2.3 ⭐⭐⭐ **"用 `int64` 算再检查域，而不是用 `uint32` 算再检查溢出"**

**✅ 与 §438 的 `static_cast<uint64_t>(*integer) > limit`**——**第三次**"整数宽度的防护"。

**⇒ 三层**：
```text
写法 A：**`uint32_t a + b`** ⇒ **溢出【回绕**】⇒ **检查【不可靠**】
写法 B：**`int64_t a + b`** ⇒ **不会溢出** ⇒ **检查【可靠**】
⇒ **⇒ 所以【后者是【正确**的】
```

**✅ ⭐⭐⭐ **"先放大到更宽的整数，再做域检查"** —— 一个**反复出现的模式**。

**⇒ 三层**：
```text
§409  **`rawCost64` 的 `int64` 中间量**
§431  **`int64` 中间量 + `clamp(0, 1000000)`**
§444  **`int64(serverTime) + timeOffset` 再检查**
⇒ **⇒ 三次"放大再检查**】
```

**✅ ⭐⭐ **一个"放大再检查"的三例表**。

**⚠ 而"`timeOffset` 可以是负的**"⇒ **一个"过去的时间戳"**。**

**⇒ 三层**：
```text
`timeOffset < 0` ⇒ **一个过去的轨迹起点**
⇒ **⇒ 而它【仍然必须 `>= 0`**】
```

**✅ 与 §404 的"`OutroTimescaleBackdateMilliseconds = 50`"**同族（**第二次"一个过去的起点**）。

**⇒ 三层**：
```text
§408  **`start = now - 50`**（**一个 50ms 的过去**）
§444  **`serverTime + timeOffset`**（**任意过去或未来**）
⇒ **⇒ 两种"过去的起点**】
```

**✅ ⭐ **一个"过去的起点"的两例**。

### 2.4 而**`type` 与 `duration` 的两个界**

```php
if (!type || !timeOffset || !duration || *type < 0 ||
    *type > std::numeric_limits<std::uint8_t>::max() ||
    *duration < 0 ||
    *duration > std::numeric_limits<std::uint32_t>::max())
```

**⇒ 八层**：
```text
1. **`type` ⇒ `0..UINT8_MAX`**（`0..255`）
2. ⇒ **`timeOffset` ⇒ 【无界**】（**只要结果在 `uint32` 里**）
3. ⇒ **`duration` ⇒ `0..UINT32_MAX`**
4. ⇒ **⇒ 所以【`duration = 0` 是【合法**的】
```

**✅ ⭐⭐ **"`duration = 0` 是合法的"** —— 与 §441 的"`shellshock` 的 `duration = 0` 拒绝"**对照**。

**⇒ 三层**：
```text
§441  **`setshellshock` 的 `duration = 0` ⇒ 拒绝**（**一个零长的效果无意义**）
§444  **`setgroundtilttrajectory` 的 `duration = 0` ⇒ 接受**（**可能意味着"瞬时"**）
⇒ **⇒ 所以【"零"【逐个字段**决定**】
```

**✅ ⭐⭐⭐ **一个"零逐字段"的第五例**。

**⇒ 三层**：
```text
§431  **`clamp(0, 1000000)`**
§439  **`round 1..255` / `goal 0..255`**
§440  **`respawn 0..60000`**
§441  **`shellshock 1..15` / `1..65535`**
§444  **`duration 0..UINT32_MAX` 与 `timeOffset` 无界**
⇒ **⇒ 五组"逐字段决定**】
```

**✅ ⭐⭐ **一个"逐字段决定"的五例表**。

## 三、**`playerSetGroundReferenceEnt` 的"零或一"**（本组第二重要）

### 3.1 那段

```php
if (call.arguments.size() > 1)
    ⇒ "playersetgroundreferenceent expects zero or one entity"
std::optional<SvPlayerState> playerState;
if (auto error = validatePlayerMethod(world, call, call.arguments.size(), playerState))
    return std::move(*error);
if (call.arguments.empty())
{
    if (!world.clearPlayerGroundReference(call.self->id)) ⇒ WorldMutationFailed
    return success(std::monostate{});
}
const auto *object = std::get_if<SvScriptObjectRef>(&call.arguments.front());
if (!object || object->kind != Entity || !object->entityGeneration)
    ⇒ InvalidArgumentType "expects a generation-safe entity"
```

### 3.2 二十层

```text
1. **`> 1` ⇒ 拒绝**（**消息说"零或一"**）
2. ⇒ **而【零 ⇒ 清除引用**】**
3. ⇒ **一个 ⇒ 设置引用**
4. ⇒ **⇒ 所以【零个参数【是一个**操作**，不是"没有操作"】
5. ⇒ **而 `validatePlayerMethod(world, call, call.arguments.size(), ...)`**
6. ⇒ **⇒ 用【实际的**参数个数验证玩家**
7. ⇒ **⇒ 所以【`0` 与 `1` 都通过**
```

### 3.3 ⭐⭐⭐ **"零个参数是一个操作，不是『没有操作』"**

**✅ 与 §442 的 `weaponIndex` 的"`self` ⇒ `InvalidSelf`"**不同（这是**一个零参调用**）。

**✅ 与 §443 的 `setModelAt` 的"可选参数必须在调用前解决"**——**同类** ✓

**⇒ 三层**：
```text
§443  **`4` 或 `5` ⇒ 先检查再验证**
§444  **`0` 或 `1` ⇒ 先检查再验证**
⇒ **⇒ 两次"可选参数的契约问题**】
```

**✅ ⭐⭐ **"可选参数的契约问题"两次**。

**⚠ 而"零个参数 ⇒ 清除"⇒ **一个"零参 = 清除"的惯例**。**

**⇒ 三层**：
```text
`playersetgroundreferenceent()` ⇒ **清除**
`playersetgroundreferenceent(entity)` ⇒ **设置**
⇒ **⇒ 所以【同一个名字两个操作，由参数个数决定**】
```

**✅ 与 §442 的 `setPlayerWeapons` 的 "`3` 或 `4`"**同族（**第三**次"参数个数决定语义"）。

**⇒ 三层**：
```text
§439  **`zmspawnactor` 的 `3` 或 `4`（可选头）**
§442  **`setplayerweapons` 的 `3` 或 `4`（可选 supplemental）**
§444  **`playersetgroundreferenceent` 的 `0` 或 `1`（清除 vs 设置）**
⇒ **⇒ 三次"参数个数决定语义**】
```

**✅ ⭐⭐ **一个"参数个数决定语义"的三例表**。

**⚠ 而"零参 = 清除"是一个**更激进**的惯例（**语义完全不同**）**。**

**⇒ 三层**：
```text
`setmodelat` 的 `4`/`5` ⇒ **同一个操作，一个可选参数**
`playersetgroundreferenceent` 的 `0`/`1` ⇒ **两个不同的操作**
⇒ **⇒ 所以【后者是【一个更强的惯例**】
```

**✅ ⭐⭐ **"两个不同的操作"** —— 一个**需要文档的惯例**。

**✅ 而消息 `"expects zero or one entity"` 部分地说明了它**（但**没说"零是清除"**）。

## 四、**五个 FX 内置的"是一个函数"重复**（本组第三重要）

**⇒ 五个（本段内）**：

```text
playSoundAt              ⇒ if (call.self) ⇒ "playsoundat is a function"
triggerExploder          ⇒ if (call.self) ⇒ "triggerexploder is a function"
fireMagicAt              ⇒ if (call.self) ⇒ "firemagicat is a function"
playFxAt                 ⇒ if (call.self) ⇒ "playfxat is a function"
spawnGroundTiltController⇒ if (call.self) ⇒ "spawngroundtiltcontroller is a function"
（加上 §442 的 weaponIndex 与 effectIndex）
```

**⇒ 七个。**

### 4.1 ⭐⭐⭐ **"七个函数各自手写同一个检查"**

**✅ 与 §437 的"八个拒绝都返回同一个 `false`"**不同（那是**同一个函数内**，这是**七个函数各写一遍**）。

**⇒ 三层**：
```text
§442  **`weaponIndex`/`effectIndex` 两个**
§444  **`playSoundAt`/`triggerExploder`/`fireMagicAt`/`playFxAt`/`spawnGroundTiltController` 五个**
⇒ **⇒ 所以【七个函数，七份相同的代码**】
```

**✅ ⭐⭐ **一个"七份重复"的实例** —— 与项目指令的"三个相似的行比一个过早的抽象好"**——七份可能超过阈值**。**

**⚠ 而"一个 `validateFunctionCall` 辅助"**会消除七份**。**

**⇒ 三层**：
```text
一个辅助：`if (call.self) return failure(InvalidSelf, name + " is a function");`
⇒ **⇒ 而【它【不存在**】】
```

**⚠ 一个**明确的抽取机会**（**标注**）。

**✅ 与 §442 的"玩家侧的四个检查复制了 `validatePlayerMethod` 的后三道"**同族（**第二次"复制的检查**）。

**⇒ 三层**：
```text
§442  **`isTouchingPlayer` 复制四道**
§444  **七个函数复制一道**
⇒ **⇒ 两次"复制**】
```

**✅ ⭐ **一个"复制"的两例**。

### 4.2 而**"`triggerExploder` 的 `1..255`"**

```php
if (!index || *index <= 0 || *index > 0xFF)
    ⇒ "triggerexploder expects an index from 1 through 255"
```

**⇒ 六层**：
```text
1. **`1..255`**（**排除 `0`**）
2. ⇒ **⇒ 与 §407 的 `EventExploder = 0x82` 配合**（**`eventParm` 是 `8` 位**）
3. ⇒ **⇒ 而 §407 说"demo 用参数 `1..29`"**
```

**✅ 与 §407 的"`EV_EXPLODER` 选一个在 `configstring 11990 + eventParm` 处发布的效果记录，demo 用参数 `1..29`"**完全闭合 ✓

**⇒ 三层**：
```text
§407  **demo 的参数是 `1..29`**
§444  **内建接受 `1..255`**
⇒ **⇒ 所以【内建的界【比 demo 的实际值【宽**】】**
```

**✅ ⭐⭐ **"界比实际值宽"**。</br>

**✅ 与 §442 的"`giveweapon` 的界比 `a` 的更宽"**同族（**第二次"界比实际宽**）。

**⇒ 三层**：
```text
§442  **`giveweapon` 接受 `1..WeaponConfigStringCount-1` 而 `a` 只接受已注册的**
§444  **`triggerexploder` 接受 `1..255` 而 demo 只用 `1..29`**
⇒ **⇒ 两次"界宽于实测**】
```

**✅ ⭐ **一个"界宽于实测"的两例**。

**⚠ 而"一个宽的界允许一个错误的值通过**"⇒ **一个潜在的风险**。**

**⇒ 三层**：
```text
`triggerexploder(200)` ⇒ **通过**
而【`configstring 11990 + 200` 可能【不存在**】
⇒ **⇒ 所以【一个错误的索引【到一个不存在的效果**】】
```

**⚠ 一个**可推导的缺口**（**而 §422 的"扣住子实体"的原则在这里没有应用**）。

## 五、**`playAnimation` 的 `flags 0..3`**

```php
std::uint8_t flags = 1;
if (argumentCount == 2) {
    if (!value || *value < 0 || *value > 3)
        ⇒ "playanimation flags must be an integer from 0 through 3";
    flags = static_cast<std::uint8_t>(*value);
}
```

**⇒ 八层**：
```text
1. **默认 `flags = 1`**
2. ⇒ **而可选的第二个参数【`0..3`**】**
3. ⇒ **⇒ 所以【`2` 位**的范围】
4. ⇒ **而【§417 的 `SvAnimationCommand::flags{1}` 默认也是 `1`**】**
```

**✅ 与 §417 的 `SvAnimationCommand::flags{ 1 };`**完全闭合 ✓

**⇒ 三层**：
```text
§417  **`SvAnimationCommand::flags{1}`**
§444  **`playanimation` 的默认 `flags = 1`**
⇒ **⇒ 同一个默认**
```

**✅ ⭐ **一个"默认值"的确认**。

**⚠ 而"`0..3`"⇒ **与 `SvAnimationCommandType` 的 `SetGoalWeight = 1` / `ClearTree = 11`**不同（**`flags` 是一个独立的 `2` 位域**）。

**⇒ 三层**：
```text
`type` ⇒ `1` 或 `11`
`flags` ⇒ `0..3`
⇒ **⇒ 两个不同的字段，两个不同的域**】
```

**✅ ⭐⭐ **"两个不同的域"**。</br>

**✅ 与 §417 的"`SvAnimationCommand` 有 `type` 与 `flags`"**配合。

## 六、**`playSoundAt` 的 `as_master`**

```php
if (call.arguments.size() != 4 && call.arguments.size() != 5)
    ⇒ "(alias, x, y, z) or (alias, x, y, z, as_master)"
...
if (call.arguments.size() == 5) {
    const auto *value = std::get_if<bool>(&call.arguments[4]);
    if (!value) ⇒ "playsoundat's optional fifth argument is a boolean";
    asMaster = *value;
}
...
if (!world.spawnSoundAliasEvent(*parameter, origin, asMaster))
```

**⇒ 十层**：
```text
1. **`4` 或 `5` 个参数**
2. ⇒ **第五个是 `as_master`（一个 `bool`）**
3. ⇒ **⇒ 与 §415 的 `EventSoundAlias = 0x03` 与 `EventSoundAliasAsMaster = 0x04`** 配合**
4. ⇒ **⇒ 所以【`as_master == true` ⇒ 用 `0x04` 的 eType**】**
```

**✅ 与 §415 的"`EventSoundAlias = 0x03` / `EventSoundAliasAsMaster = 0x04`"**完全闭合 ✓

**⇒ 三层**：
```text
§415  **两个事件**（`0x03` / `0x04`）
§444  **一个 `bool` 决定用哪个**
⇒ **⇒ 所以【一个 API 两个事件**】
```

**✅ ⭐⭐⭐ **"一个 API 两个事件"** —— 与 §442 的 `getOrigin` 的"一个名字两个分支"**同族（**第三次"一个名字两个行为**）。

**⇒ 三层**：
```text
§441  **`getOrigin` 一个名字两个分支（`Player`/`Entity`）**
§444  **`playSoundAt` 一个 `bool` 两个事件**
⇒ **⇒ 两次"一个入口两个行为**】
```

**✅ ⭐ **一个"一个入口两个行为"的两例**。

**⚠ 而"`Sprite` 的 `asMaster`"⇒ **`EventSoundAliasAsMaster` 的语义**。**

**✅ 与 §415 的"`EventSoundAliasAsMaster = 0x04` 的用途"**（**未说明**）。

**⚠ 一个**未闭合点**。

## 七、`playFxAt` 的开头

```php
if (call.self)
{
    return failure(
        SvScriptBuiltinErrorCode::InvalidSelf,
```

**⇒ 六层**：
```text
1. **同 `playSoundAt` 的"是一个函数"检查**
2. ⇒ **⇒ 第七份**
3. ⇒ **而【`playFxAt` 的参数（下一段）】**
```

**✅ 与 §444 四 的"七份重复"**完全一致 ✓

## 八、关键结论

1. **⭐⭐⭐ `setGroundTiltTrajectory` 的"时间在服务器时钟之外"**：`trajectoryTime = int64(serverTime) + timeOffset` ⇒ **在 `int64` 里算所以溢出不可能 ⇒ 然后检查 `0..UINT32_MAX`** —— **"先放大到更宽的整数，再做域检查"**（第三次，与 §409/§431 同族）。
2. **⭐ `timeOffset` 可以是负的 ⇒ 一个"过去的轨迹起点"** —— 与 §408 的 `OutdateTimescaleBackdateMilliseconds = 50`（一个 50ms 的过去）同族。
3. **⭐⭐ `duration = 0` 在这里【合法】而 §441 的 `setshellshock` 的 `duration = 0` 【拒绝】** ⇒ **"零逐字段决定"的第五例**（与 §431/§439/§440/§441 同族）。
4. **⭐⭐ "`timeOffset` 无界"（只要结果在 `uint32` 里）** ⇒ 一个**由结果约束而不是由输入约束**的域。
5. **⭐⭐⭐ `playerSetGroundReferenceEnt` 的"零或一"**：**零参 ⇒ 清除引用，一参 ⇒ 设置引用** ⇒ **"零个参数是一个操作，不是『没有操作』"** —— 第三次"参数个数决定语义"（与 §439/§442 同族），而这里是**最强的惯常**（**两个完全不同的操作**）。
6. **⭐⭐ "七个函数各自手写同一个 `if (call.self) ⇒ InvalidSelf` 检查"**（`weaponIndex` / `effectIndex` / `playSoundAt` / `triggerExploder` / `fireMagicAt` / `playFxAt` / `spawnGroundTiltController`）—— **七份重复**，与项目指令的"三行重复优于抽象"**——七份可能超过阈值**；而**一个 `validateFunctionCall` 辅助会消除七份** —— 明确标注的抽取机会。
7. **⭐⭐ `triggerExploder` 的 `1..255` 而 §407 的 demo 只用 `1..29`** ⇒ **"界比实际值宽"** —— 与 §442 的 `giveweapon`（界比 `a` 宽）同族。
8. **⚠ 一个可推导的缺口**：**`triggerexploder(200)` 通过检查，而 `configstring 11990 + 200` 可能不存在** ⇒ **一个错误的索引指向一个不存在的效果**（**§422 的"扣住子实体"原则在这里没有应用**）。
9. **⭐ `playAnimation` 的 `flags 0..3`（默认 `1`）** 与 §417 的 `SvAnimationCommand::flags{1}` 默认一致；而 **`flags`（`2` 位）与 `type`（`1` 或 `11`）是两个不同的域**。
10. **⭐⭐⭐ `playSoundAt` 的 `as_master`（一个 `bool`）与 §415 的 `EventSoundAlias = 0x03` / `EventSoundAliasAsMaster = 0x04` 闭合** ⇒ **"一个 API 两个事件"** —— 与 §441 的 `getOrigin`（一个名字两个分支）同族。

## 九、未闭合点

- `EventSoundAliasAsMaster` 的真实语义。
- `SvEntityDamageKind` 的完整枚举。
- `playFxAt` 的完整参数。
- `playFxOnTag` 的参数。
- `setGroundTiltControllerTrajectory` 的 `type` 语义。
- `sv_script_builtin_mp.cpp` 2400 行之后未读取（**共 `4424` 行**）。
