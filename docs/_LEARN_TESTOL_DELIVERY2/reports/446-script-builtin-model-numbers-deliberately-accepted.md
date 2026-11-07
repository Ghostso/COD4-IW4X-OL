# 446 · **"Model 号在这里被刻意接受，因为这是从录像测出的地图专属配置串索引"** —— `spawnActor` 的五个界、`setActorPositions` 的 `4 + 5n` 形状、以及 `Ev_FIRE_WEAPON` 的"表现与伤害分离"

## 一、范围

本报告学习 `sv_script_builtin_mp.cpp` 2740–3080 行（`radiusDamageAt` 的四个正数、`spawnActor` 的五个界、`setActorState`、`setActorPosition`、`setActorPositions` 的 `4 + 5n`、`actorFire` 的开头）。

## 二、**"Model 号在这里被刻意接受"**（本组最重要的一段）

### 2.1 那段

```php
// Materialize one of the campaign map's actor spawners. The map entity
// contributes the authored origin and angles. AgentState +0x04 is the
// spawned entity number and is filled transactionally by spawnActor.
//
//     local actor = codol.call("method:spawnactor", spawner,
//         slot, model, team, animation, animation_start_time)
//
// Model numbers are deliberately accepted here because this is the
// map-specific model configstring index measured from the recording.
```

### 2.2 二十层

```text
1. **物化战役地图的一个 actor spawner**
2. ⇒ **地图实体【贡献作者的 `origin` 与 `angles`**】**
3. ⇒ **`AgentState +0x04` 是【被生成的实体号**】** ⇒ **由 `spawnActor` 事务性地填**
4. ⇒ **用法**：`codol.call("method:spawnactor", spawner, slot, model, team, animation, animation_start_time)`
5. ⇒ **⚠ 【Model 号在这里【被刻意接受**】】**
6. ⇒ **⇒ 因为【这是【从录像测出的、地图专属的**】模型 configstring 索引**
```

### 2.3 ⭐⭐⭐ **"Model 号在这里被刻意接受，因为这是从录像测出的地图专属索引"**

**✅ 这是本报告里**最重要的一个"按名字 vs 按数字"的例外**。**

**✅ 与 §439 的"模型被命名，从不被编号"**——**这是一个例外，而有理由** ✓

**⇒ 三层**：
```text
通用规则 ⇒ **模型被命名，从不被编号**（§439）
例外 ⇒ **`spawnactor` 接受一个数字**
理由 ⇒ **它是【从录像测出的、地图专属的**】
⇒ **⇒ 所以【一个例外只有在【它被测量**时才是合法的**】
```

**✅ ⭐⭐⭐ **"一个例外只有在它被测量时才是合法的"** —— 一个**极重要的判据**。

**⇒ 三层**：
```text
§414  **"按名字从不按零售的数字"**（`modelResolver`）
§417  **"从不 demo 的字面 `287`"**
§439  **"模型被命名，从不被编号"**
§446  **例外：`spawnactor` 的 model 是一个【从这个地图的录像**测出的号**】
⇒ **⇒ 所以【例外是【一个有测量支撑的特例**】
```

**✅ ⭐⭐⭐ **一个"测量支撑的例外"** —— 与 §417 的"从不 demo 的字面 `287`"**形成精确对照**（**那里拒绝，这里接受，区别是"这是否是一个被测量的地图专属值"**）。

**⚠ 而"地图专属"⇒ **一个关键限定**。**

**⇒ 三层**：
```text
若【一个数字是【地图专属**的】⇒ **只对那个地图有效** ⇒ **脚本必须知道它在哪个地图上**
⇒ **⇒ 所以【`spawnactor` 【只能在战役地图上用**】
```

**✅ 与 §417 的"这个服务器的带索引"**不同（**那是一个【从这个服务器解出的**号**）。

**⇒ 三层**：
```text
§417  **`actorField009C` = 从【名字】解出的【这个服务器的】**带索引
§446  **`spawnactor` 的 `model` = 从【录像】测出的【那个地图的】**号
⇒ **⇒ 两个不同的来源，两种合法性**
```

**⚠ 一个**需要标注的区别**（**而注释说"deliberately accepted here"，承认了它**）。

