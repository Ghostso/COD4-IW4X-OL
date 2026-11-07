# COMBAT_SERVER_BLOCKERS — 当前阻塞点、证据与未知项

**性质**：只读汇编。**不预设最终原因**，凡无法由证据判定的分支一律标注"不可区分 / UNKNOWN"。
**配套**：`COMBAT_SERVER_HISTORICAL_FINDINGS.md`、`COMBAT_SERVER_EVIDENCE_INDEX.md`、`COMBAT_SERVER_CALLCHAIN_MAP.md`、`COMBAT_SERVER_BASELINE_SHA256.txt`。

---

## 0. 阻塞点总览

| 序 | 阻塞点 | 类别 | 级别 | 证据状态 |
|---|---|---|---|---|
| **P0** | 宿主映像身份门禁：`EngineBindings::bind()` 要求 `SizeOfImage==0x0E5D6000`（且 `TimeDateStamp==0x6096930A`），实测客户端为 `0x0E659000` | 接口不兼容 + 初始化条件不满足 | **硬阻塞（一条阻断 100% 战斗链）** | **真实运行证据 ×3** |
| **P0-a** | 失败**具体发生在哪一项**（DOS/NT 签名、`TimeDateStamp`、`SizeOfImage`）**不可区分** | 可观测性缺口 | 硬 | 源码 + 日志反证 |
| **P1** | 部署件陈旧：build `DBA7273A…` ≠ deployed `6D493B82…` | 工程流程 | 阻断"改源码后验证" | 哈希实测 ×2 |
| **P2** | 后端下发 `ConfigureSession` 未在真实环境接通（28961 ← backend） | 网络/会话未打通 | 阻断开服 | 28960 从未监听 |
| **P3** | 两个真实客户端的 `room→ready→capture→connect→snapshot` 自然闭环未发生 | 缺真实运行证据 | 需 P0 先解除 | 文档自述 |
| **P4** | `G_Damage` / Lua thread / PVS / SD 回合机等可玩性缺口 | 缺实现 | 影响"可玩"，**不阻断"能进对局"** | 文档/源码 |
| **Q1** | （并行线）`6/14 mmbook/mmstart` booking 应答帧格式 UNKNOWN | 协议逆向线 | 阻断 L2 的 Lobby→Battle | 9/9 断连实测 |
| **Q2** | （并行线）客户端对局流量被送到外部腾讯 `101.67.36.18:10035` | 路由未接管 | 阻断 L2 | 600 s 抓包 0 次 28960 |
| **Q3** | 唯一硬入口 `Ayria\Injector32.exe`；`CodolGame.py` 路径失败；`ol_deploy` 禁用 | 授权/工具 | 阻断全部实机验收 | 实测 exit 1/3 |
| **Q4** | 真实客户端 Frida 附加失败（2 次 0 成功） | 工具/可行性 | 阻断"读运行时映像"的捷径 | 实测 |
| **Q5** | 9 个插件专属文件 31,953 行零测试 | 工程风险 | 插件边界正确性不可验证 | 源码实测 |

---

## 1. 引擎绑定失败（P0 / P0-a）

### 1.1 历史报告的核心表述（逐条转写）

- `EngineBindings::bind()` 在**宿主映像 `SizeOfImage` 检查处**失败。
- 当前客户端测得 **`0x0E659000`**。
- 门禁期望 **`0x0E5D6000`**。
- 两者的 **`TimeDateStamp` 相同**（`0x6096930A`）。
- 原有绑定包含 **146 个 RVA 和 82 条守卫**。

### 1.2 这些数值的来源与适用目标（本轮核实）

