# 阶段 3 — 协议缺口与冲突（EARLY_SERVER_03_PROTOCOL_GAPS）

本文件只列**尚未闭合**的协议项与**未强行统一的冲突证据**。每条给出：现象、双方证据、影响、闭合所需的最小验证。
证据等级沿用任务书术语。**未观察 ≠ 不存在。**

---

## 1. 已确认无缺口（对照基线）

以下项两端一致，**不**构成缺口，列出以便界定"已闭合"边界：

- NAT 遍历 type 0x0D→0x0C（29B 原样回显）。
- bdDTLS INIT 16B `01 02` / INIT_ACK 38B。
- COOKIE_ACK 114B `04 02`，服务端公钥 100B @[6:106]。
- DATA 记录外层 16B 头 `06 02 tag(2) counter(2) mac8(8) len(2)`。
- 公钥曲线 P-224、编码 100B libtomcrypt。
- OOB 线格式 `4×0xFF + text + NUL`。
- `getchallenge` / `connect` 命令名与响应文本前缀。
- clc 3 位 opcode 分发器（服务端侧 CONFIRMED）。
- CODOL wire 值 `svc_serverCommand=1` / `svc_EOF=5`（有 lobby 实测旁证）。

---

## 2. 冲突 A — DATA 密码学原语：AES192/Tiger192 vs AES128/SHA1

| | 早期 native 源码 | 现有 C# 实现 |
|---|---|---|
| 密钥派生 | `Tiger192(x[28]‖security[16])`→key24（`codol_crypto.c:28-37`） | 直接用 transportKey24 前 16B 作 AES128 key（`Aes128.cs` 调用点 `CodolProtocol.cs:213-215`） |
| keystream | `AES192-ECB(Tiger192(counter LE 4B))`，小端 CTR（`codol_crypto.c:39-63`） | `AES128(ECB)`，seed=`{seqLo,seqHi,0,0,tagLo,tagHi}` 经 SHA1 作计数器（`CodolProtocol.cs:241-244`） |
| MAC | `HMAC-SHA1(key24, header[6]‖cipher)` 截 8B（`codol_crypto.c:65-78`） | 同（`CodolProtocol.cs:201-208`） |
| 作者自述 | `docs/CODOL_ASSOCIATION.md:24-27`："alpha0022 `dtls_crypto.py` 导言的 SHA1/AES128 说明已过时，活动实现用 Tiger192+AES192" | `Aes128.cs:1-5`："依据 REF_LOBBY_KIT/battle_server.py::_keystream_xor / codol_crypto.py" |

**影响**：若原生原语正确，现有 C# 的 DATA 解密在真实 C1 上会**全部 MAC 失败**——这与 C# README"收包=0"的症状一致，是可能的根因之一（**CANDIDATE，未验证**）。

**闭合所需最小验证**（隔离环境，需批准）：
1. 用同一 (shared_x, securityKey, counter, plaintext) 分别跑 native `CODOL_EncryptRecord` 与 C# `BuildData`，比对密文与 MAC。
2. 对 `lobby` 保留的 `captures\*.jsonl` 或 `re/alpha0022/dtls_capture.txt`（若随包存在）做**离线** MAC 复算：先试 AES192/Tiger192，再试 AES128/SHA1，看哪种能验通一条真实记录。
3. 不启动服务端、不连真实客户端。

**当前判定**：CONFLICT（保留）。倾向原生（有作者明确注释 + 合成对等体测试），但**未独立验证**。

---

## 3. 冲突 B — COOKIE_ECHO 长度 189B vs 219B

| | 早期 native | 现有 C# |
|---|---|---|
| 长度 | 硬性 `n==189`（`codol_handshake.c:47`） | `KeyExchangeLength=219`（`CodolProtocol.cs:35`） |
| 布局 | outer[6] + init_ack[38]@6 + common addr[37] + security id[8] + pubkey[100]@89 | type[2] + cookie[38]@6 + … + u64 1@111 + pubkey[100]@119 |

`docs/CODOL_ASSOCIATION.md`（212 行）独立复算：`COOKIE_ECHO = outer header[6] + 完整 INIT_ACK[38] + common address[37] + security ID[8] + public key[100] = 189B`，并给出 alpha0022 offsets 81/89。这与 native `codol_handshake.c:54`（校验 `packet+81`==init[8:16]，`packet+89`=公钥）**自洽**。

C# 的 219B 多出 30B，且其"公钥@119、u64@111"布局与 native 的"公钥@89、id@106"不一致。

**影响**：若 native 正确，现有 C# 的 `TryBuildInitAck`/cookie 解析对真实 C1 **不匹配**；反之亦然。二者对应的 C1 构建可能不同。

