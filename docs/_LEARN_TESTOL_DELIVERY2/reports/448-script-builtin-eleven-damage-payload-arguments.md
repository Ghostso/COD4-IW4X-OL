# 448 · **"`11` 个参数的伤害载荷与 `6` 个独立的读取器"** —— `readPlayerDamagePayload` 的十个域、`finishSharedPlayerDamage` 的 `12` 与"两个玩家同一份载荷"

## 一、范围

本报告学习 `sv_script_builtin_mp.cpp` 3420–3760 行（`readOptionalEntityNum`、`readInteger`、`readPlayerDamagePayload` 的 `11` 个参数、`finishDamageResult` 的六个映射、`finishPlayerDamage`、`finishSharedPlayerDamage`、注册表构造器的开头）。

## 二、**`readPlayerDamagePayload` 的 `11` 个参数**（本组最重要的一段）

### 2.1 那段

```php
if (arguments.size() != 11) return false;
payload.targetClientNum = targetClientNum;
if (!readOptionalEntityNum(arguments[0], payload.inflictorEntityNum) ||
    !readOptionalEntityNum(arguments[1], payload.attackerEntityNum) ||
    !readInteger(arguments[2], 1, INT32_MAX, damage) ||
    !readInteger(arguments[3], 0, 0xFFFFFFFFLL, damageFlags) ||
    !readInteger(arguments[4], 0, MethodOfDeathCount - 1, methodOfDeath) ||
    !readInteger(arguments[5], 1, MaximumWeaponAssetIndex, weaponAssetIndex) ||
    !readOptionalVector(arguments[6], payload.point) ||
    !readOptionalVector(arguments[7], payload.direction) ||
    !readInteger(arguments[8], 0, HitLocationCount - 1, hitLocation) ||
    !readInteger(arguments[9], INT32_MIN, INT32_MAX, timeOffset) ||
    !readInteger(arguments[10], 0, 0xFFFF, boneIndex))
{
    return false;
}
```

### 2.2 二十四层

```text
1. **`11` 个参数**【逐项命名**】**
2. ⇒ **`inflictor`（可选实体号）**
3. ⇒ **`attacker`（可选实体号）**
4. ⇒ **`damage` ⇒ `1..INT32_MAX`**（**必须正**）
5. ⇒ **`damageFlags` ⇒ `0..0xFFFFFFFF`**（**`32` 位**）
6. ⇒ **`methodOfDeath` ⇒ `0..MethodOfDeathCount-1`**
7. ⇒ **`weaponAssetIndex` ⇒ `1..MaximumWeaponAssetIndex`**（**必须非零**）
8. ⇒ **`point`（可选向量）**
9. ⇒ **`direction`（可选向量）**
10. ⇒ **`hitLocation` ⇒ `0..HitLocationCount-1`**
11. ⇒ **`timeOffset` ⇒ `INT32_MIN..INT32_MAX`**（**可负**）
12. ⇒ **`boneIndex` ⇒ `0..0xFFFF`**（**`16` 位**）
13. ⇒ **⇒ 而 `targetClientNum` 【由调用者传**】而不是参数**
```

### 2.3 ⭐⭐⭐ **"`targetClientNum` 由调用者传而不是参数"**

**✅ 与 §446 的"`agentNum` 由 `spawnactor` 的第一个参数传"**不同（这是**一个隐含的参数**）。

**⇒ 三层**：
```text
`readPlayerDamagePayload(arguments, targetClientNum, payload)` ⇒ **`targetClientNum` 【不在 `arguments` 里**】
⇒ **⇒ 所以【调用者【把它作为第二个参数**】传**
⇒ **⇒ 因为【`call.self->id` 就是那个目标**】
```

**✅ ⭐⭐⭐ **"因为 `call.self->id` 就是那个目标"** —— 与 §447 的"`suppressCorpse` 的玩家分支是同一个键"**同族（**第五次"一个隐含的参数"）。

**⚠ 而"`1..INT32_MAX` 的 `damage`"⇒ **必须正**。**

**⇒ 三层**：
```text
`damage >= 1` ⇒ **不允许 `0`**
⇒ **⇒ 所以【一个零伤害的调用【被拒绝**】
```

