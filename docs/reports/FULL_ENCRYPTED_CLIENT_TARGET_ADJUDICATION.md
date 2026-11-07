# FULL_ENCRYPTED_CLIENT_TARGET_ADJUDICATION — 目标纠偏与运行路线重裁定

**日期**：2026-10-10
**工作基准**：**F = `F:\桌面\ol\ol-mod-olfinal`**（唯一活动基准；D 只读冻结）
**本轮性质**：只读源码/文档/Git 溯源 + 只读制品核验。**未构建、未运行、未启动客户端、未注入、未改源码、未提交 Git。**
**目的**：纠正"把学习文档中的去壳 `out.exe` 当作项目级强制输入"这一目标模型错误，重新划分阻断项，并给出以**真实全加密客户端**为目标的实施路线。

---

## 0. 最终裁定

```text
PROJECT TARGET MODEL: CORRECTED

SERVER-SIDE DEVELOPMENT: CONTINUE WHERE INDEPENDENTLY VERIFIABLE

FULL-ENCRYPTED CLIENT RUNTIME COMPATIBILITY: UNVERIFIED UNTIL EVIDENCE EXISTS

CLIENT LAUNCH / INJECTION: NOT EXECUTED; SEPARATE AUTHORIZATION REQUIRED
```

**一句话**：`out.exe` 是**历史逆向的来源对象**，不是我们运行全加密客户端所必需的文件。我们实际运行的对象是**全加密零售客户端 `codoMP_client_shipRetail.exe`**；真正未闭合的门禁不是"缺 `out.exe`"，而是"**该客户端的运行时映像是否满足现有绑定门禁**"——这一项本轮无证据，必须保留为 BLOCKED，且**不得通过删除门禁来消除**。

---

## 1. 修正后的项目目标模型

### 1.1 旧模型（错误）

```text
[根依赖] OLFinal unpacked out.exe (E3823FD6… / 044c396c…)
   ↓ 缺失 ⇒ B1 BLOCKED
   ↓ 因此"全部实机验收"乃至"整个项目"被描述为受阻
[下游] 地图 .ff、工具链、构建、测试、Golden Copy、对局
```

该模型的表述可见于 [SOURCE_FEASIBILITY_2026-10-09.md](<F:/桌面/ol/ol-mod-olfinal/.agents/audits/2026-10-09/SOURCE_FEASIBILITY_2026-10-09.md>) §11 Q2/Q5：

> Q2 … **批准的目标客户端二进制**（`E3823FD6...`，**或**明确批准的 OLFinal `out.exe` + 其 SHA-256）… 它是**唯一的根依赖**。
> Q5 … 在它到手之前，任何构建、抓包、Golden 或运行时验证都无法产生可信证据。

以及 [ARTIFACT_REQUIREMENTS.md](<F:/桌面/ol/ol-mod-olfinal/.agents/audits/2026-10-09/ARTIFACT_REQUIREMENTS.md>) §A / §E：

> **需要**：OLFinal **unpacked** `out.exe`（或其明确来源 + 完整 SHA-256）。
> 交付清单（最小集）… 1. OLFinal unpacked `out.exe` **或其来源 + 完整 SHA-256**

**这个模型的错误有三层**：

1. **对象错位**：把一个"逆向来源样本"当成了"运行前置文件"。`out.exe` 是推导 RVA/前缀时所用的**分析对象**；运行时真正被判定的是**进程内映像**。
2. **范围放大**：把"绑定门禁无法通过"扩大成"所有服务端工作都被阻断"。事实上服务端绝大多数代码、协议、测试与客户端身份**无关**（见 §5）。
3. **自相矛盾**：仓库自己的启动链 [CodolGame.py](<F:/桌面/ol/ol-mod-olfinal/tools/runtime/CodolGame.py>) 第 28 行默认目标就是 `codoMP_client_shipRetail.exe`，而 [Auth3ClientPatches.cpp](<F:/桌面/ol/ol-mod-olfinal/src/backend/Demonware/Auth3ClientPatches.cpp>) 第 138-139 行已经把 `out.exe` **和** `codoMP_client_shipRetail.exe` 并列接受为合法宿主映像。

### 1.2 新模型（修正后）

```text
[运行目标]  全加密零售客户端 codoMP_client_shipRetail.exe（本机实测存在）
              ↓ 启动链：Injector32.exe → Bootstrapper32.dll → 5 个插件
              ↓ 运行时对象：进程内映像 (GetModuleHandleW(nullptr) + PE 头 + 代码字节)
[门禁]      绑定/前缀校验必须针对"运行时映像"成立 —— 未验证 ⇒ BLOCKED（不得删除）
[来源对象]  历史去壳样本 out.exe / 3.3.3.3 QA 客户端 —— 仅用于推导与交叉核对
[独立可做]  服务端逻辑、协议序列化、离线测试、回环网络、可追溯性 —— 与客户端身份无关
```

**关键概念替换**：

| 旧表述 | 新表述 |
| --- | --- |
| "必须先拿到 `out.exe`" | "必须让**运行时映像**通过绑定门禁（或证明门禁常量需要按实测修订，且该修订需单独授权）" |
| "客户端身份 = SHA-256 等于 `E3823FD6…`" | "客户端身份 = **我们实际运行的那个文件**的 SHA-256（待登记），且**运行时映像**另行核验" |
| "B1 阻断全部实机验收" | "运行时兼容性阻断**实机验收**；**不**阻断服务端开发" |

---

## 2. 对象区分：`out.exe` / 3.3.3.3 QA / 实际全加密客户端

### 2.1 六类对象

| 对象 | 标识 | 证据来源 | 在本项目中的角色 |
| --- | --- | --- | --- |
| **O-1 历史去壳样本** | `out.exe`；SHA-256 `044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9`；build 1649370；`TimeDateStamp=0x6096930A`；`SizeOfImage=0x0E5D6000` | `tools/reverse/annotations/out.exe.json:3`；`EngineBindings.hpp:438-439`；git `55fcdbf` | **逆向来源对象**。`EngineBindings` 的 145 个 RVA 与 82 处前缀守卫由它推导 |
| **O-2 3.3.3.3 QA 客户端** | `TimeDateStamp=0x57611E31`；`SizeOfImage=0x0C72A000` | `backend/Demonware/CodolClientPatches.cpp:45-46, 612-613`；git `55fcdbf` 明确记录 `0x57611E31 -> 0x6096930A` 的翻转 | **旧基线**。`CodolClientPatches` 的 8 个客户端钩子仍键在它上面，**在本客户端上故意不安装** |
| **O-3 实际运行目标（全加密零售客户端）** | 文件名 `codoMP_client_shipRetail.exe`；SHA-256 `36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537`；7,841,344 B；`FileVersion=1649370`；`TimeDateStamp=0x6096930A`；`SizeOfImage=0x0E659000`；7 段 `.tp3`×6 + `.tvm0` | **本轮只读 PE 实测**；`arch_modules.csv:29`；`codol_module_inventory.csv:11`；`artifact_provenance.json:24-46` | **我们实际运行的对象**。启动链默认目标 |
| **O-4 运行时映像** | 进程内 `GetModuleHandleW(nullptr)` 的 PE 头 + 代码字节 | **无任何证据** | **门禁 A/B 真正判定的对象** |
| **O-5 `E3823FD6…F37B`** | 完整 SHA-256 `E3823FD6AFC80FB25FA84747E6E9634707B9A0B189357A5466921CDA354AF37B` | `GOLDEN_COPY_SPEC.md:29` 称"客户端 EXE"；`artifact_provenance.json:9` 称"OLFinal unpacked `out.exe`"；**本任务指令称其属 3.3.3.3 QA 客户端** | **归属未裁定**。三方表述互斥，本轮**不裁定、不重写** |
| **O-6 `OL.exe`** | 哈希未知（本机未实测） | git `55fcdbf`：门禁 A 对其"gate mismatching 且 55/66 守卫失败" | 第三个零售客户端对象；**非本机对象**，仅登记 |

