# 学习报告 111（重开）— `MatchmakingService.hpp`（116 行）+ `LanDiscovery`（52 + 295 行）

**学习范围**：`MatchmakingService.hpp`（7,779 B / 116 行）+ `LanDiscovery.hpp`（1,896 B / 52）+ `.cpp`（11,351 B / 295）
**性质**：全实测（**三文件逐行读完**）
**★★★★★ 本报告收录五个重大发现**：①**`MEEP` 协议的完整线格式（端口 `0x4321`）** ②**`RoomHostUid = 1000001` 与主 ID 的双轨设计** ③**`HandleMMBookReply` 的 5 秒重试循环根因** ④**30 秒会话生命周期** ⑤**`isLegacyBase64` 的兼容判断**

---

## 一、★★★★★ **`MEEP` 协议的完整线格式**

### 1.1 ★★★★★ 端口（`LanDiscovery.cpp:22`）

```cpp
constexpr auto DiscoveryPort = std::uint16_t{ **0x4321** };
```

★★★ **⇒ **`0x4321` = 17185**（十进制）⇒ 局域网发现端口。**

### ★★★★★ `encodePacket` 的完整构造（第 176–191 行）

```cpp
std::vector<std::uint8_t> LanDiscovery::encodePacket(
    const std::string_view event,
    const std::uint64_t origin,
    const std::string_view payload)
{
    const nlohmann::json message{
        { "**Payload**", isLegacyBase64(payload) ? std::string(payload) : base64Encode(payload) },
        { "**Origin**", origin },
        { "**Event**", event },
    };
    const auto encoded = **base64Encode(message.dump())**;
    std::vector<std::uint8_t> packet{ '**M**', '**E**', '**E**', '**P**' };
    packet.insert(packet.end(), encoded.begin(), encoded.end());
    return packet;
}
```

### ★★★★★ 完整的包结构（**双层 base64**）

```
`M E E P`（4 字节魔数）
  + base64( JSON )
        ↓
JSON = `{"Payload": <base64 或原始>, "Origin": <u64>, "Event": "<字符串>"}`
        ↓
★★★ 而 `Payload` 本身**又是一层 base64**（除非它已经是 legacy base64）
        ↓
★★★★★ ⇒ **双层 base64 编码**：
  外层 = `base64(JSON)`（去掉 `MEEP` 后）
  内层 = `JSON.Payload` 字段 = `base64(实际载荷)`
```

### ★★★ 三个 JSON 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| **`Payload`** | **string** | ★★ **base64(实际载荷)** 或**原始 legacy base64** |
| **`Origin`** | **u64** | ★ 发送者的 `localId_` |
| **`Event`** | **string** | 事件名 |

### ★★★★★ 两个事件名（第 197–205 行）

```cpp
void LanDiscovery::broadcastUpdate(const nlohmann::json &properties)
{
    broadcast("**Matchmaking::Update**", properties.dump());
}

void LanDiscovery::broadcastTerminate()
{
    broadcast("**Matchmaking::Terminate**", {});
}
```

★★★ **⇒ 只有**两个**内建事件：`Matchmaking::Update` / `Matchmaking::Terminate`。**

### ★★★★★ `ingestPacket` 的完整解析（第 214–296 行）

```cpp
constexpr std::array<std::uint8_t, 4> Signature{ 'M', 'E', 'E', 'P' };
if (packet.size() <= Signature.size() ||
    !std::ranges::equal(packet.first(Signature.size()), Signature))
    return false;

const std::string encoded(packet.begin() + Signature.size(), packet.end());
const auto decoded = base64Decode(encoded);                        // ★ 外层解码
const auto message = nlohmann::json::parse(*decoded);
const auto origin  = message.value("Origin",  std::uint64_t{});
const auto event   = message.value("Event",   std::string{});
const auto payload = message.value("Payload", std::string{});
if (!origin || **origin == localId_**) return false;               // ★ 丢弃自己发的
...
const auto decodedPayload = base64Decode(payload);                 // ★ 内层解码
...
if (event == "Matchmaking::Terminate") { ...erase...; return true; }
if (event == "Matchmaking::Update")    { ...upsert...; return true; }
```

### ★★★★★ 五个精确行为

```
① ★★ **`origin == localId_` ⇒ 丢弃**（不处理自己广播的包）
        ↓
② ★★★ **`nodeAddresses_` 绑定 origin → sourceAddress**
   ⇒ 若同一 origin 从**不同地址**来 ⇒ **拒绝**（`!inserted && node->second != sourceAddress`）
        ↓
③ ★★ `Terminate` ⇒ **删除该会话**
        ↓
④ ★★ `Update` ⇒ **upsert**（存在则更新 properties + updatedAt）
        ↓
⑤ ★ **其他事件** ⇒ 走 `handlers_`（`subscribe` 注册的回调）
```

