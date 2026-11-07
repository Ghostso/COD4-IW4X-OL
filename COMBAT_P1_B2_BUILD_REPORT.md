# COMBAT_P1_B2_BUILD_REPORT — 显式目标编译验证结果（成功）

**任务**：COMBAT-P1-B2（执行 `xmake build ol_game_server`）
**日期**：2026-10-11
**最终状态**：**编译成功**（唯一的错误码类别均未出现；仅有既有告警）
**权威结论**：**B-1 的 297 行追加可通过目标 x86 release 配置的真实编译与链接。**
**严格边界**：**编译通过 ≠ 采样功能已验证，也 ≠ 运行时行为已验证。** 运行时事实（`0x0FEA20` / `0x8371A` 字节、运行时 `SizeOfImage`）仍未取得，仍为**待核验的静态期望值**。

---

## 0. 结论速览

| 项 | 结果 |
|---|---|
| 执行命令 | `xmake build ol_game_server`（**显式目标**；工作目录 = F） |
| 退出码 | **0** |
| 耗时 | **29.156 s**（日志内计时）/ 30 s（外部计时） |
| 编译范围 | **增量**：仅 `src\game_server\EngineBindings.cpp` 被重编 + 链接 |
| 错误 | **0**（`error C` = 0、`fatal error` = 0） |
| 关键错误码缺席 | `C2712` = 0、`C4530` = 0、`C3861` = 0、`C2065` = 0、`C2039` = 0、`C2248` = 0、`C2084` = 0、`C2365` = 0、`C2011` = 0、`C2079` = 0 |
| 告警 | 5 条，**全部为既有告警**（`C4324`×2 于 hpp、`C4456`×2 于 cpp:267/279、`C4244`×1 于 cpp:6728、`C4996`×1 于 cpp:7969）；**无一条落在 B-1 新增范围（3646–3952）** |
| 新产物 | DLL 6,565,376 B / `175BBC31…`；MAP 9,437,977 B / `9801C964…`；OBJ 16,223,173 B / `078D59A9…` |
| 导出数 | **仍为 53**（`.exp` 内容哈希未变）⇒ B-1"不新增导出"在编译产物中成立 |
| 副作用 | **无部署、无进程启动、无沙箱写入**；沙箱与 stage DLL 哈希未变 |

---

## 1. 阶段一：执行前安全检查（只读）

| # | 检查项 | 结果 |
|---|---|---|
| 1 | F HEAD / 分支 / 变更数 | `2a75bdd8872bb9f54006382a924c3006ec9affc2` / `OLfinal-live` / **18** 条；D = **6** 条 |
| 2 | `EngineBindings.cpp` B-1 差异 | `git diff --numstat` = **`297 0`**；885,136 B；SHA-256 `5B3794254DB79CEF1E74AA94E2ABBC4E0C41EC0F0CB0597C70C5970FD753BB6F` |
| 3 | 构建前备份与当前制品哈希 | 7 项（DLL/决定 stage DLL/沙箱 DLL/MAP/EXP/LIB/OBJ）与备份**逐一同哈希**（见 §3 构建前列） |
| 4 | `xmake.lua` 依赖与钩子 | `ol_deploy`（`:214`）为 `phony` + `set_default(true)`（`:217`），其 `add_deps`（`:218`）**包含 `ol_game_server`**；其 `after_build`（`:219-243`）调用 `os.vrunv("powershell.exe", …)`（`:235`）运行 `tools\distribution\InstallCodolRuntime.ps1`。**`ol_game_server`（`:191-213`）不含任何钩子（0 行）**。全文件仅此一处进程调用钩子。 |
| 5 | 显式目标是否可能间接触发部署 | **不可能**：依赖方向是 `ol_deploy → ol_game_server`（非反向），且 `ol_game_server` 无钩子 ⇒ 命名该目标不会纳入 `ol_deploy`。**并以显式目标的 dry-run 实证**：`xmake build --dry-run ol_game_server` 输出 88 条编译/链接计划，**危险行（ol_deploy / InstallCodolRuntime / powershell / codol-game-dir / StageCodolRuntime）= 0**。 |

**阶段一通过 ⇒ 允许执行编译。**（本轮**未**修改 `config/codol-game-dir.txt`，**未**修改任何构建配置。）

---

## 2. 阶段二：唯一授权的编译命令

```
工作目录 : F:\桌面\ol\ol-mod-olfinal
命令     : xmake build ol_game_server
工具链   : xmake v3.1.1+HEAD.3ba37a0d4
配置     : windows | x86 | release   (xmake.lua:7-9)
退出码   : 0
耗时     : 29.156 s（xmake 自报）
完整日志 : _combat_p1_b2_evidence\logs\build_ol_game_server_20261011.log
```

