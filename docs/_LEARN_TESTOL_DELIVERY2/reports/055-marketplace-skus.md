# 学习报告 055（重开）— `MarketplaceSkus.json` 结构（2,578,582 字节）

**学习范围**：`payload\Ayria\Assets\Alwaysoffline\1004\MarketplaceSkus.json`
**方法**：读头部 512 字节 + 全文正则计数
**性质**：全实测
**★★★ 本报告给出**商城数据的完整结构**与**四个源 CSV 的名字**

---

## 一、★★★★★ 文件头（前 512 字节，逐字）

```json
{
  "formatVersion": 2,
  "source": {"titleId":1004,"tables":{"skus":"mp_comarketplaceskus.csv","products":"mp_comarketplaceproducts.csv","product_items":"mp_comarketplaceproductitems.csv","items":"mp_coMarketplaceItems.csv"},"skuCount":12349,"productCount":10056,"additionalProductItemCount":63},
  "products": [
    {"productId":1,"grants":[{"itemId":100,"quantity":1,"name":"heg_scarfmask","type":"cat","subtype":"heg"}],"requirement":"uf_prestige_rank","requirementValue":44},
    {"productId":2,"grants":[{
```

### ★★★★★ 完整的头部结构

```
formatVersion : 2
source:
  titleId    : 1004
  tables:
    skus          : "mp_comarketplaceskus.csv"
    products      : "mp_comarketplaceproducts.csv"
    product_items : "mp_comarketplaceproductitems.csv"
    items         : "mp_coMarketplaceItems.csv"
  skuCount                   : 12349
  productCount               : 10056
  additionalProductItemCount : 63
products: [ ... ]
```

★★★ **⇒ 四个源 CSV 的精确名字：**
```
mp_comarketplaceskus.csv
mp_comarketplaceproducts.csv
mp_comarketplaceproductitems.csv
mp_coMarketplaceItems.csv          ← ★★★ 大小写不一致（MarketplaceItems 大写 M/I）
```

★★★ **⇒ 第 4 个的命名风格与前三不同 ⇒ **真实发布文件的命名不一致被保留**。**

★ **⇒ `mp_co*` 前缀 = **CODOL（Chinese Online）**。**

---

## 二、★★★★★ 三个精确计数

| 项 | 值 |
|---|---|
| `skuCount` | **12,349** |
| `productCount` | **10,056** |
| `additionalProductItemCount` | **63** |

★★ **⇒ 10,056 个产品 + 63 个附加产品项 = **10,119**。**

★★★ **⇒ 而全文扫描的 `"itemId"` 计数正好是 **10,119** ✓ 完全吻合。**

---

## 三、★★★★★ 全文结构统计（逐项实测）

| 键 | 出现次数 | 说明 |
|---|---|---|
| `"productId"` | **22,405** | ★★ **是 `productCount` 的 2.2 倍** |
| `"grants"` | **10,056** | ✓ 与 `productCount` 一致 |
| `"itemId"` | **10,119** | ✓ = 10,056 + 63 |
| `"quantity"` | **10,119** | ✓ 同 `itemId` |
| `"name"` | **10,150** | ★ 比 `itemId` 多 **31** |
| `"type"` | **10,119** | ✓ |
| `"subtype"` | **10,119** | ✓ |
| `"requirement"` | **3,188** | ★ 只有 **31.7%** 的产品有条件 |
| `"requirementValue"` | **3,185** | ★ 比 `requirement` 少 **3** |
| **`"skuId"`** | **0** | ★★★ **不存在！** |
| **`"price"`** | **0** | ★★★ **不存在！** |

### ★★★★★ 三个关键发现

**① `"productId"` 出现 22,405 次，是 `productCount` 的 2.2 倍**

★★★ **⇒ 说明 `productId` 出现在**两个地方**：**
```
① products[] 数组里（10,056 次）
② ★ 某个映射表里（约 12,349 次 —— 正好等于 skuCount！）
```

★★ **⇒ `10,056 + 12,349 = 22,405` ✓ **完全吻合**。**

★★★ **⇒ 所以文件里**还有一个 `skus` 映射**（每个 sku 指向一个 productId）。**

**② `"skuId"` 和 `"price"` 出现 0 次**

★★★ **⇒ 这个文件**完全没有价格和 SKU ID 字段**。**

★ **⇒ 说明：**
```
价格不在这个文件里（可能在 mp_comarketplaceskus.csv 里，未导出）
skuId 也不是这个文件的字段
```

★★ **⇒ 所以 `skus` 映射用的是**别的键名**（可能是 `productId` 作 key）。**

**③ `"name"` 出现 10,150 次（比 `itemId` 多 31）**

★★ **⇒ 有 **31 个额外的 `name`**（可能来自 `source.tables` 或某个元数据块）。**

**④ `requirement` 3,188 vs `requirementValue` 3,185（差 3）**

★★ **⇒ 有 **3 个产品有 `requirement` 但没有 `requirementValue`**。**

---

## 四、★★★★ 产品的完整字段结构（实测样例）

### 4.1 ★★★ 带条件的产品（`productId: 1`）

