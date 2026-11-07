# SERVER-PVE-BOOKING-RESPONSE-010
# 恢复 PvE coop 的真实 mmbook booking response（服务器侧）

> 2026-10-08 执行。静态 + 服务器源码/日志分析。未启动游戏、未发送 response 到非本地目标。

---

## 1. MVP Goal

让客户端在收到正确 booking response 后，真正向 `GAME_IP:GAME_PORT`(127.0.0.1:28960) 发 UDP/DTLS。

---

## 2. Current Server Architecture

```
lobby_server.py  : TCP 127.0.0.2:3074（Lobby + booking）
battle_server.py : UDP 0.0.0.0:28960（战斗服，收包=0）
findSessions(21/5) 下发 session 对象（含 Hostaddress + SessionId）
createRoom(11/13) 回 roomId=SESSION_ID
mmbook(6/14) → 当前回空 ACK（booking 开关 off）/ 靶场信封（on）
```

---

## 3. Existing mmbook Request

实测（10-08 日志）客户端发 `6/14 mmbook`：

```
0a 01 00 00 00 00 00 00 00      senderId=1 (u64)
13 08 1d 00 00 00              blob
19 00 00 00                   u32 len 25
"mmbook 796 AQAAAAAAAAA= 0"    命令（796=playlist, AQAAAAAAAAA==8B 全 0 token）
```

---

## 4. Existing Response（当前靶场信封）

lobby_server.py 6/14 分支（FR_BOOKING_FLAG 打开时）：

```python
accepted = u32len(16) + b"mmbook accepted\x00"
pushes = [(2, cc.instant_push_body(1, "localhost", accepted))]
# envelope: 08 15 | 0A 01 | 10 "localhost" | 13 08 <len> <accepted>
```

即：service=21 push，**senderId=1**，message="mmbook accepted\0"。

```
EXISTING_RESPONSE = CONFIRMED（senderId=1 的 "mmbook accepted" 靶场信封）
```

---

## 5. 9/9 Failure Evidence

STAGE_REPORT_BATTLE.md：
- "已实测否证：用靶场信封回 PvE booking → 9/9 断连"
- `firingrange-booking-push.enabled.OFF_CONFIRMED_CRASH`（靶场 booking 推送开启即崩）
- battle_srv.log：28960 收包=0（客户端从未发起 battle UDP）

```
9/9_FAILURE = CONFIRMED（靶场信封 senderId=1 不触发 battle，且致断连）
```

---

## 6. ol-mod Source Search

搜索范围：D:\、C:\Users\Z7-CT5N1、E:\handoff2（含 `DedicatedControl*`、
`Servers.cpp`、`sharedRoomClient*`、`bookingDispatcher*`、`sv_main_mp.cpp`、
`playable_architecture.md`、`ol-mod*`、`olfinal*`）。

结果：**全部 0 命中**。E:\handoff2 不存在。

```
OL_MOD_SOURCE = NOT_FOUND（booking 应答权威源码不在本机）
```

---

## 7. DedicatedControl Analysis

无源码。仅能引用既有文档事实（STAGE_REPORT_BATTLE.md）：
`sharedRoomClient_.connect(identity, DedicatedControl::configuredClientBridgePort())`
是**服务器侧**连接专用控制端口的逻辑，不是客户端 booking response。

```
DEDICATED_CONTROL = UNKNOWN（源码缺失；既有结论：非客户端 booking socket）
```

---

## 8. Booking Handler（客户端侧，承接 003~005）

客户端 unified booking handler `0x632680`：

```asm
0x6326B9  cmp [ebp+8],  [esi+0x3a048]   ; arg1(A) == this+0x3a048
0x6326C8  cmp [ebp+0xc],[esi+0x3a04c]   ; arg2(B) == this+0x3a04c
0x6326DF  call strncmp(msg,"mmbook accepted",15)
0x6326E9  jne failure
```

其中 `this+0x3a048/0x3a04c` = 预约项 `item+0x168/+0x16C`（PARAMS-005 CONFIRMED）。

