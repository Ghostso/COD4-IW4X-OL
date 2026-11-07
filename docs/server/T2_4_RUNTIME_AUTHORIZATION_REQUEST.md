# T2_4_RUNTIME_AUTHORIZATION_REQUEST — 真实 Frida 运行时验证授权申请

**日期**：2026-10-10
**工作树**：**F = `F:\桌面\ol\ol-mod-olfinal`**（HEAD `2a75bdd8872bb9f54006382a924c3006ec9affc2`，分支 `OLfinal-live`）
**申请性质**：**授权申请 + 最小实验协议**。本阶段**未启动游戏、未附加 Frida、未读内存、未部署、未终止任何真实进程**，也未新增任何代码。
**上游**：T-2.3 **有条件通过**（[T2_3_REGRESSION_REPORT.md](T2_3_REGRESSION_REPORT.md) §8）

---

## 0. 申请一句话

> 请求批准**分三段、可分别否决**的运行时验证：**Stage C（无害进程，不碰游戏）**、**Stage D/E（单个沙箱客户端，只读 + 一次状态改变）**、**Stage F（可选端口检查）**。
> 目标不是“证明 CODOL 复活成功”，而是**第一次取得真实 Frida 运行时的可追溯证据**，并把“工具成功 / 插件停止 / UDP 端口释放 / 客户端退出”四件事**分别**观测、分别判定。

## 1. 六个必须回答的问题

### Q1 实验需要什么权限和前置条件？

**权限**（逐项，可分别批准）：

| 编号 | 请求的权限 | 涉及范围 |
| --- | --- | --- |
| **P-C** | 向一个**无害非游戏进程**附加 Frida 并执行只读脚本 | 不涉及 CODOL、不涉及插件 |
| **P-D** | 向**沙箱客户端**附加 Frida，执行 `status`（只读） | 会在目标进程内安装异常处理器与终止调用钩子（见 Q3） |
| **P-E** | 向同一客户端执行**一次** `--disable` | 调用 `CODOL_GameServerSetEnabled(false)`，改变插件状态 |
| **P-F** | 由独立进程做一次端口占用/重绑定检查 | 只读 `netstat` + 一次 `bind` 尝试 |
| **P-T** | 按 §5 流程结束该客户端进程 | 仅在明确需要收尾时 |

**前置条件**（全部已满足，见 §2）：T-1 基线 7/7、工具 34/34、调用方 59/1（既有 `-qa`）、`verify-target` exit 0、`git diff --check` exit 0。

### Q2 每个假设由什么证据验证？

| 假设 | 主要证据 | 关键观测 |
| --- | --- | --- |
| **H1** Frida 16.5.9 能执行修复后的脚本 | C0 运行时 API 探针 + C1 出货脚本载入探针 | `Module.findExportByName(null, …)` 存在且行为正确；出货脚本无 JS 异常地执行到插件查找 |
| **H2** 工具能确认目标进程身份 | B3 构建指纹 + D1 工具身份校验通过 | 恰好一个 PID；映像名/路径/SHA-256/FileVersion 与基线逐项一致 |
| **H3** 能附加并找到必需插件导出 | **D1 只读 `status` 返回 confirmed** | 9 个必需导出全部解析成功；`after.installed/enabled/transport_bound` 有值 |
| **H4** `SetEnabled(false)` 被实际调用并返回明确结果 | E1 `--disable` 的 `result` 与退出码 | `confirmed`(0) 或 `refused`(2) ⇒ 已调用并返回布尔；`unavailable`/`tool-error` ⇒ **未成立** |
| **H5** 停止后 `transport.bound` 符合实现语义 | E2 只读 `GetTransportStatus` + E3 插件日志 | `confirmed` ⇒ `bound=0` 且日志无失败行；`refused` ⇒ `bound=1` 且日志有失败行 |
| **H6** 操作后进程状态符合预期 | E4 `tasklist` + 窗口/崩溃观察 | 进程仍在、无崩溃、无异常退出（本阶段**不**终止它） |
| **H7** 端口检查能区分释放与其他原因 | F1 `netstat -ano` 归属 + F2 `bind` 的**精确** WSA 错误 | 见 [T2_4_MINIMAL_EXPERIMENT_PROTOCOL.md](T2_4_MINIMAL_EXPERIMENT_PROTOCOL.md) §7 一致性判定表 |

### Q3 哪些步骤可能影响真实客户端？

