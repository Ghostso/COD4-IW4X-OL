# R0 基线完整性校验

任务：CODOL-LOBBY-FULL-LIFECYCLE-REPAIR-056  
核验时间：2026-10-29 11:43–11:47 (+08:00)  
项目根：`D:\BaiduNetdiskDownload\使命召唤OL`

## 判定

**R0 的静态核验已完成；默认 GOLDEN 启动基线不健康。可以进入 R1 的隔离分析/修补，但不能把默认 GOLDEN 当作可直接启动的干净基线。**

- REF 受保护清单实测 **8/9 匹配**。唯一既有偏差为 `marketplace_store.py`；启动器显式检查的 6 个 launch_core 文件全部匹配，两个零字节隔离旗标也正常。
- GOLDEN `_run_once_hashes.json` 实测 **38/39 匹配**。`lobby_server.py` 已变为 88,162 B，而清单仍是 87,080 B；按 `run_frozen_chain_once.py:171-178`，默认启动会被拒绝。
- 已有 `run_codol_001\kit_R1_PVE_REPRO_20261029` 清单 **39/39 匹配**，可作为 R1 的隔离复制候选，但它不是已验证成功基线。
- 未修改任何 REF/GOLDEN/历史日志，未启动客户端，未提权、未动态调试、未初始化仓库、未提交或建分支。

## 1. 历史结论与原始运行证据

已读取 `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053\00_INDEX.md`、`01_EXECUTIVE_TECHNICAL_FINDINGS.md`、`07_HISTORICAL_REGRESSION_ANALYSIS.md`，以及 `CODOL-LOBBY-FULL-LIFECYCLE-FORENSICS-055\00_INDEX.md`、`01_LOBBY_CURRENT_STATE.md`、`11_HISTORICAL_SUCCESS_FAILURE_TIMELINES.md`、`20_FINAL_LOBBY_TECHNICAL_ASSESSMENT.md`。本报告只做 R0 身份/完整性判断，不重写 053/055。

### 2026-10-26：成功连接战斗服

Run：`D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\ONCE_20261026_220815`

- `preflight.json`：源 Kit=`CODOL_VERIFIED_GOLDEN_20261019`（当时字节），工作 Kit=`...\ONCE_20261026_220815\kit`，游戏根=`run_codol_001\sandbox_ifs1_20260923`，客户端 PID=15580（由 `chain_pos.txt:3` / `postflight.json:5` 证实）。
- `kit\lobby_srv.log`：22:08:47 hello/KDF；22:09:15 playlist=10、mmbook、mmstart，地图 `coop_train_mp_firingrange`、roomChatChannelID=0。
- `kit\_battle_out.txt:8-22`：NAT、DTLS、KEY_EXCHANGE_OK、getchallenge、connect、STATS_COMPLETE；后续有 RX_CLIENT_GAME_HEADER。
- 大厅日志：31,613 B / `BF650058EA8027F0222BCD80EF922DA9FDFBDC079A9CC11A5F895374BC2C2CEA`。
- 053/055 共登记 8 轮成功；这里选取最后一轮做身份锚点。它是战斗连接证据，不是完整对局证据。

### 2026-10-27：成功进入大厅

Run：`D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\ONCE_20261027_120832`

- `preflight.json`：源 Kit=GOLDEN（当时字节），游戏根=`COD OL`，工作 Kit=`...\ONCE_20261027_120832\kit`。
- `chain_body9.txt:1-3`：客户端 PID=16520；模块枚举 93；4/4 兼容补丁成功；`5E8` 到 3。
- `kit\lobby_srv.log:6-51`：12:09:01 建连，hello/0x81/0x82/KDF/0x83，解密请求和应答正常。
- `docs\PVE_BATTLESTART_STATUS_20261027_1220.md:3-7` 与 `docs\PROGRESS_SAVE_20261027.md:38-42` 是“完整进大厅”结论的同期说明；根因是 `COD OL\iips.ini` 的 `enable_iips` 从 0 改为 1。
- 大厅日志：39,830 B / `5DF8DB811B826579DF034AF284126376389F521B592C2457E77D80151CBD78E0`。
- 该轮随后进入 BOT/房间路径且 UDP 28960 零收包，不能把它误称为战斗连接成功。

### 2026-10-29：E1 失败

启动 run=`run_codol_001\runs\ONCE_20261029_103202`，分析 run=`run_codol_001\runs\E1_20261029_103001`。

