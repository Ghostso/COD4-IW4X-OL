# 263 · `SLOW TRACE` 的三层计时、`TRACE CENSUS` 的 50 ms/63 ms、**两个 trace 的参数顺序在 build 之间互换**

## 一、范围

本报告学习 `EngineBindings.cpp` 17216–17450 行。

## 二、`SlowTraceReport`：**析构函数里的计量**

```cpp
struct SlowTraceReport
{
    const std::array<float,3> &start;
    const std::array<float,3> &end;
    const TraceBounds &bounds;
    std::uint32_t contentMask;
    std::chrono::steady_clock::time_point began{ std::chrono::steady_clock::now() };

    ~SlowTraceReport() { ... }
} slowTraceReport{ start, end, bounds, contentMask };
```

### 2.1 **一个 RAII 计时器**

**在构造时记时间、在析构时报告。**

**⇒ 所以"trace 耗了多久"由作用域结束自动度量** ✓

### 2.2 那句"输入不是退化的"

```cpp
// The input is NOT degenerate -- validTraceInput above already rejects
// non-finite starts, ends, midpoints and half-sizes, and negative extents --
// so this says WHICH query goes deep rather than assuming why.
```

**⇒ 所以慢 trace 不是"坏输入"而是"真的深"。**

**"它说的是**哪一个**查询变深，而不是假定为什么。"**

### 2.3 "沉默时无异常，且有上限以便报告器永远不会变成它所测量的东西"

```cpp
// Silent while nothing is wrong, and capped so the reporter can never become
// the thing it is measuring.
```

**⇒ `reported >= reportLimit(16)` ⇒ 最多 16 行。**

**⇒ 这是"诊断不能成为问题"的第 N 次**（§239 的 60,249 次、§244 的 `refuse` 封顶、§259 的 `limit`）。

## 三、**`TRACE CENSUS` 的三层计数**

### 3.1 第一层：`censusCount` / `censusMicroseconds` / `censusBegan`

```cpp
static std::uint64_t censusCount{};
static std::uint64_t censusMicroseconds{};
static auto censusBegan = finished;
++censusCount;
censusMicroseconds += elapsed;
const auto window = (uint64)(finished - censusBegan).count()  [microseconds];
```

**⇒ 两个计数器 + 一个窗口起点。**

### 3.2 第二层：5 秒窗口 + 两个开关

```cpp
if (window >= 5'000'000 && !SV_PerfBaseline() && OlMod::RuntimeLog::verbose())
```

**⇒ 三个条件**：

```text
窗口 >= 5 秒
非 perf-baseline 模式
【verbose 日志开启】
```

**"★ 2026-10-13（热日志修复）：5 s 窗口统计默认关（`OLMOD_VERBOSE_LOG`）"**

**⇒ 中文注释标明这是后来的修复。**

### 3.3 第三层：报告的六个量

```cpp
"TRACE CENSUS %llu traces in %llu ms = %llu/s, %llu us in traces (%.1f%% of wall), mean %.1f us"
```

```text
censusCount                        trace 总数
window / 1000                      窗口毫秒
censusCount * 1e6 / window         每秒 trace 数
censusMicroseconds                 总微秒
100.0 * censusMicroseconds / window  占墙钟百分比
censusMicroseconds / censusCount   平均微秒
```

### 3.4 **`window | 1` 与 `censusCount | 1`**

```cpp
censusCount * 1'000'000 / (window | 1)
...
static_cast<double>(censusMicroseconds) / static_cast<double>(censusCount | 1)
```

**⇒ `| 1` 保证分母非零。**

**⚠ 但 `window | 1` 在 `window == 0` 时得 1，在 `window == 2` 时得 3。**

**⇒ 所以它不是"避免除零"而是"改变分母值"。**

**⇒ 对于 `window >= 5,000,000`，`window | 1` 只影响最低位（±1）⇒ 可忽略。**

**⇒ 对于 `censusCount`，`| 1` 只在 `censusCount == 0` 时改变值（0 → 1），而那时 `censusMicroseconds` 也是 0 ⇒ 结果 0/1 = 0 ✓**

**⇒ 所以 `| 1` 在这里是正确的技巧，虽然它同时改变了奇数的值。**

### 3.5 **窗口是 `censusBegan = finished`（第一个 trace 的时间）**

```cpp
static auto censusBegan = finished;
```

**⇒ 静态初始化在第一次进入时执行** —— 所以 `censusBegan` 是**第一个** trace 的结束时间。

**⇒ 所以第一个 trace 的 `window = 0`** ⇒ 不报告 ✓

### 3.6 而 `censusBegan` 在报告后重置为 `finished`

```cpp
censusCount = 0;
censusMicroseconds = 0;
censusBegan = finished;
```

**⇒ 所以窗口是**滚动的 5 秒**（每次报告后重启）** ✓