★★★ **⇒ 第 ② 条是**防伪造**：一个 origin 只能来自一个地址。**

---

## 二、★★★★★ **`isLegacyBase64` 的兼容判断**

### 2.1 ★★★★★ 完整实现（第 24–35 行）

```cpp
bool isLegacyBase64(const std::string_view input)
{
    if (input.empty()) return false;
    return std::ranges::all_of(input, [](const unsigned char value)
    {
        return (value >= '**A**' && value <= '**Z**') ||
            (value >= '**a**' && value <= '**z**') ||
            (value >= '**/**' && value <= '**9**') ||        // ★ 注意：'/' 到 '9' 覆盖 0-9 和 :;<=>?@
            value == '**=**' || value == '**+**';
    });
}
```

### ★★★★★ 字符范围分析

```
`A`–`Z`  ⇒ 大写
`a`–`z`  ⇒ 小写
`/`–`9`  ⇒ ★★★ **ASCII 0x2F 到 0x39**
   ⇒ 包含：`/` `0`-`9` `:` `;` `<` `=` `>` `?` `@`
        ↓
★★★ ⇒ 这个范围**比标准 base64 宽**（标准只有 `A-Za-z0-9+/=`）
   ⇒ 额外允许 `:` `;` `<` `>` `?` `@`
```

★★ **⇒ 可能是**故意放宽**（避免误判）,也可能是**笔误**（本应 `0`–`9`）。**
**⇒ 记录为**待核对项**（但实际影响小,因为只用于判断"是否已经是 base64"）。**

### ★★★ 用途（第 181 行）

```cpp
{ "Payload", isLegacyBase64(payload) ? std::string(payload) : base64Encode(payload) },
```

★★★ **⇒ 若 payload **已经是 base64 形态** ⇒ **不再编码**（避免双层）。**
**⇒ 否则 ⇒ `base64Encode(payload)`。**

★ **⇒ 这是**"兼容旧格式"的判断**（legacy 客户端可能直接发 base64）。**

---

## 三、★★★★★ **`RoomHostUid = 1000001` 与主 ID 的双轨设计**

### 3.1 ★★★★★ 完整注释（`MatchmakingService.hpp`，逐字）

```cpp
// ★★★ 2026-10-07 05:0x -- **候选/房间的 host uid，唯一权威副本**（原先只在 .cpp 的匿名命名空间里）。
// 它同时是：候选记录 `+0x168/+0x16C` 的值（`writeSessionRecordTail` 第二个字段）
// **以及** `HandleMMBookReply` 门3 要求推送 SenderID 等于的那个值 ⇒ 必须两边同源。
// 反汇编依据：`sub_62F6F0` 把候选 `+0x168/+0x16C` 存进 `room+0x3A048/+0x3A04C`，
// `sub_632680` 拿推送的 u64 与它比。见 `…-0255.md` §11.2。
static constexpr std::uint64_t RoomHostUid = **1000001**;
```

### ★★★★★ 与 `setLocalUserId` 的双轨

```cpp
// ★★★ 2026-10-07 05:0x -- "主 ID" = 账号 userId（黄金对齐；由 `Servers.cpp` 用
// `session_.snapshot().userId` 接线）。候选记录 `+0x168` 与候选推送 SenderID 都用它。
// 未接线时默认值 = `RoomHostUid`（保持旧行为，便于回退）。
void setLocalUserId(std::uint64_t userId);
...
mutable std::uint64_t localUserId_ = **RoomHostUid**;      // ★ 默认 = 1000001
```

★★★★★ **⇒ 一个**双轨设计**：**
```
`localUserId_` 的**默认值 = `RoomHostUid`（1000001）**
        ↓
★★★ 但 `Servers.cpp` 会用 `session_.snapshot().userId` **接线覆盖它**
   ⇒ 即 **`0x01100001DEADC0DE`**（报告 105/110）
        ↓
★★★ ⇒ **未接线 ⇒ 保持旧行为（1000001）**；**接线后 ⇒ 黄金对齐值**
```

★★ **⇒ 这与报告 110 的"主 ID 改回自己"**完全一致** ✓**
**⇒ 且给出了**回退路径**（不接线即旧行为）。**

### ★★★★★ `HandleMMBookReply` 的 5 秒重试循环根因（逐字）

