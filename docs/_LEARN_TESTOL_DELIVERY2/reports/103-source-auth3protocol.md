# 学习报告 103（重开）— `backend\Demonware\Auth3Protocol.cpp`（12,998 B / 335 行）

**学习范围**：`backend\Demonware\Auth3Protocol.cpp` 全文
**性质**：全实测（**逐行读完**）
**★★★★★ 本报告收录六个重大发现**：①**128 字节 ticket 的完整布局（含 `0xEFBDADDE` magic）** ②**ticket 用 3DES-EDE3-CBC + 固定 IV `A68022CC34ACE697`** ③**两个 `codo_request` 解析器（task 28 / 32）** ④**`extra_data` 的 5 个字段** ⑤**两个彩蛋字符串** ⑥**`extended_data` 的 JWE 结构**

---

## 一、★★★★★ **128 字节 ticket 的完整布局**

### 1.1 ★★★★★ `makeTicket` 全文（第 142–160 行）

```cpp
ByteVector makeTicket(const AuthIdentity &identity)
{
    ByteVector ticket(128);
    writeU32(ticket, 0,   **0xEFBDADDE**);          // 偏移 0
    ticket[4] = 0;                                 // 偏移 4
    writeU32(ticket, 5,   identity.titleId);       // 偏移 5
    const auto now = std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());
    writeU32(ticket, 9,   static_cast<std::uint32_t>(now));  // 偏移 9
    writeU32(ticket, 13,  **0x7FFFFFFF**);          // 偏移 13
    writeU64(ticket, 17,  0);                      // 偏移 17
    writeU64(ticket, 25,  identity.userId);        // 偏移 25
    const auto usernameSize = std::min<std::size_t>(**17**, identity.username.size());
    std::copy_n(identity.username.begin(), usernameSize, ticket.begin() + **33**);  // 偏移 33
    std::copy(identity.sessionKey.begin(), identity.sessionKey.end(), ticket.begin() + **97**);  // 偏移 97
    ticket[**121**] = '3';
    ticket[**122**] = 'U';
    ticket[**123**] = '"';
    return ticket;
}
```

### ★★★★★ 完整的 128 字节布局

| 偏移 | 大小 | 值 | 说明 |
|---|---|---|---|
| **0** | 4 | ★★★ **`0xEFBDADDE`** | **magic** |
| **4** | 1 | **0** | 保留 |
| **5** | 4 | `titleId` | 标题 ID |
| **9** | 4 | **当前 Unix 时间戳** | 签发时间 |
| **13** | 4 | ★ **`0x7FFFFFFF`** | **INT32_MAX**（≈ 永不过期） |
| **17** | 8 | **0** | 保留（u64） |
| **25** | 8 | `userId` | 用户 ID（u64） |
| **33** | **17** | `username`（≤17 字节） | ★ 用户名 |
| **50** | **47** | **0**（未写） | 保留 |
| **97** | **16** | `sessionKey` | ★ 会话密钥 |
| **113** | **8** | **0**（未写） | 保留 |
| **121** | 1 | ★ **`'3'`** = `0x33` | |
| **122** | 1 | ★ **`'U'`** = `0x55` | |
| **123** | 1 | ★ **`'"'`** = `0x22` | |
| **124** | 4 | **0**（未写） | 保留 |

### ★★★★★ 与报告（`fake_auth_tls.py`）的**精确吻合**

```
报告 044–046（`fake_auth_tls.py`）记：
  ticket 128B 布局：magic **`0xEFBDADDE`** at +0,
  `ticket[k] = (k*31+7)&0xFF`,
  **username at `+0x21`(33) 17 bytes**,
  sessionKey at **`0x61`(97)**,
  **`'3','U','"'` at `0x79`(121)**
        ↓
★★★★★ 本报告（C++ 实现）：
  magic **`0xEFBDADDE`** ✓
  username at **33**（= `0x21`）**17 字节** ✓
  sessionKey at **97**（= `0x61`）✓
  **`'3','U','"'` at 121**（= `0x79`）✓
        ↓
★★★ ⇒ **Python 与 C++ 两份实现逐字段一致**
```

★★ **⇒ 唯一差异：C++ 版**没有**填 `ticket[k] = (k*31+7)&0xFF` 的模式,而是**保留零**。**
**⇒ 即：Python 版是**更完整的还原**（填了默认模式）,C++ 版只填了必要字段。**

