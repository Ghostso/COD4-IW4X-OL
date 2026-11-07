# 438 · **"基于索引是故意的"** —— `SvScriptValue` 没有表类型、`vmspawncrossesbarrier` 的"没有目标 = 没有路由 = 不是错误"、以及 `56` 个内建的两类

## 一、范围

本报告学习 `sv_script_builtin_mp.cpp` 1–360 行，以及全部 `56` 个内建的清单。

## 二、**"基于索引是故意的"**（本组最重要的一段）

### 2.1 那段

```php
// THE zm ZONE BUILTINS. re/demo-re/21-zm-zones-and-spawners.md.
//
// INDEX-BASED ON PURPOSE. SvScriptValue has no table or list-of-strings type,
// so the script cannot be handed the zone model as a structure; it walks it
// with a count and an index instead. Zones are ordered by name, so an index is
// stable for a given map and a script may cache it within a round.
```

### 2.2 二十层

```text
1. **zm 区域内建**
2. ⇒ **基于索引【是故意的**】**
3. ⇒ **因为 `SvScriptValue` 【没有表类型或字符串列表类型**】**
4. ⇒ **⇒ 所以【脚本【不能被交给**】那个区域模型作为一个结构**
5. ⇒ **⇒ 它【用一个计数与一个索引**】来遍历它**
6. ⇒ **⇒ 而区域【按名字排序**】**
7. ⇒ **⇒ 所以【一个索引【对一个给定的地图是稳定的**】】**
8. ⇒ **⇒ 而【一个脚本【可以在一轮里缓存它**】】**
```

### 2.3 ⭐⭐⭐ **"`SvScriptValue` 没有表类型，所以脚本不能作为一个结构收到它"**

**✅ 这是本报告里**最重要的一条"用协议约束反推 API 形状**。**

**⇒ 三层**：
```text
约束：`SvScriptValue` = `variant<monostate, string, int64, ...>`（**无表/列表**）
后果：**不能传一个区域模型结构**
⇒ **⇒ 所以【count + index 是唯一可能**的接口**】
```

**✅ 与 §432 的"没有命令产生它们，因为【没有命令能】"**同族（**第三次"约束反推设计**）。

**⇒ 三层**：
```text
§408  **`_tp` 只在资产存在时写**
§433  **`C`/`D`/`E` 不行，因为没有命令能**
§438  **索引接口，因为没有表类型**
⇒ **⇒ 三次"约束决定形状**】
```

**✅ ⭐⭐⭐ **一个"约束反推设计"的三例表**。

**⚠ 而"按名字排序 ⇒ 索引稳定 ⇒ 可缓存**"⇒ **一个三段的稳定性论证**。**

**⇒ 三层**：
```text
排序：**按名字**
⇒ **⇒ 所以【索引【对一个地图是稳定的**】】
⇒ **⇒ 所以【一个脚本可以【在一轮里缓存它**】】**
```

**✅ ⭐⭐ **"一个索引的可缓存性由排序保证"** —— 与 §414 的"`<map>_const.ff` 的号升序无重复"**同族（**第二次"排序产生稳定性"）。

### 2.4 而**"一到基的索引，因为 Lua 是一到基的"**

```php
// ONE-BASED, because Lua is. A script that writes `for i = 1, count` is
// reading the zone it thinks it is.
if (*integer < 1 || static_cast<std::uint64_t>(*integer) > limit)
    return failure(... " index " + ... + " is outside 1.." + ...);
out = static_cast<std::size_t>(*integer) - 1;
```

**⇒ 八层**：
```text
1. **一到基（`1..n`）**，因为 **Lua 是**
2. ⇒ **⇒ 所以【一个写 `for i = 1, count` 的脚本【在读它以为的那个区域**】】**
3. ⇒ **而内部**`- 1`**转成零到基**
4. ⇒ **⇒ 所以【一个边界转换【在【一个地方**】做】
```

**✅ ⭐⭐ **"一个边界转换在一个地方"** —— 与 §422 的"`sdOriginText` 是模板 on purpose"**同族（**第二次"一个适配点"）。

**⚠ 而"`*integer < 1 || uint64 > limit`"⇒ **两端的检查**。**

