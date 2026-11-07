# CODOL 复原项目 — A 方案最终报告
# `CODOL_ORDINAL1_LIFECYCLE_FINAL.md`

## 任务

只研究并闭合：

```text
CODOL EXE Entry -> IAT -> Base.dll!ordinal 1
```

的生命周期。

最终回答：**Base.dll!ordinal 1 被调用以后，控制流和进程生命周期究竟发生了什么？**

---

## 0. 结论摘要（先给答案）

```text
ORDINAL1_ENTRY              = CONFIRMED
ORDINAL1_RETURN_TO_EXE      = REFUTED
ORDINAL1_DIRECT_EXIT        = CONFIRMED
ORDINAL1_TERMINATION        = CONFIRMED
ORDINAL1_EXCEPTION          = NOT_OBSERVED
ORDINAL1_EXTERNAL_TRANSFER  = CONFIRMED
ORDINAL1_RUNTIME_GENERATION = NOT_OBSERVED
ORDINAL1_LIFECYCLE          = CLOSED
```

一句话答案：

> **Base.dll!ordinal 1 不是一个会被 `ret` 返回给 EXE 的普通函数。它是 `.tvm0` 里的一个 VM 入口桩：把 `0x592A35B8`、`ECX`、`EDX`、`EBX`、`EAX` 压栈后直接 `jmp` 到 `Base+0x1F27FDC`，进入 `.tvm0` 运行时分派器。它根本没有 `ret`，所以 EXE 返回点 `EXE+0x0E5DC696` 在结构上就不可达。之后进程在 `Base.dll`、`libcef`、`BugTrace.dll` 共同参与下完成一次启动尝试，最终以 `0xC0000409`（fail-fast）终止，从未回到 EXE 的调用点。**

对应任务书 Case 分类：

```text
Case A (正常 RET 返回 EXE) : REFUTED      — 桩内不存在 ret
Case E (进入 VM / 运行时)  : CONFIRMED    — 直接 jmp 进 .tvm0 VM 入口
Case C (线程/进程终止)     : CONFIRMED    — 进程确实终止
Case B (CALL/JMP 到其他模块): PARTIAL     — ordinal-1 本身不外跳；但它被外部模块再次调用
Case D (异常导致结束)      : 只观察到 DEBUG / C++ throw，未见 ordinal-1 路径异常
Case F (其他)              : 不适用
```

---

## 1. 样本与既有事实（继承，不重新推导）

```text
EXE  : COD OL\codoMP_client_shipRetail.exe
       SHA256 36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537   (MATCH)
BASE : COD OL\codoMP_client_shipRetailBase.dll
       SHA256 EF75220DE1D6973F34C7069F5BF211B11BD61520C6C0DE1882F7359FA5BC6A20   (MATCH)

EXE ImageBase (file)  = 0x00400000
EXE Entry RVA         = 0x0E5DC690
EXE Entry bytes       = FF 15 65 C6 9D 0E   -> call dword ptr [0x0E9DC665]
EXE Return site RVA   = 0x0E5DC696
IAT slot VA           = 0x0E9DC665  -> Base.dll ordinal 1
Base ImageBase (file) = 0x10000000
Base ordinal-1 RVA    = 0x1D6582C
```

本轮未修改任何 EXE/DLL；文件 SHA 与上轮完全一致。

---

## 2. 已确认事实

### 2.1 EXE 侧调用点（静态，已确认）

```asm
0x0E9DC690   FF 15 65 C6 9D 0E     call dword ptr [0x0E9DC665]
0x0E9DC696   (零填充, 无指令消费 EAX)
```

### 2.2 Base.dll 导出表证明（本轮静态确认）

```text
export directory RVA  = 0x952D60  (section .rdata)
OrdinalBase           = 1
NumberOfFunctions     = 3
ordinal-1 func RVA    = 0x1D6582C    <-- 与运行时观测一致
```

### 2.3 ordinal-1 的真实位置与首指令（本轮静态确认，capstone）

