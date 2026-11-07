# 450 · **`sv_script_builtin_mp.cpp` 全文件收尾** —— "`method:` 前缀漏了所以永解析不到"、`addkill` 的"第一次击杀就结束比赛"、以及一个文件里六种"数字的两种拼写"

## 一、范围

本报告学习 `sv_script_builtin_mp.cpp` 4100–4424 行（六个 `add*` 内建的同构、`method:playsound` 的两次修正、`invoke` 的分派），并收尾整个文件（**共 `4,424` 行**）。

## 二、**"我原来只写了 `"playsound"`，于是 Lua 的 `codol.call` 永远解析不到"**（本组最重要的一段）

### 2.1 那段

```php
handlers_.emplace(
    // ★ P0 修正（刀CC）：现有内建 ID **带 `method:` 前缀**（`"method:delete"` /
    //   `"method:getorigin"` / `"method:adddeath"` …），我原来只写了 `"playsound"`，
    //   于是 Lua 的 `codol.call("method:playsound", 62)` **永远解析不到**
    //   —— 日志实证：`kill sound special skipped series=tank` ×3（系列判定对、
    //   武器确实是 `honeybadgertank_mp`，只是调用失败）。
    SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "method:playsound" },
```

### 2.2 二十四层

```text
1. **现有内建 ID 【带 `method:` 前缀**】**
2. ⇒ **（`"method:delete"` / `"method:getorigin"` / `"method:adddeath"`）**
3. ⇒ **⚠ 我原来【只写了 `"playsound"`**】**
4. ⇒ **⇒ 于是 Lua 的 `codol.call("method:playsound", 62)` **永远解析不到**】**
5. ⇒ **⇒ 日志实证：`kill sound special skipped series=tank` ×`3`**】
6. ⇒ **（**系列判定对**、**武器确实是 `honeybadgertank_mp`**、**只是调用失败**）**
```

### 2.3 ⭐⭐⭐ **"系列判定对、武器确实是 `honeybadgertank_mp`、只是调用失败"**

**✅ 这是本报告里**最重要的一条"一个小的命名不一致导致一个完整的静默失败**。**

**✅ 与 §447 的"`suppresscorpse` 每一次调用都失败（`20+` 次/局）"**同族（**第五次"一个特性从未工作**）。

**⇒ 三层**：
```text
逻辑正确：**系列判定对、武器对**
缺陷：**名字错了**
⇒ **⇒ 所以【一个功能【完全正确**而【完全不可达**】
```

**✅ ⭐⭐⭐ **"完全正确而完全不可达"** —— 本报告的核心观察。

**⚠ 而"`method:` 前缀"⇒ **一个幂等的重复**。**

**⇒ 三层**：
```text
`SvScriptBuiltinId{ SvScriptBuiltinKind::Kind, "method:playsound" }` ⇒ **kind 已经是 `Method` 而名字【又带 `method:`**】
⇒ **⇒ 所以【`"method:"` 是【冗余**的**】**
```

### 2.4 ⚠⚠ **一个结构性的不一致**

**⇒ 而让我检查其它注册**：

```text
`SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "delete" }`          ← 无前缀
`SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "getorigin" }`       ← 无前缀
`SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "adddeath" }`        ← 无前缀
`SvScriptBuiltinId{ SvScriptBuiltinKind::Function, "zmzonecount" }`   ← 无前缀
...
`SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "method:playsound" }` ← **有前缀！**
```

**✅ ⭐⭐⭐ **"`method:playsound` 是【唯一**一个带前缀的 `Method**】**"**。

**⇒ 三层**：
```text
其它 `55` 个 ⇒ **无前缀**
`method:playsound` ⇒ **有前缀**
⇒ **⇒ 所以【它是一个【异常**】
```

**⚠ 而注释说"现有内建 ID **带 `method:` 前缀**（`"method:delete"` / `"method:getorigin"` / `"method:adddeath"`）"** —— **但那三个注册实际是【无前缀**的**！**

