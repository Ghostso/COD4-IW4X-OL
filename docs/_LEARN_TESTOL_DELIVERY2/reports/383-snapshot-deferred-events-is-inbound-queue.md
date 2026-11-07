# 383 · **"`deferredEvents_` 是【入向】的 begin-frame 队列，不是一个额外的 tick 延迟"** —— 四个 append 的队列选择、`eventSequence_` 永不为零、`heads/bodyPart` 的实际代际比较

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 24800–25200 行。

## 二、**`appendEntityDamageEvent` 的 `beforeFrameEventRotation`**（本组最重要的一段）

### 2.1 那段

```php
// OLMOD(headless-frame-event-owner): deferredEvents_ is the incoming
// begin-frame queue, not an extra tick delay for pre-rotation producers.
// Ordinary command damage remains in the current synchronous Lua batch.
// TODO(CODOL): replace this adapter with recovered script notify ownership;
// no native damage probabilities or death timings are inferred here.
// Append after enriching this immutable event with its scoring outcome.
...
(beforeFrameEventRotation ? deferredEvents_ : frameEvents_).push_back(event);
```

### 2.2 九层

```text
1. **`deferredEvents_` 是【入向的】begin-frame 队列**
2. ⇒ **不是一个对"轮换前的生产者"的额外 tick 延迟**
3. ⇒ **普通的命令伤害留在【当前同步的 Lua 批次】里**
4. ⇒ **所以两个队列的语义不同**：
     · `frameEvents_`      **当前帧的（同步）**
     · `deferredEvents_`   **下一帧的（入向）**
5. ⇒ **而 `beforeFrameEventRotation` 选哪个**
6. ⇒ **为真 ⇒ `deferredEvents_`**（轮换之前产生的事件）
7. ⇒ **为假 ⇒ `frameEvents_`**（轮换之后产生的）
```

**✅ 与 §368 的"ZM 回合心跳必须在事件轮换【之后】"**完全闭合 ✓

**⇒ 三层**：

```text
轮换前产生 ⇒ `deferredEvents_` ⇒ **下一帧的 frameEvents_**
轮换后产生 ⇒ `frameEvents_`    ⇒ **当前帧**
```

**✅ 与 §368 的"两行 rotate 事件列表 ⇒ 之前排队的被移进 previousFrameEvents"**完全一致。

**⚠ 而"轮换前"⇒ **所以轮换之后 `deferredEvents_` 被清空**（§368 的 `deferredEvents_.clear()`）。

**✅ **完整闭合。**

### 2.3 而**"普通的命令伤害留在【当前同步】的 Lua 批次里"**

**✅ 与 §349 的"事务性"**第九次。

**⇒ 三层**：

```text
命令伤害（`clientThink` 里）  ⇒ **同步**（在当前 Lua 批次里）
头部衰减 tick（`stepZmDeathFx`）⇒ **在轮换前** ⇒ `deferredEvents_`
```

**✅ 与 §353 的"`appendEntityDamageEvent({cause, health, before}, {}, true, true)`"**完全一致 ✓

**⇒ **第二次确认 `headlessDecay` 的 `true, true` 参数。**

## 三、**`eventSequence_` 的"永不为零"**（本组第二重要）

### 3.1 五处相同的模式

```php
// appendSdEvent / appendEvent / appendPlayerDamageEvent / queueZmRoundTickEvent /
// queuePlayerKilledEvent / appendEntityDamageEvent
++eventSequence_;
if (!eventSequence_)
    ++eventSequence_;
```

**⇒ 六处（含 `appendEntityDamageEvent`）。**

### 3.2 四层

```text
1. **`++eventSequence_`**
2. ⇒ **若回绕到 `0` 则【再 `++`】**
3. ⇒ **所以 `eventSequence_ ∈ [1, UINT32_MAX]`**
4. ⇒ **`0` 是【保留的**】
```

**✅ 与 §382 的"`appendSdEvent` 的同样模式"**第二次确认。

**⇒ **第四次"零是保留的"**（§346 / §382 / §383）。

**⚠ 而**六处重复**⇒ **一处明显的可抽取**。**

**✅ 与 §337 的"两个几乎相同的函数"**第五次。

## 四、**`stageZmDeathFx` 在 append 里的位置**（本组第三重要）

### 4.1 那段

