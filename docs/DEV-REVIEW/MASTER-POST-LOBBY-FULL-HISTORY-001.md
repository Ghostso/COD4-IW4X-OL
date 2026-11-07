# MASTER-POST-LOBBY-FULL-HISTORY-001
# CODOL 复活项目 —— 从首次进入正式 Online Lobby 起的全工程考古总账

```
FILES_SCANNED     = 47,397 个 anchor 之后被修改的文件（全工作区，不含 COD OL / run_codol_001 游戏本体）
                    其中工程文档(md/txt) ~50 篇、只读分析脚本 200+、服务端/客户端配置与开关 100+、
                    其余为内存转储(mem_linear/mem_marketplace/mem_sku)、日志、nt10 运行转储与备份
WORK_ITEMS_FOUND  = 136 个编号条目（两套编号部分指向同一件事的不同视角，未强行去重）
                    · §3 时间线 T01-T68        68 项（严格按时间，主口径）
                    · §4 域内补充 B-00..B-21    22 项（战斗/UDP/DTLS）
                    · §4 域内补充 MK-00..MK-21  22 项（商城/目录/发行方/玩家/库存）
                    · 其余 ASSET-01..08、REF-01..04、PB-01..03、PR-01、MO-01、RE-01/02、RUN-01、FAIL-01、TOOL-01..03
TIME_RANGE        = 2026-10-05 16:36 → 2026-10-08 20:44（anchor 之前只作"前置依赖"引用）
REPORT_STATUS     = COMPLETE（S1/S2/S3/S4/S5 五个并行考古子任务 + 主 agent 复核）
```

> 本报告是"**从首次进入正式大厅开始，CODOL 复活项目后来实际发生过的全部工程工作总账**"。
> 大厅只是 START POINT。Booking / Battle / Server / Protocol / Player / Marketplace /
> Resource / Reverse Engineering / Reference Research / 工具 / 失败实验 全部在范围内。
> 所有事实尽量落回项目文件、报告、日志、脚本或证据；两份资料冲突时**双留**并标 SOURCE_CONFLICT。

---

## §0 本报告的性质与方法

### 0.1 这不是什么
- 不是"大厅恢复总结"，也不是"Booking/Battle 总结"。
- 不是开发计划，不提出新方案，不重新逆向。

### 0.2 是什么
- 一次**历史考古 + 全量工作汇总**：把 anchor 之后项目实际做过的每一件事找出来、
  按时间摆开、按生命周期还原、按结局分类，形成可交接的总账。

### 0.3 方法（第一原则：先考古，再总结）
1. 不凭记忆写报告。所有条目都回到磁盘证据（报告 / 日志 / 脚本 / 开关 / 备份 / 哈希）。
2. 用文件 mtime + 文档内声明时间 + 日志行时间戳重建时间线；无法精确者标 TIME_APPROXIMATE。
3. 并行派 5 个考古子任务（S1 大厅链路/UI/协议；S2 商城/目录/发行方/玩家；S3 Booking/PvE；
   S4 Battle/UDP/DTLS；S5 参考研究/资源/工具），各自独立读材料，主 agent 复核并合并。
4. 冲突不静默修正：两侧都留，进 §17 SOURCE_CONFLICT。

### 0.4 一个必须先说的结构事实（它决定后面所有事）
**anchor 之后，我们自己写的 CODOLServer 大厅栈没有被再修改过一个字节。**

```
CODOLServer\lobby_server\lobby_plain_probe.py     最后写入 = 2026-10-05 15:05:09（anchor 之前）
其 __pycache__                                            2026-10-05 15:05
CODOLServer\lobby_server\ 其它 *.py                 全部 ≤ 2026-10-04 22:55
CODOLServer\_mainline\                              无 anchor 之后写入
```

⇒ anchor 不是"我们自己的栈终于调通了"，而是"**我们放弃自研协议栈，改用第三方完整实现
   (REF_LOBBY_KIT，从 F: 盘复制)**"。所有 anchor 之后的工程工作都发生在
   `REF_LOBBY_KIT\` 及其两个克隆 `GOLDEN-LOBBY-001\REF_LOBBY_KIT\`、
   `DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\` 里。
   命名陷阱：`CODOLServer\lobby_server\lobby_plain_probe.py`（我们的）与
   `REF_LOBBY_KIT\lobby_server.py`（第三方的）是**两个不同的服务端**；
   进大厅的是后者。

---

## §1 时间边界与锚点

```
起点（ANCHOR）  2026-10-05 16:36
  证据   HANDOFF_20261005_LOBBY_REACHED.md（mtime 10-05 16:49:13）
         标题："★★★ 已进入大厅（2026-10-05 16:36）"
         截图   REF_LOBBY_KIT\lobby_live.png    mtime 10-05 16:36:34
                REF_LOBBY_KIT\lobby_window.png  mtime 10-05 16:36:51
         判据   窗口类 CODO 可见、标题 "使命召唤online"、
                任务数 34 → 47、hmac 全 OK、无致命弹窗
终点（NOW）     2026-10-08 20:44（本报告写作时的最新工程状态）
```

anchor 之前的内容只作**前置依赖**引用（在 anchor 之后被真实使用/验证/修改过的）：

```
PRQ-1  HANDOFF_20261005_LOBBY_REACHED.md（起点本身）
PRQ-2  STAGE_REPORT_BATTLE.md（10-07，被 003/010/011/019 反复引用的唯一来源）
PRQ-3  GOLDEN-LOBBY-001 冻结手册 + _golden_hashes.json + 开关 .OFF_CONFIRMED_CRASH
PRQ-4  运行期解壳镜像
       CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin
       （10,899,456 B，base 0x400000，可读 0x400000..0xE65000）—— 001..019 全部静态分析的唯一指令级源
PRQ-5  客户端 EXE / Base.dll（COD OL\）：001 的静态源；003/spec-002/003 的 Base.dll 限定扫描对象
PRQ-6  REF_LOBBY_KIT\_ref\CodolLocalLobbyServer.cs（第三方 C# 参考实现）—— 唯一的行为参照
```

---

## §2 扫描范围与证据基础

### 2.1 扫描的目录
```
顶层      HANDOFF_20261005_*.md（8 篇）、GOLDEN-LOBBY-001.md、CLIENT_OBJECT_SCHEMA.md
REF_LOBBY_KIT\ + DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\ + GOLDEN-LOBBY-001\REF_LOBBY_KIT\
          anchor 后 .md 16 篇；服务端 9 个核心 .py；开关/备份/日志/转储 33,455 个文件
DEV-BOOKING\   anchor 后 112 个文件；.md 31 篇（含 SERVER-PVE-BOOKING-RESPONSE-010）
                  + scripts\ 200+ 只读脚本 + evidence\ + runtime_net_001\ + runtime_net_ch003\
CODOLServer\   anchor 后仅 1 个文件（提权代理日志 elevated_agent.json）
IW4X\ / OfflineServer\ / restore003\ / restore005\ / restore006\ /
analysis_logs\ / toolchain\ / restore_iips_contract_*\ / ace_facade\
                  anchor 之后 **0 个文件被修改**（S5 复核）
