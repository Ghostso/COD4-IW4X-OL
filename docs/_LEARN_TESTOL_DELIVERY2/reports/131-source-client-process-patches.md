# 学习报告 131（重开）— `ClientProcessPatches.cpp`（1,938 行）：十六个客户端补丁面

**学习范围**：`ClientProcessPatches.cpp`（82,545 B / 1,938 行）——**全文逐行读完**
**性质**：全实测
**★★★★★ 本报告收录十二个重大发现**：①**电池 HUD 除法的完整替换（含 `fxsave`）** ②**`SetThreadExecutionState` 的 6 字节替换（含 `add esp,4`）** ③**原始鼠标 `WM_INPUT` 钩子的完整实现** ④**`CL_ParseGamestate` 的两遍武器遍历** ⑤**七个空守卫的完整字节与跳转目标** ⑥**`UnlockAll` 谓词的 15 字节签名** ⑦**`config_mp.cfg` 的"两个都要或都不要"** ⑧**`com_maxfps` 只改 imm32** ⑨**TCLS 的"打开或创建并持有句柄"** ⑩**`ForceRecordValidator` 的停用理由（d27）** ⑪**两个被禁用的常量值** ⑫**`sub_806F20` 的逐字段类型流**

---

## 一、★★★★★ **电池 HUD 除法补丁**

### 1.1 ★★★★★ 完整注释（第 24–30 行，逐字）

```cpp
// CODREF(1649370): **HUD 466450 reads battery_multiplier at 46659E**,
// **multiplies by 1000 at 4665DA** and **uses that divisor at 4665EC/466610**.
// The **distributed EB4B bypass leaves 1000 even in Factory (retail 1.2)**.
// **Intercept the divide; keep native whole/remainder/percentage rendering.**
constexpr std::size_t BatteryDivideRva = **0x665E9**;
constexpr std::array<std::uint8_t, 7> BatteryDivideBytes{
    **0x8B, 0xC7, 0x99, 0xF7, 0x7C, 0x24, 0x0C**};
```

★★★★★ **⇒ 六个精确地址 + 七字节反汇编：**
```
`0x466450` ⇒ HUD 函数
`0x46659E` ⇒ 读 `battery_multiplier`
`0x4665DA` ⇒ **× 1000**
`0x4665EC` / `0x466610` ⇒ **用该除数**
        ↓
★★★ `0x665E9` 的 7 字节：**`8B C7 99 F7 7C 24 0C`**
   `8B C7`     ⇒ `mov eax, edi`
   `99`        ⇒ `cdq`
   `F7 7C 24 0C` ⇒ `idiv dword ptr [esp+0x0C]`
        ↓
★★★★★ ⇒ **就是 `eax = edi / [esp+0x0C]` 的有符号除法**
```

### ★★★★★ **`EB 4B` 是分发版的 bypass**（第 851 行）

```cpp
if (image[0x6659C] != **0xEB** || image[0x6659D] != **0x4B**)
    return false;      // ★ 只对"分发版 bypass 构建"生效
```

★★★ **⇒ 两个精确字节：`0x6659C = 0xEB`,`0x6659D = 0x4B`**
**⇒ `EB 4B` = `jmp +0x4B` ⇒ 这是分发版的 bypass,把倍数固定成 1000。**

### ★★★★★ **`clientBatteryDisplayStub` 的完整实现**（第 58–80 行）

```cpp
__declspec(naked) void clientBatteryDisplayStub()
{
    __asm
    {
        pushfd
        pushad
        mov ebx, esp              // ★ 保存原 ESP
        sub esp, 528              // ★ 528 = 512（fxsave 区）+ 16
        and esp, 0FFFFFFF0h       // ★ 16 字节对齐
        fxsave [esp]              // ★ 保存 FPU/SSE 状态
        call readBatteryDisplayDivisor
        // Original ESP+12:36 saved bytes plus12. Preserve all other state.
        mov [ebx+48], eax         // ★ 把新除数写回**保存区**
        fxrstor [esp]             // ★ 恢复 FPU/SSE
        mov esp, ebx
        popad
        popfd
        mov eax, edi              // ★ 复原 `mov eax, edi`
        cdq                       // ★ 复原 `cdq`
        idiv dword ptr [esp+12]   // ★ 用**新除数**做除法
        jmp dword ptr [BatteryDivideContinuation]   // ★ 跳到 0x665F0
    }
}
```

★★★★★ **⇒ 七个精确细节：**
```
① `pushfd` + `pushad` ⇒ 保存全部
② `mov ebx, esp` ⇒ 记下原 ESP
③ **`sub esp, 528`** ⇒ 528 = **512（`fxsave` 区）+ 16**
④ **`and esp, 0xFFFFFFF0`** ⇒ **16 字节对齐**（`fxsave` 要求）
⑤ `fxsave [esp]` / `fxrstor [esp]` ⇒ **保存/恢复 FPU+SSE**
⑥ **`mov [ebx+48], eax`** ⇒ 新除数写回
   ⇒ `ebx` = 原 ESP（`pushfd` 后）
   ⇒ `+48` = `pushfd`(4) + `pushad`(32) + **12** = 48
   ⇒ **`esp+12` 正是 `idiv` 的操作数**
⑦ 复原 `mov eax,edi` + `cdq` + **用新除数 `idiv`**
```

### ★★★★★ **`readBatteryDisplayDivisor` 的两条路径**（第 35–56 行）

```cpp
const auto *dvar = FindBatteryDvar("battery_multiplier");
if (!dvar) return **1000**;
double multiplier{};
if (dvar[8] == **1**)                                  // ★ type 1 = float
{
    float value{};
    std::memcpy(&value, dvar + 12, sizeof(value));      // ★ +12 是值
    multiplier = value;
}
else                                                   // ★ 其他 = string
{
    const char *value{};
    std::memcpy(&value, dvar + 12, sizeof(value));
    multiplier = value ? std::atof(value) : 0.0;
}
return clientBatteryDisplayDivisor(multiplier);
```

★★★★★ **⇒ 三个精确值：**
```
`dvar[8]` = **类型**（**1 = float**,其他 = string）
`dvar + 12` = **值**
        ↓
★★★ 与报告 129/130 的 **`DvarIntValueOffset = 12`** 与 **`[ecx+0Ch]`****完全一致** ✓
```

### ★★★★★ **`clientBatteryDisplayDivisor` 的边界**（第 835–844 行）

```cpp
const double units = multiplier * **1000.0**;
if (!std::isfinite(units) || units < **1.0** ||
    units > (double)std::numeric_limits<int>::max())
    return **1000**;
return (int)units;
```

★★★ **⇒ 三个拒绝条件：非有限 / `< 1` / `> INT_MAX` ⇒ 全部回退 **1000**。**

### ★★★ 两个全局（第 888–889 行）

```cpp
FindBatteryDvar = (BatteryDvarLookup)(module + **0x36F190**);
BatteryDivideContinuation = module + **0x665F0**;
```

★★★ **⇒ 两个精确 RVA：`0x36F190`（dvar 查找）/ `0x665F0`（续点）。**

---

## 二、★★★★★ **`SetThreadExecutionState` 的 6 字节替换**

### 2.1 ★★★★★ 完整注释（第 81–103 行，逐字）

```cpp
// CODOL WndProc calls **SetThreadExecutionState** at its entry -- **0x00643FE0 on 3.3.3.3**,
// **0x00780860 on out.exe (1649370)**.
//
// CODREF(client_window_proc): **all four constants below were re-derived for 1649370 by
// IMPORT SIGNATURE**, which is the one anchor that survives an unrelated build: **an import
// is named in the file**, so `call [SetThreadExecutionState]` means the same thing everywhere
// even though **the IAT slot moved `0x00B5B244` -> `0x0E9D34A8`** and out.exe's table was
// **rebuilt by its unpacker**. **Each build contains EXACTLY ONE call site for that API**, so
// there was nothing to disambiguate. **CL_MouseEvent and its caller were pinned the same way**
// -- **{ClipCursor, InterlockedExchange, QueryPerformanceCounter}** and
// **{GetCursorPos, GetForegroundWindow, ScreenToClient}** each match **exactly one function**
// in out.exe, and **the caller is 0xB0 bytes in BOTH builds**.
//
// **ClientWindowHandle is a data global, so it is positional**: inside that caller pair
// **every .data reference aligns at an identical byte offset**, `0x03749AAC` appears at
// **+0x10 and +0x4F** and maps to **0x081AA758** both times, and its neighbour
// `0x03749ABC` -> `0x081AA768` keeps the same **+0x10** adjacency.
```

