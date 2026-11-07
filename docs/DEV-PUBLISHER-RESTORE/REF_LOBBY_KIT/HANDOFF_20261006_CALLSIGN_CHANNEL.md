# 名片/徽章/称号(Callsign) 通道 —— 2026-10-06 结论

## 一句话(已修正)

名片/徽章/称号是**独立物品类型**(`pcb`/`pci`/`pct`/`bdg`/`cnc` 前缀)，
有**自己的 SKU 编号体系**，通过 marketplace 通道(80/154、93/131)购买。
购买后客户端读 `codo.objects.CallSignObj` 的
`cardXxxItemID` 字段来判断"是否拥有 / 是否装备"。

**关键: 这些表的路径字符串只在内存里, 包文件里搜不到**
(974 个 .ifs 全扫, 0 命中) —— 说明表名是被压缩/加密进 FF 的。

## 硬证据(来自 exe 字符串表)

### 1. CallSignObj 的字段(0x006C8D31 附近)

```
realName | isSpeaking | pilot | codo.objects.CallSignObj | callSignObj
```

紧邻的字段表(0x006A31BC):

```
userId | userName | background | title | icon | namePlate | frame |
clanId | wargodScore | wargodSeason
```

结论: 名片是**玩家档案里的槽位**(background/title/icon/namePlate/frame)，
不是库存条目。

### 2. 客户端接口(0x006B624C 附近)

```
Callsign_HandleTryonItems      Callsign_TryonTitle
Callsign_TryonEmblem           Callsign_TryonBackground
Callsign_TryonNameplate        Callsign_TryonBadge
Callsign_TryonFrame            Callsign_TryonAdvancedConsumable
Callsign_GetActiveCallsignTitle
Callsign_GetActiveCallsignBackground
Callsign_GetActiveCallsignNameplate
Callsign_GetActiveCallsignEmblem
Callsign_GetActiveCallsignBadge
Callsign_GetActiveAdvancedConsumable
Callsign_UnequipItem           Callsign_UnequipAdvancedConsumable
```

### 3. 客户端要读的表(0x006BDE33 / 0x006C8A0B)

```
mp/callsignTitle.csv
mp/callsignBackground.csv
mp/callsignIcon.csv
mp/callsignFrame.csv
mp/callsignNameplate.csv
mp/item_cnc.csv
mp/badgeTable.csv
mp/rankIconTable.csv
mp/spyKarmaTable.csv
```

**这些表我们没有提供。** 客户端读不到 -> 名片的"可选/已拥有"列表就是空的，
所以军牌定制里看不到刚买的东西。

### 4. isOnlyTryon(0x006CA370)

```
baseID | key | parentName | killsReq | unlockRank | isOnlyTryon |
exclusiveList | itemDat | primaryValKeyArray
```

`isOnlyTryon` = "只能试戴、不能真正拥有"。军牌定制里那些点不了的，
很可能就带这个标记。

## 实测记录(2026-10-06 两轮)

购买**在服务端是成功的**:

| 时间 | SKU | item | 货币 | 结果 |
|---|---|---|---|---|
| 14:06:22 | 37251 | 29892 | CP 8000 | 服务端成功 |
| 14:06:31 | 31181 | 22381 | GP 680 | 服务端成功 |
| 14:06:33 | 31184 | 22384 | GP 680 | 服务端成功 |

库存里也确认写入了(`marketplace-inventory.json` 里 22381/22384/29892 都是 1)，
而且 `inventory_results` 已把它们排在应答最前面(绕过 480KB 截断)。

**但客户端军牌定制里仍然看不到、买不到。**

## 已排除的原因

1. ~~货币不对~~ —— 已按真实购买帧设置(93->GP, 80->CP)。
2. ~~SKU 不在目录~~ —— 31181/31184/37251/39593 都已补入(共 101 条新增)。
3. ~~库存被 480KB 截断~~ —— 已加 Priority 置顶, 确认应答前 4 件就是它们。
4. ~~购买应答格式错~~ —— 服务端按 v32 参考实现返回余额对象, 与武器购买一致。

## 2026-10-06 最小仓库实验(决定性)

把仓库从 17372 件缩到 **4 件**(只留买过的), 彻底排除 480KB 截断干扰:

| 时间 | SKU | item | 货币 | 服务端 | 库存 | 203 应答 | 客户端 |
|---|---|---|---|---|---|---|---|
| 14:28:25 | 18079 | 15166 | GP 2580 | 成功 | 有 | 发出 | **不认** |

