# 467 · **`sv_mapents_mp.cpp` 全文件收尾** —— "目标是一个『名字』而不是一个『目的地』"、`pfNNN` 前缀是全部的键、以及一个"形状不在这里"

## 一、范围

本报告学习 `sv_mapents_mp.cpp` 70–618 行与 955–1415 行，收尾整个文件（**共 `1,415` 行**）：`quotedString` 的两字符转义、`parseVector` 的"必须恰好三个且恰好用尽"、`parseBrushModel` / `parseTriggerModel` 的 `*`/`?` 分离、`entityAngles`、`regularMultiplayerEligibility`、`SV_SelectLogicalMapEntities`、`SV_SelectTopPlayersCamera`/`Places`、`SV_SelectInitialSpawn` 的六元回退表、`SV_SelectModeSpawnPoints`、`SV_AssignMapEntityNumbers`、`SV_SelectZmBarriers` 的三趟、`SV_SelectZmZones` 的三趟与目标解析、`SV_ZmVolumeContains`、`SV_ZmZoneAdjacency`、`SV_ZmZoneAt`。

## 二、**"为一个 `player_volume` 的 `target` 是一个『名字』而不是一个『目的地』"**（本组最重要的一段）

### 2.1 那段

```cpp
// MEASURED, zm_factory_sh MapEnts: 61 of its 69 `zombie_spawner`
// structs carry a `target`, ALL 61 resolve, and every one resolves to
// a `node_pathnode` -- the map's own AI navigation nodes -- 159 to 738
// units away. That is retail's pathing data, not a choice made here.
//
// THE NAME ALONE WAS NOT USABLE. This struct's old comment called
// `goal` "retail's navigation goal", but it is a NAME and the first
// factory spawn point's reads `outside_up_spawners` -- a spawner GROUP.
// It has to be resolved, never trusted as a destination.
//
// An unresolved goal stays ABSENT rather than defaulting: a zombie with
// no goal must stand still, not walk to (0,0,0).
```

### 2.2 二十四层

```text
1. **测量 `zm_factory_sh` MapEnts**：`69` 个 `zombie_spawner` 里的 `61` 个【带一个 `target`**】**
2. ⇒ **【全部 `61` 个都解析**】**
3. ⇒ **⇒ 而【每一个都解析到一个 `node_pathnode`**】】
4. ⇒ **（**地图自己的 AI 导航节点**）**
5. ⇒ **距离 `159` 到 `738` 单位**
6. ⇒ **⇒ 【那是零售的 pathing 数据，不是这里做的一个选择**】**
7. ⇒ **⚠ 【光那个名字【不可用**】】**
8. ⇒ **（**这个结构的旧注释叫 `goal` "零售的导航目标"**）**
9. ⇒ **⇒ 但【它是一个【名字**】】
10. ⇒ **⇒ 而【第一个 factory 出生点的【读作 `outside_up_spawners`**】】
11. ⇒ **⇒ 【**一个 spawner **组**】**
12. ⇒ **⇒ 【它【必须被解析，绝不能被信任**为一个目的地】】
13. ⇒ **⇒ ⚠ 而【一个未解析的目标【保持【缺席**】】
14. ⇒ **⇒ 而【不取默认**】】
15. ⇒ **⇒ 因为【一个【没有目标**的僵尸【必须站着不动**】】
16. ⇒ **⇒ 而【不走 `(0,0,0)`**】】
```

### 2.3 ⭐⭐⭐ **"它必须被解析，绝不能被信任为一个目的地"**

**✅ 这是本报告里**最重要的一条"一个名字与一个位置的混淆**。**

**✅ 与 §462 的"`clientNum` 是一个错的 MW3 名字"**——**不同**（那里是一个**标签错**，这里是**一个类型错**）。

**⇒ 三层**：
```text
`goal` 的类型：**`std::string`**（**一个名字**）
而旧代码把它当一个**位置**用
⇒ **⇒ 所以【那一类 bug 【编译得过**而【运行时**指向一个组**
```

**✅ ⭐⭐⭐ **"那一类 bug 编译得过而运行时指向一个组"**。</br>

**✅ 而"`outside_up_spawners` 是一个 spawner 组"⇒ **一个具体的反例**。**

**⇒ 十层**：
```text
若【`goal` 被当成位置**】⇒ **`outside_up_spawners` 解析成 `(0,0,0)`**（或崩溃）
而【它是一个【组名**】⇒ **所以【僵尸【会走错方向**】
⇒ **⇒ 而实际解析到【一个 `node_pathnode`** ⇒ **一个真实的 AI 导航节点**
```

**✅ ⭐⭐⭐ **"而实际解析到一个真实的 AI 导航节点"** —— 一个**正确的实现**。

### 2.4 而**"一个未解析的目标保持缺席，不取默认"**

**✅ 与 §464 的"槽 `20` 静默不做而不是夹"**同族（**第十三次"省略优于错误**）。

**⇒ 三层**：
```text
默认 ⇒ **僵尸走 `(0,0,0)`** ⇒ **走到地图外** ⇒ **看上去像"AI 坏了**"
缺席 ⇒ **站着不动** ⇒ **一个可见的症状**
⇒ **⇒ 所以【后者正确**】
```

**✅ ⭐⭐⭐ **"缺席让症状可见"** —— 与 §463 的"静默让 bug 不被掩盖"**同族**（**第二次"静默优于默认**）。

**⇒ 三层**：
```text
§463  **`slot >= 15` ⇒ 静默不做**（**不夹**）
§467  **`goal` 未解析 ⇒ 保持缺席**（**不默认**）
⇒ **⇒ 两次"不取一个错误的默认**】
```

**✅ ⭐⭐ **"不取一个错误的默认"两例**。

### 2.5 而**"两趟"的必然性**

```cpp
// RESOLVE EVERY GOAL NAME TO A POSITION. A second pass, because a
// spawner can target a node that appears later in the entity list.
```

**⇒ 六层**：
```text
1. **一个生成器【可以指向一个【在实体列表里更后面出现**的节点**】
2. ⇒ **⇒ 所以【必须【两趟**】
3. ⇒ **⇒ 而【一趟【会漏掉那些后出现的**】
```

**✅ ⭐⭐ **"一个生成器可以指向一个更后面出现的节点"** —— 一个**顺序无关性**的要求。

**✅ 与 §466 的 `Skipped` 顺序依赖**——**一个精确的对照**（那里**顺序重要**，这里**顺序不重要但必须两趟**）。

## 三、**`pfNNN` 前缀是全部的键**（本组第二重要）

```cpp
// The `pfNNN` prefix is what joins a board group to its traversal. Everything
// after the first underscore differs between the two -- factory's boards are
// `pf678_auto1` and its negotiation pair is `pf678_auto2108` -- so the prefix
// is the whole of the key.
const auto prefixOf = [](const std::string_view name) {
    const auto cut = name.find('_');
    return cut == std::string_view::npos ? name : name.substr(0, cut);
};
```

**⇒ 十层**：
```text
1. **`pfNNN` 前缀【把一块板组【与它的遍历【连起来**】】**
2. ⇒ **第一个下划线【之后的一切【在两者之间【不同**】】
3. ⇒ **（factory 的板是 `pf678_auto1` 而它的协商对是 `pf678_auto2108`**）**
4. ⇒ **⇒ 所以【前缀【是【那个键的【全部**】】】
```

### 3.1 ⭐⭐⭐ **"前缀是那个键的全部"**

**✅ 与 §454 的"`144` 个 profile = `24` 个障碍 × `6` 个槽"**——**一个前向引用** ✓

