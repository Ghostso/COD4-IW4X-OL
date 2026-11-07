# COMBAT_P1_ARTIFACT_CONSISTENCY — 源码 / 构建产物 / 沙箱部署 DLL 一致性核验

**任务**：COMBAT-P1（阶段一：只读核验）
**日期**：2026-10-11
**性质**：**只读**。未构建、未部署、未启动/附加/注入/终止任何进程、未读进程内存、未改源码或冻结基线、未在 F 与 D 之间复制文件。
**配套**：`COMBAT_P1_RUNTIME_SAMPLING_PLAN.md`、`COMBAT_P1_DECISION_MATRIX.json`、`COMBAT_P1_SHA256_MANIFEST.txt`。

**证据分级（全篇使用）**
- `[直读]` 本轮直接读取的原始载体（文件字节、PE 头、构建日志、manifest、git 对象）
- `[转引]` 历史报告转引
- `[推断]` 由前述证据得出的推断（附反证条件）
- `[未知]` 无法判定
- `[需授权]` 需用户单独授权才能执行的下一步

---

## 0. 结论速览

| # | 比较对象 | 判定 | 关键依据 |
|---|---|---|---|
| **V1** | 沙箱部署 DLL ↔ F `build\stage` DLL | **MATCH** | 字节级同一：同 SHA-256 `6D493B82…`、同尺寸 6,556,672、同 PE `TimeDateStamp` `0x6AC88076` `[直读]` |
| **V2** | 沙箱部署 DLL ↔ F 当前 `build\bin\release` DLL | **MISMATCH** | SHA-256 / 尺寸（6,556,672 ↔ 6,559,232）/ PE 时间戳（10-09 13:49:42 ↔ 10-10 12:52:50）均不同；共同前缀 **5,180,803 / 6,556,672 字节不同** `[直读]` |
| **V3** | 部署 DLL ↔ **当前工作区源码整体** | **MISMATCH** | 4 个 TU（`Appmain.cpp`、`FrameHook.cpp`、`server_mp/sv_network_mp.cpp`、`win32/win_net.cpp`，另 `FrameHook.hpp`/`win_net.hpp`/`xmake.lua`）相对 HEAD 有工作区修改，且其 `.obj` mtime 晚于部署构建 `[直读]` |
| **V4** | 部署 DLL ↔ **`bind()` 所在 TU（`EngineBindings.cpp`/`.hpp`）** | **MATCH（源码级）** | 工作区文件 **== HEAD blob**（`git hash-object` 逐字相等）；`_build_olgs.log` 证明部署构建**编译了该 TU**；其 `.obj` mtime 属于该构建且 10-10 构建**未重编** `[直读]` |
| **V5** | 部署 DLL 中 `bind()` 的**机器码** ↔ 当前源码编译结果 | **UNKNOWN** | 无 PDB（全树 0 个）、两 DLL 均**无 CodeView/RSDS**、无部署构建的 `.map`、**LTO 已启用** `[直读]+[未知]` |
| **V6** | 部署 DLL 的来源构建 | **已确定** | `_build_olgs.log`（mtime 2026-10-09 13:49:42）记录 `artifact size=6556672` / `sha256=6D493B82…`；同一日志含 87 条 `compiling.release` 与链接行 `[直读]` |

**一句话**：**部署件确实是 2026-10-09 13:49:42 的那次构建**，而**不是**当前源码树的产物；但 **`bind()` 这个翻译单元的源码与当前 HEAD 完全一致**，所以 COMBAT-P0 对"无 stage 日志 ⇒ 静默分支"的推断仍然成立；只是"部署件里 `bind()` 的机器码"在 LTO 下**无法核验**，必须保持 `UNKNOWN`。

---

## 1. 任务 A.1 — HEAD 与工作区状态

| 项 | F（活动基准） | D（冻结副本） | 证据 |
|---|---|---|---|
| HEAD | `2a75bdd8872bb9f54006382a924c3006ec9affc2` | 同 | `[直读]` `git rev-parse HEAD` |
| 分支 | `OLfinal-live` | `OLfinal-live` | `[直读]` |
| `git status --porcelain` 条数 | **17**（12 M + 5 ??） | **6**（5 M + 1 ??） | `[直读]` |

