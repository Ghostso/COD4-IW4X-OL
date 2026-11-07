# 362 · **"`0x80000` 是客户端的『重新初始化这具尸体』标志"** —— 每秒重置 20 次而永不动画、`±36 / [-88,+18]` 的拾取盒、`300ms` 的全都 145 个

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 16400–16800 行。

## 二、**领奖台相机的类型 7 → 4**（本组第四重要）

```cpp
// Native type 7 is the measured accelerating trajectory. At its 500 ms
// endpoint BG_EvaluateTrajectory adds delta * durationSeconds / 2.
constexpr float AcceleratedDisplacement = 0.25f;
for (axis) {
    state.origin[axis] += state.positionTrajectoryDelta[axis] * AcceleratedDisplacement;
    state.angles[axis] += state.angleTrajectoryDelta[axis] * AcceleratedDisplacement;
}
entity.currentOrigin = state.origin;
entity.currentAngles = state.angles;
state.positionTrajectoryType = 4;
state.positionTrajectoryTime = trajectoryStartTime;
state.positionTrajectoryDuration = 16'500;
state.angleTrajectoryType = 4;
state.angleTrajectoryTime = trajectoryStartTime;
state.angleTrajectoryDuration = 16'500;
```

### 2.1 七层

```text
1. **原生类型 7 是【测量的加速轨迹】**
2. ⇒ **在它 500ms 的端点，`BG_EvaluateTrajectory` 加上 `delta * durationSeconds / 2`**
3. ⇒ **`durationSeconds = 0.5` ⇒ `delta * 0.25`**
4. ⇒ **所以 `AcceleratedDisplacement = 0.25`**
5. ⇒ **然后切到类型 4**（速度恒定）
6. ⇒ **时长 `16'500`ms = 16.5 秒**
7. ⇒ **所以 0.5 秒加速 + 16.5 秒匀速 = 17 秒总行程**
```

**✅ 与 §361 九的"`CameraMotionSeconds = 17.0f`"**完全闭合 ✓**

**⇒ `0.5 + 16.5 = 17.0` ✓**

**✅ **一个精确的两阶段分解。**

### 2.2 而**"加速轨迹的端点位移是 `delta * t/2`"**

**✅ 三层**：

```text
1. 匀加速：位置 = ½ a t²，而 delta 若理解为"末速度"
2. ⇒ **则 ½ v t**
3. ⇒ **所以 `delta * durationSeconds / 2`**
```

**✅ 一个**物理上正确的公式**。**

**⚠ 而 `delta` 在这里是**末速度**而不是**平均速度**。**

**⇒ 与 §354 的"`delta = Δ / duration`"（那是**平均**）**不同**。**

**⚠ 所以**同一个 `delta` 字段两种语义**（取决于 `type`）。**

**✅ 与 §342 的"`type` 决定编解码器"**同族。

## 三、**`spawnScavengerBag` 的完整实测**（本组第三重要）

### 3.1 那段

```php
// MEASURED (retail dm, entity 255 at 52800): the pack enters as
// ET_ITEM / trType 3 with a 50 ms trajectory, scale 1, item row 902,
// and the dead player in +0x84. At 53700 that owner becomes 2045;
// the bag is picked up at 56400. A second dropped-weapon item from the
// same death remains for exactly 60 seconds, which supplies the common
// item lifetime used here when nobody can refill from the pack.
auto &network = entity.networkState;
network.eType = EntityTypeItem;
network.origin = victim->second.client.playerState.origin;
network.angles = { 0.0f, victim->second.client.playerState.viewAngles[1], 0.0f };
network.positionTrajectoryType = 3;
network.positionTrajectoryTime = snapshot_.serverTime;
network.positionTrajectoryDuration = 50;
const auto yaw = network.angles[1] * (pi/180);
network.positionTrajectoryDelta = { cos(yaw)*70.0f, sin(yaw)*70.0f, -64.0f };
network.angleTrajectoryType = 0;
network.groundEntityNum = EntityNumWorld;
// +0x9C is ET_ITEM's 12-bit item/weapon asset field.
network.scriptMoverBrushModelIndex = itemWeaponAssetIndex;
network.otherEntityNum = (uint16)victimClientNum;
network.modelScale = 1.0f;
```

### 3.2 十四层

```text
1. **测量（零售 dm，实体 255 在 52800ms）**：
     · **包裹以 `ET_ITEM` / trType 3 / 50ms 轨迹进入**
     · **scale 1**
     · **物品行 902**
     · **而死亡玩家在 `+0x84`**
