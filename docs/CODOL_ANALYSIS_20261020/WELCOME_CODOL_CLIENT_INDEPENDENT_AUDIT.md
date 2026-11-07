# Welcome_CODOL_client-main 独立静态审计

日期：2026-10-21（Asia/Shanghai）

范围：`F:\下载\Welcome_CODOL_client-main` 的整个交付包。只读静态审计；未启动客户端、战斗服务器、Auth、Lobby、IIPS，也未执行 CoD4x/IW4X。此报告不替代 CODOL 3.19 的第三轮 P0 证据；仅在报告内给出“客户端物证相关、服务端实现不近”的层级化判定，不形成跨项目源码血缘定论。

## 0. 结论摘要

状态：**静态审计已覆盖当前交付边界；本轮未再执行项目，运行能力未证实。交付包内没有服务器实现；不能据此推断外部完整仓库的服务端能力。**

一句话判定：这是一个面向 `1649370` 客户端的离线运行、原生内存适配、本地档案与资源供应链工程，不是战斗服务器实现，也不是完整游戏安装。

最重要的三项结论：

1. **服务端实现在本交付包内为 0。** 生产源码没有 socket server、netchan、dedicated server、快照生产、ACK 状态机、Pmove、碰撞 trace 或权威战斗循环。`application/multiplayer` 与 `adapters/transport` 只在文档中规划，目录不存在。
2. **客户端运行能力仍是有条件候选。** 离线 EXE 的入口、PE 结构和本地适配代码有较强的门禁与回读逻辑，但清单明确写有 `runtime_verified=false`、`offline_lobby_verified=false`；交付包又缺少运行所需的外部原客户端、资源与工作区。
3. **对 CODOL C 战斗服最有价值的不是“套服务端代码”，而是可复用方法。** 高价值部分为固定构建门禁、PE 恢复与导入恢复核验、Fastfile/Zone 容器完整性、资源来源与收据、单次运行目录隔离、失败关闭；这些方法可以指导重构，但网络、世界、移动、快照和战斗规则必须另建权威实现。

与本地 3.19 C 服务器是否“近血缘”？**同族客户端物证同源，但实现血缘不近。** 相同点主要是 `1649370` 客户端版本、材质资源、UI/DDL/Fastfile 格式；不同点是服务器协议与状态职责完全缺席，不能把该项目当成 3.19 C 服务器的直接代码祖先或另一实现。

## 1. 输入身份与盘点

| 项 | 独立复算结果 |
|---|---:|
| 文件 | 148 |
| 总字节 | 14,769,291 |
| 生产 Python | 66 文件 / 429,396 B |
| 测试源码 | 39 `test_*.py` / 238,046 B / 4,507 行 / 261 个 `test_` 方法 |
| 冻结测试夹具 | 17 文件 / 164,391 B |
| 文档 | 6 Markdown / 82,036 B |
| 二进制 | 2 EXE / 13,743,474 B（守卫 x86 PE32，ImageBase `0x400000`，SHA `31156231...a6`） |
| 扩展名 | 131 `py`、6 `md`、4 `json`、2 `exe`、2 `txt`、1 `cpp`、1 `cmd` |

### 1.1 盘点方法

递归枚举常规文件，排除版本库与缓存目录；每个路径记录相对路径、字节数、扩展名、粗分类和 SHA-256。源目录全量复验 148/148，错误 0；清单本身 SHA-256 为 `3326f22e9e4d5505a270a9f64bc039035c9451c017a1ff38e1cc928c2712f433`。项目除 `.gitignore` 外没有隐藏对象文件，也没有 `__pycache__`，说明交付包内没有提交 Python 字节码缓存。

分类中的 `other` 包含根入口、依赖文件和元数据；测试夹具与测试源码分别统计，避免把冻结历史字节码当作现行生产模块。

独立清单：[WELCOME_CODOL_CLIENT_INVENTORY.csv](./WELCOME_CODOL_CLIENT_INVENTORY.csv)，148 行逐文件 SHA-256；摘要见 [WELCOME_CODOL_CLIENT_INVENTORY.summary.json](./WELCOME_CODOL_CLIENT_INVENTORY.summary.json)。源目录无 `.git`，报告与清单均写在审计目录，未写入交付包。

交付包内 `manifests/build1649370.json` 的固定输入核对结果如下：

