# 02 — 模块复用矩阵

> 分类：`REUSE`、`ADAPT`、`REIMPLEMENT`、`BLOCKED`、`OPTIONAL`。
> 证据来源优先使用已有报告、源码函数/RVA，不把同名函数默认视为同版本行为。

| 模块 | 已有实现/资产 | 分类 | 证据与适配点 | 当前缺口 |
|---|---|---|---|---|
| 网络传输 UDP/Recv/Send | C# `Engine/UdpTransport.cs`；旧 `src/netchan.c` 的 `Netchan_Init/Setup/Transmit`；旧 `codol/net/codol_network.c` | ADAPT | C# 有 socket 主循环；旧源码有完整 netchan/分片/loop | 2697 wire 加密、端口/会话描述符和真实客户端连通未验证 |
| Netchan/分片/重排 | 旧 `netchan.c` + `codol/net/codol_netchan.c`；C# `CodolProtocol` 已有 DATA 记录 | ADAPT | 旧源码记录层/重放窗口/分片逻辑可参考；C# 有 AES/HMAC/序列号实现 | 旧版与 2697 的版本偏移/冲突需离线复算 |
| 握手与连接状态机 | 旧 `codol_handshake.c`、`codol_connect.c`；C# `ClientLogic`、`CodolProtocol` | ADAPT | getchallenge/connectResponse、P-224、cookie、CS_PRIMED 有源码/测试 | COOKIE_ECHO 长度冲突；真实 2697 客户端握手未观测 |
| 消息序列化基础 | 旧 `msg.c` 的 `MSG_WriteByte/Short/Long/Data/String/Bits` | REUSE/ADAPT | 语言无关消息游标和读写原语；可作为字段层参考 | 2697 字段顺序和分支需按 2697 服务端重验 |
| Reliable command | 旧 `codol/net/codol_client_command.c`；C# `ClientCommandReader.cs`；E3 `0x8612E` | ADAPT/BLOCKED | 服务端 2697 新格式已确认；旧源码有命令队列/分发器 | 客户端 `0x02` 分派未闭合；不能只凭字段形状认定一致 |
| Gamestate | 旧 `codol/snapshot/codol_game.c`、`codol_configstrings.c`；E1 2697 writer | ADAPT/BLOCKED | 2697 有真实 gamestate 调用、门控和编码路径；旧源码有数据模型 | 客户端 `0x03` 读取/初始化状态未验证；`0x06` 语义未知 |
| Snapshot | 旧 snapshot 76 文件；C# `MotionSnapshot.cs`、`GameWorld.cs`；E2 `0xA4860` | ADAPT/BLOCKED | 旧源码有实体/玩家/delta/快照框架；C# 有 bit-level 快照 | 2697 与旧版串行化差异；客户端 delta/EOF/实体解析未闭合 |
| Configstring | 旧 `codol_configstrings.c`；E1 `0xA0468` | ADAPT/BLOCKED | 2697 opcode/顺序/终止符已确认；旧源码有索引/数据来源 | 6519 索引语义、客户端 consumer、动态更新未验证 |
| 地图与资源 | 2697 `runtime-assets`（FF/地图/UI）；旧 assets/GSC 树 | REUSE/ADAPT | 资源已与 2697 服务端配套；FF 数据可直接作为本地资产来源 | 资源加载器、脚本编译、索引转换依赖引擎内部结构 |
| 游戏状态/实体 | 旧 `sv_game.c`、`sv_client.c`、游戏模块；ol-mod `server_mp` | ADAPT | 有玩家、entity、spawn、基础模式框架 | 2.6.9.7 版本 state layout/pmove 需重验；ol-mod 为 3.3.3.3 |
| 武器子系统 | 旧 `codol/weapon`；2697 attachment registry；ol-mod weapon 源码 | OPTIONAL/ADAPT | 后置模块；首个 MVP 只需基础武器/默认 loadout | 2697 新武器/引擎状态依赖，不应进入 M0–M4 |
| 平台依赖 | TenProxy、IIPS/IFS、TCLS；Python lobby 研究 | OPTIONAL/BLOCKED | 已有协议/运行研究报告；本地启动可能绕开下载层但不是安全绕过 | 认证/启动门控的实际必要性需定向验证 |
| 启动与配置 | 2697 `run_native_connection.py`、`room_host2697.py`；旧源码配置手册 | ADAPT | 已有 `codol_target2697`、`codol_clientExe`、`runtime-assets`、`scripts` 等参数样例 | 2697 注册/资源对象门控和初始化依赖未完全闭合 |
| 会话描述符/大厅 | C# `SessionDescriptor.cs`、`SessionExporter.cs`；Python lobby handoff | REUSE/ADAPT | 258B session、16B securityKey、endpoint 导出已实现 | 与 2697 客户端大厅版本关系未验证 |
| 构建/测试 | C# 122 项 selftest；旧源码回归；ol-mod 测试 | REUSE | 可作为离线回归基础 | 旧工具链缺失；构建通过不等于客户端兼容 |

## 最关键分类

- **REUSE**：C# 基础传输/密码原语/会话描述符/离线回归；旧源码的消息游标与 netchan 结构；2697 runtime-assets。
- **ADAPT**：Handshake、netchan、reliable command、gamestate/configstring/snapshot 的 2697 字段/分支。
- **REIMPLEMENT**：2697 专属客户端兼容层、未闭合的 opcode 分派消费、缺失的资源/脚本桥。
- **BLOCKED**：客户端 0x02→`0xA2E50` 分派、0x06 语义、2697 注册门控的合法运行路径。
- **OPTIONAL**：2697 完整武器子系统、PvE booking、结算、持久化、反作弊/平台生产依赖。
