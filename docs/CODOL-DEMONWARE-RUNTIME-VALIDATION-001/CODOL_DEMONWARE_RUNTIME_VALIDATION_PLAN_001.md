# CODOL Demonware Keyflow 运行时验证方案（001）

> 任务：**CODOL-DEMONWARE-RUNTIME-VALIDATION-001**
> 唯一目标：建立一份可执行、可审计、可重复的 Keyflow 验证方案，明确现有静态证据与运行时证据之间的差距，为后续互通测试提供验收标准。
> 性质：**纯静态 / 离线交付**。本文件是方案；除 G0 完整性校验外，**未执行任何运行时测试**。
> 结论边界：`KEYFLOW-EQUIVALENT` 与 `REUSE-SUPPORTED（静态）` **维持**；实时互操作 **NOT-OBSERVED（不变）**。

## 0. 目录与命名约定

沿用既有 `<TASK-NAME>-<NNN>` 目录约定（参考 `CLIENT-DEMONWARE-CODEC-KEYFLOW-001`、`CLIENT-DEMONWARE-PEER-REUSE-AUDIT-001`）：

```text
D:\BaiduNetdiskDownload\使命召唤OL\CODOL-DEMONWARE-RUNTIME-VALIDATION-001\
  CODOL_DEMONWARE_RUNTIME_VALIDATION_PLAN_001.md      <- 本文件
  CODOL_KEYFLOW_EVIDENCE_TRACE_001.csv
  CODOL_KEYFLOW_TEST_MATRIX_001.csv
  CODOL_RUNTIME_VALIDATION_GATES_001.md
  CODOL_REGISTER_GOVERNANCE_DELTA_001.md
  SHA256SUMS_RUNTIME_VALIDATION_001.txt
```

交付物采用"`CODOL_` + 全大写下划线"文件命名，与既有 `CODOL_2697_SERVER_STATIC_ANALYSIS_20261011` 下的报告命名一致；
**未新建与既有目录互不兼容的结构**，亦**未覆盖或改写任何历史证据**。

## 1. 本轮实际完成的工作

| # | 工作 | 状态 |
|---|---|---|
| 1 | 定位正式证据包与外层 SHA-256 清单，逐文件校验 | **已完成**（94/94） |
| 2 | 冻结输入基线登记（文件/版本/哈希/审计日期） | **已完成** |
| 3 | 把既有审计报告与去重/登记材料纳入输入登记 | **已完成** |
| 4 | 建立 Keyflow 证据追踪表（20 条 claim） | **已完成（静态映射）** |
| 5 | 设计验证用例矩阵（36 条用例，8 组） | **已完成（设计；未执行）** |
| 6 | 定义运行时验证门槛 G0–G5 | **已完成（定义）** |
| 7 | 登记表治理增量（Q-101 取代、Q-44 裁决建议、双计检查、口径声明） | **已完成（建议）** |
| 8 | 生成完整性清单 `SHA256SUMS_RUNTIME_VALIDATION_001.txt` | **已完成** |

**未执行**：TC-01…TC-36 任何用例；未启动客户端/服务端/模拟器；未注入；未读取运行时内存；未连接网络。

## 2. 输入基线（TASK-01）

### 2.1 正式证据包

