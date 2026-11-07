# 学习报告 008（重开）— `sd.lua` / `zm.lua` 头部（含"实体不可见"根因）

**学习范围**：`gametypes\sd.lua`(20,121) 行 1–34 + `gametypes\zm.lua`(37,359) 行 1–28
**性质**：全实测
**★★★ 本报告发现 FX 表的**两代版本**，以及一个**通用的"实体不可见"故障类**

---

## 一、★★★ `sd.lua` 行 1–11 —— `setmapgameobjects` 的**变参**形态

```lua
local _, error_message, error_code = codol.call(
    "function:setmapgameobjects",
    "sd",
    "bombzone",
    "blocker",
    "airdrop_pallet")
assert(
    error_message == nil,
    tostring(error_message) .. ":" .. tostring(error_code))

print("gametype map gameobjects activated", "sd")
```

★★★ **⇒ `setmapgameobjects` 是**变参**的：**
```
cha  →  ("cha", "airdrop_pallet")                          1 个对象
sd   →  ("sd", "bombzone", "blocker", "airdrop_pallet")    3 个对象
```

★ **⇒ 第 1 参固定是 gametype 名，其余是对象类名（0..N 个）。**

---

## 二、★★★★ `sd.lua` 行 13–27 —— **击杀特效的完整逆向证据链**

