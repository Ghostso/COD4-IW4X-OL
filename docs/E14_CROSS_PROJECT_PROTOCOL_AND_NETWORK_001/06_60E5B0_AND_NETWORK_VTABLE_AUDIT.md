# 06 — `0x60E5B0` 与网络虚表审计

> 等级：`PROVEN` / `INFERRED` / `BLOCKED` / `REFUTED`

---

## 1. 决定性更正：`0x60E5B0` 不是协议状态机

E-13 曾把 `0x60E5B0` 登记为"协议状态机候选"（含 20+ 函数指针调用）。**本轮推翻该假设。**

**证据（DIRECT）：**

```asm
60E5B0  push ebp / mov ebp,esp / sub esp,0xF60
60E5C3  mov eax,[ebp+0xc]              ; 参数 2 = putc 回调
60E5C8  mov esi,[ebp+0x10]             ; 参数 3 = format 字符串
60E5CC  mov edi,[ebp+8]                ; 参数 1 = 回调上下文
60E5CF  mov [ebp-0xd2c],eax            ; 保存回调
60E5E9  mov eax,esi
60E5EB  mov [ebp-0xd30],edi
60E5F1  mov [ebp-0xd48],0xC38A5C       ; 格式标志表
60E607  call 0xA0DE50                  ; 解析格式串
60E623  mov al,[esi]
60E625  cmp al,0x25                    ; '='%' 字符
60E627  je  0xA0E663                   ; 转换符分支
60E633  push edi / push ecx
60E635  call dword ptr [ebp-0xd2c]     ; ← putc 回调
60E63E  cmp eax,-1
...
60E735  cmp eax,6
60E738  ja  0xA0EF31
60E73E  jmp dword ptr [eax*4+0xA0EF84] ; 7 项转换符跳转表
```

**语义（PROVEN）：**

| 元素 | 含义 |
|---|---|
| `[ebp+8]` | 输出上下文（流/缓冲结构） |
| `[ebp+0xc]` | **putc 回调函数指针** |
| `[ebp+0x10]` | format 字符串 |
| `[ebp+0x14]` | va_list |
| `0x25` 比较 | `'%'` 格式引入符 |
| `[eax*4+0xA0EF84]` | 7 项转换符表（s/c/d/pn/n/x 类） |
| 20+ `call [ebp-0xd2c]` | 逐字符输出 |

**裁定：`0x60E5B0` 是 `_vsnprintf` 风格的格式化器。REFUTED（"协议状态机"）。**

## 2. `0x60E5B0` 的调用链（DIRECT）

| 调用点 | 调用者 | 说明 |
|---|---|---|
| `0x60E4CA` | `0x60E4A0` | 包装器（`0x60E4A0` 传 `0x60E470` 作回调） |
| `0x60EFC6` | `0x60E5B0`（递归） | 内部递归 |
| `0x60F046` | `0x60F020` | |
| `0x60F0B4` | `0x60F0A0` | |

`0x60E470`（回调）实现：

```asm
60E470  mov eax,[ebp+0xc]      ; 上下文
60E476  mov ecx,[eax+4]        ; 已写长度
60E479  cmp ecx,[eax+8]        ; 对比容量
60E47C  jae 0xA0E48F           ; 溢出 → -1
60E480  mov cl,[ebp+8]         ; 字符
60E483  mov [edx],cl           ; 写入
60E485  inc [eax] / inc [eax+4]
```

→ **典型 snprintf 写入回调。**

## 3. E-13 的 9 收包函数 → `0x60E5B0` 路径的真实性质

E-13 的路径 `0x6029A0 → 0x602760 → 0x60E5B0`：

```asm
6029A0  ...  call [0xbae490]            ; recv
6029CF  cmp edi,-1
6029D4  call [0xbae4dc]                 ; WSAGetLastError
6029F3  call 0xA0FB00                   ; 错误码 → 字符串
6029FB  push 0xC37244                   ; "Recv failure: %s"
602A01  call 0xA02760                   ; → 0x60E5B0 格式化
602A0B  mov [ecx+0x85F4],edx            ; 记录错误码
602A14  mov [ebx],0x38                  ; 错误字
```

**结论（PROVEN）：** `0x6029A0` → `0x60E5B0` 是 **错误日志格式化路径**，不是协议解析。收包返回值 `-1` 时才进入。

**这解释了 E-13 的"20+ 函数指针"假象：** 它们是 snprintf 的逐字符输出回调，不是协议处理器注册表。

## 4. 网络虚表 `0x898588` / `0x898590`

| 项 | 值 | 证据 |
|---|---|---|
| 表位置 | `.rdata` `0x898580`–`0x898600` | 原始 dump |
| `0x898588` 内容 | `0xb75a50` `0xb75a80` `0xb75ab0` … | DIRECT |
| `0x898590` 内容 | `0xb75ab0` `0xb75af0` `0xb75b30` … | DIRECT |
| `0x775A50`（recv） | 直接数据指针 `.rdata@0x898588` | DIRECT |
| `0x775AB0`（recvfrom） | 直接数据指针 `.rdata@0x898590` | DIRECT |

**性质（INFERRED）：** 相邻槽位 + 同类 `recv`/`recvfrom` 语义 → **平台 socket 抽象虚表**。

**构造者定位：BLOCKED。** 本轮未定位写入该虚表指针的构造函数（需回溯对象实例化路径）。

## 5. 裁定

| 项 | 裁定 |
|---|---|
| `0x60E5B0` 是协议状态机 | **REFUTED** |
| `0x60E5B0` 是 vsnprintf 格式化器 | **PROVEN** |
| `0x6029A0` → `0x60E5B0` 是错误日志路径 | **PROVEN** |
| `[ebp-0xd2c]` 是 putc 回调 | **PROVEN** |
| 虚表 `0x898588/0x898590` 是 socket 抽象 | **INFERRED** |
| 虚表构造者 | **BLOCKED** |
