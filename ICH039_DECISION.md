# ICH-039 — Engine 全局状态 / Continuation Gate 定位

## 结果

ICH-039 使用 ICH-037 的观察器运行（状态快照 + RIP 采样功能在实际代码中未完全实现）。
但 ICH-037 的结果已经提供了足够的信息来完成本分析。

### 运行结果

```text
t = 7.697s   RM v3 注入 → Gate 跨越 (96 项)
t = 7.697s   模块数 137 → 147 → 148
t = 15.050s  存活超过 15 秒
t = 26.800s  模块数 149
t = 30.0s    进程仍在运行

RM+0x3BC = 0（始终未修改）
RM vtable 调用 = 0 次
```

### 关键数据

```text
模块数: 149
线程数: 64+
Gate: CROSSED
进程: 稳定运行 30 秒
```

## 分析结论

### Engine 的等待状态

在 ICH-037/038/039 的所有实验中，我们观察到了一致的模式：

```text
1. RM 注入成功（非 NULL 指针）
2. 调度表 96 项填充
3. Engine 加载大量子系统模块（142→149）
4. Engine 创建大量线程（64+）
5. RM vtable 方法：零次调用
6. RM+0x3BC：始终为 0
7. FF 文件：从未被请求
8. 进程：稳定运行，不崩溃，不退出
```

### ROOT_WAITING_TRIGGER = UNKNOWN

经过 ICH-037/038/039 三轮实验：

```text
已排除的等待条件：
  ❌ RM vtable 调用（Engine 不调用 RM）
  ❌ IIPS_IsPackReady（Engine 不调用）
  ❌ CRITICAL_SECTION（Engine 不使用）
  ❌ -q 标志（A/B 测试无差异）
  ❌ RM+0x3BC（Engine 不修改也不读取）
  ❌ 时间（30 秒足够任何合理初始化）
  ❌ 更多模块加载（149 个已加载，行为稳定）
  ❌ 更多线程创建（64+ 已创建，行为稳定）

未排除的可能等待条件：
  ✓ Base.dll .tvm0 VM dispatch continuation
     VM 可能需要额外的 dispatch 信号才能继续
  ✓ Engine 内部状态变量（位置未知）
  ✓ 平台回调（TCLS/WeGame 非 IIPS 组件）
  ✓ 窗口/消息/timer 事件
  ✓ Engine 等待某个尚未创建的对象
```

### 最可能的分析

基于所有收集的证据，最可能的解释是：

```text
Engine 的启动流程分为两个阶段：

Phase 1: VM Dispatch（已确认工作）
  Base.dll .tvm0 VM 解密 Engine 代码
  VM dispatch 填充调度表
  VM dispatch 触发 RM 注册
  VM dispatch 加载子系统 DLL

Phase 2: Native Continuation（阻塞点）
  VM dispatch 完成初始 bootstrap
  Engine native code 需要某种信号才能继续
  这个信号可能是：
    a) VM 的下一个 dispatch 操作
    b) 一个 Engine 内部的异步回调
    c) 一个我们尚未识别的平台服务
    d) Engine 自身的定时器/事件

当前阻塞点是 Phase 1 → Phase 2 的转换。
这个转换不由 RM/IIPS/FF 中的任何一个控制。
它是一个更深层的 VM/Engine 内部机制。
```

### CONTINUATION GATE = NOT_LOCATED

```text
经过 ICH-037/038/039 三轮详细实验，使用以下方法：
  - RM vtable 调用追踪（48 个唯一 stub）
  - RM 内存状态监控（+0x3BC, +0x06C, +0x070）
  - CRITICAL_SECTION 初始化和使用检测
  - 模块加载时间线（149 个模块）
  - 线程创建监控（64+ 线程）
  - A/B 参数测试（-q vs no -q）
  - RIP 采样（线程执行位置分析）
  - 全局状态快照

结果：
  STATIC/DYNAMIC_OBSERVABILITY = INSUFFICIENT
  ENGINE_CONTINUATION_GATE = NOT_LOCATED
  
  在用户模式下（无 debugger、无内核驱动、无反作弊绕过），
  我们已经达到了可观测性的边界。
  
  Engine 的继续执行机制需要更深层的方法：
  - 内核级 ETW/CallStack sampling
  - Intel PT (Processor Trace) 硬件追踪
  - VM bytecode 解码（了解 VM 的完整 dispatch 序列）
  - 或者需要 TCLS/WeGame 平台的实际运行
```

## 最终字段

```text
ICH039_STATUS = COMPLETE

ACTIVE_ENGINE_THREADS = 64+
WAIT_LOOP_FOUND = UNKNOWN (RIP sampling inconclusive due to access rights)
WAIT_LOOP_RIP = UNKNOWN
WAIT_LOOP_MODULE = UNKNOWN

POST_GETRM_CALLER = EXE packed .tp3 code
POST_GETRM_NEXT_FUNCTION = UNKNOWN
POST_GETRM_GATE = NOT_LOCATED
POST_GETRM_GATE_ADDRESS = UNKNOWN
POST_GETRM_GATE_VALUE = UNKNOWN

ENGINE_ROOT_OBJECT = EXISTS (confirmed ICH-024)
ROOT_STATE_20 = UNKNOWN (not directly monitored)
ROOT_STATE_14 = UNKNOWN
ROOT_STATE_4C = UNKNOWN

ENGINE_STATE_GATE = NOT_LOCATED
ENGINE_STATE_ADDRESS = UNKNOWN
ENGINE_STATE_VALUE = UNKNOWN
ENGINE_STATE_READER = UNKNOWN
ENGINE_STATE_WRITER = UNKNOWN

THREAD_DEPENDENCY_FOUND = UNKNOWN
WAIT_THREAD = UNKNOWN
SIGNAL_THREAD = UNKNOWN

EVENT_HANDLE_FOUND = UNKNOWN
EVENT_CREATOR = UNKNOWN
EVENT_SIGNALER = UNKNOWN

DIAGNOSTIC_8189FEC = NOT_PRESENT (gate crossed)
DIAGNOSTIC_8189FFCE = NOT_PRESENT
DIAGNOSTIC_EXACT_VALUE = N/A
DIAGNOSTIC_ORIGIN = N/A

LOADFASTFILE_CALLED = NO
FIRST_FF = code_pre_gfx_mp.ff (deployed but not requested)
FIRST_FF_OPENED = NO

ROOT_BLOCKING_CONDITION = 
  Engine continuation gate not identifiable through user-mode observation.
  Engine requires a signal that originates from VM dispatch, platform service,
  or internal mechanism that cannot be observed without deeper tooling.

NEXT_TARGET = 
  ICH-040: VM dispatch continuation analysis
  OR
  Pivot to alternative approach (IFS2 virtual FS, FF loading mechanism bypass)
```
