# 357 · **"重新断言，不要锁存"（12.96）** —— `slot 0 @33950=481 @37050=225` 的零售序列、航点的双阈值（到达 24 / 高度 8）、`28` 单位的撕屏障三车道

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 14400–14800 行。

## 二、**航点消费的双阈值**（本组第三重要）

```cpp
// Take the next waypoint as soon as this one is reached. More than one
// can fall in a single frame at 38 units of travel and 24 of arrival.
while (route.cursor < route.nodes.size()) {
    const auto &waypoint = zmNavGraph_.nodes[route.nodes[route.cursor]];
    const auto wx = waypoint[0] - entity.currentOrigin[0];
    const auto wy = ...; const auto wz = ...;
    const auto planarDistance = std::sqrt(wx*wx + wy*wy);
    ...
    if (!passedByLookahead &&
        (planarDistance > SvActorWaypointArrivalDistance ||
         // A node directly above the actor is still on the wrong floor.
         // Consuming it solely because X/Y are exact allowed the receiver
         // ramp route to skip its climb and start the next edge 100+ units
         // below node 851.  The zero-distance guard below safely stops this
         // frame; collision/edge recovery owns the invalid leg rather than
         // silently teleporting route state to another storey.
         std::abs(wz) > SvActorWaypointArrivalHeight))
        break;
    route.previousNode = route.nodes[route.cursor];
    ++route.cursor;
}
```

### 2.1 八层

```text
1. **一到就取下一个航点**（`while` 循环）
2. ⇒ **在一帧里可以落多个**（38 单位行程 / 24 单位到达）
3. ⇒ **两个阈值**：
     · `planarDistance > SvActorWaypointArrivalDistance`（24）
     · **`|wz| > SvActorWaypointArrivalHeight`**（8）
4. ⇒ **X/Y 精确而在楼上 ⇒ 仍在错的楼层**
5. ⇒ **只因 X/Y 精确就消费它让接收器斜坡路由【跳过它的爬升】**
6. ⇒ **而在节点 851 下方 100+ 单位开始下一条边**
7. ⇒ **下面的零距离守卫安全地停住这一帧**
8. ⇒ **碰撞/边恢复拥有那条无效腿，而不是静默地把路由状态传送到另一层**
```

### 2.2 **"38 单位行程 / 24 单位到达"**

**⚠ 而 §355 说行走速度是 **79 单位/秒** ⇒ **每帧（50ms）3.95 单位**。**

**⇒ 所以"38 单位行程"是一帧的全部移动？**

**⚠ 那需要 **950 单位/秒** —— 与 79 不符。**

**⇒ 所以"38 单位"可能指**一条边的长度**（不是一帧）。**

**✅ 而注释说"在一帧里可以落多个"⇒ **所以要 `while`。**

**⇒ **一条边可能短于 4 单位 ⇒ 一帧落多个。**

**✅ 合理。**

### 2.3 而**三维距离的两个分量**

```text
planarDistance = sqrt(wx² + wy²)   ≤ 24
|wz|                                ≤ 8
```

**⇒ 所以航点必须在**水平 24 单位、垂直 8 单位**内。**

**✅ 与 §354 的 `ordinaryRouteEdge` 的 `|Δz| <= 8.0f`**完全一致 ✓**

**⇒ **第二次确认 8 单位的垂直容差。**

### 2.4 而**"100+ 单位下方"**

**✅ 与 §354 的"44 单位回退"、§356 的"151 单位"**同族。**

**⇒ **第四次具体距离**。**

## 三、**"重新断言，不要锁存"（12.96）**（本组最重要的一段）

### 3.1 那段

