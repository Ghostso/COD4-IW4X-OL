# 449 · **"一个内建两个名字，由 `publishPresentation` 区分"** —— `actorfire`/`actortracedamage` 的同一函数、`isbot` 的"没有回调就答 `false`"、以及 `servertime` 的读取

## 一、范围

本报告学习 `sv_script_builtin_mp.cpp` 3760–4100 行（注册表的全部 `emplace`、`actorfire`/`actortracedamage` 的一个函数两个名字、`isbot`、`sendservercommand`、`setconfigstring`、`servertime`、`finishmission`）。

## 二、**"一个内建两个名字，由 `publishPresentation` 区分"**（本组最重要的一段）

### 2.1 那段

```cpp
handlers_.emplace(
    SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "actorfire" },
    [this](SvServerWorld &world, const SvScriptBuiltinCall &call) {
        return actorFire(world, call, weaponResolver_, true);
    });
handlers_.emplace(
    SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "actortracedamage" },
    [this](SvServerWorld &world, const SvScriptBuiltinCall &call) {
        return actorFire(world, call, weaponResolver_, false);
    });
```

### 2.2 二十层

```text
1. **两个名字：`actorfire` 与 `actortracedamage`**
2. ⇒ **而【它们调用【同一个 `actorFire`**】】
3. ⇒ **`actorfire` ⇒ `publishPresentation = true`**
4. ⇒ **`actortracedamage` ⇒ `publishPresentation = false`**
5. ⇒ **⇒ 所以【一个函数，一个 `bool`，两个内建**】
6. ⇒ **⇒ 而 `actorFirePresentation` 【是第三个**入口】（**只发表现，无伤害**）**
7. ⇒ **⇒ 所以【三个内建，一个实现 + 一个 `bool`**】
```

### 2.3 ⭐⭐⭐ **"三个内建，一个实现 + 一个 `bool`"**

**✅ 这是本报告里**最重要的一条"用 `bool` 拆分一个 API**。**

**✅ 与 §447 的"任务可以独立地发布那个表现，从它的每一次连发的一次伤害尝试"**——**完全闭合** ✓

**⇒ 三层**：
```text
`actorfire`             ⇒ **伤害 + 表现**
`actortracedamage`      ⇒ **只有伤害**（**"一个 trace 伤害"**）
`actorfirepresentation` ⇒ **只有表现**
⇒ **⇒ 所以【三种组合【三个名字**】
```

**✅ ⭐⭐⭐ **"三种组合三个名字"** —— 而 **`(1,0)` / `(0,1)` / （`1,1`）= `actorfire`**。

**⇒ 三层**：
```text
`(damage=true, presentation=true)`  ⇒ `actorfire`
`(damage=true, presentation=false)` ⇒ `actortracedamage`
`(damage=false, presentation=true)` ⇒ `actorfirepresentation`
`(damage=false, presentation=false)` ⇒ **不存在**（**无意义**）
⇒ **⇒ 所以【三个组合中的三个**】
```

**✅ ⭐⭐⭐ **"三个组合中的三个"** —— 而**第四个组合被省略**（**无意义**）。

**⚠ 而"`actortracedamage` 的名字"⇒ **一个"trace 伤害"**。**

**⇒ 三层**：
```text
`actortracedamage` ⇒ **"一个 `trace` + 伤害"** ⇒ **而【没有表现**】
⇒ **⇒ 所以【这个名字【精确描述了它的行为**】
```

**✅ ⭐⭐ **"名字精确描述行为"** —— 与 §442 的 `weaponindex` 的"is a function"**同族（**第三次"名字即文档**）。

## 三、**`isbot` 的"没有回调就答 `false`"**（本组第二重要）

### 3.1 那段

