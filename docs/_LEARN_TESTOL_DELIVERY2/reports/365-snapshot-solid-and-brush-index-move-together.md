# 365 · **"实心与画笔模型索引必须一起动，否则帧验证器拒绝整条实体"** —— `238` 个实体的配对、`0x400` 的 clip 上限、八块电源的双阶段

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 17600–18000 行。

## 二、**`solid` 与 `brushModelIndex` 的强制配对**（本组最重要的一段）

### 2.1 那段

```php
// SOLID AND THE BRUSH MODEL INDEX MOVE TOGETHER OR THE FRAME VALIDATOR
// REJECTS THE ENTITY -- and a rejected entity takes the whole frame for
// every client with it. They are paired because retail pairs them: in
// the shipped const baselines +0x0AC == 0xFFFFFF and +0x09C != 0 hold on
// exactly the same 238 entities.
entity->second.networkState.scriptMoverBrushModelIndex = active
    ? static_cast<std::uint16_t>(model.clipHandle)
    : 0;
```

### 2.2 十层

```text
1. **`solid` 与画笔模型索引【一起动】否则帧验证器拒绝整条实体**
2. ⇒ **而一条被拒的实体带走【每一个客户端】的整帧**
3. ⇒ **它们被配对因为【零售配对它们】**
4. ⇒ **在已发货的 const 基线里，`+0x0AC == 0xFFFFFF` 与 `+0x09C != 0`**
5. ⇒ **恰好在【同样的 238 个实体】上成立**
6. ⇒ 所以 `active ? clipHandle : 0`
```

### 2.3 ⭐ **"同样的 238 个实体"**

**✅ 与 §350 的"带画笔模型索引的 238 个恰好是携带 `0x00FFFFFF` 的那 238 个"**完全一致 ✓**

**⇒ **第三次确认 238。**

**✅ 而这里是**从 `solid` 侧**论证同一件事**（双向）。**

**⇒ **一个完整的配对证明**。

### 2.4 而**"一条被拒的实体带走每一个客户端的整帧"**

**✅ 与 §346 的"缺一个 eType 拒掉整帧"**第三次确认。

**⇒ 三层**：

```text
1. 验证器是**帧级**的
2. ⇒ **一条坏实体 ⇒ 整帧拒**
3. ⇒ **而整帧拒 ⇒ 每个客户端都没数据**
```

**✅ **一个极端的放大**（1 → 全体）。

## 三、**`clipHandle < 0x400` 的三次检查**（本组第四重要）

### 3.1 三处

```text
§350  `definition.collision.clipHandle >= 0x400` ⇒ 拒绝
§352  `definition.collision.clipHandle >= 0x400` ⇒ 拒绝
§365  `model.clipHandle >= 0x400` ⇒ 拒绝
```

**✅ 与 §350 的"`logicalMapEntity` 的 NUL 检查出现三次"**同族（**第二次三处重复**）。

**⚠ 而 `0x400 = 1024`。**

**⇒ 所以**clipHandle 上限 1023**。**

**✅ 与 §350 的 `scriptMoverBrushModelIndex <= 0xFFF`（4095）**不同**。**

**⚠ 所以**clipHandle 的界（1024）比 brushModelIndex 的界（4096）小**。**

**✅ **一个较紧的界**（碰撞句柄）。

## 四、**`linkEntityCollision` 的"转换"语义**（本组第五重要）

### 4.1 那段

```php
const auto previous = entity->second;
entity->second.ownerEntityNum = ownerEntityNum;
entity->second.currentOrigin = origin;
entity->second.currentAngles = {};
entity->second.collisionBounds = bounds;
entity->second.collisionShape = SvCollisionShape::Capsule;
entity->second.brushModelClipHandle.reset();
entity->second.scriptGameObjectName.clear();
entity->second.mapClassName.clear();
entity->second.mapTargetName.clear();
entity->second.mapDestructibleType.clear();
entity->second.mapModeEligible = true;
entity->second.collisionContents = contents;
entity->second.gameplayActive = true;
entity->second.collisionLinked = true;
entity->second.networkState.solid = *solid;
// This entity is no longer a brush model -- brushModelClipHandle was
// just reset above -- so the brush model index has to go with it, or a
// converted entity carries an index with a non-brush solid and fails
// the frame validator's pairing.
entity->second.networkState.scriptMoverBrushModelIndex = 0;
```

