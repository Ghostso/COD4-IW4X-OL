# 学习报告 099（重开）— `qcommon\net_chan_mp.cpp`（50,686 B / 1,106 行）

**学习范围**：`game_server\qcommon\net_chan_mp.cpp` 全文（**1,106 行逐行读完**）
**性质**：全实测
**★★★★★ 本报告收录六个重大发现**：①**武器索引 10→11 位的完整 bug 与症状** ②**分片头 10 字节的精确布局** ③**三个序列标志位** ④**`Com_HashKey` 的精确算法** ⑤**可靠命令环的"跳号不可修复"** ⑥**两处"一次失败要花一整轮"的教训**

---

## 一、★★★★★ **武器索引 10 → 11 位（一个已修复的完整 bug）**

### 1.1 ★★★★★ 完整注释（第 350–361 行，逐字）

```cpp
// CODDIFF(1649370): THESE ARE WEAPON INDICES AND THEY ARE ELEVEN BITS HERE.
// sv_gamestate_mp.cpp already carries the derivation -- "the weapon block grew
// 900 -> 1700 entries, so the weapon index widened 10 -> 11", WeaponIndexBits =
// 11 -- and this decoder is 3.3.3.3's verbatim, still reading ten.
//
// It fails exactly the way a one-bit-per-field shortfall must. A delta field
// costs nothing while it is UNCHANGED, so an idle client parses perfectly: the
// log shows hundreds of clean commands. The moment a player spawns and holds a
// weapon the field starts changing, three fields read one bit short each, and
// the stream slips. The reported failure is always the trailer, which is merely
// where the damage becomes visible -- the trace shows buttons decoding to
// 0x146574C3 and gates opening at random by then.
constexpr std::uint32_t UserCmdWeaponIndexBits = 11;
```

### ★★★★★ 完整的 bug 因果链

```
① ★★★ **武器块从 900 增至 1700 项** ⇒ **武器索引从 10 位加宽到 11 位**
   （`sv_gamestate_mp.cpp` 已有推导：`WeaponIndexBits = 11`）
        ↓
② ★★★ 但本解码器是 **3.3.3.3 的逐字复制,仍在读 10 位**
        ↓
③ ★★★★★ **为什么"空闲时完美、一开枪就崩"**（逐字）：
   "A delta field **costs nothing while it is UNCHANGED**,
    so an **idle client parses perfectly**: the log shows **hundreds of clean commands**."
        ↓
④ ★★★ **玩家一出生并持枪** ⇒ **该字段开始变化**
   ⇒ **三个字段各少读 1 位** ⇒ **流错位**
        ↓
⑤ ★★★★★ **报错永远指向 trailer**（逐字）：
   "The reported failure is **always the trailer**, which is merely
    **where the damage becomes visible**"
        ↓
⑥ ★★★★ **trace 显示 `buttons` 解到 `0x146574C3`**,且此时**门控随机打开**
```

### ★★★★★ 三个受影响的字段（第 363–369 行）

```cpp
const std::array weaponIndexFields{
    std::pair{ &command.weapon,                  baseline.weapon },
    std::pair{ &command.lastWeaponAltModeSwitch, baseline.lastWeaponAltModeSwitch },
    std::pair{ &command.offHandIndex,            baseline.offHandIndex },
};
```

★★★ **⇒ 恰好**三个**字段（与注释的"three fields read one bit short each"吻合）。**

★★ **⇒ 每次少读 1 位 × 3 个字段 = **3 位错位**。**

### ★★★★ 为什么"delta 未变时不花位"

```
`readDelta` 的逻辑（第 145–167 行）：
  ① 先读 **1 位 `changed`**
  ② 若 `changed == 0` ⇒ **直接用 baseline,不读任何字段位**
  ③ 若 `changed == 1` ⇒ 读 `bits` 位
        ↓
★★★ ⇒ **空闲时三个武器字段都是 `changed = 0`** ⇒ 各只花 1 位
   ⇒ **10 位 vs 11 位的差异完全暴露不出来**
        ↓
★★★★★ ⇒ 这就是"**hundreds of clean commands**"的原因
```

★★ **⇒ 这是一个**极好的"潜伏 bug"范例**：位宽错误的代价只在**字段真的变化**时才显现。**

---

## 二、★★★★★ **`readDeltaUserCmd` 的完整位布局**

### 2.1 ★★★★★ 分阶段读取顺序（第 212–473 行）

