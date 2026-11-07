# T2_1_CALLER_REGRESSION_REPORT — 调用方回归与多 PID 聚合验收

**日期**：2026-10-10
**工作树**：**F = `F:\桌面\ol\ol-mod-olfinal`**（HEAD `2a75bdd8872bb9f54006382a924c3006ec9affc2`，分支 `OLfinal-live`）
**本轮性质**：仅修复 G1/G2、补齐 G3 单测、重新验收。**未部署、未启动客户端、未附加 Frida 到游戏进程、未读内存。**
**最终结论**：**有条件通过**（见 §8）。

---

## 1. 基线与 T-2 一致性核对

| 项 | 值 | 与 T-2 报告一致 |
| --- | --- | --- |
| F HEAD / 分支 | `2a75bdd8872bb9f54006382a924c3006ec9affc2` / `OLfinal-live` | ✅ |
| F `git status --porcelain -uall` | **15** 条（11 M + 4 ??）；T-2 为 13 条（11 M + 2 ??，其中 2 M 为 T-2 新增） | 本轮 +2（`CodolGameServerControl.py` M、`CodolGameServerControlTests.py` ??） |
| `CodolGame.py`（T-2 后） | `136E0A684B927F6082C5196E9983EFDF75AF341FA71C846246B056310F349001` 43740 B | ✅ 与 `T2_SHA256_MANIFEST.txt` 逐字相同 |
| `CodolGameTests.py`（T-2 后） | `F916ED10A0A06872C095043C7896971D58621C8BE48862B3F7838228FE00A32A` 27918 B | ✅ 与 `T2_SHA256_MANIFEST.txt` 逐字相同 |
| `CodolGameServerControl.py`（T-2 后） | `EF3A8F163F10B1D629AB173EBA417A0E8627C90F62FD0F6DD15EC0434D5C8F18` 78850 B | ✅ 与 T-2 manifest 的 "CALLER-SIDE TOOLING" 值相同（T-2 **未**改动它） |
| HEAD 版 `CodolGame.py` / `CodolGameTests.py` / 工具 | `3324CD8D…` / `E5668698…` / `EF3A8F16…` | ✅ 与 T-2 manifest "before, from HEAD" 逐字相同 |

> 结论：本轮起点就是 T-2 的**确切末态**，没有版本漂移。

## 2. G3：多 PID 聚合单测（新增 7 项）

全部位于 `tools/runtime/CodolGameTests.py`，通过 `_aggregate_stop` 辅助器驱动真实的 `CodolGame.stop()`（mock 掉 `running_pids` / `request_graceful_stop` / `terminate_pids`）：

| 场景 | 测试 | 期望退出码 | 实测 |
| --- | --- | --- | --- |
| 全部停止成功（2 PID 均 confirmed） | `test_multi_pid_stop_aggregates_all_confirmed` | 0 | ✅ 0，且两条确认打印、stderr 为空 |
| 一个插件明确拒绝 | `test_multi_pid_stop_reports_one_refusal_as_exit_4` | 4 | ✅ 4 |
| 一个停止请求不可用 | `test_multi_pid_stop_keeps_going_when_one_request_is_unavailable` | 0 | ✅ 0（警告后继续） |
| 一个工具异常 | `test_multi_pid_stop_does_not_call_a_tool_error_a_refusal` | 0 | ✅ 0，且 stderr **不含** "refused the graceful stop" |
| 进程终止失败 | `test_multi_pid_stop_reports_a_termination_failure` | 3 | ✅ 3 |
| 停止拒绝 **且** 进程终止失败 | `test_a_termination_failure_outranks_a_refusal` | **3**（3 优先于 4） | ✅ 3 |
| 重复 PID（`[111,111,222]`） | `test_duplicate_pids_are_requested_once` | 0，且优雅停止仅请求 2 次 | ✅ `call_args_list == [111, 222]` |
| 空 PID 列表 | `test_stop_does_not_request_a_graceful_stop_when_nothing_is_running`（T-2 既有） | 0，且不请求、不终止 | ✅ |

