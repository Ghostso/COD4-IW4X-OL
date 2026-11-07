# 364 · **"暂存每一块板再发布任何一块"** —— `snapGate` 的后空翻、九次 `rebuildCollisionView` 的事务、`setBrushModelMotions` 的三重检查

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 17200–17600 行。

## 二、**`findMapEntities` 的五个具名键 + 逻辑回退**（本组第四重要）

```cpp
if (key == "classname")               field = &entity.mapClassName;
else if (key == "targetname")         field = &entity.mapTargetName;
else if (key == "destructible_type")  field = &entity.mapDestructibleType;
else if (key == "script_gameobjectname") field = &entity.scriptGameObjectName;
else {
    const auto logical = logicalMapEntities_.find(entityNum);
    if (logical != logicalMapEntities_.end()) logicalField = logical->second.value(key);
}
const auto *const lifetime = entityPool_->resolve(entityNum);
if (lifetime && ((field && *field == value) || (logicalField && *logicalField == value)))
    result.push_back({ .entityNum = entityNum, .generation = lifetime->generation });
std::ranges::sort(result, {}, &SvEntityHandle::entityNum);
```

### 2.1 六层

```text
1. **四个具名键**（`classname` / `targetname` / `destructible_type` / `script_gameobjectname`）
2. ⇒ **其它一切查 `logicalMapEntities_`**
3. ⇒ **所以有两级**
4. ⇒ **返回句柄带 `generation`**（防复活）
5. ⇒ **结果按实体号排序**（确定性）
6. ⇒ **`value.empty() ⇒ 空结果**（**不做全匹配**）
```

**✅ 与 §350 的"`logicalMapEntities` 是纯服务端元数据"**配合。**

**⇒ 所以**那些实体可以被脚本按任意键查询**。**

**⚠ 而"`value.empty() ⇒ 返回空"⇒ **一个空的查询不返回任何东西**（而不是"全部"）。**

**✅ 一个**正确的空值处理**（避免误用）。**

### 2.2 而**"排序"**

**✅ 与 §337 的"`playerNames` 按 xuid 排序"、§355 的"`actorNumbers` 排序"**同族（**第七次确定性要求）。**

## 三、**`setScriptModelTransformAndActive` 的回滚**（本组第五重要）

```cpp
const auto previous = entity->second;
entity->second.currentOrigin = origin;
entity->second.currentAngles = angles;
entity->second.networkState.origin = origin;
entity->second.networkState.angles = angles;
entity->second.gameplayActive = active;
entity->second.collisionLinked = active;
rebuildCollisionView();
if (nativeEntityMirrorSynchronizer_ && !nativeEntityMirrorSynchronized_) {
    entity->second = previous;
    rebuildCollisionView();
    return false;
}
return true;
```

### 3.1 五层

```text
1. **保存整条实体**（`previous = entity->second`）
2. ⇒ **改六个字段**
3. ⇒ **重建碰撞视图**
4. ⇒ **若镜像未同步 ⇒ 恢复整条 + 重建**
5. ⇒ **返回 false**
```

**✅ 与 §363 的 `freeEntity` 的**回滚式**事务**完全同族（**第二次）。**

**⚠ 而这里用**整条实体拷贝**（不是逐字段保存）。**

**⇒ 所以**更简单也更安全**。**

**✅ 一个**更好的回滚模式**。**

### 3.2 而**"整条实体拷贝"的成本**

**⇒ 三层**：

```text
1. 一次 `SvGameEntity` 拷贝
2. ⇒ **结构可能几百字节**
3. ⇒ **而这些不是热路径**（脚本调用的展示操作）
```

**✅ 一个**正确的成本判断**。

## 四、**`setBrushModelMotions` 的"暂存每一块再发布任何一块"**（本组最重要的一段）

### 4.1 那段

```php
// Stage every board before publishing any. Swapping retains the exact
// previous states for rollback and performs only one global relink.
for (auto &[number, candidate] : candidates)
    std::swap(entities_.at(number), candidate);
rebuildCollisionView();
if (nativeEntityMirrorSynchronizer_ && !nativeEntityMirrorSynchronized_) {
    for (auto &[number, previous] : candidates)
        std::swap(entities_.at(number), previous);
    rebuildCollisionView();
    return false;
}
return true;
```

