# 学习报告 112（重开）— `InstantMessageService`（66 + 242 行）+ `Unknown0BService.hpp`（132 行）

**学习范围**：`InstantMessageService.hpp`（3,465 B / 66 行）+ `.cpp`（12,905 B / 242）+ `Unknown0BService.hpp`（8,655 B / 132）
**性质**：全实测（**三文件逐行读完**）
**★★★★★ 本报告收录六个重大发现**：①**`mmbook accepted` 的 19 vs 15 字节反复（三次翻转）** ②**`mmbook` token 的 FNV 哈希 `0xDEC30B2A`** ③**房间服务的完整反汇编链（按准备键不发任何东西）** ④**task 13 必须带恰好一个结果** ⑤**房间记录的 7 个字段与两个来源的分歧** ⑥**一次"点准备即卡死"的回滚**

---

## 一、★★★★★ **`mmbook accepted` 的 19 vs 15 字节（三次翻转）**

### 1.1 ★★★★★ 第一次：裸 15（原始 Python）

```cpp
// ★★ 2026-10-05 22:1x -- BODY CORRECTED against the PYTHON BASELINE THAT ACTUALLY ENTERED
// MAPS: `Workmd\10-current\CODOL_ROUTE_ORIGINAL\lobby_server.py:263-270` verbatim
//     return (bytes([0x08]) + struct.pack("<I", 21) +
//             bytes([0x0A]) + struct.pack("<Q", sender_id) +
//             bytes([0x10]) + name + b"\x00" +
//             bytes([0x13, 0x08]) + struct.pack("<I", len(message)) +
//             message)
// called at `:292-294` as `_build_event21_push(local_id, name, b"mmbook accepted")`.
// The message is therefore the **RAW 15-byte ASCII, with NO inner <u32 len> and NO trailing NUL**.
```

★★★ **⇒ 原始 Python 基线：`message` = **裸 15 字节 ASCII**（无内层长度、无 NUL）。**

### ★★★★★ 第二次：改成 19（双层长度）

```cpp
// ★★★ 2026-10-07 04:2x -- ①**已实测证伪并撤回**（单变量，一次为限）。
//
// 我按 3.3.3.3 的抓包把推送体改成"内层 u32 + 15"（字段长 19），实测（d13）：
//   推送确实变成 `13 08 [13 00 00 00] [0F 00 00 00] "mmbook accepted"`，
//   但客户端**仍每 5 s 重发 `mmbook`**，`mmstart` 一次都没出现。
//
// 反汇编给了原因（`sub_632680` = `HandleMMBookReply`，0x6326E9）：
//     if (sub_C3C678("mmbook accepted", a5, 0xF) != 0)  → 派发 dwRoomMessageStartGameFailed
// 它拿**推送体的前 15 字节**与 `"mmbook accepted"` 逐字节比；19 字节体的前 15 字节是
//     `0F 00 00 00 6D 6D 62 6F 6F 6B 20 61 63 63`
```

★★★ **⇒ d13 实测：改成 19 后**客户端仍每 5 秒重发**,`mmstart` 一次都没出现。**
**⇒ 反汇编给出了原因：`sub_C3C678("mmbook accepted", a5, 0xF)` ⇒ 拿**前 15 字节**比。**
**⇒ 而 19 字节体的前 15 字节是 `0F 00 00 00 6D 6D 62 6F 6F 6B 20 61 63 63`（≠ 目标）。**

### ★★★★★ 第三次：**又恢复 19**（d24 推翻"裸 15"）

```cpp
// ★★★ 2026-10-07 04:5x -- **再更正：恢复双层长度（19）**（单变量；d24 实测推翻"裸 15"）：
//   d24 = 第一次「全对齐」轮（`server_index=0`、记录 `+0x168=0xF4241`、`room+0x3A048=0xF4241`、
//   推送 `SenderID=0xF4241`），当时 body = 裸 15 ⇒ 客户端**静默**循环
//   （无 StartGameFailed、无清零、无 `mmstart`）⇒ "比前 15 字节"的指针假设不成立。
//   黄金对照（`成果-抓包定因…-1645.md` §8.2 + §9.1）：跑通轮的推送体 =
//   `13 08 [13 00 00 00] [0F 00 00 00] "mmbook accepted"`（外层 19 = 内层 4 + 15），
//   与客户端自己的 `1308 [1D] [19] "mmbook 796 …"` 同构 ⇒ 解析器读的是**内层 u32 之后的 payload**。
//   （d13 那次 19 实验失败的因 = SenderID 未对齐 + 记录未解析，不是形态问题。）
```

