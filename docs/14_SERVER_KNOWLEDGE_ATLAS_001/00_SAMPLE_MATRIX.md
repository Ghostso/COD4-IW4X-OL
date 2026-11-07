# 00 — 样本矩阵 / SAMPLE MATRIX（阶段 A）

> 归属：`14_SERVER_KNOWLEDGE_ATLAS_001`（服务端全景技术档案与证据整合总任务）+ 本扩展任务
> 生成日期：2026-10-12（Asia/Shanghai）
> 性质：**只读档案整合**。未启动游戏/服务端/注入器，未读取进程内存，未修改任何原始样本、成功启动基线或工程工作树。
> 上游任务号：`14_SERVER_KNOWLEDGE_ATLAS_001`；本扩展覆盖 OLD / 2697 / OL-mod / CoD4x / IW4x / 最终版客户端。

---

## 0. 证据等级约定（全档案统一）

| 等级 | 含义 |
|---|---|
| `VERIFIED` | 有直接、可复算的证据（磁盘字节、SHA-256、指令级反汇编、源码行号、运行日志） |
| `STATIC-INFERENCE` | 由静态结构/命名/形状有依据地推断，尚未由独立观察闭合 |
| `NOT-OBSERVED` | 本项目当前没有运行时/互通/抓包观察 |
| `BLOCKED` | 因样本缺失、保护壳、恢复质量或工具条件不足而无法闭合 |
| `REFUTED` | 已被现有证据推翻 |
| `SOURCE-CONFLICT` | 两份本地材料互相冲突，双方均保留 |

**纪律：** “服务端能写” ≠ “客户端能读”。任何跨端结论在缺少独立客户端证据时必须保留 `NOT-OBSERVED` 或 `BLOCKED`，不得升级为 `VERIFIED`。

---

## 1. 服务端 / 引擎样本总表

| ID | 样本 | 路径 | 大小(B) | SHA-256 | 等级 |
|---|---|---|---|---|---|
| S-Old | OLD 原生服务端 `codol_dedrun.exe` | `D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\dedicated\bin\codol_dedrun.exe` | 8,469,493 | `28366ae992310bfe41d3c8975ec8dbc36e4de202ce438c1266e1a09e335dd98a` | VERIFIED |
| S-Old-Next | OLD `codol_dedrun_next.exe` | 同目录 | 8,469,493 | 与 S-Old **逐字节相同** | VERIFIED |
| S-1113 | 1.1.1.13 服务端 `codol_dedrun.exe` | `D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_1.1.1.13\CODOL_Server\dedicated\bin\codol_dedrun.exe` | 8,622,389 | `a96c5dfb5386f166a0e1d4262b8fdecf9835b856cf1a863f891ead4eda5cb6e9` | VERIFIED |
| S-2697 | 2697 原生服务端 `codol_dedrun.exe` | `D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe` | 7,295,919 | `80816711946a5392abab81a625a516f24fb4d649e9b8008fc5a4e506be750ea1` | VERIFIED |
| S-2697-Mirror | 2697 服务端镜像副本 | `D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe` | 7,295,919 | 与 S-2697 **逐字节相同** | VERIFIED |

**关键结论：** S-Old、S-1113、S-2697 是 **三个互不相同的构建产物**（大小、SHA-256、节区、导入、符号、字符串均不同）。不能因“都是 `codol_dedrun.exe`”或“同一引擎家族”而视为同一构建。

---

## 2. 客户端样本总表（必须严格区分）

| ID | 版本 | 路径 | 大小(B) | SHA-256 | 打包/形态 | 等级 |
|---|---|---|---|---|---|---|
| C-1113 | 1.1.1.13 | `...\CODOL-AlphaBuild By Antia\CODOL_Client\codoMP_client_shipRetail.exe` | 20,918,752 | `904436480938632a856b39dea73fb94c9682b5a0ebf7fa619ecd5dd5475ed3b6` | 早期客户端 | VERIFIED |
| C-3333 | 3.3.3.3（QA / title 1004） | `codoMP_client_shipRetail.exe`（ol-mod 运行分发目标） | 7,841,344 | `36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537` | FileVersion 1649370；主 DLL `codoMP_client_shipRetailBase.dll` 60,327,992 B | VERIFIED |
| C-2697 | 2.6.9.7（最终版兼容目标） | `D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe` | 9,964,656 | `353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1` | TenProtect 包装；仅导入 `codoMP_client_shipRetailBase.dll` ordinal `#1` | VERIFIED |
| C-2697-Rec | 客户端静态恢复镜像 | `D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin` | 12,571,648 | `24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4` | aplib 静态恢复镜像，**非运行时 dump** | VERIFIED(文件) / BLOCKED(运行时等价性) |
| C-2697-Manifest | 启动器清单 | `D:\BaiduNetdiskDownload\CODOL_2697_Launcher\manifest.json` | 1,558 | `34017bf787800678a66d277520869873c3352c713da883e9dce2d348f669da00` | version `2.6.9.7`；`original_exe_sha256` 与 C-2697 一致 | VERIFIED |

