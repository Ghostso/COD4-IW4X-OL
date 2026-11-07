# 353 · **`zmDamageRoll` 的拒绝采样**、僵尸死亡的 BO1 六分支、**`113`/`115` 的 effect|(bone<<9) 打包**

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 12800–13200 行。

## 二、`zmGoalRoutable` 的**节点 + 分量双检**（本组第三重要）

```cpp
bool SvServerWorld::zmGoalRoutable(const std::array<float, 3> &goal) const
{
    // The SAME radius the router uses to turn a goal into a node. A goal that
    // does not land on a node has no way on to the graph at all, which is the
    // other half of unroutable.
    const auto node = SV_ZmNavNearestNode(zmNavGraph_, goal, 64.0f);
    if (!node || *node >= zmNavComponent_.size()) return false;
    return zmNavComponent_[*node] == zmNavMainComponent_;
}
```

### 2.1 五层

```text
1. **与路由器把一个目标转成节点用的【同一个】半径**
2. ⇒ **一个落不到节点上的目标根本没有通往图的途径**
3. ⇒ **那是"不可路由"的【另一半】**
4. ⇒ 所以两项：**落到节点 + 在主分量里**
5. ⇒ `64.0f` 是半径
```

**✅ 与 §352 的"`zmNavMainComponent_` 是 1100 里的 837"**配合。**

**⇒ 所以"可路由"= 落在主分量的某个节点 64 单位内。**

**⚠ 而"同一个半径"是一个**必须同步的常数**（路由器与这里）。**

**⇒ 与 §346 的"一个加宽的界只是端口的一半"同族（**两处常数必须一致**）。**

## 三、`zmSpawnCrossesBarrier` 的**四级判定**（本组第四重要）

### 3.1 那段

```php
// OLMOD(window-spawn-eligibility): align selection with map/demo-owned entrance.
// Eligibility must honor the same entrance ownership as stepZombieActors.
// In particular auto414 is explicitly mapped to pf683 from retail demo
// evidence. A plain shortest path can bypass that entrance and formerly
// excluded its spawner before the actor controller ever ran.
const auto measured = zmNavGraph_.spawnBarrierByGoal.find(goal);
if (measured != zmNavGraph_.spawnBarrierByGoal.end())
    return zmBarriers_.contains(measured->second) && zmGoalRoutable(goal);
constexpr float MaximumGoalToBarrierDistanceSquared = 128.0f * 128.0f;
for (const auto &[edge, barrier] : zmBarriers_) {
    const auto &outside = zmNavGraph_.nodes[barrier.outsideNode];
    const auto dx = outside[0] - goal[0], dy = ...;
    if (dx*dx + dy*dy + dz*dz <= MaximumGoalToBarrierDistanceSquared)
        return zmGoalRoutable(goal);
}
const auto start = SV_ZmNavNearestNode(zmNavGraph_, goal, 64.0f);
if (!start) return false;
const auto destination = nearestPlayerNavNode(goal);
if (!destination) return false;
const auto route = SV_ZmNavRoute(zmNavGraph_, *start, *destination);
for (leg = 1; leg < route.size(); ++leg) {
    if (zmBarriers_.contains({from, to}) || zmBarriers_.contains({to, from})) return true;
}
return false;
```

### 3.2 四级（短路顺序）

```text
① 查表：`spawnBarrierByGoal[goal]` 存在 ⇒ 用【表里的】屏障
② 距离：任何一个屏障的 outsideNode 在 128 单位内 ⇒ 直接 true
③ 路由：nearestNode(64) + nearestPlayerNavNode + SV_ZmNavRoute
④ 逐腿：任何一腿的节点对（双向）在 zmBarriers_ 里 ⇒ true
```

### 3.3 七层

```text
1. **在 `stepZombieActors` 里对齐窗口生成资格到【地图/demo 拥有的入口】**
2. ⇒ **资格必须尊重【同一个入口所有权】**
3. ⇒ **特别是 `auto414` 被显式映射到 `pf683`，来自零售 demo 证据**
4. ⇒ **一条纯最短路径可以绕过那个入口**
5. ⇒ **并【以前】在 actor 控制器第一次运行之前就排除了它的生成器**
6. ⇒ 所以有 ① 查表（显式）
7. ⇒ 而 ③④ 是回退（路由）
```

**✅ 与 §349 的"42 个阶段"、§350 的"硬编码号"配合。**

**⚠ 而 `auto414`/`pf683` 是**两个地图实体名**。**

**⇒ 所以这里有一处**显式的地图特定数据**。**

**✅ 与 §350 的 `zm_factory_sh` 硬编码同族。**