**聚合规则（已冻结并由单测保护）**：
- **任一 `refused` ⇒ 4**（sticky OR）。
- **进程终止失败 ⇒ 3 优先于 4**（任务 §四的既定优先级，**未被 4 覆盖**）。
- `unavailable` / `tool-error` 不影响退出码，但各自打印独立 WARNING，绝不打印成功。
- 部分成功/部分失败时，成功项打印 `Graceful stop confirmed for PID …`，失败项打印对应 WARNING，最终行 `Stopped ol-mod PID(s): …` 或 `Could not stop PID(s): …`。

**重复 PID 的防御**：`stop()` 现在以 `sorted(set(running_pids()))` 去重（`CodolGame.py:1066-1068`），避免重复项把最坏延迟 `20 s × N` 翻倍。

## 3. 测试执行结果

| 套件 | 命令 | 测试数 | 失败 | 退出码 | 日志 |
| --- | --- | --- | --- | --- | --- |
| 调用方（T-2.1 当前） | `python CodolGameTests.py -v` | **40** | **1** | 1 | `_t2_1_evidence/caller_tests_current.log` |
| 工具（新增） | `python CodolGameServerControlTests.py -v` | **24** | **0** | 0 | `_t2_1_evidence/tool_tests_current.log` |
| 相邻套件回归 | `CodolAimControlTests.py` / `CodolTwoClientMatchTests.py` / `CodolClientAccountTests.py` | 1 / 3 / 4 | 0 / 0 / 0 | 0 | 内联 |

### 3.1 唯一失败项 = 既有失败，非本轮引入

```
FAIL: test_only_dedicated_uses_native_qa_launch_bypass (CodolGameTests.py:103)
AssertionError: Lists differ: ['-qa'] != []
```

**HEAD+HEAD 正确对照**（同环境、同解释器、**模块与测试文件同版本**）：

| 配置 | 测试数 | 失败 | 失败项 | 日志 |
| --- | --- | --- | --- | --- |
| **HEAD `CodolGame.py` + HEAD `CodolGameTests.py`**（`git show` 逐字节取出） | **17** | **1** | `test_only_dedicated_uses_native_qa_launch_bypass` | `_t2_1_evidence/caller_tests_head_both.log` |
| 当前 `CodolGame.py` + 当前 `CodolGameTests.py` | **40** | **1** | **同一项** | `_t2_1_evidence/caller_tests_current.log` |

⇒ 该失败在 HEAD 上以**完全相同**的方式存在，与本轮及 T-2 均无关（`launch_arguments` 的 `-qa` 门禁是有意行为，测试未跟进；位于**启动**路径，与停止路径无关）。
本轮**未**修改该测试或启动参数。

## 4. T-1 回归（`REPRODUCE.ps1`）

```
powershell -NoProfile -ExecutionPolicy Bypass -File _t1_fix_evidence\REPRODUCE.ps1 \
  -Repository 'F:\桌面\ol\ol-mod-olfinal' -LogDirectory _t2_1_evidence
```

| 检查 | 结果 |
| --- | --- |
| 退出码 | **0** |
| HEAD 断言 | `2a75bdd…` == 期望 `2a75bdd…` |
| 基线哈希 | **7/7 OK**（sv_network_mp.cpp/hpp、win_net.cpp/hpp、TransportLifecycleTests.cpp、EngineBindings.hpp、ClientProcessPatches.cpp） |
| `ol_transport_lifecycle_tests` | **checks=124 failures=0**，exit 0 |
| `ol_game_server_tests` | exit 0 |
| `ol_lua_runtime_tests` | exit 0 |
| `ol_game_server`（生产插件，仅编译链接） | exit 0 |
| `git diff --check` | exit 0 |
| `build\stage` mtime | **2026-10-09 17:01:07**（与 T-2 记录一致，未变） |
| 日志 | `_t2_1_evidence/reproduce_20261010_141310.log`（51899 B） |

## 5. 破坏性/越界操作核查

