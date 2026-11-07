# -*- coding: utf-8 -*-
"""构建保守合并目录 marketplace-catalog-merged.json。

背景(2026-10-06):
  * 服务端原来用 exe 反射目录 marketplace-catalog-client.json (37615 条),
    用户实际能点到的 SKU(37116/37251/16096/31184/31774...)不在里面 -> Unsupported SKU。
  * 内存采集版 marketplace-catalog-full.json (38424 条) 多出 809 条;
    其中 Item<100 + Price==9999999 的是布局误命中(哨兵价), 不能全信。
  * 交叉验证: 可信条目的 Item 在 exe 目录里也有同 item 的别的 SKU:
       37116 -> Item 29767  (exe 里 49479/49480 也是 29767)
       31184 -> Item 22384  (exe 里 31759/37990 也是 22384)
    这说明内存采集对这类条目的解析是对的。

策略: 只并入 Item>=1000 的 extras (177 条), 另加显式白名单
      31774(用户点过, Item=122 但无法交叉验证)。
      其余低 Item 噪声不并入。

★ 2026-10-07 复盘(重要): 曾试过把过滤放宽到"Price<9999999 全并入",
  结果把 964/980/982/984/986/988/995/998/1005 这批低 Item 条目也放了进来。
  **这是错的, 已回滚。** 依据 HANDOFF_20261006_CATALOG_LAYOUT.md §3:
  内存记录里的 `+0x14` 是**客户端自己的一套 Item 编号**, 与 exe.Item / 库存 key
  **不是同一套体系**(交叉命中率仅 8.7%, 接近随机基线)。
  把这套编号当 exe.Item 写进服务端目录, 会让购买"假成功但入错物品"
  —— 正是文档反复警告的失败模式。低 Item 条目一律不并入。

输出: marketplace-catalog-merged.json (按 Id 升序)
"""
import json
import os
import sys
import csv

ROOT = os.path.dirname(os.path.abspath(__file__))
CLIENT = os.path.join(ROOT, "marketplace-catalog-client.json")
FULL = os.path.join(ROOT, "marketplace-catalog-full.json")
OUT = os.path.join(ROOT, "marketplace-catalog-merged.json")
# ★ 2026-10-07: 客户端运行时 SKU 表(布局经 ground truth 反证, 见 _extract_sku_table_v2.py)。
#   只并入**合并目录里还没有**的 SKU —— 已有的那些与内存表**编号体系冲突**,
#   一律以 exe/合并目录为准, 不覆盖, 避免"入错物品"。
SKU_TABLE = os.path.join(ROOT, "mkt_assets", "sku_table_v2.csv")
SKU_TABLE_FLAG = os.path.join(ROOT, "catalog-include-sku-table.on")

# 用户实测点过但 Item 无法交叉验证的 SKU -> 显式放行(可随时从名单移除)
EXPLICIT_KEEP = {31774}
MIN_ITEM = 1000


def main():
    cli = json.load(open(CLIENT, "r", encoding="utf-8"))
    full = json.load(open(FULL, "r", encoding="utf-8"))
    cli_by_id = {r["Id"]: r for r in cli}
    kept, skipped = {}, []
    for r in full:
        sid = r["Id"]
        if sid in cli_by_id:
            continue
        if int(r.get("Item", 0)) >= MIN_ITEM or sid in EXPLICIT_KEEP:
            kept[sid] = r
        else:
            skipped.append(r)
    merged = dict(cli_by_id)
    merged.update(kept)
    # ---- 并入"客户端运行时 SKU 表"里合并目录**还没有**的条目 ----
    tbl_added = 0
    if os.path.exists(SKU_TABLE_FLAG) and os.path.exists(SKU_TABLE):
        with open(SKU_TABLE, "r", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                sid = int(r["sku"])
                if sid in merged:            # 编号体系冲突 -> 不覆盖
                    continue
                # ★ 若提取脚本给了 confidence 列, 只并 high(跨区一致/单文件)。
                if r.get("confidence", "high") != "high":
                    continue
                merged[sid] = {
                    "Id": sid,
                    "Item": int(r["item"]),
                    "Currency": 1,           # 有 currency-lenient.on 兜底, 实际按客户端请求币种
                    "Price": int(r["price"]),
                    "Category": 0,
                    "Stackable": False,
                    "Grant": 1,
                    "SelectedDays": int(r["days"]),
                }
                tbl_added += 1
    rows = [merged[k] for k in sorted(merged)]
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, separators=(",", ":"))
    print("client      = %d" % len(cli_by_id))
    print("full        = %d" % len(full))
    print("并入 extras = %d (Item>=%d 或显式白名单)" % (len(kept), MIN_ITEM))
    print("丢弃噪声    = %d (Item<%d 且不在白名单)" % (len(skipped), MIN_ITEM))
    print("SKU 表补入  = %d (catalog-include-sku-table.on)" % tbl_added)
    print("merged      = %d -> %s" % (len(rows), OUT))
    for sid in (37116, 37251, 16096, 31184, 31774):
        r = merged.get(sid)
        print("  %6d %s" % (sid, json.dumps(r, ensure_ascii=False) if r else "MISSING"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
