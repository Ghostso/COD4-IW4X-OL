# CODOL 战斗服务器 · 运行时阻塞清理报告

**日期**：2026-10-09
**仓库**：F:\桌面\ol\ol-mod-olfinal
**分支 / HEAD**：OLfinal-live / `2a75bdd8872bb9f54006382a924c3006ec9affc2`
**考察目标**：`ol_game_server` → `build\bin\release\CodolGameServer.Localnet32`
**产物哈希**：6,556,672 B / SHA-256 `6D493B820E84A21B096C9914616B75DCEC488920D7AC76867049B20C5C6B2021`
**本轮范围**：制品身份更正 · 地图制品恢复 · overlay 核验 · 离线验证推进 · 运行时阻塞门禁
**执行限制**：未执行 Injector32、未启动游戏、未注入、未调试、未抓包、未读进程内存、未修改正式配置、未批准任何基线切换

---

## 0. 执行摘要

| 门禁 | 上轮结论 | 本轮结论 | 变化 |
| --- | --- | --- | --- |
| BUILD_PASS | 通过 | 通过 | — |
| LINK_PASS | 通过 | 通过 | — |
| UNIT_TEST_PASS | 通过（3 套 EXE exit 0） | 通过 | — |
| 制品身份（与批准目标） | FAIL（误判） | **NOT_VERIFIED** | 更正误判 |
| 地图 fastfile | 未找到 | **已找到（mp_crash_tropical）** | ✅ 解除 |
| 隔离 overlay | 副本缺失 44/44 | **副本齐备 44/44** | ✅ 解除 |
| PLUGIN_LOAD_PASS | NOT_TESTED | **NOT_TESTED** | 仍被授权闸门阻塞 |
| SERVER_INIT_PASS | NOT_TESTED | **NOT_TESTED** | 同上 |
| CLIENT_CONNECT / GAMESTATE / SNAPSHOT / BATTLE_SMOKE | NOT_TESTED | **NOT_TESTED** | 同上 |

**一句话**：本轮未启动任何游戏进程，但把运行时验收的**全部静态前置条件清空** —— 地图、overlay、副本身份与资源契约均已就位；剩余唯一闸门是「Injector32 注入 + 客户端启动」的授权。

---

## 1. 制品身份：**未确认**（三项声明必须分离）

依据 `.agents/audits/2026-10-09/artifact_provenance.json` 第 81-85 行的 `sourceRelationRules`：**文件身份（SHA-256）、构建身份（guard/RVA）、源码兼容性（OLMod 绑定）是三项独立声明，必须分别记录。**

| # | 声明 | 状态 | 依据 |
| --- | --- | --- | --- |
| 1 | **文件身份**（测量值） | CONFIRMED | `E:\CODOL_SANDBOX\RUN001\codoMP_client_shipRetail.exe` = 7,841,344 B / `36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537`（= 审计「候选 A」） |
| 2 | **与批准目标 `E3823FD6…F37B` 的关系** | **UNKNOWN（不可比）** | `artifact_provenance.json:9` 将该哈希的对象定义为 **OLFinal unpacked `out.exe`**；实测对象是**打包**的 `codoMP_client_shipRetail.exe`。两者不是同一类文件，哈希不同是结构性必然，**不能作为匹配/不匹配的判据** |
| 3 | **构建身份**（guard / RVA） | UNKNOWN | `artifact_provenance.json:38-41`：打包镜像，78/79 守卫失配且唯一匹配项是**数据常量**，文件字节无法定论 |
| 4 | **源码-ABI 兼容性**（OLMod 绑定） | NOT_VERIFIED | 需运行时内存镜像级核验。本机全盘 0 个 `out.exe`；加载客户端未授权 |

### 1.1 更正

- 上一轮预检第 5 项记为 `FAIL`，属**错误判定**：拿**解包** `out.exe` 的哈希去比对**打包**客户端，属跨类比较。
- 现更正为 **`NOT_VERIFIED`**。
- **不宣称**候选 A 兼容或已不兼容；**未修改**任何正式预期哈希。

### 1.2 附带发现的文档缺陷

`.agents/audits/2026-10-09/GOLDEN_COPY_SPEC.md` 第 29 行的 G1 要求：

    G1. 客户端 EXE SHA-256 == E3823FD6AFC80FB25FA84747E6E9634707B9A0B189357A5466921CDA354AF37B

但任何**打包发布**的 `codoMP_client_shipRetail.exe` 都无法满足该条；同一文件第 48 行又把 `out.exe` 单独列出。**G1 按字面不可满足**，需澄清「客户端 EXE」指**内存镜像**还是**分发文件**。此项纯记录，未修改该文件。