### 3.7 **那两个 50 ms / 63 ms**

```cpp
// OLMOD(trace-census): section 103d put 50 ms of a 63 ms frame in
// clientThink, and section 97g priced a trace at ~250 us against tens
// of microseconds for a real CoD trace. Whether that is a handful of
// very expensive descents or a flood of cheap ones decides the fix,
// and nothing here knew which.
```

### 3.8 四个数

```text
50 ms          clientThink 占 63 ms 帧的
63 ms          一帧
~250 us        一个 trace 的实测
tens of us     真 CoD trace 的量级
```

**⇒ 所以我们的 trace 比真 CoD **慢 5-25 倍**。**

### 3.9 而"这决定修法"

```text
少数非常昂贵的下降  vs  大量便宜的下降
```

**⇒ 两个不同的修法，而"这里不知道是哪个"。**

**⇒ 所以 `TRACE CENSUS` 的存在理由是**分辨这两者**。

**这是一个"用计数分辨两种可能的性能问题"** —— 而 `SLOW TRACE` 与 `TRACE CENSUS` 正好是这两个半边。

### 3.10 `SLOW TRACE` 的阈值是 **50 ms**

```cpp
constexpr std::uint64_t slowMicroseconds = 50'000;      // 50 ms
if (elapsed < slowMicroseconds || reported >= reportLimit || SV_PerfBaseline()) return;
```

**⇒ 50 ms 是"半个 63 ms 帧"。**

**⇒ 所以任何单次 trace 吃半个帧就报告。**

**⚠ 但 §263 开头说"50 ms of a 63 ms frame in clientThink"** —— 那是**整帧里 clientThink 占一半**，而不是单次 trace。

**⇒ 所以 50 ms 的阈值可能**太高**（一次 trace 5 ms 就已经很贵）。**

**⇒ 注释没有解释为什么选 50 ms。**

## 四、`traceCapsule` 的**六个参数**

```cpp
const auto mask = contentMask;
__asm
{
    push edi
    mov edi, endPointer        // ← 【end 在 EDI】
    mov edx, mask              // ← 【contentMask 在 EDX】
    push callbacksPointer
    push boundsPointer
    push startPointer
    push resultPointer
    call function
    add esp, 10h               // ← 【清 4 个参数 = 16 字节】
    pop edi
}
```

### 4.1 五个通道

```text
result        【栈参数 1】（最后 push ⇒ 最低地址 ⇒ 最靠近返回地址）
start         【栈参数 2】
bounds        【栈参数 3】
callbacks     【栈参数 4】
contentMask   【EDX】
end           【EDI】
```

### 4.2 **`add esp, 10h` = 16 = 4 个栈参数**

**⇒ 所以调用者清 4 个栈参数** ✓ 与五个通道里四个在栈上一致。

### 4.3 **`push edi` / `pop edi` 保护 callee-saved**

**⇒ 因为 `__usercall` 用 EDI 传参，而 EDI 是 callee-saved。**

**⇒ 所以调用者必须保存并恢复它。**

**这是一个正确的 ABI 处理** ✓

### 4.4 而 `edx` 不需要保存

**⇒ EDX 是 caller-saved** ✓

## 五、**两个 trace 的参数顺序在 build 之间互换**（本组最重要的一段）

### 5.1 那段完整的对照表

```php
// CODREF(sv_trace): 1649370's convention is NOT 3.3.3.3's. Section 74.
//
//                    3.3.3.3 0x0058B330      1649370 0x00668560
//   [ebp+08] arg1    result                  result
//   [ebp+0C] arg2    start                   start
//   [ebp+10] arg3    bounds                  bounds
//   [ebp+14] arg4    targetBounds            contents
//   [ebp+18] arg5    contents                targetOrigin
//   ECX              targetOrigin            targetBounds
//   end              EAX                     EDX
```

### 5.2 七个通道的完整对照

| 通道 | 3.3.3.3 | 1649370 |
|---|---|---|
| `[ebp+08]` | `result` | `result` |
| `[ebp+0C]` | `start` | `start` |
| `[ebp+10]` | `bounds` | `bounds` |
| **`[ebp+14]`** | **`targetBounds`** | **`contents`** |
| **`[ebp+18]`** | **`contents`** | **`targetOrigin`** |
| **`ECX`** | **`targetOrigin`** | **`targetBounds`** |
| **`end`** | **`EAX`** | **`EDX`** |

### 5.3 **四个位置全部变了**

```text
arg4   targetBounds ↔ contents          【互换】
arg5   contents     ↔ targetOrigin      【移位】
ECX    targetOrigin ↔ targetBounds      【移位】
end    EAX          ↔ EDX               【换寄存器】
```

