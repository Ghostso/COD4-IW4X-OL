# 逆向总结 —— 2026-10-06 商城/购买问题

## 一句话结论

**服务端购买链路完全正常, 问题是服务端的 SKU 目录覆盖不全。**
客户端真正使用的是 6 张 `coMarketplace*.csv` 表(CODOL 还叠加了
`conoMarketplace*.csv`), 而我们从 exe 反射出的目录只是其中一小部分。

## 已用实测证明的结论

### 1. 购买链路正常(有库存增长为证)

```
15:37:37  购买成功 sku=22251  -> 库存 7600 -> 7601
15:37:41  购买成功 sku=31847  -> 库存 7601 -> 7602
15:39:02  购买成功 sku=31726  -> 库存 7602 -> 7603
```

### 2. 能不能买 = SKU 在不在服务端目录里

| SKU | 在 exe 目录 | Category | 结果 |
|---|---|---|---|
| 22251 / 22255 / 31726 / 31847 | **是** | 3(武器) | 成功 |
| 37116 / 37251 / 16096 / 19428 / 31184 | 否 | — | **Unsupported SKU** |

用户观察到的"武器能买、名片/道具不能买", 实际是**目录覆盖差异**,
不是类别限制。

### 3. 客户端商城表的真面目

内存 `mp/marketplace.json`(zlib)解出后是一份清单, 指向 6 张表:

```
coMarketplaceItems.csv
coMarketplaceProducts.csv         商品(productId)
coMarketplaceProductItems.csv     ★ productId -> itemId
coMarketplaceSKUs.csv             SKU 定义
coMarketplaceDiscounts.csv
unlockFlags.csv
version = 1625160
```

每张带 MD5。另有 CODOL 专属的 `conoMarketplaceitems.csv`
(内存里**内容已明文**, 含 Levisthan/Tyrant/Aurora 等品牌与武器 ref)。

### 4. 客户端对象字段(权威)

```
商品: currency | price | purchasable | productId | stackable |
      duration | promoSkuId | SKUObj | skuId
物品: currencyID | itemType | itemId | seasonTime | seasonName |
      seasonId | rewardType
函数: GetItemInfoBySku | GetItemInfo | isOwned | selectBestSKU | SKUs
```

### 5. 表不在任何 IIPS 包里(已穷尽验证)

```
974 个 .ifs 全扫:
  .csv 表名              0 命中
  coMarketplace*         0 命中
  表内容串(如品牌名)      0 命中
```

FF 包是加密容器, 表只在**客户端解密后的内存**里存在。

## 卡点

现有内存转储(10/5 21:52, 延迟 150s)里, 按 MD5 反查那 6 张表
**0 命中** —— 抓取时**没打开过商城界面**, 表尚未解密。 

## 下一步(唯一可行)

**在打开商城/军牌定制界面后抓内存**, 用清单里的 MD5 定位那 6 张表。

做法二选一:
- A. 把 `memlinear_after.txt` 延迟改小(如 20s), 进大厅后立刻开商城界面
- B. 改 `nt10.py` 加周期扫描: 每 15s 按 MD5 扫内存, 命中即 dump

拿到表后:
1. `coMarketplaceProductItems.csv` -> productId→itemId(权威映射)
2. `coMarketplaceItems.csv` -> itemId→类型(权威 Category)
3. 重建服务端目录 -> 所有可购买 SKU 都可买

## 本轮已修复/确认的其他项

- `8/3` 玩家档案上传: 已按 C# `SavePublicProfile` 逐字节实现并验证
  (CRC 通过, 重建的 public_result 33428 字节与原文件完全一致)
- 购买应答: 改为与 C# 参考实现一致的"空对象 + status"
- 库存体积: 7600 件(460KB), 无截断
