# OFFLINE_002 — 协议基线（当前已确认 / 仍未知）

> 任务：`EARLY-SERVER-OFFLINE-VALIDATION-002` §6（回答 §7 问题 1）。整合六阶段报告与本轮 `OFFLINE_002` A–H。
> 输入：只读。派生脚本/证据仅写 `08_OFFLINE_002\`；不启动服务端/客户端，不执行 `.cmd`，不修改样本/既有报告。
> 状态词：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / REFUTED / NOT_OBSERVED / INSTRUMENTATION_BLOCKED。
> 说明：本文件只登记**协议基线**（哪些已确认、哪些未知）；逐条证据以各分册为准，不重复展开。

---

## P.0 一句话结论

- **契约/明文层（握手、OOB、NAT/QoS、INIT/COOKIE/DATA 外层、serverCommand/EOF）已确认**；本轮**新增**确认 **CODOL 自定义 svc opcode 空间（2/3/5/1）** 有 REF + 真实客户端实测旁证。
- **两个硬未知**：① **snapshot opcode**（原生写 `0x00`，REF 实测 "still unknown"）；② **客户端 svc 分派表 / 解码入口**（VMProtect 加壳，INSTRUMENTATION_BLOCKED）。
- **会话描述符编号歧义已裁决**（field#15 ≠ field#19，两套独立结构，CONFIRMED）。
- **真实会话 8B MAC 逐字节复算**仍 INSTRUMENTATION_BLOCKED（缺完整 24B key / ECDH 私钥）。

---

## P.1 已确认（CONFIRMED / STRONG_CANDIDATE）——承六阶段 + 本轮

| # | 协议项 | 状态 | 证据 |
|---|---|---|---|
| 1 | bdNATTrav INTRO（0x0D→0x0C，29B） | **CONFIRMED** | `codol_network.c:366-372`；03 矩阵 |
| 2 | bdQoSProbe（0x28→0x29，18B/27B） | **CONFIRMED** | `codol_network.c:326-350`；03 矩阵 |
| 3 | getchallenge → challengeResponse（明文 OOB） | **CONFIRMED** | `sv_client.c:271-277`；`codol_connect.c:95-99` |
| 4 | connect → connectResponse（明文 OOB） | **CONFIRMED**（`protocol=1` 值需实机复验） | `sv_client.c:295`；`codol_connect.c:84-93` |
| 5 | bdDTLS INIT/INIT_ACK（0x01/0x02） | **CONFIRMED**（合成对等体；真实 C1 UNKNOWN） | `codol_handshake.c:12-39`；`codol_network.c:380-410` |
| 6 | bdDTLS COOKIE_ECHO/COOKIE_ACK（0x03/0x04） | **CONFIRMED**（记录格式）；本会话 219B = **STRONG_CANDIDATE** | `codol_handshake.c:40-66`；`battle_srv.log:2324` |
| 7 | bdDTLS DATA 记录外层（16B 头，type 0x06） | **CONFIRMED**（记录格式） | `codol_crypto.c:80-120`；`CodolProtocol.cs:192-244` |
| 8 | DATA MAC 构造 `HMAC-SHA1(key24, hdr[0:6]‖…)[:8]` | **CONFIRMED**（四实现构造）；C#/REF/ol-mod 输入 `pkt[0:6]‖pkt[14:]` **CONFIRMED** | `OFFLINE_002_A` A.1/A.5 |
| 9 | 观测会话原语 = SHA1 派生 + AES-128 | **STRONG_CANDIDATE** | `OFFLINE_002_A` A.1（三实现同族 + 行为链） |
| 10 | 原生 Tiger192/AES192 对观测客户端成立 | **REFUTED** | `codol_crypto.c:28-78` vs 219B 硬拒 |
| 11 | netchan 头 + 分片（server 6B / client 4B，stride 1162） | **STRONG_CANDIDATE** | `codol_netchan.c:8-49`；`codol_wire.c:22-95` |
| 12 | serverCommand 线值 `0x01`、EOF 线值 `0x05` | **CONFIRMED** | `sv_snapshot.c:61-62`；`protocol_map.md:332-333` |
| 13 | **CODOL 自定义 svc opcode 空间**：gamestate=2、configstring=3、EOF=5、serverCommand=1 | **STRONG_CANDIDATE**（新增） | `codol_configstrings.c:276/298` + `protocol_map.md:330-333`（`console_mp.log` 判据） |
| 14 | clc_* 客户端命令：服务端分发器（3-bit opcode） | **CONFIRMED**（服务端侧）；生产端 UNKNOWN | `sv_client.c:2505/2515`；03 矩阵 |
| 15 | sh1x_status 文本契约 | **CONFIRMED** | `codol_match_status.c:38-61` |
| 16 | loopback RCON（4x0xff 明文 OOB） | **CONFIRMED** | `net_game.c:43-53`；`sv_main.c:2375` |
| 17 | 会话描述符 258B = 33 字段；securityKey = field#15 @147/负载@153..168 | **CONFIRMED** | `OFFLINE_002_C`（`SessionDescriptor.cs:131-159` + 字节复算） |
| 18 | field#15（258B 记录）与 field#19（28 字段 pickle）是不同结构，非零基/一基冲突 | **CONFIRMED** | `OFFLINE_002_C` C.2 |
| 19 | pickle field19 == `securitykey.bin`（同 SHA-256） | **CONFIRMED** | `OFFLINE_002_C` C.1.2 |
| 20 | 服务端序列化器 gamestate/configstrings/snapshot 编码路径（源码级） | **CONFIRMED** | `OFFLINE_002_D` |

---

## P.2 仍未知 / 未观察（UNKNOWN / NOT_OBSERVED / INSTRUMENTATION_BLOCKED）

| # | 未决项 | 状态 | 缺失证据（最小闭合任务） |
|---|---|---|---|
| U-1 | **snapshot 线值 opcode** | **UNKNOWN** | 原生写 `0x00`（`codol_snapshot.c:23`）；REF 实测 "still unknown"（`protocol_map.md:334`）。需客户端 svc 分派表或带载荷抓包 |
| U-2 | **客户端 svc 分派表 / 解码入口语义** | **INSTRUMENTATION_BLOCKED** | VMProtect（`.vmp0` + `nsn`）；需动态调试或未加壳版本（`OFFLINE_002_E`） |
| U-3 | **客户端 `CS_PRIMED` 状态转换点** | **UNKNOWN** | 状态枚举常量无字符串（`OFFLINE_002_E` E.4） |
| U-4 | **clc_* 客户端生产端布局** | **UNKNOWN** | 客户端发送侧未反汇编（`04_BLOCKERS.md` K5） |
| U-5 | **真实会话 8B MAC / keystream 逐字节复算** | **INSTRUMENTATION_BLOCKED** | 缺完整 24B transport key 或同期 ECDH 私钥/共享 X（`OFFLINE_002_A` A.1 问 5） |
| U-6 | **原生 `mac()` 第二段是否含 `[14:16]`** | **UNKNOWN** | 原生 `cipher` 调用点未闭合（`OFFLINE_002_A` A.2） |
| U-7 | **258B 记录 37B 短地址 vs COOKIE_ECHO 67B 长地址实机对应** | **NOT_OBSERVED** | 无实机对应证据（`OFFLINE_002_C` C.5） |
| U-8 | **目标运行时唯一 16B securityKey** | **UNKNOWN** | 258B 记录用 16×`0x01`，`securitykey.bin` 为另一值（`OFFLINE_002_C` C.4） |
| U-9 | **内部 codec 187 vs connectResponse protocol 1** | **冲突保留** | 内部选择 vs 出站线值；不强行统一（03 矩阵） |
| U-10 | **序列化器产出可被真实客户端解析** | **NOT_OBSERVED** | 无带完整载荷的下行抓包（`wiretap_report.md:185`） |
| U-11 | **C# 参考实现与客户端互通** | **NOT_OBSERVED** | `MotionSnapshot.cs:3` 自述移植自 Python REF；无联调（`OFFLINE_002_H`） |
| U-12 | **lobby→battle booking 帧格式 / DedicatedControl 端口** | **UNKNOWN / BLOCKED** | ol-mod 源码不在本机（`STAGE_REPORT_BATTLE.md`） |

---

## P.3 冲突状态一览

| 冲突 | 本轮结论 | 等级 |
|---|---|---|
| **A：DATA MAC 原语（Tiger192/AES192 vs SHA1/AES128）** | 构造一致；观测会话 = SHA1/AES128；真实会话逐字节复算阻塞 | 部分裁决（`OFFLINE_002_A`） |
| **B：COOKIE_ECHO 长度（189 vs 219）** | 本会话 = 219B；189B 为独立合法短地址变体（本会话不适用） | 已裁决（对观测会话） |
| **字段编号：field#15 vs field#19** | 两套独立结构，非零基/一基冲突 | **已裁决**（`OFFLINE_002_C`） |
| **svc 编号：线值 vs `svc_ops_e` 枚举** | 两套编号系并存；客户端用 CODOL 自定义空间（2/3/5/1） | 部分裁决（opcode 有旁证，snapshot 未定） |

---

## P.4 证据等级汇总

| 断言 | 等级 | 依据 |
|---|---|---|
| 明文 OOB / NAT / QoS / INIT / COOKIE / DATA 外层 / serverCommand / EOF 已确认 | **CONFIRMED** | 03 矩阵 + 本轮 A/B |
| CODOL svc opcode 空间 2/3/5/1 有客户端实测旁证 | **STRONG_CANDIDATE** | `protocol_map.md:330-333` |
| snapshot opcode 未定 | **UNKNOWN** | `protocol_map.md:334` |
| 客户端解码入口/状态机 | **INSTRUMENTATION_BLOCKED** | VMProtect（E 报告） |
| 会话描述符编号歧义已裁决 | **CONFIRMED** | C 报告 |
| 真实会话 MAC 逐字节复算 | **INSTRUMENTATION_BLOCKED** | A 报告 |
| 序列化器产出可被客户端解析 | **NOT_OBSERVED** | 无带载荷抓包 |

---

## P.5 复算/核对命令（只读）

```
Get-Content -LiteralPath '...\EARLY_SERVER_ANALYSIS\03_PROTOCOL\EARLY_SERVER_03_PROTOCOL_MATRIX.csv'
Get-Content -LiteralPath '...\CODOL_Server\lobby\docs\protocol_map.md' | Select-Object -Skip 326 -First 12
Get-Content -LiteralPath '...\EARLY_SERVER_ANALYSIS\08_OFFLINE_002\OFFLINE_002_A_MAC_REVIEW.md'
Get-Content -LiteralPath '...\EARLY_SERVER_ANALYSIS\08_OFFLINE_002\OFFLINE_002_C_DESCRIPTOR_INDEX_REVIEW.md'
```
