# 352 · **"把一件枪械放进冻结装备里否则它在每个重要的地方都被拒"** —— `a <n>` 与事件 35 的 300ms 配对、SD 死亡保持、`spawnScriptModel` 的两行可见性判据

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 12400–12800 行。

## 二、**`givePlayerWeapon` 的四层**（本组最重要的一段）

### 2.1 前置检查

```cpp
if (clientNum >= weaponGrants_.size() || !weaponAssetIndex ||
    weaponAssetIndex >= WeaponConfigStringCount || !weaponDefinitionResolver_)
{
    return false;
}
```

**⇒ 四项**：

```text
① clientNum 在范围内
② weaponAssetIndex 非零（0 = 无武器）
③ weaponAssetIndex < WeaponConfigStringCount（1700，§239）
④ 解析器已注入
```

**✅ 与 §239 的 `WeaponConfigStringCount = 1700`**完全一致 ✓**

### 2.2 而**"信任调用方要的索引而不是定义回显的"**

```cpp
// Trust the index the caller asked for over whatever the definition echoes
// back, so a resolver that fills the rest of the struct but leaves this field
// alone cannot silently grant a different gun.
resolved.weaponAssetIndex = weaponAssetIndex;
```

**⇒ 四层**：

```text
1. **信任调用方要的索引而不是定义回显的任何东西**
2. ⇒ **所以一个填了结构其余部分而【这个字段留着没动】的解析器**
3. ⇒ **不能静默地授予一把不同的枪**
4. ⇒ 所以强制覆盖
```

**✅ 与 §346 的"`psDomainValue` 用名字 + 值"**同族 —— **防御一个不完整的实现**。

### 2.3 ⭐ **"并且把它放进冻结装备里"**（本组核心）

```php
// AND PUT IT IN THE FROZEN LOADOUT, or the weapon is refused everywhere that
// matters. NativeWeaponMovementBindings is explicit -- "nonzero weapons remain
// constrained to the frozen loadout" -- and it looks the CURRENT weapon up with
// SV_FindResolvedWeapon, returning nullopt when it is not the primary or the
// secondary. That nullopt is WeaponMovementRejected, which kills the whole
// client think for the frame; the firing path (SV_HandleClientEventsDetailed)
// takes the same resolvedLoadout and refuses an unknown weapon the same way,
// which is why a granted gun could not shoot.
//
// The SECONDARY slot takes the grant, not the primary. Primary is what
// equipResolvedLoadout would hand back if anything ever re-equips the class,
// and overwriting it would make an unarmed dmz spawn silently inherit the last
// looted gun. Secondary is unused on an unarmed spawn.
// THE LOADOUT IS NOT EDITED HERE. The grant is recorded above and applied as
// a per-frame HOLD on the think's candidate copy -- see the weapon-grant hold
// in clientThink. A single write into the stored SvResolvedLoadout was the
// first version and it was wrong twice over: it made a looted gun the player's
// permanent secondary, and it fought sect.190's rule that the frozen loadout is
// not where a weapon outside the class belongs.
```

### 2.4 十七层

```text
1. **并且把它放进【冻结装备】里，否则这把武器在每一个重要的地方都被拒**
2. ⇒ `NativeWeaponMovementBindings` 是显式的 —— **"非零武器保持被约束到冻结装备"**
3. ⇒ **而它用 `SV_FindResolvedWeapon` 查【当前】武器**
4. ⇒ **当它不是主武器或副武器时返回 `nullopt`**
5. ⇒ **那个 `nullopt` 是 `WeaponMovementRejected`**
6. ⇒ **它杀死那一帧的【整个客户端 think】**
7. ⇒ **开火路径（`SV_HandleClientEventsDetailed`）取同一个 `resolvedLoadout`**
8. ⇒ **并以同样方式拒绝一个未知武器**
9. ⇒ **那就是为什么一把被授予的枪【不能开火】**
10. ⇒ **【副】槽接收这个授予，不是主槽**
11. ⇒ **主槽是 `equipResolvedLoadout` 若有什么重新装备职业时会交回来的**
12. ⇒ **而覆盖它会让一个无武装的 dmz 出生静默继承最后捡到的枪**
13. ⇒ **副槽在一个无武装出生上是不用的**
14. ⇒ **装备【不在这里被编辑】**
15. ⇒ **授予在上面被记录而作为 think 的候选副本上的一个【每帧保持】被施加** —— 见 clientThink 的 weapon-grant hold
16. ⇒ **一次写进存储的 `SvResolvedLoadout` 是第一版而它【错了两次】**：
     · **它让一把捡来的枪成为玩家的永久副武器**
     · **而它与第 190 节的规则冲突：冻结装备不是一个职业外的武器该在的地方**
```

