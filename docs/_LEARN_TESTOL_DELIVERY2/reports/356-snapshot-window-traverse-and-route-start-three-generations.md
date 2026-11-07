# 356 · **"这一条边是【作者化的 AI 协商】，不是一次普通行走"** —— 翻窗的三重例外、路由起点的三代修正（**在墙这边** / **在飞行的航点** / **在脚下的位置**）、`1,063` 条轨的绕圈测量

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 14000–14400 行。

## 二、**翻窗的"唯一例外"**（本组最重要的一段）

### 2.1 那段

```php
// THIS ONE EDGE IS AN AUTHORED AI NEGOTIATION, NOT AN ORDINARY WALK.
// Factory's static collision includes the sandbag/window volume that
// the retail AI mantle is specifically allowed to cross. Sweeping our
// ordinary navigation capsule against that volume stopped every
// traverse at its first sample: the lead actor stayed in the opening
// forever and the correctly queued actors consequently stayed at the
// spawn side forever.
//
// Do not generalise this exception. It exists only after all six
// boards on route.spawnBarrier have been removed, only while the
// actor owns that exact map-authored outside->inside negotiation, and
// only for this selected original clip's duration. Every approach leg
// and every post-window leg still goes through the world capsule
// trace below, so a zombie cannot use this to walk through any wall.
```

### 2.2 十三层

```text
1. **这一条边是一个【作者化的 AI 协商】，不是一次普通行走**
2. ⇒ **Factory 的静态碰撞包含沙袋/窗口体**
3. ⇒ **而零售 AI 的翻越是【被特别允许】穿过它的**
4. ⇒ **把我们普通的导航胶囊对着那个体扫**
5. ⇒ **在【第一个采样】就停掉了每一次翻越**
6. ⇒ **首席 actor 永远停在开口里**
7. ⇒ **而正确排队的 actor 于是永远停在生成侧**
8. ⇒ **不要把这个例外一般化**
9. ⇒ **它只在 `route.spawnBarrier` 上的【全部六块板】被移除之后存在**
10. ⇒ **只在 actor 拥有那个精确的地图作者化 outside→inside 协商时**
11. ⇒ **只为这个选中的原始片段的时长**
12. ⇒ **每一条接近腿与每一条过窗后的腿仍走下面的世界胶囊 trace**
13. ⇒ **所以一个僵尸不能利用这个穿任何墙**
```

### 2.3 **三个精确的限定**

```text
① 六块板全部移除（`torn >= boardClipHandles.size()`）
② 该 actor 拥有那个精确的 outside→inside 协商
③ 只为该 clip 的时长
```

**✅ 与 §346 的"一个在这里缺失的 eType 拒掉整帧"**不同** —— 这是**一个极窄的例外**。**

**⇒ **"不要一般化这个例外"是一条明确的设计禁令。**

**⚠ 而"六块板"是一个**具体数字**（与 §354 的 `boards.size()` 一致）。**

**✅ **第三次确认"六块板"。**

### 2.4 而**"在第一个采样就停掉了"**

**✅ 与 §355 的"脚会打滑"、§353 的"到一半停止挥击"**同族（**第五次具体症状**）。**

**⇒ 而"**永远停在开口里**"是一个**具体的姿态**。**

### 2.5 而**翻窗的完整时间线**

```cpp
const auto &clip = SvZmWindowClips[route.windowTraverseVariant];
const auto elapsed = std::min((float)(now - route.windowTraverseStartedAt), clip.duration());
const auto previousOrigin = entity.currentOrigin;
const auto traverseOrigin = route.windowTraverseLanding ? previousOrigin
    : SV_ZmWindowRootWorld(route.windowTraverseVariant, elapsed,
                           route.windowTraverseStart, route.windowTraverseYaw);
entity.currentOrigin = traverseOrigin;
const auto yaw = route.windowTraverseYaw;
entity.currentAngles[1] = yaw;
entity.networkState.origin = entity.currentOrigin;
entity.networkState.angles = { 0.0f, yaw, 0.0f };
const auto perSecond = 1000.0f / (float)frameMilliseconds;
entity.networkState.actorVelocity = { Δx*perSecond, Δy*perSecond, Δz*perSecond };
if (route.windowTraverseAnim && entity.networkState.actorAnimIndex != route.windowTraverseAnim) {
    entity.networkState.actorAnimIndex = route.windowTraverseAnim;
    entity.networkState.actorAnimStartTime = route.windowTraverseStartedAt;
}
```

**⇒ 九层**：

