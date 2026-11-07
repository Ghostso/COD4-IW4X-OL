# EVIDENCE_STATUS — OLMod 证据状态审计（2026-10-09）

被审计仓库: F:\\桌面\\ol\\ol-mod-olfinal
分支: OLfinal-live
HEAD: 3915fa9813be7255d7031c307d31ad12043dfbd4
HEAD 日期: 2026-10-02T09:41:50-05:00
审计时工作树: 干净（git status --porcelain = 0 行，stash = 0，untracked = 0，tracked = 627）
审计性质: 只读。除本审计包（.agents/audits/2026-10-09/）为新增文件外，未改动任何既有文件。

---

## 1. 环境事实（先于一切证据判断）

### 1.1 构建/测试工具链：完全缺失

在 C:\\Program Files、C:\\Program Files (x86)、D:、E:、F:（深度 3-4）全盘搜索后确认:

| 工具 | 状态 |
| --- | --- |
| xmake | 不存在（PATH 无，文档记载的 D:\\Program Files\\xmake 与作者路径均无） |
| MSVC (cl.exe) | 不存在；vswhere.exe 也不存在，即无任何 Visual Studio 安装 |
| vcpkg | 不存在；VCPKG_ROOT 为空 |
| cmake / ninja | 不存在 |
| build/ 目录 | 不存在 |
| Python 3.11 / py / git | 存在 |

=> 后果: **任何需要编译或运行测试的目标（7 个测试套件、ol_game_server 构建）在本环境为 INSTRUMENTATION_BLOCKED。** 仓库内的协议 conformance 测试无法被实际执行验证。

### 1.2 客户端与游戏目录：不匹配 / 缺失

| 项 | 记录值 | 本机实际 |
| --- | --- | --- |
| 已验证 3.3.3.3 客户端 SHA-256 | E3823FD6AFC80FB25FA84747E6E9634707B9A0B189357A5466921CDA354AF37B | 不存在 |
| patched 候选 SHA-256 | 9E283099240521E55D152B5DBE035B28F6E090C98A0ED80E807D914CB4B666F9 | 不存在 |
| 本机客户端副本 | — | 41 份，仅 2 个构建: 36997674... (40 份) / 7B31168D... (1 份)，**均不匹配** |
| 配置游戏目录 config/codol-game-dir.txt | D:\\codo_3.19.26.13_fresh\\CoD Online | 不存在 |
| out.exe (OLfinal, build 1649370) | FF 工具与大量 RVA 绑定此构建 | 不存在 |

=> 后果: 所有绑定具体构建的 RVA、netfield 表、patch 偏移与客户端 parser 地址（如 CL_ParseServerMessage 0x0046E6A0 等）**在本机无法复核**；也无法产生任何新的客户端静态/运行时证据。

### 1.3 运行时产物：全盘为空

对 D:、E:、F:、G: 全盘扫描（1,125,752 个文件）后，以下 OLMod 运行产物**全部 0 命中**:

netchan_trace.jsonl / server_samples.jsonl / frame_trace.jsonl / frame_trace.summary.json /
input_scenario.snapshot.json / dedicated_asset_trace.jsonl / viewmodel_trace.json /
cbuf_commands.jsonl / ol-mod-processes.json / ol-mod-runtime-manifest.json /
CodolGameServer.log / AlwaysofflineRe.Localnet32.log / Localnetworking.log / client-commands.csv / client-ps.csv

目录 .runtime / natural-match: **0 命中**。仅有的 Ayria 目录是仓库自带的 distribution/legacy/Ayria（分发组件），不是已安装的运行目录。

=> 结论: **OLMod 在本机上不存在任何原始运行产物。** 所有 .runtime/natural-match/<时间戳>/ 引用（含仅有的两条具名 summary.json: 20260731_233232、20260801_014234）均为外部证据，本机不可核验。

### 1.4 仅有的外部工件属于另一个（已关闭路线的）项目

