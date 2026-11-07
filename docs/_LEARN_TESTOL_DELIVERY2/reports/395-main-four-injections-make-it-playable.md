# 395 · **"四个注入物齐了才算可玩"** —— `setGameplayAuthorityReady` 的五次联动、SD 的四个 `use` 定义、`setSpawnAnimationRunner` 是唯一不持锁的

## 一、范围

本报告学习 `sv_main_mp.cpp` 2050–2400 行。

## 二、**`setGameplayAuthorityReady` 的五次联动**（本组最重要的一段）

### 2.1 五个注入点

```cpp
void setSharedPmoveRunner(runner) {
    const std::lock_guard lock(mutex_);
    world_.setSharedPmoveRunner(std::move(runner));
    clients_.setGameplayAuthorityReady(world_.sharedPmoveAvailable());
}
void setWeaponMovementRunner(runner) { ... 同样 ... }
void setPlayerStateToEntityStateConverter(converter) { ... 同样 ... }
void setClientEventsHandler(handler) { ... 同样 ... }
```

**⇒ 四个注入点带联动，而 `setDeathAnimationRunner` / `setAltFireResolver` / 四个 trace runner / `setTriggerContactRunner` / `setNativeEntityMirrorSynchronizer`【不】带。**

### 2.2 十层

```text
1. **`world_.sharedPmoveAvailable()` 的【四个】** 见 §349
2. ⇒ **每注入一个就重算一次"可玩性"**
3. ⇒ **并推给 `clients_`**
4. ⇒ **所以四个注入物齐了才算可玩**
5. ⇒ **而四个不带联动的注入是【不需要】的**：
     · `DeathAnimationRunner`  ⇒ 只影响死亡表现
     · `AltFireResolver`       ⇒ 只影响 alt 切换
     · 四个 trace runner        ⇒ 只影响碰撞查询
     · `TriggerContactRunner`  ⇒ 只影响触发体
     · `MirrorSynchronizer`    ⇒ 只影响镜像
6. ⇒ **所以"可玩性"的判据是【最小集】**
```

**✅ 与 §349 的"`sharedPmoveAvailable()` 的四项"**完全闭合 ✓

**⇒ 三层**：

```text
四项：`sharedPmoveRunner_` / `weaponMovementRunner_` /
      `playerStateToEntityStateConverter_` / `clientEventsHandler_`
⇒ **而这四项恰好是四个带联动的 setter**
⇒ **⇒ 一对一**
```

**✅ ⭐ **一个"判据与注入点一一对应"的闭合**。**

**⚠ 而"四个不带联动的"⇒ **每一个都是可选增强**。**

**✅ 一个**精确的最小可玩集**。**

### 2.3 而**`setSpawnAnimationRunner` 是唯一【不持锁】的**

```cpp
void ServerCore::setSpawnAnimationRunner(SvSpawnAnimationRunner runner)
{
    world_.setSpawnAnimationRunner(std::move(runner));
}
```

**⚠ 而所有其它 setter 都有 `const std::lock_guard lock(mutex_);`。**

**⇒ 三层**：

```text
唯一没有锁的 setter
⇒ **而其它十七个都有**
⇒ **⇒ 一处真实的并发缺陷**
```

**⚠ 而注释**没有解释**。**

**⇒ 所以**可能是一个遗漏**。**

**✅ 与 §388 的"两把锁"**不同（这是**零把锁**）。

**⚠ 一个**需要标注的缺陷**。**

### 2.4 而 `setLoadoutProvider` 的**额外清 `resolvedLoadouts_`**

```cpp
void setLoadoutProvider(LoadoutProvider provider) {
    const std::lock_guard lock(mutex_);
    loadoutProvider_ = std::move(provider);
    resolvedLoadouts_.clear();
}
```

**⇒ 三层**：

```text
1. **换 provider ⇒ 清缓存**
2. ⇒ **因为旧解析结果可能不再有效**
3. ⇒ **⇒ 一个正确的缓存失效**
```

