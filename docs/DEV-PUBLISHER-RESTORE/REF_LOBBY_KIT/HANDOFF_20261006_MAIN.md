# CODOL 离线复活 —— 2026-10-06 主交接文档

> 本文取代本轮其它 6 篇 HANDOFF（CATALOG_LAYOUT / CALLSIGN_CHANNEL /
> PURCHASE_FIX / BUY_MATRIX / REVERSE_SUMMARY / MARKET_MANIFEST）。
> 那些文档保留作为**证据底稿**，但结论以本文为准（其中若干条已被后续推翻，见 §5）。

---

## 0. 当前状态（可直接接手）

```
目录
  marketplace-catalog.json         37615 条   ← 服务端实际使用的目录
  marketplace-catalog-client.json  37615 条   ← 同上（已回滚为 exe 版本）
  marketplace-catalog-full.json    38424 条   ← 内存采集版（未启用）

库存
  marketplace-inventory.json        7609 件   ← 当前在用
  .bak_big / .bak_full             17372 件   ← 全量赠送版（备份）
  .bak_before_allitems_*               7 件   ← 原始小仓库（备份）

开关（均为项目既有开关，非本轮新增）
  marketplace-catalog-client.on / mirror_predicted.on / poke_off.flag
  ready_push.on / sku-live.on / tas_off.flag
```

## 1. 唯一核心结论

**能不能买，只取决于该 SKU 在不在服务端目录 `marketplace-catalog.json` 里。**

与类别（武器/名片/道具）、货币（CP/GP）都无关。用户观察到的
"武器能买、名片道具不能买"，是**目录覆盖差异**，不是类别限制。

### 实测矩阵（同一次会话，服务端日志带库存件数变化）

| SKU | 在 exe 目录 | Category | 结果 | 库存变化 |
|---|---|---|---|---|
| 22251 / 22255 / 31726 / 31847 | **是** | 3（武器） | 购买成功 | 7600→7601→7602→7603 |
| 37251 | 否 | — | 已拥有，不重复加 | 不变 |
| 37116 / 16096 / 19428 / 31184 | 否 | — | **Unsupported SKU** | 不变 |

购买帧格式在成功/失败两种情况下**逐字节相同** —— 证明失败不是解析问题。

## 2. 根因：两套目录不是一份数据

客户端真正使用的是 **6 张 `coMarketplace*.csv`**，由
`mp/marketplace.json`（内存里 zlib 压缩）索引：

```
coMarketplaceSKUs.csv            SKU 定义
coMarketplaceProducts.csv        商品（productId）
coMarketplaceProductItems.csv    ★ productId → itemId
coMarketplaceItems.csv           itemId → 类型/名称
coMarketplaceDiscounts.csv
unlockFlags.csv
version = 1625160
```

另有 CODOL 专属的 `conoMarketplaceitems.csv`（`cono` = COD Online），
内存里**内容已明文**：含 Levisthan / Tyrant / Aurora / Wareagle 等品牌
与武器 ref（如 `mp5ktool_mp|ak47tool_mp|scarsaprreskin_mp`）。

**exe 反射提取的 `marketplace-catalog.json` 只是其中一小部分**，
所以用户能点到的很多 SKU 服务端根本不认识。

## 3. 为什么拿不到那 6 张表（已穷尽验证）

### 3.1 不在 .ifs 包里

```
974 个 .ifs 全扫：
  1,469,394 个 zlib 流，按 MD5 比对 → 命中 0 / 6
```

**方法论自检**（防止误判）：

```
lf_init_common_marketplace_1_V49.ifs 内：
  main/images      4215 次  ← 资源路径是明文，证明"能搜到"
  iwi              4248 次
  pcb_amorphous01     0 次  ← 资产数据是加密/压缩的
```

即 `.ifs` 是**部分明文（路径表）+ 部分加密（资产数据）**，
所以"字符串 0 命中"不能否证 —— **MD5 全量扫描才是可靠的否证**。

### 3.2 不在文件系统里（已实测过）

磁盘 `mp/marketplace.json` 是我们之前放的**探针**，内容为：

```
"_experiment_artifact": true, "_result": "NEGATIVE",
"_note": "客户端不读 mp/marketplace.json 这个明文文件 ...
         This asset must be registered in the asset table at 0x239B120"
```

2026-09-29 已验证：**放明文文件无效**。

### 3.3 资源表在 .tvm0（壳虚拟化节）—— 本轮定位结果

`0x239B120` 是 **RVA**（此前被误当作文件偏移读，得出乱码）。
按 PE 节区表映射后：

```
Base.dll  ImageBase 0x10000000
  .tvm0   RVA 0x19DD000  VirtSize 0x1F5E000 (32MB)  RawPtr 0x19D1E00

RVA 0x239B120 → .tvm0 off 0x238FF20 : 03 bf 4e d9 ... 高熵（加密）
RVA 0x49D3B0  → .text  off 0x49C7B0 : 04 89 44 24 78 ... 正常 x86 代码
```

**结论：资源注册表位于 TP3 壳的虚拟化节，只有运行时解密后才存在。**
静态分析到此为止。

## 4. 客户端数据结构（权威，来自内存 ActionScript 元数据）

```
商品对象: currency | price | purchasable | productId | stackable |
          duration | promoSkuId | SKUObj | skuId
物品对象: currencyID | itemType | itemId | seasonTime | seasonName |
          seasonId | rewardType
名片对象: cardTitleItemID | cardIconItemID | cardBackgroundItemID |
          cardNameplateItemID | cardTitleURL | cardIconURL |
          cardBackgroundURL | cardFrameURL | cardTitleTryon | ...
函数:     GetItemInfoBySku | GetItemInfo | isOwned | selectBestSKU | SKUs
          | MKT_UpdateInventory | MKT_InvalidatePreviewList
          | WL_FillInInventoryProductItems（武器专用）
```

