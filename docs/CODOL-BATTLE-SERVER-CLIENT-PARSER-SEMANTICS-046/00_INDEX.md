# CODOL-BATTLE-SERVER-CLIENT-PARSER-SEMANTICS-046

**任务:** CLIENT PARSER SEMANTICS & MOVEMENT EVIDENCE CROSS-VALIDATION
**前序:** 040 / 041 / 042 / 043 / 044 / 045
**日期:** 2026-10-13 (Asia/Shanghai)
**性质:** 只读静态取证 + 既有材料交叉验证。
未启动游戏/客户端/战斗服;无动态调试/注入/hook/运行时内存读取;
未修改原始客户端、原始战斗服、进入大厅基线、040–045 任何交付物或正式服务器源码。
全部新产物只落在本目录。

---

## 0. 一句话结论

1. **045 的接收链 `0x85D96E → 0x87BA50(select+recv) → 0x87D5A0` 判定为 `CONFIRMED_PLATFORM_PATH`(TQOS/QoS 平台层),不是游戏业务解析入口。**
   决定性证据:该链所在函数 `0x85D870` 的唯一字符串是 `udp://%s:%d`;其兄弟函数 `0x85D5A0/0x85D2E0` 构造的是
   `QOSCSPkg/QOSSSPkg` 描述符并调用 `tqos_create_protohandle`;`0x87D5A0`/`0x87C110` 是腾讯 **TDR**
   (`lib_src\tdr\tdr_net.c`)的 net-buffer 解包器,接收侧由 `QOSCSPkg` 工厂喂入。
2. **045 不能仅凭"recv 之后进入通用 decoder"推断为游戏业务协议**,因为该 decoder 是通用/共享的 TDR
   容器解包器,并**没有**任何证据把它连到游戏快照/usercmd/gamestate/configstrings 消费者。
3. **移动物理资料是项目侧参考实现 + 离线/实跑实验产物**,对 usercmd / snapshot / PlayerState 提供了
   `DIRECT_ARTIFACT_EVIDENCE`,但这些产物**不是**官方客户端反汇编,不能升级为官方内部实现证据。
4. **结论:当前证据不足以开始实现 CODOL 战斗服核心协议。** 最先需要解决的单一阻塞是
   **在官方客户端里定位并证实"游戏网络接收 → gamestate/configstring/snapshot 消费者"的实际数据流**
   (见 `09_NEXT_ACTION_DECISION.md`)。

---

## 1. 证据等级(本任务统一口径)

| 等级 | 含义 |
|---|---|
| `DIRECT_STATIC_EVIDENCE` | 原始二进制/指令/交叉引用/数据流直接支持 |
| `DIRECT_ARTIFACT_EVIDENCE` | 项目源码/协议向量/实验日志/结构化追踪直接支持,但只适用于该产物 |
| `CROSS_VALIDATED` | ≥2 类相互独立证据支持同一结论 |
| `INFERRED` | 符合现有证据但仍存在其他解释 |
| `REPORT_ONLY` | 仅见于历史报告,尚未重查原始证据 |
| `UNKNOWN` | 证据不足 |
| `BLOCKED` | 因文件/符号/映像/上下文缺失无法继续 |

**禁令(全程遵守):** 不把 `DIRECT_ARTIFACT_EVIDENCE` 提升为官方内部实现的 `DIRECT_STATIC_EVIDENCE`;
不把内存布局等同于网络线格式;不把"未找到"写成"不存在";函数名/字符串相邻/结构相似/宽度相同
均不足以为协议语义定案。

**地址约定:** 全部显式标注 `RVA`(= `VA - ImageBase`)与 `file_offset`。
S-IMG(`image_best.bin`)`ImageBase=0x00400000`,且**对文件内出现的字节 `file_offset == RVA`**。
**勘误继承:** 040–044 曾把绝对 VA 当 RVA 比对文件长(045-C1),本任务所有引用均双形式核对。

---

## 2. 输入资料

### 2.1 既有静态分析成果(040–045)

全部**实际存在**并已读取(见 `01_INPUT_INTEGRITY.md` §2):
`CODOL-BATTLE-SERVER-DLL-NETBIND-040`、`...-DLL-RECVBUFFER-TO-PARSER-041`、
`...-CLIENT-GAME-MSG-ENTRY-042`、`...-CLIENT-EVIDENCE-AUDIT-043`、
`...-CLIENT-STATIC-CLOSURE-044`、`...-CLIENT-IMPORT-IDENTITY-045`。

### 2.2 新增移动物理资料

`CODOL_MOVEMENT_PHYSICS_20261004.zip` 与其配套 `...md` **不在工作目录根**;经 Windows Recent 链接定位到
`C:\Users\Z7-CT5N1\Documents\xwechat_files\...\2026-10\CODOL_MOVEMENT_PHYSICS_20261004(1).zip`,已复制进
`_input/`。逐项哈希与内部 79 文件校验见 `01_INPUT_INTEGRITY.md`。

### 2.3 主要样本

| 编号 | 文件 | SHA-256(前缀) |
|---|---|---|
| S-IMG | `CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin` | `17cef6e0…f045` |
| S-EXE | `COD OL\codoMP_client_shipRetail.exe` | `36997674…b537` |
| S-DLL | `COD OL\codoMP_client_shipRetailBase.dll` | `ef75220d…6a20` |

---

## 3. 交付物导航

| 文件 | 内容 |
|---|---|
| `00_INDEX.md` | 本文:范围、输入、结论导航 |
| `01_INPUT_INTEGRITY.md` | 输入路径、SHA-256、ZIP 逐文件校验、缺失项 |
| `02_045_CHAIN_ATTRIBUTION.md` | **核心 A**:045 接收链业务归属裁定 |
| `03_DECODER_SEMANTICS.md` | **核心 B**:关键 decoder 边界/参数/语义 |
| `04_MOVEMENT_EVIDENCE_MATRIX.md` | **核心 C**:usercmd / snapshot / PlayerState 字段级矩阵 |
| `05_CLIENT_PATH_MAPPING.md` | **核心 C4**:官方候选路径 ↔ 项目侧映射结果 |
| `06_SIX_WAY_CROSS_VALIDATION.md` | **核心 D**:六方协议/架构对照矩阵 |
| `07_A_BLOCKERS_STATUS.md` | **核心 E**:五项 A 类问题状态与固定权重闭环率 |
| `08_TESTS_AND_HASHES.md` | 脚本清单、自检结果、输入/输出哈希 |
| `09_NEXT_ACTION_DECISION.md` | 下一任务建议、前置证据、禁止越界 |
| `evidence/` | 原始证据转储(`00_*`…`c03_*`) |
| `scripts/` | 只读分析脚本 |

---

## 4. 完成标准对照

| # | 标准 | 结果 |
|---|---|---|
| 1 | 045 链归属结论 | ✅ `CONFIRMED_PLATFORM_PATH`(§02) |
| 2 | 关键 decoder 调用关系/IO/已知语义 | ✅ §03 |
| 3 | 移动资料已证实事实/项目侧事实/推断分开 | ✅ §04 |
| 4 | usercmd/snapshot/PlayerState 字段级矩阵 | ✅ §04 |
| 5 | 不混淆内存结构/Demo 格式/网络协议 | ✅ §04 §6 |
| 6 | 六方矩阵 + 五项 A 类状态 | ✅ §06 §07 |
| 7 | 输入输出清单与哈希可复核 | ✅ §08 |
| 8 | 未改基线、未运行 | ✅ §01 §08 |
