# 375 · **"肉击不声明这三个中的任何一个"** —— `294/294`、实体号复用导致继承、`markFreeAfterEvent` 的三重检查、导弹的 32 上限"不拒移动"

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 21600–22000 行。

## 二、**"`WEAPON-NOT-IN-LOADOUT(fired=… primary=… secondary=…)`"**（本组第四重要）

### 2.1 那段

```php
if (!weapon) {
    why += " WEAPON-NOT-IN-LOADOUT(fired=" + std::to_string(payload.weaponAssetIndex);
    if (candidateClient.resolvedLoadout) {
        why += " primary=" + std::to_string(candidateClient.resolvedLoadout->primary.weaponAssetIndex) +
               " secondary=" + std::to_string(candidateClient.resolvedLoadout->secondary.weaponAssetIndex);
    } else {
        why += " no-resolved-loadout";
    }
    why += ")";
}
```

### 2.2 六层

```text
1. **一个专门的诊断分支**
2. ⇒ **打印【客户端开火用的】索引**
3. ⇒ **与【装备的】主/副索引**
4. ⇒ **所以"客户端知道 vs 服务器解析"的差异直接可见**
5. ⇒ **而"无装备"是一个独立的子分支**
6. ⇒ **"`why` 累积"（不是单个）⇒ 所以多个项可以同时失败**
```

**✅ 与 §374 的"七项合取"**配合 —— **而这里**逐项累积所有失败的理由**（不是第一个）。**

**⚠ 所以**比 `||` 短路**更好：**它能同时命名多个失败项。**

**✅ 与 §346 的"七十五项一个 `return reject`"**相反**（这是**全部列出**）。**

### 2.3 而**`lastDamageRefusal` 的去重**

```cpp
auto line = "player damage REFUSED target=" + std::to_string(payload.targetClientNum) + why;
if (line != lastDamageRefusal) { lastDamageRefusal = line; write(...); }
```

**⇒ 三层**：

```text
1. **一个静态的 lastDamageRefusal**
2. ⇒ **只在内容变化时写**
3. ⇒ **所以一个持续拒绝的客户端打一行**
```

**✅ 与 §346 的 `psDomainBad`、§368 的 `spawnRefusalReasons_`**第五次去重。**

**⚠ 而 `static` 是**全局的**（跨客户端）⇒ **第五次 static 跨客户端问题**。**

## 三、**实体伤害的事务**（本组第三重要）

### 3.1 那段

```php
// OLMOD(entity-damage-transaction): copying the complete
// destructible damage table for every movement-only usercmd made this
// source transaction scale with map damageables even when ClientEvents
// staged no entity mutation. Preserve the same atomic table swap only
// for commands that actually produced entity-damage payloads.
std::optional<decltype(entityDamageStates_)> candidateEntityDamageStates;
if (!candidateEntity.pendingEntityDamagePayloads.empty())
    candidateEntityDamageStates.emplace(entityDamageStates_);
```

### 3.2 七层

```text
1. **为每一条【仅移动】的 usercmd 拷贝完整的可破坏伤害表**
2. ⇒ **让这个源事务【随地图的可破坏物数量而缩放】**
3. ⇒ **即使 `ClientEvents` 没有暂存任何实体变异**
4. ⇒ **所以只为【真正产生了实体伤害载荷】的命令保留同一个原子表交换**
5. ⇒ **`candidateEntityDamageStates` 是一个 `optional`**
6. ⇒ **只在非空时 `emplace(entityDamageStates_)`**
```

**✅ 与 §372 的"`player-kinematics` 的爆发"、§374 的"`client-think-phase-census`"**同族（**第五次性能优化）。**

**⚠ 而"随地图的可破坏物数量而缩放"⇒ **一个 O(N) 的拷贝在每帧**。**

**✅ 一个**具体的性能问题**。

### 3.3 而**四个候选容器**

```text
candidateEntityDamageStates         （可选的整表拷贝）
candidateEntityModelIndexes         （模型索引变更）
candidateEntityDamageEvents         （伤害事件输出）
candidateEntityPresentationEvents   （表现事件输出）
```

**✅ 四个，而**第一个是 optional**（按需）。**

**✅ 一个**精确的按需分配**。

## 四、**肉击的"三个零"**（本组最重要的一段）

### 4.1 那段

