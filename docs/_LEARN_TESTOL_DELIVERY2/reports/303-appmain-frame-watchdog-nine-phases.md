# 303 · **"一个线程的挂起无法自己报告"** —— 帧看门狗的九个阶段、栈扫描代替 EBP 走链

## 一、范围

本报告学习 `Appmain.cpp` 7200–7420 行。

## 二、`brushmodel census` 与**总账日志**

### 2.1 census 的**九个字段**

```php
"brushmodel census [" + i + "] clip=*" + clipHandle +
" contents=0x" + %08X +
" origin=" + x,y,z +
" targetname=" + (空 ? "-" : name) +
" gameobject=" + (空 ? "-" : name) +
" destructible=" + (空 ? "-" : name) +
" mpEligible=" + (0|1) +
" active=" + (0|1)
```

**⇒ 九个（含 `clip=*<N>`）。**

### 2.2 而 `clip=*<N>` 的**格式**与 §302 的 `* N` 一致

**⇒ 所以 census 直接打印"这个 brush model 在配置串里会写成 `* N`"。**

**✓ 与 §302 的"`clipHandle` 就是那个 N"配合。**

### 2.3 而 `contents=0x%08X` 用 **snprintf 到一个 16 字节缓冲**

```cpp
" contents=0x" + [&] {
    char buffer[16]{};
    std::snprintf(buffer, sizeof(buffer), "%08X", b.collision.contents);
    return std::string(buffer);
}() +
```

**⇒ 一个立即执行的 lambda 做十六进制格式化。**

**⚠ 而文件里别处有 `hex` lambda（§251/§261）⇒ 又一处重复。**

## 三、`world spawn configured` 的**十三个量**

```php
"world spawn configured map=" + mapName +
" preparationMs=" + (now - preparationStart) +
" cachedLookups=" + (lookupRequests - lookupMisses) + "/" + lookupRequests +
" spawnPoints=" + worldSpawnPoints.size() +
" brushModels=" + brushModels.size() +
" conservativeActiveBrushModels=" + activeBrushModels +
" scriptModels=" + scriptModels.size() +
" scriptModelsOnRetailNumbers=" + Server.constBaselineScriptModelCount() +
" conservativeActiveScriptModels=" + activeScriptModels +
" destructibleDamageOwners=" + scriptModelDamageOwners.size() +
" glassPieces=" + glassMetadata->initialPieces.size() +
" glassThresholds=" + glassThresholds->weaken + "/" + glassThresholds->destroy
```

### 3.1 十二个字段（十三个值）

```text
preparationMs                     总准备时间
cachedLookups / lookupRequests    【命中 / 总】
spawnPoints
brushModels / conservativeActiveBrushModels
scriptModels / scriptModelsOnRetailNumbers / conservativeActiveScriptModels
destructibleDamageOwners
glassPieces
glassThresholds（weaken/destroy）
```

### 3.2 **`cachedLookups = lookupRequests - lookupMisses`**

**⇒ 所以"命中数"是**推导的**。**

**⇒ 而 §294 说 `lookupMisses` 统计的是"缓存未命中"。**

**⇒ 所以 `cachedLookups` = 总请求 - 缓存未命中 = **缓存命中数**。**

**✓ 语义正确，但**名字 `lookupMisses` 仍然误导**（已在 §294 指出）。**

### 3.3 而 **`conservativeActive*`** 的"保守"含义

**⇒ 与 §299 的"`gameplayActive` 用两个条件"配合 —— 所以"保守"= 只在两个条件都满足时才算 active。**

### 3.4 而 `scriptModelsOnRetailNumbers`

**⇒ 与 §294 的"`<map>_const.ff` 的实体编号"**直接相关**。**

**⇒ 所以这个数给出"有多少 script model 落在零售编号上"。**

**✓ 一个直接的**质量指标**。**

## 四、`PendingWorldAsset` 的**清除**

```cpp
const std::lock_guard lock(WorldAssetMutex);
if (PendingWorldAsset &&
    PendingWorldAsset->mapName == request->mapName &&
    PendingWorldAsset->gameType == request->gameType)
{
    PendingWorldAsset.reset();
}
```

**⇒ 三个条件**（存在 + mapName 匹配 + gameType 匹配）。

**⇒ 所以"只有同一个请求才清除"。**

**✓ 与 §294 的 `reportFailure` 的匹配检查同族。**

## 五、**"一个线程的挂起无法自己报告"**（本组最重要的一段）

### 5.1 那段完整论证

