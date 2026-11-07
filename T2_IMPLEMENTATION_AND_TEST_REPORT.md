# T2_IMPLEMENTATION_AND_TEST_REPORT — 最小实现与测试结果

**日期**：2026-10-10
**工作基准**：**F = `F:\桌面\ol\ol-mod-olfinal`**（HEAD `2a75bdd`）
**结果**：**已实施最小改动 · 调用方测试 25 项（新增 8 项全部通过）· T-1 基线回归全绿**
**未做**：未改 ABI / 导出签名 / 错误码 10037 / DLL 析构 / `DllMain`；未启动游戏；未注入；未部署；未提交 Git。

---

## 0. 结论速览

| 项 | 结果 |
| --- | --- |
| 是否实施 | **是** —— 存在可定位且必要的调用方缺口，且现有接口足以安全支持（以子进程方式复用） |
| 改动文件 | `tools/runtime/CodolGame.py` · `tools/runtime/CodolGameTests.py`（**均为调用方工具，非插件源码**） |
| 改动规模 | `CodolGame.py` +3 hunks（+76 行净）· `CodolGameTests.py` +2 hunks（+148 行） |
| 新增导出 | **无** |
| 调用方测试 | 改动前 **17 项（1 项预先存在失败）** → 改动后 **25 项（同一项预先存在失败）**；**新增 8 项全部通过** |
| T-1 回归 | `REPRODUCE.ps1` 全绿：基线哈希 7/7 OK、`checks=124 failures=0`、4 个目标 `exit 0`、`diff-check exit=0`、`stage` mtime 未变 |
| 真实客户端验证 | **未执行**（本轮禁止注入）。Frida 附加路径**未验证** |

---

## 1. 为什么实施（决策依据）

| 判据 | 结论 |
| --- | --- |
| 缺口是否**可定位** | ✅ `CodolGame.py stop()` 全文无停止请求；唯一的优雅停止机制 `CodolGameServerControl.py --disable` 无任何调用方 |
| 缺口是否**必要** | ✅ `taskkill /F` 不运行 `DLL_PROCESS_DETACH`；正常退出时释放发生在加载器锁下的析构中。不请求停止就没有其它机会 |
| 现有接口能否安全支持 | ✅ 可以 —— 但**必须子进程调用**（见下） |
| 是否需要新增导出 | ❌ 不需要（`SetEnabled(false)` 已是入口） |
| 是否触碰被禁区域 | ❌ 未触碰（无 ABI / 导出 / 10037 / 析构 / `DllMain`） |

**为什么用子进程而不是 import**：`CodolGameServerControl.py` 在导入期执行 `configure_frida_runtime()`（`:13-15`），后者改写进程级 `TEMP/TMP/TMPDIR` 与 `tempfile.tempdir`（`CodolFridaRuntime.py:33-36`）并清理 `.runtime/frida` 下的旧目录。若在启动器内 import，这些副作用会作用于**启动器进程**。子进程调用完全隔离。

---

## 2. 最小 diff

### 2.1 `tools/runtime/CodolGame.py`

**Hunk 1**（`@@ -588,6 +588,70 @@`，紧随 `terminate_pids` 之后）—— 新增常量与桥接函数：

```python
GRACEFUL_STOP_TOOL = "CodolGameServerControl.py"
GRACEFUL_STOP_OUTCOMES = ("confirmed", "refused", "unavailable")


def request_graceful_stop(pid: int, timeout: float = 20.0) -> tuple[str, str]:
    """Ask the in-process plugin to release its UDP transport before termination.

    The plugin's only stop entry is CODOL_GameServerSetEnabled(false), and the
    only way to reach it from outside the client is an in-process call: the
    DedicatedControl channel carries no stop command, the plugin watches no file,
    and Server.setEnabled(false) has no other caller. CodolGameServerControl.py
    --disable is that call, and it reports the plugin's own return value through
    its exit code (0 = the plugin returned true, 2 = it returned false or the
    process could not be reached).

    It is invoked as a SUBPROCESS on purpose: importing it would execute
    configure_frida_runtime(), which rewrites TEMP/TMP/TMPDIR and
    tempfile.tempdir for the whole launcher process.

    Returns (outcome, detail), outcome being one of GRACEFUL_STOP_OUTCOMES:
      "confirmed"   the plugin returned true; the transport is released
      "refused"     the tool ran and the plugin returned false, or the attach
                    failed; the transport may still be bound
      "unavailable" the tool or its runtime is missing, so nothing was asked
    Never raises: a caller that is about to terminate the process must not be
    stopped by a diagnostic failure.
    """
    tool = Path(__file__).resolve().with_name(GRACEFUL_STOP_TOOL)
    if not tool.is_file():
        return "unavailable", f"{GRACEFUL_STOP_TOOL} is not next to CodolGame.py"
    command = [
        sys.executable,
        str(tool),
        "--disable",
        "--pid",
        str(pid),
        "--sample-seconds",
        "0",
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding=locale.getpreferredencoding(False),
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return "unavailable", "the Python interpreter for the stop tool was not found"
    except subprocess.TimeoutExpired:
        return "refused", f"the stop tool did not answer within {timeout:.0f}s"
    except OSError as error:
        return "unavailable", f"the stop tool could not be started: {error}"
    if result.returncode == 0:
        return "confirmed", "the plugin reported the transport stopped"
    detail = (result.stdout or "").strip() or (result.stderr or "").strip()
    if len(detail) > 400:
        detail = detail[:400] + "..."
    return "refused", f"exit {result.returncode}: {detail or 'no output'}"
```