### 2.4 而**五个界**

```cpp
constexpr std::array<std::uint32_t, 5> Maximum{
    23, 0x3FF, 0x7FF, 0xFFF,
    std::numeric_limits<std::uint32_t>::max(),
};
// slot = values[0], model = values[1], team = values[2], animation = values[3],
// animation_start_time = values[4]
agent.agentNum = values[0];
agent.fields[SvAgentState::ModelField]            = values[1];
agent.fields[SvAgentState::TeamField]             = values[2];
agent.fields[SvAgentState::AnimationField]        = values[3];
agent.fields[SvAgentState::AnimationStartTimeField] = values[4];
```

**⇒ 十六层**：
```text
1. **`slot`（`agentNum`）⇒ `0..23`**
2. ⇒ **`model` ⇒ `0..0x3FF`**（**`10` 位**）
3. ⇒ **`team` ⇒ `0..0x7FF`**（**`11` 位**）
4. ⇒ **`animation` ⇒ `0..0xFFF`**（**`12` 位**）
5. ⇒ **`animation_start_time` ⇒ `0..UINT32_MAX`**
6. ⇒ **⇒ 五个界，四个来自位宽，一个来自池大小**
```

### 2.5 ⭐⭐⭐ **"`slot` 是 `0..23` 而 §415 说 `32` 个槽"**

**✅ 这是本报告里**最重要的一处数值差异**。**

**⇒ 三层**：
```text
§415  **"`sub_530C30` 用 `cmp ecx, 20h` 遍历 ⇒ `32` 是硬计数"**
§416  **`SvAgentSlotCount = 32`**
§446  **`spawnactor` 的 `slot` ⇒ `0..23`**
⇒ **⇒ 三个数：`32` / `32` / `24`**
```

**⚠ 一个**真实的差异**（**`24` vs `32`**）。

**⇒ 三种可能的解释**：
```text
① `24` 是【战役**的上限（`Wetwork` 的 `24` 个 agent）
② `24` 是【一个笔误**（应该是 `31` 或 `32`）
③ 而 §415 说"**retail delta-codes `31` of them**" ⇒ **`31` 是实际使用数**
```

**⚠ 一个**需要标注的未闭合**（**`23` 可能是"`24` 个槽，零到基"，而 `32` 是"客户端数组的大小"**）。

**✅ 与 §415 的"`32` 是硬计数，而 retail delta-codes `31` of them"**配合。

**⇒ 三层**：
```text
客户端数组 ⇒ **`32`**
retail 实际用 ⇒ **`31`**
`spawnactor` 的 `slot` ⇒ **`0..23`（`24` 个）**
⇒ **⇒ 所以【`24` 可能是【一个更保守的**上界**】
```

**✅ ⭐⭐ **"一个更保守的上界"** —— 与 §438 的"界比实际值宽"**相反**（这是**窄**）。

**⇒ 三层**：
```text
§442  **`giveweapon` 的界比 `a` 宽**
§444  **`triggerexploder` 的界比 demo 宽**
§446  **`spawnactor` 的 `slot` 界比客户端数组窄**
⇒ **⇒ 三次"界与实际的差异"，两个方向**
```

**✅ ⭐⭐⭐ **一个"界与实际"的三例表（两个方向）**。

**⚠ 而 `model` 是 `0x3FF`（`10` 位）**⇒ **与 §415 的"`ModelField` 是 `10` 位"**完全吻合 ✓

**⇒ 三层**：
```text
§415  **"agentState field 8, +0x00C, TEN BITS"**
§446  **`model` 的 `Maximum` 是 `0x3FF`**
⇒ **⇒ 完全一致**
```

**✅ ⭐ **一个"位宽"的确认**。

**⚠ 而 `team` 是 `0x7FF`（`11` 位）**⇒ **而 `SvTeam` 只有 `0..3`**。**

**⇒ 三层**：
```text
`team` 的界 ⇒ **`0..0x7FF`**（`11` 位）
而 `SvTeam` ⇒ **`None`/`Tf`/`Sc`/`Spectator` = `0..3`**
⇒ **⇒ 所以【这个界【远宽于**实际需要的】
```

**⚠ 一个**宽了 `8` 个数量级**的界**（**标注**）。

