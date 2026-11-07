# 178 · 位序定案：`LSB-first`（R17 的 MSB-first 是错的）+ item 21 段条件

> 卷次：178（**第二次更正卷** —— 更正 177 卷的位序推断）
> 方法：从 `0xB777C0` 的**掩码生成式**反推位序，再用自洽性检验
> 结论：**`LSB-first`，不是 MSB-first。**

---

## §0 结论

1. **位序 = LSB-first**（整数低位先出，字节内低位对齐）。177 卷说 MSB-first，**错**。
2. `W_TAG` = 5 位，值 = `clamp(n, 0, 31)` —— 177 卷这条**对**。
3. item 的 21 段条件 = `([item+8] | [item+0xC]) != 0`，即"两个指针任一非空"。

---

## §1 位序推导（掩码法）

### 1.1 `0xB777C0` 的掩码生成（`0xB77810..0xB77863`）

```asm
0xB77810  mov  eax, [esi+0x14]   ; offset = 当前位位置
0xB77813  and  eax, 7            ;   offset % 8
0xB77816  mov  edi, 8
0xB7781B  sub  edi, eax          ; edi = 8 - (offset%8)
0xB7781D  mov  [ebp-0x1c], eax   ; 保存 offset%8
...
; 目标字节要保留的位算出来：
0xB77832  or   dl, 0xFF          ; dl = 0xFF
0xB77835  shl  dl, cl            ; cl = k + (offset%8)
0xB77839  mov  eax, 0xFF
0xB7783E  sar  eax, cl           ; al = 0xFF >> (8 - offset%8)
0xB77844  or   dl, al            ; ★ dl = (0xFF << (k+off)) | (0xFF >> (8-off))
```

### 1.2 代入验证（offset = 0，k = 5，即写一个 5 位字段到空流）

```
cl  = 5 + 0 = 5
dl  = (0xFF << 5) | (0xFF >> 8)
    = 0xE0 | 0x00
    = 0xE0
```

`0xE0` = `1110_0000`，**保留 bit5..bit7**。

后面 `0xB7789D shl al, cl`（`cl = offset%8 = 0`）→ 数据不右移，直接落在 **bit0..bit4**。

### 1.3 自洽性检验

| 假设 | 保留位 | 数据落点 | 是否自洽 |
|---|---|---|---|
| **LSB-first** | `0xE0` = bit5..7 | bit0..4 | ✅ 互不重叠 |
| MSB-first | 应保留 bit0..2 = `0x07` | bit3..7 | ❌ 实测是 `0xE0` |

★ **掩码 `0xE0` 只在"数据占低位、保留高位"时才是正确的。** 若是 MSB-first（数据占高位），掩码应该是 `0x07`。

### 1.4 源方向也一致

```asm
0xB7785E  mov ecx, eax
0xB77860  shr eax, 3             ; 字节索引 = 位索引 >> 3
0xB77868  mov al, [edi + eax]     ; 取源字节
0xB7786B  and ecx, 7               ; 位在字节内的偏移
0xB7788C  shr al, cl               ; ★ 右移到低位
```

**整数按小端取值 + 右移到低位** ⇒ 整数的低比特先写。**LSB-first。**

---

## §2 item 的 21 段条件

### 2.1 源码（写侧 `0x6255AC..0x6255FA`）

```asm
0x6255AC  mov eax, [edi+8]        ; ★ 指针 A
0x6255AF  mov [esp+0x28], eax
0x6255B3  mov edi, [edi+0xC]      ; ★ 指针 B
0x6255B6  or  eax, edi            ; ★ A | B
0x6255B8  mov [esp+0x2c], edi
0x6255BC  je  0x6255C2            ; 两个都为空 → bl = 0
0x6255BE  mov bl, 1
...
0x6255F2  mov ecx, [esp+0x28]     ; A
0x6255F6  or  ecx, [esp+0x2c]     ; A | B
0x6255FA  je  0x625615            ; ★ 都空 → 跳过 21+64 段
0x6255FE  push 0x15               ; W_TAG(21)
0x625607  push 0x40               ; W_VAL(64 位)
```

