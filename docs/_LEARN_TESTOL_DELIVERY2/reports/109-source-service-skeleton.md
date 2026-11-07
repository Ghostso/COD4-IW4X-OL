# 学习报告 109（重开）— `Demonware` 的服务骨架（ServiceRegistry / AckOnlyServices / CodolStartupTasks / RecoveredCatalog）

**学习范围**：`ServiceRegistry.hpp`（69 行）+ `.cpp`（74）+ `AckOnlyServices.hpp`（45）+ `.cpp`（65）+ `CodolStartupTasks.hpp`（8）+ `.cpp`（56）+ `RecoveredCatalog.hpp`（26）+ `.cpp`（60）
**性质**：全实测（**8 文件逐行读完**）
**★★★★★ 本报告收录六个重大发现**：①**完整的 27 个服务目录（含 2019-12-08 DLL 的 RVA）** ②**`OriginalTransactionPrefix = 0x797265766E6F4300`（"Corevy"）** ③**"只推不回"的 Python 出处与 `suppressReply`** ④**`acknowledgeUnhandled` 的实测数据（27 次重试 vs 12 次）** ⑤**11 个 AckOnly 任务的精确载荷形状** ⑥**`AckOnlyServices` 的一段**自我更正**

---

## 一、★★★★★ **完整的 27 个服务目录（RecoveredCatalog）**

### 1.1 ★★★★★ 来源声明（逐字）

```cpp
// Recovered from every xref to Alwaysoffline sub_10035B81. RVAs point to
// the service dispatchers in the **2019-12-08 x86 DLL (image base 0x10000000)**.
```

★★★ **⇒ 完整的血统：**
```
**2019-12-08 的 x86 DLL**
镜像基址 **`0x10000000`**
函数 **`sub_10035B81`** 的**所有交叉引用**
        ↓
★★★ ⇒ 即：**从 2019 年那个 Ayria DLL 里反推出来的服务目录**
```

### ★★★★★ 完整的 27 个服务（6 auth + 21 lobby）

#### Auth 端点（6 个）

| # | ID | RVA | 名称 |
|---|---|---|---|
| **1** | **`0x1A`** | `0x03758B` | `UnknownAuth1A` |
| **2** | **`0x07`** | `0x037C6A` | `UnknownAuth07` |
| **3** | **`0x00`** | `0x038AA3` | `UnknownAuth00` |
| **4** | **`0x0A`** | `0x039373` | `UnknownAuth0A` |
| **5** | **`0x0C`** | `0x039956` | `UnknownAuth0C` |
| **6** | **`0x1C`** | `0x03A090` | ★★ **`SteamTicketAuth`** |

#### Lobby 端点（21 个）

| # | ID | RVA | 名称 |
|---|---|---|---|
| **7** | **`0x47`** | `0x03AA63` | ★★★ **`Tencent`** |
| **8** | `0x21` | `0x03B6B0` | `Unknown21` |
| **9** | `0x32` | `0x03E23E` | `Unknown32` |
| **10** | `0x43` | `0x03FB77` | `Unknown43` |
| **11** | **`0x50`** | `0x04284C` | ★★★ **`Marketplace`** |
| **12** | **`0x0A`** | `0x04B5B9` | ★★★ **`Storage2`** |
| **13** | `0x12` | `0x04BE08` | `Unknown12` |
| **14** | `0x1B` | `0x04C493` | `Unknown1B` |
| **15** | **`0x15`** | `0x04D2EC` | ★★★ **`Matchmaking`** |
| **16** | **`0x8A`** | `0x04D555` | ★★ **`Matchmaking2`** |
| **17** | **`0x09`** | `0x04EB2F` | ★★★ **`Friends2`** |
| **18** | **`0x06`** | `0x051C27` | ★★ **`BandwidthTest`** |
| **19** | **`0x0B`** | `0x051C90` | ★★★ **`Unknown0B`** |
| **20** | `0x66` | `0x051D4F` | `Unknown66` |
| **21** | **`0x08`** | `0x053742` | ★★★ **`Profiles2`** |
| **22** | **`0x44`** | `0x053AFA` | ★★ **`RichPresence`** |
| **23** | **`0x0C`** | `0x054624` | ★★ **`TitleUtilities2`** |
| **24** | `0x26` | `0x054F74` | `Unknown26` |
| **25** | `0x17` | `0x0551A5` | `Unknown17` |
| **26** | **`0x1C`** | `0x055866` | ★★ **`ContentUnlock2`** |
| **27** | `0x0F` | `0x056083` | `Unknown0F` |