**✅ 与 §415 的"`TeamField = 21`，`+0x004`，`11` 位"**——**而 `unk_DA9920 + 0x008 = 2`**。

**⇒ 三层**：
```text
§415  **`TeamField` 是索引 `21`，而 `unk_DA9920` 的 `+0x008 = 2`**
§446  **`team` 的界是 `0x7FF`（`11` 位）**
⇒ **⇒ 所以【那个字段确实是 `11` 位而只有 `0..3` 有意义**】
```

**✅ ⭐⭐ **一个"位宽 vs 语义范围"的区分**。

## 三、**`setActorPositions` 的 `4 + 5n` 形状**（本组第二重要）

### 3.1 那段

```php
// Move Wetwork's helicopter cast with one collision/native mirror
// rebuild. Arguments are the receiver's x/y/z/yaw followed by repeated
// (actor, x, y, z, yaw) groups.
if (call.arguments.size() < 4 || (call.arguments.size() - 4) % 5 != 0)
    ⇒ "setactorpositions received an invalid argument count"
```

### 3.2 二十层

```text
1. **形状：`4 + 5n`**
2. ⇒ **头四个 ⇒ 接收者的 `x/y/z/yaw`**
3. ⇒ **然后【重复的 `(actor, x, y, z, yaw)` 组**】**
4. ⇒ **⇒ 所以【`4` 个后【每 `5` 个**一组】
5. ⇒ **而 `(size - 4) % 5 != 0` ⇒ 拒绝**
6. ⇒ **⇒ 一个【模数**形状检查】
```

### 3.3 ⭐⭐⭐ **"一个 `4 + 5n` 的模数形状检查"**

**✅ 与 §442 的 `setPlayerWeapons` 的 `3` 或 `4`**不同（这是**一个任意长度的重复组**）。

**⇒ 三层**：
```text
§439/§442/§444  ⇒ **固定个数或"`n` 或 `n+1`"**
§446  ⇒ **`4 + 5n`**（**一个任意长度的重复**）
⇒ **⇒ 所以【参数形状【第三个种类**】
```

**✅ ⭐⭐ **"参数形状的第三个种类"**。

**⚠ 而"一个 `collision/native mirror rebuild`"⇒ **一个性能动机**。**

**✅ 与 §422 的"`setActorTransforms` 一次事务"**完全闭合 ✓

**⇒ 三层**：
```text
§422  **"Wetwork 在直升机上携带七个 actor 而每 `100ms` 一起更新它们；七个独立的变更重建完整的碰撞/原生镜像七次，而让脚本相机的时间线饥饿"**
§446  **`setActorPositions` 的 `4 + 5n` 一次提交**
⇒ **⇒ 同一个动机的两个层次**
```

**✅ ⭐⭐⭐ **一个"性能动机"的完整闭环**。

**⚠ 而"`transforms.reserve(1 + (size - 4) / 5)`"⇒ **一个精确的预留**。**

**⇒ 三层**：
```text
`1` ⇒ **接收者**
`(size - 4) / 5` ⇒ **组数**
⇒ **⇒ 所以 `reserve` 恰好**
```

**✅ ⭐ **一个"精确预留"的实例**。</br>

**✅ 与 §411 的"零新增分配"**同族（**第三次"避免分配**）。

### 3.4 而**`appendTransform` 是一个 lambda 返回 `optional<Result>`**

```cpp
const auto appendTransform = [&](const SvEntityHandle actor, const std::size_t valueOffset)
    -> std::optional<SvScriptBuiltinResult> {
    if (!world.entity(actor)) return failure(ObjectNotFound, "...");
    for (axis 0..2) { double, isfinite }
    yaw = ...
    transforms.push_back({ .actor = actor, .origin = origin, .angles = { 0, yaw, 0 } });
    return std::nullopt;
};
```

**⇒ 八层**：
```text
1. **一个 lambda，返回 `optional<Result>`**
2. ⇒ **`nullopt` ⇒ 成功**（**继续**）
3. ⇒ **`Result` ⇒ 失败**（**返回**）
4. ⇒ **⇒ 与 `validatePlayerMethod` 的同一个惯例**（§438）
5. ⇒ **⇒ 所以【一个"返回 optional 的错误"**的功能**惯用法**
```

