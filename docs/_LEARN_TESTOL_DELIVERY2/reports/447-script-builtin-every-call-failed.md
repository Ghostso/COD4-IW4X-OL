# 447 · **"这个内置用了 `validateEntityMethod`，所以每一次调用都失败"** —— `suppressCorpse` 的 `20+` 次/局失败、`setAgentField` 的禁止索引、以及"同一个数字两种拼写"

## 一、范围

本报告学习 `sv_script_builtin_mp.cpp` 3080–3420 行（`actorFire` 的 `48.0f` 与 `methodOfDeath = 2`、`actorFirePresentation`、`actorCorpse` 的"零或一"、`setAgentField` 的禁止索引、`deleteEntity` 的"双重删除安全"、`suppressCorpse` 的完整病历、`setLoot` 的双拼写）。

## 二、**`suppressCorpse` 的完整病历**（本组最重要的一段）

### 2.1 那段

```php
// 28800: ACCEPT A PLAYER OBJECT, NOT ONLY AN ENTITY OBJECT.
//
// The 28600 call site passes the VICTIM PLAYER (`codol.player(num)`),
// because that is the object the kill handler already holds. This
// builtin used validateEntityMethod, so every call failed with
//   "suppresscorpse requires a generation-safe entity object code=6"
// (20+ times per match) and no corpse was ever suppressed.
//
// The key it stores is the entity NUMBER, and a player's entity
// number IS its client number on this build -- spawnPlayerCorpse
// consumes the same number from deadPlayer.networkState.number.
// So the player branch is the same key, not a second channel.
```

### 2.2 二十四层

```text
1. **接受一个【玩家对象**，不只是实体对象**
2. ⇒ **`28600` 的调用点【传【受害者玩家**】（`codol.player(num)`）**
3. ⇒ **因为【那是【击杀处理器【已经持有的**对象**】**
4. ⇒ **⚠ 而这个内置【用了 `validateEntityMethod`**】**
5. ⇒ **⇒ 所以【每一次调用【都失败**】**
6. ⇒ **（`"suppresscorpse requires a generation-safe entity object code=6"`）**
7. ⇒ **⇒ 【每一局 `20+` 次**】，而【没有一具尸体【被抑制**】】
8. ⇒ **⚠ 而它存的键是【实体号**】**
9. ⇒ **而【一个玩家的实体号【在这个 build 上【就是它的客户端号**】】**
10. ⇒ **（`spawnPlayerCorpse` 从 `deadPlayer.networkState.number` 消费同一个号**）**
11. ⇒ **⇒ 所以【玩家分支【是同一个键**，不是一个第二通道**】
```

### 2.3 ⭐⭐⭐ **"每一次调用都失败，而每一局 `20+` 次，而没有一具尸体被抑制"**

**✅ 这是本报告里**最重要的一条"一个验证器用错**。**

**✅ 与 §443 的"`codol.entity(n)` 看起来像一个构造函数"**同族（**第六次"一个 API 用错**）。

**⇒ 三层**：
```text
调用点 ⇒ **传一个玩家**
内置 ⇒ **要一个实体**
⇒ **⇒ 所以每一次调用【都失败**】，而那是**一个静默的功能缺失**
```

**✅ ⭐⭐⭐ **"一个静默的功能缺失"** —— 与 §416 的"`perks` 从未写过 ⇒ 从来没有一个 perk 图标"**同族（**第四次"一个特性从未工作**）。

**⇒ 三层**：
```text
§400  **`battery_multiplier` 缺失 ⇒ 除零**
§416  **`perks` 从未写 ⇒ 无图标**
§443  **`spawnmodel` 每一次都失败**
§447  **`suppresscorpse` 每一次都失败（`20+` 次/局）**
⇒ **⇒ 四次"一个特性从未工作**】
```

**✅ ⭐⭐ **一个"从未工作"的四例表**。

**⚠ 而"`code=6`"⇒ **一个具体的错误码**。**

**⇒ 三层**：
```text
`code=6` ⇒ **`SvScriptBuiltinErrorCode` 的第 `6` 个**（`InvalidSelf` 若从 `0` 数）
⇒ **⇒ 而日志【带着它**】⇒ 所以【那个失败【是可诊断的**】
```

**✅ ⭐⭐ **"那个失败是可诊断的"** —— 与 §437 的"八个拒绝都返回同一个 `false`"**对照**。

