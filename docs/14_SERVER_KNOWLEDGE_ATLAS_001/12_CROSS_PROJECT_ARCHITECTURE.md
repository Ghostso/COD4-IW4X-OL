# 12 — 跨项目架构同构分析 / CROSS-PROJECT ARCHITECTURE

> 证据 ID 见 `_EVIDENCE_REGISTER.md`。目标：从**实际执行路径**出发做同构分析，而不是按目录/函数名类比。
> 分类词汇：`IDENTICAL_SOURCE` / `PORTED_CODE` / `STRUCTURAL_MATCH` / `ARCHITECTURAL_ANALOGY` / `SAME_NAME_ONLY` / `UNRELATED_OR_DIVERGED` / `UNKNOWN`。

---

## 0. 参与对象与代号

| 代号 | 对象 | 目标客户端 | 源码 |
|---|---|---|---|
| OLD | `CODOL-AlphaBuild` 服务端 | 1.1.1.13 | 有 |
| 1113 | `CODOL.NET\CODOL_1.1.1.13` 服务端 | 1.1.1.13 | 有（与 OLD 同源） |
| 2697 | `CODOL_2697_Launcher` 原生服务端 | 2.6.9.7 | 无 |
| OLMOD | `_e1_regression\ol-mod-olfinal` | 3.3.3.3 | 有 |
| COD4X | `_lineage021\CoD4x_Server` | CoD4 (IW3) | 有 |
| IW4X | `iw4x-client`（两个克隆） | MW2 (IW4) | 仅客户端 |
| CSHARP | `CODOL-Combat-Server-v0.1` | 2697 实验 | 有 |

---

## 1. 模块一：生命周期与主循环

### 1.1 各项目实际执行路径

| 项目 | 启动 | 初始化 | 主循环 | 证据 |
|---|---|---|---|---|
| OLD / 1113 | `WinMain` | `Sys_Main` → `Com_Init` → `NET_Init`/`Netchan_Init`/`Huffman_InitMain`/`PHandler_Init` → `SV_Init` | `while(1) Com_Frame` → `SV_Frame` → `G_RunFrame` | EV-Old-Init, EV-Old-Frame |
| 2697 | 同族（Python 启动器 → `codol_dedrun.exe`） | 同族 + 2697 资源/CVar 初始化 | 同族 `SV_Frame`；gamestate 链新增门控 | EV-2697-Gate（链）；STATIC-INFERENCE（顺序） |
| OLMOD | `Injector32.exe` 注入 → `Bootstrapper32.dll` | 插件 lifecycle exports（3 个） | `Appmain.cpp` + `FrameHook`（hook 原生帧） | EV-R-OlMod |
| COD4X | `main`/`Sys_Main` | `Com_Init` → `NET_Init` → `SV_Init` | `Com_Frame` → `SV_Frame` | 源码 |
| IW4X | `DllMain`（被 MW2 进程加载） | `Loader` 组件 | **无独立主循环**（寄生宿主） | EV-R-IW4x-NoServer |
| CSHARP | `Program.cs` | 配置/自检 | `ServerHost` 循环 + `UdpTransport` | EV-CS-Selftest |

### 1.2 同构判定

| 对照对 | 分类 | 理由 |
|---|---|---|
| OLD ↔ 1113 | `IDENTICAL_SOURCE`（生命周期层） | 同一源码树，仅 `g_sv_main.c` 玩法改动；初始化/主循环逐行一致 |
| OLD/1113 ↔ 2697 | `PORTED_CODE` | 同一引擎骨架的延续版本；2697 叠加独立模块层（新增文件/导入），非重写 |
| OLD/1113 ↔ COD4X | `STRUCTURAL_MATCH` | 都有 `Com_Init→NET_Init→SV_Init` 与 `Com_Frame→SV_Frame`；**但 COD4X 无 CODOL 专用层**，且 CODOL 声称基于 CoD4x fork → 实为**共同祖先**（见 `13`） |
| OLMOD ↔ OLD/1113 | `ARCHITECTURAL_ANALOGY` | OLMOD **不重用**原生服务端进程；它用注入+原生函数绑定，把服务端逻辑放进插件。生命周期**角色**相似，实现不同 |
| IW4X ↔ 任意服务端 | `UNRELATED_OR_DIVERGED` | IW4X 无服务器主循环（DLL-only） |
| CSHARP ↔ 2697 | `ARCHITECTURAL_ANALOGY` | 自研独立实现，模仿协议语义；无共同代码 |

