# Phase 6 收口：Event / Scoreboard / Match State（2026-10-23）

状态：`DONE`（3.19 客户端直接证据）

## 1. 事件命令目录

已从 3.19 客户端函数 `0x4F2350` 提取 46 个事件命令：

`fixtures/inmatch_event_commands_20261023.json`

覆盖 MATCHENDED、PLAYERKICKED、SERVERCOMMANDOVERFLOW、
LOSTRELIABLECOMMANDS、CONFIGSTRINGMISMATCH、SERVERISFULL 等。

## 2. 事件 Handler

直接 xref 已定位：

- `0x4F2350`：事件文本比较/分类
- `0x5BF940` / `0x5BFB10`：MATCHENDED 处理
- `0x5C0FD0`：连接/服务端命令分派
- `0x776A60`：可靠命令异常处理
- `0x60C0A0`：AWAITINGGAMESTATE
- `0x473180`：CONFIGSTRINGMISMATCH

清单：

`fixtures/inmatch_event_handlers_20261023.json`

## 3. Scoreboard 结论

3.19 没有单独的 scoreboard netField 表。

scoreboard 相关字符串：

- `scoreboard_death` `0x00DAF908`
- `scoreboard_score` `0x00DAF924`
- `scoreboard_bot` `0x00DAF940`
- `scoreboard_rtt` `0x00DB02FD / 0x00DB3D37`
- `scoreboard_rtt_enabled` `0x00DB1608`
- `scoreboard` `0x00DBF4B0 / 0x00DC5DB6`

直接控制点：

- `0x44AF99` 注册 scoreboard/rtt cvar
- `0x808C40` scoreboard 可见性/状态判断
- `0x60D540` 字符串/命令查询

结论：scoreboard 是客户端渲染视图，数据来源是已复制的 player/client state，
不是额外的一张网络字段表。

## 4. Kill / Death / Score

已确认的 UI/消息键包括：

- `killcounter_vmgun`
- `killcam`
- `killiconmelee`
- `killiconsuicide`
- `killiconfalling`
- `killiconcrush`
- `killicondied`
- `scoreboard_death`
- `scoreboard_score`

这些属于 UI 事件/资源键；其数值状态由 player/client state 驱动，
不构成独立的 netField 表。

## 5. 产物

- `fixtures/inmatch_event_commands_20261023.json`
- `fixtures/inmatch_event_handlers_20261023.json`
- `docs/PHASE6_EVENT_COMMANDS_20261023.md`
- `docs/PHASE6_EVENT_HANDLER_INVENTORY_20261023.md`

## 6. 结论

Phase 6 在协议层完成：

- 事件命令目录完成
- 事件 handler 直接 xref 完成
- scoreboard 确认无独立网络字段表
- kill/death/score 是 UI/state 渲染项
- match state 通过事件与服务端命令传播