| 阶段 | 读什么 | 位数 | 条件 |
|---|---|---|---|
| **1** | `deltaTime` 标志 | **1** | 总是 |
| **2a** | 若 `deltaTime` ⇒ `delta`（相对） | **8** | `deltaTime == 1` |
| **2b** | 否则 ⇒ `absolute`（绝对） | **32** | `deltaTime == 0` |
| **3** | `changed`（经 `readKey`） | **1** | 总是 |
| **4** | 若 `!changed` ⇒ `trailer` 必须 = **7** | **3** | `changed == 0` |
| **5** | `full`（经 `readKey`） | **1** | `changed == 1` |
| **6** | `attack`（经 `readKey`） | **1** | 总是 |
| **7** | `angles[0]` / `angles[1]` delta | **1 + 16** | 每个 |
| **8** | `movement` delta | **1 + 4** | 总是 |
| **9** | 若 `!full` ⇒ `trailer` 必须 = **2** | **3** | `full == 0` |
| **10** | `angles[2]`（roll）delta | **1 + 16** | `full == 1` |
| **11** | `buttons`（29 位）delta | **1 + 29** | `full == 1` |
| **12** | **三个武器索引** delta | **3 × (1 + 11)** | `full == 1` |
| **13** | 若 `buttons & 0x20000` ⇒ `selectedLocation[3]` | **3 × (1 + 8)** | 条件 |
| **14** | 若 `buttons & 0x200000` ⇒ `selectedDirection[2]` | **2 × (1 + 8)** | 条件 |
| **15** | 若 `buttons & 0x4` ⇒ 三个 conditional 字段 | **3 组** | 条件 |
| **16** | `trailer` 必须 = **5**（full）或 **2**（partial） | **3** | 总是 |

### ★★★★★ 三个 trailer 的精确值

```
`changed == 0`（未变）      ⇒ trailer 必须 = **7**
`changed == 1, full == 0`   ⇒ trailer 必须 = **2**
`changed == 1, full == 1`   ⇒ trailer 必须 = **5**
        ↓
★★★ ⇒ 三个不同的哨兵值（7 / 2 / 5）
```

### ★★★★★ **三个条件门控的精确位掩码**（第 387–389 / 391 / 409 / 427 行）

```cpp
trace->selectedLocation  = (command.buttons & 0x20000u)  != 0;   // bit 17
trace->selectedDirection = (command.buttons & 0x200000u) != 0;   // bit 21
trace->conditional       = (command.buttons & 4u)        != 0;   // bit 2
```

| 门控 | 掩码 | 位 | 附加字段 |
|---|---|---|---|
| **`selectedLocation`** | **`0x20000`** | **17** | `selectedLocation[3]`（3 × 8 位） |
| **`selectedDirection`** | **`0x200000`** | **21** | `selectedDirection[2]`（2 × 8 位） |
| **`conditional`** | **`0x4`** | **2** | 三个 conditional 字段 |

### ★★★★★ conditional 块的三个字段（第 427–463 行）

```cpp
if (command.buttons & 4u)
{
    // ① conditionalAngle：16 位定点
    const auto baselineAngle = static_cast<std::uint16_t>(
        static_cast<std::int16_t>(baseline.conditionalAngle * **182.0444488525391f**));
    readDelta(..., 16, baselineAngle, value, readShort);
    command.conditionalAngle = static_cast<float>(
        static_cast<std::int16_t>(value)) * **0.0054931640625f**;
    // ② conditionalByte：8 位
    readDelta(..., 8, baseline.conditionalByte, value, readBits(8));
    // ③ conditionalElevenBits：11 位
    readDelta(..., 11, baseline.conditionalElevenBits, value, readBits(11));
}
```

★★★★★ **⇒ 两个精确的定点转换常量：**
```
`182.0444488525391f`  ≈ **65536 / 360** = **182.0444…**  ⇒ **角度 → 16 位**
`0.0054931640625f`    = **360 / 65536** = **0.0054931…**  ⇒ **16 位 → 角度**
        ↓
★★★ ⇒ **互为倒数**（1/182.0444488525391 = 0.0054931640625）
   ⇒ 即：**conditionalAngle 是 16 位定点角度**（全圆 = 65536）
```

★★ **⇒ `conditionalElevenBits` 确认是 **11 位**（与报告 098 的字段名一致）。**

---

## 三、★★★★★ **`UserCmdTrace`：为离线重放设计的诊断结构**

### 3.1 ★★★★★ 完整注释（第 189–199 行，逐字）

```cpp
// WHAT THE DECODER SAW, SO A REJECTION CAN BE REPLAYED OFFLINE.
// The usercmd reader survives hundreds of commands and then desyncs, which means a
// width or a gate is wrong on a field the IDLE path never exercises -- it only shows
// once a player is spawned and pressing things. A rejection reason names the last
// check to fail, never the field that consumed the wrong number of bits, and those
// are different fields by construction: the trailer is simply where the damage
// becomes visible.
//
// So record the branch taken and every conditional gate, and let the caller print it
// beside the raw bits. Then the desync can be found by hand against the bit stream
// instead of by another cycle per guess.
```

★★★★★ **⇒ 两条核心洞察：**
```
① ★★★ **"a rejection reason names the last check to fail,
   **never the field that consumed the wrong number of bits**"**
   ⇒ **报错点 ≠ 出错点**（这是位流解析的根本困难）
        ↓
② ★★★ **"the trailer is simply where the damage becomes visible"**
   ⇒ trailer 只是**损伤显现的地方**
        ↓
★★★★★ 对策："record the branch taken and every conditional gate"
   ⇒ 让调用方**把 trace 打在原始位流旁边** ⇒ **手工对位流定位**
   ⇒ "instead of **another cycle per guess**"
```