★★★★★ **⇒ 最终结论：**19 字节（内层 u32 长度 15 + 15 字节 ASCII）**。**
**⇒ 且明确 d13 那次失败的原因是**"SenderID 未对齐 + 记录未解析"**,不是形态问题。**

### ★★★★★ 完整的三次翻转表

| 轮次 | body 形态 | 结果 | 原因 |
|---|---|---|---|
| **原始 Python** | ★ **裸 15** | 跑通 | — |
| **d13** | **19**（双层长度） | ★ 失败 | **SenderID 未对齐 + 记录未解析** |
| **d24** | ★ **裸 15** | ★★ **静默循环** | — |
| **最终（04:5x）** | ★★★ **19** | — | 黄金对照确认 |

★★★ **⇒ 这是一个**"同一个改动做对了但环境没准备好"的经典案例**：**
```
d13 的 19 失败 ⇒ 被误判为"形态错"
        ↓
改回 15（d24）⇒ 静默循环 ⇒ 才发现**不是形态问题**
        ↓
★★★ ⇒ 最终恢复 19,并明确"d13 失败的因 = SenderID 未对齐 + 记录未解析"
```

★★ **⇒ 与报告 107 的"两处 getter 字节回读确认已写入但门仍未放行"**同一类**（补丁生效了,但环境不对）。**

### ★★★★★ 最终的 body 构造（第 200–208 行）

```cpp
static const std::vector<std::uint8_t> AcceptedBody = []
{
    std::vector<std::uint8_t> body{ **0x0F, 0x00, 0x00, 0x00** };      // ★ 内层长度 = 15
    constexpr std::string_view Accepted = "**mmbook accepted**";
    body.insert(body.end(), Accepted.begin(), Accepted.end());
    return body;
}();
```

★★★ **⇒ `body` = `0F 00 00 00` + `"mmbook accepted"`（15 字节）= **19 字节**。**
**⇒ 而外层 `writeBlob` 会再加 `13 08 <u32 19>`。**

### ★★★★★ 完整的推送体（逐字对照）

```
`13 08 [13 00 00 00] [0F 00 00 00] "mmbook accepted"`
  ↑     ↑              ↑
  外层  外层长度=19     内层长度=15
        ↓
★★★ 与客户端自己的 `1308 [1D] [19] "mmbook 796 …"` **同构** ✓
```

---

## 二、★★★★★ **`mmbook` token 的 FNV 哈希 `0xDEC30B2A`**

### 2.1 ★★★★★ 完整实现（第 216–224 行）

```cpp
const auto separator = command.find(' ');
const auto token = std::string_view(command).substr(0, separator);
std::uint32_t hash = **0x811C9DC5**;                        // ★ FNV offset basis
for (const auto character : token)
    hash = (hash ^ static_cast<std::uint8_t>(character)) * **0x01000193**;   // ★ FNV prime
if (hash != **0xDEC30B2A**)
    return std::nullopt;

// ★ 2026-10-05 22:5x -- LOCAL OVERRIDE (DSH): **this token IS `mmbook`**.
```

### ★★★★★ FNV-1a 32 位的完整对照

```
`0x811C9DC5` = **2166136261** ⇒ FNV offset basis ✓
`0x01000193` = **16777619**   ⇒ FNV prime ✓
        ↓
★★★ ⇒ 与报告 099 的 `net_chan_mp.cpp` 的 `checksum()` **完全相同的 FNV-1a**
        ↓
★★★★★ ⇒ **`"mmbook"` 的 FNV-1a 32 哈希 = `0xDEC30B2A`**
```

★ **⇒ 这是一个**可直接验证的哈希值**（`"mmbook"` → `0xDEC30B2A`）。**

### ★★★ 命令格式

```cpp
const auto separator = command.find(' ');
const auto token = std::string_view(command).substr(0, separator);
```

★★ **⇒ 命令格式是 **`"<token> <参数>"`**（空格分隔）。**
**⇒ `mmbook` 的完整形态（从注释）是 **`"mmbook 796 …"`**。**

### ★★★ `mmstart` 的处理（第 212–214 行）

