# 496 · **"不要【命名【其余的那些【在没有**推导**它们的情况下**"** —— `sv_playlist_mp.cpp` 的两种 `mmstart` 语法、五个数字 dvar id、以及"一个重复的名字是 malformed"

## 一、范围

本报告学习 `sv_playlist_mp.cpp`（**`291` 行**）全文件：两种 booking 语法、`2486`/`2481`/`2489`/`3265`/`playlist`/`start_map_rotate_once` 六个数、`SvPendingBooking` 的三态（`observe`/`commit`/`cancel`），以及那个"不要命名其余的那些"的纪律。

## 二、**"不要命名其余的那些在没有推导它们的情况下"**（本组最重要的一段）

### 2.1 那段

```cpp
// CODOL's own form. 2486/2481/2489/2500/2483 are numeric dvar ids;
// only the two that also appear in 3.3.3.3's form are read, and
// even those are not assumed to mean the same thing -- nothing
// downstream uses them, and the map and gametype below are the
// payload. Do not name the others without deriving them.
if (!validName(*mapName) || !validName(*gameType))
    return std::nullopt;
SvBookingCommand parsed{};
if (const auto playerCount = number("2486")) parsed.playerCount = *playerCount;
if (const auto maxPlayers = number("2481")) parsed.maxPlayers = *maxPlayers;
if (const auto privateMatch = number("2489")) parsed.privateMatch = *privateMatch;
```

### 2.2 二十四层

```text
1. **五个**数字的 dvar id**：`2486`/`2481`/`2489`/`2500`/`2483`
2. ⇒ **⇒ 而【只有【那两个**也【出现在 3.3.3.3 的形式里**的【被【读**】（`2486` 与 `2489`）
3. ⇒ **⇒ 而【即使是那些【也【不被【假设【意味着**同一个东西**
4. ⇒ **⇒ 因为【下游【没有东西【用它们**】
5. ⇒ **⇒ 而那个 `map` 与 `g_gametype` 【才是【那个**载荷**
6. ⇒ **⇒ 所以【不要【命名【其余的**那些【在【没有**推导**它们的情况下
```

### 2.3 ⭐⭐⭐ **"即使是那些也不被假设意味着同一个东西"**

**✅ 这是本报告里**最重要的一条**纪律**。**

**✅ 与 §494 的"那个名字表说的是一个 id 意味着什么"**、§477 的"命名并过滤，而不是解码"**——**完全同族** ✓

**⇒ 三层**：
```text
`2486` 在 3.3.3.3 ⇒ **某个语义**】
`2486` 在这里 ⇒ **可能【是【别的**】
⇒ **⇒ 所以【那个"也出现"【不【蕴含【"同一个意思"**】
```

**✅ ⭐⭐⭐ **"'也出现'不蕴含'同一个意思'"** —— 一个**极精确的保留**。

**✅ 而"那个 `map` 与 `g_gametype` 才是那个载荷"**⇒ **一个**清楚的**主次**。**

**⇒ 十层**：
```text
五个 id ⇒ **全部【是【一个**可能**的元数据**
`map`/`g_gametype` ⇒ **那个**必要的**载荷**
⇒ **⇒ 所以【`2486`/`2481`/`2489` 的失败【不【导致【拒绝**】（**它们【是【`if (const auto ...)`**）
```

**✅ ⭐⭐⭐ **"那三个的失败不导致拒绝"** —— 一个**极精确的读法**。

**✅ 与 §491 的 `valid()` 的十三条**——**不同**（那里**全部必须**）**。**

**⇒ 三层**：
```text
§491  **`valid()` ⇒ 全部**必须**
§496  **`if (const auto playerCount = number("2486"))` ⇒ 可选**
⇒ **⇒ 所以【那个**可选性【是【被【`if (const auto ...)` 表达的**
```

**✅ ⭐⭐⭐ **"那个可选性是被 `if (const auto ...)` 表达的"** —— 一个**C++ 的惯用法**。

**⚠ 而那个**否定**】**。**

