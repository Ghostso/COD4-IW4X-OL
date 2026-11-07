# 学习报告 121（重开）— `Storage2Service`（179 + 553 行）+ `Friends2Service`（39 + 342 行）

**学习范围**：`Storage2Service.hpp`（1,791 B / 45 行）+ `.cpp`（19,411 B / 553）+ `Friends2Service.hpp`（1,627 B / 39）+ `.cpp`（17,532 B / 342）
**性质**：全实测（**四文件逐行读完**）
**★★★★★ 本报告收录八个重大发现**：①**`configs_s.info` 必须加密（否则静默崩溃）** ②**`makeOfflinePlaylist` 的 `rule 1011` 改写** ③**`serializeContextualFileInfo` 的 7 字段** ④**`CodolPresence` 136 字节常量** ⑤**好友列表的 **v18–v28 十轮失败史** ⑥**`0x60` 行定长补齐** ⑦**`68/4` 的 presence 镜像** ⑧**文件名安全校验**

---

## 一、★★★★★ **`configs_s.info` 必须加密（否则静默崩溃）**

### 1.1 ★★★★★ 完整注释（第 374–389 行，逐字）

```cpp
// **configs_s.info IS ENCRYPTED ON THIS BUILD; every other publisher file is plaintext.**
//
// Serving it as plaintext **does not fail visibly and that is the trap**: the client
// **DECRYPTS** this one on receipt, so plaintext decrypts to garbage, the parse yields
// nothing, and the config store ends up empty **WHILE STILL FLAGGED LOADED**. The client
// then runs on happily and **dies much later in `atof(NULL)` on a missing config key**,
// with nothing connecting the crash to this reply. Symptom seen here on 2026-08-28:
// the lobby handshake and twenty service calls all succeed, and out.exe then
// **disappears with a 254 MB dump and not one error line anywhere**.
//
// Established in the C# reference (`LobbyServer/Services/Storage.cs`) from a **dump scan**,
// not assumed: the content of every publisher file served is resident in client memory
// afterwards **EXCEPT `configs_s`**, which is **alone in being absent**.
//
// The cipher is **content-independent, deterministic and position-keyed**, so encrypting
// is a plain XOR against a captured keystream of at least the plaintext's length.
```

### ★★★★★ 完整的失败链

```
`configs_s.info` 以**明文**提供
        ↓
★★★ 客户端**解密**它（其他文件不解密）
   ⇒ 明文解出来是**垃圾**
   ⇒ 解析**什么都没得到**
        ↓
★★★ 配置存储**变空但标记仍是"已加载"**
        ↓
★★★★★ 客户端继续跑,**很久之后在 `atof(NULL)` 崩溃**
   ⇒ **没有任何东西把这个崩溃和这条应答联系起来**
        ↓
★★★ 实测（2026-08-28）：握手 + **20 个服务调用全部成功**,然后 out.exe
   **带着 254 MB 的 dump 消失,一行错误都没有**
```

### ★★★★★ 三条精确事实

| # | 项 | 值 |
|---|---|---|
| **1** | ★★★ 崩溃点 | **`atof(NULL)`**（缺失的配置键） |
| **2** | ★★ 崩溃规模 | **254 MB dump**，**零错误行** |
| **3** | ★★★ 证据来源 | **dump 扫描**：所有发布方文件的内容都驻留在客户端内存里，**唯独 `configs_s` 缺席** |

★★ **⇒ 第 3 条是**关键证据**：用"内存里有没有"反推出"这个文件被特殊处理"。**

### ★★★★★ 加密的实现（第 390–419 行）