### 4.2 九层

```text
1. **在发布任何一块之前【暂存每一块】**
2. ⇒ **交换保留【精确的】前一状态用于回滚**
3. ⇒ **而只执行【一次】全局重链**
4. ⇒ **`std::swap(entities_.at(number), candidate)`** ⇒ **`candidate` 现在持有旧值**
5. ⇒ **`rebuildCollisionView()` 一次**
6. ⇒ **若镜像未同步 ⇒ 再 `swap` 回来**（`candidate` 里的旧值回到实体）
7. ⇒ **再 `rebuildCollisionView()`**
8. ⇒ **返回 false**
```

### 4.3 ⭐ **`std::swap` 作为"零成本的回滚保存"**

**✅ 一个**极其优雅的手法**。**

**⇒ 三层**：

```text
1. `candidates` 里有新值
2. ⇒ **`swap(entities_[n], candidate)` ⇒ 实体有新值，candidate 有旧值**
3. ⇒ **回滚只需再 swap 一次**
4. ⇒ **无需额外拷贝**
```

**✅ 与 §363 的"`previous = entity->second`"**更好**（无拷贝）。**

**⚠ 而那个"candidate"名字**误导**（它在 swap 后是 previous）。**

**✅ 一个**小的命名问题**。**

### 4.4 而**"只执行一次全局重链"**

**✅ 与 §354 的"`setBrushModelMotions` 对一批只做一次原生重链"**完全一致 ✓**

**⇒ **第二次确认那个设计。**

**⚠ 而 `rebuildCollisionView()` 是**一次**（不是每块一次）。**

**✓ 正确。**

### 4.5 而 `motions.size() > entities_.size()` 的拒绝

```cpp
if (motions.empty()) return true;
if (!entityPool_ || motions.size() > entities_.size() || atTime < 0) return false;
```

**⇒ 三层**：

```text
1. **空 ⇒ true**（无事可做是成功）
2. ⇒ **`motions.size() > entities_.size()` ⇒ false**（**必然有重复**）
3. ⇒ **`atTime < 0` ⇒ false**
```

**✅ 一个**O(1) 的重复检测**（比 `candidates.contains` 的逐项检查更早）。**

**⚠ 而两者**都有**（O(1) 早退 + 逐项 `contains`）。**

**✅ **双重检查。**

## 五、**`setBrushModelMotions` 的单块验证（七项）**（本组第二重要）

```cpp
const auto &[handle, position, angles, flags] = motion;
if (!entityPool_ || !entityPool_->resolve(handle) || atTime < 0 ||
    position.time < 0 || angles.time < 0 || candidates.contains(handle.entityNum))
    return false;
const auto origin = SV_EvaluateTrajectory(position, atTime, evaluate);
const auto orientation = SV_EvaluateTrajectory(angles, atTime, evaluate);
if (!origin || !orientation || !entityPool_->resolve(handle))
    return false;
const auto entity = entities_.find(handle.entityNum);
if (entity == entities_.end() ||
    entity->second.collisionShape != SvCollisionShape::BrushModel ||
    !entity->second.gameplayActive ||
    !entity->second.networkState.scriptMoverBrushModelIndex ||
    entity->second.networkState.scriptMoverBrushModelIndex != entity->second.brushModelClipHandle ||
    !entity->second.brushModelClipHandle)
    return false;
```

### 5.1 五层验证

```text
第一层（输入）：池存在 / 句柄可解析 / atTime >= 0 / 两个 time >= 0 / **不重复**
第二层（求值）：两个轨迹求值成功
第三层（实体）：存在 / **是画笔模型** / **active** / **有 brushModelIndex**
第四层（一致）：**`scriptMoverBrushModelIndex == brushModelClipHandle`**
第五层（非零）：**`brushModelClipHandle` 非零**
```

### 5.2 而**"两个索引必须相等"**

