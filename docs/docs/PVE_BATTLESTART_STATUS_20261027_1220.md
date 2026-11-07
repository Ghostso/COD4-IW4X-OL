# 剧情模式「战斗开始」卡点 — 2026-10-27 12:20 现状

## 0. 本轮已解决的前提

本体 6 秒必崩的根因是 `COD OL\iips.ini` 里 `enable_iips=0`（沙箱是 1）。
改成 1 之后本体完整进大厅（模块 93、`5E8=1→3`、Auth `10→11`、31 个 service 应答）。
备份：`COD OL\iips.ini.bak_before_iips_enable_20261027`。

## 1. 卡点的客观现象（`ONCE_20261027_120832`）

```
12:09:46  11/13 createRoom            -> roomId=0x1122334455667788
12:09:46  21/5  findSessions          -> 动态选单房间 playlist=10 map=coop_training_mp_cargoship
12:09:46  6/14  mmbook                -> push 'mmbook accepted'
12:09:46  6/14  mmstart               -> 仅空应答
12:09:46  11/4  setRoomData (ready)   -> 回显 + 推 GAME_START_PAYLOAD(162B)
12:10:09  71/15 UNMAPPED              -> 空 ACK
12:10:39  <- keepalive                （之后只剩心跳）
```

- 客户端 TCP 会话**不断**（3074 一直 Established，心跳正常）
- 战斗服 UDP 28960 **零收包**
- 客户端**从不**向 28960 建连

用户观察补充：**大厅对话显示「离线」**。

## 2. mmstart 完整命令（客户端自己报的，无歧义）

```
mmstart sv_resetServer; 2486 1; 3265 1; 2489 0; 2574 0; 2500 0;
        g_gametype coop;  g_difficulty 0; ;
        map coop_training_mp_cargoship; 2654 M7-E8S6Client;
        roomChatChannelID 1234605616436508552;
```

`1234605616436508552` = `0x1122334455667788` = `11/4` 用的频道号，与 `11/13` 返回的
roomId **完全一致** ⇒ 频道号本身没问题，问题在**频道订阅的回执**。

## 3. 已排除的假设（都有实证）

| 假设 | 结论 | 证据 |
|---|---|---|
| ACE 内核驱动杀进程 | ✗ | 驱动一直是 Running，但崩溃时并不介入 |
| `.local` 里打补丁的 Base.dll | ✗ | 去掉 `.local` 后模块数 83→92（接近沙箱 93），仍 6 秒崩 |
| TAS 注入 | ✗ | `tas_off.flag` 一直在 |
| 缺地图资产 | ✗ | `main\coop_training_mp_cargoship.ff` 13.6MB 在位，IIPS 也在 12:13 补写资源 |
| `service=71` 是订阅状态机 | ✗ | `0xDB4C00` 一带全是 **TLog 日志模板**（`ChannelSubscriptionFail`、`CreateRoom`、`ChatMessageReport`…）。`71/3` 的 payload 是 `CreateRoom\|${TIMESTAMP_OFFSET(-5)}\|…` 事件串。**SERVICE71_CLIENT_REVERSE_20261024.md 的 `0x27DA/0x6C` 判据是把日志串误读成了状态码** |
| 战斗服地图不对 | ✗（但未实测） | `codol_world_init()` 只把 map_name 存成字符串，clipmap 恒为 `codol_static_boxes`；地图名不进网络包 ⇒ 换图**不会**改变客户端是否连 28960 |
| `127.0.0.1:10090` | ✗ | EXE 里 `10090` 只出现在 OpenSSL 曲线表和数字表里，不是配置端点 |

## 4. 真正的候选：`GAME_START_PAYLOAD` 是靶场常量

`codol_crypto.py:803-826` 自带警告（原文）：

> ⚠️ 2026-10-07: 这条 162B 是三方从 **firingrange** 抓到的常量。实机确认触发 + 推送都成功，
> 但 PvE coop 客户端仍停在"战斗开始"，战斗服 0 收包。
> 因此它**不是已验证的 coop 开局数据**。

离线解包结果吻合这个警告：

```
0A 01 10 00 00 00 00 00 00      08 <u16> ...  帧头
13 08 85 00 00 00 81 00 00 00    TLV 长度 0x85=133，内层 129
内层：02 04 00 00 00 A4 01 00 00 18 18 02 00 00 00 46 7D 09 D8 AF 02
      F8 07 F8 07 00 00  ×10 对          ← 2047 = onGround?2046:2047 的「永远在空中」
      E8 4B FA 9A 13 8B 17 40 00 00 00 18 ...
```

`F807`(=2047) 出现 10 次，正是快照里"恒在空中"的那个哨兵值 ⇒ 这**确实是靶场快照**，
不是 coop 开局数据。

## 5. 客户端侧的决策点（ActionScript 层，已定位）

```
0x0397BF92  dw_autoStartGame          → getDvarBool
0x0397BFAF  gotoPage PAGE_HIDDEN_ROOM_MATCH_START_MSG
0x0397BFD9  NOTE_START_GAME
0x0397C2B9  goGameCountingDown
0x0397C2CC  startMatchCountDown
0x0397C31D  dw_enterRoomCountingDown  → goRoomCountingDown
0x0397C376  dw_startGameCountingDown  → goGameCountingDown
0x0397C410  dw_matchmaking_intermission
0x0397C42C  Dvar_GetInt
```

⇒「战斗开始」= `MatchController` 的倒计时页；走完它需要
`dw_autoStartGame` / `dw_startGameCountingDown` 这几个 dvar。

`players\config_mp.cfg`（7.8KB）整体加密，里面读不到 dvar。
dvar 在内存里是**按编号**索引的（名字表 `0x00DDE834` 附近与 `2724/2804/2907/2909` 等数字交错）。

## 6. 下一步的三个可选方向

1. **补全 11/4 的频道回显语义** —— 让「大厅对话」不再显示离线。
   现状：`ready_push.on` 存在时已回显 + 推 game start，但用户界面仍显示离线。
   需要确认客户端判"在线"的具体回执字段。
2. **从真实抓包推导 coop 的 game-start 数据** —— 停服前正版进剧情只需 1~2 秒，
   数据一定来自服务端。可在 `docs/` 与历史 run 里搜是否留有当年抓包。
3. **在内存里直接读 dvar 当前值** —— 转储里按编号找 `dw_autoStartGame` 的值，
   看它是不是 0。若是 0，就要找谁负责下发它（可能正是 `6/14 mmstart` 的应答）。
