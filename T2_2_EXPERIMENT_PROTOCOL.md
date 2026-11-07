# T2_2_EXPERIMENT_PROTOCOL — 真实客户端停止验证最小实验方案

**日期**：2026-10-10
**状态**：**方案，未执行。需单独授权。** 当前判定为 **暂不就绪**（见 [T2_2_RUNTIME_READINESS_REVIEW.md](T2_2_RUNTIME_READINESS_REVIEW.md) §0 的阻塞项 B1）。
**适用范围**：本方案只回答一个问题——**`CODOL_GameServerSetEnabled(false)` 在一次真实调用中究竟保证了什么**。不回答兼容性以外的问题，不外推到双客户端或其它构建。

---

## 0. 前置门禁（**全部满足才可申请授权**）

| 门禁 | 内容 | 当前状态 |
| --- | --- | --- |
| **G-B1** | **修复 `CodolGameServerControl.py:270` 的 `Module.findGlobalExportByName`**，改用 `Module.findExportByName(null, exportName)`（或等价的 16.x API）；随后重跑 T-2.1 工具/调用方测试与 T-1 `REPRODUCE.ps1` | ❌ **未满足（硬阻塞）** |
| **G-C4** | 收敛 Frida 版本三方声明（安装 / `requirements-codol.txt` / 代码实际要求），并记录最终值 | ❌ 未满足 |
| **G-C1** | 以显式 `--game-dir E:\CODOL_SANDBOX\RUN001` 启动，**不修改** `config/codol-game-dir.txt` | ⏳ 协议已规定 |
| **G-C3** | 构建指纹基线已记录（§2.3），并纳入步骤 3 | ✅ 已采集 |
| **G-C2** | 终止前逐 PID 复核映像（§5.4） | ⏳ 协议已规定 |
| **G-C5** | （建议）修复后的脚本先在**无害非游戏进程**上做载入自检 | ❌ 未做 |
| **G-AUTH** | 用户**单独**给出的运行授权（启动客户端 + Frida 附加） | ❌ 未取得 |

> **在 G-B1 与 G-AUTH 满足之前，本协议的步骤一律不得执行。**

## 1. 授权边界

| 允许 | 禁止 |
| --- | --- |
| 启动**一个**客户端进程（`--game-dir E:\CODOL_SANDBOX\RUN001`） | 启动双客户端 / 房间对局 |
| 让 `CodolGameServerControl.py --disable` 附加该进程并调用导出 | 手工注入、调试器附加、断点、修改内存 |
| 只读插件日志（`Ayria\Logs\*.log`） | 读取进程内存（Frida 调用导出本身除外） |
| 只读 `GetStatus` / `GetTransportStatus` 返回值 | 抓包（如需另批） |
| 只读 `tasklist` / `Get-Process -Id <pid>` / 文件哈希 | 修改 `config/codol-game-dir.txt` / 部署到正式安装目录 |
| 记录前后哈希与日志 | 提交 Git / 推送 / `ol_deploy` |

**沙箱**：`E:\CODOL_SANDBOX\RUN001`（已存在）。**不触碰正式安装目录**。

## 2. 目标与假设

### 2.1 待验证命题

> 对构建 1649370 的**单个** `dedicated` 角色客户端，`--disable` 返回 `confirmed`（exit 0）时，调用后 `Server.status().enabled == false` 且 `SvUdpTransport::status().bound == false`。

### 2.2 明确不验证

- 不验证“本次真的关闭了 UDP socket”（句柄本已无效时 `close()` 也返回 true）；
- 不验证 `WSACleanup()` 成功（返回值被忽略）；
- 不验证 28961 / 28962 被释放（预期**不被** `SetEnabled(false)` 触及）；
- 不验证进程退出与停止的关系（S5 无关）；
- 不验证其它角色、其它构建、双客户端。

### 2.3 构建指纹基线（E-Env，已采集）

| 项 | 值 |
| --- | --- |
| 映像路径 | `E:\CODOL_SANDBOX\RUN001\codoMP_client_shipRetail.exe` |
| 大小 | 7,841,344 B |
| SHA-256 | `36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537` |
| FileVersion / ProductVersion | 1649370 / 1649370 |
| 插件 | `E:\CODOL_SANDBOX\RUN001\Ayria\Plugins\CodolGameServer.Localnet32`（6,556,672 B，SHA-256 `6D493B820E84A21B096C9914616B75DCEC488920D7AC76867049B20C5C6B2021`） |

## 3. 最小实验步骤

