# 376 · **"按逆序回滚并重建旧的碰撞/原生镜像"** —— 七处 commit/rollback 的对称、`CLIENTTHINK PHASE` 的四段计时、爆炸的十一项验证

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 22000–22400 行。

## 二、**七处 `std::swap` 的提交与对称回滚**（本组最重要的一段）

### 2.1 提交（七处）

```cpp
std::swap(state.client, candidateClient);
std::swap(state.entity, candidateEntity);
std::swap(glassState_, candidateGlassState);
std::swap(glassDamageState_, candidateGlassDamageState);
if (stagedMissiles) std::swap(missiles_, *stagedMissiles);
if (candidateEntityDamageStates) std::swap(entityDamageStates_, *candidateEntityDamageStates);
for (const auto &[entityNum, modelIndex] : candidateEntityModelIndexes)
    entities_.at(entityNum).networkState.modelIndex = modelIndex;
...
std::swap(*entityPool_, *stagedEntityPool);
for (auto &[handle, eventEntity] : stagedEventEntities) { entities_.emplace(...); insertedEventEntityNums.push_back(...); }
```

### 2.2 回滚（完全对称）

```cpp
const auto rollbackSourceCommit = [&, this]() {
    // OLMOD(source-native-command-rollback): reverse publication order
    // and rebuild the old collision/native image. candidate values now
    // hold every pre-commit owner because all publications used swap.
    for (const auto entityNum : insertedEventEntityNums) entities_.erase(entityNum);
    if (stagedMissiles) std::swap(missiles_, *stagedMissiles);
    if (stagedEntityPool) std::swap(*entityPool_, *stagedEntityPool);
    for (const auto &[entityNum, modelIndex] : previousEntityModelIndexes)
        entities_.at(entityNum).networkState.modelIndex = modelIndex;
    if (candidateEntityDamageStates) std::swap(entityDamageStates_, *candidateEntityDamageStates);
    std::swap(glassDamageState_, candidateGlassDamageState);
    std::swap(glassState_, candidateGlassState);
    std::swap(state.entity, candidateEntity);
    std::swap(state.client, candidateClient);
    rebuildCollisionView();
};
```

### 2.3 十四层

```text
1. **按【逆序】回滚并重建旧的碰撞/原生镜像**
2. ⇒ **候选值现在持有每一个 pre-commit 所有者**
3. ⇒ **因为所有发布都用 `swap`**
4. ⇒ **所以回滚【不需要任何拷贝】**
5. ⇒ **七处 `swap` ⇒ 七处 `swap` 回来（对称）**
6. ⇒ **而两处【非 swap】的**：
     · **`entities_.emplace`（插入）⇒ 回滚是 `erase`**
     · **`modelIndex` 赋值 ⇒ 回滚用 `previousEntityModelIndexes`**
7. ⇒ **所以混合了两种回滚机制**
8. ⇒ **而顺序是逆序**（后提交的先回滚）
9. ⇒ **最后 `rebuildCollisionView()`**
```

**✅ ⭐ **"候选值现在持有每一个 pre-commit 所有者，因为所有发布都用 `swap`"** —— 这是本文件里**最优雅的事务设计**。**

**⇒ 三层**：

```text
swap 前：candidate = 新值，state = 旧值
swap 后：state = 新值，candidate = 旧值
⇒ **所以 candidate 就是"回滚所需的一切"**
```

**✅ 与 §364 的"`std::swap` 作为零成本的回滚保存"**完全一致 ✓

**⇒ **第三次确认那个手法。**

### 2.4 而**"逆序"**

**⇒ 三层**：

```text
1. 提交顺序：client → entity → glass → missiles → pool
2. ⇒ **回滚是反的**：pool → missiles → glass → entity → client
3. ⇒ **因为后提交的可能依赖先提交的**
```

**✅ 一个**正确的栈式回滚**。

**⚠ 而"七处"⇒ **一个复杂的多资源事务**。**

**✅ 与 §349 的"staged-then-commit"**第八次。

