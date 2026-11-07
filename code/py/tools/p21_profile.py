#!/usr/bin/env python3
"""21/1 与 21/12 每个元素位置的取值分布（找出哪些是常量、哪些是变量）。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))


def profile(svc, task, npos):
    print("\n=== %d/%d 各位置取值分布 ===" % (svc, task))
    pos = collections.defaultdict(collections.Counter)
    tagpos = collections.defaultdict(collections.Counter)
    for r in corpus:
        if (r["svc"], r["task"]) != (svc, task):
            continue
        b = bytes.fromhex(r["payload"])
        good, els, why = G.parse(b)
        if not good:
            continue
        for i, (t, v) in enumerate(els):
            tagpos[i][hex(t)] += 1
            if isinstance(v, bytes) and len(v) in (1, 2, 4, 8):
                iv = int.from_bytes(v, "little", signed=(t == 0x07))
                pos[i][iv] += 1
            elif isinstance(v, bytes):
                pos[i][("len", len(v))] += 1
    for i in range(npos):
        tc = tagpos[i]
        pc = pos[i]
        if not pc:
            continue
        if len(pc) == 1:
            v = list(pc)[0]
            print("  #%02d %s  恒=%s  x%d" % (i, dict(tc), v, list(pc.values())[0]))
        else:
            print("  #%02d %s  distinct=%d top=%s" % (i, dict(tc), len(pc), pc.most_common(4)))


profile(21, 1, 31)
profile(21, 12, 33)
