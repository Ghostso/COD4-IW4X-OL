# 14 — E：GO / NO-GO 裁决

> 任务：`EARLY-NATIVE-TAP-TOOLCHAIN-001`（为 `EARLY-NATIVE-TAP-BUILD-001` 准备可复现构建环境）
> 边界：**只读**。本轮未安装/升级任何工具链，未修改 PATH/注册表/全局设置，未修改源码、实验副本、候选补丁或大厅基线，未编译、未应用补丁、未运行游戏/服务端/launcher，未执行任何 `.cmd`/`.bat`/构建脚本。
> 状态词：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / NOT_OBSERVED / INSTRUMENTATION_BLOCKED / REFUTED。

## E.0 一句话裁决

- **设计/规格（工具链目标）：GO。** 目标工具链身份已被项目内证据与既有产物指纹双重锁定，规格明确、来源可追溯。
- **构建环境：NO-GO / INSTRUMENTATION_BLOCKED。** 本机**不存在**该 32 位 MinGW-w64/NASM 工具链，无法构建。
- **运行实验：NO-GO。** 无可运行候选产物，前置条件未满足。

`GO`（设计/规格）仅表示“目标已确定、方案可复现”，**不代表已获得构建或运行授权，也不代表已完成任何编译验证**。

## E.1 逐项通过条件与阻塞项

| # | 条件 | 结果 | 状态 |
|---|---|---|---|
| A1 | 已确认主机 OS/架构 | Windows 10 22H2 (10.0.19045) x64 | **CONFIRMED** |
| A2 | 已盘点 PATH 中的编译器/汇编器/资源编译器/构建工具 | 全部 NOT_FOUND；`cc` 仅为 Claude 配置档脚本 | **CONFIRMED（环境检查）** |
| A3 | 已检查常见 MSYS2/MinGW/VS 安装位置 | MSYS2/MinGW 全部不存在；VS Build Tools 2022 存在 | **CONFIRMED（环境检查）** |
| A4 | 已提取项目 README/Makefile/脚本/CI 的构建声明 | 是，见 `14_B` | **CONFIRMED** |
| A5 | 已确认 32 位 ABI/宏/汇编/旧编译器约束 | 是，见 `14_B` | **CONFIRMED** |
| A6 | 是否存在来源明确、可复现的锁定工具链依据 | 是：CI 固定 `i686-8.1.0-release-posix-dwarf-rt_v6-rev0` | **CONFIRMED** |
| A7 | 本机是否已安装该工具链 | 否（`C:\mingw810`、`C:\mingw32` 均不存在；无缓存 7z） | **CONFIRMED（环境检查）** |
| A8 | 是否已获得可构建环境 | 否 | **INSTRUMENTATION_BLOCKED** |
| B1 | 已产出候选工具链兼容性矩阵 | 是，`14_C`（9 行候选） | **CONFIRMED** |
| B2 | 已产出最小验证计划 | 是，`14_D`（6 步，独立授权） | **CONFIRMED** |
| C1 | 是否已执行任何编译/构建验证 | 否 | **NOT_EXECUTED** |
| C2 | 是否已应用补丁 | 否 | **NOT_EXECUTED** |
| C3 | 是否已运行游戏/服务端/launcher | 否 | **CONFIRMED（本轮操作记录）** |
| C4 | 是否修改原始源码/实验副本/补丁/基线 | 否 | **CONFIRMED（本轮操作记录）** |

## E.2 阻塞项汇总