**✅ 与 §438 的 `validatePlayerMethod` 返回 `optional<Result>`**完全同族 ✓

**⇒ 三层**：
```text
§438  **`validatePlayerMethod` ⇒ `optional<Result>`（`nullopt` = 通过）**
§446  **`appendTransform` ⇒ 同一惯例**
⇒ **⇒ 所以【一个项目级的惯用法**】
```

**✅ ⭐⭐ **"一个项目级的惯用法"**。

**⚠ 而"`{ 0.0f, yaw, 0.0f }`"⇒ **`pitch`/`roll` 恒零**。**

**✅ 与 §439 的"`spawnZombieActor` 强制 `pitch`/`roll` 为零"**同族（**第二次"只 `yaw`**）。

**⇒ 三层**：
```text
§439  **`zmspawnactorat` ⇒ `.angles = { 0.0f, yaw, 0.0f }`**
§443  **`setmodelat` ⇒ 只接受 `yaw`**
§446  **`setactorpositions` ⇒ `{ 0, yaw, 0 }`**
⇒ **⇒ 三次"只 `yaw`**】
```

**✅ ⭐ **一个"只 `yaw`"的三例表**。

## 四、**`radiusDamageAt` 的四个正数**（本组第三重要）

```php
if (!effectRadius || !std::isfinite(*effectRadius) ||
    *effectRadius <= 0.0 || !data1 || *data1 <= 0 ||
    *data1 > std::numeric_limits<std::int32_t>::max() ||
    !data2 || *data2 <= 0 ||
    static_cast<std::uint64_t>(*data2) > std::numeric_limits<std::uint32_t>::max())
    ⇒ "radiusdamageat expects a positive radius and positive 32-bit data words"
```

**⇒ 十二层**：
```text
1. **`effectRadius > 0`**（**有限**）
2. ⇒ **`data1 > 0` 且 `<= INT32_MAX`**
3. ⇒ **`data2 > 0` 且 `<= UINT32_MAX`**
4. ⇒ **⇒ 两个 `data` 的【上界不同**】（`INT32_MAX` vs `UINT32_MAX`）
5. ⇒ **⇒ 而【两个【都必须 `> 0`**】】**
```

### 4.1 ⭐⭐⭐ **"`data1` 是 `INT32_MAX` 而 `data2` 是 `UINT32_MAX`"**

**✅ 与 §444 的"`timeOffset` 无界而 `duration` 是 `UINT32_MAX`"**不同（这是**两个 `data` 的两个上界**）。

**⇒ 三层**：
```text
`data1` ⇒ **`INT32_MAX`**（**一个有符号上界**）
`data2` ⇒ **`UINT32_MAX`**（**一个无符号上界**）
⇒ **⇒ 所以【两个"32 位数据字"【有不同的上界**】
```

**⚠ 一个**需要理由的差异**（**可能一个是"时间"一个是"标志"**）。

**✅ 与 §407 的"`EventRadiusDamage` 的 `+58` 是一个 `float32`、`+5C/+60` 是两个整数字"**——**而这里 `effectRadius` 是 `float`，`data1`/`data2` 是两个整数** ✓

**⇒ 三层**：
```text
§407  **"`CG_EntityEvent` 从 `+58` 读一个 `float32` 并从 `+5C/+60` 读两个整数字"**
§446  **`effectRadius: float`、`data1: int64→uint32`、`data2: int64→uint32`**
⇒ **⇒ 完全一致**
```

**✅ ⭐⭐⭐ **一个跨报告的字段闭合**。

**⚠ 而"`data1` 是 `INT32_MAX` 而 `data2` 是 `UINT32_MAX`"⇒ **仍无解释**。**

**⇒ 三层**：
```text
`data1` ⇒ **可到 `2^31-1`**
`data2` ⇒ **可到 `2^32-1`**
⇒ **⇒ 所以【`data2` 可以用【最高位**】
```

**⚠ 一个**可推导的观察**（**`data2` 可能携带一个符号位或一个高位标志**）。

**✅ 与 §432 的"`challenge &= 0x7FFFFFFF` ⇒ `31` 位"**不同（那是**主动裁剪**）。

