# 382 · **"一个跨地图的 clip 画笔【从不】被 `out.exe` 的逐实体 broadphase 剔除"** —— `50-72ms` 的 SLOW TRACE 尖峰、`2221` vs `130`、三个碰撞视图的完整构建

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 24400–24800 行。

## 二、**跨地图 clip 刷的完整性能事故**（本组最重要的一段）

### 2.1 那段

```php
// OLMOD(broadphase-defeating-clip 2026-08-26): a map-spanning clip brush
// (mp_nuked entity 95: half=2221,1640 ceiling playerclip at Z 255..329) is
// never culled by out.exe's per-entity broadphase, so EVERY player trace
// descends its clipmap -- measured as ~half the per-frame clientThink cost
// and the 50-72 ms SLOW TRACE spikes. Such a clip only matters when a player
// is actually inside its volume, which for a high ceiling clip never happens
// in normal play. So link it only while an active player is near its bounds;
// otherwise leave it unlinked. The margin covers the player's own extent plus
// a frame of fast vertical travel, so the clip re-links before contact.
```

### 2.2 十六层

```text
1. **一个跨地图的 clip 画笔**
2. ⇒ **（`mp_nuked` 实体 95：`half = 2221, 1640` 的天花板 playerclip 在 Z `255..329`）**
3. ⇒ **从不被 `out.exe` 的逐实体 broadphase 剔除**
4. ⇒ **所以【每一个玩家 trace】都下潜它的 clipmap**
5. ⇒ **测量为每帧 `clientThink` 成本的【约一半】**
6. ⇒ **以及 `50-72ms` 的 SLOW TRACE 尖峰**
7. ⇒ **这样一个 clip 只在【一个玩家真的在它的体内】时才重要**
8. ⇒ **而一个高天花板 clip 在正常游玩里【从不】发生**
9. ⇒ **所以只在【一个活动玩家靠近它的 bounds】时链接它**
10. ⇒ **否则让它【不链接】**
11. ⇒ **那个 margin 覆盖玩家自己的范围加上一帧的快速垂直移动**
12. ⇒ **所以 clip 在接触之前【重新链接】**
```

### 2.3 ⭐⭐ **"每一帧 clientThink 成本的一半"**

**✅ 与 §371 的"`findXAsset` 守卫把战斗服卡成 1.2 秒每帧"、§372 的"140 行/秒 × 全局锁"**同族（**第五次性能事故）。**

**⇒ 三层**：

```text
一个 clip 画笔
⇒ **每一个玩家 trace 都下潜它**
⇒ **⇒ 每帧 clientThink 成本的一半**
```

**✅ **一个极具体的性能归因**（不是"感觉慢"）。**

**⚠ 而"`50-72ms` 的 SLOW TRACE 尖峰"⇒ **一个具体的量**。**

**✅ 与 §374 的"`3000ms` 的帧"**同族（**第二次"毫秒级性能度量"）。**

### 2.4 而**"`half = 2221, 1640` vs `~130`"**

```php
// The threshold is far above any real
// prop or wall (nuketown's next-largest brush half-extent is ~130) and
// far below the map-spanning clip (~2221), so only broadphase-defeating
// clips take the conditional path; every other brush links as before.
constexpr float SvMapSpanningBrushHalfExtent = 512.0f;
```

### 2.5 八层

```text
1. **`SvMapSpanningBrushHalfExtent = 512`**
2. ⇒ **远高于任何真实的道具或墙**（nuketown 的次大画笔半宽是 **`~130`**）
3. ⇒ **而远低于跨地图 clip**（**`~2221`**）
4. ⇒ **所以只有【broadphase 击败型】的 clip 走条件路径**
5. ⇒ **其它每一个画笔【照旧链接】**
```

**✅ ⭐ **一个由两端夹出阈值**的经典手法。**

**⇒ 三层**：

```text
130  ⇒ 真实墙
512  ⇒ **阈值（在中间）**
2221 ⇒ 跨地图 clip
```

**✅ 与 §351 的"237 个间隔方程"**同族（**第三次"由数据定阈值"）。**

**⚠ 而 `512` 是**2 的幂**（可能只是"一个大数"）。**

**✅ 一个**合理的选择**。

