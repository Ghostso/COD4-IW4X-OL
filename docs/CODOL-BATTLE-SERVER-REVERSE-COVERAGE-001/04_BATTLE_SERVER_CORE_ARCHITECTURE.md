# 04 — 战斗服务器核心架构 / CORE ARCHITECTURE

**任务**：`CODOL-BATTLE-SERVER-REVERSE-COVERAGE-001` 第三阶段
**目标版本**：2.6.9.7
**性质**：基于现有证据描述**目标架构**与**已知协议边界**；未验证项显式保留 `UNKNOWN`。

---

## 1. 协议栈分层（CODOL 家族，已证）

```
平台/启动层（非游戏通道，NOT_REQUIRED）
  TCLS → CreateProcessW → TAS/SHELL 共享内存 → IIPS / TenProxy / TGuard / ACE
                          ↓（游戏进程内）
大厅/控制面（HTTP/自有契约，非战斗服目标）
  登录、心跳、配置下发、匹配（21/5 findSessions）、booking（6/14 mmbook/mmstart）
  → 下发 Battle 端点 + securityKey
                          ↓（UDP）
战斗/游戏通道
  ┌───────────────────────────────────────────────────────┐
  │ 握手层   NAT 0x0D / INIT 0x01 / INIT_ACK 0x02 /        │
  │          COOKIE_ECHO 0x03 / COOKIE_ACK 0x04            │
  │          （P-224 ECDH，自定义 bdDTLS 风格）             │
  ├───────────────────────────────────────────────────────┤
  │ 记录层   DATA 0x06：16B 头 {06 02, tag, counter, MAC8, │
  │          len}；AES 流 + HMAC-SHA1 截断 8B               │
  ├───────────────────────────────────────────────────────┤
  │ netchan  序列号 / 分片(1162,128) / XOR / 32位重放窗口   │
  ├───────────────────────────────────────────────────────┤
  │ 消息层   clc（3 位）/ svc（0x00..0x06）                 │
  ├───────────────────────────────────────────────────────┤
  │ 应用层   Gamestate / Configstrings / Snapshot /          │
  │          可靠命令 / 事件                                 │
  └───────────────────────────────────────────────────────┘
```

**关键分层事实（CONFIRMED）**
- 平台层（TCLS/IIPS/TenProtect）与游戏通道是**两套东西**；平台组件存在 **不等于** 游戏协议调用链闭合。
- 战斗端点由**大厅下发**（会话记录 Hostaddress），**不是客户端常量**；端口 28960 与 CoD4x `PORT_SERVER` 相同只是**数值巧合，不构成血缘**。
- CODOL 自有 netchan（头 4/6 B、分片描述 6 B、上限 1162×128、body XOR）与 CoD4x/IW4x netchan（头 10 B、上限 0x20000、无加密）**不是同一实现** → 最多 **ARCHITECTURAL_ANALOGY**。

---

## 2. 目标服务器组件边界

| 组件 | 职责 | 现有最合适底座 | 版本适用性 |
|---|---|---|---|
| **A. Transport / Record Layer** | UDP socket；记录层 framing/序列号/重放窗口；分片/重组；只输出完整字节消息 | C# `UdpTransport.cs`；OLD `netchan.c`、`codol_netchan.c` | ADAPT（2697 记录层参数需重验） |
| **B. Handshake / Session FSM** | getchallenge/connectResponse；cookie/key exchange；P-224 ECDH；连接状态回滚 | C# `CodolProtocol.cs`；OLD `codol_handshake.c`/`codol_connect.c` | ADAPT |
| **C. Message Codec** | 可靠命令 0x01/0x02；gamestate 0x03；configstring 0x04；snapshot 0x00；终止 0x06 | 2697 服务端写入事实（E1/E2/E3/E08/E09）为准 | REIMPLEMENT（以 2697 为 oracle） |
| **D. World State / Resource Adapter** | 玩家/客户端/实体最小集合；spawn/原点/基础 movement；configstring 索引；runtime-assets 最小加载 | OLD `sv_*`；ol-mod `server_mp` | ADAPT（2697 layout 需重验） |
| **E. Control Plane Bridge** | 与大厅/booking/DedicatedControl 接线；会话描述符下发 | ol-mod `DedicatedControl`/`SharedRoomClient`/`DedicatedBookingDispatcher` | REUSE（3.3.3.3 目标） |
| **F. Observability / Test Harness** | 每消息 hex/长度/字段/MAC；三方字段对照；金样；失败回滚 | C# `SelfTest.cs`；ol-mod 测试目标 | REUSE |

**MVP 状态机（建议）**
```
NEW -> CHALLENGE -> CONNECTED -> KEYED -> PRIMED -> ACTIVE -> DISCONNECTED
```