### 2.2 本轮新增的只读实测（把 O-1 与 O-3 的关系说清楚）

对 O-3 的磁盘文件做只读 PE 读取（方法见 §10.2）：

| 字段 | O-3 实测 | O-1 的期望值（`EngineBindings`） | 比较 |
| --- | --- | --- | --- |
| `TimeDateStamp` | **`0x6096930A`** | `0x6096930A` | **相同** |
| `SizeOfImage` | **`0x0E659000`** | `0x0E5D6000` | 不同（差 `0x83000`） |
| `FileVersion` | **`1649370`** | build 1649370 | **相同** |
| `Machine` / `magic` | `0x014C` / `0x010B` (PE32 x86) | x86 | 相同 |
| 段表 | `.tp3`×6 + `.tvm0`（加壳） | （去壳样本，无这些段） | 结构性差异 |

**可支持的推断（标注为推断，不是结论）**：
O-3 与 O-1 **很可能属于同一构建（1649370）**——两者 `FileVersion` 相同，且 O-3 的 `TimeDateStamp` 精确等于 O-1 的期望时间戳；加壳器保留原 PE 的链接时间戳是常见行为。O-3 的 `SizeOfImage` 更大，与"多了 `.tp3`/`.tvm0` 段"相符。

**不得从该推断推出的结论**：
- ❌ 不得据此宣称 O-3 的**运行时映像**满足门禁 A。
- ❌ 不得据此把 O-3 的 SHA-256 写成 `E3823FD6…` 或 `044c396c…`。
- ❌ 不得据此删除或放宽任何 RVA/前缀/尺寸校验。
- ❌ 不得把"同 `TimeDateStamp`"当作"同一构建"的证明（`artifact_provenance.json:81-85` 的 `sourceRelationRules` 明确禁止）。

### 2.3 仓库内已有的一次同类纠错（先例，不是我的新提案）

[Auth3ClientPatches.cpp](<F:/桌面/ol/ol-mod-olfinal/src/backend/Demonware/Auth3ClientPatches.cpp>) 第 103-119 行**已经完整记录过一次同型错误及其修正**：

> `// WHY THERE IS NO PROCESS-NAME GATE HERE ANY MORE -- handoff §§191g.`
> `// This used to refuse any image not named codoMP_client_shipRetail.exe, copied from the`
> `// sibling gate in CodolClientPatches.cpp. There it is CORRECT and documented: every RVA in`
> `// that file is a 3.3.3.3 address, so the build IS the precondition. Here it was never the`
> `// precondition -- the three sites below are found by BYTE SIGNATURE …`
> `// The cost of the borrowed gate was a remote player's login. installAuth3ClientPatches()`
> `// returned TRUE WITHOUT PATCHING on out.exe, ServerFactory::create read that as success,`
> `// and the client validated the self-signed certificate Auth3TlsTransport mints at runtime`
> `// for real -- \`tlsv1 alert unknown ca\`, then a 40 second stall and a hang up.`
> `// The honest precondition is the one install() already enforces: an i386 image in which`
> `// all three signatures locate, and locate UNIQUELY. A name is a lossy view of that.`

并且第 136-140 行：

> `bool isKnownClientImage(const std::string &name) { return _stricmp(name.c_str(), "out.exe") == 0 || _stricmp(name.c_str(), "codoMP_client_shipRetail.exe") == 0; }`

**这条先例给出三点可直接引用的结论**：
1. "**借用来的身份门禁**"在本仓库已经造成过一次真实故障（远程登录失败），并被记录为教训。
2. 正确的门禁形式是"**在目标映像中按签名唯一定位**"，而不是"文件名/单一哈希相等"。
3. 仓库已经把 `out.exe` **与** `codoMP_client_shipRetail.exe` **并列**视为合法客户端映像。

---

## 3. 旧 B1 门禁逐项裁定表

旧 B1 的组成（[CODOL_SERVER_PROGRESS_20261009.md](CODOL_SERVER_PROGRESS_20261009.md) §9 与 §4，以及 [ARTIFACT_BLOCKERS.md](ARTIFACT_BLOCKERS.md)）：

| # | 旧 B1 组成 | 性质裁定 | 处置 |
| --- | --- | --- | --- |
| **1** | "可信 `out.exe` 本体缺失" ⇒ **项目级** BLOCKED | **A 类：不再适用的文档前置条件** | **撤销其项目级地位**。`out.exe` 降为 O-1 逆向来源对象；其缺失只影响"以 O-1 为唯一依据的离线复核"，不影响项目推进 |
| **2** | "历史 SHA-256 `044c396c…257f9` 尚未对本体复核" | **A 类（降级）** | 保留为 **O-1 的登记项**；仅在"使用 O-1 派生的 RVA/前缀"时才是必要条件 |
| **3** | "`TimeDateStamp`/`SizeOfImage` 与该 SHA-256 无独立交叉证据" | **A 类（降级）** | 同上；对 O-1 的构建身份登记。**不得**用它去判 O-3 |
| **4** | "RVA `0x0FEA20` / `0x8371A` 预期字节未对可信目标制品复核" | **B 类：仍然有效的运行时安全门禁**（对象需更正） | **保留**。对象从"O-1 文件"改为"**O-4 运行时映像**"；对 O-1 的复核只是其中一条（离线）路径 |
| **5** | "`E3823FD6…` 属 3.3.3.3 QA 客户端，不得默认用作 OLfinal 目标哈希" | **A 类：未裁定的文档冲突** | **保留冲突、不裁定**。见 §8.2 |
| **6** | "加壳候选与去壳目标的等价性 UNKNOWN" | **B 类（提法需更正）** | **保留**，但重述为"**O-3 的运行时映像是否满足门禁 A/B**"，而不是"加壳件 vs 去壳件是否等价" |
| **7** | （隐含）"`SizeOfImage=0x0E659000 ≠ 0x0E5D6000` ⇒ 宿主身份不匹配" | **错误推论** | **更正**：该比较用的是**磁盘加壳文件**的头，而门禁读的是**运行时映像**的头。两者不是同一对象，该不等**不能**作为身份判负的依据 |

**一句话**：旧 B1 里真正需要保留的只有第 4、6 项，而且**对象都必须从"磁盘文件"改为"运行时映像"**；其余是错误继承的目标假设或对象错位。

---

## 4. 仍然有效的运行时安全门禁（B 类，**不得删除、不得置为 GO**）

### 4.1 现存门禁清单（只读实测）

