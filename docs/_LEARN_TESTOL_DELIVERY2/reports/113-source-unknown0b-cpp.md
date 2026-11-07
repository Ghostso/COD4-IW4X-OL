# 学习报告 113（重开）— `Unknown0BService.cpp`（39,926 B / 709 行）

**学习范围**：`backend\Demonware\Unknown0BService.cpp` 全文（**709 行逐行读完**）
**性质**：全实测
**★★★★★ 本报告收录七个重大发现**：①**`0x1D0` 记录的 36 个字段位打包表** ②**双长度前缀 blob 的 4 字节缺口** ③**`0x238` 候选的 `+0x168/+0x16C/+0x170` 布局** ④**H1 与 D 两次编码风格证伪** ⑤**H2 放宽 ready 侦测导致"进不去房间"** ⑥**`task2` 的 32 位内部 ID** ⑦**`task13` 的 7 字段与三处 disputed**

---

## 一、★★★★★ **`0x1D0` 记录的 36 个字段位打包表**

### 1.1 ★★★★★ 完整的 `RecordFields`（第 109–115 行）

```cpp
struct RecordField { std::uint8_t tag; std::uint8_t width; };
constexpr std::array<RecordField, **36**> RecordFields{ {
    { 10, 64 }, { 3, 8 }, { 1, 1 }, { 21, 16 }, { 21, 16 }, { 21, 8 }, { 21, 8 },
    { 21, 64 }, { 21, 32 }, { 1, 1 }, { 21, 8 }, { 21, 8 }, { 21, 16 }, { 21, 16 },
    { 21, 16 }, { 21, 16 }, { 21, 16 }, { 21, 8 }, { 21, 16 }, { 21, 8 }, { 21, 32 },
    { 21, 32 }, { 21, 8 }, { 21, 32 }, { 21, 32 }, { 21, 8 }, { 1, 1 }, { 1, 1 },
    { 1, 1 }, { 1, 1 }, { 1, 1 }, { 1, 1 }, { 21, 32 }, { 3, 8 }, { 3, 8 }, { 1, 1 },
} };
```

### ★★★★★ 完整的 36 字段表

| # | tag | 位宽 | # | tag | 位宽 | # | tag | 位宽 |
|---|---|---|---|---|---|---|---|---|
| **0** | **10** | **64** | **12** | 21 | 16 | **24** | 21 | 32 |
| **1** | **3** | **8** | **13** | 21 | 16 | **25** | 21 | 8 |
| **2** | **1** | **1** | **14** | 21 | 16 | **26** | 1 | 1 |
| **3** | 21 | 16 | **15** | 21 | 16 | **27** | 1 | 1 |
| **4** | 21 | 16 | **16** | 21 | 16 | **28** | 1 | 1 |
| **5** | 21 | 8 | **17** | 21 | 8 | **29** | 1 | 1 |
| **6** | 21 | 8 | **18** | 21 | 16 | **30** | 1 | 1 |
| **7** | 21 | 64 | **19** | 21 | 8 | **31** | 1 | 1 |
| **8** | 21 | 32 | **20** | 21 | 32 | **32** | 21 | 32 |
| **9** | **1** | **1** | **21** | 21 | 32 | **33** | **3** | **8** |
| **10** | 21 | 8 | **22** | 21 | 8 | **34** | **3** | **8** |
| **11** | 21 | 8 | **23** | 21 | 32 | **35** | **1** | **1** |

### ★★★★★ tag 语义表（第 103 行，逐字）

```
// tag 编号见类型表：**3=UChar8 / 1=Bool / 21=FullType / 8=UInt32** …
```

| tag | 语义 |
|---|---|
| **1** | ★ **Bool** |
| **3** | ★ **UChar8** |
| **8** | ★ **UInt32** |
| **10** | ★ **UInt64** |
| **16** | ★ **String** |
| **21** | ★★ **FullType**（"完整类型" ⇒ 带显式位宽） |

### ★★★★★ 三个特殊字段的索引（第 118–120 行）

```cpp
constexpr std::uint64_t RecordField88Value = **2**;
constexpr std::uint64_t RecordReadyOffsetIndex = **2**;   // 第 3 个字段 = +0x90
constexpr std::uint64_t Record88OffsetIndex = **1**;      // 第 2 个字段 = +0x88
```

★★★ **⇒ 三个精确约定：**
```
字段 **0** ⇒ `userId`（tag 10,UInt64,64 位）
字段 **1** ⇒ **`+0x88`** ⇒ 值 **`2`**（"dump 实测值 2"）
字段 **2** ⇒ **`+0x90`** ⇒ 值 **`1`**（**ready**；"否则 freeze 判「全员 ready」不过"）
其余 ⇒ **一律 0**（"等价于构造器清空态"）
```

★★ **⇒ 字段 1 是 `+0x88`、字段 2 是 `+0x90` ⇒ 每个字段**占 8 字节**（但位宽不同 ⇒ 说明是**位打包**）。**
**⇒ 实际偏移不是简单累加（因为 tag 5 位 + 变长值）。**

