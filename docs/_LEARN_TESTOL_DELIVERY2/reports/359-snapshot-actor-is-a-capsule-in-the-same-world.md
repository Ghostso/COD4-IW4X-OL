# 359 · **"一个 actor 是一个胶囊，在玩家走的同一个世界里"（12.162/12.163）** —— 两个导航包围盒的晋升、两种让行、18 单位步进、`1500ms` 的边黑名单

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 15200–15600 行。

## 二、**翻窗的启动（十个字段）**（本组第四重要）

```cpp
auto variant = (unsigned)((entityNum ^ actorHandle.generation) & 1u);
if (!zmNavGraph_.windowTraverseAnimations[variant]) variant ^= 1u;
const auto clipAlias = zmNavGraph_.windowTraverseAnimations[variant];
if (!clipAlias) { entity.networkState.actorVelocity = {}; continue; }
route.windowTraverseVariant = variant;
route.windowTraverseYaw = atan2(inside[1]-outside[1], inside[0]-outside[0]) * 180/PI;
route.windowTraverseStart = entity.currentOrigin;
route.windowTraverseStart[2] = groundedZ;
route.windowTraverseEnd = SV_ZmWindowRootWorld(variant, SvZmWindowClips[variant].duration(),
    route.windowTraverseStart, route.windowTraverseYaw);
route.windowTraverseEndNode = barrier->second.insideNode;
route.windowTraverseAnim = clipAlias;
route.windowTraverseStartedAt = now;
route.windowTraverseActive = true;
route.windowTraverseLanding = false;
```

### 2.1 八层

```text
1. **变体 = `(entityNum ^ generation) & 1`** ⇒ 0 或 1（**v6 或 v7**）
2. ⇒ **若该变体的动画别名不存在 ⇒ 取另一个**
3. ⇒ **两个都没有 ⇒ 停住**（不发一个缺失的别名）
4. ⇒ **起点用 `groundedZ`**（不是 `currentOrigin[2]`）
5. ⇒ **终点 = `SV_ZmWindowRootWorld(变体, 时长, 起点, yaw)`** ⇒ **预先算好**
6. ⇒ **`windowTraverseEndNode = insideNode`**
7. ⇒ **`startedAt = now`**
8. ⇒ **`active = true` / `landing = false`**
```

**✅ 与 §358 的"v6 与 v7 都在这些窗口被观察到"**完全一致 ✓**

**⇒ 而这里给出**选择规则**：`(entityNum ^ generation) & 1`。**

**✅ 一个**确定性的伪随机变体**（同一 actor 稳定）。**

**⚠ 而 `entityNum ^ generation` 使**同一个号的新生 actor 可能换变体**。**

**✅ 与 §355 的"号复用"配合（代际区分）。**

### 2.2 而**"绝不发一个缺失的别名"**

**✅ 与 §355 的"`setZmPresentation` 的 `>= 400 ⇒ 0`"**同族（**第十五次"不要发无效值"**）。**

## 三、**"用一个 XY 移动在当前脚高"**（本组第五重要）

```php
auto proposedOrigin = entity.currentOrigin;
proposedOrigin[0] += dx * scale;
proposedOrigin[1] += dy * scale;
// Node Z is an AI-node marker height, not the actor's foot height.  Driving
// the capsule toward it diagonally makes a 15-unit stair riser look like a
// vertical wall.  Move in XY at the current foot height; the traced step
// move below climbs ledges and the downward probe then places the feet on
// the actual collision surface.
```

### 3.1 六层

```text
1. **节点的 Z 是一个 AI 节点标记高度，不是 actor 的脚高**
2. ⇒ **斜向把胶囊朝它驱动让一个【15 单位的楼梯竖板】看起来像一堵垂直墙**
3. ⇒ **在【当前脚高】上只做 XY 移动**
4. ⇒ **下面的 traced 步进移动爬台阶**
5. ⇒ **而向下的探测然后把脚放在【实际碰撞面】上**
6. ⇒ **所以 Z 从不由目标驱动**
```

**✅ 与 §358 的"Z 是被独处的"、§357 的"不要传送 actor Z"**同族（**第六次"Z 归碰撞所有"**）。**

**⚠ 而"15 单位的竖板"⇒ **一个具体的楼梯尺寸**。**

**✅ 与 §359 五 的"18 单位步进"配合（18 > 15 ✓）。**

