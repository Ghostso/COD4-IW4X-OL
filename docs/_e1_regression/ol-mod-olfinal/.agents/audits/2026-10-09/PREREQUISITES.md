# PREREQUISITES — 运行前置条件核验（阶段 B，2026-10-09）

本文件是阶段 B 的独立记录。**不修改原始审计记录**（AUDIT.md / EVIDENCE_STATUS.md / GOLDEN_COPY_SPEC.md / MANIFEST.json / NON_CODOL_SUBSTITUTIONS.md / SHA256SUMS.txt 保持原样，见提交 6d2705d2）。

统一字段: 状态 / 一手证据位置 / 复现方法 / 证据等级 / 剩余阻塞 / 下一步动作。

---

## 重要更正：1649370 是构建号，不是文件大小

上级指令写“或审计中注明的 `out.exe` 文件大小：1,649,370 bytes”。**这是误读**，原始审计从未如此声称。

一手证据:
- assets/backend/1004/Server/configs_s.info:314 明确写 `build_number=1649370`。
- 全仓库 283 处 `1649370` 引用全部用作**构建标识**，形式为 `CODDIFF(1649370)` / `CODREF(1649370)` / “out.exe build 1649370”。
- docs/olfinal-fastfiles.md:5 “the format recovered from `out.exe` build 1649370”。

结论: 1649370 = out.exe 的 build number。**按文件大小 1,649,370 字节去搜索是错误的**。
- 状态: REFUTED（该前置描述被一手证据否定）
- 证据等级: CONFIRMED（configs_s.info 直接给出 build_number）
- 备注: 我仍按要求做了“大小 == 1,649,370”的全盘扫描，结果 0 命中（见下），进一步说明它不是大小。

---

## B1. 匹配客户端

### 状态: `BLOCKED_NO_MATCHING_CLIENT`

### 目标
`E3823FD6AFC80FB25FA84747E6E9634707B9A0B189357A5466921CDA354AF37B`（记录中的已验证 3.3.3.3 客户端）

### 一手证据位置
本次独立扫描: D:\\、E:\\、F:\\、G:\\、C:\\Users（深度 8-10）
- 扫描文件数: **2,138,998**
- 候选（名称匹配 codoMP_client_shipRetail.exe / out.exe / olalpha13.exe，或大小恰为 1,649,370）: **42**
- 去重后**仅 2 个不同构建**:

| SHA-256 | 份数 | 大小 | 示例路径 |
| --- | --- | --- | --- |
| 36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537 | 41 | 7,841,344 | D:\\BaiduNetdiskDownload\\codoMP_client_shipRetail.exe |
| 7B31168D42A5A6BA11750D404971EE52F9FD1CAB93C56A8A85DA94AE76C41342 | 1 | 7,841,344 | D:\\...\\使命召唤OL\\工具\\EXPERIMENT_017_BOOT_SKIP\\codoMP_client_shipRetail.exe |

- `TARGET_SHA_FOUND = false`
- `out.exe` 实例数 = **0**
- 大小恰为 1,649,370 字节的文件 = **0**
- 两个本地构建均已标记 **MISMATCH**（名称相同不构成匹配）

### 复现方法
遍历上述根目录，对每个名称候选计算完整 SHA-256，与目标常量逐字节比较；不使用文件名或大小作为判定依据。

### 证据等级
CONFIRMED（本次独立计算；方法可重复）

### 剩余阻塞
需要外部提供匹配构建。**不得**从不可信来源下载可执行文件，**不得**尝试修改二进制以匹配哈希。

### 下一步动作
用户在合法安装目录 / 归档 / 备份中提供 SHA-256 = E3823FD6... 的客户端（或 OLfinal 的 out.exe）。在取得之前:
- 不得猜测或使用任何 RVA、结构偏移、parser 行为；
- 所有依赖客户端构建的结论保持 INSTRUMENTATION_BLOCKED。

---

## B2. 完整 CODOL 游戏资产目录

### 状态: `BLOCKED_NO_VERIFIED_ASSET_SET`

### 已配置目录
- config/codol-game-dir.txt = `D:\\codo_3.19.26.13_fresh\\CoD Online`
- **不存在**（exists=false）

### 一手证据位置（本机实际存在的 CODOL .ff）
在 D:\\BaiduNetdiskDownload\\使命召唤OL 下（深度<=9）找到 **42 个 .ff**，分布 5 个目录:

| 目录 | 文件数 | 字节 | common_mp.ff | ui_mp.ff | 地图 .ff |
| --- | --- | --- | --- | --- | --- |
| run_codol_001\\sandbox_datafix_20260929\\main | 16 | 151,330,643 | 有 | 有 | **0** |
| backup_reverse_engineering\\...\\error100_dwauth_20260927_042146\\main | 10 | 40,411,390 | 无 | 有 | **0** |
| COD OL\\main | 10 | 40,411,390 | 无 | 有 | **0** |
| CODOLServer\\logs\\IFS_EXTRACT_TEST | 3 | 33,096,841 | 无 | 无 | **0** |
| backup_reverse_engineering\\...\\IFS_EXTRACT_TEST | 3 | 33,096,841 | 无 | 无 | **0** |

