# 442 · **"一个名字或一个裸索引，因为模块化武器在带里没有朴素名字"** —— `setObjective` 的五个域、`giveWeapon` 的双形态、以及 `permitsNone`

## 一、范围

本报告学习 `sv_script_builtin_mp.cpp` 1380–1720 行（`setObjective` 的五个界、`getEntityNumber`、`getMapEntityField`、`isTouchingPlayer`、`giveWeapon` 的双形态、`setPlayerWeapons` 的 `permitsNone`、`weaponIndex`/`effectIndex`、`setPlayerWeaponAmmo`）。

## 二、**"一个名字或一个裸索引"**（本组最重要的一段）

### 2.1 那段

```php
// A NAME OR A RAW INDEX. Names are preferred and are what a real script
// should use, but a MODULAR weapon -- which is what battle royale loot
// actually is -- has no plain name in the band to resolve: its
// configstring is a `**` definition, not `ak104dmz_mp`. So the loot band's
// own numbers have to be passable directly.
std::optional<std::uint16_t> weaponIndex;
if (const auto *const index = std::get_if<std::int64_t>(&call.arguments[0])) { ... }
else if (const auto *const weaponName = std::get_if<std::string>(&call.arguments[0]); weaponName && !weaponName->empty()) { ... }
else return failure(InvalidArgumentType, "giveweapon expects a weapon name or a weapon index");
```

### 2.2 二十层

```text
1. **一个名字【或一个裸索引**】**
2. ⇒ **名字是【首选**的】而【是一个真实脚本【应该用的**】】**
3. ⇒ **⚠ 而【一个【模块化**武器**】**
4. ⇒ **（**那正是【大逃杀拾取【实际上**】的东西**）**
5. ⇒ **【在带里【没有朴素名字**】可解析**
6. ⇒ **⇒ 它的 configstring 是一个 **`**` 定义**，不是 `ak104dmz_mp`**
7. ⇒ **⇒ 所以【**那个拾取带【自己的号**】必须【可直接传入**】**
```

### 2.3 ⭐⭐⭐ **"它的 configstring 是一个 `**` 定义，不是 `ak104dmz_mp`"**

**✅ 这是本报告里**最重要的一条"模块化武器的形态**。**

**⇒ 三层**：
```text
普通武器 ⇒ **configstring 是 `ak104dmz_mp`**（**一个名字**）
模块化武器 ⇒ **configstring 是 `**`**（**一个定义串**）
⇒ **⇒ 所以【一个名字解析【无法**分辨它们**】
```

**✅ 与 §430 的"`a <index>` 的值域是 loot 带（`1148..1211`）及其上方"**完全闭合 ✓

**⇒ 三层**：
```text
§430  **`a` 的三个值在 `1148..1211` 带内、三个在带上方**（"一把刚被注册的模块化变体"）
§442  **模块化武器的 configstring 是 `**` 定义**
⇒ **⇒ 同一个概念的两次**
```

**✅ ⭐⭐⭐ **一个"模块化武器"的两面**。

**⚠ 而"`**` 定义"⇒ **一个前缀标记**。**

**⇒ 三层**：
```text
`**` ⇒ **可能是"这是一个定义而不是一个名字"的标记**
⇒ **⇒ 所以【一个名字解析器【会拒绝它**】】
```

**✅ 与 §414 的"`name.front() == '*'` ⇒ 拒绝"**完全闭合 ✓

**⇒ 三层**：
```text
§414  `registerOutfitModelConfigString`：`name.front() == '*' ⇒ return nullopt`
§442  **模块化武器的 configstring 以 `**` 开头**
⇒ **⇒ 所以【同一条规则在【两个地方**】】
```

**✅ ⭐⭐⭐ **"同一条规则在两个地方"** —— **§414 的 `'*'` 检查的正确性在这里被确认**。

**⇒ 三层**：
```text
§414  **`'*'` 前缀 ⇒ 拒绝**（**"一个名字不能以 `*` 开头"**）
§442  **而模块化武器【确实**以 `**` 开头**】
⇒ **⇒ 所以【§414 的检查【不是防御性的而是语义性的**】】
```