### 2.5 **"杀死那一帧的整个客户端 think"**

**✅ 与 §349 的 `SvClientThinkFailureStage::WeaponMovementRejected`**完全一致 ✓**

**⇒ 而 §349 说"原生 pmove 占四十个阶段里的十七个"。**

**⚠ 而这里 `WeaponMovementRejected` 是**武器移动**而不是 pmove。**

**⇒ 所以是**另一个失败源**。**

**✅ 现在知道它的**触发条件**：`SV_FindResolvedWeapon` 返回 nullopt。**

### 2.6 而**"错了两次"的三层**

```text
① 让捡来的枪成为永久副武器
② 与"冻结装备不放职业外武器"冲突
```

**✅ 与 §343 的"两个极端都错"**同族（**第二次"两个方向都试过"**）。**

**⚠ 而这里是**同一个实现有两个独立的错**（不是两个极端）。**

**✅ 一个**更细的分类**。**

### 2.7 而**"每帧保持" vs "写一次"**

**⇒ 三层**：

```text
写一次（第一版）  ⇒ 永久副作用（两个方向都错）
每帧保持（终版）  ⇒ 只在当前帧有效
```

**✅ 与 §349 的"投递状态只在整快照成功后提交"**同族（**第二次"事务性 vs 永久"**）。**

**⇒ **一个**极重要的设计模式**：**
```
把"临时覆盖"实现为"每帧重新施加"而不是"写进持久状态"
```

**✅ **本文件第三次出现该模式**（§345 的 `constBaselineStorage`、§349 的 `commandDelivery`、这里）。**

## 三、**`a <n>` 与事件 35 的 300ms 配对**（本组第二重要）

### 3.1 那段

```php
// AND TELL THE CLIENT, which is the half that actually puts a gun on the
// screen. Everything above only makes the SERVER agree; forcing the playerstate
// alone was measured to change nothing the player could see, because the weapon
// is never in the snapshot.
auto announced = reliableCommandSender_(clientNum, "a " + std::to_string(weaponAssetIndex));
OlMod::RuntimeLog::write(..., "weapon ANNOUNCE a " + ... + (announced ? " queued" : " REJECTED") : " NO SENDER");
// AND FIRE THE ACQUIRE EVENT, which is the half that tells the client to take
// the weapon rather than merely draw it. MEASURED in
// C-2021-7-25[22-23-22]dmz: every `a <n>` is followed about 300 ms later by a
// playerState event 35 carrying the same weapon number -- `a 1184` then
// (35, 1184), `a 1193` then (35, 1193), `a 1232` then (35, 1232), all seven --
// and 35 fires again on its own every time the player swaps guns.
//
// THE NUMBER IS A DIAL, because the id is measured from ONE capture and its
// meaning is inferred. OLMOD_DMZ_PICKUP_EVENT=0 turns it off; any other number
// sends that id instead, so the next candidate costs a restart rather than a
// rebuild.
```

### 3.2 十三层

```text
1. **并且告诉客户端，那是真正把一把枪放到屏幕上的那一半**
2. ⇒ **上面的一切只让【服务器】同意**
3. ⇒ **单独强制 playerState 被测量为【什么也没改变玩家能看见的】**
4. ⇒ **因为武器从不在快照里**
5. ⇒ **并且发【获取事件】，那是告诉客户端【拿】这把枪而不是仅仅【画】它的那一半**
6. ⇒ **在 `C-2021-7-25[22-23-22]dmz` 里测量**：
     · **每一个 `a <n>` 都在约 300ms 后跟着一个携带同一武器号的 playerState 事件 35**
     · `a 1184` 然后 `(35, 1184)`
     · `a 1193` 然后 `(35, 1193)`
     · `a 1232` 然后 `(35, 1232)`
     · **全部七个**
7. ⇒ **而 35 在玩家每次换枪时自己又发一次**
8. ⇒ **那个号是一个【旋钮】，因为 id 是从【一个】捕获里测的而它的意义是推断的**
9. ⇒ **`OLMOD_DMZ_PICKUP_EVENT=0` 关掉它；任何其它号发那个 id 取而代之**
10. ⇒ **所以下一个候选值花一次重启而不是一次重编**
```