---

## 2. 地图制品：**已找到**（离线解包，未启动客户端）

### 2.1 方法

复用仓库既有的**只读**离线解包器 `CODOLServer\_mainline\_ifs_extract.py`：

- 容器格式已逆向并文档化（见该脚本第 1-18 行；`ICH033_NIFS_FORMAT.md`、`ICH033_NIFS_HEADER_ANALYSIS.csv`）。
- 该脚本**只读** `.ifs`，只把内嵌 `IWff` blob 写到输出目录，**从不修改源容器**。
- **已有成功先例**：`ICH033_FF_IFS_MAPPING.csv` 已 **CONFIRMED** 记录 `ff_init_common_gfx_V109.ifs` → `ui_mp.ff` / `mp_playlists.ff` / `code_*.ff` 等 10 个 `.ff`，**正是 `RUN001\main\` 中现存的那 10 个**，证明该机制在本机已成功运行过。

### 2.2 产出（已验证为 CODOL fastfile）

| 产物绝对路径 | 大小 | SHA-256 | 格式 |
| --- | --- | --- | --- |
| `E:\CODOL_SANDBOX\RUN001\main\mp_crash_tropical.ff` | **32,652,693** | `8443E29599C194C6B734460F5F623AAF4BC7899D50603E72E12DEFB46B601AC8` | `IWff0100` **v=461** ✅ |
| `E:\CODOL_SANDBOX\RUN001\main\mp_crash_tropical_load.ff` | 24,885 | `D69B6E0B7A5DFC204C40D5AA656541E901ABBC6E20F1BEDF4AB766DC7448BA44` | `IWff0100` v461 ✅ |
| `E:\CODOL_SANDBOX\RUN001\main\mp_crash_tropical_const.ff` | 140,465 | `6B26058D67CFAF0D762A187ED55994A29FD59E01FCAA00186660C5DA7452FFA4` | `IWff0100` v461 ✅ |

- **来源安装目录**：`E:\CODOL_SANDBOX\RUN001`，自其 IIPS 补丁包 `IIPS\IIPSDownload\ff_init_mp_crash_tropical_V73.ifs`（32,818,417 B / `F7E428E516A776210D0D570E487802024CFEC7312DC13DABAE6A418299C1090E`）。
- **源容器未被修改**：解包后重新计算哈希与大小完全不变。
- **格式独立复核**：文件头 16 字节与同目录参考件 `ui_mp.ff` / `mp_playlists.ff` **逐字节同型**（`49 57 66 66 30 31 30 30 CD 01 00 00`），确认为 CODOL fastfile（非 IW4/IW4X）。
- 该图恰为 `Match_CODOL_Two_Clients.bat` 第 35 行的默认测试图 `CODOL_MATCH_MAP=mp_crash_tropical`。

### 2.3 负面结果（诚实记录）：`mp_nuked` 不可用

同一解包器对 `ff_init_mp_nuked_V74.ifs` **名称/blob 对齐失败**：

- blobs 数 4，名字数 3，多出未命名 `blob3.ff`（82,515 B）；
- 产出的 `mp_nuked_load.ff`（22,422,224 B）版本字段为 `0x552F73A2`（**非 461**，非法 fastfile 头）；
- 产出的 `mp_nuked.ff` 仅 546,261 B，对地图 zone 不合理。

**结论：`mp_nuked` 整套产物未验证，不得使用。** 需要修正 blob/名称对齐后方可再试。

### 2.4 `.ff` 普查（仅已记录来源，无重复扫描）

3 个 CODOL 专属根共 **105** 个 `.ff` / 69 个不同名。

| 来源 | 数量 | 判定 |
| --- | --- | --- |
| `D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\_lineage021\iw4x-rawfiles\zone\patch\` | 53 | **排除**：magic `IWffu100` v=276 = **IW4/IW4X**，非 CODOL。含 3 个形似地图的 `*_load.ff`（620-624 B），已用文件头证伪 |
| `ws-sandbox-datafix` (16) + `CODOL_SANDBOX\RUN001` (10) + `COD OL\main` (9) + `CODOLServer\logs\IFS_EXTRACT_TEST` (3) + `backup_reverse_engineering` (若干) | 52 | CODOL 格式 `IWff0100` v461；**地图类原有 0 个**，本轮经离线解包新增 3 个 ✅ |

> 一致性校验：105 − 53 = **52**，与阶段 G 记录的「52 个 `.ff` / 地图 0」完全吻合。

### 2.5 排除清单（按要求）

`playlist` / `ui` / `localized` / `common` / `code` / `development` / `marketplace` / `loadscreen` 类以及全部 IW4X 资产均已排除；`mp_playlists.ff` 不作为地图接受。

---

## 3. overlay 核验与隔离副本部署

### 3.1 overlay 与契约一致性

| 检查 | 结果 |
| --- | --- |
| `build\stage\codol\ol-mod-runtime-manifest.json` | schemaVersion 1 / titleId 1004 / x86 / **44 条目** |
| 与 `distribution/runtime-components.json` 的 15 项 destination 逐项对照 | **全部一致**（2 legacy + 5 rebuilt + 2 config + 5 资源目录 + 1 launcher） |
| 无来源组件 | **无** —— 44 条目每一项都有 `source`、`installPolicy` 与恢复条件 |
| 插件哈希 | `CodolGameServer.Localnet32` 仍为 `6D493B82…2021`（未被后续构建重链） |

### 3.2 目标副本缺失清单

| 时点 | `E:\CODOL_SANDBOX\RUN001` | 明细 |
| --- | --- | --- |
| 部署前 | **缺失 44 / 44**（`present=0`） | 根目录无 `Ayria\`：缺 `Injector32.exe`、`Bootstrapper32.dll`、4 个插件、`ol_room_owner.exe`、`Launch_OLMod.bat` 及全部 `Assets` |
| 部署后 | **齐备 44 / 44**（`missing=0`） | 见 3.3 |

### 3.3 本轮已执行的隔离准备

    robocopy  F:\桌面\ol\ol-mod-olfinal\build\stage\codol   E:\CODOL_SANDBOX\RUN001   /E
    copy      _map_extract\mp_crash_tropical{,_load,_const}.ff  ->  E:\CODOL_SANDBOX\RUN001\main\

7 项启动前置件现全部存在：`Ayria\Injector32.exe`、`Ayria\Bootstrapper32.dll`、`Ayria\Plugins\Localnetworking.Ayria32`、`Ayria\Plugins\Platformwrapper.Ayria32`、`Ayria\Plugins\Alwaysoffline.Localnet32`、`Ayria\Plugins\CodolGameServer.Localnet32`、`Ayria\ol_room_owner.exe`。

### 3.4 未触碰项（机械核对）

| 项 | 核对值 | 结论 |
| --- | --- | --- |
| `config\codol-game-dir.txt` | SHA-256 `9AEEFD107F677EDD4F2A85DA7E38FF796718C7BF64F60E1B7D1CD6F1092019AA` | **未修改**（内容仍为 `D:\codo_3.19.26.13_fresh\CoD Online`，该目录不存在） |
| `git status --porcelain` | 0 | **工作树干净** |
| `git rev-parse HEAD` | `2a75bdd8872bb9f54006382a924c3006ec9affc2` | 未变 |
| `E:\OLMOD_BACKUP_*` 冻结备份 | — | 未读写 |
| `ol_deploy` 目标 | — | 未触发 |

---

## 4. 离线验证边界

### 4.1 已通过

| 项 | 证据 |
| --- | --- |
| 三套独立测试 EXE | `ol_game_server_tests` / `ol_dedicated_control_tests` / `ol_playerdata_def_tests` 均 exit 0 |
| **Lua 资源契约** | `src\game_server\server_mp\sv_script_source_mp.cpp` 第 143-147 行：读取顺序固定为 `common.lua` → `gametypes/<gameType>.lua` → `maps/<mapName>.lua`，缺文件时 `continue` 容错。stage 中三者对 `sd` + `mp_crash_tropical` 齐备 ✅ |
| **传输层语义** | `tests\game_server\ServerCoreTests.cpp` 第 27411-27494 行：`configureSessionDescriptor` → `setEnabled` → `NET_DtlsPacket` INIT→INIT_ACK→CHALLENGE→CONNECT，断言 `status().connectedClients == 1`，含固定 CODOL P-224 ECDH 向量 ✅ |
| overlay 一致性 / 地图格式 | 见第 2、3 节 |

### 4.2 未覆盖（关键路径）

xmake 的 3 个测试目标只链接 `game_server_core`（`xmake.lua` 第 92-107、264、316 行）。以下 **9 个插件专属源文件（合计 30,838 行）不进入任何测试目标**：

| 文件 | 行数 | 承载内容 |
| --- | --- | --- |
| `src\game_server\Appmain.cpp` | **9,312** | **全部 53 个导出**、`initialize()`、角色分流、`Network.start()`、`CODOL_GameServerGetTransportStatus` |
| `src\game_server\EngineBindings.cpp` | **17,419** | 170 个 RVA + 104 个 prefix 守卫 |
| `src\game_server\NativePmoveBindings.cpp` | 1,963 | 原生 pmove 绑定 |
| `src\game_server\NativeWeaponMovementBindings.cpp` | 629 | 武器移动绑定 |
| `src\game_server\ClientCommandTrace.cpp` | 602 | 客户端诊断 |
| `src\game_server\NativeWeaponBindings.cpp` | 411 | 武器绑定 |
| `src\game_server\ClientNoclipHotkey.cpp` | 247 | 热键 |
| `src\game_server\NativeEntityStateBindings.cpp` | 191 | 实体状态绑定 |
| `src\game_server\FrameHook.cpp` | 64 | 帧钩子安装 |

具体缺口：

- `CODOL_GameServerGetTransportStatus` / `SetEnabled` / `ConfigureSession` 全族 **零直接测试**；
- **真实 UDP socket 绑定无测试**（现有测试走内存 `NET_DtlsPacket`）；
- `EngineBindings` 的 RVA 校验无测试；
- `OlMod::processRole()` 三态无测试。

对照：进入测试的核心源为 **77,962 行**（`qcommon` + `server_mp` + `win32`），覆盖扎实 —— **缺口在插件边界，不在服务端逻辑**。

### 4.3 新增可独立运行的测试方案（**仅方案，未实施，需批准**）

| 编号 | 内容 | 影响面 | 回滚 |
| --- | --- | --- | --- |
| T1 | 导出面/生命周期冒烟：新增 target `ol_game_server_surface_tests`，把上述 9 个文件编入测试目标，断言 `Createserver(nullptr) == nullptr`、53 个导出名存在、`processRole()` 对 `OLMOD_PROCESS_ROLE` 三态、各 `Get*Status(nullptr)` 守卫返回 false | 仅 `xmake.lua` 新增 target，不改现有源 | 删除该 target |
| T2 | 真实传输绑定：离线单测对 `Network.start()/stop()` 做 127.0.0.1:0 绑定，断言 `bound=1`、`port≠0`、重复 `start()` 幂等、`stop()` 后 `bound=0` | 需把 `Network` 的状态查询与 socket 绑定解耦为可测函数（小幅重构 `Appmain.cpp`） | `git checkout` 该文件 |
| T3 | 地图资源契约：以 `build\stage\codol\Ayria\Assets\OlMod\GameScripts` 作为 `scriptRoot` 做真值测试（覆盖 `mp_crash_tropical.lua` / `sd.lua` 存在与缺失容错） | 仅新增测试文件 | 删除测试文件 |

---

## 5. 运行时阻塞与解除条件

| # | 阻塞 | 状态 | 解除条件 |
| --- | --- | --- | --- |
| B1 | **进程注入**：唯一入口 `Ayria\Injector32.exe`（`tools\runtime\CodolGame.py` 第 371 行），且第 291 行注明不可加参数 | **BLOCKED** | 显式授权执行 Injector32。**无免注入等价路径**：插件为进程内 DLL，生命周期入口 `onStartup`/`onInitialized` 由归档 `Bootstrapper32.dll` 在注入后调用 |
| B2 | 启动客户端 | **BLOCKED** | 同 B1 授权 |
| B3 | overlay 缺失 | **已解除** ✅ | 已部署 44/44 |
| B4 | 地图 `.ff` 缺失 | **已解除** ✅ | 已离线解包并置入 `main\`（`mp_crash_tropical`） |
| B5 | 客户端构建身份 | **UNKNOWN** | 授权后读内存镜像哈希比对 `E3823FD6…`；或由用户提供 `out.exe` |
| B6 | 源码/ABI 兼容性 | **NOT_VERIFIED** | 授权后观察 `Ayria\Logs\CodolGameServer.log` 是否出现 `client frame hook installed` |
| B7 | `config\codol-game-dir.txt` 指向不存在的目录 | **已绕过**（未修改） | 用 `--game-dir E:\CODOL_SANDBOX\RUN001` 显式传参；不改配置文件 |
| B8 | `mp_nuked` 解包错位 | **NOT_VERIFIED** | 修正解包器 blob/名称对齐；或改用 `mp_crash_tropical`（已是默认图） |

---

## 6. 下一步（唯一最高优先级动作）

**申请授权执行「单进程最小挂载验证」** —— 这是唯一剩余的硬闸门；其余静态前置条件本轮已全部清空。

- **输入**：`E:\CODOL_SANDBOX\RUN001`（overlay 44/44 + `mp_crash_tropical.ff` 已就位）
- **操作**（单进程，非双客户端）：

      python tools\runtime\CodolGame.py launch-dedicated --wait 15 --game-dir E:\CODOL_SANDBOX\RUN001

  将启动 `Ayria\Injector32.exe` → `codoMP_client_shipRetail.exe`（`OLMOD_PROCESS_ROLE=dedicated`，参数仅 `-qa`）以及 `ol_room_owner.exe`。
  **不抓包、不调试、不读内存、不改配置**；只读 `RUN001\Ayria\Logs\*.log`。

- **验收条件**（三条全中 = `PLUGIN_LOAD_PASS` + `SERVER_INIT_PASS`）：
  1. `Ayria\Logs\CodolGameServer.log` 出现 `client frame hook installed`（若为 `failed` → B6 判负，需换 `E3823FD6…` 客户端）；
  2. 日志证明 backend 调用了 `CODOL_GameServerConfigureSession`；
  3. `CODOL_GameServerGetTransportStatus` 报 `bound=1` 且 `port≠0`。

- **回滚**：`python tools\runtime\CodolGame.py stop`；`Remove-Item E:\CODOL_SANDBOX\RUN001\Ayria -Recurse`。

该步一次性把 B5 / B6 从 UNKNOWN 定论，并决定是否进入三进程双客户端 `BATTLE_SMOKE_PASS` 验收。

---

## 7. 证据索引

| 类别 | 路径 |
| --- | --- |
| 制品记录 | `.agents/audits/2026-10-09/artifact_provenance.json`（:9、:22-70、:81-85） |
| 黄金副本规范 | `.agents/audits/2026-10-09/GOLDEN_COPY_SPEC.md`（:29、:48） |
| fastfile 清单 | `.agents/audits/2026-10-09/fastfile_inventory.json` |
| 组件契约 | `distribution/runtime-components.json` |
| 分发说明 | `distribution/README.md`（:16-24、:50-57） |
| 挂载链源码 | `src\localnetworking\Localnetworking.cpp`(:350-379,:400-415) · `src\localnetworking\RuntimePaths.cpp`(:8-33) · `src\backend\Demonware\MatchmakingService.cpp`(:166-297) · `src\game_server\Appmain.cpp`(:7012,:7153-7162,:8142-8158) · `src\shared\ProcessRole.hpp`(:17-50) |
| 测试 | `tests\game_server\ServerCoreTests.cpp`(:27411-27494) |
| IFS 解包工具 | `CODOLServer\_mainline\_ifs_extract.py` |
| IFS 格式分析 | `ICH033_NIFS_FORMAT.md` · `ICH033_NIFS_HEADER_ANALYSIS.csv` · `ICH033_FF_IFS_MAPPING.csv` |
| 本轮提取产物 | `_map_extract\mp_crash_tropical.ff`（32,652,693 B） |
| 本轮构建日志 | `_build_olgs.log` · `_build_plugins.log` · `_stage_final.log` · `_run_tests.log` |

---

## 8. 本轮变更与纪律

**已产生的副作用（全部可回滚）**

| 位置 | 内容 | 回滚方式 |
| --- | --- | --- |
| `E:\CODOL_SANDBOX\RUN001\Ayria\` | overlay 44 文件 | `Remove-Item ...\Ayria -Recurse` |
| `E:\CODOL_SANDBOX\RUN001\main\mp_crash_tropical*.ff` | 3 个离线解包产物 | 删除该 3 个文件 |
| `F:\桌面\ol\ol-mod-olfinal\build\stage\codol` | stage 目录（gitignore） | 删除 `build\stage` |
| `D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\` | 提取输出 | 删除目录 |

**未发生（机械核对）**

- 未执行 Injector32、未启动游戏、未注入、未调试、未抓包、未读进程内存；
- 未修改 `config\codol-game-dir.txt`（哈希逐字不变）、未触发 `ol_deploy`、未部署到任何正式安装目录；
- 未改动源码、哈希、RVA、ABI、协议常量、fixture 或 S2/S3 默认值；
- 未 push / amend / reset / rebase；未覆盖任何冻结备份；
- `git status --porcelain` = 0，`src/` 修改 = 0。

**未执行项一律保留 `NOT_TESTED` / `BLOCKED` / `UNKNOWN`，未以 `PASS` 代替。**