```cpp
if (bookingSink_ && command.starts_with("**mmstart **"))
    bookingSink_(command);
```

★★★ **⇒ `mmstart` 命令交给 `BookingSink`（进入 `SessionStart` → 地图加载）。**

★★ **⇒ 这与报告 109 的完整链条**完全吻合** ✓**
```
FIND_SERVERS → Session.Role=server → 0x06/14 mmbook → event 21 "mmbook accepted"
  → 0x06/14 mmstart → BookingSink → SessionStart → map
```

### ★★★★★ `suppressReply` 的**最终决定**（第 226–230 行）

```cpp
// ★ 2026-10-05 22:5x -- LOCAL OVERRIDE (DSH): this token IS `mmbook`.
// ★★★ 2026-10-07 05:0x -- **不再 suppress**（黄金对齐）：3.3.3.3 跑通轮服务端对 `6/14 mmbook`
// 回了 `030E 0800000000` ack，随后才是推送（`…-1645.md` §9.1）。此处照抄黄金。
suppressReply = **false**;
```

★★★★★ **⇒ 一次**回退**：**
```
报告 109 记：`suppressReply` 用于"只推不回"（不发 `0x85`）
        ↓
★★★ 本报告：**05:0x 改为 `suppressReply = false`**
   ⇒ 理由（逐字）："3.3.3.3 跑通轮服务端对 `6/14 mmbook` 回了 **`030E 0800000000`** ack,
     随后才是推送"
        ↓
★★★★★ ⇒ **黄金抓包显示：先 ack,后推送** ⇒ 所以要**回**（不 suppress）
```

★★ **⇒ 这**更正了报告 109 的结论**：`suppressReply` 机制**仍存在**（`ServiceResponse` 里还有那个字段）,
但 `decodeLocalCommand` **不再设置它**（恒为 false）。**

★★★ **⇒ ack 的字节是 **`03 0E 08 00 00 00 00`**：**
```
`03`     ⇒ **U8 类型码**（报告 105 已确认）
`0E`     ⇒ ★ **task 14**
`08 00 00 00 00` ⇒ **U32 = 0**
        ↓
★★★ ⇒ 即：**`{task: 14, error: 0}`**（空成功 ack）
```

---

## 三、★★★★★ **房间服务的完整反汇编链**

### 3.1 ★★★★★ 完整注释（`Unknown0BService.hpp`，逐字）

```cpp
/// Lobby service 11 -- the **ROOM service**, and the one that gates the 准备 (Ready) button.
///
/// THE CHAIN (full derivation in CODOL-main re/ROOM-START.md sect.38-39):
///
///   Pressing 准备 reaches **dwRoomImp vtable+0x84 (FUN_0062c690)**, which **SENDS NOTHING** -- it
///   appends to the room's outbound priority queue at **dwRoomImp+0x3A0D4**. The per-frame pump
///   **FUN_00632e80** drains those queues only inside `if (vtable+0x5c)`, and that predicate
///   (**FUN_0062FED0**) requires the client to **BE IN A ROOM**:
///
///       (room != 0 && room[1] != 0) || roomID64 != 0
///
///   Entering the room screen allocates one of two static **0x25D0-byte** records at
///   **0x0E374640**, stores it at **dwRoomImp+0x1C**, and then asks US to create the room --
///   **FUN_007e7ee0 -> FUN_00b8e670 -> FUN_00b78bc0(buffer, 0x0B, 0x0D)**: service **11**, task **13**.
///   If that task fails, the client **tears the record straight back down**
///   (**FUN_006340d0 -> FUN_00633ee0**) and the queued ready message **never leaves**.
```

### ★★★★★ 完整的七步链

