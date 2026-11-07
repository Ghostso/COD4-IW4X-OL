# 11 — 历史成功/失败运行时间线（逐 run 独立重建）

> 每一条都是独立 run 目录的原始日志，**不拼接、不合并**。
> 标注：`[L]` = 真实日志证明；`[S]` = 源码推断；`[R]` = 历史报告声称；`[?]` = 无证据。

---

## R1 · ONCE_20261026_220815 —— 最后一次成功连接

| 项 | 值 |
|---|---|
| 日志 | `runs\ONCE_20261026_220815\kit\lobby_srv.log`（31,613 B，SHA `bf650058…`） |
| 战斗服日志 | `…\kit\_battle_out.txt`（64,012,556 B） |
| 启动根 | `run_codol_001\sandbox_ifs1_20260923`（`chain_pos.txt` 第 1 行）[L] |
| UI 入口 | PvE 剧情（由 mmstart 内容反推）[S] |

**时间线（全部 [L]）**

```
22:08:22  lobby 启动；靶场开关 session=True booking=True battle=True；战斗服已起 pid=3692
22:08:47  大厅连接建立；客户端 hello(28B)；0x81/0x82/0x83 握手；KDF 试解命中
22:08:47  S1 bootstrap 开始（71/4 起 35 个请求）
22:09:15  21/5 findSessions  playlist=10  → 回 mission session 280B maxPlayers=4
22:09:15  6/14 mmbook        → push 'mmbook accepted'(20B)
22:09:15  6/14 mmstart       → 仅空应答
              mmstart … 2486 0; 3265 18; 2489 0; 2574 0; 2500 0;
                       g_gametype coop; g_difficulty 1; ;
                       map coop_train_mp_firingrange;2654 ; roomChatChannelID 0;
22:09:15  ★ 已记住剧情地图 → coop_map.txt = coop_train_mp_firingrange
22:12:30  recv 异常 10054（客户端关闭，非崩溃）
```

**战斗服侧同一时刻**（`_battle_out.txt` 头部）[L]：
```
[battle] TX_NAT_REPLY 29B
[battle] TX_DTLS_INIT_ACK 38B
[battle] KEY_EXCHANGE_OK -> TX_DTLS_KEY_EXCHANGE_ACK 114B
[battle] RX_OOB cmd='getchallenge 0 "e7c8a98a6b4c2d0e"'
[battle] RX_OOB cmd='connect e7c8a98a6b4c2d0e "\name\TTctRThTNkNsaWVudA==\xuid\…\natType\3\rank\69\…"'
[battle] RX_OOB cmd='stats'
[battle] STATS_COMPLETE total=764
[battle] RX_OOB cmd='heartbeat' ×N
```

**关键事实**
- `roomChatChannelID 0` ⇒ 不在任何房间 [L]
- **无 `11/13`、无 `11/4`** [L]
- `mmstart` 带**具体地图名** [L]

---

## R2 · ONCE_20261026_233111 —— 第一次失败（紧邻成功之后 83 分钟）

| 项 | 值 |
|---|---|
| 日志 | `…\ONCE_20261026_233111\kit\lobby_srv.log`（29,382 B，`495b9501…`） |
| 启动根 | **同一沙箱**（`chain_sptest` 同批）[L] |

```
23:31:17  lobby 启动；靶场开关 session=True booking=True battle=True
23:32:34  S1 bootstrap（与 R1 前 35 条完全一致）[L]
23:32:34  11/13 createRoom → roomId=0x1122334455667788 secondId=0x42706516032933CB (37B)
23:32:34  21/5 findSessions playlist=10 → 280B maxPlayers=4（与 R1 相同）[L]
23:32:34  6/14 mmbook → push 'mmbook accepted'
23:32:34  6/14 mmstart → 仅空应答
              mmstart … 2486 1; 3265 1; 2489 0; … g_difficulty 0; ;
                       map coop_training_mp_cargoship;2654 M7-E8S6Client;
                       roomChatChannelID 1234605616436508552;
23:32:34  0B/4 setRoomData ×2（含 16B ready 批次）→ 已回显 + game start
```

**战斗服侧**：`_battle_out.txt` 仅 7 行初始化，**零 RX** [L]

**与 R1 的差异（同环境、同沙箱、83 分钟内）**