```cpp
void Storage2Service::encodePublisherFile(
    const std::string &name, std::vector<std::uint8_t> &payload) const
{
    if (_stricmp(name.c_str(), "**configs_s.info**") != 0)
        return;                                          // ★ 只加密这一个

    const auto keystream = readFile(
        assetRoot_ / std::to_string(session_.snapshot().titleId) /
            "**Keystreams**" / "**configs_s.keystream**");
    if (keystream.size() < payload.size())
    {
        // Loudly, because the alternative is a silent crash minutes later that looks
        // like anything but a storage problem.
        AlwaysofflineRe::log(
            "STORAGE2 WARNING: '" + name + "' needs a keystream of at least " +
            std::to_string(payload.size()) + " bytes but got " +
            std::to_string(keystream.size()) +
            ". **Serving PLAINTEXT - the client will discard it and crash later.**");
        return;
    }

    for (std::size_t index = 0; index < payload.size(); ++index)
        payload[index] ^= keystream[index];               // ★ 纯 XOR

    AlwaysofflineRe::log("STORAGE2 encrypted '" + name + "' (" + ... + " bytes)");
}
```

### ★★★★★ 与报告 086 的**完全吻合**

```
报告 086（插件字符串面）：
  `configs_s.info` / `configs_s.keystream` / `Keystreams`
  `'needs a keystream of at least N bytes but got M'`
  `'. Serving PLAINTEXT - the client will discard it and crash later.'`
        ↓
★★★★★ 本报告：**逐字相同的三条字符串** ✓
        ↓
★★★ ⇒ **报告 086 的发现得到源码级确认**
```

### ★★★★★ 密文的三个性质（逐字）

```
"The cipher is **content-independent, deterministic and position-keyed**,
 so encrypting is a plain **XOR against a captured keystream of at least the
 plaintext's length**."
        ↓
★★★ ⇒ 三条：
① **content-independent**（与内容无关）
② **deterministic**（确定性）
③ ★★★ **position-keyed**（按位置索引）
        ↓
★★★★★ ⇒ 所以就是**纯 XOR**
```

---

## 二、★★★★★ **`makeOfflinePlaylist` 的 `rule 1011` 改写**

### 2.1 ★★★★★ 完整实现（第 126–193 行）

```cpp
std::vector<std::uint8_t> makeOfflinePlaylist(const std::span<const std::uint8_t> data)
{
    constexpr std::string_view RuleName = "**rule**";
    constexpr std::string_view MinimumPlayersKey = "**1011**";
    ...
    while (offset < text.size())
    {
        // 逐行解析
        if (line.substr(cursor).starts_with(RuleName))
        {
            cursor += RuleName.size();
            if (isHorizontalSpace(line[cursor]))
            {
                while (isHorizontalSpace(line[cursor])) ++cursor;
                if (line.substr(cursor).starts_with(MinimumPlayersKey))
                {
                    cursor += MinimumPlayersKey.size();
                    ...
                    std::uint32_t minimumPlayers{};
                    std::from_chars(..., minimumPlayers);
                    if (parsed 成功 && **minimumPlayers > 1**)
                    {
                        output.append(text.substr(offset, valueBegin));
                        output.push_back(**'1'**);          // ★★★ 强制改成 1
                        output.append(text.substr(offset + cursor, next - offset - cursor));
                        offset = next;
                        continue;
                    }
                }
            }
        }
        output.append(text.substr(offset, next - offset));
        offset = next;
    }
}
```

### ★★★★★ 完整的改写规则

```
找到 `rule 1011 <N>` 且 **`N > 1`**
        ↓
★★★ 把 `N` **原地替换成字符 `'1'`**
   ⇒ 即 `rule 1011 N` ⇒ `rule 1011 1`
        ↓
★★★★★ 只改**这一个字段**,其余字节**逐字保留**
```

### ★★★★★ 与报告 079/110 的**精确吻合**

```
报告 079（`mp_playlists`）：playlist 里有 `rule 1011 1` / `rule 1011 6` / `rule 1011 16` / `rule 1011 17`
报告 110（`MatchmakingService`）：会话记录里 **`rule 1011`** 相关
        ↓
★★★★★ 本报告：`rule 1011` = **最小玩家数**
   ⇒ 线上把它**全改成 1**（离线单人也能开）
```

