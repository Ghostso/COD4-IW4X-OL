# 145 · ServerCore / ClientSystem / GameState 三大头文件

## 一、范围

本报告完整学习 **3 个头文件**：

- `sv_main_mp.hpp`（1794 行，ServerCore 完整声明）
- `sv_client_mp.hpp`（884 行，ClientSlot / SvClientSystem）
- `sv_gamestate_mp.hpp`（728 行，configstring 全表 + SvGameState）

`server_mp` 进度推进到 **95/154**。

这三个头文件是整个战斗服的**骨架**：ServerCore 是每帧驱动，SvClientSystem 是每个客户端的状态机与线协议，SvGameState 是 configstring 索引全表。它们把前面 140 多份报告里的零部件串成一台机器。

## 二、帧率：为什么默认 100 ms 而不是 50 ms

`sv_main_mp.hpp` 里有一段完整论证，值得逐字记住：

- KisakCoD 注册 CoD4 默认 `sv_fps 20` = 50 ms，所以 50 是"正确的默认"；
- **但 50 除不尽这台主机**：out.exe 以 **30 Hz** 驱动插件（实测 hostGap 33.4 ms），而 `FixedFrameScheduler` **每次回调最多跑一帧**；50 ms 会落在回调 2、4、5、7… 上，即"三次回调两帧"，平均 20 Hz，实际间隔在 33/67 ms 之间交替；
- **实测零售**（`re/demo-re/01-container.md`，54,682 份快照）：97.4% 的快照 `serverTime` 步进 **100 ms**，规则均匀；
- 100 ms 正好是三次主机回调。

所以 `OLMOD_SV_FRAME_MS=100` 不是"更慢的服务器"，而是**零售自己的节拍，也是这台主机唯一能均匀交付的节拍**。范围 clamp 到 1..1000 ms。

另外 `SvZombieRoundGoal = 8`：五份零售 zm demo 的 `ui_hud_round_goal` 都是 8，第 9 回合与 `ui_hud_final_round "1"` 同帧宣布 ⇒ **终局 = goal + 1**，不是 goal。3.3.3.3 项目猜的 16 是错的。

## 三、Think 预算：零是默认

```text
SV_ClientThinkBudgetMilliseconds()  → 0（默认：排空整个队列）
SV_ChargeClientThinkTime(...)
```

注释明确：**CODOL 自己根本没有 think 预算**——`CG_PredictPlayerState 0x00464A90` 对每条待处理命令跑一次 Pmove，不做任何计数；Pmove `0x0041DCD0` 的 1000 ms clamp 和 66 ms 切片是它唯一的积压限制。

本项目的预算是**自己的**，理由是"原生世界所有权只存在于 beginFrame/endFrame 之内，一个客户端的积压不能饿死后续客户端或快照发布"。因为有 `PendingUserCmdCapacity = 32`，工作量天然有界。`OLMOD_SV_THINK_BUDGET_MS` 只用于诊断 A/B。

## 四、usercmd 容量：32，是 CODOL 自己的数

`PendingUserCmdCapacity = 32`，注释给了完整推导：

```text
CODREF(cl_write_packet): CODOL out.exe 1649370 CL_WritePacket 0x005B2C10 (RVA 0x1B2C10)
    count = cl.cmdNumber - outPackets[..].cmdNumber;
    if (count > 32) count = 32;
```

即 CODOL 客户端**单包最多带 32 条 usercmd**。原来用的是 Ghosts 的 8，会在超过 8 条同包到达时**静默丢弃玩家输入**。

更重要的是后半段实测：

> 50 ms 帧下队列峰值 7/8，**从未触顶**；100 ms 帧下 33% 的采样**正好在容量上**，且每一次都是丢失的 usercmd。**天花板才是缺陷，tick rate 不是。**

## 五、reliable command 容量：512，不是 256 也不是 128

`ServerReliableCommandCapacity = 512`，注释给了地址级证据：

```text
3.3.3.3  sub_46E3B0   and ebx,0FFh   shl ebx,0Ah   lea esi,[ebx+ecx+40154h]
out.exe  sub_4737E0   and ebx,1FFh   shl ebx,0Ah   lea esi,[ebx+ecx+80154h]
```

