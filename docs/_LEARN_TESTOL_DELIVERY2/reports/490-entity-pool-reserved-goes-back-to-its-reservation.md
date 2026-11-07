# 490 · **"一个被保留的号【回到【它的保留**，而不是【回到【那个 FIFO —— 回收它【会【把【一个静态实体的基线【交给【下一个【生成的东西**"** —— `sv_entity_mp.cpp` 的高水位线、`rollbackFree` 的 O(1) 恢复、以及"三代"的证明

## 一、范围

本报告学习 `sv_entity_mp.cpp`（**`269` 行**）全文件：`reset` / `reserve` / `spawnAt` / `spawn` / `free` / `rollbackFree` / `markFreeAfterEvent` / `expiredEventEntities` / 两个 `resolve`，以及它们共享的**高水位线 + 保留位**这套双索引。

## 二、**"一个被保留的号回到它的保留，而不是回到那个 FIFO"**（本组最重要的一段）

### 2.1 那段

```cpp
// A reserved number goes back to its reservation, not to the FIFO --
// recycling it would hand a static entity's baseline to whatever spawns
// next.
if (!reserved_[handle.entityNum])
    freeEntities_.push_back(handle.entityNum);
return true;
```

### 2.2 二十四层

```text
1. **一个被保留的号【回到【它的保留**】
2. ⇒ **⇒ 而不是【回到【那个 **FIFO**】
3. ⇒ **⇒ 因为【回收它【会【把【一个【静态实体的基线**】交给【那个【下一个【生成的东西**】
4. ⇒ **⇒ 所以【那个 `if (!reserved_)` 【是【一个**单向**的分叉**】
```

### 2.3 ⭐⭐⭐ **"回收它会把一个静态实体的基线交给下一个生成的东西"**

**✅ 这是本报告里**最重要的一条"**两个分配策略【必须【分开**"**。**

**✅ 与 §489 的"`reserve` 是必须的前置"**——**完全闭合** ✓

**⇒ 三层**：
```text
顺序分配 ⇒ **`highWaterEntityNum_++`**（**一个**单向的**指针**）
FIFO 回收 ⇒ **`freeEntities_`**（**一个**双端**的队列**）
⇒ **⇒ 所以【两个**独立的**结构**】⇒ **⇒ 而【`reserved_` 【是【那个**唯一的**开关**】
```

**✅ ⭐⭐⭐ **"两个独立的结构，而 reserved_ 是那个唯一的开关"**。

**⚠ 而 `free()` 的**三个界**】**。**

**⇒ 十六层**：
```cpp
if (!configured_ || handle.entityNum < firstDynamicEntityNum_ ||
    handle.entityNum >= EntityNumWorld ||
    (handle.entityNum >= highWaterEntityNum_ && !reserved_[handle.entityNum]))
{
    return false;
}
```
```text
1. **`< firstDynamicEntityNum_` ⇒ 拒绝**】（**低于动态区**）
2. ⇒ **`>= EntityNumWorld` ⇒ 拒绝**】（**越界**）
3. ⇒ **⇒ ⚠ 而【`>= highWaterEntityNum_ && !reserved_` ⇒ 拒绝**】
4. ⇒ **⇒ 所以【一个【被保留的**号【在【高水位线之上【是【可以被释放**的**
```

**✅ ⭐⭐⭐ **"一个被保留的号在高水位线之上是可以被释放的"** —— 而**注释【明说**了那个理由**。**

**⇒ 十层**：
```cpp
// A reserved slot sits ABOVE the high-water mark by construction -- it
// was withheld from sequential allocation -- so the ordinary bound
// would refuse to free any static entity the map published through
// spawnAt.
```
```text
1. **一个被保留的槽【在【高水位线之上【是【按构造**的**】
2. ⇒ **⇒ 因为【它【被【从【顺序分配【扣留**】
3. ⇒ **⇒ 所以【那个【通常的**界【会【拒绝【释放【任何【通过 `spawnAt` 发布的静态实体**】
```

**✅ ⭐⭐⭐ **"通常的界会拒绝释放任何通过 spawnAt 发布的静态实体"** —— 一个**极精确的理由**。