★★ **⇒ 而报告 079 的 playlist 1 里有 `rule 1011 1` / playlist 4 有 `rule 1011 6`**
**⇒ 说明 `1011` 的值随 playlist 不同,而这里**统一改成 1**。**

### ★★★ 触发条件（第 513–517 行）

```cpp
if (session_.snapshot().titleId == **1004** &&
    name == "**mp_playlists_shipRetail_release.info**")
{
    data = makeOfflinePlaylist(data);
}
```

★★★ **⇒ 只对 `titleId == 1004` 且 `mp_playlists_shipRetail_release.info` 生效。**

### ★★★★★ 文件名的**别名**（第 503–504 行）

```cpp
if (name == "**mp_playlists_shipRetail.info**")
    name = "**mp_playlists_shipRetail_release.info**";
```

★★★★★ **⇒ 客户端请求的是 `mp_playlists_shipRetail.info`（**无 `_release`**）,**
**⇒ 而盘上的文件是 `mp_playlists_shipRetail_release.info`（**有 `_release`**）。**
**⇒ 这里做**名字映射**。**

★★ **⇒ 这与报告 079 的文件名 `mp_playlists_shipRetail_release.info`**完全对应** ✓**

---

## 三、★★★★★ **`serializeContextualFileInfo` 的 7 字段**

### 3.1 ★★★★★ 完整实现（第 195–212 行）

```cpp
std::vector<std::uint8_t> serializeContextualFileInfo(
    const std::string &name, const std::uint32_t modifiedTime,
    const std::span<const std::uint8_t> data)
{
    ByteBuffer output;
    output.writeU32(static_cast<std::uint32_t>(data.size()));   // ① 大小
    output.writeU64(**fileId**(name));                            // ② FNV-1a 哈希
    output.writeU32(modifiedTime);                                // ③ 修改时间
    output.writeU32(modifiedTime);                                // ④ ★ 重复
    output.writeBool(**false**);                                  // ⑤ 恒 false
    output.writeU64(**0**);                                       // ⑥ 恒 0
    output.writeString(name);                                     // ⑦ 名字
    const auto checksum = md5(data);
    output.writeString(std::string_view(checksum.data(), checksum.size()));   // ⑧ MD5
}
```

### ★★★★★ 完整的 8 个字段

| # | 类型 | 值 |
|---|---|---|
| **①** | **u32** | `data.size()` |
| **②** | **u64** | ★★ **`fileId(name)`**（FNV-1a 32 位扩展成 u64） |
| **③** | **u32** | `modifiedTime` |
| **④** | **u32** | ★★ **`modifiedTime`（重复）** |
| **⑤** | **bool** | **`false`** |
| **⑥** | **u64** | **`0`** |
| **⑦** | **string** | `name` |
| **⑧** | **string** | ★★★ **`md5(data)`**（16 字节当字符串） |

★★★ **⇒ 三个精确细节：**
```
① ★★ `modifiedTime` **写两次**（③ 与 ④）
② ★★★ **`md5(data)` 被当成 string 写入**（16 字节 + NUL）
③ ★ FNV-1a 的 `fileId`
```

### ★★★ `fileId` 的实现（第 88–97 行）

```cpp
std::uint64_t fileId(const std::string_view name)
{
    std::uint32_t result = **0x811C9DC5**;
    for (const unsigned char character : name)
    {
        result ^= character;
        result *= **0x01000193**;
    }
    return result;
}
```

★★★ **⇒ **FNV-1a 32 位**（`0x811C9DC5` + `0x01000193`）⇒ **第四次出现**（前三次：099/112/118）。**

★ **⇒ 返回 `u64` 但实际只有 32 位 ⇒ 高 32 位恒 0。**

---

## 四、★★★★★ **`CodolPresence` 的 136 字节常量**

### 4.1 ★★★★★ 完整定义（`Friends2Service.cpp:27-40`）

