# CODOL Demonware 统一问题登记簿（Q-01 … Q-111）

> **口径（继承 E-15 §1 权重标度，未改动）**：I4=8 / I3=5 / I2=3 / I1=1；
> 解决度：PROVEN=1.0、INFERRED(强)=0.6、INFERRED(弱)=0.3、BLOCKED=0.0、REFUTED=0.0、CLOSED=1.0。
> **来源**：Q-01…Q-43 取 XVAL-02 权威账本 `XVAL02_QUESTION_REGISTER_MIGRATION.csv`；
> Q-44…Q-111 取 E-21…E-27 与本项目两份登记簿增量的实测行。
> **时点**：CLIENT-DEMONWARE-CODEC-KEYFLOW-001 交付后。

## 1. 总账

| 项 | 值 |
|---|---:|
| 问题总数 | 111 |
| 总权重（分母） | **634** |
| 加权得分 | **350.5** |
| 风险加权解决率（认知完备率） | **55.28%** |
| I4 条目数 | 47 |
| I4 权重 | **376** |
| I4 加权得分 | **217.6** |
| I4 加权完备率 | **57.87%** |
| 实时互操作状态 | **NOT-OBSERVED** |

**纪律**：认知完备率 ≠ 互通完成率。本表所有条目均保留其历史状态，
被后续轮次推翻者以 `REFUTED` 记录并保留原文，不删除、不改权。

## 2. 全量条目