| 数值 | 来源 | 适用目标 | 本轮核实 |
|---|---|---|---|
| `ExpectedTimestamp = 0x6096930A` | `EngineBindings.hpp:438` | **O-1 去壳 out.exe**（build 1649370） | 已读取源码行，一致 |
| `ExpectedImageSize = 0x0E5D6000` | `EngineBindings.hpp:439` | 同上 | 已读取源码行，一致 |
| `ComFrameRva = 0x0FEA20` | `EngineBindings.hpp:440` | 同上 | 已读取源码行，一致 |
| 当前客户端 `SizeOfImage = 0x0E659000` | O-3 磁盘 PE 实测 | **加壳零售件**（`.tp3`×6+`.tvm0`） | 已读取 `_combat_baseline/pe_identity.log`，一致 |
| 客户端 `TimeDateStamp = 0x6096930A` | 同上 | 同上 | 一致 |
| **146 个 RVA** | `CODOL_SERVER_PROGRESS_20261009.md:184`；`COMBAT_SERVER_RECOVERY_BASELINE.md:25` | ol-mod（F 树） | **本轮实测（D 树）：`static constexpr … *Rva =` 得 145；宽口径去重标识符得 146；另有报告记 170。见 §6 冲突** |
| **82 条守卫** | `CODOL_SERVER_PROGRESS_20261009.md:185`；`COMBAT_SERVER_RECOVERY_BASELINE.md:25` | ol-mod（F 树） | **本轮实测（D 树）：`std::equal(` = 82，一致**；另有报告记 66 / 78–79 |

### 1.3 相关代码与历史验证结果

- **门禁**：`EngineBindings.cpp:3647-3667`。`:3653` `bindingCommitted_.store(false)`（fail-closed）；`:3654` `module_ = GetModuleHandleW(nullptr)`；`:3662-3664` 三项同处一个 `if`。
- **具名守卫**：`:3669-3693`（`native entity binding prefix mismatch function=`）、`:3695-3742`（player DObj）。
- **未具名复合守卫**：`:3744-4023`（失败只写 `stage=function_prefixes`，`:4021`）。
- **其他阶段**：`:4153 runtime_slots`、`:4203 message_bindings`、`:4210 glass_bridge`；`:4214 bindingCommitted_.store(true)`；`valid()` `:4218`。
- **消费点**：`Appmain.cpp:7133-7137`（`logGameServer("engine binding failed")` + `return`）；`FrameHook.cpp:59-67`（`!bindings.valid()` ⇒ `invalid-bindings` 拒绝）。
- **离线重放（历史）**：`tools/reverse/ReplayEngineBindings.py`（42,867 B），68 断言 / 16 用例 / 0 失败；对加壳候选 A/B 的裁定为 **`INSUFFICIENT_EVIDENCE`**；其**负对照**（自有未加壳插件 DLL）结果为 `PASS=0 FAIL=53 AMBIGUOUS=26 INSUFFICIENT=2 → verdict: FAIL`，证明该工具**不是"全通过"工具**（`OFFLINE_BINDING_REPLAY_REPORT.md:17-19`；`_p14_evidence/replay_plugin_negative_control.log`）。

### 1.4 真实运行证据（三次，完全一致）

`E:\CODOL_SANDBOX\RUN001\Ayria\Logs\CodolGameServer.log`（6 行 / 582 B）：

```
[2026-10-10 15:47:48] [combined/game-server] engine binding failed
[2026-10-10 15:47:48] [combined/game-server] LOGSTALL lockUs=0 fileUs=913 consoleDebugUs=143018 prefix=engine binding failed
[2026-10-10 15:48:28] [combined/game-server] engine binding failed
[2026-10-10 15:48:28] [combined/game-server] LOGSTALL lockUs=0 fileUs=359 consoleDebugUs=141923 prefix=engine binding failed
[2026-10-10 15:50:14] [combined/game-server] engine binding failed
[2026-10-10 15:50:14] [combined/game-server] LOGSTALL lockUs=0 fileUs=386 consoleDebugUs=138151 prefix=engine binding failed
```

- 三次文本**完全一致**；仅 `LOGSTALL` 的 `fileUs`（913 / 359 / 386）与 `consoleDebugUs`（143018 / 141923 / 138151）微差。
- 同刻 `AlwaysofflineRe.Localnet32.log` 各 1 条 `Refused to apply CODOL startup patches to an unknown executable image.`。
- **角色 = `combined`**（日志前缀 + 启动器 `Launch_OLMod.bat` 未设 `OLMOD_PROCESS_ROLE`、未传参数）。

### 1.5 本轮独立推导出的强约束（**推断，附反证条件**）

`bind()` 共 9 处 `return false`，其中**只有** `:3656`（`!module_`）、`:3660`（DOS `e_magic`）、`:3666`（NT 签名/时间戳/尺寸）**不写日志**；其余 6 处均先写日志。
且 `RuntimeLog.cpp:60`（通道名 `"game-server"`）与 `:77`（文件名 `CodolGameServer.log`）证明 `bind()` 的日志与 `logGameServer` **同文件同前缀**。