同样的 1024 字节槽、同样的 `push 3FFh` strncpy、同样的 `xor ecx,0D362501Fh` cookie，但 **512 项 vs 256 项**；序列字段与环基址都移动 0x40000，正好是多的 256 槽。

为什么必须精确：客户端用 `serverCommands[reliableAcknowledge & mask]` 给包做 XOR，**mask 错了两侧就从不同槽推导密钥**。而之前写的 **128 两边都不是**，还会让 staleness guard 在 128..511 的间隙返回空 key，是同一 XOR 的第二种失步方式。

## 六、client 超时：45 s 连接 / 15 s 活动

`SvClientTimeouts{ connectingMilliseconds=45000, activeMilliseconds=15000 }`。

原来是 80 s / 240 s。四分钟才能回收座位在崩溃重进时不可用；而 zhunt 加载崩溃落在 CONNECTING 状态，每次要赔 80 s。

理由：**生命周期一进入 Playing，静默就无歧义**——游戏里没有任何合法情形会 15 s 不发包。但 gamestate 确认甚至早期 move 包都可能在地图加载完成前到达，所以连接宽限一直保留到 Playing。大图（za_island、mp_battlecity、Wetwork）确实要几十秒。

可用 `OLMOD_CLIENT_TIMEOUT_MS` / `OLMOD_CONNECT_TIMEOUT_MS` 覆盖。

## 七、configstring 全表（1649370 版）

这张表是本项目最重要的地址级成果之一。注释说明：每个索引都比 3.3.3.3 重新推导过，且**表不是整体移动一个常量**：

| 区段 | 3.3.3.3 | 1649370 | 变化 |
|---|---:|---:|---|
| 固定低区（0/5/6/8/9/13/15/16、dvar 名值对 24..663） | — | — | **完全没动** |
| 玩家名块 | 1975 | 2452 | **+477** |
| 主体 | — | — | **+517** |
| 武器块 | 5443 / 900 项 | 5960 / **1700** 项 | +517 **且变大** |
| 其上全部 | — | — | **+5446** |

整张表是从一对函数读出来的：`CG_ConfigStringModified` A `0x57A300` ↔ C `0x60FD80`，加上延迟资产加载器 A `0x57A080` ↔ C `0x60F650`（它的显式 for 循环边界钉住了分发器只做测试的区间）。

### 7.1 关键索引

| 索引 | 含义 | 备注 |
|---:|---|---|
| 0 | serverinfo | 280 字节 fixture 的正文 |
| 1 | systeminfo | |
| 2 | gamename = `"cod"` | |
| 13 | 雾（11 个 token，首项是开始时间） | 零售值 `791 0.000113538 166 173 150 1 0 0 0.5 70 90` |
| **15** | **比赛结束时间（绝对毫秒）** | HUD 倒计时的**唯一**驱动 |
| 16 | 地图中心 | |
| 23 | **`\winner\-2` / `\winner\-1`** | allies→-2、axis→-1 |
| 463/464/465 | ui_scorelimit / ui_timelimit / ui_halftime | 只喂菜单文字，**不驱动时钟** |
| 479 | 比赛判定时发一次 `d 479 1` | **索引和值实测，名字未取证** |
| 792 | objective marker | podium 时清空 |
| 856..951 | **hint string 带（96 宽）** | 服务端从 **槽 7** 开始分配 |
| 1413..1585 | obituary 本地化名带（173 项） | 本服一条都没发 |
| 2452..2469 | 玩家名（18 项） | |
| 2554 | northYaw | |
| 2555 | minimap | |
| 2557..2562 | 六个 vision set | 值格式 `"<name>" <blendMs>` |
| 2568..3591 | 模型（1024） | |
| 3624..4135 | 音效别名（512） | |
| 4136..4535 | 特效（400） | |
| 4808..4871 | 脚本菜单（64） | |
| 4872..5895 | 服务端材质（1024） | |
| 5960..7659 | 武器（**1700**） | |
| 7669..11764 | 动画（4096） | |
| 11861 | timescale `"%i %i %g %g"` | +5446 |
| 12246 | weaponCount | 原 6800，**不是** +608 |

