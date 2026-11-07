#!/usr/bin/env python3
"""s137 R3: 110 卷遗留 —— 值 932 在 4/13 与 4/4 的上下文结构.
纯静态语料分析.
"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

def dump(b):
    good, els, why = G.parse(b)
    if not good:
        return None, why
    return els, ""

print("=== A) 4/13 与 4/4 全样本 ===")
for svc, task in ((4, 13), (4, 4)):
    rows = [r for r in corpus if r["svc"] == svc and r["task"] == task]
    print("\n--- %d/%d : %d 条 ---" % (svc, task, len(rows)))
    for r in rows[:3]:
        b = bytes.fromhex(r["payload"])
        els, why = dump(b)
        print("  run=%s idx=%s len=%d hex=%s" % (r.get("run"), r.get("idx"), len(b), b.hex()))
        if els is None:
            print("    PARSE FAIL: %s" % why)
        else:
            for i, (t, v) in enumerate(els):
                if isinstance(v, bytes):
                    iv = int.from_bytes(v, "little") if len(v) in (1, 2, 4, 8) else None
                    print("     #%02d tag=0x%02x len=%d val=%s" % (i, t, len(v), iv if iv is not None else v.hex()))
                else:
                    print("     #%02d tag=0x%02x cnt=%d body=%s" % (i, t, v[0], v[1][:40].hex()))

print("\n=== B) 元素结构统计 (tag 序列) ===")
for svc, task in ((4, 13), (4, 4)):
    seqs = collections.Counter()
    raws = collections.Counter()
    for r in corpus:
        if (r["svc"], r["task"]) != (svc, task):
            continue
        b = bytes.fromhex(r["payload"])
        els, why = dump(b)
        raws[len(b)] += 1
        if els is None:
            seqs[("FAIL", why)] += 1
        else:
            seqs[tuple((t, len(v) if isinstance(v, bytes) else "arr") for t, v in els)] += 1
    print("\n  %d/%d  payload len dist: %s" % (svc, task, dict(raws)))
    for k, n in seqs.most_common(12):
        print("     x%-5d %s" % (n, k))

print("\n=== C) 值 932 的所有出现 (全 corpus, 全位置) ===")
pos = collections.Counter()
perrun = collections.defaultdict(int)
nontag = collections.Counter()
for r in corpus:
    b = bytes.fromhex(r["payload"])
    els, why = dump(b)
    p = []
    if els is not None:
        for i, (t, v) in enumerate(els):
            if isinstance(v, bytes) and len(v) == 4 and int.from_bytes(v, "little") == 932:
                p.append((t, i, len(els)))
    # 也扫原始字节里任何偏移上的 932 (0xa4 0x03 0x00 0x00)
    pat = (932).to_bytes(4, "little")
    off = 0
    while True:
        j = b.find(pat, off)
        if j < 0:
            break
        nontag[("raw", j)] += 1
        off = j + 1
    for key in set(p):
        pos[(r["svc"], r["task"]) + key] += 1
    if p:
        perrun[r.get("run")] += 1
for k, n in pos.most_common(20):
    print("  svc=%d/%d tag=0x%02x elem#%d/%d  x%d" % (k[0], k[1], k[2], k[3], k[4], n))
print("  --- raw (任何偏移) 出现次数 top:")
for k, n in nontag.most_common(20):
    print("     %s x%d" % (k, n))
