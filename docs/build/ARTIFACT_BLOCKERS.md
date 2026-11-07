# ARTIFACT_BLOCKERS — 目标客户端制品缺口与解除门禁所需证据

**日期**：2026-10-10
**门禁状态**：**BLOCKED（全部 6 项保持 BLOCKED）**
**本轮范围**：只登记制品来源、文件长度、SHA-256、PE 字段与只读核验结果。
**本轮未下载、未替换、未获取、未修改任何客户端制品；未修改任何期望哈希、fixture 或正式配置。**

> **纪律声明**：本文件**不得**通过修改期望值来"解除"。任何一项的解除都必须来自"重新计算哈希 == 记录哈希"这一机械事实，或来自用户显式提供的来源说明 + 完整 SHA-256。

---

## 0. 门禁总表

| # | 缺口 | 状态 | 解除条件（唯一路径） |
| --- | --- | --- | --- |
| **B1** | 可信 `out.exe` 本体缺失 | **BLOCKED** | 用户提供 `out.exe` 本体（或其来源说明 + 完整 SHA-256） |
| **B2** | 历史 SHA-256 `044C396C…257F9` 尚未对本体复核 | **BLOCKED** | 取得 `out.exe` 本体后重算 SHA-256 并逐字比对 |
| **B3** | `TimeDateStamp` / `SizeOfImage` 与该 SHA-256 无独立交叉证据 | **BLOCKED** | 在同一份可信制品上同时读出 SHA-256 与 PE 字段，并三方互证 |
| **B4** | RVA `0x0FEA20` / `0x8371A` 的预期字节未对可信目标制品复核 | **BLOCKED** | 在可信 `out.exe` 的内存镜像或文件映射上读取该两处 RVA 的字节 |
| **B5** | `E3823FD6…F37B` 属 3.3.3.3 QA 客户端，不得默认用作 OLfinal 目标哈希 | **BLOCKED（且存在未裁定的文档冲突）** | 用户显式裁定该哈希归属哪个构建；在此之前两处文档矛盾必须并列保留 |
| **B6** | 加壳候选与去壳目标的等价性 | **UNKNOWN** | 需要"同一次构建的加壳件与去壳件"同时可比，或由用户提供来源说明 |

---

## 1. B1 — 可信 `out.exe` 本体缺失

**状态：BLOCKED**

| 核验项 | 方式 | 结果 |
| --- | --- | --- |
| `out.exe` 在授权根内的存在性 | `Get-ChildItem -Recurse -File`（`E:\CODOL_SANDBOX` depth 3、`F:\桌面\ol` depth 3、`D:\BaiduNetdiskDownload\使命召唤OL\COD OL` depth 2） | **0 命中** |
| `out.exe` 在 F 的 `references/` 与 `distribution/` | 递归检索 | **0 命中** |
| 上游审计声明 | F 的 `.agents/audits/2026-10-09/artifact_provenance.json:9-13` | `"artifact": "OLFinal unpacked out.exe"`，`"status": "NOT_FOUND"`，`"reason": "bounded search over the authorised roots returned 0 out.exe"` |
| 前轮报告声明 | [CODOL_RUNTIME_BLOCKER_CLEARANCE_20261009.md](CODOL_RUNTIME_BLOCKER_CLEARANCE_20261009.md) 第 40 行 | `本机全盘 0 个 out.exe` |

**本轮独立复核的边界**：我只在三个授权根 + 上述深度内独立确认 0 命中。**全盘 0** 这一更强声明来自上游审计与既有报告，**本轮未独立重跑全盘扫描**（`D:` 已用 804 GB，全盘遍历超出本轮的只读预算）。

**解除条件**：用户提供 `out.exe` 本体，或提供其**来源说明 + 完整 SHA-256**。二者任一到达即可把 B1 从 BLOCKED 提升为"待复核"。

---

## 2. B2 — 历史 SHA-256 `044C396C…257F9` 尚未对本体复核

**状态：BLOCKED**

**完整哈希**：`044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9`

**记录位置（只读检索，本轮确认）**：

| 位置 | 行 | 原文摘录 |
| --- | --- | --- |
| `F:\...\tools\reverse\annotations\out.exe.json` | 3 | `"sha256": "044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9"` |
| `F:\...\tools\reverse\catalogs\codol_server_function_matrix.json` | 1057 | `"Addresses are for out.exe SHA256 044c396c…257f9, not the historical 3.3.3.3 catalog target."` |
| 同上 | 1117 / 1176 | `"CODOL addresses refer to out.exe SHA256 044c396c…257f9."` |
| 同上 | 1239 | `"All CODOL addresses are for out.exe SHA256 044c396c…257f9, not the historical 3.3.3.3 target."` |
| `F:\...\tools\reverse\catalogs\codol_gameplay_source_audit.json` | 3159 / 3171 | `"exact out.exe SHA044c396c...257f9"` |