```text
1. **`elapsed` 被 `min` 到 `clip.duration()`**
2. ⇒ **`windowTraverseLanding` 时位置【冻结】**（`previousOrigin`）
3. ⇒ **否则用 `SV_ZmWindowRootWorld(变体, elapsed, 起点, yaw)`** —— **参数化曲线**
4. ⇒ **yaw 是固定的 `windowTraverseYaw`**（不是速度）
5. ⇒ **速度 = 相邻帧差分 × perSecond**
6. ⇒ **动画在第一次不匹配时设，而 `animStartTime = windowTraverseStartedAt`**（**保持相位**）
```

**✅ 与 §355 的"`animStartTime = negotiationStartedAt + walkingHandoff`"**完全同族（**第二次相位保持**）。**

### 2.6 而**落地检测的六项**

```cpp
if (elapsed >= clip.duration()) {
    route.windowTraverseLanding = true;
    auto floorStart = entity.currentOrigin;  auto floorEnd = floorStart;
    floorStart[2] += 18.0f;  floorEnd[2] -= 24.0f;
    constexpr TraceBounds landingFoot{ .midpoint={0,0,0.5f}, .halfSize={0.5f,0.5f,0.5f} };
    const auto floor = traceCapsule(floorStart, floorEnd, landingFoot, ActorWorldContentMask, movementFilter);
    if (!floor || floor->startSolid || floor->allSolid || floor->fraction >= 1.0f || floor->normal[2] < .7f)
    {
        entity.networkState.actorVelocity = {};
        continue;
    }
    const auto grounded = floorStart[2] + (floorEnd[2]-floorStart[2]) * clamp(floor->fraction, 0.0f, 1.0f);
    entity.currentOrigin[2] = SV_ZmSettleWindowHeight(entity.currentOrigin[2], grounded, frameMilliseconds);
    ...
    if (std::abs(entity.currentOrigin[2] - grounded) > .01f) continue;
    ...
}
```

**⇒ 十层**：

```text
1. **片段播完 ⇒ 进入落地阶段**
2. ⇒ **胶囊从 `z+18` 到 `z-24`**（共 42 单位）
3. ⇒ **六个拒绝条件**：
     · 无命中
     · `startSolid`
     · `allSolid`
     · `fraction >= 1.0`（**没打到地面**）
     · **`normal[2] < 0.7`**（**斜坡太陡**）
4. ⇒ **`grounded = floorStart[2] + Δz * fraction`**
5. ⇒ **`SV_ZmSettleWindowHeight` 平滑沉降**
6. ⇒ **`|currentZ - grounded| > 0.01` ⇒ 继续等**（下一帧再沉降）
```

**✅ 与 §355 的"`retireAt = now + downMilliseconds`"**不同** —— 这里是**迭代收敛**（每帧逼近）。**

**⚠ 而 `normal[2] < 0.7` 是一个**坡度阈值**（约 45°）。**

**✅ 具体：`cos(θ) >= 0.7` ⇒ `θ <= 45.6°`。**

### 2.7 而**完成后的十二项重置 + "在完成快照【本身】上打戳"**

```php
route.windowTraverseActive = false;
route.windowTraverseLanding = false;
route.spawnBarrierPassed = true;
route.wallFollowWaypoint.reset();
route.wallFollowSign = 0;
route.previousNode = SV_ZmNavNearestNode(zmNavGraph_, entity.currentOrigin, SvActorNodeSearchRadius);
route.nodes.clear();
route.cursor = 0;
route.planned = false;
route.blockedCandidate.reset();
route.directPursuitClear = false;
entity.networkState.actorVelocity = {};
if (zmActorWalkAnim_) {
    entity.networkState.actorAnimIndex = zmActorWalkAnim_;
    entity.networkState.actorAnimStartTime = now;
}
```

**⇒ 而注释解释理由：**

```php
// The retail Factory handoff changes from traversal to
// walk-fast at the inside node.  Stamp it on the completion
// snapshot itself; waiting for the next step left the completed
// actor owned by the traversal pose for another frame, and the
// old periodic command rotation could extend that stale pose by
// more than a second.
```

**⇒ 七层**：

```text
1. **零售 Factory 的交接在 inside 节点从"翻越"变到"快走"**
2. ⇒ **在【完成快照本身】上打戳**
3. ⇒ **等下一步让完成的 actor 被翻越姿态再拥有【一帧】**
4. ⇒ **而旧的周期命令轮换能把那个陈旧姿态延长【超过一秒】**
5. ⇒ 所以必须在这一帧设
```

**✅ 与 §347 的"重复施加命令让动画看起来冻结"**同族（**第三次"姿态陈旧"**）。**

**⚠ 而"超过一秒"来自 §347 的"每个 actor 每秒一对"。**

**✅ **两个事实互相印证。**

### 2.8 而**"重新锚定路由在落地的 actor 上，不是它背后的那个标记"**

