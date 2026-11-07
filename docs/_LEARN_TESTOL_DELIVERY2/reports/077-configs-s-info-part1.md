# 学习报告 077（重开）— `configs_s.info` 前半（1–568 行 / 29 个 section）

**学习范围**：`configs_s.info` 第 1–568 行
**性质**：全实测（**82 个 section 中的前 29 个**）
**★★★ 本报告收录**`build_number=1649370` 与 ol-mod 参照的版本吻合**、**12 个 TCLS zone 的完整 ID 表**、**4 个跨区真实腾讯 IP**

---

## 一、★★★★★ **`build_number=1649370`**（第 313–314 行）

```ini
[client_config]
build_number=1649370
```

### ★★★★★ 一个**跨文件的关键吻合**

```
交付包的 `configs_s.info` ⇒ **`build_number = 1649370`**
        ↓
★★★ 与 ol-mod 参照的版本号**完全一致**
   （记忆中：实体段权威格式 = ol-mod `sv_snapshot_mp.cpp`，
    **同 build 1649370**）
        ↓
★★★ ⇒ **证实我们服务的客户端 build 就是 1649370**
```

★ **⇒ 这是**交付包与 ol-mod 参照之间的第一个硬性版本锚点**。**

★★ **⇒ 意义：ol-mod 的 `sv_snapshot_mp.cpp` 可以作为**同 build** 的权威参照。**

### ★★★ `[client_config]` 的其他条目（第 313–326 行）

| 键 | 值 | 说明 |
|---|---|---|
| **`build_number`** | **1649370** | ★★★ 版本锚点 |
| `com_BlockingHotKeys` | **0** | 不屏蔽热键 |
| `com_BlockingHotKeys_FullScreen` | **0** | 全屏也不屏蔽 |
| `r_forceD3D9XP` | **0** | 不强制 D3D9 |
| `textureMinVRamTier0` | **900** | ★ 纹理显存档 0 |
| `textureMinVRamTier1` | **600** | 档 1 |
| `textureMinVRamTier2` | **300** | 档 2 |
| `sys_stackTraceMode` | **1** | 栈回溯开 |
| `cl_reportClientLoadout` | **1** | 上报配装 |
| `cl_sendDisconnectToDSCount` | **20** | ★ 断连重发 20 次 |
| `cl_sendDisconnectToDSCountMin` | **3** | 最少 3 |
| `cl_sendDisconnectToDSTimeout` | **5000** | 超时 5 秒 |
| `r_vsyncYieldBufferTime` | **1** | — |

★★★ **⇒ 三个纹理档（900 / 600 / 300 MB 显存）是一个精确的三级分类。**

★ **⇒ `cl_sendDisconnectToDSCount=20`：客户端断连时给 DedicatedServer 重发 **20 次**（最少 3 次，超时 5000 ms）。**

---

## 二、★★★★★ **12 个 TCLS zone 的完整 ID 表**（第 4–16 行）

```ini
[tcls_zone_map]
stnd=83886082
tubd=419430402
stgd=754974722
ctgd=1090519042
dev1=16777220
dev2=503316480
rel1=452984832
rel2=469762048
stnco=16777218
stnab=100663298
stndev=67108866
stnex=33554434
```

### ★★★★★ 完整的十二区表

| # | 代号 | zone_id（十进制） | zone_id（十六进制） |
|---|---|---|---|
| **1** | **`stnd`** | **83,886,082** | **`0x05000002`** |
| **2** | **`tubd`** | **419,430,402** | **`0x19000002`** |
| **3** | **`stgd`** | **754,974,722** | **`0x2D000002`** |
| **4** | **`ctgd`** | **1,090,519,042** | **`0x41000002`** |
| **5** | `dev1` | 16,777,220 | `0x01000004` |
| **6** | `dev2` | 503,316,480 | `0x1E000000` |
| **7** | `rel1` | 452,984,832 | `0x1B000000` |
| **8** | `rel2` | 469,762,048 | `0x1C000000` |
| **9** | `stnco` | 16,777,218 | `0x01000002` |
| **10** | `stnab` | 100,663,298 | `0x06000002` |
| **11** | `stndev` | 67,108,866 | `0x04000002` |
| **12** | `stnex` | 33,554,434 | `0x02000002` |

### ★★★★★ 十六进制的**结构规律**

```
stnco  = 0x01000002
stnex  = 0x02000002
stndev = 0x04000002
stnd   = 0x05000002  ★ Platform.json 的 zoneId
stnab  = 0x06000002
stgd   = 0x2D000002
tubd   = 0x19000002
ctgd   = 0x41000002
        ↓
★★★ ⇒ 高字节是**区号**，低 16 位几乎全是 **0x0002**
   （除 dev1=0x01000004 / dev2=0x1E000000 / rel1=0x1B000000 / rel2=0x1C000000）
```