- `preflight.json`：源 Kit=`run_codol_001\kit_E1_20261029`，游戏根=旧沙箱，工作 Kit=`...\ONCE_20261029_103202\kit`。
- 客户端 PID=20360；`kit\lobby_srv.log` 为 playlist=50 BOT 房间路径，有 createRoom/setRoomData，无 mmbook/mmstart。
- `kit\_battle_out.txt` 仅 7 行初始化；`e1.pcapng` 156 B，无数据包。`E1_RESULT.md` 同样确认零 RX。
- 这**不是**对 10-26 PvE 成功路径的有效复刻。E1 与成功轮的 13 个已比对核心文件逐项同哈希，因此也不是“相对成功轮换了核心 Kit”；它们共同区别于当前 GOLDEN。

### 当前并行运行（非 R0 成功证据）

`ONCE_20261029_114237` 使用 `kit_R1_PVE_REPRO_20261029` + `COD OL` 本体，日志到 mmstart 并推 109 B StartGame；截至读取时 `_battle_out.txt` 仍只有初始化，没有 NAT/DTLS/RX。检测到 PID 20224 客户端与 PID 2140 战斗服仍在，活动 `_battle_out.txt` / `R1_PVE_REPRO_console.txt` 被占用，**未对活动文件给出哈希，也未终止进程**。另外，当前 GOLDEN 的 5/5 成功日志不能掩盖其 nt10 源码中 `len(done)==4` 的日志条件错误。

## 2. 当前组件精确身份

### 启动器与运行/工作目录

- 启动器：`D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\run_frozen_chain_once.py`  
  18,443 B / `0E6460E7E3E5AEBBF6B30A2C35894476C86F13231AC51E57DDCAC98178EB794C`。
- 默认源 Kit：`CODOL_VERIFIED_GOLDEN_20261019`；默认游戏根：`COD OL`。
- 每轮工作目录：`run_codol_001\runs\<RUN_ID>\kit`。启动器复制 Kit、改写副本的 GAME_ROOT 与 start_battle_server；不应把 run 内 `run_all.py` 的哈希当作源文件哈希。
- 当前完整候选 Kit：`run_codol_001\kit_R1_PVE_REPRO_20261029`，39/39 清单匹配。R1 必须再复制到独立工作目录，不能在其上原地修改。

### 自研大厅服务端

- 文件：`D:\BaiduNetdiskDownload\使命召唤OL\CODOL_VERIFIED_GOLDEN_20261019\lobby_server.py`。
- 88,162 B / `FF4732041B673D89FA2BF1F14D4540D7C5806EB859B1087634618AB12E5A8DFC`。
- Python/TCP 3074。含 memberCount=1、房间下行构造、coop_map.txt 自校正、mmstart StartGame 推送。
- GOLDEN 陈旧声明：87,080 B / `EB8ACE0F25E5A0CF20CE0616657EA87CDFA6A7C89BA9709AE2DF688162437BBE`。
- `codol_crypto.py`：42,853 B / `E836C63AF75DD82EF6F3B07EF63FAE48B044B3B5047336127093C92B07644607`。
- 同哈希副本位于候选 R1 Kit；`PATCHES\baseline\lobby_server.py` 也是这个哈希。

### 自研 C 战斗服（不是大厅）

- 源码根：`D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021`；`CMakeLists.txt:16-47` 登记 27 个 C 源文件。
- 当前 `include` + `src` 共 57 个 C/H 文件。内容树聚合 SHA-256：`5218B4AF94CDE993E8878788319A42376941F0D72E5561C0B750B4E105E92023`。算法：逐文件小写 SHA-256 + 两个空格 + 排序相对路径 + LF，再对 UTF-8 文本求 SHA-256。
- `src\main.c`：6,781 B / `34146F4015CF8D09921B664AC1DBA945B46F4968CF965FCC69FAF8EA6AA0A1C0`。
- `CMakeLists.txt`：10,288 B / `2C3A2E14EA87090D8E33217F319B9192119556059CEE53287561F2A5059968BC`。
- 构建产物：`build\Debug\codol_battle_server.exe`，314,368 B / `275B165F0A7960CAF8FAC8BA07216A8FC651FB8ABF4BFCB31EE84FEB790B28A9`；GOLDEN 和候选 Kit 内 EXE 与它逐字节同哈希。
- 未重新构建，故这里证明的是“部署产物与现存 Debug 产物相同”，不是从当前源码做可重现构建证明。

### 客户端与配置

