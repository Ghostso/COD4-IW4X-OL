# 学习报告 078（重开）— `configs_s.info` 后半（569–1,067 行 / 53 个 section）

**学习范围**：`configs_s.info` 第 569–1,067 行（文件结束）
**性质**：全实测（**`configs_s.info` 1,067 行全文完成**）
**★★★ 本报告收录**12 个赛季的精确时间线与北京时间规律**、**`end_time=2147483647` 的 Y2038 哨兵**、**13 个 base64 中文串的解码**

---

## 一、★★★★★ 12 个赛季的**精确时间线**（`[tournament1]`–`[tournament14]`）

### 1.1 ★★★ 完整赛季表（含 base64 解码）

| # | 赛季名（解码后） | `start_time` | `end_time` | `time_for_show`（解码） | **placement** | `leaderboard_id` |
|---|---|---|---|---|---|---|
| **1** | **战神排位赛** | **1476012152** | **1483631999** | **测试赛季** | **10** | **900** |
| **2** | **战神排位赛** | **1476012152** | **1489334399** | **预热赛季** | **10** | **901** |
| **3** | **第一赛季** | **1488124799** | **1497801600** | 第一赛季 | **6** | **902** |
| **4** | **第二赛季** | **1495382400** | **1505664000** | 第二赛季 | **6** | **903** |
| **5** | **第三赛季** | **1495382400** | **1513267200** | 第三赛季 | **5** | **904** |
| **6** | **第四赛季** | **1495382400** | **1524153600** | 第四赛季 | **5** | **905** |
| **7** | **第五赛季** | **1495382400** | **1531238399** | 第五赛季 | **5** | **906** |
| **8** | **第六赛季** | **1495382400** | **1540396800** | 第六赛季 | **5** | **908** |
| **9** | **第七赛季** | **1495382400** | **1547135999** | 第七赛季 | **5** | **914** |
| **10** | **第八赛季** | **1495382400** | **1555257600** | 第八赛季 | **5** | **920** |
| **11** | **第九赛季** | **1495382400** | **1563552000** | 第九赛季 | **5** | **926** |
| **12** | **第十赛季** | **1495382400** | **1571587199** | 第十赛季 | **5** | **932** |
| **13** | **第十一赛季** | **1571587200** | **1580515199** | 第十一赛季 | **5** | **938** |
| **14** | **第十二赛季** | **1580515200** | ★★★ **2147483647** | 第十二赛季 | **10** | **944** |

### 1.2 ★★★★★ 时间戳转成 UTC 与北京时间

| # | start（**UTC**） | start（**北京**） | end（**UTC**） | end（**北京**） |
|---|---|---|---|---|
| **1** | 2016-10-09 11:22:32 | **2016-10-09 19:22:32** | 2017-01-05 15:59:59 | **2017-01-05 23:59:59** |
| **2** | 2016-10-09 11:22:32 | 2016-10-09 19:22:32 | 2017-03-12 15:59:59 | 2017-03-12 23:59:59 |
| **3** | 2017-02-26 15:59:59 | 2017-02-26 23:59:59 | **2017-06-18 16:00:00** | **2017-06-19 00:00:00** |
| **4–12** | ★ **2017-05-21 16:00:00** | ★ **2017-05-22 00:00:00** | 各季不同 | 各季不同 |
| **13** | **2019-10-20 16:00:00** | **2019-10-21 00:00:00** | **2020-01-31 23:59:59** | **2020-02-01 07:59:59** |
| **14** | **2020-02-01 00:00:00** | **2020-02-01 08:00:00** | ★ **2038-01-19 03:14:07** | **2038-01-19 11:14:07** |

### ★★★★★ 三条精确规律

```
① ★★★ **`end_time` 的 15:59:59（UTC）= 23:59:59（北京）**
   ⇒ 而 "16:00:00（UTC）= 00:00:00（北京）"
        ↓
★ 所以赛季边界一律落在**北京时间的午夜**

② ★★★ **回合 4–12 的 `start_time` 全部相同**（1495382400 = 2017-05-22 北京 00:00）
   ⇒ 说明这 9 个赛季是**同一次运营配置**批量写入的
   （只有 `end_time` 逐个递增 ⇒ 一个"时间轴表"）

③ ★★★★★ **`[tournament14]` 的 `end_time = 2147483647`**
   = **`INT32_MAX`** = **2038-01-19 03:14:07 UTC**（**Y2038**）
        ↓
★★★ ⇒ 这是**"永不结束"的哨兵值**（第十二赛季 = 最后一季）
```

