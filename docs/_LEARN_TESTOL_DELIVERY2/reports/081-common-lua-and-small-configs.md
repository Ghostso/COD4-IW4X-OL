# 学习报告 081（重开）— `common.lua` + Alwaysoffline 小配置 + `market_ui.info` 解压

**学习范围**：`OlMod\GameScripts\common.lua`（2,866 B）+ `Alwaysoffline\` 下 10 个小配置文件
**性质**：全实测（**发现 `common.lua` 是家族级伤害处理器,发现 `market_ui.info` 是 zlib 压缩**）
**★★★★★ 本报告收录四个重大发现**：①**`codol_friendly_fire_mode` 四值的实现处在 `common.lua`** ②**`market_ui.info` 是 zlib 压缩（全包唯一）** ③**三份 `supply_drop` 配置版本不同** ④**`Identity.json` 就是显示名载体**

---

## 一、★★★★★ `common.lua`（2,866 B / 82 行）——**家族级伤害处理器**

### 1.1 ★★★★★ **`codol_friendly_fire_mode` 四值的实现处就在这里**

```lua
assert(codol.on("player_damage", function(player, event)
    local inflictor = entity_reference(event.inflictor_entity_num)
    local attacker = entity_reference(event.attacker_entity_num)
    local damage_target = player
    local damage = event.damage
    local builtin = "method:finishplayerdamage"
    local shared_target = nil

    if event.attacker_entity_num ~= nil and
        event.attacker_entity_num ~= event.target_client_num then
        local attacker_player = codol.player(event.attacker_entity_num)
        local same_team, team_error = codol.call(
            "method:issameteam", player, attacker_player)
        if team_error == nil and same_team then
            local mode = codol_friendly_fire_mode
            if mode == 0 then
                return
            elseif mode == 1 then
                damage_target = player
            elseif mode == 2 then
                damage_target = attacker_player
                damage = math.max(1, math.floor(damage * 0.5))
            elseif mode == 3 then
                builtin = "method:finishsharedplayerdamage"
                shared_target = attacker_player
                damage = math.max(1, math.floor(damage * 0.5))
            else
                print("player_damage deferred", "invalid friendly-fire mode", mode)
                return
            end
        end
    end
    ...
end))
```

### ★★★★★ 完整的四值实现（**这是报告 076 悬而未决点的答案**）

| mode | 行为 | 目标 | 伤害 | 用的 builtin |
|---|---|---|---|---|
| **0** | ★ **直接 `return`**（不伤害） | — | — | — |
| **1** | `damage_target = player` | ★ **受害者** | 原值 | `finishplayerdamage` |
| **2** | `damage_target = attacker_player` | ★★ **攻击者**（**反射**） | **`max(1, floor(damage × 0.5))`** | `finishplayerdamage` |
| **3** | `shared_target = attacker_player` | ★★★ **受害者 + 攻击者** | **`max(1, floor(damage × 0.5))`** | ★ **`finishsharedplayerdamage`** |
| 其他 | ★ **`print` 后 `return`** | — | — | — |

★★★ **⇒ 与 `sd.lua:331` 的注释**逐字对应**：**
```
`sd.lua` 注释："CODOL/COD team modes use
 **0=no damage, 1=target, 2=half reflect, 3=half shared**"
        ↓
`common.lua` 实现：
  **0** ⇒ 无伤害 ✓
  **1** ⇒ `damage_target = player`（**target**）✓
  **2** ⇒ `damage_target = attacker_player` + **×0.5**（**half reflect**）✓
  **3** ⇒ `finishsharedplayerdamage` + **×0.5**（**half shared**）✓
        ↓
★★★★★ ⇒ **注释与实现完全一致,四个语义被独立证实** ✓
```

★★ **⇒ 且**只有队友之间**才进入这个开关（`issameteam == true`）⇒ 敌人伤害永远按原值走。**
**⇒ 若无 `codol_friendly_fire_mode` 变量 ⇒ `mode == nil` ⇒ 落到 `else` ⇒ **打印"invalid friendly-fire mode" 并忽略伤害**（★ fail-closed）。****

### 1.2 ★★★★★ **`codol_friendly_fire_mode` 是"gametype 层声明、common 层消费"**

```
11 个 gametype 文件：`codol_friendly_fire_mode = 0`（**全部 = 0**）
        ↓
`common.lua`（家族级,所有 gametype 共享）：**读这个变量并执行**
        ↓
