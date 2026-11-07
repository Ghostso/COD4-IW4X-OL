# 05 — 消息与序列化 / MESSAGE SERIALIZATION

> 目标：追踪“调用方 → 编码函数 → 缓冲区 → 传输层”与“传输层 → 解码函数 → 分派 → 状态更新”两条方向。

## 1. 序列化原语（MSG_*）

### 1.1 OLD/1113（源码，VERIFIED）

`dedicated\src\msg.c`：

| 函数 | 行号 | 行为 |
|---|---|---|
| `MSG_WriteByte` | 141 | 越界报 `MSG_WriteByte: range error` |
| `MSG_WriteShort` | 158 | 越界报 range error |
| `MSG_WriteLong` | 174 | — |
| `MSG_WriteData` | 211 | 逐字节写 |
| `MSG_WriteString` | 218 | 空串写 1 B 0；超 `MAX_STRING_CHARS` 写空串 |
| `MSG_WriteBits` | 305 | 位流写入 |
| `MSG_WriteDeltaEntity` | 395-452 | 位标志 + 5 位 changedBitIndex + 实体索引位 |

**位流与字节流共存**：`MSG_WriteBits` 与 `MSG_WriteByte` 混用，是 Snapshot/Entity 序列化的基础。

### 1.2 CoD4x（外部参考，VERIFIED）

`msg.c` 同样有 `MSG_WriteByte/Short/Long/Data/String/Bits`，含 `Huffman`（`#include "huffman.h"`）。命名与结构同 CODOL 家族 → 共同 Quake3 血统。

### 1.3 IW4x（外部参考）

IW4x 序列化在客户端 `Game/` + `Components/Modules/`（如 `ConfigStrings.cpp`、`ServerCommands.cpp`、`ClientCommand.cpp`、`ConnectProtocol.cpp`）。**非服务器实现。**

## 2. 客户端命令（clc）分派（OLD/1113，VERIFIED）

```
sv_client.c:2505   MSG_ReadBits(&decompressMsg, 3)   ← 3 位 clc opcode
net_game_conf.h:85-99  clc_ops_e:
  clc_move        = 0
  clc_moveNoDelta = 1
  clc_clientCommand = 2
  clc_EOF         = 3
  clc_nop         = 4
  clc_download    = 5
  clc_sApiData    = 5
```

- CODOL 分支**不做 Huffman 解压**（`sv_client.c:2422-2427`）——与标准 Quake3 不同。
- 分派：`clc_move/clc_moveNoDelta → SV_UserMove`；`clc_clientCommand → SV_ClientCommand`；`clc_EOF → return`。

**方向：** 客户端→服务端。生产端（客户端）在 C-1113 上**未观测**；服务端分发器为 VERIFIED。

## 3. 服务端命令（svc）与快照流（OLD/1113，VERIFIED）

```
sv_snapshot.c:61-62   SV_WIRE_SERVERCOMMAND = 1
                      SV_WIRE_EOF           = 5
sv_snapshot.c:97-111  SV_UpdateServerCommandsToClient
net_game_conf.h:64-78 svc_ops_e
```

| svc | 线上值 | 形态 |
|---|---|---|
| serverCommand | 0x01 | `{0x01, u32 cmdSeq, cstring} xN`（在 snapshot 头之前） |
| gamestate (legacy) | 0x02 | `_CODOL_WriteGamestate` RVA 0xA865A，终止 0x05 |
| configstring (legacy) | 0x03 | `_CODOL_WriteConfigstrings` RVA 0xA857F，终止 0x05 |
| snapshot | 0x00 | `SV_WriteSnapshotToClient`（sv_snapshot.c:224）**仍用 IW3 序列化器** |
| svc_EOF | 0x05 | STRONG_CANDIDATE |

## 4. 2697 消息层（VERIFIED 字节 / STATIC-INFERENCE 语义）

### 4.1 消息类型重新核验（EV-2697-MsgTypes）

| 流 | 旧通道（三样本一致） | 2697 通道（NEW-only） |
|---|---|---|
| gamestate | `0x02` | 起 `0x03`，终 `0x06` |
| configstring | `0x03` | 内部写 `0x04`，终 `0x06` |
| snapshot | `0x00` | `0x00`（多处）+ 内部 `0x06` |
| serverCommand（可靠命令） | `0x01` | `0x02`（结构化 payload）；回退 `0x01` |
| EOF | `0x05` | `0x06` |

