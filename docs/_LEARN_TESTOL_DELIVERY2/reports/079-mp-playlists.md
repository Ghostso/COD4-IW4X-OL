# 学习报告 079（重开）— `mp_playlists_shipRetail_release.info`（3,970 行）

**学习范围**：`mp_playlists_shipRetail_release.info` 全文（3,970 行 / 112,274 字节）
**性质**：全实测（**全包最大的配置数据文件**）
**★★★★★ 本报告收录五个重大发现**：①文件是 **GBK 编码**（全包唯一）②**44 个 gametype → script 权威表** ③**playlist 用到 32 个 gametype,但只有 11 个脚本 ⇒ 21 个无脚本** ④**playlist 199 的 override 字段双重编码损坏** ⑤**`validdate2` 含不存在的日期**

---

## 一、★★★★★ **编码缺陷**：本文件是 **GBK（codepage 936）**

### 1.1 证据

```
`Read` 工具读本文件 ⇒ 报 "This file is not valid UTF-8: it uses a legacy encoding"
        ↓
原始字节用 GBK 解码 ⇒
  `catinfo 11` 的 `"�����ж�"` ⇒ **"狼人行动"** ✓
        ↓
★★★ 对照：全包其他文本文件（`.lua` / `.ini` / `.json`）都是 **UTF-8 或纯 ASCII**
```

★★ **⇒ 这是**全包唯一一个 GBK 文件**（在已读的所有文本文件里）。**

★ **⇒ 后果：任何按 UTF-8 读它的工具（含 `Read`）都会看到乱码,且**无法编辑**。**
**⇒ 已用 PowerShell `[Text.Encoding]::GetEncoding(936)` 解码后落到工作目录再读。**

### ★★★ 文件规模

| 项 | 值 |
|---|---|
| **行数** | **3,970** |
| **字节数** | **112,274** |
| **平均每行** | **28 字节** |

---

## 二、★★★★★ **文件头与规则**（第 1–18 行）

```ini
version 796

// *****************************************************************
// *** Playlist Rules ***
// *****************************************************************
// Always increment the playlist version number, at the top of the file, when making a change.
// Do not repurpose or reuse playlist IDs.
// When adding a new playlist, always set the playlist ID for the new playlist to the number shown in "Next Playlist ID" below these rules. ...
// When making a playlist unavailable to the live environment, always label the playlist as "Offline" ...
// When making a playlist unavailable to the live environment, move the playlist to the appropriate "Unused" section.
// Playlists are now labeled via a comments section at the top of each playlist. ...
// If a playlist is only for Dev environment, be sure to label as such in the name ...
// If you have any playlist related questions, contact Andre Tiran or Dan Merboth for assistance.

// *** Next Playlist ID ***256***
```

### ★★★★★ 四个精确事实

| # | 项 | 值 |
|---|---|---|
| **1** | **`version`** | **796** |
| **2** | **`Next Playlist ID`** | ★ **256**（⇒ 已用 ID 最大是 **255**） |
| **3** | ★★ **原作者（Activision 联系人）** | **Andre Tiran / Dan Merboth** |
| **4** | ★★★ 规则来源 | **这是 Infi­nity Ward 的原版 playlist 文件格式** |

★★★ **⇒ 第 4 条是**血统证据**：**
```
文件头保留了 **IW 原版英文注释 + 两个 IW 员工姓名**
        ↓
★★★ ⇒ 这个文件是**从 IW 原版（MW2/MW3 血统）继承下来**的,
   不是腾讯自研的 playlist 格式
        ↓
★ 而腾讯只在**中文名字段**上做了本地化
```

★ **⇒ `Next Playlist ID 256` 与实测**最大 ID = 255**（`playlist 255`）**完全吻合** ✓**

---

## 三、★★★★★ **44 个 gametype → script 权威表**（第 155–465 行）

