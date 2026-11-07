# 354 · **"屏障的 outside 与 inside【就是】图里的节点"** —— 修复的 150ms 抬升 + 100ms 滑入、**六个 `nearestPlayerXxx` 的完全重复**、`8.0f` 的紧半径

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 13200–13600 行。

## 二、`setZmBarriers` 的**五层构建**（本组第三重要）

### 2.1 那段

```php
// A barrier's outside and inside ARE nodes in the graph -- they are the
// negotiation pair, and 12.58 put those pairs in as edges. So the barrier is
// recognised by the EDGE, and the resolution is just finding the two node
// indices. The radius is tight because these are node origins, not guesses.
for (const auto &barrier : barriers) {
    if (!barrier.hasVault || barrier.boards.empty()) continue;
    const auto outside = SV_ZmNavNearestNode(zmNavGraph_, barrier.outside, 8.0f);
    const auto inside = SV_ZmNavNearestNode(zmNavGraph_, barrier.inside, 8.0f);
    if (!outside || !inside || *outside == *inside) continue;
    BarrierState state{ .name = barrier.name, .outsideNode = *outside, .insideNode = *inside };
    state.boardClipHandles.reserve(barrier.boards.size());
    for (const auto &board : barrier.boards) {
        state.boardClipHandles.push_back(board.clipHandle);
        if (board.boardIndex < 1 || board.boardIndex > state.boards.size()) continue;
        auto &slot = state.boards[board.boardIndex - 1];
        slot.clip = board.clipHandle;
        const auto profiles = SV_FactoryBoardFlights();
        const auto profile = std::ranges::find_if(profiles, [&](const auto &p) {
            return p.barrier == barrier.name && p.slot == board.boardIndex;
        });
        if (profile != profiles.end()) slot.profile = &*profile;
    }
    OlMod::RuntimeLog::write(..., "ZMBARRIER profiles barrier=" + state.name + " measured=" +
        count_if(state.boards, [](const auto &b) { return b.clip && b.profile; }) + "/" +
        state.boardClipHandles.size());
    zmBarriers_.emplace(std::pair{ std::min(*outside, *inside), std::max(*outside, *inside) }, std::move(state));
}
```

### 2.2 十层

```text
1. **一个屏障的 outside 与 inside 【就是】图里的节点**
2. ⇒ **它们是那个协商对，而 12.58 把那些对作为【边】放进去了**
3. ⇒ **所以屏障由【边】识别，而解析只是找两个节点索引**
4. ⇒ **半径很紧因为那些是节点【原点】，不是猜测**
5. ⇒ **`8.0f`**（而 §353 的 `zmGoalRoutable` 用 `64.0f`）
6. ⇒ **`outside != inside` 是必须的**
7. ⇒ **board 的 `boardIndex` 是 1 基，越界则跳过（但仍推入 `boardClipHandles`）**
8. ⇒ **profile 按 `barrier 名 + slot` 查找**
9. ⇒ **日志报 `measured=<有 clip 且有 profile 的>/<总 board 数>`**
10. ⇒ **`zmBarriers_` 的键是 `{min, max}` 的【有序对】**（与 §353 三.5 的双向查配合）
```

### 2.3 而 **`8.0f` vs `64.0f`**

**⇒ 三层**：

```text
setZmBarriers         8.0f   屏障的 outside/inside 是【精确的节点原点】
zmGoalRoutable        64.0f  **任意目标**要落到一个节点上
```

**✅ "半径很紧因为那些是节点原点，不是猜测"是一个**精确的区分**。**

**⚠ 而 `64.0f` 对 `8.0f` 是 8 倍。**

**⇒ 所以**两个不同的容差语义**。**

### 2.4 而 **`boardClipHandles` 无条件推入而 `boards[...]` 有条件**

```cpp
state.boardClipHandles.push_back(board.clipHandle);         // 无条件
if (board.boardIndex < 1 || board.boardIndex > state.boards.size()) continue;   // 再判
```

**⇒ 三层**：

```text
1. **`boardClipHandles` 收到【每一个】 board**
2. ⇒ **而 `state.boards[idx]` 只收到索引有效的**
3. ⇒ **所以日志的分母是【全部 board】而分子是【有 profile 的】**
```

**⚠ 所以 `measured=N/M` 里的 M 可能是**大于** `state.boards.size()`。**

**⇒ 一处**统计口径不一致**（但无害）。**

### 2.5 而**"12.58 把那些对作为边放进去"**

**⇒ 三层**：