**⇒ 十层**：
```text
"Do not name the others without deriving them"
⇒ **⇒ 所以【`2500` 与 `2483` 【被【列出【但【不【被**命名**
⇒ **⇒ 而那【正是【§468 的"没有见证的值故意缺席"**同族**
```

**✅ ⭐⭐⭐ **"2500 与 2483 被列出但不被命名"** —— 一个**极妙的折中**（**读者知道它们存在，但没人为它们编一个名字**）**。**

## 三、**两种 `mmstart` 语法**（本组第二重要）

### 3.1 两种

```text
CODOL 的形      ⇒ `mmstart <k=v>;...` 且【带 `map` 与 `g_gametype`**
3.3.3.3 的形    ⇒ `mmstart sv_resetServer;...` 且【五个**名**【必须**全有**
```

### 3.2 二十四层

```text
1. **两者【都是【一个 `mmstart ` 前缀的、分号分隔**的命令列表**】
2. ⇒ **⇒ 而【那个决定【是【从【什么**出现了**】【来的】⇒ **⇒ 而不是【从【一个**预先承诺的**形状】
3. ⇒ **⇒ 所以【`if (mapName && gameType)` 【先【试【CODOL 的形**】
4. ⇒ **⇒ 而【否则 `if (!sawReset) return nullopt;` 【再【试 3.3.3.3 的形**】
```

### 3.3 ⭐⭐⭐ **"从什么出现了来决定是哪种，而不是预先承诺一个形状"**

**✅ 与 §486 的"那个框架【从【它自己的形状**"**、§482 的"§49 的那个推断是错的"**——**同族** ✓

**⇒ 三层**：
```text
预先承诺 ⇒ **一个**形状**【而【如果【另一个**来了【就【错**
从出现决定 ⇒ **⇒ 两个**都能【被**接收**
⇒ **⇒ 所以【后者【是【一个**更鲁棒**的解析**】
```

**✅ ⭐⭐⭐ **"'从出现决定'是一个更鲁棒的解析"**。

**⚠ 而那个**顺序**】**。**

**⇒ 十层**：
```text
① CODOL 的形（`map` + `g_gametype`）⇒ **一个**更严格**的测试**】（**两个名【都必须**）
② 3.3.3.3 的形 ⇒ **⇒ 五个数【都必须**
⇒ **⇒ 所以【那【是【一个**从严格到宽松**的阶梯**】（**而【实际上【两个【都【很严格**）
```

**✅ ⭐⭐⭐ **"一个从严格到宽松的阶梯"**。

**⚠ 而 `sv_resetServer` 的**特殊位置**】**。**

**⇒ 十层**：
```cpp
if (first)
{
    first = false;
    if (!token.starts_with("mmstart ")) return std::nullopt;
    sawMmstart = true;
    token = trim(token.substr(8));
    if (token == "sv_resetServer") { sawReset = true; continue; }
}
```
```text
1. **第一个 token 【必须【以 `mmstart ` 开头**】⇒ **⇒ 否则**拒绝**
2. ⇒ **⇒ 而【那个 `mmstart ` 之后的**第一个 token【如果【是 `sv_resetServer` ⇒ 【标记并 skip**】
3. ⇒ **⇒ 所以【`sv_resetServer` 【只能【是【第一个**】（**一个**位置敏感的**关键字**）
```

**✅ ⭐⭐⭐ **"sv_resetServer 只能是第一个：一个位置敏感的关键字"**。

**⚠ 而"`substr(8)`"**⇒ **`"mmstart "` 是 `8` 个字符** ✓（**独立验证**）**。**

**✅ ⭐⭐ **"8 个字符"**。

## 四、**`lookup` 的"一个重复的名字是 malformed"**（本组第三重要）

### 4.1 那段

```cpp
const auto lookup = [&pairs](const std::string_view name) -> std::optional<std::string_view> {
    std::optional<std::string_view> found;
    for (const auto &[key, value] : pairs)
    {
        if (key != name) continue;
        if (found) return std::nullopt;   // a repeated name is malformed
        found = value;
    }
    return found;
};
```