### 2.6 而 **`mapSpanningClipNeedsLink` 的实现**

```cpp
const auto mapSpanningClipNeedsLink = [&activePlayerOrigins](
    const std::array<float, 3> &origin, const TraceBounds &bounds) {
    constexpr float margin = 128.0f;
    for (const auto &player : activePlayerOrigins) {
        bool overlaps = true;
        for (std::size_t axis = 0; axis < 3; ++axis) {
            const float center = origin[axis] + bounds.midpoint[axis];
            const float reach = bounds.halfSize[axis] + margin;
            if (player[axis] < center - reach || player[axis] > center + reach) {
                overlaps = false; break;
            }
        }
        if (overlaps) return true;
    }
    return false;
};
```

**⇒ 六层**：

```text
1. **`margin = 128`**
2. ⇒ **对每一个活动玩家**
3. ⇒ **三轴 AABB 测试**（`center ± (halfSize + margin)`）
4. ⇒ **任一玩家重叠 ⇒ `true`**
5. ⇒ **否则 `false`**
6. ⇒ **所以是一个纯几何的"是否需要"判据**
```

**✅ 与 §354 的 `RepairRadius = 112`**不同（**128 是 margin**）。

**⚠ 而 `margin = 128` ⇒ **大于玩家的半宽（15）与一帧的垂直移动（79×0.05 = 4）**。**

**✅ 所以**充裕**。**

## 三、**三个碰撞视图的完整构建**（本组第二重要）

### 3.1 三个视图

```text
collisionEntities_                通用碰撞（伤害/胶囊）
playerMovementCollisionEntities_  只给 Pmove
bulletCollisionEntities_          子弹（含 actor 的骨骼姿态）
```

### 3.2 而**三个的构建顺序**

```cpp
// 1. 玩家（三个都加）
for (clientStates_) { collisionEntities_.push_back(*ce); bulletCollisionEntities_.push_back(move(*ce)); }
// 2. 世界实体（按 shape 分三个分支）
for (entities_) { ... bulletCollisionEntities_.push_back(*ce); ... }
// 3. 最后 playerMovement = collision + 全部
playerMovementCollisionEntities_.insert(end, collisionEntities_.begin(), collisionEntities_.end());
// 4. 三个都排序
sort(playerMovementCollisionEntities_, {}, &SvCollisionEntity::entityNum);
sort(collisionEntities_, {}, &...);
sort(bulletCollisionEntities_, {}, &...);
```

### 3.3 七层

```text
1. **玩家 ⇒ 进 `collision` 与 `bullet`**
2. ⇒ **世界实体 ⇒ 按 shape 三分支，然后进 `bullet`**
3. ⇒ **而 actor 类【不】进 `collision`**（`if (!isActorEType(...)) collisionEntities_.push_back(...)`）
4. ⇒ **`playerMovement` = `collision` + 全部**
5. ⇒ **三个都 `sort`**
6. ⇒ **所以 `playerMovement ⊇ collision`**
7. ⇒ **而 `bullet` 是独立的**
```

**✅ 一个**精确的三视图关系**。**

**⚠ 而"actor 类不进 `collision`"⇒ **所以 `collisionEntities_` 只含玩家与画笔模型**。**

**⇒ 三层**：

```text
collisionEntities_     玩家 + 画笔模型（**无 actor**）
bulletCollisionEntities_  玩家 + 画笔模型 + actor（**有骨骼姿态**）
playerMovement         collision + 全部（**含 actor 的 packed solid**）
```

**✅ 与 §349 的"`reset()` 清三个碰撞集"**第四次确认。**

### 3.4 而**三个 `sort`**

**✅ 与 §355 的"`actorNumbers` 排序"、§376 的"`sort(numbers)`"**第九次确定性要求。

**⚠ 而 `collisionEntity(entityNum)` 用 `lower_bound` ⇒ **所以排序是必需的**。**

**✅ 与 §379 的"`stagedMissiles` 的 `lower_bound`"**同族（**第二次"排序支持二分"）。**

## 四、**actor 的 packed solid 与骨骼姿态**（本组第三重要）

### 4.1 packed solid

