# 05 — 最小服务器架构与模块边界

> 目标：先证明协议和状态机正确，再追求大厅/战斗画面。MVP 不包含完整武器、PvE、赛事、商店、持久化和反作弊子系统。

## 1. 总体架构

```text
[2697 服务端 EXE / 既有抓包 / 旧源码]  ->  协议规格与黄金向量
                  |
                  v
+---------------------------------------------------+
| 独立 MVP Server                                    |
|                                                   |
|  A. Transport / Record Layer                       |
|     UDP socket, netchan, fragment, replay window  |
|                                                   |
|  B. Handshake / Session State Machine              |
|     challenge, connect, cookie, key exchange,      |
|     reliable command, disconnect                   |
|                                                   |
|  C. Internal Message Codec                         |
|     0x01/0x02 reliable, 0x03 gamestate,            |
|     0x04 configstring, 0x00 snapshot, 0x05/0x06    |
|                                                   |
|  D. World State / Resource Adapter                 |
|     players, entities, spawn, map/config data       |
|                                                   |
|  E. Observability & Test Harness                   |
|     hex vectors, assertions, packet traces          |
+---------------------------------------------------+
                  |
                  v
          2.6.9.7 Client (later, separately approved)
```

## 2. 模块边界

### A. Transport / Record Layer
职责：
- UDP recv/send；
- 连接记录 framing、序列号、重放窗口、分片/重组；
- 只输出“完整字节消息”，不解释内部 opcode。

优先复用：
- C# `Net/UdpTransport.cs`；
- B1 `netchan.c` 的 `Netchan_Process/Transmit`；
- B2 `qcommon/net_chan_mp.cpp` 的接口布局参考。

必须适配：
- 2697 的记录头、密钥/计数器、外层 tag；
- 旧 A/B 冲突（AES192/Tiger192 vs AES128/SHA1、COOKIE_ECHO 长度）。

接口：
```text
Send(datagram) / Poll() -> PacketBytes
DecodeRecord(PacketBytes, session) -> PlainBytes | RejectReason
EncodeRecord(PlainBytes, session) -> PacketBytes
```

### B. Handshake / Session State Machine
职责：
- getchallenge / connectResponse；
- cookie/key exchange；
- 会话 ECDH/共享密钥；
- connect/join/primed/disconnect；
- 超时、重传、状态回滚。

优先复用：
- B3 `CodolProtocol`、`BigInt.cs`、`P224.cs`、`Aes128.cs`、`Sha1.cs`；
- B1 `codol_handshake.c`、`codol_connect.c`、`codol_association.c`；
- B2 的 backend/session 层作为接口参考。

MVP 状态机：
```text
NEW -> CHALLENGE -> CONNECTED -> KEYED -> PRIMED -> ACTIVE -> DISCONNECTED
```

### C. Internal Message Codec
职责：
- 可靠命令 `0x01/0x02`；
- gamestate `0x03`；
- configstring `0x04`；
- snapshot `0x00`；
- `0x05/0x06` 终止/阶段标记。

2697 已确认服务端事实：
- `0x02 | long | short(length) | data`；
- `0x01 | long | string`；
- gamestate/configstrings 新路径 `0x03/0x04 + ... + 0x06`；
- snapshot 内层/外层有不同的 `0x06` 位置。

MVP 首先实现**可断言编码器/解码器**：
```text
EncodeReliable(cmd) -> bytes
DecodeReliable(bytes) -> cmd
EncodeGamestate(snapshotDescriptor) -> bytes
EncodeConfigstrings(indexMap) -> bytes
EncodeSnapshot(worldFrame) -> bytes
```

### D. World State / Resource Adapter
职责：
- 玩家/客户端/实体最小集合；
- spawn、原点和基础 movement state；
- configstring 索引来源；
- 2697 runtime-assets/scripts 的最小加载接口；
- 只提供首个 gamestate、首个 snapshot 所需字段。

暂不实现：
- 完整 pmove、武器伤害/弹道/命中；
- killstreak、载具、PvE、zombie、结算、商店、持久化。

### E. Observability & Test Harness
职责：
- 记录每条消息的 hex、长度、字段、CRC/HMAC；
- 对 2697 服务端/旧源码/C# 三方做字段对照；
- 生成金样；
- 失败时回滚状态，不伪装成功。

## 3. 数据流

```text
UDP -> Record decode -> complete plaintext
    -> opcode dispatch
    -> ReliableCommand / Gamestate / Configstring / Snapshot
    -> world/resource adapter
    -> encode response
    -> record layer -> UDP
```

内部 opcode 与外层 record 类型必须分开：
- Outer：记录层 framing、cookie/tag、sequence；
- Inner：server message opcode；
- End marker：可能是 message EOF、子段/阶段结束，不能混用。

## 4. 推荐实现栈

短期：
- **C# v0.1** 作为可构建骨架（csc 已存在）。
- 读取 B1/B2 作为参考，但不直接复制旧版本协议常量。

中期：
- 若要长期维护或需要更多引擎行为，可评估 B2 C++ 作为 server 主干；
- 需要先解决工具链与许可问题。

不建议：
- 将 2697 原生 EXE 作为最终开发主干；
- 直接把 1.1.1.13/3.3.3.3 字段名和 offset 标成 2697。

## 5. MVP 不作假设

- 不把字段长度匹配当作 opcode 匹配。
- 不把离线编码通过当作客户端兼容。
- 不把“进入大厅”当作“进入战斗”。
- 不把 2697 服务端能写消息当作客户端能读消息。