| 角色 | 清单身份 |
|---|---|
| 目标客户端 EXE | `codoMP_client_shipRetail.exe`，7,841,344 B，SHA `36997674...b537` |
| 目标客户端 Base DLL | `codoMP_client_shipRetailBase.dll`，60,327,992 B，SHA `ef75220d...6a20` |
| 资源版本 | `461` |
| 本地目标构建 | `1649370` |
| 运行镜像源候选 | `893f20f8...c3a38` |

清单只声明“8 个固定分析输入”，不是完整可运行安装。交付包内当前实际存在的是恢复镜像与守卫，不是原版 EXE、Base DLL、IFS、地图或完整资源树。

## 2. 项目性质与目录职责

| 层 | 实际职责 | 是否服务器 |
|---|---|---|
| `bootstrap` | 单次运行装配、参数、资源准备、进程启动编排 | 否 |
| `runtime` | DebugLoop、WOW64 上下文、进程/令牌、断点、文件缺失门 | 否 |
| `adapters/game/v1649370` | 固定 VA/ABI、PE 恢复、UI、本地档案、房间对象内存补丁 | 否，客户端适配 |
| `application/accounts` | 本地账号初始化、购买规则、事务状态 | 否 |
| `adapters/persistence` | SQLite 双档案、revision CAS、设置保存 | 否 |
| `resources` | Fastfile、Zone、RawFile、NetConstStrings、IWI、缓存 | 否，资产分析 |
| `analysis` | LZ4/AP32 静态恢复、PE 分析 | 否，离线研究 |
| `tools` | 启动、资源准备、索引、缓存快照 | 否 |
| `native/offline_guard` | WFP 断网、Job 单进程、PID/路径/创建时间绑定 | 安全边界 |
| `application/multiplayer` | README 规划“服务端房间与对局” | **不存在** |
| `adapters/transport` | README 规划通信端口 | **不存在** |

证据：README 第 1 段明确“尚未实现多人联机及完整对局闭环”；架构文档写明 multiplayer/transport “尚未创建”；源码检索未发现任何网络服务端调用或 netchan 实现。

## 3. A-S 域静态覆盖

| 域 | 状态 | 证据与边界 |
|---|---|---|
| A 身份与构建 | 已盘点到交付边界 | build `1649370`、资源 `461`、目标输入清单、恢复镜像清单 |
| B 入口与生命周期 | 部分实现，未运行证明 | `bootstrap.launch.run -> prepare -> ProcessSession.start -> DebugLoop.run` |
| C 帧循环与线程 | 无服务器帧循环 | 只有客户端调试事件循环、周期设置采样；无 `SV_Frame` 或权威 tick |
| D 网络基础层 | **缺失** | 无 socket server、UDP/TCP listener、netchan；WFP 只做拒绝 |
| E 连接状态机 | **缺失** | 无 challenge、connect、gamestate、client enter world |
| F 消息与传输 | **缺失** | 无可靠命令、sequence、ACK、分片、delta 编解码 |
| G 地图与资产 | 部分分析工具 | Fastfile/Zone/IWI/RawFile；无 CLIPMAP、MAP_ENTS、ComWorld 解析 |
| H 世界与碰撞 | **缺失** | 无 brush/BSP/trace/collision 实现 |
| I 移动与控制 | **缺失** | 无 Pmove、usercmd、ground trace、重力/摩擦/台阶 |
| J 实体与状态 | 客户端局部状态适配 | 本地房间、成员、档案对象；无服务器实体/playerstate |
| K 快照与复制 | **缺失** | 无 snapshot、baseline、delta、帧预算或复制表 |
| L 游戏逻辑 | **缺失** | 无 spawn、weapon、damage、death、round、score |
| M 脚本与规则 | 解析少量 RawFile | 可解压 GSC 类 RawFile，但不在服务器中执行规则 |
| N 配置与管理面 | 无管理面 | 只有启动参数和本地数据库 |
| O 认证与安全 | 本地/运行安全较强 | 本地账号、固定指纹、低权限令牌、WFP、Job、路径越界防护 |
| P 插件与平台适配 | 平台适配存在 | Win32 ctypes、Junction、ACL、WOW64；无插件 ABI |
| Q 外部服务 | 刻意关闭 | 明确禁止保护 DLL、动态断网；无 Auth/Lobby/IIPS 服务端实现 |
| R 构建与验证 | 静态可读，运行待证 | 无锁定构建脚本/原生工程文件；运行镜像清单写 `runtime_verified=false` |
| S 缺口与适用性 | 本报告登记 | 见缺件、冲突与复用建议 |

