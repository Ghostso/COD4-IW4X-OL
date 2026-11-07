# 学习报告 120（重开）— `ClanService.cpp`（24,704 B / 665 行）

**学习范围**：`backend\Demonware\ClanService.cpp` 全文（**665 行逐行读完**）
**性质**：全实测
**★★★★★ 本报告收录六个重大发现**：①**`parseUid` 的一个"清空整张表"的 bug** ②**9 个 typed 写入辅助函数** ③**8 个任务 + 18 个空 ack** ④**`persist()` 的合并写（绝不清空盘上数据）** ⑤**`teamInfos` 的 12 字段** ⑥**`members` 的 100 上限与 base64 名字**

---

## 一、★★★★★ **`parseUid` 的一个"清空整张表"的 bug**

### 1.1 ★★★★★ 完整注释（第 23–25 行，逐字）

```cpp
// ★ 2026-10-20：clans.json 里 owner/members 是 **16 位 HEX 字符串**，而旧代码用
//   `json.value<u64>()` 直接取 ⇒ **抛类型异常** ⇒ 外层 catch 把**整张表清空**
//   （实测后果：**66 家种子战队全丢，只剩运行期新建的 1 家**）。这里两种都接受。
```

### ★★★★★ 完整的 bug 链

```
`clans.json` 里 `owner` / `members` 是 **16 位 HEX 字符串**
        ↓
★★★ 旧代码用 `json.value<u64>()` 直接取
        ↓
★★★ **抛类型异常**
        ↓
★★★★★ 外层 `catch (...)` 把**整张表清空**
        ↓
★★★ 实测后果：**66 家种子战队全丢,只剩运行期新建的 1 家**
```

★★ **⇒ 这是一个**"单字段类型错误导致整表丢失"的经典案例**（与报告 114 的"一处偏移错误制造一批假发现"同类）。**

### ★★★★★ `parseUid` 的完整实现（第 26–50 行）

```cpp
std::uint64_t parseUid(const nlohmann::json &value)
{
    if (value.is_number_unsigned()) return value.get<std::uint64_t>();
    if (value.is_number_integer())  return static_cast<std::uint64_t>(value.get<std::int64_t>());
    if (!value.is_string())         return 0;                       // ★ 非字符串 ⇒ 0
    const auto text = value.get<std::string>();
    if (text.empty())               return 0;

    const bool hex = text.find_first_of("**ABCDEFabcdef**") != std::string::npos ||
        text.rfind("0x", 0) == 0 || text.rfind("0X", 0) == 0;        // ★★ 自动判进制
    try
    {
        std::size_t used = 0;
        const auto start = (hex && text.size() > 1 && (text[1] == 'x' || text[1] == 'X')) ? **2** : 0;
        const auto parsed = std::stoull(text.substr(start), &used, hex ? **16** : **10**);
        return static_cast<std::uint64_t>(parsed);
    }
    catch (...) { return 0; }
}
```

★★★ **⇒ 三个精确的兼容处理：**
```
① **数字** ⇒ 直接取（unsigned 或 integer）
② **字符串** ⇒ ★★ **自动判进制**（含 `A-F` 或 `0x` 前缀 ⇒ 16 进制,否则 10 进制）
③ 其他 ⇒ **0**（不抛异常）
```

★★ **⇒ 第 ② 条的判据：**`text.find_first_of("ABCDEFabcdef") != npos`** ⇒ 有十六进制字母 ⇒ 16 进制。**

### ★★★ 构造函数的三层 catch（第 285–353 行）

```cpp
try
{
    ...
    try { in >> doc; } catch (...) { return; }        // ★ 第一层：JSON 解析失败 ⇒ 返回（不抛）
    if (!doc.is_object() || !doc.contains("clans")) return;
    ...
}
catch (...)
{
    // 战队数据坏了也不能影响客户端启动：直接空表。
    clans_.clear();                                    // ★★ 第二层：任何异常 ⇒ 清空
}
```

