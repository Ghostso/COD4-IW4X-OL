# CODOL 服务器重构规格与完整审计清单

日期：2026-10-21（Asia/Shanghai）

状态：**审计规格，不是完成声明。**

目标版本：CODOL 3.19.26.22 / Build 1649370。

本文件回答“全服务器范围到底要查什么、查到什么程度才算够、缺什么、怎么取得”。它不把旧版本、另一套实现或推测字段当成 3.19 事实。

## 1. 审计对象

| ID | 对象 | 角色 | 当前证据边界 |
|---|---|---|---|
| O1 | 3.19 客户端 | 目标线协议与行为消费者 | 唯一最终判据；运行时消费链未闭合 |
| O2 | v0.1 C# 服 | 可运行协议/快照实验原型 | 从未有真实 3.19 客户端连接 |
| O3 | 047 C# 服 | 严格协议隔离与生命周期骨架 | 最终 CODOL 解码显式未实现 |
| O4 | 1.1.1.13 旧 C 服 | 同族历史实现与算法样本 | 非目标版本；真实对局未验收 |
| O5 | 3.3.3.3 ol-mod | 最完整同族服务器与控制面参考 | 非目标版本；工作树有未提交改动 |
| O6 | 2.6.9.7 / 2697 原生服 | 同族二进制协议事实源 | 原目录当前不可见，派生证据可复核 |
| O7 | REF_LOBBY_KIT | 启动、鉴权、大厅、靶场经验证据 | 冻结输入；既有基线不一致须保留 |
| O8 | GOLDEN_20261019 | 冻结回归基线 | 不是线上语义，不代表版本升级 |

服务器系统包括战斗进程、进程启动器、IIPS、Auth、Lobby、booking/matchmaking、TCLS/更新入口、管理面、资产生产、配置、部署、日志、监控与恢复。客户端只作为协议和行为证据来源。

## 2. 证据等级

| 等级 | 定义 | 可用于重构 |
|---|---|---|
| E0 | 同版本 3.19 真实客户端输入/输出或受控运行字节 | 直接依据 |
| E1 | 同版本 3.19 静态映像、反汇编、结构与可复核 xref | 直接依据，行为仍需验证 |
| E2 | 同族其他版本的服务端/客户端代码、二进制与抓包 | 结构与算法线索，须显式版本适配 |
| E3 | 本项目实现、离线测试、合成 fixture | 只证明该实现自身行为 |
| E4 | README、声明、注释、未验证报告 | 线索，不证明协议或可玩性 |
| E5 | 文件名、地址邻近、命名相似、未解释转储 | 待判，不得补空白 |

## 3. A-S 完整检查表

### A. 身份、版本与构建

必须查清：

- 3.19 客户端、2697 服务端、旧 C 服、ol-mod、v0.1、047 各自的哈希、版本、构建标识和来源。
- 每个二进制是否加壳、签名、重定位、可用节区与映像完整性。
- 工具链、依赖、许可证、确定性构建与产物追溯。
- README/报告中的数字是否与源码和实际测试一致。

验收：

- 任一结论都能追到文件哈希和具体版本。
- 构建和运行证据不是同一个模糊的“已验证”。

### B. 入口、生命周期与进程角色

必须查清：

- Client、Dedicated、Launcher、Auth、Lobby、IIPS、booking 的入口和启动顺序。
- 单实例、工作目录、命令行、配置、退出、崩溃和清理。
- Dedicated 是否仍复用完整 MP 引擎，哪些分支由角色常量控制。
- 客户端先启动/服务端先启动/中途重连时的状态与失败路径。

验收：

- 从进程入口追到 socket、帧循环和服务关闭。
- 每个服务有明确的启动前置和失败反馈。

### C. 帧循环、时钟与线程

必须查清：

- 服务端 tick、snapshot 发送节流、命令时间、客户端预测时间。
- 时间源、回绕、暂停、快进、系统时间变化。
- 线程所有权、并发队列、锁、关闭顺序和竞争条件。
- 固定步长与网络抖动下的可重复性。

