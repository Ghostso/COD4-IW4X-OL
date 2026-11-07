# 客户端商城表清单 —— 2026-10-06 重大发现

## 找到的东西

内存 `r_48110000_0105A000.bin @0x3FEC26` 里有 **`mp/marketplace.json`**,
紧随其后是 zlib 数据(`78 DA`)。解出来是一份**清单**:

```json
{
  "coMarketplaceItems.csv":        "29ECAC6583404C3DA026B2BC0852F7B4",
  "coMarketplaceProducts.csv":     "8E28FE82D782B957ACC303DB653DD701",
  "coMarketplaceProductItems.csv": "4546218F39C6DA111EE55939B7C68D1C",
  "coMarketplaceSKUs.csv":         "34D383EAA01D6CF357D13D138E83789C",
  "coMarketplaceDiscounts.csv":    "00FEB0FC06B17347A68A64D475F9DD43",
  "unlockFlags.csv":               "14FE5D77C1E35DC35BF0744754F3DB19",
  "version": 1625160
}
```

值都是 **MD5 校验值**。这几个表才是**客户端真正使用的商城数据**:

| 表 | 作用 |
|---|---|
| `coMarketplaceSKUs.csv` | SKU 定义 |
| `coMarketplaceProducts.csv` | 商品(productID)定义 |
| `coMarketplaceProductItems.csv` | **productID → itemID**(就是 `AS_GetItemIDsFromProduct` 的数据源) |
| `coMarketplaceItems.csv` | 物品(itemID → 名称/图标/类型) |
| `coMarketplaceDiscounts.csv` | 折扣 |
| `unlockFlags.csv` | 解锁标志 |

## 这解释了全部现象

1. **为什么 exe 目录覆盖不全**:
   `marketplace-catalog.json`(37615 条)是从 **exe 反射**提取的,
   而客户端实际用的是这 6 张 **co* 表**。两者不是一份数据。

2. **为什么"武器能买、名片道具不能买"**:
   用户点的那批武器 SKU 恰好也在 exe 目录里, 名片/道具的恰好只在 co* 表里。
   服务端只认 exe 目录 → 不在里面的 SKU 一律 `Unsupported SKU`。

3. **`version = 1625160`**:
   客户端 `80/70`(getSkusPaginated)请求里就带着字符串 **`"1625160"`** ——
   那是它期望的目录版本号。服务端应该按这个版本提供目录。

4. **`mp/comarketplaceitems.csv`**:
   同一个内存区 0x3FED2A 还有这个表名(小写 co), 说明表名在客户端里是
   `coMarketplace*.csv`。

## 下一步(明确)

## 2026-10-06 追加确证: 表不在 IIPS 包里

扫了**全部 974 个 `.ifs`**, 结果:

```
唯一 .csv 名: 0 个
含 comarketplace / marketplace.json / unlockflags 的位置: 0
```

=> 这 6 张表**不在任何 IIPS 包的可搜索内容里**。
FF 包是加密容器, 字符串层面搜不到; 表名/内容只在**客户端解密后的内存**里出现。

所以只能从内存里拿。已在内存里确认到的东西:

- `mp/marketplace.json` 本体 + 它指向的 6 张表名 + 各自 MD5
- 表名出现位置: `r_48110000_0105A000.bin @0x3FED2A`(`mp/comarketplaceitems.csv`)

但**按 MD5 全库反查那 6 张表: 0 命中** —— 说明抓内存转储的时刻,
这些表要么还没加载, 要么已经被释放。

### 因此最可靠的一步

**在客户端刚加载完商城表时立刻 dump 内存**(而不是登录很久之后),
然后用 marketplace.json 里的 MD5 反查定位。具体时机:
- 客户端进入商城/军牌定制界面时
- 或 `MKT_UpdateInventory` / `AS_GetItemIDsFromProduct` 被调用之后

拿到那 6 张表后:
1. `coMarketplaceProductItems.csv` 给出 **productID -> itemID**(权威映射)
2. `coMarketplaceItems.csv` 给出 **itemID -> 类型/名称**(权威 Category 等价物)
3. 据此重建服务端目录, 覆盖所有可购买的 SKU

