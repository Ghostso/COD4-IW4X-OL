# 学习报告 098（重开）— `game_server\qcommon\net_chan_mp.hpp`（7,412 B / 182 行）

**学习范围**：`game_server\qcommon\net_chan_mp.hpp` 全文
**性质**：全实测（**逐行读完**）
**★★★★★ 本报告收录四个重大发现**：①**OLfinal 用 opcode 5 结束消息,而 3.3.3.3 用 6（54,682/54,682 实测）** ②**`UserCmd` 的 15 个字段与 `+0x18` 的精确 CODREF** ③**netchan 分片的完整状态机** ④**`userCmdKey` 的三重异或与"不可从解码字节恢复"**

---

## 一、★★★★★ 7 个 netchan 常量（第 15–32 行）

| 常量 | 值 | 说明 |
|---|---|---|
| **`NetchanSequenceMask`** | ★ **`0x1FFFFFFF`** | **29 位**序列号掩码 |
| **`NetchanFragmentSize`** | ★★ **1154** | ★ 分片大小 |
| **`NetchanMaximumFragments`** | **128** | 最多分片数 |
| **`NetchanMaximumFragmentedMessage`** | **`0x20000`** = **131,072** | 最大分片消息 |
| **`ClientCommandReliable`** | **2** | 客户端命令：可靠 |
| **`ClientCommandEof`** | **3** | 客户端命令：结束 |
| **`ServerCommandReliable`** | **1** | 服务端命令：可靠 |
| **`ServerCommandReliableBinary`** | **2** | 服务端命令：可靠二进制 |
| ★★★ **`ServerCommandEof`** | ★★ **5** | ★★★ **服务端命令：结束（OLfinal 用 5）** |

### ★★★★★ `1154` 与既有 memory 的**精确吻合**

```
本报告：**`NetchanFragmentSize = 1154`**
        ↓
★★★ memory（FAT 分片帧真实布局）：
   "10 字节头 index/last/stride(**1154**)/length"
        ↓
★★★★★ ⇒ **`1154` 是同一个常量**,在**两处独立确认** ✓
```

### ★★★ `0x1FFFFFFF` = **29 位**序列号

★ **⇒ 与报告 094 的 `bulletHitEntityNum = 2047`（11 位）**是不同的位宽**（序列号 29 位）。**

### ★★★★★ `0x20000` 与 128 × 1154 的关系

```
128 × 1154 = **147,712**
而 `NetchanMaximumFragmentedMessage = 0x20000 = **131,072**
        ↓
★★★ ⇒ **131,072 < 147,712** ⇒ 128 个分片**装得下** 131,072 字节
   （131,072 / 1154 ≈ **113.6** ⇒ 最多 **114** 个分片就够）
   ⇒ 128 是**留了余量**的上限
```

---

## 二、★★★★★ **OLfinal 的 opcode 5 vs 3.3.3.3 的 6（54,682/54,682 实测）**

### 2.1 ★★★★★ 完整注释（第 23–31 行，逐字）

```cpp
// 3.3.3.3 ends a server message with 6; OLfinal ends it with 5, and this constant was
// carried across unchanged. MEASURED on two independent corpora and recorded in
// re/demo-re/01-container.md sec 4 and 06-olevents.md sec 2: it is the final byte of
// 54,682/54,682 demo snapshot payloads, the end token of the gamestate's configstring
// block, and the byte after the gamestate's clientNum/checksumFeed pair -- every slot
// where 3.3.3.3 writes 6. The rest of the table is unchanged: 0 snapshot, 1
// serverCommand, 2 binary serverCommand, 3 gamestate, 4 configstring block start.
// OLfinal has no opcode 6 at all, so a message terminated with 6 is not merely read
// wrong -- it falls through to the parse loop's error exit.
constexpr std::uint8_t ServerCommandEof = 5;
```

### ★★★★★ 三重实测证据

| # | 证据 | 精确数据 |
|---|---|---|
| **1** | ★★★ **54,682 / 54,682** 个 demo 快照 payload 的**最后字节**是 5 | **100% 命中** |
| **2** | ★★ **gamestate 的 configstring 块的结束 token** | 是 5 |
| **3** | ★★ **gamestate 的 `clientNum`/`checksumFeed` 对之后的字节** | 是 5 |

★★★ **⇒ 第 1 条的**100% 命中率**是极强的证据（54,682 个样本无一例外）。**

### ★★★★★ 完整的 server opcode 表

| opcode | 含义 | 3.3.3.3 | **OLfinal** |
|---|---|---|---|
| **0** | **snapshot** | ✓ | ✓ |
| **1** | **serverCommand** | ✓ | ✓ |
| **2** | **binary serverCommand** | ✓ | ✓ |
| **3** | **gamestate** | ✓ | ✓ |
| **4** | **configstring block start** | ✓ | ✓ |
| ★ **5** | ★★★ **EOF** | ★ **（无）** | ★★★ **EOF** |
| ★ **6** | **EOF** | ★ **EOF** | ★★★ **不存在** |

★★★ **⇒ 唯一差异就是"结束符"：**
```
**3.3.3.3** ⇒ 用 **6** 结束
**OLfinal** ⇒ 用 **5** 结束
        ↓