**⇒ 三层**：
```text
注释声称：`"method:delete"` / `"method:getorigin"` / `"method:adddeath"` **带前缀**
实际代码：`"delete"` / `"getorigin"` / `"adddeath"` **无前缀**
⇒ **⇒ 所以【注释与代码【相反**】
```

**⚠⚠⚠ **一个真实的矛盾**（**注释描述了一个不存在的约定，而代码【遵循了那个不存在的约定**】）。

**⇒ 三种可能的解释**：
```text
① **Lua 桥【在调用时加前缀**】（则 `"playsound"` 也应该工作 ⇒ 而它不工作）
② **`method:` 是【一个历史遗留**（`"method:playsound"` 是从一个旧的约定来的）
③ **那个 `emplace` 【是一个真正的 bug**（`"method:playsound"` 永远不可达，而 `"playsound"` 应该被注册）
```

**⇒ 而"日志实证 `kill sound special skipped` ×3"⇒ **所以这条修正【【没有修好**】。**

**⇒ 三层**：
```text
修正前：`"playsound"` ⇒ **不可达**（若 Lua 传 `"method:playsound"`）
修正后：`"method:playsound"` ⇒ **可达**（若 Lua 传 `"method:playsound"`）
而【其它 `55` 个内建都是无前缀** ⇒ **而它们【可达**（**若 Lua 传无前缀**）
⇒ **⇒ 所以【要么那个修正是对的（而其它 55 个都错），要么它仍然是错的**】
```

**⚠ 一个**需要核对的严重不一致**（**这是我发现的一个可能的真实缺陷**）。

**✅ 与 §447 的"玩家分支是同一个键"**不同（这是**一个命名约定的混乱**）。

**⇒ 三层**：
```text
`SvScriptBuiltinId` 的 `kind` ⇒ **`Function` 或 `Method`**
`name` ⇒ **一个裸名**（`"delete"` / `"zmzonecount"`）
⇒ **⇒ 所以【`"method:"` 前缀【在其它 `55` 个里【从不出现在 name 里**】
```

**✅ ⭐⭐⭐ **"`method:` 前缀在其它 55 个里从不出现在 `name` 里"** —— **所以 `"method:playsound"` 是唯一的异常**。

**⚠ 而 `invoke` 的实现**：

```cpp
SvScriptBuiltinCall call{
    .id = { kind, std::string(name) },
    ...
};
const auto handler = handlers_.find(call.id);
if (handler == handlers_.end())
    return failure(UnknownBuiltin, "unknown script builtin: " + call.id.name);
```

**⇒ 三层**：
```text
`invoke(kind, name, ...)` ⇒ **直接用 `name` 查**
⇒ **⇒ 所以【一个 `"method:playsound"` 的注册【只能被一个 `name == "method:playsound"` 的调用**命中**】
⇒ **⇒ 而【如果 Lua 传 `"playsound"`** ⇒ **`UnknownBuiltin`**
```

**✅ ⭐⭐⭐ **"只能被一个 `name == "method:playsound"` 的调用命中"** —— **所以要么 Lua 传带前缀的，要么它仍然不可达**。

**⚠ 而 `contains` 的实现**：

```cpp
bool contains(kind, name) const { return handlers_.contains({ kind, std::string(name) }); }
```

**⇒ 三层**：
```text
`contains(kind, name)` ⇒ **同一次查找**
⇒ **⇒ 所以【`contains(Method, "playsound")` ⇒ `false`**
```

**✅ ⭐⭐ **"`contains` 会返回 `false`"** —— **一个可判定的验证**。</br>

**✅ 而"日志实证：`kill sound special skipped series=tank` ×3"**⇒ **一个可执行的验证步骤**。

**⇒ 三层**：
```text
若【那个修正是对的**】⇒ **`playsound` 现在会成功** ⇒ **日志里不应再有 `skipped series=tank`**
若【它仍然是错的**】⇒ **仍有 `skipped`**
⇒ **⇒ 所以【那个日志行【是一个判据**】
```

