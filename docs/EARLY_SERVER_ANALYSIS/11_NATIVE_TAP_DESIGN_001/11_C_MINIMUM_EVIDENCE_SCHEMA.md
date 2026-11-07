# 11 — C：最小证据格式与秘密材料边界

> 任务：`EARLY-NATIVE-TAP-DESIGN-001`，只读设计。
> 本文件只定义后续实验的记录格式，不执行捕获、不启动程序、不落盘秘密材料。
> 状态词仅使用：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / NOT_OBSERVED / INSTRUMENTATION_BLOCKED / REFUTED。

## C.0 结论先行

后续若获授权进行运行实验，最小证据格式必须同时满足：

1. **可按会话、方向、消息类别、序号和捕获阶段关联**；
2. **可证明消息边界、准确长度和首字节**；
3. **可关联客户端状态转换与错误日志**；
4. **默认不记录认证秘密、密钥、完整凭据或无关用户数据**；
5. **完整载荷仅在隔离环境的临时内存中优先处理；必须落盘时先做秘密过滤**。

本轮只定义 schema，不生成任何捕获文件。

## C.1 记录单位

建议每条消息记录为一个 JSONL 对象；如后续需要 CSV，可从 JSONL 导出扁平字段，但不要丢失嵌套的 `payload` 引用与 `error_refs`。

```json
{
  "schema_version": "codol-native-tap-1",
  "session_id": "s-<random-128-bit-hex>",
  "event_id": 1,
  "timestamp_utc": "YYYY-MM-DDTHH:MM:SS.sssZ",
  "timestamp_monotonic_ms": 0,
  "direction": "s2c",
  "message_category": "snapshot",
  "capture_stage": "pre_netchan_transmit",
  "capture_location": "sv_snapshot.c:688",
  "server_build_ref": {
    "path": ".../codol_dedrun_next.exe",
    "sha256": "28366AE992310BFE41D3C8975EC8DBC36E4DE202CE438C1266E1A09E335DD98A"
  },
  "client_build_ref": {
    "path": ".../codoMP_client_shipRetail.exe",
    "sha256": "904436480938632A856B39DEA73FB94C9682B5A0EBF7FA619ECD5DD5475ED3B6"
  },
  "client_slot": 0,
  "outgoing_sequence": 123,
  "message_sequence": 123,
  "reliable_ack": 7,
  "wire_len": 1234,
  "payload_len": 1234,
  "opcode": "0x00",
  "opcode_source": "wire_byte_0",
  "payload_sha256": "<sha256>",
  "payload_temp_ref": "mem://session/s-.../event-1",
  "payload_storage": "memory_only",
  "client_state": "CA_PRIMED",
  "server_state": "CS_PRIMED",
  "correlation_id": "s-...:seq-123",
  "error_log_refs": [],
  "redaction": {
    "applied": true,
    "classes": ["credentials", "keys", "user_identifiers", "chat_text"],
    "notes": "no secret material persisted"
  },
  "notes": ""
}
```

## C.2 必填字段

| 字段 | 类型 | 必填 | 语义 | 证据用途 |
|---|---|---|---|---|
| `schema_version` | string | 是 | 固定版本号 | 格式可复算 |
| `session_id` | string | 是 | 随机、非凭据、每次实验独立 | 会话关联 |
| `event_id` | integer | 是 | 会话内单调递增 | 去重与排序 |
| `timestamp_utc` | string | 是 | UTC 时间 | 与客户端日志对齐 |
| `timestamp_monotonic_ms` | integer | 是 | 单调时钟 | 时序/间隔分析 |
| `direction` | enum | 是 | `s2c` 或 `c2s` | 方向 |
| `message_category` | enum | 是 | `gamestate`、`snapshot`、`server_command`、`reliable_ack`、`other` | 消息类型 |
| `capture_stage` | enum | 是 | 见 C.3 | 协议阶段 |
| `capture_location` | string | 是 | 源码文件:行或可复算位置 | 证据定位 |
| `wire_len` | integer | 是 | 网络层消息准确长度 | 边界/长度 |
| `payload_len` | integer | 是 | 被记录明文长度；不记录载荷时也必须记录长度 | 边界/长度 |
| `opcode` | string/null | 是 | 首字节，如 `0x00`；无边界时为 `null` | 消息类型 |
| `opcode_source` | string/null | 是 | 如 `wire_byte_0`、`segment_byte_0`、`unknown` | 防止猜测 |
| `correlation_id` | string | 是 | 会话内跨日志关联键 | 双端关联 |
| `client_state` | string/null | 是 | 客户端状态快照 | 状态转换 |
| `server_state` | string/null | 是 | 服务端状态快照 | 状态转换 |
| `error_log_refs` | array | 是 | 客户端/服务端日志行引用 | 错误关联 |
| `redaction` | object | 是 | 过滤类别与结果 | 秘密材料边界 |

## C.3 `capture_stage` 允许值

| 值 | 含义 | 可获得的边界 |
|---|---|---|
| `post_gamestate_serialize` | gamestate 序列化完成后、发送前 | gamestate 段边界；需保存调用前游标 |
| `post_snapshot_serialize` | snapshot 准备/序列化完成后、收尾前 | snapshot 段边界；需处理 match-data 和 EOF |
| `pre_netchan_transmit` | 调用 `SV_Netchan_Transmit` 前 | 整条调用者消息边界 |
| `pre_netchan_encode` | `SV_Netchan_Encode` 前 | 整条明文；无内部消息边界 |
| `reliable_server_command` | `SV_UpdateServerCommandsToClient` 内 | 每条命令边界 |
| `snapshot_section` | `CODOL_WriteSnapshotDeltaNumber` 内 | 段级字段边界 |
| `console_trace` | 现有 `codol_debugTrace` 日志 | 只有元数据，无完整载荷 |
| `client_receive` | 另行授权的客户端接收观测 | 客户端接收边界 |
| `client_parse` | 另行授权的客户端解析观测 | 解析结果 |

