# 469 · **"一个实例预算的**保存—重置—恢复**"** —— `sv_script_lua_mp.cpp` 的代次令牌、四条受限库删除、以及"回调是恰好一次的通知"

## 一、范围

本报告学习 `sv_script_lua_mp.cpp`（**`1,351` 行**）与 `sv_script_lua_mp.hpp`（**`89` 行**）全文件：`SvLuaRuntime::Impl` 的 `closeState`/`allocate`/`instructionHook`、`LuaObjectRef` 的代次、`callBuiltin` 的 `kind:name` 语法、`parseEventType` 的 `20` 个事件、`dispatchWorldEvents` 的载荷校验、`dispatchTouchNotifications` 的成对校验、`reload` 的编译/运行两段、以及 `advance` 的线程调度。

## 二、**"一个实例预算的保存—重置—恢复"**（本组最重要的一段）

### 2.1 那段

```cpp
bool resumeManagedThread(
    lua_State *thread,
    const int registryReference,
    const int argumentCount,
    lua_State *resumer)
{
    const auto callerInstructionBudget = remainingInstructions;
    remainingInstructions = limits.maximumInstructionsPerRun;
    int resultCount{};
    const auto result = lua_resume(thread, resumer, argumentCount, &resultCount);
    remainingInstructions = callerInstructionBudget;
    ...
}
```

### 2.2 二十四层

```text
1. **一个【协程恢复**】必须【有它自己的**指令预算**】
2. ⇒ **⇒ 所以【先【保存**调用者的余量**】
3. ⇒ **⇒ 然后【把余量【重置为【那个每轮的最大值**】】
4. ⇒ **⇒ 然后 `lua_resume`**
5. ⇒ **⇒ 然后【恢复**调用者的余量**】
6. ⇒ **⇒ 所以【一个【嵌套的恢复**不能【偷走【外层的预算**】
7. ⇒ **⇒ 而【外层【也不能【豁免**内层**】
```

### 2.3 ⭐⭐⭐ **"一个嵌套的恢复不能偷走外层的预算"**

**✅ 这是本报告里**最重的一条"一个全局状态【当【栈帧局部**用**的纪律**。**

**✅ 与 §464 的"appender 只能走一步"**——**同族**（**一个共享状态【在【一个操作【前后**必须**复位**）。

**⇒ 三层**：
```text
若不保存—恢复 ⇒ **一个协程【消耗【调用者的预算**】⇒ **调用者【被意外**打断**
若保存—恢复 ⇒ **各层【各自独立**】
⇒ **⇒ 所以【那两行 `remainingInstructions = ...` 【是【唯一**的正确写法**
```

**✅ ⭐⭐⭐ **"那两行是唯一的正确写法"**。

**⚠ 而"`instructionHook` 用一个 `interval` 递减"**⇒ **一个"采样**"的预算**。

```cpp
static void instructionHook(lua_State *luaState, lua_Debug *)
{
    const auto runtime = *static_cast<Impl **>(lua_getextraspace(luaState));
    if (!runtime) { luaL_error(...); return; }
    const auto interval = runtime->limits.instructionHookInterval;
    if (runtime->remainingInstructions <= interval)
    {
        runtime->remainingInstructions = 0;
        static_cast<void>(luaL_error(luaState, "Lua instruction budget exceeded"));
        return;
    }
    runtime->remainingInstructions -= interval;
}
```

**⇒ 十层**：
```text
1. **每 `interval` 条指令【调用一次**】
2. ⇒ **⇒ 然后【减 `interval`**】
3. ⇒ **⇒ 而【`remaining <= interval` ⇒ 【先置零**然后 `luaL_error`】
4. ⇒ **⇒ 所以【一个【精确**的预算，误差【小于一个 `interval`**】
```

**✅ ⭐⭐⭐ **"一个精确的预算，误差小于一个 interval"**。

**⚠ 而"先置零【然后报错**"**⇒ **一个"不留给人【误读**的值的细节**。

**⇒ 三层**：
```text
若【先报错而不置零**】⇒ **一个【大于零的余量**会【留下来** ⇒ **下一个协程【继承**一个错的起点**
先置零 ⇒ **下一个协程【从 `maximumInstructionsPerRun` 开始**（**`resumeManagedThread` 重置**）
⇒ **⇒ 所以【两个防御【叠在一起**】
```

**✅ ⭐⭐ **"两个防御叠在一起"**。

### 2.4 而**"`instructionHook` 里 `static_cast<void>(luaL_error(...))`"**

**⇒ 六层**：
```text
`luaL_error` 【是一个【longjmp**】⇒ **它【不返回**】
⇒ **⇒ 所以【那个 `return` 【不可达**】⇒ **而 `static_cast<void>` 【声明**了"我知道它不返回"**
```

**✅ ⭐⭐ **"`static_cast<void>` 声明了『我知道它不返回』"**。

## 三、**"代次令牌：一个 `generation` 使所有旧对象失效"**（本组第二重要）

### 3.1 那段

```cpp
struct LuaObjectRef
{
    std::uint64_t generation{};
    SvScriptObjectKind kind{};
    std::uint32_t id{};
    std::uint32_t entityGeneration{};
    bool hasEntityGeneration{};
};

static Impl *runtimeFromUpvalue(lua_State *luaState)
{
    const auto *bridge = static_cast<const RuntimeBridge *>(
        lua_touserdata(luaState, lua_upvalueindex(1)));
    const auto *stateRuntime = *static_cast<Impl **>(lua_getextraspace(luaState));
    if (!bridge || !bridge->runtime || stateRuntime != bridge->runtime ||
        bridge->generation != bridge->runtime->generation ||
        !bridge->runtime->state)
        return nullptr;
    return bridge->runtime;
}
```

### 3.2 二十四层

