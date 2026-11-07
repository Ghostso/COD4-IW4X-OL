# BOOKING-RESPONSE-PARAMS-005
# A/B 参数来源 + accepted 分支到 28960 的路径（静态）

> 2026-10-08 执行。纯静态。镜像 `image_best.bin`（base 0x400000）。
> 未修改 Golden/Server/PE/patch/KDF hook，未启动游戏，未发送 response。

---

## 1. Scope

只研究两个问题：
```
A. call 0x632680(this, A, B, ptr, msg, 15) 中 A/B 的精确来源与语义
B. 0x632680 accepted branch 最终如何进入 28960 battle-server 路径
```

---

## 2. Previous Confirmed Chain（承接 003/004）

```
Lobby TCP → 0x85 decrypt → marker=2 → service=21 immediate-message envelope
  → command="mmbook accepted"
  → 0x7F1544 strncmp(cmd,"mmbook",6)
  → 0x7F1554 global [0x82e13fc] → vtable+0x13C → 0x632680
  → 0x7F156F call 0x632680(this, A, B, ptr, msg, 15)
  → 0x6326DF strncmp(msg,"mmbook accepted",15) → accepted / failure
vtable 基 = 0xDC7274（不是 0xDC7270）
  +0x13C = 0x632680(mmbook 统一 handler)   +0x140 = 0x62E9F0(mmrsv)
```

---

## 3. Dispatcher Caller Analysis

dispatcher = service=21 handler `0x7F1400`（函数指针表 `0xDE080C` 项，索引 21）。
它 `ret 0x14`（thiscall + 5 参数）：`[ebp+8]..[ebp+18]`。

在 0x7F156F 处，它把**自己的参数**转发给 0x632680：

```asm
0x7F1567  mov edx,[ebp+0xc]   ; B = dispatcher arg2
0x7F156B  mov edx,[ebp+8]     ; A = dispatcher arg1
0x7F156E  push edx            ; arg1=A
0x7F156F  call 0x632680
```

因此 **A = dispatcher 的 arg1，B = dispatcher 的 arg2**。
dispatcher 由 frame parser 通过函数指针表调用（service=21），arg1/arg2 来自
即时消息信封解包结果（见 §4/§5 的高置信判定，帧层 arg→字段映射未逐条反汇编确认）。

---

## 4. A 参数 Dataflow（★ 请求侧 CONFIRMED）

请求侧写入点 `0x62F6F0`（BOOKING_EVIDENCE-002 所述 "从 [edi+0x168]/[edi+0x16C] 写 A/B"）：

```asm
0x62F6F0  55             push ebp            ; this=esi, 参数 edi=reservation item 指针
0x62F717  mov [esi+0x3a048], ebx(0)          ; A 清零初始化
0x62F71D  mov [esi+0x3a04c], ebx(0)          ; B 清零初始化
0x62F736  mov ecx, [edi+0x168]               ; ★ A = item+0x168
0x62F73C  mov [esi+0x3a048], ecx              ;    存 this+0x3a048
0x62F742  mov edx, [edi+0x16c]               ; ★ B = item+0x16C
0x62F748  mov [esi+0x3a04c], edx              ;    存 this+0x3a04c
0x62F74E  lea edx,[edi+0x170]                ; item+0x170 = 字符串
0x62F760..0x62F767  strlen([edi+0x170])       ; 计算字符串长度
0x62F78D  call 0xc427f0                      ; 复制到 this+0x3a050
```

```
A 数据类型  = u32
A 来源      = reservation item 字段 [item+0x168]
A 本地存储  = [this+0x3a048]
B 数据类型  = u32
B 来源      = reservation item 字段 [item+0x16C]
B 本地存储  = [this+0x3a04c]
```

reservation item 是一个 stride=0x238（imul eax,0x238）的结构数组；
item+0x168/0x16C 是一对相邻 u32（合成一个 u64），item+0x170 是配套字符串。

```
A_B_SOURCE_REQUEST_SIDE = CONFIRMED
```

---

## 5. B 参数 Dataflow（响应侧校验）

`0x632680` 入口校验（对 0x7F156F 传入的 A/B）：

```asm
0x6326B6  mov eax,[ebp+8]            ; arg1 = A
0x6326B9  cmp eax,[esi+0x3a048]      ; A 必须 == 本地 A
0x6326C5  mov ebx,[ebp+0xc]          ; arg2 = B
0x6326C8  cmp ebx,[esi+0x3a04c]      ; B 必须 == 本地 B
```

即：**响应里的 A/B 必须与请求时写入的 [this+0x3a048]/[this+0x3a04c] 一致**，
否则直接 `jne 0x632916` 丢弃。

```
A/B 语义 = 预约/匹配会话标识（u64，低 u32=A，高 u32=B）
A/B 作用 = request ↔ response 关联键（防止错配到别的 reservation）
```

响应侧 A/B 来源：service=21 信封解包后经 frame parser → dispatcher arg1/arg2
传入。最可能对应信封的 `senderId`(u64)（低/高 u32）或等价字段。