```php
// 28800: method:isbot -- answers from the network client slot, which
// only ServerCore owns. A registry that was built without the callback
// answers false rather than failing, so an older wiring cannot break
// the gametype script.
handlers_.emplace(
    SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "isbot" },
    [this](SvServerWorld &world, const SvScriptBuiltinCall &call) {
        std::optional<SvPlayerState> playerState;
        if (const auto invalid = validatePlayerMethod(world, call, 0, playerState))
            return std::move(*invalid);
        const std::uint32_t clientNum = call.self->id;
        return success(
            matchScoreCallbacks_.isBotClient &&
            matchScoreCallbacks_.isBotClient(clientNum));
    });
```

### 3.2 十八层

```text
1. **`isbot` 从【网络客户端槽**】回答**
2. ⇒ **而那个槽【只有 `ServerCore` 拥有**】**
3. ⇒ **⇒ 所以【它【通过一个回调**问**
4. ⇒ **⚠ 一个【没有那个回调**】构建的注册表【答 `false`**】**
5. ⇒ **⇒ 而不是【失败**】**
6. ⇒ **⇒ 所以【一个【更旧的接线**】不能【弄坏**】那个 gametype 脚本**
```

### 3.3 ⭐⭐⭐ **"一个没有那个回调的注册表答 `false` 而不是失败，所以一个更旧的接线不能弄坏那个 gametype 脚本"**

**✅ 与 §438 的"`zmZoneModel` 的 `!provider ⇒ failure`"**——**相反** ✓

**⇒ 三层**：
```text
§438  **`!provider` ⇒ `failure(InvalidObjectState, "... has no zone provider")`**
§449  **`!isBotClient` ⇒ `false`**（**不失败**）
⇒ **⇒ 所以【两个相反的处置**】
```

**✅ ⭐⭐⭐ **"两个相反的处置"** —— 而**理由不同**：

**⇒ 三层**：
```text
`zmZoneModel` ⇒ **没有 provider ⇒ 那个内建【完全无法工作**】（**一个结构性缺失**）
`isbot` ⇒ **没有回调 ⇒ 只能答 `false`**（**而 `false` 是一个【合法的答案**】）
⇒ **⇒ 所以【"能否给出一个有意义的答案**】决定**
```

**✅ ⭐⭐⭐ **"能否给出一个有意义的答案"** —— 本报告最精确的判据。

**⚠ 而"`false` 是一个合法的答案"⇒ **因为"不是 bot"是【最常见的**情况**。**

**⇒ 三层**：
```text
一个【真人玩家**】⇒ `isBot = false`
⇒ **⇒ 所以【那个默认答案【对多数情况【正确**】】
```

**✅ 与 §440 的"`""` 让容错成为可能"**同族（**第五次"一个默认答案的合理性**。

**⇒ 三层**：
```text
§440  **`zmzoneat` 的 `""`**
§447  **`spawnmodel` 的 `nil`**
§449  **`isbot` 的 `false`**
⇒ **⇒ 三次"一个默认答案**】
```

**✅ ⭐⭐ **一个"默认答案"的三例表**。

**⚠ 而"两处 `missionCallbacks_` 的 `!callback || !callback(...)`"⇒ **同样的宽容**。**

```cpp
if (!missionCallbacks_.sendServerCommand || !missionCallbacks_.sendServerCommand(...))
    ⇒ MatchStateUnavailable
if (!missionCallbacks_.setConfigString || !missionCallbacks_.setConfigString(...))
    ⇒ MatchStateUnavailable
if (!missionCallbacks_.finishMission || !missionCallbacks_.finishMission())
    ⇒ MatchStateUnavailable
```

**⇒ 三层**：
```text
三个 `missionCallbacks_` ⇒ **都没有 ⇒ `MatchStateUnavailable`**
⇒ **⇒ 而那个名字【说"比赛状态不可用"**】⇒ **一个准确的描述**
```

**✅ ⭐⭐ **"一个准确的描述"** —— 而 **`isbot` 是**唯一的**例外**（**`false` 而不是错误**）。

