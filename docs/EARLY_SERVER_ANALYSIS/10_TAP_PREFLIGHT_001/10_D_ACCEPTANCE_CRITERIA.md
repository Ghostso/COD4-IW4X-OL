# 10 — D：分层验收标准（Acceptance Criteria）

> 任务：`EARLY-SERVER-TAP-PREFLIGHT-001`，只读审查与实验设计。
> 本轮不运行实验，不声称任何层级已被本次实验证明。
> 状态词仅使用：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / NOT_OBSERVED / INSTRUMENTATION_BLOCKED / REFUTED。

---

## D.0 核心原则

六个层级必须独立判定，不能自动等同：

1. 服务端源码中的编码逻辑。
2. 服务端实际发送的完整消息。
3. 客户端接收到消息。
4. 客户端成功解析 gamestate。
5. 客户端成功处理 snapshot。
6. 客户端状态转换及后续行为。

任一层通过，不得自动写成下一层通过。最终“本仓库服务端可被当前客户端消费”只能由第 3 至第 6 层在同一会话、同一消息序列上共同证明。

---

## D.1 层级 1：服务端源码编码逻辑

### 可观察证据

- `SV_WriteGameState` 调用 `CODOL_WriteServerGamestate`（`sv_main.c:3939-3948`）。
- `CODOL_WriteGamestate` 写首字节 `2`，随后 seq、map、zone_type、crc、configstrings、clientNum、checksumFeed、终止字节 `5`（`codol_configstrings.c:288-308`）。
- `CODOL_WriteConfigstrings` 写首字节 `3`、u16 count、位字段、终止字节 `5`（`codol_configstrings.c:269-286`）。
- `SV_WriteSnapshotToClient` 调用 `CODOL_PrepareClientSnapshot`（`sv_snapshot.c:224-263`）。
- `CODOL_WriteSnapshotDeltaNumber` 写首字节 `0`、u32 serverTime、delta、flags、各段、终止字节 `5`（`codol_snapshot.c:22-41`）。
- `SV_SendMessageToClient` 在 CODOL 分支调用 `SV_Netchan_Transmit(client, msg->data, msg->cursize)`（`sv_snapshot.c:642-696`）。
- `SV_Netchan_Transmit` 先 memcpy，再 `SV_Netchan_Encode`，再 `CODOL_NetchanSubmit`，保留调用者明文（`sv_net_chan.c:135-149`）。

### 通过条件

- 源码位置、调用链、写入顺序和常量可复算。
- 明确区分 CODOL 可达分支与传统 `svc_ops_e` 死分支。
- 不把源码预期写成运行时已发生。

### 当前状态

**CONFIRMED（源码级）**。该层级已由 `09_A_SERVER_MESSAGE_LEDGER.md` 建立；本轮只复核关键行号。

---

## D.2 层级 2：服务端实际发送的完整消息

### 可观察证据

- 在实验副本的发送前边界记录 `msg->data`、`msg->cursize`、`messageSequence`、发送返回值。
- 对 gamestate/snapshot 分别记录完整 `payload_hex` 与精确 `payload_len`。
- 记录 `msg->overflowed`、失败原因、`nextSnapshotTime` 回滚（如发生）。

### 通过条件

- 观察到完整 gamestate 与 snapshot 载荷，长度精确。
- 首字节与静态账本一致或差异被逐项解释。
- 能证明消息实际提交到 `SV_Netchan_Transmit`，并记录返回值。
- 不把“构造了消息”当成“发送成功”。

### 当前状态

**NOT_OBSERVED**。现有 `wiretap-*.jsonl` 只有 lobby/seckey/stun 层，`game=0`；`wiretap_report.md:183-185` 明确“No game-layer events ... has not been applied/run yet”。

---

## D.3 层级 3：客户端接收到消息

### 可观察证据

- 客户端日志出现与本次服务端消息对应的 `Received gamestate from server, N bytes`。
- `N` 与层级 2 的 gamestate `payload_len` 一致，且时间顺序一致。
- 无“ignoring illegible message”等接收/解密/校验失败。

### 通过条件

- 同一会话内，服务端发送记录与客户端接收记录可通过 `session_id`、时间、长度、序号关联。
- 客户端确实收到至少一条 gamestate 和至少一条 snapshot。

### 不能证明

- 不能仅凭“收到”证明解析成功。
- 不能仅凭历史 `console_mp*.log` 中的 `Received gamestate` 证明本次原生服务端被消费；那些日志对应的是参考 Python 服务端流。

### 当前状态

**NOT_OBSERVED**（对本仓库原生服务端）；历史参考实现消费为 **CONFIRMED（行为级，仅限参考实现）**。

---

## D.4 层级 4：客户端成功解析 gamestate

### 可观察证据

- 客户端日志出现：
  - `CL_ParseGamestate: begin parse of gamestate`
  - `CL_ParseGamestate: begin wait on fast files` / `end wait on fast files`
  - `CL_ParseGamestate: comparing files with server`
  - `CL_ParseGamestate: calling CL_DownloadsComplete`
- 无 `bad command byte`、`EXE_CONFIGSTRINGMISMATCH`、configstring 索引溢出等错误。
- 可进一步用客户端接收点日志/跟踪证明解析器确实进入。

### 通过条件

- gamestate 解析流程完成到 `CL_DownloadsComplete`。
- configstring 子流的 count、索引、终止位置与服务端记录一致，或差异可解释。
- 无错误行。

### 当前状态

