# 战斗服零收包：根因定位（2026-10-28 第十四轮）

## 一、根因：`mmstart` 里没有 map

对比两种入口的 `mmstart` 原文：

**能连上 28960 的那轮**（`ONCE_20261026_220815`，PvE 剧情入口）：
```
mmstart sv_resetServer; 2486 0; 3265 18; 2489 0; 2574 0; 2500 0;
        g_gametype coop;  g_difficulty 1; ; map coop_train_mp_firingrange;2654 ;
        roomChatChannelID 0;
```
→ **带 `map coop_train_mp_firingrange` 和 `g_gametype coop`**
→ 战斗服立即收到 NAT/DTLS/getchallenge/connect

**当前所有轮次**（BOT 房间入口）：
```
mmstart sv_resetServer; 2486 1; 3265 6; 2489 1; 2574 2; playlist 37;
        start_map_rotate_once 4; roomChatChannelID 1234605616436508552;
```
→ **没有 map、没有 g_gametype**
→ 战斗服 0 收包

⇒ **客户端在没有确定目标地图时，不会去连战斗服。**
这是"进不了对局"的直接原因，与房间 UI 消息格式无关。

## 二、两个入口的 playlist 语义不同

| 入口 | findSessions 请求 | mmstart 携带 |
|---|---|---|
| PvE 剧情 | `playlist=10` | `map <具体地图>` + `g_gametype coop` |
| BOT 房间 | `playlist=50` | `playlist 37` + `start_map_rotate_once N` |

`playlist=50` / `playlist 37` **都不是官方 ID**（官方表 123 项里没有 37 和 50），
而是**排序后列表的下标**（`_PlaylistResolver.resolve()` 的兜底逻辑）：

```
下标 50 -> playlist 148 -> mp_raid / mp_village / mp_mountain / mp_nuked  (hp)
下标 37 -> playlist 123 -> mp_crash_tropical / mp_estate_tropical / ...   (sd)
```

**本地已解包的图只有 5 张**：
`coop_train_mp_firingrange`、`coop_training_mp_cargoship`、`mp_cargoship`、
`mp_firingrange`、`mp_raid`

⇒ `findSessions(50)` 回的 `mp_raid` **有**本地资源；
但 `mmstart` 的 `playlist 37` 解析出的是 SD 模式地图，**本地一张都没有**。

## 三、`mmbook` 之后客户端确实进了下一阶段

时序证据（`ONCE_20261028_224009`）：

```
[22:41:13] 6/14 payload 含 "mmbook 796 ..."
[22:41:13] -> push 'mmbook accepted'(20 B)
[22:41:13] 6/14 payload 含 "mmstart sv_resetServer; ..."
```

客户端收到 `mmbook accepted` 后**立即**发 `mmstart` —— 说明这一步是通的，
卡点在 `mmstart` 之后：客户端要服务端来决定地块，服务端没回应。

## 四、尚待确认

1. `mmstart` 里的 `playlist 37` 究竟是 playlist ID、下标、还是轮换序号？
   三种解释里只有"下标"能落到实际 playlist，但选出的图本地没有。
2. 客户端期待服务端用什么方式告知"这局打哪张图"？
   候选：`dwRoomMessageStartGame` 的字段（我们推了 109B 但内容未验证）、
   或 `mmstart` 之后的另一条命令。
3. 10-26 那轮之所以能连，是因为**客户端自己带了 map**，
   而那条路径（PvE 剧情）我们还没在 BOT 房间场景下复现。

## 五、结论

战斗服零收包**不是**网络层问题、不是端口问题、也不是 `mmbook accepted` 没发。
是**客户端拿不到目标地图，因此不发起连接**。

要让 BOT 对局跑起来，必须让客户端得到一张**本地已解包、且战斗服能加载**的地图。
本地唯一的 BOT 多人图是 `mp_raid`，而战斗服当前硬编码 `mp_firingrange`
（`CODOL_SERVER_319_20261021/src/main.c:64`）。

⇒ 下一步应当让 `findSessions` 与 `mmstart` 的应答都指向同一张本地可用图，
并让战斗服按该图加载。

## 六、工具

```
（本轮主要靠日志对比 + mp_playlists 解压解析，未新增脚本）
遍历 run_codol_001/runs/*/kit/lobby_srv.log 对比 findSessions / mmstart
zlib 解压 publisher_files/mp_playlists_shipRetail_1.0.0.info（112664 字节，123 个 playlist）
```