**⇒ 三层**：
```text
`isbot` ⇒ **`false`**（**一个合法的答案**）
`sendServerCommand`/`setConfigString`/`finishMission` ⇒ **`MatchStateUnavailable`**（**无法完成请求**）
⇒ **⇒ 所以【四种"没有回调"，两种处置**】
```

**✅ ⭐⭐⭐ **"四种『没有回调』，两种处置"** —— **由"能否给出一个答案"决定**。

## 四、**`sendservercommand` 的 `1024` 与 `setconfigstring` 的 `1000`**（本组第三重要）

```cpp
// sendservercommand
if (!command || command->empty() || command->size() >= 1024 ||
    command->find('\0') != std::string::npos)
    ⇒ "sendservercommand expects a non-empty command shorter than 1024 bytes"

// setconfigstring
if (!index || !value || *index < 0 || *index > UINT16_MAX ||
    value->size() >= 1000 || value->find('\0') != std::string::npos)
    ⇒ "setconfigstring expects a uint16 index and value shorter than 1000 bytes"
```

**⇒ 十层**：
```text
1. **`sendservercommand` ⇒ `< 1024`**
2. ⇒ **`setconfigstring` ⇒ `< 1000`**
3. ⇒ **⇒ 两个不同的上界**】
4. ⇒ **⇒ 而 §425 的 `parseUserInfo` 是 `<= 1024`**
5. ⇒ **⇒ 所以【三个不同的界**】
```

### 4.1 ⭐⭐⭐ **"`1024` / `1000` / `1024`（`<=` vs `<`）"**

**✅ 与 §442 的"三个长度上界（`128`/`64`/`64`）"**同族（**第七次"界由语义决定"）。

**⇒ 三层**：
```text
§442  **`weaponIndex`/`effectIndex` ⇒ `< 128`；`getEntArray`/`getMapEntityField` ⇒ `<= 64`；`setMapGameObjects` ⇒ `<= 64`**
§449  **`sendservercommand` ⇒ `< 1024`；`setconfigstring` ⇒ `< 1000`；`parseUserInfo` ⇒ `<= 1024`**
⇒ **⇒ 两次"三个界**】
```

**✅ ⭐⭐ **"三个界"两次**。

**⚠ 而"`setconfigstring` 的 `< 1000`"⇒ **而 §430 的 `SV_SetConfigString` 是 `< 1024`**。**

**⇒ 三层**：
```text
§430  **`SV_SetConfigString`：`command.size() >= 1024 ⇒ return 0`**（**那是 `"d " + index + " " + value` 的总长**）
§449  **`setconfigstring` 的 `value.size() >= 1000`**（**只是值**）
⇒ **⇒ 所以【`1000` 是【为命令前缀**留的空间**】**
```

**✅ ⭐⭐⭐ **"`1000` 是为命令前缀留的空间"** —— 一个**可推导的理由**（`"d " + 5 位索引 + " " = 8 字节`，**`1000 + 8 < 1024`**）。

**✅ 与 §433 的"`1021 <= 1022` 只差 `1` 字节"**同族（**第二次"预算的算术**）。

**⇒ 三层**：
```text
§433  **`1185 - 164 = 1021 <= 1022`**（**差 `1`**）
§449  **`1000 + 8 = 1008 < 1024`**（**差 `16`**）
⇒ **⇒ 两次"预算的算术**】
```

**✅ ⭐ **一个"预算算术"的两例**。

## 五、**`servertime` 的 `snapshot().serverTime`**（本组第四重要）

```cpp
handlers_.emplace(
    SvScriptBuiltinId{ SvScriptBuiltinKind::Function, "servertime" },
    [](SvServerWorld &world, const SvScriptBuiltinCall &call) {
        if (call.self) ⇒ InvalidSelf "servertime is a function"
        if (!call.arguments.empty()) ⇒ InvalidArgumentCount
        return success(static_cast<std::int64_t>(world.snapshot().serverTime));
    });
```

