# CODOL-TASK-031 — 大厅 accepted → matching latch → mmstart 单变量回归验证

**任务性质：** 本地受控验证 + 证据补全。**不进行服务器协议实现**，**不进入 snapshot 实现**。
**日期：** 2026-10-13（Asia/Shanghai）
**目标客户端：** CODOL **3.19.26.22** / Build **1649370**
**目标 EXE SHA-256：** `36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537`（本轮实测，见 `FILE_HASH_MANIFEST.tsv`）
**前置报告：** `CODOL-TARGET-PROTOCOL-TRACE-009`
**证据效力更正：** 2026-10-13 第二次修订 —— **本轮动态部分的前置条件不成立**，按更正要求整体降级（见 §0、§1）。

---

## 0. ⚠ 证据效力更正（第二次修订，必须最先读）

**本次运行的客户端停在 "100" 弹窗错误处，未通过已固化的正式启动链成功进入游戏。**
据此，**本轮运行未满足大厅匹配业务验证的前置条件**，其动态结论**不得**用于推断正常大厅流程的行为。

已核实的启动链差异（逐项证据见 `evidence\LAUNCH_CHAIN_DIFF.tsv`）：

| 项 | 已知成功的固化启动链 | 本轮实际执行 | 结论 |
|---|---|---|---|
| 启动脚本 | `run_codol_001\capture_elevated_network.ps1` | `_work\lab\run_all.py` | **不同** |
| 游戏沙箱 | `run_codol_001\sandbox_ifs1_20260923` | `run_codol_001\sandbox_datafix_20260929` | **不同** |
| 沙箱 `dwauth.ini` | `127.0.0.1 / 0 / 127.0.0.1 / 443 / ...` | `formal-zone-lsg.codol.qq.com 3074 / ...` | **不同** |
| auth 服务 | `lobby_probe_server.py` @ `127.0.0.1:8443` | `fake_auth_tls.py` @ `127.0.0.1:3074` | **不同** |
| 大厅服务 | `lobby_socket_server.py` @ `127.0.0.2:8444` | `lobby_server.py` @ `127.0.0.2:3074` | **不同** |
| portproxy | `443→8443` 与 `443→8444` 两条 | 仅 `127.0.0.1:443→8443`；**缺 8444** | **不完整** |
| 客户端退出码 | 正常跑满窗口 / `rc=0` | **`rc=-1 (0xFFFFFFFF)`，`t=8.0s` 与 `t=40.0s`** | **异常** |

`CODOL_SERVER_OPERATIONS_MANUAL.md` §8 明确写有：**"游戏 8 秒内 `0xFFFFFFFF` 退出：启动/IIPS 前置失败"**。
因此本轮**连"进入游戏"都未成立**，更谈不上大厅业务就绪。

---

## 1. 结论与判据（已按更正降级）

> **总判定：`INVALID_PRECONDITION`。**
> 本轮动态观测**全部作废**为正常流程证据；仅作为**一次错误启动会话的记录**保留。

| 判据 | 本轮状态（更正后） | 说明 |
|---|---|---|
| `LATCH_CONFIRMED` | **INVALID_PRECONDITION** | 未进入大厅，无法判定 |
| `MMSTART_CONSTRUCTED` | **INVALID_PRECONDITION** | 同上 |
| `MMSTART_SENT` | **INVALID_PRECONDITION** | 同上 |
| `BATTLE_CONNECT_ATTEMPTED` | **INVALID_PRECONDITION** | 同上 |
| `accepted` 动态行为 | **INVALID_PRECONDITION** | 同上 |
| 总判 | **INVALID_PRECONDITION** | 前置条件（成功进入大厅且业务会话就绪）未满足 |

**明确撤销的表述（第二次修订）：**

1. ~~"客户端从未发出 `mmbook`"~~ → **仅适用于本次错误启动会话**。
   **不得**推导为"正常大厅流程不会触发 `mmbook`"。
2. ~~"大厅握手及加密任务成功"~~ → 仅能证明**局部通信链有活动**，
   **不能**证明大厅业务状态已就绪（客户端停在 "100" 弹窗，业务未建立）。
3. `accepted` / matching latch / `mmstart` / 战斗连接的动态结论
   一律**统一标记为 `INVALID_PRECONDITION`**；原始观测**原样保留**（见 §5），
   **不得改写**为"正常流程失败"。

---

## 2. 静态反汇编结论（独立保留，不因本次启动失败而受影响）

静态部分基于**运行时解包镜像** `image_best.bin`（`17cef6e0…`），与本次运行是否进大厅**无关**，故**独立保留**。等级继续区分 `CONFIRMED` 与 `INFERRED`：

| 结论 | 等级 |
|---|---|
| `accepted` 指纹门为 `strncmp(arg5,"mmbook accepted",15)`，比较函数 `0xC3C678` 为**逐字节**语义 | **CONFIRMED** |
| 解析入口 `0x632680`（`ret 0x14`，5 参数，条件链 G1–G7） | **CONFIRMED** |
| `[matching+0x288]` 以立即数写 **1** 于字节域仅 `0x63280B` 一处（在 `0x632680` 成功分支内） | **CONFIRMED** |
| 闩锁消费者 `0x634402` 及其条件公式 | **CONFIRMED** |
| `mmstart` 构造器 `0x632070`、两个调用者、格式串 `0xDC6800` | **CONFIRMED** |
| `0x632680` 的 `arg5` **指向内层数据起点** | **INFERRED** |
| `accepted` **接收通道 / 调用者** | **UNKNOWN**（两条 vtable 副本在镜像内零直接引用） |
| 变体 B（内层 `u32(15)` 前缀）**使门失败** | **INFERRED（条件式）** —— 前提是上面那条 INFERRED 成立 |
| `0x62F47A` / `0x634B13` 以 word 写覆盖 `0x288/0x289` → 闩锁存在**复位**静态来源 | **CONFIRMED** |