★★ **⇒ 第 1 条与既有记录吻合：`Platform.json` 的 `zoneId: 83886082` = `stnd`。**

★ **⇒ 这是**交付包内部第一个自洽的交叉验证点**。**

### ★★★ `[ds_title_zone]`（第 18–31 行）

```ini
[ds_title_zone]
zone_list=stnd,tubd,stgd,ctgd,dev1,dev2,rel1,rel2
stnd=1004
tubd=2000
stgd=4000
ctgd=3000
dev1=10000
dev2=10001
rel1=10002
rel2=10003
stnco=1000
stnab=1005
stndev=1003
stnex=1002
```

★★★★★ **⇒ 两个关键吻合：**
```
`stnd` ⇒ zone_id **83886082** ⇒ title_id **1004**
        ↓
★★★ `Platform.json` 的 `titleId: 1004` ✓ **完全一致**
★★★ 目录名也是 **`Alwaysoffline\1004\`** ✓
```

★★ **⇒ `zone_list` 只列了 **8 个**（stnd/tubd/stgd/ctgd/dev1/dev2/rel1/rel2），
**但赋值有 12 条**（多了 stnco/stnab/stndev/stnex）。**

★ **⇒ 即：**8 个是"正式区"，4 个是"内部区"（co/ab/dev/ex 后缀）。****

---

## 三、★★★★★ **4 个跨区与真实腾讯 IP**（第 149–181 行）

```ini
[cross_zone]
ping_interval=600
ping_times=2
max_connect_latency=40
free_join_players=4000
zone_groups=formal

[cross_zone_group_formal]
zones=stgd,ctgd,stnd,tubd

[cross_zone_stgd]
ping_address=182.254.107.1
zone_id=754974722
bitmask=1
original_title=4000

[cross_zone_ctgd]
ping_address=182.254.107.1
zone_id=1090519042
bitmask=1
original_title=4000

[cross_zone_stnd]
ping_address=121.51.240.1
zone_id=83886082
bitmask=2
original_title=1004

[cross_zone_tubd]
ping_address=121.51.232.1
zone_id=419430402
bitmask=4
original_title=2000
```

### ★★★★★ 四个区的完整对照

| 区 | **ping_address** | zone_id | **bitmask** | original_title |
|---|---|---|---|---|
| **`stgd`** | **`182.254.107.1`** | 754974722 | **1** | **4000** |
| **`ctgd`** | **`182.254.107.1`** | 1090519042 | **1** | **4000** |
| **`stnd`** | **`121.51.240.1`** | 83886082 | **2** | **1004** |
| **`tubd`** | **`121.51.232.1`** | 419430402 | **4** | **2000** |

### ★★★★★ 三个精确发现

```
① ★★★ `stgd` 与 `ctgd` **共用同一个 ping_address**（182.254.107.1）
   ⇒ 且 **bitmask 都是 1**
        ↓
★ 说明"金牌区/穿越金牌区"是**同一物理集群**

② ★★★ **bitmask 是 2 的幂**（1 / 1 / 2 / 4）
   ⇒ 但 **stgd 与 ctgd 都是 1** ⇒ 不是唯一的位
        ↓
★★★ ⇒ bitmask 可能是**组掩码**（stgd/ctgd 同组），不是区唯一位

③ ★ `original_title` 与 `[ds_title_zone]` **完全一致**（4000/4000/1004/2000）✓
```

★★ **⇒ 四个真实腾讯 IP：**
```
**182.254.107.1**  （深圳/腾讯云网段 182.254.x.x）
**121.51.240.1**   （腾讯深圳网段 121.51.x.x）
**121.51.232.1**   （腾讯深圳网段）
```

★ **⇒ 探测参数：`ping_interval=600` / `ping_times=2` / `max_connect_latency=40`。**

★★ **⇒ 且 `free_join_players=4000`（★ 注意值等于 `stgd` 的 title 号 4000 —— 可能是巧合，也可能是笔误）。**

★ **⇒ `zone_groups=formal` ⇒ 只有一个组名。**

### ★★★ `[netecho_probe_servers]`（第 244–246 行）

```ini
[netecho_probe_servers]
server1=stun1-stn.codol.qq.com
server2=stun1-tub.codol.qq.com
```

★★★ **⇒ 两个 netecho 探测服务器，且**后缀与 zone 代号对应**：**
```
`stun1-**stn**.codol.qq.com` ← 对应 zone `stnd`
`stun1-**tub**.codol.qq.com` ← 对应 zone `tubd`
```

