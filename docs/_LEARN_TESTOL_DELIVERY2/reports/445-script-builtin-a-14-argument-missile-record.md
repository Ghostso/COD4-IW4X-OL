# 445 · **"一个 14 参数记录的导弹、两个时间域"** —— `readScriptedMissileState` 的九个浮点、`playFxAt` 的 `1..399`、以及 `physicsExplosionSphereAt` 的"`0 <= inner <= outer`"

## 一、范围

本报告学习 `sv_script_builtin_mp.cpp` 2400–2740 行（`playFxAt` 的 `6` 个变换数、`playFxOnTag` 的 `tag 0..254`、`readScriptedMissileState` 的 `14` 参数、`spawnScriptedMissile`/`setScriptedMissile`、`earthquakeAt`、`physicsExplosionSphereAt`、`radiusDamageAt` 的开头）。

## 二、**`readScriptedMissileState` 的 `14` 参数**（本组最重要的一段）

### 2.1 那段

```php
if (call.arguments.size() != 14)
    ⇒ " expects (weapon, position_type, position_time_offset,
                x, y, z, dx, dy, dz, angle_type, pitch, yaw, roll,
                launch_time_offset)"
...
// CODREF(Wetwork demo ET_MISSILE): the capture's RPG rows use
// eFlags 0x1000, scale 1, no attached ground entity, linear or
// gravity position trajectories, and stationary angle trajectories.
state = {
    .number = 0,
    .weapon = static_cast<std::uint16_t>(*weapon),
    .owner = EntityNumWorld,
    .ground = EntityNumNone,
    .eFlags = 0x1000,
    .position = {
        .type = static_cast<std::int32_t>(*positionType),
        .time = static_cast<std::int32_t>(positionTime),
        .duration = 0,
        .base = { values[0], values[1], values[2] },
        .delta = { values[3], values[4], values[5] },
    },
    .angles = {
        .type = static_cast<std::int32_t>(*angleType),
        .time = 0,
        .duration = 0,
        .base = { values[6], values[7], values[8] },
        .delta = {},
    },
    .scale = 1.0f,
    .launchTime = static_cast<std::uint32_t>(launchTime),
};
```

### 2.2 二十四层

```text
1. **`14` 个参数**【逐项命名**】**
2. ⇒ **`weapon`** ⇒ 武器号
3. ⇒ **`position_type`** ⇒ **`1` 或 `2`**（**线性或重力**）
4. ⇒ **`position_time_offset`** ⇒ 一个有符号偏移
5. ⇒ **`x, y, z`** ⇒ `base`
6. ⇒ **`dx, dy, dz`** ⇒ `delta`
7. ⇒ **`angle_type`** ⇒ **`0` 或 `1`**（**静止或其它**）
8. ⇒ **`pitch, yaw, roll`** ⇒ 角度 `base`
9. ⇒ **`launch_time_offset`** ⇒ 一个有符号偏移
10. ⇒ **⇒ 而 `state` 的构造**：
      · **`number = 0`**（**由池分配**）
      · **`weapon`**
      · **`owner = EntityNumWorld`**（**`2046`**）
      · **`ground = EntityNumNone`**（**`2047`**）
      · **`eFlags = 0x1000`**
      · **`position`** ⇒ `type`/`time`/`duration=0`/`base`/`delta`
      · **`angles`** ⇒ `type`/`time=0`/`duration=0`/`base`/**`delta = {}`**
      · **`scale = 1.0f`**
      · **`launchTime`**
```

### 2.3 ⭐⭐⭐ **"`eFlags 0x1000`、`scale 1`、没有附着的地面实体、线性或重力的位置轨迹、静止的角度轨迹"**

**✅ 这是本报告里**最完整的一条"从一个 demo 的实测量反推一个结构**。**

