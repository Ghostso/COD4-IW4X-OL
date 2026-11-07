# 478 · **"一个 DEMO VORONOI 过渡【不是一个可走边**"** —— `sv_zm_navgraph_mp.cpp` 的 `72` 单位地板容差、`833→651` 的实测失败、以及一条"三个演员撞同一个世界 brush"的边

## 一、范围

本报告学习 `sv_zm_navgraph_mp.cpp`（**`666` 行**）全文件：`SvZmNegotiationMotion::position` 的插值、三张手工采样表、`SV_BuildZmNavGraph` 的七段（节点序 / 位置校验 / 反向边 / 障碍 / 接地 / 边准入 / CSR）、两条 `A*`（带与不带启发式）、以及 `usableEdge` 的五条判据。

## 二、**"一个 DEMO VORONOI 过渡【不是一个可走边**"**（本组最重要的一段）

### 2.1 那段

```cpp
// A DEMO VORONOI TRANSITION IS NOT AUTOMATICALLY A WALKABLE EDGE.
//
// The frozen reconstruction assigned each demo sample to the nearest map
// node in X/Y.  Factory has several storeys above the same plan position,
// so that procedure admitted ordinary walk links between different floors.
// The live failure was node 833 (Z=24) -> node 651 (Z=120): a ground-level
// actor aimed at the upper walkway and the collision solver quite correctly
// made it hug the intervening wall forever.
//
// Preserve every map-declared negotiation.  Those are the authored vault,
// mantle and drop links whose vertical displacement is intentional.  Only
// a plain inferred Walk is rejected when it exceeds the same 72-unit floor
// tolerance used by nearest-node selection.
```

### 2.2 二十四层

```text
1. **一个 demo Voronoi 过渡【不是【自动【一个可走边**】
2. ⇒ **⇒ 那个冻结的重建【把【每个 demo 样本【分配到【X/Y 上最近的**地图节点**】
3. ⇒ **⇒ 而 Factory 【在【同一个平面位置【之上【有【几层**】
4. ⇒ **⇒ 所以【那个过程【放进了【不同楼层之间【的**普通走链接**】
5. ⇒ **⇒ 而那个活的失败【是【节点 `833`（`Z=24`）⇒ 节点 `651`（`Z=120`）**】
6. ⇒ **⇒ 一个【地面层的**演员【瞄准【上面的走道**】
7. ⇒ **⇒ 而【那个碰撞求解器【相当正确地【让它【永远【贴着【那道【中间的墙**】
8. ⇒ **⇒ 所以【保留【每一个【地图声明的**协商**
9. ⇒ **⇒ （那些【是被编写的 `vault`/`mantle`/`drop` 链接，它们的垂直位移【是有意的**）**
10. ⇒ **⇒ 只有【一个【普通推断的** `Walk` 【在【超过【那个【同一个 `72` 单位的**地板容差**时【被拒绝**】
```

### 2.3 ⭐⭐⭐ **"那个碰撞求解器相当正确地让它永远贴着那道中间的墙"**

**✅ 这是本报告里**最重要的一条"一个图缺陷【的**运行时**表现**"**。**

**✅ 与 §477 的"每枚投掷物都在第一帧被静默退役"**——**同族** ✓

**⇒ 三层**：
```text
图 ⇒ **一个【错的边**（`833 → 651`）**
求解器 ⇒ **完全正确**（**贴墙**）
⇒ **⇒ 所以【症状【是【一个"AI 卡住**"**】而【病因【是【一个**边的准入**】
```

**✅ ⭐⭐⭐ **"症状是一个『AI 卡住』，而病因是一个边的准入"** —— 一个**极精确的归因**。

**✅ 与 §471 的"打不死人 + 穿透仍无效是同一刀的两个症状"**——**同族**（**第二次"一个**症状【指向【一个**错误的子系统**"**）。

**⚠ 而 `833`（`Z=24`）与 `651`（`Z=120`）的差**⇒ **`96` 单位**。**

**⇒ 独立验证**：
```text
`120 - 24 = 96`
而【那个 `72` 单位的**容差**】⇒ **⇒ 所以【那条边【超过了【`24` 单位**】
⇒ **⇒ 而【它【会【被【新的 `usableEdge` **拒绝** ✓
```

**✅ ⭐⭐⭐ **"96 − 72 = 24 单位 ⇒ 那条边会被新的判据拒绝"** —— 一个**精确的算术闭合**。

**✅ 与 §467 的"`1100 + 106 - 1 = 1205`"**——**同族**（**第二次"一个**具体的数【验证【一个判据**"**）。

### 2.4 而 `usableEdge` 的五条

