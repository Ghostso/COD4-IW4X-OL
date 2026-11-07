# 193 · 故障见证的完整实现：RVA、寄存器、记录、栈扫描

## 一、范围

本报告学习 `EngineBindings.cpp` 150–309 行。

## 二、`witnessCanRead`：五层可读性检查

```cpp
if (!address || !VirtualQuery(address, &info, sizeof(info))) return false;
if (info.State != MEM_COMMIT) return false;

constexpr DWORD Readable = PAGE_READONLY | PAGE_READWRITE | PAGE_WRITECOPY |
                           PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE |
                           PAGE_EXECUTE_WRITECOPY;
if (!(info.Protect & Readable) || (info.Protect & (PAGE_GUARD | PAGE_NOACCESS)))
    return false;

const auto end = (uintptr_t)info.BaseAddress + info.RegionSize;
const auto want = (uintptr_t)address + length;
return want <= end;
```

**五个维度**（与 `ClientCommandTrace` 的 `readable()` 相同）加一个**显式的"必须有可读位"**：

- 非空；
- `VirtualQuery` 成功；
- 已提交；
- **至少有一种可读保护位**；
- 没有 GUARD/NOACCESS；
- 不跨区域。

**第四条是这里特有的** —— 只检查"没有 NOACCESS"是不够的，`PAGE_EXECUTE`（无读）也是不可读的。

## 三、`armVectoredFaultWitnessImpl`：两处武装

```cpp
// ARMED FROM TWO PLACES NOW. The dedicated arms it around native animation
// init; the CLIENT arms it at startup, because the crash worth catching
// (HANDOFF section 152w) happens in the client and a CODOL client that
// crashes exits tidily with no dump -- the handler is the only thing that
// runs before its own TopLevelExceptionFilter swallows the context.
```

**关键洞察**：

> **一个崩溃的 CODOL 客户端【干净地退出，没有 dump】** —— **这个 handler 是在它自己的 `TopLevelExceptionFilter` 吞掉上下文之前唯一跑得起来的东西。**

即：**必须抢在客户端自己的崩溃报告器之前**。`AddVectoredExceptionHandler(1, ...)` 的 `1`（first-chance）正是为此。

而日志里第一行就报"是否武装成功"：

```text
"native fault witness armed=%u module=0x%08X"
```

`armed=0` 会直接暴露注册失败。

## 四、六种"值得记一行"的异常码

```cpp
EXCEPTION_ACCESS_VIOLATION      (0xC0000005)
EXCEPTION_STACK_OVERFLOW        (0xC00000FD)
EXCEPTION_ILLEGAL_INSTRUCTION   (0xC000001D)
EXCEPTION_PRIV_INSTRUCTION      (0xC0000096)
EXCEPTION_IN_PAGE_ERROR         (0xC0000006)
EXCEPTION_INT_DIVIDE_BY_ZERO    (0xC0000094)
```

**六种**，覆盖：

- 内存访问（两种：AV 与 in-page）；
- 栈溢出（递归或深调用）；
- 非法/特权指令（跳到数据上）；
- 整数除零。

**没有 `EXCEPTION_BREAKPOINT`** —— 因为断点是正常的调试事件，记日志会淹没。

## 五、封顶 10 条

```cpp
if (!interesting || VectoredWitnessCount.fetch_add(1) >= 10)
    return EXCEPTION_CONTINUE_SEARCH;
```

注释：

> **十足够看一个模式，又少到循环内部的一次 fault 不会埋掉日志的其余部分。**

注意 `fetch_add` 在**过滤之后**：不感兴趣的码不消耗计数。

## 六、日志行：八个字段

```text
"native fault witness code=0x%08lX rva=0x%07X op=%u target=0x%08X thread=%lu stage=%s"
```

1. **code** —— 异常码；
2. **rva** —— `address - base`（`module` 为空或 `address < base` 时给绝对地址）；
3. **op** —— 0 读 / 1 写 / 8 执行，`NumberParameters < 2` 时是 `0xFFFFFFFF`；
4. **target** —— 被访问的地址；
5. **thread** —— 线程 id；
6. **stage** —— `SV_CurrentNativeStage()`。

### 6.1 那段关于 stage 的注释

> **一个 RVA 说引擎死在哪里；它不说 ol-mod 的哪一次调用把它放到那里**，**而 clientThink 里的每一个 stage 都到达同一段共享 BG 代码**。
>
> **这个面包屑每次原生调用只花一次原子存储，而它把 `0xC0000005 at 0x411310` 变成一个有名有姓的嫌疑人。**