### 3.4 而 ② 的**"任何屏障 128 单位内 ⇒ 直接 true"**

**⇒ 三层**：

```text
1. 遍历所有屏障
2. ⇒ **若目标的 128 单位内有一个屏障的 outsideNode**
3. ⇒ **返回 `zmGoalRoutable(goal)`**（而不是 `true`）
```

**⚠ 所以 ② 实际上**只是跳过路由检查**，仍要求可路由。**

**✅ 与 ① 一致（都是 `zmGoalRoutable`）。**

**⇒ **一个目标在屏障附近但仍必须可路由。**

### 3.5 而 ④ 的**双向查**

```cpp
if (zmBarriers_.contains({from, to}) || zmBarriers_.contains({to, from}))
```

**⇒ 三层**：

```text
1. **屏障按它们穿越的节点对键**
2. ⇒ **而图是【无向】的**
3. ⇒ **所以两个顺序都得试**
```

**✅ 一个**正确性细节**。**

## 四、`zmDamageRoll` 的**拒绝采样**（本组第二重要）

### 4.1 完整

```cpp
std::uint32_t SvServerWorld::zmDamageRoll(const std::uint32_t bound)
{
    // Local PRNG, sampled only on accepted damage transitions. Rejection
    // avoids modulo bias. Seed supplied once per map; no native/global RNG.
    std::uint32_t value{};
    const auto limit = (0u - bound) % bound;
    do {
        zmDamageRandom_ = 1664525u * zmDamageRandom_ + 1013904223u;
        // Reversible mixing avoids the LCG low bit alternating torso choices.
        value = zmDamageRandom_ ^ (zmDamageRandom_ >> 16);
    } while (value < limit);
    return value % bound;
}
```

### 4.2 九层

```text
1. **本地 PRNG，只在【被接受的伤害转换】上采样**
2. ⇒ **拒绝采样避免模偏差**
3. ⇒ **种子每图提供一次；没有原生/全局 RNG**
4. ⇒ **LCG 参数 `1664525` / `1013904223`**（Numerical Recipes 的常数）
5. ⇒ **`limit = (0 - bound) % bound`** = `2^32 % bound`
6. ⇒ **拒绝 `value < limit`**
7. ⇒ **返回 `value % bound`**
8. ⇒ **可逆混合避免 LCG 低位交替地选择躯干**
9. ⇒ `value = state ^ (state >> 16)`
```

### 4.3 而 **`(0u - bound) % bound` 是 `2^32 % bound`**

**⇒ 三层**：

```text
1. `0u - bound` 在无符号下 = `2^32 - bound`
2. ⇒ `(2^32 - bound) % bound = 2^32 % bound`  （因为 `bound % bound = 0`）
3. ⇒ **所以在 `[0, 2^32)` 里均匀时，`value % bound` 的偏差只来自前 `limit` 个值**
```

**✅ 一个**教科书级正确的拒绝采样**。**

**⚠ 而 `2^32 % bound` 对 `bound ∈ {2, 100, 471}` 的值：**

```text
bound = 2      ⇒ 0        （无拒绝）
bound = 100    ⇒ 96       （拒绝 96 个值）
bound = 471    ⇒ ？
```

**⚠ 而 `bound = 2` 时 **`limit = 0`** ⇒ **循环一次就退出 ✓**

**✅ 而 `xorshift` 混合使 `value` 均匀 ⇒ 所以拒绝采样正确。**

### 4.4 而 **"可逆混合避免 LCG 低位交替"**

**✅ 一个**极精细的观察**。**

**⇒ 三层**：

```text
1. LCG 的低位在模 2^k 下**周期极短**（纯 LCG 低位周期 = 2^k）
2. ⇒ **所以 `state & 1` 会严格交替**（因为乘数是奇数而增量是奇数）
3. ⇒ **而 `zmDeathFx_.torso` 的选择用 `zmDamageRoll(2) == 0`**
4. ⇒ **⇒ 躯干/内脏的选择会严格交替**
```

**⚠ 所以注释说"避免 LCG 低位交替地选择躯干"。**

**✅ 一个**真实的、具体的 PRNG 缺陷**被规避。**

**⚠ 而"可逆"指 `x ^ (x >> 16)` 是可逆的（xorshift 混合）。**

**✅ 一个**高质量的选择**。**

### 4.5 而**"只在被接受的伤害转换上采样"**

**⇒ 三层**：

```text
1. 只在接受的伤害上调用
2. ⇒ **所以被拒的帧不消耗 PRNG**
3. ⇒ **⇒ 同样的输入序列给出同样的输出**（确定性）
```

