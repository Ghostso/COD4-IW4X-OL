====================================================================================================
[10-08 13:17] BOOKING-ACCEPTED-WORKER-006.md  | BOOKING-ACCEPTED-WORKER-006
# accepted 状态消费者 + matchmaking endpoint + 战斗连接 worker（静态）

> 2026-10-08 执行。纯静态。镜像 `image_best.bin`（base 0x400000）。
> 未修改 Golden/Server/PE/patch/KDF hook，未启动游戏，未发送 response。


## 1. Scope

只追一条链：

```
accepted state → state consumer → matchmaking/server endpoint → connect worker
```

回答：谁消费 accepted 状态、endpoint 存哪、谁最终 connect。
====================================================================================================
[10-07 19:22] BOOKING-CLIENT-CONTRACT-001.md  | BOOKING-CLIENT-CONTRACT-001
> 原 CODOL 客户端**究竟期待什么** Booking 响应？
> 本文只陈述**有客户端侧证据**的结论。无证据一律 `UNKNOWN`。
>
> 分析源：`COD OL\codoMP_client_shipRetail.exe`（7,841,344 B，无壳区）
> 方法：字符串表 + 格式串交叉比对 + 实测帧对照
> 纪律：**未修改 Golden**；静态分析产物置于 `DEV-BOOKING\`

```
GOLDEN-LOBBY-001 = COMPLETE（只读，本次未触碰）
BOOKING_SOURCE   = UNAVAILABLE
分析类型          = 纯静态（第一阶段），未改 Server
```


## 0. 一句话结论（先说结论）

**客户端的 `6/14` 是"客户端→服务端"的**预约命令**，
而客户端**自己就带**了期望的响应字符串**：`mmbook accepted`。**

### 证据等级：CONFIRMED

```
0x6B29B0  "mmbook accepted"     ← 客户端 exe 内
====================================================================================================
[10-08 14:17] BOOKING-CONNECT-PATH-007.md  | BOOKING-CONNECT-PATH-007（完整版）
# 0x818de0 状态机 + 0x803830 传输对象 + endpoint + connect（静态）

> 2026-10-08 执行。纯静态。镜像 `image_best.bin`（base 0x400000）。
> 未修改 Golden/Server/PE/patch/KDF hook，未启动游戏，未发送 response。


## 1. Scope

闭合 `0x818de0 → 0x803830 → endpoint → socket → connect`，并核实 006 的链归属。
====================================================================================================
[10-08 12:14] BOOKING-RESPONSE-CHANNEL-003.md  | BOOKING-RESPONSE-CHANNEL-003
# 非侵入定位 6/14 mmbook 的真实响应通道

> 2026-10-08 执行。纯只读：分析既有服务器日志、NDIS ETL 抓包、静态镜像 `image_best.bin`。
> **未修改** Golden / Server / 4 个 patch / KDF hook / EXE / ACE。
> **未发送**任何 Booking response。**未启动**游戏进程（复用 10-08 已跑出的日志与抓包）。


## 0. Executive Summary

**一句话结论：6/14 mmbook 的响应通道就是大厅 TCP 连接本身（共享连接），不存在独立的 booking socket。**

```
BOOKING_RESPONSE_CHANNEL   = SHARED_CONNECTION_CONFIRMED   （对应成功标准 C）
BOOKING_RESPONSE_HANDLER   = UNKNOWN 的只是"谁做 vtable+0x140 的间接调用"，
                             静态 handler 本体已确认 = 0x632680
6/14 TRANSPORT             = TCP（loopback 127.0.0.1 -> 127.0.0.2:3074）
6/14 RESPONSE SHAPE        = 0x85 应答(空 ACK) + 可选 type=2 push "mmbook accepted"
```

关键事实链（证据见后文各节）：

1. 客户端把 6/14 当作大厅协议里的**普通业务帧**（service=6 task=14）发出，
   与 71/4、28/1、21/5、11/13、11/4 等共用**同一条 TCP 连接**。
2. 服务端对 6/14 的应答走**同一条连接**回给客户端：booking 开关未开时是
====================================================================================================
[10-08 12:34] BOOKING-RESPONSE-DISPATCH-004.md  | BOOKING-RESPONSE-DISPATCH-004
# 静态闭合 service=21 -> type=2 -> mmbook -> vtable -> 0x632680 分派链

