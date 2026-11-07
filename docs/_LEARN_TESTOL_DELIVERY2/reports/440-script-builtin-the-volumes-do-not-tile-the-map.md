# 440 · **"这些体积不铺满地图，所以在这里失败会让脚本把『无处』当成一个故障"** —— `zmPlayerCount` 的 `snapshot()` 空、`cooperativeZmSpawnZones` 的逗号串、以及 `respawn` 的 `0..60000`

## 一、范围

本报告学习 `sv_script_builtin_mp.cpp` 700–1040 行（`zmZoneAt` 的空名契约、`zmPlayerCount` 的"快照是空的"、`zmCooperativeSpawnZones` 的相邻联合、`zmPlayerZone`、`zmSpawnGoal`、四个玩家方法、`setMapGameObjects`）。

## 二、**"这些体积不铺满地图"**（本组最重要的一段）

### 2.1 那段

```php
// zone is an ordinary place to be -- the volumes do not tile the map --
// and failing here would make a script treat "nowhere" as a fault.
return success(zone ? zone->name : std::string{});
```

**⇒ 而 `zmPlayerZone` 的对应段：**

```php
// The volumes do not tile the map. Preserve the same empty-name contract
// as zmzoneat so a director can retain its last usable zone while the
// player crosses a gap instead of treating an ordinary position as an
// engine failure.
return success(zone ? zone->name : std::string{});
```

### 2.2 二十四层

```text
1. **这些体积【不铺满地图**】**
2. ⇒ **⇒ 所以【"不在任何区域里"是【一个普通的位置**】】**
3. ⇒ **⇒ 而【在这里失败【会让脚本把『无处』当成一个故障**】】**
4. ⇒ **⇒ 所以返回 `success("")`**
5. ⇒ **而 `zmPlayerZone` 保留【同一个空名契约**】**
6. ⇒ **⇒ 所以【一个导演**【可以在玩家穿过一个空隙时**【保留它最后可用的那个区域**】】**
7. ⇒ **⇒ 而【不是把一个普通位置【当成一个引擎失败**】】**
```

### 2.3 ⭐⭐⭐ **"这些体积不铺满地图，所以在这里失败会让脚本把『无处』当成一个故障"**

**✅ 这是本报告里**最重要的一条"错误语义的设计**。**

**✅ 与 §439 的 `zmZoneAt`（同一个函数）**——**这里给出了"为什么"** ✓

**⇒ 三层**：
```text
假设：**不在任何区域 = 一个错误**
真相：**这些体积不铺满地图 ⇒ 不在任何区域是【常见的**】
⇒ **⇒ 所以【把它当错误会【让脚本对正常情况报警**】】
```

**✅ 与 §438 的"一个没有目标的点没有路由可测 ⇒ 那是『否』，不是『一个错误』"**完全同族（**第四次"一个合法的空**）。

**⇒ 三次闭合**：
```text
§420  **不可路由 ⇒ 永远得不到 actor**
§438  **没有目标 ⇒ 返回 `0`**
§439/§440  **不在任何区域 ⇒ 返回 `""`**
⇒ **⇒ 三种"合法的空**】
```

**✅ ⭐⭐⭐ **一个"合法的空"的三例表**。

**⚠ 而"一个导演可以保留它最后可用的那个区域"⇒ **一个具体的使用场景**。**

**⇒ 五层**：
```text
若返回错误 ⇒ **脚本必须处理** ⇒ **而它【能做什么**】？**
若返回 `""` ⇒ **脚本【保留上一个**】 ⇒ **一个平滑的过渡**
⇒ **⇒ 所以【`""` 让【容错**成为可能**】
```

**✅ ⭐⭐ **"`""` 让容错成为可能"** —— 与 §440 五 的"空串让循环简单"**互补**。

**⇒ 三层**：
```text
`""` ⇒ **一个"未知但非错误"的返回值**
⇒ **⇒ 所以【调用方【可以用它做状态保持**】】
```

**✅ ⭐⭐⭐ **一个"用返回值表达容错"的实例**。

## 三、**`zmPlayerCount` 的"快照是空的"**（本组第二重要）

### 3.1 那段

```php
// World events run after beginFrame and before endFrame. During that
// interval snapshot().playerStates is deliberately empty: endFrame
// assembles the candidate snapshot transactionally. clientStates_,
// exposed through playerState(), is the authoritative live frame state
// and already contains every active client at this callback boundary.
std::int64_t playerCount{};
for (std::uint32_t clientNum = 0; clientNum < MaximumGameClients; ++clientNum)
    if (world.playerState(clientNum)) ++playerCount;
```

