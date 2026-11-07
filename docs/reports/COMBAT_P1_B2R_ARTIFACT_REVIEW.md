# COMBAT_P1_B2R_ARTIFACT_REVIEW — 新构建 DLL 只读静态审查

**任务**：COMBAT-P1-B2R（只读静态审查与部署前核验）
**日期**：2026-10-11
**性质**：**只读**。未运行任何 `xmake build`；未部署；未调用 `ol_deploy`；未启动/附加/注入/终止任何进程；未修改源码/配置/RVA/ABI/门禁/协议常量；未覆盖任何既有产物或历史证据。
**执行前已重新实测**：下列所有哈希/大小/PE 字段均由**本轮重新计算**，未沿用历史报告数值。

---

## 0. 结论速览

| 结论 | 内容 | 证据强度 |
|---|---|---|
| A | 新构建 DLL（`175BBC31…`）与旧构建 DLL（`DBA7273A…`）、stage/沙箱部署件（`6D493B82…`）**互为不同制品**；stage == 沙箱 | **直接证据** |
| B | 导出面（名称集合、序号、函数 RVA）在新旧 DLL 之间**完全相同**（53/53，0 差异） | **直接证据** |
| B' | 导出面相同 **≠** 内部 ABI / 函数机器码相同；两 DLL 的大小、`SizeOfImage`、`TimeDateStamp`、哈希均不同 | **直接证据** |
| C | **B-1 采样代码确实进入了最终 DLL**：14/14 个 B-1 特征字符串在新 DLL 中存在，在旧 DLL 与沙箱 DLL 中**全部不存在**；新 MAP 含 34 处 B-1 辅助符号，旧 MAP 为 0 | **直接证据（二进制级）** |
| C' | 采样的**运行时行为**（能否正确执行、日志字段是否如设计） | **UNKNOWN**（本任务不运行） |
| C'' | 新 DLL 中采样函数对应的**机器码语义**是否与源码逐条一致 | **UNKNOWN**（无 PDB；未反汇编） |
| D | B-1 源码差异为 **+297 / −0**（纯追加）；`EngineBindings.hpp` **未修改**；门禁 `if` 文本与 HEAD **逐字节相同**（仅位移 +297 行） | **直接证据** |
| E | 沙箱部署 DLL **未被覆盖**；F/D/HEAD/冻结大厅基线**均未变化** | **直接证据** |

---

## A. 产物身份（任务 A）

### A.1 四个制品的实测身份（本轮重新计算）

| # | 制品 | 路径 | 字节 | SHA-256 | PE `TimeDateStamp` | `SizeOfImage` | 导出数 |
|---|---|---|---:|---|---|---|---:|
| 1 | **新构建 DLL** | `<F>\build\bin\release\CodolGameServer.Localnet32` | **6,565,376** | `175BBC31D6C972AC734F919C5D90064D45970BBFED9ADD7BFA85057CEBCFBBAF` | `0x6ACA0481` (2026-10-10 17:25:21) | `0x007E2000` | 53 |
| 2 | **旧构建 DLL**（构建前副本） | `_combat_p1_b2_evidence\prebuild\bin_release_CodolGameServer.Localnet32` | 6,559,232 | `DBA7273A0C9DD31CDD5619DD47B11C01EDC21AE17EEFC18FDD71F43B992097BC` | `0x6AC9C4A2` (2026-10-10 12:52:50) | `0x007E0000` | 53 |
| 3 | **stage DLL** | `<F>\build\stage\codol\Ayria\Plugins\CodolGameServer.Localnet32` | 6,556,672 | `6D493B820E84A21B096C9914616B75DCEC488920D7AC76867049B20C5C6B2021` | `0x6AC88076` (2026-10-09 13:49:42) | `0x007E0000` | 53 |
| 4 | **沙箱部署 DLL** | `<E:SANDBOX/RUN001>\Ayria\Plugins\CodolGameServer.Localnet32` | 6,556,672 | `6D493B820E84A21B096C9914616B75DCEC488920D7AC76867049B20C5C6B2021` | `0x6AC88076` | `0x007E0000` | 53 |

### A.2 身份关系

```
新构建(175BBC31)  != 旧构建(DBA7273A)  != 部署件(6D493B82)
stage(6D493B82)   == 沙箱(6D493B82)            <- 同一制品（字节级同一）
```

