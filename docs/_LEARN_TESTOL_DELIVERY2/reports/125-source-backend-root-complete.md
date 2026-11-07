# 学习报告 125（重开）— `backend` 根收官：`SharedRoom*` 六文件 + 两个头

**学习范围**：`DedicatedBookingDispatcher.hpp`（69 行）+ `IServer.hpp`（3 行）+ `SharedRoomClient.hpp/.cpp`（49/189）+ `SharedRoomControl.hpp/.cpp`（92/456）+ `SharedRoomHost.cpp`（54）+ `SharedRoomSessionOwner.hpp/.cpp`（75/172）
**性质**：全实测（**八文件逐行读完**）
**★★★★★ 本报告收录六个重大发现**：①**房间协议 `SchemaVersion = 2` 的完整线格式（六种消息）** ②**`DefaultPort = 28970`（独立于专服 28961/28962）** ③**`connect` 的重复判定 = (port, ipv4) 二元组** ④**`freeze` 的 `allocationOwnerUserId_` 粘性** ⑤**`canonicalSessionDescriptor_` 的首次写入即定案** ⑥**`backend` 根 13 文件全部完成**

---

## 一、★★★★★ **房间协议 `SchemaVersion = 2` 的完整线格式**

### 1.1 ★★★ 公共框架

```cpp
constexpr std::uint8_t **SchemaVersion = 2**;    // ★ 每条消息首字节

appendU16 / appendU32 / appendU64   ⇒ **小端**（shift 0,8,16,... 逐字节 push_back）
readU16  / readU32  / readU64       ⇒ **小端**
```

★★★ **⇒ 与 `DedicatedControl` 一致**（报告 094 已记录小端）。

### 1.2 ★★★★★ **六种消息的完整字节布局**

| 消息 | 总长 | 布局 |
|---|---|---|
| **`ConnectRequest`** | **12 + N** | `[0]`=**ver 2** · `[1..8]`=**u64 userId** · `[9..10]`=**u16 bridgePort** · `[11]`=**u8 nameLen** · `[12..]`=**name（GBK）** |
| **`MemberRequest`** | ★ **17** | `[0]`=ver · `[1..8]`=u64 userId · `[9..16]`=u64 token |
| **`ReadyRequest`** | ★★ **18** | = `MemberRequest`(17) + `[17]`=**u8 ready** |
| **`SessionDescriptorRequest`** | **17 + N** | = `MemberRequest`(17) + **descriptor** |
| **`FreezeRequest`** | ★★ **25** | `[0]`=ver · `[1..8]`=u64 generation · `[9..16]`=u64 claimant.userId · `[17..24]`=u64 claimant.token |
| **`Token`（应答）** | ★ **9** | `[0]`=ver · `[1..8]`=u64 token |
| **`FrozenRoomRoster`** | **18 + Σ(24+N)** | `[0]`=ver · `[1..8]`=u64 generation · `[9..16]`=u64 ownerUserId · `[17]`=**u8 成员数** · 每成员 **24 + nameLen** |

### ★★★★★ **`FrozenRoomRoster` 的成员记录 24 字节布局**

```cpp
appendU64(member.userId);            // [0..7]
appendU16(member.bridgePort);        // [8..9]
appendU32(member.bridgeIpv4);        // [10..13]
appendU64(member.connectionToken);   // [14..21]
push_back(ready ? 1 : 0);            // [22]
push_back(displayName.size());       // [23]
insert(displayName);                 // [24..24+N)
```

★★★ **⇒ 精确偏移：**
```
`[0..7]`   u64 userId
`[8..9]`   u16 bridgePort
`[10..13]` u32 bridgeIpv4      ← ★ 4 字节,夹在两个 u64 之间
`[14..21]` u64 connectionToken
`[22]`     u8  ready            ← ★ 校验 `> 1` 则拒绝
`[23]`     u8  nameLen          ← ★ 校验 `== 0` 则拒绝
`[24..]`   name
```

★ **⇒ 解码时逐项校验（第 311–318 行）：**
```cpp
if (input.size() - offset < 24)                 return nullopt;   // ★ 长度不足
const auto nameSize = input[offset + 23];
if (!nameSize || input[offset + 22] > 1 ||
    input.size() - offset < 24u + nameSize)     return nullopt;   // ★ 三个校验
```

### ★★★ 两个终检（第 329–331 行）