### 3.2 二十层

```text
1. **世界事件【在 `beginFrame` 之后、`endFrame` 之前**】跑**
2. ⇒ **在那个区间里 `snapshot().playerStates` 【刻意地是空的**】**
3. ⇒ **⇒ 因为 `endFrame` 【事务性地组装**那个候选快照**
4. ⇒ **⇒ 所以【在 `endFrame` 之前读它，什么也看不到**】**
5. ⇒ **而 `clientStates_`（通过 `playerState()` 暴露）是【权威的活体帧状态**】**
6. ⇒ **⇒ 而它【在那个回调边界【已经含有每一个活跃客户端**】】**
7. ⇒ **⇒ 所以 `zmPlayerCount` 【必须用 `playerState()` 【而不是**】`snapshot()`**】
```

### 3.3 ⭐⭐⭐ **"`snapshot().playerStates` 刻意地是空的，因为 `endFrame` 事务性地组装那个候选快照"**

**✅ 与 §413 的"`logPlayerPresentation` 必须在 `endFrame` 之后，因为 `world_.snapshot()` 只有 `endFrame` 发布它之后才是客户端会收到的帧，而更早读它找到完全没有 `ET_PLAYER` 实体"**——**完全同源** ✓

**⇒ 三层**：
```text
§413  **`snapshot()` 在 `endFrame` 前 ⇒ 空**
§440  **`snapshot().playerStates` 在 `endFrame` 前 ⇒ 空**
⇒ **⇒ 两次"一个还没发布的量**】
```

**✅ ⭐⭐⭐ **一个"读一个还没发布的量"的两例表**。

**⚠ 而"`playerState()` 是【权威的活体帧状态**】"⇒ **一个明确的替代**。**

**⇒ 三层**：
```text
`snapshot()` ⇒ **已发布的**（**在 `endFrame` 之后**）
`playerState()` ⇒ **活的**（**任何时候**）
⇒ **⇒ 所以【两个 API，两个时机**】
```

**✅ ⭐⭐ **"两个 API，两个时机"** —— 与 §438 的"`VmSpawnCrossesBarrier` 每次跑 A*"**不同（这是**一个时机选择**）。

**⇒ 三层**：
```text
§413  **`snapshot()` 在 `endFrame` 之后才有效**
§440  **`playerState()` 在 `endFrame` 之前就有效**
⇒ **⇒ 所以【脚本内建【在帧中间跑 ⇒ 必须用后者**】
```

**✅ ⭐⭐ **"脚本内建在帧中间跑 ⇒ 必须用活体状态"**。</br>

**✅ 与 §418 的"`WireZeroBaseline()` 的成员默认值"**不同（这是**一个 API 的时机契约**）。

**⚠ 而"`MaximumGameClients`"⇒ **`18`**（§422 的推断）。**

**⇒ 三层**：
```text
`for (clientNum = 0; clientNum < MaximumGameClients; ++clientNum)`
⇒ **⇒ 所以【它扫【所有可能的玩家槽**】】
```

**✅ ⭐ **一个"扫全槽"的实例**。

## 四、**`zmCooperativeSpawnZones` 的"逗号串"**（本组第三重要）

### 4.1 那段

```php
// One compact response gives Lua a stable, final target set.  That keeps
// adjacency calculation on its one-second source-status poll instead of
// rebuilding it once for every selected zone.
std::string result;
for (std::size_t index{}; index < selected.size(); ++index)
{
    if (!selected[index]) continue;
    if (!result.empty()) result.push_back(',');
    result += std::to_string(index + 1u);
}
return success(std::move(result));
```

### 4.2 二十层

```text
1. **一个紧凑的响应给 Lua 一个【稳定的、最终的目标集**】**
2. ⇒ **⇒ 那让【相邻计算【留在它的【一秒一次**的源状态轮询上】】**
3. ⇒ **⇒ 而不是【为【每一个被选中的区域**】重新构建它一次**
4. ⇒ **格式：`"1,3,5"`（**逗号分隔的一到基索引**）**
5. ⇒ **⇒ 所以【它【绕开了**"没有表类型"的限制**】
6. ⇒ **⇒ 用一个【字符串**编码一个整数列表**
```

### 4.3 ⭐⭐⭐ **"一个字符串编码一个整数列表"**

**✅ 与 §438 的"`SvScriptValue` 没有表类型 ⇒ 索引是唯一可能的接口"**——**这是一条绕开的方法** ✓

**⇒ 三层**：
```text
约束：**没有列表类型**
方法 A：**count + index**（§438）
方法 B：**逗号分隔字符串**（§440）
⇒ **⇒ 所以【两个绕开的方式**】
```

