# -*- coding: utf-8 -*-
"""搞清两套 SKU 编号的关系。

事实:
  - 武器类 SKU(22251/22255/31726/31847) 既在客户端点击流里, 也在 exe 目录里
  - 名片/道具类 SKU(37116/37251/16096/19428/31184) 只在客户端点击流里

假设 A: exe 目录是老版本(不含后加的网页活动道具)
假设 B: 两套编号不同源

判据: 若 exe 目录里也有"同价位/同类别"的条目, 只是编号不同 -> 假设 A
      若 exe 目录的编号体系完全对不上 -> 假设 B
"""
import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
CLICKED = (37116, 37251, 16096, 19428, 31184, 39115, 31816, 18079, 37253)
OK_SKUS = (22251, 22255, 31726, 31847)


def main():
    cat = {int(e["Id"]): e for e in
           json.load(open(os.path.join(ROOT, "marketplace-catalog.json"),
                          "r", encoding="utf-8"))}
    print("exe 目录 %d 条" % len(cat))
    ids = sorted(cat)
    print("SKU 范围: %d .. %d" % (ids[0], ids[-1]))
    print()
    # 段分布
    seg = Counter(i // 5000 for i in ids)
    print("SKU 按 5000 分段的条目数:")
    for s in sorted(seg):
        print("  %6d-%6d : %d" % (s * 5000, s * 5000 + 4999, seg[s]))
    print()
    print("能买到的武器 SKU 落在哪段:")
    for s in OK_SKUS:
        print("  %-7d -> 段 %d, Cat=%s" % (s, s // 5000, cat.get(s, {}).get("Category")))
    print()
    print("点过但买不到的 SKU 落在哪段:")
    for s in CLICKED:
        print("  %-7d -> 段 %d, 在目录=%s"
              % (s, s // 5000, "是" if s in cat else "否"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