203 应答只发 5 件(386 字节, 远低于 480KB 上限), 5 件全部发出, 无截断。

**结论: 截断不是原因。** 购买链路(请求解析 -> 扣款 -> 入库 -> 应答)全部正确,
客户端就是**不认**。

## 根因(已定位)

客户端要判断"这个 itemID 对应军牌定制里的哪个格子", 必须查
`mp/callsignBackground.csv` 等表里的 `ref <-> itemID` 映射。
这些表我们没提供, 所以客户端拿到 itemID 15166 也无法显示。

### 已抽出的表数据(但缺 ID 映射)

从内存 `r_48110000_0105A000.bin` 抽出 **4784 条 callsign 物品 ref**:

| 前缀 | 条数 | 对应表 |
|---|---|---|
| pcb | 2406 | mp/callsignBackground.csv |
| pci | 895 | mp/callsignIcon.csv |
| pct | 805 | mp/callsignTitle.csv |
| pcai | 253 | 动态图标 |
| pcab | 250 | 动态背景 |
| pcaf | 65 | 动态边框 |
| pcf | 46 | mp/callsignFrame.csv |
| pcn | 33 | 名称 |
| cnc | 30 | mp/item_cnc.csv |
| bdg | 1 | mp/badgeTable.csv |

每条的结构(已验证):

```
pcb_amorphous01                      物品 ref
PLAYERCARDS_PCB_AMORPHOUS01_NAME     显示名
PLAYERCARDS_PCB_AMORPHOUS01_DESC     描述
PCB_AMORPHOUS01_ITEM_ICON            图标资源
SCALEFORM_ASH/ITEMICONS/PCB_..._ICON
```

输出在 `mkt_assets/callsign_<prefix>.csv`。

**但 ref 后面跟的不是 itemID**(实测 +4/+8/+12 处都是图标尺寸之类的常量),
说明 `ref -> itemID` 的映射在**另一张表**里, 目前还没找到。

## 下一步(明确)

### ★★ 决定性对照: C# 参考实现也没成功

`REF_LOBBY_KIT/_ref/lsg.log`(2026-10-02) 里有两笔"成功"购买:

```
22:31:32 RAW_PURCHASE_COMMITTED sku=22858 currency=2   -> item 10080 (Cat0)
22:31:32 RAW_LOCAL_PURCHASE_RESULT status=0
22:31:33 RAW_INVENTORY_REPLY items=8
22:31:37 RAW_PURCHASE_COMMITTED sku=22865 currency=1   -> item 26552 (Cat1 外观类)
22:31:37 RAW_LOCAL_PURCHASE_RESULT status=0
22:31:37 RAW_INVENTORY_REPLY items=9
```

但对照它的落盘文件 `CODOLServer/lobby_server/data/`:

```
marketplace-inventory.json  Items = 7 件(10007 26666 27724 27725 27720 11016 11722)
player-account.json         CodPoints=985699  Gold=883599
```

**买的那两件(item 10080 / 26552)都不在库存里, 余额也没扣。**

=> `items=8 -> 9` 是 203 应答里的**件数**, 不是真实入库。
   C# 参考实现在"买名片"这件事上**同样没成功**。

这排除了"我们的实现写错了"这一可能 —— 三方参考实现走的是同一条死路。

### ★★ 2026-10-06 最新突破: `8/3` 是玩家档案上传

抓到的 payload(`lobby_tasks.bin`, service=8 task=3, 1958/1961 字节):

```
08 04 00 00 00       tag08 u32 = 4      (档案版本/类型?)
08 01 00 00 00       tag08 u32 = 1
08 01 00 00 00       tag08 u32 = 1
08 25 25 19 37       tag08 u32 = 0x37192525   (CRC)
13 08 1a 05 00 00    tag13 blob, len=0x51a=1306
   78 01 ed 9a ...   ← zlib 压缩的档案数据!
```

`78 01` 是 **zlib 头**(默认压缩级别)。解压后就是玩家档案,
里面包含 `CallSignObj` 的 `cardXxxItemID` 槽位。

**我们一直回空 ACK, 所以客户端上传的档案被丢弃了。**
这解释了为什么买了名片不生效: 装备状态存在档案里, 而档案上传被我们忽略了。

同一会话里新出现的其它通道(也是空 ACK):

| service/task | payload | 猜测 |
|---|---|---|
| 8/3 | 1958B(zlib 档案) | ★ 玩家档案上传 |
| 102/2 | 1B `00` | ? |
| 102/5 | 10B | ? |
| 177/29 | 679609568(乱码) | 密钥未对上 |
| 71/20 | ? | ? |