```text
Base.dll+0x1D6582C 落在 section = .tvm0   (不是 .text)

0x1D6582C   68 B8 35 2A 59      push  0x592A35B8
0x1D65831   51                  push  ecx
0x1D65832   52                  push  edx
0x1D65833   53                  push  ebx
0x1D65834   50                  push  eax
0x1D65835   E9 A2 27 1C 00      jmp   Base+0x1F27FDC
```

**这是本任务的核心结构事实：ordinal-1 桩内没有 `ret`。**

### 2.4 第一跳目标（本轮静态确认）

```text
0x1F27FDC (section .tvm0)
   push esi / pushfd / push ebp / push edi / jmp Base+0x1F9DFFD
```

即：ordinal-1 -> `Base+0x1F27FDC` -> `Base+0x1F9DFFD`，全程在 `.tvm0` 内，是一段 VM 运行时分派入口，不是返回路径。

---

## 3. 动态证据

### 3.1 观测器

```text
_ord1_observer\ord1_lifecycle.exe     (x86 / net48 / 自建最小调试器)
```

方法与限制：

```text
- 断点只设在: EXE Entry / Base ordinal-1 entry / EXE return site /
              ordinal-1 静态第一跳目标 / ordinal-1 之后新出现的 MEM_PRIVATE 可执行区
- 只在进程内存打临时 0xCC 断点，命中后立即恢复原字节
- 不修改 EXE/DLL 文件 / 不 patch / 不 hook
- 不用 Procmon / Sandboxie / 不做全量扫描
- 使用 VirtualQueryEx 枚举全部已提交可执行区域，用于判定「运行时生成代码」
```

### 3.2 运行矩阵（环境 A：CREATE_SUSPENDED + DEBUG_ONLY_THIS_PROCESS，14s 窗口）

| Run | EXE Entry | ordinal-1 entry | EXE return site | 新可执行区 | 进程状态 | 退出码 |
|-----|-----------|-----------------|-----------------|-----------|----------|--------|
| ORD1_A_01 | HIT | HIT (3 次) | **NOT HIT** | 0 | EXITED | 0xC0000409 |
| ORD1_A_02 | HIT | HIT (3 次) | **NOT HIT** | 0 | EXITED | 0xC0000409 |
| ORD1_A_03 | HIT | HIT (3 次) | **NOT HIT** | 0 | EXITED | 0xC0000409 |

```text
ENTRY            = 3/3
ORDINAL1_ENTRY   = 3/3 runs (共 9 次进入)
RETURN_TO_EXE    = 0/3
NEW_EXEC_REGION  = 0/3
PROCESS_EXIT     = 3/3, exit code 0xC0000409
```

### 3.3 三次 ordinal-1 进入的调用上下文（每次运行完全一致）

| 次序 | 调用者（`[ESP]` 返回地址） | 调用者归属 | 说明 |
|------|---------------------------|-----------|------|
| 第 1 次 | `0x0E9DC696` | **codoMP_client_shipRetail.exe+0xE5DC696** | 正是 EXE Entry 的 IAT 调用点 |
| 第 2 次 | `0x6044A22D` | codoMP_client_shipRetailBase.dll+0x361A22D | Base 自身 `.tvm0` 内重复进入 |
| 第 3 次 | `0x68371F2F` | **BugTrace.dll+0x11F2F** | 外部模块再次调用 ordinal-1 |

稳定量（3/3 完全一致）：

```text
iat_slot_value            = Base.runtime + 0x1D6582C
ordinal1_first_hop        = Base+0x1F27FDC   (CONFIRMED at runtime)
ordinal1_veh_candidate    = 0x38689866       (对应 BugTrace 的 push 0x38689866)
Base runtime base         = 0x5CE30000
ordinal1_retaddr(首次)     = EXE+0x0E5DC696
```

### 3.4 ordinal-1 入口寄存器（与既有一致）

