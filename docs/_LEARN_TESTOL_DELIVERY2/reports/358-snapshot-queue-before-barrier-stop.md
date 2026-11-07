# 358 · **"队列测试必须【先于】屏障停止"** —— `33,029` 个有界对、`80..300` 的实测带、`320` 上限、五个入口对八个生成器

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 14800–15200 行。

## 二、**直追（direct pursuit）的"探测缓存而目标不缓存"**（本组最重要的一段）

### 2.1 那段

```php
// The sweep is deliberately cached, but the PURSUIT POINT is
// not.  All three Factory captures align moving actors most
// strongly with the player's current position and progressively
// worse with 100..1000-ms-old positions (33,029 bounded pairs).
// Retaining directPursuitTarget here made an otherwise clear
// actor visibly walk left/right toward the prior probe until the
// player moved eight units or its 200-ms clock expired.  Recompute
// the stand-off from the live player every frame; the movement
// capsule below remains authoritative if that small unprobed
// displacement has crossed into world geometry, and no extra
// traces or A* work are introduced.
target = SV_ZmPursuitStandOffTarget(entity.currentOrigin, *playerTarget, pursuitRadius);
directPursuit = true;
```

### 2.2 十二层

```text
1. **扫掠是被【有意缓存】的，而【追点】不是**
2. ⇒ **三个 Factory 捕获里移动的 actor 与玩家的【当前位置】对齐最强**
3. ⇒ **而与 100..1000ms 之前的位置【逐渐更差】**（`33,029` 个有界对）
4. ⇒ **在这里保留 `directPursuitTarget` 让一个否则清晰 actor【可见地左右走】向先前探测点**
5. ⇒ **直到玩家移动 8 单位或它的 200ms 时钟过期**
6. ⇒ **每帧从活玩家重算 stand-off**
7. ⇒ **下面的移动胶囊仍是权威**（若那一小段未探测的位移已进入世界几何）
8. ⇒ **而不引入额外的 trace 或 A* 工作**
```

### 2.3 ⭐ **"扫掠缓存而目标不缓存"**

**✅ 一个**极精细的缓存分层**。**

**⇒ 三层**：

```text
扫掠（`directPursuitClear`）  缓存：Trace 昂贵而结果稳定
追点（`directPursuitTarget`） 不缓存：玩家每帧动
```

**✅ 与 §347 的"缓存 vs 每帧重算"**同族。**

**⚠ 而**成本不对称**是关键（trace 昂贵 → 缓存；向量计算便宜 → 每帧）。**

**✅ 与 §345 的"代价不对称的正确选择"**同族（**第十一次**）。

### 2.4 而 **`33,029` 个有界对**

**✅ 与 §355 的 `259,968` 个断言、§351 的 `237` 个间隔方程**同族。**

**⇒ **第四次大规模统计**（`1,063` / `259,968` / `33,029` / `237`）。**

**⚠ 而"100..1000ms 之前的位置"⇒ **一个 900ms 的窗口**（10 个 100ms 桶）。**

**✅ `33,029 / 10 ≈ 3,303` 对每桶。**

### 2.5 而**"8 单位或 200ms"**

```text
8 单位      ⇒ `SV_ZmPursuitProbeDue` 的位移阈值
200ms       ⇒ 时间阈值
```

**⚠ 而 `LookaheadRefreshMilliseconds = 100`（§358 四）。**

**⇒ 两个不同的刷新周期**（探测 200 / 预看 100）。**

## 三、**`80..300` 的实测带与 `320` 上限**（本组第二重要）

### 3.1 那段

```php
// The exact Factory demos retain strongest heading alignment
// with the current player through the measured 80..300-unit
// band. The generic 192-unit bound forced otherwise clear actors
// back onto coarse graph bends until they were close, which read
// as a delayed left/right target update. Keep graph shortcuts
// conservative, but validate the live-player corridor across the
// complete measured band.
constexpr float DirectPursuitMaximumLength = 320.0f;
```

### 3.2 八层

