# 301 · **出生点"丢点而不是整图失败"**、`2568 + 1..1023` 的确认、`1148` 是战利品不是近战

## 一、范围

本报告学习 `Appmain.cpp` 6760–6980 行。

## 二、**预热查找**而不发布

```php
// Warm the script-selected Factory appearance lookups during map setup,
// without publishing or changing a configstring. Both names already live
// in this map's model band; this only fills the resolver's validated hints
// so the first live spawn does not perform the 1023-slot scans.
if (request->gameType == "zm")
{
    for (const auto name : {"c_zom_ger_body_blue", "c_zom_ger_head"})
    {
        const auto index = Bindings.resolveModelConfigStringIndex(name);
        logGameServer("zm actor model lookup primed name=" + name +
            (index ? " index=" + N : " -- NOT IN CURRENT MODEL BAND"));
    }
}
```

### 2.1 三层

```text
1. **预热**查找而**不发布也不变更**配置串
2. 两个名字都在这个地图的模型带里
3. ⇒ 只填解析器的**验证过的提示**（§259 的 `modelHints`）⇒ 首次 live spawn 不做 1023 槽扫描
```

**✓ 与 §259 的提示缓存**完全配套**。**

### 2.2 而"NOT IN CURRENT MODEL BAND"的日志

**⇒ 所以预热也**验证**了存在性。**

### 2.3 而两个名字的**族前缀**

```text
c_zom_ger_body_blue
c_zom_ger_head
```

**⇒ 而 §298 用的是 `c_zom_garbageman`/`c_zom_worker`/`c_zom_secunityguard`。**

**⚠ 所以 `c_zom_` 后面是**不同的族**：`ger`、`garbageman`、`worker`、`secunityguard`。**

## 三、`factoryArrivalSpawns` 的**四项**

```cpp
const bool factoryArrivalSpawns = request->gameType == "zm" &&
    request->mapName == "zm_factory_sh" && entryFlag &&
    std::string_view(entryFlag) == "1";
if (factoryArrivalSpawns)
{
    modeSpawns = SV_SelectFactoryArrivalSpawns(*entities);
    if (!modeSpawns) { reportFailure("factory_arrival_spawn_records"); return; }
    logGameServer("Factory arrival uses authored initial_spawn_points; native ground trace follows");
}
```

### 3.1 四项

```text
gameType == zm
mapName == zm_factory_sh
OLMOD_FACTORY_ENTRY 设置
其值 == "1"
```

### 3.2 而"用**作者的** initial_spawn_points，原生地面 trace 跟随"

**⇒ 先取作者点，**然后**跑地面 trace（下面）。**

**✓ 两段串联。**

## 四、**`info_player_start` 缺席时的回退**（本组第二重要）

```php
auto connectionSpawn = SV_SelectConnectionSpawn(*entities);
if (!modeSpawns) { reportFailure("initial_spawn_select"); return; }
if (!connectionSpawn && !modeSpawns->empty())
{
    // Not every CODOL MP map ships an info_player_start - mp_estate_tropical
    // does not, and the search-and-destroy maps that do are the only ones
    // this path had ever been run against. The connection spawn is just
    // where a client is parked before it spawns for real, so any valid
    // point serves; refusing the whole map for want of one classname does not.
    connectionSpawn = modeSpawns->front().spawn;
    logGameServer("no info_player_start in " + mapName + ", parking connections on " + connectionSpawn->className);
}
if (!connectionSpawn) { reportFailure("connection_spawn_select"); return; }
```

### 4.1 四层

```text
1. **不是每张 CODOL MP 地图都出货一个 `info_player_start`** —— `mp_estate_tropical` 就没有
2. 而"有这个"的地图（sd 类）是这条路唯一跑过的
3. 连接出生点只是**客户端在真正 spawn 之前停靠的地方** ⇒ **任何有效点都行**
4. ⇒ 为一个 classname 拒绝整张地图不行
```

### 4.2 而"`mp_estate_tropical` 没有 `info_player_start`"

