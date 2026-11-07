# 合并目录突破 —— 2026-10-06 晚间接手记录

> 承接 `HANDOFF_20261006_MAIN.md`。本轮把"6 张 coMarketplace 表"路线
> **彻底走完并否证**，改用内存采集目录做保守合并，已在服务端验证可购买。

## 0. 一句话

**能不能买 = SKU 在不在服务端目录里**。本轮把内存采集到、且可信的
178 条目录条目并进服务端目录后，用户之前点失败的
`37116 / 37251 / 16096 / 31184 / 31774` 全部有了权威映射，
服务端购买链路验证通过。客户端实机点购仍待一次现场确认。

## 1. `.tvm0` 路线：已走完，结论是否定的

上一轮把"资源注册表在 Base.dll 的 `.tvm0`，必须 dump 运行时映像"列为
唯一出路。本轮把这条路线跑通后否证了它。

### 1.1 先修掉两个工具 bug

1. **模块选错**：`.tvm0` 不是 Base.dll 独有。TGuard / TenProtect 有 90+ 个
   模块带同名节。第一版按"第一个有 `.tvm0` 的模块"匹配，dump 到的是
   `TGuard\TerSafe.dll`（rva 0x310000 / vs 0x4C2000）。
   改成按 Base.dll 的**唯一签名**匹配：`va=0x19DD000 / vs=0x1F5E000`
   （见 `_scan_market_tables_live.py` 的 `TVM_VA_SIG/TVM_VS_SIG`
   与 `_parse_sections/find_tvm_section`）。
2. **扫描覆盖**：预算用尽后每轮都从地址 0 重扫，高地址区（含 Base.dll
   映像）永远扫不到。改成返回断点地址跨轮续扫（`scan_live_once` 的
   `start_addr` 返回值）。

另外 dump `.tvm0` 改为**按页读取**（TP3 只提交被访问过的页，整块 4MB
读会因个别不可读页整块失败），并在 t=20/90/180/300s 取多份快照。

### 1.2 抓到的结果

```
Base.dll  base = 0x5DE50000   SizeOfImage = 0x3991000
.tvm0     rva  = 0x19DD000  vsize = 0x1F5E000 (32,890,880 B)
dump      t020/t090/t180 三份, 每份 32,890,880 字节(整节 100% 可读)
```

### 1.3 否证

| 检验 | 结果 |
|---|---|
| 运行时映像 vs 磁盘节内容 | **99.94% 完全相同**（仅 21,156 字节不同） |
| 差异形态 | 6,988 个簇，绝大多数是 2 字节；符合 PE 重定位/壳补丁，不是解密出的数据 |
| t020 vs t090 vs t180 | 100% 相同（没有"后来被解密"的页） |
| 明文锚点 (`coMarketplace*`, `marketplace.json`, `productId`, `IWffs100`) | 0 命中 |
| 分块熵 | avg 6.66（不是密文期望的 ~8.0），像虚拟化字节码而非数据表 |

**结论：`.tvm0` 是壳的虚拟化节，不是明文数据段。** 资源注册表
`0x239B120` 不能靠"dump 这一段映像"拿到。

## 2. 6 张表 MD5 路线：全内存覆盖后 0/6

用 `_scan_market_tables_live.py` 在游戏**早期句柄**下扫全部可读区
（PRIVATE + IMAGE + MAPPED），对每条 zlib 流同时校验：

* 解压后字节的 MD5
* 原始压缩流的 MD5

```
第 1 轮: 从 0x00000000 扫 1969 个区, zlib 候选 81323, 命中 0/6
第 2 轮: 从 0x56F8B000 扫 1411 个区, zlib 候选 45557, 命中 0/6
合计约 3380 个区 / 126,880 条 zlib 候选 -> 0/6
```

加上上一轮对 974 个 `.ifs` / 146 万条 zlib 流的扫描也是 0/6，
可以下结论：**客户端把 CSV 解析进结构体后就丢弃了原始字节**，
不存在可以按 MD5 命中的完整原始表。

> 这条路线到此为止。不要再重复"抓内存按 MD5 找表"。

## 3. 实际突破：内存采集目录的保守合并

