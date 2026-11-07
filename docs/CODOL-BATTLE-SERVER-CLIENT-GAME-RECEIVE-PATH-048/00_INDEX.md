# 048 — CODOL 官方客户端游戏网络接收路径闭环

**任务编号:** `CODOL-BATTLE-SERVER-CLIENT-GAME-RECEIVE-PATH-048`
**承接:** 040–046(静态取证) / 047(工程基线)
**日期:** 2026-10-14 (Asia/Shanghai)
**性质:** 只读静态逆向 + 047 工程衔接。

未启动 CODOL 客户端或战斗服;未做动态调试 / 注入 / hook / 运行时内存读取;
未修改最终客户端、进入大厅基线或 040–046 任何历史产物。所有新产物仅落于本目录,
以及 047 工程的一条独立开发分支 `048/analysis-adapters`。

---

## 0. 四问直答

**A. 是否已经证明最终 CODOL 的「游戏网络接收 → 解析 → 分派 → 游戏状态消费者」链?**
**没有。** 该链**未闭环**。本轮拿到的是:
- 一批**可复核的接收候选**(P4/P5/TQOS)及其 socket API、调用者、缓冲区流向;
- 连接无关(connectionless / OOB)**握手层的完整命令词表 + 收发方向 + 客户端自身分派比较点**;
- 一条明确结论:连接无关(握手)层**可以**开始实现;in-match 层(opcode / gamestate /
  configstring / snapshot / reliable)**仍无接收→消费者的指令级证据**。

**B. 如果已证明,第一项应立即实现的协议模块?**
链未闭环,但**唯一达到实现条件的模块**是:
`握手与连接状态(Connectionless / OOB)`。
证据:见 `03_STRING_TO_HANDLER.md` §3 与 `06_PROTOCOL_MODULE_READINESS.md` §2。该模块的
词表方向来自客户端自身比较点(`0x1C13A0`),不是项目侧假设。

**C. 若未证明,最小断点在哪里?**
**最小断点 = in-match(连接建立之后)的接收→消费者边。**
已证实:OOB 握手层存在且可读;`recv/recvfrom/select` 的调用点已全部枚举。
未证实:哪一条 `recv` 缓冲区进入 in-match 消息解析(opcode),再进入 `CA_GAMESTATE` /
`gamestateupdate %d` / `ExpectedNetConfigStringMismatch` 消费者。
**下一步定向突破**(唯一优先目标)见 `10_NEXT_ACTION_DECISION.md`。

**D. 047 工程本轮实际发生了什么?**
新增 5 个 C# 源文件(2 个 Analysis 适配层 + 1 个 FinalCodol opcode 分派器 + 1 个连接无关
命令词表 + 1 个连接无关文本解码器),测试从 **31 项扩到 39 项,全绿**;
Release 构建 **0 warning / 0 error**;040–046 历史校验 **547 文件 0 失败**;
commit 基线 `a9f0314` → 本分支 `8f3e331`。
所有新增线上格式代码都带证据等级,未知 opcode 一律显式拒绝。

---

## 1. 证据等级(沿用 046 口径,未改定义)

| 等级 | 含义 |
|---|---|
| `DIRECT_STATIC` | 原始二进制字节 / 指令 / 交叉引用 / 数据流直接支持 |
| `DIRECT_ARTIFACT` | 项目源码 / 向量 / 追踪直接支持,但只对该产物成立 |
| `CROSS_VALIDATED` | ≥2 类独立证据支持同一结论 |
| `INFERRED` | 符合证据但仍有其他解释 |
| `REPORT_ONLY` | 仅见于历史报告,本轮未重查 |
| `UNKNOWN` | 证据不足 |
| `BLOCKED` | 因缺失输入/符号/映像无法继续 |

## 2. 地址口径(重要)

- 恢复映像 `image_best.bin`:`ImageBase = 0x00400000`,且**文件内 `file_offset == RVA`**。
- 因此本报告同时给出 `RVA` 与 `VA = RVA + 0x400000`;凡引用磁盘 `codoMP_client_shipRetail.exe`
  的原始偏移时单独标注 `disk_offset`。
- 磁盘 EXE 为腾讯 `.tp3/.tvm0` 加壳;第一代码节在磁盘上被压缩,`image_best.bin` 是**已解包的
  运行时映像**(见 `01` §4 的同一性验证)。

## 3. 交付物导航

| 文件 | 内容 |
|---|---|
| `00_INDEX.md` | 本文:范围、四问直答、结论导航 |
| `01_INPUT_IDENTITY_AND_HASHES.md` | 输入身份、SHA-256、PE 结构、恢复覆盖、副本 |
| `02_RECEIVE_CANDIDATES.md` | 接收候选统一表(P1..P7, RX-CAND-001..)与排序 |
| `03_STRING_TO_HANDLER.md` | 游戏协议字符串 → handler 反向追踪 |
| `04_SOCKET_TO_CONSUMER.md` | recv/recvfrom/select → 缓冲区 → 分派 正向追踪 + 最后已证实节点 |
| `05_GAME_PATH_ATTRIBUTION.md` | 业务归属判定、反证、替代解释、负证据 |
| `06_PROTOCOL_MODULE_READINESS.md` | 八类协议模块实现准备度 |
| `07_FOUNDATION_047_CHANGES.md` | 047 实际代码变更及依据 |
| `08_TESTS_AND_BUILD.md` | 构建 / 测试 / 回归结果 |
| `09_EVIDENCE_DUMPS.md` | 反汇编、交叉引用、数据流证据索引 |
| `10_NEXT_ACTION_DECISION.md` | 下一任务唯一优先目标与可执行步骤 |
| `scripts/048_harness.py` | 共享只读分析骨架 |
| `scripts/analyze_048.py` | 一键重生成全部证据 JSON |
| `evidence/` | 原始证据 dump(反汇编 / JSON) |
| `SHA256SUMS.txt` | 报告 / 脚本 / 证据完整性清单 |

## 4. 完成标准对照

| # | 标准 | 结果 |
|---|---|---|
| 1 | 读取并校验 046/047 原始产物 | ✅ `01` §2 |
| 2 | 稳定接收候选清单 | ✅ `02`(RX-CAND-001..014) |
| 3 | 字符串调用关系反向追踪 | ✅ `03` |
| 4 | 独立 socket 候选正向数据流追踪 | ✅ `04` |
| 5 | 明确闭环状态(不推断冒充确认) | ✅ `04` §6 / `05` |
| 6 | 八类模块实现准备度 | ✅ `06` |
| 7 | 说明哪些模块现在可真正开始 | ✅ `06` §2(仅握手/连接) |
| 8 | 代码变更的构建 / 测试 / commit / 哈希 | ✅ `07`/`08` |
| 9 | 历史基线与原始客户端未变 | ✅ `08` §4 |
| 10 | 下一任务唯一优先目标 | ✅ `10` |