```cpp
constexpr auto CodolPresence = []
{
    std::array<std::uint8_t, **136**> value{};
    value[**28**] = 0x6D;  value[**29**] = 0x75;   // 'm' 'u'
    value[**32**] = 0x6B;  value[**33**] = 0x75;   // 'k' 'u'
    value[**36**] = 0x6C;  value[**37**] = 0x75;   // 'l' 'u'
    value[**44**] = 0x10;
    value[**120**] = 0x04;
    value[**121**] = 0x04;
    return value;
}();
```

### ★★★★★ 完整的字节布局

```
136 字节,全零,只填 10 个位置：
偏移 28–29 ⇒ `6D 75` = **`"mu"`**
偏移 32–33 ⇒ `6B 75` = **`"ku"`**
偏移 36–37 ⇒ `6C 75` = **`"lu"`**
偏移 44    ⇒ **`0x10`**（= String 类型码）
偏移 120   ⇒ **`0x04`**
偏移 121   ⇒ **`0x04`**
```

★★★ **⇒ 六个 ASCII 字节拼成 `"mukulu"`（分三段）⇒ 可能是一个**假的地图/模式名**。**

### ★★★★★ 十轮失败的完整诊断史（第 814–827 行，逐字）

```cpp
// ★★ 2026-10-07 20:5x -- 【单变量实验 v25：presence blob 逐条目唯一化】★
//   v19–v24 六连失败给出的关键对照：
//   * 客户端**自己的** blob（68/3 上传实测）里装的是**它自己的数据**：
//     `8×00 + 名字UTF-8 + NUL`（每次上传都带）；
//   * 老外 9/16 的 `Blob[120]` 里也是**每会话不同的值**（c513/c313/uid 槽…）；
//   * 而我们的 `CodolPresence`（136B）**对每个好友逐字节相同** —— **常量**。
//   ⇒ 若客户端按 blob 内容对好友做**去重/键控**（同 blob = 同一好友），
//     100 个好友会塌缩成 1 个：第 1 条幸存（uid/name 正常）、其余槽位全空
//     —— 与全部观测吻合；也解释了为什么 v22–v24 改列尾毫无效果（blob 没动）。
```

★★★★★ **⇒ 一个**极其精确的假设**：**
```
客户端自己的 blob ⇒ `8×00 + 名字UTF-8 + NUL`（**每条不同**）
老外的 `Blob[120]` ⇒ **每会话不同**
我们的 `CodolPresence` ⇒ ★★★ **对每个好友逐字节相同（常量）**
        ↓
★★★ 若客户端按 blob 内容**去重/键控**（同 blob = 同一好友）
   ⇒ **100 个好友塌缩成 1 个**
        ↓
★★★★★ ⇒ **完美解释"第 1 条幸存、其余槽位全空"**
```

### ★★★★★ v18–v28 的完整实验表

| 版本 | 单变量 | 结果 |
|---|---|---|
| **v18** | ★ **交换前两条**（第 1 条 = `Zephy_`） | 诊断用 |
| **v21** | 好友列表缩到 **2 条** | 诊断用 |
| **v22–v24** | 改**列尾** | ★★ **毫无效果**（blob 没动） |
| **v25** | ★★ **blob 头 8 字节写 uid**（逐条唯一化） | — |
| **v26** | 等长占位名 | ★★ **已证与长度无关** |
| **v27** | ★★★ **删 `03 00`（u8 字段）** | — |
| **v28** | ★★★ **删整个 blob** | — |
| **2026-10-16** | ★★★ **补齐到 `0x60`（96 B）** | ★ **解决** |

★★★ **⇒ v27 的关键洞察（第 803–809 行，逐字）：**
```
"★ 五连失败（v21–v26）的 diff 结论：**`03 00` 这个字节在每一个版本里都存在**
 —— v21/22 改的是它后面的 bool 标签、v23 删的是 bool、v24 在其后追加终止符、
 v25 改它后面的 blob 内容、v26 改它前面的名字长度：**没有任何一版动过 `03 00` 本身**。
 若客户端条目语法在"名字"之后**直接接 blob**（`13 …`），那么每一版都在同一字节处撞墙
 （readType 失配 → 该条中止、其余条目留空）——与全部观测吻合，
 且**完美解释"改哪儿都无感"**。"
```