### ★★★★★ 位写入器（第 74–100 行）

```cpp
class BitWriter
{
public:
    void put(const std::uint64_t value, const unsigned bits)
    {
        for (unsigned i = 0; i < bits; ++i)
        {
            if (bit_ % 8 == 0) buffer_.push_back(0);                    // ★ 需要时扩一字节
            if ((value >> i) & 1ULL)
                buffer_[bit_ / 8] |= static_cast<std::uint8_t>(1u << (bit_ % 8));   // ★ LSB-first
            ++bit_;
        }
    }
};
```

★★★ **⇒ **LSB-first**（低位先写,字节内也是低位先占）。**
**⇒ 注释明确："与客户端 `sub_B772E0` 的读取顺序**严格互逆**"。**

### ★★★ 记录体的完整构造（第 123–152 行）

```cpp
constexpr unsigned TagBits = **5**;   // layer B：5 bit tag（sub_B77630 -> sub_B75D40(0x1F)+1）
BitWriter writer;
// sub_626130 前导：tag UChar8(3) + 8 bit typeId=10
writer.put(**3**, TagBits);
writer.put(**10**, 8);
for (index...) {
    writer.put(field.tag, TagBits);
    writer.put(value, field.width);
}
// 记录之后：tag String(16) + 逐字符 8 bit + NUL（≤63 字符，写记录 +0x48）
writer.put(**16**, TagBits);
writer.putBytes(clipped);       // ≤ 63 字节
writer.put(**0**, 8);           // NUL
```

★★★★★ **⇒ 完整的记录结构：**
```
① **tag `3`（UChar8,5 位）+ typeId **`10`**（8 位）** ⇒ 前导
② **36 个字段**（每个 tag 5 位 + 值 width 位）
③ **tag `16`（String,5 位）+ ≤63 字节 + NUL**
        ↓
★★★ ⇒ **`0x1D0` = 464 字节是位打包后的总长**
```

### ★★★ `kCodolOfficialBotNames` 的 738 个名字（第 5–8 行，逐字）

```cpp
// ★★ 2026-10-12（会话 98000）—— M23：房间成员显示名取**客户端自带的官方名池**
// （`kCodolOfficialBotNames`，**738 名**，从活客户端资产堆只读取出）。严禁自造人机 / 自造名字：
// 这里是「接线既有池」，不是新造（rope §0.2；甲方红线）。
#include "game_server/codol_bot_names.hpp"
```

★★★ **⇒ **738 个官方 bot 名字**（从活客户端资产堆只读取出）。**
**⇒ 且明确"**严禁自造人机 / 自造名字**"（甲方红线）。**

★ **⇒ 与报告（`codol_bot_names.hpp` 16,545 B / 760 行）对应。**

---

## 二、★★★★★ **双长度前缀 blob 的 4 字节缺口**

### 2.1 ★★★★★ 完整注释（第 179–192 行，逐字）

```cpp
// ★★ 2026-10-12 17:2x（会话 98000）—— **实测修**：blob 是**双长度前缀**。
//
// `ByteBuffer::writeBlob(v)` 只写**外层长度**（`13 | 08 | u32 v.size() | v`）；
// **内层裸 u32 长度必须由值自带**。真样本（同一日志 17:19:41 的 11/4 回显）：
//     `13 08 28 00 00 00 | 24 00 00 00 | <36 B>`   ⇒ 外层 0x28=40 = 内层 0x24=36 + 4
// 客户端自己的 11/4 blob 就自带 `24 00 00 00` 前缀，所以 `decodeChannelPush()`
// 直接回显 messageBytes 才成立；**我先前直接 writeBlob(body)** 漏了这 4 字节
// ⇒ 客户端把 `02 0A 00 00` 当成长度 ⇒ 整条丢弃（2026-10-12 17:25 实机 11 条推送无效果的真因）。
```

### ★★★★★ 完整的字节对照

```
真样本：`13 08 28 00 00 00 | 24 00 00 00 | <36 B>`
        ↑  ↑  ↑              ↑
        |  |  外层长度 0x28=40 内层长度 0x24=36
        |  Blob 类型 0x08
        Blob 类型码 0x13
        ↓
★★★ **外层 40 = 内层 36 + 4** ✓
```

### ★★★★★ 一次"漏 4 字节"的实测代价

```
`ByteBuffer::writeBlob(v)` 只写**外层长度**（`13 | 08 | u32 v.size() | v`）
        ↓
★★★ **内层裸 u32 长度必须由值自带**
        ↓
★★★ 漏了 ⇒ **客户端把 `02 0A 00 00` 当成长度** ⇒ **整条丢弃**
        ↓
★★★★★ 实测代价：**2026-10-12 17:25 实机 11 条推送无效果**
```

