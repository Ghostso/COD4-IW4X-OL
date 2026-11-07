# 10 — E：GO / NO-GO 审查（Go / No-Go）

> 任务：`EARLY-SERVER-TAP-PREFLIGHT-001`，只读审查与实验设计。
> 本轮不执行运行实验，不应用 diff，不启动任何程序。
> 状态词仅使用：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / NOT_OBSERVED / INSTRUMENTATION_BLOCKED / REFUTED。

---

## E.0 裁决摘要

### 针对“按 `wire_interception.md §4` 原样应用并运行实验”：**NO-GO**

理由：

1. §4 目标文件 `game-server.py` 在 `D:\BaiduNetdiskDownload` 全盘不存在（`count=0`）。
2. §4 依赖的 `tap_report.py` 同样不存在（`count=0`）。
3. 当前服务器启动脚本明确运行原生 `codol_dedrun_next.exe`，并写明它替代 Python `game-server.py`（`START-CODOL-SERVER.cmd:4-6`）。
4. §4 即使被移植，也只记录 gamestate 元数据和 snapshot `op` 计数，不记录完整 gamestate/snapshot 载荷；它不满足本任务最小捕获要求。
5. 当前没有对原生栈重新设计、构建、审查和授权的插桩补丁。

### 针对“先完成原生栈插桩设计与审查，再单独申请运行实验”：**具备申请条件，但不是本轮的 GO**

本轮只完成了原生候选插桩点的设计。运行实验仍需：

- 另行设计并审查原生栈补丁；
- 在独立实验副本中构建；
- 获得明确的运行实验授权；
- 按 `10_C_ISOLATION_ROLLBACK.md` 和 `10_D_ACCEPTANCE_CRITERIA.md` 执行。

---

## E.1 逐项通过条件与阻塞项

| 项 | 通过条件 | 当前证据 | 状态 | 是否阻塞 |
|---|---|---|---|---|
| G-1 目标文件存在 | §4 目标 `game-server.py` 可定位且哈希固定 | 全盘搜索 `count=0` | **REFUTED** | **是** |
| G-2 辅助工具存在 | `tap_report.py` 可定位并核验 | 全盘搜索 `count=0` | **REFUTED** | **是** |
| G-3 运行时匹配 | 文档目标与当前启动路径一致 | 当前启动 `codol_dedrun_next.exe`，脚本明示替代 Python `game-server.py` | **REFUTED** | **是** |
| G-4 diff 边界明确 | 插桩位于加密前/发送前且可证明不改线协议 | §4 目标缺失，边界无法对当前栈核验 | **UNKNOWN** | **是** |
| G-5 完整载荷能力 | 能记录 gamestate/snapshot 完整明文与长度 | §4 只记录元数据/op 计数；现有 `wiretap` 无 game 层 | **REFUTED / NOT_OBSERVED** | **是** |
| G-6 秘密材料可排除 | 不导出/不落盘认证秘密 | 既有 `key_fp()` 与 seckey 脱敏先例证明可行 | **CONFIRMED（可行性）** | 否，但必须执行 |
| G-7 隔离与回滚 | 独立副本、原始树只读、实验前后哈希 | 方案已形成（`10_C`） | **CANDIDATE（待授权执行）** | 是 |
| G-8 分层验收 | L1-L6 独立判定 | 标准已形成（`10_D`） | **CANDIDATE（待执行验证）** | 是 |
| G-9 服务端编码账本 | 原生 CODOL 分支调用链与首字节可复算 | 09_A 已建立，本轮复核关键行号 | **CONFIRMED（源码级）** | 否 |
| G-10 客户端消费证据 | 本仓库原生服务端 ↔ 当前客户端闭环 | 历史日志仅证明参考 Python 服务端 | **NOT_OBSERVED** | **是** |

---

## E.2 §4 逐 hunk 可行性裁决