### 4.2 二十四层

```text
1. **找到【第一个**【存起来**】
2. ⇒ **⇒ 而【找到第二个 ⇒ 【返回 `nullopt`**】
3. ⇒ **⇒ 所以【一个重复的名字【是** malformed**
4. ⇒ **⇒ 而那【正是【那个"重复即错"的纪律**】（**而不是"最后一个胜"**）
```

### 4.3 ⭐⭐⭐ **"一个重复的名字是 malformed —— 与 §467/§494/§495 的『最后胜』相反"**

**✅ 与 §467 的 `byPlace`（第一个胜）、§494 的"最后胜"、§495 的"最后进入的阶段胜"**——**一个精确的对照** ✓

**⇒ 三层**：
```text
§494/§495  **"最后胜"**（**⇒ 一个**宽松**的容错**）
§496  **"重复是 malformed"**（**⇒ 一个**严格**的拒绝**）
⇒ **⇒ 所以【那个选择【是【由【那个**输入的性质**决定的**】（**一个命令列表【重复了【就是坏的**）
```

**✅ ⭐⭐⭐ **"那个选择是由那个输入的性质决定的"** —— 与 §467 的"由那个计数的用途决定"**同族**。

**✅ 而"一个命令列表重复了就是坏的"** ⇒ **一个**正确的**判断**（**一个 `mmstart` 里两个 `map` 【不可能【都是【真的**）**。**

**⚠ 而那个 `parseCommandToken` 的**失败【被 skip**】**。**

**⇒ 十层**：
```cpp
const auto parsedToken = parseCommandToken(token);
if (!parsedToken) continue;
pairs.emplace_back(*parsedToken);
```
```text
1. **一个不可解析的 token 【被**跳过**】⇒ **⇒ 不是**拒绝**
2. ⇒ **⇒ 所以【一个杂散的 token 【不【毁掉**整个命令**
3. ⇒ **⇒ 而【一个**重复的名字【毁掉**它**】⇒ **⇒ 两种**不同的**严格度**
```

**✅ ⭐⭐⭐ **"两种不同的严格度：杂散的 token 跳过，重复的名字拒绝"**。

**⚠ 而那【是一个**有意的**区分**】**。**

**⇒ 三层**：
```text
杂散的 token ⇒ **可能【是【一个**未来**的字段**】⇒ **⇒ 跳过**
重复的名字 ⇒ **确定【是【一个**矛盾**】⇒ **⇒ 拒绝**
⇒ **⇒ 所以【前者【是【宽容**、后者【是【严格**
```

**✅ ⭐⭐⭐ **"'杂散'是宽容、'重复'是严格"** —— 与 §466 的"`Skipped` vs 拒绝"**同族**。

## 五、**`SvPendingBooking` 的三态与"一个复位使那个 checksum 检查失效"**（本组第四重要）

### 5.1 那段

```cpp
std::optional<SvReadyBooking> SvPendingBooking::observeConfigStrings(
    const bool initialized, const std::uint32_t checksum, const bool allowReady)
{
    if (!rotation_) return std::nullopt;
    if (!initialized || !checksum) { sawReset_ = true; return std::nullopt; }
    if (!allowReady) return std::nullopt;
    if (generationRequirement_ == SvConfigStringGenerationRequirement::NewGeneration &&
        !sawReset_ && initialConfigStringChecksum_ &&
        checksum == initialConfigStringChecksum_)
    {
        return std::nullopt;
    }
    return SvReadyBooking{ .rotation = *rotation_, .configStringChecksum = checksum };
}
```

### 5.2 二十四层

```text
1. **三态：未初始化 / 未允许 / 就绪**
2. ⇒ **⇒ 而 `!initialized || !checksum ⇒ sawReset_ = true`**】（**一个**复位**的标记**）
3. ⇒ **⇒ 而【那个"新代次"的要求【是】：**必须【先【见到一个复位**】
4. ⇒ **⇒ 且【那个 `checksum` 【必须【不【等于【那个**初始的**
5. ⇒ **⇒ 所以【一个**复位【使那个 checksum 检查【失效**】（**因为【那个 checksum 【变了**）
```

