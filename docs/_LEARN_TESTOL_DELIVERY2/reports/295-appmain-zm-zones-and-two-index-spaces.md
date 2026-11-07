# 295 · **zm 区域的四张预测表（12/63/61 等）**、**`?N` 与 `cmodel` 是两套索引**、`18` 单位的台阶 + `260` 单位走廊

## 一、范围

本报告学习 `Appmain.cpp` 5440–5660 行。

## 二、`static order` 诊断的**默认关闭**

```php
// ★ 2026-10-13（甲方令「新构建先把热日志修复掉」）：逐实体 `static order` 诊断默认关。
const bool verboseStatics = OlMod::RuntimeLog::verbose();
for (const auto &entity : *entities)
{
    const auto className = entity.value("classname").value_or("");
    const auto model = entity.value("model").value_or("");
    if (!verboseStatics) continue;                      // ← 【在取 classname/model 之后】
    if (className == "script_brushmodel") { ... ordinal++ ... }
    else if (className == "script_model") { ... ordinal++ ... }
}
logGameServer("mapent census total=" + entities->size() +
    " firstDynamicEntityNum=" + FirstDynamicServerEntityNum);
```

### 2.1 ⚠ **`verboseStatics` 检查在**两次 `value()` 之后**

**⇒ 所以即使诊断关着，每个实体都要做两次字符串查找与分配。**

**⇒ 对于 397 个实体 × (classname + model)，这是一笔**无谓的开销**。**

**⚠ 应该把 `if (!verboseStatics) continue;` 移到**循环开头**。**

**⇒ 与 §235 的"热日志修复"同族但**这次没修彻底**。**

### 2.2 而"甲方令「新构建先把热日志修复掉」"

**⇒ 又一次操作者指令。**（§292 的"严禁自己造人机"之后的第二条。）

### 2.3 而 `ordinal++` **只在两种类型时自增**

**⇒ 所以 `ordinal` 是"静态实体序号"（brush + script model）。**

**⇒ 与 §294 的"brush `*N` 随槽序严格上升"配合。**

## 三、`SV_SelectBrushModelSpawns` 与 `SV_SelectScriptModelSpawns`

```cpp
const auto brushSpawns = SV_SelectBrushModelSpawns(*entities);
if (!brushSpawns) { reportFailure("brush_spawn_parse"); return; }
const auto scriptModelSpawns = SV_SelectScriptModelSpawns(*entities);
if (!scriptModelSpawns) { reportFailure("script_model_spawn_parse"); return; }
```

**⇒ 两个阶乘阶段**：

```text
brush_spawn_parse
script_model_spawn_parse
```

**⇒ 与 §294 的六个阶段合起来 ⇒ **八个阶段**。**

## 四、**zm 区域的四张预测表**（本组最重要的一段）

### 4.1 那段

```php
// ZM ZONES AND SPAWN POINTS -- OBSERVATION ONLY. Step 1 of the zombie work:
// nothing consumes this yet. It parses the zone/spawner model out of the map
// entity string and LOGS the counts so the parse can be checked against the
// measured numbers BEFORE anything is built on it.
//
// re/demo-re/21-zm-zones-and-spawners.md predicts, per map:
//     zm_factory_sh   12 zones / 63 spawn points / 61 with a goal
//     zm_sumpf_sh     11 zones / 74 spawn points / 32 with a goal
//     zm_prototype_sh  3 zones / 41 spawn points / 41 with a goal
//     zm_asylum_sh     9 zones / 38 spawn points / 38 with a goal
// Those are the numbers this line must print. A different count means the
// parse is wrong, not that the map is unusual.
//
// A PARSE FAILURE IS LOGGED AND IGNORED ON PURPOSE. This is new code on a path
// four zm maps already load correctly; refusing the world spawn over an
// observational parser would turn a wrong count into a broken map.
```

### 4.2 四张预测表

```text
zm_factory_sh     12 zones / 63 spawn / 61 goal
zm_sumpf_sh       11 zones / 74 spawn / 32 goal
zm_prototype_sh    3 zones / 41 spawn / 41 goal
zm_asylum_sh       9 zones / 38 spawn / 38 goal
```

### 4.3 **"那些就是这个行必须打印的数字。不同的计数意味着解析错了，而不是地图不寻常。"**

**⇒ 这是一个**预注册的判据** —— 在任何代码被写之前先固定期望值。**

**⇒ 与 §288 的"75 个全试过"、§277 的"fraction=0.437363"同族**（第七次"先定期望"）。

### 4.4 而"解析失败记录并**故意忽略**"

