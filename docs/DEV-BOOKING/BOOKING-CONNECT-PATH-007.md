# BOOKING-CONNECT-PATH-007（完整版）
# 0x818de0 状态机 + 0x803830 传输对象 + endpoint + connect（静态）

> 2026-10-08 执行。纯静态。镜像 `image_best.bin`（base 0x400000）。
> 未修改 Golden/Server/PE/patch/KDF hook，未启动游戏，未发送 response。

---

## 1. Scope

闭合 `0x818de0 → 0x803830 → endpoint → socket → connect`，并核实 006 的链归属。

---

## 2. Previous Confirmed Chain（承接 003~006）

```
mmbook accepted → 0x632680 → accepted branch（[this+0x288]=1,[0x849b61c]=1）
  → vtable+0x150(0x6297A0 thunk) → vtable+0x14C(0x629730) 序列化入队 [this+0x3a0b0]
  → worker 0x6334xx → 0x818de0 → 0x803830 → UNKNOWN
```

---

## 3. 0x818de0 State Machine（完整反汇编）

```asm
0x818DE0  mov edi,eax                 ; 入参 = &队列节点数据
0x818DED  cmp byte [0x849ba3d],0      ; 守卫
0x818DF9  mov eax,[0x84aba50]         ; 全局状态 0..5
0x818DFE  cmp eax,5 / ja bail
0x818E07  jmp [eax*4 + 0x818f54]      ; 6 路跳表
```

跳表：`[0..3]=0x818f4b(bail), [4]=0x818e0e, [5]=0x818f4b`。
仅 state 4 有实现，其内容引用字符串 `"chat.private"`（0x818f15）。

```
STATE_MACHINE_818DE0 = CONFIRMED  (= chat.private 私聊状态机，仅 state4 实现)
```

---

## 4. 0x803830 Transport Analysis（完整反汇编）

```asm
0x803830  mov eax,[0x8269774]      ; 全局单例
0x803837  jne 已存在
0x803839  malloc(0x1618)           ; 5656 B
0x80384C  call 0xb82130            ; 构造 transport manager（vtable 0xd599dc）
0x803851  mov [0x8269774],eax      ; 存单例
0x80385F  call 0xb7a400            ; 设置
0x803881  call 0xb7a640            ; 注册回调（vtable 0xde6814）
```

对象接口（0xb7xxxx）：`0xb7a670`(get_state, 读 [this+0x4f4] 连接对象→0xba0780)、
`0xb7a770`(get_address)、`0xb7a640`(set_callback)。

```
TRANSPORT_803830 = CONFIRMED  (= transport/connection manager 懒加载单例 getter)
```

---

## 5. Queue Payload Structure

`[this+0x3a0b0]` 队列节点：`+0x000/+0x004 载荷、+0x008 序列化数据、+0x808/+0x810 回调、+0x818/+0x81c next/prev`。

```
QUEUE_PAYLOAD_STRUCT = CONFIRMED（承 006）
```

---

## 6. Worker Analysis（★ 修正 006 归因）

worker 0x6334xx → 0x818de0，而 0x818de0 只有 chat.private 一态 ⇒
该链是**私聊消息处理**，不是 booking→battle。

```
WORKER_TO_818DE0 = CONFIRMED（chat.private）
006 把该链归为 booking = REFUTED
```

---

## 7. Endpoint Storage

transport manager 单例 [0x8269774] 内含连接对象（[this+0x4f4]），
其 sockaddr 存储于 **[this+0x538]**（0xBA4080 内 `rep movsd` 0xb0 字节拷贝）。

```
0xBA4098  lea eax,[ebx+0x5f4]
0xBA40B4  lea edi,[ebx+0x538]
0xBA40C0  rep movsd (0x2c dwords = 0xb0 B)   ; 拷贝 endpoint/sockaddr 到 this+0x538
```

```
ENDPOINT_STORAGE = CONFIRMED（sockaddr @ [连接对象+0x538]，由 0xBA4080 写入）
```

---

## 8. Endpoint Producer / Consumer

```
producer: matchmaking 响应（findSessions/createRoom）动态下发 → 解析
consumer: 连接对象 0xba97c0（endpoint 解析，含 hash 常量 0xcdea3856...）
```

```
ENDPOINT_PRODUCER = HIGH-CONFIDENCE
ENDPOINT_CONSUMER = CONFIRMED（0xba9970/0xba97c0 解析 IP:port）
```

---

## 9. IP / Port Dataflow

IP/port 以字符串 "IP:port" 进入 0xba97c0 解析成 sockaddr，存入 [this+0x538]。
IP 与 port 在同一 sockaddr 结构内（sin_addr/sin_port），未分离。

```
IP_DATAFLOW   = PARTIAL（解析链已见，来源字段未闭合）
PORT_DATAFLOW = PARTIAL（同上）
```

---

## 10. findSessions/createRoom Comparison

本阶段未重研究协议。endpoint 解析器（0xba97c0）是否被 findSessions/createRoom
复用：未闭合（模式 A/B/C 未裁决）。

```
ENDPOINT_REUSE = UNKNOWN
```

---

## 11. Socket Wrapper

connect 调用链已定位到连接对象层：

```
0xBA4080  establish/restart（拷贝 sockaddr → 0xba0760）
0xba0760  connect wrapper（push 1 → 0xba0750）
0xba0750  → 0xba05a0（实际 connect，thunk）
```