### 3.3 **"武器从不在快照里"**

**✅ 与 §345 的"一个活玩家的 `modelIndex` 被断言一次然后静默六千个快照"**同族。**

**⇒ 三层**：

```text
1. **武器不走快照**（走 `a <n>` 可靠命令）
2. ⇒ **所以强制 playerState 的武器字段【什么也不改变】**
3. ⇒ **必须走 `a`**
```

**✅ 与 §342 的"`-94` 事件编解码器"配合 —— **武器通过事件而非字段**。**

**⚠ 而 §345 的 `packEntityWeapon` 打包两个武器索引 ⇒ 所以**实体**有武器但**玩家**没有？**

**⇒ 可能 `entityState` 的 weapons 是**别的实体**（导弹/物品）的。**

**✅ 一个**合理的区分**。**

### 3.4 而**"300ms"**

**⇒ 三层**：

```text
1. `a <n>` 之后约 300ms
2. ⇒ **跟一个 `(35, <same n>)`**
3. ⇒ **所以是【两个独立的命令】而客户端需要两者**
```

**✅ 与 §347 的"`0x19..0x1E` 换弹"**不同**（那是事件环）。**

**⇒ 而这是一个**playerState 事件**（`SV_AppendNativePlayerStatePredictableEvent`）。**

**⚠ 所以**三个不同的"武器出现"机制**：**

```text
`a <n>`           可靠命令（客户端拿枪）
事件 35           获取事件（客户端"接受"）
playerState 字段  服务端的认知
```

**✅ **三者都需要。**

### 3.5 而**"那个号是一个旋钮"**

**✅ 与 §349 的"`OLMOD_PLAYER_VOCALS=0`"、§350 的"`OLMOD_FACTORY_POWER_MOTION=1`"**同族。**

**⇒ **环境变量作为旋钮** 是一个**反复的模式**。**

**⇒ 而理由是：**

```text
"id 是从【一个】捕获里测的而它的意义是推断的"
⇒ 所以下一个候选值花一次【重启】而不是一次【重编】
```

**✅ 与 §343 的"更好的是省略而不是错"、§350 的"`PublishScriptModelsOnRetailNumbers`"配合。**

**⇒ **一个明确的"这是推断值"标记**。**

### 3.6 而**"全部七个"**

**⇒ 三层**：

```text
1. 七个样本
2. ⇒ **每个 `a <n>` 都有一个 `(35, n)`**
3. ⇒ **所以配对是 7/7**
```

**✅ 一个**小样本而完全一致**的测量。**

**⚠ 而注释**承认**"从一个捕获" ⇒ 所以**样本量小**。**

**✅ 与 §345 的"从一个不可能包含一个的样本得出结论"**互补（**这里是"样本小但一致"**）。**

## 四、**SD 死亡保持**（本组第三重要）

```php
// OLMOD(sd-round-death-hold): 经典爆破 is the one round-based mode this
// server boots (the live boot line names it: "map spawn classes
// mp_crash_tropical sd:"), and its respawn belongs to the round, not to
// the death animation. Measured before this gate, on the opposing bots:
//     respawn client=6 via=timed msSinceDeath=1700 deathAnimMs=1616
// -- a kill, then the same bot standing back up 1.7 s later, which the
// operator reported as bots endlessly re-spawning. The round path is
// untouched.
roundBasedDeathHold_ = (gameType == "sd");
```

### 4.1 八层

```text
1. **经典爆破是这个服务器引导的【唯一】回合制模式**
2. ⇒ **（活动引导行点名它：`map spawn classes mp_crash_tropical sd:`）**
3. ⇒ **而它的重生属于【回合】，不属于死亡动画**
4. ⇒ **在这个门控之前测量，在对面的 bot 上**：
     · `respawn client=6 via=timed msSinceDeath=1700 deathAnimMs=1616`
5. ⇒ **一次击杀，然后同一个 bot 在 1.7 秒后站起来**
6. ⇒ **而操作员报告为"bot 无尽地重生"**
7. ⇒ **回合路径不动**
```