```text
1. **确切的 Factory demo 通过测量的 `80..300` 单位带保留最强的朝向对齐**
2. ⇒ **泛型的 192 单位界把否则清晰的 actor 强制回到粗图弯道上**
3. ⇒ **直到它们接近**
4. ⇒ **那读起来像一个【延迟的左右目标更新】**
5. ⇒ **保持图捷径保守**
6. ⇒ **但在【完整的测量带】上验证活玩家走廊**
7. ⇒ **所以上限是 `320`**（> 300，留余量）
```

### 3.3 而 **`192` → `320`**

**⇒ 三层**：

```text
192   泛型值（可能是 6 个快照 × 32？）
320   测量带上界 300 + 20 余量
```

**⚠ 而 `192` 与 `24` 的 8 倍、`96` 的 2 倍**无直接关系。**

**⇒ 可能来自**别的推导**。**

**✅ 而 320 明确来自 300。**

### 3.4 而**"读起来像一个延迟的左右目标更新"**

**✅ 与 §357 的"可见的左右游荡"**完全同族（**第二次同样的症状**）。**

**⇒ 而**两种不同的原因**：

```text
§357  协商边无 root-motion ⇒ 推墙 ⇒ 左右游荡
§358  界限太窄 ⇒ 回到图弯道 ⇒ 延迟的左右更新
```

**✅ **两个不同的 bug 一个症状**。 —— 一个**极有价值的记录**。

## 四、**预看（area lookahead）的五条件 + 100ms**（本组第三重要）

### 4.1 那段

```php
// CODREF(actor_path_lookahead): BO1 Path_CalcLookahead 0x90A120
// and Ghosts 0x1400FF410 select by accumulated bend area. BO1
// 0x90A670 grows/reduces that budget after prediction; 0x908820 owns
// progress against the previous lookahead plane. The fixed 60-unit
// substitute pulled every actor back toward the same short segments.
// OLMOD(bounded-lookahead-adapter): retain the existing 100-ms trace
// cadence, full CODOL capsule, floor/negotiation boundaries and final
// grounded step owner. This is not the original CODOL AI controller.
if (!pursuitLeg && route.spawnBarrierPassed && route.fullNavigationBounds &&
    !barrierHolds && !approachNegotiation && !route.negotiationActive &&
    route.cursor+1u < route.nodes.size())
{
    constexpr std::uint32_t LookaheadRefreshMilliseconds = 100u;
    const auto refresh = routeReplannedThisFrame || route.lookaheadCheckedAt == 0u ||
        route.lookaheadCursor != route.cursor || now - route.lookaheadCheckedAt >= LookaheadRefreshMilliseconds;
```

### 4.2 十层

```text
1. **`BO1 Path_CalcLookahead 0x90A120` 与 `Ghosts 0x1400FF410` 按【累积弯曲面积】选**
2. ⇒ **`BO1 0x90A670` 在预测后增长/缩减那个预算**
3. ⇒ **`0x908820` 拥有对先前预看平面的进度**
4. ⇒ **固定的 60 单位替代把每个 actor 拉回同样的短片段**
5. ⇒ **保留既有的 100ms trace 节奏、完整 CODOL 胶囊、地板/协商边界与最终接地步所有者**
6. ⇒ **这不是原始 CODOL AI 控制器**（一个明确的免责）
7. ⇒ **七个条件**（非追腿 / 屏障已过 / 完整边界 / 无屏障保持 / 无接近协商 / 无活跃协商 / 有下一个）
8. ⇒ **四个刷新触发**：重规划 / 未检查过 / 游标变了 / 100ms 到
```

**✅ 与 §357 的"六个前置"**同族（**第三次多条件前置**）。

### 4.3 而 **"60 单位" vs "320 单位"**

**⇒ 三层**：

```text
60    旧的固定预看距离（"把每个 actor 拉回同样的短片段"）
320   直追的最大长度
```

**⚠ 所以**两个不同的"看得多远"**。**

**✅ 一个**复杂的三层导航**：图路由 / 预看 / 直追。**

### 4.4 而 **"累积弯曲面积"**

