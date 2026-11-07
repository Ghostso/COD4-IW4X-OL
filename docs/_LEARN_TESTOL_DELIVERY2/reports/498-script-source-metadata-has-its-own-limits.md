# 498 · **"元数据执行【有分开的**分配器与指令限额**，但战役地图的 chunk 【也【携带【测量的**移动表** ⇒ **匹配【那个游戏源码的尺寸上限**，使那些地图【到达【它们早期的**元数据返回**，而不是【失败【那个文件大小的**预检**"** —— `sv_script_source_mp.cpp/.hpp`

## 一、范围

本报告学习 `sv_script_source_mp.cpp`（**`289` 行**）+ `.hpp`（**`61` 行**）：三个候选文件的拼接、预算的 `assign`/`clear`、`MapMetadataLuaLimits` 的 `512 KiB`/`100000`/`1000`、以及那唯一一个 `minimap_material`。

## 二、**"战役地图的 chunk 也携带测量的移动表 ⇒ 匹配那个游戏源码的尺寸上限"**（本组最重要的一段）

### 2.1 那段

```cpp
// Metadata execution has separate allocator and instruction limits,
// but campaign map chunks also carry measured movement tables. Match
// the gameplay source-size ceiling so those maps reach their early
// metadata return instead of failing the file-size precheck.
std::size_t maximumSourceBytes = 1024 * 1024);
```

### 2.2 二十四层

```text
1. **元数据执行【有分开的**分配器与指令限额**】
2. ⇒ **⇒ 而【战役地图的 chunk 【也【携带【测量的**移动表**
3. ⇒ **⇒ 所以【匹配【那个游戏源码的尺寸上限**】（`1 MiB`）
4. ⇒ **⇒ ⇒ 使那些地图【到达【它们【早期的**元数据返回**
5. ⇒ **⇒ 而不是【失败【那个文件大小的**预检**
```

### 2.3 ⭐⭐⭐ **"匹配那个上限，使那些地图到达它们早期的元数据返回"**

**✅ 这是本报告里**最重要的一条"**一个**上限【的**副作用**"**。**

**✅ 与 §496 的"从什么出现了来决定是哪种，而不是预先承诺一个形状"**——**同族** ✓

**⇒ 三层**：
```text
若【用一个**小的**上限（`512 KiB`**）⇒ **⇒ 战役地图【失败**】⇒ **⇒ 而【它们**本会【在【执行【一个**早期返回**后【成功**
匹配 ⇒ **⇒ 那些地图【都【通过**】
⇒ **⇒ 所以【那个上限【是【一个**必要条件的放宽**】
```

**✅ ⭐⭐⭐ **"那个上限是一个必要条件的放宽"**。

**⚠ 而那个**早期返回**】**。**

**⇒ 十层**：
```cpp
luaL_loadbufferx(state, source->data(), source->size(), chunkName.c_str(), "t") != LUA_OK ||
lua_pcall(state, 0, 1, 0) != LUA_OK || !lua_istable(state, -1)
```
```text
1. **`lua_pcall(state, 0, 1, 0)` 【期待【一个**返回值**】
2. ⇒ **⇒ 而 `lua_istable(state, -1)` ⇒ 【那个返回值【必须【是一个**表**
3. ⇒ **⇒ 所以【一个地图的 `.lua` 【必须【返回【一个**表**】（**⇒ 而【那个"早期返回**"【正是【那个 `return { minimap_material = ... }`）
```

**✅ ⭐⭐⭐ **"那个『早期返回』正是那个 return { minimap_material = ... }"** —— 而**注释说**"**campaign map chunks also carry measured movement tables**"** ⇒ **所以【那个文件【很**大**（**因为【那些表**）而【那个 `return` 【在**很前面**】**。**

**⚠ 一个**可推导的观察**：那个 `.lua` 【可能【有【一个【很**靠前**的 `return`，而【其后的**移动表**码【根本【不【被执行**（**因为 Lua 的 `return` 【终止【那个 chunk**）**。**