★★★ ⇒ **`common.lua` 才是 4 种友军伤害模式的唯一实现处**
   gametype 文件只是**声明选择**
```

★ **⇒ 这解释了为什么 11 个文件都写 `= 0`：**它们只是把默认值设为"无友军伤害"。****

### 1.3 ★★★★★ `player_damage` 事件的**完整字段表**（第一次被完整列出）

```lua
event.inflictor_entity_num      -- ★ 施加实体
event.attacker_entity_num       -- ★ 攻击者实体
event.target_client_num         -- ★ 目标客户端号
event.damage                    -- ★ 伤害值
event.damage_flags              -- ★★ 伤害标志
event.method_of_death           -- ★★ 死亡方式
event.weapon_asset_index        -- ★★ 武器资产索引
event.point                     -- ★★ 命中点（向量）
event.direction                 -- ★★ 方向（向量）
event.hit_location              -- ★★ 命中部位（与 `hit_location == 1/2` 的爆头判据同源）
event.time_offset               -- ★★ 时间偏移
event.bone_index                -- ★★ 骨骼索引
```

★★★ **⇒ **12 个字段**,其中 `hit_location` 就是 `dm.lua` / `war.lua` / `conf.lua` 用的爆头判据。**
**⇒ 且 `damage_flags` / `method_of_death` / `weapon_asset_index` / `point` / `direction` /
`time_offset` / `bone_index` 是**首次出现**的字段名。**

### 1.4 ★★★★★ 两个 builtin 的**参数签名**

```lua
-- mode 0/1/2（无 shared_target）
codol.call(builtin,                 -- "method:finishplayerdamage"
    damage_target,
    inflictor,
    attacker,
    damage,
    event.damage_flags,
    event.method_of_death,
    event.weapon_asset_index,
    event.point,
    event.direction,
    event.hit_location,
    event.time_offset,
    event.bone_index)               -- ★ 12 个参数

-- mode 3（有 shared_target）
codol.call(builtin,                 -- "method:finishsharedplayerdamage"
    damage_target,
    shared_target,                  -- ★★ 多出来的第二个参数
    inflictor,
    attacker,
    damage,
    event.damage_flags,
    event.method_of_death,
    event.weapon_asset_index,
    event.point,
    event.direction,
    event.hit_location,
    event.time_offset,
    event.bone_index)               -- ★ 13 个参数
```

★★★ **⇒ 与报告 080 的 `coop_training_mp_cargoship.lua` 对照：**
```
报告 080：`finishplayerdamage(player, nil, nil, 1000, 0, 16, 165,
                              nil, {0,0,1}, 0, 0, 0)` ← **11 个参数**
本报告：  `finishplayerdamage(target, inflictor, attacker, damage,
                              damage_flags, mod, weapon, point, direction,
                              hitloc, time_offset, bone_index)` ← **12 个参数**
        ↓
★★★ ⇒ **差一个参数！**
   ⇒ 报告 080 的调用把 `inflictor` 与 `attacker` **合并成了 nil,nil** 但少了一个
   ⇒ ★ 实际是：报告 080 的 11 参 = `player, nil, nil, 1000, 0, 16, 165, nil, {0,0,1}, 0, 0, 0`
     数一下：player(1) nil(2) nil(3) 1000(4) 0(5) 16(6) 165(7) nil(8) {0,0,1}(9) 0(10) 0(11) 0(12)
   ⇒ ★★★ **其实是 12 个,我先前数错了**（把 {0,0,1} 当成了一个参数但漏数了一个 0）
```

★★ **⇒ 以本报告为准：`finishplayerdamage` 有 **12 个参数**（含 target）。**
**⇒ `finishsharedplayerdamage` 有 **13 个**（多 `shared_target`）。**

### 1.5 ★★★ `entity_reference` 的 nil 守卫（第 1–6 行）

```lua
local function entity_reference(entity_num)
    if entity_num == nil then
        return nil
    end
    return codol.entity(entity_num)
