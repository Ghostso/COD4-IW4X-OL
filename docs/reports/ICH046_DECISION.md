# ICH-046 — Base VM → Engine Continuation 定向恢复

## 判定

```text
ICH046_STATUS             = NOT_LOCATED
VM_ENGINE_CONTINUATION    = NOT_LOCATED
PRIMARY_ENGINE_TARGET     = UNKNOWN
CONTINUATION_MECHANISM    = UNKNOWN
RUNTIME_CORRELATION       = PARTIAL
NEXT_TARGET               = STOP
```

## 分析过程

### Anchor A (RVA 0x18AE194 = 0x00E83B00)

Anchor A 是 Base.dll .tls 段中 0x00E83B00（Engine dispatch table base）的唯一一处静态引用。

±0x100 窗口分析：
- 前后为 VM bytecode stream 的操作数，非 x86 指令
- 无相邻 dispatch index
- 无 function pointer pair
- 无 jump table
- 无 callback table
- 无 vtable metadata

±0x400 窗口内发现 10 个 Engine gap 地址（0x00994000-0x00CA789A 范围），但它们散布在 VM bytecode stream 中，无集中模式，无法构成 dispatch 机制。

±0x1000 窗口内发现 28 个 Engine gap 地址，同样是散布分布。

结论：**Anchor A 是孤立 dword，不是 dispatch header、不是 continuation 入口。**

### Anchor B (RVA 0x15EC784 = 0x00E83C00)

Anchor B 位于 Base.dll .tls 段的 dense VM constant stream 中。

±0x100 内所有 dword 均为 0x00E8xxxx / 0x0082xxxx 交替模式，不属于 Engine gap 地址范围（0x00994000-0x00CA789A）。0x00E83C00 的 0xE83C 值超出了 Engine gap 上限 0x00CA789A。

结论：**Anchor B 是 VM constant pool 成员，不构成 Engine dispatch 数据。**

### Engine 地址反向搜索

| Engine 地址 | .tls 中出现次数 | 分类 |
|---|---|---|
| 0x00CA0000 | 90 | 散布，VM bytecode 伪随机匹配 |
| 0x009B9C00 | 0 | 不存在 |
| 0x00B00000 | 81 | 散布，VM bytecode 伪随机匹配 |
| 0x00E83B00 | 1 | Anchor A，孤立 |
| 0x00E83C18 | 0 | 不存在 |

0x00E83C18 和 0x009B9C00 完全不出现在 .tls 中，说明 dispatch table 的 slot 值和被写入的 function pointer 是 runtime 动态生成的，不存在于任何静态 VM 数据中。

0x00CA0000 和 0x00B00000 的 90/81 个 hit 是 VM bytecode stream 中的伪随机字节匹配（dword 恰好等于这些地址值），不是地址引用。90 hits 分布在 0xF82B03~0x19A4797 的 15MB 范围内，无集中模式。

### Dispatch candidate 搜索

在 Anchor A ±0x1000 范围内：
- 未找到间接 call/jmp 指令（.tls 不是 x86 代码）
- 未找到 dispatch index / table header
- 未找到 function pointer table
- 未找到 jump table
- 未找到 callback table

在 Anchor B ±0x100 范围内：
- 未找到 Engine gap 地址（0x00E83xxx 超出 Engine gap 范围）
- 是 VM constant pool 交替模式

结论：**有限窗口内无法建立可靠的 continuation candidate。**

### Runtime correlation

Runtime timing 已确认（ICH-021/026/044）：
- 0x00CA0000 executes at t≈6.8s
- Dispatch table populated at t≈7.0s
- Gate crossed at t≈7.875s

但 caller/return address 不可获取（ICH-042 证明 debugger 路线不可用，GetThreadContext 被 TP3Shell 拒绝）。

## Hard Stop 判定

满足以下 Hard Stop 条件：

1. **已知 Engine 地址静态关联无法超过普通常量引用** — Anchor A 是孤立 dword，不是 dispatch
2. **有限窗口内无法建立可靠 continuation** — ±0x1000 内无任何 dispatch 结构
3. **出现大量候选但无法区分真实 dispatch** — 0x00CA0000 的 90 hits 无法从 VM bytecode noise 中区分真实引用

按 Hard Stop 要求，不得扩大到全 .tvm0 扫描，不得恢复 VM ISA。

## 结论

Base.dll .tls 中的 Engine 地址引用是 VM bytecode 的常量池数据，不是可直接解读的 dispatch/callback/function pointer table。

Engine 的 96-entry dispatch table 和 0x00CA0000→0x00E83C18 的写入是 VM 在 runtime 动态完成的，其调用机制存在于 .tvm0 的 VM bytecode 解释器中，无法在不恢复 VM ISA 的前提下从静态 .tls 数据中恢复 continuation 路径。

## 输出文件

- ICH046_ANCHOR_A.csv
- ICH046_ANCHOR_B.csv
- ICH046_ENGINE_REF.csv
- ICH046_DISPATCH_CANDIDATES.csv
- ICH046_RUNTIME_CORRELATION.csv
- ICH046_DECISION.md
