# 学习报告 003（重开）— `payload\Ayria\Assets\Alwaysoffline\` 逐文件

**学习范围**：`Identity.json` + `1004\` 下 14 个文件
**方法**：全文读入 + Grep 提取结构 + 字节数与换行反推
**性质**：全实测

---

## 一、★★★ `configs_s.info`（26,249 字节）—— 交付包里**信息密度最高**的配置

### 1.1 结构：**82 个节**（CRLF 换行）

★★ **判别依据**：Grep `^\[.*\]$` **无命中**，而 `^\[` 有命中 ——
**⇒ 行尾是 `\r\n`，`\r` 破坏了 `$` 锚点。**

```
[version]                       ← g_dwConfigVersion=1
[tcls_zone_map]                 ★★★ zone ID 表
[ds_title_zone]                 ★★★ zone → titleId
[xp_bonus]  [com_data]  [qq_membership]  [party_bonus]
[netcafe_privileges]  [server_cmd]
[dw_config]                     ★★★ Demonware 主配置（70 行）
[cross_zone] [cross_zone_group_formal] [cross_zone_stgd]
[cross_zone_ctgd] [cross_zone_stnd] [cross_zone_tubd]
[wargod_party]  [skill_config]
[dw_service_info]               ★★★★ 服务开关矩阵（19 项）
[dw_task_timing_overrides]      ★★ 任务超时
[netecho_probe_servers]         ★★★ STUN 域名
[ui_config] [client_config] [client_demo] [lockedmaps] [map_loads_ratio]
[comscore_config] [tencent_config] [tencent_nfs_config]
[clan_config] [clan_xp_bonus] [clan_ap_bonus] [clan_url_config]
[global_chat]
[supply_drop_list] [supply_drop_info] [supply_drop_samples]
[supply_drop_featured] [supply_drop_reward] [supply_drop_video]
[game_moment] [tencent_website] [tencent_datamore]
[leaderboard] [ability_diagram] [onboarding] [matchstreak]
[tournament] [junior_tournament_placement_playlist] [junior_tournament_playlist]
[tournament_jwg_challenge_reward] [tournament_honor_point]
[tournament_honor_point_quota] [tournament_honor_point_bonus]
[tournament_challenge_reward] [tournament_season_reward]
[tournament_top100_reward] [tournament1..14]
[spy_mode] [localization_overrides] [saleTimesFlag]
[weeklyChallengeReward]
[DMZLeague] [DMZLeague_1] [DMZLeague_2]
[DMZLeague_Chest_Pool] [DMZLeague_Sub_Pool]
[ZHUNT_Override_Reward_Weights] [ZHUNT_Scalers]
```

### 1.2 ★★★★ `[dw_service_info]` —— **DW3 服务开关矩阵**（第 215–235 行）

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
marketplace=0            ← ★★ 商城**关闭**
matchmaking=1            ★ 开
messaging=1              ★ 开
pooledstorage=0
profiles=1               ★ 开
storage=1                ★ 开
tags=0
teams=0
tencent=0                ← ★★ 腾讯服务**关闭**
titleutilities=0
reward=0
stats=1                  ★ 开
```

★★★ **⇒ 19 个服务里只有 5 个开启：**

```
matchmaking   配对
messaging     消息
profiles      档案
storage       存储
stats         统计
```

★★★ **⇒ 这就是**后端必须实现的 DW3 服务清单** ——
**比任何文档都权威（是客户端自己读的配置）。**

★ **注意 `marketplace=0` 但 `MarketplaceSkus.json`（2.5 MB）仍被打包** ——
**商城服务关闭，但数据文件在。**（可能是加载器需要文件存在）

★ **`tencent=0`** —— **腾讯平台服务关闭**（与 `Platformwrapper` 只提供接口不做网络的观察一致）

### 1.3 ★★★★ `[tcls_zone_map]` + `[ds_title_zone]`（第 4–32 行）

```ini
[tcls_zone_map]
stnd=83886082            ← ★★★ 十进制
tubd=419430402
stgd=754974722
ctgd=1090519042
dev1=16777220
dev2=503316480
rel1=452984832
rel2=469762048

[ds_title_zone]
zone_list=stnd,tubd,stgd,ctgd,dev1,dev2,rel1,rel2
stnd=1004                ← ★★★ titleId
tubd=2000
stgd=4000
ctgd=3000
dev1=10000
dev2=10001
```

★★★ **跨文件核对（实测值对得上）**：

| 值 | `configs_s.info` | `Platform.json` | 一致？ |
|---|---|---|---|
| `zoneId` | `stnd=83886082` | `"zoneId": 83886082` | ✓ |
| `titleId` | `stnd=1004` | `"titleId": 1004` | ✓ |

★★★ **⇒ **`Platform.json` 的 `zoneId` 就是 `[tcls_zone_map]` 里的 `stnd`**，
**`titleId` 就是 `[ds_title_zone]` 里 `stnd` 的映射值。** 两个文件互相印证。

★ **⇒ `83886082 = 0x05000002` 不是随机的，是**CODOL 标准区（stnd）**的编号。**

★ **`tubd`（Tencent/Union Board?）= 419430402 = 0x19000002`**
★ **`stgd` = 754974722 = 0x2D0000 02`**
★ **`ctgd` = 1090519042 = 0x41000002`**

★★ **⇒ 全部是 `0xXX000002` 形态 —— 高字节是区类型，低 24 位是 `2`。**

### 1.4 ★★★ `[netecho_probe_servers]`（第 244–246 行）

```ini
[netecho_probe_servers]
server1=stun1-stn.codol.qq.com
server2=stun1-tub.codol.qq.com
```

★★★ **⇒ 与 `stun.ini` / `preflight.ps1` 的 `stun*.codol.qq.com` 同族。**

★ **注意这里是 `stun1-stn` 和 `stun1-tub`（不是 `stun1-tub`/`stun2-tub`/`stun3-tub`）。**

★★ **⇒ `configs_s.info` 用的是 `-stn`/`-tub` 后缀（区名），
`stun.ini` 用的是数字后缀。两套并存。**

### 1.5 `[dw_config]`（70 行，第 79–148 行）★ 关键参数

```ini
[dw_config]
enable_reconnect=1
reconnect_timeout=120
require_client_build=-1          ← ★ -1 = 不检查 build
qos_probe_enable=1
qos_probe_interval=90
qos_probe_maxcount=3
netecho_probe_maxcount=3
dw_keep_alive_period=30
dw_keep_alive_duration=120
dw_logoffWait=5000
ds_session_name=DS_Session
dw_useLocalIPAsPublicIP=0
...
matchmaking_sortType=2
matchmaking_findRoomTimeout=13
matchmaking_searchIdlingTimeout=8
matchmaking_waitingPlayersTimeout=8
room_serverBookingTimeout=5
room_maxRoomResults=50
room_migrationTimeout=10
...
dailyChanllengeDisabled=1        ← ★ 拼写错误 "Chanllenge"
use_replacement_perk_0=specialty_heartbreaker
enable_wild_card_slot_for_specialty_siderollingexpert_bundle=38869
```

★★ **`require_client_build=-1`** —— **不校验客户端 build 号。**
★ **这对离线很重要**（否则 build 不匹配会拒连）。

★★ **`dailyChanllengeDisabled=1` —— 多了个 `l`（`Chanllenge`）** ——
**原始 CODOL 配置文件的拼写错误被原样保留。**
★ **⇒ 说明这是**从真实发布文件抄来的**，不是重写的。**

### 1.6 `[dw_task_timing_overrides]`（第 237–242 行）

```ini
[dw_task_timing_overrides]
0=25000,25000,2000,5
1=25000,25000,2000,10
2=25000,25000,2000,5
3=60000,60000,2000,5
4=60000,60000,2000,10
```

★ **5 个任务，每个 4 个数字（毫秒级超时）** —— 与 DW3 的任务重试有关。

### 1.7 文件尾部（第 1053–1066 行）

```ini
[ZHUNT_Scalers]
exp_scaler=1
weapon_exp_scaler=1
gp_scaler=1
nightmare_*_scaler=1
zombie_hp_scaler=1
miniboss_hp_scaler=1
finalboss_hp_scaler=1
actor_zombie_miniboss_bodypart_1=1
...
```

★ **全部 = 1（标准倍率）** —— **无魔改。**

---

## 二、★★★ `market_ui.info`（2,010 字节）—— **是 zlib 压缩数据**

### 实测（Read 工具报错原文）

> This file has **NUL bytes** in its first 8 KB: **binary data**, UTF-16/UTF-32 without a
> byte-order mark, or text with embedded NULs.

### ★★★ 文件头字节

```
x�uX]o5...
78 9C 75 58 5D 6F 35 ...
```

★★★ **`78 9C` = zlib 头**（CMF=0x78, FLG=0x9C）：
```
CMF = 0x78:  CM=8 (deflate), CINFO=7 (32K window)
FLG = 0x9C:  FLEVEL=2 (default), FDICT=0, FCHECK=0x1C
检查： (0x78<<8 | 0x9C) % 31 = 0x789C % 31 = 30876 % 31 = 0  ✓ 合法 zlib
```

★★★ **⇒ `market_ui.info` 是一个 **zlib deflate 流**，不是 INI。**

★ **⇒ 需要解压才能看内容。** 交付包没附解压工具。

★★ **对比**：同目录的 `sku_tags.info`（3,520 B）是**明文 INI** ——
**⇒ 同一目录下**明文与压缩并存**。**

---

## 三、★★ `sku_tags.info`（3,520 字节）—— 明文 INI，**LF 换行**

### 4 个节

```ini
[tags]                    ← 40 行，HOT/NEW/POPULAR/RECOMMEND 各 10 项
45542=HOT:1
45533=HOT:2
...
45137=RECOMMEND:1
...
[supply_drop_list]        ← 3 项
0=60216
1=60217
2=11861
[supply_drop_info]        ← ★ supply_drop_version=337.0（唯一的浮点）
60216_SlotCount=3
60216_SupplyMultipleConsume=0
60217_SlotCount=1
60217_DustSKU=22644
60217_DustRequirement=100
...
[supply_drop_samples]     ← 递增编号（60216_0 .. 60216_N）
60216_0=10070_0
60216_1=10071_0
...
```

★★ **换行判别：Grep `^\[.*\]$` **有命中** ⇒ LF 换行。**
★★★ **⇒ 与 `configs_s.info`（CRLF）**不一致**！**

★ **`[tags]` 是**商城物品的标签**（HOT/NEW/POPULAR/RECOMMEND 各 10 名）。**
★ **`supply_drop_*` 是**补给箱**配置（版本 `337.0`）。**

★★ **⇒ 但 `[dw_service_info] marketplace=0`（商城关闭）—— 这些数据可能不会被读。**

---

## 四、★★ `mp_playlists_shipRetail_release.info`（112,274 字节）

### 头部（Read 工具报错原文）

> This file is **not valid UTF-8**: it uses a **legacy encoding** such as Windows-1252,
> Shift-JIS or **GBK**, or it is binary.

### 前 30 行

```
version 796                       ← ★ 文件版本
// *******************************
// *** Playlist Rules ***
// *******************************
// Always increment the playlist version number, at the top of the file, when making a change.
// Do not repurpose or reuse playlist IDs.
// When adding a new playlist, always set the playlist ID for the new playlist to the number
//   shown in "Next Playlist ID" below these rules. Example, if the newest ID is 65, your new
//   playlist ID will be ID 65.
// ...
// If you have any playlist related questions, contact Andre Tiran or Dan Merboth for assistance.
// *** Next Playlist ID ***256***
rule 3266 8
rule 2085 1
rule cg_drawfps 1
rule party_minlobbytime 10
rule com_maxfps 85                ← ★★★ 帧率上限 85
set scr_airdrop_nuke 0
set scr_airdrop_mega_nuke 0
set 124 300
set 123 128
set 97 0
```

★★ **`com_maxfps 85`** —— **帧率上限 85**（不是常见的 60 或 125）。

★ **`Next Playlist ID ***256***`** —— **播放列表 ID 空间到 256。**

★★ **非 UTF-8** ⇒ 文件里可能有 GBK 中文（播放列表名）。

★ **这是**原始发布文件**（含 Activision 员工姓名）** —— 又一次证明**原样抄的**。**

---

## 五、★★ 其余小节

| 文件 | 字节 | 内容 |
|---|---|---|
| `Identity.json` | 34 | `{"username":"Alwaysoffline"}`（LF） |
| `1004\MarketplaceSkus.json` | 2,578,582 | 商城 SKU 全表（未读） |
| `Server\activities_v1.info` | **2** | `20 20`（两个空格） |
| `Server\broadcast.info` | 23 | `<MSG T=1570255261,P=0/>` |
| `Server\daily_challenge_config.info` | **0** | ★ 空文件（SHA256 = `E3B0C442…` = 空串哈希） |
| `Server\MOTD.info` | **0** | ★ 空文件（同上哈希） |
| `Server\market-down.info` | 90 | `[Market] update=1 / onetimefetch=1 / starttime=1569560400 / endtime=1569562200 / interval=600` |
| `Server\selected_playlist.txt` | 17 | `Original Playlist` |
| `Server\tlogconfig.info` | 154 | `[TLog]` + `dwdsmm_slope=1.9` |
| `Server\whitelist_tester.info` | 93 | `[Whitelist]` 3 个 u64 userid |

★★★ **`E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`** 是
**空输入的标准 SHA256** —— **两个 0 字节文件确证为空。**

---

## 六、★★★ 换行风格的**三种并存**（累计实测）

| 文件 | 字节 | 换行 | 判别依据 |
|---|---|---|---|
| `Platform.json` | 256 | **LF** | 报告 017 转储 |
| `Identity.json` | 34 | **LF** | 报告 017 转储 |
| `sku_tags.info` | 3,520 | **LF** | ★ Grep `^\[.*\]$` **命中** |
| **`configs_s.info`** | **26,249** | **CRLF** | ★★ Grep `^\[.*\]$` **不命中** / `^\[` 命中 |
| `market-down.info` | 90 | **CRLF** | 报告 017 转储 |
| `tlogconfig.info` | 154 | **CRLF** | 报告 017 转储 |
| `whitelist_tester.info` | 93 | **CRLF** | 报告 017 转储 |
| `selected_playlist.txt` | 17 | **无** | 报告 017 |
| `broadcast.info` | 23 | **无** | 报告 017 |
| `activities_v1.info` | 2 | **无** | 报告 017 |

★★★ **⇒ 同一目录下三种换行风格并存 ⇒ 客户端**不校验换行**。**

★ **新发现：`configs_s.info`（CRLF）与 `sku_tags.info`（LF）**相邻但不同**。**

---

## 七、★★★ 编码风格并存

| 文件 | 编码 |
|---|---|
| `configs_s.info` | ASCII（纯英文） |
| `sku_tags.info` | ASCII |
| `mp_playlists_shipRetail_release.info` | ★ **非 UTF-8**（legacy / GBK） |
| `market_ui.info` | ★★★ **zlib 二进制** |
| `MarketplaceSkus.json` | 未测 |

★ **⇒ 同一目录下**纯文本 + 旧编码 + 压缩二进制**三种格式并存。**

---

## 八、逐字节证据总表

| # | 文件 | 字节 | 结构 | 关键发现 |
|---|---|---|---|---|
| 1 | `configs_s.info` | 26,249 | 82 节 / CRLF | ★★★ `[dw_service_info]` 5/19 开 |
| 2 | ↳ `[tcls_zone_map]` | — | — | `stnd=83886082` = Platform.json zoneId ✓ |
| 3 | ↳ `[ds_title_zone]` | — | — | `stnd=1004` = Platform.json titleId ✓ |
| 4 | ↳ `[netecho_probe_servers]` | — | — | `stun1-stn` / `stun1-tub` |
| 5 | ↳ `[dw_config]` | — | 70 行 | `require_client_build=-1` |
| 6 | ↳ `[dw_task_timing_overrides]` | — | 5 项 | 4 元组超时 |
| 7 | `sku_tags.info` | 3,520 | 4 节 / **LF** | `supply_drop_version=337.0` |
| 8 | `market_ui.info` | 2,010 | ★★★ **zlib** | `78 9C` 头 |
| 9 | `mp_playlists_...info` | 112,274 | 非 UTF-8 | `version 796` / `com_maxfps 85` |
| 10 | `daily_challenge_config.info` | **0** | — | 空哈希 `E3B0C442…` |
| 11 | `MOTD.info` | **0** | — | 空哈希 |
| 12 | `Identity.json` | 34 | LF | `Alwaysoffline` |

---

## 九、结论

### 1. ★★★★ `[dw_service_info]` 是**后端实现的权威清单**

```
必须实现：matchmaking / messaging / profiles / storage / stats  （5 个）
不必实现：其余 14 个（含 marketplace / tencent / friends / teams）
```

★★★ **⇒ 换战斗服、甚至重写后端，都应以这张表为准。**

### 2. ★★★ `configs_s.info` 与 `Platform.json` **互相印证**

```
zoneId  83886082  ←→  [tcls_zone_map] stnd
titleId 1004      ←→  [ds_title_zone] stnd
```

### 3. ★★★ 交付包资产**格式三态**：明文 INI / 旧编码 / zlib

★ **`market_ui.info` 是 zlib，但包里没有解压工具。**

### 4. ★★ 多种换行并存 ⇒ 客户端不校验

### 5. ★★ 原始发布文件的痕迹（拼写错误、Activision 员工姓名、版本号）

★★★ **⇒ 这些资产是**从真实发布文件抄来的**，不是重做的。**
**`dailyChanllengeDisabled` 的拼写错误和 `contact Andre Tiran or Dan Merboth` 是铁证。**

---

## 十、下一步

`payload\Ayria\Assets\` 还剩：
- `1004\MarketplaceSkus.json`（2,578,582 B）
- `OlMod\GameScripts\` 31 个 Lua（`common.lua` / 11 gametype / 19 map）
- `Platformwrapper\Platform.json`（已知）
- `ol-mod-runtime-manifest.json`（28,209 B，来源标注）