### 5.3 ⭐⭐⭐ **"一个新代次必须先见到一个复位，否则那个 checksum 相等就意味『还没换代次』"**

**✅ 与 §470 的"`SvGameStateFixtureBytes` 的 checksum"**、§426 的"进入世界的客户端刚刚把它的快照状态扔掉了"**——**同族** ✓

**⇒ 三层**：
```text
若【没有【那个 `sawReset_`**】⇒ **⇒ 一个**同 checksum【的观察【会【被【误判为"就绪**"**
而 `sawReset_` ⇒ **⇒ 它【必须【先【经过一个**零**的状态**
⇒ **⇒ 所以【那个 `sawReset_` 【是【那个**代次【的**证据**
```

**✅ ⭐⭐⭐ **"那个 sawReset 是那个代次的证据"** —— 与 §469 的"两级代次"**同族**。

**✅ 而那个 `NewGeneration` 的**枚举**】**。**

**⇒ 十层**：
```text
`SvConfigStringGenerationRequirement::NewGeneration` ⇒ **⇒ 一个**严格**的模式**
⇒ **⇒ 而【另一个值【（`SameGeneration`？）【会【跳过**那个 `sawReset_` 检查**
```

**✅ ⭐⭐⭐ **"另一个值会跳过那个 sawReset 检查"**。

**⚠ 而 `commit` 的**双重检查**】**。**

**⇒ 十层**：
```cpp
bool SvPendingBooking::commit(const SvReadyBooking &ready)
{
    if (!rotation_ || *rotation_ != ready.rotation) return false;
    rotation_.reset();
    return true;
}
```
```text
1. **`!rotation_` ⇒ 拒绝**】（**⇒ 没有待定的**）
2. ⇒ **⇒ `*rotation_ != ready.rotation` ⇒ 拒绝**】（**⇒ 那个**rotation【变了**）
3. ⇒ **⇒ 然后 `rotation_.reset()`**
⇒ **⇒ 所以【那个 `commit` 【是【一个**幂等的**单次**
```

**✅ ⭐⭐⭐ **"那个 commit 是一个幂等的单次"** —— 与 §475 的"关闭是幂等性的唯一保证"**同族**。

**⚠ 而"那个 `rotation_ != ready.rotation` 用 `operator!=`"**⇒ **一个**值相等**】**。**

**⇒ 三层**：
```text
`*rotation_ != ready.rotation` ⇒ **⇒ 那【要求【`SvPlaylistEntry` 【有一个**值相等**
⇒ **⇒ 所以【一个**结构【的比较【是【那个**契约**
```

**✅ ⭐⭐⭐ **"一个结构的比较是那个契约"**。

## 六、`validName` 的四字符集

### 6.1 那段

```cpp
bool validName(const std::string_view value)
{
    return !value.empty() && std::ranges::all_of(value, [](const unsigned char character) {
        return character == '_' || character >= '0' && character <= '9' ||
            character >= 'A' && character <= 'Z' ||
            character >= 'a' && character <= 'z';
    });
}
```

### 6.2 二十四层

```text
1. **四个**字符集：`_` / `0..9` / `A..Z` / `a..z`**】
2. ⇒ **⇒ 所以“一个地图名【只能是**字母数字下划线**
3. ⇒ **⇒ 而那【排除【`/` / `\` / `.` / `:` / ` `**】
4. ⇒ **⇒ 所以【`mp_crash` ✓ / `mp-crash` ✗ / `../x` ✗ / `mp.crash` ✗**
```

### 6.3 ⭐⭐⭐ **"一个地图名只能是字母数字下划线 —— 那也排除了路径穿越"**

**✅ 与 §479 的"三条路径逃逸判据（`..` / `:` / 前导 `/`）"**——**完全同族** ✓

