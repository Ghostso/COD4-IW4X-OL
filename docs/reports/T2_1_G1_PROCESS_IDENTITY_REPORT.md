# T2_1_G1_PROCESS_IDENTITY_REPORT — PID 与目标进程身份校验

**日期**：2026-10-10
**工作树**：**F = `F:\桌面\ol\ol-mod-olfinal`**（HEAD `2a75bdd8872bb9f54006382a924c3006ec9affc2`，分支 `OLfinal-live`）
**修复范围**：`tools/runtime/CodolGameServerControl.py`（工具）、`tools/runtime/CodolGame.py`（调用方预检）
**结论**：**G1 已修复**。PID 身份在三个独立层次校验，任一层次失败即**失败关闭**；新增 19 项 G1 相关单测全部通过。剩余限制见 §6。

---

## 1. 缺陷回顾（T-2 验收审查 §4.1 / §7.1 G1）

修复前 `CodolGameServerControl.py:49-51`：

```python
def find_pid(device: frida.core.Device, requested: int | None) -> int:
    if requested is not None:
        return requested          # <-- 直接采信，零校验
```

- 调用方 `CodolGame.running_pids()` 用 `tasklist` 得到 PID，再经 `request_graceful_stop(pid)` 交给工具。
- `tasklist` 查询与 `device.attach(pid)` 之间存在 TOCTOU 窗口；PID 一旦被回收，Frida 会附加到**无关进程**。
- 附加到无关进程后，插件导出不存在 → JS 抛错 → 工具 exit 2 → 调用方把"环境故障"误判为"插件拒绝"（G2）。

## 2. 修复设计：三层校验，全部复用既有机制

| 层 | 位置 | 复用的既有机制 | 失败时的行为 |
| --- | --- | --- | --- |
| **L1 调用方预检** | `CodolGame.target_image_matches`（`CodolGame.py:629-647`） | 既有 `process_image_name(pid)`（`tasklist /FI "PID eq <pid>" /FO CSV`），即 `stop()` 早已用于 room-owner 校验的同一函数 | 返回 `unavailable`，**不启动停止工具子进程** |
| **L2 工具附加前** | `CodolGameServerControl.find_pid`（`CodolGameServerControl.py:84-106`） | 工具既有的 `device.enumerate_processes()` 与新增的 `image_matches_target` 名字规则 | 返回 `unavailable`（exit 3），**不调用 `device.attach`** |
| **L3 工具附加后** | 注入 JS 身份守卫（`CodolGameServerControl.py:200-213`） | 脚本**原本就使用**的 `Process.enumerateModules()[0]`（同一对象已用于固定偏移 `0x162E7EC`） | 返回 `unavailable`（exit 3），**在解析/调用任何插件导出之前抛出** |

**没有新增第二套进程枚举逻辑**：L1 用 tasklist（既有），L2/L3 用 Frida 枚举（既有），两者各自只有一处名字规则。

### 2.1 L2 关键改动

```python
def find_pid(device, requested):
    processes = device.enumerate_processes()          # 一次枚举，两条路径共用
    if requested is not None:
        match = next((p for p in processes if p.pid == requested), None)
        if match is None:
            raise RuntimeError(f"pid {requested} is not running")
        if not image_matches_target(match.name):
            raise RuntimeError(f"pid {requested} runs {match.name!r}, not {TARGET_NAME!r}")
        return requested
    matches = [p.pid for p in processes if image_matches_target(p.name)]
    if len(matches) != 1:
        raise RuntimeError(f"expected one {TARGET_NAME} process, found {len(matches)}")
    return matches[0]
```

`run()` 捕获该异常并返回 `unavailable`（`CodolGameServerControl.py:173-180`）；`frida.get_local_device()` 失败同样归类 `unavailable`（`:165-172`）。

### 2.2 L3 附加后复核（评估结论：可行，且已实现）

- **Frida 是否提供附加后的身份信息**：提供。`Process.enumerateModules()[0]` 是 Frida 载入脚本的进程映像；脚本原本就依赖它做固定偏移寻址，因此**零新增依赖、零新增语义**。
- **为什么它比"再查一次 PID"强**：它不是对 PID 的又一次外部观察，而是**被附加进程在附加之后自述映像**，因此消除了 L1/L2 与 `attach` 之间的 TOCTOU。
- **守卫位置**：在 `Process.findModuleByName(PLUGIN_NAME)` **之前**，因此身份不匹配时**不会** `getExportByName('CODOL_GameServerSetEnabled')`，更不会调用它。
- **失败关闭**：`clientModule.name` 缺失/为空 → 视为不匹配 → `unavailable`。
- 插件未加载（映像正确但 DLL 未注入）同样归类 `unavailable`（**不是** `refused`）。

### 2.3 名字比较的明确规则（任务 §二.3）

| 问题 | 结论 | 依据 |
| --- | --- | --- |
| 是否区分大小写 | **不区分** | Python 侧 `str.casefold()`；JS 侧 `String.prototype.toLowerCase()`。`TARGET_NAME` 是 ASCII 映像名，两种折叠等价 |
| 是否接受完整路径 | **不接受** | `tasklist /FO CSV` 与 Frida `Process.name` / `Module.name` 都只返回**基名**；`C:\games\x.exe` ≠ `x.exe`（有单测） |
| 是否接受前缀/近似名 | **不接受** | 精确相等，`x.exe.bak` ≠ `x.exe`（有单测） |
| 实际允许的客户端映像名 | `CODOL_CLIENT_EXECUTABLE` 环境变量优先，否则 `codoMP_client_shipRetail.exe` | 与 `CodolGame.py:28` 逐字一致；`Match_CODOL_Two_Clients.bat:22` 使用同一约定 |

