# COMBAT_P1_B1_SAFETY_REVIEW — 只读采样代码的边界与副作用审查

**任务**：COMBAT-P1-B1（仅授权 B-1）
**日期**：2026-10-11
**被审查对象**：F `src/game_server/EngineBindings.cpp` 的 +297 行纯追加（见 `COMBAT_P1_B1_SOURCE_DIFF.md`）
**审查性质**：**静态审查**。**未编译、未构建、未部署、未运行**。凡未能由编译器确认的项，一律列入 §5「尚未验证的编译风险」。

---

## 1. 授权边界逐条核对（步骤 2 的 8 条）

| # | 约束 | 状态 | 证据 |
|---|---|---|---|
| 1 | 诊断开关**默认关闭** | **满足** | `SampleHostImageIdentity` 首段即 `GetEnvironmentVariableA("OLMOD_COMBAT_P0_SAMPLE", …)`，仅当**恰好**返回长度 1 且字符为 `'1'` 时才继续；否则立即 `return` |
| 2 | 关闭时保持现有绑定行为**不变** | **满足（静态论证）** | 关闭路径只多一次「读环境变量」调用，无任何内存读/写、无日志、无分支依赖；`bind()` 的判定式、日志文本、守卫顺序、控制流均未出现在 diff 中（**+297 / −0**） |
| 3 | 采样结果**不参与门禁判定** | **满足** | `SampleHostImageIdentity` 返回 `void`；调用点未使用任何返回值；调用点位于判定之前且其后代码逐字未改 |
| 4 | 不修改 RVA / ABI / 既有守卫 / 协议常量 / 网络逻辑 | **满足** | 新增行中「触碰既有守卫模式 `std::equal(…, module_ + …)`」计数 = **0**；未新增/修改任何常量定义；未触碰网络代码 |
| 5 | **不新增导出** | **满足** | 新增行中 `dllexport` 计数 = **0**；采样函数位于**匿名命名空间**（内部链接） |
| 6 | 不调用 Frida，不附加/注入/启动/终止游戏进程 | **满足** | 本轮未执行任何进程操作；新增代码不含任何进程/注入 API |
| 7 | 不构建、不部署、不调用 `ol_deploy` | **满足** | 本轮未执行构建或部署 |
| 8 | 不覆盖既有修改、历史证据或大厅冻结基线 | **满足** | diff 为纯追加（0 删除）；未触碰 D、`GOLDEN-LOBBY-001`、`REF_LOBBY_KIT`、既有日志 |

---

## 2. 只读性论证

新增代码**全部**的内存访问都是**读**，且被三层保护包围（§3）：

| 可能的写操作 | 新增行中的计数 |
|---|---|
| `VirtualProtect`（改页保护） | **0** |
| `WriteProcessMemory` | **0** |
| 对 `module_ + …` 的赋值/`memcpy` 写入目标 | **0**（方向恒为「从映像读到栈上 POD 缓冲」） |
| `bindingCommitted_.store(true)` | **0** |
| 调用任何被守卫函数（通过绑定指针） | **0** |
| `SetEnvironmentVariable` / 任何环境变更 | **0** |

采样只读两类位置：
1. **PE 元数据**：「module+0x3C」（e_lfanew）、「module+e_lfanew」（IMAGE_NT_HEADERS）。
2. **两个指定 RVA 的字节**：「module+0x000FEA20」5 字节、「module+0x0008371A」8 字节。

不读取模块的节数据、不遍历导出/导入、不读其他模块、不读其他进程。

---

## 3. 异常与失败处理

| 层 | 机制 | 失败标志（写入日志） |
|---|---|---|
| 显式边界 | `rva > sizeOfImage \|\| size > sizeOfImage - rva` | `stage=out_of_sizeofimage` |
| 页可读性 | `VirtualQuery` 要求 `State == MEM_COMMIT`、保护位含可读掩码、整段在同一 region 内 | `stage=not_readable` |
| SEH | `__try { 逐字节复制 } __except (EXCEPTION_EXECUTE_HANDLER) { return false; }` | `stage=read_faulted` |
| 其它早退 | `module == nullptr` / e_lfanew 不可读 / e_lfanew 越界 / NT 头不可读 | `module_missing` / `e_lfanew_unreadable` / `e_lfanew_out_of_range` / `nt_headers_unreadable` |

**任何一条失败路径都不会改变 `bind()` 的控制流**：采样函数在所有这些情况下都只是写一行日志并返回 `void`。
**C2712 规避**：含 `__try` 的 `ReadHostBytesSafely` 内**没有任何带析构函数的局部对象**（目标缓冲由调用方以 POD 提供）；所有 `std::string` 构造都在 `__try` **之外**。

**先例证据（同一 TU 内已存在相同 API）**：`__try` 55 处、`VirtualQuery` 4 处、`GetEnvironmentVariableA` 11 处、`snprintf` 79 处均为**改动前既有** ⇒ 这些 API 在本工程配置下已被编译通过。

---

## 4. 潜在副作用（穷举）