**F 的 12 个已修改文件**：`src/game_server/Appmain.cpp`、`FrameHook.cpp`、`FrameHook.hpp`、`server_mp/sv_network_mp.cpp`、`server_mp/sv_network_mp.hpp`、`win32/win_net.cpp`、`win32/win_net.hpp`、`xmake.lua`、`tools/runtime/CodolGame.py`、`tools/runtime/CodolGameServerControl.py`、`tools/runtime/CodolGameTests.py`、`tools/runtime/requirements-codol.txt`。
**F 的 5 个未跟踪文件**：`config/codol-target-build.json`、`tests/game_server/TransportLifecycleTests.cpp`、`tools/reverse/ReplayEngineBindings.py`、`tools/reverse/ReplayEngineBindingsTests.py`、`tools/runtime/CodolGameServerControlTests.py`。

**关键：`EngineBindings.cpp` 与 `EngineBindings.hpp` 不在修改列表内。** 本轮进一步用 `git hash-object`（工作区内容）与 `HEAD:<path>`（提交内容）**逐字比对** `[直读]`：

| 文件 | 工作区 blob | HEAD blob | 结论 |
|---|---|---|---|
| `src/game_server/EngineBindings.cpp` | `cc679b5db6…` | `cc679b5db6…` | **SAME-AS-HEAD** |
| `src/game_server/EngineBindings.hpp` | `e47e4590c4…` | `e47e4590c4…` | **SAME-AS-HEAD** |
| `src/game_server/Appmain.cpp` | `082b6e551f…` | `c1f6f39fb4…` | **DIFFERS-FROM-HEAD** |
| `src/game_server/FrameHook.cpp` | `b813bbeb5f…` | `856d97b86a…` | **DIFFERS-FROM-HEAD** |
| `src/game_server/server_mp/sv_network_mp.cpp` | `9353f783e3…` | `6050530965…` | **DIFFERS-FROM-HEAD** |
| `src/game_server/win32/win_net.cpp` | `0425ba2d1b…` | `8a1e576282…` | **DIFFERS-FROM-HEAD** |

> 这是 **V4** 的基础：`bind()` 所在的 TU 与 HEAD 逐字相同。

---

## 2. 任务 A.2 — 三份制品的路径 / 大小 / SHA-256 / 时间戳

| # | 制品 | 路径 | 字节 | SHA-256 | PE `TimeDateStamp`（本地） | 文件 mtime |
|---|---|---|---|---|---|---|
| A | F 当前构建产物 | `<F>\build\bin\release\CodolGameServer.Localnet32` | **6,559,232** | `DBA7273A0C9DD31CDD5619DD47B11C01EDC21AE17EEFC18FDD71F43B992097BC` | `0x6AC9C4A2` = **2026-10-10 12:52:50** | 2026-10-10 12:52:50 |
| B | F stage 产物 | `<F>\build\stage\codol\Ayria\Plugins\CodolGameServer.Localnet32` | 6,556,672 | `6D493B820E84A21B096C9914616B75DCEC488920D7AC76867049B20C5C6B2021` | `0x6AC88076` = **2026-10-09 13:49:42** | 2026-10-09 13:49:42 |
| C | **沙箱部署件** | `<E:SANDBOX/RUN001>\Ayria\Plugins\CodolGameServer.Localnet32` | 6,556,672 | `6D493B820E84A21B096C9914616B75DCEC488920D7AC76867049B20C5C6B2021` | `0x6AC88076` = 2026-10-09 13:49:42 | 2026-10-09 13:49:42 |
| D | D 冻结副本构建产物 | `<D>\build\bin\release\CodolGameServer.Localnet32` | 6,556,672 | `0EABD5F54763976CA4A92CC4C0DBB34A5CC8E60DE6EBFE4A3C6FA28A6A157971` | — | 2026-10-09 17:32:40 |

**B 与 C 逐字节相同** `[直读]`：SHA-256 相同、字节数相同、PE `TimeDateStamp` 相同、`debugDirRva` 相同（`0x005BD250`）。⇒ **V1 = MATCH**。

**PE 结构（A 与 C 对比）** `[直读]`：

| 字段 | A（当前构建） | C（部署件） |
|---|---|---|
| `Machine` | `0x014C`（x86） | `0x014C` |
| `NumberOfSections` | 5 | 5 |
| `SizeOfImage` | `0x007E0000` | `0x007E0000` |
| `CheckSum` | `0x00000000`（未设置） | `0x00000000` |
| Debug Directory → CodeView | **无**（`codeview: null`） | **无**（`codeview: null`） |
| 导出函数数 | 53 | 53 |
| 导出名集合 SHA-1 | `41B4FE7F377C1B46099D56F05B6FE0BADFA5F6A4` | **同** |

⇒ **导出面完全一致**（差异在内部，不在 ABI 表面）。

**逐节字节差异（A vs C，共同前缀 6,556,672 字节）** `[直读]`：