**✅ 与 §349 的"事务性投递"、§352 的"每帧保持"**同族（**第五次"事务性"**）。**

**⇒ **确定性 = 可复现 = 可调试。**

## 五、`setZmPresentation` 的**两处截断**

```cpp
void SvServerWorld::setZmPresentation(std::span<const SvZmOutfit> outfits,
    std::span<const SvZmDeathClip> deaths, SvZmDeathFx fx)
{
    zmOutfits_.clear(); zmDeaths_.clear();
    zmDeathFxStates_.clear();
    zmFaceGlowStates_.clear(); zmFaceGlowDiagnosticCount_ = 0;
    zmDeathFx_ = std::move(fx);
    zmDeathFx_.refined = zmDeathFx_.refined && zmDeathFx_.bo1Derived;
    for (auto *effect : {&zmDeathFx_.neck, &zmDeathFx_.torso, &zmDeathFx_.shock, &zmDeathFx_.shockEyes})
        if (*effect >= 400) *effect = 0;
    zmDamageRandom_ = zmDeathFx_.randomSeed ? zmDeathFx_.randomSeed : 1;
    zmHeadFrame_ = zmHeadsThisFrame_ = 0;
    zmDeathFxDiagnosticCount_ = 0;
    zmOutfitSequence_ = zmDeathSequence_ = 0;
    for (const auto &o : outfits)
        if (o.body > 0 && o.body < 1024 && o.head > 0 && o.head < 1024 && zmOutfits_.size() < 15)
            zmOutfits_.push_back(o);
    for (const auto &c : deaths)
        if (SV_ZmValidDeathClip(c) && zmDeaths_.size() < 7) zmDeaths_.push_back(c);
}
```

### 5.1 五项

```text
① `refined` 只在 `bo1Derived` 时可为真
② **四个 effect 索引 `>= 400` ⇒ 归零**
③ **种子：`randomSeed` 或 1**
④ **outfits：`body/head ∈ (0, 1024)` 且最多 15 个**
⑤ **deaths：`SV_ZmValidDeathClip` 且最多 7 个**
```

### 5.2 而 **`>= 400` 的界**

**⇒ 三层**：

```text
1. effect 索引必须 < 400
2. ⇒ **否则归零（"没有效果"）**
3. ⇒ **而不是拒绝整个 fx**
```

**✅ 与 §344 的"更好的是省略而不是错"**同族（**第十二次**）。**

**⚠ 而**`400` 与 `1024`（模型）与 `2046`（EntityNumWorld）是不同的边界。**

**⇒ 三个不同的号空间。**

### 5.3 而 **15 个 outfit、7 个 death clip**

**⇒ 三层**：

```text
1. **最多 15 个装扮**
2. ⇒ **最多 7 个死亡片段**
3. ⇒ **超出则静默丢弃**
```

**⚠ 而"15"可能是**客户端的能力上限**（`actorModelIndex` 的选择集？）。**

**✅ 与 §344 的 `ActorCorpseRingSize`（四槽环）**不同。**

## 六、`applyZmHeadLoss` 的**五个门**（本组第五重要）

```cpp
void SvServerWorld::applyZmHeadLoss(ZmDeathFxState &state, const std::uint32_t now)
{
    if (state.headless || !state.outfit.behead || !zmDeathFx_.neck || state.outfit.neckBone == 255) return;
    if (zmHeadFrame_ != now) { zmHeadFrame_ = now; zmHeadsThisFrame_ = 0; }
    if (zmHeadsThisFrame_ >= 4) { state.pendingHead = false; return; }
    ++zmHeadsThisFrame_;
    state.headless = true; state.pendingHead = false;
    state.attachment0 = state.outfit.behead;
    state.applied = false;
    state.emissions[0] = { zmDeathFx_.neck, state.outfit.neckBone, now + 50 };
    const auto health = entityDamageStates_.find(state.handle.entityNum);
    if (health != entityDamageStates_.end() && health->second.health > 0) {
        // BO1 damage_over_time: 20% of health at head loss each second.
        // Integer health adaptation rounds up so low-health actors terminate.
        state.dotDamage = std::max(1, (health->second.health + 4) / 5);
        state.dotAt = now + 1000;
    }
}
```

### 6.1 六层

```text
1. **四个前置门**：已无头 / 无 behead 模型 / 无 neck 效果 / neckBone==255
2. ⇒ **【每帧最多 4 个断头】**（`zmHeadsThisFrame_ >= 4`）
3. ⇒ **超过则清 `pendingHead` 并返回**
4. ⇒ **设无头、设 attach0、清 `applied`（触发重新发布）**
5. ⇒ **`emissions[0]` = neck 效果 + neckBone + `now + 50`**
6. ⇒ **DoT：`max(1, (health + 4) / 5)`** = **20% 向上取整**
```