**⇒ 十层**：
```text
`return { ... }` 在【文件**前部**】
⇒ **⇒ 而后面的**移动表定义【不【被执行**
⇒ **⇒ 所以【那个 `100000` 条指令【足够**】
```

**✅ ⭐⭐⭐ **"那个 100000 条指令足够，因为那个 return 终止了那个 chunk"**。

## 三、那三个候选文件的拼接（本组第二重要）

### 3.1 三个

```cpp
const std::array candidates{
    scriptRoot / "common.lua",
    scriptRoot / "gametypes" / (std::string(gameType) + ".lua"),
    scriptRoot / "maps" / (std::string(mapName) + ".lua"),
};
```

### 3.2 二十四层

```text
1. **`common.lua` ⇒ 全局**】
2. ⇒ **⇒ `gametypes/<gt>.lua` ⇒ 模式**】
3. ⇒ **⇒ `maps/<map>.lua` ⇒ 地图**】
4. ⇒ **⇒ 而【缺一个【不**拒绝**】（`if (!exists) continue`**）
5. ⇒ **⇒ 而【全部**缺**才【`NoSource`
```

### 3.3 ⭐⭐⭐ **"缺一个不拒绝，而全部缺才 NoSource"**

**✅ 与 §465 的"`formatMiniMap` 的三道字符检查"**——**不同**，但与 §493 的"四层回退"**同族**（**第二次"一个**分级【的**失败**"**）。

**⇒ 三层**：
```text
若【缺一个【就拒绝**】⇒ **⇒ 大多数地图【会【失败**】（**因为【大多数【没有【一个【自己的** `.lua`）
而【缺【三个**才【`NoSource`】⇒ **⇒ 而【`common.lua` 【通常【存在**
⇒ **⇒ 所以【那个**部分成功【是【必须的**
```

**✅ ⭐⭐⭐ **"那个部分成功是必须的"**。

**⚠ 而那个**拼接【的包装**】**。**

**⇒ 十六层**：
```cpp
const std::string prefix = "-- source: " + relative + "\ndo\n";
constexpr std::string_view suffix = "\nend\n";
result.source.append(prefix);
result.source.append(source);
result.source.append(suffix);
```
```text
1. **`-- source: <relative>` ⇒ 一个**行注释**】⇒ **⇒ 使【一个**错误【能【指向【那个文件**
2. ⇒ **⇒ 而 `do ... end` ⇒ 一个**块**
3. ⇒ **⇒ 所以【那个 `local` 【不会【泄漏**到【下一个文件**
4. ⇒ **⇒ 而【那【正是【三个文件【被【拼成【一个 chunk**的【正确方式**
```

**✅ ⭐⭐⭐ **"do ... end 使 local 不泄漏到下一个文件"** —— 一个**极重要的 Lua 语义**。

**✅ 与 §469 的 `openRestrictedLibraries`**——**同族**（**第三次"一个**Lua 的作用域**"**）。

**⚠ 而那个 `maximumSourceBytes - result.source.size()` 的**递减预算**】**。**

**⇒ 十层**：
```cpp
const auto remaining = maximumSourceBytes - result.source.size();
if (prefix.size() > remaining ||
    source.size() > remaining - prefix.size() ||
    suffix.size() > remaining - prefix.size() - source.size())
```
```text
1. **三条**减法之前【都有**检查**】
2. ⇒ **⇒ 所以【那个 `size_t` 【不会**下溢**
3. ⇒ **⇒ 而【那【是那个**递减预算**的正确写法**
```

**✅ ⭐⭐⭐ **"三条减法之前都有检查，所以 size_t 不会下溢"** —— 一个**极精确的实现**。

**✅ 与 §484 的"`bytes > readAt` ⇒ 拒绝"**——**同族**（**第三次"一个**size_t 下溢的守卫**"**）。

**⇒ 三层**：
```text
§469  **`allocator.usedBytes -= min(...)`**
§484  **`if (bytes > readAt) error`**
§498  **三条 `> remaining` 检查**
⇒ **⇒ 三次【一个**无符号减法**的守卫**
```

**✅ ⭐⭐⭐ **"一个无符号减法的守卫"三例**。

