# T2_5_RUNTIME_VERIFICATION_REPORT — 真实客户端控制链与服务器运行验证

**日期**：2026-10-10
**工作树**：**F = `F:\桌面\ol\ol-mod-olfinal`**（HEAD `2a75bdd8872bb9f54006382a924c3006ec9affc2`，分支 `OLfinal-live`）
**本轮实际执行**：**仅阶段 1（只读预检）**。
**未执行**：Stage D / E / F / T。**未启动、未附加、未注入、未读取、未终止任何 CODOL 进程。**

---

## 0. 结论摘要

> **阶段 1 全部 8 项 PASS**（P1.1–P1.8），基线零漂移。
>
> **但真实控制链证据为 0 条**：本轮没有向任何 CODOL 进程附加，因此**尚未取得**目标身份（运行时）、九个导出的加载态结果、`status` 执行结果、服务器停止结果、端口释放证据。
>
> **阻塞点就是授权本身**，不是技术未知。下一步最小且有价值的真实实验是 **Stage D（单客户端、一次只读 `status`）**，其具体风险与待批准动作见 §6。

## 1. 基线核对（运行前重新记录，未沿用历史值）

| 项 | 当前实测值 | 判定 |
| --- | --- | --- |
| 分支 / HEAD | `OLfinal-live` / `2a75bdd8872bb9f54006382a924c3006ec9affc2` | 与 T-2.4-C 一致 |
| `git status -uall` | **17** 条（12 M + 5 ??） | 未漂移 |
| T-2.3 已验收 6 文件 | `DF7291F3…` / `74892CDE…` / `D04479DD…` / `FF875F16…` / `0AD4FB80…` / `B892F5C9…` | **6/6 未变** |
| T-1 冻结 9 文件 | `EF4E209B…` … `5C54E358…` | **9/9 未变** |
| `build\stage` mtime | `2026-10-09 17:01:07` | 未变（无部署） |
| D 历史副本 | `_e1_regression\ol-mod-olfinal` `statusCount=6` | 只读，未操作 |
| Python / Frida | 3.11.9 / **frida 16.5.9** + frida-tools 13.0.1 | 在 `frida>=16.5,<19` 区间内 |

## 2. 阶段 1 逐项结果

### P1.1 目标文件指纹（**以当前文件实际计算为准**）

| 项 | 实测值 |
| --- | --- |
| 路径 | `E:\CODOL_SANDBOX\RUN001\codoMP_client_shipRetail.exe` |
| 大小 | **7,841,344** B |
| SHA-256 | **`36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537`** |
| FileVersion / ProductVersion | **1649370 / 1649370** |
| 架构 | **32 位**（PE machine `0x014c`） |
| 文件 mtime | 2026-09-10 00:06:54 |
| 插件 | `…\Ayria\Plugins\CodolGameServer.Localnet32`，6,556,672 B，`6D493B82…2021`，**32 位** |

`CodolGame.py verify-target --game-dir E:\CODOL_SANDBOX\RUN001` → **exit 0**，`ok: true`，与 `config/codol-target-build.json` **逐项一致**。

### P1.2 沙箱位置确认

`E:\CODOL_SANDBOX\RUN001` 存在且为目录；`out.exe` **不存在** ⇒ 目标映像名即默认的 `codoMP_client_shipRetail.exe`，无需设置 `CODOL_CLIENT_EXECUTABLE`。

### P1.3 无意外运行的 CODOL 实例

按进程名（`codoMP|ol_room_owner|Injector32`）与可执行路径（`*CODOL_SANDBOX*`）双重过滤：**匹配 0 个**。

### P1.4 端口现状（区分监听 / 占用 / 可绑定 / 所有权）

| 端口 | 用途 | OS 端点（netstat -ano） | 瞬态绑定 `0.0.0.0` | 瞬态绑定 `127.0.0.1` |
| --- | --- | --- | --- | --- |
| 28960 | game transport | **无** | 成功 | 成功 |
| 28961 | dedicated control | **无** | 成功 | 成功 |
| 28962 | client bridge | **无** | 成功 | 成功 |
| 28970 | room owner | **无** | 成功 | 成功 |

- **无任何监听或占用**，无套接字所有者；四个端口当前均**可绑定**；
- 探测不设 `SO_REUSEADDR`，绑定后立即关闭（证据 `port_snapshot.json`）；
- **注意**：这是**实验前基线**，**不是**“端口已释放”的证据——目前根本没有服务器在运行。