**⇒ 三层**：
```text
§467  **板组【按 `pfNNN`**分组**】
§454  **`144` 个 profile 是【`24` 个障碍 × `6` 个槽**】
⇒ **⇒ 所以【`24` 个障碍【就是【`24` 个 `pfNNN` 前缀**】
```

**✅ ⭐⭐⭐ **"`24` 个障碍就是 `24` 个 `pfNNN` 前缀"** —— 一个**跨报告的确定**。

**⚠ 而"`pf678_auto1` 与 `pf678_auto2108`"⇒ **一个精确的实例**。**

**⇒ 十层**：
```text
板：`pf678_auto1`
协商对：`pf678_auto2108`
⇒ **⇒ 两个【共享 `pf678`**】
⇒ **⇒ 而【第一个下划线【之后【不同**】
```

**✅ ⭐⭐ **"两个共享 `pf678`"**。</br>

**✅ 与 §454 的"`SV_ZmBoardFlightTable` 的 `at()` 九个守卫"**配合。

### 3.2 而**"`script_noteworthy` 是 `1..6` 槽，而没有它的板仍然算一块板"**

```cpp
// `script_noteworthy` is the 1..6 slot. A board without one still counts as
// a board -- the group is what matters -- so index 0 records "unslotted"
// rather than dropping it and changing the count.
```

**⇒ 八层**：
```text
1. **`script_noteworthy` 【是 `1..6` 的槽**】
2. ⇒ **⚠ 而一个【没有它的**板【仍然算一块板**】】
3. ⇒ **因为【组【是重要的那个**】】
4. ⇒ **⇒ 所以【索引 `0` 记录"**无槽**"**】
5. ⇒ **⇒ 而【不【丢弃它**并**改变那个计数**】
```

**✅ ⭐⭐⭐ **"索引 0 记录『无槽』而不是丢弃它并改变那个计数"** —— 一个**极精确的计数保护**。

**✅ 与 §454 的"`24 × 6 = 144`"**——**一个**必须**成立的算术。

**⇒ 三层**：
```text
若【丢弃无槽的板**】⇒ **`groups` 的 size 变** ⇒ **而 `144/24 = 6` 会不成立**
保留 ⇒ **计数稳定** ⇒ **而"无槽**"是【一个可见**的槽**
⇒ **⇒ 所以【保留是【正确的**】
```

**✅ ⭐⭐⭐ **"保留是正确的"** —— 而 **"无槽"作为一个可观测状态** 是**本文件的一个设计原则**。

**✅ 与 §466 的"`bombzone` 缺失 ⇒ 拒绝"**——**相反**（那里**缺失即失败**，这里**缺失即记录**）。

**⇒ 三层**：
```text
§466  **`bombzone` 不足两个 ⇒ `nullopt`**（**缺失即失败**）
§467  **板无槽 ⇒ 索引 `0`**（**缺失即记录**）
⇒ **⇒ 所以【由【那个计数的用途**决定**
```

**✅ ⭐⭐⭐ **"由那个计数的用途决定"** —— 一个**精确的判据**。

## 四、**`SV_SelectZmZones` 的三趟与"两个卷声称一个区名但指向不同组是矛盾"**

### 4.1 "一个区名 + 一个组"（`info_volume` + `player_volume`）

```cpp
// A player_volume with no name or no group cannot be placed. All 132
// player_volumes across the four zm maps carry both.
```

**⇒ 八层**：
```text
1. **`classname == "info_volume"` + `script_noteworthy == "player_volume"`**
2. ⇒ **`targetname` ⇒ 【区名**】
3. ⇒ **`target` ⇒ 【生成器组**】
4. ⇒ **而【四个 zm 地图上的全部 `132` 个 `player_volume` 【都带这两个**】**
5. ⇒ **⇒ 所以【一个缺它们的 ⇒ `nullopt`**】
```

**✅ ⭐⭐⭐ **"`132` 个全部带这两个"** —— 一个**完备的测量**。

**⚠ 而"两个卷声称一个区名但指向不同组"⇒ **一个"不可解决的矛盾"**。**

```cpp
// Two volumes claiming one zone name for DIFFERENT groups is a
// contradiction this parse cannot resolve, not a merge to paper over.
if (existing->spawnerGroup != *group)
    return std::nullopt;
```

**⇒ 八层**：
```text
同一个区名 ⇒ **两个组**
⇒ **⇒ 【这个解析【不能解决**】】
⇒ **⇒ 而【不是一个【可以糊过去的合并**】**
```

**✅ ⭐⭐⭐ **"不是一个可以糊过去的合并"** —— 与 §466 的"重复 label ⇒ 拒绝"**同族**（**第九次"全或无**）。

**⇒ 三层**：
```text
§466  **`bombzone` 重复 label ⇒ 拒绝**
§467  **`player_volume` 两个组 ⇒ 拒绝**
⇒ **⇒ 两次"一个不可解决的矛盾 ⇒ 拒绝**】
```

**✅ ⭐⭐ **"一个不可解决的矛盾 ⇒ 拒绝"两例**。

### 4.2 而**"`zombie_dog_spawner` 与 `zombie_spawner` 同处"**

```cpp
// `zombie_dog_spawner` is admitted alongside `zombie_spawner`
// because zm_factory_sh carries a dog spawner and nothing here needs to
// separate them yet.
```

**⇒ 六层**：
```text
1. **两个 noteworthy【都被接受**】
2. ⇒ **理由：【`zm_factory_sh` **带一个狗生成器**】**
3. ⇒ **⇒ 而【这里【没有什么**需要分开它们**】
4. ⇒ **⇒ 所以【一个"暂时不区分**"的决定**
```

**✅ 与 §435 的"这缩短窗口，它不关闭它"**同族（**第五次"一个保留但不推荐的路径**）。

**⇒ 三层**：
```text
§462  **`altForceTest` 保留但不要用**
§467  **`zombie_dog_spawner` 接受但不区分**
⇒ **⇒ 两次"接受但不区分**】
```

**✅ ⭐⭐ **"接受但不区分"两例**。

### 4.3 而**"一个空区 ⇒ 拒绝"**

```cpp
// A zone that resolves to no spawn points would silently stop spawning in
// that part of the map. All 35 zones across the four zm maps carry at least
// two, so an empty one means the group name did not resolve.
for (const auto &zone : zones)
    if (zone.spawnPoints.empty()) return std::nullopt;
```

**⇒ 十层**：
```text
1. **全 `35` 个区【每一个至少两个**出生点】**
2. ⇒ **⇒ 所以【一个空区【意味着【那个组名【没有解析**】】】
3. ⇒ **⇒ 而【一个空区【会【静默地停止**在那个地图部分生成**】】
4. ⇒ **⇒ 所以【拒绝比静默好**】
```

**✅ ⭐⭐⭐ **"一个空区会静默地停止在那个地图部分生成，所以拒绝比静默好"** —— 与 2.4 的"缺席优于默认"**同族**（**第三次"拒绝优于静默"）。

**⇒ 三层**：
```text
§463  **`slot >= 15` ⇒ 静默**（**调用者 bug**）
§467  **`goal` 未解析 ⇒ 缺席**（**数据缺失**）
§467  **空区 ⇒ 拒绝**（**解析失败**）
⇒ **⇒ 三次"不可用即暴露**】
```

**✅ ⭐⭐ **"不可用即暴露"三例表**。

### 4.4 而**"`65` 个里 `61` 个带 `target`，`8` 个不带"**的算术

