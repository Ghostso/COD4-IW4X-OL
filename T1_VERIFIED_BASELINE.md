# T1_VERIFIED_BASELINE — T-1 通过基线固化

**日期**：2026-10-10
**工作基准**：**F = `F:\桌面\ol\ol-mod-olfinal`**（唯一活动基准）
**冻结对象**：FF-1（OS 层端口释放回归）+ FF-2（`lastSocketError` 契约）的**已验证成果**
**本阶段性质**：**只读核对 + 新增一份可复现脚本与一份文档。未修改任何生产源码，未修改任何测试，未覆盖或删除任何历史日志，未提交 Git。**

---

## 0. 冻结结论

| 项 | 冻结值 |
| --- | --- |
| F HEAD | `2a75bdd8872bb9f54006382a924c3006ec9affc2` |
| F 分支 | `OLfinal-live`（`0 behind / 8 ahead`） |
| F 工作区状态 | **11** 条（8 M + 3 ??） |
| `git diff --check` | **exit 0** |
| 最终断言 | **`checks=124 failures=0` · `run exit=0`** |
| 受保护常量 / ABI / RVA / 协议 / 启动链 / S2-S3 | **未变** |
| `ol_deploy` | **未触发**（`build\stage` mtime 仍为 2026-10-09 17:01:07） |
| D 工作树 | **冻结只读**（6 条状态，HEAD 同 F，未触碰） |
| Git 提交 / 推送 | **无** |

---

## 阶段 A 逐项核对

### A1 — HEAD、git status、T-1 文件哈希

**F**：`HEAD=2a75bdd…` · `branch=OLfinal-live` · `ab=0 8` · `statusCount=11` · `diffCheck=0`

```
 M src/game_server/Appmain.cpp
 M src/game_server/FrameHook.cpp
 M src/game_server/FrameHook.hpp
 M src/game_server/server_mp/sv_network_mp.cpp
 M src/game_server/server_mp/sv_network_mp.hpp
 M src/game_server/win32/win_net.cpp
 M src/game_server/win32/win_net.hpp
 M xmake.lua
?? tests/game_server/TransportLifecycleTests.cpp
?? tools/reverse/ReplayEngineBindings.py
?? tools/reverse/ReplayEngineBindingsTests.py
```

**D**：`HEAD=2a75bdd…` · `branch=OLfinal-live` · `ab=0 8` · `statusCount=6` · `diffCheck=0`（5 M + 1 ??，与轮次开始时逐行相同）

**T-1 相关文件哈希（F，冻结值）**：

| 文件 | 字节 | SHA-256 | 本轮是否改动 |
| --- | --- | --- | --- |
| `src/game_server/server_mp/sv_network_mp.cpp` | 7,382 | `EF4E209BDD9EFDCD5A1F7F69B3789E77852FD98C1371D7C1154677EEBFF19B60` | **否**（FF-2 已实施，本阶段只固化） |
| `src/game_server/server_mp/sv_network_mp.hpp` | 4,808 | `53E5907AE4AFD9251A2192DB2634D88223F6037DB57D772DCC7A081D4E8612C1` | **否** |
| `src/game_server/win32/win_net.cpp` | 9,054 | `3A34D953D2A7A4830D99FF77988A2C791AAB36F968049906F06B832EABAA9A14` | **否**（FF-3/FF-4 未实施） |
| `src/game_server/win32/win_net.hpp` | 2,642 | `8F0FF3189887660DEBB968C6CFF1E055CF065951E82E72F2E2ECF71451F5FBC1` | **否** |
| `tests/game_server/TransportLifecycleTests.cpp` | 32,859 | `FA67AE5B9C6D222CB3B8630D0EEA3D143A860A5E4C55753EB0951A7650A4C8AD` | **否** |

### A2 — FF-1 / FF-2 源码差异与本轮报告一致