★★★★★ **⇒ 七个精确值：**
```
`SetThreadExecutionState` 调用点：3.3.3.3 **`0x00643FE0`** / 1649370 **`0x00780860`**
IAT 槽：**`0x00B5B244`** → **`0x0E9D34A8`**
        ↓
★★★ **方法：按导入签名重定**（导入名在文件里 ⇒ 跨 build 稳定）
★★★ **每个 build 里该 API 恰好一个调用点** ⇒ 无需消歧
        ↓
★★★ `CL_MouseEvent` 的两个签名：
   **{`ClipCursor`, `InterlockedExchange`, `QueryPerformanceCounter`}**
   **{`GetCursorPos`, `GetForegroundWindow`, `ScreenToClient`}**
★★★ **调用者在两个 build 里都是 `0xB0`（176）字节**
        ↓
★★★ `ClientWindowHandle` 是**数据全局 ⇒ 只能按位置**：
   `0x03749AAC` 出现在 **+0x10** 和 **+0x4F** ⇒ 映射到 **`0x081AA758`**
   邻居 `0x03749ABC` → **`0x081AA768`**（**同样的 +0x10 相邻**）
```

### ★★★★★ **6 字节的替换（含栈平衡）**（第 104–115 行，逐字）

```cpp
constexpr std::size_t ExecutionStateCallRva = **0x380880**;
constexpr std::array<std::uint8_t, 6> ExecutionStateCall{
    **0xFF, 0x15, 0xA8, 0x34, 0x9D, 0x0E**,          // call dword ptr [0x0E9D34A8]
};
// The original **WINAPI call consumes the preceding `push 2`**. Keep
// that **stack effect** when removing the call or **MainWndProc returns
// with ESP shifted and eventually trips its /GS cookie check**.
constexpr std::array<std::uint8_t, 6> ExecutionStateReplacement{
    **0x83, 0xC4, 0x04, 0x90, 0x90, 0x90**,          // add esp,4; nop;nop;nop
};
```

★★★★★ **⇒ 六个精确值：**
```
原始：**`FF 15 A8 34 9D 0E`** = `call dword ptr [0x0E9D34A8]`（**6 字节**）
替换：**`83 C4 04 90 90 90`** = `add esp,4` + **3 个 NOP**
        ↓
★★★★★ ⇒ 理由：**WINAPI 调用消耗了前面的 `push 2`**
   ⇒ 移除调用时必须**保持栈效果**
   ⇒ 否则 **`MainWndProc` 返回时 ESP 偏移** ⇒ **最终触发 `/GS` cookie 检查**
```

### ★★★★★ **`executionStateImportMatches` 的三级校验**（第 272–296 行）

```cpp
① 从 `ExecutionStateCallRva + 2` 读 **4 字节 IAT 地址**
② 校验 `moduleStart <= iatAddress <= moduleEnd - sizeof(void*)`
③ 读 IAT 槽里的实际函数指针
④ `GetModuleHandleW(L"kernel32.dll")` + `GetProcAddress(..., "SetThreadExecutionState")`
⑤ **比较两者**
```

★★★ **⇒ 这是**运行时**的导入校验（不只看字节,还验证 IAT 指向真正的 API）。**

### ★★★ 判定（第 243–270 行）

```cpp
if (equal(actual, ExecutionStateReplacement)) return **Patched**;
for (index...) {
    if (index >= 2 && index < 6) continue;   // ★ 跳过 IAT 地址（可重定位）
    if (actual[index] != ExecutionStateCall[index]) return **Unexpected**;
}
return **Original**;
```

★★★ **⇒ 只校验 `[0]`（`0xFF`）和 `[1]`（`0x15`）两个字节 ⇒ 因为后 4 字节是 IAT 地址。**

---

## 三、★★★★★ **原始鼠标 `WM_INPUT` 钩子**

### 3.1 ★★★★★ 四个常量（第 116–121 行）

```cpp
constexpr std::size_t ClientMouseEventCallRva = **0x37ADF2**;
constexpr std::array<std::uint8_t, 5> ClientMouseEventCall{
    **0xE8, 0x99, 0x66, 0xE3, 0xFF**,       // rel32 = 0xFFE36699 = -1,872,231
};
constexpr std::size_t ClientMouseEventRva = **0x1B1490**;
constexpr std::size_t ClientWindowHandleRva = **0x7DAA758**;
```

### ★★★★★ **`clientMouseEventRawInputStub` 的完整实现**（第 314–344 行）

```cpp
__declspec(naked) void clientMouseEventRawInputStub()
{
    __asm
    {
        push ebp
        mov ebp, esp
        push edi
        sub esp, 8
        lea eax, [ebp-12]           // ★ &deltaY
        push eax
        lea ecx, [ebp-8]            // ★ &deltaX
        push ecx
        call drainRawMouseDelta
        add esp, 8
        test al, al
        jz use_legacy_delta
        mov edi, [ebp-8]            // ★ deltaX ⇒ edi
        mov edx, [ebp-12]           // ★ deltaY ⇒ edx
        mov [ebp+16], edx           // ★ 覆盖第二个参数
    use_legacy_delta:
        push dword ptr [ebp+16]     // ★ 参数 2
        push dword ptr [ebp+12]     // ★ 参数 1
        push dword ptr [ebp+8]      // ★ 参数 0
        call dword ptr [OriginalClientMouseEvent]
        add esp, 12                 // ★ 3 个参数
        mov edi, [ebp-4]            // ★ 恢复 edi
        mov esp, ebp
        pop ebp
        ret
    }
}
```

★★★★★ **⇒ 五个精确细节：**
```
① **三个参数**（`[ebp+8]` / `[ebp+12]` / `[ebp+16]`）⇒ `add esp, 12`
② **`edi` 被返回**（`mov edi, [ebp-8]`）⇒ 这是 `CL_MouseEvent` 的返回值约定
③ **`[ebp+16]`（第二个参数）被 deltaY 覆盖**
④ `[ebp-8]` = deltaX,`[ebp-12]` = deltaY（局部）
⑤ **没有原始输入时走 legacy 路径**（`use_legacy_delta`）
```

### ★★★★★ **`rawInputWindowProcedure` 的四个过滤条件**（第 505–534 行）

```cpp
if (message == WM_INPUT)
{
    RAWINPUT input{};
    UINT size = sizeof(input);
    if (GetRawInputData((HRAWINPUT)lParam, RID_INPUT, &input, &size,
            sizeof(RAWINPUTHEADER)) == size &&
        input.header.dwType == **RIM_TYPEMOUSE** &&
        !(input.data.mouse.usFlags & **MOUSE_MOVE_ABSOLUTE**) &&
        (input.data.mouse.lLastX || input.data.mouse.lLastY))
    {
        AcquireSRWLockExclusive(&RawMouseLock);
        RawMouseDeltaX += input.data.mouse.lLastX;
        RawMouseDeltaY += input.data.mouse.lLastY;
        ++RawMouseEventCount;
        ReleaseSRWLockExclusive(&RawMouseLock);
    }
}
return CallWindowProcA(PreviousWindowProcedure, window, message, wParam, lParam);
```

★★★ **⇒ 四个过滤：**
```
① `GetRawInputData` 返回 `== size`（完整读取）
② `dwType == RIM_TYPEMOUSE`
③ **`!(usFlags & MOUSE_MOVE_ABSOLUTE)`** ⇒ 排除绝对坐标（触摸板/远程桌面）
④ `lLastX || lLastY`（非零位移）
```

### ★★★ `maintainClientRawInputWindow` 的三步（第 1633–1671 行）

```cpp
① 读 `*(HWND*)(module + **0x7DAA758**)` ⇒ `IsWindow` 检查
② `SetWindowLongPtrA(window, GWLP_WNDPROC, &rawInputWindowProcedure)` ⇒ 保存旧过程
③ `RegisterRawInputDevices({usUsagePage=**0x01**, usUsage=**0x02**, dwFlags=**0**, hwndTarget=window})`
```

★★★ **⇒ 三个精确值：**
```
`usUsagePage = **0x01**`（**Generic Desktop**）
`usUsage = **0x02**`（**Mouse**）
`dwFlags = **0**`（**不用 `RIDEV_INPUTSINK`** ⇒ 只有前台窗口收到）
        ↓
★★★ 失败时**恢复旧过程**（`SetWindowLongPtrA(..., previous)`）
```

