# 06 - 下一里程碑

> 本任务在 M0-M2 后停止，不进入客户端连接、Gamestate 发布或游戏状态模拟。

## 当前完成度

- M0: 基线、源码哈希、编译器、测试入口已记录。
- M1: reliable、gamestate、configstring、snapshot 已建立规格 JSON。
- M2: 已确认字段 codec 与 26 项离线黄金测试通过。

## 建议下一里程碑 M3（离线状态机集成）

目标: 把 codec 与现有 CodolProtocol、ClientCommandReader、MotionSnapshot 串成无 socket 的会话状态机。

前置条件:
1. 接受当前 02_PROTOCOL_SPEC.json 作为唯一协议真值。
2. 对 0x02/0x06 的未决语义继续保持 BLOCKED。
3. 继续使用独立工作副本，不修改原工程。

建议实现:
- SessionStateMachine 仅处理内存事件。
- 使用已确认 reliable 0x01/0x02 状态转移。
- 对 gamestate/configstring/snapshot 使用显式未决占位，不伪造客户端消费。
- 增加 --session-selftest，只运行离线事件序列。

验收:
- 无网络 socket。
- 事件序列可重放。
- 状态转移、可靠序列号、超时和回滚可断言。
- 未决协议项保持显式 BLOCKED。
- 原有 111 项基线失败情况不变。

停止条件:
- 没有客户端 0x02 分派/0x06 语义证据时，不得进入 M4。
- 没有明确批准时，不得启动客户端、服务端或网络会话。
- 不得把 codec 单元测试通过写成客户端兼容。
