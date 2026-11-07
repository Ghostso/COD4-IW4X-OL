# -*- coding: utf-8 -*-
import sys, os, hashlib
sys.stdout.reconfigure(encoding="utf-8")
T=os.path.dirname(os.path.abspath(__file__))
os.chdir(T)
def W(n,s):
    open(n,"w",encoding="utf-8",newline="\n").write(s)
    print("wrote",n,len(s))

W("00_INDEX.md", r"""# CODOL-BATTLE-SERVER-CLIENT-PARSER-SEMANTICS-046

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
""")

W("01_INPUT_INTEGRITY.md", r"""# 01_INPUT_INTEGRITY

**任务:** CODOL-BATTLE-SERVER-CLIENT-PARSER-SEMANTICS-046(只读)。
**日期:** 2026-10-13 (Asia/Shanghai)。

---

## 1. 工作目录

```
D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-CLIENT-PARSER-SEMANTICS-046\
    _input\     原始输入副本(只读)
    _extracted\ ZIP 解包(与 SHA256SUMS.txt 逐文件比对)
    evidence\   本任务原始证据转储
    scripts\    本任务只读分析脚本
```

**重要事实:** 该任务目录在本轮开始前**不存在**,由本任务创建。
本任务未写入 `COD OL\`、任何 040–045 目录、冻结基线或正式服务器源码。

---

## 2. 既有静态分析输入(040–045)存在性核验

| 目录 | 存在 | 关键文件抽样 |
|---|---|---|
| `CODOL-BATTLE-SERVER-DLL-NETBIND-040` | 是 | `00_INDEX.md`、`BUFFER_WRITE_AND_LENGTH_FLOW.tsv`、`SHA256SUMS.txt` |
| `CODOL-BATTLE-SERVER-DLL-RECVBUFFER-TO-PARSER-041` | 是 | `02_RECEIVE_CALLCHAIN.md`、`05_DATAFLOW_GRAPH.md` |
| `CODOL-BATTLE-SERVER-CLIENT-GAME-MSG-ENTRY-042` | 是 | `04_NET_BUFFER_READER.md`、`05_RECEIVE_PATH.md` |
| `CODOL-BATTLE-SERVER-CLIENT-EVIDENCE-AUDIT-043` | 是 | `02_DECODER_INSTRUCTION_AUDIT.md`、`10_CORRECTION_LOG.md` |
| `CODOL-BATTLE-SERVER-CLIENT-STATIC-CLOSURE-044` | 是 | `03_DECODER_CONTROL_FLOW.md`、`06_BLOCKER_REASSESSMENT.tsv` |
| `CODOL-BATTLE-SERVER-CLIENT-IMPORT-IDENTITY-045` | 是 | `02_IMPORT_IDENTITY_HYPOTHESES.md`、`03_IO_PATH_EVIDENCE.tsv` |

无缺失项。本任务中的引用均指向上述实际文件。

---

## 3. 新增移动物理资料

### 3.1 定位过程(记录"不在当前工作环境"歧义的解决)

任务书给出的入口 `CODOL_MOVEMENT_PHYSICS_20261004(1).zip` / `...md` **不在**
`D:\BaiduNetdiskDownload\使命召唤OL` 根目录。经 Windows 最近使用记录
`%APPDATA%\Microsoft\Windows\Recent\CODOL_MOVEMENT_PHYSICS_20261004.md.lnk` 解析到实际路径:

```
C:\Users\Z7-CT5N1\Documents\xwechat_files\wxid_da5kndak61n522_587e\msg\file\2026-10\
    CODOL_MOVEMENT_PHYSICS_20261004(1).zip   (393,674 B)
    CODOL_MOVEMENT_PHYSICS_20261004(1).md    (16,275 B)
```

(同目录另有 `..._20261004.zip/.md` 无 `(1)` 版本;`(1)` 与无 `(1)` 的 `.md` 内容相同、
`.zip` 时间戳不同 —— 本任务采用任务书指定的 `(1)` 版本。)

### 3.2 输入 SHA-256

| 文件 | 字节 | SHA-256 |
|---|---|---|
| `CODOL_MOVEMENT_PHYSICS_20261004(1).zip` | 393,674 | `18ca339a563469883a369781f713db6077493dccb046f15c47ada39c69cc8466` |
| `CODOL_MOVEMENT_PHYSICS_20261004(1).md` | 16,275 | `093b30412c7eacc6156d58c7f1e4cd1f707d8438906269739cb675b2499b51d0` |
| `_input\CODOL_MOVEMENT_PHYSICS_20261004.zip` | 393,674 | `18ca339a…8466`(与上一致) |
| `_input\CODOL_MOVEMENT_PHYSICS_20261004.md` | 16,275 | `093b3041…51d0`(与上一致) |

> 说明:ZIP 内 `docs/CODOL_MOVEMENT_PHYSICS_20261004.md` 与顶层 `...md` 同哈希,
> 即 `...md` 是 ZIP 内文档的副本(`CROSS_VALIDATED`)。

### 3.3 ZIP 内部完整性

`_extracted\SHA256SUMS.txt` 列 79 条;逐文件重算 `sha256`:

```
OK=79  BAD=0  MISSING=0
```

→ ZIP 内容自洽,可作为 `DIRECT_ARTIFACT_EVIDENCE` 使用。

### 3.4 ZIP 文件清单(按目录)

| 目录 | 文件数 | 代表文件 |
|---|---|---|
| (根) | 2 | `README.txt`、`SHA256SUMS.txt` |
| `docs/` | 2 | `CODOL_MOVEMENT_PHYSICS_20261004.md`(16,275 B)、`HANDOFF.md`(208,750 B) |
| `evidence/` | 7 | `battle_srv_excerpt.log`、`lobby_srv.log`、`firingrange-gamestate.bin`、`secrets_kdf.txt`、`tick_hz.txt`、`pred_lead_ms.txt` |
| `reference/` | 45 | `CodolClientCommandReader.cs`、`CodolMotionSnapshot.cs`、`CodolLocalBattleServer.cs`、`usercmd-native-vectors.json`、`playerstate-motion-trace.json`、`demo-player-fields-trace.json`、`playerstate-fields.json` … |
| `scripts/` | 10 | `battle_server.py`、`nt10.py`、`demo_parse.py`、`lobby_server.py`、`codol_crypto.py`、`run_all.py` … |

### 3.5 任务书"重点检查"入口对照

任务书列为重点的**全部存在**:`docs/CODOL_MOVEMENT_PHYSICS_20261004.md`、`docs/HANDOFF.md`、
`reference/CodolClientCommandReader.cs`、`reference/CodolMotionSnapshot.cs`、
`reference/CodolLocalBattleServer.cs`、`reference/playerstate-motion-trace.json`、
`reference/demo-player-fields-trace.json`、`reference/usercmd-native-vectors.json`、
`scripts/battle_server.py`、`scripts/nt10.py`、`scripts/demo_parse.py`、`evidence/*`、`SHA256SUMS.txt`。
**无缺失重点入口**。

### 3.6 引用了但**不在 ZIP 内**的产物(必须标注)

| 文档引用 | 状态 |
|---|---|
| `load-assets-34680\camera-motion.json`(靶场真机 1500 帧,含 snapshot/input angles) | **不在 ZIP 内** → 该对应结论为 `REPORT_ONLY`(见 §04) |
| `gameplay-playerstate.bin`(文档称与 `playerstate-fields.json` 双重证实偏移) | **不在 ZIP 内** |
| `predicted.bin` / `pred_trace.txt`(§9/§10 逐 tick 轨迹) | **不在 ZIP 内**;仅 `_an_trace.py` 与文档统计值可读 |
| `battle.log` / `n10*.txt`(launcher 与探针整轮日志) | **不在 ZIP 内**;仅 `evidence/battle_srv_excerpt.log` 摘录 |

---

## 4. 样本身份(本轮重算)

| 编号 | 文件 | 字节 | SHA-256 |
|---|---|---|---|
| S-IMG | `CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin` | 10,899,456 | `17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045` |
| S-EXE | `COD OL\codoMP_client_shipRetail.exe` | 7,841,344 | `36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537` |
| S-DLL | `COD OL\codoMP_client_shipRetailBase.dll` | 60,327,992 | `ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20` |

与 045 `01_SAMPLE_IDENTITY_AND_ADDRESS_MAPPING.md` §1 独立复算一致(`CROSS_VALIDATED`)。

S-IMG 节区(本轮独立读取):

| 节区 | VA | VSize | Raw | RSize |
|---|---|---|---|---|
| `.tp3` | `0x00001000` | `0x008A689A` | `0x00001000` | `0x008A7000` |
| `.tp3`(第2) | `0x008A8000` | `0x0016DA70` | `0x008A8000` | `0x0016E000` |
| `.tp3`(第3) | `0x00A16000` | `0x0DBB1CC0` | `0x00A16000` | `0x00062000` |
| 其余 4 节 | `0x0E5C8000`+ | — | `0x00A78000`+ | — |

> **注意:** 本任务所有代码地址落在**第1节区**(`file_off==RVA`),字符串落在第1/第2节区。
> **第3节区 `RSize=0x62000`**,故 `RVA ≳ 0x00A78000` 不可读 —— 这解释了 043/044 的
> 部分"覆盖缺口"表述,但**不**适用于本任务引用的地址。

---

## 5. 缺失/受限项汇总

| 项 | 状态 | 影响 |
|---|---|---|
| 040–045 报告 | 全部存在 | 无 |
| 移动物理 ZIP 及其 79 文件 | 全部存在且哈希通过 | 无 |
| 移动文档引用的 `camera-motion.json` 等外部产物 | **缺失** | 相关结论最高只能 `REPORT_ONLY` |
| 游戏业务 netchan 消费链的原始证据 | 未在现有映像中闭合 | 见 `02`/`09` |
| 官方 TDR/usercmd/snapshot 结构定义(符号) | 缺失 | 语义靠推断,见 `03`/`04` |
""")
print("DONE")