这 6 张表**不在已抓的内存转储里**(MD5 全库反查 0 命中), 说明:
- 要么它们在客户端**解密后没被 dump 的那部分内存**里
- 要么它们由**服务端**提供(客户端通过 80/70 之类通道拉取)

所以优先做两件事:
1. **抓 8/70 的完整往返**: 客户端请求带 `1625160`, 如果我们能返回正确的
   SKU 页, 客户端就不需要本地表了。这需要先拿到真实 SKU 页的**格式**
   (之前自编格式打挂过服务, 见 lobby_server 注释)。
2. **或在客户端加载完商城表后立刻 dump 内存**, 用 MD5 反查定位这 6 张表
   (现在的转储是登录后很久才抓的, 可能表已被释放)。

## 2026-10-06 决定性否证: 表不在任何 .ifs 压缩流里

### 方法论先自检(重要)

先验证"字符串搜包"是否可靠 —— 拿**确定存在**的串去搜:

```
lf_init_common_marketplace_1_V49.ifs (594 MB):
  main/images                    4215 次   ← 资源路径是明文
  iwi                            4248 次
  pcb_amorphous01                   0 次  ← 资产数据是加密/压缩的
  callsignNameplate                 0 次
  codo.objects                      0 次
```

结论: `.ifs` 是**部分明文(资源路径表) + 部分加密(资产数据)**。
所以"字符串搜不到"**不能**证明表不在包里 —— 之前几轮的"0 命中"
只能说明表名/内容不以明文出现, 不足以否证。

### 所以才做了 MD5 全量扫描(这才是决定性的)

原理: `mp/marketplace.json` 给出 6 张表各自的 **MD5**。
      扫包里**所有合法的 zlib 流**, 解压后算 MD5 与之比对。
      这覆盖了"压缩存放"的情形, 与字符串是否明文无关。

结果:

```
974 个 .ifs 全扫
1,469,394 个 zlib 流候选
命中 0 / 6
```

**=> 这 6 张表不在任何 .ifs 的 zlib 流里。**

配合前面"包内资源路径是明文"的事实, 再加上**项目里已有的既有结论**,
可以确定这些表的宿主机制:

### ★ 与既有结论对齐(项目里 2026-09-29 已逆向到)

`CODOLServer/SESSION_APPEND_20260929_STAGE3_SUCCESS.md` 等多份文档记载:

```
客户端不按文件系统读资产, 而是查【资产注册表 0x239B120】(stride 0x1C)
  +0x00 是类型码 (某些路径要求 == 0xC)
配套表: 0x1E2D338 / 0x239B120 / 0xE5C8C0
```

而且**已经实测过放明文 `mp/marketplace.json` 无效**:
磁盘上那个文件就是我们之前放的探针, 内容写着
`"_result":"NEGATIVE"`, 并注明
"It does not: ... This asset must be registered in the asset table
 at 0x239B120". 且"资源表 0x239B120 里没有 mp/marketplace.json 这条记录"。

=> **这 6 张表的入口是资产注册表, 不是文件系统, 也不是 .ifs 内容。**
   这解释了为什么全盘扫 974 个包、146 万个压缩流都 0 命中。

## 已解出的文件

## 2026-10-06 定位: 0x239B120 落在 .tvm0(壳虚拟化节)

### 先纠正一个方法错误

之前直接拿 `0x239B120` 当**文件偏移**读 Base.dll, 全是乱码 ——
因为它其实是 **RVA**。按 PE 节区表映射后才对。

### Base.dll 节区表(已解析)

```
ImageBase 0x10000000   SizeOfImage 0x3991000   (文件 60327992 字节)
name       VirtAddr   VirtSize     RawPtr
.text      0x001000   0x742000     0x000400
.rdata     0x743000   0x26C000     0x742000
.data      0x9AF000   0x153000     0x9AD200
.idata2    0xB02000   0x004EBA     0xAF7C00
.rsrc2     0xB07000   0x002B9C     0xAFCC00
.tls       0xB0A000   0xED3000     0xAFF800
.tvm0      0x19DD000  0x1F5E000    0x19D1E00
.reloc     0x393B000  0x056000     0x392F400
```

### 关键地址的归属

