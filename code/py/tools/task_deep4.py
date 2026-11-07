#!/usr/bin/env python3
"""4/4 vs 4/13 深挖：932 是什么、101 是什么；71/4 的字段；8/3 的 blob；68/3 的 3 形态。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

# 4/13 与 4/4 的全部形态
for key in [(4, 13), (4, 4)]:
    print("\n########## %d/%d ##########" % key)
    forms = collections.Counter(r["payload"] for r in corpus if (r["svc"], r["task"]) == key)
    for hx, n in forms.most_common(12):
        b = bytes.fromhex(hx)
        good, els, why = G.parse(b)
        desc = []
        for i, (t, v) in enumerate(els):
            if isinstance(v, bytes) and len(v) in (1, 2, 4, 8):
                s = int.from_bytes(v, "little", signed=(t == 0x07))
                desc.append("%d" % s)
            elif isinstance(v, bytes):
                desc.append("blob%d" % len(v))
        print("  x%-4d %s" % (n, desc))

# 71/4 的 6 个字段
print("\n########## 71/4 字段 ##########")
for r in corpus:
    if (r["svc"], r["task"]) != (71, 4):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    for i, (t, v) in enumerate(els):
        if isinstance(v, bytes) and len(v) in (1, 2, 4, 8):
            print("  #%d 0x%02x=%d" % (i, t, int.from_bytes(v, "little", signed=(t == 0x07))))
        elif isinstance(v, bytes):
            try:
                s = v.decode("ascii")
                if all(32 <= ord(c) < 127 for c in s):
                    print("  #%d 0x%02x='%s'" % (i, t, s))
                else:
                    print("  #%d 0x%02x[len%d]=%s" % (i, t, len(v), v.hex()[:40]))
            except Exception:
                print("  #%d 0x%02x[len%d]" % (i, t, len(v)))
    break

# 68/3 的 3 形态与 blob 内容
print("\n########## 68/3 3 形态 ##########")
forms = collections.Counter(r["payload"] for r in corpus if (r["svc"], r["task"]) == (68, 3))
for hx, n in forms.most_common():
    b = bytes.fromhex(hx)
    good, els, why = G.parse(b)
    print("  x%-4d len=%d" % (n, len(b)))
    for i, (t, v) in enumerate(els):
        if isinstance(v, bytes) and len(v) in (1, 2, 4, 8):
            print("     #%d 0x%02x=%d" % (i, t, int.from_bytes(v, "little", signed=(t == 0x07))))
        elif isinstance(v, bytes):
            print("     #%d 0x%02x[len%d]=%s" % (i, t, len(v), v.hex()[:60]))
            if len(v) > 6:
                try:
                    print("        ascii=%r" % v.decode("latin1")[:50])
                except Exception:
                    pass