### 4.2 九层

```text
1. **角清零**（`currentAngles = {}`）
2. ⇒ **`brushModelClipHandle.reset()`**
3. ⇒ **四个字符串清空**（`scriptGameObjectName` / `mapClassName` / `mapTargetName` / `mapDestructibleType`）
4. ⇒ **`mapModeEligible = true`**
5. ⇒ **`solid = *solid`**（玩家实心）
6. ⇒ **`scriptMoverBrushModelIndex = 0`**
7. ⇒ **所以一个"变形"的实体彻底丢弃它原来的身份**
8. ⇒ **而注释解释为什么 `brushModelIndex` 必须清**
```

**✅ 与 §365 二 的"配对"**完全闭合 ✓**

**⇒ 三层**：

```text
`brushModelClipHandle` 被 reset（本地）
⇒ **所以 `scriptMoverBrushModelIndex` 也必须清（线上）**
⇒ **否则"一个索引配一个非画笔的实心" ⇒ 验证器拒绝**
```

**✅ **一个严格的因果链**。

### 4.3 而**`ownerEntityNum` 的保留**

**⇒ 三层**：

```text
1. `ownerEntityNum = ownerEntityNum`（参数）
2. ⇒ **所以"所有者"在转换后【更新】而不是清**
3. ⇒ **因为新碰撞属于那个所有者**
```

**✅ 与 §345 的"`groundEntityNum` 的双角色"**不同**（那是一个字段两个语义，这是**一个字段的新值**）。

## 五、**`linkBrushModelCollision` 的"四件事"**

```php
entity->second.networkState.eType = EntityTypeScriptMover;
entity->second.networkState.origin = origin;
entity->second.networkState.angles = angles;
entity->second.networkState.modelIndex = 0;
entity->second.networkState.scriptMoverBrushModelIndex = (uint16)model.clipHandle;
entity->second.networkState.solid = *solid;
if (entity->second.networkState.modelScale <= 0.0f)
    entity->second.networkState.modelScale = 1.0f;
```

### 5.1 六层

```text
1. **eType = `ET_SCRIPTMOVER`**（§350 第四次确认）
2. ⇒ **`origin` / `angles` 从参数**
3. ⇒ **`modelIndex = 0`**（画笔模型没有 xmodel）
4. ⇒ **`scriptMoverBrushModelIndex = clipHandle`**
5. ⇒ **`solid = *solid`**
6. ⇒ **`modelScale <= 0 ⇒ 1.0`**（**第四次"零缩放"**）
```

**✅ 与 §350 的"字段 26 而非字段 19"**完全一致 ✓

**⇒ **第二次确认 `modelIndex = 0` 对画笔模型**。

### 5.2 而注释

```php
// ET_SCRIPTMOVER and the brush model field, matching both world-spawn
// paths -- ET_GENERAL's presentation handler never draws a brush model,
// and solid without the index fails the frame validator's pairing.
```

**⇒ 五层**：

```text
1. **`ET_SCRIPTMOVER` 与画笔模型字段，匹配【两个世界生成路径】**
2. ⇒ **`ET_GENERAL` 的表现处理器【从不】画一个画笔模型**
3. ⇒ **而【没有索引的实心】失败帧验证器的配对**
4. ⇒ **所以两者都要**
```

**✅ 与 §350 的"两个入口必须一致"**第三次一致。**

**⇒ **注意：这里是**第三个入口**（`linkBrushModelCollision`）。**

**⚠ 所以**三个入口都必须设 `ET_SCRIPTMOVER`**。**

**✅ **三次确认。**

## 六、**`setBrushModelGameplayActive` 的"零"分支**

