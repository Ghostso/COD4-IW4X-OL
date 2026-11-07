# BOOKING-RESPONSE-CHANNEL-003
# 非侵入定位 6/14 mmbook 的真实响应通道

> 2026-10-08 执行。纯只读：分析既有服务器日志、NDIS ETL 抓包、静态镜像 `image_best.bin`。
> **未修改** Golden / Server / 4 个 patch / KDF hook / EXE / ACE。
> **未发送**任何 Booking response。**未启动**游戏进程（复用 10-08 已跑出的日志与抓包）。

---

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
   66 字节空 ACK（object=0）；开关打开时会**追加一条 type=2 的主动推送**
   （envelope=service 21 即时消息，message=`mmbook accepted\0`）。
3. 客户端在收不到 "mmbook accepted" 推送时，**主动重置该连接**并**新建一条大厅连接**
   重试整段 booking 流程（findSessions → createRoom → setRoomData → mmbook），
   重试间隔约 3~9 秒（均值 ~5.5s），期间**从不触碰 28960**（战斗服 0 收包）。
4. 静态侧：accepted handler = `0x632680`（vtable+0x140），timeout handler =
   `0x632A00`（vtable+0x13C），字符串 `mmbook accepted`/`mmbook timedout` 分别位于
   `0xDC69B0`/`0xDC69D4`。timeout 路径已定位到调用点 `0x632FCD`（带 `mmbook timedout`），
   accepted 路径的最终间接调用者仍未定位（全镜像只有 1 处 `+0x140` 间接调用，
   且签名不符，已排除）。

**因此本阶段的网络层问题已被答清**：response channel = 大厅 TCP 连接，无需再找独立端口。
剩余 UNKNOWN 全部收缩到"客户端大厅分派器里**哪段代码**用 service/task/即时消息把
响应路由到 `vtable+0x140`"，以及"PvE coop（playlist=10）需要的确切 accepted 报文内容"。

---

## 1. 6/14 精确 socket identity

来源：`DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\lobby_srv.log`（10-08 09:30:32 启动的那次大厅会话）。

```
协议        TCP（非 UDP、非 HTTP/TLS）
local  IP   127.0.0.1        （客户端）
local  port 动态临时端口，每轮重试都变：57510 / 57548 / 57556 / 57560 / 57567 / 57569 ...
remote IP   127.0.0.2        （大厅服务端，hosts 重定向别名）
remote port 3074             （lobby_server 监听 127.0.0.2:3074）
socket 创建 每次"大厅连接建立"时新建（见 §7）
是否复用   是 —— 6/14 与其它大厅 task 复用同一连接
是否新建   否 —— 6/14 不单独 connect；是 —— 每轮重试整条连接都新建
```

日志直接证据（6/14 到达时的连接身份）：

```
[09:31:54] === 大厅连接建立 ('127.0.0.1', 57548) ===
...
[09:31:59]   ★ 解密成功 #17 ... service=6 ver=0x03 task=14 declared=48
[09:31:59]        payload(45): 0a 01 00..00 13 08 1d 00..00 19 00 00 00
                               6d 6d 62 6f 6f 6b 20 37 39 36 20 41 51 41..41 3d 20 30 00
[09:31:59]        -> 6/14 命中 'mmbook' (booking 开关未开, 仅空应答)
[09:31:59]   -> 0x85 应答 seq=17(replyId=17) service=6 task=14 对象=0 (66 字节)
```

payload 解码（与 PUBLISHER_FILE_RECOVERY-002 一致）：

```
0a 01 00 00 00 00 00 00 00     senderId = 1 (u64)
13 08 1d 00 00 00             blob, len 0x1d = 29
19 00 00 00                 内层 u32 长度 25
"mmbook 796 AQAAAAAAAAA= 0"    命令内容（796=playlist 版本，AQAAAAAAAAA= = 8 字节全 0 token）
```

---

## 2. Transport 分类

```
6/14 transport = TCP，复用大厅持久连接（lobby "lsg" 协议）
  帧壳   = 0x85（KIND_TASK），请求明文 marker=0x86
  加密   = AES-CBC + HMAC8（会话密钥经 0x81/0x82/0x83 KDF 握手协商）
  分派   = service/task 双字节路由（6/14 = service 6 / task 14）
  endpoint = loopback 中介：127.0.0.1(客户端) <-> 127.0.0.2:3074(服务端)
```

明确否证项（禁止把 3074 直接叫 "Battle server protocol"）：