### ★★★ `UserCmdTrace` 的 8 个字段（第 200–210 行）

```cpp
struct UserCmdTrace
{
    std::uint32_t deltaTime{};
    std::uint32_t changed{};
    std::uint32_t full{};
    std::uint32_t buttons{};
    bool selectedLocation{};
    bool selectedDirection{};
    bool conditional{};
    std::size_t bitsAtTrailer{};
};
```

### ★★★★★ trace 的实际打印格式（第 568–580 行）

```cpp
result.reason += " [buttons=0x" + <hex8> +
    " deltaTime=" + trace.deltaTime +
    " changed=" + trace.changed +
    " full=" + trace.full +
    " gates=" + (selectedLocation ? "L" : "-") +
               (selectedDirection ? "D" : "-") +
               (conditional ? "C" : "-") +
    " bitsAtTrailer=" + trace.bitsAtTrailer + "]";
```

★★★★★ **⇒ 完整的诊断串格式：**
```
`... [buttons=0x146574C3 deltaTime=1 changed=1 full=1 gates=LDC bitsAtTrailer=347]`
        ↓
★★★ `gates=LDC` ⇒ **L**ocation / **D**irection / **C**onditional 三个门控都开了
```

---

## 四、★★★★★ **`parseClientCommands` 与"链起点"的关键修复**

### 4.1 ★★★★★ 完整注释（第 535–549 行，逐字）

```cpp
// THE CHAIN START IS THE ACKNOWLEDGED PLAYERSTATE BASELINE.
//
// CODREF(cl_write_packet): OLFinal 1649370 CL_WritePacket
// 0x005B2C10 calls MSG_SetDefaultUserCmd 0x0066F170 once before
// choosing clc_move/clc_moveNoDelta, stores that local command as
// the first baseline, then advances the baseline only inside the
// packet's MSG_WriteDeltaUsercmdKey loop. It never starts a packet
// from the previous packet's usercmd.
//
// The previous-command override was fatal during Wetwork's turret
// intro. It retained button 0x4 across the packet boundary, so this
// reader entered the optional 35-bit conditional block even though
// the client had encoded against a zeroed default and omitted it.
// Every spawned-player packet then failed at the trailer and no
// mouse input reached pmove.
```

### ★★★★★ 两个精确地址

```
**`CL_WritePacket = 0x005B2C10`**
**`MSG_SetDefaultUserCmd = 0x0066F170`**
        ↓
★★★ 语义（逐字）："calls MSG_SetDefaultUserCmd once **before** choosing
 clc_move/clc_moveNoDelta, **stores that local command as the first baseline**,
 then advances the baseline **only inside the packet's MSG_WriteDeltaUsercmdKey loop**.
 It **never starts a packet from the previous packet's usercmd**."
```

### ★★★★★ 一个致命的实测故障（逐字）

```
"**The previous-command override was fatal during Wetwork's turret intro.**
 It **retained button `0x4` across the packet boundary**,
 so this reader **entered the optional 35-bit conditional block**
 even though the client had **encoded against a zeroed default and omitted it**.
 **Every spawned-player packet then failed at the trailer and
 no mouse input reached pmove.**"
        ↓
★★★ 完整因果链：
  ① 旧实现**跨包保留了上一包的 usercmd 作为 baseline**
  ② 上一包有 `buttons & 0x4`（conditional 门控开）
  ③ ⇒ 本包**进入了 35 位的 conditional 块**
  ④ 但客户端**是对零值 default 编码的,压根没写这个块**
  ⑤ ⇒ **每个出生后的包都在 trailer 处失败**
  ⑥ ⇒ **鼠标输入从未到达 pmove**
```

★★★ **⇒ 第 ③ 条的 "**35-bit conditional block**" 是一个精确的位宽：**
```
conditional 块 = ① `conditionalAngle`（1 + 16）
                + ② `conditionalByte`（1 + 8）
                + ③ `conditionalElevenBits`（1 + 11）
        ↓
★★★ **= 3 + 16 + 8 + 11 = 38**（含 3 个 changed 位）
   ⇒ 若只算数据位：16 + 8 + 11 = **35** ✓
        ↓
★★★★★ ⇒ **"35-bit conditional block" 指的是数据位总和** ✓
```

### ★★★ 修复（第 550 行）

```cpp
auto baseline = defaultUserCmd;      // ★ 每包都从 default 开始
```

★ **⇒ 即：**每包都用 `defaultUserCmd` 作 baseline**,不跨包继承。**

### ★★★ "重复旧命令仍接受"的理由（第 584–589 行，逐字）

```cpp
// COD's SV_UserMove still accepts the packet when a
// client repeats an old command in its move window.
// Server-side command watermarks discard it after
// netchan state and ACKs have advanced. Rejecting the
// whole packet would make the client retransmit the
// same window forever.
```

★★★ **⇒ 若因"重复命令"拒包 ⇒ **客户端会永远重传同一窗口**（死锁）。**
**⇒ 所以**接受,由服务端水印丢弃**。**