**⇒ 十层**：
```text
1. **`servertime` 返回 `snapshot().serverTime`**
2. ⇒ **⚠ 而 §440 说"在那个区间里 `snapshot().playerStates` 刻意地是空的**】**
3. ⇒ **⇒ 所以【`snapshot().serverTime` 【是【有效的**】】**
4. ⇒ **⇒ 因为【只有 `playerStates` 是【在 `endFrame` 才组装的**】**
```

### 5.1 ⭐⭐⭐ **"`snapshot().serverTime` 有效而 `snapshot().playerStates` 空"**

**✅ 与 §440 的"`zmPlayerCount` 必须用 `playerState()` 而不是 `snapshot()`"**——**精确对照** ✓

**⇒ 三层**：
```text
`snapshot().serverTime`   ⇒ **有效**（**一个标量，在 `beginFrame` 就设了**）
`snapshot().playerStates` ⇒ **空**（**一个向量，在 `endFrame` 组装**）
⇒ **⇒ 所以【同一个快照【两个字段两个时机**】
```

**✅ ⭐⭐⭐ **"同一个快照的两个字段两个时机"** —— 一个**极精确的实现细节**。</br>

**✅ 与 §444 的"`world.snapshot().serverTime` 在 `setgroundtilttrajectory`"**、§445 的"`readScriptedMissileState`"**、§447 的"`playAnimation` 的 `startTime`"**完全一致 ✓

**⇒ 三层**：
```text
§444  **`setgroundtilttrajectory` ⇒ `snapshot().serverTime`**
§445  **`readScriptedMissileState` ⇒ `snapshot().serverTime`**
§447  **`playAnimation` ⇒ `snapshot().serverTime`**
§449  **`servertime` ⇒ `snapshot().serverTime`**
⇒ **⇒ 四次"用 `snapshot().serverTime`"**
```

**✅ ⭐⭐ **"四次用同一个读取"** —— 而 **§440 的 `zmPlayerCount` 用 `playerState()`**（**因为它需要 `playerStates`**）。

**⇒ 三层**：
```text
`serverTime` ⇒ **`snapshot()`**（**一个标量**）
`playerStates` ⇒ **`playerState()`**（**一个向量**）
⇒ **⇒ 所以【两个读取器，两种字段**】
```

**✅ ⭐⭐⭐ **"两个读取器，两种字段"** —— 本报告的核心洞察。

## 六、`finishmission` 的 `MatchStateUnavailable`

```php
if (!missionCallbacks_.finishMission || !missionCallbacks_.finishMission())
    ⇒ MatchStateUnavailable "finishmission is unavailable outside an active campaign mission"
```

**⇒ 六层**：
```text
1. **没有回调 ⇒ `MatchStateUnavailable`**
2. ⇒ **而【消息说"在一个活跃的战役任务之外不可用"**】**
3. ⇒ **⇒ 所以【一个非战役的地图【调用它 ⇒ 得到一个【准确的错误**】】
```

**✅ 与 §449 三.3 的"四种没有回调两种处置"**完全一致 ✓

**⇒ 三层**：
```text
`finishMission` ⇒ **只有在战役里存在** ⇒ **一个人可以理解的错误消息**
⇒ **⇒ 所以【"不可用"这个措辞【精确**】
```

**✅ ⭐⭐ **"不可用这个措辞精确"**。

## 七、`setconfigstring` 的 `uint16` 索引

```php
*index < 0 || *index > std::numeric_limits<std::uint16_t>::max()
```

**⇒ 六层**：
```text
1. **索引是 `0..65535`**
2. ⇒ **⇒ 而 §413 的 `SV_SetConfigString` 的 `index` 是 `std::uint16_t`**
3. ⇒ **⇒ 所以【一致**】
```