---

## 四、★★★★★ **`CL_ParseGamestate` 的两遍武器遍历**

### 4.1 ★★★★★ 完整注释（第 123–131 行，逐字）

```cpp
// CODREF(1649370): **CL_ParseGamestate performs TWO calls to sub_59B560**.
// **0x454A54 walks ordinary weapon configstrings with arg 1**;
// after **defaultweapon/defaultknife and registry finalization**,
// **0x454B55 walks modular strings with arg 0**. **The latter is the exact
// boundary where runtime-only alpha WeaponDefs must be restored after the
// parser's registry clear and before "** <base> ..." is resolved.**
constexpr std::size_t ClientModularWeaponWalkCallRva = **0x54B55**;
constexpr std::size_t ClientWeaponWalkRva = **0x19B560**;
```

★★★★★ **⇒ 四个精确值：**
```
`CL_ParseGamestate` 对 **`sub_59B560`** 调用 **两次**
        ↓
★★★ **`0x454A54`** ⇒ 遍历**普通**武器 configstring,**arg = 1**
★★★ **`0x454B55`** ⇒ 遍历**模块化**字符串,**arg = 0**
        ↓
★★★ 中间有 **`defaultweapon` / `defaultknife` 和注册表定稿**
        ↓
★★★★★ ⇒ **`0x454B55` 正是"运行时 alpha WeaponDefs 必须恢复"的边界**
   （在**解析器的注册表清空之后**,在 **`"** <base> ..."` 解析之前**）
```

### ★★★★★ **`clientAlphaWeaponModularWalkStub` 的"只做一次"**（第 346–364 行）

```cpp
__declspec(naked) void clientAlphaWeaponModularWalkStub()
{
    __asm
    {
        // The patched site is inside a **1..1699 loop**. Restore the alpha
        // bases **once**, immediately before its first modular lookup.
        cmp edi, **1**
        jne invoke_native_walk
        pushfd
        pushad
        call dword ptr [AlphaWeaponPrepareCallback]
        popad
        popfd
    invoke_native_walk:
        // The original call's return address is already on the stack;
        // **tail-jump** so sub_59B560 returns directly to CL_ParseGamestate.
        jmp dword ptr [OriginalClientWeaponWalk]
    }
}
```

★★★★★ **⇒ 三个精确事实：**
```
① 循环范围 **1..1699**（`cmp edi, 1` 只匹配第一次）
② **只在第一次调用前**恢复 alpha bases
③ **尾跳**（`jmp` 而非 `call`）⇒ `sub_59B560` 的 `ret` **直接返回 `CL_ParseGamestate`**
        ↓
★★★ ⇒ 不需要额外 `add esp`（返回地址已在栈上）
```

### ★★★★★ **`patchClientAlphaWeaponGamestateCallBuffer` 的三步校验**（第 594–630 行）

```cpp
① `call[0] != 0xE8` ⇒ false
② 解出 `presentDisplacement` ⇒ 算 `presentTarget`
③ `presentTarget == replacement` ⇒ **已补,true**
④ `presentTarget != imageBase + **0x19B560**` ⇒ **false**（不是我们派生的调用）
⑤ 写入新的 displacement
```

★★★ **⇒ 第 4 条是**目标校验**：只有原本指向 `sub_59B560` 的调用才会被改。**

---

## 五、★★★★★ **七个空守卫的完整字节**

### 5.1 ★★★★★ **`clientLoopFxNullGuardStub`**（第 366–385 行）

```cpp
constexpr std::size_t ClientLoopFxWorkerRva = **0xDAE70**;
constexpr std::array<std::uint8_t, 6> ClientLoopFxWorkerPrologue{
    **0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x20**,     // push ebp; mov ebp,esp; sub esp,20h
};
...
__asm
{
    mov eax, [esp+8]        // ★ 第二个参数 = effect descriptor
    test eax, eax
    jz missing_effect
    cmp dword ptr [eax], 0  // ★ 第一层解引用必须非空
    jz missing_effect
    push ebp                // ★ 重放被偷的序言
    mov ebp, esp
    sub esp, 20h
    jmp dword ptr [ClientLoopFxWorkerContinuation]
missing_effect:
    xor eax, eax
    ret
}
```

★★★★★ **⇒ 五个精确事实：**
```
`sub_4DAE70` = **`0xDAE70`**
序言 = **`55 8B EC 83 EC 20`**（6 字节）
        ↓
★★★ 首次解引用：`mov edx, [esi]` 后 `mov eax, [edx+0x18]`（第 133–135 行注释）
★★★ ⇒ **两层都要非空**：`[esp+8]`（descriptor）+ `[eax]`（effect 指针）
        ↓
★★★ **缺失 ⇒ `xor eax,eax; ret`**（返回 null ⇒ 无视觉效果）
★★★ **有 ⇒ 重放 3 条序言指令 + 尾跳**
```

★★★ **⇒ 注释（第 136–140 行）：**
```
"The first crash was reached through **CG_AddLoopFx**, but **a later trace reached the same
 worker through out.exe+0x131C7B**; there are **18 native callers**. **Guard the shared
 worker entry so every missing effect degrades to no visual.**"
```

### 5.2 ★★★★★ **`clientEntityEventWeaponGuardStub`**（第 387–398 行）

```cpp
constexpr std::size_t ClientEntityEventWeaponReadRva = **0x132A76**;
constexpr std::array<std::uint8_t, 7> ClientEntityEventWeaponRead{
    **0x80, 0xB9, 0xF3, 0x0E, 0x00, 0x00, 0x00**,   // cmp byte ptr [ecx+0x0EF3], 0
};
constexpr std::size_t ClientEntityEventWeaponReadResumeRva = **0x132A7D**;
constexpr std::size_t ClientEntityEventNullWeaponRva = **0x132A8C**;
...
__asm
{
    test ecx, ecx              // ★ ecx = WeaponDef
    jz null_weapon
    cmp byte ptr [ecx+0EF3h], 0    // ★ 重放被偷的读
    jmp dword ptr [ClientEntityEventWeaponReadContinuation]
null_weapon:
    jmp dword ptr [ClientEntityEventNullWeaponContinuation]
}
```

★★★★★ **⇒ 三个精确值：**
```
`CG_EntityEvent` = **`0x00532A60`**
读取点 = **`0x00532A76`**：**`80 B9 F3 0E 00 00 00`** = `cmp byte ptr [ecx+0x0EF3], 0`
函数自己的空检查在 **`0x00532A9C`**
        ↓
★★★ ⇒ **读取在空检查**之前** ⇒ 无武器的 event 在 **`out.exe+0x0132A76`** 崩溃
★★★ ⇒ 三个续点：正常 **`0x132A7D`** / 空武器 **`0x132A8C`**
```

### 5.3 ★★★★★ **`clientEntityEventRangeGuardStub`**（第 420–444 行）

```cpp
constexpr std::size_t ClientEntityEventRva = **0x132910**;
constexpr std::array<std::uint8_t, 6> ClientEntityEventPrologue{
    **0x55, 0x8B, 0xEC, 0x83, 0xE4, 0xF8**,     // push ebp; mov ebp,esp; and esp,-8
};
constexpr std::size_t ClientEntityEventResumeRva = **0x132916**;
constexpr std::uint32_t MaximumClientEntityEvent = **184**;
...
__asm
{
    cmp dword ptr [esp+4], **0B8h**    // ★ 184
    jbe valid_event
    pushfd
    pushad
    mov eax, [esp+20]
    push eax
    mov eax, [esp+44]
    push eax
    call recordRejectedClientEntityEvent
    add esp, 8
    popad
    popfd
    xor eax, eax
    **ret 8**                          // ★ 弹 2 个参数
valid_event:
    push ebp
    mov ebp, esp
    and esp, 0FFFFFFF8h                // ★ 重放 `and esp,-8`
    jmp dword ptr [ClientEntityEventContinuation]
}
```

★★★★★ **⇒ 五个精确值：**
```
上界 = **`0xB8`** = **184**
        ↓
★★★ 超界 ⇒ 记录 + **`xor eax,eax` + `ret 8`**（**弹 2 个参数** ⇒ 函数是 `__stdcall` 2 参）
★★★ 合法 ⇒ 重放 3 条序言（`push ebp` / `mov ebp,esp` / **`and esp,-8`**）+ 尾跳
        ↓
★★★ 注释（第 159–162 行）："Its **default jump-table arm calls Com_Error** for anything
 larger, **turning a stale network event into a client drop**."
```