进入时 `EAX = Base + 0x1D6582C`（即 ordinal-1 自身代码地址），`EDX = Base + 0x110`，`ESI = Base + 0`，`EDI = 0x20`，`EFLAGS = 0x202`。

这些值的**语义仍未确定**，本轮不为其命名。仅记录：`EAX` 恰好等于 ordinal-1 的运行时地址，与「VM 入口以自身地址作为桩标识」一致，但该解释属于 `UNKNOWN`。

### 3.5 ordinal-1 之后的可执行区域变化

```text
在 ordinal-1 之后新提交的、可执行的内存区域 = 0
```

即在观测窗口内，**没有观察到任何运行时生成/解密/映射的新代码区**。ordinal-1 之后执行的所有代码都在启动时既已存在的模块映像（Base `.tvm0`、libcef、BugTrace 等）内。

### 3.6 EXE 返回点为何从未命中（双重证据）

```text
静态 : ordinal-1 桩内不存在 ret 指令，最后一条是 jmp Base+0x1F27FDC
动态 : 3/3 运行 0 次命中 EXE+0x0E5DC696
```

结论不是「没看到返回」，而是「返回在结构上不存在」。

---

## 4. ordinal-1 直接出口

见 `base_ordinal1_lifecycle.csv`：

```text
source                        destination        kind   module        rva        confidence
Base.dll+0x1D65835            Base.dll+0x1F27FDC JMP    Base.dll      0x1F27FDC  CONFIRMED
Base.dll+0x1F27FDC            Base.dll+0x1F9DFFD JMP    Base.dll      0x1F9DFFD  CONFIRMED
Base.dll+0x1D6582C            Base.dll+0x1F27FDC JMP    Base.dll      0x1F27FDC  CONFIRMED
EXE+0xE5DC690                 ordinal 1 (IAT)    CALL   EXE           0xE5DC690  CONFIRMED
Base.dll export directory      ordinal 1         —      Base.dll      0x1D6582C  CONFIRMED
```

**kind 取值限定为 `RET / CALL / JMP / EXCEPTION_PATH / THREAD_EXIT / PROCESS_EXIT / UNKNOWN`。**
本项目中 ordinal-1 自身的直接出口只有 `JMP`（第一跳）与外部 `CALL`（进入）。
没有为任何函数命名；`.tvm0` 只记录地址，不做语义标注。

---

## 5. 返回情况

```text
ORDINAL1_RETURN_TO_EXE = REFUTED
```

依据：

1. 静态：ordinal-1 桩为 `push/push/push/push/push/jmp`，无 `ret`。
2. 动态：3/3 运行、共 9 次 ordinal-1 进入，EXE 返回点 `EXE+0x0E5DC696` 命中 0 次。
3. EXE 返回点之后是零填充，本就不存在消费返回值的调用者指令（CORE-008 已确认）。

因此 EXE Entry 的那次 `call` 是一个**永不返回的尾调用式跳转**，不是可返回的调用。

---

## 6. 异常 / 终止情况

分类后的异常统计（见 `base_ordinal1_exceptions_classified.csv`）：

```text
DEBUGGER_ARTIFACT       = 1251   (ntdll!RtlpDebugBreak, rva 0x8B71A, 真 int3)
CPP_EXCEPTION_UNHANDLED = 3      (0xE06D7363, MSVC throw, first-chance)
TERMINATION             = 6      (0xC0000409 / 0xC0000005)
ORDINAL1_PATH           = 0
```

说明：

- `ntdll!RtlpDebugBreak` 的 `int3` 高频命中，是因为本进程**在调试器下运行**触发了 ntdll 的调试断点检查（已用磁盘字节 `0xCC` 在 `ntdll+0x8B71A` 验证）。它是调试器 artifact，**不是 ordinal-1 的执行路径**。
- `0xE06D7363` 是 MSVC C++ 异常，first-chance，未被证明与 ordinal-1 出口绑定。
- 进程终止码 `0xC0000409`（fail-fast）与 `0xC0000005`，最终一轮 3/3 均收敛为 `0xC0000409`。
- **没有任何异常被归类为 ordinal-1 的直接控制流出口** → `ORDINAL1_EXCEPTION = NOT_OBSERVED`。