★★ **⇒ 修复（第 187–192 行）：**
```cpp
std::vector<std::uint8_t> blobValue;
blobValue.reserve(body.size() + 4);
for (unsigned shift = 0; shift < 32; shift += 8)
    blobValue.push_back(static_cast<std::uint8_t>(body.size() >> shift));   // ★ 先写内层长度
blobValue.insert(blobValue.end(), body.begin(), body.end());
push.writeBlob(blobValue);     // 13 | 08(内层+4) | 裸 u32 内层 | body
```

### ★★★★★ 层 A 信封的完整格式（第 154–195 行，逐字）

```cpp
/// 层 A 信封（`confirmed`，第 95 轮 20 条真字节零误差）：
///   u32 kind | u64 senderId | string senderName | u64 channelId |
///   blob(双长度前缀) | u32 messageType
push.writeU32(**8**);            // kind=8（房间/频道消息）
push.writeU64(senderId);
push.writeString(senderName);
push.writeU64(channelId);
push.writeBlob(blobValue);       // 双长度前缀
push.writeU32(**1**);            // messageType=1（真样本同）
```

### ★★★★★ 完整的层 A 信封

| 偏移 | 类型 | 值 |
|---|---|---|
| **0** | **u32** | ★ **`kind = 8`**（房间/频道消息） |
| **4** | **u64** | `senderId` |
| **12** | **string** | `senderName`（NUL 结尾） |
| … | **u64** | `channelId` |
| … | **blob** | ★★ **双长度前缀** |
| … | **u32** | ★ **`messageType = 1`** |

### ★★★ blob body 的三段结构（第 161–172 行）

```cpp
// blob body = `02 | u32 typeId(=10) | u32 len | payload`（第 95 轮 §3.3；len 语义未定，
// 装配器取 len(payload) —— 与并发会话脚本 `channel_blob()` 一致）。
std::vector<std::uint8_t> body;
body.push_back(**0x02**);
appendRawU32(**10**);                                    // typeId
appendRawU32(static_cast<std::uint32_t>(record.size()));  // len
body.insert(body.end(), record.begin(), record.end());    // payload
```

★★★ **⇒ blob body = `0x02` + `u32 10`（typeId）+ `u32 len` + `payload`。**

★★ **⇒ 注意 `len` 的语义"未定"（注释明确），取 `len(payload)`。**

---

## 三、★★★★★ **`0x238` 候选的精确布局**

### 3.1 ★★★★★ 完整注释（第 341–360 行，逐字）

```cpp
// **为什么"回 1 个对象"就等于"count = 1"**：`ServiceResponse::serialize()`
// （`ServiceRegistry.cpp:35-41`）先写 `objects.size()` 当 count，非空时再写一遍，
// 然后 `writeRaw(object)`。所以：
//     objects = { 0x238 字节 }  ⇒  count 1 + data = 那 0x238 字节
// 正好对上客户端侧 `0x00637735 server_count := count`、
// `0x00637752 memcpy(room+0x7470, data, count * 0x238)`、`0x0063776A server_index := 0`
//
// **候选里要放什么**：`0x0062F6F0` 只读三个偏移 ——
//     **+0x168 = ID lo、+0x16C = ID hi、+0x170 = 串（≤63 B + NUL）**
// **ID 必须等于 event-21 `mmbook accepted` 推送里那个 u64 的两半**，否则
// `HandleMMBookReply`(0x00632680) 门3 对不上（`cmp eax,[esi+0x3A048]` /
// `cmp ebx,[esi+0x3A04C]`）。实测那次推送解析出来是
//     `arg0 = 0xDEADC0DE`、`arg1 = 0x01100001`
// 就是 `AuthSession.hpp:15 userId{ 0x1100001DEADC0DE }` 的低/高 dword。
```

### ★★★★★ 候选的三个偏移

| 偏移 | 大小 | 内容 |
|---|---|---|
| **`+0x168`** | **4** | ★★ **ID lo** |
| **`+0x16C`** | **4** | ★★ **ID hi** |
| **`+0x170`** | **≤64** | ★ **字符串**（≤63 B + NUL） |

★★★ **⇒ 而 `ID lo` = `0xDEADC0DE`、`ID hi` = `0x01100001`**
**⇒ 正是 `0x1100001DEADC0DE` 的低/高 dword** ✓（与报告 105 完全吻合）

### ★★★★★ 三个客户端地址（逐字）

```
**`0x00637735`** ⇒ `server_count := count`
**`0x00637752`** ⇒ `memcpy(room+0x7470, data, count * 0x238)`
**`0x0063776A`** ⇒ `server_index := 0`
```

★★ **⇒ 三个精确地址 + 一个 `memcpy` 的目标 `room+0x7470`。**

### ★★★ `+0x170` 的取值（第 358–360 行，逐字）

