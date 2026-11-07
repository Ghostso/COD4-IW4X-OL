# 学习报告 074（重开）— `dm.lua` 全文（83 行）：两个实测 50 与仪器选择

**学习范围**：`dm.lua` 第 1–83 行（文件全文）
**性质**：全实测（**`dm.lua` 全文完成**）
**★★★ 本报告收录**XP=50 与重生=1500 两个实测的完整证据链**与**一次"仪器选择"的示范**

---

## 一、★★★★★ 自由混战的身份（第 1–8 行，逐字）

```lua
-- Free-for-all. The client books this as the playlist token "ffa"; the engine
-- gametype - and so this file's name - is "dm", which is the stock IW name.
--
-- There are no map game objects: playlist 23 carries no objective of any kind,
-- and the shipped description is "Eliminate the enemies to score. First player
-- to reach the score limit wins."
```

### ★★★★★ 三个精确的标识

| # | 项 | 值 |
|---|---|---|
| **1** | **客户端 playlist token** | **`ffa`** |
| **2** | **引擎 gametype（= 文件名）** | **`dm`**（IW 原名） |
| **3** | **playlist 号** | **23** |
| **4** | **官方描述** | **"Eliminate the enemies to score. First player to reach the score limit wins."** |

★★★ **⇒ 这是**token → gametype 映射的又一例**：**
```
`ffa`（客户端）⇒ `dm`（引擎）    ← 本报告
`kc`  （客户端）⇒ `conf`（引擎）  ← 报告 0xx
`tdm` （客户端）⇒ `war` （引擎）  ← 报告 0xx
```

★ **⇒ playlist 23 无任何 objective ⇒ 无 map game objects。**

---

## 二、★★★★★ **没有阵营**的精确后果（第 10–13 行，逐字）

```lua
-- Free-for-all has no sides. Every player is left at team None, which makes
-- issameteam false for every pair, so the only self-kill check needed is the
-- attacker not being the victim. There is deliberately no addteamscore here -
-- that is the one line that separates this from cha.
```

### ★★★★★ 完整的逻辑链

```
自由混战**没有阵营**
        ↓
★ 每个玩家都留在 **team None**
        ↓
⇒ **`issameteam` 对每一对都是 false**
        ↓
★★★ ⇒ 唯一需要的自杀检查是 **"attacker ≠ victim"**
        ↓
★★★ **故意没有 `addteamscore`**
        ↓
★★★ "that is **the one line** that separates this from `cha`"
```

★ **⇒ 这是**`dm.lua` 与 `cha.lua` 的**唯一一行差异**（团队分）。**

★★ **⇒ 与报告 069 的 `zm.lua` 呼应：`zm.lua` **有意不计分**；`dm.lua` **有意不加团队分**。**
**两者都是"故意不做某事"的明确声明。**

---

## 三、★★★★★ **两个计数器、两种单位**（第 18–24 行，逐字）

```lua
-- Two counters, in two different units, exactly as cha keeps them.
-- addscore is the DISPLAY score at 50 a kill; addkill is the one the
-- score limit reads, at 1 a kill, and is free-for-all's stand-in for
-- cha's addteamscore. The shipped limit is 30, so awarding only the
-- display score would end the match on the first kill.
-- 50 is MEASURED, not cha's 100: the retail dm server sets
-- ui_DMKillScore "50" at serverTime 0 and its score popup carries 50.
```

### ★★★★★ 两个计数器的完整对照

| 计数器 | 每击杀 | 用途 |
|---|---|---|
| **`addscore`** | **50** | ★ **显示分数** |
| **`addkill`** | **1** | ★ **比分上限读取的那个** |

★★★ **⇒ 关键：`addkill` 是 `dm` 里 `cha` 的 `addteamscore` 的**替代品**。**

### ★★★★★ "为何不能只给显示分"（逐字）

```
"The shipped limit is **30**, so awarding only the display score would
 **end the match on the first kill**."
        ↓
若只 `addscore(50)` 而 limit 读的是 addkill
        ↓
★★★ 第一次击杀就会**结束比赛**（50 > 30）
```