```php
entity->second.gameplayActive = active;
entity->second.collisionLinked = collision.has_value();
entity->second.networkState.solid = active ? *solid : 0;
entity->second.networkState.scriptMoverBrushModelIndex = active
    ? (uint16)model.clipHandle : 0;
```

### 6.1 五层

```text
1. **`gameplayActive = active`**
2. ⇒ **`collisionLinked = collision.has_value()`**（**不是 `active`**）
3. ⇒ **`solid = active ? *solid : 0`**
4. ⇒ **`brushModelIndex = active ? clipHandle : 0`**
5. ⇒ **所以"不活动" ⇒ 三个都清零**
```

**⚠ 而 ② 与 `active`**不同**（`collision.has_value()`）。**

**⇒ 三层**：

```text
若 `active` 而 `contents == 0` ⇒ **不建 collision** ⇒ `collisionLinked = false`
⇒ **所以一个"活动但无内容"的画笔模型【不连碰撞】**
```

**✅ 一个**精确的三态**。**

## 七、**`purchaseMapTargetGroup` / `openMapTargetGroup` 的原子性**（本组第六重要）

### 7.1 那段

```php
// OLMOD(factory-door-motion): purchase remains one atomic group transaction.
// Measured sliding brushes stay visible and collidable at their evaluated
// pose. Existing nonmoving clip/model behavior is deliberately unchanged.
std::vector<std::pair<std::uint32_t, SvGameEntity>> previous;
for (const auto &[entityNum, entity] : entities_) {
    if (!entity.gameplayActive || entity.mapTargetName != targetName ||
        (entity.mapClassName != "script_brushmodel" && entity.mapClassName != "script_model")) continue;
    const auto motion = factoryDoorMotions_.find(entityNum);
    if (motion != end && (motion->second.started || !entityPool_->resolve(motion->second.handle))) return false;
    auto candidate = entity;
    if (motion != end) {
        const auto trajectory = SV_FactoryDoorTrajectory(motion->second.profile, snapshot_.serverTime, snapshot_.serverTime);
        const auto pose = SV_EvaluateTrajectory(trajectory, ..., zmBoardTrajectoryEvaluator_);
        if (!pose) return false;
        candidate.currentOrigin = *pose;
        auto &net = candidate.networkState;
        net.origin = trajectory.base; net.positionTrajectoryType = (uint8)trajectory.type;
        net.positionTrajectoryTime = trajectory.time; net.positionTrajectoryDuration = trajectory.duration;
        net.positionTrajectoryDelta = trajectory.delta;
    } else {
        candidate.gameplayActive = false; candidate.collisionLinked = false;
        if (candidate.collisionShape == SvCollisionShape::BrushModel) {
            candidate.networkState.solid = 0; candidate.networkState.scriptMoverBrushModelIndex = 0;
        }
    }
    previous.emplace_back(entityNum, std::move(candidate));
}
if (previous.empty()) return false;
for (auto &[number, candidate] : previous) std::swap(entities_.at(number), candidate);
rebuildCollisionView();
if (nativeEntityMirrorSynchronizer_ && !nativeEntityMirrorSynchronized_) {
    for (auto &[entityNum, state] : previous) entities_.at(entityNum) = std::move(state);
    rebuildCollisionView(); return false;
}
for (const auto &[number, old] : previous) {
    const auto motion = factoryDoorMotions_.find(number);
    if (motion != end) motion->second.started = snapshot_.serverTime;
}
```

### 7.2 十一层

```text
1. **购买保持为一个【原子组事务】**
2. ⇒ **测量的滑动画笔在它们的求值姿态上【保持可见且可碰撞】**
3. ⇒ **既有不动的 clip/模型行为【故意不变】**
4. ⇒ **遍历所有 `gameplayActive` 且 `mapTargetName == targetName` 且类是画笔或模型**
5. ⇒ **若已有 motion 且已开始 或 句柄失效 ⇒ 【整个函数返回 false】**
6. ⇒ **有两支**：
     · **有 motion ⇒ 设为轨迹的【起始姿态】**（位置 + 四个轨迹字段）
     · **无 motion ⇒ 关掉**（`gameplayActive` / `collisionLinked` / 若是画笔还清 solid 与索引）
7. ⇒ **空 ⇒ false**
8. ⇒ **`std::swap` 全部（暂存回滚）**
9. ⇒ **一次 `rebuildCollisionView`**
10. ⇒ **镜像失败 ⇒ 逐个 `= std::move(state)` 恢复**（**不是 swap**）
11. ⇒ **成功后【才】设 `started`**
```

