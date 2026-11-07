# 对局内 codec 语义（0x6701D0 全分支实测）

> 证据：`run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin`
> 反汇编：`docs\_6701D0.txt`（0x6701D0–0x670CAF，1067 条）
> 辅助函数已单独反汇编：0x66F060 / 0x66FCF0 / 0x66FC40 / 0x66FE90 / 0x66FE30 / 0x66EE10 / 0x66EE60

---

## 1. 读位原语

| 函数 | 语义 |
|---|---|
| `0x447190` | 读 1 bit，返回 0/1；越界返回 -1 |
| `0x66EC30(n)` | 读 n bit，LSB-first |
| `0x66ED70` | 对齐到字节边界，返回字节位置 |
| `0x66EE10` | 读 4 字节（32 位原样） |
| `0x66EE60` | 读 4 字节并按 float 解释；`0xFFFFFFFF` → 标记 overflow 并返回常量 |
| `0x66FE30(bits)` | 读 `bits` 位并做**符号扩展**（`0x66FD90` 是底层变长读） |
| `0x66FD90(n)` | 读 n bit（支持 >32 位，逐字节拼） |

---

## 2. 已确认的 codec（对局 6 张表实际用到的）

### 2.1 `bits > 0` —— 整数

```
1 bit  changed
  0 -> value = 0
  1 -> value = ReadBits(bits) ^ from
```
（`0x670AF2` → `0x670B15`，`0x66FE30` 负责符号扩展）

### 2.2 `bits == 0` —— float（0x67020D）

```
1 bit
  0 -> 1 bit b; value = b << 31        (±0.0)
  1 -> 1 bit
        1 -> 32 bit raw ^ from
        0 -> 5 bit + 5 bit             (压缩浮点, 待定公式)
```

### 2.3 `-55`（0x670983）—— 4 字节直拷

```
1 bit
  1 -> memcpy(dst, src_from, 4); dst[3] = (src_from[3] != 0) - 1
  0 -> 走默认 changed 路径
```

### 2.4 `-56`（0x67094D）—— 定点小数

```
6 bit n
value = n / 10.0 + 0.5
```
（`fdiv [0xDE7E08]=10.0`，`fadd [0xDE7C50]=0.0`；0xDE7C50 实为 0）

### 2.5 `-57`（0x67092E → 0x66F060）—— 16 位角度

```
2 字节有符号 (movsx)
value = n * 0.0054931640625          ; = 360/65536
```
即 `angle_deg = int16 * 360 / 65536`。

### 2.6 `-58`（0x6708BF → 0x66FE90，常量 10.0）—— 小角度

```
1 bit
  1 -> 0x66EE60  (4 字节 float；0xFFFFFFFF 视为 overflow)
  0 -> 2 bit n
       value = n * (n + 10) * 1.52587890625e-05    [公式待精确复核]
```
用于 entityState[0]（offset 0x4C）。

### 2.7 `-75`（0x6703FC）—— 3 段式

```
1 bit
  1 -> 4 bit + 4 bit  (两段小值)
  0 -> 转 0x66F9E0
```

### 2.8 `-77 / -91 / -92`（0x670B82 / 0x6707B6 → 0x66FC40）—— 16 位角度 + 基准

```
1 bit
  0 -> 7 bit n; value = (n - 0x40) + from
  1 -> 16 bit; value = 0x8000 + (from - from_base) ^ read  [待精确复核]
```
`0x66FC40` 内对 `-0x5C`(-92) / `-0x53`(-83) 有特判，取不同全局基准。

### 2.9 `-78 / -80 / -88`（0x670BA5 / 0x6704E3 → 0x66EE10）—— 32 位原样

```
4 字节原样（-88 额外与 from 异或）
```

### 2.10 `-81 / -82 / -83`（0x67085E / 0x67080A / 0x6707B6）—— 掩码异或

```
按 codec 选全局掩码：-83→0xE51A84, -82→0xE51B1C, -81→0xE51B20
value = (read ^ ~mask ^ ptr) ...  [与 0x670BDC 组同族]
```

### 2.11 `-90`（0x670790 → 0x66FCF0）—— 16 位角度（固定基准）

```
1 bit
  0 -> 7 bit n; value = (n - 0x40) + from
  1 -> 16 bit; value = 0x8000 + (from - const) ^ read
```
`const` = `[0xC7AF6D0]`。

### 2.12 `-94`（0x670EF4）—— 8 字节原样

```
memcpy(dst, src, 8)   ; 0x769710
```

### 2.13 `-97`（0x670BBF → 0x66F9E0）—— 带 time 的 32 位

```
1 bit
  0 -> 8 bit delta; value = from - delta
  1 -> 4 字节原样
```
`0x66F9E0(edi=from, esi=msg)`。

### 2.14 `-98`（0x670679 → 0x66FC00）—— 1+30 或 1+5+变长

```
1 bit
  1 -> 30 bit
  0 -> 5 bit n; 然后按 n 决定后续位数  [0x66FC00 后续]
```

### 2.15 `-99`（0x6705C9）—— 1 bit 双分支

```
1 bit
  0 -> value = 0
  1 -> 1 bit 再分支
```

### 2.16 `-100`（0x670B5B → 0x66FEE0）—— 压缩浮点

```
1 bit
  0 -> 5 bit exponent + 5 bit mantissa
  1 -> 16 bit + 8 bit
```
用于 entityState[1]/[2]/[7]。

### 2.17 `-101`（0x6702B0）—— float → int A

```
1 bit
  1 -> 4 字节 float，转 int
  0 -> 1 bit; 1 -> 6 bit; 0 -> 6 bit 再定
```

