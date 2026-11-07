# CODOL A-S 能力矩阵
| 域 | 已证实 | 仅离线/代码 | 仅报告/历史 | 缺失 |
|---|---|---|---|---|
| A 身份/构建 | 目标 EXE/DLL 哈希、PE 版本、TCLS/IIPS 版本 | v0.1/047 构建记录 | 3.3.3.3 旧标签、2697 派生记录 | 去壳 EXE、完整运行时镜像 |
| B 启动/生命周期 | 客户端、IIPS、TCLS、Auth/Lobby 文件存在 | C# ServerHost 阶段机 | CODOLServer 历史启动日志 | 3.19 同 PID 端到端启动链 |
| C 帧/线程 | 代码有 tick 常量与控制面插件 | C# 主循环、ol-mod 帧钩子 | 20Hz/128Hz 历史资料 | 目标服帧率、线程所有权、关闭竞争 |
| D 网络基础 | UDP、NAT、socket 证据 | v0.1 UDP、ol-mod Winsock、旧 C net | 端口/会话报告 | 目标战斗端口真实会话 |
| E 连接状态 | 目标 OOB 候选 | 047 状态机、旧 C 码 | C# 日志 | 目标握手/Active 闭环 |
| F 消息/传输 | 目标类型分派器与 OOB 引用 | netchan/可靠命令/分片 | 2697 writer、旧抓包 | 目标 opcode、ACK、帧边界 |
| G 地图/资产 | IIPS 清单、13 个 .ff 容器 | 旧 C fastfile、ol-mod 资产代码 | runtime-assets 统计 | 目标 zone 依赖图、挂载表 |
| H 世界/碰撞 | 旧 C/ol-mod 有 clip/trace | 旧 C 碰撞测试与 fixture | 地形/模型报告 | 3.19 clipMap/MapEnts/physics 与 trace |
| I 移动/pmove | 目标字段/函数候选未闭；ol-mod 双端 1 秒前进窗口未重触发重传 | 旧 C pmove、ol-mod NativePmove、C# 水平积分 | 移动实验记录 | AABB、地面吸附、台阶/斜坡、完整姿态/障碍、目标 pmove |
| J 实体/状态 | 目标类型表候选 | 旧 C 244 玩家字段/22 实体表、ol-mod 原生状态 | 2697 写入链 | 目标位宽、实体生命周期、客户端读取 |
| K 快照/复制 | ol-mod 双端 snapshots=2972 历史窗口；C# 离线编码 | 旧 C section codec、ol-mod snapshot | 2697 writer、历史 delta | 3.19 帧边界、baseline、消费链、长时丢包 |
| L 游戏逻辑 | ol-mod SD 分队/目标状态历史证据；旧 C/ol-mod 有规则骨架 | 伤害/武器/复活/记分测试 | 历史对局声明 | 目标可玩伤害、死亡、plant/defuse、回合、HUD、双客户端 |
| M 脚本/规则 | GSC 文件存在 | 旧 C script、ol-mod Lua/GSC | 2697 脚本 1,341 文件 | 目标 VM/builtin、地图脚本执行 |
| N 配置/管理 | 客户端配置、C# 命令、ol-mod control | RCON/管理测试 | 运维日志 | 目标 cvar 来源、权限与审计 |
| O 安全/认证 | TLS/ECDH/AES/HMAC 组件与历史证据 | 047 拒绝未知握手 | Auth/证书/ACE 历史 | 目标 ticket、密钥生命周期、重放负测试 |
| P 插件/平台 | ol-mod/WeGame/TGuard/TenProxy | Localnet/平台包装测试 | 平台启动报告 | 3.19 插件边界与服务器平台分支 |
| Q 外围服务 | TCLS/IIPS/Auth/Lobby/booking 文件 | REF_LOBBY_KIT/Auth/Lobby Python | 端点与会话报告 | 目标端点下发、booking、同 PID 全链 |
| R 构建/验证 | v0.1/047 可构建；ol-mod 有双客户端历史窗口 | 153 个旧 C 测试、ol-mod 测试 | 122/31/更多断言 | 目标客户端同 PID 真实连接、长时与可玩对局 |
| S 缺口/版本 | 文件总账、冲突表 | 历史报告 | 2697/3.3.3.3 材料 | 目标运行时、抓包、地图、C 服源码 |
