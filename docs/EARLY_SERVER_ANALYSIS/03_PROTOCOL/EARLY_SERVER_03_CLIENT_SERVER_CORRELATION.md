# 阶段 3 — 客户端/服务端协议对应关系（EARLY_SERVER_03_CLIENT_SERVER_CORRELATION）

样本（只读）：`D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server`
早期客户端（只读对照）：同包 `..\CODOL_Client\codoMP_client_shipRetail.exe`（1.1.1.13，20,918,752B，SHA-256 `904436480938632a...`）
现有项目（只读对照）：`D:\BaiduNetdiskDownload\使命召唤OL\CODOL-Combat-Server-v0.1\src\Codol\*`

证据等级沿用任务书：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / REFUTED / NOT_OBSERVED / INSTRUMENTATION_BLOCKED。
**静态分析**与**运行验证**分开标注。源码函数名真实可用，无需自拟 RVA。

---

## 0. 结论摘要

早期服务端的协议栈分两层，两层都由**同一份 native 源码**实现，且与**早期 C1.exe 的字符串表可对上**：

1. **传输层（bdDTLS，Demonware）**：NAT 遍历 → DTLS INIT/INIT_ACK → COOKIE_ECHO/COOKIE_ACK → 加密 DATA 记录。
   由 `dedicated/src/codol/net/codol_network.c` 单一入口 `CODOL_NetworkReceive` 驱动，密码学原语在 `codol_crypto.c`/`codol_association.c`/`codol_ecdh.c`。
2. **游戏层（netchan + OOB + clc/svc）**：DTLS DATA 解出的明文进入 `SV_PacketEvent`，走 connectionless 分发（getchallenge/connect/stats/heartbeat/rcon）或 `SV_ExecuteClientMessage` 的 **3 位 clc opcode** 分发。

**最强对应证据**：`codoMP_client_shipRetail.exe` 的 `.rdata` 里存在服务端源码逐字对应的 Demonware 类名——
`bdDTLSAssociation::sendInit/handleInitAck/handleInit/sendCookieEcho/handleCookieAck/sendData/handleData`、
`bdDTLSCookieEcho::bdDTLSCookieEcho`、`bdDTLSData::serialize/deserialize`、
`bdNATTravClient::receiveFrom/sendStage1/sendStage2/connect`、
`bdQoSProbe::sendRequest/handleReply`、`bdQoSReplyPacket::deserialize`。
服务端 `codol_network.c` 的注释直接引用了这些客户端函数的**具体 RVA**（如 `bdQoSProbe::sendRequest 0xa547a0`、`bdNATTravClient::receiveFrom 0xa60560`、`bdQoSProbe_start 0x4dd2a0`、`bdQoSProbe::pump 0xa56568`），说明作者是按早期 C1 的实机行为实现的服务端。

> 说明：以上 RVA 来自**服务端源码注释**（作者对 C1.exe 的静态定位），非本报告独立反汇编所得；本报告另在早期 C1 字符串表中独立确认了同名函数/类存在（`.rdata` 偏移见矩阵表）。两者互为佐证。

---

## 1. 传输层对应链（bdDTLS）

```
[客户端 C1.exe]                          [服务端 codol_dedrun.exe / codol_network.c]
bdNATTravClient::sendStage1  ──0x0D──▶   CODOL_NetworkReceive:366  (type 0x0D,29B)
                                          └─▶ 回显 type 0x0C (原样)
bdNATTravClient::receiveFrom ◀──0x0C──
bdDTLSAssociation::sendInit  ──0x01──▶   CODOL_NetworkReceive:380  (16B)
                                          └─ CODOL_HandshakeInit (codol_handshake.c:12)
bdDTLSAssociation::handleInitAck ◀─0x02── (38B INIT_ACK)
bdDTLSAssociation::sendCookieEcho ─0x03─▶ CODOL_NetworkReceive:411  (189B)
                                          └─ CODOL_HandshakeCookie (codol_handshake.c:40)
                                          └─ CODOL_SharedSecret(P-224) → CODOL_DeriveKey
bdDTLSAssociation::handleCookieAck ◀0x04─ (114B COOKIE_ACK)
bdDTLSAssociation::sendData  ──0x06──▶   CODOL_NetworkReceive:419  (DATA)
                                          └─ CODOL_AssociationOpenDetailed (codol_association.c:45)
                                          └─ MSG_InitReadOnly + SV_PacketEvent (:431)
bdDTLSAssociation::handleData ◀──0x06──  (服务端下行 DATA)
```