**核验结果**：该哈希在仓库中**只作为"这些 RVA 所指向的目标构建"的标注**出现。**没有任何本地文件**在计算后等于该哈希（因为本机没有 `out.exe`）。因此 **B2 无法推进**。

**注意**：`codol_server_function_matrix.json` 同时被 Batch 10 报告 §3.2 指出其 `reference_builds.codol.idb_path` 指向 **3.3.3.3 QA 构建（2015-06-15）**，与源码 2026-08-18 翻转到的 `out.exe`（1649370）**不一致**。该目录级漂移与 B5 属同一类问题，已登记为跨文件发现（见 [T1_DIFF_REVIEW.md](T1_DIFF_REVIEW.md) §4.6 X-1 之外的独立事项）。

**解除条件**：取得 `out.exe` 本体后，`Get-FileHash -Algorithm SHA256` 的结果与该字符串**逐字**比对（大小写不敏感，长度必须 64）。**禁止**用"文件名相同 / FileVersion 相同 / 目录相同"替代。

---

## 3. B3 — `TimeDateStamp` / `SizeOfImage` 与该 SHA-256 无独立交叉证据

**状态：BLOCKED**

**期望值来源**（F 的实际源码，只读）：

| 常量 | 值 | 位置 |
| --- | --- | --- |
| `EngineBindings::ExpectedTimestamp` | `0x6096930A` | `F:\...\src\game_server\EngineBindings.hpp:438` |
| `EngineBindings::ExpectedImageSize` | `0x0E5D6000` | `F:\...\src\game_server\EngineBindings.hpp:439` |

**本轮新增的只读数据点（重要，但不是解除）**：

我对本机**唯一**存在的客户端候选做了独立 PE 读取：

| 字段 | 候选 A 实测 | `EngineBindings` 期望 | 比较 |
| --- | --- | --- | --- |
| `TimeDateStamp` | **`0x6096930A`**（2021-05-08 13:32:58 UTC） | `0x6096930A` | **相同** |
| `SizeOfImage` | **`0x0E659000`** | `0x0E5D6000` | **不同**（差 `0x83000` = 536,576 B） |

**如何解读（严格限制）**：
- 这**只是**"加壳候选 A 的链接时间戳与期望值相同"。它**不**证明 A 就是目标构建。
- 加壳器通常会保留原 PE 的 `TimeDateStamp`，所以"时间戳相同 + 映像尺寸更大（多了 `.tp3`/`.tvm0` 段）"与"同一构建的加壳形态"**相容**，但也与其它解释相容。
- 按 `.agents/audits/2026-10-09/artifact_provenance.json:81-85` 的 `sourceRelationRules`：**文件身份（SHA-256）、构建身份（guard/RVA）、源码兼容性（OLMod 绑定）是三项独立声明**。时间戳相同**不能**把任一项提升为已证实。

**解除条件**：在同一份**可信**制品上同时读出 SHA-256 与 `TimeDateStamp`/`SizeOfImage`，三者互证。当前**缺少**"SHA-256 = `044C396C…257F9`"的那份本体，故无法推进。

---

## 4. B4 — RVA `0x0FEA20` / `0x8371A` 的预期字节未对可信目标制品复核

**状态：BLOCKED**

**两个 RVA 的定义与期望字节（来自 F 的实际源码，只读）**：

| RVA | 语义常量 | 期望字节 | 定义位置 |
| --- | --- | --- | --- |
| `0x0FEA20` | `EngineBindings::ComFrameRva` | `55 8B EC 56 57`（5 B） | `EngineBindings.hpp:440`；前缀数组 `EngineBindings.cpp:755-757`；守卫点 `EngineBindings.cpp:3744` |
| `0x8371A` | `ClientProcessPatches::UnsignedFastfileVerificationRva` | `83 7C 24 08 01 0F 94 C0`（8 B，`cmp [esp+8],1; sete al`） | `ClientProcessPatches.cpp:207-211`；打补丁点 `ClientProcessPatches.cpp:811-831`、`1254-1261` |

**本轮对候选 A 的只读实测（RVA → 文件偏移映射，PE32）**：

| RVA | 候选 A 实测字节 | 期望字节 | 比较 |
| --- | --- | --- | --- |
| `0x0FEA20` | `03 C1 E0 06 50` | `55 8B EC 56 57` | **不匹配** |
| `0x8371A` | `00 D9 45 10 8B 4D 08 8B` | `83 7C 24 08 01 0F 94 C0` | **不匹配** |

