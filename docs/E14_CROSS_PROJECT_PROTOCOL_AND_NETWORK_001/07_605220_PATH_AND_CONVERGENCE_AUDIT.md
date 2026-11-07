# 07 — `0x605220` 路径与汇合审计

> 等级：`PROVEN` / `INFERRED` / `BLOCKED` / `REFUTED`

---

## 1. `0x605220` 逐指令（DIRECT）

```asm
605220  push ebp / mov ebp,esp / sub esp,8
605228  mov edi,[ebp+8]
60522B  mov esi,[edi+0x5b8]           ; SSL 连接对象
605231  test esi,esi / je 0xA0526B
605235  mov eax,[edi+0x44]
60523A  test eax,eax / je 0xA0526B
60523C  push 0xA05200                 ; 比较回调
605244  mov [ebp-8],esi
60524E  mov edx,[eax+0x34]
605253  call 0xA06650                 ; 超时/可读检查
60525B  cmp [ebp-4],0 / jne 0xA05274
605261  mov dword [edi+0x5b8],0       ; 清除
60526B  or eax,-1                      ; 返回 -1
605274  mov eax,[ebp+0xc] / mov [eax],esi
60527D  cmp dword [esi+0x17c],0
60528D  call 0x9FB510                 ; ← SSL_pending 类
605295  test eax,eax / jne 0xA052B5
6052A2  push 2 / push 1 / lea eax,[ebp+0xb]
6052AB  call [0xbae490]               ; recv（2 字节 peek）
```

## 2. `0x5FB510` → `0x6104D0` → `0x672460`（DIRECT）

```asm
5FB510  ... jmp 0x6104D0
6104D0  mov ecx,[ebp+8]
6104D6  mov edx,[ecx+0x188]
6104DC  push 1 / lea eax,[ebp+0xb] / push eax / push edx
6104E3  call 0x672460
6104EB  test eax,eax
6104ED  jle 0xA104F6
6104EF  mov eax,1 / ret
```

```asm
672460  mov eax,[esp+4]
672464  cmp dword [eax+0x20],0         ; OpenSSL 对象状态
672468  jne 0xA7248C
67246A  push 0x38B / push 0xC5650C     ; 源文件/行号
672474  push 0x114 / push 0x10E / push 0x14
672480  call 0xA27F20                  ; 错误报告
672488  or eax,-1 / ret
67248C  test byte [eax+0x30],2 / je 0xA72495
672492  xor eax,eax / ret
672495  mov ecx,[eax+8]
67249C  mov eax,[ecx+0x1c]
67249F  jmp eax                        ; ← 对象方法虚分派
```

**证据：** `0xC5650C` 是 OpenSSL 源文件路径字符串；`0xC3D0D2` 等 5 处含 `"OpenSSL 0.9.8p 16 Nov 2010"`。

**判读（PROVEN）：** `0x672460` 是 **OpenSSL 对象方法分派**（读 `[obj+8]` → `[+0x1c]` → `jmp`），`0x6104D0`/`0x5FB510` 是其封装，`0x605220` 是 **TLS 读路径**。

## 3. 与 `0x6029A0` 路径的汇合审计

| 检查 | 结果 |
|---|---|
| `0x605220` 6 层闭包大小 | **7** 个函数 |
| `0x6029A0` 6 层闭包大小 | **39** 个函数 |
| **共享下游** | **0** |

**裁定（REFUTED）：** 两条路径在 6 层内**无共享下游**，**不存在可证汇合**。

**注意：** 两者都调用 `recv`（同一 IAT `0xBae490`），但这是**共享底层 socket API**，不是汇合点（按任务要求：仅访问相同全局/API 不足以证明路径相同）。

## 4. 两条路径的性质对比

| 项 | `0x6029A0` 路径 | `0x605220` 路径 |
|---|---|---|
| 下游规模 | 39 | 7 |
| 关键下游 | `0x602760` → `0x60E5B0`（**printf**） | `0x5FB510` → `0x6104D0` → `0x672460`（**OpenSSL**） |
| 语义 | recv 错误日志格式化 | **TLS 读取** |
| 是否业务解析 | **否**（REFUTED） | **否**（TLS 层） |
| 是否到达 Gamestate | 否 | 否 |

**结论：** 两条路径**都不**是 Gamestate 消费者；一条是日志，一条是 TLS。

## 5. 裁定

| 项 | 裁定 |
|---|---|
| `0x605220` 是 TLS 读路径 | **PROVEN** |
| `0x672460` 是 OpenSSL 对象方法分派 | **PROVEN** |
| `0x6029A0` → `0x60E5B0` 是错误日志 | **PROVEN** |
| 两路径存在可证汇合 | **REFUTED** |
| 任一路径到达 Gamestate | **REFUTED** |