### 6.2 而**"每帧最多 4 个断头"**

**✅ 与 §347 的"四槽环"**不同**（那是事件环容量）。**

**⚠ 而这里也是 **4**。**

**⇒ 可能因为**四槽事件环每帧只能承载四个新事件**。**

**✅ **一个合理的容量约束。**

**⚠ 而"超过则清 `pendingHead`"⇒ **永久放弃**（不是延期）。**

**⇒ 所以第 5 个及之后的断头**永远不会发生**。**

**⚠ 一处**有意的取舍**（可能因为特效风暴更糟）。**

### 6.3 而 **`(health + 4) / 5` 的向上取整**

**⇒ 三层**：

```text
1. `(h + 4) / 5` 是整数除法
2. ⇒ **对 `h = 5k` ⇒ `k`**（精确 20%）
3. ⇒ **对 `h = 5k+r` ⇒ `k+1`**（向上取整）
4. ⇒ **而 `max(1, ...)` 保证至少 1**
```

**✅ 与注释的"整数健康适配向上取整以便低健康 actor 终止"完全一致 ✓**

**⇒ 若向下取整，`h = 4` ⇒ **0** ⇒ **永不死亡**。**

**✅ 一个**真实的"否则永不死"陷阱**被规避。**

## 七、`stageZmDeathFx` 的**六分支**（本组最重要的一段）

### 7.1 六个前置

```cpp
if (damage.damage <= 0 || !entityPool_ || !entityPool_->resolve(handle)) return;
const auto found = entities_.find(handle.entityNum);
if (found == entities_.end() || found->second.mapClassName != "zombie_actor" ||
    found->second.networkState.eType != EntityTypeActor) return;
```

**⇒ 六项**：伤害 > 0 / 池存在 / 句柄可解析 / 实体存在 / **`mapClassName == "zombie_actor"`** / **`eType == EntityTypeActor`**。

**✅ 与 §344 的"`validActorEntity`"配合。**

**⚠ 而 `mapClassName` 是**字符串比较** ⇒ 所以"僵尸"是一个**类名**而不是一个 eType。**

**✅ 一个**额外的区分**（actor 可以是别的东西？）。**

### 7.2 而 **outfit 的二级查找**

```cpp
const auto outfit = existing != zmDeathFxStates_.end() && existing->second.outfit.body
    ? existing->second.outfit
    : [&] {
        const auto it = std::ranges::find(zmOutfits_, actor.actorModelIndex, &SvZmOutfit::body);
        return it == zmOutfits_.end() ? SvZmOutfit{} : *it;
    }();
if (!outfit.body) return;
```

**⇒ 四层**：

```text
1. **若已有 state 且它的 outfit 有 body ⇒ 用它**（保持一致性）
2. ⇒ **否则按 `actorModelIndex` 在 `zmOutfits_` 里找**
3. ⇒ **找不到 ⇒ 空 outfit**
4. ⇒ **空 ⇒ 返回**（不做特效）
```

**✅ 一个**稳定的装扮绑定**（第一次选定后就固定）。**

**⚠ 而注释在 §7.4 说"BO1 资格不确立 CODOL 零售几率"。**

### 7.3 而**三个命中判定**

```cpp
const auto valid = [](uint16_t n) { return n > 0 && n < 1024; };
const bool head = damage.hitLocation == SvAnimHitLocationHeadPart ||
    damage.hitLocation == SvAnimHitLocationHelmetPart ||
    damage.hitLocation == SvAnimHitLocationNeckPart;
const bool torso = damage.hitLocation == 4 || damage.hitLocation == 5;
const bool bullet = SV_IsBulletPaintMethodOfDeath(damage.methodOfDeath);
```

**⇒ 三层**：

```text
head    三个具名常量（头/头盔/颈）
torso   **两个裸数字 4 与 5**
bullet  `SV_IsBulletPaintMethodOfDeath`
```

**⚠ 所以 `head` 用**具名常量**而 `torso` 用**裸数字**。**

**⇒ 一处**不一致**（可能是历史遗留）。**

**✅ 与 §339 的"裸整数索引对工具不可见"**同族（**第三次裸整数问题**）。**

### 7.4 而 **AN 回退（`!zmDeathFx_.bo1Derived`）**