### ★★★ `0x7FFFFFFF` 作为"永不过期"

★ **⇒ 与报告 078 的 `[tournament14] end_time = 2147483647`（同一个 `INT32_MAX`）**同一手法**。**
**⇒ 这是一个**跨文件的"永不过期"哨兵**。**

---

## 二、★★★★★ **ticket 用 3DES-EDE3-CBC + 固定 IV**

### 2.1 ★★★★★ 完整实现（第 162–191 行）

```cpp
ByteVector encryptTicket(
    const std::span<const std::uint8_t> ticket,
    const std::span<const std::uint8_t> sessionKey)
{
    EVP_CIPHER_CTX *context = EVP_CIPHER_CTX_new();
    ByteVector output(ticket.size() + EVP_MAX_BLOCK_LENGTH);
    const auto initialized = EVP_EncryptInit_ex(
        context, **EVP_des_ede3_cbc()**, nullptr,
        sessionKey.data(), **CodolTicketIv.data()**);
    const auto padding = EVP_CIPHER_CTX_set_padding(context, **0**);   // ★ 无填充
    const auto updated = EVP_EncryptUpdate(context, output.data(), &first,
        ticket.data(), static_cast<int>(ticket.size()));
    const auto finished = EVP_EncryptFinal_ex(context, output.data() + first, &final);
    ...
}
```

### ★★★★★ 三个精确参数

```
① 算法 = **`EVP_des_ede3_cbc()`** = **3DES-EDE3-CBC**
② 密钥 = **`sessionKey`**（16 字节?但 3DES 需要 **24** 字节!）
③ IV   = **`CodolTicketIv`** = `{ 0xA6, 0x80, 0x22, 0xCC, 0x34, 0xAC, 0xE6, 0x97 }`（**8 字节**）
④ 填充 = **关闭**（`set_padding(0)`）
```

★★★ **⇒ 第 ② 条值得注意：3DES 需要 **24 字节**密钥,而 `sessionKey` 在 ticket 里是 **16 字节**。**
**⇒ 说明 `sessionKey` 实际可能是 24 字节（ticket 里只放了前 16）,或 OpenSSL 会补零。**
**⇒ 记录为**待核对项**。**

### ★★★ 固定 IV（第 23–25 行）

```cpp
constexpr std::array<std::uint8_t, 8> CodolTicketIv{
    0xA6, 0x80, 0x22, 0xCC, 0x34, 0xAC, 0xE6, 0x97,
};
```

★★★ **⇒ IV 是**硬编码的常量**,不是随机的。**
**⇒ 8 字节 = 3DES 块大小 ✓**

★ **⇒ 这意味着**同一 sessionKey + 同一 ticket 内容 ⇒ 密文相同**（确定性加密）。**

---

## 三、★★★★★ **两个 `codo_request` 解析器（task 28 / 32）**

### 3.1 ★★★ `consumeTask28CodoRequest`（第 199–213 行）

```cpp
void consumeTask28CodoRequest(const Json &extra, AuthIdentity &identity)
{
    const auto encoded = valueString(extra, "codo_request");
    const auto decoded = base64Decode(encoded);
    if (decoded.size() < **56**) return;

    identity.userId = readU64(decoded, **6**);                    // 偏移 6
    const auto name = std::span(decoded).subspan(**14**, **16**); // 偏移 14,16 字节
    const auto terminator = std::find(name.begin(), name.end(), std::uint8_t{});
    identity.username.assign(...);
    std::copy_n(decoded.begin() + **32**, identity.sessionKey.size(), identity.sessionKey.begin());  // 偏移 32
}
```

### ★★★★★ task 28 的 `codo_request` 布局

| 偏移 | 大小 | 字段 |
|---|---|---|
| **0** | 6 | 未使用 |
| **6** | 8 | ★ `userId`（u64 LE） |
| **14** | **16** | ★ `username`（NUL 结尾,最多 16） |
| **30** | 2 | 未使用 |
| **32** | **16** | ★ `sessionKey` |
| **48** | 8 | 未使用 |
| **56** | — | 最小长度 |

★★ **⇒ `if (decoded.size() < 56) return;` ⇒ 最小 **56 字节**。**

### ★★★ `consumeTask32CodoRequest`（第 215–242 行）