| ID | 门禁 | 代码位置 | 判定对象 | 现状 |
| --- | --- | --- | --- | --- |
| **G-A1** | 宿主 PE 身份：`TimeDateStamp==0x6096930A && SizeOfImage==0x0E5D6000` | `EngineBindings.cpp:3661-3667`；复用点 `ClientProcessPatches.cpp:548-551`、`DedicatedProcessPatches.cpp:460-461,681-682` | **O-4 运行时映像** | **UNVERIFIED**（无运行时证据） |
| **G-A2** | 82 处 `std::equal` 字节前缀守卫（`ComFrameRva=0x0FEA20` 的 `55 8B EC 56 57` 等） | `EngineBindings.cpp`（`bind()` 内），定义见 `EngineBindings.cpp:755-757` | **O-4 运行时映像的代码字节** | **UNVERIFIED** |
| **G-A3** | 145 个 `constexpr std::size_t *Rva` 常量（`EngineBindings.hpp`） | `EngineBindings.hpp` | O-4 | 常量存在；**适用性** UNVERIFIED |
| **G-B1** | 后端客户端补丁身份：`TimeDateStamp==0x57611E31 && SizeOfImage==0x0C72A000` + 文件名 `codoMP_client_shipRetail.exe` | `CodolClientPatches.cpp:610-616`（名字检查 :598） | O-4 | **已知会拒 O-1 与 O-3**（该文件自身注释说其 8 个 RVA 是 3.3.3.3 的、未移植到 1649370）。**这是有意的降级，不是缺陷** |
| **G-C1** | `Auth3` 客户端补丁：i386 + 三处签名**唯一定位**（**无名字门禁**） | `Auth3ClientPatches.cpp:142-158` | O-4 | 已按正确方向修正；其**在该映像上是否定位成功**仍 UNVERIFIED |
| **G-D1** | 插件加载与调用约定：`Injector32.exe` → `Bootstrapper32.dll` → `onStartup`/`onInitialized` | `CodolGame.py:368-382`；沙箱 `E:\CODOL_SANDBOX\RUN001\Ayria\` | O-4 进程 | **UNVERIFIED**（无加载日志） |
| **G-E1** | 真实网络对局链路（connect / gamestate / snapshot / 双客户端） | 见 [SOURCE_FEASIBILITY_2026-10-09.md](<F:/桌面/ol/ol-mod-olfinal/.agents/audits/2026-10-09/SOURCE_FEASIBILITY_2026-10-09.md>) §3 | 双客户端进程 | **UNVERIFIED** |

### 4.2 为什么这些门禁必须保留

1. **G-A1/G-A2 是"防止静默错调"的护栏**。`EngineBindings.cpp:4156-4162` 的注释已经写明这类风险：

   > `// Leaving them pointing at the 3.3.3.3 RVAs would have been the silent failure instead: a`
   > `// plausible address, called through a function pointer, on a build where it is some`
   > `// unrelated function.`

   若删掉门禁，3.3.3.3 的 RVA 会在本客户端上被当作合法函数指针调用——这正是要避免的。

2. **仓库自己把门禁设计成"失败即 fail-closed"**。`bind()` 第 3653 行先 `bindingCommitted_.store(false)`，失败即撤销已发布的有效性；`Auth3` 的教训正是"**返回 TRUE 却没有打补丁**"造成的真实故障（§2.3）。

3. **G-B1 的"拒绝"是设计而非缺陷**，且其注释写明了退出条件：

   > `// TODO(CODOL): port the eight RVAs below to 1649370 if the OLfinal client turns out to need`
   > `// these hooks. … Exit condition is a live client reaching its loadout with these absent;`
   > `// if it does, delete this note instead of porting.`

   该退出条件需要**运行时证据**（客户端能否在缺少这些钩子时到达 loadout），本轮无法取得。

### 4.3 需要澄清的一处风险（不是删除门禁，而是确认其常量）

`EngineBindings.hpp:438-439` 的 `ExpectedImageSize = 0x0E5D6000` 是**对运行时映像**的断言。O-3 的**磁盘**映像为 `0x0E659000`。因此存在两种可能，**目前无法区分**：

- **情形 α**：加壳器在运行时就地解壳并恢复原始 PE 头 ⇒ `SizeOfImage` 变为 `0x0E5D6000` ⇒ G-A1 通过。
- **情形 β**：运行时仍保留加壳布局（`0x0E659000`）⇒ G-A1 会**拒绝**一个代码正确的宿主 ⇒ 门禁常量需要按实测修订。

**处置（本轮）**：
- **不修改任何常量**（§七 明确禁止）。
- 把"区分 α/β"登记为 **D 类待授权验证项**，其证据是"进程内 PE 头"（见 §7 E-2）。
- 若将来实测为 β，则修订 `ExpectedImageSize` **必须**满足：有实测证据、有单独授权、且**同时**用 G-A2 的字节前缀作为真正的正确性判据——**不得**以"让门禁变绿"为理由修改。

---

## 5. 可立即继续的服务端工作清单（C 类，不触碰客户端进程）

**判定原则**：与客户端 PE 身份、运行时映像、插件加载**无关**；离线可执行或离线可验证。

### 5.1 已有测试目标（`xmake.lua`，全部 `set_default(false)`）

| 目标 | 行 | 链接内容 | 与客户端身份的关系 |
| --- | --- | --- | --- |
| `ol_transport_lifecycle_tests` | 326 | `game_server_core` + `TransportLifecycleTests.cpp` | **无关**（真 socket 回环） |
| `ol_game_server_tests` | 258 | `game_server_core` + `ServerCoreTests.cpp` | **无关**（内存协议/fixture） |
| `ol_dedicated_control_tests` | 285 | `src/shared/*` + 测试 | **无关** |
| `ol_lua_runtime_tests` | 311 | `game_server_core` + `LuaRuntimeTests.cpp` | **无关** |
| `ol_backend_tests` | 245 | `backend_core` + 测试 | **无关**（Demonware 服务端侧） |
| `ol_playerdata_def_tests` | 272 | `PlayerDataDef.cpp` + 测试 | **无关** |
| `ol_localnetworking_tests` | 339 | localnetworking | **无关**（本机 socket 桥） |
| `ol_platformwrapper_tests` | 367 | platformwrapper | **无关** |
| `ol_archived_tls_probe` | 384 | probe | **无关** |
| `ol_localnetworking_fixture` | 357 | fixture 插件 | **无关** |
| `ol_deploy` | 214 | **`set_default(true)`** | **危险**：会自动调用 `InstallCodolRuntime.ps1` 部署到 `config/codol-game-dir.txt` 指定的目录 |

> ⚠️ **构建纪律**：`ol_deploy` 是**默认目标**，且 `config/codol-game-dir.txt` 非空（内容 `D:\codo_3.19.26.13_fresh\CoD Online`，该目录**不存在**）。任何裸 `xmake` / `xmake build` 都会尝试部署。**必须显式命名目标。**

### 5.2 可立即推进的任务（按"零客户端依赖"排序）

