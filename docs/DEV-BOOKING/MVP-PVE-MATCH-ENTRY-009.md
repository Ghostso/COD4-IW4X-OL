# MVP-PVE-MATCH-ENTRY-009
# 从 mmbook accepted 到进入 PvE 对局：缺哪一条链（静态定位 + 阻塞点）

> 2026-10-08 执行。纯静态（镜像 + 服务器源码/日志）。未启动游戏、未发送 response。

---

## 1. MVP Goal

```
Client → Lobby → mmbook → mmbook accepted → Battle endpoint
  → Battle connect → Battle handshake → PvE session → 进入地图
```

唯一成功标准 = 真正进入一局 PvE 对局（地图），不是"协议理解完整"。

---

## 2. Existing Confirmed Chain（承 003~007）

```
Lobby TCP 127.0.0.2:3074
  → service=6/task=14 mmbook
  → service=21/type=2 "mmbook accepted"
  → 0x7F1544 → [0x82e13fc] → vtable+0x13C → 0x632680
  → accepted branch: [this+0x288]=1, [0x849b61c]=1
A/B = reservation item +0x168/+0x16C (u64 会话标识)
```

---

## 3. mmbook Accepted

服务器侧（lobby_server.py）：

```python
# 6/14 命中 'mmbook' 时，若 firingrange-booking-push.enabled 存在：
accepted = u32len(16) + b"mmbook accepted\x00"
push = instant_push_body(1, "localhost", accepted)   # service=21, sender=1
```

**"mmbook accepted" 不含 battle endpoint**——endpoint 另有来源（§8）。

```
MMBOOK_ACCEPTED = CONFIRMED（无 endpoint，仅触发）
```

---

## 4. Accepted Notifications（0x632680 成功路径副作用）

```
vtable+0x150(0x6297A0 thunk) → +0x14C(0x629730 序列化入队 [this+0x3a0b0])
vtable+0x148(0x62C580) / +0x5C(0x62FDE0) / +0x24(0x62DE90 广播)
[this+0x288]=1（对象态）  [0x849b61c]=1（全局态）
复位 A/B（0x62f6c0）
```

已证：入队 [this+0x3a0b0] 的 worker 0x6334xx → 0x818de0 = **chat.private 私聊**（非 battle）。
故 accepted 的 battle 触发不在这条 queue。

```
ACCEPTED_NOTIFICATIONS = CONFIRMED（但 battle 触发未在这些通知里闭合）
```

---

## 5. Booking-specific Consumer

```
[0x849b61c] 2 个 reader（游戏流程）：0x7CB1E2→0x620590、0x7CFA87→0x7cb210
[this+0x288] 读者：未逐条归属
vtable+0x24 广播 receiver：未枚举
```

booking→battle 的**专属消费者仍未定位**（静态链在此断裂）。

```
BOOKING_SPECIFIC_CONSUMER = UNRESOLVED
```

---

## 6. 0xB82025 Caller Inventory（transport connect 调用者枚举）

transport manager connect 方法 = 0xB81EF0（内含 0xB82025→0xBA4080）。
完整上行调用链（唯一）：

```
0x7f2600(DNS 状态机, "DW_DNS_*")
  → 0x7f3600 → 0x7f3890(connect to server)
  → 0xb82070 → 0xb81ef0(connect) → 0xBA4080 → ... → socket/connect
  endpoint 读全局 [0x84abb08]/[0x84abb14]/[0x84abb0c]
```

分类：这是 **Lobby/主连接（DNS 解析→connect）**，不是 battle。

```
TRANSPORT_CONNECT_CALLER = CONFIRMED（= Lobby 主连接，唯一链）
BATTLE 专用 connect         = 未发现（无第二个 0xB81EF0 调用者）
```

---

## 7. Endpoint Storage

- transport manager 连接对象 sockaddr @ [this+0x538]（0xBA4080 rep movsd 写入）→ **Lobby endpoint**。
- battle endpoint：服务器侧在 findSessions session 对象里（§8），客户端存储字段未定位。

```
ENDPOINT_STORAGE = PARTIAL（lobby 侧 CONFIRMED；battle 侧客户端字段未定位）
```

---

## 8. Endpoint Source（★ 关键）

服务器 lobby_server.py：

