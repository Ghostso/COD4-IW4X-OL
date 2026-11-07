# 367 · **"按它【是什么】判别，不是按它的 eType"** —— 画笔模型迁到 `ET_SCRIPTMOVER` 后测试别名、`frameReject=entity_domain` 而零快照、血量再生的边界第一跳

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 18400–18800 行。

## 二、**`setMapGameObjects` 的别名 bug**（本组最重要的一段）

### 2.1 那段

```php
// DISCRIMINATE ON WHAT THE ENTITY IS, NOT ON ITS eType. This used
// to lead with `eType == EntityTypeScriptMover` and read it as "a
// script model, so force solid to 0" -- correct only while brush
// models were ET_GENERAL. Once they moved to ET_SCRIPTMOVER the
// test aliased, every one of the map's brush models took the script
// model branch, and each came out of it with solid cleared while its
// brush model index stayed set. That pair is an invariant the frame
// validator enforces, and a single entity failing it rejects the
// WHOLE frame for EVERY client -- the server logged
// `frameReject=entity_domain` and sent no snapshots at all while the
// client sat on "waiting for player data".
//
// The collision shape is what actually separates the two, so it
// goes first and the eType test only sees what it always meant.
const auto isBrushModel =
    entity.collisionShape == SvCollisionShape::BrushModel &&
    entity.brushModelClipHandle.has_value();
if (!isBrushModel) {
    if (entity.networkState.eType != EntityTypeScriptMover) continue;
    staged.push_back({ ... .solid = 0, .brushModelIndex = entity.networkState.scriptMoverBrushModelIndex });
    continue;
}
```

### 2.2 十六层

```text
1. **按它【是什么】判别，不是按它的 eType**
2. ⇒ **这过去以 `eType == EntityTypeScriptMover` 打头**
3. ⇒ **并把它读成"一个脚本模型，所以强制 solid 为 0"**
4. ⇒ **那【只在】画笔模型是 `ET_GENERAL` 时正确**
5. ⇒ **一旦它们迁到 `ET_SCRIPTMOVER`**
6. ⇒ **那个测试【别名】了**
7. ⇒ **地图的每一个画笔模型都走了脚本模型分支**
8. ⇒ **而每一个出来时 `solid` 被清零而其 `brushModelIndex` 仍置位**
9. ⇒ **那一对是帧验证器强制的一个不变式**
10. ⇒ **而一条实体失败它【拒掉每个客户端的整帧】**
11. ⇒ **服务器记了 `frameReject=entity_domain`**
12. ⇒ **而【一个快照也不发】**
13. ⇒ **而客户端坐在 "waiting for player data"**
14. ⇒ **碰撞形状才是真正分开两者的东西**
15. ⇒ **所以它先走而 eType 测试只看到它一直意味着的东西**
16. ⇒ `isBrushModel = collisionShape == BrushModel && brushModelClipHandle.has_value()`
```

### 2.3 ⭐⭐ **"迁移之后测试别名了"**

**✅ 这是本文件里**最珍贵的一条迁移教训**。**

**⇒ 三层**：

```text
1. `ET_GENERAL` = 画笔模型（旧）
2. ⇒ **迁到 `ET_SCRIPTMOVER`（§350）**
3. ⇒ **而一个 `eType == ET_SCRIPTMOVER` 的判别变成了"所有脚本模型 + 所有画笔模型"**
4. ⇒ **即编译器不报错，而语义彻底变了**
```

**✅ 与 §350 的"`ET_SCRIPTMOVER` 而不是 `ET_GENERAL`，而这就是【门不可见】的原因"**形成一个**完整的回声。**

**⇒ **一次改动在一个地方修好而在另一个地方弄坏。**

**⚠ 而这里**症状完全不同**：**

```text
§350  门不可见（渲染层）
§367  零快照（验证层）
```

**✅ 与 §360 的"eType 21 杀死客户端"**同族（**第二次"eType 改动的远端后果"**）。

**⇒ 两个 eType 改动的后果：**

```text
§360  19 → 21  ⇒ 编解码器不同 ⇒ 客户端崩溃
§367  ET_GENERAL → ET_SCRIPTMOVER ⇒ 判别别名 ⇒ 零快照
```

**✅ **两次 eType 迁移两次事故**。

### 2.4 而**`frameReject=entity_domain` + "waiting for player data"**

