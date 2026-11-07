# COMBAT_P1_RUNTIME_SAMPLING_PLAN — 运行时只读采样方案（仅设计，不执行）

**任务**：COMBAT-P1（阶段二：方案设计）
**日期**：2026-10-11
**性质**：**方案。本任务不执行。** 未启动/附加/注入任何进程，未读任何进程内存，未构建，未部署。
**配套**：`COMBAT_P1_ARTIFACT_CONSISTENCY.md`、`COMBAT_P1_DECISION_MATRIX.json`、`COMBAT_P1_SHA256_MANIFEST.txt`。

> **核心判据**：本方案的存在目的是**判定 α/β/γ**（见第 8 节与判定矩阵），**不是**"让门禁变绿"。
> **默认不放宽 `SizeOfImage`**、**不删除/绕过任何门禁**、**不修改 RVA/ABI/协议常量**。

---

## 0. 先评估"不改变目标进程状态的现有证据来源"（任务要求）

| # | 候选来源 | 能否取得运行时映像事实 | 判定 |
|---|---|---|---|
| S-1 | **磁盘上的客户端 PE 头**（静态读取） | 只给出**加壳文件**的头（`SizeOfImage=0x0E659000`）。TenProtect 可在内存中解包并恢复原始 PE 头，故磁盘值**不能**代表运行时映像（O-4）。 | **不足** |
| S-2 | **现有日志**（sandbox `Ayria\Logs\*`） | 三次运行只有 `engine binding failed` + `LOGSTALL`；**无**任何 PE 头 / RVA 字节行（COMBAT-P0 §1.5 已核实）。 | **不足** |
| S-3 | **现有导出**（`CODOL_GameServerGet*Status` 族） | 无任何"宿主映像身份"字段。且要调用导出，必须有**进程内调用者**或跨进程调用 —— 后者正是被排除的手段。 | **不可用** |
| S-4 | **DedicatedControl 28961 网络通道** | 该通道是**网络**连接，理论上可在不读进程内存的情况下把映像事实传出来。但：① 现有消息枚举（`DedicatedControl.hpp:23-82`）**没有**该类消息；② **循环依赖** —— 28961 由 `ensureDedicatedControlServer()` 在 `onServerFrame` 中启动，而 `onServerFrame` 只在 `bind()` 成功、帧钩子安装后才会被调用 ⇒ 门禁失败时该通道**永不存在**。 | **不可用（循环依赖）** |
| S-5 | **外部只读工具 / 操作系统接口** | 读取**另一个进程**的模块头需调试器/附加/跨进程读取，属本任务明确排除项。 | **不可用（排除）** |
| S-6 | **插件自身只读自省**（`GetModuleHandleW(nullptr)` + PE 头 + 指定 RVA 字节） | **可以**。插件在自己的进程内、在自己的模块上读自己的映像，不改任何状态。缺点：需要一处**纯只读**代码改动并重新构建/落盘/启动一次。 | **唯一可行** |

**结论（明确说明）**：在不改变目标进程状态的前提下，**现有证据来源无法取得运行时映像事实**。唯一可行路线是 **S-6 插件自身只读自省**，它需要四项分别授权的前置操作（改只读代码、构建、落盘、启动一次）。
**不得**以 Frida 附加、进程注入、跨进程内存读取或修改运行映像作为替代方案；本任务不执行任何替代实验。

---

## 1. 目标证据清单（六项，逐项给出格式与判据）

| # | 目标证据 | 采集来源 | 判定用格式 |
|---|---|---|---|
| E1 | 宿主模块 `TimeDateStamp` | 自省 PE 头 `IMAGE_NT_HEADERS.FileHeader.TimeDateStamp` | `timestamp=0x6096930A` 或实测值 |
| E2 | 宿主模块 `SizeOfImage` | 自省 PE 头 `OptionalHeader.SizeOfImage` | `sizeofimage=0x0E5D6000` / `0x0E659000` / 其他 |
| E3 | RVA `0x0FEA20` 处的字节（5 B） | 自省模块映像 | `effective=55 8B EC 56 57`（静态期望值，**待核验**） |
| E4 | RVA `0x8371A` 处的字节（8 B） | 自省模块映像 | `effective=83 7C 24 08 01 0F 94 C0`（静态期望值，**待核验**） |
| E5 | 采样对象身份 | 自省 `GetModuleFileNameW(nullptr)` + 外部独立核验 | `path=…\codoMP_client_shipRetail.exe` + 外部文件 SHA-256 |
| E6 | 采样时间 / 工具版本 / 证据文件 SHA-256 | 日志时间戳 + `sampler_version` + 外部哈希 | 三个字段齐全 |