```php
// RE-ASSERT, DO NOT LATCH (12.96). This condition alone is what made the
// actors play one clip and then hold it: once actorAnimIndex equalled
// desiredAnim it never changed again, so animStartTime was stamped exactly
// once per actor per animation and the delta writer -- which only emits
// these fields when they CHANGE (writeClients, `state.animStartTime !=
// oldAnimStartTime`) -- never put a second assert on the wire.
//
// Retail does the opposite, measured off C-2021-7-31[15-32-16]zm in 12.50:
//   slot 0  @33950=481 @37050=225 @38850=230 @41650=283 @44950=0
//   slot 6  @35950=476 @38550=3   @41150=288 @42750=0
// i.e. a fresh assert every 1600-3300 ms, forever, returning to 0 between
// bursts. A constant index held for the life of the actor is not a state
// retail ever publishes.
const auto animExpired = SvActorReassertAnim &&
    (entity.networkState.actorAnimStartTime == 0u ||
     now - entity.networkState.actorAnimStartTime >= SvActorAnimReassertMilliseconds);
```

### 3.2 十二层

```text
1. **重新断言，不要锁存（12.96）**
2. ⇒ **这个条件【单独】就是让 actor 播一个片段然后【保持】它的原因**
3. ⇒ **一旦 `actorAnimIndex` 等于 `desiredAnim` 它就再也不变**
4. ⇒ **所以 `animStartTime` 每个 actor 每个动画只被打一次戳**
5. ⇒ **而 delta 写入器 —— 只在【它们变化时】才发这些字段**（`writeClients` 的 `state.animStartTime != oldAnimStartTime`）——**从不在线上放第二个断言**
6. ⇒ **零售做的是相反的事，在 12.50 里从 `C-2021-7-31[15-32-16]zm` 测量**：
     · **slot 0：`@33950=481 @37050=225 @38850=230 @41650=283 @44950=0`**
     · **slot 6：`@35950=476 @38550=3 @41150=288 @42750=0`**
7. ⇒ **即每 1600-3300ms 一个新断言，永远，在爆发之间返回 0**
8. ⇒ **一个恒定的索引被持有 actor 的一生不是零售曾发布的任何状态**
```

### 3.3 **"这个条件【单独】"**

**✅ 与 §356 的"这一条边是一个作者化的协商"**同族 —— **一个条件负载全部**。**

**⇒ 三层**：

```text
1. `actorAnimIndex != desiredAnim || animExpired`
2. ⇒ **去掉 `animExpired` ⇒ 只播一次**
3. ⇒ **所以"一个条件单独就是 bug 的全部"**
```

**✅ **第五次"一个条件负载全部"。**

### 3.4 而**两个 slot 的完整序列**

```text
slot 0   33950 → 481
         37050 → 225     (+3100ms)
         38850 → 230     (+1800ms)
         41650 → 283     (+2800ms)
         44950 → 0       (+3300ms)   ← 归零

slot 6   35950 → 476
         38550 → 3       (+2600ms)
         41150 → 288     (+2600ms)
         42750 → 0       (+1600ms)   ← 归零
