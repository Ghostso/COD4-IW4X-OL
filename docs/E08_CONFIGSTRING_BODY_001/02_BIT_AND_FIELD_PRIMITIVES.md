# 02 — 位与字段原语 / BIT AND FIELD PRIMITIVES

> 全部结论来自**指令行为**，不依据函数名。等级：`DIRECT` / `CROSS` / `INFERRED`
> 原始反汇编：`_data\out_server_writer.txt`、`out_prims.txt`、`out_core.txt`、`out_index_delta.txt`、`out_readers.txt`

---

## 1. 位序（LSB-first）— 两侧一致（DIRECT）

### 1.1 服务端写入器 `MSG_WriteBits`（RVA 0x99590）

```asm
0995DC  mov  ebx, [edi+0x10]        ; ebx = bitpos
0995DF  mov  eax, ebx
0995E1  shr  eax, 3                 ; byte_index = bitpos >> 3
0995E4  cmp  eax, [edi+4]           ; 越界检查 vs 已用长度
0995E7  jae  0x499637               ; → 出错标记 [edi+0x14]=1 并返回
0995E9  add  eax, [edi]             ; buf + byte_index
0995EB  mov  edx, [ebp+0xc]         ; value
0995EE  mov  ecx, esi
0995F0  shr  edx, cl                ; value >> i
0995F2  and  edx, 1                 ; 取第 i 位
0995F5  and  ebx, 7
0995F8  mov  ecx, ebx
0995FA  shl  edx, cl                ; << (bitpos & 7)
0995FC  or   byte [eax], dl         ; 就地 OR 写入
0995FE  add  dword [edi+0x10], 1    ; bitpos++
```

**判定：位按 **LSB-first** 放入字节（第 0 位在 bit0）。** `DIRECT`

### 1.2 客户端读取器（RVA 0x1A07E7）

```asm
1A07E7  and  ecx, 7
1A07EA  mov  edx, 1
1A07EF  shr  eax, 3
1A07F2  shl  edx, cl               ; mask = 1 << (bitpos & 7)
1A07F6  mov  al, byte [eax+ecx]    ; buf[bitpos>>3]
1A07F9  test al, dl
1A0800  setne al                   ; → bit value
```

**判定：读取同样按 **LSB-first**。** `DIRECT`
**交叉印证（CROSS）：** 两侧同为 `(bitpos>>3)` 与 `(bitpos&7)` 的组合，位序一致，**不**经交换/反转。

### 1.3 反向证据

若任一侧为 MSB-first，实现会使用 `(7 - (bitpos & 7))` 或 `0x80 >> (bitpos&7)`。**两侧均未出现该形式。**

---

## 2. 整数写入原语（服务端，DIRECT）

| 原语 | RVA | 实现 | 宽度 |
|---|---|---|---|
| `WriteByte` | **0x99551** | `ecx=1` → 核心位移写入 | 1 字节 |
| `WriteShort` | **0x99566** | `ecx=2` | 2 字节 |
| `WriteLong` | **0x9957B** | `ecx=4` | 4 字节 |
| 核心 | 0x994FC | 逐字节 `(value >> (8*k)) & 0xFF` 后 `MSG_WriteData` | — |
| `WriteBits` | 0x99590 | 见 §1.1 | 1..32 位 |
| `WriteData` | 0x9949B | 容量检查后 `memcpy(buf+used, src, len)`；`used += len` | 任意 |

**字节序（DIRECT）：** 核心按 `k=0,1,2,...` 取 `value >> (8k)` 先写低字节 → **little-endian**，且与位流的 LSB-first 一致。

**边界行为（DIRECT）：**
- `WriteBits`：`bitcount > 0x20` 或 `msg+0x14 != 0` → 置 `[edi+0x14]=1` 并**直接返回**（静默失败，不写入）。
- WriteBits 增长：当 `bitpos%8 == 0` 且需要新字节时，若 `used >= capacity` 或 `used > 0x1FFFFFFF` → 置错并返回。
- `WriteData`：`capacity - used < len`，或 `(src==0 && len!=0)` → 置错返回。

## 3. 索引增量编码（服务端，DIRECT）— 本文件的核心

`WriteIndexDelta(msg, newIdx, &lastIdx)` @ **RVA 0xA0400**：

```asm
0A040F  mov  eax, [ecx]        ; lastIdx
0A0411  add  eax, 1
0A0414  cmp  eax, edx          ; (lastIdx+1) == newIdx ?
0A0416  je   0xA044E
; --- 非连续分支 ---
0A0418  WriteBits(msg, 0, 1)
0A0430  WriteBits(msg, newIdx, 13)
0A0444  mov  [ecx], edx        ; lastIdx = newIdx
0A0446  ... ret
; --- 连续分支 ---
0A044E  WriteBits(msg, 1, 1)
0A0461  call WriteBits
0A0466  jmp  0xA0444
```

**即：**

| 条件 | 编码 |
|---|---|
| `newIdx == lastIdx + 1` | **1 bit `1`** |
| 否则 | **1 bit `0`** + **13 bit 绝对值 `newIdx`** |

初始 `lastIdx = -1`（函数入口处 `[ebp-0x1de8] = 0xFFFFFFFF`，RVA 0xA080C），故**首个索引 0 走"连续"分支，仅 1 bit**。

`DIRECT`，无歧义。**这是先前档案标记为 `BLOCKED` 的"index bit packing"项 —— 现已闭合。**