| # | 任务 | 为什么现在能做 | 需要的授权 |
| --- | --- | --- | --- |
| **C-1** | **T-1 最小修复**（见 §6）：`stop()` 后端口实际释放的证明、`lastSocketError` 清除语义、合成哨兵与真实错误码分离、析构资源清理 | 纯离线、回环 socket、已有 106 断言基础 | 改源码需授权；仅"先出差异方案"不需授权 |
| **C-2** | **9 个插件专属文件的边界测试目标**（导出面/生命周期冒烟） | 该缺口与客户端身份**无关**：它验证的是"我们的插件导出与守卫逻辑"，可在无宿主时对空/伪模块运行 | 新增 `xmake` target + 测试文件需授权 |
| **C-3** | **preflight 反例回归**（`mp_fake.ff` 必须不再获得 `ASSET_SET_VERIFIED`） | 收紧补丁**已在 HEAD `f0d1b82` 落地**（schemaVersion 2 已含 `game.map_sizes`/`game.map_completeness`/`game.build_association`）；需要的是**回归测试**而非新功能 | 新增测试需授权 |
| **C-4** | **协议序列化/解析的固定向量测试**（DTLS / netchan / usercmd delta / gamestate writer） | 已有 fixture；且这些**捕获字节来自我们实际运行的客户端**（见 §5.3），与 O-1 无关 | 新增测试需授权 |
| **C-5** | **后端业务逻辑测试**（Auth3/LSG/Matchmaking/Booking/Storage2/Marketplace） | 全部为服务端侧实现，`ol_backend_tests` 已存在 | 新增测试需授权 |
| **C-6** | **离线绑定重放工具**（把 `bind()` 的门禁与 82 处前缀守卫对一个给定 PE 文件离线重放） | `verify-bindings.py` **在本树不存在**（见 §5.4）。补上它，就能在不启动客户端的前提下对 O-3 的**磁盘文件**做一次判定——预期会失败（加壳），但可建立工具与基线 | 新增工具需授权 |
| **C-7** | **可追溯性**：把构建产物、日志、工作树、HEAD 绑定成一份机器可读清单 | 纯文档/脚本，无客户端依赖 | 低 |
| **C-8** | **文档修订**（见 §8） | 纯文本 | 需批准（不批量改写） |

### 5.3 一个被低估的重要事实：协议证据来自**我们实际运行的客户端**

[SOURCE_FEASIBILITY_2026-10-09.md](<F:/桌面/ol/ol-mod-olfinal/.agents/audits/2026-10-09/SOURCE_FEASIBILITY_2026-10-09.md>) §3 记录：

> DTLS 与 getchallenge 为**捕获字节 CONFIRMED**
> 首个包 XOR 布局与 **EOF=5（3.3.3.3 为 6）** 已由捕获字节 CONFIRMED

**含义**：服务端协议层的若干关键常量**不是**从 `out.exe` 推导的，而是从**实机抓包**得到的，并且该抓包明确区分了 3.3.3.3（EOF=6）与我们实际运行的客户端（EOF=5）。因此：

- 协议层工作**本来就以真实客户端为准**，与 `out.exe` 是否到手**无关**；
- 这进一步证明"缺 `out.exe` ⇒ 全部服务端工作受阻"的说法不成立。

### 5.4 本树缺失的离线工具（登记）

git `55fcdbf` 与 `CodolClientPatches.cpp:41-44` 引用了两个**不在本树**的工具：

| 工具 | 引用处 | 本树状态 |
| --- | --- | --- |
| `verify-bindings.py` | git `55fcdbf`（"replays bind()'s own gate and all 66 std::equal guards against out.exe offline"） | **不存在**（已在 `tools/src/tests/docs/distribution` 递归检索，0 命中） |
| `Tools/olfinal/import-signature.py` | `CodolClientPatches.cpp:41` | **不存在**（同上） |
| `Tools/olfinal/check-auth3-patches.py` | `Auth3ClientPatches.cpp:110` | **不存在**（同上） |

按 [SOURCE_FEASIBILITY_2026-10-09.md](<F:/桌面/ol/ol-mod-olfinal/.agents/audits/2026-10-09/SOURCE_FEASIBILITY_2026-10-09.md>) §9 第 6 项，它们属于**不在本机**的 `CODOL-main` 交接仓库。这构成 **C-6** 的动机。

---

## 6. T-1 当前状态及最小后续修复建议

### 6.1 状态复核方式：**字节同一性**（本轮未重新构建/运行）

本轮**没有**重新构建或运行 T-1（遵守 §七 的只读边界）。改用更强的证明方式：**五个相关文件的 SHA-256 与上一轮产出 `checks=106 failures=0` 时逐字相同**。

| 文件 | 本轮实测 SHA-256 | 与上轮一致 |
| --- | --- | --- |
| `src/game_server/server_mp/sv_network_mp.cpp` | `AF93F7C8EEDE4E4C4417835F73D943544D906A7E1F3C5FBA9892CB82EEC58AA6` | ✅ |
| `src/game_server/server_mp/sv_network_mp.hpp` | `A5BBE54734A1F7DBB675F73CF1BAE4BC420C38B6E39A1D48B64EC67047F40915` | ✅ |
| `src/game_server/win32/win_net.cpp` | `3A34D953D2A7A4830D99FF77988A2C791AAB36F968049906F06B832EABAA9A14` | ✅ |
| `src/game_server/win32/win_net.hpp` | `8F0FF3189887660DEBB968C6CFF1E055CF065951E82E72F2E2ECF71451F5FBC1` | ✅ |
| `tests/game_server/TransportLifecycleTests.cpp` | `FA6A2760B73BBE52B377178C10BAA64390ADC43522A97D455070DE79DBE7DE94` | ✅ |
| 产物 `build/bin/release/ol_transport_lifecycle_tests.exe` | `4BE2180D1856DB6A8CF1BBD831001BE8C059E2A519582A5DAED99BE7E5A18468`（3,826,176 B，2026-10-10 11:58:29） | ✅ |

**结论**：源码与测试**零字节变化** ⇒ 上轮的 `106/0` 结果与下列缺陷**同时仍然有效**。

### 6.2 已知问题是否仍然存在 —— 逐项复核

| # | 问题 | 是否仍存在 | 本轮只读证据 |
| --- | --- | --- | --- |
| **FF-1** | **无任何用例证明 `stop()` 后 OS 层端口绑定真的释放** | ✅ **仍存在** | 测试中所有 `NET_IPSocket` 调用都是 `(0, …)`（临时端口）：`:348`、`:366`、`:371`、`:479`、`:520`。`[6/8]` 用 `start(0)` 重绑，OS 可给出**另一个**临时端口 ⇒ 不构成释放证明 |
| **FF-3** | **`lastSocketError` 清除语义与文档不符** | ✅ **仍存在** | `sv_network_mp.cpp` 的两条"已打开 + 成功"早退路径直接 `return true;`（`:31`、`:49`），全函数**没有** `lastSocketError = 0;`；而 `sv_network_mp.hpp:69` 仍写 `cleared by the next successful start()` |
| **FF-6** | **合成哨兵与真实 Winsock 错误共用同一 `int` 字段** | ✅ **仍存在** | `win_net.hpp:27` `inline constexpr int SocketAlreadyBoundError = 10037;`（`WSAEALREADY`），注释在 `:26` 自称由 `static_assert` 锁定；而真实端口冲突由 OS 报 `10048`（`WSAEADDRINUSE`，见既有运行日志 `error=10048`） |
| **FF-7** | **析构忽略 `close()` 失败** | ✅ **仍存在** | `win_net.cpp:48-51` `NetUdpSocket::~NetUdpSocket() { close(); }` —— `close()` 返回 `bool` 却被丢弃；失败路径会提前 `return false`，从而**跳过 `WSACleanup()`** 并保留句柄 |
| **FF-2** | close 失败分支只由 IAT 伪造覆盖 | ✅ 仍存在（已在测试注释中诚实披露） | `TransportLifecycleTests.cpp:45-52` 的 `// SIMULATED FAILURE` 说明块 |