> 2026-10-08 执行。纯静态逆向，镜像源 `image_best.bin`（base 0x400000，10,899,456 B）。
> 未修改 Golden/Server/PE/patch/KDF hook，未启动游戏，未发送任何 response。


## 1. Scope

只做静态：定位客户端从「大厅 TCP 收到 service=21 即时消息」到「调用 booking handler」
的完整分派链，并核对上一阶段给出的 vtable 槽位与 handler 归属是否准确。

```
目标链： Lobby TCP → decrypt/frame parser → service=21 → type=2 immediate-message
        → message dispatch → booking object → vtable → 0x632680
```
====================================================================================================
[10-08 12:44] BOOKING-RESPONSE-PARAMS-005.md  | BOOKING-RESPONSE-PARAMS-005
# A/B 参数来源 + accepted 分支到 28960 的路径（静态）

> 2026-10-08 执行。纯静态。镜像 `image_best.bin`（base 0x400000）。
> 未修改 Golden/Server/PE/patch/KDF hook，未启动游戏，未发送 response。


## 1. Scope

只研究两个问题：
```
A. call 0x632680(this, A, B, ptr, msg, 15) 中 A/B 的精确来源与语义
B. 0x632680 accepted branch 最终如何进入 28960 battle-server 路径
```
====================================================================================================
[10-07 19:27] BOOKING_PROTOCOL_SPEC-001.md  | BOOKING_PROTOCOL_SPEC-001（静态规格，第二阶段）
> 本文**只写有反汇编证据的结论**。无证据一律 `UNKNOWN`。
> **未修改 Server / Golden / patch / KDF hook**。

```
分析源   image_best.bin（运行期镜像 VA 0x400000..0xE65000，10,899,456 B，已解壳）
方法     反汇编 + 数据引用图 + vtable 归属回溯
纪律     不发送任何猜测性 Booking response
```


## 0. P0 结论：accepted handler 不是被 call 的，而是挂在 vtable 上

### 0.1 穷举结果（CONFIRMED）

```
0x632680 的直接 call rel32        = 无
0x632680 的 dword 引用（vtable 槽）= 2 处：0x00DC73B0 / 0x00DC7850
```

### 0.2 精确虚调用点（CONFIRMED）

用"寄存器同源"约束（`mov reg,[obj+disp]` 紧跟 `call 同寄存器`）全镜像扫描：
====================================================================================================
[10-07 19:39] BOOKING_PROTOCOL_SPEC-002.md  | BOOKING_PROTOCOL_SPEC-002
> 第三阶段静态恢复规格（P0-P7 收束版）
> 分析源：`CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin`
> 运行期镜像 VA：`0x00400000..0x00E65000`，10,899,456 B，已解壳
> 状态：纯静态，未修改 Golden / Server / 4 个 Lobby patch / KDF hook
> 未发送任何 Booking response


## 0. 本阶段结论摘要

