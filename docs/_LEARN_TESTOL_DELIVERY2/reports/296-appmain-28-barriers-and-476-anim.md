# 296 · **`28 屏障 / 168 板 / 28 翻越`**、`476` 是 `ai_zombie_boardtear_l_1`、`18` 个撕裂片段

## 一、范围

本报告学习 `Appmain.cpp` 5659–5880 行。

## 二、`SV_BuildZmNavGraph` 的**六项参数**

```cpp
auto zmNavGraph = SV_BuildZmNavGraph(
    *entities,
    request->mapName,
    [](std::string_view animName) { return Bindings.resolveAnimConfigStringIndex(animName); },
    navGroundResolver,
    navSource,
    navReferenceWalkValidator);
```

### 2.1 六项

```text
entities            地图实体
mapName             地图名
animResolver        【注入】动画名 → 配置串索引
navGroundResolver   地面解析器（只有 factory 有）
navSource           CodolRecovered 或 Bo1Hybrid
navReferenceWalkValidator  行走验证器
```

**⇒ 两个函数作为**依赖注入**。**

**⇒ 与 §270 的 `ServerCore` 的五参数同族。**

## 三、`bo1_hybrid` 在**非 factory 地图被忽略**

```cpp
else if (bo1HybridRequested)
{
    logGameServer("zm nav source=bo1_hybrid ignored outside zm_factory_sh");
}
```

**⇒ 三层**：

```text
1. `bo1_hybrid` 只在 `zm_factory_sh` 里生效
2. 其它地图 ⇒ **忽略**
3. 且**明说**忽略
```

**✓ 与 §236/§244 的"拒绝要命名"同族。**

## 四、`FACTORYROOM` 草稿的**六个常量**

```cpp
if (const auto *room = std::getenv("OLMOD_FACTORY_ROOM_DRAFT");
    room && std::string_view(room) == "1" &&
    request->mapName == "zm_factory_sh" && bo1HybridRequested)
{
    logGameServer("FACTORYROOM " + SV_ApplyFactoryRoomDraft(zmNavGraph, navGroundResolver,
        navReferenceWalkValidator,
        [](from, to) {
            const auto clear = [](a, b) {
                constexpr TraceBounds compact{{0,0,28},{1,1,20}};    // ← 【极窄】
                const auto hit = traceWorld(a, b, compact, ...);
                return hit && !hit->startSolid && !hit->allSolid && hit->fraction >= 0.999f;
            };
            const auto ground = [](p) { a[2]+=18; b[2]-=32; ... };
            return SV_ZmSupportedStairWalk(from, to, ground, clear, 32.0f, 18.0f);
        }));
}
```

### 4.1 五个常量

```text
{0,0,28} / {1,1,20}     compact 身体（【半径 1】）
+18 / -32               地面搜索
32.0f                   最大走廊
18.0f                   台阶高度
```

### 4.2 **`halfSize = {1, 1, 20}` 是"极窄"的**

**⇒ 与 §295 的 `{15,15,34}`（玩家尺寸）**对比**：**

```text
玩家     {15, 15, 34}
compact  { 1,  1, 20}    ← 【半径 1】只验证一条细线
```

**⇒ 所以 `compact` 只检查"这条细通道是否畅通"而**不检查玩家尺寸的净空**。**

**⇒ 注释说"与 `stepZombieActors` 相同的 compact landing hull，由调用者限制在两个已知的短窗口出口端口"。**

**⇒ 所以这是一个**特定的、窄的用途**。**

### 4.3 而 `SV_ZmSupportedStairWalk(..., 32.0f, 18.0f)` 有**五个参数**

**⇒ 而 §295 的 `SV_ZmSupportedStairWalk(from, from, ground, clear)` 只有**四个**。**

**⚠ 同一个函数两种调用：**

```text
§295  4 参数（无长度与台阶高度 ⇒ 用默认）
§296  5 参数（32.0f 长度 + 18.0f 台阶）
```

**⇒ 所以它有**默认参数**。**

## 五、导航图的**四个统计**

```cpp
const auto zmNavNodes = zmNavGraph.nodes.size();
const auto zmNavEdges = zmNavGraph.adjacency.size() / 2u;
const auto zmNavVaults = zmNavGraph.vaultAnim.size();
const auto *const zmNavTable = SV_ZmNavTable(request->mapName);
```