**⇒ 三层**：
```text
§437  **八个原因一个 `false`** ⇒ **不可诊断**
§447  **`code=6` 带在消息里** ⇒ **可诊断**
⇒ **⇒ 所以【后者【更容易被发现**】
```

**✅ ⭐⭐ **"可诊断的错误更容易被发现"** —— 而**这个 bug 被发现，正是因为错误是具名的**。

### 2.4 而**"玩家分支是同一个键，不是一个第二通道"**

```php
if (call.self->kind == SvScriptObjectKind::Player)
{
    const auto playerState = world.playerState(call.self->id);
    if (!playerState) return failure(ObjectNotFound, "suppresscorpse player does not exist");
    world.suppressPlayerCorpse(call.self->id);
    return success(std::monostate{});
}
SvEntityHandle handle;
if (auto error = validateEntityMethod(world, call, 0, handle)) return std::move(*error);
world.suppressPlayerCorpse(handle.entityNum);
```

**⇒ 十层**：
```text
1. **玩家分支 ⇒ `suppressPlayerCorpse(call.self->id)`**
2. ⇒ **实体分支 ⇒ `suppressPlayerCorpse(handle.entityNum)`**
3. ⇒ **⇒ 两个分支【调用同一个函数**】**
4. ⇒ **⇒ 只是参数来源不同**】
5. ⇒ **⇒ 所以【"同一个键，不是第二个通道"**】
```

**✅ ⭐⭐⭐ **"同一个键，不是第二个通道"** —— 与 §447 二.3 的"一个静默的功能缺失"**互补**。

**⇒ 三层**：
```text
若【第二个通道**】⇒ **两个独立的路径** ⇒ **可能不一致**
若【同一个键**】⇒ **一个路径，两个来源** ⇒ **必然一致**
⇒ **⇒ 所以【后者是【更正确的设计**】
```

**✅ 与 §441 的"`getOrigin` 一个名字两个分支"**同族（**第四次"一个函数两个来源**）。

**⇒ 三层**：
```text
§441  **`getOrigin`：`Player` ⇒ `playerState->origin`，`Entity` ⇒ `entity->currentOrigin`**（**两个不同的数据源**）
§447  **`suppressCorpse`：`Player` ⇒ `self->id`，`Entity` ⇒ `handle.entityNum`**（**同一个键**）
⇒ **⇒ 所以【一个有两个数据源，一个只有一个**】
```

**✅ ⭐⭐⭐ **一个"两个 vs 一个"的对照**。

**⚠ 而"一个玩家的实体号在这个 build 上就是它的客户端号"**⇒ **一个关键事实**。**

**✅ 与 §413 的"`killCamLookAtEntity` 是 `6` 而 `6` 就是 `clientNum`"**完全同族（**第三次"实体号 = 客户端号"）。

**⇒ 三层**：
```text
§407  **`killCamLookAtEntity` = `6` = `clientNum`**
§421  **`L` 的第二个参数就是槽位号**
§447  **"一个玩家的实体号就是它的客户端号"**
⇒ **⇒ 三次"两个号是同一个**】
```

**✅ ⭐⭐ **一个"两个号是同一个"的三例表**。

## 三、**`setAgentField` 的"禁止索引"**（本组第二重要）

### 3.1 那段

```php
if (!field || *field < 0 ||
    *field >= static_cast<std::int64_t>(SvAgentState::FieldCount) ||
    *field == static_cast<std::int64_t>(SvAgentState::EntityNumField) ||
    !value || *value < 0 ||
    static_cast<std::uint64_t>(*value) > std::numeric_limits<std::uint32_t>::max())
    ⇒ "setagentfield expects a mutable field index and uint32 value"
```

### 3.2 二十层

```text
1. **`field` 必须 `0..FieldCount-1`**（`0..23`）
2. ⇒ **而【不能是 `EntityNumField`（`20`）**】**
3. ⇒ **⇒ 所以【`20` 是【一个禁止的索引**】】**
4. ⇒ **`value` 必须 `0..UINT32_MAX`**
5. ⇒ **⇒ 所以【脚本【可以写任何其它 `23` 个字段**】】**
```

### 3.3 ⭐⭐⭐ **"`EntityNumField`（`20`）是一个禁止的索引"**

**✅ 与 §417 的"`EntityNumField = 20` 是 actor 的实体号"**完全闭合 ✓

**⇒ 三层**：
```text
§417  **`EntityNumField = 20`** ⇒ **actor 的实体号**
§446  **`spawnActor` 事务性地填它**（"`AgentState +0x04` 是【被生成的实体号**，由 `spawnActor` 事务性地填**）
§447  **`setagentfield` 【禁止**写它**
⇒ **⇒ 所以【一个字段【只能由它的所有者**写**】
```