### 1.3 关键问答（任务书 3.1）

1. **主循环结构是否相同？** OLD/1113/2697 家族相同（`Com_Frame→SV_Frame→G_RunFrame`）；OLMOD 不同（hook 宿主帧）。
2. **相同函数是否在同一调用位置？** OLD↔1113 完全相同；2697 在发送链上加门控层。
3. **初始化顺序是否相同？** OLD↔1113 相同；2697 增加文件/句柄探测导入（`_open_osfhandle`/`_stati64`/`GetFileInformationByHandle`）。
4. **相同生命周期来自公共引擎还是独立实现？** 来自**公共 Quake3/CoD 引擎骨架**（Id/Ninja/TheKelm 版权链）；CODOL 在其上叠加。
5. **OLMOD 是重用引擎服务端还是把服务端逻辑重实现为插件？** **混合**——重用原生游戏引擎内核，其余控制面/服务器逻辑作为插件实现。
6. **2697 大厅/连接生命周期能否映射？** 连接/入世骨架可映射；**gamestate 门控之后的客户端消费不可映射**（BLOCKED）。
7. **哪些有调用链证据？** OLD/1113 全链、2697 服务端写入链有；2697→客户端消费链**无**。

---

## 2. 模块二：网络传输层

| 子模块 | OLD/1113 | 2697 | OLMOD | COD4X | IW4X |
|---|---|---|---|---|---|
| socket 创建 | `NET_Init` | 同族 + 11 loopback 守卫 | 自有 `WinsockHooks` | `sys_net.c` | 客户端 `Network.cpp` |
| 收包入口 | `NET_UDPPacketEvent` | 同族 | hook | `sys_net` 事件 | 客户端 |
| 自定义加密握手 | **bdDTLS（P-224 ECDH + MAC）** | 同族 | 自有 `net_dtls_cod.cpp` | **无**（仅 XOR 混淆） | **无** |
| 记录层 | DATA 16B 头 | 同族 | 自有 | 无 | 无 |
| netchan 头 | 4/6 B 自有 | 同族 | 自有 `net_chan_mp.cpp` | 10 B（Quake3） | 同 CoD4x |
| 分片 | `{index,last,stride=1162,chunk}` | 同族 | 自有 | 4 B start + 2 B len | 同 CoD4x |
| body 变换 | `CODOL_Xor` | 同族 | — | XOR 混淆 | 无 |
| 上限 | 1162×128 | 同族 | — | `0x20000` | `0x20000` |

**同构判定：**

| 对照对 | 分类 |
|---|---|
| OLD/1113 ↔ 2697 传输 | `PORTED_CODE` |
| CODOL ↔ COD4X 传输 | `STRUCTURAL_MATCH`（都是 netchan），但**握手/加密 `UNRELATED_OR_DIVERGED`** |
| CODOL ↔ IW4X 传输 | `ARCHITECTURAL_ANALOGY`（OOB/发现）＋ 握手 `UNRELATED_OR_DIVERGED` |
| COD4X ↔ IW4X netchan | `IDENTICAL_SOURCE`（`netchan_t` 1:1） |

**强制否定：** 不能因为“都用 UDP”或“都有 `Netchan_*`”认定协议相同。三者的头长度、分片描述、上限、加密均不同。

---

## 3. 模块三：消息与序列化

