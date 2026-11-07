# 162 · 帧钩子实现与断开见证

## 一、范围

本报告学习 **2 处实现**：

- `FrameHook.cpp`（74 行，完整）
- `DisconnectWitness.cpp` 前 80 行

## 二、`Com_Frame` 钩子：五字节跳板的完整构造

### 2.1 两段式：trampoline + naked 钩子

```cpp
constexpr std::size_t HookSize = 5;
void *OriginalComFrame{};
FrameCallback Callback{};

__declspec(naked) void comFrameHook() {
    call dword ptr [OriginalComFrame]
    pushfd
    pushad
    call runServerFrame
    popad
    popfd
    ret
}
```

顺序值得注意：**先调原始函数**（保留 5 字节被偷走的指令的语义），**再保存标志与寄存器**，然后调回调，恢复后 `ret`。

`pushfd`/`pushad` 包住回调，所以回调里改寄存器不影响调用者的状态。`runServerFrame` 是 `__cdecl`，用 `GetTickCount()` 而不是自建时钟。

### 2.2 trampoline 构造

```cpp
trampoline = VirtualAlloc(nullptr, HookSize + 5, MEM_COMMIT|MEM_RESERVE, PAGE_EXECUTE_READWRITE);
copy_n(target, HookSize, trampoline);          // 偷来的 5 字节
trampoline[5] = 0xE9;                          // jmp
*(int32*)(trampoline+6) = (target+5) - (trampoline+10);   // 跳回原函数 +5
```

总计 **10 字节**：`HookSize + 5`（1 字节 opcode + 4 字节 rel32）。

### 2.3 安装

```cpp
VirtualProtect(target, 5, PAGE_EXECUTE_READWRITE, &old);   // 失败 → 释放 trampoline，返回 false
OriginalComFrame = trampoline;
Callback = callback;
target[0] = 0xE9;
*(int32*)(target+1) = &comFrameHook - (target+5);
FlushInstructionCache(...);                                // 关键：改代码后必须刷
VirtualProtect(target, 5, old, &old);                      // 恢复原保护
```

`FlushInstructionCache` 在多核上是必须的——不刷的话其他核心可能还跑旧的解码结果。

### 2.4 幂等

```cpp
if (!bindings.valid() || !callback || OriginalComFrame) return false;
```

`OriginalComFrame` 非空即已安装，二次调用直接返回 false。

## 三、断开见证：为什么钩**写入点**而不是函数入口

### 3.1 症状

> 在 `mp_battlecity` 上客户端现在能到达 `cls.state 10 (ACTIVE)`、确认可靠命令、发送按键输入——**然后大约一秒后把 `cls.state` 归零**。不是 `Com_Error`（`com_errorMessage` 保持为空），不是崩溃（没有 ClientException），**服务端发的任何东西都解释不了它**。**六个服务端理论都死在这一秒上。**

### 3.2 扫描结果

> 扫描 `.text` 找每一处对 `cls.state`（`0x076446B0`）的写入，**正好找到五处，只有一处存 0**：`0x0077C343` 的 `mov dword ptr [0x076446B0], 0`，在 `sub_77C290` 内。**它的三个调用者扇出到 97 个调用点**，读代码太窄不了，**所以调用者的返回地址就是答案，而钩子是读它的唯一办法。**

### 3.3 为什么不能钩函数入口——两个都是实测的

> **1.** 钩 `sub_77C290` 的入口曾经装好过（日志 "disconnect witness installed" 21:09:50），**而客户端在 21:12:08 仍然把 `cls.state` 从 10 变成 0，钩子没有触发**。**到达那个写入的东西不经过函数序言。**
>
> **2.** 那个序言是 `55 8B EC 83 E4 F8`——`push ebp / mov ebp,esp / AND ESP,-8`。**五字节窃取会把 `and esp,-8` 切成两半**，所以 trampoline 会执行一条被截断的指令。**即使它触发了也是错的。**

### 3.4 写入指令是 10 字节

```text
C7 05 B0 46 64 07 00 00 00 00   mov dword ptr [0x076446B0], 0
```