```
BOOKING_HANDLER = CONFIRMED（需 A/B 匹配 + "mmbook accepted"）
```

---

## 9. PvE Branch（★ 关键）

A/B 的语义来源——findSessions session 对象（codol_crypto.py build_session_record）：

```python
ob.blob(bd_common_addr(host_ipv4, host_port))   # ① Hostaddress = battle endpoint
ob.blob(struct.pack("<Q", session_id))          # ② SessionId  = u64 会话标识
```

服务器侧 `SESSION_ID = 0x1122334455667788`。

靶场用 `MISSION_SESSION_ID_BLOB = [1,0,0,0,0,0,0,0]`（sessionId=1）。

```
PvE sessionId = 0x1122334455667788
靶场 sessionId = 1
```

客户端把 ② SessionId（u64）写入预约项 `item+0x168(A)/+0x16C(B)`。

```
PVE_BRANCH = CONFIRMED（sessionId 决定 A/B）
```

---

## 10. Response Builder

dispatcher（service=21 handler `0x7F1400`）把 envelope 的 **senderId(u64) 拆成 A/B**
传给 `0x632680`（005 标 HIGH-CONFIDENCE）：

```asm
0x7F1567  mov edx,[ebp+0xc]   ; B = senderId 高 32
0x7F156B  mov edx,[ebp+8]     ; A = senderId 低 32
0x7F156F  call 0x632680
```

```
RESPONSE_BUILDER = CONFIRMED（envelope senderId → A/B）
```

---

## 11. Wire Format

booking accepted 应答（推测）：
```
marker=2 push, service=21
08 <u32 21> | 0A <u64 SessionId> | 10 <name> | 13 08 <len> <"mmbook accepted\0">
```

其中 **senderId 必须 = SessionId**（PvE 为 0x1122334455667788）。

```
WIRE_FORMAT = HIGH-CONFIDENCE
```

---

## 12. Response Sequence

```
mmbook request
  → 空 ACK（reply to 6/14）
  → push "mmbook accepted"（senderId=SessionId）
  → 客户端 0x632680 校验 A/B==SessionId 通过 → accepted 状态 → battle UDP
```

```
RESPONSE_SEQUENCE = HIGH-CONFIDENCE（单条 push + ACK，无需多条）
```

---

## 13. Reservation Correlation

```
服务器 SESSION_ID = 0x1122334455667788
客户端 A/B        = item+0x168/+0x16C = SessionId
response senderId = 必须 = SESSION_ID
```

```
RESERVATION_CORRELATION = CONFIRMED（senderId 必须回显 SessionId）
```

---

## 14. Battle Endpoint Correlation

battle endpoint 来自 findSessions 的 ① Hostaddress（GAME_IP=127.0.0.1, GAME_PORT=28960），
与 booking response 的 senderId（SessionId）是**两个独立字段**，客户端分别消费。

```
BATTLE_ENDPOINT_CORRELATION = CONFIRMED（endpoint 在 findSessions，非 booking response）
```

---

## 15. Current vs Expected Response（★ 根因）

| 字段 | 当前值 | 期望值 | 证据 |
|---|---|---|---|
| service | 21 | 21 | 一致 |
| senderId | **1** | **0x1122334455667788** | 靶场=1 因靶场 sessionId=1；PvE=0x1122... |
| name | "localhost" | 未定（可留） | 待验 |
| message | "mmbook accepted\0" | "mmbook accepted\0" | 一致 |

**根因：PvE 的 response senderId=1，与客户端预约项 A/B（SessionId=0x1122334455667788）不匹配，
0x632680 的 A/B 校验失败 → 走 failure 分支 → 断连/重试，不触发 battle UDP。**

```
ROOT_CAUSE = HIGH-CONFIDENCE（senderId ≠ SessionId）
```

---

## 16. Minimal Server Fix

仅改 DEV 副本 lobby_server.py 的 6/14 "mmbook" 分支：