```cpp
// `+0x170` 用 "mmbook accepted"：与 2026-10-05 23:05 那次纯 RPM 种值实验一致
// （`rpm_seed_allocation.py`，`read_server_entries_rpm.py` 判 `mmbook_route_ready: true`）。
// 它不参与门3 的比较，先照那个已验证的取值走，保持单变量。
constexpr std::string_view SessionKey = "**mmbook accepted**";
```

★★ **⇒ `+0x170` = `"mmbook accepted"`（**不参与门 3 比较**）。**

---

## 四、★★★★★ **H1 与 D 两次编码风格证伪**

### 4.1 ★★★★★ H1：裸 572 字节（**证伪**）

```cpp
// H1（假设 + 判据 + 止损一次，出处
// `01-docs\30-topics\findings\定因-11-4分配应答是空ack-AllocResultHandler-ok0-20261006-1217.md` §8.3）：
//     对象 := <u32 count=1> + <568 B 候选>   （总长 572）
// 客户端侧应当：`data` 指向对象首字节、`count = *(u32*)data`、候选自 `data+4` 起
```

★★★ **⇒ H1 假设：对象 = `u32 count=1` + `568 B 候选` = **572 字节**。**

### ★★★★★ H1 的证伪（第 421–428 行，逐字）

```cpp
// H1（裸 572 B）实测证伪：`frida_trace_chain.py` 10 钩那一发看到
//   `AllocAssemble ctx+0x28` 的容器 **`data = NULL`**、
//   `AllocResultHandler(arg0=0, arg1=0)` ⇒ 我们那个裸对象**没有被解码成对象**；
//   而同一轮的 `21/5` 应答（对象 = 带标签 `ByteBuffer` 流，见
//   `MatchmakingService.cpp:784-798`）被客户端解成了 **`count = 1`** + 有内容 data。
// ⇒ 差别就是这个：**对象必须是带标签的字段流**，不能是裸字节。
```

★★★★★ **⇒ H1 的证伪证据：**
```
`AllocAssemble ctx+0x28` 的容器 **`data = NULL`**
`AllocResultHandler(arg0=0, arg1=0)`
        ↓
★★★ ⇒ **裸对象没有被解码成对象**
        ↓
★★★ 而同一轮的 `21/5` 应答（**带标签 `ByteBuffer` 流**）被解成 **`count = 1`** + 有内容 data
        ↓
★★★★★ 结论：**"对象必须是带标签的字段流，不能是裸字节"**
```

### ★★★★★ D：带标签的 `ByteBuffer`（最终形态）

```cpp
// D 的形态：`writeU32(count)` + `writeBlob(候选)`（与 21/5 同风格；语义＝「1 个候选」）。
// 候选内部布局 **一字不动**（`+0x168/+0x16C/+0x170`）。
// 判据（证真）：`AllocResultHandler(ok=1, data≠0)`、`server_cnt 1`、`server_idx 0`、
//              `CandidateToMMBookCtx 0x62F6F0 ≥1`、`BuildMMStartCommand 0x632070 ≥1`。
// 止损：D 只做一次；不中即转 B（修判别）/C（放宽条件）之前先复核 §10.1 模板法。
ByteBuffer object;
object.writeU32(CandidateCount);                                  // ★ 带标签的 u32 count
object.writeBlob(std::span<const std::uint8_t>(candidate));       // ★ 带标签的 blob
```

★★★ **⇒ D 的形态 = `writeU32(count)` + `writeBlob(candidate)`（**两个都带标签**）。**

### ★★★★★ 完整的 H1 → D 演进

| 版本 | 形态 | 结果 |
|---|---|---|
| **H1** | ★ `u32 count=1` + `568 B 候选`（**裸字节,572 B**） | ★★★ **证伪**（`data = NULL`） |
| **D** | ★★ `writeU32(count)` + `writeBlob(candidate)`（**带标签**） | 最终形态 |

★★ **⇒ 且注释明确 D 的**五个判据**（`AllocResultHandler(ok=1, data≠0)` / `server_cnt 1` / `server_idx 0` / `CandidateToMMBookCtx ≥1` / `BuildMMStartCommand ≥1`）。**

### ★★★ 一个"用错 API"的坑（第 362–371 行，逐字）

```cpp
// ★★ 2026-10-06 12:3x —— 这里踩了我自己一个坑，记下来：
//
// **`message` 是裸字节，不是类型化字段流**，所以**不能用 `ByteBuffer::readU32`**。
// 证据（就在本函数下面几行）：`std::ranges::equal(message, CapturedReadyMessage)`
// 是拿它跟 16 个**原始字节**（`0C 00 00 00 02 02 00 00 …`）直接比。
// 而 `ByteBuffer::readU32` 读的是**带 tag 的类型化字段**
// （`ByteBuffer.cpp:16` `TypeU32 = 0x08`）⇒ 在 `27 00 00 00` 上必然失败。
//
// **实测代价**：2026-10-06 12:27:29 客户端发了 `blob_len=43 op=0x27`，
// 而后端照旧回空 ack、本分支一次都没进 ⇒ **白烧一轮部署**。
```