```

**⇒ 八层**：

```text
1. **每个间隔 1600-3300ms**
2. ⇒ **最后归零**（"在爆发之间返回 0"）
3. ⇒ **所以 0 是一个"无动画"状态**
4. ⇒ **而一个"爆发"= 一个动作序列**（如走路 → 停下 → 再走）
```

**✅ 与 §344 的"`actorAnimIndex` 的默认是 0"**配合。**

**⚠ 而**归零**意味着**客户端不再播任何东西**。**

**⇒ 所以零售是**间歇的**。**

**✅ 一个**极具体的实测序列**（时间戳 + 动画索引）。**

### 3.5 而**"1600-3300ms"**

**⇒ 六个间隔：**

```text
3100, 1800, 2800, 3300, 2600, 2600, 1600
```

**⇒ 范围 `[1600, 3300]` ✓**

**✅ **七个数落在声明的范围内。**

### 3.6 而**`SvActorAnimReassertMilliseconds`**

**⇒ 三层**：

```text
1. 一个常量（未在此处给出）
2. ⇒ **`animStartTime == 0` 也算过期**（首次）
3. ⇒ **所以每 `SvActorAnimReassertMilliseconds` 重断言一次**
```

**⚠ 而零售是 **1600-3300ms** ⇒ 所以常量应在**这个范围内**。**

**✅ 与 §347 的"每个 actor 每秒一对命令"**可能冲突？**

```text
§347  每秒一对命令（`animStartTime` 与 animIndex）
§357  每 1.6-3.3 秒一次重断言
```

**⚠ 两处不同的频率。**

**⇒ 但**不同层**：`§347` 是**命令段**（`writeAnimationCommands`），而这里是**客户端状态**（`actorAnimIndex`）。**

**✅ **两个独立的通道。**

## 四、**"最后一个航点不是目标玩家"**（本组第二重要）

### 4.1 那段

```php
// THE LAST WAYPOINT IS NOT THE TARGET PLAYER. The factory graph is coarse:
// the live route report put several actors on node 848, about 38 units from
// the player, with start=dest and route=1. Retargeting the exhausted route
// at nodes.back() therefore made every zombie converge on and stop at one
// shared point. Retail demo tracks continue beyond their last graph waypoint;
// the final leg is to the actual living player's origin.
const auto playerTarget = monkeyTarget ? monkeyTarget : nearestPlayerOrigin(entity.currentOrigin);
if (finalLeg && !playerTarget) { entity.networkState.actorVelocity = {}; continue; }
auto target = finalLeg ? *playerTarget : zmNavGraph_.nodes[route.nodes[route.cursor]];
```

### 4.2 九层

```text
1. **最后一个航点不是目标玩家**
2. ⇒ **factory 的图是【粗】的**
3. ⇒ **活动路由报告把几个 actor 放在节点 848 上，距玩家约 38 单位**
4. ⇒ **`start == dest` 而 `route == 1`**
5. ⇒ **所以把耗尽的路由重定向到 `nodes.back()`**
6. ⇒ **让每一个僵尸收敛到【一个共享点】并停在那里**
7. ⇒ **零售 demo 轨【越过】它们最后一个图航点继续**
8. ⇒ **最后的腿是到【实际活着的玩家原点】**
```

### 4.3 而**"38 单位"**

**⚠ 而 §357 二的 `SvActorWaypointArrivalDistance = 24`。**

**⇒ 所以 38 > 24 ⇒ **节点 848 不会被消费**？**

**⚠ 但注释说"几个 actor 在节点 848 上"。**

**⇒ 所以它们**到了**（< 24）而**距玩家 38**。**

**✅ **两个不同的距离**（到节点 vs 到玩家）。**

### 4.4 而**"一个共享点"**

**✅ 与 §355 的"逐字节相同的堆"**同族（**第二次重叠**）。**

**⇒ 三层**：

```text
1. 所有 actor 走同一条图路由
2. ⇒ **图的终点是一个共享节点**
3. ⇒ **所以它们全停在那里**
```

**✅ 而解法是**最后一条腿走真玩家位置**。**

**⇒ 但玩家只有一个 ⇒ 所以它们仍会重叠。****

**⚠ 而 §355 的"排队规则"（低编号先走）是**重叠的解法**。**

**✅ 两层解法**（最后一腿走向玩家 + 排队防重叠）。

## 五、**"停规则只属于最后一条腿"**（本组第四重要）

### 5.1 那段

```php
// THE STOP RULE BELONGS TO THE LAST LEG ONLY, and getting that wrong
// freezes every actor: the waypoint radius is deliberately small and the
// stop radius is 96, so an actor that stopped short of an INTERMEDIATE waypoint would
// never reach it, never advance the cursor and stand there for good.
```

### 5.2 六层

```text
1. **停规则只属于【最后一条腿】**
2. ⇒ **搞错这个【冻结每一个 actor】**
3. ⇒ **航点半径是【故意小】的**
4. ⇒ **而停半径是【96】**
5. ⇒ **所以一个在【中间】航点前停下的 actor**
6. ⇒ **永远不会到达它、永不推进游标，并永远站在那里**
```

### 5.3 而 **`24` vs `96`**

```text
SvActorWaypointArrivalDistance   24   （到达）
停半径                            96   （停下来打人/待机）
```

**⚠ 所以 24 < 96 ⇒ **若用 96 判定到达，中间航点永不消费**。**

**✅ 一个**精确的数值陷阱**。**

**⚠ 而 96 与 §354 的 `RepairHeight = 96`**同值。**

**⇒ 可能**不同的语义同样的数**。**

## 六、**`ordinaryRouteEdge` 的五个条件**

```cpp
const auto ordinaryRouteEdge = [&](std::uint16_t a, std::uint16_t b) {
    return !zmNavGraph_.vaultAnimFor(a,b) &&
        !zmNavGraph_.negotiationMotion.contains({a,b}) &&
        !zmNavGraph_.negotiationMotion.contains({b,a}) &&
        !zmBarriers_.contains({std::min(a,b),std::max(a,b)}) &&
        std::abs(zmNavGraph_.nodes[a][2] - zmNavGraph_.nodes[b][2]) <= 8.0f;
};
```

### 6.1 五项

```text
① 不是翻越边（`vaultAnimFor`）
② 不是协商边（正向）
③ 不是协商边（反向）
④ 不是屏障边（**有序对**）
⑤ **|Δz| <= 8.0**
```

**✅ 与 §354 的"8 单位垂直容差"**第三次。**

**⚠ 而 ④ 用**有序对**而 ②③ 用**双向**。**

**⇒ 因为屏障的键已经是 `{min,max}`（§354 二.4）**。**

**✅ **一致的键约定。**

## 七、**"预看"（lookahead）的五个条件**

```cpp
const auto passedByLookahead = route.spawnBarrierPassed &&
    route.fullNavigationBounds &&
    incomingNode &&
    route.cursor+1u < route.nodes.size() &&
    ordinaryRouteEdge(*incomingNode, route.nodes[route.cursor]) &&
    ordinaryRouteEdge(route.nodes[route.cursor], route.nodes[route.cursor+1u]) &&
    (SV_ZmWaypointPassed(entity.currentOrigin, zmNavGraph_.nodes[*incomingNode], waypoint) ||
     // CODREF(actor_path_lookahead): BO1 0x908820 uses the
     // saved steering plane to trim a smoothed corner. The old
     // 32-unit incoming-edge corridor cannot consume a wider
     // accepted chord. Never reuse that chord after a replan.
     (!routeReplannedThisFrame && route.lookaheadClear &&
      route.cursor <= route.lookaheadLastNode &&
      SV_ZmPassedLookaheadPlane(entity.currentOrigin, waypoint, route.lookaheadDirection)));