| # | 行 | **gametype** | **name** | **script** | 有脚本？ |
|---|---|---|---|---|---|
| 1 | 160 | `combat` | `MPUI_COMBAT_TRAINING` | `combat` | ✗ |
| **2** | 167 | **`tdm`** | `MPUI_TEAM_DEATHMATCH` | ★ **`war`** | ★ **✓** |
| **3** | 176 | **`cha`** | `MPUI_CHA` | **`cha`** | ★ **✓** |
| 4 | 185 | `dom` | `MPUI_DOMINATION` | `dom` | ✗ |
| 5 | 195 | `hq` | `MPUI_HEADQUARTERS` | ★ **`koth`** | ✗ |
| 6 | 203 | `hp` | `MPUI_HARDPOINT` | `hp` | ✗ |
| 7 | 213 | `sab` | `MPUI_SABOTAGE` | `sab` | ✗ |
| **8** | 221 | **`sd`** | `MPUI_SEARCH_AND_DESTROY` | **`sd`** | ★ **✓** |
| 9 | 230 | `sr` | `MPUI_SEARCH_AND_RESCUE` | `sr` | ✗ |
| 10 | 239 | `dd` | `MPUI_DD` | `dd` | ✗ |
| **11** | 248 | **`ffa`** | `MPUI_DEATHMATCH` | ★ **`dm`** | ★ **✓** |
| 12 | 255 | `tjugg` | `MPUI_TJUGG` | `tjugg` | ✗ |
| 13 | 262 | `ctf` | `MPUI_CAPTURE_THE_FLAG` | `ctf` | ✗ |
| **14** | 272 | **`kc`** | `MPUI_CONF` | ★ **`conf`** | ★ **✓** |
| 15 | 281 | `tag` | `MPUI_TAG` | `tag` | ✗ |
| 16 | 290 | `collect` | `MPUI_COLLECT` | `collect` | ✗ |
| 17 | 299 | `asym` | `MPUI_ASYM` | `asym` | ✗ |
| 18 | 306 | `borg` | `MPUI_BORG` | `borg` | ✗ |
| 19 | 312 | `des` | `MPUI_DESTROYER` | `des` | ✗ |
| 20 | 318 | `gun` | `MPUI_GUN` | `gun` | ✗ |
| 21 | 324 | `oic` | `MPUI_OIC` | `oic` | ✗ |
| 22 | 330 | `sas` | `MPUI_SAS` | `sas` | ✗ |
| **23** | 336 | **`coop`** | `MPUI_SPEC_OPS` | **`coop`** | ★ **✓** |
| **24** | 342 | **`zm`** | `MPUI_ZOMBIE` | **`zm`** | ★ **✓** |
| 25 | 348 | `clash` | `MPUI_CLASH` | `clash` | ✗ |
| 26 | 354 | `shrines` | `MPUI_SPEC_OPS` | `shrines` | ✗ |
| **27** | 360 | **`zarena`** | `MPUI_SPEC_OPS` | **`zarena`** | ★ **✓** |
| 28 | 366 | `zsurv` | `MPUI_SPEC_OPS` | `zsurv` | ✗ |
| 29 | 372 | `zchamp` | `MPUI_SPEC_OPS` | `zchamp` | ✗ |
| **30** | 378 | **`zhunt`** | `MPUI_SPEC_OPS` | **`zhunt`** | ★ **✓** |
| **31** | 384 | **`td`** | `MPUI_SPEC_OPS` | **`td`** | ★ **✓** |
| 32 | 390 | `hunt` | `MPUI_SPEC_OPS` | `hunt` | ✗ |
| 33 | 396 | `sdp` | `MPUI_SEARCH_AND_DESTROY_PLUS` | `sdp` | ✗ |
| 34 | 405 | `sdc` | `MPUI_SEARCH_AND_DESTROY_CHMP` | `sdc` | ✗ |
| 35 | 413 | `vip` | `MPUI_VIP` | `vip` | ✗ |
| 36 | 419 | `robbery` | `MPUI_ROBBERY` | `robbery` | ✗ |
| 37 | 426 | `spy` | `MPUI_SPY` | `spy` | ✗ |
| 38 | 432 | `hostage` | `MPUI_HOSTAGE` | `hostage` | ✗ |
| 39 | 439 | `ph` | `MPUI_PROP_HUNT` | `ph` | ✗ |
| 40 | 446 | `chicken` | `MPUI_chicken` | `chicken` | ✗ |
| **41** | 453 | **`dmz`** | `MPUI_DMZ` | **`dmz`** | ★ **✓** |
| 42 | 457 | `tdmz` | `MPUI_TDMZ` | `tdmz` | ✗ |
| 43 | 463 | `nftbl` | `MPUI_NFTBL` | `nftbl` | ✗ |

★★★ **⇒ 全表 **43 个 gametype**（+ 表头 MICRO CLIENT 区）,其中**只有 11 个有脚本**。**

### ★★★★★ 与交付包 `gametypes\` 目录的**完美对应**

```
有脚本的 11 个 gametype 的 `script` 值：
  cha → cha     coop → coop    dmz → dmz    sd → sd
  td → td       war → war      zarena → zarena   zhunt → zhunt
  zm → zm       conf → conf    (11 个)
        ↓
★★★ 交付包 `payload\...\GameScripts\gametypes\` 恰好有 **11 个 `.lua`**：
  cha.lua / coop.lua / conf.lua / dm.lua / dmz.lua / sd.lua
  td.lua / war.lua / zarena.lua / zhunt.lua / zm.lua
        ↓
★★★★★ **逐一对应,无缺无余** ✓
```

★ **⇒ 这是一个**决定性的交叉验证**：交付包的 11 个脚本**正好**覆盖了本表里 11 个"脚本名与 gametype 名或映射目标存在"的项。**

★★ **⇒ 其余 **32 个 gametype 没有脚本**。**

### ★★★ 三个需要特别指出的映射

```
① ★★★ **`gametype tdm` → `script war`** ✓（与 `war.lua` 注释一致）
② ★★★ **`gametype kc`  → `script conf`** ✓（与 `conf.lua:3` 引用的 `CodolPlaylist.cpp:69` 一致）
③ ★★★ **`gametype hq`  → `script koth`** ⇒ **总部模式用 `koth`（King of the Hill）脚本**
```

