# 208 · NativeTraceResult 的 0x28、StringTable、两处不同位移的回调补丁

## 一、范围

本报告学习 `EngineBindings.cpp` 2840–3019 行。

## 二、`StringTable` 的两个尺寸

```cpp
struct StringTableCell {
    const char *value;
    std::uint32_t hash;
};
struct StringTable {
    const char *name;
    std::int32_t columnCount;
    std::int32_t rowCount;
    const StringTableCell *values;
};
static_assert(sizeof(StringTableCell) == 8);
static_assert(sizeof(StringTable) == 16);
```

**`StringTableCell` = 8 字节**（4 + 4）—— 与 §143 里 `SV_StringTableHash` 的"cells cache this lowercase polynomial hash beside their text pointer"完全对应。

**`StringTable` = 16 字节**（4 + 4 + 4 + 4）—— 四个字段。

## 三、`NativeTraceResult`：`0x28 = 40` 字节

### 3.1 字段与偏移

```text
+0x00  float fraction
+0x04  array<float,3> normal          （12 字节，到 +0x10）
+0x10  uint32 surfaceFlags
+0x14  uint32 contents
+0x18  uint32 hitType
+0x1C  uint16 hitId
+0x1E  uint16 modelIndex
+0x20  uint16 partName
+0x22  uint16 partGroup
+0x24  uint8 allSolid
+0x25  uint8 startSolid
+0x26  uint8 walkable
+0x27  uint8 unknownEnd
```

**总 40 = 0x28** ✓

### 3.2 七条断言

```cpp
static_assert(sizeof(NativeTraceResult) == 0x28);
static_assert(sizeof(TraceBounds) == 0x18);
static_assert(offsetof(NativeTraceResult, hitType)    == 0x18);
static_assert(offsetof(NativeTraceResult, hitId)      == 0x1C);
static_assert(offsetof(NativeTraceResult, modelIndex) == 0x1E);
static_assert(offsetof(NativeTraceResult, partName)   == 0x20);
static_assert(offsetof(NativeTraceResult, partGroup)  == 0x22);
static_assert(offsetof(NativeTraceResult, allSolid)   == 0x24);
```

**`TraceBounds == 0x18`** = 24 = 两个 12 字节的向量 ✓

### 3.3 与 `NativeDObjTraceResult` 的差别

| | `NativeDObjTraceResult` | `NativeTraceResult` |
|---|---|---|
| 大小 | 0x1C (28) | 0x28 (40) |
| normal 偏移 | 0x08 | 0x04 |
| 有 contents | ✗ | ✓ (+0x14) |
| 有 hitType/hitId | ✗ | ✓ |
| 有 allSolid/startSolid/walkable | ✗ | ✓ (+0x24..0x26) |

**`NativeDObjTraceResult` 在 `+0x04` 直接是 surfaceFlags，而 `NativeTraceResult` 在 `+0x04` 是 normal** —— **两个结构的前半段布局不同**。

**这是两个不同的原生类型**，不能互相替换。

### 3.4 `unknownEnd`

**`+0x27` 一个字节显式命名为 `unknownEnd`** —— 而不是 `padding`。

**"unknown" 而不是 "padding"** —— 说明这 40 字节里最后一个字节**还不知道是什么**，但必须占据空间。

## 四、`invokePointTraceStaticModels`：四寄存器

```asm
push edi
mov edi, output         ; EDI = NativeTraceResult*
mov edx, contentMask    ; EDX = 掩码
mov ecx, endPointer     ; ECX = 终点
push startPointer       ; 栈 = 起点
mov eax, function
call eax
add esp, 4
pop edi
```

### 4.1 四个入口

```text
EDI = output
EDX = contentMask
ECX = end
栈  = start
```

**与 §`EngineBindings.hpp` 里那条注释完全一致**：

> `PointTraceStaticModelsRva`：`EDX mask, ECX end, EDI trace, stack start`。

### 4.2 `push edi`/`pop edi`

**因为 EDI 是输出参数且是被调用者保存寄存器** —— 与前面几个同族。

### 4.3 与 `invokeDObjTraceline` 的对照

```text
invokeDObjTraceline:        ECX = result, EDX = end,   栈 = priorityMap/start/dobj
invokePointTraceStaticModels: ECX = end,  EDX = mask, EDI = output, 栈 = start
```

**ECX 与 EDI 的角色互换了** —— 同族函数但寄存器分配不同。

## 五、玻璃回调桥：**两处不同位移**

### 5.1 为什么必须两处

```text
两处站点都把引擎自己的玻璃回调存进一个栈局部 ——
`mov [ebp-disp], offset callback` —— 而 mod 把它们重定向到 SV_Glass_IsPieceSolid。
```

### 5.2 识别方式

```text
在 1649370 上【用回调的地址】而不是用位置识别它：
    每个 build 正好包含【两处】这样的存储，
    拥有它们的函数相对应（第二个是 TransformedBrushModelTrace，本文件已经绑定），
    而回调体在两个 build 上逐字节相同 —— `32 C0 C3`，xor al,al / ret。
```

**`32 C0 C3` = `xor al,al; ret`** —— 一个**永远返回 false** 的桩。