```

### 7.1 八层

```text
1. **六个前置**：屏障已过 / 完整导航边界 / incoming 存在 / 有下一个 / 两条边都是普通边
2. ⇒ **然后两个可替代的判定**：
     · **`SV_ZmWaypointPassed`**（已越过）
     · **或预看平面**
3. ⇒ **`CODREF(actor_path_lookahead)`：BO1 `0x908820` 用保存的转向平面来裁剪一个平滑拐角**
4. ⇒ **旧的 32 单位 incoming 边走廊不能消费一条更宽的已接受弦**
5. ⇒ **在一次重规划之后【绝不】重用那条弦**（`!routeReplannedThisFrame`）
```

**✅ 与 §355 的"`OpenBLOPS Actor_Negotiation_Think`"**同族（**第四次引用外部实现**）。**

**⚠ 而"32 单位走廊"⇒ ****与 24 到达距离不同**。**

**✅ 三个不同的距离常数**（8 / 24 / 32 / 96）。

## 八、**`authoredNegotiation` 的"作者化协商边【不】就是移动解法"**（本组第五重要）

### 8.1 那段

```php
// AN AUTHORED NEGOTIATION EDGE IS NOT BY ITSELF A MOVEMENT SOLUTION.
//
// Factory contains several paired pathnodes on opposite floors (for
// example 945->958, 946->957 and 949->950).  Their xanim is known, but
// this server has no measured root-motion for those directed legs.
// Steering the ordinary ground capsule straight at the upper endpoint
// makes it push into the intervening wall for 1500 ms, wall-follow,
// reject the edge, and repeat.  With several actors this is both the
// visible left/right wandering and a periodic trace/replan spike.
//
// Reject such a leg before movement.  The assigned receiver-window
// crossing is deliberately excluded: that transition is owned by the
// barrier controller and windowTraverseActive, not negotiationMotion.
// Ordinary ramps and stairs remain routable because their successive
// node height is within the normal grounded-walk tolerance.
const auto authoredNegotiation = directedLeg &&
    std::ranges::find(zmNavGraph_.reverseNegotiationEdges,
        std::pair{directedLeg->second, directedLeg->first}) !=
            zmNavGraph_.reverseNegotiationEdges.end();