```

### 2.2 anchor 之后的文档清单（工程文档、按时间）
```
10-05 16:49  HANDOFF_20261005_LOBBY_REACHED.md          （anchor 记录）
10-05 18:35  HANDOFF_20261005_LOBBY_BUGS.md              （大厅全量 BUG 诊断与计划）
10-06 11:13  HANDOFF_20261006_CATALOG_LAYOUT.md
10-06 15:05  HANDOFF_20261006_CALLSIGN_CHANNEL.md
10-06 15:27  HANDOFF_20261006_PURCHASE_FIX.md
10-06 15:41  HANDOFF_20261006_BUY_MATRIX.md
10-06 17:14  HANDOFF_20261006_REVERSE_SUMMARY.md
10-06 18:43  HANDOFF_20261006_MARKET_MANIFEST.md
10-06 19:09  HANDOFF_20261006_MAIN.md                    （取代当日其余 6 篇）
10-06 21:38  HANDOFF_20261006_MERGED_CATALOG.md
10-06 22:33  HANDOFF_20261006_LOBBY_MAP.md               （大厅协议系统排查）
10-07 13:06  CLIENT_OBJECT_SCHEMA.md                     （客户端对象字段表）
10-07 14:34  HANDOFF_20261007_TAKEOVER.md                （41,542 B，总入口交接手册）
10-07 15:19  HANDOFF_20261007_BATTLE_SERVER.md
10-07 18:20  BATTLE_SERVER_PROTOCOL.md                   （41,148 B）
10-07 19:01  GOLDEN-LOBBY-001.md                         （冻结清单）
10-07 19:13  STAGE_REPORT_BATTLE.md                      （P0-1/P0-2/P0-3 阶段报告）
10-07 19:22 → 10-08 20:26   DEV-BOOKING 全系列 31 篇（001→019 与证据/规格）
```

---

## §3 全量时间线（先按时间，不按领域）

时间来源：文件 mtime / 日志行 / 文档内声明。标 `TIME_APPROXIMATE` 者为按文档顺序推定。

| ID | 时间 | 领域 | 工作 | 目的 | 实际动作 | 结果 | 后续 |
|---|---|---|---|---|---|---|---|
| T01 | 10-05 16:00 [TA] | 大厅/协议 | 采用第三方 kit | 停止手写协议 | 复制 F: scripts → REF_LOBBY_KIT；设 GAME_ROOT；给 nt10 加 --root | 34 条任务、hmac 全 OK | 后续全部工作都在 kit 上 |
| T02 | 10-05 16:01–16:03 | 大厅/协议 | ready_push + mirror_predicted 轮 | 消除弹窗 | n10push/n10push2 | 仍弹 [100]；0B/4 频道从未出现 | **REFUTED**（推送不是阻塞点） |
| T03 | 10-05 16:30–16:40 | 大厅/协议 | **两个真实修复** | 过 fatal、拿到正确 challenge | ①0x83 改用本会话 KDF challenge（配对 0x82 票据密钥，最多等 5s）②10/21 文件名同义名回退 + 实体别名文件 | 任务 34→47；窗口 CODO 可见 | **★ ANCHOR** |
| T04 | 10-05 16:31:29 | 证据 | popup_fatal_error.png | 记录修复前致命弹窗 | 截图 | EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE 存档 | KEPT |
| T05 | 10-05 16:36:34 / 16:36:51 | 证据 | **lobby_live.png / lobby_window.png** | 记录进入正式大厅 UI | 1920x1080 截图 | 好友/公告/福利/任务面板 + Lv70 + 多人入口 | **ANCHOR 物证** |
| T06 | 10-05 16:40–16:47 | 动态 | n10repro_lobby 复现轮 | 复现并观察重连 | 重跑成功配置 | 主连接 64808 活 4m40s、56 任务、hmac 全 OK、keepalive 正常 | → T07 |
| T07 | 10-05 ~16:47 [TA] | 更正 | 重连 hmac=BAD 重新归因 | 停止追错误阻塞点 | 重读日志 | "**BAD 是结果，不是原因**"：没有游戏世界 → 客户端正常关连接并重连 | **REPLACED**（旧归因保留在原文） |
| T08 | 10-05 16:43:58 | 证据 | lobby_repro.png | 复现物证 | 截图 | KEPT | — |
| T09 | 10-05 16:49:13 | 文档 | HANDOFF_20261005_LOBBY_REACHED.md | 记录 anchor 轮 | 写报告（含 §2.5 更正） | 同一文件内同时存在旧归因与更正 | SOURCE_CONFLICT #2 |
| T10 | 10-05 16:55:12 | 会话/房间 | 靶场开关组 | 打开 21/5 session + battle，booking 保持关 | 建 firingrange-session.enabled / firingrange-battle.enabled；把 booking 改名 .OFF_CONFIRMED_CRASH | 仅开关状态；9/9 断连原因文档只存在于 10-07 | → R 组 |
| T11 | 10-05 16:59–17:10 | 动态 | n10world ×4 | 找可进入的游戏世界 | 跑并抓取 | 无报告、无日志留存 | **UNKNOWN** |
| T12 | 10-05 17:16 / 17:27 | 库存 | 全物品发放 | 让商城/背包有东西 | _grant_all_items.py / _set_inventory_count.py | 17372 件库存；lobby_allitems.png 17:41:18 | 后来被指为 480KB 截断诱因 |
| T13 | 10-05 18:01–18:26 | 工具 | UI 失败转储工具 | 从客户端自报里找原因 | _dump_uiexception.py / _dump_tasks.py；_tasks_offset.txt=3866 | 识别 71/7 UIException 通道 | → T14 |
| T14 | 10-05 18:35:14 | 诊断 | 大厅 BUG 全量诊断 | 系统化 | HANDOFF_20261005_LOBBY_BUGS.md | 根因按数据源归组；证实第三方参照也没实现这些功能 | → 10-06 全天 |
| T15 | 10-05 20:44–23:49 | 商城 | 内存 SKU/目录扫描 | 找回 SKU 目录 | _scan_marketplace_mem.py / _sku_schema.py / _scan_sku_arrays.py / sku-live.on | 产出 mkt_assets\*.csv | → T17 |
| T16 | 10-05 23:02:50 | 基线 | _config_mp.baseline_*.cfg | 客户端 mp 配置基线 | 快照 | KEPT | — |
| T17 | 10-06 11:13 | 商城 | 目录布局 | 摸清 catalog 结构 | HANDOFF_20261006_CATALOG_LAYOUT.md | — | → T18 |
| T18 | 10-06 13:23:12 | 商城 | 启用客户端目录 | 让购买可解析 | marketplace-catalog-client.on | — | → T22 |
| T19 | 10-06 14:26–15:27 | 商城 | 库存/目录备份 | 保证可回滚 | .bak_big / .bak_full / .bak_inferred | — | — |
| T20 | 10-06 15:05 | 商城 | 名片/徽章/称号通道 | 解释"买了看不到" | HANDOFF_20261006_CALLSIGN_CHANNEL.md | 名片是玩家档案槽位；客户端要读 mp\callsign*.csv / item_cnc.csv / badgeTable.csv，我们没提供 | 未解决 |
| T21 | 10-06 15:14:32 | 商城 | _build_full_catalog.py | 造全量目录 | 生成 catalog-full 38424 条 | 未启用 | — |
| T22 | 10-06 15:27–15:41 | 商城 | **购买解析修复** | "点购买没反应" | 由 58B 硬模板改为按类型标签 TLV 解析 | 实测购买成功 sku=32223，GP 883599→819999（真实扣款） | **KEPT** |
| T23 | 10-06 17:14 | 商城 | 逆向小结 | 汇总 | HANDOFF_20261006_REVERSE_SUMMARY.md | — | — |
| T24 | 10-06 18:43 | 商城 | 商城清单 | 汇总 | HANDOFF_20261006_MARKET_MANIFEST.md | — | — |
| T25 | 10-06 19:09 | 总 | **当日主交接** | 取代当日其余 6 篇 | HANDOFF_20261006_MAIN.md | 唯一核心结论：能不能买只取决于 SKU 在不在服务端目录 | 若干旧结论在 §5 被推翻 |
| T26 | 10-06 19:33:53 | 商城 | 合并目录开关 | 扩展可买范围 | marketplace-catalog-merged.on | — | → T29 |
| T27 | 10-06 21:28–21:29 | 玩家 | public.result 尾部注入实验 | 验证 125×0x07 = 装备清单 | _patch_public_tail.py + 服务端 _inject_public_tail() | 客户端行为不变 | **REFUTED / ROLLED_BACK** |
| T28 | 10-06 21:33 | 商城 | marketplace_store.py + 货币宽松 | 解释"武器能买、名片不能" | marketplace-currency-lenient.on | 重新归因为**货币字段不一致** | KEPT |
| T29 | 10-06 21:38 | 商城 | 合并目录 | 汇总 | HANDOFF_20261006_MERGED_CATALOG.md | §8.4：客户端**根本不认** marketplace 库存里的名片拥有关系 | 未解决 |
| T30 | 10-06 21:40 / 21:44 | 工具 | 任务矩阵 + UIException 解码 | 系统化而非逐个修 | _lobby_task_matrix.py / _dump_uiexception_bin.py | 43 组 service/task，21 未映射；4 条 UI 崩溃链 | → T34 |
| T31 | 10-06 21:49–22:48 | 大厅 UI | **mp_playlists 重建** | 修空游玩清单（#1009 MatchMakingStripView） | _build_playlists.py；4 组时间戳备份 | 262B→658B→716B（zlib 文本，version 796，6 模式）；版本崩溃消失但列表仍空 | KEPT（10-07 继续） |
| T32 | 10-06 22:00:19 | 工具 | _lobby_data_audit.py | 数据源→UI 映射 | 静态审计 | 10 个 publisher 文件（4 个占位）；21 个未映射服务 | → T34 |
| T33 | 10-06 22:22–22:28 | 商城 | **SKU sentinel 探针** | 反推 80/70 线格式 | market_sku_probe.py + 伪造 SKU 列表 | ★ 商城/仓库变灰、**角色被锁**；内存有 32 个 sentinel 但解析失败 | **ROLLED_BACK**（22:28:24） |
| T34 | 10-06 22:33:04 | 大厅 | LOBBY_MAP.md | 大厅协议系统地图 | 写报告 | 矩阵 + 4 条崩溃链 + 三层修复计划 | 10-07 的基础 |
| T35 | 10-06 22:37:20 | 工具 | provider-dump.on.done | 只读转储实验收尾 | 写 marker | 实验关闭 | — |
| T36 | 10-06 22:59:36 | 启动器 | run_all.py 修 | 启动器修复 | 编辑（体积不变 31,507 B） | 10-07 被冻结 | — |
| T37 | 10-07 10:43–11:17 | 日志 | logs_before_pve_*（4 份） | 归档 PvE 前日志 | 复制 | 10-05/10-06 服务端日志**已不存在** | UNKNOWN |
| T38 | 10-07 13:06 | 逆向 | CLIENT_OBJECT_SCHEMA.md | 客户端自己声明的字段表 | 从 mem_linear 提取 codo.objects::Class\field | 挑战/公告/游玩清单/快速匹配字段全表 | 10-07 修复依据 |
| T39 | 10-07 14:34 | 交接 | HANDOFF_20261007_TAKEOVER.md（41 KB） | 总入口 | 写报告 | 含"现状：能登录、能进大厅"、4 个内存补丁 + KDF hook 地址、ivp/密钥 | 后续全部接力的入口 |
| T40 | 10-07 15:19 | 战斗 | HANDOFF_20261007_BATTLE_SERVER.md | 战斗服交接 | 写报告 | — | → T42 |
| T41 | 10-07 18:06–18:08 | 协议 | **推送序号机制 + 事故** | 修 0x85 推送序号 | push_seq_offset.txt；lobby_server.py 推送段 | 记录 18:06:28 的客户端 seq 冲突事故；定 +1000 偏移 | 与 019 的 marker 疑问相关 |
| T42 | 10-07 18:20 | 战斗 | BATTLE_SERVER_PROTOCOL.md（41 KB） | 战斗服协议 | 写报告 | — | → T44 |
| T43 | 10-07 19:01 | 冻结 | **GOLDEN-LOBBY-001 冻结** | 立只读基线 | 22 个文件 SHA-256 + _golden_hashes.json | 冻结值含 lobby_server.py D7EEB456… / nt10.py 05863EBA… / codol_crypto.py E836C63A… | 后续所有"未改 Golden"以它为准 |
| T44 | 10-07 19:13 | 阶段 | STAGE_REPORT_BATTLE.md | 三阶段报告 | P0-1 冻结；P0-2 找 ol-mod 源码；P0-3 Lobby→Booking→Battle | **P0-2 BLOCKED**（全盘 0 命中）；booking 需走独立 DedicatedControl/client bridge 但端口与帧格式 UNKNOWN | → DEV-BOOKING |
| T45 | 10-07 19:22–19:46 | Booking | 静态阶段 001–004 | 契约→协议规格 | BOOKING-CLIENT-CONTRACT-001 / PROTOCOL_SPEC-001..004 / STATE-001 / evidence-002 | 定位 handler 0x632680；A/B 真实写入 0x62F6F0；reservation 数组 this+0x75D8 stride 0x238 | → T46 |
| T46 | 10-07 19:50 | Booking | BOOKING_RUNTIME_TRACE-001 | 想断点观测 | 评估运行期能力 | **INSTRUMENTATION_BLOCKED**（只有 ReadProcessMemory；Frida 因 ACE 禁用） | ABANDONED → T47 |
| T47 | 10-07 20:10 | Booking | BOOKING_RUNTIME_NETWORK-002 | NDIS 抓包观测 6/14 | netsh trace + 窗口文本 | 6/14 **NOT_SENT**；弹 EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE；28960 出现 33 次但非 booking | → T48 |
| T48 | 10-07 20:18 | Booking | PUBLISHER_FAILURE_SPEC-001 | 定位 fatal 根因 | 静态 + 日志比对 | FAILURE_FUNCTION=0x66A650；条件=同一 publisher 文件连续 3 次失败；reason=NOT_FOUND | → T49 |
| T49 | 10-08 09:10 | 发行方 | PUBLISHER_FILE_RECOVERY-001 | 找原始 .info | 只读全盘搜索 + 恢复矩阵 | 原始文件在 REF_LOBBY_KIT\publisher_files\；根因判为 **Golden 冻结副本缺数据目录** | → T50 |
| T50 | 10-08 09:25 | 发行方 | **PUBLISHER_FILE_RECOVERY-002** | DEV 副本恢复验证 | 建 DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\ | fatal 消失；**09:23:45 首次真正发出 6/14 mmbook** | 解锁全部后续动态实验 |
| T51 | 10-08 12:14 | Booking | RESPONSE-CHANNEL-003 | 6/14 响应通道 | 静态 + 既有日志/NDIS ETL | **SHARED_CONNECTION_CONFIRMED**（大厅 TCP 本身）；重试 3~9s | → T52 |
| T52 | 10-08 12:34 | Booking | RESPONSE-DISPATCH-004 | service=21→type=2→mmbook→vtable→0x632680 | 静态 | **修正 vtable 基 0xDC7274；+0x13C=0x632680；+0x140=0x62E9F0(mmrsv)**；0x632A00 不是 timeout | **REFUTED** 两处旧结论 |
| T53 | 10-08 12:44 | Booking | RESPONSE-PARAMS-005 | A/B 来源 + accepted→28960 | 静态 | 请求侧 A/B=item+0x168/+0x16C；28960 非客户端硬编码；accepted 不直接 connect | → T54 |
| T54 | 10-08 13:17 | Booking | ACCEPTED-WORKER-006 | accepted 消费者/endpoint/worker | 静态 | [0x849B61C] 8 写 2 读；vt+0x14C 序列化入队 [this+0x3A0B0] | 部分被 T55 修正 |
| T55 | 10-08 14:17 | Booking | CONNECT-PATH-007 | 0x818de0/0x803830/endpoint/connect | 静态 | **0x818DE0 = chat.private 私聊状态机 → 006 的 booking→battle 归因 REFUTED** | 砍掉错误轴 |
| T56 | 10-08 14:33 | PvE | MVP-PVE-MATCH-ENTRY-009 | accepted→进 PvE 缺哪条链 | 静态 + 服务端源码/日志 | endpoint 由 findSessions(21/5) 下发 127.0.0.1:28960；battle=UDP/DTLS；BOOKING_TO_BATTLE_CONNECT=UNRESOLVED | → T57 |
| T57 | 10-08 14:49 | 服务端 | **SERVER-PVE-BOOKING-RESPONSE-010** | 恢复 PvE booking response | **改 lobby_server.py**：6/14 分支 senderId 1 → SESSION_ID（备份 .bak_010_20261008_145002） | 根因假设 HIGH-CONFIDENCE | 保留至今（见 §6） |
| T58 | 10-08 14:57 | 动态 | DYNAMIC-VALIDATION-011 | 受控验证 | 尝试起提权代理 | UAC 未批 → **ENVIRONMENT_BLOCKER**；未叠加任何修改 | 10-08-15:14 重跑 |
| T59 | 10-08 15:14 | 动态 | **DYNAMIC-VALIDATION-012** | 真实跑一轮 PvE | run_all.py --secs 600；人工建 booking-push 开关 | wire senderId=SessionId **MATCH**；battle RX=0；开关 ON 时客户端跳过 setRoomData 直接断连重连 | → T60 |
| T60 | 10-08 15:23 | 静态 | SENDERID-AB-ENDIAN-013 | A/B 拆半序 | 静态（无 bs wap） | 判 LOW_HIGH / **MATCH**（HIGH-CONFIDENCE） | **后被 T65/T66 证伪**（字段身份） |
| T61 | 10-08 15:31 | 静态 | BATTLE-TRIGGER-014 | accepted→battle UDP | 静态 | [0x849B61C] 两 reader 均 UI/telemetry；跨模块直接 call=0；BATTLE_TRIGGER_PATH UNRESOLVED | → T62 |
| T62 | 10-08 16:48–17:23 | 静态 | LISTENER-BRIDGE-015 | listener→注册源/vtable/callback | 静态（+UDP socket 侧核查） | **LISTENER→BATTLE = REFUTED 7/7**；ws2_32 IAT 槽位；4 个 UDP 创建点；0x77FBF0=IPX LAN | → T63 |
| T63 | 10-08 17:29–17:37 | 静态 | BATTLE-OBJECT-016 | type-2 network object 是什么 | 静态（RTTI 扫描 + IAT 全枚举） | **type-2 = Demonware lobby TCP 连接**（socket(2,1,6)+connect；"DW_LOBBY_CONNECTED"）；TYPE2_TO_UDP **REFUTED**；修正 _015_glob.py 1 字节回溯假阳性 | → T64/T65 |
| T64 | 10-08 17:57–18:21 | 动态+工具 | ACCEPTED-STATE-DYNAMIC-017 | accepted 分支是否执行 | 用户批准加 nt10 只读采样线程（accepted-state-probe.on），2 轮（40ms / ~6ms） | **ACCEPTED_WIRE=CONFIRMED(9 次)** 但 **ACCEPTED_HANDLER_EXECUTED=NO**；[matching+0x288] 全 0；更正 [0x849B61C] 不是判据 | NEXT_GATE=字段身份 |
| T65 | 10-08 18:48–18:55 | 静态 | AB-FIELD-IDENTITY-018 | matching A/B 是哪个字段 | 静态 | A/B = 21/5 会话对象 **tag 0x0A u64 #7** 低/高 32 位（值 1）；**013 的"=SessionId 低32" REFUTED** | → T66 |
| T66 | 10-08 20:07–20:26 | 动态+服务端 | **AB-ALIGN-019** | 单变量 A/B 对齐实验 | 改 codol_crypto.py 一行 #7 = SessionId；baseline + test；事后恢复 | matching A/B 变 (0x55667788,0x11223344) 与响应 A/B 相等（72 采样点）；客户端把 #7 回显进 mmbook 请求；**但 accepted 分支仍未执行（267 采样点 this288=0）** → **RESULT_CASE=B**；0x6326B9 = NECESSARY BUT NOT SUFFICIENT | NEXT_GATE=ADDITIONAL_ACCEPTED_GUARD |
| T67 | 10-08 20:37–20:43 | 工具 | _020_* + gist | 文档索引/摘要 | 只读脚本 | 产出 _gist_tmp.md（26,678 B） | 作者归属 UNKNOWN |
| T68 | 10-08 20:4x | 审计 | **Golden 哈希复核（本报告新增）** | 核对冻结基线是否漂移 | 比对当前文件与 _golden_hashes.json | **lobby_server.py 与 nt10.py 已 DIVERGED**（见 §6） | 写入 §6/§12 |

> §3 的 T01–T68 覆盖 anchor 之后的全部主线。S2（商城/目录/发行方/玩家）与
> S4（Battle/UDP/DTLS）子任务补充的条目并入 §4 对应领域小节，编号 M-*/W-*。

---

## §4 按领域的完整生命周期

格式：PROBLEM / HYPOTHESIS / ACTION / MODIFICATION / OBSERVATION / RESULT / EVIDENCE /
DISPOSITION / IMPACT。横跨多领域的项在首次出现处给全，后续引用 T-ID。

### 4.1 大厅链路 / 协议 / UI 内容

**T01 采用第三方 kit**（KEPT）
P：我们的 CODOLServer 栈只解出 4 条任务（71/4→71/3→71/7→71/9）就停。
H：第三方实现里编码了我们弄错的语义。
A：复制 F: scripts → REF_LOBBY_KIT；改 GAME_ROOT；给 nt10 补 --root。
O：参照序列 71/4(declared=84, field1="nQloP0oCVWR6RDJS")、71/10、10/12、80/70、12/6、6/5、8/1、8/2、10/21×N。
R：34 条任务、hmac 全 OK、连接稳定约 3 分钟（我们的栈只有 4 条）。
E：HANDOFF_20261005_REFKIT_WORKS.md §1/§3；REF_LOBBY_KIT\_ref\lsg.log。
I：**自研栈在 2026-10-05 15:05 冻结，之后所有工作都移到 kit。**

**T02 推送轮（REFUTED）**
P：34 条任务、hmac 全 OK，仍弹 [100]无法连接大厅服务。
H：客户端需要服务端主动推送（11/21）才认为通道存活。
A：开 ready_push.on + mirror_predicted.on，跑 n10push/n10push2。
O：弹窗照旧；0B/4 频道**从未出现**。注意：该文档引用的 lobby_check.png/v2.png/v3.png 在全工作区**不存在**（glob 0 命中）。
R：作为阻塞点 **REFUTED**。
E：HANDOFF_20261005_REFKIT_WORKS.md §4.5；ready_push.on / mirror_predicted.on（0 B，mtime 10-05 15:59:31）。

**T03 两个真实修复 → ANCHOR**（KEPT）
P：①0x83 用了过期 challenge → 客户端立刻断开、0 任务；②连续 3 次请求 mp_playlists_shipRetail_1.0.0.info，套件里只有 ..._release.info → 致命弹窗。
H：①0x82 可能比 nt10 的 KDF hook 写 kdf_sessions.txt 早约 1 秒，退回 secrets.txt 就用了上一会话的 challenge（9acd25c0bd5d0820 vs 真实 09ac31d14c07bd30）；②同名不同版本。
A：0x82 分支用票据 24B 会话密钥配对 kdf_sessions.txt、最多等 5s 取本会话 challenge，否则退回全局快照；10/21 加同义名回退并放实体别名文件。
M：REF_LOBBY_KIT\lobby_server.py 0x82 分支（约 L1248-1287；5s 循环 L1253、全局 3s L1276）；L534-539 同义名回退；新增 publisher_files\mp_playlists_shipRetail_1.0.0.info。
O：日志 [multi] 本连接会话密钥=… → [challenge 来源: kdf-session, 等待 0.15s] → 解密成功 #1 seq=1 hmac=OK service=71 task=4 declared=84。
R：首帧与参照逐字段一致；任务 34→47；窗口类 CODO；标题"使命召唤online"。
E：HANDOFF_20261005_LOBBY_REACHED.md §1.1/§1.2/§5。
I：**这就是产生 anchor 的修复**；后被 T07 重新框定为"机制正确但触发条件理解不足"。

**T07 重连 hmac=BAD 重新归因**（REPLACED）
P：成功轮之后客户端重连，服务端出现 hmac=BAD + ConnectionResetError(10054)；早先被写成"握手密钥竞态残留"。
H（更正后）：根本没有游戏世界，客户端在大厅找不到可进入的世界，于是正常关闭主连接并重连。
A：重读该轮：主连接 64808 从 16:42:40 活到 16:47:21（约 4 分 40 秒）、56 任务、**hmac 全 OK**、keepalive 正常；重连与 BAD **只在对端关闭之后**出现。
O：文档原文"早先把它写成'握手密钥竞态残留'是错的 … BAD 是结果，不是原因"。
R：RF-1：hmac=BAD-on-reconnect 不是阻塞点；方向转为"提供游戏世界（21/5 session / booking）"。
E：HANDOFF_20261005_LOBBY_REACHED.md §2.5。I：催生会话/房间工作流（T10/T11）。

**T10/T11 靶场开关组与"找世界"**（KEPT / UNKNOWN）
P：需要一个可进入的 session/room。
A（in-window）：建 firingrange-session.enabled、firingrange-battle.enabled（0 B，mtime **10-05 16:55:12**）；把 firingrange-booking-push.enabled 改名 .OFF_CONFIRMED_CRASH（同 mtime）。
O：_lobby_data_audit.py（10-06 22:00）记录 ("11/4,11/13,21/5","房间/匹配","已实现","靶场/房间")；LOBBY_MAP §1.3 记 11/4 空应答、11/13 createRoom OK、21/5 findSessions OK。但 handler 代码注释日期是 **2026-10-03**（pre-window）⇒ in-window 改的只是开关。
R：开关状态 in-window 改变；是否真的跑过世界**无日志可证**（T11 的 n10world×4 无报告、无日志）。
E：开关 mtime；lobby_server.py L19/L587/L784/L806/L458-486；HANDOFF_20261006_LOBBY_MAP.md §1.3。I：战斗入口的解决落在 10-07。

**T13/T14/T30 UIException 诊断通道**（KEPT）
P：几乎每个大厅交互都是空的，但服务端没有报错。
H：service 71 task 7 是客户端自己的崩溃上报通道，答案在里面。
A：_dump_uiexception.py（10-05 18:10）、_dump_tasks.py + _tasks_offset.txt=3866（10-05 18:26）；10-06 再写 _lobby_task_matrix.py（21:40）、_dump_uiexception_bin.py（21:44）。
O：payload 是 lobby_tasks.bin 里的 base64（记录格式 svc(1B) task(1B) len(u32 LE) payload），解出 4 条链：
① #1009 MarketScrollGrid.as:145 → MarketplaceView / SupplyDropView.as:202（商城空白 + 军火箱页面重叠）
② #1009 MatchMakingStripView.as:343→:152→DataManager.as:296/333/218→LobbyController.as:1236/1262（游玩/匹配列表空）
③ #1010 OnboardingChallengesChecklistListItem.as:127 → HomeView.as:271/101（首页挑战）
④ #1125 FilterCategoryButton.as:215/247 → MOTDNotificationsPopup.as:464/131（公告/筛选弹层）
R：43 组 service/task，**21 个未映射**；4 条崩溃链对应 4 类缺失数据源。
E：HANDOFF_20261005_LOBBY_BUGS.md §1；HANDOFF_20261006_LOBBY_MAP.md §1/§6；lobby_task_matrix.csv（41 行）。I：把"一堆孤立 BUG"变成"4 个数据源缺口"。

**T31 mp_playlists 重建**（KEPT）
P：游玩/匹配列表空；MatchMakingStripView #1009；旧占位还在大厅里留了个 TextField 对话框。
H：占位文件 version=1 只有一条 coop；客户端要 PLAYLIST_VERSION=796 + 真实模式/地图。
A：_build_playlists.py（创建于 10-06 21:49:46）重建两个 .info，各自备份。
M：两文件被覆写；备份 21:50:09(262B) / 21:56:06(658B) / 22:07:58(716B) / 22:48:17(716B)。
O：当前产物是 **zlib 压缩文本**，头 "// CODOL local lobby playlists (rebuilt 2026-10-06)"、version 796、gametype war/dm/dom/hp/tag/sr。
R：版本崩溃消失；但模式/地图名仍不对，列表仍空。
E：_build_playlists.py docstring 1-15 / VERSION=796 L26 / PLAYLISTS L46-53；8 个 .bak_before_playlists_*；LOBBY_MAP §7.2/§7.4。I：本区第一个真正的**内容**修复。

**T32/T34 数据源审计与大厅协议地图**（KEPT）
O：占位 publisher 文件 daily_challenge_config.info(67B)、MOTD.info(29B，内容 "; No local message entries.")、activities_v1.info(30B)、whitelist_tester.info(30B)；.info 是 INI，键表在 exe @0x6A9E00；80/70,107,119,173,174,232 全空。
E：_lobby_data_audit.py L21-101；HANDOFF_20261006_LOBBY_MAP.md §7.1-§7.5。
R：给出可重写 INI 的结论；**但 MOTD/挑战/活动的重写在窗内未完成**（UNKNOWN）。

**T38 CLIENT_OBJECT_SCHEMA**（KEPT）
A：从 mem_linear\r_259D0000_06400000.bin 提取 codo.objects::Class\field（客户端自己声明的读取字段）。
O：挑战 11 类、公告 3 类、游玩清单/快速匹配 5 类字段全表；并**更正**旧 HANDOFF：[%s] / %s=%s 属 OpenSSL config 解析器，与 .info 格式无关；catinfo/displayorder/unlockflag 等键在内存与 DLL 中**一处都搜不到**。
E：CLIENT_OBJECT_SCHEMA.md §1-§4 与"重要更正(2026-10-07)"。I：10-07 修复的字段级依据。

**T41 推送序号机制与事故**（KEPT，且是 019 的伏笔）
P：0x85 推送的序号怎么放。
A：lobby_server.py 推送段引入 push_seq_offset.txt（默认 +1000）。
O：代码内记录 2026-10-07 18:06:28 的客户端 seq 冲突事故。
E：lobby_server.py L1173-1198；push_seq_offset.txt mtime 10-07 18:08:45。
I：**与 019 的 marker 疑问直接相关** —— 推送这条路（marker=0x02、跳号）本身就一直不稳。


### 4.2 商城 / 目录 / 购买 / 玩家数据

**T12 全物品发放**（KEPT，副作用牵涉 T33）
P：商城/背包没东西。A：_grant_all_items.py / _set_inventory_count.py。
R：17372 件库存；lobby_allitems.png 17:41:18。
E：marketplace-inventory.json 与 .bak_big / .bak_full / .bak_before_allitems_20261005_171532。

**T15/T17/T18/T21/T26/T29 目录重建线**（KEPT，含多次切换与回滚）
P：客户端能点的很多 SKU 服务端不认识 → Unsupported SKU。
H：把 exe 内嵌目录扩成服务端可用目录。
A：内存扫描（T15）→ marketplace-catalog.json 37615 条；client 版回滚为 exe 版本；full 版 38424 条（未启用）；merged 版启用。
O：HANDOFF_20261006_MAIN.md §1 唯一核心结论：**能不能买只取决于 SKU 在不在服务端目录里**（与类别、货币无关）；§2 根因：客户端真正用的是 6 张 coMarketplace*.csv 加一张 CODOL 专属 conoMarketplaceitems.csv，由内存里 zlib 压缩的 mp\marketplace.json 索引，version=1625160。
R：目录覆盖扩大；80/70 等页仍空。
E：HANDOFF_20261006_CATALOG_LAYOUT / MAIN / MERGED_CATALOG；marketplace-catalog-*.json；marketplace-catalog-client.on 与 -merged.on。I：把商城阻塞从"解析"移到"目录覆盖"。

**T20 名片/称号通道**（KEPT，问题被推到客户端侧）
O：名片/徽章/称号是独立物品类型（pcb/pci/pct/bdg/cnc），有自己的 SKU 体系，走 marketplace 通道；购买后客户端读 codo.objects.CallSignObj 的 cardXxxItemID 判断是否拥有/装备。客户端要读 mp\callsignTitle.csv、callsignBackground.csv、callsignIcon.csv、callsignFrame.csv、callsignNameplate.csv、item_cnc.csv、badgeTable.csv、rankIconTable.csv —— **我们一张都没提供**。
O：实测服务端购买成功（37251/31181/31184），库存也写入了，但客户端军牌定制里仍看不到。
E：HANDOFF_20261006_CALLSIGN_CHANNEL.md §1-§4（exe 字符串 0x6C8D31 / 0x6A31BC / 0x6B624C / 0x6BDE33 / 0x6CA370）。R：**未解决**；MERGE §8.4 进一步判"客户端根本不认 marketplace 库存里的名片拥有关系"。

**T22 购买解析修复**（KEPT，本区最实在的修复）
P：4/5 号背包、副武器、近战"点购买没反应"。
H：第三方 C# 用单一 58B 硬模板逐字节比对，只认普通直购帧形；其它帧形长度/可选字段不同 → 模板必失败 → Unsupported purchase parameters。
A：改为按类型标签 TLV 解析（0x08 u32 / 0x03 u8 / 0x01 bool / 0x10 string / 0x13 blob），取 vals[1]=sku、vals[3]=qty。
O：回测三方实测帧 sku=22858 qty=1 正确；实机 购买成功 sku=32223 qty=1，GP 883599→819999（真实扣款）。
E：HANDOFF_20261005_LOBBY_BUGS.md §3.1；HANDOFF_20261006_PURCHASE_FIX.md 与 BUY_MATRIX.md。I：先修好解析，才暴露出真正的目录覆盖问题。

**(S2 备注)** 商城/目录/发行方/玩家一线的完整时间线与逐项生命周期由并行考古子任务 S2 覆盖；
本报告 §3 时间线已含其主干（T12/T15/T17-T29/T33，以及 T48-T50 的发行方恢复），
其产出物包括 mkt_assets\*.csv、sku_arrays\、marketplace_store.py、market_skus.py 等。
若需字段级细节，见 §18 证据索引中 S2 列出的具体路径。

**T27 public.result 尾部注入**（REFUTED / ROLLED_BACK）
P：买到的名片从不出现在"已拥有"。
H：public.result 尾部 125 个 0x07 槽位等于装备清单。
A：_patch_public_tail.py 加服务端 _inject_public_tail()，注入 22381/22384/15166/29892/16339/122/7110/29767（8/3 存档时也注入）。
O：客户端行为完全不变。
R：**REFUTED** —— 125 槽不是名片拥有关系来源。
E：HANDOFF_20261006_MERGED_CATALOG.md §8.3；public-tail-inject.on.rejected_20261006（133 B，21:29:38）；public.result.bak_before_tail_20261006_212954。
I：关掉一个诱人的死胡同。

**T33 SKU sentinel 探针（本区最严重的回滚事故）**（ROLLED_BACK / REFUTED）
P：80/70 返回空 → MarketScrollGrid.as:145 数据源为 null → 商城空白加军火箱页面重叠（同一根因）。
H：只要类型标签对（String=10、int=07、Boolean=01、currency=u8=03），自造 SKU 列表就能被解析。
A：market_sku_probe.py（22:22:15）加 _scan_probe_sentinels.py（22:23:16）；发 sentinel（name=PROBE0、id=0x11111111、productId=0x22222222、price=0x44444444、currency=0x55）；marker 文件 market-sku-probe.on.tested_ok、market-sku-probe.txt=1、market-sku-probe-count.txt=1（全在 22:24:26）。
O：内存里有 32 个 sentinel，但**真机商城与仓库变灰、角色被锁**；协议层还活着（客户端继续 80/203、80/230、93/131，甚至完成一次购买，库存 7614）。
R：**REFUTED** —— sentinel 进了内存不等于被解析；结论：标签对但 SKUObj 字段顺序不对。静态追到 exe 0xBA3710 → 0xBA3A05 call 经 [edi+0x608] 加 0x0C → TenProxy vtable 0x128305D0 slot 0x0C = 0x1281137F 跳 0x12817980，真正的 parser 在 tp_runtime.bin（167,936 B）之外。
回滚：marketplace-skus.on.rolled_back_20261006（13 B）、marketplace-skus-allow-unsafe.on.rolled_back_20261006（24 B），均 22:28:24；安全空页恢复；重启游戏后恢复。
E：HANDOFF_20261006_LOBBY_MAP.md §3.1 与 §8.1-§8.3；上述脚本与 marker 文件。I：教训写进两篇文档（LOBBY_MAP、MAIN §7.3）：**不要猜 80/70 的线格式**。

**T28/T29 货币字段宽松与"买到但不认"**（KEPT，部分解决）
O：MERGE §8.2 把名片失败重新归因为**货币字段**（目录写 CP、客户端请求 GP），marketplace-currency-lenient.on 在临时副本上验证 39038/39601/40284/41526/45137；§8.4 结论：客户端不认 marketplace 库存里的名片拥有关系。
E：HANDOFF_20261006_MERGED_CATALOG.md §8.1-§8.6；marketplace-currency-lenient.on。I：阻塞点被推到**客户端侧**。

**K-02 80 系列空页（窗内未修）**（UNKNOWN）
O：请求已解出（70 与 107 带 1625160；119 带 0x6CA62CD7；173 带 u16(700)；174 带 700；232 为空串），80/70 被定为本区 P0。
R：**未修**。E：HANDOFF_20261006_LOBBY_MAP.md §1.1/§2/§3.3/§7.5；lobby_task_matrix.csv 行 80/70 至 80/232。

### 4.3 发行方（Publisher）

**T48 PUBLISHER_FAILURE_SPEC-001**（KEPT）
P：客户端在任务数到 34 时弹 EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE。
H：某组 .info 发行方文件加载失败。
A：静态（image_best.bin）加运行日志比对。
O：ERROR_STRING_XREF=0x0066A827 唯一引用 0x00DC9C6C；FAILURE_FUNCTION=0x0066A650（inc [ebx+0xC7AEAC8] / cmp 3 / jg）；调用者 0x50E9B1 与 0x50EA7B 的分发表 push 8 个 .info 名；日志记 10 个 .info 全"缺"。
R：FAILURE_CONDITION=同一 publisher 文件连续 3 次加载失败；FAILURE_REASON=NOT_FOUND（CONFIRMED）；GAME_STAGE=内容/发行方文件准备（STRONG_CANDIDATE）。
E：DEV-BOOKING\PUBLISHER_FAILURE_SPEC-001.md §1-§7。

**T49 PUBLISHER_FILE_RECOVERY-001**（KEPT，方案由 T50 执行）
P：原始 .info 在哪？为何 Golden 冻结后必失败？
H：文件其实存在，只是放在别处。
A：只读全盘搜索加恢复矩阵加 SHA256 核对。
O：原始文件在 REF_LOBBY_KIT\publisher_files\（12 个含 manifest.json）；manifest 记录 name/encoding/wireBytes/plainBytes/plainSha256/wireSha256/evidence（反汇编地址 0x50dc10 / 0x50e500 / 0x50eb80 / 0x66d1f0）；客户端期望路径是 lobby_server.py 同目录下的 publisher_files\name.info（lobby_server.py L257/L533）。
R：根因判为 GOLDEN_DATA_DIR_INCOMPLETE（缺 publisher_files、player_profiles、user_files）；11 项 SHA256 全对。
E：DEV-BOOKING\PUBLISHER_FILE_RECOVERY-001.md §1-§3。I：指向 T50。

**T50 PUBLISHER_FILE_RECOVERY-002（真实数据恢复）**（KEPT）
P：恢复后 fatal 是否消失、6/14 是否发出。
A：**SERVER/DATA 改动** —— 复制 REF_LOBBY_KIT 到 DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT（含数据目录），复制清单含 publisher_files(12)、player_profiles(public.result/secure.result)、user_files(the.json)、mkt_assets、sku_arrays，以及 9 个运行必需 .py。
O：10 个 publisher 全部下发（09:21:50）；窗口变 class=CODO title=使命召唤online；**09:23:45 首次真正发出 6/14 mmbook**（09:23:51 与 09:23:55 重试）；payload 0a 01 … 13 08 1d 19 00 00 00 加 "mmbook 796 AQAAAAAAAAA= 0"；endpoint 127.0.0.2:3074。
R：RESTORED_IN_DEV / PUBLISHER_SERVE_CONFIRMED / PUBLISHER_FAILURE_RESOLVED / BOOKING_GATE_REACHED 全 CONFIRMED。
E：DEV-BOOKING\PUBLISHER_FILE_RECOVERY-002.md §2-§6 与 §8（含 SHA-256 基线）。I：**这是一切后续动态实验的前提**。

### 4.4 Booking / PvE / mmbook（10-07 19:22 → 10-08 20:26）

**T45 静态阶段 001–004**（KEPT，含两处自我更正）
P：客户端到底期待什么 booking 响应？0x632680 被谁调用？A/B 从哪来？
H：客户端 exe 内自带期望字符串；响应走虚分派。
A：静态（EXE 字符串表 + 运行期镜像反汇编 + 寄存器同源虚调用扫描）。
O：0x6B29B0 有 "mmbook accepted"、0x6B29D4 有 "mmbook timedout"；0x632680 没有直接 call，只有两个 vtable 槽；唯一 +0x140 间接调用 0x91B19C 是 1 参数且 test al,0xf，与 ret 0x14（5 参数）不符。
R：CONTRACT-001 定解析器 0x632680；SPEC-001 证 0x91B19C 不成立；SPEC-002 定 0x62F6F0 是 A/B 真实写入、reservation 数组 this+0x75D8 / stride 0x238、filler 0x62F840；SPEC-003 定 index 来源 0x637720、数组拷贝 0x6379E0；SPEC-004 证 callback 槽 +0x1610 进不了 0x632680，宣告 STATIC_RECOVERY_LIMIT_REACHED。
E：DEV-BOOKING 各篇。I：把卡点从"找不到 parser"推进到"parser 已在手"；SPEC-004 的"静态到极限"判断后来被 004 用分派器文本比较打破。

**T46 BOOKING_RUNTIME_TRACE-001**（ABANDONED）
P：能否断点捕获 0x632680 入口与 5 个参数。
O：提权代理可用（debug_privilege=true），但 _dyn100_mem.py 只有 CreateProcessW(SUSPENDED)/OpenProcess/ReadProcessMemory/VirtualQueryEx，断点类 API 命中 0；Frida 因 ACE 与 Golden 手册禁令不可用。
R：**INSTRUMENTATION_BLOCKED**（权限不是瓶颈，能力是）。I：确立后续只用"只读采样 / 网络层 / 服务端"三种观测 —— 这条纪律一直影响到 017/019。

**T47 BOOKING_RUNTIME_NETWORK-002**（KEPT）
P：6/14 之后客户端是否收到响应。
A：netsh trace（NDIS，payload-capable）+ 窗口文本只读抓取。
O：时间线 20:01:54 启动 → 20:02:22 握手完成 → 20:07:28 对端关闭；lobby_srv.log 搜 mmbook 0 命中；窗口弹出 ["致命错误","确定","EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE"]；端口计数 3074=1875、28960=33、8443=525、8444=569、8446=508；XML 中 mmbook / MM_RESERVE_CMD_REQUEST / booking 全 0 命中。
R：6/14 **NOT_SENT**；阻塞是发行方文件；28960 的 33 次不构成 Battle 证据。I：主线转入 T48。

**T51–T53 响应通道 / 分派 / 参数**（KEPT，含两处 REFUTED）
P：6/14 的响应通道是哪个 socket？service=21 如何走到 0x632680？A/B 精确来源？
A：静态加既有日志与 NDIS ETL（booking_ch003.xml，65,942,694 B）。
O：6/14 与 71/4、28/1、21/5、11/13、11/4 共用同一条 TCP（local 127.0.0.1:57548 → remote 127.0.0.2:3074）；重试间隔 3~9 秒（均值约 5.5）；0x7F153C push 6 / push "mmbook" / call strncmp；0x7F1554 mov ecx,[0x82e13fc]；0x7F155C mov eax,[eax+0x13c]；0x7F156F call eax（5 栈参数）；0x62C025 mov [ebx],0xDC7274；兄弟分支 mmrsv 走 +0x140=0x62E9F0、mminvite 走 [0x82e1404]+0xc；0x632A00 实为 ret 4 的 0x1D0 字节复制方法。
R：BOOKING_RESPONSE_CHANNEL = **SHARED_CONNECTION_CONFIRMED**（无独立 booking socket）；BOOKING_RESPONSE_DISPATCH = CONFIRMED；**修正 vtable 基 0xDC7274、+0x13C=0x632680、+0x140=0x62E9F0**；**REFUTED：0x632A00=timeout handler**；A/B=dispatcher arg1/arg2；28960 非客户端硬编码常量（0x7120 只出现在 OpenSSL 数据）。
E：RESPONSE-CHANNEL-003 / DISPATCH-004 / PARAMS-005；runtime_net_ch003/booking_ch003.xml。

**T54/T55 accepted 消费者与 0x818de0 归因更正**（KEPT + REFUTED）
P：谁消费 accepted 状态？0x818de0 是不是 booking→battle worker？
O：[0x849B61C] 14 处引用 = 8 写 2 读（0x7CB1E2、0x7CFA87）；vt+0x14C=0x629730 序列化入队 [this+0x3A0B0]；0x818DE0 的 6 路跳表只有 state 4 实现且引用 "chat.private"。
R：ACCEPTED_STATE_CONSUMER=CONFIRMED；**REFUTED：0x6334xx→0x818de0 是 booking→battle**（它是私聊状态机）。I：砍掉 accepted→queue→battle 这条错误轴。

**T56 MVP-PVE-MATCH-ENTRY-009**（KEPT）
P：从 accepted 到进 PvE 缺哪条链。
O：GAME_IP=127.0.0.1 / GAME_PORT=28960 由 session_objects() → build_session_record(21/5) 下发；battle 为 UDP 0.0.0.0:28960；0xB81EF0 唯一上行链 0x7f2600(DW_DNS_*)→0x7f3600→0x7f3890→0xb82070→0xb81ef0→0xBA4080。
R：BOOKING_TO_BATTLE_ENDPOINT=CONFIRMED；BOOKING_TO_BATTLE_CONNECT=UNRESOLVED；**REFUTED** 五条（0x818de0=booking worker、0x803830=socket、transport connect=battle connect、"mmbook accepted" 含 endpoint、battle=TCP）。

**T57 SERVER-PVE-BOOKING-RESPONSE-010（第一次真实改 booking response）**（KEPT，见 §6）
P：senderId=1 的靶场信封为何不触发 PvE battle。
H：senderId 必须等于 findSessions 的 SessionId。
A：**改 lobby_server.py**：6/14 分支 instant_push_body(1,…) → instant_push_body(SESSION_ID,…)（备份 .bak_010_20261008_145002）。
O：SESSION_ID=0x1122334455667788（L458）；靶场用 MISSION_SESSION_ID_BLOB=[1,0,…]。
R：格式/触发/根因 = HIGH-CONFIDENCE；MINIMAL_FIX = CANDIDATE。I：**这就是 019 后来认定"破坏了 A/B 相等"的那次改动**（Golden 时信封 senderId=1，与会话对象 #7=1 本来就相等；改成 SessionId 后才不等）。

**T58/T59 动态验证 011/012**（BLOCKED → 完成）
P：修复后 wire senderId 是否正确？客户端是否连 28960。
O：011：两次等待共约 13s，elevated_agent.json 未生成，ping 失败 → **ENVIRONMENT_BLOCKER=CONFIRMED**，未做任何测试、未叠加修改。
O：012：提权代理 pid 12244 debug_privilege=true；run_all.py --secs 600；人工建 firingrange-booking-push.enabled；findSessions 解析 [1, 0, 10, -695030357]；roomId=0x1122334455667788；wire 信封 0A 88 77 66 55 44 33 22 11 加 10 "localhost"；battle_srv.log 15:08–15:13:30 全程 收包=0；开关 OFF 时客户端继续发 11/4 setRoomData，开关 ON 时跳过 setRoomData 直接关闭重连并出现 ConnectionResetError(10054)。
R：SENDERID_SESSIONID_MATCH=YES；CLIENT_UDP_28960_SEEN=FAILED；排除 Case4，落 Case2/Case3 之间。

**T60 013 A/B 拆半序**（HIGH-CONFIDENCE → 后被 REFUTED）
O：A=[ebp+8]、B=[ebp+0xc]；0x62F736/0x62F73C、0x62F742/0x62F748；路径无 bswap/rol/ror/xchg。
R：SENDERID_AB_MAPPING=LOW_HIGH；AB_CORRELATION_PREDICTION=**MATCH**；NEXT_GATE=不再改 booking response。
⚠ **其前提"item+0x168 = SessionId 低 32 位"被 017 实测与 018 静态共同证伪**（见 §10）。端序部分（无 bswap）本身未被推翻。

**T61/T62/T63 014 / 015 / 016**（KEPT，其中 015 的两处被 016 更正）
O：014：[0x849B61C] 两 reader 0x7CB1E2/0x7CFA87 下游均 UI/telemetry；DTLS/ECDH/secp224 字符串在 0xE3xxxx；matching/lobby → battle 直接 call = 0。
O：015：广播 site 0x632824..0x632844（arg 1,0）与 0x63289E..0x6328B3（0,2），被 0x63281E call [esi.vt+0x5C] / 0x632822 jne 门控；容器 [0x82E13FC]+4 = {head,tail,count}；节点 12B；7 个注册点；**7 个 listener 的 vtable+0x24 全部锁定 = 5×0x4F7590(ret 8) + 0x738E70(wargod 排位) + 0x7CAF30(UI/CEF)**；ws2_32 IAT 槽 0xCA84D4..0xCA855C（socket 0xCA8548 / connect 0xCA84F0 / htons 0xCA8550）；4 个 UDP 创建点；0x77FBF0 = socket(AF_IPX=6,SOCK_DGRAM,NSPROTO_IPX=1000)。
O：016：0x62FDE0 完整反汇编含 GATE-A（[this+0x1C]）与 GATE-B（[this+0x10758]|[this+0x1075C]）；0xB7A670 语义 = byte[sing+0x4F8]!=0 且 0xBA0780([sing+0x4F4])==2；transport vtable 0xD5A4F4（邻字符串 HMAC mismatch / stun.*.demonware.net）；ctor 0xBA2800 size 0xAE8；唯一创建链 0x7F3890→0xB82070→0xB81EF0→0xBA4080→0xC73900→0xC76920；**0xC768D0 = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)**；0x7F278E 引用 "DW_LOBBY_CONNECTED"；RTTI 全镜像 0 条。
R：LISTENER→BATTLE = **REFUTED 7/7**；TYPE2_TO_UDP = **REFUTED**（type-2 = Demonware lobby TCP 连接）；**更正 015 的门控描述（漏两道前置守卫）**；**证伪 _015_glob.py 的 1 字节回溯假阳性**（0x470172 真实 mov 被读成 or）。

**T64 ACCEPTED-STATE-DYNAMIC-017**（KEPT）
P：客户端是否真正执行 0x632680 的 accepted 分支。
H：若 byte[matching+0x288] 的唯一写入点 0x63280B 执行过，该字节必保持 1（0x62F6C0 不触碰它）。
A：**经用户批准在 nt10.py 加只读采样线程 _accprobe**（开关 accepted-state-probe.on，5ms 名义/6~11ms 实测，13 字段，仅 ReadProcessMemory）；Run1 420.9s、Run2（含 retry）；另写 _017_scan_c686.py 全镜像扫 mov byte [reg+disp32],imm8（2462 条，disp=0x288 且 imm=1 仅 0x63280B）。
O：ACCEPTED_WIRE 9 次实际发出（Run1 4 + Run2 5）；Run1 281 行、Run2 433 行采样，**this288_byte=1 命中 0**；Run2 18:12:48.338 观察到 this278=0x0101 且 A=0x00000001 B=0x00000000；[0x849B61C] 0→1 但同一样本行 this288=0；battle 收包恒 0；客户端 9/9 收到 push 后立刻优雅关闭大厅连接；附带**动态证实 016 模型**（t_C8 1→2、t_5E8 0→1→2→3、net4F8 0→1、dw 0x01→0x02）。
R：**ACCEPTED_HANDLER_EXECUTED = NO**；机制 = 0x6326B9 cmp 0x55667788, 1 → jne 0x632916 第一守卫直接退出；RESULT_CASE=C。**并更正 [0x849B61C] 不是 accepted 判据**。

**T65 AB-FIELD-IDENTITY-018**（KEPT）
P：matching+0x3A048/+0x3A04C 的字段身份与来源链，为什么是 (1,0)。
A：严格 STATIC。
O：0x62F6F0 三个调用点的 edi 均为 matching+0x7470+idx*0x238；数组 50×0x238=0x6EF0（ctor 0x62C0CD 循环 0x31+1 次）；元素类 ctor 0x806B50（size 0x238、vtable 0xDC79F0、+0x168/+0x16C 初值 0）；元素 vtable[0]=0x806F20 是反序列化器：0xB95D70 吃 5 个字段（blob、blob、u32、u32、u32 → +0x18/+0x10/+0x11C/+0x120/+0x124），0xB76A30（tag 0x10）→ +0x128，**0xB769A0（硬编码 tag 0x0A 读 8 字节，写 [eax] 与 [eax+4]）→ +0x168/+0x16C**，0xB76A30 → +0x170；客户端过滤器 0x637950 用 rec+0x124 <= 1，与服务端 #5 u32 1 数值与位置双吻合；全镜像 +0x168/+0x16C 写点 119 处，本类唯一非零生产者即 0x806F20。
R：**A/B = 21/5 会话对象 tag 0x0A u64 #7 的低/高 32 位（值 1）**；RESPONSE_AB(0x55667788,0x11223344) != MATCHING_AB(1,0)；FIELD_IDENTITY_STATUS=CONFIRMED；**REFUTED：matching+0x3A048 来自 SessionId 低 32 位**（SessionId 走 #2 tag 0x19 blob → rec+0x10）。

**T66 AB-ALIGN-019（本轮之前最后一次单变量实验）**（KEPT + 服务端 ROLLED_BACK）
P：把 findSessions #7 u64 对齐到 SessionId，能否解除第一守卫并触发 accepted。
H：A/B 对齐后 0x6326B9 通过 → accepted 分支执行 → battle UDP。
A：**服务端单变量** —— codol_crypto.py 仅 L542 ob.u64(1) # 7 → ob.u64(0x1122334455667788) # 7；#28、#2、lobby_server.py 均未动；baseline 20:08–20:13、test 20:21–20:24；备份 .bak_019_20261008_200724；事后恢复并 SHA-256 校验。
O：BASELINE mmbook payload 以 0a 01 开头、probe 328 行 A=1 共 11 次；TEST mmbook payload 以 0a 88 77 66 55 44 33 22 11 开头（**客户端把 #7 回显**），probe 267 行 A=0x55667788 共 72 次、B=0x11223344 共 72 次（对齐成功）；**this288_byte=1 命中 0、ALERT 0**；baseline 与 test 客户端对 push 的反应逐条同型（对端关闭加立即重连）；Get-NetUDPEndpoint 28960 只有自己的监听 pid 2404。
R：**RESULT_CASE = B**；AB_ALIGNMENT=CONFIRMED；**AB_GUARD_CAUSALITY = 0x6326B9 = NECESSARY BUT NOT SUFFICIENT**；ACCEPTED_HANDLER_EXECUTED=NO；NEXT_GATE=ADDITIONAL_ACCEPTED_GUARD（首选"消息通道 marker 0x02 推送 vs 0x01 应答对象"）。
I：**当前主线终点**。

### 4.5 Battle / UDP / DTLS / 净码（S4 考古 + 主 agent 复核）

**B-00 battle_server 基线（前置依赖，anchor 后被持续使用）**（KEPT）
battle_server.py 实现：NAT 穿越 29B（首字节 13→12，要求尾 7f 00 00 01 20 71）；DTLS init 16B→38B cookie（打 serverTag）；cookie+pubkey 219B→纯 Python ECDH P-224（secp224r1）；传输密钥 = SHA1(shared_x_28B_be || 0x01×16) 取 24B；数据帧 06 02 <serverTag> <seq> <hmac8> <len> <cipher>（SHA1 派生 keystream + HMAC-SHA1[:8]）；OOB netchan/stats/heartbeat。
每次启动打印 securityKey(16B)=0101…01、idx45 关、viewangles 下发、方向按 yaw 原样、位置镜像客户端预测。
E：battle_server.py:1-24、226-355、401-540。

**B-01 配置锁定与"监听器健康、客户端缺席"**（KEPT，观测）
10-05 至 10-07 共 **64 次** battle_server 启动：1 次无 mirror（10-05 15:49:39，pre-anchor），**63/64 开启 mirror_predicted.on**；52 次 "game state 文件 (缺)"，12 次 "(259 字节)"（全部为 10-07 14:44:28 之后）；[stat] 行 2499 条为 RX=0，仅 4 条非零（都在 10-06 21:28 那次）。
I：任何"我们修好了战斗服"的说法都必须与"客户端从未拨入"分开陈述。

**B-02 2026-10-05 16:56:33 重复 bind（anchor 后 1 分钟）**（KEPT，防护有效）
同一秒两个 battle_server（pid 9768 与 pid 4076）；9768 打 [*] 已监听，4076 无监听行（全日志唯一一次）。因故意不设 SO_REUSEADDR，重复 bind 被拒。
E：battle_srv.log:111-120 与 :121-129；battle_server.py:1429-1439；run_all.py:719-723；lobby_server.py:1361-1362。
I：证明"僵尸战斗服抢端口"这一失效模式已关闭 ⇒ RX=0 不是端口归属问题。

**B-03 2026-10-06 21:28 唯一一次完整真实握手（本线最重要的正面证据）**（KEPT）
对端 127.0.0.1:22011；RX#1/#2 为两个相同 29B NAT 探测；RX#3 为 16B DTLS init（clientTag 16850）；RX#4 为 219B cookie+key；RX#5-#7 为 54/463/855B 数据帧，解出 getchallenge "e7c8a98a6b4c2d0e"、connect（\name\M7-E8S6Client）、stats；RX#8 起 30B OOB 心跳 ×9，随后 ~60 秒内每 ~0.5 秒一个 14B usercmd。
统计：收包=155 NAT=2 init=1 keyex=1 data=151 会话=1；传输密钥 22d0fa6843b44afe0bedd2777d22f7c1；**TX_GAMESTATE=0**；21:29:24-25 客户端连发 20 次 cancelConnect 后停止。
R：握手 + stats + 心跳全部可用；该次服务端**从未下发 game state**。
E：battle_srv.log:2320-2564；解码进 battle_selftest.py:10-15、57-59、365-372。
I：(a) 否定"协议层没实现"；(b) 证明客户端在等服务端的第一帧 game state。

**B-04 修复：不等客户端就下发首帧 game state 与快照**（KEPT，本线最有价值的修复）
P：客户端 connect 后卡在"等待连接/等待玩家数据"。
H：服务端把 game state 门控在 ready（只有解析到 usercmd 才置位），快照门控在 OOB gamestateupdate，而真实客户端从不发 gamestateupdate。
M：battle_server.py 三处 —— connect 时置 assoc["connect_done"]=True 与 gamestate_due=now+0.2（:603-617）；把 pump_gamestate 门控放宽为 ready or connect_done（:727-736）；发送 game state 时启动 snapshot_due（:754-761）。
O：**10-07 15:01:00 首次出现 TX_GAMESTATE seq=1 state=259B**，随后 128Hz 的 141B 运动快照。
E：battle_server.py:481-485、605-617、725-763；battle_srv.log:3024-3036、3194-3234；BATTLE_SERVER_PROTOCOL.md §0/§3。
⚠ **SOURCE_CONFLICT SC2**：文档把 10-06 那次 TX_GAMESTATE=0 归因于 ready 门控；但同一次会话的日志第 34 行写 "game state 文件: firingrange-gamestate.bin (缺)"，而 battle_server.py:738-739 在文件缺失时直接 return。**两个原因同时成立**，文档只讲了一个。两边都保留。

**B-05 恢复 firingrange-gamestate.bin（259 B）**（KEPT）
从 F: 证据目录复制；启动日志由 (缺) 变为 (259 字节)（10-07 14:44:28）；随后 TX_GAMESTATE state=259B。
⚠ 该文件 mtime 是 2026-10-04T02:59Z（复制保留了源时间戳）—— **不要用 mtime 判定恢复时间**，日志把它定在 10-07 14:44。

**B-06 快照字段序列对齐（S4 认为是最深的静态战斗工作）**（KEPT，含一个被证伪的假设）
假设1（后被证伪）：以 reference/demo-player-fields-trace.json 为准 → "真实快照只有 140 bit，我们差很多"。
假设2（被采纳）：以 playerstate-motion-trace.json 为准（completed=True、totalBits=497、reads=173）。
A：新写 snapshot_diff.py 与 _idx84_decode.py；把 idx21..24 改写为武器槽三元组（present? + has? + 11bit weapon，:1145-1178）；补上 clips/owned/reserve 段缺失的 w.index(84,prev) 标记（:1210-1285）；默认去掉 idx219（:1203-1206）；idx45 保持关闭。
O：snapshot_diff.py 报 **29/29 对齐**，无缺无多；帧由 124B 增到 141B。
R：真实字段**顺序**吻合；idx45/idx219 的**语义**仍未知。
E：snapshot_diff.py:10-27、35、82-114；battle_server.py:1145-1285；BATTLE_SERVER_PROTOCOL.md §7.1-§7.9。
⚠ 权威 trace JSON 是**外部文件**（F: 盘 reference/playerstate-motion-trace.json），**不在本工作区**（glob 0 命中）；只有解码结果硬编码在 battle_selftest.py:460-462 里。

**B-07 battle_selftest.py：离线回归套件（新工具，本线最强存活产物）**（KEPT）
FakeClient 自行推导同一 ECDH 传输密钥，发真实 16B DTLS init、真实 getchallenge/connect 串、826B stats、心跳、以及真实的 14B usercmd。
13 条断言：NAT、cookie、key ack、getchallenge、connect、stats、heartbeat、第 8 步服务端主动下发 game state、第 9 步数据帧、第 10 步真实 14B 被解析、第 11 步快照自动开始、第 12 步 idx21..24 存在、第 13 步 29/29 序列。
**[VERIFY] 本轮（10-08）在隔离临时副本上重跑：13/13 全绿，exit 0**；89 数据帧、278 快照帧、TX_GAMESTATE seq=1 state=259B。
E：battle_selftest.py（:62-259、:332-472）。
I：**战斗服的声明现在可以脱离游戏独立复现** —— 这是战斗线最可靠的资产。

**B-08 工具副作用：真实 10-06 客户端 stats 被覆盖**（KEPT，原内容 UNKNOWN）
firingrange-clientstats-last.bin（826B）在 10-06 21:28:20 由真实客户端写入；10-07 15:00-15:03 与 19:04-19:05 被 selftest 的随机字节覆盖（battle_selftest.py:217-227 用 random.randrange(256) 填 826B）。**不要再把它当抓包证据。**

**B-09 大厅 hmac=BAD 断连循环（战斗 E2E 的前置阻塞）**（KEPT）
P：10-07 15:26 那轮根本没到战斗服，因为大厅连接被 reset。
H：pick_keyset 未命中时猜了错误的密钥组。
A：改为不使用猜的密钥组，帧留在 pending 等正确密钥组通过 HMAC。
O：修复前 hmac=BAD marker=0x4F service=133 declared=79273349，3 次断连；修复后 **88 hmac=OK / 0 BAD**，完整 40 项会话。
I：10-07 15:26 的 RX=0 由大厅 bug 解释，不是战斗服的问题。

**B-10 PvE 地图不匹配与 coop_map.txt 自纠环**（KEPT，部分）
客户端 mmstart 报的 map 与我们 21/5 回的不是同一张；三轮出现三张不同地图（coop_take_mp_fav_tropical、coop_chopper_mp_suburbs、coop_evasion_mp_con_spring），所以硬编码永远不可能匹配。改为把 mmstart 的 map 写进 coop_map.txt，下一轮 findSessions 用。**只能滞后一轮收敛**；coop_map.txt 现在是 0 字节空文件。

**B-11 mmbook accepted 推送崩溃与三个被否证的修法**（ROLLED_BACK / REFUTED / 保留但禁用）
P：在 6/14 上推 mmbook accepted 会让客户端断连/ClientException（17:45-18:13 三次点击，然后 9/9）。
① replyId 改为独立计数器 → 仍崩 → **ROLLED_BACK**
② 认为是推送抢了客户端的帧序号（客户端 seq 13、14 后推 seq=15，客户端又发 15）→ 改 request_seq + 1000 偏移 → **仍 9/9 断连 → REFUTED**
③ 认为信封是"靶场专用信封用在 PvE booking 上"（客户端 mmbook 解出 "mmbook 796 AQAAAAAAAAA= 0" 即 playlist 796 = PvE，而回的是第三方的靶场 reply：senderId=1、localhost、service 21）→ **KEPT 为最佳解释**
M：把 firingrange-booking-push.enabled 改名 .OFF_CONFIRMED_CRASH；关掉后不再崩，但客户端每 5 秒轮询 mmbook 并显示"服务器繁忙" —— 推送既是毒药又（似乎）是唯一的进度信号。
⚠ **SOURCE_CONFLICT SC4**：10-07 10:34 那次同样的推送**没有**立即断连（客户端继续 #55/#56/#57，直到 10:37:02 才关闭）。**"推送总会断连"不普适**；条件差异 UNKNOWN。

**B-12 "不存在独立的靶场入口"**（REFUTED）
playlists=[1,2,3,4,5,6,10]，gametypes=[coop,dm,dom,hp,sr,tag,war]；playlist 10（Coop Mission）里含 coop_train_mp_firingrange，即靶场是一个 **coop 关卡**；所有观察到的 21/5 findSessions payload 逐字节相同，都解析为 playlist=10。
R：**没有任何客户端选择能到达 21/5**；靶场 session 对象只由我们自己的路由产生。I：**"直接用靶场"这条退路死在这里**。

**B-13 强制靶场 session 对象：仍然 RX=0（10-07 10:34/10:39）**（REFUTED）
三开关全开、客户端点 PvE：10:34:57 findSessions payload 解析为 playlist=10，却被回以靶场 mission session（268 字节、map=mp_firingrange、GameType=0x1000007、MaxPlayers=1）；6/14 mmbook → push accepted（seq=52）；mmstart → 第二次 push（seq=54）；11/4 setRoomData 回显 ×2 + game-start push；10:35:02 收到 71/7 UIException，但会话活到 10:37:02 才对端关闭。**该轮 battle 日志 RX=0。**
I：靶场 session + booking accept **没有**产生战斗连接（对本客户端版本）。

**B-14 GOLDEN-LOBBY-001 冻结（战斗相关事实）**（KEPT）
冻结 22 文件 + SHA-256；battle_srv.log 冻结在 322,463 B（收包=0）；firingrange-booking-push.enabled.OFF_CONFIRMED_CRASH 冻结为"禁止开启"。battle_server.py sha256 71bb7beb…、battle_selftest.py 06b8b5a8…。
⚠ 冻结快照**已包含** anchor 之后的修复（selftest、coop_map.txt、push_seq_offset.txt、gamestate 文件），所以它**不是**"修复前基线"。

**B-15 通宵运行到 2026-10-08**（KEPT，观测）
10-07 18:10:40 起的战斗服一直跑到 10-08 09:41（备份日志 331,527 B），每个采样都是 RX=0。I：RX=0 不是进程死亡造成的。

**B-16 2026-10-08 静态逆向 booking→battle 触发（DEV-BOOKING 全系列）**（REFUTED ×5 / UNRESOLVED）
见 §4.4 的 T56/T61/T62/T63。战斗侧结论：客户端内部**独立于我们的服务器**确认了 P-224/DTLS（"DTLS"@0xd55db0、"ECDH"@0xd5611d、"secp224"@0xd3d628，表在 0xE3xxxx）；但 matching(0x62-0x63)/lobby(0x7f) → battle(0xE3-0xE5) **直接 call = 0**。
附录：0x804A82 端口表 8300-8316/8400/8600 → 仅 CANDIDATE，无引用链。

**B-17/B-18 2026-10-08 动态验证与 A/B 对齐**（见 §4.4 T64/T66）
战斗侧补充：accepted 分支从未执行；guard 0x6326B9 因构造失败；**所有 battle_srv.log 采样 RX=0**；客户端无任何到 28960 的 socket。

**B-19 2026-10-08 恢复工作区后的战斗运行（全 RX=0）**（KEPT，负结果）
10-08 的每一轮（15:07:30→15:46:01、18:02:13→18:09:43、18:10:11→20:07:43 baseline019、20:08:13→20:13:43 test019、20:14:16→20:20:46 test019b、20:21:16→20:47:22）**全部 RX=0**。I：发行方数据恢复没有改变任何东西，阻塞点回到客户端侧 booking 接受。

**B-20 持续 RX=0 意味着什么/不意味着什么**（KEPT）
RX=0 对 anchor 之后**每一次真实客户端运行**都成立；但**不是全文件性质**：10-06 21:28 服务端收到 155 包并记录完整握手。
客户端流量去了别处：n10_battlefix_20261007.txt 中 "28960" **0 次**；PvE 那轮发往 101.67.36.18:10035（gcloudvoice.dll）与 112.132.225.216:10009。
R：RX=0 = "客户端从未拨入我们通告的端点"，而不是"端点坏了"。

**B-21 "靶场路径"到底是什么意思**（KEPT 能力 / UNREACHABLE）
服务端支持已验证：build_mission_session_object(firing_range=True) 发 67B 地址块、map=mp_firingrange、GameType=0x1000007、MaxPlayers=1；battle_server 服务 firingrange-gamestate.bin（0x20 0x71 = 127.0.0.1:28960 小端）。
但客户端从未请求过它（B-12），唯一服务它的那轮什么也证明不了（B-13）。**靶场是我们能服务的代码路径，不是客户端会走的路由。**

### 4.6 参考研究 / 资源 / 资产 / 工具（S5 考古）

**REF-01 IW4X 复用评估**（参考/架构研究，KEPT）
CODOL 与 IW4X 同属 IW4 血统但**不 ABI/协议兼容**；隔离探针 exit 0xC0000135（缺 iw4x.dll）；G: 的 MW2 iw4mp.exe 是 x64 不同代。
R：IW4X 只能作"服务器工程结构参考"；地址/命令/auth **不可照搬**。
E：CODOLServer\IW4X_CODOL_REUSE_REPORT.md。I：**"当前 Server 基于 IW4X"被项目自己 REFUTED**（STAGE_REPORT_BATTLE.md:180-184：IW4X 直接引用 = 0）。

**REF-02 F: 盘第三方参考实现依赖**（外部依赖，KEPT）
F: 盘的 C# 参考（CodolLocalLobbyServer.cs 58.8KB、CodolLocalBattleServer.cs 28.9KB、CodolBattleKeyExchange.cs、CodolMotionSnapshot.cs 等）+ 大厅 python 套件；本地副本 _ref\CodolLocalLobbyServer.cs（10-01 23:06）与 _ref\lsg.log（10-02 22:58）。
I：anchor 之后的实现**依赖 F: 的 C# 参考**，不依赖 IW4X 代码。

**REF-03 ol-mod 解锁检查 → BLOCKED**（ABANDONED）
E:\handoff2\ol-mod-olfinal.zip 不存在；E:\handoff2\ 不存在；全机 depth-6 搜 Servers.cpp / DedicatedControl.* / sharedRoomClient.* / bookingDispatcher.* / ol-mod*.zip → 0 命中。
R：BOOKING_SOURCE = BLOCKED；BOOKING_PROTOCOL = UNKNOWN；BATTLE_ENTRY = NOT_OBSERVED。
⚠ 注意与 DEV-BOOKING 的关系：DEV-BOOKING 的 booking 实验**仍在继续**，该"停止"只作用于 battle stage-report 那条支线。

**ASSET-01 .ff 层一解密（前置依赖，被复用最多）**（KEPT）
布局 = XFileHeader(21B, magic IWff0100, version 461) + 256B RSA 块 + AES-CTR 体；RSA 私钥（1191B DER）与 IW4X FastFiles::ZoneKey **逐字节相同**；AES-192 key da135e91c7981459a13ddc2aed3050ae6dd9a7ce619bb6c5 全仓唯一；CTR 为整块小端递增。
R：10/10 main\*.ff 解出；层二对 zlib/deflate/gzip/lzma/bz2/LZ4/ECB/CBC/CFB/OFB/CTR 变体全部 REFUTED。

**ASSET-02 .ff 层二静态攻坚（anchor 后，REFUTED）**（REFUTED）
所有假设（周期 ~0x1000 的重复 XOR、zone 名派生 AES key）全否；熵 8.000；周期扫描 P=256..8192 最小 Δ −0.009；zone-name KDF 0 命中。
⚠ **方法论陷阱已记档**：首个探针的 dist=0x1000 → 熵 7.41 是**小样本偏差**（4KB 随机期望约 7.7）；64KB → 7.999、1MB → 7.9998。
R：静态路线关闭 → 转运行期内存路线。

**ASSET-03 全量 common_marketplace 明文 nifs 提取（anchor 后）**（KEPT）
o 主目录里一直有完整版 common_marketplace：**37 个包 / 9.4 GB**，是 nifs 明文容器（不是加密 ff），头 0x200 之后就是 main/images\xxx_item_icon.iwi 这类资源路径。
R：mkt_assets_summary.md —— **34911 条唯一资源路径 / 124929 条原始条目 / 18 个来源包**；分类含名片背景 1205、头像图标 441、称号 1。

**ASSET-04 IFS/FF 扫描工具（anchor 后，TOOLING）**（KEPT，含方法论更正）
12 个脚本；在 lf_init_common_marketplace_1_V49.ifs（594MB）上 main/images 4215×、iwi 4248×，但 pcb_amorphous01 / callsignNameplate / codo.objects **0×** ⇒ **.ifs = 部分明文（路径表）+ 部分加密（资产数据）**，"字符串搜不到"**不能**否证存在。I：早先"0 命中"的字符串搜索方法论不足，后被 MD5 全扫纠正。

**ASSET-05 974 个 .ifs 的 MD5 全扫（anchor 后，决定性负结果）**（KEPT）
974 包 / 1,469,394 个 zlib 候选 / **0/6 命中** ⇒ 6 张客户端市场表**不在任何 .ifs 压缩流里**；入口是客户端资源注册表 0x239B120（stride 0x1C），落在 Base.dll .tvm0（壳虚拟化节）。
⚠ 记录一个方法错误更正：0x239B120 是 **RVA** 不是文件偏移。
I：基于文件/IFS 的表恢复被放弃。

**ASSET-06 codol_crypto.py（anchor 后，TOOLING/移植）**（KEPT）
REF_LOBBY_KIT\codol_crypto.py（10-07 17:12，41.8KB）是 F: 套件 10.4KB 版本的**扩展本地派生**，不是新算法。I：加密核心来自 F: 参考。

**ASSET-07 2026-10-08 20:32:23 974 个 .ifs 被整体重写（anchor 后，原因 UNKNOWN）**（UNKNOWN，观测 KEPT）
COD OL\IIPS\IIPSDownload 下**全部 974 个 .ifs** 的 LastWriteTime = LastAccessTime = **2026-10-08 20:32:23**，而 CreationTime 保持安装时（2026-09-10 00:15:0x）；无硬链接/重解析点。
关联动态证据：沙箱 IIPS 在**同一秒**写了 run_codol_001\...\vodcache\download.db（SQLite，old_items 表 0 行），当天另有 6 个 TenioLog（18:12:05 / 20:08:29 / 20:14:31 / 20:21:36 / 20:24:41 / 20:25:28），其中 20:25:28 全是 "LoadImage LoadImageFromBuffer failed"（TPFUI PNG）。
未解假设：(a) IIPS 就地修复/全量校验重写；(b) 批量恢复到真实安装；(c) 仅触碰时间戳。CT 保留支持 (a) 但不证明。
规模：974 个内容包 ≈ **23.8 GB**（其中 695 个内嵌 IWff）在一秒内被重写。
⚠ **这是本报告扫描到的、anchor 之后未被任何文档记录的最后事件**，必须交给接力者。

**ASSET-08 _cleanout 层一产物（anchor 后）**（KEPT）
4 个 layer1.bin（common_marketplace_lite 28.9MB、lite1 3.36MB、localized_lite 64.8KB、ff_init_common_marketplace_V95.ifs 32.3MB）；这三个 marketplace zone 正好是 pre-anchor mount 审计里缺失的三个。

**RE-01 _lb015 内存转储逆向（anchor 后）**（UNKNOWN）
45 个一次性脚本（10-08 15:36–16:10），源为 REF_LOBBY_KIT\mem_linear_20261007_134406；b10.py 反汇编 0x7CAF30（listener E69CB0 +0x24）；c2.py 扫 PE 的 IAT 槽并与 dump 对齐。**无报告、无输出留存。**

**RE-02 _s1.py A/B 写入点扫描（anchor 后）**（UNKNOWN）
root _s1.py（10-08 14:46）扫 image_best.bin 中 0x620000–0x63A000 对 [reg+0x168]/[reg+0x16c] 的写入。**只有脚本，无输出。**

**RUN-01 run_codol_001 沙箱活动（anchor 后，DYNAMIC）**（KEPT，原始证据）
19 个 anchor 后文件：probe_dump.xml（3.1MB ETW，10-07 20:00）、BugTrace.log（503.5KB，10-08 18:02，ACE 仍在写）、cacert.pem（20:21）、ACE-DRV32.dll（6.7MB，20:25）、tcj.dll.bh（4.2MB，20:25）、players\config_mp.cfg（7.7KB，20:26，客户端写了配置）、_co.tlg（20:30）、TenproxyLog\20261008_180217.log（0B）、IIPSClient.ini（18:11）、TenioLog×6、download.db（20:32）、Progress.ini（0B，20:32）。
O：沙箱一直跑到 10-08 20:32；IIPS 反复加载不了自己的 TPFUI 图片；ACE BugTrace 仍在写。

**FAIL-01 自编 SKU 页把 marketplace 打挂（anchor 后，ROLLED_BACK/REFUTED）**
HANDOFF_20261005_LOBBY_BUGS.md §8 记录 2026-10-05 22:10 的事故；REF_LOBBY_KIT\_rollback_state.py 与 _revert_to_trusted_catalog.py 回滚到可信目录。

**TOOL-01/02/03 工具与基础设施**
TOOL-01 CODOLServer\_mainline（802 文件，最新 10-05 15:36）**anchor 后未被修改，但是 anchor 之后唯一的动态通道**（HANDOFF_20261005_LOBBY_REACHED §3 的复现命令依赖 agent_client.py；LOBBY_BUGS §3.3 依赖 agent_client.py + nt10.py）。
TOOL-02 DEV-PUBLISHER-RESTORE 镜像（10-08 09:22 建立，13,691 个文件）—— 按 GOLDEN-LOBBY-001.md:205-208"实验必须在 DEV 副本做"。
TOOL-03 observer/实验目录清单（多为 pre-anchor，anchor 后 0 活动）：_dyn_stage1(277)、_pml_analyze(27)、_ebo1_observer(19)、_ich015…_ich048_observer、_ord1_observer 等；根目录 617 个 .py 中只有 _mkt_layer2_probe.py、_mkt_period_probe.py、_s1.py 是 anchor 之后的。

### 4.7 房间 / 会话 / 匹配（Room / Session / Matchmaking）

```
在 anchor 之后这个领域**没有独立的新工作流**，它分散在三处：
1) T10 的靶场开关组（10-05 16:55:12，新建 firingrange-session.enabled 与 firingrange-battle.enabled）；
2) 21/5 / 11/4 / 11/13 handler 本体是 **ol-mod 移植**，代码注释日期为 2026-10-03/10-04（pre-anchor）：
   lobby_server.py:19（21/5、21/16 findSessions 会话对象 258B）、:587（靶场模式 2026-10-03）、
   :784（2026-10-03 实测）、:806（2026-10-04 重做）、:832+（11/5、11/10）、:458-486（SESSION_ID/ROOM_ID）；
