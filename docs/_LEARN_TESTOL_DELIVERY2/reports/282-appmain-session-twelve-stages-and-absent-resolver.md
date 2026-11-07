# 282 · 会话消费的**十二个阶段**、"同地图代际复用"、`CharacterSelectionResolve` 在 OLfinal 上不存在

## 一、范围

本报告学习 `Appmain.cpp` 2575–2795 行。

## 二、**"同地图代际复用"**（本组最重要的一段）

```php
// matchmaking request. Re-entering the retail zone loader for a
// second request on the already resident Wetwork map faults inside
// out.exe. Reuse the loaded generation until the requested level
// actually changes.
const auto sameMapGeneration = DedicatedMapGeneration &&
    DedicatedMapGeneration->mapName == session.booking.mapName &&
    DedicatedMapGeneration->gameType == session.booking.gameType;
if (!sameMapGeneration)
{
    if (!Bindings.beginLevelZoneLoad(session.booking.mapName, session.booking.gameType))
    {
        logGameServer("map asset load rejected map=... gametype=...");
        failSession(MapAssetLoadFailed, -1, 0);
        continue;
    }
    DedicatedMapGeneration = DedicatedMapGenerationPreparation{ .requestId, .mapName, .gameType };
    logGameServer("map asset load requested map=... gametype=...");
    { lock; DedicatedSessionConsumption.waiting(WaitingForMapAssets); }
    deferredSessions.push_back(queued);
    continue;
}
```

### 2.1 三层

```text
1. 对【已经常驻的 Wetwork 地图】第二次进入零售的 zone loader 会在 out.exe 里 fault
2. ⇒ 复用已加载的代际直到请求的关卡真的变了
3. ⇒ `sameMapGeneration` 比较 (mapName, gameType) 两元组
```

### 2.2 **"重入 zone loader 会 fault"是一个硬约束**

**⇒ 与 §245 的 `ensureWeaponRegistryInitialized` 的"reset 条件化"同族。**

**⇒ 而这里更彻底：**完全不重入**。**

### 2.3 而 `deferredSessions.push_back` 后 `continue`

**⇒ 所以第一次看到新地图时**不处理**这个会话** —— 启动加载然后延后。**

**⇒ 下次 `processDedicatedControlMessages` 时 `sameMapGeneration` 为真 ⇒ 继续。**

**✓ 一个正确的"启动 + 延后"模式。**

## 三、**十二个阶段**（本组核心）

### 3.1 完整清单

```text
 ① stageSessionRoster                        （§281）
 ② sameMapGeneration 检查 → beginLevelZoneLoad → deferred
 ③ zoneLoaded(mapName) 检查 → deferred
 ④ initializeLevelWorld → WorldInitializationFailed
 ⑤ CCS_Clear → ConfigStringGenerationResetFailed
 ⑥ CCS_EnsureInitialized → ConstantConfigStringsInitializationFailed → deferred
 ⑦ initializeMantleAnimations → WorldInitializationFailed
 ⑧ ensureWeaponRegistryInitialized
      CommonAssetsUnavailable → WeaponRegistryUnavailable → deferred
      其它失败 → WeaponRegistryInitializationFailed → failSession
 ⑨ initializeServerAnimationContext → WorldInitializationFailed
 ⑩ resolveSessionCharacterPresentation（每成员）
 ⑪ （后续）
 ⑫ （后续）
```

### 3.2 而**三种不同的失败处理**

```text
failSession(stage, -1, 0)      ⇒ 【回滚 + 失败】
deferredSessions.push_back     ⇒ 【延后重试】
continue（无标记）              ⇒ 【跳过这个会话】
```

### 3.3 而 `WeaponRegistryStatus` 的**两个分支**

```php
if (weaponRegistryStatus != CommonAssetsUnavailable)
    logGameServer("weapon registry initialization failed status=" + N);
if (weaponRegistryStatus == CommonAssetsUnavailable)
{
    { lock; DedicatedSessionConsumption.failed(WeaponRegistryUnavailable, -1, 0); }
    deferredSessions.push_back(queued);
}
else
{
    failSession(WeaponRegistryInitializationFailed, -1, 0);
}
```

