# 159 · 分片重组与 XOR 键、profile 按名读取、断开见证

## 一、范围

本报告学习 **4 处**：

- `qcommon/net_chan_mp.cpp` 550–869 行（包尾、XOR、HashKey、分片重组）
- `PlayerDataDef.hpp`（195 行，完整）
- `DisconnectWitness.hpp`（18 行，完整）

## 二、命令流收尾与"重复旧命令不能整包拒绝"

```cpp
result.userCommands.push_back(command);
baseline = command;      // 包内逐条推进基线
```

读完 N 条后读 5 个 long 的 `predictedState.values`，再读 3 位并必须等于 `ClientCommandEof (3)`。

注释解释了为什么旧命令不拒绝：

> COD 的 `SV_UserMove` 在客户端于它的移动窗口内重复一条旧命令时**仍然接受这个包**。服务端的命令水位线（watermark）在 netchan 状态与 ACK 推进之后才丢弃它。**拒绝整个包会让客户端永远重传同一个窗口。**

这是"幂等收下 + 后续丢弃"与"整包拒绝"的分野：前者可恢复，后者死锁。

## 三、失败信息里为什么要带 trace

```cpp
result.reason += " [buttons=0x" + hex(trace.buttons) +
    " deltaTime=" + ... + " changed=" + ... + " full=" + ... +
    " gates=" + (L?-:'-') + (D?'D':'-') + (C?'C':'-') +
    " bitsAtTrailer=" + ... + "]";
```

注释：

> 说清楚解码器**在失败之前相信了什么**。原因点名的是最后一个检查；**故障在它的上游**，在某个吃错位数的东西里。**真正重要的是那些门**：三个条件块挂在 buttons 的 `0x20000`、`0x200000`、`0x4` 上，而每一个都只在**玩家出生并按东西**之后才触发——**正是这个解码器在几百条干净命令之后开始失败的那一刻。**

## 四、连接无关包的两种拒绝必须分开

```cpp
if (packet.size() < 5)  → "netchan packet too short: N bytes, minimum 5"
if (NET_IsConnectionlessPacket(packet)) → "out-of-band packet reached the netchan path (...)"
```

注释：

> **两种很不同的拒绝此前戴着同一条消息，代价是一轮排查**：`sv_main_mp.cpp` 的分派器已经把 OOB 包路由到 `SV_ConnectionlessPacket`，所以**带着 OOB 包到达这里是路由 bug**，而短包只是短包。**说清楚是哪一个，以及多大。**

## 五、分片：CODOL 是 10 字节头，不是老式 qport/start/length

### 5.1 序列标志

```text
0x80000000  分片
0x40000000  reliable
0x20000000  分片确认
```

头结构：

```text
+0..3  rawSequence
+4     fragmentIndex
+5     lastFragmentIndex
+6..7  fragmentStride (u16, 必须 == 1154)
+8..9  fragmentLength (u16)
+10..  载荷
```

### 5.2 确认包（0x20000000）

要求：`size >= 26`、**不能同时是 reliable**、stride 必须 1154、`sequence == chan.outgoingSequence`。

读 4 个字（16 字节）**OR 进** `chan.fragmentAcknowledgements`，返回 `FragmentAcknowledgement`。

### 5.3 片段包的边界检查（一次九项）

```text
sequence != 0
fragmentIndex <= lastFragmentIndex
lastFragmentIndex < 128
fragmentStride == 1154
fragmentLength <= fragmentStride
packet.size() >= 10 + fragmentLength
（非末片时）fragmentLength == fragmentStride
```

即：**除了最后一片，每一片都必须满长**。这条让"中间缺一截"不可能被误当成完整消息。

### 5.4 重复/乱序的处理

```cpp
if (incomingSequenceReceived && sequence <= chan.incomingSequence) {
    // 若 reliable 且 sequence == incomingSequence，回一个 0xA0000000 | sequence
    // 的控制回复，四字位图全 1（告诉对端"我全收到了"）
    return controlReply.empty() ? Duplicate : FragmentPending;
}
```

