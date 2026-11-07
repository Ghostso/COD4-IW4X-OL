# OFFLINE_001 — 工作流 B：COOKIE_ECHO 长度冲突裁决

> 任务：`EARLY-SERVER-OFFLINE-VALIDATION-001` 工作流 B。
> 只读输入；派生脚本/报告仅写 `07_OFFLINE_001\`；不启动服务端/客户端，不执行 `.cmd`。
> 状态词：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / REFUTED / NOT_OBSERVED / INSTRUMENTATION_BLOCKED。

---

## B.0 一句话结论

**冲突 B 为"已裁决"（对观测到的 1.1.1.13/22011 客户端）。**

- 该客户端实际发送的 COOKIE_ECHO **总长 = 219B**（STRONG_CANDIDATE；两份独立脚本 + 长度/偏移自洽）。
- **189B = 另一条合法变体**（37B 短地址形态），在**本次观测中被 REFUTED 为该会话的实际形态**。
- 结论：`219 = 44(前缀) + 67(长地址) + 8(securityId) + 100(公钥)`；`189 = 44 + 37 + 8 + 100`。
- **对客户端兼容性的直接影响**：原生服务端硬性要求 `n==189`（`codol_handshake.c:47`），会**硬拒**该客户端 → 原生路径与该客户端不兼容。

---

## B.1 冲突定义与证据来源

冲突 B（`04_REUSE\EARLY_SERVER_04_BLOCKERS.md` K3；`03_PROTOCOL\EARLY_SERVER_03_CLIENT_SERVER_CORRELATION.md:147,156`）：

| 侧 | 长度 | 关键偏移 |
|---|---|---|
| 原生 `codol_handshake.c` | 189B（`:47 if(... n != 189) return 0;`） | cookie@6，secId@81，pubkey@89 |
| 现有 C# `CodolProtocol.cs` | 219B（`:35 KeyExchangeLength=219`） | cookie@6，u64 1@111，pubkey@119 |

### 证据定位（已逐条打开核对）

1. **真实报文**：`...\REF_LOBBY_KIT\battle_srv.log:2324`
   `[21:28:19] RX #4 peer=127.0.0.1:22011 len=219 hex=03 02 c3 f2 00 00 02 02 ...`（日志 `pkt[:128]`，见下）。
2. **原生硬性 189**：`...\dedicated\src\codol\net\codol_handshake.c:47`；`:49 memcmp(s->echo,packet,189)`；`codol_network.c:411 else if(packet[0]==3 && packet[1]==2 && n==189)`。
3. **现有 C# 219**：`...\CODOL-Combat-Server-v0.1\src\Codol\CodolProtocol.cs:35` `KeyExchangeLength=219`；`:40-42` `CookieOffsetInKeyExchange=6`，`MagicOneOffsetInKeyExchange=111`，`PublicKeyOffsetInKeyExchange=119`；`:161-170` `TryParseKeyExchange`。
4. **参考 Python 219**：`...\REF_LOBBY_KIT\battle_server.py:452-468`（`if len(pkt)!=219 or pkt[0]!=3 or pkt[1]!=2`；`:468 derive_transport_key(bytes(pkt[119:219]))`）。
5. **第三方双形态**：`...\_e1_regression\ol-mod-olfinal\...\net_dtls_cod.cpp:324-341`
   - `:324-328` 注释："A bdCommonAddr is 67 bytes on the wire, but an older session record carried the 37-byte short form, and the client echoes back whatever it was given -- **so both 219 and 189 are real** and the offsets after the address move with it."
   - `:333-341` `LongAddressSize=67`，`ShortAddressSize=37`，`AddressOffset=44`，`SecurityIdSize=8`；按 `packet.size()` 选 67 或 37。
   - `:353-357` secId 偏移 = `AddressOffset + addressSize`；pubkey 紧随其后。

---

## B.2 逐字节长度账本（219B 形态）

线上总长（`len=219`，直接来自 `recvfrom` 的 `len(pkt)`）与分段：

| # | 字段 | 起始偏移 | 长度 | 日志内可见 | 取值/说明 |
|---|---|---|---|---|---|
| 1 | 类型/版本 `03 02` | 0 | 2 | 是 | COOKIE_ECHO |
| 2 | verificationTag `c3 f2` | 2 | 2 | 是 | = serverTag 62147（LE 0xf2c3） |
| 3 | reserved `00 00` | 4 | 2 | 是 | 0 |
| 4 | cookie | 6 | 38 | 是 | `02 02 d2 41 ... 00 00`（含 clientTag@8:10、serverTag@24:26） |
| 5 | address block（bdCommonAddr 长形态） | 44 | 67 | 是 | `c0 a8 55 01 fb 55 ... 00 3c 01 f8 cf 9b 06 01` |
| 6 | u64 magic = 1 | 111 | 8 | 是 | `01 00 00 00 00 00 00 00` |
| 7 | 客户端公钥 | 119 | 100 | **否**（仅前 9B） | `30 44 03 02 07 00 02 01 1c` = DER SEQUENCE |
| — | **合计** | — | **219** | — | `2+2+2+38+67+8+100 = 219` |

