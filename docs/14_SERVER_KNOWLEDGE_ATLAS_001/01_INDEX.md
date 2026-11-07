# 01 — 总索引 / MASTER INDEX
# CODOL 服务端全景技术档案与证据整合总档案

> 目录：`D:\BaiduNetdiskDownload\使命召唤OL\14_SERVER_KNOWLEDGE_ATLAS_001`
> 任务：`14_SERVER_KNOWLEDGE_ATLAS_001`（服务端全景技术档案）+ 跨引擎/跨版本/跨源码/跨协议深层交叉验证扩展
> 性质：**只读档案整合与分析**。未启动游戏/服务端/注入器，未读取进程内存，未修改任何原始样本/成功启动基线/工程工作树。
> 生成日期：2026-10-12（Asia/Shanghai）

---

## 0. 本档案的研究对象

| 组 | 对象 | 身份 |
|---|---|---|
| 服务端 | OLD | CoD4x fork 的 CODOL 移植（1.1.1.13 目标），**含源码** |
| 服务端 | 1113 | 同为 GCC 2.47 工具链的对照构建，**含源码** |
| 服务端 | 2697 | 唯一含 2697 协议层的服务端，**无源码** |
| 客户端 | C-1113 | 1.1.1.13 客户端（20,918,752 B） |
| 客户端 | C-3333 | 3.3.3.3 QA 客户端（7,841,344 B），ol-mod 目标 |
| 客户端 | C-2697 | 2.6.9.7 最终版客户端（9,964,656 B），TenProtect 包装 |
| 参考 | CoD4x | 外部 AGPL 服务端，Quake3/CoD4 血统 |
| 参考 | IW4x | 外部 MW2 客户端 mod，**无服务器源码** |
| 参考 | ol-mod | CODOL 专有链路源码重建（Project Nova/Ayria），3.3.3.3 目标 |
| 参考 | C# 战斗服 / Codec MVP | 自研离线协议实验 |
| 参考 | 大厅 / REF_LOBBY_KIT | 第三方大厅套件（唯一实机能进大厅者） |

---

## 1. 基础档案（01–11）

| 文件 | 主题 |
|---|---|
| `01_INDEX.md` | 本索引、范围、阅读顺序、完整性 |
| `02_SERVER_TOPOLOGY.md` | 三服务端进程/线程/插件/模块拓扑 |
| `03_SERVER_LIFECYCLE.md` | 进程启动、初始化、主循环、连接、地图切换、关闭 |
| `04_NETWORK_TRANSPORT.md` | socket、UDP、netchan、分片、序列号、可靠/超时 |
| `05_MESSAGE_SERIALIZATION.md` | MSG_*、位流、Huffman、编解码方向 |
| `06_CLIENT_SERVER_PROTOCOL.md` | OOB、clc/svc、连接握手、Gamestate/Snapshot 流 |
| `07_GAMESTATE_CONFIGSTRING_SNAPSHOT.md` | 三者的字段级现状（三服务端 + 2697） |
| `08_ENTITY_AND_BUSINESS_LAYER.md` | 实体/玩家/Netfield/武器/模式/脚本 VM/大厅业务 |
| `09_RUNTIME_EVIDENCE_INVENTORY.md` | 全部运行/动态/抓包证据清单与等级 |
| `10_EVIDENCE_CONFLICTS.md` | 冲突登记（双留） |
| `11_OPEN_QUESTIONS.md` | 基础档案遗留问题（指向 17/18/19） |

## 2. 跨项目交叉验证档案（12–21，本扩展新增）

