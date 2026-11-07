#!/usr/bin/env python3
"""0x6c 修正模型验证：body = [N][item x N]（N=元素数, 含自身? 还是 [N][item x N] 总长 N+1?)
上面测出 body[0]==len(u) 恒成立 ⇒ body=[N][item x (N-1)]。
再验证 tail(cnt) 与 body 的关系，以及 28/4 的 126 个 item 分布。"""
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
                yield (r["svc"], r["task"], u, cnt, r.get("run"))


print("=== 新模型: body = [N][item x (N-1)]  (N=u32总数) ===")
print("=== 28/4 的 126 个 item 是否恒定 + 分布 ===")
sets = collections.Counter()
for svc, task, u, cnt, run in all_6c():
    if (svc, task) == (28, 4):
        sets[tuple(u)] += 1
print("distinct = %d" % len(sets))
for k, n in sets.most_common(1):
    items = list(k)[1:]
    print("  N=%d, item数=%d, x%d" % (k[0], len(items), n))
    print("  items=%s" % items)
    # 是否连续 0..126?
    print("  是否 0..%d 连续: %s" % (len(items)-1, items == list(range(len(items)))))

print("\n=== 28/1 各 body 的 item 部分 ===")
c = collections.Counter()
for svc, task, u, cnt, run in all_6c():
    if (svc, task) == (28, 1):
        c[(tuple(u[1:]), u[0] if u else 0, cnt)] += 1
for k, n in c.most_common():
    print("  items=%-10s N=%d tail=%d x%d" % (list(k[0]), k[1], k[2], n))

print("\n=== tail(cnt) 与 body 的关系：tail 是否 = 某全局上限 ===")
c = collections.Counter()
for svc, task, u, cnt, run in all_6c():
    c[(svc, task, cnt)] += 1
for k, n in sorted(c.items()):
    print("  %d/%d tail=%d x%d" % (k[0], k[1], k[2], n))
