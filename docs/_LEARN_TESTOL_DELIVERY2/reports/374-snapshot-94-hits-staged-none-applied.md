# 374 · **"94 次命中暂存而没有一次被应用"** —— 七项具名拒绝、`1147` 的 `220` 次连续拒绝、副槽陷阱与"每 think 从 `weaponGrants_` 重推导"

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 21200–21600 行。

## 二、**`1147` 的副槽陷阱**（本组第二重要）

### 2.1 那段

```php
// THE SECONDARY SLOT, AND ONLY WHEN IT DIFFERS FROM THE PRIMARY.
// SV_IsResolvedLoadoutValid ends with
// `primary.weaponAssetIndex != secondary.weaponAssetIndex`, so writing a weapon
// the class ALREADY carries would make the two slots equal, invalidate the
// whole loadout, and have SV_FindResolvedWeapon return nullptr for EVERY
// weapon. MEASURED: picking up 1147 -- the first modular index, which is also
// this class's own primary -- produced 220 weapon_movement_rejected in a row.
// A weapon already in the primary needs nothing; it resolves as it stands.
if (candidateClient.resolvedLoadout) {
    const auto grantSlot = (size_t)clientNum;
    if (grantSlot < weaponGrants_.size() && weaponGrants_[grantSlot].active) {
        const auto &granted = weaponGrants_[grantSlot].weapon;
        if (candidateClient.resolvedLoadout->primary.weaponAssetIndex != granted.weaponAssetIndex) {
            candidateClient.resolvedLoadout->secondary = granted;
        }
    }
}
```

### 2.2 十四层

```text
1. **【副】槽，而【只在它与主槽不同时】**
2. ⇒ **`SV_IsResolvedLoadoutValid` 以 `primary.weaponAssetIndex != secondary.weaponAssetIndex` 结束**
3. ⇒ **所以写一个职业【已经携带】的武器会让两个槽【相等】**
4. ⇒ **使【整个装备】无效**
5. ⇒ **并让 `SV_FindResolvedWeapon` 对【每一把】武器返回 nullopt**
6. ⇒ **实测：捡起 `1147` —— 第一个模块化索引，而它也是这个职业自己的主武器**
7. ⇒ **产生 `220` 次连续的 `weapon_movement_rejected`**
8. ⇒ **一个已经在主槽里的武器【不需要任何东西】**
9. ⇒ **它按现状解析**
10. ⇒ **所以只有不同时才写副槽**
```

### 2.3 ⭐ **"一个槽的相等使整个装备无效"**

**✅ 与 §371 的"把 1137 放进装备会让那个槽失败 ⇒ 带走整个装备"**同族（**第二次"一个槽毁掉全部"）。**

**⇒ 两个不同的"槽级错误"：**

```text
§371  空手的槽【缺字段】 ⇒ 那个槽失败
§374  副槽【等于主槽】 ⇒ 那个槽失败
⇒ **两者都带走整个装备**
```

**✅ **第八次"全有或全无"。**

### 2.4 而**"`220` 次连续"**

**✅ 与 §371 的 `4,253` 次**同族（**第二次大规模拒绝计数）。**

**⚠ 而 `220` 次**短得多**（因为一次拾取后玩家可能停手）。**

**✅ 与 §374 三的"94 次命中"**同族。

### 2.5 而**"每 think 从 `weaponGrants_` 重推导"**

```php
// WHY A HOLD RATHER THAN A WRITE. sect.190 is explicit that a weapon outside
// the class does not go into SvResolvedLoadout -- that struct sits inside the
// client state the address-keyed native buffer is sized against -- and the
// alt-fire path answers the same problem with a lookup for exactly that reason.
// This does not grow the struct and does not touch the player's stored class:
// it is re-derived from weaponGrants_ every think, on the candidate copy, and
// the spawn re-copies the class loadout over it on every life. Same shape as
// applyNoclipHold above, and for the same reason -- the world rebuilds this
// state every frame, so a single write is gone by the next one.
```

**⇒ 十二层**：

```text
1. **为什么是一个保持而不是一次写**
2. ⇒ **sect.190 明确：一个职业外的武器【不】进 `SvResolvedLoadout`**
3. ⇒ **因为那个结构坐落在【被按地址键的原生缓冲区所尺寸】的客户端状态里**
4. ⇒ **而 alt-fire 路径以一次查找回答同一个问题**
5. ⇒ **这个不增长结构也不碰玩家存储的职业**
6. ⇒ **它每 think 从 `weaponGrants_` 重推导，在【候选副本】上**
7. ⇒ **而 spawn 在每一世重新拷职业装备【覆盖】它**
8. ⇒ **与上面的 `applyNoclipHold` 同一个形状，同一个理由**
9. ⇒ **因为世界每帧重建这个状态，所以一次单写在下一帧就没了**
```