- **必须记录**：旧构建 DLL 的**原始路径已被 B-2 构建覆盖**（编译的必然结果；构建前已按要求备份）。因此"旧构建 DLL"的身份**只能**取自备份副本（#2）；其哈希与 `COMBAT_P1_ARTIFACT_CONSISTENCY.md` 记录的 `DBA7273A…` 一致，可交叉验证。
- **本轮未覆盖、未替换任何部署件**：stage 与沙箱 DLL 仍为 `6D493B82…`，mtime 仍为 2026-10-09 13:49:42。
- **新旧不一致的事实被保留**：新构建产物**既未进入 stage，也未进入沙箱**。

---

## B. 导出与 ABI 表面（任务 B）

**完整有序清单见 `COMBAT_P1_B2R_EXPORT_COMPARISON.txt`**（含四份 DLL 的全部 53 条导出、序号、函数 RVA，以及程序计算出的清单哈希）。

| 比较项 | 结果 |
|---|---|
| `NumberOfFunctions` / `NumberOfNames` / `Base` | 新旧均 `53 / 53 / 1` |
| 导出**名称集合** | **完全相同** |
| 导出**序号** | **完全相同** |
| 导出**函数 RVA** | **完全相同** |
| 逐项差异条数（名称/序号/RVA） | **0** |

### B.1 必须明确的区分（任务 B.4）

| 层次 | 新 vs 旧 | 证据 |
|---|---|---|
| **导出面**（名称/序号/入口 RVA） | **相同** | 直接解析 PE 导出目录，逐项比较，差异 0 |
| **文件身份** | **不同** | SHA-256、字节数（6,559,232 → 6,565,376）、`TimeDateStamp`、`SizeOfImage` 均不同 |
| **内部 ABI**（结构布局、调用约定、内部符号布局） | **无法判定为相同** | 无 PDB；导出面相同**不蕴含**内部布局相同；且新 DLL 增加了匿名命名空间代码 |
| **函数机器码** | **不同（至少部分）** | `bind()` 在 MAP 中由 `0001:00209ff0`（RVA `0x20AFF0`）移至 `0001:0020b0a0`（RVA `0x20C0A0`）；LTO 全局重排 |
| **可调用性 / 运行兼容性** | **不据此断言** | 本任务不运行、不部署 |

> **纪律**：导出面相同**不得**写成"ABI 完全相同"，也**不得**写成"与旧版等价"。

---

## C. 采样代码静态核验（任务 C）

### C.1 源码差异（本轮实测）

| 项 | 值 |
|---|---|
| 文件 | `<F>\src\game_server\EngineBindings.cpp` |
| `git diff --numstat` | `297  0`（**新增 297，删除 0**） |
| 当前 SHA-256 | `5B3794254DB79CEF1E74AA94E2ABBC4E0C41EC0F0CB0597C70C5970FD753BB6F` |
| `EngineBindings.hpp` | **未修改**：工作区 blob `e47e4590c4923a4d31c0e0bbcc0dcd5d4b320fc7` == `HEAD:...` |

### C.2 采样代码是否进入最终 DLL —— **是，直接证据**

**证据一：特征字符串在二进制中的存在性（ASCII 字节级检索）**

| B-1 特征字符串 | 新构建 DLL | 旧构建 DLL | 沙箱部署 DLL |
|---|:--:|:--:|:--:|
| `OLMOD_COMBAT_P0_SAMPLE` | **有** | 无 | 无 |
| `image-sample v=1` | **有** | 无 | 无 |
| `sampler=combat-p1-b1` | **有** | 无 | 无 |
| `stage=module_missing` | **有** | 无 | 无 |
| `stage=e_lfanew_unreadable` | **有** | 无 | 无 |
| `stage=e_lfanew_out_of_range` | **有** | 无 | 无 |
| `stage=nt_headers_unreadable` | **有** | 无 | 无 |
| `gate_expected_timestamp=` | **有** | 无 | 无 |
| `gate_sizeofimage_equal=` | **有** | 无 | 无 |
| `source=EngineBindings.cpp:755-757` | **有** | 无 | 无 |
| `source=ClientProcessPatches.cpp:207-211` | **有** | 无 | 无 |
| `out_of_sizeofimage` | **有** | 无 | 无 |
| `not_readable` | **有** | 无 | 无 |
| `read_faulted` | **有** | 无 | 无 |
| **合计** | **14 / 14** | **0 / 14** | **0 / 14** |

**证据二：链接映像（MAP）中的符号**