```cpp
const auto usableEdge = [&graph, &grounded, mapName, &resolveGround](const SvZmNavEdge &edge) {
    const auto factoryCentreFalseEdge = resolveGround &&
        mapName == "zm_factory_sh" &&
        std::min(edge.a, edge.b) == 617u &&
        std::max(edge.a, edge.b) == 840u;
    return grounded[edge.a] && grounded[edge.b] &&
        !factoryCentreFalseEdge &&
        (edge.via != SvZmNavVia::Walk ||
            std::abs(graph.nodes[edge.a][2] - graph.nodes[edge.b][2]) <= SvZmNavHeightTolerance);
};
```

**⇒ 十六层**：
```text
1. **`grounded[a] && grounded[b]`**（**两端的接地**）**
2. ⇒ **`!factoryCentreFalseEdge`**（**一个【具体的**黑名单边**）
3. ⇒ **⇒ 而【`via != Walk` ⇒ 【接受**】（**协商边**无条件**通过垂直判据**）
4. ⇒ **⇒ 而【`via == Walk` ⇒ 【要求【`|Δz| <= 72`**】
```

### 2.5 ⭐⭐⭐ **"协商边无条件通过垂直判据，因为它们的垂直位移是有意的"**

**✅ 与 §467 的 `Skipped` 的五个 classname**——**同族**（**第三次"一个**白名单【绕过【一个**通用规则**"**）。

**⇒ 三层**：
```text
通用规则 ⇒ **`|Δz| <= 72`**
例外 ⇒ **`via != Walk` ⇒ 跳过【那个规则**】
⇒ **⇒ 所以【那个规则【只【约束**推断的边**】
```

**✅ ⭐⭐⭐ **"那个规则只约束推断的边"** —— 一个**极清晰的划分**。

**✅ 与 §467 的"`Skipped` 是五个 classname 而不是一个规则"**——**一个精细的对照**（那里**显式五个**，这里**一个类的划分**）**。**

## 三、**`617 → 840` 的那条边：三个演员撞同一个世界 brush**（本组第二重要）

### 3.1 那段

```cpp
// The absolute-demo Voronoi reconstruction still inferred one straight
// chord through Factory's centre machinery. Three independent live
// actors (704/707/708) hit the same world brush on 617->840 at
// (-3.375,-14.860,29.886), fraction 0.032061, normalZ 0. This is a
// shared graph defect, not actor-local congestion: reject it once while
// constructing the graph instead of making every zombie wall-follow for
// 1500 ms and rediscover the identical obstruction.
```

### 3.2 二十四层

```text
1. **那个绝对 demo 的 Voronoi 重建【仍然【推断出【一条【直的**弦】】
2. ⇒ **⇒ 穿过【Factory 的【中央机械**】
3. ⇒ **⇒ 而【三个独立的活演员（`704`/`707`/`708`）【在 `617 → 840` 上【撞【同一个世界 brush**】
4. ⇒ **⇒ 在 `(-3.375, -14.860, 29.886)`，`fraction 0.032061`，`normalZ 0`**
5. ⇒ **⇒ 这是【一个**共享的图缺陷**，不是【演员局部的**拥堵**】
6. ⇒ **⇒ 所以【在【构造图**时【拒绝它一次**】
7. ⇒ **⇒ 而不是【让【每一个僵尸【贴墙 `1500ms` 【并【重新发现【那个同一的**障碍**】
```

### 3.3 ⭐⭐⭐ **"在构造图时拒绝它一次，而不是让每一个僵尸贴墙 1500ms 并重新发现那个同一的障碍"**

**✅ 这是本报告里**最精确的一条"**一次 vs 每一帧**"**。**

**✅ 与 §475 的"发送它的轨迹，而不是每一帧把一个模型往上步进"**——**完全同族** ✓

**⇒ 三层**：
```text
§475  **发送轨迹 ⇒ 客户端【自己**插值**】
§478  **在图里拒绝那条边 ⇒ 每个僵尸【不必【重新发现**】
⇒ **⇒ 两次"把【一个**重复的计算【上移【一次**"**
```

**✅ ⭐⭐⭐ **"把一个重复的计算上移一次"两例**。

**⚠ 而 `fraction 0.032061`**⇒ **一个**极小的**值**。**

**⇒ 十层**：
```text
`fraction = 0.032061` ⇒ **⇒ 所以【那个碰撞【在【那条弦的【`3.2%** 处】
⇒ **⇒ 而【那【意味着【那个 brush 【就在【起点【的【很近**处】
⇒ **⇒ 所以【那是【一个【立即**的阻挡**（**不是【中途**的**）
```

**✅ ⭐⭐⭐ **"那是一个立即的阻挡（不是中途的）"** —— 一个**极精确的读法**。

**✅ 与 §471 的"`0.135 / 0.125 = 1.08` 单位"**——**同族**（**第三次"一个**几何的量【验证【一个结论**"**）。

**⚠ 而 `normalZ 0`**⇒ **一个**垂直的**墙**。**

**⇒ 三层**：
```text
`normalZ == 0` ⇒ **那个法线【没有【`z` 分量**】⇒ **⇒ 所以【那是一面【垂直的墙**】
⇒ **⇒ 而【那【证实【那个"中央机械【是一堵墙**"**的读法**】
```

**✅ ⭐⭐ **"那证实『中央机械是一堵墙』的读法"**。

### 3.4 而那个黑名单的**硬编码**

**⇒ 十层**：
```cpp
const auto factoryCentreFalseEdge = resolveGround && mapName == "zm_factory_sh" &&
    std::min(edge.a, edge.b) == 617u && std::max(edge.a, edge.b) == 840u;
