# 02 — 全部历史问题台账（含已解决 / 已作废 / 证据不足）

> 目的：**避免重复调查**。本表把历史结论分成四类，让新 agent 一眼看出"哪些别再做了"。
> 计数口径：本表是"历史结论清单"，不是"当前问题数"——当前问题数见 `03_MASTER_UNRESOLVED_ISSUES.md`。

四类标记：

| 标记 | 含义 | 处理方式 |
|---|---|---|
| **CLOSED** | 有足够证据证明已解决，且验收条件满足 | 不要重做；如需引用，核对下面给出的证据 |
| **OBSOLETE** | 前提被推翻，问题不再成立 | 不要重做；不要引用其结论 |
| **WRONG** | 曾经是结论，但已被后续证据否证 | 不要重做；文中若再见此说法，标记为错误 |
| **UNVERIFIED** | 声称已解决，但只有离线/自测证据 | **必须重新验证**才能当作已解决 |

---

## 一、CLOSED — 已解决，别再重做

| # | 结论 | 证据 | 备注 |
|---|---|---|---|
| C1 | 本体 6 秒必崩的根因是 `iips.ini` 的 `enable_iips=0` | `docs/PVE_BATTLESTART_STATUS_20261027_1220.md` §0；改 1 后模块 83→93、Auth 10→11、31 个 service 应答 | 环境依赖未受管，见 ISSUE-0007 |
| C2 | ACE / `.local` / TAS 都不是崩溃原因 | 同上 §3 表：去掉 `.local` 后模块数 83→92 仍 6 秒崩；`tas_off.flag` 一直在 | — |
| C3 | 快照索引 run 编码必须固定 **4 位一组、步长 15** | `HANDOFF_20261025_BINARY_BISECT.md` §8；改回后 messageAck 0→4272、19022 条 usercmd、fwd/right 518/832、武器号 1156 | 10-23 的"7 位"修正方向反了 |
| C4 | `codol_battle_service_bind_world` 从未被调用是实体层全死的根因 | 同上 §16；一行接线后 damage=33、位移 89.1、trace fraction 0.292 | Phase 7 文档曾声称"已接线"，是**错的** |
| C5 | `11/13 createRoom` 的 memberCount 0→1 会让 dwRoomMatchUber 首次出现 | `docs/AB_MEMBERCOUNT_RESULT_20261027.md`；vtable 0x00DC795C + vtable+0x68=0x63C5E0 双校验 | 语义出处是 ol-mod，见 ISSUE-0015 |
| C6 | 71/3 的 `CreateRoom` 是 TLog 统计事件，不是开局请求 | `docs/PVE_BATTLESTART_STATUS_20261027_1220.md` §3；0xDB4C00 一带全是 TLog 日志模板 | — |
| C7 | `dwRoomMessage*` 的 RTTI 没被剥离，偏移是 `-9` 不是 `-8` | `docs/DWROOM_PROTOCOL_20261027.md`；49/49 解析成功 | 推翻了 `codol-memdump-and-rtti-limits` 里的旧判断 |
| C8 | 闸门 B（dvar 3291）与 0x63C5E0 属于两个不同的类，闸门 B 只是旁支 | `docs/GATE_B_INIT_PATH_20261027.md` §'重大更正' | 见 ISSUE-0014（OBSOLETE） |
| C9 | 训练图只有 333 个装饰 + 1 个 actor ⇒ "没有 BOT" 是地图设计 | `HANDOFF_20261025_BINARY_BISECT.md` §16.3 | 见 ISSUE-0068 |
| C10 | 房间上行不是位流（穷举 160 bit 偏移零命中） | `docs/ROOM_MSG_NOT_BITSTREAM_20261028.md` / `TYPE02_IS_TEXT_20261028.md` | 但下行**是**位流——两者不要混 |
| C11 | type 0x02 = `dwRoomMessageText`（聊天），不是通用分发 | `docs/TYPE02_IS_TEXT_20261028.md`：0x63495A → call 0x625940 → vtable 0x00DC7504 | — |
| C12 | 房间路由键 = roomId 的高低 32 位（不是 service/task） | `docs/ROOM_PUSH_ROUTE_KEY_SLOT_20261028.md`；表项 +0x10/+0x14 实测 | 信封布局仍未知，见 ISSUE-0011 |
| C13 | `ui_mp.ff` 是加密的（熵 7.95–8.00），SWF/GFX 签名全是假阳性 | `docs/UI_FF_ENCRYPTED_20261028.md` | 见 ISSUE-0046 |
| C14 | 按参照逐字节重写快照编码器会让本客户端卡住 | `HANDOFF_20261025_BINARY_BISECT.md` §15；两轮实机均卡 | 见 ISSUE-0026（OBSOLETE） |
| C15 | 服务端改位置推不动客户端（3 坐标 × 2 频率全部无效） | 同上 §13；字节级确认坐标上线 | 负面结论，见 ISSUE-0025 |
| C16 | 22/22 ctest 在 2026-10-26 22:07 全通过 | `build/Testing/Temporary/LastTest.log`：22 Passed / 0 Failed | 覆盖面有限，见 ISSUE-0005 |
| C17 | coop_train zone 里 27 个平面全是垂直面、没有地板 | `docs/CLIPMAP_EXTRACTION_20261026.md` | 这是数据事实，不是缺陷 |
| C18 | 本体 3095 文件 / 24.7 GB，沙箱残缺；实验必须在本体上跑 | `run_codol_001/run_frozen_chain_once.py` 注释（2026-10-27 用户决定） | — |

