# 学习报告 106（重开）— `IdentityConfig`（108 + 165 行）+ `Auth3TlsTransport.hpp`（31 行）

**学习范围**：`IdentityConfig.hpp`（8,954 B / 108 行）+ `IdentityConfig.cpp`（6,983 B / 165 行）+ `Auth3TlsTransport.hpp`（939 B / 31 行）
**性质**：全实测（**三文件逐行读完**）
**★★★★★ 本报告收录五个重大发现**：①**`DefaultUsername = "SGamingSH0X"`（现役值）+ 十次改名的完整历史** ②**`d39` 拒单原文（base64 逐字节对比）** ③**GBK 与 UTF-8 的渲染分裂** ④**`validateDisplayName` 的 1–16 **字节**上限** ⑤**身份文件的路径与原子写**

---

## 一、★★★★★ **`DefaultUsername` 的现役值与十次改名史**

### 1.1 ★★★★★ 现役值（`IdentityConfig.hpp` 最后一行）

```cpp
inline constexpr std::string_view DefaultUsername = "**SGamingSH0X**";
```

★★★ **⇒ 现役值 = `SGamingSH0X`（10 字节纯 ASCII）。**

### ★★★★★ 完整的改名时间线（从注释逐条提取）

| # | 时间 | 值 | 编码 | 字节数 | 说明 |
|---|---|---|---|---|---|
| **1** | 2026-10-07 10:3x | **`AdministraClient`** | — | — | 对齐客户端当时的实际名 |
| **2** | 2026-10-07 11:0x | **`Lifetime`** | — | — | 甲方指定 |
| **3** | 2026-10-07 15:0x | **`Lifetime丷`** | ★ **GBK** | **10** | `4C 69 66 65 74 69 6D 65 81 52` |
| **4** | 2026-10-07 15:5x | **`Lifetime丷`** | ★★ **UTF-8** | **11** | `4C…65 E4 B8 B7` |
| **5** | 2026-10-07 16:5x | **（全线 UTF-8）** | UTF-8 | — | v13 最终方案 |
| **6** | 2026-10-11 | **`Lifetime_`** | UTF-8 | 9 | ★ **从未部署** |
| **7** | 2026-10-11 同日 | ★ **`Sunl1ght`** | UTF-8 | **8** | 甲方追加 |
| **8** | 2026-10-12 | ★★ **`内裤再美终究装逼`** | ★ **GBK** | **16**（**正好装满**） | 甲方选定 |
| **9** | 2026-10-13（会话 2005） | ★★★ **`SGamingSH0X`** | UTF-8 | **10** | ★ **现役** |

★★★ **⇒ 九次记录（含一次"从未部署"）。**

### ★★★★★ 每一轮都强调的**"三处必须逐字节相同"**

```
⚠ 三处必须**逐字节相同**，缺一即进不去服：
  1) 本常量（`IdentityConfig.hpp`）
  2) 启动器 `restart_chain.ps1` 的 `OLMOD_DISPLAY_NAME` **且** `..._ENC`（'utf-8' 或 'gbk'）
  3) `force_display_name.py` 写进 16 字节字段的字节（编码与上面一致）
        ↓
★★★★★ ⇒ **这是整个项目最脆弱的一致性约束**
```

---

## 二、★★★★★ **`d39` 拒单原文（逐字节对比）**

### 2.1 ★★★★★ 完整日志（逐字）

```
connect userinfo name does not match the session roster
  (name="**QWRtaW5pc3RyYUNsaWVudA==**" expected="**QWx3YXlzb2ZmbGluZQ==**" username="**Alwaysoffline**")
```

### ★★★★★ base64 解码

| 字段 | base64 | **解码** |
|---|---|---|
| **`name`** | `QWRtaW5pc3RyYUNsaWVudA==` | ★ **`AdministraClient`** |
| **`expected`** | `QWx3YXlzb2ZmbGluZQ==` | ★ **`Alwaysoffline`** |
| **`username`** | （明文） | **`Alwaysoffline`** |

★★★ **⇒ 客户端报的名字是 `AdministraClient`,而我们栈的房内身份名是 `Alwaysoffline` ⇒ 失配。**