### 5.1 三项 + 一个表

```text
nodes       节点数
edges       adjacency.size() / 2      ← 【因为无向图每边存两次】
vaults      vaultAnim.size()
table       SV_ZmNavTable(mapName)    ← 【可能为 null】
```

**⇒ 与 §292 的 `316 nodes / 956 entries` 一致（956/2 = 478 边）** ✓

**⚠ 而 §292 说 "956 entries" 是 CSR 条目而这里是 `adjacency.size()`。**

**⇒ 若 adjacency.size() == 956 ⇒ 478 边。**

**✓ 吻合。**

## 六、两个**审计开关**

### 6.1 `OLMOD_ZM_NODE_GROUND_AUDIT`

```cpp
// Diagnostic only: authored node Z is not the walking surface. Keep
// the current graph untouched while measuring retained world collision
// under its nodes for comparison with absolute Factory demo positions.
// One map-load pass, opt-in; never runs in the actor/frame loop.
if (audit == "1")
{
    for (node : zmNavGraph.nodes)
    {
        start = node; end = node;
        start[2] += 1.0f; end[2] -= 256.0f;
        const auto hit = traceWorld(...);
        logGameServer("ZMNODEGROUND node=" + node + " authoredZ=" + node[2] +
            " fraction=" + hit->fraction + " z=" + 解析出的地面 z +
            " startSolid= allSolid= normalZ=");
    }
}
```

**⇒ 四个量**：

```text
authoredZ     作者写的 z
fraction      trace 的 fraction
z             由 trace 算出的地面 z
startSolid / allSolid / normalZ
```

**⇒ 所以"作者写的 z 与真实地面 z"可以直接对比。**

**⇒ 与 §294 的"brush 锚点"同族（用已测量的作为锚）。**

### 6.2 `OLMOD_ZM_CORRIDOR_AUDIT`

```php
// Research-only, one map-load pass. Compare a rejected node chord
// against absolute demo20-21-43 actor810, 921800..924950. World-only
// sweeps do not establish clearance against dynamic doors or actors.
if (audit == "1" && mapName == "zm_factory_sh" && navGroundResolver &&
    zmNavGraph.nodes.size() > 871u)
{
    constexpr std::array<array<float,3>, 7> samples{{
        {-757.0f,-281.0f,67.0f}, {-744.0f,-328.0f,67.0f},
        {-738.0f,-353.0f,68.0f}, {-730.0f,-378.0f,68.0f},
        {-723.0f,-403.0f,67.0f}, {-717.0f,-422.0f,67.0f},
        {-698.0f,-478.0f,67.0f}}};
    ...
    probe("chord869to871", nodes[869], nodes[871]);
    for (i = 1; i < samples.size(); ++i) probe("demo810leg" + i, samples[i-1], samples[i]);
    constexpr std::array<array<float,3>, 7> climbExit{{
        {62,213,96},{59,212,95},{54,208,95},{48,205,95},
        {43,201,95},{37,198,95},{31,195,93}}};
    for (i) probe("climbExit710point" + i, climbExit[i], climbExit[i]);
}
```

### 6.3 **三组探针**

```text
chord869to871        被拒绝的节点弦
demo810leg1..6       绝对 demo 的 6 段腿（actor810）
climbExit710point0..6  7 个点（【起点=终点】的零长度探针）
```

### 6.4 而 `climbExit` 的**7 个绝对坐标**

```text
{62,213,96} {59,212,95} {54,208,95} {48,205,95}
{43,201,95} {37,198,95} {31,195,93}
```

**⇒ 从 (62,213,96) 到 (31,195,93)** —— 一个**递降**的路径。**

**⇒ 而 `probe(point, point)` 是**零长度**的 ⇒ 只问"这个点是否在实心内"。**

**✓ 与 §267 的 `contactBrushModel` 的 `start == end` 同族。**

### 6.5 而"仅世界的扫掠不能对着动态门或 actor 建立净空"

**⇒ 一个**明确的局限声明** —— 所以这个审计**不能代替**实测。**

**⇒ 与 §288 的"75 个全试过"同族（第七次"承认局限"）。**

### 6.6 而 `nodes.size() > 871u` 的门

**⇒ 因为要访问 `nodes[869]` 与 `nodes[871]`。**