```php
// CODREF(sv_trace): out.exe 0x46DAE0 clips packed type19
// capsules with contents1; 0x46D6E0 supplies their inset bounds.
// 0x413E60's start-solid retry removes 02004000, not bit1.
// OLMOD(zm-player-collision): build this Pmove-only projection
// once per collision rebuild. Do not alter the bullet mirror or
// actor navigation (shared spawn positions may overlap).
if (entity.networkState.eType == EntityTypeActor && entity.mapClassName == "zombie_actor") {
    const auto bounds = SV_DecodePackedSolidBounds(entity.networkState.actorField00AC);
    if (bounds) {
        const auto body = SV_LinkActorCollisionEntity(entityNum, entity.ownerEntityNum,
            entity.currentOrigin, entity.currentAngles, *bounds, 1u);
        if (body) playerMovementCollisionEntities_.push_back(*body);
    }
}
```

**⇒ 十一层**：

```text
1. **`out.exe 0x46DAE0` 用 contents `1` 裁剪打包的 type19 胶囊**
2. ⇒ **`0x46D6E0` 提供它们的【内缩 bounds】**
3. ⇒ **`0x413E60` 的 start-solid 重试移除 `0x02004000`，不是 bit1**
4. ⇒ **每次碰撞重建时构建【一次】这个 Pmove-only 投影**
5. ⇒ **不要改变子弹镜像或 actor 导航**
6. ⇒ **（共享的生成点可能重叠）**
7. ⇒ **`SV_DecodePackedSolidBounds(actorField00AC)`** ⇒ **从 packed 索引解 bounds**
8. ⇒ **`SV_LinkActorCollisionEntity(..., 1u)`** ⇒ **contents `1`**
9. ⇒ **进 `playerMovementCollisionEntities_`**
```

**✅ ⭐ **`actorField00AC` 是**打包的 solid bounds**（`0x6801FF` 那个值，§361）。**

**⇒ **第三次确认 `actorField00AC`。**

**⚠ 而"`0x02004000`"⇒ **一个具体的位掩码**。**

**✅ 与 §371 的"`ps+0x10` 测试 `0x1800`"**不同（不同字段）。**

### 4.2 而**骨骼姿态（`actorHitPose`）**

```php
if ((zmDeathFx_.neck || zmDeathFx_.torso) && entityPool_ &&
    entity.mapClassName == "zombie_actor" &&
    entity.networkState.eType == EntityTypeActor)
{
    const auto *life = entityPool_->resolve(entityNum);
    if (life && life->inUse) {
        collisionEntity->actorHitPose = SvActorHitPose{
            .generation = life->generation,
            .body = entity.networkState.actorModelIndex,
            .head = entity.networkState.actorAttachModelIndex0,
            .animation = entity.networkState.actorAnimIndex ? entity.networkState.actorAnimIndex : SvActorAnimIndex,
            .animationStartTime = entity.networkState.actorAnimStartTime,
            .lower = zmDeathFxStates_.contains(entityNum) ? zmDeathFxStates_.at(entityNum).attachment1 : uint16_t{},
        };
    }
}
```

**⇒ 八层**：

```text
1. **三个前置**：有 neck/torso 效果 / 池存在 / 是 `zombie_actor` / eType 是 actor
2. ⇒ **池的 `inUse`**
3. ⇒ **七个字段的 `SvActorHitPose`**：
     · `generation`
     · `body`
     · `head`
     · `animation`（**有默认回退**）
     · `animationStartTime`
     · `lower`（**只在 `zmDeathFxStates_` 有时**）
4. ⇒ **所以子弹命中可以用【骨骼级】的姿态**
```

**✅ 与 §353 的"`applyZmHeadLoss` 的 `attachment0`"**配合。**

**⚠ 而"`animation` 的默认回退到 `SvActorAnimIndex`"⇒ **与 §379 的 `.animIndex` 的回退相同**。**

**✅ **第二次确认那个回退。**

## 五、**`nativeEntityMirrorSynchronized_` 的单一赋值点**

```cpp
nativeEntityMirrorSynchronized_ = nativeEntityMirrorSynchronizer_ &&
    nativeEntityMirrorSynchronizer_(phase, bulletCollisionEntities_, nativeEntityStates, snapshot_.serverTime);
```

