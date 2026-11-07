# 388 · **`sv_snapshot_mp.cpp` 完成** —— 三个"三个 float32 union 字"事件、脚本化位置的四件套、`trigger_` 的两种判定

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 27083–27613 行（文件末尾）。

**更正**：本文件实际 **27,613 行**；此前各报告里的"27,016 行"是错的（把某个中间计数当成总数）。以本报告为准。

## 二、**三个事件共用同一组 union 字**（本组最重要的一段）

### 2.1 `PhysicsExplosionSphere`

```php
// CODREF(Wetwork demo): CODOL moved the sphere's outer radius out of
// eventParm (whose event-131 width is zero) and carries inner radius,
// outer radius, and magnitude as three float32 union words at
// +58/+5C/+60. The client applies them to ragdolls and dynamic props.
entity.networkState.eType = EntityTypePhysicsExplosionSphere;
entity.networkState.eventParm = 0;
entity.networkState.lerpData0058 = bit_cast<uint32>(innerRadius);   // +0x58
entity.networkState.movementDir = bit_cast<int32>(outerRadius);     // +0x5C
entity.networkState.scriptMoverAnimationStartTime = bit_cast<uint32>(magnitude);  // +0x60
```

### 2.2 `RadiusDamage`

```php
// CODREF(Wetwork demo 416950..420200 and out.exe CG_EntityEvent case
// 134): these six event lives carry a float at +58 and integer words at
// +5C/+60. The client's case passes those exact values to 0x004BC960;
// eventParm is zero and is not used by the handler.
entity.networkState.eType = EntityTypeRadiusDamage;
entity.networkState.lerpData0058 = bit_cast<uint32>(effectRadius);  // +0x58
entity.networkState.movementDir = (int32)data1;                     // +0x5C
entity.networkState.scriptMoverAnimationStartTime = data2;           // +0x60
```

### 2.3 `Earthquake`

```php
// CODREF(Wetwork demo ET_EVENTS event 136 and COD4 CG_EntityEvent):
// +58 is camera-shake scale, +5C radius, and +60 duration. Reuse the
// flattened union owners without growing the address-pinned record.
entity.networkState.eType = EntityTypeEarthquake;
entity.networkState.lerpData0058 = bit_cast<uint32>(scale);          // +0x58
entity.networkState.movementDir   = bit_cast<int32>(radius);         // +0x5C
entity.networkState.scriptMoverAnimationStartTime = durationMilliseconds;  // +0x60
```

### 2.4 十一层

```text
1. **三个事件【共用同一组三个 union 字】**（`+0x58` / `+0x5C` / `+0x60`）
2. ⇒ **而每一个的语义完全不同**：
     · PhysicsExplosionSphere：内半径 / 外半径 / 幅度
     · RadiusDamage：效果半径 / data1 / data2
     · Earthquake：抖动 scale / 半径 / 时长
3. ⇒ **而三者都 `eventParm = 0`**
4. ⇒ **因为 event 131 的宽度是【零】**（`PhysicsExplosionSphere` 的注释明说）
5. ⇒ **而 `RadiusDamage` 的 `eventParm` "不被 handler 使用"**
6. ⇒ **"重用扁平的 union 所有者【而不增长那个按地址钉住的记录】"**
7. ⇒ **所以是【第十一次"不能增长按地址键的缓冲区"】**
```

**✅ ⭐⭐ **三个事件、三个 union 字、三套语义** —— 这是本文件里**最极端的"一成员多语义"实例**（第 12–14 次）。**

**⚠ 而"重用扁平的 union 所有者【而不增长那个按地址钉住的记录】"⇒ **明确引用了 §370 的 `184h` 教训**。**

**✅ **第十一次确认那条铁律。**

### 2.5 而 **`eventParm = 0` 的"宽度是零"**

**✅ 与 §342 的"无宽度 ⇒ 参数必须为 0"**第三次确认。**

**⇒ 三层**：