### 1.1 关键字段对应

| 项 | 客户端（C1.exe 证据） | 服务端（源码证据） | 一致性 |
|---|---|---|---|
| NAT 首字节 | 0x0D→0x0C（C# 抓包实录 + 字符串 `bdNATTravClient`） | `codol_network.c:366-372` | ✅ 一致 |
| INIT 长度/类型 | 16B，`01 02`（C# `CodolProtocol.cs:109-117`） | `codol_handshake.c:18-20` `n==16, packet[0]==1, packet[1]==2` | ✅ 一致 |
| INIT security id | `[8:16]` | `codol_handshake.c:20 memcmp(packet+8, id, 8)` | ✅ 一致 |
| INIT_ACK 长度 | 38B（C# `CookieLength=38`） | `codol_handshake.c:12 out[38]` | ✅ 一致 |
| COOKIE_ECHO 长度 | 189B（`docs/CODOL_ASSOCIATION.md`；C# 219B 见冲突） | `codol_handshake.c:47 n==189` | ⚠️ 见 §3 冲突 |
| COOKIE_ACK 长度 | 114B，`[0]=4,[1]=2` | `codol_handshake.c:45 ack[114]={4,2}` | ✅ 一致 |
| 公钥长度 | 100B（C# `PublicKeyLength=100`） | `codol_ecdh.c:47 out[100]` | ✅ 一致 |
| 曲线 | P-224（`codol_ecdh.c:58 SECP224R1`；C# 有 P224.cs） | `codol_ecdh.c:58` | ✅ 一致 |
| DATA 头 | 16B `06 02 tag(2) seq(2) mac8(8) len(2)` | `codol_crypto.c:87-95` | ✅ 一致 |
| DATA tag 校验值 | cookie `[14:16]`（serverTag） | `codol_association.c` 校验 `record[2:4]==local_tag`，local_tag=init_ack[16:18] | ✅ 一致 |
| 计数器 | u16 LE | `codol_crypto.c:89-90` u16 LE | ✅ 一致 |

### 1.2 密码学原语（**冲突保留**，见 §3）

- 服务端 `codol_crypto.c`：密钥派生 `Tiger192(x[28] || security[16])`→key24；keystream = `AES192-ECB(Tiger192(counter LE 4B))` 小端 CTR；MAC = `HMAC-SHA1(key24, header[6]+cipher)` 截 8B。
- 服务端源码注释（`codol_crypto.c:55`）：`mbedtls CTR increments big endian, whereas Demonware increments LE.`
- 现有 C# `Aes128.cs`/`CodolProtocol.cs`：`AES128` keystream + `HMAC-SHA1` 截 8；seed=`{seqLo,seqHi,0,0,tagLo,tagHi}`。
- `docs/CODOL_ASSOCIATION.md:24-27` 明确：alpha0022 `dtls_crypto.py` **导言里的 SHA1/AES128 说明已过时**，**活动实现用 Tiger192 + AES192**。

**判定**：DATA 记录**外层格式**两端一致（CONFIRMED）；**密钥派生/keystream 原语**两端文档冲突（服务端源码=AES192/Tiger192，现有 C#=AES128）。这是本阶段最重要的未决冲突，必须在实机验证前解决（详见 `EARLY_SERVER_03_PROTOCOL_GAPS.md` §2）。

---

## 2. 游戏层对应链（OOB + netchan + clc/svc）

### 2.1 Connectionless（OOB）

服务端 `SV_ConnectionlessPacket`（`sv_main.c:2328`）分发的命令，与客户端/现有项目证据对应：

