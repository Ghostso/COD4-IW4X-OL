# 04 — 实际新增与修改代码

## 1. 新增库文件

| 文件 | 作用 | 证据等级 |
|---|---|---|
| `Core\Evidence.cs` | EvidenceLevel/Attribute、Guard、ByteUtil | 工程约定 |
| `Core\ProtocolVersion.cs` | 协议家族与三个显式版本 | FinalCodol=Unknown |
| `Transport\UdpDatagramTransport.cs` | UDP 生命周期、边界、错误分类、端口回报 | PROJECT_IMPLEMENTATION_CONFIRMED |
| `Sessions\ClientSession.cs` | 生命周期、超时、序号上下文 | PROJECT_IMPLEMENTATION_CONFIRMED |
| `Protocol\MixedBitReader.cs` | 混合位/字节游标读取与边界校验 | 项目证据 |
| `Protocol\ProtocolCodec.cs` | 解码结果模型 + 版本注册表 + 显式未实现解码器 | FinalCodol=Unknown |
| `Protocol\Versions\Local2697Wire.cs` | 2697 常量/读写辅助（隔离） | PROJECT_IMPLEMENTATION_CONFIRMED（非最终协议） |
| `Protocol\Versions\Local2697PacketReader.cs` | 2697 分片重组/重放窗口 | 同上 |
| `Protocol\Versions\Local2697PacketBuilder.cs` | 2697 服务端分片构造 | 同上 |
| `Protocol\Versions\Local2697ClientDatagramBuilder.cs` | 2697 客户端方向构造（测试用） | 同上 |
| `Reliable\ReliableCommandChannel.cs` | 内部序号/重传/重放拒绝 | 内部模型 |
| `GameState\GameStateModel.cs` | 权威/预测分离、configstring、快照 | 内部模型 |
| `Movement\MovementModel.cs` | 角度归一化、方向、积分、异常检测 | 内部模型 |
| `Diagnostics\Diagnostics.cs` | 分级诊断接口 | 工程约定 |
| `Diagnostics\JsonLineDiagnosticsSink.cs` | JSONL 诊断 + 构建摘要 | 工程约定 |

## 2. 新增测试文件

- `tests\Codol.BattleServer.Tests\Program.cs`：31 个测试，覆盖 B1–B6 与 F1–F3 要求。

## 3. 修复的真实缺陷

1. **传输层绑定端口 0 不回报实际端口** → 修复为绑定后回读 `socket.LocalEndPoint`。
2. **2697 读写方向混淆风险** → 显式拆分为 Server 方向 builder 与 Client 方向 builder。
3. **可空警告** → 消除，构建零警告。

## 4. 未实现（显式）

- 最终 CODOL handshake / opcode 表 / reliable-command 线格式 / snapshot 解码 / gamestate consumer。
- 任何将内部结构写入最终 CODOL 线上格式的代码。
