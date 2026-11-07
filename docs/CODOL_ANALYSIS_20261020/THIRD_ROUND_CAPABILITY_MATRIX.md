# 第三轮全服务器能力矩阵

日期：2026-10-21（Asia/Shanghai）

说明：状态分为已证实（C）、部分（P）、冲突（X）、未知（U）。3.19 列是目标裁决；其他列只能提供结构或算法参考。

| 域 | 3.19 目标 | 2697 | 3.3.3.3 | CoD4x/IW4X | 第三轮判定 |
|---|---|---|---|---|---|
| A 身份/构建 | P：客户端构建已固定，服务端构建未闭 | C：2.6.9.7 PE 与哈希 | P：3.3.3.3 工程身份 | C：CoD4x 源码；IW4X 宿主未锁 | 目标身份可锁，服务端产物未完成 |
| B 入口/生命周期 | P：入口与若干恢复链 | P：原生 dedrun 入口存在 | P：game_server/Dedicated 入口 | C/P：CoD4x 完整；IW4X 宿主依赖 | 可借结构，不能借目标入口 |
| C 时钟/线程 | P：局部运行证据 | P：原生服务端未运行验证 | P：有注入/宿主线程边界 | C/P：CoD4x 可读；IW4X host scheduler | 必须自建确定性 tick |
| D UDP/TCP/OOB | P/X：目标端点与消费者未闭 | P：有原生网络与守护工具 | P：LocalNetworking/控制面 | C：CoD4x socket/OOB；IW4X OOB | 借算法，目标字节自建 |
| E 连接状态机 | P：存在状态候选，消费未闭 | P：同族状态机 | P：完整工程状态路径 | C/P：CoD4x state；IW4X host | 目标触发器需证据 |
| F netchan/消息 | P/X：有候选写侧和消费边 | P：旧/2697 新写通道 | P：同族消息层 | C：两项目均有 netchan 概念 | 协议隔离，不能跨版本回退 |
| G 地图/zone/资产 | P/X：FF 仅局部，世界资产未导出 | P：配套 runtime-assets | P：版本资产存在 | C/P：CoD4x BSP；IW4X open formats | 目标格式必须自证 |
| H 世界/碰撞 | U：目标 clip/trace 未闭 | P：同族世界数据 | P：Native Pmove/碰撞入口 | C/P：CoD4x clip/trace 参考 | 可借算法，不可借格式 |
| I Pmove/玩家控制 | P/X：移动修复但无落地/撞墙根因链 | P：前代状态 | P：原生绑定与实测历史 | C/P：CoD4x asm；IW4X host | 目标常量必须先恢复 |
| J 实体/玩家状态 | P：字段局部 | P：字段 writer 局部 | P：同族结构 | P/C：字段表存在 | 权限归世界实例，禁止全局可变状态 |
| K Snapshot/复制 | P/X：帧边界未闭 | P：writer 与 EOF 现象 | P：历史窗口 | C/P：CoD4x/IW4X 算法 | 目标 delta 需闭环 |
| L 游戏规则 | U：无完整规则闭环 | P：业务扩展 | P：较完整工程结构 | U/P：不能提供 CODOL 3.19 rules | 必须目标重建 |
| M 脚本/VM | P：脚本存在，语义未闭 | C/P：scripts 1,341 文件 | P：Game/Scripting | C：VM 概念 | 借 VM 设计，不借规则 |
| N 配置/管理 | P：控制面较多 | P：原生控制入口 | P/C：backend、DedicatedControl | C：CoD4x RCON/WebAdmin；IW4X RCon | 目标管理面另行定义 |
| O 认证/安全 | P/X：握手/记录层候选 | P：注册门控与 loopback | P：控制面 | P/C：CoD4x auth；IW4X envelope | 目标定制握手独立实现 |
| P 插件/平台 | P：Python/调试边界 | P：原生模块 | P：插件/注入边界 | C：插件 ABI/hook ABI | 借 ABI 经验，禁套宿主 |
| Q 外部服务 | P/X：Auth/Lobby/booking 已见 | P：原生房间/注册 | P：backend/localnetworking | P：master/party | 端点契约必须目标验证 |
| R 构建/测试 | P：离线材料丰富，端到端缺 | U：无构建 | P：工程可构建性未全验 | C/P：独立审计已冻结 | 验收方案需分阶段 |
| S 缺口/版本 | X：仍有多项未闭 | P：缺原包/消费 | P：版本不匹配 | C/P：工具链/宿主缺 | 外部证据作为明确阻塞 |

## 当前最重要的五种判断

1. 3.19 是唯一的协议和行为裁决者。
2. 2697 只能帮助解释同族前代的写侧结构。
3. 3.3.3.3 只能帮助解释较完整的同族工程分层。
4. CoD4x 与 IW4X 只能帮助建立服务器骨架、边界和算法。
5. 任何低版本字段、opcode、结构和资产字节在没有 3.19 证据时都必须标为候选或禁止。

## 状态使用规则

- C 可以进入实现，但仍需目标版本 fixture。
- P 可以进入设计，不得进入最终 wire。
- X 必须保留冲突，禁止静默选择一方。
- U 只能列为外部逆向需求，不能用其他版本补空白。
