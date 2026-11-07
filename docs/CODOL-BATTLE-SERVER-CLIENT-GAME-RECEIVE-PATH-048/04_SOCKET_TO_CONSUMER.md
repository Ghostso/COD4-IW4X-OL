# 04 — 正向网络数据流:recv/recvfrom → 缓冲区 → 解析 → 分派 → 消费者

方法:枚举**所有** socket API IAT 调用点(RVA 0xCA84xx..0xCA86xx 的 `FF 15`),按函数归组,
再逐条做正向数据流(从 `recv` 的参数与返回值出发)。

---

## 1. 全部 socket 接收相关调用点(实测)

| API | 调用点 RVA | 所在函数 | 直接调用者 |
|---|---|---|---|
| recv | 0x6D3DF1 | 0x6D3DE0 | 0x6EC781 |
| recv | 0x6D437E | 0x6D4360 | (无) |
| recv | 0x6D6C6B | 0x6D6C57 | 0x6D6B52 |
| recv | 0x85D2CA | 0x85D2CA(TQOS) | 0x867B62 |
| **recv** | **0x8655CC** | **0x8655B0(P4)** | **(无)** |
| **recv** | **0x876EED** | **0x876ED0(P5)** | **0x873A0E** |
| recv | 0x87BEC3 | 0x87BE00(TQOS) | 0x87BA50(jmp) |
| recvfrom | 0x7B163C | 0x7B15E0 | **0x87401E(P5)** |
| recvfrom | 0x86563E | 0x865610(P4) | (无) |
| select | 0x6CBC58, 0x6CC022 | libcurl | (间接) |
| select | 0x85D941, 0x85EAE7 | TQOS | 内部 |
| select | 0x8654F4 | 0x8654A0(P4) | (无) |
| select | 0x876AFF, 0x876BB7 | 0x876AB0 / 0x876B40(P5) | 1 / 2 |
| select | 0x87BBDD, 0x87BD40, 0x87BE84 | TQOS | 内部 |

---

## 2. 正向链 #1:P5 `recv`(目前**最后一个已证实节点**最远的一条)

### 2.1 节点 A — `recv` 包装函数 `0x876ED0`

```
876ED0  push ebp; mov ebp,esp; push edi
876ED4  mov edi,[ebp+8]          ; edi = socket
876ED7  cmp edi,-1 ; je ret(-9)  ; 无效 socket 短路
876EE2  mov eax,[ebp+0x10]       ; arg4 = flags (=0)
876EE5  mov ecx,[ebp+0x0c]       ; arg3 = len
876EE8  push 0                   ; flags
876EEA  push eax
876EEB  push ecx                 ; len
876EEC  push edi                 ; socket
876EED  call [0x00CA84E4]        ; **recv(socket, buf, len, 0)**
876EF3  mov ecx,eax
876EF5  test ecx,ecx ; jns OK
876EFE  call [0x00CA853C]        ; WSASetLastError
...     (错误码映射表 0xC76FB0)
876F9E  OK: 累加统计; 返回收到字节数
```

- 缓冲区指针 = `[ebp+0x0c]`(参数 2),长度 = `[ebp+0x10]`(参数 3)。
- **结论:函数确实把调用方提供的缓冲区直接交给 `recv`。**`DIRECT_STATIC`。

### 2.2 节点 B — 调用者 `0x873A00`

```
873A00  push ebp; mov ebp,esp
873A03  mov eax,[ebp+0x0c]       ; len
873A06  mov edx,[ebp+0x08]       ; buf
873A09  push eax
873A0A  mov eax,[ecx]            ; socket = this->sock
873A0C  push edx
873A0D  push eax
873A0E  call 0x876ED0            ; recv wrapper(sock, buf, len)
873A13  add esp,0x0c; ret 8
```

- `ecx` = 对象指针,对象首字段 `[ecx]` = socket。这是 `CTcpClient::Recv(buf,len)` 形态。
- **同族**还有 `0x8739E0`(`send` 包装)、`0x873A20`(`close`)、`0x8739C0`。

### 2.3 节点 C — `0x873A00` 的上游(**在此断点**)

`0x873A00` 直接调用者:`0x7A20D9, 0x7A3FD6, 0x7A42DA, 0x7B001C`。

继续上溯:

| 层 | 函数 | 调用者 |
|---|---|---|
| 1 | `0x7A20A0..0x7A22A0` | `0x7A42B9` |
| 2 | `0x7A41D0..0x7A460B` | `0x7A4491` |
| 3 | `0x7A41D0`(自环) | — |

- `0x7A41D0` 是**独立线程/会话循环**(含 `WaitForSingleObject` 风格间接调用),其上溯
  在当前可读映像中**收敛为环**,再往上没有调用者。
- **断点:此循环的启动者(线程创建/对象注册)不在已检查范围内。**
- 不排除:该启动者位于第 3 节不可读区(0xA16000 之后),或以函数指针注册到 vtable。