**✅ 与 §357 的"保存的转向平面"**同族。**

**⇒ 三层**：

```text
1. **按【累积的弯曲面积】决定预看多远**
2. ⇒ **弯多 ⇒ 预看更远**（提前切弯）
3. ⇒ **弯少 ⇒ 预看更近**
```

**✅ 一个**与几何自适应**的预看**（不是固定距离）。**

### 4.5 而 `route.lookaheadArea.observe(...)`

```cpp
route.lookaheadArea.observe(route.lookaheadClear, lookahead->consumedArea, lookahead->completed);
```

**⇒ 三层**：

```text
1. 一个**自适应预算**对象
2. ⇒ **喂入**：是否清晰 / 消耗的面积 / 是否完成
3. ⇒ **所以它自己调整**
```

**✅ 与 §357 的"`0x90A670` 在预测后增长/缩减预算"**完全一致 ✓**

**⇒ **一个有状态的自适应器。**

## 五、**"Z 是被独处的"**（本组第四重要）

### 5.1 那段

```php
// Z IS LEFT ALONE. There is no ground trace on this path, and dragging a
// zombie vertically toward a node on another floor would be worse than
// standing still -- factory's spawn point 4 sits 48 units below its own
// node (12.55b).
const auto dx = targetDx;
const auto dy = targetDy;
const auto distance = targetDistance;
```

### 5.2 六层

```text
1. **Z 被独处**
2. ⇒ **这条路径上【没有地面 trace】**
3. ⇒ **而把一个僵尸垂直拖向另一个楼层的节点会比站着不动更糟**
4. ⇒ **factory 的生成点 4 坐在它自己节点【下方 48 单位】**（12.55b）
5. ⇒ 所以 `dx` / `dy` / `distance` 全用**平面**值
6. ⇒ **Z 完全不动**
```

**✅ 与 §357 的"不要传送 actor Z"、§355 的"不数 Z"、§354 的"只动 X"**同族（**第五次"Z 归碰撞所有"**）。**

**⚠ 而"48 单位"⇒ **一个具体的误差量**。**

**✅ 一个**极具体的例子**。**

## 六、**队列的"只检查【更早的】actor"**（本组第五重要）

### 6.1 那段

```php
// THE MAP HAS FIVE ENTRANCES FOR FACTORY'S EIGHT ACTIVE SPAWNERS.
// Several actors consequently share one authored goal/window.  Retail's
// navigator supplies crowd avoidance; this measured graph is only a set
// of centrelines, so without this guard every follower occupies the
// leader's exact coordinate at the window and the whole wave appears to
// have spawned in one pile.
//
// Test the PROPOSED position against earlier actors assigned to the same
// spawner goal.  Entity number is the stable queue order.  Checking only
// earlier actors prevents two followers from mutually deadlocking, and
// restricting it to an identical authored goal avoids blocking actors on
// unrelated routes that merely cross nearby.
```

### 6.2 十二层

```text
1. **地图对 factory 的【八个】活跃生成器有【五个】入口**
2. ⇒ **于是几个 actor 共享一个作者化目标/窗口**
3. ⇒ **零售的导航器提供【人群避让】**
4. ⇒ **而这个测量的图只是一组【中心线】**
5. ⇒ **所以没有这个守卫，每一个跟随者占领导者的精确坐标**
6. ⇒ **而整波看起来生成在【一个堆里】**
7. ⇒ **用【提议的】位置去测更早的、被分配到同一生成器目标的 actor**
8. ⇒ **实体号是稳定的队列顺序**
9. ⇒ **只检查更早的 actor 防止两个跟随者【互相死锁】**
10. ⇒ **而限制到相同的作者化目标避免阻塞【仅仅在附近穿过】的无关路由上的 actor**
11. ⇒ 所以 `if (otherNum >= entityNum) break;`
```

### 6.3 **"八个生成器五个入口"**

**✅ 3 对 8 的**不足**（5 < 8）。**

**⇒ 所以**至少 3 个生成器共享入口**。**