**✅ 与 §371 的"空手是一个保持状态"**完全同族（**第三次）。**

**⚠ 而"sect.190 明确：职业外武器不进 `SvResolvedLoadout`"⇒ **一个明确的架构禁令**。**

**✅ 与 §370 的"第 184h 节：向按地址键的原生缓冲区加字段让死亡动画坏了两次"**同族（**第七次"不能增长按地址键的缓冲区"）。**

## 三、**`94` 次命中零应用的七项**（本组最重要的一段）

### 3.1 那段

```php
if (!SV_IsPlayerDamagePayloadValid(payload, PlayerDamagePayloadLimits) ||
    !targetClient || !targetEntity || !weapon ||
    targetClient->gameplayState != ClientGameplayState::Playing ||
    targetClient->playerState.health <= 0 ||
    targetEntity->networkState.number != payload.targetClientNum ||
    targetEntity->clientNum != payload.targetClientNum)
{
    // SAY WHICH CONJUNCT REFUSED. Section 187l.
    //
    // 94 bullet-hits staged and NOT ONE applied, against 7 deaths in a
    // cycle earlier the same day -- so every hit is dying in this seven-term
    // test and the term is not recoverable from the outside, because they
    // all produce the same ClientEventsRejected.
    //
    // `weapon` is the one to watch: SV_FindResolvedWeapon matches the
    // payload's weaponAssetIndex against the loadout's primary or secondary
    // and nothing else, and adding an equipped attachment builds a NEW
    // modular weapon variant with a NEW asset index. If the client fires
    // with the index it knows and this server resolved a different one,
    // every shot is rejected here and nothing anywhere says so.
```

### 3.2 十六层

```text
1. **说【哪一个合取项】拒绝了**（第 187l 节）
2. ⇒ **94 次子弹命中被暂存而【一次也没有】被应用**
3. ⇒ **对照的是同一天早些时候一个循环里的 7 次击杀**
4. ⇒ **所以每一次命中都在这个【七项测试】里死掉**
5. ⇒ **而那一项【从外面不可恢复】**
6. ⇒ **因为它们全都产生同一个 `ClientEventsRejected`**
7. ⇒ **`weapon` 是要盯的那个**
8. ⇒ **因为 `SV_FindResolvedWeapon` 把载荷的 `weaponAssetIndex` 对装备的主或副匹配，【别的什么都不】** —— **9.**⇒ **而添加一个装备的附件会构建一个【新的模块化武器变体】带一个【新的资产索引】**
9. ⇒ **所以若客户端用【它知道的】索引开火而本服务器解析出【一个不同的】**
10. ⇒ **每一枪都在这里被拒而【任何地方都没说】**
```

### 3.3 ⭐⭐ **"添加一个附件构建一个新的模块化武器变体带一个新的资产索引"**

**✅ 这是本文件里**最深的武器系统洞察**。**

**⇒ 三层**：

```text
1. 客户端开火时用它持有的 `weaponAssetIndex`
2. ⇒ **而服务器从【冻结装备】解析**
3. ⇒ **而那个装备的索引是【职业的】不是【玩家的模块化变体】**
4. ⇒ **⇒ 两个索引不匹配 ⇒ 每一枪都被拒**
```

**✅ 与 §370 的"alt 的 `+3720` 是零而 `+12` 命名基础武器"**同族（**第三次"模块化索引空间"）。**

**⚠ 而"添加附件 ⇒ 新变体 ⇒ 新索引"⇒ **所以索引是**动态的**。**

**✅ 与 §345 的"客户端的基线 xmodel 不是文件的 xmodel"**同族（**第六次"两个 id 空间"）。**

**⇒ **三个 id 空间**：**

```text
configstring 带（模型）
clientInfo 的 characterItemId
**模块化武器变体索引**
```

**✅ **第三次确认多 id 空间。**

### 3.4 而**七项的完整清单**

```text
① SV_IsPlayerDamagePayloadValid(payload, Limits)
② targetClient 存在
③ targetEntity 存在
④ weapon（SV_FindResolvedWeaponOrAlt）
⑤ targetClient->gameplayState == Playing
⑥ targetClient->playerState.health > 0
⑦ targetEntity->networkState.number == targetClientNum
⑧ targetEntity->clientNum == targetClientNum
```

