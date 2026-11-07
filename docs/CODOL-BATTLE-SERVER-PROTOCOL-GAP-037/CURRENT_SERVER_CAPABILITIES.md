# CURRENT_SERVER_CAPABILITIES — 现有服务器能力清单

**证据来源：** `CODOL-Combat-Server-v0.1` 正式源码、配置、FREEZE-005 证据包。  
**口径：** 本文件只声明“服务器已实现并能自证什么”，不声明“目标客户端已验证接受”。

---

## 1. 能力总览

| 能力 | 实现位置 | 状态 | 说明 |
|---|---|---|---|
| UDP 绑定/收发 | `src/Net/UdpTransport.cs` | `SERVER_IMPLEMENTED`、`TEST_VERIFIED` | 绑定 `127.0.0.1:28960`；FREEZE-005 已观察真实 socket |
| 主循环与调度 | `src/Engine/ServerHost.cs:242-284` | `SERVER_IMPLEMENTED`、`TEST_VERIFIED` | 128 Hz 帧推进；每 tick 收包、推进世界、调 `ClientLogic.Update()` |
| NAT 探针回复 | `src/Codol/CodolProtocol.cs:73-90` | `SERVER_IMPLEMENTED`、`TEST_VERIFIED` | 校验尾部 6B 为发送方地址，首字节改 `0x0C` 原样回 |
| DTLS-like cookie | `src/Codol/CodolProtocol.cs:109-130` | `SERVER_IMPLEMENTED`、`TEST_VERIFIED` | 38B cookie，含 clientTag/serverTag/timestamp |
| P-224 key exchange | `src/Codol/P224.cs`、`ClientLogic.cs:206-245` | `SERVER_IMPLEMENTED`、`TEST_VERIFIED` | 校验 cookie/serverTag，派生 24B transport key，发 114B ack |
| 数据帧封装 | `src/Codol/CodolProtocol.cs:192-244` | `SERVER_IMPLEMENTED`、`TEST_VERIFIED` | 16B header + HMAC-SHA1(8B) + AES-128 keystream XOR |
| OOB 文本收发 | `ClientLogic.cs:247-301`、`CodolProtocol.cs:246-270` | `SERVER_IMPLEMENTED` | `FF FF FF FF` + 文本；处理 getchallenge/connect/heartbeat/stats/cancelConnect/gamestateupdate |
| legacy 13B netchan | `ClientLogic.cs:314-328`、`670-704` | `SERVER_IMPLEMENTED`、`TEST_VERIFIED` | 旧 3.3.3.3 抓包链路；有离线复放 |
| 2697 netchan | `src/Codol/Codol2697Protocol.cs`、`ClientLogic.cs:334-375` | `SERVER_IMPLEMENTED`、`TEST_VERIFIED` | 4B/6B 头、29-bit mask、分片、XOR body；来自 2697 服务端证据 |
| 玩家命令解析 | `src/Codol/ClientCommandReader.cs`、`ClientLogic.cs:377-449` | `SERVER_IMPLEMENTED`、`TEST_VERIFIED` | 可靠命令 + usercmd；含基线校验与截断处理 |
| 权威实体表 | `src/Engine/GameWorld.cs`、`ClientLogic.cs:524-560` | `SERVER_IMPLEMENTED`、`TEST_VERIFIED` | slot↔entityId↔会话一一对应；有不变式测试 |
| gamestate/configstring | `GameWorld.Build2697GameState`、`ClientLogic.PumpGameState` | `SERVER_IMPLEMENTED` | legacy 用 259B 实机素材；2697 用服务端写入链 |
| snapshot 编码 | `src/Codol/MotionSnapshot.cs`、`ClientLogic.PumpSnapshot` | `SERVER_IMPLEMENTED` | legacy 位级格式；2697 默认禁用 |
| 会话生命周期 | `ClientLogic.cs:563-590` | `SERVER_IMPLEMENTED`、`TEST_VERIFIED` | 握手超时/静默超时/取消/满员/停机清理 |
| 重连状态 | `ClientLogic.cs:592-668` | `SERVER_IMPLEMENTED`、`TEST_VERIFIED` | 默认 Off；Identity 模式仅按 `\xuid\` |
| 会话描述符导出 | `SessionExporter.cs`、`SessionDescriptor.cs` | `SERVER_IMPLEMENTED`、`TEST_VERIFIED` | 导出 258B/268B/237B 对象与 16B securityKey |
| 构建与自测 | `build/build.ps1`、`SelfTest.cs` | `SERVER_IMPLEMENTED`、`TEST_VERIFIED` | 正式基线证据：构建 PASS、251/251 自测 PASS |

---

## 2. 协议模式与默认配置

- 默认：`protocol_mode = legacy3333`（`config/combat_server.cfg`）。
- 可切换：`protocol_mode = codol2697`。
- 默认 `enable_experimental_snapshot2697 = 0`。
- `ServerHost.cs:119-121` 明确：2697 且未开启实验 snapshot 时，“snapshot 发送保持关闭”。
- `PumpSnapshot` 在 2697 模式且未开启实验时直接返回，日志写“不下发：2697 snapshot 帧边界/delta 基准仍是 BLOCKED”。

**结论：** 默认模式不是目标版本已证实协议；它是旧抓包链路。2697 模式也不是目标 3.19.26.22 已闭合协议，它来自本地 2697 服务端证据。

---

## 3. 连接建立至发送状态的实际接线

```text
UdpTransport.TryReceive
  -> ServerHost.Run 主循环
     -> ClientLogic.HandlePacket
        -> 已有 transport: TryReadData -> HandlePlain
           -> OOB: getchallenge/connect/heartbeat/stats/cancelConnect/gamestateupdate
           -> 非 OOB: legacy 或 2697 netchan
        -> NAT / cookie / key exchange 阶段
     -> GameWorld.Frame(dt)
     -> ClientLogic.Update
        -> PumpGameState
        -> PumpSnapshot