**⇒ 三层**：
```text
`< 1` ⇒ **拒绝 `0` 与负数**
`> limit` ⇒ **拒绝超界**
⇒ **⇒ 所以【`1..limit` 是【唯一接受的**区间**】
```

**✅ 而"`static_cast<uint64_t>`"**⇒ **一个无符号转换，避免负值绕过上界**。**

**✅ ⭐⭐⭐ **"把负数转成无符号以绕过上界检查"** —— 一个**经典的边界处理**。

**⇒ 三层**：
```text
若【直接比较 `*integer > limit`**】⇒ **`-1 > 3` 是假** ⇒ **通过**
若【`uint64_t(-1) > 3`**】⇒ **真** ⇒ **拒绝** ✓
⇒ **⇒ 所以【那个 cast 【正是**】这个检查能工作的原因**】
```

**✅ ⭐⭐ **"那个 cast 正是这个检查能工作的原因"** —— 一个**极精确的实现解读**。

**⚠ 而 `std::int64_t` 是输入的 `variant` 类型 ⇒ **它可能为负**。**

## 三、**`validatePlayerMethod` 的六道检查**（本组第二重要）

```cpp
if (call.arguments.size() != expectedArgumentCount)  ⇒ InvalidArgumentCount
if (!call.self)                                      ⇒ MissingSelf
if (call.self->kind != SvScriptObjectKind::Player)   ⇒ InvalidSelf
playerState = world.playerState(call.self->id);
if (!playerState || !gameplayState)                  ⇒ ObjectNotFound
if (*gameplayState != ClientGameplayState::Playing)  ⇒ InvalidObjectState
```

**⇒ 十层**：
```text
1. **参数个数** ⇒ `InvalidArgumentCount`
2. ⇒ **`self` 必须存在** ⇒ `MissingSelf`
3. ⇒ **`self->kind` 必须是 `Player`** ⇒ `InvalidSelf`
4. ⇒ **`playerState` 与 `gameplayState` 都必须取到** ⇒ `ObjectNotFound`
5. ⇒ **且 `gameplayState` 必须是 `Playing`** ⇒ `InvalidObjectState`
6. ⇒ **⇒ 五道，五个不同的错误码**
```

### 3.1 ⭐⭐⭐ **"五道检查，五个不同的错误码"**

**✅ 与 §437 的"五个（实为八）拒绝都返回同一个 `false`"**——**完全相反** ✓

**⇒ 三层**：
```text
§437  **八个拒绝 ⇒ 同一个 `false` ⇒ 一个具名 lambda 补救**
§438  **五道 ⇒ 五个错误码 ⇒ 【内建在设计上就是具名的**】
⇒ **⇒ 一个学到了而另一个从开始就对**
```

**✅ ⭐⭐⭐ **"一个学到了而另一个从开始就对"** —— 本报告里最漂亮的一处跨文件对比。

**⇒ 三层**：
```text
`sv_client_mp.cpp` 的 `commitExecutedUserCmd` ⇒ **曾经是静默的** ⇒ **后来加了名字**
`sv_script_builtin_mp.cpp` ⇒ **从开始就分错误码**
⇒ **⇒ 两个文件【对"可诊断性"的成熟度不同**】
```

**✅ ⭐⭐ **一个"成熟度不同"的对比**。

### 3.2 而**"错误码 vs 错误消息"**

```php
SvScriptBuiltinResult failure(const SvScriptBuiltinErrorCode code, std::string message)
```

**⇒ 六层**：
```text
1. **一个 `code` + 一个 `message`**
2. ⇒ **⇒ 所以【程序可判定的**（`code`）与【人可读的**（`message`）**分开**
3. ⇒ **而 `SvScriptBuiltinResult::succeeded()` 只查 `error.code == None`**
4. ⇒ **⇒ 所以【消息【不参与**成功判定**
```

**✅ ⭐⭐ **"程序可判定 + 人可读"** —— 与 §409 的"名字不是数字"**同族（**第四次）。

**⇒ 三层**：
```text
§409  `sdTeamName`/`sdBombPhaseName` 把枚举变名字
§419  `SV_ClientThinkFailureStageName` 等三个 `Name()` 函数
§438  **一个 `code` 字段 + 一个 `message` 字段**
⇒ **⇒ 三次"两个消费面**】
```

**✅ ⭐ **一个"两个消费面"的三例表**。