```
① 按「准备」⇒ **`dwRoomImp` vtable+0x84（`FUN_0062c690`）**
   ⇒ ★★★ **什么都不发**,只把消息**追加到 `dwRoomImp+0x3A0D4` 的出站优先队列**
        ↓
② 每帧泵 **`FUN_00632e80`** 只在 **`if (vtable+0x5c)`** 里排空队列
        ↓
③ 该谓词 **`FUN_0062FED0`** 要求客户端**在房间里**：
   `(room != 0 && room[1] != 0) || roomID64 != 0`
        ↓
④ 进入房间画面 ⇒ 在 **`0x0E374640`** 分配**两个静态 `0x25D0` 字节记录之一**
   ⇒ 存到 **`dwRoomImp+0x1C`**
        ↓
⑤ ★★★ 然后**要求我们创建房间**：
   `FUN_007e7ee0 -> FUN_00b8e670 -> FUN_00b78bc0(buffer, 0x0B, 0x0D)`
   ⇒ **service 11, task 13**
        ↓
⑥ ★★★ **若该 task 失败** ⇒ 客户端**把记录拆掉**
   （`FUN_006340d0 -> FUN_00633ee0`）
        ↓
⑦ ★★★ ⇒ **排队的 ready 消息永远不会发出**
```

★★ **⇒ 五个精确的数字/地址：**
```
记录大小 **`0x25D0`** = 9,680 字节（**两个静态副本**）
记录数组地址 **`0x0E374640`**
房间对象偏移 **`dwRoomImp+0x1C`**
出站队列偏移 **`dwRoomImp+0x3A0D4`**
service/task = **`0x0B` / `0x0D`** = **11 / 13**
```

---

## 四、★★★★★ **task 13 必须带恰好一个结果**

### 4.1 ★★★★★ 完整注释（逐字）

```cpp
/// SO TASK 13'S REPLY MUST CARRY **EXACTLY ONE RESULT**. A zero-result acknowledgement is a
/// failure as far as the client is concerned, and it is **the failure that looks most like
/// success in a log**. The tell is on the wire one request later: the client's next **11/4**
/// echoes the room id back as **`0A 0000000000000000`** -- a **tag-10 u64 of ZERO** -- because it
/// never received one. **Check that field before believing the room came up.**
```

★★★★★ **⇒ 三条精确事实：**
```
① ★★★ **task 13 的应答必须带**恰好一个**结果**
   ⇒ 零结果的 ack 在客户端看来是**失败**
   ⇒ 且是"**在日志里看起来最像成功的那种失败**"
        ↓
② ★★★ **判据在下一个请求上**：客户端的 `11/4` 会把 room id 回显成
   **`0A 0000000000000000`**（tag-10 的 u64 = 0）
   ⇒ 因为它从未收到过
        ↓
③ ★★★ **"Check that field before believing the room came up."**
```

★ **⇒ 第 ② 条是**一个可直接观测的判据**（`0A 0000000000000000` = 房间没建起来）。**

### ★★★★★ 房间记录的 7 个字段（逐字表）

```
| reader        | tag        | object | room record | 含义                                    |
| FUN_00b769c0  | 10 UInt64  | +0x08  | +0x10       | **ROOM ID** — FUN_007e7a20 用它查房间   |
| FUN_00b76200  |  8 UInt32  | +0x10  | +0x18       | **成员数**（FUN_007e7b00 用它遍历
|               |            |        |             |   room+0x40 + i*0x60）                  |
| FUN_00b76200  |  8 UInt32  | +0x14  | +0x1C       |                                         |
| FUN_00b769c0  | 10 UInt64  | +0x18  | +0x20       | **第二个 id**,由 FUN_00634350 转发      |
| FUN_00b76870  |  1 Bool    | +0x20  | +0x28       |                                         |
| FUN_00b76870  |  1 Bool    | +0x21  | +0x29       |                                         |
| FUN_00b76200  |  8 UInt32  | +0x24  | +0x2C       |                                         |
```

### ★★★★★ 完整的字段表

| # | reader | tag | object 偏移 | room 偏移 | 含义 |
|---|---|---|---|---|---|
| **1** | **`FUN_00b769c0`** | **`10 UInt64`** | **`+0x08`** | **`+0x10`** | ★★★ **ROOM ID**（`FUN_007e7a20` 用它查房间） |
| **2** | **`FUN_00b76200`** | **`8 UInt32`** | **`+0x10`** | **`+0x18`** | ★★ **成员数**（`FUN_007e7b00` 遍历 `room+0x40 + i*0x60`） |
| **3** | `FUN_00b76200` | `8 UInt32` | `+0x14` | `+0x1C` | |
| **4** | **`FUN_00b769c0`** | **`10 UInt64`** | **`+0x18`** | **`+0x20`** | ★ 第二个 id（`FUN_00634350` 转发） |
| **5** | `FUN_00b76870` | `1 Bool` | `+0x20` | `+0x28` | |
| **6** | `FUN_00b76870` | `1 Bool` | `+0x21` | `+0x29` | |
| **7** | `FUN_00b76200` | `8 UInt32` | `+0x24` | `+0x2C` | |