```
否证：6/14 走 UDP           —— 证据：走 0x85 加密 TCP 帧，UDP 战斗服 28960 整场 0 收包
否证：6/14 走 HTTP/TLS       —— 证据：0x85 自加密帧，无 HTTP 行
否证：6/14 是独立 socket     —— 证据：与其它 task 同连接、同 seq 连续递增
否证：6/14 走本地 proxy      —— 证据：127.0.0.2 为 hosts 直连别名，非代理端口
```

---

## 3. 首次请求时间线（连接 57510，登录后首轮完整 booking 流）

```
[09:31:49]  keepalive
[09:31:51]  #47 11/13 createRoom  -> roomId=0x1122334455667788 (对象=1, 114B)
[09:31:51]  #48 28/1  任务参数    -> 空 ACK
[09:31:51]  #49 21/5  findSessions -> PvE coop mission 会话(playlist=10, map=coop_take_mp_fav_tropical)
[09:31:51]  #50 6/14  mmbook      -> 空 ACK (66B, object=0)      ← T0
[09:31:51]  #51 11/4  setRoomData -> 空 ACK + 频道回显推送(type=2)
[09:31:51]  服务端再推 1 条 type=2 回显
[09:31:51]  对端关闭（clean FIN）          ← 客户端主动关闭
```

> 注意顺序：createRoom(11/13) → findSessions(21/5) → mmbook(6/14) → setRoomData(11/4)。
> 6/14 夹在 findSessions 与 setRoomData 之间，是 booking 序列的一环，不是孤立的握手。

---

## 4. Retry 时间线（连接 57548 起，每轮重试）

| 连接 | mmbook 时刻 | seq | 结束方式 | 解出任务数 |
|---|---|---|---|---|
| 57510 | 09:31:51 | 50 | 对端关闭(clean) | 51 |
| 57545 | —        | —  | 对端关闭(0 task) | 0  |
| 57548 | 09:31:59 | 17 | ConnectionReset(10054) | 21 |
| 57553 | —        | —  | 对端关闭(0 task) | 0  |
| 57556 | 09:32:04 | 16 | ConnectionReset(10054) | 17 |
| 57558 | —        | —  | 对端关闭(0 task) | 0  |
| 57560 | 09:32:10 | 20 | ConnectionReset(10054) | 21 |
| 57563 | —        | —  | 对端关闭(0 task) | 0  |
| 57567 | 09:32:17 | 16 | ConnectionReset(10054) | 18 |
| 57569 | 09:32:23 | 18 | ...（后续同理） | ... |

mmbook 相邻间隔：8 / 5 / 6 / 7 / 6 / 4 / 9 / 3 / 5 / 5 / 3 秒
→ **均值 ~5.5s，范围 3~9s**（应用层计时器抖动，非固定 socket 超时）。

---

## 5. request -> retry 之间发生的网络事件

以连接 57548 一轮为例：

```
T0      [09:31:59] 6/14 mmbook (seq=17)
T0+0ms  服务端 -> 0x85 应答 seq=17 对象=0 (66B)     ← 空 ACK
T0+~0   客户端继续发 #18..21: 102/1, 102/7, 102/1, 11/4 setRoomData
T0+~0   服务端 -> 11/4 空 ACK + 2 条 type=2 推送(回显/game start)
T0+~0   recv 异常: ConnectionResetError(10054)      ← 客户端 RST
T0+~0   === 大厅连接结束 (57548) ===
T0+~0   新建 57553 -> 握手 -> 0 task -> 对端关闭
T0+~5s  新建 57556 -> 完整握手 -> 下一轮 mmbook
```

**关键判定**：request 与 retry 之间**不存在任何独立 socket 上的 response**。
服务端确有回包（66B 空 ACK + 推送），但都在大厅连接内；客户端因未收到
"mmbook accepted" 而重置连接并重开。

```
中间是否有 network response = 有（同连接内的空 ACK + 推送）
是否独立 socket 上的 response = 否
结论 = 不存在"另一个等待响应的通道"，等待与发送在同一连接
```

---

## 6. socket 复用 / 新建分析

```
6/14 自身        ：复用大厅连接，不新建 socket
booking 重试     ：每轮新建一条大厅 TCP 连接（新 local 端口 575xx）
0-task 连接      ：每两轮 mmbook 之间夹一次"只握手、0 task 就关闭"的连接
                  （57545/57553/57558/57563...，判定：客户端重连探测/预连接，
                   具体驱动原因 UNKNOWN，见 §11）
```

即：

```
BOOKING_RESPONSE_CHANNEL = SHARED_CONNECTION_CONFIRMED
（6/14 与响应共用大厅连接；重试时整条连接重建，而非复用旧连接）
```

---

## 7. 静态 response-handler 候选

镜像源：`CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin`
（base 0x400000，10,899,456 B）。