| MAP | B-1 辅助符号命中数（`SampleHostImageIdentity` / `ReadHostBytesSafely` / `HostImageReadRva` / `HostRangeIsReadable` / `HostImageHex32` / `HostImageSampleLog`） |
|---|---|
| **新 MAP**（`Timestamp is 6aca0481`，2026-10-10 17:25:21） | **34 处** |
| **旧 MAP**（构建前副本，`Timestamp is 6ac9c4a2`，2026-10-10 12:52:50） | **0 处** |

**证据三：`bind()` 自身被重排**

| MAP | `?bind@EngineBindings@CodolGameServer@@QAE_NXZ` |
|---|---|
| 新 | `0001:0020b0a0` → RVA `0x20C0A0` |
| 旧 | `0001:00209ff0` → RVA `0x20AFF0` |

**结论与强度**：由"新增字符串仅存在于新 DLL"+"新 MAP 含 B-1 符号而旧 MAP 不含"+"`bind()` 位置变化"三条独立证据，**可直接确认 B-1 采样代码被编译并链接进最终 DLL** —— 强于"源码存在"这一层。

### C.3 诊断开关默认关闭（源码逻辑，逐字复核）

```
void SampleHostImageIdentity(std::uint8_t *const module)
{
    char enabled[8]{};
    const auto enabledLength = GetEnvironmentVariableA(
        HostImageSampleSwitch,        // "OLMOD_COMBAT_P0_SAMPLE"
        enabled,
        static_cast<DWORD>(sizeof(enabled)));
    if (enabledLength != 1 || enabled[0] != '1')
        return;
    ...
```

- 仅当环境变量**恰好**为单字符 `'1'` 时才继续；其余一切取值（不存在、`"0"`、`"true"`、`"1 "`、长度 ≠ 1）⇒ **立即 return**，不读内存、不写日志。
- **源码级结论**：默认关闭成立。

### C.4 采样结果不参与绑定判定（源码逻辑，逐字复核）

```
        module_ = reinterpret_cast<std::uint8_t *>(GetModuleHandleW(nullptr));

        // AUTHORISED COMBAT-P1 B-1 DIAGNOSTIC. Read-only and opt-in: returns immediately
        // unless OLMOD_COMBAT_P0_SAMPLE == "1". Its output goes to the log only and is NOT
        // consulted by any condition below; the gate and every guard are unchanged.
        SampleHostImageIdentity(module_);

        if (!module_)
            return false;
```

- 函数返回 `void`；调用语句**未使用任何返回值**；其后代码未改。
- 新增行中 `bindingCommitted_` 唯一出现处是**注释**（"never touches bindingCommitted_"）；`bindingCommitted_.store(true)` 在新增行中出现 **0** 次。
- **源码级结论**：采样结果不参与判定。

### C.5 必须标记为 UNKNOWN 的部分（任务 C.4）

| # | UNKNOWN | 原因 |
|---|---|---|
| U-1 | 采样函数在真实进程中的**行为正确性** | 本任务**不运行**；无运行证据 |
| U-2 | 采样函数对应的**机器码是否与源码逐条语义一致** | **无 PDB**；**未反汇编**；LTO 会重排/内联 |
| U-3 | 新 DLL 中 `bind()` 其余部分是否与旧 DLL 逐位一致 | LTO 全局优化；MAP 显示 `bind()` 已移动，无法逐函数比对 |
| U-4 | 运行时 `TimeDateStamp` / `SizeOfImage` / RVA `0x0FEA20`、`0x8371A` 字节 | 仍需 B-4 类运行证据；**不得**用本审查替代 |
| U-5 | 开关**关闭**时"逐位等价"的二进制级证明 | LTO 下不可得；只能行为级复核 |

> 本审查**不声称**采样代码"能工作"，只声称它**进入了最终 DLL**，且**源码层面默认关闭、不参与判定**。

---

## D. 原有门禁与代码差异（任务 D）

### D.1 B-1 精确差异

- `+297 / −0`（**纯追加**）；删除行 **0**；新增行 `dllexport` = **0**；新增行中"触碰既有守卫模式 `std::equal(..., module_ + …)`" = **0**。
- 两个 hunk：`@@ -3645,4 +3645,295 @@`（新增只读采样辅助块）与 `@@ -3653,4 +3944,10 @@`（门禁前的唯一调用）。

### D.2 本次编译前后没有额外修改 RVA / ABI / 协议常量 / 既有守卫 / 门禁逻辑