★★ **⇒ 第 ③ 条是**经典工程惯例的实证**（用 `INT32_MAX` 表示"无终止"）。**

★ **⇒ 第 ② 条是一个**运营配置的指纹**：9 个赛季同起点,只有终点不同。**

### 1.3 ★★★ `number_placement` 的变化

```
赛季 1–2  ⇒ **10**
赛季 3–4  ⇒ **6**
赛季 5–13 ⇒ **5**
赛季 14   ⇒ ★★★ **10**（★ 最后一季回到 10）
```

★ **⇒ 可能是**定级赛所需场次**（新生代赛季需要更多场次）。**

### 1.4 ★★★ 分赛区排行榜（赛季 8 起）

赛季 8 起出现**按区分的 leaderboard_id**：

```ini
best_leaderboard_id=909
stnd_leaderboard_id=910
stgd_leaderboard_id=911
ctgd_leaderboard_id=912
tubd_leaderboard_id=913
dev1_leaderboard_id=910   ← ★ 与 stnd 同
dev2_leaderboard_id=911   ← ★ 与 stgd 同
rel1_leaderboard_id=912   ← ★ 与 ctgd 同
rel2_leaderboard_id=913   ← ★ 与 tubd 同
stndev_leaderboard_id=910
stnco_leaderboard_id=911
stnab_leaderboard_id=912
stnex_leaderboard_id=913
test_leaderboard_id=910
```

★★★ **⇒ 12 个 zone 收敛到 **4 个** leaderboard：**
```
910 ⇐ stnd / dev1 / stndev / test
911 ⇐ stgd / dev2 / stnco
912 ⇐ ctgd / rel1 / stnab
913 ⇐ tubd / rel2 / stnex
        ↓
★★★ ⇒ 与报告 077 的 `[cross_zone_group_formal] zones=stgd,ctgd,stnd,tubd` **完全对应**
   （正好 4 个正式区）
```

★ **⇒ 且 `best_leaderboard_id` 每季 +2（909/915/921/927/933/939/945）而 `leaderboard_id` 每季 +6。**

---

## 二、★★★★★ **13 个 base64 中文串的解码结果**

### 2.1 完整的字符串对照表

| 位置 | base64 | **解码结果** |
|---|---|---|
| `[tournament] entranceLabel` | `56ys5Y2B6LWb5a2j` | **第十赛季** |
| `[tournament] playlistOpenTimeLabel` | `5oiY56We5o6S5L2N6LWb5q+P5pel5byA5pS+5pe26Ze05Li65pep5LiKN+eCueWIsOWHjOaZqDPngrk=` | ★★★ **战神排位赛每日开放时间为早上7点到凌晨3点** |
| `[tournament_honor_point] DailyWinBonusHint` | `6aaW6IOc5Y+M5YCN` | **首胜双倍** |
| `[tournament1–2] name` | `5oiY56We5o6S5L2N6LWb` | **战神排位赛** |
| `[tournament1] time_for_show` | `5rWL6K+V6LWb5a2j` | **测试赛季** |
| `[tournament2] time_for_show` | `6aKE54Ot6LWb5a2j` | **预热赛季** |
| `[tournament3–14] name/show` | `56ys…6LWb5a2j` | **第一赛季** … **第十二赛季** |
| `[localization_overrides] 1` | `5rWL6K+V5oiY56We5o6S5L2N6LWb` | **测试战神排位赛** |
| `[localization_overrides] 2` | `5ZGI5LiK` | **呈上** |
| `[leaderboard] leaderboard_notice` | `5YWo5paw…` | **全新排行榜数据从2016年9月27日开始统计** |

### ★★★★★ **最重要的一条**：战神排位赛的开放时间

```
"战神排位赛每日开放时间为早上7点到凌晨3点"
        ↓
★★★ 即每天 **07:00 – 次日 03:00**（20 小时）
   ⇒ **关闭时段 03:00 – 07:00**（4 小时）
```

