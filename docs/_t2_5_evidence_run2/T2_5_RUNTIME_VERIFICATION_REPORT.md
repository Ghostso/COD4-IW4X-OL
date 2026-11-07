# T2_5_RUNTIME_VERIFICATION_REPORT - 真实客户端控制链与服务器运行验证

**日期**：2026-10-10　**执行**：Stage 1（只读预检，本轮重新实测）

**工作树 F**：`F:/桌面/ol/ol-mod-olfinal`　分支 `OLfinal-live`　HEAD `2a75bdd8872bb9f54006382a924c3006ec9affc2`

**证据目录**：`D:\BaiduNetdiskDownload\使命召唤OL\_t2_5_evidence_run2`（本次运行的新目录；上一轮 `_t2_5_evidence` 原样保留未动）

> **结论**：Stage 1 十项检查 **9 项 PASS、1 项 PASS_WITH_DEVIATION**（DEV-1，已完全解释且发生在本任务之前）。
> **真实 CODOL 控制链证据仍为 0 条**：本轮**未启动、未附加、未注入、未读取、未终止任何 CODOL 进程**（attached = 0）。
> **Stage D / E / F / T 全部 NOT_AUTHORIZED**；Stage D 的具体授权申请见 §8。

---

## 1. 环境与基线（本轮重新记录，未沿用历史值）

| 项 | 本轮实测值 |
| --- | --- |
| Python | `3.11.9` `C:\Users\Z7-CT5N1\AppData\Local\Programs\Python\Python311\python.exe` |
| Frida / frida-tools | `16.5.9` / `13.0.1` |
| 分支 / HEAD | `OLfinal-live` / `2a75bdd8872bb9f54006382a924c3006ec9affc2` |
| git status -uall | **17** 条（12 M + 5 ??） |
| build/stage mtime | `2026-10-09T17:01:07+0800`（未变，未部署） |
| D 历史副本 | `_e1_regression/ol-mod-olfinal` HEAD `2a75bdd8872bb9f54006382a924c3006ec9affc2`，statusCount **6**，只读查询、未写入 |

**T-2.3 已验收 6 文件**：**6/6 全部未变**

**T-1 冻结 9 文件**：**9/9 全部未变**

**额外守卫**（T-2 验收清单禁止区 src/game_server/FrameHook.cpp）：未变

| 文件 | 期望 | 实测 | 判定 |
| --- | --- | --- | --- |
| `tools/runtime/CodolGameServerControl.py` | `DF7291F3CAE0EBD1...` | `DF7291F3CAE0EBD1...` | OK |
| `tools/runtime/CodolGame.py` | `74892CDEEC889320...` | `74892CDEEC889320...` | OK |
| `tools/runtime/CodolGameTests.py` | `D04479DD9AFB3FC1...` | `D04479DD9AFB3FC1...` | OK |
| `tools/runtime/CodolGameServerControlTests.py` | `FF875F1683DA865B...` | `FF875F1683DA865B...` | OK |
| `tools/runtime/requirements-codol.txt` | `0AD4FB806C21DE95...` | `0AD4FB806C21DE95...` | OK |
| `config/codol-target-build.json` | `B892F5C9D8B0F4DE...` | `B892F5C9D8B0F4DE...` | OK |
| `src/game_server/server_mp/sv_network_mp.cpp` | `EF4E209BDD9EFDCD...` | `EF4E209BDD9EFDCD...` | OK |
| `src/game_server/server_mp/sv_network_mp.hpp` | `53E5907AE4AFD925...` | `53E5907AE4AFD925...` | OK |
| `src/game_server/win32/win_net.cpp` | `3A34D953D2A7A483...` | `3A34D953D2A7A483...` | OK |
| `src/game_server/win32/win_net.hpp` | `8F0FF3189887660D...` | `8F0FF3189887660D...` | OK |
| `tests/game_server/TransportLifecycleTests.cpp` | `FA67AE5B9C6D222C...` | `FA67AE5B9C6D222C...` | OK |
| `src/game_server/EngineBindings.hpp` | `9ACE87313419DB58...` | `9ACE87313419DB58...` | OK |
| `src/game_server/ClientProcessPatches.cpp` | `E81D760A6B362076...` | `E81D760A6B362076...` | OK |
| `src/game_server/Appmain.cpp` | `407B6F9896A5F035...` | `407B6F9896A5F035...` | OK |
| `xmake.lua` | `5C54E3585817E908...` | `5C54E3585817E908...` | OK |
| `src/game_server/FrameHook.cpp` | `1CA962D707F23DA4...` | `1CA962D707F23DA4...` | OK |

