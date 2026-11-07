# 学习报告 006（重开）— `war.lua` / `cha.lua` 头部 + **哈希矛盾定案**

**学习范围**：`gametypes\war.lua`(7,018) / `gametypes\cha.lua`(21,493) 头部
**性质**：全实测
**★★★ 本报告发现交付包内**自相矛盾**的哈希断言**

---

## 一、★★★ `war.lua` 头部（第 1–42 行）—— TDM 契约

### 1.1 token 错位（第 1–2 行）

> **Team deathmatch.** The client books this as the playlist token **`tdm`**; the engine
> gametype — and so this file's name — is **`war`**, which is the **stock IW name**.

★★★ **⇒ 第三个 token/gametype 错位实例：**

| token | gametype（文件名） | 出处 |
|---|---|---|
| `ffa` | `dm`（但在 `td.lua` 里） | `td.lua:1-3` |
| `kc` | `conf` | `conf.lua:1-3` |
| **`tdm`** | **`war`** | `war.lua:1-2` |

### 1.2 ★★★ 限分来源（第 4–6 行）

> There are **no map game objects**: playlist **30** carries no objective script, and
> both the score limit and the clock come from the playlist rules
> **`scr_war_scorelimit` / `scr_war_timelimit`**, read for the ENGINE prefix.

★ **播放列表 30；比分与时钟来自 `scr_war_*` cvar。**

### 1.3 ★★★ "WHY THIS FILE EXISTS AT ALL"（第 8–16 行）

> war is a **TEAM mode**, so its limit is read from the TEAM score:
> **`sv_main_mp.cpp:2944-2955` `evaluateMatchLimits()`** compares
> `clients_.teamScore(Tf/Sc)` against `rules.scoreLimit`, and only
> **`addTeamScoreForClient()` / `addKillForClient()`** ever call it.
> **Nothing in the engine awards team score on its own — a gametype script has to.**
> Before this file the directory held **`cha/coop/dm/dmz/sd/td/zm/zhunt/zarena`**
> and the loader takes the name by string (**`sv_script_source_mp.cpp:143-147`**),
> so **war had NO script, no `player_killed` callback, and therefore zero team score
> for the whole match**: the clock was the only thing that could ever end it.

★★★ **⇒ 这是**第二个"缺失文件导致整局无分"**案例（第一个是 `conf`）。**

★ **目录清单（写 war 时）**：`cha/coop/dm/dmz/sd/td/zm/zhunt/zarena`（**9 个**）
★★ **⇒ 与 `conf.lua` 说的（10 个，含 war）差一项 —— 两份注释是**不同时间**写的。**

### 1.4 ★★★★ 第 18–21 行 —— **对 `td.lua` 的明确否证 + 一个哈希**

> **`td.lua` is NOT the model for this file.** `td.lua` / `zarena.lua` / `zhunt.lua`
> are **byte-identical (sha256 `40e1d88adb37af0f...`)** and `td.lua`'s own header still
> says "Free-for-all ... the engine gametype is dm" and prints "dm" —
> **it is a copy of `dm.lua` and it never calls `addteamscore`, which is exactly the
> gap above.**

★★★ **⇒ 三件事同时确认：**
1. **三胞胎确实 byte-identical** ✓（与清单一致）
2. **`td.lua` 是 `dm.lua` 的副本**，且**从不调 `addteamscore`**
3. ★★★ **注释里给的哈希是 `40e1d88adb37af0f…`**

---

## 二、★★★★ **哈希矛盾定案**（本次核心发现）

### 2.1 两处哈希的直接对照

| 来源 | `td.lua` 的 SHA256 前 16 |
|---|---|
| `war.lua:19`（源码注释） | **`40e1d88adb37af0f`** |
| `MANIFEST.sha256:46`（打包清单） | **`5D4D27342AF613B0`** |

★★★ **⇒ 两者**完全不同**。**

### 2.2 排除"我读错了"

**清单第 46/48/49 行（实测）**：
```
5D4D27342AF613B0D04BE37E386B450D6B96C1733A1EAD0D73BB78AF734BEDF0  .../gametypes/td.lua      3595
5D4D27342AF613B0D04BE37E386B450D6B96C1733A1EAD0D73BB78AF734BEDF0  .../gametypes/zarena.lua  3595
5D4D27342AF613B0D04BE37E386B450D6B96C1733A1EAD0D73BB78AF734BEDF0  .../gametypes/zhunt.lua   3595
```

★ **三者一致（byte-identical 成立）**，但**值是 `5D4D2734…`，不是 `40e1d88a…`。**

### 2.3 ★★★ 结论：`war.lua` 的注释**比 `td.lua` 旧**

```
写 war.lua 时：  td.lua 的哈希 = 40e1d88adb37af0f…  （某版本）
打包时：         td.lua 的哈希 = 5D4D27342af613b0…  （另一版本）
```