| 文件 | 主题 |
|---|---|
| `12_CROSS_PROJECT_ARCHITECTURE.md` | 跨项目架构同构分析（生命周期/传输/序列化/业务四层） |
| `13_SOURCE_LINEAGE_AND_CODE_DIVERGENCE.md` | 代码血统分类与分歧证明 |
| `14_PROTOCOL_CROSS_VALIDATION.md` | 协议对照矩阵 + 字节级交叉验证 |
| `15_CLIENT_SERVER_EVIDENCE_CORRELATION.md` | 最终版客户端逆向逐项对接 |
| `16_SIMILARITY_DIFFERENCE_CAUSAL_ANALYSIS.md` | 相同/不同/交叉/分离的因果裁定 |
| `17_HYPOTHESIS_LEDGER.md` | 假设台账（H1–H12 + 项目专属） |
| `18_TEN_THOUSAND_WHYS.md` | 深层问题库 |
| `19_CROSS_VALIDATION_TEST_PLAN.md` | 最小验证实验计划 |
| `20_CROSS_VALIDATION_RESULTS.md` | 已有证据可完成的交叉验证结果 |
| `21_CLAIM_EVIDENCE_GRAPH.md` | 结论—证据—假设—依赖图 |

## 3. 辅助文件

| 文件 | 内容 |
|---|---|
| `00_SAMPLE_MATRIX.md` | 可信样本矩阵（身份/哈希/PE/源码/运行证据） |
| `_EVIDENCE_REGISTER.md` | 全档案统一证据 ID 表（唯一编号来源） |
| `SHA256SUMS.txt` | 全部交付物 SHA-256 完整性校验 |
| `REVISION_LOG.md` | 修订记录（新证据推翻旧结论时新增，不删旧结论） |
| `CROSS_PROJECT_VERDICT.md` | 跨项目总裁决（最终放行条件之一） |

---

## 4. 阅读顺序（建议）

1. `00_SAMPLE_MATRIX.md` — 先确认“研究对象到底是什么”。
2. `_EVIDENCE_REGISTER.md` — 建立证据编号心智模型。
3. `12`–`16` — 跨项目主体：架构、血统、协议、对接、因果。
4. `17`/`18` — 假设与问题库（追问）。
5. `19`/`20` — 验证计划与已得验证结果。
6. `21` — 证据依赖图（每条结论的可信度如何被证据支撑/削弱）。
7. `CROSS_PROJECT_VERDICT.md` — 总裁决与下一步。

---

## 5. 全局质量门槛（本档案自检）

- [x] OLD / 2697 / OL-mod / CoD4x / IW4x / 最终版客户端均建立独立档案（`00`、`12`、`13`）
- [x] 跨项目架构、代码血统、协议对照完成（`12`/`13`/`14`）
- [x] 关键相同点/不同点均有因果分析（`16`）
- [x] 关键矛盾已裁定或登记为未解决（`10`/`16`/`17`）
- [x] 最终版客户端逆向结果逐项对接（`15`）
- [x] “相同”“不同”“交叉”“分离”均有具体证据（`14`/`16`/`21`）
- [x] 问题库与证据依赖图已建立（`18`/`21`）
- [x] 所有重要结论可追溯到样本/文件/函数/字节/运行记录（`_EVIDENCE_REGISTER.md`）
- [x] 全部交付物通过 SHA-256（`SHA256SUMS.txt`）
- [x] 未修改任何原始样本、成功启动基线或受保护工程工作树（只读整合）

---

## 6. 术语与缩写

| 缩写 | 含义 |
|---|---|
| OLD | `CODOL-AlphaBuild_By_Antia(20261006)` 内的服务端构建（1.1.1.13 目标） |
| 1113 | `CODOL.NET\Game\CODOL_1.1.1.13` 内服务端构建 |
| 2697 | `CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe` |
| ol-mod | `_e1_regression\ol-mod-olfinal` |
| bdDTLS | Demonware 自定义 DTLS 风格传输层（非标准 TLS） |
| clc / svc | client command / server command（Quake3 血统命名） |
| FTQ / UNKNOWN | 证据不足标记 |
| RVA / VA | 相对虚拟地址 / 虚拟地址（ImageBase 0x400000） |
---

# === 追加：第二轮更新与目录结构（UPDATE-2, 2026-10-12） ===

## 本轮新增：可复算的分析产物