**⇒ **步进高度必须 ≥ 竖板高度**。**

**✅ **完整的闭合。**

## 四、**两个导航包围盒与"晋升"**（本组最重要的一段）

### 4.1 两个盒

```cpp
// THE SPAWNER -> FIRST PATHNODE LEG STARTS INSIDE THE SPAWN CLOSET.
//
// Factory's spawn closets and receiver windows overlap the ordinary
// standing capsule by design.  The compact probe is therefore retained
// only until the assigned window negotiation has finished.  Keeping its
// one-unit radius for the rest of the route was the wall-clipping bug:
// the actor's centre cleared a brush while its visible body and linked
// 15-unit capsule were already inside it.
constexpr TraceBounds CompactActorNavigationBounds{
    .midpoint = { 0.0f, 0.0f, 28.0f },
    .halfSize = { 1.0f, 1.0f, 20.0f },
};
constexpr TraceBounds FullActorNavigationBounds{
    .midpoint = { 0.0f, 0.0f, 35.0f },
    .halfSize = { 15.0f, 15.0f, 34.0f },
};
```

### 4.2 十层

```text
1. **生成器 → 第一个路径节点的那条腿【从生成壁橱内部开始】**
2. ⇒ **Factory 的生成壁橱与接收器窗口【按设计】与普通站立胶囊重叠**
3. ⇒ **所以紧凑探测只保留到【指定的窗口协商完成】**
4. ⇒ **在路由的其余部分保留它的【一单位半径】就是【墙壁裁剪 bug】**
5. ⇒ **actor 的【中心】清过了一个画笔模型**
6. ⇒ **而它可见的身体与链着的 15 单位胶囊【已经在里面】**
7. ⇒ **紧凑盒 2×2×40**（`halfSize = 1,1,20`，`midpoint z = 28`）
8. ⇒ **完整盒 30×30×68**（`halfSize = 15,15,34`，`midpoint z = 35`）
9. ⇒ **完整盒的水平尺寸匹配 `StandingPlayerTraceBounds`**
10. ⇒ **"留一单位在导航壳之下，这样接地的原点不会仅因触地就变成 `startSolid`"**
```

### 4.3 而**两个盒的几何**

```text
Compact   x,y ∈ [-1, 1]      2 × 2        （一单位半径）
          z   ∈ [8, 48]      40 高

Full      x,y ∈ [-15, 15]    30 × 30      （15 单位半径 = 站立玩家）
          z   ∈ [1, 69]      68 高
```

**⚠ 而紧凑盒的 z 从 **8** 开始（`28-20`）而完整盒从 **1**（`35-34`）。**

**⇒ 所以**完整盒离地只有 1 单位**（"留一单位"）。**

**✅ 与注释的"留一单位在导航壳之下"**完全一致 ✓**

### 4.4 而**"墙壁裁剪 bug"**

**✅ 与 §356 的"在第一个采样就停掉了"、§358 的"放进生成壁橱的墙里"**同族（**第三次"探测盒尺寸错误导致穿墙/卡住"**）。**

**⇒ 三层**：

```text
1. 一单位半径 ⇒ 中心能过 ⇒ 身体不能
2. ⇒ **所以"清过了"**
3. ⇒ **而视觉上身体在墙里**
```

**✅ **一个与 §350 的"接收了、存储了、从未被画"不同的失败**（这是**视觉错位**而不是**不可见**）。**

### 4.5 而**晋升的"实际静止世界测试"**

```cpp
// Promotion is based on an actual stationary world test, not a fixed
// distance past the window.  The authored mantle may land close enough
// to the sandbag volume that the full body still overlaps it. Continue
// with the compact probe only until the first genuinely clear position,
// then latch full bounds for the remainder of the actor's life.
const auto mayPromoteNavigationBounds =
    route.spawnBarrierResolved && (!route.spawnBarrier || route.spawnBarrierPassed);
if (!route.fullNavigationBounds && mayPromoteNavigationBounds) {
    const auto occupancyTrace = traceCapsule(entity.currentOrigin, entity.currentOrigin,
        FullActorNavigationBounds, ActorWorldContentMask, movementFilter);
    if (occupancyTrace && !occupancyTrace->allSolid && !occupancyTrace->startSolid) {
        route.fullNavigationBounds = true;
        OlMod::RuntimeLog::write(..., "ZMNAVBODY serverTime=... entity=... radius=15");
    }
}
const auto &actorNavigationBounds = route.fullNavigationBounds
    ? FullActorNavigationBounds : CompactActorNavigationBounds;
```