| 命令 | 服务端处理 | 客户端证据 | 对应关系 |
|---|---|---|---|
| `getchallenge` | `sv_client.c:271-277 SV_GetChallenge` → `codol_connect.c:95` | C1 字符串 `"getchallenge 0 \"%s\""`@8678472、`"challengeResponse"`@8679184 | ✅ |
| `connect` | `sv_client.c:295 SV_DirectConnect` → `codol_connect.c:84` | C1 字符串 `"connectResponse"`@8679288 | ✅ |
| `stats` | `sv_main.c:2370 SV_ReceiveStats` | 无直接 C1 符号（stats 上传） | STRONG_CANDIDATE |
| `heartbeat` | `sv_main.c:2353`（需 `CODOL_NetworkAuthenticated`） | 无直接 C1 符号 | STRONG_CANDIDATE |
| `rcon` | `sv_main.c:2375`（+ `net_game.c:43` 环回直通） | N/A（运维/lobby） | ✅ |
| `getstatus`/`getinfo` | `sv_main.c:2342/2345` | C1 未发送（lobby `protocol_map.md:259` 记录未实现） | NOT_OBSERVED |
| `HostMigrationPacket` | `sv_main.c:2391` | 无 | CANDIDATE |
| `Source-Engine-Query` | `sv_main.c`（连接less 分支） | 无 | CANDIDATE |

**OOB 线格式**（CONFIRMED，`codol_connect.c:77-83 finish()`）：`4×0xFF` 前缀 + 文本 + 尾 `NUL`。这与 Path A 明文 `\xff\xff\xff\xff` 前缀一致，也与现有 C# `OobPrefix` 一致。

### 2.2 connect 响应的 protocol 值（**冲突保留**）

- 服务端出站：`codol_connect.c:91` 硬编码 `protocol\1\shortversion\1.1.1.13`，注释（`:89-90`）记录 **2026-09-02 实机二分：187 卡住客户端，1 能连**。
- 服务端**内部** codec 选择：`codol_wire.h:8 CODOL_PROTOCOL 187`；`sv_client.c:385 version=CODOL_PROTOCOL`。
- `docs/CODOL_ASSOCIATION.md:203-230`：dvar 2490 的 ROM 值 187 **不能**证明 connect-response 线值；实测 userinfo 只含数值 key 2490（值 -1157214325），无文本 protocol/shortversion。

**判定**：**内部 codec 187 ≠ 出站 connectResponse protocol 1**，两者被作者有意分开。二者都不是猜测——都有代码位置。此冲突按任务书要求保留。

### 2.3 netchan / 分片

- 服务端 `codol_netchan.c:8-49 CODOL_NetchanProcess`：server 头 6B（u32 seq|flags + u16 qport），client 头 4B；`ACK_BIT` 包直接丢弃；`sequence <= incomingSequence` 丢弃。
- `codol_wire.c:22-52 CODOL_WritePacket`：`len < 1162` 单包，否则 `FRAGMENT_BIT` + 6B 分片头 `{index,last,stride=1162,chunk}`。
- `codol_wire.c:97 CODOL_Xor`：对称 XOR（key ^= command[j] << (i&1)）。
- `codol_wire.c:110 CODOL_ExtendCounter`：16 位→32 位 epoch。

> **注意**：服务端 netchan 头是 **6B(server)/4B(client)**，而 lobby `protocol_map.md` B.2 实测的 **明文 body 头是 15B**（`sequence u32, qport u16, serverId u8, messageAck u32, reliableAck u32`）。这**不是同一层**：15B 是 IW4OL 风格 reliable 信封（Python 参考服/客户端 bdDTLS 内层），而 6B/4B 是 native CoD4x 移植的 CoDOL wire 头。两者并存，属于不同实现分支——见 GAPS §3。

### 2.4 客户端命令分发（**关键新发现**）

服务端 `sv_client.c:2412 SV_ExecuteClientMessage`：

