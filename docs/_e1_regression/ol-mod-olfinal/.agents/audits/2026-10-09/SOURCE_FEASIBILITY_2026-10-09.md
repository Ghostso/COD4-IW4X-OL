# SOURCE_FEASIBILITY_2026-10-09 — 前置条件解除与源码可行性核验

新增的阶段记录，**不覆盖任何已冻结的审计记录**（SHA256SUMS.txt / STAGE2 / STAGE3 保持原样，本次全部复验通过）。

机器可读版本: `source_feasibility.json`（32 项检查，每项含 status/evidence/expected/actual/reason/next_action）
fastfile 清单: `fastfile_inventory.json`

---

## 0. 本轮结论（一句话）

**战斗链路在源码层面是「普遍 partial」而不是「已实现」；三项前置条件（客户端 / 地图资产 / 工具链）全部未满足，因此本轮没有任何运行验证。**
唯一新达成的可核验产出是：一份完整的 `.ff` 清单（42 个、含逐文件 SHA-256）与一次对 preflight 判定逻辑的**实证反例**（24 字节伪造文件即可拿到 `ASSET_SET_VERIFIED`）。

## 1. 基线安全（执行前重新检查，未假定报告之后无变化）

| 项 | 值 |
| --- | --- |
| HEAD | `1276b7299e9ccaa98d99193ed0a97a956bbe9928` |
| 分支 | `OLfinal-live` |
| 工作树 | `porcelain = 0`，`stash = 0` |
| 与上游 | `0 behind / 3 ahead`（**未推送**） |
| 变更文件 vs origin | 17 个，全部为 `.agents/audits/2026-10-09/**` + `codol-preflight.ps1`；**`src/` 修改 = 0** |
| 备份 | `E:\OLMOD_BACKUP_20261009_095356` 存在（821 文件） |
| 审计清单复验 | `SHA256SUMS.txt` 6/6、`STAGE2` 4/4、`STAGE3` 3/3 全部通过 |

未执行 reset / clean / checkout 覆盖；未 amend、未改写 author、未推送。

## 2. preflight 判定逻辑审计（任务明确要求逐条检查）

| # | 检查点 | 结论 | 证据 |
| --- | --- | --- | --- |
| P1 | 是否正确识别客户端 SHA-256 | **PASS** | 只按完整 SHA-256 精确比对；`FileVersion` 不参与判定 |
| P2 | 是否把 FileVersion 错当身份 | **WARN** | 未用于判定，但该行以 `status=PASS` 记录（标注 informational），PASS 令牌可能被误读 |
| P3 | 是否把 `.ff` 容器头当成完整地图资产证明 | **FAIL（已实证）** | 见 §2.1 |
| P4 | 是否验证工具链版本/架构/依赖/triplet | **FAIL** | 仅 `Get-Command` 存在性检查；无 MSVC 版本、无 xmake 版本（仓库要求 ≥3.0.9）、无 `x86-windows-static` triplet、无 OpenSSL |
| P5 | 是否存在错误返回 `READY_TO_BUILD` 的路径 | **WARN** | 本机不可达（客户端与工具链均失败）；但 `READY_TO_BUILD = 客户端哈希 ∧ assetsOk ∧ toolchainOk`，而后两项都过弱，最弱项决定整体强度 |
| P6 | JSON/编码/换行/哈希可重复验证 | **PASS** | 实测 `BOM=false, CRLF=0, validJson=true` |
| P7 | 报告哈希可重复性 | **PARTIAL** | 报告含 `generatedAt` 与绝对路径 → **字节与 SHA-256 每次运行都不同**；可复现的是状态集合，不是文件哈希 |

### 2.1 P3 的实证反例（本轮最重要的发现）

我没有只读代码判断，而是**构造了一个反例并实际运行**：