```

### 8.2 十一层

```text
1. **一个作者化的协商边【本身】不是一个移动解法**
2. ⇒ **Factory 包含几对在【对面楼层】的配对路径节点**（`945->958`、`946->957`、`949->950`）
3. ⇒ **它们的 xanim 已知**
4. ⇒ **但这个服务器对那些【有向腿】没有测量的 root-motion**
5. ⇒ **把普通地面胶囊直接朝上端点转向**
6. ⇒ **让它推进那道中间的墙【1500ms】**
7. ⇒ **沿墙走、拒绝那条边、并重复**
8. ⇒ **有多个 actor 时这既是【可见的左右游荡】也是一个周期性的 trace/重规划尖峰**
9. ⇒ **在移动之前拒绝这样的腿**
10. ⇒ **指定的接收器窗口穿越是【有意排除的】**：那个转换归屏障控制器与 `windowTraverseActive`，**不归 `negotiationMotion`**
11. ⇒ **普通的斜坡与楼梯仍可路由，因为它们的连续节点高度在正常的【接地行走】容差内**
```

### 8.3 而**"1500ms"**

**✅ 与 §356 的"44 单位"、§355 的"151 单位"**同族。**

**⇒ 一个**极具体的时长**（1.5 秒推墙）。**

### 8.4 而**三对相反楼层的节点**

```text
945 -> 958
946 -> 957
949 -> 950
```

**✅ 三对。**

**⚠ 而 §356 的"六块板" ⇒ **六个**。**

**⇒ 两个不同的"六"？**

**⚠ 而这里是**三对**（= 六条有向边）。**

**✅ 合理的解释（三对 = 六条有向）。**

### 8.5 而**"可见的左右游荡"**

**✅ 与 §355 的"脚会打滑"、§353 的"到一半停止挥击"、§356 的"原地走/绕圈/对墙滑动"**同族（**第七次具体症状**）。**

## 九、**撕屏障的三车道（`28` 单位间距）**（本组第六重要）

```php
if (barrierHolds && activeBarrier && tearLane) {
    target = zmNavGraph_.nodes[activeBarrier->outsideNode];
    const auto &inside = zmNavGraph_.nodes[activeBarrier->insideNode];
    auto ox = target[0]-inside[0], oy = target[1]-inside[1];
    const auto length = std::sqrt(ox*ox + oy*oy);
    if (length > 0.001f) {
        ox /= length; oy /= length;
        // Factory pf707/pf679/pf680/pf683 tear assertions: middle
        // six units outside the node, l/r spaced 28 units from it.
        // Ground remains collision-owned; do not teleport actor Z.
        const auto lateral = ((float)*tearLane - 1.0f) * 28.0f;
        target[0] += ox*6.0f - oy*lateral;
        target[1] += oy*6.0f + ox*lateral;
    }
    ...
}
```

### 9.1 七层

```text
1. **目标 = outside 节点**
2. ⇒ **方向 = outside → inside 的单位向量**
3. ⇒ **`lateral = (lane - 1) * 28`** ⇒ **车道 0/1/2 ⇒ -28 / 0 / +28**
4. ⇒ **目标 = outside + 法线方向外 6 单位 + 侧向 lateral**
5. ⇒ **`ox*6 - oy*lateral`（x）与 `oy*6 + ox*lateral`（y）** ⇒ **二维旋转**
6. ⇒ **"Ground remains collision-owned; do not teleport actor Z"`**
7. ⇒ **注释给出四个实测的屏障名**（`pf707/pf679/pf680/pf683`）
```

