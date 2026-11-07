# T2_4_MINIMAL_EXPERIMENT_PROTOCOL — 最小实验步骤、观测与逐项假设判定

**日期**：2026-10-10　**状态**：**方案，未执行。**
**授权**：见 [T2_4_RUNTIME_AUTHORIZATION_REQUEST.md](T2_4_RUNTIME_AUTHORIZATION_REQUEST.md)。**未获批准前，本文档任何步骤都不得执行。**

---

## 0. 总则

1. **一假设一判定**：H1–H7 **分别**定义前置、证据、通过、失败、中止。任一假设成立**不得**外推为另一假设成立。
2. **一步一中止**：每一步都可独立中止，中止后不进入下一步，不需要“先把本阶段跑完”。
3. **只读优先**：整个实验中**唯一的状态改变动作**是 E1 的 `--disable`。
4. **不猜补**：缺失的日志或未采集的状态一律记为 `not-collected`，**不得**用推断补齐。
5. **时间戳**：每步记录开始/结束时间（本地时间 + UTC 偏移）。

## 1. 阶段划分与授权边界

| 阶段 | 内容 | 触碰 CODOL？ | 独立授权 |
| --- | --- | --- | --- |
| **A** | 环境与构建前置（只读文件） | 否 | 与 A 之后各项一起批准 |
| **B** | 启动单个沙箱客户端 | **是**（启动） | **是** |
| **C** | 无害进程上的 Frida 运行时探针（H1） | **否** | **是**（可与 D/E 分开批准） |
| **D** | 只读 `status`（H2、H3） | **是**（附加，只读） | **是** |
| **E** | 一次 `--disable`（H4、H5、H6） | **是**（附加 + 状态改变） | **是** |
| **F** | 端口占用/重绑定检查（H7，可选） | 否（只读 + 一次 bind） | **是** |
| **G** | 收尾 | 视情况 | **是** |

> **C 可以且建议先单独批准并先执行**：它在无害进程上进行，却足以取得**第一次真实 Frida 运行时证据**。

## 2. 证据采集清单

| # | 证据 | 采集方式 | 能证明 | **不能**证明 |
| --- | --- | --- | --- | --- |
| E0 | 环境与版本 | `git rev-parse HEAD`、`git status`、`frida --version`、文件哈希 | 实验起点可复现 | 任何运行时行为 |
| E1 | 目录级构建前置 | `verify-target --game-dir E:\CODOL_SANDBOX\RUN001` | 磁盘上的目标文件是已批准构建 | 运行中的进程就是该文件 |
| E2 | 进程级身份指纹 | `tasklist`、`(Get-Process -Id <pid>).Path`、SHA-256、FileVersion | 附加前该 PID 的映像文件与路径等于基线 | 进程启动后未被内存改写；不是原子/密码学身份保证 |
| E3 | 工具 JSON + 退出码 + stderr | 工具调用原样落盘 | 工具的分类结论（confirmed/refused/unavailable/tool-error） | 插件内部状态本身 |
| E4 | 插件只读状态 | `status` 的 `after.installed / enabled / transport_bound / transport_port` | 调用后的插件状态 | “本次关闭了 socket”；OS 层是否释放 |
| E5 | 插件日志 | 只读 `Ayria\Logs\*.log` | 失败路径是否发生 | 未记录的事件不存在 |
| E6 | 操作后进程状态 | `tasklist`、窗口/崩溃观察 | 进程是否仍存活 | 退出是否干净 |
| E7 | 端口观测（可选） | `netstat -ano -p UDP` + 独立 `bind` 探针 | 28960 的当前归属与可否被重新绑定 | 该 socket 是否由本次调用关闭 |
| E8 | 产物哈希 | 对全部日志/JSON 计算 SHA-256 | 可审计性 | 结论正确性 |

## 3. 假设 H1–H7 逐项定义

### H1 — Frida 16.5.9 能执行修复后的脚本

拆成两个可分别判定的子项，避免把“API 存在”和“脚本能跑”混为一谈：