验收：

- 能用记录输入重放同一帧结果。
- 时间回绕、暂停和重连有测试。

### D. 网络基础层

必须查清：

- UDP/TCP 套接字、绑定、端口、NAT、OOB、challenge、地址族和发送失败。
- bdDTLS INIT/COOKIE/COOKIE_ACK/DATA、密钥建立、重放保护与重协商。
- 分片大小、队列、ACK 请求/响应、重传、窗口、超时与序号耗尽。
- IP/端口是否来自 session 下发、NAT 反射或配置文件，优先级如何。

验收：

- 真实 3.19 字节能完成连接、保活、断开和重连。
- 有丢包、重复包、乱序、截断、伪造 MAC 与超大包测试。

### E. 连接与玩家状态机

必须查清：

- Free/Cookie/Handshake/Connected/Active/Disconnected/Reconnect 等真实命名与转换条件。
- 认证、challenge、connect、priming、gamestate、首帧、超时和踢出。
- 槽位分配、玩家身份绑定、会话恢复窗口、重复连接和地址变化。

验收：

- 每个状态都有触发、允许消息、超时、清理和可观测字段。
- 不经未验证握手不能进入 Active。

### F. 消息、可靠命令与序列化

必须查清：

- 消息前缀、opcode、位/字节混合游标、边界、EOF 和错误路径。
- reliable string/structured command、序号、ACK、重传、合并和上限。
- 压缩、加密、HMAC、配置串更新和消息最大长度。
- 每种线格式的目标版本与证据样本。

验收：

- 同一输入能够稳定编码/解码并给出否定测试。
- 不能把 2697、legacy3333 或 IW4 格式静默回退给 3.19。

### G. 地图、zone 与资产

必须查清：

- fastfile/zone 容器、加密、签名、块哈希、压缩、目录和 rawfile。
- `clipMap`、`MapEnts`、`ComWorld`、physics、XModel、material、weapon、script 等资产类型。
- 区依赖、加载顺序、替换/卸载、缺失资产与版本差异。
- 3.19 靶场与其他地图的实际资产清单。

验收：

- 至少一个目标地图能离线完整加载并列出资产依赖图。
- 资产解析失败不会用旧版本结构猜测补齐。

### H. 世界、碰撞与 trace

必须查清：

- plane、node、leaf、brush、brush side、BSP 树、contents/surface flags。
- `CM_BoxTrace`/`SV_Trace` 的起点、终点、AABB、mask、碰撞结果和地面判定。
- 静态模型、dynamic entity、terrain、glass、trigger、physics body 的参与方式。
- 出生点合法性、卡住处理、穿墙和地面吸附。

验收：

- 给定坐标能查询实体、向下距离、墙/地/斜坡分类。
- 服务端权威位置与客户端 pmove 在固定 replay 中对齐。

### I. 玩家控制与 pmove

必须查清：

- usercmd 字段、批次、时间、按键、摇杆、武器、视角和扩展输入。
- pmove 的加速度、摩擦、冲刺、蹲伏、跳跃、俯冲、游泳/爬梯、台阶、斜坡。
- 玩家盒体尺寸、站姿变化、贴墙、卡住恢复、地面吸附和服务端预测修正。
- 控制器/键鼠输入的客户端差异是否影响服务端语义。

验收：

- 离线场景覆盖直行、斜走、斜坡、台阶、角落、跳落和贴墙。
- 服务端位置、速度、`OnGround`、`groundEntityNum` 有实际 trace 依据。

### J. 实体、玩家与客户端状态

必须查清：

- 实体池、编号、类型、链接、事件、生命周期和删除。
- playerState/clientState/entityState 所有实际字段、位宽、增量规则。
- 武器、弹药、HUD、生命、死亡、姿态、队伍、记分和模式字段。
- 版本间重叠字段与不可复用字段。

