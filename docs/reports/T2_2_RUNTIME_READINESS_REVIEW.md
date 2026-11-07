# T2_2_RUNTIME_READINESS_REVIEW — 真实客户端验证前置条件审查

**日期**：2026-10-10
**工作树**：**F = `F:\桌面\ol\ol-mod-olfinal`**（HEAD `2a75bdd8872bb9f54006382a924c3006ec9affc2`，分支 `OLfinal-live`）
**本轮性质**：**仅静态审查、离线测试、环境信息核对、方案编制。未启动游戏、未附加 Frida、未读取游戏内存、未部署。**
**上游**：[T2_1_CALLER_REGRESSION_REPORT.md](T2_1_CALLER_REGRESSION_REPORT.md)（有条件通过）· [T2_RUNTIME_VALIDATION_PREREQUISITES.md](T2_RUNTIME_VALIDATION_PREREQUISITES.md)

---

## 0. 结论

> ### **③ 暂不就绪**
>
> 发现一个**硬阻塞项 B1**：工具注入的 JS 调用了 **Frida >= 19.0.0 才存在**的 API `Module.findGlobalExportByName`，而本机安装的是 **Frida 16.5.9**（项目声明 `frida>=17,<18`）。该调用**无 try/catch 保护**且位于**任何插件导出调用之前**，因此对真实目标脚本会在载入时抛 `TypeError`，工具返回 `tool-error`（exit 1），**`CODOL_GameServerSetEnabled(false)` 永远不会被调用**。在修复并重新验证之前，真实运行实验**不可能产出任何目标证据**。
>
> 另有 4 项必须先满足的条件（C1–C4，见 §9）。P1/P3/P4/P5/P6 本身**已就绪**。

**证据等级**（本报告统一使用）：

| 等级 | 含义 | 本轮数量 |
| --- | --- | --- |
| **E-Static** | 源码/配置静态阅读 | 多处 |
| **E-Offline** | 可重复的离线实测（哈希、类型检查、单测） | 5 类 |
| **E-Env** | 环境信息核对（版本、路径、文件存在性） | 4 类 |
| **E-Runtime** | **真实客户端运行时证据** | **0 项** |

---

## 1. 冻结核对（E-Offline / E-Env）

| 项 | 值 | 判定 |
| --- | --- | --- |
| F HEAD / 分支 | `2a75bdd8872bb9f54006382a924c3006ec9affc2` / `OLfinal-live` | 与 T-2、T-2.1 一致 ✅ |
| F `git status --porcelain -uall` | **15** 条（11 M + 4 ??） | 与 T-2.1 末态一致 ✅ |
| T-2.1 清单逐文件校验 | `CodolGame.py` `8CBF194A…`、`CodolGameServerControl.py` `4B7C1CE4…`、`CodolGameTests.py` `B0B53130…`、`CodolGameServerControlTests.py` `BC227C76…` | **全部 OK** ✅ |
| T-2.1 证据文件校验 | `_t2_1_evidence/` 7 个文件 | **全部 OK** ✅ |
| T-1 冻结基线 | `REPRODUCE.ps1` 7/7 OK | ✅ |
| `build\stage` mtime | `2026-10-09 17:01:07` | **未变**，无部署 ✅ |
| D 历史副本 | `D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal`：HEAD 同 F、`statusCount=6`（与 T-2 manifest 逐字相同） | **未修改** ✅ |
| D 副本的 runtime 工具 | `CodolGame.py` `3324CD8D…`、`CodolGameServerControl.py` `EF3A8F16…`、`CodolGameTests.py` `E5668698…` = **HEAD 版** | 证明 D 未含 T-2/T-2.1 改动 ✅ |
| 破坏性操作 | 未执行 `reset` / `rebase` / `clean` / `commit` / `push` / `ol_deploy` | ✅ |

> 注：`D:\BaiduNetdiskDownload\使命召唤OL` 根目录**不是** git 工作树；D 历史副本实为 `_e1_regression\ol-mod-olfinal`。

## 2. T-2.1 实现与报告一致性（E-Static / E-Offline）