### 4.2 而 **`msSinceDeath=1700` 而 `deathAnimMs=1616`**

**⇒ 三层**：

```text
1. 死亡动画 1616ms
2. ⇒ **而 1700ms 后重生**
3. ⇒ **所以重生死于动画结束（84ms 之后）**
```

**✅ 一个**极精确的数字对照**。**

**⇒ 所以"1.7秒后站起来"是**动画刚结束**。**

**⚠ 而玩家看到的是**"bot 无尽重生"** —— 因为 1.7 秒的死亡太短暂。**

**✅ 与 §349 的"玩家的判决"**同族（**第三次以玩家观感为终审**）。**

### 4.3 而**"回合路径不动"**

**⇒ 三层**：

```text
1. 只改【死亡动画武装的重生】
2. ⇒ **不改 `beginNextRound() ++spawnSequence`**
3. ⇒ **所以回合逻辑完整**
```

**✅ 与 §346 的"两处 allowlist 独立"**同族（**改动范围精确**）。**

### 4.4 而**三个 OLMOD 环境变量在同一段**

```text
OLMOD_FACTORY_POWER_MOTION      == "1" 且 zm_factory_sh + zm
OLMOD_ZM_COOP_REVIVE            == "1" 且 zm_factory_sh + zm
OLMOD_ZM_DEBUG_GODMODE          == "1" 且 factoryArrivalMap_
OLMOD_FACTORY_PERK_MACHINES     == "1" 且 zm_factory_sh + zm
OLMOD_FACTORY_INTERACTABLES     == "1" 且 zm_factory_sh + zm
```

**⇒ 五个（不是三个）。**

**✅ 而全部要求**特定的地图 + 模式组合**。**

**⇒ **"opt-in 且精确的 Factory 地图/模式准入"**（注释原话）。**

**✅ 一个**双重门控**：环境变量 + 地图/模式。**

### 4.5 而 **`roundBasedDeathHold_` 不需要地图**

**⇒ 三层**：

```text
1. `roundBasedDeathHold_ = (gameType == "sd")`
2. ⇒ **只看模式，不看地图**
3. ⇒ **因为 sd 是"唯一的回合制模式"**
```

**✅ 与其它五个的门控**不同**（更简单）。**

**⇒ 而因为它是一个**修正**而不是一个**特性**。**

## 五、**`configureSpawnAndBrushModelEntities` 的失败回滚**（本组第四重要）

```cpp
rebuildCollisionView();
if ((nativeEntityMirrorSynchronizer_ && !nativeEntityMirrorSynchronized_) ||
    !configureSpawn(origin, angles))
{
    if (nativeEntityMirrorSynchronizer_)
        static_cast<void>(nativeEntityMirrorSynchronizer_(
            SvNativeEntityMirrorPhase::Collision, {}, {}, snapshot_.serverTime));
    nativeEntityMirrorSynchronized_ = false;
    spawnPoints_.clear();
    entityPool_.reset();
    entities_.clear();
    factoryDoorMotions_.clear();
    missiles_.clear();
    factorySpecialWeapons_.clear(); factorySpecialCombat_.clear(); factorySpecialStatuses_.clear();
    multiplayerOffhandWeapons_.clear();
    factoryViewFxRecipients_.clear(); factoryViewFxNext_.clear();
    factoryTrapPresentation_.clear(); factoryTrapFx_ = {};
    scavengerBags_.clear();
    entityDamageStates_.clear();
    entityDamageHandlers_.clear();
    collisionEntities_.clear();
    playerMovementCollisionEntities_.clear();
    return false;
}
```

### 5.1 而**两个失败条件**

```text
① 有镜像同步器而【未同步】   ⇒ 失败
② `configureSpawn(origin, angles)` 失败 ⇒ 失败
```

**⚠ ① 是**在已经赋值之后**检查 ⇒ 所以它实际上是**验证前一步**。**

**⇒ 而 `nativeEntityMirrorSynchronized_` 在**同一个函数里没有被设**（除了在失败路径清它）。**

**⚠ 所以**这个检查可能永远为假**（或者由 `rebuildCollisionView()` 设置）。**

**✅ 一个**需要核对的推理**。**

### 5.2 而**回滚清十五项**

**⇒ 而 `reset()` 清六十八项。**

