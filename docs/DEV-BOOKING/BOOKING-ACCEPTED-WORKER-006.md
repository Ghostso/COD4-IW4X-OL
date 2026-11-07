# BOOKING-ACCEPTED-WORKER-006
# accepted 状态消费者 + matchmaking endpoint + 战斗连接 worker（静态）

> 2026-10-08 执行。纯静态。镜像 `image_best.bin`（base 0x400000）。
> 未修改 Golden/Server/PE/patch/KDF hook，未启动游戏，未发送 response。

---

## 1. Scope

只追一条链：

```
accepted state → state consumer → matchmaking/server endpoint → connect worker
```

回答：谁消费 accepted 状态、endpoint 存哪、谁最终 connect。

---

## 2. Previous Confirmed Chain（承接 003/004/005）

```
service=21/type=2 "mmbook accepted"
  → 0x7F1544 strncmp("mmbook",6)
  → [0x82e13fc] → vtable+0x13C → 0x632680(this,A,B,ptr,msg,15)
  → 0x6326DF strncmp("mmbook accepted",15)
  → accepted branch: [this+0x288]=1 , [0x849b61c]=1 + vtable 通知
A/B = reservation item +0x168/+0x16C (u64 会话标识)，存 this+0x3a048/0x3a04c
```

---

## 3. `[0x849B61C]` Readers（★ 分类读写）

14 处引用逐条反汇编分类：

| 地址 | 指令 | 读/写 |
|---|---|---|
| 0x632827 | mov [0x849b61c],1 | 写（accepted branch）|
| 0x634BEC | mov [0x849b61c],1 | 写 |
| 0x639A79 | mov [0x849b61c],1 | 写 |
| 0x63C9C1 | mov [0x849b61c],1 | 写 |
| 0x7C4743 | mov [0x849b61c],1 | 写 |
| 0x7C482A | mov [0x849b61c],1 | 写 |
| 0x7CB1F9 | mov [0x849b61c],bl(0) | 写（清 0）|
| 0x7CB234 | mov [0x849b61c],1 | 写 |
| 0x7CF7F7 | mov [0x849b61c],dl | 写 |
| 0x7CFAEA | mov [0x849b61c],1 | 写 |
| **0x7CB1E2** | **cmp [0x849b61c],bl** | **读** |
| **0x7CFA87** | **cmp [0x849b61c],al** | **读** |

（0x6398AF 的 imul、0x7CFADC 的 add eax 为字节巧合，非真引用）

**只有 2 个 reader**，都在 0x7cxxxx（游戏流程）模块：

```
reader#1 0x7CB1E2: cmp [0x849b61c],0 → je 跳过
  if(flag && [0xc7341db]) call 0x620590
  上下文：读 [0x82e13fc] 并 call vtable+0x110（匹配单例状态查询）

reader#2 0x7CFA87: cmp [0x849b61c],0 → je 跳过
  上下文：读 [0x82e13fc] vtable+0x94 做浮点进度计算，否则 call 0x7cb210
```

```
ACCEPTED_STATE_CONSUMER = CONFIRMED
  （global flag 的 2 个读取点已定位，均在 0x7cxxxx 游戏流程模块）
```

---

## 4. `[this+0x288]` Readers

`[this+0x288]`（对象级 accepted 状态）由 `0x63280B` 置 1。
该字段是 disp 相对访问（[reg+0x288]），全镜像同类 offset 很多，需先证明
`reg` 来自匹配对象（vtable=0xDC7274 / 单例 [0x82e13fc]）才能归属。

本阶段未做全量 disp 扫描归属（0x288 是高频 offset，误报多）。

```
[this+0x288]_READERS = PARTIAL（未逐条归属；已知写点 0x63280B，读点待证）
```

---

## 5. Accepted Notification Analysis

accepted branch（0x632680 成功路径）调用 5 个 vtable 槽：

| slot | target | 分析 | 与 endpoint 关系 |
|---|---|---|---|
| +0x150 | 0x6297A0 | **thunk**：strlen(字符串) → 转调 +0x14C | 转发 |
| +0x14C | 0x629730 | **serialize + 入队**：call 0x769710 序列化，写 [this+0x3a0b0]，call 0x6568f0 | ★ 关键（入队）|
| +0x148 | 0x62C580 | 状态清理/迁移 | 次要 |
| +0x5C  | 0x62FDE0 | 状态查询（bool） | 次要 |
| +0x24  | 0x62DE90 | 监听者广播（循环 vtable+0x24） | 通知 |

