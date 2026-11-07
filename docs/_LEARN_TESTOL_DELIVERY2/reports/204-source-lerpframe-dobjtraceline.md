# 204 · lerp 帧访问器的双手装、两个 part-bits 变体、DObj trace 结果布局

## 一、范围

本报告学习 `EngineBindings.cpp` 2124–2303 行。

## 二、`invokeBGPlayerAnimation` 的实现

```asm
push edi
mov edi, characterInfo
push 0            ; a4 = 0（游戏传的）
push entityState  ; a3
push -1           ; a2 = -1（哨兵）
mov eax, function
call eax
add esp, 0Ch      ; 三个栈参数
pop edi
```

**`push edi` / `pop edi`** 包住整个调用 —— 因为 **EDI 在这里既是参数又需要保存**（与 §194 里 `invokeConfigStringGet` 的 ESI 同样的问题）。

**`add esp, 0Ch` 在 `pop edi` 之前** ✓ —— 栈平衡顺序正确。

## 三、`invokeNativeLerpFrameAccessorInitialize`：**一次调用干两件事**

这是本组最复杂的一个适配器。

### 3.1 前置

```cpp
if (!function || !frame || !zeroVector ||
    selector >= SvNativeLerpFrameSelectorCount(33))
    return false;
```

三个指针 + 一个范围（`selector < 33`）。

### 3.2 三个偏移

```cpp
encodedSet     = frame + SvNativeLerpFrameSetAccessorOffset      // +0x1C
encodedGet     = frame + SvNativeLerpFrameGetAccessorOffset      // +0x20
protectedValue = frame + SvNativeLerpFrameProtectedValueOffset   // +0x24
```

**与 §154 的 `sub_408A70` 分析完全一致**：

```text
SET 存在 +0x1C，以 +0x20 的地址为键
GET 存在 +0x20，以 +0x1C 的地址为键
保护值在 +0x24
```

### 3.3 第一段：调初始化器

```asm
push edi
mov edi, encodedGet          ; EDI = GET 槽地址
push setKey
push encodedSet              ; 栈参 3
push encodedGet              ; 栈参 2
push selector                ; 栈参 1
mov eax, encodedSet          ; EAX = SET 槽地址
mov edx, getKey              ; EDX = get key
mov ecx, function            ; ECX = 函数
call ecx
add esp, 16                  ; 四个栈参数
```

**六个入口**：

```text
ECX  函数地址
EAX  encodedSet（+0x1C）
EDX  getKey
EDI  encodedGet（+0x20）
栈   selector / encodedGet / encodedSet / setKey
```

**注意 `encodedSet` 与 `encodedGet` 各出现两次**（一个在寄存器、一个在栈）—— 这对应 §154 里"交叉键控"：

```text
SET 指针存在 +0x1C，以 +0x20 的地址为键
```

所以初始化器需要**两个槽地址**（用于交叉），而 `getKey` 在 EDX、`setKey` 在栈。

### 3.4 第二段：立刻用刚装好的访问器

```asm
mov ecx, encodedSet
mov ecx, dword ptr [ecx]     ; ecx = 已编码的 SET 指针
xor ecx, setKey              ; 解 SET 键
mov eax, encodedGet
xor ecx, eax                 ; 再 XOR GET 槽【地址】
push protectedValue
push zeroVector
call ecx                     ; 调用解码出来的函数
add esp, 8
```

### 3.5 这段内联的算法

```text
f = *(uint32*)(frame + 0x1C) ^ setKey ^ (frame + 0x20)
```

**这正是 `SV_DecodeNativeLerpFrameAccessors` 做的事**，而这里**在汇编里重做了一遍**。

而 §154 里 `sub_408A70` 的三条指令是：

```text
408deb  (dword_E60B3C ^ *(frame+28) ^ (frame+32))(source, frame+36)     ; SET
408b9a  (dword_E60B40 ^ (frame+28) ^ *(frame+32))(frame+36, dest)       ; GET
```

**对照**：`dword_E60B3C` = `setKey`、`dword_E60B40` = `getKey`。

而这里的第二段做的是：

```text
ecx = *(frame+0x1C) ^ setKey ^ (frame+0x20)
```

即 `(encodedSet_content ^ setKey) ^ encodedGet_ADDRESS` —— **这是 SET 的解码形式**（`dword_E60B3C ^ *(frame+28) ^ (frame+32)`，其中 `(frame+32)` 是**地址**）。

**完全一致** ✓

### 3.6 为什么初始化后立刻调用

因为它要把**保护值写到 `+0x24` 并清零**：

```asm
push protectedValue   ; frame + 0x24
push zeroVector
call ecx
```

**两个栈参数**：目标地址与零向量。

**所以这个适配器的名字（Initialize）掩盖了它实际做两件事**：装访问器 + 用它写初值。

## 四、`invokeDObjGeomTracelinePartBits`：ESI 输出 + 一个栈参数

```asm
push esi
mov esi, output        ; ESI = 32 字节输出
push dobj
mov eax, function
call eax
add esp, 4
pop esi
```