★★★ 而 **OLfinal 根本没有 opcode 6**
   ⇒ 所以用 6 结束的消息**不是"读错"**,
     而是**直接落到解析循环的错误出口**
```

★★★★★ **⇒ 这是一条**极高价值的差异**（解释了为什么照抄 3.3.3.3 的实现会失败）：**
```
若按 3.3.3.3 写 6 ⇒ **OLfinal 的解析器会走错误出口**（不是静默错读）
        ↓
★ 与 memory 的「ol-mod 不是 3.19」呼应：
  "ol-mod 自己在 `net_chan_mp.hpp` 写'3.3.3.3 用 6 收尾;**OLfinal** 用 5'"
        ↓
★★★★★ ⇒ **memory 里的这条记录现在有了完整的上下文与三重实测证据**
```

★ **⇒ 出处：`re/demo-re/01-container.md sec 4` + `06-olevents.md sec 2`。**

---

## 三、★★★★★ **`UserCmd` 的 15 个字段（含 `+0x18` 的精确 CODREF）**

### 3.1 ★★★ 完整定义（第 40–62 行）

```cpp
struct UserCmd
{
    std::uint32_t commandTime{};
    std::uint32_t buttons{};
    std::array<std::uint16_t, 3> angles{};
    std::uint16_t weapon{};
    std::uint16_t offHandIndex{};
    // Legacy names above/below are retained for the diagnostics ABI.
    // CODREF(1649370): 0x5B2241 writes cg.equippedOffHand through
    // clientActive+0x3C64 into native usercmd+0x18: THIS member is the
    // equipped offhand. The preceding +0x16 member comes from the
    // per-weapon lookup at cg+0xC7238, not cg.equippedOffHand.
    std::uint16_t lastWeaponAltModeSwitch{};
    std::int8_t forwardMove{};
    std::int8_t rightMove{};
    float conditionalAngle{};
    std::uint8_t conditionalByte{};
    std::uint16_t conditionalElevenBits{};
    std::array<std::uint8_t, 3> selectedLocation{};
    std::array<std::uint8_t, 2> selectedDirection{};
};
```

### ★★★★★ 完整的 15 个字段与**精确的偏移**

| 偏移 | 类型 | 字段 | 说明 |
|---|---|---|---|
| **+0x00** | u32 | `commandTime` | 命令时间 |
| **+0x04** | u32 | `buttons` | 按键 |
| **+0x08** | u16×3 | `angles[3]` | 视角（6 字节） |
| **+0x0E** | u16 | `weapon` | 武器 |
| ★ **+0x10** | u16 | `offHandIndex` | 副手索引 |
| ★★ **+0x12** | u16 | `lastWeaponAltModeSwitch` | ★ 见下 |
| **+0x14** | i8 | `forwardMove` | 前后移动 |
| **+0x15** | i8 | `rightMove` | 左右移动 |
| **+0x16** | f32 | `conditionalAngle` | ★ 4 字节（对齐填充后） |
| **+0x1A** | u8 | `conditionalByte` | |
| **+0x1B** | u16 | `conditionalElevenBits` | ★★ **11 位**（名字直接写了） |
| **+0x1D** | u8×3 | `selectedLocation[3]` | |
| **+0x20** | u8×2 | `selectedDirection[2]` | |

★★ **⇒ 注意：偏移是我按字段顺序推算的（`#pragma pack` 未知），`+0x18` 的 CODREF 说明**原生布局与这里不同**：**
```
注释（逐字）："**CODREF(1649370): 0x5B2241 writes cg.equippedOffHand through
 clientActive+0x3C64 into native usercmd+0x18**: THIS member is the
 **equipped offhand**. The preceding **+0x16** member comes from the
 **per-weapon lookup at cg+0xC7238**, not cg.equippedOffHand."
        ↓
★★★★★ ⇒ 原生 `usercmd` 的布局：
  **`+0x16`** = 来自 **`cg+0xC7238`** 的**每武器查表**（不是 `cg.equippedOffHand`）
  **`+0x18`** = **`cg.equippedOffHand`**（经 `clientActive+0x3C64`）
        ↓
★★★ ⇒ 即：**`offHandIndex` 与 `lastWeaponAltModeSwitch` 的语义容易搞反**
   ⇒ 注释明确：**`+0x18` 才是 equipped offhand**
```