---

## 五、★★★★★ **分片传输：10 字节头的精确布局与三个标志位**

### 5.1 ★★★★★ 三个序列标志位（第 692–696 行，逐字）

```cpp
// CODREF(netchan_fragment): CODOL 0x005A5960 uses sequence flags
// 0x80000000 fragmented, 0x40000000 reliable and 0x20000000 fragment
// acknowledgement. Its fragment header is index, last-index,
// 1154-byte stride and payload length; it is not the older
// qport/start/length layout.
```

| 标志 | 掩码 | 含义 |
|---|---|---|
| **`fragmented`** | ★ **`0x80000000`** | 分片（bit 31） |
| **`reliable`** | ★ **`0x40000000`** | 可靠（bit 30） |
| **`fragment acknowledgement`** | ★ **`0x20000000`** | 分片确认（bit 29） |

★★ **⇒ 三个高位依次是 31 / 30 / 29。**
**⇒ 而 `NetchanSequenceMask = 0x1FFFFFFF`（29 位）⇒ 正好避开这三个高位 ✓**

### ★★★★★ 10 字节分片头的精确布局

```cpp
constexpr std::size_t FragmentHeaderSize = 10;
const auto sequence            = rawSequence & NetchanSequenceMask;  // 偏移 0-3（低 29 位）
const auto reliable            = (rawSequence & 0x40000000u) != 0;
const auto acknowledgement     = (rawSequence & 0x20000000u) != 0;
const auto fragmentIndex       = packet[4];                          // 偏移 4
const auto lastFragmentIndex   = packet[5];                          // 偏移 5
const auto fragmentStride      = packet[6] | packet[7] << 8;         // 偏移 6-7（u16 LE）
const auto fragmentLength      = packet[8] | packet[9] << 8;         // 偏移 8-9（u16 LE）
```

| 偏移 | 大小 | 字段 |
|---|---|---|
| **0–3** | 4 | ★ `sequence`（低 29 位）+ 3 个标志位 |
| **4** | 1 | ★ `fragmentIndex` |
| **5** | 1 | ★ `lastFragmentIndex` |
| **6–7** | 2 | ★★ `fragmentStride`（**= 1154**） |
| **8–9** | 2 | ★ `fragmentLength` |

★★★★★ **⇒ 与 memory 的「FAT 分片帧真实布局」**逐字段吻合**：**
```
memory："**10 字节头** index/last/stride(1154)/length"
        ↓
本报告：**10 字节头** = sequence(4) + index(1) + last(1) + stride(2) + length(2) ✓
        ↓
★ 而 memory 记的"10 字节头"里**没算 sequence** ⇒ 现在明确了：
  **sequence 在前 4 字节,分片元数据在后 6 字节**
```

★★★ **⇒ 且明确"**it is not the older qport/start/length layout**"**
**⇒ 即：这不是老式的 `qport/start/length` 布局。**

### ★★★★★ 分片校验的**七重条件**（第 748–754 行）

```cpp
if (!sequence ||
    fragmentIndex > lastFragmentIndex ||
    lastFragmentIndex >= NetchanMaximumFragments ||          // 128
    fragmentStride != NetchanFragmentSize ||                 // 1154
    fragmentLength > fragmentStride ||
    packet.size() < FragmentHeaderSize + fragmentLength ||
    (fragmentIndex != lastFragmentIndex && fragmentLength != fragmentStride))
```

★★★ **⇒ 七条：**
```
① `sequence != 0`
② `fragmentIndex <= lastFragmentIndex`
③ `lastFragmentIndex < 128`
④ **`fragmentStride == 1154`**（严格相等）
⑤ `fragmentLength <= fragmentStride`
⑥ 包长度 ≥ 10 + `fragmentLength`
⑦ ★★ **非最后一片时 `fragmentLength` 必须恰为 `stride`**（即只有最后一片可以短）
```

### ★★★ 确认包的构造（第 766–774 行）

```cpp
appendU32(controlReply, sequence | **0xA0000000u**);    // ★ bit31 + bit29
controlReply.push_back(fragmentIndex);
controlReply.push_back(lastFragmentIndex);
controlReply.push_back(stride 低字节); controlReply.push_back(stride 高字节);
controlReply.push_back(length 低字节); controlReply.push_back(length 高字节);
for (index < 4) appendU32(controlReply, **0xFFFFFFFF**);   // ★ 4 个全 1
```

★★★ **⇒ 确认包的标志是 `0xA0000000` = **bit31（分片）+ bit29（确认）**,**不含 bit30（可靠）**。**
**⇒ 且尾部 4 个 u32 全 `0xFFFFFFFF`（= 128 位全 1 位图 ⇒ "全部收到"）。**

### ★★★ 可靠分片的确认回复（第 823–831 行）

```cpp
appendU32(fragmentControlReply, sequence | **0xA0000000u**);
...
for (const auto acknowledgementWord : chan.receivedFragmentBits)
    appendU32(fragmentControlReply, acknowledgementWord);   // ★ 真实的 4 字位图
```