**⇒ 八项（不是七）。**

**⚠ 而注释说"七项测试"。**

**⇒ 一处**计数不符**（第三次）。**

### 3.5 而**"94 次对 7 次击杀"**

**✅ 与 §355 的 `259,968`、§371 的 `4,253`**第八次大规模统计。

**⚠ 而"94 命中而零应用"⇒ **一个 100% 的失败率**。**

**✅ 与 §371 的"4,253 次全 `weapon=1137`"**同族（**第三次"100% 一致"）。**

## 四、**`clientThink` 的候选副本架构**（本组第三重要）

### 4.1 那段

```cpp
auto candidateCommandState = SvGameClientCommandState{
    .currentUserCmd = effectiveCommand, .lastCmdTime = snapshot_.serverTime,
};
if (state.client.commandState) candidateCommandState.oldUserCmd = state.client.commandState->currentUserCmd;
...
auto candidateClient = state.client;
candidateClient.commandState = candidateCommandState;
applyNoclipHold(clientNum, candidateClient.playerState);
// 副槽保持
auto candidateEntity = state.entity;
auto candidateGlassState = glassState_;
auto candidateGlassDamageState = glassDamageState_;
candidateEntity.pendingScriptNotifications.clear();
... 三个 pending 容器 clear
const auto *const resolvedLoadout = candidateClient.resolvedLoadout ? &*candidateClient.resolvedLoadout : nullptr;
const auto failureStage = clientThinkReal(candidateEntity, candidateClient, candidateGlassState, candidateGlassDamageState, resolvedLoadout);
```

### 4.2 十一层

```text
1. **构造 `candidateCommandState`**（`effectiveCommand` + `oldUserCmd`）
2. ⇒ **拷 `state.client` 到 `candidateClient`**
3. ⇒ **替换它的 `commandState`**
4. ⇒ **`applyNoclipHold` 在候选上**
5. ⇒ **副槽保持在候选上**
6. ⇒ **拷 `state.entity` 到 `candidateEntity`**
7. ⇒ **拷两个玻璃状态**
8. ⇒ **清四个 pending 容器**
9. ⇒ **取 `resolvedLoadout` 指针**
10. ⇒ **调 `clientThinkReal` 全是候选**
11. ⇒ **所以主状态在 `clientThinkReal` 期间【完全不变】**
```

**✅ 与 §349 的"staged-then-commit"**第七次。**

**⇒ **一个彻底的"候选副本"架构**：**

```text
commandState / client / entity / glass×2 / resolvedLoadout
⇒ **全部候选**
```

**✅ **第六次"事务性"，而这里是**最大范围的候选**。

### 4.3 而**四个 `pending` 容器的清空**

```cpp
candidateEntity.pendingScriptNotifications.clear();
candidateEntity.pendingPlayerDamagePayloads.clear();
candidateEntity.pendingEntityDamagePayloads.clear();
candidateEntity.pendingEntitySpawns.clear();
```

**⇒ 三层**：

```text
1. **四个容器必须【每 think 清空】**
2. ⇒ **因为它们是【输出】**
3. ⇒ **而候选取自 `state.entity`（上一帧的）**
```

**⚠ 所以若上一帧的 `state.entity` 保留了**未提交的输出**，这会让它们**被丢弃**。**

**⇒ 与 §349 的"提交在成功之后"**一致 ✓**

**✅ 一个**正确的事务边界**。

### 4.4 而**`effectiveCommand.weapon == 0` 的翻译**

```cpp
// S3: an empty pistol slot is represented by usercmd.weapon == 0 on
// the selection frame. The class provider resolves that slot to the
// live `chicken_melee_mp` definition, so translate the request before
// native Pmove/weapon movement sees it. Keep genuine native null-weapon
// states (mantle/ladder/spawn) untouched by requiring the player to be
// holding the resolved primary weapon at the transition.
if (effectiveCommand.weapon == 0 && state.client.resolvedLoadout &&
    state.client.resolvedLoadout->secondary.weaponAssetIndex == 1154 &&
    state.client.playerState.currentWeaponAssetIndex != 0 &&
    state.client.playerState.currentWeaponAssetIndex == state.client.resolvedLoadout->primary.weaponAssetIndex)
{
    effectiveCommand.weapon = state.client.resolvedLoadout->secondary.weaponAssetIndex;
}
```

**⇒ 十层**：