★★ **⇒ 注释明确（逐字）："`name` 解码 = `AdministraClient`（客户端在 netchan connect 里报的自己的玩家名）"。**

### ★★★★★ 另一次拒单（GBK vs UTF-8,逐字节）

```
16:34:12 拒单原文
  name="**TGlmZXRpbWWBUg==**"(GBK)  vs  expected="**TGlmZXRpbWXkuLc=**"(UTF-8)
```

| 字段 | base64 | **字节** | 编码 |
|---|---|---|---|
| **`name`** | `TGlmZXRpbWWBUg==` | ★ `4C 69 66 65 74 69 6D 65 **81 52**` | **GBK** |
| **`expected`** | `TGlmZXRpbWXkuLc=` | ★ `4C 69 66 65 74 69 6D 65 **E4 B8 B7**` | **UTF-8** |

★★★★★ **⇒ 精确的字节对照：**
```
`丷` 的 **GBK**   = `**81 52**`（2 字节）⇒ 全名 **10** 字节
`丷` 的 **UTF-8** = `**E4 B8 B7**`（3 字节）⇒ 全名 **11** 字节
        ↓
★★★ ⇒ 同一个字,两种编码差 **1 字节** ⇒ **connect 校验逐字节相等 ⇒ 失配**
```

★ **⇒ 这是**"同一个字在不同编码下字节不同"的精确物证**。**

### ★★★ 为什么我们这套不跑 `Auth3Protocol::authenticate`

```
"我们这套 auth 走 `fake_auth_tls.py`（Python shim），
 laowai 的 `Auth3Protocol::authenticate` **不会跑**
 ⇒ `identity.username` **永远停在 `AuthIdentity` 的编译期默认值**（本常量）,
 不会被 `resolveDisplayName`（`Identity.json`）覆盖。"
        ↓
★★★ ⇒ **`DefaultUsername` 常量才是真正的生效值**
   ⇒ 而 `Identity.json` 在**我们的路径上不生效**
```

★★ **⇒ 这修正了报告 081 的推断（"`Identity.json` 是显示名载体"）：**
```
报告 081：`Identity.json` = `{"username": "Alwaysoffline"}`,字段名是 `username`
        ↓
★★★ 本报告：`Identity.json` 的 schema 是 `{"schemaVersion": 1, "displayName": "..."}`
   ⇒ **字段名是 `displayName`,不是 `username`**!
   ⇒ 而 `loadConfiguredUsername` 读的是 **`username`** 字段（另一个函数）
        ↓
★★★★★ ⇒ **两个不同的读取路径：**
   `loadDisplayName(path)`      ⇒ 读 **`displayName`**（schemaVersion 1）
   `loadConfiguredUsername(path)` ⇒ 读 **`username`**（无 schema 校验）
   ⇒ ★ 交付包的 `Identity.json` 有 `username` ⇒ 走 `loadConfiguredUsername`（migration seed）
```

---

## 三、★★★★★ **GBK 与 UTF-8 的渲染分裂**

### 3.1 ★★★★★ 完整证据（逐字）

```cpp
//   ② 名字被多处消费：**只有大厅右上角是 GBK 渲染**；房间内角色名/右侧面板/榜单/列表
//      全部是 **UTF-8 渲染**（GBK 字节在这些地方显示成 `▮R`）。
//   ③ 字段一份字节不可能同时满足两种渲染 ⇒ 先保大头（全 UTF-8）,
//      右上角的「丷」留给**分缓冲定向写入**专项（给不同内存拷贝写不同编码）。
```

### ★★★★★ 两套渲染的完整清单

| 位置 | 渲染编码 |
|---|---|
| **大厅右上角** | ★ **GBK** |
| **房间内角色名** | ★★ **UTF-8** |
| **右侧面板** | **UTF-8** |
| **榜单** | **UTF-8** |
| **列表** | **UTF-8** |

★★★ **⇒ 5 个消费点里 **1 个 GBK、4 个 UTF-8** ⇒ "先保大头"。**

### ★★★ 榜单把 GBK 渲染成 `▮R` 的证据

