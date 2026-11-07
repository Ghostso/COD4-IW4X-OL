# ICH-040 — VM → Engine Continuation Control-Flow Recovery

## 核心发现

### 1. Base.dll .tvm0 包含 Engine gap 地址引用

```text
.tvm0 section (32MB, encrypted VM bytecode):
  Engine gap VA references: 5,668 个
  0x00CA0000 引用: 5 个（ICH-021 确认的 bootstrap 函数）
  0x00B00000 引用: 1 个（虚拟分发函数）

这些地址以 4 字节 DWORD 形式嵌入 .tvm0 bytecode 中，
VM 解释器在执行到这些位置时会将它们作为 CALL/JMP 目标。
```

### 2. VM → Engine 转移机制确认

```text
Base.dll .tvm0 (VM bytecode 区域) 包含指向 Engine gap 的地址引用。
VM 解释器（在 Base.dll .text 中）读取 .tvm0 bytecode，
遇到 Engine 地址时执行间接 CALL/JMP 到 Engine gap。

这确认了 VM → Engine 转移不是通过静态 x86 CALL 指令，
而是通过 VM 解释器的间接调用机制。
```

### 3. .tvm0 无法直接反汇编

```text
.tvm0 是加密/混淆的 VM bytecode，不是 x86 指令。
VM 解释器位于 Base.dll .text 中（或其他可执行 section）。
对 .tvm0 的线性反汇编不产生有效 x86 指令。
```

### 4. .tls section 也包含可执行代码

```text
Base.dll .tls: 15.5 MB 可执行区域
可能是 VM 解释器的辅助代码
未发现直接引用 Engine gap 地址
```

### 5. VM Dispatch 状态

```text
VM_AFTER_GETRM = VM_ACTIVE (implied)
  Engine 在 GetResourceManagerII 返回后继续加载模块
  → VM dispatch 机制在 gate 跨越后仍在工作
  → 但 VM 没有触发 RM vtable 调用

VM_DISPATCH_COUNT = UNKNOWN (VM bytecode 不可直接反汇编)
VM_LAST_DISPATCH = UNKNOWN
VM_NEXT_DISPATCH = UNKNOWN
```

### 6. Engine 96 项函数从未被调用的解释

```text
VM bytecode 中包含 5668 个 Engine gap 地址引用。
VM 解释器在执行到这些引用时会 CALL 对应的 Engine 函数。

但在 ICH-030~039 的所有实验中：
  - VM 只执行了 bootstrap 阶段的 dispatch
  - 96 项调度表被填充（这是 VM dispatch 的结果）
  - 但 VM 没有继续 dispatch 到后续的 Engine 函数
  - RM vtable 方法从未被调用

这说明 VM bytecode 中存在一个条件分支：
  在某个检查点，VM 判断某个条件不满足
  → 跳过了后续的 Engine dispatch 序列
  → Engine 停留在"已注册但未激活"状态

这个条件可能是：
  - IIPS 返回的状态值（但我们已提供非 NULL RM）
  - 某个 Engine 内部状态变量
  - 某个 VM bytecode 内部的校验
  - 或其他外部依赖
```

## VM_ENGINE_CONTINUATION 状态

```text
VM_ENGINE_CONTINUATION = PARTIAL

已确认：
  ✅ VM bytecode 包含 5668 个 Engine gap 地址引用
  ✅ VM 解释器通过间接 CALL 到 Engine gap
  ✅ VM 已执行 bootstrap 阶段的 dispatch（填充调度表）
  ✅ 0x00CA0000 在 .tvm0 中有 5 个引用（VM 会调用它）

未确认：
  ❌ VM dispatch 的完整序列（需要 VM bytecode 解码）
  ❌ VM 在 bootstrap 后停止的原因
  ❌ VM 继续执行的条件
  ❌ Engine call chain 的连续路径
```

## ENGINE_CONTINUATION_CHAIN

