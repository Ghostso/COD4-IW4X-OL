# T2_1_G2_RESULT_CLASSIFICATION_REPORT — 区分附加失败与插件拒绝

**日期**：2026-10-10
**工作树**：**F = `F:\桌面\ol\ol-mod-olfinal`**（HEAD `2a75bdd8872bb9f54006382a924c3006ec9affc2`）
**修复范围**：`tools/runtime/CodolGameServerControl.py`、`tools/runtime/CodolGame.py` 及对应测试
**结论**：**G2 已修复**。工具与调用方均以四态结构化结果表达，附加失败不再伪装成插件拒绝，工具异常不再伪装成停止成功。

---

## 1. 缺陷回顾（T-2 验收审查 §4.5 / §7.1 G2）

- 工具只用**布尔退出码**：`return 0 if result.get("ok") else 2`（旧 `:1782`）。exit 2 同时表示"attach 失败"与"插件返回 false"。
- 调用方 `request_graceful_stop` 把**任何非零退出码**统一映射为 `("refused", …)`，`stop()` 据此返回退出码 4。
- 已实证后果：不存在的 PID（attach 必然失败）也被报成"插件拒绝"，把排查方向引向插件。
- 反向风险同样存在：`{"ok": false, …}` 若因异常分支产生，也会被当成插件拒绝。

## 2. 新的结果契约

工具在 **stdout 输出唯一一个 JSON 文档**（pretty-printed），其中 `result` 字段为权威分类，`ok` 仅为兼容保留：

| `result` | `ok` | 工具退出码 | 含义 | 调用方 `stop()` 行为 |
| --- | --- | --- | --- | --- |
| `confirmed` | `true` | **0** | 已成功附加并调用插件，插件返回 **true** | 打印确认；不警告 |
| `refused` | `false` | **2** | 已成功附加并调用插件，插件明确返回 **false** | 警告；最终退出码 **4** |
| `unavailable` | `false` | **3** | 无法请求停止：工具缺失、解释器缺失、本地设备/枚举/身份/附加失败、插件未加载 | 警告"未请求优雅停止"；**继续**终止流程 |
| `tool-error` | `false` | **1** | 工具异常、超时、输出无法解析、字段缺失、状态非法或自相矛盾 | 警告"停止工具失败"；**继续**终止流程，**不**升级为 4 |

**优先使用结构化字段**：调用方先解析 `result`，仅在**完全无法解析**时才参考退出码；且退出码**只用于交叉核对**，不作为分类依据（任务 §三.2）。

## 3. 工具侧改动（`CodolGameServerControl.py`）

1. **常量与映射**（`:28-44`）：`RESULT_CONFIRMED/REFUSED/UNAVAILABLE/TOOL_ERROR`、`STOP_RESULTS`、`RESULT_EXIT_CODES`。
2. **`report(result, payload)`**（`:109-121`）：统一打印文档并返回退出码；`result` 与 `ok` 由 `report` 权威写入，杜绝 JS 侧不一致。
3. **`main()` 包裹 `run()`**（`:1905-1916`）：任何未预期异常都打印 traceback 到 stderr，并在 stdout 输出 `{"result":"tool-error"}`（任务 §三.6：保留诊断、不丢失结构化结果）。
4. **注入 JS 的错误打标**（`:193-199`、`:214-220`、`:1777-1780`、`:1800-1813`）：
   - 身份不匹配 / 插件未加载 → `codolStop('unavailable', …)`
   - `CODOL_GameServerSetEnabled(true|false)` 返回 false → `codolStop('refused', …)`（**唯一**的拒绝来源）
   - 其它 JS 异常 → `result: 'tool-error'`
   - 成功采样 → `result: 'confirmed'`
5. **`on_detached` 在取得样本前断开 → `unavailable`**（`:1857`）。
6. **尾部兜底**（`:1891-1902`）：`result` 缺失/非法一律归一为 `tool-error`，绝不读作成功。

## 4. 调用方侧改动（`CodolGame.py`）

| 新增/修改 | 位置 | 作用 |
| --- | --- | --- |
| `GRACEFUL_STOP_OUTCOMES` 扩为四态；新增 `GRACEFUL_STOP_EXIT_CODES` | `:591-597` | 契约单一来源 |
| `clip_detail` | `:600-602` | 诊断文本截断（保持 400 字符上限） |
| `last_json_object` | `:605-626` | 从**多行** stdout 中取出最后一个完整 JSON 对象（工具是 pretty-printed，不能按行解析） |
| `target_image_matches` | `:629-647` | G1 的 L1 预检，复用 `process_image_name` |
| `classify_stop_result` | `:650-…` | 结构化分类 + 退出码交叉核对 + `ok` 一致性核对 |
| `request_graceful_stop` | `:…` | 预检 → 子进程 → `classify_stop_result`；超时/启动失败分别归类 |
| `stop()` 的 `tool-error` 分支 | `:1104-1108` | 单独警告"graceful stop tool failed"，与 `refused` 分离 |
| `stop()` PID 去重 | `:1066-1068` | `sorted(set(running_pids()))`，重复项不会使最坏延迟翻倍（G3 场景） |

**关键判定（任务 §三.4）**：只有 `result == "refused"` 才会置位 `graceful_refused`，也只有它使 `stop()` 返回 **4**。

## 5. 退出码兼容性分析（任务 §三.3）

### 5.1 工具退出码