```cpp
return roster.generation && roster.ownerUserId && offset == input.size()
    ? std::optional{ roster } : std::nullopt;
```

★★ **⇒ 三个必须：`generation != 0` / `ownerUserId != 0` / **`offset == input.size()`（无尾随字节）。**

### ★★★ 四个 `encode` 的拒绝条件

| 编码器 | 拒绝条件 |
|---|---|
| `ConnectRequest` | `displayName.empty() \|\| size > 0xFF` |
| `SessionDescriptorRequest` | `descriptor.empty() \|\| size > MaximumPayloadSize - 17` |
| `FrozenRoomRoster` | `!generation \|\| members.empty() \|\| size > 0xFF` + 任一 `displayName` 空或 > 0xFF |
| `encodeToken` | 无（恒成功） |

---

## 二、★★★★★ **`DefaultPort = 28970`（第三个端口）**

```cpp
constexpr std::uint16_t DefaultPort = **28970**;
```

### ★★★★★ 三个端口的完整对照

| 端口 | 用途 | 出处 |
|---|---|---|
| **28961** | **专服控制口**（`DedicatedControl::DefaultPort`） | 报告 094 |
| **28962** | **客户端 bridge 口** | 报告 094 |
| ★★★ **28970** | **房间主控口**（`SharedRoomControl::DefaultPort`） | ★ **本报告** |

★★★ **⇒ 三个端口**互不重叠**,且 **28970 与 28961/28962 相隔 8/9**（不是连续段）。**

### ★★★ 环境变量覆盖

```cpp
_dupenv_s(&configured, &size, "**OLMOD_ROOM_OWNER_PORT**");
        ↓
解析失败 / 0 / > 0xFFFF ⇒ **回退 DefaultPort**
```

★★★ **⇒ 新增第 30 个 `OLMOD_*` 变量：`OLMOD_ROOM_OWNER_PORT`。**

---

## 三、★★★★★ **`connect` 的重复判定 = (port, ipv4) 二元组**

### 3.1 ★★★★★ 完整实现（第 31–59 行）

```cpp
const std::lock_guard lock(mutex_);
// TWO MEMBERS COLLIDE ONLY WHEN THEY SHARE A PORT ON THE SAME MACHINE.
// Keying on the port alone was right while everyone was on the owner's
// box and is exactly wrong once they are not: two friends both running
// the DEFAULT bridge port **28962** on their own PCs are not a duplicate,
// and the second of them used to be refused here.
if (!userId || !bridgePort || !validDisplayName(displayName) ||
    (!members_.contains(userId) && members_.size() >= capacity_) ||
    std::ranges::any_of(members_, [&](const auto &entry) {
        return entry.first != userId &&
            entry.second.bridgePort == bridgePort &&
            entry.second.bridgeIpv4 == bridgeIpv4;   // ★ 两个条件都要等
    }))
{
    return std::nullopt;
}
```

### ★★★★★ 四个拒绝条件

| # | 条件 | 说明 |
|---|---|---|
| **1** | `!userId` | id 为 0 |
| **2** | `!bridgePort` | 端口为 0 |
| **3** | `!validDisplayName(displayName)` | 名字非法 |
| **4** | `!contains(userId) && size >= capacity_` | ★ **新成员**且已满 |
| **5** | ★★ **`(port, ipv4)` 二元组重复** | 排除自己 |

★★★ **⇒ 第 4 条的措辞**精确**：`!members_.contains(userId) && size >= capacity_`
```
**已有成员**重新 connect ⇒ **不检查容量**（允许原地更新）
**新成员** ⇒ 满则拒
```

### ★★★★★ 第 5 条的实测背景（逐字）

```
"TWO MEMBERS COLLIDE ONLY WHEN THEY SHARE A PORT ON THE SAME MACHINE."
        ↓
★★★ 老实现：**只看端口** ⇒ 在"所有人都在房主机器上"时正确
★★★ 新现实：**两个朋友各自在自己 PC 上跑默认 bridge 端口 `28962`**
   ⇒ **不是重复** ⇒ 但老实现**把第二个人拒了**
```

★ **⇒ 与报告 124 的 `rosterBridges` 的"THE PAIR, NOT THE PORT"**完全同源** ✓**

### ★★★ `capacity` 默认 **18**

```cpp
explicit SharedRoomSessionOwner(std::size_t capacity = **18**);
```