| 检查 | 结果 |
|---|---|
| `EngineBindings.hpp` | **未修改**（工作区 blob == HEAD blob）⇒ 145 个 RVA 常量与门禁常量**均未动** |
| 门禁常量值 | `EngineBindings.hpp:438` = `0x6096930A`；`:439` = `0x0E5D6000`；`:440` = `0x0FEA20`（**原值**） |
| 门禁 `if` 文本 | 与 HEAD 版本**逐字节相同**；行号由 `3662-3664` 位移到 `3959-3961`（= +297，恰等于新增行数） |
| `if (!module_)` | 由 `3655` 位移到 `3952`（= +297）；文本相同 |
| 新增行对门禁常量的引用 | `ExpectedTimestamp` ×2、`ExpectedImageSize` ×2 —— **全部为"读取用于打印/比较"**；赋值 **0** 次 |
| 新增行中的 `ComFrameRva` 命中 | 2 次，均为**新局部常量名** `HostImageSampleComFrameRva` 的**子串匹配**，不是对门禁常量 `ComFrameRva` 的引用 |
| 新增行中的 `std::equal` | 2 次，均为采样器自身的**只读比较**（`ComFramePrefix`、探针期望字节），**不是** `bind()` 的守卫 |
| 导出表 | `dllexport` 新增 0；新 DLL 导出数仍 53（见 B） |
| 其他源文件 | 工作区另有 7 个 `src` 文件处于 **B-1 之前既有**的未提交修改状态（`Appmain.cpp` / `FrameHook.{cpp,hpp}` / `sv_network_mp.{cpp,hpp}` / `win_net.{cpp,hpp}`）；**本轮与 B-1 均未新增改动**，`git status` 仍为 **18** 条 |

### D.3 三类结论必须分开（任务 D.3）

| 层次 | 结论 | 依据 |
|---|---|---|
| **源码级** | B-1 为纯追加；默认关闭；不参与判定；门禁与守卫源码未改 | `git diff`、逐字复核（C.3/C.4/D.1/D.2） |
| **构建元数据级** | 新 MAP 含 B-1 符号（34 处）、旧 MAP 为 0；新 MAP 时间戳 17:25:21；`bind()` RVA 由 `0x20AFF0` → `0x20C0A0` | MAP 文本检索 |
| **二进制/机器码级** | B-1 特征字符串**存在于新 DLL**、不存在于旧 DLL/沙箱 DLL；新 DLL 与旧 DLL 的 SHA-256/大小/`SizeOfImage`/`TimeDateStamp` **均不同** | 直接哈希与字节检索 |
| **（未达）运行时级** | 采样行为、运行时映像事实 | **UNKNOWN**（未运行） |

### D.4 不得由大小差异推断函数正确性（任务 D.4）

- 新 DLL 比旧 DLL **大 6,144 字节**（6,559,232 → 6,565,376），`SizeOfImage` 由 `0x007E0000` 增到 `0x007E2000`。
- **这只是"体积变化"**，**不能**用于推断：某函数正确/不正确、采样逻辑是否符合预期、门禁是否会被通过、旧 RVA 是否仍成立。本审查**不作**此类推断。

---

## E. 基线完整性（任务 E）

| 项 | 检查方式 | 结果 |
|---|---|---|
| 沙箱部署 DLL SHA-256 | 直接实测 | `6D493B820E84A21B096C9914616B75DCEC488920D7AC76867049B20C5C6B2021`，mtime **2026-10-09 13:49:42** ⇒ **未被覆盖** |
| stage DLL | 直接实测 | 同哈希、同 mtime ⇒ **未被覆盖** |
| F `git status --porcelain` | 实测 | **18** 条（与 B-2 后一致） |
| F HEAD | `git rev-parse` | `2a75bdd8872bb9f54006382a924c3006ec9affc2`（未变） |
| D `git status` / HEAD | 实测 | **6** 条 / `2a75bdd…`（未变） |
| `GOLDEN-LOBBY-001/REF_LOBBY_KIT` | 文件数与最新 mtime | **141 文件**；最新 mtime **2026-10-07 22:10:52**（未触碰） |
| 本轮是否执行构建/部署/复制/清理/进程操作 | 全轮操作清单 | **均未执行**（仅只读读取与哈希计算） |

---

## F. 未解决的风险与未知项

