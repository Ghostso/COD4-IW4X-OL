# TOOLCHAIN_REQUIREMENTS — 工具链清单（阶段 F，2026-10-09）

**只准备方案，不安装任何工具。** 所有需求均来自仓库内可核验的声明（路径 + 行号），不凭猜测。

状态定义: `VERIFIED`（已有可复核证据）/ `MISSING`（已检查且不存在）/ `UNKNOWN`（当前无法确认）/ `NOT_AUTHORIZED`（需用户授权才能执行）。

## 1. 构建系统与编译器

| # | 组件 | 版本 / 架构要求 | 证据 | 当前状态 | 验证命令 |
| --- | --- | --- | --- | --- | --- |
| 1 | **xmake** | **≥ 3.0.9** | `xmake.lua:3` `set_xmakever("3.0.9")`；`tools/build.ps1:12-21` 从 PATH 或 `D:\Program Files\xmake\xmake.exe` 解析 | **MISSING** | `xmake --version` |
| 2 | **MSVC**（Visual Studio C++ 工具链） | 必须能产出 **x86** 目标 | `xmake.lua:10` `set_toolchains("msvc")`；`tools/build.ps1:45` `xmake f -p windows -a x86` | **MISSING** | `vswhere.exe -all -products * -property installationPath`；`cl` banner 应含 `for x86` |
| 3 | **Windows SDK** | 随 VS C++ 工作负载 | 隐含要求（`windows` 平台 + MSVC 链接） | **MISSING**（无 VS 即无 SDK） | `vswhere -requires Microsoft.VisualStudio.Component.Windows10SDK` |
| 4 | 语言/运行库配置 | `c++latest`；release **`MT`**（静态 CRT），debug `MTd`；release 启用 LTO | `xmake.lua:13`、`:19`、`:22`、`:24` | 由 1-3 决定 | 构建时 `xmake f -p windows -a x86 -m release -y` 的回显 |
| 5 | 编译器/链接器开关 | `/Zc:__cplusplus /permissive- /arch:SSE2`；`/INCREMENTAL:NO` | `xmake.lua:27`、`:28` | 由 1-3 决定 | 同上 |
| 6 | **系统库 syslinks** | `user32`、`advapi32`、`crypt32` | `xmake.lua:49`；原因见 `xmake.lua:30-48`（新版 VS 2026 (x86) 精简了 CRT 默认库集，导致 **34 个未解析外部符号**且**无源码改动**） | 由 3 决定 | 链接阶段无 LNK2019 |

> **重要风险**: `xmake.lua:30-48` 明确记录了一次 **Visual Studio 版本导致的链接回归**。因此“装了 VS 就行”不成立——需要记录**实际使用的 VS 版本**，并确认 `add_syslinks` 覆盖了该版本精简掉的默认库。

## 2. 依赖（vcpkg）

| # | 组件 | 版本 / 配置 | 证据 | 当前状态 | 验证命令 |
| --- | --- | --- | --- | --- | --- |
| 7 | **vcpkg** | `VCPKG_ROOT` 指向含 `vcpkg.exe` 的目录；否则回退 `E:\Source\Repos\Main\vcpkg` | `tools/build.ps1:23-32` | **MISSING** | `Test-Path $env:VCPKG_ROOT\vcpkg.exe` |
| 8 | **vcpkg baseline** | `aa2d37682e3318d93aef87efa7b0e88e81cd3d59` | `xmake.lua:57`、`vcpkg.json:5` | **UNKNOWN**（需 vcpkg 存在后才能解析） | `vcpkg x-update-baseline --dry-run` / 检查 `vcpkg.json` 解析 |
| 9 | **vcpkg triplet** | **`x86-windows-static`** | 由 `set_allowedarchs("windows|x86")`（`xmake.lua:6`）+ 静态 CRT `MT`（`xmake.lua:22`）+ preflight/PREREQUISITES 记录推导 | **MISSING** | `Test-Path $env:VCPKG_ROOT\triplets\x86-windows-static.cmake` |
| 10 | **OpenSSL** | `vcpkg::openssl`（**静态 x86**） | `xmake.lua:58-61`；消费方 `ol_backend:170`、`ol_game_server:211`、`ol_backend_tests:254`、`ol_game_server_tests:268`、`ol_lua_runtime_tests:320`、`ol_archived_tls_probe:389` | **MISSING** | `Test-Path $env:VCPKG_ROOT\installed\x86-windows-static\include\openssl\ssl.h` |
| 11 | **libcrypto 传递依赖** | `crypt32`、`ws2_32`、`advapi32`、`user32` | `xmake.lua:42-46` 引用 vcpkg 自带 `libcrypto.pc` 的 `Libs:` 行 | 由 10 决定 | 链接阶段无 LNK2019 |
| 12 | **mhook** | `vcpkg::mhook`，同 baseline | `xmake.lua:62-65`；消费方 `ol_localnetworking:148`、`ol_platformwrapper:159`、`ol_localnetworking_tests:337` | **MISSING** | `vcpkg list mhook` |

## 3. 依赖（xmake-repo，**需要网络**）