**⇒ 九层**：

```text
1. **晋升基于一个【实际静止世界测试】，不是一个窗口后的固定距离**
2. ⇒ **作者化的翻越可能落得离沙袋体足够近而完整身体仍与它重叠**
3. ⇒ **继续用紧凑探测直到【第一个真正清晰的位置】**
4. ⇒ **然后为 actor 一生的其余部分【锁存】完整盒**
5. ⇒ **两个前置**：屏障已解析 且（无屏障 或 已过）
6. ⇒ **零长度胶囊（`start == end`）测占用**
7. ⇒ **`!allSolid && !startSolid` ⇒ 晋升**
8. ⇒ **日志 `ZMNAVBODY ... radius=15`**
9. ⇒ **之后 `actorNavigationBounds` 是完整盒**
```

**✅ 与 §347 的"两个极端都错"**不同** —— 这是**一个精确的晋升条件**。**

**⚠ 而"锁存"（latch）与 §357 的"不要锁存"**字面矛盾**。**

**⇒ 但语义不同：**

```text
§357  **动画**不要锁存（要每 1.6-3.3 秒重断言）
§359  **导航盒**要锁存（一旦清晰就永久用完整的）
```

**✅ **两个相反的正确选择**（因为一个是"应该变化"一个是"不应回退"）。**

**⇒ **一个极精细的区分。**

### 4.6 而**"零长度胶囊测占用"**

**⇒ 三层**：

```text
1. `traceCapsule(p, p, bounds, ...)` —— 起点 = 终点
2. ⇒ **所以它测的是【胶囊在原地的重叠】**
3. ⇒ **不是移动**
```

**✅ 一个**巧妙的复用**（同一个 trace 函数测两种东西）。**

## 五、**"爬升腿留在【测量的中心线】上"**（本组第二重要）

### 5.1 那段

```php
// Demo-measured climbing routes are narrow centrelines.  In particular,
// receiver node 753 climbs through 742/741/740 before reaching 851.
// Applying a lateral crowd lane on those legs pushed followers off the
// stair/ramp collision while their route cursor continued upward.  Keep
// elevation legs on the measured centreline; yielding still controls
// follower speed on flat approaches and the authored window queue owns
// spacing before traversal.
auto elevationLeg = false;
if (!pursuitLeg && route.previousNode && route.cursor < route.nodes.size()) {
    const auto &fromNode = zmNavGraph_.nodes[*route.previousNode];
    const auto &toNode = zmNavGraph_.nodes[route.nodes[route.cursor]];
    elevationLeg = std::abs(toNode[2] - fromNode[2]) > 8.0f;
}
```

### 5.2 九层

```text
1. **demo 测量的爬升路由是【窄中心线】**
2. ⇒ **特别是接收器节点 753 通过 `742/741/740` 爬到 851**
3. ⇒ **在那些腿上施加侧向人群车道把跟随者推离楼梯/斜坡的碰撞**
4. ⇒ **而它们的路由游标继续向上**
5. ⇒ **所以让爬升腿留在测量的中心线上**
6. ⇒ **让行仍控制平坦接近上的跟随者速度**
7. ⇒ **而作者化的窗口队列拥有穿越前的间距**
8. ⇒ **`elevationLeg = |Δz| > 8.0`**（**第四次 8 单位**）
```

**✅ 与 §354 的"`ordinaryRouteEdge` 的 `|Δz| <= 8`"**完全一致 ✓**

**⇒ **第五次确认 8 单位。**

### 5.3 而**节点链 `753 → 742 → 741 → 740 → 851`**

**⇒ 五层**：

```text
1. **一个具体的爬升路径**
2. ⇒ **753 → 742 → 741 → 740 → 851**
3. ⇒ **四段**
4. ⇒ **而 851 是顶部**
```

**⚠ 与 §357 的"在节点 851 下方 100+ 单位开始下一条边"**配合。**

**⇒ 所以**851 是一个已知的顶部节点。**

**✅ **两个注释互相印证。**

## 六、**两种让行机制**（本组第三重要）

### 6.1 让行一：**"追行让行而不合成侧向目的地"**

