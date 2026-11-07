# 学习报告 097（重开）— `shared\DedicatedControl.cpp`（36,106 B / 894 行）

**学习范围**：`shared\DedicatedControl.cpp` 全文（**894 行逐行读完**）
**性质**：全实测（**`shared\` 10 个文件至此全部完成**）
**★★★★★ 本报告收录五个重大发现**：①**4 个 magic 与 24 字节帧头（含 FNV-1a 校验）** ②**`GameplayStatus` 的 v1–v5 五级向后兼容解码** ③**回环 vs `INADDR_ANY` 的安全判据** ④**`userId = 0` 的真实语义** ⑤**`shared\` 完整收官账**

---

## 一、★★★★★ **4 个 magic 与 24 字节帧头**

### 1.1 ★★★★★ 四个 magic（第 22–27 行，逐字）

```cpp
constexpr std::uint32_t FrameMagic          = 0x43444C4F; // **OLDC**
constexpr std::uint32_t EndpointStatusMagic = 0x4553444F; // **ODSE**
constexpr std::uint32_t GameplayStatusMagic = 0x5352444F; // **ODRS**
constexpr std::uint32_t NoclipRequestMagic  = 0x434E444F; // **ODNC**
constexpr std::size_t RequestHeaderSize  = 24;
constexpr std::size_t ResponseHeaderSize = 24;
```

### ★★★★★ 四个 magic 的 ASCII 解码（小端）

| 常量 | 十六进制 | 小端字节 | **ASCII** |
|---|---|---|---|
| **`FrameMagic`** | `0x43444C4F` | `4F 4C 44 43` | ★ **`OLDC`** |
| **`EndpointStatusMagic`** | `0x4553444F` | `4F 44 53 45` | ★ **`ODSE`** |
| **`GameplayStatusMagic`** | `0x5352444F` | `4F 44 52 53` | ★ **`ODRS`** |
| **`NoclipRequestMagic`** | `0x434E444F` | `4F 44 4E 43` | ★ **`ODNC`** |

★★★ **⇒ 命名规律：`OL` = Ol-mod,`D` = Dedicated,第三个字母是**功能**：**
```
`OL` + `D` + `C`  ⇒ **OLDC** = Ol-mod Dedicated **C**ontrol（帧）
`OD` + `S` + `E`  ⇒ **ODSE** = Ol-mod **D**edicated **S**tatus **E**ndpoint
`OD` + `R` + `S`  ⇒ **ODRS** = Ol-mod **D**edicated **R**untime **S**tatus
`OD` + `N` + `C`  ⇒ **ODNC** = Ol-mod **D**edicated **N**o**c**lip
        ↓
★ 与报告 093 的 `OLDS`（`0x53444C4F` = **O**l-mod **L**oadout **D**edicated **S**ession）
   ⇒ **同一个 `OL`/`OD` 前缀家族**
```

### ★★★★★ 24 字节帧头布局（`encodeRequest`，第 134–149 行）

```cpp
appendU32(output, FrameMagic);                            // 偏移 0,  4 字节
appendU16(output, ProtocolVersion);                       // 偏移 4,  2 字节
appendU16(output, static_cast<std::uint16_t>(message.type)); // 偏移 6,  2 字节
appendU32(output, static_cast<std::uint32_t>(payload.size())); // 偏移 8,  4 字节
appendU64(output, message.requestId);                     // 偏移 12, 8 字节
appendU32(output, checksum(payload));                     // 偏移 20, 4 字节
        ↓