**⇒ 三层**：
```text
§432  **`challenge` 主动裁到 `31` 位**
§446  **`data2` 接受 `32` 位**
⇒ **⇒ 所以【两个不同的策略**】
```

**✅ ⭐ **一个"两个策略"的对照**。

## 五、**`actorFire` 的"表现与伤害分离"**（本组第四重要）

### 5.1 那段

```php
// One native campaign-rifle trace. The confirmed Wetwork recording
// carries EV_FIRE_WEAPON (41, parameter 0) on ET_ACTOR. The mission
// can publish that presentation independently from its one damage
// attempt per burst; damage still uses the ordinary retained
// finishPlayerDamage owner and requires a clear locational trace.
SvScriptBuiltinResult actorFire(
    SvServerWorld &world, const SvScriptBuiltinCall &call,
    const SvScriptBuiltinRegistry::WeaponResolver &resolveWeapon,
    bool publishPresentation)
```

### 5.2 二十层

```text
1. **一次原生战役步枪的 trace**
2. ⇒ **确认的 Wetwork 录像携带【`EV_FIRE_WEAPON`（`41`，参数 `0`）**】在 `ET_ACTOR` 上**
3. ⇒ **⇒ 任务【可以【独立地发布那个表现**】**
4. ⇒ **⇒ 从它的【每一次连发的【一次伤害尝试**】】**
5. ⇒ **⇒ 而伤害【仍然用【普通的保留 `finishPlayerDamage` 所有者**】**
6. ⇒ **而它【要求一条【清晰的 locational trace**】**
```

### 5.3 ⭐⭐⭐ **"任务可以独立地发布那个表现，从它的每一次连发的一次伤害尝试"**

**✅ 这是本报告里**最重要的一条"表现与伤害分离"**。**

**⇒ 三层**：
```text
表现（`EV_FIRE_WEAPON`）⇒ **每次都发** ⇒ **视觉/音频**
伤害 ⇒ **每次连发【一次**】 ⇒ **判定**
⇒ **⇒ 所以【一个 `bool publishPresentation` 参数**】
```

**✅ 与 §410 的"`SMALL` 每发 `LARGE` 不发"**同族（**第四次"表现与逻辑分离**）。

**⇒ 三层**：
```text
§410  **`EV_BULLET_HIT` 与 `EV_BULLET_HIT_CLIENT_SMALL`**（**两个事件**）
§418  **`obituary` 的"创建 vs 发出"**（**两个声明**）
§446  **`publishPresentation`**（**一个参数**）
⇒ **⇒ 三次"分离**】
```

**✅ ⭐⭐⭐ **一个"表现与逻辑分离"的三例表**。

**⚠ 而"`EV_FIRE_WEAPON` 是 `41`"⇒ **与 §415 的事件表**——**`41` 不在那里**。**

**⇒ 三层**：
```text
§415  **列出的事件：`0x03`/`0x04`/`0x2C`/`0x4B`/`0x53`/`0x56`/`0x6F`/`0x71`/`0x82`/`0x83`/`0x86`/`0x88`/`0x8F`**
§446  **`EV_FIRE_WEAPON` = `41` = `0x29`**
⇒ **⇒ 所以【`0x29` 【不在**§415 的表里**】
```

**✅ 一个**新的事件 id**（**`0x29` = `41`**）。</br>

**⚠ 而 §415 说"`eType = 23 + eventId`"⇒ **所以 `eType = 64`**。**

**⇒ 三层**：
```text
`41 + 23 = 64` ⇒ **一个 `ET_EVENTS` 的 `eType`**
⇒ **⇒ 而【§415 的 `EntityTypeFireMagic = 67 = 23 + 44`**】
```

**✅ 与 §415 的 `EventFireMagic = 0x2C = 44` ⇒ `eType = 67`**配合（**`44` 与 `41` 相邻**）。

## 六、关键结论

