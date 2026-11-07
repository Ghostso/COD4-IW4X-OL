# CODOL 第一轮服务器对象与身份表

日期：2026-10-21

状态：第一轮证据盘点，行为审计未完成。

## 对象总表

| ID | 对象 | 路径 | 版本/身份 | 当前用途 | 主要缺口 |
|---|---|---|---|---|---|
| O1 | 目标客户端 EXE | `COD OL/codoMP_client_shipRetail.exe` | 7,841,344 B；SHA-256 `36997674...B537`；FileVersion `1649370`；目标实例标签 `3.19.26.22` | 协议与行为消费者 | EXE 运行时镜像、初始化/消费链 |
| O2 | 主引擎 DLL | `COD OL/codoMP_client_shipRetailBase.dll` | 60,327,992 B；SHA-256 `EF75220D...6A20` | 引擎、网络与状态解析 | 公开符号、完整消费链、运行时映射 |
| O3 | v0.1 C# 服 | `CODOL-Combat-Server-v0.1` | 25 个 `.cs`；独立原型 | UDP/协议/快照实验 | 真实客户端、世界、战斗 |
| O4 | 047 C# 服 | `CODOL-BATTLE-SERVER-IMPLEMENTATION-FOUNDATION-047` | .NET 8；27 个源文件；31 项离线测试 | 协议隔离、会话与诊断骨架 | 最终 CODOL 解码显式未实现 |
| O5 | 1.1.1.13 旧 C 服 | `EARLY_SERVER_ANALYSIS/13_NATIVE_TAP_BUILD_001/experiment_copy` | CoD4x fork；591 个 CoDOL 域源文件 | 历史算法、资产、快照与测试参考 | 非 3.19；真实对局未验收 |
| O6 | ol-mod 游戏服 | `_e1_regression/ol-mod-olfinal/src/game_server` | 3.3.3.3 QA；173 源文件/139,127 行 | 最完整同族源码参考 | 版本不对口；工作树有改动 |
| O7 | ol-mod 控制面 | `_e1_regression/ol-mod-olfinal/src/{backend,shared,client_bridge,localnetworking,platformwrapper}` | 3.3.3.3；约 4,800 行 | booking、Dedicated、房间与平台参考 | 不能补 3.19 线格式 |
| O8 | 2697 原生服 | 原目录当前不可见 | 2.6.9.7；227 份派生分析文件 | 同族服务端协议事实源 | 原始 EXE/资源/脚本缺位 |
| O9 | Python 控制面 | `REF_LOBBY_KIT` | Auth/Lobby/battle 与历史运行产物 | 启动与大堂握手证据 | 版本、重复转储、冻结基线冲突 |
| O10 | 黄金基线 | `CODOL_VERIFIED_GOLDEN_20261019` | 冻结回归输入 | 完整性回归 | 不是 3.19 服务器语义 |
| O11 | 地图容器 | `_map_extract` | 13 个 `.ff` 样本 | 资产解析入口 | 未解 clipMap/MapEnts/physics |
| O12 | 目标 IIPS 资产 | `COD OL/IIPS/IIPSDownload` | 974 条清单，构建 `1649370.2021-05-07` | 目标资产发布树 | 挂载关系与资产类型未解 |

## 版本裁定

目标 EXE 采用四类证据：PE FixedFileInfo `3.19.26.22`、StringFileInfo `1649370`、TCLS `mmog_data.xml`、IIPS 构建标签。旧材料把同一对象称为 3.3.3.3 QA 的结论，对当前实例标为 `REFUTED_FOR_THIS_INSTANCE`；3.3.3.3 仍是 ol-mod 的独立目标版本。

## 禁止结论

不能把文件版本当成完整运行时兼容证明；不能把 2697 写链当成 3.19 消费链；不能把 ol-mod 字段直接互换；不能把启动、离线自测或快照编码当成可玩对局。