| Hunk | 目标 | 可行性 | 原因 |
|---|---|---|---|
| WT-G0 | import 块 | **REFUTED** | 目标文件不存在 |
| WT-G1 | `note_client_packet` | **REFUTED** | 目标文件不存在；当前原生栈无该 Python 函数 |
| WT-G2 | 可靠命令循环 | **REFUTED** | 目标文件不存在；且会记录命令文本，需额外脱敏 |
| WT-G3 | usercmd decode 成功分支 | **REFUTED** | 目标文件不存在；变量上下文无法核验 |
| WT-G4 | `build_gamestate` | **REFUTED** | 目标文件不存在；且只记录元数据，不含完整载荷 |
| WT-G5 | `_send_snapshot_now` | **REFUTED** | 目标文件不存在；且只做 `op` 计数，不含完整载荷 |
| WT-G6 | `_queue_server_cmd` | **REFUTED** | 目标文件不存在；且命令文本可能敏感 |

结论：7/7 hunk 对当前树的适用性均为 **REFUTED**。

---

## E.3 原生栈重新设计的候选点裁决

| 候选点 | 当前状态 | 后续要求 |
|---|---|---|
| N-1 gamestate 明文段（`codol_sv_state.c:141-146` 后） | **CANDIDATE** | 设计补丁、构建、审查、授权；记录精确偏移和长度 |
| N-2 snapshot 明文段（`sv_snapshot.c:260-263` 后） | **CANDIDATE** | 同上；需处理 `msg` 偏移和 prepared 状态 |
| N-3 发送前整包明文（`sv_snapshot.c:688`） | **CANDIDATE** | 记录整包明文与返回值；用于证明实际提交 |
| N-4 加密前 netchan 明文（`sv_net_chan.c:143-144`） | **CANDIDATE** | 高频；需采样/开关；不提供内部消息边界 |
| N-5 可靠 server command（`sv_snapshot.c:97-107`） | **CANDIDATE** | 命令文本脱敏/白名单 |
| N-6 snapshot 段级收尾（`codol_snapshot.c:22-41`） | **CANDIDATE** | 与 N-2/N-3 关联 |

这些候选点均**未应用、未编译、未运行**。

---

## E.4 是否适合另行授权运行实验

### 可以申请的条件

- 原生栈插桩补丁已单独设计；
- 补丁只记录已解密/发送前游戏层数据，不导出认证秘密；
- 实验副本独立，原始树只读；
- 有实验前后 SHA-256 核验；
- 有明确停止条件；
- 有分层验收标准。

### 当前不满足的条件

- 尚无原生栈插桩补丁；
- 尚未在副本中构建或审查；
- 尚未获得运行实验授权；
- §4 不能作为可直接执行的方案。

### 结论

- **本轮：NO-GO（不得按 §4 原样进入运行实验）**。
- **后续：在完成原生栈插桩设计、隔离方案和审查后，可另行申请 GO；该 GO 只表示“具备申请下一阶段运行实验的条件”，不代表已经获得运行授权。**

---

## E.5 阻塞项清单

| 编号 | 阻塞项 | 类型 | 解除条件 |
|---|---|---|---|
| B-1 | `game-server.py` 不存在 | 目标缺失 | 不再尝试应用 §4；改为原生栈方案 |
| B-2 | `tap_report.py` 不存在 | 工具缺失 | 不再依赖该工具；另设分析通道 |
| B-3 | 当前运行栈为原生 exe | 运行时替换 | 针对原生栈设计插桩 |
| B-4 | §4 无完整载荷记录 | 证据不足 | 新方案必须记录完整 gamestate/snapshot 明文与长度 |
| B-5 | 无原生插桩补丁 | 设计缺失 | 单独设计、构建、审查 |
| B-6 | 无运行授权 | 授权缺失 | 用户明确授权后另行实验 |
| B-7 | 历史日志仅覆盖参考实现 | 证据范围不足 | 用本仓库原生服务端重新采集并按 L1-L6 验收 |

---

## E.6 最终回答

1. **是否可以按 §4 原样执行？** 不可以。**NO-GO / REFUTED**。
2. **是否有原生栈候选插桩点？** 有。**CANDIDATE**，未应用。
3. **是否可以设计安全、可回滚的实验？** 可以。方案见 `10_C`。
4. **本轮是否执行了实验？** 没有。
5. **下一步最小工作是什么？** 为原生栈单独设计并审查 N-1/N-2/N-3 补丁，确认完整载荷记录能力和脱敏边界后，再申请运行实验授权。