| 子模块 | OLD/1113 | 2697 | COD4X | IW4X | OLMOD |
|---|---|---|---|---|---|
| MSG_WriteByte/Short/Long/Data/String/Bits | 有（msg.c） | 同族 | 有（同名同结构） | 客户端 | 有 `msg_mp.cpp` |
| Huffman | `Huffman_InitMain` | 同族 | 有 | 有 | — |
| clc 3 位 opcode | 有（`sv_client.c:2505`） | 同族 | 有 | 客户端 | 自有 |
| Huffman 解压 | **clc 分支不做** | 同族 | 做 | 客户端 | — |
| 可靠命令 | `0x01 + string` | **`0x01 + string` / `0x02 + long + short + data`** | 自有 | 自有 | 自有 |
| gamestate opcode | `0x02` | `0x03` | `0x02`(IW3) | IW4 自有 | 自有 |
| configstring opcode | `0x03` | `0x04` | `0x03` | IW4 自有 | 自有 |
| EOF | `0x05` | `0x06` | `0x05` | 自有 | 自有 |

**同构判定：**

| 对照对 | 分类 |
|---|---|
| OLD/1113 ↔ COD4X `MSG_*` | `STRUCTURAL_MATCH`（同名同结构，Quake3 血统）；**不能**升级为 CODOL↔CoD4x 直接血缘（见 `13`） |
| OLD/1113 ↔ 2697 | `PORTED_CODE` |
| CODOL ↔ IW4X 序列化 | `ARCHITECTURAL_ANALOGY` |
| 2697 `0x02` ↔ 客户端 `0xA2E50` | `STRUCTURAL_MATCH`（字段形状），绑定 `UNKNOWN` |

**强制否定：** 只发现同名函数最多判定为候选对应关系。`0x02` 与 `0xA2E50` 就是这种情形。

---

## 4. 模块四：游戏状态与业务层

| 子模块 | OLD/1113 | 2697 | OLMOD | COD4X | IW4X |
|---|---|---|---|---|---|
| client_t 状态机 | CS_* | 同族 | 自有 | `clientConnectState_t` | CA_*/CS_* |
| entity delta | MSG_WriteDeltaEntity | `codol_2697_delta.c` | `sv_gamestate_mp` | 自有 | `ConfigStrings.cpp` |
| Configstrings | 6519（武器 5362 起） | count ≤ 0x1DD7 | 自有 | `SV_SetConfigstring` | `ConfigStrings` |
| Snapshot | IW3 serializer（未收敛） | `_WriteSnapshot→_WriteSnapshotReached` | 自有 | `SV_WriteSnapshotToClient` | 客户端 |
| 武器 | `codol\weapon\*` | `codol_weapon_2697.c` + attachment registry | `weapon_*` | `bg_weapons.cpp` | `Weapons` |
| 脚本 VM | `scr_vm_*`/`cscr_*` | 同族 | `Game/Scripting` | `cscr_*` | `GSC` |
| 大厅/匹配 | lobby（Python） | 2697 注册门控 + 脚本 | backend（Demonware） | master server | `Party`/`Session` proto |

**同构判定：**

| 对照对 | 分类 |
|---|---|
| OLD/1113 ↔ 2697 业务层 | `PORTED_CODE`（骨架）＋ CODOL 业务定制（新增门控/武器/archive） |
| OLD/1113 ↔ OLMOD 业务层 | `ARCHITECTURAL_ANALOGY`（同为 CODOL，但 3.3.3.3 vs 1.1.1.13 版本差异） |
| CODOL ↔ COD4X 业务层 | `STRUCTURAL_MATCH`（引擎能力）＋ `UNRELATED_OR_DIVERGED`（CODOL 业务） |
| CHSHARP ↔ 2697 业务层 | `ARCHITECTURAL_ANALOGY`（模仿） |

---

## 5. 统一模块交叉图（节点/边/证据/可信度）

**边类型图例：** `CALL`=调用 · `DATA`=数据传递 · `INHERIT`=代码继承 · `PROTO`=协议对应 · `INFER`=推断关系