| 环节 | 等级 | 结论 |
|---|---|---|
| `+0x278` 守卫 | STRONG_CANDIDATE | 1 字节 `BOOKING_PENDING/ACTIVE` |
| reservation 数组基址 | CONFIRMED | `this+0x75D8`，stride `0x238` |
| reservation 索引 | CONFIRMED | `[ebp+0xC]` 写入 `[this+0xE360]` |
| reservation 填充者 | CONFIRMED | `vtable+0x40` = `0x62F840` |
| A/B 真实写入 | CONFIRMED | `0x62F6F0` 从 `[edi+0x168]` / `[edi+0x16C]` 写入 |
| A/B 在 mmbook 请求中读取 | CONFIRMED | `0x62F7F9` / `0x62F809` |
| accepted parser | CONFIRMED | `0x632680`，`ret 0x14` |
| accepted 成功副作用 | CONFIRMED | `0x632745` 写 `[esp+0x28]=1` |
| accepted handler 调用者 | UNKNOWN | EXE 内未找到 5 参数虚调用点 |
| timeout handler | CONFIRMED | vtable `+0x13C` = `0
====================================================================================================
[10-07 19:43] BOOKING_PROTOCOL_SPEC-003.md  | BOOKING_PROTOCOL_SPEC-003
> 第四阶段：收束两个剩余静态边界
> 分析源：`image_best.bin`（VA 0x400000..0xE65000，已解壳）
> 纯静态。未修改 Golden / Server / patch / KDF hook。
> 未启动游戏，未发送 Booking response。


## 0. 本阶段结论

| 项目 | 等级 | 结论 |
|---|---|---|
| A_SOURCE | CONFIRMED | `item+0x168` |
| B_SOURCE | CONFIRMED | `item+0x16C` |
| A/B real writer | CONFIRMED | `0x62F6F0` |
| reservation index slot | CONFIRMED | `[this+0xE360]` |
| reservation index source | **CONFIRMED（本地匹配结果下标）** | `0x637720` 选择后写入 |
| reservation array fill | CONFIRMED | `0x6379E0` 从 `this+0x340` 拷贝到 `this+0x7470` |
| reservation array clear | CONFIRMED | `0x62CD30` |
| `0x62F840` ARG1 | CONFIRMED | 模式/标志字节，`[ebp+8]` |
| `0x62F840` ARG2 | CONFIRMED | reservation index，`[ebp+0xC]` |
| `0x62F840` ARG3 | CONFIRMED | 字节，`[ebp+0x10]` |
| accepted handler | CONFIRMED | `0x632680` |
| accepted handler caller | UNKNOWN | 未定位 |
| response channel | UNKNOWN | 不能由 `0x803830` 状态推出 |
====================================================================================================
[10-07 19:46] BOOKING_PROTOCOL_SPEC-004.md  | BOOKING_PROTOCOL_SPEC-004
> 第五阶段：`0xB82034` callback 槽最后边界
> 纯静态。未修改 Golden / Server / 4 个 patch / KDF hook。
> 未启动游戏，未发送 Booking response。
>
> 分析源：`image_best.bin`（VA 0x400000..0xE65000，10,899,456 B，已解壳）


## 0. 一句话结论

`0xB82034` 读取的 `[obj+0x1610]` **不是被直接间接调用**。
它被传给 `0xBA0DE0`，存进内部连接对象的 `+0xAE4`；
该字段仅在两处被读取，且两处都只是对回调对象做 vtable[0] 调用（清理/析构），
随后进入连接创建 / 状态机路径，**不进入**：

```
0x633FE0 → 0x634240 → 0x634080 → 0x632680
```

因此：

```
RESPONSE_CHANNEL = NOT_ESTABLISHED
NO_BOOKING_RESPONSE_LINK_ESTABLISHED
====================================================================================================
[10-07 20:10] BOOKING_RUNTIME_NETWORK-002.md  | BOOKING_RUNTIME_NETWORK-002
> 运行期观测阶段 002：非侵入式网络层观测
> 目标：6/14 之后客户端是否收到网络响应，来自哪条连接
>
> 结论：
>
> ```
> NETWORK_OBSERVATION_CHANNEL = AVAILABLE (NDIS, payload-capable)
> 6/14 REQUEST                 = NOT_SENT
> BOOKING_RESPONSE_NETWORK     = NOT_OBSERVED
> RESPONSE_CHANNEL             = NOT_ESTABLISHED
> BLOCKING_ERROR               = EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE
> ```
>
> 客户端在**发出 6/14 之前**就弹“致命错误”并终止，
> 因此本轮不存在可观测的 Booking 请求，更无响应可谈。


## 0. 纪律核对

```
Server 修改              = 无
Golden 修改              = 无
4 个 Lobby patch 修改    = 无
====================================================================================================
[10-07 19:50] BOOKING_RUNTIME_TRACE-001.md  | BOOKING_RUNTIME_TRACE-001
> 运行期观测阶段 001
> 目标：真实执行到 6/14 时捕获 `0x632680` 入口及调用栈
>
> 结论先行：
>
> ```
> INSTRUMENTATION_BLOCKED
> BOOKING_HANDLER_RUNTIME = NOT_OBSERVED
> RESPONSE_CHANNEL        = NOT_ESTABLISHED
> ```
>
> 原因：当前可用的运行期链路是**只读内存快照**，
> 不具备指令级断点与寄存器捕获能力；
> 唯一具备该能力的 Frida 不能在受 ACE 保护的进程上使用，
> 且 Golden 手册禁止规避/触碰 ACE。


## 0. 本轮未被违反的纪律

```
Server 修改              = 无
Golden 修改              = 无
4 个 Lobby patch 修改    = 无
====================================================================================================
[10-07 19:33] BOOKING_STATE-001.md  | BOOKING_STATE-001 —— `[this+0x278]` 状态位完整调查（P0）
> 纯静态。**未修改 Server / Golden / patch / KDF hook**。
> 分析源：`image_best.bin`（运行期镜像，已解壳）


