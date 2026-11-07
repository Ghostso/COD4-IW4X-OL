# T2_4C_RUNTIME_PROBE_REPORT — Stage C 真实 Frida 运行时无害探针

**日期**：2026-10-10　**运行 ID**：`T24C-20261010T151037-fe775bfe`
**工作树**：**F = `F:\桌面\ol\ol-mod-olfinal`**（HEAD `2a75bdd…`，分支 `OLfinal-live`）
**范围**：**仅 Stage C**。未启动、未附加、未注入、未读取、未终止任何 CODOL 进程。

## 0. 最终裁定

> ### **A. Stage C 通过**
>
> 六个用例（A–F）全部 `PASS`：真实 Frida 原生运行时 **16.5.9** 附加到专用无害进程并执行了 JavaScript 探针；**实际调用了 `Module.findExportByName(null, exportName)`**；已存在导出返回非空地址、不存在导出返回 `null` 且不抛异常；脚本异常、超时、**矛盾结果**均被准确报告为失败而非成功；测试进程按身份复核后**优雅退出**（exit 0，未使用 `taskkill /T /F`）；仓库与 T-2.3 已验收代码零变化。

## 1. 环境与版本

| 项 | 值 |
| --- | --- |
| Python | 3.11.9（`C:\Users\Z7-CT5N1\AppData\Local\Programs\Python\Python311\python.exe`） |
| Frida Python 包 | **16.5.9** |
| **Frida 原生运行时**（`Frida.version`，由探针在目标进程内读取） | **16.5.9** |
| frida-tools | 13.0.1 |
| Frida 临时目录 | `_t2_4c_evidence\frida-tmp`（隔离，未写入项目树） |
| 单用例消息超时 | 8.0 s |
| 提取的 agent（x86_64） | `frida-agent.dll` 24,416,768 B / `85B5BE94…3302` |

> Python 包版本与原生运行时版本**一致**（均为 16.5.9），且落在 T-2.3 声明的 `frida>=16.5,<19` 区间内。

## 2. 无害测试进程身份

| 项 | 值 |
| --- | --- |
| 宿主脚本 | `probe_host.py`（仅 import json/os/sys/time；**不开 socket、不发流量、不加载任何 CODOL 模块**） |
| PID | **17832** |
| 映像路径 | `…\Python311\python.exe` |
| nonce | 运行期随机生成，随命令行走参数传递 |
| 握手文件自述 PID == 驱动 spawn 的 PID | ✅ true |
| 握手 nonce == 驱动生成的 nonce | ✅ true |
| OS 层映像路径 == 驱动解释器路径 | ✅ true |
| OS 层命令行包含本宿主脚本路径 | ✅ true |
| 四项合并判定 `identity_ok` | **true** |

> 身份无法确认时驱动**不会附加**（代码路径已实现；本次未触发）。这是“不能可靠区分测试进程就停止”的落实方式。

## 3. 用例结果

> **`exit_code` 约定**：用例的 `exit_code` 是**分类码**（`PASS=0 / FAIL=1 / ERROR=2 / TIMEOUT=124 / SKIPPED=77`），不是子进程退出码——Frida 探针没有子进程。驱动自身与宿主进程的真实退出码见 §6。

| 用例 | 目的 | 状态 | 分类码 | 耗时(s) | 判定说明 |
| --- | --- | --- | --- | --- | --- |
| **A** | 附加 + 脚本执行 + `send()` 携带运行 ID | **PASS** | 0 | 0.128 | 原生 Frida 16.5.9 在 pid 17832 内执行了探针 |
| **B** | **已存在**导出的查找 | **PASS** | 0 | 0.014 | `ExitProcess` 与 `Sleep` 均返回非空地址 |
| **C** | **不存在**导出的查找 | **PASS** | 0 | 0.012 | 返回 `null`，未抛异常 |
| **D** | 脚本异常分类 | **PASS** | 0 | 0.007 | 故意异常被报为 `error`，未被当作结果 |
| **E** | 超时处理 | **PASS** | 0 | 8.008 | 超时后会话被干净关闭，宿主仍存活 |
| **F** | **结果异常**（负对照） | **PASS** | 0 | 0.008 | 自相矛盾的结果被**拒绝**而非接受 |