```php
// Preserved AN fallback; all BO1 policy is behind the explicit opt-in.
if (event.remainingHealth > 0 || !bullet || existing != zmDeathFxStates_.end()) return;
ZmDeathFxState state{.handle = handle};
if (head && zmDeathFx_.neck && valid(outfit.behead) && outfit.neckBone < 255) {
    state.body = outfit.body; state.attachment0 = outfit.behead;
    state.effect = zmDeathFx_.neck; state.bone = outfit.neckBone;
}
else if (torso && zmDeathFx_.torso && valid(outfit.torso) && valid(outfit.lower) && outfit.torsoBone < 255) {
    state.body = outfit.torso; state.attachment0 = outfit.head; state.attachment1 = outfit.lower;
    state.effect = zmDeathFx_.torso; state.bone = outfit.torsoBone;
}
else return;
state.ignoreCollision = 1;
zmDeathFxStates_.emplace(handle.entityNum, state); return;
```

**⇒ 七层**：

```text
1. **保留的 AN 回退；全部 BO1 策略在一个显式 opt-in 后面**
2. ⇒ **三个前置：剩余健康 > 0 / 非子弹 / 已有 state** ⇒ 返回
3. ⇒ **头分支：body + behead + neck 效果 + neckBone**
4. ⇒ **躯干分支：torso + head + lower + torso 效果 + torsoBone**
5. ⇒ **否则返回**（不认识的命中部位）
6. ⇒ **`ignoreCollision = 1`**
7. ⇒ **每个实体只做一次**（`existing != end` 就返回）
```

**✅ 一个**极简的两分支**（vs BO1 的六分支）。**

### 7.5 而 **BO1 的四个前置**

```cpp
const bool player = damage.attackerEntityNum && clientStates_.contains(*damage.attackerEntityNum);
const bool excluded = std::ranges::find(zmDeathFx_.excludedWeapons, damage.weaponAssetIndex) != ...end();
const bool electrical = std::ranges::find(zmDeathFx_.electricalWeapons, damage.weaponAssetIndex) != ...end();
if (!player || excluded || !damage.weaponAssetIndex) return;
const auto before = event.previousHealth > 0 ? event.previousHealth
    : clamp<i64>(remainingHealth + damage.damage, 1, INT32_MAX);
if (!electrical && (!bullet || !SV_ZmBo1DamageThreshold(damage.damage, before))) return;
```

**⇒ 六层**：

```text
1. **`player`：攻击者是一个客户端**（不是另一个 actor）
2. ⇒ **`excluded`：武器在排除表里**
3. ⇒ **`electrical`：武器在电击表里**
4. ⇒ **三者任一不满足 ⇒ 返回**
5. ⇒ **`before` = `previousHealth` 或（剩余 + 伤害）**
6. ⇒ **非电击 ⇒ 必须子弹且伤害过阈值**
```

**✅ 与 §349 的"整场速率"配合。**

**⚠ 而 `player` 要求**攻击者是玩家** ⇒ 所以 **actor 杀 actor 不做特效**。**

**✅ 一个**有意的限制**。**

### 7.6 而**电击分支**

```cpp
if (electrical) {
    // A real configured weapon ID, NEVER a randomly selected Tesla clip.
    if (state.electrical || event.remainingHealth > 0) return;
    state.electrical = true; state.headCause = damage;
    if (!zmDeathFx_.refined && zmDeathFx_.shock && outfit.shockBone < 255)
        state.emissions[2] = {zmDeathFx_.shock, outfit.shockBone, now + 50};
    if (!state.headless && zmDamageRoll(100) < 50) {
        state.pendingHead = true; state.headDue = now + 530 + zmDamageRoll(471);
        log("tesla-head-pending");
    } else {
        if (zmDeathFx_.shockEyes && outfit.eyeBone < 255)
            state.emissions[3] = {zmDeathFx_.shockEyes, outfit.eyeBone, now + 50};
        log("tesla-eyes");
    }
    return;
}
```

**⇒ 八层**：

```text
1. **一个真实配置的武器 ID，【绝不】是一个随机选的 Tesla 片段**
2. ⇒ **已电击 或 还活着 ⇒ 返回**
3. ⇒ **设 electrical 与 headCause**
4. ⇒ **非 refined ⇒ 发 shock 效果**（`emissions[2]`）
5. ⇒ **50% ⇒ 断头待发，延迟 `530 + roll(471)` ms**（⇒ 530..1000ms）
6. ⇒ **否则 ⇒ shockEyes 效果**（`emissions[3]`）
```

**⚠ 而 `530 + roll(471)` ⇒ `[530, 1000]`。**

**✅ 一个**精确的延迟范围**。**

**⚠ 而"50%"来自 `zmDamageRoll(100) < 50` ⇒ **半个区间**。**