## 0. 一句话结论

```
[this+0x278] 是 **1 字节** 状态位（所有访问都用 byte ptr）
它在匹配模块内共 29 处访问：**2 处写 1**、其余为读
写 1 的两处都出现在"**开始匹配/预约流程启动**"函数里
⇒ [this+0x278] = "**预约流程已启动**"标志（booking pending/active）

证据等级：STRONG_CANDIDATE
  （行为与调用位置高度一致，但尚无字符串/枚举直接命名它）
```
====================================================================================================
[10-08 17:37] CLIENT-BOOKING-BATTLE-OBJECT-016.md  | CLIENT-BOOKING-BATTLE-OBJECT-016
# matching 的 "type-2 network object" 到底是什么，以及它是否是 accepted → Battle UDP 的桥梁

> 2026-10-08 执行。**纯静态**。未修改 client / server / senderId / booking response /
> SessionId / Battle endpoint / 28960。未 hook、未 patch、未伪造 UDP/DTLS、未运行游戏。
>
> 分析源：CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin
> （运行期已解壳镜像，10,899,456 B，**VA = 0x00400000 + 文件偏移**，
> 可读范围 `0x00400000 .. 0x00E65000`）。
> 所有 VA 为镜像 VA（imagebase 0x00400000）。
>
> 承接：013（A/B 已关）、014（accepted 出口枚举）、015（listener 7/7 REFUTED + UDP socket 锚点）。
> 本轮**只**沿 015 留下的 `matching->vt+0x5C = 0x62FDE0` 这一条新轴推进。


## 0. 结论先行（一句话回答本轮最终问题）

```
TYPE2_OBJECT = 全局 Demonware 网络核单例 [0x8269774] 当前挂载的 "transport 连接对象"
               在 "已连接 / connected" 状态下的形态。

它的 socket 是：
   socket(AF_INET, SOCK_STREAM = 1, IPPROTO_TCP = 6)   ← TCP，不是 UDP
再 connect() 到 Demonware 服务地址（host + 16-bit port）：
   0x7F3800 状态机 case 2 → 日志字符串 "DW_LOBBY_CONNECTED"（CO
====================================================================================================
[10-08 15:31] CLIENT-BOOKING-BATTLE-TRIGGER-014.md  | CLIENT-BOOKING-BATTLE-TRIGGER-014
# accepted state → Battle UDP socket 的客户端触发路径（静态追踪）

> 2026-10-08 执行。纯静态。未修改任何 server/客户端/协议。未重新动态实验。


## 0. 结论先行

```
ACCEPTED_HANDLER        = 0x632680（unified mmbook handler）
ACCEPTED_STATE_WRITES   = [this+0x288]=1、[0x849B61C]=1

0x849B61C_READERS       = 0x7CB1E2、0x7CFA87（均为 UI/progress，非 battle）
0x7CB1E2_DOWNSTREAM     = 0x620590（UI/telemetry，非 battle）
0x7CFA87_DOWNSTREAM     = 0x7CB210（UI/telemetry，非 battle）

GAME_IP_STORAGE         = 未定位到精确字段（session object ① Hostaddress，解析代码未逐条确认）
GAME_PORT_STORAGE       = 同上
GAME_ENDPOINT_CONSUMER  = UNRESOLVED

UDP_SOCKET_CREATE       = UNRESOLVED（battle 模块 0xE3xxxx，DTLS/ECDH 表已定位，socket 代码未定位）
UDP_SOCKET_CALLER_CHAIN = UNRESOLVED

BATTLE_TRIGGER_PATH     = UNRESOLVED（跨模块间接触发，非直连）
LOBBY_CONNECT_PATH_EXCLUDED = YES（0xB81EF0→0xBA4080 已排除，未重走）
====================================================================================================
[10-08 17:23] CLIENT-BOOKING-LISTENER-BRIDGE-015.md  | CLIENT-BOOKING-LISTENER-BRIDGE-015
# accepted handler 的 listener 广播 → 注册源 / vtable / callback 的静态闭合