注意回复用的是 `0xA0000000`（分片 + 确认），而位图填 `0xFFFFFFFF` —— 这是"我已全收"的语义，不是"我收到了哪些"。

### 5.5 位图与重组

```cpp
fragmentMask = 1u << (index & 31);
word = receivedFragmentBits[index >> 5];
if ((word & mask) == 0) {
    写入 fragmentBuffer + index*stride, length 字节
    word |= mask;
    fragmentLength += length;
}
```

`fragmentLength` 是**累计写入量**，不是"已收到的片数 × stride"——因为最后一片可能不满。

完整性检查遍历 `0..lastFragmentIndex` 每一位。

完成后：

```text
reassembled = u32(sequence) + fragmentBuffer[0..fragmentLength)
```

**在重组流前面补回 4 字节序列号**，让后续解析路径与未分片的包走同一段代码。

### 5.6 大小上限

```text
fragmentBuffer.size() > NetchanMaximumFragmentedMessage (0x20000)
```
即 **128 KiB**。`buffer.assign((lastIndex+1)*stride)` —— 128 × 1154 = 147,712 > 0x20000(131,072)，所以上限确实会先触发。

## 六、`Netchan_XorCommands`：一个滚动键

```cpp
key = (uint8)seed;
for each byte:
    commandByte = reliableCommand[commandIndex++]   // 循环，遇 NUL 归零
    key ^= (uint8)(commandByte << (index & 1));
    result[i] = payload[i] ^ key;
```

要点：

- 键**逐字节演化**，不是固定 seed；
- 可靠命令字符串按索引循环取用；
- `<< (index & 1)` **隔字节左移一位**——奇偶索引不同权重；
- 遇到 NUL 字节把索引归零（字符串重新从头取）。

这是对称操作：同一函数既加密也解密。

## 七、`Com_HashKey`

```cpp
hash += (int8)value[i] * (119 + i);
unsignedHash = (uint32)hash;
return unsignedHash ^ ((unsignedHash ^ (unsignedHash >> 10)) >> 10);
```

参数：`(119 + i)`，**字符按有符号 int8 解释**（高位字符为负）。默认 `maxLength = 32`。

最后一步是经典的"折叠高位"：`h ^ ((h ^ (h>>10)) >> 10)`。

## 八、`PlayerDataDef`：按名字读 profile schema

### 8.1 为什么不再用手测 ordinal

> `EngineBindings` 为这个 schema 带了**八个手测 ordinal**——`characterClasses` 在 605、步长 14、`weaponClasses` 在 1607 步长 37、`slots` 在子 ordinal 5、`primaryBase` 22、`secondaryBase` 29——**每一个都是 per-build 常量**。八个里有六个在 3.3.3.3 上不同（576/10/1 与 1154/36），所以同样的代码读同样的名字在那边会读到垃圾。
>
> **附件那组更糟：它们不是测出来的，而是推导成 `weaponOrdinal - AttachmentCount`**，源码注释自己称之为 numerology，而且已经落错过一次武器（§187g/187m）。**def 把它们命名出来**——`primaryAttach` 在 16、`secondaryAttach` 在 23、宽 6——**问它既更短又按构造正确**。

### 8.2 内存形态 = 磁盘形态 + 指针修复

> 一个 zone 作为连续镜像加载，加载器把每个 `0xFFFFFFFF`"数据紧随其后"占位符替换成该内联数据的地址。**这是实测的不是假设的**：def 的 `+0x38` 头字在提取出来的文件里是 `0xFFFFFFFF`，运行时是偏移表**指针**。这也正是让测试能走一个提取出来的 def 的原因：**把占位符链接起来，生产代码就在两个不同 build 的真实 schema 上原样运行。**

### 8.3 布局（全部公开，因为测试夹具链接器需要同样偏移）