### 2.4 节点 D — 缓冲区是否进入游戏解析?

`0x873A00` 把 `recv` 的返回值返回给调用者;调用者 `0x7A20A0`/`0x7A41D0` 内部继续处理。
本轮对 `0x7A20A0..0x7A22A0`、`0x7A41D0..0x7A460B` 做了字符串与调用目标扫描:
- 未发现与 `gamestateupdate`/`CA_GAMESTATE`/`configstring`/`snapshot` 任何锚点相连的调用边;
- **不能**因此断定它不处理游戏数据(见 §6 与 `05` §6 的口径限制)。

## 3. 正向链 #2:P5 `recvfrom` → 连接无关解析器

```
874000  ...(0x873FC0 体内,异常帧 SEH)
87401E  call 0x7B15E0            ; recvfrom wrapper
7B15E0  ...call [0x00CA851C]     ; **recvfrom**
```

- `0x873FC0` 是 P5 对象的 `recvfrom` 方法(边界 `0x873FC0..0x8740A0`)。
- `0x873FC0` 的直接调用者:**0**(与 P4 类似),且无裸 dword 指针引用。
- 但是:`0x7B15E0` 的 `recvfrom` 恰是连接无关层可能用到的原语(握手/OOB 通常走
  `recvfrom` + 未连接 socket)。
- **未证实:** 没有指令级证据把 `0x873FC0` 的缓冲区连到 `0x1C1EE0`。

## 4. 正向链 #3:连接无关泵 `0x0F8FB0`(消费者明确,生产者不明)

```
0F8FB0  泵循环入口
0F9060  loop:
0F906E  lea ecx,[ebp-0x20098]
0F9075  call 0x621E50            ; 取下一个已入队报文
0F9085  ... 组装 msg_t (data/maxsize/readcount/datalen)
0F90B5  ... 若未初始化: call 0xCA84C8(?) ; 时间源
0F9135  call 0x1C1EE0            ; **连接无关解析器**
```

- **已证实:`0x0F8FB0` 的报文 → `0x1C1EE0` 解析 → `0x1C13A0` 分派 → 各命令 handler。**
- **未证实:`0x621E50` 所读队列的写入者(`0x0F8C50`/`0x0F8CF0`/`0x0F8D70`)之上,
  哪个函数从 socket 收到字节并 `enqueue`。** 这三者体内没有 socket 调用。

`0x0F8C50` 体内:

```
0F8C5C  mov edi,[0xCA84C8]        ; 时间源函数指针
0F8C63  push 0; push ebx; call 0x66EFD0   ; 从 msg 取 token/数据
0F8C7D  call edi                  ; 更新时间
0F8CD6  call 0x5C2260             ; -> 0x1C1EE0 解析(经 0x1C22ED)
```

## 5. 其它 recv 调用点(排除)

| 函数 | 归属 | 依据 |
|---|---|---|
| 0x6D3DE0 / 0x6D4360 / 0x6D6BE0 | 第三方网络库 | 同段有 `recvfrom/ioctlsocket/WSASetLastError` 通用封装;无游戏串 |
| 0x85D2CA / 0x87BE00 | TQOS/QoS | 046 已定;函数体内仅平台逻辑 |
| 0x8655B0 / 0x865610 | P4 | 无调用者;见 `02` §3 |

## 6. 最后一个已证实节点 / 第一个未证实节点

| 候选链 | 最后已证实节点 | 第一个未证实节点 |
|---|---|---|
| P5 客户端 recv | `recv(sock,buf,len)` @ 0x876EED,缓冲区=参数 | `0x7A41D0` 循环的启动者(谁提供 socket + 何时收) |
| 连接无关 recvfrom | `recvfrom` @ 0x7B163C | `0x873FC0` 的调用者(0 个直接) |
| 连接无关泵 → 解析 | 报文 → `0x1C1EE0` → `0x1C13A0` → handler | 队列的 socket 生产者 |
| 游戏状态消费者 | 锚点字符串与其宿主函数 | 「读包缓冲 → 锚点宿主」的数据流边 |

## 7. 闭环判据(B4)逐条核对

| # | 判据 | 状态 |
|---|---|---|
| 1 | 输入来自游戏网络接收(非 TQOS/HTTP/日志) | **部分**:P5 `recv` 已证;但未见游戏串 |
| 2 | 接收缓冲区进入解析逻辑 | **未证**:P5 缓冲进入 `0x7A41D0`,其上断开 |
| 3 | 解析结果流入游戏消息分派/状态消费者 | **未证**:无 opcode 表;OOB 仅有握手分派 |
| 4 | 关键连接有直接指令/数据流/xref 证据 | **握手层:是**;**in-match:否** |
| 5 | 已记录主要替代解释 | ✅ `05` §5 |

**总结论:游戏网络「接收 → 解析 → 分派 → 状态消费者」链未闭环。**
连接无关(握手)子链已闭环到客户端命令 handler;in-match 主链在
`0x7A41D0`(P5 消费循环)之上断开。