**✅ ⭐⭐⭐ **"两种绕开"** —— 与 §438 的"索引空间弥补约束"**互补**。

**⇒ 三层**：
```text
§438  **`zmzoneadjacentat` 返回一个索引 ⇒ 可组合**
§440  **`zmcooperativespawnzones` 返回一个逗号串 ⇒ 一次给全**
⇒ **⇒ 所以【一个【单值**一个【集合**】
```

**✅ ⭐⭐ **"一个单值一个集合"** —— 两个不同的绕开方式。

**⚠ 而"逗号串 ⇒ Lua 必须解析**"⇒ **一个解析的成本**。**

**⇒ 三层**：
```text
服务器：**一个字符串**
Lua：**必须 `split(",")`** ⇒ **一个解析**
⇒ **⇒ 所以【一次传输换一次解析**】
```

**✅ ⭐ **一个权衡的实例**。

**⚠ 而"保留相邻计算在一秒一次的轮询上"⇒ **一个性能设计**。**

**✅ 与 §438 的"每次调用跑一条 A* ⇒ 缓存"**同族（**第三次"性能约束**）。

**⇒ 三层**：
```text
§420  **`zmSpawnCrossesBarrier` 每次 A***
§438  **脚本必须缓存**
§440  **`SV_ZmZoneAdjacency` 只在一秒一次的轮询上算**
⇒ **⇒ 三次"避免重复计算**】
```

**✅ ⭐ **一个"避免重复"的三例表**。

### 4.4 而**"只选活跃的，而且只看邻接"**

```php
for (const auto occupiedZone : occupied) {
    if (zones[occupiedZone].active) selected[occupiedZone] = true;
    for (const auto neighbour : adjacency[occupiedZone]) {
        if (zones[neighbour].active) selected[neighbour] = true;
    }
}
```

**⇒ 十层**：
```text
1. **对于每一个【被占据**的区域**
2. ⇒ **若它【活跃**】⇒ 选中它**
3. ⇒ **对它【每一个邻居**】**
4. ⇒ **若那个邻居【活跃**】⇒ 选中它**
5. ⇒ **⇒ 所以【只有【活跃的**区域可能被选**
6. ⇒ **⇒ 而【被占据的**区域【优先**】
7. ⇒ **⇒ 而它的【直接邻居**次之**
```

### 4.5 ⭐⭐⭐ **"一个『被占据的活跃区域 + 它的活跃邻居』的联合"**

**✅ 与 §440 二 的"一个导演保留它最后可用的区域"**不同（这是**一个选择规则**）。

**⚠ 而"`if (zones[occupiedZone].active)`"⇒ **一个被占据但不活跃的区域【不被选**】**。**

**⇒ 三层**：
```text
若【一个玩家站在一个【不活跃**】的区域里 ⇒ **它【不被选**】
⇒ **⇒ 所以【"被占据"不够，还要"活跃**"】
```

**✅ ⭐ **一个"两个条件"的实例**。</br>

**✅ 与 §438 的"`zmZoneActive` 是 `zone.active ? 1 : 0`"**配合。

## 五、**`zmSpawnGoal` 的"一个空串是一个真实的答案"**

```php
// AN EMPTY STRING IS A REAL ANSWER, not a missing one: zm_sumpf_sh carries
// a goal on only 32 of its 74 spawn points.
return success(point.goal);
```

**⇒ 八层**：
```text
1. **一个空串【是一个真实的答案，不是一个缺失的**】**
2. ⇒ **因为 `zm_sumpf_sh` 的 `74` 个 spawn 点里【只有 `32` 个**】携带一个 goal**
3. ⇒ **⇒ 所以 `42/74 = 57%` 【没有 goal**】
4. ⇒ **⇒ 所以【空串是【常态**不是异常**】
```

**✅ 与 §420 的"factory 的 `69` 个 spawner 里 `8` 个没有目标"**同族（**第五次"一个具体的缺失比例"）。

**⇒ 三层**：
```text
§420  **`8/69` = `11.6%`**（factory）
§438  **`5/30`**（factory 跨屏障）
§440  **`42/74` = `57%`**（`zm_sumpf_sh` 没有 goal）
⇒ **⇒ 三次"一个分数**】
```

**✅ ⭐⭐ **一个"分数"的三例表**。

**⚠ 而"`zm_sumpf_sh` 的 `74` 个 spawn 点"⇒ **与 §414 的"`zm_sumpf_sh` 有 `275` 个条目"**不同（**那是实体，这是 spawn 点**）。

