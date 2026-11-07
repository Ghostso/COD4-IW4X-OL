# T2_4_ABORT_AND_RECOVERY_MATRIX — 中止条件与恢复流程

**日期**：2026-10-10　**状态**：**方案，未执行。**
**配套**：[T2_4_MINIMAL_EXPERIMENT_PROTOCOL.md](T2_4_MINIMAL_EXPERIMENT_PROTOCOL.md) · [T2_4_RUNTIME_AUTHORIZATION_REQUEST.md](T2_4_RUNTIME_AUTHORIZATION_REQUEST.md)

---

## 0. 三条不可违反的规则

> 1. **身份无法确认时，不得终止目标 PID。**
> 2. **工具失败时，不得自动重试、更不得改附加到其它进程。**
> 3. **强制终止不是默认恢复动作。默认动作是“保持运行并报告”。**

## 1. 立即中止总表

| # | 触发条件 | 检测方式 | 立即动作 | 禁止动作 |
| --- | --- | --- | --- | --- |
| A1 | 构建指纹任一项不符，或无法确认（路径/名称/SHA-256/FileVersion） | Stage B3 / Stage A4 | 停在 B，不进入 D；保存全部输出 | 不得“先试着附加看看” |
| A2 | `tasklist` 中目标映像 PID 数 ≠ 1 | Stage B2 / 任意阶段复查 | 停在当前阶段；记录全部 PID | 不得任选一个 PID 继续 |
| A3 | 工具返回 `unavailable`（附加失败 / 插件未加载 / 必需导出缺失 / Frida 版本越界） | E3 `result` 字段 | 停在当前阶段；保存完整 JSON 与 stderr | 不得重试、不得换 PID、不得忽略后继续 |
| A4 | 工具返回 `tool-error`，或 stdout 与退出码矛盾 | E3 | 停在当前阶段；保存 traceback | 不得把 `tool-error` 解释为插件行为 |
| A5 | 工具超时（`did not answer within …s`） | E3 `error` | 停在当前阶段；记录耗时 | 不得加大超时后重试 |
| A6 | 插件返回 `false`（`refused`, exit 2） | E3 | **保留证据后中止**；不重复调用 | 不得第二次 `--disable` 试图“改结果” |
| A7 | `confirmed` 与 `transport_bound = 1` 同时出现 | E1 + E2 | **立即中止**（语义矛盾） | 不得继续 Stage F |
| A8 | `transport_bound = 0` 但 `netstat` 显示 28960 仍属于该客户端 | F1 + E2 | **立即中止** | 不得改判为“已释放” |
| A9 | `transport_bound = 1` 但 28960 无归属且 bind 成功 | F1 + F2 + E2 | **立即中止** | 同上 |
| A10 | bind 探针返回 `WSAEADDRINUSE` 以外的错误 | F2 `winerror` | 记 `inconclusive`；不中止 H5 判定，但**不得**据此宣称释放 | 不得把未知错误当作“已释放” |
| A11 | 客户端崩溃 / 卡死 / 弹窗 / 掉线 | E6 + 目视 | **立即中止**；进入 §3 恢复 | 不得继续任何附加 |
| A12 | 出现反作弊/TenProtect/TGuard 介入迹象 | 目视 + 日志 | **立即中止**；进入 §3 恢复 | 不得再附加、不得排查式重启 |
| A13 | 28961 / 28962 在 `--disable` 后被释放 | E2 + F1 | **立即中止**（与源码分析不符） | 不得继续，须回源码复核 |
| A14 | 需要读内存 / 调试器 / 抓包才能继续 | 主观 | **立即中止** | 超出授权 |
| A15 | 日志或状态信息不足（`not-collected`） | 任一证据缺失 | 如实标注缺失；若该缺失使假设无法判定，则记为 **`inconclusive`** | **不得**用推断/猜测补齐 |

## 2. 九类失败的处理矩阵

### F1 身份校验失败

| 项 | 内容 |
| --- | --- |
| 检测 | ① 协议 B3 四项指纹任一不符/不可读；② 工具 `unavailable` 且 `error` 含 `refusing to attach` |
| 立即动作 | 停止；不附加、不终止；保存 `tasklist` 全量输出与 `.Path` 读取结果 |
| 禁止 | 终止该 PID；改附加其它 PID；忽略不符继续 |
| 恢复 | §3 R0（保持运行）→ 报告 → 等待指示 |

### F2 Frida 附加失败

| 项 | 内容 |
| --- | --- |
| 检测 | 工具 `unavailable` 且 `error` 含 `failed to attach to target` |
| 立即动作 | 停止；保存完整错误文本与退出码 |
| 禁止 | 自动重试；换 PID 重试；以管理员身份强行重试 |
| 恢复 | §3 R0 → 报告；由申请人判断是否为权限/保护组件问题 |

### F3 JS 脚本加载异常

| 项 | 内容 |
| --- | --- |
| 检测 | 工具 `tool-error`（退出码 1），stderr 含 `Traceback`，stdout `error` 含异常类型 |
| 立即动作 | 停止；完整保存 stdout + stderr（traceback 是定位依据） |
| 禁止 | 把 `tool-error` 当作插件拒绝或插件成功；在未分析前重跑 |
| 恢复 | §3 R0 → 报告；回到 T-2.3 的静态/离线证据比对 |

### F4 必需导出不存在

| 项 | 内容 |
| --- | --- |
| 检测 | 工具 `unavailable` 且 `error` 含 `does not export`（由 `nativeExport` 抛出） |
| 立即动作 | 停止；记录**缺失的导出名**与插件模块名 |
| 禁止 | 视为插件拒绝；视为环境噪声；换客户端重试 |
| 恢复 | §3 R0 → 报告；核对插件 DLL 是否与基线一致（`config/codol-target-build.json` 的 `plugin.sha256`） |