```cpp
//   `sub_62F6F0`（= `CandidateToMMBookCtx`，被 `AllocResultHandler(0x637720)` 调用）把
//   **候选记录的 `+0x168/+0x16C`** 存进房间 `+0x3A048/+0x3A04C`，作为"期望的 mmbook ID"；
//   `HandleMMBookReply(0x632680)` 拿**推送的 ID** 与它比：
//       if (a2 == room[59410] && a3 == room[59411]) { … 文本比 "mmbook accepted" … 否则
//           再比 记录(+0x168/+0x16C) —— 不等就 `sub_6292B0` **重发分配请求** }
//   我们候选记录的 `+0x168` 写的是 `writeSessionRecordTail` 的第二个字段 = `RoomHostUid = 1000001`
//   （`MatchmakingService.cpp:147`），而推送带的却是 `session_.snapshot().userId`
//   ⇒ **必然不等 ⇒ 5 秒重试循环**（d13 实测：`room+0x3A048/4C` 被清零、`mmbook` 每 5 s 一发）。
```

### ★★★★★ 完整的循环链

```
① 候选记录 `+0x168` = **`RoomHostUid` = 1000001**
        ↓
② 推送的 SenderID = **`session_.snapshot().userId`**（= `0x01100001DEADC0DE`）
        ↓
★★★ ③ **必然不等**
        ↓
★★★ ④ `HandleMMBookReply` 不等 ⇒ `sub_6292B0` **重发分配请求**
        ↓
★★★★★ ⑤ ⇒ **5 秒重试循环**（d13 实测：`room+0x3A048/4C` 被清零、`mmbook` 每 5 s 一发）
```

★★ **⇒ 修复：**让推送的 SenderID 用同一个权威值**（`setLocalUserId` 接线）。**

### ★★★ 三个精确的地址

| 地址 | 名称 | 作用 |
|---|---|---|
| **`sub_62F6F0`** | ★ `CandidateToMMBookCtx` | 把候选 `+0x168/+0x16C` 存进 `room+0x3A048/+0x3A04C` |
| **`AllocResultHandler = 0x637720`** | — | 调用 `sub_62F6F0` |
| **`HandleMMBookReply = 0x632680`** | — | 拿推送 ID 与期望值比 |

★★ **⇒ 三个精确的 RVA：`0x637720` / `0x632680`（`sub_62F6F0` 未给 RVA,只有名字）。**

### ★★★ `ServerCandidatePublisher` 的签名变化（逐字）

```cpp
// ★★★ 2026-10-07 04:2x -- **带 host uid**（单变量 ②：推送 ID 与候选记录对齐）。
using ServerCandidatePublisher = std::function<void(**std::uint64_t hostUid**)>;
```

★★ **⇒ 从 `void()` 改成 `void(std::uint64_t hostUid)` ⇒ **把权威值传下去**（"避免第二份常量副本"）。**

---

## 四、★★★★★ **30 秒会话生命周期**

### 4.1 ★★★★★ `activeSessions`（第 283–295 行）

```cpp
std::vector<LanDiscovery::RemoteSession> LanDiscovery::activeSessions() const
{
    constexpr auto Lifetime = std::chrono::seconds(**30**);
    const auto now = std::chrono::steady_clock::now();
    std::scoped_lock lock(sessionsMutex_);
    std::erase_if(sessions_, [now](const RemoteSession &session)
    {
        return now - session.updatedAt >= Lifetime;
    });
    return sessions_;
}
```

★★★ **⇒ 30 秒无更新 ⇒ 会话过期删除。**

★★ **⇒ 而报告 110 的 `broadcastUpdate` 在每次 `createSession`/`updateSession` 时调用 ⇒ 30 秒窗口足够。**

### ★★★ `RemoteSession` 的四个字段（`LanDiscovery.hpp`）

```cpp
struct RemoteSession
{
    std::uint32_t address{};
    std::uint64_t id{};
    nlohmann::json properties = nlohmann::json::object();
    std::chrono::steady_clock::time_point updatedAt;
};
```

### ★★★ UDP socket 的配置（第 62–90 行）

```cpp
socket_ = socket(AF_INET, **SOCK_DGRAM**, IPPROTO_UDP);
const auto enabled = TRUE;
setsockopt(socket_, SOL_SOCKET, **SO_BROADCAST**, ...);       // ★ 允许广播
setsockopt(socket_, SOL_SOCKET, **SO_REUSEADDR**, ...);       // ★ 地址复用
ioctlsocket(socket_, **FIONBIO**, &nonblocking);               // ★ 非阻塞
address.sin_port = htons(**DiscoveryPort**);
address.sin_addr.s_addr = htonl(**INADDR_ANY**);              // ★ 绑所有接口
bind(...);
worker_ = std::thread([this] { receive(); });                 // ★ 后台线程
```