### 6.3 最小修复建议（**本轮未实施**；需授权）

> 以下每项都给出**具体文件、预期差异、测试方式**。**未获授权前不修改正式源码。**

| 针对 | 文件 | 预期差异（最小） | 测试方式 |
| --- | --- | --- | --- |
| **FF-1** | 仅 `tests/game_server/TransportLifecycleTests.cpp` | 在 `[4/8]`/`[6/8]` 中记录 `stop()` 前的 `status().port`；`stop()` 后用**新的** `NetUdpSocket` 尝试 `NET_IPSocket(<该端口>, LoopbackIpv4)`，断言 probe 成功。若旧绑定未释放，OS 会以 `WSAEADDRINUSE` 拒绝该 bind | 重跑 `ol_transport_lifecycle_tests`；期望断言数 106 → 约 109-110，`failures=0`。**反例校验**：故意在实现里把 `stop()` 改成只清状态不 close，该用例必须 FAIL |
| **FF-3** | 二选一：**(a)** `src/game_server/server_mp/sv_network_mp.cpp`（2 行）在 `:30-31` 与 `:48-49` 的成功早退前补 `status_.lastSocketError = 0;`；**(b)** 仅改 `sv_network_mp.hpp:66-69` 的措辞为"仅在真正重新绑定成功时清除" | (a) 改实现 2 行；(b) 只改注释 | (a)：在 `[A-1]` 中补一条 `lastSocketError == 0` 断言；`[7/8]` 的粘性错误断言不得受影响。(b)：无需改测试 |
| **FF-6** | `src/game_server/win32/win_net.hpp`（常量值）+ `sv_network_mp.cpp`（3 处赋值）+ 测试（3 处断言） | 把哨兵移出 Winsock 错误空间（例如私有值 `0x4F4C4D42`），或新增独立字段 `lastConflict` | 重跑；`[3/8]`/`[7/8]`/`[A-1]` 断言改为新常量。**注意**：这是**语义清理**，不得改变 `start()` 的拒绝行为 |
| **FF-7** | `src/game_server/win32/win_net.cpp`（1-4 行） | 析构中显式记录失败：`if (!close()) { /* 记录句柄泄漏 */ }`。**不要**在失败路径强制 `WSACleanup()`——那会与"保留句柄以便重试"的语义冲突，需先裁定优先级 | 需一条"析构时 close 失败"的注入用例（可复用 P1 的 IAT 机制），或至少一条静态断言/注释 |

**强制约束（任何修复都必须保持）**：
- 生产调用点的**无参数调用语义**：`Appmain.cpp:2096`、`:8178` 的 `Network.start()` 仍等价于 `start(28960, 0)`。
- **默认绑定地址行为**：`AnyIpv4Address == 0 == INADDR_ANY`。
- **正式协议常量与网络数据格式**：DTLS/netchan/usercmd/gamestate 的任何常量不得触碰。
- **ABI / RVA / 固定启动链 / S2-S3 默认值**：`EngineBindings`、`ClientProcessPatches`、`DedicatedProcessPatches`、`CodolClientPatches`、`Auth3ClientPatches` 的常量与守卫**一个字节都不动**。

---

## 7. 实际全加密客户端后续验证所需的证据清单

**前置条件（全部）**：显式授权（§七 的 D 类）。

| ID | 证据 | 为什么需要 | 采集方式（授权后） | 本轮可否离线取得 |
| --- | --- | --- | --- | --- |
| **E-1** | **O-3 文件身份**：完整 SHA-256 + 字节数 + 来源说明 | 建立"我们实际运行的对象"的身份记录（当前只有哈希，无用户来源说明） | `Get-FileHash`（已可只读执行） | ✅ **已取得哈希**；缺"来源说明" |
| **E-2** | **O-4 运行时 PE 头**：进程内 `GetModuleHandleW(nullptr)` 的 `TimeDateStamp` / `SizeOfImage` / `Machine` / 段表 | **区分 §4.3 的情形 α / β**，决定 G-A1 是否适用于本客户端 | 授权后在客户端进程内只读读取自身模块头（**不读他人内存**） | ❌ 需启动客户端 |
| **E-3** | **O-4 的 RVA 字节**：`0x0FEA20` 与 `0x8371A` 在**运行时映像**中的 8/5 字节 | 判定 G-A2 的前缀守卫是否成立；这是**真正的正确性判据** | 同上 | ❌ |
| **E-4** | **插件加载证据**：`Ayria\Logs\CodolGameServer.log` 出现 `client frame hook installed`（而非 `failed`） | 判定 G-D1（加载与调用约定） | 启动后只读日志文件 | ❌ 当前沙箱 `E:\CODOL_SANDBOX\RUN001\Ayria\` **没有 `Logs` 目录** |
| **E-5** | **绑定结果**：`EngineBindings::bind()` 的成功/失败，以及失败发生在哪一阶段 | 判定 G-A1/G-A2/G-A3 | 插件日志（`engine binding validation failed stage=…`） | ❌ |
| **E-6** | **后端补丁结果**：`CodolClientPatches::install()` 返回 false 是"预期降级"还是"新缺陷" | 判定 G-B1 的降级是否可接受 | 插件日志 + 客户端能否到达 loadout | ❌ |
| **E-7** | **Auth3 三处签名定位结果** | 判定 G-C1（这是真实玩家登录路径，历史故障点） | 插件日志 | ❌ |
| **E-8** | **地图资产**：≥1 个真实地图 `.ff` + 与 O-3 同安装的关联声明 | 世界加载 | 用户提供 | ❌ 当前 0 个地图 |
| **E-9** | **对局链路**：connect → gamestate → snapshot → 双客户端 | 实机验收 | 授权后 | ❌ |

**关键**：**E-2/E-3 是全部实机验收的"第一道闸"**，也是本轮**唯一**能澄清"我们的客户端是否满足现有门禁"的证据。在它们到手之前，**不得**对门禁做任何修改。

---

## 8. 文档修订建议（最小；**本轮未改写任何文档**）

### 8.1 建议修订项（逐条给出原文 / 证据 / 建议）

| # | 文件:行 | 原文（摘录） | 证据 | 建议修订（最小） |
| --- | --- | --- | --- | --- |
| **D-1** | [ARTIFACT_REQUIREMENTS.md](<F:/桌面/ol/ol-mod-olfinal/.agents/audits/2026-10-09/ARTIFACT_REQUIREMENTS.md>) §A 第 9 行 | `**需要**：OLFinal **unpacked** \`out.exe\`（或其明确来源 + 完整 SHA-256）。` | 启动链默认目标是 `codoMP_client_shipRetail.exe`（`CodolGame.py:28`）；`Auth3ClientPatches.cpp:138-139` 已并列接受两者 | 改为："**A. 历史逆向来源对象（非运行前置）**"；并在文件开头加一句"本文件描述**离线逆向复核**所需工件，**不**构成本项目运行全加密客户端的强制输入" |
| **D-2** | 同上 §E 第 109 行 | `1. OLFinal unpacked \`out.exe\` **或其来源 + 完整 SHA-256**` | 同上 | 把该条从"最小集**必需**"移到"可选（仅当使用 O-1 派生的 RVA/前缀时）" |
| **D-3** | [GOLDEN_COPY_SPEC.md](<F:/桌面/ol/ol-mod-olfinal/.agents/audits/2026-10-09/GOLDEN_COPY_SPEC.md>) G1 第 29 行 | `G1. 客户端 EXE SHA-256 == E3823FD6…（或明确记录为另一构建并同时记录该构建哈希）。` | 该哈希归属三方互斥（§2.1 O-5）；同文件第 48 行又把 `out.exe` 单列 | 把 G1 拆成两条：**G1a 文件身份**（"本次运行实际加载的客户端文件 SHA-256，实测记录"）、**G1b 运行时映像身份**（"进程内 PE 头 + 关键 RVA 字节"）。**不修改** `E3823FD6…` 字符串本身 |
| **D-4** | [artifact_provenance.json](<F:/桌面/ol/ol-mod-olfinal/.agents/audits/2026-10-09/artifact_provenance.json>) `requiredArtifacts[0]` 第 7-13 行 | `"id": "A", "artifact": "OLFinal unpacked out.exe", "status": "NOT_FOUND"` | 同上 | 把 `"id": "A"` 的语义从 `requiredArtifact` 改为 `researchSample`（或新增 `"class": "reverse-engineering-source"` 字段）。**不改 `status`**（它确实 NOT_FOUND） |
| **D-5** | [SOURCE_FEASIBILITY_2026-10-09.md](<F:/桌面/ol/ol-mod-olfinal/.agents/audits/2026-10-09/SOURCE_FEASIBILITY_2026-10-09.md>) §11 Q2 / Q5 | `它是**唯一的根依赖**` / `在它到手之前，任何构建、抓包、Golden 或运行时验证都无法产生可信证据` | §5.1 的 10 个测试目标均与客户端身份无关；§5.3 协议常量来自实机抓包 | 改为："它是**引擎绑定层**的根依赖，**不是**服务端开发或离线测试的根依赖"；Q5 改为"唯一最高优先级 = 取得 O-4 运行时证据（或授权离线解壳）" |
| **D-6** | [EngineBindings.hpp](<F:/桌面/ol/ol-mod-olfinal/src/game_server/EngineBindings.hpp>) 第 434-435 行 | `// OLMOD(engine-binding-catalog): fixed identity and DB/qcommon/CCS` `// entry points for the 0x57611E31, 0x0C72A000 CODOL executable only.` | `0x57611E31`/`0x0C72A000` 是 **O-2（3.3.3.3）** 的常量，定义在 `backend/Demonware/CodolClientPatches.cpp:45-46`；本文件自己的常量在 `:438-439` 是 `0x6096930A`/`0x0E5D6000` | 更正注释为 `for the 0x6096930A, 0x0E5D6000 (build 1649370) host`，并注明旧值属 3.3.3.3。**只改注释，不动常量** |
| **D-7** | [CodolGame.py](<F:/桌面/ol/ol-mod-olfinal/tools/runtime/CodolGame.py>) 第 22-27 行 | `3.3.3.3 ships codoMP_client_shipRetail.exe, and the OLfinal bring-up runs out.exe (build 1649370)…` | **本机实测**：名为 `codoMP_client_shipRetail.exe` 的文件其 `FileVersion=1649370`、`TimeDateStamp=0x6096930A`（= O-1 的期望值） | 加一段"**实测更正**"：本机该文件名为零售名、但携带 1649370 的身份标记；"文件名 ≠ 构建"已在本仓库被证明过一次（`Auth3ClientPatches.cpp:103-119`）。**不改 `TARGET_NAME` 默认值**（会破坏 3.3.3.3 调用的字节同一性） |
| **D-8** | [codol-preflight.ps1](<F:/桌面/ol/ol-mod-olfinal/codol-preflight.ps1>) 第 20 行 | `[string] $ExpectedClientSha256 = ""` | 脚本本身**没有**硬编码 `E3823FD6…`（好设计） | 在参数帮助中写明：该参数是"**你实际运行的那个客户端**的已批准 SHA-256"，**不是**隐含 `out.exe`。无需改逻辑 |