| RVA | 节 | 内容特征 |
|---|---|---|
| `0x239B120` (资源表) | **.tvm0** | 高熵, 加密/虚拟化 |
| `0x1E2D338` | **.tvm0** | 高熵 |
| `0xE5C8C0` | .tls | 高熵 |
| `0x49D3B0` / `0x4A9330` | .text | **正常 x86 代码** |

```
RVA 0x49D3B0 -> .text off 0x49C7B0: 04 89 44 24 78 8b 44 24 60 ...
RVA 0x4A9330 -> .text off 0x4A8730: 8b 44 24 38 50 e8 c7 44 dd ff ...
RVA 0x239B120 -> .tvm0 off 0x238FF20: 03 bf 4e d9 c6 46 8a 19 ...  (乱码)
```

### 结论

**资源注册表 0x239B120 位于 `.tvm0` —— TP3 壳的虚拟化节。**

- `.tvm0` 虚拟大小 0x1F5E000(32MB), 内容是**运行时才被壳解密**的
- 静态文件里读出来必然是加密数据
- 这解释了为什么:
  - 全盘扫 974 个 .ifs / 146 万个 zlib 流 -> 0 命中
  - 内存转储里 0x239B120 未被覆盖(转储没包含 .tvm0 的运行时映射)

=> 要看这张表, **必须拿到壳解密后的运行时内存**(.tvm0 的运行时映射)。
   静态分析到此为止。

- `mkt_assets/marketplace.json.raw` —— 387 字节, zlib 原文解压结果
- `mkt_assets/marketplace.client.json` —— 上面那份清单的 JSON

## 追加: 客户端商品/物品对象的字段定义(内存 0x4F18078 / 0x44E4C58)

从客户端 ActionScript 元数据里挖到的**权威字段表**:

### 商品对象(SKUObj / productObj)

```
currency     货币
price        价格
purchasable  可购买
productId    商品 ID          ← 对应 AS_GetProductIDFromSKU
stackable    可堆叠
duration     时长
promoSkuId   促销 SKU
SKUObj       SKU 对象
skuId        SKU ID
```

### 物品对象(itemObj)

```
currencyID   货币类型
itemType     物品类型          ← 就是 category 的等价物
itemId       物品 ID           ← 对应 AS_GetItemIDsFromProduct
seasonTime / seasonName / seasonId   赛季
rewardType   奖励类型
```

### 配套函数(同一段元数据里)

```
GetItemInfoBySku     按 SKU 取物品信息
GetItemInfo          取物品信息
isOwned              是否拥有
selectBestSKU        选最优 SKU
SKUs                 SKU 列表
```

**这组字段就是服务端目录条目应该提供的完整信息。**
对比我们的 `marketplace-catalog.json`, 缺的正是
`purchasable` / `promoSkuId` / `itemType` 这几个字段。

## 追加: 发现了第二张商城表 `mp/cononemarketplaceitems.csv`

内存 `r_48110000_0105A000.bin @0x91F047` 处有**另一张表**,
而且**内容已解密可见**(不像那 6 张只有名字):

```
品牌/公司名:
  Levisthan   UI_MARKET_COMPONY_LEVISTHAN_NAME / _DESC
  Tyrant      UI_MARKET_COMPONY_TYRANT_NAME / _DESC
  logo_tools_levisthan
  UI_MARKET_BRAND_LUXURY_NAME

物品 ref(竖线分隔):
  ss_mp|vectordeatheg_mp|g18deatheg_mp
  mp5ktool_mp|ak47tool_mp|rpdtool_mp|scarsaprreskin_mp|pechenegreskin_mp|gpas12reskin_mp
  scarsaprtyrant_mp|veprtyrant_mp|r5rgptyrant_mp|r870ronin_mp|scarronin_mp|mp5sdronin_mp|augronin_mp|honeybadgerronin_mp
```

=> `cono` = **COD Online** 专属商城表。它才是 CODOL 真实在用的那套,
和 `coMarketplace*`(通用/国际版) 并存。

### 另一个关键线索

`mp/comarketplaceitems.csv` 表名**前面**紧邻一串物品 ID:

```
10111  10106  10122  10123  10108  10129  10134  10135  10139  10138
10141  10142  10144  10125  10127  10071  10070  10072  10075  10081  10082
```

这是一段**连续的 ID 列表**(10070..10144), 说明表已按 ID 索引加载,
只是可能换了存放形式(不是明文 CSV)。
