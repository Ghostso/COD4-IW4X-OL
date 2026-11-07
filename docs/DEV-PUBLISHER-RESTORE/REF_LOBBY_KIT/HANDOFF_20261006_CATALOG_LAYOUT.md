# CODOL 商城目录布局 —— 2026-10-06 进展与结论

## 一句话

客户端运行时商品记录的布局已经**钉死并可复现**：

```
+0x00 SKU
+0x08 价格(变体 A)
+0x0C 价格(变体 B)
+0x14 物品 ID(客户端自己的编号空间)
+0x1C 类别
```

价格已用 exe 目录交叉验证（330/336 吻合）。
**但客户端的物品 ID 编号与 exe 目录 / 库存的编号不是同一套**，
所以直接拿 exe.Item 或库存 key 去填目录仍然买不进去。

## 已验证事实

### 1. 购买帧里只有 SKU，没有 Item

`lobby_tasks.bin` 里 80/154 与 93/131 的 payload 都是 58 字节，结构固定：

```
10 00 | 08 <sku u32> | 08 01 00 00 00 | 08 01 00 00 00 |
01 00 | 08 01 00 00 00 | 0A 00 00 00 00 00 00 00 00 |
10 00 | 08 00 00 00 00 | 08 00 00 00 00 |
03 00 | 08 <currency u32> | 00
```

实测样例（hex 里 `cd790000` = 31181、`e44b0000` = 19428）：

- 93/131 sku=31181 currency=0
- 93/131 sku=19428 currency=0
- 80/154 sku=37251 currency=1

结论：**购买请求只带 SKU + 货币，不带物品 ID**。

### 2. 运行时记录布局（0x60 步长，来自 r_259D0000_06400000.bin）

干净的连号样本（SKU 连号 → Item 也连号）：

```
37115 -> price=8000   item=29766  cat=4
37116 -> price=10000  item=29767  cat=4
37117 -> price=8000   item=29768  cat=4
37118 -> price=10000  item=29769  cat=4

28847 -> price=5000   item=20469  cat=2
28849 -> price=5000   item=20470  cat=2

17272 -> price=1500   item=10032  cat=1
17274 -> price=1500   item=10033  cat=1
17276 -> price=2500   item=10034  cat=1
17278 -> price=3800   item=10035  cat=1
17280 -> price=2500   item=10036  cat=1
17282 -> price=3800   item=10037  cat=1
```

连号 SKU 对应连号 Item —— 这是物品 ID 枚举的硬特征，
不是随机噪声（随机基线下 5 个连续值同时对齐的概率可忽略）。

### 3. 价格字段的交叉验证

与 `marketplace-catalog.json` 重叠的 SKU 里，
`+0x0C`（或变体的 `+0x08`）等于 exe.Price 的有 330/336。

结论：价格字段确认；`+0x14` 不是价格。

## 关键卡点

### A. 客户端 Item 编号 ≠ exe.Item 编号 ≠ 库存 key

- 已知成功入库的一笔：`sku=32223 → 库存 key 18481`（exe 目录也记 Item=18481）。
- 但 `sku=32223` 在**运行时内存里根本没有干净记录**（clean hits = 0）。
- 反过来，用户点过的 105 个 SKU，**0 个**出现在 exe 的 37615 条目录里。
- `+0x14` 的值落在 exe.Item 全集的比例只有 8.7%（随机基线 3.5%），
  说明只是数值区间重叠，不是同一套编号。

也就是说：

```
购买帧 SKU  ──(客户端运行时表)──> 客户端 Item 编号
exe 目录 SKU ──(exe 目录)──────> exe Item 编号（与库存一致）
```

这两条链目前没有打通的证据。

### B. 105 个已点 SKU 的完整提取结果

已导出到 `mkt_assets/client_catalog.csv`（本次），
105 个 SKU 里 99 个拿到候选、剔除 2 个歧义后剩 **97 条干净记录**：
例如 980→13、984→49、986→51、16350→8270、19428→16339、
37115→29766、37251→29892。

提取判据（每条都过审计）：

```
+0x04 == 0 且 +0x10 == 0
+0x1C 是 -1 或 0..15 的类型枚举
+0x14 是 1..500000 的物品 ID
价格在 +0x0C(标准) 或 +0x08(变体), 且 >= 10
同一 SKU 若有两个票数相同的候选 -> 剔除
```

审计脚本 `_audit_client_catalog.py` 输出：**冲突 0、缺失 0、干净 97**。

## 下一步（按优先级）

1. **实测购买（已就绪）**：

   ```powershell
   # 打开客户端目录开关
   New-Item -ItemType File -Path 'REF_LOBBY_KIT\marketplace-catalog-client.on' -Force

   # 跑一轮
   python -X utf8 "CODOLServer\_mainline\agent_client.py" run python -X utf8 `
     "D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT\run_all.py" --secs 300 --out n10clientcat.txt
   ```

   进大厅点军牌定制/商城里的商品购买，看是否入库、扣款是否正确。
   这份目录里 **97 条**全部是**你实际点过**的 SKU，货币取自真实购买帧。
   （105 个已点 SKU 里 6 个在主区没有干净记录，2 个有互斥候选，
   按"不猜"原则剔除。）

2. 若购买仍失败，看 `lobby_srv.log` 里那笔的报错：
   - `Unsupported SKU/currency/quantity` → 货币不匹配（对照 `sku_currency.csv`）
   - `Insufficient balance` → 余额
   - 其它 → 需要运行时挂钩
     `AS_GetItemIDsFromProduct` / `AS_GetItemInfoBySku` 抓真实映射。

3. 若购买成功但仓库没出现，说明 `Item` 只是目录序号而不是库存键，
   这时才需要挂钩拿 `AS_GetItemIDsFromProduct` 的真实返回值。

## 已就绪的开关与文件

| 文件 | 作用 |
|---|---|
| `marketplace-catalog-client.json` | 客户端真实目录（37615 + 97 条） |
| `marketplace-catalog-client.on` | 开关（默认不存在 = 用旧目录） |
| `mkt_assets/client_catalog.csv` | 97 条 (sku, price, item) |
| `mkt_assets/sku_currency.csv` | 102 个 SKU 的真实货币 |

## 项目内相关文件（本次新增）

生产用:

- `marketplace-catalog-client.json` —— 客户端真实目录（37615 + 97 条）
- `marketplace-catalog-client.on` —— 启用开关（默认不存在）
- `_extract_client_catalog.py` —— 提取 (SKU, Price, Item, Category)
- `_extract_sku_currency.py` —— 从购买帧提取真实货币
- `_build_client_catalog.py` —— 生成客户端目录
- `_verify_client_catalog.py` —— 校验目录 + 开关
- `marketplace_store.py` —— 新增 `catalog_path()` 开关分支（默认行为不变）

分析与验证:

- `_final_field_check.py` —— 字段判定 + 105 SKU 明细
- `_dump_clicked_records.py` —— 已点 SKU 原始记录
- `_inspect_serial_records.py` —— 连号样本原始记录
- `_test_known_good.py` —— 已知成功 SKU 的决定性测试
- `_probe_item_mapping.py` —— 购买帧 + 物品字段探查
- `_analyze_real_catalog.py` —— 0x60 布局交叉验证
- `_check_runtime_items_in_inventory.py` —— 运行时 item 与库存比对
- `_audit_client_catalog.py` —— 97 条逐条审计（冲突/缺失检查）

数据:

- `mkt_assets/client_catalog.csv` —— 97 条 (sku, price, item)
- `mkt_assets/sku_currency.csv` —— 102 个 SKU 的真实货币