| Q | 轮次 | 协议层 | 问题 | 影响 | 权重 | 状态 | 解决度 | 加权 | 证据引用 |
|---|---|---|---|---|---:|---|---:|---:|---|
| Q-01 | E-15 | 传输 | 游戏协议走哪条传输栈 | I4 | 8 | BLOCKED | 0.0 | 0.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-02 | E-15 | 传输 | 实时收包→应用层分派调用边 | I4 | 8 | BLOCKED | 0.0 | 0.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-03 | E-15 | 消息 | 实时消息外层分帧 | I4 | 8 | BLOCKED | 0.0 | 0.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-04 | E-15 | 消息 | 实时消息类型分派器 | I4 | 8 | BLOCKED | 0.0 | 0.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-05 | E-15 | Gamestate | 实时 Gamestate 0x03 消费者 | I4 | 8 | BLOCKED | 0.0 | 0.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-06 | E-15 | Configstring | Configstring 子帧识别(0x04) | I3 | 5 | BLOCKED | 0.0 | 0.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-07 | E-15 | Configstring | Configstring body reader 实时归属 | I3 | 5 | BLOCKED | 0.0 | 0.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-08 | E-15 | Configstring | 子帧尾 0x06 读取/对齐/终止 | I3 | 5 | BLOCKED | 0.0 | 0.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-09 | E-15 | Configstring | count1/A1/A2/A3 字段序 | I3 | 5 | PROVEN | 1.0 | 5.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-10 | E-15 | Configstring | A2 计数字宽(11bit) | I2 | 3 | PROVEN | 1.0 | 3.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-11 | E-15 | 可靠命令 | Reliable Command 0x01/0x02 字段序 | I4 | 8 | PROVEN | 1.0 | 8.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-12 | E-15 | Gamestate | 服务端 Gamestate 字段序 | I4 | 8 | PROVEN | 1.0 | 8.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-13 | E-15 | 传输 | CODOL 分片层常量 | I3 | 5 | PROVEN | 1.0 | 5.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-14 | E-15 | 传输 | TLS/libcurl 链归属 | I2 | 3 | CLOSED_NON_GAME | 1.0 | 3.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-15 | E-15 | 工程 | 网络虚表构造者 0x898588/0x898590 | I2 | 0 | MERGED | 0.0 | 0.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-16 | E-15 | 工程 | 0x67F5F0 真实函数边界 | I1 | 1 | BLOCKED | 0.0 | 0.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-17 | E-16 | 传输 | 0x1B0430 归属(ICMP) | I2 | 3 | PROVEN | 1.0 | 3.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-18 | E-16 | 工程 | 0x78772D 归属(时间戳工具) | I1 | 1 | PROVEN | 1.0 | 1.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-19 | E-16 | 消息 | 剩余 recv/recvfrom 调用点归属 | I4 | 8 | CLOSED | 1.0 | 8.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-20 | E-17 | 传输 | 0x6B4DE0 归属 | I2 | 3 | PROVEN | 1.0 | 3.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-21 | E-17 | 传输 | 0x784F60 归属 | I2 | 3 | PROVEN | 1.0 | 3.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-22 | E-17 | 传输 | Demonware 栈是否为游戏会话路径 | I3 | 0 | MERGED | 0.0 | 0.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-23 | E-17 | 传输 | 0x775A50/0x775AB0 虚表归属 | I4 | 8 | CLOSED | 1.0 | 8.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-24 | E-18 | 传输 | 0x898588/0x898590 槽位身份(=Q-15) | I2 | 3 | PROVEN | 1.0 | 3.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-25 | E-18 | 工程 | 虚表构造者/对象分配 | I2 | 3 | PROVEN | 1.0 | 3.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-26 | E-18 | 传输 | libcurl 簇是否为游戏路径 | I3 | 5 | CLOSED_NON_GAME | 1.0 | 5.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-27 | E-18 | 工程 | 0x776170 的注册者 | I1 | 1 | BLOCKED | 0.0 | 0.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-28 | E-18 | 传输 | Demonware 栈是否承载游戏会话 | I4 | 8 | BLOCKED | 0.0 | 0.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-29 | E-19 | 传输 | 0x6ABBC0 分帧器身份 | I3 | 5 | PROVEN | 1.0 | 5.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-30 | E-19 | 传输 | 0x6ABE80 状态机身份 | I3 | 5 | PROVEN | 1.0 | 5.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-31 | E-19 | 传输 | 0x788133 归属 | I2 | 3 | REFUTED | 0.0 | 0.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-32 | E-19 | 传输 | Demonware 类型码语义→游戏协议 | I4 | 8 | BLOCKED | 0.0 | 0.0 | E-15..E-19 / XVAL-01 / XVAL-02 审计 |
| Q-33 | XVAL-01 | 方法学 | 客户端搜索空间完备性（.data/.tp3/.tvm0）是否可恢复 | I4 | 8 | REFUTED | 0.0 | 0.0 | XVAL01_UNIFIED_QUESTION_REGISTER_UPDATE.md |
| Q-34 | XVAL-01 | 可靠命令 | 客户端 0x02→0xA2E50 绑定被独立字节/运行时验证 | I4 | 8 | BLOCKED | 0.0 | 0.0 | XVAL01_UNIFIED_QUESTION_REGISTER_UPDATE.md |
| Q-35 | XVAL-01 | Configstring | 0x04 外层值级识别 + 0x06 客户端读取闭合 | I3 | 5 | BLOCKED | 0.0 | 0.0 | XVAL01_UNIFIED_QUESTION_REGISTER_UPDATE.md |
| Q-36 | XVAL-01 | 握手 | COOKIE_ECHO 189 vs 219 对目标客户端的裁决 | I3 | 5 | BLOCKED | 0.0 | 0.0 | XVAL01_UNIFIED_QUESTION_REGISTER_UPDATE.md |
| Q-37 | XVAL-01 | 证据治理 | 项目内跨报告主张的一致性（无静默漂移） | I2 | 3 | INFERRED_WEAK | 0.3 | 0.9 | XVAL01_UNIFIED_QUESTION_REGISTER_UPDATE.md |
| Q-38 | XVAL-01 | 开源 | 开源实现可迁移边界被显式化 | I2 | 3 | PROVEN | 1.0 | 3.0 | XVAL01_UNIFIED_QUESTION_REGISTER_UPDATE.md |
| Q-39 | XVAL-02 | 传输 | 打包端 .text/.tvm0 的 aplib 保真性可独立验证 | ? | 3 | PROVEN | 1.0 | 3.0 | XVAL02_IMAGE/REGISTER AUDIT |
| Q-40 | XVAL-02 | 方法学 | 是否曾把 PE 节区尺寸比误用为内容缺失证据 | ? | 3 | PROVEN | 1.0 | 3.0 | XVAL02_IMAGE/REGISTER AUDIT |
| Q-41 | XVAL-02 | 证据治理 | REFUTED 解决度映射跨任务是否一致 | ? | 3 | BLOCKED | 0.0 | 0.0 | XVAL02_IMAGE/REGISTER AUDIT |
| Q-42 | XVAL-02 | 镜像 | 末节 .tp3（VS 52.5MB）未恢复是否掩盖游戏代码 | ? | 5 | BLOCKED | 0.0 | 0.0 | XVAL02_IMAGE/REGISTER AUDIT |
| Q-43 | XVAL-02 | 镜像 | BSS 尾部（208.1MB loader 零填）能否静态隐藏分派表 | ? | 5 | BLOCKED | 0.0 | 0.0 | XVAL02_IMAGE/REGISTER AUDIT |
| Q-44 | E-21 | 加密/会话 | HMAC/加密载荷对象协议归属 | I4 | 8 | INFERRED（非游戏；仍有替代解释） | 0.0 | 0.0 | E21-PRODUCER-CONSUMER, E21-INDIRECT |
| Q-45 | E-22 | 加密/会话 | HMAC 调用方向（入站/出站/共用） | I3 | 5 | INFERRED（共用入站校验，方向未闭合） | 0.0 | 0.0 | E22-CALLSITE, E22-DIRECTION, E22-OBFUSCATION |
| Q-46 | E-23 | 镜像/方法学 | 五个下游目标地址（0xA85AD0/0xA85BE0/0xA85640/0xA87830/0xA878A0）的 VA/RVA 基准归属 | I3 | 5 | **PROVEN** | 1.0 | 5.0 | E23-IMAGE-LAYOUT, E23-INIT-CLOSURE（VA→.text，354 直接调用点） |
| Q-47 | E-23 | 会话/分派 | `[edi+0x5F4]` 协商对象的身份与 slot+3 语义 | I4 | 8 | INFERRED（强） | 0.6 | 4.8 | E23-DISPATCH（ctor 0xA87BA0，vtable 0xC5A31C，slot+3 0xA87D50） |
| Q-48 | E-23 | 镜像/方法学 | E-22 "BSS 虚拟尾部"定位是否成立（历史更正） | I3 | 5 | **REFUTED** | 0.0 | 0.0 | E23-IMAGE-LAYOUT（同址按 RVA=BSS，按 VA=.text；调用点 354 处） |
| Q-49 | E-24 | 会话/分派 | `0x6AB310` 的入口与触发条件 | I4 | 8 | **PROVEN** | 1.0 | 8.0 | E24-ENTRY（唯一调用者 0x6AC192，条件 `[+0x5CC]==1 && msgcode==0x81`） |
| Q-50 | E-24 | 会话/生命周期 | `[edi+0x5F4]` 协商对象的构造/赋值/释放/复用 | I4 | 8 | **PROVEN** | 1.0 | 8.0 | E24-LIFECYCLE（ctor 0xA87BA0，vtable 0xC5A31C，写 0x6AB9B3/0x6AB9E7，删 0x6AA16F） |
| Q-51 | E-24 | 会话/加密 | `0xA87D50` 缓冲参数语义与 `0xACE180`/`0xACE1B0` 数据流 | I3 | 5 | INFERRED（强） | 0.6 | 3.0 | E24-A87D50（16 字节拷贝 + 表驱动变换；cipher 表静态不可得） |
| Q-52 | E-24 | 握手 | `[+0x5CC]` 阶段机与 0x81/0x83/0x84/0x85 的映射 | I3 | 5 | **PROVEN** | 1.0 | 5.0 | E24-OPCODE（阶段写点 6 处，分派表实测） |
| Q-53 | E-24 | 握手 | 0x85 入站方向（接收计数器 + HMAC）独立确认 | I4 | 8 | INFERRED（强） | 0.6 | 4.8 | E24-OPCODE（`[+0x5D0]` 递增 + `Bad recv counter`） |
| Q-54 | E-24 | 方法学 | E-23 "0x6AB310 无直接调用"报告与自有工具不一致 | I3 | 5 | **REFUTED** | 0.0 | 0.0 | E24-ENTRY + E-23 `_tools/t21_callers2.py` 输出 |
| Q-55 | E-24 | 握手 | 0x83/0x84/0x85 的产生侧归属 | I3 | 5 | BLOCKED | 0.0 | 0.0 | E24-OPCODE（入站解析产生，未闭合到构造点） |
| Q-56 | E-24 | 握手 | 阶段编号 1/2/3 的协议语义命名 | I2 | 3 | BLOCKED | 0.0 | 0.0 | E24-OPCODE（无独立语义证据） |
| Q-57 | E-25 | 会话/发送 | 应答数据块（`0x6ABAAA/0x6ABABB`）的字段来源与类型 | I3 | 5 | **PROVEN** | 1.0 | 5.0 | E25-PROVENANCE（序列化器 `0xDAB40`，`[ebx+0xC]`/`[ebx+0x10]`，data0/data1） |
| Q-58 | E-25 | 会话/发送 | `0x6AA230` 的真实职责（入队 vs 发送） | I4 | 8 | **PROVEN** | 1.0 | 8.0 | E25-CALLER-CALLEE（克隆 0x1C 节点 + 头插 `[edi+0xB8]`；无 send 引用） |
| Q-59 | E-25 | 会话/发送 | 出站队列 `[edi+0xB8]` 的弹出与递交 | I4 | 8 | **PROVEN** | 1.0 | 8.0 | E25-DOWNSTREAM（`0x6AA83D` 出队 → `0x6AA88D` 递交） |
| Q-60 | E-25 | 会话/发送 | 应答数据是否到达 `ws2_32!send` | I4 | 8 | **PROVEN** | 1.0 | 8.0 | E25-DOWNSTREAM（`0x783B50 → 0x784E40 → [0xBAE4C8]=ws2_32!send`） |
| Q-61 | E-25 | 会话/发送 | 套接字来源与生命周期（socket/closesocket） | I3 | 5 | **PROVEN** | 1.0 | 5.0 | E25-DOWNSTREAM（`0xB84950` socket(AF_INET,SOCK_STREAM,IPPROTO_TCP)；`0xB84B00` closesocket） |
| Q-62 | E-25 | 会话/发送 | 状态推进与入队/发送的相对时序 | I3 | 5 | **PROVEN** | 1.0 | 5.0 | E25-STATE（组装 → 入队 → 写 `[+0x5CC]`；发送在下一次泵） |
| Q-63 | E-25 | 会话/发送 | `[+0x628]` 传输对象的身份与 slot0 目标 | I3 | 5 | BLOCKED | 0.0 | 0.0 | E25-DOWNSTREAM（`0x6AA7C6 call edx` 运行时 vtable） |
| Q-64 | E-25 | 会话/发送 | 线上载荷与组装缓冲的逐字节一致性 | I4 | 8 | BLOCKED | 0.0 | 0.0 | 需运行时内存（本轮冻结约束禁止） |
| Q-65 | E-25 | 会话/发送 | 0x83/0x84/0x85 的处理函数是否经 `0x6AA230` 入队 | I3 | 5 | **REFUTED** | 0.0 | 0.0 | E25-STATE（`0x6AA230` 全部调用者仅 `0x6AA465`/`0x6ABAFC`，三码走各自处理函数） |
| Q-66 | E-25 | 会话/发送 | 方法学：E-24 "`0x6AA230` 入队到发送缓冲"是否成立 | I2 | 3 | **PROVEN** | 1.0 | 3.0 | E24 遗留建议被证实；但更正 `0x6AA230` 非发送函数本身 |
| Q-67 | E-25 | 会话/发送 | 第二个入队点函数 `0x6AAA10`（入队 `0x6AADE6`）的可达性与触发条件 | I3 | 5 | BLOCKED | 0.0 | 0.0 | E25-REACH（无 E8/E9 调用者、无指针引用；疑经计算跳转或不可达） |
| Q-68 | E-26 | 服务端/传输 | 2697 服务端是否有明确接收入口与顶层分派 | I4 | 8 | **PROVEN** | 1.0 | 8.0 | E26-RECV（`recvfrom`→`_SV_ReadPackets`→`_SV_PacketEvent`） |
| Q-69 | E-26 | 服务端/消息 | 服务端客户端消息 opcode 空间（宽度与取值） | I4 | 8 | **PROVEN** | 1.0 | 8.0 | E26-RECV（`0x472E7D` 3 位；`0x472EA7` cmp 4；跳表 `0x7B37A0`） |
| Q-70 | E-26 | 握手 | 服务端握手族身份（iD-Tech vs Demonware） | I4 | 8 | **PROVEN** | 1.0 | 8.0 | E26-FIELDMAP（`_CODOL_HandshakeInit`/`_HandshakeCookie`/`challengeResponse %d`） |
| Q-71 | E-26 | 握手 | `CLIENTCHAL`/`BDDATA` 在服务端是否存在 | I4 | 8 | **REFUTED**（服务端侧不存在，范围内） | 0.0 | 0.0 | E26-FIELDMAP（三样本各 0 命中） |
| Q-72 | E-26 | 握手 | 双侧共享握手标识（`challengeResponse`/`7F000001`） | I3 | 5 | **PROVEN** | 1.0 | 5.0 | E26-CROSSWALK（两侧均存在，含代码引用） |
| Q-73 | E-26 | 协议一致性 | 客户端 `0x81..0x85` 与服务端 `0..4` 是否同分派器 | I4 | 8 | **REFUTED** | 0.0 | 0.0 | E26-CONFLICTS（C-1：8 位 vs 3 位） |
| Q-74 | E-26 | 协议一致性 | 客户端阶段 `[+0x5CC]` 是否有服务端同构状态 | I3 | 5 | **REFUTED** | 0.0 | 0.0 | E26-CONFLICTS（C-3，无同构字段） |
| Q-75 | E-26 | 协议一致性 | 客户端下行编码（Demonware slot+3）是否有服务端同构 | I3 | 5 | **REFUTED** | 0.0 | 0.0 | E26-CONFLICTS（C-4，服务端 `0x01..0x06`） |
| Q-76 | E-26 | 握手 | 客户端 Demonware 握手的服务端对端存在性 | I4 | 8 | BLOCKED | 0.0 | 0.0 | E26-BLOCKERS（B-1，本样本及两 DLL 均无） |
| Q-77 | E-26 | 握手 | `challengeResponse` 两侧字段序对齐 | I3 | 5 | BLOCKED | 0.0 | 0.0 | E26-BLOCKERS（B-2） |
| Q-78 | E-26 | 服务端/方法学 | 服务端 legacy writer 与 2697 writer 并存是否影响分派判定 | I2 | 3 | **PROVEN** | 1.0 | 3.0 | E26-RECV（`CODOL2697_PROFILE_WIRE` VA 0x7B9812 切换） |
| Q-79 | E-26 | 服务端/归属 | 2697 服务端是否唯一可执行入口（是否另有 Demonware 服务端组件） | I3 | 5 | BLOCKED | 0.0 | 0.0 | E26-BLOCKERS（B-1/B-4） |
| Q-80 | E-27 | 生态/清单 | 2697 服务端生态的文件/模块全清单 | I2 | 3 | **PROVEN** | 1.0 | 3.0 | E27-INVENTORY（12,511 文件 / 1742.0 MB / 4 PE，100% 字节覆盖） |
| Q-81 | E-27 | 生态/归属 | 2697 服务端生态是否含 Demonware 组件 | I4 | 8 | **REFUTED** | 0.0 | 0.0 | E27-SIGSEARCH（`CLIENTCHAL`/`BDDATA` 0 命中，4 PE 全覆盖） |
| Q-82 | E-27 | 生态/归属 | `codol_dedrun.exe` 之外 3 个 PE 是否承担 Demonware | I3 | 5 | **REFUTED** | 0.0 | 0.0 | E27-MODULE（导出仅 Loopback/Guard；0 标记） |
| Q-83 | E-27 | 生态/对端 | Demonware 会话协议的服务端对端实现是否存在（工作区） | I4 | 8 | **PROVEN** | 1.0 | 8.0 | E27-CROSSWALK（`Crypto.cpp` L205-207；`codol_crypto.py::derive_session_keys`） |
| Q-84 | E-27 | 生态/对端 | 对端密钥派生是否与客户端 E-21 字符串一致 | I4 | 8 | **PROVEN** | 1.0 | 8.0 | E27-CROSSWALK（`CLIENTCHAL`→16B / `BDDATA`→72B 切分 20/20/16/16） |
| Q-85 | E-27 | 生态/对端 | 对端帧结构（`0xAB85` + AES-128-CBC + HMAC-SHA1[:8]） | I3 | 5 | **PROVEN** | 1.0 | 5.0 | E27-CROSSWALK（`codol_crypto.py` 文档头逐字段 + 实现） |
| Q-86 | E-27 | 生态/适配 | 对端实现是否直接适用于 2697 客户端 | I4 | 8 | **REFUTED** | 0.0 | 0.0 | E27-CROSSWALK（对端引用的 `0x9CE310` 在 2697 镜像不成立；面向 1.1.1.13/3.3.3.3） |
| Q-87 | E-27 | 生态/分层 | Demonware 控制面与 iD-Tech 对局面是否分层共存 | I3 | 5 | **INFERRED（强）** | 0.6 | 3.0 | E27-CROSSWALK（客户端同时含两族标记；对端为 TCP 大厅，`codol_dedrun` 为 UDP 17733） |
| Q-88 | E-27 | 生态/清单 | 2697 客户端是否为 Demonware 客户端 | I3 | 5 | **PROVEN** | 1.0 | 5.0 | E27-SIGSEARCH（`bdLobby`2 / `dwLobby`1 / `dwRoom`38 / `CLIENTCHAL`1 / `BDDATA`1） |
| Q-89 | E-27 | 生态/对端 | 2697 客户端 Demonware 帧的魔数/解码入口 | I4 | 8 | BLOCKED | 0.0 | 0.0 | E27-BLOCKERS（`0x686210` 为写入 `0xDEADBEEF`，解码入口未定位） |
| Q-90 | E-27 | 生态/对端 | 2697 Demonware 服务端模块的物理位置 | I4 | 8 | BLOCKED | 0.0 | 0.0 | E27-BLOCKERS（生态内 0 命中；生态外对端为其它构建） |
| Q-91 | E-27 | 生态/方法学 | `bds`/`demonware` 在 2697 生态内的命中性 | I2 | 3 | **REFUTED** | 0.0 | 0.0 | E27-NEGATIVE（`bds` 57 全为字节巧合；`demonware` 2 为致谢表/注释） |
| Q-92 | PEER-REUSE-AUDIT-001 | 客户端/定位 | 2697 客户端 `CLIENTCHAL`/`BDDATA` 节区、VA、RVA、终止方式 | I2 | 3 | PROVEN | 1.0 | 3.0 | 01 §2（`.rdata`，NUL 终止） |
| Q-93 | PEER-REUSE-AUDIT-001 | 客户端/xref | 两串全部交叉引用及所在函数 | I4 | 8 | PROVEN | 1.0 | 8.0 | 01 §3（各 1 处，同属 `0xAAB310`） |
| Q-94 | PEER-REUSE-AUDIT-001 | 客户端/KDF | `expandKey` 语义、标签与长度参数 | I4 | 8 | PROVEN | 1.0 | 8.0 | 01 §5-6（`0xAA9CE0`，0x0A/0x10、0x06/0x48） |
| Q-95 | PEER-REUSE-AUDIT-001 | 客户端/KDF | secret 层 = HMAC-SHA1(key=SHA1(transcript), data=sessionKey24) | I4 | 8 | PROVEN | 1.0 | 8.0 | 01 §5（`0xAA95C0`@`0xAAB884`，push 0x18） |
| Q-96 | PEER-REUSE-AUDIT-001 | 客户端/密钥切分 | 72B 切分 20/20/16/16 与 challenge[8:16] | I4 | 8 | PROVEN | 1.0 | 8.0 | 02 §1（`0xAA8D70`/`0xAA8BF0` 偏移） |
| Q-97 | PEER-REUSE-AUDIT-001 | 客户端/帧格式 | `u32len｜AB｜85｜seq｜iv16｜ct｜tag8` | I3 | 5 | PROVEN | 1.0 | 5.0 | 03 §1（`0xAAAA10`） |
| Q-98 | PEER-REUSE-AUDIT-001 | 客户端/完整性 | MAC 覆盖 `frame[:-8]`、取前 8B、比较逻辑 | I4 | 8 | PROVEN | 1.0 | 8.0 | 03 §2（`0xAAAE70`） |
| Q-99 | PEER-REUSE-AUDIT-001 | 客户端/序列号 | 接收序列号严格递增语义 | I3 | 5 | PROVEN | 1.0 | 5.0 | 03 §3（`[+0x5D0]`） |
| Q-100 | PEER-REUSE-AUDIT-001 | 客户端/状态机 | 握手消息码与阶段分派 | I3 | 5 | INFERRED（强） | 0.6 | 3.0 | 03 §4（`0xAAC0C0`） |
| Q-101 | PEER-REUSE-AUDIT-001 | 对端/适配 | 参考对端派生链是否已与 2697 客户端完全等同（含 20B/16B codec 层） | I4 | 8 | REFUTED | 0.0 | 0.0 | 05 §缺口（codec 常量/置换扫描 0 命中；对端无对应实现） |
| Q-102 | PEER-REUSE-AUDIT-001 | 方法学/地址 | E-27 的 `0x9CE310`/`0x6AB310` 地址口径 | I3 | 5 | PROVEN | 1.0 | 5.0 | 04 §3（RVA vs VA 更正） |
| Q-103 | CODEC-KEYFLOW-001 | 密钥流/Codec | 两 codec 的调用约定、常量 XOR、置换、方向语义 | I4 | 8 | PROVEN | 1.0 | 8.0 | 01 §1–§5 |
| Q-104 | CODEC-KEYFLOW-001 | 密钥流/字段 | `+0x5F0/+0x5F4` 与 `+0x5F9/+0x60D` 的真实语义 | I4 | 8 | PROVEN | 1.0 | 8.0 | 02 §0（更正上轮错标） |
| Q-105 | CODEC-KEYFLOW-001 | 密钥流/def-use | codec 输出的唯一写入者与唯一读取者 | I4 | 8 | PROVEN | 1.0 | 8.0 | 02 §4–§5 |
| Q-106 | CODEC-KEYFLOW-001 | 密钥流/消费 | 四个最终消费点的密钥来源与方向 | I4 | 8 | PROVEN | 1.0 | 8.0 | 03 §1–§3 |
| Q-107 | CODEC-KEYFLOW-001 | 密钥流/等价 | codec 是否改变最终消费值（STORE/LOAD 同掩码） | I4 | 8 | **PROVEN（等价）** | 1.0 | 8.0 | 03 §4 / 05 §2 |
| Q-108 | CODEC-KEYFLOW-001 | 对端/适配 | 参考对端是否已有该 codec 的等价实现 | I4 | 8 | **PROVEN** | 1.0 | 8.0 | 05 §3（`DecodeKey` 逐字节一致） |
| Q-109 | CODEC-KEYFLOW-001 | 方法学 | 上轮"对端无 codec"与 `.tvm0` 地址口径 | I2 | 3 | **REFUTED** | 0.0 | 0.0 | 06 §4 |
| Q-110 | CODEC-KEYFLOW-001 | `.tvm0` | VM 段是否存在与 codec/字段的交集路径 | I4 | 8 | PROVEN（交集全空） | 1.0 | 8.0 | 04 §1（`5F0/5F8/5F9/5FC/60C/60D` 全 0；`5F4` 2 处误命中） |
| Q-111 | CODEC-KEYFLOW-001 | `.tvm0` | VM 段完整语义是否已还原 | I3 | 5 | **BLOCKED** | 0.0 | 0.0 | 04 §5（未逐指令还原） |