### 2.18 `-102`（0x67033D）—— float → int B

```
1 bit
  1 -> 4 字节 float，转 int
  0 -> 1 bit; 1 -> 31 bit
```

---

## 3. 6 张表用到的 codec 汇总

| 表 | codec 集合 |
|---|---|
| playerState `0xDA8078` | 无（全是正位宽 + 36 个 bits==0） |
| entityState `0xDA63E8` | -57 ×3, -58 ×1, -97 ×2, -100 ×3 |
| struct3 `0xDA90A8` | -57 ×1, -97 ×1 |
| arrayElem `0xDA4608` | -55,-71,-72,-73,-74,-75,-77,-78,-79,-80,-81,-82,-83,-93,-94,-96,-97,-98 |
| subStruct `0xDA9138` | -65,-85,-86,-90,-91,-92,-97,-99 |
| bigStruct `0xDA8520` | -8,-16,-55,-57,-70,-75,-87,-88,-90,-91,-92,-94,-97,-98,-100,-101,-102 |

---

## 4. 仍待精确复核

| codec | 问题 |
|---|---|
| -8 | 出现在 bigStruct 4 次，未在 0x6701D0 分支表里出现 → 可能是 change_hint 而非 codec，需复核 |
| -16 | bigStruct 9 次，同上 |
| -58 | 小角度二次公式需逐指令复核 |
| -81/-82/-83 | 与 -40 组共享 0x670BDC，掩码运算顺序需复核 |
| -77/-91/-92 | 0x66FC40 的 `from_base` 来源需确认 |
---

## 5. 更正（2026-10-22 追加）

`0x6701D0` 的 `cmp ecx,<imm8>` 分支全集已穷举，共 **45 个 codec**：

```
-64 -63 -62 -101 -102 -80 -78 -75 -89 -88 -61 -60 -59 -99 -65 -98 -97
-74 -73 -72 -71 -70 -96 -93 -95 -94 -90 -83 -82 -81 -100 -79 -58 -57
-56 -87 -86 -85 -84 -76 -69 -55
```

**没有 `-8` / `-16` 分支**。因此：

- `bigStruct 0xDA8520` 里出现的 `bits=-8`(4 处) / `bits=-16`(9 处)
  **不是 codec**，而是把 `change_hint` 列误当成 `bits` 读出来的结果。
  该表的条目布局需要重新按列解析（可能 hint 与 bits 列顺序与其它表不同）。

- 同理，`arrayElem 0xDA4608` 里的 `-71/-72/-73/-74/-79/-80/-93/-96`
  是**真实 codec**（在 45 个分支内），但 `bigStruct` 的 `-8/-16` 不是。

修正方式：对 `0xDA8520` 重新按 `{offset, hint, bits}` 或 `{offset, bits, hint}`
两种列序各解析一遍，取「所有 bits 都落在 45 个已知 codec ∪ 正位宽 ∪ 0」的那一种。

---

## 6. 关键修正：负 bits 的两种含义

0x6701D0 默认分支：

    00670B15  call 0x447190          ; changed bit
    00670B1E  je   0x670B20          ; 0 -> value = 0
    00670B37  mov eax,[ebp-0x14]
    00670B3A  mov eax,[eax+4]        ; eax = entry->bits  (可为负)
    00670B40  call 0x66FE30          ; 读 abs(bits) 位 + 符号扩展

0x66FE30：

    0066FE39  test esi,esi
    0066FE3B  sets bl                ; bl = (bits < 0)
    0066FE42  neg esi                ; n = abs(bits)
    0066FE45  call 0x66FD90          ; 读 n 位
    0066FE68  xor eax,ecx            ; ^ from
    0066FE6E  ... 若 bl 且最高位=1 -> 符号扩展

结论：

| bits | 含义 |
|---|---|
| > 0 | 无符号整数，宽度 = bits |
| == 0 | 不发送 |
| < 0 且命中 45 个 codec 之一 | 该 codec 专用编码 |
| < 0 且不在 codec 表里 | 有符号整数，宽度 = abs(bits) |

所以 bigStruct 0xDA8520 的 -8 = int8、-16 = int16（共 13 处）；
arrayElem / subStruct 里的 -91/-92/-77 仍是真 codec。



---

## 7. 已实现并通过自校验的部分（tools/codol_codec.py）

| 项 | 状态 |
|---|---|
| index varint (0x670CB0) 双向 | PASS 6 张表 x 43 run 值 |
| bits>0 无符号整数 | PASS |
| bits<0 非 codec = 有符号整数（含符号扩展） | PASS |
| bits==0 = float codec（1bit 存在 + 1bit 符号/32bit 异或） | PASS 288 例 |
| playerState 整结构 delta 往返 | PASS 30 例 |

未实现（下一步）：
- codec -57 / -58 / -97 / -100 / -101 / -102 的精确公式
- 其余 39 个 codec

## 8. 2026-10-23 run 编码收口

写入器已不再把 run 固定为 4 位。`src/battle/snapshot.c` 现在按表宽计算
`indexBits`：playerState(87) 为 7，entityState(24) 为 5，struct3(9) 为 4；
`run=1` 写单 bit 1，否则写 0 后按 `indexBits` 写 mask 分块。
位级回归位于 `tests/test_snapshot_run.c`。

现有 141B 黄金向量不覆盖旧的固定 4 位错误，因此不能把“黄金向量一致”
提升为完整 codec 证据。历史 124B 向量的写侧冲突仍保持 `PARTIAL`。
