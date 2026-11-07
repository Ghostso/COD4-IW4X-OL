# OLMod / CODOL 本地战斗服务器 — 阶段 0 审计报告

- 报告时间: 2026-10-09T01:43:12.644Z
- 被审计仓库: F:\\桌面\\ol\\ol-mod-olfinal
- 分支 / HEAD: OLfinal-live / 3915fa9 (Restore Factory teleporter links and staged return travel)，工作树干净
- 审计性质: 只读。未修改被审计仓库任何文件。
- 证据等级约定: [已核验] = 本次直接读取源码/磁盘证据；[文档声明] = 仅见于文档、本次无法核验。

---

## 0. 结论摘要（必须先读）

任务的三个前提与磁盘事实不符，这决定了后续所有工作方向：

### 前提错误 1 — OLMod 不是待补全的基础，而是已经完成的 CODOL 本地服务器

任务把 OLMod 当成需要“建立 CODOL Adapter、打通 Lobby -> Match -> Battle Server -> Handshake -> Map/Zone Load -> Player Spawn”的基础。
实际上 OLMod (ol-mod-olfinal) 本身就是 CODOL (title 1004) 的源码级本地服务器，且其自称进度**远超**该里程碑：

- 仓库自述: 用于恢复《使命召唤 Online》QA 客户端离线运行所需的控制面与游戏服务器链路 (README.md:3)。
- 六阶段链在 .agents/AGENTS.md:251 被声明为“已闭合”: 自然 mmstart -> client native selection/loadout capture -> backend entitlement -> dedicated SessionStart -> native assets/map/collision -> CCS -> gamestate accepted -> world spawn -> snapshots。
- 双真实客户端同局已在 docs/devlog/2026-08-14-dedicated-two-client.md:5-10 记录: dedicated 出现两个独立 client slot，两端 state=3 / gamestate_stage=6 / gameplay=1，snapshots 持续增长。
- HEAD 近期提交已推进到 Factory 僵尸、传送器、双持、合作复活等玩法层 (git log 3915fa9 起)。

=> “打通第一目标”这件事已由仓库自述完成。本报告的价值不在于重复实现，而在于核实其证据是否可复现。

### 前提错误 2 — OLMod 与 IW4X 无关

任务要求“优先复用 OLMod/IW4X 已有实现”。OLMod 不基于 IW4X：它是 CODOL 专有链路的源码重建（Project Nova / Ayria 组件 + 对 CODOL 客户端与 out.exe 的原生绑定）。
仓库内 IW4/BO1/BO2/Ghosts 的出现绝大多数是 CODREF/CODDIFF 形式的**跨版本反编译参照**（用于推断语义），不提供资产，也不构成兼容性证明。

但**存在 3 处真实的非 CODOL 资产/数据替代**，其中 2 处默认开启 —— 这与任务“禁止用 MW2/IW4X 资产替代 CODOL 资产”直接冲突，是本次审计最有行动价值的发现，见 §4.2。

### 前提错误 3 — 证据链在本机不可核验，且要求的 Golden Copy 不存在

- 所有里程碑证据都指向 .runtime/natural-match/<时间戳>/。该目录在 C:/D:/E:/F:/G: **全盘不存在**（.gitignore:4 也忽略它）[已核验]。
- 仓库内**没有** Golden Copy / 不可变基线 / 运行清单。最接近的产物是仓库外、会话工作目录中的 GOLDEN-LOBBY-001，且它**只冻结了大厅** [已核验]。
- 记录在案的“已验证”客户端 EXE 哈希与本机任何 EXE 都不匹配 [已核验]。

---

## 1. 审计范围与方法