```php
const auto parts = [&]() {
    const auto it = zmDeathFxStates_.find(damageEvent.damage.targetEntityNum);
    if (it == zmDeathFxStates_.end() || it->second.handle.generation != damageEvent.damage.targetGeneration)
        return std::pair{false, false};
    const auto &s = it->second;
    return std::pair{
        s.headless || (s.effect && s.effect == zmDeathFx_.neck),
        s.bodyDamaged || (s.effect && s.effect == zmDeathFx_.torso)};
};
const auto beforeParts = parts();
stageZmDeathFx(damageEvent);
const auto afterParts = parts();
const SvZmFeedbackFacts feedbackFacts{
    .lethal = damageEvent.remainingHealth <= 0,
    .headRemoved = !beforeParts.first && afterParts.first,
    .bodyPartRemoved = !beforeParts.second && afterParts.second,
    .headlessDecay = headlessDecay && beforeParts.first,
    .melee = damageEvent.damage.methodOfDeath == SvMethodOfDeathMelee,
    .headHit = damageEvent.damage.hitLocation == 2,
};
```

### 4.2 十二层

```text
1. **`parts()` 是一个 lambda，先取 `beforeParts`**
2. ⇒ **然后 `stageZmDeathFx(damageEvent)`**
3. ⇒ **然后取 `afterParts`**
4. ⇒ **所以是【前后差分】**
5. ⇒ **而 `parts()` 有两项**：头 / 身体
6. ⇒ **而它【先检查代际匹配】**
7. ⇒ **不匹配 ⇒ 返回 `{false, false}`**
8. ⇒ **所以一个旧的 `zmDeathFxStates_` 条目【不贡献"已移除"**】
9. ⇒ **六个 `feedbackFacts`**：
     · `lethal`（剩余 <= 0）
     · **`headRemoved = !before && after`**（**真正的转换**）
     · **`bodyPartRemoved = !before && after`**
     · **`headlessDecay = headlessDecay && before`**（**只在本已无头**）
     · `melee`
     · `headHit`（`hitLocation == 2`）
```

**✅ ⭐ **"比较【实际的代际拥有的部件转换】，不是单独的`hitGroup`"** —— 一个精确的差分。**

**⇒ 三层**：

```text
朴素：`hitGroup == head` ⇒ "头被移除"
正确：**`!before && after`** ⇒ "头【刚刚】被移除"
⇒ **所以第二次击中头不会重复计数**
```

**✅ 与 §370 的"`371/374` 次读回宿主"**同族（**第二次"前后差分而不是状态"）。**

**⚠ 而 `headlessDecay = headlessDecay && before`⇒ **只在本已无头时**。**

**✅ 与 §353 的"`applyZmHeadLoss` 的 DoT"**完全闭合 ✓

**⇒ **第三次确认那条链。**

### 4.3 而 **`hitHit = hitLocation == 2`**

**⚠ 而 §375 的"`fleshHit` 用 `hitLocation == 4 || 5` 判躯干"。**

**⇒ 所以**`2` 是头**（与 §375 的"1 头盔 / 2 头 / 3 颈 / 4/5 躯干"一致）。**

**✅ **第二次确认那张表。**

## 五、**`zombieBattery_` 的饱和加法**（本组第四重要）

```php
auto &battery = zombieBattery_[*damage.attackerEntityNum];
const auto batteryAward = zmActorNamespaceEnabled_ ? award.battery
    : (damageEvent.remainingHealth <= 0 ? 50u : 10u);
battery = std::min(std::numeric_limits<std::uint32_t>::max() - battery, batteryAward) + battery;
```

### 5.1 五层

```text
1. **两种奖励值**：
     · **ZM ⇒ `award.battery`（从 `SV_ZmDamageAward`）**
     · **非 ZM ⇒ 致命 `50` / 非致命 `10`**
2. ⇒ **饱和加法**：
     · `min(UINT32_MAX - battery, award) + battery`
     · **所以【永不溢出】**
3. ⇒ **而 `UINT32_MAX - battery` 在 `battery` 大时很小**
```

**✅ 与 §366 的"`changeFactoryBattery` 的拒绝而不是饱和"**相反**。**

**⚠ 而两处**不同的溢出策略**：**

```text
§366  脚本请求的电池变更  ⇒ **拒绝**（可观察）
§383  伤害奖励的电池      ⇒ **饱和**（静默）
```

**✅ 一个**精确的区分**（一个可回滚，一个不可）。**

**✅ 与 §362 的"退款必须精确"**配合。

## 六、**`setWeaponAmmoClip` 的六项结果**（本组第五重要）

```cpp
enum class WeaponAmmoMutationResult {
    ClientNotFound, NotPlaying, WeaponNotOwned, AmmoStateMissing, Applied, ...
};
```

### 6.1 而代码路径

```text
① 客户端不存在 ⇒ `ClientNotFound`
② 非 Playing    ⇒ `NotPlaying`
③ 无装备        ⇒ `WeaponNotOwned`
④ 名字找不到武器 ⇒ 查副手（含持有检查）
⑤ 仍找不到      ⇒ `WeaponNotOwned`
⑥ 无对应 clip   ⇒ `AmmoStateMissing`
⑦ 否则 clamp + 应用 ⇒ `Applied`
```