```text
1. 这是四个 zm 地图【已经正确加载】的路径上的新代码
2. ⇒ 为一个【观察性】解析器拒绝世界 spawn
3. ⇒ 会把一个错误的计数变成一个**坏掉的地图**
```

**⇒ 与 §244 的"两个方向的代价不对称"同族**（第五次）。

### 4.5 而四个 zm 地图的 `goal` 分布

```text
factory    63 spawn / 61 goal    ⇒ 2 个没有 goal
sumpf      74 spawn / 32 goal    ⇒ 42 个没有
prototype  41 spawn / 41 goal    ⇒ 全有
asylum     38 spawn / 38 goal    ⇒ 全有
```

**⇒ 所以 `sumpf` 有**过半**的 spawn 没有 goal。**

**⇒ 这可能是一个**地图设计特征**（那些点是"纯出生"而不是"巡逻目标"）。**

## 五、**`?N` 与 `cmodel` 是两套索引**（本组第二重要）

### 5.1 那段自我更正

```php
// RESOLVE EACH VOLUME'S SHAPE OUT OF MapEnts.trigger.
//
// NOT through resolveBrushModelCollision. That indexes the clipmap's
// cmodel list while `?N` indexes MapEnts.trigger, and routing zone
// volumes through it reported success on all 32 and returned a
// different brush every time -- see the comment on the reader.
//
// A volume that will not resolve is LEFT UNRESOLVED, and the
// containment test skips it, so the failure mode is "no zone" rather
// than a confidently wrong one.
```

### 5.2 五层

```text
1. 每个 volume 的形状从 `MapEnts.trigger` 解析
2. **不**通过 `resolveBrushModelCollision`
3. 因为**那个索引 clipmap 的 `cmodel` 列表而 `?N` 索引 `MapEnts.trigger`**
4. ⇒ 把 zone volume 走它 ⇒ **32 个全报成功而每次都返回一个不同的 brush**
5. ⇒ 一个解析不了的 volume **保持未解析**，容器测试**跳过它** ⇒ 失败模式是"没有区域"而不是"自信地错"
```

### 5.3 **"32 个全报成功而每次都返回一个不同的 brush"**

**⇒ 这是"检查通过而语义全错"的**最强实例**。**

**⇒ 与 §261 的"骨骼名用附件表 ⇒ 返回武器名"、§250 的"两个 52 字节表互换"同族。**

**⇒ 所以"成功"这个返回值在这里**完全没有意义**。**

### 5.4 而"失败模式是没有区域而不是自信地错"

**⇒ 与 §244 的"读作 NOT enabled 至多漏一个部件"同族**（第六次代价不对称）。

### 5.5 而五个统计

```cpp
size_t zmVolumes{}, zmResolved{}, zmHulls{}, zmSlabs{};
for (auto &zone : *zmZones)
    for (auto &volume : zone.volumes)
    {
        ++zmVolumes;
        auto hulls = Bindings.resolveTriggerModelHulls(request->mapName, volume.triggerModel);
        if (!hulls || hulls->empty()) continue;
        zmHulls += hulls->size();
        for (const auto &hull : *hulls) zmSlabs += hull.slabs.size();
        volume.hulls = std::move(*hulls);
        volume.hullsResolved = true;
        ++zmResolved;
    }
```

### 5.6 五个量

```text
zmVolumes    总 volume 数
zmResolved   成功解析的
zmHulls      总 hull 数
zmSlabs      总 slab 数
（plus zones/spawnPoints/withGoal）
```

**⇒ 所以日志给出"多少个 volume 解析成功"。**

### 5.7 而 `resolveTriggerModelHulls` 是 §258 的函数

**⇒ 它用 `mapEnts->models[triggerModel]` ⇒ 所以是 `MapEnts.trigger` 的空间** ✓

## 六、`Server.setZmZones(*zmZones)` 的**第 2 步**

```php
// HAND THE MODEL TO THE SCRIPT LAYER. Step 2: the zm builtins read
// it from here. Still nothing spawns -- this only makes the parsed
// zones reachable from zm.lua.
Server.setZmZones(*zmZones);
```

**⇒ 三层**：

```text
1. 交给脚本层
2. zm 内置函数从这里读
3. **仍然什么也不生成** —— 只让解析出的区域从 `zm.lua` 可达
```

**⇒ 与 §295 开头的"Step 1: nothing consumes this yet"形成**两阶段推进**。**

### 6.1 而 `zmDetail` 的每个区域格式

```cpp
zmDetail += " " + zone.name + "(v" + zone.volumes.size() + ",p" + zone.spawnPoints.size() + ")";
```

**⇒ `" name(v3,p5)"`** —— 体积数与生成点数。

## 七、**导航图的"空图是合法答案"**