```php
// PURSUIT YIELDING WITHOUT A SYNTHETIC LATERAL DESTINATION. Factory's
// demos and authored graph provide the route, while the player origin
// owns the final bearing. The previous crowd workaround deflected that
// bearing left/right every time neighbours changed and visibly made
// zombies wander before reacquiring the player. A rear actor may slow
// behind a close leader, but both axes stay on the original bearing.
if (SV_ZmPursuitYieldApplies(pursuitLeg, route.spawnBarrierPassed,
        route.fullNavigationBounds, elevationLeg, distance))
{
    const auto forwardX = dx / distance, forwardY = dy / distance;
    const auto lateralX = -forwardY, lateralY = forwardX;
    auto crowdSpeedScale = 1.0f;
    for (const auto otherNum : livingActorNumbers) {
        if (otherNum >= entityNum) break;
        ...
        const auto ahead = otherX * forwardX + otherY * forwardY;
        const auto side = otherX * lateralX + otherY * lateralY;
        if (ahead > -4.0f && std::abs(side) < SvActorCrowdSeparationRadius) {
            crowdSpeedScale = std::min(crowdSpeedScale,
                std::clamp(separation / SvActorCrowdSeparationRadius, 0.30f, 1.0f));
        }
    }
    proposedOrigin[0] = entity.currentOrigin[0] + dx * scale * crowdSpeedScale;
    proposedOrigin[1] = entity.currentOrigin[1] + dy * scale * crowdSpeedScale;
}
```

### 6.2 十层

```text
1. **追行让行而【不】合成侧向目的地**
2. ⇒ **Factory 的 demo 与作者化图提供路由，而【玩家原点】拥有最终方位**
3. ⇒ **以前的人群变通【每次邻居变化时】左右偏转那个方位**
4. ⇒ **而可见地让僵尸游荡然后重新获取玩家**
5. ⇒ **一个后方的 actor 可以在一个近的领导者后面【减速】**
6. ⇒ **但两个轴都留在【原始方位】上**
7. ⇒ **只检查更早的（`otherNum >= entityNum` break）**
8. ⇒ **`ahead > -4.0`（在前方 4 单位内）且 `|side| < 分离半径`**
9. ⇒ **速度缩放 `[0.30, 1.0]`**（最小 30%）
10. ⇒ **只缩 `scale` 而不改方向**
```

**✅ 与 §358 的"绝不把跟随者推到分离的坐标"**同族（**第二次"绝不侧移"**）。**

**⚠ 而 §358 是**队列**（按住不动）而这里是**减速**（仍前进）。**

**✅ 两种不同的让行。**

### 6.3 让行二：**`Actor_TeamMoveBlocked` 式的图让行**

```php
// Actor_TeamMoveBlocked-style graph yielding.  Only the stable
// lower entity-number actor leads; followers in the same narrow
// forward corridor wait rather than stacking at a node.  This is
// intentionally longitudinal: graph centrelines continue to own
// stairs/corners, and no additional world trace is introduced.
if (SV_ZmGraphYieldApplies(pursuitLeg, route.spawnBarrierPassed,
        route.fullNavigationBounds, elevationLeg, distance))
{
    ...
    graphYieldScale = std::min(graphYieldScale, SV_ZmGraphYieldScale(ahead, side, separation));
    if (graphYieldScale <= 0.0f) break;
    proposedOrigin[0] = entity.currentOrigin[0] + dx * scale * graphYieldScale;
    ...
}
```

**⇒ 六层**：

```text
1. **`Actor_TeamMoveBlocked` 式的图让行**
2. ⇒ **只有稳定的低实体号 actor 领先**
3. ⇒ **同一个窄前向走廊里的跟随者【等待】而不是在一个节点上堆**
4. ⇒ **这是【有意纵向的】**
5. ⇒ **图中心线继续拥有楼梯/拐角**
6. ⇒ **而不引入额外的世界 trace**
```

**✅ 与 §358 的"只检查更早的"**第三次一致。**

**⇒ **三次都是单向（低编号领先）。**

**✅ **一个贯穿全文件的秩序原则。**

### 6.4 而**两种让行的选择条件**

```text
SV_ZmPursuitYieldApplies   （追行腿）⇒ 减速
SV_ZmGraphYieldApplies     （图腿）  ⇒ 等待
```

**⇒ 三层**：

```text
1. **追玩家时**（无图）⇒ 减速（因为目标就是玩家）
2. ⇒ **沿图走时** ⇒ 等待（因为必须沿中心线）
3. ⇒ **两者都要求** `spawnBarrierPassed` + `fullNavigationBounds` + `!elevationLeg`
```

