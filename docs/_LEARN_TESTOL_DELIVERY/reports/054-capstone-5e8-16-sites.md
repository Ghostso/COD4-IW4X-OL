# 学习报告 054 — capstone 全 opcode 扫描：`0x5E8` 的 16 处访问（含 state=1）

**方法**：全 opcode 扫描（`89`/`C7`/`8B`/`8D`/`FF`/`D9`/`D8`/`D9`/`88`/`83`）+ capstone 回解
**性质**：权威反汇编
**★★★ 本报告补全了 `state = 1` 的写入点，并发现 `+0x5E8` 被**多个不同类**共用**

---

## 一、★★★ 全部 16 处访问（实测）

```
00598361  8b81e8050000    mov  eax, [ecx + 0x5e8]      ← 读
006E1246  89bee8050000    mov  [esi + 0x5e8], edi       ← 写（构造 A）
006F42FB  899ee8050000    mov  [esi + 0x5e8], ebx       ← 写（构造 B）
00872AEE  d986e8050000    fld  dword [esi + 0x5e8]      ← ★★★ 浮点读！
008736CC  d99ee8050000    fstp dword [esi + 0x5e8]      ← ★★★ 浮点写！
00873C5A  d99ee8050000    fstp dword [esi + 0x5e8]      ← ★★★ 浮点写
00873D87  d996e8050000    fst  dword [esi + 0x5e8]      ← ★★★ 浮点读
008743E0  d986e8050000    fld  dword [esi + 0x5e8]      ← ★★★ 浮点读
00B824AC  889ee8050000    mov  byte [esi + 0x5e8], bl   ← ★★ 1 字节写！
00B83920  c686e805000001  mov  byte [esi + 0x5e8], 1    ← ★★★ state = 1（字节）
00BA07A6  83b9e805000003  cmp  dword [ecx + 0x5e8], 3    ← 比较 == 3
00BA2984  899ee8050000    mov  [esi + 0x5e8], ebx       ← 写（构造 C）
00BA2B6A  83bbe805000003  cmp  dword [ebx + 0x5e8], 3    ← 比较 == 3
00BA3251  00c7            add  bh, al                  ← 假命中
00BA34E6  83bee805000003  cmp  dword [esi + 0x5e8], 3    ← 比较 == 3
00BA44E8  8b86e8050000    mov  eax, [esi + 0x5e8]      ← 读（消息分派）
```

★★★ **⇒ 真实 15 处，按类型分：**

| 类型 | 数量 | 地址 |
|---|---|---|
| dword 读 | 3 | `0x598361` / `0xBA44E8` / （`0xBA07A6` 是比较） |
| dword 写 | 3 | `0x6E1246` / `0x6F42FB` / `0xBA2984` |
| dword 比较 ==3 | 3 | `0xBA07A6` / `0xBA2B6A` / `0xBA34E6` |
| **浮点读写** | **5** | `0x872AEE` / `0x8736CC` / `0x873C5A` / `0x873D87` / `0x8743E0` |
| **字节写** | **2** | `0xB824AC` / **`0xB83920`** |
| 立即数写（`C7 86`） | 2 | `0xBA3460`（=0）/ `0xBA3C47`（=3） |
| 假命中 | 1 | `0xBA3251` |

★★★ **⇒ **`0x5E8` 被**多个不同的类**共用：**
- `0x6Exxxx` / `0x87xxxx` / `0xB8xxxx` / `0xBAxxxx` 四个区域
- **有的把它当 dword，有的当 float，有的当 byte**

★★★ **⇒ 这不是一个字段，而是**多个对象各自的 `+0x5E8`**！**

---

## 二、★★★ 关键修正：`0x5E8` 不是唯一字段

### 证据

```
0x6Exxxx:  dword 写（构造 A）
0x6Fxxxx:  dword 写（构造 B）
0x87xxxx:  float 读写（★ 完全不同的语义！）
0xB8xxxx:  byte 写（★ 3 字节？）
0xBAxxxx:  dword 写/读/比较（P4 族）
```

★★★ **⇒ `[X + 0x5E8]` 在不同对象里有**完全不同的类型和语义**。**

★★ **⇒ 只有当 `X` 是同一个 svc 对象时，它们才指同一个字段。**

★★★ **⇒ 记忆里的 `5E8=3` 只能对应 `0xBAxxxx` 族**（因为 P4 写 3）。

---

## 三、★★★ `0xB83920` —— state = 1 的写入点

```asm
00B83920  c686e805000001   mov  byte ptr [esi + 0x5e8], 1   ← ★★★ 字节写 1
```

★★ **是 **`byte` 写**，不是 dword。**

★★★ **⇒ `0xB8xxxx` 族的 `+0x5E8` 是一个**字节字段**，与 `0xBAxxxx` 族的 **dword 字段**不同。**

★ **但要注意：小端下，写 byte 1 到 `[+0x5E8]` 会让 dword 变成 `0x00000001`（如果高 3 字节是 0）。**

★★★ **⇒ 如果**构造函数清空了高 3 字节**，那 byte 写 1 就等于 dword 写 1。**
**⇒ **可能是同一个字段的两种写法**（编译器优化）。**

