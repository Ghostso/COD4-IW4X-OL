# T2_3_REGRESSION_REPORT — 离线回归验收

**日期**：2026-10-10
**工作树**：**F = `F:\桌面\ol\ol-mod-olfinal`**（HEAD `2a75bdd8872bb9f54006382a924c3006ec9affc2`，分支 `OLfinal-live`）
**本轮性质**：离线验收。**未启动游戏、未附加 Frida、未读内存、未部署、未执行 reset/rebase/clean/commit/push。**
**最终结论**：**有条件通过**（见 §8）。

---

## 1. 冻结核对

| 项 | 值 | 判定 |
| --- | --- | --- |
| F HEAD / 分支 | `2a75bdd8872bb9f54006382a924c3006ec9affc2` / `OLfinal-live` | 与 T-2.1 / T-2.2 一致 ✅ |
| F `git status -uall` | **17** 条（12 M + 5 ??）；T-2.2 为 15 条 | +1 M（`requirements-codol.txt`）+1 ??（`config/codol-target-build.json`） |
| T-2.2 交付物哈希 | `T2_2_RUNTIME_READINESS_REVIEW.md` `15E4DCE7…`；`T2_2_EXPERIMENT_PROTOCOL.md` `4512A5A1…`；`T2_2_SHA256_MANIFEST.txt` `3A955F80…` | 与 T-2.2 清单一致 ✅ |
| D 历史副本 | `_e1_regression\ol-mod-olfinal`：HEAD 同、`statusCount=6` | **未修改** ✅ |
| `build\stage` mtime | `2026-10-09 17:01:07` | **未变**，无部署 ✅ |

## 2. 测试执行（全部离线）

| # | 套件 | 命令 | 测试数 | 失败 | 退出码 | 日志 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | **Frida 工具** | `python CodolGameServerControlTests.py -v` | **34** | **0** | **0** | `_t2_3_evidence/tool_tests_t23.log` |
| 2 | **调用方** | `python CodolGameTests.py -v` | **59** | **1** | 1 | `_t2_3_evidence/caller_tests_t23.log` |
| 3 | **HEAD+HEAD 对照** | HEAD 版模块 + HEAD 版测试（同版本配对） | **17** | **1** | 1 | `_t2_3_evidence/caller_tests_head_both.log` |
| 4 | T-1 复现 | `REPRODUCE.ps1`（`-ExecutionPolicy Bypass`） | — | — | **0** | `_t2_3_evidence/reproduce_20261010_144933.log` |
| 5 | 空白检查 | `git diff --check` | — | — | **0** | 内联 |

**合计**：93 项（工具 34 + 调用方 59），失败 **1**（既有 `-qa` 项）。

### 2.1 唯一失败项 = 既有失败，非本轮引入

``
FAIL: test_only_dedicated_uses_native_qa_launch_bypass (CodolGameTests.py:103)
AssertionError: Lists differ: ['-qa'] != []
``

**HEAD+HEAD 正确对照**（用 `git show HEAD:` 逐字节取出同版本的模块与测试文件）：

| 配置 | 测试数 | 失败 | 失败项 |
| --- | --- | --- | --- |
| HEAD `CodolGame.py` + HEAD `CodolGameTests.py` | **17** | **1** | `test_only_dedicated_uses_native_qa_launch_bypass` |
| 当前 `CodolGame.py` + 当前 `CodolGameTests.py` | **59** | **1** | **同一项** |

⇒ 该失败在 HEAD 上以**完全相同**的方式存在，与 T-2.1 / T-2.2 / T-2.3 均无关（`launch_arguments` 的 `-qa` 门禁是有意行为，测试未跟进；位于**启动**路径，与停止路径无关）。

**未删除任何历史失败日志**，也**未**修改该测试或启动参数以“消除”失败。

### 2.2 相对 T-2.1 / T-2.2 的测试规模

| 套件 | T-2.1 | T-2.3 | 变化 |
| --- | --- | --- | --- |
| Frida 工具 | 24 | **34** | **+10** |
| 调用方 | 40 | **59** | **+19** |
| 合计 | 64 | **93** | **+29** |
| 失败 | 1（既有） | **1**（同一既有项） | 0 |

新增 10 项工具测试：API 面白名单（含 `node --check` 真语法检查）、必需导出校验、缺失导出分类、Frida 版本守卫与边界、脚本载入异常分类。
新增 19 项调用方测试：9 项 `terminate_pids` 身份复核、10 项 `verify_target_build` / 基线解析。

## 3. T-1 回归（`REPRODUCE.ps1`）

| 检查 | 结果 |
| --- | --- |
| 退出码 | **0** |
| HEAD 断言 | `2a75bdd…` == 期望值 |
| 基线哈希 | **7/7 OK** |
| `ol_transport_lifecycle_tests` | **checks=124 failures=0**，exit 0 |
| `ol_game_server_tests` / `ol_lua_runtime_tests` | exit 0 / exit 0 |
| `ol_game_server`（生产插件，仅编译链接） | exit 0 |
| `git diff --check`（脚本内） | exit 0 |
| `build\stage` mtime | `2026-10-09 17:01:07`（未变） |

## 4. G-C1 前置条件实测

| 命令 | 结果 | 退出码 |
| --- | --- | --- |
| `verify-target --game-dir E:\CODOL_SANDBOX\RUN001` | `ok: true`；size/sha256/fileVersion 与基线逐项一致 | **0** |
| `verify-target --game-dir E:\CODOL_SANDBOX\NO_SUCH_RUN` | `ok: false`；`the game directory does not exist` | **1** |
| `verify-target`（无可解析的 `--game-dir`） | 要求显式参数 | **2** |