| 节 | raw size | 不同字节数 | 差异范围（文件偏移） |
|---|---:|---:|---|
| `.text` | 4,496,896 | 3,799,882 | `0x5E6 .. 0x44A1FF` |
| `.rdata` | 1,670,656 | 1,072,284 | `0x44A200 .. 0x5E1FF4` |
| `.data` | 162,816 | 90,826 | `0x5E2000 .. 0x609BFF` |
| `.fptable` | 512 | 467 | `0x609C00 .. 0x609DFE` |
| `.reloc` | 227,328 | 217,312 | `0x609E00 .. 0x640BFF` |
| **合计（共同前缀）** | — | **5,180,803**（首差 `0x110`，末差 `0x640BFF`） | A 另有 **2,560** 字节尾部独有 |

> 差异**不是局部**而是**全节铺开**。这与 **LTO** 一致（见第 5 节），**不能**据此断言"两个 DLL 的实现相差很多"或"相差很少"——只能断言"二进制不同"。

---

## 3. 任务 A.3 — 能否证明与同一源码版本对应

### 3.1 可用的构建/链接元数据盘点 `[直读]`

| 类别 | 找到什么 | 能否证明源码版本对应 |
|---|---|---|
| **PDB** | **全 F 构建树 0 个 `.pdb`** | **不能**（连调试符号都没有） |
| **CodeView/RSDS 调试目录** | A 与 C **均为空**（`codeview: null`） | **不能**（DLL 内不含 PDB GUID/Age，无法与任何 PDB 配对） |
| **`.map`（链接映像）** | **仅 1 份**：`<F>\build\bin\release\CodolGameServer.map`，mtime 2026-10-10 12:52:50，头部 `Timestamp is 6ac9c4a2 (Sat Oct 10 12:52:50 2026)`，覆盖 86 个 `.cpp.obj` | **只能**给当前构建（A）建立"源码→目标文件→符号地址"映射；**部署构建（C）的那份 map 已不存在** ⇒ 对 C **不能** |
| **`.exp` / `.lib`** | `CodolGameServer.exp` 10-10 12:52:32；`CodolGameServer.lib` **10-09 13:49:25** | `.lib` 的 mtime 落在**部署构建**期间；但导入库只含导出名与 DLL 名，**不含源码身份** |
| **构建日志** | `_build_olgs.log`（mtime **2026-10-09 13:49:42**，34,231 B）：含 **87 条 `compiling.release`**、`[92%] linking.release CodolGameServer.Localnet32`、`build ok, spent 44.718s`、`artifact size=6556672`、`artifact sha256=6D493B82…` | **能**证明"C 是这次构建的产物"，并**列出被编译的 TU 清单**；但日志**不含源文件内容哈希** |
| `_t1_compat.log` | mtime 2026-10-09 17:32:40；`artifact size=6556672`、`sha256=0EABD5F5…` | 说明 13:49 之后源码又变过一次（尺寸相同、哈希不同），与 D 的产物一致 |
| **目标文件（`.obj`）mtime** | `EngineBindings.cpp.obj` = **2026-10-09 13:49:21**；`sv_snapshot_mp.cpp.obj` = 13:49:21；`Appmain.cpp.obj` = **2026-10-10 12:52:31**；`sv_network_mp.cpp.obj` = 10-10 12:52:26；`FrameHook.cpp.obj` = **10-09 19:43:39**；`win_net.cpp.obj` = **10-09 19:01:49** | **能**证明哪些 TU 在部署构建时被编译、哪些后来被重编 |
| **部署清单** | `<E>\ol-mod-runtime-manifest.json`：`files=44`；插件条目 `{size:6556672, sha256:6D493B82…, source:"build/bin/release/CodolGameServer.Localnet32", kind:"rebuilt", origin:"xmake target ol_game_server"}` | **能**证明"沙箱里放的就是 6D493B82 这一份，且来源路径是构建产物目录" |
| **批准的目标构建** | `<F>\config\codol-target-build.json`（`approvedAt: 2026-10-10`）：client `36997674…B537`，plugin `6556672 / 6D493B82…` | **能**证明"当前批准的目标插件就是部署件"（注意：批准日期 10-10，**晚于**部署件构建日期 10-09） |
| **可重复构建钩子** | 未发现（无 `/Brepro`、无 `SOURCE_DATE_EPOCH`、无版本戳注入） | — |

### 3.2 部署件的来源链（**已确定**）