### ★★★★★ 与报告 090 的 15 个服务类对照

```
报告 090（RTTI 类名）：MatchmakingService / Profiles2Service / Storage2Service /
  StatsService / MarketplaceService / ClanService / VClanService / Friends2Service /
  InstantMessageService / TencentService / TitleUtilitiesService / ContentUnlock2Service /
  Unknown0BService（+ Auth3Server / LobbyServer / StunServer / PendingStreamServer）
        ↓
★★★★★ 本报告（服务 ID 目录）：
  `0x47` = **Tencent** ✓
  `0x50` = **Marketplace** ✓
  `0x0A` = **Storage2** ✓
  `0x15` = **Matchmaking** ✓
  `0x09` = **Friends2** ✓
  `0x08` = **Profiles2** ✓
  `0x0B` = ★★★ **`Unknown0B`** ✓ **（报告 090 的 `Unknown0BService` 就是 `0x0B`）**
  `0x1C`(lobby) = **ContentUnlock2** ✓
  `0x0C`(lobby) = **TitleUtilities2** ✓
  `0x44` = **RichPresence** ✓
        ↓
★★★ ⇒ **10 个名字完全对应** ✓
```

★★★ **⇒ 且解决了报告 090 的一个悬案：**
```
报告 090：`Unknown0BService` 名字未知（"0B" 可能是 opcode/编号）
        ↓
★★★★★ 本报告：**`0x0B` 是服务 ID**（lobby 端点,RVA `0x051C90`）
   ⇒ 名字里的 "0B" **就是服务编号** ✓
```

### ★★★★★ 三个**新发现**的服务

| ID | 名称 | 说明 |
|---|---|---|
| **`0x1C`**(auth) | ★★ **`SteamTicketAuth`** | ★★★ **Steam 票据认证**（CODOL 有 Steam 版？） |
| **`0x06`** | ★★ **`BandwidthTest`** | 带宽测试 |
| **`0x8A`** | ★★ **`Matchmaking2`** | 第二个 matchmaking |

★★ **⇒ `SteamTicketAuth` 是一个**重要发现**（CODOL 的 Steam 版本路径）。**

### ★★★ 14 个 `Unknown*` 服务

```
`UnknownAuth1A` / `UnknownAuth07` / `UnknownAuth00` / `UnknownAuth0A` / `UnknownAuth0C`
`Unknown21` / `Unknown32` / `Unknown43` / `Unknown12` / `Unknown1B`
`Unknown0B` / `Unknown66` / `Unknown26` / `Unknown17` / `Unknown0F`
        ↓
★★★ ⇒ **15 个未命名**（27 − 12 个有名字 = 15）
```

★★ **⇒ 注：`Unknown0B` 现在可以**正式命名为 "服务 0x0B"**（名字就是编号）。**

---

## 二、★★★★★ **`OriginalTransactionPrefix = 0x797265766E6F4300`（"Corevy"）**

### 2.1 ★★★★★ 完整常量（`ServiceRegistry.hpp:13`）

```cpp
inline constexpr std::uint64_t OriginalTransactionPrefix = **0x797265766E6F4300**ULL;
```

### ★★★★★ 十六进制解码（小端）

```
`0x797265766E6F4300`
        ↓ 按字节（小端）
`00 43 6F 6E 76 65 72 79`
        ↓ 去掉前导 00,其余是 ASCII
**`C o n v e r y`**
        ↓
★★★★★ ⇒ **`"Convery"`**（7 个字符 + 1 个前导零字节）
```

★★★ **⇒ 事务 ID 的前缀是字符串 **`"Convery"`**。**