| 报告声称 | 代码核对 | 判定 |
| --- | --- | --- |
| 四态结果 + 退出码 0/1/2/3 | `CodolGameServerControl.py:31-44`（`RESULT_*`、`RESULT_EXIT_CODES`）；`CodolGame.py:595-597` | 一致 ✅ |
| 工具输出结构化 JSON（`result` 权威） | `report()` :109-121；尾部兜底 :1891-1902 | 一致 ✅ |
| 调用方只在插件返回 false 时判 `refused` | `classify_stop_result`（`CodolGame.py:650-…`），要求 `result`、退出码、`ok` 三者自洽 | 一致 ✅ |
| 三层身份校验 | L1 `target_image_matches` `CodolGame.py:629-647`；L2 `find_pid` :84-106；L3 JS 守卫 `CodolGameServerControl.py:200-213` | 一致 ✅ |
| 多 PID 聚合、3 优先于 4 | `stop()` `CodolGame.py:1066-…`；7 项单测 | 一致 ✅ |
| 测试规模 | 调用方 **40 项 / 1 失败**（既有 `-qa`）；工具 **24 项 / 0 失败** | 与报告一致 ✅ |

**⇒ T-2.1 的实现与报告逐条相符，未发现报告虚报。**

## 3. P1：目标身份

### 3.1 允许的客户端映像名及来源（E-Static / E-Env）

| 来源 | 值 | 位置 |
| --- | --- | --- |
| 调用方 | `CODOL_CLIENT_EXECUTABLE` 环境变量优先，否则 `codoMP_client_shipRetail.exe` | `CodolGame.py:28` |
| 工具 | 同上（本轮 T-2.1 已改为同源解析） | `CodolGameServerControl.py:25` |
| 批处理约定 | `if not defined CODOL_CLIENT_EXECUTABLE set "CODOL_CLIENT_EXECUTABLE=codoMP_client_shipRetail.exe"` | `Match_CODOL_Two_Clients.bat:22` |

比较规则：**大小写不敏感、仅基名**（完整路径不匹配），L1 用 `tasklist`、L2/L3 用 Frida 枚举 + `Process.enumerateModules()[0].name`。

### 3.2 名字级校验不能区分同名不同构建（明确披露）

名字相等只能证明“映像基名相同”。它**不能**排除：同机另一份同名构建、被替换/打过补丁的同名映像、或同一构建的另一实例。**这不是进程身份的密码学保证**，本报告与协议均不如此表述。

### 3.3 用现有非侵入性信息进一步确认构建：**可行**（E-Env）

本轮已实际采集到沙箱目标的构建级指纹（**未启动进程**，仅读文件）：

| 项 | 值 |
| --- | --- |
| 目标映像 | `E:\CODOL_SANDBOX\RUN001\codoMP_client_shipRetail.exe` |
| 大小 / SHA-256 | 7,841,344 B / `36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537` |
| PE 版本资源 | **FileVersion = ProductVersion = 1649370**（Activision Blizzard） |
| 插件 DLL | `…\Ayria\Plugins\CodolGameServer.Localnet32`（6,556,672 B，SHA-256 `6D493B820E84A21B096C9914616B75DCEC488920D7AC76867049B20C5C6B2021`） |

**可加入协议的非侵入式构建确认链**（不需要 Frida，不需要调试器）：

1. `tasklist /FI "IMAGENAME eq <name>"` ⇒ 确认**恰好一个** PID；
2. `(Get-Process -Id <pid>).Path` ⇒ 取得该 PID 的**映像全路径**（本轮已在本机验证该技术可用）；
3. 对该全路径文件计算 SHA-256 与 `VersionInfo.FileVersion`，与 §3.3 记录的基线比对；
4. 不匹配 ⇒ 中止。

**能证明**：附加前该 PID 的映像文件就是已记录的那一份构建（路径 + 哈希 + 版本资源三重一致）。
**不能证明**：进程启动后是否被内存补丁改写；不构成密码学身份保证；存在步骤 2→3 之间的极短竞态（文件被替换），概率极低但非零。

### 3.4 P1 判定：**就绪（附 C3 条件）**

## 4. P2：Frida 兼容性 —— **阻塞项 B1**

### 4.1 版本三方不一致（E-Env）