```
2026-10-09 13:49:xx  xmake 编译（_build_olgs.log，87 个 TU，含 [67%] EngineBindings.cpp）
2026-10-09 13:49:21  EngineBindings.cpp.obj 落盘
2026-10-09 13:49:25  CodolGameServer.lib 落盘（导入库）
2026-10-09 13:49:3x  [92%] linking.release CodolGameServer.Localnet32
2026-10-09 13:49:42  build ok, spent 44.718s -> artifact size=6556672 sha256=6D493B82...
                    +- 同一时刻：PE TimeDateStamp = 0x6AC88076
                    +- 落到 build\stage\codol\Ayria\Plugins\CodolGameServer.Localnet32
                    +- 经 overlay 部署到 E:\CODOL_SANDBOX\RUN001\Ayria\Plugins\
                       （ol-mod-runtime-manifest.json 记录 sha256=6D493B82...）
```

**判定：V6 = 部署件的来源构建已确定**（`[直读]`，非"时间戳相近"推断：日志**记录的就是该 SHA-256**）。

### 3.3 部署件与"当前源码"的对应关系

| 层次 | 结论 | 证据 |
|---|---|---|
| **整体（整个插件）** | **MISMATCH** | 4 个 TU（`Appmain`/`FrameHook`/`sv_network_mp`/`win_net`）相对 HEAD 有工作区修改；且 `Appmain.cpp.obj` 与 `sv_network_mp.cpp.obj` 的 mtime（10-10 12:52）**晚于**部署构建 ⇒ 部署 DLL 内不是这些 TU 的当前内容 |
| **`bind()` 所在 TU** | **MATCH（源码级）** | ① 工作区 `EngineBindings.cpp/.hpp` == HEAD blob；② `_build_olgs.log` 证明部署构建编译了 `EngineBindings.cpp`（`[67%]` 行）；③ 该 TU 的 `.obj` mtime = 10-09 13:49:21（属于部署构建），且 10-10 构建**未重编**（mtime 未变） |
| **部署 DLL 的 `bind()` 机器码** | **UNKNOWN** | 无 PDB / 无 CodeView / 无部署构建的 map；**LTO 已启用**（`xmake.lua:24` `set_policy("build.optimization.lto", true)`）⇒ 跨 TU 全局代码生成，**同一 TU 的 IR 不一定产出同样的机器码** |
| **部署 DLL 的 `bind()` 日志行为** | **[推断] MATCH** | 日志分支与文案由 `EngineBindings.cpp` 的**源码**决定；LTO **不会删除可达分支中的日志调用**（这些分支由外部输入决定，编译期不可判定）。**反证条件**：若部署构建使用过不同的 `EngineBindings.cpp` 内容，则失效——但该 TU 与 HEAD 逐字相同、且其 `.obj` 属于该构建，故反证条件不成立。 |

**关于字节块搜索的诚实记录** `[直读]+[未知]`：以当前构建的 `.map` 定位 `bind()`（`EngineBindings.cpp.obj`，`0001:00209ff0` → RVA `0x20AFF0`），从 A 取 256 字节，在 C 中**未找到逐字节相同块**。该结果在 LTO 下**不确定**：全局优化会使同一源码的机器码变化。**不得**把它读作"源码不同"的证据。

### 3.4 缺少的证据清单（**不得**用"时间戳相近 / 文件名相同"替代）

| # | 缺失证据 | 为什么需要 | 可得性 |
|---|---|---|---|
| M1 | 部署构建（2026-10-09 13:49:42）的 **PDB** | 唯一能把 DLL 与具体编译单元/源码路径绑定的载体 | **本机 0 个 PDB**；未知是否有外部备份 |
| M2 | 任一 DLL 的 **CodeView/RSDS 目录项** | 若无该目录，DLL 内**根本不含**构建身份 | A 与 C 均为空 ⇒ **结构性不可得**（需重新构建并开启调试目录） `[需授权]` |
| M3 | 部署构建的 **`.map`** | 提供 `bind()` 等符号的地址 | 已被 10-10 构建覆盖；**不可恢复** |
| M4 | 部署构建时 **工作区源码的完整快照 / 版本标记** | 直接证明源内容 | 需要外部快照；本机未发现 |
| M5 | **可重复构建**证明 | 证明"同源码 + 同工具链 ⇒ 同二进制" | 需要构建（**本任务禁止**） `[需授权]` |
| M6 | 构建日志中的 **源文件内容哈希** | 当前日志只列 TU 路径 | 当前日志无此字段 |

---

## 4. 任务 A.5 — 逐项判定与解释

