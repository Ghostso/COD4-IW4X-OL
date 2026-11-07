# OFFLINE_001 — 工作流 A：DATA MAC 冲突裁决

> 任务：`EARLY-SERVER-OFFLINE-VALIDATION-001` 工作流 A。
> 输入：只读。派生脚本与报告仅写入 `EARLY_SERVER_ANALYSIS\07_OFFLINE_001\`。
> 本轮不启动服务端/客户端，不执行 `.cmd`/未知脚本，不修改样本与既有报告，不输出秘密材料。
> 状态词：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / REFUTED / NOT_OBSERVED / INSTRUMENTATION_BLOCKED。

---

## A.0 一句话结论

**冲突 A 为"部分裁决"。**

- DATA 记录的**外层 MAC 构造**在全部四个独立实现中**逐字节一致**（CONFIRMED）。
- 真实客户端会话实际使用的**原语族**是 **SHA1 派生 + AES-128 流 + HMAC-SHA1 截 8B**（STRONG_CANDIDATE，三条独立实现 + 一条实机 MAC 通过链）。
- 原生样本的 **Tiger192 派生 + AES-192 流** 对**本会话观测到的客户端**为 **REFUTED**（它只自洽于原生服务端自己保存的 association，从未与真实 C1 对齐）。
- **逐字节复算该会话的 8B MAC 被 INSTRUMENTATION_BLOCKED**：日志只留 24B transport key 的**前 16B**，且 ECDH 私钥每次运行随机、不落盘。缺该会话完整的 24B transport key（或同会话的 ECDH 私钥/共享 X）。

---

## A.1 冲突定义与证据来源

冲突 A（登记于 `04_REUSE\EARLY_SERVER_04_BLOCKERS.md` K2、`06_ASSESSMENT\EARLY_SERVER_06_FEASIBILITY_ASSESSMENT.md` Q4）：

| 侧 | 派生 | keystream | MAC |
|---|---|---|---|
| 原生 `codol_crypto.c` | Tiger192(x28‖security16)→key24 | AES-192-ECB，seed=Tiger192(counter LE4)，LE 自增 | HMAC-SHA1(key24, hdr[0:6]‖cipher)[:8] |
| 现有 C# `Aes128.cs`/`CodolProtocol.cs` | （由上游给出）transportKey24 | AES-128-ECB，counter=SHA1(seed6)，LE 自增 | HMAC-SHA1(key24, pkt[0:6]‖pkt[14:])[:8] |

### 证据定位（已逐条打开核对）

1. **原生原语**：`...\CODOL_Server\dedicated\src\codol\net\codol_crypto.c`
   - `:1-3` 文件头注释："SHA1/AES128 ... comments are stale: DATA uses Tiger192 key derivation and IV, AES192 CTR-LE, HMAC-SHA1 truncated to eight bytes."
   - `:18-34` `tiger()`；`:28-37` `CODOL_DeriveKey` = Tiger192(x[28]‖security[16])。
   - `:40-62` keystream：`:46` seed=counter 4B LE；`:47` `tiger(seed)`；`:49` `setkey_enc(...,192)`；`:51` AES-192-ECB；`:56` digest++ LE。
   - `:65-78` `mac()` = HMAC-SHA1(key24, header[6]‖cipher)。
2. **现有 C# 原语**：`...\CODOL-Combat-Server-v0.1\src\Codol\Aes128.cs:155-171`（counter=SHA1(seed6)，AES-128-ECB，LE 自增）；`...\src\Codol\CodolProtocol.cs:201-215`（MAC=HmacSha1(key24, pkt[0:6]‖pkt[14:])，`key16=transportKey24[0:16]`，`Seed(seq,tagLo,tagHi)` 见 `:241-244`）。
3. **参考 Python 实现**：`...\REF_LOBBY_KIT\battle_server.py`
   - `:328-336` `derive_transport_key` = SHA1(shared_x28_BE ‖ security16) ‖ 4×0x00 → 24B。
   - `:340-352` `_keystream_xor`：counter=SHA1(seed6)，AES-128-ECB，LE 自增。
   - `:516-517` / `:524-534` MAC = HMAC-SHA1(key24, pkt[0:6]‖pkt[14:])[:8]。
   - `:387-397` `read_security_key` 默认 16×0x01。
   - `:13-18` 文件头自述 DATA 帧 = `AES 流 + HMAC-SHA1 前 8B`，派生 = `SHA1 → 20B → 补 4 个 0 成 24B`。
4. **第三方实现 ol-mod**：`...\_e1_regression\ol-mod-olfinal\src\game_server\qcommon\net_dtls_cod.cpp`
   - `:197-203` `DtlsSessionKeys::derive` = SHA1(44B sharedMaterial)。
   - `:205-217` `aesKey()` = digest[0:16]；`hmacKey()` = digest20 ‖ 4×0x00 = 24B。
   - `:219-231` `iv()` = SHA1(seq‖verificationTag)；`:269-295` AES-CTR-LE + HMAC-SHA1。
   - `net_dtls_cod.hpp:18` SecurityKeySize=16；`:33` digest[20]；`:36-38` aesKey16/hmacKey24/iv。
5. **真实客户端会话**：`...\REF_LOBBY_KIT\battle_srv.log`
   - `:2324` `RX #4 peer=127.0.0.1:22011 len=219`（COOKIE_ECHO，见工作流 B）。
   - `:2325` `KEY_EXCHANGE_OK peer=127.0.0.1:22011 transport=<16B hex 前缀>`。
   - `:2327` `RX #5 ... len=54 hex=06 02 c3 f2 01 00 cb 41 89 7b 49 23 f6 94 26 00 40 c5 ...`（DATA 记录）。
   - `:2328` `RX_OOB ... cmd='getchallenge 0 "e7c8a98a6b4c2d0e"'` —— **服务端用该会话密钥对 RX#5 完成 MAC 校验 + 解密后，才读出明文 OOB**。