★★ **⇒ 这是**"diff 找出从未被改动的字节"的方法论**。**

### ★★★★★ 最终的解法（第 828–841 行，逐字）

```cpp
// ★★ 2026-10-16 26:00 -- 清单 #14：**每条补齐到 `0x60`（96 B）**。
//   依据（findings\定因-好友与stats同一类缺行-…-20261012-45000.md）：
//   stats 侧（StatsService.cpp:286-292）已用"行定长 **0x98** 补齐"解决过同一现象
//   （**客户端按行对象尺寸步进读取游标，非定长 ⇒ 第 2 条起全部错位**）；
//   好友侧实测每条仅 **19 B**（Zephy_），而客户端好友行数组**行距 = `0x60`（96 B）**。
...
{
    static constexpr std::uint8_t ZeroPad[0x60] = {};
    const auto written = object.data().size();
    if (written < 0x60)
        object.writeRaw(std::span<const std::uint8_t>(ZeroPad, 0x60 - written));
}
```

★★★★★ **⇒ 完整的根因 + 解法：**
```
★★★ **客户端按行对象尺寸步进读取游标**
        ↓
非定长 ⇒ **第 2 条起全部错位**
        ↓
★★★ 好友侧每条仅 **19 B**,而行距是 **`0x60`（96 B）**
        ↓
★★★★★ 解法：**每条补齐到 96 字节**
   （与 `StatsService` 的 **`0x98`** 补齐**同一手法**）
```

★★ **⇒ 第 6 条与报告 118 的 `MaxRows = 100` 的 `0x98` 步进**完全对应** ✓**

### ★★★★★ 好友行数组的精确地址（第 794–796 行，逐字）

```
"客户端好友行数组（**`0xE379208`, 96B/行**）= [count=2], 行0 = uid+名字（完整），行1 = 空槽（uid=0）。"
        ↓
★★★ ⇒ 三个精确值：
  数组地址 **`0xE379208`**
  行距 **96 B**（= `0x60`）
  结构 **[count=2] + 行0 + 行1**
```

★ **⇒ 且另一处提到 **`0xE379268`**（第 800 / 834 行）⇒ 可能是 `行1` 的地址（`0xE379208 + 0x60 = 0xE379268`）✓ 算术正确。**

---

## 五、★★★★★ **`68/4` 的 presence 镜像**

### 5.1 ★★★★★ 完整实现（第 876–944 行）

```cpp
ServiceResponse Friends2Service::getPresence(const ServiceRequest &request) const
{
    // 请求形状实测（18:33:10 / 18:39:56 / 18:48:07）：
    //   `10 "" 08 <u32 2> 0A <u64 uid> 10 "" 0A <u64 0> 10 "" 00`
    // = 一个"最多 2 条"的用户槽位表（0 = 空槽）。收集所有非零 0A u64。
    ...
    for (const auto id : ids)
    {
        const auto entry = 在 roster 里找;
        if (entry == roster.end()) { log "not in roster; skipped"; continue; }
        ByteBuffer record;
        record.writeString("");       // 与客户端 68/3 同形
        record.writeU64(id);
        record.writeString("");
        record.writeU8(**1**);
        ByteBuffer blob;
        static constexpr std::uint8_t Zeros[**8**] = {};
        blob.writeRaw(Zeros);                                    // ★ 8 个零
        blob.writeRaw(entry->name);                              // ★ 名字
        static constexpr std::uint8_t Nul[**1**] = {};
        blob.writeRaw(Nul);                                      // ★ NUL
        record.writeBlob(blob.data());
        response.objects.push_back(record.data());
    }
}
```

### ★★★★★ 请求的精确形状（逐字）

```
`10 "" 08 <u32 2> 0A <u64 uid> 10 "" 0A <u64 0> 10 "" 00`
```