★★ **21 段（+ 64 位值）仅在 `[item+8] | [item+0xC]` 非零时才写。**
`[+8]` / `[+0xC]` 是 item 对象里的**两个指针**。

### 2.2 读侧对应

```asm
0x6257B1  mov esi, [edi]
0x6257B3  push 0x15 / call 0xB774E0    ; R_TAG(21)
0x6257BC  push 0x40 / call 0xB772E0    ; R_VAL(64)
```

读侧在 `cmp byte [esp+0x12], 0 / setne al` 之后才读 21 段 —— **读侧判断的是"前面某个存在位"**。
两侧逻辑一致：**有 64 位附加值才写/读 21 段。**

---

## §3 代码落地：R18

`build_manifold` 的打包改为：

```python
def wb(val, n):
    v = (val or 0) & ((1 << n) - 1)
    for k in range(n):                  # ★ 低位先出
        bits.append((v >> k) & 1)

# 打包：bit k 落到 byte[k//8] 的 bit(k%8)
out = bytearray((len(bits) + 7) // 8)
for k, b in enumerate(bits):
    if b:
        out[k >> 3] |= 1 << (k & 7)
```

### 3.1 位级对账（`verify8.py` ALL PASS）

| 输入 | 输出 | 字节 |
|---|---|---|
| `(0, ())` | `03 00 01 00 00 00 00` | 7 |
| `(0x10, (b"\x01\x02",))` | `03 02 05 00 00 00 84 13 09 00 00 00 04 08 00` | 15 |

逐位断言全过：
```
W_TAG(3)=3 @bit0:5 / type=0 @bit5:13 / W_TAG(8)=8 @bit13:18 / count=0 @bit18:50
item: W_TAG(1)=1 / 有值=1 / W_TAG(19)=19 / W_TAG(8)=8 / len=2 / payload 01 02
```

★ **注意 `count=0` 现在是 `03 00 01 00 ...`**（177 卷的 MSB 版是 `18 02 00 ...`）。两者都能被"读到 tag=3 / tag=8"，但 LSB 版才是掩码推导的结果。

---

## §4 诚实的证据强度

| 结论 | 强度 | 依据 |
|---|---|---|
| 位序 LSB-first | **中强** | 掩码 `0xE0` 推导 + 源方向 + 自洽 |
| W_TAG 5 位 clamp(0,31) | **强** | `push 0x1F` 钳位 + 读侧 bool |
| 21 段条件 = `[+8]\|[+0xC]` | **强** | 源码 `or` + `je` 直接可读 |
| 整体字节序列 | **中** | 无真实 6/5 位流样本可对账 |

★★ **仍然没有真实样本。** 所有 run 的 6/5 应答都是"对象=0"。
`10 08 40 00 00` 那个"5 字节 body"来自 `kit_E8_OK_20261029` 自己写的
`build_ready()`（伪代码 `w.write(msg_type,8); w.write(subtype,3); ...`），
**是服务端自造，不是客户端真实数据** —— 用它验证会得到错误结论（我试过，两个模型都对不上，正因为它是错的）。

★ 这一条很重要：**"日志里有字节"不等于"客户端发/收过这些字节"。** 必须区分"服务端自造"与"客户端原始"。

---

## §5 方法论

1. **★★★ 位序要从「掩码生成式」推，不要从"看起来像"猜。** `dl = (0xFF << (k+off)) | (0xFF >> (8-off))` 代入 offset=0、k=5 得 `0xE0`，直接判定 LSB-first。
2. **★★ 自洽性检验：保留位与数据位不能重叠。** `0xE0` 保留高位 ⇒ 数据必在低位。
3. **★★★ "日志里的字节"要分清来源。** `10 08 40 00 00` 是服务端 `build_ready()` 自造常量，不是客户端数据。用它当"第一权威"会得出完全错误的结论。
4. **★★ 更正要连带修所有基于旧结论的验证脚本。** R18 之后 `verify4` 里 3 条 MSB 断言全部失效，必须同步改。
