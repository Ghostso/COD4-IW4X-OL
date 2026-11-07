# COMBAT_SERVER_HISTORICAL_FINDINGS — CODOL 复活项目战斗服务器历史结论总集

**轮次性质**：只读历史研究成果搜集与证据归档（不是新的研发实现轮次）。
**日期**：2026-10-11（本文件生成时点）
**会话工作目录**：`D:\BaiduNetdiskDownload\使命召唤OL`（工作区根，即本项目既定交付文档目录；与前序 Batch 交付同址）
**本轮限制**：未修改任何生产代码/配置；未启动/附加/注入/终止任何进程；未构建/部署/提交/推送；未清理工作区。仅新增本文件与其余 4 份交付物。

> **本文件不产生新结论。** 所有条目均为已有源码、二进制、日志、报告与哈希清单的转写；凡历史资料未证明者一律标注 `UNKNOWN`，不以常见游戏架构补全。互相冲突的历史结论**并列保留**，不擅自消除。

---

## 0. 证据等级与复核口径

| 标记 | 含义 |
|---|---|
| `[源码]` | 本工作区/活动基准中可直接读取的源码常量、函数体、注释 |
| `[静态二进制]` | 对实际 PE 文件/IDA 结论的测量（本轮对可读文件做了只读复核） |
| `[离线测试]` | 独立测试可执行文件的真实退出码与断言数（非真实客户端运行） |
| `[真实运行]` | 真实游戏进程/插件的运行日志或实测记录 |
| `[仅历史报告]` | 只有文档自述，原始制品或运行目录在本工作区不存在/不可复核 |
| `UNKNOWN` | 历史资料未证明 |

**两类必须分开的记录**
1. **两套启动/战斗线**：`ol-mod-olfinal`（C++ Ayria 插件 `CodolGameServer.Localnet32`）与 `CODOLServer / REF_LOBBY_KIT`（Python 协议逆向线，含 `lobby_server.py` / `battle_server.py`）。本任务点名的事实（`CodolGameServer.Localnet32`、`Createserver`、`combined/dedicated/client`、`EngineBindings::bind()`、146 RVA/82 守卫、`0x0E5D6000` vs `0x0E659000`）**全部属于 ol-mod 线**。
2. **两套工作树**：**F** = `F:\桌面\ol\ol-mod-olfinal`（唯一活动基准）与 **D** = `D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal`（冻结历史回归副本，只读）。两树 HEAD 均为 `2a75bdd8872bb9f54006382a924c3006ec9affc2`（`OLfinal-live`）。

---

## 1.（A）项目整体目标与历史决策

### 1.1 用户明确确认的项目目标（本轮任务书）

> 在现有 CODOL 启动至大厅链路的基础上，**直接围绕游戏战斗创建服务器**，使客户端能够进入实际战斗并完成对局。本项目**不是**以大厅、登录、匹配、通用 Dedicated Server、启动器改造或 Frida 工具开发为最终目标。

### 1.2 历史文档中记录的目标定义（按文档对象区分，不得混用）

| 对象 | 目标定义 | 证据 |
|---|---|---|
| **ol-mod 战斗线** | `src/game_server` 是 **x86 dedicated gameplay server 实现**，通过 `Com_Frame` hook 驱动网络与 server core，负责**局内 authoritative simulation**，不负责 Auth3/仓库/档案/商城/匹配策略 | `.agents/modules/game_server.md:193-195` |
| **ol-mod 战斗线（B3 结论）** | 战斗服务器**不是独立进程**，而是**客户端进程内嵌模块**；另有 `ol_room_owner.exe` 只做房间/会话归属，不承载战斗模拟 | `COMBAT_SERVER_RECOVERY_BASELINE.md:140-149` |
| **协议逆向线目标** | 重建目标 = **CODOL observable compatibility**（wire 协议、可达 service/task、持久化副作用、服务端推送、启动到持续对局的状态转换）；不要求指令级等价 | `.agents/research/project_nova_codol_scope.md:57-67` |
| **协议逆向线剩余高价值frontier** | ready-to-map 与服务分配、listen/dedicated 游戏服务器建立、challenge/gamestate/snapshot、地图加载/GSC/持续play、赛后持久化、真实双客户端 LAN | `project_nova_codol_scope.md:131-138` |
| **大厅阶段目标（另一任务书口径）** | 该阶段的最终交付是**大厅复现**，**不是 PvE 对局** | `DEV-REPRO/REPRODUCTION-BASELINE-LOBBY-001.md` §1.1–§1.3（转引自本轮子代理盘点） |

> **注意**：1.2 中"大厅阶段交付是大厅"与 1.1"最终目标是进实际战斗"是两个不同层级的表述，来自**不同任务书**。本轮**不裁定**二者关系，二者并列保留。

### 1.3 已确认的架构判断与重要决策

| # | 结论 | 证据 |
|---|---|---|
| A-1 | `ol_game_server` 是 `set_kind("shared")`、产物名 `CodolGameServer.Localnet32` —— **是 DLL，不是 exe** | `xmake.lua:191-194` |
| A-2 | `EngineBindings` 绑定的是**宿主进程自己的主映像**：`module_ = GetModuleHandleW(nullptr)` | `EngineBindings.cpp:3654` |
| A-3 | `Createserver` **故意返回 nullptr**，注释写明该导出只为"让 Localnetworking 加载器保留本模块" | `Appmain.cpp:8152-8158` |
| A-4 | 服务逻辑挂载在 `Com_Frame`（RVA `0x0FEA20`）的 5 字节相对跳转上 | `FrameHook.cpp:39-71` |
| A-5 | `runsGameServer(role) = role != Client` ⇒ **`combined`（默认）与 `dedicated` 都跑战斗服务器**（listen-server 形态） | `ProcessRole.hpp:47-50` |
| A-6 | **UDP 28960 监听是结果不是起点**：触发者是后端下发的会话配置，不是插件加载 | `Appmain.cpp:2084-2098`；`COMBAT_SERVER_RECOVERY_BASELINE.md:184-188` |
| A-7 | CODOL 客户端**没有通用 GSC compiler/VM**，authoritative GSC 必须由 `ol_game_server` 承载 | `CODOL_SERVER_PROGRESS_20261009.md:175` |
| A-8 | 后端**尚未成为独立网络 daemon**；`client` 角色下仍是进程内 Localnetworking socket bridge | `backend.md:7`；`CODOL_SERVER_PROGRESS_20261009.md:92` |
| A-9 | 引擎绑定层是"CODOL 引擎 ↔ 重建服务端"的**唯一桥梁** | `CODOL_SERVER_PROGRESS_20261009.md:190` |

### 1.4 曾经否决/撤销的方案及原因

| # | 被否决方案 | 原因 | 证据 |
|---|---|---|---|
| R-1 | 自研大厅协议栈（自建 0x81/0x82/0x83 栈） | 未能推进，改为复用 `REF_LOBBY_KIT` | `HANDOFF_20261005_PUSH_TO_LOBBY.md`、`HANDOFF_20261005_BREAKTHROUGH.md`、`HANDOFF_20261005_REFKIT_WORKS.md` |
| R-2 | 用**靶场（firing range）信封**回答 **PvE booking** | 实测 **9/9 断连**；两种 booking 信封不可混用 | `REF_LOBBY_KIT/STAGE_REPORT_BATTLE.md` P0-2；`BATTLE_SERVER_PROTOCOL.md` §9.2/§9.13 |
| R-3 | 开启 `firingrange-booking-push.enabled` | 推送 `mmbook accepted` 会打断连接（1~2 秒内对端关闭）；已改名 `….OFF_CONFIRMED_CRASH`，**必须保持关闭** | `BATTLE_SERVER_PROTOCOL.md` §9.1–§9.12；`GOLDEN-LOBBY-001.md` |
| R-4 | `replyId` 用独立计数器（不回显 seq）／推送 seq +1000 | 断连，已回退 | `MASTER-POST-LOBBY-FULL-HISTORY-001.md` RB-4/RB-5（转引） |
| R-5 | `--tas` 注入 / TAS | 实测**卡住**；默认 `tas_off.flag` | `GOLDEN-LOBBY-001.md`；`REPRODUCTION-BASELINE-LOBBY-001.md` §8.1 |
| R-6 | 把 `CodolGameplayProbe.py` 扩写成正式战斗服务器 | 文档明确"**不要**用它手工添加武器/移动/出生/目标/动画/碰撞/比赛规则"；定位为 conformance harness | `playable_architecture.md:214-218` |
| R-7 | 把去壳 `out.exe` 当作**项目级强制输入** | 被裁定为"对象错位 + 范围放大"；`out.exe` 降级为**逆向来源对象（O-1）** | `FULL_ENCRYPTED_CLIENT_TARGET_ADJUDICATION.md:26-71,135-149`；`NEXT_PHASE_PLAN.md:32-39` |
| R-8 | 通过修改期望哈希/RVA/前缀/尺寸常量"让门禁变绿" | 明令**禁止**；门禁不得删除、不得置为 GO | `NEXT_PHASE_PLAN.md:41-51`（B 类）、`§5 P4-3`；`ARTIFACT_BLOCKERS.md:8` |
| R-9 | 在 Golden 只读目录直接跑 | 会复现 `EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE`（数据目录缺失） | `REPRODUCTION-BASELINE-LOBBY-001.md` §5.7 |
| R-10 | 关闭/绕过 ACE / TenProtect | 纪律禁止；历史实测蓝屏 `0x01010002` | `REPRODUCTION-BASELINE-LOBBY-001.md` §7.4 |

### 1.5 已明确要求保持不变的基线与运行环境

| 项 | 内容 | 证据 |
|---|---|---|
| 活动基准 | **F = `F:\桌面\ol\ol-mod-olfinal`** 是唯一活动工作基准；新源码修改/构建/测试只允许在 F | `BASELINE_ADJUDICATION.md` R1 |
| 冻结副本 | **D** 只读：禁止构建/运行/写入/清理/双向同步；D 的 pre-T-1 标注不可信；D 的"回归通过"记录作废；禁恢复 E1 | `BASELINE_ADJUDICATION.md` R2–R5/R8 |
| 构建纪律 | 必须**显式命名目标**（`ol_deploy` 是 `set_default(true)` 且 `config/codol-game-dir.txt` 非空） | `BASELINE_ADJUDICATION.md` R6 |
| 受保护常量 | 协议常量 / ABI / RVA / 机器码前缀 / 固定启动链 / S2–S3 默认值**一个字节都不改** | `NEXT_PHASE_PLAN.md:19-23` |
| 无参语义 | `Network.start()` ≡ `start(28960, 0)`；默认绑定地址 `AnyIpv4Address == 0 == INADDR_ANY` | `NEXT_PHASE_PLAN.md:20-21` |
| 大厅 Golden | `GOLDEN-LOBBY-001` 只读冻结；实验在开发副本；不依赖记忆恢复 | `GOLDEN-LOBBY-001.md`；子代理 D 盘点 |
| 出厂原件 | `COD OL/` 为出厂原件（974 个 IIPS .ifs），**只读** | `REPRODUCTION-BASELINE-LOBBY-001.md` §5.7（转引） |

### 1.6 四分类：目标 / 建议 / 已实施 / 未执行

**A. 用户明确确认的目标**
- 最终目标 = 进实际战斗并完成对局（本任务书，见 §1.1）。
- 纪律硬边界：不绕 ACE/TenProtect；沙箱实验可回滚；Golden 只读；不依赖记忆恢复。