```php
// Original root endpoints extend past the inside marker.
// Re-anchor routing at the landed actor, not behind it at
// that marker (v6 otherwise walks backwards about 44 units).
route.previousNode = SV_ZmNavNearestNode(zmNavGraph_, entity.currentOrigin, SvActorNodeSearchRadius);
```

**⇒ 四层**：

```text
1. **原始的根端点【伸过】 inside 标记**
2. ⇒ **所以把路由重锚在落地的 actor 上**
3. ⇒ **而不是它背后的那个标记**
4. ⇒ **（v6 否则向后走约 44 单位）**
```

**✅ 一个**具体的 44 单位回退**被修正。**

**⚠ 而"v6"是**一个版本标识**（不是 §354 的 `v6` 遍历？）。**

**⇒ 可能是**同一个 v6**（traverse-v6，§347 提过"traverse-v6 的实测停顿"）。**

**✅ 与 §347 的"traverse-v6 在窗口处约两秒冻结"**配合。**

**⇒ **第三次提到 v6。**

## 三、**路由起点的三代修正**（本组第二重要）

### 3.1 第一代：**从 `actorGoal` 开始 ⇒ 走原地**

```php
// WHERE THIS ACTOR JOINS THE GRAPH, and getting this wrong makes it walk in
// circles rather than walk badly.
//
// THE FIRST ROUTE STARTS ON THE SPAWN SIDE OF THE WALL.
//
// `actorGoal` is the spawner's authored entrance/window node, not the node
// occupied by the newly created actor.  Treating it as the route start made
// cursor zero point through solid world geometry: for example Factory's
// (-21,961,14) receiver spawn was sent directly to node 921 at
// (-328,768,24), while node 930 is only 16 units from the actor on the same
// side of the wall.  The collision trace correctly stopped that invalid leg
// at the wall, leaving every actor walking in place forever.
```

**⇒ 十层**：

```text
1. **这个 actor 在哪里接入图，而搞错这个让它【绕圈】而不是走得差**
2. ⇒ **第一条路由从【墙的生成侧】开始**
3. ⇒ **`actorGoal` 是生成器的作者化入口/窗口节点，不是新创建 actor 所占的节点**
4. ⇒ **把它当路由起点让游标零【穿过实心世界几何】**
5. ⇒ **例：Factory 的 `(-21,961,14)` 接收器出生被直接送到 `(-328,768,24)` 的节点 921**
6. ⇒ **而节点 930 距 actor 只有 16 单位且在墙的同一侧**
7. ⇒ **碰撞 trace 正确地停住了那条无效腿**
8. ⇒ **留下每一个 actor【永远原地走】**
9. ⇒ 所以**在离 actor 自己最近的节点接入图**
10. ⇒ **而下面的强制屏障路由把它经生成侧的路径节点带到生成器指定的 outside 节点，撕掉那个窗，并穿过 outside→inside 协商边**
```

