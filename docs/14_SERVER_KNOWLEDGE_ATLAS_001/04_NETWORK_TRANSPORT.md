# 04 — 网络传输层 / NETWORK TRANSPORT

> 不能因为“都用 UDP”或“都有 Netchan_*”就认定协议相同。本文分别给出各项目实现与证据。

## 1. 传输层分层（三视角）

```
应用层  clc/svc 消息          (03/14 协议档案)
   ↓
消息层  MSG_* 位/字节流        (05 序列化档案)
   ↓
传输层  netchan + 分片/重排    (本文)
   ↓
记录层  bdDTLS DATA 记录       (仅 CODOL：加密/MAC/序列号)
   ↓
握手层  NAT / INIT / COOKIE    (仅 CODOL：P-224 ECDH)
   ↓
UDP socket
```

**关键区分：** 有 `Netchan_*` 的共享代码（Old/1113）与 **CODOL 专有的 bdDTLS 记录层/握手层** 是**两层不同的东西**。前者是 Quake3 血统；后者是 CODOL 自身证据。

## 2. socket 生命周期

| 项目 | 证据 | 等级 |
|---|---|---|
| OLD/1113 | `NET_Init`（sys_net.c:3694）→ `NET_Config(qtrue)`；`Win_Net` 创建 UDP socket；`--codol-info` 分支不开 socket | VERIFIED（源码） |
| 2697 | 与 OLD/1113 同族导入 WS2_32（含新增 `inet_pton/getpeername/htonl/WSASetLastError`）；11 个 loopback 守卫包装 socket API | VERIFIED（导入差分）/ STATIC-INFERENCE（顺序） |
| C-2697 | 9 处 socket() 创建点，逐一给出 (af,type,proto)；套接字抽象类 vtable 0xD8E3A8，ctor 0xC65D30，工厂 0xC65D70（分配 0x24 B） | VERIFIED（EV-Battle-Sockets） |
| CoD4x | `sys_net.c` 事件循环；`Netchan_Init(qport)` | VERIFIED（源码） |
| IW4x | 客户端侧 `Network.cpp`；**无服务器 socket 生命周期** | VERIFIED（缺服务器源码） |

**C-2697 socket 枚举（关键）：**

| # | 调用点 | af / type / proto | 判定 |
|---|---|---|---|
| 1 | 0x77FC11 | 6 / 2 / 1000 | AF_IPX + SOCK_DGRAM + NSPROTO_IPX（局域网广播） |
| 2 | 0xAD6D7F | 来自描述符 | 通用 socket 包装（可被 `[edi+0x1B8]` 钩子接管） |
| 3 | 0xBB18B9 | 2 / 2 / 0x11 | **AF_INET + SOCK_DGRAM + IPPROTO_UDP** |
| … | … | … | 共 9 处 |

## 3. UDP 收发与包边界

| 项目 | 实现 | 证据 |
|---|---|---|
| OLD/1113 | `NET_UDPPacketEvent` 单一收包入口；`CODOL_NetworkReceive` 优先于 `SV_PacketEvent` | EV-Old-Recv |
| 2697 | 同族收包入口；`codol_loopback_win32.c` 的 11 个 `_guard_*` 包装 send/recv | EV-2697-Guards |
| C-2697 | 真实 IAT 调用点：call [recv] 0x602441/0x6029BE/0x6052AD/0x784F7F/0x788135；jmp [recv] 0x76D65E；call [recv] 0x775A6E；call [sendto] 0x775AA2；call [recvfrom] 0x775ADE；call [send] 0x77592C | EV-C-2697-NetCalls |

## 4. netchan 与序列号

### 4.1 CODOL 自有 netchan（OLD/1113 源码，VERIFIED）

`codol\net\codol_netchan.c:8-49`（`CODOL_NetchanProcess`）、`codol_wire.c:22-95`：

| 项 | 值 |
|---|---|
| 头 | `{u32 sequence|flags, [u16 qport 仅 server]}` |
| flags | FRAGMENT_BIT `0x80000000`、FORCE_ACK `0x40000000`、ACK `0x20000000`、MASK `0x1fffffff` |
| 分片 | 6 B `{index, last, stride=1162, chunk}` |
| body 变换 | `CODOL_Xor`（对称 XOR） |
| 上限 | 分片 1162 B，最多 128 片（`CODOL_MAX_MESSAGE = 1162*128`） |
| 丢包/乱序 | ACK_BIT 包被丢弃；32 位重放窗口（association established 后） |

### 4.2 CoD4x netchan（外部参考，VERIFIED 源码）

`netchan.c`：`PACKET_HEADER 10`（4 B seq + [2 B qport] + 4 B fragment start）、`MAX_MSGLEN 0x20000`、`FRAGMENT_BIT (1<<31)`、`seq == -1 → OOB`。

### 4.3 IW4x netchan（外部参考）

`netchan_t` 布局与 CoD4x **1:1 相同** → 二者共享 Quake3 血统。**CODOL 未发现该结构。**

| 对照 | CODOL 自有 | CoD4x | IW4x |
|---|---|---|---|
| 头长度 | 4/6 B（依方向） | 10 B（含 fragment start） | 与 CoD4x 相同 |
| 分片描述 | 6 B `{index,last,stride=1162,chunk}` | 4 B start + 2 B len | 同 CoD4x |
| body 变换 | XOR | 无（可选） | 无加密 |
| 上限 | 1162×128 | 0x20000 | 0x20000 |

**结论：** CODOL 的 netchan **不是** CoD4x/IW4x netchan 的同一实现（头长度、分片描述、上限均不同）。最多算 **ARCHITECTURAL_ANALOGY**。

## 5. 记录层与握手层（仅 CODOL，VERIFIED / 部分 UNKNOWN）