⇒ **三次日志中只有 `engine binding failed`、没有任何 stage/前缀不匹配行，证据上支持"失败落在 `:3656/`:3660/`:3666` 三处之一"**。
⇒ 由于 DLL 明显已被加载（`Localnetworking.log:2`），`:3656` 概率极低；**剩余候选为 `:3660` 与 `:3666`**。
⇒ **但 `TimeDateStamp` 与 `SizeOfImage` 同处 `:3662-3664` 一个 `if`，代码不记录是哪一项 —— 该二分支不可区分（P0-a）。**

> **反证条件（若出现，本推断作废）**：若实际构建的插件在 `bind()` 早退点存在与本工作区源码不同的日志行为，或在 `RuntimeLog` 初始化失败时静默丢弃日志，则"无 stage 日志"不能推出上述结论。**沙箱部署件（`6D493B82…`，2026-10-09 13:49）并非 F 树当前构建（`DBA7273A…`，2026-10-10 12:52）**，两者源级一致性未经比对 —— 这正是必须先解决 P1 的原因。

### 1.6 不得据此推出的结论（历史报告明令）

1. **不得**认定全部 145/146 个 RVA 或 82 条守卫失效（**它们从未在真实目标上执行过一次**）。
2. **不得**认定"只需放宽 `SizeOfImage` 检查"就能通过（`TimeDateStamp` 与尺寸不可区分；且守卫从未执行）。
3. **不得**以"让门禁变绿"为由修改任何常量或删除任何校验。
4. **不得**用磁盘加壳件的 PE 头推断运行时映像门禁结果（已裁定为"对象错位"）。

### 1.7 P0 的两种处置路线（历史提案，**待用户裁定，本轮未实施**）

| 路线 | 内容 | 优点 | 代价/风险 |
|---|---|---|---|
| **R-A** | 取得去壳 `out.exe` 本体（或来源说明 + 完整 SHA-256） | 零代码风险；145/146 RVA 与 82 条守卫**原样成立** | 依赖外部制品；本机/授权根 **0 命中**（B1/B2/B3 BLOCKED） |
| **R-B** | 在受控试验下越过 `SizeOfImage` 门禁，让 82 条守卫**实际执行** | 不需缺失制品；结果决定性（守卫全过 ⇒ 可用；否则精确指出第一处不匹配） | 若运行时布局不同，需大规模重标定；**必须一次只放宽一项，且保留全部守卫** |

**核心未知（禁止用运行时实验以外的猜测消除）**：TenProtect 在内存中解包后，`0x0FEA20` 等 RVA 处的**运行时代码字节**是否等于 `out.exe` 的期望值。文件级测量（已做）**不能**回答，因为加壳映像的文件字节必然被替换。

### 1.8 该阻塞的下一步所需证据（最小集）

| ID | 证据 | 用途 | 采集方式（历史报告已给出，本轮未执行） |
|---|---|---|---|
| **E-2** | 运行时映像（O-4）的 `TimeDateStamp` / `SizeOfImage` / `Machine` / 段表 | 区分 `:3660` / `:3662` / `:3664` 分支 | 授权后**在插件内只读读取自身模块头**并写日志 |
| **E-3** | 运行时映像中 `0x0FEA20`（`55 8B EC 56 57`）与 `0x8371A`（`83 7C 24 08 01 0F 94 C0`）的实际字节 | **真正的正确性判据**；必须在门禁放宽之前取得 | 同上 |
| **（前置）** | 门禁具名化（纯日志：把 `:3647-3667` 两项比较拆分记录 `stage=host_image_timestamp/size effective=… expected=…`） | 让失败可诊断 | **T-3.0 提案**，未批准 |

---

## 2. 服务器模块加载（`Localnetworking.log` 证据的边界）

### 2.1 事实

`E:\CODOL_SANDBOX\RUN001\Ayria\Logs\Localnetworking.log`（29 行 / 2,356 B，mtime 2026-10-10 15:50:20）：