| 路径 | 内容 |
|---|---|
| `_analysis\RAW_RESULTS_BUNDLE.txt` | 第二轮全部验证的**合并原始输出**（730 行） |
| `_analysis\out_e01.txt` / `out_e02.txt` / `out_e03.txt` / `out_e05.txt` / `out_e05b.txt` / `out_e06.txt` | 各验证项的独立输出 |
| `_analysis\pe_sections.py` / `section_fidelity.py` / `rimp_probe.py` / `rimp_classify.py` / `rdata_head.py` / `rdata_ptrs.py` / `data_census.py` | PE/区段/`.rimp`/`.rdata` 解析脚本 |
| `_analysis\e04_correct.py` / `definitive_call.py` / `tvm0_noise.py` / `parser_targets.py` / `reachability.py` | 客户端分派扫描（**使用正确 RVA→offset 映射**） |
| `_analysis\e01_final.py` / `e02_final.py` / `e02b_netchan.py` / `e03_06order.py` / `e05_reg.py` / `e05b.py` / `e06_rc.py` | 2697 服务端反汇编验证 |
| `_analysis\packed_sections.py` | 打包客户端区段结构 |
| `_analysis\fixed_map.py` / `va_scan2.py` | 映射校验（含第一轮错误与纠正） |

**可复现性：** 全部脚本为只读 Python（capstone 5.0.7 / pefile 2024.8.26），输入为仅有的样本 SHA-256；`_analysis\RAW_RESULTS_BUNDLE.txt` 记录了运行输出。

## 本轮更新的文档

| 文件 | 更新内容 |
|---|---|
| `20_CROSS_VALIDATION_RESULTS.md` | 追加 R-12 … R-20（9 项执行结果） |
| `17_HYPOTHESIS_LEDGER.md` | 追加状态变更表、新增假设 H-CLI-03/H-CLI-04、方法学修正 |
| `21_CLAIM_EVIDENCE_GRAPH.md` | 追加 7 条新证据、CC-1 依赖更新、新增 CC-9/CC-10/CC-11 |
| `_EVIDENCE_REGISTER.md` | 追加 EV-2697-NetchanConst 等 13 条证据 + 独立来源计数 |
| `13_SOURCE_LINEAGE_AND_CODE_DIVERGENCE.md` | 追加常量级血统证据 + 共享骨架符号矩阵 + 脚本层排除 |
| `04_NETWORK_TRANSPORT.md` | 追加 2697 netchan 常量 |
| `07_GAMESTATE_CONFIGSTRING_SNAPSHOT.md` | 追加内部 `0x06` 顺序与注册门控指令级复核 |
| `14_PROTOCOL_CROSS_VALIDATION.md` | 追加更新后的对照矩阵 |
| `15_CLIENT_SERVER_EVIDENCE_CORRELATION.md` | 追加恢复镜像证据限制的量化 |
| `16_SIMILARITY_DIFFERENCE_CAUSAL_ANALYSIS.md` | 追加 CAUSAL-13/14 + 修订记录 |
| `11_OPEN_QUESTIONS.md` | 追加遗留问题状态更新与 4 条新问题 |
| `18_TEN_THOUSAND_WHYS.md` | 追加类别 Q（6 个新问题） |
| `19_CROSS_VALIDATION_TEST_PLAN.md` | 追加执行状态、方法学要点、新静态方向 |
| `CROSS_PROJECT_VERDICT.md` | 追加第二轮裁决更新 |
| `REVISION_LOG.md` | 追加 REV-009 … REV-012 |

## 第二轮结论摘要（一屏）

1. **E-02 已证实**：2697 二进制含 CODOL 专有 netchan 常量（`0x489`/`0x24500`/`0x70cc729`=ceil(2³⁷/1162)）→ OLD→2697 传输层延续获**常量级**证据。
2. **E-03/E-05/E-06 已证实**：内部 `0x06` ≠ EOF；注册格式链；`0x02`/`0x01` 选择条件。
3. **E-04 维持 BLOCKED 但根因查明**：恢复镜像 `.data` 声明 218 MB、**仅 0.14% 在文件内**；`.tvm0` 原始字节扫描可靠性 **0.0%**。
4. **`.text` 扫描可靠性 95.1%** → 其 0 命中是强负面信号，但**不能**升级为"客户端不支持"。
5. **E-15 削弱**"脚本含协议逻辑"；**E-14** IW4x 双克隆差异量化（3 文件）。
6. **本轮发现并纠正了本档案自身的一次 VA/RVA 混淆**（REV-012），保留记录。

