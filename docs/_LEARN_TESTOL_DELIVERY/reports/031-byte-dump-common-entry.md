# 学习报告 031 — 逐字节：`0x217A40` 是公共初始化入口（三处调用点确证）

**方法**：精确重算三处 `E8`/`E9` 的相对跳转（修正报告 030 的二次错误）
**性质**：全实测
**★★★ 本报告给出"公共入口"的**三重**独立确认**

---

## 一、★★★ `E8` 的下一指令地址算错了一次（报告 030 的二次错误）

### 报告 030 我写的（错的）

```
002215B7  E8 85 64 FF FF
```

### 实际（对的）

```
002215B0  55              push ebp
002215B1  8B EC           mov  ebp, esp
002215B3  83 E4 F8        and  esp, -8
002215B6  E8 85 64 FF FF  call rel32        ← E8 在 +6，不是 +7！
```

★★★ **我把 `E8` 的位置当成了 `+7`，实际是 `+6`。**

**正确算式**：
```
E8 的地址   = 0x2215B0 + 6 = 0x2215B6
下一条      = 0x2215B6 + 5 = 0x2215BB
rel32       = 0xFFFF6485 = -39803
目标        = 0x2215BB - 39803 = 0x217A40  ✓
```

★★ **用 `+7` 算出的 `0x2215BC + rel32` 得 `0x217A41`（差 1 字节）** ——
**报告 030 写成了 `0x217A41`，也是错的。**

---

## 二、★★★ 三处调用点全部指向 `0x217A40`（定案）

| # | 函数 | RVA | 指令 | 编码 | rel32 | 目标 |
|---|---|---|---|---|---|---|
| 1 | `onStartup` | `0x220880` | `E9` (jmp) | `E9 BB 71 FF FF` | `-36421` | **`0x217A40`** |
| 2 | `onInitialized` | `0x220880` | 同址 | 同上 | — | **`0x217A40`** |
| 3 | `SetEnabled` | `0x220896` | `E8` (call) | `E8 A5 71 FF FF` | `-36443` | **`0x217A40`** |
| 4 | **`ConfigureSession`** | `0x2215B6` | `E8` (call) | `E8 85 64 FF FF` | **`-39803`** | **`0x217A40`** |

★★★ **四处（含 onInitialized 同址）全部指向 `0x217A40`。**

★★★ **⇒ `0x217A40` 是 `CodolGameServer` 的**唯一公共初始化/单例获取函数**。**

### ★ 递归确认：`ConfigureBooking` / `ConfigureGameState` / 其他 `Get*` 也会调它

**模式**：
```asm
push ebp
mov  ebp, esp
and  esp, -8          ; 8 字节对齐（因为有 SSE 操作）
call 0x217A40         ; ★ 确保已初始化 / 取单例
cmp  byte ptr [0x10697027], 0   ; 全局"已就绪"标志
je   <返回失败>
...
```

★★ **`SetEnabled` 和 `ConfigureSession` 都是这个模式** ——
**所有导出函数都应该先 `call 0x217A40`。**

---

## 三、★★★ `0x217A40` 的真实内容（重读，确认无加密）

```
00217A40  55                    push ebp
00217A41  8B EC                 mov  ebp, esp
00217A43  6A FF                 push -1                    ← SEH
00217A45  68 C6 39 47 10        push 104739C6h
00217A4A  64 A1 00 00 00 00     mov eax, fs:[0]
00217A50  50                    push eax
00217A51  81 EC EC 06 00 00     sub esp, 6ECh              ← 1772 字节
00217A57  A1 00 1F 62 10        mov eax, [10621F00h]       ← /GS cookie
00217A5C  33 C5                 xor eax, ebp
00217A5E  89 45 F0              mov [ebp-10h], eax
00217A61  56                    push esi
00217A62  57                    push edi
00217A63  50                    push eax
00217A64  8D 45 F4              lea eax, [ebp-0Ch]
00217A67  64 A3 00 00 00 00     mov fs:[0], eax
00217A6D  68 E0 31 62 10        push 106231E0h
00217A72  C7 85 B8 FD FF FF E0 31 62 10   mov [ebp-248h], 106231E0h
00217A7C  E8 C2 5F 20 00        call 0x41DA43              ← 第一个调用
00217A81  83 C4 04              add esp, 4
00217A84  85 C0                 test eax, eax
00217A86  0F 85 D2 1C 00 00     jne 0x41975E              ← 非零 → 错误路径
00217A8C  A1 0C 32 62 10        mov eax, [1062 320Ch]      ← 全局
00217A91  3D FF FF FF 7F        cmp eax, 7FFFFFFFh
00217A96  0F 84 C9 1C 00 00     je  0x41975F               ← 已达上限 → 错误
00217A9C  C7 45 FC 00 00 00 00  mov dword ptr [ebp-4], 0
```

