# 学习报告 075（重开）— `war.lua`（121 行）与 `conf.lua`（124 行）：团队分与重建边界

**学习范围**：`war.lua` 第 1–121 行 + `conf.lua` 第 1–124 行（两文件全文）
**性质**：全实测（**两文件全文完成**）
**★★★ 本报告收录**"引擎自己不加团队分"的完整论证**、**kill confirmed 的重建边界**、以及**两处头注释与正文矛盾**

---

## 一、★★★★★ **为什么 `war.lua` 必须存在**（第 8–16 行，逐字）

```lua
-- WHY THIS FILE EXISTS AT ALL. war is a TEAM mode, so its limit is read from the
-- TEAM score: sv_main_mp.cpp:2944-2955 evaluateMatchLimits() compares
-- clients_.teamScore(Tf/Sc) against rules.scoreLimit, and only
-- addTeamScoreForClient()/addKillForClient() ever call it. Nothing in the engine
-- awards team score on its own - a gametype script has to. Before this file the
-- directory held cha/coop/dm/dmz/sd/td/zm/zhunt/zarena and the loader takes the
-- name by string (sv_script_source_mp.cpp:143-147), so war had NO script, no
-- player_killed callback, and therefore zero team score for the whole match:
-- the clock was the only thing that could ever end it.
```

### ★★★★★ 完整的因果链

```
`war` 是**团队模式** ⇒ 其上限从**团队分**读
        ↓
`evaluateMatchLimits()`（`sv_main_mp.cpp:2944-2955`）
  比较 `clients_.teamScore(Tf/Sc)` 与 `rules.scoreLimit`
        ↓
★ 且**只有** `addTeamScoreForClient()` / `addKillForClient()` 会调用它
        ↓
★★★ **"Nothing in the engine awards team score on its own -
      a gametype script has to."**
        ↓
但修复前目录里是：**cha / coop / dm / dmz / sd / td / zm / zhunt / zarena**
（★ **没有 `war`**）
        ↓
且加载器**按字符串取名字**（`sv_script_source_mp.cpp:143-147`）
        ↓
★★★ ⇒ `war` **没有脚本、没有 `player_killed` 回调**
        ↓
★★★ ⇒ **整场比赛团队分为零** ⇒ **时钟是唯一能结束它的东西**
```

### ★★★★★ 修复前的九个目录名（逐字）

| # | 目录名 |
|---|---|
| 1 | `cha` |
| 2 | `coop` |
| 3 | `dm` |
| 4 | `dmz` |
| 5 | `sd` |
| 6 | `td` |
| 7 | `zm` |
| 8 | `zhunt` |
| 9 | `zarena` |

★★★ **⇒ 九个里**没有 `war`** ⇒ 这正是 `war.lua` 存在的理由。**

★ **⇒ 与报告 073/074 呼应：这正是 `dmz.lua` **逐字节等于 `dm.lua`** 的同一类问题的另一个面。**

---

## 二、★★★★★ **`td.lua` 不是范本**（第 18–21 行，逐字）

```lua
-- td.lua is NOT the model for this file. td.lua/zarena.lua/zhunt.lua are
-- byte-identical (sha256 40e1d88adb37af0f...) and td.lua's own header still says
-- "Free-for-all ... the engine gametype is dm" and prints "dm" - it is a copy of
-- dm.lua and it never calls addteamscore, which is exactly the gap above.
```

### ★★★★★ 一个**名牌与内容不符**的三元组

| 文件 | 内容 |
|---|---|
| **`td.lua`** | ★ **头注释写 "Free-for-all ... the engine gametype is dm"**，`print("dm")` |
| **`zarena.lua`** | ★ 与之**逐字节相同** |
| **`zhunt.lua`** | ★ 与之**逐字节相同** |

```
sha256 = **40e1d88adb37af0f...**
        ↓
★★★ 三者**逐字节相同**，且**都自称 dm 且都打印 "dm"**
        ↓
★★★ 且**都从不调用 `addteamscore`**
        ↓
⇒ 正是上面那个缺口
```

★★ **⇒ 注意 sha 前缀是 **`40e1d88adb37af0f...`**（与更早记录里 `5D4D27342AF613B0...` 不同）。**
**⇒ 说明这两个值属于**两组不同的三元组**，或其中一个是旧记录 —— 需交叉核对（见第九节）。**

★ **⇒ 这是**"文件名欺骗"的实证**（`td` = team deathmatch，但内容是 dm）。**

---