## 3. 分轮次增量与历史变更记录

| 轮次 | 新增 Q | 权重增量 | 得分增量 | 交付时点总权重 | 交付时点得分 | 交付时点完备率 | 备注 |
|---|---|---:|---:|---:|---:|---:|---|
| E-15 (基线) | Q-01…Q-16 | +91 | +32.0 | 91 | 32.0 | 35.17% | 权重标度首次定义 |
| XVAL-02 (权威账本) | Q-01…Q-43 | +115 | +56.9 | 206 | 88.9 | 43.16% | 登记簿口径校正：I4 分母 104；Q-14/Q-23/Q-26/Q-31/Q-33/Q-37 重评 |
| E-21 | Q-44 | +8 | +0.0 | 214 | 88.9 | 41.54% | REFUTED: E-21 前对 0xA85AD0 的段区判定 |
| E-22 | Q-45 | +5 | +0.0 | 219 | 88.9 | 40.59% | REFUTED: 五地址属 .data BSS（Q-48 后续推翻） |
| E-23 | Q-46…Q-48 | +18 | +9.8 | 237 | 98.7 | 41.65% | 更正常数 I4 分母 104→112；Q-48 REFUTED |
| E-24 | Q-49…Q-56 | +47 | +28.8 | 284 | 127.5 | 44.89% | Q-54 REFUTED（0x6AB310 有唯一调用者） |
| E-25 | Q-57…Q-67 | +65 | +42.0 | 349 | 169.5 | 48.57% | Q-65 REFUTED（三码不同队列） |
| E-26 | Q-68…Q-79 | +76 | +32.0 | 425 | 201.5 | 47.41% | Q-71 REFUTED（服务端无 CLIENTCHAL/BDDATA） |
| E-27 | Q-80…Q-91 | +74 | +32.0 | 499 | 233.5 | 46.79% | Q-81/Q-82/Q-86/Q-91 REFUTED；对端在生态外 |
| PEER-REUSE-AUDIT-001 | Q-92…Q-102 | +71 | +61.0 | 570 | 294.5 | 51.67% | REUSE-PARTIAL；Q-101 REFUTED（对端无 codec） |
| CODEC-KEYFLOW-001 | Q-103…Q-111 | +64 | +56.0 | 634 | 350.5 | 55.28% | KEYFLOW-EQUIVALENT；更正上述两处措辞；Q-109 REFUTED、Q-111 BLOCKED |