```cpp
void consumeTask32CodoRequest(const Json &extra, AuthIdentity &identity)
{
    const auto decoded = base64Decode(valueString(extra, "codo_request"));
    const auto bitCount = parseU32(
        valueString(extra, "codo_request_size_bits"), **10**,
        static_cast<std::uint32_t>(decoded.size() * 8));
    BitReader bits(decoded, bitCount);
    std::uint32_t typed{};
    if (!bits.read(**1**, typed)) return;                        // ★ 1 位 typed

    std::uint32_t length{};
    if (typed != 0)
    {
        std::uint32_t type{};
        if (!bits.read(**5**, type) || type == 20 || type != 6) return;   // ★ 5 位 type,必须 = 6
    }
    if (!bits.read(**16**, length) || length > decoded.size()) return;   // ★ 16 位长度

    ByteVector value(length);
    if (!bits.readBytes(value)) return;
    identity.sessionKey.fill(0);
    std::copy_n(value.begin(), std::min(value.size(), identity.sessionKey.size()), identity.sessionKey.begin());
}
```

### ★★★★★ task 32 的位流格式

```
① **1 位** `typed` 标志
② 若 `typed != 0` ⇒ **5 位** `type`,且**必须 = 6**（且 `!= 20`）
③ **16 位** `length`（**位**数?或字节数?—— 代码按字节用 `readBytes(value)`）
④ `length` 个**字节** ⇒ 就是 `sessionKey`
        ↓
★★★ 注意：`length` 被当作**字节数**用（`ByteVector value(length)` + `readBytes`）
   ⇒ 但位流读取 ⇒ 实际消耗 `length * 8` 位
```

★★ **⇒ `codo_request_size_bits` 是**独立参数**（十进制,默认 `decoded.size() * 8`）。**
**⇒ 即：客户端可以声明**有效位数少于实际字节数**。**

### ★★★ `BitReader` 的 LSB-first 位序（第 66–104 行）

```cpp
const auto bit = (data_[(position_ + index) / 8] >> ((position_ + index) % 8)) & 1;
value |= static_cast<std::uint32_t>(bit) << index;
```

★★★ **⇒ 位序是 **LSB-first**（字节内从低位开始,值也是从低位累加）。**
**⇒ 与报告 099 的 `ClientCommandReader::readBits` **完全相同的位序** ✓**

---

## 四、★★★★★ **`extra_data` 的 5 个字段与两个彩蛋**

### 4.1 ★★★★★ 完整构造（第 283–299 行）

```cpp
const std::string registerData = "**Shippo fuute, mofu-mofu!**";
const std::string codoId = "**Hedgehogscience0**";
constexpr std::string_view extendedData =
    "eyJfX3YiOjEsImFsZyI6IlJTQS1PQUVQIiwiZW5jIjoiQTEyOENCQy1IUzI1NiIsImtpZCI6InVtYl8xIn0=.AAA…";

Json extraData{
    { "encrypted_register_codoid_data", base64Encode(registerData) },
    { "encrypted_codoid",               base64Encode(codoId) },
    { "extended_data",                  extendedData },
    { "time_to_live",                   9999 },
    { "username",                       base64Encode(identity.username) },
};
```

### ★★★★★ 两个彩蛋字符串

| 字段 | **明文值** | 语义 |
|---|---|---|
| **`encrypted_register_codoid_data`** | ★★★ **`"Shippo fuute, mofu-mofu!"`** | ★ 日式可爱语（"しっぽ ふーて、もふもふ！"≈"尾巴呼—，毛茸茸！"） |
| **`encrypted_codoid`** | ★★★ **`"Hedgehogscience0"`** | ★ 刺猬科学 0 |

★★★ **⇒ 两个字段名都叫 `encrypted_*`,但内容是**明文 base64**（不是真加密）⇒ 是**占位/彩蛋**。**

★★ **⇒ `Hedgehogscience0` 的 `0` 后缀 ⇒ 可能是**账号名 + 序号**的格式。**

### ★★★★★ `extended_data` 的 JWE 结构（base64 解码）

```
`eyJfX3YiOjEsImFsZyI6IlJTQS1PQUVQIiwiZW5jIjoiQTEyOENCQy1IUzI1NiIsImtpZCI6InVtYl8xIn0=`
        ↓ base64 解码
`{"__v":1,"alg":"RSA-OAEP","enc":"A128CBC-HS256","kid":"umb_1"}`
        ↓
★★★★★ ⇒ **这是一个 JWE 头部**：
  `__v` = **1**（版本）
  `alg` = **`RSA-OAEP`**（密钥加密算法）
  `enc` = **`A128CBC-HS256`**（内容加密：AES-128-CBC + HMAC-SHA256）
  `kid` = **`umb_1`**（密钥 ID）
```

