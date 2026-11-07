# 195 · 六种调用适配器（续）与"返回 1 的函数被当作指针"

## 一、范围

本报告学习 `EngineBindings.cpp` 488–668 行。

## 二、`invokeDirectionToAngles` 的收尾

```cpp
__asm {
    mov esi, direction
    mov edi, output
    mov eax, function
    call eax
}
```

**ESI 入、EDI 出、EAX 调函数** —— 三个寄存器并行使用。

## 三、四个新的 `try*` 适配器

### 3.1 `tryLinkXAssetEntry` —— 普通 cdecl

```cpp
entry = ((void*(__cdecl*)(uint32, void**))function)(type, header);
```

**两个栈参数，返回值是 `void*`** —— 与 `DBLinkXAssetEntry` 的 typedef 一致。

### 3.2 `trySetXAssetEntryZone` —— 只写一次

```cpp
if (!entry || !zone) return false;
auto* bytes = (uint8_t*)entry;
if (!bytes[16]) bytes[16] = zone;
return bytes[16] != 0;
```

**三个要点**：

1. **`entry` 为 `void*`，按字节索引 `[16]`** —— 不假设结构；
2. **只在为空时写** —— 不覆盖已有值；
3. **返回"写完后的值非零"** —— 而不是"写成功"，所以**如果原来就有值也会返回 true**。

`zone` 为零时直接拒绝 —— 因为零在字节层面等于"未设置"。

### 3.3 `tryInitializeGfxImage` —— 同一指针传两次

```cpp
((void(__cdecl*)(void**, void*))function)((void**)image, image);
```

**与 `sub_BE7470(header, header)` 完全同构** —— 第一个参数是槽位地址，第二个是 image 本身。因为 load-def 指针到达时在 `image+0`。

### 3.4 `tryInternScriptString` —— 三参数 + 范围校验

```cpp
interned = ((uint32(__cdecl*)(const char*, uint32, uint32))function)(
    value, 4, (uint32)(strlen(value) + 1));
if (!interned || interned > 0xFFFF) return false;
result = (uint16)interned;
```

**三个参数**：

```text
value       字符串
4           kind（zone loader 用的那个）
strlen+1    长度，含 NUL
```

**双重校验**：非零 且 ≤ 0xFFFF（因为结果是 `uint16`）。

`strlen(value) + 1` 与之前 §154 的"`length` 计 NUL"一致。

### 3.5 `tryQueueXModelStream` —— ESI + 栈

```cpp
__asm {
    mov esi, model
    movzx eax, priority
    push eax
    mov eax, function
    call eax
    add esp, 4
}
```

**两个参数分两处**：`model` 在 **ESI**、`priority` 在 **栈**。

`movzx eax, priority` —— 把 `uint8` 零扩展成 32 位再压栈。

### 3.6 `invokeEvaluateTrajectory` —— 三个寄存器

```cpp
// CODREF(1649370): 410BD0, EAX=time, ECX=plain trajectory, EDI=out.
// Callee's EAX result is incidental; all three coordinates are output.
__asm {
    mov eax, atTime
    mov ecx, trajectory
    mov edi, output
    mov edx, function
    call edx
}
```

**EAX = 时间、ECX = 轨迹指针、EDI = 输出** —— 三个都是寄存器参数。

**"被调用者的 EAX 返回值是附带品；三个坐标全是输出"** —— 所以不读 EAX。

这与 §151 里"`BG_EvaluateTrajectory 0x410BD0` 读朴素 36 字节轨迹"直接对应，而 `0x410EA0` 是地址混淆变体（这里用的是朴素入口）。

### 3.7 `invokeDObjFree` —— ESI + 提前拒绝

```cpp
if (!function || !dobj) return false;
__asm { mov esi, dobj; mov eax, function; call eax; }
```

**与 `invokeServerDObjGet` 是同一族**，但参数在 ESI 而不是 EAX。

## 四、十种适配器的完整清单