**✅ ⭐⭐⭐ **"那个日志行是一个判据"** —— 与 §427 的"阳性对照"**同族（**第四次"一个可判定的判据**）。

## 三、**`method:playsound` 的第二次修正：`double` 的接受**（本组第二重要）

### 3.1 那段

```php
// ★ 刀CD 修正：**Lua 的数字是 double**，原来只 `get_if<std::int64_t>` ⇒
//   传 62 会被判 InvalidArgumentValue（日志只剩 `skipped`，看不到原因）。
//   现在两种都接受：整数原样取，浮点必须是无小数且落在 0..255 的有限值。
long long raw{};
if (const auto *asInt = std::get_if<std::int64_t>(&call.arguments[0]))
    raw = static_cast<long long>(*asInt);
else if (const auto *asDouble = std::get_if<double>(&call.arguments[0]))
{
    if (!std::isfinite(*asDouble) ||
        *asDouble != static_cast<double>(static_cast<long long>(*asDouble)))
        return failure(InvalidArgumentValue, "playsound expects an alias index in 0..255");
    raw = static_cast<long long>(*asDouble);
}
else return failure(InvalidArgumentType, "playsound expects an alias index in 0..255");
if (raw < 0 || raw > 255) ⇒ InvalidArgumentValue
```

### 3.2 二十层

```text
1. **Lua 的数字【是 `double`**】**
2. ⇒ **原来只 `get_if<std::int64_t>`**】
3. ⇒ **⇒ 传 `62` 会被判 `InvalidArgumentValue`**】
4. ⇒ **⇒ （日志只剩 `skipped`，看不到原因**）**
5. ⇒ **现在两种都接受**
6. ⇒ **整数【原样取**】**
7. ⇒ **浮点【必须是【无小数**且【落在 `0..255`**的【有限**值**】**
```

### 3.3 ⭐⭐⭐ **"Lua 的数字是 double，而传 62 会被判 InvalidArgumentValue"**

**✅ 与 §447 的"`setLoot` 的『一个数字的两种拼写』"**——**完全同族** ✓

**⇒ 三层**：
```text
§447  **`setLoot` 的 `radius` ⇒ `double` 或 `int64_t`**（**而理由给的是"`60.0` vs `60`"**）
§450  **`playsound` 的 `alias` ⇒ 同，而【理由更精确**："**Lua 的数字是 `double`**"**
⇒ **⇒ 同一手法，两处理由，一处更精确**
```

**✅ ⭐⭐⭐ **"同一手法，一处理由更精确"**。</br>

**✅ 而这是一个**贯穿全文件的模式**：**

**⇒ 而让我数一下**：
```text
§439  **`zmSetRound` ⇒ `int64_t`（只整数）**
§446  **`zmSpawnActorAt` 的 `yaw` ⇒ `double` 或 `int64_t`**
§447  **`setLoot` 的 `radius` ⇒ `double` 或 `int64_t`**
§450  **`playsound` 的 `alias` ⇒ `double` 或 `int64_t`**
⇒ **⇒ 三个"双拼写"，一个"只整数"**
```

**⚠ 一个**真实的不一致**（**`zmSetRound` 的 `round`/`goal` 只接受 `int64_t`**）**。

**⇒ 三层**：
```text
若【Lua 的数字是 `double`**】⇒ **`zmsetround(5.0, 8.0)` 会失败**
而【`zmsetround(5, 8)` 会成功**】（**若 Lua 传整数**）
⇒ **⇒ 所以【那个"Lua 的数字是 `double`"的声明【与 `zmsetround` 矛盾**】
```

**⚠⚠ **一个可推导的缺陷**（**而它取决于 Lua 桥的实际行为**）。

**✅ 与 §450 二 的"注释与代码相反"**同族（**第二次"一个声明与实际不符**）。