★★★ **⇒ 成员记录步长 **`0x60` = 96 字节**（`room+0x40 + i*0x60`）。**

### ★★★★★ 两个来源的**三处分歧**（逐字）

```
/// TWO SOURCES DISAGREE ON THREE OF THOSE VALUES, and the disagreement is **deliberately left
/// standing rather than resolved by preference**. dest1yo's shipped DLL -- which this code
/// ports and which drives a real client -- sends **member count 0, third field 18, last field
/// 1**, and uses **the user id as the room id**. The C# OLfinal server sends **1, 0, 0** with a
/// **fixed room id of 69421**, reasoning that room+0x18 is the member count and one member is us.
/// **Both reach a lobby**, so **neither is refuted**, and the values below stay as the shipped
/// DLL had them.
```

### ★★★★★ 两个来源的完整对照

| 字段 | **dest1yo 的 DLL**（本代码移植） | **C# OLfinal 服务器** |
|---|---|---|
| **room id** | ★ **用户 id** | ★★ **固定 `69421`** |
| **成员数**（字段 2） | ★ **`0`** | ★ **`1`** |
| **第三个字段**（字段 3） | ★ **`18`** | ★ **`0`** |
| **最后一个字段**（字段 7） | ★ **`1`** | ★ **`0`** |

★★★ **⇒ 三处分歧（其实是四处）：**
```
① room id（用户 id vs 69421）
② 成员数（0 vs 1）
③ 第三个字段（18 vs 0）
④ 最后一个字段（1 vs 0）
```

★★★★★ **⇒ 作者的决定（逐字）：**"**Both reach a lobby, so neither is refuted**,
 and the values below stay as the shipped DLL had them."
**⇒ 即：**两个都能进大厅 ⇒ 都不算被证伪 ⇒ 保留 DLL 的值**。**

★★ **⇒ 且给了明确的 TODO：**"settle it by measurement -- put a client in a room and read
`room+0x18` and `room+0x2C` out of the live record at `0x0E374640`."**

★ **⇒ 这是**"不靠偏好解决分歧,靠实测"的明确态度**。**

---

## 五、★★★★★ **一次"点准备即卡死"的回滚**

### 5.1 ★★★★★ 完整注释（`Unknown0BService.hpp`，逐字）

```cpp
// ⚠ 2026-10-16（会话 28100）—— **刀J 已回滚**（`emitRoomSelfMember()` 曾在 96-116 行）。
// 实机结果：回推后**自定义房间点准备即卡死**（见 findings 事故条目）。
// 观察到的两个可疑点（下一刀要逐个排除，不要再原样重放）：
//   1. `record=105B` —— 定因文档要求记录体是 `0x1D0 = 464 B`
//      （`定因-房间成员消息typeId与记录体布局-20261012-95000.md`），
//      而 `memberInfoAddRecord()` 实际只产 **105 B**；该函数的 bot 路径从未实机跑过
//      （被 `OLMOD_ROOM_BOTS` 默认 0 挡住）⇒ 字节形状**未验证**；
//   2. **推送时机**：`roomEventSink_` 是在 `task4` 的处理栈内被调用的，而 `pushSink_` 走
//      `protocol_.queuePush(...)` ⇒ **在协议处理栈内再入队 = 重入**，这与既有 bot 推送
//      （同样在 task4 内、但默认不执行）是同一个风险面。
// 重做方向：**把推送移出处理栈**（下一帧 / 由后端主循环发），且**先离线校验 464 B 记录形状**再上线。
```

### ★★★★★ 两个可疑点

| # | 可疑点 | 精确数据 |
|---|---|---|
| **1** | ★★★ **记录体只有 105 B,而要求是 464 B** | `0x1D0 = **464**`；`memberInfoAddRecord()` 实际产 **105 B**；且该函数的 bot 路径**从未实机跑过**（被 `OLMOD_ROOM_BOTS` 默认 0 挡住） |
| **2** | ★★★ **推送时机 = 重入** | `roomEventSink_` 在 `task4` 的处理栈内被调用,而 `pushSink_` 走 `protocol_.queuePush(...)` ⇒ **在协议处理栈内再入队** |