## 2. 目标身份（P1.1 / P1.2）

| 项 | 实测值 |
| --- | --- |
| 路径 | `E:\CODOL_SANDBOX\RUN001\codoMP_client_shipRetail.exe` |
| 大小 | **7841344** B |
| SHA-256 | **`36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537`** |
| FileVersion / ProductVersion | 1649370 / 1649370 |
| CompanyName / FileDescription | Activision Blizzard / Call of Duty Online |
| PE machine | **0x014c**（32 位） |
| 文件 mtime | 2026-09-10T00:06:54+0800 |
| 插件 | `E:\CODOL_SANDBOX\RUN001\Ayria\Plugins\CodolGameServer.Localnet32`，大小 6556672，SHA-256 `6D493B820E84A21B096C9914616B75DCEC488920D7AC76867049B20C5C6B2021` |
| out.exe | 不存在 ⇒ 映像名即默认 codoMP_client_shipRetail.exe |

CodolGame.py verify-target --game-dir E:/CODOL_SANDBOX/RUN001 → **exit 0**，ok=True，与 config/codol-target-build.json 的 size / sha256 / fileVersion / plugin sha256 逐项一致。

**判定：P1.1 PASS（文件级身份确认）；P1.2 PASS（位于指定沙箱目录）。**

## 3. 进程与端口现状（P1.3 / P1.4）

### P1.3 无意外运行的 CODOL 实例

- 全机进程数 **278**；
- 过滤规则：Name contains codo|ol_room_owner|injector32|olgs|codol, or ExecutablePath contains CODOL_SANDBOX；
- **匹配数 0** ⇒ 当前没有任何 CODOL 客户端、room owner 或 injector 在运行。

### P1.4 端口现状（监听 / 占用 / 可绑定 / 所有权四者区分）

| 端口 | 用途 | OS 端点（netstat -ano） | 瞬态绑定 0.0.0.0 | 瞬态绑定 127.0.0.1 |
| --- | --- | --- | --- | --- |
| 28960 | game transport | **无** | 成功 | 成功 |
| 28961 | dedicated control | **无** | 成功 | 成功 |
| 28962 | client bridge | **无** | 成功 | 成功 |
| 28970 | room owner | **无** | 成功 | 成功 |

> 探测**不设 SO_REUSEADDR**，绑定后立即关闭。
> **这是实验前基线，不是“端口已释放”的证据**：当前根本没有服务器在运行，四个端口为空是预期状态，不能用来证明停止链正确。

**判定：P1.3 PASS；P1.4 PASS（仅作为基线记录）。**

## 4. 控制脚本清单（P1.5 / P1.6 / P1.7）

清单不是读源码得到的，而是**捕获工具真正会加载的那份生成脚本**（1628 行）后分析得到，产物为 generated_control_script.js。

### P1.5 执行顺序与 Hook

| 顺序 | 操作 | 行 |
| --- | --- | --- |
| 1 | identity guard (Process.enumerateModules()[0].name) | 20 |
| 2 | plugin module lookup (Process.findModuleByName) | 24 |
| 3 | nativeExport: CODOL_GameServerSetEnabled | 112 |
| 4 | nativeExport: CODOL_GameServerGetTransportStatus | 466 |
| 5 | Process.setExceptionHandler | 46 |
| 6 | Module.findExportByName(null, ...) hook loop | 83 |
| 7 | Interceptor.attach(termination exports) | 85 |
| 8 | action branch (enable/disable/status) | 1591 |

- **必需导出 9 个**，全部经 nativeExport(plugin, name, ...) 校验后才构造 NativeFunction；
- **可选导出 31 个**，各自 try/catch，失败保持 null；
- 身份守卫：Process.enumerateModules()[0].name 必须等于 codoMP_client_shipRetail.exe（行 17-23）；
- 插件查找：Process.findModuleByName('CodolGameServer.Localnet32')（行 24），为 null 即 unavailable；
- 全局导出查找：Module.findExportByName(null, exportName)（行 83）→ Interceptor.attach（行 85）。

### P1.6 ⚠ status 路径**不是**无副作用的（本轮最关键的风险发现）