> 2026-10-08 执行。**纯静态**。未修改 client / server / senderId / booking response /
> SessionId / 28960 / Battle server。未 hook、未 patch、未伪造 UDP/DTLS。未运行动态实验。
>
> 分析源：`CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin`
> （运行期已解壳镜像，10,899,456 B，**VA = 0x00400000 + 文件偏移**，可读范围
> `0x00400000 .. 0x00E65000`）。超出该范围的全局只能看到"引用它的指令"，看不到内容。
>
> 补充数据源（本轮新用）：`COD OL\codoMP_client_shipRetail.exe` 的 **section[2] (.tp3) raw 区**
> （RVA 0xA16000..0xA78000，文件偏移 0x702000..0x764000，**明文未加密**）。
> 用于读出 0xE69xxx 静态 listener 对象的 vtable 指针（镜像 dump 里读不到）。


## 0. 结论先行

```
ACCEPTED_HANDLER            = 0x00632680（base matching 对象 vtable+0x13C）
ACCEPTED_BROADCAST_SITE     = 0x00632824..0x00632844（成功）/ 0x0063289E..0x006328B3（失败）
ACCEPTED_BROADCAST_ABI      = listener->vtable+0x24(arg1, arg2)
                              成功 = (1, 0)；失败 = (
====================================================================================================
[10-08 14:33] MVP-PVE-MATCH-ENTRY-009.md  | MVP-PVE-MATCH-ENTRY-009
# 从 mmbook accepted 到进入 PvE 对局：缺哪一条链（静态定位 + 阻塞点）

> 2026-10-08 执行。纯静态（镜像 + 服务器源码/日志）。未启动游戏、未发送 response。


## 1. MVP Goal

```
Client → Lobby → mmbook → mmbook accepted → Battle endpoint
  → Battle connect → Battle handshake → PvE session → 进入地图
```

唯一成功标准 = 真正进入一局 PvE 对局（地图），不是"协议理解完整"。
====================================================================================================
[10-07 20:18] PUBLISHER_FAILURE_SPEC-001.md  | PUBLISHER_FAILURE_SPEC-001
> EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE 定位
> 纯静态（image_best.bin）+ 已有运行期日志比对
> 未修改 Server / Golden / 4 patch / KDF hook / 客户端
> 未启动 Booking Server，未发送 6/14，未修复任何文件


## 0. 结论摘要

| 项 | 值 | 等级 |
|---|---|---|
| ERROR_STRING_XREF | `0x0066A827` 唯一引用 `0x00DC9C6C` | CONFIRMED |
| FAILURE_FUNCTION | `0x0066A650` | CONFIRMED |
| FAILURE_CONDITION | 同一个 publisher 文件连续 3 次加载失败 | CONFIRMED |
| PUBLISHER_FILE | 一组 `.info` 发行方文件（见 §4） | CONFIRMED |
| FAILURE_REASON | 本地文件 NOT_FOUND | CONFIRMED |
| GAME_STAGE | 内容/发行方文件准备（非 Booking 前置校验） | STRONG_CANDIDATE |

一句话：

> 客户端在进入剧情/靶场时，尝试加载一组发行方（publisher）
> `.info` 文件；这些文件本地不存在，连续 3 次重试失败后，
> 调用 `0x66A650` 弹出 `EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE`。
====================================================================================================
[10-08 09:10] PUBLISHER_FILE_RECOVERY-001.md  | PUBLISHER_FILE_RECOVERY-001
> Publisher Files 恢复阶段 001
> 目标：定位原始 .info，建立恢复矩阵
> 只读搜索 + 静态证据，未修改任何文件


## 0. 结论摘要

```
ORIGINAL_PUBLISHER_FILES = FOUND_ORIGINAL
```

10 个 publisher `.info` 文件全部已经存在，位于：

```
D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT\publisher_files\
```

失败 `EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE` 的真正原因不是文件丢失，
而是 Golden 冻结副本缺少 3 个数据目录：

```
GOLDEN-LOBBY-001\REF_LOBBY_KIT\
    publisher_files\   （缺失）
====================================================================================================
[10-08 09:25] PUBLISHER_FILE_RECOVERY-002.md  | PUBLISHER_FILE_RECOVERY-002
> DEV-PUBLISHER-RESTORE 恢复验证结果
> 2026-10-08 执行，未修改 Golden / 协议 / patch / KDF / ACE


