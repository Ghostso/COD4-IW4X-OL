# 157 · qcommon 层：角、消息、网络类型、netchan、DTLS

## 一、范围

本报告完整学习 **5 个文件**：

- `qcommon/com_math.hpp`（27 行，完整）
- `qcommon/msg_mp.hpp` + `msg_mp.cpp`（46 + 31 行，完整）
- `qcommon/net_types.hpp`（15 行，完整）
- `qcommon/net_chan_mp.hpp`（182 行，完整）
- `qcommon/net_dtls_cod.hpp`（212 行，完整）

`server_mp` 145 个文件已全部完成，本组开始进入 `qcommon` 层。

## 二、角度：两个互逆比例

```text
ShortAngleScale = 360.0f / 65536.0f     // short → 度
AngleShortScale = 65536.0f / 360.0f     // 度 → short
```

```cpp
BG_ShortToAngle(u16)  = value * ShortAngleScale
BG_AngleToShort(float) = (u16)(int32_t)(value * AngleShortScale)
BG_NormalizeAngle360(float)
```

注意 `BG_AngleToShort` 的是**先截断成 int32 再转 u16**——负数取整后转无符号是定义良好的模运算，所以 -1.0° 会落到 65535 附近，正是短角表示的期望行为。

`BG_NormalizeAngle360` 用 `fmod` 后补 360，把负值折回正值。

## 三、`msg_t`：x86 布局被逐字段断言

```text
overflowed / readOnly / data* / splitData* / maxsize / cursize
splitSize / readcount / bit / lastEntityRef / flush / targetLocalNetID
```

断言（全部带 `sizeof(void*) != 4 ||` 前缀，即**只在 32 位下检查**）：

```text
sizeof(msg_t)          == 0x30
offsetof(data)         == 0x08
offsetof(cursize)      == 0x14
offsetof(readcount)    == 0x1C
offsetof(bit)          == 0x20
```

这个 `sizeof(void*) != 4 ||` 前缀让同一份头文件在 64 位主机上也能编译（此时结构会变宽，断言自动跳过）——**这是把 ABI 检查与可移植编译兼得的标准写法**。

`MsgWriter` 是纯虚基类，四个纯虚：`MSG_WriteData` / `MSG_WriteBits` / `MSG_WriteString` / `overflowed`。三个非虚便捷方法都**小端**：

```cpp
MSG_WriteByte  → 1 字节
MSG_WriteShort → 低字节、高字节
MSG_WriteLong  → 低、次低、次高、高
```

这是 CoD 系列线格式的基础约定，所有多字节字段都是显式小端而不是 memcpy，避免主机字节序问题。

## 四、`PeerAddress` 只有两个字段

```cpp
struct PeerAddress { std::uint32_t ipv4; std::uint16_t port; };
```

注释明确：

> 插件使用的传输身份。**这不是 CODOL 内存里的 `netadr_t` 布局。**

这与之前报告的"peer key = `(ipv4<<16)|port`"一致——一个 64 位键。

## 五、netchan：本 build 的 EOF 是 5，不是 6

### 5.1 常量

```text
NetchanSequenceMask               = 0x1FFFFFFF
NetchanFragmentSize               = 1154
NetchanMaximumFragments           = 128
NetchanMaximumFragmentedMessage   = 0x20000
ClientCommandReliable = 2  ClientCommandEof = 3
ServerCommandReliable = 1  ServerCommandReliableBinary = 2
ServerCommandEof = 5
```

### 5.2 EOF 的取证

> 3.3.3.3 用 6 结束服务端消息；**OLfinal 用 5**，而这个常量此前被原样搬了过来。**在两组独立语料上实测**，记录在 `re/demo-re/01-container.md` §4 与 `06-olevents.md` §2：
>
> - 它是 **54,682/54,682** 个 demo 快照载荷的最后一个字节；
> - 它是 gamestate 的 configstring 块结束 token；
> - 它是 gamestate 的 clientNum/checksumFeed 对之后的那个字节；
>
> ——3.3.3.3 写 6 的**每一个**位置都是它。
>
> **OLfinal 根本没有 opcode 6**，所以用 6 结束的消息不只是读错——它**掉进解析循环的错误出口**。

这是本项目最重要的一条：opcode 表其余部分（0 snapshot、1 serverCommand、2 binary serverCommand、3 gamestate、4 configstring 块开始）都不变，只有结束符从 6 变成 5。

### 5.3 `UserCmd`

```text
commandTime / buttons / angles[3] (u16) / weapon / offHandIndex
lastWeaponAltModeSwitch (u16)      ← 名字是遗留的
forwardMove / rightMove (i8)
conditionalAngle (f32) / conditionalByte / conditionalElevenBits
selectedLocation[3] / selectedDirection[2]
```

`lastWeaponAltModeSwitch` 的注释纠正了语义：

> `0x5B2241` 把 `cg.equippedOffHand` 经 `clientActive+0x3C64` 写进原生 `usercmd+0x18`：**这个成员就是已装备的副手**。前面 `+0x16` 的成员来自 `cg+0xC7238` 的每武器查表，不是 `cg.equippedOffHand`。

即字段名"最后一个切换的替代模式"是错的，实际是"已装备副手"。

### 5.4 netchan 状态：发与收是两套

**发送侧**：

```text
unsentFragments / reliableFragments / unsentLength / unsentBuffer
fragmentSendCount[128] / fragmentAcknowledgements[4] / lowestFragmentSendCount
```