```
:1  Loaded Localnet32 plugin Alwaysoffline.Localnet32.
:2  Loaded Localnet32 plugin CodolGameServer.Localnet32.
:3  Localnetworking backend listening on 127.0.0.1:4200.
:4-11   sendto-target pid=23828 … target=122.96.96.225 port=8081 bytes=308 clientPort=0/52377
:12-25  connect-target … 101.72.248.61:80 / 218.60.84.93:443 ×4 / 127.0.0.1:5770x-5772x 本地回环
:26-29  sendto-target … target=182.50.14.56 port=8081 bytes=164/196
```

### 2.2 该证据能证明什么

1. `CodolGameServer.Localnet32` **被 Localnetworking 枚举并 `LoadLibraryW` 成功**（插件 ABI / 调用约定 G-D1 / E-4 的问题 **已回答**）。
2. 插件的 `onStartup` / `onInitialized` → `initialize()` **确实被调用**（否则不会有 game-server 通道日志输出）。
3. 客户端进程（pid 23828）**确实启动到网络阶段**，真实向腾讯 `8081` / `443` 发起流量（mod 后端 **4200** 与游戏端口无关）。
4. 角色 = `combined`。

### 2.3 该证据**不能**证明什么

1. **不能**证明初始化成功（同批运行的 `CodolGameServer.log` 明确为 `engine binding failed`）。
2. **不能**证明帧钩子安装（0 次 `client frame hook installed`）。
3. **不能**证明 28960/28961/28962/28970 任一端口进入监听（实测**从未监听**）。
4. **不能**证明 `Createserver` 被用于任何 hostname 认领（它返回 `nullptr`，会被记入 `rejectedHosts`）。
5. **不能**证明客户端处于大厅状态（其流量指向真实腾讯服务器；`Alwaysoffline` 拒绝打补丁）。

### 2.4 关联的后续服务器初始化日志（必须与本节合并阅读）

`CodolGameServer.log` = 三次 `engine binding failed`（见 §1.4）。**加载成功 + 初始化失败**是本阻塞点的完整表述。

### 2.5 证据分级提醒

沙箱目录中另有 `build/bin/release/Ayria/Logs/CodolGameServer.log`（186 KB / 1,496 行 / **全部同一时间戳 2026-10-09 13:52:25** / 0 次 `engine binding failed` / 0 次 `Localnet32` / 0 次 `frame hook`）。该文件是**测试进程副产物**（`T1_ACCEPTANCE_REPORT.md:50`），**不得**当作三次初始化失败的证据。

---

## 3. 三次初始化失败（完整上下文、共同点与差异）

| 项 | 内容 |
|---|---|
| 日期 | 2026-10-10 |
| 次数 | **3** |
| 时间 | 15:47:48 / 15:48:28 / 15:50:14（间隔约 40 s、106 s） |
| 运行目标 | `E:\CODOL_SANDBOX\RUN001\codoMP_client_shipRetail.exe`（7,841,344 B，`36997674…B537`，FileVersion 1649370） |
| 执行动作 | 照搬出货启动器 `Launch_OLMod.bat` 的调用形式：`Injector32.exe "codoMP_client_shipRetail.exe"`，**无参数、不设 `OLMOD_PROCESS_ROLE`** ⇒ `combined` |
| 观测结果 | 三次均为 `[combined/game-server] engine binding failed`；插件被加载；`Alwaysoffline` 三次均拒绝打补丁；`Bootstrapper32` 加载 2 个 `.Ayria32` 插件 |
| 差异 | **仅 `LOGSTALL` 的两个微秒计数值**（`fileUs` 913/359/386；`consoleDebugUs` 143018/141923/138151）；其余文本逐字相同 |
| **共同点** | 同一客户端、同一插件（deployed `6D493B82…`）、同一角色（combined）、同一失败点（`bind()`）、同一"无 stage 日志"形态 |
| 证据位置 | `E:\CODOL_SANDBOX\RUN001\Ayria\Logs\{CodolGameServer,Localnetworking,Bootstrapper32,AlwaysofflineRe.Localnet32}.log` |
| 原始报告 | `COMBAT_SERVER_RECOVERY_BASELINE.md` §1.6；`CODOL_RUNTIME_BLOCKER_CLEARANCE_20261009.md` §0/§5 |
| 独立对照/复核 | 本轮**独立重读全部 6 个日志**（行数/大小/时间戳一致）；并独立核实 `bind()` 的 9 处 `return false` 与日志通道 |