```
A_B_RESPONSE_SIDE_SOURCE = HIGH-CONFIDENCE
  （校验逻辑 CONFIRMED；帧层 envelope 字段→dispatcher arg 的逐条映射未反汇编确认）
```

---

## 6. Request/Response Correlation

```
booking request (6/14 mmbook)
  → 0x62F6F0 把 reservation item 的 [item+0x168]/[item+0x16C] 写入
    this+0x3a048(A) / this+0x3a04c(B)
  → 服务端 booking 成功后回 service=21 "mmbook accepted"（信封携带 A/B）
  → dispatcher 把信封 A/B 传给 0x632680
  → 0x632680 校验 A/B == this+0x3a048 / this+0x3a04c
  → 匹配才进入 accepted branch
```

```
CORRELATION_FIELD_OFFSETS = CONFIRMED
  request field: item+0x168(A) / item+0x16C(B)
  local storage: this+0x3a048(A) / this+0x3a04c(B)
  response arg:  arg1(A) / arg2(B)
```

---

## 7. 0x632680 Full Disassembly（要点）

已完整反汇编（0x632680..0x632960，next fn 0x632A00）。控制流：

```
0x63268D  cmp [esi+0x278],0        ; 守卫 booking pending
0x63269B  cmp [0x76446b0],3        ; 全局计数 <3
0x6326B9  cmp arg1,[esi+0x3a048]   ; A 校验
0x6326C8  cmp arg2,[esi+0x3a04c]   ; B 校验
0x6326DA  push "mmbook accepted"; push 15; call strncmp
0x6326E9  jne 0x632876             ; 非 accepted → failure 分支
0x6326EF..0x632710  再校验 reservation[i](stride 0x238) 的 A/B
0x632736  进入 accepted branch（成功路径）
0x632876  进入 failure/timeout 分支
```

---

## 8. Accepted Branch（0x632736..0x632873）

```asm
0x632745  mov [esp+0x28],1             ; 成功标志=1
0x632761  call 0x771320                ; 日志/遥测（"Ub" @0xdc74f8）
0x632770  call 0x631e90 / 0x632070     ; 处理
0x632780  call vtable+0x150(0x6297A0)  ; 携带 A/B
0x632791  call 0x631e50                ; 布尔判断
0x6327A1  call 0x811340                ; （条件）
0x6327AB  call vtable+0x14C(0x629730)
0x6327F5  call 0x62abf0                ; 构造 reservation item
0x6327FC  call vtable+0x148(0x62C580)
0x63280B  mov byte [esi+0x288],1       ; ★ 对象状态 = accepted
0x632812  call 0x62f6c0                ; 复位 A/B（清 this+0x3a048/0x3a04c）
0x632819  call vtable+0x5C(0x62FDE0)   ; 检查
0x632824  loop: call vtable+0x24(0x62DE90)  ; 遍历监听者通知
0x632827  mov byte [0x849b61c],1       ; ★ 全局标志 = 1
0x632846  call 0x6293b0 / 0x629f80
0x632873  ret 0x14
```

关键副作用：
```
[this+0x288]  = 1   （对象级 accepted 状态）
[0x849b61c]   = 1   （全局 accepted 标志）
+ 一串 vtable 通知调用（0x150/0x14C/0x148/0x5C/0x24）
+ 复位 A/B（0x62f6c0）
```

**accepted branch 不直接调用 socket/connect**，只做状态迁移 + 通知。

```
ACCEPTED_BRANCH = CONFIRMED
```

---

## 9. Timedout/Failure Branch（0x632876..0x6328E8）

```asm
0x632876  cmp byte [esi+0x280],0
0x63287F  cmp [esi+0x10780],0xa
0x63288C  call 0x62f6c0                ; 复位 A/B
0x6328BB  call vtable+0x148(0x62C580)  ; 清理/状态迁移
0x6328E8  ret 0x14
```

与 accepted 分支对比：**共同点**是都调用 `0x62f6c0`（复位 A/B）和 vtable+0x148；
**不同点**是 accepted 额外写 `[this+0x288]=1`、`[0x849b61c]=1` 并广播 vtable+0x24 通知。
即「置 accepted 状态」是 accepted 分支独有的、触发后续 28960 的关键动作。

---

## 10. State Transition

```
accepted:  [this+0x288]=1 , [0x849b61c]=1 , 广播 vtable+0x24(0,1)
timedout:  仅复位 A/B + vtable+0x148
```

`[0x849b61c]` 是**全局字节标志**，被 14 处引用（0x63xxxx 匹配模块 + 0x7cxxxx UI/房间流）。
它是 accepted 状态对外可见的全局信号，后续战斗连接/房间流程据此推进。

---

## 11. Battle Endpoint Dataflow（★ 重要负结果）

搜索 28960 端口常量：
```
0x7120 (28960)      refs = 0xd9453a, 0xd94597   → 均在字符串 "p q" 内（非端口）
htons(28960)=0x2071  refs = 0x804aba            → 是端口范围表 0x206c..0x207b 之一（=8305，非 28960）
```