## 四、`SV_IsValidGameplaySourceSelection` 的五元字符集

### 4.1 那段

```cpp
return !value.empty() && value.size() <= 64 &&
    std::ranges::all_of(value, [](const unsigned char character) {
        return character == '_' || character == '-' ||
            character >= '0' && character <= '9' ||
            character >= 'A' && character <= 'Z' ||
            character >= 'a' && character <= 'z';
    });
```

### 4.2 二十四层

```text
1. **非空 + `<= 64`**】
2. ⇒ **⇒ 而【五个**字符集**：`_` / `-` / `0-9` / `A-Z` / `a-z`**】
3. ⇒ **⇒ 与 §496 的 `validName` 的**四个**差【一个 `-`**】
```

### 4.3 ⭐⭐⭐ **"与 §496 的 validName 差一个 `-`"**

**✅ 与 §496 的四字符集**——**一个精确的对照** ✓

**⇒ 三层**：
```text
§496  **`validName`：`_` / `0-9` / `A-Z` / `a-z`**（**用于【那个**地图名【与【那个 gametype**
§498  **`SV_IsValidGameplaySourceSelection`：+ `-`**（**用于【那个**文件名的选择**）
⇒ **⇒ 所以【后者【允许【一个 `mp-crash`**】而【前者【不**
```

**✅ ⭐⭐⭐ **"后者允许一个 mp-crash 而前者不"** —— 一个**值得注意的不一致**（**同一个概念【两个**谓词**）**。**

**⚠ 而 `<= 64` 的**上界**】**。**

**⇒ 十层**：
```text
`<= 64` ⇒ **⇒ 而【§479 的 `SV_BotNavCandidatePaths` 【没有【一个**长度**界**】（**只有三条逃逸判据**）
⇒ **⇒ 所以【两个**文件名【的选择【两个**不同的**守卫**
```

**✅ ⭐⭐⭐ **"两个文件名的选择两个不同的守卫"**。

**✅ 与 §479 的"三条路径逃逸判据"**——**同族**（**第四次"一个**路径【的**白名单**"**）。

## 五、`MapMetadataLuaLimits` 的三个预算

### 5.1 三个

```text
MapMetadataMaximumMemoryBytes        512 * 1024      = 512 KiB
MapMetadataMaximumInstructions       100'000
MapMetadataInstructionHookInterval   1'000
```

### 5.2 二十四层

```text
1. **`512 KiB` 内存**】⇒ **⇒ 而 §469 的 `SvLuaRuntime` 是 **`8 MiB`**】⇒ **⇒ 那个元数据【是** 1/16**
2. ⇒ **⇒ `100000` 条指令**】⇒ **⇒ 而 §469 的是 **`1,000,000`**】⇒ **⇒ 也是 1/10**
3. ⇒ **⇒ 而 `1000` 的间隔**】⇒ **⇒ 与 §469 的**同一个**
```

### 5.3 ⭐⭐⭐ **"元数据是 512 KiB / 100000，而运行时的 Lua 是 8 MiB / 1000000"**

**✅ 与 §469 的 `SvLuaRuntimeLimits`**——**一个精确的对照** ✓

**⇒ 独立对照**：
```text
               元数据              运行时         比值
内存        512 KiB            8 MiB          1/16
指令        100,000            1,000,000      1/10
间隔        1,000              1,000          1
⇒ **⇒ 所以【那个**间隔【相同**而【两个**上限【不同**
```

**✅ ⭐⭐⭐ **"间隔相同而两个上限不同"** —— 而**那【是【一个**极清晰的**分级**】。**

**✅ 与 §494 的三档血统**——**同族**（**第四次"一个**分级的**预算**"**）。

**⚠ 而 `allocateMapMetadataLua` 与 §469 的 `allocate` 是**同一个模式**】**。**

**⇒ 十层**：
```text
§469  **`accountedOldSize = pointer ? oldSize : 0`，而【只【看**增量**
§498  **同一个模式**（**逐字**）
⇒ **⇒ 所以【那个**分配器【被【复制**了**】⇒ **⇒ 而【那【是【一个【**可报告**的重复】
```