1. **目标工具链缺失（决定性阻塞）**：本机不存在 `i686-w64-mingw32-gcc`/`gcc`/`g++`/`windres`/`nasm`/`make`/`mingw32-make`；`C:\msys64`、`C:\MinGW`、`C:\mingw810`、`C:\mingw32` 均不存在；全盘扫描无命中；注册表无相关安装项；无缓存安装包。
2. **替代路径也不可用**：WSL 无发行版（`Lxss` 为空）；工作区 LLVM 18 为不完整解压且目标为 `windows-msvc`；MSVC 存在但 ABI/工具集不兼容（缺 GCC/NASM/windres）。
3. **精确版本约束**：既有二进制与 597 个 `.o` 由 **GCC 8.1.0（i686-posix-dwarf-rev0）** 构建；CI 亦固定 8.1.0。任何较新工具链的适配性均为**未验证风险**，不能因“能编译简单 C 程序”而判定适配。
4. **无编译验证结果**：本阶段只做环境盘点，**不得**将盘点结论冒充编译验证结果。
5. **补丁应用检查未在本轮重跑**：`n3_hooks.diff` 的 `git apply --check` 通过记录来自上一阶段（`13_B`/`13_E`），本轮未重复执行。

## E.3 阶段 B/C/D 验收问题逐条回答

1. **当前 Windows 环境是否已有与 CODOL 服务端兼容的 32 位 MinGW/MSYS2 工具链？**
   否。**CONFIRMED（环境检查）**。目标工具链缺失，构建环境 **INSTRUMENTATION_BLOCKED**。
2. **项目声明的编译器/架构/运行库/依赖是什么？**
   GNU Make + `gcc`/`g++` + `-m32`（i686/PE32）+ NASM(win32) + Windres；静态链接 msvcrt、posix 线程、dwarf 展开；mbedTLS 2.16.6 + vendored tomcrypt/zlib；需 POSIX shell/coreutils + `python3`。**CONFIRMED（静态）**。详见 `14_B`。
3. **推荐哪条工具链？**
   **MinGW-w64 `i686-8.1.0-release-posix-dwarf-rt_v6-rev0`**（+ NASM + MSYS2/Git-Bash POSIX shell + windres），与既有二进制、597 个 `.o` 及 CI 完全一致。**推荐（首选）**。
4. **其他候选（MSYS2 当前 i686、MSVC、LLVM、winlibs、WSL、xmake、Git Bash）是否可用？**
   MSYS2 当前 i686 / winlibs / WSL 交叉为**候选但需验证**（版本非 8.1.0，属未验证风险）；MSVC、LLVM、Git Bash **不可用**（ABI/工具集不匹配或组件缺失）；xmake 仅为构建前端，不能替代 make/编译器。详见 `14_C`。
5. **是否已产出最小验证计划？**
   是，`14_D`，六步顺序：身份/版本 → 架构+基础编译 → 头文件/生成文件/第三方依赖 → 补丁应用检查 → 单独授权的对象编译/构建 → 构建成功后才重新评估运行实验。**CONFIRMED**。
6. **是否已执行验证第 4–6 步？**
   **否**。本任务未执行第 4–6 步，也未执行任何编译动作。**NOT_EXECUTED**。
7. **是否具备申请运行实验的条件？**
   否。无可运行候选二进制与运行时无扰动证据。**NO-GO**。

## E.4 后续建议（不含执行授权）

- 若要推进构建，需**单独授权**并取得 **MinGW-w64 i686-8.1.0-posix-dwarf-rt_v6-rev0**（官方 SourceForge 归档，与 CI 一致）+ NASM + POSIX shell 环境；建议在独立副本中先执行 `make objects`（仅编译、不链接）。
- 若无法取得 8.1.0，可评估 MSYS2 当前 i686 工具链作为**次选**，但必须视为“未验证适配”，不得直接替代。
- 任何构建尝试都须遵守 `14_D` 的隔离与单独授权原则，且不得覆盖 `bin\codol_dedrun.exe`/`bin\codol_dedrun_next.exe`。

## E.5 最终裁决

**设计/规格（工具链目标）：GO。构建环境：NO-GO / INSTRUMENTATION_BLOCKED。运行实验：NO-GO。**

推荐工具链：**MinGW-w64 GCC 8.1.0（i686-8.1.0-release-posix-dwarf-rt_v6-rev0）+ NASM + MSYS2/Git-Bash POSIX shell + windres**；本机当前未安装，需在获得授权后单独获取并验证。

> 本文件为**环境盘点与方案裁决**，非编译验证结果；未编译、未链接、未应用补丁、未运行任何程序。本阶段完成后停止，等待下一步指令。