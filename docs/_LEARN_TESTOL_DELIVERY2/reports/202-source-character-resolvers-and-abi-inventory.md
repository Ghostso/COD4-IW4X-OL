# 202 · 两个角色解析器的签名、五类自定义 ABI 调用器

## 一、范围

本报告学习 `EngineBindings.cpp` 1766–1945 行。

## 二、`sub_619AD0`：两次遍历，第二次填默认

```cpp
// sub_619AD0(record, characterItemId). __cdecl, two stack arguments, no return
// value that matters. It makes TWO passes over the twelve-entry record:
// the first marks which entries are occupied and which extra entries each
// occupying item claims, and the second FILLS every entry still empty from
// the character's own per-slot default table.
// That second pass is why this port supplies one id.
using CharacterRecordFillDefaults = void(__cdecl*)(void*, int);
```

### 2.1 两次遍历

```text
第一遍：标记哪些条目被占、以及每个占用的物品声明了哪些额外条目
第二遍：用【角色自己的 per-slot 默认表】填每一个仍然空的条目
```

⇒ **这就是为什么本移植只提供一个 id** —— 其余十一个由引擎推导。

### 2.2 "每个占用的物品声明了哪些额外条目"

这是**一次物品可能占多个记录条目**的机制。与 §200 里 `CharacterRecordToSelectionName{11,0,1,...,11,9}` 中 `11` 出现两次呼应 —— **一个物品可以声明多个条目**。

## 三、`sub_61B6C0`：`0x2C` = 十一个 char*

```cpp
// sub_61B6C0(names, record, baseItemId, variant). __cdecl, four stack arguments,
// `add esp, 0x10` at its only call site. It memsets `names` to 0x2C -- ELEVEN
// char* -- and maps record entries 1..9 to names 0..8 and entry 11 to name 9,
// skipping entries 0 and 10.
using CharacterRecordToSelectionNames = void(__cdecl*)(void*, const void*, int, int);
```

### 3.1 映射表

```text
记录条目 1..9  →  名字 0..8
记录条目 11    →  名字 9
跳过条目 0 与 10
```

**条目 0 没丢**：

> 条目 0 没有丢失：`sub_619E90` 的尾部单独解码它，**而它正是 `baseItemId`**。

**条目 10 直接跳过** —— 与 §200 的 `{11,0,1,2,3,4,5,6,7,8,11,9}` 对照：

```text
索引:  0   1  2  3  4  5  6  7  8  9  10  11
值:   11   0  1  2  3  4  5  6  7  8  11   9
```

**索引 0 → 11**（条目 0 映射到名字 11？而名字数组只有 11 项 0..10，所以 11 越界了）……

**这需要谨慎**。表里 `{11, 0, 1, ...}` 的语义可能是"名字 i 来自记录条目 x[i]"：

```text
名字 0  ← 条目 11
名字 1  ← 条目 0
名字 2  ← 条目 1
...
名字 8  ← 条目 7
名字 9  ← 条目 8
名字 10 ← 条目 11  ← 重复！
```

**与注释"条目 1..9 → 名字 0..8、条目 11 → 名字 9"不符**。

两个可能的解释：

1. 那个数组是**另一个方向**的映射（记录→名字）；
2. 数组的索引与条目的对应关系与注释描述的是不同版本。

**这里存在一处需要核对的矛盾** —— 我把它记为未闭合点。

### 3.2 `0x2C` 的守卫意义

§197 里提到 `CharacterRecordToSelectionNamesPrefix` 的 `6A 2C` 就是 `push 0x2C`：

> **一个选择名数组不再是一个 dword 的构建，会正好在那个说出这一点的字节上失败。**

`0x2C = 44 = 11 × 4` ✓

## 四、`invokeCharacterSlotGet`：包一层 `__try`

```cpp
std::optional<int> invokeCharacterSlotGet(int(__cdecl*)(int,int) function,
    int characterIndex, int slot) noexcept
{
    if (!function) return std::nullopt;
    __try { return function(characterIndex, slot); }
    __except (EXCEPTION_EXECUTE_HANDLER) { return std::nullopt; }
}
```

注释：

> **`sub_50FF30` 读公开 profile，而 profile 未解析时【会 fault】**，所以它被包在与这里每一个其它原生读同一个守卫后面。

**普通 cdecl，两个 int 参数** —— 所以不需要汇编块，只需要 `__try`。

## 五、`invokeWeaponClassFieldGet`：ECX + EDX + 栈

```cpp
// ecx = element index (-1 for a scalar field), edx = the field name,
// one stack dword = the class index. Plain `retn`, so this pops it.
// The engine has already un-obfuscated the value and subtracted one, so
// what comes back is the item id, or 0 for an empty slot.
__asm {
    mov ecx, elementIndex
    mov edx, field
    push classIndex
    call function
    add esp, 4
    mov value, eax
}
```

### 5.1 三处入口

