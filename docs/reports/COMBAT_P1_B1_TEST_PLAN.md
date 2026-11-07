# COMBAT_P1_B1_TEST_PLAN — 只读采样代码的验证计划

**任务**：COMBAT-P1-B1（仅授权 B-1）
**日期**：2026-10-11
**性质**：**计划。本轮不执行任何编译、构建、部署或运行。**
**配套**：`COMBAT_P1_B1_SOURCE_DIFF.md`、`COMBAT_P1_B1_SAFETY_REVIEW.md`、`COMBAT_P1_B1_SHA256_MANIFEST.txt`

> **纪律**：RVA `0x0FEA20` / `0x8371A` 的静态期望字节**只是待核验的静态期望值**，本计划中任何一条通过都**不**等于已取得运行时事实。

---

## 1. 分层验证结构

| 层 | 内容 | 需要的授权 | 本轮状态 |
|---|---|---|---|
| **T-A. 静态/结构验证** | 不编译即可做的差异与结构核对 | 无（只读） | **已执行**（见 §2） |
| **T-B. 编译验证** | `xmake build ol_game_server`（显式命名目标） | **B-2** | 未执行 |
| **T-C. 落盘验证** | 把新插件放入沙箱（不经 `ol_deploy`） | **B-3** | 未执行 |
| **T-D. 运行时验证** | 启动 1 个沙箱客户端并只读日志 | **B-4** | 未执行 |
| **T-E. 默认关闭负对照** | 同一客户端、开关关闭 | **B-5**（可选） | 未执行 |

---

## 2. T-A 静态/结构验证（**本轮已执行**）

| ID | 检查 | 结果 | 判据 |
|---|---|---|---|
| T-A1 | diff 为纯追加 | **PASS** | `addedLines=297, removedLines=0` |
| T-A2 | 括号平衡 | **PASS** | `{`=34/`}`=34；`(`=133/`)`=133 |
| T-A3 | 匿名命名空间数量 | **PASS** | 1 个（与既有用法一致） |
| T-A4 | 无新增导出 | **PASS** | 新增行 `dllexport` = 0 |
| T-A5 | 未触碰既有守卫 | **PASS** | 新增行中 `std::equal(..., module_ + …)` = 0 |
| T-A6 | 无内存写/改页/发布绑定 | **PASS** | `VirtualProtect` / `WriteProcessMemory` / `bindingCommitted_.store(true)` = 0 |
| T-A7 | 符号唯一性（12 个新标识符） | **PASS** | 每个标识符的出现次数 == 定义 + 预期引用 |
| T-A8 | `ComFramePrefix` 可见性 | **PASS（静态）** | 最近外层为 `EngineBindings.cpp:37` 匿名命名空间（位于 `CodolGameServer` 内），新增块同层 |
| T-A9 | 门禁常量可访问性 | **PASS（静态）** | `EngineBindings.hpp:438` 之上最近说明符为 `public:`（第 296 行） |
| T-A10 | 开关默认关闭的代码路径 | **PASS（静态）** | 首段即环境变量检查；不等于 `"1"` 时立即 `return` |
| T-A11 | 调用点位于门禁之前 | **PASS** | 调用在第 3950 行，紧随 `module_` 赋值；`if (!module_)` 在其后（第 3952 行） |
| T-A12 | 调用点忽略返回值 | **PASS** | 函数返回 `void` |

---

## 3. T-B 编译验证（需 **B-2** 授权；本轮未执行）

| ID | 步骤 | 期望 | 失败处理 |
|---|---|---|---|
| T-B1 | `git -C F status --porcelain` 记录基线（应为 18 条） | 与记录一致 | 不一致则停止 |
| T-B2 | `git -C F hash-object src/game_server/EngineBindings.cpp` | `5894e06bb5d1bf6cfb7896600b17ef8ea53b48b6` | 不一致则说明文件被改动，停止 |
| T-B3 | **显式**运行 `xmake build ol_game_server`（**不得**裸跑 `xmake`） | 编译+链接成功，退出码 0 | 出现 **C2712 / C4530 / C3861 / C2039** 等错误 ⇒ 记录全文，**停止**，不得自行扩大改动 |
| T-B4 | 记录告警清单 | 允许新增告警；**不得**新增错误 | 若出现 `WX` 级失败（本工程未启用 `/WX`，预期不会），停止 |
| T-B5 | 记录产物 `build\bin\release\CodolGameServer.Localnet32` 的 size + SHA-256 + PE `TimeDateStamp` | 新哈希 ≠ `DBA7273A…` 且 ≠ `6D493B82…` | — |
| T-B6 | 确认导出数 | **仍为 53**（约束 5） | 若变化 ⇒ 停止（说明引入了导出） |
| T-B7 | 「开关关闭等价性」的**静态**复核 | 反汇编比对：`bind()` 在**未设**环境变量时的行为与改动前一致（除一次环境变量查询） | 若发现判定路径变化 ⇒ 停止 |