| 维度 | R1 | R2 |
|---|---|---|
| 11/13 createRoom | **无** | **有** |
| roomChatChannelID | `0` | `0x1122334455667788` |
| mmstart map | `coop_train_mp_firingrange` | `coop_training_mp_cargoship` |
| mmstart 序号段 | `2486 0; 3265 18;` | `2486 1; 3265 1;` |
| g_difficulty | `1` | `0` |
| 11/4 | 无 | **有** |
| 21/5 应答 | 280 B | **280 B（相同）** |

⚠️ 五个变量同时变化 ⇒ **不能把其中任何一个单独认定为根因**（任务书 §六 的要求）。

---

## R3 · ONCE_20261027_202345 —— 房间路径也走到了 mmstart

```
20:24:41  11/13 createRoom
20:24:41  21/5 findSessions playlist=10 → 280B maxPlayers=1
20:24:41  6/14 mmbook → accepted
20:24:41  6/14 mmstart  … 2486 1; 3265 1; … map coop_training_mp_cargoship;… ;
20:24:51  重复一遍（找房→预约→mmstart）
```

**关键**：这条 run 证明 **房间路径 B1 也能走到 mmstart** [L]。
所以 10-29 E1 没走到 mmstart **不是代码缺陷**。

---

## R4 · ONCE_20261028_224009 —— 首次出现可观测行为差异

```
22:41:03  21/5 findSessions playlist=50 → 261B
22:41:03  11/13 createRoom → 推送房间状态 x3 (106/130/54 B)
22:41:04  11/4 ready → 发 Ready + RoomStateUpdated(countdown)
22:41:06  11/4 ready → 再发一次
22:41:13  21/5 findSessions playlist=10 → 281B
22:41:13  6/14 mmbook → accepted
22:41:13  6/14 mmstart  playlist 37; start_map_rotate_once 4; roomChatChannelID 1234605616436508552;
              ★ mmstart 选择: gametype=? map=?     ← 解析失败
```

**这一轮首次出现 `★ mmstart 选择: gametype=? map=?`** [L]，
因为房间路径的 mmstart 里**没有 `map` 关键字**。

---

## R5 · ONCE_20261029_103202（E1）—— 未复刻成功条件

```
10:33:21  21/5 findSessions playlist=50 → 266B
10:33:21  11/13 createRoom
10:33:21..10:33:59  0B/4 setRoomData ×11（含 2 次 16B ready 批次）
          ★ 全程无 21/5(playlist=10)、无 6/14 mmbook、无 6/14 mmstart
10:36:02  recv 异常 10054
```

**E1 的形态 = 路径 B2（房间内没有走到"开始"）** [L]。

**为什么没走到**：用户授权的是"复刻 10-26 成功条件"，但
- E1 用的 kit 是 10-26 的旧 kit（`memberCount=0`、缺补丁 #5）；
- 且客户端进的是 **BOT 多选单（playlist=50）**，不是 PvE 剧情入口。

⇒ E1 本身**没有构成对路径 A 的检验**。这条结论修正了 `E1_RESULT.md` 的措辞。

---

## 6. 第一次分歧点在哪里

按时间顺序看：

```
R1（成功）  21/5(10) → mmbook → mmstart(map)          → 连战斗服
R2（失败）  11/13 → 21/5(10) → mmbook → mmstart(playlist) → 不连
```

**第一次分歧发生在 `11/13 createRoom` 是否出现**（R1 没有，R2 有），
它把客户端从"路径 A"推到了"路径 B"。

但注意 R3/R4/R5：**进入路径 B 之后仍可能走到 mmstart**，
所以"有没有 11/13"与"有没有 mmstart"是两件事。

**真正的分水岭是 mmstart 的内容**：
- 带 `map <具体地图>`（路径 A）→ 有过成功
- 带 `playlist 37`（路径 B）→ **从未观测到成功**

⚠️ 但这仍是**相关**，不是因果：路径 A 与路径 B 在"是否建房"上同样共线。

---

## 7. 四类事件标注汇总

| 事件 | 类别 |
|---|---|
| 握手 0x81/0x82/0x83 + KDF 试解命中 | [L] |
| S1 前 20 个请求的**集合**（顺序不恒定，仅 32/56 全序一致） | [L] |
| 21/5 应答 280 B（两轮相同） | [L] |
| 11/13 / 11/4 / 0B/4 的存在与次数 | [L] |
| mmstart 原文 | [L] |
| 战斗服 RX 全链路 | [L] |
| "用户点了 PvE 剧情入口" | [S]（由 mmstart 内容反推） |
| "用户点了房间内的开始" | [S] |
| "服务端主动推送 roomInfo" | [?] 无此证据 |
| "客户端在 mmstart 后获得地址" | [?] 实测地址在 21/5 应答里 |