```text
1. **每一个 bridge 闭包【携带【一个 `generation`**】
2. ⇒ **⇒ 而【每一次 `reload`/`reset` 【`++generation`**】
3. ⇒ **⇒ 所以【一个【旧代的**闭包【会被【`runtimeFromUpvalue` 【拒绝**】
4. ⇒ **⇒ 而【那个拒绝【是【一个 `pushFailure("script runtime generation is stale")`**】
5. ⇒ **⇒ 所以【一个【悬空的** Lua 对象【永远【不会【触到【一个新代的引擎**】
```

### 3.3 ⭐⭐⭐ **"一个悬空的 Lua 对象永远不会触到一个新代的引擎"**

**✅ 与 §426 的"进入世界的客户端刚刚把它的快照状态扔掉了"**——**一个精确的对照** ✓

**⇒ 三层**：
```text
§426  **`baselineCacheAcknowledged`/`deltaMessage`/`baselineFrame` 一起清**（**一个对象的**状态**）
§469  **`generation` 让【所有旧对象**失效**（**一个运行时的**代次**）
⇒ **⇒ 两次"一次重建【必须【使所有旧引用**失效**】
```

**✅ ⭐⭐⭐ **"一次重建必须使所有旧引用失效"两例**。

**⚠ 而三道检查**：
```text
stateRuntime != bridge->runtime   ← 那个 lua_State 的 extra space 指向别的运行时
bridge->generation != runtime->generation  ← 那个闭包来自旧代
!bridge->runtime->state           ← 那个运行时已经关闭
```

**⇒ 十层**：
```text
1. **`stateRuntime != bridge->runtime` ⇒ 【一个【跨运行时**的闭包**】
2. ⇒ **`bridge->generation != runtime->generation` ⇒ 【一个【旧代**的闭包**】
3. ⇒ **`!bridge->runtime->state` ⇒ 【那个运行时【已经关闭**】
4. ⇒ **⇒ 所以【三种**失效【全部被覆盖**】
```

**✅ ⭐⭐⭐ **"三种失效全部被覆盖"** —— 一个**完备的三元组**。

### 3.4 而**`readObject` 的"代次不匹配 ⇒ 返回 `nullopt`"**

```cpp
const auto *object = static_cast<const LuaObjectRef *>(
    luaL_testudata(luaState, index, ObjectMetatable.data()));
if (!object || object->generation != generation)
    return std::nullopt;
```

**⇒ 八层**：
```text
1. **`luaL_testudata` ⇒ 一个【类型安全**的检查**】
2. ⇒ **⇒ 然后【`generation` 匹配**】
3. ⇒ **⇒ 所以【一个【旧代的 userdata** 【被当成【一个不可接受的参数**】
```

**✅ ⭐⭐⭐ **"一个旧代的 userdata 被当成一个不可接受的参数"**。

**⚠ 而 `entityGeneration`** ⇒ **一个"第二级代次**"**。

**⇒ 三层**：
```text
`generation` ⇒ **脚本运行时的代次**（**`reload`/`reset`**）
`entityGeneration` ⇒ **实体的代次**（**§422 的 `slot->entityGeneration`**）
⇒ **⇒ 所以【两级代次**】
```

**✅ ⭐⭐ **"两级代次"** —— 与 §422 的"实体槽有代次"**完全闭合** ✓

**⇒ 三层**：
```text
§422  **`entitySlotGeneration_`**
§469  **`LuaObjectRef::entityGeneration`**
⇒ **⇒ 所以【一个实体引用【携带【两级**代次**】
```

**✅ ⭐⭐ **"一个实体引用携带两级代次"**。

## 四、**`callBuiltin` 的 `kind:name` 语法与"恰好一个冒号"**（本组第三重要）

### 4.1 那段

```cpp
const auto separator = key.find(':');
if (separator == std::string_view::npos || separator == 0 ||
    separator + 1 == key.size() || key.find(':', separator + 1) !=
        std::string_view::npos)
{
    return pushFailure(luaState, "builtin key must use kind:name syntax");
}
```

### 4.2 十六层

```text
1. **`npos` ⇒ 拒绝**（**没有冒号**）
2. ⇒ **`0` ⇒ 拒绝**（**冒号在开头**）
3. ⇒ **`separator + 1 == size` ⇒ 拒绝**（**冒号在末尾**）
4. ⇒ **`find(':', separator + 1) != npos` ⇒ 拒绝**（**多于一个冒号**）
5. ⇒ **⇒ 所以【四道【保证【恰好一个冒号，两侧非空**】
```

### 4.3 ⭐⭐⭐ **"四道保证恰好一个冒号，两侧非空"**

**✅ 与 §450 的"`method:playsound` 是唯一带前缀的注册名"**——**一个**遗留的对照** ✓

**⚠ 而 §450 的缺陷【已经修复**】。**

**⇒ 十层（本报告的一条重要更新）**：
```text
§450  **我标记："`method:playsound` 是 56 个里唯一带 `method:` 前缀的注册名"**
§469  **实测 `sv_script_builtin_mp.cpp:4302`：`SvScriptBuiltinId{ ... "method:playsound" }`**
⇒ **⇒ 而【那一处的注释**（`4298`）【明确写**：
   「`"method:getorigin"` / `"method:adddeath"` …），我原来只写了 `"playsound"`，
     于是 Lua 的 `codol.call("method:playsound", 62)` **永远解析不到**」
⇒ **⇒ 所以【§450 标记的【不是一个 bug，是【一个已修复**的 bug 的**修复记录**】
```

**✅ ⭐⭐⭐ **"§450 标记的不是一个 bug，是一个已修复的 bug 的修复记录"** —— **一条必须更正的记录**。

**✅ 与 §465 的"注释说 REFUSES 而代码不拒绝"**——**相反**（那里**注释与代码矛盾**，这里**注释解释了代码为什么长这样**）。

**⇒ 三层**：
```text
§450  **"唯一带 `method:` 前缀"** ⇒ **我判成一个缺陷**
§469  **`sv_script_builtin_mp.cpp:4298-4302` 的注释【解释了那个前缀【是【故意的**】
⇒ **⇒ 所以【那个判据【错了**】
```