### 9.2 而**"六个单位在节点外，左右各 28 单位"**

**✅ 三层**：

```text
1. 中间车道在节点外 6 单位
2. ⇒ **左右车道各侧 28 单位**
3. ⇒ **三个 actor 并排撕屏障**
```

**✅ 与 §356 的"屏障拥有三个撕占用者"**完全一致 ✓**

**⇒ 而 §354 说 `occupants` 是 `array<..., 3>`。**

**✅ **三次确认"三车道"。**

### 9.3 而**四个实测屏障名**

```text
pf707   （auto410 的目标）
pf679   （auto412 的目标）
pf680   （auto411 的目标）
pf683   （auto413 与 auto414 的目标）
```

**✅ 与 §356 四.2 的四个映射**完全一致 ✓**

**⇒ **第二次确认那四个名。**

### 9.4 而**"不要传送 actor Z"**

**✅ 与 §344 的"`validActorEntity` 拒绝俯仰/翻滚"**同族（**不要伪造物理**）。**

**⇒ 三层**：

```text
1. 水平目标可以调（撕屏障的位置）
2. ⇒ **但 Z 归碰撞所有**
3. ⇒ **所以只调 X/Y**
```

**✅ 与 §355 的"`nearestPlayerDistance` 不数 Z"**同族（**第四次"只动两个轴"**）。

## 十、`SV_ZmUnsupportedGroundTransition` 的**五参数**

```cpp
if (directedLeg && SV_ZmUnsupportedGroundTransition(
        windowOwnsLeg,
        measuredMotion != zmNavGraph_.negotiationMotion.end(),
        authoredNegotiation,
        zmNavGraph_.nodes[directedLeg->first][2] - zmNavGraph_.nodes[directedLeg->second][2],
        SvActorWaypointArrivalHeight))
{
    // 加入 blockedEdges、清路由、清速度、记日志、continue
}
```

### 10.1 五参数

```text
① windowOwnsLeg            窗口拥有这条腿
② measuredMotion 存在       有测量的运动
③ authoredNegotiation      是作者化协商
④ Δz                       高度差
⑤ SvActorWaypointArrivalHeight   容差（8）
```

**✅ 而判定"不支持"⇒ 阻塞该边。**

**⇒ 所以**一个五参数谓词**集中了所有"这条腿不能走"的理由。**

**✅ 与 §346 的"七十五项合取"**不同**（这里**抽出成函数**）。**

**⇒ **一个更好的做法。**

## 十一、`windowOwnsLeg` 的**"从这条腿解析移动所有者，不是那个更早的标志"**

```php
// OLMOD(zm-grounded-transition): route advancement above can change
// the leg after assignedWindowEdge was computed for replanning.
// Resolve the movement owner from this leg, not that earlier flag.
const auto windowOwner = route.spawnBarrier ? zmBarriers_.find(*route.spawnBarrier) : zmBarriers_.end();
const auto windowOwnsLeg = directedLeg && windowOwner != zmBarriers_.end() &&
    SV_ZmWindowOwnsGroundTransition(directedLeg->first, directedLeg->second,
        windowOwner->second.outsideNode, windowOwner->second.insideNode,
        route.spawnBarrierPassed);
```

### 11.1 四层

```text
1. **上面路由推进会改变那条腿**
2. ⇒ **在 `assignedWindowEdge` 为【重规划】计算之后**
3. ⇒ **所以从【这条腿】解析移动所有者，而不是那个更早的标志**
4. ⇒ 用 `SV_ZmWindowOwnsGroundTransition`（带 `spawnBarrierPassed`）
```

**✅ 与 §356 的"这一条边是方向性的"**同族（**第五次"所有者"**）。**

