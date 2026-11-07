#!/usr/bin/env python3
"""10/21 与 10/12 全结构；71/11 base64 解码；字符串顺序。"""
import base64
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))


def dump(svc, task, limit=2):
    print("\n=== %d/%d 结构（前 %d 条）===" % (svc, task, limit))
    seen = 0
    for r in corpus:
        if (r["svc"], r["task"]) != (svc, task):
            continue
        b = bytes.fromhex(r["payload"])
        good, els, why = G.parse(b)
        print("  len=%d 元素=%d run=%s" % (len(b), len(els), r.get("run")))
        for i, (t, v) in enumerate(els):
            if isinstance(v, bytes):
                esc = v.decode("latin1", "replace").encode("unicode_escape").decode()
                print("    #%02d 0x%02x len=%d %s" % (i, t, len(v), esc[:70]))
            else:
                print("    #%02d 0x%02x %r" % (i, t, v))
        seen += 1
        if seen >= limit:
            break


dump(10, 21, 2)
dump(10, 12, 2)
dump(71, 11, 2)
dump(71, 2, 2)

# 10/21 的字符串序列（一条完整报文里出现的所有 .info）
print("\n=== 10/21 每个报文的字符串序列（前 3 条）===")
seen = 0
for r in corpus:
    if (r["svc"], r["task"]) != (10, 21):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    strs = [v.decode("latin1", "replace") for t, v in els if t == 0x10]
    tags = [hex(t) for t, v in els]
    print("  元素序列 tags=%s" % tags)
    print("  字符串=%r" % strs)
    seen += 1
    if seen >= 3:
        break

# 10/21 报文数 & 每报文 .info 数
print("\n=== 10/21 统计 ===")
cnt = collections.Counter()
nmsg = 0
for r in corpus:
    if (r["svc"], r["task"]) != (10, 21):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    nmsg += 1
    ns = sum(1 for t, v in els if t == 0x10)
    cnt[ns] += 1
print("  报文数=%d, 每报文字符串数分布=%s" % (nmsg, dict(cnt)))

# 71/11 base64
print("\n=== 71/11 的 base64 ===")
s = "MjAxNTA3MjQxNzMx"
d = base64.b64decode(s)
print("  %s -> %r (len=%d)" % (s, d, len(d)))