### 2.5 而**两处非 swap 的补偿**

```cpp
// 提交
for (auto &[handle, eventEntity] : stagedEventEntities) {
    const auto [_, inserted] = entities_.emplace(handle.entityNum, std::move(eventEntity));
    if (!inserted) break;
    insertedEventEntityNums.push_back(handle.entityNum);
}
// 回滚
for (const auto entityNum : insertedEventEntityNums) entities_.erase(entityNum);
```

**⇒ 四层**：

```text
1. **`emplace` 的返回值决定是否记入 `insertedEventEntityNums`**
2. ⇒ **所以记录【只包含真正插入的】**
3. ⇒ **回滚 `erase` 那些**
4. ⇒ **而"若有一个不插入 ⇒ `break`"**
```

**⚠ 而 `break` 之后 `insertedEventEntityNums.size() != stagedEventEntities.size()`。**

**⇒ 所以检查在那之后：**

```cpp
if (insertedEventEntityNums.size() != stagedEventEntities.size()) {
    rollbackSourceCommit();
    return reject(ClientEventsRejected);
}
```

**✅ 一个**精确的完整性检查**（部分插入 ⇒ 全回滚）。

**✅ 与 §346 的"全有或全无"**第九次。

## 三、**`CLIENTTHINK PHASE` 的四段计时**（本组第二重要）

### 3.1 那段

```php
struct ClientThinkPhaseAggregate {
    uint64 count{}, realUs{}, transactionUs{}, rebuildUs{}, callbacksUs{}, totalUs{}, maxTotalUs{};
};
static std::array<ClientThinkPhaseAggregate, 2> phaseAggregates{};
...
const auto moving = command.forwardMove != 0 || command.rightMove != 0;
auto &phase = phaseAggregates[moving ? 1u : 0u];
const auto totalUs = microseconds(thinkPhaseBegan, thinkPhaseFinished);
++phase.count;
phase.realUs += microseconds(thinkPhaseBegan, thinkRealFinished);
phase.transactionUs += microseconds(thinkRealFinished, sourceCommitFinished);
phase.rebuildUs += microseconds(sourceCommitFinished, collisionRebuildFinished);
phase.callbacksUs += microseconds(collisionRebuildFinished, thinkPhaseFinished);
phase.totalUs += totalUs;
phase.maxTotalUs = std::max(phase.maxTotalUs, totalUs);
```

### 3.2 九层

```text
1. **两个聚合桶**（`moving ? 1 : 0`）⇒ **移动 vs 空闲**
2. ⇒ **四段**：
     · `real`        = thinkReal（pmove + 转换 + 事件）
     · `tx`          = 源事务（swap 七处）
     · `rebuild`     = 碰撞重建
     · `callbacks`   = 提交后回调
3. ⇒ **`total` 与 `maxTotal`**
4. ⇒ **每 5 秒报一次**
```

**✅ 与 §374 的"`client-think-phase-census`"**完全闭合 ✓

**⇒ 而这里是**它的实现**。**

### 3.3 而**格式**

```text
"CLIENTTHINK PHASE idle n=%llu avg=%lluus real=%llu tx=%llu rebuild=%llu callbacks=%llu max=%llu | move n=... avg=..."
```

**⇒ 三层**：

```text
1. **两个桶并列（`|` 分隔）**
2. ⇒ **各七个字段**
3. ⇒ **所以一次比较移动 vs 空闲的完整分解**
```

**✅ 与 §372 的"`CLIENTTHINK` 的每五秒一行"**同族。**

**⚠ 而"`moving = forwardMove != 0 || rightMove != 0`"⇒ **只看移动键**。**

**⇒ 所以**开火但不动**归入"空闲"。**

**✅ 一个**合理的分类**（因为关切是"移动让 ClientThink 变慢"）。

### 3.4 而**时间重置条件**

```cpp
if (snapshot_.serverTime < phaseReportServerTime) {
    phaseAggregates = {};
    phaseReportServerTime = snapshot_.serverTime;
}
if (!phaseReportServerTime) phaseReportServerTime = snapshot_.serverTime;
```