| 子项 | 前置 | 证据 | 通过标准 | 失败标准 | 中止条件 |
| --- | --- | --- | --- | --- | --- |
| **H1a** 运行时提供 `Module.findExportByName(moduleName, exportName)` | 无害进程在运行（Stage C） | C0 探针 JSON | `findExportByName_present = true`；`Module.findExportByName(null,'ExitProcess')` 返回**非空**指针；`Module.findExportByName(null,'<不存在的导出>')` 返回 **null 且不抛异常**；`findGlobalExportByName_present = false`（如实记录 16.5.9 上该 19+ API 不存在） | 任一不符：`false`、抛异常、或不存在的导出返回非空 | 探针抛异常或 5 秒内无回包 |
| **H1b** 出货脚本能在真实 Frida 运行时载入并执行 | 同上 | C1 工具调用 JSON | 工具返回 `result = unavailable` 且 `error` 含 `is not loaded in the target process`，退出码 **3** | 返回 `tool-error`(1)、`confirmed`(0) 或 `refused`(2)；或超时 | 出现 `tool-error`，或客户端外的进程被误伤 |

> **H1 的残留缺口（必须记录）**：C1 走到的是“插件未加载”分支，**没有**执行到 `Module.findExportByName(null, …)` 所在的终止钩子循环（该循环在插件查找之后）。因此**出货脚本真正执行那一行**只能在 **Stage D**（真实客户端、插件已加载）中观察到。H1a + H1b 只把“API 可用 + 脚本可载入”变成运行时事实。

### H2 — 工具能确认目标进程身份

| 项 | 内容 |
| --- | --- |
| 前置 | Stage B 已启动**恰好一个**沙箱客户端；E1 `verify-target` exit 0 |
| 证据 | E2 指纹四项 + D1 工具返回**不**是身份类 `unavailable` |
| 通过标准 | ① `tasklist /FI "IMAGENAME eq codoMP_client_shipRetail.exe"` 恰好 1 个 PID；② 该 PID 的 `.Path` == `E:\CODOL_SANDBOX\RUN001\codoMP_client_shipRetail.exe`；③ 该文件 SHA-256 == `36997674…537`；④ FileVersion == `1649370`；⑤ 工具未因 L1/L2/L3 任一层返回身份类 `unavailable` |
| 失败标准 | 任一项不符；PID 数 ≠ 1；任一值无法读取 |
| 中止条件 | 失败即中止（不进入 D 的后续判定） |

> **不得**把 H2 通过表述为“进程身份已得到密码学保证”。它是 名称 + 路径 + 哈希 的三重一致，仍有 PID 复用窗口。

### H3 — 能附加并找到所需的插件导出

| 项 | 内容 |
| --- | --- |
| 前置 | H2 通过 |
| 证据 | **D1 只读 `status`** 的 E3 + E4 + E5 |
| 通过标准 | 工具退出码 **0**、`result = confirmed`、`after.installed = true`，且 `after` 中 `transport_bound` / `transport_port` 存在；stderr 无附加/导出类错误 |
| 失败标准 | `unavailable`：`failed to attach`（附加失败）/ `is not loaded`（插件未加载）/ `does not export`（必需导出缺失，9 个必需导出任一）/ Frida 版本越界；或 `tool-error` |
| 中止条件 | 任一失败即中止；**不得**重试附加到其它 PID |

> 为什么用 `status`：脚本在动作分支**之前**就构造全部 9 个必需导出，因此 `status` 足以证明“附加成功 + 必需导出全部存在”，而**不改变任何插件状态**。

### H4 — `CODOL_GameServerSetEnabled(false)` 被实际调用并返回明确结果

| 项 | 内容 |
| --- | --- |
| 前置 | H3 通过 |
| 证据 | E1 `--disable` 的 E3（完整 JSON、退出码、stderr） |
| 通过标准 | `result ∈ {confirmed, refused}`：**两者都表示插件被调用并返回了布尔**。`confirmed` ⇒ 退出码 0；`refused` ⇒ 退出码 2 |
| 失败标准 | `result ∈ {unavailable, tool-error}` ⇒ 插件**未**被有效调用，H4 **不成立** |
| 中止条件 | 失败即中止；`refused` 属于“已得到明确结果但为否定”，**保留证据后中止**，不做第二次尝试 |

> **H4 通过 ≠ H5 通过**。`confirmed` 只说明插件返回了 `true`。

### H5 — 停止后 `transport.bound` 符合实现语义

| 项 | 内容 |
| --- | --- |
| 前置 | H4 成立（插件被调用并返回布尔） |
| 证据 | E2 只读 `status`（操作后）的 `transport_bound` / `transport_port` + E3 插件日志 |
| 通过标准（正分支） | `--disable` = `confirmed` ⇒ 操作后 `transport_bound = 0` 且 `transport_port = 0`，且日志**不含** `udp transport stop failed op=close` 与 `game server disable failed` |
| 通过标准（负分支） | `--disable` = `refused` ⇒ 操作后 `transport_bound = 1`（仍绑定）且日志**含** `udp transport stop failed op=close` **或** `game server disable failed: udp transport is still bound` |
| 失败标准 | `confirmed` 但 `bound = 1`（语义矛盾）；或 `refused` 但 `bound = 0`；或日志与返回值互相矛盾 |
| 中止条件 | 失败即**立即中止**（说明“成功”语义与实现不符） |