★★★ **⇒ 与 `MaximumSessionMembers = 18`（报告 095）**完全一致** ✓**

### ★★★ `validDisplayName` 的放宽（第 14–23 行，逐字）

```cpp
return !value.empty() && value.size() <= **16** &&
    // ★ 2026-10-07 15:0x -- 放宽到「无控制符」：名字线编码 = **GBK 字节**
    //   （`Lifetime丷` = `... **81 52**`），与 `IdentityConfig::validateDisplayName`
    //   同一口径；原先的 **0x7E 上限**会把 GBK 名字拒掉（**room owner 连接会失败**）。
    std::ranges::all_of(value, [](const unsigned char character) {
        return character >= **0x20** && character != **0x7F**;
    });
```

★★★★★ **⇒ 三个精确事实：**
```
① 长度 ≤ **16**
② 合法字符：**`>= 0x20 && != 0x7F`**（**允许 0x80..0xFF 即 GBK 高位字节**）
③ ★★★ 反例：`Lifetime丷` 的 GBK 尾部 = **`81 52`**
   ⇒ 老实现（**0x7E 上限**）会**拒掉** ⇒ **room owner 连接失败**
```

★★ **⇒ 与报告 106 的 `IdentityConfig::validateDisplayName`**同一口径** ✓**

### ★★★ `canonicalSessionDescriptor_` 的失效点

```cpp
connect()    ⇒ canonicalSessionDescriptor_.reset();   // ★ 新连接 ⇒ 清
disconnect() ⇒ canonicalSessionDescriptor_.reset();   // ★ 断开 ⇒ 清
```

★★ **⇒ 两次 reset,`setReady` 不清。**

---

## 四、★★★★★ **`freeze` 的 `allocationOwnerUserId_` 粘性**

### 4.1 ★★★★★ 完整实现（第 93–140 行）

```cpp
const std::lock_guard lock(mutex_);
if (const auto frozen = frozenRosters_.find(generation); frozen != frozenRosters_.end())
    return frozen->second;                     // ★ ① 已冻结 ⇒ 原样返回（幂等）
if (!generation || members_.empty() ||
    std::ranges::any_of(members_, [](const auto &e) { return !e.second.ready; }))
    return std::nullopt;                       // ★ ② 有未 ready 的成员 ⇒ 拒绝
std::uint64_t ownerUserId = claimantUserId;
if (claimantUserId || claimantToken)
{
    const auto claimant = members_.find(claimantUserId);
    if (claimant == members_.end() || claimant->second.connectionToken != claimantToken)
        return std::nullopt;                   // ★ ③ 认领者校验
    if (!allocationOwnerUserId_)
        allocationOwnerUserId_ = claimantUserId;   // ★★ ④ 首次认领者 ⇒ 粘住
    ownerUserId = *allocationOwnerUserId_;
}
else if (!members_.empty())
    ownerUserId = members_.begin()->first;     // ★ ⑤ 无认领者 ⇒ 取首个成员
```

### ★★★★★ 五个分支

| # | 分支 | 结果 |
|---|---|---|
| **①** | `frozenRosters_` 已有该 `generation` | ★ **原样返回**（幂等） |
| **②** | `!generation` / 空 / **任一未 ready** | 拒绝 |
| **③** | 认领者的 `token` 不符 | 拒绝 |
| **④** | ★★ **首次认领 ⇒ `allocationOwnerUserId_` 粘住** | 后续认领者被**忽略** |
| **⑤** | 无认领者 | 取 `members_.begin()->first` |

★★★★★ **⇒ 第 ④ 条是关键：**
```
第一次成功的 `freeze` 的 claimant ⇒ **成为永久 owner**
        ↓
★★★ 后续任何人的 `freeze` ⇒ `ownerUserId = *allocationOwnerUserId_`（**不看自己是谁**）
        ↓
★★★ ⇒ 只有**首个认领者**能当房主（房主身份**粘性**）
```

★★ **⇒ 与报告 124 的 `non_owner_booking_ignored`**配合**：`ownerUserId` 决定谁有权 booking。**

### ★★★ 幂等的意义

```cpp
if (const auto frozen = frozenRosters_.find(generation); ...)
    return frozen->second;
```