- **线上总长度**：219（权威，来自 `recvfrom` 返回值）。
- **头部**：`[0:6]` = type/ver + tag + reserved（6B）。
- **载荷**：`[6:219]` = cookie(38) + address(67) + magic(8) + pubkey(100) = 213B。
- **相关长度字段**：本帧**无显式长度字段**，长度由 UDP 数据报本身界定；报文内 `[4:6]=00 00` 为保留，非长度。
- **日志截断说明**：`battle_server.py:1457-1458` 记录 `pkt[:128].hex(" ")`，故日志内仅前 **128B**；`[119:128]` 恰含公钥前 9B。**总长 219 不受截断影响**（长度来自 `len(pkt)`）。

### 189B 对照账本（短地址形态）

| 字段 | 起始 | 长度 |
|---|---|---|
| 前缀（type/ver + tag + reserved） | 0 | 44 |
| address block（bdCommonAddr 短形态） | 44 | 37 |
| securityId | 81 | 8 |
| 公钥 | 89 | 100 |
| **合计** | — | **189** |

- **对本会话的判定（REFUTED）**：若为 189 形态，`u64 magic` 应在偏移 **103**，公钥应在 **111**。实测 `[103:111] = 00 3c 01 f8 cf 9b 06 01`（≠1），`[111:119] = 01 00 00 00 00 00 00 00`（≠DER）→ **189 形态与该 219B 报文不符**。脚本 `alt189_magic_matches=false`、`alt189_pubkey_is_der=false`。

---

## B.3 客户端构造路径 vs 服务端解析路径

- **客户端构造**：ol-mod 注释 `net_dtls_cod.cpp:324-328` 明确"**客户端回显它所收到的地址形态**"。故长度由 lobby 下发的 bdCommonAddr 形态决定：长 67B → 219B；短 37B → 189B。**同一客户端可因下发形态不同而发 219 或 189**。
- **服务端解析（原生）**：`codol_handshake.c:47` 仅接受 `n==189`，按 81/89 取 secId/pubkey → **对 219B 直接 `return 0`（拒绝）**。
- **服务端解析（C#/REF）**：`CodolProtocol.cs:163` 仅接受 219；`battle_server.py:453` 仅接受 219。两者对 189B 会拒绝。
- **结论**：189 与 219 **不是"谁对谁错"，而是"地址形态选择"**；本轮观测到的是**长地址（219B）**。

---

## B.4 独立离线复算（脚本与结果）

两个**独立**脚本（不同解析策略）：

- `_tools\verify_offline_001.py`（正则 + 显式偏移表）→ `_evidence\offline_001_evidence.json`。
- `_tools\verify_cookie_len_2nd.py`（字符索引切片 + 显式偏移表，不复用正则）→ `_evidence\offline_001_evidence_2nd.json`。

### 复算步骤（可重复）

1. 计算 `battle_srv.log` SHA-256 = `3CB3E9CD…`（见 B.6）。
2. `python verify_offline_001.py` → `workflows.B_cookie_echo.ledger`：`declared_len=219`，`hex_byte_count_in_log=128`，`truncated_in_log=true`，`field_checks.u64_at_111_eq_1=true`，`pubkey_starts_DER_SEQ=true`。
3. `python verify_cookie_len_2nd.py` → `B_cookie_echo_ledger`：`sum_of_segment_lengths=219`，`equals_declared=true`，`u64_magic_is_one=true`，`pubkey_prefix_is_der=true`，`alt189_magic_matches=false`，`alt189_pubkey_is_der=false`。

### 结果

- 两脚本**独立得出同一长度账本**：`6 + 38 + 67 + 8 + 100 = 219`。
- 两脚本**独立排除 189**：magic 位置 111≠103，公钥前缀在 111 处非 DER。
- 该会话随后 `:2325 KEY_EXCHANGE_OK`、`:2327 RX#5 DATA`、`:2328 getchallenge` 明文成功 → **该 219B 帧被参考服务端完整接受**（交叉佐证 219 为真实形态）。

---

## B.5 排除项

