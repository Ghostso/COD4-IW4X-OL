# EARLY_SERVER_06 — 可行性量化评估

> 阶段 6 交付物（第 1 件）。所有百分比均为**主观工程估计**，标注依据与不确定性，非客观测量。
> 状态词：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / REFUTED / NOT_OBSERVED / INSTRUMENTATION_BLOCKED。

---

## 0. 最终总结：Q1–Q6

**Q1：发现了哪些真正的服务端程序和游戏逻辑模块？**
- **原生游戏服务端**：`dedicated\bin\codol_dedrun.exe`（8,469,493B，x86，185 `Plugin_*` 导出，CoD4x fork 的 CoDOL 原生移植）——**唯一的真实游戏服务端主程序**。
- **游戏逻辑模块**：`dedicated\src\codol\` 9 区域 591 文件（net/snapshot/player/weapon/vehicle/script/assets/collision/stats）。
- **大厅后端**：`lobby\`（alpha0022，纯 Python，服务 10/11/21/80/4/102，无认证）。
- **插件**：8–9 个进程内 DLL；**工具/编排**：`tools\`、`START-*.cmd`。
- **客户端改造**：`Kernel33.dll` + `patcher\`（暂不可用，见 D 类）。

**Q2：哪些可直接使用，哪些适合移植，哪些只能参考？**
- **直接复用（A，10 项）**：契约层——明文 OOB 连接文法、`sh1x_status`、准入名册、loopback RCON、lobby↔战斗服文本契约、selftests、结算契约、测试基座。
- **移植（B，18 项）**：传输核心、netchan/分片、snapshot 序列化、assets/collision、lobby 各业务包。
- **参考（C，12 项）**：`codol/player|weapon|vehicle|script`（版本锁定）、docs、日志、捕获、档案。
- **暂不可用（D，2）**：`Kernel33.dll`/patcher（反保护绕过，超范围）、`build\` 环境。**排除（E，6）**：重复 exe、pexports、图标、备份、空 .git、编译中间产物。

**Q3：早期服务端能否帮助现有 CODOL 从大厅进本地战斗？最强证据是什么？**
- **能，但不是"直接拿来跑"**。最强证据：① 契约层已被**双端实测**旁证（名册/状态/RCON/明文 OOB），现有 Lobby 可据此配合；② 早期 `codol/net` 提供现有项目缺失的**逐字节传输参考实现**；③ 合成对等体已推进到 **CS_PRIMED 并收到重组加密 gamestate**（`docs/CODOL_ASSOCIATION.md`）。
- **注意**：真人 C1 可玩性**未被本快照证实**（qconsole 全 humans=0）。

**Q4：如果不能直接运行，距离可用还缺什么？**
- **核心闸门**：gamestate/configstrings/snapshot **序列化器未移植**（PORT §4）。
- **两个未统一冲突**：密码学原语（A）、COOKIE_ECHO 长度（B）。
- **运行验证缺失**：真实 C1 互操作未在隔离环境跑通。
- **数据映射**：武器 1024 wire ID vs 128 槽；6519 configstrings 语义。
- **资源**：缺资产（defaultweapon_mp 等）、GSC 脚本编译错误。

**Q5：下一步最值得执行的三个任务？**
1. **离线复算 `lobby/captures/*.jsonl` 的 DATA MAC** → 定冲突 A（零风险、最高杠杆）。
2. **离线复算 COOKIE_ECHO 长度/偏移** → 定冲突 B。
3. **对齐会话描述符（258B 记录 + 16B securityKey）**，并据此校正现有 C# 战斗服的密钥下发。
（三者均**不需启动服务端**；序列化器攻坚（C04）留待真实 C1/回放就绪后。）

**Q6：哪些结论已确认，哪些仍未知？**
- **已确认**：真实服务端程序与模块清单；架构/初始化/帧循环/网络接收链（行号级）；协议项（NAT/QoS/INIT/COOKIE/DATA 外层/明文 OOB/svc 1/5）；契约层；指纹差异（单体 vs exe+Base.dll）。
- **仍未知/未证实**：真人 C1 能否连入**当前打包 build**；冲突 A/B 的真值；clc 客户端生产端布局；序列化器正确形态；`startgame.txt`/`mpdata_s` 完整字段语义。

---

## 1. 十维度评估

| # | 维度 | 状态 | 主观估计 | 依据与不确定性 |
|---|---|---|---|---|
| 1 | 服务端程序完整性 | **CONFIRMED** | ~90% | 主程序 + 591 CoDOL 文件 + 引擎底座齐全；缺"可玩收敛" |
| 2 | 服务端运行依赖完整性 | **STRONG_CANDIDATE** | ~65% | 可自跑 bots；缺真实客户端资产/地图安装、脚本编译 |
| 3 | 协议恢复程度 | **STRONG_CANDIDATE** | ~70% | 传输/握手/外层记录 CONFIRMED；序列化器与 clc 生产端未闭合 |
| 4 | 客户端配套程度 | **CANDIDATE** | ~40% | 早期 C1 在样本内；但需 patcher 改造（D 类）；现客户端形态不同 |
| 5 | 房间与玩家业务逻辑完整性 | **STRONG_CANDIDATE** | ~75% | lobby 8 包齐全、selftests 绿；字段语义未全闭合 |
| 6 | 战斗分配逻辑完整性 | **CONFIRMED** | ~85% | 选图 + 5 条 RCON + 会话描述符 + 准入名册，双端实测 |
| 7 | 地图加载及战斗初始化完整性 | **CANDIDATE** | ~45% | 探针可初始化（2053 configstrings/4689 leaves），但缺资产/脚本失败 |
| 8 | 对当前 CODOL 的兼容性 | **CANDIDATE** | ~40% | 系谱 CONFIRMED（IW4 分支）；单体 exe vs exe+Base.dll；线协议待现客户端侧确认 |
| 9 | 本地独立运行可行性 | **STRONG_CANDIDATE** | ~70% | 服务端能跑；端到端"真人进战斗"未证实 |
| 10 | 直接复用与移植预期成本 | **CANDIDATE** | 中-高 | 契约层低；序列化器高；AGPL3 法律成本 |

> 百分比均为**主观工程估计**，用于相对比较，不构成承诺。

---

## 2. 三条路线对比

### 路线 A — 早期服务端直接运行 / 最小适配
- **已确认前提**：`codol_dedrun.exe` 能自主启动跑 bots；握手/分片/输入桥已集成；早期 C1 在样本内。
- **未解决风险**：PORT §4 序列化器未移植（**阻塞**）；冲突 A/B；真人 C1 未证实；AGPL3 传染。
- **最小验证实验**：隔离环境用早期 C1 连本服务端，抓包观察是否越过 CS_PRIMED。**需批准。**
- **预期里程碑**：C1 收到可解析 gamestate → 进入世界。
- **成本/停止条件**：中；若 CS_PRIMED 后无画面/崩溃 → 转 B/C。

### 路线 B — 移植早期协议+业务逻辑到现有本地服务器（**推荐起点**）
- **已确认前提**：契约层可直接复用；`codol/net` 提供逐字节参考；现有 C# 已有握手全链/位级快照/会话描述符。
- **未解决风险**：冲突 A/B；序列化器；AGPL 许可（若复制源码须按 AGPL 发布）。
- **最小验证实验**：**离线**复算 `captures/*.jsonl` 的 MAC 与 COOKIE_ECHO 长度。**不启动服务端。**
- **预期里程碑**：C# 战斗服通过真实 C1 握手并收到首个 usercmd。
- **成本/停止条件**：中-高；若离线证明现有 C# 原语错误 → 立即改原语（低成本高收益）。

### 路线 C — 以现有 CODOL 为主体，选择性复用（**并行**）
- **已确认前提**：现有 Lobby 可进大厅；早期 docs/resources 提供数据模型。
- **未解决风险**：版本差异（单体 exe vs exe+Base.dll）。
- **最小验证实验**：现客户端侧反汇编确认 clc 生产端与 svc 值。
- **预期里程碑**：明确"哪些早期逻辑对现客户端成立"。
- **成本/停止条件**：低-中；作为 B 的并行知识补充。

---

## 3. 优先级建议（只建议，不执行）

1. **P0**：离线定冲突 A/B（零风险、最高杠杆）。
2. **P0**：对齐会话描述符（258B + 16B securityKey）。
3. **P1**：复用传输层参考（netchan/分片/clc）。
4. **P1**：集中攻克 gamestate/snapshot 序列化器（真正闸门）。
5. **P2**：pmove/武器/结算/持久化。

---

## 4. 覆盖率声明

- **已审计**：顶层结构、12 真实 PE、`codol/*` 9 区域目录级、协议核心源码、lobby 8 包、契约文件、patcher 文档。
- **未逐行审计**：`codol/script`(150)、`player`(87)、`snapshot`(76)、`weapon`(64)、`vehicle`(48) 的函数级语义。
- **受阻**：真实 C1 互操作、序列化器收敛——需运行验证，本轮只登记需求。