**⚠ 而"`SvScriptBuiltinErrorCode` 的七种"（从本段看）：

```text
None
InvalidArgumentCount
InvalidArgumentType
InvalidArgumentValue
MissingSelf
InvalidSelf
ObjectNotFound
InvalidObjectState
WeaponNotOwned
InvalidAmmoState
```

**⇒ 十个**。

## 四、**`zmSpawnCrossesBarrier` 的"没有目标 ⇒ 没有路由 ⇒ 不是错误"**（本组第三重要）

### 4.1 那段

```php
// DOES A ZOMBIE SPAWNED HERE HAVE TO COME THROUGH A WINDOW?
//
// The real question the gametype script has been approximating with zone
// adjacency. See SvServerWorld::zmSpawnCrossesBarrier: it runs an A* per
// call, so the script must ask once per spawn point and cache the answer.
...
// A point with no goal has no route to test, and 8 of factory's 69
// spawners carry none. That is "no", not an error.
if (!spawn.hasGoalOrigin)
    return success(std::int64_t{ 0 });
```

### 4.2 十八层

```text
1. **一个在这里出生的僵尸【必须穿过一扇窗吗**】？**
2. ⇒ **那是 gametype 脚本【一直在用区域邻接【近似**】的那个真问题**
3. ⇒ **`SvServerWorld::zmSpawnCrossesBarrier` 【每次调用跑一条 A***】**
4. ⇒ **⇒ 所以【脚本必须【每个出生点问一次**并【缓存那个答案**】】**
5. ⇒ **⚠ 一个【没有目标**】的点【没有路由可测**】**
6. ⇒ **而 factory 的 `69` 个 spawner 里【`8` 个**】携带没有**
7. ⇒ **⇒ 那是【"否"，不是【一个错误**】**
```

### 4.3 ⭐⭐⭐ **"那是『否』，不是『一个错误』"**

**✅ 与 §420 的"一个不可路由的目标仍然得不到一条发明的路径，它只是永远得不到一个 actor"**完全同族（**第九次"省略/否 优于 错误"）。

**⇒ 三层**：
```text
§420  `zmGoalRoutable` ⇒ **返回 false 而不是发明路径**
§438  **`hasGoalOrigin == false` ⇒ 返回 `0` 而不是 `failure(...)`**
⇒ **⇒ 两次"一个缺失的输入不是错误**】
```

**✅ ⭐⭐⭐ **一个"缺失的输入不是错误"的两例**。

**⚠ 而"`8` of `69`"⇒ **`11.6%`**。**

**✅ 与 §420 的"`5` of factory 的 `30` 个 spawner 目标跨越一个屏障"**配合。

**⇒ 三层**：
```text
`8/69` ⇒ **没有目标**
`5/30` ⇒ **跨屏障**
⇒ **⇒ 两个不同的分数**
```

**✅ ⭐ **一个"两个分数"的对照**。

**⚠ 而"一次 A* per call ⇒ 脚本必须缓存"⇒ **一个性能约束以一个注释的形式传达**。**

**✅ 与 §420 的"每个出生点问一次并缓存"**完全一致 ✓

**⇒ 三层**：
```text
§420  **"调用者必须每个出生点问一次并缓存"**
§438  **"脚本必须每个出生点问一次并缓存那个答案"**
⇒ **⇒ 同一警告两处**
```

**✅ ⭐ **一个"警告重复"的确认**。

## 五、**`zmZoneAdjacentAt` 的 `+ 1u`**

```cpp
return success(static_cast<std::int64_t>(adjacency[zone][neighbour] + 1u));
```

**⇒ 六层**：
```text
1. **`adjacency[zone][neighbour]` 是零到基**
2. ⇒ **`+ 1u` ⇒ 一到基**
3. ⇒ **⇒ 所以【返回给脚本的是【一到基**】**
4. ⇒ **⇒ 而【它【直接可喂回**】`zmzonename`/`zmzonespawncount`**】
```

**✅ ⭐⭐ **"返回值可直接喂回另一个内建"** —— 一个**索引空间的闭合**。

**⇒ 三层**：
```text
`zmzoneadjacentat` ⇒ **返回 `1..n`**
`zmzonename(i)` ⇒ **接受 `1..n`**
⇒ **⇒ 所以【`zmzonename(zmzoneadjacentat(z, i))` 合法**】
```