**✅ 与 §346 的"`entity_domain reject num=700 eType=19`"**同族（**第二次同一个 reject 名**）。**

**⚠ 而 §346 的 offender 行命名了具体实体。**

**⇒ 而这里说"服务器记了 `frameReject=entity_domain` 而**一个快照也不发**"。**

**⚠ 所以**即使有 offender 行，这个 bug 仍需要人去找**。**

**✅ 一个**真实的定位困难**。

### 2.5 而 `svg` 的两支对比

```text
非画笔（脚本模型）：
    solid = 0
    brushModelIndex = 保留

画笔：
    solid = active ? *solid : 0
    brushModelIndex = active ? clipHandle : 0
```

**⇒ 三层**：

```text
脚本模型：`solid = 0` 而索引【不动】
画笔：    两个【配对】动
```

**✅ 与 §365 的"配对"**第四次。**

**⚠ 而**脚本模型的 `solid = 0` 是恒定的**（不需要索引清零）。**

**✅ 因为**脚本模型没有 `brushModelIndex`**（它是 xmodel）。**

**⚠ 但代码写 `brushModelIndex = entity.networkState.scriptMoverBrushModelIndex`（保留）。**

**⇒ 所以**若一个脚本模型有非零的 `brushModelIndex`** ⇒ **那仍是不变式违反**。**

**⚠ 但**`solid = 0`** ⇒ **所以配对是 (0, 非零)**。**

**⚠ 而 §365 说"`solid` 与索引必须配对"。**

**⇒ 所以**`solid = 0` 而索引非零会失败**。**

**⚠ 一个**潜在的矛盾**。**

**⇒ 可能脚本模型的 `scriptMoverBrushModelIndex` **总是 0**。**

**✅ 一个**合理的假设**。**

### 2.6 而**`Activation` 结构的九项**

```cpp
struct Activation {
    uint32 entityNum{};
    bool previousActive{}, previousCollisionLinked{};
    uint32 previousSolid{};
    bool active{}, collisionLinked{};
    uint32 solid{};
    uint16 previousBrushModelIndex{}, brushModelIndex{};
};
```

**⇒ 九项 = 四个"previous" + 五个"new"。**

**✅ 与 §364 的"整条实体拷贝"**不同**（这里**逐字段**）。**

**⚠ 所以**两种回滚风格**：**

```text
§364  `previous = entity->second`（整条）
§367  `Activation` 的四个 previous 字段（逐字段）
```

**✅ 而**逐字段更省**（4 个 vs 整条）。**

**⚠ 而**整条更安全**（不会漏字段）。**

**✅ **一个真实的权衡**。

### 2.7 而**"一个实体失败 ⇒ 整帧拒 ⇒ 每个客户端零快照"**

**✅ 与 §346 的"缺一个 eType 拒掉整帧"**第四次。

**⇒ **一个极端的放大链**：

```text
1 条实体
⇒ 1 帧
⇒ 1 客户端
⇒ **N 个客户端**
⇒ **整场比赛**
```

**✅ 与本文件反复的"全有或全无"**完全一致。

## 三、**`unlinkEntityCollision` 的"配对，同其它一切地方"**

```php
entity->second.ownerEntityNum.reset();
entity->second.currentAngles = {};
entity->second.collisionShape = SvCollisionShape::Capsule;
entity->second.brushModelClipHandle.reset();
entity->second.scriptGameObjectName.clear();
entity->second.mapModeEligible = true;
entity->second.collisionContents = 0;
entity->second.gameplayActive = false;
entity->second.collisionLinked = false;
entity->second.networkState.solid = 0;
// Paired with solid, for the same reason as everywhere else.
entity->second.networkState.scriptMoverBrushModelIndex = 0;
```

**⇒ 十层，而注释只说一句"与 `solid` 配对，与其它一切地方同一个理由"。**

**✅ 与 §365 的"配对"**第五次。**

**⇒ **第五次出现 ⇒ 注释已简化为交叉引用。**

**✅ 一个**成熟的注释收敛**。

## 四、**血量再生的"边界第一跳"**（本组第二重要）

### 4.1 那段

