# BASELINE_ADJUDICATION — 工程基准裁定与冻结规则

**裁定日期**：2026-10-10
**裁定人**：CODOL 复活项目 / Batch 10 审阅后基线冻结轮次
**会话工作目录**：`D:\BaiduNetdiskDownload\使命召唤OL`（**未改变**）
**本轮性质**：只读采集 + 差异归档 + 显式命名的隔离测试目标构建/运行。**未做任何工作树切换、复制、覆盖、合并或清理。**

---

## 0. 一页裁定

| 项 | 裁定 |
| --- | --- |
| **唯一活动工作基准** | **F = `F:\桌面\ol\ol-mod-olfinal`** |
| **冻结历史回归副本** | **D = `D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal`** |
| D 的允许操作 | 只读检视、哈希核验、差异比对。**禁止**构建、运行、写入、清理、同步 |
| T-1 实现采用版本 | **F**（D 的 `start()` 是人工回退的 pre-T-1 体） |
| T-1 测试采用版本 | **F**（106 断言 / 13 用例；D 的 49 断言 / 9 用例是 F 的严格子集） |
| 会话是否已锚定到 F | **否**。会话工作目录仍是工作区根；F 侧操作全部通过**显式绝对路径 / `workdir`** 执行 |
| 客户端身份门禁 | 仍然 **BLOCKED**（见 [ARTIFACT_BLOCKERS.md](ARTIFACT_BLOCKERS.md)） |
| 本轮未授权同步次数 | **0** |

> **重要**：本会话的声明工作目录是 `D:\BaiduNetdiskDownload\使命召唤OL`，**不是** F。本节不声称"已切换基准"。所有 F 侧动作（构建、运行、哈希）都是逐条以绝对路径显式指向 F 完成的；会话的锚点没有被移动，也没有伪造移动。

---

## 1. 双工作树身份记录（采集时点 2026-10-10 11:5x）

| 项 | F | D |
| --- | --- | --- |
| 绝对路径 | `F:\桌面\ol\ol-mod-olfinal` | `D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal` |
| HEAD | `2a75bdd8872bb9f54006382a924c3006ec9affc2` | 同 F |
| 分支 | `OLfinal-live` | 同 F |
| upstream / 追踪 | `origin/OLfinal-live`，`branch.ab +8 -0` | 同 F |
| `origin` URL | `https://github.com/CODOL-EMU/ol-mod-olfinal.git` | 同 F |
| `.git` 形态 | 真实目录（非 gitfile、非 linked worktree） | 真实目录 |
| `.git` 体积 | 27.2 MB | 27.2 MB（**逐字节同尺寸**） |
| `.git\index` mtime | 2026-10-09 12:26:40 | 2026-10-09 12:26:40（**相同**） |
| reflog 条目数 | 54 | 54 |
| reflog 前 6 条 | 与 D 逐字相同 | 与 F 逐字相同 |
| 修改文件数 | **8** | **5** |
| 未跟踪文件 | `tests/game_server/TransportLifecycleTests.cpp` | 同名同路径 |
| `git diff --check` | exit 0 | exit 0 |
| 构建可行性 | **可用**（xmake v3.1.1 + MSVC 2022 x86 release） | **不可用**（见 §4） |

### 1.1 两树关系：D 是 F 的文件系统副本

证据一致指向：**D 由 F 通过 robocopy 复制而来，复制时点 2026-10-09 18:27**。