**✅ ⭐⭐⭐ **"一个字段只能由它的所有者写"** —— 与 §424 的"`fullNavigationBounds` 只提升"**同族（**第四次"所有权**）。

**⇒ 三层**：
```text
§409  **`advanceSdRound` 的四个 candidate**（**世界拥有它们**）
§422  **`setPlayerCanTakeDamage` 的代次作用域**（**世界拥有它**）
§447  **`setagentfield` 禁止写 `EntityNumField`**（**`spawnActor` 拥有它**）
⇒ **⇒ 三次"所有权**】
```

**✅ ⭐⭐ **一个"所有权"的三例表**。

**⚠ 而"其它 `23` 个字段【脚本可以写**】"⇒ **一个非常开放的 API**。**

**⇒ 三层**：
```text
`23` 个字段（`24 - 1`）
⇒ **⇒ 而【`spawnActor` 只写其中 `4` 个**】（`Model`/`Team`/`Animation`/`AnimationStartTime`）
⇒ **⇒ 所以【剩下的 `19` 个【只能通过 `setagentfield`**】】
```

**✅ ⭐⭐ **"19 个字段只能通过 `setagentfield`"**。

**⚠ 而"`Value` 是 `uint32`"⇒ **一个统一的类型**。**

**⇒ 三层**：
```text
`SvAgentState::fields` ⇒ `std::array<std::uint32_t, 24>`
⇒ **⇒ 所以【一个统一的 `uint32` 是正确的**】
```

**✅ 与 §417 的"`std::array<std::uint32_t, FieldCount> fields{...}`"**完全闭合 ✓

**⚠ 而"`setActorAgentState` 失败 ⇒ `InvalidArgumentValue`（不是 `WorldMutationFailed`）"**⇒ **一个有趣的选择**。**

**⇒ 三层**：
```cpp
if (!world.setActorAgentState(actor, *agent))
{
    return failure(
        SvScriptBuiltinErrorCode::InvalidArgumentValue,
        "setagentfield rejected a value outside that field's wire domain");
}
```

**⇒ 三层**：
```text
失败 ⇒ **`InvalidArgumentValue`**（**一个参数错误**）
而【大多数 `WorldMutationFailed`**
⇒ **⇒ 所以【这个失败【被分类为"值的域"而不是"世界的失败**】
```

**✅ ⭐⭐⭐ **"这个失败被分类为『值的域』而不是『世界的失败』"** —— **因为世界层的检查【是那个字段的线缆域**】。**

**⇒ 三层**：
```text
`setagentfield` ⇒ **一个 `uint32` 的入口**
`setActorAgentState` ⇒ **一个【每个字段的线缆域**的检查**
⇒ **⇒ 所以【"那个值在那个字段的域之外"** 是【正确的描述**】
```

**✅ ⭐⭐ **"正确的错误分类"**。</br>

**✅ 与 §438 的"五道五个错误码"**同族（**第三次"错误分类**）。

## 四、**`setLoot` 的"同一个数字两种拼写"**（本组第三重要）

### 4.1 那段

```php
// EITHER SPELLING OF A NUMBER. Lua hands an integer literal over as an
// integer and `60.0` as a double, and a radius is exactly the argument
// somebody writes both ways.
double radius{};
if (const auto *const value = std::get_if<double>(&call.arguments[1]))
    radius = *value;
else if (const auto *const whole = std::get_if<std::int64_t>(&call.arguments[1]))
    radius = static_cast<double>(*whole);
else return failure(InvalidArgumentType, "setloot expects a pickup radius");
```

### 4.2 二十层

```text
1. **一个数字的【两种拼写**】**
2. ⇒ **Lua 把一个整数字面量【作为一个整数**】交过来**
3. ⇒ **而 `60.0` **作为一个 `double`**】
4. ⇒ **⇒ 而【一个半径【正是【某个人会两种都写**】的那个参数**】**
5. ⇒ **⇒ 所以【`double` 与 `int64_t` 【都被接受**】】
```

### 4.3 ⭐⭐⭐ **"一个半径正是某个人会两种都写的那个参数"**

**✅ 与 §446 的"`yaw` 接受 `double` 或 `int64_t`（`zmspawnactorat` 与 `setActorPosition`）"**同族**——但这里给出了理由。**