**✅ ⭐⭐ **"不是防御性的而是语义性的"** —— 一个**极精确的定性**。

### 2.4 而**"索引必须在带内"**

```cpp
if (*index <= 0 || *index >= WeaponConfigStringCount)
    ⇒ "giveweapon received a weapon index outside the band"
```

**⇒ 六层**：
```text
1. **`index <= 0` ⇒ 拒绝**（**从 `1` 开始**）
2. ⇒ **`index >= WeaponConfigStringCount` ⇒ 拒绝**
3. ⇒ **⇒ 所以【`1..WeaponConfigStringCount-1`**】
4. ⇒ **⇒ 与 §430 的 `a <index>` 的"必须是已注册的"**不同（**那是【更严的**】）
```

**✅ ⭐⭐ **"这里的界比 `a` 的更宽"** —— 与 §430 的 `queueReliableCommand` 的检查**对照**。

**⇒ 三层**：
```text
`giveweapon` ⇒ **`1..WeaponConfigStringCount-1`**（**宽**）
`queueReliableCommand("a N")` ⇒ **必须是 `modularWeaponConfigStrings` 里的**（**窄**）
⇒ **⇒ 所以【两个检查【不同的严格度**】】
```

**⚠ 一个**潜在的不一致**（**`giveweapon` 授予一个未注册的索引 ⇒ `a` 会拒绝**）。

**✅ 与 §430 的"静态区不受检查"**配合。

**⇒ 三层**：
```text
`giveweapon` 接受【任何带内索引**】
而 `a` 只接受【静态 或 已注册的模块化**】
⇒ **⇒ 所以【一个 `giveweapon` 到未注册的模块化索引 ⇒ 武器在手而【没有 `a` 能显示它**】】
```

**⚠ 一个**可推导的缺口**（**标注**）。

## 三、**`setObjective` 的五个域**（本组第二重要）

### 3.1 那段

```php
if (*slot < 0 || *slot >= 32 || *state < 0 || *state > 5 ||
    *icon < 0 || *icon > 0xFFF ||
    *entityNum < 0 || *entityNum > EntityNumNone ||
    *teamNum < 0 || *teamNum > 0xF)
{
    return failure(InvalidArgumentValue, "setobjective values exceed the CODOL objective wire domains");
}
```

### 3.2 二十层

```text
1. **`slot` ⇒ `0..31`**（`32` 个槽，**与 §416 的 `std::array<SvObjective, 32>` 闭合**）
2. ⇒ **`state` ⇒ `0..5`**（**六个 `SvObjectiveState`**）
3. ⇒ **`icon` ⇒ `0..0xFFF`**（**`12` 位**）
4. ⇒ **`entityNum` ⇒ `0..EntityNumNone`**（**`2047`**）
5. ⇒ **`teamNum` ⇒ `0..0xF`**（**`4` 位**）
6. ⇒ **⇒ 五个域，全部由【线上的位宽**】决定**
```

### 3.3 ⭐⭐⭐ **"五个域，全部由线上的位宽决定"**

**✅ 与 §419 的"那四条指令就是整个规格"**同族（**第三次"位宽决定范围**）。

**⇒ 三层**：
```text
§414  **`field00E4` 是 `8` 位 ⇒ `0..255`**
§419  **`7` 位 ⇒ `0..127`（而曲线的上限 `100`）**
§442  **`icon` `12` 位 ⇒ `0..0xFFF`；`teamNum` `4` 位 ⇒ `0..0xF`**
⇒ **⇒ 三次"位宽决定范围**】
```

**✅ ⭐⭐ **一个"位宽决定范围"的三例表**。

**⚠ 而"`entityNum <= EntityNumNone`（`2047`）"⇒ **允许 `2047`**。**

**⇒ 三层**：
```text
`entityNum` 可以是 `2047` = `EntityNumNone` ⇒ **一个合法的"没有"**
⇒ **⇒ 所以【这个域【包含它的哨兵**】】
```

**✅ 与 §416 的"`EntityNumNone = 2047`"**完全闭合 ✓

**⇒ 三层**：
```text
§417  **`2047` 是 `EntityNumNone`**
§442  **`setobjective` 接受 `2047`**
⇒ **⇒ 所以【一个 objective 可以【指向"没有实体"**】】
```

