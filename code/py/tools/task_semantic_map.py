#!/usr/bin/env python3
"""把 55 个 task 的固定 payload 与权威语义表对照，逐条给字节解读。
重点：3/46,48,53(生涯/结算) 9/5,9/14(好友) 29/10(任务) 68/3,68/8(遥测) 102/1,5,7"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

TARGETS = [(3, 46), (3, 48), (3, 53), (9, 5), (9, 14), (29, 10), (102, 1), (102, 2), (102, 5), (102, 7),
           (68, 3), (68, 8), (71, 2), (71, 3), (71, 4), (71, 7), (71, 9), (71, 10), (71, 11), (71, 13),
           (71, 15), (71, 18), (71, 20), (4, 13), (4, 4), (10, 20), (12, 6), (11, 2), (21, 3), (80, 130),
           (80, 173), (80, 174), (80, 230), (80, 232), (93, 1), (8, 1), (8, 2)]

for key in TARGETS:
    recs = [r for r in corpus if (r["svc"], r["task"]) == key]
    if not recs:
        continue
    forms = collections.Counter(r["payload"] for r in recs)
    print("\n=== %d/%d  n=%d distinct=%d ===" % (key[0], key[1], len(recs), len(forms)))
    hx, n = forms.most_common(1)[0]
    b = bytes.fromhex(hx)
    good, els, why = G.parse(b)
    print("  最常见: x%d len=%d good=%s hex=%s" % (n, len(b), good, hx[:100]))
    if good:
        desc = []
        for i, (t, v) in enumerate(els):
            if isinstance(v, bytes) and len(v) in (1, 2, 4, 8):
                u = int.from_bytes(v, "little")
                s = int.from_bytes(v, "little", signed=True) if t == 0x07 else u
                desc.append("#%d 0x%02x=%s" % (i, t, s))
            elif isinstance(v, bytes):
                try:
                    st = v.decode("ascii")
                    if all(32 <= ord(c) < 127 for c in st) and st:
                        desc.append("#%d 0x%02x=%r" % (i, t, st))
                    else:
                        desc.append("#%d 0x%02x[len%d]" % (i, t, len(v)))
                except Exception:
                    desc.append("#%d 0x%02x[len%d]" % (i, t, len(v)))
        print("  " + " | ".join(desc))