**⇒ 所以回滚是 `reset()` 的一个**子集**（但多清 `spawnPoints_` 与 `collisionEntities_`）。**

**⚠ 两处**不完全一致**。**

**✅ 与 §349 的"`reset()` 六十八项"配合。**

### 5.3 而**"事务性赋值"的模式**

```cpp
logicalMapEntities_ = std::move(stagedLogicalMapEntities);
entityDamageStates_ = std::move(stagedDamageStates);
entityDamageHandlers_ = std::move(stagedDamageHandlers);
constBaselineNumbering_ = everyBrushModelOnRetailNumber;
...
entityPool_ = std::move(stagedPool);
entities_ = std::move(stagedEntities);
```

**⇒ 三层**：

```text
1. **所有工作在一个 `stagedXxx` 局部里做完**
2. ⇒ **验证通过后一次 move 进成员**
3. ⇒ **失败则成员未被碰过**
```

**✅ 与 §350 的 `stagedPool`/`stagedEntities` 配合。**

**⇒ **本文件的核心模式：staged-then-commit。**

**✅ 与 §349 的"事务性投递"、§352 三的"每帧保持"**同族。**

**⇒ **第四次"事务性"**。**

### 5.4 ⚠ 而**在一段里 `logicalMapEntities_` 与 `entityPool_` 之间还有赋值**

```cpp
logicalMapEntities_ = std::move(stagedLogicalMapEntities);
logicalMapTriggerTable_ = SV_MapTriggerTable(mapName);
entityDamageStates_ = std::move(stagedDamageStates);
entityDamageHandlers_ = std::move(stagedDamageHandlers);
constBaselineNumbering_ = everyBrushModelOnRetailNumber;
constBaselineScriptModels_ = scriptModelsOnRetailNumbers;
constBaselineTable_ = everyBrushModelOnRetailNumber ? constBaselines : nullptr;
rebuildCollisionView();
// ← 这里检查
if (...) { /* 回滚 */ return false; }
```

**⇒ 而 `constBaselineTable_` 在检查**之前**被赋值。**

**⚠ 而回滚**不清它**。**

**⇒ 所以失败后 `constBaselineTable_` 可能是**非空的而 `entities_` 是空的**。**

**⚠ 一处**真实的不一致**（但可能无害 —— 没有实体就没人用它）。**

**✅ 一个**值得记下的细节**。**

### 5.5 而 `rebuildCollisionView()` 在**检查之前**

**⇒ 三层**：

```text
1. 重建碰撞视图
2. ⇒ **然后才检查**
3. ⇒ **失败则清碰撞集**
```

**✅ 与回滚里的 `collisionEntities_.clear()` 配合 ✓**

## 六、**`configureBrushModelEntities` 的"两个入口必须一致"**

```php
// ET_SCRIPTMOVER, matching configureSpawnAndBrushModelEntities --
// the two entry points must agree or a gametype-spawned brush model
// would be the only invisible one.
entity.networkState.eType = EntityTypeScriptMover;
```

### 6.1 四层

```text
1. **`ET_SCRIPTMOVER`，与 `configureSpawnAndBrushModelEntities` 一致**
2. ⇒ **两个入口【必须】一致**
3. ⇒ **否则一个由游戏类型生成的画笔模型会是【唯一不可见的那个】**
4. ⇒ 所以显式对齐
```

**✅ 与 §350 的"`ET_SCRIPTMOVER` 是唯一到达 `R_AddBrushModelToScene` 的路径"**完全一致 ✓**

**⚠ 所以**两个入口 + 一个约束**。**

**⇒ **第三次"三处同型"**（§344 的 allowlist、§346 的三处 allowlist、这里两个入口）。**

## 七、`spawnScriptModel` 的**两行可见性判据**（本组第五重要）

### 7.1 那段

```php
// THE TWO LINES THAT DECIDE WHETHER ANY OF THIS IS VISIBLE. The publication
// gate is `if (!entity.gameplayActive) return false;`, and mapModeEligible is
// what setScriptModelPresentation later checks before it will activate this
// entity -- without it every subsequent setmodelat on this loot would fail the
// same way the original spawn did.
entity.gameplayActive = true;
entity.mapModeEligible = true;
```

### 7.2 六层