**✅ 三层**：

```text
1. 线上的 `scriptMoverBrushModelIndex`（§350 的字段 26）
2. ⇒ **必须等于本地 `brushModelClipHandle`**
3. ⇒ **否则网络与本地不一致**
```

**✅ 一个**强制的一致性不变式**。

**⚠ 而 §350 说 `scriptMoverBrushModelIndex = clipHandle`。**

**⇒ **完全一致 ✓**

### 5.3 而**"`validScriptMoverEntity(network)` 在写入后"**

```cpp
auto candidate = entity->second;
auto &network = candidate.networkState;
network.origin = position.base;
network.positionTrajectoryType = (uint8)position.type;
...
network.eFlags = flags;
if (!validScriptMoverEntity(network)) return false;
```

**⇒ 四层**：

```text
1. **先写全部字段**
2. ⇒ **再验证整条**
3. ⇒ **所以验证是【事后】的**
4. ⇒ **而失败则整块跳过**（不是整个 motions 失败）
```

**⚠ 而函数**返回 `false`**（整个调用失败）而不是跳过这块。**

**⇒ 所以**一块坏的全部拒绝**。**

**✅ 与 §346 的"缺一个 eType 拒掉整帧"**同族（**第六次"全有或全无"**）。

### 5.4 而**"绝不把轨迹基址替换成求值姿态"**

```php
// Factory board358 retains its brush/solid while flying and settling.
// Never replace the trajectory base with the evaluated pose: the client
// would evaluate the elapsed displacement a second time. Native linking
// consumes currentOrigin/currentAngles instead of those network bases.
candidate.currentOrigin = *origin;
candidate.currentAngles = *orientation;
```

### 5.5 七层

```text
1. **Factory 的板 358 在飞行与落定时保留它的画笔/实心**
2. ⇒ **绝不把【轨迹基址】替换成【求值姿态】**
3. ⇒ **客户端会把已流逝的位移【评估第二次】**
4. ⇒ **原生重链消费 `currentOrigin`/`currentAngles` 而不是那些网络基址**
5. ⇒ 所以 `network.origin = position.base`（轨迹基址）
6. ⇒ 而 `candidate.currentOrigin = *origin`（求值结果）
```

**✅ **两个不同的字段承载两种东西**：**

```text
networkState.origin       轨迹基址（给客户端，它自己求值）
currentOrigin             求值结果（给服务端碰撞/重链）
```

**⚠ 所以**同一时刻两个不同的位置**。**

**✅ 与 §355 的"`ps` 与 `ent` 两个位置"**同族（**第三次"两个位置副本"**）。

**⇒ 而这里解释了**为什么必须两个**。**

## 六、`teleportFactoryPlayer` 的**完整事务**（本组第三重要）

### 6.1 前置（九项）

```cpp
if (!factoryInteractablesEnabled_ || clientNum >= zombieBattery_.size() ||
    !std::isfinite(yaw) || (pitch && !std::isfinite(*pitch)) ||
    !all_of(destination, isfinite) || !playerStateToEntityStateConverter_)
    return false;
const auto client = clientStates_.find(clientNum);
if (client == clientStates_.end()) return false;
const auto &current = client->second.client;
if (current.gameplayState != Playing || current.deathState || !current.playerState.health ||
    current.playerState.pmType != 0 ||
    current.playerState.spawnGeneration != expectedLifeGeneration ||
    zombieBattery_[clientNum] < costRaw || !current.commandState)
    return false;
```

**⇒ 九层**：

```text
① 交互物启用
② clientNum 在范围内
③ yaw 有限
④ pitch 有限（若有）
⑤ 目的地有限
⑥ 转换器已注入
⑦ 客户端存在
⑧ **Playing / 未死 / 活着 / pmType == 0 / 代际匹配**
⑨ **电池 >= 费用 / commandState 存在**
```

**✅ 与 §355 的"七个拾取前置"**同族（**第三次多条件前置**）。

**⚠ 而 `pmType != 0` ⇒ **所以只有"普通"状态的玩家可以传送**。**