end
```

★★ **⇒ `codol.entity(n)` 是**第四个** `codol.*` 访问器（继 `codol.call` / `codol.on` / `codol.player` 之后）。**

### 1.6 ★★ 两个 `TODO(CODOL)`（明确的未实现）

```lua
-- TODO(CODOL): apply native no-protection and producer-specific
-- exemptions once those damage flags and event classes are restored.
...
-- TODO(CODOL): last stand and producer-specific protection branches
-- remain fail-closed until their native state owners are restored.
```

★★★ **⇒ 两条明确声明：**
```
① **原生的"无保护"与"生产者专属豁免"尚未实现**
② ★★ **"last stand"（濒死反击）与"生产者专属保护"分支保持 fail-closed**
   —— 直到它们的**原生状态所有者被恢复**
```

★ **⇒ 第 ② 条证实了"fail-closed"是一个**刻意的设计选择**（宁可不错,不可错杀）。**
**⇒ 与报告 069 的 `zm.lua` 的"fail-closed"和报告 067 的 zone 暂停**同类**。****

### 1.7 ★★★★★ `common.lua` 在 Lua 契约中的位置

```
`conf.lua`（第 5–7 行）逐字：
  "The loader takes the gametype by string -
   **common.lua + gametypes/<gametype>.lua + maps/<map>.lua**
   (`sv_script_source_mp.cpp:144-146`)"
        ↓
★★★ ⇒ 三者**拼接**成一次 gameplay source
        ↓
`common.lua`（**家族级,所有模式共享**）
  + `gametypes/<gt>.lua`（模式层,11 个）
  + `maps/<map>.lua`（地图层,18 个小的 + 1 个大战役的）
```

★ **⇒ `common.lua` 只有 **82 行** 且**只注册一个事件**（`player_damage`）⇒ 它是**最小共享层**。**

---

## 二、★★★★★ `Alwaysoffline\` 的 10 个小配置文件

### 2.1 ★★★★★ `Identity.json`（34 B）——**显示名的载体**

```json
{
  "username": "Alwaysoffline"
}
```

★★★ **⇒ 这就是**玩家显示名**的载体！**

★ **⇒ 与报告 048–050 的 `force_display_name.py` 呼应：**
```
`force_display_name.py`（19,288 B）尝试 **5 条通道**改变显示名,全部失败：
  ① ticket+33 ② extra_data.username（b64）③ **Identity.json displayName**
  ④ TCLS 共享内存（1,517 MB 扫描,**0 命中**）⑤ Platformwrapper（无名字槽）
        ↓
★★★ 而本文件是 `{"username": "Alwaysoffline"}` —— 字段名是 **`username`**
   而不是 `displayName`！
        ↓
★ 可能解释：**该脚本找的字段名不对**（`displayName` vs `username`）
```

★★ **⇒ 这是一个**新的可验证假设**（但**未实测**，仅记录为线索）。**
**⇒ 文件只有 **34 字节**，是全包最小的 JSON。**

### 2.2 ★★★★★ `market_ui.info`（2,010 B）——**zlib 压缩**（全包唯一）

```powershell
首 64 字节： 78 DA 75 58 5D 6F 1D 35 10 7D DF 1F 83 3C E3 6F A4 7D 40 6D 10 12 ...
字节值分布：**256 / 256 全部出现**（满熵）
可打印 ASCII 比例：**37.1%**
        ↓
★★★ 首两字节 **`78 DA`** = **zlib 头**
   （CMF=0x78 ⇒ deflate + 32K 窗口；FLG=0xDA ⇒ 无预设字典）
        ↓
★★★★★ 用 `System.IO.Compression.ZLibStream` 解压 ⇒
   **2,010 字节 → 6,669 字节**（膨胀 **3.3 倍**）
```

★★★ **⇒ 全包**唯一一个压缩的配置文件**（其他 `.info` / `.json` 都是纯文本）。**

★ **⇒ 而文件名是 `.info`（与未压缩的 `sku_tags.info` 同后缀）⇒ **后缀不暗示压缩**。**
**⇒ 任何按文本读它的工具都会看到乱码（我最初也以为是加密）。**

### 2.3 ★★★★★ **三份 `supply_drop` 配置的版本差异**

| 文件 | 大小 | **`supply_drop_version`** | 压缩？ |
|---|---|---|---|
| **`configs_s.info`** | **26,249 B** | ★ **`260.35`** | 否 |
| **`sku_tags.info`** | **3,520 B** | ★ **`337.0`** | 否 |
| **`market_ui.info`** | **2,010 B**（解压 6,669 B） | ★★★ **`361.0`** | ★ ★ **是（zlib）** |

★★★★★ **⇒ 同一份配置有三个版本,`market_ui.info` 最新、`configs_s.info` 最旧。**

★ **⇒ 而三份的 **`[tags]` 榜单内容不同**：**
```
`sku_tags.info`   HOT:1 = **45542**
`market_ui.info`  HOT:1 = **45137**
        ↓