★★★ **⇒ 两层 catch,但第二层会**清空 `clans_`**（就是那个 bug 的放大器）。**

---

## 二、★★★★★ **9 个 typed 写入辅助函数**

### 2.1 ★★★★★ 完整清单（第 53–142 行）

```cpp
void cat(Bytes &out, const Bytes &tail)                    // 追加
Bytes u8(const std::uint8_t value)      { return { **0x03**, value }; }
Bytes boolean(const bool value)         { return { **0x01**, value ? 1 : 0 }; }
Bytes u16(const std::uint16_t value)    { return { **0x06**, lo, hi }; }
Bytes u32(const std::uint32_t value)    { return { **0x08**, b0, b1, b2, b3 }; }
Bytes i32(const std::int32_t value)     { return { **0x07**, b0, b1, b2, b3 }; }
Bytes u64(const std::uint64_t value)    { return { **0x0a**, b0..b7 }; }
Bytes str(const std::string &text)      { return { **0x10**, chars..., **0** }; }
std::string base64(const std::string &input)
```

### ★★★★★ 8 个类型码的完整表

| 函数 | tag | 大小 |
|---|---|---|
| **`u8`** | **`0x03`** | 2 |
| **`boolean`** | **`0x01`** | 2 |
| **`u16`** | **`0x06`** | 3 |
| **`u32`** | **`0x08`** | 5 |
| **`i32`** | **`0x07`** | 5 |
| **`u64`** | **`0x0a`** | 9 |
| **`str`** | **`0x10`** | 1 + N + 1 |

★★★ **⇒ 全部与报告 105 的类型码表**一致** ✓**
**⇒ 且 `str` **自动加 NUL**。**

### ★★★ `Reader` 的对称读取（第 145–273 行）

```cpp
struct Reader
{
    bool tag(std::uint8_t &value);                    // 读一个 tag
    bool raw(std::size_t count);                      // 跳过 N 字节
    bool skip(std::uint8_t kind);                     // 按类型跳过
    bool number(std::uint64_t &value);                // ★ 读到下一个数值（跳过其他类型）
    bool text(std::string &value);                    // ★ 读到下一个字符串（跳过其他类型）
    bool memberId(std::uint64_t &value);              // ★ 读 member{u64, str},只取 uid
};
```

★★★ **⇒ `number` / `text` 都是**"扫描到目标类型"**（跳过其他）,而不是严格按位置读。**
**⇒ 这是一个**容错的读取策略**（与报告 118 的 `TypedReader::readNumber` **同一手法**）。**

### ★★★ `memberId` 的细节（第 256–272 行）

```cpp
// 读一个 member{u64 userId, str platform}：跳过字符串，只取 uid。
bool memberId(std::uint64_t &value)
{
    if (!number(value)) return false;
    std::uint8_t kind{};
    if (!tag(kind)) return true;                       // ★ 没有后续 ⇒ 成功
    if (kind == 0x10) { ...跳过字符串... }
    else { **--offset**; }                              // ★ 不是字符串 ⇒ 回退一字节
    return true;
}
```

★★★ **⇒ `--offset` 是关键：**若下一个不是字符串 ⇒ 回退,让后续读取重新看到这个 tag**。**

★ **⇒ 这是**"前瞻一个 tag 再决定"的模式**。**

---

## 三、★★★★★ **8 个任务 + 18 个空 ack**

### 3.1 ★★★★★ 完整任务表（第 386–414 行）