**⇒ 十层**：
```text
`69` 个 `zombie_spawner`
`61` 个带 `target`
⇒ **`69 - 61 = 8` 个不带**
⇒ **⇒ 而这 `8` 个【`goal` 为空** ⇒ **站着不动**（**§2.4 的"缺席**"）
```

**✅ ⭐⭐ **"那 `8` 个 `goal` 为空 ⇒ 站着不动"** —— 一个**可推导的行为**。

## 五、**`SV_ZmVolumeContains` 的"形状不在这里"**

```cpp
// Hull bounds are VOLUME-LOCAL; the entity's own origin is where the shape
// sits. No rotation: not one of the 132 player_volumes across the four zm maps
// carries an `angles` key.
```

**⇒ 十层**：
```text
1. **包围盒【是【卷局部**的**】
2. ⇒ **而【实体自己的 `origin` 是【那个形状【坐的地方**】】
3. ⇒ **⚠ 【没有旋转**】
4. ⇒ **（`132` 个 `player_volume` 里【没有一个**带 `angles` 键）**
5. ⇒ **⇒ 所以【一个【无旋转的 AABB/SAT**】
```

### 5.1 ⭐⭐⭐ **"没有旋转：`132` 个里没有一个带 `angles`"**

**✅ 与 §465 的"`SV_MapTriggerTouches` 是一个精确的 SAT"**——**一个前向引用** ✓

**⇒ 三层**：
```text
§465  **触发器【有 `hullCount` 与多个 hull** ⇒ **需要 SAT**
§467  **`player_volume` 【无旋转且 `132/132` 无 `angles`** ⇒ **只需 AABB**
⇒ **⇒ 所以【两个不同的几何问题**】
```

**✅ ⭐⭐⭐ **"两个不同的几何问题"** —— 一个**极精确的对照**。

**⚠ 而"`19` of factory's `32` volumes and all `36` of asylum's"⇒ **`55/68` 是纯盒子**。**⇒ 十二层**：

```text
factory：`19/32` **无 slab** ⇒ **纯盒子**
asylum：`36/36` **全无 slab**
⇒ **⇒ 所以 `55` 个里 `19+36 = 55` 是纯盒子**
⇒ **而 `32 - 19 = 13` 个【有 slab**】
```

**✅ ⭐⭐ **"`13` 个有 slab"** —— 一个**可推导的数**。

### 5.2 而**"一个 hull 没有 slab ⇒ 一个普通盒子"**

```cpp
// Then every slab. A hull with none is a plain box, which is the common
// case: 19 of factory's 32 volumes and all 36 of asylum's.
for (const auto &slab : hull.slabs) { ... }
```

**✅ 与 §465 的"多 hull"**——**一个"多边形 ⇒ 多个凸块**的分解**。

**⇒ 三层**：
```text
一个【凸块**】⇒ **一个 AABB**（`midpoint` ± `halfSize`）
其内部【若干 slab**】⇒ **额外的半空间**（`direction` · `local − midPoint` ≤ `halfSize`）
⇒ **⇒ 所以【一个【凸多面体**的表示**】
```

**✅ ⭐⭐⭐ **"一个凸多面体的表示：一个盒子 + 若干 slab"** —— 一个**标准的表示**。

**⚠ 而"`slab.midPoint` 与 `slab.halfSize`"⇒ **一个"平板"的名字**。**

**⇒ 三层**：
```text
`distance = local · direction`
`|distance - midPoint| <= halfSize`
⇒ **⇒ 所以【一个【沿 `direction` 的带**】
```

**✅ ⭐⭐ **"一个沿方向的带"**。

## 六、`SV_ZmZoneAdjacency` 的"`tolerance` 的容差盒"

```cpp
const auto touches = [tolerance](const Box &a, const Box &b) {
    for (std::size_t axis = 0; axis < 3; ++axis)
        if (a.low[axis] - tolerance > b.high[axis] ||
            b.low[axis] - tolerance > a.high[axis]) return false;
    return true;
};
```

**⇒ 十层**：
```text
1. **一个 AABB 的相交【加 `tolerance`**】
2. ⇒ **`a.low - tol > b.high` ⇒ 分离**
3. ⇒ **或 `b.low - tol > a.high` ⇒ 分离**
4. ⇒ **⇒ 所以【一个"膨胀 `tolerance`"的相交**】
5. ⇒ **⇒ 而【三个轴【全部**通过 ⇒ 相交**
```

**✅ ⭐⭐ **"一个膨胀 tolerance 的相交"** —— 与 §465 的"一个 `tolerance` 的精确 SAT"**同族**（**第二次"`tolerance`**）。

**⇒ 三层**：
```text
§465  **`SV_MapTriggerTouches` 的 `tolerance`**
§467  **`SV_ZmZoneAdjacency` 的 `tolerance`**
⇒ **⇒ 而【两者【都【膨胀**要相交的盒**】
```

**✅ ⭐⭐ **"两者都膨胀要相交的盒"**。

**⚠ 而"`adjacency[left]` 与 `adjacency[right]` 两向都填"⇒ **一个对称的邻接**。**

**⇒ 三层**：
```text
`adjacency[l].push_back(r)` 与 `adjacency[r].push_back(l)`
⇒ **⇒ 所以【一个【无向图**的邻接表**
```

**✅ ⭐⭐ **"无向图的邻接表"** —— 与 §451/§452/§453 的 **navgraph 邻接**同族（**第四次"无向图邻接表**）。

**⇒ 三层**：
```text
§451  **BO1 hybrid 的 `5553` 条边**
§452  **`1970` 条边**
§453  **`1189` 条边**
§467  **`SV_ZmZoneAdjacency` 的 `zones` 级邻接**
⇒ **⇒ 四层图**
```

**✅ ⭐⭐ **"四层图"** —— 一个**分层的空间结构**。

## 七、`SV_SelectInitialSpawn` 的六元回退与"没有它 ⇒ 一把没有武器没有手的枪"

### 7.1 那段

```cpp
// `_so` IS THE SPECIAL-OPS / CAMPAIGN SPAWN AND IT IS THE ONLY ONE A
// COOP LEVEL HAS. Counted in coop_training_mp_cargoship's own decrypted
// zone: worldspawn x1, info_player_start_so x1, trigger_multiple_spawn x2
// -- no `info_player_start`, no mp_*_spawn of any kind. Without it the
// selector returned nullopt and the server logged
// `spawn refused ... NO_SPAWN_POINT`, which reaches the player as a
// loaded map with no weapon and no viewhands.
```

**⇒ 二十层**：
```text
1. **`_so` **是【special-ops / campaign 出生点**】**
2. ⇒ **而它【是【一个 coop 关卡【唯一有的**那个**】**
3. ⇒ **在 `coop_training_mp_cargoship` 自己的【解密 zone**里数到**：
4. ⇒ **`worldspawn` ×1**
5. ⇒ **`info_player_start_so` ×1**
6. ⇒ **`trigger_multiple_spawn` ×2**
7. ⇒ **⇒ 【没有 `info_player_start`**】
8. ⇒ **⇒ 【没有【任何一种 `mp_*_spawn`**】】
9. ⇒ **⇒ 所以【没有它，那个选择器【返回 `nullopt`**】】
10. ⇒ **⇒ 而【服务器【记录 `spawn refused ... NO_SPAWN_POINT`**】】
11. ⇒ **⇒ 而【那【到玩家那里【变成一个【已加载的地图，没有武器，也没有 viewhands**】】】
```

### 7.2 ⭐⭐⭐ **"一个已加载的地图，没有武器，也没有 viewhands"**