| 证据 | 内容 |
| --- | --- |
| 复制日志 | [_e1_copy.log](_e1_copy.log)：`=== E1 ISOLATED COPY ===` / `start=2026-10-09T18:27:47` / `robocopy exit=1` / `dest bytes=1320623938`（约 1.32 GB，与 F 的 `build\` 体积同量级） |
| `.git` 同源 | 两侧 `.git` 体积、`index` mtime、reflog 条目数与内容**完全一致** |
| HEAD 相同 | 两侧同为 `2a75bdd`，且 `branch.ab` 同为 `+8 -0` |
| 文件 mtime 断层 | D 的全部 T-1 相关文件 mtime 落在 2026-10-09 17:29–18:28，此后 D 再无写入 |

> 保留说明：`_e1_copy.log` **没有**在日志文本里署名 robocopy 的源/目标路径。上面的"F→D"方向是依据上表四项独立证据的**推断**，不是日志的直接署名。这一点按原样记录，不升格为已证实事实。

### 1.2 两树内容差异（未提交工作区）

**仅 F 有、D 没有的修改（3 个文件）**：

| 文件 | F 工作区 SHA-256 | F 字节 / 行 | D 侧值 | D 相对 HEAD |
| --- | --- | --- | --- | --- |
| `src/game_server/Appmain.cpp` | `407B6F9896A5F0354625B9D0724A3519BA4ACEDDFC36BA34CE879F79100BE7B1` | 481,281 / 9,546 | `69FDC488D0594A5DC65270ADBD3B7B8DA8A20AC753A19CB09173F8CED11C43CC`（= HEAD） | 未修改 |
| `src/game_server/FrameHook.cpp` | `1CA962D707F23DA40F60878DB5A8542601BA68398FE4EA226D0F957BE8008D8A` | 3,683 / 117 | `D7E398184935632D9B8CCF4B6CFB9694BBF9A826645DCB9F3ED1E6184B2DCF26`（= HEAD） | 未修改 |
| `src/game_server/FrameHook.hpp` | `6EDF4F9A21511468E99B779FE64BE5EA6B637F1E6AE24F91362013AA1EF5ACF5` | 1,213 / 27 | `EAD8A036BA73E7BB27316173F1993D8904BA5C6F2C41FE2312BF6607EBEA6B4F`（= HEAD） | 未修改 |

**两树都修改、但内容不同的文件（5 个 + 1 个未跟踪）**：

| 文件 | F SHA-256 | D SHA-256 | 关系 |
| --- | --- | --- | --- |
| `src/game_server/server_mp/sv_network_mp.cpp` | `AF93F7C8EEDE4E4C4417835F73D943544D906A7E1F3C5FBA9892CB82EEC58AA6` | `CA34DAF579A7CD92D29B903C2BB24B504FA80786A0034E16468062EE22E15324` | D 的 `start()` 被人工替换为 pre-T-1 体 |
| `src/game_server/server_mp/sv_network_mp.hpp` | `A5BBE54734A1F7DBB675F73CF1BAE4BC420C38B6E39A1D48B64EC67047F40915` | `3AF3104EA0FEF31ECC86204DA029DAB7BF268B7F92AC1FE67E928628C9F9B1B6` | 同左 |
| `src/game_server/win32/win_net.cpp` | `3A34D953D2A7A4830D99FF77988A2C791AAB36F968049906F06B832EABAA9A14` | `B4850F93FC07939E26F6FCE5D68C7264479413154073337D6EF1D18F0F8413EB` | F 多出日志辅助与 `boundAddress()` |
| `src/game_server/win32/win_net.hpp` | `8F0FF3189887660DEBB968C6CFF1E055CF065951E82E72F2E2ECF71451F5FBC1` | `9F4A50582D66706A7D8BEF308426E36949769098D02C691BBA07DF8358AB8851` | F 多出 `boundAddress()` 声明 |
| `xmake.lua` | `5C54E3585817E908AD32F7D2A36FD69A6130B8964591C25775A48A23605B6FE8` | **同一哈希** | **两树逐字节相同** |
| `tests/game_server/TransportLifecycleTests.cpp`（未跟踪） | `FA6A2760B73BBE52B377178C10BAA64390ADC43522A97D455070DE79DBE7DE94`（27,504 B / 639 行） | `00EBDB2C48065A3CEEC96C1A442774DCCC7BDD62634B57445D813230458D96CA`（10,662 B / 255 行） | F 是 D 的**严格超集**（F vs D 新增 349 行、删除 0 行） |

两侧 HEAD 索引 blob 完全一致（例如 `sv_network_mp.cpp` 索引 `6050530…`、`win_net.cpp` 索引 `8a1e576…`），因此上表差异**全部来自未提交的工作区修改**，不是提交历史分叉。

**完整差异归档**（本轮生成，未修改任何被比较文件）：

| 归档 | 路径 | 规模 |
| --- | --- | --- |
| F 的 `git diff` | [diff_F_git.patch](_batch10_evidence/diff_F_git.patch) | 25,009 B / 605 行 |
| D 的 `git diff` | [diff_D_git.patch](_batch10_evidence/diff_D_git.patch) | 9,616 B / 229 行 |
| F 与 D 的源码树差异 | [diff_F_vs_D_src.patch](_batch10_evidence/diff_F_vs_D_src.patch) | 22,495 B / 471 行（+213 / −33） |
| 两份 T-1 测试差异 | [diff_T1tests_F_vs_D.patch](_batch10_evidence/diff_T1tests_F_vs_D.patch) | 18,721 B / 424 行（+349 / −0） |
| F 侧 T-1 测试副本 | [T1_tests_F.cpp](_batch10_evidence/T1_tests_F.cpp) | 27,504 B |
| D 侧 T-1 测试副本 | [T1_tests_D.cpp](_batch10_evidence/T1_tests_D.cpp) | 10,662 B |

---

## 2. 冻结规则（本轮生效，直到显式解除）

| # | 规则 |
| --- | --- |
| **R1** | **F 是唯一活动工作基准**。新的源码修改、构建、测试只允许在 F 进行。 |
| **R2** | **D 冻结**。只读检视与哈希核验允许；构建、运行、写入、清理、`robocopy` 一律禁止。 |
| **R3** | **禁止双向同步**。任何形式的 F↔D 复制、覆盖、合并、`/MIR` 回写都不在本轮授权内。 |
| **R4** | **D 的"pre-T-1"标注不可信**。D 只回退了 `start()`；`stop()`/`close()`/`NET_IPSocket()` 已经是 T-1 形态。D **不是**干净的 pre-T-1 快照（详见 [T1_DIFF_REVIEW.md](T1_DIFF_REVIEW.md)）。 |
| **R5** | **D 的既有"回归通过"记录作废**。见 §4。 |
| **R6** | **构建必须显式命名目标**。`ol_deploy` 是 `set_default(true)`，且 `config/codol-game-dir.txt` 非空；裸 `xmake` / `xmake build` 会尝试部署。只允许 `xmake build <target>`。 |
| **R7** | **禁止破坏性 Git 操作**。本轮未执行 `reset` / `rebase` / `amend` / `clean` / `checkout` / `stash` / `commit` / `push`。 |
| **R8** | **禁止恢复 E1**。D 的 E-1 回归线**保持现状、不修复、不重跑**，只登记为证据无效。 |

---

## 3. 与 Batch 10 报告的基准不一致（已核实）

Batch 10 报告（[CODOL_SERVER_PROGRESS_20261009.md](CODOL_SERVER_PROGRESS_20261009.md)，第 4 行）自己声明的评估基准是：

> 工程副本 `_e1_regression\ol-mod-olfinal`（HEAD `2a75bdd`，`OLfinal-live`）

即 **报告实测的是 D，不是 F**。可用行数独立复核：

| 报告 §6.2 声称 | D 实测 | F 实测 | 结论 |
| --- | --- | --- | --- |
| `Appmain.cpp` 9,520 行 | **9,519 行** | **9,546 行** | 报告写的是 D |
| `FrameHook.cpp` 75 行 | **74 行** | **117 行** | 报告写的是 D |
| `EngineBindings.cpp` 18,029 行 | 18,028 行 | 18,028 行 | 两树相同，无区分度 |

**因此**：报告的 §4（宿主身份）与 §6.2（插件专属文件清单）描述的是 D 的形态；报告完全**没有**覆盖 F 独有的 `Appmain.cpp` / `FrameHook.cpp` / `FrameHook.hpp` 三处修改。这正是任务 §七 预警的"工作树状态与报告不一致"。

**处置**：不改写报告；在本轮交付中并列记录两树实测值，并以 F 为准继续。

---

## 4. D 的构建环境不可用 / E-1 回归从未成立

工作区日志记录了 D 侧共 **7 次**构建尝试（`_e1_regression.log` 与 `_e1_regression2..8.log`），结果：

| 日志 | 关键行 | 结果 |
| --- | --- | --- |
| [_e1_regression.log](_e1_regression.log) | `BUILD exit=-1` 后仍执行 `=== RUN (expect FAIL) ===` → `checks=49 failures=0` | **构建失败，却运行了旧二进制** |
| [_e1_regression2.log](_e1_regression2.log) | `removed stale copied exe` / `'f' is not a valid target name` | 失败 |
| [_e1_regression3.log](_e1_regression3.log) | `'ol_transport_lifecycle_tests' is not a valid target name for this project` | 失败 |
| [_e1_regression4.log](_e1_regression4.log) | 清空副本 build 缓存后仍同名失败 | 失败 |
| [_e1_regression5.log](_e1_regression5.log) | 显式 workdir 仍同名失败 | 失败 |
| [_e1_regression6.log](_e1_regression6.log) | `fatal error C1083: 无法打开包括文件: "openssl/crypto.h"` | 失败 |
| [_e1_regression7.log](_e1_regression7.log) | 回灌 F 的 build 状态后仍 C1083 | 失败 |
| [_e1_regression8.log](_e1_regression8.log) | `xmake -P` 配置成功后仍 C1083 | 失败 |

**结论（按证据，不按措辞）**：

1. D 侧从未成功构建出 `ol_transport_lifecycle_tests.exe`。本轮复核确认 D 的 `build\` 下**当前不存在任何 `ol_transport_lifecycle_tests.exe`**。
2. [_e1_regression.log](_e1_regression.log) 的 `checks=49 failures=0` **不是** pre-T-1 回归结果。它前面紧跟着 `BUILD exit=-1`；而 [_e1_regression2.log](_e1_regression2.log) 明确记录"移除了被复制过来的旧 exe"，[_e1_copy.log](_e1_copy.log) 记录了 F→D 的 robocopy。因此那次运行执行的是**从 F 复制来的 T-1 二进制**，跑出 0 失败是必然的。
3. 由此，**"E-1 回归证明新测试能抓住旧缺陷"这一证据从未真正产生**。D 的 pre-T-1 `start()` 与 D 自己的测试在静态上必然冲突（见 [T1_DIFF_REVIEW.md](T1_DIFF_REVIEW.md) §4.3），但**没有任何一次真实执行**验证过这一点。
4. D 侧构建失败的根因（`openssl/crypto.h` 不可达）**本轮未定位**，且按 R2 未再做任何 D 侧构建尝试。

---

## 5. 本轮"未发生"的机械核对

| 项 | 核对方式 | 结果 |
| --- | --- | --- |
| F↔D 复制/覆盖/合并/清理 | 全轮操作清单 | **0 次** |
| 工作树文件写入 | 两侧 `git status --porcelain` 前后一致 | F：8 M + 1 ??；D：5 M + 1 ??（与轮次开始时逐行相同） |
| `git diff --check` | 两树 | exit 0 |
| HEAD 变动 | 两树 `git rev-parse HEAD` | 未变（`2a75bdd`） |
| 分支变动 | 两树 | 未变（`OLfinal-live`） |
| 破坏性 Git 操作 | 全轮命令清单 | **0 次** |
| `config/codol-game-dir.txt` | 两树 SHA-256 | `9AEEFD107F677EDD4F2A85DA7E38FF796718C7BF64F60E1B7D1CD6F1092019AA`，**未修改** |
| `ol_deploy` 触发 | `F:\...\build\stage` mtime | 仍为 2026-10-09 17:01:07，**未触发** |
| 客户端启动 / 注入 / 内存读取 | 全轮命令清单 | **0 次** |
| Git 提交 / 推送 | 全轮命令清单 | **0 次** |

### 5.1 本轮唯一的写入副作用（全部在授权范围内）

| 位置 | 内容 | 说明 |
| --- | --- | --- |
| `D:\BaiduNetdiskDownload\使命召唤OL\_batch10_evidence\` | 5 个归档文件（2 份 patch、1 份对比 patch、2 份测试副本）+ 2 份新日志 | 新建目录，工作区侧 |
| `D:\...\使命召唤OL\`（工作区根） | 本轮的 5 份交付文档 | 新建文件 |
| `F:\...\ol-mod-olfinal\build\` | `ol_transport_lifecycle_tests.exe` 被强制重建（`.gitignore` 已忽略 `/build/`），以及该 exe 目录下的 `Ayria\Logs\CodolGameServer.log` | **仅构建输出**，未触碰任何受版本控制文件 |
| `F:\...\ol-mod-olfinal\.xmake\` | `xmake f` 刷新了项目配置缓存（`.gitignore` 已忽略 `/.xmake/`） | 同上 |

> F 的工作区源码**一个字节都没有被改动**：轮次结束时 F 的 9 个待处理路径哈希与轮次开始时逐项相同（见 [FILE_OWNERSHIP_MANIFEST.md](FILE_OWNERSHIP_MANIFEST.md)）。

---

## 6. 基准切换方案（供将来执行，本轮**未执行**）

若将来决定把"活动基准"从工作区会话层面正式指向 F，建议按顺序执行：

1. **确认 F 可用**：`xmake --version`、`git -C F status --porcelain`、`git -C F rev-parse HEAD` 三项与 [FILE_OWNERSHIP_MANIFEST.md](FILE_OWNERSHIP_MANIFEST.md) 记录一致。
2. **冻结 D**：把 D 的 `build\` 与 `.xmake\` 只读化（`attrib +R`）或整体移出构建路径，防止误构建。
3. **显式化 F 路径**：所有构建/测试脚本改为显式 `--project=F:\桌面\ol\ol-mod-olfinal` 或 `workdir=F`，不依赖当前目录。
4. **切换后复验**：在 F 重新执行 `xmake f` + `xmake build ol_transport_lifecycle_tests` + 运行，并把日志写入 F 侧而非工作区侧。
5. **登记**：把切换前后的 `git status`、`HEAD`、产物哈希写入 [FILE_OWNERSHIP_MANIFEST.md](FILE_OWNERSHIP_MANIFEST.md)。

**在第 1–5 步被显式授权并执行之前，不得声称基准已切换。**

---

## 7. 关联交付

- [T1_DIFF_REVIEW.md](T1_DIFF_REVIEW.md) — 两份 T-1 实现与测试的逐项差异和采用版本
- [T1_ACCEPTANCE_REPORT.md](T1_ACCEPTANCE_REPORT.md) — T-1 覆盖、实际执行结果、失败与未验证项
- [ARTIFACT_BLOCKERS.md](ARTIFACT_BLOCKERS.md) — 目标客户端制品缺口与解除门禁所需证据
- [FILE_OWNERSHIP_MANIFEST.md](FILE_OWNERSHIP_MANIFEST.md) — 文件归属、哈希、构建时间、产物与日志路径
- [_batch10_evidence\](_batch10_evidence/) — 本轮全部原始归档与日志