```text
1. **决定这一切是否可见的那两行**
2. ⇒ **发布门控是 `if (!entity.gameplayActive) return false;`**
3. ⇒ **而 `mapModeEligible` 是 `setScriptModelPresentation` 后来检查的**
4. ⇒ **在它会激活这个实体之前**
5. ⇒ **没有它，每一个后续的 `setmodelat` 在这个战利品上都会以同样的方式失败**
6. ⇒ **就像原始生成所做的那样**
```

**✅ 与 §350 的 `validScriptModel` 的 `(mapModeEligible || !gameplayActive)`**完全一致 ✓**

**⇒ **两个标志必须同时为真**才能可见。**

**⚠ 而 `validScriptModel` 允许 `!gameplayActive`（纯装饰）。**

**⇒ 而 `spawnScriptModel` 两者都设真。**

**✅ **两个不同的用途**（验证 vs 生成）。**

### 7.3 而**"每一个后续的 `setmodelat` 都会以同样的方式失败"**

**⇒ 三层**：

```text
1. 生成失败 ⇒ 无实体
2. ⇒ **而后续的 `setmodelat` 也失败**
3. ⇒ **所以脚本会以为战利品没了**
```

**✅ 与 §350 的"接收了、存储了、而从未被画"**不同** —— 这里是**根本没有实体。****

**⚠ 所以**两级失败**（无实体 vs 有实体但不可见）。**

### 7.4 而**参数筛查在占槽之前**

```php
// The same argument screen setScriptModelPresentation applies, run BEFORE a
// slot is taken rather than after: a rejected spawn must not cost an entity.
// `*` prefixes name a brush model, which is not an xModel and cannot be
// attached this way.
if (!modelIndex || modelIndex >= ModelConfigStringCount ||
    modelName.empty() || modelName.front() == '*' ||
    modelName.find('\0') != std::string_view::npos ||
    !finiteVector(origin) || !finiteVector(angles)) return std::nullopt;
const auto handle = spawnEntity();
```

**⇒ 五层**：

```text
1. **同一个参数筛查 `setScriptModelPresentation` 施加的**
2. ⇒ **在占一个槽【之前】运行而不是之后**
3. ⇒ **一个被拒的生成绝不能花掉一个实体**
4. ⇒ **`*` 前缀命名一个画笔模型**
5. ⇒ **而它不是 xModel 而不能这样被附着**
```

**✅ 一个**正确的顺序**（验证在副作用之前）。**

**⚠ 与 §350 的 `validScriptModel` **同样的九项**（少一项 `scale`）。**

**⇒ 所以**两个函数共享同一套筛查**（代码重复）。**

**✅ 与 §337 的"两个几乎相同的函数"**第三次。**

## 八、`setZmNavGraph` 的**连通分量标注**

```cpp
// LABEL EVERY NODE WITH ITS CONNECTED COMPONENT, once, here.
//
// Weak topology membership only: A* additionally enforces barrier direction
// and live blocked edges. Membership does not prove a route. The largest
// component is taken as the map's main body: on factory that is 837 of 1100
// nodes and it is where the players' own nearest node lands.
const auto nodeCount = zmNavGraph_.nodes.size();
zmNavComponent_.assign(nodeCount, 0u);
zmNavMainComponent_ = 0u;
if (nodeCount == 0) return;
std::vector<bool> seen(nodeCount, false);
std::vector<std::uint16_t> stack;
std::uint16_t component = 0;
std::size_t largest = 0;
for (start = 0; start < nodeCount; ++start) { ... }
```

### 8.1 七层

```text
1. **给每个节点标注它的连通分量，一次，在这里**
2. ⇒ **只有【弱拓扑】成员关系**
3. ⇒ **A* 额外强制屏障方向与实时阻塞边**
4. ⇒ **成员关系【不证明】一条路线**
5. ⇒ **最大分量被取为地图的主体**
6. ⇒ **在 factory 上那是 1100 个节点里的 837 个**
7. ⇒ **而它是玩家自己的最近节点落的地方**
```

**✅ 与 §347 的"这是线半而对另一半盲"**同族（**第四次"声明仪器的边界"**）。**

**⇒ "成员关系不证明一条路线"是一个**极精确的限定**。**

### 8.2 而 **837/1100 = 76%**

**⇒ 三层**：

```text
1. 主分量 837 个节点
2. ⇒ **总共 1100**
3. ⇒ **所以 263 个节点不在主分量上**
```

