# 学习报告 049 — capstone：vtable 定案 + P4 函数入口

**方法**：读 vtable 内容 + 搜索函数序言 + 反汇编两个新发现的方法
**性质**：权威反汇编
**★★★ 本报告发现 vtable 后紧跟的是**地图名字符串**，而非纯函数表**

---

## 一、★★★ vtable @ `0xDE6814` 的真实内容（实测）

```
vtable[ 0] = 0x00C77130        ← ★ 析构函数（报告 048 的 vtable[0]）
vtable[ 1] = 0x008038B0        ← ★ 第二个虚函数
vtable[ 2] = 0xFFFFFFFC        ← -4
vtable[ 3] = 0x0000004C        ← 76
vtable[ 4] = 0xFFFFFFFC        ← -4
vtable[ 5] = 0x00000060        ← 96
vtable[ 6] = 0xFFFFFFFC
vtable[ 7] = 0x0000006C        ← 108
vtable[ 8] = 0xFFFFFFFC
vtable[ 9] = 0x00000058        ← 88
vtable[10] = 0x4955504D        ← ★★★ ASCII "MPUI"
vtable[11] = 0x434C445F        ← "DCL_"  （"CLD_"? 小端 = "_DLC"...）
vtable[12] = 0x414E5F36        ← "6_NA"
vtable[13] = 0x0000454D        ← "ME\0\0"
vtable[14] = 0x36636C64        ← "dlc6"
vtable[15] = 0x00000000
```

### ★★★ 字符串解码（小端）

```
0x4955504D → 4D 50 55 49 → "MPUI"
0x434C445F → 5F 44 4C 43 → "_DLC"
0x414E5F36 → 36 5F 4E 41 → "6_NA"
0x0000454D → 4D 45 00 00 → "ME"
0x36636C64 → 64 6C 63 36 → "dlc6"
```

连贯：**`"MPUI_DLC6_NAME"`** + 后面 `"dlc6"`

★★★ **⇒ vtable[10] 之后**不是函数指针**，是**字符串**！**

★★ **⇒ vtable[0..9] 只有 **10 个条目**（0.5 个函数表 + 一些结构）。**

★★★ **`"MPUI_DLC6_NAME"` 是** DLC6 的 UI 名称本地化 key**。**

★★ **⇒ 这个对象与**DLC6（可能是某个内容包）**相关，不是 LSG 连接对象！**

---

## 二、★★★ 修正报告 048：`0xDE6814` 不是 svc 的 vtable

### 重新审视 `0x80387B`

```asm
00803874  8b0d74972608      mov ecx, [0x8269774]     ← svc
0080387A  50                push eax                 ← 另一个对象
0080387B  c7001468de00      mov dword ptr [eax], 0xDE6814   ← ★ eax 的 vtable
```

★★★ **`mov dword ptr [eax], 0xDE6814` 中 `eax` 是 `push` 进去的那个对象，
不是 svc（`ecx`）。**

★★ **⇒ `0xDE6814` 是**被 push 的子对象**的 vtable，不是 svc 的。**

★★★ **⇒ **报告 048 的 "svc vtable = 0xDE6814" 结论错误**。**

★ **svc 的真实 vtable 需要另找（`0x80384C` 的构造函数 `0xB82130` 里）。**

---

## 三、★★★ `0xB7A400` —— 4 字节的 setter

```asm
00B7A400  55              push ebp
00B7A401  8bec            mov  ebp, esp
00B7A403  8b4508          mov  eax, [ebp + 8]
00B7A406  8981f0040000    mov  [ecx + 0x4F0], eax    ← ★★★ 写 +0x4F0
00B7A40C  5d              pop  ebp
00B7A40D  c20400          ret  4
```

★★★ **`0xB7A400(this=ecx, value) { this->field_0x4F0 = value; }`**

★★ **`0x4F0` 紧邻 `0x4F4`（记忆里的 sub 偏移）** ——
**`+0x4F0` 是一个字段，`+0x4F4` 是**下一个**字段。**

★★★ **⇒ 这确认了 `svc` 在 `+0x4F0` 区有连续字段：**
```
+0x4F0   ← 0xB7A400 写（配置值）
+0x4F4   ← 记忆里的 "sub"（其实是同一个对象的下一个字段）
```

★★ **⇒ **记忆里"sub = [svc+1268]"可能理解错了**：
`svc + 0x4F4` 是**同一个对象的字段**，不是"取指针"，
除非 `+0x4F4` 存的是指针。**

★ **从报告 048 的 10 次 `mov ecx, [ecx+0x4f4]` 看，`+0x4F4` **确实存指针**。**

★★★ **⇒ 所以是：`svc + 0x4F0` = 值，`svc + 0x4F4` = 指针（sub）。**

### ★ 后续 `0xB7A410`

```asm
00B7A410  8b81b4050000    mov eax, [ecx + 0x5B4]    ← ★ 另一个字段
00B7A416  c3              ret
```

★★ **`0xB7A410(this) { return this->field_0x5B4; }`** —— getter。

★★ **`+0x5B4` 与 `+0x5E8`（state）**相差 `0x34`（52）。**

---

## 四、★★★ P4 函数的**真正入口** `0xBA3BA0`

★★ **我在 `0xBA3900..0xBA3C05` 范围搜 `55 8B EC`，只命中 **`0xBA3BA0`**。**