★ **⇒ 这是**两个计数器单位不同**的直接后果。**

### ★★★★★ **50 的实测出处**（逐字）

```
"50 is **MEASURED, not cha's 100**:
 the retail dm server sets **`ui_DMKillScore "50"`** at **serverTime 0**
 and its **score popup carries 50**."
        ↓
★★★ 两个独立证据：
  ① 零售 dm 服务器在 **serverTime 0** 设 `ui_DMKillScore = "50"`
  ② 其**分数弹窗携带 50**
        ↓
★ 且明确对比：**"not cha's 100"**（`cha` 是 100）
```

★★ **⇒ 所以 `dm` = 50，`cha` = 100 —— **两种模式不同**。**

---

## 四、★★★★★ **XP 的实测与 CODREF 双重来源**（第 30–34 行，逐字）

```lua
-- CODREF: IW4 _rank.gsc registers 50 XP for a teamless kill and 50
-- more for a headshot. CODOL's retail DM trace independently confirms
-- the 50-point base: an ordinary kill moves the AAR row XP 50 farther
-- than aarTotalBonusXP. Keep progression awards beside scoring rather
-- than deriving them later from presentation medals.
```

### ★★★★★ 双来源交叉验证

| 来源 | 内容 |
|---|---|
| **CODREF（IW4 `_rank.gsc`）** | **无阵营击杀 50 XP** + **爆头再加 50** |
| **CODOL 零售 DM trace** | ★★ **独立确认**：普通击杀让 **AAR 行 XP 前进 50** |

★★★ **⇒ 两个**完全独立**的来源给出同一数值 ⇒ 可信度极高。**

★★ **⇒ 且给了**架构理由**（逐字）：**
```
"Keep progression awards **beside scoring** rather than deriving them later
 from **presentation medals**."
        ↓
★ 进度奖励**紧邻计分代码**，不要以后从"展示用奖章"反推
```

### ★★★ 爆头的 **两个** `hit_location` 值（第 40 行）

```lua
if event.hit_location == 1 or event.hit_location == 2 then
```

★★ **⇒ 爆头 = `hit_location == 1` **或** `== 2`（两个值）。**

★ **⇒ `dmz.lua` 完全照抄这一行（报告 073 已记录）。**

### ★★★ 四个 API 调用

```lua
codol.player(event.attacker_entity_num)          ← 取 attacker 对象
codol.call("method:addscore", attacker, 50)      ← 显示分 50
codol.call("method:addxp",    attacker, 50)      ← XP 50
codol.call("method:addxp",    attacker, 50)      ← 爆头再 50（条件）
codol.call("method:addkill",  attacker, 1)       ← 击杀数 1
```

★★ **⇒ 与 `dmz.lua` **逐字节相同**（除了注释）。**

---

## 五、★★★★★ **重生延迟 1500 的完整实测**（第 55–76 行，逐字）

```lua
-- 1500 IS MEASURED. C-2021-7-25[1-19-26]dm.demo, mp_cross_fire, 8 clients: the recording
-- client's playerState pm_type goes 0 -> 8 on death and 8 -> 0 when it is controllable
-- again, and across the whole match that gap is
--     n=24   min 1500   p25 1500   median 1500   p75 1500   max 1600
-- with 23 of the 24 at exactly 1500. The single 1600 is one serverTime step; this demo's
-- snapshots are 100 ms apart. p25 == median == p75, so it is a constant, not a computation.
--
-- 3000 WAS INVENTED and it was twice too slow.
```

### ★★★★★ 完整的统计表

| 统计量 | 值 |
|---|---|
| **样本数 n** | **24** |
| **min** | **1500** |
| **p25** | **1500** |
| **median** | **1500** |
| **p75** | **1500** |
| **max** | **1600** |
| **恰好等于 1500 的** | ★ **24 个中的 23 个** |

★★★ **⇒ 四个统计量完全相同（p25 = median = p75）⇒ **是常量，不是计算**（逐字："it is a constant, not a computation"）。**

★★ **⇒ 唯一的 1600 是**一个 serverTime 步长**（本 demo 快照间隔 **100 ms**）。**

