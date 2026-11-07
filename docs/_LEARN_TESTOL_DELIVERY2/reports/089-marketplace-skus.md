# 学习报告 089（重开）— `MarketplaceSkus.json` 全量逐条（2,578,582 B / 22,413 行）

**学习范围**：`Alwaysoffline\1004\MarketplaceSkus.json`（**10,056 products + 12,349 skus**）
**性质**：全实测（**用 `ConvertFrom-Json` 完整解析后做全量统计,不是抽样**）
**★★★★★ 本报告收录全部 7 个字段的穷尽统计**：12 种 grant type / 53 种 type·subtype / 8 类 tag / 12 档时长 / 210 个不同价格

---

## 一、★★★★★ 顶层结构

```json
{
  "formatVersion": 2,
  "source": {
    "titleId": 1004,
    "tables": {
      "skus":          "mp_comarketplaceskus.csv",
      "products":      "mp_comarketplaceproducts.csv",
      "product_items": "mp_comarketplaceproductitems.csv",
      "items":         "mp_coMarketplaceItems.csv"
    },
    "skuCount": 12349,
    "productCount": 10056,
    "additionalProductItemCount": 63
  },
  "products": [ … 10,056 项 … ],
  "skus":     [ … 12,349 项 … ]
}
```

| 项 | 值 |
|---|---|
| **`formatVersion`** | **2** |
| **`titleId`** | ★ **1004** ✓（与 `Platform.json` / 目录名 / `mp_playlists` 一致） |
| **`skuCount`** | **12,349** ✓（实测 `skus` 数组长度 = 12,349） |
| **`productCount`** | **10,056** ✓（实测 `products` 数组长度 = 10,056） |
| **`additionalProductItemCount`** | ★ **63** |

### ★★★★★ 四个来源 CSV（**首次完整列出**）

| 键 | **CSV 文件名** |
|---|---|
| **`skus`** | **`mp_comarketplaceskus.csv`** |
| **`products`** | **`mp_comarketplaceproducts.csv`** |
| **`product_items`** | **`mp_comarketplaceproductitems.csv`** |
| **`items`** | ★ **`mp_coMarketplaceItems.csv`**（★ 注意 `co` 小写,其余是 `co` 后接 `marketplace` 全小写） |

★★★ **⇒ 命名不一致：`mp_co**m**arketplaceskus` vs `mp_co**M**arketplaceItems`**
**⇒ 前三个是 `comarketplace*`（全小写 m）,第四个是 `coMarketplace*`（大写 M）。**
**⇒ 这是**上游 CSV 的真实文件名**,不是转换错误。**

---

## 二、★★★★★ `products[]` 的 7 个字段

| 字段 | 出现次数 | 占比 |
|---|---|---|
| **`productId`** | **10,056** | **100%** |
| **`grants`** | **10,056** | **100%** |
| **`requirement`** | **3,188** | **31.7%** |
| **`requirementValue`** | **3,185** | **31.7%** |
| **`name`** | ★ **31** | **0.31%** |
| **`icon`** | ★ **31** | **0.31%** |
| **`description`** | ★ **31** | **0.31%** |

★★★ **⇒ 只有 **31 个 product**（0.31%）带 `name`/`icon`/`description`** ⇒ 其余 **10,025 个**没有。**
**⇒ 即：绝大多数商品的显示名由**其他机制**提供（可能是 `items` 表或客户端本地化串）。**

### ★★★ `requirement` 的 3,188 vs `requirementValue` 的 3,185（差 3）

★★ **⇒ 有 **3 个 product** 有 `requirement` 但**没有** `requirementValue`。**

### ★★★★★ `requirement` 的完整分布（**只有 1 个非武器项 + 约 200 个武器解锁**）

```
**`uf_prestige_rank`**          ⇒ **466** 个  ★★★ **唯一非武器前缀**
**`uf_<weapon>_mp_rank`**       ⇒ **约 2,719 个**（每把武器 2–25 个）
        ↓
★★★ 总计 **3,188** ✓
```