**✅ 而 `bound = 100` 而阈值 50 ⇒ **精确的 50%。**

### 7.7 而**头分支**

```cpp
if (head) {
    if (!state.headless && SV_ZmBo1HeadThreshold(event.remainingHealth, state.maxHealth)) {
        state.headCause = damage; applyZmHeadLoss(state, now); log("head");
    }
    return; // Ineligible head hits must not randomly damage the torso.
}
```

**⇒ 四层**：

```text
1. **未无头 且 过头部阈值**
2. ⇒ **设 headCause 并施加断头**
3. ⇒ **返回**
4. ⇒ **不合资格的头部命中绝不能随机损坏躯干**
```

**✅ 与 §353 六的"四槽环"配合。**

**⚠ 而"不返回会让头命中落到躯干分支"是一个**真实的 bug 模式**。**

### 7.8 而**躯干/手臂分支**

```cpp
const int arm = zmDeathFx_.refined ? SV_ZmArmSide(damage.hitLocation) : 0;
if ((torso || arm) && !state.bodyDamaged && zmDeathFx_.torso && valid(outfit.lower)) {
    // CODDIFF(actor_head_attachment): CODOL supplies cyborg multipart
    // variants, rather than BO1 flesh gibs. An arm hit retains its side;
    // only torso hits use the original BO1 guts/right-arm choice.
    const bool guts = arm == 0 && zmDamageRoll(2) == 0;
    const auto model = guts ? outfit.torso : (arm < 0 ? outfit.leftArmOff : outfit.rightArmOff);
    const auto bone = guts ? outfit.torsoBone : (arm < 0 ? outfit.leftArmBone : outfit.rightArmBone);
    // Missing selected variants are not silently converted into guts.
    if (!valid(model) || bone == 255) { log("body-asset-missing"); return; }
    state.bodyDamaged = true; state.body = model; state.attachment1 = outfit.lower;
    state.applied = false; state.emissions[1] = {zmDeathFx_.torso, bone, now + 50};
    log(guts ? "guts" : (arm < 0 ? "left-arm" : "right-arm"));
}
```

**⇒ 十层**：

```text
1. **`arm` 只在 refined 时判定**（否则 0 = 躯干）
2. ⇒ 前置：躯干或手臂 / 未损坏 / 有 torso 效果 / 有 lower 模型
3. ⇒ **CODOL 提供【赛博格多部件变体】而不是 BO1 的血肉碎块**
4. ⇒ **手臂命中保留它的【侧】**
5. ⇒ **只有躯干命中用原来的 BO1 内脏/右臂选择**
6. ⇒ **`guts = arm == 0 && roll(2) == 0`**
7. ⇒ **缺选的变体【不被静默转成内脏】**
8. ⇒ 所以 `if (!valid(model) || bone == 255) log("body-asset-missing"); return;`
9. ⇒ 否则设 body/attach1/清 applied/emissions[1]
```

**✅ 与 §353 四.4 的"LCG 低位交替"**完全闭合 ✓**

**⇒ 因为 `roll(2)` 用拒绝采样 + xorshift ⇒ **不会交替**。**

**✅ **两个注释互相印证。**

### 7.9 而**"缺选的变体不被静默转成内脏"**

**✅ 与 §344 的"更好的是省略而不是错"**第三次（第十三次）。**

**⇒ 三层**：

```text
1. 手臂命中而手臂模型缺失
2. ⇒ **不退回内脏**（那是另一个模型）
3. ⇒ **什么都不做并记日志**
```

**✅ **一个正确的"不要猜"**。**

## 八、`stepZmDeathFx` 的**两个发布顺序约束**（本组第六重要）

```php
// OLMOD(death_fx_lifetime): publish models before their bone events, bound
// emissions and headless damage ticks, and retain native corpse ownership.
if (zmDeathFx_.bo1Derived) {
    if (state.pendingHead && now >= state.headDue) applyZmHeadLoss(state, now);
    if (!state.applied) {
        entity.networkState.actorModelIndex = state.body;
        entity.networkState.actorAttachModelIndex0 = state.attachment0;
        state.applied = true; state.modelAt = now;
        for (auto &fx : state.emissions) if (fx.effect && !fx.played) fx.due = std::max(fx.due, now + 50);
    }
    for (auto &fx : state.emissions) { ... }
    ...
}
```

### 8.1 四层

```text
1. **在它们的骨骼事件【之前】发布模型**
2. ⇒ **有界地发效果与无头伤害 tick**
3. ⇒ **保留原生的尸体所有权**
4. ⇒ 所以 `state.applied` 后**把所有 emission 的 due 推到 `now + 50`**
```