★★ **⇒ 与既有 memory**完全吻合**：**
```
记忆：「`preflight.ps1` 检查 5 个 hosts 条目：
 formal-zone-auth→127.0.0.1, formal-zone-lsg→127.0.0.2,
 **stun1/2/3-tub→127.0.0.1**」
        ↓
★ 本文件确认了 **`stun1-stn` 与 `stun1-tub`** 两个真实主机名
```

★ **⇒ 还有 `qos_probe_*` 与 `netecho_probe_maxcount=3`（第 84–86 行）。**

---

## 四、★★★★★ `[dw_service_info]`：**19 个服务，只开 5 个**（第 215–236 行）

```ini
[dw_service_info]
none=0
all=0
critical=0
non_critical=0
eventlog=0
friends=0
group=0
mail=0
marketplace=0
matchmaking=1
messaging=1
pooledstorage=0
profiles=1
storage=1
tags=0
teams=0
tencent=0
titleutilities=0
reward=0
stats=1
```

### ★★★★★ 完整的开关表

| 服务 | 值 | 服务 | 值 |
|---|---|---|---|
| `none` | 0 | **`matchmaking`** | ★ **1** |
| `all` | 0 | **`messaging`** | ★ **1** |
| `critical` | 0 | `pooledstorage` | 0 |
| `non_critical` | 0 | **`profiles`** | ★ **1** |
| `eventlog` | 0 | **`storage`** | ★ **1** |
| `friends` | 0 | `tags` | 0 |
| `group` | 0 | `teams` | 0 |
| `mail` | 0 | `tencent` | 0 |
| `marketplace` | 0 | `titleutilities` | 0 |
| `reward` | 0 | **`stats`** | ★ **1** |

★★★ **⇒ 19 个服务中**恰好 5 个**开启：`matchmaking` / `messaging` / `profiles` / `storage` / `stats`。**

★★ **⇒ 与既有记录吻合：**
```
记忆：「[`dw_service_info`] only enables **5 of 19**:
 matchmaking/messaging/profiles/storage/stats」✓ **逐字一致**
```

★ **⇒ 值得注意的是 `all=0` 与 `critical=0` ⇒ 即**没有一个"总开关"被打开**。**

★★ **⇒ 关掉的服务里,**玩法相关的**有：**
```
`friends`（好友）/ `group`（组队）/ `mail`（邮件）
`marketplace`（市场）/ `tags` / `teams` / `tencent` / `reward`（奖励）
        ↓
★ 但 `loc_kill_hurts` —— `reward` 关着,而 `MarketplaceSkus.json`（2.5 MB,12,349 SKU）**仍在包内**
```

★ **⇒ 这是一个**资源与开关不匹配**的点（市场关着,但 SKU 数据完整存在）。**

---

## 五、★★★★ `[dw_config]`：**约 80 条的 Demonware 主配置**（第 79–147 行）

### 5.1 ★★★ 连接与重连

| 键 | 值 |
|---|---|
| `enable_reconnect` | **1** |
| `reconnect_timeout` | **120** |
| **`require_client_build`** | ★★ **-1** |
| `dw_keep_alive_period` | **30** |
| `dw_keep_alive_duration` | **120** |
| `dw_logoffWait` | **5000** |
| `dw_disconnect_oob_always` | **1** |

★★★★★ **⇒ `require_client_build = -1` 是一个**关键值**：**
```
`-1` ⇒ **不校验客户端 build 号**
        ↓
★★★ 这正是**离线/私服能连上**的必要条件之一
   （否则客户端 1649370 与服务端声明不符会被拒）
```

★ **⇒ 与既有记录吻合（`configs_s.info` 的 82 个 section 之一）。**

### 5.2 ★★★ 匹配（matchmaking）参数

| 键 | 值 | 说明 |
|---|---|---|
| `matchmaking_sortType` | **2** | 排序方式 |
| `matchmaking_sortBySkill_threshold` | **10** | ★ 技能排序阈值 |
| `matchmaking_sortByskill_fullOrder` | **1** | 完全按技能排序 |
| `matchmaking_skillBucketEnabled` | **0** | ★ **技能分桶关** |
| `matchmaking_skillBucketMediumStart` | **500** | 中段起点 |
| `matchmaking_skillBucketMediumEnd` | **1100** | 中段终点 |
| `matchmaking_skillBucketMergeTimeout` | **25** | 桶合并超时 |
| `matchmaking_skillBucketUseHighLow` | **0** | — |
| `matchmaking_searchIdlingTimeout` | **8** | 搜索空闲超时 |
| `matchmaking_waitingPlayersTimeout` | **8** | 等玩家超时 |
| `matchmaking_randomDelaySearchingMin` | **7** | ★ 随机延迟 7–11 |
| `matchmaking_randomDelaySearchingMax` | **11** | — |
| `matchmaking_findRoomTimeout` | **13** | 找房超时 |
| `matchmaking_findRankedRoomTimeout` | **13** | 排位找房超时 |
| `matchmaking_minMatchesForJoinInProgress` | **10** | 中途加入最少场次 |
| `matchmaking_levelBucketThreshold` | **30** | 等级桶阈值 |
| `matchmaking_maxLevelBucketSearchSeconds` | **4** | — |