1. **⭐⭐⭐ "Model 号在这里被刻意接受，因为这是从录像测出的地图专属模型 configstring 索引"`** —— **一个"测量支撑的例外"**，与 §417 的"从不 demo 的字面 `287`"形成**精确对照**（**那里拒绝，这里接受，区别是"这是否是一个被测量的地图专属值"**）。
2. **⭐⭐ "一个例外只有在它被测量时才合法"`** —— 而 **"地图专属"是一个关键限定**（**`spawnactor` 只能在那个战役地图上用**）。
3. **⭐⭐⭐ `spawnActor` 的五个界**：`slot 0..23`（**`24`**）/ `model 0..0x3FF`（`10` 位）/ `team 0..0x7FF`（`11` 位）/ `animation 0..0xFFF`（`12` 位）/ `animation_start_time 0..UINT32_MAX`。
4. **⚠ 一处真实的数值差异**：**`spawnactor` 的 `slot` 是 `0..23`（`24` 个）而 §415/§416 说 `SvAgentSlotCount = 32`，而 retail 实际 delta-codes `31` 个** ⇒ **三个数 `32`/`31`/`24`**（**`24` 可能是"一个更保守的上界"**）—— 与 §442/§444 的"界比实际宽"**相反**（这是**窄**）。
5. **⭐ `model` 的 `0x3FF`（`10` 位）与 §415 的"`ModelField` 是 `TEN BITS`"完全吻合**；而 **`team` 的 `0x7FF`（`11` 位）远宽于 `SvTeam` 的 `0..3`**（一个**位宽 vs 语义范围**的区分）。
6. **⭐⭐⭐ `setActorPositions` 的 `4 + 5n` 形状**（`(size - 4) % 5 != 0` ⇒ 拒绝）—— **参数形状的第三个种类**（固定个数 / `n` 或 `n+1` / **任意长度的重复组**）。
7. **⭐⭐⭐ "Move Wetwork 的直升机演员表【一次碰撞/原生镜像重建】"`** —— 与 §422 的"七个独立的变更重建完整的碰撞/原生镜像七次，而让脚本相机的时间线饥饿"**完全闭合**（**同一个性能动机的两个层次**）。
8. **⭐ `transforms.reserve(1 + (size - 4) / 5)` 是一个精确的预留**（`1` = 接收者）—— 第三次"避免分配"。
9. **⭐⭐ `appendTransform` 是一个返回 `optional<Result>` 的 lambda**（`nullopt` = 通过）⇒ **与 §438 的 `validatePlayerMethod` 是同一个项目级惯用法**。
10. **⭐⭐ "只 `yaw`"的第三例**：`spawnZombieActor`（§439）、`setmodelat`（§443）、`setactorpositions`（§446）⇒ **`pitch`/`roll` 恒零，而 `{ 0.0f, yaw, 0.0f }` 是那个形状**。
11. **⭐⭐⭐ `radiusDamageAt` 与 §407 的"`CG_EntityEvent` 从 `+58` 读一个 `float32` 并从 `+5C/+60` 读两个整数字"完全一致**（`effectRadius: float` / `data1` / `data2`）—— 一个跨报告的字段闭合。
12. **⚠ `data1` 的上界是 `INT32_MAX` 而 `data2` 是 `UINT32_MAX`**（两处差异未解释，**可能是"一个时间一个标志"**）。
13. **⭐⭐⭐ `actorFire` 的"表现与伤害分离"**：**"任务可以独立地发布那个表现（`EV_FIRE_WEAPON`，`41`，参数 `0`）从它的每一次连发的一次伤害尝试"`** ⇒ **一个 `bool publishPresentation` 参数** —— 第三次"表现与逻辑分离"（与 §410、§418 同族）。
14. **⭐ `EV_FIRE_WEAPON` = `41` = `0x29` ⇒ `eType = 64`，而 §415 的 `EventFireMagic = 0x2C = 44` ⇒ `eType = 67`** ⇒ **两个相邻的事件**。

## 七、未闭合点

- `spawnactor` 的 `slot 0..23` 与 `SvAgentSlotCount = 32` 的差异。
- `data1`（`INT32_MAX`）与 `data2`（`UINT32_MAX`）的上界差异。
- `EV_FIRE_WEAPON` = `41` 的完整语义（参数 `0`）。
- `finishDamageResult` 的实现（前向声明）。
- `animation_start_time` 的语义（与 §417 的 `animStartTime`）。
- `sv_script_builtin_mp.cpp` 3080 行之后未读取（**共 `4424` 行**）。
