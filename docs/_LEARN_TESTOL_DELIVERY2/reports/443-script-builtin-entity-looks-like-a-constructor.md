# 443 · **"`codol.entity(n)` 看起来像一个构造函数而它不是"** —— `spawnModel` 的一次事务、`setModelAt` 的 `validateEntityMethod` 精确计数陷阱、以及"池拒绝是普通的"

## 一、范围

本报告学习 `sv_script_builtin_mp.cpp` 1720–2060 行（`setHealth` 的 `value_or` 默认、`setCanDamage` 的三分支、`setModel`、`setModelAt`、`spawnModel` 的完整理由、`spawnGroundTiltController`）。

## 二、**"`codol.entity(n)` 看起来像一个构造函数而它不是"**（本组最重要的一段）

### 2.1 那段

```php
// ALLOCATE A WORLD ENTITY. Without this the script layer cannot build loot at
// all, and the reason is easy to miss: `codol.entity(n)` LOOKS like a
// constructor and is not one.
//
//     codol.entity(37)   -- "give me a handle to entity 37"
//     codol.entity()     -- error: object id must be an integer
//
// It is `createObject(..., Entity)` in sv_script_lua_mp.cpp, which wraps an
// entity NUMBER that already exists into a userdata. Nothing in the sixteen
// builtins allocated a slot, so the only entities a script could ever touch were
// the ones the map shipped -- 31 script models on mp_battlecity, all of them
// scenery the map wants where it put them. A loot system needs entities that did
// not exist when the map was compiled.
```

### 2.2 二十四层

```text
1. **分配一个世界实体**
2. ⇒ **没有它，脚本层【根本无法构建拾取**】**
3. ⇒ **⇒ 而理由是【很容易错过**的】**
4. ⇒ **`codol.entity(n)` **看起来像一个构造函数而【它不是**】】**
5. ⇒ **`codol.entity(37)`** ⇒ **"给我一个【到实体 37**】的 handle"**
6. ⇒ **`codol.entity()`** ⇒ **错误：`object id must be an integer`**
7. ⇒ **它是在 `sv_script_lua_mp.cpp` 里的 `createObject(..., Entity)`**
8. ⇒ **⇒ 它把【一个【已经存在的**】实体号【包进一个 userdata**】】**
9. ⇒ **⇒ 十六个内建里【没有一个分配槽**】**
10. ⇒ **⇒ 所以【一个脚本【能触碰的唯一实体**】是【那些地图发运的**】】**
11. ⇒ **（`mp_battlecity` 上 `31` 个 script model）**
12. ⇒ **⇒ 全部是【地图想要放在它放的地方**】的场景**
13. ⇒ **⇒ 而一个拾取系统【需要【在地图被编译时【不存在**】的实体**】】**
```

### 2.3 ⭐⭐⭐ **"`codol.entity(n)` 看起来像一个构造函数而它不是"**

**✅ 这是本报告里**最重要的一条"API 命名陷阱**。**

**✅ 与 §421 的"`setScriptModelPresentation` 是一个 mutator 不是一个 constructor"**——**完全同族** ✓

**⇒ 三层**：
```text
§421  **`setScriptModelPresentation` ⇒ mutator，**需求**一个已有模型**
§443  **`codol.entity(n)` ⇒ 包装一个已有实体**
⇒ **⇒ 两次"看起来像构造而实际是包装**】
```

**✅ ⭐⭐⭐ **一个"API 陷阱"的两例表**。

**⇒ 三层**：
```text
`codol.entity(37)` ⇒ **一个"取句柄"**
而【名字像"构造实体 37"**】
⇒ **⇒ 所以【一个脚本作者【会自然地错**】
```

**✅ 与 §443 五.1 的"从 `spawnEntity` + `setPresentation` 到 `spawnScriptModel`"**完全闭合 ✓