**✅ 一个**清晰的二分**。**

## 七、**18 单位步进**（本组第六重要）

### 7.1 那段

```php
// PMOVE-STYLE STEP: a horizontal capsule sweep correctly hits the
// vertical face of a stair or low ledge.  Try up, forward, then let the
// ground probe below trace back down.  This preserves wall collision:
// the raised forward sweep still rejects a full-height wall and the
// upward sweep rejects a low ceiling.
if (fraction < 1.0f) {
    // Player movement and the retained engine research both use an
    // 18-unit standing step.  Forty-eight let zombies mount rails,
    // sandbags and machinery as though those were stair treads.
    constexpr float ActorStepHeight = 18.0f;
    constexpr float ActorMinimumStepProgress = 0.10f;
    constexpr float ActorStepProgressAdvantage = 0.05f;
    auto stepStart = entity.currentOrigin;  stepStart[2] += ActorStepHeight;
    auto stepEnd = entity.currentOrigin;
    stepEnd[0] = intendedMovementOrigin[0];
    stepEnd[1] = intendedMovementOrigin[1];
    stepEnd[2] += ActorStepHeight;
    const auto upTrace = traceCapsule(entity.currentOrigin, stepStart, ...);
    if (upTrace && !upTrace->allSolid && !upTrace->startSolid && upTrace->fraction >= 1.0f) {
        const auto forwardTrace = traceCapsule(stepStart, stepEnd, ...);
        if (forwardTrace && ...) {
            const auto stepFraction = clamp(forwardTrace->fraction, 0, 1);
            if (stepFraction >= ActorMinimumStepProgress &&
                stepFraction > fraction + ActorStepProgressAdvantage) {
                proposedOrigin = interpolate(stepStart, stepEnd, stepFraction);
                stepped = true;
                ...
            }
        }
    }
}
```

### 7.2 十二层

```text
1. **一个水平胶囊扫掠【正确地】命中一个楼梯或低台的【垂直面】**
2. ⇒ **试：向上、向前，然后让下面的地面探测回溯向下**
3. ⇒ **这保留了墙碰撞**：
     · **抬升的前向扫掠仍拒绝一堵全高的墙**
     · **向上的扫掠拒绝一个低的天花板**
4. ⇒ **玩家移动与保留的引擎研究都用【18 单位站立步进】**
5. ⇒ **`48` 让僵尸爬上栏杆、沙袋与机械【就像它们是楼梯踏板】**
6. ⇒ **`ActorStepHeight = 18`**
7. ⇒ **`ActorMinimumStepProgress = 0.10`**（至少 10% 前进）
8. ⇒ **`ActorStepProgressAdvantage = 0.05`**（必须比原路径好 5%）
9. ⇒ **三阶段：向上 trace ⇒ 向前 trace ⇒ 插值**
10. ⇒ **向上必须完全清晰（`fraction >= 1.0`）**
11. ⇒ **向前必须满足两个门槛**
12. ⇒ **`stepped = true` ⇒ 记录**
```

### 7.3 而 **"48 让僵尸爬上栏杆"**

**✅ 与 §355 的"`0.385` 错 4.8 倍"**同族（**一个数值错误造成可见的行为错**）。**

**⚠ 而 `48 / 18 = 2.67×`。**

**⇒ 与 §355 的 `4.8×` **不同倍数**。**

**✅ **两个独立的数值错误。**

### 7.4 而**两个步进门槛的算术**

```text
ActorMinimumStepProgress      0.10   ⇒ 至少走 10%
ActorStepProgressAdvantage    0.05   ⇒ 比原路径好 5%
```

**⇒ 三层**：

```text
1. 若原 `fraction = 0.02`（几乎撞墙）
2. ⇒ **步进必须 > 0.07 且 >= 0.10**
3. ⇒ **所以门槛是 `max(0.10, fraction + 0.05)`**（隐式）
```

**✅ 两个门槛**同时**生效（AND）。**

**⚠ 而若 `fraction = 0.60`（大部分通过）⇒ 步进需 > 0.65。**

**⇒ 所以**步进只在"原来走很少"时启用**。**

**✅ 合理（不必为一个已经通过很多的路径绕路）。**

## 八、**`1500ms` 的边黑名单**（本组第七重要）

### 8.1 那段