**✅ ⭐ **一个"哨兵在域内"的实例** —— 与 §439 的"`round 1..255` 排除 `0`"**对照**（**那里排除哨兵，这里包含**）。

**⇒ 三层**：
```text
§439  **`round` 排除 `0`**
§442  **`entityNum` 包含 `2047`**
⇒ **⇒ 所以【哨兵【是否合法【逐个字段决定**】】
```

**✅ ⭐⭐ **一个"哨兵是否合法"的对照**。</br>

**✅ 与前文"零是否合法逐个字段决定"**同族（**第五次**）。

## 四、**`setPlayerWeapons` 的 `permitsNone`**（本组第三重要）

### 4.1 那段

```cpp
std::array<std::uint16_t, 4> weaponIndexes{};
const auto selectedArgument = call.arguments.size() - 1;
for (std::size_t index{}; index < call.arguments.size(); ++index)
{
    const auto *const value = std::get_if<std::int64_t>(&call.arguments[index]);
    const auto permitsNone = index == selectedArgument;
    if (!value || *value < (permitsNone ? 0 : 1) || *value >= WeaponConfigStringCount)
    {
        return failure(InvalidArgumentValue,
            "setplayerweapons expects nonzero owned weapon indexes and a selected index or zero");
    }
    weaponIndexes[index] = static_cast<std::uint16_t>(*value);
}
const std::uint16_t supplemental = call.arguments.size() == 4 ? weaponIndexes[2] : 0;
const auto selected = weaponIndexes[selectedArgument];
```

### 4.2 二十层

```text
1. **`selectedArgument = arguments.size() - 1`** ⇒ **最后一个参数**
2. ⇒ **`permitsNone = (index == selectedArgument)`** ⇒ **只有最后一个可以 `0`**
3. ⇒ **⇒ 其它参数【必须 `>= 1`**】**
4. ⇒ **⇒ 所以【"武器索引 `0`" 只在【selected**】上合法**】
5. ⇒ **而 `supplemental` 只在【`4` 个参数时**】有值**
6. ⇒ **⇒ 所以【`3` 个参数 ⇒ `primary, secondary, selected`**】**
7. ⇒ **而【`4` 个参数 ⇒ `primary, secondary, supplemental, selected`**】**
```

### 4.3 ⭐⭐⭐ **"只有最后一个可以 `0`"**

**✅ 这是本报告里**最重要的一条"位置决定合法性**。**

**⇒ 三层**：
```text
`selected = 0` ⇒ **"没有选中任何武器"** ⇒ 合法（**空手**）
`primary = 0` ⇒ **"没有主武器"** ⇒ **而 §413 说空手不可用**（AV） ⇒ 拒绝
⇒ **⇒ 所以【同一个 `0` 在【不同位置**上有不同语义**】
```

**✅ 与 §435 的"`SvTeam::None` 有两个意思"**同族（**第五次"一值多义**）。

**⇒ 三层**：
```text
§406  `None` ⇒ "平局"
§416  `None` ⇒ 空指针
§435  `None` ⇒ 两种含义
§437  `-1` ⇒ 两种含义
§442  **`0` 在 `primary` 与 `selected` 上不同**
⇒ **⇒ 五次"一值多义**】
```

**✅ ⭐⭐⭐ **一个"一值多义"的五例表**。

**⚠ 而"`*value >= WeaponConfigStringCount` ⇒ 拒绝"**⇒ **上界对所有参数一致**。**

**⇒ 三层**：
```text
下界 ⇒ **逐位置**（`0` 或 `1`）
上界 ⇒ **统一**（`WeaponConfigStringCount-1`）
⇒ **⇒ 所以【只有下界是位置相关的**】
```

**✅ ⭐⭐ **"只有下界是位置相关的"**。

### 4.4 而**"`3` 或 `4` 个参数"**

```cpp
if (call.arguments.size() != 3 && call.arguments.size() != 4)
    ⇒ "setplayerweapons expects primary, secondary, optional supplemental, and selected indexes"
```