### 7.2 configstring 15 的机制（最重要的一条）

```text
CG_ConfigStringModified sub_C1A300 case 0xF → sub_C19830 = atoi(cs15) 存到 cg+0xEC
消费者 sub_C121C0:
    seconds = (cg[0xEC] - *(DWORD*)(cgs[0x357C] + 13612)) / 1000
    +13612 = 当前服务器时间
```

⇒ **cs15 是绝对结束时刻，不是时长也不是开始时刻**。没有它 HUD 就没有结束时间、没有倒计时。

### 7.3 hint string 带的四条独立证据

1. `sub_45A720`：`mov esi,[edi+0xC71E4]; add esi,0x358; call CL_GetConfigString` —— 客户端就是 `+856` 且不加别的；
2. 武器定义加载器 `sub_4E8490` 通过通用分配器 `sub_4EC5D0` 注册武器自己的 hint，参数 `base=0x358, max=0x60`；
3. 带描述符表 `out.exe 0xDA9808`（12 字节 `{start,count,flag}`），条目 14 = `{856, 96}`，而本头文件已声明的**每一个**带（模型 2568/1024、音效 3624/512、特效 4136/400、材质 4872/1024、脚本菜单 4808/64、武器 5960/1700、dvar 名 24/320、dvar 值 344/320）都在同一张表里逐项对上；
4. 零售 zm demo 用的是 863..884，第一个服务端写的在 863（相对 7），7-31 那份在门和碎片上发布相对 3/4/5/6。

⇒ **服务端从相对 7 开始分配**，0..6 由别的东西填。

无提示时 `playerState.cursorHintString = -1`（不是 0 —— 0 是 cs 856 这个真实槽；客户端自己的淡出路径 `sub_45BA10 @0x45BACC` 就写 `0xFFFFFFFF`）。

### 7.4 音效别名的两个带

这是最容易错的一处：

- **n < 512**：`p n` 播放 configstring `3624+n`，这是**地图的**别名表（512 项），**动态分配**，所以索引 15 每局都可能是不同声音；
- **n ≥ 512**：客户端**自己的常量字符串表**（CCS type 5），**没有任何服务端写过它**；`n-512` 索引进已加载 zone 的 `ncs_snd_*` 块拼接（按加载顺序）。**服务端不需要任何 configstring 或 precache**。

只有三个 zone 贡献 `ncs_snd` 块：`localized_common_mp`（1537 项）、`common_gametype_mp`（99 项）、关卡自己那一小块 ⇒ 整个播报带**按 build 固定**而非按局变化。前 392 项都是 `uk_1mc_*`（1MC = 舰载广播系统）。

base=512 是**解出来的不是断言的**：`Tools/olfinal/name-announcers.py` 用十份来自两份零售 dm demo 的锚点试遍所有 base，只有一个存活，且与从头文件另一侧读出的 `SoundAliasConstantStringBase = 0x200` 一致。五个锚点跨块边界，所以加载顺序错了会失败而不是轻微偏移：

| 参数 | 名字 | 证据 |
|---:|---|---|
| 1414 | `uk_1mc_free_for_all` | 两份 demo，比赛第一条播报，且 gametype 就是 dm |
| 2131 | `uk_victory_music` | demo 1 比赛结束那一帧，且那份录制者先结束 |
| 2128 | `uk_defeat_music` | demo 2 最后一条命令，且那份录制者输了 |
| 1620 | `uk_1mc_winning_fight` | demo 1 0:58.9 |
| 1494 | `uk_1mc_losing_fight` | demo 2 92600 |
| 1277 | `uk_1mc_achieve_uav` | demo 2 两次，各在授权帧前 3.0 s |
| 1605 | `uk_1mc_use_uav` | demo 2 两次，各在使用帧后 3.0 s |

**唯一的猜测**：`SvAnnouncerWinningMusic = 2132`（`uk_winning_music`），因为两份 demo 都只产生了败北音乐，赢家音乐无捕获；2132 是已测四条（2128 败/2129 输/2130 出生/2131 胜）的**块 2 邻居**，按对称选，注释明说是"按对称选而非实测"。