| # | 项 | 类别 | 说明 |
|---|---|---|---|
| R-1 | 新 DLL **同时包含** B-1 之外的工作区改动 | **部署范围风险** | 新 DLL 由**当前工作区**链接而成：除 B-1 外，还含 `Appmain.cpp` / `FrameHook.*` / `sv_network_mp.*` / `win_net.*` 等**既有未提交修改**（这些改动在旧构建 `DBA7273A…` 中已存在，但**不在**已批准目标 `6D493B82…` 中）。因此部署新 DLL **不是"只部署采样代码"**，而是"部署当前工作树状态"。**B-3 授权必须显式接受这一点**，或另立收窄方案。 |
| R-2 | 编译通过 ≠ 可运行 | 运行时风险 | 本轮与 B-2 均未运行；采样代码在真实进程中的行为为 **UNKNOWN** |
| R-3 | 无 PDB ⇒ 机器码级语义不可核 | 证据缺口 | 无法逐函数证明等价性；`bind()` 位置已变 |
| R-4 | 运行时映像事实仍未取得 | 目标缺口 | `TimeDateStamp` / `SizeOfImage` / `0x0FEA20` / `0x8371A` 仍为**待核验的静态期望值** |
| R-5 | `BUILD-RISK-XMAKE-AFTER-BUILD-001` 仍 OPEN | 流程风险 | 见该文件；本轮未执行任何 `xmake` 命令 |
| R-6 | 旧构建 DLL 的原始路径已被覆盖 | 证据管理 | 已有构建前副本（A.1 #2）与其哈希 |

---

## G. 是否具备申请 B-3 独立授权的条件（任务六.5）

**结论：静态层面已具备申请条件；但申请中必须显式声明 R-1。**

支持申请的事实：
1. B-1 采样代码**已被证明进入最终 DLL**（14/14 特征字符串 + 34 处 MAP 符号 + `bind()` 重排，三条独立证据）；
2. 导出面（名称/序号/RVA）**完全未变**，未新增导出；
3. 源码层面**默认关闭**、**不参与判定**；`EngineBindings.hpp` 未改，门禁与既有守卫文本**逐字节未改**；
4. 沙箱/stage/工作区/冻结基线**均未被触碰**，构建前状态已备份。

必须在 B-3 申请中一并声明/决定：
- **R-1（部署范围）**：部署 `175BBC31…` 等于部署"当前工作树"，含 B-1 之外的既有未提交修改。需用户明确接受，或另立收窄方案（任何收窄都需单独授权，本轮不得实施）。
- 部署方式必须**不经 `ol_deploy`**（替代落盘流程），且部署前备份沙箱现有 `6D493B82…`；
- 部署后**只做只读日志采样**，**不启用任何尺寸容差**、**不放宽门禁**；
- 采样必须在**开关开启**（`OLMOD_COMBAT_P0_SAMPLE=1`）与**关闭**两种条件下各观察一次，以验证默认路径不变；
- 采样结果只用于回答 `gate_timestamp_equal` / `gate_sizeofimage_equal` 与两个 RVA 的 `match`，随后按 `COMBAT_P1_DECISION_MATRIX.json` 的 A/B/C/D 判定，**不得**据采样结果直接改常量。

**本任务不申请、不执行 B-3；不授权 B-4；不做任何运行实验。**

---

## H. 交付物与复核

| 文件 | 说明 |
|---|---|
| `COMBAT_P1_B2R_ARTIFACT_REVIEW.md` | 本文件 |
| `COMBAT_P1_B2R_EXPORT_COMPARISON.txt` | 四份 DLL 的完整有序导出清单 + 逐项比较 + 清单哈希 |
| `COMBAT_P1_B2R_SHA256_MANIFEST.txt` | 本轮交付物与被引用证据的 SHA-256 清单 |

- **未覆盖**之前的 B-2 报告与清单（`COMBAT_P1_B2_BUILD_REPORT.md`、`COMBAT_P1_B2_SHA256_MANIFEST.txt` 保持原样；事件轮副本另存于 `_combat_p1_b2_evidence/`）。
- 本轮**唯一写入**：上述三份新交付物。

---

## I. 纪律声明

- 未运行任何 `xmake build`；未调用 `ol_deploy`；未部署；未复制文件到沙箱；未清理。
- 未启动、附加、注入或终止任何游戏进程；未读取其他进程内存。
- 未修改源码、配置、RVA、ABI、门禁或协议常量；未 `reset`/`clean`/`rebase`/`commit`/`push`。
- 未覆盖既有构建产物、部署件或历史证据。
- **未把静态期望字节描述为已验证的运行时字节**；对无法由现有证据判定者一律标注 **UNKNOWN**。