```php
// A HANG ON ONE THREAD CANNOT REPORT ITSELF. The dedicated's frame thread stops a few
// seconds after the gamestate is configured (sec 36d): the process stays alive, the control
// thread keeps answering and keeps writing to this same log, and the frame thread simply
// stops. Nothing it could print would ever come out, because it is the thread that is stuck.
//
// So the report has to come from somewhere else. The frame thread only STORES a phase, which
// costs an atomic write per stage, and a watchdog on its own thread notices when the tick
// counter stops moving and prints the phase it stopped in. That turns "the log went quiet"
// into "it went quiet in <phase>", which is the whole question.
//
// Deliberately one-shot per stall: a watchdog that repeats every interval buries the log it
// is trying to make readable.
```

### 5.2 六层

```text
1. **一个线程的挂起无法自己报告**
2. 专用服的帧线程在 gamestate 配置后几秒**停止**（§36d）
3. 进程活着、控制线程继续应答并继续写同一个日志，而**帧线程就是停了**
4. ⇒ 它能打印的任何东西**都不会出来**，因为**它就是那个卡住的线程**
5. ⇒ 所以报告必须来自**别处**：帧线程只**存**一个阶段（每阶段一个原子写）
6. ⇒ 而一个**看门狗在自己的线程上**注意到 tick 计数器停止移动并打印它停在哪一阶段
7. ⇒ 这把"日志变静了"变成"**它在 <phase> 里变静了**"
```

### 5.3 而"**一次每次停*** 是刻意的

```text
// Deliberately one-shot per stall: a watchdog that repeats every interval
// buries the log it is trying to make readable.
```

**⇒ 三层**：

```text
1. 每个停顿只报**一次**
2. 因为一个每隔一段时间重复的看门狗**埋掉它正要使其可读的日志**
3. ⇒ 一个自我否定的设计
```

**✓ 与 §299 的"分块不截断"、§288 的"75 个全试过"同族**（第八次"诊断不能成为问题"）。

### 5.4 而五个原子量

```cpp
std::uint32_t LastCensusConnectedClients{};
std::atomic<std::uint32_t> FramePhase{};
std::atomic<std::uint64_t> FrameTick{};
std::atomic<bool> FrameWatchdogRunning{};
std::atomic<HANDLE> FrameThreadHandle{};
```

**⇒ 一个普通 `uint32` + 四个原子。**

### 5.5 而 `FrameThreadHandle` 的**关键注释**

```php
// A duplicate of the frame thread, so the watchdog can look at where it is stopped. Opened
// once, from the frame thread itself, because that is the only place that knows which one it
// is.
```

**⇒ 三层**：

```text
1. 一个**帧线程的副本**（句柄）以便看门狗看它停在哪
2. **从帧线程本身打开一次**
3. 因为那是**唯一知道它自己是谁的地方**
```

**⚠ 而 `SuspendThread` 需要一个 `HANDLE` —— 所以必须**复制句柄**。**

**⇒ 用 `DuplicateHandle` 或 `OpenThread`。**

## 六、**九个帧阶段**（本组第二重要）

```cpp
switch (phase)
{
// Each name is the region the frame thread has ENTERED, i.e. the work between this
// mark and the next one. A stall reports the phase it is inside, not the one it finished.
case 0: return "not_started";
case 1: return "entry";
case 2: return "role_and_client_patches";
case 3: return "dedicated_control";
case 4: return "loadout_refresh";
case 5: return "pending_booking_and_worldspawn";
case 6: return "server_frame(Server.onComFrame)";
case 7: return "dobj_probe_script_logs_and_net_send";
case 8: return "status_and_periodic_report";
}
```

### 6.1 九个阶段与它们的工作

```text
0  not_started
1  entry
2  role_and_client_patches          角色与客户端补丁
3  dedicated_control                专用服控制消息
4  loadout_refresh                  loadout 刷新
5  pending_booking_and_worldspawn   待定预定与世界生成
6  server_frame(Server.onComFrame)  【服务端帧】
7  dobj_probe_script_logs_and_net_send  DObj 探针 + 脚本日志 + 网络发送
8  status_and_periodic_report       状态与周期报告
```

### 6.2 而"**每个名字是帧线程已经进入的区域**"

```text
1. 每个名字是帧线程**已经进入**的区域
2. = **这个标记与下一个标记之间的工作**
3. ⇒ **一个停顿报告它所在的阶段，而不是它完成的那个**
```

**⇒ 这是一个**精确的语义** —— 避免了"差一阶段的误读"。**

**✓ 与 §245 的"`stage` 记进度 vs `faultStage` 记故障点"**同族**（第三次该问题的处理）。**

### 6.3 而**第 6 阶段是 `Server.onComFrame`**

**⇒ 所以"专用服帧线程在 gamestate 配置后几秒停止"最可能停在第 6 阶段。**

**⇒ 而 §302 的 `brushmodel` 不发布与 §265 的"没有 SV_Trace"都可能在这里崩。**