★★★ **⇒ 重做方向（逐字）：**
```
① **把推送移出处理栈**（下一帧 / 由后端主循环发）
② **先离线校验 464 B 记录形状**再上线
```

★ **⇒ 第 ② 条是**"先离线校验,再上线"的纪律**。**

### ★★★★★ 房间消息的**证据分级**（逐字）

```cpp
// 【证据级别】外层信封 = `confirmed`（第 95 轮用 **20 条真实 LSG_PUSH 字节零误差复现**）；
// 0x1D0 记录体 + 位打包 = `hypothesis`（代码级 Observed，**尚未实机字节闭合**，
// 第 95 轮 §6 明确列出「层 A 字节对齐 vs 层 B 位打包」未定）。
```

★★★★★ **⇒ 两级证据：**
```
**外层信封 = `confirmed`** ⇒ 用 **20 条真实 `LSG_PUSH` 字节零误差复现**
**`0x1D0` 记录体 + 位打包 = `hypothesis`** ⇒ 代码级 Observed,**尚未实机字节闭合**
        ↓
★★★ 未定项：**"层 A 字节对齐 vs 层 B 位打包"**
```

★ **⇒ 这是**证据分级最清晰的一处**（`confirmed` vs `hypothesis`）。**

### ★★★ 门闸 `OLMOD_ROOM_BOTS`（逐字）

```cpp
// 门闸 `OLMOD_ROOM_BOTS`（默认 0）：为 0 时本组代码**一行都不执行**
// ⇒ 与 V1.20 行为等价，满足 rope §2.3 单变量（可 A/B）。
```

★★ **⇒ 默认 0 ⇒ 完全等价于旧行为（可 A/B 测试）。**

---

## 六、★★★★ **`InstantMessageService` 的三个任务**

### 6.1 ★★★★★ 任务表（第 28–43 行）

```cpp
registry.registerTask(0x06, **5**,  "Messaging::readQueuedMessages");
registry.registerTask(0x06, **14**, "Messaging::sendGlobalInstantMessage");
registry.registerTask(0x06, **18**, "Messaging::sendInstantMessage");
```

### ★★★★★ 三个任务的语义

| task | 名称 | 行为 |
|---|---|---|
| **5** | `readQueuedMessages` | ★ **恒返回空**（"The archived ring has no insertion xrefs. Both pagination modes are therefore observably empty in this build."） |
| **14** | `sendGlobalInstantMessage` | ★★ **单收件人**（`u64 recipient` + `blob message`） |
| **18** | `sendInstantMessage` | ★★★ **多收件人**（`blob message` + N × `u64 recipient`） |

★★★ **⇒ task 14 与 18 的区别：**
```
**task 14** ⇒ `u64 recipient` + `blob message`（**一个收件人**）
**task 18** ⇒ `blob message` + **循环读 `u64 recipient`**（**多个收件人**）
        ↓
★★★ ⇒ 字段顺序**相反**（14 是 recipient 先,18 是 message 先）
```

### ★★★★★ `task14` 的三分支（第 80–108 行）

```cpp
const auto localUserId = session_.snapshot().userId;
if (recipient != 0 && recipient != localUserId)
{
    publish(recipient, message, true, true);         // ★ ① 发给别人
}
else
{
    bool suppressReply = false;
    if (auto body = decodeLocalCommand(message, suppressReply))
        publish(localUserId, *body, true, false);     // ★ ② 本地命令（mmbook/mmstart）
    response.suppressReply = suppressReply;           // ★ 现在恒 false
}
```

★★★ **⇒ 三个分支：**
```
① **`recipient != 0 && recipient != localUserId`** ⇒ **发给别人**（`invokeLocalReceiver=true, broadcastEvent=true`）
② **`recipient == 0 || recipient == localUserId`** ⇒ **当本地命令处理**（`decodeLocalCommand`）
   ⇒ 若是 `mmbook` ⇒ **推送 `mmbook accepted`**（`invokeLocalReceiver=true, broadcastEvent=false`）
③ 若 `decodeLocalCommand` 返回 `nullopt` ⇒ **什么都不做**
```

### ★★★ `publish` 的 JSON 事件（第 148–154 行）

```cpp
const nlohmann::json event{
    { "**Sendername**", identity.username },
    { "**Recipient**", recipient },
    { "**SenderID**", sender },
    { "**Message**", messageBytes },
};
```