**✅ 而"`actorGoal` 仍是选择【哪个屏障属于这个生成器】的权威"`** —— 一个精确的职责分离。

**⚠ 而"16 单位"vs"巨大距离" ⇒ **第一个就错得很远**。**

### 3.2 第二代：**每次重规划从最近节点开始 ⇒ 绕圈**

```php
// EVERY LATER ROUTE STARTS AT THE WAYPOINT ALREADY BEING WALKED TO, and NOT
// at the nearest node. Re-planning from the nearest node is what caused the
// circling: an actor mid-leg is still nearest the node it just LEFT, so A*
// handed back a route whose first waypoint was behind it, it turned round,
// and a second later the replan did it again. Measured at 79 u/s: two of four
// actors walked 151 units for 11 and 15 units of net progress. Continuing
// from the waypoint in flight cannot backtrack by construction -- the leg
// being walked is preserved and only the remainder is re-planned.
```

**⇒ 十一层**：

```text
1. **每一条【之后的】路由从【已经正在被走的那个航点】开始**，而不是最近节点
2. ⇒ **从最近节点重规划正是绕圈的原因**
3. ⇒ **一个在腿中途的 actor 仍【最靠近它刚离开的】节点**
4. ⇒ **所以 A* 交回一条第一航点在它【身后】的路由**
5. ⇒ **它转身，而一秒后重规划又做一次**
6. ⇒ **在 79 单位/秒下测量：四个 actor 里两个为 11 与 15 单位的净进展走了 151 单位**
7. ⇒ **从飞行中的航点继续在【构造上】不能回退**
8. ⇒ **正在走的腿被保留而只有剩余部分被重规划**
```

### 3.3 **"151 单位换来 11 与 15 单位的净进展"**

**✅ 一个**极精确的量化**。**

**⇒ `151 / 11 = 13.7×` 与 `151 / 15 = 10.1×` 的**浪费比**。**

**⚠ 而"四个里两个" ⇒ **50% 的 actor 受影响**。**

**✅ 一个**明确的失败率**。**

### 3.4 第三代：**耗尽的路由从 actor 站立处开始**

```php
// AND AN EXHAUSTED ROUTE STARTS FROM WHERE THE ACTOR IS STANDING.
//
// This fell through to `goalNode` -- the SPAWNER's own node -- so an
// actor that finished its route was handed a fresh one beginning back at
// its spawn closet. It turned round, walked all the way back, re-planned,
// and came forward again. Reported from the map as zombies "walking and
// resetting back to the place they're walking", and it is a loop rather
// than a teleport.
//
// The comment above is about a MID-LEG replan, where nearest-node picks
// the node just left and backtracks. A FINISHED route is the opposite
// case: the actor is stationary on its last waypoint, which IS a node
// origin, so nearest-node is exact there. It falls back to the spawner's
// node only if the actor somehow stands near none. That fallback is now
// deliberately gone: retail filters graph-entry candidates with a capsule
// sight trace, and returning to an unverified spawn node recreates the
// through-wall route this selection is meant to prevent.
```

**⇒ 十四层**：

```text
1. **而一个耗尽的路由从【actor 站立的地方】开始**
2. ⇒ **这过去落到 `goalNode` —— 生成器【自己的】节点**
3. ⇒ **所以一个走完路由的 actor 被交给一条从它的【生成壁橱】开始的新路由**
4. ⇒ **它转身，走回去，重规划，然后再向前来**
5. ⇒ **从地图上报告为僵尸"走着然后又重置回它们正在走的地方"**
6. ⇒ **而它是一个【循环】而不是一次传送**
7. ⇒ **上面的注释是关于【腿中途】的重规划，那里最近节点选的是刚离开的节点而回退**
8. ⇒ **一个【完成】的路由是相反的情况**
9. ⇒ **actor 静止在它最后一个航点上，而那【就是】一个节点原点**
10. ⇒ **所以最近节点在那里是【精确的】**
11. ⇒ **它只在 actor 莫名其妙站在无节点附近时才回退到生成器的节点**
12. ⇒ **那个回退现在被【有意移除】**
13. ⇒ **因为零售用胶囊视线 trace 过滤图入口候选**
14. ⇒ **而回到一个未验证的生成节点会重建这个选择本来要防止的【穿墙路由】**
```

**✅ 三代修正的**完整记录**：**

```text
第一代  从 actorGoal 开始           ⇒ 穿过实心几何 ⇒ 原地走
第二代  每次从最近节点              ⇒ 腿中途回退 ⇒ 绕圈（151/11）
第三代  第一路由从最近可见节点
        后续从飞行中的航点
        耗尽的从站立处              ⇒ 正确