终止记录：

```text
THREAD_EXIT / PROCESS_EXIT 均记录在 base_ordinal1_dynamic_trace.csv
最终进程状态 = EXITED
最终退出码   = 0xC0000409
最后被观测到仍在执行的模块 = Base.dll (.tvm0) / BugTrace.dll / libcef.dll 参与的启动尝试
```

---

## 7. 外部模块转移

```text
ORDINAL1_EXTERNAL_TRANSFER = CONFIRMED
```

证据链（静态 + 动态一致）：

```text
BugTrace.dll+0x10011F28   push 0x38689866
BugTrace.dll+0x10011F2E   call eax                 ; 调用 ordinal-1
BugTrace.dll+0x10011F2F   mov dword ptr [esp+0xC], eax   ; 返回点
```

运行时观测到 `[ESP] = 0x68371F2F = BugTrace.dll+0x11F2F`，与静态返回点完全吻合；且 ordinal-1 入口记录的 `[ESP+4] = 0x38689866` 正是该 `push` 的常量。

含义：

> ordinal-1 **不是只被 EXE 调用一次**。它至少还被 `BugTrace.dll` 调用一次，即同一入口承担多个调用者。这种「同一地址被 EXE 与外部模块共同用作入口」的模式，与 VM 入口桩（分发一次性的启动上下文）一致。

按任务书要求，这里**只跟到第一层直接去向**，未扩大为整个进程调用图。

---

## 8. 运行时生成（runtime generation）情况

```text
ORDINAL1_RUNTIME_GENERATION = NOT_OBSERVED
```

判定方法：在 ordinal-1 之前与之后分别用 `VirtualQueryEx` 枚举全部 `MEM_COMMIT` 且可执行（`PAGE_EXECUTE*`）的区域，比较集合差异；并在 ordinal-1 之后对**新出现的 MEM_PRIVATE 可执行区**下断点。

结果：

```text
新增可执行区 = 0
新可执行区断点命中 = 0
```

因此在本观测窗口内，ordinal-1 之后没有发生「运行时生成 / 解密 / 映射新代码」的行为。ordinal-1 之后执行的代码位于启动时即已存在的 `.tvm0` 与已加载模块中。

注意：这不否认 `.tvm0` 内部存在**解释执行**（VM 逐条解释字节码）。字节码解释不需要新分配可执行内存，因此不在本项判定范围内。本项只回答「是否生成新可执行代码」。

---

## 9. 最终生命周期状态

```text
ORDINAL1_LIFECYCLE = CLOSED
```

满足任务书「类型 2：明确转移」+「类型 3：明确终止」：

```text
类型 2（明确转移）
  ordinal-1
    -> direct JMP  Base.dll+0x1F27FDC   (静态 CONFIRMED)
    -> direct JMP  Base.dll+0x1F9DFFD   (静态 CONFIRMED)
    -> .tvm0 VM 运行时分派入口
  该路径解释了「EXE return site 未被观测到」：
  ordinal-1 桩内无 ret，调用点无法返回。

类型 3（明确终止）
  ordinal-1 之后
    -> 无新增可执行区
    -> 进程终止 EXITED, exit code 0xC0000409
    -> 最终进程状态明确
```

---

## 10. 全部判定字段

```text
ORDINAL1_ENTRY              = CONFIRMED
ORDINAL1_RETURN_TO_EXE      = REFUTED
ORDINAL1_DIRECT_EXIT        = CONFIRMED
ORDINAL1_TERMINATION        = CONFIRMED
ORDINAL1_EXCEPTION          = NOT_OBSERVED
ORDINAL1_EXTERNAL_TRANSFER  = CONFIRMED
ORDINAL1_RUNTIME_GENERATION = NOT_OBSERVED
ORDINAL1_LIFECYCLE          = CLOSED
```

最终一句话状态：