```

关键源码位置：

- `ServerHost.cs:256-273`：收包并调用 `_logic.HandlePacket`。
- `ServerHost.cs:275-281`：推进世界并调用 `_logic.Update`。
- `ClientLogic.cs:87-204`：包入口与握手分派。
- `ClientLogic.cs:247-301`：OOB 与连接内消息分流。
- `ClientLogic.cs:730-778`：gamestate 发送。
- `ClientLogic.cs:780-868`：snapshot 发送。

---

## 4. 已实现但**未被目标证据支持**的关键模块

| 模块 | 服务器实现 | 目标证据 | 当前处置 |
|---|---|---|---|
| legacy 13B netchan | 有 | 无 3.19.26.22 直接证据 | 保留旧模式，不得称目标已确认 |
| 2697 netchan | 有 | 来自 2697 服务端证据，非本目标 | 实验模式，默认关闭 |
| 2697 gamestate/configstring | 有 | 目标只有解析族存在性，字段语义 UNKNOWN | 不得升级为目标格式 |
| legacy snapshot 位流 | 有 | 目标无对应证据 | 不得用于 2697 |
| `0x25/0x92` 禁用字节 | 有 | 目标区间 0 命中 | 服务器侧约束，不适用目标 |
| `ClientState` 映射 | 有服务端状态机 | 目标 `[0x76446B0]` 为不同状态空间 | 禁止混用 |

---

## 5. 只实现编码器但未被目标证据闭合的路径

1. **2697 gamestate**：`GameWorld.Build2697GameState` 会生成 `0x03 ...` 记录层消息，但 034 未定位目标客户端的实际消费者入口。
2. **2697 snapshot**：`MotionSnapshot` 与 `Send2697Netchan` 路径存在，但 2697 帧边界/delta 基准未闭合，默认不发送。
3. **legacy snapshot**：由旧抓包字节复放验证，不代表目标 3.19.26.22。
4. **会话描述符**：导出与黄金向量验证存在，但它只解决“战斗地址/密钥下发”，不等于战斗协议互通。

---

## 6. 工程可运行性结论

| 项目 | 结论 | 证据 |
|---|---|---|
| 默认协议配置 | `legacy3333` | `config/combat_server.cfg` |
| 显式协议配置 | `+set protocol_mode codol2697` | 配置解析与 `ServerHost.cs:117-121` |
| 编解码器与主循环接线 | 已接线 | `ServerHost.cs`、`ClientLogic.cs` |
| 错误路径 | 有拒绝日志与计数 | `ClientLogic.cs` DTLS/DATA/NETCHAN 分支 |
| 资源清理 | 有会话/实体归零 | FREEZE-005、本轮副本自测 |
| 测试覆盖 | 251 项自测 | FREEZE-005 `selftest.stdout.log` |
| 构建结果 | FREEZE-005 PASS；本轮脚本路径异常，直接 csc 复验成功 | 见 `TEST_AND_BUILD_RESULTS.md` |
| 编码器未接真实目标路径 | 是 | 2697 snapshot 默认禁用；目标 opcode 入口 UNKNOWN |