### ★★★ `recordRejectedClientEntityEvent` 的两个偏移（第 400–418 行）

```cpp
const auto number = entity ? *(u32*)(entity + **0xF4**) : 0xFFFFFFFF;
const auto type   = entity ? *(u32*)(entity + **0xF8**) : 0xFFFFFFFF;
```
★★★ **⇒ `entity+0xF4` = 实体号,`entity+0xF8` = `eType`；上限 **16** 次。**

### 5.4 ★★★★★ **`clientAmmoLookupWeaponGuardStub`**（第 446–462 行）

```cpp
constexpr std::size_t ClientAmmoLookupRva = **0x21A70**;
constexpr std::array<std::uint8_t, 10> ClientAmmoLookupEntry{
    **0x55, 0x8B, 0xEC, 0x8B, 0x0C, 0x85, 0x50, 0x8B, 0x98, 0x01**,
};
constexpr std::size_t ClientAmmoLookupResumeRva = **0x21A7A**;
...
__asm
{
    test eax, eax                 // ★ weapon index
    jz no_ammo
    mov ecx, dword ptr [eax*4+**01988B50h**]   // ★ 重放查表
    test ecx, ecx
    jz no_ammo
    push ebp
    mov ebp, esp
    jmp dword ptr [ClientAmmoLookupContinuation]
no_ammo:
    xor eax, eax
    ret
}
```

★★★★★ **⇒ 四个精确值：**
```
`BG_GetAmmoInClip(ps, weapon, hand)` = **`sub_421A70`**
10 字节：`55 8B EC` + **`8B 0C 85 50 8B 98 01`** = `mov ecx, [eax*4+0x01988B50]` + `mov ebx,[eax+0x18B...]`
        ↓
★★★ 武器表基址 = **`0x01988B50`**
★★★ 解引用 `WeaponDef + **0x7F4**`（第 172 行注释）
```

### 5.5 ★★★★★ **`clientWeaponInventoryGuardStub`**（第 464–477 行）

```cpp
constexpr std::size_t ClientWeaponInventoryReadRva = **0x2C146**;
constexpr std::array<std::uint8_t, 7> ClientWeaponInventoryRead{
    **0x8B, 0x0C, 0x85, 0x50, 0x8B, 0x98, 0x01**,
};
constexpr std::size_t ClientWeaponInventoryResumeRva = **0x2C14D**;
constexpr std::size_t ClientWeaponInventorySkipRva = **0x2C187**;
...
__asm
{
    cmp eax, **06A3h**                  // ★ 1699 = MaximumWeaponAssetIndex
    ja missing_weapon
    mov ecx, dword ptr [eax*4+**01988B50h**]
    cmp ecx, **10000h**                 // ★ 必须 >= 65536
    jb missing_weapon
    jmp dword ptr [ClientWeaponInventoryContinuation]
missing_weapon:
    jmp dword ptr [ClientWeaponInventorySkipContinuation]
}
```

★★★★★ **⇒ 三个精确值：**
```
上界 = **`0x06A3`** = **1699**（= `MaximumWeaponAssetIndex`，与报告 128 的注册表 **1700** 一致 ✓）
指针下界 = **`0x10000`**（65,536）⇒ **低于此值的不是有效指针**
        ↓
★★★ `sub_42C0E0` 遍历 **15 个武器槽**（第 179 行注释）
★★★ 空指针时读 `null + 0x7EC` 会崩
```

### 5.6 ★★★★★ **`clientUiOperatorResolverGuardStub`**（第 479–503 行）

```cpp
constexpr std::size_t ClientUiOperatorResolverRva = **0x1A41E0**;
constexpr std::array<std::uint8_t, 6> ClientUiOperatorResolverPrologue{
    **0x55, 0x8B, 0xEC, 0x51, 0x8B, 0x17**,     // push ebp; mov ebp,esp; push ecx; mov edx,[edi]
};
constexpr std::size_t ClientUiOperatorResolverResumeRva = **0x1A41E6**;
...
__asm
{
    cmp eax, **13h**                // ★ 19 ⇒ 20 个运算符（0..19）
    ja invalid_expression
    test edi, edi                   // ★ 操作数 1
    jz invalid_expression
    cmp dword ptr [edi], **2**      // ★ 类型 <= 2（3 种类型 0..2）
    ja invalid_expression
    mov edx, [esp+4]                // ★ 操作数 2
    test edx, edx
    jz invalid_expression
    cmp dword ptr [edx], **2**
    ja invalid_expression
    push ebp
    mov ebp, esp
    push ecx
    mov edx, [edi]                  // ★ 重放
    jmp dword ptr [ClientUiOperatorResolverContinuation]
invalid_expression:
    xor eax, eax
    **ret 4**
}
```

★★★★★ **⇒ 五个精确值：**
```
`sub_5A41E0` 解析 **20 × 3 × 3** 的函数指针表
        ↓
★★★ 运算符上界 **`0x13`** = **19**（⇒ **20 个**）
★★★ 两个操作数的类型上界 **`2`**（⇒ **3 种**）
        ↓
★★★ 五重校验：`eax <= 19` / `edi != 0` / `[edi] <= 2` / `edx != 0` / `[edx] <= 2`
★★★ 失败 ⇒ `xor eax,eax; ret 4`（返回 null ⇒ 原生无操作路径）
```

★★★ **⇒ `20 × 3 × 3 = 180` 个函数指针 ⇒ 表大小 **720 字节**（32 位）。**

---

## 六、★★★★★ **`UnlockAll` 谓词的 15 字节签名**

### 6.1 ★★★★★ 完整注释（第 1322–1336 行，逐字）

```cpp
// sub_5E3550 on out.exe: **`a1 == onboardCharacterID || (a1 > 0 && sub_80A5E0(a1))`**,
// the predicate that lets **sub_5E3760 report an item owned when the inventory hash does
// not have it**. Image base 0x400000, so **RVA 0x1E3550**.
constexpr std::size_t UnlockAllPredicateRva = **0x1E3550**;

// **mov al, 1 ; ret**.  The original opens with `push ecx` and closes `pop ecx ; ret`, so
// **returning before the push leaves the stack exactly as the caller left it** -- and the
// function's own success path is **literally `b0 01 59 c3`, the same AL**.
constexpr std::array<std::uint8_t, 3> UnlockAllReplacement{ **0xB0, 0x01, 0xC3** };

// **THE GUARD SKIPS THE RELOCATED OPERANDS.** **Byte 4..7 is the address of the
// "onboardCharacterID" string** and **9..12 a call displacement**; both move when the image
// is rebased, so a signature that included them would **fail on a perfectly good client**
// and, worse, **could match somewhere else after a rebase**. Only the **fixed opcodes and
// the distinctive `cmp esi,eax / jnz / mov al,1 / pop ecx / ret` tail** are checked.
```

★★★★★ **⇒ 六个精确值：**
```
谓词 = **`sub_5E3550`**（RVA **`0x1E3550`**）
逻辑 = **`a1 == onboardCharacterID || (a1 > 0 && sub_80A5E0(a1))`**
调用者 = **`sub_5E3760`**（94 个调用点，报告 127 已记录）
        ↓
★★★ 原始开头 **`push ecx`**,结尾 **`pop ecx; ret`**
★★★ 自身成功路径 **`b0 01 59 c3`** = `mov al,1; pop ecx; ret`
        ↓
★★★ 替换 = **`B0 01 C3`**（`mov al,1; ret`）
   ⇒ **在 `push ecx` 之前返回** ⇒ **栈与调用者离开时完全一致**
```

### ★★★★★ **15 字节签名的完整偏移表**

```cpp
{ 0, 0x51 }, { 1, 0x6A }, { 2, 0x00 }, { 3, 0x68 },
{ 8, 0xE8 },
{ 13, 0x83 }, { 14, 0xC4 }, { 15, 0x08 },
{ 16, 0x3B }, { 17, 0xF0 },
{ 18, 0x75 }, { 19, 0x04 },
{ 20, 0xB0 }, { 21, 0x01 }, { 22, 0x59 },
```