**✅ 与 §489 的"那个 `reserve` 是一个必须的前置"**——**完全闭合**。

## 三、**`rollbackFree` 的 O(1) 与"只在另一个池变更之前有效"**（本组第二重要）

### 3.1 那段

```cpp
// OLMOD(entity-free-source-rollback): free() appends exactly one FIFO
// entry. A rollback is valid only before another pool mutation and
// restores the complete generation-owned lifetime in O(1).
if (!configured_ || handle.entityNum < firstDynamicEntityNum_ ||
    handle.entityNum >= highWaterEntityNum_ ||
    previousLifetime.entityNum != handle.entityNum ||
    previousLifetime.generation != handle.generation ||
    !previousLifetime.inUse || freeEntities_.empty() ||
    freeEntities_.back() != handle.entityNum)
{
    return false;
}
const auto &freed = entities_[handle.entityNum];
if (freed.inUse || freed.generation != handle.generation + 1)
    return false;
freeEntities_.pop_back();
entities_[handle.entityNum] = previousLifetime;
return true;
```

### 3.2 二十四层

```text
1. **`free()` 【恰好【追加【一个** FIFO 条目**】⇒ **⇒ 所以【那个 `back()` 【是【那个**刚追加的**】
2. ⇒ **⇒ 而那个 `rollbackFree` 【检查 `freeEntities_.back() != handle.entityNum`**】
3. ⇒ **⇒ 所以【它【只能【撤销【那个【最近的**释放**】
4. ⇒ **⇒ 而 `freed.generation != handle.generation + 1` ⇒ 拒绝**】（**⇒ 那个 `free()` 【递增**了**）
5. ⇒ **⇒ 然后 `pop_back()` + `entities_[n] = previousLifetime`**】
```

### 3.3 ⭐⭐⭐ **"一个回滚只在另一个池变更之前有效"**

**✅ 与 §489 的"`rollbackFree` 是那个 `entity free rollback lost FIFO ownership` 的一个正确的替代"**——**完全闭合** ✓

**⇒ 三层**：
```text
§424  **`entity free rollback lost FIFO ownership`**（**那个错误【是【一个【丢了 FIFO 所有权的**回滚**）
§490  **`freeEntities_.back() != handle.entityNum` ⇒ 拒绝**（**⇒ 只撤销【那个**最近的有效
⇒ **⇒ 所以【那个检查【正是【那个错误的**一个修复**
```

**✅ ⭐⭐⭐ **"那个检查正是那个错误的一个修复"** —— 一个**跨报告的完整闭合**。

**⚠ 而那个 `freed.generation == handle.generation + 1` 的**检查**】**。**

**⇒ 十层**：
```text
`free()` ⇒ **`nextGeneration = entity.generation + 1`**】
`rollbackFree` ⇒ **检查 `freed.generation == handle.generation + 1`**】
⇒ **⇒ 所以【那个**代数【证明【那个 `free()` 【是【那个**最近的**
```

**✅ ⭐⭐⭐ **"那个代数证明那个 free() 是那个最近的"** —— 一个**极精巧的证明**。

**✅ 与 §469 的"代次三元失效"**——**同族**（**第三次"一个**代次【是【一个**证明**"**）。

## 四、**`spawn` 的"跨过被保留的号"**（本组第三重要）

### 4.1 那段

```cpp
if (!entityNum)
{
    // Step over reserved numbers. They belong to the map's static
    // entities and the client resolves them against a baseline that is
    // specific to each one, so sequential allocation must not hand one
    // to a dynamic entity even while it sits unspawned.
    while (highWaterEntityNum_ < EntityNumWorld &&
           reserved_[highWaterEntityNum_])
    {
        ++highWaterEntityNum_;
    }
    if (highWaterEntityNum_ >= EntityNumWorld)
        return std::nullopt;
    entityNum = highWaterEntityNum_++;
}
```

### 4.2 二十四层

```text
1. **跨过【被保留的号**】
2. ⇒ **⇒ 它们【属于【那个地图的静态实体**】
3. ⇒ **⇒ 而【客户端【用一个【对它们【每一个【都**特定**的基线【解析它们**】
4. ⇒ **⇒ 所以【顺序分配【不能【把一个【交给【一个动态实体**】
5. ⇒ **⇒ 即使【它【仍然【未生成**】
```