**⇒ 三层**：
```text
§421  **`spawnEntity()` 交回一个空白槽而 `setScriptModelPresentation` 要求一个非空槽**
§443  **第一次实现【正是**那么做的，而【每一次生成都失败**】】
⇒ **⇒ 所以【两个"看起来能组合"的东西【不能**】】
```

**✅ ⭐⭐⭐ **一个"不能组合"的完整闭环**。

**⚠ 而"`31` 个 script model 在 `mp_battlecity` 上"⇒ **一个具体的数**。**

**⇒ 三层**：
```text
`mp_battlecity` ⇒ **`31` 个地图自带的 script model**
⇒ **⇒ 所以【一个脚本【最多**能碰 `31` 个**】
```

**✅ 与 §438 的"`mp_battlecity` 的 `firstDynamicWeapon = 1147`"**配合。

## 三、**"池拒绝是普通的，不是例外的"**（本组第二重要）

### 3.1 那段

```php
// Returns the entity on success and nil on failure, so a script can spawn until
// the pool says no without a pcall around every call. Failure is expected and
// ordinary here: the pool is finite (dynamic numbers start at 37) and a loot
// routine that scatters a hundred crates WILL hit the end of it.
...
const auto handle = world.spawnScriptModel(*modelIndex, *modelName, origin, angles);
if (!handle)
{
    // The pool refusing is ordinary, not exceptional; see above.
    return success(std::monostate{});
}
```

### 3.2 二十层

```text
1. **成功时返回实体，失败时返回 `nil`**
2. ⇒ **⇒ 所以【一个脚本【可以一直生成直到池说不**】】**
3. ⇒ **⇒ 而【不必在【每一次调用**外面套一个 `pcall`**】**
4. ⇒ **⚠ 失败在这里【是被期待的、普通的**】**
5. ⇒ **⇒ 因为【池【是有限的**】】（**动态号从 `37` 开始**）**
6. ⇒ **⇒ 而【一个散播一百个箱子的拾取例程【会碰到它的尽头**】】**
7. ⇒ **⇒ 所以【返回 `success(monostate{})` 而不是 `failure(...)`**】
```

### 3.3 ⭐⭐⭐ **"失败在这里是被期待的、普通的，所以返回 `nil` 而不是一个错误"**

**✅ 与 §440 的"一个空串是一个真实的答案，不是一个缺失的"**、§439 的"那是『否』不是『一个错误』"**完全同族（**第七次"合法的空/失败**）。

**⇒ 三次闭合**：
```text
§438  **没有目标 ⇒ 返回 `0`**
§440  **不在任何区域 ⇒ 返回 `""`**
§443  **池满 ⇒ 返回 `nil`（`monostate`）**
⇒ **⇒ 三次"一个可预期的失败【不是错误**】
```

**✅ ⭐⭐⭐ **"一个可预期的失败不是错误"** —— 本报告的核心区分。

**⚠ 而"动态号从 `37`"⇒ **`FirstDynamicServerEntityNum = 37`**（§414）。**

**⇒ 三层**：
```text
§414  **`zm_factory_sh` 的最低实体号是 `37`**
§443  **"动态号从 `37` 开始"**
⇒ **⇒ 两种"37"的含义**】
```

**⚠ 一处**需要区分的巧合**（**`37` 在 §414 是【表的第一个条目**】而在这里是**动态分配的下界**）。

**⇒ 三层**：
```text
§414  **`37` 是 `zm_factory_sh` 表的最低号**
§443  **`37` 是动态实体的起点**
⇒ **⇒ 两者【可能是【同一个**概念**（**`FirstDynamicServerEntityNum`**）**
```

**✅ ⭐⭐ **一个可能的同一概念**。</br>

**✅ 而 §414 的 `.hpp` 注释说"**lowest is 37 -- which is `FirstDynamicServerEntityNum`, derived independently here**"** ⇒ **确认！**

**⇒ 三层**：
```text
§414  **`37` = `FirstDynamicServerEntityNum`（"derived independently here"）**
§443  **"dynamic numbers start at 37"**
⇒ **⇒ 完全同一个常量**
```