### P1.5 控制脚本清单（从**真实生成的脚本**提取，非源码阅读）

生成的脚本 **1628 行**；执行顺序（行号）：

| 顺序 | 操作 | 行 |
| --- | --- | --- |
| 1 | 身份守卫 `Process.enumerateModules()[0].name` | 20 |
| 2 | 插件模块查找 `Process.findModuleByName('CodolGameServer.Localnet32')` | 24 |
| 3 | 9 个**必需**导出经 `nativeExport` 校验后构造 `NativeFunction` | 25–45 |
| 4 | **`Process.setExceptionHandler(...)`** | **46** |
| 5 | 31 个**可选**导出 `try/catch` 构造 | 47–76 |
| 6 | **`Module.findExportByName(null, exportName)`** 循环（4 个终止导出） | 83 |
| 7 | **`Interceptor.attach(address, …)`** | **85** |
| 8 | 动作分支 `enable` / `disable` / `status` | 1591 / 1593 / 1595 |

**Hook 总数**：1 个异常处理器 + 最多 **4** 个 `Interceptor` 钩子（`ExitProcess`、`TerminateProcess`、`RaiseFailFastException`、`RtlExitUserProcess`）。

### P1.6 ⚠ `status` 路径**不是**无副作用的（关键发现）

| 副作用 | 是否发生 | 依据 |
| --- | --- | --- |
| 安装异常处理器 | **是**（行 46，在动作分支**之前**） | 任何动作都会执行 |
| 安装 `Interceptor` 钩子 | **是，最多 4 个**（行 83–85，在动作分支**之前**） | 任何动作都会执行 |
| **读取游戏进程内存** | **是，约 58 字节** | 见下表 |
| 在目标进程内分配内存 | **是**（脚本含 **183** 处 `Memory.alloc`） | 脚本内分配，非游戏数据 |
| 调用状态改变型导出 | 否 | `status` 分支不调用 `setEnabled` |

**内存读取点**（`hexBytes` 定义为 `pointer.readByteArray(size)`，行 478–486）：

| 位置 | 字节数 | 分支 |
| --- | --- | --- |
| `clientModule.base + 0x162E7EC`（`readU32`） | 4 | **成功与失败分支都会读** |
| `base + 0x19E000` / `0x09E7D0` / `0x1A1140` / `0x1A11E0` / `0x1A12B0` / `0x1850B0`（各 9 字节） | 54 | 仅 `getStatus` 失败分支 |

> **这条必须进入 Stage D 授权范围**：现有的 `status` 路径**既安装 Hook 又读取游戏内存**。它不是“只读调用”。如果授权只允许“只读查询而不安装 Hook/不读内存”，那么**现有脚本不满足**，需要先改造或明确接受这些副作用。

### P1.7 九个必要导出（**文件级**）

插件 DLL 导出表（PE 解析，未附加进程）：机器 `0x014c`（32 位），共 **53** 个导出，其中 `CODOL_*` **50** 个。

| # | 导出名 | 文件级存在 | 用途 | 缺失时分类 |
| --- | --- | --- | --- | --- |
| 1 | `CODOL_GameServerSetEnabled` | ✅ | **停止/启动入口**（Stage E 目标） | `unavailable` |
| 2 | `CODOL_GameServerGetStatus` | ✅ | 服务器 enabled/frame/time | `unavailable` |
| 3 | `CODOL_GameServerGetNetworkStatus` | ✅ | 已连接客户端数 | `unavailable` |
| 4 | `CODOL_GameServerGetNetchanStatus` | ✅ | 收包/丢包/可靠命令计数 | `unavailable` |
| 5 | `CODOL_GameServerGetSessionStatus` | ✅ | 会话配置状态 | `unavailable` |
| 6 | `CODOL_GameServerConfigureGameState` | ✅ | 配置对局状态 | `unavailable` |
| 7 | `CODOL_GameServerGetGameStateStatus` | ✅ | 对局状态 | `unavailable` |
| 8 | `CODOL_GameServerGetConstantConfigStringStatus` | ✅ | 常量配置串校验 | `unavailable` |
| 9 | `CODOL_GameServerGetTransportStatus` | ✅ | **transport.bound / port**（Stage F 关键） | `unavailable` |