**⇒ 四层**：

```text
1. **`serverTime` 倒退 ⇒ 清空**（新地图/新局）
2. ⇒ **而 `!phaseReportServerTime` ⇒ 初始化**
3. ⇒ **所以两处都需要**
4. ⇒ **而倒退是一个**可靠的**"新代际"信号**
```

**✅ 与 §347 的"`newDeliveryGeneration` 的 `serverTime` 倒退"**同族（**第二次"用时间倒退检测新代际"）。**

## 四、**导弹帧事务的十一项验证**（本组第三重要）

### 4.1 那段

```php
// OLMOD(missile-frame-transaction): stage only missile entities, not
// the entire map. A rejected continuation or native presentation must
// leave every missile origin, trajectory, fuse and pool slot intact.
```

### 4.2 五层

```text
1. **只暂存【导弹实体】，不是整张地图**
2. ⇒ **一个被拒的继续或原生表现必须让每一个导弹的原点、轨迹、引信与池槽【完好】**
3. ⇒ **所以是一个**精确的**暂存范围**
```

**✅ 与 §375 的"`stagedEntityPool = *entityPool_` 的整池拷贝"**对比** —— 那里是**整池**，这里是**只导弹**。**

**⚠ 所以**一个改进**（从整池到只导弹）。**

**⚠ 而"只导弹"⇒ **但 `candidateMissilePool = *entityPool_` 仍是整池**。**

**⚠ 一处**残留的整池拷贝**。**

### 4.3 而**九项前置检查**

```php
if (!entityPool_->resolve(missile.handle) || entity == entities_.end() ||
    missile.handle.entityNum != number || missile.network.number != number ||
    entity->second.networkState.number != number ||
    entity->second.networkState.eType != SvEntityTypeMissile ||
    missile.lastUpdateTime > snapshot_.serverTime)
    return false;
if (missile.hasRunFrame && missile.lastUpdateTime == snapshot_.serverTime) continue;
```

**⇒ 七项 + 一个跳过。**

**✅ 与 §373 的"八项 `converted_state_mismatch`"**同族。**

**⚠ 而三项都是**"`number` 一致"**（`missile.handle` / `missile.network` / `entity.networkState`）。**

**⇒ 所以**一个导弹的身份有四个副本**。**

**✅ 与 §355 的"`ps` 与 `ent` 两个位置"**同族（**第五次"多副本一致"）。**

### 4.4 而**"`hasRunFrame && lastUpdateTime == serverTime` ⇒ 跳过"**

```php
// A throw is eligible in its spawn frame, including an already
// due fuse. Only an actually committed update may suppress a
// second simulation at the same clock; spawn time alone cannot.
if (missile.hasRunFrame && missile.lastUpdateTime == snapshot_.serverTime) continue;
```

**⇒ 六层**：

```text
1. **一次投掷在它的【生成帧】就是合格的**（包括一个已经到期的引信）
2. ⇒ **只有一次【实际提交的更新】才能在同一时钟上抑制第二次模拟**
3. ⇒ **仅生成时间【不能】**
4. ⇒ **所以 `hasRunFrame` 与 `lastUpdateTime` 都要**
```

**✅ 一个**精确的"是否已模拟"判据**。**

**⚠ 而"仅生成时间不能"⇒ **一个真实的错误被规避**。**

### 4.5 而**"原生 `G_RunFrame` 走【升序】实体号"**

```php
// Native G_RunFrame walks ascending entity numbers. Never let an
// unordered_map choose collision/think continuation order.
std::ranges::sort(numbers);
```

**⇒ 四层**：

```text
1. **原生 `G_RunFrame` 走升序实体号**
2. ⇒ **绝不让一个 `unordered_map` 选择碰撞/think 的继续顺序**
3. ⇒ **所以 `sort(numbers)`**
4. ⇒ **一个确定性要求**
```

**✅ 与 §355 的"`actorNumbers` 排序"**同族（**第八次确定性要求）。**

