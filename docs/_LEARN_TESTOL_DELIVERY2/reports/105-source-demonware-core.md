# 学习报告 105（重开）— `Demonware` 的 4 组基础件（Auth3Protocol.hpp / AuthSession / ByteBuffer / Crypto）

**学习范围**：`Auth3Protocol.hpp`（29 行）+ `AuthSession.hpp`（26）+ `.cpp`（50）+ `ByteBuffer.hpp`（50）+ `.cpp`（258）+ `Crypto.hpp`（33）+ `.cpp`（225）
**性质**：全实测（**7 文件逐行读完**）
**★★★★★ 本报告收录六个重大发现**：①**`AuthIdentity` 的默认 userId = `0x1100001DEADC0DE`（解开 083 的悬案）** ②**`parsePlatformUserId` 的 `0x0110000100000000 \| parsed` 拼接** ③**Demonware 的 12 个类型码** ④**`CLIENTCHAL`/`BDDATA` 密钥扩展** ⑤**`expandKey` 的 HMAC 链式扩展** ⑥**用 `BCrypt` 而非 OpenSSL**

---

## 一、★★★★★ **`AuthIdentity` 的默认值（解开报告 083 的悬案）**

### 1.1 ★★★★★ 完整定义（`AuthSession.hpp:10-17`）

```cpp
struct AuthIdentity
{
    std::uint32_t titleId{ **1004** };
    std::uint64_t userId{ **0x1100001DEADC0DEULL** };
    std::string username{ DefaultUsername };
    std::array<std::uint8_t, **24**> sessionKey{};
};
```

### ★★★★★ 四个默认值

| 字段 | 默认值 | 印证 |
|---|---|---|
| **`titleId`** | ★ **1004** | ✓ 与报告 077 的 `build_number` 同文件、083 的清单 `titleId`、089 的 `MarketplaceSkus.titleId` 全部一致 |
| **`userId`** | ★★★★★ **`0x1100001DEADC0DE`** | ★★★ **见下** |
| **`username`** | `DefaultUsername`（在 `IdentityConfig.hpp`） | — |
| **`sessionKey`** | ★★ **24 字节** | ★ 与报告 103 的"3DES 需 24 字节密钥"**完全吻合** |

### ★★★★★ **`0x1100001DEADC0DE` 与报告 083 的对照**

```
报告 083（`ol-mod-runtime-manifest.json`）：
  玩家种子目录名 = **`1100001DEADC0DE`**
  而我推断 = `Platform.json` 的 `platformUserId` **`"01100001DEADC0DE"` 去掉前导 0**
        ↓
★★★★★ 本报告（代码级）：
  `userId` 默认值 = **`0x1100001DEADC0DE`**
        ↓
★★★ 十六进制 **`0x1100001DEADC0DE`** 去掉 `0x` = **`1100001DEADC0DE`** ✓
        ↓
★★★★★ ⇒ **报告 083 的推断被代码级完全证实**
```

★★ **⇒ 且现在知道了**为什么是 `11` 而不是 `01`：**
```
`Platform.json` 的 `platformUserId` = `"**01100001**DEADC0DE"`（16 字符）
        ↓
★★★ 若按 `uint64` 解析这个**十六进制串** ⇒ `0x01100001DEADC0DE`
   ⇒ **去掉前导 0 后是 `1100001DEADC0DE`**（15 字符）
        ↓
★★★ 而代码里的默认值是 **`0x1100001DEADC0DE`**（**同一个数**）
   ⇒ 即：`0x01100001DEADC0DE == 0x1100001DEADC0DE`（前导零无意义）
        ↓
★★★★★ ⇒ **两者是同一个 64 位整数**,只是书写形式不同
```

### ★★★★★ `sessionKey` 的 24 字节