- `:2415 static const char *clc_strings[256] = {"clc_move","clc_moveNoDelta","clc_clientCommand","clc_EOF","clc_nop","clc_sApiData"};`
- `:2505 c = MSG_ReadBits(&decompressMsg, 3);` → **3 位 opcode**
- `:2522 clc_move(0)` → `SV_UserMove(qtrue)`；`:2526 clc_moveNoDelta(1)` → `SV_UserMove(qfalse)`；`:2530 clc_clientCommand(2)` → `SV_ClientCommand`；`:2519 clc_EOF(3)` → return；`:2537 clc_nop(4)`。
- CODOL 分支（`:2422-2427`）**不做 Huffman 解压**（"Applying CoD4's Huffman decoder here destroys command framing"），直接 `MSG_WriteData` 拷贝。

对照 `net_game_conf.h:85-99 clc_ops_e`：`clc_move=0, clc_moveNoDelta=1, clc_clientCommand=2, clc_EOF=3, clc_nop=4, clc_download=5, clc_empty1/2, clc_steamcommands, clc_statscommands, clc_empty3/4, clc_acdata`。

> **任务书校正**：任务书提到的现有 CODOL `0x81/0x82/0x83` 消息只是线索。早期源码中 `0x81/0x82/0x83` 出现在 `scr_vm.h`（`OP_object`/`OP_thread_object`，GSC VM 操作码）等**无关位置**，**不可与网络 opcode 混淆**。早期版本的 clc opcode 是 **3 位字段**，与 `0x81` 系列不是同一编码空间。

### 2.5 服务端命令（svc）

- `sv_snapshot.c:61-62`（CODOL 分支）：`SV_WIRE_SERVERCOMMAND 1`、`SV_WIRE_EOF 5`；非 CODOL 分支 `= svc_serverCommand/svc_EOF`（`:65-66`）。
- `sv_snapshot.c:97-111 SV_UpdateServerCommandsToClient`：`{0x01, u32 cmdSeq, cstring}` × N，写在 snapshot 头之前。
- `sv_snapshot.c:759 SV_SendClientSnapshot` → `SV_BeginClientSnapshot(:774)` → `SV_WriteSnapshotToClient(:224)` → `SV_EndClientSnapshot(:827)`（写 `SV_WIRE_EOF`）。
- `net_game_conf.h:64-78 svc_ops_e`：`svc_nop=0, svc_gamestate=1, svc_configstring=2, svc_baseline=3, svc_serverCommand=4, svc_download=5, svc_snapshot=6, svc_EOF=7, ...`。

**冲突保留**：`sv_snapshot.c` 的 `SV_WIRE_SERVERCOMMAND=1/SV_WIRE_EOF=5` 与 `net_game_conf.h` 的 `svc_serverCommand=4/svc_EOF=7` **值不同**。CODOL 定制 wire 值（1/5）与引擎默认枚举（4/7）并存。lobby `protocol_map.md` B.3 实测 `svc_EOF=5`、`svc_serverCommand=1`，**与 CODOL 定制值一致**——这是对 CODOL wire 值的独立旁证。

---

## 3. 与现有项目（C# CODOL-Combat-Server-v0.1）的对应

现有 C# 是**从零实现**（README 明确"客户端从未连上本服（收包=0）"），其协议常量来自 `REF_LOBBY_KIT` 实机抓包。与早期 native 源码逐项对照：

| 项 | 现有 C# | 早期 native | 判定 |
|---|---|---|---|
| NAT 0x0D→0x0C 回显 | `CodolProtocol.cs:73-90` | `codol_network.c:366-372` | ✅ 完全一致 |
| INIT 16B `01 02` | `:109-117` | `codol_handshake.c:18-20` | ✅ |
| INIT_ACK 38B | `:120-130` | `codol_handshake.c:30-36` | ✅ |
| COOKIE_ECHO 长度 | **219B**（`:35 KeyExchangeLength=219`，cookie@6，u64@111，公钥@119） | **189B**（`codol_handshake.c:47`，cookie@6，u64@81，公钥@89） | ⚠️ **冲突** |
| COOKIE_ACK 114B | `:175-185` | `codol_handshake.c:45-59` | ✅ |
| DATA 头 16B `06 02` | `:192-244` | `codol_crypto.c:87-95` | ✅ |
| HMAC 输入 | `pkt[0:6]+pkt[14:]`（`:201-204`） | `header[6]+cipher`（`codol_crypto.c:71-75`，cipher 即 `record+16`，等价 `pkt[14:]`） | ✅ |
| keystream 原语 | **AES128** + SHA1 seed | **AES192** + Tiger192 IV | ⚠️ **冲突** |
| 公钥曲线 | P-224（`P224.cs`） | P-224（`codol_ecdh.c:58`） | ✅ |
| 公钥编码 | 100B libtomcrypt | 100B libtomcrypt（`codol_ecdh.c:47-72`） | ✅ |