★★★ **⇒ 四个 socket 选项：`SO_BROADCAST` / `SO_REUSEADDR` / `FIONBIO` / `INADDR_ANY`。**

### ★★★ 接收循环的 200 ms 超时（第 148–153 行）

```cpp
FD_SET readSet{};
FD_SET(socket_, &readSet);
timeval timeout{};
timeout.tv_usec = **200'000**;                                 // ★ 200 ms
const auto selected = select(0, &readSet, nullptr, nullptr, &timeout);
```

★★ **⇒ `select` 用 **200 ms** 超时 ⇒ 可及时响应 `stopping_`。**

### ★★★ 广播地址（第 116–119 行）

```cpp
destination.sin_port = htons(DiscoveryPort);
destination.sin_addr.s_addr = htonl(**INADDR_BROADCAST**);
sendto(...);
```

★★ **⇒ 广播到 **`INADDR_BROADCAST`**（`255.255.255.255`）的 `0x4321` 端口。**

---

## 五、★★★★ **`MatchmakingService.hpp` 的其余设计**

### 5.1 ★★★ 六个回调类型

```cpp
using GameServerProvider           = std::function<std::optional<GameServerEndpoint>()>;
using GameServerConfigurator       = std::function<bool(std::span<const std::uint8_t>)>;
using SessionDescriptorCanonicalizer = std::function<std::optional<std::vector<std::uint8_t>>(std::span<const std::uint8_t>)>;
using SessionUpdatePublisher       = std::function<void(const nlohmann::json &)>;
using SessionTerminatePublisher    = std::function<void()>;
using ServerCandidatePublisher     = std::function<void(std::uint64_t hostUid)>;
```

★★★ **⇒ 六个注入点 ⇒ **高度可测试**（每个都能替换）。**

### ★★★ 两个"留底"的接口（逐字）

```cpp
// ★★ 2026-10-07 02:3x -- D2'（单变量）：把最近一次 `FIND_SERVERS`(kind 1) 应答里下发的
// **服务端记录对象**留一份，供 `Unknown0BService` 在 `11/4 op=0x27` 分配请求上**原样回放**。
// 依据：客户端刚在同一房间**接受过**这份对象（容器 count=1、data 有内容），
// 而 `AllocResultHandler` 拿容器 data 按 `count*0x238` 拷进 `room+0x7470`
// ⇒ 两条应答承载的是同一类 `0x238` 字节记录。
[[nodiscard]] std::vector<std::vector<std::uint8_t>> lastServerRecords() const;
```

★★★★★ **⇒ 两个精确数字：**
```
**`count * 0x238`** ⇒ 每条记录 **568 字节**（`0x238` = 568）
**`room + 0x7470`** ⇒ 拷贝目标
        ↓
★★★ 与报告 110 的"**568 字节的 wire record**"**完全吻合** ✓
```

### ★★★ 两个 mutex 的非递归声明（`MatchmakingService.hpp:72`）

```cpp
mutable std::mutex localMutex_;
```

★★★ **⇒ 明确是 `std::mutex`（非递归）⇒ 与报告 110 的死锁**完全对应** ✓**

### ★★★ 三个 mutex

| mutex | 保护 |
|---|---|
| **`localMutex_`** | `localProperties_` |
| **`performanceMutex_`** | `performanceValues_` |
| **`lastServerRecordsMutex_`** | `lastServerRecords_` |
| **`ownSessionRecordMutex_`** | `ownSessionRecord_` |

★ **⇒ 实际是 **4 个**（含 `ownSessionRecordMutex_`）。**

---