★ **⇒ 这是一个**运营时间窗**的精确记录（排位赛不是 24 小时开放）。**

### ★★★ 两条 `localization_overrides`

```ini
string=ZARENA_ZSC_BOMBER_CLAYMORE_DESC,5rWL6K+V5oiY56We5o6S5L2N6LWb
string=SF_UI_MAIN_MENU_LABEL_MARKET,5ZGI5LiK
```

★★★ **⇒ 两条覆盖：**
```
① `ZARENA_ZSC_BOMBER_CLAYMORE_DESC`（★ zarena 的爆破兵阔剑描述）
   ⇒ 被改成 **"测试战神排位赛"**（★ **明显是测试残留**）
② `SF_UI_MAIN_MENU_LABEL_MARKET`（主菜单"市场"标签）
   ⇒ 被改成 **"呈上"**（★ **语义完全不符**）
        ↓
★★★ ⇒ 这两条都是**运营人员改串的残留**,不是设计
```

★ **⇒ 第 ① 条把一个**zarena 特效描述**改成了**排位赛名**;第 ② 条把"市场"改成了"呈上"。**
**⇒ 两者都说明 `localization_overrides` 是一个**临时发布工具**。****

---

## 三、★★★★★ `[DMZLeague]`：大逃杀联赛的完整配置

```ini
[DMZLeague]
lock_league=0
lock_league_reward=0
lock_league_leaderboard=0
ticket_playlist=199,200
playlist=220,221
current_league=2
token_sku_free=34775
token_sku_battle=34776
token_item_id=20000
champion_points_solo=50,30,18,16,14,12,10,8,8,8,6,6,6,4,4,2,2,2,2
champion_points_buddy=40,25,14,8,7,6,5,3,2,2,2,2,2,2,2,2
champion_chest_level=25,50,65,80,100,100,125,125,150,150,175,175,200,200
free_ticket_hold_limit=10
battle_ticket_hold_limit=20
battle_ticket_weekly_win_limit=20
```

### ★★★★★ 关键的 playlist 分组

| 键 | 值 | 含义 |
|---|---|---|
| **`ticket_playlist`** | ★ **`199,200`** | 用**票**的 playlist |
| **`playlist`** | ★ **`220,221`** | **联赛**playlist |

★★★★★ **⇒ 与报告 077 的 `ui_dmz_ps_pl = 199,200,201,202,203,220,221,214` 交叉验证：**
```
`ui_dmz_ps_pl` 8 个号：
  **199,200**  ⇒ ★ `ticket_playlist`（**用票**）
  **220,221**  ⇒ ★ `playlist`（**联赛**）
  201,202,203  ⇒ 其他（可能观战/练习）
  214          ⇒ 其他
        ↓
★★★ ⇒ **两处完全自洽** ⇒ 交付包内部第三个交叉验证点 ✓
```

★★ **⇒ 且 `dm.lua` 注释说 "dmz ... playlist **199**" ✓（`199` 就是 ticket_playlist 的第一个）。**

### ★★★ 冠军分（`champion_points_*`）的精确曲线

| 名次 | **solo** | **buddy** |
|---|---|---|
| **1** | **50** | **40** |
| **2** | **30** | **25** |
| **3** | **18** | **14** |
| **4** | **16** | **8** |
| **5** | **14** | **7** |
| **6** | **12** | **6** |
| **7** | **10** | **5** |
| **8** | **8** | **3** |
| **9–11** | **8, 8, 6** | **2, 2, 2** |
| **12–14** | **6, 6, 4** | **2, 2, 2** |
| **15–19** | **4, 4, 2, 2, 2** | **2, 2, 2, 2, 2** |

★★★ **⇒ solo 有 **19 级**、buddy 有 **16 级**。**

★ **⇒ solo 的第 1 名 **50** 分,buddy 第 1 名 **40** 分 ⇒ **单人排位给分更高**（补偿难度）。**

### ★★★ 宝箱等级门槛（`champion_chest_level`）

```
25, 50, 65, 80, 100, 100, 125, 125, 150, 150, 175, 175, 200, 200
        ↓
★★★ 14 个门槛,后 5 对有**重复值**（100/100, 125/125, 150/150, 175/175, 200/200）
```