**✅ 与 §366 的"十四项具名拒绝"**同族（**第三次"具名结果"。**

**⚠ 而这里是**枚举返回值**而不是字符串。**

**✅ 一个**更好的可测性**。**

### 6.2 而**副手的 `offhandAmmo` 合成**

```cpp
SvResolvedWeapon offhandAmmo;
if (!weapon) {
    if (const auto *equipment = playerEquipment(clientNum, state.playerState.spawnGeneration)) {
        for (const auto &offhand : equipment->weapons) {
            if (!offhand.weaponAssetIndex || offhand.weaponName != weaponName) continue;
            if (std::ranges::none_of(state.playerState.heldWeapons, [&](const auto &held) {
                    return held.weaponAssetIndex == offhand.weaponAssetIndex; })) continue;
            offhandAmmo.weaponAssetIndex = offhand.weaponAssetIndex;
            offhandAmmo.clipIndex = offhand.clipIndex;
            offhandAmmo.clipSize = offhand.clipCapacity;
            weapon = &offhandAmmo;
            break;
        }
    }
}
```

**⇒ 五层**：

```text
1. **主武器找不到 ⇒ 查副手装备**
2. ⇒ **名字必须匹配**
3. ⇒ **而玩家必须【持有】它**
4. ⇒ **然后【合成】一个 `SvResolvedWeapon`**（只填三个字段）
5. ⇒ **而 `clipSize = clipCapacity`**（副手的容量字段不同）
```

**✅ **一个"就地合成"的适配器**（因为副手的结构不同）。**

**⚠ 而"只填三个字段"⇒ **其它字段为零**。**

**✅ 而后续只用 `clipIndex` ⇒ **所以够了**。**

**✅ 与 §366 的"六个前置"**同族。

### 6.3 而 **`std::clamp<std::int64_t>(count, 0, weapon->clipSize)`**

**⇒ 三层**：

```text
1. **`int64` 的 count**（脚本可能传负数或巨大值）
2. ⇒ **clamp 到 `[0, clipSize]`**
3. ⇒ **然后转 `uint16`**
```

**✅ 与 §381 的"拒绝而不是钳制"**相反**（这里**钳制**）。**

**⚠ 所以**两条不同的策略**：**

```text
§381  游标提示的索引  ⇒ **拒绝**（因为会读别人的数据）
§383  弹药计数        ⇒ **钳制**（因为一个数就是数）
```

**✅ 一个**精确的区分**。

## 七、**`deathAnimationConditions` 的命中位置映射**

### 7.1 那段

```php
// out.exe's hit-location names, 0x00E4FB30: 1 helmet, 2 head, 3 neck,
// 4/5 torso, 12..17 the leg and foot pairs. Everything else -- none, the
// arm and hand pairs, gun, shield -- has no death animation of its own
// and reads as a torso hit, which is what leaves a body on the ground.
if (payload.hitLocation == SvAnimHitLocationHelmetPart || payload.hitLocation == SvAnimHitLocationHeadPart)
    conditions.hitLocation = SvAnimHitLocationHead;
else if (payload.hitLocation == SvAnimHitLocationNeckPart)
    conditions.hitLocation = SvAnimHitLocationNeck;
else if (payload.hitLocation >= SvAnimHitLocationFirstLegPart && payload.hitLocation <= SvAnimHitLocationLastLegPart)
    conditions.hitLocation = SvAnimHitLocationLegs;
```

### 7.2 九层

```text
1. **`out.exe` 的命中位置名（`0x00E4FB30`）**：
     · **`1` 头盔**
     · **`2` 头**
     · **`3` 颈**
     · **`4/5` 躯干**
     · **`12..17` 腿与脚的对**
2. ⇒ **其它一切**（无、臂与手的对、枪、盾）
3. ⇒ **没有自己的死亡动画**
4. ⇒ **读作【躯干命中】**
5. ⇒ **那就是【在地上留下一具身体】的原因**
6. ⇒ **所以三个映射**：
     · 头盔或头 ⇒ `Head`
     · 颈 ⇒ `Neck`
     · `12..17` ⇒ `Legs`
     · **其它 ⇒ 保持默认（躯干）**
```

**✅ **第三次确认那张表。**

**⚠ 而"其它 ⇒ 躯干命中 ⇒ 地上留下一具身体"⇒ **一个极具体的行为**。**

**✅ 与 §375 的"`fleshHit` 用 4/5"**配合。

### 7.3 而 **`methodOfDeath` 的推断**

```php
// TODO(CODOL): the MOD -> DAMAGETYPE mapping is INFERRED. Bullets and
// explosions are unambiguous by name; everything else defaults to
// DAMAGE_BULLET, because a set that matches beats no set at all and
// because inventing a value is how §113b's splash rows went wrong. Exit
// condition: read what the shipped anim script's DEATH sets actually
// condition on.
switch (payload.methodOfDeath) {
case ExplosiveBullet: case Grenade: case Projectile: case Explosive: case Impact:
    conditions.damageType = Explosion; break;
case GrenadeSplash: case ProjectileSplash:
    conditions.damageType = ExplosionLight; break;
...
```