### F5 插件拒绝停止

| 项 | 内容 |
| --- | --- |
| 检测 | 工具 `result = refused`，退出码 2 |
| 立即动作 | **保留证据后中止**；记录 `error` 文本；随后做**一次**只读 `status` 记录 `bound` 与日志 |
| 禁止 | 第二次 `--disable`；把 `refused` 当成工具故障 |
| 恢复 | §3 R0 → 报告。`refused` 是**有效结论**：命题被否证，不是流程失败 |

### F6 工具超时

| 项 | 内容 |
| --- | --- |
| 检测 | 工具 `tool-error` 且 `error` 含 `did not answer within` |
| 立即动作 | 停止；记录实际耗时与完整输出 |
| 禁止 | 增大超时重试；对同一 PID 反复调用 |
| 恢复 | §3 R0 → 报告 |

### F7 停止后进程仍存活

| 项 | 内容 |
| --- | --- |
| 检测 | E4 `tasklist` 仍显示该 PID |
| 立即动作 | **这是 H6 的预期结果**（本阶段不终止进程）：记录，不采取动作 |
| 禁止 | 因为“还活着”就自动 `taskkill` |
| 恢复 | 无需恢复。若申请人希望结束，走 §3 R2（需单独授权） |

### F8 端口重绑定检查失败

| 项 | 内容 |
| --- | --- |
| 检测 | §4 一致性表落入“矛盾”或 `inconclusive` |
| 立即动作 | 矛盾 ⇒ **立即中止**；inconclusive ⇒ 记录精确 `winerror` 并标注不可判定 |
| 禁止 | 把 `inconclusive` 记为“已释放”或“未释放”；重复 bind 直到成功 |
| 恢复 | 矛盾 ⇒ §3 R0 + 报告；inconclusive ⇒ 报告并保留 H5 的原判定 |

### F9 日志或状态信息不足

| 项 | 内容 |
| --- | --- |
| 检测 | 证据 E4/E5/E6 任一缺失、日志文件不存在或为空 |
| 立即动作 | 如实记为 `not-collected` / `absent`；不推断内容 |
| 禁止 | 用其它阶段的值、源码语义或经验“补齐”缺失日志；把缺失当默认通过 |
| 恢复 | 报告该假设为 `inconclusive`；不重跑（重跑不会补出历史日志） |

## 3. 恢复流程

### R0（默认）：不终止，保持运行

1. 停止一切附加与工具调用；
2. 保存全部产物（stdout/stderr/退出码/`tasklist`/`netstat`/日志/哈希）；
3. 记录当前时间与阶段编号；
4. 报告中止条件编号与原始输出；
5. **等待指示**。

### R1：Frida 会话已断开但进程仍存活

无需动作。Frida 断开会话不改变插件状态；在证据中记录断开原因（如 `on_detached` 的 reason）。**不得**因为断开就重新附加。

### R2：需要结束客户端（**需单独授权**）

**前置**：已获 P-T 授权。**逐 PID 复核后再终止**：

``
# 1. 复核映像名（必须仍等于基线映像）
tasklist /FI "PID eq <pid>" /FO CSV /NH

# 2. 复核映像路径（必须仍等于基线路径）
(Get-Process -Id <pid> -ErrorAction Stop).Path

# 3. 只有 1 与 2 都通过，才执行单 PID 终止
taskkill /PID <pid> /T /F
``

| 复核结果 | 动作 |
| --- | --- |
| 映像名与路径**都**等于基线 | 允许单 PID `taskkill /PID <pid> /T /F` |
| 映像名或路径**任一**不符 | **跳过该 PID**，记录并报告。**不得**终止 |
| 查询失败 / 进程已不存在 | 跳过；进程已不存在时无需终止 |

**禁止**：批量 `CodolGame.py stop`（它会对早先枚举的 PID 逐个 `taskkill`）；对未复核 PID 使用 `/T`；把强制终止当作默认恢复动作。

### R3：无害进程（Stage C）的收尾

直接结束该无害进程即可（它不是 CODOL 进程，`/T` 无进程树风险）。**不得**把这条流程用于客户端。

### R4：`.runtime/frida` 残留

可选清理：删除 `F:\桌面\ol\ol-mod-olfinal\.runtime\frida`，或运行 `tools/runtime/CleanupRuntimeTemp.py`。该目录已被 gitignore 覆盖，不影响仓库状态。

### R5：仓库与部署目录

本实验**不产生任何仓库改动**。收尾时记录 `git status` 与 `build\stage` mtime，确认与实验前一致（`2026-10-09 17:01:07`）。若不一致 ⇒ 立即报告，**不得**自行 `git checkout` 或重新部署。

## 4. 与假设的对应

| 失败类别 | 主要影响的假设 |
| --- | --- |
| F1 身份校验失败 | H2 |
| F2 附加失败 | H3 |
| F3 脚本加载异常 | H1、H3 |
| F4 必需导出不存在 | H3 |
| F5 插件拒绝停止 | H4（成立但否定）、H5（负分支） |
| F6 工具超时 | H3、H4 |
| F7 进程仍存活 | H6（预期） |
| F8 端口检查失败 | H7 |
| F9 信息不足 | 全部（记 `inconclusive`） |

## 5. 关联交付

- [T2_4_RUNTIME_AUTHORIZATION_REQUEST.md](T2_4_RUNTIME_AUTHORIZATION_REQUEST.md) · [T2_4_MINIMAL_EXPERIMENT_PROTOCOL.md](T2_4_MINIMAL_EXPERIMENT_PROTOCOL.md) · [T2_4_SHA256_MANIFEST.txt](T2_4_SHA256_MANIFEST.txt)