★ **⇒ 出处：`C-2021-7-25[1-19-26]dm.demo`，地图 `mp_cross_fire`，**8 个客户端**。**

### ★★★ **状态变量：`pm_type`**

```
死亡时：`pm_type` **0 → 8**
可再次操作时：**8 → 0**
        ↓
★ 整场比赛的这个间隔 = 重生延迟
```

★★★ **⇒ 旧值 **3000** 是**发明的，且慢了一倍**（逐字："3000 WAS INVENTED and it was
twice too slow"）。**

---

## 六、★★★★★ **仪器选择的完整示范**（第 64–69 行，逐字）

```lua
-- MEASURED ON pm_type, NOT ON THE UI VERB, and the difference matters. The first pass timed
-- `u 10` (death screen) to `u 11` (alive) and got median 1500 with a tail to 2500 -- which
-- reads as "1500 plus something unidentified". It is not: that window also encloses the
-- killcam, so it measures when the SCREEN closes. pm_type is the engine's own movement state
-- and is what decides whether the player can move. Two instruments disagreed on the first
-- death (1500 vs 2200) and the one that actually wraps the quantity won.
```

### ★★★★★ 两台"仪器"的完整对照

| 仪器 | 测量窗口 | 结果 | 问题 |
|---|---|---|---|
| **`u 10` → `u 11`** | 死亡屏 → 活着 | median **1500**，但**尾巴到 2500** | ★★★ **窗口也包含 killcam** ⇒ 测的是**屏幕何时关闭** |
| **`pm_type` 0→8→0** | 引擎自身移动状态 | **1500**（23/24 精确） | ★ 引擎决定玩家**能否移动**的那个量 |

★★★ **⇒ 关键结论（逐字）：**
```
"`pm_type` is **the engine's own movement state** and is
 **what decides whether the player can move**.
 Two instruments **disagreed on the first death (1500 vs 2200)**
 and **the one that actually wraps the quantity won**."
        ↓
★ 判据：**哪台仪器真正"包裹"了所要测的量**
```

★ **⇒ 两条可证伪的错误读数：**
```
① `u 10` → `u 11`：median 1500 但**尾巴到 2500**
   ⇒ 误读成"1500 加上某个未识别的东西"
   ⇒ 真相：**窗口里还有 killcam**
② 首次死亡：两台仪器**分歧**（**1500 vs 2200**）
```

★★ **⇒ 这是一个**方法论级别的示范**：**
```
★ 测"死亡到可控"时，必须选**引擎内部决定可控性的那个变量**
  （`pm_type`），而不是**UI 层的事件**（`u 10`/`u 11`）
```

---

## 七、★★★★★ **明确的未测项与语料限制**（第 71–74 行，逐字）

```lua
-- STILL UNMEASURED: whether this varies with anything -- gametype, player count, killcam on
-- or off. One 8-player mp_cross_fire match cannot say, and it is the ONLY dm demo in the
-- 84-demo corpus. dmz cannot stand in for it: that is BATTLE ROYALE (playlist 199,
-- "BattleCity - SOLO"), and a single-life mode has no respawn delay to compare against.
```

### ★★★★★ 三个精确的语料事实

| # | 项 | 值 |
|---|---|---|
| **1** | 未测项 | 是否随 **gametype / 玩家数 / killcam 开关** 变化 |
| **2** | ★★ **整个语料里唯一的 dm demo** | **84 个 demo 语料中的 1 个** |
| **3** | ★★★ **`dmz` 不能替代** | 它是 **BATTLE ROYALE**（**playlist 199**，"**BattleCity - SOLO**"），**单命模式没有重生延迟** |

★★★ **⇒ 第 3 条是**逻辑闭环**：**
```
想用 `dmz` 的 demo 补样本
        ↓
★ 但 `dmz` 是**单命模式**
        ↓
★★★ **根本没有重生延迟可测**
        ↓
⇒ 不能替代
```

★ **⇒ 第 2 条给出语料的**精确定量**：**84 个 demo**，其中 dm **只有 1 个**。**

★★ **⇒ 与报告 073 呼应：`dmz` 的 playlist 号是 **199**。**
```
`dm`  = playlist **23**
`dmz` = playlist **199**
```