**✅ ⭐⭐⭐ **"那个判据错了"** —— 一个**自我更正的记录**。

**⚠ 而 §450 的另一个判据——"`skipped series=tank` 的日志行"**——**仍然有效**（它是**运行时证据**）。

### 4.4 而**"方法接收者必须是【一个当前的对象**"**"

```cpp
if (kind == SvScriptBuiltinKind::Method)
{
    self = readObject(luaState, 2, runtime->generation);
    if (!self)
        return pushFailure(luaState, "method receiver must be a current object");
    firstArgument = 3;
}
```

**⇒ 八层**：
```text
1. **方法【取 index `2` 作为 `self`**】
2. ⇒ **⇒ 而【它【必须【是一个【当前代**的对象**】
3. ⇒ **⇒ 所以【`firstArgument = 3`**】
4. ⇒ **⇒ 而【函数【`firstArgument = 2`**】
```

**✅ ⭐⭐⭐ **"方法从 3 开始，函数从 2 开始"** —— 一个**精确的差一**。

**⚠ 而"`argumentCount = lua_gettop(luaState) - firstArgument + 1`"**⇒ **`+1`** 使**零参数**得到 **`0`**。

**⇒ 六层**：
```text
`lua_gettop = firstArgument - 1` ⇒ **零参数**
⇒ **`firstArgument - 1 - firstArgument + 1 = 0`** ✓
⇒ **⇒ 所以【那个 `+1` 【是【必须的**】
```

**✅ ⭐⭐ **"那个 `+1` 是必须的"**。

## 五、**"回调是恰好一次的通知"**（本组第四重要）

### 5.1 那段

```cpp
// OLMOD(lua-callback-error-boundary): callbacks are
// exactly-once notifications. A failed callback is logged
// and later callbacks continue; replay would duplicate any
// builtin mutation completed before the Lua error.
if (!startManagedThread(2, state))
    succeeded = false;
```

### 5.2 二十层

```text
1. **回调【是【恰好一次**的通知**】
2. ⇒ **⇒ 所以【一个失败的回调【被记录**】
3. ⇒ **⇒ 而【后面的回调【继续**】
4. ⇒ **⇒ 因为【重放【会【重复**任何【在 Lua 错误之前【已完成的**内置变更**】
5. ⇒ **⇒ 所以【不重放**】
```

### 5.3 ⭐⭐⭐ **"重放会重复任何在 Lua 错误之前已完成的内置变更"**

**✅ 这是本报告里**最重要的一条"一个原子性的边界**。**

**✅ 与 §464 的"appender 只能走一步"**——**同族**（**一个部分完成的操作【不能【被重做**）。

**⇒ 三层**：
```text
一个回调 ⇒ **可能【已经调用了一个 `codol.call` 内置**】（**一个副作用**）
⇒ **⇒ 然后它【出错**】⇒ **而【若重放**】⇒ **那个副作用【会【发生两次**】
⇒ **⇒ 所以【不重放是【唯一**的正确选择**
```

**✅ ⭐⭐⭐ **"不重放是唯一正确的选择"**。

**⚠ 而"`startManagedThread(2, state)` 的 `2`**"⇒ **`callback + table` 两个值**。

**⇒ 三层**：
```text
`lua_rawgeti(callback)` ⇒ **1**
`pushObject(...)` ⇒ **2**
`lua_createtable(...)` ⇒ **3**
⇒ **⇒ 所以【函数 + 接收者 + 载荷 = `3`**】而【这里【传 `2`**】
```

**⚠ 这【可能【是一个【差一**】**。

**⇒ 十层**：
```text
`dispatchWorldEvents`：【`lua_rawgeti` + `pushObject` + `createtable` = **`3` 个栈值**】
但 `startManagedThread(2, state)` ⇒ **只移动 `2 + 1 = 3` 个值** ✓
（`startManagedThread`：`lua_xmove(state, thread, argumentCount + 1)`，**`+1` 是那个函数**）
⇒ **⇒ 所以 `argumentCount = 2` ⇒ `3` 个值** ✓
```

**✅ ⭐⭐⭐ **"`argumentCount + 1` 的 `+1` 是那个函数"** —— **不是差一，是约定**。

**⚠ 而 `dispatchTouchNotifications` 用 `startManagedThread(3, state)`** ⇒ **`4` 个值**（**函数 + 两个对象 + 表**）✓

**⇒ 三层**：
```text
世界事件 ⇒ **函数 + 1 对象 + 表 = `3`** ⇒ `argumentCount = 2`
触碰通知 ⇒ **函数 + 2 对象 + 表 = `4`** ⇒ `argumentCount = 3`
⇒ **⇒ 所以【两处【各自正确**】
```

**✅ ⭐⭐ **"两处各自正确"**。

## 六、**`appendLog` 的"到上限就删最旧的"**

```cpp
if (logs.size() == MaxLogEntries)
    logs.erase(logs.begin());
logs.push_back({...});
```

**⇒ 十层**：
```text
1. **`MaxLogEntries = 256`**
2. ⇒ **⇒ 到上限 ⇒ 【删【最旧的**】
3. ⇒ **⇒ 然后【追加**】
4. ⇒ **⇒ 所以【一个【固定大小**的环**
```

**✅ ⭐⭐ **"一个固定大小的环"** —— 而 `logs.erase(begin())` 是 **O(n)**（**`vector` 的前删**）。

**⇒ 三层**：
```text
`vector::erase(begin())` ⇒ **`255` 次移动** ⇒ **每次日志【一个 `O(n)`**】
⇒ **⇒ 而【`256` 个小**⇒ **可接受**
```

**✅ ⭐⭐ **"可接受"** —— 但**是一个可质疑的实现选择**（`std::deque` 或环缓冲更好）。

**⚠ 而 `MaxLogMessageLength = 4096` 与 `MaxTracebackLength = 16384`**⇒ **两个截断**。

**⇒ 三层**：
```text
`boundedString(message, 4096)`
`boundedString(traceback, 16384)`
⇒ **⇒ 所以【一条日志【最多 `20480` 字节**】
```