```php
// Unsigned throughout, because SvPlayerState::health is. A dead player
// is health 0 and has no window; a full one has nothing to gain.
if (currentHealth == 0 || maxHealth == 0 || currentHealth >= maxHealth) return currentHealth;
const auto begins = state.lastDamageTime + SvHealthRegenDelayMilliseconds;
// Compared before subtracting, so a serverTime short of the window
// cannot wrap into an enormous elapsed.
if (serverTime < begins) return currentHealth;
// THE FIRST TICK LANDS ON THE BOUNDARY, and that is measured, not
// assumed: in the spec demo a player left on 22 at t=101700 is already
// on 42 at t=106700 -- exactly +5000 ms and already one 100 ms frame's
// worth of healing. Elapsed alone returns 22 there and heals a frame
// late for the rest of the run; crediting one frame up front is what a
// server that ticks regen on the frame the timer expires does, and it
// fits the corpus better (87%/94% of post-damage assertions against
// 71%/86% without it -- Tools/demo-re/health-timeline.py).
const std::uint64_t elapsed = (uint64_t)(serverTime - begins) + frameMilliseconds;
// Derived from the damage point rather than accumulated per frame: an
// accumulator drifts whenever frameMilliseconds does not divide the
// rate, and silently heals slower than retail. This cannot drift.
const auto healed = (uint64_t)state.healthAtDamage + (elapsed * SvHealthRegenHealthPerSecond) / 1000;
const auto target = (uint32)std::min<uint64_t>(healed, maxHealth);
// Never take health AWAY: something else may legitimately have raised
// it since the damage that opened this window.
return std::max(currentHealth, target);
```

### 4.2 十九层

```text
1. **全用无符号，因为 `SvPlayerState::health` 是无符号的**
2. ⇒ **一个死玩家是 health 0 而没有窗口**
3. ⇒ **一个满的没什么可获得的**
4. ⇒ `begins = lastDamageTime + SvHealthRegenDelayMilliseconds`
5. ⇒ **在【减法之前】比较，所以一个短于窗口的 `serverTime` 不能回绕成一个巨大的 elapsed**
6. ⇒ **第一跳落在【边界】上，而那是【测量的】不是假设的**
7. ⇒ **在 spec demo 里一个在 `t=101700` 停在 22 的玩家在 `t=106700` 已经是 42**
8. ⇒ **恰好 +5000ms 而已经是【一个 100ms 帧】的 healing**
9. ⇒ **只有 elapsed 在那里返回 22 而在剩下的运行里【慢一帧】**
10. ⇒ **预先记一帧是一个"在计时器到期的那一帧 tick 再生"的服务器所做的**
11. ⇒ **而它更好地拟合语料**（**87%/94% 对 71%/86%**）
12. ⇒ **（`Tools/demo-re/health-timeline.py`）**
13. ⇒ **`elapsed = (serverTime - begins) + frameMilliseconds`**
14. ⇒ **从伤害点推导而不是每帧累积**
15. ⇒ **因为一个累积器在 `frameMilliseconds` 不整除速率时会【漂移】**
16. ⇒ **并【静默地】比零售回得更慢**
17. ⇒ **这个不能漂移**
18. ⇒ `healed = healthAtDamage + elapsed * rate / 1000`
19. ⇒ **`target = min(healed, maxHealth)`** 而 **`return max(currentHealth, target)`**
```

### 4.3 ⭐ **"`87%`/`94%` 对 `71%`/`86%`"**

**✅ 一个**定量的模型选择**。**

**⇒ 三层**：

```text
不带"边界第一跳"  71% / 86%
带"边界第一跳"    87% / 94%
⇒ **两组都提升，而第二组更高**
```

**✅ 与 §355 的 `259,968`、§351 的 `237`**第六次大规模统计。

**⚠ 而"87%/94%"⇒ **两个不同的指标**（可能"伤害后断言的匹配率"）。**

**✅ 一个**明确的量化判据**。**

### 4.4 而**"从伤害点推导而不是每帧累积"**

**✅ 与 §353 的"`zmDamageRoll` 的确定性"**同族（**第二次"避免漂移"**）。

**⇒ 三层**：

```text
累积：`health += rate * dt`    ⇒ **`dt` 不整除时漂移**
推导：`health = f(t)`          ⇒ **无漂移**
```

**✅ 与 §354 的"`delta = Δ * (1000/duration)`"**同族（**推导而非累积**）。

**⇒ **第三次"推导优于累积"。**

### 4.5 而**"在减法之前比较"**

**⇒ 三层**：