★★★ **总计 = 4 + 2 + 2 + 4 + 8 + 4 = 24 字节** ✓
```

| 偏移 | 大小 | 字段 |
|---|---|---|
| **0** | 4 | `FrameMagic`（`OLDC`） |
| **4** | 2 | `ProtocolVersion`（= **2**） |
| **6** | 2 | `message.type` / `response.status` |
| **8** | 4 | `payloadSize` |
| **12** | 8 | `requestId` |
| **20** | 4 | **`checksum(payload)`** |

★★★ **⇒ **请求与响应**的帧头**布局完全相同**（都 24 字节），只有偏移 6 的语义不同：**
```
请求的偏移 6 ⇒ **`MessageType`**（1..20）
响应的偏移 6 ⇒ **`ResponseStatus`**（0..3）
```

### ★★★★★ `checksum` = **FNV-1a 32 位**（第 89–98 行，逐字）

```cpp
std::uint32_t checksum(const std::span<const std::uint8_t> input)
{
    std::uint32_t result = 2166136261u;      // ★ 0x811C9DC5 = FNV offset basis
    for (const auto value : input)
    {
        result ^= value;
        result *= 16777619u;                 // ★ 0x01000193 = FNV prime
    }
    return result;
}
```

★★★★★ **⇒ 这是**教科书级的 FNV-1a 32 位**：**
```
offset basis = **2166136261** = `0x811C9DC5`
prime        = **16777619**   = `0x01000193`
算法         = `result ^= byte; result *= prime;`  ← **FNV-1a**（先异或后乘）
```

★ **⇒ 注意与 FNV-1（先乘后异或）的区别：这里是 **1a**。**

★★ **⇒ 校验只覆盖 **payload**,不覆盖头（头里的 `payloadSize` 本身没被校验）。**

---

## 二、★★★★★ **服务端：回环 vs `INADDR_ANY` 的安全判据**

### 2.1 ★★★★★ 绑定逻辑（第 223–233 行，逐字）

```cpp
// Loopback is the default because a control listener reachable from
// the network is a decision, never an accident. hostIsRemote() asks the
// only question that matters: is this stack being addressed over a
// network at all? If it is, every control listener has to accept from
// there, because the room owner, the dedicated and each client's bridge
// are no longer guaranteed to share a machine.
sockaddr_in address{};
address.sin_family = AF_INET;
address.sin_addr.s_addr = htonl(
    hostIsRemote() ? INADDR_ANY : INADDR_LOOPBACK);
address.sin_port = htons(port);
```

★★★★★ **⇒ 一个精确的安全设计：**
```
`hostIsRemote()` 为 **false** ⇒ 绑 **`INADDR_LOOPBACK`**（只本机）
`hostIsRemote()` 为 **true**  ⇒ 绑 **`INADDR_ANY`**（所有接口）
        ↓
★★★ 理由（逐字）："a control listener **reachable from the network is a decision,
 **never an accident**"
        ↓
★★★★★ ⇒ 这是**"默认最小暴露面"**的明确实现
```

★★ **⇒ 与报告 095 的 `OLMOD_HOST_ADDRESS` 未设 = `127.0.0.1` **完全一致**（同一哲学）。**

### 2.2 ★★★ `listen(listener, 4)` 的 backlog

```cpp
listen(listener, 4) != 0
```

★ **⇒ backlog = **4**（很小,因为控制通道是**低频**的）。**

### 2.3 ★★★ 每个连接的超时（第 274–278 行）

```cpp
DWORD timeout = 500;
setsockopt(client, SOL_SOCKET, SO_RCVTIMEO, ...);
setsockopt(client, SOL_SOCKET, SO_SNDTIMEO, ...);
```

★ **⇒ 收/发超时各 **500 ms**（与报告 094 的 `submit()` 默认超时一致）。**

### 2.4 ★★★★★ 服务端的**六重校验**（第 287–293 行）

```cpp
if (readU32(header, 0) == FrameMagic &&                      // ① magic
    readU16(header, 4) == ProtocolVersion &&                  // ② 版本
    payloadSize <= MaximumPayloadSize)                        // ③ 大小上限
{
    std::vector<std::uint8_t> payload(payloadSize);
    if (receiveAll(client, payload) &&
        checksum(payload) == readU32(header, 20))              // ④ 校验和
    { ... }
}
```

★★★ **⇒ 四重（加上 `receiveAll` 成功）：**
```
① `magic == FrameMagic`
② `version == ProtocolVersion`（**严格相等,不是范围**）
③ `payloadSize <= 16,384`
④ `checksum(payload) == header[20]`
```

### 2.5 ★★★★★ 两处 `catch (...)`（第 305–317 行）

```cpp
try
{
    response = state->handler(message);
    if (response.payload.size() > MaximumPayloadSize)
    {
        response = { .status = ResponseStatus::Rejected };
    }
}
catch (...)
{
    response = { .status = ResponseStatus::Rejected };
}
```

★★★ **⇒ 两条保护：**
```
① handler 返回的 payload **超过 16,384** ⇒ 改成 `Rejected`
② handler **抛任何异常** ⇒ 改成 `Rejected`（**catch(...) 兜住一切**）
        ↓