**⚠ 一个**可报告的重复**：`allocateMapMetadataLua` 与 `SvLuaRuntime::Impl::allocate` 是**逐字的同一个函数**（**除那个 `limits` 的类型**）⇒ **⇒ 那【可以【被【提取**成一个模板**）**。**

**✅ 与 §497 的"同一个常数住在两个地方"**——**同族**（**第五次"一个**重复**的病灶**）**。**

**⇒ 三层**：
```text
§497  **同一个常数【两个地方**】
§498  **同一个函数【两个地方**】
⇒ **⇒ 两次【同一个**重复【的类型**】（**一个【常数**，一个【**函数**）
```

**✅ ⭐⭐⭐ **"同一个重复的两个类型：一个常数，一个函数"**。

**⚠ 而那个 `mapMetadataInstructionHook` 与 §469 的 `instructionHook`**】**。**

**⇒ 层**：
```text
§469  **`if (remaining <= interval) { remaining = 0; luaL_error(...); }`**
§498  **`if (!limits || remaining <= interval) { if (limits) remaining = 0; luaL_error(...); }`**
⇒ **⇒ 同一个模式【加【一个 `!limits` 的守卫**
```

**✅ ⭐⭐⭐ **"同一个模式加一个 !limits 的守卫"** —— 而**§498 的【更**防御**（**因为【那个 `extraspace` 【可能【是**空**）**。**

## 六、那个 `minimap_material` 的五道校验

### 6.1 五道

```text
① `lua_isnil` ⇒ 缺席（合法）
② `lua_type == LUA_TSTRING` ⇒ 必须
③ `length` 非零且 `<= 255`
④ 无 `"` 或 `\`
⑤ 无 `\0`
```

### 6.2 二十四层

```text
1. **五道，而【第 ① 道【是【一个**缺席合法**】**】
2. ⇒ **⇒ 而【第 ④ 道的**两个字符**（`"` / `\`）【与 §470 的 `formatMiniMap` **完全一致**】
3. ⇒ **⇒ 而【第 ③ 道的 `255` 【也【与 §470 的 `> 255` **一致**】
```

### 6.3 ⭐⭐⭐ **"第 ③ ④ ⑤ 道与 §470 的 formatMiniMap 完全一致"**

**✅ 与 §470 的 `formatMiniMap`**——**完全同族** ✓

**⇒ 三层**：
```text
§470  **`miniMap.material.empty() || size() > 255 || find_first_of("\"\\") != npos || find('\0') != npos` ⇒ 拒绝**
§498  **`!length || length > 255 || find_first_of("\"\\") != npos || find('\0') != npos` ⇒ 拒绝**
⇒ **⇒ 一个**逐条对应**的模型**
```

**✅ ⭐⭐⭐ **"一个逐条对应的模型"** —— 而**§498 的【那个 `!length`（**零长度**）【是【§470 的 `empty()`**】**。**

**⚠ 而"那个 `minimap_material` 【是【唯一**的元数据**"**】**。**

**⇒ 十层**：
```cpp
struct SvMapScriptMetadata
{
    std::optional<std::string> miniMapMaterial;
    bool operator==(const SvMapScriptMetadata &) const = default;
};
```
```text
1. **只有一个**字段**
2. ⇒ **⇒ 所以【那些 `.lua` 【可能【返回【更多**字段，而【这里【只【读【一个**
3. ⇒ **⇒ 而【那【是【一个**有意的**最小化**（**与 §468 的"没有见证的值故意缺席"**同族**）
```

**✅ ⭐⭐⭐ **"那是一个有意的最小化"**。

## 七、`luaL_loadbufferx(..., "t")` 的"只接受文本"

### 7.1 那段

```cpp
if (luaL_loadbufferx(state, source->data(), source->size(), chunkName.c_str(), "t") != LUA_OK || ...)
```

### 7.2 二十四层

```text
1. **`"t"` ⇒ **只接受**文本**】（**与 §469 的 `luaL_loadbufferx(..., "t")` **完全一致**）
2. ⇒ **⇒ 所以【一个【预编译的**字节码【会被**拒绝**
```

