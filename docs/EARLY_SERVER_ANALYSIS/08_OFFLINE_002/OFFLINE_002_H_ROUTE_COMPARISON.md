# OFFLINE_002 — H：三条路线对比（序列化器 / 协议基线）

> 任务：`EARLY-SERVER-OFFLINE-VALIDATION-002` §5/§6。回答"gamestate/configstrings/snapshot 中哪一部分可以直接复用、按哪条路线复用"。
> 输入：只读。派生脚本/证据仅写 `08_OFFLINE_002\`；不启动服务端/客户端，不执行 `.cmd`，不修改样本/既有报告。
> 状态词：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / REFUTED / NOT_OBSERVED / INSTRUMENTATION_BLOCKED。
> 说明：本报告**只对比既有实现与既有证据**，不凭函数名或传统 CoD 架构相似性断言兼容。

---

## H.0 一句话结论

- 存在**三条互相独立、尚未证明互通**的战斗序列化路线：
  - **路线 A（原生早期服务端 CoDOL 序列化器）**：源码级完整、自洽（D 报告），但其**线值 opcode 与 `svc_ops_e` 枚举不一致**，且**从未与真实客户端逐字节比对**。
  - **路线 B（现有 C# Combat Server v0.1 参考实现）**：`MotionSnapshot` 自述**逐行移植自 Python REF `battle_server.py`**，与路线 A **不是同一实现**；`SelfTest.cs:1067` 期望 game state = **263B**，与原生 CoDOL gamestate 布局无关。
  - **路线 C（真实客户端解码期望）**：仅**字符串级存在性**（E 报告），VMProtect 加壳 → **INSTRUMENTATION_BLOCKED**。
- **本轮新增关键旁证**：`lobby\docs\protocol_map.md` 记录了 REF（Python）参考服与**真实客户端 `console_mp.log`** 的交互实测——`svc_gamestate=2`、`configstring=3`、`svc_EOF=5`、`svc_serverCommand=1`（`protocol_map.md:330-333`）。这与**原生服务端线值（2/3/5/1）逐值吻合**，为路线 A 的 opcode 空间提供了**独立于原生源码**的旁证；但 `svc_snapshot` 仍标注 "still unknown"（`:334`）。
- **可复用判断**：**没有一条路线达到"可直接复用"（CONFIRMED 级）**。路线 A 的服务端编码器**源码自洽 = CONFIRMED**，**可复用性 = CANDIDATE**（缺客户端逐字节验证）；路线 B 与客户端互通 = **NOT_OBSERVED**。

---

## H.1 三条路线的定位与证据来源

| 路线 | 主体 | 源码/样本位置 | 本报告依据 |
|---|---|---|---|
| **A** | 原生早期服务端 CoDOL 序列化器（C） | `CODOL_Server\dedicated\src\codol\snapshot\*` + `sv_client.c`/`sv_main.c`/`sv_snapshot.c` | `OFFLINE_002_D_SERIALIZER_SERVER_MAP.md` |
| **B** | 现有 C# Combat Server v0.1（C#，自实现） | `CODOL-Combat-Server-v0.1\src\Codol\MotionSnapshot.cs` + `Engine\ClientLogic.cs`/`GameWorld.cs` | 本报告 H.3；`OFFLINE_002_G` BLK-5 |
| **C** | 真实客户端解码期望（`codoMP_client_shipRetail.exe`） | 客户端 EXE 字符串 + 引用点 RVA | `OFFLINE_002_E_SERIALIZER_CLIENT_MAP.md` |
| （旁证） | REF（Python）参考服 + 真实客户端实测 | `CODOL_Server\lobby\docs\protocol_map.md` + `console_mp.log` | 本报告 H.4 |

> 路线 B 的 `MotionSnapshot.cs:3` 自述："逐行移植自 `REF_LOBBY_KIT/battle_server.py::_BitWriter / _build_motion_snapshot`"。故 B 的**上游**是 Python REF，而非路线 A 的 C 实现——**B 与 A 非同源**。

---

## H.2 路线 A（原生 CoDOL）序列化器结构（摘要，详见 D 报告）

| 段 | 编码入口 | 线值/布局 | 等级 |
|---|---|---|---|
| gamestate | `sv_main.c:3939 SV_WriteGameState` → `codol_sv_state.c:119` → `codol_configstrings.c:288` | `0x02` + u32 seq + cstr map + cstr zone + u32 crc + configstrings 子流 + u32 clientNum + u32 checksumFeed + `0x05` | **CONFIRMED（源码级）** |
| configstrings | `codol_configstrings.c:269` | `0x03` + u16 count + `{1bit,13bit,cstr}*` + `0x05` | **CONFIRMED（源码级）** |
| snapshot | `sv_snapshot.c:224 SV_WriteSnapshotToClient` → `codol_sv_snapshot.c:241` → `codol_snapshot.c:8` | `0x00` + u32 serverTime + u8 delta + u8 flags + 1bit base + 6 段 + `0x05` | **CONFIRMED（源码级）** |
| 差分 codec | `codol_delta.c:9-61` | compressed / angle(×182.04444885253906, u16) / integer / trimmed / ReachDeltaValue | **STRONG_CANDIDATE**（`codol_delta.c:1` 自述 "C1.exe sub_5A0510 codecs"） |
| 位流 | `codol_msg.c:67-92` + `codol_msg.h:9-13` | 位池字节在字节游标处预留；整字节字段**永不**对齐/重置位池；LE 整数 | **CONFIRMED** |
| 出网 | `sv_snapshot.c:642 SV_SendMessageToClient` → `:688 SV_Netchan_Transmit` | 无整包 Huffman（`sv_snapshot.c:63-67` 宏未定义） | **CONFIRMED** |

---

## H.3 路线 B（现有 C# 参考）结构与 A 的差异

| 维度 | 路线 A（原生 CoDOL） | 路线 B（C# v0.1） | 证据 |
|---|---|---|---|
| gamestate 来源 | `CODOL_WriteServerGamestate`（引擎 configstring 池） | `GameWorld.GameState`（`.bin` 或 `BuildMinimalGameState`） | `GameWorld.cs:147/164/180` |
| gamestate 长度 | 由 configstring 池决定（非定长） | `SelfTest.cs:1067` 期望 **263B**；`PumpGameState` 限 16..1100B | `ClientLogic.cs:411`；`SelfTest.cs:1067` |
| gamestate 传输 | netchan body（外层分片/XOR） | 4B seq + state，`i>=8` 逐字节 XOR mask `(seq^1)&0xFF` | `ClientLogic.cs:418-426` |
| snapshot 字段序 | 6 段（player/anim/actors/entities/clients/glass） | 单段 29 字段索引序 `0,1,3,8,10,11,13,14,17,18,19,20,21,22,23,24,29,34,38,39,41,44,54,56,60,61,63,68,84` | `codol_snapshot.c:28-40` vs `MotionSnapshot.cs:222-227` |
| 位流模型 | 位池预留 + 整字节不对齐 | `BitWriter.Bytes()` 把原始字节**追加到末尾**、位指针不动，位流与原始字段**交错** | `codol_msg.c:1-3` vs `MotionSnapshot.cs:5-13` |
| 差分/压缩 | `codol_delta.c` 族（C1 sub_5A0510） | `BitWriter.Index`（1bit "紧跟" / 1bit+4bit 步长链） | `MotionSnapshot.cs:47-56` |
| 上游来源 | 引擎 + CoDOL 移植 | 自述移植自 Python REF `battle_server.py` | `MotionSnapshot.cs:3` |

**判定（CONFIRMED）**：路线 A 与路线 B 的**gamestate 长度模型、snapshot 段布局、位流模型**均不同 → **不是同一序列化器**。**二者未证明互通（NOT_OBSERVED）**。**不得**用 B 替代 A 的验证。

---

## H.4 opcode 线值交叉核对（本轮新增，价值最高）

**旁证来源**：`CODOL_Server\lobby\docs\protocol_map.md`（SHA-256 `A0759286DC7852D91FEBACF05E9F57ED11FB101D80BF3E56478075885FB04FE2`，728 行）。该文档自述其证据为 `dw-capture.log` / `gs*.log` / **`console_mp.log`（"the client's own verdict on our replies"）** / `C1.exe`。

| 线值 | 原生 CoDOL 写点（路线 A） | REF 实测（protocol_map.md） | 一致性 |
|---|---|---|---|
| `svc_gamestate` | `0x02`（`codol_configstrings.c:298`） | `2`（`:330`，live `probe="play"` 路径） | **吻合** |
| configstring 块 | `0x03`（`codol_configstrings.c:276`） | `3`（`:331`，`CODOL_CS_OP`） | **吻合** |
| 块终止 / `svc_EOF` | `0x05`（`codol_configstrings.c:284/306`、`codol_snapshot.c:41`、`sv_snapshot.c:62`） | `5`（`:332`，"MEASURED at 0x005D82BB/0x005D8354；was 6"） | **吻合** |
| `svc_serverCommand` | `0x01`（`sv_snapshot.c:61 SV_WIRE_SERVERCOMMAND 1`） | `1`（`:333`，"emitted before the snapshot header"） | **吻合** |
| `svc_snapshot` | `0x00`（`codol_snapshot.c:23`） | **"still unknown"**（`:334`，`CODOL_SNAP_OP` 未定） | **未闭合** |

- **结论（STRONG_CANDIDATE）**：原生路线 A 的 **gamestate=2 / configstring=3 / EOF=5 / serverCommand=1** 四个线值，被 REF（Python）与**真实客户端**的实测独立旁证——这解释了 D 报告 §D.6 的"线值 vs `svc_ops_e` 枚举"冲突：**客户端接受的是 CODOL 自定义 opcode 空间（2/3/5/1），而非引擎 `svc_ops_e` 枚举（1/2/7/4）**。
- **仍未闭合（UNKNOWN）**：**snapshot opcode**。原生写 `0x00`，REF 实测**未确定**（`:334`），故 `0x00` 只是**候选**，**不得**据此断言客户端接受。
  - **注**：`codol_snapshot.c:22` 注释把该字节称为 "section byte header"，其**是否同时充当外层 svc opcode** 需以客户端 svc 分派表或带载荷抓包确认（受 E 报告 BLK-2/BLK-4 约束）。
- **证据边界**：REF 旁证来自**另一份实现（Python）**的实测，**不等于**原生 C 实现的产出被客户端接受；两条路线的 **snapshot 段编码本身仍不同**（H.3）。opcode 层吻合**不**蕴含 payload 层兼容。

---

## H.5 逐段"可否直接复用"判断

| 段 | 路线 A（原生 CoDOL） | 路线 B（C# v0.1） | 判断依据 |
|---|---|---|---|
| gamestate 外层 opcode（2） | **CANDIDATE** | N/A（B 用不同外层） | REF 旁证吻合，但原生产出未与客户端比对 |
| configstrings 位布局（1+13bit+cstr） | **CANDIDATE** | N/A | 与 `protocol_map.md:331` 结构描述**一致**，但字节级未比对 |
| gamestate 字段序 | **CONFIRMED（源码级）** | **NOT_OBSERVED** | 原生 `codol_configstrings.c:299-306`；B 的 263B 模型无关 |
| snapshot opcode（0） | **CANDIDATE** | N/A | 与 REF `:334` "unknown" 不矛盾，但未确认 |
| snapshot 6 段布局 | **CONFIRMED（源码级）** | 与 A 不同 | `codol_snapshot.c:28-40`；B 为单段 29 字段 |
| 差分 codec | **STRONG_CANDIDATE** | 不同实现 | `codol_delta.c:1` 自述 C1 sub_5A0510 |
| 位流引擎 | **CONFIRMED（源码级）** | 不同实现 | `codol_msg.c:1-3` vs `MotionSnapshot.cs:5-13` |
| 出网（分片/XOR） | **CONFIRMED（源码级）** | 不同外层 | `codol_wire.c:22-95`；B 用 4B seq + XOR mask |
| 客户端可解析性 | **NOT_OBSERVED** | **NOT_OBSERVED** | 无带载荷抓包 |

**总判定**：路线 A 的**服务端编码器源码自洽 = CONFIRMED**；**面向真实客户端的可复用性 = CANDIDATE**（顶层 opcode 有旁证，payload 段无旁证）。**没有任何一段达到"可直接复用"**。

---

## H.6 对序列化器移植优先级的影响（承接 OFFLINE_001 最终裁决）

`OFFLINE_001_FINAL_DECISION.md` 已裁定：**实现基线切换为 219B 长地址 + SHA1/AES128**；258B 记录采用 **37B 短地址**；原生 **Tiger192/AES192 降为"仅参考"**。本轮复核**维持**该裁决，并补充：

1. **传输层（AES/SHA1/219B）与序列化器是两条独立轴**：H.4 的 opcode 旁证**不依赖**密码学原语裁决 → 即便原语仍待实机复算，opcode 结论已可用。
2. **优先级变化**：
   - **P0（不变）**：先闭合 **snapshot opcode**（原生 `0x00` vs REF unknown）与 **snapshot 段 payload** —— 这是"进战斗"的真正闸门（`04_BLOCKERS.md` K1）。
   - **P1（新增旁证支持）**：gamestate/configstring 的 **2/3/5/1 opcode 空间**已有客户端实测旁证，**移植信心提升**，但仍需一份带载荷抓包做字节级比对。
   - **参考降级**：原生 `Tiger192/AES192` 路径**不作为主路径**（承 001）；**C# `MotionSnapshot` 亦不得**作为路线 A 的验证替身（H.3）。
3. **不建议**：以 C# 263B gamestate 或 C# 单段 29 字段 snapshot 直接对接客户端——与原生 CoDOL 结构**不同**且**未互通**。

---

## H.7 证据等级汇总

| 断言 | 等级 | 依据 |
|---|---|---|
| 路线 A（原生）gamestate/configstrings/snapshot 编码路径存在且源码自洽 | **CONFIRMED** | `codol_sv_state.c:119` / `codol_configstrings.c:269/288` / `codol_snapshot.c:8` |
| 路线 A 线值 2/3/5/1 被 REF + 真实客户端实测旁证 | **STRONG_CANDIDATE** | `protocol_map.md:330-333`（`console_mp.log` 判据） |
| 路线 A snapshot opcode = `0x00` 被客户端接受 | **UNKNOWN** | REF `:334` "still unknown" |
| 路线 A 与路线 B 不是同一序列化器 | **CONFIRMED** | gamestate 长度模型 + snapshot 段布局 + 位流模型均不同 |
| 路线 B（C#）与真实客户端互通 | **NOT_OBSERVED** | `MotionSnapshot.cs:3` 自述移植自 Python REF；无联调 |
| 路线 A 的 gamestate/configstrings 可直接复用 | **CANDIDATE** | opcode 有旁证，payload 无字节级比对 |
| 客户端可解析任一路线产出 | **NOT_OBSERVED** | 无带载荷下行抓包（`wiretap_report.md:185`） |
| 客户端解码入口语义 | **INSTRUMENTATION_BLOCKED** | VMProtect（E 报告） |

---

## H.8 复算/核对命令（只读）

```
# 原生写点
$root='D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\dedicated\src'
Get-Content -LiteralPath "$root\codol\snapshot\codol_snapshot.c"       | Select-Object -First 46
Get-Content -LiteralPath "$root\codol\snapshot\codol_configstrings.c" | Select-Object -Skip 265 -First 45
# 旁证
Get-Content -LiteralPath '...\CODOL_Server\lobby\docs\protocol_map.md' | Select-Object -Skip 326 -First 12
# 路线 B
Get-Content -LiteralPath '...\CODOL-Combat-Server-v0.1\src\Codol\MotionSnapshot.cs' | Select-Object -First 60
```