> **陷阱：** 2697 gamestate 起始字节 `0x03` 与旧 configstring 同值，但属于**另一套 2697 上下文**，不可直接等同解释。

### 4.2 Reliable command 双格式（EV-2697-RC-Format，VERIFIED）

```
_SV_WriteReliableCommand  RVA 0x8612E
  if (ret < 0)  Com_Error
  if (ret == 0) → 0x01 | long | NUL-terminated string
  if (ret > 0)  → 0x02 | long | short(length) | data[length]
```

| 分支 | 写入点（RVA） |
|---|---|
| 0x02 byte | 0x8616B |
| 0x02 long | 0x8617D |
| 0x02 short | 0x86189 |
| 0x02 data | 0x8619F |
| 0x01 byte | 0x861D0 |
| 0x01 long | 0x861E2 |
| 0x01 string | 0x861EE |

### 4.3 边界常量（EV-2697-RC-Limits，VERIFIED）

`0xCCC`、`0x7FFB`、`0xFF`、`0x3FB`、`0x3FC`；长度 1 拒绝；`O → 0x01`、`Z → 0x00`、大写两位 hex 合成字节（小写不接受）。

### 4.4 2697 分派（客户端）— BLOCKED

- 无 `opcode 0x02 → cmp/shl-jump → 0xA2E50` 的可复现控制流（EV-C-2697-Dispatch-Blocked）。
- 客户端 `0xA2E50` 字段形状 `long(4)+short(2)+payload` **与服务端 0x02 负载匹配**（EV-C-2697-A2E50）。
- 因此：**字段形状 VERIFIED，opcode 绑定 STATIC-INFERENCE，分派 BLOCKED。**

## 5. Gamestate / Configstrings / Snapshot（简要；详见 07）

| 项 | OLD/1113 | 2697 |
|---|---|---|
| gamestate opcode | 0x02 | 0x03 |
| gamestate 终止 | 0x05 | 0x06 |
| configstring opcode | 0x03 | 0x04 |
| configstring 终止 | 0x05 | 0x06 |
| configstring 数量 | 6519（武器从 5362 起） | short count ≤ 0x1DD7 |
| snapshot | IW3 serializer（未收敛） | `_CODOL2697_WriteSnapshot → _WriteSnapshotReached` |

## 6. 双向调用链追踪结论

### 6.1 编码方向（调用方 → 编码 → 缓冲 → 传输）

| 项目 | 链 | 等级 |
|---|---|---|
| OLD/1113 | `SV_Frame → CODOL_Publish* → MSG_Write* → SV_SendClientMessages → netchan` | VERIFIED |
| 2697 reliable | `0x710B7/0x86DE0/0x873E4 → _SV_WriteReliableCommand 0x8612E → 0x02 字段 → _SV_SendMessageToClient 0x86B06 → _SV_Netchan_Transmit 0x856B6` | VERIFIED |
| 2697 gamestate | `SV_SendClientGameState → _CODOL2697_WriteNativeGamestate(门控) → _WriteGamestate 0xA21B8 → _WriteConfigstrings 0xA0468` | VERIFIED |
| 2697 snapshot | `_CODOL2697_WriteSnapshot 0xA4FA0 → _WriteSnapshotReached 0xA4860 → 分段 writer → 区域复制` | VERIFIED |

### 6.2 解码方向（传输 → 解码 → 分派 → 状态）

| 项目 | 链 | 等级 |
|---|---|---|
| OLD/1113 | `NET_UDPPacketEvent → CODOL_NetworkReceive → MSG_InitReadOnly → SV_PacketEvent → clc 分派` | VERIFIED（服务端侧） |
| 2697 | 服务端侧同族；**客户端侧未闭合** | 客户端 BLOCKED |

---

## 7. 序列化对照结论

1. `MSG_*` 原语是 **Quake3/CoD 公共血统**（OLD/1113 与 CoD4x 同名同结构）。**名字相同 ≠ CODOL 与 CoD4x 同一构建。**
2. **CODOL 的关键差异在消息层之上**：clc 分支去掉 Huffman；2697 引入新的 opcode 集合（0x02/0x03/0x04/0x06）。
3. **只发现同名函数最多判定为候选对应关系**。2697 的 `0x02` 与客户端 `0xA2E50` 是“形状匹配 + 绑定未闭合”，不是“已证实实现一致”。