**⇒ 三层**：
```text
§446  **`zmspawnactorat` 的 `yaw` ⇒ `double` 或 `int64_t`**（**未给理由**）
§447  **`setloot` 的 `radius` ⇒ 同，而【给了理由**："`60.0` vs `60`"**
⇒ **⇒ 所以【同一手法，一处有理由**】
```

**✅ ⭐⭐⭐ **"同一手法，一处有理由"** —— 与 §438 的"一个 `code` 一个 `message`"**同族（**第三次"同一手法的成熟度不同**）。

**⚠ 而"其它字段【不接受双拼写**】"⇒ **一个不一致**。**

**⇒ 三层**：
```text
`setloot` 的 `radius` ⇒ **`double` 或 `int64_t`**
`setmodelat` 的 `origin` ⇒ **只 `double`**
`zmspawnactorat` 的 `position` ⇒ **只 `SvScriptVector`**
⇒ **⇒ 所以【三个位置/数值参数【三种接受方式**】
```

**⚠ 一个**真实的不一致**（**一个 Lua 脚本【可以写 `setloot(crate, 1149, 60)` 但不能写 `setmodelat(crate, "m", 1, 2, 3)` 用整数**）。

**✅ 与 §441 的"`setScriptedPosition` 的 `origin` 只 `double`"**配合。

**⇒ 三层**：
```text
`setloot` ⇒ **接受整数半径**（**一个 bug 修过**）
`setmodelat` ⇒ **不接受整数位置** ⇒ **一个【可能**的同类 bug**
```

**⚠ 一个**可推导的缺口**（**标注**：**`setmodelat("m", 1, 2, 3)` 会失败，因为 `1`/`2`/`3` 是 `int64_t` 而不是 `double`**）。

**✅ 这是我发现的一个**潜在缺陷**。**

## 五、**`actorFire` 的 `48.0f` 与 `methodOfDeath = 2`**（本组第四重要）

```cpp
auto start = actorEntity->currentOrigin;
auto end = targetState->origin;
start[2] += 48.0f;
end[2] += 48.0f;
const auto trace = world.tracePoint(SvPointTraceRequest{
    .start = start, .end = end,
    .contentMask = PlayerCollisionContentMask,
    .filter = { .passEntityNum = actor.entityNum },
    .mode = SvPointTraceMode::RifleLocational,
    .allowChildren = true,
});
if (!trace) ⇒ MatchStateUnavailable
const bool reachedTarget = trace->fraction >= 1.0f ||
    (trace->hitType == TraceHitTypeEntity && trace->hitId == target->id);
if (!reachedTarget) return success(false);
...
return finishDamageResult(world.finishPlayerDamage(SvPlayerDamagePayload{
    .targetClientNum = target->id,
    .inflictorEntityNum = actor.entityNum,
    .attackerEntityNum = actor.entityNum,
    .damage = static_cast<std::int32_t>(*damage),
    .methodOfDeath = 2,
    .weaponAssetIndex = *weaponIndex,
    .direction = direction,
}), call.id.name);
```

**⇒ 十六层**：
```text
1. **`start`/`end` 都 `+48.0f`** ⇒ **一个眼位/胸位的近似**
2. ⇒ **`PlayerCollisionContentMask`** ⇒ **只测玩家**
3. ⇒ **`filter.passEntityNum = actor.entityNum`** ⇒ **排除自己**
4. ⇒ **`mode = RifleLocational`** ⇒ **与 §412 的真实弹道对齐**
5. ⇒ **`allowChildren = true`** ⇒ **同样对齐**
6. ⇒ **`reachedTarget`：`fraction >= 1.0` 或【命中那个目标**】**
7. ⇒ **⇒ 所以【一个被别的实体挡住的 trace ⇒ 不伤害**】
8. ⇒ **`methodOfDeath = 2`** ⇒ **一个固定的值**
9. ⇒ **`direction` 是一个归一化的**指向目标的向量**
```

### 5.1 ⭐⭐⭐ **"`mode = RifleLocational` + `allowChildren = true` 与 §412 的真实弹道对齐"**

**✅ 与 §412 的"参数对齐真实弹道：`.mode = BulletLocational`（步枪 `.mode = RifleLocational`）+ `.allowChildren = true`"**——**完全闭合** ✓

**⇒ 三层**：
```text
§412  **bot 的遮挡门【对齐真实弹道**】
§447  **`actorfire` 的 trace【同样对齐**】
⇒ **⇒ 所以【同一个纪律两处**】
```

