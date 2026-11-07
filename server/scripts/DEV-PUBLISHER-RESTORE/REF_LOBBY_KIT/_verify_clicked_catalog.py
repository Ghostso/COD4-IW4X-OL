# -*- coding: utf-8 -*-
"""逐个核对用户点过的 SKU: 在 exe 目录里吗? 在客户端目录里吗? 真实字段?

这能一次性判定: 我们是不是把 exe 已有的正确数据覆盖错了。
"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SKUS = (610, 611, 1011, 19428, 21718, 31184, 32327, 41314, 37251, 18079,
        16350, 16092, 39039)


def load(name):
    p = os.path.join(ROOT, name)
    if not os.path.exists(p):
        return {}
    return {int(e["Id"]): e for e in json.load(open(p, "r", encoding="utf-8"))}


def main():
    exe = load("marketplace-catalog.json")
    cli = load("marketplace-catalog-client.json")
    print("exe 目录 %d 条, 客户端目录 %d 条" % (len(exe), len(cli)))
    print()
    hdr = "%-8s %-22s %-30s" % ("sku", "exe 目录", "客户端目录(实际使用)")
    print(hdr)
    print("-" * len(hdr))
    for s in SKUS:
        a = exe.get(s)
        b = cli.get(s)
        def fmt(e):
            if not e:
                return "—"
            return "it=%-6d C=%d %s p=%-6d d=%d %s" % (
                e["Item"], e["Category"],
                "CP" if e["Currency"] == 1 else "GP",
                e["Price"], e["SelectedDays"],
                "堆叠" if e["Stackable"] else "唯一")
        print("%-8d %-28s %s" % (s, fmt(a), fmt(b)))
    print()
    print("差异: 客户端目录里 Category/Stackable 与 exe 不同的条目")
    n = 0
    for s in sorted(set(exe) & set(cli)):
        if (exe[s]["Category"] != cli[s]["Category"]
                or exe[s]["Stackable"] != cli[s]["Stackable"]
                or exe[s]["Item"] != cli[s]["Item"]
                or exe[s]["Price"] != cli[s]["Price"]):
            print("  sku=%-7d exe=%s -> cli=%s"
                  % (s, (exe[s]["Item"], exe[s]["Category"], exe[s]["Stackable"]),
                     (cli[s]["Item"], cli[s]["Category"], cli[s]["Stackable"])))
            n += 1
            if n > 10:
                break
    print("  (共检查完, 以上为前 10 例)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