**Hunk 2**（`@@ -927,6 +991,29 @@`）—— 在 `terminate_pids` **之前**请求停止：

```python
    stopped = [*pids]
    if room_owner_pid is not None:
        stopped.append(room_owner_pid)

    # Request the graceful stop BEFORE anything is killed. taskkill /F does not
    # run DLL_PROCESS_DETACH, and a normal exit would release the transport from a
    # destructor under the loader lock, so this is the only opportunity to stop it
    # in normal execution. A failure here never cancels the termination the caller
    # asked for, and it is never reported as a success.
    graceful_refused = False
    for pid in pids:
        outcome, detail = request_graceful_stop(pid)
        if outcome == "confirmed":
            print(f"Graceful stop confirmed for PID {pid}: {detail}")
        elif outcome == "refused":
            graceful_refused = True
            print(
                f"WARNING: the plugin refused the graceful stop for PID {pid}: {detail}",
                file=sys.stderr,
            )
        else:
            print(
                f"WARNING: no graceful stop was requested for PID {pid}: {detail}",
                file=sys.stderr,
            )

    failed = terminate_pids(stopped)
```

**Hunk 3**（`@@ -940,6 +1027,16 @@`）—— 拒绝时使用独立退出码：

```python
    print(f"Stopped ol-mod PID(s): {', '.join(map(str, stopped))}")
    if graceful_refused:
        # The processes are gone, so the stop succeeded; the transport release is
        # a separate claim that the plugin explicitly denied. Report it as its own
        # exit code instead of folding it into "stopped".
        print(
            "Stopped, but the plugin did not confirm the UDP transport release; "
            "see the CodolGameServer log for the socket error.",
            file=sys.stderr,
        )
        return 4
    return 0
```

### 2.2 `tools/runtime/CodolGameTests.py`

**Hunk 1**：新增 `import contextlib` / `import io`（用于捕获 stderr）。
**Hunk 2**：新增 8 个测试 + 1 个静态辅助 `_running_once`。

**未改动的既有测试**：全部 17 项保留原样（含 1 项预先存在的失败，见 §5）。

---

## 3. 测试前后结果

| 时点 | 命令 | 结果 |
| --- | --- | --- |
| 改动后（当前） | `python CodolGameTests.py -v` | **Ran 25 tests · FAILED (failures=1)** · exit 1 |
| HEAD 版本基线（同测试文件） | `git show HEAD:tools/runtime/CodolGame.py` → 临时目录 → 同命令 | **Ran 17 tests · FAILED (failures=1)** · exit 1 |

**唯一失败项在改动前后完全相同**：`test_only_dedicated_uses_native_qa_launch_bypass` ⇒ **本次改动没有引入任何回归**。

| 指标 | 改动前 | 改动后 |
| --- | --- | --- |
| 测试总数 | 17 | **25**（+8） |
| 通过 | 16 | **24** |
| 失败 | 1（预先存在） | **1（同一项）** |

**新增 8 项（全部 ok）**：