```
创建 C:\Windows\Temp\codol-preflight-probe\main\mp_fake.ff
内容 = 24 字节：ASCII "IWff0100" + UInt32LE 461 + 8 字节 0
运行 .\codol-preflight.ps1 -RepoPath . -GamePath <该临时目录> -OutFile <临时>\probe.json
```

实测结果:

| 字段 | 值 |
| --- | --- |
| `verdict` | `BLOCKED`（因客户端与工具链失败） |
| **`tokens.ASSET_SET_VERIFIED`** | **`true`** ← 24 字节伪造文件 |
| `tokens.CLIENT_HASH_VERIFIED` | `false` |

根因: `game.map_ff` 只做**文件名正则**（`^(mp|zm|coop|sp)_` 且不含 playlist），`game.header` 只探测**体积最大的那一个**文件的头，且**完全不检查资产与目标构建的关联**。
因此 `ASSET_SET_VERIFIED` 这个令牌当前可以被一个文件名正确、头部合法、内容为空壳的文件骗过——这与任务对该令牌的定义（“地图资产清单、哈希及构建关联经过验证”）严重不符。

**本轮未修改该工具**（避免动到已冻结的 STAGE3 记录）。建议的最小收紧见 §7。

## 3. 战斗链路逐项证据表（阶段 A.4/A.5）

状态定义: `CONFIRMED` / `PARTIAL` / `NOT_IMPLEMENTED` / `UNKNOWN` / `BLOCKED`。
**任何一项都不得因“函数存在 / 常量存在 / 注释 / 别的游戏的实现”而升级为已完成。**

| 领域 | 状态 | 具体源文件与函数 | 实际调用链 | 已有测试 | 与 CODOL 目标构建一致的证据 | 缺失的运行时验证 |
| --- | --- | --- | --- | --- | --- | --- |
| 连接与认证 | PARTIAL | `sv_client_mp.cpp:3360-3382` getchallenge、`:3384-3515` connect、`:522-556` stats；`qcommon/net_dtls_cod.cpp:544/712`、`:197-231` 密钥派生 | encode→DTLS→OOB dispatch→router | fixtures `ServerCoreTests.cpp:27314-27391`（DTLS/明文/HMAC）、`:27478-27500` | **DTLS 与 getchallenge 为捕获字节 CONFIRMED**；connect 的 name/rank/natType 等 userinfo 键**仅存在于手工 fixture**，属 [REF] | 从未执行 |
| netchan 收发 | PARTIAL | `qcommon/net_chan_mp.cpp:660` Process、`:1012` Transmit、`:1061` TransmitNextFragment、`:623` XOR | 入站 entry `sv_client_mp.cpp:643→:747` | fixtures `:27502-27517`（首个客户端包）、`:27546-27555` | 首个包 XOR 布局与 **EOF=5**（3.3.3.3 为 6）已由捕获字节 CONFIRMED | 从未执行 |
| gamestate 与配置字符串 | PARTIAL | `server_mp/sv_gamestate_mp.cpp:949-995` SV_WriteGameState；`sv_gamestate_mp.hpp` 分段常量 | configureBooking→configureGameState→writers | `ServerCoreTests.cpp` 1649370 configstring map fixtures | 索引映射是 **1649370 派生**；catalog 未给出 CODOL 自身的 gamestate producer 映射 | 从未执行 |
| 客户端状态管理 | PARTIAL | `sv_client_mp.hpp:137` ClientSlot、`:457-461` 超时；`sv_client_mp.cpp:1438-1501` sweep | 每帧 sweep→snapshot | `ServerCoreTests.cpp` 调度/超时用例 | 源码 45s/15s；文档仍写 80s/240s → **REFUTED** | 从未执行 |
| world/map 初始化 | PARTIAL + BLOCKED | `Appmain.cpp:2527-2592`；`EngineBindings.cpp:4525-4650`（CM_LoadMap `0x585B20`、CM_LinkWorld `0x58C810`） | SessionStart→level-zone load→CM_LoadMap→CM_LinkWorld→CCS | 无运行测试可能 | RVA 绑定 out.exe 1649370，**目标构建缺失** | 需目标构建 + 地图 .ff |
| entity / playerState | PARTIAL | `sv_native_playerstate_mp.hpp:23`（本构建 `0x3BBC`）、`sv_native_entitystate_mp.hpp:32-36`（`0x118`）、`sv_client_spawn_mp.cpp:206-412` | command candidate→overlay→round-trip→commit | `ServerCoreTests.cpp` static_assert/往返用例（未运行） | 尺寸由该构建自身 clear loop 推得；`0x3564` 属**另一构建** | 从未执行 |
| 快照生成与发送 | PARTIAL | `sv_snapshot_mp.cpp:10082` SV_WriteSnapshot；`sv_client_mp.cpp:1418-1427` | world endFrame→SV_SendClientMessages→DTLS | `ServerCoreTests.cpp` 快照 fixtures（未运行） | 50 ms 节拍是 **[SRC] + 显式 TODO(CODOL)**，且 **LAN peer 直接旁路** | 速率契约未恢复；从未执行 |
| 输入/移动/伤害/规则 | PARTIAL | `NativePmoveBindings.cpp:650`；`sv_bullet_mp.cpp`；`sv_damage_mp.*` | usercmd→PmoveSingle→events→dispatcher | `ServerCoreTests.cpp` gameplay 用例（未运行） | catalog: **38/39 partial，1 missing**（`g_run_frame_for_entity`） | penetration / vehicle / pain-die 未闭合 |
| 多客户端状态同步 | PARTIAL / NOT_IMPLEMENTED | `src/backend/SharedRoom*.cpp`、`DedicatedBookingDispatcher.cpp` | room owner→freeze roster→逐成员 capture→SessionStart v5 | `shared/DedicatedSessionTests.cpp`、`ClientSessionBridgeTests.cpp`（未运行） | owner 已建立；**dispatcher 多 bridge capture 未接线** | 两个真实客户端从未验证 |

