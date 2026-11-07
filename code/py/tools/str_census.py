#!/usr/bin/env python3
"""0x10 字符串全语料：所有不同取值 + 次数 + task 分布 + 可打印性分类。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

vals = collections.Counter()
task_of = collections.defaultdict(collections.Counter)
nstr = 0
nbytes = 0
nonascii = 0
empty = 0

for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t != 0x10 or not isinstance(v, bytes):
            continue
        nstr += 1
        nbytes += len(v)
        if not v:
            empty += 1
        if any(c < 0x20 or c >= 0x7F for c in v):
            nonascii += 1
        try:
            s = v.decode("utf-8")
        except Exception:
            s = v.decode("latin1", "replace")
        vals[s] += 1
        task_of[s][(r["svc"], r["task"])] += 1

print("字符串总数 = %d, 总字节 = %d, 空串 = %d, 含非 ASCII/控制符 = %d" % (nstr, nbytes, empty, nonascii))
print("不同取值 = %d" % len(vals))
print("\n=== 全部取值（按次数）===")
for s, n in vals.most_common():
    tasks = task_of[s].most_common(4)
    ts = " ".join("%d/%d:%d" % (a, b2, c) for (a, b2), c in tasks)
    disp = s.encode("unicode_escape").decode()[:48]
    print("  x%-4d %-50r  [%s]" % (n, disp, ts))