状态“部分实现”只说明源码中有路径和门禁，不表示在当前交付包可运行或已实机成功。

## 4. 启动与隔离链

已读源码的主要链路：

```text
start_client.cmd
  -> tools/launch_offline.py
  -> bootstrap.launch.run
  -> bootstrap.resource_setup.prepare
       -> fixed image copy
       -> dependency copy
       -> resource manifest / cache / ACL / junction
       -> settings restore
       -> prepare_runtime_image
  -> ProcessSession.start
       -> CreateRestrictedToken (low integrity)
       -> CreateProcessAsUserW(suspended)
       -> launch offline_guard.exe via runas
       -> wait guard-ready.json
       -> verify exact child PID/path/creation time
       -> ResumeThread
  -> DebugLoop.run
       -> module / exception / breakpoint / file-miss events
  -> session close
       -> terminate exact child
       -> write guard-done.json
       -> close dynamic WFP session
```

静态优点：

- `SessionLog` 要求 `workspaces/offline-runs/<new name>` 尚不存在，避免复用运行目录。
- 目标由低权限令牌启动；运行环境改写到会话目录，减少用户配置污染。
- 守卫不只按 PID：还核对完整镜像路径和进程创建时间；身份不符时不终止该进程。
- WFP 使用动态会话，规则覆盖 IPv4/IPv6 connect/receive；Job 限制单成员并 `KILL_ON_JOB_CLOSE`。静态复核还应核对 `AssignProcessToJobObject` 对已经放入父 Job 的调试目标可能失败；这是未执行验证点，不把它写成已通过。
- 启动在守卫 ready 之前保持进程挂起；未就绪不恢复线程。
- 资源库、overlay、输出、缓存、DLL 路径均有相对路径或重解析点约束。
- 失败路径尽量留下 `result.json`、`events.jsonl`、`guard-*.json`，而不是把“窗口出现”当作成功。

静态限制：

- 守卫源码注释指向外部 `D:/Games/Launcher source code` 与 `rebuild/evidence`，这些来源和构建记录不在交付包中；只有 `offline_guard.cpp`，没有 `.sln/.vcxproj/Makefile` 或校验过的构建配方。
- `ProcessSession.close` 在超时观察后会主动终止子进程；它证明宿主控制，不证明客户端自然退出或大厅成功。
- `DebugLoop.run` 在有限时长到时只记录 `observation_timeout`，不能把超时当成客户端启动失败以外的功能成功。
- `start_client.cmd` 固定 `C:\Python314\python.exe`；交付包没有该解释器，实际宿主环境也未随包锁定。
- 网络禁止是一个“黑盒运行边界”，不是服务端网络实现；不能从 WFP 过滤器反推出战斗协议。

## 5. 离线镜像与 PE 恢复

`bin/v1649370/codol1649370-offline.exe` 独立复核：

| 字段 | 结果 |
|---|---|
| SHA-256 | `55f067ac24e7d5ea9bea5acd46a1514eb1b7780a627b73c2094f41133dce3ffd` |
| 大小 | 11,075,584 B |
| Machine / Magic | `0x14c` / `0x10b`（x86 PE32） |
| ImageBase | `0x400000` |
| SizeOfImage | `0xE65D000`（241,549,312 B） |
| 节数 | 8 |
| 节名 | `.text`、`.rdata`、`.data`、`.tls`、`.rsrc`、`.tvm0`、`.protect`、`.rimp` |
| 原入口 RVA | `0xE5DC690` |
| 恢复入口 RVA | `0x8427DB` |
| 入口字节 | `e8dbff0000e989feffff`，与清单一致 |
| 资源目录 | 存在，RVA `0xE5D1000` |
| 导入 / 异常 / TLS 目录 | 存在 |
| 重定位目录 | 空 |

源码 `prepare_image` 的静态校验链包括：源 SHA、PE 机器/基址、入口字节、无重定位、19 DLL/455 import、TLS 模板可读、TLS index 可写、无未审计 TLS callback、固定节名、代码节原字节不变、TLS/导入回读不变、manifest 唯一提权属性降级、校验和重算。这些是良好的“候选物证固定”做法。需要核对 `pefile.PE(data=...)` 的默认目录解析方式，确保 `DIRECTORY_ENTRY_IMPORT/TLS/RESOURCE` 在进入这些检查前已真正加载；当前报告只记录静态语义，不把函数名或清单字段代替实际执行证明。