```
```text
1. **一个【单条边**的【硬编码**黑名单**】
2. ⇒ **⇒ 而【它【绑定在【`resolveGround` 与【地图名**上**】
3. ⇒ **⇒ 所以【它【只【在【`zm_factory_sh` 的接地表**上【生效**】
```

**⚠ 一个**可报告的**观察：这是一条**特例**，而**注释【解释了【为什么**（**三个独立演员、同一坐标**）**。**

**⇒ 三层**：
```text
若【没有那个注释**】⇒ **⇒ 一个**魔法**的边对**】⇒ **⇒ 不可维护**
有那个注释**】⇒ **⇒ 一个**测量的**黑名单**】⇒ **⇒ 可维护**
⇒ **⇒ 所以【关键【是【那个测量**】
```

**✅ ⭐⭐⭐ **"关键是那个测量"** —— 与 §468 的"没有见证的值故意缺席"**同族**（**第四次"一个**魔法数【必须有【一个**测量的出处**"**）。

## 四、**`SvZmNegotiationMotion::position` 的插值**（本组第三重要）

### 4.1 那段

```cpp
std::array<float, 3> SvZmNegotiationMotion::position(const std::uint32_t elapsed) const
{
    if (samples.empty()) return {};
    if (elapsed >= duration()) return samples.back();
    const auto first = elapsed < firstInterval;
    const auto index = first ? 0u : 1u + (elapsed - firstInterval) / 100u;
    const auto fraction = first ? static_cast<float>(elapsed) / firstInterval
        : static_cast<float>((elapsed - firstInterval) % 100u) / 100.0f;
    auto result = samples[index];
    for (std::size_t axis = 0; axis < 3; ++axis)
        result[axis] += (samples[index + 1u][axis] - result[axis]) * fraction;
    return result;
}
```

### 4.2 二十四层

```text
1. **第一段【是【一个【可变长度**的区间**】（`firstInterval`，`50` 或 `100`）**
2. ⇒ **⇒ 而【之后【每 `100ms` 一段**】
3. ⇒ **⇒ 而【那个 `first` 分支【用一个【不同的**除数**】
4. ⇒ **⇒ 所以【那个 `firstInterval` 【是【一个**真实的**第一段**（**注释：`50ms`**）**
```

### 4.3 ⭐⭐⭐ **"保留那个 50ms 的第一段，而不是移动动画时钟"**

**✅ 与 §475 的"`2000 + 100 + 899 = 2999` 而有 1ms 的空隙"**——**同族**（**第三次"一个**时间窗口【的**精确**"**）**。

**⇒ 独立验证**：
```text
`firstInterval = 50` ⇒ **第一段 `0..50ms`**
之后 ⇒ **`50..150` / `150..250` / …**
⇒ **⇒ 而 `index = 1 + (elapsed - 50) / 100`**
  `elapsed = 50` ⇒ `1 + 0 = 1` ✓
  `elapsed = 149` ⇒ `1 + 0 = 1`，`fraction = 99/100` ✓
  `elapsed = 150` ⇒ `1 + 1 = 2`，`fraction = 0` ✓