---

## 3. 消息类型（线上 opcode）与版本差异

| 流 | 旧通道（OLD/1113，三样本一致） | 2697 通道（NEW-only） | 置信 |
|---|---|---|---|
| serverCommand（可靠命令） | `0x01` | `0x02`（结构化 payload）；回退 `0x01` | CONFIRMED（2697 服务端写入） |
| gamestate | `0x02` | 起 `0x03`，终 `0x06` | CONFIRMED（写入）/ UNKNOWN（客户端消费） |
| configstring | `0x03` | 内部写 `0x04`，终 `0x06` | CONFIRMED（写入+客户端 body） |
| snapshot | `0x00` | `0x00`（多处）+ 内部 `0x06` | PARTIALLY_CONFIRMED（帧边界 BLOCKED） |
| EOF | `0x05` | `0x06` | CONFIRMED（写入）/ UNKNOWN（客户端语义） |

> **陷阱**：2697 gamestate 起始字节 `0x03` 与旧 configstring 同值，属**另一套上下文**，不可等同解释。

### 3.1 可靠命令双格式（CONFIRMED，服务端侧）
`_SV_WriteReliableCommand` **RVA 0x8612E**：
```
if (ret < 0)  Com_Error
if (ret == 0) -> 0x01 | long | NUL-terminated string   （写入点 0x861D0/0x861E2/0x861EE）
if (ret > 0)  -> 0x02 | long | short(length) | data[N] （写入点 0x8616B/0x8617D/0x86189/0x8619F）
```
边界常量：`0xCCC / 0x7FFB / 0xFF / 0x3FB / 0x3FC`；长度 1 拒绝；`O→0x01`、`Z→0x00`、大写两位 hex 合成字节（小写不接受）。

### 3.2 configstring body 位编码（CONFIRMED，服务端 + 客户端 body）
`0x04 | count1 | A1 | A2 | A3 | 0x06`，其中 `count1` = **2 字节小端（16 位）**（8 位假设已 REFUTED）。
- 索引增量编码：连续 = 1 bit；否则 0 + 13 bit；初值 -1。
- 三组字段宽度：8/16、10、7、4、12。
- 客户端消费者 **RVA 0xA2660**，与服务端 `_CODOL2697_WriteConfigstrings`（body 0xA0807..0xA0997）**逐字段一致**。
- 客户端共享位读取器 **RVA 0x1AC670**（LSB-first）；服务端 `MSG_WriteBits` 同为 LSB-first。
- **外层分帧与终止未闭合**（BLK-7 外层分派器未定位；BLK-8 `0x06` 性质）。

### 3.3 2697 服务端写入调用链（CONFIRMED）
```
可靠命令：0x710B7/0x86DE0/0x873E4
        -> _SV_WriteReliableCommand 0x8612E -> 0x02 字段
        -> _SV_SendMessageToClient 0x86B06 -> _SV_Netchan_Transmit 0x856B6
gamestate：SV_SendClientGameState -> _CODOL2697_WriteNativeGamestate(门控)
        -> _WriteGamestate 0xA21B8 -> _WriteConfigstrings 0xA0468
snapshot：_CODOL2697_WriteSnapshot 0xA4FA0 -> _WriteSnapshotReached 0xA4860
        -> 分段 writer -> 区域复制
地图挂载：_CODOL_MountTarget2697Archives 0x1400C3；_CODOL_Target2697ArchivesActive 0x140133（判 [edx+0x34]==0x16D）
```

---

## 4. 数据流

```
UDP -> Record decode -> complete plaintext
    -> opcode dispatch
    -> ReliableCommand / Gamestate / Configstring / Snapshot
    -> world / resource adapter
    -> encode response (server msg opcode)
    -> record layer -> UDP
```

**内外层必须分开**：Outer = 记录层 framing/cookie/tag/sequence；Inner = server message opcode；End marker = 可能是 message EOF 或子段/阶段结束（`0x06`），**不能混用**。

### 4.1 权威边界（架构结论）
- CODOL 客户端**没有通用 GSC compiler/VM** → authoritative GSC 必须由服务器承载（脚本层 `common.lua → gametypes/<gt>.lua → maps/<map>.lua`）。
- Demonware 类控制面**不模拟地图、不跑权威帧**；战斗服必须独立拥有：地图/FF 加载、服务端 GSC VM、实体/玩家状态仿真、usercmd 处理、snapshot/configstring/可靠命令/事件、得分与结算提交。
- **客户端是否保留休眠 server frame loop 未证**（Gate A，属于 3.3.3.3 证据，非 2697 已确认）。

---

## 5. 连接建立时间线（真实抓包，3.3.3.3）