但必须保留以下边界：

- 镜像清单自身写 `runtime_verified=false`、`offline_lobby_verified=false`；`dynamic_protection_calls` 仍记录 `TenProxy.dll`/`TerSafe.dll` 动态装载点，只是宿主运行时拒绝这些模块。
- 源镜像 SHA 是候选源，不是原版目标 EXE 的哈希；它是导入恢复/代码恢复候选，不是完整运行时 dump。
- raw 文件只有 11.1 MB，而 `SizeOfImage` 约 241.5 MB；大量虚拟尾部靠零填充和运行时结构，不能据此声称完整静态代码已恢复。
- 镜像不包含完整本地依赖；清单要求至少 `GCloudVoice.dll`、`bink2w32.dll`、`dbghelp.dll`、`libcef.dll`、`mss32.dll`，这些不在交付包。
- 对 3.19 缺失区 `RVA 0xCA8400..0xCA8700`：本项目仍不能补齐。其为 `1649370` 的客户端镜像；即使存在相同区段，也未证明 VA/RVA 对齐、加载覆盖或函数体字节一致。不得把本项目镜像当作 `R3-A01` 的解。
- `.text` 可读不等于原客户端所有后期模块、保护页、动态代码或服务端二进制可读。
- 静态必须区分“文件地址”和“模块地址”：本镜像固定 `ImageBase=0x400000`，`layout.py` 里大量以 `0x5E...`、`0x62...`、`0x84...` 写出的常量实际是 VA；换算 RVA 必须减基址。报告不把这些 VA 与第三轮的 RVA 混用。
- 本项目镜像的 `.data` 虚拟大小远大于其磁盘大小（约 230,366,400 B 虚拟 / 401,408 B 原始），说明很多运行时状态只能由加载器/客户端初始化提供；静态文件本身不能替代完整内存证据。

## 6. Fastfile / Zone / 资源分析

### 6.1 Fastfile

`resources/fastfile.py` 的外层检查只接受 `IWff0100` / `IWffu100`，支持版本集合 `{334,365,461}`，AES-192-CTR 小端计数器、RSA 材料指纹、签名头、哈希链、zlib、Zone 目录连续性。`decode_fastfile` 在全部验证后才写输出，并拒绝覆盖输入或原客户端目录。

静态注意事项：

- 第三轮证据中的 `mp_firingrange.ff` layer-1 头部为 `IWffs100`。本模块的“签名后解密 header 期望”含 `IWffs100`，但外层 `inspect` 只接受两种外层魔数；不能把它当作第三轮样本已在本项目成功完整解码的证据。
- 代码从外部旧项目来源迁移了部分算法（源码注释点名 `D:/Games/CODOL/GameServer/...`），交付包没有该来源、对应 C 源或历史测试记录；许可声明为 AGPL-3.0-or-later，复用前需单独审阅。
- 代码只证明容器完整性、签名/哈希/Zlib/Zone 目录；报告自身明确 `asset_internal_layout_compatible=None`，不等于地图可加载。

### 6.1A 静态字符串中的协议线索（只作采集线索）

`analysis/bootstrap.py` 的 `anchor_references` 在恢复代码中搜索以下字符串：`getchallenge 0 "%s"`、`connectResponse`、`https://%s:%d/auth/`、`dwLogonStart`、`DW_ACCOUNT_LOGIN_COMPLETE`、`DW_LOBBY_CONNECTED`、`dwauth.ini`。这提供了客户端侧协议/认证的**静态线索**，说明恢复代码里确有相关字符串和可能引用。

独立复算确认这些 ASCII 字符串在当前离线镜像中各出现一次，且存在绝对指针字节候选：`getchallenge 0 "%s"` -> VA `0x5C071F` 前有 `0x68`；`https://%s:%d/auth/` -> `0xB99EBF`、`0xB9AC8A` 前有 `0x68`；`DW_ACCOUNT_LOGIN_COMPLETE`、`DW_LOBBY_CONNECTED` 也有 `0x68` 前置候选。另有 `connectResponse`、`dwLogonStart` 的非 push 引用候选，以及 `dwauth.ini` 的 `0x77EF42` push 候选。

但这些仍只是**字符串和指针字节**，源码自己也把结果称为“candidate references”；没有证明调用点、参数布局、消息方向、Reader/Writer、网络包裹或状态转移。对 C 服务器重构，正确做法是把这些字符串登记为 future capture 的搜索锚点，不是直接把 `getchallenge/connectResponse` 当作已闭合协议。