**✅ 与 §381 的"`effectivePlayerAbilities` 从不存储而是每次计算"**相反**（这里**有缓存**）。**

**⚠ 所以**两种策略并存**：**

```text
`effectivePlayerAbilities` ⇒ **每次计算**
`resolvedLoadouts_`        ⇒ **缓存 + 换 provider 时清**
```

**✅ 一个**合理的区分**（武器解析昂贵、技能叠加便宜）。**

## 三、**SD 的四个 `use` 定义**（本组第二重要）

### 3.1 那段

```cpp
const std::array useDefinitions{
    SvUseObjectDefinition{
        .objectId = sdBombSiteRuntime_[0].plantTrigger.objectId,
        .ownerTeam = SvTeam::Sc,
        .allowedRelation = SvUseTeamRelation::Enemy,
        .useDurationMilliseconds = sdBombRules_.plantMilliseconds,
        .requiresKeyObject = true,
    },
    SvUseObjectDefinition{
        .objectId = sdBombSiteRuntime_[1].plantTrigger.objectId,
        .ownerTeam = SvTeam::Sc,
        .allowedRelation = SvUseTeamRelation::Enemy,
        .useDurationMilliseconds = sdBombRules_.plantMilliseconds,
        .requiresKeyObject = true,
    },
    SvUseObjectDefinition{
        .objectId = sdBombSiteRuntime_[0].defuseTrigger.objectId,
        .ownerTeam = SvTeam::Sc,
        .allowedRelation = SvUseTeamRelation::Friendly,
        .useDurationMilliseconds = sdBombRules_.defuseMilliseconds,
    },
    SvUseObjectDefinition{
        .objectId = sdBombSiteRuntime_[1].defuseTrigger.objectId,
        .ownerTeam = SvTeam::Sc,
        .allowedRelation = SvUseTeamRelation::Friendly,
        .useDurationMilliseconds = sdBombRules_.defuseMilliseconds,
    },
};
```

### 3.2 十一层

```text
1. **四个 use 定义**：两个站点 × （下包 / 拆包）
2. ⇒ **下包：`ownerTeam = Sc` / `allowedRelation = Enemy` / `plantMilliseconds` / `requiresKeyObject = true`**
3. ⇒ **拆包：`ownerTeam = Sc` / `allowedRelation = Friendly` / `defuseMilliseconds` / 无 key**
4. ⇒ **而 `ownerTeam` 都是 `Sc`**（**守方拥有那些盒子**）
5. ⇒ **所以下包要求"敌方"**（Tf）
6. ⇒ **而拆包要求"友方"**（Sc）
7. ⇒ **`requiresKeyObject` 只有下包有**（**炸弹本体是一个 key object**）
```

### 3.3 ⭐ **"`ownerTeam = Sc` 而 `Enemy` 意味着 Tf 可以下包"**

**✅ 与 §391 的"攻方全灭而【已下包】⇒ 没有结果"**配合。**

**⇒ 三层**：

```text
`ownerTeam = Sc`（守方）
⇒ `allowedRelation = Enemy` ⇒ **只有 Tf 可以用**
⇒ **⇒ 所以"敌人"是一个【相对关系】而不是一个固定队伍**
```

**✅ ⭐ **一个"关系而非身份"的权限模型**。**

**⚠ 而"`requiresKeyObject`"⇒ **一个额外的物品要求**。**

**✅ 与 §380 的"`consumePlayerUavAction` 的 `rewardActionType`"**不同（这是**一个持有检查**）。

## 四、**`configureSdBombRuntime` 的二十项验证**（本组第三重要）

### 4.1 三个 lambda

