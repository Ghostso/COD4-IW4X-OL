# 07 — 房间下行事件分派

> 对应任务书 §四 D。核心要求：**不得把"消息已发送"视为"客户端已处理"**。

---

## 1. 全部已知房间下行事件

服务端当前会发的下行（实测 + 源码）：

| # | 事件 | 协议 | 字节 | 触发 | 证据等级 |
|---|---|---|---|---|---|
| 1 | `mmbook accepted` | 6/14 push | 20 | 收到 mmbook | L（日志） |
| 2 | `11/4` 频道回显 | 11/4 → 频道 | 与上行同 | 收到 11/4 | L |
| 3 | `Ready` (type 0x01) | 房间 push | ~6 | `ready_push.on` + 收到 16 B 批次 | L（日志"发 Ready"） |
| 4 | `RoomStateUpdated` (countdown) | 房间 push | — | 同上 | L |
| 5 | `dwRoomMessageStartGame` (109 B) | 6/14 push | 109 | 10-28 起在 mmstart 后 | L |
| 6 | 自造 room push ×3 | 房间 push | 106/130/54 等 | createRoom 后 | L |
| 7 | `RoomInfo` (type 0x0F) | 房间 push | 位流 | 早期 kit | L（编码存在） |

**客户端订阅了 20 个 MM 事件（6/5），服务端只发过上面 3–7 里的少数几条。**

---

## 2. 消息封装（已有字节证据的部分）

### 2.1 L1 外层信封（`instant_push_body(kind=11)`）

```
08 0b 00 00 00         kind = 11
0a <u64 senderId>
10 "Player\0"
13 08 <u32 payloadLen>
```
与客户端自己的发送缓冲区**共同前缀 23 字节**（`ROOM_PROTOCOL_COMPLETE §二`）。

### 2.2 L2（上行 vs 下行不同 —— 已定案）

| 方向 | 结构 | 证据 |
|---|---|---|
| **上行** | `0a <roomId> \| 13 08 <len> \| <u32 len-4> \| <body> \| 08 <1>` | 209 条样本，`declared==len-4` 100% |
| **下行** | 无 `<u32 len-4>` 前缀；body 直接是位流 | `0x637000` 用 `(ptr, len*8)` 建流 |

### 2.3 位流编码（2026-10-29 转储独立复核）

`0x637000`（房间信道消息处理）：

```asm
00637019  mov  ecx, [ebp+0x24]      ; 长度参数
0063701C  lea  edx, [ecx*8]         ; ★ nbits = 字节数*8
00637023  mov  ecx, [ebp+0x20]      ; buf
0063702C  call 0xB779A0             ; 构造位流
00637048  push 3
0063704C  call 0xB774E0             ; readBits(3)
00637055  push 8
0063705D  call 0xB772E0             ; readData(8) = type
0063706E  cmp  eax, 1               ; type==1 分支
```

⇒ **这是"下行是位流"的独立复现**（此前只有 10-28 的结论）。

---

## 3. 事件编号与分派

### 3.1 分发表

`0x636f3c`，**47 项（type 0x00–0x2E）**，41 个有效 handler。

| type | handler | 语义 | 证据 |
|---|---|---|---|
| `0x02` | `0x63495A` → `0x625940` → vtable `0x00DC7504` | **`dwRoomMessageText`（聊天）** | 反汇编 |
| `0x0F` | `0x635968` | `RoomInfo`（有闸门 `[ebx+0x278]` + roomId 双校验） | 反汇编 |
| 其余 39 | — | **未逐一命名** | — |

**⚠️ 已知的 41 个 handler 里，只有 2 个能确定语义。**

### 3.2 客户端上行里出现过的 type

87 条上行样本，**首字节只有两种**：`0x02`（53 次）、`0x18`（34 次）。

⇒ 客户端"自己发"的只有这两类；**其余 39 个 type 是服务端该推的**。

---

## 4. 哪些事件会更新 UI / 触发下一次请求

| 事件 | 会更新 UI？ | 会触发下一请求？ | 证据 |
|---|---|---|---|
| `mmbook accepted` | 否 | **是**（随后发 mmstart） | L：全部 mmbook run 后都有 mmstart |
| `11/4` 回显 | 否（回声） | 否 | L |
| `Ready` / `RoomStateUpdated` | **UNKNOWN** | UNKNOWN | 未证明被解析 |
| `dwRoomMessageStartGame` | **UNKNOWN** | **否**（10-28/10-29 推了但无后续请求） | L：推后无新上行 |
| 自造 room push ×3 | **UNKNOWN** | 否 | L |

**唯一被证明"能触发下一次请求"的下行只有 `mmbook accepted`。**

---

## 5. 为什么这条链没闭合

三条独立原因，都未排除：

**H1 信封路由键不对**
- 房间信道路由键 = `roomId` 高低 32 位（`0x7E7C90` 表项 `+0x10/+0x14`）。
- 我们三种信封构造都不满足 `obj+8 == roomId_lo` / `obj+0xc == roomId_hi`。

**H2 客户端根本不解析**
- 从未做过"畸形对照"：把推送字段截断，看客户端行为是否变化。
- 没有这个对照，**所有格式微调都是盲调**。

**H3 内容不足**
- 即使格式对，缺客户端从没发过的字段（如成员列表、房主标志）。

---

## 6. 结论

| 问题 | 答案 |
|---|---|
| 消息封装 | L1 = `instant_push_body(kind=11)`（已验证共同前缀 23 B） |
| 位流编码 | 下行是位流，`readBits(3)` + `readData(8)`（2026-10-29 独立复核） |
| 事件编号 | 分发表 47 项；**仅 2 个语义确定**（0x02=Text、0x0F=RoomInfo） |
| 分派函数 | `0x637000`（建流）→ `0x634870`（按 type 分派） |
| 哪些更新 UI | **UNKNOWN** |
| 哪些触发下一请求 | 仅 `mmbook accepted` 被证明 |

**本专项的核心未知**：39 个未命名 type 中哪一个对应 `RoomInfo`/`Ready`/`RoomStateUpdated`/`StartGame`，
以及信封里 roomId 的确切字节位置。