3) 10-07 之后的路线选择工作：B-10 的 coop_map 自纠环、B-12 的"无独立靶场入口"、
   B-13 的强制靶场 session、T57/T59 的 PvE session（PVE_PLAYLIST_IDS 回填 playlist）。
```

状态（只列有证据的）：

```
11/13 createRoom        OK（LOBBY_MAP §1.3）
11/4  setRoomData       空应答（靶场用）（LOBBY_MAP §1.3）
21/5  findSessions      OK；单条 PvE/靶场 session 对象；长度口径冲突见 §17
21/1  21/13 21/16       已实现（lobby_server.py:19 注释）
playlist 路由           is_pve = playlist in PVE_PLAYSTL_IDS（10-07 加入；此前一律回靶场对象）见 SC5
mmbook 6/14             见 §4.4（accepted 分支不可达）
```

⚠ 本领域**没有** 10-05/10-06 的服务端日志（T37 归档后，唯一存活日志从 10-07 开始），
所以那段时期的房间/会话行为只能靠文档叙述，属 **UNKNOWN**。

---

## §5 结局面分类（成功 / 部分成功 / 失败 / 回滚 / 被证伪 / 仅静态 / 未知）

### 5.1 SUCCESSFUL WORK（真正保留下来的成果）
```
S-1  采用第三方 kit 并打通大厅（T01/T03）—— 自研栈 4 条任务 → kit 34 条 → 修两个真问题后 47 条 + 大厅 UI 渲染
S-2  0x83 使用本会话 KDF challenge（等 5s 配对 kdf_sessions.txt）（T03）
S-3  10/21 发行方文件名同义名回退 + 实体别名文件（T03）
S-4  购买解析由 58B 硬模板改为 TLV 类型标签解析（T22）—— 实测扣款 883599→819999
S-5  目录重建与合并：37615 → 37793 → 37834；currency-lenient 解决"货币字段不一致"（T18/T26/T28/MK-10/MK-16）
S-6  mp_playlists 重建到 version 796（262→658→716B，zlib 文本，6 模式）（T31）
S-7  8/3 玩家档案上传逐字节复刻（CRC32/zlib/tag 08-19-07），重建 public.result 33428 B 一致（PR-01）
S-8  库存削减 + Priority 机制，绕开 480KB 应答上限（MK-06）
S-9  SKU 表 ground-truth 逆向：sku_table_v2.csv 635 条高置信（MK-15）
S-10 发行方文件恢复（DEV 副本含数据目录）→ fatal 消失、6/14 真正发出（T49/T50/PB-02/PB-03）
S-11 战斗服 NAT/DTLS/ECDH P-224/数据帧协议层（B-00）
S-12 战斗服 connect_done + snapshot_due 修复（不等客户端即下发首帧 game state）（B-04）
S-13 快照字段序列对齐 29/29（124B→141B）（B-06）
S-14 battle_selftest.py 13/13 离线回归（本线最可靠资产，脱离游戏可复现）（B-07）
S-15 大厅 keyset 纪律修复：不再猜密钥，帧留 pending；88 hmac=OK / 0 BAD（B-09）
S-16 Booking 静态链闭合到 0x632680（契约/通道/分派/参数/状态）（T45/T51-T53）
S-17 listener 7/7 与 type-2 两条轴彻底关闭（T61-T63）
S-18 017 只读采样能力（nt10 _accprobe）与 accepted 唯一判据的建立（T64）
S-19 018 字段身份闭合 + 019 单变量实验（A/B 对齐成立，且客户端回显 #7 做行为级确认）（T65/T66）
S-20 一整套只读逆向工具链（_015_* / _016_* / _017_* / _018_* / _019_* / _020_* / snapshot_diff / battle_selftest）
S-21 Golden 哈希体系与 DEV 副本纪律（T43/T50）
S-22 mkt_assets 明文 nifs 资产清单：34911 唯一路径 / 124929 条目（ASSET-03）
```

### 5.2 PARTIAL SUCCESS（只解决一部分）
```
P-1  大厅 UI 内容：playlists 版本问题解决，但模式/地图名仍不对 → 列表仍空（T31）
P-2  商城：能买/不能买规则弄清了，但 80/70 页始终空 → 商城空白 + 军火箱页面重叠未除（K-02）
P-3  名片/称号："买到但看不到"未解决，阻塞被推到客户端侧（T20/MK-02）
P-4  PvE 地图匹配：改成 coop_map 自纠环，但只能滞后一轮收敛（B-10）
P-5  大厅协议：0x81/0x82/0x83/0x85/KDF/keepalive/seq 都成立，但推送序号（marker 0x02、跳号）一直不稳（T41/B-11）
P-6  战斗服：协议层与离线回归完整可用，但真实客户端自 10-06 21:28 之后再未拨入（B-03/B-20）
P-7  Booking：静态链完整、A/B 对齐成立，但 accepted 分支仍不可达（T66）
P-8  发行方：DEV 副本解决，但 Golden 冻结副本仍缺数据目录（T49/PB-02）
```

### 5.3 FAILED WORK（尝试失败，未回滚也无效）
```
F-1  ready_push + mirror_predicted 轮：弹窗照旧、0B/4 频道从未出现（T02）
F-2  BOOKING_RUNTIME_TRACE-001：想断点观测 0x632680 → INSTRUMENTATION_BLOCKED（T46）
F-3  BOOKING_RUNTIME_NETWORK-002：6/14 NOT_SENT，阻塞在发行方文件（T47）
F-4  DYNAMIC-VALIDATION-011：UAC 未批 → ENVIRONMENT_BLOCKER（T58）
F-5  013 的 A/B MATCH 推断：被 017/018 证伪（T60）
F-6  强制靶场 session（三开关全开）：仍 RX=0（B-13）
F-7  "用靶场信封回答 PvE booking"：9/9 断连，冻结为 .OFF_CONFIRMED_CRASH（B-11）
F-8  ol-mod 源码获取：全盘 0 命中 → BOOKING_SOURCE = BLOCKED（REF-03）
F-9  .ff 层二静态解密：所有假设被否（ASSET-02）
F-10 从 .ifs/文件系统找 6 张 coMarketplace 表：0/6（MK-07/ASSET-05）
F-11 MOTD/挑战/活动占位文件重写：审了、计划了、**没做**（MO-01）
```

### 5.4 ROLLED BACK WORK（最终回滚）
```
R-1  public.result 尾部 125x0x07 注入（.rejected_20261006）（T27/MK-09）
R-2  SKU sentinel 探针（marketplace-skus*.on.rolled_back_20261006）（T33/MK-11）
R-3  itemgroup SKU 页（count=1 实机）→ 商城+HUD 锁定 → 15:07 回滚（MK-17）
R-4  "自编 SKU 页"（pre-anchor 事故，rollback 标记在 anchor 后）（MK-00/FAIL-01）
R-5  replyId 独立计数器（B-11 假设一）
R-6  低 Item 条目合并（MK-14）→ 后在 MK-16 以"仅补不覆盖"方式部分重做（SC-01）
R-7  019 的 codol_crypto.py #7 = SessionId 单变量修改（T66）—— SHA-256 校验恢复
```

### 5.5 REFUTED HYPOTHESES（被证据推翻）
```
RF-1  重连 hmac=BAD 是握手密钥竞态（T07 自我更正：BAD 是结果）
RF-2  0x632680 的 accepted handler = vtable +0x140 / base 0xDC7270（T52 更正为 +0x13C / 0xDC7274）
RF-3  0x632A00 是 timeout handler（T52）
RF-4  0x6334xx→0x818de0 是 booking→battle worker（T55：它是 chat.private 私聊状态机）
RF-5  accepted → listener → battle（T62：7/7）
RF-6  type-2 network object 是 Battle 桥梁（T63：它是 Demonware lobby TCP 连接）
RF-7  matching+0x3A048 来自 SessionId 低 32 位（T65：来自 21/5 会话对象 #7 u64）
RF-8  0x0849B61C == 1 可作 accepted 判据（T64：有 5+7 个写入者）
RF-9  A/B 对齐即可解除 accepted 守卫（T66：必要非充分）
RF-10 28960 是客户端硬编码常量（T53）
RF-11 6/14 响应走 UDP/HTTP/独立 socket（T51：走大厅 TCP 的 0x85 帧）
RF-12 Battle 是 TCP（T56）
RF-13 0x818de0 是 booking dispatcher / 0x803830 是 socket/connect / 0xB81EF0 是 battle connect（T55/T56）
RF-14 "存在独立靶场入口"（B-12）
RF-15 "靶场 session 足够"（B-13）
RF-16 "推送抢了客户端序号"→ +1000 偏移可修（B-11 假设二）
RF-17 "推送总会断连"（SC4：10-07 10:34 未立即断连）
RF-18 "480KB 截断是所有购买无效的原因"（MK-02：4 件最小仓库实验否证）
RF-19 "两套 SKU 编号不兼容是购买失败原因"（MAIN §5 已否）
RF-20 "表在 .ifs 包里"（MK-07/ASSET-05）
RF-21 "放明文 mp/marketplace.json 可行"（09-29 实测 NEGATIVE）
RF-22 "内存记录 +0x18/+0x1C 是 Category"（MAIN §5）
RF-23 "那 499KB 抓包是称号表"（MAIN §5：是本地化字幕）
RF-24 "demo-player-fields-trace 是快照基线"（B-06 假设一）
RF-25 "67B 地址块 / 地图不匹配是战斗入口的根因"（S4 否证）
RF-26 _015_glob.py 报出的 or eax,<全局> 结果（016 §1.1：1 字节回溯假阳性）
RF-27 "当前 Server 基于 IW4X"（REF-01/STAGE_REPORT：IW4X 直接引用 = 0）
RF-28 ".ifs 里字符串搜不到 = 不存在"（ASSET-04：.ifs 是部分明文，字符串法无效）
RF-29 .ff 层二周期 0x1000 的弱密钥（ASSET-02：7.41 是小样本偏差）
```

### 5.6 STATIC ONLY（只完成分析，未实施）
```
ST-1 DEV-BOOKING 001-018 全系列静态报告（011/012/017/019 四次是动态）
ST-2 BOOKING_PROTOCOL_SPEC-001..004 / BOOKING_STATE-001 / evidence-002
ST-3 CLIENT-BOOKING-BATTLE-TRIGGER-014 / LISTENER-BRIDGE-015 / BATTLE-OBJECT-016
ST-4 PUBLISHER_FAILURE_SPEC-001（诊断做完，未动手）
ST-5 MK-01 / MK-07（目录布局与宿主搜索，结论是"静态路走不通"）
ST-6 ASSET-02 / ASSET-04 / ASSET-05（.ff 层二与 .ifs 扫描）
ST-7 REF-01（IW4X 评估）
```

### 5.7 UNKNOWN（证据不足）
见 §12 CURRENT UNKNOWN。

---

## §6 数据 / Server 修改追踪（每一次改动：前 / 内容 / 后 / 客户端表现 / 是否保留）

| # | 时间 | 对象 | 修改前 | 修改内容 | 修改后 | 客户端表现 | 保留 |
|---|---|---|---|---|---|---|---|
| M-01 | 10-05 16:30 | lobby_server.py 0x82 分支 | 退回 secrets.txt 上一会话 challenge | 用票据 24B 密钥配对 kdf_sessions.txt，最多等 5s | challenge 来源 = kdf-session | 首帧逐字段一致，任务 34→47，**进大厅** | **KEPT** |
| M-02 | 10-05 16:30 | publisher_files/ | 无 1.0.0.info | 加同义名回退 + 放实体别名文件 | 10/21 可服务 | 过 EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE | **KEPT** |
| M-03 | 10-05 16:55:12 | 开关组 | booking-push 开；session/battle 无 | 建 firingrange-session.enabled、firingrange-battle.enabled；booking-push 改名 .OFF_CONFIRMED_CRASH | 3 个新/改开关 | 靶场/战斗可服务；booking 推送关闭 | **KEPT** |
| M-04 | 10-05 17:16 | marketplace-inventory.json | 7 件 | 全物品发放 | 17372 件 | 商城有内容；后成 480KB 截断诱因 | 后改（见 M-05） |
| M-05 | 10-05 21:29 起 | marketplace-inventory.json | 17372 | 削减 + Priority 播种 | 7600 → 7614 → 7619 → **7620**（Priority 37） | 80/203 应答 460KB 不再截断 | **KEPT** |
| M-06 | 10-05/10-06 | lobby_server.py 购买分支 | 58B 硬模板逐字节比对 | TLV 类型标签解析 | sku/qty 正确解出 | **购买成功 sku=32223，GP 883599→819999** | **KEPT** |
| M-07 | 10-06 13:23 | 目录开关 | — | marketplace-catalog-client.on | client 目录 = exe 37615 | 目录可解析 | KEPT |
| M-08 | 10-06 15:24 | marketplace-catalog-client.json | 37716（含 101 条内存推断） | 回滚为纯 exe 副本 | 37615（旧状态存 .bak_inferred=37716） | 恢复可信目录 | KEPT |
| M-09 | 10-06 15:27 | lobby_server.py 购买应答 | 余额对象 | 空对象 + status=0（对齐 C# 参考） | 应答形状改变 | **客户端行为不变** → 应答形状不是根因 | KEPT |
| M-10 | 10-06 19:33 | marketplace-catalog-merged.json | — | exe + full(Item≥1000) + 白名单 31774 | 37793 | 服务端购买验证通过 | KEPT |
| M-11 | 10-06 21:29:38 | player_profiles/public.result + lobby_server.py | — | 尾部 125x0x07 注入 + 开关 | public-tail-inject.on.rejected_20261006 | **无变化** | **ROLLED BACK** |
| M-12 | 10-06 21:33 | 货币宽松开关 | — | marketplace-currency-lenient.on | 按客户端请求货币计费 | 39038/39601/40284/41526/45137 OK | **KEPT** |
| M-13 | 10-06 21:50–22:48 | mp_playlists_shipRetail_*.info（2 文件 4 轮备份） | 262B 高熵占位 | 重建为 zlib 文本 version 796 | 716B（含 war/dm/dom/hp/tag/sr） | 版本崩溃消失；列表仍空（名字不对） | **KEPT** |
| M-14 | 10-06 22:22–22:28 | 80/70 SKU 页 + 开关 | 空页（安全） | 发 sentinel SKU 页 | marketplace-skus*.on.rolled_back_20261006 | **商城/仓库变灰、角色被锁** | **ROLLED BACK** |
| M-15 | 10-06 22:59 | run_all.py | — | 启动器修复 | 体积不变 31507B | — | KEPT |
| M-16 | 10-07 14:44:28 | firingrange-gamestate.bin | 缺失 | 从 F: 复制 259B | 启动日志 (缺)→(259 字节) | 使 TX_GAMESTATE 成为可能 | **KEPT** |
| M-17 | 10-07 15:00 前后 | battle_server.py | game state 门控在 ready；快照门控在 OOB gamestateupdate | connect 即置 connect_done + gamestate_due；快照随 game state 启动 | 3 处编辑 | **10-07 15:01:00 首次 TX_GAMESTATE** | **KEPT** |
| M-18 | 10-07 下午 | battle_server.py 快照字段 | idx21..24 旧序、无 idx84、含 idx219 | 改写 idx21..24；补 w.index(84)；默认去 idx219 | 124B→141B | 29/29 对齐 | **KEPT** |
| M-19 | 10-07 15:26–15:39 | lobby_server.py keyset 分支 | pick_keyset 未命中时猜密钥 | 不猜，帧留 pending 等正确密钥 | 88 hmac=OK / 0 BAD | 大厅稳定，战斗 E2E 前提就绪 | **KEPT** |
| M-20 | 10-07 18:06–18:08 | lobby_server.py 推送段 + push_seq_offset.txt | 推送复用请求 seq（冲突） | 独立出站序号 + 推送偏移 1000 | push_seq_offset.txt=6B | **仍 9/9 断连** → 偏移法被否 | 机制 KEPT / 效果 REFUTED |
| M-21 | 10-07 19:01 | GOLDEN-LOBBY-001（22 文件 + _golden_hashes.json） | — | 冻结只读基线 | 见 §6.2 审计 | — | **KEPT** |
| M-22 | 10-06 15:19/15:24 | _rollback_state.py / _revert_to_trusted_catalog.py | — | 回滚工具 | 目录回到可信状态 | — | KEPT（工具） |
| M-23 | 10-07 15:43:11 | marketplace-inventory.json / player-account.json / player_profiles/secure.result | 旧值 | **写入者不明** | 7620 件 / CP972299 GP523619 / 32983B | 与 Golden §1.2 完全一致 | **UNKNOWN（写入者）** |
| M-24 | 10-08 09:22 | DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT（新目录） | Golden 缺 publisher_files/player_profiles/user_files | 从 REF_LOBBY_KIT 复制（含数据目录 + 9 个运行必需 .py） | fatal 消失 | **09:23:45 首次真正 6/14** | **KEPT** |
| M-25 | 10-08 14:49 | lobby_server.py 6/14 分支 | instant_push_body(1,…) | instant_push_body(SESSION_ID,…)（备份 .bak_010_20261008_145002） | 信封 senderId = 0x1122334455667788 | 见 §6.3：这正是 019 认定"破坏 A/B 相等"的改动 | **KEPT** |
| M-26 | 10-08 17:57–18:21 | nt10.py（**Golden 范围外文件**） | 无采样 | 加只读线程 _accprobe（+accepted-state-probe.on） | +5,715 B | 建立 accepted 唯一判据 | **KEPT（属 Golden 后改动）** |
| M-27 | 10-08 20:07–20:26 | codol_crypto.py L542 | ob.u64(1) # 7 | ob.u64(0x1122334455667788) # 7 | A/B 由 (1,0) 变 (0x55667788,0x11223344) | accepted 分支仍未执行 | **ROLLED BACK（SHA-256 已校验）** |
| M-28 | 10-08 20:32:23 | COD OL\IIPS\IIPSDownload 下全部 974 个 .ifs | 原始安装文件 | **整体重写（1 秒内，CT 保留）** | LWT=AT=20:32:23 | 无任何文档记录 | **UNKNOWN（机制）** |

### 6.1 目录 / 数据库数值谱系
```
marketplace-catalog.json          37615（exe 反射，服务端基准）
marketplace-catalog-client.json   37615 →（37716 .bak_inferred）→ 37615
marketplace-catalog-full.json     38424（内存采集版，未启用）
marketplace-catalog-merged.json   37793 → **37834**（bak_trusted_37793_20261007）
inventory                         7 → 17372（.bak_big/.bak_full）→ 7600 → 7614 → 7619 → **7620**
sku_table_v2.csv                  635 条高置信（5/5 ground truth）
item_sku_arrays.csv               1609 行 / 572 items / 394 多档（曾被误覆盖为 128 items，已恢复 + 加写保护）
unknown_skus.txt                  155 行（REF 10-07 11:01）→ 158 行（DEV 10-08 09:35，+sku 22632 x3）
public.result 33428 B；secure.result 32983 B；CP 972299 / GP 523619 / Lv70 / Prestige4
playlists                         1.0.0.info version 796（7 playlists）；playlist 集合 [1..6,10]
```

### 6.2 GOLDEN 冻结漂移审计（本报告新增）
拿 REF_LOBBY_KIT\_golden_hashes.json（10-07 冻结）与**当前实际文件**逐个比对：

```
run_all.py             MATCH     （2aaa8847f112d926…）
codol_crypto.py        MATCH     （e836c63af75dd82e…，019 已恢复）
battle_server.py       MATCH     （71bb7beb85e51408…）
marketplace_store.py   MATCH     （28b4a1be67de06f4…）
**lobby_server.py**    **DIVERGED**（Golden 76,410 B → 现 76,428 B；diff 恰 2 行：推送信封 senderId 1 → SESSION_ID，即 M-25）
**nt10.py**            **DIVERGED**（Golden 169,491 B → 现 175,206 B；含 017 的只读采样等 Golden 后新增段）
```

⇒ 结论：**Golden 冻结已被两次真实漂移打破**（lobby_server.py 由 10-08 booking 工作改动；nt10.py 由 10-08 只读采样改动）。
其余核心文件仍在冻结状态。任何以"未改 Golden"为前提的陈述，必须限定为这两个文件之外。

### 6.3 一个重新解读：M-25 是 A/B 失配的起点
```
Golden 冻结时（10-07）的信封 senderId = **1**；而 21/5 会话对象 #7 u64 也是 **1**（codol_crypto L542）。
⇒ **在 Golden 时期，A/B 本来就是相等的（1 == 1）**，只是那时 booking 推送被冻结禁用（.OFF_CONFIRMED_CRASH），
   所以从未被测过。
