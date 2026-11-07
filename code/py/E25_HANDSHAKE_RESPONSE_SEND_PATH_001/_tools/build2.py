# -*- coding: utf-8 -*-
from pathlib import Path
OUT=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001")
files={}

files["E25_6AA230_CALLER_CALLEE_DATAFLOW.md"]=r'''# E25 `0x6AA230` 调用者/被调者数据流

## 1. 入口与调用约定

`0x6AA230`（VA `0xAAA230`，`.text`）：

```asm
6AA230  push ebp
6AA231  mov  ebp,esp
6AA233  push -1
6AA235  push 0xB9858B          ; SEH
6AA241  sub  esp,0x1C
6AA258  mov  edi, ecx          ; this = 会话对象
...
6AA31C  ret  8
```

**约定：thiscall（ECX=this）+ 2 栈参数 + `ret 8`。返回值：无（void，`EAX` 未定义）。**

参数：
| 参数 | 含义 | 来源（`0x6AB310`） |
|---|---|---|
| `[ebp+8]` | data0 = 缓冲指针 | `0x6ABAE2 [ebx+0xC]` |
| `[ebp+0xC]` | data1 = 字节长度 | `0x6ABAED call 0xDF16878` 返回值 |

## 2. 三个被调者与作用

### 2.1 `0x0DF9AA45`（`.tvm0`）— 分配器

```asm
6AA25A  push 0x1C
6AA25C  call 0x0DF9AA45       ; 分配 0x1C 字节节点
```

### 2.2 `0x320E30`（`.text`）— 节点克隆/拷贝

```asm
6AA273  mov  ecx, [ebp+8]      ; 源缓冲
6AA276  push esi               ; arg3 = 0 (flag)
6AA277  push ebx               ; arg2 = len
6AA278  push ecx               ; arg1 = src
6AA27B  call 0x320E30
```

`0x320E30` 内部：

```asm
320E48  mov dword ptr [esi],0xCBBD24   ; node vtable
320E4E  mov dword ptr [esi+8],edi      ; len
320E61  push edi; call 0x0DF9AA45      ; 分配 len
320E6D  mov dword ptr [esi+0xC],eax    ; 缓冲
320E74  call 0xB4FF60                  ; memcpy(buf, src, len)
320E7F  mov dword ptr [esi+0x14],eax   ; 写游标
320E82  mov dword ptr [esi+0x10],eax   ; 读游标
```

### 2.3 `0x6A97E0`（`.text`）— 包装为 pair 描述符

```asm
6AA2B3  lea ecx,[ebp-0x28]
6AA2B6  call 0x6A97E0
```

`0x6A97E0` 写 vtable `0xC5B0E0`，并把 node（`[esi+8]`）、长度/偏移（`[esi+0xC]`/`[esi+0x10]`）、标志字节（`[esi+0x14]`）填入。

### 2.4 `0x0DF806F2`（`.tvm0`）— **入队（头插）**

```asm
6AA2BB  mov  eax, dword ptr [edi+0xBC]   ; 队尾/容量
6AA2C1  lea  ecx, [edi+0xB8]             ; <== 链表头
6AA2C7  lea  edx, [ebp-0x28]             ; 描述符
6AA2CA  push edx
6AA2CB  push eax
6AA2CC  mov byte ptr [ebp-4],2
6AA2D0  call 0x0DF806F2                   ; insert(&[edi+0xB8], tail, &desc)
```

### 2.5 `0x0DF37227`（`.tvm0`）— 释放描述符

```asm
6AA2DC  lea ecx,[ebp-0x28]
6AA2E3  call 0x0DF37227
```

## 3. 队列容器 `[edi+0xB8]`

| 字段 | 含义 | 证据 |
|---|---|---|
| `[edi+0xB8]` | 链表头（队首） | `0x6AA2C1 lea ecx,[edi+0xB8]`；`0x6AA8CE mov edi,[esi+0xB8]` |
| `[edi+0xBC]` | 队尾/容量 | `0x6AA2BB mov eax,[edi+0xBC]`；`0x6AA8E5 cmp edi,[esi+0xBC]` |
| `[edi+0xC0]` | 元素计数 | 构造器 `0x6AA61F` 置 0；`0x6AA961 dec dword ptr [esi+0xC0]` |
| 初始化 | 构造器 `0x6AA613/0x6AA619/0x6AA61F` 全置 0 | PROVEN（零初始化） |

## 4. 全部静态调用者

| 调用者 | 上下文 | 状态变化 |
|---|---|---|
| `0x6AA465` | 函数 `0x6AAA320`（阶段 1 建立） | 调用后 `0x6AA46E mov [edi+0x5CC],1` |
| `0x6ABAF C` | 函数 `0x6AB310`（阶段 1 应答收尾） | 调用后 `0x6ABB01 mov [edi+0x5CC],2` |

**裁定**：`0x6AA230` 是**共享的"克隆本题 + 入队"工具**，被阶段 1 的建立侧与应答侧各调用一次；它**不是**发送函数本身。

## 5. 职责定级

| 主张 | 等级 |
|---|---|
| `0x6AA230` 把 (ptr,len) 克隆成 0x1C 节点 | **PROVEN** |
| 该节点插入 `[edi+0xB8]` 链表 | **PROVEN** |
| `0x6AA230` 是发送函数 | **REFUTED**（无 send/sendto 引用；仅入队 + 驱动泵） |
| 入队后紧接驱动泵 `0x6AA7B0` | **PROVEN**（`0x6AA2D7 call 0x6AA7B0`） |
'''