### 3.4 三层

```text
CommonAssetsUnavailable     ⇒ 【延后】（资产还没到）
其它非 Ready                ⇒ 【失败 + 回滚】
```

**⇒ 而且 `CommonAssetsUnavailable` **不打印错误日志**。**

**⇒ 因为它是**正常**的等待状态** ✓

### 3.5 而 `CCS_EnsureInitialized` 失败也 `deferred` 但**先标 failed**

```php
if (!initialized && !Bindings.CCS_EnsureInitialized())
{
    { lock; DedicatedSessionConsumption.failed(ConstantConfigStringsInitializationFailed, -1, 0); }
    deferredSessions.push_back(queued);
    continue;
}
```

**⚠ 标记 `failed` 又 `deferred`** —— 与 `CommonAssetsUnavailable` 的处理**不同**（那里也标 failed 然后 deferred）。

**⇒ 实际上两处一致：`failed` + `deferred`。**

**⇒ 所以 `failed` 的语义不是"终止"而是"这一轮失败"。**

**⇒ 待读 `DedicatedSessionConsumption` 的语义。**

### 3.6 而 ⑨ 的 `animationStatus != Ready ⇒ WorldInitializationFailed`

**⇒ 动画初始化失败被归为"世界初始化失败"。**

**⚠ 一个**误导的**阶段名** —— 因为动画初始化不是世界初始化。

**⇒ 与 §255 的"门控在 `currentCharacterIndex` 里 ⇒ 失败读成索引不可用"同族。**

## 四、`CCS` 的三段

```php
if (!DedicatedMapGeneration->configStringsCleared)
{
    if (!Bindings.CCS_Clear()) { failSession(ConfigStringGenerationResetFailed, -1, 0); continue; }
    DedicatedMapGeneration->configStringsCleared = true;
    logGameServer("CCS generation reset complete");
}

// The client can only become ready for gamestate after it has
// received the gamestate message. Waiting here would therefore
// deadlock the dedicated handshake before configureBooking() can
// publish the pending gamestate. Readiness remains an explicit
// post-gamestate gate below in the native client state machine.
const auto initialized = Bindings.CCS_Initialized();
if (!initialized && !Bindings.CCS_EnsureInitialized()) { ... failed + deferred ... }
```

### 4.1 而那段**关键的注释**

```text
1. 客户端只有在【收到 gamestate 消息之后】才能对 gamestate 就绪
2. ⇒ 在这里等会**死锁**专用服握手（在 `configureBooking()` 能发布 pending gamestate 之前）
3. ⇒ 就绪性保持为下方原生客户端状态机里的【显式 post-gamestate 门】
```

### 4.2 三层

```text
1. 客户端就绪需要 gamestate
2. gamestate 需要 configureBooking
3. configureBooking 在这个循环之后
⇒ 所以在这里等就绪 = 死锁
```

**⇒ 一个**清晰的循环依赖识别**。**

**⇒ 与记忆里"duplicate usercmd accepted then discarded (rejecting deadlocks)"同族 —— 死锁是一个反复出现的主题。**

### 4.3 而 `CCS_Clear` 的语义

**⇒ 与 §235 的"`CCS_Clear` 返回『清空后确认为未初始化』"一致** ✓

**⇒ 所以 `if (!CCS_Clear())` 意味着"清空失败"。**

## 五、`initializeLevelWorld` 与 `initializeMantleAnimations`

```php
if (!DedicatedMapGeneration->levelWorldInitialized)
{
    if (!Bindings.initializeLevelWorld(mapName, gameType)) { failSession(WorldInitializationFailed, -1, 0); continue; }
    DedicatedMapGeneration->levelWorldInitialized = true;
    logGameServer("world initialized map=" + mapName);
}

if (!Bindings.initializeMantleAnimations()) { failSession(WorldInitializationFailed, -1, 0); continue; }
```

### 5.1 而 `levelWorldInitialized` 是**代际标志**

