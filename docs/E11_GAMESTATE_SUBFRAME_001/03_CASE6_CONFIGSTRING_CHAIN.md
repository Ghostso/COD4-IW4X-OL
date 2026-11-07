# 03 — case 6 与 Configstring body 链 / CASE 6 CHAIN

> 等级：`DIRECT` / `CROSS` / `INFERRED` / `BLOCKED`

---

## 1. case 6 完整指令（DIRECT）

```asm
354697  push 0x20000
35469C  lea ecx,[ebp-0x2000C]
3546A2  push 0 / push ecx
3546A5  call 0xB50900                    ; memset 256KB 缓冲
3546AD  lea edx,[ebp-0x2000C]
3546B3  push 0x20000 / push edx
3546B9  lea esi,[ebp-0x20060]
3546BF  call 0x1AC190                    ; MSG_InitReadOnly(buf,0x20000)
3546C4  mov ecx,[edi+0x89244]
3546CB  lea eax,[ebp-0x2004C]
3546D1  push 4                            ; 读 4 字节
3546D4  call ecx                          ; → [ebp-0x2004C] = LEN
3546D6  mov edx,[ebp-0x2004C]             ; edx = LEN
3546DC  mov eax,[ebp-0x20058]             ; eax = msg.buf
3546E2  mov ecx,[edi+0x89244]
3546EB  push ebx / push edx / push eax
3546EE  call ecx                          ; 读 LEN 字节 → msg.buf
3546F3  call 0x352F80                     ; → 0xA2660
```

**语义（DIRECT）：** case 6 = `u32 LEN` + `LEN 字节载荷`，载荷被装入一个新的只读 MSG，然后交给 `0x352F80`。

## 2. `0x352F80` 的 +1 游标（DIRECT）

```asm
352F80  push 0x27760 / push 0 / push 0x1B47EE4
352F8C  call 0xB50900                    ; 清零状态
352F91  mov ecx,[esi+0x18]               ; msg.size
352F94  add ecx,[esi+0x14]               ; + offset
352F97  mov eax,[esi+0x1C]               ; msg.pos
352F9D  cmp eax,ecx
352F9F  jge 0x752FAC
352FA1  inc eax                          ; pos += 1
352FA2  mov [esi+0x1C],eax
352FA5  mov ecx,esi
352FA7  jmp 0xA2660                      ; → body reader
352FAC  mov dword [esi],1                ; 越界标志
352FB2  mov ecx,esi
352FB4  jmp 0xA2660
```

**关键（DIRECT）：** `0x352F80` 无条件把 msg 游标 **+1 字节**后才进入 `0xA2660`；越界分支也进入（只是先置错误标志）。

## 3. `0xA2660` 读取的第一个字段（DIRECT）

```asm
0A2693  mov ecx,[esi+0x18]
0A2696  mov eax,[esi+0x1C]
0A2699  add ecx,[esi+0x14]
0A269C  lea edi,[eax+2]                  ; pos+2
0A26A5  cmp edi,ecx
0A26AF  push 2                           ; 读 2 字节
0A26B2  call 0x1AC1D0                    ; MSG_ReadData
0A26B7  movsx eax,word [ebp-0x108]       ; 有符号 16 位
```

**即 `0xA2660` 进入后立刻读 2 字节 count1**（DIRECT）。

## 4. 与服务端的字段对照（CROSS）

| 步骤 | 服务端 | 客户端 | 一致 |
|---|---|---|---|
| 子帧头 | `WriteByte(4)` @0xA07F8 | `0x352FA1` +1 字节 | 位置一致（值未比较） |
| count1 | `WriteShort(count1)` @0xA0807（2B） | `push 2` + `MSG_ReadData` @0xA26B2 | ✅ |
| A1/A2/A3 | 见 `_CODOL2697_WriteConfigstrings` | `0xA2660` 内 `MSG_ReadBits` | ✅（字段级） |
| 子帧尾 | `WriteByte(6)` @0xA0997 | **未定位** | ❌ |

## 5. 长度前缀 `LEN` 的来源分析

case 6 先读 4 字节 `LEN`，再把 `LEN` 字节装进 MSG。服务端 `0xA22C1` 调用 `WriteConfigstrings` 时**没有**写任何长度前缀（`WriteByte(4)` 紧跟在 `WriteInt32(field4)` 之后）。

| 假设 | 证据 | 裁定 |
|---|---|---|
| `LEN` 是 Configstring 子帧的显式长度 | 服务端无对应写入 | **REFUTED** |
| `LEN` 属于外层分片/缓冲协议（非 `0xA21B8` 内） | case 6 在 `0x354100` 内，`0x354100` 由 `0x350170`/`0x3512A0` 驱动 | **INFERRED** |
| `LEN` 是 Gamestate 的某个 4 字节字段 | 服务端 `0xA2288 WriteInt32(field4)` 位置对应 | **INFERRED（候选）** |

**说明：** 客户端 `0x34FD80` 同样使用“u32 长度 + 载荷”包装，说明该客户端在**读取层**普遍使用长度前缀分片。因此 case 6 的 `LEN` 更可能是**读取层分片长度**，而非 Configstring 自身字段。

## 6. 裁定

| 项 | 裁定 |
|---|---|
| case 6 与 `0xA2660` 的连接 | **PROVEN**（`0x3546F3 → 0x352F80 → 0xA2660`） |
| `0x352F80` 的 +1 字节 | **PROVEN**（指令级） |
| 被跳过字节 = 服务端 `0x04` | **INFERRED**（位置一致，无值比较） |
| case 6 的 4 字节 `LEN` 语义 | **BLOCKED**（服务端无对应写入） |
| Configstring 字段序一致 | **CROSS**（count1/A1/A2/A3） |
| 子帧尾 `0x06` 客户端读取 | **BLOCKED** |