```cpp
registry.registerTask(0x03, **0x1E**, "Clan::create");
registry.registerTask(0x03, **0x2E**, "Clan::memberships");
registry.registerTask(0x03, **0x26**, "Clan::teamInfos");
registry.registerTask(0x03, **0x2F**, "Clan::members");
registry.registerTask(0x03, **0x80**, "Clan::search");
registry.registerTask(0x03, **0x22**, "Clan::leave");
// 其余先空 ack，避免 pending op 卡死
for (task : { **0x1F**, **0x20**, **0x21**, **0x23**, **0x24**, **0x25**, **0x30**, **0x32**,
              **0x33**, **0x34**, **0x35**, **0x39**, **0x3F**, **0x40**, **0x41**, **0x42**,
              **0x5B**, **0x5C** })
    registry.registerTask(0x03, task, "Clan::ack");
```

### ★★★★★ 完整的 24 个任务

| 类型 | 任务号 |
|---|---|
| **实装（6）** | **`0x1E`** create / **`0x2E`** memberships / **`0x26`** teamInfos / **`0x2F`** members / **`0x80`** search / **`0x22`** leave |
| **空 ack（18）** | `0x1F` `0x20` `0x21` `0x23` `0x24` `0x25` `0x30` `0x32` `0x33` `0x34` `0x35` `0x39` `0x3F` `0x40` `0x41` `0x42` `0x5B` `0x5C` |

★★★ **⇒ 理由（逐字）："其余先空 ack,避免 pending op 卡死"。**

★ **⇒ 服务 ID = **`0x03`**（Teams）⇒ 与报告 109 的 `0x03` = **Teams** ✓**

★★ **⇒ 且与报告 109 的 `AckOnlyServices` 的 `0x03/53`(=`0x35`)/`0x03/46`(=`0x2E`)/`0x03/48`(=`0x30`)** 有重叠**：**
```
报告 109：`0x03/53` `0x03/46` `0x03/48`（**十进制**）⇒ 即 `0x03/0x35` `0x03/0x2E` `0x03/0x30`
        ↓
★★★ 本报告：`0x2E` = **memberships**（实装）,`0x30`/`0x35` = **空 ack**
        ↓
★★★ ⇒ **`AckOnlyServices` 最后注册 ⇒ 它的名字胜出**（报告 109 已说明此设计）
```

---

## 四、★★★★★ **`persist()` 的合并写**

### 4.1 ★★★★★ 完整实现（第 437–493 行）

```cpp
// ★ 2026-10-20：战队落盘。schema 与既有 clans.json 一致（id/name/owner/members，uid 用 16 位大写 HEX）。
void ClanService::persist() const
{
    ...
    // ★ **合并写**：先读盘上已有条目，按 id 覆盖/追加，**绝不因为内存表为空就把盘上清空**。
    std::map<std::uint64_t, nlohmann::json> merged;
    {
        std::ifstream existingIn(root / "clans.json");
        if (existingIn)
        {
            // 读盘上已有 ⇒ 按 id 放进 merged
        }
    }
    for (const auto &[teamId, clan] : clans_)
    {
        nlohmann::json entry;
        entry["id"] = teamId;
        entry["name"] = clan.name;
        entry["owner"] = **uidToHex**(clan.ownerId);           // ★ 16 位大写 HEX
        entry["members"] = nlohmann::json::array();
        for (const auto &member : clan.members)
            entry["members"].push_back(**uidToHex**(member.userId));
        merged[teamId] = std::move(entry);                    // ★ 覆盖
    }
    for (auto &[id, entry] : merged)
    {
        if (!entry.contains("id")) entry["id"] = id;
        doc["clans"].push_back(std::move(entry));
    }
    ...
    out << doc.dump(**2**);
    AlwaysofflineRe::log("Clan: persisted " + std::to_string(clans_.size()) + " clans");
}
```

### ★★★★★ 合并写的三步

```
① **读盘上已有条目** ⇒ 按 id 放进 `merged`
        ↓
② **内存表覆盖/追加**（`merged[teamId] = entry`）
        ↓
③ **全部写出**
        ↓
★★★★★ ⇒ 关键（逐字）："**绝不因为内存表为空就把盘上清空**"
```