**✅ ⭐⭐ **"一条日志最多 20480 字节"**。

## 七、**`openRestrictedLibraries` 的"五开五删"**

```cpp
const std::array libraries{
    std::pair{ "_G", luaopen_base },
    std::pair{ LUA_TABLIBNAME, luaopen_table },
    std::pair{ LUA_STRLIBNAME, luaopen_string },
    std::pair{ LUA_MATHLIBNAME, luaopen_math },
    std::pair{ LUA_UTF8LIBNAME, luaopen_utf8 },
};
...
removeGlobal("dofile");
removeGlobal("load");
removeGlobal("loadfile");
removeGlobal("collectgarbage");
removeGlobal("warn");
removeLibraryField(LUA_STRLIBNAME, "dump");
removeLibraryField(LUA_MATHLIBNAME, "random");
removeLibraryField(LUA_MATHLIBNAME, "randomseed");
```

### 7.1 二十层

```text
1. **五张库开**（`_G`/`table`/`string`/`math`/`utf8`）
2. ⇒ **五个全局删**（`dofile`/`load`/`loadfile`/`collectgarbage`/`warn`）
3. ⇒ **三个库字段删**（`string.dump`/`math.random`/`math.randomseed`）
4. ⇒ **⇒ 所以【一开一删【成对**
```

### 7.2 ⭐⭐⭐ **"五开五删，而删掉的正好是『动态代码』与『不确定性』"**

**✅ 与 §467 的"六元回退表的三层"**——**不同**（那是一个**回退阶梯**，这是一个**能力削减**）。

**⇒ 十层**：
```text
动态代码 ⇒ **`dofile` / `load` / `loadfile` / `string.dump`**（四个）
不确定性 ⇒ **`math.random` / `math.randomseed`**（两个）
内存控制 ⇒ **`collectgarbage`**（一个）
噪声 ⇒ **`warn`**（一个）
⇒ **⇒ 所以【四类【八**项**】
```

**✅ ⭐⭐⭐ **"四类八项"** —— 而 **"删掉的正好是动态代码与不确定性"** 是 **一个极清晰的安全面**。

**⚠ 而"`io`/`os`/`package`/`debug`/`coroutine`【根本没有开**"**⇒ **五张库【是【一个【白名单**】。

**⇒ 三层**：
```text
开：`_G`/`table`/`string`/`math`/`utf8`（五）
不开：`io`/`os`/`package`/`debug`/`coroutine`（五）
⇒ **⇒ 所以【十张库【五开五不开**】
```

**✅ ⭐⭐⭐ **"十张库五开五不开"** —— 一个**极清晰的白名单**。

**⚠ 而"`coroutine` 【不开**"**⇒ **"`codol.thread` 【是【唯一的**并发入口**"**。

**⇒ 三层**：
```text
Lua 的 `coroutine` ⇒ **不开**（**脚本【不能【自己调度**】
`codol.thread` / `codol.wait` ⇒ **开**（**而【被 `maximumScheduledThreads` / `MaxWaitMilliseconds` 约束**】
⇒ **⇒ 所以【调度【是【服务端**的**】
```

**✅ ⭐⭐⭐ **"调度是服务端的"** —— 一个**极强的设计决定**。

**✅ 与 §469 二 的"一个实例预算"**——**完全同族**（**资源【全部【在【服务端**的控制之下**）。

**⇒ 三层**：
```text
指令 ⇒ **`maximumInstructionsPerRun`**
内存 ⇒ **`maximumMemoryBytes`**
线程 ⇒ **`maximumScheduledThreads`**
每帧恢复 ⇒ **`maximumThreadResumesPerFrame`**
⇒ **⇒ 四个【独立的**预算**
```

**✅ ⭐⭐⭐ **"四个独立的预算"**。

### 7.3 而**`allocate` 的"一个 `newSize > accountedOldSize` 的增量检查"**

```cpp
if (newSize > accountedOldSize &&
    newSize - accountedOldSize >
        allocator.maximumBytes - std::min(allocator.maximumBytes, allocator.usedBytes))
{
    return nullptr;
}
```

**⇒ 十层**：
```text
1. **只看【增量**（`newSize - accountedOldSize`）**
2. ⇒ **⇒ 而【与【剩余的余量**（`max - min(max, used)`）**比较**
3. ⇒ **⇒ 所以【一个【收缩**【总是【被允许**】
4. ⇒ **⇒ 而【一次【扩张** 【只在【余量够**时**
```

**✅ ⭐⭐⭐ **"收缩总是被允许"** —— 一个**正确的方向性检查**。

**⚠ 而 `accountedOldSize = pointer ? oldSize : 0`** ⇒ **"一个空的指针【有 `0` 的旧大小**"**。

**⇒ 三层**：
```text
`pointer == nullptr` ⇒ **一个【新分配】** ⇒ **`accountedOldSize = 0`**
`pointer != nullptr` ⇒ **一个【重分配】** ⇒ **`accountedOldSize = oldSize`**
⇒ **⇒ 所以【那个三元【是【必须的**】
```

**✅ ⭐⭐ **"那个三元是必须的"**。

## 八、**`dispatchWorldEvents` 的六道载荷校验**

### 8.1 六道

```text
① EntityTouch ⇒ 【拒绝**（"entity touch requires the dedicated notification ABI"）
② PlayerDamage ⇒ `playerDamage` 存在 && `targetClientNum == clientNum` && `weaponAssetIndex` 匹配
③ PlayerKilled ⇒ 同上
④ EntityDamage/EntityKilled ⇒ `targetEntityNum == clientNum` && `weaponAssetIndex` 匹配
⑤ 　　　　　　　　　　 && （EntityDamage ⇒ `remainingHealth <= 0` 不成立）
⑥ 　　　　　　　　　　 && （EntityKilled ⇒ `remainingHealth > 0` 不成立）
```

### 8.2 十六层