| 武器 | `requirement` 条数 |
|---|---|
| **`uf_scarsapr_mp_rank`** | **25** |
| `uf_scar_mp_rank` / `uf_ff58_mp_rank` / `uf_m14ebr_mp_rank` | **24** |
| `uf_famas_mp_rank` / `uf_type95_mp_rank` / `uf_acr_mp_rank` / `uf_m16_mp_rank` / `uf_m4_mp_rank` / `uf_fn2000_mp_rank` / `uf_spbc_mp_rank` / `uf_m16se_mp_rank` | **23** |
| `uf_tar21_mp_rank` / `uf_ak104common_mp_rank` / `uf_an94_mp_rank` / … | **22** |
| … | 递减 |
| ★ **`uf_coltanaconda_mp_rank`** | ★ **2**（最少） |

★★★ **⇒ 完整的解锁模型：**
```
**军衔解锁**（`uf_prestige_rank`）⇒ **466 个商品**
**武器等级解锁**（`uf_<weapon>_mp_rank`）⇒ **约 2,719 个商品**
        ↓
★★★ ⇒ 即：**商店里绝大多数东西要"用某把枪打到某个等级"才解锁**
   ⇒ 这是一个**武器进度驱动的解锁体系**
```

★ **⇒ 约 **200 把武器**出现在 `requirement` 里（含大量皮肤变体：`coral` / `tile` / `event` / `wargod` / `insect` / `hex` / `gld` / `irradiated` / `paladin` / `ninja` / `crayon` / `octopus` / `heaven` / `judge` / `scrawl` / `candy` / `3kingdoms` / `3kingdoms` …）**

---

## 三、★★★★★ `grants[]` 的 **12 种 type**（完整）

| `type` | 数量 | 占比 | **样例 name** | 语义 |
|---|---|---|---|---|
| **`wat`** | ★★★ **7,469** | **74.3%** | `mag_flechette`（`subtype: mag`） | ★★★ **武器附件**（Weapon Attachment） |
| **`cat`** | **1,213** | 12.1% | `heg_scarfmask`（`subtype: heg`） | ★ **角色装扮**（Character Accessory Type?） |
| **`pcb`** | **400** | 4.0% | `pcb_landscape06` | ★ **玩家卡背景**（Player Card Background） |
| **`wea`** | **376** | 3.7% | `m4_mp`（`subtype: ast`） | ★ **武器**（Weapon） |
| **`pct`** | **215** | 2.1% | `pct_basic6` | ★ **玩家称号**（Player Card Title） |
| **`pci`** | **139** | 1.4% | `pci_emblems22` | ★ **玩家卡图标**（Player Card Icon） |
| **`itm`** | **95** | 0.9% | `loadout4enable`（`subtype: cac`） | ★ **功能项**（如"解锁配装槽 4"） |
| **`kis`** | **56** | 0.6% | `uav` | ★ **连杀奖励**（Killstreak） |
| **`equ`** | **55** | 0.5% | `frag_grenade_mp`（`subtype: let`） | ★ **装备**（Equipment） |
| **`per`** | **48** | 0.5% | `specialty_marathon`（`subtype: pk3`） | ★ **特长**（Perk） |
| **`cha`** | **32** | 0.3% | `cha_INFbaseA`（`subtype: cha`） | ★ **角色模型**（Character） |
| **`bdg`** | **21** | 0.2% | `badge_veteran` | ★ **徽章**（Badge） |
| **合计** | **10,119** | — | — | （**10,056 product** 共 **10,119 个 grant**） |

★★★ **⇒ `wat`（武器附件）占 74.3%** ⇒ **这个商店的主体是武器配件。**

★★ **⇒ `pcb` / `pci` / `pct` 三个前缀语义一致：**
```
`pcb` = **Player Card Background**（背景）
`pci` = **Player Card Icon**（图标）
`pct` = **Player Card Title**（称号）
        ↓
★ 三者合计 **754 个** ⇒ 玩家卡装饰是第二大品类
```

### ★★★★★ 53 种 `type/subtype` 组合（Top 20）