⇒ **⇒ 所以【那个公式【正确**】**
```

**✅ ⭐⭐⭐ **"那个公式正确"** —— 一个**精确的分段线性插值**。

**⚠ 而那个 `samples` 的**尾部重复**（`{93,253,-2}` ×4）**⇒ **一个**静止**的终态**。**

**⇒ 十层**：
```text
`FactoryDrop977976` 的最后四个【是 `{93,253,-2}`**】
⇒ **⇒ 所以【那个运动【在【到达【后**】⇒ **⇒ 停留【在同一**点**】
⇒ **⇒ 而 `if (elapsed >= duration()) return samples.back();` ⇒ **一个**显式的**短路**】
```

**✅ ⭐⭐ **"一个显式的短路，所以尾部重复不是必需的但提供了冗余"**。

### 4.4 而三张采样表

```text
FactoryClimb948947  46 个样本 / 3750ms / firstInterval 50 / 180.0f
FactoryDrop977976   13 个样本 / 1150ms / firstInterval 50 / 0.0f
FactoryDrop975974   13 个样本 / 1150ms / firstInterval 100 / 180.0f
```

**⇒ 十六层**：
```text
1. **`46` 个样本【而 `3750ms`**】⇒ **⇒ 而【`50 + 37×100 = 3750`** ✓
2. ⇒ **⇒ 所以【`46` 个样本【恰好【覆盖【那个时长**】
3. ⇒ **`13` 个样本【而 `1150ms`**】⇒ **⇒ 而【`50 + 11×100 = 1150`** ✓（**`12` 个样本**）
4. ⇒ **⇒ ⚠ 但【`13` 个样本**】⇒ **⇒ 一个多出来的**（**那个 `index+1` 的访问**）
5. ⇒ **⇒ 而 `FactoryDrop975974` 的 `firstInterval = 100`**】⇒ **⇒ `100 + 11×100 = 1200 ≠ 1150`**】
```

### 4.5 ⭐⭐⭐ **"`firstInterval = 100` 而 `duration = 1150` ⇒ 公式会用到第 12 个样本之后"**

**⇒ 独立核查**：
```text
`firstInterval = 100`，`duration = 1150`
`elapsed = 1149` ⇒ `index = 1 + (1149-100)/100 = 1 + 10 = 11`，`fraction = 49/100`
⇒ **⇒ 而【访问 `samples[12]`**】⇒ **⇒ 而 `13` 个样本的最后一个【是【索引 `12`** ✓
⇒ **⇒ 所以【恰好**够用**】
```

**✅ ⭐⭐⭐ **"恰好够用（不多不少）"** —— 一个**精确的边界**。

**✅ 与 §468 的"`p == storage.size()` 是唯一的『完全理解』证明"**——**同族**（**第四次"一个**恰好**的边界"**）。

**⚠ 而 `FactoryClimb948947` 的 `46` 个样本**⇒ **`index` 最大 `1 + (3749-50)/100 = 1 + 36 = 37`** ⇒ **访问 `samples[38]`** ⇒ **而 `46` 个样本【有 `8` 个**余量**】**。**

**⇒ 十层**：
```text
`46` 个样本 ⇒ **而被用到【只有【前 `39` 个**（`0..38`）**
⇒ **⇒ 所以【有 `7` 个**未使用的**】
⇒ **⇒ 而【那【与【注释【的"walk-fast 开始在【它的身体【清出【那个编写的 ledge clip【之前**"**一致**（**那 `7` 个【是【走出去**的**）
```

**✅ ⭐⭐⭐ **"那 7 个是走出去的"** —— 一个**与注释一致的读法**。

**✅ 而与注释"**保留那个测量的出口，不是一条到节点中心的直线**"**一致**。**

## 五、**`SvZmNavHeightTolerance` 的 `72` 与 `SV_ZmNavNearestNode` 的"同一个"**

### 5.1 那段

```cpp
// THE FLOOR TEST FIRST. Nearest in plan view is meaningless on a map with
// storeys: the node directly overhead is 15 units away and 212 units up.
if (std::abs(graph.nodes[i][2] - point[2]) > maxHeightDelta)
    continue;