**B. Agent 曾提出但尚未批准的建议（不得写成已批准决策）**
- `NEXT_PHASE_PLAN.md` 的 **P1–P4 全部任务**（P1-1 T-1 最小修复、P1-2 插件边界测试目标、P1-4 离线绑定重放工具、P1-6 协议向量扩展；P3-1..P3-5 运行时验证；**P4-1 启动客户端+注入 / P4-2 读内存 / P4-3 改常量 / P4-4 部署**）。
- `CODOL_RUNTIME_BLOCKER_CLEARANCE_20261009.md` §4.3 的三条新测试方案 **T1/T2/T3**（仅方案）。
- `COMBAT_SERVER_RECOVERY_BASELINE.md` §6 的 **T-3.0**（门禁具名化 + 复合守卫首失败者具名 + `OLMOD_BINDING_IMAGE_SIZE_TOLERANCE` 默认关闭的受控旁路）。
- P0 处置路线 **R-A（取得去壳 out.exe）/ R-B（受控试验 + 目录移植）** —— **待用户裁定**。
- 商城目录放量、首页挑战/公告 .info 语法等（需先取得真实键名）。

**C. 已经实际实施的改动**
- `GOLDEN-LOBBY-001` 冻结（2026-10-07）+ `_golden_hashes.json`；`GOLDEN-LOBBY-001/REF_LOBBY_KIT/` 22 文件转只读。
- 进大厅两个真实修复：`0x83` 改用**本会话 KDF challenge**；`mp_playlists_shipRetail_1.0.0.info` **同义名回退**（并已置入实体别名文件）。
- Publisher 数据恢复（消除 `EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE`）；购买解析改 TLV；AES 优先 PyCryptodome；目录 37,615→37,834（可回滚开关）。
- 战斗线：**T-1 最小修复**落地（断言 106→112→124，`failures 2→0`）+ `_t1_fix_evidence/REPRODUCE.ps1`；T-2.1–T-2.4 工具/守卫修复与文档。
- 2026-10-10 三次战斗服务器启动（首次产出战斗服务器运行日志）；沙箱 overlay 44/44 与 `mp_crash_tropical*.ff` 就位。
- `firingrange-gamestate.bin`（259 B）补齐。

**D. 尚未执行的计划**
- `PLUGIN_LOAD_PASS` / `SERVER_INIT_PASS` / `CLIENT_CONNECT` / `GAMESTATE` / `SNAPSHOT` / `BATTLE_SMOKE`：全部 `NOT_TESTED`。
- T-2.4 Stage C/D/E/F/T：`NOT_AUTHORIZED`；T-2.5 报告自述"仅阶段 1 只读预检"，真实控制链证据 0 条。
- 制品门禁 B1–B6：全部 `BLOCKED/UNKNOWN`。
- `GOLDEN-BATTLE-001`：**尚未创建**（该阶段自定判据要求成功后立即冻结，未达成）。
- booking 控制面（mmbook/mmstart 应答）**未实现**。

---

## 2.（B）原版客户端与引擎研究

### 2.1 客户端对象标识（六类）

| 对象 | 标识 | 角色 | 证据 |
|---|---|---|---|
| **O-1 历史去壳样本** | `out.exe`；SHA-256 `044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9`；build 1649370；`TimeDateStamp=0x6096930A`；`SizeOfImage=0x0E5D6000` | **逆向来源对象**；`EngineBindings` 的 RVA/前缀由它推导 | `tools/reverse/annotations/out.exe.json:3`；`EngineBindings.hpp:438-439`；`FULL_ENCRYPTED_CLIENT_TARGET_ADJUDICATION.md:80` |
| **O-2 3.3.3.3 QA 客户端** | `TimeDateStamp=0x57611E31`；`SizeOfImage=0x0C72A000`；**无独立 SHA 记录** | 旧基线；`CodolClientPatches` 的 8 个钩子仍键在它上面，**在本客户端上故意不安装** | `src/backend/Demonware/CodolClientPatches.cpp:45-46,610-616` |
| **O-3 实际运行目标** | `codoMP_client_shipRetail.exe`；7,841,344 B；SHA-256 `36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537`；`FileVersion=1649370`；`TimeDateStamp=0x6096930A`；`SizeOfImage=0x0E659000`；ImageBase `0x00400000`；EntryRva `0x0E5DC690`；7 段（`.tp3`×6+`.tvm0`） | **实际运行对象**；启动链默认目标 | `FULL_ENCRYPTED…:82,441-454`；`ARTIFACT_BLOCKERS.md:159-180`；本轮只读 PE 复核一致 |
| **O-4 运行时映像** | 进程内 `GetModuleHandleW(nullptr)` 的 PE 头 + 代码字节 | **门禁真正判定的对象** | **无任何证据** |
| **O-5 `E3823FD6…F37B`** | 完整 SHA-256 `E3823FD6AFC80FB25FA84747E6E9634707B9A0B189357A5466921CDA354AF37B` | **归属未裁定**（三方互斥） | `ARTIFACT_BLOCKERS.md:124-151` |
| **O-6 `OL.exe`** | 哈希未知 | 第三个零售客户端对象；历史记录门禁 A"mismatching 且 55/66 守卫失败" | `FULL_ENCRYPTED…:85` |

**边界 DLL**：`codoMP_client_shipRetailBase.dll`，60,327,992 B，SHA-256 `EF75220DE1D6973F34C7069F5BF211B11BD61520C6C0DE1882F7359FA5BC6A20`；ImageBase `0x10000000`、8 节、`SizeOfImage=0x03991000`、EntryPoint `0x149C`；导出目录 RVA `0x952D60`、OrdinalBase 1、NumberOfFunctions 3、**0 个具名导出**（`COD OL/docs/protocol.md:15-41,47`）。块 6/15/17 为全序数块，前缀不可信（`protocol.md:157`）。

### 2.2 已确认的模块 / 导入表 / 导出表

| 项 | 结论 | 证据 |
|---|---|---|
| EXE 导入描述符 | **恰好 1 个**：仅 `codoMP_client_shipRetailBase.dll` | `_core012_artifact_summary.md:23`；`COD OL/docs/game-net-hunt-report.md:1854` |
| IAT 槽 | VA `0x0E9DC665`（RVA `0x0E5DC665`），文件值 `0x80000001` = Base.dll ordinal 1 | `_core012…:22`；`CODOL_ORDINAL1_LIFECYCLE_FINAL.md:60` |
| 入口指令 | `FF 15 65 C6 9D 0E` = `call dword ptr [0x0E9DC665]` | `_core012…:21` |
| 重定位 | **无 base relocations**（目录大小 0） | `_core012…:24` |
| EXE 导出表 | `UNKNOWN` | 未找到任何记录 |
| Base.dll 导入 | PE 头 Import 目录只列 `kernel32.dll`+`libcef.dll`；真实导入表在 `.idata2`（21 DLL / 748 槽；被 call 512 槽；`call dword ptr [abs]` 2286 处） | `protocol.md:48,55,61-69` |
| 网络层 | 游戏 EXE 与 Base.dll 的窄 IOCP 扫描 **No matches**（含阳性对照）⇒ **CODOL 游戏侧不使用 IOCP**；Base.dll `.text` socket 创建点仅 6 处，`accept`/`listen` 各 2 点全在 libcurl 内 ⇒ **进程不监听端口** | `game-net-hunt-report.md:1805-1813`；`net-familyAB-report.md:354-410,422-423` |
| 唯一自研网络模块 | `p2papp.dll`（4 份副本） | `game-net-hunt-report.md:1821-1823` |
| 客户端门禁 | Base.dll 硬编码读取 `TCLS_SHAREDMEMEMORY`/`TCLS_TASMEMORY_` 等内核对象名，读不到即弹 `WIN_NO_TCLS` | `protocol.md:181-198` |

> 纪律提示：**不得**因为模块名包含 `Server` 就断言其职责。本档案中 `ol_room_owner.exe` 明确**不承载战斗模拟**（`COMBAT_SERVER_RECOVERY_BASELINE.md:137,142`）。

### 2.3 引擎绑定：常量、守卫、门禁

| 指标 | 实测值（本轮在 D 树只读复算） | 备注 |
|---|---|---|
| `EngineBindings.cpp` | **17,419 行**（D 树）；F 树 18,028/18,029 行 | 行数随工作树不同；见 §7 冲突 C-13 |
| `EngineBindings.hpp` `static constexpr … *Rva =` | **145** | 与文档的 146 冲突（C-2） |
| 宽口径 `*Rva =` 标识符（去重） | **146**（多出 `CURRENT_CHARACTER_GET_RVA`，非 `static constexpr`） | 可解释"146"的来源 |
| `std::equal(` 前缀守卫 | **82** | 与 66 / 78–79 冲突（C-3） |
| `ClientProcessPatches.cpp` `*Rva` 常量 | **25**（含 `UnsignedFastfileVerificationRva=0x8371A`） | `FULL_ENCRYPTED…:480` |
| 门禁点 | 4 处（`bind()`、`DedicatedProcessPatches`×2、`ClientProcessPatches`×1） | |

**宿主身份常量（源码级事实）**

```
EngineBindings.hpp:438  static constexpr std::uint32_t ExpectedTimestamp = 0x6096930A;
EngineBindings.hpp:439  static constexpr std::size_t   ExpectedImageSize = 0x0E5D6000;
EngineBindings.hpp:440  static constexpr std::size_t   ComFrameRva       = 0x0FEA20;
EngineBindings.hpp:434-435  // 注释仍写 "for the 0x57611E31, 0x0C72A000 CODOL executable only"
```

> :434-435 的注释引用的是 **O-2（3.3.3.3）** 常量，而 :438-439 是本文件自身的 O-1 常量 —— 已确认属**过期注释**（`FULL_ENCRYPTED…:339` D-6），**只建议改注释、不动常量**。

**门禁实现（静默失败）** `EngineBindings.cpp:3647-3667`：

```cpp
bindingCommitted_.store(false, std::memory_order_release);   // :3653 fail-closed
module_ = reinterpret_cast<std::uint8_t *>(GetModuleHandleW(nullptr));  // :3654
if (!module_) return false;                                  // :3655-3656  【静默】
... e_magic != IMAGE_DOS_SIGNATURE -> return false;          // :3659-3660  【静默】
if (nt->Signature != IMAGE_NT_SIGNATURE ||
    nt->FileHeader.TimeDateStamp != ExpectedTimestamp ||
    nt->OptionalHeader.SizeOfImage != ExpectedImageSize)     // :3662-3664
    return false;                                            // :3666        【静默】
```

**本轮独立核实的关键判定**：`bind()` 内共 9 处 `return false`，其中**只有 3656 / 3660 / 3666 三处不写日志**；其余（3692、3741、4022、4154、4204、4211）均**先写日志再返回**，且日志与 `logGameServer` 使用**同一文件、同一前缀**（`RuntimeLog.cpp:60` `"game-server"`；`:77` `L"CodolGameServer.log"`）。据此，三次实机日志中**只出现** `engine binding failed` 而没有 `native entity binding prefix mismatch` / `stage=function_prefixes` / `stage=runtime_slots` / `stage=message_bindings` / `stage=glass_bridge` 任何一行，**在证据上支持**"失败发生在 3656/3660/3666 三处之一"。**但**：`TimeDateStamp` 与 `SizeOfImage` 在**同一个 `if`** 内，代码**不记录是哪一项不符**，故**无法**据此认定"只需放宽尺寸检查"。

**具名守卫**：`3669-3693`（`SV_LinkEntity`/`SV_UnlinkEntity`/`SV_Trace`，日志 `native entity binding prefix mismatch function=`）、`3695-3742`（player DObj 族）。
**未具名复合守卫**：`3744-4023` 的 `||` 链，失败只写 `engine binding validation failed stage=function_prefixes`（`:4021`）。
**其他阶段**：`:4153` `stage=runtime_slots`；`:4203` `stage=message_bindings`；`:4210` `stage=glass_bridge`；`:4214` `bindingCommitted_.store(true)`；`valid()` `:4218`。
**期望字节**：`0x0FEA20` → `55 8B EC 56 57`（`EngineBindings.cpp:755-757`）；`0x8371A` → `83 7C 24 08 01 0F 94 C0`（`ClientProcessPatches.cpp:207-211`）。
**打补丁点**：`ClientProcessPatches.cpp:811-831`、`1254-1261`。

