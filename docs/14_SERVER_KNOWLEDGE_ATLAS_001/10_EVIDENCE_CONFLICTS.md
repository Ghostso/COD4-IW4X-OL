# 10 — 证据冲突登记 / EVIDENCE CONFLICTS

> 原则：**不静默修正**。两份本地材料冲突时，双方都留，登记来源、影响与裁定状态。

## CONFLICT-01 — COOKIE_ECHO 长度：189 B vs 219 B

| 侧 | 值 | 来源 |
|---|---|---|
| A | 189 B | `codol_handshake.c:47`（`n == 189` 校验）；`COOKIE_ECHO` 结构 `[89:189]=100B 客户端公钥` |
| B | 219 B | C# `CodolProtocol.cs`；`DEV-BOOKING\PVE-BATTLE-CONTRACT-LINEAGE-021.md` §8 “cookie+pubkey 219B / ack 114B” |

- 影响：握手字节级复现与真实客户端互操作。
- 已有裁定（局部）：对观测到的 1.1.1.13/22011 客户端，**冲突 B 为已裁决**（`OFFLINE_001_B_COOKIE_ECHO_LENGTH.md`）。
- 全局状态：`SOURCE-CONFLICT`（保留）——**两个数字可能分别对应不同版本/不同阶段的 packet**。
- 证伪条件：对 C-2697 抓包得到确定长度。

## CONFLICT-02 — 协议号：内部 codec 187 vs 出站 protocol 1

| 侧 | 值 | 来源 |
|---|---|---|
| A | `CODOL_PROTOCOL 187` | `codol_wire.h:8` |
| B | `protocol\1\shortversion\1.1.1.13` | `codol_connect.c:91` 出站 connectResponse |
| C | 实机二分：187 卡住客户端，1 能连 | `codol_connect.c:89-91` 注释（2026-09-02） |

- 影响：任何“CODOL 协议号 = X”的断言。
- 状态：`SOURCE-CONFLICT`（内部选择 vs 出站线值），**不强行统一**。
- 证伪条件：对 C-2697 抓取 connectResponse。

## CONFLICT-03 — “CODOL 使用 DTLS”

| 侧 | 判断 | 来源 |
|---|---|---|
| 旧 | 存在 DTLS/ECDH/secp224 字符串 → CODOL 使用 DTLS | 早期字符串扫描 |
| 新 | 这些是**静态链接 OpenSSL 自带表**（OpenSSL x45、DTLS1_ x27…）；字符串不能作证 | DEV-BOOKING-021 §3 |

- 状态：**旧结论被降级**。CODOL 有 **bdDTLS 风格的自定义记录层**，但**不能**断言使用了标准 DTLS。
- 修订记录：见 `16` §7 与 `REVISION_LOG.md` REV-001。
- 证伪条件：找到 CODOL 游戏通道调用标准 DTLS API 的调用链。

## CONFLICT-04 — COOKIE_ACK / INIT_ACK 结构表述

| 侧 | 内容 |
|---|---|
| 源码 | `codol_handshake.c:45` `ack[114]={4,2}`；`out[38]` INIT_ACK |
| C# | `CookieLength=38`、`PublicKeyLength=100`、`BuildKeyAck` |

- 状态：基本一致，但字段命名不同（源码 vs C#）。**保留双述**，不做合并。

## CONFLICT-05 — 客户端版本混淆风险（3.3.3.3 vs 2.6.9.7）

| 侧 | 值 |
|---|---|
| C-3333 | SHA-256 `36997674…`，7,841,344 B，FileVersion 1649370，ol-mod 目标 |
| C-2697 | SHA-256 `35375404…`，9,964,656 B，manifest `original_exe_sha256` |

- 影响：把 3.3.3.3 的运行结果当作 2.6.9.7 的证据。
- 状态：**已显式隔离**（`00` §2.2）；任何跨用必须标注。
- 证伪条件：无（这是身份事实）。

## CONFLICT-06 — IW4x 的双克隆

| 侧 | HEAD |
|---|---|
| A | `d1b175da1a25d31043246de103a702b206269e5a`（2026-09-20） |
| B | `0699a7e5716ded53bcfa6748bcb89a535f8f39f0`（2026-09-17） |

- 影响：引用“IW4x 的行为”时不指明 HEAD 即为不可复现。
- 状态：`SOURCE-CONFLICT` / BLOCKED（差异清单未建立）。
- 证伪条件：生成两份克隆的差异清单。

## CONFLICT-07 — `IW4X_SERVER_SOURCE_NOT_FOUND` vs 早期任务假设

| 侧 | 判断 |
|---|---|
| 早期任务 | “优先复用 OLMod/IW4X 已有实现” |
| 证据 | IW4x 只产出 DLL，**无专用服务器源码**；ol-mod **不基于 IW4x** |

- 状态：早期假设 **REFUTED**。修订记录 REV-002。
- 证伪条件：找到 IW4x 专用服务器源码（本地不存在）。

## CONFLICT-08 — OLD 源码 vs 二进制对应性

| 项 | 状态 |
|---|---|
| OLD `dedicated\src\` | 完整 C 源码存在 |
| OLD `codol_dedrun.exe` | 8,469,493 B，与源码**无 PDB/MAP 绑定** |
| 源码→二进制逐函数对应 | **未建立**（无符号表） |

- 影响：源码行号结论与二进制 RVA 结论必须分开标注，不能互证为“同一函数”。
- 状态：BLOCKED（无调试信息）。
- 证伪条件：找到匹配的 MAP/PDB 或做签名匹配。

## CONFLICT-09 — 2697 “含源码” vs 实际

| 侧 | 内容 |
|---|---|
| 表面 | `codol_2697_*.c` 源文件名字符串存在于二进制 |
| 实际 | 旧包源码树 `grep 2697` = **0 命中**；本地无 2697 源码 |

- 状态：`source file names` VERIFIED；`source code availability` REFUTED。
- 证伪条件：发现 2697 源码树。

## CONFLICT-10 — 大厅服务端身份

| 侧 | 内容 |
|---|---|
| `CODOLServer\lobby_server\lobby_plain_probe.py` | 自研（anchor 后未再改） |
| `REF_LOBBY_KIT\lobby_server.py` | 第三方（真正进大厅者） |

- 状态：命名陷阱，已澄清（EV-Lobby-Third）。**两个不同服务端。**

---

## 冲突汇总

| ID | 主题 | 状态 |
|---|---|---|
| 01 | COOKIE_ECHO 长度 | SOURCE-CONFLICT（局部已裁决） |
| 02 | 协议号 187 vs 1 | SOURCE-CONFLICT |
| 03 | DTLS 使用 | 旧结论已降级 |
| 04 | ACK 结构表述 | 双留 |
| 05 | 客户端版本混淆 | 已隔离 |
| 06 | IW4x 双克隆 | SOURCE-CONFLICT / BLOCKED |
| 07 | IW4x 服务器源码 | REFUTED 旧假设 |
| 08 | OLD 源码↔二进制 | BLOCKED |
| 09 | 2697 源码可用性 | REFUTED |
| 10 | 大厅服务端身份 | 已澄清 |

> 任务书 §9 反证研究：以上冲突 03/07/09 属于**已执行的反例**（推翻了先前的正向判断）。