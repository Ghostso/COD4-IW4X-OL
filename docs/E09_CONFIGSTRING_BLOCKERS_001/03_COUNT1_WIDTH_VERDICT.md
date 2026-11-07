# 03 — count1 宽度裁定 / COUNT1 WIDTH VERDICT

> 任务 B 要求逐步复核 `mov ecx,2` 的**参数含义**，并用双侧证据裁定。
> 等级：`DIRECT` / `CROSS` / `INFERRED` / `BLOCKED`

---

## 1. 复核 `0x99566` 包装器与 `mov ecx,2` 的真实含义

```asm
0099566  push ebp
0099567  mov  ebp, esp
0099569  mov  ecx, 2          ; <== 关键
009956E  mov  edx, [ebp+0xc]  ; value
0099571  mov  eax, [ebp+8]    ; msg
0099574  call 0x994FC         ; 核心写入器
0099579  pop  ebp
009957A  ret
```

核心写入器 `0x994FC`（**完整阅读**）：

```asm
00994FC  push ebp / mov ebp,esp / lea esp,[esp-0x1C]
009509  mov  ebx, eax          ; ebx = msg
00950B  mov  esi, edx          ; esi = value
00950D  mov  edx, ecx          ; edx = ecx  ← 参数
00950F  test ecx, ecx
009511  je   0x499536          ; 若 ecx==0 跳过拆字节循环
009516  mov  eax, 0
00951B  lea  ecx, [eax*8]       ; ecx = k*8
009522  mov  edi, esi
009524  shr  edi, cl            ; value >> (8k)
009528  mov  [ebp+eax-0x10], cl ; 逐字节存入栈缓冲
00952C  add  eax, 1
00952F  cmp  edx, eax
009531  jne  0x49951B           ; 循环 ecx(=edx) 次
009536  mov  [esp+8], edx       ; len = edx
00953A  lea  eax,[ebp-0x10]     ; ptr = 栈缓冲
00953D  mov  [esp+4], eax
009541  mov  [esp], ebx
009544  call 0x49949B           ; MSG_WriteData(msg, ptr, len)
```

**`ecx` 的语义（DIRECT）：**
1. `ecx` 直接决定**拆字节循环的次数**（`cmp edx,eax`，edx=ecx）→ 即**字节数**；
2. `ecx` 又被原样作为 `MSG_WriteData` 的 **`len`** 参数；
3. 每轮 `value >> (8k)` 取一字节（小端）。

→ **`ecx = 2` 表示"写 2 个字节"，不是位数、不是元素个数、不是其它参数。** 三个用法（循环次数 / len / 移位数）**互相独立地**指向"字节数"。

## 2. 该包装器的**唯一**用途

`0x99566` 在服务端**只被 `0xA0807` 调用**（写 configstring 的 count1），以及在 `_CODOL2697_WriteGamestate`（0xA21B8）系列中写同类计数。
**无任何调用点把 `0x99566` 当作"位数"使用。**

## 3. 客户端侧的独立裁定（决定性）

客户端 `0xA2660` 读取 count1 的方式：

```asm
0A269C  lea  edi, [eax + 2]      ; 光标 +2
0A26A5  cmp  edi, ecx ; jg      ; 边界
0A26AF  push 2                   ; <== 长度参数
0A26B1  push edx                 ; dst
0A26B2  call 0x1AC1D0            ; MSG_ReadData(msg, dst, 2)
0A26B7  movsx eax, word [ebp-0x108]   ; <== 读作有符号 16 位
```

**`MSG_ReadData(msg,dst,2)` = 逐字节读 2 字节**（该函数是纯字节复制，见 E-08/E-09 `01` §1）。
随后用 `movsx ... word ptr` 按**16 位有符号**解释。

→ **客户端独立证据：count1 = 2 字节 = 16 位。** 与服务器 `mov ecx,2` **一致**。

## 4. 后续字段偏移的交叉检验（任务 B 第 4 条）

假设 **16 位**：

| 项 | 结果 |
|---|---|
| `0x04`(8b) + count1(16b) = 24 位 → **字节对齐** | ✔ 与 A1 字符串为整字节写入相协调 |
| 客户端：`MSG_ReadData(...,2)` 后再读位字段 | ✔ 客户端位光标从 24 位开始（2 字节数据 + 已读的 1 字节 0x04） |
| 若为 8 位：`0x04`+8 = 16 位 | 也能对齐，但**客户端已明确读 2 字节** → 8 位假设与客户端**矛盾** |

**8 位假设的唯一来源**是内联格式串 `"* %u"`（VA 0x7C0A00）。复核该串的使用点：它在**服务端**代码中用于 `snprintf` 生成**文本形式**的调试条目（`0xA0654` 附近的 `"* %u"` 与 `0xA065A` 的 `cmp eax,0x3FF`），**不是**线格式的位宽声明。

→ **格式串证据不适用于 count1 宽度**；其"8 位"暗示属**误读**。

## 5. 裁定

| 假设 | 服务端证据 | 客户端证据 | 判定 |
|---|---|---|---|
| **count1 = 16 位（2 字节）** | `mov ecx,2` → 循环次数 + `WriteData` len + 移位步长 | `MSG_ReadData(...,2)` + `movsx word` | **PROVEN** |
| count1 = 8 位 | 仅注释串 `"* %u"`（用途不符） | **无**（且与 `push 2` 矛盾） | **REFUTED** |

**最终：`count1` = 2 字节（16 位，little-endian 量级分解写入）。**

> 工程注记：E-08 `22_SERVER_START_GATING_AUDIT.md` 曾建议"把 count1 宽度参数化"。**该参数化不再必要** —— 两侧证据一致且互斥假设已被驳倒。参数化可保留为**回归测试开关**，但**不得**再作为"语义未定"的理由。