### 7.1 字符串与 handler（CONFIRMED）

```
0xDC6704  "MM_RESERVE"
0xDC6724  "mmbook"
0xDC6800  "mmstart"
0xDC69B0  "mmbook accepted\0"      xref -> 仅 0x6326DB（0x632680 内部）
0xDC69D4  "mmbook timedout\0"      xref -> 0x632FB1（timeout 调用点）
```

vtable（matching object，基址 0xDC7270）：

```
+0x13C  [79]  0x00632A00   timeout handler
+0x140  [80]  0x00632680   accepted handler   ← "mmbook accepted"
+0x14C  [83]  0x0062C580
```

`0x632680` 在镜像中的引用：仅 vtable 槽 `0xDC73B0` / `0xDC7850`；**无任何直接 call**。

### 7.2 已定位的 timeout 调用点（CONFIRMED）

```asm
0x632FAD  mov eax, [ebx]                 ; this->vtable
0x632FB1  push 0xdc69d4                  ; "mmbook timedout"
0x632FC4  mov edx, [eax + 0x13c]         ; timeout handler
0x632FCD  call edx                       ; thiscall(ebx) + 5 栈参数(ret 0x14)
```

⇒ **retry 的静态触发点已找到**（`0x632FCD`，携带 `mmbook timedout`），见 §8。

### 7.3 accepted handler 的间接调用者（UNKNOWN，1 处候选已排除）

全镜像 `disp=0x140` 的寄存器源间接调用仅 1 处：

```asm
0x91B198  mov esi, ecx        ; this
0x91B19C  mov edx, [eax+0x140]
0x91B1A2  push edi            ; 仅 1 个栈参数
0x91B1A3  call edx
```

但 `0x632680` 是 `ret 0x14`（5 栈参数），与此处"1 参数 thiscall"**签名不符** ⇒
该 `+0x140` 是**另一个对象**的 vtable，**REFUTED** 为 accepted caller。

⇒ 与既往结论一致：`ACCEPTED_HANDLER_CALLER = UNKNOWN`。
网络侧证据表明它应位于"大厅 service/task + 即时消息分派器"里（数据驱动分派，
故无直接 call 可搜），但未在本轮定位到具体地址。

### 7.4 响应入口候选（CANDIDATE）

```
RESPONSE_ENTRY_CANDIDATE = 大厅连接 recv -> 0x85 解密/分派
   网络对象取包/回调注册   = 0x7E7E30   （既往已 CONFIRMED）
   后续路由到 0x632680    = UNKNOWN 的最终一跳
```

---

## 8. retry 触发机制

```
BOOKING_RETRY_TRIGGER = CANDIDATE（时间线与触发点均已观测到，缺一个字段级确证）
```

证据链：

1. 静态：`0x632FCD` 在 `cmp byte [ebx+0x278],0` 守卫通过后，用
   `mmbook timedout` 调用 timeout handler `0x632A00`（vtable+0x13C）。
2. 运行期：每轮 booking 未成功 → 客户端 RST 大厅连接 → 新建连接重发 booking。
3. 间隔 3~9s、非固定 ⇒ 是**应用层状态机超时**（booking state timeout），
   不是 TCP socket 超时，也不是服务端显式拒绝。

判定排除：

```
否证 socket timeout       —— 间隔抖动 + 客户端主动 RST 整条连接
否证 server 拒绝即停       —— 服务端回空 ACK 后客户端继续发 11/4，随后才重置
否证固定计时器             —— 间隔 3~9s 不等
支持 booking state 超时    —— "mmbook timedout" 被 timeout handler 消费
```

---

## 9. Evidence 表