| 项 | 值 |
|---|---|
| 目录 | `D:\BaiduNetdiskDownload\使命召唤OL\CODOL-DEMONWARE-EVIDENCE-BUNDLE-20261012\` |
| 别名 | `CODOL-DEMONWARE-BUNDLE-001`（该目录为生成脚本 + 同一份登记簿，非独立证据源） |
| 外层清单 | `SHA256SUMS_BUNDLE.txt` |
| 清单条目数 | 94 |
| 审计/冻结日期 | 2026-10-12 |
| 明细清单（另一副本） | `CODOL-Demonware-Evidence-Bundle-20261012.zip`（446,731 B，工作区根目录） |

**外层清单校验结果：94/94 命中，缺失 0，失配 0。**
（校验方式：逐行解析 `<sha256>  <相对路径>`，对包内文件复算 SHA-256；脚本化，可重复。）

### 2.2 子包内层清单校验

| 子包 | 条目 | 结果 |
|---|---:|---|
| `02_E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001/SHA256SUMS.txt` | 8 | 8/8 通过 |
| `03_E27_DEMONWARE_SERVER_PEER_DISCOVERY_001/SHA256SUMS.txt` | 8 | 8/8 通过 |
| `04_CLIENT-DEMONWARE-PEER-REUSE-AUDIT-001/SHA256SUMS.txt` | 12 | 12/12 通过 |
| `05_CLIENT-DEMONWARE-CODEC-KEYFLOW-001/SHA256SUMS.txt` | 12 | 12/12 通过 |
| **合计** | **40** | **40/40 通过** |

### 2.3 冻结输入（关键二进制）

| 角色 | 路径 | 大小 (B) | SHA-256 | 本轮复算 |
|---|---|---:|---|---|
| 客户端（恢复镜像，静态分析主样本） | `D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin` | 12,571,648 | `24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4` | 一致 |
| 客户端（打包原件，2.6.9.7） | `D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe` | 9,964,656 | `353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1` | 一致 |
| 服务端（2697 对局面） | `D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe` | 7,295,919 | `80816711946a5392abab81a625a516f24fb4d649e9b8008fc5a4e506be750ea1` | 一致 |
| 服务端（同镜像副本） | `D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe` | 7,295,919 | 同上（字节一致） | 一致 |

**版本判定**：以 `manifest.json` 版本字段 `2.6.9.7` 与镜像路径 `CODOL_2.6.9.7` 一致为准（见 `CODOL_2697_SERVER_STATIC_ANALYSIS_20261011/01_SAMPLE_IDENTITY.md`）。
**样本身份与清单声明一致，不等于已实际互通**（互通 = NOT-OBSERVED）。

### 2.4 纳入本轮的既有审计报告与去重/登记材料

| 材料 | 路径 | SHA-256（本轮复算） |
|---|---|---|
| CODEC-KEYFLOW-001 最终判定 | `CLIENT-DEMONWARE-CODEC-KEYFLOW-001/05_FINAL_VERDICT.md` | `3711462cb959199e3e5cc6e45f7217b5391cbbf9047e8b335f9555125fe08ed3` |
| PEER-REUSE-AUDIT-001 复用判定 | `CLIENT-DEMONWARE-PEER-REUSE-AUDIT-001/05_REUSE_VERDICT.md` | `c6c87cfcadad513b43ac8e084ce2f05a939c51b79b8a0d29f86278476c4df84e` |
| E-21 执行摘要（Q-44 出处） | `E21_CRYPTO_PAYLOAD_CONSUMER_ATTRIBUTION_001/E21_EXECUTIVE_SUMMARY.md` | `217e8cd0108bc197f8c503f2ea831ddf9521ae9512edcdddb671d5043a235a63` |
| E-22 登记增量 | `E22_HMAC_DIRECTION_RETURN_PATH_001/E22_UNIFIED_REGISTER_DELTA.md` | `2916f9ef335d71136694e925c5b02f56d6c5346251917cd2050c9bf3a15b2601` |
| E-23 登记增量 | `E23_BSS_INITIALIZATION_AND_DISPATCH_RECOVERY_001/E23_UNIFIED_REGISTER_DELTA.md` | `23e5f7934784cd631b16c2996ba89517fda85b06d6cb03d3ad397fec1d5dc84d` |
| E-24 登记增量 | `E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001/E24_UNIFIED_REGISTER_DELTA.md` | `bcab169a469d22eba455634239ce3f5972663d73e0202da2b65f2043f6a88804` |
| E-25 登记增量 | `E25_HANDSHAKE_RESPONSE_SEND_PATH_001/E25_UNIFIED_REGISTER_DELTA.md` | `c0908ba850b96cd097d7c1736e8cd44c4128c49c7ac35982cb0f4ba5fb0905f1` |
| E-26 登记增量 | `E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001/E26_UNIFIED_REGISTER_DELTA.md` | `9b229d164e1eb88adae2cab793914c01280d0ed53f441a84e8ad70f424649ef5` |
| E-27 登记增量 | `E27_DEMONWARE_SERVER_PEER_DISCOVERY_001/E27_UNIFIED_REGISTER_DELTA.md` | `3854da48aa01922a3f57f74100d23cffe04c2de31897486e5777785af0c95e10` |
| E-27 交叉表 | `E27_DEMONWARE_SERVER_PEER_DISCOVERY_001/E27_CLIENT_SERVER_PEER_CROSSWALK.md` | `471d3e1964683f21954f533e253c22805d7742d6fe9c70752f4bf81ea746a8eb` |
| 统一问题登记簿（Q-01…Q-111） | `CODOL-DEMONWARE-EVIDENCE-BUNDLE-20261012/00_CONSOLIDATED_QUESTION_REGISTER.md` | `57b886e2409cdf5fc3e238b342ab717cc35a9860b6cda8b8948f2e5b08175921` |
| I4 口径差异说明 | `CODOL-DEMONWARE-EVIDENCE-BUNDLE-20261012/00_REGISTER_I4_RECONCILIATION_NOTE.md` | `dd91cc431ee5e7e961bd18f01a228e353d9ba9c1cb06f1018cce24e37543b7ed` |
| 权威源账本（Q-01…Q-43） | `XVAL-02_IMAGE_INTEGRITY_AND_REGISTER_AUDIT/XVAL02_QUESTION_REGISTER_MIGRATION.csv` | `73344d87a20f4d8dfdafe31ed6b7bbf820423fbff1b10647a3c2dba3102b542f` |
| 权重/得分复算审计 | `XVAL-02_IMAGE_INTEGRITY_AND_REGISTER_AUDIT/XVAL02_WEIGHTED_SCORE_RECALCULATION.md` | `a229edae15556b3020aad48f2db947f44403fe1542be7a0400c9b95906105b48` |
| 去重先例（Q-15→Q-24、Q-22 家族合并） | 同上 §3 | 同上 |

本轮的"去重/交叉报告语义去重"输入即来自 `XVAL-02_..._WEIGHTED_SCORE_RECALCULATION.md` §3 与统一登记簿 §4 的历史变更记录；
治理增量见 `CODOL_REGISTER_GOVERNANCE_DELTA_001.md`。

### 2.5 参考实现（本工作区内，非 2697 生态内产物）

| 实现 | 路径 | SHA-256 |
|---|---|---|
| C++ `Crypto.cpp`（`deriveSessionKeys`） | `_e1_regression/ol-mod-olfinal/src/backend/Demonware/Crypto.cpp` | `4fa5f8f6a3b6fd25fa69783ef46cf586a8f9fbf605066429008af5a5b596ef9b` |
| C++ 头 | `_e1_regression/ol-mod-olfinal/src/backend/Demonware/Crypto.hpp` | `68181027499b414991eb413095644bda7c6ba945be4c0c3759cd4e02b4e13408` |
| C++ 大厅协议 | `_e1_regression/ol-mod-olfinal/src/backend/Demonware/LobbyProtocol.cpp` | `8ace124d7f8e2edf230d2c6618cd447c3eddf37fc5c4bd9fd6b89a2a05485dc9` |
| KAT / 抓包测试 | `_e1_regression/ol-mod-olfinal/tests/backend/DemonwareTests.cpp` | `230853f08f049ed7532f3e9cf180fd3e4490b25f891b101b14a0003c524e9e2f` |
| Python `codol_crypto.py` | `REF_LOBBY_KIT/codol_crypto.py` | `e836c63af75dd82ef6f3b07ef63fae48b044b3b5047336127093c92b07644607` |
| C# `CodolLocalLobbyServer.cs` | `REF_LOBBY_KIT/_ref/CodolLocalLobbyServer.cs` | `7116b5052839d55054f8b5e3443dce913c8318d10e8e2455cc33ab3afb60d58c` |

**独立性判定（关键）**：三者**互为同源派生** —— `codol_crypto.py` 自述"依据三方 `CodolLocalLobbyServer.cs` 逐字段照抄"，
C++ 与 Python 共用 `DemonwareTests.cpp` 的**同一组 KAT**。因此它们**不构成**独立外部验证（详见 §5 与门槛文档 G2）。

### 2.6 基线漂移检查

| 检查 | 结果 |
|---|---|
| 外层清单条目数 vs 包内文件数 | 94 vs 94，一致 |
| 冻结样本哈希 vs E-27 记录 | 全部一致（无漂移） |
| 统一登记簿总账 vs 逐项复算 | 634 / 350.5 / 55.28%，一致 |
| 输入版本是否变化 | **未变化** |

**结论**：输入基线**无漂移**，本轮 6 份交付物与既有历史报告属**同一基线**，不存在新旧混用。

## 3. 完整性校验结果汇总

| 校验对象 | 方法 | 结果 |
|---|---|---|
| 外层 SHA-256 清单（94 条） | 逐文件复算 | **94/94 通过** |
| 内层子包清单（40 条） | 逐文件复算 | **40/40 通过** |
| 冻结输入（4 个二进制） | SHA-256 复算 | **4/4 一致** |
| 关键参考源码（6 份） | SHA-256 复算 | 已登记（见 §2.5） |
| 历史报告（10 份） | SHA-256 复算 | 已登记（见 §2.4） |

## 4. Keyflow 证据追踪表（TASK-02）

完整表见 `CODOL_KEYFLOW_EVIDENCE_TRACE_001.csv`（20 条，字段：`claim_id,结论,证据文件,源码/函数位置,验证方法,独立性,限制,状态`）。

追踪项与任务书八项要求对应：

| 任务书要求 | claim_id | 结论摘要 | 状态 |
|---|---|---|---|
| KDF 使用 SHA-1/HMAC-SHA-1 过程 | KF-01, KF-02, KF-03, KF-04, KF-08 | transcript → SHA-1 → secret → expandKey（计数器模式） | PROVEN（静态） |
| `CLIENTCHAL`、`BDDATA` 标签及其输入输出 | KF-05, KF-06, KF-07 | 10B→16B、6B→72B；各 1 处 xref，同属 `0xAAB310` | PROVEN（静态） |
| BDDATA 72B 与 20/20/16/16 分段 | KF-09 | `[ebp-0xA8..ebp-0x60)` 四切片，方向与参考一致 | PROVEN（静态） |
| Codec A/B 变换与逆变换关系 | KF-10, KF-11, KF-12 | `out[j]=in[j]^CONST[PERM[j]]`；STORE/LOAD 同掩码 ⇒ 恒等 | PROVEN（静态, bit-exact） |
| AES 密钥及相关密钥切片 | KF-14, KF-15 | 两个 provider，setKey(16B)，AES key 不经 codec | PROVEN（静态） |
| 帧结构 `u32len｜AB｜85｜seq｜iv16｜ciphertext｜tag8` | KF-16, KF-17 | 逐字段写入点已定位；26 头 + ct + 8 tag | PROVEN（静态） |
| HMAC 覆盖范围与 8B 标签截取 | KF-18 | 覆盖 `frame[:-8]`，取前 8B 比较 | PROVEN（静态） |
| 序列号递增、异常帧、边界条件 | KF-19, KF-20 | `[+0x5D0]` 严格递增；诊断串三处已复读 | PROVEN（存在性, 静态） |

**独立性纪律（已执行）**：追踪表"独立性"列显式区分
`ARTIFACT-INDEPENDENT`（客户端二进制 vs 参考源码）、`NONE`（仅客户端单实现）、`SOURCE-SHARED`（同源派生）。
**未**把同源代码副本或重复报告计为独立外部验证。

## 5. 验证矩阵及未覆盖情况（TASK-03）

完整矩阵见 `CODOL_KEYFLOW_TEST_MATRIX_001.csv`（36 条，8 组），字段含：`输入来源,输入,预期结果,判定条件,失败分类,复现步骤,证据类型,当前状态`。

| 组 | 用例 | 覆盖主题 | 状态 |
|---|---|---|---|
| 1-KDF | TC-01..TC-06 | KDF 中间值与最终输出、截断边界 | 未执行 |
| 2-Codec | TC-07..TC-11 | 变换前后字节、逆变换、置换域、参考解码等价 | 未执行 |
| 3-AES | TC-12..TC-15 | AES 输入输出、切分边界、对齐、非法长度 | 未执行 |
| 4-Frame | TC-16..TC-18 | 编码/解码/往返、逐字节布局、抓包复现 | 未执行 |
| 5-MAC | TC-19..TC-23 | 正确/错误/截断/覆盖边界/短帧 | 未执行 |
| 6-Seq | TC-24..TC-27 | 正常/重复/跳号/回绕 | 未执行 |
| 7-Len | TC-28..TC-32 | keepalive/超长/截断/非对齐/短帧 | 未执行 |
| 8-Diff | TC-33..TC-36 | 客户端↔参考逐字节差异定位 | 未执行 |

**尚未覆盖的情况（明确列出）**
1. **无真实原始服务器样本**：全部用例只能标为**内部一致性 / 参考实现兼容性**，**不得**称为原始服务器兼容性测试。
2. **无运行时密钥样本**：KDF/codec 等价性仍为静态推论，未做 bit 级运行时比对（KF-12/KF-15 的"运行时 NOT-OBSERVED"）。
3. **回绕语义未静态闭合**：TC-27（`0xFFFFFFFF→0`）行为**待定**，需实测记录。
4. **异常帧的处置后果未定性**：KF-20 仅证"存在失败分支与诊断串"，未证"断开 vs 丢弃"及幂等性。
5. **`.tvm0` 完整语义未还原**（Q-111 BLOCKED）：不影响已闭合链（三条交集全 0），但"绝对不参与"的更强命题未证。
6. **参考实现非独立**：G2 所需"非派生实现"尚未引入。
7. **G4/G5 环境未授权**：授权隔离测试环境尚未建立。

## 6. 运行时验证门槛（TASK-04）

完整定义见 `CODOL_RUNTIME_VALIDATION_GATES_001.md`（G0–G5，含通过/失败条件、所需证据、允许结论）。

| 门槛 | 本轮状态 |
|---|---|
| G0 证据与基线完整 | **已通过** |
| G1 静态调用链及关键数据流可追踪 | **已通过（静态）** |
| G2 独立实现固定测试向量一致 | **未通过（未执行；且现有参考非独立）** |
| G3 帧编码/解码/认证行为测试 | **未通过（未执行）** |
| G4 可归档真实运行时交互证据 | **未通过（NOT-OBSERVED）** |
| G5 端到端互通可重复复现 | **未通过（NOT-OBSERVED）** |

**当前最高通过门槛 = G1（静态）。**

## 7. 登记表治理增量（TASK-05）

完整内容见 `CODOL_REGISTER_GOVERNANCE_DELTA_001.md`。要点：

1. **Q-101 取代关系**：登记 `SUPERSEDED-BY: Q-101 → Q-108`（保留 Q-101 原文/权重 8/得分 0.0）。
2. **Q-44 裁决建议**：单独提出三种口径方案（推荐 A：计入分母，采用全量逐项口径 376/57.87%），待负责人批准。
3. **重复计入检查**：列出 7 组候选重叠对（D-1..D-7），**不判定、不扣分**，供人工裁决；与 XVAL-02 已有的 Q-15→Q-24 合并先例对齐。
4. **分数口径声明**：总账 634 / 350.5 / 55.28%（两口径一致）；I4 子集双口径并列（376/57.87% 与 368/59.13%）。
5. **未变更声明**：本轮未修改任何历史条目或正式分数；所有处置均为建议。

## 8. 阻塞项与所需证据

| # | 阻塞项 | 所需最小证据 | 解锁门槛 |
|---|---|---|---|
| B-1 | 无独立非派生实现 | 一份与本工作区参考无派生关系的实现（独立重写或独立密码库封装）+ 固定向量比对记录 | G2 |
| B-2 | 无运行时密钥/帧样本 | 授权隔离环境内的运行时抓取或内存转储（含哈希与采集脚本） | G3→G4 |
| B-3 | 无真实原始服务器样本 | 2.6.9.7 原版 Demonware 服务端的原始帧样本或服务端二进制 | G4→G5 |
| B-4 | 2697 服务端生态不含 Demonware 组件 | 面向 2.6.9.7 的 Demonware 会话服务端二进制（生态内/外） | G5 |
| B-5 | 参考对端面向 1.1.1.13/3.3.3.3，地址口径不匹配 | 在 2697 恢复镜像上重新定位对端引用的客户端地址并逐项比对 | G2/G5 |
| B-6 | `.tvm0` 完整语义未还原 | `.tvm0` 解码后的逐指令语义（仅在需要更强命题时） | G1 加强（非当前阻塞） |
| B-7 | 回绕与异常帧处置未定性 | TC-27 / TC-20-TC-23 / TC-28-TC-32 实测结果 | G3 |
| B-8 | 运行时测试环境未授权 | 负责人对本地/隔离测试环境的书面授权 + 环境清单 | G4 |

## 9. 下一步唯一优先任务

**优先任务：补足 G2 的独立性 —— 引入一份与被测客户端无派生关系的独立实现，并对 KDF/Codec 固定向量做逐字节比对（执行 TC-01…TC-11）。**

理由：G1（静态）已通过，G2 是"静态结论"迈向"可验证一致性"的第一道**可本地执行**门槛，
且当前唯一硬伤是**参考实现同源**（`ol-mod` C++ / Python / C# 互为派生）。在不接触授权运行环境的前提下，
这一步即可大幅降低"自洽即正确"的风险，并直接决定 `KEYFLOW-EQUIVALENT` 能否从"静态 bit-exact"升级为"独立工具一致"。

**不作为本轮之后的优先项**：G3 的帧/序列号行为测试（可紧随 G2）、G4/G5 的运行时互通（依赖 B-2..B-4/B-8 授权与样本，须在 G2/G3 之后）。

## 10. 交付物与 SHA-256

见 `SHA256SUMS_RUNTIME_VALIDATION_001.txt`（本轮自身交付物的完整性清单）。

## 11. 最终声明

- 本任务完成**不代表**运行时互通完成。
- 本任务**未**修改正式游戏二进制，**未**覆盖已冻结文件。
- 本任务**未**伪造运行时数据、原始服务器样本或测试通过记录。
- 本轮所有"未执行"的用例一律标记为**未执行**，未写成"通过"。
- `KEYFLOW-EQUIVALENT`、`REUSE-SUPPORTED（静态）` 维持；实时互操作 **NOT-OBSERVED（不变）**。
