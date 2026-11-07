# PVE-BOOKING-DYNAMIC-VALIDATION-012
# senderId=SessionId 假设的动态验证（本轮已实际执行）

> 2026-10-08 执行。受控动态验证：真实跑了一轮 PvE matchmaking，观察 Battle UDP。

---

## 0. 前置：提权代理就绪

```
UAC_APPROVED             = YES（用户已批准）
ELEVATED_AGENT_READY     = YES（pid 12244, debug_privilege=true, port 61486）
logs\elevated_agent.json = 存在（mtime 15:56:16 上一轮，本轮复用 pid 12244）
```

---

## 1. 环境与基线

```
DEV 副本 = DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT
修复状态 = senderId: 1 → SESSION_ID（lobby_server.py line 851/909，已语法校验）
battle_srv.log / lobby_srv.log = 已轮换（.bak_012_20261008_150236）
GAME_IP:GAME_PORT = 127.0.0.1:28960（battle_server.py 绑 0.0.0.0:28960/UDP，pid 19768）
```

启动前手动创建开关：`firingrange-booking-push.enabled`（使 6/14 分支推送 "mmbook accepted"）。

---

## 2. Test 1/2：SessionId 与 wire response

findSessions 本轮实际解析（lobby_srv.log）：

```
★ findSessions 解析值=[1, 0, 10, -695030357] -> 回填 playlist=10
→ findSessions → PvE coop mission session 对象(236B, map=coop_take_mp_fav_tropical,
  GameType=0x1000003 MaxPlayers=4 playlist=10)
createRoom → roomId=0x1122334455667788
```

mmbook 响应（开关 ON 后）：

```
[15:10:32] 6/14 命中 'mmbook' -> push 'mmbook accepted'(data=20)
[15:10:32] 0x85 推送 type=2 seq=1024 (98 字节 body=51)
[15:11:34] 6/14 命中 'mmbook' -> push 'mmbook accepted'(data=20)
[15:11:34] 0x85 推送 type=2 seq=1020 (98 字节 body=51)
```

wire envelope（body=51 字节，按 codol_crypto.Buf 反推）：
```
08 15 00 00 00                      service=21 (u32)
0A 88 77 66 55 44 33 22 11         senderId = 0x1122334455667788 (LE u64)
10 6c 6f 63 61 6c 68 6f 73 74 00   name="localhost"
13 08 14 00 00 00 + 16B            blob = u32len(16)+"mmbook accepted\0"
```

```
SESSION_ID              = 0x1122334455667788（findSessions 下发，本轮实际）
WIRE_SENDER_ID          = 0x1122334455667788（LE，与 SessionId 一致）
SENDERID_SESSIONID_MATCH = YES（wire 层已确认 senderId==SessionId）
```

---

## 3. Test 4：Battle UDP 首包（★ 关键结果）

battle_srv.log（整轮）：

```
[15:08:00] 收包=0 ... [15:11:00] 收包=0 ... [15:13:30] 收包=0
```

```
CLIENT_UDP_28960_SEEN = FAILED（0 收包，客户端未发 battle UDP）
```

---

## 4. 客户端行为差异（重要观察）

开关 OFF（15:08:27/15:08:30，对照）：
```
mmbook → 空 ACK → 客户端继续发 0B/4 setRoomData → 对端关闭
```

开关 ON（15:10:32 / 15:11:34，本轮）：
```
mmbook → 空 ACK + push "mmbook accepted" → 对端关闭（未发 setRoomData）
  → 新连接 → 2 条任务 → ConnectionResetError(10054)
```

即 push 使客户端**跳过了 setRoomData 直接关连接**，随后 reconnect + reset（重试模式），
但**始终未向 28960 发 UDP**。

---

## 5. 决策树判定

```
Case 1 (senderId==SessionId & accepted & RX#1) : 不成立（RX=0）
Case 2 (senderId==SessionId & accepted=NO)     : 可能
Case 3 (accepted=YES & RX=0)                    : 可能
Case 4 (WIRE_SENDER_ID != SESSION_ID)           : 不成立（wire 已确认相等）
```

结论：**senderId=SessionId 已正确写入 wire，但仍未触发 battle UDP。**
落在 Case 2 / Case 3 之间，需区分「accepted 未执行（A/B 拆半序错）」还是
「accepted 已执行但 accepted→battle UDP 是独立断点」。

```
AB_CORRELATION           = NOT_OBSERVED（无 runtime trace，未 hook）
ACCEPTED_BRANCH_EXECUTED = UNKNOWN
```

---

## 6. 最终状态

```ini
SESSION_ID               = 0x1122334455667788
WIRE_SENDER_ID           = 0x1122334455667788
SENDERID_SESSIONID_MATCH = YES
AB_CORRELATION           = NOT_OBSERVED
ACCEPTED_BRANCH_EXECUTED = UNKNOWN
CLIENT_UDP_28960_SEEN    = FAILED
BATTLE_RX_COUNT          = 0
BATTLE_DTLS_HANDSHAKE    = NOT_TESTED
PVE_SESSION_CREATED      = NOT_TESTED
MAP_ENTRY                = NOT_TESTED
```

```
NEXT_GATE = 区分 Case 2 / Case 3：
  若 A/B 拆半序(endian)错 → 修 senderId 的 low/high 映射
  若 accepted 已执行但无 UDP → 转 CLIENT-BOOKING-BATTLE-TRIGGER（accepted→battle socket）
```

---

## 7. 下一步（二选一，不叠加修改）

1. **静态确认 A/B 拆半序**：dispatcher `0x7F1400` 的 `[ebp+8]/[ebp+0xc]` 到底映射
   `envelope.senderId.low/high` 还是 `high/low`；同时确认客户端 findSessions 解析时
   `SessionId → item+0x168/+0x16C` 的拆半序。若两者不一致，据此再修 senderId 编码（仅这一变量）。
2. **静态追 accepted→battle**：若 A/B 序已对，则问题在 `0x632680 accepted branch →
   [this+0x288]/[0x849b61c] → booking-specific consumer → battle UDP socket`（009 的 UNRESOLVED）。

---

## 8. 回滚

若需回滚 senderId 修复：`lobby_server.py.bak_010_20261008_145002`。
开关 `firingrange-booking-push.enabled` 可删除以恢复「仅空应答」。
本轮未修改任何其它字段。
```
