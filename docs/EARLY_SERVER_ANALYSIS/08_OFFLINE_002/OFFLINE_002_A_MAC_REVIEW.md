# OFFLINE_002 — 复核 A：DATA MAC 结论复核

> 任务：`EARLY-SERVER-OFFLINE-VALIDATION-002` §2（复核 `07_OFFLINE_001` 工作流 A）。
> 输入：只读。派生脚本/证据仅写 `08_OFFLINE_002\`；不启动服务端/客户端，不执行 `.cmd`，不修改样本/既有报告，不输出密钥材料。
> 状态词：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / REFUTED / NOT_OBSERVED / INSTRUMENTATION_BLOCKED。
> 被复核断言：`HMAC-SHA1(key24, hdr[0:6] || pkt[14:])[:8]`。

---

## A.0 复核结论（一句话）

- **MAC 构造（外层）**：四份实现逐字节一致 → **CONFIRMED**（本轮以源码逐行复核确认，未升级为"真实会话已验证"）。
- **真实客户端原语族 = SHA1 派生 + AES-128 流**：**STRONG_CANDIDATE**（三条独立实现同族 + 一条"MAC 通过后明文成功"的行为链）。
- **真实会话 8B MAC 逐字节复算**：**INSTRUMENTATION_BLOCKED**（缺本会话完整 24B key / ECDH 私钥）。
- **未升级声明**：实现一致性（CONFIRMED）与算法推断（STRONG_CANDIDATE）**均不得**直接升级为"真实会话逐字节验证"。本轮明确保留该鸿沟。

---

## A.1 五个必答问题

### 问 1：四种实现是否使用独立的实现路径和输入解析逻辑？

**结论：是（CONFIRMED）。** 四份实现的**语言、原语库、密钥派生、输入区间**均不同：

| # | 实现 | 语言/库 | 派生 | keystream | MAC 输入区间 | 文件:行 |
|---|---|---|---|---|---|---|
| 1 | 原生早期服务端 | C / tomcrypt+mbedtls | Tiger192(x28‖sec16)→24B | AES-192-ECB，seed=Tiger192(counter LE4)，LE 自增 | `header[6] ‖ cipher[length]` | `codol_crypto.c:65-78` |
| 2 | 现有 C# | C#（自实现 AES/SHA1） | 上游给 transportKey24 | AES-128-ECB，counter=SHA1(seed6)，LE 自增 | `pkt[0:6] ‖ pkt[14:]` | `CodolProtocol.cs:201-215` |
| 3 | 参考 Python | Python（stdlib 或自带） | SHA1(shared_x28_BE‖sec16)‖4×00→24B | AES-128-ECB，counter=SHA1(seed6)，LE 自增 | `pkt[0:6] ‖ pkt[14:]` | `battle_server.py:516-534` |
| 4 | 第三方 ol-mod | C++ | SHA1(44B 共享材料) | AES-CTR-LE，iv=SHA1(seq‖tag) | `pkt[0:6] ‖ pkt[14:]` | `net_dtls_cod.cpp:259-296` |

- **输入解析逻辑独立**：原生侧直接以 `header[6]` 形参 + `cipher` 指针表达；C#/Python/ol-mod 均以"整包切片 `[0:6]` 与 `[14:]`"表达。两种表达**在字段边界上等价**（`[0:6]` 与 header 6B 相同；`[14:]` 与 cipher 起点相同，因为 `len` 字段位于 `[14:16]`，cipher 从 `[16:]` 起——见问 2 说明）。
- **四条路径不存在共享代码或共享解析器**（分属 4 个不同工程、4 种语言），故"一致"不是同源复制的结果。

> 说明：**输入区间语义等价性**是本轮从源码逐行核对确认的（CONFIRMED）；`hdr[0:6]` 对应 C# 的 `pkt[0:6]`；原生 `cipher` 从 `[16:]` 起，而 C# `pkt[14:]` 含 `len` 两字节 + cipher——**两者并非同一字节序列**。见 A.2 澄清。

### 问 2：实现之间逐字节一致的证据是什么？

**结论：构造形态一致（CONFIRMED）；但"输入区间是否逐字节相同"存在一个必须澄清的差异。**

- **一致部分**：四者都是 `HMAC-SHA1(key24, A ‖ B)` 取前 8 字节，其中 `A` = 报文前 6 字节、`B` = 认证覆盖的密文/载荷部分，key 均为 24 字节。
- **必须澄清的差异**（本轮新增，纠正"四者逐字节相同"的过度表述）：
  - 原生 `codol_crypto.c:65-78` 的 `mac()` 第二段是 **`cipher`（纯密文）**，即 `hdr[0:6] ‖ cipher`。
  - C#/REF/ol-mod 的第二段是 **`pkt[14:]`**，即 `len(2B) ‖ cipher`。
  - 二者相差**报文 `[14:16]` 的两个长度字节**。因此严格地说，**原生 MAC 输入 ≠ C#/REF/ol-mod MAC 输入**，除非原生调用点传入的 `cipher` 指针实际起始于 `[14:]`（含 len）。该调用点未在本轮所取的 `codol_crypto.c` 片段内闭合。
  - **本轮判定**：把"四实现 MAC 输入区间逐字节相同"降级为 **CANDIDATE**（而非 CONFIRMED），并登记为待澄清项（见 A.5）。**能确认的是**：C# / REF / ol-mod **三者之间** `pkt[0:6] ‖ pkt[14:]` 完全一致（CONFIRMED）；原生与这三者的差异落在 `[14:16]` 两字节。
- **RX#5 头字段解析一致（CONFIRMED）**：`verify_offline_002.py` 独立解析 `battle_srv.log:2327` 的 54B 帧，得 `type_ver=[6,2]`、`tag_le=[195,242]`、`seq_le=[1,0]`、`mac8=cb41897b4923f694`、`len_le=[38,0]`（=38），`frame_self_consistent=true`（`16+38=54`）。字段偏移与 C# `:199-215`、原生 `codol_crypto.c:87-95` 完全对应。

### 问 3：哪些证据支持客户端使用 SHA1 与 AES128？

**结论：STRONG_CANDIDATE。** 支持证据（三条独立实现 + 一条行为链）：

1. **C# `CodolProtocol.cs:213-214`**：`key16 = transportKey24[0:16]`，用 AES-128；`:241-244` `Seed(seq,tagLo,tagHi)={seq&0xFF, seq>>8, 0,0, tagLo,tagHi}`。
2. **REF `battle_server.py:328-336`**：`derive_transport_key` = `SHA1(shared_x28_BE ‖ security16) ‖ 4×0x00 → 24B`；`:340-352` keystream = AES-128-ECB + counter=SHA1(seed6)。
3. **ol-mod `net_dtls_cod.cpp:197-203`**：`derive` = `SHA1(44B)`；`:205-217` `aesKey()`=digest[0:16]，`hmacKey()`=digest20‖4×00；`net_dtls_cod.hpp:18` `SecurityKeySize=16`。
4. **行为链（最强）**：`battle_srv.log:2324`（219B COOKIE_ECHO）→ `:2325`（`KEY_EXCHANGE_OK`）→ `:2327`（54B DATA）→ `:2328`（`RX_OOB ... getchallenge`）——参考服务端用**该会话密钥**对该 DATA 完成 MAC 校验 + 解密后才读出明文 OOB。这条链**只证明**"REF 的 SHA1/AES128 路径与该客户端互通"，**不证明** C# 或 ol-mod 亦互通。

**不支持原生的证据**：原生 `codol_crypto.c:1-3` 文件头自述 DATA 用 Tiger192 派生 + AES-192，与上述四条相反；原生硬性要求 COOKIE_ECHO `n==189`（`codol_handshake.c:47`），而本会话为 219B → 原生路径**未与该客户端对齐**。

### 问 4：真实会话 MAC 是否已经通过验证？

**结论：未通过逐字节复算验证 —— INSTRUMENTATION_BLOCKED。**

- 日志 `battle_srv.log:2325` 只记录 `transport=22d0fa6843b44afe0bedd2777d22f7c1`（**32 个 hex 字符 = 16 字节**），即 24B transport key 的**前 16 字节**。
- `verify_offline_002.py` 复核：`transport_prefix_len_chars=32`（`offline_002_evidence.json`）。
- 缺**后 8 字节**，且 ECDH 私钥每轮随机、不落盘 → 无法重建完整 24B key → **无法逐字节复算 8B MAC**。
- **行为性通过**（REF 侧）≠ **离线逐字节通过**：`:2328` 证明 REF 服务端在**它自己持有的密钥上下文**下校验通过；这不能替代"用独立脚本对该会话 MAC 逐字节复算"。

### 问 5：缺少完整密钥材料后，哪些结论仍然无法确认？

| 无法确认项 | 原因 | 最小闭合证据 |
|---|---|---|
| 该会话 8B MAC 的逐字节值 | 只有 16/24B key | 完整 24B transport key（绑定 seq） |
| keystream 逐字节 | 同上（AES-128 需要 key16，但需完整 key 才能派生验证） | 同上，或同期 ECDH 私钥/共享 X(28B) |
| C# / ol-mod 对**真实客户端**的互通 | 仅 REF 有行为链 | 对同一 24B key 复算 C#/ol-mod 路径并比对 |
| 原生 Tiger192/AES-192 是否**绝对**错误 | 仅对本观测客户端不成立 | 一份原生 association 与真实 C1 的同期密钥上下文 |
| `[14:16]` 是否计入 MAC 输入（原生 vs C#） | 原生 `cipher` 调用点未闭合 | 原生 `mac()` 调用点源码/反汇编 |

---

## A.2 澄清：`hdr[0:6] ‖ cipher` 与 `pkt[0:6] ‖ pkt[14:]`

- C# 侧：`pkt` 布局 = `[0:2]` type/ver、`[2:4]` tag、`[4:6]` seq、`[6:14]` mac8、`[14:16]` len、`[16:]` cipher。故 `pkt[14:]` = `len(2) ‖ cipher`。
- 原生侧：`mac(digest, header[6], cipher, length, key)` —— 第二段是 `cipher`（纯密文）。
- 若原生调用点传入的 `cipher` 指向 `[16:]`，则原生 MAC 覆盖 `[0:6] ‖ [16:]`，**不含** `[14:16]`；C# 覆盖 `[0:6] ‖ [14:]`，**含** `[14:16]`。二者**相差 2 字节**。
- **本轮不强行统一**：将该点登记为 UNKNOWN，最高只能给"三者一致（C#/REF/ol-mod）CONFIRMED + 原生差异 CANDIDATE"。

---

## A.3 捕获数据限制（本轮复核）

- 四个 `wiretap-*.jsonl` 共 **11,878** 事件，`kind ∈ {task,push,auth_frame,udp,stun_reply,counter,write,handler_exception,undecodable,refused,udp_unhandled}`，`layer ∈ {lobby,seckey,stun}`，**0 个事件携带报文载荷字节**。
- `lobby\docs\wiretap_report.md:185` 自述 "No game-layer events in this capture"。
- **结论（REFUTED）**：现有捕获**无游戏层载荷**，**不能**裁决 A。本轮**不**从不存在载荷的捕获中推断 MAC。

---

## A.4 复算步骤（可重复，只读）

1. 计算 `battle_srv.log` SHA-256 = `3CB3E9CD47472AC121F35301B59D1D9DFC7313BC689D760F6E6A546C8C1C01BA`（与 `OFFLINE_001_CHECKSUMS.txt` 一致）。
2. 运行 `_tools\verify_offline_002.py`（第三份独立解析器，byte-index 策略）。
3. 读 `_evidence\offline_002_evidence.json` 的 `A_data_mac`：`declared_len=54`、`hex_tokens_in_log=54`、`not_truncated=true`、`mac8=cb41897b4923f694`、`len_le_value=38`、`frame_self_consistent=true`、`transport_prefix_len_chars=32`。
4. 逐行核对四份源码的 MAC 调用点（见 A.1 表）。
5. 结论：构造一致（CONFIRMED）；真实会话复算阻塞（INSTRUMENTATION_BLOCKED）。

---

## A.5 证据等级汇总

| 断言 | 等级 | 依据 |
|---|---|---|
| C#/REF/ol-mod 三者 MAC 输入 `pkt[0:6]‖pkt[14:]` 一致 | **CONFIRMED** | 三份源码逐行 + RX#5 头解析 |
| 四者（含原生）MAC 输入逐字节相同 | **CANDIDATE** | 原生 `cipher` 起点未闭合（`[14:16]` 差异） |
| 四者 MAC 构造形态（HMAC-SHA1 取前 8B，key24）一致 | **CONFIRMED** | 四份源码逐行 |
| 观测会话原语 = SHA1 派生 + AES-128 流 | **STRONG_CANDIDATE** | C#/REF/ol-mod 同族 + RX#5 后 OOB 成功解密 |
| 原生 Tiger192/AES-192 对观测客户端成立 | **REFUTED** | 原生硬拒 219B；audit 自述未验证真实 C1 |
| 该会话 8B MAC 逐字节复算 | **INSTRUMENTATION_BLOCKED** | 仅 16/24B key；ECDH 私钥不落盘 |
| `captures/*.jsonl` 可裁决 A | **REFUTED** | 无载荷字节 |

---

## A.6 与工作流 B/C 的一致性

- 与 B 一致：本会话为 **219B 长地址**形态（原生 189B 路径不适用）。
- 与 C 一致：16B securityKey 是 ECDH 派生输入的一半（`codol_crypto.c:28-37`），进入 `x28‖sec16 → key24`。
- **无矛盾**；A 的阻塞（缺完整 key/私钥）与描述符布局**无关**，未强行关联。

---

## A.7 本轮新增/修正（相对 001）

1. **新增澄清**：原生 `hdr[0:6]‖cipher` 与 C# `pkt[0:6]‖pkt[14:]` 在 `[14:16]` 上可能相差 2 字节 → 将"四者逐字节相同"从 CONFIRMED 降为 **CANDIDATE**（三者一致仍 CONFIRMED）。
2. **保留**：逐字节 MAC 复算 INSTRUMENTATION_BLOCKED；捕获无载荷 REFUTED。
3. **未越界**：未将实现一致性/算法推断升级为真实会话验证。