```
"① 榜单把 GBK 的 `81 52` **逐字节渲染成「▮R」**（该管线不是 GBK 解码）"
        ↓
★★★ ⇒ `0x81` 和 `0x52` 被**当成两个独立字符**渲染
   ⇒ `0x52` = `'R'` ⇒ 显示成 `▮R`
        ↓
★★★ ⇒ 这是**"管线按 UTF-8 解释 GBK 字节"**的精确症状
```

★ **⇒ 与报告 106 的 `d39` 拒单是**同一根因的两个表现**（一个是校验失败,一个是显示错误）。**

### ★★★ `nlohmann::json` 的 `type_error.316`（第 3 个后果）

```cpp
//   另：GBK 字节若直接进 nlohmann JSON 会在 `.dump()` 抛 `type_error.316`（mmbook 推送链上）,
//   JSON 边界已统一走 `NameWireCodec.hpp`（JSON=UTF-8 / 线上=GBK）。
```

★★★ **⇒ 第三个后果：GBK 字节进 JSON 会抛异常。**

★★ **⇒ 解决：**`NameWireCodec.hpp` 统一处理 JSON=UTF-8 / 线上=GBK。**

★★ **⇒ 且日志里那 3 条 `Rejected LSG frame: [json.exception.type_error.316] invalid UTF-8 byte at index 1: 0xDA`：**
```
`内` 的 GBK = `**C4 DA**`
        ↓
★★★ `0xDA` 不是合法 UTF-8 起始字节 ⇒ 抛 `type_error.316`
```

---

## 四、★★★★★ **`validateDisplayName` 的 1–16 **字节**上限**

### 4.1 ★★★★★ 完整实现（`IdentityConfig.cpp:20-42`）

```cpp
void validateDisplayName(const std::string_view displayName)
{
    if (displayName.empty() || displayName.size() > **16**)
        throw std::runtime_error("display name must contain 1 to 16 **bytes**");
    // ★ 2026-10-05 22:2x -- LOCAL OVERRIDE (DSH).  Upstream rejects every byte outside
    // 0x20..0x7E ("printable ASCII only"), which throws on a CJK display name and makes
    // `resolveDisplayName` fall back to the migration seed's `username`.  MEASURED
    // 2026-10-05 21:47-21:49: with `displayName = "笑死了"` (9 bytes UTF-8) the backend's own
    // room/instant-message sender name was `Alwaysoffline` -- i.e. the profile name was
    // refused and the seed won.  The name reaches the client as UTF-8 in two places
    // (auth ticket `+33`, `extra_data.username` base64), and `fake_auth_tls.py` already
    // encodes it UTF-8, so the check is relaxed to "no control characters" while the
    // 1..16 **byte** cap above stays exactly as upstream wrote it.
    for (const auto character : displayName)
    {
        const auto byte = static_cast<unsigned char>(character);
        if (byte < **0x20** || byte == **0x7F**)
            throw std::runtime_error("display name must not contain control characters");
    }
}
```

### ★★★★★ 一次实测失败的完整记录（逐字）

```
"MEASURED **2026-10-05 21:47-21:49**: with `displayName = "**笑死了**"` (**9 bytes UTF-8**)
 the backend's own room/instant-message sender name was `**Alwaysoffline**`
 -- i.e. **the profile name was refused and the seed won**."
        ↓
★★★ ⇒ 上游的 `0x20..0x7E`（"printable ASCII only"）**拒绝了 CJK 名**
   ⇒ `resolveDisplayName` **回退到 migration seed 的 `username`**
   ⇒ 表现为"设了名字但没生效"
```

### ★★★ 三条精确的规则对照

| 规则 | 值 |
|---|---|
| **长度上限** | ★ **1–16 字节**（不是字符） |
| **允许** | ★★ **`≥ 0x20` 且 `≠ 0x7F`**（**无控制符**） |
| **上游原规则** | ★★★ **`0x20..0x7E`（仅可打印 ASCII）** |

★★★ **⇒ 与报告 093 的 `DedicatedSession::validUsername` **完全相同的口径** ✓**
**⇒ 且注释明确："the 1..16 **byte** cap above stays exactly as upstream wrote it"（字节上限未动）。**

---

## 五、★★★★★ **身份文件的路径与原子写**

### 5.1 ★★★★★ `identityPath`（第 158–164 行）