| 项 | 值 | 来源 |
| --- | --- | --- |
| **实际安装** | **frida 16.5.9**（Python dist 与 `frida --version` 一致）；frida-tools 13.0.1 | `importlib.metadata` / CLI |
| **项目声明** | `frida>=17,<18` | `tools/runtime/requirements-codol.txt:1` |
| **代码实际要求** | **>= 19.0.0** | 见 §4.3 |

### 4.2 API 使用点逐项检查（E-Static / E-Offline）

**Python 侧（9 个异常类 + 8 个调用）**：全部存在于安装的 16.5.9（`dir(frida)` 实测），`frida.get_local_device` / `Device.enumerate_processes` / `Device.attach` / `Session.create_script` / `Session.on` / `Script.on` / `Script.load` / `Script.unload` / `Session.detach` 均为 16.x 稳定 API ⇒ **兼容** ✅

**JS 侧**（逐项对照 `types/frida-gum@16.5.1`）：

| API | 16.5.1 类型定义 | 判定 |
| --- | --- | --- |
| `Process.enumerateModules()` | 存在 | ✅ |
| `Process.findModuleByName()` | 存在 | ✅ |
| `Process.id` / `Process.setExceptionHandler()` | 存在 | ✅ |
| `Interceptor.attach()` / `NativeFunction` | 存在 | ✅ |
| `Memory.alloc()` / `Memory.allocUtf8String()` | 存在 | ✅ |
| `Thread.backtrace()` / `Backtracer.ACCURATE` | 存在 | ✅ |
| `DebugSymbol.fromAddress()` | 存在 | ✅ |
| `module.getExportByName()`（实例方法，用于 60+ 个可选导出） | 存在 | ✅ |
| **`Module.findGlobalExportByName()`** | **不存在** | ❌ **B1** |

### 4.3 B1：非法的 Frida API 调用

**调用点**（E-Static）：

``
tools/runtime/CodolGameServerControl.py:270   (HEAD:174)
    for (const exportName of [
        'ExitProcess', 'TerminateProcess', 'RaiseFailFastException',
        'RtlExitUserProcess'
    ]) {
        const address = Module.findGlobalExportByName(exportName);   // <-- 不存在
        if (address === null) continue;
        Interceptor.attach(address, { ... });
    }
``

该循环位于脚本**顶层 try 内**、`const setEnabled = new NativeFunction(...)` **之前**，且**无逐项 try/catch**。整棵树仅此一处使用（`git log -S` 显示由提交 `6517a63 "Complete dedicated booking handoff"` 引入）。

**三重独立证据**（E-Offline）：

1. **官方类型定义全版本扫描**：`@types/frida-gum` 12.6.0 → 18.8.0 的 `GlobalExportByName` 出现次数**全部为 0**；**19.0.0 起**才出现
   `static findGlobalExportByName(name: string): NativePointer | null;`
   `static getGlobalExportByName(name: string): NativePointer;`
   16.5.1 中 `Module` 的全部 ExportByName 成员只有：`findExportByName(exportName)`、`getExportByName(exportName)`、`static findExportByName(moduleName: string | null, exportName)`、`static getExportByName(moduleName: string | null, exportName)`
2. **安装二进制字符串扫描**：`_frida.pyd`（16.5.9）中 `GlobalExport` / `findGlobalExportByName` / `getGlobalExportByName` 出现 **0** 次，而 `findExportByName`(29)、`getExportByName`(43)、`NativeFunction`(184)、`enumerateModules`(20) 均存在（对照组有效）
3. **机器化类型检查**：把该语句原文放入 `probe.ts`，用 `tsc --noEmit --strict` 配合 `types/frida-gum@16.5.1`：
   `probe.ts(5,24): error TS2551: Property 'findGlobalExportByName' does not exist on type 'typeof Module'. Did you mean 'findExportByName'?`
   两条对照语句 `Module.getExportByName(null, ...)` / `Module.findExportByName(null, ...)` **无报错**，证明检查装置有效。

旁证：与本机 16.5.9 配套的 frida-tools 13.0.1 自身的 agent 在需要全局导出时使用的是 `Module.getExportByName(null, name)`（`frida_tools/itracer_agent.js`）。

### 4.4 后果

