# 01 — 本地逆向资产盘点 / REVERSE ASSET INVENTORY

**任务**：`CODOL-BATTLE-SERVER-REVERSE-COVERAGE-001` 第一阶段
**日期**：2026-10-12
**方法**：只读枚举工作区与本机相关目录；二进制逐文件计算 SHA-256；文档转述一律标注复核状态。
**工作区根**：`D:\BaiduNetdiskDownload\使命召唤OL\`（另有样本位于 `D:\BaiduNetdiskDownload\CODOL.NET\`、`D:\BaiduNetdiskDownload\CODOL_2697_Launcher\`，均在库外但可读）。

> 复核状态：`已复核` = 本轮直接读取文件/哈希；`已登记` = 本轮读取，内容未逐行复核；`文档转述` = 仅来自上游报告，本轮未直接读取原始载体。
> 不能访问或未验证的文件一律标注，不假设已检查。

---

## 1. 目标版本锚点

| 版本 | 客户端 SHA-256 / 大小 | 版本判定依据 | 等级 |
|---|---|---|---|
| **2.6.9.7（最终版，兼容目标）** | `353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1` / 9,964,656 B | `manifest.json` `version=2.6.9.7`，`original_exe_sha256` 与之一致；TenProtect `.tp3`×6+`.tvm0` 段 | CONFIRMED |
| 3.3.3.3（QA，title 1004） | `36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537` / 7,841,344 B | FileVersion 1649370；ol-mod 运行分发目标 | CONFIRMED（上游登记） |
| 1.1.1.13（早期） | `904436480938632a856b39dea73fb94c9682b5a0ebf7fa619ecd5dd5475ed3b6` / 20,918,752 B | 早期 AlphaBuild 配套 | CONFIRMED（上游登记） |

> **警告**：3.3.3.3 与 2.6.9.7 均为 `codoMP_client_shipRetail.exe`，但大小/哈希/fileversion 完全不同。任何跨用必须显式标注（上游 CONFLICT-05）。

---

## 2. 客户端与战斗服务器相关二进制

| 相对/绝对路径 | 类型 | 大小(B) | SHA-256 | 游戏版本 / 判定依据 | 样本分类 | 已有研究 | 与战斗服务器的关联 | 复核状态 |
|---|---|---|---|---|---|---|---|---|
| `D:\...\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe` | PE32 加壳客户端 | 9,964,656 | `35375404…14d6e1` | 2.6.9.7（manifest） | 原始样本 | 2687 客户端逆向、E06/E08/E09/E11/E12/E15/E20… | **兼容目标**；客户端消费链证据来源 | 已复核 |
| `D:\...\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe` | PE32 服务端 | 7,295,919 | `80816711…50ea1` | 2697（配套 launcher；无源码；含 2697 协议层） | 原始样本 | `CODOL_2697_SERVER_STATIC_ANALYSIS_20261011`、`12_CODEC_MVP_001` | **唯一 2697 协议事实源** | 已复核 |
| `D:\...\CODOL.NET\Game\CODOL_2.6.9.7\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe` | 服务端镜像 | 7,295,919 | 与上逐字节相同 | 同上 | 重复样本 | — | 冗余，使用主 EXE 即可 | 文档转述 |
| `D:\...\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin` | aplib 静态恢复镜像 | 12,571,648 | `24b4ef25…b97e4` | 2697 | 分析产物 | E06…；`15_CLIENT_SERVER_EVIDENCE_CORRELATION.md` | 客户端静态分析载体；**非运行时 dump** | 已复核（文件） |
| `D:\...\CODOL_2697_Launcher\manifest.json` | JSON 清单 | 1,558 | `34017bf7…da00` | 2.6.9.7 | 分析产物/基线 | 版本与组件哈希基线 | 版本判定锚点 | 已复核 |
| `...\server2697\client_room2697.dll` | DLL | 184,832 | `120c4cfd…f6c3a7` | 2697 | 原始样本 | 与 manifest 一致 | 客户端房间/loopback 组件 | 文档转述 |
| `...\server2697\client_native_loopback.dll` | DLL | 125,440 | `53c6fbe2…e4074829` | 2697 | 原始样本 | 与 manifest 一致 | loopback 客户端桥 | 文档转述 |
| `...\server2697\client_loopback_guard.exe` | EXE | 242,176 | 未登记 | 2697 | 原始样本 | loopback 审计 | 本地隔离链路守卫 | 文档转述 |
| `...\server2697\evidence\client-registration2697.txt` | 文本证据 | 2,976 | `4f1b4a38…289e2c` | 2697 | 分析产物 | `12_CODEC_MVP_001` | 2697 合法注册校验输入格式实例 | 文档转述 |

---

## 3. 旧版服务端（含源码，参考实现）

| 路径 | 类型 | 大小(B) | SHA-256 | 版本 | 分类 | 关联 | 复核状态 |
|---|---|---|---|---|---|---|---|
| `EARLY_SERVER_ANALYSIS\13_NATIVE_TAP_BUILD_001\experiment_copy\bin\codol_dedrun.exe` | PE32 服务端 | 8,469,493 | `28366ae9…dd98a` | 1.1.1.13（CoD4x fork） | 原始样本+源码配套 | netchan/msg/sv_* 源码；`src\codol\net`、`src\codol\snapshot` | 已复核 |
| 同目录 `codol_dedrun_next.exe` | 重复构建 | 8,469,493 | 与上逐字节相同 | 同上 | 重复样本 | — | 文档转述 |
| `D:\...\CODOL.NET\Game\CODOL_1.1.1.13\CODOL_Server\dedicated\bin\codol_dedrun.exe` | PE32 服务端 | 8,622,389 | `a96c5dfb…5cb6e9` | 1.1.1.13 | 原始样本+同源源码 | 与 S-Old 同源（1 文件差异） | 已复核 |

> **关键**：S-Old / S-1113 / S-2697 是三个互不相同的构建（大小/哈希/节区/导入/符号/字符串均不同）。**不得**因同名 `codol_dedrun.exe` 视为同一构建。
> **源码对应性**：OLD 的 `dedicated\src\` 完整存在，但**无 PDB/MAP**，源码行号↔二进制 RVA 的逐函数对应**未建立**（上游 CONFLICT-08，BLOCKED）。

---

## 4. 独立/参考服务端工程

| 资产 | 路径 | 规模 | 目标版本 | 分类 | 关联 | 复核状态 |
|---|---|---|---|---|---|---|
| ol-mod 全源码 | `_e1_regression\ol-mod-olfinal` | 1,555 文件 / 1,182.6 MB；`src\game_server` 173 文件 / ~139,300 行 | 3.3.3.3 QA | 参考实现（含源码） | 最完整 CODOL 原生服务端；`DedicatedControl`/booking/ServerCore | **已复核（本轮新确认存在）** |
| C# 战斗服 | `CODOL-Combat-Server-v0.1` | 75 文件 / 0.5 MB；22 源文件 | 未标 2697 | 参考实现（含源码） | 可 `csc` 构建；122 项离线自测；协议字节来自抓包 | 已复核 |
| C# 构建产物 | `CODOL-Combat-Server-v0.1\build\bin\CODOLCombatServer.exe` | 126,464 | — | 分析产物 | `--selftest` 111/122 通过（3 项临时目录权限） | 已复核 |
| Python lobby/server | `CODOLServer` | 21,047 文件 / 4,672.8 MB | 多版本实验 | 参考实现 | lobby/认证/IIPS/TCLS/抓包洞察 | 已登记 |
| 协议逆向线 | `REF_LOBBY_KIT` | 35,489 文件 / 27,888 MB（绝大部分内存转储） | 3.3.3.3 | 参考实现+冻结基线 | `battle_server.py`、`BATTLE_SERVER_PROTOCOL.md`、`GOLDEN-LOBBY-001.md` | 已复核（核心文件） |
| 离线服务端 | `OfflineServer` | 55 文件 / 0.3 MB | — | 参考实现 | — | 已登记 |
| 外部参考 | `IW4X` | 566 文件 / 52.4 MB | MW2 | 参考实现 | **无专用服务器源码**；`netchan_t` 与 CoD4x 1:1 | 已登记 |

---

## 5. 2697 配套资源（资源与脚本底座）

| 资产 | 路径 | 规模 | 分类 | 关联 | 不确定性 | 复核状态 |
|---|---|---|---|---|---|---|
| 运行时资源 | `...\server2697\runtime-assets` | 11,033 文件 / ~1.797 GB | 原始资源 | chinese FF、地图、UI、资源索引；本地资源底座 | 未逐文件解析 | 文档转述 |
| GSC 脚本 | `...\server2697\scripts` | 1,341 文件 / ~19.15 MB | 原始资源 | 地图/模式/武器/挑战脚本 | 已判定**不含协议逻辑**（15/1341 相关且为游戏逻辑） | 文档转述 |
| 脚本 overlay | `...\server2697\script-overlay2697` | 99 文件 / ~1.73 MB | 原始资源 | 修正/覆盖脚本 | 仅局部 | 文档转述 |
| 附件/武器表 | `...\attachment-registry2697.json/.txt` | 101,415 / 72,864 B | 原始资源 | 武器/附件索引 | 非 MVP 必需 | 文档转述 |
| 运行时资源(客户端) | `COD OL\...`（安装树） | 2,973 文件 / 25 GB 级 | 原始资源 | 客户端资源 | — | 已登记 |

---

## 6. 分析产物目录（既有逆向档案，禁止重复生成同内容报告）

| 目录/文件 | 规模 | 内容 | 本审计的引用 |
|---|---|---|---|
| `14_SERVER_KNOWLEDGE_ATLAS_001` | 27 文件 | 服务端全景档案 + 跨项目交叉验证（拓扑/生命周期/传输/序列化/协议/gamestate/实体 + 22 号开工准入） | 证据集成总档案（主要来源） |
| `11_CUSTOM_SERVER_FEASIBILITY_001` | 8 文件 | 2697 自建服务器可行性（资产/复用/路线A/路线B/MVP/里程碑/结论） | 路线与 MVP 架构 |
| `12_CODEC_MVP_001` | 6 文件 | 离线 codec 规格与测试向量 | 编解码基线 |
| `CODOL_2697_SERVER_STATIC_ANALYSIS_20261011` | 231 文件 | 2697 样本身份/目录差异/二进制差异/协议路径/客户端兼容/下一步 | 2697 服务端静态事实 |
| `COMBAT_SERVER_*`（根目录 60+ 文件） | ~0.9 MB | 战斗服务器恢复基准/调用链/阻塞/证据索引/历史发现/P0 引擎绑定/v0.1各 NEXT 报告 | 战斗链主证据 |
| `EARLY_SERVER_ANALYSIS` | 4,006 文件 / 219 MB | OLD/1113 服务端 00–16 阶段分析 | 旧版源码/协议参考 |
| `E06…E27`（15+ 目录） | 各 30–100 文件 | demonware/keyflow/configstring/tvm0/socket/session 等定向取证 | 2697 与客户端消费链证据 |
| `DEV-BOOKING` / `DEV-PUBLISHER-RESTORE` / `DEV-REPRO` | 30,000+ 文件 | booking、发布/恢复、复现 | 大厅→战斗 booking 证据 |
| `_combat_baseline` / `_combat_next001` / `_combat_next011*` | ~200 文件 | 宿主身份、匹配客户端、RVA/派发探针 | 引擎绑定的只读测量 |
| `REF_LOBBY_KIT_CAP009` / `GOLDEN-LOBBY-001` | 143 / 22 冻结文件 | 抓包、内存 GPU、冻结复现 | 唯一实机进大厅证据 |
| `_t1_*_evidence` / `_t2_*_evidence` / `T1_*` / `T2_*` | ~2,000 文件 | 旧版传输生命周期、错误态、回归证据 | 工程回归基线 |

---

## 7. 重复研究 / 过时结论 / 冲突登记

| 项 | 内容 | 状态 |
|---|---|---|
| CONFLICT-01 | `COOKIE_ECHO` 长度 189（源码）vs 219（C#/抓包） | CONFLICTED（局部对 1.1.1.13/22011 已裁决；C-2697 未定） |
| CONFLICT-02 | 协议号：内部 codec 187 vs 出站 protocol 1 | CONFLICTED |
| CONFLICT-03 | 「CODOL 使用 DTLS」——实为静态链接 OpenSSL 表 | 旧结论**已降级**（CONFLICTED/REFUTED） |
| CONFLICT-04 | `COOKIE_ACK`/`INIT_ACK` 结构表述（源码 vs C# 命名不同） | 双留 |
| CONFLICT-05 | 3.3.3.3 vs 2.6.9.7 客户端混淆风险 | 已隔离 |
| CONFLICT-06 | IW4x 双克隆 HEAD 不同 | CONFLICTED / BLOCKED（差异清单未建） |
| CONFLICT-07 | 「IW4x 有专用服务器源码」 | **REFUTED** |
| CONFLICT-08 | OLD 源码↔二进制逐函数对应 | BLOCKED（无 PDB/MAP） |
| CONFLICT-09 | 「2697 含源码」——仅有源文件名串 | **REFUTED**（无 2697 源码树） |
| CONFLICT-10 | 大厅服务端身份：自研 `CODOLServer` vs 第三方 `REF_LOBBY_KIT` | 已澄清为两个不同服务端 |
| 过时结论 | 协议端口早期结论（IIPS=8000/游戏=8801）、「无静态 IAT」、「out.exe 是项目级根依赖」 | **作废/降级**，见 `COMBAT_SERVER_EVIDENCE_INDEX.md` CS-X11..X13、CS-A11 |
| 重复研究 | 根目录存在多份同主题报告（`T1_*`、`T2_*`、`COMBAT_*NEXT_*`、`RESTORE_*`、`ICH*_observer`） | 已整合；本审计**不重复生成同内容报告**，仅建立索引与结论映射 |
| 文档漂移 | `codol_server_function_matrix.json`（8-16，指向 3.3.3.3）落后于 10-09 源码；`game_server_coverage.md`、`game_server.md` 旧 | 评估失真风险，见 `05` |

---

## 8. 不能访问 / 未验证的资产（明确标注）

| 项 | 原因 | 影响 |
|---|---|---|
| **C-2697 运行时解包 dump** | 不存在（ACE ~10s 后内存读取失效；Frida 附加失败×2） | 恢复镜像≡运行时映射**无法证明**；客户端侧结论上限 |
| `.data` 初始化来源（`.rimp` 指针修复） | 静态仅解析出结构，完整重放规则未定 | 客户端 vtable/xref 缺失 |
| `.tvm0`（RVA 0xD958000） | 未解码；原始字节 E8/E9 扫描可靠性 0.0% | 客户端分派搜索空间不完整 |
| 最后 `.tp3`（VA 0xDC11000 起，VSize≈52.5 MB） | 未归还 | `.rdata` 部分缺失 |
| 2697 战斗通道抓包 | 未采集（需真实互通/授权） | 无法做字节级双向闭合 |
| 2697 完整黄金向量 | 不存在 | 无法独立解码交叉测试 |
| 2697 `runtime-assets`（1.7 GB） | 未逐文件解析 | 资源/索引层未核验 |
| `out.exe`（去壳，`044c396c…257f9`） | 全盘有界扫描 0 命中 | ol-mod L1 硬阻塞 B1 |

---

## 9. 盘点结论

1. 研究对象完整登记：**3 个客户端版本 + 3 个服务端构建 + 6 类源码/仓库 + 2697 配套资源**，全部有哈希或目录级统计。
2. OL-mod 源码与 `DedicatedControl`/booking 源码**现已在本工作区**，取代了 2026-10-07「ol-mod 源码 BLOCKED」的旧结论。
3. 2697 与 2.6.9.7 的正确研究对象齐备；**唯一结构性缺口是客户端运行时镜像**与**2697 战斗通道字节样本**。
4. 冲突 03/07/09 属于已执行的**反例研究**（推翻了先前的正向判断），保留登记。
5. 除上述缺口外，其余资产均可作为后续实现的可追溯依据；不存在需要重复生成同内容静态报告的情形。
