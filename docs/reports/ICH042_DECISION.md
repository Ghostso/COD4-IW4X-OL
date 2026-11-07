# ICH-042 — Runtime VM Dispatch Anchor

## 核心结论

**RUNTIME_VM_CALLER = NOT_OBSERVED**

在 3 个已知 Engine targets (0x00CA0000, 0x00B00000, 0x009B9C00) 和
GetResourceManagerII 上，均无法在运行时捕获到 VM caller 的 return address。

## 实验过程

### 方法 1: C# Observer (ReadProcessMemory + GetThreadContext)

使用与 ICH-020/021 相同的 C# observer 方法：
- 启动 codoMP_client_shipRetail.exe -q
- 轮询 Engine gap (0x00CA0000, 0x00B00000, 0x009B9C00)
- 尝试通过 GetThreadContext 获取 RIP/ESP
- 结果：GetThreadContext 因线程访问权限被拒绝，无法获取寄存器
- 已知状态变化（0xE83C18 = 0x9B9C00）再次确认了 0x00CA0000 的执行
- 但无法获取 return address

### 方法 2: CDB 断点

使用 WinDbg CDB 设置硬件断点：
- bp 0x00CA0000 / bp 0x00B00000 / bp 0x009B9C00
- 附加调试器后进程启动
- TenProtect (TP3Shell) 反作弊检测到调试器存在
- 在 Engine gap 被填充（t≈5s）之前，
  进程因堆损坏 (HEAP[...]: Invalid address specified to RtlFreeHeap) 终止
- 断点从未被命中
- 多次尝试（-q / no -q, sxi * / sxe -c "g" *, 不同 g 计数）均产生相同结果

## 根本原因

```text
TP3Shell (Base.dll) 反作弊层检测到调试器附加
→ 触发堆损坏作为反调试保护
→ 进程在 VM bootstrap 阶段（Engine gap 填充之前）崩溃
→ Engine 代码从未被执行
→ 断点无法命中
```

## 结论

| 指标 | 状态 |
|------|------|
| RUNTIME_VM_CALLER | NOT_OBSERVED |
| VM_RETURN_CONTEXT | NOT_OBSERVED |
| VM_CONTINUATION | NOT_OBSERVED |
| ENGINE_TARGET_EXECUTED (no debugger) | YES (ICH-021 已确认) |
| ENGINE_TARGET_EXECUTED (under debugger) | NO |
| VM_PC_CANDIDATE | NOT_OBSERVED |
| DIAGNOSTIC_VM_RELATION | NOT_OBSERVED |

## 原因分析

在无调试器的运行中（ICH-020/021），Engine gap 正常填充，
0x00CA0000 正常执行并写入 0x009B9C00。

但获取 return address 需要以下条件之一：
1. 调试器附加（触发反调试，进程崩溃）
2. GetThreadContext 权限（TP3Shell 保护的进程拒绝了此访问）
3. 内核级 ETW/Intel PT（超出本轮用户模式范围）

三个条件均无法满足，因此无法捕获 VM caller 的 return address。

## 产出文件

- ICH042_DECISION.md
- ICH042_RUNTIME_ENGINE_CALLS.csv (空)
- ICH042_RETURN_CONTEXT.csv (空)