**✅ 这是本报告里**最重要的一条"一个拒绝的**玩家可见**后果**。**

**✅ 与 §465 的"`NO_SPAWN_POINT` 的日志"**——**一个具体症状的确定性** ✓

**⇒ 三层**：
```text
服务器侧：**`spawn refused ... NO_SPAWN_POINT`**（**一行日志**）
客户端侧：**一个加载了的地图 + 没有武器 + 没有手**
⇒ **⇒ 所以【一行日志【对应【一个可见的崩坏**】
```

**✅ ⭐⭐⭐ **"一行日志对应一个可见的崩坏"**。</br>

**✅ 与 §463 的"日志里的那个数就是密码文"**同族（**第二次"日志与可见症状的一个精确映射**）。

**⇒ 三层**：
```text
§463  **`otherFlags=1461489901` ⇒ 没有快照到达客户端**
§467  **`NO_SPAWN_POINT` ⇒ 没有武器也没有手**
⇒ **⇒ 两次"一个日志行【解释**一个可见症状**】
```

**✅ ⭐⭐ **"一个日志行解释一个可见症状"两例**。

### 7.3 而**"`mp_<gametype>_spawn` 形式【对大多数 token 不存在**"**

```cpp
// THE `mp_<gametype>_spawn` FORM DOES NOT EXIST FOR MOST TOKENS. Counted in
// mp_deathmarch_chap1's own decrypted zone: mp_dm_spawn, mp_tdm_spawn,
// mp_tdm_spawn_allies_start, mp_tdm_spawn_axis_start, worldspawn -- and no
// mp_zhunt_spawn, no info_player_start of either kind.
```

**⇒ 十二层**：
```text
1. **一个 `mp_<gametype>_spawn` **的【形式**】
2. ⇒ **对大多数 token 【不存在**】**
3. ⇒ **`mp_deathmarch_chap1` 自己的 zone 里**：
4. ⇒ **`mp_dm_spawn`**
5. ⇒ **`mp_tdm_spawn`**
6. ⇒ **`mp_tdm_spawn_allies_start`**
7. ⇒ **`mp_tdm_spawn_axis_start`**
8. ⇒ **`worldspawn`**
9. ⇒ **⇒ 【没有 `mp_zhunt_spawn`**】
10. ⇒ **⇒ 【没有【任何一种 `info_player_start`**】】
```

**✅ ⭐⭐⭐ **"没有 `mp_zhunt_spawn`，也没有任何一种 `info_player_start`"** —— 一个**极重要的发现**。

**✅ 与 §466 的"`Skipped` 五个"**——**一个同族的"枚举不可靠"的教训** ✓

**⇒ 三层**：
```text
§466  **`<map>_const.ff` 的编号【不可从实体列表恢复**】
§467  **`mp_<gametype>_spawn` 【不可假设存在**】
⇒ **⇒ 两次"枚举的假设【必须【用测量**修正**】
```

**✅ ⭐⭐ **"枚举的假设必须用测量修正"两例**。

### 7.4 而**六元回退表**

```cpp
const std::array<std::string, 6> classNames{
    "mp_" + gameType + "_spawn_attacker",
    "mp_" + gameType + "_spawn",
    "info_player_start",
    "info_player_start_so",
    "mp_dm_spawn",
    "mp_tdm_spawn",
};
```

**⇒ 十层**：
```text
1. **两个【动态**的（`mp_<gt>_spawn_attacker` / `mp_<gt>_spawn`）**
2. ⇒ **两个【固定**的（`info_player_start` / `info_player_start_so`）**
3. ⇒ **两个【兜底**的（`mp_dm_spawn` / `mp_tdm_spawn`）**
4. ⇒ **⇒ 所以【三层：模式特定 / 单人 / 通用**】
5. ⇒ **⇒ 而【按顺序**试**
```

**✅ ⭐⭐⭐ **"三层：模式特定 / 单人 / 通用"** —— 一个**极清晰的回退阶梯**。

**⚠ 而"`mp_dm_spawn` 与 `mp_tdm_spawn` 【每一个 MP 派生地图都带**"⇒ **"不管它被当哪个模式玩**"**。

**⇒ 三层**：
```text
注释：**"每一个 MP 派生地图都带，不管它被当哪个模式玩"**
⇒ **⇒ 所以【最后两道【几乎总是成功**】
```

**✅ ⭐⭐ **"最后两道几乎总是成功"**。

## 八、`SV_SelectModeSpawnPoints` 的"asset gametype 与 rules gametype 不是一回事"

```cpp
// THE ASSET GAMETYPE AND THE RULES GAMETYPE ARE NOT THE SAME THING
// (section 152n). The token picks which FASTFILES load and must match what
// the client's playlist loaded, or the level checksum rejects the
// join. The RULES come from gametypes/<token>.lua, and dmz and zm
// are both served with a COPY of dm.lua -- so for spawning they are
// deathmatch and draw from the same pool.
```

**⇒ 二十四层**：
```text
1. **asset gametype 与 rules gametype 【不是一回事**】
2. ⇒ **那个 token 【选【哪些 fastfile 加载**】】
3. ⇒ **⇒ 而【必须【匹配【客户端的 playlist 加载了什么**】】】
4. ⇒ **⇒ 否则【那个关卡校验和【拒绝那个 join**】】
5. ⇒ **而【那个 rules 【来自 `gametypes/<token>.lua`**】】
6. ⇒ **⇒ 而【`dmz` 与 `zm` 【两个都用【`dm.lua` 的一个副本**】】
7. ⇒ **⇒ 所以【对出生**它们【是 deathmatch 且【从同一个池**里取】
```

### 8.1 ⭐⭐⭐ **"asset gametype 与 rules gametype 不是一回事"**

**✅ 与 §466 的"asset 与 rules"**——**一个更强的版本** ✓

**⇒ 三层**：
```text
asset token ⇒ **fastfile 的** ⇒ **关卡校验和** ⇒ **join 被拒**
rules token ⇒ **`gametypes/<token>.lua`** ⇒ **出生池**
⇒ **⇒ 所以【两个 token 【必须【分别**正确**】
```

**✅ ⭐⭐⭐ **"两个 token 必须分别正确"**。</br>

**✅ 而"`dmz` 与 `zm` 都用 `dm.lua`"⇒ **一个具体的实例**。**⇒ 十层**：

```text
`dmz` ⇒ **`dm.lua`**
`zm` ⇒ **`dm.lua`**
⇒ **⇒ 所以【两个 token 【在 rules 上【等价**】
```

**✅ ⭐⭐ **"两个 token 在 rules 上等价"**。

### 8.2 而**"`mp_battlecity` 上 `mp_dm_spawn` ×18 与 `mp_tdm_spawn` ×18"**

```cpp
// Measured on mp_battlecity: the map carries mp_dm_spawn x18 and
// mp_tdm_spawn x18, this chain did not match "dmz", the selector fell
// through to SV_SelectInitialSpawn and logged "selected 1 from
// info_player_start", and the player spawned UNDER the map.
```

**⇒ 十四层**：
```text
1. **`mp_battlecity` 带 `mp_dm_spawn` ×18 与 `mp_tdm_spawn` ×18**
2. ⇒ **⇒ 所以【整整 `36` 个出生点**
3. ⇒ **⚠ 而这个链【没有匹配 `"dmz"`**】
4. ⇒ **⇒ 所以【那个选择器【落穿到 `SV_SelectInitialSpawn`**】】
5. ⇒ **⇒ 而【记录 `selected 1 from info_player_start`**】**
6. ⇒ **⇒ 而【那个玩家【在【地图下面**出生】
```