**✅ ⭐⭐⭐ **一个跨报告的常量闭合**。

## 四、**`setModelAt` 的 `validateEntityMethod` 精确计数陷阱**（本组第三重要）

### 4.1 那段

```php
// validateEntityMethod checks an EXACT count, so the optional yaw is
// resolved here first rather than by calling it twice and reporting whichever
// error came second.
const auto argumentCount = call.arguments.size();
if (argumentCount != 4 && argumentCount != 5) ⇒ InvalidArgumentCount
SvEntityHandle handle;
if (auto error = validateEntityMethod(world, call, argumentCount, handle)) return std::move(*error);
```

### 4.2 二十层

```text
1. **`validateEntityMethod` 检查一个【精确的个数**】**
2. ⇒ **⇒ 所以【那个可选的 `yaw` 【必须【先在这里解决**】】】**
3. ⇒ **⇒ 而不是【调用它两次**并【报告【第二个**】的错误**】**
4. ⇒ **⇒ 所以【先取 `argumentCount`，检查 `4` 或 `5`，再把 `argumentCount` 传给验证器**】**
5. ⇒ **⇒ 一个"先决定再验证"的顺序**
```

### 4.3 ⭐⭐⭐ **"而不是调用它两次并报告第二个的错误"**

**✅ 与 §439 的"越早越好"**同族（**第三次"错误的时机/选择**）。

**⇒ 三层**：
```text
错误做法：**`validateEntityMethod(..., 4)` 失败 ⇒ 再试 `5` ⇒ **报告第二个错误**
正确做法：**先检查 `4` 或 `5` ⇒ 再用那个数验证**
⇒ **⇒ 所以【第一个尝试的失败【被丢弃**】】
```

**✅ ⭐⭐ **"第一个尝试的失败被丢弃"** —— 与 §437 的"五个拒绝都返回同一个 `false`"**不同（那里**信息被合并**，这里**被丢弃**）。

**⚠ 而"一个错误的顺序"⇒ **一个可推导的缺陷**（**若调用两次**）**。**

**✅ 与 §438 的"`static_cast<uint64_t>` 让检查工作"**不同（这是**一个 API 的契约**）。

**⇒ 三层**：
```text
`validateEntityMethod` 的契约 ⇒ **精确计数**
⇒ **⇒ 所以【任何"可选参数**"都必须【在调用前解决**】
```

**✅ ⭐⭐⭐ **"任何可选参数都必须在调用前解决"** —— 一个**API 契约的后果**。

**⚠ 而"`spawnModel` 也做同样的 `4`/`5` 检查"**⇒ **同一模式的两处**。**

**⇒ 三层**：
```text
`setModelAt` ⇒ **`4` 或 `5`**
`spawnModel` ⇒ **`4` 或 `5`**
⇒ **⇒ 同一模式两处**】
```

**✅ ⭐ **一个"同一模式"的实例**。

## 五、**`setModelAt` 的"只需要 `yaw`"**（本组第四重要）

### 5.1 那段

```php
// Angles are (pitch, yaw, roll) and only yaw is taken: loot lying on the ground
// wants a facing, not a tumble, and a script that can set pitch can stand a crate
// on its corner. Widen it when something needs it.
```

**⇒ 十层**：
```text
1. **角度是 `(pitch, yaw, roll)` 而【只接受 `yaw`**】**
2. ⇒ **⇒ 因为【躺在地上的拾取【想要一个朝向**，不是一个翻滚**】】**
3. ⇒ **⇒ 而【一个【能设 `pitch`**】的脚本【能让一个箱子【站在它的一角上**】】**
4. ⇒ **⇒ 所以【当有什么需要它时【再扩展**】】**
```

### 5.2 ⭐⭐⭐ **"一个能设 pitch 的脚本能让一个箱子站在它的一角上"**