**✅ ⭐⭐⭐ **"同一个纪律两处"** —— 一个**跨文件的模式**。</br>

**✅ 与 §412 的"按『不重复造轮子』，直接对齐那一组参数"**同族（**第二次"对齐既有参数**）。

**⇒ 三层**：
```text
§412  **bot 的对齐**
§447  **actorfire 的对齐**
⇒ **⇒ 两次"对齐**】
```

**✅ ⭐ **一个"对齐"的两例**。

**⚠ 而"`methodOfDeath = 2`"⇒ **一个固定的值**。**

**⇒ 三层**：
```text
`methodOfDeath = 2` ⇒ **一个硬编码**
而【§410 的"子弹路径只填 `MOD_PISTOL_BULLET`/`MOD_RIFLE_BULLET`，从不填 `MOD_HEAD_SHOT`**】**
⇒ **⇒ 所以 `2` 可能是 `MOD_RIFLE_BULLET`**】
```

**✅ 与 §410 的"爆头提升是服务端的"**配合。

**⇒ 三层**：
```text
§410  **服务端把 `methodOfDeath` 提升为 `SvMethodOfDeathHeadShot`**
§447  **`actorfire` 用 `methodOfDeath = 2`**（**一个步枪子弹**）
⇒ **⇒ 所以【两个路径【不同的 `mod`**】
```

**✅ ⭐⭐ **"两个路径不同的 `mod`"**。

**⚠ 而"`48.0f`"⇒ **一个具体的偏移**。**

**⇒ 三层**：
```text
`48.0f` 加到【`start` 与 `end` **两者**】
⇒ **⇒ 所以【一个 48 单位的高度补偿**
```

**✅ 与 §412 的"`chest[2] += target->viewHeightCurrent * 0.5f`"**对照（**那里用一个计算的视高一半，这里用一个常数 `48`**）。

**⇒ 三层**：
```text
§412  **bot ⇒ `viewHeightCurrent * 0.5f`**（**动态**）
§447  **`actorfire` ⇒ `48.0f`**（**常数**）
⇒ **⇒ 所以【一个动态一个常数**】
```

**⚠ 一个**可推导的不一致**（**`48` 可能是一个平均胸高，而 §412 的发现是"`origin` 是脚底"**）。

**✅ 一个**需标注的点**。

## 六、**`deleteEntity` 的"双重删除安全"**

```php
// The generation check in validateEntityMethod makes a double delete safe -- the
// second call holds a stale generation and is refused as ObjectNotFound rather
// than freeing whatever now occupies that number.
```

**⇒ 十层**：
```text
1. **`validateEntityMethod` 的代次检查【让一个双重删除【安全**】】**
2. ⇒ **第二次调用【持有一个陈旧的代次**】**
3. ⇒ **⇒ 而被拒为 `ObjectNotFound`**】
4. ⇒ **⇒ 而不是【释放【那个现在占据那个号的**】东西**
```

### 6.1 ⭐⭐⭐ **"而不是释放那个现在占据那个号的东西"**

**✅ 与 §424 的"代次 `0` 让 `freeEntity` 静默失败"**——**完全同源** ✓

**⇒ 三层**：
```text
§424  **`SvEntityHandle{ num, 0 }` ⇒ 代次不匹配 ⇒ 【静默失败**】
§447  **一个陈旧的代次 ⇒ `ObjectNotFound` ⇒ 【一个具名的拒绝**】
⇒ **⇒ 所以【同一个机制，两个层次**】
```

**✅ ⭐⭐⭐ **"同一个机制，两个层次（静默 vs 具名）"** —— 而**§424 的缺陷正是"静默"**。

**⇒ 三层**：
```text
§424  **代次不匹配 ⇒ 静默**（**一个缺陷**）
§447  **代次不匹配 ⇒ `ObjectNotFound`**（**正确**）
⇒ **⇒ 所以【§447 是【那个机制的正确用法**】
```

**✅ ⭐⭐ **"那个机制的正确用法"**。

**⚠ 而"一个悬空句柄"⇒ **一个经典问题**。**

**⇒ 三层**：
```text
`delete(crate)` ⇒ **槽被释放**
`delete(crate)` ⇒ **同一个句柄，陈旧代次** ⇒ **`ObjectNotFound`**
⇒ **⇒ 所以【双重删除【无害**】
```

**✅ 与 §433 的"槽复用要清状态"**同族（**第十次"槽复用"）。

## 七、关键结论