| # | 副作用 | 触发条件 | 严重度 | 说明 |
|---|---|---|---|---|
| E-1 | 多写 4 行日志（identity / pe / 两个 rva） | **仅当开关 = "1"** | 极低 | 走既有 `RuntimeLog::Channel::GameServer`；每次 `bind()` 至多一次 |
| E-2 | 一次 `GetEnvironmentVariableA` 调用 | 每次 `bind()`（含关闭时） | 可忽略 | 纯读，无锁竞争、无分配 |
| E-3 | 启动期日志 I/O 开销 | 仅当开关 = "1" | 极低 | 4 行；历史 `LOGSTALL` 已显示单行落盘约数百微秒 |
| E-4 | 栈占用 | 仅当开关 = "1" | 低 | `imagePath[520]` + 小缓冲 + 若干 `std::string`，总量 < 4 KB（默认 1 MB 栈） |
| E-5 | SEH 处理器安装 | 仅在实际读取时 | 无 | 局部 `__try`，非向量化异常处理器；不改变进程全局异常行为 |
| E-6 | 影响绑定结果 | **不可能** | — | 返回 void、调用点忽略、其后代码未改 |
| E-7 | 影响导出/ABI | **不可能** | — | 匿名命名空间；无新增导出 |
| E-8 | 影响其他 TU 行为 | **不可能** | — | 全部新符号为内部链接；无头文件改动 |

**"关闭即等价"的强度**：除 E-2 外，关闭路径在**语义**上与改动前完全相同；E-2 是无副作用的查询。**但**该等价性目前是**静态论证**，尚未经编译器/运行时验证（见 §5、§6）。

---

## 5. 尚未验证的编译风险（**明确列出，不得声称已编译通过**）

| # | 风险 | 评估 | 缓解/证据 | 现状 |
|---|---|---|---|---|
| CR-1 | `EngineBindings::ExpectedTimestamp` / `ExpectedImageSize` 从匿名命名空间的自由函数访问，若为 `private` 则不编译 | **已静态排除** | `EngineBindings.hpp:438` 之上最近的可访问性说明符为 **`public:`（第 296 行）** | 静态确认；**未经编译器确认** |
| CR-2 | 含 `__try` 的函数触发 **C2712**（需要对象展开） | 低 | `ReadHostBytesSafely` 内无带析构函数的对象；格式化在 `__try` 外 | **未经编译器确认** |
| CR-3 | `__try/__except` 与 `/EHsc` 组合告警（C4530） | 低 | 同 TU 既有 55 处 `__try` 已编译通过 | **未经编译器确认** |
| CR-4 | `GetEnvironmentVariableA` / `GetModuleFileNameA` / `GetCurrentProcessId` / `VirtualQuery` / `MEMORY_BASIC_INFORMATION` / `PAGE_*` / `MEM_COMMIT` 在 `WIN32_LEAN_AND_MEAN` 下可见性 | 低 | 同 TU 既有使用（11 / 4 处） | **未经编译器确认** |
| CR-5 | `std::snprintf` 需 `<cstdio>` | 低 | 文件第 20 行已 `#include <cstdio>`；同 TU 既有 79 处 `snprintf` | **未经编译器确认** |
| CR-6 | `IMAGE_NT_HEADERS` 在 x86 下为 32 位变体 | 低 | `bind()` 同 TU 已使用 | **未经编译器确认** |
| CR-7 | `std::to_string(unsigned long long)` 重载 | 低 | 标准库保证；已显式转换 | **未经编译器确认** |
| CR-8 | 名称冲突（新增 12 个标识符） | **已静态排除** | 全文件出现次数与「定义 + 预期引用」完全一致 | 静态确认 |
| CR-9 | 括号/命名空间不平衡 | **已静态排除** | 新增行 `{`/`}` = 34/34，`(`/`)` = 133/133；1 个匿名命名空间块 | 静态确认 |
| CR-10 | `set_warnings("all","extra")` 造成告警 | 低 | **未启用 `/WX`**（`xmake.lua` 无 `WX`/`werror`）⇒ 告警不致构建失败 | 静态确认 |
| CR-11 | `ComFramePrefix` 可见性 | **已静态排除** | 其最近外层为 `EngineBindings.cpp:37` 的 `namespace {`，位于 `CodolGameServer`（第 35 行）内；新增块同层 | 静态确认 |

> **结论**：CR-1、CR-8、CR-9、CR-10、CR-11 已由**静态证据**排除；**CR-2..CR-7 必须由一次编译确认**，本任务未授权构建，因此**当前状态为「未验证」**。

---

## 6. 仍未验证的运行时事实（不得写成已证实）

- RVA `0x0FEA20` 的**运行时**字节是否为 `55 8B EC 56 57`：**未验证**。
- RVA `0x8371A` 的**运行时**字节是否为 `83 7C 24 08 01 0F 94 C0`：**未验证**。
- 宿主运行时 `SizeOfImage` 是 `0x0E5D6000` 还是 `0x0E659000`：**未验证**。
- 门禁 3 个静默早退点中**具体哪一项**失败：**仍未判定**。

上述四项均为**待采样核验的静态期望值**，本次实现**只是提供了观测手段**，**没有产生任何运行时结论**。

---

## 7. 本审查未覆盖的范围

- 未做编译器校验（未授权构建）。
- 未做任何运行时验证（未授权启动）。
- 未审查 B-2/B-3/B-4 的操作安全性（仅 B-1 在本轮授权内）。
- 未修改、未评估任何与门禁判定相关的改动（本实现刻意不含此类改动）。

---

## 8. 基线不变性核对（本轮）

| 项 | 值 |
|---|---|
| F `git status --porcelain` | 实施前 17 → 实施后 **18**（新增 `M src/game_server/EngineBindings.cpp`） |
| D `git status --porcelain` | **6**（未变） |
| D 的 `EngineBindings.cpp` | **未修改**（工作区 blob 仍 == HEAD blob） |
| `GOLDEN-LOBBY-001/REF_LOBBY_KIT` | **未写入**（141 文件，最新 mtime 仍为 2026-10-07 22:10:52） |
| 既有日志 / 历史证据 | **未覆盖** |
| F 的其余 16 项工作区改动 | **未触碰**（diff 仅涉及 `EngineBindings.cpp`） |