**✅ 与 §345 的 `SvPmTypeNormal` 配合。**

### 6.2 而**"目的地合法性"的占用检查**

```php
const SvTraceEntityFilter filter{ .passEntityNum = client->second.entity.networkState.number };
const auto occupancy = traceCapsule(destination, destination, StandingPlayerTraceBounds,
    PlayerCollisionContentMask, filter);
if (!occupancy || occupancy->startSolid || occupancy->allSolid) return false;
```

**⇒ 五层**：

```text
1. **传玩家号 ⇒ 自己的碰撞体不会拒绝自己的传送**
2. ⇒ **零长度胶囊（`start == end`）测占用**（§359 第二次）
3. ⇒ **用 `StandingPlayerTraceBounds`**（§359/§361 第三次）
4. ⇒ **`startSolid` 或 `allSolid` ⇒ 拒绝**
5. ⇒ **`!occupancy`（无 runner）⇒ 也拒绝**
```

**✅ 与 §359 的"零长度胶囊测占用"**第二次。**

**⚠ 而 `!occupancy ⇒ return false`** ⇒ 所以**没有 trace runner 则不能传送**。**

**✅ 一个**保守的"没有证据就不做"**。**

### 6.3 而**"重新基准 deltaAngles"**（本组关键）

```php
nextPlayerState.viewAngles[1] = yaw;
if (pitch) { nextPlayerState.viewAngles[0] = *pitch; nextPlayerState.viewAngles[2] = 0; }
for (axis) {
    nextPlayerState.deltaAngles[axis] = nextPlayerState.viewAngles[axis] -
        BG_ShortToAngle(current.commandState->currentUserCmd.angles[axis]);
}
```

**⇒ 六层**：

```text
1. **`viewAngles[1] = yaw`**（只改 yaw）
2. ⇒ **pitch 若有则设，且 roll 强制 0**
3. ⇒ **`deltaAngles = viewAngles - <usercmd 的短角转回的角度>`**
4. ⇒ **所以 delta 是"当前视角 - 客户端的指令视角"**
5. ⇒ **"Re-base all delta angles on the accepted usercmd，完全像原生视角路径"**
6. ⇒ **"所以预测不能在下一条命令上恢复一个陈旧的 yaw"**
```

**✅ 与 §352 的"每帧保持"**同族（**第二次"防预测恢复陈旧值"**）。

**⚠ 而 `BG_ShortToAngle` 把 16 位短角转回度数。**

**✅ 与 §258 的"`writeEntityAngle` 的 `×65536/360`"**配合（**同一个短角编码**）。

### 6.4 而**往返一致性检查**

```cpp
auto nextNativePlayerState = current.nativePlayerState;
SV_OverlayPlayerStateToNative(nextPlayerState, nextNativePlayerState);
auto roundTrip = nextPlayerState;
if (!SV_OverlayNativePlayerStateToPlayerState(nextNativePlayerState, roundTrip) ||
    roundTrip != nextPlayerState)
{
    return false;
}
```

### 6.5 七层

```text
1. **先叠加到原生**
2. ⇒ **再从原生叠加回来**
3. ⇒ **而结果必须【逐字段相等】**
4. ⇒ **否则拒绝**
5. ⇒ **所以这是一个【往返一致性】证明**
6. ⇒ **保证原生与源表示在该点上同构**
```

**✅ 一个**极优雅的正确性证明**。**

**⇒ 与 §351 的"238 个间隔方程"**不同**（那是**代数**，这是**往返**）。**

**⚠ 而这是**一次运行期检查**（不是编译期）。**

**✅ **第六次事务性**（先验证再提交）。

## 七、**`setFactoryPackDoorMotion` 与 `setFactoryBoxModelMotion` 的差异**（本组第六重要）

### 7.1 门