```python
GAME_IP = "127.0.0.1"   # 21/5 findSessions 会话对象里的"权威服务器地址"
GAME_PORT = 28960
session_objects() → build_session_record(SESSION_ID, GAME_IP, GAME_PORT, ...)
```

**battle endpoint（127.0.0.1:28960）由 findSessions(21/5) 的 session 对象下发**，
不是由 "mmbook accepted" 下发。

```
ENDPOINT_SOURCE = CONFIRMED（findSessions 21/5 session 对象 → 127.0.0.1:28960）
```

---

## 9. Client Reservation Correlation

```
Client reservation A/B = item+0x168/+0x16C → this+0x3a048/+0x3a04c
Server SESSION_ID      = 0x1122334455667788（roomId 同源派生）
```

客户端 A/B 与服务器 SESSION_ID 的**字段级对齐未闭合**（是否同一 u64 未证实）。

```
CLIENT_SERVER_RESERVATION_CORRELATION = PARTIAL
```

---

## 10. Server Reservation Correlation

服务器固定 SESSION_ID=0x1122334455667788、GAME_PORT=28960、GAME_IP=127.0.0.1。
战斗服（battle_server.py）绑定 UDP 0.0.0.0:28960，实测**收包=0**（客户端从未连入）。

```
SERVER_RESERVATION = CONFIRMED（但 battle 0 收包 → 客户端未连接）
```

---

## 11. Battle Endpoint

```
IP   = 127.0.0.1（服务器 GAME_IP）
port = 28960（服务器 GAME_PORT，动态候选 8300~8316 为 CANDIDATE）
transport = UDP（战斗服 UDP + NAT→DTLS→cookie→ECDH P-224 握手）
```

**重要：battle 是 UDP/DTLS，不是 TCP。** 任务里的 "Battle TCP connect" 与此证据不符，
battle transport 需独立确认（本阶段不把 Lobby 0x85 framing 当 battle framing）。

```
BATTLE_ENDPOINT = CONFIRMED（127.0.0.1:28960, UDP）
```

---

## 12. Transport Manager

0x803830 = transport manager 单例 getter；连接对象 [this+0x4f4]；connect=0xB81EF0。
已证它是 **Lobby 主连接**（DNS→connect）。battle 是否复用同一 transport manager
的第二个连接对象：**未证实**。

```
TRANSPORT_MANAGER = CONFIRMED（lobby 连接）；battle 复用 = UNKNOWN
```

---

## 13. Socket Wrapper

connect 链：0xBA4080→0xba0760→0xba0750→0xba05a0（literal WinSock 在 0xba05a0 内，
import 名已剥离）。这是 **Lobby TCP** socket。battle UDP socket 创建点未定位。

```
SOCKET_WRAPPER = PARTIAL（lobby TCP connect 链 CONFIRMED；battle UDP socket UNKNOWN）
```

---

## 14. Battle Connect

```
（静态未闭合）
mmbook accepted → [0x849b61c]=1 / [this+0x288]=1
  → ??? → 读 findSessions 存下的 endpoint(127.0.0.1:28960)
  → ??? → 创建 battle UDP socket + 握手
```

```
BATTLE_CONNECT = UNRESOLVED（客户端"消费 endpoint + 建 battle socket"代码未定位）
```

---

## 15. Battle Handshake

服务器侧已知（STAGE_REPORT_BATTLE.md）：`NAT 29B → DTLS 16B → 38B cookie → 219B → ECDH P-224 → 114B ack`（UDP）。
客户端对应 parser 未定位。

```
BATTLE_HANDSHAKE = UNKNOWN（客户端 parser 未定位；服务器侧顺序已知）
```

---

## 16. PvE Session

未进入（battle 0 收包）。PvE coop（playlist=10）与靶场（playlist=1）协议不同，
"mmbook accepted" 靶场信封实测 9/9 断连（STAGE_REPORT_BATTLE.md）。

```
PVE_SESSION = NOT_TESTED（被 battle connect 阻塞）
```

---

## 17. Dynamic Validation（下一步，本阶段未执行）

达到 HIGH-CONFIDENCE 后最小验证：
```
Test1 mmbook→accepted→观察 battle SYN/UDP 首发
Test2 battle 连接建立
Test3 battle 握手
Test4 PvE session
Test5 进入地图
```

