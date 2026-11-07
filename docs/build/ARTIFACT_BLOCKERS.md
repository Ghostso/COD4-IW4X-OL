# BUILD-RISK-XMAKE-AFTER-BUILD-001 — `after_build` 钩子与 `--dry-run` 的副作用风险

**风险编号**：`BUILD-RISK-XMAKE-AFTER-BUILD-001`
**登记日期**：2026-10-11
**登记轮次**：COMBAT-P1-B2（编译验证轮）
**类型**：构建流程副作用 / 未经授权的自动部署
**严重度**：**高（潜在）**，本轮**实际影响：无**（触发条件恰好不满足）
**状态**：**OPEN（未消除，仅登记）**
**处置约束**：**禁止**以修改 `config/codol-game-dir.txt` 或任何构建配置的方式"绕过"本风险（本轮任务明令禁止）。

---

## 1. 事实（按发生顺序，均有原始证据）

| # | 事实 | 证据 |
|---|---|---|
| F1 | **无目标**的 `xmake build --dry-run`（工作目录 = F）**执行了默认目标 `ol_deploy` 的 `after_build` 钩子**，而非仅打印计划 | 该次调用的输出中出现 PowerShell 错误文本：`At F:\桌面\ol\ol-mod-olfinal\tools\distribution\InstallCodolRuntime.ps1:13 char:14` / `FullyQualifiedErrorId : PathNotFound,Microsoft.PowerShell.Commands.ResolvePathCommand` |
| F2 | 该钩子**调用**了 `InstallCodolRuntime.ps1` | `xmake.lua:214-243`：`target("ol_deploy")` → `set_default(true)`（`:217`）→ `after_build(function)`（`:219`）→ `os.vrunv("powershell.exe", {… "-File", installer, "-GameDirectory", game_directory, "-Mode", build_mode, "-SkipBuild"})`（`:235-242`）；`installer = tools\distribution\InstallCodolRuntime.ps1`（`:234`） |
| F3 | 脚本**在 `Resolve-Path` 处失败**，原因是目标目录不存在 | `InstallCodolRuntime.ps1:13` = `$GameRoot = (Resolve-Path -LiteralPath $GameDirectory).Path`；`config/codol-game-dir.txt` 内容为 `D:\codo_3.19.26.13_fresh\CoD Online`，**该目录不存在** ⇒ `PathNotFound`；脚本在 `:20` 调用 `StageCodolRuntime.ps1` **之前**中止 |
| F4 | **未发现**构建产物或沙箱部署件被写入 | 触发前/后逐项哈希比对（见 §2），**全部相同**；`build\stage` 目录 mtime 仍为 `2026-10-09 17:01:07`；沙箱 4 个插件 mtime 未变 |
| F5 | **`--dry-run` 不能被视为副作用隔离保证** | F1 即为反例：`--dry-run` 抑制了编译/链接任务，但**没有**抑制 `after_build` 钩子中的 `os.vrunv` |
| F6 | 本轮后续的**显式目标**构建**未触发**任何钩子 | `xmake build --dry-run ol_game_server` 的输出中危险行（`ol_deploy` / `InstallCodolRuntime` / `powershell` / `codol-game-dir` / `StageCodolRuntime`）= **0**；随后 `xmake build ol_game_server` 正常完成（exit 0，29.156 s），无部署、无进程启动 |

---

## 2. 触发时的写入核验（F4 的原始数据）

| 对象 | 触发前 | 触发后 | 判定 |
|---|---|---|---|
| `<F>\build\bin\release\CodolGameServer.Localnet32` | `DBA7273A…` / 6,559,232 / 2026-10-10 12:52:50 | 同 | 未写 |
| `<F>\build\stage\…\CodolGameServer.Localnet32` | `6D493B82…` / 6,556,672 / 2026-10-09 13:49:42 | 同 | 未写 |
| `<E:SANDBOX/RUN001>\Ayria\Plugins\CodolGameServer.Localnet32` | `6D493B82…` / 6,556,672 | 同 | 未写 |
| `<F>\build\bin\release\CodolGameServer.map` | `CDADB0E1…` / 9,429,721 | 同 | 未写 |
| `<F>\build\obj\…\EngineBindings.cpp.obj` | `E23EDA8B…` / 16,188,029 | 同 | 未写 |
| `build\stage` 目录 mtime | 2026-10-09 17:01:07 | 2026-10-09 17:01:07 | 未写 |

**结论**：由于 `config/codol-game-dir.txt` 指向**不存在的目录**，安装脚本在解析路径时即失败，**未进入暂存/复制阶段** ⇒ 本轮**无实际损害**。

---

## 3. 风险陈述

> **风险**：本项目存在一个**默认启用**的构建钩子（`ol_deploy.after_build`），它在满足"配置文件指向有效游戏目录"这一条件时会**自动执行部署/暂存**（`InstallCodolRuntime.ps1` → `StageCodolRuntime.ps1`）。任何**未显式限定目标**的构建调用——**包括 `--dry-run`**——都可能触发它。

**当前为何暂未造成损害**：`config/codol-game-dir.txt` 指向不存在的目录，安装器必然失败。**这是偶然的、脆弱的保护，不是设计上的保证**：

