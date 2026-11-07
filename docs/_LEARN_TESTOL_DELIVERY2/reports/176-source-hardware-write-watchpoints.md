# 176 · 硬件写断点：两个软件钩子都空手而归之后

## 一、范围

本报告学习 `DisconnectWitness.cpp` 199–399 行。

## 二、那次"值变了但没有指令碰它"

### 2.1 三个实测事实

```text
2026-09-04 实测：
  镜像里唯一的 `mov dword [cls.state], 0` 上的钩子 —— 已武装，从未触发
  Com_Error 上的钩子 —— 已武装，从未触发
  没有 ClientException，没有比赛结束
  而 cls.state 仍然在客户端进入约一秒后从 10 变成 0
```

### 2.2 结论与推理

> **一个值在没有任何指令触碰它地址的情况下改变，是一个被当作更大操作的一部分被抹掉的值：一次覆盖整个 `cls` 结构的 `memset`，而它不引用任何扫描能发现的地址。**

这是本组最重要的一条推理：**"找不到写入者"本身就是证据**——它把嫌疑从"某条 mov"推向"某个块操作"。

### 2.3 为什么硬件断点能抓到

> **CPU 不在乎写是怎么发生的。**`DR0` + `DR7` 让它在**地址**上陷入，所以 `memset` 里的一条 `rep stosd` 会被抓得和一条 `mov` 完全一样。
>
> **异常地址是写入【之后】的那条指令**，那足以点名函数。

### 2.4 为什么要在每个线程上装

> **调试寄存器是每线程的**，而**没有任何保证那次抹除发生在安装它的那个线程上**。

## 三、地址算错的那个教训

```cpp
constexpr DWORD_PTR ClsStateAbsolute = 0x076446B0;
constexpr DWORD_PTR AssumedImageBase = 0x00400000;
target = (DWORD_PTR)module + (ClsStateAbsolute - AssumedImageBase);
```

注释：

> `cls.state` 是相对 `0x400000` 镜像基址的 `0x076446B0` 绝对值，所以从模块算是 `0x072446B0`。**从常量推导而不是再手写一个字面量**：第一次尝试手写了 `0x036446B0`，**在完全错误的地址上武装**，并如实地抓到了一个无关的写（日志里的 `0x03A446B0`）。

这是"二次常量 = 定时炸弹"的又一个实例，而且这次它**产生了看似成功的错误结果**（确实抓到了一次写，只是错的写）。

## 四、第二个断点：`com_errorCode`

```cpp
context.Dr1 = (DWORD_PTR)module + (0x033E7904 - AssumedImageBase);
```

理由：

> **镜像里只有一条指令写它**（`sub_4F7DA0+0x21E`，`= ecx`），**而那是丢弃处理器在存它已经拿到的码**——所以**把它设成 2 的那个人是通过指针做的，正如 `cls.state` 是通过指针被抹掉的一样**。**同一个硬件陷阱回答同一种形状的问题。**

### 4.1 DR7 的双槽装配

```cpp
context.Dr7 = (context.Dr7 & ~static_cast<DWORD_PTR>(0xFF000F)) |
    0x1 | 0x4 |                      // L0 与 L2 本地启用
    (0x1 << 16) | (0x3 << 18) |      // DR0: 只写，4 字节
    (0x1 << 20) | (0x3 << 22);       // DR1: 只写，4 字节
```

**注意掩码是 `~0xFF000F`** 而不是 `~0xF`：

```text
0xFF000F = 0x0000000F  （L0..L3 本地启用位）
         | 0x00FF0000  （R/W0-3 与 LEN0-3，位 16..31 的低半）
```

即**一次清掉"启用位 + DR0/DR1 的 R/W/LEN 字段"**（位 16..23），保留 DR2/DR3 的字段（位 24..31）不动。

与 `armWriteWatch` 里的 `~0xF` **不同** —— 那里只用一个槽（DR0），所以只需清启用位；这里两个槽，要清对应的 RW/LEN 字段。

装配后：

```text
bit 0   L0  → DR0 启用
bit 2   L2  → DR1 启用（注意是 L2 不是 L1，因为 DR1 的本地启用位是 bit 2）
bit 16-19  DR0: R/W=01, LEN=11
bit 20-23  DR1: R/W=01, LEN=11
```

**`0x4` 是 `L1` 位**——x86 的映射是 `L0=bit0, L1=bit1, L2=bit2, L3=bit3`，而 **DR1 对应 G1/L1 = bit 1（全局）/ bit 2？**

实际上 x86 的 DR7 布局是：

```text
L0 G0 L1 G1 L2 G2 L3 G3   （bits 0..7，每个 2 bit：L 在偶位，G 在奇位）
```

所以 **`L0 = bit 0`、`L1 = bit 2`**（因为 `G0 = bit 1`）。所以 `0x1 = L0`、`0x4 = L1` ✓。

代码注释写的 "bits 0 and 2" 是对的。

## 五、`watchpointHandler`

### 5.1 只认自己的 DR6 位