★★ **⇒ 这与报告 103 的"3DES 需 24 字节密钥,而 ticket 里 `sessionKey` 只 16 字节"**解决了矛盾**：**
```
`AuthIdentity::sessionKey` = **24 字节**（正确）
        ↓
★★★ 但 `makeTicket` 里 `std::copy(identity.sessionKey.begin(), identity.sessionKey.end(), ticket.begin() + 97)`
   ⇒ **复制 24 字节到偏移 97**
        ↓
★★★ 而 ticket 只有 128 字节 ⇒ **97 + 24 = 121** ⇒ ★★★ **正好覆盖到偏移 120**
   ⇒ 而 `ticket[121] = '3'` ⇒ **紧接其后,不冲突** ✓
        ↓
★★★★★ ⇒ **报告 103 里"只 16 字节"的说法是错的**
   ⇒ `sessionKey` 是 **24 字节**,`makeTicket` 复制 24 字节到 `[97, 120]`
   ⇒ 而报告 044 的 Python 版记 "sessionKey at `0x61`(97)" 时**可能只记了前 16**
```

★★ **⇒ 更正：ticket 的 `[97, 120]` 是 **24 字节** sessionKey,`[121,123]` 是 `'3','U','"'`。**

---

## 二、★★★★★ **`parsePlatformUserId` 的 ID 拼接**

### 2.1 ★★★★★ 完整实现（`AuthSession.cpp:11-27`）

```cpp
bool parsePlatformUserId(std::string_view value, std::uint64_t &output)
{
    if (value.starts_with("0x") || value.starts_with("0X"))
        value.remove_prefix(2);
    if (value.empty()) return false;

    std::uint64_t parsed{};
    const auto result = std::from_chars(value.data(), value.data() + value.size(), parsed, **16**);
    if (result.ec != std::errc{} || result.ptr != value.data() + value.size() || !parsed)
        return false;
    output = parsed <= **0xFFFFFFFF**ull
        ? **0x0110000100000000**ull | parsed      // ★★★ 拼接
        : parsed;
    return true;
}
```

### ★★★★★ **`0x0110000100000000 | parsed` 的精确语义**

```
若 `parsed <= 0xFFFFFFFF`（即 32 位以内）
    ⇒ `output = **0x0110000100000000** | parsed`
        ↓
★★★ 即：**把 32 位的值放进低 32 位,高 32 位填 `0x01100001`**
        ↓
★★★★★ ⇒ **`0x01100001` 是"平台前缀"**（8 个十六进制字符 = 32 位）
   ⇒ 与 `platformUserId` 的 **`01100001`DEADC0DE** 结构**完全吻合** ✓
```

### ★★★★★ 完整的 ID 结构

```
`0x` **`01100001`** `DEADC0DE`
   ↑         ↑
   平台前缀   用户 ID（32 位）
        ↓
★★★★★ ⇒ **`0x01100001` 是 CODOL 平台命名空间前缀**
   ⇒ 若用户只给 32 位的 ID（如 `DEADC0DE`）⇒ **自动补上前缀**
   ⇒ 若已给 64 位 ⇒ **原样使用**
```

★★ **⇒ 这解释了报告 083 的"两个命名空间"问题：**
```
**平台 ID**（LSG/room 层）= `0x01100001` **+ 32 位用户 ID**
**Demonware account ID** = 独立的 64 位值（如 `0xE7C8A98A6B4C2D0E`）
        ↓
★★★ ⇒ 本文件处理的是**平台 ID**（`0x01100001` 前缀）
```

### ★★★ 环境变量（第 35–47 行）

```cpp
if (_dupenv_s(&configured, &size, "**OLMOD_PLATFORM_USER_ID**") == 0 && configured)
{
    std::uint64_t parsed{};
    if (parsePlatformUserId(configured, parsed))
        identity_.userId = parsed;
    std::free(configured);
}
```

★★ **⇒ 第 **14** 个 `OLMOD_*` 环境变量。**

### ★★★ `AuthSession` 的线程安全

```cpp
[[nodiscard]] AuthIdentity snapshot() const { std::scoped_lock lock(mutex_); return identity_; }
void update(AuthIdentity identity) { std::scoped_lock lock(mutex_); identity_ = std::move(identity); }
```

★★ **⇒ `mutable std::mutex` + `scoped_lock` ⇒ 标准做法。**

---

## 三、★★★★★ **`ByteBuffer`：Demonware 的 12 个类型码**

### 3.1 ★★★★★ 完整类型表（`ByteBuffer.cpp:8-20`）