对任何真实目标执行 `--disable`（或 `--enable` / `status`）时：

``
script.load()
  └─ TypeError: Module.findGlobalExportByName is not a function
       └─ 顶层 catch ⇒ send({ok:false, result:'tool-error', error:'...'})
            └─ 工具 print result=tool-error，exit 1
                 └─ 调用方 classify_stop_result ⇒ ("tool-error", "exit 1: ...")
``

- **`CODOL_GameServerSetEnabled` 从未被解析、从未被调用** ⇒ 实验设计中的 S1–S5 一个也采不到。
- T-2.1 的失败分类**表现正确**（如实报 `tool-error`，未伪装成 `refused`，未伪装成成功）——这一点反而得到验证。

**旁证（E-Offline）**：在 `_t2_evidence`、`_t2_acceptance_evidence`、`_t1_fix_evidence`、沙箱日志目录中搜索 `sample_index` / `transport_bound` / `"after"`，**命中 0**。迄今没有任何一次成功的工具调用被记录过。

### 4.5 最小修复方向（**本轮未实施，需授权**）

把该行改为 16.x 起即存在的等价写法：

``
const address = Module.getExportByName(null, exportName);      // 找不到会抛，需逐项 try/catch
const address = Module.findExportByName(null, exportName);     // 找不到返回 null，与现有 === null 分支天然契合
``

推荐 **`Module.findExportByName(null, exportName)`**：与紧邻的 `if (address === null) continue;` 完全兼容，改动一行、无新增分支。
同时必须**收敛版本声明**：安装版本、`requirements-codol.txt` 声明、代码实际要求三者必须一致。

### 4.6 P2 判定：**不就绪（阻塞项 B1）**

> **本轮未附加任何进程**，因此上述结论全部来自版本信息、官方类型定义、安装二进制与离线类型检查，**不含**真实运行时证据。修复后仍需在真实目标上确认脚本能载入。

## 5. P3：停止成功语义（E-Static）

### 5.1 调用链与精确行号

``
CODOL_GameServerSetEnabled(false)                       src/game_server/Appmain.cpp:8174-8201
  ├─ if (!ensureInstalled()) return false;                                :8176-8177
  ├─ Server.setEnabled(false);                                            :8180
  ├─ const auto transportStopped = Network.stop();                        :8183
  ├─ { lock(WorldAssetMutex); PendingWorldAsset.reset(); }                :8184-8187
  ├─ if (!transportStopped) { log("game server disable failed: udp transport is still bound"); return false; }  :8188-8198
  └─ return true;                                                         :8200

SvUdpTransport::stop()                                  src/game_server/server_mp/sv_network_mp.cpp:72-98
  ├─ if (!socket_.close()) { status_.lastSocketError = err;
  │     log("udp transport stop failed op=close error=" + err); return false; }   :75-86
  ├─ status_.bound = false; status_.port = 0; …                            :87-92
  └─ return true;                                                          :97

NetUdpSocket::close()                                   src/game_server/win32/win_net.cpp:149-170
  ├─ if (socket_ != InvalidSocket) {
  │     if (closesocket(...) == SOCKET_ERROR) { lastError_ = WSAGetLastError(); return false; }  :153-160
  │     socket_ = InvalidSocket; }                                         :161
  ├─ port_ = 0;                                                            :163
  ├─ if (winsockStarted_) { WSACleanup(); winsockStarted_ = false; }       :164-168   <- 返回值被忽略
  └─ return true;                                                          :169
``

### 5.2 五个状态必须分开（与 T-2 一致，本轮逐行复核通过）

| 状态 | 含义 | 与 `return true` 的关系 |
| --- | --- | --- |
| S1 API 调用成功 | 函数返回 | `true` 即 S1 |
| S2 插件状态切换 | `Server.status().enabled == false` | **被蕴含**（:8180 无条件执行，幂等） |
| S3 `Network.stop()` 完成 | 返回 true | **被蕴含**（:8188 否则 return false） |
| S4 UDP socket 关闭 | 调用后 `socket_ == InvalidSocket` | **不严格蕴含**：句柄本已无效时 `close()` 也返回 true 而未关闭任何 socket；真正的保证是“**调用后 `socket_.open() == false`**” |
| S5 进程退出 | 进程终止 | **完全无关** |