**⇒ 所以这是一个**越界防护** ✓

## 七、**`28 屏障 / 168 板 / 28 翻越`**（本组最重要的一段）

### 7.1 那段

```php
// THE BARRIERS. A board group joined to the traversal sharing its `pfNNN`
// prefix -- 12.66. Expect 28 barriers / 168 boards / 28 vaulted on factory.
const auto zmBarriers = SV_SelectZmBarriers(*entities);
size_t zmBoards{}, zmVaulted{};
std::map<size_t, size_t> zmBoardsPer;
for (const auto &barrier : zmBarriers)
{
    zmBoards += barrier.boards.size();
    zmVaulted += barrier.hasVault ? 1u : 0u;
    ++zmBoardsPer[barrier.boards.size()];
}
std::string zmBoardShape;
for (const auto &[count, howMany] : zmBoardsPer)
    zmBoardShape += " " + howMany + "x" + count;
```

### 7.2 三个预测

```text
28 barriers
168 boards    （= 28 × 6）
28 vaulted    （【每一个】都可翻越）
```

### 7.3 而 `zmBoardsPer` 是**形状直方图**

```text
" 28x6"      ⇒ 28 组各 6 板
```

**⇒ 所以一次日志给出"多少组 × 多少板"的分布。**

**✓ 与 §144 的"barrier 3 lanes × 6 boards"一致** ✓

**⇒ 而 168 = 28 × 6 ⇒ 所以**全是 6 板**。**

**⇒ 而 §144 说"3 lanes × 6 boards"** ⇒ 那是**一个** barrier 的内部结构（3 条道 × 6 板 = 18）。**

**⚠ 而这里 6 板/组 ⇒ 可能是"一组的板数"而不是"3 道 × 6"。**

**⇒ 总之：168/28 = 6。**

### 7.4 而"板组连接到**共享其 `pfNNN` 前缀**的遍历"

**⇒ 所以 `pfNNN` 是**配对键**。**

**⇒ 与 §144 的"`factoryCentreFalseEdge` 617→840 rejection"同族（用名字前缀配对）。**

### 7.5 而 `Server.setZmBarriers` **在导航图之后**

```php
// AFTER the nav graph: a barrier is keyed by the node pair of its traversal,
// so the graph has to exist before the barriers can be resolved onto it.
Server.setZmBarriers(zmBarriers);
```

**⇒ 三层**：

```text
1. barrier 用它的**遍历的节点对**作键
2. ⇒ 图必须先存在
3. ⇒ 所以 `setZmBarriers` 在 `setZmNavGraph` 之后
```

**⇒ 与 §247/§248 的"发布顺序是严格依赖链"同族** ✓

### 7.6 而 `onGraph` **低于 `vaulted` 是预期的**

```php
// How many resolved onto a graph EDGE, which is what the stepper can
// actually gate on. Lower than `vaulted` means some traversals are not
// in the graph -- expected, the graph is a measured floor (12.58).
" onGraph=" + Server.zmBarrierCount()
```

**⇒ 三层**：

```text
1. `onGraph` = 解析到**图的一条边**上的数量
2. 那才是 stepper 真正能门控的
3. 低于 `vaulted` ⇒ 有些遍历不在图里 —— **预期之内**，图是**测量出来的地板**（12.58）
```

**⇒ 与 §295 的"空图是合法答案"同族**（第八次"缺失即答案"）。

## 八、**`476` 是 `ai_zombie_boardtear_l_1`**

### 8.1 那段

```php
// THE BASE ANIMATION, resolved the same way and for the same reason. 476 --
// what every actor has published since 12.53 -- is `ai_zombie_boardtear_l_1`,
// a zombie tearing boards off a barrier, held forever (12.61).
const auto zmWalkAnim = Bindings.resolveAnimConfigStringIndex(SvActorWalkAnimName);
Server.setZmActorWalkAnim(zmWalkAnim.value_or(uint16{}));
const auto zmTearAnim = Bindings.resolveAnimConfigStringIndex(SvActorTearAnimName);
Server.setZmActorTearAnim(zmTearAnim.value_or(uint16{}));
```

### 8.2 四层