★★★ **⇒ 完整的 JWE 五段结构（用 `.` 分隔）：**
```
段 1：`{"__v":1,"alg":"RSA-OAEP","enc":"A128CBC-HS256","kid":"umb_1"}`
段 2：**全 A 的 base64**（≈ 256 字节零 ⇒ 加密的 CEK）
段 3：**全 A 的 base64**（≈ 16 字节零 ⇒ IV）
段 4：`W0VuY3J5cHRlZCBkYXRhLi4gbXVjaCBzZWNyZXQuLl0=` ⇒ ★★★ 解码 = **`[Encrypted data.. much secret..]`**
段 5：**全 A 的 base64**（认证标签）
        ↓
★★★★★ ⇒ **段 4 是一个**字面彩蛋**："`[Encrypted data.. much secret..]`"**
```

★★ **⇒ 整个 `extended_data` 是**一个格式完整但内容全是占位的 JWE**。**

### ★★★ 另外三个字段

| 字段 | 值 |
|---|---|
| **`time_to_live`** | ★ **9999** |
| **`username`** | ★★ **base64(明文用户名)** ⇒ 与报告 044 的"名字真正载体是 `extra_data.username`"**完全吻合** ✓ |

---

## 五、★★★★★ **响应的 7 个字段与 `auth_task + 1`**

### 5.1 ★★★★★ 完整构造（第 300–313 行）

```cpp
Json response{
    { "client_ticket", ticket64 },                          // ★ 同一个 ticket
    { "server_ticket", ticket64 },                          // ★ 同一个 ticket
    { "code", "**700**" },
    { "extra_data", extraData.dump() },                     // ★ 注意：dump() 成字符串
    { "auth_task", std::to_string(**authTask + 1**) },      // ★★ +1
    { "identity", <requestIdentity 的十六进制> },
    { "iv_seed", std::to_string(ivSeed) },
};
```

### ★★★★★ 三个精确观察

```
① ★★★ **`client_ticket` 与 `server_ticket` 是**同一个** ticket**
   ⇒ 即：服务端不需要独立生成 server ticket
        ↓
② ★★★ **`auth_task = authTask + 1`** ⇒ **每次请求推进一个 task**
   ⇒ 与报告 044 的 `TASK_MAP = {0:1, 10:11, 12:13, 24:25, 26:27, **32:57**}`
     **不完全一致**（那里有跳跃）
        ↓
★★★ ⇒ 可能：`TASK_MAP` 是**客户端发起**的映射,而这里是**服务端响应**的简单 +1
   ⇒ ★ **未完全核对,记录为待验证**
        ↓
③ ★★★ **`extra_data` 是 `extraData.dump()` ⇒ 一个**JSON 字符串**
   ⇒ 即：响应里的 `extra_data` 是**嵌套的 JSON 字符串**（不是对象）
   ⇒ ★ 与报告 044 的"response 有 3 层嵌套,fields 在顶层与 data 内重复"**部分吻合**
```

### ★★★ `identity` 的十六进制转换（第 306–311 行）

```cpp
{ "identity", [&] {
    std::array<char, 9> buffer{};
    const auto converted = std::to_chars(
        buffer.data(), buffer.data() + buffer.size(), **requestIdentity**, **16**);
    return std::string(buffer.data(), converted.ptr);
}() }
```

★★ **⇒ `identity` 是**十六进制小写**（`to_chars` 基数 16 默认小写）。**
**⇒ 而 `requestIdentity` 是**从请求里解析的**（`parseU32(valueString(request, "identity"), **16**, 0)`）。**
**⇒ 即：**原样回显（但重新格式化成十六进制）。**

★★ **⇒ 缓冲区是 **9** 字节 ⇒ 最多 8 个十六进制字符 + NUL ⇒ 即 **32 位值**。**

---

## 六、★★★★★ **`authenticate` 的完整流程**

### 6.1 ★★★ 七步（第 254–323 行）