10-08 14:49 的 M-25 把信封 senderId 改成 SESSION_ID（0x1122334455667788），
   A/B 立刻变成 (0x55667788, 0x11223344) 而客户端侧仍是 (1,0) → **第一守卫从此必然失败**。
019 的做法是反过来把**会话对象 #7** 抬到 SESSION_ID 以重新对齐（对齐成功）。
⇒ 路径选择上，**回退 M-25（senderId 回到 1）本应与 019 等效且改动更小**；
   但 019 的结论（对齐后 accepted 仍不执行、客户端反应逐条同型）说明**真正的门在更上游（通道/marker）**，
   这与 Golden 时期"推送一开就 9/9 断连"的历史一致。
```

---

## §7 ROLLBACK REGISTER

| # | 实验 | 修改 | 原因 | 副作用 | 回滚方式 | 当前是否恢复原状 |
|---|---|---|---|---|---|---|
| RB-1 | 自编 SKU 页（MK-00/FAIL-01） | 80/70 发手写 SKU | 商城整片死亡：库存/商城变灰 + **角色被锁** | 该会话不可恢复，需重启 | 代码硬门控回空页；marketplace-skus*.on.rolled_back_20261006 | **是**（空页为安全态） |
| RB-2 | public.result 尾部注入（T27） | 125x0x07 填入 8 个 itemID | 客户端毫无变化 → 假设被否 | 无 | 开关改名 public-tail-inject.on.rejected_20261006；备份 public.result.bak_before_tail_20261006_212954 | **是** |
| RB-3 | sentinel SKU 探针（T33/MK-11） | 发含 sentinel 的 80/70 页 | 商城/仓库变灰 + **角色被锁**；"内存有 sentinel ≠ 被解析" | 同上 | marketplace-skus.on.rolled_back_20261006 + marketplace-skus-allow-unsafe.on.rolled_back_20261006（22:28:24） | **是** |
| RB-4 | replyId 独立计数器（B-11 假设一） | 应答 replyId 不再回显请求 seq | 客户端仍然崩（且与出站序号错位） | 断连 | 代码回退到"回显请求 seq" | **是** |
| RB-5 | 推送序号 +1000 偏移（B-11 假设二/T41） | 推送 seq = 请求 seq + 1000 | **9/9 断连**（未解决）；偏移法被否 | 断连 | 开关整体关闭（.OFF_CONFIRMED_CRASH） | 机制**保留**，效果**被否** |
| RB-6 | itemgroup SKU 页（MK-17） | count=1 的 item→SKU[] 页 | 客户端**不再发 80/203** → 商城+HUD 锁定 | 锁定 | 15:07 运行 enable_itemgroup_sku_test.py off，两个 flag 删除（现确认为 absent） | **是** |
| RB-7 | 低 Item 条目合并（MK-14） | 把 client Item 12/13/28/49… 合入目录 | 判为"假成功、入错物品" | — | 重生成 37793 | 部分 —— **SC-01**：MK-16 后来对"目录中不存在"的 SKU 又做了同类合并（当前 37834 里确实含那 9 个低 Item SKU） |
| RB-8 | sku_table 覆盖事故（MK-18） | 在"未打开商城"的 dump 上跑覆盖写 | 表被写成 128 items，5 个 ground truth 全丢 | 数据损坏 | 用旧 dump 重跑恢复（572 items / 1609 行）+ 加 ground-truth 写保护（exit 2） | **是** |
| RB-9 | 019 A/B 对齐（T66） | codol_crypto.py #7 = SessionId | 对齐成功但 accepted 仍不执行 → 必要非充分 | 无（服务端单变量） | 备份 codol_crypto.py.bak_019_20261008_200724；SHA-256 恢复为 E836C63A…44607 | **是（已逐一校验）** |
| RB-10 | 目录覆盖实验（多次） | client/merged/full 目录切换 | 目录体系混用会导致"买到错东西" | — | .bak_inferred / .bak_trusted_37793_20261007 | 部分（当前 37834 为最终态） |
| RB-11 | 商城协议实验整体（Golden 纪律） | — | GOLDEN-LOBBY-001 第 4 条：marketplace 协议实验冻结 | — | 10-07 19:01 起冻结 | **是**（10-08 未再做商城协议实验） |

**回滚遗留（必须提醒接力者）**：
```
· RB-7 的残留：当前 marketplace-catalog-merged.json(37834) 内含 9 个"客户端低 Item"SKU，
  与 TAKEOVER §13.2 的禁令直接冲突（SOURCE_CONFLICT SC-01）→ 若再次触发"买到错东西"，优先查这里。
