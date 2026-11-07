#!/usr/bin/env python3
"""137 独立复核 B12/B13: 0x13 room 族头部不变量 + F1=K<<10 + F2=M<<11 + V=02 闭式 + ×4 恒等式.
抽取逻辑复用 blob_typeA_inner.py 的 parse_blobs."""
import json
import struct
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CORPUS = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs = json.load(open(CORPUS, encoding="utf-8"))
TAGS = {0x01: 1, 0x03: 1, 0x06: 2, 0x07: 4, 0x08: 4, 0x09: 8, 0x0a: 8}


def parse_blobs(payload):
    out, i, n = [], 0, len(payload)
    while i < n:
        t = payload[i]
        i += 1
        if t == 0x00:
            continue
        if t == 0x10:
            j = payload.find(b"\x00", i)
            if j < 0:
                break
            i = j + 1
            continue
        if t in TAGS:
            i += TAGS[t]
            continue
        if t in (0x13, 0x6b, 0x6c):
            if i >= n or payload[i] != 0x08:
                break
            i += 1
            if i + 4 > n:
                break
            ln = struct.unpack_from("<I", payload, i)[0]
            i += 4
            data = payload[i:i + ln]
            i += ln
            if t in (0x6b, 0x6c):
                i += 4
            if t == 0x13:
                out.append(data)
            continue
        break
    return out


inner_all = []
for r in recs:
    if r.get("svc") == 11 and r.get("task") == 4:
        for data in parse_blobs(bytes.fromhex(r["payload"])):
            if len(data) < 5:
                continue
            decl = struct.unpack_from("<I", data, 0)[0]
            if decl != len(data) - 4:
                continue
            inner_all.append(data[4:])

room = [x for x in inner_all if x and x[0] == 0x02]
ready = [x for x in inner_all if x and x[0] == 0x18]
print("0x13 内层总数 %d ; room(0x02)=%d ; ready(0x18)=%d ; 其它=%d" % (
    len(inner_all), len(room), len(ready),
    len(inner_all) - len(room) - len(ready)))

inv = Counter()
Kset, Mset = {}, {}
Vcnt = Counter()
for x in room:
    L = len(x)
    F1 = struct.unpack_from("<I", x, 4)[0]
    F2 = struct.unpack_from("<H", x, 8)[0]
    V = x[1]
    Vcnt[V] += 1
    inv["byte2==0"] += (x[2] == 0)
    inv["byte3==0"] += (x[3] == 0)
    inv["byte4==0"] += (x[4] == 0)
    inv["byte7==0"] += (x[7] == 0)
    inv["byte8==0"] += (x[8] == 0)
    inv["F1%1024==0"] += (F1 % 1024 == 0)
    inv["F2%2048==0"] += (F2 % 2048 == 0)
    inv["byte9%8==0"] += (x[9] % 8 == 0)
    inv["F1==u16@5*256"] += (F1 == struct.unpack_from("<H", x, 5)[0] * 256)
    inv["u16@5==4*(F1>>10)"] += (struct.unpack_from("<H", x, 5)[0] == 4 * (F1 >> 10))
    K, M = F1 >> 10, F2 >> 11
    Kset.setdefault(V, set()).add(K)
    Mset.setdefault(V, set()).add(M)
    if V == 2:
        inv["V=02: F1>>10 == len-10"] += (K == L - 10)

print("\n-- 头部不变量 (分母 %d) --" % len(room))
for k, v in inv.items():
    print("   %-26s %d/%d" % (k, v, len(room)))
print("\n-- V 计数 --", dict(sorted(Vcnt.items())))
print("-- K 集合 (V) --")
for V in sorted(Kset):
    print("   V=%02X: %s" % (V, sorted(Kset[V])))
print("-- M 集合 (V) --")
for V in sorted(Mset):
    print("   V=%02X: %s" % (V, sorted(Mset[V])))
print("\n-- V=02 时 K 是否 == len-10 : %d/%d" % (
    sum((struct.unpack_from("<I", x, 4)[0] >> 10) == len(x) - 10 for x in room if x[1] == 2),
    sum(1 for x in room if x[1] == 2)))