### 3.1 进程与端口对照（同一批运行）

| 时间 | 事件 |
|---|---|
| 15:44:34 | `CodolGame.py launch` → **exit 3**，`Injector exited with code 1`（`CODOLLauncher.log`/`T25_launcher_direct.log` = `Could not create process. Error: 2`） |
| 15:47:48 | pid **24016** 出现，约 20 s 后消失；本轮日志出现第 1 条 `engine binding failed` |
| 15:48:28 | pid **24580**（`mods 5`，`ExecutablePath = …\codoMP_client_shipRetail.exe`）；第 2 条 `engine binding failed` |
| 15:50:14 | pid **23828**（`processCount=1`、`fileSha256 36997674…`、`fileVersion 1649370`）；第 3 条 `engine binding failed` |
| 15:22 / 15:43 | T-2.5 Stage 1 基线：28960/28961/28962/28970 **OS 端点为空**；瞬态 bind 8/8 成功（`SO_REUSEADDR` 未设，探完即关） |
| Stage D 各步 | `PRE/POST ports: []` ⇒ **四次客户端启动期间四个游戏端口从未进入监听** |

> **不得**把 Stage 1 的"bind 成功"读成"端口已释放/可用"证据：当时**没有任何服务器在运行**（`codolProcesses=0`）。

---

## 4. 生产部署件与当前源码差异（P1）

### 4.1 已有哈希与构建记录（本轮只读复算，未构建）

| 制品 | 大小 | SHA-256 | 时间 |
|---|---|---|---|
| F 构建产物 `build\bin\release\CodolGameServer.Localnet32` | 6,559,232 | `DBA7273A0C9DD31CDD5619DD47B11C01EDC21AE17EEFC18FDD71F43B992097BC` | 2026-10-10 12:52:50 |
| D 构建产物（同路径） | 6,556,672 | `0EABD5F54763976CA4A92CC4C0DBB34A5CC8E60DE6EBFE4A3C6FA28A6A157971` | 2026-10-09 17:32:40 |
| stage 产物（F 与 D 相同） | 6,556,672 | `6D493B820E84A21B096C9914616B75DCEC488920D7AC76867049B20C5C6B2021` | 2026-10-09 13:49:42 |
| **沙箱部署件** `E:\CODOL_SANDBOX\RUN001\Ayria\Plugins\CodolGameServer.Localnet32` | 6,556,672 | `6D493B820E84A21B096C9914616B75DCEC488920D7AC76867049B20C5C6B2021` | 2026-10-09 13:49:42 |
| 另一历史构建哈希 | — | `21D1481735828B48…`（`_batch2_build.log`） | — |
| 其余 4 个运行时制品 | — | `Localnetworking.Ayria32 8F1BC5D4…100A` / `Platformwrapper.Ayria32 A7420E17…8D2F` / `Alwaysoffline.Localnet32 D2B9CA40…EF54` / `ol_room_owner.exe 354D5B29…BCB3` | 均与 build **SAME** |

### 4.2 含义

**5 个运行时制品中只有战斗服务器本体是旧的。** 当前源码树对 `src/game_server` 的任何修改**从未落到沙箱**。任何"改源码后直接跑"的验证都是无效的。

### 4.3 部署清单

`E:\CODOL_SANDBOX\RUN001\ol-mod-runtime-manifest.json`（28,209 B，mtime 2026-10-09 17:01:08）：`schemaVersion=1`、`titleId=1004`、`architecture=x86`、`gameExecutable = codoMP_client_shipRetail.exe`。

### 4.4 本轮约束与未知

- **禁止**本轮构建或部署来重新验证（任务明令）。
- `ol_deploy` 被禁用；`config/codol-game-dir.txt` 指向一个不存在的目录（`D:\codo_3.19.26.13_fresh\CoD Online`，SHA-256 `9AEEFD10…19AA`，未修改）。
- **未知**：沙箱 `Alwaysoffline` 的 44 项 overlay 是否与当前源码一致（未逐项比对）。
- **推论风险**：由于 deployed 插件（10-09 13:49）≠ F 当前构建（10-10 12:52），§1.5 关于"无 stage 日志"的推断**必须在源级比对两个插件后**才能完全成立。

---

## 5. 启动链与注入失败（仅登记与战斗服务器研究有关的事实）