**⇒ 三层**：

```text
1. **`nativeEntityMirrorSynchronized_` 在【这里】被赋值**
2. ⇒ **而它是 `synchronizer != null && synchronizer(...)` 的结果**
3. ⇒ **所以"没有同步器" ⇒ `false`**
```

**⚠ 而"没有同步器 ⇒ `false`"⇒ **所以每个调用方都会认为"未同步"。**

**⚠ 但 §364/§365 的检查是 `nativeEntityMirrorSynchronizer_ && !nativeEntityMirrorSynchronized_`。**

**⇒ 所以**两层检查**（先看有没有同步器）。**

**✅ **完整闭合。**

### 5.1 而 **`refreshClientCollisionView` 的 `IncrementalCollision` 阶段**

```cpp
nativeEntityMirrorSynchronized_ = nativeEntityMirrorSynchronizer_(
    SvNativeEntityMirrorPhase::IncrementalCollision,
    std::span<const SvCollisionEntity>{&*collisionEntity, 1},
    std::span<const SvNativeEntityStateSource>{&nativeEntityState, 1},
    snapshot_.serverTime);
```

**⇒ 四层**：

```text
1. **一个【增量】阶段**（只一个实体）
2. ⇒ **而 `rebuildCollisionView` 是【全量】**
3. ⇒ **所以两个阶段**
4. ⇒ **而 `IncrementalCollision` 只更新一个**
```

**✅ 与 §349 的"`SvNativeEntityMirrorPhase::Collision` 与 `Presentation`"**配合（**第三个阶段）。**

**⇒ **四次确认至少三个阶段**：**

```text
Collision             全量碰撞
IncrementalCollision  单实体增量
Presentation          表现
```

**✅ 一个**清晰的分层**。

### 5.2 而 `replaceSorted` 的 `lower_bound` + `insert`

```cpp
const auto replaceSorted = [clientNum, &collisionEntity](auto &collisionView) {
    const auto found = std::ranges::lower_bound(collisionView, clientNum, {}, &SvCollisionEntity::entityNum);
    if (found != collisionView.end() && found->entityNum == clientNum) *found = *collisionEntity;
    else collisionView.insert(found, *collisionEntity);
};
replaceSorted(collisionEntities_);
replaceSorted(bulletCollisionEntities_);
```

**⇒ 五层**：

```text
1. **`lower_bound` 找到位置**
2. ⇒ **有同号 ⇒ 覆盖**
3. ⇒ **否则【插入到那个位置】**（保持排序）
4. ⇒ **所以插入是 O(n) 但保持有序**
5. ⇒ **两个视图都更新**
```

**✅ 与 §381 的"`registerLootItem` 的 `find` + 覆盖"**不同**（那里是**线性查找 + push_back**）。**

**⚠ 而 `lower_bound + insert` 更好（**保持有序**）。**

**✅ 一个**更精确的实现**。

## 六、**`dispatchEntityTouchHandlers` 的两级**

```cpp
if (callback.receiverEntityNum < MaximumGameClients) {
    if (!clientStates_.contains(callback.receiverEntityNum)) continue;
    const auto found = playerTouchHandlers_.find(callback.receiverEntityNum);
    if (found != playerTouchHandlers_.end()) handler = found->second;
} else {
    const auto found = entityTouchHandlers_.find(callback.receiverEntityNum);
    if (found == entityTouchHandlers_.end() || !entityPool_ ||
        !entityPool_->resolve(SvEntityHandle{ .entityNum = ..., .generation = found->second.generation }))
        continue;
    handler = found->second.handler;
}
if (handler) handler(callback);
```

**⇒ 七层**：

```text
1. **`< MaximumGameClients` ⇒ 玩家处理器**
2. ⇒ **先确认 `clientStates_` 有这个客户端**
3. ⇒ **而动态实体 ⇒ 必须 `resolve`（代际检查）**
4. ⇒ **所以两个不同的前置**
5. ⇒ **而 `handler` 可能为空 ⇒ 不调**
```

**✅ 与 §363 的"代际拥有"**完全一致 ✓

**⇒ **第三次确认 `resolve` 的代际检查。**

## 七、`appendSdEvent` 的**类型范围检查**

