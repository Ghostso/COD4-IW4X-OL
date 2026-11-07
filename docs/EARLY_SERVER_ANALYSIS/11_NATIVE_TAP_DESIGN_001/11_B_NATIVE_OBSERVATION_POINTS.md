# 11 — B：原生观测边界与最小风险方案

> 任务：`EARLY-NATIVE-TAP-DESIGN-001`，只读设计。
> 本文件不生成可执行补丁，不编译，不注入进程，不运行服务端或客户端。
> 状态词仅使用：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / NOT_OBSERVED / INSTRUMENTATION_BLOCKED / REFUTED。

## B.0 结论先行

| 观测目标 | 最小风险方式 | 完整载荷能力 | 当前等级 |
|---|---|---|---|
| 服务端是否生成 gamestate | 现有 `codol_debugTrace` / `developer` 元数据路径，或 N-1 段级记录 | 元数据路径不能；N-1 可取得段级完整明文（需另行设计/构建） | **CANDIDATE** |
| 服务端是否生成 snapshot | 现有 snapshot clock 元数据；N-2 段级记录 | 元数据路径不能；N-2 可取得段级明文（需另行设计/构建） | **CANDIDATE** |
| 服务端是否实际交给 netchan | N-3 发送前整包记录 | 可取得完整 netchan 明文，但不自动拆分内部消息 | **CANDIDATE** |
| 服务端是否进入编码阶段 | N-4 `SV_Netchan_Encode` 前记录 | 可取得完整调用者明文；无内部消息边界 | **CANDIDATE** |
| 客户端是否接收/解析 | 必须另行运行并观察；本轮静态无法完成 | 本设计不执行 | **NOT_OBSERVED / INSTRUMENTATION_BLOCKED（客户端分派）** |

**推荐最小风险组合：** 先利用现有 `codol_debugTrace` 和 `developer` 日志取得服务端元数据；只有需要验证完整线载荷时，才在独立实验副本中设计 N-3（发送前整包）记录，并用 N-1/N-2 对 gamestate/snapshot 段做交叉核对。不要优先选择 N-4 作为唯一观测点，因为它没有内部消息边界且覆盖面更宽。

## B.1 候选观测点总表

| 编号 | 位置 | 协议阶段 | 可获得的边界/长度 | 元数据最小集 | 完整载荷需要什么 | 行为影响 | 状态 |
|---|---|---|---|---|---|---|---|
| N-1 | `codol_sv_state.c:141-146` 之后 | gamestate 序列化完成后、整包发送前 | 段起始为序列化前 `msg->cursize`，长度为 `wire.size` / 新旧 `cursize` 差；需保存调用前游标 | client、map、zone、gametype、sequence、`wire.size`、首字节、`msg->cursize` | 记录 `msg->data + old_cursize` 起 `wire.size` 字节 | 若只读复制并异步处理，理论上不改协议；同步日志/分配可影响时序或内存 | **CANDIDATE** |
| N-2 | `sv_snapshot.c:260-263` 之后 | snapshot 段准备/序列化完成后、收尾前 | 以调用前 `msg->cursize` 与返回后 `msg->cursize` 求差；需确认没有并发写入 | client slot、sequence、ack、delta、flags、`msg->cursize` 前后值、首字节 | 记录新增区间完整字节；需处理 match-data 追加和 EOF 保留 | 读复制原则上不改 `msg`，但同步 I/O 可影响发送节奏；必须验证 prepared 状态 | **CANDIDATE** |
| N-3 | `sv_snapshot.c:688`，`SV_Netchan_Transmit` 调用点 | 整条 netchan 消息交给发送函数前 | `msg->data[0..msg->cursize)` 是完整消息；长度精确 | client、sequence、state、`msg->cursize`、首 4 字节、返回值、时间 | 记录 `msg->data` 全长；这是整包明文 | 若记录在调用前后同步执行，可能影响帧时序；不能在发送失败前改变缓冲区 | **CANDIDATE** |
| N-4 | `sv_net_chan.c:143-145`，`SV_Netchan_Encode` 前 | 调用者明文进入加密/封装前 | `data[0..cursize)` 是完整调用者消息；无内部消息边界 | `cursize`、调用序号、方向、首字节、返回值 | 记录 `data` 全长；不含内部 svc 分段 | 高频；同步记录影响更明显；复制或日志异常可能改变发送 | **CANDIDATE** |
| N-5 | `sv_snapshot.c:97-107` | 可靠 server command 序列化时 | 每条 command 的 `0x01`、u32 seq、cstring；长度由消息游标差确定 | client、seq、命令类别、长度、消息偏移 | 记录命令字符串全文；但可能含敏感文本 | 文本记录与脱敏逻辑可影响时序；不脱敏则不应落盘 | **CANDIDATE** |
| N-6 | `codol_snapshot.c:22-41` | snapshot 段内部字段编码完成时 | 段首字节、serverTime、delta、flags、base、section、EOF | 首字节、字段、section 边界、失败原因 | 记录段内完整字节；必须另行关联 `msg` 偏移 | 段级记录不能单独证明整包发送；同步 I/O 可影响时序 | **CANDIDATE** |
| T-1 | `common.c:567-576`、`sv_snapshot.c:264-283` | 现有运行日志元数据 | 无完整载荷边界；只有 snapshot clock 字段和失败原因 | client、seq、ack、delta、gap、server time、flags、ent0、pof 等 | 不适用 | 启用高频日志会增加同步写日志开销；设计上应限流/短会话 | **CANDIDATE（运行未观察）** |

