# 06 — 客户端/服务端协议总览 / CLIENT-SERVER PROTOCOL

## 1. 协议栈总览（CODOL 家族）

```
┌──────────────────────────────────────────────────────────────┐
│ 平台/启动层（非游戏通道）                                      │
│   TCLS → CreateProcessW → 命令行 -q/-i/-s/-g/-u/-n            │
│   TAS/SHELL 共享内存（Tenio cipher）                           │
│   IIPS / TenProxy / TGuard / ACE                              │
└──────────────────────────────────────────────────────────────┘
                          ↓ （游戏进程内）
┌──────────────────────────────────────────────────────────────┐
│ 大厅/控制面（HTTP/自有契约）                                    │
│   登录、心跳、配置下发、匹配（21/5 findSessions 等）             │
│   由 REF_LOBBY_KIT / CODOLServer / ol-mod backend 模拟          │
└──────────────────────────────────────────────────────────────┘
                          ↓ （下发 Battle 端点 127.0.0.1:28960）
┌──────────────────────────────────────────────────────────────┐
│ 战斗/游戏通道（UDP）                                            │
│   ┌────────────────────────────────────────────────────────┐ │
│   │ 握手层 NAT/INIT/COOKIE（P-224 ECDH，自定义 bdDTLS 风格） │ │
│   ├────────────────────────────────────────────────────────┤ │
│   │ 记录层 DATA 16B 头（tag/counter/MAC8/len）              │ │
│   ├────────────────────────────────────────────────────────┤ │
│   │ netchan（序列号/分片/XOR）                              │ │
│   ├────────────────────────────────────────────────────────┤ │
│   │ 消息层 clc（3位）/ svc（0x00..0x06）                    │ │
│   ├────────────────────────────────────────────────────────┤ │
│   │ 应用层 Gamestate / Configstrings / Snapshot / 可靠命令   │ │
│   └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

**关键分层事实（VERIFIED）：**
- 平台层（TCLS/IIPS/TenProtect）与游戏通道**是两套东西**。平台组件存在 **不等于** 游戏协议调用链闭合（任务书 6.1 硬要求）。
- 战斗端点由**大厅下发**（会话记录 ① Hostaddress），**不是客户端常量**；端口 28960 与 CoD4X `PORT_SERVER` 相同只是**数值巧合，不构成血缘**。

## 2. 连接建立时间线（CODOL 战斗通道）

```
客户端                                        服务端
  │  NAT 0x0D (29B)                            │
  ├───────────────────────────────────────────► NET_UDPPacketEvent
  │                                            │  CODOL_NetworkReceive:366
  │  NAT 0x0C (回显)                            │
  ◄───────────────────────────────────────────┤
  │  INIT 0x01 16B {01 02, ..., id[8:16]}       │
  ├───────────────────────────────────────────► CODOL_HandshakeInit (codol_handshake.c:12)
  │  INIT_ACK 0x02 (38B)                        │
  ◄───────────────────────────────────────────┤
  │  COOKIE_ECHO 0x03 (189B / 219B?)            │
  ├───────────────────────────────────────────► CODOL_HandshakeCookie (codol_handshake.c:40)
  │                                            │  CODOL_SharedSecret(P-224) → CODOL_DeriveKey
  │  COOKIE_ACK 0x04 (114B)                     │
  ◄───────────────────────────────────────────┤
  │  DATA 0x06 (16B 头 + cipher)                 │
  ├───────────────────────────────────────────► CODOL_AssociationOpenDetailed
  │                                            │  MSG_InitReadOnly → SV_PacketEvent:431
  │  → CS_CONNECTED → CS_PRIMED                 │
  │  ← gamestate (0x02 legacy / 0x03 2697)      │
  │  → 首个 usercmd                             │
  │  → CS_ACTIVE → snapshot                     │
```

证据：EV-DTLS-Wire, EV-Old-Recv, EV-Old-Connect, EV-DTLS-Client。

## 3. OOB / connectionless 命令

`SV_ConnectionlessPacket`（sv_main.c:2328）分派：

| 命令 | 处理 |
|---|---|
| `connect` | `SV_DirectConnect`（:2351） |
| `getchallenge` | `SV_GetChallenge`（:2379） |
| `getstatus` / `getinfo` / `stats` | 状态查询 |
| `rcon` | 远程命令（+ 环回 4×0xff 变体，net_game.c:43-53 / sv_main.c:2375） |
| `v` / SE-Query | — |

**环回 RCON：** `4x0xff + "rcon <password> <cmd>"`，仅 NA_LOOPBACK 或 127.x；C1 游戏流量不经此路径（EV-RCON）。

## 4. 版本/协议字段（SOURCE-CONFLICT）

| 字段 | 值 A | 值 B | 冲突 |
|---|---|---|---|
| 内部 codec | `CODOL_PROTOCOL 187`（codol_wire.h:8） | — | — |
| connectResponse 出站 | `protocol\1\shortversion\1.1.1.13` | — | — |
| 实机二分（2026-09-02） | 187 卡住客户端 | 1 能连 | `codol_connect.c:89-91` |

→ 保留为冲突（EV-Protocol-Conflict）：**内部选择 vs 出站线值**。任何“CODOL 协议号是 187”的断言都必须标注这一冲突。

## 5. 大厅与战斗的边界（VERIFIED）

| 层 | 谁负责 | 证据 |
|---|---|---|
| 进大厅 | 第三方 `REF_LOBBY_KIT\lobby_server.py` | EV-Lobby-Third |
| 大厅冻结 | `GOLDEN-LOBBY-001`（2026-10-07，只冻结大厅） | EV-Lobby-Golden |
| 战斗端点下发 | 21/5 `findSessions` 会话记录 ① Hostaddress | EV-Battle-Endpoint |
| 进战斗 | **未发生**：监听 28960 时 `BATTLE_RX=0` | EV-Battle-RX0 |
| 完整 PvE | `NOT_REPRODUCED` | EV-Lobby-NoFullPVE |

**因果纠正（重要）：** “缺少 Battle Server”曾被当作“客户端不进入战斗”的解释；**被 EV-Battle-RX0 推翻**——客户端根本没走到拨号阶段。因此下一步**不是**先写 Battle Server。

## 6. 协议总览结论

1. CODOL 战斗通道是**三层叠加**：自定义 bdDTLS 握手 + DATA 记录 + netchan/消息。
2. 与 CoD4x/IW4x 的**决定性差异在握手与加密**（它们都没有 cookie+ECDH）。
3. 2697 相对 Old/1113 是**同一家族的消息层升级**（新 opcode 集 + 门控），不是新协议。
4. 客户端消费侧是本档案最薄弱环节（多处 BLOCKED）。
5. 已证大厅 ≠ 已证战斗；两者必须分开陈述。