```text
1. `12.58` 是一个文档节号
2. ⇒ **它把 outside/inside 对作为【边】放进图**
3. ⇒ **所以屏障靠边识别**
```

**✅ 与 §350 的 `12.x` 系列（12.122/12.153/12.154/12.155/12.158/12.47/12.75/12.77）**同族。**

**⇒ **第九次引用 12.x 文档节**。**

## 三、`repairableZmBarrierAt` 的**六项过滤**（本组第四重要）

```cpp
constexpr float RepairRadius = 112.0f;
constexpr float RepairHeight = 96.0f;
const BarrierState *nearest{};
auto nearestDistanceSquared = RepairRadius * RepairRadius;
for (const auto &[edge, barrier] : zmBarriers_) {
    if (!barrier.torn) continue;
    // Use the board's authored home rather than a navigation node. The
    // inside node is an AI routing point and may sit well down a corridor;
    // the retail use volume is at the physical window the player faces.
    for (slot = 0; slot < barrier.boards.size(); ++slot) {
        const auto &board = barrier.boards[slot];
        if (!board.handle || !board.homeCaptured || !board.settled ||
            board.repairStartedAt || !barrier.controller.released((uint8)slot)) continue;
        const auto &point = board.homePosition.base;
        if (std::abs(point[2] - origin[2]) > RepairHeight) continue;
        const auto dx = point[0] - origin[0], dy = point[1] - origin[1];
        const auto distanceSquared = dx * dx + dy * dy;
        if (distanceSquared > nearestDistanceSquared) continue;
        nearestDistanceSquared = distanceSquared; nearest = &barrier;
    }
}
return nearest ? std::optional{ nearest->name } : std::nullopt;
```

### 3.1 九层

```text
1. **用 board 的【作者化 home】而不是一个导航节点**
2. ⇒ **inside 节点是一个 AI 路由点而可能坐在走廊很远处**
3. ⇒ **而零售的使用体量在玩家面对的那个【物理窗口】处**
4. ⇒ **前置：屏障已破**
5. ⇒ **六项 board 过滤**：
     · 有 handle
     · `homeCaptured`
     · `settled`
     · 未在修复中
     · **控制器已释放该槽**
6. ⇒ **高度差 `<= 96`**
7. ⇒ **平面距离 `<= 112`**
8. ⇒ **取最近的（跨屏障）**
```

### 3.2 而**"inside 节点是一个 AI 路由点而可能坐在走廊很远处"**

**✅ 这是对 §354 二.2 的**重要限定**。**

**⇒ 三层**：

```text
1. `inside` 节点是【AI 路由用】的
2. ⇒ **而可能远离物理窗口**
3. ⇒ **所以"玩家能修复"的判定用 board 的 home 而不是节点**
```

**✅ 与 §340 的"`table+0x10` 零次引用"、§347 的"这是线半"**同族（**第五次承认语义的分层**）。**

### 3.3 而**五个常量**

```text
RepairRadius           112.0f
RepairHeight            96.0f
8.0f    （setZmBarriers 的节点半径）
64.0f   （zmGoalRoutable 的节点半径）
128*128 （zmSpawnCrossesBarrier 的屏障距离平方）
```

**⇒ 五个。**

**⚠ 而 112 与 96 是**修复的体量**。**

**⇒ 一个**接近玩家身高（约 96）与臂展（约 112）**。**

**✅ 合理。**

## 四、`repairZmBarrier` 的**反向遍历**（本组第五重要）

```cpp
for (std::size_t reverse = barrier.boards.size(); reverse > 0; --reverse) {
    const auto slot = static_cast<std::uint8_t>(reverse - 1u);
    auto &board = barrier.boards[slot];
    if (!barrier.controller.released(slot) || !board.handle || !board.homeCaptured ||
        !board.settled || board.repairStartedAt || !entityPool_->resolve(*board.handle))
        continue;
    const auto entity = entities_.find(board.handle->entityNum);
    if (entity == entities_.end()) continue;
    board.repairStartOrigin = entity->second.currentOrigin;
    board.repairStartAngles = entity->second.currentAngles;
    board.repairStartedAt = snapshot_.serverTime;
    OlMod::RuntimeLog::write(..., "ZMBARRIER repair begin serverTime=" + ... + " barrier=" + barrier.name + " slot=" + std::to_string(slot + 1u));
    return true;
}
```

### 4.1 六层

