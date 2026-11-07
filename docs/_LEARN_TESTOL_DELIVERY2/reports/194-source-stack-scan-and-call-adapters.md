# 194 · 栈扫描的三类返回地址、六种调用适配器

## 一、范围

本报告学习 `EngineBindings.cpp` 309–488 行。

## 二、栈扫描：三类 `call` 编码

```cpp
const auto limit = base + 0x0E5D6000;   // 【3.3.3.3 的 SizeOfImage】，见下
auto esp = (uintptr_t)context->Esp;
int found = 0;
for (slot = esp; slot < esp + 0x400 && found < 14; slot += 4) {
    if (!witnessCanRead(slot, sizeof(uintptr_t))) break;   // 【不是 continue】
    value = *(uintptr_t*)slot;
    if (value < base + 0x1000 || value >= limit) continue; // .text 范围
    before = (const uint8_t*)value;
    if (!witnessCanRead(before - 6, 6)) continue;
    afterCall = before[-5] == 0xE8
             || (before[-6] == 0xFF && (before[-5] & 0x38) == 0x10)
             || (before[-2] == 0xFF && (before[-1] & 0xF8) == 0xD0);
    if (!afterCall) continue;
    ... 追加 " 0x%07X" ...
    ++found;
}
```

### 2.1 三类 `call` 编码

```text
1.  before[-5] == 0xE8
        E8 rel32                    call rel32（相对调用）

2.  before[-6] == 0xFF && (before[-5] & 0x38) == 0x10
        FF /2 = call r/m32          call [mem] 或 call reg
        ModRM 的 reg 字段 = 2 ⇒ bits 3..5 = 010 ⇒ (x & 0x38) == 0x10

3.  before[-2] == 0xFF && (before[-1] & 0xF8) == 0xD0
        FF /2 with ModRM = D0..D7   call eax/ecx/edx/ebx/esp/ebp/esi/edi
        (x & 0xF8) == 0xD0 覆盖全 8 个寄存器
```

**第二类是"内存/寄存器间接调用"的通用形式**（`FF 15` 是 `call [abs32]`，`FF 55 xx` 是 `call [ebp+disp8]` 等）；**第三类是"寄存器调用"的特化**（`FF D0` = `call eax`）。

**第三类其实是第二类的特例**（`FF D0` 也满足第 2 类吗？`before[-5]` 在 `FF D0` 里是 `D0`，`0xD0 & 0x38 = 0x10` ✓，但 `before[-6]` 是**更早一个字节**，不一定等于 `0xFF`）。所以两类**不能互相替代**——`call eax` 只有 2 字节。

### 2.2 `break` 而不是 `continue`

```cpp
if (!witnessCanRead(slot, ...)) break;
```

**栈不可读意味着已经越过栈顶**（或者是守卫页），**再往后读没有意义** —— 所以 `break` 而不是 `continue`。

### 2.3 那个 `limit` 是**3.3.3.3 的**尺寸

```cpp
const auto limit = base + 0x0E5D6000;
```

而 §183 里明确：

```cpp
ExpectedImageSize = 0x0E659000;   // 本地覆盖，实际镜像
// 注释说：上游 out.exe 是 0x0E5D6000
```

**所以这里是硬编码的上游值** —— 对本 build（`0x0E659000`）来说，`0x0E5D6000..0x0E659000` 之间的地址会被**当作"不在 .text"而跳过**。

那是 **0x80000 = 512 KB** 的范围。这个范围在 `SizeOfImage` 之内，所以是真实映射的——**但它在 `.text` 之后吗？** 取决于节表。如果 `.text` 结束早于 `0x0E5D6000`，那这个 `limit` 是无害的保守上界；如果 `.text` 跨过它，则会漏掉一部分返回地址。

**这是一个应当指出的不一致**：`ExpectedImageSize` 已经改成 `0x0E659000`，而这里的 `limit` 仍是旧值。

### 2.4 上限 14 个 + 缓冲 352 字节

```cpp
found < 14
char frames[352]
```

每条 `" 0x%07X"` 是 1 + 2 + 7 = **10 字节**，14 条 = 140 字节，加上前缀 `"  stack scan"`（12 字节）= **152 字节**，远小于 352。**352 是保守的**。

`written` 的边界检查：

```cpp
if (written < 0 || (size_t)written >= sizeof(frames)) break;
const auto added = snprintf(frames + written, sizeof(frames) - written, ...);
if (added > 0) written += added;
```

**`written < 0`** 检查 `snprintf` 的编码错误（理论上可能）。

## 三、六种调用适配器

### 3.1 `tryCallVoid` —— 无参数

```cpp
__try { ((void(__cdecl*)())function)(); return true; }
__except (captureNativeFault(GetExceptionInformation(), fault)) { return false; }
```