```cpp
std::filesystem::path PlayerIdentityStore::identityPath(
    const std::uint32_t titleId, const std::uint64_t userId) const
{
    return assetRoot_ / std::to_string(titleId) / userIdDirectory(userId) / L"Identity.json";
}
```

### ★★★★★ 完整路径

```
`<assetRoot>` / `<titleId>` / `<userId 大写十六进制>` / `Identity.json`
        ↓
默认 assetRoot = `./Ayria/Assets/Alwaysoffline`
默认 titleId   = `1004`
        ↓
★★★ 例：`./Ayria/Assets/Alwaysoffline/**1004**/**1100001DEADC0DE**/Identity.json`
        ↓
★★★★★ ⇒ **与报告 083 的清单条目 `Ayria/Assets/Alwaysoffline/1004/1100001DEADC0DE/the.json`
   同一个目录**（只是文件名不同：`Identity.json` vs `the.json`）
```

### ★★★ `userIdDirectory` 的**大写十六进制**（第 44–56 行）

```cpp
std::string userIdDirectory(const std::uint64_t userId)
{
    std::array<char, 16> buffer{};
    const auto result = std::to_chars(buffer.data(), buffer.data() + buffer.size(), userId, **16**);
    ...
    for (auto &character : value)
        if (character >= 'a' && character <= 'f')
            character = static_cast<char>(character - 'a' + 'A');    // ★ 转大写
    return value;
}
```

★★★ **⇒ `to_chars(..., 16)` 默认小写 ⇒ **手工转大写**。**
**⇒ 所以目录名是 **`1100001DEADC0DE`**（全大写）✓ 与报告 083 的清单**完全一致**。**

### ★★★★★ 原子写（`saveDisplayName`，第 78–118 行）

```cpp
auto temporary = path;
temporary += L"**.writing**";                          // ★ 临时文件后缀
{
    std::ofstream output(temporary, std::ios::trunc);
    output << Json{
        { "schemaVersion", **1** },
        { "displayName", displayName },
    }.dump(**2**) << '\n';                             // ★ 2 空格缩进
    ...
}
if (!MoveFileExW(
        temporary.c_str(), path.c_str(),
        MOVEFILE_REPLACE_EXISTING | **MOVEFILE_WRITE_THROUGH**))   // ★ 原子替换
{
    ...
    std::filesystem::remove(temporary, error);
    throw std::system_error(...);
}
```

★★★★★ **⇒ 三个精确细节：**
```
① 临时文件后缀 **`.writing`** ⇒ 与报告 096 的 `RuntimeLog` 的 `.writing.` **同一约定** ✓
② `MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH` ⇒ **原子替换 + 直写磁盘**
③ 失败则**删除临时文件**并抛异常
```

★ **⇒ 第 ② 条的 `MOVEFILE_WRITE_THROUGH` ⇒ **不经过系统缓存**,确保落盘。**

### ★★★ 两份 JSON 的 schema 差异

| 函数 | 读/写的字段 | schema 校验 |
|---|---|---|
| **`loadDisplayName(path)`** | ★★ **`displayName`** | ★ **必须 `schemaVersion == 1`** |
| **`loadConfiguredUsername(path)`** | ★★★ **`username`** | ★ **无 schema 校验** |
| **`saveDisplayName(path, name)`** | **`displayName`** | 写 `schemaVersion: 1` |

★★★★★ **⇒ 两条读取路径的字段名**不同**：**
```
`loadDisplayName`      ⇒ `displayName`（+ schemaVersion 1）
`loadConfiguredUsername` ⇒ `username`（无 schema）
        ↓
★★★ 而交付包的 `Identity.json` = `{"username": "Alwaysoffline"}`
   ⇒ **走 `loadConfiguredUsername`**（migration seed 路径）
        ↓
★★★★★ ⇒ 这解释了报告 081 的观察（字段是 `username`）
   ⇒ 也解释了为什么 `force_display_name.py` 找 `displayName` 会失败
     （那个文件里根本没有 `displayName` 字段）
```

### ★★★ `resolveDisplayName` 的三级逻辑（第 108–132 行）