| 段 | 内容 |
|---|---|
| **`10 ""`** | 空字符串（context） |
| **`08 <u32 2>`** | ★ **最多 2 条** |
| **`0A <u64 uid>`** | ★ 第 1 个用户 |
| **`10 ""`** | 空字符串 |
| **`0A <u64 0>`** | ★ **空槽** |
| **`10 ""`** | 空字符串 |
| **`00`** | 结尾 |

### ★★★★★ 响应的 5 个字段

| # | 类型 | 值 |
|---|---|---|
| **①** | **string** | **`""`**（与客户端 `68/3` 同形） |
| **②** | **u64** | `id` |
| **③** | **string** | **`""`** |
| **④** | **u8** | ★ **`1`** |
| **⑤** | **blob** | ★★ **`8 个零` + `名字` + `NUL`** |

★★★ **⇒ 第 ⑤ 条的 blob 形状与**客户端自己 `68/3` 上传的完全一致**（第 819–820 行逐字）：**
```
"客户端**自己的** blob（68/3 上传实测）里装的是**它自己的数据**：
 `**8×00 + 名字UTF-8 + NUL**`（每次上传都带）"
```

### ★★★ 三个任务的完整表

| 服务/任务 | 名称 | 行为 |
|---|---|---|
| **`0x09/0x1A`** | `Friends2::getFriends` | ★ 回**只有自己**（`userId` + `base64(name)` + `u8 0` + `bool true` + **`CodolPresence`**） |
| **`0x09/5`** | `Friends2::getFriendList` | ★★ **按名册返回好友**（每条补齐 `0x60`） |
| **`0x44/4`** | `RichPresence::getPresence` | ★★★ **镜像 `68/3` 形状** |

★★★ **⇒ `0x44` = RichPresence（与报告 109 的 `0x44` = **RichPresence** ✓）**

---

## 六、★★★★★ **`Storage2Service` 的 4 个任务**

### 6.1 ★★★★★ 任务表（第 239–257 行）

```cpp
registry.registerTask(**0x0A**, **10**, "bdStorage::uploadFile");
registry.registerTask(**0x0A**, **12**, "bdStorage::getFile");
registry.registerTask(**0x0A**, **20**, "Storage2::listAllPublisherFiles");
registry.registerTask(**0x0A**, **21**, "Storage2::getPublisherFile");
```

★★★ **⇒ 4 个任务,服务 ID **`0x0A`**（= Storage2,与报告 109 的 `0x0A` = **Storage2** ✓）**

### ★★★★★ 两个文件名的安全校验（第 430 / 448 / 505 行）

```cpp
if (name.empty() || std::filesystem::path(name).filename().string() != name)
    return std::nullopt;      // 或 reportStorageError("rejected unsafe uploadFile filename")
```

★★★★★ **⇒ 一个精确的**路径穿越防护**：**
```
`std::filesystem::path(name).filename().string() != name`
        ↓
★★★ 即：**去掉目录后的文件名必须等于原名**
   ⇒ 若含 `\` 或 `/` 或 `..` ⇒ **不相等** ⇒ **拒绝**
```

★ **⇒ 报错串 **`"rejected unsafe uploadFile filename"`** ⇒ 与报告 086 的**完全一致** ✓**

### ★★★ 上传的完整校验（第 295–313 行）

```cpp
if (!input.readString(context) || !input.readString(name) ||
    !input.readBool(visibility) || !input.readBlob(data) ||
    !input.readU64(owner) || !input.readString(platform) ||
    !input.readU32(flags) || !input.valid() ||
    !(input.empty() || (input.remainingSize() == 1 && input.remaining().front() == 0)) ||
    data.size() > **MaximumUserFileSize**)                       // ★ 16 MB
{
    reportStorageError("rejected malformed uploadFile request");
    return error;
}
```

★★ **⇒ 7 个字段 + 尾部 0 + **16 MB 上限**（`MaximumUserFileSize = 16 * 1024 * 1024`）。**