**⇒ **一个贯穿全文件的原则**。**

### 4.6 而**"一个非副手的导弹以前没有 runner"**

```php
// 28700: a NON-offhand missile (an RPG / AT4 / Stinger round) used
// to have no runner at all and fell into `SvMissileRetirement` on
// its first frame -- launched, vanished, never exploded. This is
// the ordinary flight continuation, expressed in the world where
// the trajectory evaluator and the point-trace runner already
// live. Offhand weapons keep their own branch untouched.
```

**⇒ 八层**：

```text
1. **一个【非副手】的导弹（一个 RPG / AT4 / Stinger 弹）【以前根本没有 runner】**
2. ⇒ **而在它【第一帧】就掉进 `SvMissileRetirement`**
3. ⇒ **发射了、消失了、从未爆炸**
4. ⇒ **这是普通的飞行继续**
5. ⇒ **表达在【轨迹求值器与点 trace runner 已经住的地方】**
6. ⇒ **副手武器保持它们自己的分支不动**
```

**✅ 与 §350 的"门不可见"**同族（**第六次"一个缺失的分支"）。**

**⚠ 而"发射了、消失了、从未爆炸"⇒ **第八次具体症状**。**

### 4.7 而**"门以前要求 runner/表【并且】有导弹"**

```php
// 28700: the gate used to require a runner/table AND missiles. With no
// offhand in the loadout both tables are empty, so a launcher round was
// never stepped at all. Flight is now intrinsic to this world, so the
// only condition is "there are missiles".
if (!missiles_.empty()) { ... }
```

**⇒ 六层**：

```text
1. **门过去要求一个 runner/表【并且】有导弹**
2. ⇒ **装备里没有副手时两张表都是空的**
3. ⇒ **所以一发发射器弹【根本不被步进】**
4. ⇒ **飞行现在是这个世界的【内在属性】**
5. ⇒ **所以唯一的条件是"有导弹"**
6. ⇒ **一个"两个条件相与"的经典 bug**
```

**✅ 与 §346 的"缺一个 eType 拒整帧"**不同** —— 这里是**一个不必要的合取**。**

**⇒ **第三次"多条件相与导致的静默失败"。**

## 五、**爆炸的十一项验证**（本组第四重要）

### 5.1 那段

```php
if (detonation->playerDamage.size() > MaximumGameClients ||
    (!detonation->playerDamage.empty() &&
        (detonation->weaponName.empty() || detonation->weaponName.size() > 127 ||
         detonation->weaponName.find('\0') != std::string::npos)))
    return false;
std::array<bool, MaximumGameClients> damaged{};
for (const auto &damage : detonation->playerDamage) {
    const auto &payload = damage.payload;
    if (!SV_IsPlayerDamagePayloadValid(payload, PlayerDamagePayloadLimits) ||
        payload.inflictorEntityNum != number ||
        payload.attackerEntityNum != missile.network.owner ||
        payload.weaponAssetIndex != missile.network.weapon ||
        damaged[payload.targetClientNum])
        return false;
    damaged[payload.targetClientNum] = true;
    const auto target = clientStates_.find(payload.targetClientNum);
    if (target == clientStates_.end() ||
        target->second.client.gameplayState != Playing ||
        target->second.client.deathState ||
        target->second.client.playerState.health <= 0 ||
        target->second.client.appliedSpawnSequence != damage.spawnSequence ||
        target->second.client.playerState.spawnGeneration != damage.spawnGeneration ||
        std::ranges::none_of(activeClients, [&](const auto &client) {
            return client.clientNum == payload.targetClientNum; }))
        return false;
}
```

### 5.2 五层

```text
第一层（集合）：玩家数 <= `MaximumGameClients`
第二层（名）：武器名非空 / <= 127 / 无 NUL
第三层（每个载荷的五项）：
     · `SV_IsPlayerDamagePayloadValid`
     · **`inflictorEntityNum == number`**（这个导弹）
     · **`attackerEntityNum == missile.network.owner`**
     · **`weaponAssetIndex == missile.network.weapon`**
     · **不重复伤害同一目标**
第四层（目标的七项）：
     · 存在 / Playing / 未死 / 活着
     · **`appliedSpawnSequence` 匹配**
     · **`spawnGeneration` 匹配**
     · **在 `activeClients` 里**
```