**⇒ 三层**：
```text
`eFlags = 0x1000` ⇒ **从 Wetwork demo 的 RPG 行**（**实测**）
`scale = 1.0f` ⇒ **同上**
`owner = EntityNumWorld` ⇒ **`2046`**
`ground = EntityNumNone` ⇒ **`2047`**
`angles.delta = {}` ⇒ **零**（**静止**）
⇒ **⇒ 所以【整个结构【从一个捕获**被反推出来**】
```

**✅ 与 §407 的"`ET_MISSILE` 把同一个 `+0x58` 用作它的发射时间"**完全闭合 ✓

**⇒ 三层**：
```text
§407  **`ET_MISSILE` 的 `+0x58` 是发射时间**
§445  **`state.launchTime`** ⇒ **一个独立的字段**
⇒ **⇒ 所以【`launchTime` ⇒ `+0x58`**】
```

**✅ ⭐⭐⭐ **一个"`launchTime` ↔ `+0x58`"的字段闭合**。

**⚠ 而"`position.duration = 0` 与 `angles.duration = 0`"⇒ **两个零**。**

**⇒ 三层**：
```text
`position.duration = 0` ⇒ **可能意味着"无限"或"由 type 决定"**
`angles.duration = 0` ⇒ **同上**
⇒ **⇒ 所以【一个脚本导弹【没有持续时间**】**
```

**✅ 与 §444 的"`setgroundtilttrajectory` 的 `duration = 0` 合法"**同族（**第三次"`duration = 0`**）。

**⇒ 三层**：
```text
§441  **`setshellshock` 的 `duration = 0` ⇒ 拒绝**
§444  **`setgroundtilttrajectory` 的 `duration = 0` ⇒ 接受**
§445  **`ET_MISSILE` 的 `duration = 0` ⇒ 一个常量**
⇒ **⇒ 三次"零"**
```

**✅ ⭐ **一个"`duration = 0`"的三例**。

### 2.4 而**"两个时间域"**

```php
const auto now = static_cast<std::int64_t>(world.snapshot().serverTime);
const auto positionTime = now + *positionTimeOffset;
const auto launchTime = now + *launchTimeOffset;
if (positionTime < std::numeric_limits<std::int32_t>::min() ||
    positionTime > std::numeric_limits<std::int32_t>::max() ||
    launchTime < 0 ||
    launchTime > std::numeric_limits<std::uint32_t>::max())
{
    return failure(..., " received a trajectory time outside the wire domain");
}
```

**⇒ 十六层**：
```text
1. **`positionTime` 是【`int32`**】域**
2. ⇒ **`launchTime` 是【`uint32`**】域**
3. ⇒ **⇒ 两个不同的域**】
4. ⇒ **而 `positionTime` 【允许负值**】（`INT32_MIN`）**
5. ⇒ **⇒ 所以【一个位置的起始时间【可以是负的**】】**
6. ⇒ **⇒ 而【发射时间【必须非负**】】**
```

### 2.5 ⭐⭐⭐ **"`positionTime` 允许负而 `launchTime` 不允许"**

**✅ 与 §444 的"`trajectoryTime` 必须 `0..UINT32_MAX`"**——**对照** ✓

**⇒ 三层**：
```text
§444  `setgroundtilttrajectory` 的 `trajectoryTime` ⇒ **`0..UINT32_MAX`**
§445  **`positionTime` ⇒ `INT32_MIN..INT32_MAX`**（**允许负**）
§445  **`launchTime` ⇒ `0..UINT32_MAX`**（**不允许负**）
⇒ **⇒ 所以【三个时间字段，两个域**】
```

**✅ ⭐⭐⭐ **"三个时间字段两个域"** —— 而 **`positionTime` 的负值有语义**（**一个"已经开始了"的轨迹**）。

**⚠ 一个**可推导的理由**（**标注**）。

## 三、**`playFxAt` 的 `1..399`**（本组第二重要）

### 3.1 那段

```php
if (call.arguments.size() != 7)
    ⇒ "playfxat expects (effect_index, x, y, z, pitch, yaw, roll)"
...
if (!effect || *effect <= 0 || *effect >= EffectConfigStringCount)
    ⇒ "playfxat expects an effect index from 1 through 399"
```

