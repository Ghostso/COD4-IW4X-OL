# 05 — 位/字节对齐重建 / BIT ALIGNMENT RECONSTRUCTION

---

## 1. 服务端侧位记账（DIRECT，指令级）

### 1.1 msg 结构字段

| 偏移 | 语义 | 证据 |
|---|---|---|
| `[msg+0]` | 缓冲区指针 | `0x9949B` |
| `[msg+4]` | 字节计数 used | `add [ebx+4],eax` @0x994DD |
| `[msg+8]` | 容量 | `0x9949B` |
| `[msg+0x10]` | 位位置 bitpos | `MSG_WriteBits` |
| `[msg+0x14]` | 溢出标志 | `0x994C8` |

### 1.2 关键重同步（DIRECT）

```asm
09960A  test byte [edi+0x10], 7      ; bitpos % 8 == 0 ?
09960E  jne 0x4995DC
099610  mov eax, [edi+4]             ; used
09961F  lea edx, [eax*8]
099626  mov [edi+0x10], edx          ; bitpos = used*8  ← 强制重同步
09962B  lea ecx, [eax+1]
09962E  mov [edi+4], ecx
099631  mov byte [edx+eax], 0        ; 追加 0 字节
```

### 1.3 WriteData / WriteLenStr 不更新 bitpos（DIRECT）

- `MSG_WriteData` `0x9949B`：只 `memcpy` + `used += len`，**无 `[msg+0x10]` 访问**。
- `WriteLenStr` `0x99651`：脚本自检 `out_c09.txt` 结果 `False`，**无 `[msg+0x10]` 写入**。

**含义：** A1 字符串以裸字节写入，位字段在下一次字节边界处强制跳到 `used*8`。

## 2. 0x04 + count1 的起点（DIRECT）

```asm
0A07E6  mov dword [edi+0x10], 0      ; bitpos 归零
0A07F8  call WriteByte(4)            ; 8 bit
0A0807  call WriteShort(count1)      ; ecx=2 → 2 字节 = 16 bit
```

`0x04`(8) + count1(16) = 24 bit = **3 字节整**，因此 body 起点在字节边界上。

## 3. Configstring 三段的位长模型

## 3.1 记录格式

| 段 | 格式 |
|---|---|
| A1 | `1 bit`（连续索引）或 `1+13 bit`（绝对索引）+ 字符串 `(len+1)` 字节 |
| A2 | 10-bit 计数 + [1 或 14 bit 索引 + 10-bit 值] |
| A3 | 10-bit 计数 + [1 或 14 bit 索引 + 10-bit A + 7-bit B + 4-bit n + n×12-bit] |

## 3.2 累计位模型（从 `0x04` 首位起算）

| 场景 | 0x06 起始 bitpos（count1=16） | 模 8 |
|---|---|---|
| A1=A2=A3 空 | 44 | 4 |
| A1=[(0,'')] | 53 | 5 |
| A1=[(0,'a')] | 61 | 5 |
| A1=[(0,'a')]、A2=[(0,1)] | **72** | **0（字节对齐）** |
| A1=[(0,'a')]、A2=[(0,1),(1,2)]、A3=[(0,1023,127,[4095,1])] | 129 | 1 |
| A1=[(0,'a'),(5,'bb')] | 99 | 3 |

**结论（DIRECT 模型）：** `0x06` **不保证字节对齐**；在特定输入下可为字节对齐。

## 4. 客户端读取端位推进

| 段 | 客户端读取 | bitpos 是否推进 |
|---|---|---|
| count1 | `MSG_ReadData(...,2)` @0xA26B2 | 字节游标 +2（DIRECT） |
| A1 | `MSG_ReadBits` 13-bit + 字符串 NUL 扫描 | 位游标推进（DIRECT） |
| A2 | `MSG_ReadBits` 11-bit / 13-bit / 10-bit | 位游标推进（DIRECT） |
| A3 | `MSG_ReadBits` 10-bit / `0xA2480` | 位游标推进（DIRECT） |
| 0x06 | **未定位** | **BLOCKED** |

**客户端位读取原语（DIRECT）：** `MSG_ReadBits` `0x1AC670` 使用 `[msg+0x20]` 作 bitpos，`and 7` / `sar 3` 与 `MSG_WriteBits` 同构（LSB-first）。

**客户端字节读取原语（DIRECT）：** `MSG_ReadData` `0x1AC1D0` 逐字节读，不使用位逻辑；`0xA2660` 的 count1 用它读 2 字节。

## 5. 裁定

| 子项 | 裁定 |
|---|---|
| `0xA2660` 内字段位序为 LSB-first | **PROVEN（DIRECT）** |
| count1 = 16 bit 字节对齐读 | **PROVEN（DIRECT）** |
| `0x06` 起始 offset 可复算 | **PROVEN（模型，DIRECT）** |
| `0x06` 是否字节对齐 | **BLOCKED（因输入相关）** |
| 客户端对 `0x06` 的对齐处理 | **BLOCKED** |