**✅ ⭐⭐⭐ **"那个玩家在地图下面出生"** —— 一个**极严重的可见症状**。

**✅ 与 §7.2 的"没有武器也没有手"**——**两个同族的"一个选择失败 ⇒ 一个可见的崩坏"**。

**⇒ 十二层**：
```text
§7.2  **`NO_SPAWN_POINT` ⇒ 没有武器没有手**
§8.2  **`selected 1 from info_player_start` ⇒ 在地图下面**
⇒ **⇒ 所以【一个"回落**"【比一个"失败**"【更危险**】
```

**✅ ⭐⭐⭐ **"一个回落比一个失败更危险"** —— 本报告的一条**极重要的判据**。

**⚠ 而"`info_player_start` 在地图下面"⇒ **一个"单人生成点【在地图外**"**。

**⇒ 三层**：
```text
`info_player_start` ⇒ **一个单人的**起点 ⇒ **在一个 MP 地图里【可能【被放在【几何体之外**】
`mp_dm_spawn` ⇒ **一个多人的，`18` 个，全部在几何体里**
⇒ **⇒ 所以【回落【选到了一个【结构上有害**的点**
```

**✅ ⭐⭐⭐ **"回落选到了一个结构上有害的点"** —— 一个**极精确的因果**。

### 8.3 而**"列出它们是【把一个单点的回落【变成整个集合**"的东西**"**

```cpp
// Listing them here is what turns a single fallback point into the
// whole set.
```

**✅ 与 §7.4 的"六元回退表"**——**一个修正** ✓

**⇒ 三层**：
```text
修正前：`"dmz"` 不在列表 ⇒ **回落到 `SV_SelectInitialSpawn`** ⇒ **1 个点**
修正后：`"dmz"` 在列表 ⇒ **`mp_dm_spawn` 的整个集合** ⇒ **18 个点**
⇒ **⇒ 所以【一行【加一个 token**】】
```

**✅ ⭐⭐⭐ **"一行加一个 token"** —— 一个**极小的修改，极大的效果**。

## 九、`SV_SelectLogicalMapEntities` 的七类与"零是一个合法序号"

```cpp
const auto isLogicalClass = [](const std::string_view className) {
    return className.starts_with("actor_") ||
        className.starts_with("trigger_") ||
        className.starts_with("script_vehicle_") ||
        className == "info_volume" ||
        className == "script_struct" ||
        className == "script_origin" ||
        className == "info_player_start_so";
};
```

**⇒ 十二层**：
```text
1. **三个前缀**（`actor_` / `trigger_` / `script_vehicle_`）
2. ⇒ **四个精确**（`info_volume` / `script_struct` / `script_origin` / `info_player_start_so`）
3. ⇒ **⇒ 所以【七种**】
4. ⇒ **⇒ 而【`mapOrdinal = ordinal`**（**不是 `ordinal - 1`**）**
```

### 9.1 ⭐⭐⭐ **`mapOrdinal = ordinal` 而 §466 的 `mapOrdinal = ordinal - 1`**

**✅ 与 §466 的"`ordinal - 1` 的两个类共享一个轴"**——**一个精确的对照** ✓

**⇒ 三层**：
```text
§466  **`SV_SelectBrushModelSpawns` ⇒ `mapOrdinal = ordinal - 1`**（**`ordinal` 从 `1` 起**）
§467  **`SV_SelectLogicalMapEntities` ⇒ `mapOrdinal = ordinal`**（**`ordinal` 是循环下标，从 `0` 起**）
⇒ **⇒ 所以【两者【都是【地图实体列表里的位置**】
```

**✅ ⭐⭐⭐ **"两者都是地图实体列表里的位置"** —— **一个一以贯之的语义，两种编号起点**。

**⚠ 而"`script_origin` 在 `isLogicalClass` 里而在 `Skipped` 里**"⇒ **一个精确的分工**。**

**⇒ 三层**：
```text
`Skipped`（§466）⇒ **关于【服务器实体号**】（**`script_origin` 不在其中，它消耗一个号**）
`isLogicalClass`（§467）⇒ **关于【逻辑实体定义**】（**`script_origin` 在其中**）
⇒ **⇒ 所以【两个列表【不是同一件事**】
```

**✅ ⭐⭐⭐ **"两个列表不是同一件事"** —— 本报告的**一条极重要的辨明**。

### 9.2 而**"一个解析失败 ⇒ 整个选择失败"**

```cpp
if (const auto originText = entity.value("origin")) {
    const auto origin = parseVector(*originText);
    if (!origin) return std::nullopt;
    ...
}
```

**⇒ 六层**：
```text
1. **一个实体的 `origin` 解析失败 ⇒ 【整个 `SV_SelectLogicalMapEntities` 返回 `nullopt`**】
2. ⇒ **⇒ 而【不是一个"跳过这个实体**"**
3. ⇒ **⇒ 所以【一个坏实体【毁掉整个地图的加载**】
```

**✅ 与 §466 的"`bombzone` 不足两个 ⇒ 拒绝"**同族（**第十次"全或无**）。

**⚠ 而这是一个**值得质疑的选择**：一个坏实体是否应该毁掉整个加载？**

**⇒ 三层**：
```text
对：**一个坏实体【意味着那个实体串【不可信**】⇒ **整个加载【应当失败**】
错：**一个坏实体【可能只是一个无关的** `script_origin` ⇒ **毁掉整个地图【过度**】
⇒ **⇒ 所以【这是一个【保守**的选择**
```

**✅ ⭐⭐ **"一个保守的选择"** —— 标注为可质疑。

## 十、`SV_SelectTopPlayersCamera` 与 `Places` 的"按 targetname 而不是 classname"

```cpp
// Matched on TARGETNAME, not classname: the classname is
// `script_struct`, which mp_cross_fire alone carries 89 of. The
// targetname is unique on both maps checked.
```

**⇒ 十层**：
```text
1. **`script_struct` 【单独 `mp_cross_fire` 就有 `89` 个**】
2. ⇒ **⇒ 所以【classname 【不可用于区分**】
3. ⇒ **而 `top_players_camera` 【在两份被检查的地图上【唯一**】
4. ⇒ **⇒ 所以【按 `targetname`**】
```

**✅ ⭐⭐⭐ **"`script_struct` 单独一张图就有 89 个"** —— 一个**极精确的数**。

**⚠ 而 §466 的"三个 `pfNNN` 前缀 = 24 个障碍"** vs 这里的"89 个 `script_struct`"**⇒ 一个对照**。

**⇒ 三层**：
```text
`script_struct` ⇒ **一个【极常用的容器类**】（`89` / 一张图）
⇒ **⇒ 所以【它的 `targetname` 【承载了全部的语义**】
```

**✅ ⭐⭐ **"它的 targetname 承载了全部语义"**。

### 10.1 而**"`script_index` 按字符串比较而不解析"**

```cpp
// script_index is "0"/"1"/"2" in every map checked, so compare the string
// rather than parse it -- there is no third form to be liberal about, and
// a silent parse failure here would put third place on the winner's plinth.
```

**⇒ 十层**：
```text
1. **`"0"`/`"1"`/`"2"` 【每一份被检查的地图都是这样**】
2. ⇒ **⇒ 所以【按字符串比较**而不解析**】
3. ⇒ **因为【没有第三种形式【可以宽容**】】
4. ⇒ **⇒ 而【一个静默的解析失败【会把第三名【放上冠军的台座**】】
```

**✅ ⭐⭐⭐ **"一个静默的解析失败会把第三名放上冠军的台座"** —— 一个**极精确的症状**。