| 核对项 | 报告声明 | 实测 | 一致 |
| --- | --- | --- | --- |
| FF-2 仅改 `sv_network_mp.cpp` 两条成功早退路径 + 注释 | 报告 §4.1 | 当前文件哈希 `EF4E209B…` 与报告 §9 一致；反向还原后得 `AF93F7C8…` = 阶段 0 基线 | ✅ |
| FF-2 仅改 `sv_network_mp.hpp` 契约措辞 | 报告 §4.2 | 当前 `53E5907A…`；反向还原后得 `A5BBE547…` = 阶段 0 基线 | ✅ |
| FF-1 只改测试文件 | 报告 §2 | `win_net.cpp` / `win_net.hpp` 哈希与阶段 0 基线**逐字节相同** | ✅ |
| FF-3 / FF-4 未实施 | 报告 §3 / §5 | `win_net.{cpp,hpp}` 未变 | ✅ |

**差异隔离的可复现证明**：`_t1_fix_evidence/_reconstruct_pre_ff2.py` 反向还原两份文件，产物哈希与阶段 0 基线**逐字节相等**（`AF93F7C8…` / `A5BBE547…`）。仅 FF-2 的差异：`ff2_only.diff`、`ff2_only_hpp.diff`。

### A3 — 测试日志中的退出码、断言数、失败数

**逐日志实测（重新解析原文件，未修改）**：

| 日志 | 断言 | FAIL 状态行 | 退出码 |
| --- | --- | --- | --- |
| `phase1_ff1_build_run.log` | `checks=112 failures=0` | 0 | `CONFIGURE exit=0` · `BUILD exit=0` · `run exit=0` |
| `phase2a_ff2_assertions_before_fix.log` | `checks=124 failures=2` | **2** | `BUILD exit=0` · **`run exit=1`** |
| `phase2b_ff2_after_fix.log` | `checks=124 failures=0` | 0 | `BUILD exit=0` · `run exit=0` |
| `phase2c_related_targets.log` | — | 0 | `BUILD exit=0` · `run exit=0` · `BUILD exit=0` · `run exit=0` · `BUILD ol_game_server exit=0` |
| `phase3_ff4_tests.log` | `checks=124 failures=0` | 0 | `diff-check exit=0` · `run exit=0` |

**断言数轨迹（只增不减）**：106 → 112 → **124**；失败 2 → 0。

### A4 — 可复现的强制构建与测试命令

新增脚本：`_t1_fix_evidence/REPRODUCE.ps1`（含基线哈希断言；**HEAD 或任一基线哈希漂移即 exit 2 停止**）。

**调用方式**（实测于 Windows PowerShell 5.1；脚本含 UTF-8 BOM，因为仓库路径含非 ASCII 字符）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ^
  "D:\BaiduNetdiskDownload\使命召唤OL\_t1_fix_evidence\REPRODUCE.ps1" ^
  -LogDirectory "D:\BaiduNetdiskDownload\使命召唤OL\_t1_fix_evidence"