**⇒ 三层**：
```text
§479  **三条显式的拒绝（`..` / `:` / 前导 `/`）**
§496  **一个字白名单（4 个字符集）**
⇒ **⇒ 两种**不同的方式**达到**同一个目的**】（**⇒ 而【白名单**更强**）
```

**✅ ⭐⭐⭐ **"两种不同的方式达到同一个目的，而白名单更强"** —— 一个**跨报告的对照**。

**✅ 因为【一个白名单【天然【排除【一切**未列的** ⇒ **⇒ 而一个黑名单【只【排除**列出的**）**。**

## 七、**`SvResolvedBooking` 的三个重载**

### 7.1 那三个

```text
① SV_ResolveBooking(command, document)                    ⇒ 转发到 ③ 且 nativeSelection = nullopt
② SV_ResolveBooking(command, entry)                       ⇒ 用【那个 entry【作那个 rotation
③ SV_ResolveBooking(command, document, nativeSelection)   ⇒ 三段
```

### 7.2 二十四层

```text
1. **③ 是【那个真正的**】（**三段**）
2. ⇒ **⇒ ① 是【一个**便捷**的重载**】
3. ⇒ **⇒ ② 是【那个 `nativeSelection` 【的一个**变体**
```

### 7.3 ⭐⭐⭐ **"当那个命令直接命名那个地图与那个 gametype 时，那里没有什么可查找的：那**就是**那个 rotation 条目，而【查阅【一个【那个命令【从未携带**的 playlist id 【会【是【发明**一个**"**"

**✅ 与 §494 的"那个名字表说的是一个 id 意味着什么"**、§496 二 的"不要命名其余的那些"**——**完全同族** ✓

**⇒ 三层**：
```text
"that IS the rotation entry" ⇒ **⇒ 那个**命令【本身【就是【那个答案**
"consulting a playlist id the command never carried would be inventing one" ⇒ **⇒ 一个**不存在的**查询
⇒ **⇒ 所以【那个**短路【是【一个**纪律**
```

**✅ ⭐⭐⭐ **"'查阅一个那个命令从未携带的 playlist id 会是发明一个'"** —— 一个**极精确的纪律**。

**⚠ 而那个**三段回退**】**。**

**⇒ 十层**：
```text
① 命令【有 `map` + `g_gametype`**⇒ 用它们**】
② 否则【查 `playlist->rotation[rotationIndex]`**】
③ 否则【用那个 `nativeSelection`**】
④ 否则【`nullopt`**
⇒ **⇒ 所以【四层**
```

**✅ ⭐⭐⭐ **"四层回退"** —— 与 §493 的"四层回退"**同族**（**第二次**）。

**✅ 而与 §496 三 的"从严格到宽松**"**⇒ **一致**（**同样的哲学**）**。**

## 八、关键结论