### 4.3 ⭐⭐⭐ **"即使它仍然未生成"**

**✅ 与 §489 的"无论是否有一个静态实体被发布在它上面"**——**完全闭合** ✓

**⇒ 三层**：
```text
若【只跳过【已生成的**】⇒ **⇒ 一个【未生成的**静态号【会【被【交给【一个动态实体**
而【那个客户端【仍然【用【那个基线**】⇒ **⇒ 一个**继承**【仍然是**错的**
⇒ **⇒ 所以【必须【跳过【那个**保留位【本身**
```

**✅ ⭐⭐⭐ **"必须跳过那个保留位本身"** —— 一个**极清晰的机制**。

**⚠ 而 `spawn` 的**FIFO 优先**】**。**

**⇒ 十六层**：
```cpp
if (!freeEntities_.empty())
{
    const auto candidate = freeEntities_.front();
    const auto &entity = entities_[candidate];
    if (serverTime - entity.eventTime >= EntityReuseDelayMilliseconds ||
        highWaterEntityNum_ >= EntityNumWorld)
    {
        entityNum = candidate;
        freeEntities_.pop_front();
    }
}
```
```text
1. **FIFO 优先**】
2. ⇒ **⇒ 而【那个 `front()` 【必须【等了 `500ms`**】（`EntityReuseDelayMilliseconds`）
3. ⇒ **⇒ **或** 那个高水位线【已满**】
4. ⇒ **⇒ 所以【那个 `||` 【是【一个**逃逸**（**当【号空间【用完时【强制【重用**）
```

**✅ ⭐⭐⭐ **"那个 || 是一个逃逸：当号空间用完时强制重用"**。

**✅ 与 §469 的"`highWaterEntityNum_ >= EntityNumWorld`"**——**不同**，但与 §489 的"`EntityReuseDelayMilliseconds = 500`"**同族**。

**⚠ 而那个 `500ms` 的**语义**】**。**

**⇒ 十层**：
```text
`serverTime - entity.eventTime >= 500` ⇒ **可重用**
⇒ **⇒ 所以【那个 `eventTime` 【在【`free()` 里【被【设为 `serverTime`**】
⇒ **⇒ 而【那【是【一个**冷却**（cooldown）
```

**✅ ⭐⭐⭐ **"那是一个 500ms 的冷却"** —— 而**注释【与 Ghosts 的 `G_Spawn` 对照**（"`2046`-slot, `500 ms` FIFO reuse rule"）**。**

**✅ 与 §486 的"`FactoryTeleportCooldown = 5000`"**——**同族**（**第八次"一个**冷却**"**）。

## 五、**`resolve` 的"按号查找也必须越过那个界"**（本组第四重要）

### 5.1 那段

```cpp
// The high-water mark bounds SEQUENTIAL allocation, and a reserved slot
// is by construction outside it -- withholding the number from spawn()
// is the whole point. Bounding lookup by it too would make every static
// entity published through spawnAt unresolvable, and therefore invisible
// to entity(), free() and the collision view.
if (!configured_ || entityNum >= EntityNumWorld ||
    (entityNum >= highWaterEntityNum_ && !reserved_[entityNum]))
{
    return nullptr;
}
```

### 5.2 二十四层

```text
1. **那个高水位线【界定【顺序分配**】
2. ⇒ **⇒ 而【一个被保留的槽【按构造【在【它**之外**】
3. ⇒ **⇒ 因为【把那个号【从 `spawn()` 扣留【正是【整个**要点**】
4. ⇒ **⇒ 所以【按它【界定【查找**也会【让【每一个【通过 `spawnAt` 发布的静态实体【不可解析**】
5. ⇒ **⇒ 而【那【意味着【对 `entity()` / `free()` / **那个碰撞视图**不可见**】
```

### 5.3 ⭐⭐⭐ **"对 entity()、free() 和那个碰撞视图不可见"**

**✅ 与 §489 的"那是一个合法的写入，但语义上错"**——**同族**（**第三次"一个**语义的**边界**"**）。