```

### 5.2 二十四层

```text
1. **那个高度检查【先**】（**在【那个平面距离**之前**）**
2. ⇒ **⇒ 因为【在一个【有多层**的地图上【最近【在平面视图里【没有意义**】
3. ⇒ **⇒ （那个【正上方的**节点【是 `15` 单位远【而 `212` 单位**高**）
4. ⇒ **⇒ 所以【顺序【是【那个【正确性**的关键**
```

### 5.3 ⭐⭐⭐ **"那个正上方的节点是 15 单位远而 212 单位高"**

**✅ 与 §478 二 的"`833`（`Z=24`）→ `651`（`Z=120`）"**——**同族**（**第二次"一个**楼层【的实测**"**）**。**

**⇒ 三层**：
```text
§478  **`833 → 651` 的 `96` 单位差**（**一条边**）
§478  **`15` 单位远 / `212` 单位高**（**最近节点**）
⇒ **⇒ 两次【同一个**楼层问题**】
```

**✅ ⭐⭐ **"两次同一个楼层问题"**。

**⚠ 而"那个顺序【是那个正确性的关键**"**⇒ **一个**极精确的实现观察**。**

**⇒ 十层**：
```text
若【先算平面距离**】⇒ **⇒ 那个正上方的节点【距离 `15` ⇒ 【可能【胜**】
若【先查高度**】⇒ **⇒ 那个节点【被【排除** ⇒ **⇒ 正确**】
⇒ **⇒ 所以【顺序**是【正确性**】
```

**✅ ⭐⭐⭐ **"顺序是正确性"** —— 与 §467 的"`++ordinal` 在 `continue` 之前是关键"**同族**（**第二次"一个**语句的顺序【是【一个**行为**"**）。

**✅ 而"那个孤立的节点【从不【作为一个路由的入口/目标**"**⇒ **一个**第二个**的守卫**。**

**⇒ 十层**：
```cpp
// Retain authored node identities, but never choose an isolated node
// as a route entry/goal. Factory live actor 707 selected node 867
// after collision steering and then obtained empty routes forever.
if (graph.neighbours(static_cast<std::uint16_t>(i)).empty()) continue;
```
```text
`neighbours(i).empty()` ⇒ **⇒ 跳过**】
⇒ **⇒ 而【为什么**：**演员 `707` 选了节点 `867`，然后【永远【得到【空的路由**】
⇒ **⇒ 所以【那个守卫【是【一个**实测**的教训**】
```

**✅ ⭐⭐⭐ **"演员 707 选了节点 867，然后永远得到空的路由"** —— 与 §478 二 的"三个演员撞同一面墙"**同族**（**第三次"一个**具体演员【的**具体失败**"**）。

**✅ 与 §478 三 的 `704`/`707`/`708`**⇒ **同一个演员 `707` 出现两次**。

**⇒ 三层**：
```text
`617 → 840` ⇒ **演员 `704`/`707`/`708`** 撞墙
节点 `867` ⇒ **演员 `707`** 得到空路由
⇒ **⇒ 所以【同一批**演员【暴露了【两个**不同的图缺陷**】
```

**✅ ⭐⭐⭐ **"同一批演员暴露了两个不同的图缺陷"** —— 一个**极重要的关联**。

## 六、**`A*` 的启发式与"一个 admisible 的理由"**

### 6.1 那段

```cpp
// A* with a straight-line heuristic, which is admissible here because an edge's
// cost is its own straight-line length.
const auto heuristic = [&](const std::uint16_t node) {
    return planarDistance(graph.nodes[node], graph.nodes[to]);
};
```

### 6.2 二十四层

```text
1. **一个 A* 用【一个直线**启发式**】
2. ⇒ **⇒ 而它【在这里【是 admissible** 的**
3. ⇒ **⇒ 因为【一条边的代价【是【它自己的【直线长度**】
```

### 6.3 ⭐⭐⭐ **"因为一条边的代价是它自己的直线长度"**

**✅ 与 §478 七 的 `SV_ZmNavRouteToClosestReachableNode`**——**一个对照**（**那里**没有启发式**，是 **Dijkstra**）**。**

**⇒ 三层**：
```text
`navRoute` ⇒ **A\***（**有启发式**）
`SV_ZmNavRouteToClosestReachableNode` ⇒ **Dijkstra**（**`open.emplace(0.0f, from)`**）
⇒ **⇒ 两个【不同的**算法**】
```

**✅ ⭐⭐⭐ **"两个不同的算法"** —— 而**那个 Dijkstra 的理由【是【它【必须【遍历【所有可达节点**（**因为【那个目标【不**是【一个**已知的节点**）**。**

**⚠ 而那个 Dijkstra 的 `queuedCost` 【被【用于【打破平局**】**。**

**⇒ 十层**：
```cpp
if (distance < closestDistance ||
    (distance == closestDistance && queuedCost < closestRouteCost))