- 主 EXE：`D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe`  
  7,841,344 B / `36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537`；Windows FileVersion=1649370。沙箱 EXE 同哈希。
- 根 DLL：`codoMP_client_shipRetailBase.dll`，60,327,992 B / `EF75220DE1D6973F34C7069F5BF211B11BD61520C6C0DE1882F7359FA5BC6A20`。
- 两个 `.local` 目录实际各含同名 `codoMP_client_shipRetailBase.dll`，均 60,327,992 B / `3D2B338DA69F2544FE29DB8D3DA3B3C2DE92F5DE9E8B5A9FB085A4C4ECC20DFD`。它们与根 DLL 不同，不能只哈希根 DLL 就宣称完整运行时身份相同。
- 目标标识：3.19 / build 1649370（AGENTS.md、战斗服日志、EXE FileVersion）。历史文档另有“3.3.3.3”名称；R0 以精确哈希区分，不以营销/协议名称替代身份。
- 本体和沙箱 `iips.ini` 同哈希：48 B / `2EB27C03261CB1603AE817DF15F79B6CC7561A435AB0D1C39874A97FC471B952`；内容均为 `enable_iips=1`、`iips_url="http://10.231.2.181/"`。

## 3. REF / GOLDEN 完整性

REF 清单文件：1,190 B / `47491202C14AC2D65C6EEBCD86939C234B12354CCFA1EA41B10D96EE47ACFF3F`。以下均为本次 Get-FileHash 实算：

| 文件 | 字节 | 实际 SHA-256 | 清单 |
|---|---:|---|---|
| battle_selftest.py | 20,145 | `06b8b5a8b32586cf066ec2c76650c3df28841acdeef56639fbdbd3f88d1a4ef5` | 匹配 |
| battle_server.py | 69,019 | `71bb7beb85e514082b91a4925d18cb09fd07d5e8916ffa7f4fbd4a9750b47274` | 匹配 |
| codol_crypto.py | 42,853 | `e836c63af75dd82ef6f3b07ef63fae48b044b3b5047336127093c92b07644607` | 匹配 |
| fake_auth_tls.py | 10,347 | `e638e96fe420d66d1d52c26f3e413a15126818e4491ae30196a806cbcdd265be` | 匹配 |
| lobby_server.py | 76,410 | `d7eeb4564af05f4c71fb3391112a8bf592b74f0aa12dec8f286b927ae046c2cf` | 匹配 |
| make_local_ca.ps1 | 6,607 | `f89e314e717a38a393fd31ea9bd0dbf69648f682d7fe14b000c68fc764dfe103` | 匹配 |
| marketplace_store.py | **50,022** | `e44358f0eb951b62c244a136a181952c26850e841d537bcb70ebb0ffc5dd034e` | **不匹配：声明 46,226 / `28b4a1be…`** |
| nt10.py | 169,491 | `05863ebafc7d7bb3820cce057bc9e4e0ea07816945ca03e38a9bbfecacab22f8` | 匹配 |
| run_all.py | 31,507 | `2aaa8847f112d926b996e5fd38dd26b697adc0697c45781f520940a8256ecda6` | 匹配 |

REF 的 `tas_off.flag` 与 `poke_off.flag` 均为零字节，SHA-256=`E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`。不要把“launch_core 通过”写成“REF 全清单通过”。

GOLDEN 的 39 项逐项结果见 `R0_BASELINE_MANIFEST.json`；38 项相同，仅大厅文件不同。`write_dwauth.py` 也在本次核心哈希范围内：2,491 B / `8991C6A44A73897DF12A28B78E8CB43331B2B2DD001B22263EBD28379516AD60`，与 REF/成功/E1 一致。

## 4. 成功、E1、当前 Kit 的真实差异

以下比较 13 个核心条目（run_all、nt10、lobby、fake_auth、crypto、write_dwauth、make_local_ca、C 战斗服、lobby/tas/patch/late 规格、ready_push）：

