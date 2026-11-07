#!/usr/bin/env python3
"""0x10 字符串：排除遥测(71/3,71/7)后剩余的所有取值；以及含非ASCII/控制符的串。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

non_tel = collections.Counter()
task_of = collections.defaultdict(collections.Counter)
binary = collections.Counter()

for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t != 0x10 or not isinstance(v, bytes):
            continue
        if any(c < 0x20 or c >= 0x7F for c in v):
            binary[(r["svc"], r["task"], len(v))] += 1
        if (r["svc"], r["task"]) in ((71, 3), (71, 7)):
            continue
        try:
            s = v.decode("utf-8")
        except Exception:
            s = v.decode("latin1", "replace")
        non_tel[s] += 1
        task_of[s][(r["svc"], r["task"])] += 1

print("=== 非遥测字符串：不同取值 %d 个 ===" % len(non_tel))
for s, n in non_tel.most_common():
    tasks = " ".join("%d/%d:%d" % (a, b2, c) for (a, b2), c in task_of[s].most_common(4))
    disp = s.encode("unicode_escape").decode()
    print("  x%-4d %-56s [%s]" % (n, disp[:56], tasks))

print("\n=== 含非 ASCII/控制符的字符串（按 task/长度）===")
for k, n in binary.most_common(30):
    print("  %d/%d len=%d  x%d" % (k[0], k[1], k[2], n))