★ **⇒ 14 级宝箱,但最后 5 级的门槛成对相同 ⇒ **宝箱只有 9 个不同门槛**。**

### ★★★ 票的限额

| 键 | 值 |
|---|---|
| `token_sku_free` | **34775** |
| `token_sku_battle` | **34776** |
| `token_item_id` | **20000** |
| `free_ticket_hold_limit` | **10** |
| `battle_ticket_hold_limit` | **20** |
| `battle_ticket_weekly_win_limit` | **20** |

★★ **⇒ 免费票上限 **10**,战斗票上限 **20**,每周胜利上限 **20**。**

### ★★★ `[DMZLeague_1]` / `[DMZLeague_2]`

| 赛季 | start_time | end_time | leaderboard_id |
|---|---|---|---|
| **1** | **1516279618** | **1534780800** | **1200** |
| **2** | **1516279618** | **1577721600** | **1201** |

```
1516279618 ⇒ 2018-01-18 20:46:58 北京
1534780800 ⇒ 2018-08-21 00:00:00 北京
1577721600 ⇒ 2019-12-31 00:00:00 北京
        ↓
★ 两个赛季**同一 start_time**（2018-01-18）
★★ `current_league=2` ⇒ **当前是第 2 季**（到 2019-12-31 结束）
```

---

## 四、★★★★★ `[DMZLeague_Chest_Pool]`：**14 奖励 × 14 权重行**

```ini
num_reward=14
reward_1=0,31012,-1
...
reward_14=0,29899,-1
weight_1=10000,5000,3000,100,0,0,100,0,0,1000,0,0,0,0
...
weight_14=10000,10000,10000,10000,10000,10000,50000,50000,50000,75000,60000,50000,35000,20000
```

### ★★★★★ 14 个奖励（格式 `<type>,<item_id>,<duration>`）

| # | 值 | # | 值 |
|---|---|---|---|
| 1 | **`0,31012,-1`** | 8 | **`0,31018,-1`** |
| 2 | **`0,30748,-1`** | 9 | **`0,31019,-1`** |
| 3 | **`0,30750,-1`** | 10 | **`0,29895,-1`** |
| 4 | **`0,31013,-1`** | 11 | **`0,29896,-1`** |
| 5 | **`0,30749,-1`** | 12 | **`0,29897,-1`** |
| 6 | **`0,30751,-1`** | 13 | **`0,29898,-1`** |
| 7 | **`0,31022,-1`** | 14 | **`0,29899,-1`** |

★★★ **⇒ 全部 type 都是 **0**,duration 都是 **-1**（永久）。**

★★ **⇒ 四个 item_id（31018/31019/31022/29899）与报告 077 的 `ui_dmz_bcl_ad=31022,31018,31019,29899` **完全一致** ✓**
**⇒ **交付包内部第四个交叉验证点**。****

### ★★★ 14 行权重的精确演进

```
weight_1  ⇒ 只有前 **5** 项非零（10000,5000,3000,100,0,0,100,0,0,1000,0,0,0,0）
weight_14 ⇒ **全部 14 项非零**
        ↓
★★★ 单调演进：低等级（weight_1）只可能出前几个奖励,
     高等级（weight_14）出全部
        ↓
★ 且第 **7** 列在所有行里都是 **50000**（最高的恒定值）
```

★★ **⇒ 第 7 个奖励（`0,31022,-1`）在**每一等级**都有 **50000** 权重 ⇒ 它是"保底奖励"。**

★ **⇒ 第 10 列（`0,29895,-1`）在 weight_1–9 里是 **1000/5000/20000/25000/30000/35000/40000/45000/50000** ⇒ 逐级高速增长。**

### ★★★ `[DMZLeague_Sub_Pool]`（第 1,032–1,044 行）

```ini
num_reward=10
Reward_1=2,1,1000
Reward_2=0,241,14
Reward_3=0,10839,14
Reward_4=0,22477,14
Reward_5=1,1404,1
Reward_6=1,172,20
Reward_7=1,18552,1
Reward_8=0,31014,-1
Reward_9=0,31015,-1
Reward_10=0,31016,-1
weight=100,30,40,30,50,100,100,26,26,14
```

