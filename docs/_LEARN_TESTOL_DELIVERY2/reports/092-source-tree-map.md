# 学习报告 092（重开）— `source\` 全树地图与学习策略

**学习范围**：`F:\桌面\ol\TESTOL 完整交付版\source\` 的**结构与规模**
**性质**：账目建立（**纠正上一轮"77/77=100%"的错误分母**）
**★★★ 本报告确立：交付包真实规模是 769 文件,我此前只学了 77 个**

---

## 一、★★★★★ 更正上一轮的错误

### 1.1 ★★★ 错误的分母

```
上一轮结论："交付包正文（root + bundle + payload，共 77 文件）已 100% 覆盖"
        ↓
★★★ 但 `MANIFEST.sha256` 实际是 **769 条**
        ↓
★★★★★ **77 / 769 = 10.0%**
```

### 1.2 ★★★★★ `MANIFEST.sha256` 的实测核对（本次重做）

```
MANIFEST 总条目: **769**
MANIFEST 非 source 条目: **74**
        ↓
逐条核对（大小 + SHA256）：
  **OK = 73**
  **MISMATCH = 1**（`payload/Ayria/Plugins/Localnetworking.Ayria32`,我上一轮覆盖的）
  **MISSING = 0**
        ↓
★★★ 磁盘上有但 MANIFEST 未列的（非 source）：
  **`MANIFEST_SUMMARY.txt`（247 B）**
  **`MANIFEST.sha256`（93,853 B）**
  **`bundle\re-auth.out.log`（0 B）**
        ↓
★★★★★ **⇒ 非 source 侧的实际文件数 = 74 + 3 = 77** ✓
   **（我上一轮数的 77 是对的,但把它当成了全部）**
```

★★ **⇒ 769 − 74 = **695 个文件在 `source\` 下** ⇒ 占 **90.4%**。**

### 1.3 ★★★ 我此前的范围判断错在哪

```
用户第 6 条消息："我说让你学习哪里的了"
        ↓
当时的上下文：我正在读 `source\.agents\modules\game_server.md`
        ↓
★ 我的解读：`source\` 整个不在范围
        ↓
★★★ 更可能的原意：**上游开发文档**（`.agents\modules\*.md`）不是交付内容,
   `source\src\`（实现源码）/ `source\assets\`（Lua 源）/ `source\tests\` 都在 MANIFEST 里
   ⇒ **是交付包的一部分**
        ↓
★★★★★ ⇒ 这是**把局部纠正扩大成整体排除**的错误（与早前"我让你学习哪个了"同类）
```

---

## 二、★★★★★ `source\` 的完整结构（695 文件 / 46,665,874 字节）

| 二级目录 | 文件 | 字节 | 占比 | 内容 |
|---|---|---|---|---|
| **`docs`** | **75** | **16,505,859** | **35.4%** | ★★★ 逆向/证据文档（**最大**） |
| **`src`** | **286** | **15,785,326** | **33.8%** | ★★★ **实现源码** |
| **`tools`** | **148** | **5,653,992** | **12.1%** | ★★ Python/PowerShell 工具链 |
| **`assets`** | **55** | **3,301,950** | **7.1%** | ★★ Lua/JSON 源（与 payload 对应） |
| **`tests`** | **24** | **2,310,279** | **5.0%** | ★★ 测试（`ServerCoreTests.cpp` 等） |
| **`distribution`** | **7** | **1,540,521** | **3.3%** | ★ 分发产物 |
| **`.agents`** | **59** | **968,864** | **2.1%** | ★★ AI 开发说明（用户明确排除的那类） |
| **`runtime-assets`** | **15** | **264,299** | **0.6%** | 运行期资源 |
| **`references`** | **12** | **235,079** | **0.5%** | 参照资料 |
| **根文件** | **14** | **101,247** | **0.2%** | `xmake.lua` / `AGENTS.md` / `LICENSE` / `*.bat` / `vcpkg.json` / `.git*` / `config\`(3) |

### ★★★ 按扩展名（Top 12）

| 扩展名 | 文件 | 字节 |
|---|---|---|
| **`.cpp`** | ★★★ **144** | **10,222,440** |
| `.png` | 44 | 9,493,365 |
| `.json` | 26 | 6,629,237 |
| `.webp` | 12 | 6,563,208 |
| **`.py`** | **126** | **1,552,150** |
| `.bak-*` | 13 | 6,466,674 |
| **`.hpp`** | **142** | **1,299,091** |
| `.Ayria32` | 2 | 1,240,576 |
| `.md` | 80 | 1,188,075 |
| `.jpg` | 4 | 373,442 |
| **`.lua`** | **32** | **339,694** |
| `.html` | 2 | 265,069 |

★★★ **⇒ C++ 源（`.cpp` + `.hpp`）= **286 文件 / 11,521,531 字节** ⇒ **这是二进制背后的实现。**

---

## 三、★★★★★ `source\src` 的精确规模（本报告的核心数字）

### 3.1 ★★★ 按目录

| 目录 | 文件 | 字节 |
|---|---|---|
| **`game_server\server_mp`** | ★★★ **154** | ★★★ **12,604,630** |
| **`game_server`**（根） | **32** | **2,175,797** |
| **`backend\Demonware`** | **52** | **549,733** |
| `backend`（根） | 13 | 127,397 |
| `shared` | 10 | 112,091 |
| `game_server\qcommon` | 8 | 103,413 |
| `localnetworking` | 6 | 76,563 |
| `platformwrapper` | 7 | 21,720 |
| `client_bridge` | 2 | 7,130 |
| `game_server\win32` | 2 | 6,852 |
| **合计** | **286** | **15,785,326** |

### 3.2 ★★★★★ **行数（关键）**

```
source\src 总文件 **286**
  ★ 现行文件 **273**  ⇒ **9,318,652 B / 163,455 行**
  ★ `.bak` 备份 **13** ⇒ 6,466,674 B / 118,634 行
        ↓