```cpp
constexpr std::uint8_t TypeBool   = **0x01**;
constexpr std::uint8_t TypeU8     = **0x03**;
constexpr std::uint8_t TypeU16    = **0x06**;
constexpr std::uint8_t TypeI32    = **0x07**;
constexpr std::uint8_t TypeU32    = **0x08**;
constexpr std::uint8_t TypeI64    = **0x09**;
constexpr std::uint8_t TypeU64    = **0x0A**;
constexpr std::uint8_t TypeString = **0x10**;
constexpr std::uint8_t TypeBlob   = **0x13**;
constexpr std::uint8_t TypeArray  = **0x6C**;
```

### ★★★★★ 完整的 10 个类型码

| 码 | 类型 | 大小 |
|---|---|---|
| **`0x01`** | **Bool** | 1 |
| **`0x03`** | **U8** | 1 |
| **`0x06`** | **U16** | 2 |
| **`0x07`** | ★★ **I32** | 4 |
| **`0x08`** | **U32** | 4 |
| **`0x09`** | **I64** | 8 |
| **`0x0A`** | **U64** | 8 |
| **`0x10`** | **String** | 变长（NUL 结尾） |
| **`0x13`** | **Blob** | 变长（u32 长度 + 数据） |
| **`0x6C`** | ★★ **Array** | 变长（元素类型 + 字节数 + 个数） |

### ★★★★★ `TypeI32 = 0x07` 的完整注释（逐字）

```cpp
// SignedInteger32 in the shared Demonware type enum, one below TypeU32. The
// matchmaking session record needs it: its query-criterion fields are SIGNED
// and the client type-checks each value, so writing them as TypeU32 is not a
// cosmetic difference.
```

★★★★★ **⇒ 三条精确事实：**
```
① `TypeI32 = 0x07` = **`TypeU32 - 1`**（"one below TypeU32"）
② ★★★ 用于 **matchmaking 会话记录**的 **query-criterion 字段**
③ ★★★★★ **客户端会**逐值检查类型** ⇒ 用 `TypeU32` 写有符号值**不是外观差异**
   ⇒ **会导致失败**
```

★★ **⇒ 这是**"类型码错误不是小事"的明确声明**（与报告 099 的武器索引 10 vs 11 同一性质）。**

### ★★★★★ 数组的精确格式（`readU32Array` / `writeU32Array`）

```
`TypeArray`(0x6C) + **元素类型**(0x08) + **字节数**(u32) + **个数**(u32) + 元素数据
        ↓
★★★ 且校验：`byteSize == count * 4`（`readU32Array` 里）
   ⇒ **字节数必须与个数严格匹配**
        ↓
★★★ 且 `count > UINT32_MAX / 4` ⇒ 拒绝（**防溢出**）
```

★★ **⇒ 一个**自描述的数组格式**（类型 + 字节数 + 个数三重信息）。**

### ★★★ `useDataTypes` 开关（第 50 行 + 第 36–38 行）

```cpp
void useDataTypes(bool enabled) { useDataTypes_ = enabled; }

bool readType(const std::uint8_t expected)
{
    if (!useDataTypes_) return true;      // ★ 关闭时跳过类型检查
    ...
}
```

★★★ **⇒ 可以关闭类型前缀 ⇒ 支持**无类型的裸数据流**（可能用于某些老协议）。**

### ★★★ `require` 的 fail-closed（第 41–49 行）

```cpp
bool ByteBuffer::require(const std::size_t size)
{
    if (!valid_ || size > remainingSize())
    {
        valid_ = false;     // ★ 一旦失败就永久 invalid
        return false;
    }
    return true;
}
```

★★ **⇒ `valid_` 一旦置 false 就**不可恢复**（后续所有读都失败）。**

---

## 四、★★★★★ **`Crypto`：Demonware 的密钥派生**

### 4.1 ★★★★★ `deriveSessionKeys` 全文（`Crypto.cpp`）