**本轮不改写任何文件**；上表是待批准的修订方案。

### 8.2 `E3823FD6…` 的角色冲突（**单独登记，不裁定**）

| 来源 | 断言 |
| --- | --- |
| `GOLDEN_COPY_SPEC.md:29` | 该哈希是 Golden Copy 要求的"**客户端 EXE**" |
| `artifact_provenance.json:9` | 该哈希的对象是 "**OLFinal unpacked `out.exe`**" |
| **本任务指令（§六.2 / §五.5）** | 该哈希**属于 3.3.3.3 QA 客户端**，不得默认用作 OLfinal 目标哈希 |

三者互斥。**本轮不采用、不裁定、不重写**；登记为 **B-5**。解除条件：用户显式说明其归属，或提供对应制品本体做哈希复核。

### 8.3 对象标注规则（建议采用）

对仓库内每个 RVA / 机器码前缀 / PE 字段 / 哈希，建议在注释或目录中标注**来源对象**，取值域固定为：

```text
[SRC-O1]  源自历史去壳样本 out.exe (044c396c…, build 1649370) —— 需运行时复核
[SRC-O2]  源自 3.3.3.3 QA 客户端 (0x57611E31 / 0x0C72A000) —— 不得套用到本客户端
[SRC-O3]  实测自全加密零售客户端 (36997674…)
[SRC-O4]  实测自运行时映像（进程内） —— 最高可信度
[SRC-WIRE]源自实机抓包字节（如 EOF=5） —— 与 PE 身份无关
```

**禁止**：把 `[SRC-O1]`/`[SRC-O2]` 的地址直接当作 `[SRC-O4]` 的事实；**禁止**通过修改期望哈希/RVA/前缀来消除门禁失败。

---

## 9. 本轮实际执行与未执行事项

### 9.1 已执行（全部只读）