> `bound = 0` **不证明**“本次调用关闭了一个 socket”（句柄本已无效时 `close()` 也返回 true），也**不证明** OS 层端口已释放，更**不覆盖** 28961/28962。

### H6 — 操作后目标进程状态符合预期

| 项 | 内容 |
| --- | --- |
| 前置 | H4 已执行 |
| 证据 | E6 `tasklist`（操作后）+ 窗口/崩溃观察 + 插件日志 |
| 通过标准 | 进程**仍在**运行；PID 未变；无崩溃、无错误弹窗、无异常掉线；日志无未预期致命错误 |
| 失败标准 | 进程消失、PID 变化、崩溃、弹窗、掉线 |
| 中止条件 | 失败即中止，进入 [T2_4_ABORT_AND_RECOVERY_MATRIX.md](T2_4_ABORT_AND_RECOVERY_MATRIX.md) |

> 本阶段**不**终止该进程，因此 H6 只回答“停止请求之后客户端是否还活着”，**不**回答“进程能否正常退出”。

### H7 — 端口检查能区分“释放”与“其它原因”

| 项 | 内容 |
| --- | --- |
| 前置 | H5 已判定；**单独授权** |
| 证据 | F1 `netstat -ano -p UDP` 中 28960 的归属 PID；F2 独立 `bind` 探针的 `bound` 与**精确** `winerror` |
| 通过标准 | 落入 §4 一致性表中“一致”的两行之一，且错误码可明确归因 |
| 失败标准 | 落入“矛盾”行 |
| 中止条件 | 出现矛盾行即中止 |
| 不可判定 | 探针返回 `WSAEADDRINUSE` 以外的错误（如 `WSAEACCES` / `WSAEINVAL`），或 28960 由**第三方 PID** 持有 ⇒ 记为 **`inconclusive`**，**不得**据此宣称 H5 成立或不成立 |

## 4. H7 一致性判定表

前置事实（来自源码静态核对，必须记录）：生产 transport 由 `Appmain.cpp:2096 Network.start()` 使用**默认参数**启动 ⇒ 端口 **28960**、地址 **INADDR_ANY (0.0.0.0)**；socket 只设置 `SO_BROADCAST`，**未**设置 `SO_REUSEADDR`，也**未**设置 `SO_EXCLUSIVEADDRUSE`（`win_net.cpp:92-105`）。

| 操作后 `transport_bound` | `netstat` 28960 归属 | bind 探针（0.0.0.0:28960，不设 SO_REUSEADDR） | 判定 |
| --- | --- | --- | --- |
| `0` | 无任何 PID | `bound = true` | **一致：已释放** |
| `0` | **本客户端 PID** | `winerror = 10048` (WSAEADDRINUSE) | **矛盾 ⇒ 中止** |
| `0` | **第三方 PID** | `winerror = 10048` | **inconclusive**（他人占用，与本次调用无关） |
| `1` | **本客户端 PID** | `winerror = 10048` | **一致：仍绑定** |
| `1` | 无任何 PID | `bound = true` | **矛盾 ⇒ 中止** |
| 任意 | 任意 | `winerror ≠ 10048` 且 `bound = false` | **inconclusive**，记录精确错误码 |

**探针设计约束**（否则结论无效）：

1. **不得设置 `SO_REUSEADDR`**——Windows 上它允许第二个 socket 抢占已被占用的端口，会让“绑定成功”失去证据意义；
2. 必须绑定 **`0.0.0.0:28960`**（与 transport 的实际绑定地址一致），可另做一次 `127.0.0.1:28960` 作为参考；
3. 绑定成功后**立即关闭**，不发送任何数据报、不连接；
4. 必须记录**精确**的 `winerror`，不得只记“失败”。

## 5. 最小步骤（每步可独立中止）

### Stage A — 环境与构建前置（只读文件，不碰游戏）

