# -*- coding: utf-8 -*-
"""看这次真入库的 SKU(22255/31847/31726) 与失败的, 类别差异。"""
import json
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(ROOT, "lobby_tasks.bin")
OK = (22255, 31847, 31726, 37251, 31184, 19428)
FAIL = []


def scan_fields(pl):
    out = []
    i = 0
    n = len(pl)
    while i < n:
        t = pl[i]
        i += 1
        if t in (0x01, 0x03):
            i += 1
        elif t == 0x06:
            i += 2
        elif t in (0x07, 0x08):
            out.append(struct.unpack_from("<I", pl, i)[0]); i += 4
        elif t in (0x09, 0x0A):
            i += 8
        elif t == 0x10:
            j = pl.find(b"\x00", i)
            if j < 0:
                break
            i = j + 1
        elif t == 0x13:
            if i + 5 > n or pl[i] != 0x08:
                break
            ln = struct.unpack_from("<I", pl, i + 1)[0]
            i += 5 + ln
        else:
            break
    return out


def main():
    cat = {int(e["Id"]): e for e in
           json.load(open(os.path.join(ROOT, "marketplace-catalog.json"),
                          "r", encoding="utf-8"))}
    raw = open(TASKS, "rb").read()
    off = 0
    frames = []
    while off + 6 <= len(raw):
        svc = raw[off]; task = raw[off + 1]
        ln = struct.unpack_from("<I", raw, off + 2)[0]
        if off + 6 + ln > len(raw):
            break
        pl = raw[off + 6:off + 6 + ln]
        off += 6 + ln
        if (svc, task) not in ((80, 154), (93, 131)):
            continue
        v = scan_fields(pl)
        if len(v) >= 4 and v[1]:
            frames.append((svc, v[1]))
    print("任务文件里的购买帧: %s" % frames)
    print()
    print("%-8s %-10s %-6s %-8s %s" % ("sku", "在 exe", "Cat", "item", "货币"))
    print("-" * 50)
    for svc, s in sorted(set(frames)):
        e = cat.get(s)
        if e:
            print("%-8d %-10s %-6d %-8d %s"
                  % (s, "是", e["Category"], e["Item"],
                     "CP" if svc == 80 else "GP"))
        else:
            print("%-8d %-10s %-6s %-8s %s"
                  % (s, "★否", "-", "-", "CP" if svc == 80 else "GP"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