| 组合 | 数量 | | 组合 | 数量 |
|---|---|---|---|---|
| **`wat/cam`** | ★ **2,147** | | **`pct/(none)`** | **215** |
| **`wat/sco`** | **1,321** | | **`cat/han`** | **199** |
| **`wat/mag`** | **1,021** | | **`cat/heg`** | **188** |
| **`wat/bas`** | **745** | | **`cat/fja`** | **180** |
| **`wat/muz`** | **667** | | **`cat/fpa`** | **163** |
| **`wat/cqc`** | **589** | | **`pci/(none)`** | **139** |
| **`wat/sra`** | **536** | | **`wea/ast`** | **124** |
| **`pcb/(none)`** | **400** | | **`cat/ves`** | **90** |
| **`wat/iro`** | **313** | | **`kis/(none)`** | **56** |
| **`cat/eye`** | **301** | | **`wat/ret`** | **55** |

### ★★★★★ **9 种武器附件 subtype（`wat/*`）**

| subtype | 数量 | 语义 |
|---|---|---|
| **`cam`** | **2,147** | ★ **迷彩**（Camo） |
| **`sco`** | **1,321** | ★ **瞄准镜**（Scope） |
| **`mag`** | **1,021** | ★ **弹匣**（Magazine） |
| **`bas`** | **745** | ★ **基础/底座**（Base?） |
| **`muz`** | **667** | ★ **枪口**（Muzzle） |
| **`cqc`** | **589** | ★ **近战**（CQC） |
| **`sra`** | **536** | ★ **侧轨**（Side Rail?） |
| **`iro`** | **313** | ★ **红点/光学**（IR Optic） |
| **`ret`** | **55** | ★ **准星**（Reticle） |
| **合计** | **7,394** | （+ 其他 75） |

★★★ **⇒ 迷彩（`cam`）是最大单项（2,147）⇒ **皮肤是商店的第一大商品。****

### ★★★ 5 种角色装扮 subtype（`cat/*`）

| subtype | 数量 |
|---|---|
| **`eye`** | **301** |
| **`han`** | **199** |
| **`heg`** | **188** |
| **`fja`** | **180** |
| **`fpa`** | **163** |
| **`ves`** | **90** |

★★ **⇒ 6 种（不只 5 种）⇒ 合计 **1,121**。**

★ **⇒ 这些三字母缩写是**零售的角色槽位代号**（`eye`=眼镜 / `han`=手 / `heg`=头饰 / `fja`/`fpa`/`ves`=身体部件）。**

---

## 四、★★★★★ `skus[]` 的 7 个字段

| 字段 | 出现次数 | 占比 |
|---|---|---|
| **`sku`** | **12,349** | **100%** |
| **`productId`** | **12,349** | **100%** |
| **`prices`** | **12,104** | **98.0%** |
| **`durationDays`** | **3,574** | **28.9%** |
| **`availableFrom`** | **3,514** | **28.5%** |
| **`availableUntil`** | **3,513** | **28.4%** |
| **`tags`** | ★★ **32** | **0.26%** |

★★★★★ **⇒ 关键：字段名是 `sku`,不是 `skuId`！**
```
早前记录（报告 055）："`"skuId"` 和 `"price"` 都是 **0 次出现**"
        ↓
★★★ 本次实测：字段名是 **`sku`**（12,349 次）与 **`prices`**（数组,12,104 次）
        ↓
★★★★★ ⇒ "0 次"是**对的**,但原因是**字段名不同**,不是"数据缺失"
   ⇒ 更正报告 055 的解读：**数据完整,只是键名是 `sku` / `prices`**
```

### ★★★ `prices[]` 的 **只有 2 个 column**

| `column` | 数量 | 占比 |
|---|---|---|
| **`2`** | **5,611** | **46.4%** |
| **`5`** | **6,494** | **53.6%** |
| **合计** | **12,105** | — |

★★★ **⇒ 只有两种货币栏（`column 2` 与 `column 5`）。**

★★ **⇒ 结合报告 077 的 `[supply_drop_info]`：**
```
`60217_DustSKU=22644` / `60217_DustRequirement=100`  ⇒ **Dust（尘）**
`11861_DustSKU=25748` / `11861_DustRequirement=100`
        ↓
★ 推测：`column 2` 与 `column 5` 对应**两种货币**（可能是 GP 与 CP，或 GP 与 Dust）
   ⇒ ★ **未实测,仅记录为候选**
```