```text
event 131 的 `EntityEventParameterBits` 是 **0**
⇒ 所以 `eventParm` 【不能承载任何东西】
⇒ **所以球的外半径被移到 `+0x5C`**
```

**✅ ⭐ **一个"因为宽度不够所以搬家"的实例**。**

**⚠ 而"CODOL 把球的外半径【移出】 `eventParm`"⇒ **一个逐 build 的重构**。**

**✅ 与 §360 的"逐 eType 的 netfield 表不共享编解码器"**同族（**第四次"逐 build 差异"）。**

## 三、**`bindScriptModelAnimationTree` 的树索引**（本组第二重要）

### 3.1 那段

```php
// CODREF(cl_parse_packet_anims): 5204B4 supplies ES+98 to527370;
// 527290 resolves the registry byte+10 and527433 gives the DObj a tree.
// Without this selector, 540040/5400B0 cannot apply a packet goal.
if (!entityPool_ || !entityPool_->resolve(handle) || !treeIndex || treeIndex > 31)
    return false;
const auto found = entities_.find(handle.entityNum);
if (found == entities_.end() || found->second.mapClassName != "script_model" ||
    found->second.networkState.eType != EntityTypeScriptMover ||
    !found->second.networkState.modelIndex || !found->second.gameplayActive)
    return false;
found->second.networkState.scriptMoverField0098 = treeIndex;
```

### 3.2 十层

```text
1. **`5204B4` 把 `ES+98` 供给 `527370`**
2. ⇒ **`527290` 解析注册表的 `byte+10`**
3. ⇒ **而 `527433` 给 DObj 一个【树】**
4. ⇒ **没有这个选择器，`540040`/`5400B0` 【不能应用一个包目标】**
5. ⇒ **所以 `scriptMoverField0098 = treeIndex`**
6. ⇒ **而 `treeIndex ∈ [1, 31]`**（**5 位**）
```

**✅ 与 §347 的"`0x540040` 解析动画 KEY"**完全闭合 ✓

**⇒ **第二次确认 `0x540040`。**

**⚠ 而"`scriptMoverField0098`"⇒ 与 §365 的"`454`... 不，是 `field0098` 的 `writeUnsignedDelta(5)`"**完全一致 ✓

**⇒ **第三次确认 `0x60` 的那个字段：5 位 / `[1, 31]`。**

## 四、**`setScriptModelAnimation` 与 `setPodiumFigureAnimation` 的差异**（本组第三重要）

### 4.1 `setScriptModelAnimation`（这里）

```cpp
retain({
    .type = SvAnimationCommandType::ClearTree,
    .time = startTime, .entityNum = handle.entityNum,
    .animationKey = 0, .blendTime = 0.2f,
});
retain({
    .type = SvAnimationCommandType::SetGoalWeight,
    .time = startTime, .entityNum = handle.entityNum,
    .animationKey = animationIndex,
    .weight = 1.0f, .rate = 1.0f, .blendTime = 0.2f, .flags = flags,
});
```

### 4.2 `setPodiumFigureAnimation`（§361）

```cpp
if (fadeOutAnimationIndex) append({ SetGoalWeight, animationKey = fadeOutAnimationIndex, weight = 0.0f, ... });
if (clearTree)            append({ ClearTree, ... });
append({ SetGoalWeight, animationKey = animationIndex, weight = 1.0f, ... });
```

### 4.3 三层差异

```text
script_model  ⇒ **【无条件】ClearTree 然后 SetGoalWeight**（两条）
podium_figure ⇒ **【可选】fade-out 然后【可选】ClearTree 然后 SetGoalWeight**（一到三条）
```

**✅ 与 §361 的"零售的退出是 weight-zero → clear-tree → emote-out goal"**完全一致 ✓

**⇒ **第二次确认那三条的顺序。**

**⚠ 而 `script_model` 没有 fade-out ⇒ **因为它是场景动画不是人像。****

**✅ 一个**精确的区分**。