### 2.1 最终版客户端的“发行 / 去壳 / 恢复 / 运行时”四态区分（任务硬要求）

| 形态 | 对象 | 状态 |
|---|---|---|
| 发行版（shipped） | C-2697（`.exe`，TenProtect 包装） | VERIFIED |
| 去壳/恢复镜像 | C-2697-Rec（`.bin`，aplib 静态恢复） | VERIFIED（文件） / 运行时映射等价性 BLOCKED |
| 运行时镜像 | 同 SHA-256 客户端的运行时解包内存 dump | **不存在**（BLOCKED） |
| 恢复修复记录 | `.rimp`（RVA `0xDC11000`）、`.tvm0`（RVA `0xD958000`） | 存在但未完全还原，见 `21` 依赖图 |

### 2.2 明确的样本身份告警

- `C-3333`（3.3.3.3，7,841,344 B）与 `C-2697`（2.6.9.7，9,964,656 B）**不是同一客户端**，`C-1113` 又是第三个。任何把 3.3.3.3 结果直接套到 2.6.9.7 上的结论都必须标注 `SOURCE-CONFLICT` 风险。
- `DEV-BOOKING` 记录：`CLIENT_SHA256 = 36997674...`（C-3333）。`CODOL_2697` 记录：`original_exe_sha256 = 35375404...`（C-2697）。**两者并存，不得混用。**

---

## 3. 源码 / 仓库样本矩阵

| ID | 项目 | 仓库（本地路径） | 分支 | HEAD 提交 | 上游 | 语言/构建 | 许可证 | 等级 |
|---|---|---|---|---|---|---|---|---|
| R-OldSrc | OLD 附带源码（CoD4x fork 的 CODOL 移植） | `...\CODOL_Server\dedicated\src\` | 无有效提交（打包） | — | Id / Ninja / TheKelm（CoD4x 血统） | C/C++，MSYS2 | AGPL-3.0（含 Id GPL 部分） | VERIFIED |
| R-OlMod | ol-mod / ol-mod-olfinal | `D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal` | `OLfinal-live` | `2a75bdd8872bb9f54006382a924c3006ec9affc2` | `https://github.com/CODOL-EMU/ol-mod-olfinal.git` | C++ / xmake / MSVC x86 | 见仓库 LICENSE | VERIFIED |
| R-Cod4x | CoD4x_Server | `D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\_lineage021\CoD4x_Server` | `master` | `ddd65fce1a1093017bad2dbb6840d75d11c0d56f`（2026-09-18） | `https://github.com/callofduty4x/CoD4x_Server` | C，GNU make，`cod4x18_dedrun` | AGPL-3.0 | VERIFIED |
| R-IW4x-A | IW4x client（DEV-BOOKING 克隆） | `...\DEV-BOOKING\_lineage021\iw4x-client` | `main` | `d1b175da1a25d31043246de103a702b206269e5a`（2026-09-20） | `https://github.com/IW4x/iw4x-client` | C++20，premake5，x86，**只产出 DLL** | 见仓库 | VERIFIED |
| R-IW4x-B | IW4x client（独立克隆） | `D:\BaiduNetdiskDownload\使命召唤OL\IW4X\Client核心代码\iw4x-client` | `main` | `0699a7e5716ded53bcfa6748bcb89a535f8f39f0`（2026-09-17） | `https://github.com/iw4x/iw4x-client.git` | 同上 | 见仓库 | VERIFIED |
| R-IW4x-Raw | iw4x-rawfiles | `...\DEV-BOOKING\_lineage021\iw4x-rawfiles` | — | — | `iw4x/iw4x-rawfiles` | 数据/二进制 | — | **空克隆（0 文件）**——缺口 |
| R-CSharp | 独立 C# 战斗服 | `D:\BaiduNetdiskDownload\使命召唤OL\CODOL-Combat-Server-v0.1` | 非 git | — | 自研（未复制上游） | C#（22 源文件） | 见 README | VERIFIED |
| R-Codec | Codec MVP 工作副本 | `D:\BaiduNetdiskDownload\使命召唤OL\12_CODEC_MVP_001\worktree\CODOL-Combat-Server-v0.1` | 非 git | — | R-CSharp 派生 | C#（24 源文件） | 同上 | VERIFIED |