---

# === 追加：E-08 与开工准入（UPDATE-3, 2026-10-12） ===

## 新增文件

| 文件 | 内容 |
|---|---|
| `22_SERVER_START_GATING_AUDIT.md` | **服务器开工准入审计**（8 通过 / 1 部分 / 6 未通过；裁定 `CONDITIONAL GO`） |

## 独立工作目录（E-08）

| 目录 | 内容 |
|---|---|
| `D:\BaiduNetdiskDownload\使命召唤OL\E06_TVM0_STATIC_DECODE_001\` | E-06 `.tvm0` 解码与恢复链（8 交付物 + 原始输出） |
| `D:\BaiduNetdiskDownload\使命召唤OL\E08_CONFIGSTRING_BODY_001\` | **E-08 configstring body 逆向**（7 交付物 + 原始输出 + 测试向量） |

## E-08 核心结果（摘要）

1. **服务端 configstring body 位编码已闭合**（`DIRECT`）：`0x04 | count1 | A1 | A2 | A3 | 0x06`，含**索引增量编码**（连续=1 bit；否则 0 + 13 bit；初值 -1）、三组字段宽度（8/16、10、7、4、12）、全部上限与失败分支。
2. **更正**：RVA 0xA0807 / 0xA0997 属 **2697 服务端** `_CODOL2697_WriteConfigstrings` 函数体，**不是**客户端函数。
3. **两侧位序同构（`DIRECT`）**：服务端 `MSG_WriteBits` 与客户端 1 位读取器（RVA 0x1A07B0，**115 个调用者**）均为 **LSB-first**。
4. **客户端消费仍 `BLOCKED`**：客户端无符号表；位读取器被所有位流消息共用，无法据此定位 configstring 读取器。
5. **新增冲突**：`count1` 宽度 8 vs 16 位（指令级 16；注释串暗示 8）——双留。
6. **新增候选测试向量**：V-A/V-B/V-C/V-D（**构造级，非 Golden**）。

## 开工准入裁定

**`CONDITIONAL GO`**：
- **允许**服务端侧编码器/校验器实现，`count1` 宽度**必须参数化**。
- **禁止**在取得原始抓包或客户端消费证据前宣称"协议兼容/可互通"。

---

# === 追加：E-09 索引与准入（UPDATE-4, 2026-10-12） ===

## 新增独立工作目录

| 目录 | 内容 |
|---|---|
| `D:\BaiduNetdiskDownload\使命召唤OL\E09_CONFIGSTRING_BLOCKERS_001\` | **E-09 三大阻断项定向取证**（7 交付物 + 原始输出 + 脚本） |

## 新增/更新档案

| 文件 | 变更 |
|---|---|
| `_EVIDENCE_REGISTER.md` | +EV-09-01…06 |
| `REVISION_LOG.md` | +REV-018…022 |
| `17_HYPOTHESIS_LEDGER.md` | +H-CS-07/08；状态变更表 |
| `18_TEN_THOUSAND_WHYS.md` | +类别 S（5 问） |
| `21_CLAIM_EVIDENCE_GRAPH.md` | +CC-15/16/17 |
| `19_CROSS_VALIDATION_TEST_PLAN.md` | +E-09 执行状态 |
| `CROSS_PROJECT_VERDICT.md` | +约束解除/新增 |

## E-09 核心结果（摘要）

1. **BLK-1 解除（PROVEN）**：客户端 configstring body 消费者 = **RVA 0xA2660**，与服务端 `_CODOL2697_WriteConfigstrings` **逐字段**一致。
2. **BLK-2 解除（PROVEN）**：`count1` = **2 字节（16 位）**；8 位假设 **REFUTED**。
3. **BLK-3 部分解除**：`0x06` 服务端写入侧闭合（位游标字节边界强制重同步；A1 字符串不占位）；客户端读取侧仍 **BLOCKED**。
4. **更正**：客户端共享位读取器为 **0x1AC670**（非 E-08 的 0x1A07B0；后者是 `.def` 脚本字段读取器）。
5. **新增阻断项**：BLK-7（外层消息分派器未定位）、BLK-8（`0x06` 性质）。