★★★ **⇒ 这是**对报告 120 第一节那个 bug 的**防御性修复**：**
```
那个 bug：`parseUid` 抛异常 ⇒ 整表清空 ⇒ 落盘时清空盘上数据
        ↓
★★★ 现在：**合并写** ⇒ 即使内存表空,盘上数据也保留
```

### ★★★ `uidToHex` 的 16 位大写（第 424–433 行）

```cpp
std::string uidToHex(const std::uint64_t value)
{
    static const char *digits = "0123456789ABCDEF";
    std::string out(**16**, '0');
    for (int i = 15; i >= 0; --i)
        out[static_cast<std::size_t>(i)] = digits[value >> ((15 - i) * 4) & 0xF];
    return out;
}
```

★★★ **⇒ 固定 **16 个十六进制字符**（= 64 位）,大写。**
**⇒ 与 `parseUid` 的"16 位 HEX 字符串"**对称** ✓**

### ★★★ 建队立刻落盘（第 529–530 行）

```cpp
// ★ 2026-10-20：**建队立刻落盘**，否则重启即丢（甲方建的 King 之前就是这样丢的）。
persist();
```

★★ **⇒ 明确的实测教训："甲方建的 King 之前就是这样丢的"。**

---

## 五、★★★★★ **`teamInfos` 的 12 字段**

### 5.1 ★★★★★ 完整实现（第 556–586 行）

```cpp
Bytes object;
cat(object, u64(clan->teamId));                    // ① teamId
cat(object, u32(clan->profileVersion));            // ② profileVersion
cat(object, str(clan->description));               // ③ description
cat(object, str(clan->announcement));              // ④ announcement
cat(object, u32(clan->autoJoinLevel));             // ⑤ autoJoinLevel
cat(object, i32(clan->recruitState));              // ⑥ recruitState（★ i32）
cat(object, u32(clan->activeTimestamp));           // ⑦ activeTimestamp
cat(object, u32(clan->createTimestamp));           // ⑧ createTimestamp
cat(object, u32(clan->ctp));                       // ⑨ ctp
cat(object, u32(clan->ctpEarnedToday));            // ⑩ ctpEarnedToday
cat(object, u32(clan->level == 0 ? 1 : clan->level));  // ⑪ ★ level（0 ⇒ 1）
cat(object, u32(clan->teamTags));                  // ⑫ teamTags
```

### ★★★★★ 完整的 12 个字段

| # | 类型 | 字段 |
|---|---|---|
| **①** | **u64** | `teamId` |
| **②** | **u32** | `profileVersion` |
| **③** | **str** | `description` |
| **④** | **str** | `announcement` |
| **⑤** | **u32** | `autoJoinLevel` |
| **⑥** | ★ **i32** | `recruitState` |
| **⑦** | **u32** | `activeTimestamp` |
| **⑧** | **u32** | `createTimestamp` |
| **⑨** | **u32** | `ctp` |
| **⑩** | **u32** | `ctpEarnedToday` |
| **⑪** | **u32** | ★★ **`level == 0 ? 1 : level`** |
| **⑫** | **u32** | `teamTags` |

★★★ **⇒ 第 ⑥ 条是**唯一的 `i32`**（其余是 `u32`）。**
**⇒ 第 ⑪ 条是**"0 ⇒ 1"的兜底**（避免 level 0）。**

### ★★★ 多队查询（第 564–569 行）

```cpp
std::uint64_t teamId{};
while (reader.number(teamId))              // ★ 循环读多个 teamId
{
    const auto *clan = findClan(teamId);
    if (clan == nullptr) **continue**;       // ★ 找不到就跳过（不发空对象）
    ...
}
```

★★ **⇒ `teamInfos` 支持**批量查询**（循环读 teamId）。**

---

## 六、★★★★★ **`members` 的 100 上限与 base64 名字**

### 6.1 ★★★★★ 完整实现（第 588–617 行）