### ★★★★★ 价格金额统计（**完整**）

| 项 | 值 |
|---|---|
| **条数** | **12,105** |
| **最小值** | ★ **0**（有免费项） |
| **最大值** | ★★ **999,999** |
| **不同值个数** | ★ **210** |
| **恰好 = 99,999** | ★★★ **3,281**（**27.1%**） |

### ★★★ 价格区间分布

| 区间 | 条数 | 占比 |
|---|---|---|
| **0 – 999** | **4,481** | **37.0%** |
| **1,000 – 4,999** | **3,348** | **27.7%** |
| **5,000 – 9,999** | **733** | **6.1%** |
| **10,000 – 29,999** | **257** | **2.1%** |
| ★ **30,000 – 99,998** | ★★★ **0** | ★★★ **0%** |
| ★★★ **≥ 99,999** | **3,286** | **27.1%** |

★★★★★ **⇒ `30,000–99,998` 区间**完全为空** ⇒ 价格是**双峰分布**：**
```
**低端**（< 5,000）⇒ **7,829 条（64.7%）** ⇒ 正常商品
**高端**（≥ 99,999）⇒ **3,286 条（27.1%）** ⇒ ★★★ **占位/不可购买**
        ↓
★★★ 中间 **30,000–99,998** 一条都没有 ⇒ **99,999 是一个硬上限/哨兵**
```

★★ **⇒ 最可能的解释：`99999` 是**"不可用/占位"的哨兵价**（类似 `end_time=2147483647` 的手法）。**

### ★★★ Top 10 常见价格

| 价格 | 次数 |
|---|---|
| ★ **99,999** | **3,281** |
| **5,003** | **613** |
| **753** | **391** |
| **380** | **365** |
| **480** | **296** |
| **580** | **284** |
| **680** | **267** |
| **880** | **240** |
| **1,080** | **238** |
| **1,000** | **234** |

★★★ **⇒ 从 380 起以 **100** 递增（380/480/580/680/880/1,080）⇒ **定价阶梯是 100 的倍数。**
**⇒ 而 `753` 与 `5,003` 是**非整数阶梯**的值（`5,003` = 5,000 + 3）⇒ 可能是**折扣后价**。**

### ★★★★ `durationDays` 的 12 档

| 天数 | 数量 | | 天数 | 数量 |
|---|---|---|---|---|
| **1** | **140** | | **14** | ★★ **690** |
| **2** | ★ **1** | | **15** | **20** |
| **3** | **218** | | **30** | ★★ **902** |
| **5** | **109** | | **40** | ★ **1** |
| **7** | ★★★ **957** | | **60** | **21** |
| **10** | **101** | | **90** | **414** |
| **合计** | — | | | **3,574** ✓ |

★★★ **⇒ 三个主力时长：7 天（957）/ 30 天（902）/ 14 天（690）⇒ 合计 2,549（71.3%）。**

★ **⇒ `2 天` 与 `40 天` 各只有 **1 个** ⇒ **异常/测试值**。**

### ★★★★ `availableFrom` / `availableUntil` 的范围

| 项 | 最小值 | 最大值 |
|---|---|---|
| **`availableFrom`** | **1433986200** = ★ **2015-06-11** | **2018236644** = ★★ **2033-12-15** |
| **`availableUntil`** | **1437407999** = **2015-07-20** | **2018275200** = ★★ **2033-12-15** |

★★★ **⇒ 时间跨度 **2015-06-11 → 2033-12-15**（**18.5 年**）。**
**⇒ `2033-12-15` 显然是一个**远期哨兵**（类似报告 078 的 `INT32_MAX` / 2038）。**

★★ **⇒ 且有 **3,514 个 `availableFrom`** 与 **3,513 个 `availableUntil`**（差 1）⇒ **有 1 个 sku 只有起点没有终点**（或反之）。**

---

## 五、★★★★★ `tags` 的 **8 类**（只有 32 个 SKU）

### 5.1 ★★★ 完整的 32 个带 tag 的 SKU

