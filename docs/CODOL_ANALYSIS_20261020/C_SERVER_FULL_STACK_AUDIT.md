# CODOL 服务器系统全栈审计

日期：2026-10-21（Asia/Shanghai）

范围：CODOL 服务器系统本身，不限于战斗进程或某一份 C# 原型。包括 3.19.26.22 / Build 1649370 客户端提供的协议与行为证据、1.1.1.13 旧 C 服、3.3.3.3 ol-mod、2.6.9.7 / 2697 原生服务端、v0.1 与 047 两套独立实现、启动控制面、Auth/Lobby/IIPS/TCLS/booking、管理面、资产生产链、逆向产物、构建与运行证据。本文件不引用 CoD4x 或 IW4X 的结论；两者将在独立审计完成后进入交叉验证。

## 0. 审计状态与结论先行

状态：**进行中，未完成。**

当前可见的服务器不是一套代码。需要分别审计以下对象，禁止用一个对象的完成度代表另一个：

| 对象 | 路径 | 形态 | 对 3.19 的适用性 |
|---|---|---|---|
| C# 实验服 v0.1 | `CODOL-Combat-Server-v0.1` | 25 个有效 `.cs`，9,702 行；另有构建、日志、备份 | 协议与线格式实验参考，未证明真实 3.19 客户端互通 |
| C# 基础实现 047 | `CODOL-BATTLE-SERVER-IMPLEMENTATION-FOUNDATION-047` | 独立 .NET 8 工程，27 个有效 `.cs`，31 项离线测试 | 强制协议隔离与生命周期骨架；最终 CODOL 解码器显式未实现 |
| 旧 C 服 | `EARLY_SERVER_ANALYSIS/13_NATIVE_TAP_BUILD_001/experiment_copy` | CoD4x fork C/C++ 源码 + EXE | 1.1.1.13 历史参考，不能直接当 3.19 |
| ol-mod 游戏服 | `_e1_regression/ol-mod-olfinal/src/game_server` | 82 `.cpp` + 91 `.hpp`，含专用服补丁、网络、物理、快照和模式 | 3.3.3.3 QA，版本不对口 |
| ol-mod 控制面 | `_e1_regression/ol-mod-olfinal/src/{backend,shared,client_bridge,localnetworking,platformwrapper}` | 房间、booking、Dedicated 控制、后端、LocalNet 钩子和平台适配 | 3.3.3.3 控制面参考，不能替 3.19 线格式 |
| 2697 原生服 | `codol_dedrun.exe`（当前原路径在本机不可见） | PE32 无源码 | 2.6.9.7 协议事实源，需逆向 |
| 3.19 客户端 | `COD OL/codoMP_client_shipRetail.exe` 等 | PE32 加壳客户端 | 最终目标行为，消费链不完整 |
| Python 控制面 | `REF_LOBBY_KIT` | Auth/Lobby/battle、抓包、内存扫描与运行产物 | 3.3.3.3 真实握手与启动链证据，不等于 3.19 |
| 受保护黄金基线 | `CODOL_VERIFIED_GOLDEN_20261019` | 冻结控制面及运行产物 | 回归基线，不是线上服务器语义 |

已确认的最高层事实：

1. 当前 C# 服能构建、能跑离线自测、能维护会话与运动快照；但从未有真实 3.19 客户端连接。
2. 当前 C# 服的移动链只解决“输入 -> 水平位移 -> 快照字段”，没有地图 BSP/clip 几何与 trace，因此穿墙和无落地是结构缺失。
3. 3.19 客户端与 2697 服务端不是同一构建。2697 证据只能作为同类协议事实源，不能直接填 3.19 字段。
4. 2697 发送侧有已经定位的 gamestate/configstring/snapshot/reliable command 写入链，但客户端消费侧仍有多个关键分派未闭合。
5. 现有材料对“全服务器”的覆盖不足：网络与部分快照较深，地图、世界、游戏规则、资源、模式与异常生命周期明显更粗。

### 0.1 A-S 覆盖状态