1. **⭐⭐⭐ `suppressCorpse` 的完整病历**：**"这个内置用了 `validateEntityMethod`，所以【每一次调用都失败】（`"suppresscorpse requires a generation-safe entity object code=6"`，每一局 `20+` 次），而【没有一具尸体被抑制】"`** —— 第四次"一个特性从未工作"（与 §416 同族）。
2. **⭐⭐⭐ "那个失败是可诊断的"（`code=6` 带在消息里）** ⇒ **"可诊断的错误更容易被发现"** —— 与 §437 的"八个原因一个 `false`"形成对照；**而这个 bug 被发现，正是因为错误是具名的**。
3. **⭐⭐⭐ "玩家分支是同一个键，不是一个第二通道"**：**两个分支调用同一个 `suppressPlayerCorpse`，只是参数来源不同** —— 与 §441 的 `getOrigin`（**两个不同的数据源**）形成**精确对照**。
4. **⭐⭐ "一个玩家的实体号在这个 build 上就是它的客户端号"** ⇒ **第三次"实体号 = 客户端号"**（与 §407 的 `killCamLookAtEntity`、§421 的 `L` 同族）。
5. **⭐⭐⭐ `setAgentField` 禁止 `EntityNumField`（`20`）** ⇒ **"一个字段只能由它的所有者写"**（`spawnActor` 事务性地填它）—— 第三次"所有权"（与 §409、§422 同族）。
6. **⭐ "剩下 `19` 个字段只能通过 `setagentfield`"**（`24 - 1 - 4 = 19`），而 **`Value` 是统一的 `uint32`**（与 §417 的 `std::array<std::uint32_t, 24> fields` 闭合）。
7. **⭐⭐⭐ `setActorAgentState` 失败返回 `InvalidArgumentValue` 而不是 `WorldMutationFailed`** ⇒ **"这个失败被分类为『值的域』而不是『世界的失败』"** —— 一个**正确的错误分类**（第三次，与 §438 同族）。
8. **⭐⭐⭐ `setLoot` 的"一个数字的两种拼写"**：**"Lua 把一个整数字面量作为一个整数交过来而 `60.0` 作为一个 `double`，而【一个半径正是某个人会两种都写的那个参数】"`** —— **而 §446 的 `yaw` 用同一手法【但没给理由**】 ⇒ **"同一手法，一处有理由"**。
9. **⚠⚠ 一个可推导的缺口（我发现）**：**`setmodelat`/`setScriptedPosition`/`zmspawnactorat` 的 `origin` 只接受 `double`，所以一个 Lua 脚本写 `setmodelat(crate, "m", 1, 2, 3)`（整数）会失败** —— 而 **`setloot` 已经修过这个 bug**，所以这是**一个同类的潜在缺陷**。
10. **⭐⭐⭐ `actorFire` 的 `mode = RifleLocational` + `allowChildren = true` 与 §412 的"参数对齐真实弹道"完全闭合** —— "同一个纪律两处"。
11. **⭐ `methodOfDeath = 2`（一个固定的步枪子弹）** 与 §410 的"服务端把 `methodOfDeath` 提升为 `SvMethodOfDeathHeadShot`"是两个**不同的 `mod` 路径**。
12. **⚠ `48.0f` 的高度补偿与 §412 的 `viewHeightCurrent * 0.5f`（动态）不一致**：**一个常数一个动态** —— 而 §412 的发现是"`origin` 是脚底"，所以 `48` 可能是一个平均胸高（**需标注**）。
13. **⭐⭐⭐ `deleteEntity` 的"双重删除安全"**：**"`validateEntityMethod` 的代次检查让一个双重删除安全 —— 第二次调用持有一个陈旧的代次，被拒为 `ObjectNotFound`，而不是【释放那个现在占据那个号的东西】"`** —— 与 §424 的"代次 `0` 让 `freeEntity` 静默失败"**同一机制的两个层次**（**静默 vs 具名**），而 **§447 是那个机制的正确用法**。

## 八、未闭合点

- `methodOfDeath = 2` 的确切含义（`MOD_RIFLE_BULLET`？）。
- `48.0f` 的高度补偿与 `viewHeightCurrent` 的关系。
- `setmodelat` 等不接受整数位置是否真的是缺陷。
- `SvScriptBuiltinErrorCode` 的完整编号（`code=6` 是哪个）。
- `PlayerCollisionContentMask` 的值。
- `sv_script_builtin_mp.cpp` 3420 行之后未读取（**共 `4424` 行**）。