```cpp
const auto finiteOrigin = [](const SvSdBombSite &site) { return all_of(site.origin, isfinite); };
const auto finiteVector = [](const auto &vector) { return all_of(vector, isfinite); };
const auto validVolume = [&](const SvTriggerVolume &volume) {
    return volume.objectId && volume.collision.clipHandle == volume.objectId &&
        volume.collision.contents && finiteVector(volume.origin) && finiteVector(volume.angles);
};
const auto matchesSite = [](const SvSdBombSite &site, const SvSdBombSiteRuntime &runtime) {
    return runtime.label == site.label &&
        runtime.plantTrigger.objectId == site.triggerModel &&
        runtime.plantTrigger.origin == site.origin &&
        runtime.plantTrigger.angles == site.angles &&
        runtime.defuseTrigger.objectId == site.defuseTriggerModel &&
        runtime.defuseTrigger.origin == site.defuseOrigin &&
        runtime.defuseTrigger.angles == site.defuseAngles;
};
```

### 4.2 九层

```text
1. **`validVolume` 五项**：
     · `objectId` 非零
     · **`collision.clipHandle == objectId`**（一个强制等式）
     · `collision.contents` 非零
     · `origin` / `angles` 有限
2. ⇒ **`matchesSite` 七项**（label + 三个 plant 字段 + 三个 defuse 字段）
3. ⇒ **所以是【站点与运行时的精确对齐】**
4. ⇒ **而 2 个站点 × 7 = 14 项**
```

**✅ ⭐ **`collision.clipHandle == objectId`** —— 一个**冗余但有意的一致性检查**。**

**⇒ 三层**：

```text
`objectId` 是【逻辑 id】
`clipHandle` 是【碰撞句柄】
⇒ **强制相等 ⇒ 所以它们必须来自同一个分配**
```

**✅ 与 §365 的"`scriptMoverBrushModelIndex == brushModelClipHandle`"**完全同族（**第二次"两个 id 必须相等"）。**

**⚠ 而"`matchesSite` 的七个浮点精确相等"⇒ **与 §351 的"两边解析同一个字符串 ⇒ float32 逐位相同"**同族（**第三次"浮点 `==` 是安全的因为同源"）。**

### 4.3 而主 `if` 的**十三项**

```php
if (!clients_.gameStateConfigured() || matchGameType_ != "sd" ||
    status_.worldSpawnConfigured || sites.size() != 2 ||
    siteRuntime.size() != 2 || !validVolume(pickupTrigger) ||
    sites[0].label != "_a" || sites[1].label != "_b" ||
    !matchesSite(sites[0], siteRuntime[0]) ||
    !matchesSite(sites[1], siteRuntime[1]) ||
    !validVolume(siteRuntime[0].plantTrigger) ||
    !validVolume(siteRuntime[0].defuseTrigger) ||
    !validVolume(siteRuntime[1].plantTrigger) ||
    !validVolume(siteRuntime[1].defuseTrigger) ||
    sites[0].target.empty() || sites[1].target.empty() ||
    !finiteOrigin(sites[0]) || !finiteOrigin(sites[1]))
    return false;
```

**⇒ 十八项（含两个 `matchesSite` 各 7 项）。**

**✅ 与 §391 的"`sites.size() != 2`"**完全闭合 ✓

**⇒ **第二次确认"恰好两个站点"。**

**⚠ 而"`sites[0].label != "_a"` 与 `sites[1].label != "_b"`"⇒ **一个【顺序】要求**。**

**✅ 与 §390 的"`siteLabel != "_a" && != "_b"`"**配合（**一次确认）。**

### 4.4 而**失败时的五项回滚**

```cpp
if (!useObjects_.configure(useDefinitions)) {
    sdBombStatus_ = {};
    sdBombPickupTrigger_.reset();
    sdBombPickupHomeOrigin_ = {};
    sdBombSiteRuntime_.clear();
    return false;
}
```

**⇒ 三层**：

```text
1. **四个字段先写**
2. ⇒ **然后 `useObjects_.configure`**
3. ⇒ **失败 ⇒ 【清四个】**
```

**✅ 与 §349 的"staged-then-commit"**第十三次。**

**⚠ 而"先写后回滚"⇒ **不是"先暂存后提交"**。**

**⇒ 一个**不同的顺序**（但结果等价）。**