**`WSACleanup()` 返回值被忽略（`win_net.cpp:166`）** —— 这是一条明确限制：`return true` 不保证 Winsock 引用计数已归零，也不保证 OS 层端口立即可被其它进程重绑。

**插件其它 socket 不受影响**：`DedicatedControl` 监听（`Appmain.cpp:2072-2086`，端口 28961）与 `ClientSessionBridge`（`Appmain.cpp:1911-2068`，端口 28962）**完全不被 `SetEnabled(false)` 触及**。

### 5.3 P3 判定：**就绪**；协议必须遵守“不把任何单个状态等同于完整资源释放”。

## 6. P4：证据采集最小集

设计见 [T2_2_EXPERIMENT_PROTOCOL.md](T2_2_EXPERIMENT_PROTOCOL.md) §4。摘要（每条含“能证明/不能证明”）：

| # | 证据 | 能证明 | **不能**证明 |
| --- | --- | --- | --- |
| E0 | 操作前：单实例 PID + 映像全路径 + 文件 SHA-256 + FileVersion 1649370 | 附加前目标是已记录的构建 | 运行期未被内存补丁改写 |
| E1 | 操作前：28960/28961/28962 占用基线；`GetTransportStatus` 基线 | 起始状态已知 | 与停止语义无关 |
| E2 | 工具 stdout JSON + 退出码 | 工具的分类结论（confirmed/refused/unavailable/tool-error） | 插件内部状态本身 |
| E3 | `GetStatus` 的 `enabled`、`GetTransportStatus` 的 `bound`/`port` | S2、S4 的调用后状态 | S4 的“本次真的关闭了 socket” |
| E4 | 插件日志（`udp transport stop failed` / `game server disable failed` 的有无） | S3/S4 的失败路径是否发生 | 未记录的事件不存在 |
| E5 | 28961/28962 在操作后**仍被占用** | `SetEnabled(false)` 的作用范围 | 无 |
| E6 | 操作后进程从 `tasklist` 消失 | S5 | 退出是否干净 |
| E7 | （安全时）由**独立进程**尝试 `bind(28960)` | OS 层端口是否真的释放 | 其它端口/其它 socket |
| E8 | 时间戳、文件哈希、逐步记录 | 可复现性与可审计性 | 结论正确性 |

## 7. P5：失败中止与恢复

见协议 §5。**中止条件**至少覆盖：映像名不匹配或身份信息不足；附加结果无法确定；工具输出与退出码矛盾；插件返回 false；调用超时或目标进程状态异常；观察到非预期的客户端或插件行为。

**新增（本轮发现）**：

| ID | 风险 | 处理 |
| --- | --- | --- |
| **R-Term** | `CodolGame.stop()` 的 `terminate_pids` 对**早先枚举到的 PID** 执行 `taskkill /PID <pid> /T /F`。G1 只保护 **Frida 附加**路径；若客户端在枚举与 `taskkill` 之间退出、PID 被复用，可能误杀无关进程树 | 协议强制：**终止前对每个 PID 重新核对映像名**，不一致则跳过该 PID 并记录；优先使用单 PID 的手工 `taskkill /PID <pid> /T /F` 而非批量 `stop` |
| **R-Tool** | 工具在真实目标上必然返回 `tool-error`（B1） | B1 未修复前**不进入实验**；中止后不得把 `tool-error` 解读为插件行为 |

## 8. P6：回归保护（E-Offline）

| 检查 | 命令 | 结果 | 日志 |
| --- | --- | --- | --- |
| T-1 复现 | `REPRODUCE.ps1`（`-ExecutionPolicy Bypass`） | **exit 0**：基线哈希 **7/7 OK**、`checks=124 failures=0`、三个目标全 exit 0、`build\stage` mtime 未变 | `_t2_2_evidence/reproduce_20261010_142849.log` |
| 调用方测试 | `python CodolGameTests.py -v` | **40 项 / 1 失败**（既有 `-qa` 项） | `_t2_2_evidence/caller_tests_t22.log` |
| 工具测试 | `python CodolGameServerControlTests.py -v` | **24 项 / 0 失败** | `_t2_2_evidence/tool_tests_t22.log` |
| 历史日志 | 未覆盖任何既有日志（本轮只新增 `_t2_2_evidence/`） | ✅ |
| 部署命令 | 未运行；`build\stage` mtime = `2026-10-09 17:01:07` | ✅ |
| D 冻结副本 | 未改动（HEAD 同、status 6、runtime 工具仍为 HEAD 版） | ✅ |