### 4.4 而两者的**共同四步**

```text
① `changed` 检测（index 或 startTime 变）
② 设 `scriptMoverAnimationIndex` / `scriptMoverAnimationStartTime`
③ **`angleTrajectoryDelta = angles`**（两者的网络字）
④ **`scriptMoverField0070 |= 1`**
⑤ 若未变 ⇒ **直接 return true**（不发命令）
⑥ `erase_if` 清同实体的旧命令
⑦ `framesRemaining = 4`
```

**✅ 与 §361 的"`framesRemaining = 4`"**第二次确认。**

**⚠ 而"`angleTrajectoryDelta = angles` 且 `field0070 |= 1`"⇒ **两者的同一对操作**。**

**✅ 与 §361 的"CODREF(retail DM reveal): `+0x48/+0x4C/+0x50` 提供动画的全精度朝向、独立于量化后的 `+0x3C..44`"**完全一致 ✓

**⇒ **第二次确认那三个偏移。**

## 五、**`logicalMapEntityTouchesPlayer` 的两种 `trigger_`**（本组第四重要）

### 5.1 两种

```php
// ① model 字段以 '?' 开头 ⇒ 用触发器表
if (const auto model = logical->second.value("model");
    model && model->size() > 1 && model->front() == '?')
{
    uint16 triggerIndex{};
    const auto [end, error] = std::from_chars(model->data() + 1, model->data() + model->size(), triggerIndex);
    if (error != std::errc{} || end != model->data() + model->size()) return false;
    const auto *const trigger = SV_FindMapTrigger(logicalMapTriggerTable_, triggerIndex);
    return trigger && SV_MapTriggerTouches(*logicalMapTriggerTable_, *trigger,
        playerStateValue->origin, playerBounds.midpoint, playerBounds.halfSize);
}
// ② trigger_radius ⇒ 用 radius + height 构造一个 AABB
if (*className != "trigger_radius" || !logical->second.hasOrigin) return false;
... radius = parsePositiveFloat(...), height = parsePositiveFloat(...)
const std::array triggerMidpoint{ 0.0f, 0.0f, *height * 0.5f };
const std::array triggerHalfSize{ *radius, *radius, *height * 0.5f };
```

### 5.2 十二层

```text
1. **`classname` 必须以 `trigger_` 开头**（`starts_with`）
2. ⇒ **`model` 以 `?` 开头 ⇒ 用【触发器表】**（`?N` 语法）
3. ⇒ **`?N` 的 N 用 `std::from_chars` 解析**
4. ⇒ **严格：解析必须【消耗整个字符串】**
5. ⇒ **否则拒绝**
6. ⇒ **而 `SV_MapTriggerTouches` 做真正的判定**
7. ⇒ **否则必须是 `trigger_radius`**
8. ⇒ **而必须有 origin / radius / height**
9. ⇒ **`radius` 与 `height` 都必须【解析成功且正】**
10. ⇒ **然后构造一个 AABB**：`midpoint = {0,0,h/2}` / `halfSize = {r,r,h/2}`
11. ⇒ **所以圆柱变成 AABB**（一个保守近似）
12. ⇒ **三轴分离测试**
```

### 5.3 ⭐ **`?N` 的严格解析**

**✅ 与 §386 的"`std::from_chars` 必须消耗整个字符串"**同族（**第二次"严格解析"）。**

**⇒ 三层**：

```text
`from_chars` 返回 `(end, error)`
⇒ **`error != errc{}` 或 `end != 末端` ⇒ 拒绝**
⇒ **所以 "?12abc" 被拒**
```

**✅ 一个**正确的严格性**。**

### 5.4 而**"圆柱变成 AABB"**

**⇒ 三层**：

```text
1. `trigger_radius` 的语义是**圆柱**
2. ⇒ **而这里用 AABB 近似**（`halfSize = {r, r, h/2}`）
3. ⇒ **所以角上是【过度包含】的**
```

**⚠ 一个**保守的近似**（会多触发）。**