### 3.1 IW4x 双克隆告警（重要）

本地存在 **两份 `iw4x-client` 克隆，HEAD 不同**（`d1b175da…` vs `0699a7e5…`）。这满足任务书“不能把同名项目/同一引擎家族/相同目录结构视为同一构建”的约束：

- 两者都叫 `iw4x-client`，都来自 `iw4x/iw4x-client`，但**提交号不同**；
- 任何引用 IW4x 具体行为的结论都必须绑定到**具体克隆与其 HEAD**；
- 未能建立两者差异清单 → 记为 `BLOCKED`（见 `17_HYPOTHESIS_LEDGER.md` H-IW4X-DUAL）。

### 3.2 CoD4x / IW4x 完整性缺口（禁止联网补全）

| 缺口 | 影响 | 处置 |
|---|---|---|
| 2697 服务端源码本地不可得（旧包 `grep 2697` = 0 命中） | 2697 层只能用反汇编 | `BLOCKED`，保留 |
| `iw4x-rawfiles` 本地为空克隆（0 文件） | 无法读取 `iw4x.exe`（3,932,160 B）与默认 cfg/playlists | `BLOCKED`，保留 |
| IW4x **没有专用服务器源码** | IW4x 只能作客户端/信封参考 | `REFUTED` “IW4x 提供服务器源码” |
| `CoD4x_Server` 浅克隆（非完整历史） | 无法做完整提交谱系比对 | `PARTIAL` |

> 本任务禁止联网。以上缺口**不得**通过下载新源码填补；若后续允许外部资料，必须另行记录来源与版本，且不得冒充本地实测证据。

---

## 4. 可执行文件/组件总表（非主 EXE）