**闭合所需最小验证**：离线复算 `re/alpha0022/dtls_capture.txt`（若存在）第 2 行 COOKIE_ECHO 的真实长度与字段偏移；或对早期 `codoMP_client_shipRetail.exe` 的 `bdDTLSCookieEcho` serializer（`docs` 记为 0xa62220/header 0xa6223a）做**静态**反汇编确认写入字节数。

**当前判定**：CONFLICT（保留）。native 有独立自洽复算，证据略强。

---

## 4. 冲突 C — 内部 codec 187 vs connectResponse protocol 1

| | 值 | 位置 |
|---|---|---|
| 内部 codec 选择 | 187 | `codol_wire.h:8 CODOL_PROTOCOL`；`sv_client.c:385 version=CODOL_PROTOCOL` |
| 出站 connectResponse | 1 | `codol_connect.c:91` 硬编码；注释 `:89-90` 记录 2026-09-02 实机二分 |

`docs/CODOL_ASSOCIATION.md:203-230` 澄清：dvar 2490 的 ROM 值 187 **不能**证明线值；实测 userinfo 只含数值 key 2490（-1157214325），无文本 protocol。

**影响**：这是**设计上的分离**，不是 bug。但意味着"协议版本 = 187"的说法**不成立于 connectResponse**。任何以 187 作为出站 protocol 的实现都可能卡住客户端（作者实测）。

**闭合所需最小验证**：已在服务端侧由作者实机二分闭合（187 卡住 / 1 能连）；剩余未知是**数值 key 2490 的编码含义**。

**当前判定**：冲突已解释，保留记录。**未知**：2490 的编码。

---

## 5. 缺口 D — svc 值双轨：CODOL 定制(1/5) vs 引擎默认(4/7)

- `sv_snapshot.c:61-62`（CODOL 分支）：`SV_WIRE_SERVERCOMMAND 1`、`SV_WIRE_EOF 5`。
- `net_game_conf.h:64-78`（引擎枚举）：`svc_serverCommand=4`、`svc_EOF=7`。
- lobby `protocol_map.md` B.3 实测 `svc_EOF=5`、`svc_serverCommand=1`。

**判定**：CODOL 定制值经 lobby 独立实测旁证（STRONG_CANDIDATE），引擎枚举值在 CODOL 路径上**不使用**。非真缺口，但必须**明确采用 1/5**，否则复现 B.3 记录的 "SVC-EOF-6" 类错误（一个字节错就丢弃整个 snapshot）。

**未闭合**：`svc_snapshot` 的确切 opcode 仍**未知**（lobby `protocol_map.md:334`：由 `CODOL_SNAP_OP` 固定或 `CODOL_SNAP_LO..HI` 扫描）。

---

## 6. 缺口 E — 服务端下行 gamestate/snapshot 序列化未完成

- `sv_snapshot.c:224 SV_WriteSnapshotToClient` 在 CODOL 分支改用 `CODOL_ClientNativeFrame`/`CODOL_BuildGameplayFrame`，但 `docs/CODOL_PORT.md` 第 3537 行 "Required before a client can play" 第 4 项明确：**configstrings/snapshots 仍用 IW3 序列化器**（6519 configstrings，武器从 5362 起）。
- `docs/CODOL_ASSOCIATION.md`：合成加密对等体可推进到 `CS_PRIMED` 并收到**重组后的加密 gamestate**，但**真实 C1 未验证**。

**判定**：CANDIDATE（未完成）。这是"能否进战斗"的核心缺口，非协议格式问题，而是**序列化器未移植**。

**闭合所需最小验证**：需要真实 C1 或高保真客户端回放（现有项目有 `CodolClientReplay.cs`/`SessionGolden.cs` 可作离线对照）。

---

## 7. 缺口 F — 客户端侧 opcode 生产端未确认

- 服务端 clc 分发器 CONFIRMED（3 位 opcode）。
- **但客户端发送端**未从 `codoMP_client_shipRetail.exe` 反汇编确认；lobby `protocol_map.md` B.2 实测 Python 参考服**没有 clc 分发器**，只用 1 字节滑动窗口扫描，`clc_move`(0x06) 仅"被识别"。

**判定**：STRONG_CANDIDATE。服务端读 3 位，客户端是否写 3 位、以及各字段布局，**未独立确认**。

**闭合所需最小验证**：对 C1.exe `SV_ExecuteClientMessage` 对应发送侧（客户端 `CL_SendCmd`/usercmd 序列化）做静态反汇编；或对已有 `captures\*.jsonl` 的 `clc_cmd`/`clc_packet` 事件做离线字段对齐。