```cpp
SessionKeys deriveSessionKeys(
    const std::span<const std::uint8_t> sessionKey,
    const std::span<const std::uint8_t> handshakeTranscript)
{
    if (sessionKey.size() != **24**)
        throw std::invalid_argument("DW session key must be 24 bytes");

    const auto transcriptHash = **sha1**(handshakeTranscript);
    const auto secret = **hmacSha1**(sessionKey, transcriptHash);
    const auto challenge = **expandKey**(secret, "**CLIENTCHAL**", **16**);
    const auto data      = **expandKey**(secret, "**BDDATA**", **72**);

    SessionKeys result;
    std::copy_n(challenge.begin() + **8**,  result.responseId.size(),  result.responseId.begin());   // 8
    std::copy_n(data.begin(),                result.requestHmac.size(), result.requestHmac.begin());  // 20
    std::copy_n(data.begin() + **20**,       result.responseHmac.size(),result.responseHmac.begin()); // 20
    std::copy_n(data.begin() + **40**,       result.decrypt.size(),     result.decrypt.begin());     // 16
    std::copy_n(data.begin() + **56**,       result.encrypt.size(),     result.encrypt.begin());     // 16
    return result;
}
```

### ★★★★★ 完整的密钥派生链

```
① `transcriptHash = **SHA1**(handshakeTranscript)`            ⇒ 20 字节
        ↓
② `secret = **HMAC-SHA1**(key=sessionKey(24), data=transcriptHash)`  ⇒ 20 字节
        ↓
③ `challenge = **expandKey**(secret, "**CLIENTCHAL**", **16**)`  ⇒ 16 字节
   `data      = **expandKey**(secret, "**BDDATA**",     **72**)`  ⇒ 72 字节
        ↓
④ 切分：
   `responseId`   = `challenge[**8..15**]`      ⇒ **8** 字节
   `requestHmac`  = `data[**0..19**]`           ⇒ **20** 字节
   `responseHmac` = `data[**20..39**]`          ⇒ **20** 字节
   `decrypt`      = `data[**40..55**]`          ⇒ **16** 字节
   `encrypt`      = `data[**56..71**]`          ⇒ **16** 字节
        ↓
★★★★★ **⇒ 8 + 20 + 20 + 16 + 16 = 80 字节输出**
   ⇒ 而 `challenge`(16) + `data`(72) = **88 字节**生成
   ⇒ 其中 `challenge[0..7]` **未使用**（8 字节）
```

★★★ **⇒ 第 ③ 条的两个标签是**Demonware 的标准 KDF 标签**：**
```
"**CLIENTCHAL**"  ⇒ 客户端 challenge
"**BDDATA**"      ⇒ BD（Bedrock/Demonware）数据密钥
```

### ★★★★★ `expandKey` 的 HMAC 链式扩展（`Crypto.cpp`）

```cpp
ByteVector expandKey(
    const std::span<const std::uint8_t> secret,
    const std::string_view label,
    const std::size_t size)
{
    ByteVector output;
    ByteVector previous;
    std::uint8_t counter = 1;
    while (output.size() < size)
    {
        ByteVector input;
        input.insert(input.end(), **previous**.begin(), previous.end());   // ★ 上一块
        input.insert(input.end(), label.begin(), label.end());            // ★ 标签
        input.push_back(**counter++**);                                    // ★ 计数器
        previous = hmacSha1(input, secret);
        output.insert(output.end(), previous.begin(), previous.end());
    }
    output.resize(size);
    return output;
}
```

★★★★★ **⇒ 这是**标准的"HMAC 计数器链"KDF**：**
```
块 i 的输入 = **前一块的输出** || **标签** || **计数器 i**
块 i 的输出 = **HMAC-SHA1**(key=secret, data=输入)
        ↓
★★★ 然后拼接所有块,截断到 `size`
        ↓
★ 与 **HKDF-Expand** 结构相同（但用 HMAC-SHA1 而非 HMAC-Hash）
```

### ★★★ `SessionKeys` 的 5 个字段（`Crypto.hpp:10-17`）

```cpp
struct SessionKeys
{
    std::array<std::uint8_t, **8**>  responseId{};
    std::array<std::uint8_t, **20**> requestHmac{};
    std::array<std::uint8_t, **20**> responseHmac{};
    std::array<std::uint8_t, **16**> decrypt{};
    std::array<std::uint8_t, **16**> encrypt{};
};
```

### ★★★ 用 **Windows `BCrypt`** 而非 OpenSSL