★ **⇒ 与"确认包"的区别：这里回的是**真实位图**（不是全 1）。**

### ★★★★★ 选择性重传的理由（第 1037–1043 行，逐字）

```cpp
// CODREF(1649370 Netchan_TransmitNextFragment 0x6743D0):
// fragmented messages use CODOL's selective-repeat transport.
// Bit 30 declares that mode, the peer returns bit 29 plus the
// 128-bit acknowledgement bitmap, and outgoingSequence advances
// only after every fragment is acknowledged.  Sending these as
// bit-31-only fire-and-forget packets made one lost gamestate or
// large snapshot fragment discard the complete message.
```

★★★★★ **⇒ 完整机制 + 一个已修复的故障：**
```
**`Netchan_TransmitNextFragment = 0x6743D0`**
        ↓
★★★ **bit 30 声明"选择性重传"模式**
   ⇒ 对端回 **bit 29 + 128 位确认位图**
   ⇒ **`outgoingSequence` 只在所有分片都被确认后才前进**
        ↓
★★★ **旧实现：只发 bit31（fire-and-forget）**
   ⇒ **丢失一个 gamestate 或大快照分片 ⇒ 整条消息作废**
```

★ **⇒ 与报告 071 的 `zm.lua` SPAWN_BACKOFF、报告 094 的 NoclipRequest 保活**同一类"**丢包必须可恢复**"的设计。**

### ★★★ 分片选择算法（第 1092–1123 行）

```cpp
if (chan.reliableFragments)
{
    while (true)
    {
        for (fragmentIndex = 0; fragmentIndex < fragmentCount; ++fragmentIndex)
        {
            if (chan.fragmentSendCount[fragmentIndex] <= chan.lowestFragmentSendCount &&
                (chan.fragmentAcknowledgements[fragmentIndex >> 5u] &
                    (1u << (fragmentIndex & 31u))) == 0)
            {
                goto fragment_selected;
            }
        }
        ++chan.lowestFragmentSendCount;    // ★ 所有片都超过水位 ⇒ 抬高水位重试
    }
}
```

★★★ **⇒ 一个**"最低发送次数水位"的公平调度**：**
```
优先选"发送次数 ≤ 水位 且 未被确认"的分片
        ↓
若没有 ⇒ **抬高水位**,重新扫
        ↓
★★★ ⇒ 保证**发送次数少的分片优先**,避免某片被饿死
```

★ **⇒ 非可靠模式（`else` 分支）用简单的"第一个未发送的"（`fragmentSendCount == 0`）。**

### ★★★★★ `OLMOD(netchan-owned-buffer)` 的差异声明（第 1112–1114 行，逐字）

```cpp
// OLMOD(netchan-owned-buffer): unlike native netchan_t, the source
// retains the complete immutable message and derives progress from
// send counts instead of advancing a raw buffer pointer.
```

★★★ **⇒ 与原生 `netchan_t` 的关键差异：**
```
原生 ⇒ **推进一个原始缓冲区指针**
本实现 ⇒ **保留完整不可变消息 + 从发送次数推导进度**
        ↓
★★★ 好处：**选择性重传成为可能**（原生指针推进后无法回头重发）
```

---

## 六、★★★★★ **`Com_HashKey` 的精确算法**

### 6.1 ★★★ 完整实现（第 647–658 行）

```cpp
std::uint32_t Com_HashKey(const std::string_view value, const std::size_t maxLength)
{
    std::int32_t hash{};
    const auto length = std::min(value.size(), maxLength);
    for (std::size_t index = 0; index < length && value[index]; ++index)
    {
        hash += static_cast<std::int8_t>(value[index]) *
            static_cast<std::int32_t>(**119 + index**);
    }
    const auto unsignedHash = static_cast<std::uint32_t>(hash);
    return unsignedHash ^ ((unsignedHash ^ (unsignedHash >> 10)) >> 10);
}
```

### ★★★★★ 完整的算法描述

```
① `hash` = **int32 0**
② 对每个字符（最多 `maxLength` = **32** 个,遇 NUL 停止）：
   `hash += (int8)ch * (119 + index)`
        ↓
★★★ 注意：字符按 **`int8_t`** 解释（**有符号**！）⇒ ≥0x80 的字符是**负数**
        ↓
③ 收尾：`unsignedHash ^ ((unsignedHash ^ (unsignedHash >> 10)) >> 10)`
        ↓
★★★ ⇒ 与 IW/CoD 的 `Com_HashKey` **完全一致**（经典实现）
```

★★ **⇒ 第 ③ 条的收尾是**"两轮 10 位右移异或"**（一种廉价混淆）。**

★★★ **⇒ 第 ② 条的 `119 + index` 意味着**字符位置参与权重**（`index` 从 0 起,基值 119）。**

---

## 七、★★★★★ **`Netchan_XorCommands` 的精确算法**

### 7.1 ★★★ 完整实现（第 623–645 行）