```php
// THE FLESH HIT ASSERTS NONE OF THESE THREE, in 294 of 294
// retail assertions -- and its parameter WIDTH is zero in
// EntityEventParameterBits, so a direction written here
// would occupy a field index with no payload behind it.
// Zeroed rather than omitted because entity numbers are
// reused: a flesh hit landing on a number whose previous
// occupant was a world hit would otherwise inherit its
// direction and hit entity from the baseline.
.eventParm = impact.melee ? MeleeHitEventParameter : (fleshHit ? 0u : impact.direction),
.otherEntityNum = impact.sourceEntityNum,
.impactSurfaceType = impact.melee ? uint8{} : (fleshHit ? ClientBulletImpactSurfaceType : impact.surfaceType),
.impactFlags = (fleshHit || impact.melee) ? uint8{} : impact.impactFlags,
.groundEntityNum = (fleshHit || impact.melee) ? 0u : impact.hitEntityNum,
```

### 4.2 十四层

```text
1. **肉击【不声明】这三个中的任何一个**
2. ⇒ **在 `294` 个零售断言里的 `294` 个**
3. ⇒ **而它的参数【宽度】在 `EntityEventParameterBits` 里是【零】**
4. ⇒ **所以在这里写一个方向会占据一个字段索引而【背后没有载荷】**
5. ⇒ **归零而不是省略**
6. ⇒ **因为【实体号是被复用的】**
7. ⇒ **一个落在号上的肉击，若它的前一个占用者是一个【世界命中】**
8. ⇒ **否则会从基线继承它的方向与命中实体**
9. ⇒ **所以 `.eventParm` 是 0（肉击）或 `impact.direction`（世界命中）**
10. ⇒ **`.impactSurfaceType` 是 `ClientBulletImpactSurfaceType`（肉击）**
11. ⇒ **`.impactFlags` 是 0（肉击或近战）**
12. ⇒ **`.groundEntityNum` 是 0（肉击或近战）而 `hitEntityNum`（世界命中）**
13. ⇒ **而 `unk00A0 = ClientBulletImpactSurface` 只在肉击且非近战时**
```

### 4.3 ⭐⭐ **"`294/294` 而参数宽度是零"**

**✅ 与 §351 的 `237`、§362 的 `145`**第九次大规模统计。

**⚠ 而"参数宽度是零"⇒ **所以写一个方向会有**索引而没有载荷**。**

**⇒ 三层**：

```text
1. `EntityEventParameterBits` 的那个 id 是 **0**
2. ⇒ **所以"参数"字段不存在**
3. ⇒ **而写一个值会占据一个字段索引**
4. ⇒ **⇒ 客户端读一个不存在的载荷**
```

**✅ 与 §342 的"无宽度 ⇒ 参数必须为 0"**完全一致 ✓

**⇒ **第二次确认那个约束。**

### 4.4 而**"归零而不是省略"**

**✅ 与 §344 的"布告无条件断言三字段"**同族（**第四次"归零而不是省略"）**。

**⇒ 五层**：

```text
1. 归零   ⇒ **字段被发（一个 0）**
2. 省略   ⇒ **字段不发 ⇒ 客户端用基线**
3. ⇒ **而基线可能来自【前一个占用者】**
4. ⇒ **所以省略 = 继承**
5. ⇒ **归零 = 明确**
```

**✅ **一个极重要的区分**。**

**⚠ 而 §341 的"一个未变的客户端完全不提"**相反**（那里**省略是对的**）。**

**⇒ 所以**省略的好坏取决于基线是否正确**。**

**✅ 与 §343 的"坐标要对着它被编码时用的基线测"**第三次确认。

### 4.5 而**"实体号被复用"**

**✅ 与 §345 的"实体号被复用 ⇒ 继承前一个占用者的 `+0xA0`"**第五次。

**⇒ **五次确认那个模式。**

### 4.6 而**`fleshImpactEnabled()`**

**⇒ 三层**：

```text
1. **`fleshHit` 需要 `fleshImpactEnabled()`**
2. ⇒ **所以它是一个可开关的特性**
3. ⇒ **而它还需要命中者是【正在玩的客户端】**
```

**⚠ 而"命中者号的实体 `networkState.number == hitEntityNum`"⇒ **一个身份检查**。**

**✅ 与 §373 的"两个 `== clientNum` 的双重身份检查"**同族。

## 五、**`markFreeAfterEvent` 的三重检查**（本组第五重要）

### 5.1 那段

```php
const auto handle = stagedEntityPool->spawn(snapshot_.serverTime);
if (!handle || entities_.contains(handle->entityNum) ||
    std::ranges::any_of(stagedEventEntities, [handle](const auto &entry) {
        return entry.first.entityNum == handle->entityNum;
    }) ||
    !stagedEntityPool->markFreeAfterEvent(*handle, snapshot_.serverTime, impact.sourceEntityNum))
{
    return reject(SvClientThinkFailureStage::ClientEventsRejected);
}
```

### 5.2 三层