```text
1. **从【最后一个】槽开始反向遍历**
2. ⇒ **只修复一个板子然后返回**
3. ⇒ **七项过滤**（比 `repairableZmBarrierAt` 多 `entityPool_->resolve` 与 `entities_.find`）
4. ⇒ **记录修复起点（位置 + 角度）**
5. ⇒ **设 `repairStartedAt = serverTime`**
6. ⇒ **日志用 `slot + 1`（1 基）**
```

### 4.2 而**为什么反向？**

**⇒ 三层**：

```text
1. 反向遍历 ⇒ **从最后一块开始**
2. ⇒ **可能因为最后一块是"最后一个被撕掉的"**
3. ⇒ **所以先修它**（LIFO）
```

**⚠ 一个**需要推断的理由**（没有注释）。**

**✅ 与 §353 的"`zmHeadsThisFrame_ >= 4`"等**其它容量决策**一样，理由不明。**

## 五、**修复动画的两段**（本组最重要的一段）

### 5.1 那段

```php
// Retail returns a board in two visible pieces: a 150 ms lift and a
// 100 ms slide into its authored home.  Keep the brush solid for the
// whole trip; setBrushModelMotions performs the native relink once for
// the batch, so repair never leaves a visual-only board behind.
if (board.repairStartedAt && board.handle && board.homeCaptured && entityPool_->resolve(*board.handle))
{
    constexpr std::uint32_t LiftMilliseconds = 150;
    constexpr std::uint32_t SlideMilliseconds = 100;
    const auto started = *board.repairStartedAt;
    const auto elapsed = now >= started ? now - started : 0u;
    SvNativeTrajectory position{};
    SvNativeTrajectory angles{};
    std::uint32_t flags = 1;
    bool complete = elapsed >= LiftMilliseconds + SlideMilliseconds;
    if (complete) {
        position = board.homePosition;
        angles = board.homeAngles;
        flags = board.homeFlags;
    } else if (elapsed < LiftMilliseconds) {
        position.type = 3;
        position.time = (int32)started;
        position.duration = (int32)LiftMilliseconds;
        position.base = board.repairStartOrigin;
        position.delta[2] = (board.homePosition.base[2] - board.repairStartOrigin[2]) * (1000.0f / (float)LiftMilliseconds);
        angles.type = 0;
        angles.base = board.repairStartAngles;
    } else {
        position.type = 3;
        position.time = (int32)(started + LiftMilliseconds);
        position.duration = (int32)SlideMilliseconds;
        position.base = { board.repairStartOrigin[0], board.repairStartOrigin[1], board.homePosition.base[2] };
        position.delta[0] = (board.homePosition.base[0] - board.repairStartOrigin[0]) * (1000.0f / (float)SlideMilliseconds);
        ...
    }
}
```

### 5.2 十一层

```text
1. **零售把一块板子分【两个可见片段】返回**：一个 **150ms 抬升**与一个 **100ms 滑入**它的作者化 home
2. ⇒ **整段行程保持画笔为实心**
3. ⇒ **`setBrushModelMotions` 为这一批做【一次】原生重链**
4. ⇒ **所以修复永不留下一个"仅视觉的"板子**
5. ⇒ **总时长 250ms**
6. ⇒ **阶段一（< 150ms）**：
     · `type = 3`（轨迹）
     · `time = started`
     · `duration = 150`
     · `base = repairStartOrigin`
     · **`delta[2] = (homeZ - startZ) * (1000/150)`** ⇒ **只动 Z**
     · `angles.type = 0`（固定角度）
7. ⇒ **阶段二（150..250ms）**：
     · `time = started + 150`
     · `duration = 100`
     · **`base = {startX, startY, homeZ}`**（Z 已是 home）
     · **`delta[0] = (homeX - startX) * (1000/100)`** ⇒ **只动 X**
8. ⇒ **`delta` 的单位是"每【秒】的位移"**（因为 `* 1000/duration`）
9. ⇒ **而 `type = 3` 是轨迹类型**（§344 的 `positionTrajectoryType == 3`）
10. ⇒ **`flags = 1`**（默认）而完成后是 `homeFlags`
```

### 5.3 **"delta 的单位是每秒位移"**

**⇒ 三层**：

```text
1. `delta[2] = Δz * (1000 / 150)`
2. ⇒ **若 `Δt = 150ms` ⇒ `delta * Δt/1000 = Δz` ✓**
3. ⇒ **所以 delta 是【速度】**（单位/秒）
```

**✅ 与 §344 的 `positionTrajectoryDelta` 是**速度**配合。**