**✅ 与 §350 的"`logicalMapEntities` 是服务端内部用途"**配合。

## 六、**脚本化位置的四件套**（本组第五重要）

### 6.1 四个函数

```text
setPlayerScriptedPosition     ⇒ origin / pmType / pmFlags + 原生 motion + view link
clearPlayerScriptedPosition   ⇒ 恢复 pmType = Normal / pmFlags = 0
setPlayerScriptedViewAngles   ⇒ viewAngles + **重算 deltaAngles**
setPlayerScriptedViewClamp    ⇒ viewAngleClampBase/Range + view link
setPlayerScriptedLinkState    ⇒ linkAngles / linkFlags + view link
```

**⇒ 五个函数。**

### 6.2 而**共享 `scriptedPlayerPositions_[clientNum]`**

```cpp
struct ScriptedPlayerPosition {
    origin, pmType, pmFlags,
    viewAngles,
    viewAngleClampBase, viewAngleClampRange,
    linkAngles, linkFlags,
};
```

**✅ 一个**状态袋**。**

### 6.3 而**"发布新点即使在没有 usercmd 的那一帧"**

```php
// Publish the new point even on a frame where no usercmd arrived.
state.entity.currentOrigin = origin;
state.entity.networkState.origin = origin;
state.entity.networkState.groundEntityNum = EntityNumNone;
```

**⇒ 四层**：

```text
1. **即使没有 usercmd 也要发布**
2. ⇒ **因为 `pmove` 不会跑**
3. ⇒ **所以实体位置【不会】自动更新**
4. ⇒ **所以显式写三个字段**
```

**✅ 与 §371 的"世界从 pmove 重建 `playerState`"**相反**（这里**pmove 不跑**）。**

**⚠ 而"三个字段"⇒ **实体侧与 `playerState` 侧都写**。**

**✅ 与 §368 的"源/投影/投影的投影"**配合。

### 6.4 而 `setPlayerScriptedViewAngles` 的**重算 `deltaAngles`**

```php
for (axis) {
    playerState.deltaAngles[axis] = viewAngles[axis] - BG_ShortToAngle(owner.commandState->currentUserCmd.angles[axis]);
}
SV_SetNativePlayerStateScriptedViewAngles(owner.nativePlayerState, playerState.viewAngles, playerState.deltaAngles);
```

**⇒ 三层**：

```text
1. **与 §364 的 `teleportFactoryPlayer` 完全相同**
2. ⇒ **`deltaAngles = viewAngles - cmd.angles`**
3. ⇒ **所以预测不能恢复陈旧值**
```

**✅ **第三次确认那个公式**（§364 / §380 / §388）。**

## 七、**`setPlayerShellshock` 的"起始时间晚一个 tick"**（本组第六重要）

### 7.1 那段

```php
// CODREF(C-2021-7-25[22-11-33]coop.demo, 362950): Wetwork's
// magazine blast asserts shellshockIndex=9, duration=14000, and a
// start time one 50 ms server tick behind the publishing snapshot.
// The client expires the effect from this timestamp; retail does not
// send a later clear. BO1 and Ghosts retain the same three-field
// playerState contract (index/start/duration), independently of their
// script-facing shellshock-name lookup.
playerState.shellshockIndex = profileIndex;
playerState.shellshockTime = snapshot_.serverTime >= 50 ? snapshot_.serverTime - 50 : 0;
playerState.shellshockDuration = durationMilliseconds;
// Native Pmove is the source of the next playerState projection. Keep
// it on the same transition so a usercmd cannot restore the old zeroes
// before the first shellshock snapshot is published.
SV_OverlayPlayerStateToNative(playerState, owner.nativePlayerState);
```

### 7.2 十二层