```
客户端                                            服务端
  NAT 0x0D (29B)                     ---------->  NET_UDPPacketEvent
  NAT 0x0C 回显                       <----------
  INIT 0x01 (16B)                    ---------->  (握手层)
  INIT_ACK 0x02 (38B cookie)          <----------
  COOKIE_ECHO 0x03 (219B)             ---------->  (P-224 公钥 100B)
  COOKIE_ACK 0x04 (114B)              <----------  服务端公钥@[6:106]
  DATA 帧 0x06                        <-------->  16B 头 + cipher
    getchallenge(54B) -> challengeResponse
    connect(463B) -> connectResponse
    stats(855B, 826B 分块) -> statResponse
    heartbeat(30B, 1s) -> heartbeatresponse
    usercmd(14B)
    <--- 服务端主动 game state(263B) + 运动快照(124B)
```

**数据帧封装（逐字节确认）**：`06 02 <serverTag:2> <seq:2> <hmac8> <len:2> <cipher(len)>`
- `serverTag` 取自 `cookie[14:16]`（写错会**静默丢包**）。
- AES 流密钥 = `SHA1(ECDH共享x(28B BE) ‖ securityKey(16B)) → 24B`。
- 计数器 seed = `seq(2)|00 00|serverTag(2)`，逐块 +1。
- `hmac8 = HMAC-SHA1(key24, [0:6]‖[14:])[:8]`。

**客户端 usercmd 明文（14B，实录）**：`01 00 00 00 | 00 00 00 00 | 00 00 00 00 | 00 02`
（`head&0xE0000000==0` 走 netchan 分支；不要用全零 14B 当空命令——会触发 `REJECT_USERCMD reason=Truncated`。）

---

## 6. 会话描述符与端点下发（CONFIRMED 于 3.3.3.3）

| 字段 | 值 |
|---|---|
| 战斗端点来源 | **21/5 findSessions 的 session 对象**（258 B 记录），**不是** `mmbook accepted` |
| securityKey | 16 B（ECDH 派生的一半输入）；两侧不一致 = 传输密钥不同 = 连上后静默丢包 |
| 导出物 | `session_record_258.bin`、`mission_normal.bin`、`mission_firingrange.bin`、`battle_security_key.txt`、`endpoint.txt`、`session_descriptor.json` |
| 校验 | 启动时校验「会话端点 == 实际监听端点」，不一致直接报 ERROR |

---

## 7. 控制面协议 DedicatedControl（ol-mod，CONFIRMED，3.3.3.3）

| 项 | 值 |
|---|---|
| ProtocolVersion | 2 |
| DefaultPort | 28961（TCP） |
| DefaultClientBridgePort | 28962（TCP） |
| FrameMagic | `OLDC`（0x43444C4F）；另有 ODSE/ODRS/ODNC |
| 头长度 | Request 24 B / Response 24 B |
| MessageType | Booking=1、CaptureLoadout=2、SessionStart=3、ConfigureSession=4、QueryEndpoint=5、QueryGameplayStatus=6、SetNoclip=7、UpdateLoadout=8、RunDiagnostic=9、PlayAnnouncer=10、SendRawCommand=11、DebugGrantBattery=12、RoomConnect=16、RoomDisconnect=17、RoomSetReady=18、RoomFreeze=19、RoomCanonicalizeSession=20 |
| ResponseStatus | Accepted=0、InvalidMessage=1、UnsupportedMessage=2、Rejected=3 |
| 环境变量 | `OLMOD_PROCESS_ROLE`（combined 默认/client/dedicated）、`OLMOD_HOST_ADDRESS`（默认 127.0.0.1）、`OLMOD_DEDICATED_CONTROL_PORT` |

**监听触发链**：`ConfigureSession(28961) → configureSessionDescriptor()（sv_main_mp.cpp:1563）→ Network.start()（sv_network_mp.cpp:20）→ bind(0.0.0.0:28960)（win_net.cpp:113）→ setEnabled(true)（sv_main_mp.cpp:1166）`。

---

## 8. 已知边界汇总（截至本审计）

| 类别 | 状态 |
|---|---|
| 可宣布完成（服务端侧） | 传输层常量；可靠命令编码器；gamestate 字段顺序；configstring body 编码器；注册格式校验器；离线黄金向量自测（自洽） |
| 不得宣布完成 | 「客户端能正确解析 configstring」（BLK-1/3）；「服务端与客户端字节级兼容」（BLK-6）；「能进入战斗/世界」（BLK-5/6 + 客户端分派 BLOCKED） |
| 准入裁定 | `CONDITIONAL GO`：允许服务端侧编码器/校验器实现（`count1` 已定为 16 位）；禁止在取得抓包或客户端消费证据前宣称兼容 |