**"有名有姓的嫌疑人"** —— 这是 $`NativeStageScope` 存在的全部价值。

### 6.2 `rva` 用 `%07X`

**七位十六进制** —— 因为镜像 `SizeOfImage` 是 `0x0E659000`（约 0xE66000），七位足够。

## 七、寄存器行：为什么必须

```cpp
// THE RVA SAYS WHERE; THE REGISTERS SAY WHY.
```

具体案例：

> `zhunt` 加载崩溃（HANDOFF §152w）死在 **`sub_59CC70+0x1A5`** 写 **`[edi+3ECh]`**，**而 `edi` 是 `sub_53F5F0` 的返回值 —— 当记录的 `+0xF8` 类型标签既不是 1 也不是 2 时它是 0**。
>
> **没有 `edi` 和 `ebx` 在手那只是一个假说；有了它们就是一个读数。**

八个寄存器一行：

```text
eax ebx ecx edx esi edi ebp esp
```

### 7.1 为什么不钩那两个函数

> 钩 `sub_53F5F0` 或 `sub_59CC70` 会回答同一个问题，**而它不是一个选项：两者都是每帧的，而一个每帧的客户端钩子一次崩掉了三个客户端。一个 vectored handler 在 fault 真的发生之前不花任何成本。**

## 八、读 `ebx` 指向的记录

```cpp
__try {
    const auto *record = (const uint8_t*)context->Ebx;
    entityIndex = *(const uint32_t*)(record + 0x194);
    weaponIndex = *(const uint16_t*)(record + 0x1CC);
    recordRead = true;
} __except (EXCEPTION_EXECUTE_HANDLER) { recordRead = false; }
```

注释：

> **读 `ebx` 指向的记录，加守卫 —— 一个在报告 fault 时自己 fault 的 handler 什么都没告诉任何人。**

**`recordRead` 布尔让"读不出"与"读到零"可区分**。

两个偏移：

```text
+0x194  sub_53F5F0 键控的实体索引
+0x1CC  武器索引（u16）
```

## 九、栈扫描而不是 EBP 链

这是本组最精彩的一段推理。

### 9.1 问题

```text
0x4888CC 说 DB 的 load pump fault 了；它没说【哪一个调用】到达那里。
```

### 9.2 为什么 EBP 链不行

> **EBP 链在这里是错误的工具，而它最先被尝试过**：pump 是 **FPO** —— `sub_4888B0` 开头是 `push ecx; push esi`，**完全没有 `mov ebp, esp`** ——
>
> **所以 fault 时刻的 EBP 属于最后跑过的那个有帧指针的函数，而走它会产出三个看起来合理的地址，而那三个都不在路径上。**

**"三个看起来合理但都不是的地址"** —— 这是最坏的一类假信息。

### 9.3 改用原始栈扫描

> **所以改扫原始栈。** 接下来一千字节里每一个**指向 `.text`** 且**前面紧跟一条 `call`** 的 dword 都是一个返回地址，**或者一个非常好的仿制品**；`E8` / `FF15` / `FF` 的五六字节形式覆盖了 MSVC 生成的几乎每一次调用。

### 9.4 它的诚实标注

> **这会过度报告**——陈旧的槽位在 ESP 之下存活——**所以它被标注为一次 SCAN 而不是一个栈，而顺序是地址顺序，不是调用顺序。**

**三个自我限制**：

1. "SCAN" 不叫 "stack"；
2. **地址顺序 ≠ 调用顺序**；
3. 会过度报告。

## 十、关键结论

1. **必须抢在客户端自己的 `TopLevelExceptionFilter` 之前**，因为崩溃的客户端**干净退出且无 dump**。
2. **可读性检查要显式要求"有可读位"**，不只是"没有 NOACCESS"。
3. **RVA 说在哪，寄存器说为什么** —— 两者都需要。
4. **FPO 函数让 EBP 链产出"看起来合理但都不对"的地址**，这是最坏的一类假信息。
5. **栈扫描要自我标注为 SCAN**，并说明"地址顺序不是调用顺序"。
6. **在报告 fault 时不能再 fault** —— 记录读取必须加守卫。

## 十一、未闭合点

- 栈扫描的完整实现（309 行之后）未读取。
- `EngineBindings.cpp` 剩余约 916 KB 未读取。