```
① 若 `<root>/<title>/<uid>/Identity.json` **是常规文件** ⇒ `loadDisplayName` 读 `displayName`
        ↓
② 若路径**存在但不是常规文件** ⇒ 抛 "player identity profile path is not a regular file"
        ↓
③ 若**不存在** ⇒ `loadConfiguredUsername(migrationSeed_)` 读 seed 的 `username`
   ⇒ **写入** `<root>/<title>/<uid>/Identity.json` ⇒ 返回
        ↓
★★★ ⇒ 这是**"首次访问时播种"**模式
```

★ **⇒ 与报告 083 的 `installPolicy: **if-missing**` + `mutable: **true**` **完全吻合** ✓**

---

## 六、★★★★ `Auth3TlsTransport.hpp` 的极简接口

```cpp
class Auth3TlsTransport
{
public:
    using Diagnostic = std::function<void(std::string_view)>;      // ★ 诊断回调

    Auth3TlsTransport(
        AuthSession &session,
        std::string hostname,                                      // ★ 主机名
        Diagnostic diagnostic = {},
        PlayerIdentityStore *identityStore = nullptr);
    ~Auth3TlsTransport();

    Auth3TlsTransport(const Auth3TlsTransport &) = delete;          // ★ 禁拷贝
    Auth3TlsTransport &operator=(const Auth3TlsTransport &) = delete;

    void reset();
    void receive(std::span<const std::uint8_t> encrypted);          // ★ 喂密文
    [[nodiscard]] std::vector<std::uint8_t> takeOutput(std::size_t limit);  // ★ 取输出

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;                                    // ★ pImpl
};
```

★★★ **⇒ 一个**流式 TLS 状态机**的接口：**
```
`receive(encrypted)` ⇒ 喂入密文
`takeOutput(limit)`  ⇒ 取出待发送的字节（带上限）
`reset()`            ⇒ 重置
        ↓
★★★ ⇒ 这是一个**"外部驱动"的 TLS**（不自己持 socket）
```

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ **`DefaultUsername` 现役值** | **`"SGamingSH0X"`**（10 字节纯 ASCII） |
| 2 | ★★★★★ **九次改名史** | `AdministraClient` → `Lifetime` → `Lifetime丷`(GBK) → `Lifetime丷`(UTF-8) → 全线 UTF-8 → `Lifetime_`(**从未部署**) → `Sunl1ght` → **`内裤再美终究装逼`(GBK,16 字节正好装满)** → **`SGamingSH0X`** |
| 3 | ★★★★★ **三处必须逐字节相同** | ①`IdentityConfig.hpp` 常量 ②`restart_chain.ps1` 的 `OLMOD_DISPLAY_NAME` **且** `..._ENC` ③`force_display_name.py` 写入的字节 |
| 4 | ★★★★★ **`d39` 拒单原文** | `name="QWRtaW5pc3RyYUNsaWVudA=="`（**`AdministraClient`**）vs `expected="QWx3YXlzb2ZmbGluZQ=="`（**`Alwaysoffline`**） |
| 5 | ★★★★★ **GBK vs UTF-8 的字节物证** | `丷`：**GBK `81 52`**（全名 10 字节）vs **UTF-8 `E4 B8 B7`**（11 字节）⇒ `name="TGlmZXRpbWWBUg=="` vs `expected="TGlmZXRpbWXkuLc="` |
| 6 | ★★★★ **为什么 `DefaultUsername` 才是生效值** | 我们走 `fake_auth_tls.py` ⇒ `Auth3Protocol::authenticate` **不跑** ⇒ `identity.username` **停在编译期默认值** |
| 7 | ★★★★★ **更正报告 081** | `Identity.json` 的 schema 是 `{"schemaVersion":1,"displayName":...}`；**字段名是 `displayName` 不是 `username`**；交付包那份有 `username` ⇒ 走 `loadConfiguredUsername` |
| 8 | ★★★★★ **渲染分裂（5 个消费点）** | **大厅右上角 = GBK**；**房间内角色名 / 右侧面板 / 榜单 / 列表 = UTF-8** |
| 9 | ★★★ `▮R` 的成因 | 榜单把 GBK 的 **`81 52`** 逐字节渲染 ⇒ `0x52 = 'R'` ⇒ **`▮R`** |
| 10 | ★★★ **`type_error.316` 的成因** | `内` 的 GBK = **`C4 DA`** ⇒ `0xDA` 不是合法 UTF-8 起始字节 |
| 11 | ★★ `NameWireCodec.hpp` | 统一 JSON=UTF-8 / 线上=GBK |
| 12 | ★★★★ **`validateDisplayName` 三规则** | **1–16 字节** / **`≥0x20` 且 `≠0x7F`** / 上游原为 **`0x20..0x7E`** |
| 13 | ★★★★★ **一次实测失败** | `displayName = "笑死了"`（**9 字节 UTF-8**）被上游拒绝 ⇒ sender name 仍是 **`Alwaysoffline`** ⇒ "**the profile name was refused and the seed won**" |
| 14 | ★★★ 与报告 093 一致 | `DedicatedSession::validUsername` **同一口径** |
| 15 | ★★★★★ **身份文件路径** | `./Ayria/Assets/Alwaysoffline/**1004**/**1100001DEADC0DE**/Identity.json` ⇒ 与清单 `the.json` **同一目录** |
| 16 | ★★★ `userIdDirectory` | `to_chars(...,16)` 后**手工转大写** ⇒ 目录名全大写 ✓ |
| 17 | ★★★★ **原子写** | 临时后缀 **`.writing`**（与 096 的 `.writing.` 同约定）+ **`MOVEFILE_REPLACE_EXISTING \| MOVEFILE_WRITE_THROUGH`** + 失败删临时 |
| 18 | ★★★ 两份 JSON schema | `loadDisplayName` 读 **`displayName`**（**必须 schemaVersion 1**）；`loadConfiguredUsername` 读 **`username`**（**无 schema 校验**） |
| 19 | ★★★ `resolveDisplayName` 三级 | 常规文件 ⇒ 读；存在但非常规 ⇒ 抛；不存在 ⇒ **播种**（写 seed 的 username） |
| 20 | ★★ 与清单吻合 | `installPolicy: if-missing` + `mutable: true` ✓ |
| 21 | ★★★ `Auth3TlsTransport` | **外部驱动的流式 TLS**（`receive` 喂密文 / `takeOutput` 取输出 / `reset`），pImpl |