★★★★★ **⇒ 完整反汇编（23 字节）：**
```
`[0]`      **`51`**           ⇒ `push ecx`
`[1]`      **`6A 00`**        ⇒ `push 0`
`[3]`      **`68 ?? ?? ?? ??`** ⇒ `push <onboardCharacterID>`（★ **[4..7] 跳过**）
`[8]`      **`E8 ?? ?? ?? ??`** ⇒ `call sub_80A5E0`（★ **[9..12] 跳过**）
`[13]`     **`83 C4 08`**     ⇒ `add esp, 8`
`[16]`     **`3B F0`**        ⇒ `cmp esi, eax`
`[18]`     **`75 04`**        ⇒ `jnz +4`
`[20]`     **`B0 01`**        ⇒ `mov al, 1`
`[22]`     **`59`**           ⇒ `pop ecx`
`[23]`     （`C3`）           ⇒ `ret`
```

★★★ **⇒ 两个跳过的区间：`[4..7]`（字符串地址）+ `[9..12]`（调用位移）。**

### ★★★ `installUnlockAllPatch` 的五步

```cpp
① `OLMOD_UNLOCK_ALL` 必须是 **`'1'`**（首字符）
② `validHostImage`（三重身份）
③ `UnlockAllPredicateRva + 24 >= SizeOfImage` ⇒ UnsupportedHost（★ **24** 而非 23）
④ 已是 `B0 01 C3` ⇒ **AlreadyPatched**
⑤ 15 个签名字节全对 ⇒ 否则 **UnexpectedBytes**
⑥ `VirtualProtect` 3 字节 ⇒ 写 `B0 01 C3`
```

---

## 七、★★★★★ **`config_mp.cfg` 的"两个都要或都不要"**

### 7.1 ★★★★★ 完整实现（第 1410–1487 行）

```cpp
constexpr std::size_t ConfigWriteEncryptGateRva = **0xFDBCC**;
constexpr std::size_t ConfigReadDecryptGateRva  = **0xF3119**;
constexpr std::array<std::uint8_t, 2> ConfigWriteGateOriginal{ **0x75, 0x6E** };
constexpr std::array<std::uint8_t, 2> ConfigWriteGatePatched{  **0xEB, 0x6E** };
constexpr std::array<std::uint8_t, 2> ConfigReadGateOriginal{  **0x75, 0x34** };
constexpr std::array<std::uint8_t, 2> ConfigReadGatePatched{   **0xEB, 0x34** };
```

### ★★★★★ **"ON BY DEFAULT" 的完整理由**（第 1424–1435 行，逐字）

```cpp
// **ON BY DEFAULT, AND THE REASON IS A TRAP RATHER THAN A PREFERENCE.**
//
// Once a client has written players/config_mp.cfg as **plain text**, **a LATER launch WITHOUT
// this patch decrypts it, gets garbage, fails the "starts with //" check at 0x004F3144, and
// silently ignores the whole file** -- so **every bind, the sensitivity and the fov revert to
// defaults and are then overwritten with an encrypted file of defaults**.
// **Leaving the patch opt-in means one forgotten environment variable costs a player their
// settings, with no error anywhere.**
//
// Default-on removes that asymmetry: the patched client reads both forms sensibly
// (a plaintext file directly, an old encrypted one discarded exactly once), and
// **OLMOD_PLAINTEXT_CONFIG=0** is there for anyone who wants the stock behaviour back.
```

★★★★★ **⇒ 一个完整的陷阱链：**
```
打过补丁的客户端写**明文** `config_mp.cfg`
        ↓
★★★ **后续启动不打补丁** ⇒ 解密明文 ⇒ 得到**垃圾**
★★★ 失败 `"starts with //"` 检查（**`0x004F3144`**）⇒ **静默忽略整个文件**
        ↓
★★★ ⇒ **所有绑定、灵敏度、fov 回默认**
★★★ 然后**用一份加密的默认值覆盖**
        ↓
★★★★★ ⇒ **一个遗忘的环境变量就让玩家丢失全部设置,而**没有任何错误提示**
        ↓
★★★ ⇒ 改为**默认开启**,`OLMOD_PLAINTEXT_CONFIG=0` 恢复原行为
```

### ★★★★★ **"BOTH OR NEITHER"**（第 1466–1474 行，逐字）

```cpp
// **BOTH OR NEITHER.** Patching only the writer leaves **plaintext on disk that the reader
// would try to decrypt**; patching only the reader leaves **an encrypted file being executed**.
// **A half-applied pair is worse than none**, so refuse unless **both sites are exactly the
// bytes they were read from**.
if (!matches(writeGate, ConfigWriteGateOriginal) ||
    !matches(readGate, ConfigReadGateOriginal))
    return UnexpectedBytes;
```

★★★★★ **⇒ 两个半应用的后果：**
```
只补写入方 ⇒ 磁盘上是**明文**,而读取方**试图解密**
只补读取方 ⇒ **加密文件被执行**
        ↓
★★★ ⇒ **半应用的对比完全不应用更糟**
```

---

## 八、★★★★★ **`com_maxfps` 只改 imm32**

### 8.1 ★★★★★ 完整实现（第 1504–1510 行）

```cpp
// `push 0C8h` supplying the MAX argument of com_maxfps' registration. **Five bytes,
// and only the imm32 at +1 is rewritten** so the **opcode and the stack effect are
// untouched**. **The DEFAULT push at 0xFC40F is deliberately left alone.**
constexpr std::size_t MaxFpsCeilingPushRva = **0xFC408**;
constexpr std::array<std::uint8_t, 5> MaxFpsCeilingPushOriginal{
    **0x68, 0xC8, 0x00, 0x00, 0x00**,     // push 200
};
```

★★★ **⇒ 两个精确值：**
```
MAX 的 `push 200` ⇒ **`0x68 C8 00 00 00`** @ **`0xFC408`**
DEFAULT 的 push ⇒ **`0xFC40F`**（**故意不动**）
```

### ★★★ 范围校验（第 1514–1519 行）

```cpp
const auto ceiling = std::strtoul(requested, nullptr, 10);
if (ceiling < **1** || ceiling > **10000**) return NotRequested;
```

### ★★★ 已补判定（第 1536–1539 行）

```cpp
std::uint32_t present{};
std::memcpy(&present, site + 1, sizeof(present));
if (site[0] == **0x68** && present == wanted) return **AlreadyPatched**;
```
★★★ **⇒ 判据是 `opcode == 0x68` **且** imm32 == 目标值。**

---

## 九、★★★★★ **TCLS 的"打开或创建并持有句柄"**

### 9.1 ★★★★★ 完整注释（第 1856–1873 行，逐字）

```cpp
// **OPEN-OR-CREATE, AND HOLD THE HANDLE. NEVER JUST LOOK.**
//
// The first version of this **asked OpenFileMapping whether the name was there, closed
// the handle, and returned AlreadyVisible without publishing anything**. Measured
// **2026-09-05**, that is **precisely what kept the bug alive**:
//
//     **19:12:42  tcls mapping ALREADY VISIBLE**      <- from inside pid **364**
//     **19:12:43  [P364] OpenFileMapping ... fail! Error code = 2**
//
// **Same process, same name, one second apart, ours succeeding and TenProxy's failing.**
// **A named section dies when its LAST handle closes**, and **SampleLauncher disposes its
// handle the moment its process poll stops seeing the client** -- so **the name existed while
// we looked and was gone when TenProxy asked**. **Looking without holding is what made the
// window**; **a diagnostic that releases the thing it is measuring changes the outcome.**
//
// **CreateFileMapping opens an existing name or makes a new one**, and **this process holds
// that handle for its whole life**. **After this call the name cannot go away while the client
// is running, whoever else lets go of it.**
```

★★★★★ **⇒ 五个精确值：**
```
第一版：`OpenFileMapping` 查存在 ⇒ **关句柄** ⇒ 返回 `AlreadyVisible` ⇒ **什么也没发布**
        ↓
★★★ 实测（**2026-09-05**）：
   **19:12:42** 从 pid **364** 内部看"已存在"
   **19:12:43** 同一进程、同一名字,**TenProxy `OpenFileMapping ... fail! Error code = 2`**
        ↓
★★★★★ ⇒ **命名段在最后一个句柄关闭时消亡**
★★★ `SampleLauncher` 在**轮询看不到客户端时立刻释放句柄**
★★★ ⇒ **我们看到时名字还在,`TenProxy` 问时已消失**
        ↓
★★★★★ ⇒ **"Looking without holding is what made the window;
   a diagnostic that releases the thing it is measuring changes the outcome."**
```