**✅ 这是本报告里**最重要的一条"最小 API**。**

**✅ 与 §422 的"不需要的字段不加"**——**同族** ✓

**⇒ 三层**：
```text
只接受 `yaw` ⇒ **一个合法的输入空间**
若接受 `pitch` ⇒ **一个能产生【荒谬状态**】的输入空间
⇒ **⇒ 所以【最小 API 【减少**了错误空间**】
```

**✅ 与 §442 的"`permitsNone` 只有最后一个可以是 `0`"**同族（**第四次"限制输入空间**）。

**⇒ 三层**：
```text
§435  **`rank` 的 `16` 位上界**
§442  **`permitsNone` 位置相关**
§443  **只接受 `yaw`**
⇒ **⇒ 三次"限制输入**】
```

**✅ ⭐⭐ **一个"限制输入"的三例表**。

**⚠ 而"当有什么需要它时再扩展"⇒ **一个明确的前进路径**。**

**✅ 与 §437 的"若重提交被看到，扩展 `beginSessionRoster()`"**同族（**第四次"可执行的前进路径**）。

## 六、**`spawnModel` 的"从两步到一个事务"**

### 6.1 那段

```php
// THE SPAWN IS ROLLED BACK IF THE MODEL DOES NOT TAKE. An allocated entity with
// no model is a slot that can never be recovered -- the script has no handle to
// free it with, because it never got one -- so the two steps are one transaction
// rather than two builtins the caller has to sequence correctly.
...
// Resolve the asset BEFORE taking a slot. A name the map's model band does not
// publish is the common script bug, and refusing it here costs the pool nothing.
```

**⇒ 十八层**：
```text
1. **若模型【不生效，那个生成【被回滚**】**
2. ⇒ **一个【分配了而没有模型**】的实体【是一个【永远无法回收**】的槽**
3. ⇒ **⇒ 因为【脚本【没有句柄去释放它**】】**
4. ⇒ **⇒ 因为它【从来没有得到**一个**
5. ⇒ **⇒ 所以【那两步是【一个事务**】】**
6. ⇒ **⇒ 而不是【两个内建【调用者必须【正确排序**】】】
7. ⇒ **⚠ 而【在取槽【之前**】解析那个资产**】
8. ⇒ **⇒ 因为【一个地图模型带【不发布**】的名字【是【常见的脚本 bug**】】**
9. ⇒ **⇒ 而【在这里拒绝它【不花池任何东西**】】**
```

### 6.2 ⭐⭐⭐ **"一个分配了而没有模型的实体是一个永远无法回收的槽，因为脚本没有句柄去释放它"**

**✅ 与 §407 的"不猜数"**同族（**第十次"一个不可恢复的状态"）。

**⇒ 三层**：
```text
若【分两步**】⇒ **第一步成功而第二步失败** ⇒ **一个泄漏的槽**
⇒ **⇒ 所以【一个事务**】
```

**✅ 与 §409 的"候选-提交模式"**、§433 的"全或无"**同族（**第七次"事务性**）。

**⇒ 三层**：
```text
§409  `advanceSdRound` 四个 candidate
§422  `purchaseMapTargetGroup`
§430  `setPlayerNameString`
§433  `queueScoreboardResponse`
§443  **`spawnModel` 的两步一个事务**
⇒ **⇒ 五次"事务性**】
```

**✅ ⭐⭐ **一个"事务性"的五例表**。

**⚠ 而"在取槽之前解析"⇒ **一个"免费拒绝"**。**

**✅ 与 §439 的"在最早的时机拒绝"**同族（**第二次"早拒绝**）。

**⇒ 三层**：
```text
§439  **`precacheModel` 在脚本初始化时拒绝**
§443  **`spawnModel` 在取槽之前拒绝**
⇒ **⇒ 两次"在最便宜的地方拒绝**】
```

**✅ ⭐⭐ **"在最便宜的地方拒绝"**。

## 七、**`setCanDamage` 的三分支**

