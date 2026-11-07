# OFFLINE_002 — 复核 B：COOKIE_ECHO 长度结论复核

> 任务：`EARLY-SERVER-OFFLINE-VALIDATION-002` §3（复核 `07_OFFLINE_001` 工作流 B）。
> 输入：只读；仅写 `08_OFFLINE_002\`；不启动服务端/客户端，不执行 `.cmd`，不修改样本/既有报告。
> 状态词：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / REFUTED / NOT_OBSERVED / INSTRUMENTATION_BLOCKED。

---

## B.0 复核结论（一句话）

- **219B 组成**在本轮由**第三份独立脚本**重新逐字节核对：`219 = 6(头部) + 38(cookie) + 67(长地址) + 8(u64 magic=1) + 100(公钥)` → **CONFIRMED（结构账本）**。
- **"该观测会话为 219B"** 的最高等级仍为 **STRONG_CANDIDATE**（受来源 U-1 限制，见 B.5）。
- **189B 仅对当前会话不适用**（本会话 **REFUTED**），但**作为独立合法短地址变体存在**（ol-mod `:324-341`）。
- **脚本独立性**：三份脚本使用**三种不同解析策略**（regex / 显式偏移切片 / token 列表 needle），但**共享同一输入文件** `battle_srv.log` → 属"解析独立、输入同源"，**不得**表述为完全独立验证。

---

## B.1 逐字节长度账本（219B，本轮独立重建）

原始证据：`REF_LOBBY_KIT\battle_srv.log:2324`
`[21:28:19] RX #4 peer=127.0.0.1:22011 len=219 hex=03 02 c3 f2 00 00 02 02 d2 41 ...`

| # | 字段 | 起始偏移 | 长度 | 日志可见 | 取值/说明 |
|---|---|---|---|---|---|
| 1 | type/version `03 02` | 0 | 2 | 是 | COOKIE_ECHO |
| 2 | verificationTag `c3 f2` | 2 | 2 | 是 | = serverTag 62147（LE 0xf2c3） |
| 3 | reserved `00 00` | 4 | 2 | 是 | 0（**非**长度字段） |
| 4 | cookie | 6 | 38 | 是 | `02 02 d2 41 ...`（含 clientTag@8:10、serverTag@24:26） |
| 5 | address block（bdCommonAddr 长形态） | 44 | 67 | 是 | `c0 a8 55 01 fb 55 ... 00 3c 01 f8 cf 9b 06 01` |
| 6 | u64 magic = 1 | 111 | 8 | 是 | `01 00 00 00 00 00 00 00` |
| 7 | 客户端公钥 | 119 | 100 | 仅前 9B | `30 44 03 02 07 00 02 01 1c` = DER SEQUENCE |
| — | **合计** | — | **219** | — | `6+38+67+8+100 = 219` |

- **线上总长度**：219（来自 `recvfrom` 的 `len(pkt)`，权威）。
- **头部**：`[0:6]`；**载荷**：`[6:219]`（cookie38 + addr67 + magic8 + pubkey100 = 213B）。
- **相关长度字段**：本帧**无显式长度字段**；`[4:6]=00 00` 为 reserved。
- **日志截断**：`battle_server.py:1457-1458` 记 `pkt[:128].hex(" ")`，故日志内仅前 **128B**；总长 219 **不受截断影响**。

### 189B 对照账本

| 字段 | 起始 | 长度 |
|---|---|---|
| 前缀（type/ver + tag + reserved） | 0 | 44 |
| address block（短形态） | 44 | 37 |
| securityId | 81 | 8 |
| 公钥 | 89 | 100 |
| **合计** | — | **189** |

- **本会话判定（REFUTED）**：189 形态要求 magic@103、pubkey@111。实测 `[103:111] = 00 3c 01 f8 cf 9b 06 01`（≠1）、`[111] = 01`（≠DER 0x30）。脚本 `alt189_magic_at_103_is_one=false`、`alt189_pubkey_at_111_is_der=false`。

---

## B.2 三脚本独立性与本轮复算

| 脚本 | 策略 | 是否共享解析函数 |
|---|---|---|
| `07_OFFLINE_001\_tools\verify_offline_001.py` | `re` 正则 + tag-driven walk | 否 |
| `07_OFFLINE_001\_tools\verify_cookie_len_2nd.py` | 显式字节索引切片 + 偏移表 | 否 |
| `08_OFFLINE_002\_tools\verify_offline_002.py` | token 列表 + byte-index slice + needle | 否 |