### 7.3 ⭐⭐⭐ **"与 §469 的 't' 模式完全一致"**

**✅ 与 §469 的 `luaL_loadbufferx(..., "t")`**——**完全同族** ✓

**⇒ 三层**：
```text
§469  **`luaL_loadbufferx(..., "t")` 且 `string.dump` 被删**（**双保险**）
§498  **`luaL_loadbufferx(..., "t")`**（**但【没有【那个库的**删除**）**
⇒ **⇒ 所以【§469 的【更**防御**
```

**✅ ⭐⭐⭐ **"§469 的更防御"** —— 而**§498 【的 chunk 【是一个**地图脚本**（**不是【一个**用户输入的脚本**）**。**

**⚠ 而那个 `chunkName = "@" + path.generic_string()`**】**。**

**⇒ 十层**：
```text
`"@"` 前缀 ⇒ **⇒ 一个**文件**名**（**不是【一个**字符串**）
⇒ **⇒ 所以【一个**错误【会【打印【一个**文件名**】（**而不是【那个**代码**
```

**✅ ⭐⭐⭐ **"'@' 前缀意味着一个文件名，所以一个错误会打印一个文件名而不是那个代码"** —— 与 §469 的 `"@" + sourceName` **完全一致**。

## 八、`readSourceFile` 的三条

### 8.1 三条

```cpp
if (!std::filesystem::is_regular_file(path, error) || error) return std::nullopt;
const auto size = std::filesystem::file_size(path, error);
if (error || size > maximumSourceBytes) return std::nullopt;
...
return !stream.bad() && source.size() == size ? std::optional{ std::move(source) } : std::nullopt;
```

### 8.2 二十四层

```text
1. **`is_regular_file` 且无 error**】
2. ⇒ **⇒ `file_size` 且 `<= maximumSourceBytes`**】
3. ⇒ **⇒ 而【读回后 `!bad` 且 `size() == size`**】（**一个**恰好用尽**）
```

### 8.3 ⭐⭐⭐ **"`source.size() == size` 是一个恰好用尽的检查"**

**✅ 与 §468 的"`p == storage.size()`"**、§482 的"`22940/22940`"**——**完全同族** ✓

**⇒ 三层**：
```text
§468  **`p == storage.size()`**
§482  **`consumed == total`**
§498  **`source.size() == size`**
⇒ **⇒ 三次"一个**恰好用尽【是【一个**可判定的正确性**"**
```

**✅ ⭐⭐⭐ **"一个恰好用尽是唯一的可判定的正确性"三例**。

**⚠ 而"`!stream.bad()`"**】**。**

**⇒ 三层**：
```text
`bad()` ⇒ **一个**I/O 错误**】
而 `fail()` ⇒ **可能是【一个正常的 **EOF**
⇒ **⇒ 所以【用 `bad` 而【不是 `fail`**【是【正确的**
```

**✅ ⭐⭐⭐ **"用 bad 而不是 fail 是正确的"** —— 一个**极精确的**区分**。**

## 九、关键结论