---

## 3. 最终必答问题（更正后）

| 问题 | 回答 |
|---|---|
| **哪个单一变量影响了闩锁？** | **无法判定（`INVALID_PRECONDITION`）。** 未进入大厅。静态上唯一可判定的是"内层字节指纹决定指纹门"，但该门在本轮**未被触达**。 |
| **是否确认 `accepted` 的接收通道及解析入口？** | **解析入口 `0x632680` = CONFIRMED；接收通道 = UNKNOWN。** 与本次启动失败无关。 |
| **是否确认 `mmstart` 被构造、发送？** | **未确认，且本轮结论为 `INVALID_PRECONDITION`。** 构造器静态存在（CONFIRMED）；动态未触发不可作为正常流程证据。 |
| **是否实际观察到战斗连接尝试？目的端点是否有直接证据？** | **未观察到（`INVALID_PRECONDITION`）。** 目的端点**无直接证据**，来源仍 `UNKNOWN`。 |
| **若仍未闭环，最早的未满足条件是什么？** | **前置条件本身未满足：客户端未成功进入大厅（停在 "100" 弹窗，`rc=-1 (0xFFFFFFFF)`）。** 这是本轮**唯一成立的**"最早未满足条件"；`mmbook` 是否触发等问题在它之前**无法讨论**。 |

---

## 4. 交付物索引

| 文件 | 内容 |
|---|---|
| `00_INDEX.md` | 本文件 |
| `BASELINE_REPRODUCTION.md` | 阶段 0（**降级为错误启动会话记录**） |
| `EXPERIMENT_MATRIX.tsv` | 阶段 0/1/2/3 设计矩阵与状态（已更正） |
| `ACCEPTED_BYTE_VARIANTS.tsv` | 三个 `accepted` 字节变体的静态/离线逐字节记录 |
| `LATCH_AND_MMSTART_TRACE.md` | 因果链 8 步取证（静态独立保留；动态降级） |
| `BATTLE_CONNECT_OBSERVATION.md` | 战斗端点观测（降级） |
| `UNKNOWN_AND_BLOCKERS.md` | 未知项、阻塞、最早未满足条件 |
| `FILE_HASH_MANIFEST.tsv` | 分析对象与证据文件哈希 |
| `SHA256SUMS.txt` | 交付物完整性清单 |
| `evidence\LAUNCH_CHAIN_DIFF.tsv` | **固化启动链 vs 本轮实际执行的逐项差异** |
| `integrity\` | **hosts 完整性事件**的全部保全副本 |
| `_work\*` | 脚本、静态验证脚本、隔离实验环境副本 |

---

## 5. 原始观测保留声明

本目录下的 `/evidence/*` 为**错误启动会话的原始观测**，按要求**原样保留、未改写**。
其正确解读是：**一次前置条件不成立的会话**，其中**不存在**"正常大厅流程 × `accepted` 变体"的对照信息。
任何引用这些文件的结论都**必须**附带 `INVALID_PRECONDITION` 标记。

---

## 6. 下一步（按更正指令执行）

**先做启动链，不做协议。**

1. **核验并复现已固化的成功进入大厅启动链**（`capture_elevated_network.ps1` + `sandbox_ifs1_20260923` + `443→8443/8444` portproxy + `lobby_probe_server`/`lobby_socket_server`）。
2. **定位本次 "100" 弹窗错误的差异**（起点：`LAUNCH_CHAIN_DIFF.tsv` 已列出的 6 项差异 + 缺失的 8444 portproxy）。
3. **在客户端真正进入大厅并确认业务会话就绪之前：**
   - **不执行** `mmbook` 触发链的动态回归；
   - **不修改** `accepted`；
   - **不修改** A/B 配对逻辑；
   - **不修改**服务器源码。
4. 只有在**成功进入大厅且业务会话就绪**之后，才重启 TASK-031 的**有效基线阶段**（届时动态结论才具有证据效力）。

---

## 7. 纪律与完整性

- 未修改 `CODOL-BATTLE-SERVER-INTEGRATION-FREEZE-005`、服务器源码、原始游戏文件、原始抓包与运行时镜像。
- 未进入 snapshot 实现；未对客户端做 hook / 注入 / 断点 / 内存写。
- 受保护对象（原始 EXE / 主 DLL / 重定向变体 / 运行时镜像 / 沙箱 EXE / 沙箱 DLL）实验后逐项复核一致（`FILE_HASH_MANIFEST.tsv` T-01..T-07）。
- **`hosts` 文件差异已作为独立完整性事件处理**，保全副本置于 `integrity\`，详见其 `HOSTS_INTEGRITY_EVENT.md`。
- 本任务隔离实验的全部本地进程已停止；无残留监听。