```
sku=180    [POPULAR:6]
sku=241    [HOT:7, NEW:3]                       ← ★ 双 tag
sku=1125   [POPULAR:2]
sku=2110   [RECOMMEND:3]
sku=11455  [RECOMMEND:2]
sku=11551  [RECOMMEND:3]
sku=13773  [RECOMMEND:5]
sku=13777  [RECOMMEND:10]
sku=13782  [RECOMMEND:9]
sku=13787  [RECOMMEND:7]
sku=13800  [RECOMMEND:2]
sku=13806  [RECOMMEND:8]
sku=15827  [POPULAR:10]
sku=16118  [RECOMMEND:6]
sku=16381  [HOT:10]
sku=17200  [RECOMMEND:4]
sku=18266  [POPULAR:9]
sku=19483  [POPULAR:3]
sku=20142  [POPULAR:4]
sku=21252  [POPULAR:5]
sku=21477  [POPULAR:7]
sku=23556  [AD_RECOMMEND:4, RECOMMEND:1, HOT:6]  ← ★ 三 tag
sku=24106  [HOT:4]
sku=24216  [HOT:5]
sku=24784  [POPULAR:8]
sku=27602  [AD_POPULAR:3, POPULAR:1, HOT:3]      ← ★ 三 tag
sku=29705  [AD_NEW:2, NEW:2, HOT:2]              ← ★ 三 tag
sku=29726  [AD_HOT:1, HOT:1, NEW:1]              ← ★ 三 tag
sku=31187  [HOT:8, NEW:4]
sku=31188  [NEW:7]
sku=31189  [HOT:9, NEW:5]
sku=31190  [NEW:6]
```

### ★★★★★ 8 类 tag 与它们的**配对规律**

| tag 族 | 出现的 sku | 说明 |
|---|---|---|
| **`HOT`** | 180? 否 → 241, 16381, 23556, 24106, 24216, 27602, 29705, 29726, 31187, 31189 | **10 个** |
| **`NEW`** | 241, 29705, 29726, 31187, 31188, 31189, 31190 | **7 个** |
| **`POPULAR`** | 180, 1125, 15827, 18266, 19483, 20142, 21252, 21477, 24784, 27602 | **10 个** |
| **`RECOMMEND`** | 2110, 11455, 11551, 13773, 13777, 13782, 13787, 13800, 13806, 16118, 17200, 23556 | **12 个** |
| **`AD_RECOMMEND`** | **23556** | ★ **1 个** |
| **`AD_POPULAR`** | **27602** | ★ **1 个** |
| **`AD_NEW`** | **29705** | ★ **1 个** |
| **`AD_HOT`** | **29726** | ★ **1 个** |

★★★★★ **⇒ 四个 `AD_*` tag 各只出现 **1 次**,且**都与同类非 AD tag 同时出现**：**
```
`AD_RECOMMEND:4` + `RECOMMEND:1` + `HOT:6`    ⇒ sku 23556
`AD_POPULAR:3`   + `POPULAR:1`   + `HOT:3`    ⇒ sku 27602
`AD_NEW:2`       + `NEW:2`       + `HOT:2`    ⇒ sku 29705
`AD_HOT:1`       + `HOT:1`       + `NEW:1`    ⇒ sku 29726
        ↓
★★★ ⇒ 四个 `AD_*` 的 sku 号 **连续/接近**（23556, 27602, 29705, 29726）
   ⇒ **这 4 个是"广告位"标记**,其余 28 个是"自然榜单"标记
```

★ **⇒ 格式 `TAG:序号` 与报告 077 的 `sku_tags.info` **完全一致**：**
```
`sku_tags.info`：`45542=HOT:1` / `45533=HOT:2` / …
本文件：        `sku=241 → [HOT:7, NEW:3]`
        ↓
★★★ ⇒ **同一套 tag 体系的两种存储形态**
   （`.info` 按 item_id 索引；`.json` 内嵌在 sku 上）
```

★★ **⇒ 但**两处的 sku/item 编号完全不同**：**
```
`sku_tags.info` 用 **item_id**（45542 / 45533 / 45137 …）
`MarketplaceSkus.json` 用 **sku 号**（180 / 241 / 1125 …）
        ↓
★ ⇒ **`sku_tags.info` 是另一套索引**（可能是 `ui_dmz_bcl_ad` 那种"广告位 item"）
```