- **三份脚本解析逻辑互不调用、互不 import**（CONFIRMED）。
- **但三者读取同一文件 `battle_srv.log`** → **共享输入**。若该日志本身有系统性记录错误，三者会**同向出错**。因此本轮**不**把"三脚本一致"表述为完全独立验证；它只排除"单一脚本解析 bug"这一类错误。
- **本轮复算结果**（`offline_002_evidence.json` 的 `B_cookie_echo`）：
  - `declared_len=219`、`hex_tokens_in_log=128`、`log_truncated_at_128=true`
  - `segments` 合计 `sum_of_segments=219`
  - `u64_magic_is_one=true`、`pubkey_prefix_is_der_seq=true`
  - `alt189_magic_at_103_is_one=false`、`alt189_pubkey_at_111_is_der=false`

---

## B.3 客户端构造 vs 服务端解析

- **客户端（构造侧）**：C# `CodolProtocol.cs:35` `KeyExchangeLength=219`；`:40-42` cookie@6、magic@111、pubkey@119；`:161-170` `TryParseKeyExchange` 要求 `pkt.Length==219`。ol-mod `net_dtls_cod.cpp:333-341` 用 `packet.size()` 在 67/37 之间选择地址长度。
- **服务端（解析侧）**：
  - **原生**：`codol_handshake.c:47` 硬性 `n != 189 → return 0`；`codol_network.c:411` `packet[0]==3 && packet[1]==2 && n==189`。→ **硬拒 219**。
  - **REF/ol-mod**：接受 219（长地址）与 189（短地址）两形态。
- **长度字段归属**：本帧**不携带显式长度字段**；长度由 UDP 数据报边界决定。服务端解析长度来自 `recvfrom` 返回的 `n`，不是报文内字段。

---

## B.4 可重复长度计算过程

```
219 = 6   (type[2] + verificationTag[2] + reserved[2])
    + 38  (cookie)
    + 67  (bdCommonAddr 长形态)
    + 8   (u64 magic = 1)
    + 100 (客户端公钥, DER SEQUENCE 30 44 ...)
    = 219

189 = 44 (prefix: type/ver + tag + reserved + ... 短形态前缀)
    + 37 (bdCommonAddr 短形态)
    + 8  (securityId)
    + 100(公钥)
    = 189
```

- 锚点校验：magic 必须 = 1（`01 00 00 00 00 00 00 00`），公钥必须以 `0x30`（DER SEQUENCE）开头。219 形态两锚点均命中（@111 / @119）；189 形态两锚点在实测字节上均**不**命中。

---

## B.5 来源可信度保留（U-1）

- `_BATTLE_ARCHAEOLOGY_20261005_20261008.md:419` 保留："docs 断言真实客户端；**日志本身无法 100% 区分**真机与实验室回放"。
- 故"该会话为 219B"的最高等级取 **STRONG_CANDIDATE**（若接受 U-1 的来源判定则为 CONFIRMED）。
- **升级到 CONFIRMED 所需最小证据**：一份能独立证明来源（真机、非回放）的同会话抓包，或客户端侧 `bdDTLSCookieEcho` serializer 的静态反汇编定位。

---

## B.6 证据等级汇总

| 断言 | 等级 | 依据 |
|---|---|---|
| 219B 结构账本 `6+38+67+8+100` 自洽 | **CONFIRMED** | 三脚本独立解析（同源输入） |
| 该观测会话 COOKIE_ECHO = 219B | **STRONG_CANDIDATE** | `:2324 len=219` + 锚点自洽 + 后续 OOB 成功（U-1 限制） |
| 189B 为该会话实际形态 | **REFUTED** | magic@103≠1、pubkey@111 非 DER |
| 189B 为独立合法短地址变体 | **STRONG_CANDIDATE** | ol-mod `:324-341` + 原生 189 路径 |
| 原生硬拒 219B | **CONFIRMED** | `codol_handshake.c:47`；`codol_network.c:411` |
| `captures/*.jsonl` 可裁决 B | **REFUTED** | 无载荷字节 |

---

## B.7 结论边界

- 本轮**只**断言"对**当前观测会话**，219B 成立、189B 不适用"；**未**断言 189B 是错误形态。
- **其他合法地址形式**：短地址 37B（189B 帧）**存在且合法**（ol-mod 双形态支持），但**不适用**于本会话。
- **脚本独立性的诚实标注**：解析独立、输入同源 → 不足以排除"日志系统性记录错误"。

---

## B.8 复算命令（只读）

```
python _tools\verify_offline_002.py     # B_cookie_echo: declared_len=219, sum=219, alt189 排除
python _tools\verify_offline_001.py     # 001 主脚本（regex 策略）
python _tools\verify_cookie_len_2nd.py  # 001 第二脚本（显式偏移策略）
```