```text
ECX = 元素索引（-1 表示标量字段）
EDX = 字段名
栈  = 职业索引
```

### 5.2 "普通 `retn`，所以它弹掉那个"

> **普通 `retn`，所以它弹掉那个** —— 即被调用者用 `ret 4` 还是 `ret`？

注释说"**this pops it**" —— 指的是**调用者在 `add esp, 4` 里弹**（因为 `retn` 不弹参数）。

对照 §186 的 `WeaponClassFieldGetRva` 注释："Plain `retn`, so the CALLER pops the stack argument" ✓

### 5.3 引擎已经做过的事

> **引擎已经把值解混淆并减一，所以回来的是物品 id，或空槽的 0。**

**两步都在引擎里**，所以调用方看到的是干净值。

## 六、`invokeCharacterItemsCopy`：EAX + 栈 + 十二项要求

```cpp
// The member index goes in EAX; see the CODDIFF on characterCurrentItemsCopy_.
// `records` must have room for TWELVE entries: the engine writes all twelve on
// both arms, including the one where its own gate said no.
__asm {
    mov eax, memberIndex
    push records
    call function
    add esp, 4
}
```

**"两条分支上都写十二个"** 与 §200 里那句"它在两条分支上都这么做"完全一致。

## 七、`invokeLevelZoneLoad`：ECX + 栈

```cpp
__asm {
    push mapName
    mov ecx, gameType
    call function
    add esp, 4
}
```

**`gameType` 在 ECX、`mapName` 在栈**。

**参数顺序值得注意**：声明是 `(function, mapName, gameType)`，而 `mapName` 走栈、`gameType` 走 ECX —— 所以**第一个参数走栈、第二个走寄存器**。

## 八、`invokeCollisionMapLoad`：ECX + 两个栈参数

```cpp
__asm {
    mov ecx, mapName
    push gameType
    push bspName
    call function
    add esp, 8
}
```

**`mapName` 在 ECX**（第三个参数走寄存器），`bspName` 与 `gameType` 走栈。

**压栈顺序 `gameType` 先、`bspName` 后** ⇒ `bspName` 在 `[esp+0]`（第一个栈参数）✓

## 九、`invokeNoArgument`：只有 `call`

```cpp
__asm { call function }
```

**最快的适配器** —— 但依然有 `__try`。

## 十、`invokeSVLinkEntity`：EAX + 可选的异常详情

```cpp
__asm {
    mov eax, entity
    mov edx, function
    call edx
}
completed = true;
__except (captureNativeException(GetExceptionInformation(), exceptionDetails))
```

**`exceptionDetails` 是可选的（默认 nullptr）** —— 而 `captureNativeException` 内部检查 `if (exception && exception->ExceptionRecord && details)`，所以传 nullptr 是安全的。

**这是第一个用完整 `captureNativeException` 而不是精简 `captureNativeFault` 的** —— 因为它可能需要寄存器。

## 十一、本组新增的六种 ABI

| 适配器 | 参数位置 | `__try` | 异常详情 |
|---|---|---|---|
| `invokeCharacterSlotGet` | 栈 2（普通 cdecl） | ✓ | 无 |
| `invokeWeaponClassFieldGet` | **ECX + EDX + 栈 1** | ✓ | 无 |
| `invokeCharacterItemsCopy` | **EAX + 栈 1** | ✓ | 无 |
| `invokeLevelZoneLoad` | **ECX + 栈 1** | ✓ | 无 |
| `invokeCollisionMapLoad` | **ECX + 栈 2** | ✓ | 无 |
| `invokeNoArgument` | 无 | ✓ | 无 |
| `invokeSVLinkEntity` | **EAX** | ✓ | **完整** |

**到 §202 为止，本文件已出现 21 种调用适配器**，其中 12 种是自定义寄存器约定。

## 十二、关键结论

1. **`sub_619AD0` 的第二遍遍历用角色默认表填空** ⇒ 本移植只提供一个 id。
2. **`sub_61B6C0` 跳过条目 0 和 10**，而条目 0 的值由 `sub_619E90` 尾部单独解码。
3. **`CharacterRecordToSelectionName` 数组与注释描述的映射存在一处需要核对的矛盾**。
4. **`invokeWeaponClassFieldGet` 的字段名走 EDX、元素索引走 ECX**，与普通约定完全不同。
5. **`invokeLevelZoneLoad` 的 mapName 走栈、gameType 走 ECX** —— 第一个参数在栈上，第二个在寄存器。
6. **`invokeSVLinkEntity` 是第一个用完整异常捕获（含寄存器）的**，且 `exceptionDetails` 可选。

## 十三、未闭合点

- `CharacterRecordToSelectionName{11,0,1,2,3,4,5,6,7,8,11,9}` 与"条目 1..9→名字 0..8、条目 11→名字 9"的映射关系需核对。
- `EngineBindings.cpp` 1945 行之后未读取。