```php
// A DEMO-INFERRED EDGE IS ONLY A HYPOTHESIS UNTIL COLLISION AGREES.
// If an actor that has already entered the map spends 1500 ms trying
// the same graph leg into a near-vertical plane, that straight chord
// is not a corridor.  Remember the physical edge, discard this route,
// and let A* choose another neighbour on the next frame.  This is the
// live proof for Factory's false 235->925 and 241->824 links; wall
// tangent motion otherwise makes actors hug those walls forever.
constexpr std::uint32_t BlockedEdgeRejectMilliseconds = 1500u;
const auto persistentGraphBlock =
    route.spawnBarrierPassed && !pursuitLeg && route.previousNode &&
    route.cursor < route.nodes.size() && fraction < 0.35f &&
    !stepped && std::abs(movementTrace->normal[2]) < 0.25f;
```

### 8.2 十二层

```text
1. **一个 demo 推断的边只是一个【假设】直到碰撞同意**
2. ⇒ **如果一个已经进入地图的 actor 花 1500ms 试【同一条图腿】进入一个近垂直平面**
3. ⇒ **那条直弦不是一个走廊**
4. ⇒ **记住那条【物理边】，丢弃这条路由**
5. ⇒ **并让 A* 在下一帧选另一个邻居**
6. ⇒ **这是 Factory 的【假 235→925 与 241→824 链接】的活证明**
7. ⇒ **而墙壁切向运动否则让 actor 【永远贴着那些墙】**
8. ⇒ **`BlockedEdgeRejectMilliseconds = 1500`**
9. ⇒ **七项条件**：屏障已过 / 非追腿 / previousNode / 有游标 / **`fraction < 0.35`** / 未步进 / **`|normal[2]| < 0.25`**（近垂直）
```

### 8.3 而**两个具体的假边**

```text
235 -> 925
241 -> 824
```

**✅ 与 §357 的"三对相反楼层"**不同**（那是**作者化协商**而这是**假图边**）。**

**⇒ 两类不同的坏边：**

```text
§357  authoredNegotiation   xanim 已知但无 root-motion
§359  false graph edge      demo 推断但碰撞不同意
```

**✅ **两个"边不可走"的原因。**

### 8.4 而**"永远贴着那些墙"**

**✅ 与 §356 的"只能永远对着那堵墙滑动"**同族（**第二次"贴墙"**）。**

### 8.5 而**进步检测（`8 单位`）**

```cpp
if (!route.blockedCandidate || *route.blockedCandidate != edge) {
    route.blockedCandidate = edge;
    route.blockedCandidateSince = now;
    route.blockedCandidateDistance = distance;
} else {
    constexpr float BlockedEdgeProgressDistance = 8.0f;
    if (distance <= route.blockedCandidateDistance - BlockedEdgeProgressDistance) {
        route.blockedCandidateSince = now;
        route.blockedCandidateDistance = distance;
    } else if (now - route.blockedCandidateSince >= BlockedEdgeRejectMilliseconds) {
        // 黑名单
    }
}
```

**⇒ 七层**：

```text
1. **新边 ⇒ 记录起点时间与距离**
2. ⇒ **同边**
3. ⇒ **若距离减少了 8 单位 ⇒ 【重置】计时**（在进步）
4. ⇒ **否则若 1500ms 到 ⇒ 黑名单**
5. ⇒ **所以"1500ms 无 8 单位进步"才触发**
```

**✅ 与 §349 的"重复直到它生效然后停止"**同族（**第二次"进展检测"**）。

**⚠ 而 `8.0f` 与 §354/§357/§359 的 `8.0f` 垂直容差**同值不同义**。**

**⇒ **第五次 8.0f。**

### 8.6 而**"自边意味着最近节点选了一个 actor 物理上无法接入的节点"**

```php
// A* includes its start node. A self-edge here means nearest-node
// selected a node the actor cannot physically join (normally the
// other side of a wall), not that there is no blocked condition.
// Time it exactly like a normal inferred edge, but invalidate the
// cached start instead of blacklisting a graph edge.
if (edge.first != edge.second && ...) { /* 黑名单 */ }
```

**⇒ 五层**：

```text
1. **A* 包含它的起始节点**
2. ⇒ **一个自边意味着最近节点选了一个 actor 物理上无法接入的节点**
3. ⇒ **（通常是墙的另一侧）**
4. ⇒ **不是"没有阻塞条件"**
5. ⇒ **像正常推断边一样计时，但【失效缓存的起点】而不是黑名单一条图边**
```