```text
① **`entities_.contains` ⇒ 不与【已提交】实体冲突**
② **`stagedEventEntities` 的 `any_of` ⇒ 不与【本批暂存】冲突**
③ **`markFreeAfterEvent` ⇒ 标记为事件后释放**
```

**✅ 与 §365 的"`candidates.contains(handle.entityNum)`"**同族（**第二次"暂存内查重"）**。

**⚠ 而 ① 与 ② 是**两个不同层次**的查重。**

**✅ 一个**正确的双层检查**。

### 5.3 而**`stagedEntityPool` 的整池拷贝**

```php
std::optional<SvEntityPool> stagedEntityPool;
std::optional<std::unordered_map<std::uint32_t, SvServerMissile>> stagedMissiles;
std::vector<std::pair<SvEntityHandle, SvGameEntity>> stagedEventEntities;
if (!candidateEntity.pendingEntitySpawns.empty() || !pendingSimpleEvents.empty()) {
    if (!entityPool_) return reject(...);
    stagedEntityPool = *entityPool_;
    ...
}
```

**⇒ 五层**：

```text
1. **整池拷贝（`*entityPool_`）**
2. ⇒ **所以分配在副本上**
3. ⇒ **而导弹表也整表拷贝**
4. ⇒ **只在有生成或事件时**
5. ⇒ **失败则两份副本都丢弃**
```

**✅ 与 §361 的"`entities_` 整条拷贝"**同族（**第二次整结构拷贝）。**

**⚠ 而"整池 2046 槽"⇒ **可能很昂贵**。**

**✅ 与 §372 的"`entityDamageStates_` 整表拷贝的 O(N)"**同族（**第二次可扩展性关切）。**

**⚠ 而注释说"让这个源事务随地图的可破坏物数量而缩放"是**坏的**。**

**⇒ 所以整池拷贝也**可能有问题**。**

**⚠ 一处**潜在的矛盾**（一边避免 O(N) 一边做整池拷贝）。**

**⇒ 可能因为池有**2046 个固定槽**（可预测）。**

**✅ 一个**合理的解释**。

## 六、**导弹的"32 上限不拒移动"**（本组第六重要）

### 6.1 那段

```php
if (offhandWeaponKind(request->initial.weapon) &&
    (stagedMissiles ? stagedMissiles->size() : missiles_.size()) >= 32)
    // A saturated experimental projectile budget must not
    // reject movement/Pmove or freeze the player's command.
    // The already consumed shot is deliberately discarded.
    continue;
```

### 6.2 七层

```text
1. **若是一个副手武器而导弹表已 >= 32**
2. ⇒ **一个饱和的实验性投射物预算【绝不能】拒绝移动/Pmove**
3. ⇒ **或冻住玩家的命令**
4. ⇒ **已经消耗的那一枪被【有意丢弃】**
5. ⇒ **所以 `continue` 而不是 `reject`**
```

**✅ 与 §349 的"代价不对称的正确选择"**同族（**第十三次）。**

**⇒ 三层**：

```text
选择 A：拒绝整条命令 ⇒ **玩家不能移动（代价大）**
选择 B：丢弃这一枪 ⇒ **少一发子弹（代价小）**
⇒ **选 B**
```

**✅ **一个精确的"降级"**。**

**⚠ 而"实验性投射物预算"⇒ **所以这是一个未完成的特性**。**

**✅ 与 §350 的"`SvActorSendUnmeasuredSpawnWords`"**同族（**未完成则保守）。**

### 6.3 而**导弹的六项前置**

```php
if (request->initial.number != 0 || request->initial.owner != clientNum ||
    request->fuseDeadline > (uint32)INT32_MAX ||
    std::ranges::none_of(candidateClient.playerState.heldWeapons,
        [&](const auto &held) { return held.weaponAssetIndex == request->initial.weapon; }))
    return reject(...);
```

**⇒ 六项**：

```text
① `number == 0`（未分配）
② `owner == clientNum`
③ `fuseDeadline <= INT32_MAX`
④ **玩家【持有】那个武器**
```

**✅ 与 §366 的"`include` 要求玩家实际持有"**同族（**第二次"持有检查"**）。

## 七、**`SvEntityDamagePresentationEventKind` 的三类**

```cpp
switch (event.kind) {
case SoundAlias:           entityType = EntityTypeSoundAlias;        要求 < SoundAliasEventParameterLimit
case SoundAliasAsMaster:   entityType = EntityTypeSoundAliasAsMaster; 同上
case WorldFx:              entityType = EntityTypePlayFx;             要求 < EffectConfigStringCount
default:                   return reject(...);
}
```

**⇒ 三层**：