**⇒ 三层**：
```text
若【用【高水位线【界定【查找**】⇒ **⇒ 静态实体【不可见**】⇒ **⇒ 三个**消费者【全部**失效**
修正 ⇒ **`|| (>= highWater && !reserved_)`** ⇒ **⇒ 只**界【那些【真正**越界的**
⇒ **⇒ 所以【那个条件【是【一个**精确的**修正
```

**✅ ⭐⭐⭐ **"那个条件是一个精确的修正"**。

**✅ 而"注释里 `entityNum >= EntityNumWorld` 与 `spawnAt` 的 `entityNum >= EntityNumWorld`"**⇒ **一个**一致的**上界**。**

**⚠ 而 `resolve(handle)` 的**代次**】**。**

```cpp
const auto *const entity = resolve(handle.entityNum);
return entity && entity->generation == handle.generation ? entity : nullptr;
```

**⇒ 十层**：
```text
`resolve(entityNum)` ⇒ **只【看【是否【在用**】
`resolve(handle)` ⇒ **再加【一个【代次**匹配**
⇒ **⇒ 所以【两个【重载【是【一个**分层**的**】
```

**✅ ⭐⭐⭐ **"两个重载是一个分层的"**。

**✅ 与 §474 的"`resolve(handle.generation)`"**——**同族**（**第二次"一个**代次【的**两级**"**）。

## 六、**`expiredEventEntities` 的只读收集**（本组第五重要）

### 6.1 那段

```cpp
// OLMOD(temp-event-lifetime): read-only collection; actual free and
// native mirror removal remain one outer transaction.
std::vector<SvEntityHandle> expired;
if (!configured_) return expired;
for (auto entityNum = firstDynamicEntityNum_; entityNum < highWaterEntityNum_; ++entityNum)
{
    const auto &entity = entities_[entityNum];
    if (entity.inUse && entity.freeAfterEvent &&
        serverTime - entity.eventTime > EntityEventLifetimeMilliseconds)
    {
        expired.push_back({.entityNum = entityNum, .generation = entity.generation});
    }
}
```

### 6.2 二十四层

```text
1. **一个**只读**的收集**】
2. ⇒ **⇒ 而【那个实际的 `free()` 与【原生的镜像移除【仍然【是【一个**外层的**事务**
3. ⇒ **⇒ 所以【这个函数【不【改【任何状态**】
4. ⇒ **⇒ 而【它【只【遍历【`firstDynamicEntityNum_ .. highWaterEntityNum_`**】
```

### 6.3 ⭐⭐⭐ **"那个实际的 free 与原生镜像移除仍然是一个外层的事务"**

**✅ 与 §469 的"只读是安全的取证方式"**、§485 的"三个投影全部无副作用"**——**完全同族** ✓

**⇒ 三层**：
```text
§485  **`SV_PlayerSnapshotView` 的 `auto view = *state`**
§490  **`expiredEventEntities` 的 `const` 方法 + 一个 `vector`**
⇒ **⇒ 两次"一个**只读【的**收集**"**
```

**✅ ⭐⭐⭐ **"一个只读的收集"两例**。

**⚠ 而那个 `>` 而不是 `>=`**】**。**

**⇒ 十层**：
```text
`> EntityEventLifetimeMilliseconds` ⇒ **严格大于**
⇒ **⇒ 所以【恰好 `300ms` ⇒ 【不**过期**
⇒ **⇒ 而【那【是【一个**有意的**边界**】（**与 §489 的 `<` 同族**）
```

**✅ ⭐⭐⭐ **"恰好 300ms 不过期，那是一个有意的边界"**。

**⚠ 而那个 `firstDynamicEntityNum_ .. highWaterEntityNum_` 的**范围**】**。**

**⇒ 三层**：
```text
它【不【覆盖【被保留的号**】⇒ **⇒ 因为【一个【被保留的**槽【可能【在【高水位线之上**
⇒ **⇒ 所以【一个【通过 `spawnAt` 发布的**事件实体【不【被【这个函数【收集**
```