```text
HeaderBytes = 0x3C
+00 Version        +04 FormatChecksum  +08 EnumCount      +0C Enums
+10 StructCount    +14 Structs         +18 IndexedArrayCount +1C IndexedArrays
+20 EnumedArrayCount +24 EnumedArrays  +28 RootCategory   +2C RootType
+30 DocumentSize   +34 OffsetTableCount +38 OffsetTable

StructRecord      20 字节：{propertyCount, properties*, sizeBytes, bitOffset, indexCount}
PropertyRecord    24 字节：{name*, category, typeIndex, offsetIndex, 0, 0}
IndexedArrayRecord 16 字节：{arraySize, elementCategory, elementTypeIndex, elementSizeBytes}
EnumedArrayRecord 16 字节 / EnumRecord 12 字节
```

### 8.4 Category 六种

```text
0 Int   1 Byte   2 Bool（存的是 BIT 偏移，不是字节偏移）
3 String（typeIndex 是最大长度）   5 Struct   6 IndexedArray
```

`Bool` 那条注释很关键：**同一个 `byteOffset` 表对 bool 返回的是位偏移**，所以调用方读 bool 时的算法与读 int 不同。

### 8.5 引擎自己的走法

```cpp
byteOffset = *(_DWORD *)(*(_DWORD *)(def + 0x38) + 4 * index)
```

即 `offsetTable[index]`。`PlayerDataDef::byteOffset(index)` 就是这一步。

### 8.6 路径解析

支持 `"characterClasses"`、`"characterClasses[3].slots"`、`"weaponClasses[7].primaryBase"`。

> **一个没有下标的尾部数组解析到它的元素 0，并报告数组长度与步长**——这就是调用方**在没被告知的情况下**得知 `slots` 是九个宽、`weaponClasses` 是六十长的办法。

### 8.7 安全

```cpp
static constexpr std::size_t MaxNameLength = 128;
using Readable = std::function<bool(const void*, std::size_t)>;
```

注释：

> 长于 128 的属性名不是名字，是**一个落进可读内存的野指针**。给字符串比较加上界，坏 def 就走不出一个页。
>
> **这里不解引用任何没被批准过的地址。** 插件里那是 `EngineBindings` 的 `VirtualQuery` 探针；测试里那是对夹具缓冲区的边界检查。

`elementSpan(category, typeIndex, depth)` 有深度限制——"数组的数组之数组不能嵌套得比 def 拥有的类型更深"。

## 九、断开见证

```cpp
enum DisconnectWitnessResult {
    NotRequested, Installed, AlreadyInstalled, UnexpectedBytes, UnsupportedHost
};
```

注释：

> 在**客户端进程**里点名谁调了 `CL_Disconnect`。见 .cpp 说明为什么用钩子而不是更多静态读取。**除非 `OLMOD_DISCONNECT_WITNESS=1`，否则关闭。**

`UnexpectedBytes` 是钩子的标准防线：**目标处的字节与预期不符就拒绝安装**，而不是硬跳过去把进程打崩。

## 十、关键结论

1. **重复旧命令必须收下再丢**，整包拒绝会让客户端重传同一窗口直到死锁。
2. **分片的非末片必须满长**（`fragmentLength == fragmentStride`），这条让"中间缺一截"不可能被误当完整。
3. **重组后要补回 4 字节序列号**，让分片与未分片走同一段解析。
4. **两种不同的拒绝不能共用一条消息**——OOB 到达 netchan 是路由 bug，短包不是。
5. **per-build ordinal 是定时炸弹**：八个手测值里六个在另一 build 不同，而附件那组是纯 numerology 且已落错过。**按名字读 schema 是按构造正确。**
6. **Bool 在 profile 里是位偏移不是字节偏移**，同一个偏移表两种语义。

## 十一、未闭合点

- `Netchan_Process` 869 行之后（客户端包解析、服务端命令生成）未在本组。
- `PlayerDataDef::resolve` 的完整实现不在本组。
- `installDisconnectWitness` 的实现不在本组。