```text
1. `serverTime < begins` ⇒ **早退**
2. ⇒ **所以 `serverTime - begins` 永不下溢**
3. ⇒ **而一个无符号下溢会是一个巨大值**
```

**✅ 与 §345 的"`serverTime - value <= 0xFF`"**同族（**第二次"减法前比较"**）。

### 4.6 而**"绝不把血量【拿走】"**

**⇒ 三层**：

```text
1. `target` 可能低于 `currentHealth`（若别的来源提高了它）
2. ⇒ **`max(currentHealth, target)`**
3. ⇒ **所以再生【永不】降血**
```

**✅ 与 §353 的"`cannotDie` 至少留 1 点血"**同族（**第二次"永不降血"**）。

## 五、**`SV_LandingPainDamage` 的"torn read"**

```cpp
// The layout is documented on SvLandingPainDamageShift. Negative can
// only mean a torn read of the ring -- the packed word is thirteen bits
// -- so it is refused rather than shifted into a plausible number.
if (eventParameter <= 0) return 0;
return (uint32)((eventParameter >> SvLandingPainDamageShift) & SvLandingPainDamageMask);
```

### 5.1 五层

```text
1. **布局在 `SvLandingPainDamageShift` 上记录**
2. ⇒ **负值【只能】意味着环的一次撕裂读**
3. ⇒ **因为打包字是【十三位】**
4. ⇒ **所以它被拒绝而不是移成一个看似合理的数字**
5. ⇒ **`& mask` 提取**
```

**✅ 与 §346 的"定向的负面"**同族（**第五次）。**

**⇒ 三层**：

```text
一个负值在 13 位打包字里【不可能】
⇒ 所以它不是"一个负的伤害"
⇒ **而是一次撕裂读**
⇒ **所以返回 0 而不是猜**
```

**✅ 与 §355 的"不猜"**同族（**第十七次"不要猜"**）。

### 5.2 而 **`SV_FallDamageApplied` 的"十五次，十五次 damage-1"**

```cpp
// Fifteen retail landings, fifteen times damage-1. See the declaration
// for the corpus and for what this deliberately does not claim.
return packedDamage ? packedDamage - 1 : 0;
```

**⇒ 四层**：

```text
1. **十五次零售落地，十五次都是 `damage - 1`**
2. ⇒ **见声明了解语料与这个【故意不声称】什么**
4. ⇒ **所以 `packedDamage - 1`（而 0 保持 0）**
```

**✅ 与 §347 的"这是线半而对另一半盲"**第六次"声明边界"。

**⚠ 而"故意不声称"⇒ **所以 15/15 仍不构成"总是 -1"的证明**。**

**✅ 一个**极谨慎的统计表述**。

## 六、`setFactoryWeaponDisplayMotion` 的**三重所有者检查**

```php
// A blank entity is admitted exactly once by spawnFactoryWeaponDisplay.
// Later calls accept only this owner, preventing callers from turning a
// map mover or arbitrary live entity into a weapon display.
if (!entity.mapClassName.empty() && entity.mapClassName != "factory_weapon_display")
    return false;
auto state = entity.networkState;
if (entity.mapClassName == "factory_weapon_display" &&
    (state.eType != EntityTypeScriptMover || state.modelIndex != 0 || entity.collisionLinked))
    return false;
```

### 6.1 六层

```text
1. **一个空白实体只被 `spawnFactoryWeaponDisplay` 接纳【一次】**
2. ⇒ **之后的调用只接受【这个所有者】**
3. ⇒ **防止调用方把一个地图 mover 或任意活实体变成一个武器展示**
4. ⇒ **两级检查**：
     · 若非空而名字不是 `factory_weapon_display` ⇒ 拒
     · 若是 `factory_weapon_display` 而（eType 错 / modelIndex 非零 / collisionLinked）⇒ 拒
5. ⇒ **所以一个"武器展示"必须保持它的三个特征**
```

**✅ 与 §365 的"变形"语义**同族（**第二次"所有者保持身份"**）。

**⚠ 而 `modelIndex != 0` ⇒ **武器展示没有 xmodel**（它用武器装配）。**

**✅ 与 §366 九的"用原生世界武器装配，不写模型指针"**完全一致 ✓

### 6.2 而**"先验证再发布"**