**✅ 与 §347 的"THE TIME FIRST"**同族（**顺序约束**）。**

**⇒ **"模型必须先于其骨骼事件"** 是一个**客户端的时序要求**。**

### 8.2 而**`max(fx.due, now + 50)`**

**⇒ 三层**：

```text
1. `fx.due` 可能已经是一个更晚的值
2. ⇒ **`max` 保留更晚的**
3. ⇒ **所以不提前**
```

**✅ 与 §343 的 `bump` 用 `max`**同族（**第二次 `max` 累积**）。**

### 8.3 而**事件 `113`（play）/ `115`（stop）**

```cpp
queueActorPresentationEvent(state.handle,
    {113, (int32)(fx.effect | ((uint32)fx.bone << 9))})
...
queueActorPresentationEvent(state.handle,
    {115, (int32)(fx.effect | (255u << 9))})
```

**⇒ 三层**：

```text
1. **事件 113 = 播放，115 = 停止**
2. ⇒ **参数是 `effect | (bone << 9)`**
3. ⇒ **停止时 bone = 255**
```

**✅ 与 §347 的"`0x98..0x9F` 脚步"**不同**（那是实体事件环）。**

**⚠ 而 `bone << 9` ⇒ **9 位偏移** ⇒ 所以 `effect` 占低 9 位（0..511）。**

**⇒ 与 §353 五.2 的 `>= 400 ⇒ 归零` 配合（**400 < 512** ✓）。**

**✅ **完整闭合：effect 必须 < 512 而配置时限制为 < 400。** **

### 8.4 而**停止用 `255`**

**⇒ 三层**：

```text
1. `bone` 是 `uint8`（0..255）
2. ⇒ **255 是一个"无骨骼"哨兵**
3. ⇒ **而 §353 六.1 的 `neckBone == 255` 是"无颈骨"**
```

**✅ **同一个 255 两个用途**（无骨骼 / 非法）。**

**⚠ 而 `outfit.*Bone < 255` 的检查与这里一致 ✓**

### 8.5 而**DoT 的 `cannotDie` 处理**

```cpp
const auto before = health->second.health;
const auto amount = health->second.cannotDie
    ? std::min(state.dotDamage, before - 1)
    : std::min(state.dotDamage, before);
state.dotAt = now + 1000;
if (amount > 0) {
    health->second.health -= amount;
    auto cause = state.headCause; cause.damage = amount;
    cause.methodOfDeath = SvMethodOfDeathUnknown;
    // Unknown prevents recursively dismembering on bleed damage.
    appendEntityDamageEvent({cause, health->second.health, before}, {}, true, true);
}
```

**⇒ 七层**：

```text
1. **`cannotDie` ⇒ 至少留 1 点血**（`min(dotDamage, before - 1)`）
2. ⇒ **否则可以降到 0**
3. ⇒ **`dotAt = now + 1000`**（每秒一次）
4. ⇒ **只在实际扣血时发事件**
5. ⇒ **`methodOfDeath = Unknown`**
6. ⇒ **"Unknown 防止在流血伤害上递归肢解"**
7. ⇒ **这是第 8 次"沉默读起来像健康"的对策**（一个递归防护）
```

**✅ 与 §353 七.7 的"头命中必须返回"**同族（**第二次显式防递归**）。**

## 九、`stepZmFaceGlow` 的**`intact` 五项**

```cpp
const bool intact = health != entityDamageStates_.end() && health->second.health > 0 &&
    n.actorAttachModelIndex0 == o.head &&
    (n.actorModelIndex == o.body || (o.torso && n.actorModelIndex == o.torso) ||
     (o.rightArmOff && n.actorModelIndex == o.rightArmOff) ||
     (o.leftArmOff && n.actorModelIndex == o.leftArmOff));
```

**⇒ 五项**：

```text
① 有伤害状态
② **血量 > 0**
③ **attach0 == head**（头还在）
④ **主模型是 body / torso / 右臂 / 左臂 之一**
⑤ 每帧换模型 ⇒ 重新判定
```

**✅ 与 §353 七.8 的"手臂/躯干变体"**完全一致 ✓**

**⇒ 所以 `intact` 覆盖全部四个身体变体。**

### 9.1 而**"换模型 ⇒ 停止 glow"**

```cpp
const bool changed = s.body != n.actorModelIndex || s.head != n.actorAttachModelIndex0;
...
if (!intact || changed) {
    for (unsigned i = 0; i < 2; ++i) if (s.playing[i] && emit(i, false)) s.playing[i] = false;
    if (s.playing[0] || s.playing[1]) return;
    s.body = n.actorModelIndex; s.head = n.actorAttachModelIndex0; s.due = now + 100;
    if (!intact) { zmFaceGlowStates_.erase(it); return; }
    return;
}
```