```cpp
std::vector<std::uint8_t> Netchan_XorCommands(
    const std::span<const std::uint8_t> payload,
    const std::uint32_t seed,
    const std::string_view reliableCommand)
{
    auto key = static_cast<std::uint8_t>(seed);     // ★ 只用 seed 的低 8 位
    std::size_t commandIndex{};
    std::vector<std::uint8_t> result;
    result.reserve(payload.size());
    for (std::size_t index = 0; index < payload.size(); ++index)
    {
        std::uint8_t commandByte{};
        if (!reliableCommand.empty())
        {
            if (commandIndex >= reliableCommand.size() || !reliableCommand[commandIndex])
                commandIndex = 0;                   // ★ 循环（遇 NUL 或到头则回绕）
            commandByte = static_cast<std::uint8_t>(reliableCommand[commandIndex++]);
        }
        key ^= static_cast<std::uint8_t>(commandByte << (index & 1));   // ★ 交替左移 0/1
        result.push_back(payload[index] ^ key);
    }
    return result;
}
```

★★★★★ **⇒ 完整算法：**
```
`key` 初值 = **`seed & 0xFF`**
        ↓
对每个字节 index：
  `commandByte` = 可靠命令的第 `commandIndex` 个字节（循环取）
  ★★ `key ^= (commandByte << (index & 1))`      ← **交替左移 0 或 1 位**
  `output[index] = payload[index] ^ key`
        ↓
★★★ ⇒ **密钥是流式的**（每字节更新一次）
   ⇒ 且**交替左移**产生 2 周期变化
```

★★ **⇒ 第 `commandByte << (index & 1)` 的 `index & 1` ⇒ **偶数索引不移,奇数索引左移 1**。**
**⇒ 这是 IW 的经典 `Netchan_Encrypt` 变体。**

### ★★★ 三个调用点的 seed

| 调用 | seed |
|---|---|
| **`Netchan_Process`**（解密） | **`challenge ^ parsed.serverId ^ parsed.messageAcknowledge`** |
| **`Netchan_Transmit`**（加密） | **`challenge ^ sequence`** |

★★★ **⇒ 两侧 seed 不同 ⇒ 这是一个**双向独立密钥**（与报告 098 的 `userCmdKey` 三层异或呼应）。**

---

## 八、★★★★★ **可靠命令环的"跳号不可修复"**

### 8.1 ★★★★★ 完整注释（第 959–966 行，逐字）

```cpp
// CODREF(1649370 reliable command ring): once a client command
// cursor exists, every new record must be the next sequence.  A
// jump cannot be repaired by accepting the later text: the next
// usercmd key is derived from the reliable ring entry, so doing so
// turns all following packets into plausible-looking XOR noise.
// The first observed record may start above one because connection
// setup can precede this source-side slot, as in the captured
// sequence-7 fixture.
```

★★★★★ **⇒ 三条精确事实：**
```
① ★★★ **每个新记录必须是下一个序号**（不能跳号）
② ★★★ **跳号不可修复**："A jump **cannot be repaired by accepting the later text**:
   the next usercmd key is **derived from the reliable ring entry**,
   so doing so turns **all following packets into plausible-looking XOR noise**"
        ↓
★★★ ⇒ **因为 `userCmdKey` 依赖可靠命令的哈希**
   ⇒ 接受错误文本 ⇒ 后续所有包的 `userCmdKey` 都错
   ⇒ 解出来是"**看起来合理的 XOR 噪声**"（最危险的情况）
        ↓
③ ★★ **第一个记录可以 > 1**（连接建立可能早于该槽位）
   ⇒ 例：捕获到的 **`sequence-7 fixture`**
```

### ★★★★★ 与报告 098 的 `changed=0 full=0 bitsAtTrailer=0` 呼应

```
报告 098：`userCmdKey` 错 ⇒ "a capture decoded under one key is **noise under another**"
本报告：可靠命令跳号 ⇒ 后续所有包变"**plausible-looking XOR noise**"
        ↓
★★★★★ ⇒ **同一个失败模式的两个入口**：
  ① 密钥来源（`checksumFeed` / `messageAcknowledge` / 可靠命令哈希）任一错
  ② 可靠命令环跳号（导致哈希错）
        ↓
★★★ ⇒ **都表现为"看起来合理的噪声"** ⇒ 极难诊断
```

★ **⇒ 所以本文件设计了 `UserCmdTrace` + `userCmdKey` 回传（报告 098 已记录）来对抗这一点。**

### ★★★ 包的完整性校验（第 861–903 行）

```cpp
if (effectivePacket.size() < ClientHeaderSize + 1)  return Rejected("payload is shorter than its header");
// ClientHeaderSize = 13
parsed = {
    .sequence            = readU32(effectivePacket, 0),   // 偏移 0
    .serverId            = effectivePacket[4],            // 偏移 4
    .messageAcknowledge  = readU32(effectivePacket, 5),   // 偏移 5
    .reliableAcknowledge = readU32(effectivePacket, 9),   // 偏移 9
    .encodedCommands     = effectivePacket.subspan(13),   // 偏移 13
};
if (!parsed.sequence || parsed.sequence > NetchanSequenceMask)  return Rejected(...);
if (parsed.messageAcknowledge > NetchanSequenceMask)             return Rejected(...);
if (chan.incomingSequenceReceived && parsed.sequence <= chan.incomingSequence) return Duplicate(...);
```