1. **捕获截断**：总长 219 取自 `len(pkt)`，与日志 hex 截断（128B）无关。→ 排除。
2. **错误分帧**：219 = 44+67+8+100，且 magic/DER 锚点自洽。→ 排除。
3. **字段偏移错误**：magic 必在 111、公钥必在 119，两处锚点均命中。→ 排除。
4. **字节序错误**：tag `c3 f2`（LE 0xf2c3=62147）与 `TX_DTLS_INIT_ACK serverTag=62147` 一致；u64 magic=1 为 LE。→ 排除。
5. **会话参数不一致**：RX#4/RX#5/RX_OOB 同 peer `127.0.0.1:22011`、同 tag `c3 f2`。→ 排除。
6. **`captures/*.jsonl` 可用性**：**REFUTED**（同 A.3-6，无载荷字节；`wiretap_report.md:185` "No game-layer events"）。E2 计划前提不成立，改用 `battle_srv.log` 真实会话。

### 来源可信度保留（与 A 共用）

- `battle_srv.log` 记录 `RX #N ... hex=` 的代码路径**仅存在于** `battle_server.py:1457-1458` 的 `main()`；selftest 的 `serve()` 循环**不打印 RX hex**且绑定 28961，而本会话端口为 28960/22011。
- `_BATTLE_ARCHAEOLOGY_20261005_20261008.md:84-95` 将该会话标为 "REAL client session"；`:419`（U-1）保留："docs 断言真实客户端；**日志本身无法 100% 区分**真机与实验室回放"。
- 故本裁决的最高等级为 **STRONG_CANDIDATE**（若接受 U-1 的来源判定则为 CONFIRMED；本报告保守取 STRONG_CANDIDATE）。

---

## B.6 输入版本与哈希（SHA-256）

| 输入 | SHA-256 |
|---|---|
| `REF_LOBBY_KIT\battle_srv.log` | `3CB3E9CD47472AC121F35301B59D1D9DFC7313BC689D760F6E6A546C8C1C01BA` |
| `...\dedicated\src\codol\net\codol_handshake.c` | `F9BE49F76C6D1A66E1FF520CC47C2456AE53B0346B7654A87F6C0A5B2F9702B1` |
| `...\dedicated\src\codol\net\codol_network.c` | `FEB5BD4A0E78CD3134F3380CCBA2DDDF75583A91985BFE2637047574D2807B55` |
| `CODOL-Combat-Server-v0.1\src\Codol\CodolProtocol.cs` | `FA06D0543B621216DC57C05A581EC1DCB8F00D18A9BF1368942213C75CF4A046` |
| `...\_e1_regression\ol-mod-olfinal\...\net_dtls_cod.cpp` | `1EB45A4398AAE9655A07772894D0A5A3479E25D62689605C4F9420027E28EC1F` |
| `REF_LOBBY_KIT\battle_server.py` | `71BB7BEB85E514082B91A4925D18CB09FD07D5E8916FFA7F4FBD4A9750B47274` |

---

## B.7 证据等级汇总

| 断言 | 等级 | 依据 |
|---|---|---|
| 观测会话 COOKIE_ECHO = 219B | **STRONG_CANDIDATE** | `:2324 len=219` + 两脚本长度/偏移自洽 + 后续 MAC/明文成功 |
| 189B 为该会话实际形态 | **REFUTED** | magic@103≠1，pubkey@111 非 DER |
| 189B 为独立合法短地址变体 | **STRONG_CANDIDATE** | ol-mod `:324-341` 双形态 + native 189 路径 |
| 原生硬拒 219 | **CONFIRMED** | `codol_handshake.c:47`；`codol_network.c:411` |
| `captures/*.jsonl` 可裁决 B | **REFUTED** | 无载荷字节 |

---

## B.8 独立复核

- **输入版本一致**：与 A/C 同一 `battle_srv.log`（`3CB3E9CD…`）。
- **共享解析错误**：两脚本用**不同**切片/正则策略得到同一 219 账本，互为独立复现。
- **隐含假设**：仅"日志 hex 前缀按偏移映射到报文前 128B"——由 `battle_server.py:1458` 的 `pkt[:128].hex(" ")` 直接定义，非假设。
- **与其他工作流矛盾**：与 A（该会话 DATA 原语 SHA1+AES128）、C（219 长地址 ↔ 67B bdCommonAddr ↔ 268B/258B 记录）一致。**无矛盾。**
- **可否独立复现**：是，任一脚本可重跑得到同一账本。
- **是否超出证据**：未断言"189 是错的"（仅断言非本会话形态）；保留 U-1 来源不确定性。

---

## B.9 结论

- 冲突 B **已裁决**：观测客户端 = **219B**；189B = 短地址变体（本会话 REFUTED）。
- **可重复长度计算**：`219 = 6(头部) + 38(cookie) + 67(长地址) + 8(securityId) + 100(公钥)`；`189 = 44 + 37 + 8 + 100`。
- **兼容性含义**：原生 `n==189` 会拒绝该客户端；C#/REF/ol-mod 的 219 路径与之匹配。
- **缺失证据（若要升级到 CONFIRMED）**：一份能**独立证明来源**（真机，非回放）的同会话抓包，或客户端侧 `bdDTLSCookieEcho` serializer 的静态反汇编定位。
