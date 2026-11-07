# `writeBitsCore` 完整语义（位流的最后一块）

> 承接 `lobby/82`
> **位流四件套的最后一块拼图：`writeBits(n)` 到底写什么**

---

## 1. 函数签名

```
writeBitsCore(value, start, width, pad)    @ 0xb77a70
  [ebp+0x08] = value
  [ebp+0x0c] = start
  [ebp+0x10] = width
  [ebp+0x14] = pad / 输出槽（复用）
  ecx        = 位流对象
```

---

## 2. 三段逻辑

### 段 1：`pad != 0` 时追加 12 位标记

```asm
0xb77a73  cmp byte [ebp+0x14], 0
0xb77a82  je  0xb77ac3              ; pad == 0 → 跳过
0xb77a84  push 0xc
0xb77a86  call writeBits(0xc)       ; ★ 写 12 位 = 0xC
0xb77a8b  cmp byte [esi+0x21], 0
0xb77a8f  je  0xb77ac3
0xb77a91  push 8
0xb77a95  call writeBits(8)         ; 8 位
0xb77a9a  push 0x20
0xb77aa5  call writeData(&val, 0x20); 32 位
...
```

**⇒ `pad != 0` 时，会额外写 `12 + 8 + 32` 位的封装头。**

### 段 2：`pad == 0` 时（我们用的路径）

```asm
0xb77ac3  mov ecx, ebx              ; width
0xb77ac5  sub ecx, edi              ; width - start
0xb77acc  je  0xb77ad8              ; 为 0 → 跳过
0xb77ace  push ecx
0xb77acf  call 0xb75d40             ; ★ 计算有效位数
0xb77ad7  inc eax
```

**⇒ `0xb75d40(n)` 计算"n 位需要的字节数"。**

### 段 3：截取并写入

```asm
0xb77ad8  mov ecx, [ebp+8]          ; value
0xb77adb  cmp ecx, ebx              ; value > width ?
0xb77add  jbe 0xb77ae3
0xb77adf  mov ecx, ebx              ; 夹到 width

0xb77ae3  cmp ecx, edi              ; value < start ?
0xb77ae5  jae 0xb77ae9
0xb77ae7  mov ecx, edi              ; 夹到 start

0xb77ae9  sub ecx, edi              ; ecx = value - start
0xb77aeb  push eax                  ; 字节数
0xb77aef  mov [ebp+0x14], ecx       ; 存"位宽"
0xb77af5  call writeData(&bits, bytes)
```

**⇒ 实际写入的是 `value - start` 这几位。**

---

## 3. ★ `writeBits(n)` 的真相

**`0xb77b10` 的实现（`lobby/70`）：**

```asm
push 0        ; start = 0
push 0x1f     ; width = 31
push 0        ; pad = 0
push eax      ; value = n
call writeBitsCore
```

**⇒ `writeBits(n)` = `writeBitsCore(n, 0, 31, 0)`。**

**代入段 3：**

```
value = n
start = 0
width = 31
→ 写入 n - 0 = n 位
```

**⇒ `writeBits(n)` **确实写 n 位**，值就是 n。**

**⇒ 我之前的"可能是写 31 位"是错的。**

---

## 4. 那 `writeBits(3)` 写的是什么

**`writeBits(3)` = 写 3 位，值为 3（二进制 `011`）。**

**⇒ 每条 dwRoomMessage 的前 3 位是 `011`。**

**⇒ 这是一个**固定的魔数标记**。**

---

## 5. 为什么是 3

**三种可能：**

1. **版本号**（消息格式版本 3）
2. **类型组**（所有 dwRoomMessage 属于组 3）
3. **长度字段的位宽声明**（接下来 3 位？）

**从 `deserialize`（`0x627ce0`）看：**

```asm
push 3
call readBits(3)      ; 读 3 位
```

**⇒ 读了但**没有比较**。**

**⇒ 那它只是"跳过 3 位"，不是校验。**

**⇒ 最可能是**版本号**，客户端不校验。**

---

## 6. 完整位流语义（最终版）

| 操作 | 等价展开 | 写入 |
|---|---|---|
| `writeBits(n)` | `writeBitsCore(n, 0, 31, 0)` | **n 位，值 n** |
| `writeData(ptr, k)` | 直接拷贝 k 位 | k 位数据 |
| `writeBitsCore(v,s,w,pad)` | — | `(v-s)` 位，范围夹在 `[s,w]` |

**缓冲区：`[+0x08]` 指针、`[+0x10]` 容量、`[+0x14]` 当前位偏移。**

**⇒ 位流是"连续位数组"，最后按 `ceil(bits/8)` 取字节。**

---

## 7. 可以复现一条消息了吗

**以 `MemberList`（`0x627d80`）为例：**

```
writeBits(3)                  写入 3 位，值 011
writeData(&[obj+4], 8)        写入 1 字节
writeBits(0x15)               写入 21 位，值 0x15
writeData(&field, 0x20)       写入 4 字节
```

**总长 = 3 + 8 + 21 + 32 = 64 位 = 8 字节。**

**⇒ 一条 `MemberList` 消息正好 **8 字节**！**

---

## 8. 这个数字可以验证

**如果将来抓到一个 `MemberList` 的推送，应该是 8 字节：
`011` + 1 字节 + 21 位 + 4 字节。**

**⇒ 这是一个可验证的预测。**

---

## 9. 剩余未解

1. `writeBits(3)` 的值是否恒为 3（需更多消息确认）
2. `0x15` 的语义（22 次出现，宽度 8/32/64）
3. 各字段的业务含义