**缺失时分类**：9 个必需导出全部经 `nativeExport` 校验，缺失即抛 `codolStop('unavailable', …)` ⇒ 工具退出码 **3**，**不会**被误判为 `refused` 或 `confirmed`。

> **这只证明文件里有这些名字**。它**不能**证明加载后的模块导出了它们、地址可用、ABI 正确或可安全调用。**必须由 Stage D2 在真实进程中复核。**

### P1.8 离线回归重跑

| 套件 | 结果 | 退出码 |
| --- | --- | --- |
| Frida 工具 `CodolGameServerControlTests.py` | **34 项 / 0 失败** | 0 |
| 调用方 `CodolGameTests.py` | **59 项 / 1 失败**（既有 `-qa` 项） | 1 |

与 T-2.3/T-2.4-C 完全一致，**无新增失败**。

## 3. 授权范围 vs 实际执行范围

| 类别 | 内容 |
| --- | --- |
| **本任务授权** | 只读预检；瞬态端口绑定探测（立即关闭） |
| **实际执行** | 文件读取与哈希、git 查询、离线单测、4 个端口的瞬态 UDP 绑定、插件 DLL 导出表 PE 解析 |
| **实际执行**（未授权动作） | **无**。附加 CODOL 进程数 = **0** |
| **未授权** | Stage D（附加）、Stage E（`SetEnabled(false)`）、Stage F（端口释放探测）、Stage T（终止） |

## 4. Stage D 授权申请

### 4.1 具体目标

| 项 | 值 |
| --- | --- |
| 沙箱 | `E:\CODOL_SANDBOX\RUN001` |
| 目标映像 | `codoMP_client_shipRetail.exe`（32 位，SHA-256 `36997674…537`，FileVersion 1649370） |
| 角色 | **一个** `dedicated` 客户端 |
| 启动方式 | `CodolGame.py` 显式 `--game-dir E:\CODOL_SANDBOX\RUN001`（**不修改** `config/codol-game-dir.txt`） |
| 附加次数 | **1 次**，仅 `status`，`--sample-seconds 0` |
| 禁止 | `--disable` / `--enable` / 终止 / 端口探测 |

### 4.2 待批准动作（逐条）

1. **启动** 一个沙箱 `dedicated` 客户端进程；
2. 对该 PID 执行**身份校验**（`tasklist` 唯一 + `(Get-Process).Path` + SHA-256 + FileVersion）；
3. 向该 PID **附加 Frida**（将使用 **x86** frida-agent）；
4. 执行**一次** `CodolGameServerControl.py --pid <pid> --sample-seconds 0`；
5. 采集：进程与端口前后快照、工具 JSON/退出码/stderr、插件日志、产物哈希；
6. **不终止**客户端（保持运行并报告）。

### 4.3 已知风险（必须在授权中明确接受）

| # | 风险 | 等级 | 说明 |
| --- | --- | --- | --- |
| R1 | 在目标进程内**安装异常处理器** | 中 | 行 46，改变异常处理路径 |
| R2 | 在目标进程内**安装最多 4 个 `Interceptor` 钩子** | **中高** | 行 83–85，patch `ExitProcess`/`TerminateProcess`/`RaiseFailFastException`/`RtlExitUserProcess` |
| R3 | **读取约 58 字节游戏内存**（固定 RVA） | 中 | 见 P1.6；若 RVA 与构建不匹配，读到的是无关代码字节（仅用于日志） |
| R4 | 在目标内分配内存 | 低 | 183 处 `Memory.alloc` |
| R5 | **32 位 agent 路径未被 Stage C 覆盖** | 中 | Stage C 验证的是 x86_64 agent；Stage D 走 x86 agent |
| R6 | 反作弊 / TenProtect 类组件可能对附加有反应 | **未知** | 沙箱含 `ACE-DRV32.dll` / `TGuard` |
| R7 | 客户端可能崩溃或行为异常 | 未知 | 出现即按中止条件停止 |

### 4.4 Stage D 验收条件（缺一不可）

1. 目标身份四项证据完整（PID 唯一 / 映像名 / 映像路径 / SHA-256+FileVersion）；
2. 九个必需导出在**加载模块**中逐项记录（名称、查找模块、地址是否为空、异常）；
3. `status` 实际执行并返回，结果**来自真实插件**（`after.installed` 与字段非默认值）；
4. **没有**把 `unavailable` / `refused` / 异常 / 超时误判为 `confirmed`；
5. 原始日志、环境记录、产物哈希齐全；
6. **未发生未授权状态变更**（未调用 `setEnabled`、未终止进程、未做端口探测）。

