# 客户端初始化证据链

## 1. 范围与方法

本轮只读检查：

- 正式代码：`CODOL-Combat-Server-v0.1`
- FREEZE-005：源码 25 文件、指纹 `5655b7b…`
- 协议与静态分析：E08–E27、协议 002、反向覆盖、14 Atlas、REF_LOBBY_KIT
- 客户端样本：按 `14_SERVER_KNOWLEDGE_ATLAS_001\00_SAMPLE_MATRIX.md` 严格分版

没有启动游戏、注入器或修改任何原始样本。

## 2. 分版本结论总表

| 阶段 | 3.9.9.7 目标 | 3.3.3.3 / C-3333 | 2.6.9.7 / C-2697-Rec |
|---|---|---|---|
| 发现/连接服务器 | 未知 | 大厅 `21/5 findSessions` 下发 session endpoint；另有 101.67.36.18:10035 冲突 | 已定位 socket/收包原语，但未定位服务发现和实际端点 |
| 首个有效包 | 无目标样本 | 真实抓包首包为 29 B NAT `0x0D` 探针 | 存在 4 B 长度前缀 + 类型码的 Demonware 帧读取；无真实抓包 |
| 连接响应 | 未证 | `INIT_ACK 0x02(38B)`、`COOKIE_ACK 0x04(114B)` | Demonware 阶段 1 应答存在发送链，但不是 gamestate/snapshot |
| init/gamestate/configstring 消费 | 未证 | 抓包 21:28 会话 `TX_GAMESTATE=0`；后续由参考实现主动补发，但没有目标客户端消费确认 | configstring body reader 字段级存在 `0xA2660`；实时归属、顶层 `0x03` 消费者、`0x06` 终止均 BLOCKED |
| 本地玩家创建/激活 | 未证 | 合成 snapshot 可使测试路径越过等待，但不得认定为可玩 | 未定位游戏世界消费者；Demonware 对象生命周期不能代替游戏玩家状态 |
| 大厅→战斗阶段 | 未证 | 大厅/booking 与 UDP 战斗明确分层 | Demonware 控制面与 iD-Tech 对局面分层；触发接线未证 |
| 继续发包条件 | 未证 | 需完成 transport-ready、challenge、connect、stats；无 gamestate 时客户端持续 heartbeat，最终 cancelConnect | Demonware 要求阶段字段和 0x81/0x83/0x84/0x85 分派；语义命名 BLOCKED |

## 3. 3.9.9.7 客户端初始化

### 3.1 结论

**没有可归属于 3.9.9.7 的客户端二进制、运行时 dump 或抓包。**  
因此以下问题均不能以目标版本事实回答：

1. 启动后如何发现官方战斗服。
2. 首个客户端战斗数据包的真实字节结构和入口 RVA。
3. connect/init 后客户端何时进入 `CS_PRIMED/CS_ACTIVE`。
4. `0x03 gamestate`、`0x04 configstring`、`0x06` 在目标客户端的实时消费者。
5. 本地玩家状态具体由哪个对象/函数创建。
6. 大厅与战斗是否复用 Demonware 会话或其地址映射。

证据：`VERSION_ISOLATION.md`；`00_SAMPLE_MATRIX.md:43-47`；文本搜索只命中四份既有任务报告的 `目标版本` 行。

### 3.2 目标版本最后已证实阶段

**不存在已证实阶段。** 这是“证据缺失”，不是“已证客户端没有初始化”。

## 4. 3.3.3.3 客户端实机初始化链

该链可以解释当前 legacy 服务器实现，但版本归属必须保持为 C-3333。

### 4.1 发现与端点

- 触发点：大厅 `21/5 findSessions` 命中后下发 258 B session 对象，其中包含 `Hostaddress ip:port` 和 16 B `securityKey`。
- 后续：`6/14 mmbook → mmstart` 进入 booking。
- 证据：`CODOL-BATTLE-SERVER-REVERSE-COVERAGE-001\02_BATTLE_ENTRY_AND_INITIALIZATION.md` 步骤 1–2。
- 冲突：600 s 抓包中没有观察到 28960；客户端曾把流量发往 `101.67.36.18:10035`。因此“地址下发是否被实际采纳”对某些流程仍是 CONFLICTED/UNKNOWN。

