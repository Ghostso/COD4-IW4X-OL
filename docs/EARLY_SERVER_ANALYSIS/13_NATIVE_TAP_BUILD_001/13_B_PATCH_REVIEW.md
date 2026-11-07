# 13 — B：候选观测补丁审查

> 任务：`EARLY-NATIVE-TAP-BUILD-001`
> 边界：只读源码审查与候选差异草案生成；**未应用补丁到实验副本、未编译、未运行服务端/客户端/launcher、未注入进程**。
> 状态词：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / NOT_OBSERVED / INSTRUMENTATION_BLOCKED / REFUTED。

## B.0 审查裁决

| 项目 | 裁决 | 状态 |
|---|---|---|
| 观测边界选择 | 采用 N-3 整包明文边界，即 `SV_SendMessageToClient` 之前、`SV_Netchan_Transmit` 之前 | **CONFIRMED（源码级）** |
| gamestate 调用点 | `src/sv_client.c:2312` 前一行；消息由 `SV_WriteGameState` 写入后、发送前 | **CONFIRMED（源码级）** |
| snapshot 调用点 | `src/sv_snapshot.c:933` 前一行；`SV_EndClientSnapshot` 已完成 EOF/恢复处理后、发送前 | **CONFIRMED（源码级）** |
| 是否只增加观测 | 从候选源码看只调用无返回值使用方；未发现直接写回 `msg`/`client` | **STRONG_CANDIDATE（源码审查）** |
| 是否证明无运行时扰动 | 未运行，同步 `fopen`/`fprintf`/`fflush` 可能影响时序 | **NOT_OBSERVED** |
| 是否能从该点准确界定内部 gamestate/snapshot opcode | 不能；`msg->data[0]` 是整个 netchan 消息首字节，不是内部段首字节 | **REFUTED（就“整包首字节即内部段 opcode”的推断而言）** |
| 候选 diff 是否能干净应用到实验源码 | 已在一次性临时副本上执行 `git apply --check`，5 个文件全部通过 | **CONFIRMED（仅限 apply-check，非编译）** |
| 候选头文件类型是否自洽 | 头文件直接 `#include "msg.h"`，不再重复 typedef；已消除 `struct msg_t` 冲突 | **STRONG_CANDIDATE（源码审查）** |
| 候选代码是否编译过 | 未编译（工具链缺失，见 `13_C`） | **INSTRUMENTATION_BLOCKED** |
| 旧 `n3_sv_snapshot_hook.diff` | 已被替代 | **SUPERSEDED** |

## B.1 候选观测点与既有设计对应

`11_B_NATIVE_OBSERVATION_POINTS.md:21-29` 定义 N-1 至 N-6：

| 编号 | 设计位置 | 本候选采用情况 |
|---|---|---|
| N-1 | `codol_sv_state.c:141-146` 后，gamestate 段级边界 | 未采用；可作为后续交叉核对 |
| N-2 | `sv_snapshot.c:260-263` 后，snapshot 段级边界 | 未采用；可作为后续交叉核对 |
| N-3 | `sv_snapshot.c:688`，`SV_Netchan_Transmit` 前整包 | **采用其协议阶段概念** |
| N-4 | `sv_net_chan.c:143-145`，`SV_Netchan_Encode` 前 | 未采用；覆盖面更广 |
| N-5 | `sv_snapshot.c:97-107`，serverCommand 序列化 | 未采用；可能涉及文本/敏感数据 |
| N-6 | `codol_snapshot.c:22-41`，snapshot 段内部字段 | 未采用；需另行关联偏移 |

本候选把观测调用放在两个**调用者发送前**位置，而不是直接改 `sv_snapshot.c:688` 内部公共发送函数：

- `src/sv_client.c:2312` 之前：gamestate 整包；
- `src/sv_snapshot.c:933` 之前：snapshot 整包。

这样可以把“消息类别”由调用点显式传入，避免仅凭首字节分类。

## B.2 源码上下文证据

### B.2.1 gamestate 调用点

源码：`experiment_copy/src/sv_client.c`。

- `:2273`：`client->state = CS_PRIMED`。
- `:2287`：写入 4 字节 reliable ACK。
- `:2293`：`SV_UpdateServerCommandsToClient`。
- `:2298`：`SV_WriteGameState(&msg, client)`。
- `:2299-2307`：overflow 时回滚并返回。
- `:2309-2311`：计算 `codolPacket`/`codolWireAck`。
- `:2312`：`SV_SendMessageToClient(&msg, client)`。
- 候选插入点：`:2311` 之后、`:2312` 之前。

调用链（继承 `09_A` 与 `13_A`）：

```text
SV_SendClientGameState
  -> SV_WriteGameState
     -> CODOL_WriteServerGamestate
        -> CODOL_WriteGamestate
           -> CODOL_WriteConfigstrings
  -> SV_SendMessageToClient
     -> SV_Netchan_Transmit
```