**⇒ 所以同一代际只初始化一次。**

**⇒ 与 §233 的"`initializeMantleAnimations` 的幂等形状"一致** ✓

### 5.2 而 `initializeMantleAnimations` **每会话都调**

**⇒ 因为它自己幂等。**

## 六、**`CharacterSelectionResolve` 在 OLfinal 上不存在**（本组第二重要）

### 6.1 那段 CODDIFF

```php
// CODDIFF(character_customization): THIS RESOLVER DOES NOT
// EXIST ON OLfinal. CharacterSelectionResolve,
// WorldCharacterModelResolve and both of their tables are
// absent - handoff section 16a, re-checked in 18d on 1649370 -
// because OLfinal replaced the whole scheme with an
// item-driven one whose `ctx` argument and selection-id
// ordering are still unknown.
```

### 6.2 四个缺失

```text
CharacterSelectionResolve
WorldCharacterModelResolve
两者的表（两个）
```

**⇒ 而 `ctx` 参数与 selection-id 顺序**仍然未知**。**

### 6.3 而"OLfinal 用一个 item 驱动的方案替换了整个方案"

**⇒ 所以 §256 的 `CharacterRecordToSelectionName` 与 `internalNames[11]` 是**我们构造的适配器**，而不是引擎的。**

**⇒ 而 `characterSelectionResolve_` 是 `nullptr` ⇒ `characterPresentationResolverAvailable()` 返回 false。**

**⇒ 所以 §256 里 §6（§256 的报告）的 `characterSelectionResolve_` 只在**非 OLfinal** 上有值。**

**⚠ 而 §256 的代码路径**依赖**它**：

```cpp
if (!module_ || !characterSelectionResolve_ || !configStringGet_ || !valid(request))
    return nullopt;
```

**⇒ 所以在 OLfinal 上 `resolveSessionCharacterPresentation` **恒返回 nullopt**。**

**✓ 与这里的 `!characterPresentationResolverAvailable()` 分支一致。**

### 6.4 而"它产生的是**装饰性**的"

```php
// What it produces is COSMETIC: a character index, a colour, a
// viewmodel index and eleven model selection ids. Failing the
// entire match on it means no player ever loads a map on this
// build over a wrong player model, which is the wrong trade.
// So when the resolver is ABSENT - not when it is present and
// rejects something - carry the character index through and go
// on, loudly.
```

### 6.5 三层

```text
1. 它产生的是【装饰性】的：角色索引、颜色、viewmodel 索引、十一个模型选择 id
2. ⇒ 为它失败整个比赛 = 在这个 build 上【没有人能加载地图】只为错误的玩家模型
3. ⇒ 当解析器【缺席】时继续（不是当它存在而拒绝时）
```

### 6.6 **"缺席 vs 存在而拒绝"是两条不同的路**

**⇒ 这是一个精确的区分** —— 与 §244 的"缺失行是真正的问题 vs 别名"同族。

### 6.7 而 `reportSessionMemberItemHandles()` **每次都打**

```php
// OLMOD(section-48-input-probe): print what the room roster holds at the
// exact moment model resolution is attempted. Section 48c has asked
// "are there real character item ids anywhere this server can reach"
// since it was written, and the only answer on record is the
// selectionIds=1,0,0,... placeholder -- which is this server's own
// output, not a measurement of the engine's input.
logGameServer(Bindings.reportSessionMemberItemHandles());
```

### 6.8 三层

```text
1. 在【模型解析被尝试的那一刻】打印房间名册持有什么
2. 记录中的唯一答案是 `selectionIds=1,0,0,...` 占位符
3. ⇒ 而那是【本服务器自己的输出】，不是对引擎输入的测量
```

**⇒ 所以 `reportSessionMemberItemHandles` 的目的是**拿到引擎的输入**。**

**⇒ 与 §255 的 `decodeKey` 对比同族。**

## 七、**"继续大声地"必须能通过校验**（本组第三重要）