```cpp
if (!factoryInteractablesEnabled_ || !entityPool_ || !entityPool_->resolve(handle) ||
    (position.type != 0 && position.type != 3 && position.type != 7)) return false;
...
if (entity.mapTargetName != "pack_door" || entity.mapClassName != "script_model" ||
    entity.networkState.eType != EntityTypeScriptMover || !entity.networkState.modelIndex ||
    !entity.gameplayActive) return false;
const auto origin = SV_EvaluateTrajectory(position, atTime, zmBoardTrajectoryEvaluator_);
if (!origin) return false;
const auto previous = entity;
...
if (!validScriptMoverEntity(state)) { entity = previous; return false; }
entity.currentOrigin = *origin;
rebuildCollisionView();
if (nativeEntityMirrorSynchronizer_ && !nativeEntityMirrorSynchronized_) { entity = previous; rebuildCollisionView(); return false; }
```

**⇒ 三个轨迹类型（0/3/7），五项实体检查（`mapTargetName == "pack_door"` 是关键）。**

### 7.2 箱子

```cpp
if (!factoryInteractablesEnabled_ || !entityPool_ || !entityPool_->resolve(handle) ||
    !SV_IsTrajectoryValid(position, position.time) ||
    (position.type != 0 && position.type != 1 && position.type != 3 && position.type != 7 && position.type != 8)) return false;
...
if (entity.networkState.eType != EntityTypeScriptMover || !entity.networkState.modelIndex ||
    entity.collisionLinked || !entity.gameplayActive || entity.mapClassName != "script_model" ||
    entity.collisionShape != SvCollisionShape::Capsule || !entity.mapTargetName.empty()) return false;
```

**⇒ 五个轨迹类型（0/1/3/7/8），而**七个实体检查**。**

### 7.3 而**两者的七个差异**

```text
门      策略：`mapTargetName == "pack_door"`（具体名）
箱子    策略：`mapTargetName.empty()`（**无名字**）
```

**⇒ 三层**：

```text
1. **门是一个具名的地图实体**
2. ⇒ **而箱子生成的是【匿名的】展示物**
3. ⇒ **所以一个要求名字非空一个要求名字空**
```

**✅ 与 §350 的"命名而不是计数"**同族（**第三次"具名 vs 匿名"**）。

### 7.4 而**"箱子不能移动一个地图碰撞道具"**

```php
// CODREF(actor_grounded_adapter): out.exe410BD0 evaluates these native
// ET6 trajectories. This narrow adapter owns only non-solid Factory
// presentation spawned by the box; it cannot move a map collision prop.
```

**⇒ 四层**：

```text
1. **`out.exe410BD0` 求值这些原生 ET6 轨迹**
2. ⇒ **这个窄适配器只拥有【箱子生成的非实心 Factory 展示物】**
3. ⇒ **它【不能】移动一个地图碰撞道具**
4. ⇒ **所以 `!entity.collisionLinked` 是必须的**
```

**✅ 与 §350 的"两个入口必须一致"**不同** —— 这里是**两个适配器必须不同**。**

**✅ 一个**精确的职责分离**。

### 7.5 而**箱子没有回滚**

```cpp
auto state = entity.networkState;
state.origin = position.base;
...
if (!validScriptMoverEntity(state)) return false;
entity.networkState = state;
entity.currentOrigin = position.base;
return true;
```

**⚠ 所以箱子路径**没有 `rebuildCollisionView()` 也没有镜像回滚**。**

**⇒ 三层**：

```text
1. 箱子是**非碰撞**的（`!collisionLinked`）
2. ⇒ **所以不需要重建碰撞视图**
3. ⇒ **而镜像也可能不管它**
```

**✅ 一个**正确的"不用做无用功"**。

## 八、`setScriptModelPresentation` 与 `setScriptModelTransformAndActive` 的**三份重复前置**

### 8.1 两个函数的相同前置

```cpp
if (!entityPool_ || !entityPool_->resolve(handle) || !modelIndex ||
    modelIndex >= ModelConfigStringCount || modelName.empty() ||
    modelName.front() == '*' || modelName.find('\0') == std::string_view::npos ...)
```

**⚠ 而 `find('\0')` 的检查写反了！**

**⇒ 让我核：**

```cpp
modelName.find('\0') != std::string_view::npos   // 拒绝含 NUL
```