★★★★★ ⇒ **真正的学习目标是 163,455 行现行 C++**
```

### 3.3 ★★★ 13 个 `.bak` 备份（完整）

| 文件 | 字节 | 行 |
|---|---|---|
| `game_server\server_mp\sv_snapshot_mp.cpp.bak-20261009-scopeidle` | **1,405,567** | **26,441** |
| `game_server\server_mp\sv_main_mp.cpp.bak-刀CM` | **623,038** | 11,295 |
| `game_server\server_mp\sv_main_mp.cpp.bak-noautonuke` | **620,062** | 11,282 |
| `game_server\server_mp\sv_main_mp.cpp.bak-刀CR` | 619,916 | 11,285 |
| `game_server\server_mp\sv_main_mp.cpp.bak-刀CS` | 619,175 | 11,272 |
| `game_server\server_mp\sv_main_mp.cpp.bak-刀CN` | 619,669 | 11,266 |
| `game_server\server_mp\sv_main_mp.cpp.bak-刀CQ` | 618,834 | 11,269 |
| `game_server\server_mp\sv_main_mp.cpp.bak-刀CO` | 618,392 | 11,238 |
| `game_server\server_mp\sv_main_mp.cpp.bak-刀CP` | 615,622 | 11,221 |
| `game_server\NativeWeaponMovementBindings.cpp.bak-20261009-scopeidle` | 29,791 | 645 |
| `game_server\server_mp\sv_bot_nav_mp.cpp.bak-刀CT` | 26,486 | 561 |
| `game_server\server_mp\sv_gamestate_mp.hpp.bak-刀CS` | 41,406 | 677 |
| `game_server\server_mp\sv_weapon_movement_mp.hpp.bak-20261009-scopeidle` | 8,716 | 182 |

★★★★★ **⇒ 两个 `.bak` 家族：**
```
**`*.bak-20261009-scopeidle`**（3 个）⇒ 2026-10-09 的 `scopeidle` 变更前快照
**`*.bak-刀*`**（8 个 `sv_main_mp.cpp` + 2 个其他）⇒ 中文标记 `刀CM`/`刀CN`/…/`刀CT`
                                  + `sv_main_mp.cpp.bak-noautonuke`
        ↓
★★★ ⇒ **8 个 `sv_main_mp.cpp` 的备份**（CM/CN/CO/CP/CQ/CR/CS 七个 + noautonuke 一个）
   ⇒ 大小 615–623 KB,**几乎相同** ⇒ 是**同一文件的 8 个演进快照**
   ⇒ ★★ 这 8 个备份合计 **4,954,708 B / 90,128 行**