**✅ 与 §463 的"一个夹会把那个 bug 藏在 slot 14 的弹药里"**同族（**第二次"一个宽容掩盖一个 bug**）。

**⇒ 三层**：
```text
§463  **夹 `slot 20 ⇒ 14`** ⇒ **bug 隐藏**
§467  **解析 `"3"` ⇒ 静默 0** ⇒ **第三名上冠军台**
⇒ **⇒ 两次"宽容是掩盖**】
```

**✅ ⭐⭐ **"宽容是掩盖"两例**。

### 10.2 而**"在第一个空隙处停止而不把它补上"**

```cpp
// Stop at the first gap rather than closing it up: place 2 standing where
// place 1 should be is a wrong podium, and an empty one is not.
```

**⇒ 八层**：
```text
1. **第一处空隙【就停**】
2. ⇒ **而不【把它【补上**】】
3. ⇒ **因为【第二名站在第一名该在的地方【是一个【错的台座**】】】
4. ⇒ **⇒ 而【一个空的台座【不是**】
```

**✅ ⭐⭐⭐ **"一个空的台座不是错的台座"** —— 与 §2.4 的"缺席优于默认"**同族**（**第四次"缺席优于错误**）。

**⇒ 三层**：
```text
§464  **`slot 20` 静默**
§467  **`goal` 缺席**
§467  **台座在第一处空隙停**
⇒ **⇒ 三次"缺席 > 错误**】
```

**✅ ⭐⭐ **"缺席 > 错误"三例表**。

## 十一、`SV_SelectFactoryArrivalSpawns` 的 `4` 个与 `script_int` 的 `'1'..'4'`

```cpp
if (entity.value("targetname") != "initial_spawn_points") continue;
const auto id = entity.value("script_int");
...
if (!spawn || !entity.value("angles") || !id || id->size()!=1 ||
    (*id)[0]<'1' || (*id)[0]>'4') return std::nullopt;
...
if (result.size()!=4) return std::nullopt;
```

**⇒ 十二层**：
```text
1. **`targetname == "initial_spawn_points"`**
2. ⇒ **`script_int` 【必须是一个字符**】
3. ⇒ **⇒ 而【它【必须是 `'1'`..`'4'`**】
4. ⇒ **⇒ 而【`angles` 【必须存在**】
5. ⇒ **⇒ 而【重复的 id ⇒ 拒绝**】
6. ⇒ **⇒ 而【`result.size() != 4` ⇒ 拒绝**】
7. ⇒ **⇒ 所以【一个【精确的四**】
```

**✅ 与 §466 的"`bombzone` 恰好两个"**——**完全同族**（**第十一次"全或无**）。

**⚠ 而 `CODREF(factory-arrival)` 说【`MapEnts` 记录 `81..84` 命名那四个**"。**

**⇒ 三层**：
```text
`MapEnts` 记录 `81..84` ⇒ **四条**
而【`script_int` 是 `'1'..'4'`
⇒ **⇒ 所以【两套**编号**
```

**✅ ⭐⭐ **"两套编号"**。

**⚠ 而"`OLMOD(factory-arrival-selection)`：保留地图顺序；多人槽位的分配是【重建的，不是恢复的**原始服务器脚本**"。**

**⇒ 三层**：
```text
`CODREF` ⇒ **偏移与几何【从 retail 字节**】
`OLMOD` ⇒ **槽位分配【是重建的**】
⇒ **⇒ 所以【一个【混合**的来源**
```

**✅ ⭐⭐⭐ **"一个混合的来源：偏移从 retail、分配是重建"** —— 一个**诚实的标注**。</br>

**✅ 与 §451 的"BO1 Der Riese 是一个捐赠参照，不是恢复的 CODOL aipaths"**同族（**第四次"混合来源的诚实标注**）。

**⇒ 三层**：
```text
§451  **aipaths ⇒ 捐赠**
§467  **槽位分配 ⇒ 重建**
§467  **几何 ⇒ retail 字节**
⇒ **⇒ 三次分层标注**
```

**✅ ⭐⭐ **"分层标注"三例**。

## 十二、`SV_SelectTopPlayersPlaces` 的 `byPlace[place]` 已存在 ⇒ 跳过

```cpp
if (byPlace[place]) continue;
byPlace[place] = spawnFromEntity(entity, "script_struct");
```

**⇒ 六层**：
```text
1. **第一个**占据一个台座
2. ⇒ **后面的【同 place ⇒ 跳过**】
3. ⇒ **⇒ 所以【第一个胜**】
```

**✅ ⭐⭐ **"第一个胜"** —— 与 §466 的"重复 label ⇒ 拒绝"**相反**（**那里**拒绝**，这里**取第一个**）。

**⇒ 三层**：
```text
§466  **`bombzone` 重复 label ⇒ `nullopt`**（**重复是矛盾**）
§467  **`top_players_loc` 重复 place ⇒ 取第一个**（**重复是冗余**）
⇒ **⇒ 所以【同名【可以有不同含义**】
```

**✅ ⭐⭐⭐ **"同名可以有不同含义"** —— 一个**极精确的分类**。

## 十三、`EntityTextParser::quotedString` 的两字符转义

```cpp
if (character == '\\' && cursor_ < text_.size() &&
    (text_[cursor_] == '\\' || text_[cursor_] == '"'))
    value.push_back(text_[cursor_++]);
else
    value.push_back(character);
```

**⇒ 十层**：
```text
1. **只转义 `\\` 与 `\"` 两种**】
2. ⇒ **⇒ 而【其余的反斜杠【原样保留**】
3. ⇒ **⇒ 所以【`\n` 【是【两个字**】】
4. ⇒ **⇒ 而【不是**一个换行**
```

**✅ ⭐⭐⭐ **"`\n` 是两个字而不是一个换行"** —— 一个**极重要的解析决定**。

**✅ 与 §465 的"`\x14`/`\x15` 分隔符"**——**一个对照** ✓

**⇒ 三层**：
```text
§465  **提示规则【用 `\x14`/`\x15` 分隔符**】
§467  **实体串【只转义 `\\` 与 `\"`**】
⇒ **⇒ 所以【两个解析器【各有各的转义规则**】
```

**✅ ⭐⭐ **"两个解析器各有各的转义规则"**。

**⚠ 而"`value_` 的最后一次【胜**"**（`fields.rbegin()`）。

**⇒ 三层**：
```text
`SvMapEntity::value` 【从 `rbegin()` 往前找** ⇒ **最后一个同名键【胜**】
⇒ **⇒ 所以【一个实体串里【重复的键【取【最后一次**】
```

**✅ ⭐⭐⭐ **"最后一个同名键胜"** —— 与 `byPlace` 的"第一个胜"**相反**。

**⇒ 三层**：
```text
键内重复 ⇒ **最后一次胜**（**`rbegin()`**）
实体间重复 ⇒ **第一次胜**（**`if (byPlace[place]) continue`**）
⇒ **⇒ 两个相反的取胜规则**
```

**✅ ⭐⭐ **"两个相反的取胜规则"** —— 一个**值得注意的不一致**。

## 十四、`parseVector` 的"必须恰好三个且恰好用尽"

```cpp
while (cursor < end && *cursor == ' ') ++cursor;
const auto parsed = std::from_chars(cursor, end, value);
if (parsed.ec != std::errc{} || parsed.ptr == cursor || !std::isfinite(value))
    return std::nullopt;