files["E25_DOWNSTREAM_QUEUE_SEND_CLOSURE.md"]=r'''# E25 下游队列与发送闭合

## 1. 会话泵 `0x6AA7B0`

调用者：`0x6AA2D7`（`0x6AA230` 入队后）、`0x6AAE13`、`0x6AC109`（会话分派器）。

```asm
6AA7B0  push ebp; mov ebp,esp; push ecx
6AA7B7  mov ecx, dword ptr [esi+0x628]   ; 传输对象（可选）
6AA7BE  test ecx,ecx
6AA7C0  je  0xAAA7C8
6AA7C2  mov eax,[ecx]; mov edx,[eax]; call edx   ; 传输对象 slot0
6AA7C8  lea ecx,[esi+0x508]
6AA7CE  call 0x7832E0                    ; 时间/速率控制
6AA7D8  cmp dword ptr [esi+0xC8],1
6AA7ED  call 0x783B30                    ; 状态机推进
6AA808  mov dword ptr [esi+0xC8],2       ; 置"进行中"
6AA812  call 0x6AA4B0                    ; 副作用/清理
6AA817  cmp dword ptr [esi+0xC8],2
6AA830  cmp dword ptr [esi+0xC0],0       ; <== 队列非空？
6AA837  je  0xAAA974                     ; 空则跳出
```

## 2. 出队 + 递交（决定性）

```asm
6AA83D  mov ebx, dword ptr [esi+0xB8]    ; 取队首节点
6AA843  mov ecx, ebx
6AA845  call 0x589230                    ; -> eax = [ebx+0x10]（读游标）
6AA84A  mov edx, eax
6AA84C  call 0x77FD10                    ; -> al = [edx+0x14]（标志）
6AA855  call 0x589230
6AA85A  add eax, 0x28
6AA85D  push eax
6AA85E  lea ecx, [esi+0x508]
6AA864  call 0x783370                    ; 环形缓冲可用空间查询
6AA869  mov edx, eax
6AA86D  jle 0xAAA9A8
6AA873  sub edx, 0x28
6AA87E  push edx                         ; 长度
6AA87F  mov ecx, ebx
6AA881  call 0x6C4070                    ; -> eax = [ebx+0xC]（缓冲指针）
6AA886  push eax                         ; 缓冲指针
6AA887  lea ecx, [esi+0xC4]              ; <== 套接字持有者对象
6AA88D  call 0x783B50                    ; <== send(fd, buf, len)
6AA892  mov edi, eax
6AA896  jle 0xAAA9AD                     ; 发送失败分支
```

## 3. 发送包装器链（到 API）

```asm
783B50  push ebp; mov ebp,esp
783B53  mov eax,[ebp+0xC]      ; len
783B56  mov edx,[ebp+8]        ; buf
783B59  push eax
783B5A  mov eax,dword ptr [ecx] ; <== 套接字句柄 fd（ecx = &[session+0xC4]）
783B5C  push edx
783B5D  push eax
783B5E  call 0x784E40          ; send wrapper
783B67  ret 8
```

```asm
784E40  push ebp; mov ebp,esp; push esi
784E44  mov esi,[ebp+8]        ; fd
784E47  cmp esi,-1             ; 无效 fd 守卫
784E52  mov eax,[ebp+0x10]     ; len
784E55  mov ecx,[ebp+0xC]      ; buf
784E58  push 0                 ; flags
784E5A  push eax
784E5B  push ecx
784E5C  push esi
784E5D  call dword ptr [0xBAE4C8]   ; <== ws2_32!send(fd,buf,len,0)
784E63  mov ecx,eax
784E65  test ecx,ecx
784E67  jns 0x784EF1
784E6D  call dword ptr [0xBAE4DC]   ; WSAGetLastError
```

导入名核对（pefile）：

```text
IAT 0xBAE4C8 = ws2_32.dll!send
IAT 0xBAE4DC = wsock32.dll!WSAGetLastError
```

## 4. 套接字来源与生命周期

| 位置 | 内容 |
|---|---|
| `0xB84950` | `push 6; push 1; push 2; call [0xBAE508]` = `socket(AF_INET=2, SOCK_STREAM=1, IPPROTO_TCP=6)`；随后 `ioctlsocket(fd, FIONBIO=0x8004667E, &mode)` |
| `0x783A50` | `call 0xB84950`，把 fd 存入 `[esi]`，`cmp eax,-1; setne al`（成功标志） |
| `0x783B90` | `mov eax,[esi]; push eax; call 0x784B00` = `closesocket(fd)`；`[esi]=-1` |
| 绑定 | 会话构造器 `0x6AA6E9..0x6AA6FB` 把 `&[esi+0xC4]` 区与 `[+0x628]` 清零；`0x68A026 mov [ecx+0x4B0],eax` → `0x68A037 call 0x6A9680` 把传输对象装入 `[session+0x628]` |

## 5. 数据流闭合表

| 层级 | 地址 | 结论 | 等级 |
|---|---|---|---|
| 构造 | `0x6AB4C3..0x6ABABB`（序列化器 `0xDAB40`） | 应答字节写入 `[ebx+0xC]` | PROVEN |
| 传递 | `0x6ABAF2/0x6ABAF9/0x6ABAFC` | (buf,len) → `0x6AA230` | PROVEN |
| 队列提交 | `0x6AA2D0 call 0x0DF806F2` | 节点入 `[edi+0xB8]` | PROVEN |
| 发送包装器 | `0x6AA88D call 0x783B50` | `send(fd,buf,len)` | PROVEN |
| 网络 API | `0x784E5D call [0xBAE4C8]` | `ws2_32!send` | PROVEN |

**裁定：应答数据到达 `ws2_32!send`，五层全部闭合。** 唯一未闭合的是"发送缓冲内容与线上字节的逐字节一致性"（需 `.data` 运行时布局）。

## 6. 反证与未覆盖

- **反证**：`0x6AA230` 内**无** send/sendto 引用（会话区间 `0x6A9000..0x6AD000` 内亦无），故"`0x6AA230` 即发送函数"被否。
- **未覆盖**：`0x783B50` 的另一调用者 `0x6A9B6E`（`0x6A9B20`，阶段 3 的空闲发送）与 `0x6B3343`（另一会话类型）未展开。
- **未覆盖**：`[esi+0x628]` 传输对象的 `slot0` 真实目标为运行时决定。
'''