★★★ ⇒ **控制通道绝不会因为一个 handler 崩溃**
```

★ **⇒ 与报告 076 的 `war.lua`/`conf.lua` 的 FAIL-SOFT `pcall` **同一哲学**（但这里是 C++ 的 `catch(...)`）。**

### 2.6 ★★★ `peerIpv4` 由传输层填充（第 303 行）

```cpp
.peerIpv4 = ntohl(peer.sin_addr.s_addr),
```

★★ **⇒ 与报告 094 的注释完全一致："**TRANSPORT-SUPPLIED AND NEVER ENCODED**"。**

---

## 三、★★★★★ **`GameplayStatus` 的 v1–v5 五级向后兼容解码**

### 3.1 ★★★★★ 五个 schema 的**精确字节数**（第 682–692 行，逐字）

```cpp
constexpr std::size_t Schema1FixedClientSize = 6 * sizeof(std::uint32_t) + 3 * 2 * sizeof(std::uint32_t);
constexpr std::size_t Schema2TransportSize = 68;
constexpr std::size_t Schema3GameplayDiagnosticsSize = 40;
constexpr std::size_t Schema4ClientThinkDiagnosticsSize = 56;
constexpr std::size_t Schema5LocationalDiagnosticsSize = 84;
const auto fixedClientSize = Schema1FixedClientSize +
    (schema >= 2 ? Schema2TransportSize : 0) +
    (schema >= 3 ? Schema3GameplayDiagnosticsSize : 0) +
    (schema >= 4 ? Schema4ClientThinkDiagnosticsSize : 0) +
    (schema >= 5 ? Schema5LocationalDiagnosticsSize : 0);
```

### ★★★★★ 完整的 schema 累加表

| schema | 增量 | **累计每客户端字节数** |
|---|---|---|
| **v1** | `6×4 + 3×2×4 = 24 + 24` | ★ **48** |
| **v2** | **+68** | **116** |
| **v3** | **+40** | **156** |
| **v4** | **+56** | **212** |
| **v5** | **+84** | ★★ **296** |

★★★ **⇒ `Schema1FixedClientSize` 的算式**：`6 × sizeof(uint32) + 3 × 2 × sizeof(uint32)` = **24 + 24 = 48**。
**⇒ 即 v1 是 6 个 u32（24 字节）+ 3 组各 2 个 u32（24 字节）⇒ 但代码只读 5 个 u32（20 字节）+ objectives（24 字节）
⇒ 说明 v1 的 "6 个 u32" 里有 1 个是 `peerPort`+`reserved` 的 u32（在 v2 里读）。**

### 3.2 ★★★★★ 版本范围检查（第 653–658 行）

```cpp
if (!canRead(input, 0, HeaderSize) ||
    readU32(input, 0) != GameplayStatusMagic ||
    (readU16(input, 4) < 1 || readU16(input, 4) > 5))
{
    return std::nullopt;
}
```

★★★ **⇒ **接受 v1–v5**（范围检查）,而帧头层要求 **v2 严格相等**。**
**⇒ 即：**`GameplayStatus` 的 payload 内部还有**自己的 schema 号**（`readU16(input, 4)`）。**

### 3.3 ★★★★★ `GameplayStatus` 的完整头（第 652 行）

```cpp
constexpr std::size_t HeaderSize = 12 + 18 * sizeof(std::uint32_t);
        ↓
★★★ = **12 + 72 = 84 字节**
        ↓
布局：
  偏移 0   u32  `GameplayStatusMagic`（`ODRS`）
  偏移 4   u16  **schema**（1..5）
  偏移 6   u16  `clientCount`
  偏移 8   u32  `serverTime`
  偏移 12  18 × u32  **SD 状态**（72 字节）
        ↓
★★★ 总计 = **84 字节** ✓
```

### 3.4 ★★★★★ **三个 payload 的精确大小**

| payload | 头 | 说明 |
|---|---|---|
| **`EndpointStatus`** | ★ **8 字节**（固定） | `magic(4) + 版本 1(1) + flags(1) + port(2)` |
| **`NoclipRequest`** | ★ **18 字节**（固定） | `magic(4) + 版本 1(1) + userId(8) + enabled(1) + holdMs(4)` |
| **`GameplayStatus`** | **84 字节** + 每客户端 **48–296** 字节 + 命令列表 | 变长 |

★★★ **⇒ `EndpointStatus` 的位域（第 449–455 行）：**
```cpp
payload[4] = 1;                        // ★ 版本
payload[5] = (sessionConfigured ? 1 : 0) |
             (enabled ? 2 : 0) |
             (bound ? 4 : 0);          // ★ 三个布尔位