★★ **⇒ 四个字段,与报告 111 的 `MEEP` 事件不同（那是 `Payload`/`Origin`/`Event`）。**
**⇒ 这个事件通过 `messageBus_->broadcast("Demonware::Instantmessage", event.dump())` 发出。**

### ★★★ `decodeInstantPush` 的推送构造（第 297–301 行）

```cpp
ByteBuffer push;
push.writeU32(**21**);                                  // ★ 事件类型 21
push.writeU64(senderId->get<std::uint64_t>());          // ★ SenderID
push.writeString(senderName->get<std::string>());       // ★ 名字
push.writeBlob(messageBytes);                           // ★ 消息
```

★★★★★ **⇒ 推送体 = `{u32 21, u64 senderId, string name, blob message}`**
**⇒ 与 Python 的 `_build_event21_push` 逐字节对应：**
```
Python：`bytes([0x08]) + pack("<I", 21)`     ⇒ **u32 21** ✓
        `bytes([0x0A]) + pack("<Q", sender_id)` ⇒ **u64 senderId** ✓
        `bytes([0x10]) + name + b"\x00"`     ⇒ **string name** ✓
        `bytes([0x13, 0x08]) + pack("<I", len)` + message ⇒ **blob** ✓
```

### ★★★ `task5` 恒空（第 47–61 行）

```cpp
// The archived ring has no insertion xrefs. Both pagination modes are
// therefore observably empty in this build.
return ServiceResponse{ .task = request.task };
```

★★ **⇒ 明确声明："归档的环没有插入 xref ⇒ 两种分页模式在这个 build 里都观测为空"。**

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **`mmbook accepted` 三次翻转** | 原始 **裸 15** → d13 **19**（失败）→ d24 **裸 15**（静默循环）→ **最终 19** |
| 2 | ★★★★ 最终形态 | `13 08 [13 00 00 00] [0F 00 00 00] "mmbook accepted"`（外层 **19** = 内层 4 + 15） |
| 3 | ★★★ d13 失败的真正原因 | "**SenderID 未对齐 + 记录未解析**,不是形态问题" |
| 4 | ★★★ 黄金对照 | 客户端自己的 `1308 [1D] [19] "mmbook 796 …"` ⇒ **同构** |
| 5 | ★★★★★ **`mmbook` 的 FNV 哈希** | **`0xDEC30B2A`**（FNV-1a 32：`0x811C9DC5` + `0x01000193`）⇒ 与报告 099 的 `checksum()` **同一算法** |
| 6 | ★★ 命令格式 | `"<token> <参数>"`（空格分隔）；`mmstart` 交给 `BookingSink` |
| 7 | ★★★★★ **`suppressReply` 回退** | 05:0x 改为 **`false`** —— 黄金抓包显示服务端对 `6/14 mmbook` **回了 `030E 0800000000` ack**,随后才是推送 |
| 8 | ★★★ ack 字节 | **`03 0E 08 00 00 00 00`** = `{U8 task=14, U32 error=0}` |
| 9 | ★★★★★ **房间服务完整链** | 按准备 ⇒ `dwRoomImp vtable+0x84`（`FUN_0062c690`）**什么都不发**,只入队 `dwRoomImp+0x3A0D4` |
| 10 | ★★★ 泵条件 | `FUN_00632e80` 只在 `if (vtable+0x5c)` 里排空；谓词 `FUN_0062FED0` = **`(room != 0 && room[1] != 0) \|\| roomID64 != 0`** |
| 11 | ★★★★ **记录分配** | 两个静态 **`0x25D0`**（**9,680**）字节记录在 **`0x0E374640`**,存到 `dwRoomImp+0x1C` |
| 12 | ★★★ **创房请求** | `FUN_007e7ee0 -> FUN_00b8e670 -> FUN_00b78bc0(buffer, 0x0B, 0x0D)` = **service 11, task 13** |
| 13 | ★★★ 失败后果 | 客户端**拆掉记录**（`FUN_006340d0 -> FUN_00633ee0`）⇒ **ready 消息永不发出** |
| 14 | ★★★★★ **task 13 必须恰好一个结果** | 零结果 ack = 失败,且是"**在日志里看起来最像成功的那种失败**" |
| 15 | ★★★★★ **判据** | 客户端的 `11/4` 会把 room id 回显成 **`0A 0000000000000000`**（tag-10 u64 = 0）⇒ "**Check that field before believing the room came up**" |
| 16 | ★★★★★ **房间记录 7 字段** | `10 UInt64`(ROOM ID,+0x08→+0x10) / `8 UInt32`(成员数,+0x10→+0x18) / `8 UInt32`(+0x14→+0x1C) / `10 UInt64`(第二 id,+0x18→+0x20) / `1 Bool`(+0x20→+0x28) / `1 Bool`(+0x21→+0x29) / `8 UInt32`(+0x24→+0x2C) |
| 17 | ★★ 成员步长 | **`0x60` = 96 字节**（`room+0x40 + i*0x60`） |
| 18 | ★★★★★ **两来源四处分歧** | room id（**用户 id** vs **69421**）/ 成员数（**0** vs **1**）/ 第三字段（**18** vs **0**）/ 最后字段（**1** vs **0**） |
| 19 | ★★★★ 作者态度 | "**Both reach a lobby, so neither is refuted**" ⇒ 保留 DLL 值 + **TODO 靠实测解决** |
| 20 | ★★★★★ **"点准备即卡死"回滚** | ①记录体只有 **105 B** 而要求 **`0x1D0` = 464 B** ②**推送时机 = 在 `task4` 处理栈内再入队 = 重入** |
| 21 | ★★★ 重做方向 | **把推送移出处理栈** + **先离线校验 464 B 记录形状** |
| 22 | ★★★★★ **证据分级** | 外层信封 = **`confirmed`**（**20 条真实 `LSG_PUSH` 字节零误差复现**）；`0x1D0` 记录体 + 位打包 = **`hypothesis`**（未实机闭合） |
| 23 | ★★ 未定项 | **"层 A 字节对齐 vs 层 B 位打包"** |
| 24 | ★★★ **`OLMOD_ROOM_BOTS`** | 默认 **0** ⇒ 完全等价旧行为（可 A/B） |
| 25 | ★★ **三个 IM 任务** | task **5**(恒空) / **14**(单收件人：`u64` + `blob`) / **18**(多收件人：`blob` + N×`u64`) |
| 26 | ★★ task 14 三分支 | ①发给别人 ②本地命令 ③`nullopt` ⇒ 什么都不做 |
| 27 | ★★★ `publish` 事件四字段 | `Sendername` / `Recipient` / `SenderID` / `Message` |
| 28 | ★★★★★ **推送体构造** | `{u32 21, u64 senderId, string name, blob message}` ⇒ 与 Python `_build_event21_push` **逐字节对应** |