验收：

- 字段表有偏移/位宽/语义/来源/版本/消费者。
- 不能只看服务端写入而不知客户端是否读取。

### K. Snapshot 与复制

必须查清：

- 基线、delta、帧历史、可见性、优先级、发送预算、节流和丢失恢复。
- 玩家/actor/entity/client/HUD/动画各 section 的顺序与终止符。
- 序列号、ACK 后提交、过期基线和完整帧回退。
- 真实 3.19 消费端解析和错误处理。

验收：

- 首帧、连续 delta、丢包、过期 ACK、空世界和断开都能重现。
- 真实客户端能消费并且画面状态与服务器一致。

### L. 游戏规则与对局

必须查清：

- 出生/复活、武器发放、切换、开火、弹道、命中、伤害、死亡、救援。
- 记分、回合、计时、胜负、围观、换边、加入/离开、比赛结束。
- 模式：DM、TDM、coop、PvE、训练/靶场、特殊模式。
- actor/bot/AI、导航、刷怪、掉落、奖励、连杀和载具。

验收：

- 单客户端最小对局闭环。
- 两客户端能互相看见、命中、死亡、复活、计分、结束与重新开始。

### M. 脚本与规则扩展

必须查清：

- GSC/VM/内置函数注册、脚本源、编译、加载和重载。
- 事件、通知、地图脚本、模式脚本、服务器配置和权限。
- 脚本失败、缺失 builtin、版本差异和错误隔离。

验收：

- 目标地图脚本无需代理替换即可跑通最小模式。
- 未实现 builtin 显式失败，不静默返回假值。

### N. 配置、管理面与运维

必须查清：

- cvar/dvar、默认值、来源、复制、启动覆盖、热更新和配置校验。
- console/RCON、管理命令、权限、审计日志、远程绑定和下载。
- 日志轮转、崩溃恢复、服务监督、健康检查和指标。
- 单实例、端口冲突、启动失败和优雅关闭。

验收：

- 管理员操作有鉴权、审计和失败返回。
- 配置错误不会静默进入错误模式。

### O. 身份、认证与安全

必须查清：

- CODOID、账号、ticket、TLS、session、securityKey、ECDH/AES/HMAC。
- challenge 防重放、身份绑定、服务端信任边界和密钥生命周期。
- 文件校验、反作弊接口、输入校验、资源上限。
- 证书、密钥、抓包和日志中的敏感数据隔离。

验收：

- 无票据不能凭自述 `xuid` 恢复身份。
- 重放、篡改、过期和错误密钥都有负测试。

### P. 插件、钩子与平台适配

必须查清：

- 插件 ABI、加载顺序、导出、回调、生命周期和版本门控。
- Windows/Steam/WeGame/Tencent 客户端的平台差异。
- dedicated 分支、客户端分支和注入代码的边界。

验收：

- 插件失败可隔离，主服务不进入半初始化状态。
- 不把客户端 hook 当成服务器实现。

### Q. 外围服务与端到端链路

必须查清：

- TCLS/更新、IIPS、Auth、Lobby、booking、matchmaking、目录、商店/资料服务。
- 端点下发、session 对象、securityKey 交接、房间创建、服务器分配和失败回退。
- 外部服务没有响应、返回旧格式或返回冲突数据时的行为。

验收：

- 同一客户端 PID 从启动到进战场有完整时间戳证据。
- IIPS/Auth/Lobby/Battle 各自有日志和成功阈值。

### R. 构建、测试与运行证据

必须查清：

- 构建命令、工具链、产物哈希、可重复性和干净环境。
- 单元、协议、fixture、集成、压力、丢包、重连和性能测试。
- 真实客户端连接、战斗、退出和清理证据。
- 每个“通过”的断言数量、测试范围和排除项。

验收：

- 报告中的断言总数与实际运行一致。
- 离线自测、进程存活和真实对局分别计数。

### S. 缺口、冲突与版本适用性

