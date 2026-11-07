# BOOKING_RUNTIME_TRACE-001

> 运行期观测阶段 001
> 目标：真实执行到 6/14 时捕获 `0x632680` 入口及调用栈
>
> 结论先行：
>
> ```
> INSTRUMENTATION_BLOCKED
> BOOKING_HANDLER_RUNTIME = NOT_OBSERVED
> RESPONSE_CHANNEL        = NOT_ESTABLISHED
> ```
>
> 原因：当前可用的运行期链路是**只读内存快照**，
> 不具备指令级断点与寄存器捕获能力；
> 唯一具备该能力的 Frida 不能在受 ACE 保护的进程上使用，
> 且 Golden 手册禁止规避/触碰 ACE。

---

## 0. 本轮未被违反的纪律

```
Server 修改              = 无
Golden 修改              = 无
4 个 Lobby patch 修改    = 无
KDF hook 修改            = 无
6/14 request 修改        = 无
client state 修改        = 无
patch / NOP / force      = 无
Booking response 发送    = 无
游戏启动                 = 无
```

本轮**没有启动游戏进程**，因此不存在被观测目标的运行期副作用。

---

## 1. 观测目标回顾

需要捕获的内容：

```
P0  0x632680 入口：EAX/ECX/EDX/EBX/ESI/EDI/EBP/ESP
    + [ESP+4]/[ESP+8]/[ESP+C]/[ESP+10]/[ESP+14]
P1  0x632736 / 0x632745 的 [ESP+0x28]
P2  0x62F902 的 [this+0xE360] 与 item+0x168/+0x16C
P3  0x62F6F0 的 A/B 与 item pointer
P4  0x632680 的 CALLER / RETURN ADDRESS / 4 个参数
P5  socket / dispatcher / packet buffer
P6  success branch 或 reject branch
```

以上全部要求**指令级执行断点**与**寄存器上下文读取**。

---

## 2. 现有运行期工具链评估

### 2.1 提权代理可用

```
python -X utf8 CODOLServer\_mainline\agent_client.py ping

{
  "ok": true,
  "pid": 11012,
  "debug_privilege": true,
  "debug_err": 0
}
```

`SeDebugPrivilege` 已启用。权限不是瓶颈。

### 2.2 内存观测器是只读快照

`CODOLServer\_mainline\_dyn100_mem.py` 的能力清单：

```
CreateProcessW(CREATE_SUSPENDED)     ← 抢在 ACE 之前拿句柄
OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ)
ResumeThread
VirtualQueryEx
ReadProcessMemory
```

显式说明（该文件自身注释）：

```
Read-only observation only
no write, no inject, no patch
Nothing is written to the target
```

### 2.3 断点/寄存器能力扫描结果

对 `_dyn100_mem.py` 全文搜索以下符号：

```
DebugActiveProcess      = 0
WaitForDebugEvent       = 0
GetThreadContext        = 0
SetThreadContext        = 0
WriteProcessMemory      = 0
CreateRemoteThread      = 0
SetWindowsHookEx        = 0
SuspendThread           = 0
ResumeThread            = 1（仅用于 CreateProcess(SUSPENDED) 后放行）
```

结论：

```
现有链路只能读取内存镜像，不能停在任何指令地址，
不能读取寄存器，不能读取 [ESP+n] 调用参数。
```

### 2.4 为什么不能改用 Frida

本机已安装 Frida：

```
C:\Users\Z5-CT5N1\AppData\Local\Programs\Python\Python311\Scripts\frida.exe
C:\Users\Z5-CT5N1\AppData\Local\Programs\Python\Python311\Scripts\frida-trace.exe
```

但目标是 CODOL 原始客户端，受 ACE / TenProtect 保护。
Golden 手册 §4 明确写明：

```
项目纪律：禁止关闭/停止/配置/规避 ACE、TenProtect
（历史实测蓝屏 0x01010002）。
```

在 ACE 保护进程上注入 Frida agent 属于规避/触碰 ACE 保护的行为，
不在本阶段允许范围内。因此不能使用。

### 2.5 判定

```
观测能力不足 = 真实存在
权限不足     = 否
```

因此按第五阶段 P8 收束条件 D：

```
INSTRUMENTATION_BLOCKED
```

必须如实记录，不用猜测填补。

---

## 3. 运行期清单（本轮实际值）

| 项目 | 本轮结果 |
|---|---|
| 6/14 timestamp | NOT_OBSERVED（未启动游戏） |
| selected_index | NOT_OBSERVED |
| reservation item | NOT_OBSERVED |
| A/B（运行期实际） | NOT_OBSERVED |
| mmbook request | NOT_OBSERVED |
| response arrival | NOT_OBSERVED |
| response channel | NOT_ESTABLISHED |
| `0x632680` caller | NOT_OBSERVED |
| five arguments | NOT_OBSERVED |
| success/reject branch | NOT_OBSERVED |
| retry behavior | NOT_OBSERVED |

辅助事实（静态已确认，非运行期实测）：

```
0x632680 入口   = thiscall, ret 0x14
0x632736 成功分支
0x632745 [esp+0x28] = 1
0x62F902 [this+0xE360] = ARG2
0x62F6F0 A = [item+0x168], B = [item+0x16C]
```

这些是**断点设置依据**，不是本轮观测结果。

---

## 4. 达成收束条件 D 的完整证据链

```
① 目标要求寄存器级入口观测
② 现有工具只有 ReadProcessMemory 快照
③ 断点相关 API 命中 = 0
④ 具备断点能力的 Frida 被 ACE 保护策略禁止使用
⑤ Golden 手册明令不得规避 ACE
⇒ 观测无法在不违反纪律的前提下进行
⇒ INSTRUMENTATION_BLOCKED
```

本轮**没有**得到：

```
RESPONSE_ENTRY          = OBSERVED
real caller             = 未获得
five arguments          = 未获得
response channel        = 未获得
```

因此不得写入任何伪造的 socket / port / packet 结论。

---

## 5. 下一阶段解锁条件

运行期阶段 002 若仍要推进，必须先满足以下**任一**条件：

```
条件 1：
  提供一个不触碰 ACE 保护的观测通道
  （例如客户端自身日志、服务端侧观测、外部网络抓包、
    或由用户明确批准的安全调试环境）。

条件 2：
  明确书面批准在 ACE 共存模式下使用硬件断点工具，
  并接受相应风险（Golden 手册当前禁止此操作）。

条件 3：
  提供一个已退 ACE 的独立分支环境用于观测。
```

满足任一条件后，断点计划为：

```
0x632680  入口      读 8 个通用寄存器 + [ESP+4..+0x14]
0x632736  成功分支
0x632745  写 [ESP+0x28]=1
0x62F902  写 [this+0xE360]
0x62F6F0  写 A/B
```

在条件满足前，不得继续静态扫描，也不得发送任何响应。

---

## 6. 环境状态

```
提权代理          = pid 11012, ok=true, debug_privilege=true
codoMP 进程       = 0 个
3074 / 28960 监听 = 0
Golden 哈希       = 未变（见提交前核对）
```

本轮未产生任何游戏进程、网络连接或客户端状态改变。