**⇒ 五层**：

```text
1. **模型变了或不再完整 ⇒ 停止两个 glow**
2. ⇒ **两个都停了才继续**
3. ⇒ **记录新模型与 head**
4. ⇒ **`due = now + 100`**（100ms 后才可能重播）
5. ⇒ **不完整 ⇒ 删除状态**
```

**✅ 一个**"先停后启"的两阶段**。**

**⚠ 而 `if (s.playing[0] || s.playing[1]) return;` ⇒ **若一个还没停成功就返回**。**

**⇒ 所以**下一帧再试**（事件队列满时）。**

**✅ 与 §353 六.2 的"四槽环"配合。**

## 十、关键结论

1. **`zmGoalRoutable` = 落到节点（64 单位）+ 在主分量里** —— 与路由器**同一个半径**（两处必须同步）。
2. **`zmSpawnCrossesBarrier` 的四级判定**，而 ① 是**显式的地图特定条目**（`auto414 → pf683`）。
3. **① 与 ② 都最终调 `zmGoalRoutable`** ⇒ 屏障附近但仍必须可路由。
4. **④ 双向查节点对**（图无向）。
5. **⭐ `zmDamageRoll` 的拒绝采样**（`limit = 2^32 % bound`），LCG + xorshift 混合。
6. **"可逆混合避免 LCG 低位交替地选择躯干"** —— 一个**真实且具体**的 PRNG 缺陷被规避。
7. **"只在被接受的伤害转换上采样"** ⇒ 不消耗 PRNG ⇒ 确定性（第五次事务性）。
8. **`setZmPresentation` 的两处截断**：effect `>= 400 ⇒ 0`；outfits ≤ 15；deaths ≤ 7。
9. **`applyZmHeadLoss` 的四个前置 + "每帧最多 4 个断头"**（超则**永久放弃** `pendingHead`）。
10. **`(health + 4) / 5` 的向上取整是必须的** —— 向下取整时 `h=4 ⇒ 0` ⇒ **永不死**。
11. **`stageZmDeathFx` 的六项前置**，其中 **`mapClassName == "zombie_actor"` 是字符串检查**。
12. **装扮第一次选定后固定**（已有 state 的 outfit 优先）。
13. **`head` 用三个具名常量而 `torso` 用两个裸数字 4/5** —— 一处不一致（第三次裸整数）。
14. **AN 回退只有两分支**（头/躯干），而 **BO1 有六分支**。
15. **BO1 的四个前置**：攻击者是玩家 / 非排除武器 / 非零武器 / 电击或（子弹 + 过阈值）。
16. **"actor 杀 actor 不做特效"** —— 一个有意的限制。
17. **电击分支：50% 断头（延迟 530..1000ms）否则 shockEyes**。
18. **"一个真实配置的武器 ID，绝不是一个随机选的 Tesla 片段"**。
19. **"不合资格的头部命中绝不能随机损坏躯干"** —— 一个真实的 bug 模式。
20. **CODOL 提供赛博格多部件变体而不是 BO1 血肉碎块**，而**手臂命中保留它的侧**。
21. **"缺选的变体不被静默转成内脏"** —— 第十三次"不要猜"。
22. **`stepZmDeathFx` 的两个顺序约束**：模型先于骨骼事件、emission 的 due 用 `max` 累加。
23. **事件 `113`（play）/ `115`（stop），参数 `effect | (bone << 9)`，停止时 bone = 255**。
24. **`effect` 占低 9 位（< 512）而配置时限制 < 400** —— **完整闭合**。
25. **`255` 同时是"无骨骼"与"非法骨骼"**。
26. **DoT 的 `cannotDie` 至少留 1 点血**，而 **`methodOfDeath = Unknown` 防递归肢解** —— 第二次显式防递归。
27. **`stepZmFaceGlow` 的 `intact` 五项**覆盖全部四个身体变体，而**换模型 ⇒ 先停后启**。

## 十一、未闭合点

- `SvAnimHitLocation` 的完整表（为什么 torso 用裸 4/5）。
- `zmOutfits_` 上限 15、`zmDeaths_` 上限 7 的来源。
- `auto414 → pf683` 的 demo 证据。
- `SV_ZmBo1HeadThreshold` / `SV_ZmBo1DamageThreshold` 的阈值。
- `zmBarriers_` 的构建方式。
- `sv_snapshot_mp.cpp` 13200 行之后未读取（27,016 行，进度 49%）。