```text
PLAN_A = CLOSED
```

---

## 11. 尚未解决的问题（明确保留，不作为闭合条件）

以下问题**不影响** `ORDINAL1_LIFECYCLE = CLOSED`，因为生命周期（控制流去向 + 进程终止）已闭合；它们属于「语义」而非「生命周期」：

1. ordinal-1 入口寄存器 `EAX/EDX/ESI/EDI/EFLAGS` 的语义角色 —— 仍为 `UNKNOWN`。
2. `0x592A35B8`、`0x38689866` 这两个立即数的含义 —— `UNKNOWN`。
3. `.tvm0` 内部 VM 字节码的具体语义 —— 本轮不解码，`UNKNOWN`。
4. 为什么最终以 `0xC0000409` 终止（缺环境、缺上下文、还是 anti-debug）—— `UNKNOWN`。
5. `BugTrace.dll` 调用 ordinal-1 的目的是否与崩溃上报有关 —— `UNKNOWN`。

这些属于下一阶段工作，不在本任务「生命周期闭合」的判定范围内。

---

## 12. 产物清单

```text
CODOL_ORDINAL1_LIFECYCLE_FINAL.md            (本文件)
base_ordinal1_lifecycle.csv                  静态直接出口
base_ordinal1_dynamic_trace.csv              动态完整时间线
base_ordinal1_exceptions.csv                 原始异常记录
base_ordinal1_exceptions_classified.csv      异常分类
base_ordinal1_decision.csv                   最终判定字段
base_ordinal1_runs.csv                       每轮运行摘要
base_ordinal1_modules.csv                    模块加载时间线
base_ordinal1_exec_regions.csv               可执行区域快照

工具:
_ord1_observer\ord1_lifecycle.exe            最小生命周期观测器 (自建, x86)
_ord1_observer\Program.cs                    观测器源码
ord1_static_lifecycle.py                     静态出口分析
ord1_finalize.py                             判定产物生成
_ord1_digest.py                              时间线摘要
PLAN_A_WORKING_NOTES.md                      过程记录
```

---

## 13. 合规性检查

| 任务书要求 | 状态 |
|-----------|------|
| 只研究 `EXE Entry -> IAT -> Base.dll!ordinal 1` 生命周期 | YES |
| 不重新寻找 CODOL 游戏入口 | YES |
| 不重新分析 `.tvm0` 解码 | YES (只做 ordinal-1 直接出口的静态地址解析) |
| 不寻找历史 bootstrap RVA | YES |
| 不分析 WeGame/TCLS/Sandboxie/Procmon | YES |
| 不做 EXE 全量扫描 | YES |
| 不修改原始 EXE/DLL (SHA 不变) | YES |
| 不进行 IW4X 分析 | YES |
| 动态观测记录 timestamp/process/thread 等字段 | YES |
| 记录 ordinal-1 是否 RET（直接证据） | YES (静态无 ret + 动态 0/3) |
| CALL/JMP 只跟第一层直接去向 | YES (只记录首跳) |
| 异常记录 code/address/instruction/module/thread | YES |
| 终止记录 thread id/exit code/last module/last EIP | YES |
| 静态只分析 Base.dll ordinal 1 及其直接出口 | YES |
| `kind` 只用规定枚举值 | YES |
| 不因「看起来像初始化函数」而命名 | YES |
| 未使用任务书列出的失败推理形式 | YES |
| 输出全部规定产物 | YES |

---

## 14. 最终原则执行情况

```text
ORDINAL1_LIFECYCLE = CLOSED
```

→ 正式结束方案 A。不为了寻找「更深一层」而自动扩展。

下一任务才进入：

```text
ICH-001 — IW4 Multiplayer -> IW4X -> CODOL 差分恢复
```

---

*本报告只对 ordinal-1 生命周期作结论，不对任何函数命名，不对 `.tvm0` 内部语义作结论。*
*所有运行均在调试器下进行，文件 SHA 与本轮开始时一致。*