---

## 二、OBSOLETE — 前提不存在了，别再投入

| # | 曾经的问题 | 为何作废 | 出处 |
|---|---|---|---|
| O1 | "目标版本是 3.9.9.7" | 实际为 3.19.26.22 / 1649370；工作区里不存在 3.9.9.7 客户端 | `CODOL-TARGET-GAME-IDENTITY-008/TARGET_VERSION_VERDICT.md`（ISSUE-0051） |
| O2 | "闸门 B 是开局链的第二道闸门" | 两个类不同；即使打开 3291 也不会让 dwRoomMatchUber 出现 | `docs/GATE_B_INIT_PATH_20261027.md`（ISSUE-0014） |
| O3 | "service 71 是订阅状态机" | 是 TLog 日志模板 | `docs/PVE_BATTLESTART_STATUS_20261027_1220.md` §3（ISSUE-0019） |
| O4 | "FAT 分片是进图阻断点" | 索引编码修好后客户端消息永远达不到 1154 阈值，FAT 不触发 | `HANDOFF_20261025_BINARY_BISECT.md` §8.2（ISSUE-0065） |
| O5 | "快照尺寸 105 vs 103 是判据" | 两种都卡；尺寸不是判据 | 同上 §3 |
| O6 | "世界模型/clipmap 改动导致进不了图" | WORLDREVERT 退回 placeholder 后仍卡 | 同上 §3 |
| O7 | "transport 初始化改动导致回退" | 实际只加了 `--bind` 解析，run_all 不传该分支 | 同上 §3 |
| O8 | "房间消息走 Demonware 位流（上行）" | 上行不是位流 | `docs/ROOM_MSG_NOT_BITSTREAM_20261028.md`（ISSUE-0010 的一半） |
| O9 | "0x82E1458 是 type→类注册表，空则丢弃" | 四快照全空；0x634870 空时是跳过而非丢弃 | `docs/TYPE02_IS_TEXT_20261028.md`（ISSUE-0010） |
| O10 | "0x00DE07A4 读不到是 ASLR 漂移" | EXE DllCharacteristics=0x8100，ASLR 关闭；真因是 ACE 拦 RPM | `docs/PROBE_BLOCKED_BY_ACE_20261028.md` |
| O11 | "E22 的五个地址在 .data BSS 尾部" | VA/RVA 误用 | `E23_BSS_INITIALIZATION_AND_DISPATCH_RECOVERY_001`（ISSUE-0048） |
| O12 | "读 API IAT 槽 0x0CA84E8 落在未覆盖节区" | 该值是绝对 VA，RVA 在文件内 | `CODOL-BATTLE-SERVER-CLIENT-IMPORT-IDENTITY-045/08`（ISSUE-0048） |
| O13 | "0x87BE00 更像 ReadFile/重叠读" | 实为 `select`+`recv` | 045（hist_e #8） |
| O14 | "0x60E5B0 是协议状态机" | 是 `vsnprintf` | `E14_CROSS_PROJECT_PROTOCOL_AND_NETWORK_001`（hist_e #74） |
| O15 | "service 71/3 是频道订阅阻断点" | 71 是遥测 | `SERVICE71_CLIENT_REVERSE_20261024.md` §14.1（hist_combat #18） |
| O16 | "房间服务在 service 11" | 是 4/13 | 同上 §14.5（ISSUE-0073） |

---

## 三、WRONG — 曾经写进报告但被后续证据直接否证的结论