低带的三个（106/107/108）是**自注册别名**：`ab_1mc_lead_taken_01`、`uk_1mc_lead_lost_01`、`uk_1mc_respawn_in_base_01`。

`SvAnnouncerTimesUp = 1577` 有一条反直觉的实测：零售在**正好剩 30.0 s**时播的是 `uk_1mc_timesup`，**不是**五个条目之前的 `uk_1mc_thirty_seconds`（1572）。

### 7.5 低带别名槽的踩坑史（很有价值）

注释记录了三次失败的索引选择：

1. **零售自己的 11/15/29 在本服是错的** —— 客户端别名表是**地图拥有的**，mp_rust_long 加载后 1..24 被地图环境音填满，11 是 `emt_insects_desert_05`、15 是 `emt_metal_rattle_squeak`；
2. **在客户端还在加载时覆写活条目**（2026-08-23 05:17）让两个客户端都崩在 "unable to join game session"：服务端记了一个两字节 netchan 包头，然后两个客户端再也没说过话。单独禁用此项即恢复 clients=2 active=2；
3. **100..102 也是错的**，方向相反——那些索引空闲但**在已初始化带之外**，客户端每次 `p` 都播不同声音。

机制原因：`p <n>` → `sub_452770` → `sub_514880` 读每个 configstring 的**类型字节** `byte_77D8250[cs]`，**只有为 21 且字符串非空**才返回别名串；否则落进 `sub_661C50/sub_661F00` 返回完全不同的东西。

现在的选择：**刀CS 改成 100/101/102/103**，注释说原先的 25/26/27/28 与零售 `mine_betty_spin` / `grenade_explode_metal` / `F_breathing_better` / `bullet_impact_headshot_2` 冲突。

### 7.6 splash 声音的归属用**比率**判定

这条方法论值得记住：300 ms 窗口下任何声音都像是与任何东西共现，所以改用比率：

| alias | 播放数 | 与 splash 同帧 | 无 splash |
|---|---:|---:|---:|
| `mp_last_stand` | 18 | **18** | **0** |
| `mp_headshot` | 4 | 4 | 0 |
| `bullet_impact_headshot_2` | 4 | 4 | 0 |
| `mp_hit_alert` | 84 | 13 | 71 |
| `mp_hit_kill` | 28 | 14 | 14 |

一场比赛有 20 次 `w 0` splash，`mp_last_stand` 命中其中 18 次且**从未单独出现**。只与横幅一起播的声音就是横幅的声音。

### 7.7 黄金 fixture：280 字节，只有一份

`SvGameStateFixtureBytes` 是 `SV_WriteGameState` 对 `mp_crash` / `tdm` 的输出，**两处**（ServerCoreTests 黄金 + `EngineBindings::bind()` 的 message_bindings 阶段）校验同一数组。

它曾经是**两份字面拷贝，并漂移过两次**：

1. `ServerCommandEof` 从 3.3.3.3 的 6 改成 5；
2. 六个 vision configstring —— 测试与写入器都更新了，`bind()` 没更新 ⇒ 下次启动 `bind()` 在 stage=message_bindings 失败，整个 dedicated 起不来。

现在 187 → 280 字节（为零售实测的十个 serverinfo 键重新生成），而且**用 diff 验证**：与旧 fixture 共享 27 字节相同前缀、129 字节相同后缀，唯一不同的区域就是 serverinfo 值本身。`bind()` 用 512 字节缓冲就是因为 256 在 280 时溢出。

## 八、ServerCore：把全部子系统连起来

### 8.1 战场/比赛结构

- `SvMatchStatus`：configured/completed/endReason/winner/**winnerClientNum**/startServerTime/**prematchClockSwitched**/elapsed/rules；
  - `winnerClientNum` 存在的原因：**FFA 没有获胜队伍**，每个玩家都无队，所以结果用槽位而非队伍表达；
  - `prematchClockSwitched`：prematch 倒计时**一次性切换**标记——gamestate 先把 cs15 指向"开打时刻"，到点由 per-frame 切成"比赛结束时间"。**必须只切一次**，因为每次 `SV_SetConfigString` 都会发一个差量。