### 3.1 仓库自身的广度清单（权威自评）

`tools/reverse/catalogs/codol_server_function_matrix.json`（updated_at 2026-08-16）:

| 字段 | 分布 |
| --- | --- |
| entries | **39** |
| implementation_status | **partial 38 / missing 1**（missing = `g_run_frame_for_entity`） |
| classification | server_only 27 / client_shared 6 / embedded_server 6 |
| confidence | high 35 / medium 4 |

其 `limitations` 明确写着：**“Implementation status is a current repository inventory, not proof of runtime conformance.”** 这正是本轮的结论依据。

## 4. 客户端身份（阶段 B1，受限核验，未全盘重扫）

| 候选 | SHA-256 | 大小 | 判定 |
| --- | --- | --- | --- |
| `D:\BaiduNetdiskDownload\codoMP_client_shipRetail.exe` | `36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537` | 7,841,344 | **MISMATCH** |
| `...\使命召唤OL\COD OL\codoMP_client_shipRetail.exe` | 同上 | 7,841,344 | **MISMATCH** |
| `...\工具\EXPERIMENT_017_BOOT_SKIP\...exe` | `7B31168D42A5A6BA11750D404971EE52F9FD1CAB93C56A8A85DA94AE76C41342` | 7,841,344 | **MISMATCH** |
| `out.exe`（深度<=3，4 个授权根） | — | — | **0 命中** |

批准目标: `E3823FD6AFC80FB25FA84747E6E9634707B9A0B189357A5466921CDA354AF37B`

PE 分析（本地候选）: Machine 0x14C(x86)、PE32、ImageBase 0x400000、TimeDateStamp 2021-05-08、节区 **`.tp3`×5 + `.tvm0`**（加壳）。RVA `0x8371A` 实测 `00D945108B4D088B`，与 build 1649370 期望 `837C2408010F94C0` **不一致**。
**保留不确定性**: 加壳镜像的文件字节不代表运行时解壳后的内存镜像；运行时一致性仍为 `UNKNOWN`。