**⇒ 一个**具体的反例**。**

**⇒ 与 §289 的"指南针与出生列表无关"同族**（第三次"一个 classname 不该决定整图"）。

## 五、**出生点"丢点而不是整图失败"**（本组最重要的一段）

### 5.1 那段完整论证

```php
// A single unusable point used to abort the whole world spawn, so
// free-for-all never spawned anyone: sd ships two small hand-placed
// sets that all pass, while a dm pool is an order of magnitude
// larger and only needs one point over a gap or inside geometry to
// take the entire match down with it.
//
// Drop the point instead. The set is a pool to pick from, not a
// contract that every entry is standable, and requiring all of them
// made the strictest possible reading of it fatal.
```

### 5.2 五层

```text
1. **一个不可用的点过去会中止整个世界 spawn**
2. ⇒ **自由混战从没 spawn 过任何人**
3. 因为 sd 出货两个小的手放集合而**全都通过**
4. 而一个 **dm 池是一个数量级更大**的 ⇒ **只需要一个点在空隙上或几何体内**
5. ⇒ 就能**把整场比赛带下去**
```

### 5.3 而"集合是一个**池**而不是**每个条目都可站立的契约**"

**⇒ 三层**：

```text
1. 集合是**用来挑的池**
2. 不是"每一项都可站立"的契约
3. ⇒ 要求**全部**是对它最严格的读法，而那个读法是**致命的**
```

**✓ 与本文件反复出现的"代价不对称"同族**（第七次）。

### 5.4 而六个拒绝条件

```cpp
if (!trace || trace->fraction >= 1.0f || trace->allSolid ||
    trace->startSolid || !trace->walkable ||
    trace->hitId != CodolGameServer::EntityNumWorld)
{
    ++rejectedSpawns;
    continue;
}
```

```text
① trace 存在
② fraction < 1.0         【必须真的碰到地面】
③ !allSolid
④ !startSolid            【起点不能已在实心内】
⑤ walkable               【法线可站立】
⑥ hitId == EntityNumWorld  【【必须打到世界而不是实体】】
```

**⇒ 六项。**

### 5.5 而 ⑥ 是**关键**

```php
trace->hitId != EntityNumWorld
```

**⇒ 所以"打到世界"而不是"打到某个实体"。**

**⇒ 因为一个出生点如果在地面上站着一个人，trace 会先打到那个人。**

**⇒ 所以必须要求世界。**

**✓ 一个精确的语义。**

### 5.6 而"从不静默"

```php
if (rejectedSpawns)
{
    // Never silently: a pool quietly shrinking to a handful of points is
    // a spawn-camping bug that would present as bad map design.
    logGameServer("spawn points rejected by the ground trace: " + rejected + " of " + total + " map=" + mapName);
}
```

**⇒ 三层**：

```text
1. **从不静默**
2. 一个静默缩到几个点的池是**一个出生营地 bug**
3. ⇒ 而它会**呈现为糟糕的地图设计**
```

**✓ 与 §283/§288 的"从不静默"同族。**

### 5.7 而"ground trace 之后**替换** origin"

```cpp
for (index = 0; index < origin.size(); ++index)
    modeSpawn.spawn.origin[index] += (traceEnd[index] - origin[index]) * trace->fraction;
```

**⇒ 所以 `origin` 被**重写**到地面接触点。**

**✓ 与 §297 的 `start[2] + (end[2]-start[2]) * fraction` 完全同一公式。**

**⇒ 第四次出现那个插值。**

### 5.8 而 `SpawnGroundTraceDistance = 8192.0f`

**⇒ 与 §272 的 `SpawnGroundTraceDistance = 8192.0f` **完全相同** ✓**

**⇒ 而 `StandardBulletRange` 也是 8192。**

## 六、`spawnTeam` 的**三分支**