每个空白必须记录：

```text
缺什么
为什么缺
哪个对象/域需要它
现有最接近证据是什么
如何取得（文件、抓包、dump、反汇编、运行实验）
取得后解除哪个阻塞
失败或版本不符时如何降级
```

验收：

- 不存在“待补”而无获取方法。
- 不存在未标版本的低优先级证据进入权威字段表。

## 4. 完整审计完成判据

### 4.1 系统范围完成

- O1-O8 全部有身份、版本、路径、哈希和职责。
- 所有外围服务、启动器、管理面与资产链均已登记。

### 4.2 文件范围完成

- 每个文件有路径、大小、哈希、对象归属和相关性。
- 重复项已去重关联，不代表重复内容被忽略。
- 未解释文件进入缺口，而不是默认无关。

### 4.3 行为范围完成

- 每个关键能力有入口、调用链、生产者、消费者、失败路径。
- 关键字段有版本身份和字节级证据。
- 构建、测试、运行三类证据分别存在。

### 4.4 重构准备完成

- 最小可玩链路与完整模式链路有明确模块边界。
- 任意低版本参考都不能静默覆盖 3.19 事实。
- 真实客户端 + 服务端 + 外围服务端到端通过。

## 5. 当前不能给出的结论

- 不能宣称旧 C 服是可玩的 3.19 服务器。
- 不能宣称 ol-mod 的字段或 opcode 就是 3.19。
- 不能宣称 2697 二进制写链等于 3.19 消费链。
- 不能因 v0.1 的 122 项离线断言通过就宣称真实对局可用。
- 不能因 047 的 31 项测试通过就宣称最终 CODOL 协议已实现。
- 不能因进程不退出、快照能编码或抓包能回放就宣称可玩。

---

# 第三轮重构规格：模块边界、数据所有权与接口

状态：可实施的模块契约草案。协议字节仍受 3.19 证据门控；2697、3.3.3.3、CoD4x 和 IW4X 只能提供结构或算法参考。

## 6. 目标服务器模块

| 模块 | 唯一职责 | 不得做什么 |
|---|---|---|
| platform | 进程启动、时间、日志、配置、信号、退出 | 不解析玩家包，不写世界状态 |
| transport | UDP/TCP socket、地址、收发预算、限速 | 不解释 opcode，不改 session 状态 |
| session | 槽位、握手、超时、重连、密钥生命周期 | 不编码 snapshot，不访问世界实体 |
| wire_codec | framing、位/字节游标、分片、可靠命令、ACK、MAC | 不包含游戏规则，不决定状态转换 |
| world_assets | FF/zone/asset 加载、不可变资产索引 | 不持有网络 socket，不写实体状态 |
| collision | clipMap、brush、trace、contents 查询 | 不改玩家对象，不读 socket |
| movement | usercmd、pmove、地面/台阶/贴墙 trace | 不直接发送网络数据 |
| entity | 实体池、client/player state、生成与回收 | 不全局暴露可变指针给网络层 |
| replication | snapshot、baseline、delta、帧历史、可见性 | 不写实体本体，不读取未确认 ACK |
| rules | spawn、weapon、damage、death、score、round | 不打开 socket，不直接编码 wire |
| control | Auth/Lobby/booking/端点下发契约 | 不直接修改世界实体 |
| diagnostics | capture、replay、fixture、evidence id | 不改变业务状态 |

## 7. 数据所有权

| 数据 | 所有者 | 访问方式 |
|---|---|---|
| socket 与服务器地址 | platform/transport | transport 独占，其他模块只接收消息副本 |
| session 表 | session | 通过显式 session handle 访问 |
| 接收缓冲与分片 | session/wire_codec | 只读游标和提交接口 |
| 不可变资产 | world_assets | 只读引用，不在帧循环中破坏 |
| 世界实体 | entity | 只通过 world 命令修改 |
| playerstate/client | entity | 快照由 replication 读取副本 |
| 快照历史 | replication | 由 ACK 提交后推进 |
| 游戏规则状态 | rules | 通过 world command 修改 |
| 控制面会话 | control | 与 battle session 分账，地址/端点单独映射 |
| 证据标签 | evidence_registry | 编译期或启动期注册，不可运行时伪造 |