**✅ 与 §356 的"四个映射"**不同**（那是 auto410-413，加 auto414 是五个）。**

**=【五个入口对五个 auto41x】** ✓**

**✅ **完全吻合。**

### 6.4 而**"只检查更早的防止互相死锁"**

**✅ 一个**经典的单向判据**。**

**⇒ 三层**：

```text
1. 若 A 检查 B 而 B 检查 A
2. ⇒ **两个都让**
3. ⇒ **死锁**
4. ⇒ **所以只检查编号更小的**
```

**✅ 与 §355 的"低编号先走"**完全一致 ✓**

**⇒ **第二次确认那个单向不变式。**

### 6.5 而**"从不要直接把跟随者推到分离的坐标"**

```php
// Hold until the leader clears the approach.  Never push the
// follower directly to a separated coordinate: that old
// correction skipped the world trace and could place an actor
// inside the spawn-closet wall, after which every trace quite
// correctly reported startSolid forever.
queueHolds = true;
break;
```

**⇒ 五层**：

```text
1. **按住直到领导者清空接近**
2. ⇒ **绝不把跟随者【直接推到】一个已分离的坐标**
3. ⇒ **那个旧修正【跳过】世界 trace**
4. ⇒ **并可能把一个 actor 放进【生成壁橱的墙】里**
5. ⇒ **之后每个 trace 都相当正确地【永远】报告 `startSolid`**
```

**✅ 与 §356 的"在第一个采样就停掉了"**同族（**"跳过 trace ⇒ 永久卡住"**）。**

**⇒ **第二次"绕过 trace 会造出永久卡住的状态"。**

### 6.6 而**两个距离测试**

```cpp
const auto currentSeparationSquared = currentQx*currentQx + currentQy*currentQy;
if (currentSeparationSquared < queueSpacingSquared) { queueHolds = true; break; }
const auto proposedQx = proposedX - other->second.currentOrigin[0];
const auto proposedQy = proposedY - other->second.currentOrigin[1];
if (proposedQx*proposedQx + proposedQy*proposedQy < queueSpacingSquared) { queueHolds = true; break; }
```

**⇒ 三层**：

```text
① **当前太近 ⇒ 已经挤了 ⇒ 让**
② **提议位置太近 ⇒ 会造成挤压 ⇒ 让**
③ 两个都通过 ⇒ 可以走
```

**✅ 与 §355 的"间距测试"**同族。**

**⇒ 两次测试（当前 + 提议）是一个**完整的守卫**。**

## 七、**"队列测试必须先于屏障停止"**（本组最重要的一段）

### 7.1 那段

```php
// THE QUEUE TEST MUST PRECEDE THE BARRIER STOP.
//
// Once an actor enters the outside->inside barrier leg, barrierHolds is
// true.  Running this branch first let every follower advance inside the
// waypoint-arrival radius and then stop on the leader's exact outside
// coordinate; the spacing guard below was never reached.  Followers now
// remain on their approach while the one actor at the window tears.
if (barrierHolds && (!tearLane || targetDistance<=2.0f ||
    (activeBarrier && activeBarrier->controller.lanes()[*tearLane])))
```

### 7.2 九层

```text
1. **队列测试必须【先于】屏障停止**
2. ⇒ **一旦一个 actor 进入 outside→inside 屏障腿，`barrierHolds` 就是真的**
3. ⇒ **先跑这个分支让每一个跟随者推进到航点到达半径【之内】**
4. ⇒ **然后停在领导者的【精确 outside 坐标】上**
5. ⇒ **下面的间距守卫【从未被达到】**
6. ⇒ **跟随者现在留在它们的接近上**
7. ⇒ **而【一个】在窗口处的 actor 撕屏障**
```

### 7.3 **"下面的间距守卫从未被达到"**

**✅ 与 §346 的"七十五项合取"**同族（**第二个从未到达的代码**）。**

**⇒ 三层**：

```text
1. `continue` 在间距守卫【之前】
2. ⇒ **所以守卫是死代码**
3. ⇒ **而症状（堆）仍然出现**
```

