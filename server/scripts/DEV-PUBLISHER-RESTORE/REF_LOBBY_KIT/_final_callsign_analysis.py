# -*- coding: utf-8 -*-
"""名片系统的最终分析汇总 —— 把已确认的事实与缺口一次列清。"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    print("=" * 76)
    print("1) 我们已买到并确认入库的名片类 item")
    print("=" * 76)
    inv = json.load(open(os.path.join(ROOT, "marketplace-inventory.json"),
                         "r", encoding="utf-8"))
    items = inv.get("Items", {})
    for k in ("15166", "22381", "22384", "29892"):
        print("  item %-6s 在库存: %s" % (k, k in items))
    print()
    print("=" * 76)
    print("2) 已抽出的 callsign ref (来自内存)")
    print("=" * 76)
    tot = 0
    for pre in ("pcb", "pci", "pct", "pcab", "pcai", "pcaf", "pcf", "pcn",
                "cnc", "bdg"):
        p = os.path.join(ROOT, "mkt_assets", "callsign_%s.csv" % pre)
        if os.path.exists(p):
            n = sum(1 for _ in open(p, encoding="utf-8-sig")) - 1
            tot += n
            print("  %-5s %5d 条" % (pre, n))
    print("  合计 %d 条" % tot)
    print()
    print("=" * 76)
    print("3) 缺口: ref <-> itemID 映射")
    print("=" * 76)
    print("  已试过且否证的路径:")
    for s in ("ref 后面的 u32 (是图标尺寸)",
              "itemID 附近 ±8KB 搜 ref (0 命中)",
              "mp/item_*.csv 里的连续整数数组 (无)",
              "974 个 .ifs 包里搜表名 (0 命中)",
              "public.result 尾部 125 个 int32 (是 Cat0, 非外观)",
              "8/3 上传的档案 (不含名片清单)"):
        print("    - %s" % s)
    print()
    print("  结论: 映射表只在客户端运行时存在(由加密 FF 解密后生成),")
    print("        必须运行时挂钩才能拿到。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