```php
// AND IT HAS TO VALIDATE, OR "continue loudly" NEVER SPAWNS ANYONE.
// Carrying only the character index leaves viewmodelIndex 0 and all
// eleven selectionIds 0, and validCharacterCustomization rejects
// exactly that -- it requires a non-zero viewmodel and at least one
// non-zero selection. The customization then resolves to nullopt, and
// the spawn conjunction in SvServerWorld drops the term in silence, so
// picking a class does nothing on screen forever and the client
// re-sends the pick until it gives up.
```

### 7.1 五层

```text
1. 只携带角色索引 ⇒ `viewmodelIndex = 0` 且十一个 `selectionIds` 全 0
2. 而 `validCharacterCustomization` **恰好拒绝**那个 —— 它要求非零 viewmodel 且至少一个非零 selection
3. ⇒ 定制化解析成 nullopt
4. ⇒ `SvServerWorld` 里的 spawn 合取式【静默地丢掉那一项】
5. ⇒ 选职业在屏幕上永远没效果，而客户端【反复重发直到放弃】
```

### 7.2 **"静默地丢掉那一项"**

**⇒ 一个**合取式里的 nullopt 被当作 false** ⇒ 整个 spawn 条件不成立 ⇒ **静默**。**

**⇒ 这是"沉默读起来像健康"的最深一层** —— 因为**没有错误，只是条件不满足**。

### 7.3 而"客户端反复重发直到放弃"

**⇒ 一个**玩家可见**的症状。**

### 7.4 与 §255 的 `NULL`/`EMPTY`/`UNREADABLE` 三态

**⇒ 这里又多了两个层次：**

```text
resolver 缺席         ⇒ 我们继续（但视图模型错）
validation 拒绝       ⇒ nullopt
spawn 合取式丢项      ⇒ 【静默】无人 spawn
```

## 八、`PreparedSessionMember` 的构造

```php
PreparedSessionMember preparedMember{
    .xuid = sessionMember.userId,
    .username = sessionMember.username,
    .characterIndex = sessionMember.loadout.characterIndex,
};
const auto presentation = Bindings.resolveSessionCharacterPresentation(sessionMember.loadout);
```

### 8.1 三项先填

```text
xuid
username
characterIndex
```

**⇒ 而其它六个字段（presentation / loadouts / perks / equipment / offhands / rewards）留待后续。**

## 九、关键结论

1. **对已常驻地图重入 zone loader 会在 out.exe 里 fault** ⇒ 必须复用代际。
2. **`sameMapGeneration` 比较 (mapName, gameType) 两元组。**
3. **三种失败处理**：`failSession`（回滚）/ `deferred`（延后）/ `continue`（跳过）。
4. **`CommonAssetsUnavailable` 延后而不打错误日志** —— 它是正常的等待态。
5. **`failSession` 与 `deferred` 可以同时用** ⇒ `failed` 的语义是"这一轮失败"而不是"终止"。
6. **动画初始化失败被归为 `WorldInitializationFailed`** —— 误导的阶段名。
7. **"在这里等就绪 = 死锁"** —— 客户端就绪需要 gamestate，gamestate 在这个循环之后。
8. **`CharacterSelectionResolve`/`WorldCharacterModelResolve` 及其两个表在 OLfinal 上不存在**。
9. **OLfinal 用 item 驱动方案替换了整个角色选择方案**，而 `ctx` 与 selection-id 顺序未知。
10. **"缺席 vs 存在而拒绝"是两条不同的路**。
11. **"继续大声"必须能通过校验** —— 否则 `validCharacterCustomization` 拒绝 ⇒ 静默地无 spawn。
12. **"合取式里的 nullopt 静默丢项"** 是"沉默读起来像健康"的最深一层。
13. **客户端反复重发直到放弃** —— 一个玩家可见的症状。

## 十、未闭合点

- `DedicatedSessionConsumption.failed` 的确切语义（与 `deferred` 合用）。
- `validCharacterCustomization` 的完整判据。
- `SvServerWorld` 的 spawn 合取式。
- `Appmain.cpp` 2795 行之后未读取。
