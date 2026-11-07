# 学习报告 005（重开）— `ol-mod-runtime-manifest.json`（28,209 B）

**学习范围**：`payload\Ayria\ol-mod-runtime-manifest.json` + `1004\MarketplaceSkus.json` 头部
**方法**：Grep 提取全部声明路径 + 与 `MANIFEST.sha256` 逐条对照
**性质**：全实测
**★★★ 本报告给出"交付包 = ol-mod 运行清单的子集"的完整差集**

---

## 一、★★★ `ol-mod-runtime-manifest.json` 的头部（逐字节）

```json
{
    "schemaVersion":  1,
    "project":  "ol-mod",
    "titleId":  1004,
    "architecture":  "x86",
    "configuration":  "release",
    "gameExecutable":  "codoMP_client_shipRetail.exe",
    "files":  [ ... ]
}
```

★★★ **注意格式细节（逐字节特征）**：

| 特征 | 值 | 含义 |
|---|---|---|
| 缩进 | **4 空格** | |
| 键值分隔 | **`:  `（冒号 + 两个空格）** | ★★ **PowerShell `ConvertTo-Json` 的特征** |
| 数组元素缩进 | 18 空格（深层） | |
| 根键顺序 | `schemaVersion`→`project`→`titleId`→… | 字母序 |

★★★ **⇒ `:  `（双空格）**是 **PowerShell `ConvertTo-Json` 的默认输出**，**
**`MANIFEST_SUMMARY.txt` 和 `MANIFEST.sha256` 也是 `-f` 格式化的产物 ——
**⇒ 这几个文件是**同一个 PowerShell 打包脚本**生成的。**

---

## 二、★★★ 每个条目的字段规范（逐字节）

```json
{
    "path":  "Ayria/Assets/OlMod/GameScripts/common.lua",
    "size":  2866,
    "sha256":  "A1761E1B546EDE23BD7FBA10579181ACF7145B89BBC635BBCD1DB44A26B781A2",
    "source":  "assets/game_scripts/common.lua",
    "kind":  "gameplay-script",
    "origin":  "ol-mod authoritative gameplay source",
    "role":  "dedicated map and gametype orchestration",
    "installPolicy":  "replace",
    "mutable":  false
}
```

### ★★★ 10 个字段的语义

| 字段 | 含义 |
|---|---|
| `path` | **安装到游戏根的目标路径**（含 `Ayria/` 前缀） |
| `size` | 字节数 |
| `sha256` | 大十六进制哈希（与 `MANIFEST.sha256` **一致**，见 §4 验证） |
| `source` | ★★ **上游 ol-mod 源路径**（`assets/...`） |
| `kind` | 类别（`gameplay-script` / `asset` / `seed`） |
| `origin` | ★★★ **来源说明**（见下） |
| `role` | 用途 |
| `installPolicy` | ★★★ **安装策略**（`replace` / `if-missing`） |
| `mutable` | ★★★ **是否可变**（`true` = 用户数据） |

### ★★★ `origin` 的四种取值（实测）

```
"ol-mod authoritative gameplay source"        ← 自研玩法脚本
"ol-mod captured publisher-file keystream"    ← 抓取的发布文件密钥流
"ayriax3/1/Ayria/Assets/Alwaysoffline/1004 player seed"      ← 玩家种子
"ayriax3/1/Ayria/Assets/Alwaysoffline/1004/Server"           ← 发布服务器资产
```

★★★ **⇒ `ayriax3/1/` 是一个**归档来源**（可能是某次客户端包/补丁的编号）。**

### ★★★ `installPolicy` 的两种取值

```
"replace"      覆盖安装（资产类）
"if-missing"   ★ 仅在缺失时安装（种子类，mutable=true）
```

★★★ **⇒ **玩家种子用 `if-missing`** —— 不覆盖用户存档。这是正确设计。**

---

## 三、★★★ 全部 44 个声明条目（按类别分组）

### A. `gameplay-script`（**7 个**，全部 `replace` / `mutable=false`）

```
Ayria/Assets/OlMod/GameScripts/common.lua
Ayria/Assets/OlMod/GameScripts/gametypes/cha.lua
Ayria/Assets/OlMod/GameScripts/gametypes/dm.lua
Ayria/Assets/OlMod/GameScripts/gametypes/coop.lua
Ayria/Assets/OlMod/GameScripts/gametypes/zm.lua
Ayria/Assets/OlMod/GameScripts/gametypes/sd.lua
Ayria/Assets/OlMod/GameScripts/gametypes/dmz.lua
Ayria/Assets/OlMod/GameScripts/gametypes/td.lua
Ayria/Assets/OlMod/GameScripts/gametypes/zhunt.lua
Ayria/Assets/OlMod/GameScripts/gametypes/zarena.lua
Ayria/Assets/OlMod/GameScripts/maps/mp_crash_tropical.lua
Ayria/Assets/OlMod/GameScripts/maps/coop_training_mp_cargoship.lua
Ayria/Assets/OlMod/GameScripts/maps/mp_nuked.lua
Ayria/Assets/OlMod/GameScripts/maps/zm_factory_sh.lua
```

