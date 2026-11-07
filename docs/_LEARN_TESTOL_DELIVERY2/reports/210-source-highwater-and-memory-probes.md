# 210 · 水线报告、`invokeSVTrace` 的正确编组、三个内存探测函数

## 一、范围

本报告学习 `EngineBindings.cpp` 3198–3377 行。

## 二、`reportTraceWriteHighWater`：倒序扫描找最高被写字节

```cpp
std::size_t highest{};
for (auto index = padded.size(); index-- > 0;)
{
    if (padded[index] != std::byte{}) { highest = index + 1; break; }
}
static std::size_t reported{};
if (highest <= reported) return;
reported = highest;
```

### 2.1 `index-- > 0` 的倒序

```text
从 size-1 开始，每次先比较再减
循环体里 index 已经是减过的值
```

**这是"从末尾往前找第一个非零"** —— 找到的就是**最高被写字节的索引 +1**。

### 2.2 `highest <= reported` 只报"新高"

```text
static std::size_t reported{};      // 函数级静态，只记最大值
if (highest <= reported) return;    // 不比已报的大就不报
```

**"单调增强"的报告** —— 只在新高时写日志。

### 2.3 日志格式

```text
"native state write sv_trace declared=%u wroteThrough=%u%s%s"
    declared      = sizeof(NativeTraceResult) = 40
    wroteThrough  = highest
    %s            = " *** PAST THE DECLARED END ***"（超标时）
    %s            = " (faulted)"（异常时）
```

**"PAST THE DECLARED END"** —— 一个非常明确的告警。

## 三、`invokeSVTrace`：正确的六 + 二

### 3.1 完整的编组

```asm
mov ecx, endPointer        ; ECX = end
mov edx, boundsPointer     ; EDX = bounds
push flagA8                ; = 0
push flagA7                ; = 0
push mask                  ; contentMask
push passEntity            ; 实体号
push startPointer          ; start
push resultPointer         ; trace_t*
call function
add esp, 18h               ; 六个栈参数
```

### 3.2 与 §209 里那三条反汇编的对照

```text
sub_46EA60(a, b, c, d, e, f)
    -> ecx = c, edx = d, push a, b, e, f, 0, 0; add esp, 18h
```

**完全一致**：

```text
栈：a=result / b=start / e=passEntity / f=contentMask / 0 / 0
ECX：c=end
EDX：d=bounds
```

**所以正确顺序是 `SV_Trace(results, start, end, bounds, passEntityNum, contentMask, 0, 0)`**。

### 3.3 A5 是实体号不是指针

```cpp
// A5 IS AN ENTITY NUMBER, NOT A POINTER. The engine builds its own
// {passEntity, -1, 1} triple from it; the 12-byte params struct this call
// used to hand over in ECX is 3.3.3.3's shape and has no slot here, so the
// owner-entity half of the filter is simply not expressible through this
// entry point.
const auto passEntity = ignore.baseEntity;
```

**三点**：

1. **A5 是实体号**；
2. **引擎自己从它构建 `{passEntity, -1, 1}` 三元组**；
3. **owner-entity 那一半过滤在这个入口点无法表达**。

**`{passEntity, -1, 1}`** —— 这正好是 §209 里 `NativeIgnoreEntParams` 的 `baseEntity/parentEntity/ignoreSelf` 三者的默认值（parent = -1，ignoreSelf = 1）。

**所以那个 12 字节结构是 3.3.3.3 的形状，这个 build 有个更简单的内建三元组**。

### 3.4 那段关于 `trace_t` 是否变大的推理

```text
IS trace_t BIGGER THAN 0x28 ON THIS BUILD? NativeTraceResult is byte-identical
to the 3.3.3.3 tree, on a build where entityState grew 0x110 -> 0x118 and
playerState 0x3564 -> 0x3BBC. If it grew, the engine writes past what we model
and reads back fields we never initialise -- which is what a groundEntityNum
flipping 2046/2047 on consecutive slices at an unchanged origin looks like,
because a deterministic trace cannot otherwise give two answers.
```

### 3.5 那个具体的症状

```text
groundEntityNum 在【原点不变】的连续切片上于 2046/2047 之间翻转
    —— 因为一个确定性的 trace 不可能给出两个答案
```

**"确定性 trace 不可能给两个答案"** —— 这是**用不变性反推"读到了未初始化内存"**的经典推理。

### 3.6 测量手法与 §43f 相同

```text
传结构 + 一个清零的尾巴，报告最高被改字节。
用【零】而不是填充模式，这样读到末尾之外会看到 null 或 0.0f；
余量吸收越界，这正是使测量可存活的原因。
```