### 3.1 关键发现

`marketplace-catalog-full.json`（38,424 条，内存采集版）里包含
用户实测点失败的 SKU，且字段完整：

| SKU | Item | Currency | Price | exe 目录 | 交叉验证 |
|---|---|---|---|---|---|
| 37116 | 29767 | 1 (CP) | 10000 | 否 | ✅ exe 里 49479/49480 也是 Item 29767 |
| 37251 | 29892 | 1 (CP) | 8000 | 否 | 新 item |
| 16096 | 7110  | 2 (GP) | 880   | 否 | 新 item |
| 31184 | 22384 | 2 (GP) | 680   | 否 | ✅ exe 里 31759/37990 也是 Item 22384 |
| 31774 | 122   | 1 (CP) | 2280  | 否 | ⚠️ 无交叉验证 |

### 3.2 噪声过滤

full 比 exe 目录多 809 条，其中 546 条 `Item<100`（Item=2/4/8、
Price=9999999、SelectedDays 异常）是内存布局误命中。

`_build_merged_catalog.py` 的策略：

```
并入: full 比 exe 多出来、且 Item >= 1000 的条目 (177 条)
      + 显式白名单 31774 (用户点过, 无法交叉验证)
丢弃: 其余 631 条低 Item 噪声
结果: marketplace-catalog-merged.json = 37,793 条
```

### 3.3 服务端验证（真实账户/库存的临时副本）

`_verify_merged_purchase.py` 结果：

```
before: CodPoints=973799 Gold=603479 Items=7609
37116 Item=29767 cur=1 10000 -> OK 扣 10000 CP, 入库
37251 Item=29892 cur=1  8000 -> rc=0, 但 Item 29892 已拥有 -> 不重复扣款
16096 Item=7110  cur=2   880 -> OK 扣 880 GP, 入库
31184 Item=22384 cur=2   680 -> rc=0, 但 Item 22384 已拥有 -> 不重复扣款
31774 Item=122   cur=1  2280 -> OK 扣 2280 CP, 入库
```

真实仓库确认：Item 29892 = 1、Item 22384 = 1（已拥有）；
29767 / 7110 / 122 未拥有，可购买。

> 含义：用户之前点 37251/31184 "没反应"，不是买不了——是**已经拥有**；
> 以前服务端目录里没有这些 SKU，所以连"已拥有"都判不出来，直接
> `Unsupported SKU`。现在能正确判定了。

## 4. 开关与回滚

* 新增开关 `marketplace-catalog-merged.on`（优先级最高）
  -> `marketplace_store.catalog_path()` 返回 `marketplace-catalog-merged.json`。
* 原有 `marketplace-catalog-client.on` 保留不动；merged 优先于它。
* **回滚**：删除 `marketplace-catalog-merged.on` 即恢复原行为。
* 重建目录：`python _build_merged_catalog.py`

## 5. 仍缺的 SKU

以下用户点过的 SKU 在 exe 目录、full 目录、sku_live 里都没有可用映射：

```
19428, 241, 242, 31816
```

`241` 在 sku_live 里有一条记录但 price=0，不可用。要补这些，需要新的
内存采集（在用户点开对应界面时跑 `sku-live.on`），或真实服务端响应样本。

## 6. 本轮文件

| 文件 | 说明 |
|---|---|
| `_scan_market_tables_live.py` | 运行时/离线定位 6 表 + dump `.tvm0`（本轮修好模块签名/覆盖/按页 dump） |
| `_build_merged_catalog.py` | 生成保守合并目录 |
| `marketplace-catalog-merged.json` | 37,793 条合并目录 |
| `marketplace-catalog-merged.on` | 启用开关（回滚=删除） |
| `_verify_merged_purchase.py` | 真实数据临时副本购买验证 |
| `marketplace_store.py` | `catalog_path()` 增加 merged 分支 |
| `mem_tvm0/t020,t090,t180/` | Base.dll `.tvm0` 运行时快照（32,890,880 B ×3） |
| `mem_tvm0_WRONG_TerSafe_20261006/` | 第一版误抓的 TerSafe 节（留作证据） |

## 7. 下一步