## B.2 各候选点的上下文与可证明性

### B.2.1 N-1：gamestate 序列化完成点

证据：

- `sv_main.c:3939-3949`：CODOL 分支调用 `CODOL_WriteServerGamestate` 后直接返回。
- `codol_sv_state.c:141-146`：初始化 `wire` 指向 `msg->data + msg->cursize`，调用 `CODOL_WriteGamestate`，再 `msg->cursize += wire.size`，最后 `msg->bit = msg->cursize * 8`。
- `codol_configstrings.c:298-306`：gamestate 首字节 `0x02`，后续 sequence、map、zone、crc、configstrings 子流、client number、checksum feed、`0x05`。
- `codol_configstrings.c:275-284`：configstring 子流首字节 `0x03`，终止 `0x05`。

能证明什么：

- 源码级可以确定：序列化完成后，gamestate 段的起始地址和 `wire.size` 在 `codol_sv_state.c:141-146` 的上下文中可计算。
- 只有保存调用前 `msg->cursize`，才能把 gamestate 段从整个 `msg` 中无损切出。
- 该点不能单独证明 gamestate 已经交给 socket；必须与 N-3 的发送返回值关联。

风险：

- 如果在同一线程内做同步写盘、分配大缓冲或打印大量 hex，会改变帧时序和内存压力。
- 必须只读复制，不得改写 `wire.size`、`msg->cursize`、`msg->bit`、`msg->overflowed` 或调用顺序。
- 需要在实验副本中单独审查并构建；本轮不生成补丁。

### B.2.2 N-2：snapshot 序列化完成点

证据：

- `sv_snapshot.c:759-769`：`SV_SendClientSnapshot` 依次执行 `SV_BeginClientSnapshot`、`SV_WriteSnapshotToClient`、`SV_EndClientSnapshot`。
- `sv_snapshot.c:224-263`：CODOL 分支取得 native frame，设置 flags、delta、rov，并调用 `CODOL_PrepareClientSnapshot`。
- `codol_sv_snapshot.c:85-130`：`CODOL_PrepareClientSnapshot` 进行分配、历史/基线准备、`CODOL_PrepareServerSnapshot` 调用、prepared 副本记录。
- `codol_snapshot.c:8-46`：snapshot 段首字节 `0x00`，字段为 serverTime、delta、flags、base bit、六个 section、EOF `0x05`。
- `sv_snapshot.c:827-849`：`SV_EndClientSnapshot` 在没有 prepared snapshot 时写 `SV_WIRE_EOF`（值为 5）。

能证明什么：

- `:260-263` 之后是 snapshot 段准备完成的可静态定位候选点。
- 若保存调用前 `msg->cursize`，并确认该调用没有其他并发写入，可以计算新增段长度和首字节。
- 但 `codol_sv_snapshot.c:111-122` 还可能在 match-data due 时追加 match data section；所以不能把“新增区间”未经核验地等同于纯 snapshot 段。
- 该点不能证明整条消息已发送；必须与 N-3 关联。

风险：

- prepared 状态和 `client_pending` 状态与发送历史绑定，观测代码不得改变 `msg` 或 pending 记录。
- 同步日志可能改变 snapshot 发送节奏，影响 delta/gap 行为。
- 任何记录逻辑都应先复制到独立缓冲，避免持有 `msg` 指针跨帧使用。