**✅ 与 §419 的"`damage.damage <= 0 ⇒ continue`"**配合（**那里是消费端的过滤，这里是入口的拒绝**）。

**⇒ 三层**：
```text
§419  **消费端：`damage <= 0 ⇒ continue`**
§448  **入口：`damage >= 1` 检查**
⇒ **⇒ 两层防护**】
```

**✅ ⭐⭐ **"两层防护"** —— 与 §438 的"`respawn` 的 `0..60000` 与世界层的二次检查"**同族（**第二次**）。

**⚠ 而"`timeOffset` 可负"⇒ **一个"过去"的伤害**。**

**✅ 与 §445 的"`positionTime` 允许负而 `launchTime` 不允许"**同族（**第二次"时间可负"）。

**⇒ 三层**：
```text
§444  **`setgroundtilttrajectory` 的 `trajectoryTime` ⇒ 不可负**
§445  **`positionTime` ⇒ 可负；`launchTime` ⇒ 不可负**
§448  **`timeOffset` ⇒ 可负**（`INT32_MIN`）
⇒ **⇒ 三次"时间域**】
```

**✅ ⭐ **一个"时间域"的三例表**。

### 2.4 而**六个 `readInteger` 调用**

```cpp
readInteger(arguments[2], 1, INT32_MAX, damage)
readInteger(arguments[3], 0, 0xFFFFFFFFLL, damageFlags)
readInteger(arguments[4], 0, MethodOfDeathCount - 1, methodOfDeath)
readInteger(arguments[5], 1, MaximumWeaponAssetIndex, weaponAssetIndex)
readInteger(arguments[8], 0, HitLocationCount - 1, hitLocation)
readInteger(arguments[9], INT32_MIN, INT32_MAX, timeOffset)
readInteger(arguments[10], 0, 0xFFFF, boneIndex)
```

**⇒ 八层**：
```text
1. **一个模板函数 `readInteger<Integer>(value, min, max, result)`**
2. ⇒ **⇒ 同一次检查【三个参数**】**
3. ⇒ **⇒ 所以【七次调用【七组界**】**
4. ⇒ **⇒ 而 `Integer` 是【推导**的】**
```

### 2.5 ⭐⭐⭐ **"一个模板函数消除七份重复"**

**✅ 与 §444 的"七个函数各自手写 `if (call.self) ⇒ InvalidSelf`"**——**完全相反** ✓

**⇒ 三层**：
```text
§444  **七个 `if (call.self)` 检查【复制了七份**】
§448  **七个 `readInteger` 调用【用一个模板**】
⇒ **⇒ 所以【一个抽了，一个没抽**】
```

**✅ ⭐⭐⭐ **"'一个抽了一个没抽'的对照"** —— 而**两者的阈值都是七**。

**⇒ 三层**：
```text
`if (call.self)` ⇒ **一行** ⇒ **复制七次可接受**（**项目指令：三行重复优于抽象**）
`readInteger` ⇒ **`min`/`max`/`result` 三类逻辑** ⇒ **抽成模板**
⇒ **⇒ 所以【抽与不抽【由复杂度**决定，不由次数**】
```

**✅ ⭐⭐⭐ **"抽与不抽由复杂度决定，不由次数"** —— 本报告最精确的一条判据。

**⚠ 而"`0xFFFFFFFFLL`"⇒ **一个 `long long` 字面量**。**

**⇒ 三层**：
```text
`0xFFFFFFFFLL` ⇒ **`4294967295`** ⇒ **一个 `uint32` 的最大值**
而【参数是 `std::int64_t`**】 ⇒ **所以字面量必须 `LL`**
⇒ **⇒ 所以【`0xFFFFFFFF` 不带 `LL` 会是一个 `unsigned int`**（**一个类型错误**）
```

**✅ ⭐⭐ **"`LL` 后缀是必要的"** —— 一个**类型细节**。</br>

**✅ 与 §438 的"`static_cast<uint64_t>` 让检查工作"**同族（**第四次"类型细节"）。

## 三、**`finishDamageResult` 的六个映射**（本组第二重要）

### 3.1 六个