## 六、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **发现端口** | **`0x4321`** = **17,185** |
| 2 | ★★★★★ **`MEEP` 包结构** | `'M','E','E','P'` + **base64(JSON)** |
| 3 | ★★★ JSON 三字段 | **`Payload`**（内层 base64）/ **`Origin`**（u64）/ **`Event`**（string） |
| 4 | ★★★★★ **双层 base64** | 外层 `base64(JSON)`,内层 `JSON.Payload` |
| 5 | ★★★ **两个内建事件** | **`Matchmaking::Update`** / **`Matchmaking::Terminate`** |
| 6 | ★★★ `origin == localId_` | **丢弃**（不处理自己广播的包） |
| 7 | ★★★★ **地址绑定防伪造** | `nodeAddresses_` 绑定 `origin → sourceAddress`；**同一 origin 从不同地址来 ⇒ 拒绝** |
| 8 | ★★ `Terminate` / `Update` | 删会话 / **upsert** |
| 9 | ★★★ **`isLegacyBase64` 的范围** | `A-Z` / `a-z` / ★★ **`/`–`9`**（比标准宽,含 `:;<>?@`）/ `=` / `+` |
| 10 | ★★ 用途 | 已是 base64 ⇒ 不再编码（避免双层） |
| 11 | ★★★★★ **`RoomHostUid = 1000001`** | 候选记录 `+0x168/+0x16C` 的值,**也是** `HandleMMBookReply` 门3 要求的推送 SenderID |
| 12 | ★★★★ **双轨设计** | `localUserId_` **默认 = `RoomHostUid`**；`Servers.cpp` 用 `session_.snapshot().userId` **接线覆盖**（`0x01100001DEADC0DE`） |
| 13 | ★★★★★ **5 秒重试循环的根因** | 候选 `+0x168` = `1000001`,推送 SenderID = `snapshot().userId` ⇒ **必然不等** ⇒ `sub_6292B0` **重发分配请求**（d13：`mmbook` 每 5 s 一发） |
| 14 | ★★★ 三个地址 | **`sub_62F6F0`**（`CandidateToMMBookCtx`）/ **`AllocResultHandler = 0x637720`** / **`HandleMMBookReply = 0x632680`** |
| 15 | ★★★ `ServerCandidatePublisher` | 从 `void()` 改为 **`void(std::uint64_t hostUid)`**（避免第二份常量副本） |
| 16 | ★★★★★ **30 秒会话生命周期** | `activeSessions` 里 `Lifetime = 30s`,过期即删 |
| 17 | ★★★ UDP 四选项 | **`SO_BROADCAST`** / **`SO_REUSEADDR`** / **`FIONBIO`** / **`INADDR_ANY`** |
| 18 | ★★ `select` 超时 | **200 ms** |
| 19 | ★★ 广播地址 | **`INADDR_BROADCAST`**（`255.255.255.255`）的 `0x4321` |
| 20 | ★★★ **六个回调注入点** | `GameServerProvider` / `GameServerConfigurator` / `SessionDescriptorCanonicalizer` / `SessionUpdatePublisher` / `SessionTerminatePublisher` / `ServerCandidatePublisher` |
| 21 | ★★★★★ **两个精确数字** | **`count * 0x238`** ⇒ 每条记录 **568 字节** ✓ 与报告 110 的"568 字节 wire record"吻合；拷贝目标 **`room + 0x7470`** |
| 22 | ★★★ `localMutex_` 非递归 | 明确 `std::mutex` ⇒ ✓ 与报告 110 的死锁**完全对应** |
| 23 | ★★ 四个 mutex | `localMutex_` / `performanceMutex_` / `lastServerRecordsMutex_` / `ownSessionRecordMutex_` |

---

## 七、结论

### 1. ★★★★★ **`MEEP` 协议的完整线格式被还原**

```
`MEEP`(4) + base64(JSON{Payload, Origin, Event})
        ↓
★★★ **双层 base64**（外层 JSON,内层 Payload）
★ 端口 **`0x4321`**,UDP 广播到 **`255.255.255.255`**
```

### 2. ★★★★★ **`RoomHostUid = 1000001` 与 `localUserId_` 是双轨设计**

```
默认 = `RoomHostUid`（1000001,旧行为）
        ↓
★★★ `Servers.cpp` 接线后 = `0x01100001DEADC0DE`（黄金对齐）
```

### 3. ★★★★★ **5 秒重试循环的根因是"两个 ID 不同源"**

★ **⇒ 候选 `+0x168` 用 `1000001`,推送 SenderID 用 `snapshot().userId` ⇒ 必然不等。**

### 4. ★★★★★ **`count * 0x238` = 每条 568 字节**（与报告 110 吻合）

### 5. ★★★★ **`localMutex_` 是 `std::mutex`（非递归）**（与报告 110 的死锁完全对应）

### 6. ★★★ **30 秒会话生命周期 + UDP 广播发现**

### 7. ★★★ **六个回调注入点 ⇒ 高度可测试**

---

## 八、下一步

- `MarketplaceService`（1,099 行）/ `StatsService`（875 行）/ `LobbyProtocol`（807 行）
- `Unknown0BService`（669 行）/ `Profiles2Service`（630 行）/ `ClanService`（623 行）
- `Storage2Service`（450 行）/ `Friends2Service`（325 行）/ `InstantMessageService`（242 行）
- `ContentUnlock2Service` / `TencentService` / `TitleUtilitiesService`
- `SharedRoom*`（4 文件）/ `Servers.cpp`（624 行）