> **纪律**：E3/E4 的静态期望值来自源码（`EngineBindings.cpp:755-757` 与 `ClientProcessPatches.cpp:207-211`），**只是待核验的静态期望值**，**不得**预先认定为运行时真值。日志中必须同时有 `effective=` 与 `expected=` 两个字段，且 `match=0/1` 由**比较**得出，不得预置。

---

## 2. 采样点与"避免门禁失败导致不可达"的设计

**问题**：门禁一旦失败，`bind()` 在 `:3666` 就返回，其后的 75 条守卫全部不可达；而门禁本身**不写日志**（COMBAT-P0 §1.1）。

**设计原则**：采样**放在门禁判定之前**，且**不参与任何判定**。

```
bool EngineBindings::bind()
{
    bindingCommitted_.store(false, std::memory_order_release);
    module_ = reinterpret_cast<std::uint8_t *>(GetModuleHandleW(nullptr));

    // [新增] 纯只读采样：位于一切判定之前，无返回值、无分支依赖、不修改任何状态
    sampleHostImageIdentity(module_);      // 受 OLMOD_COMBAT_P0_SAMPLE=1 显式开关控制

    if (!module_) return false;            // 原有逻辑逐字不变
    ...                                    // 以下全部保持原样
}
```

| 设计要点 | 说明 |
|---|---|
| **可达性** | 位于 `module_` 赋值之后、任何 `return false` 之前 ⇒ 无论门禁通过与否都执行。不依赖 `bind()` 的结果。 |
| **幂等** | 每次 `bind()` 调用至多写一行/两行；`bind()` 由 `initialize()` 的 `StartupMutex`+`Installed` 保护，正常只执行一次。 |
| **默认行为不变** | 由**显式环境变量**控制（建议 `OLMOD_COMBAT_P0_SAMPLE=1`）。**未设置时不得输出任何新行、不得改变任何判定**。 |
| **不放宽门禁** | 采样**只记录**，**不**参与 `if` 判断，**不**提供任何"跳过尺寸检查"的路径。 |
| **不破坏既有日志** | 追加新行，不改 `Appmain.cpp:7135` 的 `engine binding failed` 文本，不改 `FrameHook.cpp` 的 `reason=` 文案。 |
| **不改 ABI** | 不新增导出、不改既有导出签名。 |

---

## 3. 采样对象身份确认（双证）

**外部证据（操作者只读执行）**
1. 运行前：确认目标文件为 `<GAME ROOT>\codoMP_client_shipRetail.exe`，记录**大小 7,841,344** 与 **SHA-256**（期望 `36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537`）。
2. 运行中/运行后：确认**恰好一个**匹配进程（按可执行文件路径过滤，不只按进程名）；记录 PID。
3. 记录该 PID 与日志中 `pid=` 字段是否一致。
4. 记录插件文件 `Ayria\Plugins\CodolGameServer.Localnet32` 的 SHA-256（用于说明"这次跑的是哪个插件"）。

**内部证据（插件自省）**
5. `GetModuleFileNameW(nullptr)` 的完整路径；期望以 `codoMP_client_shipRetail.exe` 结尾且位于沙箱根。
6. 模块基址非零；PE 签名 `0x00004550`；`Machine=0x014C`。
7. `sampler_version` 与插件 SHA-256 在报告中一一对应。

**身份判据（全部满足才算"对象身份符合"）**：文件名匹配 ∧ 文件大小/SHA-256 匹配 ∧ 只有一个候选进程 ∧ PID 一致 ∧ 模块基址非零 ∧ `Machine` 为 x86。

> **不得**以"进程名相同"单独作为身份证明（COMBAT-P0 已登记同类教训：文件名 ≠ 构建）。

---

## 4. 只读性与安全性约束