### 2.4 调用约定与结构偏移（已确认事实）

| 函数 | 调用约定 | 证据 |
|---|---|---|
| `PmoveSingle 0x0041DBA0` | `__cdecl`，双 stack 参数 | `.agents/modules/reverse_engineering.md:211` |
| `PM_SetPitchValues 0x0041E720` | `EAX=playerState_s*` + 单 stack `pmove_t*` | 同上 |
| `DB_GetAllXAssetOfType 0x0049ED90` | `EDI`=可空 XAssetHeader* 数组，栈传 type，`EAX` 返回数量 | :134 |
| `DB_GetRawBuffer 0x004A1620` | `ECX`=16B `RawFile*`，栈传 dest/capacity | :134 |
| `CM_WorldTrace 0x0058AFE0` | `EDX=contentMask`、`EDI=end`，栈 results/start/bounds/callbacks | :163 |
| `CM_TransformedBrushModelTrace 0x0058B230` | `ECX=angles`、`EDX=trace result`，caller cleanup `0x18` | :165 |
| `SV_Trace 0x005FB940` | `ECX=IgnoreEntParams*`、`EDX=end`，栈 result/start/bounds/contentMask，cleanup `0x10` | :171 |
| `BG_PlayerStateToEntityState 0x004134B0` | `EAX=entityState_s*`、`ECX=playerState_s*` | :183 |
| `PM_GetEffectiveStance 0x00415CD0` | `EDI=playerState_s*` | :157 |
| `QuatToAxis 0x0062A5A0` | `EAX=float[4]`、`ECX=float[3][3]` | :175 |
| `CL_ExecuteBindingAction 0x00460870` | localClientNum 在 `ECX`，action/key 在栈；**不强行套 __cdecl** | :205 |

**结构尺寸（CONFIRMED）**：`playerState_s=0x3564`、`usercmd_s=0x2C`、`pmove_t=0x12C`、`trace_t=0x28`、`entityState_s=0x110`、`DObjModel_s=0x2C`、`DObj_s=0xCC`、`characterInfo_t=0x3B8`、`hudelem_s=0xA8`、`weaponState_t=0x90`、`viewState_t=0x24`、`pointtrace_t=0x58`、`IgnoreEntParams=12`、`RawFile=16`（`reverse_engineering.md:209,211,179,271,197,183,251`）。

> 纪律（源码内明示）：不能准确表达的 custom register ABI **只命名 + 寄存器注释，不强套 prototype**（`reverse_engineering.md:77,285`）。

### 2.5 已追踪的战斗创建入口（详见 §4）

- **`Com_Frame` = RVA `0x0FEA20`** —— 唯一的帧驱动挂载点（`EngineBindings.hpp:440`）。
- 项目源码中的 `NET_Frame`（`sv_network_mp.cpp:100`）是**项目自建函数**，**不是**原版引擎函数；原版 `NET_Frame` `UNKNOWN`。
- `Createserver` 导出**故意返回 nullptr**（`Appmain.cpp:8155-8158`）。
- 原版引擎中独立存在的"CreateServer / 战斗会话创建"函数：`UNKNOWN`（未定位）。

### 2.6 地图与游戏模式初始化

| 项 | 结论 | 证据 |
|---|---|---|
| 资产/zone 加载 | `DB_FindXAssetHeader 0x0049E7D0`、`DB_GetAllXAssetOfType 0x0049ED90`、`DB_LoadXAssets 0x0049F960`、`DB_AppendCommonMPZones 0x0049FD00`、`DB_IsZoneLoaded 0x004A0820`、`DB_GetRawBuffer 0x004A1620` | `reverse_engineering.md:90-95,136` |
| Hunk/registry | `Com_StartHunkUsers 0x0059CFE0` 的完整链路**继续保留**（v38 证伪了跳过它；v44 恢复后 registry 自然推进 `0/0 → 357/151`） | `game_server.md:217-219` |
| 地图/UI | `UIViewer_Init 0x005660D0`、`UIViewer_LoadMap 0x00566560`、`UIViewer_Update 0x00567860` | `reverse_engineering.md:138` |
| World 加载 | `CM_LoadMap 0x00585B20`（custom ABI：`ECX=mapName`，栈 bspName/gameType，`EAX` 返回 collision checksum）→ `CM_LinkWorld 0x0058C810` → 查 `COMWORLD` | `game_server.md:271-275` |
| mapents | `mp_crash_tropical`：262,262 B entity string、2,123 实体、185 个 `script_brushmodel`；dedicated pool 189 项 | `reverse_engineering.md:257` |
| 地图 `.ff` | `mp_crash_tropical` 已离线解包可用；`mp_nuked` **解包失败，整套产物未验证，不得使用** | `CODOL_RUNTIME_BLOCKER_CLEARANCE_20261009.md` §2.2/§2.3；`_map_extract/` 实测含 `blob3.ff` 82,515 B 与非法头产物 |
| playlist | slot `26 → raw 111 → Map: Crash Tropical`；raw `133` 是禁用的 Express；`52 → raw 161` 才是启用中的 9v9 SD | `game_server.md:364` |
| GSC | CODOL 客户端**无通用 GSC compiler/VM**；地图脚本按 `common.lua → gametypes/<gt>.lua → maps/<map>.lua` 顺序加载，缺文件 `continue` | `CODOL_SERVER_PROGRESS_20261009.md:172,175` |
| configstrings | 3.3.3.3 的索引表在 `out.exe` 上**已整表重新推导**（非同一 delta 平移） | `game_server.md:287-308` |
| 原版 gametype 初始化入口 | `UNKNOWN` | — |

---

## 3.（C）战斗服务器代码盘点（`src/game_server`）

### 3.1 规模与结构（本轮在 D 树实测）

| 目录 | 文件 | 行（`Measure-Object -Line`，不计空行） |
|---|---|---|
| `src/game_server/`（根） | 29 | 39,146 |
| `server_mp/` | 134 | 92,425 |
| `qcommon/` | 8 | 2,292 |
| `win32/` | 2 | 256 |
| **合计** | **173** | **134,119**（精确计行与 `CODOL_SERVER_PROGRESS_20261009.md:34` 的 139,300 一致） |

根目录最大文件（精确行数）：`Appmain.cpp` 9,519；`EngineBindings.cpp` 18,028；`EngineBindings.hpp` 2,142；`ClientProcessPatches.cpp` 1,862；`DedicatedProcessPatches.cpp` 919；`FrameHook.cpp` 74。

### 3.2 已实现的服务器初始化路径

| # | 步骤 | 位置（D 树） |
|---|---|---|
| 1 | `DllMain(DLL_PROCESS_ATTACH)` → `initialize()` | `Appmain.cpp:9511-9519` |
| 2 | `initialize()`：`StartupMutex` 守卫 + `Installed` 早退 | `Appmain.cpp:7012-7017` |
| 3 | `role = OlMod::processRole()`（读 `OLMOD_PROCESS_ROLE`） | `Appmain.cpp:7017`；`ProcessRole.hpp:17-40` |
| 4 | unsigned fastfile patch | `Appmain.cpp:7022-7035` |
| 5 | Client 角色：单实例 mutex patch | `Appmain.cpp:7100-7109` |
| 6 | Dedicated 角色：`installDedicatedProcessPatches()`，失败即 return | `Appmain.cpp:7111-7132` |
| 7 | **`Bindings.bind()` 失败 → `logGameServer("engine binding failed")` → return** | **`Appmain.cpp:7133-7137`** |
| 8 | Client 可选 alpha weapon gamestate patch | `Appmain.cpp:7138-7152` |
| 9 | 非服务器角色：`installFrameHook(Bindings, onServerFrame)` → `installClientInputPatches(role)` → return | `Appmain.cpp:7153-7162` |
| 10 | 服务器角色：配置 providers 后 `Installed = installFrameHook(...)` | `Appmain.cpp:8128-8132` |
| 11 | `ensureInstalled()` = `initialize()` + `Installed` | `Appmain.cpp:8135-8139` |
| 12 | 导出 `onStartup` / `onInitialized` → `initialize()` | `Appmain.cpp:8142-8145` / `:8147-8150` |
| 13 | `installFrameHook`：目标 `module + ComFrameRva`，`HookSize=5`，蹦床 + `0xE9` 相对跳转 | `FrameHook.cpp:12,39-71` |
| 14 | 每帧回调：`runServerFrame() → Callback(GetTickCount()) = onServerFrame` | `FrameHook.cpp:16-34` |

> 行号以 **D 树**为准。`COMBAT_SERVER_RECOVERY_BASELINE.md:159-165` 记 `DllMain` 在 `:9538-9544`、`FrameHook.cpp:59-113` —— 那是 **F 树**（含未提交 FrameHook/Appmain 改动）的行号。

### 3.3 网络传输 / 套接字 / 控制消息 / 会话管理

| 端口 | 定义 | 角色 |
|---|---|---|
| **28960/UDP** | `server_mp/sv_network_mp.hpp:56` | 战斗服务器 gameplay UDP（DTLS） |
| **28961/TCP** | `src/shared/DedicatedControl.hpp:16`（`ProtocolVersion=2` :15） | DedicatedControl：后端 → 战斗服务器配置会话 |
| **28962/TCP** | `DedicatedControl.hpp:17`（`DefaultClientBridgePort`） | ClientSessionBridge：client 进程内 loadout/session 捕获 |
| **28970/TCP** | `src/backend/SharedRoomControl.hpp:14` | `ol_room_owner.exe` 房间/名册 owner（**非战斗模拟**） |
| **4200/TCP（+0..63）** | `src/localnetworking/Localnetworking.hpp:27` | Localnetworking backend loopback 监听 |

**传输栈**：`SvUdpTransport`（`sv_network_mp.hpp:40-88`）；`start()/stop()`（`sv_network_mp.cpp:22-40/42-62`）；`NET_Frame` 每帧最多 `MaxPacketsPerFrame=64` 收包 → `ServerCore::NET_DtlsPacket`（`sv_network_mp.cpp:64-111`）；`NetUdpSocket`（`win32/win_net.hpp:28-61`，`AnyIpv4Address=0`，`SocketAlreadyBoundError=10037`）；`NET_IPSocket`/`close`/`NET_GetPacket`/`NET_SendPacket`（`win_net.cpp:28/113/136/182`）。
**DTLS 状态机**：`DtlsPeerSystem::NET_DtlsPacket`（`qcommon/net_dtls_cod.cpp:544`；INIT `:570`；COOKIE_ECHO `:608`；DATA `PacketType=0x06` `net_dtls_cod.hpp:45`）。握手序列 **INIT(0x01) → INIT_ACK(0x02) → COOKIE_ECHO(0x03) → COOKIE_ACK(0x04) → DATA(0x06)**。
**netchan**：`Netchan_Process`（`net_chan_mp.cpp:660`）、`Netchan_Transmit`（`:1012`）、`Netchan_TransmitNextFragment`（`:1061`）、`NET_IsConnectionlessPacket`（`:617`）。
**控制消息枚举（`DedicatedControl.hpp:23-82`）**：`Booking=1, CaptureLoadout=2, SessionStart=3, ConfigureSession=4, QueryEndpoint=5, QueryGameplayStatus=6, SetNoclip=7, UpdateLoadout=8, RunDiagnostic=9, PlayAnnouncer=10, SendRawCommand=11, DebugGrantBattery=12, RoomConnect=16..RoomCanonicalizeSession=20`；`MaximumPayloadSize=16*1024`。
**客户端状态机**：`enum class ClientState { Free, Connected, ClientLoading, Active }`（`sv_client_mp.hpp:63-69`，注明为**语义状态机，非原生枚举序数**）。
**会话/名册**：`stageSessionRoster`/`commitSessionRoster`/`rollbackSessionRoster`（`sv_main_mp.cpp:1605/1613/1619`）。

### 3.4 游戏逻辑 / 帧循环 / 客户端通信

