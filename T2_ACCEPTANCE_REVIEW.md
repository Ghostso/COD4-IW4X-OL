# T2_ACCEPTANCE_REVIEW — T-2 调用方停止链路独立验收

**日期**：2026-10-10
**工作基准**：**F = `F:\桌面\ol\ol-mod-olfinal`**（HEAD `2a75bdd`）
**本轮性质**：**只审查、测试、形成决策。未修改任何文件；未启动客户端；未附加 Frida 到游戏进程；未读内存；未部署。**
**结论**：**③ 暂不进入真实运行验证** —— 成功语义已明确，但 **PID 目标选择可靠性**与**失败分类完整性**两项未达门槛（§7）

---

## 0. 三选一结论

> ### **③ 暂不进入**
> 停止工具的成功语义**已证明明确**（§3），超时处理**已证明完整**（§4.2），但门槛要求的"**PID 目标选择可靠**"**无法证明**（§4.1 G1），且"**异常处理完整**"存在一处已实证的分类缺陷（§4.5 G2）。
> 两项缺口均为**调用方侧、小范围、可精确修复**；建议先修 §7.2 的最小方案，再重新评估。

| 门槛条件（用户给定） | 结论 | 依据 |
| --- | --- | --- |
| 停止工具的成功结果具有明确语义 | ✅ **已证明** | §3：`exit 0 ⇔ result.ok ⇔ 插件返回 true ⇔ `Server.enabled==false ∧ transport.bound==false` |
| PID 目标选择可靠 | ❌ **无法证明** | §4.1 G1：工具在收到 `--pid` 时**不做任何名字校验**；`tasklist` 与 `attach` 之间存在 TOCTOU 窗口 |
| 超时与异常处理完整 | ⚠️ **部分** | §4.2 超时**完整**（已实证子进程被杀）；§4.5 G2 失败分类**不完整**（attach 失败与插件拒绝同为 exit 2 → 均映射为 `refused` → 退出码 4） |

---

## A. 基线与差异审查

### A1 — 已读材料

[T1_VERIFIED_BASELINE.md](T1_VERIFIED_BASELINE.md) · [NETWORK_UNLOAD_LIFECYCLE_REVIEW.md](NETWORK_UNLOAD_LIFECYCLE_REVIEW.md) · [T1_FF3_ERROR_DOMAIN_DECISION.md](T1_FF3_ERROR_DOMAIN_DECISION.md) · [T2_CALLER_SHUTDOWN_FLOW.md](T2_CALLER_SHUTDOWN_FLOW.md) · [T2_IMPLEMENTATION_AND_TEST_REPORT.md](T2_IMPLEMENTATION_AND_TEST_REPORT.md) · [T2_SHA256_MANIFEST.txt](T2_SHA256_MANIFEST.txt) · [\_t1_fix_evidence\\REPRODUCE.ps1](_t1_fix_evidence/REPRODUCE.ps1)

### A2 — HEAD、工作区状态、T-2 实际 diff

| 项 | 值 |
| --- | --- |
| F HEAD / 分支 | `2a75bdd8872bb9f54006382a924c3006ec9affc2` / `OLfinal-live` |
| F `git status --porcelain` | **13** 条（8 M + 3 ?? 为历史遗留；**2 M 为 T-2 新增**） |
| D HEAD / status | 同 F / **6** 条（**未被修改**） |
| T-2 改动文件 | 仅 `tools/runtime/CodolGame.py` 与 `tools/runtime/CodolGameTests.py` |
| `tools/runtime/CodolGame.py` | 43,740 B · `136E0A684B927F6082C5196E9983EFDF75AF341FA71C846246B056310F349001` |
| `tools/runtime/CodolGameTests.py` | 27,918 B · `F916ED10A0A06872C095043C7896971D58621C8BE48862B3F7838228FE00A32A` |
| 与 [T2_SHA256_MANIFEST.txt](T2_SHA256_MANIFEST.txt) 一致 | ✅ 两文件哈希逐字相同 |

**T-2 的实际 diff 范围**：`git diff --stat -- src/` 列出的 7 个 `src/` 文件**全部是 T-1 之前既有的未提交改动**，**没有一个**由 T-2 触及；T-2 的改动**完全局限在 `tools/runtime/`**。

### A3 — 未修改被禁区域

| 检查 | 结果 |
| --- | --- |
| DLL ABI / 导出布局 | ✅ 未改（`src/` 零改动） |
| 错误码 `10037` | ✅ 未改（`win_net.hpp` = `8F0FF318…`，与 T-1 冻结值相同） |
| `DllMain` / 全局网络析构 | ✅ 未改（`Appmain.cpp` = `407B6F98…`，`win_net.cpp` = `3A34D953…`，均为 T-1 冻结值） |
| 部署产物 | ✅ 未触碰（`build\stage` mtime 仍为 **2026-10-09 17:01:07**） |
| `ol_deploy` | ✅ 未触发 |

### A4 — D 历史副本

✅ 未修改：HEAD 同 F、`status` 仍 6 条、本轮零写入。

### A5 — 未执行破坏性/部署操作

✅ 未执行 `reset` / `rebase` / `clean` / `commit` / `push` / `ol_deploy`。

---

## B. 语义审查

### B1 — 停止调用成功语义（用户重点问题 ①）

**完整链路**（逐行核对）：

```text
CODOL_GameServerSetEnabled(false)                 Appmain.cpp:8174-8201
  ├─ if (!ensureInstalled()) return false;                         :8176-8177
  ├─ Server.setEnabled(false);                    :8180  ← 状态切换
  │     └─ ServerCore::setEnabled                  sv_main_mp.cpp:1166-…
  │           幂等：status_.enabled 已是 false 则**立即返回**
  │           否则记录日志并 reset 所有已连接 client
  ├─ const auto transportStopped = Network.stop();  :8183
  │     └─ SvUdpTransport::stop                     sv_network_mp.cpp:72-89
  │           └─ NetUdpSocket::close                 win_net.cpp:149-170
  │                 ├─ 若 socket_ == INVALID_SOCKET → 跳过 closesocket，返回 true
  │                 ├─ 否则 closesocket() == SOCKET_ERROR → 返回 false（保留句柄）
  │                 └─ 成功 → socket_=INVALID_SOCKET, port_=0, WSACleanup()
  ├─ if (!transportStopped) { log; return false; }                 :8188-8198
  └─ return true;                                                  :8200
