# 10 — B：最小捕获范围与脱敏边界（Capture Minimum）

> 任务：`EARLY-SERVER-TAP-PREFLIGHT-001`，只读审查与实验设计。
> 本轮不执行抓包，不启动客户端/服务端，不落盘任何真实会话材料。
> 状态词仅使用：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / NOT_OBSERVED / INSTRUMENTATION_BLOCKED / REFUTED。

---

## B.0 一句话结论

最小捕获应聚焦 **s2c 游戏层明文消息边界与完整 gamestate/snapshot 载荷**，辅以 c2s ACK/序列对齐和客户端状态日志。认证密钥、私钥、MAC、完整会话凭据不进入捕获文件；长期秘密只允许以 `key_fp()` 形式的不可逆指纹出现。

当前 §4 的 Python tap diff 未应用且目标不存在，因此以下均为**重新设计的捕获要求**，不是对 §4 已存在能力的描述。

---

## B.1 目标会话与消息边界

### B.1.1 目标会话

- 客户端：当前 1.1.1.13 样本，SHA-256 `904436480938632A856B39DEA73FB94C9682B5A0EBF7FA619ECD5DD5475ED3B6`。
- 服务端：原生 CODOL fork，`codol_dedrun_next.exe`，SHA-256 `28366AE992310BFE41D3C8975EC8DBC36E4DE202CE438C1266E1A09E335DD98A`。
- 会话范围：从客户端连接/进入游戏到 `CA_ACTIVE`，至少覆盖首个 gamestate、首个基线 snapshot 和若干后续 delta snapshot。
- 传输层：当前原生路径为 UDP netchan；实际线上端口以实验副本配置为准，不能由本文件猜测。

### B.1.2 必须关联的边界

每条记录至少要能回答：

1. 方向：`c2s` 或 `s2c`。
2. netchan 消息边界：`messageSequence`、`reliableAcknowledge`（若可用）。
3. 消息内游戏层边界：从哪个偏移开始、长度多少、何时遇到 EOF `0x05`。
4. 首字节：gamestate `0x02`、configstring 子流 `0x03`、snapshot `0x00`、serverCommand `0x01`、EOF `0x05` 是否实际出现。
5. 消息顺序与时间：相对连接阶段、gamestate、首个 snapshot、后续 delta 的先后关系。

如果实现只能拿到整条 netchan 明文而不能给出内部消息边界，则必须把“整包完整载荷”和“消息内 svc 边界”分开记录，不能把前者当作后者。

---

## B.2 最小字段集

| 类别 | 字段 | 必要性 | 说明 |
|---|---|---|---|
| 会话标识 | `session_id`（本地随机/实验编号） | 必需 | 不记录真实账号、XUID、IP 之外的认证信息；可用哈希化连接标识 |
| 方向 | `dir` | 必需 | `s2c` 为主，`c2s` 仅用于 ACK/序号对齐 |
| 时间 | `ts`（epoch）、`t`（本地时间） | 必需 | 与客户端日志、服务端日志对齐 |
| netchan | `messageSequence` | 必需 | 发送顺序与 ACK 关联 |
| netchan | `reliableAcknowledge` | 必需 | 判断可靠命令/快照基线 |
| netchan | `outgoingSequence` / 服务端 frame 序号 | 强烈建议 | 与 `SV_SendMessageToClient` 的 frame 记录关联 |
| netchan | `cursize` / `wire_len` | 必需 | 长度必须为精确值，不能只记截断后的长度 |
| 游戏层 | `op`（首字节） | 必需 | 记录实际值，不预设含义 |
| 游戏层 | `payload_hex` | 必需 | gamestate/snapshot 完整明文；仅存实验目录，限时保留 |
| 游戏层 | `payload_len` | 必需 | 精确长度，与 `payload_hex` 长度一致 |
| gamestate | `seq` | 必需 | 与客户端日志和 ACK 对齐 |
| gamestate | `map`、`zone_type`、`gametype` | 必需 | 用于与静态账本比对 |
| gamestate | `const_crc` / `fs_crc` | 必需 | 用于识别 checksumFeed 相关差异 |
| gamestate | `configstring_count` | 必需 | 与子流 count 和客户端日志比对 |
| snapshot | `server_time` | 必需 | 段首 u32 |
| snapshot | `delta`、`flags`、`base_present` | 必需 | 基线/增量判定 |
| snapshot | 内部段边界（playerState/anim/actors/entities/clients/glass） | 强烈建议 | 至少记录每段偏移与长度，便于局部失败定位 |
| 上行 | `lastClientCommand`/ACK、`clc_move` 序号 | 强烈建议 | 仅用于对齐，不记录认证凭据 |
| 客户端 | 状态转换行 | 必需 | `CA_LOADING`、`CA_PRIMED`、`CA_ACTIVE` 及时间 |
| 客户端 | 错误行 | 必需 | `bad command byte`、`CL_GetSnapshot: truncated`、`CONFIGSTRINGMISMATCH`、overflow 等 |
| 服务端 | 发送结果/overflow/failure 原因 | 必需 | 证明消息是否实际提交给 netchan，以及是否失败 |
| 关联 | `correlation_id` | 必需 | 将 netchan 消息、游戏层载荷、日志行串起来 |

### B.2.1 gamestate 完整载荷

必须保存：

- `payload_len`；
- 完整 `payload_hex`；
- 首字节 `op=0x02`；
- `seq`、`map`、`zone_type`、`const_crc`、`clientNum`、`checksumFeed`；
- configstring 子流的起始偏移、长度、count、终止字节位置。

静态账本给出的预期布局见 `09_A_SERVER_MESSAGE_LEDGER.md:83-110` 和 `09_B_SVC_OPCODE_SYSTEMS.md`。捕获只是验证实际发送，不得反过来假设静态布局已经运行验证。