关键证据（0x629730，vtable+0x14C）：

```asm
0x629761  call 0x769710          ; 序列化（拼出下一条消息）
0x629776  lea eax,[esi+0x3a0b0]  ; ★ 目标字段
0x62978D  call 0x6568f0          ; 入队到 this+0x3a0b0 队列
```

即 accepted 的**实际落点是「向对象内消息队列 [this+0x3a0b0] 入队一条已序列化消息」**，
不是直接 connect。

```
ACCEPTED_NOTIFICATION = CONFIRMED（+0x150 thunk → +0x14C 序列化入队）
```

---

## 6. Matchmaking Endpoint Storage

`[this+0x3a0b0]` 是一条**消息队列头指针**（链表，节点 stride ≈0x820）：

```
node+0x000 / +0x004  : 载荷
node+0x008           : 序列化数据（lea esi+8 传入 0x818de0）
node+0x808 / +0x810  : 回调函数指针
node+0x818 / +0x81c  : next / prev（链表）
```

consumer（worker 0x6334xx）：

```asm
0x633517  mov esi,[ebx+0x3a0b0]   ; 取队头
0x633530  call 0x818de0           ; 处理消息（状态机）
0x633545  call [esi+0x810]        ; 节点回调
0x63355F  mov edx,[eax+0x818]     ; next 节点
```

endpoint 具体 IP/port 字段**未在 0x3a0b0 区域直接定位**；它是动态下发，
来自 matchmaking 响应（findSessions/createRoom 的 session/room 对象），
存于匹配对象/连接对象的某字段，再由 worker 消费。

```
MATCHMAKING_ENDPOINT_STORAGE = PARTIAL
  （消息队列 [this+0x3a0b0] CONFIRMED；IP/port 精确字段偏移未定位）
```

---

## 7. Endpoint Producer

端点在 accepted 前由 matchmaking 响应产生（findSessions 21/5 → createRoom 11/13）。
服务端下发的 session/room 对象被解析后写入匹配对象。

```
ENDPOINT_PRODUCER = HIGH-CONFIDENCE（响应解析路径，精确字段未逐条反汇编）
```

---

## 8. Endpoint Consumer

worker 0x6334xx → 0x818de0（状态机）→ 0x803830（底层传输类型）→ 0xb7a670。

```
0x818de0  状态机，switch [0x84aba50]（0..5）跳表 0x818f54
          其中某 case: call 0x803830（取对象底层传输类型）+ 0xb7a670
0x803830  此前记录为 "返回对象的底层传输类型"（BOOKING_EVIDENCE-002 UNKNOWN）
```

```
ENDPOINT_CONSUMER = HIGH-CONFIDENCE（队列 worker → 状态机链路可见，未到 connect 本体）
```

---

## 9. State Machine / Worker

架构形态（与任务提示一致，非 direct-connect）：

```
0x632680 accepted
  → 写 [this+0x288]=1、[0x849b61c]=1（状态）
  → vtable+0x14C 序列化入队 [this+0x3a0b0]
  → worker 0x6334xx 出队 → 0x818de0 状态机 → 0x803830 传输类型 → ...
  → （下游）socket/connect
```

`[0x849b61c]` 的 2 个 reader 则是**轮询/游戏流程**消费（进度、状态推进），
与队列 worker 是两条并行消费路径。

```
WORKER_ARCHITECTURE = CONFIRMED（queue + state + poll 双路径）
```

---

## 10. Socket Wrapper

未定位到明确 connect 包装（socket/AF_INET/SOCK_DGRAM/htons(port)→connect）。

```
SOCKET_WRAPPER = UNRESOLVED
```

---

## 11. Dynamic IP/Port Dataflow（★ 重要负结果 + 候选）

```
REFUTED: 28960 = 客户端硬编码端口（镜像内无 0x7120 端口常量，仅字符串 "p q"）
CANDIDATE: 客户端默认候选端口表（0x804A82）：
    0x206c..0x207b = 8300..8316
    0x20d0 = 8400 , 0x2198 = 8600 ...
   —— 战斗服端口疑似动态/区间下发，符合任务提示 "3074 → response → 8300~8319"
```