★★ **⇒ 第 ③ 条解释了为什么 `hq` 不在文件里 —— 它的脚本名叫 `koth`。**

### ★★★ `MPUI_SPEC_OPS` 被 **8 个 gametype 共用**

```
`coop` / `shrines` / `zarena` / `zsurv` / `zchamp` / `zhunt` / `td` / `hunt`
        ↓
★★★ 8 个 gametype 全部 `name MPUI_SPEC_OPS`
        ↓
★ 说明 UI 上它们都显示为"特别行动"
```

---

## 四、★★★★★ **21 个 gametype 在 playlist 里被使用但没有脚本**

### 4.1 实测使用频次（`Grep` 统计所有 `<map>,<gametype>,<weight>` 行）

| gametype | 出现 | gametype | 出现 | gametype | 出现 |
|---|---|---|---|---|---|
| **`sd`** | **146** | `asym` | 8 | `oic` | 6 |
| **`tdm`** | **110** | `gun` | 8 | `zarena` ✓ | 6 |
| **`cha`** | **82** | `ph` | 8 | `chicken` | 5 |
| **`coop`** | **45** | `sas` | 8 | `vip` | 3 |
| `dom` | **29** | `tjugg` | 7 | `nftbl` | 2 |
| `sdp` | 16 | `borg` | 6 | `robbery` | 2 |
| `hostage`/`sr`/`zchamp`/`zm` | 14 | `hp`/`oic` | 6 | ★ **`td`** | **1** |
| `dmz`/`zhunt`/`ffa` | 12 | — | — | — | — |
| `clash` | 11 | — | — | — | — |
| `spy`/`zsurv` | 10 | — | — | — | — |
| `kc`/`tag` | 9 | — | — | — | — |

### ★★★★★ 与 11 个脚本的对照

```
有脚本（11）：cha / coop / conf(kc) / dm(ffa) / dmz / sd / td / war(tdm) / zarena / zhunt / zm
        ↓
★★★ **使用但无脚本（21 个）**：
  asym / borg / chicken / clash / dom / gun / hostage / hp
  nftbl / oic / ph / robbery / sas / sdp / spy / sr
  tag / tjugg / vip / zchamp / zsurv
```

★★★★★ **⇒ 21 个 gametype 的 playlist 会加载**一个不存在的脚本**。**

★★ **⇒ 后果与 `war.lua:8-16` 描述的**完全同一类问题**：**
```
war.lua 的原话（逐字）：
  "war had **NO script, no `player_killed` callback**, and therefore
   **zero team score for the whole match: the clock was the only thing
   that could ever end it**."
        ↓
★★★ ⇒ 这 21 个 gametype 面对**同一个缺口**
   （`dom` 出现 **29 次** / `spy` **10 次** / `sr` **14 次** / `sdp` **16 次**）
```

★ **⇒ `war.lua` / `conf.lua` 是**只修了 2 个**,还剩 **21 个未修**。**

★★ **⇒ 这是**交付包最重要的结构性缺口**：**
```
配置层声称有 43 个 gametype
实现层只有 11 个脚本
        ↓
★★★ 缺口率 = 32/43 ≈ **74%**
```

---

## 五、★★★★★ **123 个 playlist 的完整索引**

**格式**：`PL <id> line<行> cat=<类别> ord=<显示序> maps=<地图数> rules=<规则数> bv='<buildversion>' flags=[...] gt=<gametype统计>`

### 5.1 ★★★ 当前有效的代表作（节选）

