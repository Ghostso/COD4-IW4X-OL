# 192 · `EngineBindings.cpp` 开头：DObj 池步长 0xD8、VEH 见证、两个异常捕获器

## 一、范围

本报告学习 `EngineBindings.cpp` 前 150 行。

## 二、DObj 池步长是 **0xD8** 而不是 0xCC

### 2.1 四处独立证据

```text
CODDIFF(1649370): THE DObj POOL STRIDE IS 0xD8, NOT 3.3.3.3's 0xCC.
out.exe 里每一处内联查找都把 map entry 乘以 216：
    allocator   sub_66BEE0      &unk_77E9720 + 216 * v5
    predicate   sub_74E160
    bulk walk1  sub_66BFF0
    bulk walk2  sub_66C050
```

### 2.2 后果

> **在 0xCC 下，索引 0 之后的每一个 DObj 都是错误的对象，错 `12 * index` 字节。**

`0xD8 - 0xCC = 0xC = 12` —— 正好是每项差 12 字节。

**这个错误的形态**：不是崩溃，是**拿到另一个对象**。所以任何"看起来能跑但动画不对"的症状都可能源于此。

### 2.3 与之前的 `ServerDObjMap` 呼应

§183 里记过：

```text
ServerDObjGet VA 0x0059E570 → ServerDObjMap VA 0x02E8D050
ServerAnimDObjMap VA 0x02EF4858（直接按 entityState.number 索引）
```

**两个表指向同一个池**，而池的步长现在是 0xD8。

## 三、八个 `atomic` 指针：DObj 系统的全局绑定

```cpp
std::atomic<std::byte*>    ServerDObjEntityBase{};
std::atomic<std::uint16_t*> ServerDObjMap{};
std::atomic<std::uint8_t*>  ServerDObjInUse{};
std::atomic<std::uint32_t*> ServerDObjFreeCount{};
std::atomic<std::byte*>     ServerDObjPool{};
std::atomic<void*>          ServerDObjCreateTarget{};
std::atomic<void*>          ServerDObjGetTarget{};
std::atomic<void*>          DObjFreeTarget{};
```

**八个全局指针都是 `atomic`** —— 因为 DObj 系统可能在多个线程被访问，而这些指针在 `bind()` 之后才有效。

**前五个是数据地址，后三个是函数地址**。

## 四、`NativeServerAnimationStateDiagnostics = false`

```cpp
// Bring-up only. BG_PlayerAnimation can run several times per server frame
// (once for each admitted usercmd), and zombie gameplay changes the reported
// lerp state on nearly every call. Formatting and synchronously writing those
// transitions caused observable frame stalls even with the console hidden.
constexpr bool NativeServerAnimationStateDiagnostics = false;
```

**三条实测事实**：

1. `BG_PlayerAnimation` **每帧可能跑多次**（每条被接纳的 usercmd 一次）；
2. 僵尸玩法**几乎每次调用都改变**报告的 lerp 状态；
3. **格式化并同步写这些转换会造成可观察的帧停顿，即使控制台隐藏**。

**"即使控制台隐藏"** 是重要细节——说明停顿来自**格式化 + 同步 I/O**，而不是窗口重绘。

**这是一个 `constexpr bool` 而不是运行时开关** —— 编译期关掉，所以零成本。

## 五、`NativeExceptionDetails` vs `NativeFault`：两个捕获器的分工

### 5.1 完整版（22 行）

```cpp
int captureNativeException(EXCEPTION_POINTERS* exception, NativeExceptionDetails* details) noexcept
{
    details->code = record->ExceptionCode;
    details->address = record->ExceptionAddress;
    if (code == EXCEPTION_ACCESS_VIOLATION && NumberParameters >= 2) {
        details->accessType = ExceptionInformation[0];
        details->faultAddress = ExceptionInformation[1];
    }
#if defined(_M_IX86)
    context->Eax/Ebx/Ecx/Edx/Esi/Edi/Ebp/Esp/Eip
#endif
    return EXCEPTION_EXECUTE_HANDLER;
}
```

**九个寄存器 + 四个异常字段**。

`#if defined(_M_IX86)` 的守卫 — 说明这段代码**只为 x86 编译**，在其他架构上 `NativeExceptionDetails` 的寄存器字段保持为零。