```text
Applied                    ⇒ success(monostate)
ClientNotFound             ⇒ ObjectNotFound       + "target does not exist"
NotPlaying                 ⇒ InvalidObjectState   + "target is not Playing"
InvalidPayload             ⇒ InvalidArgumentValue + "payload is invalid"
DeathTransitionUnavailable ⇒ DeathTransitionUnavailable + "death transition is not restored"
NativeMirrorUnavailable    ⇒ WorldMutationFailed  + "native entity mirror rejected the damage transaction"
（default）                ⇒ WorldMutationFailed  + "returned an invalid result"
```

**⇒ 十层**：
```text
1. **六个具名结果 + 一个 default**
2. ⇒ **⇒ 而【六个【各自一个**错误码**】
3. ⇒ **⇒ 其中 `Applied` ⇒ `success`**
4. ⇒ **而【其余五个 ⇒ 五个不同的错误码**】
5. ⇒ **⇒ 所以【一个六值枚举【完整映射**】】**
```

### 3.2 ⭐⭐⭐ **"六个值，六个结果，五个错误码"**

**✅ 与 §437 的"八个拒绝都返回同一个 `false`"**——**完全相反** ✓

**⇒ 三层**：
```text
§437  **一个函数内，八个原因 ⇒ 一个 `false`**（**缺陷**）
§448  **一个枚举，六个值 ⇒ 六个具名结果**（**正确**）
⇒ **⇒ 所以【§448 是【那个缺陷的【正确形态**】
```

**✅ ⭐⭐⭐ **"那个缺陷的正确形态"** —— 与 §438 的"五道五个错误码"**同族（**第四次"错误码的成熟度**）。

**⇒ 三层**：
```text
§438  **五道五个码**
§442  **两个方向两个具名错误**
§448  **六个值六个结果**
⇒ **⇒ 三次"完整映射**】
```

**✅ ⭐⭐ **一个"完整映射"的三例表**。

**⚠ 而"`DeathTransitionUnavailable`"⇒ **一个独特的错误码**。**

**⇒ 三层**：
```text
`SvServerWorld::FinishPlayerDamageResult::DeathTransitionUnavailable`
⇒ **`SvScriptBuiltinErrorCode::DeathTransitionUnavailable`**（**同名**）
⇒ **⇒ 所以【一个一一对应**】
```

**✅ ⭐⭐ **"一个一一对应的映射"** —— 与 §438 的 `ammoMutationResult` 的五个映射**同族（**第二次**）。

**⇒ 三层**：
```text
§438  **`WeaponAmmoMutationResult` 五个值 ⇒ 五个错误码**
§448  **`FinishPlayerDamageResult` 六个值 ⇒ 六个结果**
⇒ **⇒ 同一手法两处**
```

**✅ ⭐ **一个"同一手法"的确认**。

## 四、**`finishSharedPlayerDamage` 的 `12` 与"两个玩家同一份载荷"**（本组第三重要）

### 4.1 那段

```php
validatePlayerMethod(world, call, 12, playerState)
const auto *other = std::get_if<SvScriptObjectRef>(&call.arguments[0]);
if (!other || other->kind != Player) ⇒ InvalidArgumentType
if (other->id == call.self->id || !world.onSameTeam(call.self->id, other->id))
    ⇒ InvalidArgumentValue "requires distinct same-team players"
SvPlayerDamagePayload first;
readPlayerDamagePayload(std::span(call.arguments).subspan(1), call.self->id, first)
auto second = first;
second.targetClientNum = other->id;
const std::array payloads{ first, second };
world.finishPlayerDamageBatch(payloads)
```

### 4.2 二十层

```text
1. **`12` 个参数** = **`1` 个 `other` 玩家 + `11` 个载荷字段**
2. ⇒ **`other` 必须是一个 `Player` 对象且【不是自己**】**
3. ⇒ **且【`onSameTeam(self, other)`**】**
4. ⇒ **⇒ 所以【"不同的队友**】**
5. ⇒ **而【同一份载荷 ⇒ 拷贝 ⇒ 只改 `targetClientNum`**】**
6. ⇒ **⇒ 所以【两个玩家【承受【完全相同的伤害**】】**
```

### 4.3 ⭐⭐⭐ **"同一份载荷 ⇒ 拷贝 ⇒ 只改 `targetClientNum`"**

**✅ 这是本报告里**最重要的一条"共享伤害的语义**。**

