# -*- coding: utf-8 -*-
"""全盘搜 Callsign(名片/称号/徽章/边框)资源 —— 不限于 marketplace 包。

已知 marketplace 包里只有:
    pcb_*(名片背景) 1196 / pci_*(头像) 441 / pcn/pcf/pcab/pcai/pcaf / bdg/pct 极少
称号 pct_ 只找到 pct_default —— 说明其余称号资源在**别的包**里。

本脚本扫 IIPS 下全部 .ifs/.ff(含工具目录的副本), 用 `前缀_名字` 的正则抓
Callsign 类资源名, 汇总成全集。
"""
import os
import re
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))

# 所有 Callsign 相关前缀(来自 exe 物品类型码 + 已确认资源)
PREFIXES = ["pcb", "pci", "pcn", "pcf", "pcab", "pcai", "pcaf",
            "bdg", "pct", "cnc", "pca"]

SCAN_DIRS = [
    os.path.join(ROOT, "..", "COD OL", "IIPS", "IIPSDownload"),
    os.path.join(ROOT, "..", "COD OL", "main"),
]


def scan_file(path, pat):
    try:
        b = open(path, "rb").read()
    except Exception:
        return Counter()
    c = Counter()
    for m in pat.finditer(b):
        c[m.group(0).decode("latin1")] += 1
    return c


def main():
    pat = re.compile(rb"(?:" + b"|".join(p.encode() for p in PREFIXES) +
                     rb")_[A-Za-z0-9_]{2,48}")
    agg = Counter()
    per = defaultdict(Counter)
    n = 0
    for d in SCAN_DIRS:
        d = os.path.abspath(d)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.lower().endswith((".ifs", ".ff", ".bin")):
                continue
            p = os.path.join(d, fn)
            try:
                if os.path.getsize(p) > 900 * 1024 * 1024:
                    continue
            except Exception:
                continue
            c = scan_file(p, pat)
            if c:
                n += 1
                agg.update(c)
                per[fn] = c
                print("%-56s %d 个 Callsign 名" % (fn, len(c)))
    print("----")
    print("命中文件 %d 个, 去重 Callsign 资源名 %d 个" % (n, len(agg)))
    pref = Counter(k.split("_")[0] for k in agg)
    for k, v in pref.most_common():
        print("   %-6s %5d" % (k, v))
    out = os.path.join(ROOT, "mkt_assets", "callsign_all.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for k in sorted(agg):
            f.write("%s\t%d\n" % (k, agg[k]))
    print("写出", out)


if __name__ == "__main__":
    main()
