# OOB_STATE_MACHINE_IMPLEMENTATION — 独立模块与接口设计

**模块根：** `CODOL-BATTLE-OOB-STATE-035`
**目标：** 在**独立 WorkCopy** 中实现 OOB 状态机的**已确认子集**，可单独编译、可单独测试。
**未做的事：** 未改动 FREEZE-005、未改动 `CODOL-Combat-Server-v0.1`、未启动游戏、未执行真实客户端 E2E。

---

## 1. 交付的源码（12 个 .cs + 2 个 .ps1）

| 文件 | 职责 | 对应证据 |
|---|---|---|
| `src\OobWire.cs` | **线缆字面量表**（命令/令牌/键/错误码/终止符），全部逐字节来自目标镜像 | `evidence\oob_literals_exact.out.txt`、`branch_literals_full.out.txt` |
| `src\TokenComparer.cs` | 令牌比较模型（ASCII 折叠、比到 NUL、独立于长度） | `evidence\string_helpers.out.txt`（helper `0x3745E0`） |
| `src\SprintfSubset.cs` | 最小 `%s` 替换器（目标用 vsprintf，非 C# `{0}`） | `0x374900` → `0x83C5E6` |
| `src\IThrottleClock.cs` | **可注入时钟**接口 + `ManualClock`（测试用） | 测试接缝（非目标代码） |
| `src\ThrottleGate.cs` | 节流纯逻辑（3000/100/500，**双时间源分离**） | `evidence\oob_branch_throttle.out.txt` |
| `src\OobSendDecision.cs` | 决策结果类型（`OobSendKind` / `OobGateReason`） | — |
| `src\OobSendStateMachine.cs` | **状态判定 + 三级门 + 分支选择**（与解析分离） | `0x1C05F0` 全函数 |
| `src\OobReceiveClassifier.cs` | **接收令牌识别**（只返回令牌，不做状态变更） | `evidence\receiver_chain.out.txt` |
| `src\ServerClientState.cs` | **服务器自有**状态枚举（与客户端门强制分离） | 任务书 §三.8 |
| `src\CancelConnectHandler.cs` | `cancelConnect` 最小清理模型 | `0x1BF1C0` |
| `src\SelfTest.cs` | 离线自测（TV-01..TV-06 + 健壮性） | 本任务 |
| `src\build.ps1` / `src\run_selftest.ps1` | 构建与运行脚本 | 本任务 |

---

## 2. 接口设计

### 2.1 状态判定（已确认子集）

```csharp
public sealed class OobSendStateMachine
{
    public OobSendStateMachine(ThrottleGate throttle);

    // clientState = 客户端进程全局 0x076446B0 的值（数字，语义 UNKNOWN）
    // hasSession / sessionBusy = 门 2 的两个条件
    public OobSendDecision Decide(int clientState, bool hasSession, bool sessionBusy);

    // 只构造"已确认完整"的 payload；state 4/5 故意返回 null
    public string BuildConfirmedPayload(OobSendKind kind, string challengeSeed);

    public ThrottleGate Throttle { get; }
}

public sealed class OobSendDecision
{
    public readonly OobSendKind Kind;     // None / GetChallenge / Connect / Stats / Heartbeat
    public readonly OobGateReason Reason; // Ok / StateNotEligible / NoSessionOrBusy / Throttled
    public bool ShouldSend { get; }
}
```

**关键设计点：** `Decide` **不**读取任何全局、**不**读时钟、**不**记录任何状态；
它是一次**纯函数式判定**（`ThrottleGate` 内的时钟是唯一注入依赖）。

### 2.2 节流（纯逻辑 + 注入时钟）

```csharp
public interface IThrottleClock { long NowMs { get; } }
public sealed class ManualClock : IThrottleClock { void Advance(long); void Set(long); }

public sealed class ThrottleGate
{
    public const int MsState34 = 3000;  // 0xBB8
    public const int MsState5  = 100;   // 0x64
    public const int MsState6  = 500;   // 0x1F4

    // 双时间源分离：刻意不合并
    public long LastStateTimeMs;    // 镜像 [ebx+0x30] —— 只有 3000 用它
    public long LastCommandTimeMs;  // 镜像 [ebx+0x08] —— 只有 100/500 用它

    public static int ThresholdFor(int clientState);
    public bool IsAllowed(int clientState);
    public void OnAllowed(int clientState);  // 放行后的记账
}
```

**为什么保留两个时间源：** 目标对 3000 读 `[ebx+0x30]`、对 100/500 读 `[ebx+0x08]`；
合并成一个"上次发送时间"会在语义未证实的情况下**改变行为**（TV-05 中有一条断言专门守这一点）。