- 未使用裸 `xmake build`；未使用**无目标**的 `--dry-run`（上一轮的教训已遵守）。
- 未使用 `-r` / `-a` / `--group`；未清理、未全量构建；未构建其他目标；未调用 `ol_deploy`。
- 构建过程中**未出现**意外部署、进程启动或其他副作用（见 §3.6）。

---

## 3. 阶段三：结果与完整性核验

### 3.1 完整编译器输出（**全文，未过滤**）

日志共 **11 行**（原始 ANSI 颜色码保留在文件中；下列为去除颜色码后的全文）：

```
[ 85%]: <ol_game_server> compiling.release src\game_server\EngineBindings.cpp
F:\桌面\ol\ol-mod-olfinal\src\game_server\EngineBindings.hpp(2029): warning C4324: “CodolGameServer::EngineBindings”: 由于对齐说明符，结构被填充
F:\桌面\ol\ol-mod-olfinal\src\game_server\EngineBindings.hpp(2050): warning C4324: “CodolGameServer::EngineBindings”: 由于对齐说明符，结构被填充
src\game_server\EngineBindings.cpp(267): warning C4456: “record”的声明隐藏了上一个本地声明
src\game_server\EngineBindings.cpp(197): note: 参见“record”的声明
src\game_server\EngineBindings.cpp(279): warning C4456: “record”的声明隐藏了上一个本地声明
src\game_server\EngineBindings.cpp(197): note: 参见“record”的声明
src\game_server\EngineBindings.cpp(6728): warning C4244: “参数”: 从“const unsigned int”转换到“const uint16_t”，可能丢失数据
src\game_server\EngineBindings.cpp(7969): warning C4996: 'getenv': This function or variable may be unsafe. Consider using _dupenv_s instead. ...
[ 92%]: <ol_game_server> linking.release CodolGameServer.Localnet32
[100%]: build ok, spent 29.156s
```

> 该日志是**完整**的 stdout+stderr 合并输出（`2>&1 | Out-File`），**未经过滤**；总计 1,367 字节，已在 §4 记录 SHA-256。

### 3.2 第四节关键检查项的实际验证结果

| # | 检查项 | 实际结果 | 依据 |
|---|---|---|---|
| 1 | **C2712**（`__try` 与 C++ 对象析构） | **未出现** | 日志中 `C2712` 计数 = **0** ⇒ 含 `__try` 的 `ReadHostBytesSafely` 编译通过（其函数体内无带析构函数的对象） |
| 2 | **C4530** 及异常处理告警 | **未出现** | `C4530` 计数 = **0** |
| 3 | x86 `IMAGE_NT_HEADERS` 类型与布局 | **编译通过** | 无 `C2065`/`C2079`/`C2011` ⇒ 32 位变体在本配置下可用 |
| 4 | `VirtualQuery`、保护常量、Win32 符号 | **全部解析成功** | 无 `C3861`（找不到标识符）、无 `C2065` ⇒ `VirtualQuery` / `MEMORY_BASIC_INFORMATION` / `MEM_COMMIT` / `PAGE_*` / `GetEnvironmentVariableA` / `GetModuleFileNameA` / `GetCurrentProcessId` 均可见 |
| 5 | `<cstdio>` / `std::snprintf` / `std::to_string` | **编译通过** | 无 `C2039`、无 `C3861` |
| 6 | 配置 / 编译参数 / LTO | **已确认** | 配置 `windows|x86|release`；`xmake.lua:24` `set_policy("build.optimization.lto", true)` 启用；`:15` `set_warnings("all","extra")`；**未启用 `/WX`**（告警未致失败） |
| 7 | 是否存在与 B-1 无关的既有编译错误 | **无任何错误** | `error C` = 0、`fatal error` = 0 |
| 附加 | 权访问门禁常量（`EngineBindings::ExpectedTimestamp` 等） | **通过** | 无 `C2248`（不可访问成员） |
| 附加 | 名称冲突 / 重定义 | **无** | 无 `C2084` / `C2365` / `C2011` |
| 附加 | B-1 新增行自身的告警 | **0 条** | 全部告警行号 = `hpp:2029/2050`、`cpp:267/279/6728/7969`；**落在 3646–3952 的条数 = 0** |

### 3.3 目标文件是否重编

| 项 | 构建前 | 构建后 | 判定 |
|---|---|---|---|
| `EngineBindings.cpp.obj` 大小 | 16,188,029 | **16,223,173** | 变化 |
| mtime | 2026-10-09 13:49:21 | **2026-10-10 17:24:59** | 更新 |
| SHA-256 | `E23EDA8B97820B067FB91F2B5B4AE2ED5EBD215429FA6A26D31F6C600FF1F999` | `078D59A921ED042F178E2C750822488B04A97EA8310695702B7553E389FC2E23` | **已重编** |

