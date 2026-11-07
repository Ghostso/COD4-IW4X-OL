#!/usr/bin/env python3
"""6/14 及 6/5、6/18 的明文命令开头实测：mmbook vs mmstart vs 其它。"""
import collections
import json
import re
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

heads = collections.Counter()
for r in corpus:
    if r["svc"] != 6:
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        heads[(r["task"], "PARSE_FAIL")] += 1
        continue
    for t, v in els:
        if t == 0x13 and isinstance(v, bytes):
            s = v.decode("latin1")
            m = re.match(r"^([a-zA-Z_]+)", s)
            heads[(r["task"], m.group(1) if m else "?", len(v))] += 1

print("=== service 6 的 blob 开头词 ===")
for k, v in heads.most_common(30):
    print("  task=%-3s head=%-12s %s : %d" % (k[0], k[1], ("len=%d" % k[2]) if len(k) > 2 else "", v))

# 直接搜全语料 mmbook / mmstart
print("\n=== 全语料 mmbook / mmstart 出现 ===")
mb = collections.Counter()
ms = collections.Counter()
for r in corpus:
    b = bytes.fromhex(r["payload"])
    if b"mmbook" in b:
        mb[(r["svc"], r["task"])] += 1
    if b"mmstart" in b:
        ms[(r["svc"], r["task"])] += 1
print("  mmbook :", dict(mb), "合计", sum(mb.values()))
print("  mmstart:", dict(ms), "合计", sum(ms.values()))

# 6/14 前 3 条完整明文
print("\n=== 6/14 前 3 条 blob 明文 ===")
n = 0
for r in corpus:
    if (r["svc"], r["task"]) != (6, 14):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x13 and isinstance(v, bytes):
            print("  [%d] %s" % (len(v), v.decode("latin1").encode("unicode_escape").decode()[:300]))
            break
    n += 1
    if n >= 3:
        break
