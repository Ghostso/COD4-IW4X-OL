# 00 — 交付索引 / DELIVERABLE INDEX

**任务**：`CODOL-BATTLE-SERVER-REVERSE-COVERAGE-001` — 最终版战斗服务器：离线逆向资产盘点与实现缺口审计
**项目**：CODOL 复活项目
**生成日期**：2026-10-12（Asia/Shanghai）
**本轮性质**：**只读审计与证据整合**。未启动游戏/服务端/注入器，未读取进程内存，未修改任何原始样本、冻结基线或工程工作树。本目录仅新增 8 份交付物与 2 份哈希清单（`_evidence_hashes.tsv`、`SHA256SUMS.txt`）。
**上游基线**：`GOLDEN-LOBBY-001`（唯一有实机进大厅证据的冻结基线）、`T1_VERIFIED_BASELINE.md`、`14_SERVER_KNOWLEDGE_ATLAS_001`、`11_CUSTOM_SERVER_FEASIBILITY_001`、`12_CODEC_MVP_001`、`COMBAT_SERVER_*` 系列。

---

## 1. 交付物清单

| 文件 | 内容 | 对应阶段 |
|---|---|---|
| `00_INDEX.md` | 本索引、方法、置信等级、结论摘要 | 全部 |
| `01_REVERSE_ASSET_INVENTORY.md` | 本地资产全面盘点（路径/类型/大小/SHA-256/版本判定/分类/关联/重复与冲突） | 第一阶段 |
| `02_BATTLE_ENTRY_AND_INITIALIZATION.md` | 战斗连接与初始化链路重建（8 步、调用链、地址、数据流、证据、置信） | 第二阶段 |
| `03_BATTLE_SERVER_COVERAGE_MATRIX.csv` | 战斗服务器核心功能覆盖矩阵（网络/主循环/战斗逻辑/资源/生命周期） | 第三阶段 |
| `04_BATTLE_SERVER_CORE_ARCHITECTURE.md` | 目标架构、分层边界、消息编解码、数据流、已证与未证边界 | 第三阶段 |
| `05_SERVER_IMPLEMENTATION_GAP.md` | 现有服务端工程与参考实现对照，逐项差距与解决方式 | 第四阶段 |
| `06_NEXT_REVERSE_TASKS.md` | 必须补充的逆向问题（BLOCKS_MVP/FEATURE/IMPROVES/DEFERRED）与可执行任务 | 第五阶段 |
| `07_BATTLE_SERVER_ROADMAP.md` | 最小战斗服务器实现路线（M0–M6）+ 依赖/证据/测试/验收/阻塞 | 第六阶段 |

**哈希清单**：`SHA256SUMS.txt`（本目录交付物）、`_evidence_hashes.tsv`（55 个被引用证据文件的 SHA-256/大小/相对路径）。

---

## 2. 置信等级口径（本审计统一）

| 等级 | 含义 | 对应上游口径 |
|---|---|---|
| `CONFIRMED` | 有直接可复算证据（磁盘字节 / SHA-256 / 指令级反汇编 / 源码行号 / 真实运行日志 / 真实抓包） | VERIFIED |
| `PARTIALLY_CONFIRMED` | 仅部分路径或部分字段被证明，其余未闭合 | — |
| `INFERRED` | 由静态结构、命名或形状有依据地推断，尚无独立观察闭合 | STATIC-INFERENCE |
| `UNKNOWN` | 现有材料不足（含样本缺失、保护壳、恢复质量不足） | NOT-OBSERVED / BLOCKED |
| `NOT_REQUIRED` | 不属于当前目标范围 | — |
| `CONFLICTED` | 现有证据相互冲突；或旧结论已被推翻但保留双述 | SOURCE-CONFLICT / REFUTED |

**两条硬纪律（贯穿全部交付物）**：
1. **「服务端能写」≠「客户端能读」**；**「字段形状一致」≠「opcode 兼容」**；**「离线编码通过」≠「客户端互通」**。
2. **版本隔离**：`1.1.1.13`、`3.3.3.3 QA`、`2.6.9.7`（最终版）互为不同构建；其他 CODOL/CoD/IW4X 版本只能作参考，**不得标注为目标版本已确认**。

---

## 3. 目标与样本锚点

**目标版本**：CODOL 最终版 **2.6.9.7**（客户端 SHA-256 `35375404…14d6e1`）。
**目标战斗服务器事实源**：2697 原生服务端 `codol_dedrun.exe`（`80816711…50ea1`，无源码）+ 2.6.9.7 客户端静态证据。

