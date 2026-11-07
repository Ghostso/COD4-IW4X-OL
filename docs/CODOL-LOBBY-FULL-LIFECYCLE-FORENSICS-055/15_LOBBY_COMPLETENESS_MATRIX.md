# 15 — 大厅完整性矩阵（说明）

> 数据源：`LOBBY_COMPLETENESS_MATRIX.csv`（18 行）。本文件解释判据。

---

## 1. 六种状态的定义

| 状态 | 判据 |
|---|---|
| `VERIFIED_COMPLETE` | 有官方客户端实机证据，且**客户端消费成功**（有可观测的下一步） |
| `PARTIALLY_IMPLEMENTED` | 服务端有实现，客户端也走到过，但有明确缺口 |
| `IMPLEMENTED_UNVERIFIED` | 服务端有实现，**客户端是否消费未证** |
| `NOT_IMPLEMENTED` | 协议层根本没有 |
| `BLOCKED` | 有实现且发出，但流程停在这里 |
| `UNKNOWN` | 证据不足 |

**严禁**仅凭"服务端有处理函数"标 `VERIFIED_COMPLETE`。

---

## 2. 18 行的判定依据

| 阶段 | 状态 | 为什么 |
|---|---|---|
| bootstrap_handshake | `VERIFIED_COMPLETE` | 56/56 run 完成 0x81→0x82→0x83，且 KDF 试解命中后客户端继续 |
| bootstrap_35_requests | `PARTIALLY_IMPLEMENTED` | 35 个都出现，但 12 个是空 ACK 未知语义 |
| player_profile | `VERIFIED_COMPLETE` | 8/1/8/2 返回后客户端继续发起 10/21 |
| publisher_config | `VERIFIED_COMPLETE` | 同上 |
| channel_subscribe | `VERIFIED_COMPLETE` | 102/1 后客户端继续 |
| find_sessions | `VERIFIED_COMPLETE` | 21/5 后客户端继续发 mmbook 或 11/13 |
| create_room | `VERIFIED_COMPLETE` | 11/13 后客户端发 11/4 |
| room_initialization | `PARTIALLY_IMPLEMENTED` | `dwRoomMatchUber` 出现，但状态机停状态 1 |
| room_member_sync | `NOT_IMPLEMENTED` | 无成员列表协议 |
| room_ui_update | `BLOCKED` | 推送发出，未证被解析 |
| room_ready | `BLOCKED` | 按钮零上行 |
| event_push_20 | `NOT_IMPLEMENTED` | 零推送 |
| mmbook | `VERIFIED_COMPLETE` | accepted → mmstart 是唯一被证明的"下行→下一请求" |
| mmstart_send | `VERIFIED_COMPLETE` | 客户端发出、服务端解析 |
| mmstart_to_battle_connect | `BLOCKED` | PvE 曾成功（8 轮），房间 0/32 |
| battle_handoff_address | `VERIFIED_COMPLETE` | 67 B 地址块在 21/5 应答里 |
| battle_udp_connect | `BLOCKED` | 零 RX、0 包 |
| exit_to_lobby | `UNKNOWN` | 无对局结束后的返回日志 |

---

## 3. 统计

| 状态 | 行数 |
|---|---|
| `VERIFIED_COMPLETE` | 8 |
| `PARTIALLY_IMPLEMENTED` | 2 |
| `BLOCKED` | 4 |
| `NOT_IMPLEMENTED` | 2 |
| `UNKNOWN` | 1 |
| `IMPLEMENTED_UNVERIFIED` | 0（没有"实现了但没验"的项——都至少走到了 BLOCKED） |

**8/18 完成 = 44%。骨架完成，肌肉与最后一米未完成。**

---

## 4. 一个容易误判的点

`battle_handoff_address` 标 `VERIFIED_COMPLETE`（地址确实给了），
而 `battle_udp_connect` 标 `BLOCKED`（客户端不连）。

**这两行必须分开看**：地址给了 ≠ 客户端用了。
把两行合并成一行"战斗交接"会掩盖真正的问题所在。
