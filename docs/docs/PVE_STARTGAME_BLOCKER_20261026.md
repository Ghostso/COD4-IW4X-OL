# 剧情模式（PvE）开局卡点 — 2026-10-26 实机验证

## 实机现象（ONCE_20261026_233111）

点击剧情任务 → 客户端显示"战斗开始" → 一直转圈，战斗服 0 收包。

## 端口实证

客户端进程（PID 17112）打开的 UDP 端口：

```
22011, 50095, 50393, 50394, 50395, 50396, 51289, 55468, 61851, 62686
```

**没有一个连向 28960。** 战斗服日志：`TX_NAT_REPLY=0 KEY_EXCHANGE_OK=0 RX_CLIENT_GAME_HEADER=0`。

## 大厅侧：能到"战斗开始"的一切都已响

| 时间 | service/task | 内容 | 我们 |
|---|---|---|---|
| 23:32:34 | 6/14 | `mmstart sv_resetServer; ... map coop_training_mp_cargoship;` | 空 ACK |
| 23:32:34 | 11/4 | `setRoomData` batch=21（16B ready 批次） | 回显 + 推 game start |
| 23:32:34 | 11/4 | 推送 type=2 seq=67 (242B, game start) | ✅ 已发 |
| 23:32:39 | 71/3 | `CreateRoom\|${TIMESTAMP_OFFSET(-5)}\|...` | 空 ACK |
| 23:32:52 | 71/15 | 二进制 124B | 空 ACK |

## ★ 关键发现：71/3 的 CreateRoom 是 TLog，不是开局请求

客户端 EXE `0x6A0E28` 的格式串：

```
CreateRoom|%s|%llu|${CODOID(%llu)}|%s|%s
```

`${TIMESTAMP_OFFSET(-5)}` / `${CODOID(...)}` 是 **TLog 模板语法**（同区还有
`OnBoarding|...`、`ClanCreate|...`、`UserWarning|...` 等统计事件）。

⇒ **这条 CreateRoom 是统计上报，与开局无关。** 之前把它当成开局信号是误判。

## ★ 真正的开局协议：dwRoomMessage* 家族

EXE 里有 **48 个 `dwRoomMessage*` RTTI 类**（Demonware 房间消息），关键成员：

```
dwRoomMessageStartGame            ← 开局
dwRoomMessageStartGameFailed
dwRoomMessageStartCountingDown    ← 倒计时
dwRoomMessageReady
dwRoomMessageRoomStateUpdated
dwRoomMessageP2PInfo              ← 可能携带战斗服地址
dwRoomMessageJoinRequest / Join / Leave / ChangeTeam / Vote / Score ...
dwRoomImp / dwRoom / dwParty / dwPartyImp / dwRoomMatch / dwRoomMatchUber
```

**客户端等的是 `dwRoomMessageStartGame`（Demonware 房间消息），
而我们现在推的是大厅 11/4 的 `GAME_START_PAYLOAD`。**

这解释了为什么 push 都发成功、客户端却不连 28960 —— **协议层不对**。

## GAME_START_PAYLOAD 的来源问题（代码自证）

`codol_crypto.py:805-813` 的注释：

```
★★ 开局(game start)推送体 —— 逐字节照抄三方 CodolLocalLobbyServer.cs:1419-1430
   的 gameStartData(162 字节)
⚠️ 2026-10-07: 这条 162B 是三方从 firingrange 抓到的常量。
   实机确认 plain[11]==0x15 触发 + 推送都成功，但 PvE coop 客户端仍停在
   "战斗开始"，战斗服 0 收包。因此它**不是已验证的 coop 开局数据**
```

162 字节结构（手动分析）：

```
0-10    头: 0A 01 10 00 00 00 00 00 00 13 08
11-14   85 00 00 00      = 133 (长度?)
15-18   81 00 00 00      = 129
19-22   02 04 00 00      = 类型
23-26   A4 01 00 00      = 420  ← 疑似 map/gametype ID
27-30   18 18 02 00
35-36   D8 AF            = 0xAFD8
37+     F8 07 × 11       = 2040 (空槽哨兵) 重复 → 11 个玩家槽
```

## 相关 cvar（客户端内）

```
dw_autoStartGame
dw_startGameCountingDown
dw_lockLobbyCountingDown
dw_enterRoomCountingDown
dw_enterGameNextMapCountingDown
dw_roomJoin
```

开局流程由这些 cvar 控制倒计时，说明是"等待倒计时/条件满足"型流程。

## 阻塞

RTTI Complete Object Locator 在文件里搜不到（引用 TD RVA `0xE6F7E0` 零命中），
EXE 被 VMProtect 处理过，vtable/解析函数定位困难。

## 下一步方向

1. **定位 `dwRoomMessageStartGame` 的解析/构造代码**（需要先解决 RTTI 引用定位，
   或改用运行时内存转储）
2. **确认 dwRoomMessage 走哪条传输通道**：Demonware 房间消息通常走
   lsg（3074）的某个 service，而不是 11/4。需要找 service 号映射。
3. 若能拿到运行时内存转储（上次的 `LIVE_FULLMEM` 已被清理），
   可以直接在内存里找 `dwRoomMessageStartGame` 的 vtable。

相关：[[codol-demonware-layer]]、[[reference-authority-hierarchy]]