★★ **⇒ 可能是**作者名**或**项目代号**（与 `Hedgehogscience` 并列）。**

### ★★★ 事务 ID 的构造（`stampTransaction`，第 60–67 行）

```cpp
void ServiceRegistry::stampTransaction(ServiceResponse &response) const
{
    if (response.transaction != 0) return;                        // ★ 已有则不覆盖
    const auto counter = static_cast<std::uint8_t>(nextTransaction_.fetch_add(1) + 1);
    response.transaction = **OriginalTransactionPrefix | counter**;   // ★ 前缀 | 8 位计数
}
```

★★★★★ **⇒ 事务 ID = `0x797265766E6F4300 | (8 位计数器)`**
**⇒ 即：**只有最低字节是变化的**,高 7 字节固定为 `"Convery"`。**

★★ **⇒ 计数器是 **`std::uint8_t`** ⇒ **每 256 次回绕**（可能有意,也可能是个隐患）。**

---

## 三、★★★★★ **"只推不回"（`suppressReply`）的完整出处**

### 3.1 ★★★★★ 完整注释（`ServiceRegistry.hpp:33-44`，逐字）

```cpp
// ★ 2026-10-05 22:5x -- LOCAL OVERRIDE (DSH): "只推不回".
//
// Provenance is the PYTHON baseline that actually reached maps,
// `Workmd\10-current\CODOL_ROUTE_ORIGINAL\lobby_server.py`:
//     :291  _FLAGS["skip_ack"] = True      # ★ 只推不回（见 _FLAGS 定义处）
//     :1616 skip_ack = _FLAGS["skip_ack"]; _FLAGS["skip_ack"] = False
//     :1622 if skip_ack:  <skip sending the 0x85 reply>
// Its `0x06/14` `mmbook` branch pushes event 21 "mmbook accepted" and sends NO 0x85 at all.
// Upstream's C++ cannot express that (every ServiceResponse is answered), which is why this
// flag exists.  Only `InstantMessageService::task14` sets it, and only for `mmbook`.
bool suppressReply{ false };
```

### ★★★★★ 三条精确出处（Python 行号）

| 行 | 代码 |
|---|---|
| **`:291`** | `_FLAGS["skip_ack"] = True` |
| **`:1616`** | `skip_ack = _FLAGS["skip_ack"]; _FLAGS["skip_ack"] = False` |
| **`:1622`** | `if skip_ack: <skip sending the 0x85 reply>` |

★★★ **⇒ 完整的机制：**
```
`0x06/14`（**service 0x06, task 14**）的 **`mmbook`** 分支
   ⇒ **推送事件 21 "mmbook accepted"**
   ⇒ ★★★ **完全不发 `0x85` 回复**
        ↓
★★★ 而"上游的 C++ 无法表达这一点"（"every ServiceResponse is answered"）
   ⇒ 所以加了 `suppressReply` 标志
        ↓
★★★ 且**只有 `InstantMessageService::task14` 会设它,且只对 `mmbook`**
```

★★★★★ **⇒ 三条关键信息：**
```
① ★★★ **`0x06/14` = `InstantMessageService::task14`**（服务 ID **`0x06`**,任务 **`14`**）
② ★★ **事件 21 = "mmbook accepted"**
③ ★★★ **`0x85` 是回复包的类型字节**（与报告 044 的 "lobby_server.py gates on it before sending 0x81" 呼应）
```

★★ **⇒ 注意：报告 044 记的是 `0x81`,这里是 `0x85`。**
**⇒ 两个不同的回复类型（`0x81` 与 `0x85`）⇒ 记录为**精确差异**。**

---

## 四、★★★★★ **`acknowledgeUnhandled` 的实测数据**

### 4.1 ★★★★★ 完整注释（`ServiceRegistry.hpp:44-52`，逐字）

```cpp
/// The reply an unregistered task gets: error 0, zero results, and a transaction id
/// from the same counter a handled task would have drawn.
///
/// This is not a courtesy. The C# OLfinal lobby server answers EVERY task this way
/// (Client.cs, `if (!handled) SendTaskReply(taskId)`), and that server is the one that
/// has actually driven an OLfinal client to the menu. Staying silent instead is not a
/// smaller version of the same behaviour -- it is a different one, and the client
/// responds to it by retrying: **27 requests for service 4 task 13 in a single measured
/// session, against 12 for a task that is answered**.
```