**⇒ 三层**：
```text
`first` ⇒ **`self` 的载荷**
`second = first` ⇒ **一份拷贝**
`second.targetClientNum = other->id` ⇒ **只改目标**
⇒ **⇒ 所以【两个玩家【除了目标之外完全一样**】
```

**✅ 与 §446 的"`actorFire` 的 `inflictor` 与 `attacker` 都是 `actor.entityNum`"**不同（这是**一份载荷两个目标**）。

**⇒ 三层**：
```text
`finishPlayerDamage`       ⇒ **一个目标**
`finishSharedPlayerDamage` ⇒ **两个目标，一份载荷**
⇒ **⇒ 所以【"共享伤害"= 同一份元数据**】
```

**✅ ⭐⭐⭐ **"共享伤害 = 同一份元数据"** —— 一个**极精确的语义**。</br>

**✅ 与 §422 的"`finishPlayerDamageBatch` 丢弃每一次命中"**配合。

**⇒ 三层**：
```text
§422  **`finishPlayerDamageBatch` 在 `:24887` 丢弃命中**
§448  **`finishSharedPlayerDamage` 用它发两个载荷**
⇒ **⇒ 所以【那个批量函数【也是"共享"的入口**】
```

**✅ ⭐⭐ **"那个批量函数也是共享的入口"**。</br>

**⚠ 而"`other->id == call.self->id` ⇒ 拒绝"⇒ **一个自伤检查**。**

**⇒ 三层**：
```text
`self == other` ⇒ **一个玩家"共享"给自己** ⇒ **无意义**
⇒ **⇒ 所以拒绝**
```

**✅ 与 §440 的"`respawn` 的 `NotPlaying` 与 `NotDead` 合并"**不同（这是**一个明确的拒绝**）。

**⚠ 而"`onSameTeam` 要求同队"⇒ **与 §416 的"`onSameTeam` 在任一侧 `None` 时是假"**配合。**

**⇒ 三层**：
```text
FFA（`None`/`None`）⇒ **`onSameTeam` 假** ⇒ **`finishSharedPlayerDamage` 【不可用**】
⇒ **⇒ 所以【这个内建【只在团队模式**】上可用**】
```

**✅ ⭐⭐ **"只在团队模式上可用"** —— 一个**隐含的模式限制**。</br>

**✅ 与 §442 的"`None = None` 视为互敌"**配合。

## 五、**注册表的 `56` 个 `handlers_.emplace`**

**⇒ 十六层**：
```text
1. **一个 `SvScriptBuiltinId{ kind, name }` 的 `unordered_map`**
2. ⇒ **每个内建【一个 `emplace`**】**
3. ⇒ **⇒ 而【`Function` 与 `Method` 【两个 kind**】**
4. ⇒ **⇒ 所以【同名的一个函数与一个方法【可以共存**】】**
5. ⇒ **而【lambda 捕获 `this` 以获得 `xxxProvider_`**】
6. ⇒ **⇒ 而【无状态的（`zmPlayerCount`/`zmCooperativeZoneSource`/`zmsetround`）用 `[]`**】**
7. ⇒ **⇒ 所以【一个"是否需要成员"的判据**】
```

### 5.1 ⭐⭐⭐ **"无状态的内建用 `[]` 而有的用 `[this]`"**

**✅ 与 §438 的"`Function` 与 `Method` 两类"**配合 ✓

**⇒ 三层**：
```text
`[this]` ⇒ **需要 `xxxProvider_`**（`zmZoneProvider_`/`modelResolver_`/...）
`[]`     ⇒ **只需要 `world`**（**从参数传**）
⇒ **⇒ 所以【一个"依赖"的精确标注**】
```

**✅ ⭐⭐ **"一个依赖的精确标注"** —— 而 **`emplace` 时的 lambda 签名统一为 `(SvServerWorld &, const SvScriptBuiltinCall &)`**。

**⚠ 而"有些直接传函数指针（`setMapGameObjects`/`getEntArray`/`setEntityHealth`）"**⇒ **第三种形式**。**

**⇒ 三层**：
```text
lambda `[this]` ⇒ **有状态**
lambda `[]`     ⇒ **无状态但需要 `world`**
函数指针        ⇒ **无状态，签名匹配**
⇒ **⇒ 三种形式**】
```