```php
// OLMOD(factory_weapon_display_admission): validate the candidate before
// publishing it or allowing the caller to debit a purchase. The frame
// guard rejects an entire snapshot, not only an invalid display entity.
if (!validScriptMoverEntity(state)) return false;
```

**⇒ 五层**：

```text
1. **在发布它【之前】验证候选**
2. ⇒ **或者在允许调用方扣一次购买之前**
3. ⇒ **因为帧守卫拒绝【整个快照】**
4. ⇒ **不只是拒绝一个无效的展示实体**
5. ⇒ **所以验证必须在扣费之前**
```

**✅ 与 §352 的"一个被拒的生成绝不能花掉一个实体"**同族（**第二次"验证在副作用之前"**）。

## 七、`purchaseZombiePerk` 的**"叠加而不是变异"**

```php
// OLMOD(factory_perk_machines): purchased effects are an overlay on the
// current class, never a mutation of its base modifiers. Reassertions and
// usercmd/snapshot refreshes therefore cannot drop or multiply a purchase.
if (factoryPerkMachinesEnabled_ && word == 0 && (mask & FactoryMachinePerks)) {
    auto &owned = factoryPurchasedPerks_[clientNum];
    if (owned.generation != playerState.spawnGeneration) owned = {playerState.spawnGeneration, 0};
    owned.mask |= mask & FactoryMachinePerks;
    ...
    const auto abilities = effectivePlayerAbilities(clientNum, playerState.spawnGeneration).value();
    if (mask & FactoryPerkArmor) {
        // Recorded purchase changes maxHealth to 250. Preserve existing
        // injury; do not turn the development death-hold option off.
        const auto maximum = (uint32)std::clamp(abilities.resolvedValues[104], 1.0f, 255.0f);
        const auto injury = playerState.maxHealth > playerState.health
            ? playerState.maxHealth - playerState.health : 0;
        playerState.maxHealth = maximum;
        playerState.health = std::max(1u, maximum - std::min(injury, maximum - 1));
    }
    SV_SetNativeAbilityModifiers(client->second.client.nativePlayerState, abilities);
}
```

### 7.1 九层

```text
1. **购买的效果是当前职业上的【一个叠加】**
2. ⇒ **绝不是它的基础修饰符的一次【变异】**
3. ⇒ **所以重新断言与 usercmd/快照刷新【不能丢弃或倍增一次购买】**
4. ⇒ **`factoryPurchasedPerks_` 有代际**
5. ⇒ **代际变 ⇒ 重置**
6. ⇒ **`effectivePlayerAbilities` 合并基础 + 购买**
7. ⇒ **装甲：`maxHealth` 变成 `resolvedValues[104]`（约 250）**
8. ⇒ **保留现有伤害**（`injury = maxHealth - health`）
9. ⇒ **而 `health = max(1, maximum - min(injury, maximum - 1))`**
```

### 7.2 ⭐ **"一个叠加，绝不是一次变异"**

**✅ 与 §352 的"每帧保持 vs 写一次"**第四次。**

**⇒ 三层**：

```text
变异：改基础修饰符 ⇒ **刷新会丢**
叠加：改一个独立的 mask ⇒ **刷新不会丢**
```

**✅ 与 §366 的"永远不创建新的持有武器"**同族的**方法论**。

**⇒ **一个贯穿全文件的架构原则：状态用可重建的叠加表示。**

### 7.3 而**`health` 的算术**

```text
injury   = maxHealth - health                    （现有伤害量）
health'  = max(1, maximum - min(injury, maximum - 1))
```

**⇒ 三层**：