**NOT_OBSERVED**（对本仓库原生服务端）。历史日志中的成功解析属于参考实现，不能直接迁移结论。

---

## D.5 层级 5：客户端成功处理 snapshot

### 可观察证据

- 首个 snapshot 之后，客户端没有：
  - `bad command byte`
  - `CL_GetSnapshot: truncated`
  - `ignoring illegible message`
  - `non-SNAPFLAG_BASELINE ... Discarding packet`
  - overflow/截断相关错误。
- 可用的快照处理日志/跟踪显示首个基线 snapshot 被接受，后续 delta snapshot 被处理。
- `CL_ParseSnapshot` 候选（`0x0049D95F`，函数起始 `0x0049D800`）与 `CG_TransitionSnapshot` 候选（`0x0045D180`）如能在运行时被观察到，应记录其实际进入；但静态候选本身不得升级为已确认入口。

### 通过条件

- 首个基线 snapshot 被客户端接受，后续至少若干 delta snapshot 被处理。
- 无截断、坏命令、基线丢弃或配置不匹配错误。
- 服务端记录的 snapshot 序号与客户端 ACK/状态推进可关联。

### 当前状态

**NOT_OBSERVED**（对本仓库原生服务端）；客户端存在 snapshot 解码器为 **CONFIRMED（存在）**，但其 opcode 分派表为 **INSTRUMENTATION_BLOCKED**。

---

## D.6 层级 6：客户端状态转换及后续行为

### 可观察证据

- `CA_LOADING -> CA_PRIMED`（got gamestate, waiting for first frame）。
- `CA_PRIMED -> CA_ACTIVE`（game views should be displayed）。
- 转换发生在本次会话的服务端 gamestate/snapshot 发送之后，且时间顺序一致。
- 后续无致命错误、无崩溃、无持续重连。

### 通过条件

- 同一会话中，客户端到达 `CA_ACTIVE`。
- 状态转换与层级 2 至 5 的消息序列可关联。
- 记录后续稳定观察窗口，不把“短暂进入”当成“持续可玩”。

### 不能证明

- 进入 `CA_ACTIVE` 不等于所有游戏功能、同步、武器、计分、快照 delta 都正确。
- 不能把 UI 未崩溃当作协议逐字节一致。

### 当前状态

**NOT_OBSERVED**（对本仓库原生服务端）；历史日志 17 次 `CA_ACTIVE` 属于参考 Python 服务端，**不能**用于证明本仓库原生服务端互通。

---

## D.7 分层判定表

| 层级 | 证明对象 | 最小证据 | 当前状态 | 通过后仍不能推出 |
|---|---|---|---|---|
| L1 | 服务端源码编码逻辑 | 源码行号与调用链 | **CONFIRMED** | 实际运行走到该路径 |
| L2 | 服务端实际发送完整消息 | 发送前完整明文 + 长度 + 返回值 | **NOT_OBSERVED** | 客户端收到 |
| L3 | 客户端收到消息 | 客户端日志/接收点与 L2 对齐 | **NOT_OBSERVED** | 成功解析 |
| L4 | 客户端解析 gamestate | `CL_ParseGamestate` 完成、无错误 | **NOT_OBSERVED** | snapshot 成功 |
| L5 | 客户端处理 snapshot | 基线/增量处理、无截断/坏命令 | **NOT_OBSERVED** | 状态转换或可玩 |
| L6 | 状态转换与后续行为 | `CA_PRIMED -> CA_ACTIVE` 且时间关联 | **NOT_OBSERVED** | 所有游戏功能正确 |

---

## D.8 失败判定与错误锚点

| 错误锚点 | 层级 | 含义 | 处理 |
|---|---|---|---|
| `bad command byte` | L4/L5 | 首字节/分派与客户端预期不符 | 记录首个失败 opcode 与偏移，停止并回到静态账本核对 |
| `EXE_CONFIGSTRINGMISMATCH` | L4 | configstring 不匹配 | 记录索引/值/服务端记录，停止 |
| `G_FindConfigstringIndex: overflow` | L4 | configstring 索引溢出 | 记录 count/索引，停止 |
| `CL_GetSnapshot: truncated` | L5 | snapshot 截断 | 记录段偏移与长度，停止 |
| `ignoring illegible message` | L3 | 消息不可读/校验失败 | 记录 netchan 序号与时间，停止 |
| `non-SNAPFLAG_BASELINE ... Discarding packet` | L5 | 客户端拒绝非基线包 | 记录 flags/delta/序列，停止 |
| overflow/failure 日志 | L2 | 服务端消息未成功构造/发送 | 记录失败原因，不自动重试 |

---

## D.9 最终接受定义

只有在同一实验会话中同时满足以下条件，才可写：

> “当前客户端能够消费本仓库原生服务端输出（协议层初步接受）”。

- L2：服务端确实发送了完整 gamestate 与 snapshot，且发送成功。
- L3：客户端收到对应消息，长度/时间/序号可关联。
- L4：gamestate 解析完成，无错误。
- L5：首个基线 snapshot 与至少若干 delta snapshot 被处理，无截断/坏命令/基线丢弃。
- L6：客户端进入 `CA_ACTIVE` 并在观察窗口内稳定。

即使满足以上条件，也不得声称“所有游戏层功能、资产、同步或玩法完全正确”；那需要独立的游戏层测试。

---

## D.10 本轮未做事项

- 未执行任何客户端/服务端运行实验。
- 未捕获任何真实载荷。
- 未将历史参考实现日志用于证明本仓库原生服务端互通。