★★★ **⇒ P4 函数从 `0xBA3BA0` 开始（不是 `0xBA3BC0`）。**

### 已知片段（`0xBA3BC0` 起，报告 045）

```asm
00BA3BC0  lea  edx, [ebp - 0x10]
00BA3BC3  push edx
00BA3BC4  push ecx
00BA3BC5  mov  [ebp - 0x10], ecx
00BA3BC8  mov  ecx, [ebp + 0x10]
00BA3BCB  push ecx
00BA3BCC  push eax
00BA3BCD  call 0xB783C0
```

★★ **`[ebp+0x10]` = 第 4 个参数；`[ebp+0x0C]` = 第 3；`[ebp+8]` = 第 1。**

★ **`ret 0xC` = 3 个参数**（12 字节）**—— 但 `[ebp+0x10]` 是第 4 个（含 `push ebp` 后的偏移）。**

**`ret 0xC` ⇒ 3 参数 ⇒ `[ebp+8]`、`[ebp+0xC]`、`[ebp+0x10]` ✓**

---

## 五、★★★ `0x74C300` —— 带 `0x30000` 标志检查的初始化

```asm
0074C300  55              push ebp
0074C301  8bec            mov  ebp, esp
0074C303  53              push ebx
0074C304  8a5d08          mov  bl, byte ptr [ebp + 8]     ← ★ 参数是 byte
0074C307  56              push esi
0074C308  57              push edi
0074C309  68f0531a08      push 0x81A53F0                  ← 临界区
0074C30E  ff159c81ca00    call dword ptr [0xCA819C]       ← EnterCriticalSection
0074C314  be8ce89d07      mov  esi, 0x79DE88C             ← ★ 表地址
0074C319  bf08000000      mov  edi, 8
0074C320  f746fc00000300  test dword ptr [esi - 4], 0x30000  ← ★ 标志检查
0074C327  743e            je   0x74C367
0074C329  8b06            mov  eax, [esi]
0074C32B  8b0d24c58907    mov  ecx, [0x789C524]
0074C331  8d0480          lea  eax, [eax + eax*4]
0074C334  845c8102        test byte ptr [ecx + eax*4 + 2], bl
0074C338  8d0481          lea  eax, [ecx + eax*4]
```

★★ **`0x74C300(byte flag)` 遍历一个表（`0x79DE88C`），
检查 `[esi-4] & 0x30000`。**

★★★ **⇒ `0x30000` 可能是 `LIVE`/`CONNECTED` 标志位。**

★ **这不是"启动 LSG"，是**遍历并筛选某些对象**。**

★★ **⇒ 报告 048 的"可能是 LSG 启动"推测**不成立**。**

---

## 六、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | `0xDE6814` 前 2 项 | `0xC77130` / `0x8038B0` |
| 2 | `0xDE6814` 第 3-10 项 | `-4, 0x4C, -4, 0x60, -4, 0x6C, -4, 0x58` |
| 3 | `0xDE6814` 第 10 项起 | ★★★ **`"MPUI_DLC6_NAME"`** 字符串 |
| 4 | **修正** | `0xDE6814` **不是** svc 的 vtable |
| 5 | `0xB7A400` | `this->field_0x4F0 = value`（4 字节 setter） |
| 6 | `0xB7A410` | `return this->field_0x5B4`（getter） |
| 7 | P4 函数入口 | **`0xBA3BA0`**（唯一 `55 8B EC`） |
| 8 | P4 参数个数 | **3**（`ret 0xC`） |
| 9 | `0x74C300` | 遍历表 + `test [esi-4], 0x30000` |
| 10 | `0x74C300` 参数 | `byte`（不是 int） |

---

## 七、结论

### 1. ★★★ 撤销报告 048 的"svc vtable = 0xDE6814"

★★ **实际是**被 push 的子对象**的 vtable，与 `"MPUI_DLC6_NAME"` 相关。**

### 2. ★★★ `+0x4F0` 是值字段，`+0x4F4` 是指针字段

★★ **`0xB7A400` 写 `+0x4F0`，报告 048 的链式访问是 `+0x4F4`（指针）。**

★ **两者相邻，是**同一个对象的连续字段**。**

### 3. ★★★ P4 函数入口 `0xBA3BA0`（3 参数）

### 4. ★★ `0x74C300` 不是 LSG 启动，是表遍历

★ **`0x30000` 是某种状态位掩码。**

### 5. ★★★ `MPUI_DLC6_NAME` 揭示了一个未注意的子系统

★★ **vtable 之后跟的是**DLC6 的 UI 名称本地化 key**。**
**⇒ 这个对象是 **DLC 内容包管理器**，不是 LSG 连接。**

---

## 八、待用 capstone 继续（★ 优先级）

- [ ] ★★★ **反汇编 `0xBA3BA0`（P4 函数的真正开头）**
- [ ] ★★★ **反汇编 `0xB82130`（svc 构造函数）→ 找真 vtable**
- [ ] ★★ **反汇编 `0xC77130`（`0xDE6814` 的 `vtable[0]`）**
- [ ] ★★ **`0x79DE88C` 表的内容**
- [ ] ★ **`0x789C524` 全局**
- [ ] ★ **`MPUI_DLC6_NAME` 的完整字符串布局**