## 三、★★★★★ `war.lua` 的**出处引用表**（第 25–36 行，逐字）

```lua
-- Scoring patterns copied from the two files that already work:
--   cha.lua:14-44  the team branch - codol.on("player_killed"), the attacker
--                  self-kill check, codol.player(event.attacker_entity_num),
--                  issameteam, then addscore + addteamscore with the
--                  `local _, err, code = codol.call(...)` / `if err ~= nil then
--                  print(...)` deferral shape.
--   dm.lua:14-80   the same callback's opening guard and `method:respawn`.
-- Values: addscore 100 and the same-team gate are cha's; 3000 ms respawn is
-- cha's (dm measured 1500 for its OWN playlist - dm.lua:55-74 - and war is
-- scored and timed like cha per DedicatedSession.cpp:414-424, so cha's value is
-- the one that transfers). No addxp here: cha and td do not award it, and there
-- is no war measurement to justify a number.
```

### ★★★★★ 完整的出处表

| # | 项 | 值 | 出处 |
|---|---|---|---|
| **1** | 团队分支模式 | `codol.on` + 自杀检查 + `issameteam` | **`cha.lua:14-44`** |
| **2** | 回调开头守卫 + `respawn` | — | **`dm.lua:14-80`** |
| **3** | `addscore` | **100** | ★ `cha` 的 |
| **4** | 同队门控 | — | ★ `cha` 的 |
| **5** | **重生延迟** | **3000 ms** | ★★ `cha` 的 |
| **6** | 归因 | `war` **按 cha 计分与计时** | **`DedicatedSession.cpp:414-424`** |

### ★★★★★ **为什么 `war` 用 3000 而不是 `dm` 实测的 1500**（逐字）

```
"3000 ms respawn is cha's
 (dm **measured 1500 for its OWN playlist** - dm.lua:55-74 -
  and **war is scored and timed like cha** per DedicatedSession.cpp:414-424,
  so **cha's value is the one that transfers**)."
        ↓
★★★ 判据：**"scored and timed like cha"**（按 cha 的方式计分与计时）
        ↓
⇒ 所以移植的是 **cha 的 3000**，不是 dm 的 1500
```

★ **⇒ 这是**"哪个值可移植"的严谨判断**（不是简单复制最近的那个）。**

★★ **⇒ 与报告 074 呼应：`dm.lua` 实测 1500 是**针对它自己的 playlist**，不可外推。**

### ★★★★ `addteamscore` 的精确出处（第 65–68 行）

```lua
-- THE counter this mode's limit reads: addTeamScoreForClient ->
-- evaluateMatchLimits (sv_main_mp.cpp:2873-2886).
local _, team_score_error, team_score_error_code = codol.call(
    "method:addteamscore", attacker, 1)
```

★★ **⇒ `addteamscore(attacker, 1)` —— 每击杀 **1 分团队分**。**

★★★ **⇒ 且注明这条路径：`addTeamScoreForClient` → `evaluateMatchLimits`（`sv_main_mp.cpp:2873-2886`）。**

### ★★★ 每客户端击杀列**不是**上限读取的路径（第 75–77 行，逐字）

```lua
-- Per-client kill column, cha's counterpart to addteamscore.
-- It is NOT what war's limit reads (that path is dm-only,
-- sv_main_mp.cpp:2916-2942), so it cannot end the match early.
```

★★★ **⇒ 关键区分：**
```
`addteamscore` ⇒ ★ **war 的上限读它**（`sv_main_mp.cpp:2873-2886`）
`addkill`      ⇒ ★★ **war 的上限不读它**（那条路径**是 dm 专属**，
                  `sv_main_mp.cpp:2916-2942`）
        ↓
★ 所以 `addkill` **不会提前结束比赛**
```

★ **⇒ 与报告 074 呼应：`dm` 的 `addkill` **是**上限读取的那个（`dm` 用 `addkill` 当团队分替代）。**

---

## 四、★★★★★ `conf.lua` 的**权威 token 表**（第 1–3 行，逐字）

```lua
-- Kill Confirmed. The client books this as the playlist token "kc"; the engine
-- gametype - and so this file's name - is "conf" (CodolPlaylist.cpp:69, the
-- authoritative token -> gametype table).
```

### ★★★★★ 一个**权威出处**

| 项 | 值 |
|---|---|
| **客户端 token** | **`kc`** |
| **引擎 gametype** | **`conf`** |
| **★ 权威表** | **`CodolPlaylist.cpp:69`**（the authoritative token → gametype table） |