## 5. 地图资产（阶段 B2）

完整清单见 `fastfile_inventory.json`。

| 项 | 值 |
| --- | --- |
| 资产根 | `D:\BaiduNetdiskDownload\使命召唤OL` |
| `.ff` 总数 / 去重 | 42 / **16** |
| 总字节 | 298,347,105 |
| 容器头 | 全部 `IWff0100` **v461**（一致） |
| **地图 .ff** | **0**（`MAP-CANDIDATE = 0`） |
| 分类计数 | marketplace 6、localized-common 7、localized-code 6、code 9、common-mp 4、development 3、playlists 3、ui 3、loadscreen 1 |
| 与目标构建的关联 | **UNKNOWN**（资产来自客户端为 `36997674...` 的沙箱，该客户端本身 MISMATCH） |

说明: 配置目录 `D:\codo_3.19.26.13_fresh\CoD Online` 不存在；`mp_playlists.ff` 是**播放列表发布文件**，不是地图，已单独归类而非计入地图。
全盘另有约 2.4 万个 `.ff` 属其他游戏（IW4X/WWII/Infinite Warfare/WaW），**明确排除，不作 CODOL 原生数据**。

## 6. 工具链与构建（阶段 C）

- 仓库声明（先读声明，未猜测版本）: `xmake.lua:10` `set_toolchains("msvc")`、`:13` `c++latest`、`:58/62` `vcpkg::openssl`/`mhook`、`:66` `nlohmann_json 3.12.0`、`:67` `lua 5.4.8`(static)；`vcpkg.json:5` baseline `aa2d3768...`、`:7-8` `mhook`,`openssl`；triplet `x86-windows-static`；7 个测试目标（`xmake.lua:245,258,272,285,311,324,352`）。
- 实测: MSVC / cl / vswhere / xmake / vcpkg / cmake / ninja **全部不存在**，`VCPKG_ROOT` 为空，无 `build/`。
- **`BUILD_CONFIRMED` 不成立**；未安装任何组件（安装需授权）。**测试退出码: 全部 NOT_RUN**（7 个套件一个都没跑）。

## 7. 提议的最小收紧（未应用，等待批准）

针对 §2.1 / §2.2 的两处过弱判定，建议的最小差异（只使判定**更严格**，不可能放宽）：

```diff
--- a/codol-preflight.ps1
+++ b/codol-preflight.ps1
@@ ASSET gate @@
-        $maps = @($ffs | Where-Object { $_.Name -match '^(mp|zm|coop|sp)_' -and $_.Name -notmatch 'playlist' })
-        Add-Check "game.map_ff" ...
+        # a map fastfile must be a real map, not a filename match: require a
+        # substantiated file (min size), a readable header, and an explicit
+        # build-association statement supplied by the caller.
+        $maps = @($ffs | Where-Object { $_.Name -match '^(mp|zm|coop|sp)_' -and $_.Name -notmatch 'playlist' -and $_.Length -ge 1MB })
+        Add-Check "game.build_association" "asset set associated with the target build" (if ($BuildAssociation) {'PASS'} else {'FAIL'}) ...
@@ header gate: probe ALL map candidates, not just the largest @@
-            $probe = $ffs | Sort-Object Length -Descending | Select-Object -First 1
+            $probe = $maps + $ffs | Sort-Object Length -Descending | Select-Object -First 8   # sample, and fail if ANY is unreadable
@@ toolchain gate @@
+    # verify versions/arch/triplet/deps, not mere presence:
+    #   cl   : cl 19.3x/19.4x, host x64, target x86
+    #   xmake: >= 3.0.9
+    #   vcpkg: triplet x86-windows-static resolvable; openssl installed
```