```cpp
if (arguments.size() != 1) ⇒ InvalidArgumentCount
if (!enabled) ⇒ InvalidArgumentType        // 必须是 bool
if (self->kind == Player) { validatePlayerMethod(0, ...); setPlayerCanTakeDamage }  // 玩家分支
// 否则实体分支
validateEntityMethod(0, handle)
state = world.entityDamageState(handle)
if (!state) ⇒ InvalidObjectState "requires initialized entity health"
state->canTakeDamage = *enabled
setEntityDamageState
```

**⇒ 十四层**：
```text
1. **一个参数（`bool`）**
2. ⇒ **`kind == Player` ⇒ 玩家分支**（**用一个代次作用域的侧存储**）
3. ⇒ **否则 ⇒ 实体分支**
4. ⇒ **而【实体【必须【已有生命值**】】**
5. ⇒ **⇒ 否则 `InvalidObjectState`**
6. ⇒ **⇒ 所以【"设一个不存在的生命值的可伤害性"** ⇒ **拒绝**】
```

### 7.1 ⭐⭐⭐ **"实体必须已有生命值"**

**✅ 与 §442 的 `setHealth` 的 `value_or(Generic)`**——**对照** ✓

**⇒ 三层**：
```text
`setHealth` ⇒ **若没有状态 ⇒ 【创建一个默认的**】（`value_or`）
`setCanDamage` ⇒ **若没有状态 ⇒ 【拒绝**】
⇒ **⇒ 所以【"创建"与"修改"是两个不同的权限**】
```

**✅ ⭐⭐⭐ **"'创建'与'修改'是两个不同的权限"** —— 一个**极精确的判据**。

**⚠ 而"玩家分支用代次作用域"⇒ **§422 的 `setPlayerCanTakeDamage`**。**

**✅ 与 §422 的"脚本从未到达它的清理"**完全闭合 ✓

**⇒ 三层**：
```text
玩家 ⇒ **代次作用域的侧存储** ⇒ **新命自动清零**
实体 ⇒ **`state->canTakeDamage`** ⇒ **随实体消失**
⇒ **⇒ 两个不同的生命周期**
```

**✅ ⭐⭐ **"两个不同的生命周期"**。

## 八、**`setHealth` 的 `value_or` 默认**

```cpp
auto state = world.entityDamageState(handle).value_or(
    SvEntityDamageState{ .kind = SvEntityDamageKind::Generic });
state.health = static_cast<std::int32_t>(*health);
```

**⇒ 六层**：
```text
1. **若没有状态 ⇒ 创建一个 `Generic` 的**
2. ⇒ **⇒ 所以【`setHealth` 【可以创建一个实体伤害状态**】**
3. ⇒ **而【`kind = Generic`】是一个默认**
```

**✅ 与 §443 七.1 的"`setCanDamage` 拒绝"**——**完全互补** ✓

**⇒ 三层**：
```text
`setHealth` ⇒ **创建**（**一个 `Generic` 状态**）
`setCanDamage` ⇒ **只修改**
⇒ **⇒ 所以【`sethealth` 之后再 `setcandamage`**是一条合法路径**】
```

**✅ 与 §443 二 的 `spawnModel` 的用例**完全闭合 ✓

**⇒ 三层**：
```text
`local crate = codol.call("function:spawnmodel", "model_name", x, y, z)`
`if crate then codol.call("method:sethealth", crate, 1) end`
⇒ **⇒ 之后 `setcandamage` 才可能**
```

**✅ ⭐⭐⭐ **一个"三步骤的合法路径"被文档示例确认**。

## 九、关键结论