★★★ ⇒ **推荐位在两次发布之间被换过**
```

★★★ **⇒ 且 `sample` 数量差异巨大：**
```
`configs_s.info`   60216 有 **12** 个 sample
`sku_tags.info`    60216 有 **151** 个（0..150）
`market_ui.info`   60216 有 **218** 个（0..217）+ 60217 **27** 个 + 11861 **27** 个
        ↓
★★★ ⇒ **`market_ui.info` 是最完整的候选池**
```

### ★★★★★ `market_ui.info` 解压后的**四个 section**（比另两份都多）

| section | 内容 |
|---|---|
| `[tags]` | **40** 项（HOT/NEW/POPULAR/RECOMMEND × 10） |
| `[supply_drop_list]` | `0=60216` / `1=60217` / `2=11861` |
| `[supply_drop_info]` | `supply_drop_version=**361.0**` + 三种箱的 SlotCount/DustSKU/DustRequirement |
| `[supply_drop_samples]` | **60216×218** + **60217×27** + **11861×27** |
| **`[supply_drop_featured]`** | ★ `60217_FeaturedEnabled=1` / **`60217_EarnSlotCount=25`**（`configs_s.info` 是 **60**） |
| ★★★ **`[supply_drop_showoff]`** | ★★ **另两份都没有的新 section**（57 项） |

★★ **⇒ `[supply_drop_showoff]` 的格式是**三段数字**：`27948_0_0`（vs 普通 sample 的 `10070_0`）。**

### ★★★★★ 道具后缀标志（首次完整记录）

```ini
60217_0=27948_0_**FEATURED**
60217_2=15765_0_**NEW|RECOMMENDED**
60217_3=18009_0_**NEW**
60217_11=15773_0               ← 无后缀
60217_5=**0_22709**_NEW        ← ★★ 格式不同（两个数字在前）
```

★★★ **⇒ 观察到**四种后缀**：**
```
（无） / **NEW** / **FEATURED** / **NEW|RECOMMENDED**（用 `|` 组合）
```

★ **⇒ 且 `60217_5=0_22709_NEW` 是**格式异常**（`<sku>_<item>` 换位 ⇒ `0_22709`）**
**⇒ 可能是"物品 22709 而 SKU 为 0"（即非 SKU 来源）。**

### 2.4 ★★★ 其余七个小文件

| 文件 | 大小 | 内容 |
|---|---|---|
| **`activities_v1.info`** | **2 B** | ★ **只有两个空格**（空配置） |
| **`selected_playlist.txt`** | **17 B** | ★★ **`Original Playlist`**（单行文本） |
| **`broadcast.info`** | **23 B** | `<MSG T=**1570255261**,P=0/>` |
| **`market-down.info`** | **90 B** | `[Market] update=1 / onetimefetch=1 / starttime=**1569560400** / endtime=**1569562200** / interval=600` |
| **`whitelist_tester.info`** | **93 B** | `[Whitelist]` **3 个 userid** |
| **`tlogconfig.info`** | **154 B** | `[TLog]` 11 项 |
| **`daily_challenge_config.info`** | **0 B** | ★ 空文件 |
| **`MOTD.info`** | **0 B** | ★ 空文件 |

### ★★★★★ 时间戳解码

| 文件 | 原值 | **UTC** | **北京** |
|---|---|---|---|
| `broadcast.info` | **1570255261** | 2019-10-05 06:01:01 | **2019-10-05 14:01:01** |
| `market-down.info` | **1569560400** | 2019-09-27 05:00:00 | **2019-09-27 13:00:00** |
| `market-down.info` | **1569562200** | 2019-09-27 05:30:00 | **2019-09-27 13:30:00** |

★★★ **⇒ `market-down.info` 的窗口只有 **1,800 秒 = 30 分钟**（2019-09-27 13:00–13:30 北京）。**
**⇒ 即：市场只停用半小时 ⇒ 这是一个**短时维护窗口**,不是永久下线。**
**⇒ 而 `interval=600`（10 分钟轮询一次）。**

### ★★★ `whitelist_tester.info` 的三个 userid

```ini
[Whitelist]
userid=4503607658266846
userid=11376448412308544053
userid=5655630139569513483
```

★★ **⇒ 三个测试者账号（★ 第三个 **5,655,630,139,569,513,483** 与记忆里的
"`userid=5655630139569513483`" 可能相关）。**

★ **⇒ 第一个 **4,503,607,658,266,846** 是一个**小于 2^53** 的数（精确可表示）。**

### ★★★ `tlogconfig.info` 的 11 项

```ini
[TLog]
uiclickcount=0
uiclick=0
uipage=1
uilastpages=0
dwdsmm_number=30
dwdsmm_initvalue=50
dwdsmm_slope=1.9
loadoutchangeevent=0
uipage_limit=30
```

★★ **⇒ 只有 **9 项**（不是 11）；`dwdsmm_*` 是三参数的一条**线性模型**：**
```
`dwdsmm_number=30` / `dwdsmm_initvalue=50` / `dwdsmm_slope=1.9`
        ↓