---

## A.2 独立离线复算（脚本与结果）

派生脚本（只读输入，仅写 `_evidence\`）：

- `_tools\verify_offline_001.py`：自实现 FIPS-197 AES-128 + SHA1/HMAC（stdlib），**不依赖** `codol_crypto.py`。
- 证据 JSON：`_evidence\offline_001_evidence.json`。

### 复算步骤（可重复）

1. 计算输入 SHA-256（见 A.4），确认与既有报告同版本。
2. `python verify_offline_001.py`。
3. 读输出：
   - `aes128_kat.ok = true`，`got = 69c4e0d86a7b0430d8cdb78070b4c55a`（FIPS-197 附录 B 官方向量，证明 AES-128 实现正确）。
   - `keystream_roundtrip = true`（XOR 自反）。
   - `workflows.A_data_mac.rx5_declared_len = 54`，`rx5_hex_count_in_log = 54`（RX#5 未被截断，全 54B 在日志内）。
   - `header`：`type_ver=06 02`，`tag_le=c3 f2`，`seq_le=01 00`，`mac8=cb 41 89 7b 49 23 f6 94`，`len_le=26 00`（=38B cipher）。
   - `transport_key_logged_prefix_line = 2325`（脚本已修正为**按 peer 关联到本会话**，非全局最后一条）。

### 复算得到的事实

- **MAC 输入规则两端等价**：原生 `hdr[0:6]‖cipher` 中 `cipher=record[16:]`，与 C#/REF 的 `pkt[0:6]‖pkt[14:]` 只差“是否含 2B len 字段”，而 len 字段在 `[14:16]` 属于 `pkt[14:]`，故三者**完全一致**：`HMAC-SHA1(key24, pkt[0:6] ‖ pkt[14:])[:8]`。→ **MAC 构造 = CONFIRMED 一致**。
- **key24 的第二半来自 16B securityKey**：`derive = HASH(shared_x28 ‖ security16)`，`key24 = digest20 ‖ 0×4`（REF/ol-mod），AES 用前 16B、HMAC 用 24B。→ 16B securityKey 直接决定 MAC 与 keystream（见工作流 C）。
- **逐字节复算被阻塞**：`transport_key_logged_prefix` 只给出 24B key 的前 16B；`battle_server.py:356/1391-1392` 每次 `main()` 调 `gen_keypair()` 重新生成随机 P-224 私钥，**私钥与共享 X 均不落盘**。缺该会话完整 24B key（或 ECDH 私钥/共享 X）→ 无法本地复算 RX#5 的 8B MAC。

### 匹配 / 失败 / 无法判定样本

| 样本 | 结果 |
|---|---|
| RX #5（54B DATA，seq=1，tag=c3f2） | **无法判定（INSTRUMENTATION_BLOCKED）**：8B MAC 已记录，但缺 24B key。 |
| RX #5 之后的 `RX_OOB getchallenge` | **匹配（间接）**：服务端 `read_data` 用本会话 key 校验 MAC 成功才输出明文 → 证明客户端与 REF/C# 侧 key 一致。 |
| `lobby/captures/*.jsonl` | **不可用**：见 A.3。 |
| 原生自测 association | **不构成本冲突的样本**：只自洽于原生服务端自己的状态。 |

---

## A.3 排除项（逐条排除解释）

1. **捕获截断**：RX#5 `len=54` 且日志内 hex 恰 54B，**未截断**（`battle_server.py:1458` 只在 >128B 时截断，RX#5 仅 54B）。→ 排除。
2. **错误分帧**：RX#5 头 `06 02` = DATA 类型/版本，`len_le=0x0026=38`，`16+38=54` 自洽。→ 排除。
3. **字段偏移错误**：`tag@2:4`、`seq@4:6`、`mac@6:14`、`len@14:16` 与 C# `:199-215`、原生 `codol_crypto.c:87-95` 完全对应。→ 排除。
4. **字节序错误**：tag/seq/len 均小端（`c3 f2`=0xf2c3=62147=serverTag，与 `TX_DTLS_INIT_ACK serverTag=62147` 一致；`seq=01 00`=1；`len=26 00`=38）。→ 排除。
5. **会话参数不一致**：RX#4（219B COOKIE_ECHO）→ RX#5（54B DATA）→ RX_OOB 同一 peer `127.0.0.1:22011`，同一 tag `c3 f2`。→ 排除。
6. **"captures 可裁决 A"的 Stage-6 前提**：**REFUTED**。四个 `wiretap-*.jsonl` 共 11,878 事件，`kind ∈ {task,push,auth_frame,udp,stun_reply,counter,write,handler_exception,undecodable,refused,udp_unhandled}`，`layer ∈ {lobby,seckey,stun}`；**无任何事件携带报文载荷字节**（`auth_frame` 仅 `b0,b1,dir,kind,layer,len,t,ts`；`udp/stun_reply` 仅 `head.b` 3B；`write` 仅 `key:"sha256:..."` 哈希）。`lobby\docs\wiretap_report.md:185` 自述 "*No game-layer events in this capture*"。→ E1 计划前提不成立，改用 `battle_srv.log` 的真实会话。

---

## A.4 输入版本与哈希（SHA-256）

| 输入 | SHA-256 |
|---|---|
| `REF_LOBBY_KIT\battle_srv.log` | `3CB3E9CD47472AC121F35301B59D1D9DFC7313BC689D760F6E6A546C8C1C01BA` |
| `...\dedicated\src\codol\net\codol_crypto.c` | `CAAD3E3CE1A8F68172C5B99F2FAD5B6BB80472D8A568C5852EC4E07F4F406FB8` |
| `CODOL-Combat-Server-v0.1\src\Codol\CodolProtocol.cs` | `FA06D0543B621216DC57C05A581EC1DCB8F00D18A9BF1368942213C75CF4A046` |
| `CODOL-Combat-Server-v0.1\src\Codol\Aes128.cs` | `999277876D728E9F800DD388F814D2A87CF97471BF35EBCC176E88D9674F422D` |
| `...\_e1_regression\ol-mod-olfinal\...\net_dtls_cod.cpp` | `1EB45A4398AAE9655A07772894D0A5A3479E25D62689605C4F9420027E28EC1F` |
| `...\net_dtls_cod.hpp` | `25DE3712BF75408300EB1BB528AF8B5F66E1886A3FBF1F693059F866882A7F0D` |
| `REF_LOBBY_KIT\battle_server.py` | `71BB7BEB85E514082B91A4925D18CB09FD07D5E8916FFA7F4FBD4A9750B47274` |
| `...\dedicated\docs\CODOL_DTLS_LOBBY_KEY_AUDIT_20260914.md` | `65B8FAB38FE5B7A065F91094348B902509427EA48E2AF832B5A77C54BE0E38A9` |

---

## A.5 证据等级汇总

| 断言 | 等级 | 依据 |
|---|---|---|
| DATA 记录外层 MAC 构造四实现一致（`HMAC-SHA1(key24,hdr[0:6]‖pkt[14:])[:8]`） | **CONFIRMED** | 四份源码逐行 + RX#5 头解析 |
| 真实客户端会话原语 = SHA1 派生 + AES-128 流 | **STRONG_CANDIDATE** | C#/REF/ol-mod 三实现同族 + RX#5 后 `getchallenge` 成功解密 |
| 原生 Tiger192/AES-192 对**观测客户端**成立 | **REFUTED** | 原生硬性 189B 与该会话 219B 不符（见 B）；原生 audit 自述未与真实 C1 对齐 |
| 该会话 8B MAC 逐字节复算 | **INSTRUMENTATION_BLOCKED** | 日志仅 24B key 前 16B；ECDH 私钥随机且不落盘 |
| `captures/*.jsonl` 可裁决 A | **REFUTED** | 无载荷字节（A.3-6） |

**原生侧关键保留**：`...\dedicated\docs\CODOL_DTLS_LOBBY_KEY_AUDIT_20260914.md:24-26` 自述仅证明"saved association 的 derived key == Tiger(saved shared-X ‖ latest lobby key)"，并**明确**"Real C1 match entry is not yet verified"（`:11`）。故 Tiger 路径从未被真实客户端证实。

---

## A.6 独立复核

- **输入版本一致**：本工作流与 B/C 使用同一 `battle_srv.log`（`3CB3E9CD…`）；A 额外用到的四份源码哈希列于 A.4。
- **共享解析错误**：MAC 输入区间由两处独立推导（原生 `hdr[0:6]‖cipher` 与 C# `pkt[0:6]‖pkt[14:]`），互为交叉校验，非单一脚本假设。
- **隐含假设**：RX#5 属于 RX#4 同一会话（同 peer、同 tag、时序相邻）——由 `:2320-2328` 的 peer/tag 连续性支撑，非假设。
- **与其他工作流矛盾**：与 B（该会话为 219B 长地址）一致；与 C（securityKey 为 16B，进 ECDH 派生）一致。**无矛盾。**
- **可否由另一脚本复现**：MAC 构造与"阻塞"结论是**结构性**的（源码 + 字段），`verify_cookie_len_2nd.py` 独立解析同 54B 头亦得到同 `mac8`。逐字节 MAC 复算则因缺 key 无法由任何脚本完成。
- **是否超出证据**：未断言"Tiger 一定错"（仅断言对本观测会话不成立）；未输出 key 材料。

---

## A.7 结论

- 冲突 A **部分裁决**：MAC 构造一致（CONFIRMED）；真实客户端原语为 SHA1+AES128（STRONG_CANDIDATE）；原生 Tiger192/AES192 对本观测客户端 REFUTED。
- **未确认**：该会话 8B MAC 的逐字节复算（INSTRUMENTATION_BLOCKED）。
- **缺失证据（精确定义）**：本会话（`peer=127.0.0.1:22011`，`tag=c3f2`，`seq=1`）的**完整 24B transport key**，或**同期 ECDH 私钥/共享 X 28B**；或任何**携带完整载荷 + 可复现密钥上下文**的抓包。
