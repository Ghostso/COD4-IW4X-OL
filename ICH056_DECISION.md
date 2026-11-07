# ICH-056 — VM Boundary Decision

## 判定

```text
ICH056_STATUS                   = PARTIAL (analysis complete, decision pending)
VM_ROLE                         = DISPATCHER + BOOTSTRAP
MINIMUM_VM_SCOPE                = 5-15 opcodes + dispatch scheduler + .tvm0 decryption
RESOURCE_TRIGGER_VM_DEPENDENCY  = CONFIRMED
GAME_INIT_VM_DEPENDENCY         = CONFIRMED
FULL_VM_RECOVERY_REQUIRED       = UNKNOWN (between minimal and full)
NEXT_TARGET                     = USER_DECISION_REQUIRED
```

## VM 角色确认

VM 承担两个角色：

### 1. BOOTSTRAP (一次性，已完成)
- 解密 3.08MB Engine native code 到 Engine gap
- 构建 96-entry dispatch table
- dispatch 0x00CA0000 (global init)
- Bootstrap 角色在 t≈7s 完成

### 2. DISPATCH (持续性，当前阻塞点)
- 继续作为所有 96 个 Engine 函数的唯一调用者
- 决定何时调用哪个 Engine 函数
- Local RM 后 VM dispatch 没有继续 dispatch 后续函数
- 这是 Engine "停滞"的直接原因

**VM 不是完整解释器。** Engine 的 3.08MB native code 是完整的 x86。
VM 只是 dispatcher，不是 code interpreter。

## 关键事实

| 问题 | 答案 | 证据 |
|---|---|---|
| Engine code 完整吗？ | YES | 3.08MB valid x86, 10 subsystem clusters |
| Dispatch table 完整吗？ | YES | 96 entries, all valid |
| RM ABI 正确吗？ | 不相关 | Engine 不调 RM |
| IIPS API 需要吗？ | 不相关 | Engine 不调 IIPS |
| Native caller 存在吗？ | NO | ICH-022 STATIC_ABSENCE |
| 平台能触发吗？ | NO | ICH-045 UI_BYPASS |
| VM 是唯一入口吗？ | YES | ICH-022/053/054 |
| Root Object 地址？ | UNKNOWN | ICH-043 |
| Game Init 函数？ | UNKNOWN | ICH-055 |

## 最小 VM 恢复范围估计

要越过当前阻塞点（触发 Resource Event → Game Init），最小需要：

```
Level 1: .tvm0 解密机制
         → 未知加密方式，可能需要理解 VM 加密 key/algorithm
         → 这是最大的不确定因素

Level 2: VM ISA dispatch/call opcode (~1-5 opcodes)
         → VM 如何调用 Engine 函数
         → 需要理解 operand encoding

Level 3: Root Object construction (~1-3 opcodes)
         → VM 如何设置 ECX (Root Object)
         → Root Object 地址 UNKNOWN

Level 4: Dispatch scheduler/condition (~1-3 opcodes)
         → VM 如何决定调用时序
         → 什么条件触发 Resource Event

估计总量: 5-15 个 opcode + 解密机制 + dispatch scheduler
```

**不确定性极大**：我们不知道 VM ISA 的实际复杂度、.tvm0 的加密方式、或 VM interpreter 在 Base.dll .text 中的具体位置。这个估计可能严重低估。

## 三种方案对比

| 方案 | 描述 | 可行性 | 风险 |
|---|---|---|---|
| A: 最小 VM | 解密 .tvm0 + 理解 dispatch opcode + Root Object + scheduler | UNKNOWN | 高：未知加密、反调试检测 |
| B: 直接 Engine call | 知道 Game Init 函数 + Root Object → 直接 call | 需要两个 UNKNOWN | 高：伪造 Root Object 可能崩溃 |
| C: 找替代路径 | 不经过 VM dispatch 的初始化路径 | 已确认不存在 | N/A |

**三个方案都需要某种形式的 VM 知识。** 没有"完全不碰 VM"的路径。

但"完整 VM ISA 恢复"可能不是必要的。最小范围可能是 5-15 个 opcode + dispatch scheduler，而非整个 VM ISA。

## FULL_VM_RECOVERY_REQUIRED 判定

```
FULL_VM_RECOVERY_REQUIRED = UNKNOWN
```

原因：
- 如果只需要 5-15 个 opcode + scheduler → 不需要完整恢复 → 情况 A
- 如果 VM ISA 极其复杂（如 VMProtect/Themida）+ .tvm0 加密强度高 → 可能需要大量工作 → 接近情况 B
- 我们目前无法确定 .tvm0 的加密强度或 VM ISA 复杂度
- 需要先尝试解密 .tvm0 或定位 VM interpreter 才能给出确定答案

## 建议的下一步

**由用户决定是否投入 VM 分析。**

如果决定继续，建议的最小路径：

1. **定位 VM interpreter**（在 Base.dll .text 中搜索 dispatch loop pattern）
2. **理解 .tvm0 加密**（对比 disk 与 runtime Engine gap 内容）
3. **识别 dispatch opcode**（在解密后的 bytecode 中搜索 Engine 地址引用）
4. **确定 Root Object 构造**（跟踪 VM 初始化 ECX 的方式）

这是一个高风险/高投入/高不确定性的方向，但在当前技术路线下是唯一能推进的路径。

## 输出

- ICH056_DECISION.md