payload[6..7] = port (u16 LE)
```
**⇒ 且解码时校验 `(bytes[5] & ~7) != 0` ⇒ **只允许低 3 位**（fail-closed）。**

★★ **⇒ `NoclipRequest` 的 `bytes[13] > 1` ⇒ 拒绝 ⇒ **`enabled` 必须是 0 或 1**。**

---

## 四、★★★★★ **`userId = 0` 的真实语义**（第 523–527 行，逐字）

```cpp
// ZERO IS A REAL VALUE HERE and means "resolve me by the address I am
// sending from". That is the CLIENT's case: it knows its platform user
// id and the server knows the xuid out.exe sent in its connect string,
// and those are different numbers. A non-zero id is the TOOL's case --
// name one slot exactly, and fail rather than fall back.
```

★★★★★ **⇒ 一个极其重要的双语义：**
```
**`userId = 0`** ⇒ **"按我发送的地址解析"**（**CLIENT 的情况**）
        ↓
★★★ 因为：客户端知道**平台 user id**,而服务端知道
   **`out.exe` 在其 connect string 里发的 xuid**
   ⇒ ★★★ **这两个是不同的数字！**
        ↓
★★★ **`userId ≠ 0`** ⇒ **"精确指定一个槽位"**（**TOOL 的情况**）
   ⇒ 且 **"fail rather than fall back"**（失败而不是回退）
```

★★ **⇒ 这解释了既有 memory 里的"两个命名空间"问题：**
```
memory：「平台 ID `0x01100001DEADC0DE`（LSG/room 层）
        vs Demonware account ID `0xE7C8A98A6B4C2D0E`」
        ↓
★★★ 本报告：**客户端用"平台 user id",服务端用"xuid from connect string"**
   ⇒ **两套编号确实存在,且代码明确知道这一点**
   ⇒ 所以 `userId = 0` 是一个**"让服务端自己解析"**的哨兵
```

---

## 五、★★★★ **三个环境变量的解析**

### 5.1 ★★★ `configuredPortValue`（第 823–847 行）

```cpp
if (_dupenv_s(&configured, &configuredSize, variable) != 0 ||
    !configured || !*configured)          // ★ 空串也算未设
{
    std::free(configured);
    return fallback;
}
std::uint32_t value{};
const auto end = configured + std::char_traits<char>::length(configured);
const auto parsed = std::from_chars(configured, end, value);
const auto valid = parsed.ec == std::errc{} && parsed.ptr == end &&
    value && value <= 0xFFFF;             // ★ 非零 且 ≤ 65535
std::free(configured);
if (!valid) return fallback;
```

★★★ **⇒ 四条校验：**
```
① 空串 ⇒ 回退
② 必须**整串**都被解析（`parsed.ptr == end`）
③ **非零**
④ **≤ 0xFFFF**
        ↓
★★★ ⇒ 任何失败都**回退到默认值**（不报错）
```

### 5.2 ★★★ 两个端口函数（第 849–859 行）

```cpp
std::uint16_t configuredPort()
{
    return configuredPortValue("**OLMOD_DEDICATED_CONTROL_PORT**", DefaultPort);
}
std::uint16_t configuredClientBridgePort()
{
    return configuredPortValue("**OLMOD_CLIENT_BRIDGE_PORT**", DefaultClientBridgePort);
}
```

★★ **⇒ **两个**端口环境变量（报告 094 只提到了控制端口那个）。**

### 5.3 ★★★★★ `configuredHostAddress` 的安全回退（第 861–880 行，逐字）

```cpp
// An unparseable address falls back to loopback rather than to a
// half-configured stack: a typo must not leave listeners open to the
// network while nothing can actually reach them.
in_addr parsed{};
if (inet_pton(AF_INET, value.c_str(), &parsed) != 1)
    return std::string(DefaultHostAddress);
```

★★★★★ **⇒ 一条精确的安全理由：**
```
地址**无法解析** ⇒ 回退到**回环**（不是"半配置"状态）
        ↓
★★★ 理由（逐字）："a **typo** must not leave listeners **open to the network**
 while **nothing can actually reach them**"
        ↓