**两个冲突必须解决**（详见 GAPS）：
1. **COOKIE_ECHO 长度 189 vs 219**：native `codol_handshake.c:47` 硬性要求 `n==189`，而 C# 用 219。两者必有一方对早期 C1 的实测有误，或对应**不同 C1 构建**。
2. **keystream 原语 AES192/Tiger192 vs AES128/SHA1**：native 源码注释明确"导言过时、活动实现是 Tiger192+AES192"。

> 说明：C# 注释声称常量来自**实机抓包**；native 源码是**对早期 C1 的实现**并做了**合成对等体测试**（`docs/CODOL_ASSOCIATION.md`，2026-09-08）。两者都声称贴近真实 C1，但**均未与真实 C1 完成端到端战斗**。按任务书要求，本报告保留冲突，不强行统一。

---

## 4. 客户端—服务端证据等级汇总

| 协议项 | 客户端证据 | 服务端证据 | 等级 |
|---|---|---|---|
| NAT 遍历 | C1 类名 + C# 抓包 | 源码函数 | CONFIRMED |
| QoS 探针 | C1 类名 + 源码注释 RVA | 源码函数 | CONFIRMED（服务端侧） |
| DTLS INIT/ACK | C1 类名 + C# | 源码函数 | CONFIRMED |
| COOKIE_ECHO/ACK | C1 类名 + 静态 serializer 地址 | 源码函数 | CONFIRMED（格式） |
| DATA 记录外层 | C1 类名 + C# | 源码函数 | CONFIRMED（格式） |
| DATA 密码学原语 | 无独立客户端确认 | 源码函数 | **冲突待验证** |
| getchallenge/connect | C1 字符串表（独立确认） | 源码函数 | CONFIRMED |
| connect protocol 值 | 无（opaque） | 源码 + 实机注释 | **冲突保留** |
| netchan 头 | 无直接符号 | 源码函数 | STRONG_CANDIDATE |
| clc 分发器 | 无生产端证据 | 源码函数 | CONFIRMED（服务端侧） |
| svc 值 | lobby 实测旁证 | 源码函数 | CONFIRMED / STRONG_CANDIDATE |
| gamestate/snapshot | 无 | 源码（作者自述未完成） | CANDIDATE |

---

## 5. 覆盖范围与未覆盖

**已覆盖（本阶段）**：`dedicated/src/codol/net/` 全部 10 个源文件 + 头文件；`sv_client.c`/`sv_main.c`/`sv_snapshot.c`/`net_game.c`/`net_game_conf.h` 的相关函数；`lobby/docs/protocol_map.md` PART B；`docs/CODOL_ASSOCIATION.md`；现有 C# `CodolProtocol.cs`/`Aes128.cs`。

**未覆盖 / 受阻**：
- 未运行任何服务端或客户端（按任务约束）。
- 未反汇编 `codoMP_client_shipRetail.exe` 的函数体（仅字符串表/类名）；客户端 opcode 生产端、字段布局、状态机**未从客户端侧确认**。
- `lobby/game-server.py`（Python 参考战斗服）**已退役**（`lobby/README.md`），源码不在本包内，无法逐行核对 189/219 与 AES 原语。
- 真实 C1 端到端握手/战斗 **UNKNOWN**（作者自述亦未验证）。

详见 `EARLY_SERVER_03_PROTOCOL_GAPS.md`。