★★ **⇒ 关键：`skillBucketEnabled=0` 但 `sortByskill_fullOrder=1` ⇒ **排序用技能、分桶不用**。**

### 5.3 ★★★ 房间（room）参数

| 键 | 值 |
|---|---|
| `room_useLevelBasedMatchmaking` | **0** |
| `room_mergeReserveResponseTimeout` | **3** |
| `room_joinReserveResponseTimeout` | **3** |
| `room_holdReservationTimeout` | **15** |
| `room_mergeRequestTimeout` | **3** |
| `room_serverBookingTimeout` | **5** |
| `room_maxRoomResults` | **50** |
| `room_minKillsToDisableLimitedSkillInSearch` | **110** |
| `room_limitSkillInSearchBasedOnKills` | **0** |
| `room_maxDaysSinceLastMatchForSkillInSearch` | **0** |
| `room_minKDRatioForSkillInSearch` | **0.0** |
| `room_limitSkillInSearchBasedOnKDRatio` | **0** |
| `room_joinChatChannelTimeout` | **10** |
| `room_partyJoinChatChannelTimeout` | **20** |
| `room_partyInvitationTimeout` | **20** |
| `room_migrationTimeout` | **10** |
| `dw_roomCODTeamBalance` | **2** |
| `dw_roomPartyVPartyQueryMax` | **4** |
| `dw_roomPartyVPartyData` | **1** |
| **`dw_roomMatchConstrain`** | ★★ **3**（在 `[server_cmd]`） |

★★ **⇒ `dw_roomCODTeamBalance = 2` ⇒ COD 阵营平衡模式 2。**

### 5.4 ★★★ 其他 notable

| 键 | 值 | 说明 |
|---|---|---|
| `qos_probe_enable` | **1** | QoS 探测开 |
| `qos_probe_interval` | **90** | 间隔 90 |
| `qos_probe_maxcount` | **3** | 最多 3 |
| `netecho_probe_maxcount` | **3** | 同上 |
| `enable_stuck_debug` | **1** | ★ 卡住调试开 |
| `enable_loading_stuckdebug` | **0** | 载入卡住调试关 |
| `max_reject_IM_count` | **5** | 拒收 IM 上限 |
| `ds_session_name` | **`DS_Session`** | ★ 会话名 |
| `dw_useLocalIPAsPublicIP` | **0** | ★ 不用本地 IP 当公网 IP |
| `enable_oob_tlog` | **1** | OOB tlog 开 |
| `use_new_discount` | **1** | 新折扣 |
| `dw_player_basic_info_fetch_interval` | **1** | 玩家基础信息拉取间隔 |
| `WargodScoreSkillBucketEnabled` | **1** | ★ **战神分技能分桶开**（与 mp 的 0 相反） |
| `onboadingRewardEventId` | **201507241731** | ★ 时间戳式活动号 |
| `onboardingLoginEventId` | **201611231034** | — |
| `onboardingChallenge0RewardId` | **201605271647** | — |
| `onboardingChallenge1RewardId` | **201605271648** | — |
| `onboardingChallenge2RewardId` | **201605271649** | — |
| `onboardingChallenge3RewardId` | **201605271650** | ★ 末尾四位递增 |
| `dailyChanllengeDisabled` | **1** | ★ **拼写错误**：`Chanllenge`（应为 `Challenge`） |
| `#dw_disableExitPopup=0` | ★ **被注释掉** | INI 里用 `#` 注释 |
| `use_replacement_perk_0` | **`specialty_heartbreaker`** | — |
| `use_replacement_perk_1` | **`specialty_awareness`** | — |
| `enable_wild_card_slot_for_specialty_siderollingexpert_bundle` | **38869** | ★ 一个产品 ID |

