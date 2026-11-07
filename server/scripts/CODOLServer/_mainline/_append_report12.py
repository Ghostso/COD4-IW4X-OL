import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\CONFIRMED_RESULTS_20260928.md"
s = open(p, encoding="utf-8", errors="replace").read()
add = """

---

## 31. 重要更正：`0xB9BBB0` 返回的是指针，不是长度

### 31.1 `0xB9BEB0` 读入器构造函数（完整）

```asm
; 0xB9BEB0(this, size, flag)
00B9BEEA  mov byte [esi+0x18], cl     ; flag
00B9BEED  mov byte [esi+0x19], cl
00B9BEF0  mov byte [esi+0x1a], 0
00B9BF1B  call 0xB9BD40               ; 真正分配

; 0xB9BD40(this, size)
00B9BD4E  lea eax, [edi+0x37]         ; 申请 size + 0x37 字节
00B9BD52  mov dword [esi+0x28], 0x18
00B9BD59  mov dword [esi+0x20], eax
00B9BD5C  call 0xB74220               ; malloc
00B9BD64  mov dword [esi+0x1C], eax   ; +0x1C = 缓冲区基址
00B9BD67  add eax, 0x1F
00B9BD6A  mov dword [esi+0xC], eax    ; +0x0C = 基址 + 0x1F
00B9BD6D  mov dword [esi+0x24], 0x1F
00B9BD74  mov dword [esi+8], edi      ; +0x08 = size
00B9BD7B  mov dword [esi+0x14], eax
00B9BD7E  mov dword [esi+0x10], eax
```

于是：

```text
0xB9BBB0 = [esi+0x1C] - [esi+0x24] + 0x1F
         = 基址 - 0x1F + 0x1F
         = 基址            <-- 返回指针！
```

**`0xB9BBB0` 返回缓冲区基址指针，不是"可用长度"。**

### 31.2 这推翻了此前若干结论

```text
第 22.3 节  「可用长度 = 0x1C - 0x24 + 31 = 28 < 200 所以没解析」  作废
第 24.2 节  「rd1c 是已缓冲字节数」                                作废
第 27 节后续「available = 0xB9BBB0(reader) 是长度」                作废
```

实际语义：

```text
reader+0x08  size（构造时给定）
reader+0x0C  游标起点 = 基址 + 0x1F
reader+0x10  读游标
reader+0x14  写游标
reader+0x1C  缓冲区基址
reader+0x20  分配大小 = size + 0x37
reader+0x24  0x1F（前缀保留量）
```

### 31.3 分发器 opcode 偏移的含义随之修正

`0xBA4440` 的取字节：

```asm
00BA44AD  mov ecx,[esi+0xB0]     ; reader
00BA44B3  call 0xB9BBB0          ; eax = 基址指针
00BA44B8  mov edi,[esi+0xAC]     ; 帧长度
00BA44CA  dec edi                ; edi = 帧长度 - 1
00BA44D8  call 0xB765A0          ; memcpy(dst, 基址 + 0, 1)，上界 = 帧长度-1
```

即 **opcode = reader 缓冲区的第 0 字节**，上界为 `帧长度-1`。

而 reader 的缓冲区由 `0xBA2125` 处的 `0xB9BEB0(size = 帧长度-2, flag=1)`
新建，其内容由 `0xBA20A0` 后续写入。

### 31.4 `0xBA3FB0` 的长度前缀读入位置

```asm
00BA3FC8  lea edx, [eax + esi + 0xA0]   ; 目标 = [req+0xA0] + 已读字节数
00BA3FD6  call 0xC73A00                 ; recv 到 [req+0xA0]
00BA3FEB  cmp dword [esi+0xA4], 4
00BA401C  mov eax, [ebp-8]
00BA401F  mov [esi+0xAC], eax           ; [req+0xAC] = u32 长度
```

4 字节长度前缀落在 `[req+0xA0]`，不是连接内部缓冲。

### 31.5 状态

```text
第一档  未闭合：opcode 缓冲区的填充路径仍差最后一步
第二档  未开始
```

本节的更正是自动推进过程中的自我纠错记录；第 22、24、27、30 节中凡
依赖「0xB9BBB0 返回长度」的推论均已作废。
"""
s = s.rstrip() + add
open(p, "w", encoding="utf-8", newline="\n").write(s + "\n")
print("appended", len(add))