```cpp
std::uint32_t index{};
for (const auto &member : clan->members)
{
    if (index++ >= **100**) break;                          // ★★ 100 上限
    Bytes object;
    cat(object, u64(clan->teamId));                         // ① teamId
    cat(object, u64(member.userId));                        // ② userId
    cat(object, str(""));                                   // ③ member.platform（空）
    cat(object, str(base64(member.userId == identity.userId
        ? identity.username
        : std::string("**Player**" + std::to_string(member.userId)))));   // ④ ★★ base64 名字
    cat(object, boolean(member.online));                    // ⑤ online
    cat(object, u8(member.role));                           // ⑥ role
    response.objects.push_back(std::move(object));
}
```

### ★★★★★ 完整的 6 个字段

| # | 类型 | 值 |
|---|---|---|
| **①** | **u64** | `teamId` |
| **②** | **u64** | `member.userId` |
| **③** | **str** | **`""`**（`member.platform` 空） |
| **④** | **str** | ★★ **`base64(名字)`** |
| **⑤** | **boolean** | `member.online` |
| **⑥** | **u8** | `member.role` |

★★★ **⇒ 第 ④ 条的两分支：**
```
**自己** ⇒ `base64(identity.username)`
**他人** ⇒ `base64("Player" + userId)`   ← ★★ **合成名**
```

★★ **⇒ `base64` 是**手写的**（第 107–142 行,标准字母表）,与报告 118 的 `toBase64` **相同实现**。**

★ **⇒ 而 `ClanService` 的构造函数里从 `ranked.json` 读真名（第 306–320 行）：**
```cpp
const auto readName = [&](const std::string &uid) -> std::string {
    std::ifstream memberIn(root / uid / "ranked.json");
    ...
    return memberDoc.value("name", std::string());
};
```
**⇒ 所以 `member.name` 有真名时不用（`members()` 里没读 `member.name`!）。**