注意 `__except` 里调用 `captureNativeFault(...)` —— **返回值就是异常处理常量**（`EXCEPTION_EXECUTE_HANDLER`）。

### 3.2 `tryWeaponLookup` / `tryWeaponResolve` —— 为什么要分开

```cpp
// OLMOD(weapon-registry-stages): the lookup and the register live
// inside ONE native resolver call, so a fault in either surfaced
// identically. Calling the lookup separately first splits them: if this
// faults the table is corrupt, and if only the resolver faults the
// REGISTRATION is what dies.
```

**"查表"与"注册"在同一个原生调用里 ⇒ 崩溃表现相同**。分开调用就把两者区分开。

**这是一个很实用的诊断技巧**：把复合调用拆成两步，让崩溃位置有信息量。

### 3.3 `invokeConfigStringGet` —— ESI 参数

```cpp
// CODDIFF(1649370): the index goes in ESI. See EngineBindings.hpp.
// ESI is callee-saved under cdecl and is an ARGUMENT here, so the
// callee is free to clobber it - save it across the call.
if (!function) return nullptr;
const char* result{};
__asm {
    push esi
    mov esi, index
    mov edx, function
    call edx
    mov result, eax
    pop esi
}
```

**注释揭示了那个矛盾**：

> `ESI` 在 cdecl 下是**被调用者保存的**，**而它在这里是参数** —— 所以**被调用者可以随意破坏它** —— **在调用前后保存它**。

即：**同一个寄存器在这里既是"参数"又是"需要保存的"**，所以必须 `push`/`pop`。

**这里没有 `__try`** —— 与其它几个不同。可能因为 `nativeConfigString` 的调用者已经在外层守卫，或者这是一个已知安全的路径。

### 3.4 `invokeServerDObjGet` —— EAX 参数

```cpp
__asm {
    mov eax, entity
    mov edx, function
    call edx
    mov result, eax
}
```

**EAX 传入实体指针，EAX 返回 DObj** —— 参数与返回值同寄存器。

**同样没有 `__try`**。

### 3.5 `invokeCCSGetConstantString` —— EAX + ECX + 栈

```cpp
__asm {
    mov eax, constantType
    mov ecx, index
    lea edx, resolved
    push edx            ; 输出指针在栈上
    mov edx, function
    call edx
    add esp, 4
    mov succeeded, eax
}
```

**三个入口**：EAX = 类型、ECX = 索引、栈 = 输出指针。

**这个有 `__try`** —— 且返回 `succeeded != 0`（原生返回码）。

**注意 `mov edx, function` 在 `push edx` 之后** —— 因为 `edx` 先被用作输出指针。

### 3.6 `invokeDirectionToAngles` —— ESI 入 / EDI 出

```cpp
// CODREF(1649370): vectoangles 764C10, ESI=input, EDI=output;
// no stack arguments. 764D20 is the signed-angle variant.
```

**两个变体**：`764C10`（无符号）与 `764D20`（有符号）。

## 四、六种适配器的调用约定汇总

| 适配器 | 入参位置 | 出参 | `__try` |
|---|---|---|---|
| `tryCallVoid` | 无 | 无 | ✓ |
| `tryWeaponLookup` | 栈（cdecl） | EAX | ✓ |
| `tryWeaponResolve` | 栈（cdecl，2 参数） | EAX | ✓ |
| `invokeConfigStringGet` | **ESI** | EAX | ✗ |
| `invokeServerDObjGet` | **EAX** | EAX | ✗ |
| `invokeCCSGetConstantString` | **EAX + ECX + 栈** | EAX + 栈 | ✓ |
| `invokeDirectionToAngles` | **ESI + EDI** | EDI | ✓ |

**五种不同的自定义约定**，每一种都要单独的 `__asm` 块。

**注释里给出的地址与寄存器**（`vectoangles 764C10`、`ESI=input, EDI=output`）说明这些都是从反汇编直接读出来的，而不是推断的。

## 五、关键结论

1. **三类 `call` 编码**：`E8 rel32`、`FF /2`（间接）、`FF D0..D7`（寄存器）。
2. **栈不可读时 `break` 而不是 `continue`**，因为已越过栈顶。
3. **`limit = base + 0x0E5D6000` 是上游值**，与实际 `SizeOfImage 0x0E659000` 不一致（差 0x80000）。
4. **把复合原生调用拆成两步能让崩溃位置有信息量**。
5. **`ESI` 既是参数又需保存**——这是自定义 ABI 与 cdecl 保存规则冲突的直接后果。
6. **六种适配器对应五种自定义约定**，每一个都要单独汇编块。

## 六、未闭合点

- 栈扫描的 `limit` 未随 `ExpectedImageSize` 更新。
- `invokeConfigStringGet` 与 `invokeServerDObjGet` 无 `__try`，其失败语义未在本组说明。
- `EngineBindings.cpp` 488 行之后未读取。