```php
// THE NAVIGATION GRAPH, measured off the zm demos because `aipaths` is
// empty in every shipped zone. re/demo-re/20-zm-actor-lifecycle.md 12.57.
//
// AN EMPTY GRAPH IS A LEGITIMATE ANSWER, not a world-spawn failure: only
// zm_factory_sh has a measured graph, and SV_BuildZmNavGraph also returns
// nothing when the loaded map's nodes disagree with the table it was built
// from. Either way the actors park on their spawners, which is correct
// placement (12.31) rather than a degraded mode.
```

### 7.1 四层

```text
1. 导航图从 zm demo **测量**（因为每个随包 zone 的 `aipaths` 是**空的**）
2. **空图是合法答案**，不是世界 spawn 失败
3. 只有 `zm_factory_sh` 有测量过的图
4. 而 `SV_BuildZmNavGraph` 在"加载地图的节点与建表时不一致"时**也返回空**
5. ⇒ 两种情况下 actors **停在它们的 spawner 上**，那是**正确的放置**而不是降级模式
```

### 7.2 而"`aipaths` 在每个随包 zone 里都是空的"

**⇒ 一个重要事实** —— 所以原生导航数据**不存在**，只能从 demo 反推。

**⇒ 与 §292 的"`OLMOD_ZM_NAV_SOURCE`"和"`bo1_hybrid`"配合。**

## 八、`navGroundResolver` 的**七个条件**（本组第三重要）

```cpp
if (request->mapName == "zm_factory_sh")
{
    navGroundResolver = [](size_t, const std::array<float,3> &origin) -> optional<float> {
        auto start = origin; auto end = origin;
        start[2] += 1.0f;                    // ← 从原点上方 1 开始
        end[2] -= 256.0f;                    // ← 向下 256
        const auto hit = Bindings.traceWorld(start, end, PointTraceBounds,
            PlayerCollisionContentMask & ~PlayerCollisionContents, SvGlassState{});
        if (!hit || hit->startSolid || hit->allSolid ||
            hit->fraction < 0.0f || hit->fraction >= 1.0f || hit->normal[2] < 0.7f)
            return nullopt;
        return start[2] + (end[2] - start[2]) * hit->fraction;
    };
    logGameServer("zm grounded navigation enabled (world-only ground; actor collision retained)");
```

### 8.1 七个条件

```text
hit 存在
!startSolid
!allSolid
fraction >= 0
fraction < 1        ← 【必须真的碰到】
normal[2] >= 0.7    ← 【必须可站立】
```

**⇒ 六项（我多算一项）。**

### 8.2 **`fraction < 1.0` 是必须**

**⇒ 因为 `fraction == 1.0` 意味着"没有碰到地面" ⇒ 不是地面。**

**✓ 与 §267 的"`fraction == 1.0f` 意味着通过"**相反**（那里通过是成功，这里通过是失败）。**

**⚠ 两个相反的语义。**

### 8.3 而 `~PlayerCollisionContents` 的**排除**

```cpp
PlayerCollisionContentMask & ~PlayerCollisionContents
```

**⇒ "玩家碰撞内容**之外**"** —— 所以排除玩家。**

**⇒ 因为"地面"查询不应该打到其他玩家。**

**✓ 与 §266 的 `passFiringEntity` 同族（排除自己/同类）。**

### 8.4 而 `256` 单位的向下距离

**⇒ 与 `+1` 起点的配合 ⇒ 从上方 1 到下方 255。**

**⇒ 所以搜索范围是 256 单位。**

### 8.5 而"仅世界地面；actor 碰撞保留"

```php
logGameServer("zm grounded navigation enabled (world-only ground; actor collision retained)");
```

**⇒ 两层**：

```text
ground resolver   只用世界
actor collision   【保留】
```

**⇒ 所以 actor 仍会与其它 actor 碰撞。**

### 8.6 而 `hit->normal[2] >= 0.7` 与 §266 的 `walkable = normal[2] >= 0.7`

**⇒ 完全相同的阈值** ✓

**⇒ 第三次出现 `0.7`。**

## 九、`bo1_hybrid` 的**四个常量**

```cpp
navReferenceWalkValidator = [](from, to) {
    const auto ground = [](point) {
        start[2] += 18.0f;         // ← 上方 18
        end[2] -= 32.0f;           // ← 下方 32
        ... 同样的七项检查 ...
    };
    const auto clear = [](start, end) {
        constexpr TraceBounds body{
            .midpoint = {0, 0, 35},
            .halfSize = {15, 15, 34},
        };
        const auto hit = Bindings.traceWorld(start, end, body, ...);
        return hit && !hit->startSolid && !hit->allSolid && hit->fraction >= 0.999f;
    };
    return SV_ZmSupportedWalk(from, to, ground, clear, 260.0f) ||
           SV_ZmSupportedStairWalk(from, to, ground, clear);
};
```