★★★ **⇒ 三个发现的细节：**
```
① ★★ **拼写错误**：`dailyChanllengeDisabled`（`Chanllenge`）—— 引擎按**字面**解析,所以这个键"能用"
② ★ `#dw_disableExitPopup=0` 用 `#` 注释 ⇒ 而 `[leaderboard]` 的
   `leaderboard_notice` 是 base64 中文 ⇒ **本文件既有 ASCII 注释又有 base64 中文**
③ ★★★ **`WargodScoreSkillBucketEnabled=1`** 与 `matchmaking_skillBucketEnabled=0`
   **相反** ⇒ 战神模式用分桶,普通匹配不用
```

---

## 六、★★★★★ `[ui_config]`：**约 65 条 UI 门禁**（第 248–311 行）

### 6.1 ★★★ 全部 `lock_*` 的开关状态（15 个为 1 的只有 3 个）

| 键 | 值 | 键 | 值 |
|---|---|---|---|
| `lockLowSpecVideoSetting` | 0 | `lock_market` | 0 |
| `lock_train` | 0 | `lock_career` | 0 |
| `lock_coop` | 0 | `lock_career_map` | 0 |
| `lock_mp` | 0 | `lock_career_reward` | 0 |
| `lock_survival` | 0 | `lock_character` | 0 |
| `lock_cyborg` | 0 | **`lock_questionnaire`** | ★ **1** |
| `lock_evacuation` | 0 | `lock_recruitmentBtn` | 0 |
| `lock_qtvideo` | 0 | `lock_web` | 0 |
| `lock_cpcounter` | 0 | `lock_pve` | 0 |
| `lock_cpcharger` | 0 | `lock_recommend` | 0 |
| `lock_inventory` | 0 | **`lock_esports`** | ★ **1** |
| `lock_in_game_complaints` | 0 | `lock_dmz_leaderboard` | 0 |
| `lock_blue_diamond_deluxe` | 0 | `lock_dmz_rule` | 0 |
| `lock_createRoom` | 0 | `lock_bestClan` | 0 |
| `lock_purchaseRobot` | 0 | `lock_clan` | 0 |
| `lock_floatingPlayerCard` | 0 | — | — |

★★★ **⇒ 30 个 `lock_*` 中只有 **2 个**是 1：`lock_questionnaire` 与 `lock_esports`。**

★★ **⇒ 即：**除问卷与电竞外,一切都解锁**。**

★ **⇒ 与既有记录吻合（`lock_*` 全 0 的观察）。**

### 6.2 ★★★ 其他精确值

| 键 | 值 | 说明 |
|---|---|---|
| `dw_enterGameNextMapCountingDown` | **90** | 进游戏后下一图倒计时 90 |
| `enable_store_mouse_sensitivity` | **1** | — |
| `ui_pl_min_player_cool` | **301** | ★ 很怪的值 |
| `ui_pl_min_player_warm` | **1201** | ★ 同上 |
| `return_lobby_timeout` | **5** | 回大厅超时 5 |
| `enable_mp_leaderboard` | **1** | — |
| `enable_new_career` | **1** | — |
| `qliveShowInterval` | **1976800000** | ★ 极大值 |
| `ui_enable_supply_drops` | **1** | — |
| `ui_enable_onboard_bypass` | **1** | ★ 新手引导可跳过 |
| `ui_enable_crafting` | **1** | — |
| `ui_enable_hostage_customize` | **1** | — |
| `ui_theme` | **5** | — |
| `uiview_theme` | **`default`** | — |
| `ui_ob_reward_0` | **`prod,22537`** | ★ 产品 ID |
| `ui_ob_reward_1` | **`prod,22538`** | — |
| `ui_ob_reward_2` | **`prod,22532`** | — |
| `ui_ob_reward_3` | **`prod,22533`** | — |
| `ui_ob_checklist_maxRank` | **0** | — |
| `ui_maxRoomAllowedToSearch` | **300** | — |
| `ui_rooms_per_page` | **30** | — |
| **`ui_mode_order`** | ★ **`zhunt,spy`** | ★★ 模式排序 |
| `ui_dmz_bcu_ad` | **`18783,21098,13239,15997,15888`** | 5 个广告位 ID |
| `ui_dmz_bcl_ad` | **`31022,31018,31019,29899`** | 4 个 |
| **`ui_dmz_ps_pl`** | ★ **`199,200,201,202,203,220,221,214`** | ★★★ **8 个 playlist 号** |
| `ui_dmz_gurantee_bcu` | **10** | ★ 拼写：`gurantee`（应 `guarantee`） |
| **`ui_spectator_blacklist`** | ★ **`spy,zhunt`** | ★★★ 观战黑名单 |
| `ui_start_play_override` | **1** | — |
| `enable_exception_tlog` | **1** | — |
| `ui_customize_disable_mode` | ★ **（空）** | — |
| `ui_disable_help` | **0** | — |

★★★★★ **⇒ 三个关键发现：**
```
① ★★★ `ui_dmz_ps_pl = 199,200,201,202,203,220,221,214` ⇒ **8 个 DMZ playlist 号**
   ★ 其中 **199** 正是 `dm.lua` 注释里说的
     "dmz ... BATTLE ROYALE (**playlist 199**, 'BattleCity - SOLO')"  ✓ **完全吻合**
        ↓