cursor = parsed.ptr;
...
while (cursor < end && *cursor == ' ') ++cursor;
return cursor == end ? std::optional{ result } : std::nullopt;
```

**⇒ 十二层**：
```text
1. **三次循环**（`for (auto &value : result)`）**
2. ⇒ **每次【跳过空格**】**
3. ⇒ **⇒ 解析一个 `float`**
4. ⇒ **⇒ 若失败 / 无进展 / 非有限 ⇒ 拒绝**】
5. ⇒ **⇒ 最后【跳过尾随空格**】
6. ⇒ **⇒ 而【`cursor == end` 才接受**】
7. ⇒ **⇒ 所以【恰好三个且【恰好用尽**】
```

### 14.1 ⭐⭐⭐ **"`!std::isfinite` ⇒ 拒绝"**

**✅ 与 §444 的"`setLoot` 接受 `double` 或 `int64_t`"**——**一个对照** ✓

**⇒ 三层**：
```text
`parseVector` ⇒ **拒绝 NaN/Inf**
而【`std::from_chars` 对 `"nan"` 【会成功**】⇒ **所以【那个 `isfinite` 是【必须的**】
⇒ **⇒ 所以【一个【显式**的有限性检查**
```

**✅ ⭐⭐⭐ **"`from_chars` 对 `nan` 会成功，所以那个 `isfinite` 是必须的"** —— 一个**极精确的防御**。

**⚠ 而 `parsed.ptr == cursor` ⇒ **"无进展**"的检查**。**

**⇒ 三层**：
```text
`from_chars` 对【空输入**】⇒ **`ec == invalid_argument`**（**不是 `ptr == cursor`**）
而【`ptr == cursor` 是【一个额外的**防御**
⇒ **⇒ 所以【两道**
```

**✅ ⭐⭐ **"两道防御"**。

### 14.2 而**`parseBrushModel` / `parseTriggerModel` 的 `*` vs `?`**

```cpp
if (text.size() < 2 || text.front() != '*') return std::nullopt;  // brush
if (text.size() < 2 || text.front() != '?') return std::nullopt;  // trigger
...
result == 0 || result > std::numeric_limits<std::uint16_t>::max()
```

**⇒ 十二层**：
```text
1. **`*N` ⇒ brush model**（**相对某个基线**）
2. ⇒ **`?N` ⇒ trigger model**（**相对某个基线**）
3. ⇒ **⇒ 两者【各自的名字空间**】（**§465**）**
4. ⇒ **⇒ 而【两个解析器【结构完全一样**】
5. ⇒ **⇒ 所以【一个宏 / 一个模板【可以合并**】
```

**✅ 与 §465 的"`?N` 是它自己的名字空间"**完全闭合 ✓

**⇒ 三层**：
```text
§465  **`?N` 与 `*N` 是两个独立的**名字空间**
§467  **`parseBrushModel`（`*`）与 `parseTriggerModel`（`?`）【结构完全一样**】
⇒ **⇒ 所以【两次同样的解析**】
```

**✅ ⭐⭐ **"两次同样的解析"**。

**⚠ 而 `result > 0xFFFF` ⇒ **拒绝**。**

**⇒ 三层**：
```text
`uint16_t` ⇒ **`0..65535`**
⇒ **⇒ 所以【`65536` 个 brush 或 trigger 的上限**】
```

**✅ ⭐⭐ **"`65536` 个上限"** —— 与 §414 的"brush 索引用 `uint16`"**一致**。

## 十五、`regularMultiplayerEligibility` 的"`script_specialops` 的三态"

```cpp
if (const auto specialOps = entity.value("script_specialops")) {
    if (*specialOps == "1") eligible = false;
    else if (*specialOps != "0") return std::nullopt;
}
if (entity.value("script_specialopsname")) eligible = false;
```

**⇒ 十二层**：
```text
1. **缺失** ⇒ **eligible = true**
2. ⇒ **`"0"`** ⇒ **eligible = true**
3. ⇒ **`"1"`** ⇒ **eligible = false**
4. ⇒ **其它** ⇒ **`nullopt`**
5. ⇒ **⇒ 而【`script_specialopsname` 【存在 ⇒ `eligible = false`**】
6. ⇒ **⇒ 所以【一个【三态** + 一个【名字的存在性**】
```

### 15.1 ⭐⭐⭐ **"`"1"` ⇒ 不合格，`"0"` 或缺失 ⇒ 合格，其它 ⇒ 拒绝"**

**✅ 与 §466 的 `SV_SelectSdBombSites` 的第 ⑤ 道**完全一致 ✓

**⇒ 三层**：
```text
§466  **`script_specialops` 不存在或 `"0"`**（**`bombzone` 的第 ⑤ 道**）
§467  **`regularMultiplayerEligibility` 的同一个三态**（**被 `brushModelFromEntity`/`scriptModelFromEntity`/`SV_SelectSdBombPickup` 调用**）
⇒ **⇒ 所以【一个【共享**的判据**
```

**✅ ⭐⭐⭐ **"一个共享的判据"** —— 而 `SV_SelectSdBombPickup` 的 `visual` 检查**也调用它**（line 961）。

**⚠ 而 `script_specialopsname` 的【存在 ⇒ 不合格**"**⇒ **一个额外的标志**。

**⇒ 三层**：
```text
`script_specialops == "1"` ⇒ **一个数值**
`script_specialopsname` 存在 ⇒ **一个名字**
⇒ **⇒ 两个条件【任一 ⇒ 不合格**】
```

**✅ ⭐⭐ **"两个条件任一 ⇒ 不合格"**。

## 十六、关键结论

1. **⭐⭐⭐ 一个 `goal` 是一个『名字』而不是一个『目的地』**：**`zm_factory_sh` 上 `69` 个 `zombie_spawner` 里的 `61` 个带 `target`，全部 `61` 个解析，每一个都解析到一个 `node_pathnode`（`159..738` 单位远），那是零售的 pathing 数据**；**旧注释叫它"零售的导航目标"，但第一个 factory 出生点读作 `outside_up_spawners`——一个 spawner 组** ⇒ **"它必须被解析，绝不能被信任为一个目的地"`**。
2. **⭐⭐⭐ "一个未解析的目标保持缺席，不取默认：一个没有目标的僵尸必须站着不动，而不走 `(0,0,0)`"`** —— 与 §463 同族，**"缺席让症状可见"`**。
3. **⭐⭐⭐ 目标解析必须是【两趟】，因为一个生成器可以指向一个在实体列表里更后面出现的节点** —— 一个**顺序无关性**要求（与 §466 的顺序**依赖**对照）。
4. **⭐⭐⭐ `pfNNN` 前缀是连接板和遍历的【全部**的键**（`pf678_auto1` vs `pf678_auto2108` 只在第一个下划线之后不同）⇒ **"`24` 个 `pfNNN` 前缀就是 §454 的 `24` 个障碍"`**。
5. **⭐⭐⭐ "`script_noteworthy` 是 `1..6` 的槽，而没有它的板仍然算一块板 ⇒ 索引 `0` 记录『无槽』而不是丢弃它并改变那个计数"`** —— 一个精确的计数保护（与 §466 的"缺失即失败"**相反**：由用途决定）。
6. **⭐⭐⭐ `SV_SelectZmZones` 的"两个卷声称一个区名但指向不同组是矛盾，不是一个可以糊过去的合并"`**；而 **"全 `35` 个区每一个至少两个出生点，所以一个空区意味着那个组名没有解析"** ⇒ **"拒绝比静默好"`** —— 第三次"不可用即暴露"。
7. **⭐⭐⭐ `SV_ZmVolumeContains` 的"包围盒是【卷局部】的，而实体的 `origin` 是形状坐的地方；没有旋转——`132` 个 `player_volume` 里没有一个带 `angles` 键"`** —— 与 §465 需 SAT 的触发器**两个不同的几何问题**；`factory` `19/32` + `asylum` `36/36` = **`55`** 个纯盒子，**`13`** 个有 slab。
8. **⭐⭐⭐ `SV_SelectInitialSpawn` 的 `_so` 是 COOP 关卡【唯一有的】出生点（`coop_training_mp_cargoship`：`worldspawn` ×1 / `info_player_start_so` ×1 / `trigger_multiple_spawn` ×2，没有 `info_player_start`、没有任何 `mp_*_spawn`）⇒ 没有它 ⇒ `spawn refused ... NO_SPAWN_POINT` ⇒ 【一个已加载的地图，没有武器，也没有 viewhands】"`**。
9. **⭐⭐⭐ "`mp_<gametype>_spawn` 形式对大多数 token **不存在**：`mp_deathmarch_chap1` 只有 `mp_dm_spawn`/`mp_tdm_spawn`/两个 `_start`/`worldspawn`，没有 `mp_zhunt_spawn`、没有任何一种 `info_player_start`"`** ⇒ 六元回退表（两个动态 / 两个单人 / 两个兜底）**三层阶梯**。
10. **⭐⭐⭐ "asset gametype 与 rules gametype 不是一回事：token 选哪些 fastfile 加载且必须匹配客户端的 playlist，否则关卡校验和拒绝 join；而 rules 来自 `gametypes/<token>.lua`，`dmz` 与 `zm` 都用 `dm.lua` 的一个副本"`**；而 **`mp_battlecity` 的"`mp_dm_spawn` ×18 + `mp_tdm_spawn` ×18，这个链没匹配 `"dmz"`，落穿到 `SV_SelectInitialSpawn`，记录 `selected 1 from info_player_start`，玩家在地图下面出生"` ⇒ **"一个回落比一个失败更危险"`** —— 本报告最重的判据；修正就是**"一行加一个 token 把一个单点变成整个集合"`**。
11. **⭐⭐⭐ `SV_SelectLogicalMapEntities` 的 `mapOrdinal = ordinal`（从 `0`）vs §466 的 `mapOrdinal = ordinal - 1`（从 `1`）** —— **两者都是"地图实体列表里的位置"，两种编号起点**；而 **`Skipped`（关于服务器实体号）与 `isLogicalClass`（关于逻辑实体定义）【不是同一件事】**（`script_origin` 在前者之外、在后者之内）。
12. **⭐⭐⭐ `script_struct` 单独 `mp_cross_fire` 就有 `89` 个** ⇒ 摄像机与台座必须按 `targetname` 匹配；而 **`script_index` 按字符串比较而不解析** —— **"一个静默的解析失败会把第三名放上冠军的台座"`** —— 第二次"宽容是掩盖"。
13. **⭐⭐⭐ "在第一个空隙处停止而不把它补上：第二名站在第一名该在的地方是一个错的台座，而一个空的台座不是"`** —— 第四次"缺席优于错误"。
14. **⭐⭐ `EntityTextParser::quotedString` 只转义 `\\` 与 `\"` 两种** ⇒ **`\n` 是两个字而不是一个换行**（与 §465 的 `\x14`/`\x15` 分割规则**两个各异的解析器**）；而 **`SvMapEntity::value` 从 `rbegin()` 找 ⇒ 键内重复【最后一次胜】**，而 **`byPlace[place]` ⇒ 实体间重复【第一次胜**】** —— **两个相反的取胜规则**（一个值得注意的不一致）。
15. **⭐⭐ `parseVector` 的"恰好三个且恰好用尽"**，而 **`!std::isfinite` 是【必须的】，因为 `from_chars` 对 `"nan"` 会成功** —— 一个极精确的防御。
16. **⭐⭐ `parseBrushModel`（`*`）与 `parseTriggerModel`（`?`）结构完全一样**（`result == 0 || result > 0xFFFF` ⇒ 拒绝）—— 与 §465 的"两个名字空间"**完全闭合**，而 **`0xFFFF` = `65536` 个的上限**。
17. **⭐⭐ `regularMultiplayerEligibility` 的三态**（`"1"` ⇒ 不合格 / `"0"` 或缺失 ⇒ 合格 / 其它 ⇒ `nullopt`）+ `script_specialopsname` 存在 ⇒ 不合格 —— 与 §466 的 `bombzone` 第 ⑤ 道**完全一致**，是一个**被三处共享**的判据。