★★ **实为 **14 个** script（10 gametype + 4 map）。**
★★★ **⇒ `conf.lua` / `war.lua` 和其余 **15 个 map** 不在声明里 —— 它们是**后加的**。**

★ **与 `conf.lua` 注释自述"我加入前目录里有 cha/coop/dm/dmz/sd/td/war/zm/zhunt/zarena"** 吻合
（那份清单**含 war**、**不含 conf**；本清单**不含 war**、**不含 conf**）。

### B. `asset`（**20 个**，全部 `replace` / `mutable=false`）

```
Ayria/Assets/Alwaysoffline/1004/Keystreams/configs_s.keystream     ← ★★★ 见 §5
Ayria/Assets/Alwaysoffline/1004/Server/tlogconfig.info
Ayria/Assets/Alwaysoffline/1004/Server/sku_tags.info
Ayria/Assets/Alwaysoffline/1004/Server/whitelist_tester.info
Ayria/Assets/Alwaysoffline/1004/MarketplaceSkus.json
Ayria/Assets/Alwaysoffline/1004/Cloud/iotd-english.jpg.Manifest    ← ★★★ 见 §5
Ayria/Assets/Alwaysoffline/1004/Cloud/iotd-english.jpg             ← ★★★
Ayria/Assets/Alwaysoffline/1004/Cloud/iotd-english.png.Manifest    ← ★★★
Ayria/Assets/Alwaysoffline/1004/Cloud/iotd-english.png             ← ★★★
Ayria/Assets/Alwaysoffline/1004/Server/market_ui.info
Ayria/Assets/Alwaysoffline/1004/Server/market-down.info
Ayria/Assets/Alwaysoffline/1004/Server/MOTD.info
Ayria/Assets/Alwaysoffline/1004/Server/selected_playlist.txt
Ayria/Assets/Alwaysoffline/1004/Server/mp_playlists_shipRetail_release.info
Ayria/Assets/Alwaysoffline/1004/Server/daily_challenge_config.info
Ayria/Assets/Alwaysoffline/1004/Server/activities_v1.info
Ayria/Assets/Alwaysoffline/1004/Server/configs_s.info
Ayria/Assets/Alwaysoffline/1004/Server/broadcast.info
Ayria/Assets/Platformwrapper/Platform.json
Ayria/Assets/Alwaysoffline/Identity.json
```

### C. `seed`（**2 个**，`if-missing` / **`mutable=true`**）

```
Ayria/Assets/Alwaysoffline/1004/1100001DEADC0DE/the.json
Ayria/Assets/Alwaysoffline/1004/1100001DEADC0DE/Publicprofile
```

### D. 二进制/可执行（**7 个**）

```
Ayria/Plugins/CodolGameServer.Localnet32
Ayria/Plugins/Localnetworking.Ayria32
Ayria/Plugins/Alwaysoffline.Localnet32
Ayria/Plugins/Platformwrapper.Ayria32
Ayria/Bootstrapper32.dll
Ayria/Injector32.exe
Ayria/ol_room_owner.exe
```

### E. 其他（**1 个**）

```
Launch_OLMod.bat          ← ★★★ 见 §5
```

---

## 四、★★★ 声明哈希与 `MANIFEST.sha256` 的**一致性验证**

| 文件 | runtime-manifest | MANIFEST.sha256 | 一致？ |
|---|---|---|---|
| `common.lua` | `A1761E1B546EDE23…` | `A1761E1B546EDE23…` | ✓ |
| `cha.lua` | `E4E28A24C0761C14…` | `99EAB1D3588386BD…` | ★★ **不一致！** |
| `dm.lua` | `E3E113EA3F288871…` | `E3E113EA3F288871…` | ✓ |
| `coop.lua` | `A83FD6F9C9F12B21…` | `A83FD6F9C9F12B21…` | ✓ |
| `tlogconfig.info` | `E8FC8D1CF8291CD5…` | `E8FC8D1CF8291CD5…` | ✓ |
| `sku_tags.info` | `D556DEDDDCC74787…` | `D556DEDDDCC74787…` | ✓ |
| `whitelist_tester.info` | `C0BB560479E79FF3…` | `C0BB560479E79FF3…` | ✓ |
| `Platform.json` | （未列） | `739129D144DA21DC…` | — |

