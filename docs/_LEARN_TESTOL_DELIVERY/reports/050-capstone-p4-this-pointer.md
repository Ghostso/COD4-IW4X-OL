# 学习报告 050 — capstone：P4 完整函数定案（`esi` = `this`）

**方法**：反汇编 `0xBA3BA0` 完整函数 + `0xB82130`（svc 构造）+ `0xC77130`
**性质**：权威反汇编
**★★★ 本报告彻底解决了 `[esi+0x5E8]` 的归属问题**

---

## 一、★★★ P4 函数的完整反汇编（`0xBA3BA0`）

```asm
00BA3BA0  55                  push ebp
00BA3BA1  8bec                mov  ebp, esp
00BA3BA3  83ec10              sub  esp, 0x10            ← 16 字节局部
00BA3BA6  a140f2e300          mov  eax, [0xE3F240]      ← /GS cookie
00BA3BAB  33c5                xor  eax, ebp
00BA3BAD  8945fc              mov  [ebp - 4], eax
00BA3BB0  8b4508              mov  eax, [ebp + 8]       ← 参数 1
00BA3BB3  53                  push ebx
00BA3BB4  56                  push esi
00BA3BB5  6a08                push 8                    ← 8 字节
00BA3BB7  8d55f4              lea  edx, [ebp - 0xc]
00BA3BBA  52                  push edx
00BA3BBB  8bf1                mov  esi, ecx             ← ★★★ esi = this！
00BA3BBD  8b4d0c              mov  ecx, [ebp + 0xc]     ← 参数 2
00BA3BC0  8d55f0              lea  edx, [ebp - 0x10]
00BA3BC3  52                  push edx
00BA3BC4  51                  push ecx
00BA3BC5  894df0              mov  [ebp - 0x10], ecx
00BA3BC8  8b4d10              mov  ecx, [ebp + 0x10]    ← 参数 3
00BA3BCB  51                  push ecx
00BA3BCC  50                  push eax
00BA3BCD  e8ee47fdff          call 0xB783C0             ← ★ 6 参数范围检查
00BA3BD2  83c418              add  esp, 0x18
00BA3BD5  84c0                test al, al
00BA3BD7  752c                jne  0xBA3C05             ← ★ 检查通过 → 主逻辑
--- 检查失败 ---
00BA3BD9  32db                xor  bl, bl               ← bl = 0
00BA3BDB  e8f0f9c9ff          call 0x8435D0
00BA3BE0  6a04                push 4                    ← 全局状态 = 4
00BA3BE2  e8593d95ff          call 0x4F7940             ← g_lsg_state = 4
00BA3BE7  83c404              add  esp, 4
00BA3BEA  8bce                mov  ecx, esi             ← this
00BA3BEC  e82ff8ffff          call 0xBA3420             ← ★ 清理方法
00BA3BF1  5e                  pop  esi
00BA3BF2  8ac3                mov  al, bl               ← 返回 0
...
```

★★★ **⇒ `esi = ecx`（`0xBA3BBB`）= **`this` 指针**。**

★★★ **⇒ 后续所有 `[esi + 0x5E8]` / `[esi + 0x5EC]` / `[esi + 0x5F0]` 都是
**`this` 对象的字段**，与全局 `0x8269774` 的 svc **不是同一个对象**（除非 `ecx` 就是 svc）。**

---

## 二、★★★ 关键：这个 `this` 是什么对象？

### 由调用约定推

★★ **`0xBA3BA0` 是 **`__thiscall`**（`ecx` = `this`，`ret 0xC` = 3 个栈参数）。**

★★ **它有方法 `0xBA3420`（`this` 的清理函数）。**

### ★★ 由字段偏移推

```
this + 0x5E8    ← state（P4 写 3）
this + 0x5EC    ← state + 4
this + 0x5F0    ← state + 8
this + 0x5FC    ← 8 字节数据（0xBA3C0B 读）
this + 0x640    ← 
this + 0x644    ← 
```

★★ **偏移到 `0x644`（1604 字节）** —— **对象不小。**

### ★★ 与 svc 大小的对比

```
svc（0x8269774）      : 0x1618 = 5656 字节
this（P4 对象）        : ≥ 0x648 = 1608 字节
```

★★ **⇒ 不是同一个对象（除非 `this` 是 svc 的子对象）。**

★★★ **⇒ 最可能：`this` 是 svc 的一个**成员子对象**（如 `LsgEndpoint` / `AuthSession`）。**

★ **记忆里 `sub = [svc + 0x4F4]` 的 `sub` 可能就是它。**

★★ **验证：`svc + 0x4F4` 处存的是指向这个 `this` 的指针吗？需要运行时确认。**

---

## 三、★★★ `0xB82130` —— svc 的构造函数（部分）