### 6.2 资产

`resources/assets.py` 只对类型 `36 RawFile` 与 `44 NetConstStrings` 做严格解析；其他类型计数为 `unparsed_type_counts`。它不解析：

- `CLIPMAP_MP`
- `MAP_ENTS`
- `ComWorld`
- `physics/XModel` collision
- pool 指针/引用重定位

因此它无法提供当前 C 服所缺的世界碰撞、出生点、实体布置或地图加载语义。对 3.19，最多作为“如何验证 FF/Zone 来源与目录”的方法参考。

### 6.3 IWI / 资源供应链

`resources/offline_resources.py` 的价值集中在：

- 严格规范 `main/images/*.iwi`，拒绝绝对路径、`..`、Windows 特殊名、保留名和 NUL。
- IFS 包固定 SHA，提取收据固定 SHA，条目路径与解码文件名绑定。
- AES-CTR 解密后严格校验 zlib 长度/EOF/尾部和 `IWi09` 头。
- 缓存清单限定 source EXE、resource version `461`、`old_version_resources_used=false`。
- 目标文件排他创建，已有文件必须字节一致；记录 `resource-supply.jsonl`。
- 缓存以 manifest SHA 为键，使用临时目录发布、硬链接、Junction 和 ACL。
- 源码内置 33 个固定 IFS 包摘要、对应提取收据摘要和少量已证明的覆盖优先级；这构成明确的“先证明再发布”策略，但它仍只是同版本客户端资源供应链，不是服务器资产协议。

严重交付缺口：

- 默认 `codec_path` 是外部绝对路径 `D:\Games\CODOL\Client\src\codol\resources\codec.py`，该文件不在交付包内；`CODEC_SHA` 校验会失败。
- 代码要求 `client/workspaces/offline-resource-raw/...` 的提取收据，交付包没有 `workspaces/`。
- 代码引用 `Original Client/IIPS/IIPSDownload` 的 IFS；交付包没有 `Original Client/`。源码虽然内置若干 IFS/收据摘要，但没有对应实体时无法独立证明其来源。
- README 声明存在 `resources/`，交付包没有该目录。

所以，资源供应链的“设计”可借鉴，“当前包可运行”不能成立。

## 7. 客户端原生适配与本地档案

`session_bridge.py`、`profile.py`、`room.py`、`purchase.py`、`ui_*.py` 都是 `1649370` 固定地址、固定字节 ABI 或 GFx 资源规则。它们：

- 在本地档案/UI 就绪后写入客户端会话内存；
- 通过 `VirtualAllocEx`、`WriteProcessMemory`、`Wow64SetThreadContext` 进行受控调试补丁；
- 在写入后做回读；
- 本地房间用 `LOCAL_MEMBER_ID=1`，明确不是平台账号或服务端玩家 ID；
- 本地购买、改名、余额和设置使用 SQLite/本地文件事务。

这不是服务器实现。它能帮助 C 服理解“客户端消费了哪些固定字段、哪些回调会在本地被替代”，但无法替代：

- 服务器侧实体/Client 布局；
- 网络序列化/反序列化；
- 服务端世界 tick 与 snapshot 广播；
- 权威移动、命中、伤害和积分。

账号/购买层可借鉴的是事务思想：revision CAS、同事务双档案、昵称与库存原子提交、失败不推进会话快照。它与 C 战斗服的运行时权威状态是不同层，不应直接搬进服务器 tick。

DDL 扫描/档案格式：

- `profile_format/scan.py` 通过 `playerdata` 版本/校验指纹和 `playersecuredata` 指纹定位定义对象，区分 relocated/raw；
- `schema.py` 从暂停点导出字段定义；
- 交付包没有这些运行时的 schema/capture，且 README 明确运行验证未完成。

这可以启发构造“只读证据采集器”，但不能被视为已有 3.19 档案字段表。

## 8. 测试、文档与交付自洽性

### 8.1 测试（仅作交付包自洽性旁证，不作为运行能力）

采用隔离复制到审计目录，未启动客户端；使用本机 Python 3.11 与现有依赖执行一次测试。结果：

| 指标 | 结果 |
|---|---:|
| 运行测试 | 216 |
| 失败 | 2 |
| 错误 | 20 |
| 跳过 | 4 |
| 结论 | `FAILED` |