```cpp
#include <bcrypt.h>
...
BCryptOpenAlgorithmProvider(&provider, algorithm, nullptr, flags)
BCryptCreateHash / BCryptHashData / BCryptFinishHash
BCryptOpenAlgorithmProvider(&provider, **BCRYPT_AES_ALGORITHM**, nullptr, 0)
BCryptSetProperty(provider, BCRYPT_CHAINING_MODE, **BCRYPT_CHAIN_MODE_CBC**, ...)
BCryptEncrypt / BCryptDecrypt
BCryptGenRandom(nullptr, ..., **BCRYPT_USE_SYSTEM_PREFERRED_RNG**)
```

★★★★★ **⇒ 与 `net_dtls_cod.cpp`（用 OpenSSL）形成**鲜明对比**：**
```
`net_dtls_cod.cpp`     ⇒ **OpenSSL**（`EVP_*` / `HMAC` / `EC_KEY`）
`Crypto.cpp`           ⇒ **Windows `BCrypt`**（`BCrypt*`）
        ↓
★★★ ⇒ 同一项目里**两套加密后端并存**
   ⇒ 可能原因：`Crypto.cpp` 更早（或作者偏好 BCrypt 的系统集成）
```

★ **⇒ 但**行为必须一致**（都是 SHA1/HMAC-SHA1/AES-128-CBC）。**

### ★★★ `aesCbc` 的严格前置条件

```cpp
if (key.size() != **16** || iv.size() != **16** || input.empty() || input.size() % **16** != 0)
    throw std::invalid_argument("AES-128-CBC requires a non-empty, block-aligned input and 16-byte key/IV");
```

★★★ **⇒ 四条：密钥 16 / IV 16 / 非空 / **块对齐**（`size % 16 == 0`）。**
**⇒ 即：**不做填充**,调用方必须自己补齐。**

★ **⇒ 与报告 101 的 `net_dtls_cod` 的 `set_padding(0)` **同一约定**（都不填充）。**

---

## 五、★★★★★ **`Auth3Protocol.hpp` 的极简接口**

```cpp
struct Auth3Result
{
    std::uint32_t titleId{};
    std::uint32_t authTask{};
    std::uint32_t ivSeed{};
    std::uint64_t userId{};
    std::string username;
    std::string json;      // ★ 完整的响应 JSON
};

class Auth3Protocol
{
public:
    explicit Auth3Protocol(AuthSession &session, PlayerIdentityStore *identityStore = nullptr);
    [[nodiscard]] Auth3Result authenticate(std::string_view requestJson);
    [[nodiscard]] static std::string httpResponse(std::string_view json);
private:
    AuthSession &session_;                    // ★ 引用（不拥有）
    PlayerIdentityStore *identityStore_{};    // ★ 指针（可空）
};
```

★★ **⇒ 两个依赖都是**非拥有**（`&` 与 `*`）⇒ 生命周期由调用方保证。**

---