- 帧回调 `onServerFrame(now)`：`Appmain.cpp:6437`；`if (!runsGameServer(role)) return` `:6603-6604`；`ensureDedicatedControlServer()` `:6606`；`processDedicatedControlMessages()` `:6607`；`Network.NET_Frame(Server, now)` **`:6633`**；出包 `NET_SendPackets` `:6710`。
- `ServerCore::runFrame` **`:8376`**（`sv_main_mp.hpp:985`）；20 Hz 编排 `SvServerWorld::beginFrame → ClientThink → endFrame`（`game_server.md:316-318`）。
- client ingress：`SV_ConnectionlessPacket`（`sv_client_mp.cpp:492`；getchallenge `:512`；connect `:514`）、`SV_PacketEvent`（`:643`）、`SV_GetChallenge`（`:3262/3360`）、`SV_DirectConnect`（`:3384`）。
- gamestate/snapshot：`configureGameState`（`sv_main_mp.cpp:1635`）、`configureMatchRules`（`:1772`）。

### 3.5 `CodolGameServer.Localnet32` 的职责与导出

**职责**：**客户端进程内嵌 authoritative 战斗服务器**（32 位 DLL，非独立 exe）。载入方式：Localnetworking 枚举 `Ayria\Plugins\*.Localnet32` → `LoadLibraryW` → `GetProcAddress("Createserver")`（`Localnetworking.cpp:367-379`、`:400-414`）。
**导出（实测 54 个 `__declspec(dllexport)`）**：生命周期 `onStartup`(`:8142`)、`onInitialized`(`:8147`)、`Createserver`(`:8155`)；配置 `ConfigureSession`(`:8494`)、`ConfigureGameState`(`:8648`)、`ConfigureBooking`(`:8812`)、`SetEnabled`(`:8160`)；以及大量 `CODOL_GameServerGet*Status` 诊断 getter（`:8176…9499`）。
**`UNKNOWN`**：`Appmain.cpp:8512/8571/8602/8617/8926/9014/9049/9072/9105/9144` 十处多行声明导出的精确符号名（`.exp` 为二进制，本轮未反汇编）。

### 3.6 combined / dedicated / client 三种角色

`ProcessRole.hpp`：`combined`（默认，兼容旧单进程）/`client`（backend 依附客户端 socket bridge，仅装最小 Com_Frame hook 做 session capture，**不跑 gameplay**）/`dedicated`（仅游戏服务器，装 gameplay hook + 控制端口并在**游戏线程**消费 `SessionStart`）。`runsBackend = role != Dedicated`；**`runsGameServer = role != Client`**。
`UNKNOWN`：生产环境是否真的设置 `OLMOD_PROCESS_ROLE=dedicated` / `OLMOD_HOST_ADDRESS`（树内只有读取方，无启动脚本）。

### 3.7 `Createserver` 的现有实现与调用关系

```cpp
// Appmain.cpp:8152-8154（注释原文）
// The archived CODOL Localnetworking loader retains only modules exposing this
// entrypoint. This plugin does not proxy a hostname, but must remain loaded once
// its in-process frame hook is installed.
extern "C" __declspec(dllexport) void *__cdecl Createserver(const char *)  // :8155
{
    return nullptr;                                                        // :8157
}
```

**调用者**：`src/localnetworking/Localnetworking.cpp:400-414`（`Bridge::claimsHost`）—— 遍历已加载 plugin，`GetProcAddress(module,"Createserver")`（`:404`）→ `callback(key.c_str())`（`:407`）→ 非空则记入 `resolvedHosts`（`:409-410`），否则记入 `rejectedHosts`（`:413-414`）。
⇒ 战斗服务器返回 `nullptr`，故 Localnetworking **不会**把它登记为 hostname 归属方；它靠"被 `LoadLibrary` 后 `onStartup/onInitialized` 触发 `initialize()`"生效。**对照**：backend 的 `Createserver` 才返回真实 `IServer*`（`src/backend/Appmain.cpp:19`）。

### 3.8 已有测试目标与实际结果

| 目标 | `xmake.lua` 行 | 实际结果 | 证据 |
|---|---|---|---|
| `ol_transport_lifecycle_tests` | :326 | **checks=106 failures=0**，run exit=0（强制全量重建 30.171 s） | `T1_ACCEPTANCE_REPORT.md:15-17,71` |
| 同测试（中间版本） | — | `_p1_build/_p1_diag` **105/7**（修复前）；`_p1_run2/_p1_final` 105/0 | `T1_ACCEPTANCE_REPORT.md:217-220` |
| 同测试（T-2 口径） | — | **checks=124 failures=0** | `T2_IMPLEMENTATION_AND_TEST_REPORT.md:19,244` |
| `ol_game_server_tests` | :258 | run exit=0（`LIVING_WEAPON`/`ZM_*`/`FACTORY_*`/`BATTERY_CG` 等断言输出） | `_run_tests.log` |
| `ol_dedicated_control_tests` | :285 | exit=0，`Dedicated control tests passed` | `_run_tests.log` |
| `ol_playerdata_def_tests` | :272 | exit=0，`PlayerDataDef tests passed` | `_run_tests.log` |
| `ol_lua_runtime_tests` | :311 | BUILD/run exit=0 | `T2_IMPLEMENTATION_AND_TEST_REPORT.md:246` |
| `ol_backend_tests` / `ol_localnetworking_tests` / `ol_platformwrapper_tests` | :245 / :339 / :367 | **本副本无运行证据**（`build/bin/release` 只有 3 个 game_server 系 exe） | 目录实测 |
| `CodolGameTests.py`（Python 工具） | — | **Ran 59 · FAILED (failures=1)**：`test_only_dedicated_uses_native_qa_launch_bypass` | `_t23_caller_tests.log` |

> **明确的测试覆盖缺口（最大工程风险）**：`game_server_core`（`xmake.lua:92-107`）只含 `client_bridge/`、部分 Client*/Dedicated*/DisconnectWitness/PlayerDataDef、`qcommon/`、`server_mp/`、`win32/`、`shared/`。**仅生产插件 `ol_game_server` 才编译的 9 个文件**（`xmake.lua:199-209`）：`Appmain.cpp`、`EngineBindings.cpp`、`NativePmoveBindings.cpp`、`NativeWeaponMovementBindings.cpp`、`NativeWeaponBindings.cpp`、`ClientNoclipHotkey.cpp`、`NativeEntityStateBindings.cpp`、`ClientCommandTrace.cpp`、`FrameHook.cpp` —— **合计 31,953 行、零直接测试**。

### 3.9 服务器自身已实现 vs 依赖原版客户端引擎

**A. 服务器自身已实现（可离线构建/测试；无真实运行证据）**
UDP socket 生命周期与 `SvUdpTransport`；DTLS 状态机（含固定向量测试）；netchan 分片/重组/ACK/reliable；会话/名册；控制面 28961/28962/28970；`server_mp/*` 全部模拟/序列化/模式/脚本源码；Lua 5.4.8 静态 VM + `kind:name` builtin registry。
**B. 依赖原版客户端引擎才能完成（全部在 `bind()` 之后）**
`EngineBindings` 全部（宿主映像 + 145/146 RVA + 82 守卫）；`FrameHook` 对 `0x0FEA20` 的写跳转；`ClientProcessPatches`（含 `0x8371A`）；`DedicatedProcessPatches`；`CM_LoadMap/CM_LinkWorld` 世界加载；原生 DB/Msg/CCS/Trace/Pmove/weapon registry。

> **判定**：当前状态是"**接口不兼容 + 初始化条件不满足**"，**不是**"缺实现"（`COMBAT_SERVER_RECOVERY_BASELINE.md:262-264`）。

### 3.10 已知未实现功能 / 失败路径 / 兼容性问题

| 项 | 状态 | 证据 |
|---|---|---|
| 通用 `G_Damage` | partial，**缺 9 依赖**；pain/view kick/score/killcam/respawn 未闭环 | `CODOL_SERVER_PROGRESS_20261009.md:119-124`；`game_server_coverage.md:28` |
| `g_run_frame_for_entity` | **missing**（矩阵唯一 missing） | 同上 :114 |
| Lua thread/wait/endon/通用 notify | 10-09 记 ❌ 无；`.agents/modules/gsc.md:69` 记后续已补第一阶段 `codol.thread`/`codol.wait`（两说并列） | `CODOL_SERVER_PROGRESS_20261009.md:173`；`gsc.md:69` |
| CODOL per-client PVS 可见性策略 | 未恢复 | `game_server_coverage.md:24` |
| SD 回合状态机 / 炸弹 / plant/defuse / objective | 全部"部分，中低" | `game_server_coverage.md:50-59`；`CODOL_SERVER_PROGRESS_20261009.md:256` |
| 世界模型缩放 `1.0f` producer | 未定位（`TODO(CODOL)`） | `game_server_coverage.md:25,74` |
| 后端独立 daemon | 未实现 | `backend.md:7` |
| launcher 多实例 / 双真实客户端自然闭环 | 未完成 | `CODOL_SERVER_PROGRESS_20261009.md:94` |
| 部署件陈旧 | 构建 `DBA7273A…` ≠ 部署 `6D493B82…` | `COMBAT_SERVER_RECOVERY_BASELINE.md:42-52` |
| 文档漂移 | `codol_server_function_matrix.json`（指向 3.3.3.3）、`game_server_coverage.md`（2026-08-16）落后于代码 | `CODOL_SERVER_PROGRESS_20261009.md:290` |

---

## 4.（D）战斗创建链路的历史研究【重点】

### 4.1 两套并行的"战斗创建链路"

| 线 | 链路要素 | 终点 |
|---|---|---|
| **ol-mod 线** | Localnetworking 载入插件 → `initialize()` → `bind()` → `installFrameHook(Com_Frame)`；后端 `ConfigureSession` → DedicatedControl 28961 → `Network.start()` → UDP 28960；`SessionStart` schema v5 → 地图/CCS/booking/gamestate | 进程内 authoritative server |
| **协议逆向线** | lobby(3074) → `0x81/0x82/0x83` → `0x85` 任务帧 → `6/14 mmbook/mmstart` booking → 战斗地址下发 → UDP 28960 → NAT/DTLS/ECDH → getchallenge/connect/stats/heartbeat → gamestate → snapshot | Python `battle_server.py` |

> **两线关系 = `UNKNOWN`**。协议逆向线在其 `STAGE_REPORT_BATTLE.md` P0-2 明确记录：**当时全机找不到 ol-mod 源码**（`E:\handoff2\ol-mod-olfinal.zip` 不存在），因此它是**独立重建**的。二者是否可互换、是否同一协议，均无证据。

### 4.2 逐问回答

**D-1「从大厅进入战斗的真实入口」**
- ol-mod 线的**客户端入口**：未在 ol-mod 源码中定位到"大厅按钮 → 战斗"的函数；已记录的是后端侧驱动：`ready room message (event 8) → FIND_SERVERS → mmbook → mmbook accepted (event 21) → mmstart → gameplay connection challenge`（`playable_architecture.md:140-147`）。
- 协议逆向线的**客户端入口**：`findSessions`（`0x15/5`，query kind 1=FIND_SERVERS / 3=FIND_LOBBIES_BY_PLAYLIST）→ `6/14 mmbook` → `mmstart`；`21/5` 返回 mission session 对象。
- **明确否证（协议逆向线）**：客户端把对局流量送到**外部腾讯地址** `101.67.36.18:10035`（发送方为 `gcloudvoice.dll`），600 秒日志中 `28960` 出现 **0 次** ⇒ 客户端**未采用** session 里下发的 `127.0.0.1:28960`（`BATTLE_SERVER_PROTOCOL.md` §8.9）。
- 结论：**"从大厅进入战斗的真实入口"在两线上都未闭合**；ol-mod 线未做客户端入口定位，协议逆向线定位到 booking 层但地址路由被否证。`BATTLE_ENTRY = NOT_OBSERVED`。