| 域 | 状态 | 现有证据与边界 |
|---|---|---|
| A 身份与构建 | 部分完成 | C#、旧 C、ol-mod、2697、3.19 客户端均已识别；3.19 的唯一完整运行镜像缺失 |
| B 入口与生命周期 | 部分完成 | C# ServerHost 有阶段机；ol-mod 有引擎绑定门禁；2697 仅有二进制入口 |
| C 帧循环与线程 | 部分完成 | C# 主循环存在；ol-mod 有双客户端历史窗口与 active=2 记录，缺长时稳定性与目标版本帧率 |
| D 网络基础层 | 部分完成 | 28960/UDP、NAT/INIT/COOKIE/DATA 已知；3.19 端点采纳未闭合 |
| E 连接状态机 | 部分完成 | C# 有 Free/Cookie/Transport/Connected/Active；真实客户端未连上 |
| F 消息与传输 | 部分完成 | CODOL netchan 常量、分片、XOR、可靠命令格式已定位；ACK/重传与客户端分派未闭合 |
| G 地图与资产 | 部分完成 | FF 文件存在；CLIPMAP_MP/MAP_ENTS/COMWORLD 未解出 |
| H 世界与碰撞 | 缺失 | 当前 C# 没有真实 BSP/clip/trace；ol-mod 有 3.3.3.3 碰撞代码但不能直接套 |
| I 移动与控制 | 部分完成 | C# 仅水平积分；ol-mod 有 NativePmove 与双端 1 秒前进窗口；2697 state layout/pmove 未验证 |
| J 实体与状态 | 部分完成 | C# 有最小 PlayerState；2697 写入字段局部已知；完整字段范围缺失 |
| K 快照与复制 | 部分完成 | C# 有 124B/72B 位级快照；ol-mod 有双端 snapshots=2972 历史窗口；2697 writer 与目标消费链未闭 |
| L 游戏逻辑 | 缺失 | 当前没有可玩的伤害、命中、死亡、复活、计分、回合与结果闭环 |
| M 脚本与规则 | 部分完成 | 2697 scripts 1,341 文件；加载器与执行语义未闭合 |
| N 配置与管理面 | 部分完成 | C# 配置/命令有；ol-mod DedicatedControl 有；RCON/管理面未全审 |
| O 认证与安全 | 部分完成 | C# 握手与加密原语；3.19/2697 记录层原语仍有冲突 |
| P 插件与平台 | 部分完成 | ol-mod 插件边界、DedicatedControl、REF_LOBBY_KIT 分属不同层 |
| Q 外部服务 | 部分完成 | TCLS/IIPS/Auth/Lobby/booking 已知；对局端点下发来源 conflicted |
| R 构建与验证 | 部分完成 | C# 可构建自测；旧 C/ol-mod 有大量离线与历史实机证据；缺同构建长时和目标端到端 |
| S 缺口与版本适用性 | 进行中 | 缺口清单见后；待逆向统一补齐 |

## 0.2 Gate A 架构边界

ol-mod 的 3.3.3.3 QA 客户端审计得到负向 Gate A：客户端保留 `CL_CheckForResend`、OOB 响应消费和 gamestate 解析等完整消费侧，但没有找到 `SV_Init`、`SV_Frame`、`SV_SpawnServer`、server gamestate/snapshot builder 或 server GSC 执行簇的等价可唤醒实现。

因此新服务器必须拥有真实权威状态；不能把客户端注入、伪造 matchmaking 成功或合成包当成战斗服务器。控制面可以独立恢复，gameplay data plane 必须另建。

这条 Gate A 结论只适用于被审计的 QA 客户端；证据仍不足以推进 3.19 目标客户端进入 battle。

## 1. 当前 C# 战斗服调用链

入口与生命周期：

```text
Program.Main
  -> ServerConfig.Load
  -> ServerHost.Initialize
       -> 绑定 UDP
       -> 初始化 GameWorld
       -> 初始化 ClientLogic
  -> ServerHost.Run
       -> TryReceive(最多 256 包)
       -> ClientLogic.HandlePacket
       -> GameWorld.Frame(dt)
       -> ClientLogic.Update()
       -> Thread.Sleep(1)
```