```
DYNAMIC_ENDPOINT = CONFIRMED（非硬编码 28960）
PORT_CANDIDATE_LIST = CANDIDATE（8300~8316/8400/8600，用途未最终证实）
```

---

## 12. Optional Envelope A/B Mapping（次要，未推进）

上阶段 A/B=envelope senderId(u64) 标 HIGH-CONFIDENCE。本阶段优先追 endpoint，
未补帧层逐条映射（会显著拖慢主链）。维持 HIGH-CONFIDENCE，留待后续。

---

## 13. Full Accepted → Connect Chain

```
service=21 "mmbook accepted"
  → 0x632680 accepted branch
  → [this+0x288]=1（对象态） / [0x849b61c]=1（全局态）
  → vtable+0x14C(0x629730) 序列化入队 [this+0x3a0b0]
  → worker 0x6334xx 出队 → 0x818de0 状态机 → 0x803830 传输类型 → 0xb7a670
  → 【UNKNOWN】socket/connect（endpoint = 动态 IP:port，来自 matchmaking 响应）
```

```
[0x849b61c] reader 0x7CB1E2 / 0x7CFA87 = 游戏流程并行消费（状态/进度）
```

---

## 14. Evidence Classification

| 项 | 地址 | 等级 |
|---|---|---|
| [0x849b61c] 写=1（accepted） | 0x632827 | CONFIRMED |
| [0x849b61c] reader#1 | 0x7CB1E2 | CONFIRMED |
| [0x849b61c] reader#2 | 0x7CFA87 | CONFIRMED |
| vtable+0x150 thunk | 0x6297A0 | CONFIRMED |
| vtable+0x14C 序列化入队 | 0x629730 | CONFIRMED |
| [this+0x3a0b0] = 消息队列头 | 0x629776/0x633517 | CONFIRMED |
| worker 出队处理 | 0x6334xx | CONFIRMED |
| 状态机 0x818de0 | 0x818de0 | CONFIRMED |
| 传输类型 0x803830 | 0x818e20 | HIGH-CONFIDENCE |
| endpoint 动态（非 28960） | 负结果 | CONFIRMED |
| 端口候选 8300~8316 | 0x804A82 | CANDIDATE |
| connect 包装 | — | UNRESOLVED |

---

## 15. Refuted Paths

```
REFUTED: accepted 直接 connect 到 28960
REFUTED: 28960 是客户端硬编码常量
REFUTED: [0x849b61c] 只有一个 reader（实为 2 个读 + 8 个写）
REFUTED: vtable+0x150 是独立业务逻辑（实为 strlen→+0x14C 的 thunk）
```

---

## 16. Remaining UNKNOWN

```
1. endpoint 的精确存储字段（IP/port 在哪个对象/偏移）
2. connect 包装函数（socket/AF_INET/htons(port)/connect 的具体地址）
3. 0x803830 返回的"传输类型"如何映射到 socket 操作
4. 端口候选表 8300~8316 是否真的用于战斗连接（或仅配置）
5. [this+0x288] 的读取者归属
```

---

## 17. Conclusion

```ini
ACCEPTED_STATE_CONSUMER      = CONFIRMED
MATCHMAKING_ENDPOINT_STORAGE = PARTIAL
BATTLE_CONNECT_PATH          = PARTIAL
```

- accepted 状态的消费者已定位：全局态 `[0x849b61c]` 的 2 个 reader（0x7CB1E2 / 0x7CFA87），
  以及对象内消息队列 `[this+0x3a0b0]` 的 worker（0x6334xx → 0x818de0 状态机）。
- endpoint 是动态下发（28960 已否证为客户端常量），存于 matchmaking 状态/队列，
  精确 IP/port 字段与最终 connect 包装仍未闭合 → PARTIAL。

---

## 18. Next Step

1. 从 0x818de0 状态机 + 0x803830 传输类型继续追，定位 socket/connect 包装
   （重点找 AF_INET/SOCK_DGRAM + htons(dynamic_port) + connect/WSASendTo）。
2. 定位 endpoint 精确字段：在 findSessions(21/5)/createRoom(11/13) 响应解析路径
   里找 sockaddr_in 构造（sin_addr=4B、sin_port=htons(动态端口)）。
3. 证实端口候选表 8300~8316 的用途（是否战斗连接 fallback 表）。
4. 归拢 [this+0x288] 读者（disp 扫描 + 对象归属验证）。
```
