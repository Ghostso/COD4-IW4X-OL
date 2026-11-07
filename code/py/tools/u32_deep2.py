#!/usr/bin/env python3
"""0x08 深挖二：4/13、4/4、80/119、3/48、29/10 全序列；0x6cc0 是否时间戳。"""
import collections
import datetime
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))


def show(svc, task, limit=2):
    print("\n=== %d/%d 全元素序列 ===" % (svc, task))
    seen = 0
    for r in corpus:
        if (r["svc"], r["task"]) != (svc, task):
            continue
        b = bytes.fromhex(r["payload"])
        good, els, why = G.parse(b)
        print("  --- len=%d 元素=%d run=%s ---" % (len(b), len(els), r.get("run")))
        for i, (t, v) in enumerate(els):
            if isinstance(v, bytes):
                if len(v) in (1, 2, 4, 8):
                    iv = int.from_bytes(v, "little", signed=(t == 0x07))
                    extra = ""
                    if len(v) == 4 and 1700000000 <= iv <= 1900000000:
                        extra = "  <~%s>" % datetime.datetime.utcfromtimestamp(iv).strftime("%Y-%m-%d")
                    print("   #%02d 0x%02x len=%d val=%d (0x%x)%s" % (i, t, len(v), iv, iv, extra))
                else:
                    txt = v.decode("latin1", "replace")
                    printable = sum(32 <= c < 127 for c in v)
                    tag = "TXT" if printable > len(v) * 0.7 else "bin"
                    print("   #%02d 0x%02x len=%d [%s] %r" % (i, t, len(v), tag, txt[:60]))
            else:
                print("   #%02d 0x%02x %r" % (i, t, v))
        seen += 1
        if seen >= limit:
            break


for st in [(4, 13), (4, 4), (80, 119), (3, 48), (29, 10), (3, 46), (80, 70)]:
    show(*st)

# 0x6cc0 时间戳检验
print("\n=== 0x6cc0 簇 全部值（转 UTC）===")
vals = []
for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x08 and isinstance(v, bytes) and len(v) == 4:
            iv = int.from_bytes(v, "little")
            if 0x6cc00000 <= iv <= 0x6cc0ffff:
                vals.append(iv)
vals.sort()
for iv in vals:
    print("  %d  0x%08x  %s" % (iv, iv, datetime.datetime.utcfromtimestamp(iv).strftime("%Y-%m-%d %H:%M:%S UTC")))
print("  差值（相邻）:", [vals[i+1]-vals[i] for i in range(min(len(vals)-1, 15))])