```text
1. **476** 是每个 actor 自 12.53 以来一直发布的动画
2. 而它是 `ai_zombie_boardtear_l_1` —— **一个僵尸从屏障上撕板子**
3. 而它被**永远保持**（12.61）
4. ⇒ 所以"僵尸一直在撕板子"是 476 的语义后果
```

**⇒ 一个**极具体的症状与其数值根因**。**

### 8.3 而 `SvActorWalkAnimName` / `SvActorTearAnimName` / `SvActorDeathAnimName`

**⇒ 三个名字常量在 `sv_zm_special_mp.hpp` 里。**

### 8.4 而 `value_or(uint16{})` ⇒ 0

**⇒ 所以解析失败 ⇒ 0 ⇒ 而 0 是"无动画"。**

**⇒ 与 §240 的"0 = 空"一致。**

## 九、**18 个撕裂片段**（本组第二重要）

```cpp
SvZmTearClips tearClips{};
size_t tearClipCount{};
if (request->mapName == "zm_factory_sh")
{
    for (size_t lane = 0; lane < 3; ++lane)
        for (size_t slot = 0; slot < 6; ++slot)
        {
            const auto name = "ai_zombie_boardtear_" + "lmr"[lane] + "_" + (slot+1);
            const auto alias = resolveAnimConfigStringIndex(name);
            const auto markers = animationNotifyTimes(name);
            if (!alias || !markers) continue;
            optional<float> boardTime, endTime;
            bool duplicate = false;
            for (const auto &[id, seconds] : *markers)
            {
                const auto marker = animationNotifyName(id);
                if (marker == "board") { duplicate |= boardTime.has_value(); boardTime = seconds; }
                else if (marker == "end") { duplicate |= endTime.has_value(); endTime = seconds; }
            }
            if (!duplicate && boardTime && endTime)
                tearClips[lane][slot] = SV_ZmTearClipFromMarkers(*alias, *boardTime, *endTime);
            if (tearClips[lane][slot].valid()) ++tearClipCount;
        }
}
Server.setZmTearClips(tearClips);
logGameServer("zm tear marker profiles resolved=" + tearClipCount + "/18");
```

### 9.1 **3 × 6 = 18 个**

```text
lane ∈ {l, m, r}          3
slot ∈ {1..6}             6
⇒ 18 个片段
```

**⇒ 与 §144 的"barrier 3 lanes × 6 boards"**完全一致** ✓**

### 9.2 而名字格式

```text
ai_zombie_boardtear_l_1
ai_zombie_boardtear_l_2
...
ai_zombie_boardtear_r_6
```

**⇒ `"lmr"[lane]` 是**左中右**。**

### 9.3 而 `boardTime` / `endTime` 两个标记

```text
"board"   ⇒ 板子脱离的时刻
"end"     ⇒ 动画结束的时刻
```

**⇒ 所以一个片段 = (别名, 板子时刻, 结束时刻)。**

**⇒ 与 §260 的 `animationNotifyTimes` 返回 `(id, seconds)` 对一致** ✓

### 9.4 而**重复检测**

```cpp
duplicate |= boardTime.has_value();   // ← 【如果已有值则 duplicate】
boardTime = seconds;
```

**⇒ 如果同一个动画里有**两个** "board" 标记 ⇒ `duplicate = true` ⇒ 拒绝。**

**⇒ 因为"哪个才是真正的板子脱离时刻"不确定 ⇒ 拒绝。**

**✓ 与 §264 的"二义即失败"同族。**

### 9.5 而"空条目保持未解析；没有猜的别名或回退计时器"

```php
// Resolve once per map, never by scanning assets in the actor frame.
// Empty entries stay unresolved; no guessed alias or fallback timer.
```

**⇒ 三层**：

```text
1. 每地图一次，**绝不在 actor 帧里扫描资产**
2. 空条目**保持未解析**
3. **没有猜的别名或回退计时器**
```

**✓ 与 §292 的"没有任何东西被发明"同族**（第九次）。

### 9.6 而 `resolved=N/18` 的分母是**硬的**

**⇒ 所以"N/18"直接给出完成度。**

## 十、`OLMOD_FACTORY_PRESENTATION` 的**颜色规格**