| 约束 | 做法 |
|---|---|
| 只读 PE 元数据 | 读 `IMAGE_DOS_HEADER` / `IMAGE_NT_HEADERS`；不写、不改页保护、不调用任何被守卫函数 |
| 边界检查 | 先确认 `e_lfanew` 合法（`< 0x1000` 且 `+ sizeof(NT) <= SizeOfImage`），再读 NT 头 |
| RVA 越界 | 逐项断言 `rva + len <= nt->OptionalHeader.SizeOfImage`；否则记 `skip=out_of_range` 并**不读** |
| 页可读性 | 用 `VirtualQuery(module_ + rva, …, sizeof(MEMORY_BASIC_INFORMATION))` 确认区域为 `MEM_COMMIT` 且 `PAGE_READONLY`/`PAGE_READWRITE`/`PAGE_EXECUTE_READ`/`PAGE_EXECUTE_READWRITE`（即可读）；不可读则记 `skip=not_readable` |
| 异常保护 | 采样体用 `__try/__except`（或等价 SEH）包裹；异常只记 `sample_error=0x……` 并返回，**绝不**影响 `bind()` |
| 不改状态 | 不调用 `VirtualProtect`、不写内存、不创建 hook、不发布指针、不改 `bindingCommitted_` |
| 不读他人内存 | 只读**自身模块**（`GetModuleHandleW(nullptr)`）；不枚举/不打开其他进程 |
| 日志开销 | 一行（或两行），无循环、无分配大缓冲；沿用既有 `RuntimeLog::Channel::GameServer` |

**日志行建议 schema（稳定、机读、可 diff）**

```
[<YYYY-MM-DD HH:MM:SS>] [<role>/game-server] image-sample v=1 pid=<n> base=0x........ path="<GetModuleFileNameW>" machine=0x014C sections=<n> timestamp=0x........ sizeofimage=0x........ rva=0x000FEA20 len=5 expected="55 8B EC 56 57" effective="55 8B EC 56 57" match=1
[<YYYY-MM-DD HH:MM:SS>] [<role>/game-server] image-sample v=1 pid=<n> rva=0x0008371A len=8 expected="83 7C 24 08 01 0F 94 C0" effective="83 7C 24 08 01 0F 94 C0" match=1
```

---

## 5. 证据保存与可重复审计

| # | 步骤 | 产物 |
|---|---|---|
| 1 | 运行前归档并哈希沙箱既有日志（或改名隔离），保证每次运行日志独立 | `run_<UTC>\pre_logs.sha256` |
| 2 | 运行后**立即**把 `Ayria\Logs\CodolGameServer.log` 复制为**只读证据副本**（如 `evidence\image-sample-<UTC>.log`） | 原始证据副本 |
| 3 | 对证据副本计算 SHA-256 并写入清单 | `evidence\<file>.sha256` |
| 4 | 记录四元组：客户端 exe SHA-256、插件 DLL SHA-256、证据副本 SHA-256、采样时间（UTC + 本地） | `evidence\sample-record.json` |
| 5 | 记录操作者、授权编号、命令原文、进程 PID | 同上 |
| 6 | 报告引用**证据副本**，原始日志保持不动 | — |

**可重复审计**：任何第三方可用 ① 客户端 SHA-256 ② 插件 SHA-256 ③ 证据副本 SHA-256 ④ 日志行原文，独立复核"该行确实来自该插件、在该客户端上、在此时刻产生"。

---

## 6. 停止条件

| # | 触发条件 | 动作 |
|---|---|---|
| ST-1 | 证据副本中**没有** `image-sample` 行 | **停止**。说明落盘的不是新插件（或开关未生效）。**不得**改用 Frida/注入。 |
| ST-2 | `path=` 不是 `codoMP_client_shipRetail.exe`，或外部文件 SHA-256 ≠ `36997674…B537` | **停止**，判"采样对象身份不符"。 |
| ST-3 | 存在**多个**候选客户端进程 | **停止**，先做单实例隔离（不改启动链，仅清理残留进程）。 |
| ST-4 | `rva + len > sizeofimage`，或页不可读，或 `sample_error=` 出现 | **停止**，记录为"采样不可行"，**不得**改用跨进程读取。 |
| ST-5 | `match=0`（任一 RVA 与静态期望不符） | **停止**，进入判定矩阵 **C 类**；**不得**修改 RVA/守卫/门禁。 |
| ST-6 | 证据四元组不完整（缺任一 SHA-256 或时间/PID） | **停止**，补齐后重跑一次；**不得**以不完整证据进入判定。 |
| ST-7 | 需要"放宽门禁才能继续观测" | **停止**。这是明令禁止项。 |