### 7.3 ⚠ **第 10 步用 `= std::move` 而不是 `swap`**

**⇒ 三层**：

```text
`std::swap(entities_[n], candidate)`   ⇒ candidate 得到旧值
⇒ 然后 `entities_[n] = std::move(state)` ⇒ **恢复旧值** ✓
```

**✅ 因为 `state` **已经**是旧值（swap 后）。**

**⚠ 而 §364 的 `setBrushModelMotions` 用**再 swap 一次**。**

**⇒ 两种等价写法。**

**✅ 一个**小的风格差异**。

### 7.4 而**"成功后【才】设 `started`"**

**✅ 与 §349 的"投递状态在整快照成功后提交"**同族（**第三次"成功后提交"**）。

**⇒ 三层**：

```text
1. 几何变更提交
2. ⇒ **然后才设 `started`**
3. ⇒ **所以一个失败的开门不消耗 motion**
```

**✅ **一个正确的事务边界。**

## 八、**`activateFactoryPower` 的双阶段**

### 8.1 那段

```php
// OLMOD(factory_power): reserve the transient native event before changing
// geometry. ServerCore registers group500 first; no snapshot is published
// inside this transaction. Roll back the event if the mirror rejects it.
SvEntityHandle steam;
if (!spawnExploderEvent(FactorySteamEventParameter, &steam)) return false;
factoryPowerLeverModel_ = model; factoryPowerBodyModel_ = bodyModel;
factoryPowerStarted_ = snapshot_.serverTime;
if (stepFactoryPowerMotions()) { ... return true; }
// This reservation was never published and owns no collision, touch or
// damage state. Undo it directly: freeEntity's live-entity mirror rollback
// would resurrect the pending effect if the mirror is still unavailable.
if (!entityPool_->free(steam, snapshot_.serverTime))
    throw std::logic_error("unpublished Factory steam reservation lost ownership");
entities_.erase(steam.entityNum);
rebuildCollisionView();
factoryPowerStarted_.reset(); factoryPowerLeverModel_ = factoryPowerBodyModel_ = 0;
return false;
```

### 8.2 十二层

```text
1. **在改变几何之【前】预留那个瞬态原生事件**
2. ⇒ **`ServerCore` 先注册 `group500`**
3. ⇒ **在这个事务内【不发布任何快照】**
4. ⇒ **若镜像拒绝 ⇒ 回滚那个事件**
5. ⇒ **所以先 `spawnExploderEvent`**
6. ⇒ **然后设三个字段**
7. ⇒ **然后 `stepFactoryPowerMotions()`**
8. ⇒ **成功 ⇒ 返回 true**
9. ⇒ **失败 ⇒ 【直接撤销】**
10. ⇒ **因为"这个预留从未被发布、不拥有碰撞/触碰/伤害状态"**
11. ⇒ **而 `freeEntity` 的活实体镜像回滚会【复活那个未决效果】**（若镜像仍不可用）
12. ⇒ **所以直接 `entityPool_->free` + `entities_.erase`**（**绕过 `freeEntity`**）
```

### 8.3 ⭐ **"`freeEntity` 的回滚会复活它"**

**✅ 这是本文件里**最精妙的"为什么不用标准函数"**。**

**⇒ 三层**：

```text
1. `freeEntity` 有镜像回滚（§363）
2. ⇒ **而一个【从未发布】的实体若镜像不可用 ⇒ 回滚会把它【复活】**
3. ⇒ **所以一个"从未存在"的实体不能走 `freeEntity`**
```

**✅ 与 §363 的"`rollbackFree` 恢复"**形成**一个精确的反面案例**。**