## 五、**`configureWorldSpawn` 的"null 触发器表"**（本组第四重要）

### 5.1 那段

```php
// Null on a map with no extracted trigger table. driveCursorHints returns
// immediately on null rather than falling back to guessed geometry.
mapTriggers_ = SV_MapTriggerTable(mapName);
```

### 5.2 五层

```text
1. **在一张没有已提取触发器表的地图上为【null】**
2. ⇒ **`driveCursorHints` 在 null 上【立即返回】**
3. ⇒ **而不是回退到【猜的几何】**
4. ⇒ **所以是一个显式的"没有就不做"**
5. ⇒ **而日志说 `map triggers map=<name> triggers=0`**
```

**✅ 与 §355 的"没有目标就站着不动"**同族（**第十九次"不要猜"）。**

**⚠ 而"`triggers=0`"⇒ **一个显式的零**。**

**✅ 与 §388 的"零也命名"**同族（**第三次）。**

### 5.3 而**九个 hint 表的清空**

```text
hintStringSlots_        / cursorHintTrigger_    / lootHintTarget_
lootActivateHeld_       / mapTriggerHintTarget_ / barrierRepairHintTarget_
zmUseActivateHeld_      / factoryAmmoHolds_     / zmRepairReadyTime_
openedMapTriggers_      / zmPowerOn_
```

**⇒ 十一项。**

**✅ 与 §394 的"`configureGameState` 里同样的十一项"**完全一致 ✓

**⇒ **第二次确认那十一个 hint 表。**

## 六、**`configureWorldSpawn` 的两个重载**

```text
重载 1：origin / angles / brushModels / scriptModels / damageOwners
        ⇒ 构造一个 `spawnPoints` 数组然后转发
重载 2：spawnPoints / ... / waitingForLoadoutPoint / mapName / gameType / logicalMapEntities
        ⇒ 真正实现
```

**⇒ 三层**：

```text
1. **重载 1 只是一个【便捷包装】**
2. ⇒ **它构造一个单元素的 `spawnPoints`**
3. ⇒ **然后转发**
```

**✅ 与 §349 的"`configureSpawn` 转发到 `configureSpawnPoints`"**完全同构 ✓

**⇒ **第二次确认那个模式。**

### 6.1 而重载 2 的**九个参数**

```text
① spawnPoints
② brushModels
③ scriptModels
④ scriptModelDamageOwners
⑤ waitingForLoadoutPoint   （optional）
⑥ mapName
⑦ gameType
⑧ logicalMapEntities
```

**⇒ 八项（`origin`/`angles` 在重载 1）。**

**✅ 与 §350 的"`configureSpawnAndBrushModelEntities` 的九个参数"**完全一致 ✓

**⇒ **第二次确认。**

## 七、**`configureUavRadar` 的 `3'600'000`**

```cpp
if (durationMilliseconds > 3'600'000) return false;
```

**⇒ 三层**：

```text
1. **上限 `3,600,000ms` = 1 小时**
2. ⇒ **所以一个 UAV 最多 1 小时**
3. ⇒ **一个宽松的上界**
```

**⚠ 而 `1 小时`⇒ **比 §391 的"`30'000ms` 超时"**长 120 倍。**

**✅ 一个**不同的量纲**（UAV 时长 vs 客户端超时）。

## 八、`configureSdBombPresentation` 的五项

```php
if (!status_.worldSpawnConfigured || !sdBombStatus_.configured ||
    sdBombStatus_.phase != SvSdBombPhase::Inactive ||
    sdBombVisualHandle_)
    return false;
const auto handle = world_.findScriptModel(visualDefinition);
if (!handle || !world_.setScriptModelPresentation(*handle, presentationModelIndex,
        presentationModelName, visualDefinition.origin, visualDefinition.angles, false))
    return false;
sdBombVisualHandle_ = *handle;
```

### 8.1 六层