```text
1. **`shellshockIndex = 9`、`duration = 14000`**
2. ⇒ **而起始时间【比发布的快照晚一个 50ms 的服务器 tick】**
3. ⇒ **客户端从这个时间戳【过期】那个效果**
4. ⇒ **零售【不】发一个后续的清除**
5. ⇒ **BO1 与 Ghosts 保留同样的三字段 `playerState` 契约**（index/start/duration）
6. ⇒ **独立于它们的脚本侧 shellshock 名字查找**
7. ⇒ **所以 `shellshockTime = serverTime - 50`**（**有下界保护**）
8. ⇒ **而原生叠加【必须在同一转换上】**
9. ⇒ **否则一个 usercmd 能在第一个 shellshock 快照发布之前【恢复旧的零】**
```

### 7.3 ⭐ **"晚一个 tick"与"源必须同步到原生"**

**✅ 与 §371 的"两个所有者"**第四次确认。**

**⇒ 三层**：

```text
若只写源 ⇒ **下一个 usercmd 的 pmove 从原生重建 ⇒ 恢复零**
⇒ **所以必须同时写原生**
⇒ **否则 shellshock 永远不生效**
```

**✅ **第五次"两个副本必须同步"。**

**⚠ 而"晚一个 50ms tick"⇒ **一个精确的观测**。**

**✅ 与 §372 的"50ms 快照间隔"**第三次确认。

**⚠ 而"`serverTime >= 50 ? serverTime - 50 : 0`"⇒ **下界保护**。**

**✅ 与 §353 的"在减法之前比较"**同族（**第三次"防下溢"）。

## 八、**`setPlayerCanTakeDamage` 的代际保护**

```cpp
if (enabled) playerDamageProtectionGeneration_.erase(clientNum);
else playerDamageProtectionGeneration_.insert_or_assign(clientNum, client->second.client.playerState.spawnGeneration);
```

**⇒ 四层**：

```text
1. **启用受伤 ⇒ 删记录**
2. ⇒ **禁用 ⇒ 记录【当前代际】**
3. ⇒ **所以一个后续世的伤害【不受】前一世的禁用影响**
4. ⇒ **自动按代际失效**
```

**✅ 与 §362 的"`spawnGeneration` 防跨死亡"**第四次确认。**

## 九、`mapEntityField` 的两级

```cpp
if (!entities_.contains(handle.entityNum)) return std::nullopt;
const auto found = logicalMapEntities_.find(handle.entityNum);
if (found != logicalMapEntities_.end())
    if (const auto value = found->second.value(key))
        return std::string(*value);
return std::nullopt;
```

**⇒ 三层**：

```text
1. **先确认实体存在**
2. ⇒ **然后查 `logicalMapEntities_`**
3. ⇒ **所以只有【逻辑实体】有字段**
```

**✅ 与 §386 的 `findMapEntities` 的"逻辑回退"**配合。**

## 十、`spawnPhysicsExplosionSphereEvent` 的七项验证

```cpp
if (!entityPool_ || !std::isfinite(innerRadius) || innerRadius < 0.0f ||
    !std::isfinite(outerRadius) || outerRadius <= 0.0f ||
    outerRadius < innerRadius || !std::isfinite(magnitude) || magnitude <= 0.0f ||
    !all_of(origin, isfinite)) return false;
```

**⇒ 七层**：

```text
① 池存在
② `innerRadius` 有限且 >= 0
③ `outerRadius` 有限且 > 0
④ **`outerRadius >= innerRadius`**
⑤ `magnitude` 有限且 > 0
⑥ `origin` 有限
```

**✅ 与 §388 的 `setPlayerShellshock` 的 `profileIndex ∈ [1, 15]`**同族（**一个值的范围检查**）。

**⚠ 而"`outerRadius < innerRadius` 拒绝"⇒ **一个几何一致性检查**。**

**✅ 一个**正确的语义验证**。

## 十一、关键结论

