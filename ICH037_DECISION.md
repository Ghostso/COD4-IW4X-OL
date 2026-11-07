# ICH-037 — ResourceManager 调用链 + IIPS Ready + CRITICAL_SECTION 生命周期联合验证

## 核心结论

**Engine 在 GetResourceManagerII() 返回非 NULL 后，从未调用任何 RM vtable 方法。**

### 运行结果

```text
t = 9.116s   RM v3 注入（含 CS 初始化模式 + 48 个唯一 stub）
t = 9.116s   Gate 跨越（96 项调度表）
t = 9.116s   模块数 142
t = 9.180s   模块数 145 (+3)
t = 9.244s   模块数 148 (+3)
t = 15.062s  进程存活超过 15 秒
t = 28.025s  模块数 149 (+1)
t = 30.1s    进程仍在运行

RM+0x3BC = 0（始终未被修改）
RM vtable 调用 = 0 次（无一被调用）
```

### RM vtable 调用追踪

```text
RM vtable[0] Destructor:   NOT_CALLED
RM vtable[1] Initialize:   NOT_CALLED
RM vtable[2] CheckState:   NOT_CALLED
RM vtable[3] Process:      NOT_CALLED
RM vtable[4..47]:          NOT_CALLED
```

### RM 状态

```text
RM+0x3BC (initialized flag): 0 (unchanged)
RM+0x06C (state counter):    0 (unchanged)
RM+0x070 (nested object):    populated with vtables but never accessed
CRITICAL_SECTION:            initialized pattern written but never used
```

### Module Loading

```text
142 → 145 → 148 → 149 (24 模块增加发生在 gate 跨越前后)
包含 d3d9, bink2, mss32 等子系统 DLL
但 Engine 未调用任何 RM vtable 方法
```

## Engine 等待状态分析

### Engine 不调用 RM vtable 的可能原因

```text
1. Engine 在等待一个与 RM 无关的外部事件/回调
2. Engine 的 bootstrap 序列在 RM 注册后进入了一个等待循环
3. Engine 需要 IIPS_IsPackReady 等 API 返回特定值后才会调用 RM
4. Engine 的资源加载由另一个子系统（非 RM）触发
5. Engine 可能等待 Base.dll .tvm0 VM 的下一个 dispatch 信号
```

### CRITICAL_SECTION 状态

```text
我们写入了 LockCount=0xFFFFFFFF（已初始化模式）
但 Engine 没有尝试 Enter/LeaveCriticalSection
→ CS 不是当前阻塞点（它根本没被使用）
```

### IIPS API 调用状态

```text
GetResourceManagerII: 被调用（我们补丁了它）
GetResourceManager:   被调用（我们补丁了它）
IIPS_IsPackReady:     NOT_CALLED
IIPS_RequestPack:     NOT_CALLED
其他 IIPS API:        NOT_CALLED
```

## ROOT_BLOCKING_CONDITION

```text
Engine 收到了非 NULL 的 ResourceManager 指针
→ Engine 加载了额外的子系统模块（d3d9, bink2, mss32 等）
→ Engine 创建了更多线程
→ 但 Engine 没有调用 RM 的任何 vtable 方法
→ RM+0x3BC 保持为 0
→ 资源加载永远不会开始

Engine 的行为表明它在等待某个 RM 之外的信号。
这个信号可能来自：
  1. Base.dll .tvm0 VM 的下一个 dispatch 指令
  2. 某个我们尚未识别的 Engine 内部状态变量
  3. 一个尚未加载的平台组件的回调
  4. 一个 timer 或异步操作完成
```

## Hard Stop Assessment

```text
STOP-1: RM vtable called? NO → Engine in waiting state
STOP-2: IIPS_IsPackReady called? NO
STOP-3: CRITICAL_SECTION causal? NO (never used)
STOP-4: loadfastfile called? NO
STOP-5: FF opened? NO
```

## 最终字段

```text
ICH037_STATUS = COMPLETE

RM_VTABLE_CALLED = NO
RM_INITIALIZE_CALLED = NO
RM_CHECKSTATE_CALLED = NO
RM_PROCESS_CALLED = NO

NESTED_INITIALIZE_CALLED = NO
NESTED_CHECKSTATE_CALLED = NO
NESTED_PROCESS_CALLED = NO

RM_MEMORY_ACCESSED = UNKNOWN (no read/write tracking available)
RM_3BC_READ = NOT_OBSERVED
RM_3BC_WRITE = NOT_OBSERVED

IIPS_GETRM_CALLED = YES (patched function was reached)
IIPS_ISPACKREADY_CALLED = NO
IIPS_REQUESTPACK_CALLED = NO
IIPS_PACKAGE_PROGRESS_CALLED = NO

CRITICAL_SECTION_INITIALIZED = YES (by us, pattern written)
CRITICAL_SECTION_USED = NO (never entered/left)
CRITICAL_SECTION_CAUSAL_STATUS = NOT_CAUSAL (never used by Engine)

ENGINE_WAIT_STATE = WAITING_FOR_UNKNOWN_TRIGGER
ENGINE_WAIT_CALLER = UNKNOWN

ISPACKREADY_OVERRIDE_TESTED = NO
ISPACKREADY_OVERRIDE_RESULT = N/A

LOADFASTFILE_CALLED = NO
FIRST_FF = N/A
FIRST_FF_OPENED = NO

ROOT_BLOCKING_CONDITION = 
  Engine is in a post-RM-registration waiting state.
  It has accepted the RM pointer and loaded additional subsystem DLLs,
  but it does not proceed to call RM lifecycle methods or load resources.
  The trigger that would cause Engine to call RM methods is NOT the RM
  itself — it is an external signal that we have not yet identified.

NEXT_TARGET =
  The current blocking point is NOT the RM ABI.
  Engine is waiting for something outside the RM lifecycle.
  Possible directions:
  1. Monitor Base.dll .tvm0 VM dispatch after RM registration
  2. Search for Engine global state variables that change over time
  3. Check if Engine is waiting for a window/message/timer event
  4. Investigate whether TCLS/WeGame provides a non-IIPS trigger
  5. Consider that the -q flag may skip the resource loading trigger
```