---

## 7. 授权分级（每一项都需**单独**批准）

| 级别 | 操作 | 内容 | 本任务是否已授权 |
|---|---|---|---|
| **B-1** | 改只读代码 | 在 `EngineBindings.cpp` 增加 `sampleHostImageIdentity()`（门禁之前、显式开关、默认关闭、纯日志） | **否** |
| **B-2** | 构建 | `xmake build ol_game_server`（**显式命名目标**，避免触发 `ol_deploy`） | **否** |
| **B-3** | 落盘到沙箱 | 用替代流程把新插件放入 `<E>\Ayria\Plugins\`（`ol_deploy` 禁用） | **否** |
| **B-4** | 启动 1 个客户端 | **单个**沙箱客户端；只读 `Ayria\Logs\*`；不抓包、不调试、不读内存、不改配置 | **否** |
| **B-5** | 关闭开关后的对照运行 | 可选：同一客户端、开关关闭，证明"默认行为逐位不变"（日志无新行） | **否** |
| **E-1** | 明确不做 | 放宽 `SizeOfImage`、删除守卫、改 RVA/ABI/协议常量、Frida、注入、跨进程读内存、改启动器/TCLS/Ayria/大厅链、在 `GOLDEN-LOBBY-001` 内运行 | — |

---

## 8. 与判定矩阵的衔接（**预先登记**，事后不得改判据）

| 观测组合 | 判定 | 允许的下一步 | 禁止 |
|---|---|---|---|
| E2 = `0x0E5D6000` ∧ E3 match ∧ E4 match | **A** | 继续核验门禁前置条件与后续守卫；**不立即修改** | 不得改动任何常量 |
| E2 ≠ `0x0E5D6000`（尤其 = `0x0E659000`）∧ E3 match ∧ E4 match | **B** | **提出**目标构建专用的门禁常量修订建议，**等待单独批准** | 不得自行改常量、不得启用容差 |
| E3 match=0 ∨ E4 match=0 | **C** | **停止**修改 RVA/守卫/门禁；先确认目标映像与 RVA 来源 | 不得改任何 RVA/守卫/常量 |
| 构建件与部署件无法建立对应（**本轮已部分解除**，见一致性报告 V1/V6） | **D** | 保持运行时结论为 `UNKNOWN`，不据当前源码推断部署件行为 | 不得以放宽尺寸/删除守卫消除 UNKNOWN |

> 完整机读版本见 `COMBAT_P1_DECISION_MATRIX.json`（含每条判定的前置谓词、所需证据字段、后果与禁止项）。

---

## 9. 明确排除的方案

1. **Frida 附加**（历史 2 次尝试 0 成功：`ProcessNotFoundError`、`ProcessNotRespondingError`）。
2. **进程注入 / DLL 注入**。
3. **跨进程内存读取**（`ReadProcessMemory` 等）。
4. **修改运行映像**或运行时打补丁以"让门禁通过"。
5. **默认或无条件启用 `SizeOfImage` 容差**（本轮方案**不含**容差开关）。
6. **删除/绕过**映像身份门禁或任何前缀守卫。
7. 在 `GOLDEN-LOBBY-001` 冻结目录内运行或写入。
8. 把"端口监听成功"或"工具运行成功"当作阶段成果。

---

## 10. 本方案仍未解决的未知项

| # | 未知 | 说明 |
|---|---|---|
| U-1 | 运行时映像 `SizeOfImage` 是否为 `0x0E5D6000` | 正是 E2 要回答的 |
| U-2 | 运行时 RVA `0x0FEA20` / `0x8371A` 的字节 | 正是 E3/E4 |
| U-3 | 加壳器是否在内存中恢复原始 PE 头与代码 | E1/E2/E3/E4 联合可判 |
| U-4 | 部署 DLL 中 `bind()` 的机器码是否等同于当前源码编译结果 | 一致性报告 V5；LTO 下**不可判定**，且**不影响**日志行为推断 |
| U-5 | 门禁失败后 75 条守卫是否会在真实映像上成立 | **不能**在门禁之前测（会改变语义）；本方案**不主张**为此放宽门禁 |