## 0. 结论

```
FOUND_ORIGINAL           = CONFIRMED
RESTORED_IN_DEV          = CONFIRMED
PUBLISHER_SERVE_CONFIRMED = CONFIRMED
PUBLISHER_FAILURE_RESOLVED = CONFIRMED
BOOKING_GATE_REACHED     = CONFIRMED
```

Publisher 文件恢复后，`EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE` 消失，
客户端正常进入大厅，并真正发出 `6/14 mmbook`。
====================================================================================================
[10-08 18:21] PVE-ACCEPTED-STATE-DYNAMIC-017.md  | PVE-ACCEPTED-STATE-DYNAMIC-017
# 动态确认 0x632680 的 mmbook accepted 分支是否执行，以及 accepted 后状态变化

> 2026-10-08 执行。**动态 + 静态**。未修改 client 指令、未新增 hook、未 patch、
> 未伪造 UDP/DTLS、未手工发包、未做 ACE/TenProtect bypass。
> 未修改 senderId / SessionId / service / type / sequence / message / endpoint / 28960。
> 未重新设计 Booking response。
>
> 唯一新增：经用户显式批准，在 nt10.py 里加了一个**只读**采样线程
> （仅 ReadProcessMemory；不写内存、不装 hook、不改指令），开关文件
> `accepted-state-probe.on`。启动客户端走既有合法提权代理 + `run_all.py`。


## 0. 结论先行

```
ACCEPTED_WIRE              = CONFIRMED（9 次 'mmbook accepted' 实际发出）
ACCEPTED_HANDLER_EXECUTED  = NO   ← mmbook accepted 分支（0x63280B）从未执行
ACCEPTED_STATE_TRANSITION  = FAILED
THIS_288_BEFORE            = 0x0000 (byte@+0x288 = 0)
THIS_288_AFTER             = 0x0000 (byte@+0x288 = 0)   ← 唯一标记从未置 1
FLAG_849B61C_BEFORE        = 0
FLAG_849B61C_AFTER         = 1   ← 但该写入**不是** accepted 分支（见 §8.2）
UDP_SOCKET_ACTIVITY        = NOT_OBSERVED
CLIENT_UDP_28960_SEEN 
====================================================================================================
[10-08 14:57] PVE-BOOKING-DYNAMIC-VALIDATION-011.md  | PVE-BOOKING-DYNAMIC-VALIDATION-011
# senderId=SessionId 假设的受控动态验证（本次未能执行）

> 2026-10-08 执行。性质：受控动态验证。结果：**被环境阻断（提权代理未就绪）**。


## 1. 本阶段性质与目标

验证唯一假设：
```
PvE mmbook response 的 senderId = findSessions 的 SessionId
= 客户端 reservation item +0x168/+0x16C = 0x632680 的 A/B 关联键
```

第一成功信号 = `battle_srv.log 出现 RX #1`（客户端 UDP → 127.0.0.1:28960）。
====================================================================================================
[10-08 15:14] PVE-BOOKING-DYNAMIC-VALIDATION-012.md  | PVE-BOOKING-DYNAMIC-VALIDATION-012
# senderId=SessionId 假设的动态验证（本轮已实际执行）

> 2026-10-08 执行。受控动态验证：真实跑了一轮 PvE matchmaking，观察 Battle UDP。


## 0. 前置：提权代理就绪

```
UAC_APPROVED             = YES（用户已批准）
ELEVATED_AGENT_READY     = YES（pid 12244, debug_privilege=true, port 61486）
logs\elevated_agent.json = 存在（mtime 15:56:16 上一轮，本轮复用 pid 12244）
```
====================================================================================================
[10-08 20:26] PVE-MATCHING-AB-ALIGN-019.md  | PVE-MATCHING-AB-ALIGN-019
# 验证 matching A/B 对齐是否解除 mmbook accepted 第一守卫

> 2026-10-08 执行。**一次最小、可回滚的 Lobby 服务端单变量实验**（用户授权）。
> 未改客户端（EXE/DLL/内存）、未 patch/hook 客户端、未发包、未动
> SessionId / senderId / accepted response / service / task / sequence / opcode /
> endpoint / Lobby TCP / type-2 / listener / UDP-Battle 参数 / ACE / 28960 / retry。
> 实验后已恢复原始服务端并做 SHA-256 校验。