**⇒ 六层**：
```text
1. **`3` 或 `4` 个参数**
2. ⇒ **消息里【"optional supplemental"**】⇒ **正是那个可选的第三位**
3. ⇒ **⇒ 所以【`3` 个 ⇒ 无 supplemental**】**
4. ⇒ **而【`4` 个 ⇒ 有**】**
```

**✅ ⭐⭐ **"消息里说 optional"** —— 与 §436 的"`EXE_SERVERISFULL` 的两条不同消息"**同族（**第四次"消息的精确性**）。

**⇒ 三层**：
```text
§430  **"两个失败打印不同的字段"**
§436  **"两条不同消息"**
§442  **"消息里明说 optional"**
⇒ **⇒ 三次"消息要精确**】
```

**✅ ⭐ **一个"消息精确性"的三例表**。

## 五、**`weaponIndex`/`effectIndex` 的"是一个函数不是一个方法"**（本组第四重要）

### 5.1 那段

```cpp
if (call.self)
{
    return failure(
        SvScriptBuiltinErrorCode::InvalidSelf,
        "weaponindex is a function");
}
```

**⇒ 六层**：
```text
1. **`weaponindex` 【是一个函数**
2. ⇒ **一个【`self`**】⇒ **`InvalidSelf`**
3. ⇒ **消息说【"is a function"**】**
4. ⇒ **⇒ 所以【一个脚本用 `player:weaponindex(...)` 会【得到一个明确的错误**】】
```

### 5.2 ⭐⭐⭐ **"一个方法调用会得到一个明确的错误"**

**✅ 与 §438 的"`MissingSelf`"**——**互补** ✓

**⇒ 三层**：
```text
`validatePlayerMethod` ⇒ **`!self` ⇒ `MissingSelf`**（**一个方法被当作函数调用**）
`weaponIndex` ⇒ **`self` ⇒ `InvalidSelf`**（**一个函数被当作方法调用**）
⇒ **⇒ 所以【两个方向都有具名错误**】
```

**✅ ⭐⭐⭐ **"两个方向都有具名错误"** —— 与 §437 的"五个拒绝都返回同一个 `false`"**形成完整对照**。

**⇒ 三层**：
```text
§437  **八个原因 ⇒ 一个 `false`**（**缺陷**）
§438  **五道 ⇒ 五个码**
§442  **两个方向 ⇒ 两个具名错误**
⇒ **⇒ 三次"错误码的成熟度**】
```

**✅ ⭐⭐ **一个"错误码成熟度"的三例表**。

**⚠ 而"`name->size() >= 128`"⇒ **一个长度上界**。**

**⇒ 三层**：
```text
`weaponIndex`/`effectIndex` ⇒ **`< 128`**
`getEntArray`/`getMapEntityField` ⇒ **`<= 64`**
`setMapGameObjects` ⇒ **`<= 64`**
⇒ **⇒ 三个不同的长度上界**】
```

**✅ 与 §441 的"界由语义决定"**同族（**第六次**）。

**⇒ 三层**：
```text
武器/效果名 ⇒ **`< 128`**（**configstring 的名字可以更长**）
map entity 的 key ⇒ **`<= 64`**
game object 名 ⇒ **`<= 64`**
⇒ **⇒ 三个界，各由它的用途决定**】
```

**✅ ⭐⭐ **"三个界各由用途决定"**。

**⚠ 而"`name->find('\0') != std::string::npos`"⇒ **嵌入 NUL 的检查**。**

**⇒ 三层**：
```text
若一个名字含 `\0` ⇒ **在 C 字符串里【被截断**】
⇒ **⇒ 所以【必须显式拒绝**】
```

**✅ 与 §425 的 `parseUserInfo` 的 `\0` 截断**不同（那里**是协议的一部分**，这里**是一个错误**）。

**⇒ 三层**：
```text
§425  **`parseMessage` 在 `\0` 处【截断**】⇒ 合法
§441/§442  **`find('\0')` ⇒ 拒绝** ⇒ 非法
⇒ **⇒ 两个相反的处置，因为【两个不同的上下文**】
```

**✅ ⭐⭐⭐ **"两个相反的处置"** —— 与 §438 的"字符串列表用逗号串，对象列表用数组类型"**同族（**第三次"同一问题两个处置"）。