| 角色 | 样本 | 结论用途 |
|---|---|---|
| 最终版客户端 | C-2697 `codoMP_client_shipRetail.exe` | 兼容目标；加壳，客户端消费链多处 `UNKNOWN` |
| 2697 原生服务端 | S-2697 `codol_dedrun.exe` | 唯一含 2697 协议层的服务端（协议事实源） |
| 旧版服务端（含源码） | S-Old / S-1113（CoD4x fork，目标 1.1.1.13） | 网络/引擎/消息层**参考实现**，非 2697 |
| ol-mod 全源码 | `_e1_regression\ol-mod-olfinal`（目标 3.3.3.3 QA） | 最完整的 CODOL 原生服务端**参考** |
| 协议逆向线 | `REF_LOBBY_KIT`（`battle_server.py`） | **唯一有真实大厅→战斗握手抓包**的实现（3.3.3.3 客户端） |
| C# 战斗服 | `CODOL-Combat-Server-v0.1` | 可用 `csc` 构建的最小实验底座 |
| 外部参考 | CoD4x_Server / iw4x-client | 骨架参考；**协议不可移植** |

---

## 4. 一屏结论

**已掌握什么**
- 2697 传输层常量（分片 1162、上限 128、29 位掩码、`ceil(2^37/1162)`）与 CODOL 自有 netchan **精确匹配**（双证）。
- 2697 服务端侧**已闭合**：可靠命令 `0x01`/`0x02` 选择条件与字段格式、gamestate/configstring/snapshot 写入链、注册门控格式链、configstring body 位编码（`count1` = 2 字节，已裁定）。
- 客户端侧 configstring body 消费者 **RVA 0xA2660** 与服务端逐字段一致（PROVEN）；客户端共享位读取器 **0x1AC670**（LSB-first）。
- 真实战斗握手的**完整字节链**已被协议逆向线记录（NAT→DTLS init→cookie→219B→114B ack→getchallenge/connect/stats/heartbeat→usercmd 14B→gamestate→snapshot）。
- ol-mod 全源码与 `DedicatedControl` 协议（ProtocolVersion 2、端口 28961/28962、`OLDC` magic、24B 头、MessageType 1–20）**现已在本工作区**（推翻 2026-10-07 的「ol-mod 源码 BLOCKED」）。

**关键缺口**
- **无任何端到端协议兼容被证明**：客户端 `0x02` 分派、`0x06` 语义、`0x03` gamestate parser、`0x04` configstring 外层分帧、snapshot 帧边界**均 `UNKNOWN`**。
- **无 2697 战斗通道抓包、无完整黄金向量**（BLK-6）。
- 客户端静态恢复镜像 `.data` 仅 0.14% 在文件内，`.tpm0/.tvm0` 未解码，`.tp3` 未归还 → 客户端侧结论上限被**结构性限制**。
- ol-mod（L1）硬阻塞：`EngineBindings::bind()` 宿主身份门禁要求去壳 `out.exe`（`SizeOfImage=0x0E5D6000`），本机仅有加壳件（`0x0E659000`）→ 28960 从未监听。
- 大厅→战斗的 **booking/DedicatedControl 应答**接入未完成；早期「boo区源码 BLOCKED」已随源码到位而消解，但**接线与实机验证仍未发生**。

**最值得优先执行的三项**
1. **取得 2697 战斗通道的真实字节证据**（同 SHA-256 客户端运行时 dump + 一条 configstring/snapshot 抓包）——一次性解除 BLK-1/2/3/5/6 与 BQ-17/21/22/23/24/25 的结构性根因。
2. **把 ol-mod 的 booking/DedicatedControl 接线打通并纳入冻洁大厅基线**（源码已在本地），解除 U-1/U-4/U-6，使「大厅→战斗」具备第一条闭环路径。
3. **把 9 个插件专属文件（31,953 行，含全部 RVA/前缀校验）纳入测试目标**，消除当前最大工程风险（插件边界零测试）。

---

## 5. 建议阅读顺序

`00` → `01`（确认对象）→ `02`（链路）→ `03`（覆盖矩阵，量化状态）→ `04`（架构边界）→ `05`（实现差距）→ `06`（下一步逆向）→ `07`（路线图）。
若只读一份：`03_BATTLE_SERVER_COVERAGE_MATRIX.csv` 是逐项状态总表；`00_INDEX.md` §4 是结论总览。

---

## 6. 全局纪律声明

- 全部结论均可追溯到 `_evidence_hashes.tsv` 中的实际文件、其行号/函数/RVA 或日志。
- 未解决项均标注状态与下一步，并对 `UNKNOWN`/`PARTIALLY_CONFIRMED`/`CONFLICTED` 做必要性分类（见 `06`）。
- 严格区分**逆向完成度**（证据）、**代码实现度**（工程）、**测试验证度**（回归/实机）。
- 不把大厅/好友/匹配平台/完整 Demonware 互通列为默认前置条件。
- 未开展高风险实验，未修改冻结基线。
- 审计结束后，除新问题直接阻塞战斗服务器实现外，不再开展与当前目标无关的泛化逆向研究。