**⚠ 一个**可报告的缺口**：`expiredEventEntities` 只遍历 `[firstDynamicEntityNum_, highWaterEntityNum_)`，而被保留的槽在 `highWaterEntityNum_` 之上 ⇒ **一个通过 `spawnAt` 发布的事件实体（且带 `markFreeAfterEvent`）永远不会被 `expiredEventEntities` 收集**。**标注为一个候选缺陷**（与 `resolve`/`free` 都显式处理了保留槽形成对照）。

## 七、`reset` 的"生产调用者提供 CODOL 确认的第一个动态槽 27"

### 7.1 那段

```cpp
// OLMOD(generation-safe-entity-pool): map/world transaction reset. The
// production caller supplies CODOL's confirmed first dynamic slot 27.
if (firstDynamicEntityNum >= EntityNumWorld) return false;
entities_ = {};
for (std::uint32_t entityNum = 0; entityNum < EntityNumWorld; ++entityNum)
{
    entities_[entityNum].entityNum = entityNum;
    entities_[entityNum].otherEntityNum = EntityNumNone;
}
```

### 7.2 二十四层

```text
1. **那个生产调用者【提供【CODOL 确认的【第一个动态槽 `27`**】
2. ⇒ **⚠ 而 §489 说【本 build 是 `37`**】
3. ⇒ **⇒ 所以【那个注释【的 `27` 【是 3.3.3.3 的**】（**⇒ 一个**过时的**注释**）
```

### 7.3 ⭐⭐⭐ **"那个注释的 27 是 3.3.3.3 的"**

**✅ 与 §489 的"CODDIFF(1649370): THIRTY-SEVEN, not 27"**——**一个精确的对照** ✓

**⇒ 三层**：
```text
§489  **`.hpp` 里【`FirstDynamicServerEntityNum = 37` 且【注释【解释**了那个 `27 → 37` 的修正**
§490  **`.cpp` 的 `reset` 注释【仍然【说 `27`**】
⇒ **⇒ 所以【那个注释【没有【被【一起**更新**
```

**✅ ⭐⭐⭐ **"那个注释没有被一起更新"** —— 一个**可报告的小不一致**（**与 §465/§482 的"注释与代码不同步"同族**）。

**⚠ 而"`highWaterEntityNum_ = firstDynamicEntityNum`"**⇒ **一个**正确的**重置**。**

**⇒ 十层**：
```text
`reset(37)` ⇒ **`highWaterEntityNum_ = 37`**】⇒ **⇒ 所以【第一个 `spawn()` 【会【拿到 `37`**】
⇒ **⇒ 而【那【与 §489 的"零售流量【最低**是 `37`"**】一致** ✓
```

**✅ ⭐⭐⭐ **"第一个 spawn 会拿到 37"** —— 与 §489 的零售流量测量**完全闭合**。

## 八、关键结论

