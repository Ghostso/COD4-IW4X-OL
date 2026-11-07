# -*- coding: utf-8 -*-
"""查 22381/22384/29892 这些 item ID 在 exe 目录/资源里对应什么。"""
import json
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    cat = json.load(open(os.path.join(ROOT, "marketplace-catalog.json"),
                         "r", encoding="utf-8"))
    # exe 目录里 item 的分布
    items = [int(e["Item"]) for e in cat]
    print("exe 目录 item 范围: %d .. %d" % (min(items), max(items)))
    print()
    for target in (22381, 22384, 29892, 8270, 16339, 18481):
        es = [e for e in cat if int(e["Item"]) == target]
        print("item %-6d -> exe 目录里 %d 条: %s"
              % (target, len(es),
                 [(e["Id"], e["Category"], e["Currency"]) for e in es][:4]))
    print()
    # 看 Category 分布
    print("exe 目录 Category 分布:",
          Counter(int(e["Category"]) for e in cat).most_common())
    return 0


if __name__ == "__main__":
    sys.exit(main())