```cpp
if (type < SvWorldEventType::SdBombPickedUp || type > SvWorldEventType::SdRoundEnded) return;
++eventSequence_;
if (!eventSequence_) ++eventSequence_;
```

**⇒ 四层**：

```text
1. **类型必须在 `[SdBombPickedUp, SdRoundEnded]` 范围**
2. ⇒ **否则静默丢弃**
3. ⇒ **`++eventSequence_`**
4. ⇒ **若回到 `0` 则再 `++`（**永不为零**）**
```

**✅ 与 §346 的"`0` 是一个哨兵"**同族（**第三次"零是保留的"）。**

## 八、关键结论

1. **⭐⭐ "一个跨地图的 clip 画笔【从不】被 `out.exe` 的逐实体 broadphase 剔除"`** —— `mp_nuked` 实体 95（`half = 2221, 1640` 的天花板 playerclip 在 Z `255..329`）。
2. **"所以【每一个玩家 trace】都下潜它的 clipmap ⇒ 每帧 `clientThink` 成本的约一半`** 与 **`50-72ms` 的 SLOW TRACE 尖峰"`** —— 第五次性能事故，而**归因极具体**。
3. **"这样一个 clip 只在一个玩家真的在它体内时才重要，而一个高天花板 clip 在正常游玩里从不发生"`**。
4. **⭐ "margin 覆盖玩家自己的范围加上一帧的快速垂直移动，所以 clip 在接触之前重新链接"`** —— 一个**前瞻性的重链接**。
5. **⭐ 阈值 `512` 由两端夹出**：真实墙 `~130` / 跨地图 clip `~2221` —— 第三次"由数据定阈值"。
6. **三个碰撞视图的精确关系**：`collisionEntities_`（玩家 + 画笔，**无 actor**）/ `bulletCollisionEntities_`（**含 actor 的骨骼姿态**）/ `playerMovementCollisionEntities_`（`collision` + 全部，**含 actor 的 packed solid**）。
7. **`if (!isActorEType(...)) collisionEntities_.push_back(...)`** —— **actor 不进通用碰撞视图**。
8. **三个 `sort` 支持 `lower_bound`** —— 第九次确定性要求、第二次"排序支持二分"。
9. **⭐ `actorField00AC` 是【打包的 solid bounds】**（`SV_DecodePackedSolidBounds`）—— 第三次确认那个字段，而 `0x6801FF` 那个值现在有含义。
10. **`out.exe 0x46DAE0` 用 contents `1` 裁剪打包的 type19 胶囊，`0x46D6E0` 提供内缩 bounds**。
11. **"`0x413E60` 的 start-solid 重试移除 `0x02004000`，不是 bit1"`** —— 一个精确的位掩码。
12. **`actorHitPose` 的七个字段**（含 `lower` 只在 `zmDeathFxStates_` 有时）—— 而 `animation` 的默认回退与 §379 **一致**。
13. **⭐ `nativeEntityMirrorSynchronized_` 的单一赋值点** = `synchronizer && synchronizer(...)` ⇒ **"没有同步器"也得到 `false`**，与 §364/§365 的 `synchronizer && !synchronized_` **完整闭合**。
14. **三个镜像阶段确认**：`Collision`（全量）/ **`IncrementalCollision`（单实体）** / `Presentation`。
15. **`replaceSorted` 的 `lower_bound` + `insert`** 比 §381 的"线性查找 + push_back"**更精确**（保持有序）。
16. **`dispatchEntityTouchHandlers` 的两级**（玩家 vs 动态实体），而**动态实体必须 `resolve`**（代际检查）—— 第三次确认。
17. **`appendSdEvent` 的类型范围检查 + "`eventSequence_` 永不为零"`** —— 第三次"零是保留的"。

## 九、未闭合点

- `SvNativeEntityMirrorPhase` 的完整枚举（至少三个）。
- `SV_DecodePackedSolidBounds` 对 `0x6801FF` 的解码。
- `0x02004000` 的两个位含义。
- `mp_nuked` 实体 95 的完整 bounds。
- `SvActorHitPose` 的消费方（子弹命中判定）。
- `sv_snapshot_mp.cpp` 24800 行之后未读取（27,016 行，进度 92%）。
