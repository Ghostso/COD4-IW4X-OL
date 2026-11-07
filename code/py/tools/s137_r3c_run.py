#!/usr/bin/env python3
"""s137 R3c: 那个'异常 run' ONCE_20261029_143736 的完整序列 + 邻域上下文.
以及 svc=4 的名称.
"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))
RUN = sys.argv[2] if len(sys.argv) > 2 else "ONCE_20261029_143736"

def vals(r):
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        return None
    return [(t, int.from_bytes(v, "little") if isinstance(v, bytes) and len(v) in (1, 2, 4, 8) else v)
            for t, v in els]

rows = [r for r in corpus if r.get("run") == RUN]
rows.sort(key=lambda r: (r.get("idx") if isinstance(r.get("idx"), int) else 0))
print("=== run %s : %d 条 ===" % (RUN, len(rows)))
for r in rows:
    v = vals(r)
    mark = ""
    if (r["svc"], r["task"]) in ((4, 13), (4, 4)):
        mark = "   <<<<<< 4/%d elem0=%s" % (r["task"], v[0][1] if v else "?")
    print("  idx=%-4s %3d/%-3d len=%-4d %s%s" % (
        r.get("idx"), r["svc"], r["task"], len(bytes.fromhex(r["payload"])),
        (str(v)[:150] if v else "FAIL"), mark))

print("\n=== svc 名字 (service 4) ===")
for f in ("_byte_papers/svc_info_table.txt", "_byte_papers/svc_names2.txt",
          "_byte_papers/svc_catalog.txt", "_byte_papers/orig_svc_names.txt",
          "_byte_papers/dw_svc_names.txt"):
    try:
        t = open(f, encoding="utf-8", errors="replace").read()
    except Exception as e:
        continue
    for ln in t.splitlines():
        if " 4" in ln or "svc 4" in ln.lower() or "=4" in ln or " 4=" in ln:
            if "4" in ln:
                print("  [%s] %s" % (f, ln))