```cpp
const auto team = [spawnTeam = modeSpawn.team] {
    switch (spawnTeam)
    {
    case SvSpawnTeam::Tf:  return SvTeam::Tf;
    case SvSpawnTeam::Sc:  return SvTeam::Sc;
    case SvSpawnTeam::Any: return SvTeam::None;
    }
    return SvTeam::None;
}();
```

**⇒ 三个 `SvSpawnTeam` → 两个 `SvTeam` + `None`。**

**⇒ 而 `Any` ⇒ `None`** —— 因为"任何队"在 `SvTeam` 里没有对应值。

**✓ 与 §292 的 `gameTypeIsTeamless` 的 `None` 语义一致。**

## 七、**`1148` 是战利品不是近战**（本组第三重要）

### 7.1 那段

```php
// WHAT WEAPON IS EACH INDEX? OLMOD_DUMP_WEAPON_BAND=1.
//
// Retail BattleCity does NOT spawn you empty-handed: the footage shows bare
// hands holding a HAMMER, which is why the hands are drawn at all -- weapon
// index 0 has no viewmodel, so "no weapon" and "no hands" are the same state.
// Finding the melee index means reading the band rather than guessing, and the
// obvious guess was already wrong once: 1148 looked like a melee slot because
// it sat just under the loot values and carried no ammo, but the captured loot
// band lists it at cs 12616, so it is lootable like the rest.
```

### 7.2 五层

```text
1. **零售 BattleCity 不让你空手 spawn** —— 画面显示**裸手拿着一把锤子**
2. ⇒ 这就是为什么手被画出来 —— **武器索引 0 没有 viewmodel ⇒ "没有武器"与"没有手"是同一个状态**
3. 找近战索引意味着**读带而不是猜**
4. 而**那个显然的猜测已经错过一次**：
5. **1148 看起来像一个近战槽**（因为它就在战利品值下面且不带弹药）
6. ⇒ 但**捕获的战利品带把它列在 cs 12616** ⇒ **所以它和其它一样可战利品化**
```

### 7.3 **"武器索引 0 没有 viewmodel ⇒ 没有武器与没有手是同一个状态"**

**⇒ 一个**关键的行为解释**。**

**⇒ 与 §278 的"`weapon.id` 0 是空"一致。**

### 7.4 而 `cs 12616` 与 §287 的 64 槽

**§287**："`{ 12616, 1148 }`"

**⇒ **完全一致** ✓**

**✅ 这是一次**跨报告闭环** —— §287 的 64 槽表里 `12616 → 1148`，而这里说"1148 在 cs 12616 所以可战利品化"。**

**⇒ 所以"看起来像近战"的猜测被**战利品表**推翻。**

### 7.5 而 `OLMOD_DUMP_WEAPON_BAND` 的实现

```cpp
if (dumpWeapons && dumpWeapons[0] == '1')
{
    size_t published{};
    for (uint16 index = 1; index < WeaponConfigStringCount; ++index)
    {
        const auto *const name = Bindings.nativeConfigString(WeaponConfigStringBase + index);
        if (!name || name[0] == '\0') continue;
        ++published;
        logGameServer("weapon band [" + index + "] " + name);
    }
    logGameServer("weapon band total=" + published + " map=" + mapName + " gametype=" + gameType);
}
```

**⇒ 三项**：

```text
逐 index 一行
空串跳过
总数 + map + gametype
```

**⚠ 而这是**1700 行**的日志 —— 与 §299 的"分块不截断"不同。**

**⇒ 但这是**显式开关**（`OLMOD_DUMP_WEAPON_BAND=1`）⇒ 所以用户要求。**

**✓ 与 §299 的"分块"不矛盾（一个是默认日志，一个是显式 dump）。**

### 7.6 而 `dumpWeapons[0] == '1'` 是**第十二种解析**

**⇒ 与 `dumpBand[0] == '1'` 相同。**

## 八、**`2568 + 1..2568 + 1023` 的确认**（本组第四重要）