★★★★★ **⇒ 一个精确的 API 误用：**
```
`message` 是**裸字节**,不是类型化字段流
        ↓
★★★ 所以**不能用 `ByteBuffer::readU32`**（它读的是 `08 <u32>` 带标签形态）
   ⇒ 在 `27 00 00 00` 上必然失败
        ↓
★★★ 正确做法：`std::memcpy(&op, message.data(), sizeof(op))`
        ↓
★★★★★ 实测代价：**白烧一轮部署**（12:27:29 客户端发 `blob_len=43 op=0x27`,分支一次没进）
```

---

## 五、★★★★★ **H2 放宽 ready 侦测导致"进不去房间"**

### 5.1 ★★★★★ 完整注释（第 454–476 行，逐字）

```cpp
// ★★ 2026-10-06 12:5x -- LOCAL OVERRIDE (DSH): ready 侦测由**逐字节全等**放宽为**结构签名**。
//
// 实测缺陷：`CapturedReadyMessage` 是**从另一轮/另一构建抄下来的 16 字节魔数**，
// 而我方客户端实际在 `11/4` 里发的准备批是
//     `10 00 00 00 02 02 00 00 00 18 00 00 00 20 10 00 …`（20 B，见后端日志）
// —— **结构一样（`u32` + `02 02` 开头），数值不同 ⇒ 严格全等永远不会命中
// ⇒ `RoomEvent::Ready` 在本镜像上从未触发过 ⇒ 房间/ready 归属链断在这里。**
//
// ...
// ★★ 2026-10-06 13:0x -- H2 **已撤回**（单变量复测）。
//
// 12:5x 我把这里放宽成「`message[4]==0x02 && message[5]==0x02` 即算 ready」，
// 目的是验证「严格 16 字节魔数导致 `RoomEvent::Ready` 永不触发」这条假设。
// **结果：改完之后「进不去匹配房间」了（甲方 13:0x 报）。**
// ⇒ 签名偏宽的代价可能是**把别的房间消息误判成 ready**，扰动房间生命周期。
// ⇒ 按 rope.md §5.2 止损纪律**撤回**，回到原样，先确认退化是不是它造成的。
// 假设本身仍未被证伪，只是**不能在没搞清副作用之前继续放宽**。
```

### ★★★★★ 完整的 H2 过程

```
① ★★★ `CapturedReadyMessage` 是**从另一轮/另一构建抄下来的 16 字节魔数**
        ↓
★★★ ② 我方客户端实际发的准备批是 **20 字节**：
   `10 00 00 00 02 02 00 00 00 18 00 00 00 20 10 00 …`
        ↓
★★★ ③ **结构一样（`u32` + `02 02` 开头）,数值不同**
   ⇒ **严格全等永远不会命中** ⇒ `RoomEvent::Ready` **从未触发过**
        ↓
★★★ ④ H2：放宽成 `message[4]==0x02 && message[5]==0x02`
        ↓
★★★★★ ⑤ **结果："进不去匹配房间"了**（甲方 13:0x 报）
        ↓
★★★ ⑥ 撤回（"按 rope.md §5.2 止损纪律"）
```

★★★ **⇒ 第 ⑤ 条是**放宽判据的代价**：**
```
签名偏宽 ⇒ **可能把别的房间消息误判成 ready** ⇒ **扰动房间生命周期**
        ↓
★★★ 结论（逐字）："假设本身仍未被证伪，只是**不能在没搞清副作用之前继续放宽**"
```

★ **⇒ 这是**"假设未被证伪,但不能继续"的精确表述**。**

### ★★★ `CapturedReadyMessage` 的 16 字节（第 450–453 行）

```cpp
constexpr std::array<std::uint8_t, 16> CapturedReadyMessage{
    0x0C, 0x00, 0x00, 0x00, 0x02, 0x02, 0x00, 0x00,
    0x00, 0x08, 0x00, 0x00, 0x00, 0x80, 0x08, 0x00,
};
```

★★★ **⇒ 以 `0C 00 00 00` 开头（u32 = 12）+ `02 02`。**
**⇒ 而实测的是 `10 00 00 00`（u32 = 16）+ `02 02`。**
**⇒ 即：**第一个 u32 不同（12 vs 16）** ⇒ 严格全等失败。**

### ★★★ 一个 TODO（第 448–449 行）

```cpp
// TODO(CODOL): capture the corresponding unready payload before
// generalizing this exact ready-state message into a field parser.
```

★★ **⇒ 明确 TODO："在把这个精确的 ready 消息泛化成字段解析器之前,先抓取对应的 unready 载荷"。**

---

## 六、★★★★★ **`task2` 的 32 位内部 ID**

### 6.1 ★★★★★ 完整注释（第 263–283 行，逐字）

