# 11 — F：GO / NO-GO 与最终回答

> 任务：`EARLY-NATIVE-TAP-DESIGN-001`，只读静态设计与核查。
> 本轮不应用补丁、不编译、不运行、不注入进程。
> 状态词仅使用：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / NOT_OBSERVED / INSTRUMENTATION_BLOCKED / REFUTED。

## F.0 裁决摘要

### 本轮是否完成原生观测设计？

**是（设计级）。**

已定位：

- 启动脚本实际运行 `codol_dedrun_next.exe`：**CONFIRMED**；
- 源码/对象/`codol_dedrun.exe` 同一构建线：**STRONG_CANDIDATE**；
- gamestate 序列化完成点：`codol_sv_state.c:141-146`：**CONFIRMED（源码级）**；
- snapshot 准备/序列化完成点：`sv_snapshot.c:260-263`、`codol_sv_snapshot.c:85-130`：**CONFIRMED（源码级）**；
- 发送前整包边界：`sv_snapshot.c:688`：**CONFIRMED（源码级）**；
- 加密前 netchan 明文点：`sv_net_chan.c:143-145`：**CONFIRMED（源码级）**；
- 最小证据 schema、分层验收、隔离/回滚和停止条件：已完成设计。

### 是否适合申请下一阶段运行实验？

**GO（有条件，仅表示具备申请资格）。**

不是“已获授权运行”，也不是“已验证互通”。下一阶段仍须：

1. 单独设计候选观测补丁；
2. 在独立实验副本中审查和构建；
3. 获得用户明确运行授权；
4. 按本目录 `11_C`、`11_D`、`11_E` 执行；
5. 若任何停止条件触发，立即停止且不自动重试。

## F.1 完成标准五问

### 1. 当前二进制与已分析源码是否能建立可信对应关系？

**STRONG_CANDIDATE。**

支持证据：

- `START-CODOL-SERVER.cmd:4-6` 明确运行原生服务器替代 Python `game-server.py`；
- `:189` 实际执行 `codol_dedrun_next.exe`；
- `codol_dedrun_next.exe` 与 `codol_dedrun.exe` 长度和 SHA-256 完全相同；
- `BUILD-CODOL.ps1:20-27` 明确构建 `codol_dedrun.exe` 并人工 promote 到 `next`；
- makefile `:16-23`、`:71-73`、`:161-178`、`:255-262` 证明 `CODOL_SERVER` 编译宏、CODOL 源集合和链接目标；
- `obj\codol` 对象/`.d` 时间链与 `codol_dedrun.exe` 时间吻合；
- `codol_dedrun_next.exe` 内嵌多条当前源码独有字符串和错误文本。

未达到 **CONFIRMED（精确 commit）** 的原因：

- 无 `.git`；
- PE VersionInfo 为空；
- 未找到 PDB/MAP/ILK 或 native server 构建日志；
- 未找到人工 promote 的独立操作日志；
- 字符串命中不能替代精确构建可重放证明。

### 2. 哪些原生消息边界已被静态确认？

| 消息/边界 | 静态确认内容 | 等级 |
|---|---|---|
| gamestate 编码入口 | `SV_WriteGameState` → `CODOL_WriteServerGamestate` → `CODOL_WriteGamestate`；CODOL 分支在 `#ifdef CODOL_SERVER` 内可达 | **CONFIRMED（源码/构建级可达）** |
| gamestate 段 | 首字节 `0x02`；u32 sequence；cstring map；cstring zone；u32 crc；configstring 子流；u32 clientNum；u32 checksumFeed；`0x05` 终止 | **CONFIRMED（源码级布局）** |
| configstring 子流 | 首字节 `0x03`；u16 count；13 位索引项；`0x05` 终止 | **CONFIRMED（源码级布局）** |
| snapshot 编码入口 | `SV_WriteSnapshotToClient` → `CODOL_PrepareClientSnapshot` → `CODOL_PrepareServerSnapshot` → `CODOL_WriteSnapshotDeltaNumber` | **CONFIRMED（源码/构建级可达）** |
| snapshot 段 | 首字节 `0x00`；u32 serverTime；u8 delta；u8 flags；1 位 base；六个 section；`0x05` 终止 | **CONFIRMED（源码级布局）** |
| reliable server command | `SV_WIRE_SERVERCOMMAND` 首字节 `0x01`；u32 seq；cstring | **CONFIRMED（源码级布局）** |
| EOF | `SV_WIRE_EOF=5`；在未 prepared 或收尾路径写入 | **CONFIRMED（源码级布局）** |
| 发送链 | `SV_SendMessageToClient` → `SV_Netchan_Transmit` → `SV_Netchan_Encode` → `CODOL_NetchanSubmit` | **CONFIRMED（源码级调用链）** |

注意：以上“确认”是**静态源码/构建级**确认，不是线上实测。实际发送和客户端接受仍为 **NOT_OBSERVED**。

### 3. 哪种观测方式最小且风险最低？

**分阶段方案：**