| # | 组件 | 版本 | 证据 | 当前状态 | 验证命令 |
| --- | --- | --- | --- | --- | --- |
| 13 | **nlohmann_json** | `3.12.0` | `xmake.lua:66` | **MISSING** | `xmake require --info nlohmann_json` |
| 14 | **lua** | `5.4.8`，`shared=false`（静态） | `xmake.lua:67` | **MISSING** | `xmake require --info lua` |
| 15 | **网络可达性**（xmake-repo / vcpkg 拉取） | 配置期需要 | `add_requires` 语义（`xmake.lua:58-67`） | **UNKNOWN**（本阶段未测试网络） | `xmake f -p windows -a x86 -m release -y` 是否成功解析 |

## 4. 构建入口（已由仓库证据确认）

| 项 | 命令 | 证据 |
| --- | --- | --- |
| 配置 | `xmake f -p windows -a x86 -m release -y` | `tools/build.ps1:45` |
| 构建（**文档入口**） | `xmake --group=plugins` | `tools/build.ps1:55` |
| 构建（单目标，合法但未文档化） | `xmake build ol_game_server` | `xmake.lua:191` |
| 测试 | `xmake test` | `tools/build.ps1:51` |
| 分发 staging | `tools\distribution\StageCodolRuntime.ps1 -Mode release -SkipBuild` | `tools/build.ps1:61`；输入 `distribution/runtime-components.json`（`StageCodolRuntime.ps1:26`） |
| 目标产物 | `build/bin/release/CodolGameServer.Localnet32`（+ `.map`） | `xmake.lua:194`（filename）、`:196`（/MAP）、`:51`（targetdir） |

**警告**: `ol_deploy` 是 `set_default(true)`（`xmake.lua:214-217`），其 `after_build`（`:219-243`）会读取 `config/codol-game-dir.txt` 并调用 `InstallCodolRuntime.ps1`。当前该文件指向**不存在**的 `D:\codo_3.19.26.13_fresh\CoD Online`。因此裸 `xmake build`（不带目标）可能触发一次面向缺失目录的部署。`tools/build.ps1:53-55` 用 `--group=plugins` 明确规避了这一点。

## 5. 未写入构建说明的依赖（已核验）

| 项 | 结论 | 证据 |
| --- | --- | --- |
| 代码生成步骤 | **无** | grep `before_build`/`on_build`/`on_load`/`generate`/`os.run` 于 `xmake.lua` 只返回 `after_build`（`:219`）与其 `os.vrunv`（`:235`），均为**部署副作用**而非生成步骤 |
| 资源/资产依赖 | 有，但**不在编译路径** | `assets/game_scripts/**`（staged 到 `Ayria/Assets/OlMod/GameScripts`）、`assets/backend/1004/**`、`assets/profile_seed/1004/**`、`distribution/legacy/Ayria/**`、`distribution/runtime-components.json` |
| 测试 fixture | 有，随仓库提交 | `tests/game_server/Fixtures/*.bin`（`mp_playerdata.def.1649370.bin`、`mp_playerdata.def.3333.bin`、`profile-69420.olfinal.document.bin`、`profile-seed.3333.document.bin`）、`tests/backend/Fixtures/**` |
| `E:\Source\Repos\Main\vcpkg` 回退路径 | 不存在 | 本次有界搜索未在该路径找到 `vcpkg.exe` |

## 6. 安装计划（**未授权，不执行**）

| 步骤 | 内容 | 状态 |
| --- | --- | --- |
| S1 | 安装 Visual Studio 2022（Desktop development with C++ + Windows SDK） | `NOT_AUTHORIZED` |
| S2 | 安装 xmake ≥ 3.0.9，加入 PATH（或置于 `D:\Program Files\xmake\xmake.exe`） | `NOT_AUTHORIZED` |
| S3 | 安装 vcpkg，设置 `VCPKG_ROOT`（或置于 `E:\Source\Repos\Main\vcpkg`） | `NOT_AUTHORIZED` |
| S4 | `vcpkg install openssl:x86-windows-static mhook:x86-windows-static` | `NOT_AUTHORIZED` |
| S5 | 解析 xmake-repo 的 `nlohmann_json 3.12.0` 与 `lua 5.4.8`（需网络） | `NOT_AUTHORIZED` |
| S6 | 记录每个工具与依赖的**实际版本**，然后配置并构建 | `NOT_AUTHORIZED` |

**在 S1-S5 完成并被授权之前，`TOOLCHAIN_READY` 与 `BUILD_CONFIRMED` 都不可能成立。**

## 7. 当前状态一览

| 状态 | 数量 | 项目 |
| --- | --- | --- |
| `MISSING` | 9 | xmake、MSVC、Windows SDK、vcpkg、triplet、OpenSSL、mhook、nlohmann_json、lua |
| `UNKNOWN` | 2 | vcpkg baseline 解析、网络可达性 |
| `VERIFIED` | 0 | —— |
| `NOT_AUTHORIZED` | 1 组（S1-S6） | 安装与构建执行 |

> 注: 构建入口与产物路径属于 `VERIFIED`（由 `xmake.lua` / `tools/build.ps1` 直接确认），但它们不是“工具链就绪”。**没有任何一个工具链组件当前处于可用状态。**
