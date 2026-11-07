# -*- coding: utf-8 -*-
from pathlib import Path
base=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001")
p=base/"E25_EXECUTIVE_SUMMARY.md"; t=p.read_text(encoding="utf-8")
old="""1. `0x6ABAAA`/`0x6ABABB` 的 `ebx` 不是数据块，而是**序列化器对象**（`0x6ABA50 mov ebx,eax` ← `0x6ABA4B call 0x4DAB40`）。两次 `call 0xDF6F97C` 只是往序列化器里追加字段，真正的字节缓冲是 `[ebx+0xC]`、长度是 `[ebx+0x10]`。"""
new="""1. `0x6ABAAA`/`0x6ABABB` 的 `ebx` 不是数据块，而是**序列化器对象**（`0x6ABA50 mov ebx,eax` ← `0x6ABA4B call 0xDAB40`，容量取 `[ebp-0x17c]+6`）。两次 `call 0xDF6F97C` 只是往序列化器里追加字段；真正传给 `0x6AA230` 的是 **`0x6ABAE2 mov edx,[ebx+0xC]`（字节缓冲指针 = data0）** 与 **`0x6ABAED call 0xDF16878`（返回序列化字节数 = data1）**。"""
assert old in t; t=t.replace(old,new)
old2="""| 1. 数据被构造 | **PROVEN** | 序列化器 `0x6AB4C3..0x6ABABB`；`[ebx+0xC]`/`[ebx+0x10]` |"""
new2="""| 1. 数据被构造 | **PROVEN** | 序列化器 `0xDAB40` vtable `0xCBBD24`；缓冲 `[ebx+0xC]`、写游标 `[ebx+0x10]` |"""
assert old2 in t; t=t.replace(old2,new2)
old3="""| 2. 数据被传递给函数 | **PROVEN** | `0x6ABAF2/0x6ABAF9/0x6ABAFC` push 参数 + `call 0x6AA230` |"""
new3="""| 2. 数据被传递给函数 | **PROVEN** | `0x6ABAF2`(len) `0x6ABAF9`(buf=`[ebx+0xC]`) + `0x6ABAFC call 0x6AA230` |"""
assert old3 in t; t=t.replace(old3,new3)
p.write_text(t,encoding="utf-8"); print("exec patched")

p=base/"E25_RESPONSE_BLOCK_FIELD_PROVENANCE.md"; t=p.read_text(encoding="utf-8")
add="""

## 6. 实际传给 `0x6AA230` 的两个参数（决定性）

```asm
6ABAD2  mov ecx, ebx
6ABAD4  call 0xDF16878          ; 取序列化状态（返回值用于成功判定）
6ABAD9  cmp byte ptr [ebp-0x172],0
6ABAE0  je  0xAABB0D
6ABAE2  mov edx, dword ptr [ebx+0xC]   ; data0 = 序列化字节缓冲指针
6ABAE7  mov dword ptr [ebp-0x18C], edx
6ABAED  call 0xDF16878                 ; data1 = 序列化字节数（返回值）
6ABAF2  push eax                       ; arg2 = data1（长度）
6ABAF3  mov eax, dword ptr [ebp-0x18C]
6ABAF9  push eax                       ; arg1 = data0（缓冲指针）
6ABAFA  mov ecx, edi                   ; this = 会话对象
6ABAFC  call 0x6AA230
```

在 `0x6AA230` 内：

```asm
6AA267  mov ebx, dword ptr [ebp+0xC]   ; ebx = data1 = 长度
6AA273  mov ecx, dword ptr [ebp+8]     ; ecx = data0 = 缓冲指针
6AA276  push esi                       ; arg3 = 0
6AA277  push ebx                       ; arg2 = 长度
6AA278  push ecx                       ; arg1 = 缓冲指针
6AA27B  call 0x320E30                  ; clone(node, buf, len, 0)
```

→ `data0` = **缓冲指针**，`data1` = **字节长度**。两者一起被 `0x320E30` 复制进新节点（`memcpy(node+0xC, data0, data1)`）。**等级：PROVEN。**
"""
t=t.rstrip()+add
p.write_text(t,encoding="utf-8"); print("provenance appended")