## 0. RESULT

```
RESULT_CASE                = B
AB_ALIGNMENT               = CONFIRMED
AB_GUARD_CAUSALITY         = 0x6326B9 = NECESSARY BUT NOT SUFFICIENT
ACCEPTED_HANDLER_EXECUTED  = NO（未观测到 accepted 分支）
NEXT_GATE                  = ADDITIONAL_ACCEPTED_GUARD

一句话：把 findSessions 会话对象的 #7 u64 从 1 改成 SessionId 之后，
客户端侧 matching+0x3A048/+0x3A04C **确实变成了** (0x55667788, 0x11223344)，
与 accepted 信封的 A/B 完全相等（第一守卫在数值上已满足），
但 0x632680 的 accepted 分支**依然没有执行** —— [matching+0x288] 全程为 0。
⇒ A/B 对齐是**必要非充分**条件，后面还卡着另一道门。
```
====================================================================================================
[10-08 18:55] PVE-MATCHING-AB-FIELD-IDENTITY-018.md  | PVE-MATCHING-AB-FIELD-IDENTITY-018
# matching+0x3A048 / +0x3A04C 的字段身份与来源链（纯静态）

> 2026-10-08 执行。**严格 STATIC ONLY**。
> 未启动游戏、未改 EXE/DLL、未 patch、未 hook、未发包、未改用调试器、
> 未改 senderId/SessionId/server/Lobby protocol/accepted response、
> 未重跑 017、未碰 listener / type-2 / UDP-28960 / endian / ACE bypass。
> 只读：原始 EXE、运行时镜像反汇编、strings、xref、构造/调用链、已有报告。


## 0. RESULT

```
RESULT = 已完整定位。

matching+0x3A048 / +0x3A04C 不是 SessionId，也不是 response envelope 的 A/B。
它们是 **21/5 findSessions 会话对象里那个 tag=0x0A 的 u64 字段（字段序 #7）**
经客户端反序列化器写进"会话记录"对象 +0x168/+0x16C，再被 0x62F6F0 搬到 matching 的。

而我们的服务端把该 u64 **硬编码成 1**（codol_crypto.py: ob.u64(1)  # 7），
envelope 的 senderId 却是 SessionId 0x1122334455667788 →
两边是**两套不同字段**，因此在 0x6326B9 必然不相等。

  RESPONSE_AB (0x55667788, 0x11223344)  !=  MATCHING_AB (1, 0)
  ⇒ RESPONSE_AB != MATCHING_AB   （CONFIRMED）
====================================================================================================
[10-08 15:23] PVE-SENDERID-AB-ENDIAN-CONFIRMATION-013.md  | PVE-SENDERID-AB-ENDIAN-CONFIRMATION-013
# senderId(0x1122334455667788) → 0x632680(A,B) 的拆分顺序（纯静态）

> 2026-10-08 执行。纯静态。未修改任何 server/客户端/协议字段。


## 0. 结论先行

```
SENDERID_NATIVE_VALUE   = 0x1122334455667788
SENDERID_LOW32          = 0x55667788
SENDERID_HIGH32         = 0x11223344

0x7F1400_ARG1_SOURCE    = envelope.senderId 低 32 位（[ebp+8]）
0x7F1400_ARG2_SOURCE    = envelope.senderId 高 32 位（[ebp+0xc]）

A = 0x55667788（低 32 位）
B = 0x11223344（高 32 位）

SESSION_ITEM_0x168      = 0x55667788（SessionId 低 32 位）
SESSION_ITEM_0x16C      = 0x11223344（SessionId 高 32 位）

SENDERID_AB_MAPPING     = LOW_HIGH
SESSIONID_ITEM_MAPPING  = LOW_HIGH
AB_CORRELATION_PREDICTION = MATCH
====================================================================================================
[10-08 14:49] SERVER-PVE-BOOKING-RESPONSE-010.md  | SERVER-PVE-BOOKING-RESPONSE-010
# 恢复 PvE coop 的真实 mmbook booking response（服务器侧）

> 2026-10-08 执行。静态 + 服务器源码/日志分析。未启动游戏、未发送 response 到非本地目标。


## 1. MVP Goal

让客户端在收到正确 booking response 后，真正向 `GAME_IP:GAME_PORT`(127.0.0.1:28960) 发 UDP/DTLS。