**D-2「战斗创建请求如何产生」**
- 后端 `MatchmakingService`：`mmbook → mmstart → BookingSink → DedicatedBookingDispatcher`（单 worker、递增 request ID、capture 失败最多重试 3 次）（`CODOL_SERVER_PROGRESS_20261009.md:83`）。
- 客户端桥在 `Com_Frame` 上捕获**原生 booking selection + item-ID loadout**（`CODOL_SERVER_PROGRESS_20261009.md:72`）。
- 协议逆向线：`0x15/5` 的 leading query discriminator 被忽略曾导致客户端收到"自己创建的 lobby session"作为服务器，最终 `EXE_CLIENTFAILEDTOCHALLENGE`；修正后排除本地玩家 lobby（`playable_architecture.md:149-159`）。
- **`UNKNOWN`**：`6/14 mmbook/mmstart` 应答的**帧格式**（协议逆向线记录为 UNKNOWN，且已实测用靶场信封回答 → 9/9 断连）。

**D-3「哪些函数负责选择地图/游戏模式或初始化战斗会话」**
| 函数/对象 | 地址 | 说明 |
|---|---|---|
| `DB_LoadXAssets` | `0x0049F960` | zone/地图资产加载 |
| `CM_LoadMap` / `CM_LinkWorld` | `0x00585B20` / `0x0058C810` | collision/world 加载与链接 |
| `CCS_InitializeConstantConfigStrings` | `0x005850B0` | 构建本地 NCS 表，`CL_ParseGameStateMessage` 比较该值 |
| `CL_ParseGamestate` / `CL_ParseGameStateMessage` | `0x02DF7D90`（后者用于 checksum 比较） | 客户端解析 gamestate |
| `CL_ParseSnapshot` | `0x0046D170` | 客户端解析 snapshot |
| `bdCommonAddr_Serialize` | `0xA36F60` | 37 字节地址布局 |
| `CG_ConfigStringModified` | `0x0057A300` | 客户端 configstring 分派 |
| **原版"战斗会话创建"函数** | — | **`UNKNOWN`** |

**D-4「战斗创建入口与 `CodolGameServer.Localnet32` 的关系」**
- `CodolGameServer.Localnet32` **不是**通过 `Createserver`/IServer 接口参与战斗创建（它返回 `nullptr`）。
- 它的战斗创建参与点 = **`Com_Frame` hook** + **DedicatedControl 控制面**：后端下发 `ConfigureSession` → `Server.configureSessionDescriptor()`（`sv_main_mp.cpp:1563`）→ `Network.start()` → bind `0.0.0.0:28960`（`win_net.cpp:113`）→ `Server.setEnabled(true)`（`sv_main_mp.cpp:1166`）。
- **结论**：`Createserver` 与战斗创建**无关**；这两者的"关系"是**同名但不同职责**（Localnetworking 的 hostname 认领 ABI）。

**D-5「`Createserver` 为什么返回 `nullptr`，原始依据是什么」**
- **原始依据 = 源码注释本身**（`Appmain.cpp:8152-8154`，见 §3.7）：该导出只为"让归档的 CODOL Localnetworking 加载器保留本模块"，插件**不 proxy hostname**。
- **调用者证据**：`Localnetworking.cpp:400-414` 的 `claimsHost` 会依次调用各 plugin 的 `Createserver`；返回 `nullptr` 即记录为 `rejectedHosts`。
- **旁证**：backend 的 `Createserver`（`src/backend/Appmain.cpp:19`）返回真实 `IServer*`，因此 hostname 认领由 `Alwaysoffline.Localnet32` 承担（其日志确有加载记录）。
- **不得据此推出的结论**：`Createserver == nullptr` **不表示**战斗服务器未实现、未加载或不工作；它已于 2026-10-10 被证明**确实被加载**（见 §6.2）。

**D-6「服务器插件如何进入加载流程」**
`Injector32.exe → Bootstrapper32.dll → Ayria\Plugins\*.Ayria32（Localnetworking.Ayria32 / Platformwrapper.Ayria32）→ Localnetworking 枚举 Ayria\Plugins\*.Localnet32 → LoadLibraryW → GetProcAddress("Createserver")`（`Localnetworking.cpp:367-379`；`COMBAT_SERVER_RECOVERY_BASELINE.md:96-128`）。
**实测**：`Bootstrapper32.log` 记 2 个 `.Ayria32` 插件；`Localnetworking.log` 记 2 个 `.Localnet32` 插件（含 `CodolGameServer.Localnet32`）。

**D-7「引擎绑定成功后，预期如何进入帧循环」**
`bind() → Appmain.cpp:8128 installFrameHook(Bindings, onServerFrame) → FrameHook.cpp:39-71` 在 `module+0x0FEA20` 写 `0xE9` 相对跳转 → 引擎每帧调用被 hook 的 `Com_Frame` → `comFrameHook`（naked）先 `call [OriginalComFrame]`，再 `pushfd/pushad` → `runServerFrame` → `Callback(GetTickCount())` = `onServerFrame`。
**状态**：**从未到达**（`bind()` 未通过）；**无任何真实运行的帧循环证据**。

**D-8「网络监听与实际战斗会话之间的关系」**
**监听是结果，不是目标**：没有后端会话配置，**28960 不会监听**。
`backend ──ConfigureSession──► DedicatedControl:28961 ──► Server.configureSessionDescriptor()（sv_main_mp.cpp:1563）──► Network.start()（sv_network_mp.cpp:20）──► bind(0.0.0.0:28960)（win_net.cpp:113）──► Server.setEnabled(true)（sv_main_mp.cpp:1166）`
**实测**：三次启动中 28960 **从未监听**（沙箱探针记录 28960/28961/28962/28970 全部无监听）。

**D-9「客户端进入地图及开始对局所需的协议与状态转换」**
- ol-mod 线（源码级）：DTLS **INIT(0x01) → INIT_ACK(0x02) → COOKIE_ECHO(0x03) → COOKIE_ACK(0x04) → DATA(0x06)**；解密后 `0xFFFFFFFF` 前缀 ⇒ `SV_ConnectionlessPacket`：**getchallenge → challengeResponse → connect → connectResponse**；在册 XUID 校验 ⇒ `ClientState::Connected → ClientLoading → Active`；gamestate（configstring 0 serverinfo / 2 `cod` / CCS checksum）+ snapshot。
- 协议逆向线（真实抓包逐字节，2026-10-04/10-07）：NAT 29B → DTLS init 16B → **38B cookie** → cookie+公钥 **219B** → **114B key-exchange ack** → 数据帧 `06 02 <serverTag:2> <seq:2> <hmac8> <len:2> <cipher>` → `getchallenge` → `challengeResponse` → `connect` → `connectResponse` → `stats` → `statResponse` → `heartbeat` → usercmd(14B) → gamestate(259B) → 运动快照（字段序列 **29/29 对齐实录**）。
- **`UNKNOWN`**：客户端"进入实际地图并开始对局"的**完成判据**在两线上都未取得（协议逆向线记录：早期合成 snapshot 使客户端越过 `waiting for player data` 进入地图，但**世界全黑、玩家不在有效出生状态**）。

### 4.3 必须记为 UNKNOWN 的调用关系（禁止按常见架构补全）

1. 原版引擎中独立的"战斗/会话创建"函数（`Createserver` 之外）。
2. 原版 `NET_Frame` 引擎函数；现有 `NET_Frame` 是项目源码。
3. 原版 gametype/playlist 初始化入口。
4. `6/14 mmbook/mmstart` booking 应答的**帧格式**；DedicatedControl 的客户端桥**端口号**与帧格式（协议逆向线记录为 UNKNOWN）。
5. 客户端"对局流量地址"的真实来源（`gcloudvoice.dll` 发出到 `101.67.36.18:10035`，但**谁下发该地址未定位**）。
6. ol-mod 线与协议逆向线的接口关系。
7. 运行时映像 O-4 的 PE 头与 RVA 字节（`0x0FEA20` / `0x8371A`）。

---

## 5.（E）启动至大厅的已固化成果（作为战斗服务器的既有基础与保护边界）

### 5.1 权威层级

| 优先级 | 文件 | 说明 |
|---|---|---|
| 1 | `REF_LOBBY_KIT/GOLDEN-LOBBY-001.md` + `_golden_hashes.json` | 2026-10-07，`STATUS=FROZEN`，**唯一权威复现依据** |
| 2 | `DEV-REPRO/REPRODUCTION-BASELINE-LOBBY-001.md` | 2026-10-08 v1.0；SOP/判据/回滚手册 |
| 3 | `REF_LOBBY_KIT/HANDOFF_20261007_TAKEOVER.md` | 总入口交接 |
| 4 | `HANDOFF_20261005_LOBBY_REACHED.md` | 2026-10-05 16:36 首次进大厅实机记录 |
| 5 | `DEV-REVIEW/MASTER-POST-LOBBY-FULL-HISTORY-001.md` | 大厅之后全量工程考古总账 |

### 5.2 已成功复现的启动流程（exe → 大厅）

```
0) 提权代理（人工批 UAC）  CODOLServer/_mainline/elevated_agent.py → agent_client.py ping
                          期望 {ok:true, debug_privilege:true}
1) REF_LOBBY_KIT/run_all.py：写 hosts（# CODOL-LOCAL-BEGIN/END）
   127.0.0.1 formal-zone-auth.codol.qq.com / 127.0.0.2 formal-zone-lsg.codol.qq.com
   + 写 <GAME ROOT>/dwauth.ini + 生成/追加本地 CA 进 cacert.pem
2) 认证服务 127.0.0.1:3074  fake_auth_tls.py（TLS，POST /auth/）
3) 大厅服务 127.0.0.2:3074  lobby_server.py（明文 lsg）
4) nt10.py：清残留 → 创建互斥 Global/{5BD75B76-601A-4b20-80C8-D2317C94BB30}
   → Popen([<GAME ROOT>/codoMP_client_shipRetail.exe], cwd=<GAME ROOT>)（无额外参数）
   → 观察 4s，坏启动(0xC0000005)最多重试 6 次 → 4 个内存补丁 + KDF hook @0x00BA0D20
5) 客户端：IIPS/IFS2 载入（t=8.094 / 9.160 / 15.245 s）→ /auth/ 200
   → 大厅 TCP → 0x81(204B) / 0x82(153B) / 0x83(204B) → 0x85 任务帧
   （u32 len | 0x86 | service | ver | task）
6) 大厅 UI：窗口类 CODO、标题「使命召唤online」、keepalive 持续
```

**进大厅 5 条判据**：① `lobby_srv.log` 出现「=== 大厅连接建立 ===」且「[keys] 试解命中」；② 首帧 `hmac=OK marker=0x86`；③ 出现 keepalive；④ 收到 `8/1` `8/2` 档案与 `10/21` 发行方配置；⑤ 全程 `hmac=BAD = 0`。
**实机锚点**：2026-10-05 16:36，任务 34→47；截图 `REF_LOBBY_KIT/lobby_window.png`；冻结指标 `lobby_srv.log` 134,649 B（建立 23 / keepalive 15 / hmac=OK 235 / hmac=BAD 0）。

### 5.3 启动器 / TCLS / Ayria / 平台模块的已确认关系

