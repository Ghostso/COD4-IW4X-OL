# 264 · **第三个 trace 的 ABI**、把 12 字节 vec3 当 40 字节结果缓冲、六项差异位掩码

## 一、范围

本报告学习 `EngineBindings.cpp` 17450–17650 行。

## 二、`traceTransformedBrushModel` 的**六项前置**

```cpp
if (!transformedBrushModelTrace_ ||
    entity.shape != SvCollisionShape::BrushModel ||
    !entity.brushModelClipHandle ||
    !validTraceInput(start, end, bounds, entity.contents) ||
    !SV_IsCollisionEntityValid(entity))
{
    return nullopt;
}
```

### 2.1 五项

```text
函数已绑定
entity.shape == BrushModel        ← 【形状必须是 brush model】
brushModelClipHandle 非空
四个输入有效
实体有效
```

### 2.2 与 `traceTransformedCapsule` 的差异

**§263 的胶囊版**没有 `shape` 与 `clipHandle` 的检查**。

**⇒ 因为胶囊只需要 `entity.bounds`，而 brush model 需要 `clipHandle`。**

## 三、**第三个 trace 的 ABI**（本组最重要的一段）

### 3.1 完整的对照表

```php
// CODREF(sv_trace): 1649370's convention is NOT 3.3.3.3's. Section 74.
//
//                    3.3.3.3 0x0058B230      1649370 0x00668470
//   [ebp+08] arg1    start                   result
//   [ebp+0C] arg2    end                     end
//   [ebp+10] arg3    bounds                  bounds
//   [ebp+14] arg4    clipHandle              clipHandle
//   [ebp+18] arg5    contents                contents
//   [ebp+1C] arg6    targetOrigin            targetAngles
//   ECX              targetAngles            targetOrigin
//   EDX              result                  start
```

### 3.2 **八行里只有三行相同**

| 通道 | 3.3.3.3 | 1649370 | 相同？ |
|---|---|---|---|
| `[ebp+08]` | `start` | `result` | ✗ **互换** |
| `[ebp+0C]` | `end` | `end` | ✓ |
| `[ebp+10]` | `bounds` | `bounds` | ✓ |
| `[ebp+14]` | `clipHandle` | `clipHandle` | ✓ |
| `[ebp+18]` | `contents` | `contents` | ✓ |
| `[ebp+1C]` | `targetOrigin` | `targetAngles` | ✗ **互换** |
| `ECX` | `targetAngles` | `targetOrigin` | ✗ **互换** |
| `EDX` | `result` | `start` | ✗ **互换** |

**⇒ 五个不变、三个成对互换**（`start↔result`、`targetOrigin↔targetAngles`）。

### 3.3 而**最致命的是 `start ↔ result`**

```php
// CARRYING 3.3.3.3's FORM HANDED THE CALLEE A
// 12-BYTE vec3 AS ITS 40-BYTE RESULT BUFFER.
```

### 3.4 完整后果

**照 3.3.3.3 的写法：**

```text
[ebp+08] 传入 start（12 字节 vec3）  ← 而 1649370 当作 40 字节 result 缓冲写入
EDX      传入 result（40 字节缓冲）  ← 而 1649370 当作 start 读三个浮点
```

**⇒ 函数会往一个 12 字节的 `start` 数组里写 40 字节的 trace 结果。**

**⇒ 覆盖栈上的 28 字节（`start` 之后的相邻局部变量）。**

**"CARRYING 3.3.3.3's FORM HANDED THE CALLEE A 12-BYTE vec3 AS ITS 40-BYTE RESULT BUFFER"**

**⇒ 这是一个**栈溢出写**。**

### 3.5 **40 字节的 `TraceResult` / `NativeTraceResult`**

```text
0x28 = 40 字节
```

**⇒ 所以 `NativeTraceResult` 是 40 字节。**

**而 `start` 是 `std::array<float,3>` = 12 字节。**

**⇒ `40 - 12 = 28` 字节的越界写。**

### 3.6 而 `targetOrigin ↔ targetAngles` 是**同样大小但语义错**

```text
3.3.3.3:  ECX = targetAngles,  [ebp+1C] = targetOrigin
1649370:  ECX = targetOrigin,  [ebp+1C] = targetAngles
```