> 十字节，所以**五字节跳 + 五字节 NOP** 绰绰有余，不会切到任何东西。

注释还记录了一次自己工具的输出错误：

> （我早先的扫描打印 `0x0077C345`，因为它报告的是**地址操作数**所在位置，不是指令起始位置。）

### 3.5 顺带钩 `Com_Error`

> `com_errorMessage` 每次客户端退出时都是空的，这被当成"`Com_Error` 从未运行"的证据。**它只证明消息是空的**——一次用空字符串或未解析字符串抛出的 `Com_Error` 从外面看完全一样，**而那也能解释整晚看到的空白对话框正文。**

站点：

```text
Com_Error is sub_4F8350，开头是 E8 7B F9 FF FF  —— 一个五字节相对 call 到 sub_4F7CD0
```

**五字节是干净的窃取，但相对 call 不能简单复制到另一个地址的 trampoline：它的目标被编码成 delta。**安装器必须重写那个 delta。

`ExpectedComError[5] = { 0xE8, 0x7B, 0xF9, 0xFF, 0xFF }` —— 原字节被当作**校验值**保存，与 `ExpectedWrite[10]` 一样。

### 3.6 只报告一次

```cpp
if (InterlockedExchange(&ComErrorReported, 1) != 0) return;
```

用 `InterlockedExchange` 做一次性的原子开关——比 `bool` + 检查更安全，因为钩子可能在多线程上被并发进入。

### 3.7 报告内容

```text
"COM_ERROR raised, called from 0x%08X (module+0x%X) -- resolve with Tools/olfinal/xrefs.py --callers"
```

**给出返回地址与 RVA 两个形式**，并**直接指名解析工具**。这是"日志应当自带下一步"的范例。

### 3.8 默认关闭

> **除非 `OLMOD_DISCONNECT_WITNESS=1` 否则关闭。**它给客户端自己的代码打补丁；**不是可以默认装备的东西。**

## 四、对比三种钩子的共同纪律

| 项目 | 站点 | 窃取大小 | 特殊处理 |
|---|---|---:|---|
| Com_Frame | 函数入口 | 5 | trampoline + naked 汇编 |
| animtree | 一处 call | 5 | 透明转发返回原值 |
| 渲染帧 | 一处 call | 5 | **尾跳**，与调用约定无关 |
| Com_Error | 函数开头相对 call | 5 | **重写 rel32 delta** |
| cls.state 写入 | 一条 10 字节 mov | 10 | 5 跳 + 5 NOP |

四条共同纪律：

1. **原字节先校验**（`Expected*` 数组），不符就拒绝而不是打补丁；
2. **`VirtualProtect` 保护旧值并恢复**；
3. **`FlushInstructionCache`**；
4. **失败路径释放已分配资源**（`VirtualFree(trampoline, ...)`）。

`FrameHook.cpp` 是这批里**唯一没有原字节校验**的——它直接检查 `bindings.valid()` 就从 `ComFrameRva` 取址。这是一个可指出的不一致：其他四处都有 `ExpectedBytes` 常量，这里没有。

## 五、关键结论

1. **五字节窃取会切碎指令**：`55 8B EC 83 E4 F8` 这种序言被切五字节后，trampoline 会跑半条 `and esp,-8`。**选择站点要先看指令长度。**
2. **相对 call 不能原样复制**，必须重写 delta。
3. **钩入口不一定能抓到**：`sub_77C290` 入口装了钩子但写入仍然发生且不经过它。**症状指向函数，证据指向更低的层。**
4. **`com_errorMessage` 为空 ≠ 没调 `Com_Error`**——空字符串与未解析字符串从外面看一样。
5. **扫描工具报的是操作数位置不是指令位置**，这个错误曾导致选错站点。
6. **日志要自带下一步**（返回地址 + RVA + 解析工具名）。

## 六、未闭合点

- `FrameHook.cpp` 缺原字节校验（与其余四处不一致）。
- `cls.state` 归零的真正调用者仍未点名（见证器默认关闭，需实测）。
- `DisconnectWitness.cpp` 80 行之后的安装逻辑未在本组。