---

## 8. 缺口 G — 任务书 0x81/0x82/0x83 线索的处置

任务书 §六 提到"现有 CODOL 的 `0x81/0x82/0x83` 消息已有部分客户端侧证据"，并明确"不能预设早期版本使用相同操作码或相同格式"。

**早期源码核对结果**：
- `scr_vm.h` 中 `0x81/0x82/0x83` 是 **GSC VM 操作码**（`OP_object`/`OP_thread_object` 等），**与网络层无关**。
- 早期网络层 clc opcode 是 **3 位字段**（值 0-5，见 §2.4 of CORRELATION），svc 是**单字节**（值 0-12）。
- 因此 `0x81/0x82/0x83` **不能**映射到早期版本的 clc/svc。

**判定**：REFUTED（作为早期网络 opcode）。保留为**现有版本**的独立调查线索。

---

## 9. 缺口 H — lobby ↔ 战斗服契约的边界

`lobby/README.md` + `codol_admission.h:7-19` 给出**明确接口边界**：

- lobby 写 `resources/mpdata_s.<uid>`、`startgame.txt`、`game_admissions.txt`、`native_server_rcon.txt`。
- 战斗服读名册行 `<ipv4> <key:32hex> <uid:16hex|0> <expires:unix> <gamertag>`；**key 即凭据**。
- lobby 每实例轮询战斗服 `sh1x_status`（`codol_match_status.c:38-61`）。
- 战斗服经 RCON（`native_server_rcon.txt` 口令）接受 `map` 等命令。

**判定**：CONFIRMED（契约文本 + 代码双证据）。这是早期服务端**最有复用价值**的部分之一——边界清晰、语言无关（文本文件 + 明文 RCON + 文本状态行）。

**未闭合**：`startgame.txt`/`mpdata_s.<uid>` 的**完整字段语义**（仅观测到部分字段）。

---

## 10. 缺口 I — 超时/重连/断开

- 连接状态机 CONFIRMED（`server.h:61-66` CS_FREE→ZOMBIE→CONNECTED→PRIMED→ACTIVE；`sv_client.c:750/2272-2273/1631-1632`）。
- 服务端有 `EXE_ERR_SERVER_TIMEOUT`、`EXE_ERR_NOT_AUTHORIZED` 出站（`sv_client.c:352/358`）。
- **客户端侧**心跳/超时/重连逻辑未确认；`stats`/`heartbeat` 的客户端发送条件 STRONG_CANDIDATE。

**判定**：部分 CONFIRMED（服务端），客户端侧 UNKNOWN。

---

## 11. 缺口汇总表

| # | 缺口/冲突 | 等级 | 阻塞"进战斗" | 最小验证 |
|---|---|---|---|---|
| A | AES192/Tiger192 vs AES128/SHA1 | CONFLICT | 是（若 C# 错） | 离线 MAC 复算 |
| B | COOKIE_ECHO 189 vs 219 | CONFLICT | 是 | 离线字段/长度确认 |
| C | 187 vs 1 (connectResponse) | 已解释 | 否 | 2490 编码 |
| D | svc 1/5 vs 4/7 | 非缺口 | 否（须用 1/5） | svc_snapshot opcode |
| E | gamestate/snapshot 序列化 | CANDIDATE | **是** | 真实 C1 / 回放 |
| F | 客户端 clc 生产端 | STRONG_CANDIDATE | 否 | C1 反汇编 |
| G | 0x81/0x82/0x83 | REFUTED | 否 | — |
| H | lobby↔战斗服契约 | CONFIRMED | 否 | 字段语义补全 |
| I | 超时/重连 | 部分 CONFIRMED | 否 | 客户端反汇编 |

---

## 12. 未观察 ≠ 不存在

- `getstatus`/`getinfo`/`getKeyAuthorize`/`echo`/`print`：早期客户端**未观测**发送；服务端**有** `getstatus`/`getinfo` 处理分支（`sv_main.c:2342/2345`）。不得据此断言客户端不使用。
- `svc_download`/`svc_nop`：lobby 参考服未实现；native 枚举存在（`net_game_conf.h:70/65`）。未观察。
- 加密 UDP（STUN）之外的 TCP 3074 lobby 通道：本阶段只覆盖战斗服 UDP 17733；lobby TCP 侧见 `protocol_map.md` PART A。
- 反调试/反作弊（XAC/TenProtect）：`SV_TryLoadXAC` 存在（`sv_main.c`），本报告**不做**任何绕过分析（任务约束）。