> 单进程、只读为主、**唯一写动作是 `--disable` 本身**。每步记录时间戳；任一步不符期望即进入 §5。

| 步 | 动作 | 期望 | 若不符 |
| --- | --- | --- | --- |
| 1 | 记录前置：F HEAD、`git status`、`.runtime/` 是否存在、`tasklist` 中**无** `codoMP_client_shipRetail.exe`、28960/28961/28962 空闲 | 全部符合 | **中止** |
| 2 | 启动**单个** `dedicated` 客户端（`--game-dir E:\CODOL_SANDBOX\RUN001`） | 进程出现；插件日志出现 | 中止 |
| 3 | **身份与构建确认**：`tasklist /FI "IMAGENAME eq codoMP_client_shipRetail.exe"` 必须**恰好一个** PID；`(Get-Process -Id <pid>).Path` 的 SHA-256 与 FileVersion 必须等于 §2.3 | 完全一致 | **中止**（C3） |
| 4 | 记录**附加前**端口占用：28960 / 28961 / 28962 | 记录实际 bound 情况 | — |
| 5 | 只读调用 `GetTransportStatus`（`status` 动作） | `bound=1`、`port != 0` | 中止 |
| 6 | **执行 `CodolGameServerControl.py --disable --pid <pid> --sample-seconds 0`** | 见 §4 的 S1–S5 | 见 §5 |
| 7 | 再次只读 `GetTransportStatus` | `bound=0`、`port=0` | 记为“拒绝”并中止后续成功判定 |
| 8 | 只读插件日志 | **不出现** `udp transport stop failed op=close error=`；**不出现** `game server disable failed` | 记为失败 |
| 9 | （可选，§3.1）由**独立进程**尝试 `bind(28960)` | 绑定成功 ⇒ OS 层确实释放 | — |
| 10 | 只读核对 28961 / 28962 | **仍被占用**（预期） | 记录差异；若被释放 ⇒ 中止并回源码复核 |
| 11 | 按 §5.4 的安全终止流程停止进程 | 进程消失 | 手工 `taskkill` |
| 12 | 记录后置哈希 / `git status` / `.runtime/` | 与步 1 一致（`.runtime/` 可能新增） | 记录 |

### 3.1 可选的 OS 层释放验证（步 9）

用独立小工具进程在 `127.0.0.1` 上尝试 `bind(28960)`：

- **成功** ⇒ OS 层确实释放（S4 的最强证据，与 T-1 探针同原理）。
- **失败**（`WSAEADDRINUSE`）⇒ 传输仍被占用 ⇒ 即使插件返回 `true`，OS 层也未释放 ⇒ **必须记为不一致**。

**前置**：仅在步 7/8 报告成功后执行；必须在 `--disable` **完成之后**运行；绑定失败**不得重试、不得强制**。

## 4. 证据采集最小集

| # | 证据 | 采集方式 | 能证明 | **不能**证明 |
| --- | --- | --- | --- | --- |
| **E0** | 目标身份 + 构建指纹 | 步 3（`tasklist` + `Get-Process -Id .Path` + SHA-256 + FileVersion） | 附加前该 PID 的映像文件是已记录的那一份构建 | 运行期未被内存补丁改写；不构成密码学身份保证 |
| **E1** | 操作前端口与 transport 基线 | 步 4/5 | 起始状态已知 | 停止语义本身 |
| **E2** | **工具结构化 JSON + 退出码** | 步 6 stdout / exit code | 工具的**分类结论**（`confirmed` / `refused` / `unavailable` / `tool-error`）及其退出码 0/2/3/1 | 插件内部状态；不证明资源已释放 |
| **E3** | `GetStatus.enabled` 与 `GetTransportStatus.bound/port` | 步 7（只读） | S2、S4 的**调用后**状态 | “本次真的关闭了一个 socket” |
| **E4** | 插件日志 | 步 8（只读） | S3/S4 的**失败路径是否发生** | 未记录的事件不存在 |
| **E5** | 28961 / 28962 仍被占用 | 步 10 | `SetEnabled(false)` 的作用范围（只覆盖 game transport） | 无 |
| **E6** | 进程从 `tasklist` 消失 | 步 11/12 | S5 | 退出是否干净 |
| **E7** | （可选）独立进程 `bind(28960)` | 步 9 | OS 层端口是否真的释放 | 其它端口/其它 socket |
| **E8** | 时间戳、文件哈希、逐步记录 | 全程 | 可复现性与可审计性 | 结论正确性 |