★★★ **⇒ 这是**token → gametype 映射的权威来源**（不是推断）。**

★ **⇒ 与报告 074 的 `ffa` → `dm` 呼应。**

---

## 五、★★★★★ **"引擎只有三条路径"与行号漂移**（第 13–19 行，逐字）

```lua
-- conf is a TEAM mode, so its limit is read from the TEAM score:
-- evaluateMatchLimits() (sv_main_mp.cpp:2950) falls through to the team branch
-- (sv_main_mp.cpp:2989-2993) for every gametype except zm and dm, and only
-- addClientScore/addTeamScoreForClient/addKillForClient ever call it. Nothing in
-- the engine awards team score on its own - a gametype script has to, which is
-- this file's job. (war.lua:9-11 cites :2944-2955 for the same branch; the V1.10
-- batch grew the file by 45 lines, the branch did not move.)
```

### ★★★★★ 三条路径与两个例外

```
`evaluateMatchLimits()`（`sv_main_mp.cpp:2950`）
        ↓
★ 对**除 `zm` 与 `dm` 之外**的每一个 gametype
  **落入团队分支**（`sv_main_mp.cpp:2989-2993`）
        ↓
★ 且**只有三条**路径会调用它：
  ① `addClientScore`
  ② `addTeamScoreForClient`
  ③ `addKillForClient`
```

★★★ **⇒ 两个例外：**`zm` 与 `dm`****（它们不走团队分支）。**

★ **⇒ 与报告 074 完全呼应：**
```
`dm`  ⇒ 上限读 **`addkill`**（不走团队分支）
`zm`  ⇒ 例外（合作模式，不计分）
其余  ⇒ 走团队分支（需要 `addteamscore`）
```

### ★★★★★ **行号漂移的明确解释**（逐字）

```
"(war.lua:9-11 cites **:2944-2955** for the same branch;
  the **V1.10 batch grew the file by 45 lines, the branch did not move**.)"
        ↓
★★★ 同一分支：
  `war.lua` 写 **:2944-2955**
  `conf.lua` 写 **:2950**（以及团队分支 **:2989-2993**）
        ↓
★ 原因：**V1.10 批次让 `sv_main_mp.cpp` 长了 45 行**
        ↓
★★★ 但**分支本身没动**
```

★★ **⇒ 这是一个**极其重要的方法论说明**：**
```
★ 行号引用会随文件增长漂移
★★★ 但代码结构（分支）不会
        ↓
⇒ 引用行号时必须注明**出处版本**
```

---

## 六、★★★★★ **`conf.lua` 的重建边界**（第 21–26 行，逐字）

```lua
-- RECONSTRUCTION BOUNDARY. Retail Kill Confirmed scores a kill only after the
-- victim's dog tag is collected, and denies it if the other team collects first.
-- This build has no tag entity, no pickup volume and no deny path, so this file
-- credits on the lethal event exactly like war.lua and cha.lua do. It wires the
-- mode's accounting; it is NOT a dog-tag implementation and must not be recorded
-- as one.
```

### ★★★★★ 完整的重建边界

```
零售 Kill Confirmed 规则：
  ① 击杀**只有在**受害者的**狗牌被拾取后**才计分
  ② 若**对方队伍先拾取** ⇒ **拒绝计分**
        ↓
★★★ 但本 build：
  · **没有 tag 实体**（no tag entity）
  · **没有拾取体积**（no pickup volume）
  · **没有拒绝路径**（no deny path）
        ↓
⇒ 本文件**在致命事件上直接计分**（与 `war.lua` / `cha.lua` 一样）
        ↓
★★★ "It **wires the mode's accounting**;
     it is **NOT a dog-tag implementation** and **must not be recorded as one**."
```

★★ **⇒ 这是**全包最明确的"重建边界"声明**（与报告 069 的 `zm.lua` "BRING-UP PLACEHOLDER" 同类，但更正式）。**

★ **⇒ 且给出**三条具体缺失**：tag 实体 / 拾取体积 / 拒绝路径。**

★★ **⇒ 与报告 073 的 `dmz.lua` 边界声明**形成对照**：**
```
`dmz.lua`  ⇒ 圆圈不绘制 + 捡枪替换（两条）
`conf.lua` ⇒ 无 tag/拾取/拒绝（三条）
`zm.lua`   ⇒ 无 AI 僵尸 builtin + 重生占位（两条）
```

---

## 七、★★★★★ **两处头注释与正文矛盾**（重要发现）

### 7.1 `war.lua` 的矛盾

