# 11 — D：分层验收标准

> 任务：`EARLY-NATIVE-TAP-DESIGN-001`，只读设计。
> 本文件定义 A–G 七层证据标准；不允许跨层推断。
> 状态词仅使用：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / NOT_OBSERVED / INSTRUMENTATION_BLOCKED / REFUTED。

## D.0 分层原则

每一层必须独立取证：

- 服务端生成消息 ≠ 服务端发送消息；
- 服务端发送消息 ≠ 客户端接收消息；
- 客户端接收消息 ≠ 客户端解析消息；
- 客户端解析消息 ≠ 客户端进入预期状态；
- 客户端进入预期状态 ≠ 后续消息持续正常处理。

任何下层证据都不能自动替代上层证据。客户端日志中的状态转换可以作为行为级证据，但不能单独证明每个字段逐字节一致。

## D.1 当前状态汇总

| 层 | 验收目标 | 当前静态/历史证据 | 当前状态 | 是否必须运行实验 |
|---|---|---|---|---|
| A | 服务端生成完整 gamestate | `SV_WriteGameState` → `CODOL_WriteServerGamestate` → `CODOL_WriteGamestate` 路径和字段已定位；没有运行捕获 | **STRONG_CANDIDATE** | 是 |
| B | 服务端生成完整 snapshot | `SV_WriteSnapshotToClient` → `CODOL_PrepareClientSnapshot` → `CODOL_WriteSnapshotDeltaNumber` 路径和 `0x00` 已定位；没有运行捕获 | **STRONG_CANDIDATE** | 是 |
| C | 服务端实际发送目标消息 | `SV_SendMessageToClient` → `SV_Netchan_Transmit` → `CODOL_NetchanSubmit` 调用链已定位；没有发送成功实测 | **CONFIRMED（源码级可达）/ NOT_OBSERVED（实际发送）** | 是 |
| D | 客户端接收到对应消息 | 无本仓库原生服务端下行捕获；历史日志只覆盖参考实现 | **NOT_OBSERVED** | 是 |
| E | 客户端成功解析 gamestate | 客户端解析器字符串/反汇编存在；历史参考实现 17 次到 `CA_ACTIVE`；原生流未验证 | **CONFIRMED（参考实现行为级）/ NOT_OBSERVED（本仓库流）** | 是 |
| F | 客户端成功处理 snapshot | `CL_ParseSnapshot` 候选存在；客户端期望 opcode 未知；无原生流实测 | **STRONG_CANDIDATE（解析器存在）/ UNKNOWN（本仓库流接受）** | 是 |
| G | 客户端进入预期状态并继续正常处理后续消息 | 历史参考实现到 `CA_ACTIVE`；原生服务端未观察 | **NOT_OBSERVED** | 是 |

## D.2 A 层：服务端生成完整 gamestate

### 目标

证明服务端在目标会话中实际生成了一条完整 gamestate，并记录其准确长度和字节边界。

### 必需证据

- 会话 ID、方向 `s2c`、消息类别 `gamestate`；
- `capture_stage` 为 `post_gamestate_serialize` 或 `pre_netchan_transmit`；
- gamestate 段起始、长度、首字节；
- 首字节为 `0x02`（服务端静态定义，`codol_configstrings.c:298`）；
- 完整 gamestate 明文字节；
- configstring 子流 `0x03` 和终止 `0x05` 的存在；
- 最终 gamestate 段末尾 `0x05`（`codol_configstrings.c:306`）；
- 服务端构建 SHA-256 和捕获位置。

### 可证明

- 服务端实际生成了完整 gamestate 段。
- 长度和字节边界可复算。

### 不能证明

- 整包已经成功发送；
- 客户端收到或解析；
- 客户端进入任何状态。

### 当前状态

**STRONG_CANDIDATE**：源码路径闭合，二进制字符串证据支持同构建线，但没有运行捕获。

## D.3 B 层：服务端生成完整 snapshot