★★★ **⇒ 这是一个**不一致**：构造函数读了 `member.name`,但 `members()` **不用它**,而是合成 `"Player"+uid`。**

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **`parseUid` 的 bug** | 旧代码 `json.value<u64>()` 对 **16 位 HEX 字符串**抛异常 ⇒ 外层 catch **清空整表** ⇒ **66 家种子战队全丢,只剩 1 家** |
| 2 | ★★★★ **`parseUid` 三兼容** | 数字直取 / **字符串自动判进制**（含 `A-F` 或 `0x` ⇒ 16）/ 其他 ⇒ **0** |
| 3 | ★★ 判据 | `text.find_first_of("ABCDEFabcdef") != npos` ⇒ 16 进制 |
| 4 | ★★★ 构造函数两层 catch | 第一层：JSON 解析失败 ⇒ **返回**；第二层：任何异常 ⇒ **`clans_.clear()`** |
| 5 | ★★★ **8 个 typed 写入** | `u8`(**0x03**) / `boolean`(**0x01**) / `u16`(**0x06**) / `u32`(**0x08**) / `i32`(**0x07**) / `u64`(**0x0a**) / `str`(**0x10**,自动加 NUL) / `cat` |
| 6 | ★★ `Reader` 6 方法 | `tag` / `raw` / `skip` / **`number`** / **`text`** / **`memberId`** |
| 7 | ★★★ `number`/`text` 策略 | **"扫描到目标类型"**（跳过其他）⇒ 容错读取 |
| 8 | ★★★ `memberId` 的 `--offset` | 下一个不是字符串 ⇒ **回退一字节**（前瞻模式） |
| 9 | ★★★★★ **24 个任务** | **实装 6**：`0x1E`/`0x2E`/`0x26`/`0x2F`/`0x80`/`0x22`；**空 ack 18** |
| 10 | ★★ 空 ack 的理由 | "**避免 pending op 卡死**" |
| 11 | ★★★ 与报告 109 的重叠 | `0x2E`/`0x30`/`0x35` 也在 `AckOnlyServices` 里 ⇒ **后者最后注册,名字胜出** |
| 12 | ★★★★★ **`persist()` 合并写** | 读盘上已有 ⇒ 内存表覆盖/追加 ⇒ 写出 ⇒ "**绝不因为内存表为空就把盘上清空**" |
| 13 | ★★★ 合并写的意义 | 是对第 1 条 bug 的**防御性修复** |
| 14 | ★★★ `uidToHex` | **固定 16 个十六进制字符**（大写）⇒ 与 `parseUid` 对称 |
| 15 | ★★ 建队立刻落盘 | "**甲方建的 King 之前就是这样丢的**" |
| 16 | ★★★★★ **`teamInfos` 12 字段** | `u64 teamId` / `u32 profileVersion` / `str description` / `str announcement` / `u32 autoJoinLevel` / ★ **`i32 recruitState`** / `u32 activeTimestamp` / `u32 createTimestamp` / `u32 ctp` / `u32 ctpEarnedToday` / **`u32 (level==0?1:level)`** / `u32 teamTags` |
| 17 | ★★ 唯一的 `i32` | `recruitState` |
| 18 | ★★ 批量查询 | `teamInfos` 循环读多个 `teamId`；找不到 ⇒ **`continue`**（不发空对象） |
| 19 | ★★★★★ **`members` 6 字段** | `u64 teamId` / `u64 userId` / `str ""` / ★★ **`str base64(名字)`** / `boolean online` / `u8 role` |
| 20 | ★★★ 名字两分支 | **自己 ⇒ `base64(username)`**；**他人 ⇒ `base64("Player"+uid)`** |
| 21 | ★★★★ **一处不一致** | 构造函数从 `ranked.json` 读了 `member.name`,但 `members()` **不用它**（合成 `"Player"+uid`） |
| 22 | ★★ `members` 上限 | **100** |
| 23 | ★★ `search` 12 字段 | 含 `u32(成员数)` / `u32(100)` / `u32(level==0?1:level)` / `u32 ctp` / `u8 recruitState` / `u32 createTimestamp` |
| 24 | ★★ `create` 的 5 字段 | `u64 teamId` / `str name` / `u64 ownerId` / `str ""` / **`u8 2`**（我是 owner） |
| 25 | ★★ 错误码 | **`301`** = 已在队伍里 |
| 26 | ★★★ `leave` 的级联 | 成员空 ⇒ **`clans_.erase(teamId)`**（解散） |
| 27 | ★★ `role` 的赋值 | `uid == ownerId ? **2** : (index == 0 ? **2** : **0**)` |

---

## 八、结论

### 1. ★★★★★ **`parseUid` 的一个类型错误导致 66 家战队全丢**

```
`json.value<u64>()` 对 16 位 HEX 字符串抛异常
        ↓
★★★ 外层 `catch` 清空整张表
        ↓
★★★★★ 实测：**66 家种子战队全丢,只剩运行期新建的 1 家**
```

### 2. ★★★★★ **`persist()` 的合并写是对该 bug 的防御性修复**

★ **⇒ "绝不因为内存表为空就把盘上清空"。**

### 3. ★★★★ **8 个 typed 写入 + 6 个容错读取**

★ **⇒ `number`/`text` 都是"扫描到目标类型",`memberId` 用 `--offset` 前瞻。**

### 4. ★★★★ **24 个任务（6 实装 + 18 空 ack）** 以避免 pending op 卡死

### 5. ★★★ **`teamInfos` 的 12 字段**（唯一 `i32` 是 `recruitState`）

### 6. ★★★★ **`members()` 不用已读到的真名,而合成 `"Player"+uid`**（一处不一致）

---

## 九、下一步

- `ClanService.hpp`（72 行）/ `Storage2Service`（450 行）/ `Friends2Service`（325 行）
- `SharedRoom*`（4 文件）/ `Servers.cpp`（624 行）/ `DedicatedBookingDispatcher`（926 行）