**⇒ 所以 `targetBounds`、`contents`、`targetOrigin` 这三个参数**循环移位**了一位，而 `end` 换了寄存器。**

**⇒ 如果照 3.3.3.3 的写法调用 1649370 的函数：**

```text
targetBounds 会拿到 contents（一个 uint32 当指针用）
contents     会拿到 targetOrigin（一个 float* 当 uint32 用）
targetOrigin 会拿到 targetBounds（一个结构指针）
end          在 EAX 而函数从 EDX 读 ⇒ 垃圾
```

**⇒ 结果是一个**必然崩溃或产生垃圾 trace** 的调用。**

### 5.4 **"实测四种方法，不是从名字读出来的"**

```php
// Measured four ways, not read off a name. Both of out.exe's own call
// sites agree (0x0046DC81 in the box clip, 0x0046E3F6 in the point
// clip) and so do both of 3.3.3.3's (0x005FB4D1 server, 0x00458DCE
// client). The callee settles it too: 0x0058B330 pushes its incoming
// EAX straight into 0x00588BC0 and reads [ebp+14]/[ebp+18], while
// 0x00668560 saves incoming ECX to [ebp-0x34], pushes incoming EDX,
// and reads [ebp+18] as the vector 0x0058B330 takes in ECX.
```

### 5.5 四种证据

```text
① out.exe 自己的两个调用点（0x0046DC81 box clip、0x0046E3F6 point clip）一致
② 3.3.3.3 的两个调用点（0x005FB4D1 server、0x00458DCE client）一致
③ 3.3.3.3 的被调方：把 EAX 推进 0x00588BC0，读 [ebp+14]/[ebp+18]
④ 1649370 的被调方：把 ECX 存到 [ebp-0x34]，push EDX，把 [ebp+18] 当作 3.3.3.3 在 ECX 收的那个向量
```

**⇒ "被调方也确定了它"** —— 从被调方的实现反推参数位置。

**这是一个极其严谨的方法** —— 四个独立的证据源。

### 5.6 而第四项**最精妙**

**"0x00668560 把 `[ebp+18]` 当作 3.3.3.3 在 ECX 收的那个向量"**

**⇒ 所以 1649370 的 `arg5` = 3.3.3.3 的 `ECX` = `targetOrigin`。**

**⇒ 而 1649370 的 `ECX` = 3.3.3.3 的 `arg4` = `targetBounds`。**

**⇒ 一次"循环右移"被完整证实。**

### 5.7 而 §204 里 `SV_Trace` 的"四个错误参数"

**记忆**："`SV_Trace` **four wrong arguments** ⇒ 'one unit per pmove, forever'"

**⇒ 所以这个项目曾经在**另一个** trace 函数上犯过同类错误。**

**⇒ §263 是那个教训的第二次应用**（同一个 bug 类，不同的函数）。

### 5.8 而 `traceCapsule` 的参数顺序是**第三种**

```cpp
push callbacksPointer      // 栈 4
push boundsPointer         // 栈 3
push startPointer          // 栈 2
push resultPointer         // 栈 1
// contentMask 在 EDX，end 在 EDI
```

**⇒ 所以 `traceCapsule`（对应 `worldTrace_`）的约定与两个 `sv_trace` 都**不同**：**

```text
result      栈 1        三个都是
start       栈 2        三个都是
bounds      栈 3        三个都是
【栈 4】     callbacks  （traceCapsule）
             targetBounds（3.3.3.3）
             contents    （1649370）
【其它】     contentMask+EDX / end+EDI   （traceCapsule）
```

**⇒ 所以 `traceCapsule` 是第三个函数（`worldTrace_`），它的 ABI 又不同。**

**⇒ 三个 trace 函数三种 ABI。**

## 六、`traceTransformedCapsule` 的**三层计时结构**

```cpp
struct ActorCapsuleCost
{
    bool enabled{};
    std::chrono::steady_clock::time_point began{};
    ~ActorCapsuleCost() { ... }
};
static const bool profileActorCapsules = [] {
    std::array<char,8> value{};
    return GetEnvironmentVariableA("OLMOD_ZM_PLAYER_COLLISION_PROFILE", value.data(), 8) == 1
        && value[0] == '1';
}();
ActorCapsuleCost cost;
cost.enabled = profileActorCapsules && entity.bodyRole == SvCollisionBodyRole::Actor && entity.contents == 1u;
if (cost.enabled) cost.began = std::chrono::steady_clock::now();
```

### 6.1 三项门

```text
环境变量开
entity.bodyRole == Actor
entity.contents == 1u
```

**⇒ 只有"僵尸玩家胶囊"被计时。**

### 6.2 `entity.contents == 1u` 是很窄的条件

**⇒ `contents == 1` 大概是 `CONTENTS_SOLID`。**

### 6.3 而 `thread_local` 的三个静态量