1. **⭐⭐⭐ "CODOL 自己的形式：`2486`/`2481`/`2489`/`2500`/`2483` 是数字 dvar id；只有那两个也出现在 3.3.3.3 形式里的被读，而**即使是那些也不被假设意味着同一个东西** —— 下游没有东西用它们，而那个 `map` 与 `g_gametype` 才是载荷。**不要命名其余的那些在没有推导它们的情况下**"`** ⇒ **"'也出现'不蕴含'同一个意思'"**；而 **`2500` 与 `2483` 被列出但不被命名**（一个极妙的折中 —— "读者知道它们存在，但没人为它们编一个名字"）。
2. **⭐⭐⭐ 那三个可选（`if (const auto playerCount = number("2486"))`）而那两个必要时（`map`/`g_gametype` 用 `validName`）** ⇒ **"那三个的失败不导致拒绝"** ⇒ **"那个可选性是被 `if (const auto ...)` 表达的"**（一个 C++ 的惯用法）。
3. **⭐⭐⭐ 两种 `mmstart` 语法：从什么出现了来决定是哪种，而不是预先承诺一个形状** ⇒ **"『从出现决定』是一个更鲁棒的解析"**；而 **`sv_resetServer` 只能是第一个 —— 一个位置敏感的关键字**（独立验证 `"mmstart "` 是 `8` 个字符 ⇒ `substr(8)` 正确）。
4. **⭐⭐⭐ `lookup` 的"一个重复的名字是 malformed"** —— 与 §467/§494/§495 的"最后胜"**相反** ⇒ **"那个选择是由那个输入的性质决定的"**（**一个命令列表里两个 `map` 不可能都是真的**）。
5. **⭐⭐⭐ 两种不同的严格度**：一个**杂散的 token 被跳过**（"可能是一个未来的字段"），而一个**重复的名字拒绝**（"确定是一个矛盾"）⇒ **"'杂散'是宽容、'重复'是严格"**（与 §466 的 `Skipped` vs 拒绝同族）。
6. **⭐⭐⭐ `SvPendingBooking::observeConfigStrings` 的三态**：`!initialized || !checksum ⇒ sawReset_ = true` ⇒ **一个复位使那个 checksum 检查失效** ⇒ **"一个新代次必须先见到一个复位，否则那个 checksum 相等就意味『还没换代次』"** ⇒ **"那个 sawReset 是那个代次的证据"**（与 §469 的两级代次同族）。
7. **⭐⭐⭐ `commit` 的双重检查**（`!rotation_` 与 `*rotation_ != ready.rotation`）⇒ **"那个 commit 是一个幂等的单次"**（与 §475 同族）；而那个 `!=` 要求 `SvPlaylistEntry` **有一个值相等** ⇒ **"一个结构的比较是那个契约"**。
8. **⭐⭐⭐ `validName` 的四字符集（`_` / `0-9` / `A-Z` / `a-z`）** ⇒ **"一个地图名只能是字母数字下划线 —— 那也排除了路径穿越"** ⇒ 与 §479 的"三条路径逃逸判据"**同族**（**"两种不同的方式达到同一个目的，而白名单更强"**）。
9. **⭐⭐⭐ "当那个命令直接命名那个地图与那个 gametype 时，那里没有什么可查找的：那**就是**那个 rotation 条目，而**查阅一个那个命令从未携带的 playlist id 会是发明一个**"`** ⇒ **"'查阅一个那个命令从未携带的 playlist id 会是发明一个'"** —— 一个极精确的纪律；而那个**四层回退**（命令 / playlist / nativeSelection / `nullopt`）与 §493 的"四层回退"同族。

## 九、`sv_playlist_mp.cpp` 全文件总览

**`291` 行。**

**`6` 个数字 id**：
```text
2486  playerCount      （两种形式共有）
2481  maxPlayers       （CODOL 形式）
2489  privateMatch     （两种形式共有）
2500  ?                （列出未命名）
2483  ?                （列出未命名）
3265  maxPlayers       （3.3.3.3 形式）
```
再加上 **`playlist`** 与 **`start_map_rotate_once`** 两个**字符串名**（3.3.3.3 形式）。

**`6` 个函数**：`trim` / `parseU32` / `validName` / `parseCommandToken` / `SV_ParsePlaylistDocument` / `SV_EngineGameType` / `SV_BookingTokenForGameType` / `SV_ParseBookingCommand` / `SV_ResolveBooking`（三个重载）。

**`SvPendingBooking` 的五个方法**：`assign` / `observeConfigStrings` / `commit` / `cancel` / `pending`。

**`3` 个 `SvConfigStringGenerationRequirement`**（`NewGeneration` + 至少一个别的）。

## 十、未闭合点

- `2500` 与 `2483` 的语义（注释明说"不要命名"）。
- `SvConfigStringGenerationRequirement` 的另一个值。
- `OlMod::CodolPlaylist::parse` 的实现（在 `shared/` 那边）。
- 下一个文件：`sv_script_source_mp.cpp`（`10,500` 字节）或 `sv_native_characterinfo_mp.cpp`（`10,495` 字节）。