### B.2.3 N-3：发送前整包边界

证据：

- `sv_snapshot.c:642-688`：`SV_SendMessageToClient` 检查 `overflowed`，记录 frame 信息，并在 `:688` 调用 `SV_Netchan_Transmit(client, msg->data, msg->cursize)`。
- `sv_snapshot.c:690-695`：发送失败时回滚 frame 记录并返回 `qfalse`。
- `sv_snapshot.c:2160` 与 `:2312`：gamestate 也通过同一发送函数；`sv_snapshot.c:759-769` 的 snapshot 也走该函数。

能证明什么：

- 该点能取得“调用者交给 netchan 的完整消息”的准确边界和长度。
- 结合返回值可以证明本次调用是否成功提交，而不只是生成缓冲。
- 该点是整包视角，不直接提供 gamestate/configstring/snapshot 的内部边界；需要 N-1/N-2/N-6 交叉核对。

风险：

- 这是发送路径上的观测点，任何阻塞、分配失败或日志异常都可能影响发送时序。
- 不得在调用前改写 `msg->data` 或 `msg->cursize`，不得改变返回值处理。
- 推荐只复制指针内容到有上限的临时缓冲，或在发送返回后按预登记元数据记录；不要跨帧持有 `msg` 指针。

### B.2.4 N-4：加密/封装前 netchan 明文

证据：

- `sv_net_chan.c:135-149`：`SV_Netchan_Transmit` 检查 `data` 和 `cursize`，`malloc` 后 `memcpy`，再 `SV_Netchan_Encode`，最后 `CODOL_NetchanSubmit`。
- `:146-148`：注释说明提交后释放临时编码缓冲，保留调用者明文供 snapshot-history validation 和 rejected retries 使用。

能证明什么：

- 该点位于加密/编码前，能看到与 N-3 相同的调用者明文，但层级更靠近传输封装。
- 不能提供内部 svc 消息边界；不能替代 N-1/N-2。
- 如果只记录密文，没有密钥和明文对照，不能恢复协议语义，也不应保存密钥。

风险：

- 所有 netchan 消息都会经过该点，频率和覆盖面比 N-3 更大。
- 复制/日志可能改变时序；`data` 指针生命周期只到函数返回，必须立即复制。
- 本轮不建议把 N-4 作为第一完整载荷观测点。

### B.2.5 N-5：可靠 server command

证据：

- `sv_snapshot.c:97-107`：循环写 `SV_WIRE_SERVERCOMMAND`、u32 command sequence、字符串。
- `sv_client.c:2293`：gamestate 消息内先发送未确认 server command。
- `sv_snapshot.c:818`：snapshot 开始阶段也调用该函数。

能证明什么：

- 可精确记录可靠命令的首字节、序号、字符串长度和消息偏移。
- 命令文本可能包含聊天、管理或会话信息；不应无条件落盘。

风险：

- 需要白名单/分类和长度上限；敏感文本必须先过滤或只记录哈希/类别。
- 不应把命令文本观测当成 gamestate 或 snapshot 的完整证据。

### B.2.6 N-6：snapshot 段级收尾

证据：

- `codol_snapshot.c:22-41`：段首、serverTime、delta、flags、base、section、EOF。
- `codol_snapshot.c:4-7`、`:14-45`：失败原因跟踪与 section 级错误记录。

能证明什么：

- 可验证 snapshot 段内字段和 EOF 的生成逻辑。
- 可与 N-2/N-3 的长度和字节位置做交叉核对。

限制：

- 段级记录不证明整包发送；也不证明客户端解析。
- 需避免把静态字段顺序直接当成客户端接受结果。

## B.3 现有非修改式观察路径

### B.3.1 `codol_debugTrace`

证据：

- `common.c:567-576`：`codol_debugTrace` 默认 0、范围 0-2；0 静默，1 movement/prediction，2 everything（bots、weapons、reliable commands）。
- `qcommon.h:80-91`：`CODOL_TRACE_ON()` 与 `CODOL_TRACE_VERBOSE()` 宏。
- `sv_snapshot.c:264-283`：当 trace 和 `developer` 都启用时，输出 `CoDOL snapshot clock`，含 client、seq、ack、delta、gap、server time、command time、lastcmd、age、rov、flags、stance、viewheight、lerp、ent0、pof。
- `sv_snapshot.c:249-252`、`:190-194`、`:845`：无 native frame、snapshot 写失败、pending mismatch 等日志原因。
- `START-CODOL-SERVER.cmd:196-198`：启动参数设置 `logfile 2`、`logrcon 1`、`developer %CODOL_DEVELOPER%`。