### ★★★★★ **"持有别人的映射 ≠ 它是对的"**（第 1882–1893 行，逐字）

```cpp
// **HOLDING SOMEBODY ELSE'S MAPPING IS NOT THE SAME AS IT BEING RIGHT.**
//
// This used to keep the handle and **leave the bytes alone**, on the reasoning that whoever
// made it had put the correct blob in. **That is false the moment a STALE publisher is still
// alive**: **SampleLauncher pre-publishes a window of 512 mappings and holds them for its
// whole life**, so **a second run leaves the first run's mappings in the prefix**. A new
// client landing on one gets **an OLD login blob**, TenProxy reads **stale credentials**, and
// **the client never authenticates** -- measured **2026-09-05**, `tcls mapping HELD` on every
// launch while **the auth server saw nothing at all for twenty minutes**.
```

★★★★★ **⇒ 四个精确值：**
```
`SampleLauncher` **预发布 512 个映射的窗口**并**终身持有**
        ↓
★★★ 第二次运行 ⇒ **第一次的映射留在前缀里**
★★★ 新客户端落上去 ⇒ 拿到**旧的登录 blob** ⇒ TenProxy 读**过期凭据**
        ↓
★★★ 实测（**2026-09-05**）：**每次启动都 `tcls mapping HELD`**
   **而认证服务器二十分钟里什么也没看到**
        ↓
★★★ ⇒ **修复：不管存在与否,都写我们的 blob**
   （"overwriting a correct copy with an identical correct copy costs nothing"）
```

### ★★★ 六个 `TclsMappingResult` 与三条"失败也持有"路径

```cpp
① `!pathSize` ⇒ **NotRequested**
② `CreateFileMappingA(...)` 失败 ⇒ **CreateFailed**
③ blob 文件打不开 ⇒ **持有 mapping** + **BlobUnreadable**
④ 读空 ⇒ **持有 mapping** + **BlobUnreadable**
⑤ `MapViewOfFile` 失败 ⇒ **持有 mapping** + **MapFailed**
⑥ 成功 ⇒ `alreadyHeld ? **AlreadyVisible** : **Published**`
```

★★★ **⇒ 第 1915–1917 行注释（逐字）：**
```
"**KEEP THE HANDLE EVEN SO.** An **empty mapping under the right name** is still better than
 **no name at all** -- `OpenFileMapping` succeeds and **TenProxy reads zeroes**, which fails
 **somewhere later and more legibly than `[100]` before a socket is opened**."
```

★★★ **⇒ 名字格式（第 1836–1839 行）：**
```cpp
return "**TCLS_SHAREDMEMEMORY**" + std::to_string(GetCurrentProcessId());
```
★★★ **⇒ 注意拼写：`MEMEMORY`（M-E-M-E-M-O-R-Y,多一个 ME）⇒ 这是**原版的拼写**,不能改。**
**⇒ 映射大小 **4096 字节**,`PAGE_READWRITE`。**

---

## 十、★★★★★ **`ForceRecordValidator` 的停用理由（d27）**

### 10.1 ★★★★★ 完整注释（第 1698–1706 行，逐字）

```cpp
// ★★★ 2026-10-07 05:2x -- **停用（d27 实测教训；单变量）**：
//   它把校验器 `sub_806F20` 改成 `mov al,1; ret 4`,而该函数**同时是解析器** ——
//   跳过它 ⇒ 候选记录字段全 0（d27 实测：`room+0x7470+0x168 = 0`）
//   ⇒ 客户端把 `mmbook` 发给 0（`0A0000000000000000`）⇒ 回执推送（SenderID=userId）
//   对不上 ⇒ `mmstart` 不再出现（卡"战斗开始"）。
//   **正确的门强制在 backend 侧**：`Alwaysoffline` 插件里 arm 门控的门内补丁
//   （`CodolClientPatches.cpp`,RVA `0x3FAF1D/0x3FAF21/0x3FAF2C`）——不碰解析器。
//   保留函数与签名（仅停用）,日志会显示 `not_requested`。
return ClientProcessPatchResult::**NotRequested**;
```

★★★★★ **⇒ 六个精确值：**
```
`sub_806F20`（RVA **`0x406F20`**）**同时是校验器和解析器**
        ↓
★★★ 跳过它 ⇒ 候选记录字段**全 0**
★★★ d27 实测：**`room+0x7470+0x168 = 0`**
★★★ 客户端把 `mmbook` 发给 **0**（**`0A0000000000000000`**）
★★★ 回执推送（`SenderID = userId`）**对不上** ⇒ **`mmstart` 不再出现**（卡"战斗开始"）
        ↓
★★★★★ ⇒ **正确的门强制在 backend 侧**：
   `CodolClientPatches.cpp` 的 **RVA `0x3FAF1D` / `0x3FAF21` / `0x3FAF2C`**（**不碰解析器**）
```

### ★★★★★ **原实现的字节**（第 1690–1694 行）

```cpp
constexpr std::size_t CandidateRecordValidatorRva = **0x406F20**;
constexpr std::array<std::uint8_t, 5> CandidateRecordValidatorOriginal{
    **0x55, 0x8B, 0xEC, 0x51, 0x53**,          // push ebp; mov ebp,esp; push ecx; push ebx
};
constexpr std::array<std::uint8_t, 5> CandidateRecordValidatorPatched{
    **0xB0, 0x01, 0xC2, 0x04, 0x00**,          // mov al,1; ret 4
};
```

★★★ **⇒ `C2 04 00` = `ret 4` ⇒ `__thiscall` 单栈参。**

### ★★★★★ **校验器的逐字段类型流**（第 1675–1682 行，逐字）

```
//   * 客户端的候选记录是**带类型标签的顺序流**（`10 字符串 / 0a u64 / 07 i32 / 13 08 blob`）；
//   * 校验器 `sub_806F20`（**RVA `0x406F20`**,VA `0x806F20`）逐字段读：
//       **`10 字符串(≤64) → 0a u64 → 10 字符串(≤64) → 07 i32 ×N → … → 0a u64 → 07 i32 ×5`**
//     任一步标签/长度不对 ⇒ 返回 0；
//   * 返回 0 ⇒ 容器状态置 **3**、错误码 **4**（实测 `status_before:3 error_before:4`）
//     ⇒ 门 `sub_7FADC0` 不写 `ctx+4 = 1` ⇒ `AllocResultHandler(ok=0, data=NULL)`
//     ⇒ `server_index` 停在 **-1** ⇒ 客户端永远进不了 `mmbook/mmstart`。
```

★★★★★ **⇒ 完整的类型流与故障链：**
```
类型标签：**`10` 字符串 / `0a` u64 / `07` i32 / `13 08` blob**
        ↓
★★★ 校验器读序：**`10` 字符串(≤**64**) → `0a` u64 → `10` 字符串(≤64) → `07` i32 ×N → … → `0a` u64 → `07` i32 ×**5**`
★★★ 任一步标签/长度不对 ⇒ **返回 0**
        ↓
★★★ 返回 0 ⇒ 容器状态 = **3**、错误码 = **4**
★★★ 门 **`sub_7FADC0`** 不写 **`ctx+4 = 1`**
★★★ ⇒ `AllocResultHandler(ok=0, data=NULL)`
★★★ ⇒ **`server_index` 停在 `-1`**
        ↓
★★★★★ ⇒ **客户端永远进不了 `mmbook/mmstart`**
```

★★ **⇒ 与报告 107 的 `sub_7FADC0` 门**完全一致** ✓**
**⇒ 且报告 122 的 9 个 typed 标签在本文件里出现 **4 个**（`0x10` / `0x0a` / `0x07` / `0x13`）。**

---

## 十一、★★★★ **其余四个补丁**

### 11.1 ★★★ `UnsignedFastfile`（第 201–215 行）

```cpp
constexpr std::size_t UnsignedFastfileVerificationRva = **0x8371A**;
constexpr std::array<std::uint8_t, 8> UnsignedFastfileVerification{
    **0x83, 0x7C, 0x24, 0x08, 0x01, 0x0F, 0x94, 0xC0**,    // cmp [esp+8],1; sete al
};
constexpr std::array<std::uint8_t, 8> UnsignedFastfileVerificationReplacement{
    **0xB0, 0x01, 0x90, 0x90, 0x90, 0x90, 0x90, 0x90**,    // mov al,1 + 6 NOP
};
```

★★★★★ **⇒ 完整注释（第 201–206 行，逐字）：**
```
"CODREF(1649370 sub_4834F0): after **rsa_verify_hash_ex returns CRYPT_OK**,
 **0x0048371A converts its out-stat at [esp+8] into AL**. The eight original bytes are
 **`cmp [esp+8],1; sete al`**. Locally repacked zones cannot reproduce Tencent's signing key,
 so the opt-in replacement **accepts that verdict** while leaving **every earlier SHA-256
 comparison and every later zone-name/block check intact**."