1. **最低风险第一步**：利用现有 `codol_debugTrace`/`developer` 日志，取得 `CoDOL snapshot clock`、无 native frame、pending mismatch、gamestate rejected 等元数据。无需修改二进制，但必须另行授权运行。
2. **完整载荷首选**：若元数据表明路径可达，优先在独立实验副本设计 **N-3：`sv_snapshot.c:688` 发送前整包**观测。它能得到准确长度和完整调用者明文，且不接触加密密钥。
3. **交叉核对**：用 N-1（gamestate 段）和 N-2（snapshot 段）验证内部布局、偏移、首字节和 EOF。
4. **不建议首选**：N-4（`sv_net_chan.c:143-145`）覆盖全部 netchan 消息、频率更高且无内部消息边界；N-5 可能接触命令文本，需要额外脱敏。

**结论：** 元数据优先，完整载荷次之；若必须记录完整载荷，N-3 是风险最低的第一观测点。所有实现都必须先在实验副本中设计、审查、构建和授权。

### 4. 哪些问题必须通过另行授权的运行实验才能回答？

- 服务端是否在真实会话中实际生成完整 gamestate 和 snapshot；
- 服务端实际交给 `SV_Netchan_Transmit` 的完整线载荷和长度；
- 客户端是否实际收到对应消息；
- 客户端期望的 snapshot opcode 是否为 `0x00`；
- 客户端是否成功解析本仓库原生 gamestate；
- 客户端是否成功处理本仓库原生 snapshot；
- 客户端是否进入 `CA_PRIMED -> CA_ACTIVE` 并继续处理后续消息；
- 当前原生服务端与当前客户端是否实际互通；
- 客户端 opcode 分派表的运行时分派目标（若静态仍被 VMProtect/间接分派阻塞）。

### 5. 是否具备申请下一阶段实验的条件？

**具备申请条件，结论为 GO（有条件）。**

通过条件：

- 目标进程和观测点已静态定位；
- 观测点位于序列化后/发送前或加密前，不接触认证秘密；
- 有最小证据 schema；
- 有 A–G 分层验收；
- 有独立副本、哈希核验、日志归档和人工回滚步骤；
- 有明确停止条件；
- 本轮未运行、未编译、未修改原始样本。

未满足的授权前提：

- 尚无候选观测补丁；
- 尚未在实验副本中审查和构建；
- 尚未获得用户明确的运行实验授权；
- 客户端分派表仍为 **INSTRUMENTATION_BLOCKED**；
- 当前原生服务端与客户端互通仍为 **NOT_OBSERVED**。

## F.2 逐项通过条件与阻塞项

| 项 | 通过条件 | 当前证据 | 状态 | 是否阻塞运行实验 |
|---|---|---|---|---|
| G-1 目标进程唯一 | 启动脚本只指向一个原生服务端 | `START-CODOL-SERVER.cmd:189` 指向 `codol_dedrun_next.exe` | **CONFIRMED** | 否 |
| G-2 二进制基线固定 | exe 路径、大小、SHA-256 已记录 | `28366AE...D98A` | **CONFIRMED** | 否 |
| G-3 源码/二进制对应 | 构建脚本、makefile、对象、字符串链 | 支持同一构建线，但缺精确 commit/构建日志 | **STRONG_CANDIDATE** | 是（需在实验前接受该边界） |
| G-4 gamestate 观测点 | 序列化完成后可取得段边界 | `codol_sv_state.c:141-146` | **CANDIDATE** | 是（需补丁设计/授权） |
| G-5 snapshot 观测点 | 准备/序列化完成后可取得段边界 | `sv_snapshot.c:260-263`、`codol_sv_snapshot.c:85-130` | **CANDIDATE** | 是（需补丁设计/授权） |
| G-6 发送前整包 | 可取得完整 `msg->data`/`msg->cursize` 和返回值 | `sv_snapshot.c:688` | **CANDIDATE** | 是（需补丁设计/授权） |
| G-7 秘密材料排除 | 不导出密钥/凭据，完整载荷可过滤 | schema 与停止条件已定义 | **CONFIRMED（可行性设计）** | 否，但必须执行 |
| G-8 隔离/回滚 | 独立副本、原始树只读、前后哈希 | `11_E` 已定义 | **CANDIDATE（待授权执行）** | 是 |
| G-9 分层验收 | A–G 独立判定 | `11_D` 已定义 | **CANDIDATE（待运行验证）** | 是 |
| G-10 客户端接受 | 客户端接收/解析/状态转换 | 历史仅参考实现；本仓库原生流未观察 | **NOT_OBSERVED / INSTRUMENTATION_BLOCKED** | 是 |

## F.3 最小后续工作（获批后）

1. 在独立实验副本中，以短会话、单客户端、低风险地图运行现有元数据 trace。
2. 若元数据正常，单独设计 N-3 的只读整包记录；审查其对缓冲区、长度、时序、返回值和错误处理的影响。
3. 在实验副本中构建候选服务端，核验原始树哈希未变。
4. 按 A–G 层收集证据，先验证服务端生成/发送，再验证客户端接收/解析/状态转换。
5. 若触发任一停止条件，停止且不自动重试。

## F.4 最终一句话

**设计已具备申请下一阶段运行实验的条件（GO 有条件）；但当前仍没有完整载荷捕获、没有原生服务端↔客户端互通实测，不能声称已验证兼容性。**