- `SvSdRoundStatus` / `SvSdBombStatus` / `SvSdEliminationState`：SD 的回合、炸弹七阶段（Inactive/Available/Carried/Dropped/Planted/Defused/Exploded）、队伍存活数。
- `SvSdBombRules{plant=5000, defuse=5000, bomb=45000}` 带 TODO：**这些是 IW4/Ghosts 共享默认值**，CODOL 的 match-rules 资产未恢复。
- `SvMatchEndReason`：ScoreLimit / TimeLimit / WinLimit / RoundLimit / TeamEliminated。
- `SvSdRoundEndReason`：AttackersEliminated / DefendersEliminated / SimultaneousElimination / BombDefused / BombExploded / TimeLimit。

### 8.2 播报队列（不是时间表）

这一段是**方法论纠正**，值得单独记住：

```text
CODREF: Black Ops mod tools, raw/maps/mp/gametypes/_globallogic_audio.gsc
        playLeaderDialogOnPlayer —— 播完 wait(3.0) 再播下一条
```

⇒ 同一客户端上**任何两条播报间隔 ≥ 3 s**（`SvAnnouncerDialogSpacingMs = 3000`）；第二条**跟在第一条后面而非覆盖它**。

这**推翻了一个被记为"无法解释"的常量**：demo 里 `on_your_own` 在 demo 1 里跟开场播报差 3.0 s、demo 2 里差 12.5 s，此前被记成"不是固定偏移，选它的东西是别的"。**实际两者都是出生时入队，队列以 3 s 排空**；demo 2 的间隔只是队列更长。**"时间表"是错的模型，它生成了一个没有意义的常量。**

其他两个常量：

- `SvAnnouncerTimesUpRemainingMs = 30000`（dm demo 1 精确到帧）；
- `SvAnnouncerLeadChangeCooldownMs = 5000`，来源 `_globallogic_score.gsc onTeamScore: getTime() - level.lastStatusTime > 5000`，比此前凭空的 30 s **短六倍**。注释同时声明：那段是**队伍路径**，Black Ops 根本没有 FFA 领先播报；CODOL 加了（两份 dm demo 都有），所以 CODOL 自己的下限**未实测**。

`SvAnnouncerClientDialog{queue, statusSlot, nextPlayServerTime}`：`statusSlot` 使新领先播报**替换**待播的旧领先播报，所以没人会听到"你要赢了"紧跟"你要输了"。

### 8.3 结算与领奖台

- `SvDmOutcomeDelayMilliseconds = 1100`、`SvDmOutcomeDurationMilliseconds = 10000`（实测：outcomeNotify 在判定后 1100 ms 出现，`reset_outcome` 在 +11100 摧毁）；
- `PodiumBaseModelName = "tag_origin"` —— 三具零售 dm demo 人偶的 modelIndex 都是 **121**，而 121 在本 build 的模型索引空间里是 `tag_origin`，**一个空模型**。角色来自字段 49（podiumClient）与该 client 的 clientInfo，**不是**来自 base；
- 四条本地化索引：matchBonus=365，placement={339, 416, 434}，defeat=326、tie=367、scoreLimit=413、timeLimit=435、victory=442。
- 收尾时间表（全部 boolean 一次性标记）：`outroScreenAsked`（`u 10` @ +11100）、`podiumScreenAsked`（`q 19` @ +17400）、`outroKillCamCleared`（+16900，与首个 `I 17433 0 0` 同帧）、`outroSlowMotionStarted/Ended`（+14000/+15500）、`outroPodiumStateAsked`（+17000 帧：`s ui_match_complete "1"`、`> 161`、`s 2972 "1"`、marker 清空、雾起始时间归零）、`outroFinalScoresAsked`（`r 19` @ +31500）。

### 8.4 命中/击杀反馈的精确数值

零售 dm demo 里解出两个完整元素：

```text
x=-12 y=-12 w=24 h=48 align=0x22 target=2047
    color=alpha0 fromColor=alpha31 fadeTime=1000            ← 命中标记
type=2 y=-50 value=50 align=0x22 alignOrg=5 label=397
    fontScale=0.9 fromFontScale=3.0 scaleTime=200
    color=alpha0 fromColor=alpha27 fadeTime=750             ← 得分弹出
```