| 步 | 动作 | 期望 | 不符则 |
| --- | --- | --- | --- |
| A1 | 记录 `git rev-parse HEAD`、`git status --porcelain -uall`、`build\stage` mtime | HEAD = `2a75bdd…`、status = 17、mtime = `2026-10-09 17:01:07` | **中止** |
| A2 | 记录 `frida --version` 与 `frida-tools` 版本 | frida 16.5.9，且 ∈ `[16.5,19)` | **中止** |
| A3 | 记录工具/配置/基线文件 SHA-256 | 等于 T-2.3 清单值 | **中止** |
| A4 | `verify-target --game-dir E:\CODOL_SANDBOX\RUN001` | exit 0，`ok: true` | **中止** |
| A5 | `netstat -ano -p UDP` 记录 28960/28961/28962 基线 | 三者**均空闲** | **中止**（残留进程） |

### Stage C — 无害进程上的 Frida 运行时探针（H1，不碰 CODOL）

| 步 | 动作 | 期望 | 不符则 |
| --- | --- | --- | --- |
| C1 | 启动一个无害进程并记录其 PID 与映像名（建议 `ping.exe -t 127.0.0.1`；备选 `powershell.exe -NoProfile -Command "Start-Sleep -Seconds 300"`） | 进程存在，PID 记录在案 | **中止** |
| C2 | 运行 **C0 探针**（§6.1 + §6.2）附加该 PID | 输出 §3 H1a 的全部字段，且满足 H1a 通过标准 | **中止**；**不得**改附加其它进程 |
| C3 | 运行**出货脚本载入探针**（§6.3）：把 `CODOL_CLIENT_EXECUTABLE` 设为该无害进程的映像名，调用工具 `--disable --pid <无害 PID> --sample-seconds 0` | `result = unavailable`、`error` 含 `is not loaded in the target process`、退出码 **3** | **中止** |
| C4 | 记录 C2/C3 的全部原始输出与哈希 | — | — |
| C5 | 关闭无害进程 | 进程消失 | 记录 |

> C3 会临时改写 `CODOL_CLIENT_EXECUTABLE`，**仅对这一次子进程生效**，绝不用于 Stage D/E。该步骤**不是** H2 的证据：身份校验此时被指向了一个合成名字。

### Stage B — 启动单个沙箱客户端（需授权）

| 步 | 动作 | 期望 | 不符则 |
| --- | --- | --- | --- |
| B1 | 以 `--game-dir E:\CODOL_SANDBOX\RUN001` 启动**一个** `dedicated` 角色客户端 | 进程出现 | 中止 |
| B2 | 记录 PID；`tasklist` 确认**恰好一个** | 恰好 1 个 | **中止** |
| B3 | 采集 E2 四项指纹并与基线逐项比对 | 四项全等 | **中止**（不进入 D） |
| B4 | 记录插件日志目录与现有日志 | 目录/文件存在性如实记录 | 记录（缺失不中止，但不得猜补） |

### Stage D — 只读 status（H2、H3）

| 步 | 动作 | 期望 | 不符则 |
| --- | --- | --- | --- |
| D1 | `python tools/runtime/CodolGameServerControl.py --pid <pid> --sample-seconds 0` | 退出码 **0**、`result = confirmed`、`after.installed = true` | 见 §3 H3 失败/中止 |
| D2 | 原样保存 stdout/stderr/退出码；提取 `transport_bound` / `transport_port` 作为 H5 基线 | — | — |
| D3 | 只读插件日志，记录 `udp transport stop failed` / `game server disable failed` 是否出现 | 出现与否如实记录 | 记录 |

### Stage E — 一次 --disable（H4、H5、H6）

| 步 | 动作 | 期望 | 不符则 |
| --- | --- | --- | --- |
| E1 | `python tools/runtime/CodolGameServerControl.py --disable --pid <pid> --sample-seconds 0` | `result ∈ {confirmed, refused}`，退出码 0 或 2 | 见 §3 H4 |
| E2 | 立即再次只读 `status`，记录 `transport_bound` / `transport_port` | 与 H5 分支一致 | 见 §3 H5 |
| E3 | 只读插件日志 | 与 H5 分支一致 | 见 §3 H5 |
| E4 | `tasklist` 记录进程是否仍存活（H6） | 仍在、PID 未变 | 见 §3 H6 |

### Stage F — 端口检查（H7，可选，需单独授权）