> 仅此一个 TU 被重编（日志 `[85%]` 行只列出它），其余 TU 未动 ⇒ 印证 §1 第 3 项的"当前制品 = 备份"状态。

### 3.4 编译产物路径 / 大小 / 时间戳 / SHA-256

| 产物 | 大小 | 时间戳 | SHA-256 |
|---|---:|---|---|
| `<F>\build\bin\release\CodolGameServer.Localnet32` | **6,565,376** | 2026-10-10 17:25:21 | `175BBC31D6C972AC734F919C5D90064D45970BBFED9ADD7BFA85057CEBCFBBAF` |
| `<F>\build\bin\release\CodolGameServer.map` | **9,437,977** | 2026-10-10 17:25:21 | `9801C96438C1C61AD5199C8D3AFC2E2166210C98C0FCDCB3B75E7FF3E5AC41C5` |
| `<F>\build\bin\release\CodolGameServer.exp` | 10,708 | 2026-10-10 17:25:00 | `EC81A2CFA18A8B9888D539FF67A3E77C85D844698AE0055BEAC13C8624B5D580`（**内容未变**） |
| `<F>\build\bin\release\CodolGameServer.lib` | 19,374 | **2026-10-09 13:49:25** | `6B950231337B6D675F37779D24DEE980002828590CCB740813561FA06EC4D564`（**未重新生成**） |
| `<F>\build\obj\…\EngineBindings.cpp.obj` | 16,223,173 | 2026-10-10 17:24:59 | `078D59A921ED042F178E2C750822488B04A97EA8310695702B7553E389FC2E23` |

**新 DLL 的 PE 头（本轮只读解析）**：`signature=0x00004550`、`machine=0x014C`、`sections=5`、`TimeDateStamp=0x6ACA0481`（2026-10-10 17:25:21）、`SizeOfImage=0x007E2000`（构建前为 `0x007E0000`）、**导出名数 = 53（未变）**。

### 3.5 沙箱部署 DLL 未被覆盖（核验）

| 文件 | 大小 | 时间戳 | SHA-256 | 判定 |
|---|---:|---|---|---|
| `<E:SANDBOX/RUN001>\Ayria\Plugins\CodolGameServer.Localnet32` | 6,556,672 | **2026-10-09 13:49:42** | `6D493B820E84A21B096C9914616B75DCEC488920D7AC76867049B20C5C6B2021` | **未变** |
| `<F>\build\stage\codol\Ayria\Plugins\CodolGameServer.Localnet32` | 6,556,672 | **2026-10-09 13:49:42** | `6D493B820E84A21B096C9914616B75DCEC488920D7AC76867049B20C5C6B2021` | **未变** |

> **编译产物（`175BBC31…`）既未部署到 stage，也未进入沙箱。**

### 3.6 所有新生成 / 修改 / 覆盖的文件（构建范围内）

| 路径 | 动作 | 性质 |
|---|---|---|
| `build\bin\release\CodolGameServer.Localnet32` | **覆盖** | 构建产物（**已有构建前副本**，见 §4 §B） |
| `build\bin\release\CodolGameServer.map` | **覆盖** | 构建产物（已有副本） |
| `build\bin\release\CodolGameServer.exp` | **重写（内容相同）** | 构建产物（已有副本） |
| `build\obj\…\EngineBindings.cpp.obj` | **覆盖** | 构建中间产物（已有副本） |
| `build\deps\…\CodolGameServer.Localnet32.d` | 更新 | 依赖文件 |
| `build\deps\…\EngineBindings.cpp.obj.d` | 更新 | 依赖文件 |
| `.xmake\windows\x64\cache\{config,detect,history,toolchain}` | 更新 | xmake 配置缓存（gitignore） |
| `build\bin\release\CodolGameServer.lib` | **未变化** | 导出未变 ⇒ 导入库未重建 |

- **未观察到删除**。
- **局限（如实声明）**：本轮只对 **7 个已登记制品**做了构建前后哈希比对，**未**对整棵 `build/` 做构建前全量清单，因此**无法排除** `build/` 其它位置有被覆盖/新增的文件（xmake 的正常行为）。已核验的范围（7 制品 + 沙箱 + stage + 工作区 + 冻结基线）**全部符合预期**。

### 3.7 工作区与基线状态

| 项 | 结果 |
|---|---|
| F `git status --porcelain` | **18** 条（与编译前一致；`EngineBindings.cpp` 的 B-1 修改仍在，未因编译而改变） |
| F HEAD | `2a75bdd`（未变） |
| D `git status` / HEAD | **6** 条 / `2a75bdd`（未变） |
| `GOLDEN-LOBBY-001/REF_LOBBY_KIT` | **141 文件**，最新 mtime 仍 **2026-10-07 22:10:52**（**未触碰**） |
| 源码是否被修改 | **否**（未修改任何源码来消除编译错误——本轮也没有错误需要消除） |
| `config/codol-game-dir.txt` | **未修改** |