**⚠ 而 §344 说"`positionTrajectoryDelta` 在 ET_SCRIPTMOVER 上是字段 5/7/8"。**

**✅ **完整的单位闭合。**

### 5.4 而**"只有 Z 然后只有 X"**

**⇒ 三层**：

```text
阶段一   只动 Z（抬升）
阶段二   只动 X（滑入）
⇒ **Y 从不被动画覆盖**
```

**⚠ 所以**Y 必须是 `startY == homeY`**（否则板子最终不在 home 的 Y）。**

**⇒ 而完成后 `position = board.homePosition` ⇒ **所以最终位置是对的**。**

**✅ 一个**"近似动画 + 精确终态"**的设计。**

### 5.5 而**"只在 X 滑入"而不是在 XY 上滑**

**⚠ 所以**Y 方向的复位是瞬时的**（在 150ms 切换点）。**

**⇒ 可能因为**板子只在 X 方向滑动**（板的形状决定）。**

**✅ 合理的假设。**

### 5.6 而**"整段行程保持画笔为实心"**

**✅ 与 §350 的"`solid == 0xFFFFFF` ⇒ 走画笔分支"配合。**

**⇒ 三层**：

```text
1. 修复中画笔仍实心
2. ⇒ **所以玩家不能穿过正在修复的板子**
3. ⇒ **而 `setBrushModelMotions` 批量重链一次**
```

**✅ 一个**正确的物理语义**。**

## 六、`nearestPlayerXxx` 的**六个函数**

### 6.1 六个

```text
nearestPlayerPosition       返回 const array<float,3>*
nearestPlayerNavNode        返回 uint16 节点（用 SvActorNodeSearchRadius）
nearestPlayerDistance       返回 float（sqrt，不是平方）
nearestPlayerOrigin         返回 optional<array<float,3>>
nearestPlayerClientNum      返回 optional<uint32>
nearestEnemyProbe           返回 struct（含 clientNum/origin/viewHeightCurrent/pmType）
enemyCentroidOrigin         返回 array<float,3>（质心）
```

**⇒ 七个（含 `enemyCentroidOrigin`）。**

### 6.2 而**七个的过滤条件完全一样**

```cpp
if (state.client.gameplayState != ClientGameplayState::Playing ||
    state.client.playerState.health <= 0 || zombieDowned(clientNum))
    continue;
```

**⇒ 三项**（Playing / 活着 / 非倒地）。

**⚠ 而这段在七个函数里**复制了七次**。**

**✅ 与 §337 的"两个几乎相同的函数"、§352 的"两个入口必须一致"**同族（**第四次"七份重复"**）。**

**⚠ 一处**明显的可抽取**。**

**⇒ 而注释**三次**强调"同样的活人过滤"（`nearestEnemyProbe` 与 `enemyCentroidOrigin` 都说了）。**

**⇒ **作者知道它在重复**。**

### 6.3 而**`nearestPlayerDistance` 用 `sqrt` 而其它用平方**

```cpp
const auto distance = std::sqrt(dx * dx + dy * dy);   // ← 这个用 sqrt
if (distance >= nearest) continue;
```

**⚠ 而其它六个用 `dx*dx + dy*dy`。**

**✅ 因为 `nearestPlayerDistance` **返回距离**而其它只比较。**

**⇒ 一个**正确的选择**。**

### 6.4 而 **`nearestPlayerDistance` 的注释：为什么不数 Z**

```php
// Same two conditions as nearestPlayerNavNode -- living and playing -- and
// the same planar measure. Height is left out on purpose: an actor on the
// walkway above a player is not in reach of them, but it is also not
// something this stepper can answer without a trace, and counting Z would
// make a zombie on a staircase stop swinging halfway up.
```

**⇒ 八层**：

```text
1. **与 `nearestPlayerNavNode` 同样的两个条件 —— 活着并在玩 —— 以及同样的【平面】度量**
2. ⇒ **高度被有意省略**
3. ⇒ **一个在玩家上方走道上的 actor 不在他们的触及范围内**
4. ⇒ **但那也不是这个步进器【不做一个追踪】就能回答的**
5. ⇒ **而数 Z 会让一个在楼梯上的僵尸【到一半就停止挥击】**
6. ⇒ ⇒ **所以平面距离**
```

**✅ 与 §344 的"yaw only"**同族（**第二次"故意忽略一个轴"**）。**

**⚠ 而"到一半就停止挥击"是一个**具体的、可见的**bug 描述。**

**✅ 一个**极强的理由陈述**。**

