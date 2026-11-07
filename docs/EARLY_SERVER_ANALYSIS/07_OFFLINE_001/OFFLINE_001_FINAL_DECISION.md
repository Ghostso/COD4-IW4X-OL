# OFFLINE_001 — 最终裁决与决策表

> 任务：`EARLY-SERVER-OFFLINE-VALIDATION-001`（工作流 A / B / C 的整合）。
> 输入：只读。派生脚本与报告仅写入 `EARLY_SERVER_ANALYSIS\07_OFFLINE_001\`。
> 本轮**未**启动服务端/客户端，**未**执行 `.cmd`/未知脚本，**未**修改样本/捕获/既有报告，**未**输出秘密材料。
> 状态词：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / REFUTED / NOT_OBSERVED / INSTRUMENTATION_BLOCKED。

---

## 0. 输入版本（三工作流共用，逐字节核对）

| 关键输入 | SHA-256 | 用途 |
|---|---|---|
| `REF_LOBBY_KIT\battle_srv.log` | `3CB3E9CD47472AC121F35301B59D1D9DFC7313BC689D760F6E6A546C8C1C01BA` | A（RX#5 DATA）+ B（RX#4 219B） |
| `...\build\bin\session_descriptor\session_record_258.bin` | `72ECC9E6E73C5AFA3051107E5A90AB60D9F115A787C43F8D49828B6BB654122C` | C（258B 布局） |
| `...\CODOL_Server\lobby\securitykey.bin` | `DB8A6DF1A30B0253A2FFE8D79A4DFDB0584F24E62125C5CDFCEB41BB04876A36` | C（16B 引用） |
| `...\CODOL_Server\lobby\session_desc.pickle` | `5423902CCDB43B02E1CD845F1526FED2B9C184D5126BDB64624EAE3F41CA6FDF` | C（28 字段对照） |
| 原生 `codol_crypto.c` / `codol_handshake.c` / `codol_network.c` / `codol_association.c` | `CAAD3E3C…` / `F9BE49F7…` / `FEB5BD4A…` / `3A965283…` | A/B/C 引用链 |
| C# `CodolProtocol.cs` / `Aes128.cs` / `Sha1.cs` / `SessionDescriptor.cs` / `SessionGolden.cs` | `FA06D054…` / `99927787…` / `CB18B5C3…` / `0E1A3170…` / `FE23C295…` | A/B/C |
| REF `battle_server.py` / `codol_crypto.py` | `71BB7BEB…` / `E836C63A…` | A/B/C |
| ol-mod `net_dtls_cod.cpp` / `net_dtls_cod.hpp` / `MatchmakingService.cpp` | `1EB45A43…` / `25DE3712…` / `74D96037…` | A/B/C 第三方 |
| 全部哈希 | 见 `OFFLINE_001_CHECKSUMS.txt` | — |

**三工作流使用同一批输入版本**（同一 `battle_srv.log`、同一 `session_record_258.bin`、同一批源码哈希），未发现版本漂移。

---

## 1. 最终决策表

| 问题 | 结论 |
|---|---|
| **冲突 A** | **部分裁决**。DATA 记录外层 MAC 构造 `HMAC-SHA1(key24, hdr[0:6]‖pkt[14:])[:8]` 在四份独立实现中**逐字节一致（CONFIRMED）**；真实客户端原语族 = **SHA1 派生 + AES-128 流**（**STRONG_CANDIDATE**，C#/REF/ol-mod 三实现同族 + RX#5 后 `getchallenge` 成功解密）；原生 **Tiger192/AES-192 对观测客户端 REFUTED**。**逐字节 MAC 复算 INSTRUMENTATION_BLOCKED**（缺完整 24B key / ECDH 私钥）。 |
| **冲突 B** | **已裁决**（对观测客户端）。该客户端 COOKIE_ECHO 总长 = **219B**（**STRONG_CANDIDATE**，两份独立脚本 + 偏移/长度自洽 + 后续 MAC/明文成功）；`219 = 6 + 38 + 67 + 8 + 100`；**189B = 另一条合法短地址变体**（本会话 **REFUTED**）。 |
| **会话描述符** | **已确认布局**：258B = 33 个带 tag 字段，地址 field#0 = Blob[37]，**securityKey = field#15 Blob[16] @147（负载 @153..168）**；与冻结参考**除 securityKey 外逐字节一致**。**客户端接受性 NOT_OBSERVED**。 |
| **对客户端兼容性的影响** | 原生服务端硬性要求 `n==189`（`codol_handshake.c:47`；`codol_network.c:411`）并走 **Tiger192/AES-192**，会**硬拒**本观测客户端（219B + SHA1/AES128）→ **原生路径与该客户端不兼容**。C#/REF/ol-mod 的 **219B + SHA1/AES128** 路径与之匹配。 |
| **对序列化器移植的影响** | 冲突 A/B **本身不解除**任何序列化器阻塞（序列化器阻塞在地址块 37/67 语义、258B/28 字段结构）。但**改变优先级**：序列化器应以 **219B 长地址 + SHA1/AES128** 为基线，把**原生 Tiger192/AES192 路径降为"仅参考"**；258B 记录应使用 **37B 短地址**形态，且必须与目标部署的 **16B securityKey** 一致。 |
| **后续运行验证** | **有必要，但受前置条件约束**。闭合 A 的逐字节复算需**同会话完整 24B transport key 或同期 ECDH 私钥/共享 X**；闭合 C 的客户端接受性需**真实客户端接入**。**本轮不开展**，需**另行授权**后按最小验证计划执行。 |

---

## 2. 三工作流结论与证据强度

### 2.1 冲突 A（DATA MAC）
- **CONFIRMED**：MAC 输入区间与构造在 `codol_crypto.c:65-78`（原生 `hdr[0:6]‖cipher`）、`CodolProtocol.cs:201-215`（C# `pkt[0:6]‖pkt[14:]`）、`battle_server.py:516-534`、`net_dtls_cod.cpp:269-295` 四处一致。
- **STRONG_CANDIDATE**：观测会话实际原语 = SHA1 派生 + AES-128（三条独立实现 + RX#5 MAC/解密成功链）。
- **REFUTED**：原生 Tiger192/AES-192 对**本观测客户端**成立（原生硬拒 219B；audit 自述 `Real C1 match entry is not yet verified`，`CODOL_DTLS_LOBBY_KEY_AUDIT_20260914.md:11`）。
- **INSTRUMENTATION_BLOCKED**：本会话 8B MAC 逐字节复算——日志仅存 24B key 的**前 16B**（`22d0fa6843b44afe0bedd2777d22f7c1`，`battle_srv.log:2325`），ECDH 私钥每轮随机且不落盘。
- 详见 `OFFLINE_001_A_DATA_MAC.md`。

### 2.2 冲突 B（COOKIE_ECHO 长度）
- **STRONG_CANDIDATE**：观测客户端 = **219B**（`:2324 len=219`；两脚本 `sum=219`、`equals_declared=true`、`u64@111==1`、`pubkey@119=DER`）。
- **REFUTED**：189B 为**本会话**形态（magic 应在 103，实测 `[103:111]=00 3c 01 f8…`≠1；公钥应在 111，实测非 DER）。
- **STRONG_CANDIDATE**：189B 为独立合法短地址变体（ol-mod `net_dtls_cod.cpp:324-341` 明述 219/189 皆真实）。
- 详见 `OFFLINE_001_B_COOKIE_ECHO_LENGTH.md`。

### 2.3 会话描述符（258B + 16B securityKey）
- **CONFIRMED**：258B = 33 字段，总长自洽；securityKey = field#15 Blob[16] @147；与黄金向量除 securityKey 外逐字节相同（`diff_count=15` 全在密钥负载，属参数差异）。
- **CONFIRMED**：16B securityKey 是 ECDH 派生输入的一半（`codol_crypto.c:28-37`、`codol_association.c:21,24`）。
- **CONFIRMED**：`lobby\session_desc.pickle` field#19 Blob[16] 与 `lobby\securitykey.bin` 逐字节相等（同 `DB8A6DF1…`）。
- **NOT_OBSERVED**：真实客户端接受该 258B 记录。
- 详见 `OFFLINE_001_C_SESSION_DESCRIPTOR.md`。

---

## 3. 独立复核（整合者检查项）

| 检查项 | 结果 |
|---|---|
| 是否使用相同输入版本与哈希 | **是**。三工作流共用 `battle_srv.log 3CB3E9CD…`、`session_record_258.bin 72ECC9E6…`，源码哈希一致（§0）。 |
| 是否存在共享解析错误 / 隐含假设 | **否（未发现）**。B/C 的关键解析由**两套独立脚本**（`verify_offline_001.py` 与 `verify_cookie_len_2nd.py`）分别实现并互相复现；A 的 MAC 输入区间由"原生 `hdr[0:6]‖cipher`"与"C# `pkt[0:6]‖pkt[14:]`"两处独立推导交叉印证。唯一保留的隐含假设是 `battle_srv.log` 会话来源（U-1，见 §4），已显式标注。 |
| 不同工作流结论是否互相矛盾 | **无矛盾**。A（219B 会话走 SHA1+AES128）与 B（同会话 219B）与 C（16B 密钥进 ECDH 派生）三者一致。C 记录的"258B 内嵌 37B 短地址 vs COOKIE_ECHO 67B 长地址"是**不同上下文**（ol-mod `:324-341` 明述客户端回显其被给形态），**记为待澄清项**，非矛盾。 |
| 计算结果能否由另一份独立脚本复现 | **能**。B/C 由第二实现复现；A 的"阻塞"是结构性结论（缺密钥），任何脚本都无法在无密钥下完成逐字节复算——此点本身即为结论。 |
| 结论是否超出实际证据范围 | **否**。未断言"Tiger 一定错"（仅对本观测会话不成立）；未断言"客户端一定接受 258B"（NOT_OBSERVED）；未输出任何密钥材料（仅 sha1/长度/公开前缀）。 |

### 3.1 关键前提保留（不隐藏不确定性）
- `battle_srv.log` 的真实会话来源存在 **U-1** 保留（`_BATTLE_ARCHAEOLOGY_20261005_20261008.md:419`）："docs 断言真实客户端；**日志本身无法 100% 区分**真机与实验室回放"。故 B 的最高等级取 **STRONG_CANDIDATE**（若接受 U-1 的来源判定则为 CONFIRMED）。
- `captures/*.jsonl` **不能**裁决 A/B：4 份捕获共 **11,878** 事件，`kind ∈ {task,push,auth_frame,udp,stun_reply,counter,write,handler_exception,undecodable,refused,udp_unhandled}`，`layer ∈ {lobby,seckey,stun}`，**0 个事件携带报文载荷字节**（`wiretap_report.md:185`："No game-layer events in this capture"）。原 E1/E2 计划"用 captures 裁决"的前提 **REFUTED**，改用 `battle_srv.log` 的真实会话。

---

## 4. 结论边界与仍未知项

1. **A 的逐字节 MAC**：未裁决。缺本会话（`peer=127.0.0.1:22011`，`tag=c3f2`，`seq=1`）**完整 24B transport key**，或**同期 ECDH 私钥/共享 X（28B）**。
2. **B 的"真机"来源**：为升级到 CONFIRMED，需一份**能独立证明来源**（非回放）的同会话抓包，或客户端侧 `bdDTLSCookieEcho` serializer 的静态反汇编定位。
3. **C 的客户端接受性**：NOT_OBSERVED；需真实客户端接入。
4. **地址块形态对应**：258B 记录内嵌 **37B** 短地址，而观测 COOKIE_ECHO 携带 **67B** 长地址；需实机证据闭合两者对应关系。
5. **16B 密钥一致性**：本机 258B 用 16×`0x01`，而 `lobby\securitykey.bin` 为另一份 16B 值；需确认目标运行时**应统一使用哪一份**（二者不一致会导致传输密钥分叉 → 静默丢包）。

---

## 5. 后续建议（仅建议，本轮不执行）

> 下列均为**建议**，须**另行授权**后方可执行；本轮**不开展任何运行验证**。

1. **闭合冲突 A（最高价值，前置条件明确）**
   - 在**受控单会话**中，同步记录 **ECDH 私钥/共享 X（28B）** 或**完整 24B transport key**（与 RX 序号绑定），随后离线复算 8B MAC 与 keystream，逐字节比对。这是把 A 从"部分裁决"升级到"逐字节裁决"的**唯一充分条件**。
   - 采集时不得将密钥材料写入可分发报告；仅记录复算结论与哈希。

2. **闭合冲突 B 来源（U-1）**
   - 取得一份**可独立证明来源**的真实客户端抓包（含完整载荷，非 `pkt[:128]` 截断），或对客户端 `bdDTLSCookieEcho` 构造路径做**静态反汇编**定位。

3. **闭合会话描述符接受性（C）**
   - 在真实客户端接入的受控环境中，观察客户端是否接受 258B 记录与 21/5 mission 对象（268/237/228B 变体），并记录客户端对**地址块长度（37 vs 67）**的实际要求（ol-mod 已测得 `*(MatchMakingInfo+70)==67` 的硬门槛，需在真实客户端复现确认）。

4. **序列化器移植优先级（不依赖运行验证）**
   - 立即将实现基线切换为 **219B 长地址 + SHA1/AES128**；258B 记录采用 **37B 短地址**；把原生 Tiger192/AES192 保留为"仅参考"，不作为主路径。

5. **最小运行验证的准入条件（供后续决策，本轮不启动）**
   - 前置：A 的密钥上下文采集方案就绪；一份完整载荷抓包（或静态反汇编）可用；目标运行时的 16B securityKey 已唯一确定。
   - 范围：单客户端、单会话、只读观察；**不得**在无密钥上下文记录的情况下启动，否则只能重复"INSTRUMENTATION_BLOCKED"。

---

## 6. 交付物清单

| 文件 | 内容 |
|---|---|
| `OFFLINE_001_A_DATA_MAC.md` | 工作流 A：MAC 构造一致、原语裁决、逐字节复算阻塞 |
| `OFFLINE_001_B_COOKIE_ECHO_LENGTH.md` | 工作流 B：219B 长度账本、189B 变体排除 |
| `OFFLINE_001_C_SESSION_DESCRIPTOR.md` | 工作流 C：258B 33 字段偏移表、16B securityKey 引用链 |
| `OFFLINE_001_FINAL_DECISION.md` | 本文件（决策表 + 独立复核） |
| `OFFLINE_001_CHECKSUMS.txt` | 全部输入 + 全部输出/脚本/证据的 SHA-256 |
| `_tools\verify_offline_001.py` | 主验证脚本（A/B/C，只读输入） |
| `_tools\verify_cookie_len_2nd.py` | B/C 第二独立实现 |
| `_tools\probe_lobby_descriptor.py` / `probe_lobby_descriptor2.py` | 28 字段大厅描述符复算 |
| `_tools\probe_golden_lengths.py` / `probe_mission_len.py` / `probe_mission_normal.py` / `probe_captures.py` | 黄金长度 / 228=237−9 / 地图名 / 捕获统计复算 |
| `_evidence\offline_001_evidence.json` / `offline_001_evidence_2nd.json` | 机器可读证据 |

**完成标准**：冲突 B 已获**可重复的证据级裁决**（219B，两独立脚本复现）；冲突 A 达**部分裁决**并**精确定位缺失证据**（完整 24B key / ECDH 私钥）。标准达成。