### 2.3 接收识别（只识别，不变更状态）

```csharp
public enum OobReplyToken { Unrecognised, ChallengeResponse, ConnectReject,
    ConnectResponse, HeartbeatResponse, StatResponse, DisconnectAck, Echo }

public static class OobReceiveClassifier
{
    public static OobReplyToken Classify(byte[] payload, int offset, int length);
    public static bool HasTerminator(byte[] payload, int offset, int length, string token);
}
```

**刻意不做：** 不返回"新状态"，不触发转移，不缓存会话。目标分支体未追踪，任何状态变更都会是**发明**。

### 2.4 `cancelConnect`

```csharp
public sealed class CancelConnectHandler
{
    public ServerClientState Handle(string sessionId, string cancelTargetSessionId,
                                    ref ServerClientState current);
}
```
规则：**仅当 `sessionId == cancelTargetSessionId`（Ordinal）时**把当前会话置为 `Closed`；
空 `sessionId` 为 no-op；**永不**返回 `Connected`。

### 2.5 服务器状态（与客户端门分离）

```csharp
public enum ServerClientState { None = 0, ChallengeIssued = 1, Connected = 2, Closed = 3 }
```
`SelfTest` 中有断言确保：**该枚举与客户端门值不是同一空间**，且 `Connected != 客户端状态 3`。

---

## 3. 构建

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File "D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-OOB-STATE-035\src\build.ps1"
```

- 编译器：`C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe`（与 FREEZE-005 同一工具链，无需额外依赖）
- 语言级别：**C# 5 / .NET Framework 4.0**（因此**不使用**数字分隔符 `10_000` 等新语法；
  这曾导致一次编译失败，已修正，见 §5）
- 输出：`build\bin\OobStateMachine.exe`（19,456 B）

**构建输出（实测）：**
```
csc      : C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe
sources  : 10
BUILD OK -> ...\CODOL-BATTLE-OOB-STATE-035\build\bin\OobStateMachine.exe
```

---

## 4. 运行

```powershell
& "D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-OOB-STATE-035\build\bin\OobStateMachine.exe"
```

**结果：`pass=84 fail=0`，`RESULT: ALL GREEN`，exit code `0`。**

| 产物 | SHA-256 |
|---|---|
| `build\bin\OobStateMachine.exe`（19,456 B） | `5f7841416565f183d9f353c2a0390a526e3b1e92bdb42ec197e4523bccb93aa3` |
| `build\selftest.output.txt`（运行 1） | `624662058e494e8893b36337ec2bf85cebdad451ef9d8a5e7ff9962592f073dd` |
| `build\selftest.run2.txt`（运行 2） | `624662058e494e8893b36337ec2bf85cebdad451ef9d8a5e7ff9962592f073dd` |

**确定性：** 两次运行的输出 SHA-256 **完全相同** ⇒ 自测是**确定性**的。

**⚠ 可重复性边界（如实声明）：** 本次使用的 `csc.exe`（.NET Framework 4.0）**不支持 `/deterministic`**，
因此 **EXE 的 SHA-256 可能随构建变化**。本任务以 **源码 SHA-256 + 构建命令 + 测试输出** 作为可重复性依据
（做法与 FREEZE-005 §8 一致），**不**宣称 EXE 逐位可复现。

---

## 5. 构建/测试中发现并修复的缺陷（如实记录）

| 轮次 | 缺陷 | 结果 | 修复 |
|---|---|---|---|
| 第 1 次构建 | `SelfTest.cs` 使用了 C# 7 数字分隔符 `10_000`，csc 4.0 报 `CS1026/CS1002/CS1525` | 构建失败 | 改为 `10000` |
| 第 1 次运行 | TV-01 断言"payload == `getchallenge 0 "abc123"`"**失败**——实现误用 C# `string.Format("{0}")` 去填目标的 **`%s`** 格式串 | `pass=83 fail=1` | 新增 `SprintfSubset.FormatS` 忠实替换 `%s`；重建后 `pass=84 fail=0` |

> 第 2 条**正是**测试的价值所在：它抓出了一个"把 C# 格式化套到 C 格式化串上"的真实实现错误。
> 若当时放宽断言，模块会产出**错的线缆字符串**。

---

## 6. 集成姿态

- 本模块**独立编译**，**不引用** `CODOL-Combat-Server-v0.1` 的任何类型。
- 因此集成是**可逆的**：见 `SERVER_INTEGRATION_GAP.tsv` 的最小集成方案。
- **保留旧协议模式**：模块不替换任何既有逻辑；接入需在配置门后（`GAP-INT-*`）。
- **不声称**真实客户端兼容（未执行任何 E2E）。