**⇒ 十层**：
```text
1. **`7` 个参数**：一个 `effect_index` + 六个变换数
2. ⇒ **`effect` 是 `1..EffectConfigStringCount-1`**
3. ⇒ **而消息说【"1 through 399"**】**
4. ⇒ **⇒ 所以 `EffectConfigStringCount = 400**】
5. ⇒ **⇒ 而 §388 说"effects 4136"** ⇒ **一个带的起点**
```

### 3.2 ⭐⭐⭐ **"`1 through 399` ⇒ `EffectConfigStringCount = 400`"**

**✅ 与 §388 的"effects 4136"**配合 ✓

**⇒ 三层**：
```text
`effects` 带的起点 ⇒ `4136`（§388）
`EffectConfigStringCount` ⇒ **`400`**
⇒ **⇒ 所以【`4136..4535` 是效果带**】
```

**✅ ⭐⭐ **一个"带的范围"的推导**。</br>

**✅ 与 §442 的 `effectIndex` 的 `>= EffectConfigStringCount` 拒绝**完全一致 ✓

**⇒ 三层**：
```text
§442  **`effectIndex`：`!index || !*index || *index >= EffectConfigStringCount`**
§445  **`playFxAt`：`!effect || *effect <= 0 || *effect >= EffectConfigStringCount`**
⇒ **⇒ 同一界，两处**
```

**✅ ⭐ **一个"同一界"的确认**。

**⚠ 而"六个变换数"⇒ **`pitch,yaw,roll` 与 `x,y,z`**。**

**⇒ 三层**：
```text
`values[0..2]` ⇒ **位置**
`values[3..5]` ⇒ **角度**
⇒ **⇒ 所以【`playFxAt` 【有完整的朝向**】**
```

**✅ 与 §443 的"`setModelAt` 只接受 `yaw`"**——**对照** ✓

**⇒ 三层**：
```text
§443  **`setmodelat` ⇒ 只 `yaw`**（"loot 想要朝向不是翻滚"）
§445  **`playfxat` ⇒ 完整 `pitch,yaw,roll`**（**一个效果【可以有任意朝向**）
⇒ **⇒ 所以【两个不同的用途，两个不同的域**】
```

**✅ ⭐⭐⭐ **"同一个概念，两个域，由用途决定"** —— 与 §442 的"界由语义决定"**同族（**第六次**）。

## 四、**`playFxOnTag` 的 `tag 0..254`**（本组第三重要）

```php
if (!effect || *effect <= 0 || *effect >= EffectConfigStringCount ||
    !tag || *tag < 0 || *tag >= 0xFF)
    ⇒ "playfxontag expects effect 1..399 and tag 0..254"