**✅ **一个"防线存在但永不执行"的实例。**

### 7.4 而 `barrierHolds` 分支的三个条件

```text
① !tearLane               没有撕车道
② targetDistance <= 2.0   已到窗口（2 单位）
③ controller.lanes()[tearLane] 已有租约（正在撕）
```

**⇒ 三个 ⇒ 任一为真就停。**

**✅ 与 §356 的"2.0 单位"**

**⚠ 而 §356 用的是 `distance <= 2.0f`（同）。**

**✅ **第二次确认 2.0 单位的"到窗口"阈值。**

## 八、**撕屏障的完整序列**（本组第六重要）

### 8.1 那段

```php
if (activeBarrier && tearLane && actorLifetime) {
    auto lease = activeBarrier->controller.lanes()[*tearLane];
    const auto &outside = zmNavGraph_.nodes[activeBarrier->outsideNode];
    const auto &inside = zmNavGraph_.nodes[activeBarrier->insideNode];
    const auto facing = std::atan2(inside[1]-outside[1], inside[0]-outside[0]) * (180.0f/PI);
    if (!lease) {
        entity.currentAngles[1] = SV_ZmTurnBody(entity.currentAngles[1], facing, frameMilliseconds);
        entity.networkState.angles = entity.currentAngles;
        // Reaching the stance is not permission to teleport yaw
        // and start the tear on that same frame.
        if (!SV_ZmFacingReady(entity.currentAngles[1], facing)) continue;
    }
    if (!lease)
        for (std::uint8_t slot = 0; slot < 6; ++slot) {
            if (!activeBarrier->boards[slot].profile) continue;
            lease = activeBarrier->controller.acquire(actorHandle, *tearLane, slot, zmTearClips_[*tearLane][slot], now);
            if (lease) { /* log ZMBARRIER tear ... */ break; }
        }
    if (lease) {
        entity.networkState.actorAnimIndex = lease->clip.animation;
        entity.networkState.actorAnimStartTime = lease->started;
        entity.currentAngles[1] = facing;
        entity.networkState.angles = entity.currentAngles;
    }
}
```

### 8.2 九层

```text
1. **朝向 = `atan2(inside - outside)`**（从外朝内）
2. ⇒ **平滑转身 `SV_ZmTurnBody`**
3. ⇒ **"到达站姿不是在同一帧传送 yaw 并开始撕的许可"**
4. ⇒ **`SV_ZmFacingReady` 未就绪 ⇒ `continue`**（下一帧再转）
5. ⇒ **然后遍历六块板找第一个有 profile 的**
6. ⇒ **`controller.acquire(handle, lane, slot, clip, now)`**
7. ⇒ **成功 ⇒ 日志 `ZMBARRIER tear` 并 break**
8. ⇒ **租约 ⇒ 设动画与 `animStartTime = lease->started`**（**相位保持**）
9. ⇒ **而 yaw 精确设到 `facing`**
```

**✅ 与 §356 的"`SV_ZmSettleWindowHeight` 的迭代收敛"**同族（**第二次"渐进 + 最终精确"**）。**

**⚠ 而**"到达站姿不是许可"**是一个**精确的时序约束**。**

**✅ 与 §347 的"THE TIME FIRST"**同族（**第三次时序约束**）。**

### 8.3 而**六块板的遍历**

```text
slot 0..5   ⇒ 六块板
跳过无 profile 的
取第一个可 acquire 的
```

**✅ 与 §354 的"`state.boards` 六个"**第四次确认。**

### 8.4 而**`zmTearClips_[lane][slot]` 是二维的**

**⇒ 三层**：

```text
1. **三个车道 × 六个槽**
2. ⇒ **= 18 个片段**
3. ⇒ **每个（车道, 板）组合一个片段**
```

**✅ 与 §354 的"三车道"、§354 的"六块板"**完全闭合 ✓**

**⇒ **18 个 `zmTearClips_` 条目。**

### 8.5 而日志的**七个字段**

```text
serverTime / barrier / actor / lane / slot（+1 基）/ animation / boardMs / endMs
```