**证据与状态的对应**：S1←E2；S2←E3；S3←E2+E4；S4←E3+E4(+E7)；S5←E6。
**禁止**：仅凭 E2 的退出码 0 宣称 S4；仅凭一次运行宣称兼容性。

## 5. 中止条件与止损

### 5.1 立即中止（不做进一步尝试）

| # | 条件 | 理由 |
| --- | --- | --- |
| A1 | 目标映像名不匹配，或 PID 数 != 1，或 E0 的路径/哈希/版本不符 | 身份信息不足（C3） |
| A2 | Frida 附加结果无法确定（工具报 `unavailable`） | 未真正请求到插件 |
| A3 | 工具 stdout 与退出码矛盾，或报 `tool-error` | 分类未知/工具异常（含 B1 未修复的情形） |
| A4 | 插件明确返回 `false`（工具 `refused`，exit 2） | 命题已被否证；保留证据后停止 |
| A5 | 调用超时，或目标进程状态异常（卡死/掉线/报错弹窗） | 安全边界 |
| A6 | 观察到非预期的客户端或插件行为（崩溃、反作弊介入、非预期端口释放） | 安全边界 |
| A7 | 步 7 显示 `bound=1` 但步 6 退出码为 0 | **语义矛盾**，说明“成功”语义有误 |
| A8 | 步 9 绑定 28960 失败而步 6/7 报告成功 | OS 层未释放 |
| A9 | 28961/28962 被意外释放 | 与源码分析不符 |
| A10 | 出现任何内存读取/调试器/抓包需求 | 超出授权 |

### 5.2 中止动作

1. **立即停止后续步骤**，不再尝试其它参数或重试；
2. **保存全部日志**：工具 stdout/stderr、插件日志、`tasklist` 输出、端口状态、时间戳；写入本轮证据目录；
3. **不删除、不覆盖**任何日志（包括失败日志）；
4. 按 §5.4 安全终止进程；
5. 记录 `git status` 与 `build\stage` mtime，确认仓库与部署目录未被改动；
6. 报告：中止条件编号、原始输出、已采证据、未采证据。

### 5.3 误杀无关进程的防护

- **禁止**在没有 PID 复核的情况下执行批量终止；
- 停止工具只会 `attach` 到**已通过三层身份校验**的 PID，不会因停止请求而误杀；
- 风险在**终止路径**：见 §5.4。

### 5.4 终止前的 PID 复核（强制，C2）

`CodolGame.stop()` 的 `terminate_pids` 对**早先枚举到的 PID** 执行 `taskkill /PID <pid> /T /F`；G1 只保护 Frida 附加路径。因此本实验要求：

1. 终止**之前**，对每个 PID 执行 `tasklist /FI "PID eq <pid>" /FO CSV /NH`，确认其映像名仍等于 `codoMP_client_shipRetail.exe`；
2. 名称不符或查询为空 ⇒ **跳过该 PID** 并记录（该 PID 可能已被复用）；
3. 优先使用**单 PID 的手工** `taskkill /PID <pid> /T /F`，而不是批量 `stop`；
4. `/T` 会结束进程树：仅在该 PID 已复核为客户端时才使用。

## 6. 回滚

| 对象 | 回滚方式 | 验证 |
| --- | --- | --- |
| 客户端进程 | 经 §5.4 复核后 `taskkill /PID <pid> /T /F`（或 `CodolGame.py stop`） | `tasklist` 中无目标镜像 |
| `.runtime/frida` | 删除该目录，或 `tools/runtime/CleanupRuntimeTemp.py` | 目录不存在 |
| 沙箱 overlay | 不修改；如需清理 `Remove-Item E:\CODOL_SANDBOX\RUN001\Ayria -Recurse` | 仅当明确要求 |
| 仓库 | **不产生任何仓库改动**（本实验不修改源码） | `git status` 与实验前一致 |
| 正式安装目录 | **从未触碰** | `config/codol-game-dir.txt` 哈希不变 |

## 7. 不得声称的内容

- ❌ 不得把 `--disable` 返回 `true` 描述为“UDP socket 被本次调用关闭”——只保证“调用后 transport 不再 bound”；
- ❌ 不得把 `--disable` 描述为“插件已完全停止”——28961/28962 不受影响；
- ❌ 不得把 mock 测试、静态阅读或离线类型检查描述为真实客户端验证；
- ❌ 不得在未采集 S4 证据（E3+E4，最好含 E7）的情况下宣称“UDP 已释放”；
- ❌ 不得把工具退出码单独当作停止成功的证据（必须与 E3/E4 交叉核对）；
- ❌ 不得用一次成功运行外推到其它角色、其它构建或双客户端场景；
- ❌ 不得把进程名匹配描述为进程身份的密码学保证。