**"用回调地址识别站点"** 比"用位置"可靠得多 —— 因为位置会随栈帧漂移。

### 5.3 那次位移不同导致的失败

```text
THE DISPLACEMENT IS PER SITE ON THIS BUILD and that is why the guard had to
change shape. 3.3.3.3 uses -0x4C at both sites, so one shared 3-byte prefix
covered them. out.exe uses -0x4C at 0x268302 and -0x48 at 0x2684CB,
because the two functions' stack frames drifted independently.
A single prefix silently fails the second site, which is exactly how this
presented: bind() reaching stage=glass_bridge and refusing.
```

**"两个函数的栈帧独立漂移了"** —— 所以一个共享前缀会**静默地在第二处失败**。

**症状**：`bind()` 到达 `stage=glass_bridge` 并拒绝。

### 5.4 指令格式

```asm
C7 45 <disp8> <imm32>       mov dword ptr [ebp+disp8], imm32
```

```cpp
constexpr std::array<std::uint8_t, 3> expected{
    0xC7, 0x45, CallbackInstructions[index].displacement,
};
constexpr std::size_t CallbackOperandOffset = 3;
```

**`C7 45` + 1 字节位移 = 3 字节前缀，操作数在 +3**。

### 5.5 两个位移的编码

```text
CallbackInstruction{ 0x268302, 0xB4 }   // -0x4C
CallbackInstruction{ 0x2684CB, 0xB8 }   // -0x48
```

**位移用无符号字节 `0xB4` / `0xB8` 存储** —— 而在 x86 的 `[ebp+disp8]` 里它们是**有符号的 -0x4C / -0x48**。

**注释把两种表示都写出来了** —— 这是必要的，因为字节比较要用 `0xB4`，而语义理解要用 `-0x4C`。

### 5.6 幂等的双重接受

```cpp
if (previousOperands[index] != (uint32)original &&
    previousOperands[index] != (uint32)replacement)
    return false;
```

**既接受原值也接受已打过的补丁** —— 所以重复安装是幂等的。

### 5.7 一次性覆盖两个站点

```cpp
first = module + CallbackInstructions.front().rva + CallbackOperandOffset;
last  = module + CallbackInstructions.back().rva + CallbackOperandOffset + 4;
patchLength = last - first;
VirtualProtect(first, patchLength, ...);
```

**从第一个操作数到第二个操作数末尾一次 `VirtualProtect`** —— 覆盖两处。

**所以是"一次保护、两处写"** —— 而验证是逐站点单独做的。

## 六、`thread_local const SvGlassState* activeGlassState`

```cpp
thread_local const SvGlassState *activeGlassState{};

bool __cdecl SV_Glass_IsPieceSolid(const std::int32_t pieceIndex)
{
    return pieceIndex >= 0 && activeGlassState &&
        activeGlassState->isPieceSolid((uint32)pieceIndex);
}
```

### 6.1 为什么 `thread_local`

**因为引擎可能在多个线程上调这个回调**，而每个线程需要看到自己当前的 `SvGlassState`。

### 6.2 三重检查

```text
pieceIndex >= 0     （负数在原生侧是合法的"无片"）
&& activeGlassState  （未设置时返回 false）
&& isPieceSolid(...)
```

**`pieceIndex >= 0` 检查在前** —— 因为 `isPieceSolid` 接受 `uint32`，负数转换会变成巨大值。

## 七、`NativeBrushModel`：72 字节

```cpp
struct NativeBrushModel {
    TraceBounds bounds;                    // 24
    array<byte, 12> unknown0018;           // 12   （+0x18）
    uint32 leafBrushContents;              //  4   （+0x24）
    uint32 leafTerrainContents;            //  4   （+0x28）
    array<byte, 28> unknown002C;           // 28   （+0x2C）
};
static_assert(sizeof(NativeBrushModel) == 72);
static_assert(offsetof(..., leafBrushContents)   == 0x24);
static_assert(offsetof(..., leafTerrainContents) == 0x28);
```

**验算**：24 + 12 + 4 + 4 + 28 = **72** ✓

**两个具名字段被 12 与 28 字节的 `unknown` 包围** —— 只建模已知部分，不假装知道其余。

## 八、关键结论

1. **两个 trace 结构的前半段布局完全不同**，不能互相替换。
2. **`unknownEnd` 而不是 `padding`** —— 说明最后一个字节含义未知但必须占位。
3. **用回调地址识别站点比用位置可靠** —— 位置会随栈帧漂移。
4. **两个站点的位移可以不同**（`-0x4C` vs `-0x48`），一个共享前缀会静默失败第二个。
5. **字节比较用 `0xB4`，语义理解用 `-0x4C`** —— 两种表示都要写出来。
6. **`thread_local` 是回调在多线程被调用时的必需**。
7. **`NativeBrushModel` 只建模两个已知字段**，其余是 `unknown`。

## 九、未闭合点

- `NativeTraceResult::unknownEnd`（+0x27）的含义未知。
- `NativeBrushModel` 的 `unknown0018`（12）与 `unknown002C`（28）未建模。
- `EngineBindings.cpp` 3019 行之后未读取。