> **兼容性说明（重要）**：修复前工具**硬编码** `codoMP_client_shipRetail.exe`。OLfinal bring-up 实际运行复制后的 `out.exe`（`CodolGame.py:22-27` 注释）。若只加校验而不统一名字来源，合法目标会被误拒。因此工具改为与启动器同源解析。工具作为子进程由调用方派生，会继承该环境变量。

## 3. 失败关闭覆盖矩阵（任务 §二.2 / §二.5）

| 情形 | 结果 | attach 是否被调用 | 插件导出是否被调用 |
| --- | --- | --- | --- |
| 正确目标进程 | 继续（`confirmed`/`refused`） | 是 | 是 |
| 错误进程名（L1） | `unavailable`，exit 3 | **否**（未派生子进程） | 否 |
| 错误进程名（L2） | `unavailable`，exit 3 | **否** | 否 |
| PID 不存在 | `unavailable`，exit 3 | **否** | 否 |
| 进程枚举失败（tasklist 抛错） | `unavailable` | **否** | 否 |
| 进程枚举失败（Frida 抛错） | `unavailable`，exit 3 | **否** | 否 |
| Frida 本地设备不可用 | `unavailable`，exit 3 | **否** | 否 |
| attach 本身失败 | `unavailable`，exit 3 | 是（失败） | 否 |
| 附加后映像不匹配 | `unavailable`，exit 3 | 是 | **否**（守卫在其之前） |
| 附加后无法读取映像名 | `unavailable`，exit 3 | 是 | **否** |
| 插件未加载 | `unavailable`，exit 3 | 是 | 否 |

## 4. 测试（G1）

### 4.1 工具级：`tools/runtime/CodolGameServerControlTests.py`（新增，24 项）

| 测试类 | 项数 | 覆盖 |
| --- | --- | --- |
| `ImageNameRuleTests` | 3 | 大小写不敏感；完整路径不匹配；前缀/空名/None 不匹配 |
| `FindPidTests` | 5 | 正确目标接受；错误映像拒绝；PID 不存在拒绝；枚举失败不吞；无 `--pid` 时要求唯一目标 |
| `PreAttachIdentityTests` | 5 | 错误映像/PID 不存在/枚举失败时 `device.attach` **未被调用**；本地设备失败；attach 失败为 `unavailable` 且**非** `refused` |
| `PostAttachIdentityTests` | 3 | 身份守卫在程序序上**先于** `Process.findModuleByName` 与 `CODOL_GameServerSetEnabled`；插件未加载为 `unavailable`；附加后身份失败为 `unavailable` 且携带 `process_name` |

> 全部使用 mock 设备/脚本，**不附加任何真实进程**。测试在导入工具前把 `CodolFridaRuntime.configure_frida_runtime` 替换为空实现，避免改写测试进程的 TEMP；其余（含真实 `frida` 包）均为出厂模块。

### 4.2 调用方级：`tools/runtime/CodolGameTests.py`（G1 相关 3 项）

- `test_request_graceful_stop_does_not_spawn_for_a_foreign_image` — 映像不符时 `subprocess.run` **未被调用**。
- `test_request_graceful_stop_does_not_spawn_for_a_gone_pid` — `process_image_name` 返回 None 时不派生子进程。
- `test_request_graceful_stop_does_not_spawn_when_the_query_fails` — tasklist 抛 `OSError` 时不派生子进程，detail 保留原因。

## 5. 与 T-2 的差异

| 文件 | T-2 后 | T-2.1 后 |
| --- | --- | --- |
| `tools/runtime/CodolGameServerControl.py` | `EF3A8F16…` 78850 B（**T-2 未改动**） | `4B7C1CE4…` 84909 B |
| `tools/runtime/CodolGame.py` | `136E0A68…` 43740 B | `8CBF194A…` 48265 B |
| `tools/runtime/CodolGameServerControlTests.py` | 不存在 | `BC227C76…` 14191 B（新增） |

## 6. 剩余风险（失败关闭前提下仍存在的限制）

| ID | 风险 | 影响 | 缓解/说明 |
| --- | --- | --- | --- |
| R1 | 身份校验是**名字级**的：不校验构建号、映像哈希或签名 | 同机同名但不同构建/实例的进程无法区分 | 名称来自 `CODOL_CLIENT_EXECUTABLE` 的显式约定；进一步校验需要读取目标文件哈希，超出本轮范围且未授权 |
| R2 | L1（tasklist）与 L2（Frida 枚举）使用**不同 API**，理论上可瞬时不一致 | 可能多拒一次（失败关闭），不会误附加 | 失败方向安全；L3 为最终裁决 |
| R3 | L3 依赖 Frida 能报告主模块名；若某进程无法报告 | 该目标被**拒绝**（失败关闭） | 符合任务 §二.5；尚未在真实客户端上取得运行时证据（本轮未授权） |
| R4 | 真实客户端上的 L3 行为**仅有结构性证据**（守卫序 + mock 消息），无运行时证据 | 无法排除 Frida 版本差异 | 明确留给下一阶段运行时验证申请 |

**未把 `tasklist` 查询成功当作身份保证**：L1 只用于避免无谓派生；身份保证由 L2 + L3 共同提供，且以 L3（被附加进程自述）为最终裁决。