---

## 八、结论

### 1. ★★★★★ **`DefaultUsername = "SGamingSH0X"` 是现役值,且有一份九次改名的完整历史**

★ **⇒ 每一轮都强调**"三处必须逐字节相同,缺一即进不去服"**。**

### 2. ★★★★★ **`d39` 拒单给出了 GBK vs UTF-8 的精确字节物证**

```
`丷`：**GBK `81 52`**（全名 10 字节）vs **UTF-8 `E4 B8 B7`**（11 字节）
        ↓
★★★ `name="TGlmZXRpbWWBUg=="` vs `expected="TGlmZXRpbWXkuLc="` ⇒ **逐字节失配**
```

### 3. ★★★★★ **名字在 5 个消费点上有两套渲染**（1 个 GBK、4 个 UTF-8）

★ **⇒ 一份字节不可能同时满足 ⇒ 只能"先保大头"。**

### 4. ★★★★★ **更正报告 081：`Identity.json` 的正确字段是 `displayName`**

```
`loadDisplayName`        ⇒ 读 `displayName`（+ schemaVersion 1）
`loadConfiguredUsername` ⇒ 读 `username`（无 schema）
        ↓
★★★ 交付包那份有 `username` ⇒ **走 seed 路径**
   ⇒ 这解释了为什么 `force_display_name.py` 找 `displayName` 会失败
```

### 5. ★★★★ **`DefaultUsername` 常量才是生效值**（`Auth3Protocol::authenticate` 在我们的路径上不跑）

### 6. ★★★ **`validateDisplayName` 与 `DedicatedSession::validUsername` 同一口径**（1–16 **字节** + 无控制符）

---

## 九、下一步

- `CodolClientPatches.cpp`（**882 行**）+ `.hpp`（41 行）
- `Auth3TlsTransport.cpp`（311 行）
- `NameWireCodec.hpp`（如果存在）
- 然后 12 个 Service 实现