### 目标

证明服务端在目标会话中实际生成了一条完整 snapshot，并记录其准确长度和字节边界。

### 必需证据

- 会话 ID、方向 `s2c`、消息类别 `snapshot`；
- `capture_stage` 为 `post_snapshot_serialize` 或 `pre_netchan_transmit`；
- snapshot 段首字节 `0x00`（`codol_snapshot.c:23`）；
- serverTime、delta、flags、base bit、section、EOF `0x05`；
- snapshot 段长度和边界；
- 是否含 match-data 追加；
- 服务端构建 SHA-256 和捕获位置。

### 可证明

- 服务端实际生成了完整 snapshot 段。
- 长度和字节边界可复算。

### 不能证明

- 整包已经成功发送；
- 客户端期望的 snapshot opcode 是 `0x00`；
- 客户端成功处理 snapshot。

### 当前状态

**STRONG_CANDIDATE**：服务端 `0x00` 已由源码确认；实际运行生成和客户端接受均未观察。

## D.4 C 层：服务端实际发送目标消息

### 目标

证明目标消息已经通过发送函数提交，而不只是停留在缓冲区。

### 必需证据

- `pre_netchan_transmit` 记录；
- `msg->data` 和 `msg->cursize` 与 A/B 层段一致；
- `SV_Netchan_Transmit` 返回值；
- `client->netchan.outgoingSequence` 前后变化；
- 是否发生失败回滚（`sv_snapshot.c:690-695`）；
- 时间戳和会话关联。

### 可证明

- 调用者实际把完整消息交给 `SV_Netchan_Transmit`；
- 在返回成功时，`CODOL_NetchanSubmit` 已提交。

### 不能证明

- 客户端收到；
- 客户端解析；
- 客户端状态转换。

### 当前状态

- 源码级调用链：**CONFIRMED**。
- 实际运行发送：**NOT_OBSERVED**。

## D.5 D 层：客户端接收到对应消息

### 目标

证明客户端接收路径实际看到了对应方向、长度和序号的消息。

### 必需证据

- 客户端接收侧记录或受控观测；
- 与 C 层的序号、时间、方向和长度关联；
- 客户端 `CL_PacketEvent` / `CL_Netchan_Decode` 路径的实际执行证据（如另行授权运行）；
- 客户端日志中没有因接收失败导致的丢包/非法消息错误。

### 可证明

- 客户端接收路径收到该消息。

### 不能证明

- 客户端成功解析 gamestate/snapshot；
- 客户端状态转换。

### 当前状态

**NOT_OBSERVED**。

客户端静态候选：

- `CL_PacketEvent @ 0x00497360`；
- `CL_Netchan_Decode @ 0x0049C5E0`。

这两者均为 **STRONG_CANDIDATE**，不是本仓库流实测。

## D.6 E 层：客户端成功解析 gamestate

### 目标

证明客户端 gamestate 解析路径实际执行并接受本仓库原生服务端的 gamestate。

### 必需证据

- 客户端日志出现 `Received gamestate from server, %d bytes` 或等效解析成功路径；
- 无 `CL_ParseGamestate: bad command byte`；
- 无 `EXE_CONFIGSTRINGMISMATCH`；
- configstring 计数和字段可关联；
- 与 C/D 层的序号、时间、长度对应。

### 可证明

- 客户端解析路径接受该 gamestate。

### 不能证明

- snapshot 处理成功；
- 客户端最终进入预期状态。

### 当前状态

- 参考 Python 服务端历史行为：**CONFIRMED（行为级）**。
- 本仓库原生服务端 gamestate：**NOT_OBSERVED**。

客户端静态证据：

- `CL_ParseGamestate: begin parse of gamestate` @ `0xC49358`；
- `CL_ParseGamestate: bad command byte %d` @ `0xC4939B`；
- `EXE_CONFIGSTRINGMISMATCH` @ `0xC4933C`；
- 这些字符串存在为 **CONFIRMED（字符串存在）**，不能单独证明当前流被接受。