★★ **⇒ 三条精确地址：**
```
**`0x5B2241`**   ⇒ 写入指令（`clientActive+0x3C64` → `usercmd+0x18`）
**`clientActive+0x3C64`** ⇒ `cg.equippedOffHand` 的来源
**`cg+0xC7238`** ⇒ `+0x16` 的每武器查表
        ↓
★★★ 且 **`CODREF(1649370)`** ⇒ 与报告 077 的 `build_number=1649370` **完全吻合** ✓
```

### ★★★ `conditionalElevenBits` 的名字（第 57 行）

```cpp
std::uint16_t conditionalElevenBits{};
```

★★★ **⇒ 字段名直接写明了**11 位** ⇒ 与报告 094 的 `bulletHitEntityNum = 2047`（11 位）**同一编码空间**。**
**⇒ 说明 usercmd 里有一个**11 位字段**（可能是实体号或索引）。**

### ★★★ `conditionalAngle` / `conditionalByte` 的命名

★★ **⇒ 三个 `conditional*` 字段 ⇒ 说明它们**不是无条件存在**（取决于某个标志位）。**
**⇒ 与报告 093 的 `LoadoutRequest` 的 `classMask` 位域**同类**（条件性字段）。**

---

## 四、★★★★★ **netchan 分片的完整状态机**

### 4.1 ★★★★★ 三个 CODREF 地址（第 98–101 行，逐字）

```cpp
// CODREF(netchan_fragment): CODOL 0x005A5490/0x005A55F0/
// 0x005A5720 retain one outgoing message under a stable sequence and
// send indexed 1154-byte fragments until completion.
```

★★★ **⇒ 三个发送侧函数地址：**
```
**`0x005A5490`** / **`0x005A55F0`** / **`0x005A5720`**
        ↓
★★★ 语义（逐字）："retain **one outgoing message under a stable sequence**
 and send **indexed 1154-byte fragments until completion**"
        ↓
★ 即：**一个出站消息保持在稳定序列号下,按索引发 1154 字节分片直到完成**
```

### ★★★★★ 第二个 CODREF（第 109–110 行，逐字）

```cpp
// CODREF(netchan_fragment): CODOL Netchan_Process 0x005A5960 owns a
// separate receive sequence, aggregate length and four-word bitmap.
```

★★★ **⇒ 接收侧：**
```
**`Netchan_Process` = `0x005A5960`**
        ↓
★★★ 拥有**独立的接收序列号 + 聚合长度 + 四字位图**
        ↓
★★★ 且 memory 已记录："权威来源 = ol-mod `net_chan_mp.cpp` **CODREF 0x005A5960**"
   ⇒ ★★ **两处一致** ✓
```

### 4.2 ★★★★ `NetchanState` 的**发送侧**字段（第 101–107 行）

```cpp
bool unsentFragments{};
bool reliableFragments{};
std::uint32_t unsentLength{};
std::vector<std::uint8_t> unsentBuffer;
std::array<std::uint8_t, NetchanMaximumFragments> fragmentSendCount{};   // 128
std::array<std::uint32_t, 4> fragmentAcknowledgements{};                 // ★ 4 字
std::uint32_t lowestFragmentSendCount{};
```

### ★★★★★ `NetchanState` 的**接收侧**字段（第 111–116 行）

```cpp
std::uint32_t fragmentSequence{};
std::uint32_t fragmentLength{};
std::uint16_t fragmentStride{};          // ★★ stride（= 1154）
std::uint8_t lastFragmentIndex{};
std::array<std::uint32_t, 4> receivedFragmentBits{};   // ★★ 4 字位图 = 128 位
std::vector<std::uint8_t> fragmentBuffer;
```