★★★★★ ⇒ **拼错地址时宁可只本机可达,也不能把监听器暴露给网络**
```

★ **⇒ 这是**fail-closed 在配置层的又一例**（与报告 087 的 `zm_factory_sh` 同类）。**

### ★★★ `hostIsRemote()`（第 890–893 行）

```cpp
bool hostIsRemote()
{
    return configuredHostIpv4() != LoopbackHostIpv4;
}
```

★★ **⇒ 只问一个问题："这个栈是否通过网络寻址？"（报告 094 的原话）。**

### ★★★ `OLMOD_*` 累计

| 变量 | 来源 |
|---|---|
| **`OLMOD_DEDICATED_CONTROL_PORT`** | 094 / 097 |
| ★★ **`OLMOD_CLIENT_BRIDGE_PORT`** | ★ **097 新增** |
| **`OLMOD_HOST_ADDRESS`** | 094 / 097 |
| **`OLMOD_ALLOW_RAW_COMMAND`** | 094 |
| **`OLMOD_PROCESS_ROLE`** | 095 |
| **`OLMOD_LOG_LEVEL`** / **`OLMOD_VERBOSE_LOG`** / **`OLMOD_CONSOLE_LOG`** | 096 |
| `OLMOD_UNLOCK_ALL` / `OLMOD_SYNTHETIC_DNS` / `OLMOD_ZM_COOP_SPAWN_ZONES` / `OLMOD_DUMP_MODEL_BAND` | 其他 |
| `NT10_INJECT` | 020–043 |

★★★ **⇒ 累计 **15 个**（本报告新增 1 个：`OLMOD_CLIENT_BRIDGE_PORT`）。**

---

## 六、★★★★★ **`shared\` 10 文件全部完成 —— 收官账**

| # | 文件 | 字节 | 行 | 报告 |
|---|---|---|---|---|
| 1 | **`CodolPlaylist.cpp`** | 7,963 | 197 | **093** |
| 2 | **`CodolPlaylist.hpp`** | 3,841 | 90 | **093** |
| 3 | **`DedicatedSession.hpp`** | 5,772 | 146 | **093** |
| 4 | **`DedicatedSession.cpp`** | 22,221 | 582 | **093** |
| 5 | **`DedicatedControl.hpp`** | 13,274 | 297 | **094** |
| 6 | **`DedicatedControl.cpp`** | 36,106 | 894 | ★ **097** |
| 7 | **`LocalnetServer.hpp`** | 1,359 | 50 | **095** |
| 8 | **`ProcessRole.hpp`** | 1,178 | 45 | **095** |
| 9 | **`RuntimeLog.hpp`** | 2,018 | 49 | **096** |
| 10 | **`RuntimeLog.cpp`** | 18,359 | 426 | **096** |
| **合计** | — | **112,091** ✓ | **2,776** | **5 份报告（093–097）** |

★★★ **⇒ `shared\` 10 文件 / 112,091 B / 2,776 行 = **100% 逐行读完**。**

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **4 个 magic** | `OLDC`(`0x43444C4F`) / **`ODSE`**(`0x4553444F`) / **`ODRS`**(`0x5352444F`) / **`ODNC`**(`0x434E444F`) |
| 2 | ★★★ 命名规律 | `OL`/`OD` 前缀 + 功能字母；与 093 的 **`OLDS`** 同族 |
| 3 | ★★★★★ **24 字节帧头** | `magic(4) + version(2) + type/status(2) + payloadSize(4) + requestId(8) + checksum(4)` |
| 4 | ★★★ 请求/响应同构 | 只有偏移 **6** 的语义不同（`MessageType` vs `ResponseStatus`） |
| 5 | ★★★★★ **`checksum` = FNV-1a 32** | offset basis **2166136261**（`0x811C9DC5`）+ prime **16777619**（`0x01000193`）；**`^=` 后 `*=`** ⇒ **1a 变体** |
| 6 | ★★ 校验范围 | **只覆盖 payload**,不覆盖头 |
| 7 | ★★★★★ **回环 vs `INADDR_ANY`** | `hostIsRemote()` 决定；理由 "a control listener **reachable from the network is a decision, never an accident**" |
| 8 | ★★ backlog | **4**（低频通道） |
| 9 | ★★ 超时 | 收/发各 **500 ms**（与 `submit()` 一致） |
| 10 | ★★★ **服务端四重校验** | magic / **version 严格相等** / `payloadSize ≤ 16,384` / **checksum** |
| 11 | ★★★★ **两处 `catch(...)`** | handler 抛异常 ⇒ `Rejected`；payload 超限 ⇒ `Rejected` ⇒ **控制通道绝不会被 handler 拖垮** |
| 12 | ★★ `peerIpv4` | 由传输层填（`ntohl(peer.sin_addr)`）⇒ 印证 094 的"TRANSPORT-SUPPLIED AND NEVER ENCODED" |
| 13 | ★★★★★ **五级 schema 字节数** | **v1 = 48** / **v2 = 116**(+68) / **v3 = 156**(+40) / **v4 = 212**(+56) / **v5 = 296**(+84) |
| 14 | ★★ 版本范围 | `GameplayStatus` 接受 **v1–v5**（范围检查）；帧头层要求 **v2 严格相等** |
| 15 | ★★★★ **`GameplayStatus` 头 = 84 字节** | `magic(4) + schema(2) + clientCount(2) + serverTime(4) + 18×u32 SD(72)` |
| 16 | ★★★ **三个 payload 大小** | `EndpointStatus` **8** / `NoclipRequest` **18** / `GameplayStatus` **84 + N×(48..296)** |
| 17 | ★★ `EndpointStatus` 位域 | `payload[5]` 低 3 位 = `sessionConfigured`/`enabled`/`bound`；解码校验 `& ~7 == 0` |
| 18 | ★★ `NoclipRequest` 校验 | `bytes[13] > 1` ⇒ 拒绝（`enabled` 只能 0/1） |
| 19 | ★★★★★ **`userId = 0` 的双语义** | **0 ⇒ "按我发送的地址解析"（CLIENT 的情况）**；非 0 ⇒ "精确指定槽位"（TOOL 的情况,且 **"fail rather than fall back"**） |
| 20 | ★★★★★ **两套 ID 的代码级确认** | 客户端知**平台 user id**,服务端知 **`out.exe` connect string 里的 xuid** ⇒ **"those are different numbers"** |
| 21 | ★★★ `configuredPortValue` | 四条校验（空串/整串解析/非零/≤65535）⇒ 任何失败**回退默认** |
| 22 | ★★ **两个端口环境变量** | `OLMOD_DEDICATED_CONTROL_PORT` + ★ **`OLMOD_CLIENT_BRIDGE_PORT`** |
| 23 | ★★★★★ **地址拼错回退回环** | "a **typo** must not leave listeners **open to the network** while **nothing can actually reach them**" ⇒ **fail-closed** |
| 24 | ★★ `hostIsRemote()` | `configuredHostIpv4() != LoopbackHostIpv4` |
| 25 | ★★ `OLMOD_*` 累计 | **15 个**（本报告新增 `OLMOD_CLIENT_BRIDGE_PORT`） |
| 26 | ★★★★★ **`shared\` 收官** | **10 文件 / 112,091 B / 2,776 行 = 100% 逐行读完**（报告 093–097） |

---

## 八、结论

### 1. ★★★★★ **`DedicatedControl` 的线协议被完整还原**

```
**24 字节帧头**：`OLDC` + version 2 + type/status + payloadSize + requestId + **FNV-1a 校验**
**4 个 magic**：`OLDC` / `ODSE` / `ODRS` / `ODNC`（与 093 的 `OLDS` 同族）
**三种 payload**：`EndpointStatus` 8 B / `NoclipRequest` 18 B / `GameplayStatus` 84 + N×(48..296) B
```

### 2. ★★★★★ **`GameplayStatus` 有 v1–v5 五级向后兼容**（每级精确字节数 48/116/156/212/296）

### 3. ★★★★★ **`userId = 0` 是一个"让服务端按来源地址解析"的哨兵**

★ **⇒ 代码明确承认**两套 ID 不同**（平台 user id vs `out.exe` connect string 里的 xuid）**
**⇒ 这为既有 memory 的"两个命名空间"提供了**代码级确认**。**

### 4. ★★★★★ **两处 fail-closed 的安全设计**

```
① **`hostIsRemote()` 为 false ⇒ 绑 `INADDR_LOOPBACK`**（"reachable from the network is a decision, never an accident"）
② **地址拼错 ⇒ 回退回环**（"a typo must not leave listeners open to the network while nothing can actually reach them"）
```

### 5. ★★★★ **控制通道的鲁棒性**（两处 `catch(...)` ⇒ handler 崩溃不会拖垮服务）

### 6. ★★★★★ **`shared\` 10 文件全部完成**（112,091 B / 2,776 行 / 5 份报告）

---

## 九、下一步

- ★★★ **`game_server\qcommon\`（8 文件 / 103,413 B）** —— `net_chan_mp`（1,106 行）/ `net_dtls_cod`（765 行）
  ⇒ 直接对应报告 090 的 `invalid CODOL netchan fragment bounds` / `DTLS public-key TLV`
- 然后 `backend\Demonware\`（52 文件 / 550 KB）
