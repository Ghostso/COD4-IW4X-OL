# BATTLE_PROTOCOL_TRACE — B 层：战斗服务器协议

**目标版本：** CODOL 3.19.26.22 / Build 1649370
**分析对象：** `COD OL\codoMP_client_shipRetail.exe`（`36997674…`，`SizeOfImage 0x0E659000`）
**性质：** 只读静态追踪。
**边界纪律：** 本节只写战斗网络；大厅见 `LOBBY_PROTOCOL_TRACE.md`；交接见 `LOBBY_BATTLE_BRIDGE.md`。

---

## 1. 战斗链总览

```
[战斗服务器 UDP]
   |  带外包: FF FF FF FF + getchallenge / connect / gamestateupdate / heartbeat
   |  profile stats: <ProfileStatsPrefix> + chunkIndex + payload
   v
[DTLS 风格握手] NAT(0x0D) / INIT(0x02) / COOKIE / COOKIE_ACK(100B ECDH)
   v
[packetEvent 0x00467520]
   v
[netchanProcess 0x005A5960]  (序列 / 分片 / 重组)
   v
[decodeMessage 0x0046BF80] -> [parseServerMessage 0x0046E6A0]
   |  opcode 0..5
   +-> 0 snapshot     -> parseSnapshot 0x0046D170
   +-> 1/2 serverCmd  -> (文本 / 二进制文本)
   +-> 3 gamestate    -> parseGameState 0x0046DEA0
   +-> 4 configstring -> parseConfigStrings 0x0046DB20
   +-> 5 EOF
   v
[parsePacketEntities 0x0046C2F0 / parsePacketClients 0x0046CC60 / parsePacketAux 0x0046C840]
[parseMatchState 0x0046D060 / parsePlayerState 0x005A4230]
   v
[连接状态机] Free -> Connected -> ClientLoading -> Active
```

---

## 2. 传输层与握手

### 2.1 带外（OOB）连接

| 项 | 值 | 等级 | 证据 |
|---|---|---|---|
| OOB 前缀 | `FF FF FF FF` | CONFIRMED（源码常量 + netchan 反证） | `ol-mod\qcommon\net_chan_mp.cpp:14`（`OobPrefix`） |
| 连接命令 | `getchallenge` / `connect` / `gamestateupdate` / `heartbeat` | CONFIRMED | `sv_client_mp.cpp:511-518`（服务端路由） |
| profile stats 前缀 | `<ProfileStatsPrefix> + chunkIndex + payload`，分块 | CONFIRMED | `sv_client_mp.cpp:522-556` |
| challenge 校验对象 | `connect` 参数 vs 服务端挑战 | CONFIRMED | `sv_client_mp.cpp`（`SV_GetChallenge`/`SV_DirectConnect`） |

> **判定：** 战斗连接使用**带外文本命令**建立（`getchallenge` → `connect` → `stats` → `heartbeat`），这与 3.3.3.3 的 NAT/INIT/COOKIE 二进制首包**不同源**，属 1649370 的形态。**REFERENCE 强度 = 强（同构建常量）。**

### 2.2 DTLS 风格握手分组

| 包 | 类型 | 关键字段 | 等级 |
|---|---|---|---|
| NAT 探针 | 首字节 `0x0D` → 应答 `0x0C` | — | REFERENCE（同构建源码） |
| INIT | type `0x02` | `verificationTag` / `counter` / `initTag` / `securityId`(8B) | REFERENCE |
| INIT_ACK | — | 38B cookie | REFERENCE |
| COOKIE_ECHO | — | `commonAddress`(**67B**) / `securityId`(8B) / `publicKey`(**100B**) | REFERENCE |
| COOKIE_ACK | — | 114B（67 + 8 + 100 结构） | REFERENCE |
| DATA | type `0x06` | header **16B**：`verificationTag(2)` / `sequenceNumber(2)` / `authenticator(8)` / `encryptedSize(2)` | REFERENCE |
| 密钥派生 | digest(20B) → aesKey(16B) / hmacKey(24B) / iv(sequence, verificationTag) | — | REFERENCE |