★★★★★ **⇒ 位图与分片数的**精确对应**：**
```
`receivedFragmentBits` = **4 × u32 = 128 位**
`NetchanMaximumFragments` = **128**
        ↓
★★★★★ ⇒ **一位一个分片,128 位正好覆盖 128 个分片** ✓
```

★★ **⇒ 与 memory 的「FAT 分片帧真实布局」对照：**
```
memory："10 字节头 index/last/**stride(1154)**/length"
        ↓
本报告：`fragmentStride`（u16）+ `lastFragmentIndex`（u8）+ `fragmentLength`（u32）
        + `fragmentSequence`（u32）
        ↓
★★★ ⇒ **字段名完全对应**（index / last / stride / length）✓
   ⇒ 而 `stride = 1154` 由 `NetchanFragmentSize` 给出
```

### ★★★ `NetchanProcessKind` 的 5 种结果（第 119–126 行）

```cpp
enum class NetchanProcessKind : std::uint8_t
{
    Accepted,               // 接受
    FragmentPending,        // ★ 分片未完成
    FragmentAcknowledgement,// ★ 分片确认
    Duplicate,              // 重复
    Rejected,               // 拒绝
};
```

★★ **⇒ 5 种结果,含 2 种分片专用状态。**

---

## 五、★★★★★ **`userCmdKey` 的三重异或（"不可从解码字节恢复"）**

### 5.1 ★★★★★ 完整注释（第 132–139 行，逐字）

```cpp
// OLMOD(section-88): THE KEY THE USERCMD DELTAS WERE READ WITH, so a
// captured stream can be REPLAYED. Every `changed` bit in a usercmd is
// keyed, so a capture decoded under one key is noise under another --
// which is why the first attempt to turn a real capture into a golden
// produced `changed=0 full=0 bitsAtTrailer=0` instead of the field it
// was aimed at. It is `checksumFeed ^ messageAcknowledge ^
// Com_HashKey(serverReliableCommand)`, and none of those three are
// recoverable from the decoded bytes.
std::uint32_t userCmdKey{};
```

### ★★★★★ 完整的密钥公式

```
**`userCmdKey = checksumFeed ^ messageAcknowledge ^ Com_HashKey(serverReliableCommand)`**
        ↓
★★★ 三个来源：
  **`checksumFeed`**              ⇒ 来自 gamestate
  **`messageAcknowledge`**        ⇒ 来自包
  **`Com_HashKey(serverReliableCommand)`** ⇒ 来自可靠命令的哈希
        ↓
★★★★★ 且明确：**"none of those three are recoverable from the decoded bytes"**
```

### ★★★★★ 一次实测失败的完整记录（逐字）

```
"Every `changed` bit in a usercmd is **keyed**, so a capture decoded under
 one key is **noise under another** -- which is why **the first attempt** to turn
 a real capture into a golden produced
 **`changed=0 full=0 bitsAtTrailer=0`**
 instead of the field it was aimed at."
        ↓
★★★ ⇒ **第一次尝试的失败症状：`changed=0 full=0 bitsAtTrailer=0`**
   ⇒ 即：**所有 `changed` 位都是 0,所有字段都是"未改变"** ⇒ 看起来像"没有数据"
   ⇒ 但真相是**密钥不对**（解出来是噪声,所以所有位都判为"未变"）
```

★★★★★ **⇒ 这是一条**极高价值的诊断线索**：**
```
若看到 **`changed=0 full=0 bitsAtTrailer=0`**
        ↓
★★★ **不要**判成"没有数据" ⇒ **要怀疑密钥错误**
```

★ **⇒ 与既有 memory 的「快照索引 run 编码必须 4 位」/「快照字段级离线对照」**同一类
（都是"看起来没数据,实际是解码参数错"）。**

---

## 六、★★★★ `Com_HashKey` 的签名（第 162–164 行）

```cpp
[[nodiscard]] std::uint32_t Com_HashKey(
    std::string_view value,
    std::size_t maxLength = 32);      // ★ 默认 32 字符
```

★★ **⇒ 哈希只取**前 32 个字符**（默认）。**

### ★★★ `Netchan_XorCommands` 的签名（第 158–161 行）

```cpp
[[nodiscard]] std::vector<std::uint8_t> Netchan_XorCommands(
    std::span<const std::uint8_t> payload,
    std::uint32_t seed,
    std::string_view reliableCommand = {});