---

## 六、★★★★ `grants` 数量的分布

| `grants` 数 | product 数 | 占比 |
|---|---|---|
| **1** | ★★★ **10,030** | **99.74%** |
| **2** | **8** | 0.08% |
| **3** | **8** | 0.08% |
| **4** | **4** | 0.04% |
| **5** | **3** | 0.03% |
| **6** | **3** | 0.03% |
| **合计** | **10,056** ✓ | **100%** |

★★★ **⇒ **99.74% 的 product 只给 1 个东西** ⇒ 商店基本是"一商品一物品"。**
**⇒ 只有 **26 个 product** 是**礼包**（2–6 个 grant）。**

★★ **⇒ 且这 26 个礼包与报告中的 31 个带 `name` 的 product**高度重叠**：**
```
31 个带 name 的 product 里，绝大多数名字是 **`MARKETPLACE_BUNDLE_*`**
（`BUNDLE_SHEVETERANB` / `BUNDLE_MUSTANG` / `BUNDLE_SUPREME_WEAPONS` /
  `BUNDLE_HELLWALKER` / `BUNDLE_PVEREAPER` / `BUNDLE_COLORFUL_CAMS` …）
        ↓
★★★ ⇒ **"礼包"是唯一需要显示名/图标/描述的商品类别**
   ⇒ 单品不需要（名字从 `items` 表来）
```

### ★★★ 31 个带 `name` 的 product 的完整分类

| 类别 | 数量 | 例子 |
|---|---|---|
| **`MARKETPLACE_BUNDLE_*`** | ★ **19** | `SHEVETERANB` / `SHEVETERANC` / `SHEVETERAND` / `SHEPRESTIGEA` / `SHEPRESTIGEB` / `MUSTANG` / `PVEREAPER`(×2) / `SUPREME_WEAPONS`(×4) / `COLORFUL_CAMS` / `LABORDAY` / `KAWAII_CAMS` / `HELLWALKER` |
| **`MARKETPLACE_BAR_*`** | ★ **8** | `GHILLIE_BASIC_CAMO` / `GHILLIE_WINTER_CAMO` / `GHILLIE_GRASS_CAMO` / `GHILLIE_FOREST_CAMO` / `INF_TOMAHAWK_BUNDLE` / `INF_GCD_BUNDLE` / `INF_SKATE_BUNDLE` / `SHE_ATHENA_BUNDLE` / `INF_MONKEYKING_BUNDLE` / `INF_STUDENT_BUNDLE`(×2) / `INF_STUDENTSAILORB/C/D_BUNDLE` |
| **`MARKETPLACE_ZOMBIEHUNTERA_NAME`** | **1** | — |

★★★ **⇒ 两个前缀：`MARKETPLACE_BUNDLE_`（通用礼包）与 `MARKETPLACE_BAR_`（"BAR" = ?）**
**⇒ `BAR` 可能是**"Bargain"（特惠）**或某个分类代号。**

★★ **⇒ 且 `SUPREME_WEAPONS` 的**同一名字被 4 个不同 productId 复用**（10693 / 10819 / 11411 / 12078）
⇒ **同一礼包的不同售卖批次**。**

★ **⇒ 有 **2 个** `PVEREAPER`（10483 / 10822）和 **2 个** `STUDENT_BUNDLE`（21809 / 21810）
⇒ 同样是**多批次**。**

### ★★★ `icon` 的命名规律