```

**✅ 与 §351 的"实体编号三个代际"**完全同族（**第二次"三代演进"**）。**

**⇒ **本文件的一个显著模式：用"代际"记录修正史。**

## 四、**`NodeJoinBounds` 与视线胶囊**（本组第三重要）

### 4.1 那段

```php
// Match retail Path_NearestNodeNotCrossPlanes: nearby candidates are
// distance ordered but a zombie joins the graph through the first node
// reached by a narrow sight capsule. Pure nearest-node attached live
// actor 705 to node 767 across a wall; A* then emitted 767 as waypoint
// zero and the actor could only slide against that wall forever.
constexpr TraceBounds NodeJoinBounds{
    .midpoint = { 0.0f, 0.0f, 32.5f },
    .halfSize = { 1.0f, 1.0f, 15.5f },
};
```

### 4.2 七层

```text
1. **匹配零售的 `Path_NearestNodeNotCrossPlanes`**
2. ⇒ **附近的候选按距离排序**
3. ⇒ **但一个僵尸通过【一个窄视线胶囊到达的第一个节点】接入图**
4. ⇒ **纯最近节点把活的 actor 705 接到墙另一侧的节点 767**
5. ⇒ **而 A* 然后把 767 作为航点零发出**
6. ⇒ **而 actor 只能永远对着那堵墙滑动**
```

### 4.3 而 `NodeJoinBounds` 的**尺寸**

```text
midpoint  z = 32.5
halfSize  x = 1.0, y = 1.0, z = 15.5
```

**⇒ 所以：**

```text
x ∈ [-1, 1]      宽 2
y ∈ [-1, 1]      深 2
z ∈ [17, 48]     高 31
```

**✅ 一个**很窄的垂直胶囊**（2×2×31）。**

**⚠ 与 §355 的 `landingFoot`（1×1×1）**不同**。**

**⇒ 两个不同的 trace 体。**

**✅ 一个是"视线"一个是"脚"。**

### 4.4 而**"actor 只能永远对着那堵墙滑动"**

**✅ 与 §356 二.4 的"永远停在开口里"、§355 的"脚会打滑"**同族（**第六次具体症状**）。**

### 4.5 而**`findVisibleStart` 的两级半径**

```cpp
const auto findVisibleStart = [&](float radius) {
    return SV_ZmNavNearestNodeIf(zmNavGraph_, entity.currentOrigin, radius,
        [&](const std::uint16_t nodeIndex) {
            if (!inRequiredComponent(nodeIndex)) return false;
            const auto hit = traceCapsule(entity.currentOrigin, zmNavGraph_.nodes[nodeIndex],
                NodeJoinBounds, ActorWorldContentMask, movementFilter);
            return !hit || (!hit->allSolid && !hit->startSolid && hit->fraction >= 1.0f);
        });
};
auto visibleNode = findVisibleStart(128.0f);
// Project boundary: Factory spawn453.5,1282 is151 units from
// its nearest authored pathnode. The128-unit initial search
// leaves it unplanned forever, before support/grounding runs.
// Expand only first attachment and retain the same component
// and native capsule-sight predicates. No origin teleport.
if (!visibleNode) visibleNode = findVisibleStart(256.0f);
```

**⇒ 九层**：

```text
1. **两个半径：128 然后 256**
2. ⇒ **两个谓词**：在同要求的分量里 且 视线胶囊无阻挡
3. ⇒ **`!hit || (!allSolid && !startSolid && fraction >= 1.0)`**
4. ⇒ **"单位/源-only 配置没有原生 runner"** ⇒ `!hit` 也算可见
5. ⇒ **`Factory spawn453.5,1282` 距它最近的作者化路径节点 151 单位**
6. ⇒ **128 单位的初始搜索让它永远未规划**，在支撑/落地运行之前
7. ⇒ **只扩展【第一次接入】而保留同样的分量与胶囊视线谓词**
8. ⇒ **没有 origin 传送**
```

**✅ 与 §350 的"没有表的图回退到顺序编号"**同族（**两级回退**）。**

**⚠ 而"151 单位"恰好超过 128 ⇒ 所以第一级失败。**

**✅ 一个**精确的边界情形**。**

### 4.6 而**"没有 origin 传送"**

**✅ 与 §355 的"不猜"**同族（**第十五次"不要猜/不要伪造"**）。**

**⇒ 三层**：

```text
1. 可以扩展搜索半径
2. ⇒ **但不能传送 actor**
3. ⇒ **所以是"扩大视野"而不是"移动身体"**
```

## 五、**分量的强制**（本组第四重要）

```php
// A geometrically nearest node can be an isolated decoration. Factory's
// (-417,-730,-116) receiver spawn is 22 units from isolated node 751, but
// only 63 units from node 752, which is connected to its assigned window.
// On the first plan choose the nearest node in the window's component;
// otherwise that authored spawn produces an empty route forever.
if (!route.planned && route.spawnBarrier) {
    const auto barrier = zmBarriers_.find(*route.spawnBarrier);
    if (barrier != zmBarriers_.end() && barrier->second.outsideNode < zmNavComponent_.size()) {
        requiredStartComponent = zmNavComponent_[barrier->second.outsideNode];
    }
}
```

**⇒ 八层**：

```text
1. **一个几何上最近的节点可以是一个【孤立的装饰】**
2. ⇒ **Factory 的 `(-417,-730,-116)` 接收器出生距【孤立节点 751】22 单位**
3. ⇒ **而距【节点 752】只有 63 单位**
4. ⇒ **而 752 与它指定的窗口相连**
5. ⇒ **在第一次规划时选窗口【分量里】的最近节点**
6. ⇒ **否则那个作者化出生永远产出一条【空路由】**
7. ⇒ 所以 `requiredStartComponent = zmNavComponent_[outsideNode]`
```

**✅ 与 §352 的"1100 个节点里主分量 837 个"**配合。**

**⇒ 所以**263 个节点是"孤立/装饰"的。**

**⚠ 而"22 单位 vs 63 单位"⇒ **更近的是孤立的**。**

**✅ 一个**极具体的陷阱**。**

## 六、**"不要因为下一个航点是 inside 就推断屏障已过"**

```php
// Do not infer that the barrier has been passed merely because the
// route's NEXT waypoint is its inside node.  At that moment the actor
// is still standing outside, ready to begin the timed negotiation.
// windowTraverseActive is the sole owner of this transition and marks
// spawnBarrierPassed only after the measured crossing has completed.
```

**⇒ 六层**：

```text
1. **不要仅仅因为路由的【下一个】航点是它的 inside 节点就推断屏障已过**
2. ⇒ **在那个时刻 actor 仍站在【外面】**
3. ⇒ **准备开始那个有时间限的协商**
4. ⇒ **`windowTraverseActive` 是这个转换的【唯一所有者】**
5. ⇒ **而它只在测量的穿越完成之后标记 `spawnBarrierPassed`**
```

**✅ 与 §345 的"唯一的写入路径"**第三次（**唯一所有权**）。**

### 6.1 而**"这一条边是方向性的"**

```php
// The assigned barrier is directional: actors approach it from
// outside and finish on the inside.  Treating the pair as unordered
// made the stale inside->outside leg look like another valid
// entrance, so the completed traverse restarted forever.
assignedWindowEdge = barrier != zmBarriers_.end() &&
    from == barrier->second.outsideNode &&
    to == barrier->second.insideNode;