### 下一步优先级(已更新)

0. **★★ 处理 `8/3`(玩家档案上传)**: 解 zlib, 看里面的 `cardXxxItemID`,
   然后把档案存下来并在 `8/1`(public.result) / `8/2`(secure.result) 时回给客户端。
   这是打通"名片装备"的最短路径。

1. **找到 `ref -> itemID` 映射表**。已知:
   - `sku=18079 -> item=15166`(实测, GP 2580)
   - `sku=31181 -> item=22381`, `sku=31184 -> item=22384`
   - 待查: 这些 itemID 对应的 ref 是什么?
   建议做法: 在内存里搜 `15166`/`22381` 附近, 看有没有 `pcb_`/`pci_` 串
   (已试 ±0x1000, 0 命中 -> 映射可能是**索引式**的, 不是字符串式)。
2. **补 Callsign 文本表**。客户端要 `mp/callsignTitle.csv`、
   `callsignBackground.csv`、`callsignIcon.csv`、`callsignFrame.csv`、
   `callsignNameplate.csv`、`item_cnc.csv`、`badgeTable.csv`。
   这些表不在文件系统里(已确认), 打包在 IIPS/FF 里。
   - 优先: 从 `common_marketplace` 明文 nifs 包里找(已抽出 124929 条资源路径,
     但表类文件 0 个 —— 说明表在**另一类**包里, 不是 marketplace 包)。
   - 次选: 运行时从内存里捞(客户端解密这些表后会在内存里留明文,
     `mem_callsign/callsign_0x71B40000.bin` 已经抓到 499712 字节的称号表)。
3. **确认档案里的槽位字段**。`Callsign_GetActiveCallsign*` 系列读的是玩家档案,
   要弄清档案里 namePlate/background/title/icon/frame 存在哪个偏移。
4. **验证 isOnlyTryon**。如果目标物品带这个标记, 买了也只能试戴。

## 关键结构(CallSignObj, 来自内存 ActionScript 元数据)

```
codo.objects::CallSignObj/cardTitleItemID        int   @pos 157
codo.objects::CallSignObj/cardIconItemID         int   @pos 200
codo.objects::CallSignObj/cardBackgroundItemID   int   @pos 243
codo.objects::CallSignObj/cardNameplateItemID    int   @pos 286
codo.objects::CallSignObj/cardTitle              String@pos 330
codo.objects::CallSignObj/cardTitleURL           @pos 366
codo.objects::CallSignObj/cardIconURL            @pos 405
codo.objects::CallSignObj/cardBackgroundURL      @pos 443
codo.objects::CallSignObj/cardBackgroundName     @pos 493
codo.objects::CallSignObj/cardNameplateColor     uint  @pos 538
codo.objects::CallSignObj/cardFrameURL           @pos 587
codo.objects::CallSignObj/cardTitleTryon         Boolean @pos 627
codo.objects::CallSignObj/cardIconTryon          Boolean @pos 672
codo.objects::CallSignObj/cardBackgroundTryon    Boolean @pos 716
```

这印证了: **拥有/装备状态存在 CallSignObj 的 `cardXxxItemID` 字段里**,
客户端用 itemID 反查表来显示名称和图标。

## 项目内相关文件(本次新增)

## ★★ 完整的"拥有判定"接口链(2026-10-06 定位)

## ★★★ 2026-10-06 最终定位: 库存截断导致一切购买"无效"

### 现象

用户实测: **不只是名片 —— 加成卡、消耗品、高级消耗品、黑市币, 全都买不成。**

### 根因(一条链)

1. `marketplace-inventory.json` 里有 **17372 件**(全量赠送的 17371 + 后加的 1)。
2. 客户端请求 `80/203` 要 **20000 件**(payload = `10 00 06 20 4e 00`, u16=20000)。
3. 但单次 0x85 应答有**体积上限**: 全量 1052KB 会 `ConnectionReset`;
   480KB(约 7741 件)是实测安全上限。
4. 于是客户端**只收到按 item ID 升序的前 7741 件**(最大 item ≈ 17925)。
5. 被截掉的 9631 件里, 包含:
   - 名片类: 8915 件(含 15166/22381/22384)
   - 用户实际点的: 60087/60088/60138/17928/16339 ...