**✅ 一个**需区分的两个数**。

## 六、**`respawn` 的 `0..60000`**

```php
if (!delay || *delay < 0 || *delay > 60'000)
    return failure(..., "respawn expects a delay from 0 through 60000 milliseconds");
switch (world.requestPlayerRespawn(call.self->id, static_cast<std::uint32_t>(*delay))) {
case Queued:          return success(std::monostate{});
case ClientNotFound:  return failure(ObjectNotFound, "respawn player does not exist");
case NotPlaying:
case NotDead:         return failure(InvalidObjectState, "respawn requires a dead Playing player");
case InvalidDelay:    return failure(InvalidArgumentValue, "respawn delay is invalid");
}
return failure(WorldMutationFailed, "respawn returned an invalid result");
```

**⇒ 十四层**：
```text
1. **`0..60000` 的延迟** ⇒ **一分钟上限**
2. ⇒ **⇒ 所以【一个脚本【不能请求一小时后的重生**】】**
3. ⇒ **而 `NotPlaying` 与 `NotDead` 【共用一个错误**】（`InvalidObjectState`）
4. ⇒ **⇒ 而【消息说"`respawn` 需要一个死的 `Playing` 玩家**】】
5. ⇒ **⇒ 所以【两个状态合成一个消息是【合理的**】（**因为它们是【同一个前提的两半**）】
6. ⇒ **而 `InvalidDelay` ⇒ 【世界层的二次检查**】**
7. ⇒ **⇒ 所以【脚本层与世界层【各检查一次**】】
```

### 6.1 ⭐⭐⭐ **"两个状态合成一个消息是合理的，因为它们是同一个前提的两半"**

**✅ 与 §437 的"五个拒绝都返回同一个 `false`"**——**相反**（那里**合并是缺陷**，这里**合并是合理**）。

**⇒ 三层**：
```text
§437  **`gameplay_authority_not_ready` / `not_playing` / ... ⇒ 五个不同的原因** ⇒ **必须分开**
§440  **`NotPlaying` / `NotDead` ⇒ 同一个前提** ⇒ **可以合并**
⇒ **⇒ 判据是【它们是【不同的原因**还是【同一个前提的两半**】】
```

**✅ ⭐⭐⭐ **"不同的原因 vs 同一个前提的两半"** —— 本报告最精确的判据。

**⚠ 而"`0..60000` 与 §438 的 `round 1..255`"⇒ **两个不同的界**。**

**⇒ 三层**：
```text
`respawn` 的延迟 ⇒ `0..60000`（**毫秒**）
`zmSetRound` 的 `round` ⇒ `1..255`
`zmSetRound` 的 `goal` ⇒ `0..255`
⇒ **⇒ 三个不同的界，各由语义决定**
```

**✅ ⭐⭐ **"界由语义决定"** —— 与 §439 的"两个下界不同因为语义不同"**同族（**第三次）。

**⇒ 三层**：
```text
§431  **`clamp(0, 1000000)`**
§439  **`round 1..255` / `goal 0..255`**
§440  **`respawn 0..60000`**
⇒ **⇒ 三次"界由语义决定**】
```

**✅ ⭐ **一个"界由语义决定"的三例表**。

## 七、**`setMapGameObjects` 的两个上限**

```php
constexpr std::size_t MaximumGameObjectNames = 32;
constexpr std::size_t MaximumGameObjectNameLength = 64;
if (call.arguments.size() > MaximumGameObjectNames) ⇒ InvalidArgumentCount
if (name->empty() || name->size() > MaximumGameObjectNameLength) ⇒ InvalidArgumentValue
```

**⇒ 十层**：
```text
1. **最多 `32` 个名字**
2. ⇒ **每个最多 `64` 字节**
3. ⇒ **⇒ 所以【一次调用【最多 `2KB`**】】**
4. ⇒ **而【空名字 ⇒ 拒绝**】**
5. ⇒ **⇒ 所以【`setMapGameObjects({})` 与 `setMapGameObjects({""})` 是【不同的**】**
```

### 7.1 ⭐⭐⭐ **"`{}` 与 `{""}` 是不同的"**

**✅ 这是本报告里**最重要的一条与 §397 的闭合**。**

**§397 的结论**：**`isAllowed` 的参数是【实体自己的名字】，而【捕获**】是允许列表 ⇒ **一个空允许列表因此拒绝每一个【有名字**的实体 ⇒ **`setMapGameObjects({})` 【是**】一个清除**。