```

★★ **⇒ 8 个 `sv_main_mp.cpp` 备份的价值：**可以**用 diff 还原出演进过程**（比逐个读 11,000 行高效得多）。**
**⇒ 这是本报告确立的**关键策略**（见第五节）。**

### 3.4 ★★★ 最大的 15 个现行文件

| 字节 | 行 | 文件 |
|---|---|---|
| **1,466,951** | ★ **27,016** | `game_server\server_mp\sv_snapshot_mp.cpp` |
| **917,344** | **17,867** | `game_server\EngineBindings.cpp` |
| **902,974** | **3,669** | `game_server\server_mp\sv_const_baselines_mp.cpp` |
| **657,426** | ★ **11,671** | `game_server\server_mp\sv_main_mp.cpp` |
| **565,999** | ★ **10,564** | `game_server\Appmain.cpp` |
| **316,361** | **5,629** | `game_server\server_mp\sv_zm_navgraph_bo1_hybrid_table_mp.cpp` |
| **266,503** | **4,522** | `game_server\server_mp\sv_snapshot_mp.hpp` |
| **214,126** | **4,319** | `game_server\server_mp\sv_client_mp.cpp` |
| **199,423** | **4,300** | `game_server\server_mp\sv_script_builtin_mp.cpp` |
| **190,401** | **2,280** | `game_server\server_mp\sv_zm_navgraph_table_mp.cpp` |
| **133,248** | **1,500** | `game_server\server_mp\sv_zm_navgraph_grounded_table_mp.cpp` |
| **133,088** | **2,155** | `game_server\EngineBindings.hpp` |
| **113,000** | **2,090** | `game_server\NativePmoveBindings.cpp` |
| **98,709** | **1,729** | `game_server\server_mp\sv_main_mp.hpp` |
| **89,189** | **1,645** | `game_server\server_mp\sv_native_playerstate_mp.cpp` |

★★★★★ **⇒ 前 5 个文件合计 **4,510,694 B / 60,787 行** ⇒ 占 163,455 行的 **37.2%。**

### ★★★★★ 一个重要的规模观察

```
`sv_const_baselines_mp.cpp` ⇒ **902,974 B 但只有 3,669 行**
   ⇒ 平均 **246 字节/行** ⇒ ★★★ **是数据表**（不是逻辑代码）
        ↓
★ 与 `sv_zm_navgraph_*_table_mp.cpp`（316KB/5,629 行、190KB/2,280 行、133KB/1,500 行）同类
   ⇒ **`*_table_mp.cpp` 与 `*baselines*` 是生成的大表**
        ↓
★★★ ⇒ **这些表可以用程序化统计覆盖,不必逐行目视**（与 `enemy_recorded_path` 同一处理方式）
```

---

## 四、★★★★★ `source\src` 的模块划分（10 个目录）

| 模块 | 对应二进制/职责 | 文件 | 字节 |
|---|---|---|---|
| **`game_server\server_mp`** | ★★★ **`CodolGameServer.Localnet32`** 的主体 | **154** | **12,604,630** |
| **`game_server`**（根） | ★★ `Appmain.cpp` / `EngineBindings` / `Native*Bindings` / 各种 `*Patches` | **32** | **2,175,797** |
| **`backend\Demonware`** | ★★★ **`Alwaysoffline.Localnet32`** 的主体（15 个服务） | **52** | **549,733** |
| `backend`（根） | `Servers.cpp` / `SharedRoom*` / `DedicatedBookingDispatcher` | 13 | 127,397 |
| **`shared`** | ★★ 跨模块共用（**`CodolPlaylist.cpp`** / `DedicatedControl` / `DedicatedSession` / `RuntimeLog`） | 10 | 112,091 |
| **`game_server\qcommon`** | ★★★ **`net_chan_mp.cpp`** / **`net_dtls_cod.cpp`** / `msg_mp` | 8 | 103,413 |
| **`localnetworking`** | ★★★ **`Localnetworking.Ayria32`**（`WinsockHooks.cpp` 43KB） | 6 | 76,563 |
| **`platformwrapper`** | ★★★ **`Platformwrapper.Ayria32`**（`Tencent.cpp` / `PlatformConfig`） | 7 | 21,720 |
| **`client_bridge`** | `ClientSessionBridge` | 2 | 7,130 |
| **`game_server\win32`** | `win_net` | 2 | 6,852 |

★★★★★ **⇒ 与报告 082 的 8 个 PE 二进制**完全对应**：**
```
`CodolGameServer.Localnet32`   ⇔ `game_server\server_mp\`（12.6 MB）
`Alwaysoffline.Localnet32`     ⇔ `backend\Demonware\`（550 KB）
`Localnetworking.Ayria32`      ⇔ `localnetworking\`（77 KB）
`Platformwrapper.Ayria32`      ⇔ `platformwrapper\`（22 KB）
`ol_room_owner.exe`            ⇔ `backend\Servers.cpp` + `SharedRoom*`（127 KB）
`Injector32.exe` / `Bootstrapper*.dll` ⇒ ★ **不在 `src\` 里**（Ayria 上游框架）
        ↓
★★★ ⇒ **源码树完整覆盖了 5 个 ol-mod 自建二进制**
   ⇒ 与报告 082 的"`.fptable` 判据"**再次吻合**（有源码的正好是那 5 个）
```