风险: 数值阈值（如 1MB）是启发式，仍需 `build_association` 这类**由调用方显式声明**的证据来承担真正的判定。回滚: 该文件为新增工具，`git checkout 1276b72 -- codol-preflight.ps1` 即恢复。
**批准后我会在下一轮应用，并生成 STAGE4 记录（不修改 STAGE3）。**

## 8. Git 状态 / 变更 / 备份

| 项 | 值 |
| --- | --- |
| 本轮开始 HEAD | `1276b7299e9ccaa98d99193ed0a97a956bbe9928` |
| 本轮结束 HEAD | 见下一轮提交（本轮新增 `SOURCE_FEASIBILITY_2026-10-09.md`、`source_feasibility.json`、`fastfile_inventory.json`、`SHA256SUMS_STAGE4.txt`） |
| `src/` 修改 | **0** |
| 备份 | `E:\OLMOD_BACKUP_20261009_095356`（未覆盖） |
| 推送 | **未推送**（0 behind / 3 ahead） |
| 冻结基线 | SHA256SUMS / STAGE2 / STAGE3 **未修改**，本轮复验全部通过 |

## 9. 未解决阻塞

| # | 阻塞 | 影响的令牌 |
| --- | --- | --- |
| 1 | 无批准客户端（目标哈希缺失；`out.exe` 缺失；本地两个构建均加壳且不匹配） | `CLIENT_HASH_VERIFIED` 及所有运行令牌 |
| 2 | 无地图 `.ff` | `ASSET_SET_VERIFIED`、世界加载 |
| 3 | 无工具链 | `TOOLCHAIN_READY`、`BUILD_CONFIRMED`、所有测试 |
| 4 | pktmon 需提权；任务给的旧语法在本机无效 | 网络取证 |
| 5 | 无 Golden Copy（依赖 1-3） | 全部运行时令牌 |
| 6 | live 交接仓库 `CODOL-main` / `OLFINAL-FFA-HANDOFF.md` 不在本机 | 分支最新意图 |

## 10. 需要用户提供或批准

1. **提供** `E3823FD6...` 的客户端；**或明确批准**改用 OLFinal `out.exe` 构建（并给出其 SHA-256）——批准后须重建基线并重新核验 RVA/协议/资产，**不得混用两个构建的证据**。
2. **提供**含地图 `.ff` 的完整 CODOL 安装目录。
3. **授权**安装工具链（VS2022 C++ + Windows SDK + xmake + vcpkg `x86-windows-static` + OpenSSL）。
4. **批准** §7 的 preflight 收紧补丁。
5. **授权**提权运行 pktmon（并接受回环漏抓的限制）。

---

## 11. 本轮结束时必须回答的五个问题

**Q1. 当前源码中哪些战斗链路是真正实现的，哪些只是部分实现或尚未验证？**
按仓库自身的广度清单: 39 项中 **partial 38 / missing 1**。按领域：连接与认证、netchan、gamestate/CCS、客户端状态、entity/playerState、快照生成 —— 都是 **PARTIAL**：源码在手、有捕获字节 fixture 支撑局部协议一致性，但**没有一项有真实运行验证**。world/map 初始化是 **PARTIAL + BLOCKED**（RVA 绑定缺失的目标构建）。输入/移动/伤害/规则是 **PARTIAL**（penetration、vehicle、pain/die 未闭合）。多客户端同步是 **PARTIAL / NOT_IMPLEMENTED**（room owner 有，多 bridge capture 未接线）。
**没有任何一项可以标为 CONFIRMED（运行时）。**

**Q2. 目前最先需要用户提供的一个工件是什么，为什么？**
**批准的目标客户端二进制**（`E3823FD6...`，**或**明确批准的 OLFinal `out.exe` + 其 SHA-256）。
原因：它是**唯一的根依赖**。OLMod 的全部关键路径（`EngineBindings.hpp` 的每个 RVA、netfield 表、patch 字节、playerState/entityState 布局）都以特定构建为键；没有它，既不能复核任何协议/结构，也不能运行任何测试或对局。地图资产和工具链都是它的下游——有了客户端，资产同源问题才可判定；有了客户端+资产，工具链才值得投入。