| 副作用 | 是否发生 | 依据 |
| --- | --- | --- |
| 安装异常处理器 | **是** | 行 46 Process.setExceptionHandler，位于动作分支**之前** |
| 安装 Interceptor 钩子 | **是，最多 4 个** | 行 76-85；目标 ExitProcess / TerminateProcess / RaiseFailFastException / RtlExitUserProcess |
| 调用插件 NativeFunction | **是，8 个** | status() 调用 getStatus / getNetworkStatus / getNetchanStatus / getSessionStatus / getGameStateStatus / getConstantConfigStringStatus / getTransportStatus 等（行 1086-1521） |
| 读取游戏内存 | **是** | clientModule.base+0x162E7EC（行 34）及失败分支的多个固定 RVA |
| 调用状态改变型导出 | 否 | setEnabled 只在 action === 'enable' / 'disable' 分支（行 1591 / 1593）；本次生成的脚本 action = 'status'（行 1579） |

> **这条必须写进 Stage D 的授权范围。** 现有 status 路径**既安装 Hook、又调用插件导出、还读取固定 RVA 内存**，它不是一个纯只读查询。
> 如果授权只允许“完全不改变目标进程行为”，现有脚本**不满足**该条件，必须先改造脚本或明确接受上述副作用。

### P1.7 九个必需导出（**仅文件级**）

插件文件导出表：machine `0x14c`（32 位），共 **53** 个导出，其中 CODOL_* **50** 个；必需导出 **9/9 存在**，缺失 []。

| # | 导出名 | 查找模块 / API | 签名 | 预期用途 | 缺失分类 | 文件级 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `CODOL_GameServerSetEnabled` | `plugin.findExportByName` | `bool(bool)` | server enable/disable entry; the Stage E target | `unavailable` | 是 |
| 2 | `CODOL_GameServerGetStatus` | `plugin.findExportByName` | `bool(*,*,*)` | server enabled / frame / server time | `unavailable` | 是 |
| 3 | `CODOL_GameServerGetNetworkStatus` | `plugin.findExportByName` | `bool(*)` | connected client count | `unavailable` | 是 |
| 4 | `CODOL_GameServerGetNetchanStatus` | `plugin.findExportByName` | `bool(*,*,*)` | packets / dropped / reliable command counters | `unavailable` | 是 |
| 5 | `CODOL_GameServerGetSessionStatus` | `plugin.findExportByName` | `bool(*)` | session configured flag | `unavailable` | 是 |
| 6 | `CODOL_GameServerConfigureGameState` | `plugin.findExportByName` | `bool(*,*,u32,u32)` | set game state (NOT invoked by the status path) | `unavailable` | 是 |
| 7 | `CODOL_GameServerGetGameStateStatus` | `plugin.findExportByName` | `bool(*,*)` | game state configured / messages sent | `unavailable` | 是 |
| 8 | `CODOL_GameServerGetConstantConfigStringStatus` | `plugin.findExportByName` | `bool(*,*,*)` | constant configstring checksum / init flag | `unavailable` | 是 |
| 9 | `CODOL_GameServerGetTransportStatus` | `plugin.findExportByName` | `bool(*,*,*)` | transport.bound / port / counters (Stage F key) | `unavailable` | 是 |

失败分类链：nativeExport 在 module.findExportByName(name) === null 时 throw codolStop('unavailable', ...) ⇒ 工具退出码 **3**，**不会**被记成 refused 或 confirmed。

> **这只证明文件里有这些名字。** 只有 Stage D2 在真实进程里对**已加载模块**逐项查询，才能证明导出存在、地址可用；即使地址非空，也**不能**推出函数语义、ABI 或可安全调用。

**判定：P1.5 PASS；P1.6 PASS（记录为高风险项）；P1.7 PASS（文件级）。**

## 5. 离线回归（P1.8 / P1.9）

| 套件 | 命令 | 返回码 | 结果 |
| --- | --- | --- | --- |
| Frida 控制工具单测 | python CodolGameServerControlTests.py -v | **0** | Ran 34 tests in 0.240s；OK |
| 调用方单测 | python CodolGameTests.py -v | **1** | Ran 59 tests in 0.080s；FAILED (failures=1) |
| T-1 传输生命周期（预编译 gtest） | build/bin/release/ol_transport_lifecycle_tests.exe | **0** | checks=124 failures=0 |

调用方套件的唯一失败项是 test_only_dedicated_uses_native_qa_launch_bypass，与 T-2.3 / T-2.4-C 记录完全一致，**不是新增失败**。
T-1 测试运行前后项目端口快照均为空（portsBefore=[]、portsAfter=[]），未遗留套接字。

