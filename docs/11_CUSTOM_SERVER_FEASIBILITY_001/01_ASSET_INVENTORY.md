# 01 — 现有资产与分析成果清单

> 目标：为 2.6.9.7（2697）客户端评估自建服务器。仅静态调查，未启动客户端/服务端，未编译、注入、补丁或安装工具。
> 结论等级：`VERIFIED`、`STATIC-INFERENCE`、`NOT-OBSERVED`、`BLOCKED`。

## 1. 核心样本

| 资产 | 路径 | 大小/SHA-256 | 源码 | 已分析 | 复用价值 | 不确定性 |
|---|---|---|---|---|---|---|
| 2.6.9.7 客户端 | `D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe` | 9,964,656 / `353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1` | 无 | A–G | 最终兼容目标 | 保护/恢复镜像等价性 BLOCKED |
| 客户端 manifest | `D:\BaiduNetdiskDownload\CODOL_2697_Launcher\manifest.json` | 1,558 / `34017bf787800678a66d277520869873c3352c713da883e9dce2d348f669da00` | 无 | A–E | 版本与组件哈希基线 | 无 |
| 2697 原生服务端 | `D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe` | 7,295,919 / `80816711946a5392abab81a625a516f24fb4d649e9b8008fc5a4e506be750ea1` | 无 | A–G | 2697 协议事实源、原生路线验证对象 | 注册/资源/初始化门控与来源未完全闭合 |
| 旧版服务端主 EXE | `D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\13_NATIVE_TAP_BUILD_001\experiment_copy\bin\codol_dedrun.exe` | 8,469,493 / `28366ae992310bfe41d3c8975ec8dbc36e4de202ce438c1266e1a09e335dd98a` | 有（CoD4x fork） | EARLY_SERVER 00–16 | 网络/引擎/旧协议底座 | 目标是 1.1.1.13，不直接等于 2697 |
| 旧版 `codol_dedrun_next.exe` | 同目录 | 8,469,493 / 与上项逐字节相同 | 有（重复构建产物） | 已确认重复 | 低；使用主 EXE 即可 | 无 |
| 独立 C# 战斗服 | `D:\BaiduNetdiskDownload\使命召唤OL\CODOL-Combat-Server-v0.1` | 源码 22 文件；构建产物 `CODOLCombatServer.exe` 126,464 / `3fa92e97453f298a27af5cf9ec0bf235100f9b18f2962723ea43a5a7297bb378` | 有 | README、源码、证据日志 | 最快可构建的实验底座 | 真实客户端连接 NOT-OBSERVED |
| ol-mod 全源码服务端 | `D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal` | 源码树完整，含 game_server/backend | 有 | 当前 handoff、模块文档、源码 | 最完整的 CODOL 原生服务器参考 | 目标是 3.3.3.3 QA，不直接等于 2697 |
| Python 研究服务端 | `D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer` | `codol_server.py` 27,374；lobby_server 多文件 | 有 | A–G/历史报告 | lobby、认证、IIPS/TCLS、抓包洞察 | 多版本/实验性，接口需核对 |

## 2. 旧源码树

| 资产 | 路径 | 内容 | 结论 |
|---|---|---|---|
| CoD4x fork 源码 | `EARLY_SERVER_ANALYSIS\13_NATIVE_TAP_BUILD_001\experiment_copy\src` | `netchan.c`、`msg.c`、`sv_main.c`、`sv_client.c`、`sv_snapshot.c`、`codol/net`、`codol/snapshot` | REUSE/ADAPT；目标 1.1.1.13（VERIFIED） |
| CoDOL net 层 | `src/codol/net` | `codol_handshake.c`、`codol_crypto.c`、`codol_ecdh.c`、`codol_netchan.c`、`codol_wire.c`、`codol_connect.c` 等 | 有逐字节参考实现；与 2697 代码/版本需重新验证（ADAPT/BLOCKED） |
| CoDOL snapshot 层 | `src/codol/snapshot` | configstrings、client/player/entity、delta、events、frame builder、snapshot 等 76 文件 | 逻辑丰富；旧报告指出 gamestate/configstrings/snapshot 序列化未收敛（BLOCKED） |
| ol-mod game_server | `ol-mod-olfinal/src/game_server/server_mp` | gamestate、snapshot、network、player/pmove、weapon、entity、collision 等大量源码 | 高价值参考/适配源；目标 3.3.3.3 QA（VERIFIED） |
| ol-mod backend | `ol-mod-olfinal/src/backend/Demonware` | Auth、ByteBuffer、booking、控制面 | 大厅/认证参考；版本需改（ADAPT） |