```

**⇒ 五层**：

```text
1. **指定的屏障是【方向性】的**
2. ⇒ **actor 从 outside 接近而在 inside 结束**
3. ⇒ **把对当作无序让陈旧的 inside→outside 腿看起来像另一个有效入口**
4. ⇒ **所以完成的穿越【永远重启】**
5. ⇒ 所以显式检查 `from == outside && to == inside`
```

**⚠ 而 §353 三.5 的 `zmSpawnCrossesBarrier` 用**双向查**！**

**⇒ 两处**不同的方向性假设**：**

```text
zmSpawnCrossesBarrier  双向（图无向）
assignedWindowEdge     单向（屏障有方向）
```

**⚠ 一处**需要区分的差异**。**

**✅ 而理由不同（一个是"任意屏障"，一个是"指定屏障"）。**

### 6.2 而**"不要在当前腿【就是】指定窗口时重规划"**

```php
// Never replan while the current leg IS the assigned window.  Replanning
// from route.nodes[cursor] uses the inside endpoint as the new start and
// constructs inside->outside->inside; between tears that advanced actors
// through the wall even though barrierHolds was otherwise correct.
const auto stale = !assignedWindowEdge && SV_ZmRouteNeedsReplan(...);
```

**⇒ 六层**：

```text
1. **在当前腿【就是】指定的窗口时绝不重规划**
2. ⇒ **从 `route.nodes[cursor]` 重规划用 inside 端点作为新起点**
3. ⇒ **而构造 inside→outside→inside**
4. ⇒ **在两次撕除之间那让 actor 【穿过墙】推进**
5. ⇒ **即使 `barrierHolds` 在其他方面是正确的**
6. ⇒ 所以 `stale = !assignedWindowEdge && ...`
```

**✅ 一个**极精确的守卫**（`!assignedWindowEdge` 与整个 `stale` 表达式与）。**

**⚠ 而注释说"即使 `barrierHolds` 正确"⇒ **两道独立防线都被绕过**。**

**✅ 与 §350 的"一个画笔模型偏离表就推翻整帧"**同族（**多道防线仍可能同时失效**）。

## 七、`routeAvoidingKnownBlocks` 的**"加入被禁止的屏障"**

```cpp
const auto routeAvoidingKnownBlocks = [&](const std::uint16_t from,
                                           const std::uint16_t to,
                                           const bool blockAssignedWindow) {
    auto forbidden = route.blockedEdges;
    if (blockAssignedWindow && route.spawnBarrier &&
        std::ranges::find(forbidden, *route.spawnBarrier) == forbidden.end())
    {
        forbidden.push_back(*route.spawnBarrier);
    }
    return SV_ZmNavRouteAvoidingEdges(zmNavGraph_, from, to, forbidden);
};
```

### 7.1 四层

```text
1. **从 `route.blockedEdges` 开始**
2. ⇒ **若要求阻塞指定窗口 且 它不在表里**
3. ⇒ **加入**
4. ⇒ **用 `SV_ZmNavRouteAvoidingEdges` 规划**
```

**✅ 一个**三处复用**的 lambda（`blockAssignedWindow` 两次 true 一次 false）。**

### 7.2 而**两段路由的拼接**

```cpp
route.nodes = routeAvoidingKnownBlocks(*startNode, barrier->second.outsideNode, false);
if (!route.nodes.empty()) {
    if (route.nodes.back() != barrier->second.insideNode)
        route.nodes.push_back(barrier->second.insideNode);
    auto insideToPlayer = routeAvoidingKnownBlocks(
        barrier->second.insideNode, *destinationNode, true);
    if (!insideToPlayer.empty()) {
        route.nodes.insert(route.nodes.end(), std::next(insideToPlayer.begin()), insideToPlayer.end());
    }
    // If the measured graph has no interior continuation,
    // retain the valid prefix through the assigned window.
    // Parking on the inside is safer than reversing through
    // that same window or discarding the entire spawn route.
}
```

**⇒ 八层**：

```text
1. **第一段：startNode → outsideNode（不阻塞窗口）**
2. ⇒ **若第二段的最后一个不是 inside ⇒ 【强制推入】 inside**
3. ⇒ **第二段：inside → destination（阻塞窗口）**
4. ⇒ **若第二段非空 ⇒ 跳过它的第一个节点（避免重复 inside）**
5. ⇒ **若第二段为空 ⇒ 只保留到窗口的前缀**
6. ⇒ **"停在 inside 上比反过来穿同一个窗口或丢弃整条生成路由都安全"**
```

**✅ 与 §355 的"没有目标就站着不动"**同族（**"停着比猜着好"**）。**

**⇒ **一个极清晰的三级降级**：**

```text
完整两段   ⇒ 最好
只有前缀   ⇒ 停在 inside（安全）
空路由     ⇒ 重规划
```

## 八、`SV_ZmNavRouteToClosestReachableNode` 的**回退**

```php
// OpenBLOPS Actor_FindPathToGoalDirectInternal selects a
// Path_FindCloseNode when the exact goal node cannot be
// used. Our demo graph has legitimate uncovered patches;
// route to the closest node reachable under the SAME edge
// rules rather than parking on an unrelated fallback node.
route.nodes = SV_ZmNavRouteToClosestReachableNode(
    zmNavGraph_, *startNode, *playerPosition,
    SvActorNodeSearchRadius, SvZmNavHeightTolerance, forbidden);