## 六、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ **`AuthIdentity` 四默认值** | `titleId` **1004** / `userId` ★★★ **`0x1100001DEADC0DE`** / `username` `DefaultUsername` / `sessionKey` ★ **24 字节** |
| 2 | ★★★★★ **解开报告 083 的悬案** | 清单的种子目录 **`1100001DEADC0DE`** = `0x1100001DEADC0DE` 去 `0x` ✓ **代码级证实** |
| 3 | ★★★ `01100001` vs `1100001` | `0x**0**1100001DEADC0DE == 0x1100001DEADC0DE`（前导零无意义）⇒ **同一个 64 位整数** |
| 4 | ★★★★★ **更正报告 103** | `sessionKey` 是 **24 字节**,`makeTicket` 复制 24 字节到 ticket `[97, 120]` ⇒ **`97+24=121` 正好紧接 `'3','U','"'`** ✓ |
| 5 | ★★★★★ **`0x0110000100000000 \| parsed`** | 若 `parsed ≤ 0xFFFFFFFF` ⇒ **高 32 位填 `0x01100001`**（**平台前缀**） |
| 6 | ★★★ 完整 ID 结构 | `0x` **`01100001`**（平台前缀）+ **32 位用户 ID** |
| 7 | ★★ 环境变量 | **`OLMOD_PLATFORM_USER_ID`**（第 **14** 个） |
| 8 | ★★★★★ **10 个 Demonware 类型码** | **`0x01` Bool / `0x03` U8 / `0x06` U16 / `0x07` I32 / `0x08` U32 / `0x09` I64 / `0x0A` U64 / `0x10` String / `0x13` Blob / `0x6C` Array** |
| 9 | ★★★★★ **`TypeI32 = 0x07`** | = **`TypeU32 - 1`**；用于 **matchmaking 的 query-criterion**；★★★ **客户端逐值检查类型** ⇒ 用 U32 写有符号值**会失败**（"not a cosmetic difference"） |
| 10 | ★★★ 数组格式 | `Array(0x6C) + 元素类型(0x08) + 字节数(u32) + 个数(u32) + 数据`，且校验 **`byteSize == count * 4`** |
| 11 | ★★ `useDataTypes` 开关 | 可关闭类型前缀 ⇒ 支持裸数据流 |
| 12 | ★★ `require` 的 fail-closed | `valid_` 一旦 false ⇒ **永久 invalid** |
| 13 | ★★★★★ **密钥派生链** | `SHA1(transcript)` → `HMAC-SHA1(sessionKey24, 该哈希)` = `secret` → `expandKey(secret,"CLIENTCHAL",16)` / `expandKey(secret,"BDDATA",72)` |
| 14 | ★★★ 切分 | `responseId = challenge[8..15]`(8) / `requestHmac = data[0..19]`(20) / `responseHmac = data[20..39]`(20) / `decrypt = data[40..55]`(16) / `encrypt = data[56..71]`(16) |
| 15 | ★★ 未使用的 8 字节 | `challenge[0..7]` **未用** |
| 16 | ★★★★ **两个 KDF 标签** | **`"CLIENTCHAL"`** / **`"BDDATA"`** |
| 17 | ★★★★★ **`expandKey` = HMAC 计数器链** | 块 i 输入 = **前块输出 \|\| 标签 \|\| 计数器**；输出 = `HMAC-SHA1(secret, 输入)` ⇒ 与 **HKDF-Expand** 同构 |
| 18 | ★★★★★ **用 Windows `BCrypt`** | 与 `net_dtls_cod.cpp` 的 **OpenSSL** 形成**两套后端并存** |
| 19 | ★★ `aesCbc` 四前置 | 密钥 **16** / IV **16** / 非空 / **`size % 16 == 0`** ⇒ **不做填充**（与 101 的 `set_padding(0)` 同约定） |
| 20 | ★★ `Auth3Protocol` 的依赖 | 两个都是**非拥有**（`&` 与 `*`） |

---

## 七、结论

### 1. ★★★★★ **`0x1100001DEADC0DE` 被代码级证实为 `userId` 默认值**

```
报告 083 从清单推断"种子目录名 = platformUserId 去前导 0"
        ↓
★★★★★ 本报告：`AuthIdentity::userId{ 0x1100001DEADC0DEULL }` ✓
   ⇒ 且明确了 **`0x0110000100000000` 是平台前缀**
```

### 2. ★★★★★ **更正报告 103：`sessionKey` 是 24 字节**

```
`AuthIdentity::sessionKey` = **24 字节**（不是 16）
        ↓
★★★ `makeTicket` 复制 24 字节到 `[97, 120]` ⇒ `97+24 = 121` 正好紧接 `'3','U','"'`
   ⇒ **与 3DES 需要的 24 字节密钥完全吻合** ✓
   ⇒ 报告 103 的"待核对项"已解决
```

### 3. ★★★★★ **Demonware 的 10 个类型码,其中 `TypeI32 = 0x07` 有一个精确警告**

★ **⇒ "客户端逐值检查类型 ⇒ 用 U32 写有符号值不是外观差异"。**

### 4. ★★★★★ **`CLIENTCHAL` / `BDDATA` 密钥扩展是标准 HMAC 计数器链**

★ **⇒ 与 HKDF-Expand 同构。**

### 5. ★★★★ **同一项目里两套加密后端并存**（`net_dtls_cod` 用 OpenSSL,`Crypto` 用 BCrypt）

---

## 八、下一步

- `IdentityConfig.hpp`（108 行）/ `.cpp`（165 行）
- `CodolClientPatches.cpp`（**882 行**）+ `.hpp`（41）
- `Auth3TlsTransport.cpp`（311）/ `.hpp`（31）
- 然后 12 个 Service 实现（`MatchmakingService` 1,101 行 / `MarketplaceService` 1,099 行 / `StatsService` 875 行 等）