**如何解读（严格限制）**：
- 候选 A 是**加壳**映像（段名 `.tp3`/`.tvm0`，7 段）。加壳后原始代码字节**必然**被替换，因此"字节不匹配"是**结构性必然**，**不能**作为"该候选与目标不兼容"的判据。
- 同理，**匹配**也不能作为兼容判据（除非在**去壳**映像上测得）。
- 上游审计已独立记录同类结论：`artifact_provenance.json:38-41` 记 `"packed image; 78/79 guards mismatch and the single match is a DATA constant, so file bytes cannot settle build identity"`。

**解除条件**：在**可信目标制品**（`out.exe` 本体或其内存镜像）上读取这两处 RVA 的字节，与上表期望值逐字节比对。**当前无法进行**（B1 未解除）。

**附加风险**：`0x0FEA20` 正是 `FrameHook.cpp` 实际打补丁的地址（`installFrameHook` 写入 `0xE9` 相对跳转）。F 的 `FrameHook` 修改**不改变**该 RVA 或 `HookSize`，但把失败原因细化并新增只读访问器。该改动**不在任何测试目标内**，其正确性同样受 B4 阻塞。

---

## 5. B5 — `E3823FD6…` 的归属存在未裁定的文档冲突

**状态：BLOCKED（且冲突未裁定）**

**完整哈希**：`E3823FD6AFC80FB25FA84747E6E9634707B9A0B189357A5466921CDA354AF37B`

### 5.1 两处文档给出**互相矛盾**的归属

| 来源 | 断言 | 原文 |
| --- | --- | --- |
| F 的 `.agents/audits/2026-10-09/GOLDEN_COPY_SPEC.md:29` | 该哈希是 **Golden Copy 要求的"客户端 EXE"** | `G1. 客户端 EXE SHA-256 == E3823FD6AFC80FB25FA84747E6E9634707B9A0B189357A5466921CDA354AF37B（或明确记录为另一构建并同时记录该构建哈希）` |
| F 的 `.agents/audits/2026-10-09/artifact_provenance.json:9` + [CODOL_RUNTIME_BLOCKER_CLEARANCE_20261009.md](CODOL_RUNTIME_BLOCKER_CLEARANCE_20261009.md) 第 38 行 | 该哈希的对象是 **OLFinal unpacked `out.exe`** | `"artifact": "OLFinal unpacked out.exe"`；报告写 `artifact_provenance.json:9 将该哈希的对象定义为 OLFinal unpacked out.exe` |
| **本任务的指令（§五.5）** | 该哈希**属于 3.3.3.3 QA 客户端**，**不得**默认用作 OLfinal 目标哈希 | — |

**三项声明无法同时成立**（"OLfinal 目标" vs "3.3.3.3 QA 客户端"），且**本轮没有取得任何制品**可以对它做哈希比对。

### 5.2 已登记的既有缺陷（不改写，只记录）

[CODOL_RUNTIME_BLOCKER_CLEARANCE_20261009.md](CODOL_RUNTIME_BLOCKER_CLEARANCE_20261009.md) §1.2 已记录：`GOLDEN_COPY_SPEC.md:29` 的 G1 按字面**不可满足**，因为任何打包发布的 `codoMP_client_shipRetail.exe` 都不可能等于一个"去壳 `out.exe`"的哈希；而同一文件第 48 行又把 `out.exe` 单独列出。

### 5.3 处置

- **不修改** `GOLDEN_COPY_SPEC.md` 或 `artifact_provenance.json`。
- **不采用**该哈希作为 OLfinal 目标哈希（遵任务 §五.5）。
- **不宣布**该哈希属于 3.3.3.3 QA 客户端（本轮无独立证据）。
- 冲突**并列保留**，直到用户显式裁定。

**解除条件**：用户显式说明该哈希归属哪个构建；或提供其对应制品本体以做哈希复核。

---

## 6. B6 — 加壳候选与去壳目标的等价性

**状态：UNKNOWN**

**候选 A 完整登记（本轮只读核验）**：