**判定：P1.8 PASS；P1.9 PASS_WITH_DEVIATION。**

### DEV-1：T-1 测试二进制哈希与 T-2 验收快照不一致（已解释）

| 项 | 值 |
| --- | --- |
| 文件 | build/bin/release/ol_transport_lifecycle_tests.exe |
| T-2 验收快照 | `FD503FAAC0AC61F8605F863BEB8161481B69A6D42C0C2D472CD19A7232307EF0`（3830272 B） |
| 本轮实测 | `85F9BFDD75644D11CDED3A47F1906C6D7468BD27A2A2AA0013AF6C0708350726`（3830272 B，mtime 2026-10-10T14:50:05+0800） |
| 原因 | T-2.3 于 2026-10-10 14:49:33 主动强制重建该测试：_t2_3_evidence/reproduce_20261010_144933.log 第 15 行 forced rebuild ol_transport_lifecycle_tests，.obj.d 时间戳 14:49:37，产物 14:50:05 |
| 行为对比 | T-2.3 报告记录 checks=124 failures=0, exit 0；本轮复现**完全一致** |
| 影响 | **T-1 冻结源码 9/9 未变**；只有这个**编译测试产物**与更早的 T-2 验收快照不同 |
| 本轮动作 | 只读哈希与运行；**未重建、未替换、未回滚** |

> 该偏差发生在本任务开始之前，属于 T-2.3 的已知动作，不是 T-2.5 造成的漂移。按纪律在此**显式记录、不隐藏、不清理**。

### DEV-1 复核结论（按要求先复核该二进制；全程只读，未重建/未替换/未回滚）

| 复核项 | 实测结果 |
| --- | --- |
| PE Linker TimeDateStamp | 2026-10-10T14:50:05+0800（与该文件 mtime 完全一致，落在 T-2.3 记录的 14:49:33-14:50:08 窗口内） |
| PE 机器 / 链接器版本 / 子系统 | 0x14c / 14.44 / 3 |
| 实际链接器 | E:\BuildTools\VC\Tools\MSVC\14.44.35207\bin\HostX64\x86\link.exe |
| 链接开关 | -nologo, -dynamicbase, -nxcompat, -machine:x86, /opt:ref, /opt:icf, -nodefaultlib:msvcrt.lib |
| 静态库 | ws2_32.lib, libcrypto.lib, libssl.lib, user32.lib, advapi32.lib, crypt32.lib |
| 导入表（仅 5 个系统 DLL） | ADVAPI32.dll, CRYPT32.dll, KERNEL32.dll, USER32.dll, WS2_32.dll |
| PDB / 调试目录 | 磁盘上无 PDB；release 构建未保留符号（预期） |
| 链接输入对象文件 | 79 个，全部存在，mtime 区间 2026-10-10T14:49:35+0800 - 2026-10-10T14:49:55+0800（全部在窗口内） |
| 窗口外对象 / 缺失对象 | [] / [] |
| 对象对应源码缺失 | [] |
| 比构建结束更新的项目源码（src/ tests/） | [] |
| 闭包内 T-1 冻结源码哈希 | 全部未变：src/game_server/ClientProcessPatches.cpp, src/game_server/server_mp/sv_network_mp.cpp, src/game_server/win32/win_net.cpp, tests/game_server/TransportLifecycleTests.cpp |
| 同目录其他测试二进制 | 与 T-2 验收快照一致 |
| build/stage 与 distribution 中的同名副本 | [] |

**复核判定：`CONSISTENT_WITH_FROZEN_SOURCES`** —— 该二进制是本地 MSVC 14.44.35207 工具链于 2026-10-10 14:49:35-14:50:05 由 79 个对象文件链接产生，其源码仍与 T-1 冻结哈希逐一相符，**不是被替换或外来的二进制**。

**局限（必须说明）**：无法证明它与重建前的 T-2 验收二进制**逐字节相同**，因为旧产物已被覆盖且未留存；现有证据是「构建溯源 + 源码同一性 + 行为一致（124/0，与 T-2.3 记录相同）」三者的组合。若要逐字节复现，需要可重复构建（如 /Brepro），本任务不构建、不部署。

## 6. 授权范围 vs 实际执行范围