| 适配器 | 参数位置 | 返回 | `__try` |
|---|---|---|---|
| `tryCallVoid` | 无 | — | ✓ |
| `tryWeaponLookup` | 栈 1 | EAX | ✓ |
| `tryWeaponResolve` | 栈 2 | EAX | ✓ |
| `tryLinkXAssetEntry` | 栈 2 | EAX | ✓ |
| `trySetXAssetEntryZone` | (直接内存) | 布尔 | ✓ |
| `tryInitializeGfxImage` | 栈 2（同一指针×2） | — | ✓ |
| `tryInternScriptString` | 栈 3 | EAX | ✓ |
| `tryQueueXModelStream` | **ESI + 栈 1** | — | ✓ |
| `invokeConfigStringGet` | **ESI** | EAX | ✗ |
| `invokeServerDObjGet` | **EAX** | EAX | ✗ |
| `invokeCCSGetConstantString` | **EAX + ECX + 栈** | EAX + 栈 | ✓ |
| `invokeDirectionToAngles` | **ESI + EDI** | EDI | ✓ |
| `invokeEvaluateTrajectory` | **EAX + ECX + EDI** | EDI | ✓ |
| `invokeDObjFree` | **ESI** | — | ✓ |

**共 14 个**，其中 **9 个是自定义寄存器约定**。

## 五、`serverDObjGetAdapter`：返回 1 的函数被当成指针

这是本组最有价值的一段。

```cpp
// THE FUNCTION THIS USED TO CALL IS A PREDICATE ON THIS BUILD, NOT A GETTER.
// ServerDObjGetRva 0x34E160 is sub_74E160 in out.exe, and it decompiles to
//     v1 = word_77E7F20[(a1 - &unk_31437A0) / 712];
//     return v1 && (&unk_77E9720 + 216 * v1) != 0;
// -- a BOOL. It returned literally 1, which is non-null, so every caller sailed
// past its null check and then failed on the first read through the "pointer".
```

### 5.1 三重错误链

```text
1. 名字叫 ServerDObjGet，但实际是【谓词】不是 getter
2. 它返回 BOOL（0 或 1）
3. 1 是"非空"，所以每个调用者的 null 检查都通过
4. 然后在第一次通过那个"指针"读取时崩
```

**"返回 1，是 non-null，所以每个调用者都从 null 检查旁边驶过"** —— 这是最坏的一类错误：**它让检查失效**。

### 5.2 反编译给出的两个全局

```text
word_77E7F20[(a1 - &unk_31437A0) / 712]     ← 索引表
&unk_77E9720 + 216 * v1                      ← 池，步长 216 = 0xD8
```

**216 = 0xD8** —— 与 §192 里 DObj 池步长完全一致，交叉验证。

而 `/ 712` 是**实体到索引的除法**（712 可能是 gentity 尺寸的倍数）。

### 5.3 新适配器自己实现

```cpp
void* __cdecl serverDObjGetAdapter(const int32 entityNum)
{
    base = ServerDObjEntityBase.load(acquire);
    if (!base || entityNum < 0 || (uint32)entityNum >= NativeServerEntityCapacity(2046))
        return nullptr;
    ...
}
```

**自己按实体号查，不调那个谓词**。

注意 `entityNum < 0` 的检查 —— 参数是 `int32` 而容量是 `uint32`，所以负数必须在转换**之前**拒绝，否则会变成巨大的正数。

## 六、`NativeServerEntityCapacity = 2046` 的复用

```cpp
constexpr std::uint32_t NativeServerEntityCapacity = 2046;
constexpr std::uint32_t NativeServerDObjCapacity = 2048;
```

**两个不同**：实体 2046（= `EntityNumWorld`），DObj 2048。

**DAObj 池比实体池大 2** —— 因为 DObj 还包括非实体的东西（viewmodel、世界模型等）。

## 七、关键结论

1. **14 个调用适配器里 9 个是自定义寄存器约定**，每一个都要单独汇编块。
2. **`trySetXAssetEntryZone` 返回"写完后的值非零"而不是"写成功"**，所以原来有值也返回 true。
3. **同一个指针传两次**（`tryInitializeGfxImage`）不是笔误，是"load-def 到达时在 image+0"的直接表达。
4. **"返回 1 的函数被当作指针"是最坏的一类错误**：它让每个调用者的 null 检查失效。
5. **`216 = 0xD8` 在两处独立出现**，交叉验证了 DObj 池步长。
6. **有符号参数作容量检查时，负数必须在转换前拒绝**。

## 八、未闭合点

- `serverDObjGetAdapter` 的完整实现（668 行之后）未读取。
- `EngineBindings.cpp` 剩余约 915 KB 未读取。
