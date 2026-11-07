# -*- coding: utf-8 -*-
"""找出最近"Unsupported SKU"失败的那些 SKU —— 它们不在我们的目录里。"""
import json
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(ROOT, "lobby_srv.log")
TASKS = os.path.join(ROOT, "lobby_tasks.bin")


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
    raw = open(TASKS, "rb").read()
    off = 0
    seen = []
    while off + 6 <= len(raw):
        svc = raw[off]; task = raw[off + 1]
        ln = struct.unpack_from("<I", raw, off + 2)[0]
        if off + 6 + ln > len(raw):
            break
        pl = raw[off + 6:off + 6 + ln]
        off += 6 + ln
        if (svc, task) not in ((80, 154), (93, 131)):
            continue
        vals = scan_fields(pl)
        if len(vals) >= 4 and vals[1]:
            seen.append((svc, vals[1]))
    print("本轮购买帧 (%d 条):" % len(seen))
    for svc, sku in seen:
        print("  service=%d sku=%d" % (svc, sku))
    print()
    cat = json.load(open(os.path.join(ROOT, "marketplace-catalog-client.json"),
                         "r", encoding="utf-8"))
    have = set(int(e["Id"]) for e in cat)
    miss = sorted(set(s for _, s in seen if s not in have))
    print("★ 不在目录里的 SKU: %s" % miss)
    return 0


if __name__ == "__main__":
    sys.exit(main())
