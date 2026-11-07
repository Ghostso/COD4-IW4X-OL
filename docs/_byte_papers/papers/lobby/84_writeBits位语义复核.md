# `writeBits` / `writeData` 的确切位语义（复核）

> 承接 `lobby/83`，这份是把"到底写几位"钉死

---

## 1. `0xb75d40` = 位长度 → 字节数

```asm
mov eax, [ebp+8]        ; nbits
and ecx, 0xffff0000
neg / sbb / and 0x10     ; 若 >= 65536 则先移 16
...
test eax, 0xff00 → 移 8
test al, 0xf0    → 移 4
test al, 0xc     → 移 2
```

**⇒ 这是标准的 `(n + 7) >> 3` 实现（含 16/8/4/2 分档）。**

**⇒ 返回"n 位需要几个字节"。**

---

## 2. `writeBits(n)` 的展开

```asm
0xb77b13  cmp byte [ecx+0x21], 0
0xb77b17  je  ret              ; ★ 位流未启用 → 什么都不写
0xb77b19  mov eax, [ebp+8]     ; n
0xb77b1c  push 0               ; pad = 0
0xb77b1e  push 0x1f            ; width = 31
0xb77b20  push 0               ; start = 0
0xb77b22  push eax             ; value = n
0xb77b23  call writeBitsCore
```

**⇒ `writeBits(n)` = `writeBitsCore(n, start=0, width=31, pad=0)`。**

---

## 3. `writeBitsCore` 的截取逻辑（复核）

```asm
0xb77ac5  sub ecx, edi          ; ecx = width - start = 31 - 0 = 31
0xb77ace  call 0xb75d40          ; 31 → 4 字节
0xb77ad8  mov ecx, [ebp+8]      ; value = n
0xb77adb  cmp ecx, ebx          ; n > 31 ?
0xb77adf  mov ecx, ebx          ; 夹到 31
0xb77ae3  cmp ecx, edi          ; n < 0 ?
0xb77ae7  mov ecx, edi          ; 夹到 0
0xb77ae9  sub ecx, edi          ; ecx = n
0xb77aef  mov [ebp+0x14], ecx   ; 位宽 = n
0xb77af5  call writeData(&n, ceil(n/8) 字节)
```

**⇒ 写 `n` 位，内容就是 `n`。**

---

## 4. ★ 但这里有个关键点：`writeData` 的 nbits 参数

**注意 `writeData(&n, bytes)` 的第一个参数是 `eax`（字节数），
而不是 `n`（位数）。**

**再看 `0xb777c0`（writeData）：**

```asm
0xb777c3  mov eax, [ebp+0xc]    ; 参数 2 = nbits
0xb777d1  lea edi, [eax+ecx-1]  ; (nbits + bitpos - 1)
0xb777d5  shr edi, 3            ; /8 → 需要的字节
```

**⇒ `writeData(ptr, nbits)` 的第二参数确实是**位**。**

**⇒ 那么 `0xb77aeb push eax` 传的是 `0xb75d40` 的返回值（字节数），**
**而 `writeData` 会把它当**位数**解释。**

**⇒ 若 `n = 21`：`0xb75d40(21) = 3` 字节，但作为 nbits 传入就是 **3 位**！**

**⇒ 这会导致只写 3 位，而不是 21 位。**

---

## 5. 这意味着什么

**两种可能：**

### A. `0xb77aeb push eax` 的参数是"字节数当位数用"（bug 或特殊设计）

**那 `writeBits(0x15)` 实际只写 **3 位**（值 21 的低 3 位 = 5）。**

### B. 我看错了 `writeBitsCore` 的段 3

**需要重新核对 `0xb77aeb` 之前 `eax` 的值。**

**从 `0xb77ace call 0xb75d40` → `inc eax`：**

```
eax = (31>>3) + 1 = 3 + 1 = 4
```

**⇒ `eax = 4`。**

**⇒ `writeData(&n, 4)` = 写 4 位。**

**⇒ `writeBits(21)` 写 4 位（值 21 的低 4 位 = 0101 = 5）。**

---

## 6. 这是一个重要更正

**`writeBits(n)` **不是**写 n 位，
而是写 **`ceil((31)/8) + 1 = 5` 位？**

**重新算：**

```
0xb77ac5: ecx = width - start = 31
0xb77ace: call 0xb75d40(31) → ceil(31/8) = 4
0xb77ad7: inc eax → 5
0xb77aeb: push 5
0xb77af5: call writeData(&n, 5)
```

**⇒ `writeBits(n)` 固定写 **5 位**，值是 n 的低 5 位。**

---

## 7. 那 `writeBits(0x15)` = 写 5 位，值 21 的低 5 位

```
21 & 0x1F = 21 = 0b10101
```

**⇒ 写 `10101`（5 位）。**

**⇒ 而 `writeBits(3)` = 写 5 位，值 `00011`。**

**⇒ 每条消息前是 **5 位**，不是 3 位！**

---

## 8. 重新核对 `writeData` 的调用

**`0xb77ac5 sub ecx, edi` 中：**
- `ebx` = `[ebp+0x10]` = width = 31
- `edi` = `[ebp+0xc]` = start = 0
- `ecx = 31`

**`0xb77d40(31)`** → 31 位 = 4 字节（3.875 向上取整）。

**`inc eax` → 5。**

**`push 5` → `writeData(ptr, 5)` → 写 **5 位**。**

**⇒ 结论：`writeBits(n)` 恒写 5 位。**

---

## 9. 这个发现颠覆了前面的位宽计算

**`lobby/82` 里我统计"`0x15` 后跟 32 位"，
那是 `writeData(&val, 0x20)` 的 0x20，**不是 `writeBits`**。**

**⇒ `writeBits` 的 5 位是**标签固定长度**，不是可变。**

**⇒ 位流格式需要重算：**

```
writeBits(3)        → 5 位，值 00011
writeData(&v, 8)    → 8 位
```

**⇒ 头是 5 + 8 = **13 位**，不是 11 位。**

---

## 10. 必须验证

**这个"5 位"的推论如果错，整个位流格式都会错。**

**验证方法：反汇编 `writeBits` 的一个真实调用，
数它写入后 `[+0x14]`（位偏移）增加了多少。**

**⇒ 需要动态验证，静态读到此为止。**

---

## 11. 状态

| 项 | 状态 |
|---|---|
| `0xb75d40` = 位→字节 | ✅ 确定 |
| `writeBits(n)` 展开 | ✅ 确定 |
| `writeBits` 写 n 位还是 5 位 | **⚠️ 两种读法都有依据，未定** |
| 消息头长度 | **11 位 或 13 位，未定** |

**⇒ 这是本轮最重要的未决点。**