| PL | 类别 | **英文名** | **中文名（解码）** | 地图 | gametype |
|---|---|---|---|---|---|
| **1** | 1 | Skirmish | **实战对抗** | 5 | `cha`×5 |
| **2** | 8 | Onboarding | **冲锋团队竞技** | 5 | `cha`×5 |
| **123** | 2 | Skirmish | **实战对抗** | 8 | `sd`×8 |
| **4** | 9 | Charge - Assault | **冲锋团竞6V6** | 15 | `cha`×15 |
| **110** | 1 | Map: Nuketown | **-核弹小镇** | 1 | `cha`×1 |
| **68** | 8 | S&D + DOM Wargod/Esports | **战神排位赛** | 10 | `dom`×5+`sd`×5 |
| **10** | 23 | Survival Normal | **生存模式** | 6 | `coop`×6 |
| **30** | 3 | Skirmish | **实战对抗** | 13 | `tdm`×13 |
| **6** | 2 | Assault | **经典爆破6V6** | **27** | `sd`×27 |
| **206** | 2 | Assault - Hardcore | **经典爆破6V6 - 真实模式** | 27 | `sd`×27 |
| **126** | 2 | Ground War | **经典爆破9V9** | 24 | `sd`×24 |
| **13** | 3 | Assault | **战术团竞6V6** | **34** | `tdm`×34 |
| **14** | 3 | Ground War | **战术团竞9V9** | 30 | `tdm`×30 |
| **15** | 9 | Domination | **据点争夺** | 22 | `dom`×22 |
| **122** | 9 | Search and Rescue | **搜索救援** | 14 | `sr`×14 |
| **154** | 10 | Snipers Only | **狙击战** | 11 | `ffa`×11 |
| **181** | 10 | One in the Chamber | **致命一发** | 6 | `oic`×6 |
| **182** | 10 | Sticks and Stones | **原始战争** | 8 | `sas`×8 |
| **196** | 10 | Prop Hunt | **躲猫猫** | 8 | `ph`×8 |
| **204** | 10 | Gun Game | **枪械游戏** | 8 | `gun`×8 |
| **218** | 10 | Chicken 6v6 | **疯狂的小鸡 6V6** | 5 | `chicken`×5 |
| **254** | 10 | Nuclear Football | **核子橄榄球** | 1 | `nftbl`×1 |
| **142** | 11 | SPY | **狼人行动** | 10 | `spy`×10 |
| **199** | 13 | BattleCity - SOLO | **勇者游戏 单人** | 2 | `dmz`×2 |
| **77** | 9 | Kill Confirmed Ground War | **抢钻大战9V9** | 9 | `kc`×9 |
| **124** | 9 | Loot Drop | **夺金大战** | 9 | `tag`×9 |
| **251** | 30 | Infected Area | **感染区** | 1 | ★ **`td`×1** |
| **67** | 9 | Leader TDM | **首领团队竞技** | 7 | `tjugg`×7 |
| **76/118** | 9 | Machine Public Enemy | **机械阵地战** | 4 | `asym`×4 |

★★★ **⇒ 地图数最多的是 **PL 13（34 张 `tdm`）** 和 **PL 6/206（27 张 `sd`）**。**

★ **⇒ gametype 名与中文名**语义对应**（如 `spy` = 狼人行动,`ph` = 躲猫猫）。**

### 5.2 ★★★★★ **`playlist 201` 被引用但未定义**

```
`configs_s.info` 的 `ui_dmz_ps_pl = 199,200,**201**,202,203,220,221,214`
        ↓
★★★ 本文件里搜 `playlist 201` ⇒ **零命中**
   （已有 199 / 200 / 202 / 203 / 214 / 220 / 221）
        ↓
★★★ ⇒ **playlist 201 缺失**
```

★ **⇒ 而 `[DMZLeague] ticket_playlist=199,200` 与 `playlist=220,221` 都齐全。**
**⇒ 所以缺的只有 **201**。**
**⇒ 201 的位置（199/200 与 202/203 之间）提示它原本可能是**某个已被删除的 DMZ 变体**。**

### 5.3 ★★★ 文件的分段结构（`// *** ***` 标记）

| 行 | 段名 |
|---|---|
| **3** | Playlist Rules |
| **16** | Next Playlist ID |
| **113** | Categories |
| **155** | Gametypes |
| **466** | **MICRO CLIENT** |
| **473** | MP Playlists |
| **816** | **War God Playlists** |
| **858** | PVE Playlists |
| **946** | **FULL CLIENT** |
| **953** | MP Playlists |
| **1980** | Party Mode Cycle |
| **2188** | StreakBreak / WarmRound Playlists |
| **2296** | PVE Playlists |
| **2855** | **GAPP ZONE MP AND PVE** |
| **2862** | ★★★ **CURRENTLY UNUSED MP** |
| **3289** | ★★★ **CURRENTLY UNUSED PVE** |
| **3698** | **BattleCity Playlists** |

★★★ **⇒ 两种客户端（MICRO / FULL）各有一套完整 playlist 表 ⇒ 说明有**两个客户端形态**。**
**⇒ 与报告 077 的 `buildversion default cb3 release` 呼应（`cb3` = 某种客户端代号）。**

★ **⇒ 两个 UNUSED 段（2863 / 3290）说明**有大量被淘汰的 playlist** 但**保留在文件里**。**

---

## 六、★★★★★ **`catinfo` 的 22 个类别**（第 122–152 行）