---

## 八、结论

### 1. ★★★★★ **`mmbook accepted` 的 19 vs 15 字节经历了三次翻转**

```
原始裸 15 → d13 改 19（失败）→ d24 改回裸 15（静默循环）→ 最终 19
        ↓
★★★ **d13 失败的真正原因不是形态,而是 "SenderID 未对齐 + 记录未解析"**
```

### 2. ★★★★★ **`"mmbook"` 的 FNV-1a 32 哈希 = `0xDEC30B2A`**

### 3. ★★★★★ **`suppressReply` 回退为 `false`**（黄金抓包显示先 ack 后推送）

### 4. ★★★★★ **房间服务的完整反汇编链被还原**（7 步,含 5 个精确地址/尺寸）

### 5. ★★★★★ **task 13 必须恰好一个结果,判据是下一个 `11/4` 的 room id**

### 6. ★★★★★ **两个来源四处分歧,作者选择"不靠偏好解决,靠实测"**

### 7. ★★★★★ **"点准备即卡死"的两个可疑点**（105 B vs 464 B / 重入）

### 8. ★★★★ **证据分级：外层 `confirmed`（20 条字节零误差）/ 内层 `hypothesis`**

---

## 九、下一步

- `Unknown0BService.cpp`（669 行）
- `MarketplaceService`（1,099 行）/ `StatsService`（875 行）/ `LobbyProtocol`（807 行）
- `Profiles2Service`（630 行）/ `ClanService`（623 行）/ `Storage2Service`（450 行）
- `Friends2Service`（325 行）/ `ContentUnlock2Service` / `TencentService` / `TitleUtilitiesService`
- `SharedRoom*` / `Servers.cpp`（624 行）