### 5.1 bdDTLS 握手（EV-DTLS-Wire）

| 阶段 | 类型字节 | 长度 | 证据 |
|---|---|---|---|
| NAT 遍历 | 0x0D → 回显 0x0C | 29 B | VERIFIED |
| INIT | 0x01 (`01 02`) | 16 B | VERIFIED |
| INIT_ACK | 0x02 | 38 B | VERIFIED |
| COOKIE_ECHO | 0x03 | **189 B（源码）vs 219 B（C#）** | SOURCE-CONFLICT |
| COOKIE_ACK | 0x04 (`[0]=4,[1]=2`) | 114 B | VERIFIED |
| DATA | 0x06 (`06 02 …`) | 16 B 头 + cipher | VERIFIED |

- 曲线：**P-224 (secp224r1)**，公钥 100 B。
- INIT security id：`[8:16]` 与 8 B id 比对。
- COOKIE_ECHO 结构（源码版）：`[0]=3,[1]=2,[2:4]=init_ack[16:18],[4:6]=0,[6:44]=init_ack(38B),[81:89]=init[8:16],[89:189]=100B 客户端公钥`。

### 5.2 DATA 记录（EV-DTLS-Wire）

```
+0  [0]=0x06  [1]=0x02
+2  tag/counter  (LE u16)          ← 序列号
+4  counter16    (LE u16)
+6  MAC 截断 8 B
+14 len          (LE u16)
+16 cipher
MAC 输入 = record[0:6] + cipher
```

### 5.3 密码学原语冲突（SOURCE-CONFLICT）

| 材料 | 原语 |
|---|---|
| `codol_crypto.c` 源码 | 有一套 AES/MAC 实现 |
| C# `CodolProtocol.cs` / `Aes128.cs` | AES-128 |
| DEV-BOOKING-021 §2-§3 | 主题为 XOR/混淆；**OpenSSL 静态表 ≠ 使用 DTLS** |

三方对“记录层原语”的描述不完全一致 → 保留为冲突（EV-DTLS-Conflict, EV-DTLS-OpenSSL）。**不强行统一。**

## 6. 加密 / 压缩 / 封装

| 机制 | CODOL | CoD4x | IW4x |
|---|---|---|---|
| 传输加密 | bdDTLS DATA（MAC + counter） | 无 | 无 |
| body 混淆 | CODOL_Xor（netchan body） | CoD4x 仅 XOR 混淆 | 无 |
| 应用层压缩 | Huffman（`Huffman_InitMain`；但 CODOL clc 分支**不做** Huffman 解压） | Huffman | Huffman |
| 平台层 | TCLS/TenProtect（启动前，非游戏通道） | 无 | 无 |

证据：EV-DTLS-Wire, EV-clc-Nohuff, EV-Battle-Distinct。

## 7. 超时 / 心跳 / 队列

| 项 | 证据 |
|---|---|
| 服务器心跳 | `SV_MasterHeartbeatInit`（sv_main.c:3717 区域） |
| 统计轮询 | `sh1x_status`（codol_match_status.c:38-61） |
| 可靠消息队列 | `SV_UpdateServerCommandsToClient`（sv_snapshot.c:97-111） |
| 限速 | `SVC_RateLimitInit` |
| 分片 ACK/重传调度 | OLD 作者自述**待完成**（EV-Old-Incomplete） |

---

## 8. 传输层对照结论（回答问题 3.2）

| 问题 | 结论 | 等级 |
|---|---|---|
| 各项目是否同一传输实现？ | 否。CODOL（Old/1113/2697 同族）与 CoD4x/IW4x 是三套不同的 netchan | VERIFIED |
| CODOL 是否用标准 DTLS？ | 有 bdDTLS 风格记录层（自定义，非标准 TLS）；客户端 OpenSSL 字符串不能作证 | VERIFIED |
| CoD4x 可否复用为 CODOL 传输？ | 只能借**骨架/事件循环**，不能借协议/加密 | VERIFIED |
| IW4x 可否复用？ | 只能借 OOB/发现/认证信封；**无服务器源码** | VERIFIED |
| 2697 与 Old/1113 传输是否同一？ | 同为 CODOL 自有 netchan 家族；2697 叠加 loopback 守卫与 archive 门控 | STATIC-INFERENCE |
---

# === 追加：2697 传输层常量（UPDATE-2, 2026-10-12） ===

从 `S-2697` 反汇编直接读出（证据 EV-2697-NetchanConst）：

```asm
; _CODOL_NetchanTransmit  RVA 0x999B6
004999FA  cmp  ecx,0x1fffffff     ; 序列掩码
00499A02  cmp  eax,0x489          ; 1161 = CODOL_FRAGMENT_SIZE-1
; _CODOL_NetchanTransmitNextFragment  RVA 0x998D8
00499900  mov  eax,0x70cc729      ; ceil(2^37 / 1162)
00499905  mul  edx
00499907  shr  edx,5              ; /32  → 分片序号
```

| 常量 | 值 | 源码对应 | 匹配 |
|---|---|---|---|
| `0x489` | 1161 | `CODOL_FRAGMENT_SIZE-1` | ✔ |
| `0x24500` | 148,736 | `1162 × 128`（`CODOL_MAX_MESSAGE`） | ✔ |
| `0x1fffffff` | 29 位 | 序列掩码 | ✔ |
| `0x70cc729` | 118,277,929 | `ceil(2³⁷/1162)` | ✔ 精确 |

**结论：** 2697 的 netchan 常量与 CODOL 家族一致，与 CoD4x（`PACKET_HEADER 10` / `MAX_MSGLEN 0x20000`）不一致 → **传输层 `PORTED_CODE` 已获常量级证据**（`13` §3.2、`REVISION_LOG.md` REV-009）。