```

**⇒ 八层**：
```text
1. **`tag` 是 `0..254`**（`< 0xFF = < 255`）
2. ⇒ **⇒ 所以【`255` 被排除**】**
3. ⇒ **而 §417 的 `SvAgentDefaultAttachTag1 = 3`** ⇒ **一个 tag 值**
4. ⇒ **而 §415 的"四个 `6` 位 tag 槽"** ⇒ **`0..63`**
```

### 4.1 ⭐⭐⭐ **"`tag 0..254` 而 `6` 位槽是 `0..63`"**

**⇒ 三层**：
```text
`playFxOnTag` 接受 `0..254` ⇒ **一个 `8` 位的域**
而 §415 的 agent 附件 tag 槽 ⇒ **`6` 位（`0..63`）**
⇒ **⇒ 所以【两个不同的 tag 空间**】
```

**⚠ 一个**需要区分的两处 tag**（**标注**）。

**✅ 与 §415 的"四个 `6` 位 TAG 槽（idx23/15/17/19）"**配合。

**⇒ 三层**：
```text
agent 附件 tag ⇒ **`6` 位**（`+0x024/028/02C/030`）
`playfxontag` 的 tag ⇒ **`8` 位**（`0..254`）
⇒ **⇒ 所以【两个不同的 tag 域**】
```

**✅ ⭐⭐ **一个"两个 tag 域"的区分**。

**⚠ 而"`255` 被排除"⇒ **可能是 `255` 是一个哨兵**。**

**⇒ 三层**：
```text
`tag = 255` ⇒ **可能是一个哨兵（"没有"）**
⇒ **⇒ 所以【排除它**】
```

**✅ 与 §417 的"`field00E4 = 255` 是 `0xFF` 哨兵"**同族（**第二次"`255` 是哨兵**）。

**⇒ 三层**：
```text
§417  **`scriptMoverField00E4 = 255` 是"没有"**
§445  **`playfxontag` 的 `tag < 255`**
⇒ **⇒ 所以【`255` 是一个保留值**】
```

**✅ ⭐⭐ **一个"`255` 保留"的两例**。

## 五、**`physicsExplosionSphereAt` 的"`0 <= inner <= outer`"**（本组第四重要）

```php
if (values[3] < 0.0f || values[4] <= 0.0f ||
    values[4] < values[3] || values[5] <= 0.0f)
    ⇒ "physicsexplosionsphereat expects 0 <= inner <= outer and positive magnitude";
```

**⇒ 十四层**：
```text
1. **`inner >= 0`**
2. ⇒ **`outer > 0`**
3. ⇒ **`outer >= inner`**
4. ⇒ **`magnitude > 0`**
5. ⇒ **⇒ 四个条件**】
6. ⇒ **⇒ 所以【三个半径/强度的关系被【显式约束**】】
```

### 5.1 ⭐⭐⭐ **"`inner >= 0` 而 `outer > 0` 的两个下界不同"**

**✅ 与 §439 的"`round 1..255` / `goal 0..255`"**、§441/§444/§445 的"零逐字段"**完全同族（**第六次**）。

**⇒ 三层**：
```text
`inner` ⇒ **`>= 0`**（**允许 `0`**）
`outer` ⇒ **`> 0`**（**不允许 `0`**）
⇒ **⇒ 所以【内半径可以是 `0`（一个点）而外半径不可以**】
```

**✅ ⭐⭐ **"内半径可以是一个点而外半径不可以"** —— 一个**几何上合理的区分**。

**⚠ 而"`outer >= inner`"⇒ **一个顺序约束**。**

**⇒ 三层**：
```text
`outer < inner` ⇒ **一个几何上矛盾的球**
⇒ **⇒ 所以【拒绝**】
```

**✅ ⭐⭐ **"一个几何上矛盾的球"** —— 与 §407 的"三个 union 字在两个事件上有不同语义"**配合**。

**⇒ 三层**：
```text
§407  **`EventPhysicsExplosionSphere` 的 `+58/+5C/+60` 是 `innerRadius`/`outerRadius`/`magnitude`**
§445  **而它们的约束是 `0 <= inner <= outer` 且 `magnitude > 0`**
⇒ **⇒ 所以【三个字段的语义【被约束确认**】】
```

**✅ ⭐⭐⭐ **一个"约束确认语义"的实例**。</br>

**✅ 与 §407 的"`RadiusDamage` 与 `Earthquake` 用同样的三个 union 字而语义完全不同"**配合。

**⇒ 三层**：
```text
`EventPhysicsExplosionSphere` ⇒ **`inner`/`outer`/`magnitude`**
`EventRadiusDamage` ⇒ **`effectRadius`/`data1`/`data2`**
`EventEarthquake` ⇒ **`scale`/`radius`/`duration`**
⇒ **⇒ 三个事件共用三个字，三个语义**】
```

**✅ ⭐⭐⭐ **一个"三事件三语义"的完整图景** —— **而它们在这里各自有一个内建**（`physicsExplosionSphereAt` / `radiusDamageAt` / `earthquakeAt`）。

**⚠ 而 `earthquakeAt` 的约束**：

```php
if (!scale || !radius || !duration ||
    !std::isfinite(*scale) || *scale <= 0.0 ||
    !std::isfinite(*radius) || *radius <= 0.0 ||
    *duration <= 0 || *duration > 0xFFFF)
    ⇒ "earthquakeat expects positive finite scale/radius and a 1..65535 ms duration"