**⇒ 两个都是 `std::array<float,3>` ⇒ **大小相同** ⇒ 不会崩溃，只会算错。**

**⇒ 所以这是一个**静默的**错误（trace 结果不对但不崩）。**

### 3.7 四种证据（"被调方自己命名了 arg1 与角度"）

```php
// The callee names arg1 and the angles by itself: 0x0058B230 does
// `fld [ecx]` / `fld [ecx+4]` on the angles and `fld [ebx]` .. `[ebx+8]`
// on [ebp+8], where 0x00668470 does the zero test on [ebp+1C] through
// EDI and reads the three start floats through EDX. Both call sites on
// each build agree (0x005FB4A7, 0x00458D7B there; 0x0046DC2F,
// 0x0046E3A1 here).
```

### 3.8 三个被调方证据

```text
3.3.3.3 0x0058B230:
  fld [ecx] / fld [ecx+4]     ⇒ ECX 是【角度】（读浮点）
  fld [ebx] .. [ebx+8]        ⇒ [ebp+8] 经 EBX 是【三个浮点】= start

1649370 0x00668470:
  通过 EDI 对 [ebp+1C] 做零测试    ⇒ [ebp+1C] 是【角度】（零测试 = identity 角度）
  通过 EDX 读三个 start 浮点       ⇒ EDX 是【start】
```

### 3.9 **`fld [ecx] / fld [ecx+4]` 只读了两个浮点**

**⇒ 角度只有两个分量被读（pitch/yaw）而第三个（roll）忽略。**

**⇒ 这解释了为什么 `targetAngles` 是 `array<float,3>` 但只用到两个。**

### 3.10 而"零测试"证明了 `[ebp+1C]` 是角度

**⇒ `0x00668470` 检查角度是否全零（identity）来走快速路径。**

**⇒ 所以 `[ebp+1C]` 在 1649370 是 angles 而在 3.3.3.3 是 origin。**

### 3.11 四个调用点（每 build 两个）

```text
3.3.3.3   0x005FB4A7（server）、0x00458D7B（client）
1649370   0x0046DC2F（box clip）、0x0046E3A1（point clip）
```

**⇒ 与 §263 的 `sv_trace` 调用点（`0x0046DC81`、`0x0046E3F6`）**只差几十字节**。**

**⇒ 所以 box clip 里连续调了两个 trace（胶囊与 brush model）。**

### 3.12 而 §263 的 `sv_trace` 与 §264 的 brush model trace 是两个不同函数

```text
§263  0x0058B330 (3.3.3.3) / 0x00668560 (1649370)   胶囊
§264  0x0058B230 (3.3.3.3) / 0x00668470 (1649370)   brush model
```

**⇒ 两个函数地址相差 `0x100`（`0x0058B330 - 0x0058B230 = 0x100`）。**

**⇒ 所以它们是同一族的两个变体。**

**⇒ 而它们的 1649370 版本相差 `0x00668560 - 0x00668470 = 0xF0`。**

### 3.13 **三个 trace 的三种 ABI**

```text
worldTrace_              （§263）栈 4 + EDX(mask) + EDI(end)       add esp, 10h
transformedCapsuleTrace_ （§263）栈 5 + ECX(targetBounds) + EDX(end)  add esp, 14h
transformedBrushModelTrace_（§264）栈 6 + ECX(targetOrigin) + EDX(start)  add esp, 18h
```

**⇒ 三个函数三个 ABI** —— 而**每一个都必须单独核实。**

**⇒ 这是本项目里"同一族函数不能假设同 ABI"的最强实例。**

### 3.14 汇编实现

```php
__asm
{
    mov ecx, targetOriginPointer
    mov edx, startPointer
    push targetAnglesPointer      // 栈 6
    push targetContents           // 栈 5
    push clipHandle               // 栈 4
    push boundsPointer            // 栈 3
    push endPointer               // 栈 2
    push resultPointer            // 栈 1
    call function
    add esp, 18h                  // 24 = 6 个参数
}
```

**⇒ 六个栈参数 + ECX + EDX = 八个通道** ✓ 与对照表一致。