1. **⚠ 本文件实际 【27,613 行】**；此前各报告的"27,016 行"是错的（把某个中间计数当成了总数）。
2. **⭐⭐ 三个事件（`PhysicsExplosionSphere` / `RadiusDamage` / `Earthquake`）【共用同一组三个 union 字】**（`+0x58` / `+0x5C` / `+0x60`），而**每一个的语义完全不同**。
3. **"重用扁平的 union 所有者【而不增长那个按地址钉住的记录】"`** —— **第十一次确认 §370 的 `184h` 铁律**。
4. **⭐ "event 131 的宽度是零 ⇒ CODOL 把球的外半径【移出】 `eventParm` 到 `+0x5C`"`** —— 一个**因为宽度不够而搬家**的实例。
5. **`bindScriptModelAnimationTree` 的 `treeIndex ∈ [1, 31]`**（5 位）⇒ **第三次确认 `scriptMoverField0098` 的 5 位**。
6. **`0x5204B4` → `527370` → `527290`（注册表 `byte+10`）→ `527433`（给 DObj 一个树）**，而没有它 **`540040`/`5400B0` 不能应用一个包目标**（第二次确认 `0x540040`）。
7. **⭐ `script_model` 与 `podium_figure` 的动画命令差异**：前者**无条件** `ClearTree` + `SetGoalWeight`（两条），后者**可选** fade-out + 可选 `ClearTree` + 新 goal（一到三条）—— 第二次确认那三条的顺序。
8. **两者的共同四步**含 **`angleTrajectoryDelta = angles`** 与 **`scriptMoverField0070 |= 1`**（第二次确认 `+0x48/+0x4C/+0x50`）以及 **`framesRemaining = 4`**（第二次确认）。
9. **⭐ `logicalMapEntityTouchesPlayer` 的两种 `trigger_`**：`model` 以 `?` 开头 ⇒ 用触发器表（`std::from_chars` 严格解析）；否则必须 `trigger_radius` ⇒ 用 `radius` + `height` 构造一个 **AABB**（圆柱的保守近似）。
10. **"`from_chars` 必须消耗整个字符串"** —— 第二次"严格解析"。
11. **⭐ 脚本化位置的五个函数**共享一个状态袋（`origin` / `pmType` / `pmFlags` / `viewAngles` / clamp / link）。
12. **"发布新点即使在没有 usercmd 的那一帧"`** —— 因为 **`pmove` 不跑 ⇒ 实体位置不自动更新**（与 §371 的"从 pmove 重建"相反）。
13. **第三次确认 `deltaAngles = viewAngles - BG_ShortToAngle(cmd.angles)`**（§364 / §380 / §388）。
14. **⭐ `setPlayerShellshock` 的"起始时间比发布的快照晚一个 50ms tick"`** —— 而 **"原生叠加必须在同一转换上，否则一个 usercmd 能在第一个 shellshock 快照发布之前恢复旧的零"`**（**第五次"两个副本必须同步"**）。
15. **`serverTime >= 50 ? serverTime - 50 : 0` 的下界保护** —— 第三次"防下溢"。
16. **`setPlayerCanTakeDamage` 记录【当前代际】⇒ 自动按代际失效** —— 第四次确认 `spawnGeneration`。
17. **`mapEntityField` 的两级**（实体存在 → 逻辑实体字段）。
18. **`spawnPhysicsExplosionSphereEvent` 的七项验证**含 **`outerRadius >= innerRadius`** 的几何一致性。

## 十二、`sv_snapshot_mp.cpp` 全文件完成总结

**27,613 行、1,466,951 字节，报告 313–388（76 份）。**

### 全文件的核心结论（按重要性）

1. **"沉默读起来像健康"** 贯穿全文件（**十一章**）：服务端只数自己的发送；`active=2` 而客户端卡加载屏；`frameReject=none:0` 说被发布的实体验证了而对被过滤的什么也没说；`ack` 冻在 11 而快照继续攀升。
2. **"一个错杀掉全体"（全有或全无）**（**十章**）：帧验证器拒绝整帧 ⇒ 每个客户端都没数据；allowlist 缺一个 eType ⇒ 拒整帧；一个槽的相等 ⇒ 整个装备无效。
3. **"零不是缺席而是索引 0"**（**七章**）：`2047`/`2046`/`0xFFFFFF` 是全一哨兵；用零代替不是"更小的无"而是"索引 0 的那个东西"。
4. **"一偏移多成员"**（**十四章**）：`+0x58`/`+0x5C`/`+0x60` 三个 union 字在十几个 eType 上各有语义；`+0x9C` 至少四个语义。
5. **"逐 build 常数不能移植"**（**五章**）：`64/8` vs `19/18`；`IW4 key4` vs `CODOL action1`；eFlags 左移两位。
6. **"两个副本必须同步"**（**六章**）：源 `playerState` 与原生 `nativePlayerState`；只改一个 ⇒ 下一帧被覆盖。
7. **"事务性"**（**十一次**）：staged-then-commit、swap 回滚、`node_type` 零拷贝、逆序回滚、成功后提交。
8. **"工具/扫描的盲区"**（**七次**）：目录级 grep 跳过二进制；`[reg+12Ch]` 的扫描因为基址错而假负面；三种 `memcpy` 编码都缺席不等于没有拷贝。
9. **"采样偏差"**（**五次**）：从几个样本读速度；从前 40 帧读稳态；采样动画之间的空隙；小样本 + 分布偏移。
10. **"实测优先于推断"**（**七次**）：崩溃说 `demoq` 是对的；the traffic wins；去问键盘不要问镜像；一个编解码器不是一个类型。

### 关键地址速查

```text
0x671170   MSG_ReadDeltaEntity（实体 delta 读取器）
0x6701D0   单字段读
0x670CB0   读跳号
0x670160   -55 四 present-bit 组的读者
0x670BF5   -80/-78/-73/-71 裸 long 派发器
0x67042C   -75 紧凑分支（baseline + ReadBits(3) + 1）
0x670448   -75 回退（8 位 XOR）
0x0046D170 CL_ParseSnapshot
0x0047222E..0x00472268  基线选择（距离 + 标志）
0x0046D170 SnapshotBaselineFlag 判据
0x515C90   CL_FirstSnapshot（gate 在 snapFlags & 2）
0x515DAE   cls.state = 10
0x00541800 CG_SetupClientCharacterInfo（clientState+0x150 > 0 才写模型）
0x00541814 早退
0x0040ABD2 BG_UpdatePlayerDObj 拒绝活玩家
0x0040AB30 测试两个 tag id
0x0040B700 门控武器在 0xC00
0x0053DF40 从 entityState+0xA0 挑 clientInfo
0x00788  … 动画树族（7886D0 / 785870 / 7891D0 / 789570 / 787490 / 787100 / 78B570）
0x00540040 动画 KEY 解析（record+20 / record+32）
0x005400B0 接受时间戳并推进全局地板
0x006718  … 动画命令（671730 头 / 471C90 列表 / 6717E0 记录读 / 671650 别名表 / 6715D0 权重 / 671550 速率 / 6714D0 blend）
0x00DA8078 clientInfo netfield 表（87 项，stride 12）
0x00DA8078 字段 36 = offset 4 / width 11 / type 0
0x0DA4608  ET_GENERAL 描述符
0x0DA5DE8  ET_ACTOR netfield 表（63 字段）
0x0DA6528  ET_ITEM（63 描述符）
0x0DA6828  ET_SCRIPTMOVER
0x0DA7A20  Missile（63 描述符）
0x0DA5E…   ET_ACTOR_CORPSE（0x00DA60E8）
0x0BA7500  绘制分发（eType 1 / 2 都进 BB88E0）
0x0BB88E0  真正的绘制（centity+0x204 bit 0）
0x0BB89E0  动画状态初始化
0x0BB56A5  sub_BB5680 材质拒绝
0x0BB4C6F  sub_BB4B70 字形高度
0x0BD8B7A  waypoint material > 0
0x0BD8B12  （在 out.exe 里落在 sub_BD7780 = r_picmip / r_specular）
0x0BB86BD  test [edi+8], 200000h（尸体 eFlags）
0x0411280  BG_PlayerStateToEntityState_CopyEvents
0x0DADC0C  服务端专属 id 数组（10 个）
0x0DADBB8  非联网 id 数组（20 个）
0x00DAA400 UI 脚本内置函数表
0x00E4FB30 命中位置名表
0x00E5FD38 eventnames 表（163 项）
0x0DA9410  事件参数宽度表（170 项）
0x0426B9F..0x0426BAC  BG_AddEvent
0x0462741  CG_CheckPlayerstateEvents
0x00411280 同上
0x00520000 区间（5204B4 / 527290 / 527370 / 527433 / 520263 / 51FE00 / 527500）
0x004BC960  半径伤害/物理球的消费者
0x004E8E70  G_FreeEntity
0x00530AF0  尸体表现所有权（native32 槽）
0x0053…     530BB0 / 530C90 / 52FBE0 / 52FBE0 / 530E70
0x0046DAE0  packed type19 胶囊裁剪（contents 1）
0x0046D6E0  内缩 bounds
0x00413E60  start-solid 重试（移除 02004000）
0x00429470  finish-drop 转换（ps+0x3F8 = pmove+0x18）
0x00429E10  从 ps+0x3E8/+0x3EC/+0x3F0 选择
0x00429DA0  需要 ps+0x254 != 2047（捡武器）
0x00425440  确认 0x100000 = ADS
0x0040E140 / 4327E0 / 4329E0  走 +0x2F4 武器列表
0x0041CB40  冻结的输入/速度门
0x0041CB97 / 41CDCA..41CDE3
```

### 关键常量速查

```text
EntityNumWorld        2046
EntityNumNone         2047
MaximumServerCollisionEntityNum  2045
ModelConfigStringCount       1024
WeaponConfigStringCount      1700
BaseWeaponAssetCount         0x514 = 1300
MaximumWeaponAssetIndex      0x7FF
MaxCurrentWeaponAssetIndex   （≤0x7FF）
firstDynamicWeapon           1224（或 1147 是第一个模块化）
材质 configstring 带         4872
标签带                       5896（+28 = cs 5924 = tag_stowed_back）
武器带                       5960
模型带                       2568
声音别名带                   3624
效果 configstring 基址        4136
提示字符串带                 +856
HUD 图标材质基址             4355
configstring 11990            ET_EVENTS event 130 的解析基址
clientState stride           0x160 = 352（clientInfo）
                             0x58 = 88（clientState_s）