★★★ **⇒ `war.lua` 写完之后，`td.lua` 被**重新生成过**（三者同步重生成）。**

★ **`td.lua:5` 的 `print("gametype has no map gameobjects", "dm")` 保留了 `dm`** ——
**说明重生成时**没改打印串**。**

### 2.4 ★★★ 与报告 005 的 `cha.lua` 哈希异常**同源**

```
报告 005：runtime-manifest 说 cha.lua = 1,839 B
          MANIFEST.sha256 说 cha.lua = 21,493 B     ← 增长 11.7×
本报告：  war.lua 注释说 td.lua = 40e1d88a…
          MANIFEST.sha256 说 td.lua = 5D4D2734…     ← 值变了
```

★★★ **⇒ 交付包内的**所有哈希断言都不是同一时刻的**：**
```
runtime-manifest   最早（cha.lua 1,839 B）
war.lua 注释       中间（td.lua 40e1d88a）
MANIFEST.sha256    打包时（权威）
```

★★★ **⇒ **唯一权威是 `MANIFEST.sha256`。****

★ **这与报告 005 的结论一致，现在有了**第二个独立证据**。**

### 2.5 ★ war.lua 还引用了另外三处源码位置

```
cha.lua:14-44      团队分支范式
dm.lua:14-80       开场守卫 + method:respawn
DedicatedSession.cpp:414-424   "war is scored and timed like cha"
dm.lua:55-74       "dm measured 1500 for its OWN playlist"
```

★★★ **⇒ **同一职业里 `dm` 的重生是 1500 ms，而 `td.lua` 写的是 3000 ms**！**

★★★ **⇒ `td.lua`（= `dm` 的副本）用的是 **3000**，而真正的 `dm.lua` 用 **1500**。**
**⇒ `td.lua` 的重生延迟**与它所声称的 `dm` 语义不符**。**

★★ **这是第三个"副本失真"证据**（前两个：不调 `addteamscore`、打印串是 `dm`）。**

---

## 三、★★ `cha.lua` 头部（第 1–30 行）—— **不是计分，是击杀特效表**

### 3.1 完全出乎意料的内容

★ **我原以为 `cha.lua`（21,493 B，最大的计分类）是**计分逻辑**。**

★★★ **实际开头是 **`KILL_FX_BY_WEAPON` 表**（92 项）：**

```lua
-- 28600: the 92-entry table only covered the weapons whose WeaponDef carries
-- an FX at +1464. The other 361 definitions still have one through their FAMILY
-- (resolved-fx-table.tsv, 453 rows, 12 FX names). Retail's "one series, one
-- effect" is exactly this table; a weapon with no family effect stays silent.
-- Generated from 01-docs\40-evidence\按武器特效基础继承-20261011-28000\
-- resolved-fx-table.tsv -- do not hand-edit; regenerate instead.
-- 28800 (second knife): OWN-ONLY KILL FX.
local KILL_FX_BY_WEAPON = {
    ["acrair_mp"] = "weapon/fx_space_death",
    ["acrdeatheg_mp"] = "weapon/fx_hit_death_engine01",
    ["acrknight_mp"] = "misc/fx_coinkill01",
    ["ak104block_mp"] = "misc/fx_death01",
    ["ak104campaigner_mp"] = "misc/fx_death04_campaigner",
    ["ak104geo_mp"] = "env/fire/fx_fire_player_torso_dragons",
    ...
```

### 3.2 ★★★ 关键技术细节

| 项 | 值 |
|---|---|
| 特效属性偏移 | **`WeaponDef + 1464`**（= `+0x5B8`） |
| 表项数（旧） | **92** |
| 表项数（新） | **453 行**（`resolved-fx-table.tsv`） |
| 特效名数 | **12** |
| 生成源文件 | `01-docs\40-evidence\按武器特效基础继承-20261011-28000\resolved-fx-table.tsv` |
| 编辑策略 | ★★ **"do not hand-edit; regenerate instead"** |
| 回退值 | `KILL_FX_FALLBACK (nil)` = **无特效** |

### 3.3 ★★★ 一段"方向的自我纠正"（第 7–18 行）

> The 453-row table was produced by propagating an FX along `base_weapon` groups in
> **BOTH directions**. That gave 32 BASE weapons (`ak47_mp`, `m4a1tech_mp`, `scar_mp`,
> `acr_mp`, `cheytac_mp`, `vepr_mp`, `rpd_mp`, `miniuzi_mp`, `mp5k_mp`,
> `deserteagle_mp`, `ump45_mp`, `aks74u_mp`, ...) a **skin variant's effect**, and it is
> exactly the operator's "**some guns have no kill effect yet they trigger one**".
>
> **Retail semantics: `WeaponDef +1464` ("fx") is a property of THIS weapon asset,
> not of its family** — `base_weapon` groups a family, `fx` describes the variant.
>
> **So only the 92 rows whose OWN definition carries an FX stay.** Everything else
> falls through to `KILL_FX_FALLBACK (nil)` ⇒ **no effect at all**, which is what the
> original ticket's "**no entry ⇒ no effect**" rule already said.