**⇒ 三层**：
```text
§450 二  **注释声称 `"method:delete"` 而有前缀，实际无前缀**
§450 三  **注释声称"Lua 的数字是 `double`"而 `zmsetround` 只接受 `int64_t`**
⇒ **⇒ 两次"声明与实际不符**】
```

**✅ ⭐⭐ **一个"声明与实际不符"的两例表**。

## 四、**`addkill` 的"第一次击杀就结束比赛"**（本组第三重要）

### 4.1 那段

```php
// Free-for-all's counterpart to addteamscore. cha keeps the DISPLAY score
// and the counter the limit reads apart - addscore 100 for the scoreboard,
// addteamscore 1 for the 50-kill limit - and free-for-all has no team to
// put the second one on. Without it the only counter left was the 100 per
// kill display score, which crosses a 30 limit on the first kill and ended
// every match immediately.
```

### 4.2 二十层

```text
1. **自由混战的 `addteamscore` 对应物**
2. ⇒ **`cha` 把【显示分数**与【限制读的那个计数器**】【分开**】**
3. ⇒ **`addscore 100` ⇒ 计分板**
4. ⇒ **`addteamscore 1` ⇒ 那个 `50` 击杀限制**】
5. ⇒ **⇒ 而【自由混战【没有队伍**】去放第二个**
6. ⇒ **⚠ 没有它，剩下的唯一计数器【是那个每杀 `100` 的显示分数**】**
7. ⇒ **⇒ 它在一个 `30` 的限制上【第一次击杀就跨过**】**
8. ⇒ **⇒ 而【结束了【每一场比赛**，立即**
```

### 4.3 ⭐⭐⭐ **"它在一个 30 的限制上第一次击杀就跨过，而结束了每一场比赛"**

**✅ 这是本报告里**最重要的一条"两个计数器的区分**。**

**⇒ 三层**：
```text
`addscore 100` ⇒ **显示**
`addteamscore 1` ⇒ **限制读的**
⇒ **⇒ 而【混用 ⇒ 第一次击杀就 `100 > 30`** ⇒ **立即结束**】
```

**✅ 与 §413 的"`dm` awards 50, the team modes 100"**配合。

**⇒ 三层**：
```text
§413  **`SvDmScoreFeedbackKillPoints`（dm `50`）vs `SvScoreFeedbackKillPoints`（团队 `100`）**
§450  **`addscore 100` 是显示而 `addteamscore 1` 是限制**
⇒ **⇒ 所以【"显示分数"与"限制计数"是【两个字段**】
```

**✅ ⭐⭐⭐ **"显示 vs 限制是两个字段"** —— 而**混用会导致立即结束**。

**⚠ 而 `addkill` 的 delta 界**：

```cpp
if (!delta || *delta < -1'000'000 || *delta > 1'000'000)
    ⇒ "addkill expects a bounded integer delta"
```

**⇒ 三层**：
```text
`delta` ⇒ **`-1'000'000..1'000'000`**
⇒ **⇒ 与 §431 的"那十个计分累加器"的 `clamp(0, 1000000)`【同值**】
```

**✅ ⭐⭐ **"`1000000` 与十个累加器的上界同值"** —— 一个**常量复用**。

**⇒ 三层**：
```text
§431  **`std::clamp<std::int64_t>(v, 0, 1'000'000)`**（**十个累加器**）
§450  **`addkill`/`addscore`/`addxp`/`addteamscore`/`adddeath`/`addassist` 的 `±1'000'000`**
⇒ **⇒ 同一常量，两个用途**】
```

**✅ ⭐ **一个"常量复用"的实例**。

## 五、**六个 `add*` 的完全同构**（本组第四重要）

### 5.1 六个

```text
addscore      ⇒ addClientScore
addxp         ⇒ addClientXp
addteamscore  ⇒ addTeamScoreForClient
addkill       ⇒ addKillForClient
adddeath      ⇒ addDeathForClient
addassist     ⇒ addAssistForClient
```