1. **⭐⭐⭐ "`codol.entity(n)` 看起来像一个构造函数而【它不是】 —— 它是把【一个已经存在的】实体号包进一个 userdata，而十六个内建里没有一个分配槽"`** —— 第二次"API 命名陷阱"（与 §421 的 `setScriptModelPresentation` 是 mutator 同族）。
2. **⭐⭐ "一个脚本能触碰的唯一实体是那些地图发运的（`mp_battlecity` 上 `31` 个 script model），全部是地图想要放在它放的地方的场景；而一个拾取系统需要【在地图被编译时不存在】的实体"`**。
3. **⭐⭐⭐ "第一次实现【正是**用了 `spawnEntity` + `setScriptModelPresentation`，而【每一次生成都失败】：`setScriptModelPresentation` 要求实体【已经**是一个携带模型的 script mover，而一个空白槽永远不是"`** —— 与 §421 的"两个正确的东西不能组合"**完全闭环**。
4. **⭐⭐⭐ "池拒绝是【普通的，不是例外的**】：池是有限的（动态号从 `37` 开始）而一个散播一百个箱子的拾取例程【会碰到它的尽头**】⇒ 所以返回 `success(monostate{})` 而不是 `failure`** —— **"一个可预期的失败不是错误"**（第七次"合法的空/失败"）。
5. **⭐⭐⭐ "`37`"**：**§414 的"lowest is 37 -- which is `FirstDynamicServerEntityNum`, derived independently here"** 与 **§443 的"dynamic numbers start at 37"** 是**同一个常量**（一个跨报告的闭合）。
6. **⭐⭐⭐ `setModelAt` 的 `validateEntityMethod` 精确计数陷阱**：**"它检查一个精确的个数，所以那个可选的 `yaw` 必须先在这里解决，而不是调用它两次并【报告第二个的错误】"`** ⇒ **"任何可选参数都必须在调用前解决"**（一个 API 契约的后果）。
7. **⭐⭐ `setModelAt` 的"只接受 `yaw`"**：**"躺在地上的拾取想要一个朝向，不是一个翻滚；而一个能设 `pitch` 的脚本能让一个箱子站在它的一角上"`** ⇒ **"限制输入空间"**（第三次，与 §435/§442 同族）；而 **"当有什么需要它时再扩展"** 是一个明确的前进路径。
8. **⭐⭐⭐ `spawnModel` 的"一个事务而不是两个内建"**：**"一个分配了而没有模型的实体【是一个永远无法回收的槽】，因为脚本【没有句柄去释放它，因为它从来没有得到一个】"`** —— 第五次"事务性"（与 §409/§422/§430/§433 同族）。
9. **⭐⭐ "在取槽之前解析那个资产：一个地图模型带不发布的名字是常见的脚本 bug，而在这里拒绝它【不花池任何东西】"`** —— 第二次"在最便宜的地方拒绝"（与 §439 同族）。
10. **⭐⭐⭐ `setCanDamage` 与 `setHealth` 的对照**：**`setHealth` 用 `value_or(Generic)` 【创建一个默认的**】状态，而 **`setCanDamage` 对一个没有状态的实体【拒绝**】（`"requires initialized entity health"`）⇒ **"'创建'与'修改'是两个不同的权限"** —— 一个极精确的判据。
11. **⭐ 玩家分支与实体分支的两个生命周期**：**玩家用代次作用域的侧存储（新命自动清零，§422），实体用 `state->canTakeDamage`（随实体消失）**。
12. **⭐⭐⭐ 一条被文档示例确认的三步骤合法路径**：**`spawnmodel` 创建一个不带生命值的实体 ⇒ 然后 `sethealth` 创建那个 `Generic` 状态 ⇒ 然后 `setcandamage` 才可能**。

## 十、未闭合点

- `SvEntityDamageKind` 的完整枚举。
- `mp_battlecity` 的 `31` 个 script model。
- `sv_script_lua_mp.cpp` 的 `createObject(..., Entity)`。
- `codol` 的六个字段（`player` / `entity` / `call` / `on` / `wait` / `thread`）。
- `spawnGroundTiltController` 的用途。
- `sv_script_builtin_mp.cpp` 2060 行之后未读取（**共 `4424` 行**）。