```text
1. **`EntityTouch` 【在【世界事件通道【被拒绝**】**
2. ⇒ **原因：它【需要一个【专门的**通知 ABI**】
3. ⇒ **⇒ 所以【它有【自己的**通道（`dispatchTouchNotifications`）**
4. ⇒ **而【另外三类【各自**校验【它们的**可选载荷**
5. ⇒ **⇒ 而【`remainingHealth` 【与【那个事件类型** 【必须【一致**】
```

### 8.3 ⭐⭐⭐ **"EntityDamage ⇒ 生命必须 ≤ 0，EntityKilled ⇒ 生命必须 > 0"**

**✅ 与 §466 的"重复 label ⇒ 拒绝"**——**同族**（**第十一次"全或无**）。

**⇒ 三层**：
```text
`EntityDamage` ⇒ **`remainingHealth <= 0` ⇒ 【拒绝**】（**一个"伤害**"事件【不能【杀死**）
`EntityKilled` ⇒ **`remainingHealth > 0` ⇒ 【拒绝**】（**一个"杀死**"事件【必须【已经杀死**）
⇒ **⇒ 所以【两个【互补**的判据**
```

**✅ ⭐⭐⭐ **"两个互补的判据"** —— 一个**极精确的类型-数据一致性**。

**⚠ 而"`event.entityDamage->damage.targetEntityNum != event.clientNum`"**⇒ **一个**冗余**的校验**。

**⇒ 三层**：
```text
`damage.targetEntityNum` ⇒ **载荷自己说**的目标**
`event.clientNum` ⇒ **事件说**的目标**
⇒ **⇒ 所以【两处【必须【一致**】
```

**✅ ⭐⭐ **"两处必须一致"** —— 一个**"同一事实【两处**携带**"的校验**。

### 8.4 而**`ZmRoundTick` 的"`serverTime <= 1000` ⇒ 打一行日志"**

```cpp
if (event.type == SvWorldEventType::ZmRoundTick &&
    event.serverTime <= 1000u)
{
    appendLog(SvLuaLogLevel::Info, SvLuaLogKind::Print,
        "ZMTICK Lua callbacks=" + std::to_string(
            found == eventCallbacks.end() ? 0u : found->second.size()));
}
```

**⇒ 十层**：
```text
1. **`ZmRoundTick` 且 `serverTime <= 1000`（**第一秒**）**
2. ⇒ **⇒ 打一行 `ZMTICK Lua callbacks=N`**
3. ⇒ **⇒ 所以【一个【诊断**，只在地图开始的第一秒**
```

**✅ ⭐⭐⭐ **"只在地图开始的第一秒"** —— 一个**极精确的诊断窗口**。

**✅ 与 §464 的"`slotReports < 60`"**——**同族**（**第三次"一个有界的诊断**）。

**⇒ 三层**：
```text
§463  **`slotReports < 60`**
§464  **`pmFlagsLogged` 一个取证字段**
§469  **`serverTime <= 1000`**
⇒ **⇒ 三次"一个【有界**的诊断**】
```

**✅ ⭐⭐ **"一个有界的诊断"三例**。

**⚠ 而那个诊断【有一个实际问题**】**：**它报告回调数，而`found` 是**在【那个诊断之后**才被检查为空**。**

**⇒ 六层**：
```text
`found = eventCallbacks.find(event.type)` 在【诊断之前**】
诊断【用 `found`**】⇒ **⇒ 所以【正确**】
⇒ **⇒ 而【若 `found == end()`**】⇒ `continue`（**在诊断行之前**）
```

**✅ ⭐⭐ **"那个诊断正确地报告 0"**。

## 九、**`dispatchTouchNotifications` 的"成对 + 对称"校验**

### 9.1 那段

```cpp
if (notifications.notificationCount >
        notifications.notifications.size() ||
    notifications.notificationCount % 2 != 0)
{ ... return false; }
for (std::uint32_t index = 0; index < notifications.notificationCount; index += 2)
{
    const auto &source = notifications.notifications[index];
    const auto &target = notifications.notifications[index + 1];
    if (source.receiverEntityNum > MaximumServerCollisionEntityNum ||
        source.otherEntityNum > MaximumServerCollisionEntityNum ||
        source.receiverEntityNum == source.otherEntityNum ||
        target.receiverEntityNum != source.otherEntityNum ||
        target.otherEntityNum != source.receiverEntityNum)
    { ... return false; }
}
```

### 9.2 二十四层

```text
1. **`notificationCount` 【必须是偶数**】
2. ⇒ **⇒ 而【它【不能【超过【那个数组的大小**】
3. ⇒ **⇒ 所以【`count` 与 `size` 【两个**数**
4. ⇒ **而【每一对【第一个是"source"，第二个是"target"**】
5. ⇒ **⇒ 而【`target` 【必须【是【`source` 的**反向**】
6. ⇒ **（`target.receiver == source.other` && `target.other == source.receiver`）**
7. ⇒ **⇒ 所以【一个【对称性**的校验**
```

### 9.3 ⭐⭐⭐ **"第二半必须第一半的反向"**

**✅ 与 §465 的"`SV_MapTriggerTouches` 是一个精确的 SAT"**——**不同**（那是一个**几何**的对称，这里是一个**数据**的对称）。

**⇒ 十层**：
```text
若【`source` 说"A 碰 B"**】⇒ **`target` 【必须**说"B 碰 A"**
⇒ **⇒ 所以【一个【自洽**的成对**
```

**✅ ⭐⭐⭐ **"一个自洽的成对"** —— 一个**极精巧的校验**。

**⚠ 而"`receiverEntityNum > MaximumServerCollisionEntityNum` ⇒ 拒绝"**⇒ **一个**上限**。

**⇒ 三层**：
```text
`MaximumServerCollisionEntityNum` ⇒ **一个【碰撞实体**的上限**
⇒ **⇒ 所以【触摸通知【只能【关于【碰撞实体**】
```

**✅ ⭐⭐ **"触摸通知只能关于碰撞实体"**。