| # | 测试 | 覆盖分支 |
| --- | --- | --- |
| 1 | `test_stop_requests_the_graceful_stop_before_terminating` | **停止成功** + **调用顺序**（断言 `["graceful:222", "terminate"]`） |
| 2 | `test_stop_returns_4_when_the_plugin_refuses_the_graceful_stop` | **插件拒绝** → 退出码 4 + stderr 两条警告 + 仍调用 `terminate_pids([222])` |
| 3 | `test_stop_still_stops_when_no_graceful_stop_can_be_requested` | **调用不可用** → 退出码 0 + 警告 + 仍终止 |
| 4 | `test_stop_reports_a_termination_failure_instead_of_the_graceful_result` | **终止失败优先** → 退出码 3（不是 4） |
| 5 | `test_stop_does_not_request_a_graceful_stop_when_nothing_is_running` | **无进程时不做无谓附加** |
| 6 | `test_request_graceful_stop_maps_the_tool_exit_code` | 退出码 0→`confirmed`、2→`refused`、9→`refused`；并断言命令行含 `--disable --pid 4242` |
| 7 | `test_request_graceful_stop_treats_a_missing_tool_as_unavailable` | 工具缺失 → `unavailable` |
| 8 | `test_request_graceful_stop_never_raises` | `FileNotFoundError` / `TimeoutExpired` / `OSError` → 均返回合法 outcome，**不抛异常** |

> **测试性质声明**：以上全部为**调用方级别的模拟测试**（`mock` 替换 `request_graceful_stop` 或 `subprocess.run`）。它们验证**调用方逻辑**，**不是**真实客户端运行验证。真实 Frida 附加**未验证**。

---

## 4. 失败分支行为定义

| 分支 | 触发条件 | 打印 | 退出码 | 是否仍终止 |
| --- | --- | --- | --- | --- |
| 成功 | 工具 exit 0 | `Graceful stop confirmed for PID <pid>: …` | 0 | 是 |
| 插件拒绝 | 工具 exit ≠ 0（含 attach 失败、插件返回 false） | `WARNING: the plugin refused the graceful stop for PID <pid>: exit N: …`（stderr）+ 结尾 `Stopped, but the plugin did not confirm the UDP transport release; see the CodolGameServer log for the socket error.` | **4** | 是 |
| 不可用 | 工具文件缺失 / 解释器缺失 / 无法启动 | `WARNING: no graceful stop was requested for PID <pid>: …`（stderr） | 0 | 是 |
| 超时 | 工具 20 s 内无响应 | 同"插件拒绝"（outcome `refused`） | **4** | 是 |
| 终止失败 | `taskkill` 失败或进程仍在 | `Could not stop PID(s): …` | **3**（优先于 4） | — |

**没有任何分支把失败报成成功。** 退出码 4 只用于"插件**实际运行并明确拒绝**"，以避免在没有 Frida 的机器上让 `stop` 恒返回非零。

---

## 5. 预先存在的失败（**不在本次范围**）

`test_only_dedicated_uses_native_qa_launch_bypass`（`CodolGameTests.py:99-106`）断言：

```python
        self.assertEqual(CodolGame.launch_arguments("auto", "client"), [])
        self.assertEqual(CodolGame.launch_arguments("auto", "combined"), [])
```

而当前实现（`CodolGame.py:280-294`）**无条件**追加 `-qa`，其注释明确记录了原因：

> `-qa is the TCLS WinMain gate. It is NOT a role flag … every role starts the SAME executable through the SAME WinMain, so the gate fires for all of them. Started with no arguments the process dies before the engine runs, on 致命错误 "请使用腾讯游戏登录器 …" … Measured on build 1649370, 2026-08-30`

⇒ 这是**测试未跟上一次有意的行为修正**，与 T-2 无关。

**证明其为预先存在**：把 `HEAD` 版本的 `CodolGame.py` 取出到临时目录，与当前测试文件一起运行，得到**完全相同的 1 项失败**（日志 `_t2_evidence/launcher_tests_HEAD_baseline.log`）。

**处置**：**未修复**（超出本次授权范围）。仅登记为待办。

---

## 6. T-1 基线回归验证

执行 [\_t1_fix_evidence\\REPRODUCE.ps1](_t1_fix_evidence/REPRODUCE.ps1)（哈希断言 + 强制重建 + 全目标运行）：

| 步骤 | 结果 |
| --- | --- |
| HEAD 断言 | `2a75bdd…` = 期望 ✅ |
| 基线哈希断言（7 项） | **全部 OK** ✅（含 5 个 T-1 文件 + `EngineBindings.hpp` + `ClientProcessPatches.cpp`） |
| `xmake f` | `CONFIGURE exit=0` |
| `xmake build -r ol_transport_lifecycle_tests` | `BUILD exit=0` |
| `ol_transport_lifecycle_tests.exe` | **`checks=124 failures=0` · `run exit=0`** |
| `ol_game_server_tests` | `BUILD exit=0` · `run exit=0` |
| `ol_lua_runtime_tests` | `BUILD exit=0` · `run exit=0` |
| `ol_game_server`（生产插件） | `BUILD ol_game_server exit=0` |
| `git diff --check` | `exit=0` |
| `build\stage` mtime | `2026-10-09 17:01:07`（**未变 ⇒ 未触发部署**） |