> 这一节的用途：如果在新文档里再看到这些说法，直接当作错误处理。

| # | 错误结论 | 正确结论 | 出处 |
|---|---|---|---|
| W1 | "Phase 7 closure 已经接线 `codol_battle_service_bind_world`" | 从未被调用，2026-10-25 才接线 | `INMATCH_COMPLETENESS_GAP_MATRIX_20261023.md` vs `HANDOFF_20261025 §16` |
| W2 | "索引 run 编码按表宽 7 位才对" | 4 位一组、步长 15 | `CODEC_SPEC_20261022.md` §8 / `BITORDER_6701D0` §5 vs §8 |
| W3 | "「权威实现恒写 2047」"（snapshot.c 旧注释） | 参照是 `OnGround?2046:2047` | `docs/SNAPSHOT_FIELD_DIFF_20261024.md` |
| W4 | "AS_SetReadyState 未实现 ⇒ 准备按钮无反应" | 不完整；房间 UI 不走 UiCpp；另有 dwRoomMatch::Init 未调用这条 | `docs/READY_BUTTON_ROOT_CAUSE_CLOSED_20261028.md §一` |
| W5 | "042/045 的 TDR/TQOS 是 CoD netfield/delta 解码器" | 是腾讯 TDR 诊断，非 netfield | `CODOL-BATTLE-SERVER-CLIENT-PARSER-SEMANTICS-046/09` |
| W6 | "0x3524F0 是接收环形缓冲" | 是发送/序列化暂存（出站） | `E13_RECV_RINGBUFFER_TRACE_001` |
| W7 | "E19：type1→size1, type2→size9" | 两者在 0x6A9978 合并，ebx 都是 9 | `E20_TYPE_BRANCH_CLOSURE_001` |
| W8 | "0x788133 与 0x6ABBC0 状态机同路径" | REFUTED | `E19` §4 |
| W9 | "GAME_START_PAYLOAD(162B) 是 coop 开局数据" | 是 firingrange 快照常量 | `docs/PVE_BATTLESTART_STATUS_20261027_1220.md §4` |
| W10 | "`mmstart` 只要发了 `mmbook accepted` 就能让客户端连上" | 10-26 成立，10-27 之后同样发了却无效 | `docs/ROOM_PUSH_SPEC_FIX_RUN_20261028.md §五` |
| W11 | "`player_origin.txt` 的 origin 列可用" | 全是 0.00 0.00 0.00，偏移猜错（angles 那列是对的） | `HANDOFF_20261025_BINARY_BISECT.md §9` |
| W12 | "出生点 (48,-572,-116) 是可信候选" | 它是 coop 图唯一设计出生点，但服务端推不动客户端；且它落在所有碰撞体之外 | 同上 §11/§13 |
| W13 | "服务端换图会改变客户端是否连 28960" | 不会；`--map` 只存字符串 | `docs/PVE_BATTLESTART_STATUS_20261027_1220.md §3` + 本次审计 ISSUE-0022 |

---

## 四、UNVERIFIED — "已解决"但只有离线/自测证据，**必须重新验证**

| # | 声称已解决 | 实际证据等级 | 需要什么才能算解决 |
|---|---|---|---|
| U1 | 战斗传输握手（NAT/DTLS/密钥交换）DONE | `simclient`：只对 `e2e_client.py` 验证过；官方客户端只在 10-26 的 8 轮里连上过 | 官方客户端抓包（ISSUE-0078） |
| U2 | Gamestate / configstring DONE | 字节往返一致（`impl`），客户端消费未证 | 客户端确在读的证据（ISSUE-0044） |
| U3 | Usercmd / 可靠命令 DONE | 向量 + 背包命令闭环（`impl`）；开火位从未出现 | 开火事件的官方证据（ISSUE-0055） |
| U4 | 实体段"客户端接受" | ack 速率不变（`official`），但"是否解析"未证、实体不可见 | 畸形对照（ISSUE-0024） |
| U5 | FAT 分片 | 离线 7/7，实机从未触发 | 触发现场（ISSUE-0065） |
| U6 | 世界伤害 / 碰撞闭合 | `probe_world_damage` 离线通过；但实时路径是距离公式不是 trace | 真实 trace（ISSUE-0030） |
| U7 | 模式状态机 DONE | 函数存在，`player_killed`/`respawn_due` 无调用者 | 一次完整对局链（ISSUE-0032） |
| U8 | 22/22 全绿 | 未覆盖 3 个探针与 e2e | 补注册（ISSUE-0005） |
| U9 | 035 模块 84/84 离线通过 | 自述"只覆盖已确认子集" | 官方客户端验证 |
| U10 | 冻结链基线完好 | 8/9（marketplace_store.py 不符） | 完成 migration（ISSUE-0001） |