```

★★ **⇒ 异或命令的 seed + 可选可靠命令（与 `userCmdKey` 的公式对应）。**

### ★★★ 两个 resolver（第 153–156 行）

```cpp
using NetchanReliableCommandResolver = std::function<
    std::optional<std::string>(std::uint32_t reliableAcknowledge)>;
using NetchanDefaultUserCmdResolver = std::function<
    UserCmd(std::uint32_t messageAcknowledge)>;
```

★★ **⇒ 两个回调让调用方注入"可靠命令"与"默认 usercmd"。**

### ★★★ 四个导出函数

| 函数 | 用途 |
|---|---|
| **`NET_IsConnectionlessPacket`** | 判断无连接包 |
| **`Netchan_XorCommands`** | 异或命令 |
| **`Netchan_Process`** | ★ 处理入站包 |
| **`Netchan_Transmit`** | 发送 |
| **`Netchan_TransmitNextFragment`** | ★ 发送下一个分片 |

### ★★★ `ClientNetchanPacket` 的 5 个字段（第 80–87 行）

```cpp
struct ClientNetchanPacket
{
    std::uint32_t sequence{};
    std::uint8_t serverId{};
    std::uint32_t messageAcknowledge{};
    std::uint32_t reliableAcknowledge{};
    std::span<const std::uint8_t> encodedCommands;
};
```

### ★★★ `ClientPredictedState`（第 64–69 行）

```cpp
struct ClientPredictedState
{
    std::array<std::uint32_t, 5> values{};   // ★ 5 个值
};
```

★ **⇒ 客户端预测状态是 **5 个 u32**（具体含义未在此文件命名）。**

### ★★★ `ClientCommandKind` 的 5 种（第 71–78 行）

```cpp
enum class ClientCommandKind : std::uint8_t
{
    MoveDelta   = 0,
    MoveNoDelta = 1,
    Reliable    = 2,
    Eof         = 3,
    Invalid     = 0xFF,
};
```

★★ **⇒ 与常量 `ClientCommandReliable = 2` / `ClientCommandEof = 3` **完全一致** ✓**

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★ **序列号掩码** | **`0x1FFFFFFF`** = **29 位** |
| 2 | ★★★★★ **`NetchanFragmentSize = 1154`** | ✓ 与 memory 的「FAT 分片 stride **1154**」**两处独立确认** |
| 3 | ★★ `NetchanMaximumFragments` | **128** |
| 4 | ★★ `NetchanMaximumFragmentedMessage` | **`0x20000` = 131,072** ⇒ 只需 **114** 个分片 ⇒ 128 是留余量 |
| 5 | ★★★★★ **OLfinal EOF = 5** | **3.3.3.3 用 6,OLfinal 用 5** |
| 6 | ★★★★★ **三重实测** | ① **54,682 / 54,682** demo 快照 payload 的**最后字节** = 5（**100%**）② gamestate 的 configstring 块结束 token ③ `clientNum`/`checksumFeed` 对之后的字节 |
| 7 | ★★★★ **完整 opcode 表** | 0 snapshot / 1 serverCommand / 2 binary serverCommand / 3 gamestate / 4 configstring block start / ★ **5 EOF（OLfinal）** / ★ **6 EOF（3.3.3.3,OLfinal 无）** |
| 8 | ★★★★★ **用 6 的后果** | "not merely read wrong -- it **falls through to the parse loop's error exit**" |
| 9 | ★★ 出处 | `re/demo-re/01-container.md sec 4` + `06-olevents.md sec 2` |
| 10 | ★★★★ **`UserCmd` 15 字段** | `commandTime` / `buttons` / `angles[3]` / `weapon` / `offHandIndex` / `lastWeaponAltModeSwitch` / `forwardMove` / `rightMove` / `conditionalAngle` / `conditionalByte` / **`conditionalElevenBits`** / `selectedLocation[3]` / `selectedDirection[2]` |
| 11 | ★★★★★ **`+0x16` vs `+0x18` 的精确 CODREF** | **`0x5B2241`** 写 `cg.equippedOffHand`（经 **`clientActive+0x3C64`**）→ **`usercmd+0x18`**；而 **`+0x16`** 来自 **`cg+0xC7238`** 的**每武器查表** ⇒ **`+0x18` 才是 equipped offhand** |
| 12 | ★★★ `CODREF(1649370)` | ✓ 与报告 077 的 **`build_number=1649370`** 完全吻合 |
| 13 | ★★ `conditionalElevenBits` | 字段名直接写 **11 位** ⇒ 与 `bulletHitEntityNum = 2047` 同一编码空间 |
| 14 | ★★★ 三个 `conditional*` | 说明是**条件性字段**（取决于标志位） |
| 15 | ★★★★ **发送侧 CODREF 三地址** | **`0x005A5490`** / **`0x005A55F0`** / **`0x005A5720`** ⇒ "retain one outgoing message under a **stable sequence** and send **indexed 1154-byte fragments** until completion" |
| 16 | ★★★★ **接收侧 CODREF** | **`Netchan_Process = 0x005A5960`** ⇒ 独立接收序列 + 聚合长度 + **四字位图** ✓ 与 memory 一致 |
| 17 | ★★★★★ **位图与分片数精确对应** | `receivedFragmentBits` = **4 × u32 = 128 位** ⇔ `NetchanMaximumFragments` = **128** ⇒ **一位一片** |
| 18 | ★★★ 接收字段对应 memory | `fragmentStride`(u16) + `lastFragmentIndex`(u8) + `fragmentLength`(u32) + `fragmentSequence`(u32) ⇔ memory 的「index/last/stride/length」 ✓ |
| 19 | ★★ `NetchanProcessKind` | **Accepted / FragmentPending / FragmentAcknowledgement / Duplicate / Rejected**（5 种） |
| 20 | ★★★★★ **`userCmdKey` 公式** | **`checksumFeed ^ messageAcknowledge ^ Com_HashKey(serverReliableCommand)`** |
| 21 | ★★★★★ **"不可恢复"** | "**none of those three are recoverable from the decoded bytes**" |
| 22 | ★★★★★ **一次实测失败的症状** | **`changed=0 full=0 bitsAtTrailer=0`** ⇒ ★ **不要判成"没数据",要怀疑密钥错** |
| 23 | ★★ `Com_HashKey` 默认长度 | **32** 字符 |
| 24 | ★ `ClientPredictedState` | **5 个 u32** |
| 25 | ★★ `ClientCommandKind` 5 种 | `MoveDelta 0` / `MoveNoDelta 1` / **`Reliable 2`** / **`Eof 3`** / `Invalid 0xFF` |

---

## 八、结论

### 1. ★★★★★ **OLfinal 用 opcode 5 结束消息,而 3.3.3.3 用 6 —— 有 54,682/54,682 的实测**

```
★★★ **100% 命中**（54,682 个 demo 快照 payload 的最后字节都是 5）
        ↓