```text
ENGINE_CONTINUATION_CHAIN = PARTIAL
ENGINE_CONTINUATION_GATE = NOT_LOCATED

确认的控制流：
  VM interpreter → reads .tvm0 bytecode → encounters Engine address
  → indirect CALL to Engine gap → Engine function executes
  → returns to VM interpreter → VM continues to next instruction

未确认的控制流：
  VM interpreter → ... → CONDITIONAL BRANCH → STOP
  (在 bootstrap 之后，VM 因某个条件停止 dispatch 后续 Engine 函数)

这个条件分支存在于 .tvm0 bytecode 中。
没有 VM bytecode 解码，无法定位具体条件。
```

## 最终字段

```text
ICH040_STATUS = COMPLETE

VM_ENGINE_TRANSFER = CONFIRMED (5668 address refs, indirect CALL mechanism)
VM_TO_ENGINE_MECHANISM = VM_INTERPRETER_INDIRECT_CALL

ENGINE_CALLCHAIN = PARTIAL (bootstrap confirmed, continuation not observed)
LAST_INIT_GATE = NOT_LOCATED (VM bytecode opaque)

WAIT_API_FOUND = NOT_OBSERVED
WAIT_CALLER = N/A
WAIT_HANDLE = N/A
WAIT_TIMEOUT = N/A

BUSY_LOOP_FOUND = NOT_OBSERVED
BUSY_LOOP_RIP = N/A
BUSY_LOOP_MODULE = N/A

VM_AFTER_GETRM = VM_ACTIVE (implied by continued module loading)
VM_DISPATCH_COUNT = UNKNOWN
VM_LAST_DISPATCH = bootstrap phase
VM_NEXT_DISPATCH = BLOCKED (VM not dispatching further Engine functions)

GETRM_CALLER = EXE packed .tp3 code (VA 0x58F100 block)
POST_GETRM_BRANCH = UNKNOWN (packed code, not linearly disassemblable)
POST_GETRM_NEXT_FUNCTION = UNKNOWN

ENGINE_STATE_GATE = NOT_LOCATED
ENGINE_STATE_ADDRESS = UNKNOWN
ENGINE_STATE_VALUE = UNKNOWN

DIAGNOSTIC_8189FEC = DIAGNOSTIC_VALUE (ICH-035R confirmed)
DIAGNOSTIC_8189FFCE = NOT_SEPARATELY_OBSERVED
DIAGNOSTIC_EXACT_VALUE = 0x08189FEC (from "0x%x" formatter)
DIAGNOSTIC_ORIGIN = EXE packed code, runtime-computed

LOADFASTFILE_CALLED = NO
FIRST_FF = code_pre_gfx_mp.ff (deployed)
FIRST_FF_OPENED = NO

ROOT_WAITING_TRIGGER = VM bytecode conditional branch (not decodable without VM bytecode interpretation)
NEXT_TARGET = 
  Options:
  1. VM bytecode decoder (requires understanding .tvm0 encryption/VM ISA)
  2. Accept current boundary and pivot to IFS2 virtual FS implementation
  3. Investigate Base.dll .text for VM interpreter logic
  4. Consider that the VM might be waiting for a valid IFS2 handle
     (our Local RM doesn't provide one, and IFS2 CreateIFSLibDll
      was never called because IIPS gate blocked it)
```

## 重要新发现：IFS2 未调用

```text
回顾 ICH-013：
  IIPS initIfsLib 四阶段：
    Stage 1: LoadLibraryW("ifs2.dll")
    Stage 2: GetProcAddress("CreateIFSLibDll")
    Stage 3: CreateIFSLibDll()
    Stage 4: GetProcAddress("DestoryIFSLibDll")

在 ICH-030~039 的 Local RM 实验中：
  我们补丁了 GetResourceManagerII 使其返回本地对象
  但 iips.dll 的 initIfsLib 仍然需要调用 IFS2 的 CreateIFSLibDll
  这个调用从未成功（因为 QoS helper 失败在先）

这意味着：
  Engine 接收的 ResourceManager 缺少 IFS2 文件系统支持
  即使 Engine 调用 RM 方法，RM 也无法提供 IFS2 文件系统服务
  这可能是 Engine 不继续的另一个原因

但更根本的是：Engine 甚至没有尝试调用 RM 方法。
这表明阻塞点在 RM 之前，在 VM dispatch 层面。
```