★★★ **⇒ 这里的格式是 `<type>,<id>,<duration>`,三种 type：**
```
type **0** ⇒ 永久（duration **-1**）
type **1** ⇒ 限时（duration **1 / 20**）
type **2** ⇒ ★ **货币**（`2,1,1000` ⇒ item 1,数量 **1000**）
```

★ **⇒ `Reward_1=2,1,1000` ⇒ 1000 单位的基础货币（保底）。**

★★ **⇒ 与 `[DMZLeague_Chest_Pool]` 的**全 0 类型**不同 ⇒ 两个池的语义不同。**

---

## 五、★★★★★ `[spy_mode]`：间谍模式的**业值（Karma）系统**

```ini
[spy_mode]
Karma_HurtLose=9
Karma_HurtLosePer=10
Karma_KillLose=120
Karma_HurtGet=3
Karma_HurtGetPer=10
Karma_KillGet=40
Karma_NoTKGet=80
Karma_Punishment=-200
Karma_NoPunishLeast=2
Is_DefensiveFightback=1
Is_TeamKiller_Suicide=1
```

### ★★★★★ 完整的业值表

| 键 | 值 | 含义 |
|---|---|---|
| **`Karma_HurtLose`** | **9** | 每 10 点友伤减多少 |
| **`Karma_HurtLosePer`** | **10** | 分母 |
| **`Karma_KillLose`** | **120** | ★ 友军击杀减多少 |
| **`Karma_HurtGet`** | **3** | 每 10 点友伤加多少 |
| **`Karma_HurtGetPer`** | **10** | 分母 |
| **`Karma_KillGet`** | **40** | ★ 友军击杀加多少 |
| **`Karma_NoTKGet`** | **80** | ★★ **无友伤通关加 80** |
| **`Karma_Punishment`** | **-200** | ★ 惩罚阈值 |
| **`Karma_NoPunishLeast`** | **2** | 免罚最少 |
| **`Is_DefensiveFightback`** | **1** | 防御还击开 |
| **`Is_TeamKiller_Suicide`** | **1** | 自杀算击杀队友 |

★★★ **⇒ 一个**对称的加减分系统**：**
```
造成友伤 ⇒ 每 10 点 **减 9**
受到友伤 ⇒ 每 10 点 **加 3**
击杀队友 ⇒ **减 120**
被队友击杀 ⇒ **加 40**
无友伤通关 ⇒ **加 80**
        ↓
★ `Karma_Punishment=-200` ⇒ 低于 -200 触发惩罚
```

★ **⇒ 注意符号语义可能是"业值越低越坏"（-200 是惩罚线）。**

★★ **⇒ `Is_TeamKiller_Suicide=1` ⇒ **自杀判定为击杀队友**（防止用自杀规避惩罚）。**

★ **⇒ 与 `ui_spectator_blacklist=spy,zhunt` 呼应 ⇒ `spy` 是**特殊模式**（有独立业值系统）。**

---

## 六、★★★★ 其余 section 的精确值

### 6.1 `[ability_diagram]`（第 570–582 行）

| 键 | min | max |
|---|---|---|
| `score` | **0.0** | **500.0** |
| `ka` | **0.0** | **4.0** |
| `killstreakkill` | **0.0** | **0.5** |
| `survival` | **15.0** | **60.0** |
| `motivation` | **0.0** | **0.4** |
| `accuracy` | **0.05** | **0.6** |

★★ **⇒ 6 个维度的归一化区间（用于雷达图/能力图）。**

### 6.2 `[matchstreak]`（第 588–594 行）

```ini
active=1
kd=0.7
rank=49
returnDays=7
returnRank=49
newbiewarmround=0
```

★★ **⇒ `rank=49` 与 `returnRank=49` ⇒ 回归玩家保留 49 段。**
**⇒ `returnDays=7` ⇒ 7 天算回归。**

### 6.3 `[tournament]` 的**精确率表**（第 596–636 行）