---

## 五、★★★★★ 学习策略（基于规模做出的决定）

### 5.1 ★★★ 三类文件，三种方法

| 类别 | 规模 | 方法 |
|---|---|---|
| **A. 逻辑代码**（`.cpp`/`.hpp` 主体） | ~120,000 行 | ★★★ **逐文件通读**，每 500–900 行一份报告 |
| **B. 生成的数据表**（`sv_const_baselines_mp.cpp` / `*_table_mp.cpp`） | ~13,000 行 / 1.5 MB | ★★ **程序化统计 + 抽样**（与 `enemy_recorded_path` 同一方式） |
| **C. `.bak` 备份**（13 个 / 118,634 行） | — | ★★★ **用 `diff` 对现行版**，只学"改了什么、为什么" |

★★★ **⇒ C 类是最大的效率杠杆：**
```
8 个 `sv_main_mp.cpp.bak-*`（合计 90,128 行）
        ↓
★★★ **与现行 `sv_main_mp.cpp`（11,671 行）逐对 diff**
   ⇒ 每次 diff 只产出"改动块"
   ⇒ 比读 90,128 行高效 **~10 倍**,且**信息量更大**（能看出演进方向）
        ↓
★ 同理 `sv_snapshot_mp.cpp.bak-20261009-scopeidle`（26,441 行）对现行 27,016 行
```

### 5.2 ★★★★★ 优先顺序（按对既有结论的价值排序）

```
① ★★★ **`shared\`（10 文件 / 112 KB）** ⇒ 立刻验证 `CodolPlaylist.cpp:69` 权威表
   （我在报告 079 从 `mp_playlists` 侧推断过 token→gametype 映射,
    现在能拿到**代码级**权威）
② ★★★ **`game_server\qcommon\`（8 文件 / 103 KB）** ⇒ `net_chan_mp` / `net_dtls_cod`
   （对应报告 090 的 `invalid CODOL netchan fragment bounds` / `DTLS public-key TLV`）
③ ★★★ **`backend\Demonware\`（52 文件 / 550 KB）** ⇒ 15 个服务的实现
   （对应报告 090 的 `Alwaysoffline` 服务清单）
④ ★★ **`game_server`（根）的 32 文件** ⇒ `Appmain.cpp`（10,564 行）/
   `EngineBindings`（17,867 行）/ `*Patches`（`CodolClientPatches` 882 行等）
⑤ ★★★ **`game_server\server_mp` 的 154 文件** ⇒ 最大块,分批推进
⑥ ★★ **`tools\`（148 文件）/ `tests\`（24）/ `assets\`（55）/ `docs\`（75）**
⑦ ★ **`.agents\`（59）** ⇒ 用户明确排除的那类,最后处理或跳过
```

---