```

**脚本内部执行的命令**（每一步都**显式命名目标**，因为 `ol_deploy` 是 `set_default(true)` 且 `config/codol-game-dir.txt` 非空）：

```powershell
xmake f                                        # 仅配置，不构建
xmake build -r ol_transport_lifecycle_tests    # 强制全量重建（隔离测试目标）
build\bin\release\ol_transport_lifecycle_tests.exe
xmake build ol_game_server_tests ;  <exe>
xmake build ol_lua_runtime_tests ;  <exe>
xmake build ol_game_server                     # 生产插件：仅编译+链接
git diff --check
```

**本轮实测结果**（日志 `reproduce_20261010_130238.log`，51,899 B）：

```
HEAD=2a75bdd… expected=2a75bdd…
OK  EF4E209B…  src\game_server\server_mp\sv_network_mp.cpp
OK  53E5907A…  src\game_server\server_mp\sv_network_mp.hpp
OK  3A34D953…  src\game_server\win32\win_net.cpp
OK  8F0FF318…  src\game_server\win32\win_net.hpp
OK  FA67AE5B…  tests\game_server\TransportLifecycleTests.cpp
OK  9ACE8731…  src\game_server\EngineBindings.hpp
OK  E81D760A…  src\game_server\ClientProcessPatches.cpp
baseline hashes all match
CONFIGURE exit=0
BUILD exit=0
ol_transport_lifecycle_tests run exit=0
checks=124 failures=0
BUILD exit=0 / ol_game_server_tests run exit=0
BUILD exit=0 / ol_lua_runtime_tests run exit=0
BUILD ol_game_server exit=0
diff-check exit=0
stage mtime=2026-10-09 17:01:07
```

> **关于 `reproduce_20261010_130228.log`（203 B）**：这是脚本**首次**运行的失败记录——当时脚本以无 BOM 的 UTF-8 落盘，PowerShell 5.1 按 ANSI 代码页读取，含中文的仓库路径被破坏，哈希断言前的 `HEAD` 比较即失败退出。该文件**保留未删**（历史证据），BOM 修复后才产生上面那份绿色日志。

### A5 — D 仍保持冻结只读

| 核对项 | D |
| --- | --- |
| HEAD / 分支 | `2a75bdd…` / `OLfinal-live`（与 F 相同） |
| `git status --porcelain` 条数 | **6**（与上一轮结束时**逐行相同**） |
| `git diff --check` | exit 0 |
| 本轮对 D 的写入 | **0** |
| 本轮对 D 的构建 / 运行 | **0** |

### A6 — 未覆盖旧日志、未删除历史证据、未提交 Git

| 项 | 结果 |
| --- | --- |
| 覆盖/删除旧日志 | **0**。`_batch10_evidence/`、`_p14_evidence/`、`_t1_fix_evidence/` 的既有文件全部保留 |
| 本阶段新增文件 | `_t1_fix_evidence/REPRODUCE.ps1` · `reproduce_20261010_130228.log`（失败记录）· `reproduce_20261010_130238.log`（绿色记录）· 三份交付文档 |
| Git 提交 / 推送 | **无**（HEAD 未变） |
| 生产源码修改 | **无**（本阶段零源码改动） |

---

## 证据分级（本阶段明确区分）

### ✅ 已验证行为（有实测退出码与断言数支撑）

| 行为 | 证据 |
| --- | --- |
| FF-1 的 OS 层释放探针在 `stop()` 后**成功** | `phase1`：`ok the OS released the port the transport held` |
| 探针具备判别力（仍被持有的端口会被拒绝） | `phase1`：`ok a still-held port refuses a second bind…`，`lastError=10048` |
| FF-2 的两条早退路径在**未修复**实现上确实**失败** | `phase2a`：`checks=124 failures=2`，`run exit=1`，2 条 FAIL 状态行 |
| FF-2 修复后三条成功路径全部清除该字段 | `phase2b`：`checks=124 failures=0`，`run exit=0` |
| 链接 `game_server_core` 的 4 个目标全部构建/运行通过 | `phase2c` + `reproduce_*` |
| 基线可复现（哈希断言 + 全绿） | `reproduce_20261010_130238.log` |

### 📄 仅由静态审查支持的结论

| 结论 | 依据 |
| --- | --- |
| `status_.bound` 与 `socket_.open()` 在稳态下等价 | `status_.bound` 全树**只有 2 处写**：`sv_network_mp.cpp:67`（紧接成功 `NET_IPSocket`）、`:87`（紧接成功 `close()`） |
| 该传输的 socket **从不调用** `connect()`/`WSAConnect()` | `win_net.cpp` 与 `sv_network_mp.cpp` 中 `connect` 0 命中；只有 `ioctlsocket(FIONBIO)`、`setsockopt(SO_BROADCAST)`、`bind`、`getsockname`、`recvfrom`、`sendto`、`closesocket` |
| `CODOL_GameServerSetEnabled(false)` 是唯一显式停止入口 | `Appmain.cpp:8174-8201`；全树 `SetEnabled` 只有 5 处引用（导出定义 + 后端 `GetProcAddress` + Frida 工具 3 处） |
| 树内无任何消费者把 `10037` 当作错误码比较 | 全树检索（详见 [T1_FF3_ERROR_DOMAIN_DECISION.md](T1_FF3_ERROR_DOMAIN_DECISION.md) §2） |

### ❓ 尚未验证的运行时假设

| 假设 | 为什么未验证 | 影响 |
| --- | --- | --- |
| 真实全加密客户端进程内 `bind`/`closesocket` 行为与测试环境一致 | 本轮未启动客户端（授权禁止） | FF-1 的探针结论仅在测试进程内被证实 |
| `CODOL_GameServerSetEnabled(false)` 会在正常卸载路径被调用 | 无任何树内调用方；Frida 工具是树外诊断路径 | 见 [NETWORK_UNLOAD_LIFECYCLE_REVIEW.md](NETWORK_UNLOAD_LIFECYCLE_REVIEW.md) |
| 真实 `closesocket` 失败路径 | 只能由 IAT 注入模拟（测试已标注为模拟） | FF-4 未实施，该路径仍不可观测 |
| 并发 `start()`/`stop()` | 无并发用例；`mutex_` 从未被竞争 | 生产多线程语义未验证 |

### ⚠️ 需要单独审批的接口变更

| 变更 | 状态 |
| --- | --- |
| FF-3 数值/结构变更（方案 B/D 或新增字段） | **未实施 · 待审批** |
| 新增导出函数（FF-3 方案 C2 或 Phase C 的关闭入口） | **未实施 · 需独立 ABI 审批** |

---

## 文件哈希与日志

**本阶段新增**：

| 文件 | 字节 | SHA-256 |
| --- | --- | --- |
| `_t1_fix_evidence/REPRODUCE.ps1` | 见清单 | 见 [\_t1_fix_evidence\\SHA256_MANIFEST.txt](_t1_fix_evidence/SHA256_MANIFEST.txt) |
| `_t1_fix_evidence/reproduce_20261010_130238.log` | 51,899 | 同上 |
| `_t1_fix_evidence/reproduce_20261010_130228.log` | 203 | 同上（失败记录，保留） |

**冻结的产物哈希**：

| 产物 | 字节 | 时间 | SHA-256 |
| --- | --- | --- | --- |
| `ol_transport_lifecycle_tests.exe` | 3,830,272 | 2026-10-10 12:50:50 | `14C13963223F3E3361A8D691DA6D6E742A4DF75A286EBB1FDC4130141E482DEB` |
| `ol_game_server_tests.exe` | 7,482,368 | 2026-10-10 12:51:48 | `706CAE920707DA8976F047E14878BB3CCC546915C566B9BAFDF66DE68D09CCEB` |
| `ol_lua_runtime_tests.exe` | 4,534,784 | 2026-10-10 12:52:22 | `9205E4BBE39EB9F5C5B24D483ED2245E8C93B0168385312D27560743D7DEC151` |
| `CodolGameServer.Localnet32` | 6,559,232 | 2026-10-10 12:52:50 | `DBA7273A0C9DD31CDD5619DD47B11C01EDC21AE17EEFC18FDD71F43B992097BC` |

> 说明：`reproduce_20261010_130238.log` 中的产物哈希可能与上表不同（重建会写入新的 PE 时间戳）。上表是**阶段 2 结束时**冻结的值；脚本每次运行都会重新记录当次哈希。

---

## 关联交付

- [T1_FF3_ERROR_DOMAIN_DECISION.md](T1_FF3_ERROR_DOMAIN_DECISION.md) — 错误码兼容性决策依据
- [NETWORK_UNLOAD_LIFECYCLE_REVIEW.md](NETWORK_UNLOAD_LIFECYCLE_REVIEW.md) — DLL 卸载前停止传输的生命周期审查
- [T1_FF1_PORT_RELEASE_REPORT.md](T1_FF1_PORT_RELEASE_REPORT.md) · [T1_FF2_ERROR_STATE_REPORT.md](T1_FF2_ERROR_STATE_REPORT.md) · [T1_FF4_DESTRUCTOR_REVIEW.md](T1_FF4_DESTRUCTOR_REVIEW.md) · [T1_FF3_ERROR_CODE_COMPATIBILITY.md](T1_FF3_ERROR_CODE_COMPATIBILITY.md)