### 3.15 **ECX/EDX 不需要保护**

**⇒ ECX 与 EDX 都是 caller-saved** ✓

**⇒ 与 §263 的 `traceCapsule` 需要 `push edi` 不同**（那里用 EDI）。

## 四、`compareNativeServerCapsuleTrace`：**六项差异位掩码**（本组第二重要）

### 4.1 那段"opt-in"的理由

```cpp
// This comparison invokes a second native SV_Trace for every source
// collision query. Keep it opt-in after source/native parity has been
// established; at two clients it can execute hundreds of times per
// second and disturb the authoritative 20 Hz frame cadence.
```

### 4.2 三个数

```text
每个源碰撞查询一次额外 native SV_Trace
两个客户端时每秒数百次
会干扰权威 20 Hz 帧节奏
```

**⇒ 所以"在源/原生一致性建立之后保持 opt-in"。**

### 4.3 而 `20 Hz` 是权威帧率

**⇒ 与记忆里"Server frame interval default 100 ms（retail cadence; host drives at 30 Hz）"对应** —— **100 ms = 10 Hz**？不，20 Hz = 50 ms。

**⇒ 而 §263 里说"a 63 ms frame"** ≈ 16 Hz。

**⚠ 三个帧率数字**：

```text
§263   63 ms 帧          ≈ 16 Hz
§264   权威 20 Hz        = 50 ms
记忆    默认 100 ms 间隔  = 10 Hz
```

**⇒ 三个不同的数。可能是不同的上下文（客户端渲染帧 vs 服务端 tick vs 默认配置）。**

## 五、`compareNativeServerCapsuleTrace` 的**五项跳过条件**

```cpp
if (!nativeTraceComparisonEnabled()) return;
const auto capsuleExtent = bounds.halfSize[0] + bounds.halfSize[1] + bounds.halfSize[2];
if (gameThreadId_.load() != GetCurrentThreadId() ||
    capsuleExtent == 0.0f ||
    glassState.nonSolidPieceCount() != 0 ||
    !nativeServerEntityMirrorMatches(entities))
{
    return;
}
```

### 5.1 五项

```text
① 开关（先查）
② 【必须在游戏线程】
③ capsuleExtent 非零
④ 【没有非实心玻璃片】
⑤ 原生实体镜像必须匹配
```

### 5.2 ③ 的理由

**`halfSize[0] + halfSize[1] + halfSize[2] == 0` ⇒ 退化胶囊 ⇒ 不比较。**

**⚠ 但三个半尺寸相加为零**不一定**意味着退化 —— 如果一个是负的（不合法但也可能）可能抵消。**

**⇒ 而 `validTraceInput` 应该已经拒绝负的半尺寸。**

**⇒ 所以这个检查是"三个都是 0"的间接表达。**

### 5.3 ④ 的理由

**"没有非实心玻璃片"** —— 因为玻璃状态会影响 trace，而原生调用与源调用用的玻璃状态可能不同。

**⇒ 所以只在"玻璃不影响"时比较。**

### 5.4 ⑤ 是最重要的

**`nativeServerEntityMirrorMatches(entities)`** —— 原生侧镜像必须与 `entities` 一致。

**⇒ 否则原生 `SV_Trace` 会看到不同的实体。**

## 六、`NativeIgnoreEntParams` 的**两个哨兵**

```cpp
const NativeIgnoreEntParams ignore{
    .baseEntity = filter.passEntityNum
        ? (int32)*filter.passEntityNum
        : 2047,
    .parentEntity = filter.passOwnerEntityNum
        ? (int32)*filter.passOwnerEntityNum
        : -1,
};
```

### 6.1 两个不同的哨兵

```text
baseEntity    默认 2047    （ENTITYNUM_NONE）
parentEntity  默认 -1      （ENTITYNUM_NONE 的另一种）
```

**⇒ **两个不同的** "none" 值。**

**⚠ 这与 §263 里 `contentMask` 之类不同 —— 这里两个"无实体"用两个不同的数。**

**⇒ 可能需要核实 `2047` 与 `-1` 在引擎里各自的含义。**

**`2047 = 0x7FF`** —— 与记忆里"11 位"的满值一致（`0x7FF`）。

