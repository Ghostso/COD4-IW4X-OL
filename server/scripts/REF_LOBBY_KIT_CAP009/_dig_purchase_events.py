# -*- coding: utf-8 -*-
"""挖客户端"购买"相关的事件名与状态字段 —— 看它凭什么判定成功/失败。

已知字符串: evt_market_purchase_task_fail
目标: 找到成功事件 + 它读取的响应字段。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MEM = os.path.join(ROOT, "mem_linear")
KEYS = [b"evt_market_purchase_task_fail", b"evt_market_purchase",
        b"market_purchase", b"MKT_Purchase", b"purchaseStatus",
        b"purchaseTask"]


def main():
    for key in KEYS:
        print("=" * 78)
        print("KEY %s" % key.decode())
        found = 0
        for fn in sorted(os.listdir(MEM)):
            p = os.path.join(MEM, fn)
            if not os.path.isfile(p):
                continue
            try:
                b = open(p, "rb").read()
            except Exception:
                continue
            i = b.find(key)
            if i < 0:
                continue
            found += 1
            if found > 2:
                break
            print("  %s @0x%X" % (fn, i))
            lo = max(0, i - 0x200)
            hi = min(len(b), i + 0x300)
            strs = re.findall(rb"[ -~]{4,90}", b[lo:hi])
            for s in strs[:45]:
                print("      %s" % s.decode("latin1"))
        if not found:
            print("  (内存里没有)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