## 六、**`getMapEntityField` 的"缺失返回 `monostate`"**

```php
const auto value = world.mapEntityField(handle, *key);
return value ? success(*value) : success(std::monostate{});
```

**⇒ 六层**：
```text
1. **有值 ⇒ `success(*value)`**
2. ⇒ **没有 ⇒ `success(monostate{})`**
3. ⇒ **⇒ 所以【一个缺失的字段【不是错误**】**
4. ⇒ **⇒ 与 §440 的"一个空串是一个真实的答案"**同族**
```

**✅ ⭐⭐ **"一个缺失的字段不是错误"** —— 而 **`monostate` 是那个"无"的表示**。

**✅ 与 §416 的"`SvScriptValue` 的 `variant` 含 `monostate`"**配合。

**⇒ 三层**：
```text
`monostate` ⇒ **一个"无"的类型**
⇒ **⇒ 所以【脚本可以【用类型判断**来区分"有值"与"无值"】
```

**✅ ⭐⭐ **"用类型判断区分有值/无值"** —— 与 §440 的"用 `""` 表示无值"**对照**。

**⇒ 三层**：
```text
`zmZoneAt` ⇒ **`""`**（**字符串的空**）
`getMapEntityField` ⇒ **`monostate`**（**类型的空**）
⇒ **⇒ 两个"空"的表示**
```

**✅ ⭐⭐⭐ **"两个空的表示"** —— **而它们都优于"一个错误"**。</br>

**✅ 与前文"合法的空"**同族（**第六次**）。

## 七、**`isTouchingPlayer` 的五道（含一个额外的 `Playing` 检查）**

```cpp
validateEntityMethod(world, call, 1, handle)   ← 五道
player = get_if<SvScriptObjectRef>(arguments[0])
if (!player || player->kind != Player) ⇒ InvalidArgumentType
state = world.playerState(player->id)
gameplay = world.gameplayState(player->id)
if (!state || !gameplay) ⇒ ObjectNotFound
if (*gameplay != Playing) ⇒ InvalidObjectState
return world.logicalMapEntityTouchesPlayer(handle, player->id)
```

**⇒ 十层**：
```text
1. **实体侧五道**（`validateEntityMethod`）
2. ⇒ **而【玩家侧的四个检查【手写**】】
3. ⇒ **⇒ 因为 `validatePlayerMethod` 检查的是 【`call.self`**】**
4. ⇒ **而这里【玩家是 `arguments[0]`**】**
5. ⇒ **⇒ 所以【不能复用**那个验证器**】
```

### 7.1 ⭐⭐⭐ **"因为 `validatePlayerMethod` 检查的是 `call.self` 而这里玩家是 `arguments[0]`"**

**✅ 与 §441 的"两个验证器已经为错误的接收者返回正确的错误"**——**互补** ✓

**⇒ 三层**：
```text
§441  **`getOrigin` 的玩家是 `self` ⇒ 可复用 `validatePlayerMethod`**
§442  **`isTouchingPlayer` 的玩家是 `arguments[0]` ⇒ **必须手写四个检查**
⇒ **⇒ 所以【验证器的复用【取决于位置**】】
```

**✅ ⭐⭐⭐ **"验证器的复用取决于位置"** —— 一个**极精确的实现约束**。

**⚠ 而"玩家侧的四个检查【复制了 `validatePlayerMethod` 的后三道**】"⇒ **代码重复**。**

**⇒ 三层**：
```text
`validatePlayerMethod` ⇒ 五道
`isTouchingPlayer` 的玩家侧 ⇒ **四道（缺"参数个数"）** + 一道 `kind`
⇒ **⇒ 所以【四道重复**】
```

**⚠ 一个**可抽取的机会**（**标注**）。

**✅ 与项目指令的"三个相似的行比一个过早的抽象好"**——**四道可能超过那个阈值**。

## 八、关键结论

