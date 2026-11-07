# 00 — CODOL-BATTLE-SERVER-PROTOCOL-002

**任务**：推进正式战斗服务器的 netchan、可靠命令、gamestate、configstring 与世界状态同步实现。
**工程主目录**：`CODOL-Combat-Server-v0.1`
**日期**：2026-10-13（Asia/Shanghai）
**本轮性质**：正式代码变更 + 可重复构建 + 自动化回归；不是研究文档替代实现。

---

## 1. 实际代码变更

| 文件 | 变更 |
|---|---|
| `src/Codol/Codol2697Protocol.cs` | 新增 2697 netchan/分片/重放窗口、XOR、客户端消息头、服务端可靠命令 0x01/0x02、configstring 位编码、gamestate 写入器 |
| `src/Engine/ClientSession.cs` | 新增 2697 netchan 序列号、分片状态、message/reliable ACK、serverId、gamestate 消息号 |
| `src/Engine/ClientLogic.cs` | legacy 与 2697 收发分流；2697 客户端消息解码；2697 gamestate 发送；snapshot 未证实时拒绝伪造 |
| `src/Engine/ServerConfig.cs` | 新增 `protocol_mode`、`server_id`、`netchan_challenge`、2697 configstring 文件及 gamestate 字段配置 |
| `src/Engine/GameWorld.cs` | 载入显式 2697 configstring 索引表；构建 2697 gamestate |
| `src/Engine/ServerHost.cs` | 输出协议模式并在 snapshot 2697 未证实缺口时显式告警 |
| `src/SelfTest.cs` + `src/SelfTest.Codol2697.cs` | 新增第 13 节，覆盖协议向量、分片、边界、XOR、gamestate 和实际发送链 |
| `config/combat_server.cfg` | 默认保持 `legacy3333`；新增 2697 模式配置说明 |
| `README.md` | 增加 2697 协议模式与已知阻塞说明 |

---

## 2. 已由本地证据支持的行为

- netchan 常量：29-bit sequence mask、`0x80000000` fragment bit、1162 B 分片、128 片、148736 B 上限。
- 服务端方向 4 B netchan 头；客户端方向 6 B（含 qport）。
- 分片描述 6 B：`{index, last, stride=1162, chunk}`；离线乱序重组、重复一致性、旧序列拒绝。
- 服务端消息：前 4 B reliableAck 明文，其余 XOR；XOR key/命令序列来自本地 CODOL 家族源码与 2697 常量链。
- 客户端消息：`serverId(u8) + messageAck(u32) + reliableAck(u32) + XOR body`。
- 可靠命令：`0x01|long|NUL-string` 与 `0x02|long|short|data`。
- gamestate：`0x03|long|map\0|mp\0|long|<configstrings>|long|long|0x06`。
- configstring：`0x04|count1(2B)|A1|A2(11-bit count/10-bit value)|A3(10/7/4/n×12)|0x06`。
- 连接状态：serverId 不匹配时不执行客户端消息；messageAck 超过已发 gamestate 时安排重发。

---

## 3. 明确证据缺口（未伪造）

- 2697 实时客户端 `0x03` gamestate 消费者未定位；服务端写入字段顺序不等于客户端已被证实可读。
- `0x04`/`0x06` 的值级识别、`.tvm0`/运行时 dump 缺口仍未闭合。
- snapshot 2697 帧边界、delta 基准、首帧 EOF/子段语义仍未闭合；`codol2697` 模式默认不发送 snapshot。
- 2697 configstring 索引业务语义未闭合；当前只接受显式 `index=value` 映射，不使用 legacy 文件冒充。
- 2697 serverId/challenge 实机来源未完全闭合；当前以显式配置 `server_id=0`、`netchan_challenge=1` 保守运行。
- 未执行真实客户端端到端验证。

---

## 4. 构建 / 测试 / 冒烟

- 构建：`BUILD OK`，25 个源文件；`source_sha256=5655b7b97350ae613c9508336983b4e318b49a435064436b12f05d38e0a9fddf`；exe `sha256=30bb3420255c5ea7213f68dc4bcd5d2b538a6fc2dc9f27c322d4492aacb320be`。
- 自测：`通过 251 项，失败 0 项。全绿。`（第 13 节 23 项 2697 协议断言）
- 运行冒烟（2697）：`protocol_mode=Codol2697`，监听 `127.0.0.1:28965`，2 秒自动停机，`sessions=0 entities=0`。
- 回归冒烟（legacy）：默认协议模式监听 `127.0.0.1:28966`，1 秒自动停机，`sessions=0 entities=0`。
- 原始输出：`BUILD_AND_TEST_LOG.txt`、`RUN_SMOKE_2697_28965.txt`、`RUN_SMOKE_LEGACY_28966.txt`。

---

## 5. 真实客户端状态

**NOT_RUN**：本轮未获得真实 CODOL 客户端连接，不得把离线自测或主循环冒烟表述为可互通。2697 模式的客户端消费链仍属于未闭合阻塞项。