★★★ **⇒ 这是又一次**用实测证伪自己**的记录（与 `stun_local.py` 的"STUN 假设被否证"同源）：**

```
假设：特效沿 base_weapon 家族传播（双向）
实测：零售语义是"每个武器资产自己的 +1464"
        ⇒ 家族传播是错的，会造成 32 把基础武器误触发皮肤特效
修正：只保留**自身定义里带 FX 的 92 项**，其余回退 nil
```

### 3.4 ★★ 中文路径泄漏（第 5 行）

```
01-docs\40-evidence\按武器特效基础继承-20261011-28000\resolved-fx-table.tsv
```

★★ **⇒ 作者的证据目录用**中文命名**（与 `fp\桌面\ol` 的风格一致）。**
★ **⇒ 该目录**不在交付包里**（`source\` 里没有 `01-docs\`）。**

---

## 四、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | token→gametype 错位 | `ffa`→`dm`（在 td.lua）/ `kc`→`conf` / **`tdm`→`war`** |
| 2 | 播放列表 30 | `war`（TDM） |
| 3 | 限分 cvar | `scr_war_scorelimit` / `scr_war_timelimit` |
| 4 | 限分读法函数 | `evaluateMatchLimits()` @ `sv_main_mp.cpp:2944-2955` |
| 5 | 加分函数 | `addTeamScoreForClient` / `addKillForClient` |
| 6 | 加载器位置 | `sv_script_source_mp.cpp:143-147` |
| 7 | ★★★ **哈希矛盾** | `war.lua:19` = `40e1d88a…` vs 清单 = `5D4D2734…` |
| 8 | ★★ dm 重生延迟 | **1500 ms**（`dm.lua:55-74` 实测）vs `td.lua` 的 **3000 ms** |
| 9 | `cha.lua` 首块 | ★★★ **`KILL_FX_BY_WEAPON`（92 项）** |
| 10 | 武器特效偏移 | `WeaponDef + 1464` |
| 11 | 特效表生成源 | `resolved-fx-table.tsv`（453 行）/ 生成目录含中文 |
| 12 | 编辑策略 | "do not hand-edit; regenerate instead" |
| 13 | 回退 | `KILL_FX_FALLBACK (nil)` = 无特效 |

---

## 五、结论

### 1. ★★★★ 交付包内**三份哈希断言互不相同**，只有 `MANIFEST.sha256` 权威

```
runtime-manifest.json   cha.lua = 1,839 B        （最早）
war.lua 注释            td.lua  = 40e1d88a…      （中间）
MANIFEST.sha256         cha.lua = 21,493 B
                        td.lua  = 5D4D2734…      （打包时 = 权威）
```

★★★ **⇒ 任何"以注释里的哈希为准"的校验都会失败。**

### 2. ★★★ `td.lua` 是 `dm.lua` 的**失真副本**（三处证据）

```
① 不调 addteamscore          （war.lua:18-21 指出）
② 打印串仍是 "dm"            （td.lua:5）
③ 重生用 3000，而 dm 实测 1500（war.lua:33-34 指出）
```

★★ **⇒ 但 `zarena.lua` / `zhunt.lua` 与它**字节相同** ⇒ 三个模式都继承了这个失真。**

### 3. ★★★ `cha.lua` 的主体是**击杀特效表**，不是计分

★ **计分逻辑在头部之外（我只读了 30 行）。**

### 4. ★★★ 又一次"实测证伪假设"的记录（特效家族传播 → 自身属性）

★ **与 `stun_local.py`、`deploy.ps1` 的同类记录一起，说明作者的工作方式**以实测为准**。**

### 5. ★★ 中文路径泄漏（`按武器特效基础继承-20261011-28000`）

★ **⇒ 证据目录未随包交付，只在注释里留了路径。**

---

## 六、下一步

- `gametypes\dm.lua`(4,618) / `sd.lua`(20,121) / `zm.lua`(37,359) 头部
- `maps\coop_training_mp_cargoship.lua`(201,269) 头部
- `cha.lua` 的**计分部分**（在 92 项特效表之后）
- `Bootstrapper64.dll`（清单里没有，但文件在）
- 包根 `README.md` / `BUILD.md` / `preflight.ps1` / `deploy.ps1` / `run.cmd`
- ★ **全量核对 `MANIFEST.sha256`**（等 PowerShell 分类器稳定）