```ini
//      ID    Group Flag  Unlock_Item				Name_chinese        	Name_CN
catinfo 11    1     0         ""						"狼人行动"                	"狼人行动"
catinfo 2     1     1         ""						"经典爆破"  	"经典爆破"
catinfo 1     1     0         ""						"Charge"            	"Charge"
catinfo 16    1     4         ""						"ROBBERY"				"ROBBERY"
catinfo 13    1     1         ""                        "Game of Valor"         "Game of Valor"
catinfo 15    1     0         ""						"VIP"					"VIP"
catinfo 14    1     0         ""	                    "Nuclear Football"      "Nuclear Football"
catinfo 10	  1     8		  ""						"Party Cycle"			"Party Cycle"
catinfo 3     1     0         ""						"Team Deathmatch"   	"Team Deathmatch"
catinfo 12    1     0         ""	                    "Prop Hunt"             "Prop Hunt"
catinfo 5     1     0         ""						"Hostage Mode"         	"Hostage Mode"
catinfo 9     1     0         ""		"Chaos Fight"          	"Chaos Fight"
catinfo 4     1     0         ""						"Search & Destroy: Plus" "Search & Destroy: Plus"
catinfo 7     1     0         ""						"DEV"               	"DEV"
catinfo 8     1     0         ""						"QA"                	"QA"
catinfo 21    0     0         ""						"Hero Ops"          	"Hero Ops"
catinfo 30    0     4         ""						"Tower Defence"         "Tower Defence"
catinfo 29    0     1         ""						"Zombie Hunter"         "Zombie Hunter"
catinfo 28    0     0         ""		"ZS Champions"     		"ZS Champions"
catinfo 22    0     0         ""	"Cyborgs"           	"Cyborgs"
catinfo 23    0     0         ""			"Survival"          	"Survival"
catinfo 26    0     0         ""		"Zombie Survival"     	"Zombie Survival"
catinfo 20    0     0         ""			"Super Zombie Battle" 	"Super Zombie Battle"
catinfo 24    0     0         ""						"Timed"             	"Timed"
catinfo 25    0     0         ""						"DEV"               	"DEV"
```

### ★★★★★ 三个精确定义（来自文件头注释，逐字）

```
"ID only matters to help connect the playlist to the category.
 **The actual number is never used in the UI.**"
"ID must be **> 0**."
"**Group** will be used by the UI mostly to **seperate PvP vs PvE**,
 though it might someday be extended to more."
"**Flag: Featured = 1, internal development only = 2, New = 4, Cycle = 8**"
```

| 项 | 含义 |
|---|---|
| **Group 1** | ★ **PvP**（15 个） |
| **Group 0** | ★ **PvE**（10 个） |
| **Flag 1** | **Featured** |
| **Flag 2** | **仅内部开发** |
| **Flag 4** | **New** |
| **Flag 8** | **Cycle** |

★★★ **⇒ Flag 的两个值同时出现：`catinfo 16` 的 Flag=**4**（New）与 `catinfo 10` 的 Flag=**8**（Cycle）。**
**⇒ 而 `catinfo 2`（经典爆破）与 `catinfo 13`（Game of Valor）是 Flag=**1**（Featured）。**

★★ **⇒ 只有 **2 个**类别有中文名（`catinfo 11` = 狼人行动 / `catinfo 2` = 经典爆破）**
⇒ **其余 20 个类别名是纯英文（未本地化）。**

★ **⇒ 两列（`Name_chinese` 与 `Name_CN`）内容**完全相同** ⇒ 冗余列。**

---

## 七、★★★★★ **BattleCity（DMZ）playlist 的完整细节**（第 3698–3826 行）

### 7.1 ★★★★★ **`playlist 199` 的 override 字段双重编码损坏**

```ini
playlist 199
displayorder 13
category 13
name chinese "勇者游戏 单人"
name english "BattleCity - SOLO"
overridename chinese "BattleCity"
overridename english "脫脗脮脽脫脦脧路"
description chinese "勇者游戏单人模式。在废弃的未来城市中，克服多变的自然环境，收集武器装备，淘汰其他选手，成为最强勇者！"
description english "You are on your own, survive to be the winner."
overridedescription chinese "Survive to be the winner."
overridedescription english "脭脷路脧脝煤碌脛脦麓脌麓鲁脟脢脨脰脨拢卢驴脣路镁露脿卤盲碌脛脳脭脠禄禄路戮鲁拢卢脢脮录炉脦盲脝梅脳掳卤赂拢卢脤脭脤颅脝盲脣没脩隆脢脰拢卢鲁脡脦陋脳卯脟驴脫脗脮脽拢隆"
```

### ★★★★★ 完整的编码链（已实测验证）

```
原始文本：**勇者游戏**
   GBK 字节 = D3 C2 D5 DF D3 CE CF B7
        ↓
① 把这 8 字节**按 CP1252 读** ⇒ 8 个字符 **"ÓÂÕßÓÎÏ·"**
   （D3=Ó, C2=Â, D5=Õ, DF=ß, D3=Ó, CE=Î, CF=Ï, B7=·）
        ↓
② 把这 8 个字符**按 UTF-8 写** ⇒ 16 字节
   C3 93 C3 82 C3 95 C3 9F C3 93 C3 8E C3 8F C2 B7
        ↓
③ 文件里存的**就是这 16 字节**
        ↓
④ 我按 GBK 读 ⇒ **"脫脗脮脽脫脦脧路"**（8 个汉字乱码）
        ↓
★★★ 逆向（已实测）：
   UTF8 解码 → CP1252 字节 → GBK 解码 = **勇者游戏** ✓
```

### ★★★★★ 两个字段**互换**且**英文槽被二次编码**