1. **实机点购验证**：进大厅，把那几件买一遍，看服务端日志是否出现
   `购买成功 sku=37116` / `16096` / `31774`，以及客户端是否刷新库存。
2. 若客户端仍无反应，问题就只剩"购买应答格式"这一层
   （服务端目录已不是瓶颈）。
3. 补 `19428/241/242/31816`：在用户点开对应界面时跑 `sku-live.on`
   重新采集，再并入 merged。

---

## 8. 2026-10-06 深夜追加: 实机点购结果

### 8.1 武器类完全打通

用户实机点购, 服务端真实扣款入库:

```
25324 -> Item 2135  GP 2680  成功
27000 -> Item 2137  GP  380  成功
```

库存 7611 -> 7612, 余额按价扣减。**武器购买链路没有问题。**

### 8.2 名片/称号类: SKU 都在目录里, 卡在"货币字段"

用户实际点的是这批 SKU:

| SKU | 目录 Item | 目录 Currency | 客户端请求 | 结果 |
|---|---|---|---|---|
| 39038 | 31518 | 1 (CP) | 2 (GP) | 曾 Unsupported |
| 39601 | 31993 | 1 (CP) | 2 (GP) | 曾 Unsupported |
| 40284 | 32570 | 1 (CP) | 2 (GP) | 曾 Unsupported |
| 41526 | 34427 | 1 (CP) | 2 (GP) | 曾 Unsupported |
| 45137 | 36806 | 1 (CP) | 2 (GP) | 曾 Unsupported |

`Unsupported SKU/currency/quantity` 不是"SKU 不存在" —— 是**目录里
Currency 记成了 CP, 客户端用 GP 请求**。这些外观条目的 Currency 是内存
采集猜的, 不可靠。

**修复**: 新增开关 `marketplace-currency-lenient.on`。SKU 存在时不再因
Currency 不一致拒绝, 直接按客户端请求的货币计价(Price 仍用目录值)。
临时副本实测:

```
39038 -> Item 31518 GP 13800  OK
39601 -> Item 31993 GP 29800  OK
40284 -> Item 32570 GP  1980  OK (30 天)
41526 -> Item 34427 GP 59800  OK
45137 -> Item 36806 GP 69800  OK
```

### 8.3 已否证: `public.result` 尾部 125 个 0x07 槽

假设"这 125 槽 = 军牌定制可装备清单"。实现 `_patch_public_tail.py` +
`lobby_server._inject_public_tail()`, 把 22381/22384/15166/29892/16339
等注入空槽, 并在 8/3 保存时持续注入。

**结果: 客户端毫无变化。** 该 125 槽不是名片的拥有判定来源。
实验开关已改名停用(`public-tail-inject.on.rejected_20261006`)。

### 8.4 仍未解决: 客户端只对"武器"认账

事实链:

1. 名片 itemID(22381/22384/15166/16339/29892) **已经在库存里**,
   而且 `Priority` 把它们排在 203 应答最前面; 客户端仍显示未拥有。
2. 服务端把新买的名片项(31518/31993/32570/34427/36806)写进库存,
   客户端也不认。
3. 武器(2135/2137)一买就出现在配装里。

=> 服务端购买链路已经正确, 问题在**客户端对 callsign(名片/称号)
的拥有判定**: 它不走 marketplace inventory, 或需要 callsign 专用表
(`mp/callsign*.csv` 的 ref→itemID 映射)。

### 8.5 下一步(客户端侧, 唯一决定性)

在客户端 hook 以下任一函数, 看它拿到的"库存集合 / itemID"是什么:

```
WL_FillInInventoryProductItems   把库存填进商品条目
IsMarketplaceItemOwned           拥有判定
AS_GetItemIDsFromProduct         productId -> itemID 权威映射
```

推荐先 hook `AS_GetItemIDsFromProduct`: 用户在名片界面翻页时, 会直接
打印出 `productId -> itemID` 的真实映射, 一次拿到缺失的 callsign 表。

### 8.6 当前开关

```
marketplace-catalog-merged.on      开  (37793 条合并目录)
marketplace-currency-lenient.on    开  (按客户端请求货币计价)
public-tail-inject.on              已停用(无效实验)
```