| 项 | 值 |
| --- | --- |
| 文件名 | `codoMP_client_shipRetail.exe` |
| 长度 | 7,841,344 B |
| SHA-256 | `36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537` |
| 本轮实测副本 1 | `E:\CODOL_SANDBOX\RUN001\codoMP_client_shipRetail.exe`（mtime 2026-09-10 00:06:54） |
| 本轮实测副本 2 | `D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe`（同上哈希） |
| 上游审计副本数 | 39（`artifact_provenance.json:25` 记 `"candidate A (39 copies)"`）—— **本轮未逐一重算 39 份** |
| PE 签名 | `0x00004550` |
| PE magic | `0x010B`（PE32） |
| Machine | `0x014C`（x86） |
| `TimeDateStamp` | `0x6096930A`（2021-05-08 13:32:58 UTC） |
| `SizeOfImage` | `0x0E659000` |
| `SizeOfHeaders` | `0x00001000` |
| `CheckSum` | `0x0078840D` |
| 段数 / 段名 | 7 / `.tp3, .tp3, .tp3, .tp3, .tp3, .tvm0, .tp3` |
| `FileVersion` / `ProductVersion` | `1649370` / `1649370` |
| `FileDescription` | `Call of Duty Online` |
| 加壳特征 | 段名 `.tp3`/`.tvm0`（TenProtect TP3 / VM0） |
| 与 `E3823FD6…F37B` 的关系 | **UNKNOWN（不可比）**。上游审计把候选 A 对 `E3823FD6…` 判为 `REJECTED`（`artifact_provenance.json:34-37`），理由是"SHA-256 不等"；但同一审计的 `sourceRelationRules` 又要求把文件身份与构建身份分开。**加壳件 vs 去壳件本就不是同类文件**，哈希不同是结构性必然 |

**候选 B 登记（仅转录上游审计，本轮未复核）**：

| 项 | 值 |
| --- | --- |
| SHA-256 | `7B31168D42A5A6BA11750D404971EE52F9FD1CAB93C56A8A85DA94AE76C41342` |
| 长度 | 7,841,344 B |
| 段 / FileVersion | `.tp3`, `.tvm0` / `1649370`（与 A 相同） |
| 上游角色 | `candidate B (1 copy)`；路径提示 `EXPERIMENT_017_BOOT_SKIP` |
| 来源 | `artifact_provenance.json:47-70` |

**为什么 UNKNOWN 无法在本轮消除**：

1. 等价性判定需要**同一构建**的加壳件与去壳件同时可比。本机**只有加壳件**（B1 未解除）。
2. 加壳映像的代码字节已被替换（B4 实测两处 RVA 均不匹配），**文件字节无法定论**。
3. `TimeDateStamp` 相同只支持"同一链接时间戳"，**不等于**"同一构建产物"。加壳器可保留该字段，其它构建也可巧合相同（`0x6096930A` 是秒级时间戳，非唯一标识）。

**解除条件**：取得去壳 `out.exe`（B1），或由用户提供"该加壳件由该去壳件加壳而来"的来源说明 + 两份完整 SHA-256。

---

## 7. 只读核验方法学（供独立复核）

本轮所有制品核验均为**只读**，未创建、未修改、未删除任何客户端文件：

| 步骤 | 方法 |
| --- | --- |
| 存在性 | `Get-ChildItem -LiteralPath <root> -Recurse -File -Depth N` |
| 长度 | `(Get-Item -LiteralPath <file>).Length` |
| SHA-256 | `(Get-FileHash -LiteralPath <file> -Algorithm SHA256).Hash` |
| PE 头 | `[System.IO.File]::Open(..., FileAccess::Read, FileShare::ReadWrite)` + `BinaryReader`；`e_lfanew` @ 0x3C → `IMAGE_NT_HEADERS` |
| RVA → 文件偏移 | 遍历段表（`VirtAddr`/`VirtSize`/`RawPtr`），命中区间后 `RawPtr + (RVA − VirtAddr)` |

**本轮未做的事**：未下载任何制品；未运行加壳器/去壳器；未修改 `EngineBindings.hpp` 的期望值；未修改 `GOLDEN_COPY_SPEC.md`；未修改 `artifact_provenance.json`；未把任何候选标记为"匹配"。

---

## 8. 关联交付

- [BASELINE_ADJUDICATION.md](BASELINE_ADJUDICATION.md) — 基准裁定与冻结规则
- [T1_DIFF_REVIEW.md](T1_DIFF_REVIEW.md) — T-1 差异与采用版本
- [T1_ACCEPTANCE_REPORT.md](T1_ACCEPTANCE_REPORT.md) — T-1 执行结果与未验证项
- [FILE_OWNERSHIP_MANIFEST.md](FILE_OWNERSHIP_MANIFEST.md) — 归属与哈希清单
- [CODOL_RUNTIME_BLOCKER_CLEARANCE_20261009.md](CODOL_RUNTIME_BLOCKER_CLEARANCE_20261009.md) — 前轮运行时阻塞清理报告（被本文件引用，未修改）
- [CODOL_SERVER_PROGRESS_20261009.md](CODOL_SERVER_PROGRESS_20261009.md) — Batch 10 评估报告（被本文件引用，未修改）