1. **⭐⭐⭐ "一个被保留的号回到它的保留，而不是回到那个 FIFO —— **回收它会把一个静态实体的基线交给下一个生成的东西**"`** ⇒ **"两个独立的结构（高水位线 + FIFO），而 `reserved_` 是那个唯一的开关"** —— 与 §489 的 `reserve` **完整闭合**。
2. **⭐⭐⭐ `free()` 的三个界**：`< firstDynamicEntityNum_` / `>= EntityNumWorld` / **`>= highWaterEntityNum_ && !reserved_`** ⇒ 第三个是**那个关键修正** —— **"一个被保留的槽在高水位线之上是按构造的（因为它被从顺序分配扣留），所以通常的界会拒绝释放任何通过 `spawnAt` 发布的静态实体"**。
3. **⭐⭐⭐ `rollbackFree` 的 O(1)**：**"`free()` 恰好追加一个 FIFO 条目。一个回滚只在另一个池变更之前有效，并在 O(1) 里恢复那个完整的代次拥有的生命期"** ⇒ 三个证明（`freeEntities_.back() == handle.entityNum` / `freed.generation == handle.generation + 1` / `!freed.inUse`）⇒ **"那个代数证明那个 free() 是那个最近的"** —— 与 §424 的 `entity free rollback lost FIFO ownership` **完整闭合**（**"那个检查正是那个错误的一个修复"**）。
4. **⭐⭐⭐ `spawn` 的"跨过被保留的号"**：**"它们属于那个地图的静态实体，而客户端用一个对它们每一个都特定的基线解析它们，所以顺序分配不能把一个交给一个动态实体 —— **即使它仍然未生成**"`** ⇒ **"必须跳过那个保留位本身"**（与 §489 的"无论是否有一个静态实体被发布在它上面"**闭合**）。
5. **⭐⭐⭐ `spawn` 的 FIFO 优先 + 那个 `||` 逃逸**：`front()` 必须等 `500ms`（`EntityReuseDelayMilliseconds`）**或** 高水位线已满 ⇒ **"那个 || 是一个逃逸：当号空间用完时强制重用"**；而那个 `500ms` 是一个**冷却**（注释与 Ghosts 的 `G_Spawn` 对照："`2046`-slot, `500 ms` FIFO reuse rule"）。
6. **⭐⭐⭐ `resolve` 必须越过那个界**：**"高水位线界定顺序分配，而一个被保留的槽按构造在它之外 —— 把那个号从 `spawn()` 扣留正是整个要点。按它界定查找也会让每一个通过 `spawnAt` 发布的静态实体不可解析，而因此对 `entity()`、`free()` 和那个碰撞视图不可见"`** ⇒ **"那个条件是一个精确的修正"**；而 `resolve(handle)` 与 `resolve(entityNum)` **是一个分层的**（只查在用 vs 再加代次）。
7. **⭐⭐⭐ `expiredEventEntities` 是只读收集**（**"那个实际的 free 与原生镜像移除仍然是一个外层的事务"**）⇒ **"一个只读的收集"**（与 §485 同族）；而判据是 `>` 而不是 `>=` ⇒ **"恰好 300ms 不过期，那是一个有意的边界"**（与 §489 的 `<` 同族）。
8. **⚠ 一个可报告的缺口**：`expiredEventEntities` 只遍历 `[firstDynamicEntityNum_, highWaterEntityNum_)`，而**被保留的槽在 `highWaterEntityNum_` 之上** ⇒ **一个通过 `spawnAt` 发布的事件实体（且带 `markFreeAfterEvent`）永远不会被 `expiredEventEntities` 收集** —— 与 `resolve`/`free` 都**显式处理了保留槽**形成对照。
9. **⚠ 一个可报告的小不一致**：`reset` 的注释说 **"the production caller supplies CODOL's confirmed first dynamic slot 27"**，而 §489 的 `.hpp` 已经把那个常量改成 **`37`** 并有 `CODDIFF(1649370): THIRTY-SEVEN, not 27` 的说明 ⇒ **那个 `.cpp` 注释没有一起更新**（与 §465/§482 的"注释与代码不同步"同族）。
10. **⭐⭐ `reset` 的 `highWaterEntityNum_ = firstDynamicEntityNum`** ⇒ **"第一个 spawn() 会拿到 37"** —— 与 §489 的零售流量测量（"其余 `37..750` 而最低恰是 `37`"）**完整闭合**。

## 九、`sv_entity_mp.cpp` 全文件总览

**`269` 行。**

**`10` 个方法**：`reset` / `reserve` / `spawnAt` / `spawn` / `free` / `rollbackFree` / `markFreeAfterEvent` / `expiredEventEntities` / `resolve(handle)` / `resolve(entityNum)` / `firstDynamicEntityNum` / `highWaterEntityNum` / `freeEntityCount`。

**`4` 个数据结构**：`entities_[2046]`（`SvEntityLifetime`）/ `reserved_[2046]`（`bool`）/ `freeEntities_`（`std::deque<uint32_t>`）/ `highWaterEntityNum_`。

**`7` 个反汇编锚点**：`G_Spawn 0x004E8C30` / `Ghosts G_Spawn 0x140168CA0` / `G_FreeEntity 0x004E8E70` / `G_Spawn`（CODOL）/ `G_FreeEntity`（Ghosts）。

## 十、未闭合点

- `markFreeAfterEvent` 的 `otherEntityNum` 参数在哪个消费者处被读。
- `expiredEventEntities` 的保留槽缺口是否真的会触发（需要一次在保留槽上的 `markFreeAfterEvent`）。
- 下一个文件：`sv_alpha_weapon_port_mp.cpp`（`14,940` 字节）。