```text
1. 保留伤害量
2. ⇒ **但不超过新的最大血量的 `maximum - 1`**
3. ⇒ **所以 `health' >= 1`**（永不因购买而死亡）
```

**✅ 一个**正确的边界处理**（购买不能杀死你）。

## 八、`beginFrame` 的**"保留上一帧镜像"**

```php
// OLMOD(begin-frame-native-transaction): ClientBegin/ClientSpawn and
// G_RunFrame publish one coherent source/native player generation in
// BO1 and Ghosts. ol-mod owns a separate source model, so retain the
// previous frame image until the fixed CODOL mirror accepts every
// active gclient/gentity mutation. ServerCore must not consume commands
// or run mode/script/end-frame work after this boundary rejects.
```

**⇒ 七层**：

```text
1. **`ClientBegin`/`ClientSpawn` 与 `G_RunFrame` 在 BO1 与 Ghosts 里发布一个【一致的】源/原生玩家代际**
2. ⇒ **ol-mod 拥有一个【独立的源模型】**
3. ⇒ **所以保留上一帧的镜像**
4. ⇒ **直到固定的 CODOL 镜像接受每一个活动 `gclient`/`gentity` 变异**
5. ⇒ **`ServerCore` 绝不能在这个边界拒绝【之后】消费命令或运行模式/脚本/结束帧工作**
6. ⇒ **一个完整的帧级事务边界**
```

**✅ 与 §355 的"`freeEntity` 排队到帧镜像提交之后"**完全同族（**第二次"帧级事务边界"**）。

**⇒ 而这里说**"绝不能在这个边界拒绝之后做任何事"** ⇒ **一个严格的契约**。

**✅ 与 §349 的"事务性"**第七次。

## 九、关键结论

1. **⭐⭐ "按它【是什么】判别，不是按它的 eType"`** —— 画笔模型迁到 `ET_SCRIPTMOVER` 后 **`eType` 测试【别名】了**。
2. **"每一个画笔模型出来时 `solid` 被清零而其 `brushModelIndex` 仍置位 ⇒ 帧验证器的不变式被违反 ⇒ 拒掉每个客户端的整帧"`** —— **`frameReject=entity_domain` 而零快照**。
3. **"客户端坐在 `waiting for player data`"`** —— 与 §360 的"`ack` 冻在 11"、§346 的"`entity_domain reject`"**第三次同一个症状**。
4. **"碰撞形状才是真正分开两者的东西，所以它先走而 eType 测试只看到它一直意味着的东西"`** —— 一个**精确的重构**。
5. **两次 eType 迁移两次事故**：`19→21`（编解码器不同 ⇒ 崩溃）与 `ET_GENERAL→ET_SCRIPTMOVER`（判别别名 ⇒ 零快照）。
6. **`unlinkEntityCollision` 的"配对，与其它一切地方同一个理由"`** —— **第五次配对，而注释已收敛为交叉引用**。
7. **⭐⭐ 血量再生的"边界第一跳"`** —— **`t=101700` 的 22 到 `t=106700` 的 42**（恰好 +5000ms 而**已是一个 100ms 帧的 healing**）。
8. **定量的模型选择：`87%/94%` 对 `71%/86%`** —— 第六次大规模统计。
9. **⭐ "从伤害点推导而不是每帧累积：累积器在 `frameMilliseconds` 不整除速率时会漂移并静默地比零售回得更慢"`** —— 第三次"推导优于累积"。
10. **"在减法之前比较，所以一个短于窗口的 `serverTime` 不能回绕成一个巨大的 elapsed"`** —— 第二次"减法前比较"。
11. **"绝不把血量拿走"`** —— 第二次"永不降血"。
12. **`SV_LandingPainDamage` 的"负值只能是环的一次撕裂读"`** —— 第五次"定向的负面"，第十七次"不要猜"。
13. **`SV_FallDamageApplied` 的"十五次落地十五次 `damage-1`"，而"故意不声称"什么`** —— 第六次"声明边界"。
14. **`setFactoryWeaponDisplayMotion` 的三重所有者检查**（名字 / eType / `modelIndex == 0` / `!collisionLinked`）。
15. **"在发布它之前验证，因为帧守卫拒绝整个快照"`** —— 第二次"验证在副作用之前"。
16. **⭐ `purchaseZombiePerk` 的"一个叠加，绝不是一次变异"`** —— 第四次"临时/叠加 vs 永久/变异"。
17. **`health' = max(1, maximum - min(injury, maximum - 1))`** —— **购买不能杀死你**。
18. **`beginFrame` 的"`ServerCore` 绝不能在这个边界拒绝之后做任何事"`** —— 一个严格的**帧级事务契约**（第七次事务性）。

## 十、未闭合点

- `SvLandingPainDamageShift` / `Mask` 的值。
- `SvHealthRegenDelayMilliseconds` / `SvHealthRegenHealthPerSecond` 的值。
- `resolvedValues[104]` / `[105]` 的语义。
- `FactoryMachinePerks` / `FactoryPerkArmor` 的位。
- `perks[word]` 的三个 word 的完整位表。
- `sv_snapshot_mp.cpp` 18800 行之后未读取（27,016 行，进度 70%）。