**✅ 与 §356 的"`Path_NearestNodeNotCrossPlanes`"**完全同族（**第二次"墙另一侧的节点"**）。

**⇒ **一个精确的区分**（自边 vs 正常边）。**

## 九、`block` 报告的**十一个字段**

```cpp
routeReport += " block" + entityNum +
    ":node=" + (pursuitLeg ? "player" : node) +
    ":to=" + target.xyz +
    ":frac=" + fraction +
    ":ss=" + startSolid +
    ":as=" + allSolid +
    ":hit=" + hitType + "/" + hitId +
    ":contents=" + contents +
    ":normal=" + normal.xyz;
```

**⇒ 十一项。**

**✅ 与 §355 的"命名是哪一个"**第四次。

**⚠ 而只在 `reportRoutes` 时（每 5 帧）⇒ **成本可控。**

## 十、关键结论

1. **翻窗变体 = `(entityNum ^ generation) & 1`** ⇒ **v6 或 v7**，而两变体都缺 ⇒ **停住**（不发缺失别名）。
2. **"节点的 Z 是一个 AI 节点标记高度，不是脚高"`** —— 斜向驱动让**15 单位楼梯竖板看起来像垂直墙**。
3. **⭐⭐ "一个 actor 是一个胶囊，在玩家走的同一个世界里"（12.162/12.163）`**。
4. **⭐ 两个导航包围盒**：紧凑 `2×2×40`（`z ∈ [8,48]`）与完整 `30×30×68`（`z ∈ [1,69]`，留**一单位**在导航壳下）。
5. **"在路由其余部分保留一单位半径就是【墙壁裁剪 bug】：中心清过了画笔模型而身体已在里面"`** —— 第三次"探测盒尺寸错误"。
6. **⭐ 晋升基于实际静止世界测试**（零长度胶囊测占用），**不是窗口后的固定距离**。
7. **"然后为 actor 一生的其余部分【锁存】完整盒"`** —— 与 §357 的"不要锁存"**字面矛盾而语义互补**（一个应该变化、一个不应回退）。
8. **⭐ "爬升腿留在测量的中心线上"`** —— 节点 753 通过 `742/741/740` 爬到 **851**，而**侧向车道把跟随者推离楼梯碰撞**。
9. **`elevationLeg = |Δz| > 8.0`** —— **第五次确认 8 单位**。
10. **两种让行**：追行让行（**减速 `[0.30,1.0]`**）与图让行（**等待**），而**两者都"不合成侧向目的地"`**。
11. **"以前的人群变通每次邻居变化时左右偏转方位 ⇒ 僵尸游荡然后重新获取玩家"`** —— 与 §357/§358 的"左右"症状**第三次**。
12. **三种让行的统一原则**：只检查**更早的** actor（低编号领先）。
13. **⭐ 18 单位步进**：向上 → 向前 → 插值，而 **"48 让僵尸爬上栏杆、沙袋与机械就像它们是楼梯踏板"`**。
14. **两个步进门槛**（至少 10% 且比原路径好 5%）⇒ 只在"原来走很少"时启用。
15. **⭐ "一个 demo 推断的边只是一个假设直到碰撞同意"`** —— 1500ms 无 8 单位进步 ⇒ 黑名单。
16. **两个具体的假边**（`235→925`、`241→824`）与 §357 的**作者化协商**是**两类不同的坏边**。
17. **"墙壁切向运动否则让 actor 永远贴着那些墙"`** —— 第二次"贴墙"。
18. **自边的精确语义**（A* 包含起始节点 ⇒ 自边 = 最近节点选了一个物理上无法接入的节点）⇒ **失效缓存起点而不是黑名单边**。
19. **`block` 报告的十一个字段**（命名而不是计数，第四次）。

## 十一、未闭合点

- `SvActorCrowdSeparationRadius` / `SvActorCrowdSameFloorHeight` 的值。
- `SV_ZmGraphYieldScale` 的完整逻辑。
- `StandingPlayerTraceBounds` 的值（完整盒声称匹配它）。
- 为什么完整盒 z 从 1 而非 0。
- `hitType` / `hitId` 的语义。
- `sv_snapshot_mp.cpp` 15600 行之后未读取（27,016 行，进度 58%）。