**⇒ 三层**：
```text
§397  **`setMapGameObjects({})` 是【一个清除**】（**因为空列表拒绝所有有名字的实体**）
§440  **而 `{""}` 【被拒绝**】（**因为 `name->empty()` ⇒ `InvalidArgumentValue`**）
⇒ **⇒ 所以【只有一个**空的列表，没有"一个空名字"**】
```

**✅ ⭐⭐⭐ **一个跨报告的精确闭合** —— **§397 的"清除"语义在这里得到了实现的确认**。

**⇒ 三层**：
```text
§397  **`setMapGameObjects({})` 的语义被【纠正**为"清除"**
§440  **而 `{""}` 被【拒绝**】⇒ 所以【不能混淆**】
⇒ **⇒ 所以【两个 API 语义一致**】
```

**✅ ⭐⭐ **"一个语义纠正被实现确认"**。

## 八、关键结论

1. **⭐⭐⭐ "这些体积不铺满地图，所以在这里失败会让脚本把『无处』当成一个故障"`** ⇒ **`""` 是一个"合法的空"** —— 第四次"合法的空"（与 §420、§438、§439 同族）。
2. **⭐⭐ "`zmPlayerZone` 保留同一个空名契约，所以一个导演可以在玩家穿过一个空隙时保留它最后可用的那个区域，而不是把一个普通位置当成一个引擎失败"`** ⇒ **"`""` 让容错成为可能"**。
3. **⭐⭐⭐ `zmPlayerCount` 的"`snapshot().playerStates` 刻意地是空的，因为 `endFrame` 事务性地组装那个候选快照；而 `clientStates_`（通过 `playerState()`）是权威的活体帧状态，已经含有每一个活跃客户端"`** —— 与 §413 的"`logPlayerPresentation` 必须在 `endFrame` 之后"完全同源（**第二次"读一个还没发布的量**）。
4. **⭐⭐ "两个 API，两个时机：`snapshot()` 是已发布的（`endFrame` 之后），`playerState()` 是活的（任何时候）⇒ 脚本内建在帧中间跑 ⇒ 必须用后者"`**。
5. **⭐⭐⭐ `zmCooperativeSpawnZones` 的"一个紧凑的响应给 Lua 一个稳定的、最终的目标集，那让相邻计算留在它的一秒一次的源状态轮询上"`** ⇒ **用【一个逗号分隔的字符串**编码一个整数列表** ⇒ **第二种绕开"没有表类型"的方法**（与 §438 的 count+index 互补）。
6. **⭐ "一个单值 vs 一个集合"**：`zmZoneAdjacentAt` 返回一个索引（可组合），`zmCooperativeSpawnZones` 返回一个逗号串（一次给全）。
7. **⭐⭐ "一个『被占据的活跃区域 + 它的活跃邻居』的联合"`** —— 而**"被占据"不够，还要"活跃"**。
8. **⭐⭐⭐ `zmSpawnGoal` 的"一个空串是一个真实的答案，不是一个缺失的：`zm_sumpf_sh` 的 `74` 个 spawn 点里只有 `32` 个携带一个 goal"`**（`42/74 = 57%` 没有）—— 第五次"一个具体的缺失比例"（与 §420 的 `8/69` 同族）。
9. **⭐⭐ `respawn` 的 `0..60000`**（一分钟上限），而 **`NotPlaying` 与 `NotDead` 共用一个 `InvalidObjectState`** ⇒ **"两个状态合成一个消息是合理的，因为它们是同一个前提的两半"`** —— 与 §437 的"五个拒绝必须分开"形成**极精确的对照**：**判据是"它们是不同的原因还是同一个前提的两半"** —— 本报告最重要的判据。
10. **⭐⭐ "界由语义决定"的第三例**：`respawn 0..60000`、`round 1..255`、`goal 0..255` —— 与 §431、§439 同族。
11. **⭐⭐⭐ `setMapGameObjects` 的"`{}` 与 `{""}` 是不同的"**：**`{}` 是清除（§397 的语义纠正），而 `{""}` 被拒绝（`name->empty() ⇒ InvalidArgumentValue`）** ⇒ **一个跨报告的精确闭合**（**§397 的"清除"语义在这里得到了实现的确认**）。

## 九、未闭合点

- `SV_ZmZoneAt` 的"在区域内"判定（体积凸包）。
- `zm_sumpf_sh` 的 `74` 个 spawn 点与 `275` 个实体条目的关系。
- `OLMOD_ZM_COOP_SPAWN_ZONES` 的"cooperative-union-reconstruction" vs "legacy-first-player"。
- `MaximumGameClients` 是否为 `18`。
- `sv_script_builtin_mp.cpp` 1040 行之后未读取（**共 `4424` 行**）。