## 3. 2697 服务端配套资源

| 资产 | 路径 | 规模/内容 | 复用价值 | 不确定点 |
|---|---|---|---|---|
| 运行时资源 | `server2697\runtime-assets` | 11,033 文件，约 1.797 GB；chinese FF、地图、UI、资源索引 | 可直接作为本地资源底座 | 初始化需服务端引擎理解和资源索引一致 |
| GSC 脚本 | `server2697\scripts` | 1,341 文件，约 19.15 MB；地图/模式/武器/挑战脚本 | 基础模式与地图逻辑来源 | 2697 服务端脚本编译器/加载器依赖待验证 |
| 脚本 overlay | `server2697\script-overlay2697` | 99 文件，约 1.73 MB | 修正/覆盖脚本 | 仅覆盖局部，不能替代完整脚本链 |
| 注册 evidence | `server2697\evidence\client-registration2697.txt` | 首行 `codol2697-registration ...` | 2697 合法注册校验输入格式实例 | 是否是运行时输入已 VERIFIED；具体门控放行需按 E1 条件 |
| 附件/武器证据 | `attachment-registry2697.json/.txt` | 101,415 / 72,864 | 武器/附件索引来源 | 完整武器子系统非 MVP 必需 |
| loopback 审计 | `client-loopback-guard.json`、`loopback-executable-audit.json` | 审计/哈希 | 本地隔离链路参考 | 自定义桥接，不是原版客户端协议 |

## 4. 协议分析成果

| 报告 | 关键结论 | 等级 |
|---|---|---|
| 01–06 | 样本身份、目录/二进制差异、2697 协议路径、客户端兼容初判 | 已验证/推断混合 |
| E1 Gamestate | `0xA3DAB` 双门控；`ReadRegistration 0xA3EA0`；失败直接返回；新通道有真实调用者 | VERIFIED |
| E2 Snapshot/EOF | 内层 `0xA4CAF` 的 `0x06`；外层 `0x87104` 选择 `0x05/0x06`；客户端 EOF 未确认 | 服务端 VERIFIED，客户端 BLOCKED |
| E3 Reliable | `0x02 + long + short + data`；`0x01` 回退；archives/env/encoder 控制 | 服务端 VERIFIED |
| E4–F | 客户端 `0xA2E50` 字段形状匹配，但 opcode 0x02→函数分派未找到 | STATIC-INFERENCE/BLOCKED |
| G1 | 恢复镜像缺少原始最后 `.tp3`；`.rimp` 是指针修复伪影 | VERIFIED 结构，运行等价性 BLOCKED |
| G2 | 已排除 libcurl/SOCKS、QoS；平台边界为 TenProxy/IIPS；无到 0xA2E50 控制流 | 负面范围 VERIFIED，原版存在性 BLOCKED |

## 5. 构建与工具链现状

| 工具 | 状态 | 证据 |
|---|---|---|
| C# `csc.exe` | 可用：`C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe` | 本机路径检查 |
| `xmake` | 未找到 | `where xmake` / 默认路径不存在 |
| `nasm`、`make`、`gcc`、`cl`、`msbuild` | 未找到 | 命令检查 |
| vcpkg 默认路径 | 未找到 | `E:\Source\Repos\Main\vcpkg` 不存在 |

结论：
- **C# 独立战斗服可直接进入离线构建/测试流程（NOT-RUN）**。
- **旧 CoD4x/ol-mod 源码目前不能在本机按 README 直接重建**，需要既有工具链或另行批准的环境；本任务不安装工具。

## 6. 资产级结论

- 已有足够材料开展自建服务器可行性/接口设计，不需继续泛化扫描。
- 直接可用于原型的是 C# 战斗服与本项目 Python lobby/研究工具。
- 旧 CoD4x/ol-mod 是**架构和算法参考**，不是 2.6.9.7 的现成实现。
- 2697 原生 EXE 是协议事实源，但没有源码且初始化门控未完全闭合。