### ★★★ owner 的鉴权（第 306–313 行）

```cpp
if (owner == 0) owner = identity.userId;                          // ★ 0 ⇒ 自己
if (identity.userId == 0 || **owner != identity.userId**)
{
    reportStorageError("rejected uploadFile request for a **non-authenticated owner**");
    return error;
}
```

★★★ **⇒ 只能写**自己**的文件（`owner` 必须等于 `identity.userId`）。**
**⇒ 报错串与报告 086 的 `"rejected uploadFile request for a non-authenticated owner"`**完全一致** ✓**

### ★★★ 临时文件名的三要素（第 470–472 行）

```cpp
auto temporary = path;
temporary += L"**.writing.**" + std::to_wstring(**GetCurrentProcessId**()) + L"." +
    std::to_wstring(**TemporaryFileSequence.fetch_add(1)**);
```

★★★ **⇒ 临时名 = `.writing.<PID>.<序号>`**（**第五次出现原子写约定,但这次带 PID + 序号**）。**

★ **⇒ 与报告 086 的 `.|w|r|i|t|i|n|g|.`（UTF-16LE 的 `.writing.`）**完全对应** ✓**

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **`configs_s.info` 必须加密** | 明文 ⇒ **解密成垃圾** ⇒ 配置存储**空但标记已加载** ⇒ 很久后 **`atof(NULL)`** 崩溃 |
| 2 | ★★ 崩溃规模 | **254 MB dump**,**零错误行**（2026-08-28） |
| 3 | ★★★ 证据来源 | **dump 扫描**：所有发布方文件内容都驻留内存,**唯独 `configs_s` 缺席** |
| 4 | ★★★ 密文三性质 | **content-independent / deterministic / position-keyed** ⇒ **纯 XOR** |
| 5 | ★★★★★ 与报告 086 吻合 | `configs_s.info` / `configs_s.keystream` / `Keystreams` / 两条警告串 **逐字相同** ✓ |
| 6 | ★★★★★ **`makeOfflinePlaylist`** | `rule 1011 <N>` 且 **`N > 1`** ⇒ **原地改成 `'1'`**,其余字节逐字保留 |
| 7 | ★★ 触发条件 | **`titleId == 1004`** 且 **`mp_playlists_shipRetail_release.info`** |
| 8 | ★★★★★ **文件名别名** | 客户端请求 **`mp_playlists_shipRetail.info`**（无 `_release`）⇒ 映射到 **`_release.info`** ✓ |
| 9 | ★★★★★ **`serializeContextualFileInfo` 8 字段** | `u32 size` / **`u64 fileId(name)`** / **`u32 modifiedTime`（写两次）** / `bool false` / `u64 0` / `string name` / **`string md5(data)`** |
| 10 | ★★★ **FNV-1a 第四次出现** | `0x811C9DC5` + `0x01000193`（前三次：099/112/118） |
| 11 | ★★★★★ **`CodolPresence` 136 字节** | 只填 10 个位置：偏移 **28–29** `"mu"` / **32–33** `"ku"` / **36–37** `"lu"` / **44** `0x10` / **120–121** `0x04 0x04` |
| 12 | ★★★★ **十轮失败的核心假设** | 我们的 blob **对每个好友逐字节相同（常量）** ⇒ 若客户端**按 blob 去重** ⇒ **100 个塌缩成 1 个** |
| 13 | ★★★ 对照 | 客户端自己的 blob = `8×00 + 名字 + NUL`（**每条不同**）；老外 `Blob[120]` **每会话不同** |
| 14 | ★★★ **v18–v28 实验表** | v18 交换 / v21 缩到 2 条 / **v22–v24 改列尾（无效果）** / v25 blob 唯一化 / v26 等长名 / **v27 删 `03 00`** / v28 删 blob |
| 15 | ★★★★ **v27 的 diff 洞察** | "**`03 00` 这个字节在每一个版本里都存在**...**没有任何一版动过 `03 00` 本身**" |
| 16 | ★★★★★ **最终根因** | **客户端按行对象尺寸步进读取游标**,非定长 ⇒ **第 2 条起全部错位** |
| 17 | ★★★ 精确数字 | 好友每条仅 **19 B**,而行距 **`0x60`（96 B）** ⇒ **补齐到 96** |
| 18 | ★★★ 与 `StatsService` 同一手法 | stats 用 **`0x98`** 补齐 ✓ 报告 118 |
| 19 | ★★★ **好友行数组地址** | **`0xE379208`**,**96 B/行**,结构 **[count=2] + 行0 + 行1**；行 1 地址 **`0xE379268`**（`+0x60` ✓） |
| 20 | ★★★★★ **`68/4` 的请求形状** | `10 "" 08 <u32 2> 0A <u64 uid> 10 "" 0A <u64 0> 10 "" 00` |
| 21 | ★★★ `68/4` 的响应 5 字段 | `str ""` / `u64 id` / `str ""` / **`u8 1`** / **`blob(8×00 + 名字 + NUL)`** |
| 22 | ★★★ blob 与客户端 `68/3` 同形 | **`8×00 + 名字UTF-8 + NUL`** ✓ |
| 23 | ★★ 三个任务 | `0x09/0x1A`(getFriends) / `0x09/5`(getFriendList) / **`0x44/4`**(getPresence) |
| 24 | ★★★ **`0x0A` 的 4 个任务** | `10`(uploadFile) / `12`(getFile) / `20`(listAllPublisherFiles) / `21`(getPublisherFile) |
| 25 | ★★★★★ **路径穿越防护** | `path(name).filename().string() != name` ⇒ 拒绝 ⇒ 报错串 **`"rejected unsafe uploadFile filename"`** ✓ 与报告 086 一致 |
| 26 | ★★ 上传 7 字段 | `context`/`name`/`visibility`/`data`/`owner`/`platform`/`flags` + 尾 0 |
| 27 | ★★ 上传上限 | **16 MB** |
| 28 | ★★★ owner 鉴权 | 只能写自己 ⇒ 报错串 **`"rejected uploadFile request for a non-authenticated owner"`** ✓ |
| 29 | ★★★ 临时文件名 | **`.writing.<PID>.<序号>`**（第五次出现原子写） |