```text
1. **S3：一个空手枪槽在选择帧上以 `usercmd.weapon == 0` 表示**
2. ⇒ **职业提供者把那个槽解析成活动的 `chicken_melee_mp` 定义**
3. ⇒ **所以在原生 pmove/武器移动看到它【之前】翻译那个请求**
4. ⇒ **保持真正的原生空武器状态（翻越/梯子/出生）不动**
5. ⇒ **通过要求玩家在转换时【持着解析出的主武器】**
6. ⇒ **所以四个条件**：`weapon == 0` / 有装备 / **副槽 == `1154`** / 当前是主武器
7. ⇒ **翻译成副槽的 `weaponAssetIndex`**
```

**✅ 与 §371 的"武器 0 是引擎自己的名字"**不同** —— 这里是**`1154` 是 `chicken_melee_mp`**。**

**⚠ 所以**三种"空"**：**

```text
武器 0     ⇒ 引擎的原生空武器
武器 1137  ⇒ `dmz_empty_mp`（客户端视模型）
武器 1154  ⇒ `chicken_melee_mp`（空手枪槽的占位）
```

**✅ **三个不同的"空"**。**

**⚠ 而三个都在 `1xxx` 或 `0` 附近。**

**✅ 一个**容易混淆的地方**。

### 4.5 而**`zombieDownedState` 的武器强制**

```cpp
if (const auto down = zombieDownedState(clientNum); down && !down->bledOut) {
    candidateCommandState.currentUserCmd.weapon = down->weaponAssetIndex;
    candidateCommandState.currentUserCmd.offHandIndex = 0;
    candidateCommandState.currentUserCmd.lastWeaponAltModeSwitch = 0;
}
```

**⇒ 三层**：

```text
1. **倒地且未流血致死 ⇒ 强制武器**
2. ⇒ **而清副手与 `lastWeaponAltModeSwitch`**
3. ⇒ **所以倒地时只有一个武器**
```

**✅ 与 §370 的"`altPair` 的陈旧检测"**配合。**

**⚠ 而"清 `lastWeaponAltModeSwitch`"⇒ **防交替模式残留**。**

**✅ 一个**正确的状态清理**。

## 五、**`clientThink` 的四个前置**

```cpp
if (state.client.gameplayState != ClientGameplayState::Playing) return reject(NotPlaying);
if (state.client.spawnedThisFrame) return reject(SpawnedThisFrame);
if (command.commandTime <= state.client.playerState.commandTime) return reject(NonIncreasingCommandTime);
```

**⇒ 三项（前两个 + 第三个）。**

**✅ 与 §349 的四十个阶段**配合。**

**⚠ 而 `spawnedThisFrame` ⇒ **出生帧跳过 think**。**

**✅ 与 §368 的"`spawnedThisFrame`"**第二次。

## 六、**`thinkStatus` 的四项记录**

```cpp
state.thinkStatus.lastAttemptedCommandTime = command.commandTime;
state.thinkStatus.playerStateCommandTime = state.client.playerState.commandTime;
state.thinkStatus.serverTime = snapshot_.serverTime;
...
const auto reject = [&state](const SvClientThinkFailureStage stage) {
    state.thinkStatus.failureStage = stage;
    ++state.thinkStatus.failureCount;
    return false;
};
```

**⇒ 三层**：

```text
1. **每次 think 都记三个时间**（尝试 / 状态 / 服务器）
2. ⇒ **而拒绝时记阶段与计数**
3. ⇒ **所以 `NonIncreasingCommandTime` 可以从这三个数直接验证**
```

**✅ 与 §369 的"`pmFlags |= 0x800` 让命令时间不推进"**完全闭合 ✓

**⇒ **一个诊断设计**：三个时间让那个 bug **可验证**。**

**✅ 与 §368 的"三层命名失败项"**同族。

## 七、`client-think-phase-census` 的**"每五秒一行"**

```php
// OLMOD(client-think-phase-census): a live Factory trace showed that
// the server remains smooth with eight actors present while the player
// is stationary, but ClientThink time rises sharply as soon as player
// movement begins.  Keep this aggregate deliberately off the hot log
// path: one line per five seconds distinguishes candidate/Pmove work,
// source transaction work, the collision/native-mirror rebuild, and
// post-commit callbacks for moving versus idle commands.
```

### 7.1 八层