**✅ ⭐⭐⭐ **一个"内建之间的可组合性"** —— 与 §438 二 的"索引是唯一可能的接口"**互补**。**

**⇒ 三层**：
```text
约束：**没有表类型** ⇒ 只有索引
补偿：**索引可组合** ⇒ 脚本仍可遍历
⇒ **⇒ 所以【约束被【一个闭合的索引空间**】弥补**】
```

**✅ ⭐⭐⭐ **"约束被一个闭合的索引空间弥补"** —— 本报告的核心洞察。

## 六、**`56` 个内建的两类**（本组第四重要）

### 6.1 清单

**`26` 个 `Function`（全局函数）**：

```text
earthquakeat / effectindex / firemagicat / getentarray / playfxat / playsoundat
precachemodel / spawnmodel / weaponindex
zmactivezonecount / zmcooperativespawnzones / zmcooperativezonesource
zmplayercount / zmplayerzone / zmsetround / zmspawnactor / zmspawnactorat
zmspawnangles / zmspawngoal / zmspawnorigin / zmzoneactive / zmzoneat
zmzonecount / zmzonename / zmzonespawncount
```

**`30` 个 `Method`（对象方法）**：

```text
actorcorpse / actorfire / addassist / adddeath / addkill / addscore / addteamscore
addxp / delete / getentitynumber / getmapfield / getorigin / getvelocity
giveweapon / isbot / isonground / issameteam / istouching / playanimation
playfxontag / respawn / setactorstate / setagentfield / setcandamage / sethealth
setloot / setmodel / setmodelat / setobjective / spawnactor / suppresscorpse
```

### 6.2 ⭐⭐ **"十三个 `zm*` 全局函数 + 六个 `zm*` 方法"**

**⇒ 五层**：
```text
1. **十三个 `zm*` 全局**（区域/spawn/round）
2. ⇒ **而【六个 `zm*` 方法**】（`setactorstate`/`setagentfield`/`suppresscorpse`/...）
3. ⇒ **⇒ 所以【zm 面【两个入口**】**
4. ⇒ **全局 ⇒ 【查询世界**】
5. ⇒ **方法 ⇒ 【对一个实体/玩家操作**】
```

**✅ ⭐⭐ **"全局查询世界 / 方法操作实体"** —— 一个**清晰的划分**。

**⚠ 而"`getentarray`"⇒ **一个返回"实体数组"的函数，而 `SvScriptValue` 没有列表类型**。**

**⇒ 三层**：
```text
若 `SvScriptValue` 无列表 ⇒ **`getentarray` 返回什么？**
⇒ **⇒ 可能【一个计数 + 索引**】？或【一个特殊类型**】？
```

**⚠ 一个**需要核对的点**。</br>

**✅ 与 §438 二 的"没有表类型"**可能**矛盾**（**若 `getentarray` 真的返回一个数组**）。

## 七、**`zmSetRound` 的"脚本拥有回合循环"**

```php
// WHAT THE ROUND HUD SHOWS. The script owns the round loop, and this is the
// only way it can say so -- nothing else in this server decides a round.
```

**⇒ 六层**：
```text
1. **回合 HUD 显示什么**
2. ⇒ **脚本【拥有回合循环**】**
3. ⇒ **而【这是它【唯一能说出来**】的方式**
4. ⇒ **⇒ 所以【这个服务器【没有别的东西**】决定一个回合**
```

**✅ 与 §432 的"`gZmRound` 由 gametype 脚本通过 `zmsetround` 设置"**完全闭合 ✓

**⇒ 三层**：
```text
§432  **`SV_SetZmRound` 与 `gZmRound`/`gZmRoundGoal` 的 atomic**
§438  **`zmsetround` 是【唯一**的入口**
⇒ **⇒ 所以【一个脚本 → 一个 atomic → 一个 HUD**】
```

**✅ ⭐⭐ **"脚本 → atomic → HUD"** —— 一个**三层的数据流**。

**⚠ 而"`nothing else in this server decides a round`"⇒ **一个强声明**。**

**✅ 与 §432 的"`12.131` 把这四个 dvar 放进 `stage 6` 而客户端卡住"**配合。