### ★★★★★ 精确的实测对比

```
**未应答**（保持沉默）⇒ **27 次请求**（service **4**, task **13**）
**已应答**           ⇒ **12 次请求**
        ↓
★★★★★ ⇒ **沉默导致 27/12 = 2.25 倍的重试**
```

★★★ **⇒ 关键洞察（逐字）：**
```
"Staying silent instead is **not a smaller version of the same behaviour --
 it is a different one**, and the client responds to it by **retrying**"
```

★★ **⇒ 这是**"静默 ≠ 简化"的精确论证**（与报告 104 的 "absent 与 ambiguous 不是同一答案"**同一类**）。**

### ★★★ C# 参考的出处

```
"The **C# OLfinal lobby server** answers EVERY task this way
 (**`Client.cs`, `if (!handled) SendTaskReply(taskId)`**),
 and **that server is the one that has actually driven an OLfinal client to the menu**."
        ↓
★★★ ⇒ **C# 版是"真正把 OLfinal 客户端带到菜单"的那个实现** ⇒ 权威
```

---

## 五、★★★★★ **11 个 AckOnly 任务的精确载荷形状**

### 5.1 ★★★★★ 完整表（`AckOnlyServices.cpp`）

```cpp
AckTask{ 0x03, 53, "Teams::getIncomingProposals" },   // x1
AckTask{ 0x03, 46, "Teams::task46" },                 // x8
AckTask{ 0x03, 48, "Teams::task48" },                 // x8
AckTask{ 0x1D, 10, "Mail::getUnreadCount" },          // x1
AckTask{ 0x44,  3, "RichPresence::setPresence" },     // x15
AckTask{ 0x66,  1, "Messaging2::task1" },             // x13
AckTask{ 0x66,  2, "Messaging2::task2" },             // x2
AckTask{ 0x66,  5, "Messaging2::task5" },             // x7
AckTask{ 0x66,  7, "Messaging2::task7" },             // x10
```

### ★★★★★ 完整的 9 个任务与载荷形状

| 服务 | 任务 | 名称 | 次数 | **载荷形状** |
|---|---|---|---|---|
| **`0x03`** | **53** | `Teams::getIncomingProposals` | **1** | — |
| **`0x03`** | **46** | `Teams::task46` | **8** | ★★ `(string "", u64 0, string "", u32 10, u32 0)` |
| **`0x03`** | **48** | `Teams::task48` | **8** | ★★ `(string "", u64 0, string "", u32 0, u32 100, u32 0)` |
| **`0x1D`** | **10** | `Mail::getUnreadCount` | **1** | ★ `(string "", u32 0, u32 100, bool true)` |
| **`0x44`** | **3** | `RichPresence::setPresence` | ★ **15** | ★★ `(string "", u64 userId, string "", u8 1, blob{...,"EDITz"})` |
| **`0x66`** | **1** | `Messaging2::task1` | **13** | ★ `(u32 0, u32 1, u8 3, u64 0)` |
| **`0x66`** | **2** | `Messaging2::task2` | **2** | ★★★ **无载荷**（整帧 = `04000000 86 66 03 02`） |
| **`0x66`** | **5** | `Messaging2::task5` | **7** | ★ `(u32 2, u8 1, u8 2)` |
| **`0x66`** | **7** | `Messaging2::task7` | **10** | ★★ `(u32 50)` + 50 × `(u8 1, u64 i)`（i = 0..49） |

### ★★★★★ 三个精确观察