失败类别：

- 交付缺件：`research/`、`verification/`、`workspaces/ui-investigation`、特定运行捕获、`trace_matchmaking_debugline`、`inspect_local_host`。
- 解释器不兼容：当前 Python 3.11 没有 `Path.is_junction`；README 固定的是 Python 3.14，不应把这一项直接归为生产缺陷。
- 生产导入缺陷（以本次旁证运行结果记录）：`runtime/contracts.py` 的 `GameEvents.bind_debugger(self, debugger: DebugControl)` 在类定义时引用了尚未定义的 `DebugControl`，且该文件没有 `from __future__ import annotations`；在 Python 3.11 下导入失败。按 Python 注解语义，该缺陷不应被解释为仅由 3.11 引起；但项目声明的是 3.14，仍应在新版本下复核后再定性。
- 兼容性差异：`Path.is_junction` 属于较新的 `pathlib` API；当前 Python 3.11 缺此方法。此项与生产导入缺陷分开，不能据此否定隔离设计本身。
- 测试期望与当前包不一致：重构差分测试、资源覆盖测试失败；不能仅用历史文档中的通过数推断当前状态。

测试源码中大量路径按 `ROOT = parents[2]` + `client/...` 设计，而交付包根目录已经是 `client` 内容；即使补全依赖，原样放置也可能失配。`tests/README.md` 也承认部分测试需要 `research/` 与 `verification/`。

### 8.2 文档冲突

| 冲突 | 证据 | 影响 |
|---|---|---|
| README 说 `test.py` 不存在 | 实际存在 `test.py` | 文档过期，不等于测试通过 |
| README 宣称有 `resources/`、`data/`、`workspaces/` | 交付包六者均不存在 | 无法按 README 启动 |
| README 说“当前支持本地离线适配” | 镜像清单写未运行验证 | 只能视为历史实现声明 |
| 文档引用 `client-refactoring-proposal.md`、`server/docs/...` | 交付包没有 | 架构与历史证据链断 |
| 测试文档引用 `research/`、`verification/` | 没有 | 当前包不是完整验收包 |
| 文档中的历史测试通过数 | 没有对应证据目录 | 只能当历史记录，不能当本轮结果 |
| `start_client.cmd` 固定 Python 3.14 | 当前系统无 `C:\Python314` | 实际启动条件未交付 |

静态核对发现 19 个 Markdown 链接，其中 8 个目标不存在；至少 6 个顶层运行目录缺失。交付包不是“解压即可启动”的完整环境。

另有一条供应链 provenance 风险：`tools/cache_new_archive.py`、`tools/index_new_resources.py`、`tools/prepare_offline_resources.py` 需要 `Original Client/`、`workspaces/offline-resource-raw`、`extract_local_ifs.exe`、`IFS2.dll` 等外部来源；其中 `prepare_offline_resources.py` 的默认 `--legacy-client` 还指向 `D:\\Games\\CODOL\\Client`。这些输入和工具/来源都没有随包交付，静态复核时不能把它们默认为可信。

## 9. 版本身份、证据等级与“血缘”判定

这里把“同版本客户端物证”和“服务器实现血缘”严格分开：

| 比较项 | 本项目 | 本地 3.19 C 战斗服材料 | 判定 |
|---|---|---|---|
| 目标客户端构建 | `1649370` | 3.19 目标链（待闭合） | 有客户端侧版本交集，不等于服务端同体 |
| 语言/运行形态 | Python 宿主 + ctypes + 固定 x86 客户端 | C 语言战斗服务器（用户描述） | 实现语言与所有权不同 |
| 网络职责 | 主动阻断，无 listener/netchan | 需要 battle transport/会话/复制 | 不近 |
| 世界/移动/战斗 | 无实现 | 服务器核心职责 | 不近 |
| Fastfile/Zone/IWI | 有容器和资源分析 | 可用于资产侧参考 | 方法相近 |
| 固定版本适配 | 完整使用固定 VA、字节、PE、GFx、DDL 契约 | 3.19 也需固定版本 | 工程方法可借鉴 |
| 源码历史 | 文档承认从外部客户端/旧项目迁移 | 3.19 逆向链独立 | 不能证明共同源文件 |

因此本项目的“血缘”结论应写成：