```text
1. **四项前置**：`worldSpawnConfigured` / `sdBombStatus_.configured` / `phase == Inactive` / **视觉句柄未设**
2. ⇒ **`findScriptModel(definition)`** ⇒ 按精确属性找（§388）
3. ⇒ **`setScriptModelPresentation(..., active = false)`** ⇒ **不激活**
4. ⇒ **所以炸弹先【不可见】**（等回合开始）
5. ⇒ **记三个字段**（句柄 / home origin / angles）
```

**✅ 与 §386 的"`findScriptModel` 的九项精确匹配"**完全闭合 ✓

**⇒ **第二次确认那个查找。**

**⚠ 而"`active = false`"⇒ **一个"先存在后激活"的两阶段**。**

**✅ 与 §350 的"两行可见性判据"**同族（**第五次）。**

## 九、关键结论

1. **⭐⭐ "四个注入物齐了才算可玩"`** —— `setGameplayAuthorityReady` 的五次联动（四次在 `setSharedPmoveRunner` / `setWeaponMovementRunner` / `setPlayerStateToEntityStateConverter` / `setClientEventsHandler`），而**这四个恰好是 `sharedPmoveAvailable()` 的四项** ⇒ **一对一闭合**。
2. **十三个不带联动的注入**（`DeathAnimationRunner` / `AltFireResolver` / 四个 trace / `TriggerContactRunner` / `MirrorSynchronizer`）—— **每一个都是可选增强**。
3. **⚠ `setSpawnAnimationRunner` 是唯一【不持锁】的 setter** —— 而其它十七个都有 `const std::lock_guard lock(mutex_);`，**注释没有解释**，可能是一个遗漏。
4. **`setLoadoutProvider` 换 provider 时清 `resolvedLoadouts_`** —— 一个正确的缓存失效，而与 §381 的"`effectivePlayerAbilities` 每次计算"**两种策略并存**（武器解析昂贵、技能叠加便宜）。
5. **⭐⭐ SD 的四个 `use` 定义**：`ownerTeam = Sc` 而**下包 `allowedRelation = Enemy`（Tf）/ 拆包 `Friendly`（Sc）** ⇒ **一个"关系而非身份"的权限模型**。
6. **`requiresKeyObject` 只有下包有**（炸弹本体是一个 key object）。
7. **⭐ `validVolume` 的 `collision.clipHandle == objectId`** —— 一个**冗余但有意的一致性检查**（第二次"两个 id 必须相等"）。
8. **`matchesSite` 的七个浮点精确相等** —— 第三次"浮点 `==` 是安全的因为同源"。
9. **主 `if` 的十八项**（含两个 `matchesSite` 各 7 项），而 **`sites[0].label == "_a"` / `sites[1].label == "_b"` 是一个【顺序】要求**。
10. **失败时的五项回滚**（先写四个字段后用 `useObjects_.configure` 验证）—— 第十三次事务性。
11. **⭐ "在一张没有已提取触发器表的地图上为 null ⇒ `driveCursorHints` 在 null 上【立即返回】而不是回退到【猜的几何】"`** —— 第十九次"不要猜"。
12. **十一个 `hint` 表的清空**（第二次确认，与 §394 的 `configureGameState` 完全一致）。
13. **`configureWorldSpawn` 的两个重载**（便捷包装转发）—— 第二次确认那个模式，而**重载 2 的八个参数与 §350 的九个一致**。
14. **`configureUavRadar` 的 `3'600'000ms`（1 小时）上限** —— 比 `30'000ms` 的客户端超时长 120 倍。
15. **`configureSdBombPresentation` 的"先存在后激活"**（`active = false` 然后等回合开始）。

## 十、未闭合点

- `setSpawnAnimationRunner` 为何不持锁。
- `SdBombRules::plantMilliseconds` / `defuseMilliseconds` 的值。
- `SvTriggerVolume::objectId` 与 `clipHandle` 的分配关系。
- `useObjects_.configure` 的实现。
- `3'600'000ms` 的来源。
- `sv_main_mp.cpp` 2400 行之后未读取。