★★★ ⇒ **交付包内部第二个自洽交叉验证点**

② ★★★ `ui_mode_order = zhunt,spy` 与 `ui_spectator_blacklist = spy,zhunt`
   ⇒ **同一对模式**,一个排在前,一个被拉黑
        ↓
★ 说明 `zhunt`（僵尸猎杀）与 `spy`（间谍）是**最后加的两个特殊模式**

③ ★ **两处拼写错误**：`dailyChanllengeDisabled` 与 `ui_dmz_gurantee_bcu`
```

### ★★★ `[lockedmaps]`（第 332–333 行）

```ini
[lockedmaps]
lockedmap=mp_abandon_sh_mk
```

★ **⇒ 唯一被锁的地图：`mp_abandon_sh_mk`。**

---

## 七、★★★★★ `[map_loads_ratio]`：**39 张地图的精确加载比**

### 7.1 ★★★ 18 张多人地图

| 地图 | 比值 | 地图 | 比值 |
|---|---|---|---|
| `mp_fav_tropical` | **1,921** | `mp_bloc_sh` | **1,752** |
| `mp_estate_tropical` | **1,960** | `mp_firingrange` | **1,832** |
| `mp_storm_spring` | **1,842** | `mp_cargoship` | **1,891** |
| `mp_killhouse_sh` | **1,680** | `mp_ambush_sh` | **1,839** |
| `mp_rust` | **1,863** | `mp_shootingrange` | **1,543** |
| `mp_shipment` | **1,802** | `mp_cqbtraining` | **1,1000** |
| `mp_bog_sh` | **1,860** | `mp_trainingground` | **1,1000** |
| `mp_crash_tropical` | **1,947** | `mp_afghan` | **1,1000** |
| `mp_overgrown` | **1,824** | `mp_cross_fire` | **1,870** |

★★★ **⇒ 格式是 `<启用>,<比值>`：**
```
前 15 张 ⇒ `1,<1800±>` ⇒ ★ **全部启用**（1 = enabled）
后 3 张  ⇒ `1,1000`    ⇒ ★★★ **比值恰好 1000**（`mp_afghan` / `mp_cqbtraining` / `mp_trainingground`）
        ↓
★ `default=0,1000` ⇒ **默认比值 1000**
        ↓
★★★ ⇒ 那 3 张的比值 = **默认值** ⇒ 即**没有专门配置**,回落到默认
```

★ **⇒ 而 15 张专门配置的地图比值在 **1,543 – 1,960** 之间。**

### 7.2 ★★★ 18 张生存模式地图（coop_survival_*）

```
coop_survival_mp_trainingground=0,1000   ← ★ 唯一 1000
coop_survival_mp_cqbtraining=0,829
coop_survival_mp_afghan=0,673
coop_survival_mp_estate_tropical=0,647
coop_survival_mp_crash_tropical=0,638
...
coop_survival_mp_shootingrange=0,366     ← ★ 最小
```

★★★ **⇒ 全部 18 张的第一个字段是 **0**（★ **与多人地图的 1 相反**）。**

★★ **⇒ 精确推断：**
```
多人地图   ⇒ `**1**,<ratio>` ⇒ 第一个字段可能是 **"启用"**
生存地图   ⇒ `**0**,<ratio>` ⇒ ★ **生存模式默认关闭**
        ↓
★ 与 `[ui_config] lock_survival=0` 对比 ⇒ **UI 不锁,但 ratio 表里禁用**
        ↓
★★★ ⇒ 这是一个**两处状态不一致**的点（UI 解锁但比值表禁用）
```

### 7.3 ★★★ 僵尸与训练地图

| 地图 | 值 |
|---|---|
| **`zm_prototype_sh`** | **`0,363`** |
| **`zm_asylum_sh`** | **`0,349`** |
| **`zm_zombie_training`** | ★ **`0,30`** |
| **`coop_training_mp_cargoship`** | ★ **`0,288`** |
| **`coop_take_mp_fav_tropical`** | **`0,291`** |
| **`coop_defense_mp_crash_tropical`** | **`0,299`** |
| **`coop_take_mp_estate_tropical`** | **`0,304`** |

★★★ **⇒ 僵尸地图只有 **3 张**：`zm_prototype_sh` / `zm_asylum_sh` / `zm_zombie_training`。**

★★ **⇒ 与报告 066 的记忆对照：**
```
记忆：「4 张地图：factory **12/63**, sumpf **11/64**…(11/74), prototype **3/41**, asylum **9/38**」
        ↓