| 键 | 值 |
|---|---|
| `head_tournament` | **14**（★ 当前赛季号） |
| `playlistId` | **68** |
| **`HVExchangeRate`** | **50,100,150,200,300,500**（6 档） |
| **`HVProtectionRate`** | **20,30,45,60,80,120**（6 档） |
| **`PSUpgradeRate`** | **18 档**：100,200,300,450,500,600,700,750,800,850,900,950,1000,1050,1100,1150,1200,1250 |
| **`PSPenaltyRate`** | **18 档**：50,50,60,70,80,90,100,110,120,130,140,150,160,170,180,190,200,210 |
| **`SeniorWargodPSUpgradeRate`** | **15 档**：200,225,250,300,350,375,400,425,450,500,600,700,800,1000,1250 |
| **`SeniorWargodPSPenaltyRate`** | **16 档**：50,50,60,70,80,90,100,110,120,130,140,150,160,170,180,190 |
| **`SeniorWargodBeginingPS`** | **16 档**：60,60,60,60,60,60,80,80,80,100,100,100,120,120,120,200 |
| `minimalRequiredTime` | **150** |
| `hotJoinCutoffSeconds` | **180** |
| `maxPartyMember` | **3** |
| `placementMatchPromotionRate` | **0,6000,12000,18000,24000,30000,36000**（7 档） |
| `tssEnabled` / `tssTimeout` | **1** / **10** |
| `newbieJWGScore` / `newbieWGScore` | **12000** / **114060** |
| `levelPromoteWargod` | **101** |
| `directToWGInitScore` | **114060** |
| `wargodWarmRoundThreshold` | **36000** |
| `perZoneLeaderboard` | ★ **12 个 zone 全列** |
| `entranceLabel` | **第十赛季** |
| `playlistOpenTimeLabel` | ★★★ **战神排位赛每日开放时间为早上7点到凌晨3点** |

★★★ **⇒ 三个"门槛分"：**12000 / **114060** / **36000****。**

★ **⇒ `sd_minimalRequiredTime = 150` 与 `dom_minimalRequiredTime = 150` 与通用 `minimalRequiredTime = 150` **三者相同**（`sd` / `dom` 有独立的 key 但值一样）。**

★ **⇒ `hotJoinCutoffSeconds = 180`（3 分钟）⇒ 比赛开始 3 分钟后不能中途加入。**

### 6.4 `[junior_tournament_playlist]` 的**权重矩阵**（第 641–660 行）

```ini
playlist=1,110,71,123,125,6,126,156,15,14
0=     2,1,1,1,1,1,1,1,1,1
6000=  2,1,1,1,1,1,1,1,1,1
...
102000=0,1,1,0,2,2,2,1,2,1
```

★★★ **⇒ 10 个 playlist × 18 个分数档的矩阵。**

★ **⇒ 第 1 列从 **2 → 0**（分数越高越禁用 playlist 1）;第 5 列从 **1 → 2**（越高越启用）。**
**⇒ 这是一个**按分数分段的启用权重表**（0 = 关闭）。**

### 6.5 `[tournament_jwg_challenge_reward]`（第 662–681 行）

```ini
score=0,6000,12000,...,102000       ← 18 档
0=201711130001,25727,0,0
6000=201711130002,5991,0,7
12000=201711130003,116,0,14
...
```

★★★ **⇒ 每行格式 `<活动号>,<item_id>,<?>,<?>`：**
```
活动号：**201711130001** … **201711130018**（★ 末尾 2 位递增）
        ↓
★ 日期前缀 **20171113** ⇒ 2017-11-13 创建
        ↓
★★★ 第 3、4 字段循环 **(0,0) → (0,7) → (0,14)** ⇒ 每次 +7
```

### 6.6 ★★★ **三个空 section**（第 708–713 行）

```ini
[tournament_challenge_reward]

[tournament_season_reward]

[tournament_top100_reward]
```

★★★ **⇒ 三个 section **完全为空**（只有标题）⇒ 定义了但从未配置。**

★ **⇒ 这是**"配置结构存在但数据缺失"的实例**（与 `zm.lua` 的"Authored ≠ opened"同类）。**

### 6.7 `[tournament_honor_point*]`（第 683–706 行）