**⇒ 所以 `baseEntity` 是 11 位的（0..2047）而 `-1` 对 `parentEntity` 是"无"。**

### 6.2 而 `filter.passEntityNum` 是 `optional`

**`filter.passEntityNum ? *... : 2047`** ⇒ `nullopt` ⇒ 2047。

## 七、`invokeSVTrace` 的**七项参数**

```php
if (!invokeSVTrace(svTrace_, ignore, start, end, bounds, contentMask, nativeResult, exceptionDetails))
{
    ++nativeTraceUnavailableCount_;
    char failure[160]{};
    snprintf(failure, sizeof(failure), "native_exception code=0x%08lX address=%p",
        (unsigned long)exceptionDetails.code, exceptionDetails.address);
    if (failure != nativeTraceComparisonFailure_)
    {
        write("native trace comparison unavailable stage=" + failure);
        nativeTraceComparisonFailure_ = failure;
    }
    return;
}
```

### 7.1 八项

```text
svTrace_            函数指针
ignore              两个实体号
start / end / bounds  三个几何
contentMask         掩码
nativeResult        输出
exceptionDetails    异常信息
```

### 7.2 **`invokeSVTrace` 是包装函数**

**⇒ 与 §263/§264 的内联汇编不同** —— 这是一个命名函数，大概也是 `__try` 包装（因为 `exceptionDetails`）。

**⇒ 所以本文件里有**两种**原生命令调用方式：**

```text
内联 __asm          （traceCapsule / transformedCapsule / transformedBrushModel）
包装函数+__try       （invokeSVTrace / invokeOwnershipResolver / tryCallVoid / ...）
```

### 7.3 而错误消息的**两级去重**

```cpp
if (failure != nativeTraceComparisonFailure_)
{
    write("native trace comparison unavailable stage=" + failure);
    nativeTraceComparisonFailure_ = failure;
}
```

**⇒ 边沿触发** ✓ 与 §244/§256 的 `refuse` 同族。

## 八、**"恢复"的日志**

```php
const auto nativeTrace = decodeTraceResult(nativeResult);
if (!nativeTrace)
{
    ++nativeTraceUnavailableCount_;
    if (nativeTraceComparisonFailure_ != "invalid_result")
    {
        write("native trace comparison unavailable stage=invalid_result");
        nativeTraceComparisonFailure_ = "invalid_result";
    }
    return;
}

if (!nativeTraceComparisonFailure_.empty())
{
    write("native trace comparison recovered");
    nativeTraceComparisonFailure_.clear();
}
```

### 8.1 三个状态

```text
正常          nativeTraceComparisonFailure_ 为空
失败中        非空（不是 "invalid_result"）
解码失败      等于 "invalid_result"
```

### 8.2 ⚠ **`"invalid_result"` 与真实失败消息共用同一个字段**

**⇒ 所以 `!empty()` 的判断包括 `"invalid_result"`。**

**⇒ 而如果一个 `"invalid_result"` 之后恢复正常，会打印 "recovered"。**

**✓ 语义正确。**

## 九、**六项差异的位掩码**

```php
const auto difference = SV_CompareTraceResults(sourceTrace, *nativeTrace);
if (difference == SvTraceComparisonDifference::None)
{
    if (!nativeTraceComparisonObservedSuccess_)
    {
        write("native trace comparison active owner=source");
        nativeTraceComparisonObservedSuccess_ = true;
    }
}
else
{
    ++nativeTraceMismatchCount_;
    const auto differenceBit = uint32{1} << (uint8)difference;
    if (!(nativeTraceLoggedDifferenceMask_ & differenceBit))
    {
        nativeTraceLoggedDifferenceMask_ |= differenceBit;
        char details[512]{};
        snprintf(details, ...,
            "native trace mismatch field=%s source_fraction=%.6f "
            "native_fraction=%.6f source_hit=%lu/%u "
            "native_hit=%lu/%u source_contents=0x%08lX "
            "native_contents=0x%08lX start=[%.3f,%.3f,%.3f] "
            "end=[%.3f,%.3f,%.3f]", ...);
        write(details);
    }
}
```