---

## 五、跨报告矛盾对照表（结论随时间的演变）

| 议题 | 早期结论 | 后续证据 | 当前判断 |
|---|---|---|---|
| 客户端是否向战斗服发数据 | "不会发"（2026-10-13 前后） | 10-26 有 8 轮真实 UDP 流量 | 会发，但取决于 mmstart 形态 |
| GameState 是否送达 | "已成功发送" | 客户端仍停"Setting up game" | 发送已实现；消费未证 |
| 快照是否被接受 | "服务端持续发送" | messageAck 0→4272 | 已被接受（在能进图的那一版） |
| 进图能力 | "10-23 已闭合" | 10-23 二进制本身卡住 | 10-23 那批源码是回退源，10-25 修好 |
| 出生点 | "服务端发坐标即可" | 三坐标 × 两频率全无效 | 服务端推不动客户端 |
| 房间推送 | "位流（离线 5/5 通过）" | 上行零命中；上下行不同；type02 是 Text | 下行走位流，但整体仍无效 |
| 运行时取证 | "早期句柄可读（t+15.39s, 1630MB）" | 10-28 测 t+0.01s 即 err=5 | **矛盾未解**（ISSUE-0045） |
| 障碍归因 | "ACE 不是原因（err=5 是 ctypes 缺 argtypes）" | 10-28 拿到 ALL_ACCESS 仍 err=5 | ACE 拦截成立；早期窗口是例外 |
| 战斗服地图 | "换图不影响连接" | 确认；且服务端也不换碰撞 | 两条都成立（ISSUE-0022） |

---

## 六、被重复登记过的同一缺陷（避免计数虚高）

以下每一组在历史报告里以不同名字出现过，本审计**合并为一条**：

| 合并后 | 历史别名 |
|---|---|
| ISSUE-0020 战斗服零收包 | "客户端从不连 28960" / "battle server zero RX" / "战斗服 0 收包" / "NAT_REPLY=0" |
| ISSUE-0009 准备按钮 | "准备按钮点不动" / "ready button no response" / "no uplink on click" |
| ISSUE-0012 Init 未调用 | "MyEventHandler 零实例" / "dwRoomMatch::Init 从未执行" / "建房回调 0x63B500 永不触发" |
| ISSUE-0041 recv→reader 边 | "RECEIVE-LINK-050 未闭合" / "payload 是否被复制" / "A-02" |
| ISSUE-0045 ACE 拦截 | "RPM err=5" / "ACE blocks debug" / "probe failed" |
| ISSUE-0029 写死地面 | "z=-116 常数" / "codol_ground_z" / "没有地板" |

---

## 七、本表未覆盖的项

- `_LEARN_TESTOL_DELIVERY*` 的 431+ 份编号报告：内容是对外部交付包（TESTOL）的学习笔记，
  不直接构成我们项目的缺陷。仅汇总为 **ISSUE-0090**（1/769 哈希不符、缺 `inject_ayria.on`、
  deploy 只比大小），其余未逐篇审计。详见 `14_AUDIT_COVERAGE_AND_MISSING_SOURCES.md`。
- 启动/IIPS/TCLS 语料（86 条）中**与主线无关**的 76 条已归档在 `_work/hist_boot_lobby_map.md`，
  不进入主台账；进入主台账的是其中最影响判断的 14 条（ISSUE-0079…0092）。
- `REVERSE_ENGINEERING_COMPLETE.md`（387 KB）：按标题检索未发现战斗/快照相关章节，仅略读。
- `CODOL_2697_SERVER_STATIC_ANALYSIS_20261011`：2697 不是目标版本，只作血统参考。

---

## 八、补充：从三份原始扫描器汇入主台账的条目

| 主台账 Issue | 原始来源 |
|---|---|
| ISSUE-0053..0070 | `_work/hist_combat_snapshot.md`（战斗/快照，98 条中的去重子集） |
| ISSUE-0071..0078 | `_work/hist_e_series.md`（E 系列，77 条中的去重子集） |
| ISSUE-0079..0092 | `_work/hist_boot_lobby_map.md`（启动/大厅/地图，86 条中的去重子集） |

三份原始清单合计 261 条，去重与分类口径见 `14_AUDIT_COVERAGE_AND_MISSING_SOURCES.md §4.2.1`。