### ★★★★★ **客户端包头 = 13 字节**的精确布局

| 偏移 | 大小 | 字段 |
|---|---|---|
| **0** | 4 | `sequence` |
| **4** | 1 | `serverId` |
| **5** | 4 | `messageAcknowledge` |
| **9** | 4 | `reliableAcknowledge` |
| **13** | … | `encodedCommands` |

★★★ **⇒ 4 + 1 + 4 + 4 = **13** ✓（`ClientHeaderSize = 13`）**

### ★★★ 两处"两种拒绝共用一个消息"的修复（第 670–673 行，逐字）

```cpp
// Two very different refusals wore one message, which cost a cycle: the dispatcher in
// sv_main_mp.cpp already routes out-of-band packets to SV_ConnectionlessPacket before
// this, so reaching here with an OOB packet would be a ROUTING bug, while a short packet
// is just a short packet. Name which, and how big.
```

★★★★★ **⇒ 又一次"**诊断信息不足花掉一整轮**"的教训：**
```
① `packet.size() < 5`         ⇒ "netchan packet too short: N bytes, minimum 5"
② `NET_IsConnectionlessPacket` ⇒ "out-of-band packet reached the netchan path
                                   (N bytes) -- the dispatcher should have sent this
                                   to SV_ConnectionlessPacket"
        ↓
★★★ ⇒ 两种情况**语义完全不同**（短包 vs 路由 bug）,但曾共用一个消息
```

---

## 九、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ 魔数 | `OobPrefix = { 0xFF, 0xFF, 0xFF, 0xFF }` / ★ **`ClientHeaderSize = 13`** |
| 2 | ★★★★★ **武器索引 10→11 位** | 武器块 **900 → 1700 项** ⇒ 索引 **10 → 11 位**；`sv_gamestate_mp.cpp` 已推导 |
| 3 | ★★★★★ **bug 的症状** | 空闲时完美（**delta 未变不花位**）⇒ **hundreds of clean commands**；一持枪则**三个字段各少读 1 位** ⇒ 错 3 位 ⇒ **报错永远在 trailer** |
| 4 | ★★★★ trace 证据 | `buttons` 解到 **`0x146574C3`**,门控**随机打开** |
| 5 | ★★ 三个受影响的字段 | `weapon` / `lastWeaponAltModeSwitch` / `offHandIndex` |
| 6 | ★★★★ **三个 trailer 哨兵** | `changed=0` ⇒ **7**；`full=0` ⇒ **2**；`full=1` ⇒ **5** |
| 7 | ★★★★★ **三个门控掩码** | **`0x20000`**（bit 17,Location）/ **`0x200000`**（bit 21,Direction）/ **`0x4`**（bit 2,Conditional） |
| 8 | ★★★★★ **conditional 块 = 35 数据位** | `conditionalAngle` 16 + `conditionalByte` 8 + `conditionalElevenBits` 11 = **35** |
| 9 | ★★★★ **两个定点常量** | **`182.0444488525391f`**（≈ 65536/360）与 **`0.0054931640625f`**（= 360/65536）⇒ **互为倒数** |
| 10 | ★★★★★ **`UserCmdTrace` 的洞察** | "a rejection reason names the **last check to fail**, **never the field that consumed the wrong number of bits**" ⇒ **报错点 ≠ 出错点** |
| 11 | ★★★ trace 打印格式 | `[buttons=0x… deltaTime=N changed=N full=N gates=LDC bitsAtTrailer=N]` |
| 12 | ★★★★★ **`CL_WritePacket = 0x005B2C10`** / **`MSG_SetDefaultUserCmd = 0x0066F170`** | baseline **每包从 default 开始**,**从不跨包继承** |
| 13 | ★★★★★ **Wetwork 炮台序章的致命故障** | 旧实现跨包保留 `buttons 0x4` ⇒ 进入 **35 位 conditional 块** ⇒ 客户端没写 ⇒ **每个出生后的包都在 trailer 失败 ⇒ 鼠标输入从未到达 pmove** |
| 14 | ★★★ "重复命令仍接受" | 若拒包 ⇒ **客户端永远重传同一窗口** ⇒ 由服务端水印丢弃 |
| 15 | ★★★★★ **三个分片标志位** | **`0x80000000`** fragmented / **`0x40000000`** reliable / **`0x20000000`** fragment-ack |
| 16 | ★★★★★ **10 字节分片头** | `sequence(4,低29位+3标志) + index(1) + last(1) + stride(2,=1154) + length(2)` |
| 17 | ★★★★ 与 memory 对照 | memory 的「10 字节头 index/last/stride(1154)/length」**逐字段吻合**,且明确了 **sequence 占前 4 字节** |
| 18 | ★★ 布局声明 | "**it is not the older `qport/start/length` layout**" |
| 19 | ★★★ **七重分片校验** | 含 ★★ **非最后一片时 `length` 必须恰为 `stride`** |
| 20 | ★★★ 确认包标志 | **`0xA0000000`**（bit31 + bit29,**不含 bit30**）+ 尾部 **4 × `0xFFFFFFFF`** |
| 21 | ★★★★★ **选择性重传** | **`Netchan_TransmitNextFragment = 0x6743D0`**；bit30 声明模式 ⇒ 对端回 bit29 + **128 位位图**；`outgoingSequence` **只在全部确认后前进** |
| 22 | ★★★★ **旧实现的故障** | 只发 bit31（fire-and-forget）⇒ **丢一个分片就整条消息作废** |
| 23 | ★★★ 分片调度 | **"最低发送次数水位"**公平调度（`fragmentSendCount ≤ lowest` 且未确认 ⇒ 选；否则抬水位） |
| 24 | ★★★ `OLMOD(netchan-owned-buffer)` | 原生推进**缓冲区指针**；本实现**保留完整不可变消息 + 从发送次数推导进度** ⇒ 选择性重传才可能 |
| 25 | ★★★★★ **`Com_HashKey` 算法** | `hash += (int8)ch * (119 + index)`,最多 **32** 字符,遇 NUL 停；收尾 `u ^ ((u ^ (u>>10)) >> 10)` |
| 26 | ★★ 有符号字符 | 按 **`int8_t`** 解释 ⇒ ≥0x80 是**负数** |
| 27 | ★★★★★ **`Netchan_XorCommands`** | `key` 初值 = `seed & 0xFF`；每字节 `key ^= commandByte << (index & 1)`（**交替左移 0/1**）；输出 `payload ^ key` |
| 28 | ★★★ 两个 seed | 解密：**`challenge ^ serverId ^ messageAcknowledge`**；加密：**`challenge ^ sequence`** |
| 29 | ★★★★★ **可靠命令环** | 必须**连续**；★★★ **跳号不可修复**（"turns all following packets into **plausible-looking XOR noise**"） |
| 30 | ★★ 首记录可 > 1 | 例 **`sequence-7 fixture`** |
| 31 | ★★★★★ **13 字节客户端包头** | `sequence(4) + serverId(1) + messageAcknowledge(4) + reliableAcknowledge(4)` = **13** ✓ |
| 32 | ★★★ 两种拒绝分离 | 短包 vs OOB 路由 bug ⇒ **各自独立的消息**（"cost a cycle"） |