| 步骤 | 影响 | 等级 |
| --- | --- | --- |
| D1 `status` | 脚本在**目标进程内**安装 `Process.setExceptionHandler` 与对 `ExitProcess` / `TerminateProcess` / `RaiseFailFastException` / `RtlExitUserProcess` 的 `Interceptor.attach` 钩子。这是**对运行中客户端的真实修改**，即使动作是只读的 | **中** |
| D1 `status` | 调用 60+ 个只读 getter 导出（不改变状态） | 低 |
| E1 `--disable` | 调用 `CODOL_GameServerSetEnabled(false)`：切换插件 enabled 状态、关闭 UDP transport、清空 `PendingWorldAsset`。**这是本实验唯一的状态改变动作** | **高** |
| E1/E2 | 插件会写日志（`Ayria\Logs`）；Frida 会在 `.runtime/frida` 下解包运行时文件 | 低 |
| F2 `bind` 探针 | 占用 28960 极短时间后立即关闭；**不会**连接、不会发包 | 低 |
| 任何附加 | 反作弊/TenProtect 类组件可能对附加敏感（本沙箱含 `ACE-DRV32.dll` / `TGuard` 目录） | **未知，须按 §5 立即中止** |

> **明确**：H4 成功**不等于** H5 成功；H5 成功**不等于** H6 成功；H6 成功**不等于**端口已释放。四者在本申请中**分别判定、分别记录**。

### Q4 哪些操作需要单独授权？

1. **启动任何 CODOL 客户端进程**（Stage B）——单独授权；
2. **向该客户端附加 Frida**（Stage D/E）——单独授权；
3. **执行状态改变动作** `--disable`（Stage E）——单独授权，与 D 分开；
4. **端口重绑定探针**（Stage F）——单独授权；
5. **终止客户端进程**（Stage G / §5 恢复）——单独授权；
6. Stage C 只附加无害进程，仍**单独授权**，且**不得**与上述任何一项合并批准。

### Q5 哪些情况必须立即中止？

摘要（完整矩阵见 [T2_4_ABORT_AND_RECOVERY_MATRIX.md](T2_4_ABORT_AND_RECOVERY_MATRIX.md)）：

- 构建指纹任一项不符或无法确认；PID 数 ≠ 1；
- 工具返回 `tool-error`；工具输出与退出码矛盾；
- 工具返回 `unavailable`（附加失败 / 插件未加载 / 必需导出缺失 / Frida 版本越界）；
- `confirmed` 与 `bound=1` 同时出现（语义矛盾）；
- `bound=0` 但 `netstat` 显示 28960 仍属于该客户端；
- 客户端崩溃、卡死、弹窗、掉线，或出现任何反作弊介入迹象；
- 任何需要读内存 / 调试器 / 抓包的冲动。

### Q6 如何在不误杀无关进程的前提下恢复？

1. **默认动作是“不终止”**：阶段结束或中止时，客户端**保持运行**，由申请人报告后等待指示；
2. 需要收尾时，**先复核再终止**：对 PID 执行 `tasklist /FI "PID eq <pid>"`，映像名必须仍等于基线映像；
3. 复核通过后，优先用**单 PID** 的 `taskkill /PID <pid> /T /F`；**不使用**批量 `CodolGame.py stop`；
4. 复核失败（映像不符/查询失败）⇒ **跳过该 PID** 并报告，**不得**强制终止；
5. **禁止**：无复核的批量终止、对未确认 PID 使用 `/T`、把强制终止当作默认恢复动作、工具失败后自动改附加到其它进程。

## 2. 基线与证据链确认

| 项 | 值 | 判定 |
| --- | --- | --- |
| F HEAD / 分支 | `2a75bdd8872bb9f54006382a924c3006ec9affc2` / `OLfinal-live` | 与 T-2.1/T-2.2/T-2.3 一致 ✅ |
| F `git status -uall` | **17** 条 | 与 T-2.3 末态一致 ✅ |
| T-2.3 清单逐文件校验 | 变更文件 6/6 **OK**、T-1 基线 9/9 **OK**、证据 10/10 **OK**、交付物 3/3 **OK** | ✅ |
| 沙箱目标 | `E:\CODOL_SANDBOX\RUN001\codoMP_client_shipRetail.exe`：7,841,344 B / `36997674…537` / FileVersion **1649370** | 与 `config/codol-target-build.json` 一致 ✅ |
| 沙箱插件 | `Ayria\Plugins\CodolGameServer.Localnet32`：6,556,672 B / `6D493B82…2021` | 一致 ✅ |
| Frida | **16.5.9**（frida-tools 13.0.1）；声明 `frida>=16.5,<19` | 安装 ∈ 声明区间 ✅ |
| 工具测试 / 调用方测试 | 34/0 · 59/1（既有 `-qa`） | ✅ |
| `verify-target --game-dir E:\CODOL_SANDBOX\RUN001` | `ok: true`，exit 0 | ✅ |
| `build\stage` mtime | `2026-10-09 17:01:07` | 未变，无部署 ✅ |
| D 历史副本 | `_e1_regression\ol-mod-olfinal`：HEAD 同、`statusCount=6` | **只读、未修改** ✅ |