> 附加成功、脚本执行成功、或返回一个 JSON 对象，**都不足以**单独判定 Stage D 通过。

### 4.5 中止条件（Stage D）

目标身份不符 / 指纹与基线不一致 / 出现未授权操作 / 脚本异常无法解释 / 结果自相矛盾 / 客户端崩溃挂起 / 出现反作弊迹象 / 回归新增失败 —— 立即停止、保留现场、不自动进入 Stage E。

## 5. Stage E / F / T（本轮未授权，仅登记）

| 阶段 | 目标 | 关键证据 | 状态 |
| --- | --- | --- | --- |
| **E** | 调用 `CODOL_GameServerSetEnabled(false)` | 真实返回值 + `Server.enabled` + `transport.bound` + 插件日志 | **NOT_AUTHORIZED** |
| **F** | 端口释放判定 | `netstat` 归属 + 不带 `SO_REUSEADDR` 的绑定 + 精确 `winerror`，按一致性表判定 | **NOT_AUTHORIZED** |
| **T** | 进程终止 | 单 PID、终止前复核身份、记录退出码 | **NOT_AUTHORIZED** |

## 6. 最终报告必须回答的十个问题

| # | 问题 | 答案 |
| --- | --- | --- |
| 1 | 实际 CODOL 目标是否通过身份校验？ | **运行时：尚未校验**（未附加）。**文件级：通过**——路径/大小/SHA-256/FileVersion 与已批准基线逐项一致 |
| 2 | 九个必要插件导出分别是什么结果？ | **文件级 9/9 存在**（插件 DLL 导出表，50 个 `CODOL_*`）；**运行时：未查询** |
| 3 | 哪一条控制路径已经在真实目标上执行？ | **没有**。真实目标上执行的控制路径数 = **0** |
| 4 | 服务器停止入口是否被实际调用？ | **否**（Stage E 未授权） |
| 5 | 若被调用，返回结果与实际状态变化是否一致？ | **不适用**（未调用） |
| 6 | 哪些套接字或端口已经得到真实释放证据？ | **无**。28960/28961/28962/28970 当前全部空闲且可绑定，这只是**实验前基线**，不是释放证据 |
| 7 | 客户端是否仍然存活？ | **没有客户端在运行**（匹配进程 0） |
| 8 | 是否已经实际建立客户端与服务器会话？ | **否** |
| 9 | 距离玩家进入对局，当前最明确的阻塞点是什么？ | **Stage D 授权**。在真实客户端上确认“模块已加载 + 9 个必需导出在加载模块中存在 + `status` 可返回真实状态”之前，无法判断启动上下文、握手或会话层。次要阻塞：停止入口与传输层从未在真实目标上运行过 |
| 10 | 下一步最小、最有价值且经过授权的真实实验是什么？ | **Stage D**：单客户端、一次只读 `status`、含完整身份指纹与前后快照（§4）。它同时回答 Q1、Q2、Q3，且**不改变插件状态** |

## 7. 未验证事项

1. 未启动、未附加、未注入、未读取、未终止任何 CODOL 进程；
2. 九个导出只在**文件**中确认，未在**加载模块**中确认；
3. `status` 从未对真实客户端执行；
4. `CODOL_GameServerSetEnabled(false)` 从未被调用；
5. `transport.bound` 语义、端口释放、客户端退出均未验证；
6. Stage C 覆盖的是 x86_64 agent，32 位客户端将使用 x86 agent，该路径**未验证**；
7. 未建立任何客户端与服务器会话。

## 8. 关联产物

- `T2_5_RESULTS.json`（逐项状态：`PASS` / `NOT_AUTHORIZED` 等）
- `T2_5_SHA256_MANIFEST.txt`
- 原始证据：`verify_target.json`、`port_snapshot.json`、`control_script_inventory.json`、`generated_control_script.js`、`plugin_export_table.json`、`tool_tests_t25.log`、`caller_tests_t25.log`、`baseline.txt`
- 采集脚本：`port_snapshot.py`、`script_analysis.py`、`plugin_exports.py`、`build_results.py`