**✅ ⭐⭐ **"三种形式"** —— 与 §438 的"`SvScriptValue` 无表类型但有对象数组"**同族（**第四次"多种形式**）。

**⇒ 三层**：
```text
§447  **参数形状三种**（固定 / `n` 或 `n+1` / `4+5n`）
§448  **注册形式三种**（`[this]` / `[]` / 函数指针）
⇒ **⇒ 两次"三种形式**】
```

**✅ ⭐ **一个"三种形式"的两例**。

## 六、关键结论

1. **⭐⭐⭐ `readPlayerDamagePayload` 的 `11` 个参数逐项命名**，其中 **`targetClientNum` 【不在参数里**】—— 由调用者传（**因为 `call.self->id` 就是那个目标**）。
2. **⭐⭐ "`damage >= 1`（入口）与 §419 的 `damage <= 0 ⇒ continue`（消费端）是两层防护"** —— 与 §438 的"`respawn` 的 `0..60000` 与世界层二次检查"同族。
3. **⭐⭐ 三个时间域**：`setgroundtilttrajectory` 的 `trajectoryTime` 不可负 / `positionTime` 可负而 `launchTime` 不可负 / **`timeOffset` 可负（`INT32_MIN`）**。
4. **⭐ `0xFFFFFFFFLL` 的 `LL` 后缀是必要的**（因为参数是 `std::int64_t`）—— 第四个"类型细节"。
5. **⭐⭐⭐ "一个模板函数消除七份重复"（`readInteger`）与 §444 的"七个函数各自手写 `if (call.self)`"形成完整对照** ⇒ **"抽与不抽由复杂度决定，不由次数"** —— 本报告最精确的一条判据（`if (call.self)` 是一行，`readInteger` 是三类逻辑）。
6. **⭐⭐⭐ `finishDamageResult` 的六个值六个结果（五个不同错误码 + 一个 default）** —— 与 §437 的"八个拒绝都返回同一个 `false`"**完全相反** ⇒ **"那个缺陷的正确形态"**。
7. **⭐ `DeathTransitionUnavailable` 在 `SvServerWorld` 与 `SvScriptBuiltinErrorCode` 里【同名**】 ⇒ 一个一一对应的映射**（与 §438 的 `ammoMutationResult` 同族）。
8. **⭐⭐⭐ `finishSharedPlayerDamage` 的"12 = 1 个 `other` 玩家 + 11 个载荷字段"**，而 **`other` 必须是一个 `Player`、不是自己、且 `onSameTeam`** ⇒ **"不同的队友"**。
9. **⭐⭐⭐ "同一份载荷 ⇒ 拷贝 ⇒ 只改 `targetClientNum`"** ⇒ **"共享伤害 = 同一份元数据"** —— 一个极精确的语义；而与 §422 的 `finishPlayerDamageBatch` 是同一个入口。
10. **⭐ 一个隐含的模式限制**：**FFA（`None`/`None`）下 `onSameTeam` 为假 ⇒ `finishSharedPlayerDamage` 【不可用**】 —— 只在团队模式上可用。
11. **⭐⭐ 注册表的三种形式**：`[this]`（有状态）/ `[]`（无状态但需要 `world`）/ **函数指针**（无状态、签名匹配）—— 而 **`emplace` 的 lambda 签名统一为 `(SvServerWorld &, const SvScriptBuiltinCall &)`**。
12. **⭐ "`Function` 与 `Method` 两个 kind ⇒ 同名的一个函数与一个方法可以共存"`**。

## 七、未闭合点

- `MethodOfDeathCount` / `HitLocationCount` 的值。
- `MaximumGameEntities` 的值。
- `SvScriptValue` 的完整 `variant` 成员（`monostate`/`string`/`int64_t`/`double`/`bool`/`SvScriptVector`/`SvScriptObjectRef`/`SvScriptObjectArray`）。
- `SvPlayerDamagePayload` 的 `point`/`direction`/`timeOffset` 的用途。
- `finishPlayerDamageBatch` 的"共享"语义。
- `sv_script_builtin_mp.cpp` 3760 行之后未读取（**共 `4424` 行**）。