```

**⇒ 六层**：

```text
1. **`OpenBLOPS Actor_FindPathToGoalDirectInternal` 在精确目标节点不能用时选一个 `Path_FindCloseNode`**
2. ⇒ **我们的 demo 图有【合法的未覆盖斑块】**
3. ⇒ **在【同样的边规则】下路由到最近可达节点**
4. ⇒ **而不是停在一个【无关的】回退节点**
5. ⇒ 所以 `SV_ZmNavRouteToClosestReachableNode`（带 `forbidden`）
```

**✅ 与 §355 的"不继续通往翻越的那条路由"**同族（**第三次引用 OpenBLOPS**）。**

**⚠ 而"合法的未覆盖斑块"承认**图的完整性不足**。**

**✅ 与 §352 的"263 个孤立节点"配合。**

## 九、**`actorGoal` 的距离分配（128 单位）**

```cpp
route.spawnBarrierResolved = true;
constexpr float MaximumGoalToBarrierDistance = 128.0f;
auto nearest = MaximumGoalToBarrierDistance * MaximumGoalToBarrierDistance;
const auto measured = zmNavGraph_.spawnBarrierByGoal.find(entity.networkState.actorGoal);
if (measured != end && zmBarriers_.contains(measured->second))
    route.spawnBarrier = measured->second;
for (const auto &[edge, barrier] : zmBarriers_) {
    if (measured != end) break;
    const auto &outside = zmNavGraph_.nodes[barrier.outsideNode];
    ... if (distance > nearest) continue;
    nearest = distance; route.spawnBarrier = edge;
}
```

### 9.1 六层

```text
1. **只解析一次**（`spawnBarrierResolved`）
2. ⇒ **先查测量的映射表**
3. ⇒ **有 ⇒ 用它（而不管距离）**
4. ⇒ **没有 ⇒ 在 128 单位内找最近的 outside 节点**
5. ⇒ **`measured != end` 时立即 break**（不覆盖）
6. ⇒ **所以测量优先于距离**
```

**✅ 与 §353 三.4 的"① 查表"**完全一致 ✓**

**⇒ **第二次确认"表优先于几何"。**

### 9.2 而**四个测量的映射**

```php
// Factory's receiver goals are 36..82 units from their intended window
// traversal (auto410->pf707, auto411->pf680, auto412->pf679,
// auto413->pf683). Distance-only auto414->pf682 was disproved by early
// demo actors723/670/713: auto414 also descends to pf683. Explicit
// measured mappings below take precedence. A shortest route directly to the
// player can legally find an already-open way around and used to make the
// actors skip those windows completely.
```

**⇒ 八层**：

```text
1. **Factory 的接收器目标距它们【打算的】窗口穿越 36..82 单位**
2. ⇒ **四个映射**：
     · `auto410 -> pf707`
     · `auto411 -> pf680`
     · `auto412 -> pf679`
     · `auto413 -> pf683`