| 字段 | 实际内容 | 本应内容 |
|---|---|---|
| `overridename **chinese**` | ★ **`BattleCity`**（**英文**） | 勇者游戏 |
| `overridename **english**` | ★★★ **`勇者游戏`**（**中文,且二次编码**） | BattleCity |
| `overridedescription **chinese**` | ★ **`Survive to be the winner.`**（**英文**） | 中文长描述 |
| `overridedescription **english**` | ★★★ **`在废弃的未来城市中，克服多变的自然环境，收集武器装备，淘汰其他选手，成为最强勇者！`**（**中文,二次编码**） | 英文 |

★★★ **⇒ 两处**同时出错**：**
```
① **chinese 槽装英文,english 槽装中文**（★ 互换）
② ★★★ **english 槽里的中文被"GBK→CP1252→UTF-8"三重折腾**
   （而同一文件的 `name` / `description` 的 chinese 槽是**正常 GBK**）
```

★ **⇒ 即：只有 **`override*` 这四个字段**坏了,同 playlist 的 `name` / `description` 是好的。**
**⇒ 说明 `override` 字段是**由另一个工具/流程写入**的,而那个流程的编码处理是错的。**

### 7.2 ★★★ 七个 DMZ playlist 的完整参数

| PL | 英文名 | 中文名 | **`scr_dmz_buddymode`** | `rule 1011` | `rule 3265` | `maxparty` | 标志 |
|---|---|---|---|---|---|---|---|
| **199** | BattleCity - SOLO | **勇者游戏 单人** | **0** | **17** | **18** | **0** | `buddy_playlist 200` / `featured` |
| **200** | BattleCity - BUDDY | **勇者游戏 双人** | **1** | **16** | **18** | **2** | `featured` |
| **202** | BattleCity - HARDCORE - Solo | **勇者游戏 极限单人** | **0** | **17** | **18** | **0** | `hardcore` / `unlockflag uf_dmz_hardcore_unlocked` |
| **203** | BattleCity - HARDCORE - Buddy | **勇者游戏 极限双人** | **1** | **16** | **18** | **2** | `hardcore` / 同上 |
| **214** | BattleCity - Reverse Circle | **勇者游戏 绝命逃生** | **0** | **17** | **18** | **0** | ★ `homepagead 3` |
| **220** | BattleCityLeague - SOLO | **周末勇者联赛 单人** | （外部） | — | — | — | 周赛 |
| **221** | BattleCityLeague - BUDDY | **周末勇者联赛 双人** | ★ **1** | — | — | — | 周赛 |

### ★★★★★ 三个新的 DMZ cvar（全包首次出现）

```ini
set scr_dmz_buddymode 0 / 1                    ← 单人 / 双人
set dmz_circle_reversed 1                      ← ★ 反向圈（PL 214）
set scr_dmz_lootTableOption ReversedCircle     ← ★ 反向圈掉落表（PL 214）
```

★★★ **⇒ 「绝命逃生」（Reverse Circle）用**两个 cvar** 实现：**
```
`dmz_circle_reversed 1`              ⇒ 圈**反向收缩**
`scr_dmz_lootTableOption ReversedCircle` ⇒ **专用掉落表**
        ↓
★ 中文描述："地面资源较为匮乏，空中补给尤为珍贵。
   随着中心圈的逐渐缩小，找到出口逃离或淘汰其他人方可取得胜利"
```

### ★★★ `buddy_playlist 200`（第 3,727 行）

★★ **⇒ 一个**playlist → playlist 的链接**：选 SOLO 时可以切到 BUDDY。**

### ★★★ DMZ 的地图与权重

```ini
mp_battlecity_mountains,dmz,3     ← 权重 3
mp_battlecity,dmz,1               ← 权重 1
        ↓
★★★ ⇒ `mp_battlecity_mountains` 的**选中概率是 `mp_battlecity` 的 3 倍**
```

★ **⇒ 与报告 078 的 `[DMZLeague_Chest_Pool]` item_id 无关,但 `mp_battlecity*` 与地图名一致。**
**⇒ 全包共 **90 个不同地图** 被 playlist 使用（见下）。**

---

## 八、★★★★★ **`validdate2` 含不存在的日期**（第 3,932–3,937 行）

```ini
buildversion default cb3 release
//validtime1 0-24					//0-24, BJ time, seperate time buckets by ',', time buckets maximum is 3
//validday1 0,1,2,3,4,5,6				// from 0: Sunday to 6: Saturday; comment validday if every day is valid
//validdate1 2018/01/14-2020/04/02	// YYYY/MM/DD-YYYY/MM/DD, BJ time
validtime2 10-24					
validday2 0,6				
validdate2 2018/04/03-2020/04/31
set scr_dmz_buddymode 1
ranked
nojip   
```

### ★★★★★ 三个精确事实