**头注释（第 35–36 行）：**
```lua
-- ... No addxp here: cha and td do not award it, and there
-- is no war measurement to justify a number.
```

**正文（第 88–89 行）：**
```lua
local _, xp_error, xp_error_code = codol.call(
    "method:addxp", attacker, 50)
```

★★★ **⇒ 头注释说"这里没有 addxp"，正文却有 `addxp 50`。**

### 7.2 `conf.lua` 的矛盾

**头注释（第 36–38 行）：**
```lua
-- ... None of them is invented here, and no addxp is
-- awarded because neither cha nor war awards one and there is no conf
-- measurement to justify a number.
```

**正文（第 91–92 行）：**
```lua
local _, xp_error, xp_error_code = codol.call(
    "method:addxp", attacker, 50)
```

★★★ **⇒ 同样矛盾。**

### ★★★★★ 原因

```
头注释写于 **V1.11 XP 批次之前**
（当时确实"没有 addxp"，且理由成立）
        ↓
★ V1.11 / (2) match info 批次（ticket **20261011-22000**）
  加入了 addxp 块（第 78–100 行 / 第 81–103 行）
        ↓
★★★ 但**头注释没有回头更新**
        ↓
⇒ 于是"no addxp here"与 `addxp 50` 并存
```

★ **⇒ 注意：新增的 XP 块**自带完整论证**（"50 IS MEASURED, NOT INVENTED"），
**所以矛盾只影响头注释的可信度，不影响代码正确性。****

★★ **⇒ 但这仍是**文档缺陷**：头注释的"no addxp"结论已作废。**

★★ **⇒ 这也解释了为什么两个文件的头注释**逐字相同**——它们是同一个模板的两次套用。**

---

## 八、★★★★ `war.lua` 与 `conf.lua` 的**逐字节对照**

| 项 | `war.lua` | `conf.lua` |
|---|---|---|
| **token** | **`tdm`** | **`kc`** |
| **gametype** | **`war`** | **`conf`** |
| **playlist** | **30** | （未注明） |
| **`print` 行位置** | 第 **23** 行 | 第 **45** 行 |
| **`addscore`** | **100** | **100** |
| **`addteamscore`** | **1** | **1** |
| **`addkill`** | **1** | **1** |
| **`addxp`** | **50**（+爆头 50） | **50**（+爆头 50） |
| **重生** | **3000** | **3000** |
| **上限读的计数器** | `addteamscore`（`:2873-2886`） | `addteamscore`（`:2929`） |
| **`addkill` 路径** | dm 专属（`:2916-2942`） | dm 专属（`:2961-2988`） |
| **`pcall` 包裹** | ★ 有（全回调） | ★ 有（全回调） |
| **`production` 差异** | 有 `print` 在头注释后 | `print` 在头注释**前**（第 45 行在 `assert` 之前） |
| **行数** | **121** | **124** |

★★★ **⇒ 两者结构**几乎逐字节对应**（只是注释长度不同）。**

★ **⇒ 唯一的顺序差异：`war.lua` 的 `print` 在第 23 行（注释块结束后），
`conf.lua` 的 `print` 在第 45 行（也在注释块结束后）—— 实际一致。****

---

## 九、★★★ 一个待核对的 sha 差异

| 报告 | sha256 前缀 | 对象 |
|---|---|---|
| **早前记录** | **`5D4D27342AF613B0...`** | `td.lua`/`zarena.lua`/`zhunt.lua` 三元组 |
| **`war.lua:19`** | **`40e1d88adb37af0f...`** | `td.lua`/`zarena.lua`/`zhunt.lua` 三元组 |

★★ **⇒ 同一个三元组有两个不同的 sha256 前缀 ⇒ 至少一个是错的。**

★ **⇒ 需要重新计算 `td.lua` / `zarena.lua` / `zhunt.lua` 的实际 sha256 来判定。**
**⇒ 记录为**待核对项**（不擅自采纳任一方）。**

---

