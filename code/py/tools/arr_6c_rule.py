#!/usr/bin/env python3
"""0x6c 全语料：body[0] == len(body_u32)? 若成立则 body[0] 是元素计数(含自身)。
并厘清 tail(cnt) 语义。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))


def all_6c():
    for r in corpus:
        b = bytes.fromhex(r["payload"])
        good, els, why = G.parse(b)
        if not good:
            continue
        for t, v in els:
            if t == 0x6C:
                cnt, body = v
                u = [int.from_bytes(body[j:j+4], "little") for j in range(0, len(body) - len(body) % 4, 4)]
                yield (r["svc"], r["task"], u, cnt)


print("=== body[0] == len(u) 验证（含空 body）===")
eq = neq = empty = 0
neq_samples = []
for svc, task, u, cnt in all_6c():
    if not u:
        empty += 1
        continue
    if u[0] == len(u):
        eq += 1
    else:
        neq += 1
        if len(neq_samples) < 10:
            neq_samples.append((svc, task, u[:6], len(u), cnt))
print("body[0]==len: %d ; !=: %d ; empty: %d" % (eq, neq, empty))
for s in neq_samples:
    print("  %d/%d body[:6]=%s len=%d tail=%d" % s)

print("\n=== body[0] == len(u)-1 验证（body[0]=计数, 后面才是数据）===")
eq2 = neq2 = 0
for svc, task, u, cnt in all_6c():
    if not u:
        continue
    if u[0] == len(u) - 1:
        eq2 += 1
    else:
        neq2 += 1
print("body[0]==len-1: %d ; !=: %d" % (eq2, neq2))

print("\n=== 各 (svc,task) 的 body[0] 与 len(u) 与 tail 三元组 ===")
c = collections.Counter()
for svc, task, u, cnt in all_6c():
    c[(svc, task, u[0] if u else None, len(u), cnt)] += 1
for k, n in sorted(c.items(), key=lambda x: (-x[1], x[0])):
    print("  %d/%d body[0]=%-4s len=%-4d tail=%-4d x%d" % (k[0], k[1], k[2], k[3], k[4], n))