```
`gift_box_*`   ⇒ 礼包（`gift_box_mustang` / `gift_box_PVE` / `gift_box_LuxuryWeapons` /
                          `gift_box_ColorCams` / `gift_box_LabourDay` / `gift_box_KawaiiCam` /
                          `gift_box_hellwalker`）
`bar_*_item_icon` ⇒ BAR 类（`bar_SNIbasic_item_icon` / `bar_INFbundleA_item_icon` / …）
`zombiehunterA`   ⇒ 单个（无后缀）
        ↓
★★★ ⇒ **图标命名有 3 种模式**，与 `name` 前缀一一对应
```

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★ 文件规模 | **2,578,582 B / 22,413 行** |
| 2 | ★ 顶层 | `formatVersion`=**2** / `titleId`=**1004** / `skuCount`=**12,349** ✓ / `productCount`=**10,056** ✓ / `additionalProductItemCount`=**63** |
| 3 | ★★★★★ **4 个来源 CSV** | `mp_co**m**arketplaceskus.csv` / `mp_co**m**arketplaceproducts.csv` / `mp_co**m**arketplaceproductitems.csv` / ★ **`mp_co**M**arketplaceItems.csv`**（★ 大小写不一致） |
| 4 | ★★ `products[]` 字段 | **7 个**：`productId`(100%) `grants`(100%) `requirement`(31.7%) `requirementValue`(31.7%) **`name`/`icon`/`description` 各 31 个(0.31%)** |
| 5 | ★★ `requirement` 两种 | ★ **`uf_prestige_rank`（466 个,唯一非武器项）** + **`uf_<weapon>_mp_rank`（约 2,719 个,~200 把武器）** |
| 6 | ★★★ 解锁模型 | **军衔解锁 466 + 武器等级解锁 2,719** ⇒ **武器进度驱动的解锁体系** |
| 7 | ★★★ `requirement` 条数极值 | 最多 **`uf_scarsapr_mp_rank`=25** / 最少 **`uf_coltanaconda_mp_rank`=2** |
| 8 | ★★★★★ **12 种 grant type** | **`wat` 7,469(74.3%)** / `cat` 1,213 / `pcb` 400 / `wea` 376 / `pct` 215 / `pci` 139 / `itm` 95 / `kis` 56 / `equ` 55 / `per` 48 / `cha` 32 / `bdg` 21 |
| 9 | ★★ grant 总数 | **10,119**（10,056 product） |
| 10 | ★★★ `pcb`/`pci`/`pct` | **Player Card Background / Icon / Title**（合计 **754**） |
| 11 | ★★★★★ **9 种 `wat/*` subtype** | **`cam` 2,147（迷彩,最大）** / `sco` 1,321 / `mag` 1,021 / `bas` 745 / `muz` 667 / `cqc` 589 / `sra` 536 / `iro` 313 / `ret` 55 |
| 12 | ★★★ **6 种 `cat/*` subtype** | `eye` 301 / `han` 199 / `heg` 188 / `fja` 180 / `fpa` 163 / `ves` 90 |
| 13 | ★★ type·subtype 组合数 | **53 种** |
| 14 | ★★★★★ **`skus[]` 字段名更正** | 字段是 **`sku`**（不是 `skuId`）与 **`prices`**（不是 `price`）⇒ **更正报告 055 的"0 次出现"解读：数据完整,只是键名不同** |
| 15 | ★★★ `prices[]` | **只有 2 个 column**：**`2`(5,611)** 与 **`5`(6,494)** |
| 16 | ★★★★★ **价格统计** | **12,105 条** / min **0** / max **999,999** / **210 个不同值** / **`99999` 出现 3,281 次(27.1%)** |
| 17 | ★★★★★ **双峰价格 + 空区间** | **0–999: 4,481** / **1,000–4,999: 3,348** / 5,000–9,999: 733 / 10,000–29,999: 257 / ★★ **30,000–99,998: 0** / **≥99,999: 3,286** |
| 18 | ★★★ `99999` 的判定 | ★ **占位/不可购买的哨兵价**（中间区间完全为空） |
| 19 | ★★ 定价阶梯 | **380/480/580/680/880/1,080** ⇒ **100 的倍数**；`753`/`5,003` 是**非阶梯值**（可能是折扣价） |
| 20 | ★★★★ **`durationDays` 12 档** | **7 天 957** / **30 天 902** / **14 天 690**（三者占 71.3%）；★ **2 天与 40 天各只 1 个**（异常值） |
| 21 | ★★★ `availableFrom/Until` | **2015-06-11 → 2033-12-15**（**18.5 年**）；`2033-12-15` 是**远期哨兵** |
| 22 | ★ 数量差 | `availableFrom` **3,514** vs `availableUntil` **3,513**（**差 1**） |
| 23 | ★★★★★ **`tags` 只有 32 个 SKU** | **8 类**：`HOT`/`NEW`/`POPULAR`/`RECOMMEND` + ★★ **4 个 `AD_*`（各只 1 次）** |
| 24 | ★★★ **4 个 `AD_*` 的 sku** | **23556 / 27602 / 29705 / 29726** ⇒ 都与同类非 AD tag 同时出现 ⇒ **"广告位"标记** |
| 25 | ★★★ tag 格式 | `TAG:序号` ⇒ 与报告 077 的 **`sku_tags.info` 同一套体系**（但那边按 **item_id** 索引,这边按 **sku 号**） |
| 26 | ★★★★ **`grants` 数量** | **1 个：10,030（99.74%）**；2–6 个合计 **26 个** ⇒ **商店基本"一商品一物品"** |
| 27 | ★★★ 26 个礼包 | 与 **31 个带 `name` 的 product** 高度重叠 ⇒ **只有礼包需要显示名/图标/描述** |
| 28 | ★★ 31 个 name 的两个前缀 | **`MARKETPLACE_BUNDLE_`（19）** + **`MARKETPLACE_BAR_`（~11）** + `ZOMBIEHUNTERA`（1） |
| 29 | ★★ 多批次商品 | `SUPREME_WEAPONS` **4 个 productId**（10693/10819/11411/12078）；`PVEREAPER` **2 个**；`STUDENT_BUNDLE` **2 个** |
| 30 | ★ 图标三模式 | **`gift_box_*`** / **`bar_*_item_icon`** / 单个（`zombiehunterA`）⇒ 与 name 前缀一一对应 |