- **10-26 成功 run 与 E1 run：13/13 相同。** `run_all.py` 均为被启动器生成的 32,332 B / `E74C4A0A…`；这不是源 `run_all.py`。
- 成功/E1 `lobby_server.py`：78,206 B / `8A1D284074E8EB1A65BF9D29CEEE1F0E856D5E3AB0C3A09225844C4B3EE30114`；memberCount=0。
- 成功/E1 `nt10.py`：169,893 B / `4C84D161E1938EB1EB7DCEF9F84D849D6AC664883C997F43D26995083715F81C`；4 个兼容补丁。E1 的源 Kit `nt10.py` 另为 `B21BF06E…`，运行时 launcher 会改写副本，故不能用源文件哈希替代 run 文件哈希。
- 当前 GOLDEN `nt10.py`：170,373 B / `6F1196E6C7806F99DD80DB34A3EC56638A7B554A911D2A20308FAC5D089BA5BA`；5 个补丁。
- 当前 GOLDEN 大厅：88,162 B / `FF473204…`；比成功/E1 多 9,956 B，增加 memberCount=1、房间推送、StartGame、coop_map 等逻辑。
- 当前 GOLDEN 与成功/E1 的 `codol_battle_server.exe` 完全相同，因此“当前不能连”不能直接归因为换过 C 战斗服二进制。
- 10-27 进大厅 run 的大厅：81,143 B / `A6A991E5C29CE6D86CEB62911FDAC55AFB2838FCCDD4F57CBDC26D94BB6CA283`；其 nt10 与成功/E1 相同。
- 根目录也不同：成功与 E1=旧沙箱；10-27 进大厅与当前默认=本体。地图/UI 路径不同是主要实验混杂变量，R0 不做单变量因果裁决。

### nt10 补丁数量与作用

1. AuthGate：运行时 `74→75`，目标 `0x00B9A78E`。
2. ClientTicket：`75→EB`，目标 `0x00B9A7C5`。
3. ParseFallback：`E8→E9` 并跳 `0x00B9A7F1`，写入点 `0x00B9A7C7`。
4. LsgNonceCheck：在 `0x00BA3C1C` 写两个 NOP。
5. 仅当前 GOLDEN/候选 R1 增加 GateB 放行：`0x0062FE80` 写 `B0 01 C3`。

这些是运行时补丁，不改变客户端磁盘哈希。成功/E1 为 4 个，当前候选为 5 个；缺 #5 不能解释 E1 的 BOT 路径选择，也不能单独证明连接因果。

## 5. Git 与非破坏性回滚

- 项目根、`REF_LOBBY_KIT`、`CODOL_VERIFIED_GOLDEN_20261019`、`CODOL_SERVER_319_20261021`、`CODOL-Combat-Server-v0.1` 均无 `.git`。
- `git` 不在 PATH，常见安装路径也不存在。
- 唯一发现的相关仓库为 `CODOL-BATTLE-SERVER-IMPLEMENTATION-FOUNDATION-047\.git`，HEAD=`ref: refs/heads/050/recv-to-consumer-trace`。它是另一套 .NET 战斗服研究树，不是当前大厅源码或当前 C 战斗服源码；**未在此建分支**。
- 非破坏性回滚机制采用 `PATCHES\baseline` 原样副本 + 本清单哈希 + 后续独立 run Kit，不依赖 Git。

## 6. 并行产物与未决项

R0 写入前，交付目录已出现其他执行者的 `PATCHES` 文件，本任务未修改它们。最近一次读到的哈希：

- `PATCHES\baseline\lobby_server.py`：88,162 B / `FF4732041B673D89FA2BF1F14D4540D7C5806EB859B1087634618AB12E5A8DFC`。
- `PATCHES\work\codol_crypto.py`：42,853 B / `E836C63AF75DD82EF6F3B07EF63FAE48B044B3B5047336127093C92B07644607`。
- `PATCHES\work\lobby_server.py`：在两次读取间从 88,316 B 变为 88,560 B，属于活动文件，不登记为稳定基线。

R1 前必须处理/确认：

1. GOLDEN 源大厅与 `_run_once_hashes.json` 的陈旧声明冲突；不要在受保护 GOLDEN 原地“修清单”，应复制出经过审阅的独立 Kit 并生成匹配清单。
2. REF `marketplace_store.py` 偏差仍未裁决；不得称为全绿，也不得为“修哈希”覆盖它。
3. 明确 R1 使用本体、完整 39/39 候选 Kit 的隔离副本，以及用户实际选择的 UI 路径；E1 的 BOT/B2 路径不是 PvE 成功复刻。
4. 记录 `.local` DLL 变体；根 EXE 相同不代表沙箱与本体运行环境相同。
5. 活动 R1 进程与并行修补者仍在写文件。下一轮需先固定输入副本/归属，避免同一目录多写者；本任务不终止进程。
6. 未做客户端启动、动态验证、源码重建或成功连接复现；这些不属于 R0 静态完整性结论。