2. ⇒ **在 53700 那个拥有者变成 `2045`**
3. ⇒ **包裹在 56400 被拾取**
4. ⇒ **同一次死亡的第二个掉落武器物品【恰好留 60 秒】**
5. ⇒ **那提供了这里在没有人能从包裹补充时使用的【常见物品生命期】**
6. ⇒ **原点 = 受害者的 `playerState.origin`**
7. ⇒ **角度 = `{0, viewAngles[1], 0}`**（只用 yaw）
8. ⇒ **trType 3（§344 的"轨迹 3"）**
9. ⇒ **时长 50ms**
10. ⇒ **位移 = `{cos(yaw)*70, sin(yaw)*70, -64}`** ⇒ **沿视线抛 70 单位 + 下降 64**
11. ⇒ **`angleTrajectoryType = 0`**（固定角度）
12. ⇒ **`groundEntityNum = EntityNumWorld`**（§345 的 2046）
13. ⇒ **`+0x9C` 是 ET_ITEM 的【12 位物品/武器资产字段】**（§344 第四次确认）
14. ⇒ **`otherEntityNum = 受害者 clientNum`** ⇒ **`+0x84` 的"拥有者"**
```

**✅ 与 §344 的"`validItemEntity` 要求 `positionTrajectoryType == 3` 与 `positionTrajectoryDuration == 50`"**完全一致 ✓**

**⇒ **而这里知道**为什么**：**从零售测的。**

**✅ **那个"魔法常数 3 与 50"现在有出处。**

### 3.3 而**"70 单位 / 64 单位下降"**

**⇒ 三层**：

```text
1. `delta = {cos*70, sin*70, -64}` 是速度（单位/秒）
2. ⇒ **而 `duration = 50ms`**
3. ⇒ **所以实际位移 = `70 * 0.05 = 3.5` 单位水平 + `-3.2` 垂直**
```

**⚠ 所以**包裹只飞 3.5 单位**。**

**✅ 一个**象征性的抛出**（不是真实物理）。**

**⇒ **而注释没说"3.5"，因为那是**推导的**。**

### 3.4 而**"2045"**

**⇒ 三层**：

```text
1. `otherEntityNum` 从 victimClientNum 变成 **2045**
2. ⇒ **而 §345 的 EntityNumWorld = 2046、EntityNumNone = 2047**
3. ⇒ **所以 2045 是第三个哨兵**
```

**✅ 与 §362 四的 `MaximumServerCollisionEntityNum`**可能同值。**

**⚠ 一处**需要确认**。**⇒ 而代码里用 `MaximumServerCollisionEntityNum`。**

**✅ 所以 `MaximumServerCollisionEntityNum == 2045`。**

**⇒ **一个可推算的常数。**

### 3.5 而**三个时间点**

```text
52800   包裹进入（生成）
53700   拥有者变成 2045    （+900ms）
56400   被拾取             （+3600ms）
```

**✅ 而代码用 `ownerClearTime = serverTime + 900`** ✓ **与 53700-52800 = 900 一致。**

**✅ **闭合**。

## 四、**`updateScavengerBags` 的完整逻辑**（本组第二重要）

### 4.1 四个容器

```cpp
std::vector<std::uint32_t> collectedBy;
std::vector<SvEntityHandle> remove;
std::vector<std::uint32_t> abandon;
```

**✅ 三层**：

```text
`collectedBy`   谁收集了（返回给调用方）
`remove`        待释放的句柄（freeEntity 在循环后）
`abandon`       待从表里删除的号
```

**✅ 与 §355 的"尸体排队而不是在这里释放"**完全同族（**第二次"收集后释放"**）。

### 4.2 而**拾取盒的精确尺寸**（本组核心）

```cpp
// CODREF(BO1 BG_PlayerTouchesItem 0x423CE0): the exact player
// pickup box is +/-36 in X/Y and item-minus-player Z in
// [-88,+18]. No radius or collision approximation is used.
if (std::abs(bag.pickupOrigin[0] - playerOrigin[0]) > 36.0f ||
    std::abs(bag.pickupOrigin[1] - playerOrigin[1]) > 36.0f ||
    vertical < -88.0f || vertical > 18.0f ||
    !grantAmmo(candidate))
{
    continue;
}
```

### 4.3 八层

```text
1. **`BO1 BG_PlayerTouchesItem 0x423CE0`：精确的玩家拾取盒**
2. ⇒ **X/Y 各 ±36**
3. ⇒ **而 item 减 player 的 Z 在 `[-88, +18]`**
4. ⇒ **不使用半径或碰撞近似**
5. ⇒ **所以是一个【72 × 72 × 106】的盒子**
6. ⇒ **Z 的【不对称】**（-88 是"物品在玩家下方"，+18 是"上方"）
7. ⇒ **负方向大得多** ⇒ 物品会掉在脚下
```

**✅ 与 §354 的"五个距离/高度常量"**同族（**一个新的常量集**）。**

**⚠ 而"±36"与"106 高的盒" ⇒ **一个很宽松的拾取范围**。**

**✅ 与 §352 的"玩家身高约 96"**配合（-88 覆盖大部分身体下方）。**

### 4.4 而**"不使用半径或碰撞近似"**

**✅ 与 §344 的"更好的是省略而不是错"**同族（**第五次"用精确值"**）。

**⇒ 三层**：

```text
1. 可以从参考实现抄一个精确值
2. ⇒ **就不该用圆柱半径近似**
3. ⇒ **所以逐轴比较**
```

**✅ 一个**从具名函数抄精确值的正确用法**。**

### 4.5 而**七个拾取前置**

```cpp
if (candidate.client.gameplayState != ClientGameplayState::Playing ||
    !candidate.client.playerState.health ||
    ability == playerAbilities_.end() ||
    ability->second.spawnGeneration != candidate.client.playerState.spawnGeneration ||
    !SV_HasAbility(ability->second.modifiers, SvAbilityScavenger) ||
    (clientNum == bag.victimClientNum && snapshot_.serverTime < bag.ownerClearTime))
{
    continue;
}
```

**⇒ 六项**：

```text
① Playing
② 活着
③ 有能力记录
④ **代际匹配**（防跨死亡）
⑤ **有 Scavenger 能力**
⑥ **不是受害者本人（或已过 ownerClearTime）**
```

**✅ 与 §355 的"`spawnGeneration` 防跨死亡"**第二次确认。**

**✅ 与 §344 的"布告无条件"**不同**（这是**逐项**检查）。

## 五、**`grantAmmo` 的两级**（本组第五重要）

### 5.1 弹药池

```cpp
for (const auto &weapon : weapons) {
    if (!weapon.weaponAssetIndex || !weapon.ammoIndex || !weapon.clipSize) continue;
    const auto pool = find_if(state.playerState.ammoPools, ammoIndex == weapon.ammoIndex);
    if (pool == end) continue;
    std::uint32_t maximum{};
    for (const auto &owned : weapons) {
        if (owned.ammoIndex == weapon.ammoIndex) maximum = min<uint32>(0x7FF, maximum + owned.maxAmmo);
    }
    const auto next = min<uint32>(maximum, pool->count + weapon.clipSize);
    changed = changed || next != pool->count;
    pool->count = (uint16)next;
}
```

### 5.2 七层

```text
1. **遍历主武器与副武器**
2. ⇒ **跳过无索引/无弹药池/无弹匣的**
3. ⇒ **找同 ammoIndex 的池**
4. ⇒ **`maximum` = 所有共享该池的武器的 `maxAmmo` 之和**（上限 `0x7FF`）
5. ⇒ **`next = min(maximum, count + clipSize)`** ⇒ **加一个弹匣**
6. ⇒ **`changed` 只在真变化时置位**
7. ⇒ **`0x7FF = 2047`** ⇒ 与 §346 的"`pool.count > 0xFFF`"**不同**（那是 12 位）
```

**⚠ 所以**同一个池的两种上限**（`0x7FF` 用于内部计算、`0xFFF` 用于线宽）。**

**✅ 一个**保守的内部界**（`0x7FF` < `0xFFF`）。**

### 5.3 而**"IW4/BO1 的 Scavenger 给一个致命副手而【故意留下战术槽】"**

```php
// IW4/BO1 Scavenger grants one lethal offhand and deliberately
// leaves the tactical slot alone. It still refuses the pack when
// all owned ammunition is full.
const auto equipment = playerEquipment_.find(state.playerState.clientNum);
if (equipment != playerEquipment_.end() &&
    equipment->second.spawnGeneration == state.playerState.spawnGeneration)
{
    const auto &lethal = equipment->second.equipment.weapons[0];
    const auto ownsLethal = lethal.weaponAssetIndex && any_of(heldWeapons, ...);
    const auto clip = find_if(ammoClips, clipIndex == lethal.clipIndex);
    if (ownsLethal && clip != end && clip->count[0] < lethal.clipCapacity) {
        ++clip->count[0];
        changed = true;
    }
}
```

**⇒ 八层**：

```text
1. **给一个致命副手**
2. ⇒ **而【故意】留下战术槽**
3. ⇒ **它在【所有拥有的弹药都满】时仍拒绝这个包裹**
4. ⇒ **代际匹配才有装备**
5. ⇒ **`weapons[0]` 是致命槽**
6. ⇒ **必须拥有它**
7. ⇒ **`clip->count[0] < clipCapacity`** ⇒ **只有一个弹匣容量**
8. ⇒ **`++count[0]`**（加一个）
```

**✅ 与 §344 的"`offhandWeaponSlots`"**配合。**

**⚠ 而"故意留下战术槽"来自**IW4/BO1 的实现**。**

**✅ 与本项目的参照层级一致（IW4X > CoD4X）。**

### 5.4 而 **`SV_OverlayPlayerStateToNative`**

```cpp
if (changed) SV_OverlayPlayerStateToNative(state.playerState, state.nativePlayerState);
```

**⇒ 三层**：

```text
1. 改了 `playerState`
2. ⇒ **必须同步到 `nativePlayerState`**
3. ⇒ **否则原生 pmove 看到旧的**
```

**✅ 与 §355 的"两个位置（`ps` 与 `ent`）"**同族（**第二次"两个副本必须同步"**）。

## 六、**`0x80000` 的完整事故**（本组最重要的一段）

### 6.1 那段

```php
// CODREF(body_end): IW3's BodyEnd clears eFlags 0x80000 once the death
// animation has run. That bit is the client's "re-initialise this corpse"
// flag - cg_snapshot_mp's ET_PLAYER_CORPSE case re-copies the model,
// re-clones the anim tree and zeroes previousEventSequence on EVERY
// snapshot while it is set, so a corpse that holds it forever is reset
// ~20 times a second and never animates. The companion bit stays.
```

### 6.2 十一层

```text
1. **IW3 的 `BodyEnd` 在死亡动画跑完后清除 `eFlags 0x80000`**
2. ⇒ **那个位是客户端的【重新初始化这具尸体】标志**
3. ⇒ **`cg_snapshot_mp` 的 `ET_PLAYER_CORPSE` 分支**：
     · **重新复制模型**
     · **重新克隆动画树**
     • **清零 `previousEventSequence`**