---

## 八、结论

### 1. ★★★★★ **`configs_s.info` 必须加密,否则客户端**静默崩溃**（254 MB dump,零错误行）

★ **⇒ 证据是 dump 扫描：所有发布方文件内容都驻留内存,唯独 `configs_s` 缺席。**
**★ ⇒ 与报告 086 的三条字符串**逐字相同** ✓**

### 2. ★★★★★ **`makeOfflinePlaylist` 把 `rule 1011 N`（N>1）原地改成 `1`**

★ **⇒ 让离线单人也能开。**

### 3. ★★★★★ **文件名别名：客户端请求无 `_release`,盘上有 `_release`**

### 4. ★★★★★ **`CodolPresence` 的十轮失败最终归结为"行定长补齐到 `0x60`"**

```
★★★ 根因：**客户端按行对象尺寸步进读取游标**,非定长 ⇒ 第 2 条起全部错位
        ↓
★ 好友每条仅 19 B,行距 96 B ⇒ **补齐到 96**
   （与 `StatsService` 的 `0x98` 补齐同一手法）
```

### 5. ★★★★★ **v27 的 diff 方法论**："找出从未被改动的字节"

### 6. ★★★★ **`68/4` 的 presence 镜像**（blob 与客户端 `68/3` 同形）

### 7. ★★★ **路径穿越防护与 owner 鉴权**（报错串与报告 086 逐字一致）

### 8. ★★★ **FNV-1a 第四次出现**

---

## 九、下一步

- `Servers.cpp`（624 行）/ `DedicatedBookingDispatcher`（926 行）/ `SharedRoom*`（4 文件）
- 然后 `game_server` 根 32 文件 / `server_mp` 154 文件
