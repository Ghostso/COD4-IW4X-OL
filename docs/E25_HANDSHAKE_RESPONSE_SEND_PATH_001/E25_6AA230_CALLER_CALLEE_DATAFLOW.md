# E25 `0x6AA230` 调用者/被调者数据流

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
| `0x6ABAFC` | 函数 `0x6AB310`（阶段 1 应答收尾） | 调用后 `0x6ABB01 mov [edi+0x5CC],2` |

**裁定**：`0x6AA230` 是**共享的"克隆本题 + 入队"工具**，被阶段 1 的建立侧与应答侧各调用一次；它**不是**发送函数本身。

## 5. 职责定级

| 主张 | 等级 |
|---|---|
| `0x6AA230` 把 (ptr,len) 克隆成 0x1C 节点 | **PROVEN** |
| 该节点插入 `[edi+0xB8]` 链表 | **PROVEN** |
| `0x6AA230` 是发送函数 | **REFUTED**（无 send/sendto 引用；仅入队 + 驱动泵） |
| 入队后紧接驱动泵 `0x6AA7B0` | **PROVEN**（`0x6AA2D7 call 0x6AA7B0`） |