### B.2.2 snapshot 调用点

源码：`experiment_copy/src/sv_snapshot.c`。

- `:642`：`SV_SendMessageToClient` 定义。
- `:648`：CODOL 分支对 `msg->overflowed` 直接返回 `qfalse`。
- `:688`：`SV_Netchan_Transmit(client, msg->data, msg->cursize)`。
- `:759-769`：`SV_SendClientSnapshot` 调用 `SV_BeginClientSnapshot`、`SV_WriteSnapshotToClient`、`SV_EndClientSnapshot`。
- `:827-849`：`SV_EndClientSnapshot` 写 EOF / 处理恢复。
- `:927-935`：CODOL 发送块。
- `:933`：`SV_SendMessageToClient(msg, client)`。
- 候选插入点：`:930-932` 计算 `packet`/`wireAck` 之后、`:933` 之前。

### B.2.3 出网与编码边界

`experiment_copy/src/sv_net_chan.c`：

- `:135`：`SV_Netchan_Transmit`。
- `:140`：拒绝 `cursize < 4` 或超过 `NETCHAN_UNSENTBUFFER_SIZE`。
- `:141-148`：复制、`SV_Netchan_Encode`、`CODOL_NetchanSubmit`、释放副本。
- `:92-99`：`SV_Netchan_Encode` 对前 4 字节之外的数据做 XOR。

因此候选插入点位于：

- **序列化之后**；
- **`SV_SendMessageToClient` 之前**；
- **`SV_Netchan_Encode` 之前**；
- **网络提交之前**。

## B.3 关键限制：整包首字节不等于内部段 opcode

`09_A_SERVER_MESSAGE_LEDGER.md:23-33` 已记录 gamestate 整包布局：

```text
4-byte reliable ACK
[0x01 + u32 seq + cstring] serverCommand*
gamestate segment (0x02)
configstring substream (0x03)
...
EOF (0x05)
```

snapshot 路径同样可能先包含：

- 4 字节 ACK；
- serverCommand 块；
- 后续 snapshot 段。

**修正后的候选逻辑（`n3_observer.c`）：** 观察器**不再**用 `msg->data[0]` 推断消息类别。`kind` 字段完全由调用点显式传入（`"gamestate"` / `"snapshot"`），首字节只作为 `wire_byte0` 原样记录，并固定打印 `segment_opcode=unknown`：

```c
static const char *CODOL_NativeTapKind(const char *kind)
{
    if (kind && kind[0]) return kind;
    return "unclassified";
}
...
"wire_byte0=0x%02x segment_opcode=unknown fnv64=%016llx\n"
```

裁决：

- `msg->data[0]` 能证明**整包首字节**；
- 它**不能**证明内部 gamestate/snapshot 段 opcode；
- 之前“用首字节 2/0 分类 gamestate/snapshot”的草稿逻辑已删除，该推断为 **REFUTED**；
- 若目标是证明内部段首字节，必须增加 N-1/N-2 段级观测或解析偏移（不在本候选内）。

## B.4 候选文件审查

### B.4.1 `patch_candidates/n3_observer.h`

当前审查版本（自包含，不再重复 typedef）：

```c
#ifdef CODOL_SERVER
#include "msg.h"

struct client_s;

void CODOL_NativeTapObserveMessage(const char *kind, struct client_s *client,
                                   msg_t *msg);
#else
static inline void CODOL_NativeTapObserveMessage(const char *kind, void *client,
                                                 void *msg)
{
    (void)kind;
    (void)client;
    (void)msg;
}
#endif
```

源码类型事实：

- `experiment_copy/src/server.h:128`：`struct client_s { ... };`
- `:246`：`typedef struct client_s client_t;`
- `experiment_copy/src/msg.h:49-63`：`typedef struct { ... } msg_t;`，是**匿名结构体 typedef**，没有 `struct msg_t` 标签。

修正历史：

- 早期草稿写 `struct msg_s; struct msg_s *msg;`，与 `msg.h` 的 `msg_t` 不匹配；
- 随后草稿写 `typedef struct msg_t msg_t;`，会与 `msg.h` 的匿名 `msg_t` typedef 冲突（在已包含 `msg.h` 时属重复 typedef，可能编译失败）；
- 当前版本改为**直接 `#include "msg.h"`**，`client_s` 仅前向声明，从而使用树中唯一的 `msg_t` 定义，消除了上述冲突。

状态：**STRONG_CANDIDATE（源码审查）；编译验证因工具链缺失为 INSTRUMENTATION_BLOCKED。**

### B.4.2 `patch_candidates/n3_observer.c`

候选行为：

- 整个翻译单元用 `#ifdef CODOL_SERVER` 包裹，非 CODOL 目标下为空单元；
- 默认 `codol_nativeTapLog=0`，不写文件；
- 启用后写：
  - `kind`（调用点显式传入）
  - `direction=s2c`
  - `state`
  - `client` slot
  - `seq`
  - `len`
  - `wire_byte0`（整包首字节）
  - `segment_opcode=unknown`（占位，避免误读）
  - FNV-1a 64 位摘要；