三次调用**均未启动游戏**、未附加 Frida、未读内存；仅读取磁盘文件。

## 5. 安全与越界核查

| 检查 | 结果 |
| --- | --- |
| 启动游戏客户端 | **未启动**（`Get-Process` 无 `codoMP_client_shipRetail` / `out` / `ol_room_owner`） |
| 附加 Frida 到游戏进程 | **未发生**（无 frida 进程；全部测试使用 mock 设备/脚本） |
| 读取游戏内存 | **未发生** |
| 终止真实游戏进程 | **未发生**（`terminate_pids` 的测试全部 mock 掉 `subprocess.run`） |
| `ol_deploy` | **未执行**（`build\stage` mtime 未变） |
| 插件 ABI / 导出签名 / 错误码 10037 / `DllMain` / 全局网络析构 | **零改动**（`src/` 未触碰；7 个 `src/` 改动全部是 T-1 之前既有内容，哈希与冻结值一致） |
| D 历史副本 | **未操作** |
| `reset` / `rebase` / `clean` / `commit` / `push` | **未执行** |

## 6. 本轮改动文件与哈希

| 文件 | T-2.1/2.2 值 | T-2.3 值 |
| --- | --- | --- |
| `tools/runtime/CodolGameServerControl.py` | `4B7C1CE4…` 84909 | `DF7291F3…` 87670 |
| `tools/runtime/CodolGame.py` | `8CBF194A…` 48265 | `74892CDE…` 58990 |
| `tools/runtime/CodolGameTests.py` | `B0B53130…` 36637 | `D04479DD…` 50279 |
| `tools/runtime/CodolGameServerControlTests.py` | `BC227C76…` 14191 | `FF875F16…` 21184 |
| `tools/runtime/requirements-codol.txt` | `9E33364C…` 57 | `0AD4FB80…` 56 |
| `config/codol-target-build.json` | — | `B892F5C9…` 815（新增） |
| `T2_2_EXPERIMENT_PROTOCOL.md`（G-C3 增补） | `4512A5A1…` 12161 | `F1E3F82F…` 9139 |

> 协议文件只在末尾**追加** §10，未删除或改写既有条款；两个哈希都已记录在 [T2_3_SHA256_MANIFEST.txt](T2_3_SHA256_MANIFEST.txt)。

## 7. 与 T-2.1 / T-2.2 的逐项对比

| 项 | T-2.1 | T-2.2 | T-2.3 |
| --- | --- | --- | --- |
| 测试总数 | 64 | 64 | **93** |
| 失败数 | 1（既有） | 1（既有） | **1**（同一既有项） |
| T-1 基线哈希 | 7/7 OK | 7/7 OK | **7/7 OK** |
| `checks=124` | ✅ | ✅ | ✅ |
| G-B1（Frida API） | — | ❌ 阻塞 | ✅ **已修复** |
| G-C1（游戏目录前置） | — | ⏳ 条件 | ✅ **已解决** |
| G-C2（终止前复核） | — | ⏳ 条件 | ✅ **已解决** |
| G-C3（构建确认） | — | ⏳ 条件 | ✅ **已进入协议** |
| G-C4（版本约束） | — | ⏳ 条件 | ✅ **已收敛** |
| `build\stage` mtime | 未变 | 未变 | **未变** |

## 8. 最终结论

> ### **有条件通过**
>
> **五项阻塞全部解决**：G-B1（非法 Frida API）、G-C1（游戏目录/构建前置）、G-C2（终止前 PID 复核）、G-C3（构建确认进入协议）、G-C4（版本约束收敛）。**离线回归全部通过**：工具 34/0、调用方 59/1（既有 `-qa`）、HEAD+HEAD 17/1（同一既有项）、`REPRODUCE.ps1` exit 0（7/7 哈希、`checks=124 failures=0`）、`git diff --check` exit 0。
>
> **未判为“通过”的原因**（明确且可控制的非关键限制）：
> 1. 修复后的注入脚本**从未在任何真实 Frida 运行时中执行过**——兼容性由官方类型定义、安装二进制与 `node --check` 语法解析共同支持，但“能成功载入并找到导出”仍待运行时确认；
> 2. 声明范围内的 Frida 17.x / 18.x 本机不存在，同样**未经执行验证**；Frida ≥19 被**有意排除**在支持范围之外；
> 3. 终止前的身份复核把 PID 复用窗口**缩小但未消除**（路径读取与 `taskkill` 之间仍有极短窗口），且身份是 名称 + 路径 + SHA-256，**不是**密码学签名。
>
> 以上均已在 [T2_3_FRIDA_API_FIX_REPORT.md](T2_3_FRIDA_API_FIX_REPORT.md) §5 与 [T2_3_ENVIRONMENT_GUARDS_REPORT.md](T2_3_ENVIRONMENT_GUARDS_REPORT.md) §3.3/§5 逐条披露，且修复方向一律是**失败关闭**。

**本轮未授权真实客户端运行验证。** 即使离线验收全部通过，也只能据此提交新的运行验证申请，不得自行启动或附加游戏。

## 9. 关联交付

- [T2_3_FRIDA_API_FIX_REPORT.md](T2_3_FRIDA_API_FIX_REPORT.md) · [T2_3_ENVIRONMENT_GUARDS_REPORT.md](T2_3_ENVIRONMENT_GUARDS_REPORT.md) · [T2_3_SHA256_MANIFEST.txt](T2_3_SHA256_MANIFEST.txt)
- [T2_2_RUNTIME_READINESS_REVIEW.md](T2_2_RUNTIME_READINESS_REVIEW.md) · [T2_2_EXPERIMENT_PROTOCOL.md](T2_2_EXPERIMENT_PROTOCOL.md) §10
- 证据：`_t2_3_evidence/`
