# -*- coding: utf-8 -*-
"""从 lobby_tasks.bin 里把所有"客户端实际点过但目录里没有"的 SKU 找出来。

这些是真实的购买请求, 每一个都代表军牌定制/商城里一个可点的商品。
"""
import csv
import json
import os
import struct
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(ROOT, "lobby_tasks.bin")


def scan_fields(payload):
    out = []
    i = 0
    n = len(payload)
    while i < n:
        tag = payload[i]
        i += 1
        if tag in (0x01, 0x03):
            i += 1
        elif tag == 0x06:
            i += 2
        elif tag in (0x07, 0x08):
            out.append(struct.unpack_from("<I", payload, i)[0]); i += 4
        elif tag in (0x09, 0x0A):
            i += 8
        elif tag == 0x10:
            j = payload.find(b"\x00", i)
            if j < 0:
                break
            i = j + 1
        elif tag == 0x13:
            if i + 5 > n or payload[i] != 0x08:
                break
            ln = struct.unpack_from("<I", payload, i + 1)[0]
            i += 5 + ln
        else:
            break
    return out


def main():
    raw = open(TASKS, "rb").read()
    off = 0
    seen = Counter()
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
        vals = scan_fields(pl)
        if len(vals) >= 4 and vals[1]:
            seen[vals[1]] += 1

    cat = json.load(open(os.path.join(ROOT, "marketplace-catalog-client.json"),
                         "r", encoding="utf-8"))
    have = set(int(e["Id"]) for e in cat)
    missing = sorted(s for s in seen if s not in have)
    print("购买请求里出现的 SKU: %d 个" % len(seen))
    print("目录已有: %d 个" % (len(seen) - len(missing)))
    print("★ 目录缺失: %d 个" % len(missing))
    print()
    for s in missing:
        print("  sku=%-7d x%d" % (s, seen[s]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