## 5. 已否证的假设（避免重复踩坑）

| 假设 | 结论 |
|---|---|
| 购买应答格式错 | 否。已改为与 C# 一致的"空对象+status"，仍无效 |
| 库存 480KB 截断 | 否。已缩到 7600 件（460KB）无截断，仍无效 |
| 两套 SKU 编号不兼容 | 否。失败与成功 SKU 落在同编号区间，且 39115 在目录里 |
| 表在 .ifs 包里 | 否。974 包 / 146 万 zlib 流 / MD5 全比对 → 0 命中 |
| 放明文 marketplace.json 可行 | 否。2026-09-29 实测 NEGATIVE |
| 内存记录 `+0x18`/`+0x1C` 是 Category | 否。70% 落 Cat0，无稳定对应 |
| 那 499KB 抓包是称号表 | 否。是本地化字幕（`ab_1mc_*` / `uk_*`） |
| public.result 尾部 125 项非名片清单 | 该结论已修正：那是客户端上传时自带的尾字段 |

## 6. 本轮已修复/确认（可保留）

- **`8/3` 玩家档案上传**：此前一律回空 ACK，客户端上传的档案被丢弃。
  已按 C# `SavePublicProfile` 逐字节实现并验证：
  CRC 校验通过、魔数 233 / 1248641861 均吻合，
  重建出的 `public.result` 为 33428 字节，与现有文件**完全一致**。
- **购买应答**：改为与参考实现一致的"空对象 + status=0"。
- **库存体积**：7600 件 / 460KB，无截断。
- **目录回滚**：撤掉从内存推断的 101 条（item 值集中在 12/13/28/49 等
  个位数，是噪声），回到 exe 反射的权威版本。

## 7. 下一步（按优先级）

### 7.1 唯一能跨过去的一步

**在游戏运行时 dump `.tvm0` 的运行时映射。**

目标地址范围：`模块基址 + 0x19DD000 .. 模块基址 + 0x393B000`（约 32MB）。
拿到后用 `mp/marketplace.json` 里的 6 个 MD5 反查定位那 6 张表。

两个做法：
- **A（不动逻辑，推荐）**：调整 `memlinear` 转储的**地址范围**，
  对准 `.tvm0`，在游戏打开商城界面时抓。
- **B**：改 `nt10.py` 加周期扫描，每 15 秒按 MD5 扫内存，命中即 dump
  （不用卡时机，但要改启动脚本）。

### 7.2 拿到表之后

1. `coMarketplaceProductItems.csv` → **productId → itemId**（权威映射）
2. `coMarketplaceItems.csv` → **itemId → 类型**（权威 Category 等价物）
3. 据此重建服务端目录 → 所有可购买 SKU 都可买

### 7.3 备用路径（若 7.1 受阻）

客户端 `80/70`（getSkusPaginated）请求里带 `version=1625160`，
即它在向服务端**要这份目录**。若能让 80/70 返回**格式正确**的 SKU 页，
客户端就不必依赖本地表。

⚠️ 风险提示：此前自编 SKU 页格式曾把**整个 marketplace 服务打挂**
（仓库/商城全红叹号、角色被锁）。必须先拿到真实 SKU 页字节或
把反序列化器逆到字段级，不能靠猜。

## 8. 运行方式（复现用）

```powershell
# 提权检查（必须）
python -X utf8 "CODOLServer\_mainline\agent_client.py" ping

# 跑一轮
python -X utf8 "CODOLServer\_mainline\agent_client.py" run python -X utf8 `
  "D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT\run_all.py" --secs 420 --out n10.txt

# 杀残留（ACE 保护的必须走提权代理）
python -X utf8 "CODOLServer\_mainline\agent_client.py" run cmd /c `
  "taskkill /F /T /IM codoMP_client_shipRetail.exe"
```

## 9. 本轮新增的分析脚本（REF_LOBBY_KIT/）

**取数/验证**
- `_extract_marketplace_json.py` — 解出 `mp/marketplace.json` 清单
- `_hunt_tables_md5_full.py` — 按 MD5 扫包找表（支持 `marketplace` / `all`）
- `_rva_map.py` — Base.dll RVA→文件偏移映射
- `_validate_string_method.py` — 方法论自检（证明"能搜到"）
- `_md5_in_region.py` — 单区 MD5 反查

**结构分析**
- `_dig_market_obj_fields.py` — 客户端商品/物品字段表
- `_find_co_tables_global.py` — 全局搜 co* 表名
- `_dig_cono_region.py` — 挖 cono 表周边（品牌表）
- `_check_addr_coverage.py` — 地址覆盖检查

**状态**
- `_status_report.py` — 目录/库存/开关总览
- `_syntax_check.py` — 关键脚本语法检查
- `_rollback_state.py` — 状态回滚（未执行）

**未执行（备用）**
- `_locate_239B120.py` — 进程模块定位（游戏未运行时不可用）
- `_scan_all_ifs_csv.py` — 全盘 csv 扫描（已跑完，见 §3.1）

## 10. 硬约束

- 客户端受 ACE/TP3 保护：**后开进程的 `VirtualQueryEx` 会被拒（err=5）**，
  必须用 `nt10.py` 的**早期句柄**（`nt10.py:1888` 注释有说明）。
- 用户已明确：**本轮只做逆向，不改其它东西**。
- `mem_marketplace`（9.5GB 旧转储）用户要求**不要删**。
- 内存转储时机：`memlinear_after.txt` 当前为 **150 秒**，
  转储时**未打开过商城界面** —— 这是拿不到表的直接原因。