## 十七、`sv_mapents_mp.cpp` 全文件总览

**行数：`1,415`**（`1,416` 含末尾空行）。

**`30` 个函数**（按行号）：
```text
 26  parse                            (EntityTextParser)
 58  skipWhitespace
 72  quotedString
 99  parseVector
120  parsePositiveFloat
134  spawnFromEntity
169  parseBrushModel
185  parseTriggerModel
203  entityAngles
216  regularMultiplayerEligibility
232  brushModelFromEntity
263  scriptModelFromEntity
305  SvMapEntity::value
315  SvLogicalMapEntityDefinition::value
326  SV_ParseMapEntities
332  SV_SelectLogicalMapEntities
376  SV_SelectTopPlayersCamera
393  SV_SelectTopPlayersPlaces
434  SV_SelectInitialSpawn
479  SV_SelectConnectionSpawn
500  SV_SelectFactoryArrivalSpawns
521  SV_SelectModeSpawnPoints
592  SV_SpawnClassNameCensus
618  SV_AssignMapEntityNumbers
650  SV_SelectBrushModelSpawns
674  SV_SelectScriptModelSpawns
697  SV_SelectMiniMapCorners
805  SV_SelectSdBombSites
919  SV_SelectSdBombPickup
996  SV_SelectZmBarriers
1122 SV_SelectZmZones
1290 SV_ZmVolumeContains
1332 SV_ZmZoneAdjacency
1401 SV_ZmZoneAt
```

**两类来源标注**：
```text
CODREF(factory-arrival)          494   "MapEnts 记录81..84 命名那四个"
OLMOD(factory-arrival-selection) 498   "保留地图顺序；多人槽位分配是重建的"
MEASURED, zm_factory_sh          1242  "61 of its 69 zombie_spawner"
```

**八个测量锚点**（全部是"数过才有资格写"）：
```text
  132  player_volumes 跨四个 zm 地图，全部带 targetname + target
   35  个区，每一个至少两个出生点
  216  个组员，每一个都是 script_struct 僵尸生成器
   61/69  factory 的 zombie_spawner 带 target，全部解析
  159..738  目标距离
  19/32  factory 的纯盒子卷
  36/36  asylum 的纯盒子卷
   89   mp_cross_fire 的 script_struct
   15   zm_asylum_sh 的 info_vehicle_node（§466 引用）
```

**四类拒绝**：
```text
nullopt（全或无）        bombzone / factory-arrival / 空区 / 重复 label
nullopt（矛盾）          player_volume 两组同名 / 非僵尸生成器的组员
nullopt（解析失败）      任何 parseVector 失败 / 任何必需键缺失
记录而非拒绝            无槽的板（索引 0）/ 未解析的 goal（缺席）
```

## 十八、未闭合点

- `FirstDynamicServerEntityNum = 37` 的独立验证。
- `SvZmZone` 的 `hullsResolved` 在哪被置真（`SV_ZmVolumeContains` 前置）。
- `SV_SelectConnectionSpawn` 的调用点。
- `sv_forge_publish_mp.cpp`（`57,344` 字节）未读。
