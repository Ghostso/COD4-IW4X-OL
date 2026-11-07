# 205 · DObjTrace 布局、四个 trace 适配器、XAnimTree 清零的有界循环

## 一、范围

本报告学习 `EngineBindings.cpp` 2303–2482 行。

## 二、`NativeDObjTraceResult` 的六条断言

```cpp
static_assert(sizeof(NativeDObjTraceResult) == 0x1C);
static_assert(offsetof(NativeDObjTraceResult, surfaceFlags) == 0x04);
static_assert(offsetof(NativeDObjTraceResult, normal)       == 0x08);
static_assert(offsetof(NativeDObjTraceResult, modelIndex)   == 0x14);
static_assert(offsetof(NativeDObjTraceResult, partName)     == 0x16);
static_assert(offsetof(NativeDObjTraceResult, partGroup)    == 0x18);
```

**`0x1C = 28`** —— 与 §204 我推算的一致（4+4+12+2+2+2+2）。

`fraction` 的偏移没有断言，因为它就在 `+0`（结构首成员）。

## 三、`invokeAngleVectors`：五条自身的更正记录

### 3.1 三个目的地

```cpp
push upPointer       // axis + 6
push rightPointer    // axis + 3
push forwardPointer  // axis + 0
push anglesPointer
add esp, 10h         // 四个栈参数
```

**Quake 的 `AnglesToAxis` = `AngleVectors` + 第二行取反**：

```cpp
for (std::size_t component{3}; component != 6; ++component)
    axis[component] = -axis[component];
```

**"所以调用者取反"** —— 取反在**调用者侧**，不是适配器内部（虽然两者都在这里）。

### 3.2 被替换那个绑定的完整错误

```text
`anglesToQuaternion_` 是 sub_7853E0，它通过 ESI 读角度、通过 EDX 写【四个】float，
而 NativeWeaponMovementBindings 的包装把它们【反着】传 ——
所以它把一个矩阵当角度读，并在调用者的角度向量上盖了一个四元数。
```

### 3.3 那个抓住它的证据

```text
实体镜像抓住它的方式是：`check=source entity=0 offset=353`，
而 353 是 0x161，在 currentAngles[1] 里面。
```

**`0x161 = 0x160 + 1`** —— 而 §183 里 `ViewAnglesOffset = 0x160`。所以写入落在 `viewAngles[1]` 的第二个字节上。

**"偏移 353" 是逐字节报告** —— 1 字节的分辨率让一个 12 字节的越界写入立刻可见。

## 四、`invokeDObjTraceline`：ECX + EDX + 三个栈

### 4.1 调用约定

```text
ECX = result（NativeDObjTraceResult*）
EDX = end 端点
栈  = priorityMap / start / dobj      （压栈顺序逆序）
add esp, 0Ch                          （三个栈参数）
```

### 4.2 证据

```text
取自 0x0046E26D..0x0046E285，
那里的清理与 DObjCalcSkel 包装的两个参数【共用】——
`add esp, 14h` 对 2 + 3 个 dword
```

**`0x14 = 20 = 5 dword`** —— 而 2（CalcSkel）+ 3（Traceline）= 5 ✓

**"共用的清理"** 意味着**两个调用点相邻，共用一条 `add esp`** —— 这是从一条指令反推两个函数的参数个数。

### 4.3 压栈顺序与参数顺序

```text
push priorityMap   （第三个栈参）
push startPointer  （第二个）
push dobj          （第一个）
```

所以 `[esp+0] = dobj` ✓

## 五、`invokeDObjContentsTraceline`：**五个纯栈参数**

```cpp
using Function = void(__cdecl*)(void*, const float*, const float*,
                                std::uint32_t, NativeDObjTraceResult*);
reinterpret_cast<Function>(function)(dobj, start.data(), end.data(),
                                     contentMask, &result);
```

**这是本组唯一一个"直接用 typedef 而不写汇编"的** —— 因为它是**纯 cdecl**。

注释：

> **contents 几何用五个调用者清理的栈参数，与玩家追踪器不同。**

**与上一个（`invokeDObjTraceline`）形成对照**：同一个 `NativeDObjTraceResult`，一个用寄存器传（ECX/EDX），一个全栈。

### 5.1 `contentMask` 为零时拒绝

```cpp
if (!function || !dobj || !contentMask) return false;
```

**零掩码意味着"什么都不追踪"** —— 所以拒绝而不是调用。

## 六、`invokeDObjCalcSkel`：ECX + 一个栈

```asm
push dobj
mov ecx, requestedParts   // partBits 数组
mov eax, function
call eax
add esp, 4
```

**`requestedParts` 在 ECX、`dobj` 在栈** —— 两个参数顺序与常规相反。

`partBits` 是 `array<uint32_t, 8>` = **32 字节**，与 §204 一致。

## 七、`clearNativeXAnimTree`：有界循环而不是一次调用

### 7.1 BO1 只调一次并断言

```cpp
// BO1 XAnimClearTree issues ONE call and asserts the field is
// then zero, because XAnimFreeInfo drains the whole sibling chain.
```

### 7.2 但这里循环

```cpp
for (std::size_t guard{}; *children && guard < 64; ++guard)
{
    freeInfo(tree?, children);   // 后续行未读
}
```

注释：

> **还是循环，有界**，**这样一次部分排空不会留下附着节点 —— 也因此这永远不可能自旋。**

**三条理由**：

1. BO1 是"一次 + 断言"，而**本项目不能断言**（会崩）；
2. 部分排空会留下附着节点 ⇒ 循环能补救；
3. `guard < 64` ⇒ **永远不可能自旋**。

**"不可能自旋"是通过硬界保证的**，不是通过逻辑保证的。

### 7.3 偏移

```cpp
auto* children = (uint16_t*)((std::byte*)tree + 4);
```

**`tree + 4` 是 children 字段** —— 与 §154 里"树头 `{anims, children}`"一致：

```text
+0  anims
+4  children
```

§184 里也提到 `XAnimFreeInfo` 最后 `mov word [edx+4], ax` —— **把 children 字段归零**。

## 八、本组新增的四个 ABI

| 适配器 | 参数位置 | 直接 typedef |
|---|---|---|
| `invokeAngleVectors` | 栈 4 | ✗ |
| `invokeDObjTraceline` | **ECX + EDX + 栈 3** | ✗ |
| `invokeDObjContentsTraceline` | 栈 5 | **✓** |
| `invokeDObjCalcSkel` | **ECX + 栈 1** | ✗ |

**`invokeDObjContentsTraceline` 是第一个纯栈的** —— 所以能直接用 typedef，不需要汇编。

## 九、关键结论

1. **`0x161` 落进 `viewAngles[1]`** —— 逐字节的偏移报告让 12 字节越界立刻可见。
2. **一条共用的 `add esp, 14h` 反推出两个函数的参数个数**（2 + 3 = 5 dword）。
3. **同一个结果结构，两个 trace 变体一个用寄存器传一个全栈**。
4. **`contentMask == 0` 要拒绝**，因为零掩码意味着"什么都不追踪"。
5. **有界循环是"不可能自旋"的保证**，而不是逻辑上不可能。
6. **纯 cdecl 的调用可以直接 typedef，不必写汇编** —— 但这个是少数。

## 十、未闭合点

- `clearNativeXAnimTree` 循环体（2482 行之后）未读取。
- `EngineBindings.cpp` 2482 行之后未读取。