```
```text
1. **先【比【那个平面距离**】
2. ⇒ **⇒ 若【相等【则【比【那个已排队的代价**】
3. ⇒ **⇒ 所以【一个【两级**的择优**】
```

**✅ ⭐⭐⭐ **"一个两级的择优（先距离，后代价）"** —— 与 §467 的"`bestClientKills` 的三级全序"**同族**（**第四次"一个**确定性的**平局打破**"**）。

**✅ 与 §472 的"平局先死亡更少，然后最低的槽"**——**同族**。

## 七、**`reverseNegotiationEdges` / `reverseBarrierEdges` 的有向性**

### 7.1 那段

```cpp
// MapEnt begin.target -> end.targetname owns traversal direction, even
// without a board group. Reversing a jump-up does not create a drop.
// The previous symmetric graph sent live actors958->945, parking them
// above the ground-floor climb start with no legal descent motion.
```

### 7.2 二十四层

```text
1. **`begin.target` ⇒ `end.targetname` 【拥有【那个遍历的方向**】
2. ⇒ **⇒ 即使【没有【一个板组**】
3. ⇒ **⇒ 因为【反转【一个跳上【不会【创造【一个落下**】
4. ⇒ **⇒ ⚠ 而【之前的对称图【把活的演员 `958 → 945` 送过去**】
5. ⇒ **⇒ 而【让他们【停【在【那个**地面层爬升起点【之上**】
6. ⇒ **⇒ 而【没有【任何合法的下降运动**】
```

### 7.3 ⭐⭐⭐ **"反转一个跳上不会创造一个落下"**

**✅ 这是本报告里**最漂亮的一条"**一个关系【不是【对称**"**。**

**✅ 与 §476 的"`SV_ShouldClipToEntity` 的三层过滤"**——**不同**（那是一个**身份**，这是一个**方向**）但**同族**（**第五次"一个**不对称【是【有意的**"**）。

**⇒ 三层**：
```text
`Walk` ⇒ **对称**（**两头【都能走**）
`jump-up` ⇒ **不对称**（**上去【可以，下来【不行**）
⇒ **⇒ 所以【那个图【必须【携带【一个【有向的**黑名单**】
```

**✅ ⭐⭐⭐ **"那个图必须携带一个有向的黑名单"** —— 而**那【正是 `reverseNegotiationEdges`**。

**⚠ 而"演员 `958 → 945` 停在爬升起点之上"**⇒ **一个**极具体**的失败**。**

**⇒ 十层**：
```text
`958 → 945` ⇒ **通过【一个反转的跳上**】
⇒ **⇒ 而【`945` 【在【那个地面层的爬升起点**之上**】
⇒ **⇒ 而【没有【合法下降 ⇒ 【永远【停在那里**】
⇒ **⇒ 而【那【正是【一个"卡住**"**
```

**✅ ⭐⭐⭐ **"那正是一个『卡住』"** —— 与 §478 二 的"贴墙 1500ms"**同族**（**第四次"一个**具体的**卡住**"**）。

**✅ 而与 §478 五 的"演员 707 得到空路由"**——**同族**（**第五次**）。

**⇒ 归纳**：
```text
① `617 → 840` ⇒ **贴墙**
② 节点 `867` ⇒ **空路由**
③ `958 → 945` ⇒ **停在上面**
⇒ **⇒ 三个【不同**的"卡住"【三个【不同的**图缺陷**】
```

**✅ ⭐⭐⭐ **"三个不同的『卡住』，三个不同的图缺陷"** —— 一个**极清晰的分类**。

## 八、`SV_BuildZmNavGraph` 的七段

```text
① 节点序：`isNavNodeClass` ⇒ "node_" 前缀，按实体串顺序
② 位置校验：`nodes.size() * 3 == table->nodeOriginBits.size()` 然后逐个 `bit_cast<float>` 比对（`SvZmNavPositionTolerance`）
③ 参考节点：BO1 hybrid 的 shadow 节点追加在后
④ 反向边：`node_negotiation_begin.target` → `end.targetname`
⑤ 障碍：`SV_SelectZmBarriers` 的 `outside`/`inside` 按位置身份匹配
⑥ 接地：`resolveGround(i, authored)` 且 `z <= authored + 1` 且 `z >= authored - 256`
⑦ 边准入 + CSR + 动画 + 三个 `negotiationMotion`
```

### 8.1 二十四层

```text
1. **七段，而【第 ② 段【是【一个【双重**的校验**】（**数 + 每一个位置**）**
2. ⇒ **⇒ 而【那【正是【§467 的"`ordinal` 的顺序【是【那个契约**"**】
3. ⇒ **⇒ 所以【那个表的边索引【依赖【那个**实体串的顺序**】
```

### 8.2 ⭐⭐⭐ **"那个顺序是那个契约"**

**✅ 与 §467 的"`++ordinal` 在 `continue` 之前，所以两个类共享一个轴"**——**完全闭合** ✓

**⇒ 三层**：
```text
§467  **`SV_AssignMapEntityNumbers` ⇒ 五个 `Skipped` + 顺序**
§478  **"那个地图自己的节点，在【实体串顺序**里。这个排序【就是【与【那个表的边索引**的契约**"**
⇒ **⇒ 一个【跨文件**的契约**
```

**✅ ⭐⭐⭐ **"一个跨文件的契约"** —— 而**注释明说**："**Kept in step with the list `sv_mapents_mp.cpp` uses to decide which entities consume an entity number -- both walk the SAME entities, and the graph's indices are that walk's order**"**。

**⚠ 而那【意味着【一个**真实的耦合风险**】**。**

**⇒ 十层**：
```text
若【`sv_mapents_mp.cpp` 的 `Skipped` 变了**】⇒ **⇒ 那个 walk 【变了**】
⇒ **⇒ 而【那个图的索引【也【变了**】⇒ **⇒ 而【那个表【没有变**】⇒ **⇒ 全部**【错位**】
```

**✅ ⭐⭐⭐ **"若那个 Skipped 变了，全部错位"** —— 与 §470 的"`SvGameStateFixtureBytes` 必须在同一个提交里重新生成"**完全同族** ✓

**⇒ 三层**：
```text
§470  **"如果你改这个字符串，你必须在同一个提交里重新生成那个数组"**
§478  **"那个排序就是与那个表的边索引的契约"**
⇒ **⇒ 两次"一个**跨文件的不变式【必须【同提交**"**
```

**✅ ⭐⭐⭐ **"一个跨文件的不变式必须同提交"两例**。

**✅ 而**两个 `isNavNodeClass` 的实现不同**】**。**

**⇒ 十层**：
```text
§467  **`Skipped` 五个精确的 classname**（`node_pathnode`/`node_negotiation_begin`/`node_negotiation_end`/`script_struct`/`info_vehicle_node`）
§478  **`isNavNodeClass ⇒ className.starts_with("node_")`**
⇒ **⇒ 两者【选的是【不同的**实体集**】
```

**✅ ⭐⭐⭐ **"两者选的是不同的实体集"** —— 而**注释说**"**Kept in step**"** ⇒ **那【是【一个**可质疑**的主张**。**

**⇒ 三层**：
```text
`starts_with("node_")` ⇒ **包括 `node_pathnode` / `node_negotiation_*` / 其它任何 `node_*`**
而 `Skipped` ⇒ **`node_pathnode` / `node_negotiation_begin` / `node_negotiation_end` 不消耗号**
⇒ **⇒ 所以【两个集【一个是"所有 node_"**，一个是"那些**不消耗号的**"**
```

**⚠ 这是一个**可报告的不一致候选**：那个注释说"kept in step"，但两个谓词**不同**。而 §467 的注释说 `node_negotiation_*` **不消耗**一个实体号。**而 §478 的节点序【只【用 `node_` 前缀**（**不【排除**）**。**

**⇒ 而 `nodes` 的索引【是【那个**图**的索引**（**从 `0` 起，只数 `node_*`**）—— **不是**那个**实体号**。**所以两者【可以【不同**。**

**✅ 结论**："kept in step"**指【的是【那个**顺序**（同样的实体串遍历序**），而不是【同一个**谓词**】**。**

## 九、关键结论

1. **⭐⭐⭐ "一个 DEMO VORONOI 过渡不是自动一个可走边：那个冻结的重建把每个 demo 样本分配到 X/Y 上最近的地图节点，而 Factory 在同一个平面位置之上有几层，所以那个过程放进了不同楼层之间的普通走链接"`** ⇒ **"那个活的失败是节点 `833`（`Z=24`）→ 节点 `651`（`Z=120`）：一个地面层的演员瞄准上面的走道，而那个碰撞求解器**相当正确地**让它永远贴着那道中间的墙"`** —— **独立验证 `120 − 24 = 96 > 72` ⇒ 那条边会被新的判据拒绝**。
2. **⭐⭐⭐ "那个碰撞求解器相当正确地让它永远贴着那道中间的墙"`** ⇒ **"症状是一个『AI 卡住』，而病因是一个边的准入"`** —— 与 §471 的"两个症状一个病因"同族（第二例）。
3. **⭐⭐⭐ `usableEdge` 的五条**（两端接地 / 非黑名单边 / `via != Walk` 免垂直判据 / `|Δz| <= 72`）⇒ **"那个规则只约束推断的边，而协商边的垂直位移是有意的"`** —— 与 §467 的 `Skipped` 一个**精细的对照**（显式五个 vs 一个类的划分）。
4. **⭐⭐⭐ `617 → 840` 的那条黑名单边**：**"三个独立的活演员（`704`/`707`/`708`）在 `617→840` 上撞同一个世界 brush，在 `(-3.375, -14.860, 29.886)`，`fraction 0.032061`，`normalZ 0`。这是一个共享的图缺陷，不是演员局部的拥堵"`** ⇒ **"在构造图时拒绝它一次，而不是让每一个僵尸贴墙 `1500ms` 并重新发现那个同一的障碍"`** —— 与 §475 的"发送轨迹而不是每帧步进"同族（**把一个重复的计算上移一次**）；而 **`fraction 0.032061` 是一个立即的阻挡（不是中途的）**、**`normalZ 0` 是一面垂直的墙**。
5. **⭐⭐⭐ `SvZmNegotiationMotion::position` 的分段插值**：第一段是可变的 `firstInterval`（`50` 或 `100`），之后每 `100ms`；**独立验证 `elapsed = 50 ⇒ index 1, fraction 0` ✓，`1149 ⇒ index 11, fraction 0.49`（而 `13` 个样本恰好够用）**。
6. **⭐⭐⭐ 三张采样表的算术**：`FactoryClimb948947` 的 `50 + 37×100 = 3750` ✓（而 `46` 个样本里**只有前 `39` 个被用到 ⇒ `7` 个余量，那正是"走出去"的**）；`FactoryDrop977976` 的 `13` 个样本、`firstInterval 50`；`FactoryDrop975974` 的 `firstInterval 100` ⇒ **`1149` 时访问 `samples[12]` ⇒ 恰好够用** —— **"恰好够用（不多不少）"**（与 §468 的 `p == storage.size()` 同族）。
7. **⭐⭐⭐ "那个高度检查先（在平面距离之前），因为在一个有多层的地图上最近在平面视图里没有意义：那个正上方的节点是 `15` 单位远而 `212` 单位高"`** ⇒ **"顺序是正确性"`** —— 与 §467 的"`++ordinal` 在 `continue` 之前是关键"同族。
8. **⭐⭐⭐ "从一个孤立的节点【从不【作为一个路由的入口/目标**：Factory 的活演员 `707` 在碰撞转向后选了节点 `867`，然后**永远**得到空的路由"`** —— 而 **`707` 也是 §478 三 的那三个撞墙演员之一** ⇒ **"同一批演员暴露了两个不同的图缺陷"`**。
9. **⭐⭐⭐ "反转一个跳上不会创造一个落下：之前的对称图把活的演员 `958 → 945` 送过去，让他们停在地面层爬升起点之上，而没有任何合法的下降运动"`** ⇒ **"那正是一个『卡住』"`** —— 与 §478 二/五 构成 **"三个不同的『卡住』、三个不同的图缺陷"**（贴墙 / 空路由 / 停在上面）。
10. **⭐⭐⭐ `A*` 的启发式是 admissible "因为一条边的代价是它自己的直线长度"`**，而 **`SV_ZmNavRouteToClosestReachableNode` 是 Dijkstra**（目标不是已知节点）—— 两个不同的算法；而后者有**两级的择优**（先平面距离、后排队代价）—— 第四次"一个确定性的平局打破"（与 §467/§472 同族）。
11. **⭐⭐⭐ 那个跨文件的契约**：**"那个地图自己的节点，在实体串顺序里。这个排序**就是**与那个表的边索引的契约"`**（注释："Kept in step with the list `sv_mapents_mp.cpp` uses to decide which entities consume an entity number"）—— 与 §470 的"如果你改这个字符串，你必须在同一个提交里重新生成那个数组"**同族**（**一个跨文件的不变式必须同提交**）。
12. **⚠ 一个可质疑的表述**：那句"kept in step"指的是**顺序**（同样的实体串遍历序），而**不是同一个谓词** —— `isNavNodeClass` 是 `starts_with("node_")`，而 §467 的 `Skipped` 是**五个精确的 classname**（其中三个是 `node_*`）。两个**集不同**，但**图的索引只数 `node_*`**，与那个**实体号**无关 ⇒ **两者可以不同而都正确**。