```cpp
// LOCAL OVERRIDE (DSH, 2026-10-05 18:15) -- ROOM MESSAGES CARRY THE **32-BIT INTERNAL** ID.
//
// MEASURED, `n10run-20261005-173725.txt`, 18:14:35:
//     LSG_REQUEST  sequence=152 service=11 task=2 payload=0ADEC0ADDE0000000000
//     LSG_RESPONSE service=11 task=2 payload=...08E8030000...        <- error 1000
// The payload is a typed u64 (`0x0A` + 8 bytes): **0xDEADC0DE**. The old check compared it
// against `session_.userId`, which here is the full platform id 0x01100001DEADC0DE, so the
// comparison could only ever fail and this client never completed a room exit.
//
// The backend already writes the 32-bit form for the room object: `task13` below does
// `object.writeU64(static_cast<std::uint32_t>(userId));   // room+0x10  room id`, and the
// client echoes exactly that value back. The two halves were never using the same form.
```

### ★★★★★ 完整的 ID 形态对照

```
客户端发：`0ADEC0ADDE0000000000` ⇒ `0x0A` + **8 字节** `DE C0 AD DE 00 00 00 00`
        ⇒ **`0xDEADC0DE`**（32 位内部 ID,零扩展成 u64）
        ↓
★★★ 旧检查比较：`session_.userId` = **`0x01100001DEADC0DE`**（完整平台 ID）
        ↓
★★★★★ ⇒ **比较必然失败** ⇒ "this client **never completed a room exit**"
```

★★★ **⇒ 修复（第 284–288 行）：**
```cpp
const auto identity = session_.snapshot();
const auto internalUserId =
    static_cast<std::uint64_t>(static_cast<std::uint32_t>(identity.userId));
if (userId != identity.userId && userId != internalUserId)
    return ServiceResponse{ .error = 1000, .task = request.task };
```

★★ **⇒ **两种形态都接受**（完整 ID 或 32 位截断）。**

### ★★★ 两处印证（逐字）

```
① `.agents\modules\backend.md:17`：
   "room internal ID 属于独立的客户端 platform identity 链 ...
    clean 自然运行后,room member identity 和内嵌 `MatchMakingInfo`
    均持有 internal ID **`0xDEADC0DE`**"
        ↓
② `AuthSession.cpp:23-25` 的单向归一化：
   `output = parsed <= 0xFFFFFFFF ? 0x0110000100000000 | parsed : parsed;`
```

★ **⇒ 第 ② 条与报告 105 的 `parsePlatformUserId` **完全一致** ✓**

---

## 七、★★★★★ **`task13` 的 7 字段与三处 disputed**

### 7.1 ★★★★★ 完整实现（第 621–650 行）

```cpp
ServiceResponse Unknown0BService::task13(const ServiceRequest &request) const
{
    const auto emptyArgument = request.payload.empty() ||
        (request.payload.size() == 1 && request.payload.front() == 0);
    if (!emptyArgument || (roomEventSink_ && !roomEventSink_(RoomEvent::Enter)))
        return ServiceResponse{ .error = 1000, .task = request.task };

    const auto userId = session_.snapshot().userId;
    ByteBuffer object;
    object.writeU64(static_cast<std::uint32_t>(userId));   // room+0x10  room id, must be non-zero
    const auto bots = roomBotCount();
    object.writeU32(bots ? bots + 1 : 0);                  // room+0x18  member count (disputed: C# sends 1)
    object.writeU32(**18**);                               // room+0x1C  (disputed: C# sends 0)
    object.writeU64(userId);                               // room+0x20  second id
    object.writeBool(false);                               // room+0x28
    object.writeBool(false);                               // room+0x29
    object.writeU32(**1**);                                // room+0x2C  (disputed: C# sends 0)
    if (bots) botPushArmed_ = true;
    return ServiceResponse{ .task = request.task, .objects = { object.data() } };
}
```

### ★★★★★ 完整的 7 字段

| # | 类型 | 值 | room 偏移 | 说明 |
|---|---|---|---|---|
| **1** | **u64** | ★ `(uint32)userId` | **`+0x10`** | **room id（必须非零）** |
| **2** | **u32** | `bots ? bots+1 : **0**` | **`+0x18`** | ★★ **成员数**（disputed：C# 发 **1**） |
| **3** | **u32** | **`18`** | **`+0x1C`** | ★★ disputed：C# 发 **0** |
| **4** | **u64** | `userId` | **`+0x20`** | 第二个 id（`FUN_00634350` 转发） |
| **5** | **bool** | **`false`** | **`+0x28`** | |
| **6** | **bool** | **`false`** | **`+0x29`** | |
| **7** | **u32** | **`1`** | **`+0x2C`** | ★★ disputed：C# 发 **0** |

★★★ **⇒ 三处 disputed（与报告 112 完全对应）：**
```
字段 2（成员数）⇒ **0** vs C# 的 **1**
字段 3         ⇒ **18** vs C# 的 **0**
字段 7         ⇒ **1** vs C# 的 **0**
```

★ **⇒ 且字段 1 的 room id = **`(uint32)userId`** = **`0xDEADC0DE`**（**32 位内部 ID**）**
**⇒ 与 `task2` 的 32 位口径**完全一致** ✓**

### ★★★★★ `task13` 的请求是**完全空**（第 615–616 行，逐字）

```cpp
/// Task 13 -- CREATE ROOM. The request carries **no arguments at all**; its whole frame is
/// **`04000000 86 0B 03 0D`**, so everything the client needs comes back in the reply.
```

★★★★★ **⇒ `task13` 的完整帧 = **`04 00 00 00 86 0B 03 0D`**（8 字节）：**
```
`04 00 00 00` ⇒ 某 4 字节字段（与报告 109 的 `Messaging2::task2` 的 `04 00 00 00` 相同）
`86`          ⇒ ★ 可能是服务 ID 的高位标志
`0B`          ⇒ **服务 ID = 11**
`03`          ⇒ ★ **协议版本 3** ✓
`0D`          ⇒ **任务 ID = 13**
```

★★ **⇒ 与报告 109 的 `Messaging2::task2` 帧 `04 00 00 00 86 66 03 02` **完全同构** ✓**
**⇒ 即：`04 00 00 00` + `86` + `<服务>` + `03` + `<任务>`。**

### ★★★ `task4` 的注释（第 294–299 行，逐字）

```cpp
/// Task 4 -- every room message the client sends, as `(u64 roomId, blob batch, u32)`.
/// **NOT a heartbeat**: FUN_007e82f0, at the end of FUN_00632e80's drain block, builds this
/// task via FUN_00b8ec00 = FUN_00b78bc0(buf, 0x0B, 4), so the packed batch of queued room
/// messages -- **准备 among them** -- arrives HERE, inside the blob. **Unlike task 13 it binds
/// no result buffer** (FUN_00b8ec00 never calls FUN_00b83cb0), so a **bare acknowledgement is
/// correct for this one**.
```

★★★ **⇒ task 4 的关键区分：**
```
task 4 ⇒ **不绑定结果缓冲**（`FUN_00b8ec00` 从不调 `FUN_00b83cb0`）
      ⇒ **裸 ack 就对了**（与 task 13 相反）
        ↓