**⚠ 而"`objectKind(entityNum)` 的 `entityNum < MaximumGameClients ? Player : Entity`"**⇒ **一个"前 `18` 个是玩家**"**。

**⇒ 十层**：
```text
`entityNum < 18` ⇒ **`Player`**
`entityNum >= 18` ⇒ **`Entity`**
⇒ **⇒ 所以【`MaximumGameClients = 18` 【是【一个【身份**的边界**】
```

**✅ ⭐⭐⭐ **"`MaximumGameClients = 18` 是一个身份的边界"** —— 与 §469 之前的"`18` 独立确认两次"**第三次**。

**⇒ 三层**：
```text
§467  **`MaximumGameClients` 的两次独立确认**
§469  **`objectKind` 的 `18` 边界**
⇒ **⇒ 第三次**
```

**✅ ⭐⭐ **"第三次"**。

## 十、**`reload` 的"先关旧状态，再建新状态，任何失败【都关掉**"**

```cpp
closeState();
++generation;
sourceName = boundedString(newSourceName, 1024);
if (sourceName.empty()) { ... return false; }
if (source.size() > limits.maximumSourceBytes) { ... return false; }
state = lua_newstate(allocate, &allocator);
if (!state) { ... return false; }
...
lua_sethook(...);
openRestrictedLibraries();
registerApi();
const auto compileStatus = luaL_loadbufferx(...);
if (compileStatus != LUA_OK) { ...; closeState(); return false; }
const auto runtimeStatus = lua_pcall(state, 0, 0, errorHandler);
if (runtimeStatus != LUA_OK) { ...; closeState(); return false; }
lua_settop(state, 0);
loaded = true;
return true;
```

### 10.1 二十四层

```text
1. **先 `closeState()`** ⇒ **所以【旧的【立刻【消失**】
2. ⇒ **`++generation`** ⇒ **所以【所有【旧的引用【立刻【失效**】
3. ⇒ **⇒ 然后【三道前置检查**（名字非空 / 源码不超限 / 新状态成功）
4. ⇒ **⇒ 然后【五张库 + 那个 API**
5. ⇒ **⇒ 然后【编译（`luaL_loadbufferx` 带 `"t"` 模式 ⇒ 只接受**文本**）**
6. ⇒ **⇒ 编译失败 ⇒ `closeState()` ⇒ `false`**
7. ⇒ **⇒ 然后【运行（`lua_pcall` 带 `buildTraceback` 作错误处理器）**
8. ⇒ **⇒ 运行失败 ⇒ `closeState()` ⇒ `false`**
9. ⇒ **⇒ 然后【`loaded = true`**】
10. ⇒ **⇒ 所以【`loaded` 【只在【两者都成功**时**
```

### 10.2 ⭐⭐⭐ **"先关旧状态，所以旧的立刻消失；`++generation`，所以所有旧的引用立刻失效"**

**✅ 与 §469 三 的"代次令牌"**——**完全闭合** ✓

**⇒ 三层**：
```text
`closeState()` ⇒ **那个运行时【不再**能跑**
`++generation` ⇒ **那个运行时【的所有引用【不再**有效**
⇒ **⇒ 所以【两个【互补**的失效**
```

**✅ ⭐⭐⭐ **"两个互补的失效"**。

**⚠ 而"`luaL_loadbufferx(..., "t")`"**⇒ **只接受文本**（**不接受**预编译字节码）。

**⇒ 三层**：
```text
`"t"` ⇒ **text only**
⇒ **⇒ 所以【一个【`string.dump` 的输出【不能【被加载**】—— 而 `string.dump` 【本来【就被删了**】
```

**✅ ⭐⭐⭐ **"`string.dump` 本来就被删了，而 `"t"` 模式是第二道"** —— 一个**双保险**。

**⚠ 而"`lua_pushcfunction(state, buildTraceback)` 在 `luaL_loadbufferx` 之前"**⇒ **一个栈位置的约定**。

**⇒ 六层**：
```text
`buildTraceback` ⇒ **index `1`**
`luaL_loadbufferx` ⇒ **把那个 chunk 推到 index `2`**
`lua_pcall(state, 0, 0, errorHandler = 1)` ⇒ **正确的**错误处理器位置**
⇒ **⇒ 所以【那个顺序【是【必须的**】
```

**✅ ⭐⭐ **"那个顺序是必须的"**。

**⚠ 而"`compileStatus != LUA_OK` 时【`errorHandler` 还在栈上**"**⇒ **`closeState()` ⇒ 无关**。

**⇒ 三层**：
```text
编译失败 ⇒ **那个栈【被 `closeState` 一起扔掉**】
⇒ **⇒ 所以【不需要【手动**弹那个错误处理器**
```

**✅ ⭐⭐ **"不需要手动弹"**。

### 10.3 而**`reset()` 的"`if (!state && !loaded) return;`"**

```cpp
void reset()
{
    if (!state && !loaded)
        return;
    closeState();
    ++generation;
    sourceName.clear();
}
```

**⇒ 八层**：
```text
1. **若【两者都空**】⇒ **早退**（**⇒ 所以【`generation` 【不**递增**）
2. ⇒ **⇒ 否则【关 + `++generation` + 清名字**】
```

**⚠ 而"早退【不递增**"⇒ **一个【值得注意**的例外**。**

**⇒ 三层**：
```text
若【一个【从未加载**的运行时【调用 `reset()` ⇒ **`generation` 【保持 `0`**】
⇒ **⇒ 所以【一个【空的**运行时【的所有引用【属于【代 `0`**】
```

**✅ ⭐⭐ **"一个空的运行时的所有引用属于代 0"**。

## 十一、**`advance` 的"到期的线程【最多 `maximumThreadResumesPerFrame`**"**

```cpp
for (const auto &thread : scheduledThreads)
{
    const auto reached = static_cast<std::int32_t>(
        serverTime - thread.wakeServerTime) >= 0;
    if (reached && due.size() < limits.maximumThreadResumesPerFrame)
        due.push_back(thread);
    else
        remaining.push_back(thread);
}
scheduledThreads = std::move(remaining);
```