### 4.2 第一段网络包与握手

真实 `battle_srv.log:2320-2326` 记录：

```text
RX #1 29B  0d 02 ... 7f 00 00 01 20 71
RX #3 16B  01 02 00 00 00 00 d2 41 01 00 00 00 00 00 00 00
RX #4 219B 03 02 c3 f2 ... 100B ECDH 公钥
```

服务端响应：

- NAT：首字节 `0x0D → 0x0C`
- INIT_ACK：`0x02`，38 B cookie
- COOKIE_ACK：`0x04`，114 B，含 100 B 服务端公钥
- DATA：`0x06 0x02` 头 + 加密体

代码映射：`src/Codol/CodolProtocol.cs` 的 `TryBuildNatReply`、`TryBuildInitAck`、`TryParseKeyExchange`；`ClientLogic.cs` 的 `HandlePacket`/`HandleKeyExchange`。

### 4.3 challenge / connect / stats / heartbeat

`battle_srv.log:2328-2346` 直接记录：

- `getchallenge 0 "..."`
- 服务端 `challengeResponse 1`
- `connect ... \name\...\xuid\...\natTy...`
- 服务端 `connectResponse`
- 826 B `stats` 分块
- 连续 `heartbeat` / `heartbeatresponse`

目标链路服务器必要条件：

1. 支持 NAT/INIT/COOKIE/ECDH 握手。
2. 提供 `challengeResponse` 与 `connectResponse`。
3. 接受 826 B stats 分块。
4. 提供 heartbeatresponse。
5. 早期捕获中服务端未主动发 gamestate；客户端持续 heartbeat 后在 21:29:24 开始发送 `cancelConnect`，说明仅完成握手不保证进入战斗。

### 4.4 gamestate 与快照

参考实现后来修改为 connect 后主动发送 259 B gamestate，并启动 124/141 B motion snapshot。`battle_srv.log:3263-3309` 是这一类运行记录，但版本仍是 C-3333，且没有证明本地玩家有效激活或进入可玩地图。

状态结论：

- transport-ready：直接抓包确认。
- challenge/connect/stats：直接抓包确认。
- gamestate 由客户端确认：**未证**。
- gamestate 后 snapshot 被客户端确认：**未证**。
- 本地玩家激活：**未证**。

## 5. 2.6.9.7 / C-2697-Rec 客户端静态初始化链

该链是当前工作区中最深的客户端静态路径，但它是 C-2697 版本，不是 3.9.9.7。

### 5.1 网络底锚

`E17_RECV_ENTRYPOINT_ATTRIBUTION_001\E17_EXECUTIVE_SUMMARY.md`：

- `ws2_32!recv` IAT：`0xBAE490`
- `wsock32!recvfrom` IAT：`0xBAE50C`
- 9 个 recv/recvfrom 调用点全部被归属到 ICMP、HTTP/TLS 更新、错误日志、Demonware 传输、libcurl socket 方法或时间戳路径。
- 在已审计闭包中**没有**进入 `0xA2660`、`0xA2E50`、`0x350170`、`0x3547D0`、`0x3524F0/0x352570` 等游戏候选。

### 5.2 Demonware 会话帧与状态机

`E19_DEMONWARE_SESSION_OBJECT_DATAFLOW_001\E19_EXECUTIVE_SUMMARY.md:15-25`：

```text
0x6ABBC0  读 4 字节长度前缀的帧读取器
0x6ABE80  4 状态接收状态机，跳表 [ebx*4+0xAAC090]
0x6A9920  读取 1 字节类型码并比较 1/2
```

状态：

| 状态 | 行为 |
|---|---|
| 0 | 清帧长度/类型/载荷状态，释放旧对象 |
| 1 | 调用 `0x6ABBC0` 读取 4 字节帧头 |
| 2 | 调用 `0x6A9920` 读取类型码和载荷 |
| 3 | 进入另一读路径 `0x989230 / 0xAC4070 → 0xB83B70` |

这只证明“存在长度前缀帧读取和状态机”，没有证明该帧承载游戏 gamestate/snapshot。