---

## 十、结论

### 1. ★★★★★ **武器索引 10→11 位是一个已修复的完整 bug,且有教科书级的症状描述**

```
**武器块 900 → 1700 项 ⇒ 索引 10 → 11 位**
        ↓
★★★ 而解码器是 **3.3.3.3 的逐字复制,仍在读 10 位**
        ↓
★★★★★ **空闲时完美**（delta 未变不花位）⇒ **一持枪就崩**
   ⇒ **三个字段各少读 1 位** ⇒ 错 3 位
   ⇒ **报错永远在 trailer**（"merely where the damage becomes visible"）
```

### 2. ★★★★★ **`UserCmdTrace` 的设计源于一条根本性洞察**

★ **⇒ "a rejection reason names the **last check to fail**, **never the field that consumed the wrong number of bits**"。**

### 3. ★★★★★ **Wetwork 炮台的致命故障：baseline 跨包继承**

```
旧实现跨包保留 `buttons 0x4` ⇒ 进入 35 位 conditional 块
        ↓
但客户端是对**零值 default** 编码的,没写这个块
        ↓
★★★ **每个出生后的包都在 trailer 失败 ⇒ 鼠标输入从未到达 pmove**
        ↓
修复：**每包都从 `defaultUserCmd` 开始**
```

### 4. ★★★★★ **分片传输：10 字节头 + 三个标志位 + 选择性重传**

```
**`0x80000000`** 分片 / **`0x40000000`** 可靠 / **`0x20000000`** 确认
        ↓
★★★ 选择性重传：bit30 声明 ⇒ 对端回 **128 位位图** ⇒ **全部确认后**才前进
   （旧实现 fire-and-forget ⇒ 丢一片就整条作废）
```

### 5. ★★★★★ **可靠命令环跳号会把后续包变成"看起来合理的噪声"**

★ **⇒ 因为 `userCmdKey` 依赖可靠命令哈希 ⇒ 这是与报告 098 的 `changed=0 full=0` **同一失败模式**。**

### 6. ★★★★ **`Com_HashKey` 与 `Netchan_XorCommands` 的算法被完整还原**

### 7. ★★★ **13 字节客户端包头与 10 字节分片头两个精确布局**

---

## 十一、下一步

- `qcommon\net_dtls_cod.cpp`（34,426 B / **765 行**）+ `.hpp`（7,620 B / 182 行）
- `qcommon\msg_mp.cpp` / `.hpp` / `com_math.hpp` / `net_types.hpp`