```
① `Json::parse(requestJson, nullptr, **false**)` ⇒ 失败返回 `is_object() == false` ⇒ 抛异常
        ↓
② `identity = session_.snapshot()` ⇒ 快照当前会话
   `configuredUsername = identity.username` ⇒ ★ 保存原用户名
        ↓
③ 从请求解析 4 个字段：`title_id`(10) / `auth_task`(10) / `iv_seed`(10) / `identity`(**16**)
        ↓
④ `extra = extraData(request)` ⇒ ★ 把 `extra_data` **字符串**解析成 JSON 对象
        ↓
⑤ `authTask == 28` ⇒ `consumeTask28CodoRequest`
   `authTask == 32` ⇒ `consumeTask32CodoRequest`
        ↓
⑥ ★★ `identity.username = identityStore_
       ? identityStore_->resolveDisplayName(titleId, userId)
       : configuredUsername`
   ⇒ ★★★ **显示名从 `PlayerIdentityStore` 解析,不是从请求**
        ↓
⑦ `session_.update(identity)`
   `ticket = makeTicket(identity)`
   若 `authTask == 28` ⇒ **`ticket = encryptTicket(ticket, sessionKey)`**
   校验 `ticket.size() == **128**`（否则抛 "Auth3 ticket must be exactly 128 bytes"）
```

★★★★★ **⇒ 第 ⑦ 条是关键：**只有 task 28 加密 ticket**,task 32 不加密。**
**⇒ 这与报告 044 的 `TASK_MAP` 里 28 与 32 的处理**不同** ⇒ 记录为**精确差异**。**

### ★★★ `base64Decode` 的 URL-safe 支持（第 119–140 行）

```cpp
std::replace(value.begin(), value.end(), **'-'**, **'+'**);
std::replace(value.begin(), value.end(), **'_'**, **'/'**);
while (value.size() % 4 != 0) value.push_back('=');
```

★★★ **⇒ 支持 **URL-safe base64**（`-`/`_` 替换 `+`/`/`）+ 自动补 `=`。**

### ★★★ `base64Encode` 用 OpenSSL

```cpp
const auto size = EVP_EncodeBlock(...);
```

★ **⇒ 标准 base64（`+`/`/`,不是 URL-safe）。**

### ★★★ HTTP 响应（第 325–333 行）

```cpp
std::string response = "HTTP/1.1 200 OK\r\n";
response += "Connection: **keep-alive**\r\n";
response += "Content-Type: application/json\r\n";
response += "Content-Length: " + std::to_string(json.size()) + "\r\n\r\n";
```