```php
// OLMOD(zm-round-colors): tag resident aliases once; spawn-time
// color selection is independent of the clothing-family cycle.
struct ColorSpec { const char *suffix; BodyColor color; };
const ColorSpec colors[]{
    {"_body_blue", BodyColor::Blue},
    {"_body", BodyColor::Base},
    {"_body_orange", BodyColor::Orange},
    {"_body_red", BodyColor::Red},
    {"_body_yel", BodyColor::Yellow}};
for (const auto &[suffix, color] : colors)
    for (const auto *family : {"garbageman", "worker", "secunityguard"})
    {
        const auto stem = "c_zom_" + std::string(family);
        const auto body = lookup(stem + suffix), head = lookup(stem + "_head");
        ...
    }
```

### 10.1 五色 × 三族 = 15 个身体

```text
五色    blue / Base / orange / red / yellow
三族    garbageman / worker / secunityguard
```

### 10.2 ⚠ **`"_body"` 在 `"_body_blue"` 之后**

**⇒ 所以 `lookup("c_zom_garbageman_body")` 会先于 `_body_blue` 被查。**

**⚠ 但如果 `_body` 是 `_body_blue` 的**前缀**，`lookup` 用**精确相等** ⇒ 不冲突。**

**✓ 因为 `lookup` 是 `entry == name`。**

### 10.3 而 `"secunityguard"` 是**拼写错误**？

**⇒ 应该是 `"securityguard"`。**

**⚠ 可能是一个**真实的资源名**（游戏里的拼写错）或**我们的拼写错**。**

**⇒ 从 `c_zom_secunityguard` 看，如果是资源名则必须照抄。**

### 10.4 而 `lookup` 是**线性扫整个 model band**

```cpp
const auto models = Bindings.modelConfigStringBand();
const auto lookup = [&](const std::string &name) -> uint16 {
    for (const auto &[index, entry] : models) if (entry == name) return index;
    return 0;
};
```

**⇒ 每次 `lookup` 是 O(1024)。**

**⇒ 而 15 个身体 + 3 个头 ≈ 18 次 ⇒ 18 × 1024 = 18,432 次比较。**

**⇒ 一次地图加载 ⇒ 可接受。**

**⚠ 但可以建一个 `unordered_map` 一次。**

## 十一、关键结论

1. **`SV_BuildZmNavGraph` 六项参数含两个注入的函数**。
2. **`bo1_hybrid` 在非 factory 地图被忽略且明说**。
3. **`FACTORYROOM` 的 `compact` 用 `{1,1,20}`（半径 1）** —— 只验证细通道。
4. **`SV_ZmSupportedStairWalk` 有 4 参数与 5 参数两种调用**（默认参数）。
5. **`edges = adjacency.size() / 2`** —— 无向图每边存两次；与 §292 的 956 条目吻合。
6. **两个审计：节点地面（`authoredZ` vs 真实 z）与走廊（`chord869to871` + demo 腿 + climbExit 点）**。
7. **`probe(point, point)` 是零长度** —— 只问"是否在实心内"。
8. **"仅世界的扫掠不能对着动态门或 actor 建立净空"** —— 明确的局限声明。
9. **`28 屏障 / 168 板 / 28 翻越`** 的预测，而 168/28 = 6 板/组。
10. **`pfNNN` 前缀是屏障与遍历的配对键**。
11. **`setZmBarriers` 必须在 `setZmNavGraph` 之后**（用节点对作键）。
12. **`onGraph` 低于 `vaulted` 是预期的**（图是测量出来的地板）。
13. **`476` 是 `ai_zombie_boardtear_l_1` ⇒ 僵尸永远在撕板子**（12.61）。
14. **18 个撕裂片段 = 3 lanes × 6 slots**，与 §144 完全一致。
15. **`boardTime`/`endTime` 两个标记，重复即拒绝**。
16. **"空条目保持未解析；没有猜的别名或回退计时器"** —— 第九次"不发明"。
17. **`resolved=N/18` 的分母是硬的**。
18. **五色 × 三族 = 15 个身体**，而 `"secunityguard"` 可能是拼写问题。
19. **`lookup` 是 O(1024) 线性扫，18 次 ≈ 18k 次比较**。

## 十二、未闭合点

- `"secunityguard"` 是资源名还是拼写错。
- `SV_ZmSupportedStairWalk` 的默认参数值。
- `476` 这个索引是配置串索引还是别名索引。
- `Appmain.cpp` 5880 行之后未读取。