★★ **⇒ 同一 `generation` 的重复 `freeze` 返回**同一份名册**（不重算）**
**⇒ `frozenRosters_` 是 `std::map<u64, FrozenRoomRoster>`（**可多代并存**）。**

---

## 五、★★★★★ **`canonicalSessionDescriptor_` 的首次写入即定案**

### 5.1 ★★★★★ 完整实现（第 154–171 行）

```cpp
const auto member = members_.find(userId);
if (member == members_.end() || member->second.connectionToken != connectionToken ||
    descriptor.empty())
{
    return std::nullopt;
}
if (!canonicalSessionDescriptor_)
    canonicalSessionDescriptor_ = std::move(descriptor);   // ★ 只在空时写
return canonicalSessionDescriptor_;                        // ★ 返回已存的
```

★★★★★ **⇒ 语义：**
```
第一次 `canonicalizeSessionDescriptor` ⇒ **存下 descriptor**
        ↓
★★★ 后续调用 ⇒ **忽略传入的 descriptor**,返回**第一次那个**
        ↓
★★★ 失效点：`connect()` / `disconnect()` 才 reset
```

★★ **⇒ 这是"会话描述符**全局唯一化**"：所有客户端必须看到同一份。**
**⇒ 但**不校验一致性**（第二个客户端的 descriptor 被静默丢弃）⇒ 记录为**设计取舍**。**

---

## 六、★★★★ **`SharedRoomClient` 的五个操作与 `SharedRoomHost` 的启动**

### 6.1 ★★★★★ 五个操作对应的消息类型

| 客户端方法 | 消息类型 | payload |
|---|---|---|
| `connect` | **`RoomConnect`** | `ConnectRequest` |
| `disconnect` | **`RoomDisconnect`** | `MemberRequest` |
| `setReady` | **`RoomSetReady`** | `ReadyRequest` |
| `freeze` | **`RoomFreeze`** | `FreezeRequest` |
| `canonicalizeSessionDescriptor` | **`RoomCanonicalizeSession`** | `SessionDescriptorRequest` |

★★ **⇒ 五个一一对应 ✓**

### ★★★ `ownerHost()` 每次重读（第 10–16 行，逐字）

```cpp
// Read per call rather than cached: the owner's address is
// configuration, and a cached copy would silently outlive a change to
// it in a process that is already running.
std::string ownerHost()
{
    return OlMod::DedicatedControl::configuredHostAddress();
}
```

★★ **⇒ 不缓存配置（避免进程内改配置后失效）。**

### ★★★ `connect` 的失败日志（第 56–61 行）

```
"shared room connect rejected user=<id> bridge=<port> delivered=<0|1> status=<n> token=<0|1>"
```

★★ **⇒ 五个字段全打。**

### ★★★ `freeze` 拒绝 `generation == 0`（第 124–125 行）

```cpp
if (!generation) return std::nullopt;    // ★ 在加锁前
```

### ★★★ `canonicalizeSessionDescriptor` 的三重前置（第 158 行）

```cpp
if (!connection_ || connection_->userId != userId || descriptor.empty())
    return std::nullopt;
```

### ★★★★ `SharedRoomHost.cpp` 的启动（第 29–54 行）

```cpp
SharedRoomSessionOwner owner;
SharedRoomControl::Handler handler(owner);
OlMod::DedicatedControl::Server server;
const auto port = SharedRoomControl::configuredPort();          // ★ 28970 或覆盖
const auto bind = DedicatedControl::hostIsRemote()
    ? std::string("**0.0.0.0**")
    : std::string(DedicatedControl::DefaultHostAddress);        // ★ 本机则绑回环
if (!server.start(port, [&handler](const auto &m) { return handler(m); }))
{
    std::cerr << "Failed to start shared room owner on " << bind << ':' << port
              << " error=" << server.lastSocketError() << '\n';
    return 1;
}
SetConsoleCtrlHandler(onConsoleControl, TRUE);
std::cout << "OL-Mod shared room owner listening on " << bind << ':' << server.port()
          << " host=" << DedicatedControl::configuredHostAddress() << '\n';
while (Running.load()) Sleep(100);
server.stop();
```

★★★★★ **⇒ 一个**独立的可执行程序**：**
```
`SharedRoomHost` = **房间主控独立进程**
   ⇒ 绑 `0.0.0.0`（远端）或回环（本机）
   ⇒ 端口 **28970**
   ⇒ 主循环 `Sleep(100)` 直到 Ctrl-C/Ctrl-Break/Ctrl-Close
```