★★★ ⇒ **task 13 必须带一个结果,task 4 必须是裸 ack** ⇒ 两者**相反**
```

---

## 八、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **36 字段位打包表** | `RecordFields` 共 **36** 项；tag 语义 **1=Bool / 3=UChar8 / 8=UInt32 / 10=UInt64 / 16=String / 21=FullType** |
| 2 | ★★★ 三个特殊字段 | 字段 **0** = `userId`（64 位）/ 字段 **1** = **`+0x88`** 值 **`2`** / 字段 **2** = **`+0x90`** 值 **`1`**（ready） |
| 3 | ★★★ 记录结构 | **`tag 3 + typeId 10`** 前导 + **36 字段** + **`tag 16` + ≤63 字节 + NUL** |
| 4 | ★★★ **`BitWriter` 是 LSB-first** | "与客户端 `sub_B772E0` 的读取顺序**严格互逆**"；**tag 占 5 位**（`sub_B77630 -> sub_B75D40(0x1F)+1`） |
| 5 | ★★★ **738 个官方 bot 名** | `kCodolOfficialBotNames`（**738 名**，从活客户端资产堆只读取出）；"**严禁自造人机/自造名字**" |
| 6 | ★★★★★ **双长度前缀 blob** | 真样本 **`13 08 28 00 00 00 \| 24 00 00 00 \| <36 B>`** ⇒ 外层 **0x28=40** = 内层 **0x24=36** + 4 |
| 7 | ★★★★★ 漏 4 字节的代价 | 客户端把 **`02 0A 00 00`** 当成长度 ⇒ 整条丢弃 ⇒ **2026-10-12 17:25 实机 11 条推送无效果** |
| 8 | ★★★★★ **层 A 信封（confirmed）** | `u32 kind=**8**` + `u64 senderId` + `string senderName` + `u64 channelId` + **双长度 blob** + `u32 messageType=**1**` |
| 9 | ★★ blob body 三段 | `0x02` + `u32 typeId=10` + `u32 len` + payload（**len 语义未定**） |
| 10 | ★★★★★ **`0x238` 候选三偏移** | **`+0x168` = ID lo** / **`+0x16C` = ID hi** / **`+0x170` = 串（≤63+NUL）** |
| 11 | ★★★ ID 的精确值 | `ID lo = **0xDEADC0DE**` / `ID hi = **0x01100001**` ⇒ `0x1100001DEADC0DE` 的低/高 dword ✓ |
| 12 | ★★ 三个客户端地址 | **`0x00637735`**（`server_count := count`）/ **`0x00637752`**（`memcpy(room+0x7470, data, count*0x238)`）/ **`0x0063776A`**（`server_index := 0`） |
| 13 | ★ `+0x170` 的取值 | **`"mmbook accepted"`**（**不参与门 3 比较**） |
| 14 | ★★★★★ **H1（裸 572 B）证伪** | `AllocAssemble ctx+0x28` 的容器 **`data = NULL`**、`AllocResultHandler(arg0=0, arg1=0)` ⇒ **裸对象没被解码** |
| 15 | ★★★★★ **D（带标签）** | `writeU32(count)` + `writeBlob(candidate)` ⇒ "**对象必须是带标签的字段流，不能是裸字节**" |
| 16 | ★★★ D 的五个判据 | `AllocResultHandler(ok=1, data≠0)` / `server_cnt 1` / `server_idx 0` / `CandidateToMMBookCtx ≥1` / `BuildMMStartCommand ≥1` |
| 17 | ★★★★ **API 误用的代价** | `message` 是**裸字节** ⇒ **不能用 `ByteBuffer::readU32`**（它读 `08 <u32>`）⇒ **白烧一轮部署**（12:27:29） |
| 18 | ★★★★★ **H2 撤回** | `CapturedReadyMessage` 是**另一构建的 16 字节**（`0C 00 00 00 02 02…`）而实测是 **20 字节**（`10 00 00 00 02 02…`）⇒ **严格全等永不命中** |
| 19 | ★★★★★ H2 的代价 | 放宽成 `message[4]==0x02 && message[5]==0x02` ⇒ **"进不去匹配房间"**（甲方 13:0x 报）⇒ 撤回 |
| 20 | ★★★ H2 的结论 | "假设本身仍未被证伪，只是**不能在没搞清副作用之前继续放宽**" |
| 21 | ★★ TODO | "capture the corresponding **unready** payload before generalizing this exact ready-state message into a field parser" |
| 22 | ★★★★★ **`task2` 的 32 位 ID** | 客户端发 **`0xDEADC0DE`**（`0A` + 8 字节）vs `session_.userId` = **`0x01100001DEADC0DE`** ⇒ **必然失败** ⇒ "never completed a room exit" |
| 23 | ★★★ 修复 | **两种形态都接受**（完整 ID 或 32 位截断） |
| 24 | ★★ 两处印证 | `.agents\modules\backend.md:17`（"internal ID `0xDEADC0DE`"）+ `AuthSession.cpp:23-25` 的归一化 ✓ |
| 25 | ★★★★★ **`task13` 七字段** | `u64 (uint32)userId`@+0x10 / `u32 0`@+0x18 / `u32 **18**`@+0x1C / `u64 userId`@+0x20 / `bool false`@+0x28 / `bool false`@+0x29 / `u32 **1**`@+0x2C |
| 26 | ★★★ 三处 disputed | 字段 2（**0** vs 1）/ 字段 3（**18** vs 0）/ 字段 7（**1** vs 0） |
| 27 | ★★★★★ **`task13` 的完整帧** | **`04 00 00 00 86 0B 03 0D`**（8 字节）⇒ 与报告 109 的 `04 00 00 00 86 66 03 02` **同构** ✓ |
| 28 | ★★★★★ **task 4 与 13 相反** | task 4 **不绑定结果缓冲** ⇒ **裸 ack 正确**；task 13 **必须带一个结果** |

---

## 九、结论

### 1. ★★★★★ **`0x1D0` 记录的 36 字段位打包表被完整还原**

★ **⇒ tag 占 **5 位**（LSB-first）,值按 `width` 位写,末尾接 `tag 16` + 名字 + NUL。**

### 2. ★★★★★ **双长度前缀 blob 是"漏 4 字节 ⇒ 整条丢弃"**

★ **⇒ 实测代价：11 条推送无效果。**

### 3. ★★★★★ **`0x238` 候选的三个偏移（`+0x168/+0x16C/+0x170`）与 ID 的精确值**

### 4. ★★★★★ **H1 与 D 两次编码风格证伪**

```
H1（裸 572 B）⇒ `data = NULL` ⇒ 证伪
D（带标签）  ⇒ "对象必须是带标签的字段流，不能是裸字节"
```

### 5. ★★★★★ **H2 放宽 ready 侦测导致"进不去房间"**

★ **⇒ 且明确"假设未被证伪,但不能继续放宽"。**

### 6. ★★★★★ **`task2` 的 32 位内部 ID**（两种形态都接受）

### 7. ★★★★★ **`task13` 与 `task4` 的结果要求**完全相反**（13 必须带,4 必须裸 ack）

---

## 十、下一步

- `MarketplaceService`（1,099 行）/ `StatsService`（875 行）/ `LobbyProtocol`（807 行）
- `Profiles2Service`（630 行）/ `ClanService`（623 行）/ `Storage2Service`（450 行）
- `Friends2Service`（325 行）/ `ContentUnlock2Service` / `TencentService` / `TitleUtilitiesService`
- `SharedRoom*` / `Servers.cpp`（624 行）