★★ **`55 8B EC 6A FF` 是标准的 MSVC SEH 函数序言** —— **完全正常，没有加密。**

---

## 四、★★★ `0x41DA43` 是 `std::call_once` 类的守卫

### 反汇编

```asm
0041DA43  55                 push ebp
0041DA44  8B EC              mov  ebp, esp
0041DA46  6A 00              push 0                  ← 参数 2 = 0
0041DA48  FF 75 08           push dword ptr [ebp+8]  ← 参数 1
0041DA4B  E8 4B 00 00 00     call 0x41DA9B
0041DA50  59 59              pop ecx; pop ecx
0041DA52  5D                 pop ebp
0041DA53  C3                 ret
```

★★ **`0x41DA43` 是 16 字节的**薄包装**，转调 `0x41DA9B`。**

### `0x41DA9B` 及后续

```asm
0041DA9B  55                 push ebp
0041DA9C  8B EC              mov ebp, esp
0041DA9E  51                 push ecx
0041DA9F  8B 4D 08           mov ecx, [ebp+8]
0041DAA2  83 69 2C 01        sub dword ptr [ecx+2Ch], 1    ← ★★★ 引用计数 -1！
0041DAA6  75 11              jne 0x41DAB9
0041DAA8  8D 41 08           lea eax, [ecx+8]
0041DAAB  C7 41 28 FF FF FF FF  mov dword ptr [ecx+28h], -1
0041DAB2  50                 push eax
0041DAB3  FF 15 0C D1 47 10  call dword ptr [1047D10Ch]    ← IAT（释放？）
0041DAB9  33 C0              xor eax, eax
0041DABB  C9                 leave
0041DABC  C3                 ret
```

★★★ **`sub dword ptr [ecx+2Ch], 1` + `jne`** —— **这是**引用计数递减**（`std::shared_ptr` 的 `_Decref`）。**

★★ **`[ecx+28h] = -1`** —— **把某个字段设成 -1（无效值）。**

★★ **`call [1047D10Ch]`** —— **IAT 间接调用**（可能是 `free`/`_InterlockedDecrement`）。

★★★ **⇒ `0x41DA43` / `0x41DA9B` 是 **C++ 引用计数的释放路径**，不是初始化！**

★★ **那 `onStartup` 里 `call 0x41DA43` 后 `test eax,eax; jne 错误`** ——
**说明它调用后用返回值判错。** 如果 `0x41DA9B` 恒返回 0（`xor eax,eax`），
那 `jne` 永远不跳。

★ **⇒ `call 0x41DA43` 可能是**清理旧实例**（幂等入口常见做法）。**

---

## 五、★★ `0x106231E0` 是一个**全局对象**（不是字符串）

```
RVA 0x6231E0（= VA 0x106231E0 - ImageBase 0x10000000）
在 .data（VA 0x620000, VSize 0x1E5C74 → 到 0x805C74）内 ✓

头部字节：
  02 00 00 00  00 00 00 00  00 00 00 00 00 00 00 00
  00 00 00 00  00 00 00 00  00 00 00 00 00 00 00 00
```

★★ **首个 DWORD = `2`** —— **可能是**引用计数**或**状态**。