```cpp
static thread_local auto window = now;
static thread_local std::uint64_t calls{}, total{}, peak{};
```

**⇒ 四个 `thread_local`** —— 所以每个线程独立统计。

**⇒ 与 §263 前半段的 `TRACE CENSUS`（非 thread_local）不同。**

**⇒ 两处对"是否按线程分开"的处理不同。**

### 6.4 而 `enabled` 门在计时**之后**

```cpp
ActorCapsuleCost cost;
cost.enabled = ...;
if (cost.enabled) cost.began = ...;
if (!transformedCapsuleTrace_ || !validTraceInput(...) || !SV_IsCollisionEntityValid(entity))
    return std::nullopt;
```

### 6.5 ⚠ **`enabled` 为 false 时 `began` 是默认的（epoch）**

**而析构函数**先检查 `if (!enabled) return;`** ⇒ 所以不会用 `began`。**

**✓ 正确。**

### 6.6 但 `cost.began` 只在 `enabled` 时设置

**⇒ 而构造函数里 `began{}` 是 epoch。**

**⇒ 所以 `enabled == false` 时 `began` 无意义但不会被用** ✓

## 七、`transformedCapsuleTrace_` 的**三处前置**

```cpp
if (!transformedCapsuleTrace_ || !validTraceInput(start, end, bounds, entity.contents) ||
    !SV_IsCollisionEntityValid(entity))
    return std::nullopt;
```

### 7.1 三项

```text
函数已绑定
四个输入有效（含 entity.contents）
实体有效
```

**⇒ 与 §263 开头 `traceCapsule` 的 `!trace_ || !validTraceInput(...)` 相比多了一项实体检查。**

## 八、`encodeTraceResult(initialTrace)` 的**初始值传递**

```cpp
auto native = encodeTraceResult(initialTrace);
...
push resultPointer
call function
```

### 8.1 **`initialTrace` 是输入而不是输出**

**⇒ `encodeTraceResult` 把 C++ 结构转成原生结构，然后当作**输入**传进去。**

**⇒ 所以原生函数**读取**初始值（例如 `fraction = 1.0`）。**

**这与 §263 开头 `traceCapsule` 的 `NativeTraceResult native{};`（零初始化）不同。**

**⇒ 两个函数对"初始 trace"的处理不同。**

### 8.2 而 §263 里 `traceTransformedBrushModel(initialTrace, ...)` 也用 `initialTrace`

**⇒ 所以 `initialTrace{ .fraction = 1.0f }` 是"从头开始的 trace"。**

## 九、关键结论

1. **RAII 计时器（`SlowTraceReport`）在析构时报告** —— 所以"trace 耗了多久"自动度量。
2. **`TRACE CENSUS` 与 `SLOW TRACE` 正好是"大量便宜"与"少数昂贵"的两个半边** —— 而 §103d 的 50 ms/63 ms 是分辨它们的动机。
3. **~250 us 的 trace 对比真 CoD 的几十 us** —— 慢 5-25 倍。
4. **`window | 1` / `censusCount | 1` 是正确的除零技巧**（只在零时改变值）。
5. **`SLOW TRACE` 的 50 ms 阈值可能太高**（一次 trace 5 ms 就极贵）—— 无注释。
6. **`traceCapsule` 的六个通道：4 栈 + EDX + EDI，`add esp, 10h`**。
7. **`push edi`/`pop edi` 因为 EDI 是 callee-saved 而用于传参**。
8. **两个 `sv_trace` 函数的参数顺序**在 build 之间循环移位**，`end` 从 EAX 换到 EDX**。
9. **四种独立证据**（两个 out.exe 调用点、两个 3.3.3.3 调用点、两个被调方实现）。
10. **像 3.3.3.3 那样调 1649370 会必然崩溃或产生垃圾**（指针与 uint32 互换）。
11. **§204 里 `SV_Trace` 的"四个错误参数"是这个 bug 类的第一次**；§263 是第二次。
12. **三个 trace 函数三种 ABI**（`traceCapsule` / 3.3.3.3 / 1649370）。
13. **`entity.contents == 1u` 是 `CONTENTS_SOLID`**，所以只有实心实体被计时。
14. **`ActorCapsuleCost` 用 `thread_local` 而 `TRACE CENSUS` 不用** —— 两处不一致。
15. **`encodeTraceResult(initialTrace)` 传初始值，而 `traceCapsule` 用零初始化** —— 两处不同。

## 十、未闭合点

- `SLOW TRACE` 的 50 ms 阈值依据。
- `traceCapsule` 与 `worldTrace_` 的完整 ABI（只有六个通道可从汇编读出）。
- `NativeTraceResult` / `TraceResult` 的字段布局（`decodeTraceResult` 未读）。
- `EngineBindings.cpp` 17450 行之后未读取。