## 七、`describeCodeAddress` 的**三项**

```cpp
std::string describeCodeAddress(const void *address)
{
    char buffer[160]{};
    HMODULE module{};
    if (GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
            GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
            (LPCSTR)address, &module) && module)
    {
        char path[MAX_PATH]{};
        if (GetModuleFileNameA(module, path, sizeof(path)))
        {
            const char *name = std::strrchr(path, '\\');
            name = name ? name + 1 : path;
            snprintf(buffer, 160, "%s+0x%X", name, address - module);
            return buffer;
        }
    }
    snprintf(buffer, 160, "0x%08X", address);
    return buffer;
}
```

### 7.1 三层

```text
① 按地址查模块
② 有模块 ⇒ `name+0xRVA`
③ 无模块 ⇒ 裸地址
```

### 7.2 而那段注释

```php
// "module+0xRVA" for a code address, or a bare address when it belongs to no loaded module.
// A module identifies ownership, not the operation: ntdll also contains heap
// and other active runtime code, so resolve the address before calling it a wait.
```

**⇒ 三层**：

```text
1. "模块+0xRVA" 或裸地址
2. **一个模块标识所有权，不是操作**
3. ⇒ **`ntdll` 也包含堆与其它活动运行时代码** ⇒ 所以在称它为"wait"之前**先解析地址**
```

**✓ 一个细致的区分 —— 避免"在 ntdll 里 ⇒ 在等待"的误判。**

### 7.3 而 `GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT`

**⇒ 所以不增加引用计数 ⇒ 不需要 `FreeLibrary`。**

**✓ 正确。**

## 八、**`describeFrameThreadStall` 的五段**（本组第三重要）

### 8.1 那段

```php
// WHERE IS IT PARKED. Suspend for the length of one GetThreadContext, read EIP, then scan the
// top of the stack for values that land in a loaded module -- return addresses, mixed with
// some noise, which is enough to name the caller when EIP itself is a syscall stub. x86 release
// code omits frame pointers often enough that an EBP walk is not dependable; a scan is.
std::string describeFrameThreadStall()
{
    auto *const thread = FrameThreadHandle.load(acquire);
    if (!thread) return "frame thread handle unavailable";
    CONTEXT context{};
    context.ContextFlags = CONTEXT_CONTROL | CONTEXT_INTEGER;
    std::array<std::uintptr_t,1024> stack{};
    SIZE_T bytes{};
    if (SuspendThread(thread) == (DWORD)-1) return "frame thread could not be suspended";
    const auto captured = GetThreadContext(thread, &context);
    if (captured)
        ReadProcessMemory(GetCurrentProcess(), (void*)context.Esp, stack.data(), sizeof(stack), &bytes);
    // No heap allocation, logging or loader lookup while the target is suspended:
    // it may own precisely those locks. Resume before formatting.
    ResumeThread(thread);
    if (!captured) return "frame thread context unavailable";
    std::string result = "eip=" + describeCodeAddress((void*)context.Eip);
    std::size_t found{};
    for (index = 0; index < bytes/sizeof(stack[0]) && found < 32; ++index)
    {
        const auto candidate = stack[index];
        if (candidate < 0x10000) continue;
        MEMORY_BASIC_INFORMATION region{};
        if (!VirtualQuery((void*)candidate, &region, sizeof(region)) || region.State != MEM_COMMIT ||
            !(region.Protect & (PAGE_EXECUTE|PAGE_EXECUTE_READ|PAGE_EXECUTE_READWRITE|PAGE_EXECUTE_WRITECOPY))) continue;
        HMODULE module{};
        if (!GetModuleHandleExA(...FROM_ADDRESS|UNCHANGED_REFCOUNT, (LPCSTR)candidate, &module) || !module) continue;
        result += (found ? " <- " : " stack: ") + describeCodeAddress((void*)candidate);
        ++found;
    }
    return result;
}
```

### 8.2 五段

```text
① 取句柄
② SuspendThread + GetThreadContext + ReadProcessMemory（1024 个 uintptr = 8 KB 栈）
③ **立刻 ResumeThread**
④ 然后格式化 EIP
⑤ 扫栈找 32 个落在可执行区域里的"看起来像返回地址"的值
```

### 8.3 **那句关键的"恢复前不格式化"**

```cpp
// No heap allocation, logging or loader lookup while the target is suspended:
// it may own precisely those locks. Resume before formatting.
```

**⇒ 三层**：

```text
1. **在被挂起时不做堆分配、日志或 loader 查找**
2. 因为它**可能正好拥有那些锁**
3. ⇒ **格式化之前先恢复**
```

**✅ 这是一个**极其正确**的并发论证。**