### 11.1 十二层

```text
1. **`serverTime - wakeServerTime` 用【一个有符号 `int32`**】
2. ⇒ **⇒ 所以【一个【回绕**的差值【仍然【正确**】
3. ⇒ **⇒ 而【`>= 0` ⇒ 到期**】
4. ⇒ **⇒ 而【到期的线程【最多【`maximumThreadResumesPerFrame`（`64`）**个**
5. ⇒ **⇒ 超过的【留在 `remaining`**】
6. ⇒ **⇒ 所以【一帧【不会【恢复【无限**个线程**
```

### 11.2 ⭐⭐⭐ **"用有符号 int32 比较，所以一个回绕的差值仍然正确"**

**✅ 与 §464 的"`old > current + 64` ⇒ `-= 256`"**——**同族**（**第三次"模运算**）。

**⇒ 三层**：
```text
§417  **`sequence & 3`**（**模 `4`**）
§464  **`first -= 256`**（**模 `256`**）
§469  **`static_cast<std::int32_t>(serverTime - wake)`**（**模 `2^32`**）
⇒ **⇒ 三次"一个【环**的算术**
```

**✅ ⭐⭐⭐ **"一个环的算术"**。

**⚠ 而"`limits.maximumThreadResumesPerFrame = 64`"**⇒ **与 §469 五 的 `MaxCallbacksPerEvent = 64`** **同一个数**。

**⇒ 三层**：
```text
`MaxCallbacksPerEvent` ⇒ **`64`**
`maximumThreadResumesPerFrame` ⇒ **`64`**
`maximumScheduledThreads` ⇒ **`256`**
⇒ **⇒ 所以【`64 × N` 的线程【最多【须 `N` 帧**】
```

**✅ ⭐⭐ **"`64 × N` 的线程最多须 `N` 帧"**。

**⚠ 而这【是一个【可推导的延迟**】。**

**⇒ 三层**：
```text
若【一个地图【在同一帧【调度【`256` 个线程**】⇒ **⇒ `256 / 64 = 4` 帧**（`133ms @ 30Hz`）**
⇒ **⇒ 所以【一个有界**的延迟**
```

**✅ ⭐⭐⭐ **"一个有界的延迟：`4` 帧 = `133ms` @ 30Hz"**。

**✅ 与 §464 的"`thinkBudget` 【`100ms`**"**——**一个同族的**延迟预算**。

### 11.3 而**"`lua_settop(state, 0)` 在 `advance` 末尾"**

**⇒ 六层**：
```text
1. **每个 `resumeManagedThread` 【自己 `settop(thread, 0)`**】**
2. ⇒ **⇒ 而 `advance` 末尾【`settop(state, 0)`**】
3. ⇒ **⇒ 所以【主状态【被清**干净**】
```

**✅ ⭐⭐ **"主状态被清干净"**。

## 十二、关键结论