files["E25_STATE_AND_OPCODE_CROSSWALK.md"]=r'''# E25 状态与消息码交叉表

## 1. 状态字段

| 字段 | 含义（据 E-24 与实测） | 写点 |
|---|---|---|
| `[+0xC8]` | 连接状态（1/2/4） | `0x6AA808`（=2）、`0x6AA791`（=4）、`0x6AA644`（=0 初始化） |
| `[+0x5CC]` | 握手阶段（0/1/2/3） | `0x6A1310`、`0x6A13F0`、`0x6A154F`、`0x6AA46E`(1)、`0x6ABB01`(2)、`0x6AB2ED`(3) |
| `[+0xB8]` | 出站队列头 | `0x6AA613`（0）、`0x6AA2D0`（入队）、`0x6AA8DF`（出队） |
| `[+0xC0]` | 出站队列计数 | `0x6AA61F`（0）、`0x6AA961`（dec） |

## 2. 状态改变与数据组装的时序

### 路径 A：`0x6AAA320`（阶段 1 建立）

```text
构造 0x1C + 缓冲 (0x6AA320)
  → 填 0xC8 字段 (0x6AA3C9)
  → 0x6AA465 call 0x6AA230（入队）
  → 0x6AA46E mov [edi+0x5CC], 1      ; ← 状态在入队【之后】
```

### 路径 B：`0x6AB310`（阶段 1 应答）

```text
解析 → 组装应答（序列化器 0xDAB40）→ 0x6ABABA 成功标志
  → 0x6AB97A call 0xA87BA0（构造 [+0x5F0]）
  → 0x6AB9DA call 0xA87BA0（构造 [+0x5F4]）
  → 0x6ABAFC call 0x6AA230（入队应答）
  → 0x6ABB01 mov [edi+0x5CC], 2      ; ← 状态在入队【之后】
```

**裁定**：
- **数据组装在前，状态推进在后**（两条路径均如此）。
- **入队发生在写 `[+0x5CC]` 之前**（PROVEN）。
- 发送（泵内 `0x6AA88D`）发生在状态推进之后的下一次泵驱动（PROVEN 控制流）。

## 3. 成功/失败分支

| 位置 | 分支 | 结果 |
|---|---|---|
| `0x6ABA00 test al,al; je 0xAABA08` | `[+0x5F4]` 对象 slot+1 失败 | 清成功标志 |
| `0x6ABAC0/0x6ABACB` | 应答组装成功/失败 | `[ebp-0x172]` = 1/0 |
| `0x6ABAE0 je 0xAABB0D` | 未成功 | 日志 `0x43A7C0` → `0x6AAA770`（置 `[+0xC8]=4`） |
| `0x6AA896 jle 0xAAA9AD` | `0x783B50` 发送返回 ≤0 | 转入错误码表 `0xAAA9DC` |
| `0x6AA907` | 泵内错误 | `0x6AAA770` + 返回 false |

## 4. 重试 / 缓存 / 异步

| 机制 | 证据 | 结论 |
|---|---|---|
| 异步队列 | `[+0xB8]` 侵入式链表 + `[+0xC0]` 计数 | **存在**（PROVEN） |
| 重试 | 泵在 `0x6AA967 cmp [esi+0xC8],2; je 0xAAA830` 循环继续处理队列 | **存在**（循环消费，非显式重试计数） |
| 缓存 | `[+0x508]` 环形缓冲（`0x783370`/`0x783390` 查询/扣除） | **存在**（PROVEN） |
| 异步回调 | 未发现与队列相关的回调注册 | BLOCKED |

## 5. 消息码与应答的关系

| 码 | 与应答的关系 | 类型 | 等级 |
|---|---|---|---|
| `0x81` | 触发生成应答；其字节经 `0x6AA230` → `[+0xB8]` → `ws2_32!send` | **数据流 + 控制流** | 控制流 PROVEN；数据流 PROVEN（同一缓冲链路） |
| `0x83` | 走 `0x6AB260`（阶段 2），在 `0x6AB2ED` 写阶段 3 与 `[+0x5D0]`；**不经过本应答序列化器** | 控制流 | PROVEN |
| `0x84` | 走 `0x6A9690`，返回后无条件 `0x6AAA770`（置 `[+0xC8]=4`） | 控制流 | PROVEN |
| `0x85` | 走 `0x6AAE70`（HMAC/计数器）；成功路径调 `[+0x5F4]` slot+3 | 控制流 + 数据流 | PROVEN |

## 6. 反例与禁止推断

- **反例**：`0x6AA230` **不是**发送函数；同一 `[+0xB8]` 队列也服务于 `0x6AAA320`（阶段 1 建立）——故"队列 = 应答专用"不成立。
- **禁止**：不得把 `[+0x5CC]` 的数值 1/2/3 直接命名为"挑战/应答/确认"等协议阶段；本轮仅证明其读写序列与消息码分派的对应关系。
- **禁止**：不得把"数据到达 `send`"表述为"协议互通已验证"——实时互操作仍为 NOT-OBSERVED。
'''

for name,content in files.items():
    (OUT/name).write_text(content,encoding="utf-8")
    print("wrote",name,len(content))
