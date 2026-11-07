# 06 — 分阶段任务、验收标准与停止条件

> 每个里程碑都必须区分：服务端自证、客户端兼容、运行时互通。
> 默认不允许启动游戏/服务端；运行级验收需要在新的任务和明确批准后执行。

## M0 — 资产、配置和依赖清单

- 前置：现有 A–G 报告、旧源码树、2697 server 目录、manifest。
- 复用：本文 01/02 清单；EARLY_SERVER 复用矩阵；C# README。
- 缺失：旧 CoD4x/ol-mod 构建工具链；2697 注册合法路径。
- 验收：
  1. 每个关键二进制有 SHA-256；
  2. 每个模块有源码或二进制证据路径；
  3. 版本目标/不匹配显式标注；
  4. 不把旧版本默认套到 2697。
- 证据：VERIFIED。
- 风险：版本混淆。
- 停止条件：没有工具链时不得尝试构建旧源码；不得安装工具。

## M1 — 2697 协议规格

- 前置：E1/E2/E3 报告；C# `CodolProtocol.cs`；B1/B2 参考。
- 复用：E3 的服务端 reliable 分支；E1 的 gamestate gate；E2 的 0x05/0x06 位置。
- 缺失：客户端 0x02 分派、0x06 语义、客户端 gamestate/configstring consumer。
- 验收：
  1. 字段、长度、终止符、分支条件写成表格；
  2. 每个字段挂一个二进制 RVA/函数或抓包证据；
  3. 未验证项明确标 BLOCKED。
- 证据：服务端 VERIFIED；客户端部分 STATIC-INFERENCE/BLOCKED。
- 停止条件：不要把字段形状匹配写成 opcode 兼容。

## M2 — 离线编码/解码黄金向量

- 前置：M1 规格；C# selftest；旧抓包/会话描述符。
- 复用：C# `CodolProtocol`、`MotionSnapshot`、`SessionDescriptor`；旧 `msg.c`。
- 缺失：2697 客户端产生的真实输入/输出向量；重定位/pointer table 影响。
- 验收：
  1. 已知字节输入逐字节编码/解码；
  2. 处理截断、长度、CRC/HMAC、异常输入；
  3. 失败不产生半状态；
  4. 全流程离线、无 socket。
- 证据：VERIFIED（仅 codec），不得升级为客户端兼容。
- 停止条件：任何未解释字节差都必须保留 BLOCKED。

## M3 — 连接状态机和可靠命令

- 前置：M2；确认 crypto/cookie 冲突。
- 复用：B3 UdpTransport/ClientLogic；B1 netchan/command queue。
- 缺失：2697 客户端的连接顺序、可靠序列号、超时/重连语义。
- 验收：
  1. 状态转移可枚举、可回滚；
  2. reliable command 1/2 分支可独立开关；
  3. 重放/重复/乱序测试通过；
  4. 服务器端收发日志可复现。
- 证据：服务器侧可实现；客户端侧 NOT-OBSERVED。
- 停止条件：未经批准的运行验证不得直接断言互通。

## M4 — 客户端分派验证

- 前置：M3；客户端 0xA2E50 调用链分析。
- 复用：阶段 F/G 的搜索工具和数据。
- 缺失：
  - opcode 读取点；
  - 0x02 → 0xA2E50 调用/间接调用；
  - 0x06 读取和终止语义；
  - 接收缓冲与内部 Msg 同一性。
- 验收：必须找到具体 RVA、分支、缓冲来源和调用链。
- 证据：当前 BLOCKED。
- 停止条件：找不到链接时，不得靠相似字段强行推进 M5。

## M5 — Gamestate 和 Configstring

- 前置：M4；E1 门控和 writer。
- 复用：E1 写路径；B1 configstrings；B2 gamestate；2697 runtime-assets。
- 缺失：客户端消费路径、索引映射、资源对象初始化。
- 验收：
  1. 编码顺序/索引/终止符与服务端事实一致；
  2. 客户端能从首包进入对应 gamestate 初始化阶段；
  3. 失败能区分“服务器没发”和“客户端没读”。
- 证据：服务端 VERIFIED；客户端 BLOCKED。
- 停止条件：客户端未解析时不得伪造成功或切旧通道。

## M6 — Snapshot、玩家和基础实体

- 前置：M5；E2 snapshot；C# MotionSnapshot；B1/B2 snapshot。
- 复用：位级快照/事件/玩家字段实现参考。
- 缺失：2697 字段顺序、delta、首个 snapshot EOF/子段语义。
- 验收：
  1. 首个 snapshot 可被解析并回读玩家原点/状态；
  2. 至少一个实体更新与一组 delta 通过；
  3. 无 overflow、无错误终止；
  4. 与客户端读取日志交叉验证。
- 证据：离线 VERIFIED 只能算 codec；客户端兼容需运行证据。
- 停止条件：若客户端不推进游标，先回到 M3/M4，不继续扩展实体。

## M7 — 大厅与首个“可玩场景”

- 前置：M6；lobby/session descriptor；地图/资源/脚本。
- 复用：C# SessionDescriptor/Exporter；Python lobby 研究；2697 runtime-assets。
- 缺失：2697 lobby 版本匹配、安全密钥、PvE booking、GSC/世界初始化。
- 验收：
  1. 进入大厅；
  2. 选择地图并成功连接战斗服；
  3. 进入局内且发出基础 usercmd；
  4. 区分“大厅成功”和“可玩战斗”。
- 证据：运行时 NOT-OBSERVED。
- 停止条件：若仅能进大厅而不能进地图，不得把它写成服务器可玩。

## 全局停止条件

- 没有客户端运行时/抓包证据，不得标记“兼容”。
- 没有合法注册/配置路径，不得绕过安全机制。
- 没有许可决策，不得把 AGPL/GPL 源码整段搬入闭源服务器。
- 没有目标版本证据，不得复用其他版本的 offset/wire ID。