- **客户端物证层**：同属 CODOL `1649370` 客户端研究/适配生态，有明确输入版本、PE/TVM/UI/DDL/资源指纹；但交付包缺少来源仓库、提交历史与旧项目 C 源，无法证明与本地 C 服的源码谱系。
- **服务端实现层**：没有网络、会话、世界、复制、规则实现，不能称为“另一个独立战斗服”或“C 服的半截实现”。它与 CoD4x/IW4X 的关系也只能在未来用内容与接口证据交叉验证，不能靠“都是 COD 引擎族”推定。
- **可借鉴层**：版本门禁、资源供应链、候选回读、失败关闭和隔离运行；不是协议/玩法代码。

这类区分对后续重构尤其重要：如果因为它也处理 CODOL 客户端，就把它的 VA、本地房间或内存补丁带进 3.19 战斗服，会同时引入错误版本地址、错误状态所有权和错误网络假设。

## 10. 与 CODOL C 战斗服的借鉴边界

### 10.1 高价值、可直接借鉴方法

1. **单次运行身份**：新会话目录、拒绝复用、固定输入哈希、前后保护文件哈希。这与当前 AGENTS.md 的单次运行和证据要求一致。
2. **固定版本门禁**：版本、SHA、ImageBase、入口、导入、TLS、目录和节名全部固定；不符合即拒绝，不靠“看起来像”。
3. **候选隔离与回读**：PE 候选、manifest、补丁原字节、写后回读、代码节不变；适合新 C 服的构建/加载输入验证。
4. **资源供应链**：来源包、清单、提取收据、编码/解码哈希、严格 zlib/IWi 头、排他写入、路径穿越防护。
5. **失败关闭**：资源不全、冲突、守卫未 ready、模块不明、写后不一致时拒绝继续，而不是用空桩伪造成功。
6. **低权限与网络边界**：受控令牌、动态 WFP、Job 单进程、PID+路径+创建时间绑定，可作为离线实验框架参考。

### 10.2 中等价值、需改造成服务器组件

- 只读内存/文件采集、DDL 指纹搜索、Fastfile/Zone 容器诊断；
- SQLite 本地档案的 revision CAS 与原子事务；
- 外部调试事件日志、缺失文件断点、模块加载监控；
- 资源缓存目录的 ACL/硬链接/Junction 设计（服务器部署时应重新验证并发与安全）。

### 10.3 无直接价值或不能搬运

- 没有 socket server、UDP/TCP listener、netchan、challenge、connect、gamestate、snapshot、ACK、delta、fragment。
- 没有服务器帧循环、世界加载、CLIPMAP/MAP_ENTS/ComWorld/physics 解析、Pmove、trace、collision。
- 没有武器、伤害、命中、死亡、出生点、计分、回合、模式规则。
- 没有 Auth/Lobby/IIPS/booking 或主服注册实现；反而刻意阻断网络。
- 没有服务器权威实体/playerstate 或客户端复制表。
- 没有完整可运行客户端安装，更不是“另一个 C 战斗服”。

因此，“借鉴”只能落在方法、证据纪律和资源验证；不能把它的本地房间/UI 适配当作网络房间服务，也不能把它的内存补丁当成服务器协议。

## 11. 对 3.19 第三轮的影响

本项目的静态存在可提供**同版本客户端身份重叠**和**格式/适配方法的旁证**，但不能关闭第三轮 P0：

| 第三轮缺口 | 本项目能否补 | 原因 |
|---|---|---|
| 完整 3.19 加载镜像 / 缺失 RVA 区 | 不能 | 只有 `1649370` 客户端恢复候选，且 `runtime_verified=false` |
| 真实战斗 pcap、gamestate、snapshot、ACK | 不能 | 项目无网络服务/抓包证据 |
| recv buffer → consumer trace | 不能 | 有调试宿主，但没有 3.19 战斗消费链证据 |
| 靶场 FF layer-2 资产 | 不能 | 只有 layer-1/容器分析工具；资产类型仅 36/44 |
| mins/maxs/重力/trace | 不能 | 没有 Pmove/碰撞实现或数据 |
| 原始 2697 booking 包 | 不能 | 无 Auth/booking/服务端实现 |
| C 服网络/快照/玩法权威 | 不能 | 整个服务器实现面缺失 |

如果未来需要把它纳入证据，最低要求是：固定源包的完整哈希、可复现的 Python/依赖环境、补齐外部资源与工作区、把运行结果限定为客户端侧观察，并单独标注它不是服务端证据。

## 12. 缺件与下一步静态工作

### 12.1 项目自身缺件

