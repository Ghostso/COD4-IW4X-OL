# -*- coding: utf-8 -*-
"""打开"item 分组 SKU 页"单条验证（默认关，随时可回滚）。

背景（2026-10-07）：
  客户端运行时目录的模型是 `item -> SKU[]`（同一 item 下 680/7天、
  2580/30天、10880/永久 等多个档）。`market_skus.build_item_sku_page`
  据此编"每个 item 一组、组内多档"的 SKU 页。

  但 80/70 的**外层/字段序仍是假设**（没有第三方参考）。历史上
  "自编 SKU 页"打挂过两次整个 marketplace 服务（仓库/商城变灰、角色锁死），
  所以这一步**只发 ground-truth 支撑的 5 个 item**，并在出错时立即回滚。

用法：
    python -X utf8 enable_itemgroup_sku_test.py            # 开(默认只发 1 个 item)
    python -X utf8 enable_itemgroup_sku_test.py 5          # 开, 发前 5 个 item
    python -X utf8 enable_itemgroup_sku_test.py off        # 关(回安全空页)

回滚：本脚本 off，或直接删这两个文件：
    marketplace-skus-itemgroup.on
    marketplace-skus-count.txt
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
FLAG = os.path.join(ROOT, "marketplace-skus-itemgroup.on")
COUNT = os.path.join(ROOT, "marketplace-skus-count.txt")


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    off = arg.lower() in ("off", "0", "close")
    if off:
        for p in (FLAG, COUNT):
            if os.path.exists(p):
                os.remove(p)
        print("已关闭 item 分组 SKU 页 -> 回安全空页（商城仍空，但不锁 UI）")
        return 0
    try:
        n = max(1, min(5, int(arg))) if arg else 1     # 可信组当前只有 5 个
    except Exception:
        n = 1
    with open(COUNT, "w", encoding="ascii") as f:
        f.write("%d\n" % n)     # 先只发少量, 确认不锁 UI
    with open(FLAG, "w"):
        pass
    print("=" * 66)
    print("已打开 item 分组 SKU 页（实验）")
    print("  marketplace-skus-itemgroup.on  = 开")
    print("  marketplace-skus-count.txt     = %d（只发前 %d 个 item）" % (n, n))
    print("-" * 66)
    print("只发 **ground-truth 支撑**的 item（当前共 5 个）：")
    print("  122 / 7110 / 22384 / 29767 / 29892")
    print("跑一局, 然后运行自动判定：")
    print("  python -X utf8 check_run.py")
    print("先 1 个 item 试; 没问题再:  python -X utf8 enable_itemgroup_sku_test.py 5")
    print("回滚：python -X utf8 enable_itemgroup_sku_test.py off")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    sys.exit(main())