```json
{
  "productId": 1,
  "grants": [
    {"itemId": 100, "quantity": 1, "name": "heg_scarfmask", "type": "cat", "subtype": "heg"}
  ],
  "requirement": "uf_prestige_rank",
  "requirementValue": 44
}
```

★★★ **⇒ 六个字段：**
```
productId        : 1
grants[]         : [{ itemId, quantity, name, type, subtype }]
requirement      : "uf_prestige_rank"     ← ★ 解锁条件
requirementValue : 44                     ← ★ 条件值
```

★ **⇒ `requirement: "uf_prestige_rank"` + `value: 44` = **需要威望等级 44**。**

### 4.2 ★★★ 无条件的（`productId: 2`）

```json
{"productId":2,"grants":[{"itemId":30058,"quantity":1,"name":"pct_basic6","type":"pct","subtype":""}]}
```

★ **⇒ 没有 `requirement` / `requirementValue` ⇒ **无条件解锁**。**

### 4.3 ★★★★★ `type` 的取值（实测三种）

| `type` | 例子 | 含义（推测） |
|---|---|---|
| **`cat`** | `heg_scarfmask` | **面罩 / 头饰**（category?） |
| **`pct`** | `pct_basic6` | **名片 / 图章**（player card?） |
| **`pcb`** | `pcb_landscape06` / `pcb_chinese01` / `pcb_cartoon07` | **背景 / 国旗**（player card background?） |

★★ **⇒ `pcb_*` 的命名很直观：**
```
pcb_landscape01..06    ← 风景
pcb_chinese01..06      ← 中国风
pcb_cartoon03..07      ← 卡通
```

### 4.4 ★★ `subtype` 的取值

```
"heg"    （cat 的子类）
""       （空 —— pct/pcb 无子类）
```

---

## 五、★★★ 文件规模分析

```
总字符数 : 2,578,582
文件字节 : 2,578,582  （★ 字符数 == 字节数 ⇒ 纯 ASCII）
```

★★★ **⇒ 字符数 == 字节数 ⇒ **文件是纯 ASCII**（无中文、无多字节字符）。**

★★ **⇒ 而 `[dw_service_info] marketplace=0`（报告 003）⇒ **商城服务关闭**，**
**但这个 2.5 MB 文件仍在包里。**

★ **⇒ 可能原因：加载器需要文件存在（即使不读）。**

### ★★★ 平均每个产品

```
2,578,582 字节 / 10,056 产品 ≈ 256 字节/产品
        ↓
★ 紧凑 JSON（每个产品一行）
```

---

## 六、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | `formatVersion` | **2** |
| 2 | `source.titleId` | **1004** |
| 3 | ★★★ 四个源 CSV | `mp_comarketplaceskus.csv` / `mp_comarketplaceproducts.csv` / `mp_comarketplaceproductitems.csv` / **`mp_coMarketplaceItems.csv`** |
| 4 | ★ `skuCount` | **12,349** |
| 5 | `productCount` | **10,056** |
| 6 | `additionalProductItemCount` | **63** |
| 7 | ★★★ **`"productId"` 22,405** | = 10,056（products）+ **12,349（skus）** |
| 8 | `"grants"` 10,056 | ✓ = productCount |
| 9 | `"itemId"` / `"quantity"` / `"type"` / `"subtype"` | **10,119**（= 10,056 + 63） |
| 10 | `"name"` | **10,150**（多 31） |
| 11 | ★★ `"requirement"` | **3,188**（**31.7%**） |
| 12 | `"requirementValue"` | **3,185**（少 3） |
| 13 | ★★★ **`"skuId"`** | **0 次（不存在）** |
| 14 | ★★★ **`"price"`** | **0 次（不存在）** |
| 15 | ★★ 产品六字段 | `productId` / `grants[]` / `requirement` / `requirementValue` |
| 16 | `grants[]` 五字段 | `itemId` / `quantity` / `name` / `type` / `subtype` |
| 17 | ★★★ `type` 三值 | **`cat`** / **`pct`** / **`pcb`** |
| 18 | ★ 命名样例 | `pcb_landscape01..06` / `pcb_chinese01..06` / `pcb_cartoon03..07` |
| 19 | ★★ 文件编码 | **纯 ASCII**（字符数 == 字节数） |
| 20 | ★ 平均大小 | **≈ 256 字节/产品** |

---

## 七、结论

### 1. ★★★★★ **`"productId"` 的 22,405 = 10,056 + 12,349**

★ **⇒ 文件里**还有一个 `skus` 映射**（每个 sku → 一个 productId）。**

### 2. ★★★ **`skuId` 和 `price` 完全不存在**

★ **⇒ 价格和 SKU ID 不在这个导出文件里。**

### 3. ★★★ **`type` 只有三个值**：`cat` / `pct` / `pcb`

### 4. ★★ **31.7% 的产品有解锁条件**（`requirement`）

### 5. ★★ **文件是纯 ASCII**（2,578,582 字符 == 字节）

### 6. ★ **`[dw_service_info] marketplace=0` ⇒ 商城关闭，但文件仍在**

---

## 八、下一步

- `source\` 结构与关键文档（最后一大块）
- `payload\` 剩余：`configs_s.info` 未读节的内容
- `bundle\` 的 `re-auth.out.log`（0 字节）