| 类别 | 内容 |
| --- | --- |
| **本任务授权** | Stage 1 只读预检；文件读取与哈希；git 只读查询；离线单测；预编译离线 gtest；四个项目端口的瞬态 UDP 绑定（立即关闭，不设 SO_REUSEADDR） |
| **实际执行** | 上述全部；另外对插件文件做 PE 导出表解析、对真实生成的控制脚本做产物分析、对 T-2.4-C 证据做哈希 |
| **未授权且未执行** | 附加任何 CODOL 进程（**附加数 0**）；调用 CODOL_GameServerSetEnabled；端口释放探测；终止任何进程；git reset/clean/rebase；ol_deploy；构建/替换/部署生产产物 |
| **越权动作** | **0** |

## 7. 失败 / 异常 / 跳过 / 未验证清单

- **KNOWN_FAILURE** — caller python suite：test_only_dedicated_uses_native_qa_launch_bypass, pre-existing since T-2.3 / T-2.4-C, no new failure
- **DEVIATION** — T-1 transport artifact hash match：DEV-1, explained and pre-existing
- **SKIPPED** — build/stage prebuilt test binaries：not present in build/stage; the T-1 gtest was run from build/bin/release instead

未验证事项：
- no CODOL process was started, attached, injected, probed or terminated (attached count = 0)
- the nine exports are confirmed in the FILE export table, not in the LOADED plugin module (that is Stage D2)
- the status path has never executed against a real client
- CODOL_GameServerSetEnabled(false) has never been called (Stage E not authorized)
- transport.bound / transport.port / port release have no runtime evidence (Stage F not authorized)
- Stage C proved the x86_64 frida-agent path; the 32-bit client will use the x86 agent, which is untested on a real target
- no client/server session has been established (no socket ownership evidence for 28960 / 28961 / 28962 / 28970)

## 8. Stage D 授权申请（具体目标、具体风险、待批准动作）

### 8.1 具体目标

| 项 | 值 |
| --- | --- |
| 沙箱 | E:/CODOL_SANDBOX/RUN001 |
| 目标映像 | codoMP_client_shipRetail.exe，32 位，SHA-256 `36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537`，FileVersion 1649370 |
| 插件 | Ayria/Plugins/CodolGameServer.Localnet32，SHA-256 `6D493B820E84A21B096C9914616B75DCEC488920D7AC76867049B20C5C6B2021` |
| 客户端数量 | **1 个** dedicated 客户端 |
| 启动方式 | CodolGame.py launch-dedicated --game-dir E:/CODOL_SANDBOX/RUN001（**不修改** config/codol-game-dir.txt） |
| 附加次数 | **1 次**，仅 status，--sample-seconds 0 |
| 明确禁止 | --disable / --enable / 终止进程 / 端口释放探测 |

### 8.2 待批准动作（逐条）

1. 在沙箱启动 **一个** dedicated 客户端进程；
2. 对该 PID 做身份校验：PID 唯一 + 映像名 + 映像路径 + SHA-256 + FileVersion（不一致立即中止）；
3. 向该 PID **附加一次 Frida**（32 位目标使用 **x86** frida-agent，该路径 Stage C 未覆盖）；
4. 执行**一次** CodolGameServerControl.py --pid <pid> --sample-seconds 0，并逐项记录九个必需导出在**已加载模块**中的查询结果（名称、查找模块/API、地址是否为空、所属模块、异常、分类）；
5. 采集实验前后进程与端口快照、工具 JSON / 退出码 / stderr、插件日志、产物哈希；
6. **不终止**客户端，保持运行并报告。

### 8.3 已知风险（需明确接受）

| # | 风险 | 等级 | 说明 |
| --- | --- | --- | --- |
| R1 | 目标内安装**异常处理器** | 中 | 生成脚本行 46，改变异常处理路径 |
| R2 | 目标内安装**最多 4 个 Interceptor 钩子** | **中高** | 行 76-85，patch 退出/终止相关导出 |
| R3 | **调用 8 个插件 Get*Status 导出** | 中 | 插件契约上应为只读，但从未在真实目标上验证 |
| R4 | 读取固定 RVA 客户端内存 | 中 | RVA 与构建不匹配时读到无关字节（仅入日志） |
| R5 | 目标内分配内存 | 低 | 脚本内 Memory.alloc |
| R6 | **32 位 x86 agent 路径未验证** | 中 | Stage C 验证的是 x86_64 agent |
| R7 | 反作弊 / TenProtect 类组件可能对附加有反应 | **未知** | 沙箱含 ACE-DRV32.dll、TGuard 目录 |
| R8 | 客户端可能崩溃或行为异常 | 未知 | 出现即按中止条件停止 |