```php
// WHAT MODELS CAN A SCRIPT ACTUALLY PLACE? OLMOD_DUMP_MODEL_BAND=1.
//
// `spawnmodel` and `setmodelat` both go through
// resolveModelConfigStringIndex, which only accepts a name the map's model
// configstring band ALREADY publishes -- it walks 2568+1 .. 2568+1023 looking
// for an exact string match and returns nullopt otherwise. A loot script
// therefore cannot invent a model name; it has to pick from this list, and
// until it is dumped nobody knows what is on it for a given map.
```

### 8.1 五层

```text
1. `spawnmodel` 与 `setmodelat` **都**走 `resolveModelConfigStringIndex`
2. 而它**只接受这张地图的模型配置串带已经发布的**名字
3. ⇒ 它走 **2568+1 .. 2568+1023** 找一个**精确的字符串匹配**而否则返回 nullopt
4. ⇒ **一个战利品脚本因此不能发明一个模型名**
5. ⇒ 它必须**从这个列表里挑**，而在被 dump 之前**没人知道某张地图上有什么**
```

### 8.2 **`ModelConfigStringBase = 2568` 与 `ModelConfigStringCount = 1024` 确认**

**⇒ 与 §300 的 `cs 2568 + index` **完全一致** ✓**

**⇒ 与 §259 的"up to 1024 configstrings"**完全一致** ✓**

**✅ 三个独立来源确认这组数字。**

### 8.3 而**"战利品脚本不能发明一个模型名"**

**⇒ 与 §292 的"没有名字被发明"、§296 的"没有猜的别名"同族**（第十三次）。**

### 8.4 而 1024 与 §259 的"1023 × 2 = 2046"

**⇒ 所以 `for (index = 1; index < 1024; ++index)` ⇒ **1023 次**。**

**✓ 完全吻合。**

### 8.5 而 2568 与 §296 的 `476` 无冲突

**⇒ `476` 是**动画**配置串索引而 `2568` 是**模型**基址。**

**✓ 不同的带。**

## 九、关键结论

1. **预热查找而不发布** —— 填 §259 的提示缓存，避免首次 spawn 的 1023 槽扫描。
2. **`c_zom_` 后面有多个族**（`ger`/`garbageman`/`worker`/`secunityguard`）。
3. **`factoryArrivalSpawns` 的四项**，且"作者的 initial_spawn_points + 原生地面 trace"。
4. **`mp_estate_tropical` 没有 `info_player_start`** —— 具体的反例。
5. **"连接出生点只是停靠点 ⇒ 任何有效点都行"**。
6. **"一个不可用的点过去会中止整个世界 spawn ⇒ 自由混战从没 spawn 过任何人"**。
7. **"dm 池比 sd 大一个数量级" ⇒ 一个坏点就能毁掉整场**。
8. **"集合是池而不是契约"** —— 最严格的读法是致命的。
9. **六个拒绝条件含 `hitId == EntityNumWorld`** —— 必须打到世界而不是实体。
10. **"从不静默"：一个静默缩小的池是出生营地 bug，会呈现为糟糕的地图设计**。
11. **地面 trace 后替换 origin** —— 与 §297 完全同一插值公式（第四次）。
12. **`SpawnGroundTraceDistance = 8192.0f`** 与 §272 一致。
13. **"武器索引 0 没有 viewmodel ⇒ 没有武器与没有手是同一个状态"**。
14. **`1148` 看起来像近战槽而被 `cs 12616` 推翻** —— 与 §287 的 64 槽表**闭环**。
15. **`OLMOD_DUMP_WEAPON_BAND` 是 1700 行日志但显式开关** —— 与 §299 的分块不矛盾。
16. **`ModelConfigStringBase = 2568`、`Count = 1024`** 由三个独立来源确认。
17. **"一个战利品脚本不能发明一个模型名"** —— 第十三次"不发明"。

## 十、未闭合点

- `mp_estate_tropical` 与其它没有 `info_player_start` 的地图。
- `1148` 的真实身份（战利品但具体是什么武器）。
- 战利品脚本如何使用这些模型名。
- `Appmain.cpp` 6980 行之后未读取。