### 9.1 **`differenceBit = 1 << difference`**

**⇒ 所以 `SvTraceComparisonDifference` 是**位标志**。**

**⇒ 而 `difference == None` 单独检查，所以 `None` 是 0。**

**⚠ 如果 `difference` 是一个组合（多个位），`1 << difference` 会溢出。**

**⇒ 除非 `SvTraceComparisonDifference` 每次只返回一个位。**

**⇒ 而从 `traceDifferenceName(difference)` 返回单个名字看，它是一个**枚举**而不是位集。**

**⇒ 所以 `1 << difference` 是"枚举值 → 位位置"的映射。**

**⇒ 这要求枚举值 < 32。**

### 9.2 六项打印

```text
fraction        source vs native
hitType/hitId   source vs native（%lu/%u 一对）
contents        source vs native
start           三个浮点
end             三个浮点
```

**⇒ 十个量。**

**⇒ 而 `hitType/hitId` 用 `%lu/%u` 是"类型/编号"的一对。**

### 9.3 **"每种差异只打印一次"**

```cpp
if (!(nativeTraceLoggedDifferenceMask_ & differenceBit))
{
    nativeTraceLoggedDifferenceMask_ |= differenceBit;
    ... 打印 ...
}
```

**⇒ 位掩码去重** —— 与 §240 的 `ordinalReported`（字符串集）、§244 的 `refuse`（边沿）不同。

**⇒ 这是"按类别去重"的第三种手法。**

### 9.4 而 `"active owner=source"` 只打印一次

```cpp
if (!nativeTraceComparisonObservedSuccess_)
{
    write("native trace comparison active owner=source");
    nativeTraceComparisonObservedSuccess_ = true;
}
```

**⇒ 一次性标志** —— 与 `std::call_once` 类似但手写。

**"owner=source"** ⇒ 说明**源实现是权威**，原生只是参照。

**⇒ 这是一个重要的架构声明** ✓

## 十、关键结论

1. **brush model trace 的 1649370 ABI 与 3.3.3.3 相比，八行里三行成对互换**（`start↔result`、`targetOrigin↔targetAngles`、`ECX↔EDX` 角色互换）。
2. **`start↔result` 的互换是栈溢出写** —— 往 12 字节的 vec3 写 40 字节结果。
3. **`targetOrigin↔targetAngles` 是静默错误** —— 两个都是 12 字节浮点数组。
4. **"CARRYING 3.3.3.3's FORM HANDED THE CALLEE A 12-BYTE vec3 AS ITS 40-BYTE RESULT BUFFER"** —— 明确写出的后果。
5. **`NativeTraceResult` = 40 字节（0x28）**。
6. **`fld [ecx] / fld [ecx+4]` 只读两个角度分量** —— roll 被忽略。
7. **零测试证明 `[ebp+1C]` 在 1649370 是 angles** —— 一个非常干净的证据。
8. **每 build 两个调用点**，且与 `sv_trace` 的调用点只差几十字节（box clip 里连续调两个）。
9. **三个 trace 函数三个 ABI**：`add esp` 分别 10h / 14h / 18h。
10. **`compareNativeServerCapsuleTrace` 是 opt-in** —— 每秒数百次会干扰 20 Hz 权威帧。
11. **三个帧率数字并存**（63 ms ≈ 16 Hz / 20 Hz / 100 ms = 10 Hz）。
12. **五个跳过条件**，其中"无非实心玻璃片"是因为玻璃状态会影响 trace。
13. **`NativeIgnoreEntParams` 用两个不同的哨兵**（`2047` 与 `-1`）。
14. **两种原生命令调用方式并存**（内联 `__asm` 与 `__try` 包装）。
15. **差异日志按**类别**位掩码去重** —— 第三种去重手法。
16. **`owner=source`** —— 源实现是权威，原生只是参照。

## 十一、未闭合点

- `SvTraceComparisonDifference` 的枚举值与总数（必须 < 32）。
- 三个帧率数字的上下文区分。
- `2047` 与 `-1` 两个哨兵各自的引擎语义。
- `invokeSVTrace` 的实现（是否有 `__try`）。
- `EngineBindings.cpp` 17650 行之后未读取。