**⇒ 八个。**

**✅ 与 §347 的"仪器命名缺陷"**第六次。

## 九、**"打开的窗口是一个【有时间限的协商】，不是一个碰撞绕过"**（本组第七重要）

### 9.1 那段

```php
// THE OPEN WINDOW IS A TIMED NEGOTIATION, NOT A COLLISION BYPASS.
//
// The old implementation disabled both movement collision and the
// ground probe for this entire graph edge.  That made an actor slide
// through the wall in whichever pose happened to be latched, and the
// full standing capsule could also settle on the sandbags at z=26.
// OLMOD(window-root-motion): pair the selected resident clip with its
// original asset-local track, clock and authored start-node facing.
// Both v6/v7 are observed at these windows. Selection below is a stable
// reconstructed choice, not a recovered native probability/gait rule.
```

### 9.2 十层

```text
1. **打开的窗口是一个【有时间限的协商】，不是一个碰撞绕过**
2. ⇒ **旧实现为【整条图边】禁用了移动碰撞【与】地面探测**
3. ⇒ **那让一个 actor 以它碰巧锁存的【任何姿势】穿过墙滑动**
4. ⇒ **而完整的站立胶囊也可能【停在 z=26 的沙袋上】**
5. ⇒ **把选中的常驻片段与它的原始【资产本地轨、时钟与作者化起始节点朝向】配对**
6. ⇒ **v6 与 v7 都在这些窗口被观察到**
7. ⇒ **下面的选择是一个【稳定的重建选择】**
8. ⇒ **不是恢复的原生概率/步态规则**（一个明确的免责）
```

**✅ 与 §356 的"这一条边是一个作者化的协商"**同族（**第三次同一个洞察**）。

**⚠ 而"z=26 的沙袋"⇒ **一个具体的坐标**。**

**✅ 第五次具体坐标/距离。**

### 9.3 而**"以它碰巧锁存的任何姿势穿过墙滑动"**

**✅ 与 §357 的"播一个片段然后保持"**同族（**第二次"锁存的姿势"**）。

## 十、**落地探测的六项**（窗口的）

```php
auto floorStart = outside;
floorStart[0] += outwardX * 32.0f;
floorStart[1] += outwardY * 32.0f;
floorStart[2] += 64.0f;
auto floorEnd = floorStart;
floorEnd[2] -= 192.0f;
constexpr TraceBounds FootProbeBounds{ .midpoint={0,0,0.5f}, .halfSize={0.5f,0.5f,0.5f} };
auto groundedZ = entity.currentOrigin[2];
if (const auto floorTrace = traceCapsule(floorStart, floorEnd, FootProbeBounds, ...);
    floorTrace && !floorTrace->allSolid && !floorTrace->startSolid && floorTrace->fraction < 1.0f)
{ ... }
```

### 10.1 六层

```text
1. **从 outside 节点向外 32 单位**（`outwardX/Y`）
2. ⇒ **再上 64 单位**
3. ⇒ **向下 192 单位**（总扫 192）
4. ⇒ **脚部胶囊 1×1×1**
5. ⇒ **五个拒绝条件**（同 §358 八.5：无命中 / allSolid / startSolid / fraction ≥ 1）
6. ⇒ **注意 `fraction < 1.0f`（不是 `>=`）** ⇒ **要求打到东西**
```

### 10.2 而**为什么"从 outside 向外 32 单位"**

**⇒ 三层**：

```text
1. 窗口在外面，而玩家站在外面
2. ⇒ **所以站位点 = outside 外 32 单位**
3. ⇒ **而地面在下方 192 内**
```

**✅ 与 §357 的"32 单位 incoming 走廊"**同值**。**

**⚠ 可能**不同语义同样的数**。**

### 10.3 而**`-192` 的扫程**

**⇒ 三层**：

```text
1. 从 `z + 64` 向下扫 192
2. ⇒ **所以覆盖 `z ∈ [z-128, z+64]`**
3. ⇒ **一个 192 单位的垂直搜索**
```