| 模块 | 已确认关系 |
|---|---|
| **TCLS（官方登录器）** | **Golden 路径不参与**：由 `nt10.py` 直接拉起 exe，不走 TCLS/Client.exe 或 WeGame |
| `WIN_NO_TCLS` 判定 | 判据是**命令行是否含 `-q` / `-qa`**，不是父进程或 Client.exe 查找 |
| TCLS 共享内存 | `TCLS_SHAREDMEMEMORY<十进制PID>` = 512 KiB 命名映射；producer `tcls_core.exe sub_7D10`，consumer `TenProxy.dll CTclsProxy::Initialize`；载荷为 tag 容器（version 0x40 @+0） |
| TCLS 目录协议 | DIRTREEREQ 33B / DIRTREERESP 774B、26B 固定头；本机复刻**字节一致** |
| ServerDir 语义 | 目录走 `tcls.qq.com:10009`；目录里**没有** CODOL 大厅地址（只有测速 URL）；无有效条目时**不连默认 IP** |
| **CODOLLauncher** | 自研 Win32 启动器；在 `ResumeThread` **之前**创建 `TCLS_SHAREDMEMEMORY+pid`；实测仍到致命错误窗口、`BOOT_DEPTH=2` ⇒ **仅 TCLS 映射不足以推进** |
| **Ayria（ol-mod 战斗线）** | `Injector32.exe → Bootstrapper32.dll → Plugins/*.Ayria32 → Localnetworking 枚举 *.Localnet32 → LoadLibraryW + GetProcAddress("Createserver")`；backend TCP `127.0.0.1:4200` |
| IIPS/IFS | IFS 是 IIPS 的本地归档/VFS 子系统（`ifs2.dll`）；`enable_iips=1` 是启动链闸门 |
| EngineBridge(RM) | Gate 跨越后引擎 standby：RM vtable 0 调用、无 FF/Zone/Asset 文件访问；结论 = 由 Base VM dispatch continuation 控制 |

### 5.4 已验证的环境条件与文件指纹

| 项 | 值 |
|---|---|
| `codoMP_client_shipRetail.exe` | 7,841,344 B / `36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537` / FileVersion 1649370 |
| `codoMP_client_shipRetailBase.dll` | 60,327,992 B / `EF75220DE1D6973F34C7069F5BF211B11BD61520C6C0DE1882F7359FA5BC6A20` |
| PE 特征 | PE32 x86、EntryRva `0x0E5DC690`、TimeDateStamp `0x6096930A`、**SizeOfImage `0x0E659000`**、7 段 `.tp3`×6+`.tvm0`（TenProtect 加壳） |
| `iips.dll` 原件 / 本项目 PE 手术产物 | 347,704 B / `72ddb9d1…`；380,928 B / `2ed47824…` |
| `IFS2.dll` | 601,656 B / `5b0324e0…8421` |

```
<GAME ROOT> = run_codol_001/sandbox_datafix_20260929
dwauth.ini  = formal-zone-lsg.codol.qq.com 3074 / formal-zone-auth.codol.qq.com 3074 / 0x03EA  (79 B)
iips.ini    = enable_iips=1 / iips_url="http://10.231.2.181/"  (46 B)
hosts       = 127.0.0.1 formal-zone-auth / 127.0.0.2 formal-zone-lsg
端口        = 3074 TCP(auth,必需) / 3074 TCP(lobby,必需) / 28960 UDP(battle) / 443,80,8081 应空闲
```

### 5.5 固化基线 / 完整性清单 / 复现文档位置

- 冻结目录 `GOLDEN-LOBBY-001/REF_LOBBY_KIT/`（只读；**缺 patch_spec/tas_spec/lobby_spec/late_spec 与 5 个数据目录**）。
- 清单与哈希：`REF_LOBBY_KIT/GOLDEN-LOBBY-001.md`、`REF_LOBBY_KIT/_golden_hashes.json`（9 个核心文件）。
- 复现手册：`DEV-REPRO/REPRODUCTION-BASELINE-LOBBY-001.md`。
- Publisher 数据副本：`DEV-PUBLISHER-RESTORE/REF_LOBBY_KIT/`。
- T-1 基线：`T1_VERIFIED_BASELINE.md`（checks=124 failures=0）+ `_t1_fix_evidence/REPRODUCE.ps1`。
- T-2 清单：`T2_SHA256_MANIFEST.txt` … `T2_ACCEPTANCE_SHA256_MANIFEST.txt`。
- 战斗服务器基准 / 制品门禁 / 路线：`COMBAT_SERVER_RECOVERY_BASELINE.md`、`ARTIFACT_BLOCKERS.md`、`CODOL_RUNTIME_BLOCKER_CLEARANCE_20261009.md`、`NEXT_PHASE_PLAN.md`、`BASELINE_ADJUDICATION.md`。

### 5.6 已知会破坏既有启动链的操作及其风险（15 项，摘要）

| # | 操作 | 后果 |
|---|---|---|
| 1 | 开启 `firingrange-booking-push.enabled`（现名 `.OFF_CONFIRMED_CRASH`） | **实测 9/9 断连**，必须保持关闭 |
| 2 | 加 `--tas` / 注入 TAS | 实测**卡住**；默认 `tas_off.flag` |
| 3 | 把 `iips.ini` 的 `enable_iips` 改回 0 | **直接失去启动链** |
| 4 | 自编 80/70 SKU 页 / sentinel / itemgroup 页 | 商城+仓库变灰、角色被锁，该会话不可恢复（已发生 3 次） |
| 5 | 用靶场信封回答 PvE booking | 9/9 断连 |
| 6 | `replyId` 独立计数器 / 推送 seq +1000 | 断连；已回退 |
| 7 | 在 Golden 目录直接跑 | 复现 `EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE` |
| 8 | 残留 `codoMP_client_shipRetail`/`TP3Helper`/`IIPSHostApp` | 单实例互斥冲突 → 坏启动 `rc=1 t≈10s` |
| 9 | 非提权运行 / 拒绝 UAC | run_all 链硬拒绝 |
| 10 | `--plain-port 8446` 与 dwauth 端口不一致 | `DW_LOBBY_ERROR` |
| 11 | 关闭/配置/规避 ACE、TenProtect | 纪律禁止；历史实测蓝屏 `0x01010002` |
| 12 | 改 `lobby_server.py` 的 `0x83` challenge 来源 / 去掉 playlist 同义名回退 | 前者任务降回 0 条；后者致命弹窗回归 |
| 13 | 裸跑 `xmake` / `xmake build`（无目标名） | `ol_deploy` 是 `set_default(true)` → **会触发部署** |
| 14 | 旧 OfflineServer 残留 `127.0.0.1:443` + portproxy 443→8443 | 与 Golden 要求的 443/80/8081 空闲不符 |
| 15 | 无 ground-truth 自检地覆盖写 `mkt_assets/item_sku_arrays.csv` | 可信表被写坏（已发生一次） |

### 5.7 当前工作区与历史副本的隔离约束

| 副本 | 角色 | 约束 |
|---|---|---|
| `COD OL/` | 出厂原件（974 个 IIPS .ifs） | **只读** |
| `REF_LOBBY_KIT/` | 开发副本（约 26.7 GB，含内存转储） | 实验在此进行；`mem_*` **用户明确要求勿删** |
| `GOLDEN-LOBBY-001/REF_LOBBY_KIT/` | 冻结只读基线 | 只读；改前先复制 |
| `DEV-PUBLISHER-RESTORE/REF_LOBBY_KIT/` | 数据恢复/实验副本 | 可实跑 |
| `run_codol_001/sandbox_datafix_20260929` | 当前 `GAME_ROOT` | 无文档声明不可改（UNRESOLVED） |
| **F** = `F:\桌面\ol\ol-mod-olfinal` | **战斗线唯一活动基准** | 新源码/构建/测试只允许在 F |
| **D** = `_e1_regression/ol-mod-olfinal` | **冻结历史回归副本**（robocopy 自 F，2026-10-09 18:27） | **只读**：禁构建/运行/写入/清理/同步 |

---

## 6.（F）所有真实运行证据

> **严格三分**：① 真实客户端运行；② 离线测试/模拟；③ 静态检查。三者在本节分列，不混为一类。

### 6.1 真实客户端运行证据 #1 —— 2026-10-10 三次战斗服务器启动（本项目历史上首次产出战斗服务器运行日志）