**⇒ **一个函数在两个不同场景下需要两条不同的路径。**

**✅ 一个**极深的细节**。

### 8.4 而**"`ServerCore` 先注册 `group500`"**

**⇒ 三层**：

```text
1. `group500` 是服务端侧的注册
2. ⇒ **在几何变更之前**
3. ⇒ **所以事件与几何的顺序是固定的**
```

**✅ 与 §347 的"THE TIME FIRST"**同族（**第三次时序约束**）。

## 九、**`stepFactoryPowerMotions` 的八块与两态**

### 9.1 绑定阶段

```php
if (!factoryPowerBound_) {
    std::vector<SvEntityHandle> handles;
    for (const auto &p : FactoryPowerPieces) {
        const auto it = entities_.find(p.number); const auto *life = entityPool_->resolve(p.number);
        if (it == end || !life || it->second.currentOrigin != p.origin ||
            it->second.networkState.eType != EntityTypeScriptMover ||
            (p.brush ? it->second.brushModelClipHandle != p.brush
                     : it->second.scriptModelName != (p.number == 343 ? "codo_asylum_electric_switch_off" : "zombie_power_lever_handle_arm03_off"))) {
            factoryPowerFailed_ = true;
            OlMod::RuntimeLog::write(..., "ZMPOWER binding refused entity=" + ...);
            return false;
        }
        handles.push_back({p.number, life->generation});
    }
    factoryPowerHandles_ = std::move(handles);
}
```

**⇒ 七层**：

```text
1. **八块（`FactoryPowerPieces`）**
2. ⇒ **每块五项检查**：存在 / 代际 / **原点精确相等** / `ET_SCRIPTMOVER` / **（画笔的 clipHandle 或模型的字符串名）**
3. ⇒ **`p.number == 343` ⇒ `codo_asylum_electric_switch_off`**（**身体**）
4. ⇒ **其它 ⇒ `zombie_power_lever_handle_arm03_off`**（**拉杆**）
5. ⇒ **失败 ⇒ `factoryPowerFailed_ = true` 并记日志**
6. ⇒ **所以这是一个【精确的绑定】**（原点 + 名字）
7. ⇒ **成功 ⇒ 记下八个句柄**
```

**✅ 与 §351 的"实体编号的三个代际"**不同** —— 这是**按精确属性绑定**。**

**⚠ 而"原点精确相等"（浮点 `==`）⇒ **极其严格**。**

**✅ 与 §351 的"两边解析同一个字符串 ⇒ float32 逐位相同"**配合。**

**⇒ **第二次"浮点 `==` 是安全的因为同源"**。

### 9.2 而**"`343` 是身体"**

**⇒ 三层**：

```text
1. 八块里 **`343`** 是"电闸箱"（`codo_asylum_electric_switch`）
2. ⇒ **其它是拉杆**（`zombie_power_lever_handle_arm03`）
3. ⇒ **所以一块是主体、其余七块是拉杆**
```

**✅ 与 §356 的"六块板"**不同**（这是**八块电源件**）。

### 9.3 而**`clipAt` 的"退役"**

```php
if (p.clipAt >= 0 && elapsed >= (unsigned)p.clipAt) {
    // OLMOD(factory_power): retire the blocker in both server
    // collision and the client's predicted brush-solid view.
    candidate.collisionLinked = false;
    candidate.gameplayActive = false;
    n.solid = 0;
    n.scriptMoverBrushModelIndex = 0;
    n.eFlags |= 1u;
}
```

**⇒ 七层**：

```text
1. **超过 `clipAt` 时间 ⇒ 退役这个阻挡物**
2. ⇒ **在【服务端碰撞】与【客户端的预测画笔实心视图】两边**
3. ⇒ **`collisionLinked = false`**（服务端）
4. ⇒ **`gameplayActive = false`**
5. ⇒ **`solid = 0` 与 `scriptMoverBrushModelIndex = 0`**（客户端，**配对**）
6. ⇒ **`eFlags |= 1`**
7. ⇒ **所以五处同时关**
```

**✅ 与 §365 二 的"配对"**第三次。**