★ **⇒ 三个控制事件：`CTRL_C_EVENT` / `CTRL_BREAK_EVENT` / `CTRL_CLOSE_EVENT`。**

### ★★★★★ `logRoomEvent` 的日志（第 98–131 行）

```
"[YYYY-MM-DD HH:MM:SS.mmm] [room-owner] <event> user=<id> bridge=<port> members=<n> ready=<n> accepted=<0|1>"
        ↓
★★★ 同时写 **stderr** 和 `<exe目录>/Logs/ol-room-owner.log`（append）
```

★★★ **⇒ 五个事件：`connect` / `disconnect` / `ready` / `unready` / `freeze`。**
**⇒ 理由（逐字）："Keep this in the standalone owner so multi-client room failures are
observable **without parsing the game's unbounded backend log**."**

---

## 七、★★★★ **`DedicatedBookingDispatcher.hpp` 的五个回调类型**

```cpp
using Diagnostic        = std::function<void(std::string_view)>;
using EntitlementCheck  = std::function<bool(std::uint64_t, std::span<const std::uint32_t>)>;
using RosterProvider    = std::function<std::optional<FrozenRoomRoster>(std::uint64_t)>;
using MatchRulesProvider= std::function<std::optional<MatchRules>(const BookingSelection &)>;
using ControlSubmit     = std::function<SubmitResult(
    std::uint32_t bridgeIpv4, std::uint16_t bridgePort,
    const Message &, std::uint32_t timeoutMilliseconds)>;
```

★★★ **⇒ 五个回调,与报告 124 的 `State` 五个成员**一一对应** ✓**

### ★★★ `ControlSubmit` 的注释（逐字）

```cpp
// (bridgeIpv4, bridgePort, message, timeoutMilliseconds). **The address
// leads because it is the half that used to be missing**: a member was
// addressed by **port alone**, which only ever worked on **one machine**.
```

★★★ **⇒ 与 `SharedRoomSessionOwner::connect` 的"THE PAIR, NOT THE PORT"**同一主题** ✓**

### ★★★ 三个构造函数（委托链）

```cpp
(session, marketplace, diagnostic)
    ⇒ (session, marketplace, {}, diagnostic)                       // 默认 roster
(session, marketplace, rosterProvider, diagnostic)
    ⇒ (session, [marketplace]{ ensureEntitlements }, rosterProvider,
       [loadMatchRules], [DedicatedControl::submit], diagnostic)    // ★ 五个回调
(session, entitlementCheck, rosterProvider, matchRulesProvider, controlSubmit, diagnostic)
    ⇒ 全部注入
```

★★ **⇒ 三层委托：最外层只给 2 个参数,最内层给 6 个。**

### ★★★ `IServer.hpp` 只有 3 行

```cpp
#pragma once
#include "../shared/LocalnetServer.hpp"
```

★ **⇒ 纯转发头（`IServer` 的真实定义在 `shared\LocalnetServer.hpp`，报告 093 已记录 2019 Ayria ABI）。**

---

