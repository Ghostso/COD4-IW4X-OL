# CLIENT-BOOKING-BATTLE-TRIGGER-014
# accepted state → Battle UDP socket 的客户端触发路径（静态追踪）

> 2026-10-08 执行。纯静态。未修改任何 server/客户端/协议。未重新动态实验。

---

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

NEXT_GATE = 追 accepted branch 的 listener 广播（[esi+4] 链表 → listener->vtable+0x24）的注册源
```

---

## 1. Accepted Handler 与状态写入（CONFIRMED）

```
0x632680 accepted branch:
  [this+0x288]=1（对象态）  0x63280B
  [0x849B61C]=1（全局态）   0x632827
  vtable+0x150(0x6297A0 thunk) → vtable+0x14C(0x629730 序列化入队 [this+0x3a0b0])
  vtable+0x148(0x62C580) / vtable+0x5C(0x62FDE0)
  listener 广播: 遍历 [esi+4] 链表，逐项 call listener->vtable+0x24(1,0)
  复位 A/B(0x62f6c0)
```

---

## 2. [0x849B61C] 消费者（CONFIRMED：均为 UI，非 battle）

```
0x7CB1E2  cmp [0x849b61c],0 → 非零则 call 0x620590
0x7CFA87  cmp [0x849b61c],0 → 非零则 call 0x7CB210
```

### 2.1 0x620590 反汇编结论

```asm
0x620596  mov edx,[0xc734258]; movzx eax,[edx+8]; neg; sbb; and eax,0xdb0000
0x6205C6  call 0x76edf0        ; 处理
0x6205D5  call 0x6175c0        ; 回调（edi=0xc7341d8）
```

判定：UI/telemetry 风格（0xdb0000 掩码 + 全局回调），**无 socket/endpoint/UDP**。

### 2.2 0x7CB210 反汇编结论

```asm
0x7CB232  push 0x66
0x7CB234  mov [0x849b61c],1    ; 自身再写 1（轮询回路）
0x7CB24B  call 0x730280        ; 事件/日志（param 0x66=102）
```

判定：UI/progress 轮询回路，**非 battle trigger**。

```
0x849B61C_CONSUMERS = NOT_BATTLE_TRIGGER（CONFIRMED）
```

---

## 3. Battle 模块定位（重要发现）

DTLS / ECDH / secp224(P-224) 字符串定位：

```
"DTLS"    @ 0xd55db0..  （数据段）
"ECDH"    @ 0xd5611d..  （数据段）
"secp224" @ 0xd3d628..  （数据段，P-224 曲线）
```

字符串表（指针表）位于 **0xE3xxxx 数据段**：
```
0xE32C80（secp224 表，被 0xe34808/0xe355e8/0xe35d80 引用）
0xE37C00（DTLS 表）
```

```
BATTLE_MODULE = 0xE3xxxx（DTLS/ECDH/UDP 子系统，独立于 matching 0x62xxxx / lobby 0x7fxxxx）
```

---

## 4. 跨模块触发（关键负结果）

直接 call 扫描：

```
matching(0x62-0x63) → battle(0xE3-0xE5) : 0 处直接调用
lobby(0x7f)        → battle(0xE3-0xE5) : 0 处直接调用
```

⇒ accepted → battle 是**跨模块间接触发**（function pointer / callback / 状态轮询），
不是直接 call。这解释了为何动态实验「accepted 状态置 1 但无 UDP」——因为中间还缺
一条 callback/注册链。

```
CROSS_MODULE_DIRECT_CALL = NONE（CONFIRMED）
```

---

## 5. accepted branch 的 battle 触发候选

排除项（CONFIRMED 非 battle）：
```
[0x849B61C] → UI/progress（§2）
[this+0x3a0b0] queue → 0x818de0 chat.private（007 已证）
vtable+0x150/0x14C → 序列化入 chat 队列
0x6293B0/0x629F80 → 状态/telemetry（含 float 队列、读 [0x82e13fc]）
```

未排除项（最可能）：
```
listener 广播：0x632824..0x632844 遍历 [esi+4] 链表，call listener->vtable+0x24(1,0)
  → 该 listener 链表注册源未定位
  → 若某 listener 是 battle 子系统，则它就是 accepted→battle 的桥
```

---

## 6. GAME_IP/GAME_PORT 消费（UNRESOLVED）

session object ① Hostaddress = `ipv4_be(4B) + port_le(2B)`（codol_crypto.bd_common_addr）。
客户端解析该字段并存入某结构，accepted 后据此建 UDP socket。

```
GAME_IP/GAME_PORT 解析与存储的客户端代码 = UNRESOLVED（未定位到具体写点/消费点）
```

---

## 7. 证据分类

| 项 | 等级 |
|---|---|
| 0x632680 accepted 写 [this+0x288]/[0x849B61C] | CONFIRMED |
| [0x849B61C] reader = 0x7CB1E2/0x7CFA87 | CONFIRMED |
| 0x620590/0x7CB210 = UI/telemetry（非 battle） | CONFIRMED |
| battle 模块(DTLS/ECDH/secp224) @ 0xE3xxxx | CONFIRMED |
| matching/lobby → battle 无直接 call | CONFIRMED |
| accepted → battle 间接触发（listener/callback） | HIGH-CONFIDENCE |
| listener 注册源（谁写入 [esi+4]） | UNRESOLVED |
| GAME_IP/GAME_PORT 客户端存储/消费 | UNRESOLVED |
| UDP socket 创建（SOCK_DGRAM） | UNRESOLVED |

---

## 8. 最终状态

```ini
ACCEPTED_HANDLER      = CONFIRMED
ACCEPTED_STATE_WRITES = CONFIRMED
0x849B61C_READERS     = CONFIRMED（UI，非 battle）
BATTLE_TRIGGER_PATH   = UNRESOLVED（跨模块间接，listener 注册源未定位）
LOBBY_CONNECT_PATH_EXCLUDED = YES
NEXT_GATE = 定位 [esi+4] listener 链表的注册源，找 battle 子系统的回调注册
```

---

## 9. 下一步（缩小范围，不扩大）

1. **追 listener 注册**：在 matching 模块找「写入 [esi+4] 链表头 / 分配 listener 节点」的
   「register/addListener」方法，确认哪些对象注册了 accepted 通知回调。
2. **追 battle 模块入口**：从 0xE3xxxx 的 DTLS/ECDH 表反查使用它们的 code
   （0xe34808/0xe355e8/0xe35d80 附近），定位 UDP socket 创建（SOCK_DGRAM）。
3. **交叉**：把 (1) 的 listener 与 (2) 的 battle 模块入口对齐，证明
   `accepted → listener callback → battle UDP socket`。
4. 动态锚点仅作参考（SESSION_ID/GAME_IP:GAME_PORT/RX=0），本轮不重跑。
```