★ **需要看 `0xB824AC` 和 `0xB83920` 的上下文。**

---

## 四、★★★ 三个 `cmp == 3` 的位置（重要）

```
0xBA07A6  cmp dword [ecx + 0x5e8], 3
0xBA2B6A  cmp dword [ebx + 0x5e8], 3
0xBA34E6  cmp dword [esi + 0x5e8], 3
```

★★★ **⇒ 有三个地方在检查"state == 3（已连接）"。**

★★ **全在 `0xBAxxxx` 族** —— **确认 `0xBAxxxx` 是 LSG 相关代码。**

★ **`0xBA34E6` 在 `0xBA3420`（清理）附近 —— 是**清理前的检查**（"如果已连接，则..."）。**

---

## 五、★★ 五个浮点读写（`0x87xxxx`）

```
0x872AEE  fld  dword [esi + 0x5e8]
0x8736CC  fstp dword [esi + 0x5e8]
0x873C5A  fstp dword [esi + 0x5e8]
0x873D87  fst  dword [esi + 0x5e8]
0x8743E0  fld  dword [esi + 0x5e8]
```

★★★ **⇒ `0x87xxxx` 族把 `+0x5E8` 当 **float**（可能是某个物理/动画参数）。**

★ **⇒ **完全不同的类**（可能是 `cg_t` / 视角状态之类）。**

★★ **⇒ 这证实了 `+0x5E8` 是**通用偏移**，在多类中各有含义。**

---

## 六、逐字节证据总表

| # | 地址 | 指令 | 类型 |
|---|---|---|---|
| 1 | `0x598361` | `mov eax,[ecx+0x5e8]` | dword 读 |
| 2 | `0x6E1246` | `mov [esi+0x5e8],edi` | dword 写（构造） |
| 3 | `0x6F42FB` | `mov [esi+0x5e8],ebx` | dword 写（构造） |
| 4 | `0x872AEE` | `fld dword [esi+0x5e8]` | ★ float 读 |
| 5 | `0x8736CC` | `fstp [esi+0x5e8]` | ★ float 写 |
| 6 | `0x873C5A` | `fstp [esi+0x5e8]` | ★ float 写 |
| 7 | `0x873D87` | `fst [esi+0x5e8]` | ★ float 读 |
| 8 | `0x8743E0` | `fld dword [esi+0x5e8]` | ★ float 读 |
| 9 | `0xB824AC` | `mov byte [esi+0x5e8],bl` | ★ 字节写 |
| 10 | **`0xB83920`** | **`mov byte [esi+0x5e8],1`** | ★★★ **state = 1** |
| 11 | `0xBA07A6` | `cmp [ecx+0x5e8],3` | 比较 |
| 12 | `0xBA2984` | `mov [esi+0x5e8],ebx` | dword 写（构造） |
| 13 | `0xBA2B6A` | `cmp [ebx+0x5e8],3` | 比较 |
| 14 | `0xBA34E6` | `cmp [esi+0x5e8],3` | 比较 |
| 15 | `0xBA44E8` | `mov eax,[esi+0x5e8]` | dword 读 |
| 16 | `0xBA3460` | `mov dword [esi+0x5e8],0` | 立即数写 0 |
| 17 | `0xBA3C47` | `mov dword [esi+0x5e8],3` | 立即数写 3 |

---

## 七、结论

### 1. ★★★ 修正报告 052：`0x5E8` **不是唯一字段**

★★★ **⇒ `+0x5E8` 在 4 个不同区域（`0x6Ex`/`0x87x`/`0xB8x`/`0xBAx`）有不同语义：**
```
dword（0x6Ex/0xBAx）
float（0x87x）
byte （0xB8x）
```

### 2. ★★★ 真正的 LSG state 是 `0xBAxxxx` 族（dword）

★★ **证据：3 处 `cmp [..+0x5e8], 3` 全在 `0xBAxxxx`。**

### 3. ★★★ 找到了 state = 1 的写入点：`0xB83920`

★★ **但它是 `byte` 写 —— 可能是同一字段的优化写法，需要上下文确认。**

### 4. ★★ `0xC8` 与 `0x5E8` 的对比

```
0xC8   通用偏移，40+ 处，无法穷举
0x5E8  也不唯一，但 4 个区域可分组
```

★★★ **⇒ 精确定位必须靠 **svc 指针（`0x8269774`）** + **同族地址范围**。**

---

## 八、待用 capstone 继续（★ 优先级）

- [ ] ★★★ **反汇编 `0xB83920` 的上下文（确认是不是 LSG state）**
- [ ] ★★★ **反汇编 `0xBA07A6` / `0xBA2B6A` / `0xBA34E6`（三处 `cmp ==3`）**
- [ ] ★★ **反汇编 `0x6E1226` 的函数入口**（判断构造的是哪个类）
- [ ] ★★ **反汇编 `0x872AEE` 的上下文（float 语义）**
- [ ] ★ **`0x598361` 的类型**
- [ ] ★ **确认 `0xB824AC` 与 `0xB83920` 是否同一字段**