### 6.5 而 `nearestEnemyProbe` 的**中文注释**

```cpp
// ★ 2026-10-16 28000（S3 v2 combat）：nearestPlayerClientNum 的敌我版。
// 同样的活人过滤（Playing+health>0+非倒地），再加：排除本人、排除同队
// 非 None（None=None 互敌 = FFA）、平面距离 <= maxRange。只返回瞄准
// 需要的小字段，不拷 playerState（每帧成本门 §3.3b）。
```

**⇒ 七层**：

```text
1. **`nearestPlayerClientNum` 的敌我版**
2. ⇒ **同样的活人过滤**（Playing + health>0 + 非倒地）
3. ⇒ **再加：排除本人、排除同队非 None**
4. ⇒ **（None = None 互敌 = FFA）**
5. ⇒ **平面距离 <= maxRange**
6. ⇒ **只返回瞄准需要的小字段**
7. ⇒ **不拷 playerState**（**每帧成本门 §3.3b**）
```

**✅ 一个**中文注释**（罕见 —— 本文件绝大多数是英文）。**

**⚠ 而 `§3.3b` 是**另一套文档编号**（不是 `12.x`）。**

**✅ 所以**两套文档编号并存**。**

### 6.6 而**"None = None 互敌 = FFA"**

```cpp
if (state.client.team == excludeTeam && excludeTeam != SvTeam::None) continue;
```

**⇒ 三层**：

```text
1. **同队 ⇒ 排除**
2. ⇒ **但 `None` 除外**
3. ⇒ **所以 `None` vs `None` 是敌对的**（自由混战）
```

**✅ 与 §347 的"`SV_PresentableTeam` 把 `None` 映射到 1 或 2"配合。**

**⇒ 所以 `None` 在**呈现**上被映射而**逻辑**上仍是互敌。**

**✅ **两个层次。**

### 6.7 而**"不拷 playerState（每帧成本门 §3.3b）"**

**⇒ 三层**：

```text
1. 每帧调用 ⇒ 成本敏感
2. ⇒ **所以只取需要的字段**
3. ⇒ **不拷 playerState 结构**
```

**✅ 与 §348 的"`P5: 每帧零日志`"**同族（**第二个热路径规则**）。**

**⇒ **两条成本纪律**：**

```text
P5         每帧零日志
§3.3b      每帧不拷 playerState
```

### 6.8 而 `enemyCentroidOrigin` 的**`double` 累加**

```cpp
std::array<double, 3> sum{};
...
for (i = 0; i < 3; ++i) sum[i] += state.client.playerState.origin[i];
++count;
...
return std::array<float, 3>{ (float)(sum[0]/count), (float)(sum[1]/count), (float)(sum[2]/count) };
```

**⇒ 三层**：

```text
1. **`double` 累加**
2. ⇒ **`float` 输出**
3. ⇒ **所以中间精度足够**
```

**✅ 一个**正确的数值选择**（float 累加几个值会丢精度，虽然只有 ≤32 个玩家时影响很小）。**

**⚠ 而 `count` 是 `size_t` ⇒ 所以 `sum/count` 是 `double / size_t`。**

**✅ 隐式转换正确。**

## 七、`ZmBarrier` 的**占用者清理**

```cpp
for (auto &occupant : barrier.occupants) {
    if (!occupant) continue;
    const auto damage = entityDamageStates_.find(occupant->entityNum);
    const auto route = actorRoutes_.find(occupant->entityNum);
    if (!entityPool_->resolve(*occupant) ||
        (damage != entityDamageStates_.end() && damage->second.health <= 0) ||
        (route != actorRoutes_.end() && route->second.spawnBarrierPassed))
    {
        barrier.controller.cancel(*occupant);
        occupant.reset();
    }
}
```

### 7.1 三层（三个释放条件）

```text
① 句柄不再可解析（实体消失）
② 受伤状态存在且血量 <= 0（死亡）
③ 路由存在且 `spawnBarrierPassed`（已过屏障）
```

**✅ 与 §353 的"六个分支"**不同**（这是**清理**）。**

**⚠ 而 ③ 的 `spawnBarrierPassed` ⇒ **生成时的屏障通过**。**

**✅ 与 §353 三的 `zmSpawnCrossesBarrier`**配合。**

## 八、`stepZmBarrierMotions` 的**`Commit` 结构**