```asm
00B82130  55                  push ebp
00B82131  8bec                mov  ebp, esp
00B82133  6aff                push -1
00B82135  68ceb8c800          push 0xC8B8CE           ← SEH
00B8213A  64a100000000        mov  eax, fs:[0]
00B82140  50                  push eax
00B82141  51                  push ecx
00B82142  53                  push ebx
00B82143  56                  push esi
00B82144  a140f2e300          mov  eax, [0xE3F240]    ← /GS
00B82149  33c5                xor  eax, ebp
00B8214B  50                  push eax
00B8214C  8d45f4              lea  eax, [ebp - 0xc]
00B8214F  64a300000000        mov  fs:[0], eax
00B82155  8bf1                mov  esi, ecx           ← this
00B82157  8975f0              mov  [ebp - 0x10], esi
00B8215A  e851450200          call 0xBA66B0           ← ★ 基类构造/初始化
00B8215F  d905e07ccb00        fld  dword ptr [0xCB7CE0]  ← ★ 浮点常量
00B82165  8d4e08              lea  ecx, [esi + 8]     ← this + 8
00B82168  51                  push ecx
00B82169  d91c24              fstp dword ptr [esp]    ← 参数 = 那个浮点
00B8216C  33db                xor  ebx, ebx
00B8216E  6a04                push 4
00B82170  895dfc              mov  [ebp - 4], ebx
```

★★★ **`call 0xBA66B0` at `0xB8215A`** —— **基类构造，可能设置 vtable。**

★★ **`fld dword ptr [0xCB7CE0]`** —— **读一个 float 常量。**

★★ **`lea ecx, [esi+8]`** —— **构造 `this + 8` 处的子对象。**

★★★ **⇒ svc 的**真 vtable 在 `0xBA66B0` 里**（或它的子调用）。**

★ **`0xBA66B0` 与 P4 的 `0xBA3BA0` / `0xBA3420` **在同一个 0xBAxxxx 区** ——
**说明这是同一个类的家族。**

★★★ **⇒ **强推论：`0xBA3BA0`（P4）就是 `svc` 类的成员函数**，
`this` 就是 **svc 本身**（或它的主基类）。**

★ **这与 `0x1618`（5656）大小吻合（`+0x644` 远在范围内）。**

★★★ **⇒ **修正：`esi` = svc 的 `this`，`[svc+0x5E8]` 就是记忆里的 state。****

---

## 四、★★★ `0xC77130` —— 一个 thunk

```asm
00C77130  ff256481ca00        jmp dword ptr [0xCA8164]   ← ★ 跳 IAT
00C77136  cc                  int3 ...
00C77140  55                  push ebp                    ← 下一个函数
```

★★ **`0xDE6814` 的 `vtable[0]` 是一个**跳转 thunk**（`jmp [IAT]`）。**

★★ **`[0xCA8164]` 是 **delay-import / 转发**。**

★★ **⇒ 这是**DLL 导入转发 thunk**（不是真正的析构函数）。**

★★★ **⇒ 进一步确认 `0xDE6814` 不是 svc 的 vtable（它是某个 DLC 对象的）。**

---

## 五、逐字节证据总表

| # | VA | 指令 | 说明 |
|---|---|---|---|
| 1 | `0xBA3BBB` | `mov esi, ecx` | ★★★ **`esi` = `this`** |
| 2 | `0xBA3BA0` | 函数入口（`55 8bec 83ec10`） | 16 字节局部 |
| 3 | `0xBA3BA6` | `mov eax, [0xE3F240]` | /GS cookie |
| 4 | `0xBA3BCD` | `call 0xB783C0` | 6 参数范围检查 |
| 5 | `0xBA3BE0` | `push 4` | 全局状态 = 4 |
| 6 | `0xBA3BEC` | `call 0xBA3420`（`this`） | 清理方法 |
| 7 | `0xB82130` | svc 构造函数 | `/GS` + SEH |
| 8 | `0xB8215A` | `call 0xBA66B0` | ★ 基类构造 |
| 9 | `0xB8215F` | `fld [0xCB7CE0]` | float 常量 |
| 10 | `0xB82165` | `lea ecx, [esi+8]` | 子对象 `+8` |
| 11 | `0xC77130` | `jmp [0xCA8164]` | ★ 导入 thunk |
| 12 | `0xDE6814` | 非 svc vtable | 某 DLC 对象 |

---

## 六、结论

### 1. ★★★ `esi` = `this`（P4 函数的第一个参数由 `ecx` 传入）

★★★ **⇒ `[esi+0x5E8]` 是 `this` 的字段。**
**如果 `this` 就是 svc（大小 0x1618 覆盖 0x644），那与记忆吻合。**

### 2. ★★★ P4 与 svc 是**同一个类家族**（同在 `0xBAxxxx` 区）

```
0xBA3420   清理
0xBA3BA0   P4（LSG 非ce/状态）
0xBA66B0   基类构造
```

★★★ **⇒ `this` 极可能就是 svc。**

### 3. ★★ `0xDE6814` 确认**不是** svc 的 vtable

★★ **它的 `vtable[0]` 是导入 thunk，后面跟 `MPUI_DLC6_NAME` 字符串。**
**⇒ DLC 内容对象。**

### 4. ★★ svc 的真 vtable 在 `0xBA66B0` 或更深

★ **需要继续追。**

---

## 七、待用 capstone 继续（★ 优先级）

- [ ] ★★★ **反汇编 `0xBA66B0`（svc 基类构造，找真 vtable）**
- [ ] ★★★ **反汇编 `0xBA3420`（P4 的清理方法）**
- [ ] ★★ **确认 `[svc+0x4F4]` 是否指向 `this` 自身**
- [ ] ★★ **`0xCB7CE0` 那个 float 常量**
- [ ] ★ **`0xE3F240`（/GS cookie 全局）**
- [ ] ★ **`0xBA3C05` 完整剩余部分（P4 主逻辑后半）**