**验收结论链**：T-1 基线（7/7、`checks=124`）→ T-2.1（四态分类 + 三层身份 + 多 PID，有条件通过）→ T-2.2（发现 G-B1，暂不就绪）→ T-2.3（G-B1/C1/C2/C3/C4 全解决，有条件通过）。证据链完整，无断点。

## 3. 目标与环境守卫

1. **沙箱参数显式**：所有客户端启动一律使用 `--game-dir E:\CODOL_SANDBOX\RUN001`，**不修改** `config/codol-game-dir.txt`（其默认值 `D:\codo_3.19.26.13_fresh\CoD Online` 在本机不存在）；
2. **目录级**：`CodolGame.py verify-target --game-dir E:\CODOL_SANDBOX\RUN001` 必须 exit 0；
3. **PID 级**：目标 PID 必须逐项满足 映像名 = `codoMP_client_shipRetail.exe`、`(Get-Process -Id <pid>).Path` = 基线路径、该文件 SHA-256 = `36997674…537`、FileVersion = `1649370`；
4. **任一不符或无法确认 ⇒ 停止**；
5. **PID 复用风险声明**：名称 + 路径 + 哈希的复核**缩小但不能消除** PID 复用窗口（读取与后续操作之间仍有间隔），**不是**原子身份保证，也**不是**密码学保证；
6. **环境记录**：Frida 16.5.9 / frida-tools 13.0.1 / Python 3.11.9 / 工具与配置哈希——全部在**不附加游戏**的前提下记录。

## 4. 最小实验协议与中止恢复

- 步骤、观测、逐项假设判定：[T2_4_MINIMAL_EXPERIMENT_PROTOCOL.md](T2_4_MINIMAL_EXPERIMENT_PROTOCOL.md)
- 中止/恢复矩阵：[T2_4_ABORT_AND_RECOVERY_MATRIX.md](T2_4_ABORT_AND_RECOVERY_MATRIX.md)

## 5. 请求批准的最小范围

| 若只批准一项 | 建议 |
| --- | --- |
| 最低风险、收益最大 | **仅 Stage C**（无害进程）。它即可取得**第一次真实 Frida 运行时证据**：证明 16.5.9 提供 `Module.findExportByName`、出货脚本能载入执行、且身份守卫在运行时会失败关闭。**完全不触碰 CODOL**。 |
| 次之 | Stage C + D（只读 `status`）。可验证 H2/H3，**不改变插件状态**。 |
| 完整 | Stage C + D + E（+ 可选 F）。只有 E 会改变插件状态。 |

## 6. 本阶段未执行 / 未证明

- 未启动任何 CODOL 客户端，未向任何游戏进程附加 Frida，未读内存，未部署，未终止真实进程；
- **未新增任何代码**（T-2.4 只产出文档）；探针脚本以**完整源码**形式内嵌在协议中，待授权后由操作者落盘到沙箱临时目录；
- 因此 **H1–H7 全部仍为“未验证”**；T-2.3 的“有条件通过”不因本申请而改变；
- 本申请通过 ≠ 兼容性已证明；只有执行后按 §7 逐项判定才算取得证据。

## 7. 判定规则（防止把四件事混为一谈）

> - **H4 成功**（插件被调用并返回布尔）**不蕴含** H5（transport 已释放）；
> - **H5 成功**（`bound=0`）**不蕴含** OS 层端口已释放，也**不蕴含** socket 是被本次调用关闭的（幂等路径下 `close()` 也返回 true）；
> - **H6 成功**（进程存活）**不蕴含**插件状态正确，也**不蕴含**进程会正常退出；
> - `WSACleanup()` 返回值被忽略（`win_net.cpp:166`），因此任何“Winsock 已清理”的表述都不成立；
> - 28961 / 28962 **不受** `SetEnabled(false)` 影响，若被释放则必须回到源码复核。

## 8. 关联交付

- [T2_4_MINIMAL_EXPERIMENT_PROTOCOL.md](T2_4_MINIMAL_EXPERIMENT_PROTOCOL.md) · [T2_4_ABORT_AND_RECOVERY_MATRIX.md](T2_4_ABORT_AND_RECOVERY_MATRIX.md) · [T2_4_SHA256_MANIFEST.txt](T2_4_SHA256_MANIFEST.txt)
- [T2_3_FRIDA_API_FIX_REPORT.md](T2_3_FRIDA_API_FIX_REPORT.md) · [T2_3_ENVIRONMENT_GUARDS_REPORT.md](T2_3_ENVIRONMENT_GUARDS_REPORT.md) · [T2_3_REGRESSION_REPORT.md](T2_3_REGRESSION_REPORT.md)
- [T2_2_EXPERIMENT_PROTOCOL.md](T2_2_EXPERIMENT_PROTOCOL.md) §10（G-C3 构建确认增补）