`SvScoreFeedbackLabel = 397` 有一段很长的自我纠正：原来是 **524**，理由写的是"397 属于 OLfinal 表、在这里会打出别的东西"，然后从 3.3.3.3 活客户端的本地化 configstring 里取了 524。**两半推理都对，只有"这里是哪个 build"错了**——§109 已确立那份 demo **就是本 build**（四个 configstring 索引与 out.exe 一致、十六个 precache 名逐字存在于本安装的 zone、SVC_EOF 是 5 不是 6）。所以 397 是 OLfinal 索引用在 OLfinal 客户端上，524 是 3.3.3.3 索引用在 OLfinal 客户端上——**正是那段注释本想避免的错误，只是反方向犯了**。

颜色也是逐字节测的：`writeHudColor` 依次写 `value&0xFF`、`>>8`、`>>16`，零售给它三个颜色字段都写 `0x29, 0xA6, 0xFF` ⇒ 线上字节来自 `0x__FFA629`。**复现字节顺序就是全部工作**——哪个字节被渲染器当红，不是这里要决定的。

得分弹出的三段缩放（零售）：

```text
t+0     fontScale 3.0, fromFontScale 0.9, scaleTime 100   生长
t+100   fromFontScale 3.0                 scaleTime 200   平在 3.0
t+300   fontScale 0.9, fromFontScale 3.0, scaleTime 172   回落
t+1000  alpha 27 -> 0                     fadeTime 750    淡出
```

**前两个缩放窗口并不相接**——第三次更新复用第二窗口的起始时间，所以发出时窗口已经过去，数字平在 3.0 然后跳。本项目去掉平段，把收缩窗口起始点正好放在生长窗口结束处，两个时长都保留零售值，因此缩放连续（`sub_BB4B70` 在同一瞬完成 3.0 的生长并开始 3.0 的回落；服务端帧 50 ms、生长 100 ms，边界正好落在帧上）。

`SvScoreFeedbackSort = 10000.0f`（描述符 21 是 `sub_BB5F60` 的 qsort 键，零售给它正好 10000）。

FFA 击杀得分 **50** 而不是 100：本服 dm 在 serverTime 0 设 `ui_DMKillScore "50"`，得分弹出自己的 value 字段读 50，且 `ui_DMKillScore` 不出现在任何 cha/war/dom demo 里。

### 8.5 客户端 UI 生命状态机（SvUiClientLife）

这个结构记录了**大量实测踩坑**：

- `connected` / `seen` / `alive` / `everAlive`：`spawnSequence` 在首次出生后**不再变化**，所以用不了；`seen` 单独也区分不出首次出生与重生（客户端在变成 Active 后一帧才变 alive 时走的是 alive 边而不是 first-sight 分支，于是首次出生被读成重生）；
- `pmFlagsLogged/Valid`：**纯只读取证**——先拿到"开局/复活后 pm_flags 到底取什么值"，再决定出生保护怎么实现。`codol_bot.c:618-619` 说 `PMF_FROZEN(0x800)` 在零售里就是 spawn protection 用的位，但本服**从未置过**，也没有任何一帧实测值 ⇒ 必须先取证；
- `prematchUntil` / `prematchTickSecond` / `prematchStageTwoAt` / `prematchStage`：零售 prematch 的**时长**来自 tweakable（`level.prematchPeriod = getTweakableValue("game","graceperiod")`），而 `:412/426` 是 `if (prematchPeriod > 0) 倒计时 else matchStartTimerSkip()` ⇒ **本服只发了状态词 `d 510 prematch`、没给时长 ⇒ 客户端当场 skip**，所以只听到 `p 52` 一声滴就结束。修法是服务端自己保持 N 秒，期间每秒重发状态词并滴一声；
- `prematchVisionStage`：两个 vision 转换（stage two 的 mpIntro→map、结尾的地图淡出）各发一次；
- `spyPhase` / `spyPhaseUntil`：demo 实测一回合节拍 `prematch → pickup_weapon → assign_role → end`；
- `spyRoundEndsAt` / `spyRoundNumber`：零售 spy 每局 **7 回合**（`s scr_spy_roundlimit "7"`）；
- `killCamAt` / `killCamActive` / `deathViewUntil`：killcam 在**死亡边**armed、**1500 ms 后**触发，且只在玩家那时**仍然死亡**才发（零售七次 killcam 全部正好落在死亡+1500 ms，十七次无 killcam 的死亡正是重生簇在同一瞬发出的那些）。