★★★ ⇒ 可能是"**采样数 30、初值 50、斜率 1.9**"的上报节流曲线
```

---

## 三、★★★★★ **`bundle\re-auth.out.log`（0 字节）**

★ **⇒ 一个**空日志文件**（上次运行的遗留,或占位）。**
**⇒ 与报告 073 的 `dmz.lua` 记录的"新 run 的 kit 带着上一轮的日志"同类现象。****

---

## 四、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **`common.lua` 的作用** | **家族级 `player_damage` 处理器**（**所有 gametype 共享**） |
| 2 | ★★★★★ **`codol_friendly_fire_mode` 的实现处** | ★ **就在这里**（4 值全部实现） |
| 3 | ★★★ **四值对照** | **0**=return / **1**=target / **2**=`attacker_player`+×0.5 / **3**=`finishsharedplayerdamage`+×0.5 |
| 4 | ★★★★★ 与 `sd.lua:331` 注释 | ★ **"0=no damage, 1=target, 2=half reflect, 3=half shared"** ⇒ **实现与注释完全一致** ✓ |
| 5 | ★★ 前提 | 只对 **`issameteam == true`**（队友）生效 |
| 6 | ★★★ 无变量时 | 落 `else` ⇒ **打印 "invalid friendly-fire mode" 并忽略伤害**（fail-closed） |
| 7 | ★★★★★ **`player_damage` 12 字段** | `inflictor_entity_num`/`attacker_entity_num`/`target_client_num`/`damage`/**`damage_flags`**/**`method_of_death`**/**`weapon_asset_index`**/**`point`**/**`direction`**/**`hit_location`**/**`time_offset`**/**`bone_index`** |
| 8 | ★★★ `finishplayerdamage` 参数数 | **12 个**（含 target） |
| 9 | ★★★ `finishsharedplayerdamage` | **13 个**（多 `shared_target`） |
| 10 | ★★ `codol.entity(n)` | **第四个访问器**（`call`/`on`/`player`/`entity`） |
| 11 | ★★ **两个 `TODO(CODOL)`** | ① 原生无保护/生产者豁免未实现 ② **last stand 与生产者保护保持 fail-closed** |
| 12 | ★★★★★ **`Identity.json`** | `{"username": "**Alwaysoffline**"}` ⇒ ★ **显示名载体,字段名是 `username`（不是 `displayName`）** |
| 13 | ★★★★★ **`market_ui.info`** | ★★ **zlib 压缩**（首字节 **`78 DA`**）⇒ **2,010 → 6,669 字节** |
| 14 | ★★★ 熵证据 | **256/256 字节值全出现**,可打印 ASCII **37.1%** |
| 15 | ★★★ 命名陷阱 | 后缀 `.info` **不暗示压缩** ⇒ 与未压缩的 `sku_tags.info` 同名式 |
| 16 | ★★★★★ **三份版本** | `configs_s.info`=**260.35** / `sku_tags.info`=**337.0** / `market_ui.info`=**361.0** |
| 17 | ★★★ 榜单不同 | `sku_tags` HOT:1=**45542** vs `market_ui` HOT:1=**45137** |
| 18 | ★★★ sample 数量 | `configs_s`=**12** / `sku_tags`=**151** / `market_ui`=**272 总和** |
| 19 | ★★★★ **`[supply_drop_showoff]`** | ★ **只在 `market_ui.info` 里**（另两份没有） |
| 20 | ★★ `EarnSlotCount` | `configs_s`=**60** vs `market_ui`=**25** |
| 21 | ★★★★★ **四种后缀** | （无）/ **`NEW`** / **`FEATURED`** / **`NEW|RECOMMENDED`** |
| 22 | ★ 格式异常 | `60217_5=**0_22709**_NEW`（数字顺序与多数不同） |
| 23 | ★★★ `selected_playlist.txt` | **`Original Playlist`** |
| 24 | ★★★ `broadcast.info` | `<MSG T=**1570255261**,P=0/>` ⇒ **2019-10-05 14:01:01 北京** |
| 25 | ★★★★ **`market-down.info`** | 窗口 **2019-09-27 13:00–13:30 北京**（**只 30 分钟**） |
| 26 | ★★ `interval` | **600**（10 分钟） |
| 27 | ★★ **`whitelist_tester.info`** | **3 个 userid**（4503607658266846 / 11376448412308544053 / 5655630139569513483） |
| 28 | ★ `tlogconfig.info` | **9 项**,含 `dwdsmm_number=30` / `initvalue=50` / **`slope=1.9`** |
| 29 | ★★ **两个空文件** | **`daily_challenge_config.info`** / **`MOTD.info`**（**0 字节**） |
| 30 | ★ `activities_v1.info` | **只有两个空格**（2 字节） |
| 31 | ★ `bundle\re-auth.out.log` | **0 字节** |

---

## 五、结论

### 1. ★★★★★ **`common.lua` 是 `codol_friendly_fire_mode` 的唯一实现处**

```
11 个 gametype 文件只**声明** `codol_friendly_fire_mode = 0`
        ↓