### 5.3 握手阶段与消息码

`E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\E24_EXECUTIVE_SUMMARY.md`：

- 分派器：`0x6AC0C0`
- 阶段字段：`[session+0x5CC]`
- 阶段 1 且消息码 `0x81` → `0x6AB310`
- 阶段 2 的消息码：`0x83`、`0x84`
- 阶段 3 的消息码：`0x85`
- `0x6AB310` 构造协商对象 `[session+0x5F4]`，之后阶段推进到 2。
- `0x85` 由 `0x6AAE70` 校验 recv counter 和 HMAC；字符串 `"HMAC mismatch"`、`"Bad recv counter"` 直接引用该函数。

消息码方向：

- `0x85` 入站：推断较强（读取接收计数器）。
- `0x81/0x83/0x84`：控制流直接证据，方向未闭合。
- 阶段编号 1/2/3 与“挑战/应答/确认”的业务命名：BLOCKED。

### 5.4 阶段 1 应答确实到达网络发送 API

`E25_HANDSHAKE_RESPONSE_SEND_PATH_001` 证明：

```text
0x6AB310 组装应答
→ 0x6ABAFC 调 0x6AA230 克隆并入队 [session+0xB8]
→ 0x6AA7B0 会话泵
→ 0x6AA88D 调 0x783B50
→ 0x784E40
→ ws2_32!send
```

这是 C-2697-Rec 的静态发送链，不是 gamestate/snapshot 消费链，也不是 3.9.9.7。

### 5.5 与 2697 服务端生态的关系

`E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001`：

- `codol_dedrun.exe` 有 `recvfrom → _SV_ReadPackets → _SV_PacketEvent → _Netchan_Process → _SV_ExecuteClientMessage`。
- 客户端消息 opcode 为 **3 bit，0..4**。
- 客户端 Demonware 路径的分派码是 `0x81/0x83/0x84/0x85`，两者不能在同一分派器中共存。
- 服务端没有 `CLIENTCHAL`、`BDDATA`、`HMAC mismatch`、`Bad recv counter`。

`E27_DEMONWARE_SERVER_PEER_DISCOVERY_001`：

- Demonware 服务端实现存在于 `ol-mod-olfinal` C++ 和 `REF_LOBBY_KIT` Python 中，但面向 1.1.1.13/3.3.3.3。
- 2697 服务端包的 4 个 PE 中都没有 Demonware 控制面字符串。
- 2697 客户端的 Demonware 对端在本机服务端生态内不存在。

## 6. 正式服务器当前实现对应关系

冻结版 `ClientLogic.cs` 的默认 `legacy3333` 路径实现了 C-3333 抓包链：

- `HandlePacket`：字节分发
- `HandleKeyExchange`：cookie 和密钥交换
- `HandlePlain`：`getchallenge/connect/stats/heartbeat`
- `PumpGameState`、`PumpSnapshot`：主动 gamestate 与 snapshot
- `Codol2697Protocol.cs`：2697 netchan/gamestate/configstring 编码器
- `2697` 实验 snapshot 默认关闭，源码明确写明“帧边界/delta 基准仍是 BLOCKED”

这意味着冻结版同时包含 C-3333 legacy 路径和 C-2697 写入路径，但两条都不是 3.9.9.7 直接证据。

## 7. 逐问题回答

1. **3.9.9.7 最后已证实阶段？**  
   无；目标版本没有可归属客户端样本、抓包或函数证据。

2. **下一个未闭合阶段缺什么？**  
   首先缺目标版本二进制/运行时映像身份；其次缺一条目标客户端与服务器的真实抓包或目标客户端函数级接收链。

3. **当前能否把目标客户端初始化入口连接到服务器实现？**  
   不能。C-3333 是抓包证据，C-2697 是另一版本静态证据，两者都不能升格为目标事实。

4. **哪些服务器条件已可复核？**  
   只对 C-3333：NAT/INIT/COOKIE/ECDH、challenge/connect、stats、heartbeat、主动 gamestate/snapshot 发送。目标版本条件未知。

5. **客户端何时创建/激活本地玩家？**  
   3.9.9.7 未证；C-3333 未证；C-2697 未定位。