### 5.2 精简版（19 行）

```cpp
struct NativeFault {
    std::uint32_t code;
    std::uint32_t address;     // ExceptionAddress, absolute
    std::uint32_t operation;   // 0 read, 1 write, 8 execute
    std::uint32_t target;      // the address it touched
};
```

注释解释了它为什么存在：

> **一个异常【码】单独无法区分"null 的 WeaponDef 字符串"与"在一个没有错误帧的线程上 `Com_Error` longjmp"**，**而这两者要相反的修法**。两者都读 `0xC0000005`，都从同一个调用出来。
>
> **出错的【指令】在一行之内把它们分开**：减去模块基址，RVA 直接落进 IDA。

**`operation` 的三个值**：

```text
0 = read
1 = write
8 = execute
```

**`8 = execute`** 是"跳到非代码地址"，与读/写完全不同的一类。

### 5.3 两者都返回 `EXCEPTION_EXECUTE_HANDLER`

**它们都用在 `__except` 表达式里**（`__except(captureNativeException(...))`），所以返回值必须是异常处理常量。

`noexcept` 保证捕获过程本身不抛。

## 六、VEH 见证：`__try` 抓不到的死亡

这是本组最重要的一段。

### 6.1 症状

```text
dedicated 进程死在 BG_AnimParseAnimScript 里，而日志里【什么都没有】——
没有异常码，没有 stage —— 而那是 __try 【产生不了】因而【无法解释】的东西。
```

### 6.2 为什么 VEH 能

> **一个 vectored handler 跑在任何 SEH 帧之前、在任何东西能展开或退出之前**，**所以即使进程即将消失，它也拿到机会写那一行。**

三层顺序：

```text
硬件异常
  → VEH（first-chance，AddVectoredExceptionHandler(1,...)）
  → SEH 帧（__try/__except）
  → 默认处理器（进程终止）
```

**VEH 在最前面**，所以 `__try` 抓不到的东西它能抓。

### 6.3 它只"见证"

> **它只【见证】：返回 `EXCEPTION_CONTINUE_SEARCH` 所以正常处理不变**，而它**过滤到值得记一行的码**，这样普通的已处理异常不会填满日志。

**`CONTINUE_SEARCH` 而不是 `CONTINUE_EXECUTION`** —— 不改变任何行为。

### 6.4 四个状态

```cpp
std::atomic<std::uint8_t*> VectoredWitnessModule{};
std::atomic<const char*>   CurrentNativeStage{"none"};
std::atomic<std::uint32_t> VectoredWitnessCount{};
void*                      VectoredWitnessHandle{};
```

`CurrentNativeStage` 的初值是 **`"none"`** —— 与 `NativeStageScope` 的析构值相同。

`VectoredWitnessCount` 是封顶计数（与前面反复出现的"日志封顶"一致）。

### 6.5 `witnessCanRead` 为什么要重复实现

```cpp
// A local readability probe, because the file's readableSpan is defined a
// couple of thousand lines further down and this runs before it.
bool witnessCanRead(const void* address, std::size_t length)
```

**同一文件里两个可读性探测函数，因为定义顺序** —— 这是一个可以指出的小重复：`readableSpan` 与 `witnessCanRead` 做同一件事，只是位置不同。

而**在 VEH 里做可读性探测是必须的**：见证器本身不能 fault。

## 七、关键结论

1. **DObj 步长 0xD8 用四处内联乘法交叉验证**，错 0xCC 会让每个 DObj 错 12×index 字节。
2. **诊断代码可以是 `constexpr bool = false`** —— 编译期关掉，零成本。
3. **异常码相同不代表原因相同**：`0xC0000005` 既可能是 null 解引用，也可能是 `Com_Error` longjmp；**只有出错的指令能区分**。
4. **VEH 跑在 SEH 之前**，所以它能记录 `__try` 看不到的死亡。
5. **见证器必须 `CONTINUE_SEARCH`**，否则会改变程序行为。
6. **见证器内部不能再 fault**，所以自带可读性探测。

## 八、未闭合点

- `witnessCanRead` 与 `readableSpan` 的重复未合并。
- `EngineBindings.cpp` 150 行之后未读取（共约 917 KB）。