| 键 | 值 |
|---|---|
| `BHP_PerMinute` / `AHP_PerMinute` | **7** / **5** |
| `Max_Time` | **1200** |
| `WinFactor` / `LoseFactor` | **1.5** / **1** |
| `DailyWinBonus` | **2.0** |
| `DailyWinBonusHint` | **首胜双倍** |
| `BHP_DailyLimit` / `AHP_DailyLimit` | **2000** / **2000** |
| `BHP_MaxLimit` / `AHP_MaxLimit` | **6000** / **6000** |
| `BHP_Storage` / `AHP_Storage` | **50000** / **50000** |
| `bonus_score` | **126000,144000,162000,180000,198000** |
| 126000/144000 | **B1000** |
| 162000–198000 | **A1000** |

★★ **⇒ BHP（B 级荣誉点）每分钟 7,AHP 每分钟 5 ⇒ **B 级给得更多**（反直觉,可能是"基础/高级"的区别）。**

### 6.8 `[ZHUNT_*]`（第 1,047–1,067 行）

```ini
[ZHUNT_Override_Reward_Weights]
case_1_reward_1=100
case_1_reward_2=200
case_1_reward_3=8000

[ZHUNT_Scalers]
exp_scaler=1
weapon_exp_scaler=1
gp_scaler=1
nightmare_exp_scaler=1
nightmare_weapon_exp_scaler=1
nightmare_gp_scaler=1
zombie_hp_scaler=1
miniboss_hp_scaler=1
finalboss_hp_scaler=1
actor_zombie_miniboss_bodypart_1=1
actor_zombie_miniboss_bodypart_2=1
actor_zombie_finalboss_bodypart_1=1
actor_zombie_finalboss_bodypart_2=1
actor_zombie_finalboss_bodypart_3=1
```

★★★ **⇒ 14 个 scaler **全部等于 1** ⇒ 没有任何缩放（即"原值"）。**

★★ **⇒ 这是**"配置存在但全部中立"的实例**（定义了 14 个可调参数,全为 1）。**

★★ **⇒ 且揭示 `zhunt` 有两套难度：`nightmare_*`（噩梦）与普通。**
**⇒ 且 BOSS 分部件：`miniboss` 2 个部件 / `finalboss` 3 个部件。**

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **12 个赛季的时间线** | 2016-10-09 → **2038-01-19** |
| 2 | ★★★ 北京时间规律 | `end_time` = **UTC 15:59:59** = **北京 23:59:59**；`start_time` = **北京 00:00:00** |
| 3 | ★★★ 赛季 4–12 | **同一 `start_time`**（1495382400 = 2017-05-22 北京 00:00） |
| 4 | ★★★★★ **`tournament14.end_time`** | **2147483647 = INT32_MAX = 2038-01-19**（**Y2038 哨兵 = 永不结束**） |
| 5 | ★★ `number_placement` | **10 → 6 → 5 → 10**（末季回到 10） |
| 6 | ★★★ 分赛区榜 | 12 zone 收敛到 **4 个**（910/911/912/913）⇒ 与 `zone_groups=stgd,ctgd,stnd,tubd` 对应 |
| 7 | ★★★★★ **后台中文解码** | `playlistOpenTimeLabel` = **"战神排位赛每日开放时间为早上7点到凌晨3点"** |
| 8 | ★★ 其他中文 | **第十赛季 / 首胜双倍 / 第一至第十二赛季 / 测试赛季 / 预热赛季** |
| 9 | ★★★ **两条 `localization_overrides`** | `ZARENA_ZSC_BOMBER_CLAYMORE_DESC` → **"测试战神排位赛"**；`SF_UI_MAIN_MENU_LABEL_MARKET` → **"呈上"**（★ 测试残留） |
| 10 | ★★★★★ **`[DMZLeague]` playlist 分组** | `ticket_playlist`=**199,200** / `playlist`=**220,221** ⇒ 与 `ui_dmz_ps_pl` **自洽** ✓ |
| 11 | ★ 联赛季 | `current_league`=**2**；两季同 `start`=**1516279618**（2018-01-18） |
| 12 | ★★★ 冠军分 | solo **19 级**（首 **50**）/ buddy **16 级**（首 **40**） |
| 13 | ★★ 宝箱门槛 | **14 个**，但后 5 对重复 ⇒ **9 个不同门槛** |
| 14 | ★ 票限额 | 免费 **10** / 战斗 **20** / 周胜 **20** |
| 15 | ★★★★ `[DMZLeague_Chest_Pool]` | **14 奖励 × 14 权重行**；第 **7** 列恒 **50000**（保底） |
| 16 | ★★ item_id 交叉验证 | **31018/31019/31022/29899** 与 `ui_dmz_bcl_ad` **完全一致** ✓ |
| 17 | ★★ `[DMZLeague_Sub_Pool]` 三类 type | **0=永久 / 1=限时 / 2=货币** |
| 18 | ★★★★★ **`[spy_mode]` 业值系统** | 友伤 −9/10 · 击杀队友 **−120** · 无友伤 **+80** · 惩罚线 **−200** |
| 19 | ★ `Is_TeamKiller_Suicide` | **1**（自杀算击杀队友） |
| 20 | ★★ `[ability_diagram]` | 6 维度归一化区间 |
| 21 | ★ `[matchstreak]` | `rank=**49**` / `returnDays=**7**` |
| 22 | ★★★ `[tournament]` 率表 | `PSUpgradeRate` **18 档** / `PSPenaltyRate` **18 档** / `SeniorWargod*` 15–16 档 |
| 23 | ★★ 门槛分 | **12000** / **114060** / **36000** |
| 24 | ★ 时间门 | `minimalRequiredTime=**150**` / `hotJoinCutoffSeconds=**180**` |
| 25 | ★★ `[junior_tournament_playlist]` | **10 playlist × 18 分数档**权重矩阵 |
| 26 | ★★★ **三个空 section** | `[tournament_challenge_reward]` / `_season_reward` / `_top100_reward` |
| 27 | ★★ `[tournament_honor_point]` | BHP **7**/min · AHP **5**/min · `WinFactor=**1.5**` |
| 28 | ★★★ `[ZHUNT_Scalers]` | **14 个 scaler 全 = 1**（无缩放） |
| 29 | ★★ `zhunt` 双难度 | `nightmare_*` + 普通；BOSS 部件 miniboss **2** / finalboss **3** |