**重要修正（已并入）：** `bdCommonAddr` 线上为 **67 字节**，不是 37；旧值会使后续字段整体前移 30 字节。证据：`net_dtls_cod.hpp`（*"67, not 37 … At the old offsets the security id came out of the 00FF00FF0000 sentinel run and the ECC parse started mid-sentinel, giving 'expected DER SEQUENCE'"*）。

---

## 3. netchan 层

| 项 | 值 | 等级 | 证据 |
|---|---|---|---|
| 处理函数 | `Netchan_Process` = **`0x005A5960`** | CONFIRMED（CODREF + 与 1649370 绑定） | `net_chan_mp.hpp` 注释；`CodolNetchanTrace.py:141` |
| 序列号掩码 | `0x1FFFFFFF` | CONFIRMED | `net_chan_mp.hpp`（`NetchanSequenceMask`） |
| 分片大小 | `1154` 字节（`NetchanFragmentSize`） | CONFIRMED | 同上 |
| 最大分片数 | `128` | CONFIRMED | 同上 |
| 最大分片消息 | `0x20000` | CONFIRMED | 同上 |
| 序列标志 | `0x80000000` 分片 / `0x40000000` 可靠 / `0x20000000` 分片确认 | CONFIRMED | `net_chan_mp.cpp` 注释（CODOL `0x005A5960`） |
| 分片头布局 | `sequence(4)` \| `index(1)` \| `lastIndex(1)` \| `stride(2)` \| `length(2)` | CONFIRMED | 同上（`FragmentHeaderSize = 10`） |
| 发送侧 | `Netchan_Transmit` / `Netchan_TransmitNextFragment` | CONFIRMED | `net_chan_mp.hpp` |
| 客户端命令类型 | MoveDelta=0 / MoveNoDelta=1 / Reliable=2 / Eof=3 | CONFIRMED | `ClientCommandKind` |
| 服务端命令类型 | Reliable=1 / ReliableBinary=2 / Eof=**5** | CONFIRMED | `ServerCommandEof = 5`（见 §4.1） |
| usercmd 解扰密钥 | `checksumFeed ^ messageAcknowledge ^ Com_HashKey(serverReliableCommand)` | CONFIRMED | `net_chan_mp.hpp`（`userCmdKey`） |

> **netchan 关键差异：** 3.3.3.3 的分片头是 `qport/start/length` 旧布局；**1649370 是 `index/lastIndex/stride/length` 新布局**。混用会导致解析整体错位。

---

## 4. 消息分派层

### 4.1 服务端命令 opcode 表

| opcode | 名称 | 处理函数 | 等级 |
|---|---|---|---|
| 0 | snapshot | `parseSnapshot 0x0046D170` | CONFIRMED（RVA + 名称） |
| 1 | serverCommand | （文本命令） | CONFIRMED |
| 2 | binaryCommand | （二进制文本） | CONFIRMED |
| 3 | gamestate | `parseGameState 0x0046DEA0` | CONFIRMED |
| 4 | configstring block start | `parseConfigStrings 0x0046DB20` | CONFIRMED |
| **5** | **EOF** | 终止 | CONFIRMED（OLfinal 无 opcode 6） |

**证据：** `sv_snapshot_mp.hpp` / `sv_gamestate_mp.hpp` 常量；`net_chan_mp.hpp`（`ServerCommandEof=5` 的 MEASURED 论证：54,682/54,682 demo snapshot 末字节、gamestate configstring 块终止符、clientNum/checksumFeed 对之后的字节）。

> **关键否定结论：** OLfinal **没有 opcode 6**；用 6 终止的消息不是「读错」，而是落入解析循环的错误出口。

### 4.2 客户端 → 服务端接收链（目标 EXE RVA）