### ★★★ `cha.lua` 的哈希不一致 —— 关键发现

```
runtime-manifest:  E4E28A24C0761C14BA1938128990123B832503B74716C2CFAD46FD973BD1CE62  size=1839
MANIFEST.sha256:   99EAB1D3588386BDBA91E60273895E867B8E61FF71762BD1DAF2535A0CD4C96D  size=21493
```

★★★ **⇒ `cha.lua` 从 1,839 字节长到 21,493 字节**（增长 11.7 倍），**哈希变了。**

★ **⇒ runtime-manifest 记录的是**旧版本**，`MANIFEST.sha256` 是**打包时的真实版本**。**

★★★ **⇒ 两个清单**不是同一次生成的**，`runtime-manifest` 更旧。**

★ **旁证**：`runtime-manifest` 的 file 列表**不含 `war.lua`**，
**而 `conf.lua` 注释说 "war.lua had exactly this disease and was fixed the same way"**
⇒ **war.lua 是后来加的，runtime-manifest 未更新。**

---

## 五、★★★★ 声明了但**未交付**的 8 个文件（差集）

| # | 声明路径 | 字节 | `kind` | 在 `source\` 里？ |
|---|---|---|---|---|
| 1 | `1004/Keystreams/configs_s.keystream` | 25,126 | asset | ★ **在**（`source/assets/backend/keystreams/`） |
| 2 | `1004/1100001DEADC0DE/the.json` | 85 | seed | ★ **在**（`source/assets/profile_seed/...`） |
| 3 | `1004/1100001DEADC0DE/Publicprofile` | 2,104 | seed | ★ **在** |
| 4 | `1004/Cloud/iotd-english.jpg.Manifest` | — | asset | ★ **在** |
| 5 | `1004/Cloud/iotd-english.jpg` | — | asset | ★ **在** |
| 6 | `1004/Cloud/iotd-english.png.Manifest` | — | asset | ★ **在** |
| 7 | `1004/Cloud/iotd-english.png` | — | asset | ★ **在** |
| 8 | `Launch_OLMod.bat` | — | — | ★ **在**（`source/distribution/launcher/`） |

★★★ **⇒ 8 个全部**存在于 `source\`，但**没有进 `payload\`**。**

### ★★★ 这与 README §5 "合规边界"**逐字对应**

**README.md:65 逐字**：
> | 玩家存档 `Assets\Alwaysoffline\1004\<UID>\*`、**`Keystreams`**、**`Cloud\iotd-*`**、
>   **`Launch_OLMod.bat`** | 打包时已排除（`payload\` 内 0 个） |

★★★ **⇒ 排除是**有意的**，且在 README 里声明了。**

★ **4 类排除：**
```
① 玩家存档 1004\<UID>\*        （the.json / Publicprofile）
② Keystreams\                  （configs_s.keystream）
③ Cloud\iotd-*                 （4 个文件）
④ Launch_OLMod.bat             （启动器）
```

★★ **排除理由（我的判读）**：
- ①②③ 是**用户数据/许可内容**（存档、密钥流、内容图）
- ④ 是**另一个启动入口**（与本包的 `2-启动.cmd` 冲突，可能打架）

---

## 六、★★★ `payload\` 比声明**多**的部分

```
payload 实际 55 个
runtime-manifest 声明 44 个
    差集：55 − 44 + 8（声明但缺）= 19 个"payload 独有"