| 动作 | 对象 |
| --- | --- |
| 记录基线 | F 的 HEAD/branch/status/13 个关键文件 SHA-256 |
| 源码审查 | `EngineBindings.{hpp,cpp}`、`ClientProcessPatches.cpp`、`DedicatedProcessPatches.cpp`、`CodolClientPatches.cpp`、`Auth3ClientPatches.cpp`、`FrameHook.{hpp,cpp}`、`sv_network_mp.{hpp,cpp}`、`win_net.{hpp,cpp}`、`Appmain.cpp`（局部） |
| 文档审查 | `GOLDEN_COPY_SPEC.md`、`artifact_provenance.json`、`ARTIFACT_REQUIREMENTS.md`、`SOURCE_FEASIBILITY_2026-10-09.md`、`CodolGame.py`、`codol-preflight.ps1`、`xmake.lua` |
| Git 溯源 | `55fcdbf`（host gate 翻转）、`96b6fb1`（Auth3 名字门禁修正）、`f0d1b82`（preflight 收紧） |
| 制品只读核验 | O-3 的 `E:\CODOL_SANDBOX\RUN001\` 与 `D:\…\COD OL\` 两份副本：大小/SHA-256/PE 头/段表/FileVersion；RVA `0x0FEA20`、`0x8371A` 的磁盘字节 |
| 日志核验 | 搜索 `client frame hook installed` / `engine binding validation failed` / `unsupported host`：**0 命中**（仅有计划文本）；确认沙箱 `Ayria\` 下**无 `Logs` 目录** |
| T-1 状态复核 | 5 个文件 SHA-256 与上轮逐字一致；4 项缺陷逐条重新定位 |
| 工具存在性 | `verify-bindings.py` / `import-signature.py` / `check-auth3-patches.py` 在本树 **0 命中** |

### 9.2 未执行（严格遵守 §七）

| 禁止项 | 状态 |
| --- | --- |
| 启动全加密客户端 / 房间进程 / 专用服务进程 | **未执行** |
| 运行 `Injector32` / DLL 注入 | **未执行** |
| 读取或修改游戏进程内存 | **未执行** |
| 修改正式启动链 / ABI / RVA / 机器码前缀 / 协议常量 | **未执行**（`EngineBindings` 等常量零字节改动） |
| 下载 / 替换 / 自行获取客户端制品 | **未执行** |
| 运行正式部署（含 `ol_deploy`） | **未执行** |
| 自动合并 F 与 D | **未执行** |
| Git 提交 / 推送 / reset / rebase / amend / clean | **未执行** |
| **构建**（含 `xmake build`） | **未执行**（本轮刻意不构建，改用字节同一性证明 T-1 状态） |
| **运行测试**（含 `ol_transport_lifecycle_tests`） | **未执行**（同上） |

### 9.3 唯一写入

| 位置 | 内容 |
| --- | --- |
| `WS\FULL_ENCRYPTED_CLIENT_TARGET_ADJUDICATION.md` | 本文件 |
| `WS\NEXT_PHASE_PLAN.md` | 后续路线 |

**F 与 D 的受版本控制文件：0 字节改动**（`git status` 9 条 / 6 条，与轮次开始时逐行一致）。

---

## 10. 文件哈希、日志与证据引用

### 10.1 基线（F，本轮实测）

| 项 | 值 |
| --- | --- |
| HEAD | `2a75bdd8872bb9f54006382a924c3006ec9affc2` |
| 分支 | `OLfinal-live` |
| `git status --porcelain` 条数 | **9**（8 M + 1 ??） |
| `EngineBindings.hpp` | `9ACE87313419DB58DC41EE6F4F38612A0970525BAF24CBF924462AD1BA88C72E`（126,514 B） |
| `EngineBindings.cpp` | `E624A8A1AFF2BB59F57CCD1D37BF1FD609D0573FFD505DB5BD6CD32C3E07465B`（871,806 B） |
| `ClientProcessPatches.cpp` | `E81D760A6B362076C346471EAC89F6841BF43B369BDA360E5E9180378C09B885`（77,535 B） |
| `FrameHook.cpp` | `1CA962D707F23DA40F60878DB5A8542601BA68398FE4EA226D0F957BE8008D8A`（3,683 B） |
| `FrameHook.hpp` | `6EDF4F9A21511468E99B779FE64BE5EA6B637F1E6AE24F91362013AA1EF5ACF5`（1,213 B） |
| `Appmain.cpp` | `407B6F9896A5F0354625B9D0724A3519BA4ACEDDFC36BA34CE879F79100BE7B1`（481,281 B） |
| `sv_network_mp.cpp` | `AF93F7C8EEDE4E4C4417835F73D943544D906A7E1F3C5FBA9892CB82EEC58AA6`（6,941 B） |
| `sv_network_mp.hpp` | `A5BBE54734A1F7DBB675F73CF1BAE4BC420C38B6E39A1D48B64EC67047F40915`（4,357 B） |
| `win_net.cpp` | `3A34D953D2A7A4830D99FF77988A2C791AAB36F968049906F06B832EABAA9A14`（9,054 B） |
| `win_net.hpp` | `8F0FF3189887660DEBB968C6CFF1E055CF065951E82E72F2E2ECF71451F5FBC1`（2,642 B） |
| `TransportLifecycleTests.cpp` | `FA6A2760B73BBE52B377178C10BAA64390ADC43522A97D455070DE79DBE7DE94`（27,504 B） |
| `codol-preflight.ps1` | `4FB3C2B9E4F6DE4ECB16F6FEF5F8EC5B2FC1B0F491E3F924EAFF63B4F432613B`（20,525 B） |
| `tools/runtime/CodolGame.py` | `3324CD8D256AB704899A5AAE2736F2F2E48AF968F567205CBFB5DAA3942D3E02`（39,495 B / 1,058 行） |
| `tools/reverse/annotations/out.exe.json` | `E0941A76C109403B…`（2,231 B；`target=out.exe`，`sha256=044c396c…`） |
| `tools/reverse/annotations/codoMP_client_shipRetail.exe.json` | `302F8989950DCC80…`（122,320 B；`target=codoMP_client_shipRetail.exe`，**无 sha256 字段**） |

### 10.2 O-3 只读核验结果（本轮新增）

| 项 | 值 |
| --- | --- |
| 路径 1 | `E:\CODOL_SANDBOX\RUN001\codoMP_client_shipRetail.exe` |
| 路径 2 | `D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe` |
| 大小 | 7,841,344 B（两副本一致） |
| SHA-256 | `36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537`（两副本一致） |
| mtime | 2026-09-10 00:06:54 |
| PE | `signature=0x00004550`、`magic=0x010B`(PE32)、`machine=0x014C`(x86)、7 段 |
| `TimeDateStamp` | `0x6096930A`（2021-05-08 13:32:58 UTC） |
| `SizeOfImage` | `0x0E659000` |
| `SizeOfHeaders` / `CheckSum` | `0x00001000` / `0x0078840D` |
| 段表 | `.tp3`(0x008A689A@0x00001000)、`.tp3`(0x0016DA70@0x008A8000)、`.tp3`(0x0DBB1CC0@0x00A16000)、`.tp3`(0x31@0x0E5C8000)、`.tp3`(0x9228@0x0E5C9000)、`.tvm0`(0x4000@0x0E5D3000)、`.tp3`(0x82000@0x0E5D7000) |
| `FileVersion` / `ProductVersion` | `1649370` / `1649370` |
| `FileDescription` | `Call of Duty Online` |
| RVA `0x0FEA20` 磁盘字节 | `03 C1 E0 06 50`（期望 `55 8B EC 56 57`，**不匹配**） |
| RVA `0x8371A` 磁盘字节 | `00 D9 45 10 8B 4D 08 8B`（期望 `83 7C 24 08 01 0F 94 C0`，**不匹配**） |
| 核验方法 | `[System.IO.File]::Open(..., FileAccess::Read, FileShare::ReadWrite)` + `BinaryReader`；`e_lfanew`@0x3C → `IMAGE_NT_HEADERS`；段表映射 RVA→文件偏移 |

> **不得**把上面两个"不匹配"解读为身份判负：O-3 是**加壳**映像，代码字节必然被替换。**同样不得**把 `TimeDateStamp` 相同解读为身份确认。

### 10.3 证据引用

| 类别 | 路径 |
| --- | --- |
| 身份门禁（引擎） | `F:\…\src\game_server\EngineBindings.hpp:438-440` · `EngineBindings.cpp:3647-3667`（`bind()`）、`:755-757`（`ComFramePrefix`）、`:3744`（守卫点）、`:4156-4165`（静默错调风险注释） |
| 身份门禁（客户端补丁） | `src\game_server\ClientProcessPatches.cpp:201-215`（`UnsignedFastfileVerificationRva=0x8371A`）、`:548-551`（宿主检查） |
| 身份门禁（专用进程） | `src\game_server\DedicatedProcessPatches.cpp:460-461,681-682` |
| 身份门禁（后端，O-2） | `src\backend\Demonware\CodolClientPatches.cpp:30-46,596-616` |
| 已修正的名字门禁（先例） | `src\backend\Demonware\Auth3ClientPatches.cpp:103-119,136-140,142-158` |
| 启动链 | `tools\runtime\CodolGame.py:22-31,47-103,280-319,368-382` |
| 预检 | `codol-preflight.ps1:88-112`（client 门禁）、`:114-163`（asset 门禁）、`:165-215`（toolchain）、`:217-233`（令牌与 verdict） |
| 构建目标 | `xmake.lua:92-117`（core/headers）、`:191-213`（`ol_game_server` 的 9 个专属文件）、`:214-244`（`ol_deploy`，`set_default(true)`） |
| Git 历史 | `55fcdbf`（`target out.exe (build 1649370): flip the host gate, the RVAs and the prefixes together`）、`96b6fb1`（`backend: Auth3 refused to patch out.exe over a hardcoded 3.3.3.3 filename`）、`f0d1b82`（`fix(preflight): require real evidence for ASSET_SET_VERIFIED and TOOLCHAIN_READY; add counterexample tests`） |
| T-1 上轮证据 | `D:\…\使命召唤OL\_batch10_evidence\T1_rerun_forced.log`（`checks=106 failures=0`）、`T1_rerun.log`、`diff_T1tests_F_vs_D.patch` |
| 前轮交付 | [BASELINE_ADJUDICATION.md](BASELINE_ADJUDICATION.md) · [T1_DIFF_REVIEW.md](T1_DIFF_REVIEW.md) · [T1_ACCEPTANCE_REPORT.md](T1_ACCEPTANCE_REPORT.md) · [ARTIFACT_BLOCKERS.md](ARTIFACT_BLOCKERS.md) · [FILE_OWNERSHIP_MANIFEST.md](FILE_OWNERSHIP_MANIFEST.md) |

---

## 11. 任务 §三 六问的直接回答

**Q1. 哪些身份和地址记录只适用于学习文档中的 `out.exe`？**
`EngineBindings.hpp:438-440` 的 `ExpectedTimestamp=0x6096930A`、`ExpectedImageSize=0x0E5D6000`、`ComFrameRva=0x0FEA20`，以及该文件全部 **145 个 `*Rva`** 与 `EngineBindings.cpp` 的 **82 处 `std::equal` 前缀**；`ClientProcessPatches.cpp` 的 **25 个 RVA**（含 `UnsignedFastfileVerificationRva=0x8371A`）；`DedicatedProcessPatches.cpp` 的补丁点；`tools/reverse/annotations/out.exe.json` 的全部注解。**它们的来源对象是 O-1，适用范围是"运行时映像中按同样布局存在的代码"——需要 O-4 证据才能确认。**

**Q2. 哪些哈希和工具明确针对 3.3.3.3 QA 客户端？**
哈希：无独立哈希记录（只有 PE 身份 `0x57611E31` / `0x0C72A000`）。工具/常量：`backend/Demonware/CodolClientPatches.cpp:45-58` 的 `CodolTimestamp`/`CodolImageSize` 与 **8 个 RVA**（`ProfileCompletionRva` … `CurrentCharacterCacheRva`），其注释明确说"**未随翻转移植**"。另有 `EngineBindings.cpp:3973-3974, 4164-4165` 引用 `CodolWeaponResolve.py:0x1945B0`，标注为"targets codoMP_client_shipRetail.exe -- **3.3.3.3**"（该工具不在本树）。

**Q3. 哪些启动逻辑和服务端代码与客户端具体 PE 身份无关？**
- 启动链的**编排**部分：`CodolGame.py` 的目录解析（`:47-103`，按"是否含客户端 exe"识别安装）、`launch_arguments`（`:280-294`）、`process_environment`（`:297-319`）、`validate_launch_files`（`:368-382`）——它们只要求"存在客户端 exe + Injector32 + Bootstrapper32 + 3 个插件"。
- **全部 10 个离线测试目标**（§5.1）与其被测代码：`qcommon/`（DTLS/netchan/msg）、`server_mp/`（快照/gamestate/usercmd/Pmove/伤害/规则）、`shared/`（DedicatedControl/Session/Playlist/RuntimeLog）、`backend/`（Auth3/LSG/Matchmaking/Booking/Storage2/Marketplace 的**服务端侧**）、`localnetworking`、`platformwrapper`、`client_bridge`。
- 协议常量中**来自实机抓包**的部分（如 netchan 首包 XOR 布局、`EOF=5`）。

**Q4. 哪些绑定、补丁和 Hook 必须依赖真实客户端的运行时映像？**
- `EngineBindings::bind()` 全部（身份门禁 + 145 RVA + 82 前缀）；
- `ClientProcessPatches`（含 `0x8371A` 的 `cmp [esp+8],1; sete al` 8 字节）、`ClientAnimtreeHook`、`ClientRenderFrameHook`、`DisconnectWitness`；
- `DedicatedProcessPatches` 的 14 个补丁点；
- `FrameHook::installFrameHook`（写 `ComFrameRva` 的 `0xE9` 跳转）；
- 后端 `CodolClientPatches`（8 个客户端钩子）与 `Auth3ClientPatches`（3 处签名定位）。
**它们的共同前提都是"在目标映像中定位到预期字节"——只能由 O-4 证据确认。**

**Q5. 当前 B1 的阻断条件中，哪些错误继承了学习文档的目标假设，哪些是真正的运行时安全条件？**
- **错误继承**：①"必须取得 `out.exe` 本体"；②"用 `044c396c…` 对本体复核"作为**项目级**门禁；③"磁盘 `SizeOfImage=0x0E659000 ≠ 0x0E5D6000` ⇒ 宿主身份不匹配"。
- **真正的运行时安全条件**：④ RVA/前缀必须对**运行时映像**成立；⑤ 插件加载与调用约定；⑥ 真实对局链路；⑦ `E3823FD6…` 的归属冲突（未裁定，不等于可忽略）。
- **需重述**：⑧"加壳件 vs 去壳件等价性"应改为"O-3 运行时映像是否满足 G-A1/G-A2"。

**Q6. 项目目前是否有足够证据识别实际全加密客户端的构建与运行时映像？如果没有，缺什么证据？**
**没有。** 现有证据只覆盖**磁盘文件**（O-3：SHA-256、大小、PE 头、段表、FileVersion）。**完全缺失 O-4（运行时映像）**：无进程内 PE 头、无 RVA 字节、无插件加载日志、无绑定结果日志。具体缺失清单见 §7（E-2/E-3 为第一道闸）。此外还缺 **O-3 的来源说明**（E-1 只完成了哈希）。

---

## 12. 关联交付

- [NEXT_PHASE_PLAN.md](NEXT_PHASE_PLAN.md) — 按优先级与授权边界排列的后续路线
- [BASELINE_ADJUDICATION.md](BASELINE_ADJUDICATION.md) · [T1_DIFF_REVIEW.md](T1_DIFF_REVIEW.md) · [T1_ACCEPTANCE_REPORT.md](T1_ACCEPTANCE_REPORT.md) · [ARTIFACT_BLOCKERS.md](ARTIFACT_BLOCKERS.md) · [FILE_OWNERSHIP_MANIFEST.md](FILE_OWNERSHIP_MANIFEST.md)