## D.7 F 层：客户端成功处理 snapshot

### 目标

证明客户端 snapshot 解析路径接受本仓库原生服务端的 snapshot。

### 必需证据

- 客户端 `CL_ParseSnapshot` 路径执行；
- 没有 `CL_GetSnapshot: truncated`；
- 没有非基线首帧被错误丢弃；
- snapshot opcode 与服务端首字节一致；
- snapshot 长度、flags、base 和 section 字段可关联。

### 可证明

- 客户端 snapshot 解析路径接受该 snapshot。

### 不能证明

- 客户端进入 `CA_ACTIVE`；
- 后续消息持续正常。

### 当前状态

- `CL_ParseSnapshot` 候选存在：**STRONG_CANDIDATE**。
- 客户端期望 opcode：**UNKNOWN**。
- 本仓库原生 snapshot 被接受：**NOT_OBSERVED**。
- 客户端 opcode 分派表：**INSTRUMENTATION_BLOCKED**。

## D.8 G 层：客户端进入预期状态并继续正常处理后续消息

### 目标

证明客户端不仅解析单条消息，还进入预期状态并持续处理后续消息。

### 必需证据

- 客户端日志出现 `CA_LOADING -> CA_PRIMED -> CA_ACTIVE`（或等效状态转换）；
- 无 `bad command byte`、`ignoring illegible message`、`CL_GetSnapshot: truncated`、`CONFIGSTRINGMISMATCH` 等错误；
- 后续多条 snapshot 稳定处理；
- 会话阶段和错误日志时间关联；
- 客户端行为（例如继续进入游戏/保持连接）可作为补充证据，但不能替代日志。

### 可证明

- 客户端进入预期状态并继续处理后续消息。

### 当前状态

- 参考实现历史日志：**CONFIRMED（行为级）**。
- 本仓库原生服务端：**NOT_OBSERVED**。

## D.9 跨层禁止推断表

| 已有证据 | 禁止直接推断 |
|---|---|
| 源码写出 `0x02`/`0x00` | 客户端接受该值 |
| 服务端段级载荷完整 | 整包已发送 |
| `SV_Netchan_Transmit` 返回成功 | 客户端收到 |
| 客户端收到字节 | 客户端解析成功 |
| 客户端解析 gamestate | snapshot 处理成功 |
| 客户端解析 snapshot | 客户端进入 `CA_ACTIVE` |
| 客户端进入 `CA_ACTIVE` | 后续消息持续正常 |
| 历史参考实现到 `CA_ACTIVE` | 本仓库原生服务端互通 |

## D.10 分层状态判定规则

| 状态 | 判定要求 |
|---|---|
| **CONFIRMED** | 有直接、可复算证据，且能排除同层其他解释 |
| **STRONG_CANDIDATE** | 多条独立静态/历史证据一致，但缺少本层直接实测 |
| **CANDIDATE** | 有路径、字符串、调用链或设计证据，尚未排除其他解释 |
| **UNKNOWN** | 没有足够证据判定 |
| **NOT_OBSERVED** | 目标事件尚未在目标对象上观察 |
| **INSTRUMENTATION_BLOCKED** | 现有静态材料无法继续闭合，需要运行时或受保护代码外证据 |
| **REFUTED** | 有直接证据否定该断言 |

## D.11 本轮结论

- A、B 层：**STRONG_CANDIDATE**，尚未运行观察。
- C 层：源码级 **CONFIRMED**，实际发送 **NOT_OBSERVED**。
- D、F、G 层：本仓库原生服务端路径 **NOT_OBSERVED**。
- E 层：参考实现 **CONFIRMED（行为级）**，本仓库原生服务端 **NOT_OBSERVED**。
- 客户端解析器存在：**CONFIRMED（字符串/反汇编存在）**；分派表：**INSTRUMENTATION_BLOCKED**。