> V1.11 **KILL EFFECT, PER WEAPON** (ticket `20261011-26000`). This block **REPLACES
> V1.10's single name** (`"impacts/deathfx_bloodpool_view"`, taken from our own 2021
> demo string pool). A single name for every weapon is a **DEFECT**: the engine's own
> weapon definitions carry a **per-weapon effect name**, and **most weapons carry none**.
>
> **SOURCE (read-only, out of THIS client's resident assets):**
> ```
> WeaponDefinitionsRva 0x1588B50        (EngineBindings.hpp:778)
> the client is x86, so the table entries are 4 bytes wide
> the definition structs are a contiguous array with stride 0x101C
> the effect name sits at +1464
> Tool:   02-tools\scripts\census_weapon_fx_fields.py
> Result: 1167 named weapons, 92 with an effect name, 12 distinct names
> Table:  01-docs\40-evidence\按武器击杀特效-20261011-26000\weapon-fx-census.tsv
> ```
> A weapon with no entry plays **NO** kill effect.
> **FAIL-SOFT, unchanged**: every branch below only prints; **kill accounting is above**.
>
> ```
> 由 gen_kill_fx_table.py 从 weapon-fx-census.tsv 生成；勿手改。
> 每项 = 武器定义名 → 该武器在引擎自带定义里的特效名（结构体 +1464）。
> ```

### ★★★ 逐项技术参数

| 项 | 值 |
|---|---|
| 武器定义表 RVA | **`0x1588B50`** |
| 出处 | `EngineBindings.hpp:778` |
| 表项宽度 | **4 字节**（x86 指针） |
| 结构体步长 | **`0x101C`**（4,124 字节） |
| 特效名字段偏移 | **`+1464`**（= `0x5B8`） |
| 命名武器总数 | **1,167** |
| 有特效名的 | **92** |
| 不同特效名 | **12** |
| 生成工具 | `census_weapon_fx_fields.py` |
| 生成器 | `gen_kill_fx_table.py` |
| 中文提示 | ★ **"勿手改"** |

### ★★★★★ 版本演进（V1.10 → V1.11）

```
V1.10：所有武器共用一个特效名 "impacts/deathfx_bloodpool_view"
       来源 = "our own 2021 demo string pool"
       ★ 这是 DEFECT（缺陷）

V1.11：改为每武器一项，取自客户端**常驻资产**（resident assets）
       来源 = 运行时武器定义表 @ RVA 0x1588B50
```

★★★ **⇒ 这是"从自家字符串池抄"→"从客户端真实资产读"的**方法论升级**。**

---

## 三、★★★★ `sd.lua` 与 `cha.lua` 的 FX 表是**两代**

### 3.1 逐项对照

| 项 | `cha.lua` | `sd.lua` |
|---|---|---|
| 表项数 | 92 | 92 |
| 每项注释 | **无** | ★ **`-- index=NN`** |
| 头部来源 | `resolved-fx-table.tsv`（453 行） | `weapon-fx-census.tsv` |
| 生成工具 | （未列） | `census_weapon_fx_fields.py` + `gen_kill_fx_table.py` |
| 中文提示 | 无 | ★ 有（"勿手改"） |
| RVA 记载 | 无 | ★ **`0x1588B50`** |
| ticket | `28600` / `28800` | `20261011-26000` |

### 3.2 ★★★ 语义差异（关键）

```
cha.lua 说：92 项 = "自身定义带 FX 的武器"；其余 361 个有"家族" FX（荷兰表 453 行）
sd.lua  说：1167 把命名武器，92 把有特效名，12 个不同名字
```

★★ **两者都收敛到 **92** —— 但描述框架不同：**
- `cha.lua`：从 **453 行**的家族传播表**收缩**到 92（否证家族传播）
- `sd.lua`：从 **1167 把**武器里**筛出** 92（直接读定义字段）

★★★ **⇒ `sd.lua` 是**更直接的路径**（直接读 `+1464` 字段），
`cha.lua` 是**经过一次否证的路径**。**

★ **`cha.lua:2` 说 "the other 361 definitions still have one through their FAMILY"**
**⇒ 92 + 361 = 453（与 453 行表吻合）。**

---

## 四、★★★★★ `zm.lua` 行 1–28 —— **"实体不可见"的根因**（本报告最重要）

### 4.1 零售 serverinfo（逐字，字节级）

```
\g_gametype\zm\g_hardcore\0\mapname\zm_factory_sh
\scr_game_allowkillcam\0\scr_team_fftype\0
```

★★ **⇒ 这是**零售服务器的真实 serverinfo 串**（`\` 分隔的 key\value）。**
★ **"byte-identical across all three `zm_factory_sh` demos"** —— 三次 demo 一致。

### 4.2 ★★★ `zm.lua` 曾经是 `dm.lua` 的逐字节副本

> Until this file was written it was a **BYTE-IDENTICAL COPY OF `dm.lua`** —
> **free-for-all rules**, including awarding **50 display score and a kill for
> shooting another player**. That is **exactly backwards for a co-operative mode**
> and is the first thing corrected here.

★★★ **⇒ 这是**第四个"副本失真"**案例：**
```
zm.lua 曾是 dm.lua 的逐字节副本   ⇒ 合作模式却按 FFA 计分
td/zarena/zhunt 仍是失真副本     ⇒ 不调 addteamscore、打印 dm、重生 3000≠1500
coop.lua 曾是 dm.lua 的陈旧副本   ⇒ 战役里每死一次加 FFA 分
conf.lua / war.lua 曾经完全缺失   ⇒ 整局无分
```

### 4.3 ★★★ 无游戏对象（第 12–15 行）

> Zombies has **no bombzone, blocker or airdrop_pallet**; there is no objective to bind.
> **Retail's own zombie map objects — the mystery box (`d 3627 zmb_box_poof` in the
> demo), doors, power — are NOT map gameobjects in this sense and have no builtin.**

★★ **⇒ "mystery box"（神秘箱）在 demo 里的记录是 `d 3627 zmb_box_poof`。**
**★ 但它**不是** `setmapgameobjects` 意义上的对象（没有对应 builtin）。**

### 4.4 ★ `codol_friendly_fire_mode = 0`（第 17–19 行）

> Every player is a survivor on the same side, so **no player should ever damage
> another**. **Mode 0 is "no damage"** and it matches retail's **`scr_team_fftype\0`**.

★★ **⇒ 交叉印证：零售 serverinfo 的 `scr_team_fftype\0` 就是 `codol_friendly_fire_mode = 0`。**

### 4.5 ★★★★★ **"THE ZOMBIE MODEL, PRECACHED BEFORE ANYTHING SPAWNS"**（第 21–28 行）

> The client resolves the agent element's **model INDEX** against its **own configstring
> band**, and **that band holds only what this server has transmitted**. Loading the same
> map does **NOT** give the client the dedicated's band: **index 308 was empty on the
> client**, so the **actor record's model name stayed `""`** and the client **built no
> DObj at all**. **Zombies were on the wire, validated, and invisible.**
>
> `re/demo-re/20-zm-actor-lifecycle.md 12.21`

★★★★★ **⇒ 这是一个**通用的故障类**，完整链条：**

```
服务端发实体（带 model index）
        ↓
客户端的 configstring band 里**没有**这个 index
        ↓
模型名解析为 ""
        ↓
客户端**不构建 DObj**
        ↓
★ 实体"在线、已校验、但不可见"
```

★★★ **⇒ 关键洞察："加载同一张地图"**不会**把服务端的 band 给客户端。**
**band 只含**服务端已传输的内容**。**

★★ **必须在使用前**预缓存（precache）**模型 —— 这就是这段标题的含义。**

★★★ **⇒ 这与记忆里的现象**完全同源**：**
> 记忆 `codol-entity-section-live-verified`：
> "**看不到实体**: 只发 eType+origin（`model_index` 恒 0 无模型引用），
>  且发的是号 0..7 = 客户端自己的槽位号 ⇒ 无可见增量"

★★★ **⇒ 两个独立项目、同一个根因：**model index ↔ configstring band 不一致 ⇒ 无 DObj ⇒ 不可见。****

---

## 五、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | `setmapgameobjects` 变参 | cha 1 个 / sd **3 个**对象 |
| 2 | sd 的对象 | `bombzone` / `blocker` / `airdrop_pallet` |
| 3 | ★ 武器定义表 RVA | **`0x1588B50`** |
| 4 | 结构体步长 | **`0x101C`** |
| 5 | 特效名字段 | **`+1464`** |
| 6 | 武器计数 | 1167 命名 / 92 有特效 / 12 个名字 |
| 7 | ★★ FX 表两代 | `cha`(453→92，无 index) / `sd`(1167→92，有 index) |
| 8 | 零售 zm serverinfo | `\g_gametype\zm\g_hardcore\0\mapname\zm_factory_sh` |
| 9 | 零售 zm fftype | `\scr_team_fftype\0` = `codol_friendly_fire_mode = 0` ✓ |
| 10 | ★★★ **"实体不可见"根因** | **configstring band 缺 index 308 ⇒ 模型名 "" ⇒ 无 DObj** |
| 11 | 原始记录出处 | `re/demo-re/20-zm-actor-lifecycle.md 12.21` |
| 12 | ★ `zm.lua` 曾是 `dm.lua` 逐字节副本 | 合作模式按 FFA 计分 |
| 13 | mystery box 记录 | `d 3627 zmb_box_poof`（**非** map gameobject） |

---

## 六、结论

### 1. ★★★★★ 找到了一条**可复用的通用故障诊断规则**

```
实体不可见 ⇒ 先查 configstring band 里 model index 是否存在
             ⇒ band 只含"服务端已传输"的内容，与"是否加载同一地图"无关
```

★★★ **⇒ 这条同时解释了两件事：**
```
① zm.lua 的"僵尸在线但不可见"（index 308 空）
② 我们项目"实体段发了但看不到"（model_index 恒 0）
```

### 2. ★★★ FX 表有**两代并存**（cha 与 sd 不同），且都被完整记录

### 3. ★★★ `zm.lua` 曾是 `dm.lua` 副本 —— 累计**五处副本失真**已全部记录

```
conf.lua / war.lua  曾经完全缺失      ⇒ 整局无分
coop.lua            曾是 dm.lua 陈旧副本 ⇒ 战役每死一次加 FFA 分
zm.lua              曾是 dm.lua 逐字节副本 ⇒ 合作模式按 FFA 计分
td/zarena/zhunt     仍是失真副本        ⇒ 不调 addteamscore / 打印 dm / 重生 3000≠1500
```

### 4. ★★ 逆向方法论的两级跳（V1.10 → V1.11）

```
自家字符串池  →  客户端常驻资产（运行时读表）
```

### 5. ★★ 中文注释混入（"勿手改"、"由 … 生成"）

---

## 七、下一步

- `gametypes\dmz.lua`(9,552) / `cha.lua` 行 175–末尾 / `zm.lua` 行 28+
- `maps\coop_training_mp_cargoship.lua`(201,269) 头部
- 包根 `README.md` / `BUILD.md` / `preflight.ps1` / `deploy.ps1` / `run.cmd` 逐字节
- ★ **全量核对 `MANIFEST.sha256`**（PowerShell 分类器恢复后）
- ★ **清理我上次留下的 6 个 `.bak` 文件**