| 检查 | 结果 |
| --- | --- |
| `ol_deploy` | **未触发**（REPRODUCE 全程命名目标，`build\stage` mtime 未变） |
| 启动游戏客户端 | **未启动**（`Get-Process` 无 `codoMP_client_shipRetail` / `out` / `ol_room_owner`） |
| 附加 Frida 到游戏进程 | **未发生**（全部测试使用 mock 设备/脚本；工具仅执行过 `--help`，在 `get_local_device()` 之前退出） |
| 读取游戏内存 | **未发生** |
| 插件 DLL / 导出签名 / 错误码 10037 / `DllMain` / 网络析构 | **零改动**（`src/` 未触碰；7 个 `src/` 改动全部是 T-1 之前既有的未提交内容，哈希与 T-1 冻结值一致） |
| `reset` / `rebase` / `clean` / `commit` / `push` | **未执行** |
| D 历史副本 | **未操作**（本轮只写 `_t2_1_evidence/` 与本轮交付物；`D:\BaiduNetdiskDownload\使命召唤OL` 根目录不是 git 工作树） |
| `.runtime/frida` | mtime 仍为 `2026/10/10 13:41:41`（T-2 验收探针遗留），本轮**未**改写 |

## 6. 与 T-2 的逐项对比

| 项 | T-2 | T-2.1 | 变化 |
| --- | --- | --- | --- |
| 调用方测试数 | 25 | **40** | **+15** |
| 工具测试数 | 0（无该文件） | **24** | **+24** |
| 合计测试数 | 25 | **64** | **+39** |
| 失败数 | 1（既有） | **1**（同一既有项） | 0 |
| G1 PID 身份校验 | ❌ 无 | ✅ 三层（调用方预检 / 附加前 / 附加后） | 修复 |
| G2 结果分类 | ❌ 非零统一 `refused` | ✅ 四态 + 结构化 JSON + 退出码交叉核对 | 修复 |
| G3 多 PID 聚合单测 | ❌ 无 | ✅ 7 项 | 补齐 |
| 工具退出码 | 0 / 2 | 0 / 1 / 2 / 3 | 兼容扩展 |
| T-1 基线哈希 | 7/7 OK | **7/7 OK** | 无回归 |
| `checks=124` | ✅ | ✅ | 无回归 |
| `build\stage` mtime | 2026-10-09 17:01:07 | **未变** | 无部署 |

**改动规模**：

| 文件 | T-2 后行数 | T-2.1 后行数 |
| --- | --- | --- |
| `tools/runtime/CodolGameServerControl.py` | 1786 | 1920 |
| `tools/runtime/CodolGame.py` | 1155 | 1253 |
| `tools/runtime/CodolGameTests.py` | 616 | 811 |
| `tools/runtime/CodolGameServerControlTests.py` | — | 362（新增） |

## 7. 证据清单

目录：`_t2_1_evidence/`

- `caller_tests_current.log` — 调用方测试（40 项，1 失败）
- `tool_tests_current.log` — 工具测试（24 项，0 失败）
- `caller_tests_head_both.log` — HEAD+HEAD 对照（17 项，1 失败）
- `head_both/` — 用 `git show HEAD:` 逐字节取出的 HEAD 版 `CodolGame.py` / `CodolGameTests.py` / `CodolClientAccount.py`
- `reproduce_20261010_141310.log` — T-1 REPRODUCE 完整日志

## 8. 最终结论

> ### **有条件通过**
>
> **功能修复已完成**：G1（三层 PID 身份校验，全部失败关闭）与 G2（工具四态结构化结果 + 调用方精确分类）均已实施；G3 多 PID 聚合由 7 项新单测保护；新增 39 项测试全部通过（工具 24/24）；T-1 基线哈希 7/7、`checks=124 failures=0`、`ol_game_server` 编译链接通过、`build\stage` 未被触碰；`git diff --check` exit 0；调用方唯一失败项在 HEAD 上以完全相同方式存在，属既有问题。
>
> **未判为"通过"的原因**：仍存在**明确且已披露**的限制（见 G1 报告 §6）——
> 1. **R1 身份是名字级的**：只比对映像基名，不校验构建号/映像哈希/签名，同机同名不同构建无法区分；
> 2. **R3/R4 附加后复核缺少运行时证据**：`Process.enumerateModules()[0]` 守卫只有结构性证据（程序序断言 + mock 消息），未在真实 Frida 附加下验证；无法报告主模块名时按失败关闭处理，可能拒绝合法目标。
>
> 上述限制均已在 G1 报告中逐条披露，且修复方向是**失败关闭**（宁可拒绝，不会误附加）。真实客户端上的运行时验证按任务要求**不在本轮授权范围**，留待独立验收通过后另行申请。