6. 客户端 `IsMarketplaceItemOwned` 查不到这些 item -> 认为**没拥有**。
7. 服务端 `purchase()` 又因为"已拥有(owned != 0)"而**不重复添加、不扣款**,
   只回一个余额对象 -> 日志显示"购买成功", 客户端却毫无变化。

**这就是"买什么都是买成功但没反应"的完整解释。**

### 决定性证据

```
本轮买的 8 笔, item 全部**本来就在库存里**:
  610->60087  611->60088  21718->60138  32327->17928
  19428->16339  31184->22384  37251->29892  18079->15166
全部 "已拥有, 不重复加"。

但 203 应答只发 7741 件, 这些 item 的 ID 都 > 17925(截断线), 发不出去。
```

### 两个可选解法

**A. 缩减仓库到 480KB 以内(最直接)**
   用户早就说过"仓库不需要太多数据"。把 17371 件砍到 ~7700 件以内,
   且**优先保留名片/消耗品/加成卡这类用户会买的**, 就能全部发出去。

**B. 分页(协议支持吗?)**
   `80/203` 的请求 payload 恒为 `u16(20000)`, **没有游标参数**。
   所以客户端不支持翻页 —— 只能一次给全。**B 路不通。**

=> 只能走 A: 把库存控制在安全体积内。

从内存 `r_259D0000_06400000.bin` 挖出的 ActionScript 函数表:

```
SKU -> 商品
  AS_GetProductIDFromSKU        SKU -> productID
  AS_GetDurationFromSKU         SKU -> 时长
  AS_GetItemIDsFromProduct      productID -> itemID 列表   ← 权威映射!

拥有判定
  IsPermanentOwnedProduct       是否永久拥有(product 级)
  IsMarketplaceItemOwned        是否已拥有(item 级)
  AS_IsDependencyOwnedForItem   依赖是否满足
  AS_IsDependencyOwnedForBundle
  AS_IsExpiredInventoryItem     是否过期
  IsItemConsumable              是否消耗品

装备
  AS_IsItemEquipped             是否已装备
  AS_GetExclusiveEquippedItem   互斥装备项

★ 库存 -> UI 的关键函数
  WL_FillInInventoryProductItems   "把库存物品填进商品条目"
  MKT_UpdateInventory              更新库存
  MKT_RequestAccountInfo           请求账户信息
  MKT_InvalidatePreviewList        让预览列表失效(刷新)
  GetMktUpdateState                商城更新状态
  IsMarketplaceReady / IsPlayerdataReady / IsWeaponDataReady

UI 字段(商品条目对象)
  isOwned | isEquipped | canAfford | unlockItem | isNewUnlock
  ACTION_BUY | ACTION_NONE | SKU_ON_SALE | PRODUCT_HOT | PRODUCT_NEW
  isGP | EHPSKUIndex | HPSKUIndex | GPSKUIndex
```

### 这条链说明了什么

1. **映射本来就是对的**: 客户端用 `AS_GetItemIDsFromProduct` 从 SKU 算 itemID,
   实测 `sku=18079 -> item=15166` 与我们的目录一致。
2. **拥有判定走 marketplace inventory**: `IsMarketplaceItemOwned` 查的就是
   203 应答里那批 item。我们已经把 15166/22381/22384 都发出去了。
3. **UI 靠 `WL_FillInInventoryProductItems` 填充**: 它把库存 item 填进
   商品条目, 然后 `isOwned` 才为真。

### 因此下一步只剩一个明确动作

在 `WL_FillInInventoryProductItems` 下断点, 看:
- 它被调用时, 传入的"库存集合"里有没有 15166/22381/22384
- 如果没有 -> 客户端没把 203 应答解析成库存(格式或时机问题)
- 如果有 -> 问题在后面的 UI 刷新(`MKT_InvalidatePreviewList` 没被触发)

这是唯一能把问题缩到"解析"还是"刷新"的一步。

- `_dig_callsignobj.py` —— 挖出 CallSignObj / Callsign_* / 表路径
- `_find_callsign_tables.py` —— 确认表不在文件系统
- `_scan_callsign_assets.py` —— Callsign 资源只有图片/模型, 无表
- `_find_more_skus.py` —— 找出"点过但目录没有"的 SKU
- `_harvest_neighbor_skus.py` —— 从内存补连号 SKU(如 39593)
- `_seed_priority.py` —— 把买过的物品置顶到库存应答
- `_make_min_inventory.py` —— 最小库存实验(未使用)
- `mem_callsign/callsign_0x71B40000.bin` —— 已抓到的称号表(499712 字节)