```cpp
struct Commit {
    BarrierState *barrier;
    BarrierState::Board *board;
    SvEntityHandle handle;
    std::optional<SvZmTearLease> release;
    std::uint32_t started;
    bool settled;
    std::uint8_t slot;
    bool repair;
    bool repairComplete;
};
std::vector<Commit> commits;
```

### 8.1 九层

```text
1. **一个 `Commit` 结构收集所有待提交的变更**
2. ⇒ **`barrier` 与 `board` 是【裸指针】**（有效直到提交）
3. ⇒ **`release` 是一个可选的"撕裂租约"释放**
4. ⇒ **`settled` / `repair` / `repairComplete` 是状态标志**
5. ⇒ **在 `motions` 批里收集运动，`commits` 里收集状态**
6. ⇒ **所以是"先收集后提交"两阶段**
```

**✅ 与 §349 的"staged-then-commit"**第六次。**

**⇒ **本文件的**绝对核心模式**。**

**⚠ 而 `BarrierState *` 与 `Board *` 是**裸指针** ⇒ 所以**依赖 `zmBarriers_` 在提交前不被修改**。**

**⇒ 而 `zmBarriers_` 是 `unordered_map` ⇒ 若期间插入会重哈希 ⇒ **指针失效**。**

**⚠ 一处**潜在风险**（但本函数不插入）。**

**✅ 一个**需要记下的前提**。**

## 九、关键结论

1. **⭐ "一个屏障的 outside 与 inside【就是】图里的节点"`** —— 屏障**由边识别**，解析只是找两个节点索引。
2. **`8.0f`（节点原点）vs `64.0f`（任意目标）** —— 两个不同容差语义。
3. **"半径很紧因为那些是节点原点，不是猜测"`**。
4. **`zmBarriers_` 的键是 `{min, max}` 有序对** —— 与 §353 的双向查配合。
5. **"12.58 把 outside/inside 对作为【边】放进去"`** —— 第九次引用 12.x 文档节。
6. **⭐ `repairableZmBarrierAt` 用 board 的【作者化 home】而不是导航节点** —— 因为 **inside 节点是 AI 路由点而可能坐在走廊很远处，而零售的使用体量在物理窗口处**。
7. **五个距离/高度常量**（112 / 96 / 8 / 64 / 128²）。
8. **`repairZmBarrier` 反向遍历（LIFO）** —— 理由未注释（可能因为最后撕掉的先修）。
9. **⭐ 修复动画两段：150ms 只动 Z（抬升）+ 100ms 只动 X（滑入）**，总 250ms。
10. **`delta = Δ * (1000/duration)` ⇒ delta 的单位是【每秒位移】= 速度** —— 与 §344 的 `positionTrajectoryDelta` 完整闭合。
11. **"整段行程保持画笔为实心"** + **`setBrushModelMotions` 批量重链一次 ⇒ 修复永不留下仅视觉的板子**。
12. **"近似动画 + 精确终态"**（完成后 `position = homePosition`）。
13. **⭐ 七个 `nearestPlayerXxx` 函数复制了【七次】同样的三条件过滤** —— 作者三次注释"同样的活人过滤"。
14. **`nearestPlayerDistance` 用 `sqrt` 而其它六个用平方** —— 因为只有它**返回距离**。
15. **⭐ "数 Z 会让一个在楼梯上的僵尸到一半就停止挥击"`** —— 第二次"故意忽略一个轴"。
16. **`nearestEnemyProbe` 的中文注释** —— `§3.3b` 是**另一套文档编号**（与 `12.x` 并存）。
17. **"None = None 互敌 = FFA"`** —— 而 §347 的 `SV_PresentableTeam` 把它映射到 1/2（呈现 vs 逻辑两层）。
18. **两条成本纪律**：`P5` 每帧零日志、`§3.3b` 每帧不拷 playerState。
19. **`enemyCentroidOrigin` 用 `double` 累加而 `float` 输出**。
20. **屏障占用者清理的三个条件**（句柄失效 / 死亡 / `spawnBarrierPassed`）。
21. **⭐ `Commit` 结构 = 第六次 staged-then-commit**，而它**持裸指针** ⇒ 依赖提交前 `zmBarriers_` 不被修改。

## 十、未闭合点

- `repairZmBarrier` 反向遍历的理由。
- 为什么滑入只动 X 而不动 Y。
- `SvActorNodeSearchRadius` 的值。
- `§3.3b` 文档的位置。
- `zmBarriers_` 插入时机（是否有 mid-step 插入）。
- `sv_snapshot_mp.cpp` 13600 行之后未读取（27,016 行，进度 50%）。