```

★★★ **⇒ 关键：补丁在 **`rsa_verify_hash_ex` 成功之后**,只把**签名判定**改成恒真。**

### 11.2 ★★★ `patchClientBatteryDisplayBuffer` 的七字节补丁（第 846–864 行）

```cpp
if (image.size() < BatteryDivideRva + 7 ||
    image[0x6659C] != **0xEB** || image[0x6659D] != **0x4B**)
    return false;
std::array<std::uint8_t, 7> patched{**0xE9**, 0, 0, 0, 0, **0x90**, **0x90**};
const auto displacement = (int32_t)(replacement - (imageBase + BatteryDivideRva + **5**));
```

★★★ **⇒ `E9` + rel32 + 2 个 NOP ⇒ 5+2 = 7 字节 ✓**

### 11.3 ★★★ `validHostImage` 的三重校验（第 536–552 行）

```cpp
return nt->Signature == IMAGE_NT_SIGNATURE &&
    nt->FileHeader.Machine == **IMAGE_FILE_MACHINE_I386** &&
    nt->FileHeader.TimeDateStamp == **EngineBindings::ExpectedTimestamp** &&
    nt->OptionalHeader.SizeOfImage == **EngineBindings::ExpectedImageSize**;
```
★★★ **⇒ 三重：架构 + 时间戳 + 镜像大小。**
**⇒ 与报告 129 的 `DedicatedProcessPatches` **同一函数形态** ✓**

### 11.4 ★★★ `drainRawMouseDelta` 的 SRW 锁（第 298–312 行）

```cpp
AcquireSRWLockExclusive(&RawMouseLock);
const auto eventCount = RawMouseEventCount;
if (eventCount) { *deltaX = RawMouseDeltaX; *deltaY = RawMouseDeltaY;
                  RawMouseDeltaX = 0; RawMouseDeltaY = 0; RawMouseEventCount = 0; }