当前可见能力：

- UDP transport、配置解析、日志；
- 会话状态机；
- NAT / INIT / COOKIE / DATA 的记录层实现；
- 2697 netchan 与 legacy 协议分支；
- usercmd 读取、玩家水平移动；
- gamestate/configstring/snapshot 编码；
- session descriptor 导出；
- 离线 selftest。

当前实现边界：

- 没有真实客户端连接；README 明确“收包=0”；
- 没有 BSP/Clip 真实碰撞；
- 没有武器、伤害、命中、死亡、复活；
- 没有地图资源加载器；
- 没有完整游戏模式与结算；
- 2697 实时客户端消费者未闭合。

## 2. 网络与协议栈

已知分层：

```text
OOB
  NAT 0x0D / INIT 0x01 / INIT_ACK 0x02
  COOKIE_ECHO 0x03 / COOKIE_ACK 0x04
DATA record
  0x06 0x02 tag counter MAC8 length cipher
CODOL netchan
  sequence / ACK / fragment / XOR
messages
  clc 3-bit / svc
application
  gamestate / configstring / snapshot / reliable command
```

版本边界：

- 3.3.3.3 抓包有真实握手，不能自动升格为 3.19 已证；
- 2697 服务端写入 0x02 可靠命令、0x03 gamestate、0x04 configstring、0x06 终止，客户端读取仍未证；
- 3.19 客户端没有任何真实战斗通道抓包；
- 28960 是候选端口，不是血缘证据。

## 3. 地图与世界

当前 C# 服：

- `ServerHost.FindMapAssetDir` 只登记目录，不解析地图；
- `GameWorld` 明确注释 BSP/Clip 与弹道/伤害未实现；
- 竖直模拟默认关闭；
- 地面固定为 spawn Z；
- OnGround 与 groundEntityNum 仅为状态字段。

必须补的地图资产：

- `ASSET_TYPE_CLIPMAP_MP`
- `ASSET_TYPE_MAP_ENTS`
- `ASSET_TYPE_COMWORLD`
- 物理/clip 关联
- 玩家 AABB/胶囊、trace mask、step height、slope limits
- 出生实体与模式/队伍过滤

## 4. 实体、快照与游戏逻辑

目前已知：

- C# `ClientSession` 保存会话、身份、握手、netchan、输入基线、PlayerState；
- C# `MotionSnapshot` 有位级 writer 和 index-skip；
- 2697 snapshot 写入链可定位到 `_CODOL2697_WriteSnapshot` / `_WriteSnapshotReached`；
- 3.3.3.3 的 ol-mod 有 entity、snapshot、weapon、damage、spawn、scoreboard 等源码，但版本不对口。

尚缺：

- 2697 snapshot 帧边界与 delta 基准；
- 3.19 客户端 snapshot 解码；
- 服务端权威字段的完整结构；
- 武器/伤害/死亡/复活/计分/回合的字段与状态机。

## 5. 各服务器对象复用判定

| 模块 | C# 实验服 | 旧 1.1.1.13 C | ol-mod 3.3.3.3 | 2697 二进制 |
|---|---|---|---|---|
| UDP/session | 可运行原型 | 历史参考 | 完整插件参考 | 服务端事实源 |
| 握手/密码 | 有实现 | 源码参考 | 版本不对口 | 需要反汇编 |
| netchan | legacy/2697 分支 | 旧实现 | 有宿主绑定 | 常量级证据 |
| 地图/clip | 缺失 | 有旧实现 | 有 3.3.3.3 实现 | 需要逆向 |
| pmove | 仅水平积分 | 旧实现 | NativePmove | 需要逆向 |
| snapshot | 位级原型 | 旧实现 | 3.3.3.3 实现 | 写入链已定位 |
| game logic | 缺失 | 旧实现 | 较大参考 | 需要逆向 |
| 资产 | 仅登记 | 旧资源 | 3.3.3.3 | runtime-assets |
| 验证 | 离线自测 | 未构建 | 未实机 | 未运行 |