★★★ 且 **OLfinal 根本没有 opcode 6**
   ⇒ 用 6 结束的消息**不是"读错",而是直接走解析循环的错误出口**
        ↓
★★★★★ ⇒ **这条差异解释了为什么照抄 3.3.3.3 的实现会失败**
   ⇒ 且 memory 里"ol-mod 自己写了这条差异"的记录现在有完整上下文与证据
```

### 2. ★★★★★ **`1154` 分片大小与 memory 的「FAT 分片 stride 1154」两处独立确认**

### 3. ★★★★★ **`userCmdKey` 的三重异或与"不可从解码字节恢复"**

★ **⇒ 且记录了一次实测失败的**精确症状**：`changed=0 full=0 bitsAtTrailer=0` ⇒ **密钥错的标志**。**

### 4. ★★★★★ **`UserCmd` 的 `+0x16` vs `+0x18` 有精确 CODREF**

```
`+0x18` = **`cg.equippedOffHand`**（经 `clientActive+0x3C64`）
`+0x16` = **`cg+0xC7238`** 的每武器查表
        ↓
★★★ ⇒ **两者语义容易搞反**,注释明确纠正
```

### 5. ★★★★ **netchan 分片的位图与分片数精确对应**（4 字 = 128 位 ⇔ 128 分片）

### 6. ★★★ **`CODREF(1649370)` 与 `build_number=1649370` 吻合**

---

## 九、下一步

- `qcommon\net_chan_mp.cpp`（50,686 B / **1,106 行**）—— 实现层
- `qcommon\net_dtls_cod.cpp`（34,426 B / 765 行）+ `.hpp`
- `qcommon\msg_mp.cpp` / `.hpp` / `com_math.hpp` / `net_types.hpp`
