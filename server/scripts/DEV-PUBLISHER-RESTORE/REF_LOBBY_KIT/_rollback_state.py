# -*- coding: utf-8 -*-
"""回滚这几轮"猜字段"造成的状态改动, 回到已知可用的起点。

回滚项:
  1. marketplace-inventory.json 从 .bak_full 恢复(完整 17372 件)
  2. 清掉 Priority 里我后加的那些(保留原有的)
  3. 确认没有残留的开关文件

★ 不删任何文件, 只恢复内容。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
INV = os.path.join(ROOT, "marketplace-inventory.json")
BAK_FULL = os.path.join(ROOT, "marketplace-inventory.json.bak_full")


def main():
    print("当前 inventory: %d 件"
          % len(json.load(open(INV, "r", encoding="utf-8")).get("Items", {})))
    if not os.path.exists(BAK_FULL):
        print("缺 %s, 无法回滚" % BAK_FULL)
        return 1
    full = json.load(open(BAK_FULL, "r", encoding="utf-8"))
    print("bak_full: %d 件" % len(full.get("Items", {})))
    with open(INV, "w", encoding="utf-8") as f:
        json.dump(full, f, ensure_ascii=False, separators=(",", ":"))
    print("已恢复为 %d 件 (Priority=%s)"
          % (len(full.get("Items", {})), full.get("Priority")))
    print()
    for flag in ("marketplace-catalog-client.on",
                 "marketplace-inventory-full.on",
                 "marketplace-skus-allow-unsafe.on"):
        p = os.path.join(ROOT, flag)
        print("  %-40s %s" % (flag, "存在" if os.path.exists(p) else "不存在"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