```
① ★★★ **`Messaging2::task2` 的整帧是 `04 00 00 00 86 66 03 02`**
   ⇒ 解码：
     `04 00 00 00` ⇒ 某 4 字节字段（可能是 transaction 或长度）
     `86`         ⇒ ★ **服务 `0x66` + 高位?**（或是一个标志）
     `66`         ⇒ 服务 ID
     `03`         ⇒ ★ **协议版本 3**（与 `parseServiceRequest` 的 `protocolVersion != 3` 校验吻合）
     `02`         ⇒ 任务 ID
        ↓
★★★ ⇒ **8 字节的最短请求帧**
        ↓
② ★★★ **`RichPresence::setPresence` 的 blob 里含 `"EDITz"`**
   ⇒ 一个**可见的字符串标记**
        ↓
③ ★★ **`Messaging2::task7` 是批量查询**（50 个索引 0..49）
```

### ★★★★★ `AckOnlyServices.hpp` 的一段**自我更正**（逐字）

```cpp
/// PROVENANCE, and a correction. An earlier version of this file said these were "handled
/// by the C# OLfinal LobbyServer". **They are not, in the sense that mattered**: Messaging2.cs,
/// RichPresence.cs and Mail.cs exist in that server but **have no arm in Client.cs's service
/// switch**, so they **never run**. What actually answered these was the **same universal
/// fallback** this backend has now -- `if (!handled) SendTaskReply(taskId)`. The bytes on the
/// wire were always the empty reply; **only the route was wrong in the comment**. The claim
/// that survives is the one that was always the real evidence: **an OLfinal client received
/// an empty reply for each of these and went on to draw the menu**.
```

★★★★★ **⇒ 一段极其诚实的更正：**
```
旧注释说这些是"C# OLfinal LobbyServer 处理的"
        ↓
★★★ 更正：**"They are not, in the sense that mattered"**
   ⇒ `Messaging2.cs` / `RichPresence.cs` / `Mail.cs` **存在但没有被 `Client.cs` 的 switch 调用**
   ⇒ 所以**从未运行**
        ↓
★★★ 实际回答它们的是**同一个通用兜底**：`if (!handled) SendTaskReply(taskId)`
        ↓
★★★★★ 结论（逐字）："**The bytes on the wire were always the empty reply;
 **only the route was wrong in the comment**.**"
   ⇒ "The claim that survives is ... **an OLfinal client received an empty reply
      for each of these and went on to draw the menu**."
```

★★ **⇒ 这是**"证据对但归因错"的精确区分**（与报告 083 的"结论对、证据错"同类）。**

### ★★★ 注册顺序的意义（逐字）

```cpp
/// SEVERAL OF THESE ALSO APPEAR IN CodolStartupTasks' recovered-capture table, and that
/// overlap is deliberate. Registration is **insert_or_assign** and this service registers
/// **LAST** (Servers.cpp), so **these entries win** -- which changes **nothing on the wire**
/// (both send the empty reply) and **everything in the log**, where `RecoveredEmpty::0x03/0x2E`
/// becomes `Teams::task46`. The startup table's provenance is a **3.3.3.3-era startup capture**;
/// these are from an **OLfinal client at the menu**. Both are real, and **the more specific
/// name wins**.
```

★★★★★ **⇒ 两套表的**重叠是刻意的**：**
```
`CodolStartupTasks`（**3.3.3.3 时代**的启动捕获）
`AckOnlyServices`（**OLfinal 客户端在菜单时**）
        ↓
★★★ 重叠的条目：**线上字节相同**（都是空回复）
   ⇒ **只有日志名不同**（`RecoveredEmpty::0x03/0x2E` → `Teams::task46`）
        ↓
★★★ 注册顺序：`AckOnlyServices` **最后注册** ⇒ **它的名字胜出**
```

---

## 六、★★★★★ **`CodolStartupTasks` 的 22 个空任务**

### 6.1 ★★★ 完整列表