能证明什么：

- 在后续获授权的运行实验中，启用已有 trace 可在**不修改二进制**的情况下提供 snapshot 生成/准备的元数据和失败原因。
- 它不提供完整 gamestate/snapshot 载荷，也不直接给出 gamestate 段边界或客户端 opcode 分派结果。

限制：

- 高频同步日志会影响服务器时序；设计上应短时、限流、优先单客户端/小地图。
- 需要另行授权运行实验；本轮不得执行。
- 现有 trace 不能替代完整载荷捕获。

### B.3.2 网络层抓包

- 只能观察到加密/封装后的线上数据，不能在不接触密钥的前提下恢复完整明文。
- 不符合“不导出密钥”的边界，也不足以证明客户端解析语义。
- 因此不作为本设计的首选路径。

## B.4 行为影响分类

| 影响类型 | 源码可证明 | 仅运行时验证 |
|---|---|---|
| 缓冲区内容 | 只读复制不改 `msg->data`；若代码不写回，理论无内容变化 | 需要确认复制逻辑无越界、无别名写 |
| 消息长度 | 记录逻辑不修改 `msg->cursize` 时，长度不变 | 需要确认没有整数溢出、截断或并发修改 |
| 发送顺序 | 记录逻辑不调用发送/休眠/阻塞时，顺序理论不变 | 同步日志、内存分配和锁可能改变实际时序 |
| 返回值/错误处理 | 不替换 `SV_Netchan_Transmit` 返回值时，源码级不变 | 日志失败、异常或调试器暂停可能改变行为 |
| 内存生命周期 | 必须立即复制 `msg->data`/`data`，不跨帧持有 | 需要运行时确认指针在复制期间有效 |

**裁决：** 任何 N-1..N-6 的实现都属于运行实验候选，必须先做独立补丁审查、构建和授权；本轮只确认静态可设计性，**不确认其运行安全性**。

## B.5 推荐的最小观测流程（仅设计，不执行）

1. **元数据阶段**：在独立实验副本中，以短会话、单客户端、低风险地图启动服务端；通过现有 `codol_debugTrace`/`developer` 收集 snapshot clock 与失败原因。此阶段不记录完整载荷。
2. **段级阶段**：若元数据证明 snapshot 准备路径可达，则在实验副本中审查 N-1/N-2 的只读复制设计，验证 gamestate/snapshot 段的偏移、长度、首字节和 EOF。
3. **整包阶段**：仅在需要证明“实际交给 netchan 的完整消息”时，采用 N-3；记录 `msg->cursize`、首 4 字节、发送返回值，并对完整载荷做临时内存处理或脱敏后落盘。
4. **客户端阶段**：另行授权后，在同一实验会话中关联客户端日志的状态转换和错误行；不得由服务端生成或发送成功直接推断客户端解析成功。

## B.6 本轮未做事项

- 未生成、应用或编译任何补丁。
- 未启动客户端、服务端、launcher 或任何未知程序。
- 未注入进程、未附加调试器、未绕过保护机制。
- 未捕获、导出或保存认证秘密、密钥、完整会话凭据或无关用户数据。
- 未把任何候选观测点升级为运行实测结论。

## B.7 证据汇总

| 断言 | 状态 | 依据 |
|---|---|---|
| gamestate 序列化完成点可静态定位 | **CONFIRMED（源码级）** | `codol_sv_state.c:141-146` |
| snapshot 序列化/准备完成点可静态定位 | **CONFIRMED（源码级）** | `sv_snapshot.c:260-263`、`codol_sv_snapshot.c:85-130` |
| 发送前整包边界可静态定位 | **CONFIRMED（源码级）** | `sv_snapshot.c:688` |
| 加密前 netchan 明文点可静态定位 | **CONFIRMED（源码级）** | `sv_net_chan.c:143-145` |
| 现有 trace 可提供 snapshot 元数据 | **CONFIRMED（源码级）** | `sv_snapshot.c:264-283` |
| 上述任一观测点已运行验证 | **NOT_OBSERVED** | 本轮不运行 |
| 客户端 opcode 分派入口 | **INSTRUMENTATION_BLOCKED** | 09_C：间接分派/VMProtect 边界 |