1. 完整 `Original Client`（EXE、Base DLL、依赖 DLL、IIPS、IFS、地图/资源）及其清单。
2. `resources/v1649370/`、`data/accounts/`、`workspaces/` 的交付副本或明确排除说明。
3. `research/`、`verification/`、`D:/Games/CODOL/Client/src/codol/resources/codec.py` 等被引用来源。
4. 原生守卫构建工程、编译版本、SDK/MinGW 参数与 `offline_guard.exe` 的构建记录。
5. Python 3.14/依赖锁定和可复现环境；`requirements.txt` 只有四个包，未锁系统架构/Python 补丁版本。
6. 历史测试捕获（如 `offline-20261020-040037...`、`ui-investigation`）若仍要作为证据，需单独送交并冻结哈希。

### 12.2 可继续做的纯静态工作

- 逐文件 AST/AST 差分审计，重点复核 `session_bridge.py` 的 588 行固定 VA/ABI、所有 `contract` 字节与当前镜像的对应关系。
- 复核 Fastfile/Zone 的版本/魔数边界与第三方算法来源，建立“本项目可支持/不可支持格式”的明确矩阵。
- 用独立解析器核验 `offline-image.json` 的 import/TLS/manifest 摘要与脚本逻辑，不执行客户端。
- 为每个资源读取路径补一张 source → cache → runtime → receipt 的静态图，找出现有缺件和潜在 TOCTOU。
- 将本项目所有 `VA`（如 `0x5EBFF3`、`0x62CCEA`）统一换算到 RVA 并和 3.19 地址表隔离，禁止跨版本直接套用。
- 对 AGPL/第三方来源做许可证与代码来源台账；在用于新 C 服前决定“借鉴方法”还是“复制代码”。

## 13. 静态审计判定

**项目类型**：CODOL 1649370 客户端离线运行/适配工程。

**服务器完整度**：客户端宿主侧有较完整的“受控进程 + 本地档案 + 资源供应链”；在交付包内没有服务器实现，不能以本项目估计外部完整工程服务端能力。

**运行成熟度**：候选物证固定做得较好，但交付包不完整，运行/大厅验证未闭合；不能把本项目当作可用客户端安装或服务端基础。

**与 C 服的关系**：客户端物证层同属 CODOL `1649370` 研究链，服务端实现层血缘不近；不是 3.19 C 服缺失证据的替代品，也不能直接作为“另一独立服”的服务器样本。

**借鉴建议**：先借方法，不借业务实现。把版本门禁、资源清单/收据、失败关闭、低权限隔离和证据分层带入新服务器工程；网络、世界、移动、快照和规则重新以服务器权威模型实现。

## 14. 证据索引

- 文件总账：[WELCOME_CODOL_CLIENT_INVENTORY.csv](./WELCOME_CODOL_CLIENT_INVENTORY.csv)
- 清单摘要：[WELCOME_CODOL_CLIENT_INVENTORY.summary.json](./WELCOME_CODOL_CLIENT_INVENTORY.summary.json)
- 项目 README：`F:/下载/Welcome_CODOL_client-main/README.md`
- 架构边界：`F:/下载/Welcome_CODOL_client-main/docs/client-code-architecture.md`
- 输入清单：`F:/下载/Welcome_CODOL_client-main/manifests/build1649370.json`
- 镜像清单：`F:/下载/Welcome_CODOL_client-main/bin/v1649370/offline-image.json`
- 启动入口：`F:/下载/Welcome_CODOL_client-main/src/codol_rebuild/bootstrap/launch.py`
- PE 恢复：`F:/下载/Welcome_CODOL_client-main/src/codol_rebuild/adapters/game/v1649370/image.py`
- 运行隔离：`F:/下载/Welcome_CODOL_client-main/src/codol_rebuild/runtime/session.py`
- 调试循环：`F:/下载/Welcome_CODOL_client-main/src/codol_rebuild/runtime/debug_loop.py`
- 本地房间：`F:/下载/Welcome_CODOL_client-main/src/codol_rebuild/adapters/game/v1649370/room.py`
- 资源供应链：`F:/下载/Welcome_CODOL_client-main/src/codol_rebuild/resources/offline_resources.py`
- Fastfile：`F:/下载/Welcome_CODOL_client-main/src/codol_rebuild/resources/fastfile.py`
- 资产：`F:/下载/Welcome_CODOL_client-main/src/codol_rebuild/resources/assets.py`