**Q3. 客户端、地图资产和工具链分别通过什么可重复的检查才能解除阻塞？**
- **客户端**（`CLIENT_HASH_VERIFIED`）: 对候选文件做完整 SHA-256 并与批准哈希**精确比对**（不看文件名、不看 FileVersion）。可重复命令:
  `Get-FileHash <client> -Algorithm SHA256`，或 `codol-preflight.ps1 -ClientPath <client> -ExpectedClientSha256 <approved>` 返回该检查 PASS。若走 OLFinal 路线，则先由用户批准并把批准哈希写入基线（**不是我自动改期望值**）。
- **地图资产**（`ASSET_SET_VERIFIED`）: 至少 1 个真实地图 `.ff` + 完整清单（路径/大小/SHA-256/容器头）+ **与目标构建的关联证据**。当前只完成了清单与容器头两项，地图数=0、关联=UNKNOWN → 仍阻塞。检查必须在我 §7 收紧**之后**才具说服力（当前实现会被空壳文件骗过）。
- **工具链**（`TOOLCHAIN_READY` → `BUILD_CONFIRMED`）: 记录实际版本（MSVC 版本、xmake ≥3.0.9、triplet `x86-windows-static`、OpenSSL），然后**真实执行** `xmake build ol_game_server`，保存 stdout/stderr/退出码/产物 SHA-256。只有退出码 0 才可标记。

**Q4. 当前有哪些工作可以安全并行推进？**
1. **应用并验证 preflight 收紧补丁**（P3/P4），并用反例回归（`mp_fake.ff` 必须不再获得 `ASSET_SET_VERIFIED`）。这是纯工具、风险最低、直接消除一个假阳性。
2. **完善 fastfile 清单**：把分类、容器头、哈希写成可复跑的清单工具（当前清单已产出 `fastfile_inventory.json`，可加一个 `-Verify` 模式）。
3. **把 S2/S3 的“可追溯性”设计成纯增量改动**（在注册 destructible / 使用玻璃阈值时把数据来源写进运行日志与 summary），**不改默认行为**——但需要工具链才能验证，所以只能先出设计。
4. **静态文档一致性修正**：把已确认的 REFUTED 数值（帧率、timeout、0x3564/0x3BBC、0x110/0x118、235/246）在文档中校正——但这属于改动既有文档，需批准。
5. **准备阶段 D 的编排器改动方案**（证据目录规范、PCAP 正确语法、LAN 漏抓限制的记录字段）——只出方案不执行。

**Q5. 下一步的唯一最高优先级是什么？**
**取得并批准目标客户端二进制（`E3823FD6...`，或用户明确批准的 OLFinal `out.exe` 及其 SHA-256）。**
在它到手之前，任何构建、抓包、Golden 或运行时验证都无法产生可信证据；其余工作只能是静态推断。与此同时唯一可并行且零风险的动作，是批准并应用 §7 的 preflight 收紧补丁，以消除当前可被 24 字节空壳文件骗过的 `ASSET_SET_VERIFIED` 假阳性。

## 12. 纪律声明

- 未执行任何 reset / clean / checkout 覆盖 / 格式化。
- **未执行 `commit --amend`**、未改写 author、未重置、未强推。
- 未修改 `src/`、未改协议常量/RVA/ABI、未动 S2/S3 默认行为。
- 未覆盖原始备份，未修改已冻结的 SHA256SUMS / STAGE2 / STAGE3。
- 未安装任何工具链组件。
- 未使用 Sandboxie / Procmon / WMI / debugger / anti-debug 绕过。
- 未下载任何来源不明的二进制。
- 所有未执行项记为 `NOT_RUN`，无法判断项记为 `UNKNOWN`，失败保留为失败。