### B.2.2 snapshot 完整载荷

必须保存：

- `payload_len`；
- 完整 `payload_hex`；
- 首字节 `op` 的实际值（静态服务端预期为 `0x00`，见 `09_A:187-203`）；
- `server_time`、`delta`、`flags`、`base_present`；
- 段边界与 EOF `0x05` 的位置；
- 首个基线 snapshot 与至少若干 delta snapshot。

### B.2.3 消息首字节与消息类型

首字节只记录为“观察到的数值 + 所在消息 + 方向 + 偏移”，不得仅凭首字节把它升级为客户端已接受的消息类型。消息类型判定必须结合客户端日志和后续解析结果。

---

## B.3 方向、阶段与状态关联

| 阶段 | 服务端侧观察 | 客户端侧观察 | 关联键 |
|---|---|---|---|
| 连接/握手后 | 是否发送可靠命令、gamestate | `CA_CONNECTED`/加载阶段日志 | session_id + 时间 |
| gamestate | 完整 gamestate 明文、seq、长度 | `Received gamestate … bytes`、`CL_ParseGamestate` 行 | seq + payload_len + 时间 |
| 首个帧 | 首个 snapshot 完整明文、delta/flags | `CA_LOADING -> CA_PRIMED` | messageSequence + serverTime |
| 激活 | 后续 snapshot、发送结果 | `CA_PRIMED -> CA_ACTIVE` | messageSequence + ACK |
| 异常 | overflow/failure/发送失败 | `bad command byte` 等错误 | 时间窗口 + 相邻 messageSequence |

客户端日志中的 `Received gamestate from server, 6691 bytes` 等行只能证明**该次运行客户端消费了某个服务端的 gamestate**，不能自动证明它是本仓库原生序列化器。必须用本次实验的 `payload_len` 与日志字节数逐条对齐后，才能升级为“客户端收到/解析本次服务端消息”。

---

## B.4 秘密材料排除策略

### B.4.1 绝不落盘

- `securitykey.bin` 的原始内容；
- `c1_keys.bin` 的原始内容；
- 私钥、证书私钥、长期会话密钥；
- 认证令牌、MAC、完整会话凭据、可重放的 challenge/response；
- 玩家账号、XUID、真实 IP、完整 userinfo（除非已做不可逆或本地化脱敏）。

### B.4.2 允许的替代表示

- 长期密钥：只允许 `key_fp(key)`，即 `"sha256:" + sha256(key).hexdigest()[:12]`（`lobby\demonware\dw_wire.py:78-81`）。
- 已知脱敏实例：`{"dir":"lobby","layer":"seckey","kind":"write","source":"live-observed","key":"sha256:db8a6df1a30b","ok":true,"conn_gen":1}`。该形式说明可以区分密钥是否变化，但不能还原密钥。
- 短报文头字段（如 messageSequence、challenge、serverId 的 u8 分量）如确为 XOR key 复算所需，可作为协议字段记录；但不得与任何长期秘密拼接后落盘。

### B.4.3 bytes 与文本处理

- 复用 `wire_tap.safe()` 的截断语义：bytes 记录为 `{"b": 前 blob_cap 字节 hex, "len": 精确长度}`（`wire_tap.py:62-81`）。
- 但 gamestate/snapshot 的“完整载荷”要求与默认 256 B 截断冲突。完整游戏层载荷必须使用**专用、限时、限目录**的记录通道，不能把默认 `safe()` 截断后的前 256 B 当作完整载荷。
- 命令文本、聊天文本、userinfo 字符串应做白名单/长度上限/模式过滤；玩家名等如需保留，必须本地化或哈希化。
- 捕获文件只保留游戏层协议证据，不保存认证握手原始帧。

### B.4.4 访问与保留

- 捕获文件只写入实验副本目录，不写入原始样本目录、既有报告目录或可运行基线目录。
- 设置短保留期（建议实验结束后立即分析、确认无长期需要后删除）。
- 记录文件权限和哈希；分析工具只读打开捕获文件。
- 如无法可靠过滤秘密材料，立即停止，不生成捕获文件。

---

## B.5 最小实验观察矩阵

| 观察项 | 最小要求 | 能证明什么 | 不能证明什么 |
|---|---|---|---|
| 服务端源码 | 只读账本与行号 | 编码逻辑与预期字节 | 实际运行是否走该路径 |
| 服务端完整发送消息 | 发送前完整明文 + 返回值 | 服务端确实提交了这些字节 | 客户端是否收到 |
| 客户端接收 | 客户端日志/接收点证据 | 客户端收到某个消息 | 客户端是否成功解析 |
| gamestate 解析 | `CL_ParseGamestate` 完成、无坏命令 | gamestate 被解析 | snapshot 是否处理 |
| snapshot 处理 | 无截断/坏命令，进入后续状态 | snapshot 被处理 | 游戏层行为是否完全正确 |
| 状态转换 | `CA_PRIMED -> CA_ACTIVE` | 客户端进入可显示视图状态 | 所有后续游戏功能都正确 |

---

## B.6 停止条件（捕获相关）

出现以下任一情况即停止，不自动重试：

- 捕获需要导出认证秘密或无法可靠过滤秘密材料。
- 目标进程/插桩点无法唯一确认。
- 捕获会改变原始网络行为且无法隔离其影响。
- 捕获输出与静态协议账本不一致，且无法解释差异。
- 客户端或服务端出现非预期崩溃、文件改写或基线漂移。

---

## B.7 本轮未做事项

- 未执行捕获。
- 未启动客户端、服务端或 launcher。
- 未读取或导出任何密钥材料。
- 未把静态布局写成已运行验证的事实。