**位置**：`E:\CODOL_SANDBOX\RUN001\Ayria\Logs\`（本轮实测该目录存在，6 个日志）
**日期与编号**：2026-10-10 15:47:48 / 15:48:28 / 15:50:14（三次）
**实际运行目标**：`E:\CODOL_SANDBOX\RUN001\codoMP_client_shipRetail.exe`（7,841,344 B，`36997674…`）
**实际执行动作**：照搬出货启动器 `Launch_OLMod.bat` 的调用形式（`Injector32.exe "codoMP_client_shipRetail.exe"`，**无参数**、**不设 `OLMOD_PROCESS_ROLE`** ⇒ 角色 = `combined`）。**不是** `CodolGame.py launch`（该入口失败，见 §6.5）。

| 日志 | 关键内容 | 意义 |
|---|---|---|
| `Localnetworking.log`（2,356 B） | `Loaded Localnet32 plugin Alwaysoffline.Localnet32.`<br>**`Loaded Localnet32 plugin CodolGameServer.Localnet32.`**<br>`Localnetworking backend listening on 127.0.0.1:4200.`<br>多条 `sendto-target pid=23828 … target=122.96.96.225 port=8081`、`connect-target … 218.60.84.93:443` | **战斗服务器插件确实被加载**（调用约定问题已答） |
| **`CodolGameServer.log`**（582 B） | **`[combined/game-server] engine binding failed`** ×3（每轮 1 条）<br>紧随 **`LOGSTALL lockUs=0 fileUs=913 consoleDebugUs=143018 prefix=engine binding failed`**（三次分别 913/359/386 µs、143018/141923/138151 µs） | 初始化在**引擎绑定**处失败；三次完全一致；**且无任何 stage/前缀不匹配日志** |
| `AlwaysofflineRe.Localnet32.log`（339 B） | `Refused to apply CODOL startup patches to an unknown executable image.` ×3 | **按设计如此**（`CodolClientPatches.cpp:30-46,610-616` 的 O-2 门禁），不是故障 |
| `Bootstrapper32.log`（110 B） | `Loaded plugin "Localnetworking.Ayria32"`、`Loaded plugin "Platformwrapper.Ayria32"` | `.Localnet32` 由 Localnetworking 加载，故 Bootstrapper 日志不含战斗服务器属正常 |
| `CODOLLauncher.log` / `T25_launcher_direct.log`（各 36 B） | `Could not create process. Error: 2` | 辅助启动器失败（见 §6.5） |
| `BugTrace.log`（12,541 B，15:49:40） | 内容为二进制/乱码形态的 TenProtect 崩溃/trace 记录 | 非战斗服务器证据，仅登记存在 |

**原始报告是否仍存在**：是 —— `COMBAT_SERVER_RECOVERY_BASELINE.md` §1.6、`CODOL_RUNTIME_BLOCKER_CLEARANCE_20261009.md` §0/§5。
**独立对照/复核**：本轮**独立重读**了全部 6 个日志（内容/时间戳/大小逐一吻合），并独立核实了"守卫失败必然写日志"（`RuntimeLog.cpp:60,77` 与 `bind()` 的 9 处 `return false`）。

### 6.2 由 §6.1 能证明与不能证明的（对 `Localnetworking.log` 那条证据的严格界定）

**能证明**
1. `CodolGameServer.Localnet32` **被 Localnetworking 成功 `LoadLibraryW`**（G-D1 调用约定问题已回答）。
2. 该模块的 `onStartup`/`onInitialized` → `initialize()` **确实被调用**（否则不会有 game-server 通道日志）。
3. 角色为 `combined`（日志前缀 + 启动器未设环境变量）。
4. `initialize()` 走到了 `Bindings.bind()` 并**返回 false**（`Appmain.cpp:7133-7137`）。
5. 失败发生在 `bind()` 的**3 个静默早退点之一**（`:3656` / `:3660` / `:3666`），而**不是** 82 条前缀守卫或后续 runtime_slots/message/glass 阶段（这些都会写日志）。

**不能证明**
1. **不能**证明失败是 `SizeOfImage` 还是 `TimeDateStamp` 还是 DOS/NT 签名 —— 三者中前两者在**同一个 `if`**（`:3662-3664`）。
2. **不能**证明全部 145/146 个 RVA 或 82 条守卫失效（它们**从未被执行过**）。
3. **不能**证明只需放宽尺寸检查即可通过（见 §7 冲突 C-7）。
4. **不能**证明 `Createserver==nullptr` 与加载失败有关（无关）。
5. **不能**证明 28960 曾被监听（相反，实测无监听）。

### 6.3 部署件与当前源码构建结果的差异（哈希证据，本轮独立复算）

| 制品 | 大小 | SHA-256 | 时间 |
|---|---|---|---|
| **F 构建产物** `F:\桌面\ol\ol-mod-olfinal\build\bin\release\CodolGameServer.Localnet32` | 6,559,232 | `DBA7273A0C9DD31CDD5619DD47B11C01EDC21AE17EEFC18FDD71F43B992097BC` | 2026-10-10 12:52:50 |
| **D 构建产物** `_e1_regression\ol-mod-olfinal\build\bin\release\CodolGameServer.Localnet32` | 6,556,672 | `0EABD5F54763976CA4A92CC4C0DBB34A5CC8E60DE6EBFE4A3C6FA28A6A157971` | 2026-10-09 17:32:40 |
| **stage/部署件（F 与 D 相同）** `…\build\stage\codol\Ayria\Plugins\CodolGameServer.Localnet32` | 6,556,672 | `6D493B820E84A21B096C9914616B75DCEC488920D7AC76867049B20C5C6B2021` | 2026-10-09 13:49:42 |
| **沙箱实际部署件** `E:\CODOL_SANDBOX\RUN001\Ayria\Plugins\CodolGameServer.Localnet32` | 6,556,672 | `6D493B820E84A21B096C9914616B75DCEC488920D7AC76867049B20C5C6B2021` | 2026-10-09 13:49:42 |
| 另一历史构建哈希 | — | `21D1481735828B48…` | `_batch2_build.log` |
| 其余 4 个运行时制品 | — | `Localnetworking.Ayria32 8F1BC5D4…100A`、`Platformwrapper.Ayria32 A7420E17…8D2F`、`Alwaysoffline.Localnet32 D2B9CA40…EF54`、`ol_room_owner.exe 354D5B29…BCB3` | 均与 build **SAME** |

⇒ **5 个运行时制品中只有战斗服务器本体是旧的**；当前源码树的改动**从未落到沙箱**。任何"改源码后直接跑"的验证都无效。部署清单 `ol-mod-runtime-manifest.json`（schemaVersion 1 / titleId 1004 / x86 / `gameExecutable=codoMP_client_shipRetail.exe`）。
**约束**：`ol_deploy` 被禁用；禁止本轮构建/部署重新验证。

### 6.4 制品门禁与身份测量（只读，静态）

- `_combat_baseline/pe_identity.log`：期望 `0x6096930A`/`0x0E5D6000`（源 `EngineBindings.hpp:438-439`）；实测客户端 `0x6096930A`/**`0x0E659000`**，`matchesExpected: false`；同时探测 `C:\Games\OLfinal\out.exe` **不存在**。
- `_combat_baseline/find_matching_client.log`：多份 `codoMP_client_shipRetail.exe` 副本全部 `0x0E659000`；**0 命中 `0x0E5D6000`**。
- `_combat_baseline/manifest_check2.log`：6 个插件/exe 的 SHA-256 与本轮独立复算**逐字一致**。
- 磁盘 RVA 实测（加壳件，**结构性必然不匹配**，不构成身份判负）：`0x0FEA20` = `03 C1 E0 06 50`（期望 `55 8B EC 56 57`）；`0x8371A` = `00 D9 45 10 8B 4D 08 8B`（期望 `83 7C 24 08 01 0F 94 C0`）。

### 6.5 启动/注入失败记录

| 记录 | 内容 | 证据 |
|---|---|---|
| `CodolGame.py launch --game-dir E:\CODOL_SANDBOX\RUN001` | **`Injector exited with code 1`**（命令 exit 3），属辅助工具参数形式问题 | `_t2_5_stageD_evidence/stageD_launch.log`；`COMBAT_SERVER_RECOVERY_BASELINE.md` §1.6 |
| `CODOLLauncher.log` / `T25_launcher_direct.log` | `Could not create process. Error: 2` | `E:\CODOL_SANDBOX\RUN001\Ayria\Logs\` |
| **Frida 注入该客户端** | **1 次尝试 `ProcessNotRespondingError`**（进程存活）；同机 32 位对照进程注入**成功**（`X86_AGENT_OK`，pid 14028 cmd.exe） | `COMBAT_SERVER_RECOVERY_BASELINE.md` §7.1 U7；`_t2_5_stageD_evidence/x86_agent_control.json` |
| T-2.4 Stage C/D/E/F/T | 全部 `NOT_AUTHORIZED`；且经静态分析，生成的状态脚本**并非无副作用**（装异常处理器 + ≤4 个 Interceptor 钩子 + 读约 58 B 内存） | `T2_4_RUNTIME_AUTHORIZATION_REQUEST.md`；`_t2_5_evidence/T2_5_RUNTIME_VERIFICATION_REPORT.md` |

### 6.6 真实客户端运行证据 #2 —— 协议逆向线的战斗服 UDP 会话记录

| 项 | 内容 |
|---|---|
| 证据文件 | `REF_LOBBY_KIT/battle_srv.log`（累计日志，328,335 B，mtime 2026-10-07 19:05:08） |
| 明确记录的真实会话 | `BATTLE_SERVER_PROTOCOL.md` §1 引用 `battle_srv.log 21:28:19~21:28:24`：**一次完整真实会话**，NAT/DTLS/ECDH/getchallenge/connect/stats/heartbeat/usercmd 逐字节解出 |
| 命令统计（本轮实测整文件） | `TX_DATA 400`、`TX_SPAWN_EXPERIMENT 354`、`RX_CLIENT_GAME_HEADER 205`、`RX_OOB 173`、`TX_GAME_OOB 124`、`TX_STAT_RESPONSE 29`、`RX_STATS 29`、`TX_GAMESTATE 27`、`RX_CANCEL_CONNECT 20`、`TX_DTLS_INIT_ACK 1`、`TX_DTLS_KEY_EXCHANGE_ACK 1` |
| 冻结基线口径 | `STAGE_REPORT_BATTLE.md` P0-1 记 `battle_srv.log 322,463 B（已监听 28960，收包=0）`；`BATTLE_ENTRY = NOT_OBSERVED` |
| **冲突** | 见 §7 C-4：同一文件既含"完整真实会话"，又与"收包=0"矛盾，且该文件**同样被离线自测路径写入**（`battle_selftest.py` 直接调用 `battle_server.handle_plain`）。**逐行来源无法用只读手段区分** ⇒ 该日志**不能单独作为**真实对局证据 |

### 6.7 离线测试 / 模拟证据（**不得当作真实运行**）

| 证据 | 内容 | 关键点 |
|---|---|---|
| `T1_ACCEPTANCE_REPORT.md` + `_batch10_evidence/T1_rerun_forced.log` | `ol_transport_lifecycle_tests` 强制重建 30.171 s，**checks=106 failures=0**，exit=0 | 真 socket 收发确有覆盖；但**没有**"OS 层绑定已释放"的反证用例（UV-1） |
| `_t1_fix_evidence/reproduce_20261010_130238.log`（51,899 B） | 哈希断言全绿 + `ol_transport_lifecycle_tests`/`ol_game_server_tests`/`ol_lua_runtime_tests` 全通过 + `xmake build ol_game_server` exit=0 | 另有首次失败记录 `reproduce_20261010_130228.log`（203 B，BOM 问题）**保留未删** |
| `_run_tests.log` | `ol_game_server_tests` / `ol_dedicated_control_tests` / `ol_playerdata_def_tests` 三套 exit=0 | 纯离线 |
| `build/bin/release/Ayria/Logs/CodolGameServer.log`（186,067 B，2026-10-09 13:52:25，1,496 行） | 含 `snapshot census`、`gamestate configuration ACCEPTED`、`server enabled false -> true`、`ZMSPAWN entity=64…` 等 | **是测试进程写出的**（`T1_ACCEPTANCE_REPORT.md:50` 明确记为测试 P1 用例副产物）⇒ **不得**当作真实客户端运行 |
| `battle_selftest.py` | 离线自测（不需游戏），可复现握手/快照 | 其输出与 `battle_server.py` 共用同一日志文件（§6.6 冲突根源） |
| `_battle_out.txt`、`_pve*_agent.out` 等 | 协议逆向线的脚本输出 | 需按调用方逐一区分真实性 |

### 6.8 静态检查证据（**不得当作运行**）

`pe_identity.log`、`manifest_check*.log`、`find_matching_client.log`、`.agents/audits/2026-10-09/artifact_provenance.json`、`GOLDEN_COPY_SPEC.md`、`codol_server_function_matrix.json`、`codol_gameplay_source_audit.json`、`runtime_module_load_order.csv`、`ICH044_*` 等。

### 6.9 文档自述但本工作区**不可复核**的运行证据

- 全部 `.runtime/natural-match/*` 自然实机运行（双客户端 FFA、SD 双客户端、性能数字、玩家确认结论）—— 该目录被 `.gitignore` 忽略且**本工作区不存在**（`CODOL_SERVER_PROGRESS_20261009.md` §9 R5）。
- `.agents/research/dedicated_two_client_validation_20260814.md`、`dedicated_sd_dual_client_validation_20260814.md` 记录的 2026-08-14 双客户端验证（分支 `v3.3.3.3-dedicated`，地图 `mp_crash_tropical`，模式 `sd`，日志引文 `SessionStart queued members=2`、`runtime clients=2 active=1 packets=408 snapshots=302`）。
- `playable_architecture.md:243-246`："The first native scaffold now lives in CodolGameServer. It is an x86 plugin loaded into the CODOL process… **For the validated QA build** it checks the PE identity and instruction prefixes, hooks CODOL `Com_Frame`…"

> **本轮关键的时间线重建（依据只读 git）**：commit `55fcdbf`（2026-08-18）"target out.exe (build 1649370): flip the host gate, the RVAs and the prefixes together"。`git show 55fcdbf^:src/game_server/EngineBindings.hpp` 中 `ExpectedTimestamp=0x57611E31`、`ExpectedImageSize=0x0C72A000`；`55fcdbf` 之后变为 `0x6096930A`/`0x0E5D6000`。⇒ 2026-08-14 的双客户端验证处于**门禁翻转之前（O-2 3.3.3.3 目标）**；而 2026-10-10 的三次失败处于**翻转之后（O-1 目标）**。这**在证据上解释了**两类记录为何看起来矛盾（详见 §7 C-16）。

---

## 7. 互相冲突的历史结论（**并列保留，不擅自消除**）

| # | 冲突 | 各主张 | 状态 |
|---|---|---|---|
| **C-1** | `E3823FD6…F37B` 归属 | ① `GOLDEN_COPY_SPEC.md:29` 称"客户端 EXE"；② `artifact_provenance.json:9` 称"OLFinal unpacked `out.exe`"；③ 本任务指令称属 3.3.3.3 QA 客户端；④ `.agents/AGENTS.md:174` 称"当前 active EXE SHA-256" | **四方互斥，未裁定** |
| **C-2** | `EngineBindings.hpp` RVA 常量数 | **145**（`FULL_ENCRYPTED…:80,161,480`）vs **146**（`CODOL_SERVER_PROGRESS_20261009.md:184`、`COMBAT_SERVER_RECOVERY_BASELINE.md:25`）；本轮实测：`static constexpr … *Rva =` **145**，宽口径去重标识符 **146** | 未裁定（口径差异已定位） |
| **C-3** | 前缀守卫数 | **82**（多份）vs **66**（git `55fcdbf` 描述，`FULL_ENCRYPTED…:254`）vs **78/79**（`artifact_provenance.json:38-41`，且明确是"加壳映像不匹配数"，未必是总数）；本轮实测 `std::equal(` = **82** | 未裁定 |
| **C-4** | `battle_srv.log` 是否含真实战斗会话 | ① `BATTLE_SERVER_PROTOCOL.md` §1 引其 21:28:19–21:28:24 为**完整真实会话**；② `STAGE_REPORT_BATTLE.md` P0-1 冻结记**收包=0**；③ 该文件**同样被离线自测写入**；④ 文件末段 19:04:56–19:05:08 有完整 UDP 会话 | **未定论**；逐行来源无法只读区分 |
| **C-5** | `EngineBindings.hpp:434-435` 目标构建 | 注释写 `0x57611E31, 0x0C72A000`（=O-2），而同文件 `:438-439` 常量是 O-1 | 已确认为**过期注释**，只建议改注释 |
| **C-6** | `codol_server_function_matrix.json` 参考构建 | 其 `reference_builds.codol.idb_path` 指向 **3.3.3.3 QA（2015-06-15）**，而源码 2026-08-18 已翻转到 `out.exe` 1649370 | **目录级漂移**，未处理 |
| **C-7** | "磁盘 `SizeOfImage≠期望` ⇒ 宿主身份不匹配" | 旧 B1 第 7 项推理 vs 更正：门禁读的是**运行时映像**，磁盘加壳头不是同一对象 | 已更正（`FULL_ENCRYPTED…:147`；`NEXT_PHASE_PLAN.md:39` A-4） |
| **C-8** | "`out.exe` 是项目根依赖" | `ARTIFACT_REQUIREMENTS.md` §A/§E、`SOURCE_FEASIBILITY` §11 Q2/Q5 vs 启动链默认目标与 Auth3 并列接受 | 已裁定**降级为逆向来源对象** |
| **C-9** | "时间戳相同 ⇒ 同一构建" | 常被推断 vs `sourceRelationRules`（`artifact_provenance.json:81-85`）明确禁止 | **禁止使用** |
| **C-10** | "全盘 0 个 `out.exe`" | `CODOL_RUNTIME_BLOCKER_CLEARANCE_20261009.md:40`（全盘）vs `ARTIFACT_BLOCKERS.md:36` 只做三授权根有界搜索 | **范围不一致** |
| **C-11** | 协议端口划分 | 早期"IIPS=8000，游戏=8801" vs 更正：`udp://ctrl.iips.qq.com:8000` 是 IIPS 补丁通道；协议端口仍未确证 | 早期结论**作废** |
| **C-12** | "网络走 GetProcAddress 动态解析、无静态 IAT" | 早期结论 vs 更正：IAT 存在，在 `.idata2`（21 DLL/748 槽） | 早期结论**作废** |
| **C-13** | `FrameHook.cpp` / `Appmain.cpp` 行数 | 报告 75 / 9,520 行 vs F 实测 117 / 9,546 vs D 实测 74 / 9,519 | 已解释为**报告基准是 D 树** |
| **C-14** | E-1 回归"证明新测试能抓旧缺陷" | D 侧 `checks=49 failures=0` vs 日志显示 `BUILD exit=-1` 后执行了从 F 复制的二进制 | **证据从未真正产生**（`BASELINE_ADJUDICATION.md` §4） |
| **C-15** | `REF_LOBBY_KIT` 核心文件是否已漂移 | `MASTER-POST-LOBBY-FULL-HISTORY-001.md` §13 D-20 称"已漂移" vs 本轮实测 `REF_LOBBY_KIT/` 与 `GOLDEN-LOBBY-001/REF_LOBBY_KIT/` **9/9 命中** `_golden_hashes.json`（而 `DEV-PUBLISHER-RESTORE/REF_LOBBY_KIT/` 确有 2 文件漂移） | 二说并列；使用前按 `_golden_hashes.json` 现算现验 |
| **C-16** | "本机从未成功初始化过一次" vs 2026-08-14 双客户端验证记录 | `COMBAT_SERVER_RECOVERY_BASELINE.md:9`（针对 OLfinal-live/1649370 线）vs `.agents/research/dedicated_*_20260814.md`（`v3.3.3.3-dedicated` 线） | **两条不同目标线**；且后者原始证据 `.runtime/` 不存在。**并列保留**，不合并 |
| **C-17** | `gsc.md` 与 `CODOL_SERVER_PROGRESS` 关于 Lua thread/wait | 前者记"后续已补第一阶段 `codol.thread`/`codol.wait`" vs 后者（10-09）记"无 thread/wait/endon/通用 notify" | 未裁定（时间序可能解释） |
| **C-18** | 2026-10-10 三次启动的方式 | `CODOL_RUNTIME_BLOCKER_CLEARANCE_20261009.md` §6 建议用 `CodolGame.py launch-dedicated`（role=dedicated）vs `COMBAT_SERVER_RECOVERY_BASELINE.md` §1.6 记实际用 `Launch_OLMod.bat`（**无参数、role=combined**），实测日志前缀为 `combined` | 已由日志前缀裁定为 **combined** |

---

## 8. UNKNOWN 总表（历史资料未证明，禁止补全）

| # | 未知项 | 影响 |
|---|---|---|
| U1 | 加壳映像**运行时**在 `0x0FEA20` / `0x8371A` 等 RVA 处的字节是否等于目录期望 | 决定 R-A/R-B，是 P0 的核心未知 |
| U2 | `out.exe`（`044c396c…`）本体是否存在 | 决定 R-A 可行性 |
| U3 | 全加密客户端 EXE 的导出表 | — |
| U4 | 生产是否设置 `OLMOD_PROCESS_ROLE=dedicated` / `OLMOD_HOST_ADDRESS` | 影响对局形态 |
| U5 | 后端下发 `ConfigureSession` 的真实 Demonware 描述符字节（含 16 B 会话密钥） | 阻断 28960 监听 |
| U6 | 沙箱 `Alwaysoffline` 的 44 项 overlay 是否与当前源码一致 | 影响后端行为 |
| U7 | Frida 为何无法注入该客户端 | 影响"读运行时映像"手段可行性 |
| U8 | 原版引擎独立的"战斗/会话创建"函数、原版 `NET_Frame`、原版 gametype 初始化入口 | 战斗创建入口判定的根本缺口 |
| U9 | `6/14 mmbook/mmstart` booking 应答帧格式；DedicatedControl 客户端桥端口与帧格式 | 阻断协议逆向线 Lobby→Battle |
| U10 | 客户端"对局流量地址"的真实来源（`101.67.36.18:10035` 由谁下发） | 阻断"客户端改用我们的 28960" |
| U11 | ol-mod 线与协议逆向线的接口关系 | 影响能否复用 |
| U12 | `E3823FD6…F37B` 归属 | 影响可接受制品集合 |
| U13 | `ICH059` PRCL `.tls` scheduler | `NOT_LOCATED` |
| U14 | `Appmain.cpp` 十处多行导出的精确符号名 | — |
| U15 | `runtime_module_load_order.csv` / `ICH044_*` 等清单内容 | 本轮未核验 |

---

### 6.10 补充：T-2.5 Stage D 的真实进程/端口/Frida 台账（本轮子代理独立复核）

| 项 | 实测 | 证据 |
|---|---|---|
| 进程 | 15:47:48 pid **24016**（存活约 20 s）；15:48:28 pid **24580**（`mods 5`）；15:50:14 pid **23828**（`processCount=1`、`fileSha256 36997674…`、`fileVersion 1649370`） | `_t2_5_stageD_evidence/stage_d_step3.log`、`stage_d_step4.log`、`stage_d_run.log` |
| 端口（Stage 1 基线，15:22） | 28960/28961/28962/28970 的 **OS 端点为 0**；瞬态 bind `0.0.0.0` 与 `127.0.0.1` 各 4/4 成功（`SO_REUSEADDR` 未设，探完即关） | `_t2_5_evidence/port_snapshot.json`（`os_endpoints: []`） |
| 端口（Stage D 运行期间） | 各步 `PRE/POST ports: []` ⇒ **四次客户端启动期间四个游戏端口从未进入监听** | `stage_d_step1/2.log`、`stage_d_run.log` |
| Frida（无害 x64 对照） | `python.exe` pid 17832，Frida 16.5.9，用例 A–F **6/6 PASS**，含负对照被拒 | `_t2_4c_evidence/frida_raw.jsonl`；`T2_4C_RUNTIME_PROBE_REPORT.md` |
| Frida（无害 x86 对照） | `cmd.exe` pid 14028，`verdict: X86_AGENT_OK` | `_t2_5_stageD_evidence/x86_agent_control.json` |
| **Frida（真实客户端）** | 15:49:50 pid 24580 → `ProcessNotFoundError`；**15:50:16 pid 23828 → `frida.ProcessNotRespondingError: either refused to load frida-agent, or terminated during injection`** ⇒ **真实客户端附加 2 次、成功 0 次** | `stage_d_attach.log`、`stage_d_run.log` |
| 离线重放负对照 | 自有未加壳插件 DLL：`PASS=0 FAIL=53 AMBIGUOUS=26 INSUFFICIENT=2 → verdict: FAIL`；候选 A/B 均 `INSUFFICIENT_EVIDENCE` | `_p14_evidence/replay_plugin_negative_control.log`；`OFFLINE_BINDING_REPLAY_REPORT.md` |
| 历史调试会话 | 2026-09-19 CDB：`Access violation - code c0000005 (first chance)` @ `KERNEL32!IsBadReadPtr+0x5a` —— **与 2026-10-10 三次运行无证据关联** | `_core009_run1.txt`、`_core009_runB.txt` |

> pid 23828 与 `Localnetworking.log` 中真实外发流量（`sendto-target pid=23828`）**完全一致** ⇒ 同一真实客户端进程。这构成本项目**最强的一条"客户端确实启动到网络阶段"证据**，但它**不是**战斗服务器初始化成功的证据。

### 6.11 三类证据的最终划分（本轮）

| 类别 | 内容 | 数量 |
|---|---|---|
| **A. 真实客户端运行** | 2026-10-10 15:44–15:50 的 4 次启动（pid 24016 / 24580 / 23828）；其中战斗服务器**初始化成功 0 次**、Frida 附加**成功 0 次** | 唯一一批 |
| **B. 真实探针但非 CODOL** | `python.exe`(17832) 6/6 PASS；`cmd.exe`(14028) `X86_AGENT_OK` | 证明工具可用，**不能**外推到客户端 |
| **C. 离线/静态** | `_t2_1`、`_t2_2`、`_t2_3`、`_t2_5_evidence`（Stage 1）、`_t2_acceptance`、`_t1_fix`、`_batch10`、`_p14`、`_combat_baseline`、`_e1_regression*`、`analysis_logs`、`CODOL_EX*/ICH*` | **不得**当作真实运行 |

**证据缺口（如实标注）**
- **Stage D 的正式报告不存在**：只有原始 `.log`/`.json`（部分 UTF-16LE），三次运行的完整上下文由原始日志 + `COMBAT_SERVER_RECOVERY_BASELINE.md` 拼合。
- 工作区内**无**真实游戏进程运行证据；唯一真实运行日志在 E 盘沙箱。
- 沙箱 `Ayria\Logs\` 中三次运行**共用同一组日志文件**，靠时间戳区分 ⇒ 逐次运行的隔离证据不足。
- 未找到任何真实客户端上成功的 Frida 附加会话。
- 186 KB 的 `CdolGameServer.log` 副本经复核确认：**distinct timestamp = 1**（全为 `2026-10-09 13:52:25`），0 命中 `engine binding failed` / `Localnet32` / `frame hook` / `listening`。

---

## 9. 本轮纪律声明

- 未修改、未创建、未删除任何生产代码/配置；仅新增 5 份交付物（本文件及同批）。
- 未启动、未附加、未注入、未终止任何进程；未构建、未部署、未提交、未推送。
- 未对历史结论做未经证据支持的纠正或覆盖；未为补充未知项开展新的运行时实验。
- 原始证据（`E:\CODOL_SANDBOX\RUN001\Ayria\Logs\*`、`_combat_baseline/*`、`_batch10_evidence/*`、`_map_extract/*`、`REF_LOBBY_KIT/battle_srv.log` 等）**保持原样**，未移动/覆盖/删除。