## 八、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **`SchemaVersion`** | **2**（每条房间消息首字节） |
| 2 | ★★★★★ **`ConnectRequest`** | **12 + N**：`[0]`ver · `[1..8]`u64 userId · `[9..10]`u16 bridgePort · `[11]`u8 nameLen · `[12..]`name |
| 3 | ★★★★★ **`MemberRequest`** | **17**：`[0]`ver · `[1..8]`u64 userId · `[9..16]`u64 token |
| 4 | ★★★ **`ReadyRequest`** | **18** = MemberRequest + `[17]`u8 ready |
| 5 | ★★★ **`SessionDescriptorRequest`** | **17 + N** = MemberRequest + descriptor |
| 6 | ★★★★★ **`FreezeRequest`** | **25**：`[0]`ver · `[1..8]`generation · `[9..16]`claimant.userId · `[17..24]`claimant.token |
| 7 | ★★★ **`encodeToken`** | **9**：`[0]`ver · `[1..8]`u64 token |
| 8 | ★★★★★ **`FrozenRoomRoster`** | **18 + Σ(24+N)**：`[0]`ver · `[1..8]`generation · `[9..16]`ownerUserId · `[17]`u8 成员数 |
| 9 | ★★★★★ **成员记录 24B** | `[0..7]`u64 userId · `[8..9]`u16 bridgePort · **`[10..13]`u32 bridgeIpv4** · `[14..21]`u64 connectionToken · `[22]`u8 ready(≤1) · `[23]`u8 nameLen(≠0) · `[24..]`name |
| 10 | ★★ 解码终检 | `generation != 0` && `ownerUserId != 0` && **`offset == input.size()`** |
| 11 | ★★★★★ **`DefaultPort = 28970`** | 房间主控口（**区别于专服 28961 / bridge 28962**） |
| 12 | ★★ 环境变量 | ★ **`OLMOD_ROOM_OWNER_PORT`**（第 30 个 `OLMOD_*`） |
| 13 | ★★★★★ **`connect` 五个拒绝条件** | `!userId` / `!bridgePort` / 名字非法 / (**新成员**且满) / **`(port, ipv4)` 二元组重复** |
| 14 | ★★★ 容量检查的措辞 | `!members_.contains(userId) && size >= capacity_` ⇒ **已有成员重连不检查容量** |
| 15 | ★★★★★ **`capacity = 18`** | 与 `MaximumSessionMembers = 18`（报告 095）**一致** |
| 16 | ★★★★★ **`validDisplayName`** | 长度 ≤ **16**；字符 **`>= 0x20 && != 0x7F`**（**允许 GBK 高位**） |
| 17 | ★★★★ GBK 反例 | `Lifetime丷` 的 GBK 尾部 = **`81 52`**；老实现 **0x7E 上限**会拒 ⇒ **room owner 连接失败** |
| 18 | ★★★★★ **`freeze` 五个分支** | ①已冻结⇒幂等返回 ②任一未 ready⇒拒 ③token 不符⇒拒 ④**首次认领⇒`allocationOwnerUserId_` 粘住** ⑤无认领⇒取首个成员 |
| 19 | ★★★★★ **房主粘性** | 首次成功 `freeze` 的 claimant **成为永久 owner**；后续认领者的身份**被忽略** |
| 20 | ★★ `frozenRosters_` | `std::map<u64, FrozenRoomRoster>` ⇒ **多代并存** |
| 21 | ★★★★★ **`canonicalSessionDescriptor_` 首次即定案** | 只在空时写；后续传入**被静默丢弃**；`connect`/`disconnect` 才 reset |
| 22 | ★★★ `SharedRoomClient` 五操作 | `RoomConnect` / `RoomDisconnect` / `RoomSetReady` / `RoomFreeze` / `RoomCanonicalizeSession` |
| 23 | ★★ `ownerHost()` 不缓存 | "a cached copy would silently outlive a change to it" |
| 24 | ★★★ connect 失败日志 | `shared room connect rejected user=<id> bridge=<port> delivered=<0\|1> status=<n> token=<0\|1>` |
| 25 | ★★★★ **`SharedRoomHost` 是独立进程** | 绑 **`0.0.0.0`**（远端）/ 回环（本机），端口 **28970**，`Sleep(100)` 主循环 |
| 26 | ★★ 三个控制事件 | `CTRL_C_EVENT` / `CTRL_BREAK_EVENT` / `CTRL_CLOSE_EVENT` |
| 27 | ★★★★ **`ol-room-owner.log`** | `[YYYY-MM-DD HH:MM:SS.mmm] [room-owner] <event> user= bridge= members= ready= accepted=` |
| 28 | ★★ 五个日志事件 | `connect` / `disconnect` / `ready` / `unready` / `freeze` |
| 29 | ★★ 独立日志的理由 | "observable **without parsing the game's unbounded backend log**" |
| 30 | ★★★ **五个回调类型** | `Diagnostic` / `EntitlementCheck` / `RosterProvider` / `MatchRulesProvider` / `ControlSubmit` |
| 31 | ★★★ `ControlSubmit` 的注释 | "**The address leads because it is the half that used to be missing**" |
| 32 | ★★ 三层委托构造 | 2 参数 → 4 参数 → **6 参数** |
| 33 | ★★ `IServer.hpp` | 3 行纯转发（真实定义在 `shared\LocalnetServer.hpp`） |

---

## 九、结论

### 1. ★★★★★ **房间协议是 `DedicatedControl` 之上的第二套 schema（`SchemaVersion = 2`）**