```cpp
EmptyTask{ 0x47, 0x04, "RecoveredEmpty::0x47/0x04" },
EmptyTask{ 0x47, 0x0A, "RecoveredEmpty::0x47/0x0A" },
EmptyTask{ 0x50, 0x46, "RecoveredEmpty::0x50/0x46" },
EmptyTask{ 0x47, 0x03, "RecoveredEmpty::0x47/0x03" },
EmptyTask{ 0x06, 0x05, "RecoveredEmpty::0x06/0x05" },
EmptyTask{ 0x50, 0x6B, "RecoveredEmpty::0x50/0x6B" },
EmptyTask{ 0x50, 0xE6, "RecoveredEmpty::0x50/0xE6" },
EmptyTask{ 0x5D, 0x01, "**Unknown93::task1**" },        ← ★ 服务 0x5D = 93
EmptyTask{ 0x09, 0x10, "RecoveredEmpty::0x09/0x10" },
EmptyTask{ 0x44, 0x01, "RecoveredEmpty::0x44/0x01" },
EmptyTask{ 0x09, 0x0E, "RecoveredEmpty::0x09/0x0E" },
EmptyTask{ 0x03, 0x35, "RecoveredEmpty::0x03/0x35" },
EmptyTask{ 0x1D, 0x0A, "RecoveredEmpty::0x1D/0x0A" },
EmptyTask{ 0x50, 0xAD, "RecoveredEmpty::0x50/0xAD" },
EmptyTask{ 0x50, 0xAE, "RecoveredEmpty::0x50/0xAE" },
EmptyTask{ 0x66, 0x01, "RecoveredEmpty::0x66/0x01" },
EmptyTask{ 0x09, 0x09, "RecoveredEmpty::0x09/0x09" },
EmptyTask{ 0x09, 0x0C, "RecoveredEmpty::0x09/0x0C" },
EmptyTask{ 0x47, 0x07, "RecoveredEmpty::0x47/0x07" },
EmptyTask{ 0x03, 0x2E, "RecoveredEmpty::0x03/0x2E" },
EmptyTask{ 0x03, 0x30, "RecoveredEmpty::0x03/0x30" },
EmptyTask{ 0x47, 0x0F, "RecoveredEmpty::0x47/0x0F" },
```

★★★ **⇒ **22 个**空任务,其中 **21 个**命名 `RecoveredEmpty::<svc>/<task>`,**1 个**命名 `Unknown93::task1`。**

### ★★★ 来源声明（逐字）

```cpp
// Every entry below was observed returning a **type-1 empty-success envelope**
// in the **recovered CODOL startup capture**.
```

★★ **⇒ 全部来自**一次启动捕获**（"type-1 empty-success envelope"）。**

### ★★★ 一个命名异常

```cpp
EmptyTask{ **0x5D**, 0x01, "**Unknown93::task1**" },
```

★★★ **⇒ 服务 `0x5D` = **十进制 93** ⇒ 名字 `Unknown93` 用的是**十进制**。**
**⇒ 而其余用**十六进制**（`0x47` 等）。**
**⇒ 命名不一致（记录为精确差异）。**

---

## 七、★★★★ **`ServiceResponse::serialize` 的精确格式**

### 7.1 ★★★ 完整实现（第 17–38 行）

```cpp
std::vector<std::uint8_t> ServiceResponse::serialize() const
{
    ByteBuffer output;
    output.writeU64(transaction);                    // ★ u64 + 类型 0x0A
    output.writeU32(error);                          // ★ u32 + 类型 0x08
    output.writeU8(task);                            // ★ u8  + 类型 0x03
    if (error != 0)
    {
        output.writeU64(transaction);                // ★★ 错误时重复 transaction
        return output.data();
    }

    output.writeU32(objects.size());                 // ★ 对象数
    if (!objects.empty())
    {
        output.writeU32(objects.size());             // ★★ 再写一次（重复!）
        for (const auto &object : objects)
            output.writeRaw(object);
    }
    return output.data();
}
```

### ★★★★★ 四个精确观察

```
① ★★★ **对象数被写**两次**（`objects.size()` 出现两遍）
   ⇒ 可能是"总字节数" + "对象数",但代码里都是 `objects.size()`
        ↓
★★★ ② **错误时只写 `transaction` 两次**,没有对象段
        ↓
③ ★★ **所有写入都带类型前缀**（`writeU64`/`writeU32`/`writeU8` 会写 `0x0A`/`0x08`/`0x03`）
        ↓
④ ★★★ **`writeRaw(object)` 不带类型前缀** ⇒ 对象是**原始字节**
```