整轮耗时 **12.184 s**。

## 4. API 调用成功与失败的原始证据

### 4.1 探针 A — 附加与执行

``
{"test": "A", "id": "T24C-20261010T151037-fe775bfe", "status": "loaded",
 "frida_version": "16.5.9", "frida_heap_size": 1499904, "pid": 17832,
 "arch": "x64", "pointer_size": 8, "image_name": "python.exe",
 "image_path": "C:\\Users\\Z7-CT5N1\\AppData\\Local\\Programs\\Python\\Python311\\python.exe",
 "module_count": 32}
``

### 4.2 探针 B — 已存在的导出（**核心**：实际执行了 `Module.findExportByName(null, …)`）

``
{"test": "B", "id": "T24C-20261010T151037-fe775bfe", "status": "loaded", "results": [
  {"name": "ExitProcess", "global_threw": false, "global_is_null": false,
   "global_address": "0x7fffc5f7e3e0", "module_threw": false, "module_is_null": false,
   "module_address": "0x7fffc5f7e3e0", "addresses_agree": true},
  {"name": "Sleep", "global_threw": false, "global_is_null": false,
   "global_address": "0x7fffc5f7b0e0", "module_threw": false, "module_is_null": false,
   "module_address": "0x7fffc5f7b0e0", "addresses_agree": true}]}
``

- 全局形式（`null` 模块名）与模块限定形式（`'kernel32.dll'`）返回**完全相同**的地址，互为交叉验证；
- 只读取地址字符串：**未**构造 `NativeFunction`、**未**调用该地址、**未**读写该地址指向的内存。

### 4.3 探针 C — 不存在的导出

``
{"test": "C", "id": "T24C-20261010T151037-fe775bfe",
 "absent": "t24c_absent_export_2c762d667884431d8f36c8bc34bfa351",
 "status": "loaded", "threw": false, "is_null": true, "address": null}
``

随机名称已写入本报告与 `T2_4C_RESULTS.json`，可原样复现。

### 4.4 探针 F — 结果异常（负对照）

``
{"test": "A", "id": "T24C-20261010T151037-fe775bfe", "status": "loaded",
 "frida_version": "16.5.9", "pid": -1, "arch": "x64", "pointer_size": 8,
 "image_name": "deliberately-wrong.exe", "module_count": -1}
``

驱动判定：`expected_classification = FAIL`，`observed_classification = FAIL`，用例状态 `PASS`（负对照被正确拒绝：`Process.id did not match the attached PID`）。

## 5. 异常与超时行为

### 5.1 脚本异常（探针 D）

``
{"type": "error", "description": "Error: T24C_DELIBERATE_SCRIPT_EXCEPTION",
 "stack": "Error: T24C_DELIBERATE_SCRIPT_EXCEPTION\n    at <eval> (/script1.js:5)",
 "fileName": "/script1.js", "lineNumber": 5, "columnNumber": 1}
``

- 驱动在 0.007 s 内收到该 `error` 消息；
- 用例被标记为**错误检出**，**没有**任何字段出现 `confirmed` 或 `refused`；
- 会话在 `finally` 中正常 `unload` / `detach`（`unload_ok`、`detach_ok` 均为 true），**清理能力未丢失**。

### 5.2 超时（探针 E）

- 探针只发 `status: started`，此后**永不**发送终态消息（延迟消息设在 60 s，远大于 8 s 上限）；
- 驱动在 **8.008 s** 判定 `TIMEOUT` 路径，随后 `unload_ok` / `detach_ok` 均为 true；
- 超时后宿主进程**仍然存活**（`host_alive_after = true`），随后的身份复核与清理均成功。

## 6. 测试进程清理