```
[引擎公共骨架] --INHERIT--> [OLD] --INHERIT--> [1113]        EV-R-OldSrc-1113   HIGH
[引擎公共骨架] --INHERIT--> [2697]                            EV-2697-Modules    MEDIUM
[CoD4x 族群]  --INHERIT--> [OLD]（CODOL 移植自 CoD4x fork）    EV-R-OldSrc        HIGH
[Quake3]      --INHERIT--> [COD4X]                            EV-Netchan-CoD4x   HIGH
[Quake3]      --INHERIT--> [IW4X]（netchan_t 1:1）             EV-Netchan-IW4x    HIGH
[OLD]         --PROTO--> [C-1113]（1.1.1.13）                  EV-C-1113          PARTIAL(未互通)
[2697]        --PROTO--> [C-2697]（2.6.9.7）                   EV-C-2697          LOW(仅形状)
[OLMOD]       --CALL--> [原生引擎内核]（注入+hook）             EV-R-OlMod         HIGH
[OLMOD]       --DATA--> [C-3333]（3.3.3.3）                     EV-C-3333          HIGH
[CHSHARP]     --PROTO--> [2697]（模仿）                        EV-CS-Codec        LOW
[COD4X]       --PROTO--> [CODOL 战斗通道]  ← 不成立             EV-Battle-Distinct REFUTED
[IW4X]        --PROTO--> [CODOL 战斗通道]  ← 仅 OOB/发现层可比   EV-Battle-Cmp      LOW-MEDIUM
```

**强制区分：** `INHERIT` 与 `PROTO` 与 `INFER` 不能用同一条未区分的边。上图中同一对节点间的不同关系已分别标注。

---

## 6. 交叉点与分离点（回答任务书 §8.1/§8.2）

### 6.1 真正交叉的模块

| 交叉点 | 边界 | 传递什么 | 在哪终止 |
|---|---|---|---|
| `MSG_*` 与消息编码器 | Quake3 血统 | 位/字节 | 消息层（CODOL 与 CoD4x 各有实现） |
| netchan 与可靠传输 | 引擎传输层 | 序列号/分片 | CODOL 自有实现（非 CoD4x 同一份） |
| `SV_*` 与服务器帧循环 | 引擎服务端层 | 帧调度 | OLD/1113/2697 同族 |
| Netfield 与实体状态 | 游戏状态层 | delta 字段 | 各项目自有序列化 |
| Gamestate/Configstrings | 应用层 | 初始化状态 | **2697 有独立 writer；客户端消费 BLOCKED** |
| OLMOD 插件与宿主引擎 | 插件边界 | 原生函数绑定 | OLMOD 自有 ABI |
| 2697 原生协议与最终版客户端 | **未交叉（BLOCKED）** | — | 在客户端分派处断开 |

### 6.2 没有交叉的模块

| 模块对 | 为什么没有交叉 |
|---|---|
| CODOL 战斗握手 ↔ CoD4x/IW4x | 只有 CODOL 有 cookie+ECDH+MAC；CoD4x 仅 XOR，IW4x 无加密 → **设计不同** |
| 2697 ↔ 客户端 `0xA2E50` 分派 | 客户端镜像未导出分派链 → **尚未闭合**（非证明不存在） |
| IW4x ↔ CODOL 服务端 | IW4x 无服务器源码 → **样本缺失** |
| OLMOD backend ↔ 2697 注册门控 | 两个不同版本（3.3.3.3 vs 2.6.9.7）→ **版本差异** |
| REF_LOBBY_KIT ↔ CODOLServer | 两个不同实现 → **实现独立** |

---

## 7. 架构同构结论

1. **共享骨架**：Quake3/CoD 引擎骨架（`Com_Init/SV_Frame/G_RunFrame/MSG_*/netchan`）跨 OLD/1113/2697/CoD4x/IW4x 存在，来源是**公共祖先**（Id + CoD4x 族群）。
2. **CODOL 独有层**：bdDTLS 握手、记录层、CODOL 业务（configstring 6519、武器 wire ID 1024、记分板/HUD/安全档案）。
3. **2697 独有层**：`codol_2697_*` 模块组、双门控、新 opcode 集、武器 2697。
4. **OLMOD 属于不同形态**：注入+插件重实现，**不重用原生服务端进程**。
5. **COD4X/IW4X 的定位**：CoD4x = 服务器骨架模板（高价值/战斗协议低价值）；IW4x = OOB/发现/认证信封参考（中低价值，无服务器源码）。
6. **真正的架构分离点在握手与加密**：CODOL 战斗通道 **DISTINCT**。