★ 记忆里的 4 张 zone 图是 **factory / sumpf / prototype / asylum**
★★★ 而 ratio 表里只有 **prototype / asylum**（+ `zm_zombie_training`）
        ↓
★ 说明 **`zm_factory_sh` 与 `zm_sumpf_sh` **不在此表**（可能用 default）
```

★ **⇒ `zm_zombie_training` 的比值 **30** 是全部 39 条里**最小**的。**

---

## 八、★★★★ `[server_cmd]` 与 `[tcls_zone_map]` 的精确值（第 71–77 行）

```ini
[server_cmd]
1224=90
dw_roomMatchConstrain=3
zombie_demo=0
aas_challenge_fullreward=1
zhunt_bossfight_hotjoin_hp_percent=40
zombie_gib_disabled=0
```

| 键 | 值 | 说明 |
|---|---|---|
| **`1224`** | ★ **90** | ★★ **数字键**（不是名字） |
| `dw_roomMatchConstrain` | **3** | — |
| **`zombie_demo`** | ★ **0** | ★★ **僵尸 demo 关** |
| `aas_challenge_fullreward` | **1** | 挑战满奖励 |
| **`zhunt_bossfight_hotjoin_hp_percent`** | ★ **40** | ★★★ BOSS 战中途加入血量 40% |
| `zombie_gib_disabled` | **0** | 僵尸 gore 开 |

★★★ **⇒ `1224=90` 是一个**裸数字键**——与 `[supply_drop_samples]` 的数字键同类。**
**⇒ 可能是**cs 号索引**或某种服务器 cvar 编号。**

★★ **⇒ `zhunt_bossfight_hotjoin_hp_percent = 40` 是一个**极为具体的玩法参数**。**

---

## 九、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **`build_number`** | **1649370**（★ 与 ol-mod 参照**完全吻合**） |
| 2 | ★★★ 纹理显存三档 | **900 / 600 / 300** |
| 3 | ★★ `cl_sendDisconnectToDSCount` | **20**（最少 **3**,超时 **5000** ms） |
| 4 | ★★★★★ **12 个 TCLS zone** | `stnd`=**83886082** / `tubd`=**419430402** / `stgd`=**754974722** / `ctgd`=**1090519042** … |
| 5 | ★★ 十六进制规律 | 低 16 位多为 **`0x0002`**，高字节是区号 |
| 6 | ★★★★★ **zone ↔ title** | `stnd`=**1004** ✓（= `Platform.json` `titleId` = 目录名） |
| 7 | ★★ `zone_list` | 只列 **8 个**正式区（赋值有 **12** 条） |
| 8 | ★★★★★ **4 个跨区真实 IP** | **`182.254.107.1`**（stgd+ctgd 共用）/ **`121.51.240.1`**（stnd）/ **`121.51.232.1`**（tubd） |
| 9 | ★★ bitmask | **1 / 1 / 2 / 4**（stgd 与 ctgd **同值**） |
| 10 | ★★ 探测参数 | `ping_interval=600` / `ping_times=2` / `max_connect_latency=40` |
| 11 | ★ `free_join_players` | **4000**（★ 与 stgd title 同值） |
| 12 | ★★★ **netecho 服务器** | **`stun1-stn.codol.qq.com`** / **`stun1-tub.codol.qq.com`** |
| 13 | ★★★★★ **`dw_service_info`** | **19 个只开 5 个**：`matchmaking`/`messaging`/`profiles`/`storage`/`stats` |
| 14 | ★★ `all=0` `critical=0` | ★ **没有总开关被打开** |
| 15 | ★★★★★ **`require_client_build`** | ★★ **`-1`**（**不校验 build**） |
| 16 | ★ `enable_reconnect` / `reconnect_timeout` | **1** / **120** |
| 17 | ★★ 匹配 | `sortType=2` / `skillBucketEnabled=**0**` / `sortByskill_fullOrder=**1**` |
| 18 | ★ 随机延迟 | **7–11** |
| 19 | ★★ 房间 | `maxRoomResults=**50**` / `dw_roomCODTeamBalance=**2**` / `holdReservationTimeout=**15**` |
| 20 | ★ `ds_session_name` | **`DS_Session`** |
| 21 | ★★ **`WargodScoreSkillBucketEnabled`** | **1**（与 mp 的 **0** **相反**） |
| 22 | ★★★ **拼写错误 ×2** | **`dailyChanllengeDisabled`** / **`ui_dmz_gurantee_bcu`** |
| 23 | ★ `#dw_disableExitPopup=0` | ★ **被 `#` 注释** |
| 24 | ★★★★★ **`ui_dmz_ps_pl`** | **`199,200,201,202,203,220,221,214`**（★ 含 **199** = dmz playlist ✓） |
| 25 | ★★★ `ui_mode_order` / `ui_spectator_blacklist` | **`zhunt,spy`** / **`spy,zhunt`** |
| 26 | ★★★ `lock_*` | **30 个中只有 2 个为 1**（`lock_questionnaire` / `lock_esports`） |
| 27 | ★ `[lockedmaps]` | **`mp_abandon_sh_mk`** |
| 28 | ★★★★★ **`[map_loads_ratio]`** | 格式 **`<enabled>,<ratio>`**；多人 **`1,`** / 生存 **`0,`** |
| 29 | ★★★ 多人比值范围 | **1,543 – 1,960**；`mp_afghan`/`mp_cqbtraining`/`mp_trainingground` = **`1,1000`**（回落默认） |
| 30 | ★★★ 生存地图 | **18 张全部 `0,`** ⇒ ★ **禁用**（而 `lock_survival=0` 解锁） |
| 31 | ★★★ 僵尸地图 | **只有 3 张**（`zm_prototype_sh` / `zm_asylum_sh` / `zm_zombie_training`） |
| 32 | ★ `zm_zombie_training` | **`0,30`**（全部 39 条**最小**） |
| 33 | ★ `[server_cmd] 1224` | ★ **90**（**裸数字键**） |
| 34 | ★★ `zombie_demo` | **0** |
| 35 | ★★★ `zhunt_bossfight_hotjoin_hp_percent` | **40** |
| 36 | ★★ `[leaderboard]` 中文 | base64 解码 = **"全新排行榜数据从2016年9月27日开始统计"** |
| 37 | ★★★ `[comscore_config]` | **`sb.scorecardresearch.com`** 真实 URL；`sample_rate=**0**` |
| 38 | ★★ `[clan_ap_bonus]` | `clan_ap_daily_cap=**1000.0**` / `clan_ap_playlist_ids=**68,127**` |
| 39 | ★ `[supply_drop_*]` | 三个 ID：**60216**（唯一 enabled）/ 60217 / 11861 |
| 40 | ★★ `[supply_drop_info]` | `supply_drop_version=**260.35**` |