⇒ **T-1 的已验证成果未被本次调用方改动破坏。**

---

## 7. 未验证项（必须保留）

| # | 未验证项 | 原因 |
| --- | --- | --- |
| U-1 | 真实客户端上 Frida 附加是否成功 | 需启动客户端 + 注入；本轮禁止 |
| U-2 | 附加是否触发 TenProtect 防护 | 同上 |
| U-3 | `CODOL_GameServerSetEnabled(false)` 在真实客户端上返回 `true` | 同上 |
| U-4 | `--disable` 的端到端退出码在真实客户端上为 0 | 同上 |
| U-5 | 安装的 frida **16.5.9** 与声明 `>=17,<18` 的差异是否影响附加 | 需真实附加；仅核对到导入级属性齐全 |
| U-6 | `--disable` 失败时 JSON **不含** `lastSocketError`（诊断缺口） | 已登记，未修（超出范围） |
| U-7 | 真实客户端退出是否走 `ExitProcess`（P2 路径） | 未观测 |

**这些项在获得单独授权前不得被描述为已验证。**

---

## 8. 文件哈希与日志

| 文件 | 改动前字节 / SHA-256 | 改动后字节 / SHA-256 |
| --- | --- | --- |
| `tools/runtime/CodolGame.py` | 39,495 · `3324CD8D256AB704899A5AAE2736F2F2E48AF968F567205CBFB5DAA3942D3E02` | 43,740 · `136E0A684B927F6082C5196E9983EFDF75AF341FA71C846246B056310F349001` |
| `tools/runtime/CodolGameTests.py` | 21,748 · `E5668698007A230E062889924BC8F64569A8D02709E5738891C6BCB37F4F6713` | 27,918 · `F916ED10A0A06872C095043C7896971D58621C8BE48862B3F7838228FE00A32A` |

| 日志 / 证据 | 路径 |
| --- | --- |
| 改动后完整测试输出 | [\_t2_evidence\\launcher_tests_after_t2.log](_t2_evidence/launcher_tests_after_t2.log) |
| HEAD 版本基线（证明失败为预先存在） | [\_t2_evidence\\launcher_tests_HEAD_baseline.log](_t2_evidence/launcher_tests_HEAD_baseline.log) |
| 改动前测试输出 | [\_t2_evidence\\launcher_tests_before_new_tests.log](_t2_evidence/launcher_tests_before_new_tests.log) |
| T-1 回归 | [\_t2_evidence\\reproduce_20261010_131941.log](_t2_evidence/reproduce_20261010_131941.log) |
| T-2 源码差异 | [\_t2_evidence\\t2_caller.diff](_t2_evidence/t2_caller.diff) |
| 完整哈希清单 | [\_t2_evidence\\T2_SHA256_MANIFEST.txt](T2_SHA256_MANIFEST.txt) |

---

## 9. 边界核对

| 禁止项 | 状态 |
| --- | --- |
| 启动游戏 / 服务进程 | **未执行** |
| 注入进程 | **未执行**（新代码路径在测试中被 mock 替换；本轮从未运行 `stop` 的真实附加） |
| 读取游戏内存 | **未执行** |
| 运行 `ol_deploy` | **未执行** |
| 修改 ABI / 导出签名 / 10037 / DLL 析构 / `DllMain` | **未修改** |
| 操作 D / 同步 F↔D | **未执行** |
| reset / rebase / clean / commit / push | **未执行** |
| 删除或覆盖历史失败日志 | **未执行**（旧日志全部保留） |

**工作树状态**：F 由 11 条 → **13 条**（新增 2 个已跟踪文件的修改）；D 仍 **6** 条。

---

## 10. 关联交付

- [T2_CALLER_SHUTDOWN_FLOW.md](T2_CALLER_SHUTDOWN_FLOW.md) — 真实调用链与证据等级
- [T2_SHA256_MANIFEST.txt](T2_SHA256_MANIFEST.txt) — 哈希清单
- [T1_VERIFIED_BASELINE.md](T1_VERIFIED_BASELINE.md) · [NETWORK_UNLOAD_LIFECYCLE_REVIEW.md](NETWORK_UNLOAD_LIFECYCLE_REVIEW.md) · [T1_FF3_ERROR_DOMAIN_DECISION.md](T1_FF3_ERROR_DOMAIN_DECISION.md)