## 8. 接口草案

~~~~c
typedef struct codol_server codol_server_t;
typedef struct codol_session codol_session_t;
typedef struct codol_world codol_world_t;
typedef struct codol_frame codol_frame_t;

int codol_server_init(codol_server_t *server, const codol_config_t *config);
int codol_transport_poll(codol_server_t *server, uint32_t budget_ms);
int codol_session_receive(codol_server_t *server, codol_session_t *session,
                          const uint8_t *data, size_t len);
int codol_wire_decode(codol_session_t *session,
                      const uint8_t *input, size_t input_len,
                      codol_message_t *message);
int codol_message_dispatch(codol_server_t *server, codol_session_t *session,
                           const codol_message_t *message);
int codol_world_step(codol_world_t *world, const codol_usercmd_t *commands,
                     size_t command_count, codol_frame_t *frame);
int codol_replication_build(codol_session_t *session, const codol_frame_t *frame,
                            uint8_t *output, size_t capacity, size_t *output_len);
int codol_session_close(codol_session_t *session, codol_close_reason_t reason);
~~~~

接口规则：

- 解码失败必须返回具体拒绝原因，不能把未知 opcode 当 legacy；
- 状态变化必须发生在 dispatch/world/rules 层，transport 与 codec 只提交结果；
- snapshot 在发送成功并收到相应 ACK 前不得推进 history；
- control 层与 battle 层不能共享隐式全局状态；
- 所有 wire 条目必须绑定 3.19 证据 id。

## 9. 协议证据门控

~~~~c
typedef struct codol_wire_entry {
    uint16_t opcode;
    const char *version;
    const char *evidence_id;
    int (*handler)(codol_session_t *, const uint8_t *, size_t);
} codol_wire_entry_t;
~~~~

启动时校验：

1. version 必须是 3.19；
2. evidence_id 必须存在于目标证据总账；
3. 使用 2697、3.3.3.3 或 CoD4x/IW4X 证据注册的 handler 只能标记为 reference；
4. reference handler 不得进入 release wire 表；
5. 未标记 opcode 必须被拒绝并记录。

## 10. 验收测试

| 层级 | 最低测试 |
|---|---|
| platform | 单实例、端口冲突、优雅退出、时间回绕、配置错误 |
| transport | 重复包、乱序、截断、超大包、地址族、发送失败 |
| session | 状态机全转换、超时、重连、槽位复用、错误密钥 |
| wire_codec | 3.19 golden bytes、EOF、未知 opcode、分片、ACK、重放 |
| world_assets | 目标 FF/Zone、缺资产、损坏资产、版本不匹配 |
| collision | floor/step/slope/brush/hit/contents fixture |
| movement | 水平、跳落、台阶、贴墙、落地、穿墙负例 |
| entity | 生命周期、回收、重复绑定、断开清理 |
| replication | 首帧、delta、丢包、过期 baseline、ACK 提交 |
| rules | 单客户端最小闭环、两客户端命中/死亡/复活/计分 |
| control | Auth/Lobby/booking/端点下发、失败回退 |
| diagnostics | 可重放、hash 对账、证据标签拒绝 |

## 11. 放行条件

1. 3.19 目标客户端能完成 Auth/Lobby/booking/battle 路径。
2. 3.19 真字节能完成握手、gamestate、两帧 snapshot 和 ACK。
3. 单客户端能进地图并在无穿墙/无落地错误的情况下移动。
4. 两客户端能互相看见、命中、死亡、复活和计分。
5. 所有 release wire 条目都有 3.19 证据 id。
6. 旧版本参考不能静默回退。
7. 构建、测试、运行证据分别归档。