| 顺序 | 函数 | RVA | 等级 | 证据 |
|---:|---|---|---|---|
| 1 | packetEvent | `0x00467520` | CONFIRMED（版本标注） | `CodolNetchanTrace.py:140` / `CodolJoinTrace.py:27` |
| 2 | netchanProcess | `0x005A5960` | CONFIRMED | `CodolNetchanTrace.py:141` |
| 3 | decodeMessage | `0x0046BF80` | CONFIRMED | `CodolNetchanTrace.py:142` |
| 4 | parseServerMessage | `0x0046E6A0` | CONFIRMED | `CodolNetchanTrace.py:143` |
| 5 | parseGameState | `0x0046DEA0` | CONFIRMED | `CodolNetchanTrace.py:144` |
| 5 | parseConfigStrings | `0x0046DB20` | CONFIRMED | `CodolNetchanTrace.py:145` |
| 5 | storeRawConfigString | `0x0046DAA0` | CONFIRMED | `CodolNetchanTrace.py:146` |
| 5 | parseSnapshot | `0x0046D170` | CONFIRMED | `CodolNetchanTrace.py:147` |
| 6 | parseMatchState | `0x0046D060` | CONFIRMED | `CodolNetchanTrace.py:149` |
| 6 | parsePacketClients | `0x0046CC60` | CONFIRMED | `CodolNetchanTrace.py:150` |
| 6 | parsePacketEntities | `0x0046C2F0` | CONFIRMED | `CodolNetchanTrace.py:151` |
| 6 | parsePacketAux | `0x0046C840` | CONFIRMED | `CodolNetchanTrace.py:152` |
| 7 | parsePlayerState | `0x005A4230` | CONFIRMED | `CodolNetchanTrace.py:148` |
| 7 | readBit / readBits | `0x00400C370` / `0x005A13A0` | CONFIRMED | `CodolNetchanTrace.py:156-157` |
| 7 | readFieldIndex | `0x005A3250` | CONFIRMED | `CodolNetchanTrace.py:155` |
| 7 | readDeltaField | `0x005A27F0` | CONFIRMED | `CodolNetchanTrace.py:153` |
| 7 | readDeltaEntity | `0x005A3670` | CONFIRMED | `CodolNetchanTrace.py:154` |
| — | playerStateFields | `0x00855F70`（**235 字段 × 12B**） | CONFIRMED | `CodolNetchanTrace.py:160-162` |
| — | configChecksumCompare | `0x0046E06B` | CONFIRMED | `CodolNetchanTrace.py:166` |

> 上述全部 RVA 已在**目标 EXE 的节区映射内**核验（均落于映像 `<0x0E659000`）⇒ 属目标构建，非跨版本搬用。

### 4.3 gamestate / configstring 语义（来自 1649370 绑定源码）

| 项 | 值 | 等级 |
|---|---|---|
| gamestate 解析器对 | A `0x0046DB20` ↔ C `0x00472D80`（`CL_ParseGameStateMessage`） | REFERENCE（`CODDIFF(1649370)`） |
| `CG_ConfigStringModified` 对 | A `0x57A300` ↔ C `0x60FD80` | REFERENCE |
| 延迟资产加载器对 | A `0x57A080` ↔ C `0x60F650` | REFERENCE |
| CL_ParseGamestate 实块 | `0x00454C1A`（含 `0x00454CD6` / `0x00454D3D` 调用点） | REFERENCE（`CODDIFF(1649370)`） |
| 关键 configstring 索引 | 0 serverinfo / 1 systeminfo / 2 gamename / **15 match end time** / **16 map center** / 463/464/465 UI 限制 / **856..951 hint strings**（起点 863）/ 13 fog | REFERENCE（`sv_gamestate_mp.hpp`） |
| 武器 configstring 带 | 900 → **1700** 条（1649370 相对 3.3.3.3 扩展） | REFERENCE |
| 索引整体位移 | 低区不动；player-name +477；主体 +517；武器 +517 且扩容；其上加 +5446 | REFERENCE |

---

## 5. 快照（snapshot）链路

### 5.1 已确认

| 项 | 值 | 等级 |
|---|---|---|
| snapshot 入口 | `parseSnapshot 0x0046D170` | CONFIRMED |
| 实体解析 | `parsePacketEntities 0x0046C2F0` | CONFIRMED |
| 客户端表 | `parsePacketClients 0x0046CC60` | CONFIRMED |
| 辅助块 | `parsePacketAux 0x0046C840` | CONFIRMED |
| delta 字段/实体读取 | `readDeltaField 0x005A27F0` / `readDeltaEntity 0x005A3670` | CONFIRMED |
| 字段索引读取 | `readFieldIndex 0x005A3250` | CONFIRMED |
| playerState 字段表 | `0x00855F70`，235 字段 × 12B | CONFIRMED |
| 命令终止 | EOF = `5` | CONFIRMED |