★★ **⇒ 第 ① 条可能是**bug**（两处都写 `objects.size()`）,也可能第一个本应是**字节数**。**
**⇒ 记录为**待核对项**。**

### ★★★ `parseServiceRequest` 的协议版本校验（第 5–16 行）

```cpp
if (decoded.size() < 3) return std::nullopt;
ServiceRequest request{
    .service = decoded[0],
    .protocolVersion = decoded[1],
    .task = decoded[2],
    .payload = ...(decoded.begin() + 3, decoded.end()),
};
if (request.protocolVersion != **3**) return std::nullopt;      // ★★ 必须 = 3
```

★★★ **⇒ 请求头是 **3 字节**：`service(1) + protocolVersion(1) + task(1)`,**版本必须 = 3**。**
**⇒ 与报告 109 第五节 `Messaging2::task2` 的帧 `86 66 03 02` 里 `03` 是版本**完全吻合** ✓**

---

## 八、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **27 个服务目录** | **6 auth + 21 lobby**，来自 **2019-12-08 x86 DLL（基址 `0x10000000`）** 的 `sub_10035B81` 所有 xref |
| 2 | ★★★ 有名字的 12 个 | `SteamTicketAuth`(0x1C/auth) / `Tencent`(0x47) / `Marketplace`(0x50) / `Storage2`(0x0A) / `Matchmaking`(0x15) / `Matchmaking2`(0x8A) / `Friends2`(0x09) / `BandwidthTest`(0x06) / **`Unknown0B`(0x0B)** / `Profiles2`(0x08) / `RichPresence`(0x44) / `TitleUtilities2`(0x0C) / `ContentUnlock2`(0x1C/lobby) |
| 3 | ★★★★★ **`Unknown0B` 的悬案解决** | 报告 090 的 `Unknown0BService` ⇒ **`0x0B` 就是服务 ID** ✓ |
| 4 | ★★★ **三个新发现** | ★★ **`SteamTicketAuth`** / **`BandwidthTest`** / **`Matchmaking2`** |
| 5 | ★★ 15 个 `Unknown*` | 未命名的服务（27 − 12 = 15） |
| 6 | ★★★★★ **`OriginalTransactionPrefix`** | **`0x797265766E6F4300`** ⇒ 小端解码 = **`00 43 6F 6E 76 65 72 79`** = **`"Convery"`** |
| 7 | ★★★ 事务 ID 构造 | `prefix \| (uint8 计数器)` ⇒ **只有最低字节变化**；计数器 **8 位 ⇒ 每 256 次回绕** |
| 8 | ★★★★★ **"只推不回"的 Python 出处** | `lobby_server.py` **`:291`** `_FLAGS["skip_ack"]=True` / **`:1616`** 读取后清零 / **`:1622`** `if skip_ack: <skip 0x85>` |
| 9 | ★★★ 适用范围 | **只有 `InstantMessageService::task14`**（服务 **`0x06`**,任务 **`14`**）设 `suppressReply`,且**只对 `mmbook`** |
| 10 | ★★ 事件 21 | **"mmbook accepted"** |
| 11 | ★★★ 回复类型 | **`0x85`**（注意与报告 044 的 `0x81` **不同**） |
| 12 | ★★★★★ **`acknowledgeUnhandled` 的实测** | **沉默 ⇒ 27 次请求**（service **4**, task **13**）vs **已应答 ⇒ 12 次** |
| 13 | ★★★★★ 洞察 | "Staying silent is **not a smaller version of the same behaviour -- it is a different one**" |
| 14 | ★★★ C# 权威出处 | `Client.cs` 的 **`if (!handled) SendTaskReply(taskId)`**；"that server is the one that **has actually driven an OLfinal client to the menu**" |
| 15 | ★★★★★ **9 个 AckOnly 任务** | `0x03/53`(×1) `0x03/46`(×8) `0x03/48`(×8) `0x1D/10`(×1) `0x44/3`(**×15**) `0x66/1`(×13) `0x66/2`(×2) `0x66/5`(×7) `0x66/7`(×10) |
| 16 | ★★★★★ **`Messaging2::task2` 整帧** | **`04 00 00 00 86 66 03 02`**（**8 字节最短帧**）⇒ `03` 是协议版本 ✓ |
| 17 | ★★ `RichPresence::setPresence` 载荷 | `(string "", u64 userId, string "", u8 1, blob{...,**"EDITz"**})` |
| 18 | ★★ `Messaging2::task7` | `(u32 50)` + 50 × `(u8 1, u64 i)` ⇒ **批量按索引查询** |
| 19 | ★★★★★ **一段自我更正** | 旧注释说"C# LobbyServer 处理"⇒ 更正："**They are not, in the sense that mattered**"（`Messaging2.cs`/`RichPresence.cs`/`Mail.cs` **没有 `Client.cs` 的 switch 分支** ⇒ **从未运行**）；"**The bytes on the wire were always the empty reply; only the route was wrong in the comment**" |
| 20 | ★★★★ **两套表的重叠是刻意的** | `CodolStartupTasks`（**3.3.3.3 时代**）与 `AckOnlyServices`（**OLfinal 菜单时**）；**线上字节相同**,只**日志名不同**；`AckOnlyServices` **最后注册** ⇒ 名字胜出 |
| 21 | ★★★ **22 个空任务** | 21 个 `RecoveredEmpty::<svc>/<task>` + 1 个 `Unknown93::task1`（服务 **`0x5D` = 93**,★ 用**十进制**命名,与其余**十六进制不一致**） |
| 22 | ★★ 来源 | "**type-1 empty-success envelope** in the recovered CODOL startup capture" |
| 23 | ★★★★ **`serialize` 的四个观察** | ①**`objects.size()` 被写两次**（待核对）②错误时只写 `transaction` 两次 ③所有写入带类型前缀 ④`writeRaw(object)` **不带前缀** |
| 24 | ★★★ **请求头 3 字节** | `service(1) + protocolVersion(1) + task(1)`，**版本必须 = 3** |