**⇒ 而六个的全部代码是同一形状**：

```cpp
validatePlayerMethod(world, call, 1, playerState)
delta = get_if<int64_t>(arguments[0])
if (!delta || *delta < -1'000'000 || *delta > 1'000'000) ⇒ InvalidArgumentValue
if (!cb || !cb(self->id, (int32_t)*delta)) ⇒ MatchStateUnavailable
return success(monostate)
```

**⇒ 六层**：
```text
1. **六份，每份约 `20` 行**
2. ⇒ **而【唯一的差异是【那个回调名**】】
3. ⇒ **⇒ 所以【六份，一个模板参数**】
4. ⇒ **⇒ 而【没有抽**】
```

### 5.2 ⭐⭐⭐ **"六份，唯一的差异是那个回调名"**

**✅ 与 §448 的"`readInteger` 抽成一个模板"**——**相反** ✓

**⇒ 三层**：
```text
§448  **七个 `readInteger` ⇒ 抽成模板**
§450  **六个 `add*` ⇒ 不抽**
⇒ **⇒ 所以【同一个文件里【一个抽一个不抽**】
```

**✅ ⭐⭐⭐ **"同一个文件里一个抽一个不抽"** —— 与 §448 的"抽与不抽由复杂度决定，不由次数"**完全闭合** ✓

**⇒ 三层**：
```text
`readInteger` ⇒ **`min`/`max`/`result` 三类逻辑** ⇒ **抽**
`add*` ⇒ **一行回调名不同** ⇒ **不抽**
⇒ **⇒ 所以【复杂度（而非次数）决定**】
```

**✅ ⭐⭐ **那个判据在这里被验证**。

**⚠ 而"'不碰任何客户端可见下发'"⇒ **一个明确的边界声明**。**

```php
// **纯服务端，不碰任何客户端可见下发（dvar / configstring）。**
```

**✅ 与 §408 的"STILL NOT SENT，每个都有一个理由"**同族（**第四次"边界声明**）。

**⇒ 三层**：
```text
§403  **"我方没有真实的角色分配，这里下发的是按 demo 形态驱动的显示值"**
§435  **"这缩短窗口，它不关闭它"**
§450  **"纯服务端，不碰任何客户端可见下发"**
⇒ **⇒ 三次"范围的声明**】
```

**✅ ⭐⭐ **一个"范围声明"的三例表**。

## 六、`invoke` 的 `UnknownBuiltin`

```cpp
const auto handler = handlers_.find(call.id);
if (handler == handlers_.end())
    return failure(UnknownBuiltin, "unknown script builtin: " + call.id.name);
return handler->second(world_, call);
```

**⇒ 八层**：
```text
1. **找不到 ⇒ `UnknownBuiltin`**（**一个具名错误**）
2. ⇒ **而消息带 `call.id.name`**
3. ⇒ **⇒ 所以【一个脚本的错名字【会得到一个明确的错误**】**
4. ⇒ **⇒ 而不是【静默地什么都不做**
```

**✅ 与 §449 的"`isbot` 没有回调就答 `false`"**不同（这是**一个真正的错误**）。

**⇒ 三层**：
```text
`UnknownBuiltin` ⇒ **一个名字错了**（**一个脚本 bug**）
`isbot` 的 `false` ⇒ **一个有意义的答案**
⇒ **⇒ 所以【两个不同的处置**】
```

**✅ ⭐⭐ **"两个不同的处置"** —— 而 **`method:playsound` 的笔误【本应**得到一个 `UnknownBuiltin`**】**

**⇒ 三层**：
```text
若 Lua 传 `"method:playsound"` 而注册的是 `"playsound"` ⇒ **`UnknownBuiltin: unknown script builtin: method:playsound`**
若 Lua 传 `"playsound"` 而注册的是 `"method:playsound"` ⇒ **`UnknownBuiltin: unknown script builtin: playsound`**
⇒ **⇒ 所以【两种情况都有【明确的错误**】
```