| 类别 | 数量 | 位置 | 归属 |
| --- | --- | --- | --- |
| summary.json | 15 | D:\\BaiduNetdiskDownload\\使命召唤OL\\CODOLServer\\archive\\CONFIRMED_2026 0928_* 等 | 旧 Python/C# 项目，**非 OLMod** |
| pktmon.pcapng | 5 (1.6 MB - 115 MB, 2026-09-24/25) | D:\\...\\使命召唤OL\\run_codol_001\\runs\\{ENTRY_CAPTURE_ELEVATED,LOBBY_DEEP,TCLS_DIR}_* | 旧项目 / 已关闭路线 |

说明: 这些**不作为 OLMod 的证据**。记录它们只是为了说明“本机确实存在抓包能力（Windows 自带 pktmon）与旧项目产物”，供 GOLDEN_COPY_SPEC 参考格式；本任务按要求**不重新调查** WeGame/TCLS/IIPS/启动器路线。

---

## 2. 证据等级定义（本次使用）

| 等级 | 含义 |
| --- | --- |
| CONFIRMED | 本次直接核验的一手证据：源码常量/断言、仓库内已提交的字节级 fixture、或我独立完成的测量 |
| STRONG_CANDIDATE | 多个一致的仓库内一手来源支持，但无捕获工件或外部验证 |
| CANDIDATE | 单一仓库内来源，或文档声明与源码一致 |
| UNKNOWN | 信息不足 |
| REFUTED | 被一手证据否定 |
| NOT_OBSERVED | 需要运行产物才能成立；本机不存在该产物，从未被观测到 |
| INSTRUMENTATION_BLOCKED | 因缺少必要条件（编译器/游戏目录/匹配客户端）而**无法测量** |

---

## 3. 主链证据矩阵: mmstart -> SessionStart -> CCS -> gamestate accepted -> world spawn -> snapshots