· M-23（10-07 15:43 不明写入者改了 inventory/account/secure.result）**没有回滚，也无写入者线索**。
· M-28（10-08 20:32 全部 974 个 .ifs 被重写）**没有回滚，也无机制线索**。
```

---

## §8 MAJOR BREAKTHROUGHS（重大突破）

```
BR-1  **2026-10-05 16:36 进入正式大厅 UI**（anchor）—— 两个真实修复：0x83 的 KDF challenge 来源 +
      10/21 发行方文件名同义名。任务 34→47，窗口类 CODO，标题"使命召唤online"。
BR-2  **发现 71/7 是客户端自报崩溃通道**（UIException）—— 把"大厅到处是 BUG"转成
      "4 条崩溃链 / 4 个缺失数据源"，此后所有 UI 修复都有据可依。
BR-3  **购买解析 TLV 化** —— 一次改动解决"背包/副武器/近战点购买没反应"，实测真实扣款。
BR-4  **命中"能不能买 = SKU 在不在服务端目录"这一唯一规则** —— 终结了按类别/货币猜测的所有弯路。
BR-5  **发行方文件恢复**（DEV 副本含数据目录）—— fatal 消失，**09:23:45 首次真正发出 6/14 mmbook**，
      解锁了此后全部动态实验。
BR-6  **6/14 响应通道 = 大厅 TCP 本身**（无独立 booking socket）—— 终结"找独立 booking 端口"这条轴。
BR-7  **Booking 分派链闭合**：service=21 即时消息 → 0x7F1544 strncmp → matching 单例 → vtable+0x13C=0x632680
      （统一 mmbook handler，内部按 "mmbook accepted" 分流）。
BR-8  **accepted 分支唯一判据的建立**：全镜像 mov byte [reg+disp],imm8 扫描 2462 条，
      disp=0x288 且 imm=1 **只有 0x63280B 一处** → 把"accepted 是否执行"变成可判定的问题。