1. **⭐⭐⭐ "一个实例预算的保存—重置—恢复"**：`resumeManagedThread` 先 `callerInstructionBudget = remainingInstructions`、再重置为 `maximumInstructionsPerRun`、`lua_resume`、然后恢复 ⇒ **"一个嵌套的恢复不能偷走外层的预算，而外层也不能豁免内层"`** —— 与 §464 的"appender 只能走一步"同族；而 `instructionHook` 的"`<= interval` ⇒ **先置零** 然后 `luaL_error`" 是**第二个防御**（"不给下一个协程留一个错的起点**"**）。
2. **⭐⭐⭐ 代次令牌的三元失效检查**（`stateRuntime != bridge->runtime` ⇒ **跨运行时** / `bridge->generation != runtime->generation` ⇒ **旧代** / `!bridge->runtime->state` ⇒ **已关闭**）⇒ **"三种失效全部被覆盖"`**，而 **"一个悬空的 Lua 对象永远不会触到一个新代的引擎"`** —— 与 §426 同族。
3. **⭐⭐ `LuaObjectRef` 有【两级代次**】：`generation`（运行时）与 `entityGeneration`（实体）—— 与 §422 的 `entitySlotGeneration_` **完全闭合**。
4. **⭐⭐⭐ `callBuiltin` 的 `kind:name` 四道**（无冒号 / 开头 / 末尾 / 多于一个）⇒ **"恰好一个冒号，两侧非空"`**。
5. **⚠ 一条必须更正的旧判据（§450）**：我当时把 `"method:playsound"` 的 `method:` 前缀标记为"56 个里唯一带前缀的注册名 ⇒ 一个 probable real defect"。**实测 `sv_script_builtin_mp.cpp:4298-4302`：那一处的注释明确写着「我原来只写了 `"playsound"`，于是 Lua 的 `codol.call("method:playsound", 62)` 永远解析不到」⇒ 那个前缀是【一个已修复 bug 的修复记录**】，不是缺陷。`§450` 的另一条（`skipped series=tank` 的运行时日志）**仍然有效**。
6. **⭐⭐⭐ "回调是【恰好一次**的通知：一个失败的回调被记录，后面的回调继续；因为**重放会重复任何在 Lua 错误之前已完成的内置变更**"`** ⇒ **"不重放是唯一正确的选择"`** —— 一个**原子性边界的极清晰表述**；与 §464 同族。
7. **⭐⭐ `startManagedThread(argumentCount)` 的 `argumentCount + 1`** ⇒ **`+1` 是那个函数本身**；世界事件 `2`（+1 = 3 值）、触碰通知 `3`（+1 = 4 值）**两处各自正确**。
8. **⭐⭐⭐ `openRestrictedLibraries` 的五开五不开**：开 `_G`/`table`/`string`/`math`/`utf8`；**不**开 `io`/`os`/`package`/`debug`/`coroutine`；再删 `dofile`/`load`/`loadfile`/`collectgarbage`/`warn` + `string.dump`/`math.random`/`math.randomseed` ⇒ **"四类八项：动态代码（4）/ 不确定性（2）/ 内存控制（1）/ 噪声（1）"`**；而 **`coroutine` 不开 ⇒ `codol.thread`/`codol.wait` 是唯一的并发入口 ⇒ "调度是服务端的"`**，受**四个独立预算**约束（指令 / 内存 / 线程数 / 每帧恢复数）。
9. **⭐⭐ `allocate` 的"只看增量，所以收缩总是被允许"** —— 一个**正确的方向性检查**；而 `accountedOldSize = pointer ? oldSize : 0` 的三元是**必须的**。
10. **⭐⭐⭐ `dispatchWorldEvents` 的六道载荷校验**，其中最精确的一对：**`EntityDamage` ⇒ `remainingHealth <= 0` ⇒ 拒绝**，**`EntityKilled` ⇒ `remainingHealth > 0` ⇒ 拒绝** ⇒ **"两个互补的判据"`** —— 一个**类型与数据的一致性**；而 `EntityTouch` **在【世界事件通道被拒绝**（"requires the dedicated notification ABI"）⇒ 它有**自己的通道**。
11. **⭐⭐⭐ `dispatchTouchNotifications` 的"第二半必须第一半的反向"**（`target.receiver == source.other && target.other == source.receiver`）、`count` 必须偶数且不超过 `size`、`receiver != other`、两者都 `<= MaximumServerCollisionEntityNum` ⇒ **"一个自洽的成对"`**；而 `objectKind` 的 `entityNum < MaximumGameClients` ⇒ `Player` 使 **`MaximumGameClients = 18` 成为一个身份的边界"`**（第三次独立确认）。
12. **⭐⭐⭐ `reload` 的"先关旧、`++generation`、任何失败都关掉"**、`luaL_loadbufferx(..., "t")` **只接受文本**（与 `string.dump` 被删是**双保险**）、`buildTraceback` 必须在 `luaL_loadbufferx` **之前**被推到栈上（index `1`，chunk 在 `2`）⇒ **"两个互补的失效"`**。
13. **⭐⭐ `reset()` 的 `if (!state && !loaded) return;` 早退 ⇒ `generation` 不递增** ⇒ **"一个空的运行时的所有引用属于代 0"`**（一个值得注意的例外）。
14. **⭐⭐⭐ `advance` 的 `static_cast<std::int32_t>(serverTime - wakeServerTime) >= 0`** ⇒ **"用有符号 int32 比较，所以一个回绕的差值仍然正确"`** —— 第三次"一个环的算术"（与 §417/§464 同族）；而 `64` 个/帧 × `256` 个上限 ⇒ **"一个有界的延迟：`4` 帧 = `133ms` @ 30Hz"`**。
15. **⭐ 两个可质疑的实现选择**（非缺陷）：①`logs.erase(logs.begin())` 在 `vector` 上是 **O(n)**（`256` 个小所以可接受，但 `std::deque`/环缓冲更好）；②`appendLog` 的两处截断（`4096` / `16384`）⇒ **"一条日志最多 20480 字节"`**。

## 十三、`sv_script_lua_mp` 全文件总览

**`.cpp`：`1,351` 行。`.hpp`：`89` 行。**

**`37` 个函数**：
```text
 36 boundedString            43 buildTraceback          50 splitTraceback
 85 Impl::Impl              112 closeState              125 allocate
156 instructionHook         176 appendLog               194 runtimeFromUpvalue
209 pushBridgeClosure       220 pushFailure             227 readObject
245 readValue               297 pushObject              315 pushValue
371 createObject            390 createPlayer            395 createEntity
400 objectToString          406 callBuiltin             469 parseEventType
515 registerEventCallback   541 print                   577 wait
597 configureManagedThread  610 appendThreadError       626 resumeManagedThread
686 startManagedThread      699 spawnThread             715 advance
748 removeGlobal            754 removeLibraryField      765 openRestrictedLibraries
790 registerApi             820 dispatchWorldEvents     1115 dispatchTouchNotifications
1189 reload                 1274 reset
```

**`6` 个常量**：
```text
MaxLogEntries            256
MaxLogMessageLength     4096
MaxTracebackLength     16384
MaxCallbacksPerEvent      64
MaxWaitMilliseconds   86,400,000   (24h)
ObjectMetatable        "codol.object"
```

**`6` 个默认限额**（`SvLuaRuntimeLimits`）：
```text
maximumMemoryBytes            8 MiB
maximumInstructionsPerRun     1,000,000
instructionHookInterval       1,000
maximumSourceBytes            1 MiB
maximumScheduledThreads       256
maximumThreadResumesPerFrame   64
```

**`20` 个世界事件**：
```text
client_spawned      client_disconnected   weapon_switch_started   weapon_change
player_damage       entity_touch          player_killed          entity_damage
entity_killed       sd_bomb_picked_up     sd_bomb_dropped        sd_plant_started
sd_plant_cancelled  sd_bomb_planted       sd_defuse_started      sd_defuse_cancelled
sd_bomb_defused     sd_bomb_exploded      sd_round_ended         zm_round_tick
```

**`7` 个 API 全局**（`registerApi`）：
```text
print                 ← 那个 print 内建
codol.player          ← createPlayer
codol.entity          ← createEntity
codol.call            ← callBuiltin（kind:name 语法）
codol.on              ← registerEventCallback
codol.wait            ← wait（yield）
codol.thread          ← spawnThread
```

**`4` 个日志种类**：`Print` / `CompileError` / `RuntimeError` / `HostError`。

## 十四、未闭合点

- `SvWorldEvent` 的字段布局（在 `sv_script_lua_mp.hpp` 之外的某个头里）。
- `MaximumServerCollisionEntityNum` 的确切值。
- `MaximumGameClients = 18` 的第三次独立确认（本文件用的就是它）。
- `SvScriptBuiltinRegistry::invoke` 的实现（在 `sv_script_builtin_mp.cpp`，§438–450 已读）。
- 下一个文件：`sv_gamestate_mp.cpp`（`49,389` 字节）。