```

**五个状态必须分开，且它们的蕴含关系如下**：

| 状态 | 含义 | 与 `return true` 的关系 |
| --- | --- | --- |
| S1 API 调用成功 | 函数返回 | `true` 即 S1 |
| S2 插件状态切换成功 | `Server.status().enabled == false` | **被蕴含**（`setEnabled(false)` 在 `:8180` 无条件执行） |
| S3 `Network.stop()` 实际完成 | 返回 `true` | **被蕴含**（`:8188` 否则 return false） |
| S4 UDP socket 关闭成功 | `closesocket()` 返回 0 | **不严格蕴含**：若句柄本已无效（幂等路径），`close()` 也返回 `true` 而**没有**关闭任何 socket。真正的保证是"**调用后 `socket_.open() == false`**" |
| S5 进程退出 | 进程终止 | **完全无关**，必须另行观察 |

**⇒ 返回值 `true` 的准确语义**：

> **调用返回后，`Server.status().enabled == false` 且 `SvUdpTransport::status().bound == false`（等价于 `socket_.open() == false`）。**

**它明确不保证的**：

| 不保证 | 依据 |
| --- | --- |
| 本次调用**关闭了**一个 socket | `close()` 在句柄已无效时也返回 `true`（`win_net.cpp:151` 的分支） |
| `WSACleanup()` 成功 | 其返回值被忽略（`win_net.cpp:164-168`） |
| OS 层端口立即可被**其它进程**重新绑定 | 属 OS 行为；T-1 的探针只在**测试进程**内证明过 |
| 插件**其它** socket 已释放 | `DedicatedControl` 监听（端口 28961，`appmain.cpp:2077-2084`）与 `ClientSessionBridge`（端口 28962，`appmain.cpp:1916-2066`）**完全未被 `SetEnabled(false)` 触及** |
| 进程将退出 | 无关 |

**对用户问题 ① 的直接回答**：`SetEnabled(false)` 返回 `true` **强于**"只是状态切换成功"——它**同时**保证 transport 不再处于 bound 状态。但它**仍然不等于**"本次真的关闭了 UDP socket"，也**不等于**"进程退出"，更**不覆盖**插件其它两个监听 socket。真实客户端上的证据**仍未取得**（本轮未附加）。

### B2 — 子进程调用与结果处理

| 审查项 | 结论 | 等级 |
| --- | --- | --- |
| PID 是否可靠绑定到目标游戏进程 | ⚠️ **部分**。`running_pids()`（`CodolGame.py:108-125`）用 `tasklist /FI "IMAGENAME eq <TARGET_NAME>"` 精确名字过滤，**意图正确**；但见 **G1** | 静态 |
| Frida 子进程是否有明确超时与终止处理 | ✅ **有，且已实证**。`subprocess.run(..., timeout=20.0)`；实证：`timeout=3.0` 时 3.03 s 抛 `TimeoutExpired` 且**子进程 PID 24304 事后不再存活** ⇒ 子进程**确实被终止** | **实证** |
| 工具缺失 | ✅ `GRACEFUL_STOP_TOOL` 路径不存在 ⇒ `("unavailable", …)`（有单测） | mock 测试 |
| 附加失败 | ⚠️ ⇒ 工具 exit 2 ⇒ `("refused", …)`（**与插件拒绝不可区分**，见 **G2**）。**已用真实子进程 + 不存在的 PID 实证**：`refused`，detail 为 `{"ok":false,…,"error":"failed to attach to target: unable to find process with pid 999999"}` | **实证** |
| 调用超时 | ✅ `TimeoutExpired` ⇒ `("refused", "the stop tool did not answer within 20s")`（有单测） | mock 测试 |
| 插件拒绝 | ✅ 工具 exit 2 ⇒ `("refused", "exit 2: <JSON>")` | mock 测试 |
| JSON 无效 | ✅ **不解析 JSON**，只看退出码。工具的最后一句是 `return 0 if result.get("ok") else 2`（`:1782`），因此 **exit 0 ⇒ 插件返回过 true**。若中途异常导致 `result={}` 则为 exit 2 | 静态 |
| stdout / stderr / 退出码收集 | ✅ `capture_output=True, text=True`；失败时 `detail = stdout or stderr`（工具在**失败时也把 JSON 打到 stdout**，`:1781`） | 静态 + 实证 |
| 是否可能把"工具启动成功"误认为"插件停止成功" | ❌ **不可能**。`returncode == 0` 需要 `result.ok` 为真，而 `result` 只在收到 `ok:true` 消息时被填充（`:1715-1717`） | 静态 |
| 停止工具是否可能影响**启动器自身** | ❌ **不会，且已实证**。真实子进程运行后，启动器的 `TEMP/TMP/tempfile.tempdir` **逐字未变**（`real_subprocess_probe.json`） | **实证** |
| 停止工具是否可能附加到**错误进程** | ⚠️ **可能**（见 **G1**） | 静态 |

**真实子进程探针（非 mock，非游戏）**：`request_graceful_stop(999999)` → `refused`，**耗时 0.59 s**（10 s 只是上限，不是延迟），启动器环境未受污染。
**副作用**：子进程执行 `configure_frida_runtime()`，在 F 中创建了 `.runtime/`（**gitignore 覆盖**，`git status` 不受影响）。这是运行该桥接的真实副作用，必须记录。

### B3 — 失败语义与退出码

| 检查 | 结论 | 等级 |
| --- | --- | --- |
| 退出码 0 的全部分支 | ① 全部 PID `confirmed`；② 全部 `unavailable`（警告后继续）。**均由单测覆盖** | mock 测试 |
| 退出码 3 的全部分支 | `terminate_pids` 返回失败 或 5 s 后仍有进程。**代码块与 T-2 前逐字相同**（未改动） | 静态 + 实证 |
| 退出码 4 的全部分支 | **任一** PID `refused` | 实证（§4.6 聚合） |
| 插件明确拒绝时是否保留诊断信息 | ⚠️ **部分**。stderr 打印 `WARNING: the plugin refused the graceful stop for PID <pid>: exit 2: <JSON>`（截断 400 字符），JSON 含 `error` 文本；**但 `lastSocketError` 与 `transport_bound` 不在其中**（`throw` 跳过了 `emitStatus()`）。socket 错误码只在插件日志 | 静态 + 实证 |
| 停止不可用时继续强制终止是否有明确警告 | ✅ 有：`WARNING: no graceful stop was requested for PID <pid>: <reason>`（stderr） | 实证 |
| **停止失败后是否仍可能退出码 0** | ✅ **可能**——当桥接**不可用**时（工具缺失 / 解释器缺失 / 无法启动）。这是**明确的兼容性策略**：避免无 Frida 的机器上 `stop` 完全不可用。**必须明确记录**（用户重点问题 ②） | 实证 |
| 多 PID 部分成功/部分拒绝的聚合规则 | ✅ **任一拒绝 ⇒ 4**（其余情形见 §4.6）。**但无单测覆盖该聚合**（缺口 G3） | 实证（临时harness） |
| 既有退出码 3 是否完全保持原语义 | ✅ 是。`if failed: … return 3` 块未改动，且 §4.6 实证"拒绝 + 终止失败 ⇒ 3"（3 优先于 4） | 实证 |
| 性能副作用 | ⚠️ 优雅停止在终止**之前**串行执行，最坏 `20 s × N` 个 client PID。**代码注释未提及该延迟**（缺口 G4） | 静态 |

### B4 — 既有失败测试

**方法学更正（诚实披露）**：本轮的**第一次**对照实验是**错的**——我把 **HEAD 版 `CodolGame.py`** 与 **当前版 `CodolGameTests.py`**（已含 8 个 T-2 测试）放在一起跑，得到 `failures=2, errors=12`（新测试因缺 `request_graceful_stop` 而 AttributeError）。该结果**不能**用于判断回归，已作废并保留原日志 [\_t2_acceptance_evidence\\acceptance_caller_tests_head.log](_t2_acceptance_evidence/acceptance_caller_tests_head.log)。

**正确的对照（HEAD + HEAD，同环境、同测试文件）**：

| 配置 | 测试数 | 失败 | 失败项 |
| --- | --- | --- | --- |
| **HEAD `CodolGame.py` + HEAD `CodolGameTests.py`** | **17** | **1** | `test_only_dedicated_uses_native_qa_launch_bypass` |
| 当前 `CodolGame.py` + 当前 `CodolGameTests.py` | **25** | **1** | **同一项** |

日志：[\_t2_acceptance_evidence\\acceptance_caller_tests_head_both.log](_t2_acceptance_evidence/acceptance_caller_tests_head_both.log) · [\_t2_acceptance_evidence\\acceptance_caller_tests_current.log](_t2_acceptance_evidence/acceptance_caller_tests_current.log)

**⇒ T-2 引入零回归；该失败在 HEAD 上同样存在，与 T-2 无关。**

**`-qa` 的冲突实质**：

| 侧 | 内容 |
| --- | --- |
| 测试断言（`CodolGameTests.py:100-101`） | `launch_arguments("auto","client") == []`；`("auto","combined") == []` |
| 实现（`CodolGame.py:280-294`） | **无条件** `arguments.append("-qa")` |
| 实现侧依据（同处注释） | `-qa` 是 TCLS WinMain 门禁，**不是角色标志**；所有角色走同一 WinMain。无参数时进程在引擎启动前即以致命错误退出。**实测于 build 1649370，2026-08-30，client 角色** |

⇒ 测试**未跟进**一次有意的行为修正。

**是否阻塞 T-2 验收？** **不阻塞**。理由：① 位于 `launch_arguments`（**启动**路径），与停止路径无关；② 在 HEAD 上以完全相同方式失败；③ T-2 未触及该函数。**本轮未修改该测试或启动参数**（按任务要求）。

---

## C. 测试与回归

| 项 | 命令 | 结果 |
| --- | --- | --- |
| C1 调用方测试 | `python CodolGameTests.py -v`（`tools/runtime`） | `Ran 25 tests · FAILED (failures=1)` · exit 1（失败项 = B4 的既有项） |
| C2 T-1 回归 | `REPRODUCE.ps1` | **exit 0**：基线哈希 **7/7 OK** · `checks=124 failures=0` · `ol_game_server_tests` / `ol_lua_runtime_tests` / `ol_game_server` 全部 `exit 0` · `stage` mtime 未变 |
| C3 | `git diff --check` | **exit 0** |
| C4 | 未启动客户端 / 未附加 Frida 到游戏 / 未读内存 / 未部署 | ✅ |

---

## D. 本轮新增的实证证据（非 mock）

| # | 检查 | 方法 | 结果 |
| --- | --- | --- | --- |
| E-1 | `subprocess.run(timeout=)` 是否**真正终止**子进程 | 启动一个会写自身 PID 并 `sleep(60)` 的子进程，`timeout=3.0` | `TimeoutExpired` @ 3.03 s；子进程 PID 24304 **事后不存在** |
| E-2 | 真实桥接的失败路径（**非 mock**） | `request_graceful_stop(999999)`（不存在的 PID；**不附加任何真实进程**） | `refused`；detail = 工具 JSON `{"ok":false,…"unable to find process with pid 999999"}`；**0.59 s** |
| E-3 | 桥接是否污染**启动器**环境 | 同 E-2，比较前后 `TEMP/TMP/tempfile.tempdir` | **逐字未变** ⇒ 子进程隔离有效 |
| E-4 | 多 PID 聚合规则 | 临时 harness 直接调用 `CodolGame.stop`（monkeypatch 三个依赖） | 见 §4.6 六种组合，**全部符合预期** |
| E-5 | `.runtime/` 副作用 | 同 E-2 | 子进程创建了 `.runtime/`（gitignore；`git status` 不受影响） |

> **E-2 是"真实子进程 + 真实 frida + 真实退出码"的端到端证据，但它没有附加到任何游戏进程，因此不构成真实客户端验证。**

---

## 4.6 聚合规则实证明细

| 场景 | 期望 | 实测 | 一致 | stderr 有 WARNING |
| --- | --- | --- | --- | --- |
| 两个 PID 都 confirmed | 0 | **0** | ✅ | 否 |
| 一个 refused、一个 confirmed | 4 | **4** | ✅ | 是 |
| 两个都 refused | 4 | **4** | ✅ | 是 |
| 两个都 unavailable | 0 | **0** | ✅ | 是 |
| refused + 终止失败 | 3 | **3** | ✅ | 是 |
| confirmed + 终止失败 | 3 | **3** | ✅ | 否 |

**规则**：**任一 refused ⇒ 4**（sticky OR）；**终止失败 ⇒ 3 优先于 4**；unavailable 不影响退出码。
数据：[\_t2_acceptance_evidence\\ad_hoc_checks.json](_t2_acceptance_evidence/ad_hoc_checks.json)

---

## 7. 缺口与结论

### 7.1 缺口清单

| ID | 缺口 | 严重度 | 是否 T-2 引入 | 影响 |
| --- | --- | --- | --- | --- |
| **G1** | **PID 无二次校验**：工具在收到 `--pid` 时**直接返回该值**（`CodolGameServerControl.py:50-51`），**不做名字校验**；`tasklist` 与 `attach` 之间存在 TOCTOU 窗口。若 PID 已被回收，Frida 会附加到**无关进程** | **中** | 否（工具既有行为），但 **T-2 使其首次被自动调用** | 附加到错误进程 + 该次调用必然失败（找不到导出）⇒ 被误报为 `refused` ⇒ 退出码 4 |
| **G2** | **失败分类不完整**：工具 exit 2 同时表示"attach 失败"与"插件返回 false"；调用方把**任何非零**都映射为 `refused` ⇒ 退出码 4。**已实证**：不存在的 PID 也得到 `refused` | **中** | **是**（调用方分类） | 环境故障被误报为"插件拒绝"，把排查方向引向插件 |
| **G3** | 多 PID 聚合规则**无单测** | 低 | 是 | 行为已实证正确，但无回归保护 |
| **G4** | 停止延迟（最坏 `20 s × N`）未在代码注释中说明 | 低 | 是 | 操作者可能误以为 `stop` 卡住 |
| **G5** | 拒绝路径**不携带** `transport_bound` / `lastSocketError`（`throw` 跳过 `emitStatus()`）；成功路径**携带但被丢弃** | 低-中 | 否（工具既有），调用方未利用 | 无法在工具输出中直接确认"传输是否仍 bound" |

### 7.2 最小修复建议（**本轮未实施**，需授权）

| 针对 | 改动 | 规模 |
| --- | --- | --- |
| **G1** | 在 `request_graceful_stop` 内、发起子进程**之前**，用 `process_image_name(pid)`（已存在，`CodolGame.py:128-141`）复核该 PID 的镜像名仍等于 `TARGET_NAME`；不匹配则返回 `("unavailable", "pid no longer the target image")`，**不发起附加** | ~6 行 |
| **G2** | 区分退出码：`2` ⇒ `refused`；其它非零（如 `1` = 工具自身异常/ImportError）⇒ **新增第四态** `("tool-error", …)`，且**不**升级为退出码 4（按"不可用"处理，仅警告） | ~8 行 + 测试 |
| **G3** | 把 §4.6 的六种组合写成单测 | ~60 行测试 |
| **G4** | 在 `stop()` 的注释与 `--help` 中写明延迟上界 | 注释 |
| **G5** | 成功时解析 stdout JSON 的 `after.transport_bound` 作为**二次确认**（不改变退出码语义，仅强化日志） | ~10 行 |

**建议顺序**：G1 → G2 → G3 →（G5 可选）→ G4 文档。

### 7.3 结论

> **③ 暂不进入真实运行验证。**
> 成功语义（门槛 1）与超时处理**已证明**；**PID 目标选择可靠性（门槛 2）无法证明**，失败分类完整性（门槛 3）存在**已实证**的缺陷。
> 两者都是**调用方侧、约 14 行**的可精确修复项。**不应**用真实客户端试验去掩盖它们——按用户给定原则，应**先修正调用方实现**。

---

## 8. 关联交付

- [T2_RUNTIME_VALIDATION_PREREQUISITES.md](T2_RUNTIME_VALIDATION_PREREQUISITES.md) — 真实运行验证的前置条件、实验方案与回滚
- [T2_ACCEPTANCE_SHA256_MANIFEST.txt](T2_ACCEPTANCE_SHA256_MANIFEST.txt) — 本轮哈希清单
- [T2_CALLER_SHUTDOWN_FLOW.md](T2_CALLER_SHUTDOWN_FLOW.md) · [T2_IMPLEMENTATION_AND_TEST_REPORT.md](T2_IMPLEMENTATION_AND_TEST_REPORT.md) · [T1_VERIFIED_BASELINE.md](T1_VERIFIED_BASELINE.md)