### 8.4 Stage D 验收条件（缺一不可）

1. 目标身份四项证据完整（PID 唯一 / 映像名 / 映像路径 / SHA-256 + FileVersion）；
2. 九个必需导出在**已加载模块**中逐项记录；
3. status 实际执行并返回，结果来自**真实插件**（after 字段非默认值、非超时回退、非模拟数据）；
4. **没有**把 unavailable / refused / 异常 / 超时误判为 confirmed；
5. 原始日志、环境记录、证据哈希齐全；
6. 未发生未授权状态变更（未调用 setEnabled、未终止进程、未做端口释放探测）。

> 附加成功、脚本执行成功、或返回一个 JSON 对象，**都不足以**单独判定 Stage D 通过。

### 8.5 中止条件

目标身份不符 / 指纹与基线不一致 / 出现未授权操作 / 脚本异常无法解释 / 结果自相矛盾 / 客户端崩溃挂起 / 出现反作弊迹象 / 回归新增失败 —— 立即停止、保留现场、**不自动进入 Stage E**。

## 9. 最终报告必须回答的十个问题

| # | 问题 | 答案 |
| --- | --- | --- |
| 1 | 实际 CODOL 目标是否通过身份校验？ | **文件级通过**：路径、大小 7841344、SHA-256 36997674B18F2896...、FileVersion 1649370 与已批准基线逐项一致，verify-target exit 0。**运行时（PID）尚未校验**，因为未获授权附加 |
| 2 | 九个必要插件导出分别是什么结果？ | **文件级 9/9 存在**（插件导出表 53 个导出，CODOL_* 50 个）；**运行时逐项结果 = 0**，Stage D2 未授权 |
| 3 | 哪一条控制路径已经在真实目标上执行？ | **没有**。真实目标上执行的控制路径数 = **0**（附加数 0） |
| 4 | 服务器停止入口是否被实际调用？ | **否**。Stage E 未授权，CODOL_GameServerSetEnabled 从未被调用 |
| 5 | 若被调用，返回结果与实际状态变化是否一致？ | **不适用**（未调用） |
| 6 | 哪些套接字或端口已经得到真实释放证据？ | **无**。28960 / 28961 / 28962 / 28970 当前无监听、无占用、均可绑定，但这只是**实验前基线**，不是释放证据 |
| 7 | 客户端是否仍然存活？ | **没有客户端在运行**（匹配进程 0），既未启动也未终止 |
| 8 | 是否已经实际建立客户端与服务器会话？ | **否**。无任何会话、无套接字所有权证据 |
| 9 | 距离玩家进入对局，当前最明确的阻塞点是什么？ | **Stage D 授权**（唯一瓶颈）。在真实客户端上确认“插件已加载 + 9 个必需导出在已加载模块中存在 + status 返回真实状态”之前，无法区分启动上下文、传输层、握手或会话层的故障。次要阻塞：停止入口与传输层从未在真实目标上运行 |
| 10 | 下一步最小、最有价值且经过授权的真实实验是什么？ | **Stage D**：单客户端、一次 status、含完整身份指纹与前后快照（§8）。它同时回答 Q1 / Q2 / Q3，且**不改变插件 enabled 状态** |

## 10. 未验证事项

- no CODOL process was started, attached, injected, probed or terminated (attached count = 0)
- the nine exports are confirmed in the FILE export table, not in the LOADED plugin module (that is Stage D2)
- the status path has never executed against a real client
- CODOL_GameServerSetEnabled(false) has never been called (Stage E not authorized)
- transport.bound / transport.port / port release have no runtime evidence (Stage F not authorized)
- Stage C proved the x86_64 frida-agent path; the 32-bit client will use the x86 agent, which is untested on a real target
- no client/server session has been established (no socket ownership evidence for 28960 / 28961 / 28962 / 28970)

## 11. 关联产物

- T2_5_RESULTS.json（逐项状态：PASS / PASS_WITH_DEVIATION / NOT_AUTHORIZED）
- T2_5_SHA256_MANIFEST.txt
- stage1_evidence.json、t1_regression_evidence.json
- raw_*.log（每条命令的 argv、cwd、起止时间、返回码、原始 stdout/stderr）
- generated_control_script.js、control_script_inventory.json、plugin_export_table.json
- raw_process_table.json（全机进程表快照）
- T-2.4-C 证据哈希见 T2_5_RESULTS.json 的 checks[P1.10]