## 十、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **`war` 必须存在的原因** | 上限读**团队分**；**引擎自己不加团队分** |
| 2 | ★★ 关键函数 | `evaluateMatchLimits()`（`sv_main_mp.cpp:2944-2955`） |
| 3 | ★★★ 修复前九个目录 | `cha/coop/dm/dmz/sd/td/zm/zhunt/zarena`（**无 `war`**） |
| 4 | ★★ 加载器 | **按字符串取名字**（`sv_script_source_mp.cpp:143-147`） |
| 5 | ★★★ 后果 | **整场团队分为零 ⇒ 时钟是唯一结束方式** |
| 6 | ★★★★★ **`td.lua` 不是范本** | 头注释写 **"Free-for-all ... gametype is dm"**，`print("dm")`，**从不 `addteamscore`** |
| 7 | ★ sha256 | **`40e1d88adb37af0f...`**（★ 与早前记录 `5D4D27342AF613B0...` **不一致，待核对**） |
| 8 | ★★★ 出处 | `cha.lua:14-44`（团队分支）/ `dm.lua:14-80`（守卫 + respawn） |
| 9 | ★★★ **重生选 3000 的判据** | `war` **按 cha 计分与计时**（`DedicatedSession.cpp:414-424`） |
| 10 | ★ ★ `dm` 的 1500 不可外推 | "dm measured 1500 for its **OWN playlist**" |
| 11 | ★★ `addteamscore` 路径 | `addTeamScoreForClient` → `evaluateMatchLimits`（`sv_main_mp.cpp:2873-2886`） |
| 12 | ★★★ `addkill` 不是上限路径 | 那条路径**是 dm 专属**（`:2916-2942`） |
| 13 | ★★★★★ **权威 token 表** | **`CodolPlaylist.cpp:69`** |
| 14 | ★★ `kc` → `conf` | 客户端 token `kc` ⇒ 引擎 `conf` |
| 15 | ★★★★★ **三条路径** | `addClientScore` / `addTeamScoreForClient` / `addKillForClient` |
| 16 | ★★ **两个例外** | **`zm` 与 `dm`**（不走团队分支） |
| 17 | ★★★★ **行号漂移** | `war.lua` 写 **:2944-2955**，`conf.lua` 写 **:2950**；**V1.10 批次长了 45 行，分支没动** |
| 18 | ★★★★★ **`conf` 重建边界** | 零售需**狗牌被拾取**才计分、对方先拾则**拒绝**；本 build **无 tag 实体 / 无拾取体积 / 无拒绝路径** |
| 19 | ★★★ 措辞 | "**NOT a dog-tag implementation** and **must not be recorded as one**" |
| 20 | ★★★★★ **两处头注释矛盾** | `war.lua:35-36` 与 `conf.lua:36-38` 都说 **"no addxp"**，正文**都有 `addxp 50`** |
| 21 | ★★ 矛盾原因 | 头注释写于 **V1.11 之前**，XP 批次（ticket **20261011-22000**）加了正文但**未回头改头注释** |
| 22 | ★★ 两者结构 | **几乎逐字节对应**（121 行 vs 124 行） |

---

## 十一、结论

### 1. ★★★★★ **"引擎自己不加团队分"**是 `war.lua`/`conf.lua` 存在的根本原因

```
团队模式的上限读**团队分**
        ↓
★ 但引擎**自己不产生团队分**
   （只有 `addTeamScoreForClient` / `addKillForClient` 会调用 `evaluateMatchLimits`）
        ↓
★★★ ⇒ **gametype 脚本必须自己加**
        ↓
缺失的后果：**整场团队分为零，时钟是唯一结束方式**
```

### 2. ★★★★★ **`td.lua` 是"文件名欺骗"**（自称 dm、打印 "dm"、从不加团队分）

★★ **⇒ 且与 `zarena.lua` / `zhunt.lua` **逐字节相同**。**

### 3. ★★★★★ **`conf.lua` 的重建边界**是全包最正式的声明

```
零售需狗牌被拾取才计分 / 对方先拾则拒绝
本 build：**无 tag 实体 / 无拾取体积 / 无拒绝路径**
        ↓
★ "It wires the mode's **accounting**; it is **NOT a dog-tag implementation**
   and **must not be recorded as one**."
```

### 4. ★★★★ **行号漂移的明确解释**（V1.10 批次 +45 行，分支未动）

### 5. ★★★★ **两处头注释与正文矛盾**（"no addxp here" vs 实际 `addxp 50`）

★ **⇒ 原因：V1.11 XP 批次未回头更新头注释。**

### 6. ★★★ **判定"哪个值可移植"的严谨判据**（"scored and timed like cha"）

---

## 十二、下一步

- **核对 `td.lua` / `zarena.lua` / `zhunt.lua` 的实际 sha256**（解决第九节的分歧）
- `cha.lua` 的团队分支（`cha.lua:14-56`）作为对照
- `configs_s.info`（1,067 行）
- `mp_playlists_shipRetail_release.info`（3,970 行）
- `coop_training_mp_cargoship.lua`（4,683 行）