---

## 八、结论

### 1. ★★★★★ **`wat`（武器附件）占 74.3%,迷彩是最大单项**

```
**9 种附件 subtype**：`cam`(迷彩) 2,147 / `sco` 1,321 / `mag` 1,021 /
                     `bas` 745 / `muz` 667 / `cqc` 589 / `sra` 536 / `iro` 313 / `ret` 55
        ↓
★★★ ⇒ **这个商店的主体是"武器皮肤 + 配件"**
```

### 2. ★★★★★ **价格是双峰分布,`99,999` 是哨兵价**

```
**0–4,999**   ⇒ **7,829 条(64.7%)** ⇒ 正常商品
★★★ **30,000–99,998 区间完全为空**
**≥ 99,999**  ⇒ **3,286 条(27.1%)** ⇒ 占位/不可购买
```

### 3. ★★★★★ **解锁是"武器进度驱动"的**

```
**`uf_prestige_rank`**（军衔）⇒ **466 个商品**
**`uf_<weapon>_mp_rank`**（某枪到某级）⇒ **约 2,719 个商品**（约 200 把武器）
        ↓
★★★ ⇒ 商店里绝大多数东西要**用特定武器打到特定等级**才解锁
```

### 4. ★★★★★ **更正报告 055：字段名是 `sku` / `prices`,不是 `skuId` / `price`**

★ **⇒ 数据**完整**,"0 次出现"只是**键名不同**。**

### 5. ★★★★ **只有 32 个 SKU 有 tag,其中 4 个是 `AD_*`（广告位）**

★ **⇒ 与 `sku_tags.info` 是**同一套 tag 体系的两种存储形态**（一个按 item_id,一个按 sku 号）。**

### 6. ★★★ **99.74% 的 product 只给 1 个物品**（商店是"一商品一物品"）

★ **⇒ 只有 26 个礼包（2–6 个 grant）,且它们正是**唯一需要显示名/图标/描述**的类别。**

### 7. ★★★ **`durationDays` 三档主力**（7/30/14 天占 71.3%），**2 天与 40 天是异常值**

### 8. ★★ **时间跨度 2015-06-11 → 2033-12-15**,`2033-12-15` 是远期哨兵

---

## 九、下一步

- 两个插件（`CodolGameServer.Localnet32` / `Alwaysoffline.Localnet32`）的完整字符串面清单
- 最终收尾报告