- `codol_nativeTapPayload=1` 时才写完整十六进制载荷。

源码审查结论：

- 未发现对 `msg->data`、`msg->cursize`、`msg->bit`、`msg->maxsize`、`msg->overflowed` 的写操作；
- 未发现对 `client->state`、netchan 状态或发送返回值的写操作；
- 未发现读取认证密钥、私钥、认证凭据；
- 但 `fopen`、`fprintf`、`fflush` 是同步 I/O，运行时对发送时序、帧节奏的影响为 **NOT_OBSERVED**。

### B.4.3 `patch_candidates/n3_hooks.diff`

当前版本为单文件 unified diff，包含 5 个文件：

- `src/common.c`：声明并注册 cvar；
- `src/sv_client.c`：包含头文件，在 gamestate 发送前调用观察器；
- `src/sv_snapshot.c`：包含头文件，在 snapshot 发送前调用观察器；
- `src/n3_observer.c`：新增观察器实现；
- `src/n3_observer.h`：新增观察器接口。

验证：

- 在一次性临时副本（仅含 3 个待改文件）上执行 `git apply --check`，5 个文件全部通过；
- 该检查只证明补丁能**干净应用**，不证明能编译，也不证明运行时无扰动。

状态：**CANDIDATE（审查草案）**；未应用到 `experiment_copy`，未编译。

### B.4.4 `patch_candidates/n3_sv_snapshot_hook.diff`

该旧草案已被当前版本替代，标记：

**SUPERSEDED — review draft only; do not apply or build.**

## B.5 行为影响与风险

| 风险 | 源码可证明结论 | 状态 |
|---|---|---|
| 改写消息缓冲区 | 候选未写 `msg->data`/`cursize`/`bit` | **STRONG_CANDIDATE（源码审查）** |
| 改变消息长度 | 无写长度字段 | **STRONG_CANDIDATE（源码审查）** |
| 改变发送顺序 | 调用位于发送前，未发现控制流改写 | **STRONG_CANDIDATE（源码审查）** |
| 改变返回值 | 观察函数为 `void`，调用方未使用其返回值 | **STRONG_CANDIDATE（源码审查）** |
| 改变错误处理 | 未插入 return/error path | **STRONG_CANDIDATE（源码审查）** |
| 时序扰动 | 同步文件 I/O 可能阻塞发送路径 | **NOT_OBSERVED** |
| 缓冲区生命周期 | 调用点在 `msg` 仍有效、发送前；未复制后异步访问 | **STRONG_CANDIDATE（源码审查）** |
| 高频开销 | snapshot 可达帧级频率，默认关闭；开启后仍有开销 | **CANDIDATE** |
| 编译可行性 | 未编译，类型自洽性仅静态审查 | **INSTRUMENTATION_BLOCKED** |

`11_E_RISK_AND_ROLLBACK.md:143-150` 要求：只读复制、不写回关键字段、完整载荷优先临时内存处理、所有构建和运行都在实验副本中进行。当前候选符合“只读复制”的源码意图，但完整载荷落盘策略尚未进入可执行审查。

## B.6 与认证秘密的边界

候选默认只写元数据和摘要；不读取或输出：

- 密钥文件；
- 私钥；
- 完整会话凭据；
- 认证 token；
- MAC。

`codol_nativeTapPayload=1` 时会写整包十六进制，其中可能包含 userinfo、聊天文本或其他会话数据。因此：

- 默认模式：可作为后续最小观测候选；
- 完整载荷模式：**未批准**，必须先做秘密过滤设计并单独审查；
- 若无法证明过滤有效，运行实验必须只保留元数据。

## B.7 结论

- N-3 整包观测点本身可由源码确认；
- 候选调用点明确、可审查；
- 候选 diff 已改为标准 unified diff，并已通过一次性副本上的 `git apply --check`；
- 观察器不再把整包首字节解释为目标 gamestate/snapshot opcode，只记录 `wire_byte0`；
- 同步 I/O 的运行时扰动未被证明；
- 候选代码**未编译**（工具链缺失），因此“可编译”仅为静态审查结论；
- 综合：**设计草案有条件通过；构建与运行仍为 NO-GO。**

## B.8 后续最小修正项（若进入下一轮）

1. 在具备 32 位 MinGW/MSYS2 工具链的环境中，仅对候选做对象编译以确认零警告/零错误；
2. 在 `experiment_copy` 中应用前先复核 `git apply --check` 与逐 hunk 对照；
3. 仅以默认元数据模式做首轮运行；
4. 若确需内部 gamestate/snapshot opcode，增加 N-1/N-2 段级交叉核对，而非依赖 N-3 整包首字节；
5. 完整载荷模式保持关闭，直至秘密过滤方案单独审查通过。