---

## 八、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ 三个标识 | token **`ffa`** / gametype **`dm`** / playlist **23** |
| 2 | ★ 官方描述 | "Eliminate the enemies to score. First player to reach the score limit wins." |
| 3 | ★★★ **无阵营后果** | 全员 team None ⇒ `issameteam` 全 false ⇒ 只需查 attacker ≠ victim |
| 4 | ★★★★★ **与 `cha` 的唯一差异** | **故意没有 `addteamscore`**（"the one line"） |
| 5 | ★★★★★ **两个计数器** | `addscore` **50**（显示）/ `addkill` **1**（**上限读取**） |
| 6 | ★ 比分上限 | **30** ⇒ 只给显示分会**第一杀就结束** |
| 7 | ★★★★ **50 的实测** | 零售 dm 在 **serverTime 0** 设 **`ui_DMKillScore "50"`**；弹窗 50；**不是 cha 的 100** |
| 8 | ★★★★★ **XP 双来源** | **CODREF** IW4 `_rank.gsc`（50+50）+ **CODOL 零售 DM trace 独立确认** |
| 9 | ★ 架构建议 | 进度奖励**紧邻计分**，不从展示奖章反推 |
| 10 | ★★ 爆头判据 | **`hit_location == 1 或 2`** |
| 11 | ★★★★★ **重生实测** | n=**24**，**23 个精确 1500**，p25=median=p75 ⇒ **是常量** |
| 12 | ★ 唯一异常 | max **1600** = **一个 serverTime 步长**（快照 **100 ms**） |
| 13 | ★ 出处 | **`C-2021-7-25[1-19-26]dm.demo`** / `mp_cross_fire` / **8 客户端** |
| 14 | ★★★ 状态变量 | **`pm_type` 0 → 8（死）→ 0（可控）** |
| 15 | ★★★ 旧值 | **3000 是发明的，慢了一倍** |
| 16 | ★★★★★ **仪器选择** | `u 10`→`u 11` 窗口**含 killcam** ⇒ 测的是屏幕关闭 |
| 17 | ★★ 判据 | **"the one that actually wraps the quantity won"** |
| 18 | ★ 首次死亡分歧 | **1500 vs 2200** |
| 19 | ★★★ 未测项 | gametype / 玩家数 / killcam 开关 |
| 20 | ★★★★ 语料限制 | **84 个 demo 中 dm 只有 1 个** |
| 21 | ★★★★★ **dmz 不能替代** | **playlist 199 / BattleCity - SOLO / 单命** ⇒ **无重生延迟可比** |
| 22 | ★ `codol_friendly_fire_mode` | **0** |

---

## 九、结论

### 1. ★★★★★ **两个数值都有完整证据链**（50 XP / 1500 ms）

```
50 XP：CODREF IW4 `_rank.gsc` + CODOL 零售 trace **独立确认**
50 分：零售 dm 在 serverTime 0 设 `ui_DMKillScore "50"`
1500：`pm_type` 统计 n=24，**23 个精确 1500**，p25=median=p75
```

### 2. ★★★★★ **仪器选择示范**（`pm_type` 胜 `u 10`/`u 11`）

★ **⇒ 判据："the one that actually **wraps the quantity** won"。**

### 3. ★★★★★ **`dm.lua` 与 `cha.lua` 的唯一一行差异是 `addteamscore`**

### 4. ★★★★ **两个计数器两种单位**（显示 50 / 上限读取 1）

★ **⇒ 上限是 30 ⇒ 只给显示分会第一杀结束。**

### 5. ★★★★ **语料限制被精确量化**（84 个 demo 中 dm 只 1 个；`dmz` 是单命不可替代）

### 6. ★★★ **旧值 3000 是发明的，慢一倍**

---

## 十、下一步

- `war.lua`（120 行）/ `conf.lua`（123 行）/ `td.lua`（67 行）
- `configs_s.info`（1,067 行）
- `mp_playlists_shipRetail_release.info`（3,970 行）
- `coop_training_mp_cargoship.lua`（4,683 行）