| 项 | 值 |
| --- | --- |
| 终止前身份复核 | `exists=true`、`path_matches=true`、`cmdline_has_host=true` |
| 清理方式 | 写入停止信号文件 → 宿主**自行退出**（**未**使用 `taskkill /T /F`） |
| 宿主退出码 | **0** |
| 是否强制终止 | **否**（`forced_single_pid_terminate = false`） |
| 优雅退出 | ✅ true |
| 事后 PID 17832 是否存在 | **否** |
| 残留 `probe_host.py` 进程 | **0**（标记通过环境变量传入，避免查询自匹配） |

## 7. 基线完整性检查

| 检查 | 结果 |
| --- | --- |
| HEAD | `2a75bdd8872bb9f54006382a924c3006ec9affc2`（未变） |
| `git status` 条目数 | **17**（与运行前一致） |
| T-2.3 已验收 6 个文件哈希 | **6/6 未变** |
| `build\stage` mtime | `2026-10-09 17:01:07`（未变，无部署） |
| D 历史副本 | `statusCount = 6`（只读，未修改） |
| CODOL / 游戏进程 | **0** |
| Frida 残留进程 | **0** |
| 游戏端口 28960/28961/28962/28970 监听 | **0** |
| 合并判定 `no_codol_touched` | **true** |

> 本轮**未修改任何生产代码**。新增文件全部位于独立证据目录 `_t2_4c_evidence\`（不属于项目生产代码）。

## 8. 未验证事项（明确披露）

1. **未启动、未附加、未注入、未读取、未终止任何 CODOL 进程**；
2. **未调用** `CODOL_GameServerSetEnabled(false)` 或任何游戏专用导出；
3. **未加载或查询**游戏插件 `CodolGameServer.Localnet32`；
4. **未验证** UDP 端口释放、`transport.bound` 语义、客户端退出；
5. 本轮的 `PASS` **只证明对应的无害场景**：API 查找成功 **不等于** 游戏插件导出存在；Frida 附加成功 **不等于** CODOL 兼容；
6. 探针在插件缺失的宿主上运行，因此**未**执行到出货脚本中的终止钩子循环——出货脚本真正走到那一行仍需 Stage D；
7. 未执行 Stage D / E / F / T，**不会**自动推进。

### 8.1 本轮发现的工具局限（如实披露）

| 项 | 说明 |
| --- | --- |
| 驱动退出码语义 | `frida_probe_driver.py` 完成时一律返回 0；**用例成败以 `cases[].status` 为准**，不看驱动退出码。若后续正式化，应让用例失败反映到进程退出码。 |
| 用例 `exit_code` | 是分类码而非子进程退出码（见 §3 说明）。 |
| 第一轮运行 | run_id `T24C-20261010T150835-6ee207fb`（探针 A–E）结果相同但**缺负对照**，已被本轮取代并归档于 `run1_superseded\`，**未删除**。 |

## 9. 越界核查（逐条对照任务禁止项）

| 禁止项 | 结果 |
| --- | --- |
| 启动/附加/注入/终止 CODOL、启动器或插件进程 | **未发生**（游戏进程计数 0，且从未附加） |
| 读取任何游戏进程内存 | **未发生** |
| 调用 `CODOL_GameServerSetEnabled` 或其他游戏导出 | **未发生** |
| 运行 `CodolGame.py stop` / `ol_deploy` | **未运行** |
| 修改插件 DLL / ABI / 游戏配置 / T-2.3 已验收代码 | **未修改**（6/6 哈希未变） |
| 操作 D 副本、reset/rebase/clean/commit/push | **未执行** |
| 把测试失败升级为更高权限操作、自动转入其他 Stage | **未发生** |

## 10. 关联产物

- `T2_4C_RESULTS.json` — 机器可读结果（含 environment / host / cases / cleanup / integrity / verdict）
- `T2_4C_SHA256_MANIFEST.txt` — 全部产物哈希
- 原始 Frida 日志：`frida_raw.jsonl`
- 驱动日志：`driver.log`、`driver_stdout.txt`
- 进程生命周期记录：`host_handshake.json`、`host_lifecycle.json`
- 探针源码：`probe_host.py`、`probe_A.js` … `probe_F.js`、`frida_probe_driver.py`、`postcheck.py`
- 第一轮归档：`run1_superseded\`
