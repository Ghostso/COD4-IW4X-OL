# E17 — 接收缓冲区数据流 / BUFFER DATAFLOW

> 等级：PROVEN / INFERRED / BLOCKED / REFUTED

---

## 1. `0x6B4DE0` 的缓冲区数据流（PROVEN）

```
调用者 (0x783F00)
  ├─ 分配/传入: [ebp+8]=sock, [ebp+0xc]=&addr_out, [ebp+0x10]=&port_out,
  │             [ebp+0x14]=len, [ebp+0x18]=flags
  └─ 调用者自身持有接收缓冲？
        └─ 0x783F5E call 0x6B4DE0
              └─ 0x6B4E3C recvfrom(sock, buf, len, flags, &from, &fromlen)
                    └─ 返回 esi = 实际长度
                          ├─ 成功: ntohs(port) -> [edi] ; [ebx]=port
                          │        [0xD47388/0xD4738C] += 字节统计
                          │        [0xD47398/0xD4739C] += 1
                          └─ 返回 eax = esi
```

**关键（PROVEN）：**
- 接收缓冲区**不在本函数内**——由 `0x783F00` 在栈上准备（`lea eax,[ebp-0x118]` 等）后传入。
- 本函数**不复制、不排队、不缓存**收到的数据。
- 唯一的"旁路写入"是 **socket 统计计数器**。

## 2. `0x783F00` 的缓冲区（PROVEN）

    783F36  lea ecx,[ebp-0x118]      ; 接收缓冲（栈，0x118 字节区）
    783F42  call 0xAB4800            ; 初始化（sockaddr 结构）
    783F56  lea eax,[ebp-0x118]
    783F5E  call 0xAB4DE0            ; -> recvfrom 封装
    783F71  sub esp,0x84
    783F84  rep movsd                ; 0x21 dwords = 0x84 字节复制
    783F86  lea ecx,[ebp-0x94]
    783F8C  call 0xA86220            ; 构造对象
    783F9D  push edx / push eax / call 0xA84CE0   ; 交付
```

**结论（PROVEN）：** 数据被复制 0x84 字节到栈上临时区，再交给 `0xA84CE0`。这是一次**定长交付**（0x84 = 132 字节），不是变长消息分帧。

## 3. `0x784F60` 的缓冲区数据流（PROVEN）

    783B73  mov eax,[ebp+0xc]        ; len
    783B76  mov edx,[ebp+8]          ; buf
    783B7A  mov eax,[ecx]            ; sock（对象字段 [ecx]）
    783B7E  call 0xB84F60            ; -> recv 封装
    783B86  ret 8

`0x783B70` 是**极薄转发**（11 条指令）：`recv(obj->sock, buf, len, 0)`，缓冲区完全由调用者提供。

## 4. 是否写入环形缓冲/队列/TLS 结构

| 候选 | 环形缓冲 (0x3524F0) | 队列 | TLS 结构 | 全局统计 |
|---|---|---|---|---|
| 0x6B4DE0 | **否** | 否 | 否 | **是**（0xD47388/0xD47398） |
| 0x784F60 | **否** | 否 | 否 | **是**（0xD47370/0xD47374） |

**裁定（PROVEN）：两候选均不写入环形缓冲、不排队。**

## 5. 统计全局的消费者（PROVEN）

| 全局 | 写入者 | 读取者 |
|---|---|---|
| 0xD47388 / 0xD4738C | 0x6B4DE0（0x6B4F25/0x6B4F2E） | （累计统计，未见 UI 读取点） |
| 0xD47398 / 0xD4739C | 0x6B4DE0（0x6B4F34/0x6B4F3D） | 同上 |
| 0xD47370 / 0xD47374 | 0x784F60（0x784FC9/0x784FD0/0x784FE3/0x784FE9） | **0x6B4920**（0x6B4960/0x6B4970） |
| 0xD47370 | 0x784E40（0x784EA4/0x784EC4） | 0x6B4920 |

**0x6B4920 是 socket 错误/状态查询函数**（读取 0xD47370 错误码与 0xD47374 状态码）。这是**诊断接口**，不是消息消费者。

## 6. 裁定

| 项 | 裁定 |
|---|---|
| 缓冲区来源 | PROVEN（调用者提供） |
| 是否复制/排队 | PROVEN（不复制/不排队） |
| 是否写环形缓冲 | REFUTED |
| 旁路写入 | PROVEN（socket 统计/状态全局） |
| 下游消费者 | PROVEN（统计查询 0x6B4920，非消息消费者） |