4. ⇒ **在【每一个快照】上，只要它被置位**
5. ⇒ **所以一具永远持有它的尸体每秒被重置【约 20 次】**
6. ⇒ **而【永不动画】**
7. ⇒ **而伴随位保持**
```

### 6.3 ⭐ **"每秒重置 20 次而永不动画"**

**✅ 与 §357 的"每帧重打戳让动画看起来冻结"**完全同族（**第三次"重置导致冻结"**）。

**⇒ 三层**：

```text
1. 客户端每快照重新初始化
2. ⇒ **动画树被重新克隆 ⇒ 播放位置归零**
3. ⇒ **而 20Hz ⇒ 每秒 20 次归零**
4. ⇒ **所以尸体永不动画**
```

**✅ **一个极清晰的机制**（比"冻结"更具体）。**

**⚠ 而"20 次/秒"与 §355 的"快照 50ms（20Hz）"**完全一致 ✓**

**✅ **四次确认 20Hz。**

### 6.4 而**"伴随位保持"**

**⇒ 三层**：

```text
1. `0x80000` 要清
2. ⇒ **而"伴随位"要保持**
3. ⇒ **所以 `0xA0002` → `0x80000`**（§362 六.5）
```

**✅ 与 §362 六.5 的"spawn `0xA0002` → settle `0x80000`"**完全闭合 ✓**

### 6.5 而**"测量的是 `spawn 0xA0002 → settle 0x80000`，1.4..2.9 秒后"**

```php
// TODO(CODOL): remove once the corpse is confirmed to stay on a
// player's screen. EDGE-TRIGGERED - one line per corpse per
// transition, not the 15-second SAMPLE the player-corpses line
// takes, which cannot show a transition at all and is why "the
// body vanishes when the animation ends" had no server-side
// counterpart to compare against. The demo's measured shape is
// spawn 0xA0002 -> settle 0x80000, 1.4..2.9 s later.
```

**⇒ 九层**：

```text
1. **在尸体被确认留在玩家屏幕上之后移除这个 TODO**
2. ⇒ **【边沿触发】—— 每具尸体每次转换一行**
3. ⇒ **而不是 `player-corpses` 那行用的【15 秒采样】**
4. ⇒ **那个采样【根本不能显示一个转换】**
5. ⇒ **而那就是为什么"动画结束时身体消失"【没有服务端对应物可比】**
6. ⇒ **demo 的测量形状是：spawn `0xA0002` → settle `0x80000`，1.4..2.9 秒后**
```

**✅ 与 §355 的"前 40 帧的日志结论都作废"**同族（**第三次"采样率不足"**）。

**⇒ 三层**：

```text
15 秒采样   ⇒ **看不到 1.4-2.9 秒的转换**
边沿触发    ⇒ **每次转换一行**
```

**✅ **一个精确的可观测性修正。**

### 6.6 而 **`0xA0002` → `0x80000` 的位运算**

```text
0xA0002 = 1010 0000 0000 0000 0010
0x80000 = 1000 0000 0000 0000 0000
```

**⇒ 三层**：

```text
1. `0xA0002` = `0x80000 | 0x20000 | 0x2`
2. ⇒ **两者共有 `0x80000`**
3. ⇒ **而 `0xA0002` 还有 `0x20000` 与 `0x2`**
```

**⚠ 所以**settle 清掉的不是 `0x80000`。**

**⇒ 而是 **`0x20002`**。**

**⚠ 与注释"clears eFlags 0x80000"**矛盾**。**

**⇒ 一处**需要核对的差异**。**

**✅ 而"伴随位保持"可能指 `0x80000`。**

**⇒ 所以**实际清的是 `0x20002`**。**

**⚠ 而注释说清 `0x80000`。**

**⇒ **一处真实的矛盾**（或我理解反了）。**

## 七、`spawnObituaryEvent` 的**300ms**

```cpp
// FIELD 13, not field 23 -- see the member's own declaration.
entity.networkState.groundEntityNum = attackerClientNum;
...
// The same 300 ms lifetime every other temp event gets, and it is what
// retail spends: the dm demo's obituary entities are first asserted at
// T, last at T+200 and removed at T+300, all 145 of them.
```

### 7.1 五层

```text
1. **字段 13，不是字段 23**（与 §344 二.4 完全一致 ✓）
2. ⇒ **`groundEntityNum = attackerClientNum`**
3. ⇒ **同样的 300ms 生命期，其它每个临时事件都得到**
4. ⇒ **而它是零售所花的**：dm demo 的布告实体在 **T 首次断言、T+200 最后断言、T+300 移除**
5. ⇒ **全部 145 个**
```

**✅ 与 §344 的"`groundEntityNum` 在布告上是字段 13 而其它是 23"**第三次确认。**

**⚠ 而"145 个全一致"⇒ **一个极强的统计**。**

**✅ 与 §355 的 `259,968`、§351 的 `237`**第五次大规模统计。

## 八、`spawnEntityAtOrAbove` 的**逐号搜索**

```cpp
auto number = std::max(floor, entityPool_->firstDynamicEntityNum());
for (; number < EntityNumWorld; ++number) {
    // reserve() refuses a number already in use and is a no-op on one
    // already reserved, so a failure here just means walk on.
    if (!entityPool_->reserve(number)) continue;
    const auto handle = entityPool_->spawnAt(number, snapshot_.serverTime);
    if (!handle) continue;
    ...
    return handle;
}
return std::nullopt;
```

### 8.1 五层

```text
1. **从 `max(floor, firstDynamic)` 开始**
2. ⇒ **逐号向上到 `EntityNumWorld`（2046）**
3. ⇒ **`reserve()` 拒绝已用而对已保留的是 no-op**
4. ⇒ **所以失败只意味着【继续走】**
5. ⇒ **成功 ⇒ `spawnAt` 并插入 `entities_`**
```

**✅ 与 §345 的"`entityPool_->reserve(entry.entityNum)`"**配合。**

**⚠ 而"`reserve()` 对已保留的是 no-op"⇒ **所以它会**成功**（返回 true）。**

**⇒ 所以 `!reserve ⇒ continue` 只在**已用（非保留）**时触发。**

**✅ 一个**微妙的语义**（"已保留"与"已用"不同）。**

## 九、`spawnEntity` 的**插入失败回滚**

```cpp
std::optional<SvEntityHandle> SvServerWorld::spawnEntity()
{
    if (!entityPool_) return std::nullopt;
    const auto handle = entityPool_->spawn(snapshot_.serverTime);
    if (!handle) return std::nullopt;
    SvGameEntity entity;
    entity.networkState.number = handle->entityNum;
    entity.clientNum = EntityNumNone;
    const auto [_, inserted] = entities_.emplace(handle->entityNum, entity);
    if (!inserted) { (void)entityPool_->free(*handle, snapshot_.serverTime); return std::nullopt; }
    return handle;
}
```

**⇒ 四层**：

```text
1. 池里分配
2. ⇒ **`entities_.emplace`** —— 若已有 ⇒ 失败
3. ⇒ **回滚池**
4. ⇒ **返回 nullopt**
```

**✅ 与 §349 的"事务性"**第六次。

## 十、关键结论

1. **领奖台相机的类型 7 → 4 的两阶段**：0.5 秒加速（`delta * 0.25`）+ 16.5 秒匀速 = **17 秒**。
2. **"加速轨迹的端点位移是 `delta * t/2`"`** —— 而 `delta` 这里是**末速度**（与 §354 的平均速度**不同语义**）。
3. **`spawnScavengerBag` 的完整实测**：实体 255 @52800、trType 3、50ms、scale 1、**物品行 902**、`+0x84` 是受害者。
4. **"53700 拥有者变成 2045；56400 被拾取"`** ⇒ **`MaximumServerCollisionEntityNum == 2045`**（第三个哨兵）。
5. **"同一次死亡的第二个掉落武器物品恰好留 60 秒"`** ⇒ 那提供了**物品生命期**。
6. **`+0x9C` 是 ET_ITEM 的 12 位物品/武器资产字段** —— **第四次确认那个偏移的双语义**。
7. **§344 的"魔法常数 3 与 50"现在有出处**（从零售测的）。
8. **`delta = {cos*70, sin*70, -64}` 而 `duration = 50ms`** ⇒ 实际只飞 **3.5 单位**（一个象征性的抛出）。
9. **四个容器**（`collectedBy` / `remove` / `abandon`）—— **第二次"收集后释放"**。
10. **⭐ 拾取盒 `±36` X/Y 与 `[-88, +18]` Z** —— 一个 **72 × 72 × 106** 的**不对称**盒子（负方向大得多）。
11. **"不使用半径或碰撞近似"`** —— 从具名函数抄精确值的正确用法（第五次"用精确值"）。
12. **七个拾取前置**，含**代际匹配**（第二次）与 **Scavenger 能力**。
13. **`grantAmmo` 的两级**（弹药池 + 致命副手），而 **`maximum` 上限 `0x7FF`**（保守的内部界 < 线宽 `0xFFF`）。
14. **"IW4/BO1 的 Scavenger 给一个致命副手而故意留下战术槽"`** —— 参照层级正确。
15. **`SV_OverlayPlayerStateToNative`** —— 第二次"两个副本必须同步"。
16. **⭐⭐ "`0x80000` 是客户端的『重新初始化这具尸体』标志"`** —— 客户端在**每一个快照**上重新复制模型、重新克隆动画树、清零 `previousEventSequence`。
17. **"一具永远持有它的尸体每秒被重置约 20 次而永不动画"`** —— 第三次"重置导致冻结"，而 **20 次/秒 = 四次确认 20Hz**。
18. **"`spawn 0xA0002` → `settle 0x80000`，1.4..2.9 秒后"`**。
19. **⚠ 注释说清 `0x80000` 而位运算显示清的是 `0x20002`** —— 一处真实的矛盾。
20. **"15 秒采样根本不能显示一个转换"`** —— 第三次"采样率不足"；改为**边沿触发**。
21. **布告的 300ms 生命期：T 首次断言、T+200 最后断言、T+300 移除，全部 145 个`** —— 第五次大规模统计。
22. **`spawnEntityAtOrAbove` 的"`reserve()` 对已保留的是 no-op"`** —— 一个微妙语义（已保留 vs 已用）。
23. **`spawnEntity` 的插入失败回滚** —— 第六次事务性。

## 十一、未闭合点

- `0xA0002` → `0x80000` 位运算与注释的矛盾。
- `MaximumServerCollisionEntityNum == 2045` 的确认。
- `PlayerCorpseRingSize` 的值。
- `FirstPlayerCorpseEntityNum` 的值。
- `markFreeAfterEvent` 的实现。
- `sv_snapshot_mp.cpp` 16800 行之后未读取（27,016 行，进度 62%）。