```python
# 改前：
pushes = [(2, cc.instant_push_body(1, "localhost", accepted))]
# 改后：
pushes = [(2, cc.instant_push_body(SESSION_ID, "localhost", accepted))]
```

`SESSION_ID = 0x1122334455667788` 已在同文件定义（line 458）。

```
MINIMAL_FIX = CANDIDATE（senderId: 1 → SESSION_ID；可回滚）
```

---

## 17. Dynamic Test 1（mmbook → response）

观察 lobby_srv.log：6/14 命中后 push "mmbook accepted"（senderId=0x1122334455667788）。

```
TEST1 = NOT_TESTED
```

---

## 18. Dynamic Test 2（response → UDP 28960）★ 关键信号

观察 battle_srv.log 或抓包：客户端是否发 UDP → 127.0.0.1:28960。

```
TEST2 = NOT_TESTED（本阶段成功的第一信号）
```

---

## 19. UDP/DTLS Result

```
UDP_DTLS = NOT_TESTED
```

---

## 20. Evidence Classification

| 项 | 等级 |
|---|---|
| 靶场信封 senderId=1 致 9/9 断连 | CONFIRMED |
| session 对象含 SessionId(0x1122...) | CONFIRMED |
| 靶场 sessionId=1（MISSION_SESSION_ID_BLOB） | CONFIRMED |
| 客户端 A/B = item+0x168/+0x16C | CONFIRMED |
| handler 校验 A/B + "mmbook accepted" | CONFIRMED |
| dispatcher senderId → A/B | HIGH-CONFIDENCE |
| senderId 必须 = SessionId | HIGH-CONFIDENCE |
| 根因 = senderId 不匹配 | HIGH-CONFIDENCE |
| ol-mod 源码 | NOT_FOUND |

---

## 21. Refuted Hypotheses

```
REFUTED: "mmbook accepted" 字符串本身错误（handler strncmp 15 一致）
REFUTED: 靶场信封 senderId=1 适用于 PvE（9/9 断连）
REFUTED: booking response 需携带 battle endpoint（endpoint 在 findSessions）
REFUTED: 28960 客户端硬编码（承 005/006）
```

---

## 22. Remaining Blockers

```
1. senderId → A/B 的帧层映射未 100% CONFIRMED（HIGH-CONFIDENCE）
2. "name" 字段是否影响（"localhost" vs player_name）
3. 修复后客户端是否真正发 UDP 28960（需动态验证）
```

---

## 23. Final Conclusion

```ini
PVE_BOOKING_RESPONSE_FORMAT = HIGH-CONFIDENCE   ("mmbook accepted" + senderId=SessionId)
PVE_RESPONSE_TRIGGER        = HIGH-CONFIDENCE   (0x632680 A/B 校验通过即触发)
CLIENT_UDP_28960_SEEN       = NOT_TESTED
BATTLE_DTLS_HANDSHAKE       = NOT_TESTED
PVE_SESSION_CREATED         = NOT_TESTED
MAP_ENTRY                   = NOT_TESTED
```

**核心结论**：PvE coop booking response 与靶场信封的唯一关键差异是 **senderId**。
靶场用 senderId=1（因靶场 sessionId=1），PvE 必须用 senderId=SESSION_ID
(0x1122334455667788)。当前服务器对 PvE 也发 senderId=1，导致客户端 0x632680
的 A/B 校验失败、不触发 battle UDP。最小修复 = 把 6/14 分支的 senderId 从 1 改为
SESSION_ID，然后动态观察 UDP 28960 首包。

---

## 24. Next Step

1. 在 DEV 副本应用 §16 最小修复（可回滚），跑一轮，看 battle_srv.log 是否出现
   `RX #1`（客户端 UDP 首包）—— 这是最关键的成功信号。
2. 若 UDP 首包出现 → 转 DTLS 握手（NAT→DTLS→cookie→ECDH P-224）。
3. 若仍无 UDP → 检查 "name" 字段/或 A/B 拆半序（低/高 32），并回退。
```