**⚠ 而"日志实证 `kill sound special skipped series=tank` ×3"⇒ **所以那个 Lua 侧【吞掉**了那个错误**。**

**⇒ 三层**：
```text
`invoke` 返回 `UnknownBuiltin`
而【Lua 侧【只记 `skipped`**】
⇒ **⇒ 所以【一个错误【在 Lua 侧【被降级为 `skipped`**】】
```

**✅ ⭐⭐⭐ **"一个错误在 Lua 侧被降级为 `skipped`"** —— 与 §405 的"一个误报它存在的那个失败的仪器比没有更糟"**同族（**第五次"一个丢失的错误信息**）。

**⇒ 三层**：
```text
§426  **两个分支都能楔死而两个都不说**
§450  **`UnknownBuiltin` 在 Lua 侧变成 `skipped`**
⇒ **⇒ 两次"错误被吞**】
```

**✅ ⭐⭐ **一个"错误被吞"的两例表**。

## 七、`SvScriptBuiltinRegistry` 的九个注入

```cpp
SvScriptBuiltinRegistry(
    SvServerWorld &world,
    MatchScoreCallbacks matchScoreCallbacks,
    ModelResolver modelResolver,
    WeaponResolver weaponResolver,
    ZmZoneProvider zmZoneProvider,
    ModelPrecacher modelPrecacher,
    MissionCallbacks missionCallbacks,
    SoundResolver soundResolver,
    AnimationResolver animationResolver,
    EffectResolver effectResolver)
```

**⇒ 十层**：
```text
1. **`world` 【一个引用**（**不是注入**）
2. ⇒ **九个 `std::function`**
3. ⇒ **`MatchScoreCallbacks` 与 `MissionCallbacks` 【是两个 struct**】**
4. ⇒ **⇒ 而【其它七个是【单个函数**】
5. ⇒ **⇒ 所以【两种注入形态**】
```

### 7.1 ⭐⭐ **"两种注入形态：七个单函数 + 两个 struct"**

**✅ 与 §420 的"`SvServerWorld` 约 `15` 个 `std::function` 注入点"**同族**——但这里给出了"为什么一个用 struct"**。

**⇒ 三层**：
```text
`MatchScoreCallbacks` ⇒ **六个回调**（`addClientScore`/`addClientXp`/`addTeamScoreForClient`/`addKillForClient`/`addDeathForClient`/`addAssistForClient`/`isBotClient`/`playSoundForClient`）= **八个**
`MissionCallbacks` ⇒ **三个**（`sendServerCommand`/`setConfigString`/`finishMission`）
⇒ **⇒ 所以【一个 struct 打包多个相关回调**】
```

**✅ ⭐⭐ **"一个 struct 打包多个相关回调"** —— 与 §420 的"`SvServerWorld` 的 `15` 个独立 `std::function`"**相反**。

**⇒ 三层**：
```text
`SvServerWorld` ⇒ **`15` 个独立注入**（**各自一个 `set*`**）
`SvScriptBuiltinRegistry` ⇒ **两个 struct**（**一个构造器**）
⇒ **⇒ 所以【两个不同的风格**】
```

**⚠ 一个**风格的不一致**（**而理由可能是"注册表【一次性构建**，而世界【增量配置**"）。**

**✅ ⭐⭐ **"一次性构建 vs 增量配置"** —— 一个**可推导的理由**。

## 八、关键结论