**⚠ 而 `eFlags |= 1` ⇒ **一个非零位**。**

**⇒ 与 §361 的 `eFlags = 2`、`eFlags = 16`**不同（**第三个位**）。

## 十、`factoryAmmoRefillCandidate` 的**四层前置**

```cpp
if (!(boxReward ? factoryInteractablesEnabled_ : factoryPerkMachinesEnabled_) || client == end)
    return std::nullopt;
auto &owner = client->second.client;
if (owner.gameplayState != Playing || !owner.playerState.health || !owner.resolvedLoadout)
    return std::nullopt;
```

**⇒ 六项**：

```text
① 按来源的开关（箱子 / 特手机）
② 客户端存在
③ Playing
④ 活着
⑤ **有 resolvedLoadout**
```

**✅ 与 §352 的"冻结装备"**配合。**

**⇒ 而"`!owner.resolvedLoadout ⇒ 返回 nullopt`"⇒ **无装备则不能补弹**。**

**✅ 一个**正确的依赖。**

## 十一、关键结论

1. **⭐⭐ "实心与画笔模型索引必须一起动，否则帧验证器拒绝整条实体"`** —— 而**一条被拒的实体带走每个客户端的整帧**。
2. **"它们配对因为零售配对它们：`+0x0AC == 0xFFFFFF` 与 `+0x09C != 0` 恰好在同样的 238 个实体上成立"`** —— **第三次确认 238**，而从 `solid` 侧的**双向论证**。
3. **`clipHandle < 0x400` 的三次检查**（§350/§352/§365）—— **第二次三处重复**。
4. **`clipHandle` 的界（1024）比 `brushModelIndex` 的界（4096）小** —— 一个较紧的碰撞句柄界。
5. **`linkEntityCollision` 的"变形"语义** —— **清七个字段 + `solid` 换成玩家实心 + `brushModelIndex = 0`** ⇒ **一个严格的因果链**。
6. **`linkBrushModelCollision` 三个入口都设 `ET_SCRIPTMOVER`**（世界生成两处 + 这里）—— **第三次确认**。
7. **"`ET_GENERAL` 的表现处理器从不画一个画笔模型"`** —— 第三次。
8. **`setBrushModelGameplayActive` 的三态**（`collisionLinked = collision.has_value()` 而非 `active`）。
9. **⭐ `openMapTargetGroup` 的"原子组事务"`** —— 两支（有 motion ⇒ 起始姿态 / 无 motion ⇒ 关掉），而**成功后【才】设 `started`**（第三次"成功后提交"）。
10. **"测量的滑动画笔在它们的求值姿态上保持可见且可碰撞"`**。
11. **⭐⭐ `activateFactoryPower` 的"绕过 `freeEntity`"`** —— 因为**一个从未发布的实体若走 `freeEntity` 的镜像回滚会【被复活】**。
12. **"`ServerCore` 先注册 `group500`，而在这个事务内不发布任何快照"`** —— 第三次时序约束。
13. **八块电源件的绑定** —— **五项检查含"原点精确相等"（浮点 `==`）**，因为**两边解析同一字符串 ⇒ float32 逐位相同**（第二次）。
14. **`343` 是身体而其余七块是拉杆**（`codo_asylum_electric_switch` vs `zombie_power_lever_handle_arm03`）。
15. **`clipAt` 的退役在五处同时关**（`collisionLinked` / `gameplayActive` / `solid` / `brushModelIndex` / `eFlags |= 1`）。
16. **`factoryAmmoRefillCandidate` 的五项前置**，含 **`resolvedLoadout` 必须存在**。

## 十二、未闭合点

- `FactoryPowerPieces` 的八块完整清单。
- `FactoryPowerDuration` / `FactorySteamEventParameter` 的值。
- `eFlags |= 1` 的位含义。
- `MaximumServerCollisionEntityNum == 2045` 的最终确认。
- `StandingPlayerTraceBounds` 的精确值。
- `sv_snapshot_mp.cpp` 18000 行之后未读取（27,016 行，进度 67%）。