```text
1. **一个活动的 Factory trace 显示：八个 actor 在场而玩家静止时服务器保持平滑**
2. ⇒ **但 `ClientThink` 时间【玩家一移动就急剧上升】**
3. ⇒ **刻意把这个聚合成远离热日志路径**
4. ⇒ **每五秒一行**
5. ⇒ **区分**：
     · **候选/Pmove 工作**
     · **源事务工作**
     · **碰撞/原生镜像重建**
     · **提交后回调**
6. ⇒ **对移动 vs 空闲命令**
```

**✅ 与 §372 的"`player-kinematics` 的爆发"**同族（**第三次"性能分析"）。

**⚠ 而"玩家一移动就急剧上升"⇒ **一个具体的性能特征**。**

**✅ 与 §371 的"`findXAsset` 守卫 1.2 秒/帧"**同族（**第四次性能问题**）。

### 7.2 而**`thinkPhaseBegan` 与 `thinkRealFinished`**

```cpp
const auto thinkPhaseBegan = std::chrono::steady_clock::now();
...
const auto failureStage = clientThinkReal(...);
const auto thinkRealFinished = std::chrono::steady_clock::now();
```

**⇒ 三层**：

```text
1. **两个 `steady_clock` 时间戳**
2. ⇒ **所以可以分段计 ClientThink 时间**
3. ⇒ **而 `steady_clock` 正确（不是 `system_clock`）**
```

**✅ 一个**正确的计时选择**。

## 八、关键结论

1. **⭐ 副槽陷阱**：`SV_IsResolvedLoadoutValid` 以 `primary != secondary` 结束 ⇒ 写一个职业已携带的武器会让**两个槽相等 ⇒ 整个装备无效 ⇒ `SV_FindResolvedWeapon` 对每一把武器返回 nullopt**。
2. **`1147`（第一个模块化索引，也是这个职业自己的主武器）产生 `220` 次连续 `weapon_movement_rejected`**。
3. **"一个已经在主槽里的武器不需要任何东西，它按现状解析"`**。
4. **"每 think 从 `weaponGrants_` 重推导，在候选副本上"`** —— 第三次"保持状态"。
5. **"sect.190 明确：职业外武器不进 `SvResolvedLoadout`，因为那个结构坐落在被按地址键的原生缓冲区所尺寸的客户端状态里"`** —— 第七次"不能增长按地址键的缓冲区"。
6. **⭐⭐ "94 次子弹命中被暂存而【一次也没有】被应用，对照同一天早些时候一个循环里的 7 次击杀"`** —— 第八次大规模统计，而 **100% 失败率**。
7. **"七项测试而那一项从外面不可恢复，因为它们全都产生同一个 `ClientEventsRejected`"`**（第四次"具名而不是笼统"的**需求陈述**）。
8. **⭐⭐ "添加一个装备的附件会构建【一个新的模块化武器变体】带一个【新的资产索引】"`** —— 若客户端用它知道的索引开火而服务器解析出**一个不同的** ⇒ **每一枪都被拒而任何地方都没说**。
9. **⚠ 注释说"七项测试"而代码是八项** —— 第三次计数不符。
10. **⭐ `clientThink` 的候选副本架构**：`commandState` / `client` / `entity` / `glass×2` / `resolvedLoadout` **全部候选** ⇒ 主状态在 `clientThinkReal` 期间完全不变。
11. **四个 `pending` 容器每 think 清空**（它们是**输出**）—— 一个正确的事务边界。
12. **⭐ 三种"空"武器**：`0`（引擎原生空）/ `1137`（`dmz_empty_mp` 视模型）/ `1154`（`chicken_melee_mp` 空手枪槽）。
13. **`effectiveCommand.weapon == 0` 的翻译需要四个条件**（含**当前持着主武器**）以保护真正的原生空武器状态。
14. **`zombieDownedState` 强制武器并清 `offHandIndex` 与 `lastWeaponAltModeSwitch`**。
15. **`thinkStatus` 的三个时间**让 `NonIncreasingCommandTime` **可直接验证** —— 一个诊断设计，与 §369 的 `pmFlags |= 0x800` 事故完全闭合。
16. **⭐ `client-think-phase-census`：八个 actor 而玩家静止时平滑，玩家一移动 `ClientThink` 时间急剧上升** ⇒ 分段计时（用 `steady_clock`）。

## 九、未闭合点

- `PlayerDamagePayloadLimits` 的完整值。
- `SV_FindResolvedWeaponOrAlt` 的 alt 回退。
- `1154` 与 `chicken_melee_mp` 的关系。
- `applyNoclipHold` 的实现。
- 七项 vs 八项的注释错误。
- `sv_snapshot_mp.cpp` 21600 行之后未读取（27,016 行，进度 80%）。