**⇒ P6 判定：就绪。T-2.1 未引入回归。**

## 9. 阻塞项与条件汇总

| ID | 类型 | 内容 | 判定依据 | 必须先满足 |
| --- | --- | --- | --- | --- |
| **B1** | **阻塞** | 工具注入 JS 调用 Frida >=19 才存在的 `Module.findGlobalExportByName`；环境为 16.5.9、声明为 `>=17,<18`。该调用无保护且先于任何插件导出 ⇒ 真实目标上工具必然 `tool-error`，停止导出永不被调用 | §4.3 三重独立证据 + `tsc` 实测 | **是** |
| C1 | 条件 | `config/codol-game-dir.txt` 指向**不存在**的 `D:\codo_3.19.26.13_fresh\CoD Online`；协议必须以显式 `--game-dir` 指向 `E:\CODOL_SANDBOX\RUN001`，不得修改该配置文件 | E-Env | 是（协议层） |
| C2 | 条件 | 终止路径存在 PID 复用误杀风险（G1 未覆盖），协议必须要求终止前逐 PID 复核映像 | E-Static | 是（协议层） |
| C3 | 条件 | 工具的身份校验仍是名字级；构建级确认必须在协议里以“路径 + SHA-256 + FileVersion”外部步骤补齐 | §3.2/§3.3 | 是（协议层） |
| C4 | 条件 | 三方版本声明必须收敛（安装 16.5.9 / 声明 `>=17,<18` / 代码需 >=19），并记录最终一致值 | §4.1 | 是 |
| C5 | 建议 | 建议把修复后的脚本在**无害非游戏进程**上做一次载入自检（不附加游戏），以确认脚本无其它载入期异常 | — | 否（但强烈建议） |

## 10. 必须明确声明的边界

> **本准备审查通过 != 真实客户端兼容性已得到证明。**
>
> - 本轮 **E-Runtime 证据为 0 项**：没有启动客户端、没有附加 Frida、没有读取游戏内存。
> - §4 的 Frida 兼容性结论全部来自版本信息、官方类型定义、安装二进制与离线类型检查；**没有**任何一次真实 `script.load()`。
> - §5 的停止语义结论全部来自源码静态阅读；**没有**任何一次真实的 `CODOL_GameServerSetEnabled(false)` 调用。
> - P1 的构建指纹（1649370 / SHA-256）是**文件层**证据，不是进程身份保证。
> - 即使 B1 修复，也**只能**在获得单独运行授权后，通过协议中的实测证据判断兼容性；不得用 mock 测试、静态阅读或一次成功运行外推到其它角色、其它构建或双客户端场景。

## 11. 关联交付

- [T2_2_EXPERIMENT_PROTOCOL.md](T2_2_EXPERIMENT_PROTOCOL.md) — 最小实验方案、证据集、中止与回滚
- [T2_2_SHA256_MANIFEST.txt](T2_2_SHA256_MANIFEST.txt) — 本轮哈希清单
- [T2_1_CALLER_REGRESSION_REPORT.md](T2_1_CALLER_REGRESSION_REPORT.md) · [T2_1_G1_PROCESS_IDENTITY_REPORT.md](T2_1_G1_PROCESS_IDENTITY_REPORT.md) · [T2_1_G2_RESULT_CLASSIFICATION_REPORT.md](T2_1_G2_RESULT_CLASSIFICATION_REPORT.md)
- [T2_RUNTIME_VALIDATION_PREREQUISITES.md](T2_RUNTIME_VALIDATION_PREREQUISITES.md) · [T1_VERIFIED_BASELINE.md](T1_VERIFIED_BASELINE.md)
- 证据：`_t2_2_evidence/`（`frida_api_audit.txt`、`environment_facts.txt`、测试日志、REPRODUCE 日志）