**✅ **一个极严的三重身份检查**（inflictor / attacker / weapon 都必须匹配）。**

**✅ 与 §373 的"两个 `== clientNum`"**同族（**第三次"多重身份检查"）。**

### 5.3 而**"`appliedSpawnSequence` 与 `spawnGeneration` 都要匹配"**

**⇒ 三层**：

```text
1. `spawnGeneration` 防跨死亡（§355）
2. ⇒ **而 `appliedSpawnSequence` 防一个【未应用的出生】**
3. ⇒ **两者都要 ⇒ 所以是**双重生命检查**。
```

**✅ 与 §355 的"`spawnGeneration`"**第四次确认。

## 六、关键结论

1. **⭐⭐ 七处 `std::swap` 的提交与**完全对称**的逆序回滚** —— 而 **"候选值现在持有每一个 pre-commit 所有者，因为所有发布都用 `swap`"`** 是本文件最优雅的事务设计。
2. **两处非 swap 的补偿**（`entities_.emplace` ⇒ `erase`；`modelIndex` ⇒ `previousEntityModelIndexes`）—— 混合两种回滚机制。
3. **回滚是【逆序】的**（后提交的先回滚）—— 一个正确的栈式回滚。
4. **"部分插入 ⇒ 全回滚"** 的完整性检查（第九次全有或全无）。
5. **⭐ `CLIENTTHINK PHASE` 的四段计时**（`real` / `tx` / `rebuild` / `callbacks`）与**移动 vs 空闲两个桶**。
6. **`moving = forwardMove != 0 || rightMove != 0`** —— 只看移动键，所以**开火但不动归入空闲**。
7. **`serverTime` 倒退 ⇒ 清空聚合** —— 第二次"用时间倒退检测新代际"。
8. **⭐ "只暂存导弹实体，不是整张地图"`** —— 一个从整池到只导弹的改进（但 `candidateMissilePool` 仍整池）。
9. **导弹的七项前置**含**三项 `number` 一致性**（`missile.handle` / `missile.network` / `entity.networkState`）⇒ **一个导弹的身份有四个副本**。
10. **⭐ "一次投掷在它的生成帧就是合格的，包括一个已到期的引信；只有一次【实际提交的更新】才能在同一时钟上抑制第二次模拟，仅生成时间不能"`**。
11. **"原生 `G_RunFrame` 走升序实体号 ⇒ 绝不让一个 `unordered_map` 选择顺序"`** —— 第八次确定性要求。
12. **⭐ "一个非副手的导弹（RPG/AT4/Stinger）以前根本没有 runner ⇒ 在第一帧就掉进 `SvMissileRetirement` ⇒ 发射了、消失了、从未爆炸"`** —— 第六次"一个缺失的分支"。
13. **"门过去要求一个 runner/表【并且】有导弹；装备里没有副手时两张表都是空的 ⇒ 一发发射器弹根本不被步进"`** —— 第三次"多条件相与导致的静默失败"。
14. **爆炸的十一项验证**含**三重身份检查**（`inflictor` / `attacker` / `weapon` 都必须匹配）。
15. **"`appliedSpawnSequence` 与 `spawnGeneration` 都要匹配"`** —— 双重生命检查（第四次确认 `spawnGeneration`）。

## 七、未闭合点

- `SvMissileFrameResult` 的三种变体。
- `stepProjectileMissile` 与 `stepFactorySpecialMissile` 的分工。
- `SvMissileRetirement` 的条件。
- `refreshClientCollisionView` 的实现。
- `damaged[]` 的数组大小与 `MaximumGameClients`。
- `sv_snapshot_mp.cpp` 22400 行之后未读取（27,016 行，进度 83%）。