**"零而非填充"** 与 **"余量吸收越界"** 是两条具体设计：

- 零 = 越界读出的是安全的空值；
- 512 字节余量 = 即使越界也不会崩。

### 3.7 结果拷贝

```cpp
std::memcpy(&result, padded.data(), sizeof(result));   // 只拷 40 字节
reportTraceWriteHighWater(padded, completed);
```

**只把前 `sizeof(result)` 拷进结果**，而**整个 552 字节的 padded 交给水线报告**。

## 四、`traceDifferenceName`：13 项映射

```text
None / Fraction / Normal / SurfaceFlags / Contents / HitType / HitId
ModelIndex / PartName / PartGroup / AllSolid / StartSolid / Walkable
```

**正好对应 `SvTraceComparisonDifference` 的 13 个枚举值** ✓

`SurfaceFlags` → `"surface_flags"`（下划线风格）—— 而枚举名是驼峰。**日志里用 snake_case，代码里用 CamelCase**。

## 五、三个内存探测函数的分工

### 5.1 `readableBytes(address)` —— 返回**可用字节数**

```cpp
if (!address || !VirtualQuery(...) || State != MEM_COMMIT ||
    (Protect & (PAGE_GUARD | PAGE_NOACCESS)))
    return nullopt;
cursor = (uintptr_t)address;
end    = (uintptr_t)BaseAddress + RegionSize;
if (cursor >= end) return nullopt;
return end - cursor;
```

**返回的是"从 address 到区域末尾还有多少字节"** —— 而不是布尔。

### 5.2 `writableBytes(address, size)` —— 逐区域推进

```cpp
cursor = address;
while (cursor < end)
{
    VirtualQuery(cursor, ...);
    检查 State / GUARD / NOACCESS;
    protection = Protect & 0xFF;
    if (protection not in {READWRITE, WRITECOPY, EXECUTE_READWRITE, EXECUTE_WRITECOPY})
        return false;
    regionEnd = BaseAddress + RegionSize;
    cursor = min(regionEnd, end);
}
return true;
```

**四个关键细节**：

1. **`memory.Protect & 0xFF`** —— 掩掉 `PAGE_NOCACHE`/`PAGE_WRITECOMBINE` 等高字节标志，只留基本保护；
2. **四种可写保护显式列举** —— 而 `readableSpan` 用的是"可读位集合"；
3. **`regionEnd <= cursor` 检查** —— 防止无限循环（如果某个区域大小为 0）；
4. **`cursor = min(regionEnd, end)`** —— 跳到下一个区域或终点。

### 5.3 溢出检查

```cpp
if (size > max_uintptr - cursor) return false;
```

**在 `cursor + size` 之前检查溢出** —— 与 §179 里"索引累加用减法比较"同一条纪律。

### 5.4 `readableSpan(address, length)` —— 布尔

```cpp
if (!address) return false;
if (!length) return true;      // 【零长度永远可读】
auto cursor = (uintptr_t)address;
...
```

**`!length` 返回 true** —— 与 `writableBytes` 里 `!size` 返回 **false** **相反**。

**这是一处不一致**：

```text
readableSpan(addr, 0)  == true
writableBytes(addr, 0) == false
```

**语义上"零长度可读"是对的**（空操作永远成功），而 `writableBytes` 返回 false 可能是因为它把"零长度"当作"无效请求"。

## 六、三个探测函数的用途分工

| 函数 | 返回 | 用途 |
|---|---|---|
| `witnessCanRead` | bool | VEH 内部（§193） |
| `readableSpan` | bool | 通用读检查 |
| `readableBytes` | `optional<size_t>` | 需要知道"还能读多少" |
| `writableBytes` | bool | 写补丁前检查 |

**四个函数做同一件事的不同变体** —— 这是可以指出的重复，但每个变体返回的信息量不同。

## 七、关键结论

1. **"确定性 trace 不可能给两个答案"** ⇒ 翻转就是读到了未初始化内存。
2. **"零而非填充" + "512 字节余量"** 是使越界测量可存活的两条设计。
3. **A5 是实体号，引擎自己构建 `{passEntity, -1, 1}` 三元组** ⇒ owner-entity 过滤在此入口不可表达。
4. **`Protect & 0xFF`** 掩掉高字节标志，只留基本保护。
5. **`regionEnd <= cursor` 检查防止无限循环**。
6. **`readableSpan` 的零长度返回 true 而 `writableBytes` 返回 false** —— 一处语义不一致。

## 八、未闭合点

- `trace_t` 是否真的比 0x28 大 —— 水线报告正是为了回答它，结果不在本组。
- `EngineBindings.cpp` 3377 行之后未读取。
