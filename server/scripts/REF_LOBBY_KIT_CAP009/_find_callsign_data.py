# -*- coding: utf-8 -*-
"""在内存里找 callsign 表的**数据**(不是表名)。

已知真实资源名前缀(来自 mkt_assets 的 7608 条 callsign 资源):
  pcb_ (名片背景 1205)  pci_ (名片图标 442)  pcai_ / pcab_ / pcf_ / pcaf_
  pcn_ / cnc_ / bdg_

如果客户端把表解密进内存, 这些前缀会成片出现。
"""
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
MEMDIR = os.path.join(ROOT, "mem_linear")
PRE = [b"pcb_", b"pci_", b"pcab_", b"pcai_", b"pcf_", b"pcaf_", b"pcn_",
       b"cnc_", b"bdg_", b"pct_"]


def main():
    total = Counter()
    files = 0
    best = []
    for fn in sorted(os.listdir(MEMDIR)):
        p = os.path.join(MEMDIR, fn)
        if not os.path.isfile(p):
            continue
        try:
            b = open(p, "rb").read()
        except Exception:
            continue
        files += 1
        c = Counter()
        for pre in PRE:
            n = b.count(pre)
            if n:
                c[pre.decode()] = n
                total[pre.decode()] += n
        if c:
            best.append((fn, sum(c.values()), c))

    print("扫 %d 个区" % files)
    print("全局前缀统计:", dict(total))
    print()
    best.sort(key=lambda x: -x[1])
    print("命中最多的区:")
    for fn, n, c in best[:20]:
        print("  %-38s %6d  %s" % (fn, n, dict(c)))

    # 对命中最多的区, 打印上下文
    if best:
        fn, n, c = best[0]
        b = open(os.path.join(MEMDIR, fn), "rb").read()
        for pre in PRE:
            i = b.find(pre)
            if i < 0:
                continue
            print()
            print("=== %s 里 %s @0x%X 附近 ===" % (fn, pre.decode(), i))
            lo = max(0, i - 64)
            hi = min(len(b), i + 512)
            strs = re.findall(rb"[ -~]{4,120}", b[lo:hi])
            for s in strs[:30]:
                print("  %s" % s.decode("latin1"))
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