判定纪律：

- 可借用的是工程分层、状态机、数据流与测试方法；
- 不能把旧版本字段、opcode、资源格式直接写成 3.19 已确认；
- 不能把“服务端编码成功”写成“客户端能消费”。

### 5.1 C# 现有测试的真实覆盖面

现有 `--selftest` 是一个高价值的离线协议回归基线，但必须单独说明其边界：

- 25 个 `.cs` 文件共 9,702 行；代码与自测都集中在一个可构建工程内。
- README 声明具备 `csc.exe` 可重复构建与 254 项断言；历史复核按 13 个分节统计。
- 测试主要覆盖：握手字节、记录层密码、netchan 分片、usercmd 读取、gamestate/configstring 编码、运动快照编码、会话描述符与配置。
- 测试不覆盖：真实客户端连接、真实地图 trace、静态实体/BSP、伤害/命中、死亡/复活、游戏模式回合、真实资源加载、客户端消费链。

因此：

```text
selftest 全绿 != 客户端兼容
字段往返一致 != 客户端能读
服务端能运行 != 可玩战斗
```

### 5.2 版本与证据优先级

对 3.19 重写服务器时，证据优先级应固定为：

1. 同版本 3.19 客户端真实字节与运行时行为；
2. 2697 原生服务端二进制中可复核的写链、字段与结构；
3. 3.3.3.3 ol-mod 的完整源码，仅作算法与工程结构参考；
4. 1.1.1.13 旧 C 源码，仅作历史与架构参考；
5. 当前 C# 实验服，仅作可运行原型与测试框架。

任何低优先级证据不得覆盖高优先级证据；版本差异必须显式记录。

## 6. 本地逆向材料分类

已读取并可作为高相关证据：

- `CODOL-BATTLE-SERVER-REVERSE-COVERAGE-001`：覆盖矩阵、架构、差距、路线；
- `CODOL_2697_SERVER_STATIC_ANALYSIS_20261011`：2697 身份、二进制差异、消息路径；
- `11_CUSTOM_SERVER_FEASIBILITY_001`：资产与模块复用矩阵；
- `14_SERVER_KNOWLEDGE_ATLAS_001`：网络、消息、实体、开放问题；
- `CODOL-BATTLE-SERVER-TRACE-034`：opcode/delta/configstring 追踪与离线测试；
- `E06`–`E27`：客户端 keyflow、TLS、socket、会话、配置串与 Demonware；
- `REF_LOBBY_KIT`：真实大厅和战斗握手证据，受保护只读；
- `FIRINGRANGE-BRINGUP-VERIFY-20261015`：靶场快照/客户端行为；
- `CODOL_NATIVE_BATTLE_CHAIN_20261019`：本地战斗链运行日志；
- `_rev_analysis`、`analysis_logs`、`backup_reverse_engineering`：历史逆向与日志。

当前仍是容器或未解资产：

- `_map_extract/mp_firingrange*.ff`：fastfile 容器，不是已解析 clipMap；
- `mp_firingrange_load.ff`、`mp_firingrange.ff`：需要 zone/fastfile 解析；
- `runtime-assets` 11,033 文件 / 1.797 GB：未逐文件分类；
- 2697 原服务端目录在当前本机路径不可见，只有报告与派生证据可复核。

与当前碰撞问题基本无关或低优先：

- marketplace/商店资产；
- TCLS/更新服务；
- 纯 UI 明文；
- 编译缓存、临时脚本与重复备份。

## 7. 缺口登记与获取方式