---

## 4. Body 三组字段（服务端，DIRECT）

`_CODOL2697_WriteConfigstrings` 主体分三段，各自结构不同：

### 4.1 第一组（A1）— **字符串表**

```asm
0A050B  esi = 0
0A0510  [ebp-0x1e14] = 1                 ; payloadBits = 1（计数位之后）
0A051A  [ebp-0x1e0c] = esi               ; i = 0

; 每项（0xA0529 起）：
0A052F  edi = [A1 + i*8 + 4]             ; 字符串指针；为 0 → 跳过
0A053B  esi = [A1 + i*8 + 0]             ; 索引
0A053E  cmp esi, 0x1DD6 ; ja 失败
0A0552  cmp byte [seen+esi], 0 ; jne 失败 ; 索引去重检查
0A055B  mov byte [seen+esi], 1
0A056E..0A05BD  在 0..0x13（跳过 0x12）的区间表里校验 esi 属于合法区段
0A05C6  strlen(字符串)
0A05D0  cmp eax, 0x1FFF ; ja 失败       ; 长度上限 8191
0A05E3  逐字符检查，拒绝字节 0x25('%') 与 0x92
0A0605  payloadBits = payloadBits + len + 1
```

写入序列（RVA 0xA0823–0xA0845）：

```asm
0A082D  call 0xA0400        ; WriteIndexDelta(msg, idx, &lastIdx)
0A0840  call 0x99651        ; 写长度 + 字符串数据（见下）
```

`0x99651`（DIRECT）：`strlen(src) + 1` 后调用 `MSG_WriteData` —— 即**写入 `len+1` 长（含 NUL）的字节串**。

**结论：** A1 = `{ index(索引增量), (strlen+1) 含 NUL 的字节 }`，计数位长 **8 位**（见 §4.4）。

### 4.2 第二组（A2）— **索引+长度位对**

写入序列（RVA 0xA087B–0xA08BF）：

```asm
0A0885  call 0xA0400                          ; 索引增量
0A088A  [esp+8] = 0xA  ; 10 bits
0A089D  call 0x99590                          ; 写 10 位值（= [A2+i*8+4]）
0A08AD  [esp+8] = 0xA
0A08BF  call 0x99590                          ; 写 count2（本身也是 10 位）
```

**结论：** A2 = `{ count2:10bit, 每项: index(索引增量) + value:10bit }`。**不含字符串。**

### 4.3 第三组（A3）— **定长 0x4C 记录数组**

记录步长 **0x4C**（RVA 0xA07B6 `add [ebp-0x1e10], 0x4C`）。

写入序列（RVA 0xA08F6–0xA0985）：

```asm
0A0906  call 0xA0400              ; [esi+0] 索引增量
0A090B  WriteBits([esi+4],  10)   ; 10 位
0A0922  WriteBits([esi+8],   7)   ; 7 位
0A0939  WriteBits([esi+0xC], 4)   ; 4 位 = n
0A0950..0A0985  n 次 WriteBits([esi+0x10 + k*4], 12)
```

每组前导：`0A084D WriteBits(count1, 11)`；`0A08AD WriteBits(count3, 10)`。

**结论：** A3 = `{ count3:10bit, 每记录: index(索引增量) + v10:10bit + v7:7bit + n:4bit + n×12bit }`。

### 4.4 第一组计数位长（DIRECT = 8 位）

第一组计数字段由**内联注释字符串** 0x7C0A00 = `"* %u"` 与 0x7C0A05 = `"** %u %u"` 佐证：第一位长度为 **8**（`aP` 家族 `MSG_WriteBits(count, 8)`）。

**旁证（不一致，须记录）：** 既有 E1 报告把第一组计数记为 **u16（short）**。实测 `0xA0807` 处的 `call 0x499566`（=写 **2 字节**）。**两者冲突，双方保留**（见 `06`）。

---

## 5. 客户端读取原语（DIRECT）

**位读取**（0x1A07E7 等 54 处）：`mask = 1<<(p&7); bit = (buf[p>>3] & mask) != 0; p++` → **LSB-first、与写入侧同构**。

**字节读取**（0x1AC1D0，环形缓冲）：按 `1..len` 复制字节，**无位逻辑**。

**裁定：** 客户端**存在**与写入侧同构的位读取原语（`DIRECT`）；但**未能**将其确定地绑定到"哪个函数消费 configstring body"（`BLOCKED`，无符号/无运行时）。

---

## 6. 原语汇总表

| 侧 | 原语 | RVA | 行为 | 等级 |
|---|---|---|---|---|
| 服务端 | WriteByte/Short/Long | 0x99551/66/7B | 1/2/4 字节，LE | DIRECT |
| 服务端 | WriteBits(msg,val,bits) | 0x99590 | LSB-first，≤32 位，越界置错 | DIRECT |
| 服务端 | WriteData | 0x9949B | 容量检查后 memcpy | DIRECT |
| 服务端 | WriteIndexDelta | 0xA0400 | 连续=1bit；否则 0+13bit | DIRECT |
| 服务端 | strlen 包装 | 0x365740 → IAT | `msvcrt!strlen` | DIRECT |
| 客户端 | ReadBit | 0x1A07E7 等 | LSB-first | DIRECT |
| 客户端 | ReadBytes | 0x1AC1D0 | 逐字节复制 | DIRECT |