**✅ ⭐⭐ **"一致"** —— 而 **§414 的配置串带最大是 `12278`**（**`12254..12278`**）⇒ **远小于 `65535`**。

**⇒ 三层**：
```text
`uint16` ⇒ **`0..65535`**
而【实际最大带 ⇒ `12278`**】
⇒ **⇒ 所以【`uint16` 【有一个充足的上界**】
```

**✅ ⭐ **一个"上界充足"的实例**。

## 八、关键结论

1. **⭐⭐⭐ "三个内建，一个实现 + 一个 `bool`"**：`actorfire`（`publishPresentation=true`）/ `actortracedamage`（`=false`）/ `actorfirepresentation`（**只发表现，无伤害**）⇒ **三个组合三个名字**，而**第四个组合（`false`/`false`）不存在**（**无意义**）。
2. **⭐ "`actortracedamage` 的名字精确描述了它的行为（一个 `trace` + 伤害，没有表现）"`** —— 第三次"名字即文档"（与 §442 同族）。
3. **⭐⭐⭐ `isbot` 的"一个没有那个回调的注册表答 `false` 而不是失败，所以一个更旧的接线不能弄坏那个 gametype 脚本"`** —— **与 §438 的 `zmZoneModel` 的 `!provider ⇒ failure` 相反** ⇒ **判据是"能否给出一个有意义的答案"**（**`false` 是一个合法的答案，而 `zmZoneModel` 没有 provider 就什么也答不了**）。
4. **⭐⭐ "四种『没有回调』，两种处置"**：`isbot` ⇒ `false` / `sendServerCommand`/`setConfigString`/`finishMission` ⇒ `MatchStateUnavailable` —— **由"能否给出一个答案"决定**。
5. **⭐⭐ "一个默认答案"的第三例**：`zmZoneAt` 的 `""`（§440）/ `spawnModel` 的 `nil`（§447）/ `isbot` 的 `false`（§449）。
6. **⭐⭐⭐ 三个长度上界**：`sendservercommand` 的 `< 1024` / **`setconfigstring` 的 `< 1000`** / `parseUserInfo` 的 `<= 1024`，而 **§430 的 `SV_SetConfigString` 是 `< 1024`（总长）** ⇒ **"`1000` 是为命令前缀留的空间"**（`1000 + 8 < 1024`）—— 一个**可推导的理由**。
7. **⭐⭐⭐ "同一个快照的两个字段两个时机"**：**`snapshot().serverTime` 有效（一个标量，在 `beginFrame` 就设了）而 `snapshot().playerStates` 空（一个向量，在 `endFrame` 组装）** —— 与 §440 的"`zmPlayerCount` 必须用 `playerState()`"**精确对照**。
8. **⭐⭐ "四次用同一个读取"**：`setgroundtilttrajectory`（§444）/ `readScriptedMissileState`（§445）/ `playAnimation`（§447）/ `servertime`（§449）**都用 `world.snapshot().serverTime`**，而**`zmPlayerCount`（§440）用 `playerState()`** ⇒ **两个读取器，两种字段**。
9. **⭐ `finishmission` 的 `MatchStateUnavailable` 消息"unavailable outside an active campaign mission"精确**。
10. **⭐ `setconfigstring` 的 `uint16` 索引与 §413 的 `SV_SetConfigString` 的 `index` 类型一致**，而**实际最大带 `12278` 远小于 `65535`** ⇒ 上界充足。

## 九、未闭合点

- `MatchScoreCallbacks` 与 `MissionCallbacks` 的完整定义。
- `isBotClient` 与 `SvClientSlot::isBot` 的关系。
- `sendservercommand` 的目标（只发给 `call.self->id`）。
- `setconfigstring` 的 `MissionCallbacks::setConfigString` 是否就是 `SvClientSystem::SV_SetConfigString`。
- `sv_script_builtin_mp.cpp` 4100 行之后未读取（**共 `4424` 行**）。