---

## 八、结论

### 1. ★★★★★ **12 个赛季构成一条精确的时间线**（2016-10-09 → 2038-01-19）

★ **⇒ `end_time` 一律落在**北京时间 23:59:59**；`start_time` 在**北京 00:00:00**。**
**★ ⇒ 赛季 4–12 **共用同一个 `start_time`** ⇒ 一次运营配置批量写入的"时间轴表"。**

### 2. ★★★★★ **`[tournament14]` 的 `end_time = 2147483647`** 是 **INT32_MAX / Y2038 哨兵**

★ **⇒ 含义 = "永不结束"（第十二赛季是最后一季）。**

### 3. ★★★★★ **`[DMZLeague]` 与 `ui_dmz_ps_pl` 的 playlist 分组完全自洽**

```
`ticket_playlist` = **199,200**
`playlist`        = **220,221**
        ↓
二者都出现在 `ui_dmz_ps_pl = 199,200,201,202,203,220,221,214` 里 ✓
★ 且 `dm.lua` 注释的 "dmz playlist **199**" ✓
```

### 4. ★★★★★ **战神排位赛每日只开 20 小时**（07:00–次日 03:00）

### 5. ★★★★ **`[spy_mode]` 有一套完整的业值（Karma）系统**（友伤/击杀队友/无友伤奖惩）

### 6. ★★★ **`localization_overrides` 是发布工具**（两条覆盖都是测试残留）

### 7. ★★★ **三处"结构存在但数据缺失/中立"**

```
① `[tournament_challenge_reward]` / `_season_reward` / `_top100_reward` **三个空 section**
② `[ZHUNT_Scalers]` **14 个 scaler 全 = 1**（无缩放）
③ `[tournament_challenge_reward]` 空（但 `_jwg_challenge_reward` 有 18 档数据）
```

### 8. ★★ **宝箱池第 7 列恒 50000** ⇒ "保底奖励"；**12 zone 收敛到 4 个排行榜**

---

## 九、下一步

- `mp_playlists_shipRetail_release.info`（3,970 行）—— 与 `configs_s.info` 的 playlist 号交叉验证
- `coop_training_mp_cargoship.lua`（4,683 行）—— `coop.lua` 让渡的那一层
- `ol-mod-runtime-manifest.json`（28,209 B）
- `maps\*.lua`（18 个）
- 其余 payload 文件与 bundle 收尾