`SvDeathViewMilliseconds = 1500` 有一段两次修正的注释：先是 2000（操作员要求），改成 1200（cha.lua 在 3000 ms 请求重生，而 killcam 在 +1500 armed，更长的尸体视角会吞掉 killcam），最后一版是 **1500**（`_damage.gsc:857-869` 的 `wait(0.25)+wait(0.25)+wait(1.0)` 之后才 `death_delay_finished`，killcam 只在之后开始；零售死亡簇的 `u 10` → `i 0 0 0 1` 间隔就是尸体视角）。

### 8.6 其他重要的自有状态

- `zmZonesMutex_` **独立于 `mutex_`**，理由写得很清楚：`loadGameplayScript` 持 `mutex_` 执行 gametype 脚本，脚本调用 zm zone builtin 读这个模型，于是同一线程**重锁一个非递归 mutex 而死锁**，日志在 "map triggers" 与 "gameplay script loaded" 之间直接停住（2026-09-01 实测）。顺序是单向的（zone 读从不取 `mutex_`），所以没有环。**不要合并回 `mutex_`。**
- `perkSlotsSent_`：实测零售 cha demo 里 `s perkSlot_*` **0 条**，本服每局 12..336 条。客户端 exe 里确实有 `perkSlot_%d`（0x6ca3d8），但只在**换装**时需要重发；`PerkLife` 每死重建 ⇒ 每死重发 6 条。现在按"该 client 上次真正发出的 6 元组"去重。
- `lastCharacterCustomizations_` 按 **XUID** 键：provider 每帧跑、答案不保留，一帧答不出就会把该 client 从快照 clientInfos 里掉出去，然后 `writeClientInfos` 会叫所有观察者**移除**一个它已经有的 clientInfo ⇒ 那个玩家 modelIndex 为 0 ⇒ 没人看得见他。按 XUID 键使复用的槽位不能继承前一个占用者的角色。
- `SvClientThinkFailureStage` / `SV_ShouldDiscardRejectedUserCmd`：思考失败阶段决定是否丢弃 usercmd。

### 8.7 bot 接口

`createBotClient(xuid, name, selectedLoadout, loadout, requestedTeam)`：

- 保留一个空槽；
- **先**在该槽自己的 `loadoutSequence` 下预填 `resolvedLoadouts_`（这样 `loadoutProvider_` 这个 profile getter 永远不会为没有 profile 的客户端被调用）；
- 再以 Active/Playing 接纳，让帧循环的单一接纳测试（`sv_main_mp.cpp:8401-8403`）捡起它；
- team 与 character faction 从第一个 Active 非 bot 槽继承；**若调用方给了队伍，faction 设为它的对侧**——这是 J4 实测出的、bot 与主机能互相伤害所必需的关系。

`nonBotTeamCounts()` 返回按 SvTeam 索引的**非 bot** 计数：没有它每个 bot 都继承主机队伍，比赛永远到不了 6v6。

### 8.8 hint 字符串分配器

`registerHintString(text)` 返回 configstring 带 856 的**相对**索引；形状与客户端自己的分配器 `sub_4EC5D0` 一致（从低端扫描、已存在则复用、否则取第一个空位）；带满返回 nullopt（**96 宽，第 97 个是调用方 bug，不是要环绕的东西**）。

`driveCursorHints` 只对 **`zombie_door`** 出提示，理由写得很好：

> 出厂表带 zm_factory_sh 的 54 个 `trigger_use`（特权机、神秘箱、弹药箱、传送器），而每一个对应的玩法都还不存在。**提供"打开一个本服务器打不开的东西"的提示，比没有提示更糟。**

## 九、SvClientSystem：客户端状态机与线协议

### 9.1 ClientState 四态

`Free → Connected → ClientLoading → Active`。

`ClientSlot` 里最值得记的几条：