1. **⭐⭐⭐ `method:playsound` 的完整病历**：**"现有内建 ID 带 `method:` 前缀，我原来只写了 `"playsound"`，于是 Lua 的 `codol.call("method:playsound", 62)` 【永远解析不到】——日志实证 `kill sound special skipped series=tank` ×3（系列判定对、武器确实是 `honeybadgertank_mp`、只是调用失败）"`** —— 第五次"一个特性从未工作"。
2. **⭐⭐⭐ "完全正确而完全不可达"**：**系列判定对、武器对，只有名字错** —— 而**一个功能可以完全正确而完全不可达**。
3. **⚠⚠⚠ 一个真实的结构性矛盾（我发现）**：**`method:playsound` 是全部 `56` 个注册里【唯一**一个名字带 `method:` 前缀的**，而注释声称 `"method:delete"` / `"method:getorigin"` / `"method:adddeath"` 也带前缀 —— **而它们的实际注册是【无前缀**的**。所以**要么那个修正是对的（其他 55 个都错），要么它仍然错** —— 而 `invoke` 直接用 `name` 查（`handlers_.find({kind, name})`）⇒ **一个 `"method:playsound"` 的注册只能被一个 `name == "method:playsound"` 的调用命中**。
4. **⭐⭐ "那个日志行（`skipped series=tank`）是一个判据"`** —— 若修正对，它应消失 —— 第四次"一个可判定的判据"。
5. **⭐⭐⭐ `method:playsound` 的第二次修正**：**"Lua 的数字是 `double`，原来只 `get_if<std::int64_t>` ⇒ 传 `62` 会被判 `InvalidArgumentValue`（日志只剩 `skipped`，看不到原因）"`** —— 与 §447 的"`setLoot` 的一个数字两种拼写"**同族**，而**这里的理由更精确**。
6. **⚠⚠ 一个可推导的缺陷（我发现）**：**若"Lua 的数字是 `double`"这个声明成立，则 `zmsetround(5.0, 8.0)`（只接受 `int64_t`，§439）会失败** —— **同一个文件里一个声明与另一处的实现矛盾**。
7. **⭐⭐⭐ `addkill` 的"第一次击杀就结束比赛"**：**"`cha` 把【显示分数】（`addscore 100`）与【限制读的计数器】（`addteamscore 1`）分开；自由混战没有队伍放第二个 ⇒ 剩下的唯一计数器是那个每杀 `100` 的显示分数，【它在一个 `30` 的限制上第一次击杀就跨过】⇒ 而【结束了每一场比赛，立即**】"`** —— **"显示 vs 限制是两个字段"**，混用会导致立即结束。
8. **⭐ 六个 `add*` 的 `delta` 界 `±1'000'000` 与 §431 的十个累加器的 `clamp(0, 1'000'000)` 同值** —— 一个常量复用。
9. **⭐⭐⭐ 六个 `add*` 的"完全同构，唯一的差异是那个回调名，而【没有抽**】"** —— 与 §448 的"`readInteger` 抽成模板"**在同一文件里相反** ⇒ **"抽与不抽由复杂度决定，不由次数"那个判据在这里被验证**。
10. **⭐ "纯服务端，不碰任何客户端可见下发（dvar / configstring）"`** —— 第三次"范围的声明"（与 §403、§435 同族）。
11. **⭐⭐⭐ `invoke` 的 `UnknownBuiltin` 与 §449 的 `isbot` 的 `false` 是两个不同的处置**（**一个名字错了 vs 一个有意义的答案**）；而**"日志实证 `kill sound special skipped`"说明 `invoke` 的 `UnknownBuiltin` 在 Lua 侧【被降级为 `skipped`**】** ⇒ **"一个错误在 Lua 侧被吞"**。
12. **⭐⭐ 两种注入形态**：`SvServerWorld` 的 `15` 个独立 `set*` 与 `SvScriptBuiltinRegistry` 的两个 struct（`MatchScoreCallbacks` 八个 + `MissionCallbacks` 三个）⇒ **"一次性构建 vs 增量配置"**。

## 九、`sv_script_builtin_mp.cpp` 全文件总览

**行数：`4,424`**。**`56` 个内建**（`26` 个 `Function` + `30` 个 `Method`）。

**十二个功能域**：

| 域 | 内建 |
|---|---|
| **ZM 区域/出生** | `zmzonecount` / `zmzonename` / `zmzonespawncount` / `zmzoneactive` / `zmactivezonecount` / `zmspawnorigin` / `zmspawnangles` / `zmzoneat` / `zmplayercount` / `zmplayerzone` / `zmzoneadjacentcount` / `zmzoneadjacentat` / `zmspawncrossesbarrier` / `zmcooperativezonesource` / `zmcooperativespawnzones` |
| **ZM actor** | `zmspawnactor` / `zmspawnactorat` / `zmspawngoal` / `precachemodel` / `zmsetround` |
| **实体** | `spawnmodel` / `setmodel` / `setmodelat` / `sethealth` / `setcandamage` / `delete` / `getorigin` / `getvelocity` / `getentitynumber` / `getmapfield` / `istouching` / `getentarray` / `setmapgameobjects` |
| **玩家** | `giveweapon` / `setplayerweapons` / `setplayerweaponammo` / `setweaponammoclip` / `setweaponammostock` / `isonground` / `issameteam` / `respawn` / `savecheckpoint` / `isbot` |
| **伤害** | `finishplayerdamage` / `finishsharedplayerdamage` |
| **计分** | `addscore` / `addxp` / `addteamscore` / `addkill` / `adddeath` / `addassist` |
| **脚本位置** | `setscriptedposition` / `setscriptedviewangles` / `setscriptedviewclamp` / `setscriptedlinkstate` / `clearscriptedposition` / `setshellshock` / `setobjective` |
| **战役 actor** | `spawnactor` / `setactorstate` / `setactorposition` / `setactorpositions` / `actorfire` / `actortracedamage` / `actorfirepresentation` / `actorcorpse` / `setagentfield` / `suppresscorpse` |
| **投掷物** | `spawnscriptedmissile` / `setscriptedmissile` |
| **FX/音效** | `playfxat` / `playfxontag` / `playsoundat` / `effectindex` / `weaponindex` / `firemagicat` / `triggerexploder` / `earthquakeat` / `physicsexplosionsphereat` / `radiusdamageat` / `playanimation` |
| **战役控制** | `sendservercommand` / `setconfigstring` / `servertime` / `finishmission` |
| **地面倾斜** | `spawngroundtiltcontroller` / `setgroundtilttrajectory` / `playersetgroundreferenceent` |
| **拾取** | `setloot` / `method:playsound`（**唯一带前缀的**） |

**十个错误码**：
```text
None / InvalidArgumentCount / InvalidArgumentType / InvalidArgumentValue
MissingSelf / InvalidSelf / ObjectNotFound / InvalidObjectState
WeaponNotOwned / InvalidAmmoState / WorldMutationFailed
DeathTransitionUnavailable / MatchStateUnavailable / UnknownBuiltin
```

**十四个"零/空/否是一个合法答案"的实例**：
```text
zmSpawnGoal 的 ""（42/74 没有 goal）
zmZoneAt / zmPlayerZone 的 ""（在每一区域之外）
zmSpawnCrossesBarrier 的 0（没有目标）
zmCooperativeSpawnZones 的 ""（opt-in 关闭）
getMapEntityField 的 monostate（字段缺失）
spawnModel 的 monostate（池满）
isbot 的 false（没有回调）
setloot 的 return（…）
actorFire 的 success(false)（目标不在 Playing / 没有 trace / 长度为零）
actorCorpse 的 true
```

## 十、未闭合点

- `method:playsound` 的 `method:` 前缀是否是一个真实缺陷（与其它 55 个不一致）。
- "Lua 的数字是 double"与 `zmsetround` 只接受 `int64_t` 的矛盾。
- `MatchScoreCallbacks` 与 `MissionCallbacks` 的完整字段。
- `SvScriptObjectKind` 的完整枚举。
- `SvScriptValue` 的完整 `variant`。
- **下一步**：`sv_zm_navgraph_bo1_hybrid_table_mp.cpp`（`316,361` 字节）。