`common.lua`（82 行,所有 gametype 共享的家族层）**读它并执行四种行为**
        ↓
★ 且**实现与 `sd.lua:331` 的注释逐字一致** ⇒ 四值语义被独立证实 ✓
```

★ **⇒ 这是**"声明在模式层、实现在家族层"的清晰分层**（与报告 076 的 FAIL-SOFT 问题形成对比）。**

### 2. ★★★★★ **`market_ui.info` 是 zlib 压缩的**（全包唯一）

```
首字节 **78 DA** = zlib 头
        ↓
2,010 字节 → **6,669 字节**（3.3 倍）
        ↓
★★★ 而文件名后缀是 `.info`（与未压缩的 `sku_tags.info` 同式）
   ⇒ **后缀不暗示压缩** ⇒ 是"按文本读会乱码"的陷阱
```

### 3. ★★★★★ **同一份 `supply_drop` 配置有三个版本**（260.35 / 337.0 / 361.0）

★ **⇒ 且**榜单内容不同**（HOT:1 = 45542 vs 45137）、**sample 数量差 22 倍**。**
**★ ⇒ `market_ui.info` 是最新且最完整的一份。**

### 4. ★★★★★ **`Identity.json` 的字段名是 `username`**（不是 `displayName`）

★ **⇒ 这对 `force_display_name.py` 的第三条通道（它找 `displayName`）是一个**新的可验证假设**。**

### 5. ★★★★ **`player_damage` 事件的 12 字段表**与两个 builtin 的 12/13 参签名

### 6. ★★★ **`market-down.info` 只是 30 分钟维护窗口**（2019-09-27 13:00–13:30 北京）

### 7. ★★★ **`common.lua` 有两个明确的 `TODO(CODOL)`**,其中 last stand 分支**刻意 fail-closed**

### 8. ★★ **两个 0 字节文件**（`daily_challenge_config.info` / `MOTD.info`）+ 一个只有空格的（`activities_v1.info`）

---

## 六、下一步

- `payload\Ayria\ol-mod-runtime-manifest.json`（28,209 B）
- 五个尚未覆盖的 PE 二进制：**`Injector32.exe`（126,464 B）/ `Bootstrapper32.dll`（159,744 B）/
  `ol_room_owner.exe`（283,648 B）/ `Localnetworking.Ayria32`（519,168 B）/
  `Platformwrapper.Ayria32`（543,232 B）**
- `enemy_recorded_path_by_spawner`（第 2542–3765 行,1,224 行）
- `bundle\` 侧剩余（`_leaf2_chain.pem` / `_ca.pem` / `_leaf2.key` 已在 051 覆盖）
- 其余 `maps\*.lua` 的逐个确认（18 个小文件已在 054 覆盖）