ReleaseSRWLockExclusive(&RawMouseLock);
return eventCount != 0;
```
★★★ **⇒ 排空式（读后清零）⇒ 累积的位移被一次性取走。**

---

## 十二、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **电池 HUD 五个地址** | HUD **`0x466450`** / 读 dvar **`0x46659E`** / **× 1000 @ `0x4665DA`** / 除数 **`0x4665EC`**/**`0x466610`** |
| 2 | ★★★★★ **电池除法 7 字节** | **`0x665E9`**：**`8B C7 99 F7 7C 24 0C`** = `mov eax,edi; cdq; idiv [esp+0xC]` |
| 3 | ★★★★★ **分发版 bypass 字节** | **`0x6659C = 0xEB`** / **`0x6659D = 0x4B`**（`jmp +0x4B`）⇒ 只对该构建生效 |
| 4 | ★★★★★ **电池 stub 的 7 个细节** | `pushfd`+`pushad` / `mov ebx,esp` / **`sub esp,528`** / **`and esp,0xFFFFFFF0`** / `fxsave`/`fxrstor` / **`mov [ebx+48],eax`** / 复原 3 条 + `jmp 0x665F0` |
| 5 | ★★★ `+48` 的构成 | `pushfd`(4) + `pushad`(32) + **12** = 48 ⇒ 正是 `idiv [esp+12]` 的操作数 |
| 6 | ★★★ 电池 dvar 的两条路径 | **`dvar[8] == 1`** ⇒ float（`+12`）；否则 string ⇒ `atof` |
| 7 | ★★★ 电池除数边界 | `multiplier × 1000`；非有限 / `< 1` / `> INT_MAX` ⇒ **1000** |
| 8 | ★★★ 两个 RVA | dvar 查找 **`0x36F190`** / 续点 **`0x665F0`** |
| 9 | ★★★★★ **`SetThreadExecutionState`** | 3.3.3.3 **`0x00643FE0`** / 1649370 **`0x00780860`**；IAT **`0x00B5B244`** → **`0x0E9D34A8`** |
| 10 | ★★★★★ **按导入签名重定的方法** | 导入名在文件里 ⇒ 跨 build 稳定；**每个 build 恰好一个调用点** |
| 11 | ★★★ `CL_MouseEvent` 的两个签名 | **{`ClipCursor`,`InterlockedExchange`,`QueryPerformanceCounter`}** / **{`GetCursorPos`,`GetForegroundWindow`,`ScreenToClient`}**；调用者 **`0xB0`** 字节 |
| 12 | ★★★ `ClientWindowHandle` 按位置 | `0x03749AAC` 在 **+0x10** 和 **+0x4F** ⇒ **`0x081AA758`**；邻居 **`0x081AA768`** |
| 13 | ★★★★★ **6 字节替换** | 原始 **`FF 15 A8 34 9D 0E`**（`call [0x0E9D34A8]`）⇒ **`83 C4 04 90 90 90`**（`add esp,4` + 3 NOP） |
| 14 | ★★★★★ **为什么必须 `add esp,4`** | WINAPI 调用**消耗了前面的 `push 2`** ⇒ 否则 `MainWndProc` **ESP 偏移** ⇒ **`/GS` cookie 检查** |
| 15 | ★★★★★ **`executionStateImportMatches`** | 读 IAT 槽 ⇒ 校验范围 ⇒ 读指针 ⇒ `GetProcAddress(kernel32,"SetThreadExecutionState")` ⇒ **比较** |
| 16 | ★★★ 判定只查 2 字节 | `[0]=0xFF` / `[1]=0x15`（后 4 字节是 IAT 地址,可重定位） |
| 17 | ★★★★★ **原始鼠标四常量** | 调用 **`0x37ADF2`**（**`E8 99 66 E3 FF`**）/ 函数 **`0x1B1490`** / 窗口句柄 **`0x7DAA758`** |
| 18 | ★★★★★ **stub 的三个参数** | `[ebp+8]` / `[ebp+12]` / **`[ebp+16]`（被 deltaY 覆盖）**；`add esp,12`；**`edi` 是返回值** |
| 19 | ★★★ 三个局部 | `[ebp-8]` = deltaX / `[ebp-12]` = deltaY / `[ebp-4]` = 保存的 edi |
| 20 | ★★★★★ **`WM_INPUT` 四过滤** | `GetRawInputData == size` / `RIM_TYPEMOUSE` / **`!(usFlags & MOUSE_MOVE_ABSOLUTE)`** / 非零位移 |
| 21 | ★★★ `RegisterRawInputDevices` | **`usUsagePage=0x01`** / **`usUsage=0x02`** / **`dwFlags=0`**（**不用 `RIDEV_INPUTSINK`**） |
| 22 | ★★★★★ **`CL_ParseGamestate` 两遍** | **`0x454A54`**（普通,arg **1**）/ **`0x454B55`**（模块化,arg **0**）；中间有 `defaultweapon`/`defaultknife` |
| 23 | ★★★ `sub_59B560` | RVA **`0x19B560`** |
| 24 | ★★★★★ **alpha 恢复只做一次** | **`cmp edi, 1`**（循环 **1..1699** 的第一次）+ **尾跳** |
| 25 | ★★★★★ **`LoopFx` 序言** | `sub_4DAE70` = **`0xDAE70`**，**`55 8B EC 83 EC 20`**（`push ebp; mov ebp,esp; sub esp,20h`） |
| 26 | ★★★ `LoopFx` 的两层空检查 | `[esp+8]`（descriptor）+ **`[eax]`**（effect 指针） |
| 27 | ★★★★★ **`LoopFx` 的 18 个调用者** | 首次经 `CG_AddLoopFx`,后来经 **`out.exe+0x131C7B`** |
| 28 | ★★★★★ **`EntityEvent` 武器读** | **`0x132A76`**：**`80 B9 F3 0E 00 00 00`** = `cmp byte ptr [ecx+0x0EF3],0`；函数自己的空检查在 **`0x00532A9C`** |
| 29 | ★★★ 三个续点 | 正常 **`0x132A7D`** / 空武器 **`0x132A8C`** / 函数入口 **`0x132910`** |
| 30 | ★★★★★ **`EntityEvent` 范围守卫** | 序言 **`55 8B EC 83 E4 F8`**；上界 **`0xB8` = 184**；超界 ⇒ **`ret 8`**（`__stdcall` 2 参） |
| 31 | ★★★ 实体号/类型偏移 | **`entity+0xF4`**（号）/ **`entity+0xF8`**（`eType`）；上限 **16** 次 |
| 32 | ★★★★★ **弹药查找** | `sub_421A70`；10 字节 **`55 8B EC 8B 0C 85 50 8B 98 01`**；武器表基址 **`0x01988B50`**；解引用 **`WeaponDef+0x7F4`** |
| 33 | ★★★★★ **武器库存守卫** | **`0x2C146`**；7 字节 **`8B 0C 85 50 8B 98 01`**；上界 **`0x06A3` = 1699**；指针下界 **`0x10000`** |
| 34 | ★★★★★ **UI 运算符解析器** | `sub_5A41E0`；序言 **`55 8B EC 51 8B 17`**；运算符 **`0x13` = 19**（20 个）；类型 **`2`**（3 种）⇒ **20 × 3 × 3** |
| 35 | ★★★ UI 守卫的五重校验 | `eax<=19` / `edi!=0` / `[edi]<=2` / `edx!=0` / `[edx]<=2`；失败 ⇒ **`ret 4`** |
| 36 | ★★★★★ **UnlockAll 谓词** | **`sub_5E3550`**（RVA **`0x1E3550`**）；逻辑 `a1 == onboardCharacterID \|\| (a1 > 0 && sub_80A5E0(a1))` |
| 37 | ★★★★★ **替换 3 字节** | **`B0 01 C3`**（`mov al,1; ret`）；自身成功路径 **`b0 01 59 c3`** |
| 38 | ★★★★★ **15 字节签名** | `[0]0x51 [1]0x6A [2]0x00 [3]0x68 [8]0xE8 [13]0x83 [14]0xC4 [15]0x08 [16]0x3B [17]0xF0 [18]0x75 [19]0x04 [20]0xB0 [21]0x01 [22]0x59` |
| 39 | ★★★★★ **跳过的两个区间** | **`[4..7]`**（字符串地址）+ **`[9..12]`**（调用位移）⇒ 重定基后会变 |
| 40 | ★★★★★ **config 两个门** | 写 **`0xFDBCC`** `75 6E`→**`EB 6E`**；读 **`0xF3119`** `75 34`→**`EB 34`** |
| 41 | ★★★★★ **"ON BY DEFAULT"** | 打过补丁后写明文 ⇒ 不打补丁的启动解密失败 ⇒ **`0x004F3144`** 检查失败 ⇒ **静默忽略** ⇒ 设置全丢 |
| 42 | ★★★★★ **"BOTH OR NEITHER"** | 只补写 ⇒ 明文被解密；只补读 ⇒ 加密文件被执行；**半应用比不应用更糟** |
| 43 | ★★★★★ **`com_maxfps`** | MAX 的 `push 200` = **`68 C8 00 00 00`** @ **`0xFC408`**；**DEFAULT @ `0xFC40F` 不动** |
| 44 | ★★★ 范围 | **1..10000** |
| 45 | ★★★★★ **TCLS 名字** | **`TCLS_SHAREDMEMEMORY<pid>`**（注意 **MEMEMORY** 拼写）；**4096 字节**,`PAGE_READWRITE` |
| 46 | ★★★★★ **`OpenFileMapping` 的陷阱** | **19:12:42** 从 pid **364** 看"已存在"；**19:12:43** 同进程 `fail! Error code = 2` |
| 47 | ★★★★★ **"looking without holding"** | **命名段在最后一个句柄关闭时消亡** ⇒ 诊断本身改变了结果 |
| 48 | ★★★★★ **"持有 ≠ 正确"** | `SampleLauncher` **预发布 512 个映射**并终身持有 ⇒ 第二次运行拿到**旧 blob** ⇒ **认证服务器 20 分钟什么也没看到** |
| 49 | ★★★ 三条"失败也持有" | blob 打不开 / 读空 / `MapViewOfFile` 失败 ⇒ **都保留句柄** |
| 50 | ★★★★★ **`ForceRecordValidator` 停用** | `sub_806F20`（**`0x406F20`**）**同时是校验器和解析器**；跳过 ⇒ 字段全 0（`room+0x7470+0x168 = 0`）⇒ `mmbook` 发给 **0** ⇒ `mmstart` 不出现 |
| 51 | ★★★★★ **正确的门** | backend 侧 `CodolClientPatches.cpp` RVA **`0x3FAF1D` / `0x3FAF21` / `0x3FAF2C`** |
| 52 | ★★★★★ **候选记录类型流** | **`10` 字符串(≤64) → `0a` u64 → `10` 字符串(≤64) → `07` i32 ×N → … → `0a` u64 → `07` i32 ×5** |
| 53 | ★★★★★ **故障链** | 返回 0 ⇒ 容器状态 **3** / 错误码 **4** ⇒ 门 **`sub_7FADC0`** 不写 **`ctx+4 = 1`** ⇒ `server_result = -1` ⇒ **永不进 `mmbook/mmstart`** |
| 54 | ★★★★★ **`UnsignedFastfile`** | **`0x8371A`**：**`83 7C 24 08 01 0F 94 C0`**（`cmp [esp+8],1; sete al`）⇒ **`B0 01` + 6 NOP** |
| 55 | ★★★ 前提 | **`rsa_verify_hash_ex` 已返回 `CRYPT_OK`** ⇒ 只放开**签名判定** |
| 56 | ★★★ `validHostImage` 三重 | `Machine == I386` && `TimeDateStamp == ExpectedTimestamp` && `SizeOfImage == ExpectedImageSize` |

---

## 十三、结论

### 1. ★★★★★ **十六个客户端补丁面全部逐字节记录**

### 2. ★★★★★ **电池 HUD 的 `fxsave` 栈处理是精细活的范例**

★ **⇒ `sub esp,528` + `and esp,0xFFFFFFF0` + `mov [ebx+48],eax` 三者的算术必须严丝合缝。**

### 3. ★★★★★ **`SetThreadExecutionState` 的 6 字节替换必须保留 `add esp,4`**

★ **⇒ 否则 `MainWndProc` 的 `/GS` cookie 检查会失败。**

### 4. ★★★★★ **按"导入签名"重定 RVA 是跨 build 最稳的方法**

★ **⇒ `CL_MouseEvent` 的两个三 API 签名在两个 build 里都唯一,且调用者都是 `0xB0` 字节。**

### 5. ★★★★★ **`CL_ParseGamestate` 的两遍遍历是 alpha 武器恢复的精确边界**

★ **⇒ 只在 `edi == 1`（循环第一次）时恢复,并尾跳。**

### 6. ★★★★★ **`UnlockAll` 的 15 字节签名跳过两个可重定位区间**

### 7. ★★★★★ **`config_mp.cfg` 的"默认开启"是**避免陷阱**,不是偏好**

★ **⇒ 一个遗忘的环境变量就让玩家丢失全部设置,且无任何错误提示。**

### 8. ★★★★★ **TCLS 的两个教训都是"诊断改变了被测量的东西"**

★ **⇒ ① `OpenFileMapping` 后关句柄 ⇒ 名字在我们看后消失；**
**⇒ ② 持有别人的映射 ⇒ 拿到**旧 blob** ⇒ 认证服务器 20 分钟什么也没看到。**

### 9. ★★★★★ **`ForceRecordValidator` 的停用是 d27 的单变量实测结论**

★ **⇒ `sub_806F20` 同时是**校验器和解析器**,跳过它字段全 0 ⇒ `mmbook` 发给 0。**

### 10. ★★★★★ **候选记录的类型流（`10`/`0a`/`07`/`13`）与故障链（状态 3 / 错误码 4 / `server_index = -1`）**

---

## 十四、下一步

`game_server` 根剩余：

1. ★ **`EngineBindings.cpp`（917,344 B）** + `EngineBindings.hpp`（133,088 B）
2. ★ **`Appmain.cpp`（565,999 B）**
3. `NativePmoveBindings.cpp`（113,000 / **2,090 行**）
4. 然后 `server_mp` 154 文件（12,604,630 B）