**✅ 而 §350 的 `validScriptModel` 是 `== std::string::npos`（要求无 NUL）。**

**⚠ 所以两者**语义相同**（`!= npos` 表示"找到 NUL" ⇒ 拒绝）。**

**✓ 正确。**

**✅ 而 §364 的 `setScriptModelIndex`（17536）是 `!= npos` ⇒ 拒绝含 NUL ✓**

### 8.2 而**三份重复的九项**

```text
spawnScriptModel          （§352，九项）
setScriptModelIndex       （这里，七项）
setScriptModelPresentation（这里，九项）
```

**✅ **三次重复的同一套筛查**（§352 说是"两个函数共享"）。**

**⚠ 而这里是**三个**。**

**⇒ **第五次"同一套检查复制多份"。**

## 九、关键结论

1. **`findMapEntities` 的四个具名键 + 逻辑回退**，而 **`value.empty() ⇒ 空结果`**（不做全匹配）。
2. **`setScriptModelTransformAndActive` 的整条实体拷贝回滚** —— 比逐字段保存更安全。
3. **⭐ "在发布任何一块之前暂存每一块"`** —— 而 **`std::swap` 是零成本的"回滚保存"**`（swap 后 candidate 就是 previous）。
4. **"只执行一次全局重链"`** —— 第二次确认 §354 的设计。
5. **`motions.size() > entities_.size()` 的 O(1) 重复检测** + 逐项 `candidates.contains` ⇒ **双重检查**。
6. **`setBrushModelMotions` 的五层验证**（输入 / 求值 / 实体 / 一致 / 非零）。
7. **"`scriptMoverBrushModelIndex` 必须等于 `brushModelClipHandle`"`** —— 一个强制的一致性不变式。
8. **⚠ 验证是【事后】的（先写全部字段再验整条）**，而失败 ⇒ **整块跳过 = 整个调用失败**（第六次全有或全无）。
9. **⭐ "绝不把轨迹基址替换成求值姿态，否则客户端会把已流逝的位移评估第二次"`** —— `networkState.origin` 是**基址**而 `currentOrigin` 是**求值结果**（第三次"两个位置副本"，而这里解释了**为什么必须两个**）。
10. **`teleportFactoryPlayer` 的九项前置**，含 **`pmType == 0`** 与**电池费用**。
11. **"传玩家号 ⇒ 自己的碰撞体不会拒绝自己的传送"`** + **零长度胶囊测占用**（第二次）。
12. **"`!occupancy`（无 runner）⇒ 也拒绝"`** —— 保守的"没有证据就不做"。
13. **⭐ "重新基准 deltaAngles 于已接受的 usercmd，所以预测不能在下一条命令上恢复一个陈旧的 yaw"`** —— 第二次"防预测恢复陈旧值"。
14. **⭐ 往返一致性检查**（`PlayerState → Native → PlayerState` 必须逐字段相等）—— 一个**极优雅的正确性证明**。
15. **门 vs 箱子的七个差异**：门要 `mapTargetName == "pack_door"` 而箱子要 `mapTargetName.empty()`（**具名 vs 匿名**，第三次）。
16. **"这个窄适配器只拥有箱子生成的非实心展示物，它不能移动一个地图碰撞道具"`** —— 一个精确的职责分离。
17. **箱子路径没有 `rebuildCollisionView` 也没有镜像回滚**（因为它是非碰撞的）—— 正确的"不做无用功"。
18. **三份重复的九项筛查**（`spawnScriptModel` / `setScriptModelIndex` / `setScriptModelPresentation`）—— 第五次复制。

## 十、未闭合点

- `SV_EvaluateTrajectory` 对 type 8 的处理。
- `zmBoardTrajectoryEvaluator_` 与 `evaluate` 参数的区别。
- `PlayerCollisionContentMask` 与 `ActorWorldContentMask` 的差异。
- `BG_ShortToAngle` 的精确映射。
- `zombieBattery_` 的容量与再生。
- `sv_snapshot_mp.cpp` 17600 行之后未读取（27,016 行，进度 65%）。