★★ **⇒ `Connection: keep-alive` ⇒ 长连接（Auth3 复用同一 TCP）。**

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **ticket magic** | **`0xEFBDADDE`**（偏移 0） |
| 2 | ★★★★★ **128 字节布局** | magic(4) + 0(1) + `titleId`(4@5) + **时间戳**(4@9) + **`0x7FFFFFFF`**(4@13) + 0(8@17) + `userId`(8@25) + **`username`(17@33)** + 0(47@50) + **`sessionKey`(16@97)** + 0(8@113) + **`'3','U','"'`(3@121)** + 0(4@124) |
| 3 | ★★★★★ **与 `fake_auth_tls.py` 吻合** | magic / username@**33**(`0x21`) 17B / sessionKey@**97**(`0x61`) / `'3','U','"'`@**121**(`0x79`) **逐字段一致** ✓ |
| 4 | ★★ 唯一差异 | C++ 版**未填** `ticket[k]=(k*31+7)&0xFF` 的默认模式（保留零） |
| 5 | ★★★ `0x7FFFFFFF` | **INT32_MAX** ⇒ "永不过期"（与 078 的 `end_time=2147483647` 同手法） |
| 6 | ★★★★★ **ticket 加密** | **`EVP_des_ede3_cbc()`**（3DES-EDE3-CBC）+ **固定 IV `A6 80 22 CC 34 AC E6 97`** + **`set_padding(0)`** |
| 7 | ★★ 待核对 | 3DES 需 **24** 字节密钥,而 ticket 里 `sessionKey` 只 **16** 字节 |
| 8 | ★★★ 确定性加密 | 固定 IV ⇒ **同一 key + 同一内容 ⇒ 密文相同** |
| 9 | ★★★★★ **task 28 的 `codo_request`** | 最小 **56** 字节；`userId`@**6**(u64) / `username`@**14**(16B,NUL 结尾) / `sessionKey`@**32**(16B) |
| 10 | ★★★★★ **task 32 的位流** | **1 位** typed ⇒ 若非 0 则 **5 位** type(**必须=6 且 ≠20**) ⇒ **16 位** length ⇒ `length` 字节 = `sessionKey` |
| 11 | ★★ `codo_request_size_bits` | 独立十进制参数（默认 `decoded.size()*8`）⇒ 客户端可声明**有效位数少于实际** |
| 12 | ★★★ `BitReader` 位序 | **LSB-first** ⇒ 与报告 099 的 `ClientCommandReader` **完全相同** ✓ |
| 13 | ★★★★★ **两个彩蛋** | `registerData = "**Shippo fuute, mofu-mofu!**"` / `codoId = "**Hedgehogscience0**"` |
| 14 | ★★★ 字段名与内容不符 | 两个 `encrypted_*` 字段里是**明文 base64**（不是真加密） |
| 15 | ★★★★★ **`extended_data` 是 JWE** | 头 = `{"__v":1,"alg":"**RSA-OAEP**","enc":"**A128CBC-HS256**","kid":"**umb_1**"}` |
| 16 | ★★★★★ **JWE 段 4 的彩蛋** | `W0VuY3J5cHRlZCBkYXRhLi4gbXVjaCBzZWNyZXQuLl0=` ⇒ **`[Encrypted data.. much secret..]`** |
| 17 | ★★ `time_to_live` | **9999** |
| 18 | ★★★★ **`extra_data.username`** | **base64(明文用户名)** ✓ 与报告 044 的"名字真正载体"**完全吻合** |
| 19 | ★★★ **响应 7 字段** | `client_ticket` / `server_ticket`（★ **同一个**）/ `code="700"` / `extra_data`（★ **dump() 成字符串**）/ `auth_task=authTask+1` / `identity`(hex) / `iv_seed` |
| 20 | ★★★★ **只有 task 28 加密 ticket** | task 32 **不加密** ⇒ 与报告 044 的 `TASK_MAP` 处理**不同**（记录为精确差异） |
| 21 | ★★★ **显示名来源** | 从 **`PlayerIdentityStore::resolveDisplayName(titleId, userId)`**,**不是**从请求 |
| 22 | ★★ `identity` 回显 | `to_chars(..., 16)` ⇒ **十六进制小写**,缓冲区 **9** 字节 ⇒ 32 位值 |
| 23 | ★★★ `base64Decode` | 支持 **URL-safe**（`-`/`_`）+ 自动补 `=` |
| 24 | ★★ HTTP 头 | `Connection: **keep-alive**` + `Content-Type: application/json` |

---

## 八、结论

### 1. ★★★★★ **128 字节 ticket 的布局与 Python 版逐字段一致**

```
magic **`0xEFBDADDE`** / username@**33** 17B / sessionKey@**97** / `'3','U','"'`@**121**
        ↓
★★★ ⇒ **两份独立实现互相印证** ✓
   ⇒ 唯一差异：C++ 版未填 `(k*31+7)&0xFF` 的默认模式
```

### 2. ★★★★★ **ticket 用 3DES-EDE3-CBC + 固定 IV `A68022CC34ACE697`,且只有 task 28 加密**

### 3. ★★★★★ **`extended_data` 是一个**格式完整但内容全是彩蛋的 JWE**

```
头：`{"__v":1,"alg":"RSA-OAEP","enc":"A128CBC-HS256","kid":"umb_1"}`
段 4：**`[Encrypted data.. much secret..]`**
        ↓
★ 且 `registerData = "Shippo fuute, mofu-mofu!"` / `codoId = "Hedgehogscience0"`
```

### 4. ★★★★ **`extra_data.username` 是 base64 明文用户名**（与报告 044 完全吻合）

### 5. ★★★★ **两个 `codo_request` 解析器**（task 28 定长 / task 32 位流）

★ **⇒ task 32 的位序与 netchan 的 usercmd 读取器**完全相同（LSB-first）。**

### 6. ★★★ **显示名来自 `PlayerIdentityStore`,不是请求**

### 7. ★★★ **`0x7FFFFFFF` 是跨文件的"永不过期"哨兵**（与 078 的 `INT32_MAX` 同）

---

## 九、下一步

- `Auth3Protocol.hpp`（29 行）+ **`Auth3TlsTransport.cpp`（311 行）** + `.hpp`（31 行）
- **`Auth3ClientPatches.cpp`（241 行）** —— 对应报告 090 的 "three Auth3 client patches"
- `AuthSession` / `ByteBuffer` / `Crypto` / `IdentityConfig`