entityState memcpy 尺寸       280 = 0x118
bmodel stride               60
centity stride              624
agent 记录                   684
corpse memcpy                952
SnapshotSceneBlockFlags      0x0A（= 0x08 | 0x02）
SnapshotBaselineFlag         0x08
SnapshotFirstSnapshotFlag    0x02
SnapshotUseEntityBaselinesFlag 0x10
SvCorpseReinitialiseFlag     0x80000
客户端 0x20000 = 跳过动画初始化（不阻止绘制）
SvEFlagsNoDraw               16
SvEFlagsIntermission         （= 16？）
SvPmFlagsMatchEndFrozen      0x800
otherFlags FOLLOWING         0x2800
ActorCorpseRingSize          32
PlayerCorpseRingSize         18（OLfinal 19..36）或 8（IW3 64..71）
```

## 十三、未闭合点

- `SvCorpseRagdollTrajectoryType` / `SvCorpseRagdollAngleTrajectoryType` 的具体值。
- `ActorCorpseLerpPrefix` 的值。
- 三个 union 字事件（球/半径/地震）的 eType 数值。
- `SvAgentState` 的完整字段表。
- `mapEntityField` 与 `findMapEntities` 的 `key` 全表。
- **`sv_main_mp.cpp`（657,426 B）及其余 `server_mp` 文件尚未读取。**