## 六、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **纠正** | 上一轮"77/77=100%"的**分母错误**；真实是 **77 / 769 = 10.0%** |
| 2 | ★★★ **MANIFEST 复核** | 769 条；非 source **74** 条（**OK 73 / MISMATCH 1 / MISSING 0**）；磁盘多 3 个（`MANIFEST.sha256` / `MANIFEST_SUMMARY.txt` / `re-auth.out.log`）⇒ 非 source 实际 **77** ✓ |
| 3 | ★★★★ **范围误判** | 把"上游开发文档不在范围"扩大成"整个 `source\` 不在范围" |
| 4 | ★★★★★ **`source\` 规模** | **695 文件 / 46,665,874 字节**（占包 **90.4% 文件 / 74% 字节**） |
| 5 | ★★ 二级目录 | `docs` 75/16.5MB · **`src` 286/15.8MB** · `tools` 148/5.65MB · `assets` 55/3.3MB · `tests` 24/2.31MB · `distribution` 7/1.54MB · `.agents` 59/0.97MB · `runtime-assets` 15/264KB · `references` 12/235KB · 根 14/101KB |
| 6 | ★★ 扩展名 | **`.cpp` 144/10.22MB** · `.png` 44/9.49MB · `.json` 26/6.63MB · `.webp` 12/6.56MB · **`.py` 126/1.55MB** · **`.hpp` 142/1.30MB** · `.lua` 32/340KB |
| 7 | ★★★★★ **`src` 精确规模** | **286 文件**；现行 **273 / 9,318,652 B / 163,455 行**；`.bak` **13 / 6,466,674 B / 118,634 行** |
| 8 | ★★ `src` 目录 | **`server_mp` 154/12.6MB** · `game_server` 32/2.18MB · **`Demonware` 52/550KB** · `backend` 13/127KB · `shared` 10/112KB · `qcommon` 8/103KB · `localnetworking` 6/77KB · `platformwrapper` 7/22KB · `client_bridge` 2/7KB · `win32` 2/7KB |
| 9 | ★★★ **最大 5 文件** | `sv_snapshot_mp.cpp` **27,016 行** / `EngineBindings.cpp` **17,867** / `sv_const_baselines_mp.cpp` 3,669 / `sv_main_mp.cpp` **11,671** / `Appmain.cpp` **10,564** ⇒ 合计 **60,787 行 = 37.2%** |
| 10 | ★★★★ **数据表特征** | `sv_const_baselines_mp.cpp` **246 字节/行** ⇒ 是**生成的大表**；`*_table_mp.cpp` 同类 |
| 11 | ★★★ 13 个 `.bak` | **两个家族**：`*.bak-20261009-scopeidle`（3 个）与 `*.bak-刀*`（8 个 `sv_main_mp.cpp` + 2 个其他）+ `noautonuke`（1） |
| 12 | ★★ 8 个 `sv_main_mp` 备份 | 合计 **4,954,708 B / 90,128 行**,大小 615–623 KB（几乎相同）⇒ **同一文件的 8 个演进快照** |
| 13 | ★★★★★ **源码↔二进制对应** | `server_mp`⇔`CodolGameServer` · `Demonware`⇔`Alwaysoffline` · `localnetworking`⇔`Localnetworking.Ayria32` · `platformwrapper`⇔`Platformwrapper.Ayria32` · `backend`⇔`ol_room_owner.exe`；**`Injector32`/`Bootstrapper*` 不在 `src\`** ⇒ **与 `.fptable` 判据再次吻合** |
| 14 | ★★★ 学习策略 | **A 逻辑代码逐读** / **B 数据表程序化统计** / **C `.bak` 用 `diff`**（效率杠杆 ~10 倍） |

---

## 七、结论

### 1. ★★★★★ **我上一轮错了,现在明确纠正**

```
交付包是 **769 文件**,我学了 **77 个（10.0%）**
        ↓
★★★ `source\` 是 **695 文件 / 46.7 MB**（**90.4% 的文件**）
   ⇒ 里面是**这 5 个自建二进制的实现源码**（163,455 行 C++）
        ↓
★★★★★ ⇒ **我之前只看了二进制的外壳（PE 头 + 字符串），没看里面的代码**
```

### 2. ★★★★★ **源码树与二进制的对应关系被完全确认**

★ **⇒ 5 个 ol-mod 自建二进制都有对应的源码目录；3 个 Ayria 上游框架件没有 ⇒ 与 `.fptable` 判据第三次吻合。**

### 3. ★★★★ **`source\src` 的真实学习量是 163,455 行**（另有 118,634 行的 `.bak`）

### 4. ★★★ **`.bak` 备份是最有价值的效率杠杆**（8 个 `sv_main_mp` 快照可用 diff 还原演进）

### 5. ★★ **数据表文件（`*_table_mp.cpp` / `*baselines*`）用程序化统计覆盖**

---

## 八、下一步

按第五节的优先顺序：
1. ★★★ **`shared\`（10 文件 / 112 KB）** —— 立刻验证 `CodolPlaylist.cpp:69` 的权威 token 表
2. `game_server\qcommon\`（8 文件）
3. `backend\Demonware\`（52 文件）
4. `game_server` 根（32 文件）
5. `server_mp`（154 文件，分批）
6. `tools` / `tests` / `assets` / `docs`