1. **⭐⭐⭐ "元数据执行有分开的分配器与指令限额，但**战役地图的 chunk 也携带测量的移动表** ⇒ **匹配那个游戏源码的尺寸上限**，使那些地图到达它们**早期的元数据返回**而不是失败那个文件大小的预检"** ⇒ **"那个上限是一个必要条件的放宽"**；而**那个"早期返回"正是那个 `return { minimap_material = ... }`** ⇒ 因为 **Lua 的 `return` 终止那个 chunk**，所以其后那些移动表**根本不执行** ⇒ **"那个 100000 条指令足够"**。
2. **⭐⭐⭐ 三个候选文件**（`common.lua` / `gametypes/<gt>.lua` / `maps/<map>.lua`）⇒ **"缺一个不拒绝，而全部缺才 `NoSource`"** ⇒ **"那个部分成功是必须的"**（因为**大多数地图没有自己的 `.lua`**）。
3. **⭐⭐⭐ 那个拼接的包装 `-- source: <relative>\ndo\n … \nend\n`** ⇒ **"`do ... end` 使 `local` 不泄漏到下一个文件"**（一个极重要的 Lua 语义）。
4. **⭐⭐⭐ 那个递减预算的三条检查**（`prefix.size() > remaining` / `source.size() > remaining - prefix.size()` / `suffix.size() > remaining - prefix.size() - source.size()`）⇒ **"三条减法之前都有检查，所以 `size_t` 不会下溢"** —— 与 §469/§484 **三次"一个无符号减法的守卫"**。
5. **⭐⭐⭐ `SV_IsValidGameplaySourceSelection` 的五字符集（`_` / `-` / `0-9` / `A-Z` / `a-z`）+ `<= 64`** 与 §496 的 `validName` 的**四字符集**差一个 `-` ⇒ **"后者允许一个 `mp-crash` 而前者不"**（**同一个概念两个谓词**）；而 §479 的 `SV_BotNavCandidatePaths` **没有长度界**（只有三条逃逸判据）⇒ **"两个文件名的选择两个不同的守卫"**。
6. **⭐⭐⭐ 三个预算的对照**：**元数据 `512 KiB` / `100000` / `1000`** vs **§469 的运行时 `8 MiB` / `1000000` / `1000`** ⇒ **"间隔相同而两个上限不同"**（`1/16` 与 `1/10`）—— **一个极清晰的分级**。
7. **⚠ 一个可报告的重复**：`allocateMapMetadataLua` 与 `SvLuaRuntime::Impl::allocate` 是**逐字的同一个函数**（只有 `limits` 类型不同）⇒ 与 §497 的"同一个常数两个地方"构成 **"同一个重复的两个类型：一个常数，一个函数"**；而 `mapMetadataInstructionHook` 与 §469 的 `instructionHook` 是**同一个模式加一个 `!limits` 的守卫**（**§498 的更防御**）。
8. **⭐⭐⭐ 那个 `minimap_material` 的五道校验与 §470 的 `formatMiniMap` 完全逐条对应**（`empty`/`255`/`"` 与 `\`/`\0`）⇒ **"一个逐条对应的模型"**；而 `SvMapScriptMetadata` **只有一个字段** ⇒ **"那是一个有意的最小化"**。
9. **⭐⭐⭐ `luaL_loadbufferx(..., "t")` 与 §469 完全一致，而 §469 的更防御**（它也删了 `string.dump`）—— 因为 **§498 的 chunk 是一个地图脚本，不是一个用户输入的脚本**；而 `"@"` 前缀 ⇒ **"一个错误会打印一个文件名而不是那个代码"**。
10. **⭐⭐⭐ `readSourceFile` 的 `source.size() == size`** ⇒ **"一个恰好用尽是唯一的可判定的正确性"**（第三次，与 §468/§482 同族）；而 **"用 `bad` 而不是 `fail` 是正确的"**（`fail` 可能是正常的 EOF）。

## 十、`sv_script_source_mp` 全文件总览

**`.cpp`：`289` 行。`.hpp`：`61` 行。**

**`3` 个元数据常量**：`512 KiB` / `100'000` / `1000`。

**`5` 个 `SvGameplaySourceLoadError`**：`None` / `InvalidSelection` / `NoSource` / `ReadFailed` / `SourceTooLarge`。

**`6` 个函数**：`allocateMapMetadataLua` / `mapMetadataInstructionHook` / `readSourceFile` / `SV_GameplaySourceLoadErrorName` / `SV_IsValidGameplaySourceSelection` / `SV_LoadGameplaySource` / `SV_LoadMapScriptMetadata`。

**`3` 个候选文件**：`common.lua` / `gametypes/<gt>.lua` / `maps/<map>.lua`。

**`1` 个字段**：`minimap_material`。

## 十一、未闭合点

- 那些地图 `.lua` 的"早期返回"的确切位置。
- `SvMapScriptMetadata` 是否应该还有别的字段。
- `allocateMapMetadataLua` 与 `allocate` 的重复是否可以合并（一个模板）。
- 下一个文件：`sv_melee_mp.cpp/.hpp`（`9,841` / `5,242`）或 `sv_weapon_movement_mp.*`。