**ESI 是输出数组指针**，`dobj` 走栈。

**`partBits` 是 `std::array<uint32_t, 8>` = 32 字节** —— 与 §190 里 `partBits` 的类型一致。

## 五、`invokeDObjContentsTracelinePartBits`：**多一个 content mask**

```asm
push esi
mov esi, output
push contentMask
push dobj
mov eax, function
call eax
add esp, 8
pop esi
```

**两个栈参数**。

### 5.1 为什么两个变体不同

注释解释了 `SV_PointTraceToEntity` 的选择：

```text
SV_PointTraceToEntity 在实体的 svFlags（gentity +0x112）上二选一：
    bit 2 清零 ⇒ locational 那对（sub_CE69A0 + DObjTraceline 0x00645DD0），
                 递给它 pointtrace 的 priority map（+0x54）
    bit 2 置位 ⇒ 这一个 + 0x00646A70，
                 递给它 content mask（+0x4C）
```

> **因此它需要那第二个参数；locational 变体不需要。**

**"所以它需要那个参数，另一个不需要"** —— 两种变体的参数差异**由调用者的选择依据决定**。

### 5.2 与 §187 里遗留 TODO 的呼应

§187 里：

> `ServerDObjMap` 的两个字是否对活玩家都已填充是 `TODO(CODOL)`，仅诊断。

而这里给出了**选择依据的完整机制**。

## 六、`NativeDObjTraceResult`：DObjTraceline 写什么

### 6.1 唯一调用者 + 序言

```text
Read off the ONE caller 1649370 still has (0x0046E280) plus the function's
own prologue, which zeroes +4, +8..+0x10 and the three words at +0x14
```

### 6.2 六个字段

```text
+0x00  fraction      【调用者预置】为当前最优
                       0x0046E1FC 在调用前从 trace_t 载入，
                       所以这是一个【取最大】而不是只写字段
+0x04  surfaceFlags       → trace_t +0x10
+0x08  normal[3]  【模型空间】  → 在 3.3.3.3 的 0x005FB7DC 转回来后才进 trace_t +4
+0x14  modelIndex         → trace_t +0x1E
+0x16  partName           → trace_t +0x20
+0x18  partGroup          → trace_t +0x22
```

### 6.3 `fraction` 是**输入兼输出**

这是最不寻常的一点：

> **`fraction` 由调用者用当前最优值【预置】** —— `0x0046E1FC` 在调用前从 `trace_t` 载入它，**所以这是一个取最大，而不是只写的字段**。

即：`DObjTraceline` 内部会**只在找到更近的命中时**才更新 `fraction`。**所以调用前必须把当前最优传进去**。

**这是一个很容易搞错的契约** —— 如果每次传 0，那么任何命中都"更近"，结果会变成"任意命中"而非"最近命中"。

### 6.4 `normal` 在**模型空间**

> **`normal[3]` 在模型空间 → 在 3.3.3.3 的 `0x005FB7DC` 转回来后才进 `trace_t +4`**

**所以调用方必须做空间变换** —— 与 §189 里"骨骼在模型空间摆姿，所以射线要用实体的 origin 与 angles 带进模型空间"是同一件事的两端。

### 6.5 结构尺寸

```cpp
struct NativeDObjTraceResult {
    float fraction;              // +0x00
    std::uint32_t surfaceFlags;  // +0x04
    std::array<float,3> normal;  // +0x08..0x13
    std::uint16_t modelIndex;    // +0x14
    std::uint16_t partName;      // +0x16
    std::uint16_t partGroup;     // +0x18
    std::uint16_t pad001A;       // +0x1A
};
```

**总 28 字节**（4 + 4 + 12 + 2 + 2 + 2 + 2）。

`pad001A` 是显式的两字节填充 —— 因为自然对齐会让它成为 32？不，4+4+12+2+2+2+2 = 28，而结构对齐是 4，所以 28 已经是 4 的倍数 ✓。

**`pad001A` 说明序言"清零 +0x14 处的三个字"** —— 即 `+0x14/+0x16/+0x18/+0x1A` 共四个 u16，而只有前三个有语义。

## 七、关键结论

1. **`push edi`/`pop edi` 包住调用**，因为 EDI 既是参数又需保存。
2. **`invokeNativeLerpFrameAccessorInitialize` 实际做两件事**：装访问器 + 用刚装的访问器写保护值。
3. **第二段的汇编与 `sub_408A70` 的解码逐项对应**（`(*(+0x1C) ^ setKey) ^ (frame+0x20)`）。
4. **`fraction` 是输入兼输出** —— 调用前必须传当前最优，否则"最近命中"退化成"任意命中"。
5. **`normal` 在模型空间**，调用方负责转回。
6. **两个 part-bits 变体的参数差异由 `svFlags` bit 2 决定**。

## 八、未闭合点

- `NativeDObjTraceResult` 的转换与 `trace_t` 的完整映射（3.3.3.3 的 `0x005FB7DC` 在本 build 的对应物）未在本组。
- `EngineBindings.cpp` 2303 行之后未读取。