BR-9  **LISTENER→BATTLE = 7/7 全部证伪** —— 一次性砍掉整条 listener 轴（5 个空实现 + wargod + UI/CEF）。
BR-10 **type-2 network object = Demonware lobby TCP 连接**（socket(2,1,6) + connect + "DW_LOBBY_CONNECTED"）
      —— 砍掉 type-2 轴，并顺带否定"battle 走 TCP"。
BR-11 **A/B 字段身份闭合**（018）：matching+0x3A048/+0x3A04C ← 会话对象记录 +0x168/+0x16C ←
      21/5 会话对象 **tag 0x0A u64 字段 #7** 的低/高 32 位。并明确指出 013 的"= SessionId 低 32 位"是错的。
BR-12 **019 单变量实验**：A/B 对齐**成立**（72 采样点），且客户端把 #7 **回显**进自己的 mmbook 请求
      （行为级确认字段身份）；同时证明对齐**必要非充分** → 把门定位到通道/marker 层。
BR-13 **battle_selftest.py 13/13 离线回归** —— 战斗服第一次可以脱离游戏自证；这是战斗线最可靠的资产。
BR-14 **战斗服 connect_done/snapshot_due 修复** —— 让服务端不等客户端就下发首帧 game state 与快照。
BR-15 **销售目录可达 37834 + currency-lenient** —— 把 25 个点不到的 SKU 找回 14 个。
BR-16 **SKU 表 ground-truth 逆向**（sku_table_v2.csv，635 条，5/5 ground truth，107/107 与旧提取器一致）。
BR-17 **mkt_assets 明文 nifs 资产清单**（34911 唯一路径 / 124929 条目 / 18 包）。
BR-18 **Golden 哈希体系 + DEV 副本纪律** —— 让"未改 Golden"成为可验证命题（并因此暴露出两次真实漂移）。
```

---

## §9 MAJOR FAILURES（重大失败）

```
FL-1  **自编 SKU 页把整个 marketplace 打挂（2026-10-05 22:10；pre-anchor 事故，anchor 后回滚）**
      —— 商城/库存变灰 + **角色被锁**，该会话不可恢复。此后 80/70 被硬门控为空页。
FL-2  **sentinel SKU 探针（2026-10-06 22:22）** —— 同一失效模式重演一次（角色被锁），
      结论"标签对但 SKUObj 字段顺序不对"，静态链止步于壳虚拟化的 tp_runtime.bin 之外。
FL-3  **itemgroup SKU 页（2026-10-07 14:41）** —— 一度被判 PASS（UIException 消失），
      随后更正：客户端**不再发 80/203** → 商城+HUD 锁定。判据被重写（check_run.py）。
FL-4  **"用靶场信封回答 PvE booking"9/9 断连** → 冻结为 .OFF_CONFIRMED_CRASH；而关掉后客户端每 5 秒轮询
      "服务器繁忙" —— 推送既是毒药又像是唯一进度信号，形成死结。
FL-5  **强制靶场 session 仍 RX=0** —— 第三方已验证的路径对本客户端版本无效。
FL-6  **BATTLE_TRIGGER_PATH 始终未找到** —— accepted → battle UDP 的触发点在客户端不可达；
      战斗服从 10-06 21:28 之后再也没有真实客户端接入。
FL-7  **ol-mod 源码全盘不存在** → BOOKING_SOURCE = BLOCKED，PvE booking 的真实 wire 格式永远缺失。
FL-8  **Frida/断点路线被 ACE 与 Golden 纪律双重封死** → 只能"只读采样"，观测能力天花板明确。
FL-9  **.ff 层二静态解密彻底失败**（所有假设被否），以及 **.ifs/文件系统找不到 6 张 coMarketplace 表**（0/6）
      —— 客户端目录体系至今只能靠运行时内存/行为反推。
FL-10 **MOTD / 挑战 / 活动占位文件始终没重写** —— #1125 / #1010 一直挂在 Golden 的 P1 缺口上。
FL-11 **两次未解的数据事故**：M-23（10-07 15:43 不明写入者改了 inventory/account/secure.result）、
      M-28（10-08 20:32 全部 974 个 .ifs 被重写）。两者都没有写入者/机制线索。
```

---

## §10 历史假设演变链

格式：初版假设 → 证据 → 实验 → 结果 → 更新假设 → 当前状态。**当时的错误判断一律保留。**

### 10.1 SessionId / A-B 身份
```
初版假设（013）：A/B = SessionId 的低/高 32 位，且与响应信封一致 → 预测 MATCH。
证据：0x6326B9/0x6326C8 校验；0x62F736/0x62F73C 与 0x62F742/0x62F748 取 A/B；0x7F1567/0x7F156B 转发；
      全程无 bswap/rol/ror/xchg；Buf.u64 与 struct.pack("<Q") 都是小端。
实验：013 纯静态，未跑游戏。
结果：判 AB_CORRELATION_PREDICTION = MATCH（HIGH-CONFIDENCE）。
→ **当时的错误判断**：以为只要 senderId 正确，守卫就会通过。
更新假设（017 实测 → 018 静态）：会话对象 #7 u64 = 1，而信封 = SessionId → **两边根本不是同一个字段**。
实验（019）：把 #7 改成 SessionId 做单变量对齐。
结果：matching A/B 变 (0x55667788,0x11223344) 与响应一致（72 采样点），
      客户端把 #7 回显进 mmbook 请求，**但 accepted 分支仍未执行（267 采样点 this288=0）**。
当前状态：**AB_ALIGNMENT = CONFIRMED；0x6326B9 = NECESSARY BUT NOT SUFFICIENT；
      NEXT_GATE = ADDITIONAL_ACCEPTED_GUARD（首选通道/marker）**。013 的 MATCH 结论被列为 REFUTED 中间假设。
```

### 10.2 accepted 响应（6/14 到底要什么）
```
初版假设：存在独立 booking socket / DedicatedControl 端口，响应走那里。
证据（003）：6/14 与 71/4、28/1、21/5、11/13、11/4 共用同一条 TCP（127.0.0.1:57548 → 127.0.0.2:3074）。
实验：NDIS 抓包 + 日志比对（无独立端口的任何证据）。
结果：BOOKING_RESPONSE_CHANNEL = **SHARED_CONNECTION_CONFIRMED**。
更新假设（004）：service=21 即时消息 → 0x7F15xx → matching 单例 vtable +0x13C = 0x632680（统一 handler）。
证据：0x7F153C push 6 / push "mmbook" / call；0x7F1554 mov ecx,[0x82e13fc]；0x7F155C mov eax,[eax+0x13c]；
      0x7F156F call eax（5 栈参数）；0x62C025 mov [ebx],0xDC7274；兄弟分支 mmrsv 走 +0x140=0x62E9F0。
结果：**修正 vtable 基 0xDC7274、+0x13C=0x632680、+0x140=0x62E9F0**；0x632A00 不是 timeout（REFUTED）。
实验（010/012）：改 senderId 1 → SESSION_ID。
结果：wire senderId = SessionId（MATCH），但仍不触发 battle。
实验（017/019）：真实推送 9 + 4 次。
结果：**ACCEPTED_WIRE = CONFIRMED（真的发出去了）**，但 **ACCEPTED_HANDLER_EXECUTED = NO**。
当前状态：响应确实走大厅 TCP 的 0x85 + type=2 push；但"以 push(marker 0x02) 形式发 accepted"
      能否被派发到 0x7F1400 尚未证实 —— 这是 019 留下的第一优先门。
```

### 10.3 marker（0x01 应答 / 0x02 推送）
```
初版假设（004 §3/§10）：marker=2 → service=21 → 0x7F15xx 派发链 HIGH-CONFIDENCE，只有上游一跳 UNKNOWN。
证据（017 §10.3 / 019 §6.2）：0x7F1400 只出现在函数指针表 0xDE080C，属**任务应答侧**；
      且客户端每次收到 marker=0x02 推送就优雅关闭并重连（9/9，以及 019 的 baseline/test 逐条同型）。
实验：019 对齐 A/B 后重放同样推送 —— 行为毫无变化。
结果：019 把"marker=0x02 推送能否到达 0x7F1400"重新列为**未证实**。
历史旁证：Golden 时期 booking-push 一开就 9/9 断连（.OFF_CONFIRMED_CRASH）；
      10-07 18:06:28 还发生过推送序号与客户端序号冲突的事故（push_seq_offset.txt）。
当前状态：**marker=0x02 通道是当前第一优先未解门**。备选：把 accepted 改成 6/14 的应答对象
      （marker 0x01，replyId = 请求 seq）。
```

### 10.4 listener（accepted 广播的接收者）
```
初版假设（014 §5）：accepted → listener 回调 → battle（listener 里应该有 battle 桥）。
证据（015）：容器 [0x82E13FC]+4 是手写双链表 {head,tail,count}；节点 12B；7 个注册点；
      广播 site 0x632824..0x632844（arg 1,0）与 0x63289E..0x6328B3（0,2），
      被 0x63281E call [esi.vt+0x5C] / 0x632822 jne 门控。
实验：把 7 个 listener 的 vtable+0x24 全部锁定并溯源。
结果：**5 个是 0x4F7590（ret 8，空实现）+ 0x738E70（wargod 排位 UI）+ 0x7CAF30（UI/CEF）→ 7/7 无一进 battle**。
更新假设（016）：门控描述被更正 —— 015 只看到 1 道检查，实际有 **GATE-A（[this+0x1C] 非空）** 与
      **GATE-B（[this+0x10758] | [this+0x1075C]）** 两道前置守卫。
当前状态：**LISTENER→BATTLE = REFUTED（7/7，无 UNKNOWN 残留）**；该轴关闭，不要再查。
```

### 10.5 type-2 network object
```
初版假设（003 §3 / 004 §4）：type==2 是"对象类型"判断，可能是 Battle 桥梁。
证据（016 完整反汇编）：0x62FDE0 含 GATE-A/GATE-B → 0x803830 单例 → 0xB7A670 归一化 type →
      ==2 → 0xB7A770 取 [sing+0x3C]；0xB7A670 = byte[sing+0x4F8]!=0 且 0xBA0780([sing+0x4F4])==2。
      唯一创建链 0x7F3890→0xB82070→0xB81EF0→0xBA4080→0xC73900→0xC76920；
      **0xC768D0 = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)**；0x7F278E 引用 "DW_LOBBY_CONNECTED"。
实验（017 动态）：采样 t_C8 1→2、t_644=0、t_5E8 0→1→2→3、net4F8 0→1、dw 0x01→0x02。
结果：**type-2 = Demonware lobby TCP 连接在"已连接"状态下的形态**；
      TYPE2_TO_UDP = REFUTED；ACCEPTED_TO_TYPE2 = 只读/单向使用（accepted 不创建它）。
当前状态：该轴关闭。
```

### 10.6 Battle 触发路径
```
初版假设（014）：accepted → [0x849B61C]=1 → 某个 consumer → battle。
证据（014）：两个 reader 0x7CB1E2 / 0x7CFA87 的下游 0x620590 与 0x7CB210 都是 UI/telemetry。
结果：REFUTED（[0x849B61C] 不是 battle 触发器）。
更新假设（006）：worker 0x6334xx → 0x818de0 是 booking→battle。
证据（007）：0x818DE0 的 6 路跳表只有 state 4 实现，且引用 **"chat.private"**。
结果：REFUTED（那是私聊状态机）。
更新假设（009 / T56）：endpoint 由 findSessions(21/5) 下发 127.0.0.1:28960，battle 是 UDP/DTLS。
结果：**endpoint 来源 CONFIRMED；但 BOOKING_TO_BATTLE_CONNECT = UNRESOLVED**。
实验（015/016/014）：找跨模块调用。
结果：matching(0x62-0x63) 或 lobby(0x7f) → battle(0xE3-0xE5) **直接 call = 0**；
      0x849B61C、listener、type-2 全部被否。
当前状态：**BATTLE_TRIGGER_PATH = UNRESOLVED**；
      客户端内部**独立确认**了 P-224/DTLS 子系统（"DTLS"@0xd55db0、"ECDH"@0xd5611d、"secp224"@0xd3d628，表在 0xE3xxxx）。
```

### 10.7 商城 / 目录
```
初版假设：购买失败是解析问题（C# 的 58B 硬模板太窄）。
证据：TLV 解析后仍有点购买无反应的 SKU。
实验：把解析改成 TLV → sku=32223 成功扣款。
结果：解析问题**确实存在并已修好**，但**不是**主因。
更新假设：目录覆盖不全（客户端用的 SKU 多数不在 exe 目录里）。
证据：连点 6 次，sku 241/242/31774/31816/32223 中只有 32223 在 catalog；
      客户端发的目录版本 token = 1822730568（0x6CA0F2CC）。
实验：内存扫描 → 37615；full 38424；merged 37793 → 37834。
结果：买到 37834，但 80/70 页仍空（商城空白）。
再更新：客户端真正用的是 6 张 coMarketplace*.csv 加 conoMarketplaceitems.csv，version=1625160，
      由内存 zlib 压缩的 mp/marketplace.json 索引。
实验：974 个 .ifs / 146 万 zlib 流 / MD5 全比对 → 0/6。
结果：**表不在 .ifs，也不在文件系统；资源注册表 0x239B120 在 Base.dll 的 .tvm0（壳虚拟化）**。
当前状态：**80/70 页格式至今未解**（三次尝试全被真机否证）；
      商城空白与军火箱页面重叠属同一根因（SKU 页为空）。
```

### 10.8 玩家数据 / 名片
```
初版假设：名片/称号是库存条目，写进 inventory 客户端就该显示。
证据：37251 / 31181 / 31184 服务端购买成功，库存也写入了。
实验：public.result 尾部 125x0x07 注入 8 个 itemID。
结果：REFUTED（客户端毫无变化）。
更新假设：480KB 截断导致高 ID 物品送不到。
实验：4 件最小仓库测试。
结果：**REFUTED**（截断不是原因）。
再更新：名片是**玩家档案里的槽位**（background/title/icon/namePlate/frame），
      客户端读 codo.objects.CallSignObj 的 cardXxxItemID，并需要 mp/callsign*.csv 等 8 张表（我们一张都没有）。
当前状态：**未解决**；MERGE §8.4 结论是"客户端根本不认 marketplace 库存里的名片拥有关系"；
      连第三方 C# 参考实现也以同样方式失败（skus 22858/22865 已提交，余额未变，物品没落地）。
```

### 10.9 发行方（Publisher）
```
初版判断（10-05 HANDOFF_20261005_LOBBY_REACHED）：EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE 是文件名不一致
      → 加同义名回退修好（并因此进大厅）。
后续判断（10-07 PUBLISHER_FAILURE_SPEC-001）：是 .info **本地 NOT_FOUND**
      （FAILURE_FUNCTION=0x66A650；同一 publisher 文件连续失败 3 次）。
再后续判断（10-08 PUBLISHER_FILE_RECOVERY-001）：文件其实都在 REF_LOBBY_KIT\publisher_files\，
      **真正缺的是 Golden 冻结副本的 3 个数据目录**（publisher_files / player_profiles / user_files）。
实验（RECOVERY-002）：建 DEV 副本（含 3 个数据目录）→ fatal 消失，6/14 真正发出。
当前状态：**DEV 副本已解决；Golden 冻结副本仍缺数据目录**。
      ⚠ 三个判断口径不同（文件名 / NOT_FOUND / 目录缺失），**全部保留**（SOURCE_CONFLICT C9）。
```

---

## §11 CONFIRMED BASELINE（拆分：静态确认 / 动态确认 / 静态+动态）

### 11.1 STATIC CONFIRMED（仅静态证据，指令级）
```
- 0x632680 = 统一 mmbook handler（ret 0x14，5 参数），vtable 基 0xDC7274，槽 +0x13C
- +0x140 = 0x62E9F0（mmrsv）；0x632A00 不是 timeout handler
- accepted 唯一副作用写入点 0x63280B（mov byte [matching+0x288],1；全镜像 disp=0x288 且 imm=1 仅此一处）
- A/B 真实写入 = 0x62F6F0，源 [edi+0x168]/[edi+0x16C]；element = matching+0x7470 + idx*0x238（50 项，0x6EF0）
- 元素类 ctor 0x806B50（size 0x238，vtable 0xDC79F0）；vtable[0] = 0x806F20（反序列化器）
- 反序列化器字段序：blob,blob,u32,u32,u32（0xB95D70）→ +0x18/+0x10/+0x11C/+0x120/+0x124；
  tag 0x10 string（0xB76A30）→ +0x128；**tag 0x0A u64（0xB769A0）→ +0x168/+0x16C**；tag 0x10 string → +0x170
- 客户端过滤器 0x637950 用 rec+0x124 <= 1，与服务端字段 #5（u32 1）数值+位置双吻合
- listener 容器 [0x82E13FC]+4 = {head,tail,count} 手写双链表；节点 12B；广播 site 0x632824 / 0x63289E
- 7 个 listener 的 vtable+0x24 = 5 x 0x4F7590(ret 8) + 0x738E70(wargod) + 0x7CAF30(UI/CEF)
- type-2 = Demonware lobby TCP：0xC768D0 = socket(2,1,6)；0xC76920 = connect；0x7F278E 引用 DW_LOBBY_CONNECTED
- 0x818DE0 = 6 态 chat.private 状态机；0x803830 = transport-manager 单例 getter（size 0x1618，vtable 0xD599DC）
- 唯一创建链 0x7F3890 → 0xB82070 → 0xB81EF0 → 0xBA4080 → 0xC73900 → 0xC76920
- 28960 不是客户端常量（0x7120 只出现在 OpenSSL 数据）
- [this+0x278] = 1 字节"预约流程已启动"（29 处访问，仅 2 处置 1：0x62CCCD / 0x62FBBB）
- 客户端内部有独立 P-224/DTLS 子系统（DTLS@0xd55db0、ECDH@0xd5611d、secp224@0xd3d628，表 0xE3xxxx）
- RTTI：全镜像 0 条 type descriptor（类名不可得）
- 客户端对象字段表（codo.objects::Class/field）：挑战 11 类 / 公告 3 类 / 游玩清单-快速匹配 5 类
- 战斗协议：NAT 29B（首字节 13→12，尾 7f 00 00 01 20 71）、DTLS 16→38B、cookie+pubkey 219B、
  ECDH P-224、key=SHA1(x28_be || 0x01x16)→24B、数据帧 06 02 tag seq hmac8 len cipher
- 快照字段序列 29/29（对齐后帧 141B）
- 目录：exe 37615 / full 38424 / merged 37834 / client.bak_inferred 37716 / merged.bak_trusted 37793
- SKU 表布局：+0x00 SKU、+0x04=0、+0x08/+0x0C price、+0x10 days、+0x14 Item、+0x28 price copy
```

### 11.2 DYNAMIC CONFIRMED（真实运行/文件系统证据）
```
- 进入正式大厅 UI：2026-10-05 16:36（lobby_live.png 16:36:34 / lobby_window.png 16:36:51；47 任务；hmac 全 OK）
- 0x83 用本会话 KDF challenge（日志 [challenge 来源: kdf-session, 等待 0.15s]）
- 大厅 keepalive 与 seq/replyId 纪律：主连接 64808 活 4 分 40 秒、56 任务、hmac 全 OK
- 购买真实扣款：sku=32223，GP 883599 → 819999
- 8/3 档案上传：CRC 通过、magic 233/1248641861、重建 public.result 33428 B 一致
- 库存 7620 件 / Priority 37；CP 972299 / GP 523619 / Lv70 / Prestige4
- 发行方 10 个 .info 全部下发（09:21:50），fatal 消失，**09:23:45 首次真正 6/14**
- 6/14 与 71/4、28/1、21/5、11/13、11/4 共用同一条大厅 TCP；重试 3~9 秒（均值约 5.5）
- ACCEPTED_WIRE = CONFIRMED（017: 9 次；019: baseline + test）
- accepted 分支从未执行：this288_byte=1 命中 **0**（017: 0/281+433 行；019: 0/267 行）
- A/B 对齐成立：019 中 A=0x55667788 与 B=0x11223344 各 **72 采样点**；客户端回显 #7 进 mmbook 请求
- [0x849B61C] 会变 1，但与 accepted 无关（同一样本行 this288=0）
- 战斗服：10-06 21:28 唯一一次完整真实握手（收包=155、NAT=2、init=1、keyex=1、data=151、会话=1）
- 战斗服离线回归：battle_selftest.py **13/13 全绿，exit 0**（89 数据帧 / 278 快照帧 / TX_GAMESTATE seq=1 state=259B）
- BATTLE_RX = 0：anchor 之后**每一次真实客户端运行**都是 0
- battle_srv.log 的 2499 条 [stat] 中仅 4 条非零（都在 10-06 21:28）
- 客户端流量去了别处：n10_battlefix 中 28960 出现 0 次；PvE 那轮发往 101.67.36.18:10035 与 112.132.225.216:10009
- 974 个 .ifs 在 2026-10-08 20:32:23 被整体重写（LWT=AT，CT 保留）
- Golden 漂移：lobby_server.py 与 nt10.py 已 DIVERGED，其余核心文件 MATCH
```

### 11.3 STATIC + DYNAMIC CONFIRMED（两边互证）
```
- **type-2 = lobby TCP**：静态（socket(2,1,6) + connect + DW_LOBBY_CONNECTED）+ 动态（t_C8 1→2、t_5E8 0→1→2→3、net4F8 0→1、dw 0x01→0x02）
- **[this+0x278] = booking armed 标志**：静态（29 处访问 / 2 处置 1）+ 动态（18:12:48.338 this278=0x0101）
- **A/B 字段身份 = 21/5 会话对象 #7 u64**：静态（0xB769A0 tag 0x0A）+ 动态（改 #7 后 matching A/B 随之改变，且客户端回显）
- **发行方 fatal 机制**：静态（0x66A650 / 连续 3 次失败 / xref 0x66A827）+ 动态（10 个 .info 全缺 → fatal；补齐后消失）
- **战斗握手协议**：静态（battle_server.py 实现）+ 动态（10-06 21:28 真实客户端完整走通）+ 独立复现（selftest 13/13）
- **6/14 走大厅 TCP**：静态（0x85 帧解析路径）+ 动态（NDIS 抓包与日志同一条连接）
- **80/70 页会导致客户端锁死**：动态为决定性证据（三次真机否证）；静态仅给出 dispatch 方向（exe 0xBA3710 → TenProxy 0x12817980）
```

---

## §12 CURRENT UNKNOWN（按优先级）

### P0（直接阻塞当前主线）
```
U0-1 **marker=0x02 推送能否被派发到 0x7F1400**（accepted 走 push 而非任务应答）
     —— 若不能，应把 accepted 改成 6/14 的应答对象（marker 0x01，replyId = 请求 seq）
