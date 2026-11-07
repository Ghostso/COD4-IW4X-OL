# 03 — 服务器架构

## 1. 分层

```
UDP Datagram (Transport)
   -> ClientSession lifecycle (Sessions)
   -> ProtocolCodecRegistry (Protocol)
        -> FinalCodolGameDecoder   (NOT IMPLEMENTED, explicit)
        -> Local2697*               (isolated, project-confirmed only)
   -> ReliableCommandChannel (internal sequence model)
   -> GameStateModel / GameStateSnapshot (internal model)
   -> MovementModel (internal prediction/authority checks)
   -> IDiagnosticsSink (structured diagnostics)
```

## 2. 边界规则

1. Transport 只处理数据报，不解释语义。
2. 协议版本必须**显式选择**；不存在默认回退到 2697。
3. 未证实的握手 → `HandshakePending`，只能由 `MarkConnectedByVerifiedHandshake(true)` 进入 `Connected`。
4. 未证实的 gamestate consumer → 禁止进入 `Active`。
5. 内部 GameState/Snapshot 结构不得直接序列化为 CODOL 线上格式。
6. 可靠命令只实现内部序号/重传模型，线格式保持未实现。

## 3. 依赖方向

- `Codol.BattleServer` 不依赖网络资源、不依赖客户端、无第三方运行时依赖。
- `Codol.BattleServer.Tests` 仅引用库工程。
- 所有诊断可注入，测试使用 `InMemoryDiagnosticsSink`。