1. **⭐⭐⭐ "一个名字或一个裸索引：名字是首选而是一个真实脚本应该用的，但一个【模块化武器】（那正是大逃杀拾取实际上是的）在带里没有朴素名字可解析 —— 它的 configstring 是一个 `**` 定义，不是 `ak104dmz_mp`"`** —— 与 §430 的"`a` 的值域是 loot 带及其上方"完全闭合。
2. **⭐⭐⭐ "§414 的 `name.front() == '*'` 检查【不是防御性的而是语义性的**】**"：**`**` 前缀【确实**意味着"这是一个定义而不是一个名字"** ⇒ **§414 的规则在这里被确认**。
3. **⚠ 一个可推导的缺口**：**`giveweapon` 接受 `1..WeaponConfigStringCount-1` 的任何索引，而 `queueReliableCommand("a N")` 只接受静态或已注册的模块化索引 ⇒ 一个 `giveweapon` 到未注册的模块化索引会让武器在手而【没有 `a` 能显示它**】。
4. **⭐⭐⭐ `setObjective` 的五个域全部由线上的位宽决定**：`slot 0..31`（`32` 个槽）/ `state 0..5`（六个枚举）/ `icon 0..0xFFF`（`12` 位）/ `entityNum 0..EntityNumNone`（`2047`）/ `teamNum 0..0xF`（`4` 位）—— 第三次"位宽决定范围"（与 §414/§419 同族）。
5. **⭐⭐ `entityNum` 的域【包含**】它的哨兵 `2047`（`EntityNumNone`）**，而 **§439 的 `round` 【排除**】它的哨兵 `0`** ⇒ **"哨兵是否合法逐个字段决定"**（第五次"零是否合法"的延伸）。
6. **⭐⭐⭐ `setPlayerWeapons` 的 `permitsNone`：只有【最后一个参数**】（`selected`）可以是 `0`** ⇒ **`selected = 0` 是"没有选中任何武器"（合法，空手），而 `primary = 0` 会导致 §413 的 AV ⇒ 拒绝** —— **"同一个 `0` 在不同位置上有不同语义"**（第五次"一值多义"）。
7. **⭐ "只有下界是位置相关的，上界对所有参数一致"`**。
8. **⭐⭐ `weaponIndex`/`effectIndex` 的"是一个函数不是一个方法"**（`self` ⇒ `InvalidSelf` + 消息明说"is a function"）—— 与 §438 的 `MissingSelf`（**一个方法被当作函数调用**）**互补** ⇒ **"两个方向都有具名错误"**；与 §437 的"八个原因一个 `false`"形成完整对照。
9. **⭐⭐ 三个长度上界**：`weaponIndex`/`effectIndex` 的 `< 128`（**configstring 名字可以更长**）、`getEntArray`/`getMapEntityField` 的 `<= 64`、`setMapGameObjects` 的 `<= 64` ⇒ **"三个界各由用途决定"**（第六次"界由语义决定"）。
10. **⭐⭐⭐ 嵌入 `\0` 的两个相反处置**：**`parseMessage`（§425）在 `\0` 处【截断**】（**协议的一部分**）而 **`weaponIndex`/`getMapEntityField` 【拒绝**】（**一个错误**）—— "同一问题两个处置，因为两个不同的上下文"。
11. **⭐⭐ `getMapEntityField` 的"缺失返回 `monostate`"** ⇒ **"一个缺失的字段不是错误"** —— 而 **`monostate`（类型的空）与 `""`（字符串的空）是两个"空"的表示**，**都优于一个错误**（第六次"合法的空"）。
12. **⭐⭐⭐ `isTouchingPlayer` 的"因为 `validatePlayerMethod` 检查的是 `call.self` 而这里玩家是 `arguments[0]` ⇒ 不能复用那个验证器"`** ⇒ **"验证器的复用取决于位置"** —— 一个极精确的实现约束；而**玩家侧的四个检查复制了 `validatePlayerMethod` 的后三道**（**一个可抽取的机会，但四道可能超过"三行重复优于抽象"的阈值**）。

## 九、未闭合点

- `**` 定义的确切格式。
- `WeaponConfigStringCount` 的值。
- `EffectConfigStringCount` 的值。
- `SvScriptObjectArray` 与 `SvScriptValue` 的关系。
- `logicalMapEntityTouchesPlayer` 的实现。
- `sv_script_builtin_mp.cpp` 1720 行之后未读取（**共 `4424` 行**）。