**⚠ 而"更早的标志"是一个**真实的陈旧状态陷阱**。**

**⇒ 与 §355 的"从前 40 帧的日志得出的结论都作废"**同族（**陈旧状态**）。**

## 十二、关键结论

1. **航点消费的双阈值**：水平 `24` + **垂直 `8`**（第三次确认 8）。
2. **"X/Y 精确而在楼上 ⇒ 仍在错的楼层"`** —— 只按 X/Y 消费让接收器斜坡**跳过爬升**，在下一条边**100+ 单位下方**开始。
3. **⭐⭐ "重新断言，不要锁存"（12.96）`** —— 这个条件**单独**就是"播一个片段然后保持"的全部原因。
4. **delta 写入器只在变化时发** ⇒ 一次断言之后**永不再发**（一个"沉默"的结构性原因）。
5. **零售的两个 slot 实测序列**：`slot 0 @33950=481 @37050=225 @38850=230 @41650=283 @44950=0`，`slot 6 @35950=476 @38550=3 @41150=288 @42750=0`。
6. **"每 1600-3300ms 一个新断言，永远，在爆发之间【返回 0】"`** —— 而**"一个恒定索引持有 actor 一生不是零售曾发布的任何状态"`**。
7. **⭐ "最后一个航点不是目标玩家"`** —— factory 的图是粗的，几个 actor 全在**节点 848** 上（`start == dest`、`route == 1`）⇒ **收敛到一个共享点**。
8. **"零售 demo 轨越过它们最后一个图航点继续；最后的腿是到实际活着的玩家原点"`**。
9. **⭐ "停规则只属于最后一条腿"`** —— 航点半径 `24` **故意小**而停半径 `96`，所以**在中间航点前停下会永久冻结**。
10. **`ordinaryRouteEdge` 的五项**（翻越 / 协商双向 / 屏障 / `|Δz| <= 8`），而屏障用**有序对**（因为键已是 `{min,max}`）。
11. **预看的六个前置 + 两个替代判定**（越过 / 预看平面），而 **"一次重规划之后绝不复用那条弦"`**。
12. **⭐ "一个作者化的协商边本身不是一个移动解法"`** —— Factory 有**三对对面楼层**的节点（`945→958`、`946→957`、`949→950`），**xanim 已知而无测量的 root-motion**。
13. **"把地面胶囊直接朝上端点转向 ⇒ 推墙 1500ms、沿墙走、拒绝、重复 ⇒ 可见的左右游荡 + trace 尖峰"`** —— 第七次具体症状。
14. **"指定的接收器窗口穿越有意排除"`** —— 那个转换归屏障控制器与 `windowTraverseActive`。
15. **撕屏障的三车道**：车道 `0/1/2` ⇒ 侧向 `-28 / 0 / +28`，中间车道在节点外 **6** 单位（四次确认）。
16. **"Ground remains collision-owned; do not teleport actor Z"`** —— 第四次"只动两个轴"。
17. **四个实测屏障名**（`pf707/pf679/pf680/pf683`）与 §356 的映射完全一致。
18. **`SV_ZmUnsupportedGroundTransition` 的五参数谓词** —— 把"这条腿不能走"的全部理由抽成一个函数（比 §346 的七十五项合取好）。
19. **⭐ "从这条腿解析移动所有者，不是那个更早的标志"`** —— 一个**陈旧状态陷阱**（`assignedWindowEdge` 之后路由推进改变了腿）。
20. **三个不同的距离常数并存**：到达 `24`、垂直 `8`、incoming 走廊 `32`、停半径 `96`。

## 十三、未闭合点

- `SvActorAnimReassertMilliseconds` 的确切值。
- `SvActorPursuitStandOffRadius` 的值。
- `lookaheadDirection` / `lookaheadLastNode` 的构建。
- `SV_ZmShortcutCursor` 的完整逻辑。
- `SvActorWaypointArrivalDistance` 是否真的 24。
- `sv_snapshot_mp.cpp` 14800 行之后未读取（27,016 行，进度 55%）。