★ **⇒ 六种消息,长度分别 12+N / 17 / 18 / 17+N / 25 / 9 / 18+Σ(24+N)。**

### 2. ★★★★★ **端口 **28970** 是第三个端口**（专服 28961 / bridge 28962 / 房间 28970）

### 3. ★★★★★ **`connect` 的重复判定从"端口"改为"**(port, ipv4) 二元组**"

★ **⇒ 与报告 124 的 "THE PAIR, NOT THE PORT" 同源：两个朋友各自默认端口 28962 不再冲突。**

### 4. ★★★★★ **`freeze` 的 `allocationOwnerUserId_` 使房主身份**粘性**

★ **⇒ 只有首个成功认领者能当房主；后续认领者的身份被忽略。**

### 5. ★★★★★ **`canonicalSessionDescriptor_` 首次写入即定案,后续静默丢弃**

### 6. ★★★★ **`SharedRoomHost` 是独立可执行程序**,日志写 `Logs\ol-room-owner.log`

### 7. ★★★ **GBK 名字的 0x7E 上限是真实故障点**（`Lifetime丷` 的 `81 52`）

### 8. ★★★★★ **`backend` 根 13 文件全部完成**

| # | 文件 | 字节 | 报告 |
|---|---|---|---|
| 1 | `DedicatedBookingDispatcher.cpp` | 47,443 | **124** |
| 2 | `Servers.cpp` | 30,698 | **123** |
| 3 | `SharedRoomControl.cpp` | 17,524 | ★ **125** |
| 4 | `SharedRoomClient.cpp` | 6,757 | ★ **125** |
| 5 | `SharedRoomSessionOwner.cpp` | 6,206 | ★ **125** |
| 6 | `Servers.hpp` | 4,781 | **123** |
| 7 | `Appmain.cpp` | 3,184 | **123** |
| 8 | `SharedRoomControl.hpp` | 2,814 | ★ **125** |
| 9 | `DedicatedBookingDispatcher.hpp` | 2,595 | ★ **125** |
| 10 | `SharedRoomSessionOwner.hpp` | 2,428 | ★ **125** |
| 11 | `SharedRoomHost.cpp` | 1,586 | ★ **125** |
| 12 | `SharedRoomClient.hpp` | 1,327 | ★ **125** |
| 13 | `IServer.hpp` | 54 | ★ **125** |
| **合计** | — | **127,397** | **3 份报告（123–125）** |

★ **⇒ 与报告 122 的目录统计 **127,397 B** 完全吻合 ✓**

---

## 十、下一步

`backend` 全部完成。接下来 **`game_server` 根 32 文件（2,175,797 B）**，按大小：

1. ★ **`EngineBindings.cpp`（917,344 B）** + `EngineBindings.hpp`（133,088 B）
2. ★ **`Appmain.cpp`（565,999 B）**
3. `NativePmoveBindings.cpp`（113,000）+ `NativeWeaponMovementBindings.cpp`（31,427）
4. `ClientProcessPatches.cpp`（82,545）+ `.hpp`（13,278）
5. `ClientAnimtreeHook.cpp`（40,829）+ `.hpp`（2,206）
6. `DedicatedProcessPatches.cpp`（39,058）+ `.hpp`（2,898）
7. `ClientRenderFrameHook.cpp`（32,154）+ `.hpp`（9,126）
8. `ClientCommandTrace.cpp`（27,720）+ `.hpp`（4,450）
9. `DisconnectWitness.cpp`（25,594）+ `.hpp`（514）
10. `NativeWeaponBindings.cpp`（17,835）
11. `codol_bot_names.hpp`（16,545）/ `codol_bot_classes.hpp`（6,021）
12. `PlayerDataDef.cpp/.hpp`（13,451 / 9,564）
13. `ClientNoclipHotkey.cpp/.hpp`（11,734 / 804）
14. `NativeEntityStateBindings.cpp`（9,299）
15. `SessionAssetRegistry.hpp`（6,580）/ `GameStateConfiguration.hpp`（6,210）
16. `DedicatedSessionConsumption.hpp`（3,393）/ `FrameHook.cpp/.hpp`（2,053 / 246）
17. `ClientBatteryLookup.hpp`（1,041）
18. ★ `NativeWeaponMovementBindings.cpp.bak-20261009-scopeidle`（29,791）—— **交付包内唯一 `.bak`**，需单独确认