| 关系 | 判定 | 依据（逐项） | 不能推出的结论 |
|---|---|---|---|
| 沙箱部署 DLL ↔ F stage DLL | **MATCH** | SHA-256 相等、字节数相等、PE `TimeDateStamp` 相等、`debugDirRva` 相等 | 不证明它们与当前源码一致 |
| 沙箱部署 DLL ↔ 当前源码**整体** | **MISMATCH** | 4 个 TU 相对 HEAD 被修改；其中 2 个 TU 的 `.obj` mtime 晚于部署构建 | 不证明 `bind()` 逻辑不同（该 TU 未变） |
| 沙箱部署 DLL ↔ 部署构建日志 | **MATCH** | `_build_olgs.log` 记录的 size 与 sha256 与部署件**完全一致** | 不证明当前源码与其一致 |
| 部署 DLL 的 `bind()` 机器码 ↔ 当前源码 | **UNKNOWN** | 无 PDB/无 CodeView/无该次 map；LTO 破坏"obj 复用 ⇒ 代码相同"的推理 | 不得据此认为日志行为不同 |
| 部署 DLL 的 `bind()` **日志行为** | **[推断] MATCH** | 源码级同一 + 可达分支的日志调用不被 LTO 消除 | 仍需 V5 解除后作最终确认（非必需） |
| 部署 DLL ↔ 批准目标 | **MATCH** | `config/codol-target-build.json` 与 manifest 均记 `6D493B82…` | 该批准日期（10-10）晚于部署件构建日期（10-09） |
| 部署 DLL ↔ D 冻结副本产物 | **MISMATCH** | D 产物为 `0EABD5F5…`（10-09 17:32:40，与 `_t1_compat.log` 一致） | — |

---

## 5. 影响 V5 判定的工具链设置 `[直读]`

| `xmake.lua` 行 | 设置 | 影响 |
|---|---|---|
| `:23` | `set_optimize("fastest")` | `/O2` 级别 |
| `:24` | **`set_policy("build.optimization.lto", true)`** | **MSVC `/GL` + `/LTCG`**：跨 TU 全局优化 ⇒ **任何 TU 的改动都可能改变 `bind()` 的机器码** |
| `:20` | `set_symbols("debug")` | 生成调试信息 —— 但**未生成/未保留 PDB**，且 DLL 内**无 CodeView 目录** |
| `:22` | `set_runtimes("MT")` | 静态 CRT（release） |
| `:13` | `set_languages("c++latest")` | — |

> **这是把"obj 复用"从"足以证明代码相同"降级为"只能证明源码相同"的唯一原因。**

---

## 6. 对 COMBAT-P0 结论的影响（必须明确记录）

COMBAT-P0 曾登记一条**反证条件**："若实际部署的插件与当前源码树在 `bind()` 的日志行为上存在差异……则'无 stage 日志 ⇒ 静默分支'的推断不成立。"

**本轮结论：该反证条件不成立（对 `bind()` 而言）。**
- `EngineBindings.cpp/.hpp` **与 HEAD 逐字相同**，且**正是部署构建所编译的那个版本**（构建日志 + `.obj` mtime 双证据）。
- 因此部署 DLL 的 `bind()` **日志分支结构与文案与当前源码一致**；2026-10-10 三次运行"只有 `engine binding failed`、没有任何 stage 行"仍然只能解释为**静默早退分支**（`:3656 / :3660 / :3662-3666`）。
- **仍未解决**的是"**具体哪一项**失败"（`TimeDateStamp` vs `SizeOfImage` vs `NT 签名`）——这正是运行时采样要回答的问题。

---

## 7. 本轮未做与需授权的下一步

**本轮未做**：未构建、未部署、未调用 `ol_deploy`、未启动/附加/注入任何进程、未读其他进程内存、未调用 `CODOL_GameServerSetEnabled`、未执行 Stage D/E/F/T、未修改任何源码/配置/RVA/ABI/门禁、未在 F↔D 间复制、未改 `GOLDEN-LOBBY-001`/`REF_LOBBY_KIT`/既有日志。

**需要用户单独授权的下一步**（详见 `COMBAT_P1_RUNTIME_SAMPLING_PLAN.md`）：
1. 在 `EngineBindings.cpp` 内加入**只读**采样（门禁之前、不改判定语义）；
2. **构建** `ol_game_server`；
3. 把新插件**落到沙箱**（`ol_deploy` 禁用，需替代流程）；
4. **启动 1 个沙箱客户端**并只读日志。
> 以上四项**必须分别授权**；本任务不申请执行。

**明确不做**：以放宽 `SizeOfImage`、删除守卫或改 RVA 的方式消除 UNKNOWN。