| 退出码 | 修复前 | 修复后 | 兼容性 |
| --- | --- | --- | --- |
| 0 | 插件返回 true | `confirmed` | **不变** |
| 2 | 插件 false **或** attach 失败 | **仅** `refused`（插件 false） | 语义**收窄**，旧调用方看到的仍是"非零=失败" |
| 1 | 未使用（argparse 错误除外） | `tool-error` | 新增；旧调用方视为失败 |
| 3 | 未使用 | `unavailable` | 新增；旧调用方视为失败 |

### 5.2 全部调用者检查

| 调用者 | 用法 | 兼容性影响 |
| --- | --- | --- |
| `CodolGame.request_graceful_stop` | `--disable --pid --sample-seconds 0` | **本轮同步更新**，按 `result` 分类 |
| `CodolAimControl.player_state`（`:44-66`） | `--pid --sample-seconds 0`，读 `payload["ok"]` 与 `payload["after"]` | 新增字段为**附加**；`returncode != 0 or not ok` 判断不变；attach 失败由 exit 2 变 exit 3，仍是非零 → 仍抛 `RuntimeError`，重试语义不变 |
| `CodolNaturalMatchTrace.start_server_watcher`（`:898-920`） | `--pid --watch-log --watch-interval --watch-seconds 0 --stop-file` | watch 行格式与 `payload.ok/after` 未变；`wait_for_server_watch_ready` 的判据（`returncode==0` 且 `ok is True`）在成功路径上不变 |
| 插件 C++ 注释引用（`DedicatedControl.hpp:215` 等） | 仅文档 | 无影响 |

**结论**：0/2 的既有约定保持不变；1/3 为新增且对"只懂零/非零"的调用方仍表现为失败。**未调整任何既有成功语义**。

### 5.3 兼容策略保持（任务 §三.7）

`unavailable` 与 `tool-error` 都**不**取消调用方请求的终止流程：打印 WARNING 后继续 `terminate_pids`，进程全部停止时最终退出码仍为 0。这正是 T-2 既定的"停止请求不可用时警告并继续"策略，本轮**未**发现该行为与报告不符，故保留。

## 6. 分类决策记录

| 情形 | 归类 | 理由 |
| --- | --- | --- |
| `attach` 失败 | `unavailable` | 任务 §三.1 明确列举"附加失败"为 unavailable |
| 插件未加载（DLL 未注入） | `unavailable` | 未能请求到插件；不是插件的回答 |
| 附加后身份不匹配 | `unavailable` | 同 G1，失败关闭 |
| `TimeoutExpired` | `tool-error` | 工具已启动但**未给出可用结果**，符合"结果不符合约定"；**不再**归为 `refused`（修复前的缺陷之一） |
| 解释器缺失 / `OSError` 启动失败 | `unavailable` | 无法请求停止 |
| 退出码非零但无有效 JSON | `tool-error` | 无法证明插件返回过 false |
| JSON 缺 `result`、值非法 | `tool-error` | 同上 |
| 退出码与 `result` 矛盾、`ok` 与 `result` 矛盾 | `tool-error` | "结果不符合约定" |

## 7. 测试（G2）

### 7.1 工具级（`CodolGameServerControlTests.py`，`ResultClassificationTests` 8 项）

- `test_report_maps_each_result_to_its_exit_code`（四态 × 退出码 × `ok`）
- `test_the_historical_exit_codes_are_unchanged`（0/2 冻结）
- `test_the_plugin_returning_true_is_confirmed`
- `test_the_plugin_returning_false_is_refused`
- `test_a_missing_result_field_is_a_tool_error`
- `test_an_illegal_result_value_is_a_tool_error`
- `test_a_timed_out_sample_is_a_tool_error_with_diagnostics`（超时 + traceback 保留）
- `test_an_unexpected_exception_still_produces_a_document`

### 7.2 调用方级（`CodolGameTests.py`，G2 相关）

- `test_request_graceful_stop_classifies_every_tool_document` — 四种文档 → 四种结果
- `test_an_attach_failure_is_never_reported_as_a_refusal` — **G2 核心回归**
- `test_a_plugin_refusal_keeps_its_own_error_text`
- `test_request_graceful_stop_rejects_output_without_a_valid_document`（空输出 / 非 JSON / 缺字段 / 非法状态）
- `test_request_graceful_stop_rejects_a_self_contradicting_document`（退出码矛盾、`ok` 矛盾）
- `test_request_graceful_stop_reads_a_pretty_printed_document`（多行文档 + 前缀噪声）
- `test_request_graceful_stop_never_raises`（重写：`FileNotFoundError`→unavailable、`TimeoutExpired`→tool-error、`OSError`→unavailable）
- `test_request_graceful_stop_treats_a_missing_tool_as_unavailable`
- `test_multi_pid_stop_does_not_call_a_tool_error_a_refusal`（见 G3 报告）

## 8. 剩余说明

| 项 | 说明 |
| --- | --- |
| watch 行内的 `returncode` 字段 | 仍为 `0 if payload.ok else 2`（`CodolGameServerControl.py:1832`）。它是**日志字段**，`CodolNaturalMatchTrace` 只读 `ok`/`after`；未改动以零风险保持兼容 |
| argparse 错误 | `parser.error()` 走 `SystemExit(2)`，不会经过 `report()`，因此其 stdout 无 JSON。调用方对"exit 2 且无 JSON"归为 `tool-error`，**不会**误判为插件拒绝。调用方命令行固定且合法，此路径实际不可达 |
| 真实客户端 | 本轮**未**附加任何真实游戏进程；`refused`/`confirmed` 的真实端到端证据仍待下一阶段运行时验证 |