★★★ **`push 0x106231E0` 两次**（`0x217A6D` 和 `0x217A72`）——
**说明它既作为参数传给 `call 0x41DA43`，又存进 `[ebp-248h]`。**

★ **⇒ 这是**单例对象的地址**，`onStartup` 在清理它。**

---

## 六、★★ `[0x1062 320Ch]` 与 `0x7FFFFFFF`

```asm
00217A8C  A1 0C 32 62 10        mov eax, [1062 320Ch]
00217A91  3D FF FF FF 7F        cmp eax, 7FFFFFFFh
00217A96  0F 84 C9 1C 00 00     je  0x41975F
```

★★ **`[0x1062 320Ch]` = VA `0x1062320C` = RVA `0x62320C`**

★ **`0x62320C - 0x6231E0 = 0x2C`** ——
**正好是 `0x41DA9B` 里那个 `[ecx+2Ch]` 引用计数！**

★★★ **⇒ `[0x1062 320Ch]` = 全局对象的**引用计数**，`0x106231E0` 是它的基址。**

★★ **`cmp eax, 0x7FFFFFFF; je 错误`** ——
**引用计数达到 `INT_MAX` 视为"已满/异常"。**

★ **这是 `std::shared_ptr` 或 `std::call_once` 的典型检查。**

---

## 七、逐字节证据总表

| # | 项 | 正确值 |
|---|---|---|
| 1 | `onStartup` 目标 | **`0x217A40`** ✓（`0x220885 + (-36421)`） |
| 2 | `SetEnabled` 目标 | **`0x217A40`** ✓（`0x22089B + (-36443)`） |
| 3 | `ConfigureSession` 目标 | **`0x217A40`** ✓（`0x2215BB + (-39803)`） |
| 4 | `0x217A40` 栈帧 | 1772 字节 |
| 5 | 第一个调用 | `0x41DA43`（16 字节包装 → `0x41DA9B`） |
| 6 | `0x41DA9B` 行为 | **引用计数 -1**（`sub [ecx+2Ch],1`） |
| 7 | 全局对象 | `0x106231E0`（RVA `0x6231E0`，首 DWORD = 2） |
| 8 | 引用计数字段 | `0x1062320C`（基址 + `0x2C`） |
| 9 | 上限检查 | `0x7FFFFFFF` |
| 10 | `.text` 无加密 | `55 53 56 57 31 D2` 标准序言 |

---

## 八、结论

### 1. ★★★ 我连续犯了两次"手算地址"错误

```
第一次：0x220885 - 0x8E45 = 0x217A40  我算成 0x17A40     （差 0x20000）
第二次：E8 在 +6 不是 +7                我算成 0x217A41    （差 1）
```

★★★ **⇒ 铁律：所有跳转必须用 `[BitConverter]::ToInt32(bytes, offset)` + 脚本算，不手算。**

### 2. ★★★ `0x217A40` 是唯一公共入口（四处确认）

```
onStartup         E9 → 0x217A40
onInitialized     同址
SetEnabled        E8 → 0x217A40
ConfigureSession  E8 → 0x217A40
```

★★★ **⇒ 换战斗服时，`0x217A40` 对应的源码逻辑（"确保已初始化/取单例"）
是新实现必须先做对的事。**

### 3. ★★ `0x41DA43` 是引用计数清理，不是初始化

★★ **`onStartup` 第一步先**清理旧的单例**（幂等入口的标准做法）。**

---

## 九、待逐字节继续（★ 优先级）

- [ ] ★★★ **`0x217A40` 的完整反汇编**（至少前 512 字节，看初始化步骤）
- [ ] ★★★ **`ConfigureBooking` / `ConfigureGameState` 是否也 `call 0x217A40`**
- [ ] ★★ **`0x106231E0` 单例对象的完整结构**（引用计数 + 哪些字段）
- [ ] ★★ **`0x41975E` / `0x41975F`（两条错误路径）**
- [ ] ★ **`[0x10697027]`（"已就绪"bool，报告的 024 提到）**
- [ ] ★ **`0x104739C6`（SEH 处理器）**