## 八、关键结论

1. **⭐⭐⭐ "基于索引是故意的：`SvScriptValue` 没有表类型或字符串列表类型，所以脚本不能作为一个结构收到那个区域模型 ⇒ 它用一个计数与一个索引来遍历它"`** —— 第三次"约束反推设计"（与 §408、§433 同族）。
2. **⭐⭐ "区域按名字排序 ⇒ 一个索引对一个给定的地图是稳定的 ⇒ 一个脚本可以在一轮里缓存它"`** —— 一个三段的稳定性论证（与 §414 的"号升序无重复"同族）。
3. **⭐⭐⭐ "一到基，因为 Lua 是：一个写 `for i = 1, count` 的脚本在读它以为的那个区域"`** —— 而内部 `- 1` 转成零到基，**一个边界转换在一个地方**。
4. **⭐⭐⭐ "`static_cast<std::uint64_t>(*integer) > limit` 那个 cast 正是这个检查能工作的原因：若直接比较 `*integer > limit` 则 `-1 > 3` 是假 ⇒ 通过；而 `uint64_t(-1) > 3` 是真 ⇒ 拒绝"`** —— 一个极精确的边界处理。
5. **⭐⭐⭐ `validatePlayerMethod` 的五道检查五个错误码**（`InvalidArgumentCount` / `MissingSelf` / `InvalidSelf` / `ObjectNotFound` / `InvalidObjectState`）—— **与 §437 的"八个拒绝都返回同一个 `false`"完全相反** ⇒ **"一个学到了而另一个从开始就对"** —— 本报告最漂亮的一处跨文件对比。
6. **⭐⭐ 一个 `code` 字段 + 一个 `message` 字段的分工**（程序可判定 vs 人可读），而 **`succeeded()` 只查 `code == None`**。
7. **⭐ `SvScriptBuiltinErrorCode` 约十个值**（`None` / `InvalidArgumentCount` / `InvalidArgumentType` / `InvalidArgumentValue` / `MissingSelf` / `InvalidSelf` / `ObjectNotFound` / `InvalidObjectState` / `WeaponNotOwned` / `InvalidAmmoState`）。
8. **⭐⭐⭐ "一个没有目标的点没有路由可测，而 factory 的 `69` 个 spawner 里 `8` 个携带没有 ⇒ 那是『否』，不是『一个错误』"`** —— 第二次"缺失的输入不是错误"（与 §420 的 `zmGoalRoutable` 同族）。
9. **⭐⭐ "`zmSpawnCrossesBarrier` 每次调用跑一条 A*，所以脚本必须每个出生点问一次并缓存那个答案"`** —— 与 §420 的同一警告在两处。
10. **⭐⭐⭐ `zmZoneAdjacentAt` 的 `+ 1u`（零到基 → 一到基）使返回值可直接喂回 `zmzonename`/`zmzonespawncount`** ⇒ **"内建之间的可组合性"** ⇒ **"约束（没有表类型）被一个闭合的索引空间弥补"** —— 本报告的核心洞察。
11. **⭐⭐ `56` 个内建的两类**：`26` 个 `Function`（全局，查询世界）与 `30` 个 `Method`（对象方法，操作实体）；而 **`zm*` 面有 `13` 个全局 + `6` 个方法**。
12. **⚠ 一个待核对的矛盾**：**`SvScriptValue` 没有表类型，但 `getentarray` 是一个"获取实体数组"的函数** —— 它返回什么需要核对。
13. **⭐⭐ "脚本拥有回合循环，而 `zmsetround` 是它唯一能说出来的方式 —— 这个服务器没有别的东西决定一个回合"`** ⇒ 与 §432 的 `gZmRound`/`gZmRoundGoal` 的 atomic 完全闭合（**脚本 → atomic → HUD** 三层数据流）。

## 九、未闭合点

- `SvScriptValue` 的确切 `variant` 成员（是否真的无列表）。
- `getentarray` 的返回类型。
- `SvScriptObjectKind` 的完整枚举。
- `SvZmZone` 的字段（`name` / `spawnPoints` / `active`）。
- `SV_ZmZoneAdjacency` 的"接触"定义（来自体积凸包）。
- `sv_script_builtin_mp.cpp` 360 行之后未读取（**共 `4424` 行**）。