| # | 缺口 | 为什么缺 | 获取方式 | 解除什么 |
|---|---|---|---|---|
| 1 | 3.19 战斗通道真实字节 | 当前只有旧版抓包 | 受控运行与 socket 边界采集 | 握手、记录层、字段兼容 |
| 2 | CLIPMAP_MP 结构 | FF 未解析 | 解出 fastfile 资产并记录 plane/brush/node/leaf | 世界几何 |
| 3 | MAP_ENTS | FF 未解析 | 解出实体字符串与出生点 | 出生与模式 |
| 4 | COMWORLD/PHYSICS | 资产关联未知 | 解析资产类型与引用 | 世界加载 |
| 5 | 玩家碰撞尺寸 | 3.19 未闭合 | 客户端 pmove 反汇编/运行时 trace | AABB/trace |
| 6 | pmove 完整规则 | 当前仅水平积分 | 3.19 客户端 pmove 与地图实验 | 落地、台阶、贴墙 |
| 7 | snapshot 边界/delta | 2697 与 3.19 未对接 | 2697 writer + 真实帧对照 | 世界同步 |
| 8 | 实体/玩家字段 | 版本差异大 | 客户端解析与 2697 写链 | 状态兼容 |
| 9 | 武器/伤害/死亡/记分 | 当前未实现 | 2697/3.3.3.3 源码 + 3.19 运行时 | 可玩战斗 |
| 10 | booking/端点下发 | 地址来源冲突 | 冻洁大厅副本 + 抓包 | 能连上 |
| 11 | 客户端消费链 | .tvm0/.data/运行时缺失 | 运行时 dump / 解码/反汇编 | 协议闭环 |
| 12 | 全量逆向资产索引 | 目录多、重复多 | 逐文件哈希、版本与相关性分类 | 可重构证据 |

## 8. 当前重构优先级

P0：

1. 冻结并确认唯一目标客户端与战斗服源码。
2. 补齐 3.19 真实战斗抓包与当前地图资产。
3. 解出 CLIPMAP_MP/MAP_ENTS，完成离线 trace。
4. 明确客户端 opcode、gamestate、snapshot 消费链。

P1：

1. 用服务端真实地图 trace 替换硬编码出生/地面。
2. 完成 usercmd、pmove、权威位置与快照一致性。
3. 建最小玩家加入、出生、移动与离开生命周期。

P2：

1. 武器、伤害、死亡、复活、计分、模式。
2. 资源/脚本加载器与模式数据。
3. RCON、管理、日志与重连。

## 9. 独立结论

当前可重构底座不是“某一个完整服务器”，而是多个版本的证据集合：

- C# 服提供可运行的最小实验框架；
- 旧 1.1.1.13 C 源码提供历史算法与消息模型；
- ol-mod 提供最完整的 3.3.3.3 服务器参考；
- 2697 二进制约提供唯一可用的 2.6.9.7 协议事实；
- 3.19 客户端提供最终目标行为，但消费链尚未闭合。

不能把“能启动”“能写消息”“能出快照”“进程不退出”当作“可玩战斗”。在真实 3.19 客户端连接、世界几何 trace、实体/玩家字段和完整游戏循环闭合之前，本审计保持未完成。


## 0.3 第一轮证据链状态

| 链 | 已有 | 未闭合 |
|---|---|---|
| OOB/challenge | 目标 OOB 状态门、挑战/心跳命令、失败错误码 | 响应字面量是否用于比较、完整会话转换 |
| netchan | 目标存在 1154/分片候选与序列掩码 | netchanProcess、分片绑定、ACK/重传 |
| gamestate/configstring | 0x6D000 解析族与调用骨架 | opcode 入口、字段顺序/位宽、表容量 |
| snapshot/delta | 类型分派器与 314/136 表结构 | 帧边界、基线、实体增删、字段语义、EOF |
| 地图/碰撞 | 13 个 FF 容器、旧 C/ol-mod 碰撞代码 | 目标 clipMap/MapEnts/physics 导出、AABB/trace |
| 控制面 | ol-mod Auth/LSG/Profiles/房间/`mmbook` 历史实机链 | 3.19 同版本、真实外部 dedicated 匹配与持久化 |
| 外部战斗服 | 旧 C/ol-mod/C# 实现和部分双端历史窗口 | 3.19 真实客户端连接、地图加载、长时权威对局 |