### 5.2 未确认（不得推测）

| 项 | 状态 |
|---|---|
| snapshot 帧内逐字段位宽 | `UNKNOWN` |
| delta baseline（首帧 / 增量基准）| `UNKNOWN` |
| 实体新增 / 删除的显式规则 | `UNKNOWN` |
| `first` 标志语义 | `UNKNOWN` |
| 实体编号（entityId）与玩家槽映射 | `UNKNOWN`（`parsePlayerState 0x5A4230` 已知但内部字段未展开） |

> **纪律：** `sv_snapshot_mp.cpp`（1.39 MB）虽含大量实现，但属同构建源码的**服务端重建**，其字段位宽在未与目标客户端解析器逐条对齐前**只能作 REFERENCE**，不得写入 CONFIRMED。

---

## 6. 客户端初始化状态转换

| 状态 | 触发 | 证据 | 等级 |
|---|---|---|---|
| `Free` | 初始 | `sv_client_mp.cpp`（`ClientState`） | CONFIRMED（服务端模型） |
| `Connected` | `connect` 带外包成功 | 同上（`SV_DirectConnect`） | CONFIRMED |
| `ClientLoading` | gamestate 数据报到达 | 同上（注释：*"Connected client to ClientLoading until the gamestate datagram"*） | CONFIRMED |
| `Active` | `gamestateupdate` 阶段 `== 6` | 同上（`slot->state = ClientState::Active`） | CONFIRMED |
| 首帧 snapshot 排程 | 进入 `Active` 时 `nextSnapshotTime = now`，且 `deltaMessage = -1`（丢弃加载期 baseline） | 同上 | CONFIRMED |

**客户端侧对应锚点（目标 EXE）：**

| 锚点 | RVA | 等级 |
|---|---|---|
| connectionState | `0x0162E7EC` | CONFIRMED（`CodolNetchanTrace.py:169`） |
| encodedClientConnection（异或 `0xD362501F`） | `0x0162A538` | CONFIRMED（`CodolNetchanTrace.py:170`；`CodolJoinTrace.py:39`） |
| encodedClientActive | `0x0162E838` | CONFIRMED（`CodolNetchanTrace.py:171`） |
| localClientIndex | `0x007417BA8` | CONFIRMED |
| setConnectionState | `0x001BE030` | CONFIRMED（`CodolJoinTrace.py:40`，标注 3.19.26.22 IDB） |
| connectFromParty | `0x001C8150` | CONFIRMED（`CodolJoinTrace.py:44`） |
| connectionStates | `0x072446B0` | CONFIRMED（`CodolJoinTrace.py:38`） |
| disconnectCommand / completeDisconnect | `0x001AA610` / `0x001C0FD0` | CONFIRMED（`CodolJoinTrace.py:41,45`） |

> **重要修正记录：** `CodolJoinTrace.py:31-37` 明确写「旧 `0x197D20` RVA 属于**另一镜像修订**；当前 3.19.26.22 IDB 的 Com_Error 为 `sub_4F82E0`（RVA `0x000F82E0`）」。这正是任务要求「不得混用不同二进制 RVA」的实例。

---

## 7. B 层结论

- **战斗接收链顺序已确认**：packetEvent → netchanProcess → decodeMessage → parseServerMessage → {snapshot/gamestate/configstring} → {entities/clients/aux} → {matchstate/playerstate/delta}。
- **netchan 常量与分片布局已确认**（1649370 新布局）。
- **服务端命令 opcode 0..5 已确认**（无 6）。
- **未闭合**：snapshot 帧内位宽、delta baseline、实体增删、entityId 映射。
- **未观测**：真实战斗端点（`BATTLE_28960 = NOT_OBSERVED`）；客户端从未发出战斗首包。
- **不得声称**：收到 gamestate = 已进入可交互战斗。