```
结论：28960 在客户端镜像里【不是】硬编码常量。
     战斗服 endpoint（IP:port）来自动态数据（matchmaking 响应 / server descriptor），
     而非编译期常量。
```

这与服务端行为一致：服务端在 booking 成功后把战斗服地址下发给客户端，
客户端按响应中的地址去连。本地参考实现里战斗服固定 28960，但**客户端侧不写死**。

```
BATTLE_ENDPOINT_SOURCE = DYNAMIC（来自响应，非客户端常量）  [HIGH-CONFIDENCE]
```

---

## 12. 28960 Connection Path

```
accepted branch
  → 写 [this+0x288]=1 + [0x849b61c]=1（状态）
  → vtable 通知（0x24 广播等）
  → 【下游 worker/状态机】读取 accepted 状态 + 响应里的战斗服 endpoint
  → connect(战斗服 IP:port)
```

0x632680 本身**不直接 connect**。28960 连接是 accepted 状态置位后由下游异步流程
消费 endpoint 发起（符合任务提示的 "state write → worker → connect" 形态）。

```
BOOKING_ACCEPTED_TO_28960 = PARTIAL
  已 CONFIRMED：accepted branch 置 accepted 状态（[this+0x288]/[0x849b61c]）+ 通知
  未 CONFIRMED：下游 worker 读取该状态并取 endpoint → connect 的精确函数链
  已排除：28960 为客户端硬编码常量（镜像内无此端口常量）
```

---

## 13. Evidence Classification

| 项 | 地址 | 等级 |
|---|---|---|
| A=[item+0x168]→this+0x3a048 | 0x62F736/0x62F73C | CONFIRMED |
| B=[item+0x16C]→this+0x3a04c | 0x62F742/0x62F748 | CONFIRMED |
| item+0x170 字符串→this+0x3a050 | 0x62F74E/0x62F78D | CONFIRMED |
| 0x632680 校验 A/B | 0x6326B9/0x6326C8 | CONFIRMED |
| dispatcher 转发 A/B | 0x7F1567/0x7F156B | CONFIRMED |
| accepted 置 [this+0x288]=1 | 0x63280B | CONFIRMED |
| accepted 置 [0x849b61c]=1 | 0x632827 | CONFIRMED |
| accepted 广播 vtable+0x24 | 0x632836 | CONFIRMED |
| accepted 复位 A/B | 0x632812 | CONFIRMED |
| 响应侧 A/B=envelope 字段(senderId?) | 帧层映射 | HIGH-CONFIDENCE |
| 28960 为动态 endpoint | 负结果 | HIGH-CONFIDENCE |
| 下游 connect 函数链 | — | UNKNOWN |

---

## 14. Refuted Paths

```
REFUTED: 28960 是客户端硬编码常量（镜像内无 0x7120 端口引用，仅有字符串 "p q"）
REFUTED: 0x804aba 的 0x2071 是 htons(28960)（实为端口范围表 8300-8319 的一项）
REFUTED: accepted branch 直接 connect 到 28960（只写状态+通知，无 socket 调用）
REFUTED: A/B 是 senderId 之外的新字段（请求侧已确认来自 item+0x168/0x16C）
```

---

## 15. Remaining UNKNOWN

```
1. 帧层 envelope 字段 → dispatcher arg1/arg2 的逐条映射（senderId u64 是否即 A/B）
2. 下游 worker 读取 [0x849b61c] / [this+0x288] 后取 endpoint 的函数链
3. 战斗服 endpoint 在哪个 matchmaking 响应字段里下发（service/task、字段偏移）
4. accepted 之后连接 28960 的具体 connect 包装函数与 IP 来源
```

---

## 16. Conclusion

```ini
BOOKING_RESPONSE_PARAMS = CONFIRMED
BOOKING_ACCEPTED_TO_28960 = PARTIAL
```

- A/B 是预约/匹配会话标识（u64，低/高 u32），请求侧来自 reservation item
  `[item+0x168]`/`[item+0x16C]`，写入 `this+0x3a048`/`this+0x3a04c`，
  响应侧经 dispatcher 传入 0x632680 校验一致 —— **A/B 数据流已闭合**。
- accepted branch 已确认置 `[this+0x288]=1`、`[0x849b61c]=1` 并广播通知，
  但它**不直接 connect**；28960 也不是客户端常量（动态 endpoint）。
  因此 28960 连接是 accepted 状态的下游消费，当前定位到状态写入点，
  尚未追到 connect 包装函数 —— PARTIAL。

---

## 17. Next Step

1. 追 envelope 字段→dispatcher arg 映射（frame parser 调 0x7F1400 的调用点），
   确认 senderId u64 == A/B，把 §5 的 HIGH-CONFIDENCE 升为 CONFIRMED。
2. 从 [0x849b61c]（14 处引用）与 [this+0x288] 的读者出发，定位下游 worker，
   建立 accepted 状态 → endpoint 提取 → connect 的完整链。
3. 在服务端侧核对：哪个 service/task 下发战斗服 IP:port（本地实现只有 28960，
   需确认真实协议字段），以便后续构造正确 endpoint 应答。
```