| 对象 | 路径 | 大小(B) | SHA-256 | 等级 |
|---|---|---|---|---|
| 2697 `client_room2697.dll` | `...\server2697\client_room2697.dll` | 184,832 | `120c4cfdd79a9a38d992598c30af3c5cabe754e7b3d17614074b4b8026ffc3a7` | VERIFIED（与 manifest 一致） |
| 2697 `client_native_loopback.dll` | `...\server2697\client_native_loopback.dll` | 125,440 | `53c6fbe264defc06629fef06f43a1ddd82fda716439432c354b5eb2ee4074829` | VERIFIED（与 manifest 一致） |
| 2697 loopback guard | `...\server2697\client_loopback_guard.exe` | 242,176 | — | VERIFIED（存在） |
| 2697 注册导出 | `...\server2697\evidence\client-registration2697.txt` | 2,976 | `4F1B4A38D8088FDCF650BE83BBAAE0A5D34D2A0550C592609BECFAD3AC289E2C` | VERIFIED |
| C# 战斗服构建产物 | `...\CODOL-Combat-Server-v0.1\build\bin\CODOLCombatServer.exe` | 126,464 | `3FA92E97453F298A27AF5CF9EC0BF235100F9B18F2962723EA43A5A7297BB378` | VERIFIED |
| 2697 运行时资源 | `...\server2697\runtime-assets\` | 11,033 files / 1,797,434,023 | 目录级统计 | VERIFIED（目录清单，未逐文件解析） |
| 2697 脚本 | `...\server2697\scripts\` | 1,341 files / 19,154,634 | 目录级统计 | VERIFIED（目录清单，未逐文件解析） |

---

## 5. PE 元数据对照（三大服务端）

| 维度 | S-2697 (NEW) | S-Old (OLD) | S-1113 |
|---|---|---|---|
| Machine / Subsystem | I386 / GUI(2) | I386 / GUI(2) | I386 / GUI(2) |
| ImageBase / EntryPoint | 0x400000 / 0x14e0 | 0x400000 / 0x1480 | 0x400000 / 0x14e0 |
| SizeOfImage | 0x15cf0000 | 0x13f6d000 | 0x13f6c000 |
| Characteristics | 0x326 | 0x126 | 0x326 |
| DllCharacteristics | 0x140 | 0x100 | 0x140 |
| Linker | 2.47 | 2.30 | 2.47 |
| 编译器串 | MSYS2 GCC 16.2.0 | GCC (ld 2.30) | MSYS2 GCC 16.2.0 |
| 节区数 | 11 | 20（含 `.CRT` + 编号节） | 11 |
| Imphash | `5298c76ec6910429495ead35879da26c` | `506faee6444b112462fb1301d26bca17` | `d5a1b1cde88e9254617905bdd9068eb1` |
| 导出 `Plugin_*` | 185 | 185 | 185 |
| 导入函数总数 | 291 | 297 | 305 |
| 符号（去重） | 36,980 | 46,160 | 46,707 |
| 字符串条数 | 62,147 | 72,859 | 71,857 |
| 附带源码 | 否 | 是（24.4 MB） | 是（与 OLD 同源，1 文件差异） |

**STATIC-INFERENCE：** S-2697 与 S-1113 出自同一代工具链/构建配置（EntryPoint、Characteristics、节区数完全一致）；S-Old 属上一代构建。版本判定以**代码/符号/字符串差异**为准，**不以 PE 时间戳**（S-2697 时间戳晚于 S-Old 但代码更“新层”）。

---

## 6. 运行证据登记

| 对象 | 运行证据 | 等级 |
|---|---|---|
| OLD (S-Old) | `qconsole.log` running=1 bots=12，humans=0 | VERIFIED（历史日志） |
| OLD (S-Old) 与真实 C1 互通 | 作者自述 “incomplete port, not a playable CoDOL server”；`CODOL_PORT.md` 列 6 项未完成 | VERIFIED（自述）/ REFUTED（可玩） |
| 2697 (S-2697) | 无运行时观测（未启动） | NOT-OBSERVED |
| C-2697 | 无运行时观测（未启动）；恢复镜像非运行时 dump | NOT-OBSERVED / BLOCKED |
| C-3333 大厅 | 2026-10-05 16:36 首次进入正式大厅（GOLDEN-LOBBY-001 冻结） | VERIFIED（实机记录） |
| OL-mod 双客户端 | 仓库自述 two-real-client Nuketown FFA / Factory 通过 | [文档声明]，`.runtime/natural-match` 证据目录本地不存在 → 不可本机复现 |

---

## 7. 样本矩阵结论

1. 研究对象共 **3 个服务端构建**（OLD / 1113 / 2697）、**3 个客户端版本**（1.1.1.13 / 3.3.3.3 / 2.6.9.7）+ **1 个恢复镜像**，**6 类源码/仓库**，全部已登记哈希与身份。
2. OLD 与 1113 附带源码且高度同源（仅 `g_sv_main.c` 玩法改动）；2697 **无源码**。
3. OLD/1113 的源码是 **CoD4x fork 的 CODOL 移植**，不是 Intel/Infinity Ward 原始泄漏源码，也不是 IW4x。
4. OL-mod 是 **CODOL 专有链路的源码重建**（Project Nova / Ayria），**不基于 IW4x**；但它**不是** 2697，目标客户端是 3.3.3.3。
5. CoD4x 与 IW4x 是**外部参考**，各有明确缺口（CoD4x 浅克隆；IW4x 无服务器源码、空 rawfiles、双克隆 HEAD 不同）。
6. 最终版客户端 2.6.9.7 的**运行时镜像不存在**，`.tp3/.tvm0/.rimp` 恢复问题构成结构性证据限制（见 `21`）。

---

## 8. 与其它档案的引用关系

- 样本身份细节 → `12_CROSS_PROJECT_ARCHITECTURE.md` §1
- 源码血统 → `13_SOURCE_LINEAGE_AND_CODE_DIVERGENCE.md`
- 协议字节 → `14_PROTOCOL_CROSS_VALIDATION.md`
- 客户端对接 → `15_CLIENT_SERVER_EVIDENCE_CORRELATION.md`
- 因果解释 → `16_SIMILARITY_DIFFERENCE_CAUSAL_ANALYSIS.md`
- 假设台账 → `17_HYPOTHESIS_LEDGER.md`
- 问题库 → `18_TEN_THOUSAND_WHYS.md`
- 验证计划 → `19_CROSS_VALIDATION_TEST_PLAN.md`
- 验证结果 → `20_CROSS_VALIDATION_RESULTS.md`
- 证据图 → `21_CLAIM_EVIDENCE_GRAPH.md`