- `isBot`：服务端自建、无 netchan peer ⇒ 豁免静默清扫，usercmd 来自 `queuePendingUserCmd` 而不是包入口。**其余完全一样**（接纳、loadout 查找、出生请求走同一路径）；
- `newestFlaggedSnapshotMessage`：**关键**——out.exe 把带标志帧的实体存在 `dword_C89E050`，一个**没有帧号的平坦数组**，`CL_ParseSnapshot` 在每一帧带标志时把游标 `dword_C89E04C` 归零（`0x00472223`）。所以那个数组正好只持**一代**：客户端解析过的**最新**带标志帧。`sub_470E90 @0x00470e97` 在基线帧 snapFlags 带 bit 8 时从它读实体基线行，**只按列表位置索引**。`baselineCacheInitializationMessage` 答不了这个（客户端一确认它就重置，而那正是选择需要的时刻），所以用这个单调字段；
- `snapshotHistory` 用 `shared_ptr<const SvSnapshotFrame>` 共享不可变聚合，而不是每个连接客户端深拷贝一份实体/client/glass 向量；
- `reliableKeyComplaints`：有界，前几次带诊断信息，之后永远同一行。

### 9.2 快照组装失败枚举

`WorldFrameUnavailable / SnapshotBuilderUnavailable / DuplicateServerTime / SnapshotBuilderEmpty / NetchanTransmitEmpty`。

### 9.3 计分列的分工

`SvClientScore{score, deaths, kills, assists, objectives, downs, revives, headshots, killstreak, xp, gp}`。

注释反复强调一条区分：

- `addClientDeaths` / `addClientAssists` / `addClientObjectives` / `addClientGp`：**只是记分板列**，不喂 `evaluateMatchLimits`，脚本不给它们发；
- `addKillForClient`：**限制计数器**，读它的限制；不能是显示得分。

FFA 的排序规则：`bestClientKills()` 取**击杀数**（不是得分——一次击杀给显示分而配发限制是 30，用得分比会在第一次击杀就结束比赛），并列时先比**更少死亡**再比**更低槽位**。`topClientsByKills(count)` 用同一规则，所以限制、结果、领奖台三者永不矛盾。

### 9.4 计分板压缩

`scoreboardRosterFingerprint_` / `scoreboardMatchFingerprint_` 按**接收客户端**分别记 roster（userIds）与比赛级字段（round/limit）。未变则不发对应 run 段，使一次普通比分更新从 1185 B 降到 ~1029 B 且不再分两条命令（客户端一次装载一次重建）。**队分不进指纹**——它每个击杀都在变。

## 十、关键结论

1. **所有"容量/索引/位宽"都必须从本 build 自己读**：usercmd 32（不是 8）、reliable 512（不是 256 也不是 128）、武器索引 11 位、configstring 区段逐个偏移。
2. **configstring 15 是绝对结束时刻**，是倒计时的唯一驱动；463/464 只喂菜单文字。
3. `p <n>` 有**两个带**，低带是地图拥有的、高带是客户端常量表；把高带索引写进低带是"每次播不同声音"的根因。
4. 播报是**队列不是时间表**——这个模型纠正消解了一个被记为"无法解释"的常量。
5. 若干注释是**自我纠正的化石**，每条都对应一次真实的翻车：1975 字节扫描三次全错、524 vs 397 的 build 误判、低带别名 11/15/29 与 100..102 的两次相反错误、fixture 两份拷贝漂移两次。
6. 死锁、掉角色、卡 prematch 这类"看起来像客户端 bug"的现象，在本项目里多次证明是服务端自己的一行状态问题。

## 十一、未闭合点

- `SvSdBombRules` 的 5000/5000/45000 是 IW4/Ghosts 共享默认，CODOL 的 match-rules 资产未恢复。
- `SvAnnouncerWinningMusic = 2132` 是按对称选的，未实测。
- configstring 479 的名字未取证（实测了索引、值和时刻）。
- 出生保护（`PMF_FROZEN 0x800`）从未置过，也无任何一帧实测值 ⇒ 只在取证。
- spy 回合上限 60 s 是先给的，零售确切秒数未取证。
- hint 带相对 0..6 由什么填充未知。