**✅ 与 §356 的"`z+18` 到 `z-24`"（42 单位）**不同**。**

**⇒ **两个不同的落地探测半径**（42 vs 192）。**

**⚠ 因为窗口可能在楼上/楼下（大范围）而落地是局部（小范围）。**

**✅ 合理。**

## 十一、关键结论

1. **⭐ "扫掠缓存而【追点】不缓存"`** —— `33,029` 个有界对证明移动 actor 与**玩家当前位置**对齐最强，与 100..1000ms 前的位置**逐渐更差**。
2. **"保留追点让 actor 可见地左右走向先前探测点，直到玩家移动 8 单位或 200ms 过期"`**。
3. **"下面的移动胶囊仍是权威"`** —— 缓存失效时的兜底。
4. **`80..300` 的实测带，而泛型的 `192` 界"把清晰的 actor 强制回到粗图弯道 ⇒ 延迟的左右更新"`** —— 与 §357 的"推墙游荡"**同一个症状两个原因**。
5. **预看的七条件 + 四个刷新触发（100ms）`**。
6. **`BO1 Path_CalcLookahead 0x90A120` 按【累积弯曲面积】选预看距离**，而 **"固定的 60 单位替代把每个 actor 拉回同样的短片段"`**。
7. **`route.lookaheadArea` 是一个【有状态的自适应预算】`**（喂入：是否清晰 / 消耗面积 / 是否完成）。
8. **⭐ "Z 是被独处的"`** —— 这条路径上**没有地面 trace**，而**factory 的生成点 4 坐在它自己节点下方 48 单位**。
9. **⭐ "地图对 factory 的八个活跃生成器有五个入口"`** ⇒ 几个 actor 共享一个目标 ⇒ **零售有导航器人群避让而我们的图只是一组中心线**。
10. **"只检查【更早的】actor 防止两个跟随者互相死锁"`** —— 第二次确认单向队列不变式。
11. **⭐ "绝不把跟随者直接推到分离的坐标"`** —— 旧修正**跳过世界 trace** ⇒ **放进生成壁橱的墙里 ⇒ 每个 trace 永远 `startSolid`**。
12. **两次间距测试（当前 + 提议）`** —— 一个完整的守卫。
13. **⭐⭐ "队列测试必须【先于】屏障停止"`** —— 否则**间距守卫从未被达到**（第二个"存在但永不执行的防线"）。
14. **`barrierHolds` 分支的三个条件**（无车道 / 距离 ≤ 2.0 / 已有租约）。
15. **撕屏障的完整序列**：平滑转身 → `SV_ZmFacingReady` → **"到达站姿不是同一帧传送 yaw 并开始撕的许可"`** → 遍历六块板 → `acquire` → 相位保持。
16. **`zmTearClips_[lane][slot]` = 3 × 6 = 18 个片段`**。
17. **"打开的窗口是一个【有时间限的协商】不是碰撞绕过"`** —— 旧实现禁用碰撞与地面探测 ⇒ **以任何锁存的姿势穿墙滑动 + 胶囊停在 z=26 的沙袋上**。
18. **"v6 与 v7 都在这些窗口被观察到"`** —— 而选择是**稳定的重建选择，不是恢复的原生概率**。
19. **窗口落地探测的六项**：从 outside 向外 32 单位、上 64、下扫 192、脚部 1×1×1 胶囊。
20. **两个不同的落地探测半径**（窗口 192 / 落地 42），因为**窗口可能跨楼层**。

## 十二、未闭合点

- `SV_ZmPursuitProbeDue` 的 8 单位与 200ms 的确切实现。
- `SvActorFormationArrivalDistance` / `SvActorAttackRange` / `SvActorWindowQueueSpacing` 的值。
- `SV_ZmAreaLookaheadTargetForRoute` 的面积计算。
- `z=26 的沙袋` 的确切位置。
- `v6`/`v7` 两个窗口变体的区别。
- `sv_snapshot_mp.cpp` 15200 行之后未读取（27,016 行，进度 56%）。