容器头核验（逐个读取前 24 字节）:
- 全部 42 个: magic = `IWff0100`，**v8 = 461**
- 即容器版本与 docs/olfinal-fastfiles.md 记录的 OLFinal 外层版本一致（461），文件可读、结构可识别。
- 去重后**仅 16 个不同文件名**。

### 关键判定
1. **没有任何地图 fastfile**。去重后唯一的 “mp_*” 文件是 `mp_playlists.ff`（49,493 字节，publisher 播放列表，不是地图）。没有 mp_crash_tropical.ff / mp_nuked.ff / zm_factory_sh.ff。
2. 这些资产属于**旧沙箱**，绑定的客户端是 36997674...（与目标 E3823FD6... 不匹配），无法建立“资产 <-> 目标构建”的可验证对应关系。
3. 全盘另有 24,662 个 .ff（约 59.6 GB），但绝大多数属于**其他游戏**（E:\\IW4X、Call of Duty WWII、Infinite Warfare、World at War 等）。**这些不是 CODOL 资产，不得用于冒充 CODOL 原生数据。**

=> 缺地图资产意味着 level-zone load（ClipMap/MapEnts/ComWorld）无输入，**无法加载任何战斗地图**。

### 复现方法
1. 遍历 CODOL 目录，对每个 .ff 读取前 24 字节记录 magic 与 v8；
2. 按文件名分类，统计 map-like（mp_/zm_/coop_/sp_）文件数；
3. 与客户端构建做配对核验（要求同一构建来源）。

### 证据等级
CONFIRMED（容器头与文件清单为本次直接读取）。资产与目标构建的对应关系: UNKNOWN。

### 剩余阻塞
需要完整 CODOL 3.3.3.3 / OLFinal 安装（含各地图 .ff），且与目标客户端构建同源。

### 下一步动作
用户提供完整游戏目录；随后逐 .ff 记录大小与 SHA-256、核验容器头、并确认与目标构建的对应关系。

---

## B3. 构建工具链

### 状态: `BUILD_NOT_CONFIRMED`（工具链缺失，无法构建）

### 仓库实际声明的需求（先读配置，再查环境）
来源 xmake.lua 与 vcpkg.json:
- xmake.lua:10 `set_toolchains("msvc")`
- xmake.lua:13 `set_languages("c++latest")`
- xmake.lua:58 `add_requires("vcpkg::openssl", ...)`
- xmake.lua:62 `add_requires("vcpkg::mhook", ...)`
- xmake.lua:66 `add_requires("nlohmann_json 3.12.0")`
- xmake.lua:67 `add_requires("lua 5.4.8", {configs = {shared = false}})`
- vcpkg.json:7-8 依赖 `mhook`, `openssl`；:5 `builtin-baseline = aa2d37682e3318d93aef87efa7b0e88e81cd3d59`
- 需要的 vcpkg triplet: `x86-windows-static`（README.md:31、AGENTS-OLFINAL.md 语境）
- 7 个测试套件必须通过（AGENTS-OLFINAL.md:115-117），均通过 xmake 运行。

### 环境检查结果（非破坏性）
| 工具 | 结果 |
| --- | --- |
| MSVC / cl.exe | 不存在；vswhere.exe 也不存在 → 无任何 Visual Studio 安装 |
| xmake | 不存在（PATH 与文档记载路径 D:\\Program Files\\xmake 均无） |
| vcpkg | 不存在；VCPKG_ROOT 为空 |
| cmake / ninja | 不存在 |
| build/ 目录 | 不存在 |
| Python 3.11 / py / git | 存在 |

搜索范围: C:\\Program Files、C:\\Program Files (x86)、D:\\、E:\\、F:\\（深度 3-4），结果 0 命中。

### 复现方法
`Get-Command xmake/cl/cmake/ninja`；检查 vswhere.exe；检查 VCPKG_ROOT；全盘搜索 MSVC/vcpkg/vswhere。

### 证据等级
CONFIRMED（工具链缺失为本次直接核验）

### 剩余阻塞
未实际构建 → **不得**标记 BUILD_CONFIRMED。仅有工具存在也不构成可构建的证明。

### 下一步动作（建议，未执行）
需用户在本机安装并授权后再进行构建:
1. Visual Studio 2022（含 C++ 桌面工作负载与 Windows SDK）；
2. xmake（≥3.0.9，README.md:31）；
3. vcpkg，`VCPKG_ROOT` 指向其根目录；
4. 依赖 `openssl` / `mhook` / `nlohmann_json 3.12.0` / `lua 5.4.8`（前两者走 vcpkg，triplet `x86-windows-static`）。
本任务**未**修改任何全局环境，也未升级项目依赖。

---

## 前置条件总表

| 项 | 状态 | 证据等级 | 阻塞 |
| --- | --- | --- | --- |
| B1 匹配客户端 | `BLOCKED_NO_MATCHING_CLIENT` | CONFIRMED | 需目标构建 |
| B2 完整资产集 | `BLOCKED_NO_VERIFIED_ASSET_SET` | CONFIRMED（缺失） | 需完整游戏目录含地图 .ff |
| B3 构建工具链 | `BUILD_NOT_CONFIRMED` | CONFIRMED（缺失） | 需 MSVC + xmake + vcpkg |