| # | 事实 | 状态 | 证据 |
|---|---|---|---|
| B1 | 进程注入唯一入口 `Ayria\Injector32.exe`；`CodolGame.py:291` 注明不可加参数 | **BLOCKED（需单独授权）** | `CODOL_RUNTIME_BLOCKER_CLEARANCE_20261009.md` §5 B1 |
| B2 | `CodolGame.py launch --game-dir E:\CODOL_SANDBOX\RUN001` → `Injector exited with code 1`（命令 exit 3）；改照搬 `Launch_OLMod.bat` 才产出日志 | FAILED（辅助启动器问题，已登记） | `_t2_5_stageD_evidence/stageD_launch.log`；`COMBAT_SERVER_RECOVERY_BASELINE.md` §1.6 |
| B3 | `CODOLLauncher.log` / `T25_launcher_direct.log` = `Could not create process. Error: 2` | FAILED（工具） | 沙箱 `Ayria\Logs\` |
| B4 | 首次战斗服务器运行日志（2026-10-10 ×3）= `engine binding failed` | 硬阻塞 | §1.4 |
| B5 | 插件**确实被加载** | CONFIRMED | §2.1 |
| B6 | `Alwaysoffline` 三次拒绝打补丁 —— **按设计如此，非故障** | CONFIRMED | §2.4 |
| B7 | 部署件陈旧 | 工程流程缺口 | §4 |
| B8 | **Frida 对真实客户端附加失败**：`ProcessNotFoundError`（pid 24580，15:49:50）与 **`ProcessNotRespondingError`**（pid 23828，15:50:16，"either refused to load frida-agent, or terminated during injection"）；**真实客户端附加成功 0 次**。同版本 x86 agent 在无害 `cmd.exe`（pid 14028）上 `X86_AGENT_OK`；x64 在 `python.exe`（pid 17832）上 6/6 PASS | 未定论（U7）；**排除 Frida 作为常规取数手段** | `_t2_5_stageD_evidence/stage_d_attach.log`、`stage_d_run.log`、`x86_agent_control.json`；`_t2_4c_evidence/*` |
| B9 | 28960 从不监听：`Network.start()` 的触发者是后端下发 `ConfigureSession`（→28961），不是插件加载 | 结果，不是目标 | §2.3；`COMBAT_SERVER_RECOVERY_BASELINE.md` §3.2 |
| B10 | 战斗服务器是**进程内模块**，经 `Com_Frame`(RVA `0x0FEA20`) 5 字节相对跳转运行；`ol_room_owner.exe`(28970) 只做房间/令牌 owner | CONFIRMED（5 条独立证据） | `COMBAT_SERVER_RECOVERY_BASELINE.md` §2.3 |
| B11 | （大厅线）`BOOKING_SOURCE = BLOCKED`；`BOOKING_PROTOCOL = UNKNOWN`；`BATTLE_ENTRY = NOT_OBSERVED` | 冻结 | `REF_LOBBY_KIT/STAGE_REPORT_BATTLE.md` P0-2 |
| B12 | （大厅线）查询 `收包=0` 与 `battle_srv.log` 存在的完整会话**互相冲突** | **未定论** | 见 §7 冲突 W-1 |
| B13 | T-2.4 Stage D/E/F/T 全部 `NOT_AUTHORIZED`；生成的 status 脚本经静态分析**并非无副作用**（装异常处理器 + ≤4 个 Interceptor 钩子 + 读约 58 B 内存） | 需重新界定授权范围 | `T2_4_RUNTIME_AUTHORIZATION_REQUEST.md`；`_t2_5_evidence/T2_5_RUNTIME_VERIFICATION_REPORT.md` |
| B14 | 历史 CDB/WinDbg 会话：`(2744.3e4): Access violation - code c0000005 (first chance)` 停在 `KERNEL32!IsBadReadPtr+0x5a`（2026-09-19） | 历史记录（与本轮无关的早期观察） | `_core009_run1.txt`、`_core009_runB.txt` |
| B15 | 历史静态裁定 EX-009：`TenProxy = NOT LOADED`；`CA8150/CA8158 runtime writer = NOT FOUND`；`current startup path = NOT PROVEN` | 历史记录 | `CODOL_EX009_BINDING_VERDICT.md:14-25` |

> **纪律**：启动器修复与 Frida 兼容性**不属于本轮范围**，此处只登记，不展开修复。

---

## 6. 冲突登记（并列保留）

| # | 冲突 | 各自主张 | 处理 |
|---|---|---|---|
| **W-1** | `battle_srv.log` 是否含真实战斗会话 | `BATTLE_SERVER_PROTOCOL.md` §1 引其 21:28:19–21:28:24 为**完整真实会话**；`STAGE_REPORT_BATTLE.md` P0-1 冻结记**收包=0**；该文件**同样被离线自测写入**（`battle_selftest.py` 调用 `battle_server.handle_plain`）；文件末段 19:04:56–19:05:08 另有完整 UDP 会话 | **未定论**；逐行来源不可只读区分 |
| **W-2** | RVA 常量数 145 / 146 / 170 | 本轮实测：`static constexpr … *Rva =` **145**；宽口径去重标识符 **146**；`CODOL_RUNTIME_BLOCKER_CLEARANCE_20261009.md` §4.2 对更早版本记 **170** | 并列；**计数口径 + 工作树版本**双重差异 |
| **W-3** | 前缀守卫数 82 / 66 / 78–79 | 本轮实测 `std::equal(` = **82**；git `55fcdbf` 描述记 66；`artifact_provenance.json:38-41` 记 78/79（且语境内是"加壳映像不匹配数"） | 并列 |
| **W-4** | `E3823FD6…F37B` 归属 | ① Golden"客户端 EXE"；② "OLFinal unpacked out.exe"；③ 任务指令称属 3.3.3.3 QA；④ `.agents/AGENTS.md:174` "当前 active EXE" | **未裁定**；不采用、不重写 |
| **W-5** | 报告基准树 | Batch 10 报告的行数对应 **D 树**；F 树另有 3 个未提交修改（`Appmain.cpp` / `FrameHook.cpp` / `FrameHook.hpp`） | 已解释；行号需标树 |
| **W-6** | `battle_srv.log` 中的"收包=0" vs 外部地址否证 | `28960` 在 600 s 日志出现 0 次（流量送 `101.67.36.18:10035`）vs 存在完整 28960 会话 | 并列（可能与不同轮次/不同入口有关） |
| **W-7** | "本机从未成功初始化" vs 2026-08-14 双客户端验证 | 前者针对 OLfinal-live/1649370 线；后者属 `v3.3.3.3-dedicated` 线（git `55fcdbf` 于 2026-08-18 才翻转门禁） | 已用只读 git 溯源解释；**原始 `.runtime/` 证据不存在** |
| **W-8** | `c0000005` 历史崩溃的归属 | `_core009` 记录的是 2026-09-19 的 CDB 会话；与 2026-10-10 三次运行**无证据关联** | 不得混为一谈 |

---

## 7. 未知项（必须保留）

| # | 未知项 | 阻塞什么 | 解除条件 |
|---|---|---|---|
| U1 | 加壳映像**运行时**在 `0x0FEA20` / `0x8371A` 等 RVA 处的字节是否等于目录期望 | 决定 R-A / R-B，是 P0 核心未知 | E-3（运行时 RVA 字节） |
| U2 | `out.exe` 本体是否存在（本机/授权根 0 命中；全盘未独立复核） | 决定 R-A 可行性 | 用户提供本体或来源说明 + 完整 SHA-256 |
| U3 | 全加密客户端 EXE 的导出表 | 逆向完整性 | 静态分析 |
| U4 | 生产是否设置 `OLMOD_PROCESS_ROLE=dedicated` / `OLMOD_HOST_ADDRESS` | 影响对局形态（listen-server vs dedicated） | 启动脚本/配置证据 |
| U5 | 后端下发 `ConfigureSession` 的真实 Demonware 描述符字节（含 16 B 会话密钥） | **阻断 28960 监听** | 真实环境样本 |
| U6 | 沙箱 `Alwaysoffline` 的 44 项 overlay 是否与当前源码一致 | 后端行为 | 逐项比对 |
| U7 | Frida 为何无法注入该客户端 | 影响"读运行时映像"手段可行性 | 独立诊断（**不在本轮范围**） |
| U8 | 原版引擎独立的"战斗/会话创建"函数；原版 `NET_Frame`；原版 gametype 初始化入口 | L1 战斗创建入口判定 | 静态逆向 |
| U9 | `6/14 mmbook/mmstart` booking 应答帧格式；DedicatedControl 客户端桥端口与帧格式 | L2 的 Lobby→Battle | 原始字节样本 / 源码 |
| U10 | 客户端"对局流量地址"的真实来源（`101.67.36.18:10035` 由谁下发） | L2 路由 | 追 `gcloudvoice.dll` 地址来源 |
| U11 | ol-mod 线与协议逆向线的接口关系 | 路线选择 | 需用户裁定 + 交叉证据 |
| U12 | `E3823FD6…F37B` 归属 | 可接受制品集合 | 用户裁定 |
| U13 | `ICH059` PRCL `.tls` scheduler | 协议逆向线 | `NOT_LOCATED` |
| U14 | `Appmain.cpp` 十处多行导出的精确符号名 | 插件 ABI 完整性 | 反汇编 `.exp` |
| U15 | `runtime_module_load_order.csv` / `ICH044_*` 等清单内容 | 运行时模块事实 | 逐行核验 |

---

## 8. 证据缺口（本轮如实标注）

| # | 缺口 | 影响 |
|---|---|---|
| G-1 | **Stage D 的正式报告不存在**：只有原始 `.log`/`.json`（`_t2_5_stageD_evidence\`，部分为 UTF-16LE） | 三次运行的完整上下文只能从原始日志与 `COMBAT_SERVER_RECOVERY_BASELINE.md` 拼合 |
| G-2 | 工作区内**没有**真实游戏进程运行证据；唯一真实运行日志在 E 盘沙箱 | 工作区自足性不足 |
| G-3 | 未找到任何**真实客户端上成功的 Frida 附加会话** | 取数手段受限 |
| G-4 | 未找到 `out.exe` 或任何 `SizeOfImage=0x0E5D6000` 的 PE | R-A 未启动 |
| G-5 | `E:\CODOL_SANDBOX\RUN001\Ayria\Logs\` 中三次运行**共用同一组日志文件**（仅靠时间戳区分） | 逐次运行的隔离证据不足 |
| G-6 | `.runtime/natural-match/**` 在本工作区**不存在** | 全部"自然实机验证"只能标为**文档自述** |
| G-7 | 沙箱部署的插件与 F 当前构建**不是同一产物** | §1.5 的推断需源级比对 |

---

## 9. 优先级建议（仅按依赖排序，**不含实施授权**）

| 序 | 事项 | 性质 | 为什么在这个位置 |
|---|---|---|---|
| 1 | 裁定 P0 路线（R-A 取得 `out.exe` / R-B 受控试验） | **需用户裁定** | 唯一硬阻塞；不裁定则无法推进实机 |
| 2 | 让 P0 可诊断（门禁具名化 + 复合守卫首失败者具名；T-3.0） | 代码变更，**需单独授权** | 使失败从"不可区分"变为"可判定" |
| 3 | 解决 P1（部署件陈旧） | 流程，**需单独授权** | 否则任何"改源码后验证"都无效 |
| 4 | 取得 E-2 / E-3（运行时 PE 头 + 关键 RVA 字节） | 运行时，**需单独授权** | 决定 R-B 是否可行 |
| 5 | 接通后端 `ConfigureSession`（P2 / U5） | 运行环境 | 决定 28960 能否监听 |
| 6 | 插件边界测试目标（31,953 行零覆盖） | 工程 | 不阻断进对局，但为最大工程风险 |

**明确不排入本优先级的项**：`G_Damage` / SD 回合机 / Lua thread / PVS / 世界模型缩放 等可玩性工作（它们影响"可玩"，不阻断"能进对局"）；启动器修复；Frida 兼容性；`ol_deploy` 与部署替代流程（属单独审批）。

---

## 10. 纪律声明

本轮未修改任何生产代码/配置；未启动/附加/注入/终止任何进程；未构建/部署/提交/推送；未清理工作区。原始证据（沙箱 `Ayria\Logs\*`、`_combat_baseline/*`、`_batch10_evidence/*`、`_t2_5_stageD_evidence/*`、`_p14_evidence/*`、`REF_LOBBY_KIT/battle_srv.log` 等）**保持原样**。