### 9.1 五个数

```text
+18      地面搜索上界
-32      地面搜索下界
(0,0,35) 身体中心
(15,15,34) 身体半尺寸
260.0f   最大走廊长度
0.999f   通过的 fraction 阈值
```

### 9.2 而 `halfSize = {15, 15, 34}` 与 §273 的 `maxsZ 70/50/30`

**⇒ `35 + 34 = 69` ≈ 70（站立高度）。**

**✓ 与"70 standing"一致。**

**⇒ 而 `15` 是半径** —— 与 §277 的"玩家胶囊半径约 15"**完全一致** ✓

### 9.3 而 `18` 单位的台阶

```php
// BO1's stored ordinary graph includes staircase links.
// The flat-only validator rejected both teleporter-room
// stairs even though the live CODOL world exposes every
// tread. Admit either a fully flat corridor or a bounded
// sequence of legal 18-unit steps; both paths still require
// continuous live floor support and actor-sized clearance.
```

**⇒ 五层**：

```text
1. BO1 的存储普通图**包含楼梯连接**
2. **纯平坦验证器**拒绝了**两个传送室楼梯**，尽管活的 CODOL 世界暴露了每一级踏面
3. ⇒ 承认要么是**完全平坦的走廊**要么是**有界的 18 单位台阶序列**
4. ⇒ 两条路径**仍要求**连续的活动地板支持与 actor 尺寸的净空
5. ⇒ 所以 `SV_ZmSupportedWalk(..., 260.0f)` **或** `SV_ZmSupportedStairWalk(...)`
```

### 9.4 而"`18` 单位台阶"与 `+18` 的上界

**⚠ `start[2] += 18.0f` 是**地面搜索的上界**而 `18` 单位台阶是**台阶高度**。**

**⇒ 两个不同的用途、同一个数字 —— 可能是**巧合**，也可能是"台阶高度决定了地面搜索范围"。**

**⇒ 从语义看应该**后者**（因为搜索上界要够得着上一级台阶）。**

**✓ 所以是有意的。**

### 9.5 而 `260.0f` 是**最大走廊长度**

**⇒ 所以 `SV_ZmSupportedWalk` 只承认 260 单位以内的直走廊。**

**⇒ 更长的走廊被拒绝** —— 因为"活动地板支持"在长距离上更难保证。

## 十、关键结论

1. **`verboseStatics` 检查在两次 `value()` 之后** —— 即使关着也有开销，未修彻底。
2. **"甲方令「新构建先把热日志修复掉」"** 是第二条操作者指令。
3. **两个 spawn 解析阶段** 加到 §294 的六个 ⇒ 八个。
4. **zm 区域的四张预测表**（12/63/61、11/74/32、3/41/41、9/38/38）。
5. **"那些就是这个行必须打印的数字。不同的计数意味着解析错了"** —— 预注册判据。
6. **"解析失败记录并故意忽略"** —— 观察性代码不能破坏已工作的路径。
7. **`sumpf` 有过半的 spawn 没有 goal** —— 一个地图特征。
8. **`?N` 索引 `MapEnts.trigger` 而 `cmodel` 索引 clipmap** —— 两套索引。
9. **"32 个全报成功而每次都返回一个不同的 brush"** —— "成功"完全无意义的最强实例。
10. **"失败模式是没有区域而不是自信地错"** —— 第六次代价不对称。
11. **`setZmZones` 是 Step 2**，仍不生成任何东西。
12. **`aipaths` 在每个随包 zone 里都是空的** ⇒ 原生导航数据不存在。
13. **"空图是合法答案"** —— actors 停在 spawner 上是**正确放置**。
14. **地面解析的七项条件**，其中 `fraction < 1.0` 是"必须真的碰到"（与 §267 相反的语义）。
15. **`~PlayerCollisionContents`** 排除玩家。
16. **`normal[2] >= 0.7`** 第三次出现。
17. **`halfSize = {15,15,34}` 与 `midpoint z = 35`** ⇒ 高度 69 ≈ 70，半径 15。
18. **`18` 单位的台阶**与 `+18` 的地面搜索上界是**有意的**配合。
19. **`260` 单位是最大走廊长度**。

## 十一、未闭合点

- `verboseStatics` 的开销（397 实体 × 2 次 `value()`）。
- `sumpf` 的 42 个无 goal 的 spawn 的性质。
- `SV_ZmSupportedWalk` 的 260 单位依据。
- `Appmain.cpp` 5660 行之后未读取。