## 8. 停止规则与预算

| 规则 | 值 |
| --- | --- |
| 单次 `--disable` 超时上限 | 工具自身 `--sample-seconds 0` + 调用方 `timeout=20 s`（`CodolGame.py`）；独立调用时使用同等上限 |
| 实验总尝试次数 | **1 次**。失败即中止，不重试（重试会掩盖首次失败原因） |
| 启动的客户端实例数 | **1** |
| 允许的写操作 | 仅 `--disable`；其余全部只读 |
| 授权有效期 | 单次实验；结束后须重新申请 |

## 9. 关联交付

- [T2_2_RUNTIME_READINESS_REVIEW.md](T2_2_RUNTIME_READINESS_REVIEW.md) — 前置条件审查与阻塞项 B1
- [T2_2_SHA256_MANIFEST.txt](T2_2_SHA256_MANIFEST.txt)
- [T2_RUNTIME_VALIDATION_PREREQUISITES.md](T2_RUNTIME_VALIDATION_PREREQUISITES.md) — T-2 原始前置条件方案
- 证据：`_t2_2_evidence/`

---

## 10. T-2.3 增补：目标构建确认（G-C3）

**增补日期**：2026-10-10（T-2.3）。本节**取代** §2.3 的记录方式与步骤 3 的临时做法；其余各节仍然有效。

### 10.1 已批准基线

基线是**数据**，位于 `config/codol-target-build.json`（schemaVersion 1），由 `CodolGame.py verify-target` 读取。不存在“没有基线就当通过”的回退路径：基线缺失或格式非法一律失败关闭。

| 字段 | 值 |
| --- | --- |
| image | codoMP_client_shipRetail.exe |
| size | 7841344 |
| sha256 | 36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537 |
| fileVersion / productVersion | 1649370 / 1649370 |
| plugin.path | Ayria/Plugins/CodolGameServer.Localnet32 |
| plugin.sha256 | 6D493B820E84A21B096C9914616B75DCEC488920D7AC76867049B20C5C6B2021 |

基线值在批准时**直接读自确认的目标文件**（`E:\CODOL_SANDBOX\RUN001`），未从任何报告转录，也未从截断哈希推导。

### 10.2 可重复的确认命令

在客户端启动前与启动后各执行一次：

``
python tools/runtime/CodolGame.py verify-target --game-dir E:\CODOL_SANDBOX\RUN001
``

- 退出码 0 = 全部一致；1 = 任一不符或无法读取；2 = 未给出可解析的 `--game-dir`。
- 该命令**只读文件**，不启动游戏、不附加 Frida、不读内存。
- 它同时校验 game 目录是否存在、目标映像是否可读、大小/ SHA-256 / FileVersion 是否逐项等于基线，以及插件 DLL 是否在位且哈希一致。

### 10.3 逐 PID 运行时确认（步骤 3 修订）

`verify-target` 校验的是**目录里的文件**，它不能证明**正在运行的进程**就是那份文件。因此步骤 3 还必须对目标 PID 执行：

1. `tasklist /FI "IMAGENAME eq codoMP_client_shipRetail.exe"` ⇒ 必须**恰好一个** PID；
2. `(Get-Process -Id <pid>).Path` ⇒ 映像全路径，必须等于基线目录下的 `codoMP_client_shipRetail.exe`；
3. 对该全路径文件重算 SHA-256 与 FileVersion，必须等于 §10.1；
4. 任一项不符、为空或无法读取 ⇒ **中止**（§5.1 A1）。

**能证明**：附加前该 PID 的映像文件就是已批准构建。
**不能证明**：进程启动后是否被内存补丁改写；步骤 2→3 之间的文件替换竞态。因此这**不是**进程身份的密码学保证。

### 10.4 与 T-2.3 其他修复的关系

- **G-C2**：终止前的逐 PID 复核已进入 `terminate_pids`（见 §5.4 与 [T2_3_ENVIRONMENT_GUARDS_REPORT.md](T2_3_ENVIRONMENT_GUARDS_REPORT.md)）。
- **G-C4**：Frida 支持范围收敛为 `frida>=16.5,<19`；工具在触碰目标前校验安装版本，范围外一律 `unavailable` 且不附加。