| 步 | 动作 | 期望 | 不符则 |
| --- | --- | --- | --- |
| F1 | `netstat -ano -p UDP` 记录 28960 的归属 PID（含“无”） | 有明确归属结论 | 记录 |
| F2 | 运行 §6.4 探针（`0.0.0.0:28960` 与 `127.0.0.1:28960`，不设 `SO_REUSEADDR`） | 返回 `bound` 与精确 `winerror` | 记录 |
| F3 | 按 §4 表判定：一致 / 矛盾 / inconclusive | 明确落格 | 矛盾 ⇒ **中止** |

### Stage G — 收尾

| 步 | 动作 | 期望 |
| --- | --- | --- |
| G1 | **默认不终止**客户端；由申请人报告后等待指示 | — |
| G2 | 若获授权终止：先按 [T2_4_ABORT_AND_RECOVERY_MATRIX.md](T2_4_ABORT_AND_RECOVERY_MATRIX.md) §R 复核，再单 PID `taskkill` | 复核通过才终止 |
| G3 | 对全部产物计算 SHA-256 并汇总 | — |

## 6. 探针源码（授权后由操作者落盘到沙箱临时目录；本轮**未**新增任何文件）

### 6.1 `frida_api_probe.js`（C0 的注入脚本）

``
'use strict';
const results = {
    findExportByName_present: typeof Module.findExportByName === 'function',
    getExportByName_present: typeof Module.getExportByName === 'function',
    findGlobalExportByName_present: typeof Module.findGlobalExportByName === 'function',
    imageName: Process.enumerateModules()[0].name,
    moduleCount: Process.enumerateModules().length,
    exitProcess: 'not-run',
    absentExport: 'not-run'
};
try {
    const found = Module.findExportByName(null, 'ExitProcess');
    results.exitProcess = (found === null) ? null : found.toString();
} catch (error) {
    results.exitProcess = 'THREW: ' + (error.message || String(error));
}
try {
    const missing = Module.findExportByName(null, 'codol_t24_no_such_export_xyz');
    results.absentExport = (missing === null) ? null : 'unexpected:' + missing.toString();
} catch (error) {
    results.absentExport = 'THREW: ' + (error.message || String(error));
}
send(results);
``

### 6.2 `frida_api_probe.py`（C0 的驱动）

``
import json, sys, time
from CodolFridaRuntime import configure_frida_runtime
configure_frida_runtime()
import frida

pid = int(sys.argv[1])
source = open(sys.argv[2], encoding='utf-8').read()
device = frida.get_local_device()
session = device.attach(pid)
script = session.create_script(source)
script.on('message', lambda message, data: print(
    json.dumps(message.get('payload', message), ensure_ascii=False)))
script.load()
time.sleep(1.0)
script.unload()
session.detach()
``

### 6.3 出货脚本载入探针（C3，无新文件）

``
$env:CODOL_CLIENT_EXECUTABLE = '<无害进程映像名>'      # 例如 ping.exe
python tools/runtime/CodolGameServerControl.py --disable --pid <无害 PID> --sample-seconds 0
Remove-Item Env:\CODOL_CLIENT_EXECUTABLE
``

### 6.4 `port_probe.py`（F2）

``
import socket

def attempt(address, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    result = {'address': address, 'port': port}
    try:
        # SO_REUSEADDR is deliberately NOT set: on Windows it would let this socket
        # bind a port another process already holds, making success meaningless.
        sock.bind((address, port))
        result.update(bound=True, error=None, errno=None, winerror=None)
    except OSError as error:
        result.update(bound=False, error=error.strerror, errno=error.errno,
                      winerror=getattr(error, 'winerror', None))
    finally:
        sock.close()
    return result

for address in ('0.0.0.0', '127.0.0.1'):
    print(attempt(address, 28960))
``

## 7. 假设 → 步骤 → 证据 映射

| 假设 | 步骤 | 证据编号 |
| --- | --- | --- |
| H1a | C2 | E3 + 探针 JSON |
| H1b | C3 | E3 |
| H2 | B3 + D1 | E2 + E3 |
| H3 | D1 | E3 + E4 + E5 |
| H4 | E1 | E3 |
| H5 | E2 + E3 | E4 + E5 |
| H6 | E4 | E6 |
| H7 | F1 + F2 | E7 |

## 8. 关联交付

- [T2_4_RUNTIME_AUTHORIZATION_REQUEST.md](T2_4_RUNTIME_AUTHORIZATION_REQUEST.md) · [T2_4_ABORT_AND_RECOVERY_MATRIX.md](T2_4_ABORT_AND_RECOVERY_MATRIX.md) · [T2_4_SHA256_MANIFEST.txt](T2_4_SHA256_MANIFEST.txt)