```
DYNAMIC_VALIDATION = NOT_TESTED（本阶段 STATIC ONLY）
```

---

## 18. Evidence Classification

| 项 | 等级 |
|---|---|
| mmbook accepted（无 endpoint） | CONFIRMED |
| battle endpoint 由 findSessions 下发 | CONFIRMED |
| battle = UDP 28960（DTLS 握手） | CONFIRMED（服务器侧）|
| transport manager connect = Lobby 主连接 | CONFIRMED |
| 0xB81EF0 唯一调用链（DNS→connect） | CONFIRMED |
| booking→battle 专属消费者 | UNRESOLVED |
| 客户端 battle UDP socket 创建 | UNRESOLVED |
| 客户端 A/B ↔ 服务器 SESSION_ID | PARTIAL |
| 0x818de0=chat.private / 0x803830=单例 | CONFIRMED（承 007）|

---

## 19. Refuted Paths

```
REFUTED: 28960 客户端硬编码（承 005/006）
REFUTED: 0x818de0 = booking→battle worker（= chat.private）
REFUTED: 0x803830 = socket/connect（= transport manager 单例）
REFUTED: transport manager connect = battle connect（= Lobby 主连接）
REFUTED: "mmbook accepted" 含 battle endpoint（endpoint 在 findSessions）
REFUTED: battle = TCP（证据为 UDP/DTLS）
```

---

## 20. Remaining Blockers

```
1. PvE coop "mmbook accepted" 应答格式（靶场信封 9/9 断连，未找到正确格式）
2. 客户端 booking→battle 专属消费者（读 endpoint + 建 battle socket 的代码）
3. battle UDP socket 创建与握手 parser（客户端侧）
4. 客户端 A/B 与服务器 SESSION_ID 的对齐方式
```

---

## 21. Minimal Fix Candidates（不直接改，仅记录）

### SERVER_MINIMAL_FIX_CANDIDATE-1：PvE coop booking 应答
```
current : 6/14 mmbook → 空 ACK（booking 开关 off）；靶场信封 9/9 断连
expected: 6/14 mmbook → 正确 PvE coop accepted 应答（触发客户端连 battle）
change  : 在 lobby_server 的 6/14 分支按 PvE 格式回 accepted（需先拿到真实格式样本）
evidence: STAGE_REPORT_BATTLE.md 的靶场信封否证 + 本阶段 battle 0 收包
```

### SERVER_MINIMAL_FIX_CANDIDATE-2：battle listener 就绪确认
```
current : battle_server.py 已监听 UDP 0.0.0.0:28960，收包=0
expected: 客户端 accepted 后连入，出现 NAT/DTLS 首包
change  : 无（已监听），确认客户端端触发即可
evidence: battle_srv.log 收包=0
```

---

## 22. Final Conclusion

```ini
BOOKING_TO_BATTLE_ENDPOINT = CONFIRMED     （endpoint 由 findSessions 下发 127.0.0.1:28960）
BOOKING_TO_BATTLE_CONNECT  = UNRESOLVED    （客户端"消费 endpoint+建 battle socket"未闭合）
BATTLE_TCP_ESTABLISHED     = NOT_TESTED
BATTLE_HANDSHAKE           = NOT_TESTED    （服务器侧 UDP/DTLS 顺序已知，客户端 parser 未定位）
PVE_SESSION_CREATED        = NOT_TESTED
MAP_ENTRY                  = NOT_TESTED
```

**核心结论**：静态链在「mmbook accepted → 客户端建 battle 连接」处断裂。
已确认的关键事实：
1. battle endpoint 已正确下发（findSessions 21/5 → 127.0.0.1:28960）；
2. battle 是 UDP/DTLS（非 TCP）；
3. transport manager 的 connect 是 Lobby 主连接（非 battle）；
4. 最大阻塞 = PvE coop 的 "mmbook accepted" 应答格式未知（靶场信封已否证）。

下一步唯一最短路径：拿到 **PvE coop 真实 booking 应答样本**（官方 pcap / ol-mod 源码），
否则客户端不会触发 battle 连接。在此之前继续静态追「客户端 booking→battle 专属消费者」，
但不能替代真实应答样本。
```
