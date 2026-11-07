#!/usr/bin/env python3
"""未定名小 task 的固定 payload 结构解剖。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

TARGETS = [(3, 46), (3, 48), (3, 53), (9, 5), (9, 14), (29, 10), (71, 2), (71, 9),
           (71, 10), (71, 13), (71, 20), (68, 3), (68, 8), (93, 1), (80, 130),
           (80, 230), (80, 232), (80, 173), (102, 2), (102, 5), (11, 2), (21, 3), (12, 6)]

for key in TARGETS:
    recs = [r for r in corpus if (r["svc"], r["task"]) == key]
    if not recs:
        continue
    forms = collections.Counter(r["payload"] for r in recs)
    print("\n########## %d/%d  n=%d distinct=%d ##########" % (key[0], key[1], len(recs), len(forms)))
    for hx, n in forms.most_common(3):
        b = bytes.fromhex(hx)
        good, els, why = G.parse(b)
        print("  x%-4d len=%d good=%s  hex=%s" % (n, len(b), good, hx[:120]))
        if good and len(els) <= 12:
            desc = []
            for i, (t, v) in enumerate(els):
                if isinstance(v, bytes) and len(v) in (1, 2, 4, 8):
                    desc.append("#%d 0x%02x=%d" % (i, t, int.from_bytes(v, "little", signed=(t == 0x07))))
                elif isinstance(v, bytes):
                    try:
                        s = v.decode("ascii")
                        if s.isprintable():
                            desc.append("#%d 0x%02x=%r" % (i, t, s))
                        else:
                            desc.append("#%d 0x%02x[len%d]" % (i, t, len(v)))
                    except Exception:
                        desc.append("#%d 0x%02x[len%d]" % (i, t, len(v)))
            print("      " + " | ".join(desc))