## 十、`sv_zm_navgraph_mp.cpp` 全文件总览

**`666` 行。**

**`3` 张手工采样表**：
```text
FactoryClimb948947   46 样本  3750ms  firstInterval 50   180.0f
FactoryDrop977976    13 样本  1150ms  firstInterval 50     0.0f
FactoryDrop975974    13 样本  1150ms  firstInterval 100  180.0f
```

**`7` 个函数**：`SvZmNegotiationMotion::position` / `isNavNodeClass` / `parseOrigin` / `planarDistance` / `SV_BuildZmNavGraph` / `SV_ZmNavNearestNode` / `navEdgeAllowed` / `rebuildRoute` / `navRoute` / `SV_ZmNavRoute` / `SV_ZmNavRouteAvoidingEdge` / `SV_ZmNavRouteAvoidingEdges` / `SV_ZmNavRouteToClosestReachableNode`。

**`5` 条拒绝（`usableEdge` + `navEdgeAllowed`）**：
```text
① 两端不接地
② 黑名单边（617–840）
③ 推断的 Walk 且 |Δz| > 72
④ reverseBarrierEdges 含 (node,next)
⑤ reverseNegotiationEdges 含 (node,next)
   以及：|Δz| > 72 且无 negotiationMotion 且无反向障碍 且 平面距离 < verticalWalkMinPlanar
```

