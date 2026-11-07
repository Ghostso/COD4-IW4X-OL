# -*- coding: utf-8 -*-
p = r'CODOL_SERVER_319_20261021\docs\SESSION_20261022_CLIENT_ARCH_AND_LOBBY_CHAIN.md'
part = '''
### 4.3 `0x7F2B90` = 建连接（唯一入口）

```asm
0x7F2BA8  mov ebx, [0x81A9EB8]           ; title_id = 1002
0x7F2BAF  movzx edi, word [0x81A9EC4]    ; port = 3074
0x7F2BB6  [0x84ABA60] = 6                ; 状态 -> 6（连接中）
0x7F2BCB  push 0x3E60                    ; 分配 0x3E60 = 15968 字节
0x7F2BD0  call 0xB74220                  ; operator new
0x7F2BDC  push edi                       ; port
0x7F2BDD  push 0x81A76A8                 ; "formal-zone-auth.codol.qq.com"
0x7F2BE2  push ebx                       ; title_id
0x7F2BE5  call 0xB88B80                  ; 构造 auth 连接对象
0x7F2BEA  [0x84ABB08] = eax
```

`push 1` 分支（state 5）走 lsg：

```asm
0x7F2C14  push edi / push 0x81A76A8 / push ebx
0x7F2C1D  call 0xB99090                  ; 构造 lsg 连接对象
0x7F2C26  [0x84ABB14] = eax
```

**关键：1002 和 3074 都来自 `dwauth.ini`，不是硬编码。** 改 ini 即改目标。

### 4.4 连接对象结构（`0xB88B80` 构造）

| 偏移 | 初值 | 含义 |
|---|---|---|
| `+0x00` | `0xD59A7C` | vtable（auth 版） |
| `+0x14` | 0 | **auth_task** 字段 |
| `+0x18` | `0xFFFF` | socket 句柄占位 |
| `+0x20` | 0 | 已完成标志 |
| `+0x160` | 0 | SSL/TLS 上下文指针 |
| `+0x31B0` | 0 | - |
| `+0x35F4` | 0 | SSL 对象指针 |
| `+0x35F8` | port | 端口 |
| `+0x360C` | 0x40 字节缓冲 | 主机名（拷贝自 `+0x3658`） |
| `+0x3650` | flag | 模式字节 |
| `+0x3658` | 0x400 字节 | 主机名副本 |
| `+0x3A58` | 0x400 字节 | 第二缓冲 |
| `+0x3E58` | 3 | 状态初值 |

**lsg 版**（`0xB99090`）vtable = `0xD5A1F8`，`+0x31A8 = 3`，`+0x31AC` 是 SSL 上下文。

### 4.5 auth 请求构造 `0xB9A9E0`

字段顺序（全部从 `push imm` 指令读出）：

```asm
0xB9AAAE  mov eax, [esi+0x14]      ; auth_task 当前值
0xB9AAB6  push "auth_task"
0xB9AAD5  push "iv_seed"
0xB9AAF1  push "title_id"
0xB9AB05  push "identity"          ; 常量 0xCC383C
0xB9ABC1  push "extra_data"
0xB9AC89  push "https://%s:%d/auth/"
0xB9AD1A  push "Content-Type" / "application/json"
0xB9AD34  push "X-TransactionID"
```

`auth_task` 的赋值点：

```asm
0xB99328  [esi+0x14] = 0x0A   ; 10（初始）
0xB88F41  [esi+0x14] = 0x20   ; 32
0xB9990E  [esi+0x14] = 0x0C   ; 12
```
'''
with open(p, 'a', encoding='utf-8') as f:
    f.write(part)
import os
print(os.path.getsize(p))