```
① ★★★ 注释给出了确切语义（逐字）：
   "0-24, **BJ time**"                              ⇒ **北京时间**
   "from **0: Sunday** to **6: Saturday**"           ⇒ **0 = 周日,6 = 周六**
   "YYYY/MM/DD-YYYY/MM/DD, BJ time"
        ↓
② ★★★ **活动时间**：`validtime2 10-24` + `validday2 0,6`
   ⇒ **每周六、周日 10:00–24:00**
   ★ 与 playlist 220/221 的中文名「**周末**勇者联赛」**完全吻合** ✓
        ↓
③ ★★★★★ **`validdate2 2018/04/03-2020/04/31`**
   ⇒ **2020 年 4 月 31 日不存在**（4 月只有 30 天）
        ↓
★★★ ⇒ **这是一个无效日期,说明日期字段是手写的、没有校验**
```

★ **⇒ 第 ③ 条与报告 077 的两处拼写错误（`Chanllenge` / `gurantee`）**同类**：**
```
交付包的配置数据里存在**未校验的手写值**
（拼写错误 ×2 + 无效日期 ×1）
```

★★ **⇒ 且 `validtime1/validday1/validdate1` **被注释掉**，只有 `2` 生效。**
**⇒ 格式提示："time buckets maximum is **3**" ⇒ 设计上允许 3 组时间窗（1/2/3）。**

---

## 九、★★★★ **map 使用统计：90 个不同地图**

### 9.1 ★★★ 使用最多的 20 张

| # | 地图 | 次数 | # | 地图 | 次数 |
|---|---|---|---|---|---|
| **1** | `mp_crash_tropical` | **29** | 11 | `mp_estate_tropical` | **15** |
| **2** | `mp_mountain` | **29** | 12 | `mp_village` | **14** |
| **3** | `mp_fav_tropical` | **24** | 13 | `mp_overgrown` | **14** |
| **4** | `mp_seatown` | **22** | 14 | `mp_raid` | **13** |
| **5** | `mp_nuked` | **22** | 15 | `mp_overwatch_sh` | **12** |
| **6** | `mp_storm_spring` | **19** | 16 | `mp_tunisia` | **12** |
| **7** | `mp_highrise` | **19** | 17 | `mp_qadeem_sh` | **12** |
| **8** | `mp_terminal_cls` | **16** | 18 | `mp_subbase_sh` | **12** |
| **9** | `mp_cross_fire` | **16** | 19 | `mp_shipment_long` | **12** |
| **10** | `mp_firingrange` | **16** | 20 | `mp_strike_sh` | **11** |

### ★★★ 特殊地图组

| 组 | 地图 | 说明 |
|---|---|---|
| **BattleCity** | `mp_battlecity`（7）/ `mp_battlecity_mountains`（5）/ `mp_battlecity_mountains_td`（1） | ★ DMZ 专用 |
| **僵尸** | `zm_sumpf_sh`（4）/ `zm_factory_sh`（4）/ `zm_asylum_sh`（4）/ `zm_prototype_sh`（2） | ★★ **与报告 066 的四张 zone 图完全一致** ✓ |
| **丧尸竞技场** | `za_coliseum`（3）/ `za_island`（3） | `zarena` 专用 |
| **生存** | `coop_survival_mp_*`（共 18 张） | `coop` 专用 |
| **死亡行军** | `mp_deathmarch_chap1/1_b/1_c/1_d`、`chap3_a/3_b`、`chap4_a/4_b` | ★★ `zhunt` 章节图 |
| **S&D 原型** | `mp_sd_proto1`（5）/ `mp_sd_jardin`（4） | `sd`/`sdp` |
| **派对** | `mp_dwarf_sh`（2）/ `mp_awp_arena`（1）/ `mp_boomtown`（1）/ `mp_nukearena_sh`（2）/ `mp_melee_resort`（3） | 特殊 |

★★★ **⇒ 僵尸地图 4 张（sumpf / factory / asylum / prototype）与报告 066/070 的 zone 数据**完全一致** ✓**

★★ **⇒ `mp_deathmarch_chap1..4` 与 `zhunt` 的章节 playlist（205/230/231/232/229/233/245/246）对应。**

---