**逐项复算（可对账）**：总权重 = 634；加权得分 = 350.5；完备率 = 350.5/634 = **55.284%**；
I4 权重 = 376；I4 得分 = 217.6；I4 完备率 = 217.6/376 = **57.872%**。

## 4. 历史变更记录（REFUTED / 重评 / 修正常数）

| 变更 | Q | 原主张 | 变更后 | 依据轮次 |
|---|---|---|---|---|
| 重评 | Q-14 | 传输/TLS 游戏协议 | CLOSED_NON_GAME | XVAL-01/XVAL-02 |
| 重评 | Q-23/Q-26/Q-31 | 按原状态 | REGRADED(XVAL-01) | XVAL-01 |
| 重评 | Q-33/Q-37 | 按原状态 | REGRADED(XVAL-02) | XVAL-02 |
| 重评 | Q-19/Q-15/Q-22 | 按原状态 | CLOSED / MERGED | XVAL-02 |
| REFUTED | Q-48 | 五下游地址属 .data BSS 虚拟尾部 | 按 VA 归属 .text（354 直接调用点） | E-23 |
| REFUTED | Q-54 | 0x6AB310 无直接调用 | 唯一调用者 0x6AC192 | E-24 |
| REFUTED | Q-65 | 0x83/0x84/0x85 经同一应答队列 | 三码各走独立处理函数 | E-25 |
| REFUTED | Q-71 | 服务端存在 CLIENTCHAL/BDDATA（codol_dedrun.exe 范围） | 该模块内无（范围 = codol_dedrun.exe） | E-26 |
| REFUTED | Q-81/Q-82 | 2697 服务端生态含 Demonware 组件 | 全部 4 个 PE 与 12,511 文件 0 命中 | E-27 |
| REFUTED | Q-86 | 对端实现可直接适用 2697 | 对端引用地址属另一构建 | E-27 |
| REFUTED | Q-91 | bds/demonware 命中为协议证据 | 均为字节巧合/致谢表 | E-27 |
| REFUTED | Q-101 | 参考对端无客户端 codec 层 | C# 路径 DecodeKey 与之逐字节一致（新增 Q-108） | CODEC-KEYFLOW-001 |
| REFUTED | Q-109 | 更正常数两处措辞与 .tvm0 VA | 6AB310=VA、5F0/5F4=provider 指针、.tvm0 VA=0x0DD58000 | CODEC-KEYFLOW-001 |
| BLOCKED | Q-111 | .tvm0 完整语义 | 未逐指令还原（交集检查为 0 命中） | CODEC-KEYFLOW-001 |

## 5. 声明

- 本登记簿为**只读汇总**，不新增、不删除任何条目，不改变任何权重与评分口径。
- `NOT-OBSERVED` 表示**未做实时互操作验证**；本轮所有结论均为静态。
- 认知完备率上升来自对既有 BLOCKED 链条的真实解析，非口径放宽。
