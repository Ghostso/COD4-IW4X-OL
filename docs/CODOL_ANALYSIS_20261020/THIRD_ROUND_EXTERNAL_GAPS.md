# 第三轮最终缺口与外部逆向需求

日期：2026-10-21（Asia/Shanghai）

状态：第三轮可以继续在现有材料范围内做交叉验证；本清单中的缺口限制的是“完整还原”和“可玩性闭环”，不是分析启动。

## 1. 3.19 目标证据缺口

| ID | 缺口 | 现有最接近证据 | 获取方式 | 解除什么 |
|---|---|---|---|---|
| T3-01 | 完整或覆盖读包路径的加载镜像 | 局部静态恢复、ACE 后零页读取 | 在允许条件下合并分段映射，记录 VA/RVA、页范围和哈希 | 3.19 recv/opcode/parser 链 |
| T3-02 | 同一 PID 的真实战斗会话 | Auth/Lobby 与诊断 TCP，无战斗 UDP | 先启动抓包，再单次启动，进入实际对局并保留双向流 | 线协议 framing/ACK |
| T3-03 | gamestate/configstrings 完整帧 | 历史小样本、写侧候选 | 同会话抓包 + consumer trace | 客户端解析字段 |
| T3-04 | 连续 snapshot 与 baseline | 部分 writer/reader 候选 | 至少两帧 snapshot、ACK 和状态对应 | delta 和历史提交 |
| T3-05 | consumer trace | recv 候选链，未有 payload 消费 | 记录 buffer、长度、opcode、parser、state delta | 服务端 writer 约束 |
| T3-06 | 目标 FF layer-2 与地图资产 | 只有 IWffs100 block-0 | 恢复 Zone 目录，导出 CLIPMAP_MP、MAP_ENTS、ComWorld、physics | 世界加载、出生、碰撞 |
| T3-07 | Pmove/碰撞目标常量 | 通用移动向量 | mins/maxs、眼高、重力、台阶、摩擦、加速度、ground trace | 无落地/穿墙修复 |
| T3-08 | 目标规则与模式证据 | 旧实现和 2697 参考 | spawn、weapon、damage、death、respawn、score、round 目标链 | 可玩对局 |
| T3-09 | 目标 C 服源码或可复现构建 | 用户所述 C 服尚未定位完整源码 | 提供路径、构建、hash 和版本 | 直接重构起点 |
| T3-10 | booking 到战斗端点消费链 | mmbook accepted 可见，无 mmstart/battle UDP | 同 PID 抓取 Lobby 响应、客户端消费、端点拨号 | 进入战斗 |

## 2. 同族参考缺口

### 2.6.9.7 / 2697

- 原始 server2697 包与最终目录；
- 新旧服务端与客户端注册导出的成对关系；
- 2.6.9.7 战斗真实抓包；
- 新通道对 3.19 的适用性差异。

### 3.3.3.3 ol-mod

- 目标构建与当前工作树差异；
- 目标版本原生进程与插件加载记录；
- 3.3.3.3 → 3.19 的字段、资产和控制面差异；
- 只用于模块边界和算法对照，不填 3.19 wire。

## 3. 外部服务器参考缺口

### CoD4x

- 32 位工具链、构建产物、构建日志；
- 合法 CoD4 资产；
- netchan、snapshot、trace、pmove 确定性 fixture；
- 插件 ABI 和 RCON 运行证据。

### IW4X

- 16 个子模块锁定；
- 精确 MW2 宿主 SHA；
- iw4x.dll 构建和 dedicated 运行；
- host 结构/地址验证；
- 资产 parser 和协议 fixture。

## 4. 缺口不会解除的错误做法

1. 用 2697 writer 直接生成 3.19 帧。
2. 用 3.3.3.3 的版本字段覆盖目标。
3. 用 CoD4x/IW4X 的 netchan 解释 CODOL bdDTLS/记录层。
4. 用 block-0 FF 宣布 layer-2 资产可用。
5. 用端口监听、进程存活或离线测试宣布端到端可玩。

## 5. 取得后的优先级

1. 3.19 目标镜像和同一 PID 战斗抓包。
2. consumer trace 与 gamestate/snapshot 帧。
3. 目标地图资产与碰撞。
4. 2697 原始包与版本差异。
5. 3.3.3.3 架构差距。
6. CoD4x/IW4X 构建和算法 fixture。

这些缺口若长期不补，第三轮的正式结论只能是：现有材料范围内的审计已完成，完整还原和可玩性仍未证明。