```cpp
if (ExceptionCode != EXCEPTION_SINGLE_STEP) return CONTINUE_SEARCH;
which = Dr6 & 0x3;                       // bit0 = DR0, bit1 = DR1
if (which == 0) return CONTINUE_SEARCH;  // 真正的单步，不关我们的事
isErrorCode = (which & 0x2) != 0;
Dr6 = 0;
```

**`which == 0` 时继续搜索** —— 这是"别的单步"（比如调试器的 trap flag），不能吞。

### 5.2 不是一次性的——那条最贵的教训

```text
NOT ONE-SHOT. The first attempt logged once and spent itself on a routine write
at 23:01:29 -- ninety seconds BEFORE the client entered the match at 23:02:57 --
so the transition that matters was never seen. cls.state is written on every
rung of the connect ladder; the interesting one is late and writes 0.
```

**只报一次会花在无关的写上面**。因为 `cls.state` 在连接阶梯的每一级都被写。

### 5.3 打印**写入后的值**

```text
Capped so a loop cannot bury the log, and the NEW VALUE is printed:
a debug write breakpoint traps AFTER the store, so the value at the address
is what was just written. `= 0` after the client has entered is the one to read.
```

`InterlockedIncrement(&reported) <= 24` —— 封顶 24 条。

**这是"硬件写断点在存之后陷入"这条事实的直接应用**：读地址得到的就是刚写进去的值。

### 5.4 日志同时给三个定位

```text
"%s = %u WRITTEN by the instruction before 0x%08X (module+0x%X)
 -- resolve with Tools/olfinal/xrefs.py; caller frame [ebp+4]=0x%08X"
```

四段信息：

1. **哪个变量 + 写入了什么值**；
2. **陷入地址**（= 写入之后的那条）与**其 RVA**；
3. **解析工具名**；
4. **`[ebp+4]` 的调用者返回地址**（如果 `ebp` 有效）。

第 4 条是额外保险：即使 `ExceptionAddress` 落在 `memset` 内部（`rep stosd` 循环里），`[ebp+4]` 仍能指出**谁调了 memset**。

## 六、`clDisconnectHook` 用 `[ebp+4]` 而不是 `[esp+36]`

```asm
pushfd
pushad
// The caller lives at [ebp+4]: this site is inside sub_77C290, whose prologue
// established the frame, so ebp+4 is the return address into whoever asked for the disconnect.
mov eax, [ebp + 4]
push eax
call recordDisconnect
```

**这是第三种取返回地址的方式**：

| thunk 类型 | 取法 |
|---|---|
| 入口钩子（未建帧） | `[esp+36]` |
| 函数体内部（已建帧） | `[ebp+4]` |

`sub_77C290` 的序言是 `push ebp / mov ebp,esp`，所以**钩子在帧建立之后**，`[ebp+4]` 是它的调用者返回地址。

### 6.1 尾跳而不是 call

```asm
// Into the trampoline: it performs the real cls.state write, then jumps
// back past the whole ten-byte instruction. A JMP, not a CALL.
jmp dword ptr [Trampoline]
```

trampoline 执行被偷的 10 字节（`mov [0x076446B0], 0`）+ `jmp` 回到 `target+10`。

## 七、安装顺序：先建 trampoline 再写跳转

```cpp
// BUILD THE TRAMPOLINE BEFORE WRITING THE JUMP, or it relocates its own jump.
```

**这是顺序上的关键**：如果先写 `target` 的 `E9`，然后才发现要复制 `target` 的前 10 字节，**复制到的就是自己刚写的跳转**。

同一条纪律在 `ClientCommandTrace` 里以另一种形式出现（"二次打补丁会把 JMP 当作原始序言"）。

### 7.1 为什么这条指令可以安全复制

> **被偷的字节是一条绝对的 `mov [imm32], imm32` —— 位置无关**，所以复制它是安全的。

对照：`Com_Error` 的 `E8 rel32` **不能**直接复制，必须重写 delta（之前报告里已记）。

**即：窃取指令是否可复制，取决于它是否位置相关。**

## 八、关键结论

1. **"值变了但没指令碰它"指向块操作**（`memset`），而这正是静态扫描抓不到的。
2. **硬件写断点挂在地址上**，`rep stosd` 与 `mov` 一视同仁。
3. **第二次写地址必须从常量推导**，手写 `0x036446B0` 曾"成功地抓到了错误的写"。
4. **写断点不是一次性的**：`cls.state` 每级连接阶梯都写，只报一次会花在无关的写上面。
5. **写断点在存之后陷入**，所以读地址得到的就是刚写的值。
6. **返回地址的两种取法**：未建帧用 `[esp+36]`，已建帧用 `[ebp+4]`。
7. **先建 trampoline 再写跳转**，否则会复制到自己的跳转。
8. **位置无关指令才能直接复制**；`E8 rel32` 必须重算。

## 九、未闭合点

- `cls.state` 10 → 0 的真正来源仍未点名（钩子与断点都已就位，结果不在本组）。
- `DisconnectWitness.cpp` 399 行之后的安装收尾未读取。
