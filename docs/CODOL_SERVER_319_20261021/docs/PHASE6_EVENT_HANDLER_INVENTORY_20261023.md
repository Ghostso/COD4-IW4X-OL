# Phase 6 进度：事件 Handler 清单（2026-10-23）

状态：`ACTIVE`（事件字符串/xref 已闭合，scoreboard 协议未闭合）

## 3.19 直接 xref

| Event | String | Handler function candidates |
|---|---|---|
| `EXE_MATCHENDED` | `0x00DBB314` | `0x004F2350` @ `0x004F23EF`, `0x005BF940` @ `0x005BF9EB`, `0x005BFB10` @ `0x005BFB4E`, `0x005C0FD0` @ `0x005C0FEC`, `0x0077DBC0` @ `0x0077E391` |
| `EXE_PLAYERKICKED` | `0x00DBB334` | `0x004F2350` @ `0x004F2427`, `0x005C0FD0` @ `0x005C10C8` |
| `EXE_PLAYERKICKED_SPY_KARMA` | `0x00DBB458` | `0x004F2350` @ `0x004F2577`, `0x005C0FD0` @ `0x005C10F2` |
| `EXE_PLAYERKICKED_AS_WISH` | `0x00DBB4D0` | `0x004F2350` @ `0x004F25E7`, `0x005C0FD0` @ `0x005C104A` |
| `EXE_SERVERCOMMANDOVERFLOW` | `0x00DBB584` | `0x004F2350` @ `0x004F26C7` |
| `EXE_LOSTRELIABLECOMMANDS` | `0x00DBB5E8` | `0x004F2350` @ `0x004F2737`, `0x00776A60` @ `0x00776B14` |
| `EXE_AWAITINGGAMESTATE` | `0x00DC5F1C` | `0x0060C0A0` @ `0x0060C14C` |
| `EXE_CONFIGSTRINGMISMATCH` | `0x00DB46E4` | `0x00473180` @ `0x004731E1`, `0x004F2350` @ `0x004F2833` |

## 已定位的主要函数

- `0x4F2350`：事件文本比较/分发族
- `0x5BF940`：MATCHENDED 相关事件处理
- `0x5BFB10`：MATCHENDED 第二处理点
- `0x5C0FD0`：连接/服务端命令分派
- `0x776A60`：LOSTRELIABLECOMMANDS 处理
- `0x60C0A0`：AWAITINGGAMESTATE 处理
- `0x473180`：CONFIGSTRINGMISMATCH 处理

## 产物

- `fixtures/inmatch_event_handlers_20261023.json`

## 未闭合

- scoreboard 消息 opcode 与字段布局
- kill/death/score/team 事件包结构
- round/objective/match state 的完整处理器
- event 与可靠命令/网络 opcode 的绑定

