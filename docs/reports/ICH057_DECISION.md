# ICH-057 — VM Interpreter / Dispatch Mechanism 定位

## 判定

```text
ICH057_STATUS                = PARTIAL
VM_INTERPRETER               = NOT_LOCATED (传统 bytecode interpreter 不存在)
VM_MECHANISM_REDEFINITION    = CONFIRMED (code decryptor + dispatch controller)
VM_LOCATION                  = .tls (dispatch scheduler candidate) + .tvm0 (encrypted code)
DISPATCH_LOOP                = NOT_LOCATED
TVM0_DECRYPTION              = NOT_LOCATED
VM_ENGINE_CALL_DESCRIPTOR    = NOT_LOCATED
MINIMUM_OPCODE_COUNT         = UNKNOWN (VM ISA 概念可能不适用)
VM_RECOVERY_COST             = UNKNOWN/HIGH
NEXT_TARGET                  = STOP_OR_USER_DECISION
```

## 核心发现：VM 概念需要重新定义

### 搜索结果

在 Base.dll .text (7.2MB) 中搜索 .tvm0 段地址引用：

| 目标 | 搜索值 | 命中 |
|---|---|---|
| .tvm0_START_VA | 0x119DD000 | 0 |
| .tvm0_END_VA | 0x1393B000 | 0 |
| .tvm0_START_RVA | 0x019DD000 | 0 |
| .tvm0_END_RVA | 0x0393B000 | 0 |
| .tvm0 前 1MB VA page | 0x0119DDxx | 0 |
| .tvm0 RVA pattern | 0x0019DD | 2 (false positives) |

**Base.dll .text 中没有通过硬编码地址引用 .tvm0 的代码。**

### 替代模型：VM = Code Decryptor + Dispatch Controller

传统"VM bytecode interpreter"模型可能不适用。证据支持一个不同的模型：

```
.tvm0 (32MB) = 加密的 Engine code + control data
.tls (15.5MB, 可执行) = dispatch scheduler / control logic
.text (7.2MB) = 标准代码 (包含 TenProtect / Tenio framework)

VM 行为:
  Phase 1: 解密 .tvm0 中的 Engine code 到 gap (批量操作, t≈5s)
  Phase 2: 构建 96-entry dispatch table (原子操作, t≈7s)
  Phase 3: dispatch 0x00CA0000 (global init, t≈6.8s)
  Phase 4: dispatch 后续 Engine 函数 (条件控制, 当前阻塞点)

这个模型中没有:
  - bytecode interpreter
  - opcode fetch/decode
  - VM register file
  - VM stack

只有:
  - code decryptor
  - dispatch scheduler (可能驻留在 .tls)
  - indirect call mechanism
```

### 支持替代模型的证据

| 证据 | 支持 |
|---|---|
| Engine code 是完整 x86（不是 bytecode） | ✓ |
| 解密是批量操作（一次出现所有 probe） | ✓ |
| .text 无 .tvm0 引用 | ✓ |
| .tls 15.5MB 可执行（异常大） | ✓ |
| 96-entry table 原子填充 | ✓ |
| .tvm0 32MB >> Engine gap 3.08MB | ✓（含 control data） |
| Anchor A/B 在 .tls 中 | ✓（VM data） |

### "VM ISA" 概念可能不适用

如果 VM 是 code decryptor + dispatch controller：
- 没有 opcode/ISA 需要恢复
- 需要恢复的是：
  a) .tvm0 解密算法
  b) .tls 中的 dispatch scheduler 逻辑
  c) indirect call descriptor 格式
  d) condition/trigger mechanism

这是**不同类型**的逆向工程问题：
- 不是"理解 VM 指令集"
- 而是"理解解密算法 + 调度逻辑"

## Agent 分工结果汇总

| Agent | 目标 | 结果 |
|---|---|---|
| 1-4 | Interpreter 候选扫描 | .text 无 .tvm0 引用 |
| 5 | VM context/register frame | NOT_APPLICABLE (无 bytecode interpreter) |
| 6 | .tvm0 解密入口 | NOT_LOCATED |
| 7 | disk .tvm0 vs runtime Engine gap | 32MB vs 3.08MB, 批量解密 |
| 8 | Engine gap 填充时序 | t≈5.075s 批量出现 |
| 9 | 96-table construction | t≈7.056s 原子填充 |
| 10-12 | dispatch descriptor 来源 | NOT_LOCATED (in .tls or .tvm0) |
| 13-14 | VM→Engine 参数传递 | indirect call through dispatch table |
| 15-17 | Slot 41 / Resource / Event VM 行为 | 依赖 dispatch scheduler |
| 18 | scheduler/condition opcode | NOT_APPLICABLE (可能不是 opcode) |
| 19 | VM code/data separation | .tvm0=code+data, .tls=scheduler |
| 20 | 独立反证 | VM interpreter 模型可能不适用 |
| 21 | 最小 opcode 集合 | NOT_APPLICABLE |
| 22 | 总结 | 见上 |

## 建议方向（如继续）

如果继续，方向应该调整：

1. **不是"恢复 VM ISA"** → 而是"找到 .tls 中的 dispatch scheduler"
2. **不是"解密 .tvm0 bytecode"** → 而是"找到 .tvm0 解密 routine"
3. **不是"理解 opcode encoding"** → 而是"理解 indirect call descriptor 格式"

具体搜索目标：
- .tls 中的 large jump table / switch dispatch
- .tls 中引用 Engine gap 地址的代码
- .tls 中的 condition-based dispatch（if/switch on state）
- .tvm0 解密 routine（在 .text 或 .tls 中，使用 .tvm0 数据）

## Hard Stop 评估

VM interpreter（传统意义）= NOT_LOCATED。
但发现了更根本的问题：VM 的概念模型需要重新定义。

这不是一个"继续搜索就能找到"的情况。
这是一个"搜索方向需要根本性调整"的情况。

## 输出

- ICH057_DECISION.md