**⚠ 而"玩家自己的最近节点落在主分量"⇒ 所以**263 个是装饰/孤立**。**

**✅ 与 §340 的"缺席是证据"配合。**

### 8.3 而**迭代式 DFS（`std::vector<uint16_t> stack`）**

**⇒ 三层**：

```text
1. **显式栈而不是递归**
2. ⇒ **避免 1100 层递归**
3. ⇒ **`uint16_t` 分量号（65535 上限）**
```

**✅ 一个**稳健的实现选择**。**

## 九、关键结论

1. **`givePlayerWeapon` 的四项前置**（clientNum / 非零索引 / `< 1700` / 解析器）。
2. **"信任调用方要的索引而不是定义回显的"** —— 防御一个不完整的解析器。
3. **⭐ "把它放进冻结装备里否则它在每个重要的地方都被拒"** —— `SV_FindResolvedWeapon` 返回 nullopt ⇒ `WeaponMovementRejected` ⇒ **杀死整帧的 client think**。
4. **而"被授予的枪不能开火"是同一原因**（`SV_HandleClientEventsDetailed` 取同一个 `resolvedLoadout`）。
5. **副槽接收授予而非主槽**（主槽会被 `equipResolvedLoadout` 交回，覆盖它会让无武装出生继承上一把捡来的枪）。
6. **⭐ "装备不在这里被编辑"** —— 实现为 think 候选副本上的**每帧保持**。
7. **第一版"写一次"错了两次**（永久副作用 + 与第 190 节冲突）。
8. **⭐ "每帧重新施加临时覆盖而不写进持久状态"** —— **本文件第三次该模式**。
9. **⭐ "武器从不在快照里"** ⇒ 强制 playerState 什么也不改变 ⇒ 必须走 `a <n>`。
10. **`a <n>` 与 `(35, <same n>)` 的 300ms 配对，7/7 一致**。
11. **三个不同的"武器出现"机制**（`a` 可靠命令 / 事件 35 / playerState 字段）。
12. **"那个号是一个旋钮"** —— 因为 id 从**一个**捕获测得而意义是推断的。
13. **SD 死亡保持：`msSinceDeath=1700` vs `deathAnimMs=1616`** ⇒ 重生死于动画结束 84ms 后 ⇒ 玩家报"bot 无尽重生"。
14. **"只改死亡动画武装的重生，回合路径不动"** —— 改动范围精确。
15. **五个 OLMOD 环境变量全部要求特定地图+模式**（双重门控），而 `roundBasedDeathHold_` 只看模式（因为它是修正不是特性）。
16. **`configureSpawnAndBrushModelEntities` 的失败回滚清十五项**，而 `reset()` 清六十八项 —— 回滚是子集。
17. **⭐ staged-then-commit 是本文件的核心模式**（`stagedPool`/`stagedEntities`/`stagedDamageStates`）—— **第四次"事务性"**。
18. **⚠ 回滚不清 `constBaselineTable_` 而它在检查前已赋值** —— 一处真实的不一致（可能无害）。
19. **`configureBrushModelEntities` 与 `configureSpawnAndBrushModelEntities` 必须都设 `ET_SCRIPTMOVER`** —— 否则游戏类型生成的画笔模型会成为唯一不可见的。
20. **⭐ `spawnScriptModel` 的"两行可见性判据"**（`gameplayActive = true` + `mapModeEligible = true`）。
21. **"一个被拒的生成绝不能花掉一个实体"** —— 筛查在占槽之前。
22. **`setZmNavGraph` 的连通分量标注：1100 个节点里主分量 837 个（76%）**。
23. **"弱拓扑成员关系；成员关系不证明一条路线"** —— 第四次声明仪器边界。
24. **迭代式 DFS 用 `uint16_t` 分量号** —— 稳健选择。

## 十、未闭合点

- `nativeEntityMirrorSynchronized_` 由谁设置。
- 回滚不清 `constBaselineTable_` 的后果。
- `WeaponConfigStringCount = 1700` 与 `weaponAssetIndex` 的关系（是否同名空间）。
- 事件 35 的确切语义（"获取"？"拾取"？）。
- `zmNavMainComponent_` 在 A* 里的使用。
- `sv_snapshot_mp.cpp` 12800 行之后未读取（27,016 行，进度 47%）。