**⇒ 十层**：

```text
1. **MOD → DAMAGETYPE 的映射是【推断的】**
2. ⇒ **子弹与爆炸按名字是明确的**
3. ⇒ **其它一切默认 `DAMAGE_BULLET`**
4. ⇒ **因为一个匹配的集合胜过没有集合**
5. ⇒ **也因为【发明一个值就是 §113b 的 splash 行出错的方式】**
6. ⇒ **退出条件：读已发货的 anim script 的 DEATH 集实际在什么上 condition**
7. ⇒ **五个 ⇒ Explosion**
8. ⇒ **两个 ⇒ ExplosionLight**
```

**✅ 与 §370 的"从反编译读出的常数是一个假设"**同族（**第四次"推断 vs 实测"）。**

**⚠ 而"默认 `DAMAGE_BULLET` 因为一个匹配的集合胜过没有集合"⇒ **一个显式的取舍**。**

**✅ 与 §355 的"更好的是省略而不是错"**不同**（这里**默认一个可能错的值**）。**

**⚠ 一处**潜在矛盾**。**

**⇒ 而理由"发明一个值就是 §113b 出错的方式"⇒ **所以这**不是**发明，而是**一个有意的默认**。**

**✅ 一个**精细的区分**（默认 vs 发明）。

## 八、关键结论

1. **⭐⭐ "`deferredEvents_` 是【入向】的 begin-frame 队列，不是一个额外 tick 延迟"`** —— 与 §368 的"ZM 心跳必须在轮换之后"**完整闭合**。
2. **两个队列的语义**：`frameEvents_`（当前帧同步）/ `deferredEvents_`（下一帧入向）。
3. **"普通的命令伤害留在【当前同步】的 Lua 批次里"`** —— 第二次确认 `headlessDecay` 的 `true, true` 参数。
4. **`eventSequence_` 的"永不为零"在六处重复**（`std::min`… 实为 `++` + 检查）—— 第四次"零是保留的"，而**六处重复是一处明显的可抽取**。
5. **⭐⭐ "比较【实际的代际拥有的部件转换】，不是单独的 `hitGroup`"`** —— `headRemoved = !before && after`，所以**第二次击中头不会重复计数**（第二次"前后差分"）。
6. **`parts()` 先检查代际匹配** ⇒ **一个旧的 `zmDeathFxStates_` 条目不贡献"已移除"**。
7. **六个 `feedbackFacts`** 含 **`headlessDecay = headlessDecay && before`**（只在本已无头）—— 第三次确认那条链。
8. **`hitLocation == 2` 是头**，与 §375 的"1 头盔 / 2 头 / 3 颈 / 4/5 躯干"**一致**。
9. **⭐ `zombieBattery_` 的饱和加法**（`min(UINT32_MAX - battery, award) + battery`）—— 与 §366 的"拒绝而不是饱和"**相反的策略**（一个可回滚、一个不可）。
10. **`WeaponAmmoMutationResult` 的六项具名结果**（枚举而非字符串）—— 第三次"具名结果"，而**这是更好的可测性**。
11. **副手 `offhandAmmo` 的"就地合成"适配器**（只填三个字段，`clipSize = clipCapacity`）。
12. **⭐ `setWeaponAmmoClip` 用 `clamp` 而 §381 的游标提示用"拒绝"`** —— 两条不同策略（一个数就是数 vs 会读别人的数据）。
13. **`out.exe 0x00E4FB30` 的命中位置完整表**：`1` 头盔 / `2` 头 / `3` 颈 / `4/5` 躯干 / `12..17` 腿脚对；**其它一切读作躯干命中**。
14. **"其它 ⇒ 躯干 ⇒ 在地上留下一具身体"`** —— 一个极具体的行为，第三次确认那张表。
15. **⭐ "MOD → DAMAGETYPE 的映射是【推断的】，其它一切默认 `DAMAGE_BULLET`，因为一个匹配的集合胜过没有集合，也因为发明一个值就是 §113b 的 splash 行出错的方式"`** —— 第四次"推断 vs 实测"，而**"默认"与"发明"是一个精细的区分**。

## 九、未闭合点

- `SvWorldEventType` 的完整枚举。
- `SvAnimDamageType` 的完整枚举。
- `§113b` 的 splash 行错误。
- `SV_ZmDamageAward` 的完整评分表。
- `SvReconstructedZmNumberStyle` 的样式。
- `sv_snapshot_mp.cpp` 25200 行之后未读取（27,016 行，进度 93%）。