U0-2 **0x632680 是否被"进入"过** —— 无持久副作用出口，无法区分"从未进入"与"进入后被守卫拦下"
U0-3 **额外未采样守卫**：[0x76446B0] < 3（0x63269B/0x6326A2）、[matching+0xE360] >= 0（0x6326AA/0x6326B0）
U0-4 **booking-armed 窗口时序**：byte[matching+0x278] 实测只在大约 20~30 ms 窗口为 1，与应答到达的时序关系未定
U0-5 **BATTLE_TRIGGER_PATH**：matching/lobby → battle 直接 call = 0；跨模块间接触发未定位
```

### P1（重要但非当前阻塞）
```
U1-1 **PvE booking（6/14）真实 wire 格式** —— ol-mod 源码全盘不存在
U1-2 **80/70 SKUObj 页的真实字段顺序** —— 三次真机尝试全被否；只有 exe accessor 字段名清单
U1-3 **客户端 battle UDP socket 创建点与握手 parser**
U1-4 **#7 vs #28 客户端实际读哪个**（019 推断只读 #7，018 说要再展开 0x806F20 读序）
U1-5 **0x806F20 的 rec 流是否逐帧来自 21/5 应答**（018 定为 STRONG_CANDIDATE，未逐帧证）
U1-6 **名片 ref → itemID 映射**（pcb/pci/pct/pcai/pcab/pcaf/pcf/pcn/cnc/bdg）
U1-7 **MOTD / 挑战 / 活动占位文件**（审了、计划了、没做；#1125 / #1010 仍在）
U1-8 **mirror_predicted.on 在真实运行中是否真的提供过位置数据**（predicted.bin 现不存在）
```

### P2（未解事件与归属）
```
U2-1 **M-28：974 个 .ifs 在 2026-10-08 20:32:23 被整体重写** —— 机制不明（IIPS 就地修复 / 批量恢复 / 仅改时间戳）
U2-2 **M-23：2026-10-07 15:43:11 谁改了 inventory / player-account / secure.result** —— 无脚本会写 secure.result
U2-3 **DEV 副本的 CP 966299 / GP 479999 与 Golden 冻结值 972299 / 523619 的差异**
U2-4 **sku 22632 的三条新 Unsupported 记录**（DEV unknown_skus.txt 158 行；append-only，无时间戳）
U2-5 **_020_* 与 _gist_tmp.md 的作者归属**（疑为并行考古任务；不改变任何结论）
U2-6 **_lb015 45 个脚本的结论**（无报告、无输出）
U2-7 **_s1.py 的输出**（无留存）
U2-8 **10-06 21:28 那次会话是真机还是实验重放**（日志无法区分；docs 断言真机）
U2-9 **101.67.36.18:10035 / 112.132.225.216:10009 / 127.0.0.1:10001 由谁发出**，重定向能否让客户端改用 28960
U2-10 **idx 45 / idx 219 的真实语义**；"29/29"是否只对单一参考 trace 成立（参考 trace JSON 不在本工作区）
U2-11 **4 个 CODOLServer 文档（TLDR / MASTER_REPORT / DYNAMIC_CAPTURE_LAYER2 / REVERSE_MANUAL）
       对 battle 关键字 grep 0 命中** —— 它们不是战斗线前置
U2-12 **battle_security_key.txt 全零是否有意**（read_security_key 拒绝全零并回落 0x01x16）
U2-13 **configs_s.info（311B，疑似加密）与 market_ui.info（16B zlib）** 的内容
U2-14 **marketplace-inventory-full.on（不截断路径）是否曾被启用**
U2-15 **itemgroup SKU 页在 15:07 回滚后是否被重试过**
```

### 已有明确答案但常被误记（列出以防再问）
```
N-1 0x632680 的槽位 = +0x13C（不是 +0x140）            N-2 type-2 不是 battle 桥
N-3 listener 里没有 battle（7/7）                       N-4 A/B 不是 SessionId 低/高 32 位
N-5 28960 不是客户端常量                                N-6 battle 不是 TCP
N-7 6/14 不走独立 socket                                N-8 [0x849B61C] 不是 accepted 判据
N-9 013 的 MATCH 结论已被 017/018 推翻
```

---

## §13 CLOSED / DO NOT REPEAT（已关闭，不要重复）

```
D-1  **不要再查 listener 方向的 battle 桥** —— 7/7 全部溯源完毕，无一进 battle（CONFIRMED 级否证）
D-2  **不要再查 type-2 network object 是 battle 桥梁** —— 它是 Demonware lobby TCP 连接
D-3  **不要再查 [0x849B61C] 作 accepted 判据** —— 至少 12 个写入者，且与 accepted 无因果
D-4  **不要再查 senderId 端序 / A/B 拆半序** —— 无 bswap；且边已对齐（AB_ALIGNMENT = CONFIRMED）
D-5  **不要再动 A/B（019 已证明必要非充分）** —— 再对齐也不会让 accepted 执行
D-6  **不要再用 0x818de0 当 booking→battle worker** —— 它是 chat.private 私聊状态机
D-7  **不要再用 0x803830 当 socket/connect** —— 它是 transport-manager 单例 getter
D-8  **不要再把 0xB81EF0 当 battle connect** —— 它是大厅 DNS/lobby 主连接链
D-9  **不要再找 28960 的客户端常量** —— 它是 21/5 findSessions 动态下发的 endpoint
D-10 **不要再假设 6/14 有独立 socket / 走 UDP / 走 HTTP** —— 它就是大厅 TCP 上的 0x85 帧
D-11 **不要再用靶场信封回答 PvE booking** —— 9/9 断连，已冻结 .OFF_CONFIRMED_CRASH
D-12 **不要指望"客户端能从 UI 进入靶场"** —— 本 build 无独立靶场入口（playlist 10 里的 coop 关卡）
D-13 **不要再猜 80/70 的 SKUObj 线格式** —— 三次真机尝试均导致商城/角色锁定；要动只能先补判据
D-14 **不要再用字符串搜索否证 .ifs 里没有某资源** —— .ifs 是部分明文，字符串法无效；要用 MD5 全比对
D-15 **不要再尝试 .ff 层二静态解密** —— 所有假设已否（含小样本熵误判的教训）
D-16 **不要再指望 Frida / 断点捕获** —— ACE 保护 + Golden 纪律双重禁止；可用能力上限是只读采样
D-17 **不要再把 firingrange-clientstats-last.bin 当真实客户端抓包** —— 已被 selftest 随机字节覆盖
D-18 **不要用 mtime 判定 firingrange-gamestate.bin 的恢复时间** —— 复制保留了源时间戳（10-04）
D-19 **不要再找 10-05 / 10-06 的大厅服务端日志** —— 已确认不存留（最早是 10-07）
D-20 **不要再以"未改 Golden"为前提陈述** —— lobby_server.py 与 nt10.py 已确认漂移
D-21 **不要用 _015_glob.py 的 or-全局 结果** —— 1 字节回溯假阳性
D-22 **不要把 marketplace-catalog-merged.json 的低 Item 条目当"安全"** —— 与 TAKEOVER §13.2 冲突（SC-01）
```

---

## §14 工程状态表（领域 / 状态 / 已完成 / 当前缺口 / 证据）

| 领域 | 状态 | 已完成 | 当前缺口 | 证据 |
|---|---|---|---|---|
| **Lobby-UI** | 可用但内容空 | 大厅能进、能渲染、能长连（47+ 任务，hmac 全 OK）；71/7 崩溃链全部解码；playlists 升到 version 796 | 商城空白 + 军火箱页面重叠（80/70 空）；游玩清单仍空（模式/地图名不对）；MOTD #1125 / 首页挑战 #1010 未修 | lobby_live.png / lobby_window.png；HANDOFF_20261005_LOBBY_BUGS.md；LOBBY_MAP.md；lobby_task_matrix.csv |
| **Player-Profile** | 部分可用 | 8/1 public.result、8/2 secure.result、**8/3 上传保存**全部工作（CRC/magic/33428B） | 名片槽位（cardXxx）不认；档案尾字段语义只有部分解出 | lobby_server.py:44-166；HANDOFF_20261006_MAIN.md §6；public.result 33428B |
| **Inventory** | 可用 | 7620 件 / Priority 37；480KB 上限已用 460KB 规避；购买可写入 | 物品"拥有"语义在客户端侧不生效（名片类）；截断与锁定的边界判据靠 check_run.py 事后发现 | marketplace-inventory.json（+bak_big/bak_full）；marketplace_store.py:549-637 |
| **Weapon** | 可用 | 武器类 SKU 购买成功（22251/22255/31726/31847 → 库存递增）；WL_FillInInventoryProductItems 字段已知 | 无独立武器线；共用 marketplace 缺口 | BUY_MATRIX.md；MAIN.md §1；CLIENT_OBJECT_SCHEMA.md |
| **Marketplace** | 部分可用 | 目录 37615→37834；购买 TLV 解析；currency-lenient；SKU 表 635 条高置信；34911 条资产路径 | **80/70 页线格式未解**（三次真机否证）；6 张 coMarketplace 表宿主未定位；11 个 SKU 仍缺 | MAIN/MERGED/CATALOG_LAYOUT/MARKET_MANIFEST.md；marketplace-catalog-merged.json；sku_table_v2.csv |
| **Publisher** | DEV 已解决 | 10 个 .info 全部下发；fatal 消失；SHA-256 基线齐全 | Golden 冻结副本仍缺 3 个数据目录（publisher_files/player_profiles/user_files） | PUBLISHER_FAILURE_SPEC-001；PUBLISHER_FILE_RECOVERY-001/002 |
| **Protocol** | 可用 | 0x81/0x82/0x83/0x85 框架、KDF challenge、keepalive、seq/replyId 纪律全部成立；6/14 响应通道 = 大厅 TCP；分派链闭合 | 推送 marker=0x02 的派发可达性未证实；PvE booking 真实应答格式未知 | LOBBY_REACHED.md；RESPONSE-CHANNEL-003 / DISPATCH-004；lobby_server.py:4-14 |
| **Local Server** | 可用 | REF_LOBBY_KIT 一套（lobby_server / codol_crypto / battle_server / fake_auth_tls / marketplace_store / nt10 / run_all） | 自研 CODOLServer 栈自 10-05 15:05 冻结，已非产品路径 | REF_LOBBY_KIT/*.py；_golden_hashes.json；S1 结构发现 |
| **Room** | 部分可用 | 11/13 createRoom OK；11/4 setRoomData 空应答（靶场用） | 无真实房间流程验证；handler 为 ol-mod 移植（注释日期 10-03/10-04） | LOBBY_MAP §1.3；lobby_server.py:769-836 |
| **Session** | 可用 | 21/5 findSessions 下发单条会话对象（靶场/PvE）；SESSION_ID / ROOM_ID 约定明确 | 21/5 应答长度口径冲突（258 / 306 / 338 字节，SC-4）；客户端是否只读 #7 未逐帧证 | codol_crypto.py:539-551；lobby_server.py:591-628 |
| **Matchmaking** | 部分可用 | PvE playlist 路由已加（PVE_PLAYLIST_IDS）；coop_map 自纠环 | 只能滞后一轮收敛；无独立匹配流程；playlist 集合仅 [1..6,10] | BATTLE_SERVER_PROTOCOL §8.1-§8.7；lobby_server.py:862-879；coop_map.txt（0B） |
| **PvE** | 部分可用 | 6/14 mmbook 真正发出（09:23:45）；accepted 推送确实上线；UIException 可解 | accepted 分支不可达；靶场路径不可达；ol-mod 源码缺失 | PUBLISHER_FILE_RECOVERY-002；PVE-ACCEPTED-STATE-DYNAMIC-017；PVE-MATCHING-AB-ALIGN-019 |
| **Booking** | 静态闭合 / 动态卡住 | 契约→通道→分派→参数→状态全链静态闭合；A/B 身份与对齐成立 | **accepted handler 未执行**；marker 通道未证实；armed 窗口时序未定 | BOOKING-CLIENT-CONTRACT-001；SPEC-001..004；FIELD-IDENTITY-018；ALIGN-019 |
| **Battle** | 服务端就绪 / 客户端未接入 | NAT/DTLS/ECDH/数据帧实现；connect_done 修复；snapshot 29/29；selftest 13/13 | **BATTLE_TRIGGER_PATH 未定位**；10-06 之后无真实客户端接入 | battle_server.py；BATTLE_SERVER_PROTOCOL.md；battle_selftest.py |
| **UDP** | 就绪未用 | 0.0.0.0:28960 持续监听（含通宵）；端口归属由 21/5 下发 | 客户端从未拨入；4 个 UDP 创建点无一可证属 battle | battle_srv.log（64 次启动）；MVP-PVE-MATCH-ENTRY-009 |
| **DTLS** | 就绪未用 | DTLS init 16→38B cookie、cookie+pubkey 219B 走通；客户端内部独立确认 P-224/DTLS 子系统 | 客户端 battle 握手 parser 未定位 | battle_server.py:412-448；BATTLE-OBJECT-016 §3 |
| **Resources** | 部分可用 | .ff 层一解密（10/10 main*.ff，RSA 键 = IW4X ZoneKey）；资源挂载审计；974 包约 23.8 GB 清单 | 层二未解；6 张市场表宿主未定位（.tvm0）；**974 个 .ifs 在 10-08 20:32 被整体重写（原因不明）** | FF_LAYER1_DECRYPT_20260930.md；ASSET-02/05/07；_cleanout/*.layer1.bin |
| **Assets** | 部分可用 | mkt_assets 清单 34911 唯一路径 / 124929 条目 / 18 包；callsign_*.csv（4784 refs）；playlists .info 重建 | 资产→itemID 映射未解；callsign 8 张表全缺；configs_s.info / market_ui.info 未解 | mkt_assets/mkt_assets_summary.md；ASSET-03 |
| **Reverse Engineering** | 强（有明确边界） | image_best.bin 静态体系；listener/type-2/0x818de0/0x803830 全部定性；唯一判据法（disp+imm 扫描）；RTTI 0 条已确认 | 断点/Frida 不可用；壳虚拟化节（.tvm0 / tp_runtime.bin）是静态天花板 | DEV-BOOKING 全系列；_015_* 至 _019_* 工具链 |
| **Tools** | 丰富且可复现 | battle_selftest.py（13/13）；snapshot_diff.py；check_run.py；_accprobe 只读采样；_020_* 文档索引；一整套 capstone 脚本 | 部分一次性脚本（_lb015 45 个、_s1.py）无输出留存 | 见 §18 工具清单 |
| **Reference Research** | 结论明确 | IW4X 不 ABI/协议兼容（仅结构参考）；依赖 F: 盘 C# 参考；ol-mod 全盘不存在 | F: 盘内容不在本工作区（外部依赖）；playerstate-motion-trace.json 缺失 | IW4X_CODOL_REUSE_REPORT.md；STAGE_REPORT_BATTLE.md:180-206 |
| **Other（环境/守护）** | 受限但清楚 | 提权代理（agent_client.py + nt10.py）是唯一动态通道；ACE/TP3 封死外部读内存与断点 | ACE 未移除、未绕过（NOT_COMPLETE）；UAC 需人工批准；10-08 20:32 的 IIPS 活动未解释 | CODOLServer/_mainline；GOLDEN-LOBBY-001.md:180；run_codol_001/* |

---

## §15 从"首次进入正式大厅"到"当前最远状态"的完整状态机

```
[2026-10-05 15:05] 自研 CODOLServer 大厅栈最后一次修改（此后永久冻结）
        │
        ▼
[2026-10-05 约 16:00] 改用第三方 REF_LOBBY_KIT（F: 盘复制）
        │  34 条任务 / hmac OK / 仍弹 [100]
        ▼
[2026-10-05 16:01-16:03] ready_push + mirror_predicted 轮 ──► ✗ 弹窗照旧（假设 REFUTED）
        │
        ▼
[2026-10-05 16:30-16:40] 两个真实修复（0x83 本会话 KDF challenge；10/21 同义名）
        │
        ▼
[★ 2026-10-05 16:36] **进入正式大厅 UI**（47 任务 / 窗口类 CODO / 标题"使命召唤online"）
        │
        ▼
[2026-10-05 16:47] 重连 hmac=BAD 被重新归因 ──► "BAD 是结果：没有游戏世界"
        │
        ▼
[2026-10-05 16:55] 靶场开关组（session ON / battle ON / booking-push OFF）
        │
        ├──► [10-05 17:16-18:26] 全面发放物品 + 71/7 UIException 通道识别
        │
        ├──► [10-05 18:35] 大厅 BUG 全量诊断（4 条崩溃链 / 21 个未映射服务）
        │
        ├──► [10-05 20:44 → 10-06] 商城目录战役（37615 → 37793 → 37834）
        │         ├─ 购买 TLV 修复 OK
        │         ├─ 自编 SKU 页 → 商城/角色锁死 ✗（回滚）
        │         ├─ sentinel 探针 → 同样锁死 ✗（回滚）
        │         ├─ itemgroup SKU 页 → 同样锁死 ✗（回滚）
        │         └─ 80/70 页格式 ──► **UNKNOWN（至今）**
        │
        ├──► [10-06 21:49] playlists 重建（version 796）──► 版本崩溃消失，列表仍空
        │
        └──► [10-06 22:33] 大厅协议地图（LOBBY_MAP.md）
        │
        ▼
[2026-10-06 21:28] ★ 战斗服唯一一次完整真实握手（收包=155 / TX_GAMESTATE=0）
        │
        ▼
[2026-10-07 14:44 → 15:39] 战斗服修复三连
        │   ① firingrange-gamestate.bin 恢复（259B）
        │   ② connect_done + snapshot_due（15:01 首次 TX_GAMESTATE）
        │   ③ 大厅 keyset 纪律（88 OK / 0 BAD）
        │
        ├──► [10-07 10:34] 强制靶场 session ──► battle RX=0 ✗（REFUTED）
        │
        ├──► [10-07 17:45-18:13] mmbook accepted 推送 → 9/9 断连 ✗
        │         └─► 冻结 .OFF_CONFIRMED_CRASH（关闭后"服务器繁忙"）
        │
        ├──► [10-07 19:01] ★ GOLDEN-LOBBY-001 冻结（22 文件 + 哈希）
        │
        └──► [10-07 19:13] STAGE_REPORT_BATTLE：P0-2 ol-mod 源码 ──► **BLOCKED（全盘 0 命中）**
        │
        ▼
[2026-10-07 19:22 → 19:46] Booking 静态第一阶段（001-004 规格）
        │   0x632680 = 统一 handler；A/B 真实写入 0x62F6F0；reservation this+0x75D8 / stride 0x238
        │
        ▼
[2026-10-07 19:50 / 20:10] 运行期观测
        │   断点路线 ──► INSTRUMENTATION_BLOCKED（ACE + Golden 纪律）
        │   NDIS 观测 ──► 6/14 NOT_SENT → 阻塞在 EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE
        ▼
[2026-10-08 09:10 → 09:25] 发行方文件恢复（DEV 副本）
        │   fatal 消失；★ **09:23:45 首次真正发出 6/14 mmbook**
        ▼
[2026-10-08 12:14 → 14:33] Booking 静态第二阶段
        │   响应通道 = 大厅 TCP（SHARED_CONNECTION_CONFIRMED）
        │   分派链修正（+0x13C = 0x632680；+0x140 = 0x62E9F0）
        │   0x818de0 = chat.private（砍掉错误轴）
        │   endpoint = 21/5 下发的 127.0.0.1:28960
        ▼
[2026-10-08 14:49] ★ M-25：信封 senderId 1 → SESSION_ID（lobby_server.py）
        │   这意味着第一守卫从此必然失败（见 §6.3）
        ▼
[2026-10-08 14:57 / 15:14] 动态验证
        │   011：UAC 未批 ──► ENVIRONMENT_BLOCKER
        │   012：wire senderId = SessionId OK，但 battle RX=0
        ▼
[2026-10-08 15:23 → 18:55] 枚举与闭合
        │   013 A/B 拆半序（后被推翻）
        │   014 [0x849B61C] 不是 battle 触发器
        │   015 ★ listener 7/7 全部证伪
        │   016 ★ type-2 = lobby TCP（UDP 桥假设被否）
        │   017 ★ accepted 分支从未执行（唯一判据建立）
        │   018 ★ A/B = 21/5 会话对象 #7 u64（013 被推翻）
        ▼
[2026-10-08 20:07-20:26] ★ 019 单变量 A/B 对齐实验
        │   A/B 对齐成立（72 采样点）+ 客户端回显 #7（行为级确认）
        │   但 accepted 分支仍未执行（267 采样点 this288=0）
        │   所以 RESULT_CASE = B；0x6326B9 = NECESSARY BUT NOT SUFFICIENT
        ▼
[2026-10-08 20:32:23] ⚠ 974 个 .ifs 被整体重写 ──► **UNKNOWN（机制）**
        ▼
[2026-10-08 20:44] 当前最远状态：
        BATTLE_RX = 0 ；ACCEPTED_HANDLER_EXECUTED = NO ；AB_ALIGNMENT = CONFIRMED
        NEXT_GATE = ADDITIONAL_ACCEPTED_GUARD（首选：marker 0x02 通道 vs 0x01 应答对象）