## C.4 完整载荷处理规则

### C.4.1 优先级

1. **临时内存处理**：只在实验进程内按会话保存，不写入永久文件；会话结束立即丢弃。
2. **临时文件**：仅在独立实验副本的受控临时目录中短期保存，权限最小化，实验结束按保留期限删除。
3. **归档**：只有经过秘密过滤和人工审查的必要证据才允许归档。

### C.4.2 可记录的载荷

- gamestate 完整明文段；
- snapshot 完整明文段；
- `SV_Netchan_Transmit` 调用前的整包明文；
- 首字节、长度、序号、方向、捕获阶段；
- 必要的字段级解析结果和哈希。

### C.4.3 禁止记录或导出

- 认证密钥、私钥、对称密钥、密钥文件内容；
- 完整会话凭据、token、cookie、认证票据；
- 完整账号、XUID、真实 IP、完整 userinfo、聊天文本；
- 与目标会话无关的用户数据；
- 任何可用于伪造或绕过认证的材料；
- 秘密材料的原始哈希指纹（如项目既有规则禁止，则应完全跳过；如允许，只使用既有不可逆 `key_fp()` 形式，不得自建可关联指纹）。

### C.4.4 脱敏字段

- `user_identifier`：只保留类别或不可逆本地化占位符；
- `chat_text`：默认丢弃或替换为长度与类别；
- `address`：只保留方向/类别，不保留真实地址；
- `credentials`：永不记录；
- `keys`：永不记录，不计算哈希；
- `rcon`：命令和输出可能含敏感信息，必须白名单化或过滤。

## C.5 会话标识与关联

`session_id` 要求：

- 使用密码学随机数生成，至少 128 bit；
- 不包含账号、机器名、时间戳、IP、端口或凭据；
- 每次实验独立；
- 仅在本次实验目录内用于关联，不作为长期标识。

`correlation_id` 建议格式：

`<session_id>:<direction>:<outgoing_sequence>:<event_id>`

客户端状态关联：

- 服务端记录 `server_state` 和 `outgoing_sequence`；
- 客户端日志记录 `CA_*` 状态转换、时间戳和错误文本；
- 关联必须基于时间窗口、序号、方向和状态，不允许只凭“都在同一会话”自动推断。

## C.6 错误日志关联

允许归档的错误类别：

- 客户端：`bad command byte`、`ignoring illegible message`、`CL_GetSnapshot: truncated`、`EXE_CONFIGSTRINGMISMATCH`、`EXE_AWAITINGGAMESTATE`；
- 服务端：`no native frame for sequence`、`CoDOL gamestate rejected`、`pending snapshot sequence/preparation mismatch at end`、snapshot write failure；
- 服务端 trace：`CoDOL snapshot clock`。

`error_log_refs` 只保存：

- 日志文件相对路径或临时引用；
- 行号；
- 时间戳；
- 经过脱敏的错误类别/摘要。

不得把完整日志中的账号、IP、chat、rcon 或凭据一并归档。

## C.7 长度和边界计算要求

### C.7.1 N-1 gamestate

记录：

- 调用前 `msg->cursize`；
- `wire.size`；
- 调用后 `msg->cursize`；
- 段起始指针与长度的一致性；
- 首字节、末字节。

### C.7.2 N-2 snapshot

记录：

- 调用前 `msg->cursize`；
- 调用后 `msg->cursize`；
- `CODOL_ClientSnapshotPrepared` 状态；
- match-data 是否追加；
- 末字节是否为 EOF `0x05`。

### C.7.3 N-3 整包

记录：

- `msg->cursize`；
- `msg->data` 前 4 字节；
- `SV_Netchan_Transmit` 返回值；
- 发送前后 `client->netchan.outgoingSequence`；
- 是否发生失败回滚。

## C.8 证据等级映射

| 证据 | 能证明 | 不能证明 |
|---|---|---|
| 服务端源码行 | 编码逻辑和静态可达性 | 实际运行、实际发送、客户端接受 |
| 服务端元数据日志 | 生成/准备/失败阶段 | 完整载荷内容、客户端解析 |
| 服务端段级完整载荷 | 目标段被序列化及字节内容 | 整包发送、客户端接受 |
| 服务端整包完整载荷 + 发送成功 | 调用者实际提交整包 | 客户端接收、解析、状态转换 |
| 客户端接收记录 | 客户端收到字节 | 解码成功 |
| 客户端解析记录 | 解析路径执行 | 状态转换和后续行为 |
| 客户端状态转换 + 错误日志 | 行为级接受/拒绝 | 逐字段协议完全一致 |

## C.9 停止条件（证据格式相关）

出现以下任一情况即停止，不自动重试：

- 无法为消息确定方向、边界、长度或捕获阶段；
- 捕获内容包含无法可靠过滤的秘密材料；
- 载荷需要永久落盘但无脱敏方案；
- 客户端状态和错误日志无法与消息建立可靠关联；
- 实际输出与静态协议账本不一致且无法解释；
- 记录逻辑可能改变缓冲区、长度、发送顺序、返回值或错误处理。

## C.10 本轮未做事项

- 未生成任何 JSONL/CSV 捕获；
- 未记录任何完整载荷；
- 未读取、复制、哈希或导出密钥、私钥、认证凭据；
- 未运行客户端、服务端、launcher 或未知程序；
- 未生成可执行补丁。