| # | 阶段 | 文档声明（位置） | 源码位置 | 磁盘运行产物 | 与当前 HEAD/客户端哈希/构建匹配 | 可否在本环境复现 | 证据等级 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | mmbook -> event 21 -> mmstart -> BookingSink | backend.md:32-35；AGENTS.md:141 | src/backend/DedicatedBookingDispatcher.cpp；Servers.cpp:407 日志串 CODOL_GAME_BOOKING | 无 | HEAD 匹配（源码存在）；客户端不匹配 | 否 | NOT_OBSERVED（实现存在: CONFIRMED） |
| 2 | dispatcher 捕获 native selection/loadout | backend.md:37-38 | src/client_bridge/ClientSessionBridge.cpp；shared/DedicatedSession.cpp | 无 | HEAD 匹配；客户端不匹配 | 否 | NOT_OBSERVED |
| 3 | entitlement 校验 | backend.md:38,51 | src/backend/**（inventory + CODOL_ItemAvailability_Query 0x695BC0 依据） | 无 | 客户端不匹配（0x695BC0 无法复核） | 否 | NOT_OBSERVED |
| 4 | SessionStart v5 多成员 | backend.md:62-65；AGENTS.md:255 | shared/DedicatedSession.cpp/.hpp (20,385 B) | 无 | HEAD 匹配 | 否 | NOT_OBSERVED |
| 5 | SessionStart -> level-zone load | game_server.md:227-247；AGENTS.md:212 | Appmain.cpp:2527-2592；EngineBindings.cpp:4525-4550 (LevelZoneLoadRva 0x09E600 / IsZoneLoadedRva 0x09F180) | 无 | RVA 绑定本机不存在的构建 | 否 | NOT_OBSERVED + INSTRUMENTATION_BLOCKED |
| 6 | CM_LoadMap + CM_LinkWorld | game_server.md:271-275；checksum 声明 0xF7E89911 | EngineBindings：CM_LoadMap 0x00585B20 / CM_LinkWorld 0x0058C810；Appmain.cpp:2573-2591 | 无 | 同上 | 否 | NOT_OBSERVED + INSTRUMENTATION_BLOCKED |
| 7 | CCS reset/init + live checksum | game_server.md:277；AGENTS.md:158 | sv_gamestate_mp.cpp；sv_playlist_mp.cpp:244-270 observeConfigStrings | 无 | 同上 | 否 | NOT_OBSERVED |
| 8 | gamestate accepted（客户端上报 gamestateupdate 6） | game_server.md:314；AGENTS.md:172；devlog 2026-07-31:47 | sv_client_mp.cpp:558-641；SV_WriteGameState sv_gamestate_mp.cpp:949-995 | 无 | 客户端 parser 地址无法复核 | 否 | NOT_OBSERVED + INSTRUMENTATION_BLOCKED |
| 9 | world spawn | game_server.md:526,530；AGENTS.md:144 | sv_client_spawn_mp.cpp:206-412；Appmain.cpp:5840-5873 (drop-to-floor) | 无 | RVA 绑定本机构建不存在 | 否 | NOT_OBSERVED + INSTRUMENTATION_BLOCKED |
| 10 | 持续 snapshot（声明 1201 条 / ~19.97 Hz / accepted 1743 / rejected 0） | AGENTS.md:145（唯一具名 summary.json 之一） | SV_WriteSnapshot sv_snapshot_mp.cpp:10082；节拍 sv_client_mp.cpp:1424-1426 | 无 | 无法核验该 summary.json | 否 | NOT_OBSERVED + INSTRUMENTATION_BLOCKED |
| 11 | 两个真实客户端同局 | docs/devlog/2026-08-14-dedicated-two-client.md:5-10 | sv_client_mp.cpp roster；shared/SharedRoom* | 无 | 需要匹配客户端 x2 | 否 | NOT_OBSERVED + INSTRUMENTATION_BLOCKED |

**总判定: 上述 11 项在源代码层面均有实现（这一点由本 HEAD 源码直接证实），但没有任何一项在当前环境存在可核验的运行证明。文档中出现的成功数字（1201 / 1743 / 1212 / 19.97 Hz / 0xF7E89911）全部不可复现。**

---

## 4. 被一手证据否定的文档声明（REFUTED）

| # | 文档声明 | 位置 | 一手证据 | 结论 |
| --- | --- | --- | --- | --- |
| R1 | server frame 以 20 Hz 编排 | game_server.md:318、:526 | sv_main_mp.cpp:1074 fallback = 100 (10 Hz)；:1061-1074 注释明确说明“默认仍为 50?? 不，默认保持 100 是因为测试套件编码了 50 ms 时间线” | REFUTED（默认实现是 100 ms = 10 Hz；50 ms 需 OLMOD_SV_FRAME_MS 显式设置） |
| R2 | 客户端 slot 超时 connecting 80s / active 240s | game_server.md:496 | sv_client_mp.hpp:457-461 = connecting 45s / active 15s | REFUTED（文档数值过期） |
| R3 | playerState_s = 0x3564 | 见任务上下文；早期报告 | sv_native_playerstate_mp.hpp:17-23 注释: 0x3564 是 3.3.3.3 的 per-client image，本构建是 0x3BBC（0x77780/32），旧尺寸比引擎认为拥有的少 1624 字节 | REFUTED（本构建用 0x3BBC） |
| R4 | entityState_s = 0x110 | 同上 | sv_native_entitystate_mp.hpp:32-36 = 0x118 | REFUTED（本构建 0x118） |
| R5 | playerstate descriptor 表 235 条 | sv_snapshot_mp.cpp:3336 注释 | 抽取出的 netfield 表为 246 条（ClientCommandTrace.hpp:45） | 未解决冲突（235 vs 246），至少一方有误 |

注 R1 需精确表述: 源码 sv_client_mp.cpp:1424-1426 的快照节拍确实是 50 ms（20 Hz）且带显式 TODO(CODOL)，属 [SRC] 而非已恢复的 CODOL dvar 契约；而 game_server.md:318/:526 把它描述为 server frame 的 20 Hz 编排，与 sv_main_mp.cpp 的 100 ms 默认 frame 冲突。二者是**两个不同的率**，文档把它们混为一谈。

---

## 5. 本次 CONFIRMED 的一手证据（仓库内可核验）

| # | 事实 | 证据 |
| --- | --- | --- |
| C1 | 捕获的 CODOL DTLS DATA 包字节、HMAC 校验与 AES-CTR 解密结果 | tests/game_server/ServerCoreTests.cpp:27314-27336（sharedMaterial 44B、verificationTag 0x855C、seq 1、encryptedSize 38） |
| C2 | 捕获的 getchallenge 明文: FF FF FF FF "getchallenge 0 \"01100001deadc0de\"" | ServerCoreTests.cpp:27325-27328（可直接人工解码核对） |
| C3 | NAT intro 0x0D -> 0x0C 的精确回复字节 | ServerCoreTests.cpp:27338-27348 |
| C4 | 捕获的首个客户端 netchan 包 010000000000000000000000008C 解码为 seq=1/serverId=0/acks=0/commands=0x03 | ServerCoreTests.cpp:27502-27517 |
| C5 | 服务端 EOF 操作码在本构建为 5（3.3.3.3 为 6）: 捕获字节 0x88 vs 本构建 0x8B，异或差恰为 3 | ServerCoreTests.cpp:27546-27555（注释内含 CODDIFF(1649370) 推理） |
| C6 | 测试语料规模: ServerCoreTests.cpp 31,527 行 / 2,550 处 require( / 102 处 fromHex( | 本次直接计数 |
| C7 | 全盘无任何 OLMod 运行产物 | 本次全盘扫描（1,125,752 文件） |
| C8 | 本机 41 份客户端 EXE 无一份匹配记录的已验证哈希 | 本次独立 SHA-256 计算 |
| C9 | 仓库内无 Golden Copy / 不可变基线 / 运行清单 | 本次搜索 |
| C10 | 仓库内无任何 PCAP/抓包工具（grep = 0） | 本次搜索 |
| C11 | 构建工具链完全缺失 | 本次全盘搜索 |

重要限定: C1-C5 是**协议一致性**证据（wire 布局/加密/命令字节），等级为 CONFIRMED，但它们**不构成 gameplay 运行验证**。它们证明“字节解释正确”，不证明“自然对局跑通”。

---

## 6. NOT_OBSERVED 与 INSTRUMENTATION_BLOCKED 的区别（避免混淆）

- NOT_OBSERVED: 该结论本可在别处被观测到，但本机没有对应产物（例如所有 .runtime 运行结果）。它不代表结论为假，只代表**未观测**。
- INSTRUMENTATION_BLOCKED: 本机**缺少产生该证据的必要条件**，因此连尝试都不可能（缺编译器 -> 无法跑测试；缺游戏目录/匹配客户端 -> 无法跑对局）。

本审计中，主链 11 项同时具备两者性质：既无产物，也无法现场产生。

---

## 7. 提升证据等级所需的最小条件

| 目标 | 最小条件 |
| --- | --- |
| 执行 7 个测试套件，把 C1-C5 从“源码 fixture”提升为“实跑通过” | 安装 MSVC + xmake + vcpkg（x86-windows-static OpenSSL），或提供预构建产物 |
| 复核任何 CODOL RVA / netfield / parser 语义 | 取得 SHA-256 = E3823FD6... 的 3.3.3.3 客户端，或 out.exe build 1649370 |
| 复现 mmstart -> ... -> snapshots 主链 | 上述客户端 + 有效的 CODOL 游戏目录（含 .ff 资产）+ 两个实例 |
| 产生 PCAP/协议记录 | 目前无实现路径；可参考旧项目的 Windows 自带 pktmon 方式，但需为本项目重新建立采集与归档流程 |
| 建立首个 Golden Copy | 先完成一次可核验的“进入战斗地图”运行（依赖上面三项），再按 GOLDEN_COPY_SPEC.md 冻结 |

---

## 8. 审计纪律声明

- 全程未执行 reset / clean / checkout 覆盖 / 批量格式化。
- 未覆盖任何既有运行证据或 Golden Copy（本机亦不存在，已确认）。
- 未修改任何既有文件；本审计包为新增。
- 未推送到 origin。
- 未调查已关闭的 WeGame / TCLS / IIPS / 启动器路线。