---

## 九、结论

### 1. ★★★★★ **27 个服务的完整目录被恢复,含 2019-12-08 DLL 的精确 RVA**

★ **⇒ 且解决了报告 090 的 `Unknown0BService` 悬案（`0x0B` 就是服务 ID）。**
**★ ⇒ 三个新发现：`SteamTicketAuth` / `BandwidthTest` / `Matchmaking2`。**

### 2. ★★★★★ **`OriginalTransactionPrefix = 0x797265766E6F4300` 解码为 `"Convery"`**

### 3. ★★★★★ **"只推不回"有三条精确的 Python 行号出处**（`:291` / `:1616` / `:1622`）

★ **⇒ 且只适用于 `0x06/14` 的 `mmbook`。**

### 4. ★★★★★ **`acknowledgeUnhandled` 有实测对比：沉默 27 次 vs 应答 12 次**

★ **⇒ "Staying silent is **not a smaller version of the same behaviour -- it is a different one**"。**

### 5. ★★★★★ **`AckOnlyServices` 有一段"证据对但归因错"的诚实更正**

```
旧："C# LobbyServer 处理这些"
        ↓
★★★ 更正：**那些 .cs 文件存在但没有 switch 分支 ⇒ 从未运行**
   ⇒ 实际是**同一个通用兜底**
   ⇒ "**only the route was wrong in the comment**"
```

### 6. ★★★★ **两套空任务表的重叠是刻意的,注册顺序决定日志名**

### 7. ★★★ **`Messaging2::task2` 的 8 字节最短帧 `04 00 00 00 86 66 03 02`**

---

## 十、下一步

- 12 个 Service 实现（`MatchmakingService` 1,101 行 / `MarketplaceService` 1,099 行 / `StatsService` 875 行 / `LobbyProtocol` 807 行 / `Unknown0BService` 669 行 / `Profiles2Service` 630 行 / `ClanService` 623 行 / `Storage2Service` 450 行 / `Friends2Service` 325 行 / `InstantMessageService` 242 行 / `ContentUnlock2Service` 79 行 / `TencentService` 94 行 / `TitleUtilitiesService` 56 行）
- `LanDiscovery`（295 行）/ `SharedRoom*`（4 文件）