3. ⇒ **纯距离的 `auto414 -> pf682` 被【早期 demo 的 actors 723/670/713】推翻**
4. ⇒ **`auto414` 也下降到 `pf683`**
5. ⇒ **下面的显式测量映射优先**
6. ⇒ **一条直接到玩家的最短路由可以合法地找到一条已经打开的路绕过**
7. ⇒ **而【以前】让那些 actor 完全跳过那些窗口**
```

**✅ 与 §353 三.3 的 `auto414 → pf683`**完全一致 ✓**

**⇒ **第二次确认。而这里是完整的四个映射。**

**⚠ 而"36..82 单位"是一个**范围**（不是固定值）。**

**⇒ 所以**距离判定在 128 内会命中多个屏障**。**

## 十、关键结论

1. **⭐ 翻窗的"唯一例外"`** —— 因为 Factory 的沙袋/窗口体在静态碰撞里，而零售 AI 的翻越**被特别允许**穿过。
2. **"在第一个采样就停掉了每一次翻越 ⇒ 首席 actor 永远停在开口里"`** —— 第五次具体症状。
3. **三个精确限定**（六块板全移除 / 拥有那个精确协商 / 只为该 clip 时长）+ **明确禁令"不要一般化这个例外"`**。
4. **翻窗的完整时间线**：参数化曲线 `SV_ZmWindowRootWorld`、固定 yaw、动画相位保持。
5. **落地检测的六项**（`normal[2] < 0.7` ⇒ 坡度 ≤ 45.6°）+ **迭代沉降**（`|Δz| > 0.01` 继续等）。
6. **"在完成快照【本身】上打戳"`** —— 否则陈旧姿态被周期命令轮换延长**超过一秒**（第三次姿态陈旧）。
7. **"重锚在落地的 actor 上而不是它背后的标记"`** —— 修正**44 单位**的回退（第三次提 v6）。
8. **⭐⭐ 路由起点的三代修正**：`actorGoal`（穿墙 ⇒ 原地走）→ 最近节点（腿中途回退 ⇒ 绕圈）→ 飞行中的航点 / 站立处。
9. **"151 单位换来 11 与 15 单位的净进展"`（13.7× / 10.1× 浪费）—— 四个 actor 里两个受影响。
10. **"从飞行中的航点继续在【构造上】不能回退"`** —— 保留正在走的腿、只重规划剩余。
11. **"耗尽的路由从站立处开始"** —— 因为完成时 actor 静止在节点原点上，**最近节点在那里是精确的**。
12. **"一个循环而不是一次传送"`** —— 玩家报告"走着又重置回正在走的地方"。
13. **`NodeJoinBounds` = 2×2×31 的窄垂直胶囊**（`z ∈ [17,48]`），匹配零售 `Path_NearestNodeNotCrossPlanes`。
14. **"纯最近节点把 actor 705 接到墙另一侧的 767 ⇒ 只能永远对着那堵墙滑动"`** —— 第六次具体症状。
15. **两级半径 128 → 256**（`Factory spawn453.5,1282` 距最近路径节点 **151** 单位）+ **"没有 origin 传送"`**（第十五次"不要猜"）。
16. **⭐ 分量的强制**：`(-417,-730,-116)` 距**孤立节点 751** 只有 22 单位，而距**相连的 752** 63 单位 —— **更近的是孤立的**。
17. **"不要因为下一个航点是 inside 就推断屏障已过"`** —— `windowTraverseActive` 是**唯一所有者**（第三次唯一所有权）。
18. **"指定的屏障是【方向性】的"`** —— 与 §353 的 `zmSpawnCrossesBarrier` 双向查**不同**（一个任意一个指定）。
19. **"不要在当前腿就是指定窗口时重规划"`** —— 否则构造 inside→outside→inside ⇒ **穿墙推进**，即使 `barrierHolds` 正确。
20. **两段路由拼接的三级降级**（完整 / 停在 inside / 重规划）—— "停着比猜着好"。
21. **`SV_ZmNavRouteToClosestReachableNode` 的"在同样的边规则下"，而不是"停在一个无关的回退节点"`** —— 第三次引用 OpenBLOPS。
22. **"合法的未覆盖斑块"`** —— 承认图的完整性不足（配 §352 的 263 个孤立节点）。
23. **`actorGoal` 的 128 单位距离分配，而测量的映射优先于几何距离**（第二次确认"表优先"）。
24. **四个完整的测量映射**（`auto410→pf707`、`auto411→pf680`、`auto412→pf679`、`auto413→pf683`）而 **`auto414→pf682` 被早期 demo 推翻**。
25. **"一条直接到玩家的最短路由可以合法地找到一条已经打开的路绕过 ⇒ 让 actor 完全跳过那些窗口"`**。

## 十一、未闭合点

- `SvZmWindowClips` 的变体数（至少 six 相关）。
- `SV_ZmWindowRootWorld` 的曲线构造。
- `SV_ZmSettleWindowHeight` 的沉降速率。
- `v6` 的确切指代（traverse-v6？）。
- 为什么 `assignedWindowEdge` 单向而 `zmSpawnCrossesBarrier` 双向。
- `sv_snapshot_mp.cpp` 14400 行之后未读取（27,016 行，进度 53%）。