**⇒ 与 §263 的"不要抢活"、§266 的"不要 suspend 调用线程"同族。**

### 8.4 而"**x86 release 代码常常省略帧指针 ⇒ EBP 走链不可靠 ⇒ 扫描可靠**"

```php
// x86 release code omits frame pointers often enough that an EBP walk is not dependable; a scan is.
```

**⇒ 三层**：

```text
1. x86 release 代码**常常省略帧指针**
2. ⇒ **EBP 走链不可靠**
3. ⇒ **扫描可靠**
```

**✓ 与本文件反复出现的"栈扫描"主题（§192–213）一致。**

**⇒ 第四次"栈扫描优于 EBP 走链"。**

### 8.5 而 `candidate < 0x10000` 的**过滤**

**⇒ 跳过低地址（null 页附近）⇒ 避免 `VirtualQuery` 在无效地址上。**

### 8.6 而**四层检查**

```text
① candidate >= 0x10000
② VirtualQuery 成功
③ State == MEM_COMMIT
④ Protect 含某个执行位
⑤ GetModuleHandleExA 成功且返回模块
```

**⇒ 五项（我数五）。**

**⇒ 而 ⑤ 是**最关键**的 —— 只保留"属于已加载模块的代码地址"。**

### 8.7 而 `found < 32` 的**上限**

**⇒ 最多 32 个返回地址。**

**⇒ 一个调用链通常 < 32 深。**

### 8.8 而 `" <- "` 的连接

**⇒ 所以输出形如：**

```text
eip=ntdll+0x1234 stack: game.dll+0x5678 <- game.dll+0x9ABC <- ...
```

**✓ 一个可读的调用链。**

### 8.9 而 `readProcessValue` 的注释

```cpp
// The stack pointer of a suspended thread is trustworthy, but the range above it is not
// guaranteed mapped for the whole scan. Read through the API that reports failure instead of
// faulting.
```

**⇒ 三层**：

```text
1. 挂起线程的栈指针**可信**
2. 但它上面的范围**不保证整个扫描都映射**
3. ⇒ 用**报告失败的 API**（`ReadProcessMemory`）而不是解引用
```

**✓ 与 §261 的"`readableSpan` 不闭合 TOCTOU"**相关** —— 但这里**线程已挂起**所以无竞态。**

**✅ 所以这里 `ReadProcessMemory` 是安全的（因为目标线程停了）。**

## 九、关键结论

1. **`brushmodel census` 的 `clip=*<N>`** 直接对应 §302 的 `* N` 格式。
2. **`cachedLookups = lookupRequests - lookupMisses`** 语义正确但 `lookupMisses` 名字仍误导。
3. **`conservativeActive*`** 的"保守"= 两条件都满足才算。
4. **`scriptModelsOnRetailNumbers`** 是一个直接的质量指标（与 §294 的 const baseline 配套）。
5. **"一个线程的挂起无法自己报告"** —— 所以看门狗必须在自己线程上。
6. **"把『日志变静了』变成『它在 <phase> 里变静了』"** —— 一个精确的诊断目标。
7. **"一次每次停顿"是刻意的** —— 重复的看门狗会埋掉它正要使其可读的日志。
8. **五个原子量**，其中 `FrameThreadHandle` 必须**从帧线程本身**打开。
9. **九个帧阶段**，而"每个名字是**已进入**的区域 ⇒ 停顿报告它**所在**的阶段"。
10. **第 6 阶段是 `Server.onComFrame`** —— 最可能的停顿点。
11. **`describeCodeAddress` 输出 `module+0xRVA` 或裸地址**。
12. **"一个模块标识所有权，不是操作"** —— 所以 `ntdll` 里不一定是 wait。
13. **"挂起时不做堆分配/日志/loader 查找，因为它可能拥有那些锁"** —— 一个极正确的并发论证。
14. **"x86 release 常省略帧指针 ⇒ EBP 走链不可靠 ⇒ 扫描可靠"** —— 第四次该主题。
15. **五层地址过滤**（`>= 0x10000`、`VirtualQuery`、`MEM_COMMIT`、执行位、模块归属）。
16. **"栈指针可信但上面的范围不保证映射"** —— 所以用 `ReadProcessMemory`。
17. **而线程已挂起 ⇒ 无 TOCTOU** —— 与 §261 的"`readableSpan` 不闭合 TOCTOU"不同。

## 十、未闭合点

- 第 6 阶段的 `Server.onComFrame` 里到底停在哪。
- `FrameThreadHandle` 的具体打开方式（`DuplicateHandle` 或 `OpenThread`）。
- `constBaselineScriptModelCount` 的实现。
- `Appmain.cpp` 7420 行之后未读取。