| # | 证据 | 来源 | 等级 |
|---|---|---|---|
| 1 | 6/14 走大厅 TCP 连接 127.0.0.1:ephemeral -> 127.0.0.2:3074 | lobby_srv.log | CONFIRMED |
| 2 | 6/14 帧壳 0x85，请求 marker=0x86，service=6 task=14 | lobby_srv.log | CONFIRMED |
| 3 | 服务端对 6/14 回 66B 空 ACK（object=0）于同一连接 | lobby_srv.log | CONFIRMED |
| 4 | booking 开关打开时追加 type=2 push "mmbook accepted" | lobby_server.py:849-852 | CONFIRMED(实现) |
| 5 | 战斗服 28960 整场收包=0（客户端从未连 28960） | battle_srv.log | CONFIRMED |
| 6 | accepted handler = 0x632680，字符串 0xDC69B0 | image_best.bin | CONFIRMED |
| 7 | timeout handler = 0x632A00，调用点 0x632FCD 带 "mmbook timedout" | image_best.bin | CONFIRMED |
| 8 | 0x632680 无直接 call，仅 vtable+0x140 | image_best.bin | CONFIRMED |
| 9 | 唯一 +0x140 间接调用 0x91B19C 签名不符（1 参 vs 5 参） | image_best.bin | REFUTED |
| 10 | 重试间隔 3~9s，均值 ~5.5s | lobby_srv.log | CONFIRMED |
| 11 | 每轮重试新建连接、新 local 端口 | lobby_srv.log | CONFIRMED |
| 12 | 0-task 连接夹在重试之间（原因） | lobby_srv.log | UNKNOWN |
| 13 | 客户端主动 RST（10054）/clean close 驱动重试 | lobby_srv.log | CONFIRMED |
| 14 | 响应 = 大厅连接内空 ACK + 推送，无独立 response socket | lobby_srv.log + battle_srv.log | CONFIRMED |
| 15 | accepted 最终路由调用者（vtable+0x140 的调用方） | image_best.bin | UNKNOWN |

---

## 10. 显式 UNKNOWN 清单

```
1. accepted handler 0x632680 的最终间接调用者（大厅分派器哪一段）
2. 大厅 service/task + 即时消息(service=21)分派器把 "mmbook accepted"
   路由到 booking 对象的确切地址/表结构
3. PvE coop(playlist=10) 需要的确切 accepted 报文内容/字段序
   （"mmbook accepted" 靶场信封曾被 9/9 断连否证，见 STAGE_REPORT_BATTLE.md）
4. 0-task 连接的驱动原因（预连接？健康探测？客户端内部竞争？）
5. retry 计时器是否与 "mmbook timedout" 的 5s 默认值字段直接对应
6. 6/14 响应若是 service=21 即时消息，客户端如何把它与 booking 会话关联
   （roomId=0x1122334455667788 是否作为关联键）
```

---

## 11. 显式 REFUTED 清单

```
REFUTED: 6/14 走 UDP
REFUTED: 6/14 走 HTTP/TLS
REFUTED: 6/14 是独立 socket / 单独 connect
REFUTED: 6/14 响应走 28960（战斗服整场 0 收包）
REFUTED: 0x91B19C 的 [reg+0x140] 调用是 accepted handler 0x632680
         （签名 1 参数 vs ret 0x14 的 5 参数不符）
REFUTED: retry 是固定 socket timeout（间隔 3~9s 抖动）
REFUTED: 0x632680 存在直接 call（镜像内 direct call = 0）
REFUTED: 6/14 响应通道是独立端口/桥（无任何非 3074/28960 的本地端口流量）
```

---

## 12. 推荐下一步实验

**本阶段目标已达成，不再扩展网络定位。** 后续只做下面这种"只读 + 单变量"实验：

1. **（推荐）在大厅连接上做"单帧 accepted 注入"验证，但不发送**：
   - 仅**记录** `RESPONSE_FORMAT_CANDIDATE`：
     `build_push(marker=2)` 包裹 `instant_push_body(1,"localhost", u32len(16)+b"mmbook accepted\0")`。
   - 按纪律**不发**，等拿到真实 PvE coop 响应样本（官方 pcap / ol-mod 源码）再逐字节对照。

2. **静态补齐最后一跳**：从 `0x7E7E30`（网络对象取包）出发，沿 0x85 解密后的
   service/task 分派表，定位 service=21（InstantMessage）的 handler 表项，
   再追它是否 `call [obj+0x140]`。目标：把 UNKNOWN#1/#2 转成 CONFIRMED。

3. **retry 计时器字段化**：在 timeout handler `0x632A00` 内找 5s 常量/字段，
   确认 `mmbook timedout` 的触发阈值来源，把 `BOOKING_RETRY_TRIGGER` 从 CANDIDATE 升 CONFIRMED。

4. **解锁条件不变**：要真正让 PvE booking 成功，仍需外部提供
   `ol-mod`（src/network/DedicatedControl.* / src/game_server/）或真实 booking 应答样本。
   在此之前任何"自编 accepted 响应"都属于被禁的猜测发送。

---

## 13. 纪律核对

```
Golden 修改            = 无
Lobby Server 修改      = 无（仅读日志/源码）
Battle Server 修改     = 无
4 个 patch 修改        = 无
KDF hook 修改          = 无
客户端 EXE/DLL 修改    = 无
Booking response 发送  = 无
猜测 opcode 发送       = 无
NOP/patch retry        = 无
强制内存状态修改       = 无
ACE/TenProtect 触碰    = 无
游戏进程启动           = 无（复用既有日志与抓包）
```