> **注**：T-B7 的"逐位等价"严格证明需要二进制级比对（同源码、同工具链、加/不加该代码），在 LTO 下不可行；因此 T-B7 只能作为**行为级**复核，并须在报告中如实标注其强度上限。

---

## 4. T-C 落盘验证（需 **B-3** 授权；本轮未执行）

| ID | 步骤 | 期望 |
|---|---|---|
| T-C1 | 备份沙箱现有插件与 6 个日志（改名，不删除） | 备份存在且有哈希 |
| T-C2 | 用替代流程（**非** `ol_deploy`）把 T-B5 的新插件放入 `<E>\Ayria\Plugins\` | 落盘后 SHA-256 == T-B5 |
| T-C3 | 记录部署清单是否需要同步 | `ol-mod-runtime-manifest.json` **不修改**（避免覆盖历史证据） |
| T-C4 | 核对客户端 exe 未变 | SHA-256 == `36997674…B537` |

---

## 5. T-D 运行时验证（需 **B-4** 授权；本轮未执行）

**每次运行只回答一个问题。**

| ID | 开关 | 目的 | 期望日志（`Ayria\Logs\CodolGameServer.log`） | 判据 |
|---|---|---|---|---|
| T-D1 | `OLMOD_COMBAT_P0_SAMPLE=1` | 取得宿主运行时映像事实 | 出现 `image-sample v=1 sampler=combat-p1-b1 pid=… path="…codoMP_client_shipRetail.exe"` | 路径匹配沙箱客户端 |
| T-D2 | 同上 | 取得 PE 事实 | 出现 `pe signature=0x00004550 machine=0x014C sections=… timestamp=0x…… sizeofimage=0x…… gate_expected_sizeofimage=0x0E5D6000 gate_sizeofimage_equal=0/1` | 字段齐全 |
| T-D3 | 同上 | 取得 RVA `0x0FEA20` 字节 | `rva=0x000FEA20 len=5 expected=55 8B EC 56 57 effective=… match=0/1` | 字段齐全 |
| T-D4 | 同上 | 取得 RVA `0x8371A` 字节 | `rva=0x0008371A len=8 expected=83 7C 24 08 01 0F 94 C0 effective=… match=0/1` | 字段齐全 |
| T-D5 | 同上 | 采样是否走了异常分支 | 不得出现 `stage=read_faulted` | 若出现 ⇒ 记录并停止 |
| T-D6 | 同上 | 门禁与守卫的既有行为是否保留 | 仍出现 `engine binding failed`（若门禁仍失败）或 `game server frame hook installed`（若通过） | 二者之一，不得两缺 |
| T-D7 | **`OLMOD_COMBAT_P0_SAMPLE` 未设** | **负对照**：默认路径 | 日志中**不得出现**任何 `image-sample` 行；其余行与 T-D1 的对应运行**逐行一致**（除时间戳） | 出现 `image-sample` ⇒ FAIL |
| T-D8 | — | 证据固化 | 复制日志为只读证据副本并计算 SHA-256 | 四元组齐全（客户端/插件/证据副本/时间） |

**停止条件（任一命中即停止，不进入下一阶段）**
- T-D1..T-D4 任一字段缺失或格式不符；
- 出现 `stage=out_of_sizeofimage` / `not_readable` / `read_faulted`；
- T-D7 出现 `image-sample` 行（说明默认未关闭 ⇒ 违约束 1/2）；
- 客户端进程数与身份不符；
- 若"继续观测"必须以放宽门禁为前提。

---

## 6. 本计划**无法**验证的内容（必须如实标注）

| # | 内容 | 为什么 |
|---|---|---|
| N-1 | 部署 DLL 中 `bind()` 的机器码 == 当前源码编译结果 | LTO 已启用、无 PDB、无 CodeView、无部署构建的 map（见 `COMBAT_P1_ARTIFACT_CONSISTENCY.md` V5） |
| N-2 | "关闭时逐位等价"的**二进制**证明 | 同上；只能做行为级复核（T-B7） |
| N-3 | 75 条既有守卫在真实运行时映像上是否成立 | 它们位于门禁**之后**；本实现**刻意不放宽门禁**，故仍不可达（这正是"不用放宽换取观测"的设计后果） |
| N-4 | `0x0FEA20` / `0x8371A` 的静态期望值是否为真值 | 恰恰是 T-D3/T-D4 要回答的；在取得日志前**仍是静态期望值** |
| N-5 | 门禁失败的具体子条件 | 由 T-D2 的 `gate_timestamp_equal` / `gate_sizeofimage_equal` 在**开关开启时**回答 |

---

## 7. 退出判据（B-1 阶段）

- **T-A 全部 PASS**：本轮已满足。
- **B-1 阶段完成的定义** = 代码差异存在、默认关闭路径成立、结构审查通过、计划齐备、哈希复核通过。
- **下一步**（需另行授权）：T-B（编译）→ T-C（落盘）→ T-D（单客户端运行）→ 按 `COMBAT_P1_DECISION_MATRIX.json` 的 A/B/C/D 判定。

**本轮到此停止，不构建、不部署、不启动客户端。**