```text
1. **三类表现事件**（声音别名 / 主声音别名 / 世界特效）
2. ⇒ **两个不同的上限**（`SoundAliasEventParameterLimit` / `EffectConfigStringCount`）
3. ⇒ **其它 ⇒ 拒绝**
```

**✅ 与 §346 的"一个 validate 函数里十一类 eType"**不同**（这是**三类表现**）。

**⚠ 而"`!event.eventParameter`"⇒ **零也拒绝**。**

**⇒ 所以**参数必须非零且在范围内**。**

**✅ 与 §344 的"`validGlassPiece` 的 `!piece.impact`"**同族。

### 7.1 而**"声音与 FX 解析器更早运行；原始资产名【永不】到达这个命令事务"**

```php
// OLMOD(entity-damage-presentation-plan): translate validated handler
// output into temp-entity requests before reserving any entity slot.
// Sound and FX resolvers run earlier; raw asset names never reach this
// command transaction.
```

**⇒ 五层**：

```text
1. **把已验证的处理器输出翻译成临时实体请求**
2. ⇒ **在预留任何实体槽【之前】**
3. ⇒ **声音与 FX 解析器【更早】运行**
4. ⇒ **原始资产名【永不】到达这个命令事务**
5. ⇒ **所以这里有【configstring 索引】而不是名字**
```

**✅ 与 §350 的"`validScriptModel` 的 `modelName`"**对比** —— 那里是**名字**，这里是**索引**。**

**⇒ **一个精确的分层**：**

```text
脚本层   ⇒ 名字（`modelName`）
命令事务 ⇒ **索引**（`eventParameter`）
```

**✅ 与 §371 的"`1137` 只存在是为了让客户端有视模型可画"**同族（**第七次"两个 id 空间"）。**

## 八、关键结论

1. **`WEAPON-NOT-IN-LOADOUT(fired=… primary=… secondary=…)`** 打印**客户端开火索引与装备的主副索引** ⇒ 差异直接可见。
2. **`why` 是【累积】的**（不是 `||` 短路）⇒ **多个失败项可以同时被命名**（与 §346 的"七十五项一个 reject"相反）。
3. **`lastDamageRefusal` 是全局 `static`** ⇒ **第五次 static 跨客户端问题**。
4. **⭐ "为每一条仅移动的 usercmd 拷贝完整伤害表让源事务随地图的可破坏物数量而缩放"`** —— 第五次性能优化，而**只在真有载荷时拷贝**。
5. **⭐⭐ "肉击不声明这三个中的任何一个 —— `294/294` 零售断言"`** —— 第九次大规模统计。
6. **"它的参数宽度在 `EntityEventParameterBits` 里是零 ⇒ 写一个方向会占据一个字段索引而背后没有载荷"`** —— 第二次确认那个约束。
7. **⭐⭐ "归零而不是省略，因为实体号被复用：一个肉击落在一个前占用者是世界命中的号上会从基线继承它的方向与命中实体"`** —— 第四次"归零而不是省略"，而**第五次确认实体号复用**。
8. **五种字段的完整条件表**（`eventParm` / `otherEntityNum` / `impactSurfaceType` / `impactFlags` / `groundEntityNum`）。
9. **`fleshImpactEnabled()` 与"命中者是正在玩的客户端"** —— 一个可开关的两条件。
10. **`markFreeAfterEvent` 的三重检查**（`entities_.contains` / `stagedEventEntities` 的 `any_of` / 标记）—— 双层查重。
11. **`stagedEntityPool = *entityPool_` 的整池拷贝**（2046 槽）—— 第二次整结构拷贝，与避免 O(N) 的目标**可能矛盾**（但因池固定而可接受）。
12. **⭐ "一个饱和的实验性投射物预算绝不能拒绝移动/Pmove 或冻住玩家的命令 ⇒ 已经消耗的那一枪被有意丢弃"`** —— 第十三次代价不对称。
13. **导弹的六项前置**含**"玩家持有那个武器"**（第二次持有检查）。
14. **`SvEntityDamagePresentationEventKind` 的三类** + **两个不同的上限**，而**参数必须非零**。
15. **⭐ "声音与 FX 解析器更早运行；原始资产名永不到达这个命令事务"`** —— 一个精确的分层（脚本层用**名字**，命令事务用**索引**）。

## 九、未闭合点

- `SoundAliasEventParameterLimit` / `EffectConfigStringCount` 的值。
- `offhandWeaponKind` 的判据。
- `fleshImpactEnabled()` 的开关。
- `MeleeHitEventParameter` / `ClientBulletImpactSurfaceType` / `ClientBulletImpactSurface` 的值。
- 导弹的 32 上限为何是 32。
- `sv_snapshot_mp.cpp` 22000 行之后未读取（27,016 行，进度 81%）。