```

**payload 独有（未在 runtime-manifest 声明）**：

| 类别 | 数量 | 例 |
|---|---|---|
| **多出的 map lua** | **15** | `mp_arkaden_sh` / `mp_backlot_sh` / …（声明只有 4 个 map） |
| 多出的 gametype lua | 2 | `conf.lua`（7,082）+ `war.lua`（7,018） |
| `Bootstrapper64.dll` | 1 | 204,288（★ 声明里没有 64 位版） |
| `ol-mod-runtime-manifest.json` | 1 | 自己（自指） |
| | **19** | ✓ 完全吻合 |

★★★ **⇒ `runtime-manifest` 是一份**过期的**清单；
**`MANIFEST.sha256` 才是交付时的权威。**

---

## 七、★ `MarketplaceSkus.json`（2,578,582 B）头部结构

```json
{
  "formatVersion": 2,
  "source": {
    "titleId": 1004,
    "tables": {
      "skus":            "mp_comarketplaceskus.csv",
      "products":        "mp_comarketplaceproducts.csv",
      "product_items":   "mp_comarketplaceproductitems.csv",
      "items":           "mp_coMarketplaceItems.csv"
    },
    "skuCount": 12349,
    "productCount": 10056,
    "additionalProductItemCount": 63
  },
  "products": [
    {"productId":1,"grants":[{"itemId":100,"quantity":1,"name":"heg_scarfmask","type":"cat","subtype":"heg"}],"requirement":"uf_prestige_rank","requirementValue":44},
    {"productId":2,"grants":[{"itemId":30058,"quantity":1,"name":"pct_basic6","type":"pct","subtype":""}]},
    ...
  ]
}
```

### ★★★ 要点

1. **`formatVersion: 2`** —— 有版本化的自有格式
2. **`source.tables` 指向 4 个 CSV** —— ★★★ **原始发布文件的名字**：
   ```
   mp_comarketplaceskus.csv
   mp_comarketplaceproducts.csv
   mp_comarketplaceproductitems.csv
   mp_coMarketplaceItems.csv          ← ★ 大小写不一致（"MarketplaceItems" 大写 M/I）
   ```
   ★ **`mp_co*` 前缀 = CODOL（Chinese Online）**
   ★ **第 4 个的名字风格与前三不同** —— **真实发布文件的命名不一致被保留。**
3. **计数**：12,349 SKU / 10,056 产品 / 63 附加产品项
4. **`grants` 结构**：`{itemId, quantity, name, type, subtype}`
   `type` 取值：`cat`（面罩）/ `pct`（名片/图章）/ `pcb`（国旗/背景）
5. **`requirement` / `requirementValue`** —— 解锁条件
   ★ 例：`productId 1` 需要 `uf_prestige_rank >= 44`
6. **紧凑 JSON**（每个产品一行）—— 生成器输出，非人写

★★ **⇒ 这是**s 从 4 个 CSV 预编译出的运行时形态**。**
★ **⇒ 但 `[dw_service_info] marketplace=0` ⇒ 客户端可能不读它。**

---

## 八、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | `ol-mod-runtime-manifest.json` | 28,209 B，44 条声明 |
| 2 | JSON 格式特征 | `:  `（PowerShell `ConvertTo-Json`） |
| 3 | 字段数/条目 | **10** |
| 4 | `kind` 取值 | `gameplay-script` / `asset` / `seed` |
| 5 | `installPolicy` 取值 | `replace` / `if-missing` |
| 6 | `mutable` 取值 | `false`（脚本/资产）/ `true`（种子） |
| 7 | `origin` 来源前缀 | `ol-mod ` / `ayriax3/1/` |
| 8 | ★★★ **`cha.lua` 哈希不一致** | 1,839 → **21,493** 字节 |
| 9 | ★★★ 声明未交付 | **8 个**（README §5 逐条对应） |
| 10 | ★★ payload 独有 | **19 个**（15 map lua + conf + war + Bootstrapper64 + 自指） |
| 11 | `MarketplaceSkus.json` | `formatVersion: 2`，12,349 SKU |
| 12 | 4 个 CSV 表名 | `mp_co*` 前缀 |

---

## 九、结论

### 1. ★★★ "交付包 = ol-mod 运行清单**去掉四类**"（README §5 已声明）

```
去掉：玩家存档 / Keystreams / Cloud\iotd-* / Launch_OLMod.bat
加回：15 个额外 map lua + conf.lua + war.lua + Bootstrapper64.dll
```

### 2. ★★★ `runtime-manifest` 是**过期清单**（`cha.lua` 哈希与大小都不对）

```
runtime-manifest:  cha.lua = 1,839 B
MANIFEST.sha256:   cha.lua = 21,493 B     ← 权威
```

★★ **⇒ 以 `MANIFEST.sha256` 为准；`runtime-manifest` 只作**来源标注**用。**

### 3. ★★★ 8 个"声明但未交付"的文件**全部在 `source\` 里**

★★ **⇒ 若需要（例如 `configs_s.keystream` 用来解某个加密文件），可从 `source\` 取。**

### 4. ★★ 两个清单都是**同一个 PowerShell 脚本**生成的（`:  ` 双空格特征）

---

## 十、下一步

`payload\Ayria\` 还剩 **4 个二进制 + 1 个 DLL**：
```
Injector32.exe          126,464
Bootstrapper32.dll      159,744
Bootstrapper64.dll      204,288      ← ★ 声明里没有，需单独看
ol_room_owner.exe       283,648
Plugins\ ×4             （前一轮已做 PE，可复用）
```

以及包根的 `README.md` / `BUILD.md` / `preflight.ps1` / `deploy.ps1` / `run.cmd` 逐字节。