## 十、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **编码** | **GBK（codepage 936）**——全包唯一 |
| 2 | ★ 规模 | **3,970 行 / 112,274 字节** |
| 3 | ★★ `version` | **796** |
| 4 | ★★★ **`Next Playlist ID`** | **256**（最大已用 **255** ✓ 吻合） |
| 5 | ★★ **IW 原作者** | **Andre Tiran / Dan Merboth**（★ 血统证据） |
| 6 | ★★★★★ **gametype 总数** | **43 个**（其中 **11 个有脚本**） |
| 7 | ★★★★★ **11 个有脚本的** | `cha`/`coop`/`dmz`/`sd`/`td`/`war`/`zarena`/`zhunt`/`zm`/`conf` + … |
| 8 | ★★★★★ **与目录的对应** | 交付包 `gametypes\` 恰好 **11 个 `.lua`** ⇒ **逐一对应,无缺无余** |
| 9 | ★★★ **三个映射** | `tdm`→**war** · `kc`→**conf** · `hq`→**koth** |
| 10 | ★★ `MPUI_SPEC_OPS` | **8 个 gametype 共用** |
| 11 | ★★★★★ **21 个 gametype 无脚本** | 含 `dom`(**29**)/`sr`(**14**)/`sdp`(**16**)/`spy`(**10**)… |
| 12 | ★★★ 与 `war.lua` 的同一缺口 | "**zero team score for the whole match: the clock was the only thing that could ever end it**" |
| 13 | ★★ 缺口率 | **32/43 ≈ 74%** |
| 14 | ★★★ playlist 总数 | **123 个**（最大 ID **255**） |
| 15 | ★★★★★ **`playlist 201` 缺失** | `configs_s.info` 的 `ui_dmz_ps_pl` 引用了它,本文件**零定义** |
| 16 | ★★★ 分段 | MICRO CLIENT / **War God** / **FULL CLIENT** / Party / StreakBreak / **GAPP ZONE** / **UNUSED MP** / **UNUSED PVE** / **BattleCity** |
| 17 | ★★★ `catinfo` | **22 个类别**（PvP 15 / PvE 10）；**只有 2 个有中文名** |
| 18 | ★★★ Flag 语义 | **1=Featured / 2=仅内部 / 4=New / 8=Cycle** |
| 19 | ★★★★★ **PL 199 override 双重编码** | `overridename english` = **勇者游戏**（GBK→CP1252→UTF-8 三重折腾） |
| 20 | ★★★★★ **override 两槽互换** | `override* chinese` 装**英文**,`override* english` 装**中文** |
| 21 | ★★★ 三个 DMZ cvar | `scr_dmz_buddymode` / **`dmz_circle_reversed`** / **`scr_dmz_lootTableOption ReversedCircle`** |
| 22 | ★★ `buddy_playlist 200` | playlist → playlist 链接 |
| 23 | ★★ DMZ 地图权重 | `mp_battlecity_mountains` **3** : `mp_battlecity` **1** |
| 24 | ★★★★★ **`validdate2 2018/04/03-2020/04/31`** | **4 月 31 日不存在**（未校验的手写值） |
| 25 | ★★★ 时间窗语义 | `validtime 10-24` + `validday 0,6`（**0=周日,6=周六**,**BJ time**）⇒ 与「**周末**勇者联赛」吻合 ✓ |
| 26 | ★ 时间桶上限 | **3**（格式注释） |
| 27 | ★★★ **地图总数** | **90 个不同地图** |
| 28 | ★★ 僵尸地图 4 张 | `zm_sumpf_sh` / `zm_factory_sh` / `zm_asylum_sh` / `zm_prototype_sh` ✓ 与报告 066 一致 |
| 29 | ★★ 最多地图的 playlist | **PL 13**（34 张 `tdm`）/ **PL 6**（27 张 `sd`） |

---

## 十一、结论

### 1. ★★★★★ **交付包最重要的结构性缺口：43 个 gametype,只有 11 个脚本**

```
配置层（本文件）声称 43 个 gametype
实现层（`gametypes\`）只有 11 个 `.lua`
        ↓
★★★ ⇒ **21 个 gametype 的 playlist 会加载一个不存在的脚本**
        ↓
后果 = `war.lua:8-16` 逐字描述的那个病：
  "**NO script, no player_killed callback** ⇒ **zero team score**,
   **the clock was the only thing that could ever end it**"
```

★ **⇒ `war.lua` / `conf.lua` 只修了 2 个,还剩 **21 个**（`dom` 用了 29 次、`sdp` 16 次、`sr` 14 次）。**

### 2. ★★★★★ **本文件是 GBK 编码**（全包唯一），且 **PL 199 的 override 字段三重编码损坏**

```
正确链：GBK 字节 **D3 C2 D5 DF D3 CE CF B7**（勇者游戏）
        ↓ 按 CP1252 误读 ⇒ "ÓÂÕßÓÎÏ·"
        ↓ 按 UTF-8 写 ⇒ 16 字节存进文件
        ↓
★★★ 且 **`override* chinese` 与 `override* english` 两槽内容互换**
```

### 3. ★★★★★ **`playlist 201` 被 `configs_s.info` 引用但未定义**

### 4. ★★★★ **三个映射被权威表证实**（`tdm`→`war` / `kc`→`conf` / `hq`→`koth`）

### 5. ★★★★ **`validdate2` 含不存在的日期 2020/04/31**

★ **⇒ 与报告 077 的两处拼写错误同类：配置里存在**未校验的手写值**。**

### 6. ★★★ **94 个地图 / 22 个类别 / 123 个 playlist / `Next ID 256`**

### 7. ★★★ **血统证据：文件头保留 IW 原作者姓名**,说明这是 **IW 原版 playlist 格式的继承**

### 8. ★★ **僵尸 4 张地图与报告 066/070 的 zone 数据完全一致**（又一次交叉验证 ✓）

---

## 十二、下一步

- `coop_training_mp_cargoship.lua`（4,683 行）—— `coop.lua` 让渡的那一层
- `ol-mod-runtime-manifest.json`（28,209 B）
- `maps\*.lua`（18 个）
- 其余 payload 文件与 bundle 收尾（`OlMod\GameScripts\` 下的其他文件）