注释：`0x005A5490 / 0x005A55F0 / 0x005A5720` 把一条待发消息保持在稳定序列下，**发送带索引的 1154 字节分片直到完成**。

**接收侧**：

```text
fragmentSequence / fragmentLength / fragmentStride / lastFragmentIndex
receivedFragmentBits[4] / fragmentBuffer
```

注释：`Netchan_Process 0x005A5960` 拥有**独立的接收序列、聚合长度和四字位图**。

两侧各有自己的 sequence，不共用。

### 5.5 `userCmdKey`：为什么必须暴露

```cpp
std::uint32_t userCmdKey{};
```

注释：

> §88：**userCmd 差分是用哪个 key 读出来的**，这样一份捕获流可以被**重放**。usercmd 里的每一个 `changed` 位都是键控的，所以**用一个 key 解码的捕获在另一个 key 下就是噪声**——这正是第一次把真实捕获变成黄金向量时产出 `changed=0 full=0 bitsAtTrailer=0` 而不是目标字段的原因。
>
> 它是 `checksumFeed ^ messageAcknowledge ^ Com_HashKey(serverReliableCommand)`，而这三个都**无法从解码后的字节恢复**。

这是"诊断信息必须记录不可反推的中间量"的典型例子。

### 5.6 `NetchanProcessKind` 五态

```text
Accepted / FragmentPending / FragmentAcknowledgement / Duplicate / Rejected
```

`FragmentPending` 与 `FragmentAcknowledgement` 分开，说明**收到一片**与**收到对分片的确认**是两种不同结果。

`Com_HashKey(value, maxLength = 32)` 的默认 32 字节上限与 `clientCommands[reliableAck & mask]` 的 1023 字符上限是不同的量级——前者是包 XOR 用的小 key，后者是存储上限。

## 六、DTLS：67 而不是 37

### 6.1 `DtlsCookieEchoPacket` 的那条更正

```cpp
std::array<std::uint8_t, 67> commonAddress{};
```

注释：

> **67，不是 37。** 线上的一个 `bdCommonAddr` 是 **67 字节**；这里的 37 是短形式，它让后面的每个字段提前 30 字节，整个包短 30 字节。C# GameServer 撞上过完全一样的问题并以同样的方式修正——在旧偏移上，security id 从 `00FF00FF0000` 哨兵串里读出来，ECC 解析从哨兵中间开始，报 `"expected DER SEQUENCE"`。

这是一个"偏移错 30 字节但错误信息指向别处"的典型：症状是 DER 解析失败，根因是包结构短了 30 字节。

### 6.2 数据包

```text
PacketType = 0x06
Version    = 0x02
HeaderSize = 16
```

字段：`verificationTag(u16) / sequenceNumber(u16) / authenticator[8] / encryptedSize(u16) / payload`。

`authenticatedBytes()` 是私有的——**认证覆盖哪些字节由实现决定，不暴露**。

### 6.3 密钥派生

```text
DtlsSessionKeys::derive(sharedMaterial) → digest[20]
aesKey()  = 前 16 字节
hmacKey() = 24 字节
iv(seq, tag) = 16 字节，依赖序列号与验证标签
```

IV 由 `(sequenceNumber, verificationTag)` 决定 ⇒ 每个包的 IV 唯一，无需随机数。

### 6.4 每会话独立密钥的理由

`DtlsPeerSystem::PeerSession` 里有：

```cpp
securityKey        // INIT 时选定的
previousSecurityKey
hasPreviousSecurityKey
keyPair / keys / previousKeys / usingPreviousKeys
lastClientSequence / nextServerSequence / clientSequenceReceived
```

注释：

> Demonware 描述符可能在多个对端完成 DTLS 时被刷新。**在 INIT 时按对端选定密钥并保留**；在 COOKIE_ECHO 时使用可变的全局描述符会让两个客户端**竞态到不同的密钥材料**上。

`previousKeys` / `usingPreviousKeys` 的存在说明支持密钥轮转的过渡期：旧包仍可解密。

### 6.5 会话表

```text
默认 maxPeers = 18（与客户端槽数一致）
sessionLifetimeMilliseconds = 120'000
```

`expireSessions(now)` + `findSession(peer)` + `allocateSession(peer)`。

`rememberSecurityKey(key)` 同时保留 `lastSecurityKey_` 与 `previousSecurityKey_`——与 per-peer 的两层是同一个模式。

## 七、关键结论

1. **`ServerCommandEof = 5` 是本项目最关键的单字节**：OLfinal 没有 opcode 6，用 6 结束会让消息掉进解析错误出口，而这个常量曾被原样从 3.3.3.3 带过来。
2. **32 位 ABI 断言用 `sizeof(void*)!=4 ||` 前缀**是可移植的正确写法。
3. **所有多字节字段显式小端**，不用 memcpy——与主机字节序解耦。
4. **分片有三套序列**：发送序列、接收序列、消息序列各自独立。
5. **不可反推的键必须记下来**（`userCmdKey`），否则捕获无法重放。
6. **67 vs 37 的教训**：偏移错 30 字节，错误信息指向 DER 解析，而不是指向包结构。

## 八、未闭合点

- `NetchanMaximumFragmentedMessage = 0x20000` 与 `MaxPacketSize = 65,507` 的关系（分片在应用层做，UDP 层不做）。
- DTLS 的握手完整性（证书链、签名验证）不在本头文件范围内。