**`12` 个测量锚点**：
```text
Factory demo C-2021-7-31[15-32-16]zm / humanoid 710 / command 69100..73550
type2 起 69100（首快照 69150）/ walk-fast 72850
第三份 Factory demo 的演员 711 独立确认 3750ms（45800→49550）
节点 833（Z=24）→ 651（Z=120）
617→840 撞在 (-3.375,-14.860,29.886) / fraction 0.032061 / normalZ 0
演员 704 / 707 / 708（撞墙）· 演员 707（节点 867 空路由）· 演员 958→945（停在上面）
演员 723 / 670 / 713 从 auto414 下降到 pf683（y~157,z~6），从不 pf682（y30,z69）
节点 948（Z≈93）与 947（Z≈−3）
正上方节点 15 单位远 / 212 单位高
72 单位的地板容差
1500 ms 的贴墙预算
53 条边共享 6 个 xanim 名
```

## 十一、未闭合点

- `verticalWalkMinPlanar` 在 MP 侧的值。
- `SvZmNavGraph::neighbours()` 的实现（`.hpp`）。
- `SV_ZmNavTable` / `SV_ZmNavGroundedTable` / `SV_ZmBo1ReferenceTable` 的 `nodeOriginBits` 布局。
- 下一个文件：`sv_bot_nav_mp.cpp`（`27,960` 字节）。

**已核实（本轮）**：`SvZmNavHeightTolerance = 72.0f`（`.hpp:500`）、`SvZmNavPositionTolerance = 0.05f`（`.hpp:643`）—— 与我由注释推出的 `72` 一致，而那个 `0.05` 是那个**位置校验**（`bit_cast<float>` 逐一比对）的容差，也解释了为什么那段代码对 `float` 做**逐轴 `abs` 比较**而不是**精确相等**。