| 子系统 | 主要依据 |
| --- | --- |
| Server Runtime | .agents/modules/runtime.md, game_server.md, xmake.lua, src/game_server/Appmain.cpp, FrameHook.cpp, server_mp/sv_main_mp.cpp |
| 网络层 / 握手 | src/localnetworking/**, src/game_server/qcommon/net_chan_mp.cpp, server_mp/sv_network_mp.cpp, win32/win_net.cpp |
| 地图加载器 | src/game_server/EngineBindings.cpp/hpp, Appmain.cpp, server_mp/sv_mapents_mp.cpp, sv_collision_mp.cpp |
| Zone/FF/Asset 管线 | docs/olfinal-fastfiles.md, tools/reverse/OlfinalFastfile.py, server_mp/sv_gamestate_mp.hpp, tools/runtime/Codol*Dump.py |
| Game State | server_mp/sv_snapshot_mp.cpp (1.39 MB), sv_native_playerstate_mp.cpp, sv_gamestate_mp.cpp |
| Lobby/Match 控制面 | .agents/modules/backend.md, .agents/pipelines/codol.dot, src/backend/** |
| 证据与哈希纪律 | tools/runtime/CodolNaturalMatchTrace.py, CaptureCodolState.py, CodolCaptureEvidence.py, tools/distribution/StageCodolRuntime.ps1 |

方法: 直接读取源码与磁盘证据；对文档声明一律标注 [文档声明] 并单独核验。未修改任何被审计文件。

---

## 2. 六阶段链的账面状态与证据缺口

.agents/pipelines/codol.dot 是仓库最诚实的进度表（working / partial / missing）。汇总如下：

| 阶段 | dot 评级 | 代表性运行目录 [文档声明] | 本次可核验性 |
| --- | --- | --- | --- |
| Lobby | working / natural | 20260809_rebuilt_platformwrapper_v1, 20260809_dest1yo_storage_persist_v5, 20260807_current_character_cache_fix_v1, 20260802_0651_clean_intro_command | 运行目录不存在 |
| Match (房间 ready) | **partial / synthetic** | — | 文档自述 SetReady(1) 本地回读不等于 backend ready ack (AGENTS.md:179) |
| Match (mmbook/mmstart) | working / natural | 20260808_dedicated_session_selection_v16, 20260812_sd_objectives_v7 | 运行目录不存在 |
| Match (结算持久化) | **missing** | — | — |
| Battle Server | working / natural | 20260808_dedicated_collision_world_v23_retry, 20260809_server_animation_clean_v18 | 运行目录不存在 |
| Handshake | working / natural | 20260731_233232/summary.json, 20260801_014234/summary.json | 全仓库仅这 2 个 summary.json 被具名引用，均不存在 |
| Map/Zone Load | partial / natural | 20260808_dedicated_collision_world_v23_retry (checksum 0xF7E89911) | 运行目录不存在 |
| Player Spawn / snapshot | partial / natural | 20260806_native_pmove_prod_v6, 20260803_client_spawn_v1, 20260810_stats_width_fix_v2 | 运行目录不存在 |
| Stable playable match | **GOAL (未达成)** | — | dot:39-44 |

关键事实:

1. [已核验] 全仓库仅 2 条 .runtime/.../summary.json 被具名引用（20260731_233232, 20260801_014234）；其余约 90 次引用只给目录名。
2. [已核验] C:/D:/E:/F:/G: 全盘不存在名为 .runtime 或 natural-match 的目录。方法已用 .git 交叉验证过滤器有效。
3. [已核验] 证据缺失是“不在磁盘上”，不是“被 gitignore 忽略了”。
4. [已核验] tools/reverse/catalogs/codol_server_function_matrix.json 自述 28 项中 partial=27 / missing=1，即服务端原语仍是受限子集。

=> 结论: 六阶段链的**实现确实存在于源码**（这一点很扎实），但**成功运行的证据链在本机完全不可核验**。任何“已验证”的说法在当前机器上只能当作文档声明。

---

## 3. 关键前置事实: 交接文档是过期的上游内容

[已核验] AGENTS-OLFINAL.md:5-13 明确写道:

- 该仓库里的 AGENTS.md 与 .agents/AGENTS.md 是 **dest1yo 的上游文档**，描述 3.3.3.3 时期的工作，最后改动 2026-08-16，为不与上游冲突而**刻意保持原样**。
- **完整项目交接在另一个仓库**: Downloads/CODOL-main/CODOL-main/AGENTS.md，运行日志 re/OLFINAL-FFA-HANDOFF.md §191ak。
- .agents/AGENTS.md:74 还把自身路径写为 E:\\codol_research\\ol-mod。

[已核验] 磁盘现状:

- C:\\Users\\Z7-CT5N1\\Downloads\\CODOL-main — 不存在。
- E:\\codol_research — 不存在。
- 在 Downloads、D:、E:、F:、G: (深度<=6) 搜索 CODOL-main / OLFINAL-FFA-HANDOFF.md — 均未找到。

=> 我读到的“当前 Handoff”是**过期的 3.3.3.3 上游状态**（2026-08-16 冻结），而 OLfinal-live 从 2026-09-29 到 10-02 的 Factory/僵尸提交并未反映在其中。真正的 live 交接文档不在本机。
=> 任何基于 .agents/AGENTS.md 的“当前状态”判断都必须降级为“上游历史状态”。

---

## 4. 与任务硬约束的冲突点

### 4.1 禁止用 MW2/IW4X 资产替代 CODOL 资产

任务明确禁止。审计发现 **3 处真实替代**（非参照、非注释）:

| # | 替代内容 | 来源 | 默认状态 | 证据 |
| --- | --- | --- | --- | --- |
| a | 僵尸导航图 (navgraph) | BO1 Der Riese 作为 donor | 关闭（opt-in） | server_mp/sv_zm_navgraph_bo1_hybrid_table_mp.cpp:1-6 自述 “BO1 Der Riese is a donor reference, not recovered CODOL aipaths”；需 OLMOD_ZM_NAV_SOURCE=bo1_hybrid 且通过地面/走廊校验，fail closed |
| b | 玻璃伤害阈值 | Ghosts 推得 | **开启** | Appmain.cpp:1394-1430: weaken=25, destroy=100，代码内含 TODO: 待 CODOL glass_map (type 17) 提供原生阈值后移除 |
| c | 可破坏物阶段数据（血量序列 + 替换模型名） | IW4 _destructible.gsc | **开启** | server_mp/sv_destructible_mp.hpp:99-106, sv_destructible_mp.cpp:11-19；仅对与 CODOL crash MapEnts 同名的 type 放行 |

另有第 4 处更彻底但属于“自研替代”而非“导入资产”: 整个脚本层被替换为项目自研 Lua VM（assets/game_scripts/*.lua，全局仅暴露 codol 对象），不执行 CODOL GSC。

未发现任何非 CODOL **二进制资产**被打包（树内无 .ff/.d3dbsp/.gsc/.iwi/.dds）。

=> 若严格执行任务禁令，(b) 与 (c) 是必须消除的默认开启项，且需要先取得对应 CODOL 原生数据来源。

### 4.2 CODOL 原始 FF/Zone/资产优先

[已核验] 地图数据确实来自原始加密 .ff: 插件驱动 out.exe 自带的 zone loader，不做自建解析。
但 FF 能力边界很窄:

- 唯一的容器代码是 tools/reverse/OlfinalFastfile.py，且**只按 out.exe build 1649370** 标定（RVA 0x8371A，密钥偏移 0x9AC4B0/0x9AC958）。
- 它只能**重打包**已序列化的 .zone body（pack_zone），**树内没有 zone body 编译器/反编译器**（OlfinalFastfileTests 只覆盖往返与损坏拒绝）。docs/olfinal-fastfiles.md:34-35 明确承认这是容器写入器，不是资产编译器。
- Tencent 签名私钥不在游戏中，工具**借用**任一已发行 .ff 的签名；运行时需 OLMOD_ALLOW_UNSIGNED_FASTFILES=1，默认关闭。
- 3.3.3.3 系列工具（CodolXAssetDump / CodolMapEntDump / CodolAssetEntryDump / CodolGlassAssetDump）使用**另一套 RVA**，与 1649370 路径不可混用。

=> 想自制/修改地图资产，目前是硬阻塞: 缺 zone body 编译器。

### 4.3 协议字段必须由客户端静态/运行时证据确认

仓库在这方面纪律很强（CODREF/CODDIFF/OLMOD/TODO(CODOL) 标记体系 + 证据等级 + 可校验 catalog），这是 OLMod 最大的工程优点。
但同一约束也意味着: **没有匹配的客户端二进制，就无法新增任何协议字段确认**。见 §5.2。

---

## 5. 硬阻塞项（必须先解决，否则任何阶段都无法推进或验证）

### 5.1 游戏目录缺失 [已核验]

- config/codol-game-dir.txt 指向: D:\\codo_3.19.26.13_fresh\\CoD Online
- 该目录**不存在**。
- 后果: 无法运行 dedicated/client，无法做 zone/FF 全量索引，无法复现任何 natural-match 运行。

### 5.2 客户端 EXE 构建不匹配 [已核验]

仓库记录的“已验证”哈希:

- active 3.3.3.3: E3823FD6AFC80FB25FA84747E6E9634707B9A0B189357A5466921CDA354AF37B
  (记录于 .agents/AGENTS.md:174, game_server.md:330, 以及 4 个 tools/runtime 工具里作为强制校验常量)
- patched/ 候选: 9E283099240521E55D152B5DBE035B28F6E090C98A0ED80E807D914CB4B666F9 (仅 AGENTS.md:174)

本机实测: 全盘共找到 **41 份** codoMP_client_shipRetail.exe，但只有 **2 个不同构建**:

| SHA-256 | 份数 | 示例 |
| --- | --- | --- |
| 36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537 | 40 | D:\\BaiduNetdiskDownload\\codoMP_client_shipRetail.exe |
| 7B31168D42A5A6BA11750D404971EE52F9FD1CAB93C56A8A85DA94AE76C41342 | 1 | D:\\...\\工具\\EXPERIMENT_017_BOOT_SKIP\\codoMP_client_shipRetail.exe |

**两者都不匹配**任何记录值。

后果（严重）:
- 计划的“通过客户端静态/运行时证据确认协议字段”**无法执行** —— 反汇编地址、netfield 表、patch 偏移全部绑定到特定构建。
- 任何用现有构建跑出的结果都不能与前例证据比较，也不能提升证据等级。
- 同理，docs/olfinal-fastfiles.md 依赖的 out.exe (build 1649370) 在本机也未找到。

### 5.3 Golden Copy 纪律未实现 [已核验]

任务要求: “第一次进入战斗地图后立即创建不可变 Golden Copy，不允许继续修改该成功版本。”

仓库现状:
- 不存在任何名为 golden / immutable baseline / run-manifest 的产物。
- 不存在“进入战斗地图”对应的冻结基线。
- 已存在的哈希纪律都是**分发/安装**或**单轮运行**范围，不是里程碑基线:
  - distribution/runtime-components.json: 4 个归档遗留组件的哈希 + 资产目录哈希映射。
  - tools/distribution/StageCodolRuntime.ps1:64-77,154-164: 生成 build/stage/codol/ol-mod-runtime-manifest.json（每文件 path/size/sha256/source/kind/role/installPolicy）。build/ 不存在。
  - tools/runtime/CodolNaturalMatchTrace.py:435-442: 冻结单轮 input_scenario + sha256（仅输入不可变性）。
  - tools/runtime/CodolCaptureEvidence.py: 单轮 raw sample 完整性校验。

仓库外、**会话工作目录内**存在唯一实际的 golden:

- D:\\BaiduNetdiskDownload\\使命召唤OL\\GOLDEN-LOBBY-001\\REF_LOBBY_KIT\\
- _golden_hashes.json 冻结 9 个文件；本次**独立核验 9/9 哈希与字节数全部匹配**。
- 但它属于**另一个（旧的 Python）项目**，且自述范围只有 “正式进入 Lobby + KeepAlive 稳定运行”，其 battle_srv.log 记录收包=0（未进对局）。

=> 即: 任务要求的 “进入战斗地图后的不可变 Golden Copy” **从未被创建**。这是应当在下一阶段立即补齐的机制。

### 5.4 真实 live 交接文档缺失 [已核验]

见 §3。继续按 .agents/AGENTS.md 推进会基于 2026-08-16 的过期状态做决策。

---

## 6. 各子系统审计要点（源码级）

### 6.1 Server Runtime

- [已核验] **没有独立 dedicated 可执行文件**: “dedicated” 就是同一个宿主 EXE 的第二实例，靠 OLMOD_PROCESS_ROLE=dedicated 由 src/shared/ProcessRole.hpp:17-50 分派角色。
- [已核验] 构建目标 (xmake.lua): ol_localnetworking:140-149, ol_platformwrapper:151-160, ol_backend:162-171, ol_room_owner:173-189, ol_game_server:191-212, ol_deploy:214-243 + 7 个测试套件。
- [已核验] 入口/主循环: Com_Frame RVA 0x0FEA20 上的 5 字节 E9 detour (FrameHook.cpp:22-73) -> onServerFrame (Appmain.cpp:6437)，分 8 个阶段；有帧停滞看门狗线程 (:6401-6435)。
- [已核验] 调度: FixedFrameScheduler 每个宿主回调**至多执行一个 world frame**，残余钳制 500ms (sv_main_mp.cpp:1119-1164)。
- [已核验] **节拍与文档不一致**: SV_FrameMilliseconds() 默认 fallback = 100 ms (sv_main_mp.cpp:1074)，即可由 OLMOD_SV_FRAME_MS 覆盖的 **10 Hz**；而 game_server.md:318/526 仍写 “20 Hz”。
- [已核验] 线程模型: 权威玩法全部跑在引擎主线程；**没有独立服务器线程** (sv_main_mp.cpp:1149-1153 显式 CODDIFF(sv_frame))。控制面是独立 TCP accept 线程，只解码并投递到 mutex 保护队列，由帧线程排空。
- [已核验] 关闭: 无有序 teardown；DllMain 只处理 PROCESS_ATTACH；控制服务器被刻意泄漏以避免 loader lock 下 join (Appmain.cpp:289-291)。

### 6.2 网络层与握手

- [已核验] 分层: Winsock 重定向 (src/localnetworking/WinsockHooks.cpp, 25.6 KB) -> UDP/win32 (server_mp/sv_network_mp.cpp, win32/win_net.cpp) -> DTLS (qcommon/net_dtls_cod.cpp) -> netchan (qcommon/net_chan_mp.cpp: Netchan_Process:660 / Transmit:1012 / TransmitNextFragment:1061) -> msg 编解码 (qcommon/msg_mp.cpp) -> 快照。
- [已核验] 控制面端口: dedicated control 28961，client bridge 28962，room owner 28970；玩法 UDP 默认 28960，实际端口来自 session descriptor。
- [已核验] 握手链: ConfigureSession(带外) -> DTLS -> OOB getchallenge -> connect -> stats -> gamestate -> gamestateupdate 1..6 -> 快照；generation-scoped pending->active roster，非 roster XUID 被拒绝 (sv_client_mp.cpp:3384-3515)。
- [已核验] DTLS 细节: NAT intro 0x0D->0x0C；INIT 0x01/INIT_ACK；COOKIE_ECHO 0x03->COOKIE_ACK 0x04 (地址自动长度: 67B 长 -> 219 总长，或 37B 短 -> 189)；DATA 0x06 用 HMAC-SHA1 + AES-128-CTR (AES-ECB 作 keystream)，secp224r1 ECDH，28B 共享材料 + 16B security key = 44B，再由 SHA1(44B) 派生 aesKey/hmacKey/IV。重放窗口: delta 0 或 >=0x8000 拒绝。
- [已核验] 证据分级（这正是任务要求的纪律）: DTLS INIT/INIT_ACK/COOKIE_ECHO/DATA、getchallenge 明文、stats 上传、gamestateupdate 字符串、首个 netchan 包均为 **[CODOL 已确认]**（有捕获字节/测试向量）；而 connect 报文中的 name/rank/natType/statver/secureProfileReady 等 userinfo 键**只存在于手工构造的 fixture** (ServerCoreTests.cpp:240-250)，属 **[参考/假定]**，仓库内没有捕获的原始 connect 字节。
- [已核验] 已知修正（CODOL 锚定，推翻过早期假定）: 服务端 EOF 操作码是 5 而非 3.3.3.3 的 6；客户端 move 流必须以 client-EOF 3 结尾；usercmd delta 基线是 snapshot/default usercmd 而非上一包命令；weapon index delta 位宽 10 -> 11；fragment 头从 qport/start/length 改为 index/last/stride/length @1154；reliable fragment 从 fire-and-forget 改为 selective repeat。
- [已核验] 文档记录了 2026-08-15 对 Netchan_Setup/TransmitFragment/Transmit/Process 的复核，推翻了旧的 qport+fragment 方案 (game_server.md:356) —— 这正是“不得因 IW4X 相似就假定兼容”纪律的正面例子。
- [已核验] **全仓库没有任何 PCAP / 抓包工具**: grep pcap / wireshark / WinPcap / Npcap / scapy / dpkt / packetlog = 0 命中。任务要求的 “PCAP/协议记录” 中，PCAP 目前完全没有实现路径。
- [已核验] 现有协议记录形式: Frida 进程内 netchan tracer 输出 JSONL (references/client_probe/CodolNetchanTrace.py，hook 了 CL_ParseServerMessage 0x46E6A0 / CL_ParseGameStateMessage 0x46DEA0 / CL_ParseSnapshot 0x46D170)；Winsock 边界文本日志 Logs/Localnetworking.log；服务端 udp packet 日志 (sv_network_mp.cpp:72-83)。
- [已核验] 当前最强的协议证据是**已提交的字节级 fixture**: tests/game_server/ServerCoreTests.cpp:27314-27391 (DTLS data/plaintext/HMAC、NAT intro、INIT/INIT_ACK、COOKIE_ECHO/COOKIE_ACK) 与 :27502-27503 (首个 client netchan 包)；另有 getchallenge 明文 fixture :27325-27328。

### 6.3 地图加载器

- [已核验] 加载链: beginLevelZoneLoad -> 原生 LevelZoneLoadRva 0x09E600 -> 轮询 IsZoneLoadedRva 0x09F180 -> initializeLevelWorld 找 ClipMapMp/Sp (type 15/14) maps/mp/<map>.d3dbsp -> 原生 CollisionMapLoad 0x262D90 + CollisionWorldLink 0x269A40 -> 要求 ComWorld (type 16) -> CCS reset/init -> 延迟 world spawn。
- [已核验] 地图带脚本绑定: <exeDir>\\Ayria\\Assets\\OlMod\\GameScripts\\{common.lua, gametypes/<gt>.lua, maps/<map>.lua}。
- [已核验] 重要区分: ?N (MapEnts.trigger) 与 *N (clipmap cmodel) 是**不同数组**，互相路由会拿到无关 brush (Appmain.cpp:4524-4533)。
- [已核验] brush producer: SV_SelectBrushModelSpawns 只收 classname==script_brushmodel；resolveBrushModelCollision 读 CollisionMap +0x90/+0x94，72 字节 stride；经 SV_LinkBrushModelCollisionEntity -> 原生 SV_LinkEntity 发布。
- [已核验] 已知缺口: 缺 CODOL gentity in-use / SVF_NOCLIENT producer，用 source 侧 eligibility 策略替代 (Appmain.cpp:5474-5476)。
- [已核验] 源码注释自相矛盾: Appmain.cpp:3897-3899 称 base MP entity string 不在任何 244 个 fastfile 中，而 EngineBindings.cpp:4588-4593 称 mp_nuked zone 携带该 .d3dbsp。运行时因为直接读已加载引擎资产所以不受影响。

### 6.4 Zone/FF/Asset 管线

- [已核验] 容器格式（按 out.exe 1649370）: 外层 IWff0100 v461，header 0x115；RSA-2048 PKCS#1 v1.5 解出 40 字节 AES-192 key+IV；内层 IWffs100 block zero（签名在 44，zone name 在 300，L1 SHA-256 表在 336 / 244 项）；AES-CTR 小端、每 0x2000 块重置计数器；zlib level-1；上限 244*256*0x2000 = 512 MiB。
- [已核验] XAsset 枚举双路径: DB_FindXAssetHeader 0x09CF30 按名查；或直接走 28 字节 XAsset entry 表 (VA 0x239B120, 120000 行)。后者存在的原因: 按名查找会阻塞在 streaming 事件上。
- [已核验] CCS 全局: checksum 0x73D8240 / initialized 0x73DB42C / per-index type 字节数组 0x73D8250；原生 CCSClear 0x261610 / CCSInitialize 0x261A30 / CCSGetConstantString 0x261C50。
- [已核验] configstring 分段: models 2568+1024, anim 7669+4096, effects 4136+400, sound 3624+, server materials 4872+1024, weapons 5960+1700, names 2452+18, vision 2557-2562。
- [已核验] 动态槽区: firstDynamicWeaponAssetIndex 扫描 type 数组到哨兵，再走原生注册表 0x7E7F738 到首个 “** ...” modular 条目；完整 CCS 的 weapon 表占 1..351，352+ 才是服务器动态区。

### 6.5 Game State

- [已核验] 状态模型: SvGameClient 持有严格尺寸的 native playerState buffer；SvGameEntity 持有完整 native entityState；**尺寸是本构建特定的** —— 本 OLfinal 构建 playerState_s = 0x3BBC、entityState_s = 0x118，而常见引用的 0x3564 / 0x110 属于 3.3.3.3 / OL.exe 参考构建 (sv_native_playerstate_mp.hpp:23,34; sv_native_entitystate_mp.hpp:32-36)。这再次说明跨构建假定 ABI 是错的。双向 overlay 只覆盖已确认字段，未知字节跨同一生命保留，并随完整候选事务回滚。
- [已核验] wire: 完整 + 增量快照、baseline/ack 历史、235 条 playerstate descriptor（每 12 字节）、changeHint==2 的 second-pass marker、auxiliary sections、严格升序要求、overflow 守卫。
- [已核验] usercmd 链: received -> pending queue -> dispatched -> candidate game current/old + playerState -> executed queue-front commit；失败回滚候选。spawn 当帧不执行 command。
- [已核验] 已知缺口（仓库自述）: 首条 SV_ClientEnterWorld oldcmd 基线未知；+20000 ms / G_SetLastServerTime 未移植；penetration 后续反向 trace/深度衰减仍 DeferredImpact。

### 6.6 Lobby/Match 控制面 (backend)

- [已核验] 完整 booking 链 (backend.md:25-41): room request -> service 0x0B -> event 8 push -> local ready -> service 0x15 task 5 kind 1 FIND_SERVERS -> service 0x06 task 14 mmbook -> event 21 -> task 14 mmstart -> BookingSink -> DedicatedBookingDispatcher -> client bridge capture -> entitlement -> SessionStart -> dedicated 解析。
- [已核验] 明确约束: query kind 1 = FIND_SERVERS，kind 3 = FIND_LOBBIES_BY_PLAYLIST；**不得把玩家自建 lobby 当作 server 返回** (backend.md:43)。
- [已核验] 身份: backend PlayerIdentityStore 按 1004/<USERID>/Identity.json 持有 displayName；Matchmaking 的 Session.Demonware 是客户端状态机拥有的 opaque descriptor，**不得用 backend 名字重写**（2026-08-09 实机证明改名后加入房间会持续等待）。
- [已核验] 多客户端共享房间是**当前主要缺口**: backend.md:55-60 明说当前 backend 不能让两个真实客户端加入同一个控制面房间；schema v5 已能编码成员数组，SharedRoomSessionOwner 已建立，但 dispatcher 尚未接入多 bridge capture。
- [已核验] 证据等级实例: backend.md:49 的记录诚实标注 “客户端尚未连接 dedicated，session_configured/transport_bound 与 gameplay packet 均为零”。

---

### 6.7 文档与源码数值不一致（已核验，系统性）

审计发现文档声明与当前分支源码常量存在**系统性偏差**，独立印证了 §3 的“上游文档已过期”结论。凡后续工作以文档数值为实现依据都会出错:

| 项 | 文档声明 | 源码实际 | 位置 |
| --- | --- | --- | --- |
| 服务端帧率 | 20 Hz (50 ms) | 默认 100 ms = **10 Hz**（OLMOD_SV_FRAME_MS 可覆盖） | sv_main_mp.cpp:1074 |
| 客户端 slot 超时 | connecting 80s / active 240s | connecting **45s** / active **15s** | sv_client_mp.hpp:457-461 |
| playerState_s | 0x3564 | 本构建 **0x3BBC**（0x3564 属 3.3.3.3/OL.exe） | sv_native_playerstate_mp.hpp:23,34 |
| entityState_s | 0x110 | 本构建 **0x118** | sv_native_entitystate_mp.hpp:32-36 |
| playerstate netfield 条数 | 235 | 抽取结果 **246**（235 vs 246 未解决） | ClientCommandTrace.hpp:45 vs sv_snapshot_mp.cpp:3336 |
| 快照节拍 | 文档称已恢复的契约 | **硬编码 50 ms 常量**，LAN 直接旁路，属 [SRC] 非 CODOL dvar | sv_client_mp.cpp:1418-1427 |

=> 结论: **不得以 .agents 文档中的数值作为实现依据**，必须以本分支源码常量为准。这也直接证明了任务中“所有协议字段必须由证据确认”的纪律必须同样适用于文档自身。

---

## 7. 建议的下一阶段方案

前提: 在 §5 的阻塞项解决前，任何“新建 CODOL 战斗服务器”的编码工作都无法被验证，且大概率重复 OLMod 已有实现。
因此建议按以下顺序，且**每一步都以可核验产物收尾**。

### 阶段 A（可在本机立即执行，无需游戏目录）— 建立可核验基线与纪律

A1. 确认/更正权威交接来源: 定位 CODOL-main 与 OLFINAL-FFA-HANDOFF.md §191ak。若确不存在，则明确将 .agents/AGENTS.md 标注为 upstream-historical，并在 OLMod 内建立新的 fork 交接入口。
A2. 建立 Golden Copy 机制（任务硬要求，当前完全缺失）: 冻结“首次进入战斗地图”的完整运行产物（源码 commit、构建物、配置、session descriptor、snapshot trace、日志、截图），生成逐文件 SHA-256 清单并设为只读。可直接复用现有 StageCodolRuntime.ps1 的 manifest 模式与 _golden_hashes.json 的格式。
A3. 建立证据归档规范: 现有 .runtime 被 gitignore 且未留存，导致所有历史声明不可核验。建议为每次里程碑运行生成不可变归档（含 summary.json + 逐文件哈希），否则历史结论会持续不可复现。

### 阶段 B（需要匹配的客户端与游戏目录）— 恢复可复现性

B1. 取得与 E3823FD6... 匹配的 3.3.3.3 客户端（或重新标定现有构建的全部 RVA/偏移，工作量极大且会废弃现有工具常量）。
B2. 恢复 config/codol-game-dir.txt 指向的真实游戏目录。
B3. 跑通一次 natural-match 并产出首个可核验 summary.json，与文档声明对照。

### 阶段 C（可选，取决于阶段 B 结果）— 补缺口而非重写

若目标是“打通第一目标”，则它已由 OLMod 实现，阶段 C 应改为按 codol.dot 的真实缺口推进:
C1. 共享 backend room owner 与多成员 booking（唯一能解锁两个真实客户端自然同局的路径）。
C2. 消除默认开启的非 CODOL 替代: Ghosts 玻璃阈值 (Appmain.cpp:1394-1430) 与 IW4 可破坏物数据，改为从 CODOL glass_map (type 17) / CODOL 定义恢复。
C3. zone body 编译器（若需要自制地图资产）。

---

## 8. 附录: 本次核验的哈希与路径清单

### 8.1 被审计仓库

| 项 | 值 |
| --- | --- |
| 仓库 | F:\\桌面\\ol\\ol-mod-olfinal |
| 分支 | OLfinal-live |
| HEAD | 3915fa9 Restore Factory teleporter links and staged return travel |
| 工作树 | 干净 |

### 8.2 记录的客户端 EXE 哈希 vs 本机实测

| 来源 | SHA-256 | 本机是否存在 |
| --- | --- | --- |
| 记录 active 3.3.3.3 | E3823FD6AFC80FB25FA84747E6E9634707B9A0B189357A5466921CDA354AF37B | 否 |
| 记录 patched 候选 | 9E283099240521E55D152B5DBE035B28F6E090C98A0ED80E807D914CB4B666F9 | 否 |
| 本机构建 #1 (40 份) | 36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537 | 是 |
| 本机构建 #2 (1 份) | 7B31168D42A5A6BA11750D404971EE52F9FD1CAB93C56A8A85DA94AE76C41342 | 是 |

### 8.3 GOLDEN-LOBBY-001 独立核验（9/9 匹配）

| 文件 | SHA-256 | 字节数 |
| --- | --- | --- |
| battle_selftest.py | 06b8b5a8b32586cf066ec2c76650c3df28841acdeef56639fbdbd3f88d1a4ef5 | 20145 |
| battle_server.py | 71bb7beb85e514082b91a4925d18cb09fd07d5e8916ffa7f4fbd4a9750b47274 | 69019 |
| codol_crypto.py | e836c63af75dd82ef6f3b07ef63fae48b044b3b5047336127093c92b07644607 | 42853 |
| fake_auth_tls.py | e638e96fe420d66d1d52c26f3e413a15126818e4491ae30196a806cbcdd265be | 10347 |
| lobby_server.py | d7eeb4564af05f4c71fb3391112a8bf592b74f0aa12dec8f286b927ae046c2cf | 76410 |
| make_local_ca.ps1 | f89e314e717a38a393fd31ea9bd0dbf69648f682d7fe14b000c68fc764dfe103 | 6607 |
| marketplace_store.py | 28b4a1be67de06f41e789e723f8befecf1ea5ac7b2a3ca20cfef557a6f571a16 | 46226 |
| nt10.py | 05863ebafc7d7bb3820cce057bc9e4e0ea07816945ca03e38a9bbfecacab22f8 | 169491 |
| run_all.py | 2aaa8847f112d926b996e5fd38dd26b697adc0697c45781f520940a8256ecda6 | 31507 |

注: 该 golden 属旧 Python 项目（会话工作目录内），范围仅 Lobby；battle_srv.log 收包=0，未进对局。

---

## 9. 审计纪律声明

- 本次审计全程只读，未修改 F:\\桌面\\ol\\ol-mod-olfinal 内任何文件。
- 凡未能直接核验的结论均标注 [文档声明]，未与 [已核验] 混同。
- 未调查已关闭的 WeGame / TCLS / IIPS / 启动器路线。
- 本报告未对 OLMod 做任何“重复实现”性质的改动建议；所有建议均为补齐证据与消除违规替代。