---

## 4. 交付物与证据

### 4.1 新增交付物

- `COMBAT_P1_B2_BUILD_REPORT.md`（本文件）
- `COMBAT_P1_B2_SHA256_MANIFEST.txt`
- `BUILD-RISK-XMAKE-AFTER-BUILD-001.md`（阶段四风险登记）

### 4.2 完整构建日志

- `_combat_p1_b2_evidence\logs\build_ol_game_server_20261011.log`（1,367 B，**全文未过滤**；SHA-256 见清单）

### 4.3 构建前备份（上一轮建立，本轮继续有效；本轮编译**覆盖的产物**均有副本）

- `_combat_p1_b2_evidence\prebuild\` 下 7 个制品 + `PREBUILD_HASHES.txt`

### 4.4 历史记录保留（**未覆盖原始事件报告**）

上一轮"中止/事件"报告与本轮同名，为不覆盖原始记录，已在改写前**逐字节复制**：

| 保留副本 | SHA-256 |
|---|---|
| `_combat_p1_b2_evidence\attempt1_COMBAT_P1_B2_BUILD_REPORT_aborted.md` | `E473D42DB374DDEFA941B029753EBF301FEC9C6004AE60FC64BCF0B439DAA28B` |
| `_combat_p1_b2_evidence\attempt1_COMBAT_P1_B2_SHA256_MANIFEST.txt` | `5CDCFBC458E065C46143D50EA814BF5A79B2D7A3935A217B42916D8D69A2A27A` |

> 上一轮事件（无目标 `--dry-run` 触发 `ol_deploy` 钩子、安装脚本在 `Resolve-Path` 失败、无写入）的完整原始记录保存在上述副本中；该事件的项目级风险已登记到 `BUILD-RISK-XMAKE-AFTER-BUILD-001.md`。

---

## 5. 阶段四：项目级风险登记

已新增 `BUILD-RISK-XMAKE-AFTER-BUILD-001.md`（**新建文件**；根目录未发现既有风险台账，故不采用追加方式；**未修改**任何既有文档，包括 `BASELINE_ADJUDICATION.md`）。要点：

- 无目标 `xmake build --dry-run` **曾触发** `ol_deploy` 的 `after_build` 钩子；
- 该钩子调用 `InstallCodolRuntime.ps1`；
- 脚本在 `Resolve-Path` 处因目标目录不存在而失败；
- 哈希与时间戳核验**未发现**构建产物或沙箱部署件被写入；
- **`--dry-run` 不能被视为副作用隔离保证**；
- 后续执行构建前必须检查：显式目标、依赖方向、钩子行为。

---

## 6. 未验证项（**不得**因编译通过而升级）

| # | 未验证 | 说明 |
|---|---|---|
| U-1 | **采样代码能否编译** | **本轮已验证通过**（唯一已解除项） |
| U-2 | 采样**运行时能否执行**、日志字段是否符合 schema | 未验证（未运行） |
| U-3 | 运行时 `TimeDateStamp` / `SizeOfImage` | 未验证；仍为静态期望值 |
| U-4 | RVA `0x0FEA20` = `55 8B EC 56 57`、RVA `0x8371A` = `83 7C 24 08 01 0F 94 C0` | **未验证；仍为待核验的静态期望值** |
| U-5 | "开关关闭时行为逐位不变"的二进制级证明 | 未做；LTO 下仅能行为级复核 |
| U-6 | 75 条既有守卫在真实运行时映像上是否成立 | 仍未可达（本实现刻意不放宽门禁） |
| U-7 | 新构建产物 `175BBC31…` 是否与沙箱/已批准目标一致 | 不一致，且**本轮未部署** |

---

## 7. 纪律声明

- 本轮**仅执行** `xmake build ol_game_server`（显式目标），**未**执行裸 `xmake build`、**未**执行无目标 `--dry-run`、**未**使用 `-r`/`-a`、**未**清理、**未**全量构建、**未**构建其他目标。
- **未调用 `ol_deploy`**；**未部署**；**未向沙箱复制任何文件**。
- **未启动、附加、注入或终止任何游戏进程**；未读取其他进程内存。
- **未修改** `config/codol-game-dir.txt`；**未修改**任何源码、构建配置、RVA、ABI、门禁或协议常量。
- 未执行 `reset`/`clean`/`rebase`/`commit`/`push`；未覆盖冻结大厅基线与既有证据（原始事件报告已逐字节保留，见 §4.4）。
- **未把编译成功等同于采样功能已验证**；**未把静态期望字节写成运行时事实**。
- **停止，不进入 B-3 部署 / B-4 客户端运行验证，等待用户单独授权。**