```

**⇒ 三层**：
```text
`scale > 0` ⇒ **不允许零**
`radius > 0` ⇒ **不允许零**
`duration 1..65535` ⇒ **不允许零**
⇒ **⇒ 所以【`earthquake` 的三个字段【都不允许零**】】
```

**✅ ⭐⭐ **对比**：
```text
`physicsExplosionSphere` ⇒ **`inner >= 0`**（**允许零**）
`earthquake` ⇒ **`scale/radius/duration` 全部 `> 0`**
⇒ **⇒ 所以【同一个类型的"三个字"【不同的约束**】
```

**✅ ⭐⭐⭐ **一个"同一位置不同约束"的实例**。

## 六、`spawnScriptedMissile` 与 `setScriptedMissile` 的"一个读两个用"

```cpp
// spawnScriptedMissile
if (call.self) ⇒ "spawnscriptedmissile is a function"
SvMissileNetworkState state;
if (auto error = readScriptedMissileState(world, call, state)) return std::move(*error);
const auto handle = world.spawnScriptedMissile(state);

// setScriptedMissile
SvEntityHandle handle;
if (auto error = validateEntityMethod(world, call, 14, handle)) return std::move(*error);
SvMissileNetworkState state;
if (auto error = readScriptedMissileState(world, call, state)) return std::move(*error);
if (!world.setScriptedMissileState(handle, state)) ...
```

**⇒ 八层**：
```text
1. **两个内建共享 `readScriptedMissileState`**
2. ⇒ **而 `spawnScriptedMissile` 【先检查 `self`**】**（**一个函数**）**
3. ⇒ **而 `setScriptedMissile` **不检查 `self`**（**它是一个方法**）**
4. ⇒ **⇒ 所以【同一个读取器，两种调用方式**】
```

### 6.1 ⭐⭐⭐ **"同一个读取器，两种调用方式"**

**✅ 与 §442 的"两个验证器已经为错误的接收者返回正确的错误"**同族（**第三次"一个函数的复用**）。

**⇒ 三层**：
```text
`readScriptedMissileState` ⇒ **纯读取**（**不关心 `self`**）
两个调用者 ⇒ **各自处理 `self`**（**一个检查、一个不用**）
⇒ **⇒ 所以【一个纯函数被两种调用者复用**】
```

**✅ ⭐⭐ **"一个纯函数被两种调用者复用"**。

**⚠ 而 `setScriptedMissile` 的 `validateEntityMethod(world, call, 14, handle)`**⇒ **`14` 与 `readScriptedMissileState` 的 `14`** **重复**。

**⇒ 三层**：
```text
`validateEntityMethod(..., 14, handle)` ⇒ **检查 14 个参数**
`readScriptedMissileState` ⇒ **也检查 14 个**
⇒ **⇒ 所以【两次检查同一个数**】
```

**⚠ 一个**可推导的冗余**（**但有理由：一个是"实体的参数个数"，一个是"记录的参数个数"**）。

**✅ 与 §443 的"`setModelAt` 先解决可选参数再验证"**相反（那里**避免重复检查**，这里**接受重复**）。

**⇒ 三层**：
```text
§443  **避免两次验证**（**因为第二次会报告错的错误**）
§445  **接受两次验证**（**因为两次是同一个数，不会报告错的错误**）
⇒ **⇒ 所以【判据是"第二次会不会报告错的错误"**】
```

**✅ ⭐⭐⭐ **一个"判据"的精确化**。

## 七、关键结论

1. **⭐⭐⭐ `readScriptedMissileState` 的 `14` 参数逐项命名**（`weapon` / `position_type` / `position_time_offset` / `x,y,z` / `dx,dy,dz` / `angle_type` / `pitch,yaw,roll` / `launch_time_offset`）而 **`state` 的构造【从一个捕获反推**】：**`eFlags = 0x1000`、`scale = 1.0f`、`owner = EntityNumWorld`（`2046`）、`ground = EntityNumNone`（`2047`）、`angles.delta = {}`**（"Wetwork demo 的 RPG 行"）。
2. **⭐⭐⭐ `state.launchTime` ↔ §407 的"`ET_MISSILE` 把同一个 `+0x58` 用作它的发射时间"** —— 一个字段闭合。
3. **⭐⭐ "两个时间域：`positionTime` 是 `int32`（允许负），`launchTime` 是 `uint32`（不允许负）"**，而 **§444 的 `setgroundtilttrajectory` 的 `trajectoryTime` 是 `uint32`** ⇒ **"三个时间字段两个域"**。
4. **⭐⭐ `position.duration = 0` 与 `angles.duration = 0`** ⇒ **一个脚本导弹【没有持续时间】** —— 第三次"`duration = 0`"（与 §441 的拒绝、§444 的接受同族）。
5. **⭐⭐⭐ `playFxAt` 的 `1..399` ⇒ `EffectConfigStringCount = 400`**，而 **§388 的 `effects 4136` 是带的起点** ⇒ **`4136..4535`**；与 §442 的 `effectIndex` 的同一界吻合。
6. **⭐⭐ `playFxAt` 接受完整的 `pitch,yaw,roll` 而 §443 的 `setModelAt` 只接受 `yaw`** ⇒ **"同一个概念，两个域，由用途决定"**（第六次"界由语义决定"）。
7. **⭐ `playFxOnTag` 的 `tag 0..254`**（`255` 被排除）⇒ **`255` 是一个保留值/哨兵**，与 §417 的 `field00E4 = 255` 同族（第二次"`255` 是哨兵"）；而 **agent 附件的 tag 是 `6` 位（`0..63`）** ⇒ **两个不同的 tag 域**。
8. **⭐⭐⭐ `physicsExplosionSphereAt` 的 `0 <= inner <= outer` 且 `magnitude > 0`** ⇒ **`inner` 可以是 `0`（一个点）而 `outer` 不可以** —— 一组**几何上合理的约束**，**而它们确认了 §407 的三个 union 字的语义**。
9. **⭐⭐⭐ "三个事件共用三个 union 字，三个语义"的完整图景**：`EventPhysicsExplosionSphere`（`inner`/`outer`/`magnitude`，`inner >= 0`）/ `EventRadiusDamage`（`effectRadius`/`data1`/`data2`）/ `EventEarthquake`（`scale`/`radius`/`duration`，**三个都不允许零**）⇒ **同一位置不同约束**。
10. **⭐⭐ `spawnScriptedMissile` 与 `setScriptedMissile` 共享 `readScriptedMissileState`（一个纯函数）** 而**各自处理 `self`**（一个检查、一个不用）—— 第三次"一个函数的复用"。
11. **⭐⭐⭐ 一个关于"重复验证"的精确判据**：**§443 的 `setModelAt` 避免两次验证（因为第二次会报告错的错误），而 §445 的 `setScriptedMissile` 接受两次验证（因为两次是同一个数，不会报告错的错误）** ⇒ **判据是"第二次会不会报告错的错误"**。

## 八、未闭合点

- `EffectConfigStringCount = 400` 与 `effects 4136` 的关系（带的范围）。
- `positionTime` 允许负值的语义。
- `eFlags 0x1000` 的含义。
- `angle_type` 的 `0`/`1` 分别是什么。
- `position_type` 的 `1`/`2`（线性/重力）的顺序。
- `sv_script_builtin_mp.cpp` 2740 行之后未读取（**共 `4424` 行**）。
