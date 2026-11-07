# -*- coding: utf-8 -*-
"""把"客户端实际点过的 SKU"与内存采集表合并成一份可用目录。

数据源:
  A. lobby_tasks.bin        里 80/154 + 93/131 的购买请求 -> sku
  B. mem_sku/sku_live.txt   内存采集到的 sku -> price/f0C/f10

输出: mkt_assets/verified_skus.csv
"""
import csv
import os
import struct

ROOT = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(ROOT, "lobby_tasks.bin")
LIVE = os.path.join(ROOT, "mem_sku", "sku_live.txt")
OUT = os.path.join(ROOT, "mkt_assets", "verified_skus.csv")


def read_bought():
    out = {}
    try:
        raw = open(TASKS, "rb").read()
    except Exception:
        return out
    off = 0
    while off + 6 <= len(raw):
        svc = raw[off]
        task = raw[off + 1]
        ln = struct.unpack_from("<I", raw, off + 2)[0]
        if off + 6 + ln > len(raw):
            break
        pl = raw[off + 6:off + 6 + ln]
        off += 6 + ln
        if (svc, task) not in ((80, 154), (93, 131)):
            continue
        vals = []
        i = 0
        while i < len(pl):
            t = pl[i]
            i += 1
            if t == 0x08 and i + 4 <= len(pl):
                vals.append(struct.unpack_from("<I", pl, i)[0])
                i += 4
            elif t == 0x03 and i + 1 <= len(pl):
                vals.append(pl[i])
                i += 1
            elif t in (0x09, 0x0A) and i + 8 <= len(pl):
                vals.append(struct.unpack_from("<Q", pl, i)[0])
                i += 8
            elif t == 0x10:
                j = pl.find(b"\x00", i)
                i = j + 1 if j >= 0 else len(pl)
            else:
                break
        if len(vals) > 1:
            out[vals[1]] = svc
    return out


def read_live():
    out = {}
    try:
        for ln in open(LIVE, encoding="utf-8"):
            p = ln.rstrip("\n").split("\t")
            if len(p) >= 2 and p[0].isdigit():
                out[int(p[0])] = (int(p[1]),
                                  int(p[2]) if len(p) > 2 and p[2].lstrip("-").isdigit() else 0,
                                  int(p[3]) if len(p) > 3 and p[3].lstrip("-").isdigit() else 0)
    except Exception:
        pass
    return out


def main():
    bought = read_bought()
    live = read_live()
    print("客户端点过的 sku: %d" % len(bought))
    print("内存采集到的 sku: %d" % len(live))
    allk = sorted(set(bought) | set(live))
    rows = []
    for k in allk:
        price, f0c, f10 = live.get(k, (None, 0, 0))
        rows.append({"sku": k,
                     "price": "" if price is None else price,
                     "f0C": f0c, "f10": f10,
                     "bought": "1" if k in bought else "",
                     "src": ("both" if (k in bought and k in live)
                             else ("bought_only" if k in bought else "mem_only"))})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["sku", "price", "f0C", "f10", "bought", "src"])
        w.writeheader()
        w.writerows(rows)
    both = [r for r in rows if r["src"] == "both"]
    bo = [r for r in rows if r["src"] == "bought_only"]
    mo = [r for r in rows if r["src"] == "mem_only"]
    print("导出 %d 条 -> %s" % (len(rows), OUT))
    print("  两者都有(最可靠): %d" % len(both))
    print("  只有购买记录(缺价格): %d" % len(bo))
    print("  只有内存记录: %d" % len(mo))
    print()
    print("【最可靠的那批(客户端点过 + 有价格)】")
    for r in both[:30]:
        print("   sku=%-7d price=%-8s f0C=%-6s f10=%s"
              % (r["sku"], r["price"], r["f0C"], r["f10"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