literal `socket()/connect()` WinSock 调用在 0xba05a0 内（import 名已剥离，未逐条展开）。

```
SOCKET_WRAPPER = PARTIAL（connect 链 0xBA4080→0xba0760→0xba0750→0xba05a0）
```

---

## 12. connect Path

```
（transport manager 连接层，已定位）
endpoint(IP:port 字符串) → 0xba97c0 解析 → sockaddr[this+0x538]
  → 0xBA4080 建立连接 → 0xba0760/0xba0750/0xba05a0 connect
0xBA4080 唯一调用者 = 0xb82025（transport manager 的 connect 方法，0xb81ef0 内）
```

```
BATTLE_CONNECT_PATH = PARTIAL（transport 连接层 CONFIRMED；booking 专属触发未闭合）
```

---

## 13. Candidate Port Table Analysis

0x804A82 端口序列 8300..8316/8400/8600：未发现「该表 → endpoint → connect」引用链，
维持 CANDIDATE。

```
PORT_TABLE = CANDIDATE
```

---

## 14. Evidence Classification

| 项 | 地址 | 等级 |
|---|---|---|
| 0x818de0 = chat.private 状态机 | 0x818de0/0x818f54 | CONFIRMED |
| 0x803830 = transport manager 单例 | 0x803830 | CONFIRMED |
| transport manager 构造 | 0xb82130 | CONFIRMED |
| 连接对象字段 [this+0x4f4] | 0xb7a673 | CONFIRMED |
| sockaddr 存储 [this+0x538] | 0xBA40B4/0xBA40C0 | CONFIRMED |
| endpoint 解析 | 0xba9970/0xba97c0 | CONFIRMED |
| connect 链 | 0xBA4080→0xba05a0 | CONFIRMED（到 wrapper 层）|
| 0xBA4080 调用者 | 0xb82025 | CONFIRMED |
| literal socket()/connect() | 0xba05a0 内 | UNKNOWN（import 剥离）|
| booking→battle 专属触发 | — | UNKNOWN |
| 端口候选表 | 0x804A82 | CANDIDATE |

---

## 15. Refuted Paths

```
REFUTED: worker 0x6334xx → 0x818de0 是 booking→battle（实为 chat.private）
REFUTED: 0x803830 是 socket/connect（实为 transport manager 单例 getter）
REFUTED: 0x818de0 是通用 booking 分派器（实为 6 态私聊状态机）
REFUTED: 28960 客户端硬编码（承 005/006）
```

---

## 16. Remaining UNKNOWN

```
1. 0xba05a0 内的 literal socket()/connect() WinSock 调用（import 名剥离）
2. transport manager 的 connect（0xb81ef0）连接的是 lobby 还是 battle（还是两者共用）
3. booking accepted 的专属消费者 → 是否/如何触发 transport manager connect
4. endpoint(IP:port) 字符串的来源字段（哪个 matchmaking 响应）
```

---

## 17. Final Call Graph

```
（确认）
mmbook accepted → 0x632680 → [this+0x288]=1,[0x849b61c]=1
  → vtable+0x150(0x6297A0)→vtable+0x14C(0x629730)→入队[this+0x3a0b0]
  → worker 0x6334xx → 0x818de0(chat.private) → 0x803830(transport 单例)

（transport 连接层，确认）
0x803830 单例 → 连接对象[this+0x4f4]
  → endpoint(IP:port) → 0xba97c0 解析 → sockaddr[this+0x538]
  → 0xBA4080(establish, caller 0xb82025) → 0xba0760→0xba0750→0xba05a0(connect)

（未确认）
booking accepted 专属消费者 ──?──→ transport manager connect(0xb81ef0) ──?──→ battle
```

---

## 18. Conclusion

```ini
STATE_MACHINE_818DE0 = CONFIRMED    (chat.private)
TRANSPORT_803830     = CONFIRMED    (transport manager 单例 getter)
ENDPOINT_STORAGE     = CONFIRMED    (sockaddr @ 连接对象+0x538)
ENDPOINT_SOURCE      = PARTIAL      (动态 IP:port 解析链已见，来源字段未闭合)
SOCKET_WRAPPER       = PARTIAL      (connect 链到 0xba05a0，literal WinSock 未展开)
BATTLE_CONNECT_PATH  = PARTIAL      (transport 连接层确认；booking 专属触发未闭合)
```

关键进展：connect 的 transport 后端已定位——transport manager 单例（0x803830）的
连接对象（[this+0x4f4]）通过 `0xBA4080 → 0xba0760 → 0xba05a0` 建立连接，
endpoint 经 0xba97c0 解析存入 [this+0x538]。但「booking accepted → 触发该 connect」
的专属消费者仍未定位（006 的 0x818de0 是 chat.private，已排除）。

---

## 19. Next Step

1. 下钻 0xba05a0 到 literal socket()/connect()（确认 SOCKET_WRAPPER=CONFIRMED）。
2. 确认 transport manager connect（0xb81ef0/0xb82025）是 lobby 还是 battle 连接。
3. 从 booking accepted 的 vtable+0x24 广播 receiver 与 [0x849b61c] reader
   （0x7CB1E2→0x620590、0x7CFA87→0x7cb210）追到 transport manager connect 的触发点。
4. 定位 endpoint(IP:port) 字符串在 matchmaking 响应中的来源字段。
```