- 该保护**取决于外部文件内容**（`config/codol-game-dir.txt`），而该文件**可被单独修改**（历史上曾指向不同目录）；
- 一旦该文件指向真实的 CODOL 安装目录，**任何**一次无目标构建（含 `--dry-run`）都会执行真实部署，可能覆盖用户环境中的运行时文件；
- 该项目文件本身是**未跟踪**的工作区配置（`xmake.lua:221` 读取），无哈希门禁。

---

## 4. 触发条件与暴露面

| 触发条件 | 是否构成风险 |
|---|---|
| `xmake` / `xmake build`（**无目标**） | **是**（且这是 `set_default(true)` 的默认行为） |
| **`xmake build --dry-run`（无目标）** | **是**（本轮实测反例；`--dry-run` **不**隔离 `after_build`） |
| `xmake build -a` / `--all` | **是**（包含所有默认目标） |
| `xmake build ol_deploy` | **是**（显式调用部署目标） |
| `xmake build ol_game_server`（显式，本任务授权的形式） | **否**（依赖方向为 `ol_deploy → ol_game_server`；`ol_game_server` 无钩子；已由 `--dry-run` 与真实构建各验证一次） |
| `xmake build <任一测试目标>` | **否**（这些目标 `set_default(false)` 且无钩子） |

---

## 5. 建议的防护措施（**仅登记建议，本轮不实施**）

| # | 建议 | 说明 | 本轮是否实施 |
|---|---|---|---|
| M1 | **始终显式命名目标**（`xmake build ol_game_server`），**永不**使用裸 `xmake build` / `--all` / 无目标 `--dry-run` | 唯一已被验证有效的护栏 | 已在本轮遵守 |
| M2 | 构建前的**强制检查项**：① 命令是否显式命名目标；② 目标依赖闭包是否包含 `ol_deploy`；③ 目标是否有 `after_build`/`before_build` 钩子；④ 钩子是否调用 `os.vrun/os.vrunv/os.exec` | 见 §6 检查清单 | 已在 `COMBAT_P1_B2_BUILD_REPORT.md` §1 执行 |
| M3 | 在文档中修订 `BASELINE_ADJUDICATION` R6 的措辞，补入"**`--dry-run` 亦不免疫**" | 需获授权才能改动该既有文档 | **未实施**（不得覆盖既有证据） |
| M4 | 由维护者考虑给 `ol_deploy` 增加显式开关（如环境变量门禁）或将其 `set_default(false)` | 属构建配置变更，须单独授权 | **未实施** |
| M5 | **不得**以"临时清空 `config/codol-game-dir.txt`"作为绕过手段 | 本轮任务明令禁止修改该文件；且它掩盖风险而非消除风险 | **未实施** |

---

## 6. 后续构建前检查清单（可直接复用）

```
[ ] 命令是否显式命名目标？               （必须；禁止裸 xmake build / --all / 无目标 --dry-run）
[ ] 目标依赖闭包是否包含 ol_deploy？      （含则停止）
[ ] 目标是否有 after_build/before_build/on_build 钩子？（有则逐行审阅）
[ ] 钩子是否调用 os.vrun/os.vrunv/os.exec/os.run？    （有则确认其副作用范围）
[ ] config/codol-game-dir.txt 当前内容？  （记录；不得为此修改它）
[ ] 构建前是否已备份将被覆盖的产物？       （是）
[ ] 本次是否获得用户对该具体命令的授权？    （是）
```

---

## 7. 关联证据

| 用途 | 路径 |
|---|---|
| 本轮成功编译报告 | `COMBAT_P1_B2_BUILD_REPORT.md` |
| **原始事件报告（中止轮，逐字节保留）** | `_combat_p1_b2_evidence\attempt1_COMBAT_P1_B2_BUILD_REPORT_aborted.md`（SHA-256 `E473D42DB374DDEFA941B029753EBF301FEC9C6004AE60FC64BCF0B439DAA28B`） |
| 原始事件清单副本 | `_combat_p1_b2_evidence\attempt1_COMBAT_P1_B2_SHA256_MANIFEST.txt`（`5CDCFBC458E065C46143D50EA814BF5A79B2D7A3935A217B42916D8D69A2A27A`） |
| 钩子定义 | `<F>\xmake.lua:214-243` |
| 安装脚本 | `<F>\tools\distribution\InstallCodolRuntime.ps1`（失败行 `:13`；后续调用在 `:20`） |
| 触发配置 | `<F>\config\codol-game-dir.txt`（内容 `D:\codo_3.19.26.13_fresh\CoD Online`，**该目录不存在**） |
| 构建前备份与哈希 | `_combat_p1_b2_evidence\prebuild\`（7 制品 + `PREBUILD_HASHES.txt`） |
| 完整编译日志（成功轮） | `_combat_p1_b2_evidence\logs\build_ol_game_server_20261011.log` |

---

## 8. 登记纪律声明

- 本文件为**新建**风险记录；根目录未发现既有"风险台账"文件，故未采用追加方式。
- **未覆盖**任何原始事件报告：上一轮同名报告已**逐字节复制**保留（见 §7），本文件的登记不改变其内容。
- **未修改**构建配置、`config/codol-game-dir.txt`、源码、RVA、ABI、门禁或协议常量。
- **未借登记风险之名**实施任何构建/部署/运行操作。
- 本风险**仍为 OPEN**：防护措施 M1/M2 是**流程纪律**，代码/配置层面的消除（M3/M4）需单独授权。