```

图中所有分叉都是**并行工作流**，不是时间顺序；标 ✗ 的是被证伪的分支，标 ★ 的是关键节点。
两条链的终点是 **UNKNOWN**：① 80/70 SKU 页格式；② booking→battle 触发路径。

---

## §16 最终十问

**Q1. 进入正式大厅之后，项目到底做了哪些工作？**
按时间共 **78 项**（§3）。主干是七条并行工作流：
① 大厅链路与协议打磨（T01-T14、T38-T41）；② 商城/目录/购买/玩家档案（T15-T29、T33）；
③ 大厅 UI 内容补全与崩溃链修复（T30-T32、T34）；④ 发行方文件恢复（T48-T50）；
⑤ Booking/PvE 逆向 001→019（T45-T47、T51-T53、T57-T60、T64-T66）；
⑥ 战斗服与 UDP/DTLS 净码（B-00 至 B-21，含 10-07 的三连修复与 selftest）；
⑦ 资源/资产/参考研究/工具（ASSET-01..08、REF-01..04、RE-01/02、RUN-01、TOOL-01..03）。

**Q2. 其中哪些属于"大厅修复"？**
T03（0x83 challenge + 10/21 同义名，直接产生 anchor）、T02（推送轮，失败）、T06/T07（keepalive 与重连重新归因）、
T12（物品发放）、T13/T14/T30（71/7 UIException 通道 → 4 条崩溃链）、T31（playlists 重建）、
T32/T34（数据源审计 + 协议地图）、T38（客户端对象字段表）、T41（推送序号机制）、
M-19（keyset 纪律修复）。**大厅本身在 10-05 16:36 就通了；之后是在补内容。**

**Q3. 哪些延伸到了 PvE / Booking / Battle？**
From T56（MVP-PVE-MATCH-ENTRY-009 定义 accepted→PvE 缺链）起：T57（改 booking 应答 senderId）、
T58/T59（两次动态验证）、T60（A/B 拆半序）、T64/T65/T66（accepted 状态、字段身份、对齐实验）；
战斗侧 B-04/B-05/B-06（game state + 快照）、B-09（大厅 keyset）、B-10（coop_map 自纠环）、
B-11（推送崩溃）、B-12/B-13（靶场路径不可达）、B-17/B-18（动态确认 accepted 未执行）。
**两个领域在 10-08 汇合到同一个阻塞点**：客户端侧的 booking→battle 触发路径。

**Q4. 哪些是纯逆向（无任何服务端/数据改动）？**
T45（Booking 静态 001-004）、T51/T52/T53（响应通道/分派/参数）、T54/T55（worker/connect path）、
T60（013）、T61（014）、T62（015）、T63（016）、T65（018）、
B-00/B-06 的静态部分、ASSET-01/02/04/05、REF-01、RE-01/02、以及 CLIENT_OBJECT_SCHEMA 的提取。
纪律上这些全部标注"未修改 Golden/Server/patch/KDF hook，未启动游戏"。

**Q5. 哪些是服务端 / 数据重建？**
**服务端代码**：M-01（0x82 challenge 分支）、M-06（购买 TLV）、M-09（购买应答形状）、
M-17（connect_done/snapshot_due）、M-18（快照字段）、M-19（keyset 纪律）、M-20（推送序号）、
M-25（booking 应答 senderId）、M-26（nt10 只读采样）。
**数据**：M-02（publisher 别名）、M-03（开关组）、M-04/M-05（库存 7→17372→7620）、
M-07/M-08/M-10/M-12（目录 37615/37716/37793/37834 + 货币宽松）、M-11（public.tail，已回滚）、
M-13（playlists 重建）、M-16（gamestate 文件）、M-24（DEV 副本含数据目录）、
M-27（codol_crypto #7，已回滚）；以及 sku_table_v2.csv、item_sku_arrays.csv 两张逆向表的产出与修复（RB-8）。

**Q6. 哪些成功了？**
见 §5.1 的 S-1 至 S-22。最实质的五个：**进大厅（S-1/S-2/S-3）**、**购买 TLV 解析并真实扣款（S-4）**、
**发行方恢复解锁 6/14（S-10）**、**battle_selftest 13/13（S-14）**、**A/B 字段身份闭合 + 对齐实验（S-19）**。

**Q7. 哪些失败了？**
见 §5.3 的 F-1 至 F-11 与 §9 的 FL-1 至 FL-11。最重的三个：
**自编/sentinel/itemgroup 三次 SKU 页事故（两次把角色锁死，FL-1/FL-2/FL-3）**、
**accepted 分支始终不可执行（FL-6）**、**ol-mod 源码缺失导致 PvE booking 格式永久未知（FL-7）**。

**Q8. 哪些被回滚了？**
见 §7 的 RB-1 至 RB-11。完整清单：
自编 SKU 页、public.result 尾部注入、sentinel 探针、replyId 独立计数器、推送 +1000 偏移（机制保留/效果被否）、
itemgroup SKU 页、低 Item 合并（部分残留）、sku_table 覆盖事故（已恢复 + 加写保护）、019 的 #7 = SessionId（已 SHA-256 校验恢复）、
目录覆盖实验（部分）、商城协议实验整体冻结。
**回滚遗留三件**：RB-7 的低 Item 残余（SC-01）、M-23 的不明写入、M-28 的 974 个 .ifs 重写。

**Q9. 哪些历史假设被证伪了？**
见 §5.5 的 RF-1 至 RF-29 与 §10 的九条演变链。最关键的六条：
重连 hmac=BAD 是密钥竞态（自我更正）、accepted handler 在 vtable +0x140（更正为 +0x13C）、
0x818de0 是 booking→battle worker（实为 chat.private）、listener 里能找到 battle（7/7 否证）、
type-2 是 battle 桥（实为 Demonware lobby TCP）、A/B = SessionId 低 32 位（实为 21/5 会话对象 #7 u64）。
另加：**A/B 对齐即可解锁 accepted（019 证明必要非充分）**。

**Q10. 项目现在处在什么状态？**
```
可运行状态：
  大厅        能登录、能进 UI、能长连、hmac 全 OK、47+ 任务
  服务端      REF_LOBBY_KIT（DEV-PUBLISHER-RESTORE 副本）运行；battle_server 监听 0.0.0.0:28960
  基线        GOLDEN-LOBBY-001 冻结仍在，但 lobby_server.py 与 nt10.py 已漂移（§6.2）
未完成状态：
  商城        空白（80/70 页格式 UNKNOWN）
  名片/称号   买到不显示（阻塞在客户端侧，UNKNOWN）
  MOTD/挑战   仍是占位文件（未重写）
  PvE/Booking 6/14 已发出，但 accepted 分支不可达（NEXT_GATE = 通道/marker）
  Battle      服务端完整就绪且可离线自证，但客户端自 10-06 21:28 起从未拨入（BATTLE_RX=0）
当前最前沿：**0x6326B9 已证明必要非充分；下一步是确认 marker=0x02 推送能否到达 0x7F1400**
          （若不能，把 accepted 改成 marker 0x01 的应答对象，replyId = 请求 seq）。
```

---

## §17 SOURCE_CONFLICT 汇总（全部双留，不静默修正）

### A 组：大厅链路 / 协议（S1）
```
A1 **协议知识归属**：HANDOFF_20261005_PUSH_TO_LOBBY.md（16:04）称 lobby_plain_probe.py 已按参考实现改好
   （seq 回显 + replyId 自增）并列了完整 reply_objects() 分发表；
   但该文件 mtime = **2026-10-05 15:05:09**，其后该目录再无写入，PUSH_TO_LOBBY 描述的编辑在磁盘上不存在。
   REFKIT_WORKS §6 则明确说应在 REF_LOBBY_KIT 上做。**两边都留**；anchor 后的现实与 REFKIT_WORKS 一致。
A2 **重连失败**：HANDOFF_20261005_LOBBY_REACHED.md §1.1/§1.2（密钥竞态框架）vs §2.5（"BAD 是结果，不是原因"）。
   **同一文件内自相矛盾，两段都留**；§2.5 更晚且与日志一致。
A3 **推送的作用**：REFKIT_WORKS §2.3 说参考实现确实主动推送（service=11/21、RAW_GAME_START 136B）；
   同文件 §4.5 说开启 ready_push+mirror_predicted 毫无变化、0B/4 从未出现。**两边都留**。
A4 **21/5 应答长度**：lobby_server.py:19 注释 258B；LOBBY_MAP §1.3 只写 OK；存活日志为 306B 与 338B。
   **三口径都留**，至少两种应答形状。
A5 **11/4 是否出现**：REFKIT_WORKS §4.5 说 0B/4 从未出现；lobby_server.py:784/797 的注释说
   2026-10-03 实测客户端确实发过 16B ready 批次。**两边都留**（不同会话）。
A6 **引用的截图不存在**：REFKIT_WORKS §4.5 引用的 lobby_check.png / v2.png / v3.png
   在全工作区 **glob 0 命中** —— "仍然弹窗"这一结论目前只有文字、没有物证。
```

### B 组：Booking / PvE（S3）
```
B1 **accepted handler 的 vtable 槽位**：001 §10.2 / evidence-002 / 003 说 base 0xDC7270、accepted = +0x140、
   timeout = 0x632A00 @ +0x13C；004 §7/§9 与 015/016/017 说 base 0xDC7274、**+0x13C = 0x632680**、
   +0x140 = 0x62E9F0、0x632A00 不是 timeout。后者有 dispatcher 反汇编与 0x62C025 ctor 为决定性证据。**两版都留**。
B2 **matching A/B 的字段身份**：005 §4/§5、010 §9/§10、013 §3 说 = SessionId 低/高 32 位且判 MATCH；
   017 §8.1、018 §0/§7.3/§8、019 §0 说 = 21/5 会话对象 #7 tag-0x0A u64（值 1），两边不等。
   018 明确把 013 标为 REFUTED 中间步。**两侧都留**。
B3 **0x0849B61C 是否 accepted 标记**：005/006/014/015/016 当作 accepted 状态之一；
   017 §8.2 用实测（同一样本行 flag=1 而 this288=0）证明它**不能作判据**，并列出 5 个 matching 侧 + 7 个 UI 侧写点。
   **两侧都留**（017 只否证"可作判据"，未否证 0x632827 写过它）。
B4 **worker 0x6334xx → 0x818de0 的归属**：006 §9 说 booking→battle；007 §6 说 0x818de0 是 chat.private。
   **两侧都留**。
B5 **"type==2"的语义**：003 §3、004 §4/§8、005 §5 当作对象类型判断；
   016 §3/§0 说是归一化连接状态（4 字段决定），type-2 = Demonware lobby TCP。**两侧都留**。
B6 **0x62FDE0 的门控结构**：015 §2 说只有一道检查；016 §2/§0 补出 GATE-A 与 GATE-B 两道前置守卫。
   016 明示"对 015 的重要更正"，未推翻其余结论。**两侧都留**。
B7 **marker=0x02 能否到达 0x7F1400**：004 §3/§10/§11 标 HIGH-CONFIDENCE；
   017 §10.3 / 019 §6.2/§7 重新列为**未证实**。**两侧都留**（这是当前 P0 未解门）。
B8 **lobby_server.py SHA-256**：RECOVERY-002 §2/§8 = D7EEB456…（Golden 值）；
   ALIGN-019 §2.1 = 2E32E719…（"从未修改"）。**时间序可解释**（010 在 14:49 改了 senderId）；
   本报告进一步用 _golden_hashes.json 确认为真实漂移（§6.2）。
B9 **发行方 alias 修复状态**：LOBBY_REACHED §1.2 说 10-05 已把别名文件放好；
   RUNTIME_NETWORK-002 §3 说 10-08 同一 fatal 再现；RECOVERY-001 说 Golden 副本整个 publisher_files/ 缺失。
   **三方都留**（可能是重新冻结/DEV 副本策略变化）。
B10 **GAME_IP / GAME_PORT 的客户端存储位置**：014 §6 = UNRESOLVED；015 §12.5 = CANDIDATE（session +0x18/+0x1C）；
   016 §9.1 = HIGH-CONFIDENCE（transport [t+8]+4 网络序 IP / 0xB75440 主机序 port）。三档证据层级并列保留。
```

### C 组：商城 / 目录 / 资产（S2、S5）
```
C1 **低 Item 条目可否合并（重大）**：TAKEOVER §13.2 说必须**不**合并（会导致"假成功、入错物品"）；
   同一文件 §14.4 又实现了同类合并（只对目录中不存在的 SKU）。**实测**：当前
   marketplace-catalog-merged.json(37834, 10-07 13:48) **确实含那 9 个低 Item SKU**。**两侧都留**。
C2 TAKEOVER §3 说运行目录 = 37793；§14.4 与 BATTLE_SERVER §7 说 37834。**实测 37834**，§3 已过期。两侧都留。
C3 TAKEOVER §13.2 引用的 marketplace-catalog-merged.json.bak_before_sane_lowitem_20261007 **不存在**
   （只有 .bak_trusted_37793_20261007）。**两侧都留**。
C4 BATTLE_SERVER §7（14:45 快照）说 marketplace-skus-itemgroup.on 开、count=5；
   §1.4（15:07）说已关且两文件删除。**实测**：两文件均不存在（OFF）。两侧都留。
C5 BATTLE_SERVER §1.5 说 item_sku_arrays.csv = 2067 条 / 576 items；§8 说恢复后 = 572 items / 1609 行。
   **实测 1609 行 / 572 items**。两侧都留。
C6 GOLDEN §1.2 冻结 inventory 7620 / CP 972299 / GP 523619；TAKEOVER §3 说 7614；
   DEV 副本显示 CP 966299 / GP 479999 且库存更大（10-08 被改动）。**两侧都留**，以 Golden 为基线。
C7 CALLSIGN_CHANNEL 说 480KB 截断可完整解释"所有购买无效"；同一文件的 4 件最小仓库实验
   证明截断**不是**原因。**两侧都留**，以后者为准。
C8 **IW4X 依赖口径**：STAGE_REPORT_BATTLE.md:180-184 说 IW4X 直接引用 = 0、"不声称当前 Server 基于 IW4X"；
   FF_LAYER1_DECRYPT_20260930.md 与 _PLAINTEXT_PROJECT README 说 .ff 的 RSA 键**与 IW4X ZoneKey 逐字节相同且被使用**。
   两者可共存（加密资产 vs 服务器代码），但读起来像矛盾。**两侧都留**。
C9 **RESTORE_ENGINE_BRIDGE 002 vs 003**：002_FINAL = 全部 UNKNOWN/NOT_OBSERVED；
   003_DECISION = COMPLETE / LOCALRM_LOAD=PASS / GETRM=FAIL。**两侧都留**（003 为后出）。
C10 **LocalRM 可构建性**：LOCALRM_001_FINAL = 无编译器/未构建/ABI 多数 UNKNOWN；
    LOCALRM_004_FINAL = PE32 已构建 / GetProcAddress PASS / LoadLibrary FAIL（磁盘上确有 LocalRM.dll、v2、v3）。
    **两侧都留**。
C11 **IIPS [100]**：IIPS_ROOT_CAUSE.md 说 host 从未初始化、是本地管道失败；
    HANDOFF_20260927_IIPS_GATE_RESOLVED.md 与 10-05 进大厅暗示该门已过。**修复 vs 绕过未定，两侧都留**。
C12 **层二"弱密钥"信号**：_mkt_period_probe.py 说 dist=0x1000 熵 7.41 明显偏低；
    LOBBY_BUGS.md:161-170 说那是小样本偏差（64KB→7.999、1MB→7.9998）。**两侧都留**（已在文档内解决）。
C13 **974 个 .ifs 重写 vs 下载数据库**：.ifs 全部 LWT=2026-10-08 20:32:23；
    COD OL/IIPS/vodcache/download.db 仍是 2026-09-28。**两侧都留；原因 UNKNOWN**。
C14 **anchor 文档自我更正**（同 A2，S5 独立记录）。两侧都留。
```

### D 组：战斗 / 净码（S4）
```
D1 **NAT 探测尾部端口**：BATTLE_SERVER_PROTOCOL.md:66 说尾 7f 00 00 01 20 71 = 127.0.0.1:8305；
   battle_server.py:404 按字节匹配，codol_crypto.py:497 记 0x20 0x71 为 127.0.0.1:28960（小端）。
   **两侧都留**（文档按大端读了，功能无影响）。
D2 **10-06 会话 TX_GAMESTATE 为何为 0**：文档 §0/§3 归因于 ready/gamestateupdate 门控；
   同一次会话的日志写 "game state 文件: firingrange-gamestate.bin (缺)"，而 pump_gamestate 在文件缺失时直接返回。
   **两个原因同时成立，文档只讲了一个。两侧都留。**
D3 **"battle_srv.log 收包=0"**：GOLDEN-LOBBY-001.md:163 与 STAGE_REPORT_BATTLE.md:39 如此描述；
   同一文件里却有 155 包的完整握手。**两侧都留**（冻结陈述指冻结时刻的最新状态）。
D4 **推送是否总会断连**：BATTLE_SERVER_PROTOCOL §9.1/§9.12 = 9/9 立即关闭；
   10-07 10:34 那轮推送后客户端继续到 10:37:02 才关闭。**两侧都留；条件差异 UNKNOWN**。
D5 **playlist 路由**：文档 §8.11 说 playlist != 10 → firing_range；代码 lobby_server.py:614-617 用 is_pve 路由；
   但 10:34 日志显示 playlist=10 的请求被回以**靶场**对象（PvE 分支当时还不存在）。**两侧都留**（改前 vs 改后）。
D6 **selftest 步数**：文档 §2 说"10 步"却列 11；§7.5 说 12；battle_selftest.py 实现 **13**。**三者都留**，以文件为准。
D7 D3 的重复表述（STAGE_REPORT 与 BATTLE_SERVER_PROTOCOL 两处）。**都留**。
```

---

## §18 证据索引与产出物

### 18.1 本轮的产出物
```
DEV-REVIEW\MASTER-POST-LOBBY-FULL-HISTORY-001.md          ← 本总报告（主交付）
HISTORY_REFERENCE_ASSETS_TOOLING_20261008.md                  ← S5 子报告（资源/参考/工具，427 行）
REF_LOBBY_KIT\_BATTLE_ARCHAEOLOGY_20261005_20261008.md     ← S4 子报告（战斗/净码）
DEV-BOOKING\scripts\_020_index.py                        ← 文档索引工具
DEV-BOOKING\scripts\_020_postanchor.py                   ← anchor 后文档清单工具
DEV-BOOKING\scripts\_020_gist.py                         ← DEV-BOOKING 文档 gist 工具
DEV-BOOKING\_gist_tmp.md                                    ← 上述工具的产物（31 篇 gist）
```

### 18.2 交给接力者的三件"未解事件"
```
1) **M-28**：2026-10-08 20:32:23，COD OL\IIPS\IIPSDownload 下全部 974 个 .ifs 被整体重写
   （LWT=AT 一致，CT 保留自 2026-09-10）；同一秒沙箱写了空的 download.db；无日志点名。**机制未知。**
2) **M-23**：2026-10-07 15:43:11，marketplace-inventory.json / player-account.json / secure.result 被同时改写；
   仓库内**没有任何脚本会写 secure.result**。**写入者未知。**
3) **RB-7 残留**：当前 marketplace-catalog-merged.json(37834) 含 9 个"客户端低 Item"SKU，
   与 TAKEOVER §13.2 禁令冲突（SC C1）。**若再现"买到错东西"，优先查这里。**

### 18.3 关键证据文件（按领域）
```
Anchor / 大厅    HANDOFF_20261005_LOBBY_REACHED.md（162 行，含 §2.5 更正）
                 HANDOFF_20261005_LOBBY_BUGS.md（352 行）
                 REF_LOBBY_KIT\lobby_live.png、lobby_window.png、lobby_repro.png、lobby_allitems.png、popup_fatal_error.png
协议/UI          HANDOFF_20261006_LOBBY_MAP.md、CLIENT_OBJECT_SCHEMA.md、lobby_task_matrix.csv
商城             HANDOFF_20261006_{CATALOG_LAYOUT,CALLSIGN_CHANNEL,PURCHASE_FIX,BUY_MATRIX,REVERSE_SUMMARY,
                 MARKET_MANIFEST,MAIN,MERGED_CATALOG}.md
                 目录 JSON：marketplace-catalog{-client,-full,-merged}.json 及 .bak_*
                 mkt_assets\{sku_table_v2.csv, item_sku_arrays.csv, callsign_*.csv, mkt_assets_summary.md}
                 unknown_skus.txt（155/158 行）；check_run.py；_extract_sku_table_v2.py；_analyze_item_sku_arrays.py
Booking/PvE      DEV-BOOKING\BOOKING-CLIENT-CONTRACT-001.md、BOOKING_PROTOCOL_SPEC-001..004.md、BOOKING_STATE-001.md
                 BOOKING_RUNTIME_TRACE-001.md、BOOKING_RUNTIME_NETWORK-002.md、evidence\BOOKING_EVIDENCE-002.md
                 PUBLISHER_FAILURE_SPEC-001.md、PUBLISHER_FILE_RECOVERY-001/002.md
                 BOOKING-RESPONSE-{CHANNEL-003,DISPATCH-004,PARAMS-005,ACCEPTED-WORKER-006,CONNECT-PATH-007}.md
                 MVP-PVE-MATCH-ENTRY-009.md、SERVER-PVE-BOOKING-RESPONSE-010.md
                 PVE-BOOKING-DYNAMIC-VALIDATION-011/012.md、PVE-SENDERID-AB-ENDIAN-CONFIRMATION-013.md
                 CLIENT-BOOKING-{BATTLE-TRIGGER-014,LISTENER-BRIDGE-015,BATTLE-OBJECT-016}.md
                 PVE-{ACCEPTED-STATE-DYNAMIC-017,MATCHING-AB-FIELD-IDENTITY-018,MATCHING-AB-ALIGN-019}.md
Battle           REF_LOBBY_KIT\BATTLE_SERVER_PROTOCOL.md（41KB）、STAGE_REPORT_BATTLE.md、HANDOFF_20261007_BATTLE_SERVER.md
                 GOLDEN-LOBBY-001.md、_golden_hashes.json
                 battle_server.py、battle_selftest.py（13 步）、snapshot_diff.py、_idx84_decode.py、battle_srv.log
                 firingrange-gamestate.bin（259B）、firingrange-clientstats-last.bin（826B，已被覆盖）
参考/资源        CODOLServer\IW4X_CODOL_REUSE_REPORT.md、FF_LAYER1_DECRYPT_20260930.md、REVERSE_STATUS_20260930.md
                 _PLAINTEXT_PROJECT\README.md；_cleanout\mkt*\*.layer1.bin
运行时证据       accepted_state.txt（+ _019test / .test019_* / .baseline019_* / _run1）
                 lobby_srv.log 及 logs_before_pve_fix_20261007_104358 等 4 份备份
                 battle_srv.log 及 bak_012_20261008_150236 / .bak_017_20261008_180059 / .baseline019_* / .test019_*
                 n10_017*.txt、n10_019*.txt、runtime_net_001\booking_net.xml（81MB）、runtime_net_ch003\booking_ch003.xml（66MB）
备份             codol_crypto.py.bak_019_20261008_200724（42853B）、lobby_server.py.bak_019_20261008_200724（76428B）、
                 lobby_server.py.bak_010_20261008_145002
分析镜像         CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin
                 （10,899,456 B；VA = 0x00400000 + 文件偏移；可读 0x400000..0xE65000）
                 mem_linear_20261007_134406（10-07 全量线性转储）、mem_linear\r_259D0000_06400000.bin
客户端 EXE       COD OL\codoMP_client_shipRetail.exe（7,841,344 B）、codoMP_client_shipRetailBase.dll
```

---

## §19 一句话交接

```
**2026-10-05 16:36 第一次进入正式大厅之后，项目做完了七件大事：把大厅链路调到稳定（0x83 KDF、
keepalive、seq 纪律）、把 71/7 变成可用的诊断通道、修好购买解析并重建销售目录（37615→37834）、
恢复发行方文件让 6/14 真正发出、把 Booking 全链静态闭合到 0x632680、用 017/018/019 三个实验把
accepted 不可达的原因从"字段错"精确定位到"通道/marker"、并把战斗服做到可离线自证（selftest 13/13）。
同一时期也留下三处明确的失败与两处未解事件：商城 80/70 页格式始终未解（三次真机把角色锁死）、
BATTLE_TRIGGER_PATH 始终未定位（战斗服自 10-06 21:28 起再没接过真实客户端）、
ol-mod 源码全盘不存在（PvE booking 真实格式永久缺失）、
以及 10-07 15:43 的不明数据写入与 10-08 20:32 的 974 个 .ifs 整体重写。**
```

*（全文完。报告时间：2026-10-08；REPORT_STATUS = COMPLETE）*
```













