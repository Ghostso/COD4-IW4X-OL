# 02 — 现有代码审计

## 1. 模块清单

| 模块 | 现有状态 | 047 处置 |
|---|---|---|
| `Net\UdpTransport.cs` | 已有、可用、非阻塞接收 | 重新实现为 `UdpDatagramTransport`，补 MaxDatagramSize/错误分类/实际端口回报 |
| `Engine\ClientSession.cs` | 已有，但状态与 2697 传输字段耦合 | 拆出纯生命周期 `Sessions\ClientSession`，握手未验证时强制断开 |
| `Codol\CodolProtocol.cs` | 已有，实机抓包链路证据 | 保留在基线；不在 047 作为最终 CODOL 协议 |
| `Codol\Codol2697Protocol.cs` | 已有，2697 netchan/分片/重放窗口 | 隔离移植为 `Protocol\Versions\Local2697*`，注册表默认不装载 |
| `Codol\ClientCommandReader.cs` | 已有，混合位/字节 usercmd 读取 | 抽象为 `Protocol\MixedBitReader`（边界安全，附测试） |
| `Codol\MotionSnapshot.cs` | 已有，项目侧快照写侧 | 不并入最终协议；047 内部模型与其区分 |
| `Engine\GameWorld.cs` | 已有，权威实体表/运动积分 | 重新实现为 `GameState\GameStateModel`（权威/预测分离） |
| `Engine\PlayerIdentity.cs` | 已有，可恢复玩家状态 | 基线保留；不在 047 作为协议层 |
| `Net\Logger.cs` | 已有，控制台+文件日志 | 替换为 `IDiagnosticsSink` + JSONL 实现 |
| `build\build.ps1` | 依赖 .NET Framework csc.exe | 047 改用 `dotnet` SDK 构建（net8.0） |

## 2. 分类结论

- **已有且测试通过（原工程自测）:** codec/握手/运动学等 251 项断言（原始工程 README 记录）。
- **已有但未经验证:** 与最终 CODOL 客户端的任何线上兼容性。
- **仅有参考代码:** 2697 是本地上游语料，不是最终 CODOL 协议。
- **缺失:** 最终 CODOL handshake、opcode 分派、reliable-command 线格式、snapshot 解码、gamestate consumer。
- **对应关系未知:** 项目侧 usercmd/snapshot 宽度表与官方线格式（046 已判 `PARTIAL_MAPPING`/否证）。