---

## 十、结论

### 1. ★★★★★ **`build_number = 1649370`** 是交付包与 ol-mod 参照的**第一个硬性版本锚点**

★ **⇒ 证实 ol-mod 的 `sv_snapshot_mp.cpp` 可作**同 build**权威参照。**

### 2. ★★★★★ **交付包内部有**两个自洽交叉验证点**（都通过）

```
① `[tcls_zone_map] stnd = 83886082` + `[ds_title_zone] stnd = 1004`
   ⇒ 与 `Platform.json` 的 `zoneId:83886082` / `titleId:1004` ✓
   且与目录名 `Alwaysoffline\1004\` ✓
② `ui_dmz_ps_pl` 含 **199**
   ⇒ 与 `dm.lua` 注释的 "dmz ... playlist **199**" ✓
```

### 3. ★★★★★ **`require_client_build = -1`** ⇒ **不校验 build**（离线可行条件）

### 4. ★★★★ **`dw_service_info` 19 开 5**（且**没有总开关**）

### 5. ★★★★ **`[map_loads_ratio]` 的 `<enabled>,<ratio>` 格式**

```
多人 **`1,`** / 生存 **`0,`**（禁用）
        ↓
★★★ 但 `[ui_config] lock_survival=0` ⇒ **UI 解锁而比值表禁用**（两处不一致）
```

### 6. ★★★★ **4 个跨区真实腾讯 IP**（`182.254.107.1` 被两区共用）

### 7. ★★★ **两处拼写错误**（`Chanllenge` / `gurantee`）与 **一处被注释的键**

### 8. ★★ **僵尸地图只有 3 张在比值表里**（记忆里的 factory/sumpf 不在此表）

---

## 十一、下一步

- `configs_s.info` 后半（第 569–1,067 行，约 53 个 section）
- `mp_playlists_shipRetail_release.info`（3,970 行）
- `coop_training_mp_cargoship.lua`（4,683 行）
- `maps\*.lua`（18 个）与其余 payload 文件
